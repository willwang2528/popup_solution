from __future__ import annotations

import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "dataset-v1"
    / "annotation-pilot"
    / "scripts"
    / "calculate_agreement.py"
)
BATCH_ID = "popsweeper-message-pilot-30-v1"


def load_module():
    assert SCRIPT.is_file(), "calculate_agreement.py must be implemented"
    spec = importlib.util.spec_from_file_location("annotation_agreement", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def slot(slot_type: str, value: str, polarity: str = "affirmed") -> dict:
    return {"slot_type": slot_type, "value": value, "polarity": polarity}


def completed_record(
    item_number: int,
    role: str,
    presence: str,
    *,
    message_text: str | None = None,
    semantic_slots: list[dict] | None = None,
    message_observability: str | None = None,
) -> dict:
    if message_observability is None:
        message_observability = (
            "complete" if presence == "popup" else "not_applicable"
        )
    return {
        "protocol_version": "1.0.0",
        "batch_id": BATCH_ID,
        "pilot_item_id": f"PMJ-PILOT-{item_number:03d}",
        "annotation_order": item_number,
        "adapter_item_handle": f"adapter://popsweeper/pilot/PMJ-PILOT-{item_number:03d}",
        "annotator_role": role,
        "annotator_id_pseudonymous": f"annotator-{role.lower()}",
        "record_status": "completed",
        "presence_label": presence,
        "message_text": message_text,
        "message_observability": message_observability,
        "semantic_slots": semantic_slots or [],
        "confidence": 4,
        "evidence": {
            "adapter_viewed": True,
            "view_session_id": f"view-{role.lower()}-{item_number}",
            "region_or_node_notes": "locally inspected through adapter",
            "raw_image_copied": False,
        },
        "blindness_attestation": {
            "peer_labels_unseen": True,
            "source_class_unseen": True,
            "model_output_unseen": True,
        },
        "annotation_started_at": "2026-09-01T01:00:00Z",
        "annotation_completed_at": "2026-09-01T01:01:00Z",
        "notes": None,
    }


def paired_records() -> tuple[list[dict], list[dict]]:
    records_a = [
        completed_record(
            1,
            "A",
            "popup",
            message_text="Pay $9.99 by 5 PM",
            semantic_slots=[slot("amount", "$9.99")],
        ),
        completed_record(
            2,
            "A",
            "popup",
            message_text="Special   OFFER",
            semantic_slots=[slot("other_critical", "special offer")],
        ),
        completed_record(
            3,
            "A",
            "popup",
            message_text="Delete account",
            semantic_slots=[slot("action_choice", "delete account")],
        ),
        completed_record(4, "A", "popup", message_text="Popup"),
        completed_record(5, "A", "no_popup"),
        completed_record(
            6,
            "A",
            "uncertain",
            message_observability="not_observable",
        ),
    ]
    records_b = [
        completed_record(
            1,
            "B",
            "popup",
            message_text="Pay $9.99 by 5 PM",
            semantic_slots=[slot("amount", "$9.99")],
        ),
        completed_record(
            2,
            "B",
            "popup",
            message_text="special offer",
            semantic_slots=[slot("other_critical", "SPECIAL OFFER")],
        ),
        completed_record(
            3,
            "B",
            "popup",
            message_text="Remove account",
            semantic_slots=[
                slot("action_choice", "delete account"),
                slot("consequence", "data removed"),
            ],
        ),
        completed_record(4, "B", "no_popup"),
        completed_record(5, "B", "no_popup"),
        completed_record(
            6,
            "B",
            "uncertain",
            message_observability="not_observable",
        ),
    ]
    return records_a, records_b


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


class AgreementUnitTests(unittest.TestCase):
    def test_normalization_preserves_critical_content(self):
        module = load_module()
        normalized = module.normalize_message("  ＤＯ NOT  pay  ￥９．９９  ")
        self.assertEqual(normalized, "do not pay ¥9.99")

    def test_agreement_metrics_are_recomputed_from_paired_records(self):
        module = load_module()
        records_a, records_b = paired_records()

        report = module.compute_agreement(records_a, records_b)

        self.assertEqual(report["paired_items"], 6)
        self.assertTrue(
            math.isclose(report["presence"]["observed_agreement"], 5 / 6)
        )
        self.assertTrue(
            math.isclose(report["presence"]["expected_agreement"], 5 / 12)
        )
        self.assertTrue(
            math.isclose(report["presence"]["cohen_kappa"], 5 / 7)
        )
        self.assertEqual(report["message"]["comparable_items"], 3)
        self.assertEqual(report["message"]["exact_agreement_count"], 1)
        self.assertTrue(
            math.isclose(report["message"]["exact_agreement_rate"], 1 / 3)
        )
        self.assertEqual(report["message"]["normalized_agreement_count"], 2)
        self.assertTrue(
            math.isclose(report["message"]["normalized_agreement_rate"], 2 / 3)
        )
        self.assertEqual(report["semantic_slots"]["exact_set_count"], 2)
        self.assertTrue(
            math.isclose(
                report["semantic_slots"]["exact_set_agreement_rate"], 2 / 3
            )
        )
        self.assertTrue(
            math.isclose(report["semantic_slots"]["mean_jaccard"], 5 / 6)
        )

    def test_completed_records_reject_blank_gold_and_protocol_leakage(self):
        module = load_module()
        valid = completed_record(1, "A", "no_popup")
        module.validate_completed_annotation(valid, expected_role="A")

        mutations = []
        blank = dict(valid)
        blank["record_status"] = "blank"
        mutations.append(blank)
        message_on_negative = dict(valid)
        message_on_negative["message_text"] = "invented"
        mutations.append(message_on_negative)
        copied_image = json.loads(json.dumps(valid))
        copied_image["evidence"]["raw_image_copied"] = True
        mutations.append(copied_image)
        unblinded = json.loads(json.dumps(valid))
        unblinded["blindness_attestation"]["source_class_unseen"] = False
        mutations.append(unblinded)

        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with self.assertRaises(module.ProtocolError):
                    module.validate_completed_annotation(
                        mutation, expected_role="A"
                    )

    def test_pairing_rejects_mismatched_item_sets(self):
        module = load_module()
        records_a, records_b = paired_records()
        with self.assertRaisesRegex(module.ProtocolError, "item sets differ"):
            module.compute_agreement(records_a, records_b[:-1])


class AgreementCliTests(unittest.TestCase):
    def test_cli_writes_report_and_adjudication_input_without_final_gold(self):
        self.assertTrue(SCRIPT.is_file(), "agreement CLI must exist")
        records_a, records_b = paired_records()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            annotations_a = root / "a.jsonl"
            annotations_b = root / "b.jsonl"
            report_path = root / "agreement.json"
            adjudication_path = root / "adjudication-input.jsonl"
            write_jsonl(annotations_a, records_a)
            write_jsonl(annotations_b, records_b)

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--annotations-a",
                    str(annotations_a),
                    "--annotations-b",
                    str(annotations_b),
                    "--report",
                    str(report_path),
                    "--adjudication-input",
                    str(adjudication_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            disagreements = [
                json.loads(line)
                for line in adjudication_path.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(report["paired_items"], 6)
        self.assertEqual(len(disagreements), 6)
        by_id = {row["pilot_item_id"]: row for row in disagreements}
        self.assertEqual(by_id["PMJ-PILOT-001"]["disagreement_reasons"], [])
        self.assertEqual(
            by_id["PMJ-PILOT-002"]["disagreement_reasons"],
            ["message_exact"],
        )
        self.assertEqual(
            by_id["PMJ-PILOT-003"]["disagreement_reasons"],
            ["message_exact", "message_normalized", "semantic_slots"],
        )
        self.assertEqual(
            by_id["PMJ-PILOT-004"]["disagreement_reasons"],
            ["presence"],
        )
        self.assertEqual(by_id["PMJ-PILOT-005"]["disagreement_reasons"], [])
        self.assertEqual(by_id["PMJ-PILOT-006"]["disagreement_reasons"], [])
        for row in disagreements:
            self.assertEqual(row["record_status"], "ready")
            self.assertEqual(row["adjudication_status"], "pending")
            self.assertEqual(row["annotation_a"]["record_status"], "completed")
            self.assertEqual(row["annotation_b"]["record_status"], "completed")
            self.assertNotIn("presence_label_final", row)
            self.assertNotIn("message_text_final", row)


if __name__ == "__main__":
    unittest.main()
