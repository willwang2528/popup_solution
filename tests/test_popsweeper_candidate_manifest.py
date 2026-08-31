from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "dataset-v1"
    / "scripts"
    / "build_popsweeper_candidate_manifest.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("popsweeper_manifest", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_fixture(path: Path, entries: list[str]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for index, name in enumerate(entries):
            archive.writestr(name, f"image-{index}".encode())
        archive.writestr("__MACOSX/app-blocking pop-ups/basic/train/ads/._1.jpg", b"fork")
        archive.writestr("app-blocking pop-ups/basic/train/ads/.DS_Store", b"metadata")


class PopSweeperCandidateManifestTests(unittest.TestCase):
    def test_discovery_parses_split_label_and_source_kind(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "source.zip"
            write_fixture(
                archive_path,
                [
                    "app-blocking pop-ups/basic/train/ads/123.jpg",
                    "app-blocking pop-ups/basic/valid/no_ads/App_Name_frame7.jpg",
                ],
            )

            rows = module.discover_candidates(archive_path)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["source_record_id"], "popsweeper:train:ads:123")
        self.assertTrue(rows[0]["popup_present_gt"])
        self.assertEqual(rows[0]["source_kind"], "rico_numeric_candidate")
        self.assertEqual(rows[1]["official_split"], "valid")
        self.assertFalse(rows[1]["popup_present_gt"])
        self.assertEqual(rows[1]["source_kind"], "recorded_app_frame")
        self.assertEqual(rows[1]["group_key"], "recording:App_Name")
        self.assertEqual(rows[1]["message_annotation_status"], "pending")
        self.assertFalse(rows[1]["eligible_for_v1_message_metrics"])

    def test_n120_profile_freezes_split_label_and_kind_quotas(self):
        module = load_module()
        quotas = module.n120_audit_quotas()

        self.assertEqual(sum(quotas.values()), 120)
        self.assertEqual(
            quotas[("train", "ads", "rico_numeric_candidate")], 27
        )
        self.assertEqual(
            quotas[("train", "no_ads", "recorded_app_frame")], 9
        )
        self.assertEqual(
            quotas[("valid", "ads", "rico_numeric_candidate")], 9
        )
        self.assertEqual(
            quotas[("test", "no_ads", "recorded_app_frame")], 3
        )

    def test_deduplication_removes_content_and_group_leakage(self):
        module = load_module()
        rows = [
            {
                "source_record_id": "popsweeper:train:ads:1",
                "official_split": "train",
                "content_key": "same-content",
                "group_key": "rico:1",
            },
            {
                "source_record_id": "popsweeper:test:ads:2",
                "official_split": "test",
                "content_key": "same-content",
                "group_key": "rico:2",
            },
            {
                "source_record_id": "popsweeper:valid:no_ads:App_frame2",
                "official_split": "valid",
                "content_key": "content-2",
                "group_key": "recording:App",
            },
            {
                "source_record_id": "popsweeper:test:no_ads:App_frame9",
                "official_split": "test",
                "content_key": "content-3",
                "group_key": "recording:App",
            },
        ]

        kept, report = module.deduplicate_candidates(rows)

        self.assertEqual(
            [row["source_record_id"] for row in kept],
            [
                "popsweeper:train:ads:1",
                "popsweeper:valid:no_ads:App_frame2",
            ],
        )
        self.assertEqual(report["removed_exact_content"], 1)
        self.assertEqual(report["removed_group_leakage"], 1)

    def test_rico_join_requires_both_semantic_json_and_png(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            rico_path = Path(directory) / "rico.zip"
            with zipfile.ZipFile(rico_path, "w") as archive:
                archive.writestr("semantic_annotations/123.json", "{}")
                archive.writestr("semantic_annotations/123.png", b"png")
                archive.writestr("semantic_annotations/456.json", "{}")

            rico_ids = module.load_complete_rico_ids(rico_path)
            joined, report = module.apply_rico_join(
                [
                    {
                        "source_kind": "rico_numeric_candidate",
                        "source_basename": "123",
                    },
                    {
                        "source_kind": "rico_numeric_candidate",
                        "source_basename": "456",
                    },
                    {
                        "source_kind": "recorded_app_frame",
                        "source_basename": "App_frame1",
                    },
                ],
                rico_ids,
            )

        self.assertEqual(rico_ids, {"123"})
        self.assertEqual(joined[0]["rico_join_status"], "verified_json_png")
        self.assertEqual(joined[1]["rico_join_status"], "not_found")
        self.assertEqual(joined[2]["rico_join_status"], "not_applicable")
        self.assertEqual(report["numeric_verified"], 1)
        self.assertEqual(report["numeric_not_found"], 1)

    def test_stratified_sample_is_deterministic_and_meets_quotas(self):
        module = load_module()
        rows = []
        for label in ("ads", "no_ads"):
            for kind in ("rico_numeric_candidate", "recorded_app_frame"):
                for index in range(8):
                    rows.append(
                        {
                            "source_record_id": f"{label}:{kind}:{index}",
                            "source_label": label,
                            "source_kind": kind,
                        }
                    )

        first = module.stratified_sample(
            rows,
            per_stratum={
                ("ads", "rico_numeric_candidate"): 3,
                ("ads", "recorded_app_frame"): 2,
                ("no_ads", "rico_numeric_candidate"): 3,
                ("no_ads", "recorded_app_frame"): 2,
            },
            seed=20260901,
        )
        second = module.stratified_sample(
            list(reversed(rows)),
            per_stratum={
                ("ads", "rico_numeric_candidate"): 3,
                ("ads", "recorded_app_frame"): 2,
                ("no_ads", "rico_numeric_candidate"): 3,
                ("no_ads", "recorded_app_frame"): 2,
            },
            seed=20260901,
        )

        self.assertEqual(first, second)
        self.assertEqual(len(first), 10)
        counts = {}
        for row in first:
            key = (row["source_label"], row["source_kind"])
            counts[key] = counts.get(key, 0) + 1
        self.assertEqual(counts[("ads", "rico_numeric_candidate")], 3)
        self.assertEqual(counts[("no_ads", "recorded_app_frame")], 2)

    def test_stratified_sample_rejects_unavailable_quota(self):
        module = load_module()
        with self.assertRaisesRegex(ValueError, "insufficient candidates"):
            module.stratified_sample(
                [
                    {
                        "source_record_id": "only-one",
                        "source_label": "ads",
                        "source_kind": "rico_numeric_candidate",
                    }
                ],
                per_stratum={("ads", "rico_numeric_candidate"): 2},
                seed=1,
            )

    def test_cli_writes_manifest_and_summary_without_extracting_images(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "source.zip"
            output_path = root / "candidates.jsonl"
            summary_path = root / "summary.json"
            entries = []
            for label in ("ads", "no_ads"):
                for index in range(3):
                    numeric_id = index + (100 if label == "ads" else 200)
                    entries.append(
                        f"app-blocking pop-ups/basic/train/{label}/{numeric_id}.jpg"
                    )
                    entries.append(
                        f"app-blocking pop-ups/basic/test/{label}/{label}_App_{index}_frame1.jpg"
                    )
            write_fixture(archive_path, entries)

            completed = subprocess.run(
                [
                    str(Path(__import__("sys").executable)),
                    str(SCRIPT),
                    str(archive_path),
                    "--output",
                    str(output_path),
                    "--summary",
                    str(summary_path),
                    "--per-label",
                    "4",
                    "--named-per-label",
                    "2",
                    "--seed",
                    "7",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            rows = [json.loads(line) for line in output_path.read_text().splitlines()]
            summary = json.loads(summary_path.read_text())
            self.assertEqual(len(rows), 8)
            self.assertEqual(summary["candidate_count"], 8)
            self.assertEqual(summary["message_annotation_status"], "pending")
            self.assertFalse(summary["empirical_message_dataset_complete"])
            self.assertEqual(list(root.glob("*.jpg")), [])


if __name__ == "__main__":
    unittest.main()
