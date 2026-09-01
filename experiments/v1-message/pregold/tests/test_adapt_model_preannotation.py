from __future__ import annotations

import json
from pathlib import Path
import subprocess
import stat
import sys
import tempfile
import unittest


PREGOLD_DIR = Path(__file__).resolve().parents[1]
SCRIPT = PREGOLD_DIR / "adapt_model_preannotation.py"


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def model_row(item_id: str, presence: str, message: str | None) -> dict:
    return {
        "adapter_item_handle": f"private://{item_id}",
        "pilot_item_id": item_id,
        "annotator_type": "AI model",
        "not_human_gold": True,
        "metric_eligible": False,
        "not_metric_eligible": True,
        "record_status": "completed",
        "presence_label": presence,
        "message_text": message,
        "semantic_slots": (
            [{"slot_type": "other_critical", "value": "retry later", "polarity": "affirmed"}]
            if presence == "popup" and message
            else []
        ),
        "message_observability": "complete" if message else "not_applicable",
        "ambiguity": {"level": "low", "notes": ""},
        "blocking_label": None,
        "annotator_id_pseudonymous": "model-b",
        "annotation_order": 1,
        "blindness_attestation": {
            "model_output_unseen": True,
            "peer_labels_unseen": True,
            "source_class_unseen": True,
        },
        "evidence": {
            "adapter_viewed": True,
            "raw_image_copied": False,
            "region_or_node_notes": "private",
            "view_session_id": "private-session",
        },
        "notes": "private",
    }


class AdaptModelPreannotationCliTest(unittest.TestCase):
    def run_cli(
        self, root: Path, rows: list[dict]
    ) -> tuple[subprocess.CompletedProcess[str], Path]:
        source = root / "model-preannotation.jsonl"
        output = root / "private" / "visual-candidate.private.jsonl"
        write_jsonl(source, rows)
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--input",
                str(source),
                "--private-output",
                str(output),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return result, output

    def test_projects_only_ai_non_gold_metric_ineligible_records(self) -> None:
        """Catches label-shaped metadata leaking past the isolated adapter."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = [
                model_row("PMJ-PILOT-001", "popup", "Try again later"),
                model_row("PMJ-PILOT-002", "no_popup", None),
                model_row("PMJ-PILOT-003", "popup", None),
            ]

            result, output = self.run_cli(root, rows)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(stat.S_IMODE(output.parent.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            adapted = [json.loads(line) for line in output.read_text().splitlines()]
            self.assertEqual([row["status"] for row in adapted], ["judged", "judged", "abstain"])
            self.assertTrue(adapted[0]["popup_present_pred"])
            self.assertFalse(adapted[1]["popup_present_pred"])
            self.assertIsNone(adapted[2]["popup_present_pred"])
            for row in adapted:
                self.assertEqual(row["evidence_kind"], "model_workflow_visual_candidate")
                self.assertFalse(row["fixed_threshold_heuristic_adaptation"])
                self.assertFalse(
                    row["repeat_execution_byte_identical_on_fixed_host"]
                )
                self.assertEqual(
                    row["cross_os_or_device_model_identity_reproducible"],
                    "not_verified",
                )
                self.assertFalse(row["human_gold_used"])
                self.assertFalse(row["scored"])
                self.assertFalse(row["paper_result_eligible"])
                self.assertNotIn("presence_label", row)
                self.assertNotIn("metric_eligible", row)
                self.assertNotIn("annotator_id_pseudonymous", row)

    def test_rejects_human_metric_eligible_or_adjudicated_inputs(self) -> None:
        """Catches unsafe promotion of human/gold/adjudicated records to method evidence."""
        unsafe_mutations = {
            "human": {"annotator_type": "human researcher"},
            "metric": {"metric_eligible": True},
            "adjudicated": {"adjudication_status": "resolved"},
        }
        for name, mutation in unsafe_mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                row = model_row("PMJ-PILOT-001", "popup", "Hello")
                row.update(mutation)

                result, output = self.run_cli(root, [row])

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("refuses", result.stderr.lower())
                self.assertFalse(output.exists())

    def test_rejects_false_or_incomplete_blindness_attestation(self) -> None:
        """Catches a model prediction that saw source classes or peer outputs."""
        unsafe_attestations = [
            {
                "model_output_unseen": True,
                "peer_labels_unseen": False,
                "source_class_unseen": True,
            },
            {
                "model_output_unseen": True,
                "peer_labels_unseen": True,
            },
        ]
        for attestation in unsafe_attestations:
            with self.subTest(attestation=attestation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                row = model_row("PMJ-PILOT-001", "popup", "Hello")
                row["blindness_attestation"] = attestation

                result, output = self.run_cli(root, [row])

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("blindness_attestation", result.stderr)
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
