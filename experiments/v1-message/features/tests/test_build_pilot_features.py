import hashlib
import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "build_pilot_features.py"


def init_git_repo(root: Path) -> None:
    subprocess.run(
        ["git", "init", "--quiet", str(root)],
        check=True,
        capture_output=True,
        text=True,
    )
    root.joinpath(".gitignore").write_text("private/\n", encoding="utf-8")


class BuildPilotFeaturesCliTest(unittest.TestCase):
    def test_builds_available_and_missing_rows_without_consuming_labels(self) -> None:
        """Catches label-dependent routing or public/private leakage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_git_repo(root)
            manifest = root / "pilot-manifest.jsonl"
            private_output = root / "private" / "pilot-features.private.jsonl"
            public_summary = root / "PUBLIC_FEATURE_SUMMARY.json"

            rows = [
                {
                    "pilot_item_id": "PMJ-PILOT-002",
                    "popup_present_gt": "DO_NOT_CONSUME_NEGATIVE",
                    "sampling_stratum": "DO_NOT_CONSUME_STRATUM_B",
                    "message_annotation_status": "DO_NOT_CONSUME_STATUS_B",
                    "source_record_id": "DO_NOT_CONSUME_SOURCE_ID_B",
                    "artifacts": [
                        {"archive_member": "no_ads/DO_NOT_CONSUME_PATH_B.json"}
                    ],
                },
                {
                    "pilot_item_id": "PMJ-PILOT-001",
                    "popup_present_gt": "DO_NOT_CONSUME_POSITIVE",
                    "sampling_stratum": "DO_NOT_CONSUME_STRATUM_A",
                    "message_annotation_status": "DO_NOT_CONSUME_STATUS_A",
                    "source_record_id": "DO_NOT_CONSUME_SOURCE_ID_A",
                    "artifacts": [
                        {"archive_member": "ads/DO_NOT_CONSUME_PATH_A.json"}
                    ],
                },
            ]
            manifest.write_text(
                "".join(json.dumps(row) + "\n" for row in rows),
                encoding="utf-8",
            )

            semantic_dir = root / "PMJ-PILOT-001"
            semantic_dir.mkdir()
            semantic_dir.joinpath("rico-semantic.json").write_text(
                json.dumps(
                    {
                        "ancestors": ["android.widget.FrameLayout"],
                        "class": "android.widget.TextView",
                        "bounds": [1, 2, 101, 42],
                        "clickable": False,
                        "text": "PRIVATE POPUP MESSAGE",
                        "componentLabel": "Text",
                        "resource-id": "com.example:id/private_message",
                        "children": [
                            {
                                "ancestors": [
                                    "android.widget.FrameLayout",
                                    "android.widget.TextView",
                                ],
                                "class": "android.widget.Button",
                                "bounds": [2, 44, 90, 80],
                                "clickable": True,
                                "text": "PRIVATE BUTTON LABEL",
                            },
                            {
                                "ancestors": ["android.widget.FrameLayout"],
                                "class": "android.view.View",
                                "bounds": [0, 82, 100, 100],
                                "clickable": False,
                                "componentLabel": "Text",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--manifest",
                    str(manifest),
                    "--private-output",
                    str(private_output),
                    "--public-summary",
                    str(public_summary),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            private_bytes = private_output.read_bytes()
            private_text = private_bytes.decode("utf-8")
            private_rows = [json.loads(line) for line in private_text.splitlines()]
            summary_text = public_summary.read_text(encoding="utf-8")
            summary = json.loads(summary_text)

            self.assertEqual(len(private_rows), 2)
            self.assertEqual(
                [row["identity"]["pilot_item_id"] for row in private_rows],
                ["PMJ-PILOT-001", "PMJ-PILOT-002"],
            )
            self.assertEqual(
                private_rows[0]["observations"][0]["structured_representation"]["availability"],
                "available",
            )
            self.assertEqual(
                private_rows[1]["observations"][0]["structured_representation"]["availability"],
                "missing",
            )
            self.assertEqual(len(private_rows[0]["candidates"]), 3)
            self.assertEqual(
                private_rows[0]["candidates"][0]["normalized"]["name_or_text"],
                "PRIVATE POPUP MESSAGE",
            )
            self.assertIsNone(
                private_rows[0]["candidates"][2]["normalized"]["name_or_text"]
            )
            self.assertEqual(
                set(private_rows[0]),
                {
                    "identity",
                    "observations",
                    "candidates",
                    "action_attempts",
                    "decision",
                    "metadata",
                },
            )
            self.assertEqual(private_rows[0]["action_attempts"], [])
            self.assertEqual(
                private_rows[0]["decision"]["policy"]["decision"], "no_action"
            )
            self.assertTrue(private_rows[0]["metadata"]["gold_blind"])
            self.assertFalse(private_rows[0]["metadata"]["gold_used"])
            self.assertFalse(private_rows[0]["metadata"]["scored"])
            self.assertFalse(private_rows[0]["metadata"]["paper_result_eligible"])

            for forbidden in (
                "DO_NOT_CONSUME_POSITIVE",
                "DO_NOT_CONSUME_NEGATIVE",
                "DO_NOT_CONSUME_STRATUM_A",
                "DO_NOT_CONSUME_STRATUM_B",
                "DO_NOT_CONSUME_STATUS_A",
                "DO_NOT_CONSUME_STATUS_B",
                "DO_NOT_CONSUME_SOURCE_ID_A",
                "DO_NOT_CONSUME_SOURCE_ID_B",
                "DO_NOT_CONSUME_PATH_A",
                "DO_NOT_CONSUME_PATH_B",
            ):
                self.assertNotIn(forbidden, private_text)
                self.assertNotIn(forbidden, summary_text)

            self.assertNotIn("PRIVATE POPUP MESSAGE", summary_text)
            self.assertNotIn("PRIVATE BUTTON LABEL", summary_text)
            self.assertNotIn(str(root.resolve()), summary_text)
            self.assertEqual(summary["counts"]["items"], 2)
            self.assertEqual(summary["counts"]["structured_available"], 1)
            self.assertEqual(summary["counts"]["structured_missing"], 1)
            self.assertEqual(summary["counts"]["structured_nodes"], 3)
            self.assertEqual(
                summary["hashes"]["private_bundle_sha256"],
                hashlib.sha256(private_bytes).hexdigest(),
            )
            self.assertFalse(summary["gold_used"])
            self.assertFalse(summary["scored"])
            self.assertFalse(summary["paper_result_eligible"])
            self.assertEqual(summary["action_mode"], "no_action")
            self.assertIn("popup_present_gt", summary["forbidden_fields_not_consumed"])
            self.assertIn("artifacts", summary["forbidden_fields_not_consumed"])
            self.assertIn("source_record_id", summary["forbidden_fields_not_consumed"])
            self.assertIn("archive_member", summary["forbidden_fields_not_consumed"])
            self.assertIn("source_label", summary["forbidden_fields_not_consumed"])
            self.assertEqual(stat.S_IMODE(private_output.parent.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(private_output.stat().st_mode), 0o600)

            mutated_manifest = root / "mutated-pilot-manifest.jsonl"
            mutated_manifest.write_text(
                "".join(
                    json.dumps(row) + "\n"
                    for row in [
                        {"pilot_item_id": "PMJ-PILOT-002"},
                        {
                            "pilot_item_id": "PMJ-PILOT-001",
                            "popup_present_gt": "FLIPPED",
                            "sampling_stratum": "FLIPPED",
                            "message_annotation_status": "FLIPPED",
                            "source_record_id": "FLIPPED",
                            "artifacts": [{"archive_member": "FLIPPED"}],
                        },
                    ]
                ),
                encoding="utf-8",
            )
            # Both manifests share the same media root. Rename only during this
            # second invocation so the builder sees identical semantic files.
            original_manifest = root / "original-pilot-manifest.jsonl"
            manifest.rename(original_manifest)
            mutated_manifest.rename(manifest)
            second_private = root / "private" / "second-pilot-features.private.jsonl"
            second_public = root / "second" / "PUBLIC_FEATURE_SUMMARY.json"
            second_result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--manifest",
                    str(manifest),
                    "--private-output",
                    str(second_private),
                    "--public-summary",
                    str(second_public),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(second_result.returncode, 0, second_result.stderr)
            self.assertEqual(private_bytes, second_private.read_bytes())
            self.assertEqual(public_summary.read_bytes(), second_public.read_bytes())

    def test_rejects_semantic_symlink_that_escapes_the_batch_directory(self) -> None:
        """Catches following a crafted pilot directory to external UI data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_git_repo(root)
            batch = root / "batch"
            batch.mkdir()
            manifest = batch / "pilot-manifest.jsonl"
            manifest.write_text(
                json.dumps({"pilot_item_id": "PMJ-PILOT-001"}) + "\n",
                encoding="utf-8",
            )
            external_semantic = root / "external-semantic.json"
            external_semantic.write_text(
                json.dumps(
                    {
                        "class": "android.widget.TextView",
                        "bounds": [0, 0, 10, 10],
                        "clickable": False,
                        "ancestors": [],
                        "text": "MUST NOT BE READ",
                    }
                ),
                encoding="utf-8",
            )
            item_dir = batch / "PMJ-PILOT-001"
            item_dir.mkdir()
            item_dir.joinpath("rico-semantic.json").symlink_to(external_semantic)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--manifest",
                    str(manifest),
                    "--private-output",
                    str(root / "private" / "pilot.private.jsonl"),
                    "--public-summary",
                    str(root / "public.json"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("escapes the manifest batch directory", result.stderr)

    def test_rejects_private_output_that_is_not_gitignored(self) -> None:
        """Catches writing UI text to a trackable location."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_git_repo(root)
            manifest = root / "pilot-manifest.jsonl"
            manifest.write_text(
                json.dumps({"pilot_item_id": "PMJ-PILOT-001"}) + "\n",
                encoding="utf-8",
            )
            private_output = root / "trackable" / "features.jsonl"
            public_summary = root / "PUBLIC_FEATURE_SUMMARY.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--manifest",
                    str(manifest),
                    "--private-output",
                    str(private_output),
                    "--public-summary",
                    str(public_summary),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must be gitignored", result.stderr)
            self.assertFalse(private_output.exists())
            self.assertFalse(public_summary.exists())


if __name__ == "__main__":
    unittest.main()
