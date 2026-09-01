from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def item_set_sha256(pilot_ids: list[str]) -> str:
    return hashlib.sha256(
        json.dumps(sorted(pilot_ids), separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def image_manifest_sha256(image_map: dict[str, str]) -> str:
    return hashlib.sha256(
        json.dumps(image_map, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def protocol(pilot_ids: list[str]) -> dict:
    frozen_image_map = {
        pilot_id: f"{int(pilot_id.rsplit('-', 1)[1]):x}" * 64
        for pilot_id in pilot_ids
    }
    return {
        "contract_version": "popup-visual-evidence-freeze-v1.0",
        "status": "ready_for_visual_bank_freeze",
        "scope": "popup_message_judgment_v1",
        "item_set_sha256": item_set_sha256(pilot_ids),
        "input_image_manifest_sha256": image_manifest_sha256(frozen_image_map),
        "frozen_before_human_gold": True,
        "action_policy": "no_action",
        "gold_blind_attestation": {
            "human_gold_used": False,
            "source_sampling_label_used": False,
            "folder_label_used": False,
            "adjudication_used": False,
            "post_action_evidence_used": False,
        },
        "presence_policy": {
            "policy_id": "frozen-popup-detector-v1",
            "mode": "frozen_detector",
            "input_channels": ["screenshot"],
            "implementation_sha256": "1" * 64,
            "model_or_rule_version": "detector-r1",
            "decision_threshold": 0.7,
            "abstain_band": [0.4, 0.7],
            "missing_evidence_action": "abstain",
            "formal_ready": True,
        },
        "roi_policy": {
            "policy_id": "predicted-popup-bbox-v1",
            "roi_kind": "predicted_popup_bbox",
            "coordinate_space": "normalized_xyxy",
            "screenshot_size_required": True,
            "detector_checkpoint_sha256": "2" * 64,
            "threshold": 0.7,
            "nms_threshold": 0.5,
            "multi_box_rule": "highest_score",
            "expansion_fraction": 0.02,
            "clipping_rule": "clip_to_image",
            "close_button_bbox_is_popup_roi": False,
            "invalid_or_missing_roi_action": "abstain",
            "formal_ready": True,
        },
        "visual_engine": {
            "provider": "local",
            "model": "fixture-vision-model",
            "revision": "r1",
            "checkpoint_sha256": "3" * 64,
            "license": "fixture-only",
            "api_version": "none",
            "preprocessing_sha256": "4" * 64,
            "prompt_template_sha256": "5" * 64,
            "config_sha256": "6" * 64,
            "image_resolution": [1080, 1920],
            "temperature": 0.0,
            "top_p": 1.0,
            "seed": 17,
            "max_tokens": 256,
            "timeout_seconds": 30,
            "max_retries": 0,
            "environment_sha256": "7" * 64,
            "repeat_execution_byte_identical_on_fixed_host": True,
            "cross_os_or_device_model_identity_reproducible": "not_verified",
            "formal_ready": True,
        },
        "budget": {
            "unit": "per_item",
            "per_item_max_calls": 1,
            "image_resolution": [1080, 1920],
            "input_token_cap": 4096,
            "output_token_cap": 256,
            "latency_cap_ms": 30000,
            "price_snapshot_version": "fixture-no-cost",
            "shared_visual_bank_sha256": None,
            "formal_ready": True,
        },
        "scored": False,
        "paper_result_eligible": False,
        "claims": {
            "empirical_performance": False,
            "method_superiority": False,
            "user_experience_improvement": False,
            "recovery_or_dismissal": False,
        },
    }


def visual_row(index: int, *, popup: bool = True) -> dict:
    return {
        "contract_version": "popup-visual-evidence-freeze-v1.0",
        "pilot_item_id": f"PMJ-PILOT-{index:03d}",
        "input_image_sha256": f"{index:x}" * 64,
        "presence_status": "judged",
        "popup_present_pred": popup,
        "presence_confidence": 0.9,
        "presence_basis": "frozen-popup-detector-v1",
        "roi_kind": "predicted_popup_bbox" if popup else "unavailable",
        "roi_normalized_xyxy": [0.1, 0.2, 0.9, 0.8] if popup else None,
        "roi_source": "predicted-popup-bbox-v1" if popup else None,
        "roi_confidence": 0.9 if popup else None,
        "model_config_sha256": "6" * 64,
        "request_sha256": "8" * 64,
        "response_sha256": "9" * 64,
        "message_text_pred": "Private popup message" if popup else None,
        "critical_facts_pred": ["private fact"] if popup else [],
        "latency_ms": 120,
        "input_tokens": 100,
        "output_tokens": 20,
        "cost": 0.0,
        "status": "judged",
        "block_reason": None,
        "human_gold_used": False,
        "source_sampling_label_used": False,
        "folder_label_used": False,
        "adjudication_used": False,
        "post_action_evidence_used": False,
        "scored": False,
        "paper_result_eligible": False,
    }


class VisualEvidenceFreezeTests(unittest.TestCase):
    @staticmethod
    def image_map(rows: list[dict]) -> dict[str, str]:
        return {row["pilot_item_id"]: row["input_image_sha256"] for row in rows}

    def test_visual_bank_is_exact_gold_blind_config_bound_and_private_by_summary(self):
        # Break caught: partial or gold-aware visual outputs enter B1/C1/MG-PU comparison.
        from popup_eval.visual_freeze import finalize_visual_evidence_bank

        pilot_ids = ["PMJ-PILOT-001", "PMJ-PILOT-002"]
        rows = [visual_row(1), visual_row(2, popup=False)]
        image_map = self.image_map(rows)
        first = finalize_visual_evidence_bank(protocol(pilot_ids), image_map, rows)
        second = finalize_visual_evidence_bank(
            protocol(pilot_ids), dict(reversed(list(image_map.items()))), list(reversed(rows))
        )

        self.assertEqual(first, second)
        self.assertEqual(first["status"], "frozen_private_visual_evidence_bank")
        self.assertEqual(first["item_count"], 2)
        self.assertEqual(first["judged_count"], 2)
        self.assertEqual(first["abstain_count"], 0)
        self.assertEqual(first["popup_roi_count"], 1)
        self.assertEqual(len(first["visual_bank_sha256"]), 64)
        self.assertEqual(
            first["input_image_manifest_sha256"],
            protocol(pilot_ids)["input_image_manifest_sha256"],
        )
        self.assertFalse(first["scored"])
        self.assertFalse(first["paper_result_eligible"])
        self.assertEqual(
            first["claims"],
            {
                "empirical_performance": False,
                "method_superiority": False,
                "user_experience_improvement": False,
                "recovery_or_dismissal": False,
            },
        )
        public_text = json.dumps(first, sort_keys=True)
        self.assertNotIn("PMJ-PILOT", public_text)
        self.assertNotIn("Private popup message", public_text)
        self.assertNotIn("private fact", public_text)

        invalid_cases = []
        invalid_cases.append((image_map, [rows[0]], "missing"))
        invalid_cases.append((image_map, [rows[0], rows[0]], "duplicate"))
        invalid_cases.append(
            (image_map, [rows[0], visual_row(3)], "unknown")
        )
        leaked = deepcopy(rows)
        leaked[0]["human_gold_used"] = True
        invalid_cases.append((image_map, leaked, "gold-blind"))
        drifted = deepcopy(rows)
        drifted[0]["model_config_sha256"] = "a" * 64
        invalid_cases.append((image_map, drifted, "config"))

        for expected_ids, candidate_rows, message in invalid_cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    finalize_visual_evidence_bank(
                        protocol(pilot_ids), expected_ids, candidate_rows
                    )

    def test_positive_judgment_requires_the_predeclared_popup_roi(self):
        # Break caught: full-screen OCR or a close-button box is relabeled as popup ROI.
        from popup_eval.visual_freeze import finalize_visual_evidence_bank

        pilot_ids = ["PMJ-PILOT-001", "PMJ-PILOT-002"]
        rows = [visual_row(1), visual_row(2, popup=False)]
        full_screen = deepcopy(rows)
        full_screen[0].update(
            {
                "roi_kind": "full_screen",
                "roi_normalized_xyxy": [0.0, 0.0, 1.0, 1.0],
                "roi_source": "whole_screenshot",
            }
        )
        missing = deepcopy(rows)
        missing[0].update(
            {
                "roi_kind": "unavailable",
                "roi_normalized_xyxy": None,
                "roi_source": None,
                "roi_confidence": None,
            }
        )

        for candidate_rows in (full_screen, missing):
            with self.subTest(kind=candidate_rows[0]["roi_kind"]):
                with self.assertRaisesRegex(ValueError, "popup ROI"):
                    finalize_visual_evidence_bank(
                        protocol(pilot_ids), self.image_map(rows), candidate_rows
                    )

    def test_presence_mode_none_cannot_emit_a_judgment(self):
        # Break caught: an unassigned presence policy is paired with a dummy hash
        # and silently promoted from the blocked protocol to a judged baseline.
        from popup_eval.visual_freeze import finalize_visual_evidence_bank

        pilot_ids = ["PMJ-PILOT-001"]
        blocked_protocol = protocol(pilot_ids)
        blocked_protocol["presence_policy"]["mode"] = "none"

        with self.assertRaisesRegex(ValueError, "presence mode none"):
            finalize_visual_evidence_bank(
                blocked_protocol, self.image_map([visual_row(1)]), [visual_row(1)]
            )

    def test_visual_bank_rejects_blocked_protocol_image_drift_and_missing_call_hashes(self):
        # Break caught: syntactically valid placeholder hashes bypass the public
        # blocked state or a row is joined to a different screenshot.
        from popup_eval.visual_freeze import finalize_visual_evidence_bank

        pilot_ids = ["PMJ-PILOT-001"]
        rows = [visual_row(1)]
        image_map = self.image_map(rows)

        blocked = protocol(pilot_ids)
        blocked["status"] = "blocked_missing_reproducible_presence_roi_visual_bank"
        blocked["presence_policy"]["formal_ready"] = False
        with self.assertRaisesRegex(ValueError, "ready"):
            finalize_visual_evidence_bank(blocked, image_map, rows)

        wrong_image_map = dict(image_map)
        wrong_image_map["PMJ-PILOT-001"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "input image hash"):
            finalize_visual_evidence_bank(
                protocol(pilot_ids), wrong_image_map, rows
            )

        drifted_rows = deepcopy(rows)
        drifted_rows[0]["input_image_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "image hash manifest"):
            finalize_visual_evidence_bank(
                protocol(pilot_ids), wrong_image_map, drifted_rows
            )

        missing_response = deepcopy(rows)
        missing_response[0]["response_sha256"] = None
        with self.assertRaisesRegex(ValueError, "response_sha256"):
            finalize_visual_evidence_bank(
                protocol(pilot_ids), image_map, missing_response
            )

        wrong_basis = deepcopy(rows)
        wrong_basis[0]["presence_basis"] = "another-detector"
        with self.assertRaisesRegex(ValueError, "presence policy"):
            finalize_visual_evidence_bank(
                protocol(pilot_ids), image_map, wrong_basis
            )


if __name__ == "__main__":
    unittest.main()
