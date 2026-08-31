"""Fail-closed validation for a private, pre-gold visual evidence bank."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from typing import Any


CONTRACT_VERSION = "popup-visual-evidence-freeze-v1.0"
ROW_KEYS = {
    "contract_version",
    "pilot_item_id",
    "input_image_sha256",
    "presence_status",
    "popup_present_pred",
    "presence_confidence",
    "presence_basis",
    "roi_kind",
    "roi_normalized_xyxy",
    "roi_source",
    "roi_confidence",
    "model_config_sha256",
    "request_sha256",
    "response_sha256",
    "message_text_pred",
    "critical_facts_pred",
    "latency_ms",
    "input_tokens",
    "output_tokens",
    "cost",
    "status",
    "block_reason",
    "human_gold_used",
    "source_sampling_label_used",
    "folder_label_used",
    "adjudication_used",
    "post_action_evidence_used",
    "scored",
    "paper_result_eligible",
}
GOLD_BLIND_FIELDS = (
    "human_gold_used",
    "source_sampling_label_used",
    "folder_label_used",
    "adjudication_used",
    "post_action_evidence_used",
)
FORBIDDEN_ROI_SOURCE_TERMS = {
    "human",
    "manual",
    "gold",
    "annotation",
    "folder",
    "sampling_label",
    "close_button",
}


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _item_set_sha256(pilot_ids: list[str]) -> str:
    return hashlib.sha256(
        json.dumps(sorted(pilot_ids), separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _image_manifest_sha256(expected_input_image_sha256: dict[str, str]) -> str:
    return hashlib.sha256(_canonical_json(expected_input_image_sha256)).hexdigest()


def _validate_protocol(
    protocol: dict[str, Any], expected_input_image_sha256: dict[str, str]
) -> None:
    expected_ids = list(expected_input_image_sha256)
    if protocol.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("visual freeze protocol contract_version is invalid")
    if protocol.get("status") != "ready_for_visual_bank_freeze":
        raise ValueError("visual freeze protocol is not ready for bank freeze")
    if protocol.get("scope") != "popup_message_judgment_v1":
        raise ValueError("visual freeze protocol scope is invalid")
    if protocol.get("action_policy") != "no_action":
        raise ValueError("visual freeze protocol must be action-free")
    if protocol.get("frozen_before_human_gold") is not True:
        raise ValueError("visual freeze protocol must be frozen before human gold")
    if protocol.get("scored") is not False or protocol.get(
        "paper_result_eligible"
    ) is not False:
        raise ValueError("visual freeze protocol cannot be scored or paper eligible")
    expected_claims = {
        "empirical_performance": False,
        "method_superiority": False,
        "user_experience_improvement": False,
        "recovery_or_dismissal": False,
    }
    if protocol.get("claims") != expected_claims:
        raise ValueError("visual freeze protocol claims must remain false")
    attestation = protocol.get("gold_blind_attestation", {})
    if set(attestation) != set(GOLD_BLIND_FIELDS) or any(
        attestation.get(field) is not False for field in GOLD_BLIND_FIELDS
    ):
        raise ValueError("visual freeze protocol gold-blind attestation is invalid")
    expected_hash = _item_set_sha256(expected_ids)
    if protocol.get("item_set_sha256") != expected_hash:
        raise ValueError("visual freeze protocol item-set hash mismatch")
    if protocol.get("input_image_manifest_sha256") != _image_manifest_sha256(
        expected_input_image_sha256
    ):
        raise ValueError("visual freeze protocol input image hash manifest mismatch")
    presence = protocol.get("presence_policy", {})
    if presence.get("mode") not in {
        "frozen_text_rule",
        "frozen_detector",
        "frozen_vlm",
    }:
        raise ValueError("visual freeze presence mode none or unknown is not ready")
    if presence.get("formal_ready") is not True:
        raise ValueError("visual freeze presence policy is not formally ready")
    if not isinstance(presence.get("policy_id"), str) or not presence[
        "policy_id"
    ].strip():
        raise ValueError("visual freeze presence policy_id is invalid")
    if not isinstance(presence.get("input_channels"), list) or not presence[
        "input_channels"
    ]:
        raise ValueError("visual freeze presence input channels are invalid")
    if not isinstance(presence.get("model_or_rule_version"), str) or not presence[
        "model_or_rule_version"
    ].strip():
        raise ValueError("visual freeze presence version is invalid")
    if presence.get("missing_evidence_action") != "abstain":
        raise ValueError("visual freeze presence policy must fail closed")
    if not _is_sha256(presence.get("implementation_sha256")):
        raise ValueError("visual freeze presence implementation hash is invalid")
    decision_threshold = presence.get("decision_threshold")
    abstain_band = presence.get("abstain_band")
    if (
        not isinstance(decision_threshold, (int, float))
        or isinstance(decision_threshold, bool)
        or not 0 <= decision_threshold <= 1
        or not isinstance(abstain_band, list)
        or len(abstain_band) != 2
        or not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and 0 <= value <= 1
            for value in abstain_band
        )
        or abstain_band[0] > abstain_band[1]
    ):
        raise ValueError("visual freeze presence thresholds are invalid")
    roi = protocol.get("roi_policy", {})
    if roi.get("roi_kind") not in {"full_screen", "predicted_popup_bbox"}:
        raise ValueError("visual freeze ROI policy is invalid")
    if roi.get("formal_ready") is not True:
        raise ValueError("visual freeze ROI policy is not formally ready")
    if not isinstance(roi.get("policy_id"), str) or not roi["policy_id"].strip():
        raise ValueError("visual freeze ROI policy_id is invalid")
    if roi.get("coordinate_space") != "normalized_xyxy":
        raise ValueError("visual freeze ROI coordinate space is invalid")
    if roi.get("close_button_bbox_is_popup_roi") is not False:
        raise ValueError("a close-button box is not a popup ROI")
    if roi.get("invalid_or_missing_roi_action") != "abstain":
        raise ValueError("visual freeze ROI policy must fail closed")
    if roi.get("roi_kind") == "predicted_popup_bbox":
        if not _is_sha256(roi.get("detector_checkpoint_sha256")):
            raise ValueError("visual freeze ROI detector hash is invalid")
        for key in ("threshold", "nms_threshold", "expansion_fraction"):
            value = roi.get(key)
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not 0 <= value <= 1
            ):
                raise ValueError(f"visual freeze ROI {key} is invalid")
        for key in ("multi_box_rule", "clipping_rule"):
            if not isinstance(roi.get(key), str) or not roi[key].strip():
                raise ValueError(f"visual freeze ROI {key} is invalid")
    engine = protocol.get("visual_engine", {})
    if engine.get("formal_ready") is not True or engine.get(
        "model_identity_reproducible"
    ) is not True:
        raise ValueError("visual freeze engine identity is not formally ready")
    for key in ("provider", "model", "revision", "license", "api_version"):
        if not isinstance(engine.get(key), str) or not engine[key].strip():
            raise ValueError(f"visual freeze engine {key} is invalid")
    for key in (
        "checkpoint_sha256",
        "preprocessing_sha256",
        "prompt_template_sha256",
        "config_sha256",
        "environment_sha256",
    ):
        if not _is_sha256(engine.get(key)):
            raise ValueError(f"visual freeze engine {key} is invalid")
    budget = protocol.get("budget", {})
    if budget.get("formal_ready") is not True:
        raise ValueError("visual freeze budget is not formally ready")
    if budget.get("unit") != "per_item" or budget.get("per_item_max_calls") != 1:
        raise ValueError("visual freeze budget must cap each item at one call")
    for key in ("input_token_cap", "output_token_cap", "latency_cap_ms"):
        value = budget.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"visual freeze budget {key} is invalid")
    if not isinstance(budget.get("price_snapshot_version"), str) or not budget[
        "price_snapshot_version"
    ].strip():
        raise ValueError("visual freeze price snapshot is invalid")


def _validate_bbox(value: Any) -> bool:
    if (
        not isinstance(value, list)
        or len(value) != 4
        or not all(
            isinstance(number, (int, float)) and not isinstance(number, bool)
            for number in value
        )
    ):
        return False
    left, top, right, bottom = value
    return 0 <= left < right <= 1 and 0 <= top < bottom <= 1


def _validate_row(row: dict[str, Any], protocol: dict[str, Any]) -> None:
    missing = sorted(ROW_KEYS - set(row))
    unexpected = sorted(set(row) - ROW_KEYS)
    if missing or unexpected:
        raise ValueError(
            f"visual bank row keys are invalid: missing={missing} unexpected={unexpected}"
        )
    if row["contract_version"] != CONTRACT_VERSION:
        raise ValueError("visual bank row contract_version is invalid")
    pilot_id = row["pilot_item_id"]
    if not isinstance(pilot_id, str) or re.fullmatch(r"PMJ-PILOT-\d{3}", pilot_id) is None:
        raise ValueError("visual bank row pilot_item_id is invalid")
    if not _is_sha256(row["input_image_sha256"]):
        raise ValueError("visual bank row input image hash is invalid")
    if any(row[field] is not False for field in GOLD_BLIND_FIELDS):
        raise ValueError("visual bank row violates the gold-blind contract")
    if row["scored"] is not False or row["paper_result_eligible"] is not False:
        raise ValueError("pre-gold visual bank row cannot be scored or paper eligible")
    if row["model_config_sha256"] != protocol["visual_engine"]["config_sha256"]:
        raise ValueError("visual bank row model config does not match the frozen config")
    for key in ("request_sha256", "response_sha256"):
        if row[key] is not None and not _is_sha256(row[key]):
            raise ValueError(f"visual bank row {key} is invalid")
    if row["status"] not in {"judged", "abstain"}:
        raise ValueError("visual bank row status is invalid")
    if row["presence_status"] != row["status"]:
        raise ValueError("visual bank presence status disagrees with row status")
    if not isinstance(row["critical_facts_pred"], list) or not all(
        isinstance(value, str) and value.strip()
        for value in row["critical_facts_pred"]
    ):
        raise ValueError("visual bank critical facts are invalid")
    for key in ("latency_ms", "input_tokens", "output_tokens", "cost"):
        value = row[key]
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            raise ValueError(f"visual bank row {key} is invalid")

    if row["status"] == "abstain":
        if (
            row["popup_present_pred"] is not None
            or row["presence_confidence"] is not None
            or row["message_text_pred"] is not None
            or row["critical_facts_pred"]
            or not isinstance(row["block_reason"], str)
            or not row["block_reason"].strip()
        ):
            raise ValueError("abstaining visual bank row must not carry an answer")
        return

    if not isinstance(row["popup_present_pred"], bool):
        raise ValueError("judged visual bank row requires popup presence")
    for key in ("request_sha256", "response_sha256"):
        if not _is_sha256(row[key]):
            raise ValueError(f"judged visual bank row {key} is required")
    confidence = row["presence_confidence"]
    if (
        not isinstance(confidence, (int, float))
        or isinstance(confidence, bool)
        or not 0 <= confidence <= 1
    ):
        raise ValueError("judged visual bank row presence confidence is invalid")
    if not isinstance(row["presence_basis"], str) or not row["presence_basis"].strip():
        raise ValueError("judged visual bank row requires a presence basis")
    if row["presence_basis"] != protocol["presence_policy"]["policy_id"]:
        raise ValueError("visual bank row does not bind the frozen presence policy")
    if row["block_reason"] is not None:
        raise ValueError("judged visual bank row cannot carry a block reason")

    if row["popup_present_pred"] is True:
        if not isinstance(row["message_text_pred"], str) or not row[
            "message_text_pred"
        ].strip():
            raise ValueError("positive visual judgment requires a message")
        if protocol["roi_policy"]["roi_kind"] == "predicted_popup_bbox":
            if row["roi_kind"] != "predicted_popup_bbox" or not _validate_bbox(
                row["roi_normalized_xyxy"]
            ):
                raise ValueError("positive visual judgment requires the predeclared popup ROI")
            source = row["roi_source"]
            if not isinstance(source, str) or not source.strip():
                raise ValueError("positive visual judgment requires a popup ROI source")
            normalized_source = source.casefold().replace("-", "_")
            if any(term in normalized_source for term in FORBIDDEN_ROI_SOURCE_TERMS):
                raise ValueError("popup ROI source is not gold blind")
            if source != protocol["roi_policy"]["policy_id"]:
                raise ValueError("popup ROI source does not bind the frozen ROI policy")
            roi_confidence = row["roi_confidence"]
            if (
                not isinstance(roi_confidence, (int, float))
                or isinstance(roi_confidence, bool)
                or not 0 <= roi_confidence <= 1
            ):
                raise ValueError("popup ROI confidence is invalid")
        elif (
            row["roi_kind"] != "full_screen"
            or row["roi_normalized_xyxy"] != [0.0, 0.0, 1.0, 1.0]
            or row["roi_source"] != protocol["roi_policy"]["policy_id"]
        ):
            raise ValueError("positive visual judgment does not match the frozen full-screen ROI")
    elif row["message_text_pred"] is not None or row["critical_facts_pred"]:
        raise ValueError("negative visual judgment cannot carry popup message semantics")


def finalize_visual_evidence_bank(
    protocol: dict[str, Any],
    expected_input_image_sha256: dict[str, str],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate and hash a complete private bank; return aggregate public metadata."""
    if not isinstance(expected_input_image_sha256, dict) or not expected_input_image_sha256:
        raise ValueError("expected visual bank image-hash map is required")
    expected_pilot_ids = list(expected_input_image_sha256)
    if not all(
        isinstance(pilot_id, str)
        and re.fullmatch(r"PMJ-PILOT-\d{3}", pilot_id) is not None
        for pilot_id in expected_pilot_ids
    ):
        raise ValueError("expected visual bank pilot_item_id is invalid")
    if not all(_is_sha256(value) for value in expected_input_image_sha256.values()):
        raise ValueError("expected visual bank input image hash is invalid")
    _validate_protocol(protocol, expected_input_image_sha256)

    by_id: dict[str, dict[str, Any]] = {}
    duplicate_ids: set[str] = set()
    for raw_row in rows:
        row = deepcopy(raw_row)
        _validate_row(row, protocol)
        pilot_id = row["pilot_item_id"]
        if pilot_id in by_id:
            duplicate_ids.add(pilot_id)
        else:
            by_id[pilot_id] = row
    if duplicate_ids:
        raise ValueError(f"visual bank has duplicate pilot_item_id values: {sorted(duplicate_ids)}")
    expected = set(expected_pilot_ids)
    actual = set(by_id)
    unknown = sorted(actual - expected)
    if unknown:
        raise ValueError(f"visual bank has unknown pilot_item_id values: {unknown}")
    missing = sorted(expected - actual)
    if missing:
        raise ValueError(f"visual bank is missing pilot_item_id values: {missing}")
    for pilot_id, row in by_id.items():
        if row["input_image_sha256"] != expected_input_image_sha256[pilot_id]:
            raise ValueError(f"visual bank input image hash mismatch: {pilot_id}")

    ordered_rows = [by_id[pilot_id] for pilot_id in sorted(expected)]
    payload = b"".join(_canonical_json(row) + b"\n" for row in ordered_rows)
    judged_count = sum(row["status"] == "judged" for row in ordered_rows)
    popup_roi_count = sum(
        row["roi_kind"] == "predicted_popup_bbox" for row in ordered_rows
    )
    return {
        "contract_version": CONTRACT_VERSION,
        "status": "frozen_private_visual_evidence_bank",
        "scope": "popup_message_judgment_v1",
        "action_policy": "no_action",
        "item_set_sha256": protocol["item_set_sha256"],
        "input_image_manifest_sha256": protocol["input_image_manifest_sha256"],
        "protocol_sha256": hashlib.sha256(_canonical_json(protocol)).hexdigest(),
        "visual_engine_config_sha256": protocol["visual_engine"]["config_sha256"],
        "visual_bank_sha256": hashlib.sha256(payload).hexdigest(),
        "item_count": len(ordered_rows),
        "judged_count": judged_count,
        "abstain_count": len(ordered_rows) - judged_count,
        "popup_roi_count": popup_roi_count,
        "gold_blind": True,
        "frozen_before_human_gold": True,
        "privacy_status": "private_rows_withheld_public_summary_only",
        "scored": False,
        "paper_result_eligible": False,
        "claims": {
            "empirical_performance": False,
            "method_superiority": False,
            "user_experience_improvement": False,
            "recovery_or_dismissal": False,
        },
    }
