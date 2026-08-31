from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
import zipfile
import zlib
from collections import Counter
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "dataset-v1"
    / "scripts"
    / "export_annotation_media.py"
)


def load_module():
    if not SCRIPT.is_file():
        raise AssertionError("export_annotation_media.py is missing")
    spec = importlib.util.spec_from_file_location("export_annotation_media", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def initialize_ignored_output(root: Path) -> Path:
    subprocess.run(
        ["git", "init", "--quiet", str(root)],
        check=True,
        capture_output=True,
        text=True,
    )
    (root / ".gitignore").write_text("annotation-media/\n", encoding="utf-8")
    return root / "annotation-media" / "pilot"


def fixture_candidate(
    *,
    member: str,
    payload: bytes,
    split: str,
    label: str,
    basename: str,
    source_kind: str,
) -> dict:
    crc = zlib.crc32(payload) & 0xFFFFFFFF
    row = {
        "source_record_id": f"popsweeper:{split}:{label}:{basename}",
        "archive_member_path": member,
        "archive_member_crc32": f"{crc:08x}",
        "archive_member_compressed_bytes": len(payload),
        "archive_member_uncompressed_bytes": len(payload),
        "content_key": f"crc32:{crc:08x}:bytes:{len(payload)}",
        "official_split": split,
        "source_label": label,
        "popup_present_gt": label == "ads",
        "source_basename": basename,
        "source_kind": source_kind,
        "group_key": (
            f"rico:{basename}"
            if source_kind == "rico_numeric_candidate"
            else "recording:" + basename.rsplit("_frame", 1)[0]
        ),
        "raw_image_distribution": "adapter_only_not_redistributed",
        "message_annotation_status": "pending",
        "eligible_for_v1_message_metrics": False,
        "sampling_stratum": f"{split}/{label}/{source_kind}",
    }
    if source_kind == "rico_numeric_candidate":
        row.update(
            {
                "rico_join_status": "verified_json_png",
                "rico_semantic_json_member": f"semantic_annotations/{basename}.json",
                "rico_semantic_png_member": f"semantic_annotations/{basename}.png",
                "rico_raw_distribution": "adapter_only_not_redistributed",
            }
        )
    else:
        row["rico_join_status"] = "not_applicable"
    return row


def write_frozen_pilot(
    root: Path,
    candidates: list[dict],
    *,
    reverse: bool = True,
) -> Path:
    path = root / "pilot.jsonl"
    ordered = list(reversed(candidates)) if reverse else list(candidates)
    rows = []
    for index, candidate in enumerate(ordered, 1):
        pilot_item_id = f"PMJ-PILOT-{index:03d}"
        rows.append(
            {
                "adapter_item_handle": (
                    f"adapter://popsweeper/pilot/{pilot_item_id}"
                ),
                "archive_member_crc32": candidate["archive_member_crc32"],
                "archive_member_path": candidate["archive_member_path"],
                "archive_member_uncompressed_bytes": candidate[
                    "archive_member_uncompressed_bytes"
                ],
                "batch_id": "popsweeper-message-pilot-test",
                "content_key": candidate["content_key"],
                "coordinator_display_order": index,
                "eligible_for_message_metrics": False,
                "group_key": candidate["group_key"],
                "human_message_gold_status": "pending",
                "official_split_audit_stratum": candidate["official_split"],
                "pilot_item_id": pilot_item_id,
                "protocol_version": "1.0.0",
                "raw_image_distribution": "adapter_only_not_redistributed",
                "selection_seed": "sha256:test-pilot",
                "source_kind": candidate["source_kind"],
                "source_label_role": "sampling_only_not_human_message_gold",
                "source_record_id": candidate["source_record_id"],
                "source_sampling_label": candidate["source_label"],
            }
        )
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    return path


def write_fixture(
    root: Path,
    *,
    unsafe_member: bool = False,
    omit_rico_png: bool = False,
) -> tuple[Path, Path, Path, list[dict], dict[str, bytes]]:
    pop_archive = root / "popsweeper.zip"
    rico_archive = root / "rico.zip"
    manifest = root / "candidates.jsonl"

    numeric_member = "app-blocking pop-ups/basic/train/ads/123.jpg"
    named_member = (
        "app-blocking pop-ups/basic/test/no_ads/Example_App_frame7.jpg"
    )
    payloads = {
        "numeric": b"numeric-popup-screenshot",
        "named": b"named-no-popup-screenshot",
        "rico_json": b'{"activity":{"root":[]}}',
        "rico_png": b"rico-semantic-png",
    }
    with zipfile.ZipFile(pop_archive, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr(numeric_member, payloads["numeric"])
        zf.writestr(named_member, payloads["named"])
        if unsafe_member:
            zf.writestr("../escape.txt", b"must-never-be-written")
    with zipfile.ZipFile(rico_archive, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr("semantic_annotations/123.json", payloads["rico_json"])
        if not omit_rico_png:
            zf.writestr("semantic_annotations/123.png", payloads["rico_png"])

    candidates = [
        fixture_candidate(
            member=numeric_member,
            payload=payloads["numeric"],
            split="train",
            label="ads",
            basename="123",
            source_kind="rico_numeric_candidate",
        ),
        fixture_candidate(
            member=named_member,
            payload=payloads["named"],
            split="test",
            label="no_ads",
            basename="Example_App_frame7",
            source_kind="recorded_app_frame",
        ),
    ]
    manifest.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in candidates),
        encoding="utf-8",
    )
    return pop_archive, rico_archive, manifest, candidates, payloads


class AnnotationMediaAdapterTests(unittest.TestCase):
    def test_valid_export_writes_two_local_items_and_verified_artifact_hashes(self):
        """Catches an adapter that validates metadata but never creates usable media."""
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pop, rico, manifest, candidates, payloads = write_fixture(root)
            pilot = write_frozen_pilot(root, candidates)
            output = initialize_ignored_output(root)

            report = module.export_annotation_media(
                candidates_path=manifest,
                pilot_manifest_path=pilot,
                popsweeper_archive=pop,
                popsweeper_sha256=sha256(pop),
                rico_archive=rico,
                rico_sha256=sha256(rico),
                output_dir=output,
                pilot_count=2,
                seed=17,
            )

            self.assertEqual(report["candidate_count"], 2)
            self.assertEqual(report["popsweeper_archive_sha256"], sha256(pop))
            self.assertEqual(report["rico_archive_sha256"], sha256(rico))
            records = [
                json.loads(line)
                for line in (output / "pilot-manifest.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual(len(records), 2)
            self.assertEqual(
                [record["pilot_item_id"] for record in records],
                ["PMJ-PILOT-001", "PMJ-PILOT-002"],
            )
            self.assertEqual(
                records[0]["source_record_id"],
                "popsweeper:test:no_ads:Example_App_frame7",
            )
            by_id = {record["source_record_id"]: record for record in records}
            numeric = by_id["popsweeper:train:ads:123"]
            named = by_id["popsweeper:test:no_ads:Example_App_frame7"]
            self.assertEqual(len(numeric["artifacts"]), 3)
            self.assertEqual(len(named["artifacts"]), 1)
            for record in records:
                for artifact in record["artifacts"]:
                    exported = output / artifact["relative_path"]
                    self.assertTrue(exported.is_file())
                    self.assertEqual(artifact["sha256"], sha256(exported))
            screenshot = output / numeric["artifacts"][0]["relative_path"]
            self.assertEqual(screenshot.read_bytes(), payloads["numeric"])

    def test_frozen_pilot_reference_must_exactly_match_candidate_manifest(self):
        """Catches a frozen pilot that silently redirects an ID to another member."""
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pop, rico, manifest, candidates, _ = write_fixture(root)
            pilot = write_frozen_pilot(root, candidates)
            rows = [json.loads(line) for line in pilot.read_text().splitlines()]
            rows[0]["archive_member_path"] = candidates[0]["archive_member_path"]
            pilot.write_text(
                "".join(json.dumps(row) + "\n" for row in rows),
                encoding="utf-8",
            )
            output = initialize_ignored_output(root)

            with self.assertRaisesRegex(
                module.AdapterError, "frozen pilot .* does not match candidate"
            ):
                module.export_annotation_media(
                    candidates_path=manifest,
                    pilot_manifest_path=pilot,
                    popsweeper_archive=pop,
                    popsweeper_sha256=sha256(pop),
                    rico_archive=rico,
                    rico_sha256=sha256(rico),
                    output_dir=output,
                    pilot_count=2,
                    seed=17,
                )

            self.assertFalse(output.exists())

    def test_wrong_archive_sha_fails_before_output_exists(self):
        """Catches export from an archive other than the pinned source."""
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pop, rico, manifest, _, _ = write_fixture(root)
            output = initialize_ignored_output(root)

            with self.assertRaisesRegex(module.AdapterError, "SHA-256 mismatch"):
                module.export_annotation_media(
                    candidates_path=manifest,
                    popsweeper_archive=pop,
                    popsweeper_sha256="0" * 64,
                    rico_archive=rico,
                    rico_sha256=sha256(rico),
                    output_dir=output,
                    pilot_count=2,
                    seed=17,
                )

            self.assertFalse(output.exists())

    def test_unreferenced_unsafe_archive_member_blocks_all_output(self):
        """Catches path traversal hidden elsewhere in an otherwise usable ZIP."""
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pop, rico, manifest, _, _ = write_fixture(root, unsafe_member=True)
            output = initialize_ignored_output(root)

            with self.assertRaisesRegex(module.AdapterError, "unsafe member path"):
                module.export_annotation_media(
                    candidates_path=manifest,
                    popsweeper_archive=pop,
                    popsweeper_sha256=sha256(pop),
                    rico_archive=rico,
                    rico_sha256=sha256(rico),
                    output_dir=output,
                    pilot_count=2,
                    seed=17,
                )

            self.assertFalse(output.exists())
            self.assertFalse((root / "escape.txt").exists())

    def test_candidate_crc_mismatch_blocks_all_output(self):
        """Catches a stale candidate row pointing at changed member content."""
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pop, rico, manifest, candidates, _ = write_fixture(root)
            candidates[0]["archive_member_crc32"] = "00000000"
            manifest.write_text(
                "".join(json.dumps(row) + "\n" for row in candidates),
                encoding="utf-8",
            )
            output = initialize_ignored_output(root)

            with self.assertRaisesRegex(module.AdapterError, "CRC32 mismatch"):
                module.export_annotation_media(
                    candidates_path=manifest,
                    popsweeper_archive=pop,
                    popsweeper_sha256=sha256(pop),
                    rico_archive=rico,
                    rico_sha256=sha256(rico),
                    output_dir=output,
                    pilot_count=2,
                    seed=17,
                )

            self.assertFalse(output.exists())

    def test_missing_exact_rico_member_blocks_all_output(self):
        """Catches an incomplete RICO join that silently drops structured evidence."""
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pop, rico, manifest, _, _ = write_fixture(root, omit_rico_png=True)
            output = initialize_ignored_output(root)

            with self.assertRaisesRegex(module.AdapterError, "missing exact RICO member"):
                module.export_annotation_media(
                    candidates_path=manifest,
                    popsweeper_archive=pop,
                    popsweeper_sha256=sha256(pop),
                    rico_archive=rico,
                    rico_sha256=sha256(rico),
                    output_dir=output,
                    pilot_count=2,
                    seed=17,
                )

            self.assertFalse(output.exists())

    def test_unignored_output_directory_is_rejected(self):
        """Catches accidental placement of third-party screenshots in publishable paths."""
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pop, rico, manifest, _, _ = write_fixture(root)
            subprocess.run(
                ["git", "init", "--quiet", str(root)],
                check=True,
                capture_output=True,
                text=True,
            )
            output = root / "publishable" / "pilot"

            with self.assertRaisesRegex(module.AdapterError, "not gitignored"):
                module.export_annotation_media(
                    candidates_path=manifest,
                    popsweeper_archive=pop,
                    popsweeper_sha256=sha256(pop),
                    rico_archive=rico,
                    rico_sha256=sha256(rico),
                    output_dir=output,
                    pilot_count=2,
                    seed=17,
                )

            self.assertFalse(output.exists())

    def test_n30_selection_preserves_source_manifest_strata(self):
        """Catches a pilot exporter that takes the first 30 sorted rows from one stratum."""
        module = load_module()
        rows = []
        available = {
            "train/ads/rico_numeric_candidate": 27,
            "train/ads/recorded_app_frame": 9,
            "train/no_ads/rico_numeric_candidate": 27,
            "train/no_ads/recorded_app_frame": 9,
            "valid/ads/rico_numeric_candidate": 9,
            "valid/ads/recorded_app_frame": 3,
            "valid/no_ads/rico_numeric_candidate": 9,
            "valid/no_ads/recorded_app_frame": 3,
            "test/ads/rico_numeric_candidate": 9,
            "test/ads/recorded_app_frame": 3,
            "test/no_ads/rico_numeric_candidate": 9,
            "test/no_ads/recorded_app_frame": 3,
        }
        for stratum, count in available.items():
            for index in range(count):
                rows.append(
                    {
                        "source_record_id": f"{stratum}:{index:03d}",
                        "sampling_stratum": stratum,
                    }
                )

        selected = module.select_pilot(rows, pilot_count=30, seed=20260901)
        counts = Counter(row["sampling_stratum"] for row in selected)

        self.assertEqual(len(selected), 30)
        self.assertEqual(counts["train/ads/rico_numeric_candidate"], 7)
        self.assertEqual(counts["train/no_ads/recorded_app_frame"], 2)
        self.assertEqual(counts["valid/ads/rico_numeric_candidate"], 2)
        self.assertEqual(counts["valid/no_ads/recorded_app_frame"], 1)
        self.assertEqual(counts["test/ads/rico_numeric_candidate"], 2)
        self.assertEqual(counts["test/no_ads/recorded_app_frame"], 1)
        self.assertEqual(
            Counter(row["sampling_stratum"].split("/")[1] for row in selected),
            {"ads": 15, "no_ads": 15},
        )


if __name__ == "__main__":
    unittest.main()
