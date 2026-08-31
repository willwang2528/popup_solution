from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def item(index: int) -> dict:
    pilot_id = f"PMJ-PILOT-{index:03d}"
    return {
        "identity": {
            "item_id": f"pmj.pending.{index:03d}",
            "pilot_item_id": pilot_id,
            "record_kind": "real_app",
        },
        "message_judgment": {
            "labels": {
                "popup_present_gt": True,
                "message_text_gt": "Gold message",
                "critical_facts_gt": [],
                "message_text_observability": "complete",
            }
        },
    }


def prediction(index: int, method_id: str) -> dict:
    return {
        "action_policy": "no_action",
        "confidence": 0.8,
        "critical_facts_pred": [],
        "human_gold_used": False,
        "message_text_pred": "Predicted message",
        "method_id": method_id,
        "paper_result_eligible": False,
        "pilot_item_id": f"PMJ-PILOT-{index:03d}",
        "popup_present_pred": True,
        "route_reason": "frozen_fixture",
        "scored": False,
        "status": "judged",
        "visual_called": False,
    }


def row_sha256(row: dict) -> str:
    payload = json.dumps(
        row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def semantic_row(prediction_row: dict, **overrides) -> dict:
    row = {
        "contract_version": "popup-message-output-adjudication-v1.0",
        "batch_id": "popsweeper-message-pilot-30-v1",
        "pilot_item_id": prediction_row["pilot_item_id"],
        "method_id": prediction_row["method_id"],
        "prediction_row_sha256": row_sha256(prediction_row),
        "record_status": "completed",
        "adjudicator_id_pseudonymous": "semantic-adj-1",
        "message_semantically_correct": True,
        "critical_hallucination": False,
        "decision_rationale": "Blind output review completed.",
        "evidence_rechecked_via_adapter": True,
        "resolved_at": "2026-09-01T00:00:00Z",
    }
    row.update(overrides)
    return row


class SemanticOutputAdjudicationTests(unittest.TestCase):
    def test_semantic_adjudication_is_hash_bound_and_complete_across_methods(self):
        # Break caught: mixed human/proxy VPMA or semantic labels for a different prediction.
        self.assertIsNotNone(
            importlib.util.find_spec("popup_eval.semantic_adjudication")
        )
        module = importlib.import_module("popup_eval.semantic_adjudication")
        items = [item(1)]
        structured = prediction(1, "structured-only-v1")
        proposed = prediction(1, "mg-pu-gated-union-v1")
        predictions = [structured, proposed]
        methods = ["structured-only-v1", "mg-pu-gated-union-v1"]

        with self.assertRaisesRegex(ValueError, "missing semantic adjudication"):
            module.prepare_semantic_output_annotations(
                items,
                predictions,
                [semantic_row(structured)],
                method_ids=methods,
            )
        with self.assertRaisesRegex(ValueError, "prediction_row_sha256"):
            module.prepare_semantic_output_annotations(
                items,
                predictions,
                [
                    semantic_row(structured),
                    semantic_row(proposed, prediction_row_sha256="0" * 64),
                ],
                method_ids=methods,
            )

        annotations = module.prepare_semantic_output_annotations(
            items,
            predictions,
            [semantic_row(proposed), semantic_row(structured)],
            method_ids=methods,
        )

        self.assertEqual(
            set(annotations),
            {
                ("pmj.pending.001", "structured-only-v1"),
                ("pmj.pending.001", "mg-pu-gated-union-v1"),
            },
        )
        self.assertTrue(
            annotations[("pmj.pending.001", "structured-only-v1")][
                "message_semantically_correct"
            ]
        )


if __name__ == "__main__":
    unittest.main()
