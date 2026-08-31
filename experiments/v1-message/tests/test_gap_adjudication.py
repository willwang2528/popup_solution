from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def canonical_row(row: dict) -> bytes:
    return json.dumps(
        row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def batch_sha256(rows: list[dict]) -> str:
    payload = b"".join(
        canonical_row(row) + b"\n"
        for row in sorted(rows, key=lambda row: row["pilot_item_id"])
    )
    return hashlib.sha256(payload).hexdigest()


def structured_batch_sha256(rows: list[dict]) -> str:
    payload = b"".join(
        canonical_row(row) + b"\n"
        for row in sorted(rows, key=lambda row: row["identity"]["pilot_item_id"])
    )
    return hashlib.sha256(payload).hexdigest()


def message_gold_row(index: int, *, popup: bool = True) -> dict:
    return {
        "protocol_version": "1.0.0",
        "batch_id": "popsweeper-message-pilot-30-v1",
        "pilot_item_id": f"PMJ-PILOT-{index:03d}",
        "record_status": "completed",
        "adjudicator_id_pseudonymous": "message-adj-1",
        "adjudication_status": "resolved",
        "presence_label_final": "popup" if popup else "no_popup",
        "message_text_final": "Private visual message" if popup else None,
        "message_observability_final": "complete" if popup else "not_applicable",
        "semantic_slots_final": (
            [
                {
                    "slot_type": "duration_deadline",
                    "value": "deadline",
                    "polarity": "affirmed",
                }
            ]
            if popup
            else []
        ),
        "decision_rationale": "Rechecked frozen screenshot evidence.",
        "evidence_rechecked_via_adapter": True,
        "resolved_at": "2026-09-01T00:00:00Z",
    }


def gold_item(index: int, *, popup: bool = True) -> dict:
    pilot_id = f"PMJ-PILOT-{index:03d}"
    return {
        "identity": {
            "item_id": f"pmj.pending.{index:03d}",
            "pilot_item_id": pilot_id,
        },
        "message_judgment": {
            "labels": {
                "popup_present_gt": popup,
                "message_text_gt": "Private visual message" if popup else None,
                "critical_facts_gt": ["deadline"] if popup else [],
                "message_text_observability": "complete" if popup else "not_applicable",
            },
            "gap_ground_truth": {
                "status": "pending_audit",
                "structured_evidence_available": None,
                "structured_message_text_gt": None,
                "structured_message_complete_gt": None,
                "gap_reasons_gt": [],
                "critical_facts_missing_from_structure_gt": [],
                "host_text_contamination_gt": None,
                "tree_screenshot_synchronized_gt": None,
                "auditor_blind_to_method_outputs": None,
                "message_gold_batch_sha256": None,
                "structured_bundle_sha256": None,
                "gap_audit_batch_sha256": None,
                "evidence_uris": [],
            },
        },
        "adjudication_provenance": {
            "adjudication_status": "resolved",
            "adjudication_batch_sha256": None,
        },
    }


def bind_items_to_message_gold(items: list[dict], rows: list[dict]) -> str:
    digest = batch_sha256(rows)
    for item in items:
        item["adjudication_provenance"]["adjudication_batch_sha256"] = digest
    return digest


def structured_row(index: int, *, available: bool = True) -> dict:
    pilot_id = f"PMJ-PILOT-{index:03d}"
    candidates = (
        [
            {
                "candidate_id": f"{pilot_id}-structured-0000",
                "source_channel": "structured",
                "normalized": {
                    "name_or_text": "Private structured fragment",
                    "value_or_hint": None,
                    "visible": True,
                },
                "features": {"node_index": 0, "depth": 0, "gap_reasons": []},
            }
        ]
        if available
        else []
    )
    return {
        "identity": {
            "item_id": pilot_id,
            "pilot_item_id": pilot_id,
            "record_kind": "unscored_pregold_input",
        },
        "observations": [
            {
                "observation_id": f"{pilot_id}-pre-action-structured",
                "phase": "pre_action",
                "structured_representation": {
                    "availability": "available" if available else "missing",
                    "representation_kind": "rico-semantic-json",
                    "node_count": len(candidates),
                    "artifact_sha256": "e" * 64 if available else None,
                },
            }
        ],
        "candidates": candidates,
        "action_attempts": [],
        "decision": {"policy": {"decision": "no_action"}},
        "metadata": {
            "contract_version": "pmj-pilot-structured-features-v1.0",
            "gold_blind": True,
            "gold_used": False,
            "scored": False,
            "paper_result_eligible": False,
            "action_mode": "no_action",
        },
    }


def independent_audit_row(
    index: int,
    *,
    slot: str,
    auditor: str,
    message_hash: str,
    structured_hash: str,
    popup: bool = True,
    complete: bool = False,
    available: bool = True,
) -> dict:
    pilot_id = f"PMJ-PILOT-{index:03d}"
    not_applicable = not popup
    return {
        "contract_version": "popup-structure-visual-gap-audit-record-v1.0",
        "batch_id": "popsweeper-message-pilot-30-gap-v1",
        "pilot_item_id": pilot_id,
        "record_status": "completed",
        "auditor_slot": slot,
        "auditor_id_pseudonymous": auditor,
        "human_auditor_attestation": True,
        "independent_of_peer_attestation": True,
        "auditor_blind_to_method_outputs": True,
        "message_gold_batch_sha256": message_hash,
        "structured_bundle_sha256": structured_hash,
        "audit_status": "not_applicable" if not_applicable else "adjudicated",
        "structured_evidence_available": None if not_applicable else available,
        "structured_candidate_ids": (
            []
            if not_applicable or not available
            else [f"{pilot_id}-structured-0000"]
        ),
        "structured_message_text": (
            None if not_applicable or not available else "Private structured fragment"
        ),
        "structured_message_complete": None if not_applicable else complete,
        "gap_reasons": (
            []
            if not_applicable or complete
            else ["missing" if not available else "merged"]
        ),
        "critical_facts_missing_from_structure": (
            [] if not_applicable or complete else ["deadline"]
        ),
        "host_text_contamination": None if not_applicable else False,
        "tree_screenshot_synchronized": None if not_applicable else True,
        "decision_rationale": (
            "Compared frozen structure with finalized screenshot message."
        ),
        "evidence_uris": [
            "evidence://private/structure",
            "evidence://private/screenshot",
        ],
        "completed_at": "2026-09-01T00:00:00Z",
    }


def final_gap_row(
    index: int,
    *,
    audit_rows: list[dict],
    message_hash: str,
    structured_hash: str,
    popup: bool = True,
    complete: bool = False,
    available: bool = True,
) -> dict:
    not_applicable = not popup
    return {
        "contract_version": "popup-structure-visual-gap-adjudication-v1.0",
        "batch_id": "popsweeper-message-pilot-30-gap-v1",
        "pilot_item_id": f"PMJ-PILOT-{index:03d}",
        "record_status": "completed",
        "adjudicator_id_pseudonymous": "gap-adj-1",
        "independent_audit_record_sha256": [
            hashlib.sha256(canonical_row(row)).hexdigest() for row in audit_rows
        ],
        "audit_status": "not_applicable" if not_applicable else "adjudicated",
        "structured_evidence_available": None if not_applicable else available,
        "structured_message_text_final": (
            None if not_applicable or not available else "Private structured fragment"
        ),
        "structured_message_complete_final": None if not_applicable else complete,
        "gap_reasons_final": (
            []
            if not_applicable or complete
            else ["missing" if not available else "merged"]
        ),
        "critical_facts_missing_from_structure_final": (
            [] if not_applicable or complete else ["deadline"]
        ),
        "host_text_contamination_final": None if not_applicable else False,
        "tree_screenshot_synchronized_final": None if not_applicable else True,
        "decision_rationale": "Adjudicated two independent gap records.",
        "evidence_uris": [
            "evidence://private/structure",
            "evidence://private/screenshot",
        ],
        "auditor_blind_to_method_outputs": True,
        "message_gold_batch_sha256": message_hash,
        "structured_bundle_sha256": structured_hash,
        "adjudicated_at": "2026-09-01T00:00:00Z",
    }


def valid_inputs(*, second_popup: bool = True) -> dict:
    items = [gold_item(1), gold_item(2, popup=second_popup)]
    message_rows = [message_gold_row(1), message_gold_row(2, popup=second_popup)]
    message_hash = bind_items_to_message_gold(items, message_rows)
    structured_rows = [structured_row(1), structured_row(2)]
    structured_hash = structured_batch_sha256(structured_rows)
    audit_rows: list[dict] = []
    final_rows: list[dict] = []
    for index, popup in ((1, True), (2, second_popup)):
        pair = [
            independent_audit_row(
                index,
                slot="A",
                auditor="gap-auditor-a",
                message_hash=message_hash,
                structured_hash=structured_hash,
                popup=popup,
                complete=popup and index == 2,
            ),
            independent_audit_row(
                index,
                slot="B",
                auditor="gap-auditor-b",
                message_hash=message_hash,
                structured_hash=structured_hash,
                popup=popup,
                complete=popup and index == 2,
            ),
        ]
        audit_rows.extend(pair)
        final_rows.append(
            final_gap_row(
                index,
                audit_rows=pair,
                message_hash=message_hash,
                structured_hash=structured_hash,
                popup=popup,
                complete=popup and index == 2,
            )
        )
    return {
        "items": items,
        "message_gold_rows": message_rows,
        "structured_feature_rows": structured_rows,
        "expected_structured_bundle_sha256": structured_hash,
        "independent_audit_records": audit_rows,
        "adjudication_rows": final_rows,
    }


class StructureVisualGapAdjudicationTests(unittest.TestCase):
    def test_finalizer_binds_real_inputs_and_updates_union_items(self):
        # Break caught: screenshot gold is mistaken for evidence of a structure exposure gap.
        from popup_eval.gap_adjudication import finalize_structure_visual_gap_audit

        inputs = valid_inputs()
        first_items, first_summary = finalize_structure_visual_gap_audit(**inputs)
        reversed_inputs = {
            key: list(reversed(value)) if isinstance(value, list) else value
            for key, value in inputs.items()
        }
        second_items, second_summary = finalize_structure_visual_gap_audit(
            **reversed_inputs
        )

        self.assertEqual(first_summary, second_summary)
        self.assertEqual(first_summary["status"], "finalized_structure_visual_gap_audit")
        self.assertEqual(first_summary["item_count"], 2)
        self.assertEqual(first_summary["adjudicated_count"], 2)
        self.assertEqual(first_summary["gap_present_count"], 1)
        self.assertEqual(len(first_summary["gap_audit_batch_sha256"]), 64)
        self.assertEqual(len(first_summary["independent_audit_batch_sha256"]), 2)
        self.assertFalse(first_summary["scored"])
        self.assertFalse(first_summary["paper_result_eligible"])
        summary_text = json.dumps(first_summary, sort_keys=True)
        self.assertNotIn("PMJ-PILOT", summary_text)
        self.assertNotIn("Private structured fragment", summary_text)
        self.assertNotIn("gap-adj-1", summary_text)

        updated = {item["identity"]["pilot_item_id"]: item for item in first_items}
        gap = updated["PMJ-PILOT-001"]["message_judgment"]["gap_ground_truth"]
        self.assertEqual(gap["status"], "adjudicated")
        self.assertFalse(gap["structured_message_complete_gt"])
        self.assertEqual(gap["gap_reasons_gt"], ["merged"])
        self.assertEqual(gap["critical_facts_missing_from_structure_gt"], ["deadline"])
        self.assertEqual(
            gap["structured_bundle_sha256"],
            inputs["expected_structured_bundle_sha256"],
        )

        injected = deepcopy(inputs)
        injected["adjudication_rows"][0]["method_id"] = "mg-pu-gated-union-v1"
        with self.assertRaisesRegex(ValueError, "keys"):
            finalize_structure_visual_gap_audit(**injected)

    def test_finalizer_rejects_unbound_hashes_bundle_drift_and_nonindependence(self):
        from popup_eval.gap_adjudication import finalize_structure_visual_gap_audit

        inputs = valid_inputs()
        forged = deepcopy(inputs)
        forged["adjudication_rows"][0]["independent_audit_record_sha256"] = [
            "b" * 64,
            "c" * 64,
        ]
        with self.assertRaisesRegex(ValueError, "independent audit hash"):
            finalize_structure_visual_gap_audit(**forged)

        changed_audit = deepcopy(inputs)
        changed_audit["independent_audit_records"][0]["decision_rationale"] += " changed"
        with self.assertRaisesRegex(ValueError, "independent audit hash"):
            finalize_structure_visual_gap_audit(**changed_audit)

        changed_bundle = deepcopy(inputs)
        changed_bundle["structured_feature_rows"][0]["candidates"][0]["normalized"][
            "name_or_text"
        ] = "tampered"
        with self.assertRaisesRegex(ValueError, "structured bundle commitment"):
            finalize_structure_visual_gap_audit(**changed_bundle)

        same_auditor = deepcopy(inputs)
        for record in same_auditor["independent_audit_records"]:
            record["auditor_id_pseudonymous"] = "same-person"
        with self.assertRaisesRegex(ValueError, "distinct human auditors"):
            finalize_structure_visual_gap_audit(**same_auditor)

    def test_finalizer_rejects_bad_status_text_candidates_and_message_gold(self):
        from popup_eval.gap_adjudication import finalize_structure_visual_gap_audit

        inputs = valid_inputs()
        bad_status = deepcopy(inputs)
        row = bad_status["adjudication_rows"][0]
        row.update(
            {
                "audit_status": "not_applicable",
                "structured_evidence_available": None,
                "structured_message_text_final": None,
                "structured_message_complete_final": None,
                "gap_reasons_final": [],
                "critical_facts_missing_from_structure_final": [],
                "host_text_contamination_final": None,
                "tree_screenshot_synchronized_final": None,
            }
        )
        with self.assertRaisesRegex(ValueError, "not_applicable.*no-popup"):
            finalize_structure_visual_gap_audit(**bad_status)

        no_text = deepcopy(inputs)
        no_text["adjudication_rows"][1]["structured_message_text_final"] = None
        with self.assertRaisesRegex(ValueError, "complete.*text"):
            finalize_structure_visual_gap_audit(**no_text)

        bad_candidate = deepcopy(inputs)
        bad_candidate["independent_audit_records"][0]["structured_candidate_ids"] = [
            "PMJ-PILOT-002-structured-0000"
        ]
        with self.assertRaisesRegex(ValueError, "candidate"):
            finalize_structure_visual_gap_audit(**bad_candidate)

        bad_gold = deepcopy(inputs)
        bad_gold["message_gold_rows"][0]["message_text_final"] = "changed gold"
        with self.assertRaisesRegex(ValueError, "message gold"):
            finalize_structure_visual_gap_audit(**bad_gold)

        uncertain_gold = deepcopy(inputs)
        uncertain_gold["message_gold_rows"][0]["presence_label_final"] = "uncertain"
        with self.assertRaisesRegex(ValueError, "resolved popup/no-popup"):
            finalize_structure_visual_gap_audit(**uncertain_gold)

    def test_no_popup_requires_and_accepts_not_applicable(self):
        from popup_eval.gap_adjudication import finalize_structure_visual_gap_audit

        inputs = valid_inputs(second_popup=False)
        _, summary = finalize_structure_visual_gap_audit(**inputs)
        self.assertEqual(summary["not_applicable_count"], 1)


if __name__ == "__main__":
    unittest.main()
