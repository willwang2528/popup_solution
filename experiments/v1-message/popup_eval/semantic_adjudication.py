"""Strict, prediction-hash-bound human review of popup-message outputs."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
import re
from typing import Any


SEMANTIC_KEYS = {
    "contract_version",
    "batch_id",
    "pilot_item_id",
    "method_id",
    "prediction_row_sha256",
    "record_status",
    "adjudicator_id_pseudonymous",
    "message_semantically_correct",
    "critical_hallucination",
    "decision_rationale",
    "evidence_rechecked_via_adapter",
    "resolved_at",
}
PILOT_ID_PATTERN = re.compile(r"PMJ-PILOT-\d{3}")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


def prediction_row_sha256(row: dict[str, Any]) -> str:
    payload = json.dumps(
        row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_semantic_row(row: dict[str, Any]) -> None:
    if set(row) != SEMANTIC_KEYS:
        missing = sorted(SEMANTIC_KEYS - set(row))
        unexpected = sorted(set(row) - SEMANTIC_KEYS)
        raise ValueError(
            f"semantic adjudication keys are invalid: missing={missing} unexpected={unexpected}"
        )
    if row["contract_version"] != "popup-message-output-adjudication-v1.0":
        raise ValueError("semantic adjudication contract_version is invalid")
    if row["batch_id"] != "popsweeper-message-pilot-30-v1":
        raise ValueError("semantic adjudication batch_id is invalid")
    if not isinstance(row["pilot_item_id"], str) or PILOT_ID_PATTERN.fullmatch(
        row["pilot_item_id"]
    ) is None:
        raise ValueError("semantic adjudication pilot_item_id is invalid")
    if not isinstance(row["method_id"], str) or not row["method_id"].strip():
        raise ValueError("semantic adjudication method_id is required")
    if not isinstance(row["prediction_row_sha256"], str) or SHA256_PATTERN.fullmatch(
        row["prediction_row_sha256"]
    ) is None:
        raise ValueError("semantic adjudication prediction_row_sha256 is invalid")
    if row["record_status"] != "completed":
        raise ValueError("semantic adjudication row must be completed")
    if not isinstance(row["adjudicator_id_pseudonymous"], str) or not row[
        "adjudicator_id_pseudonymous"
    ].strip():
        raise ValueError("semantic adjudicator identity is required")
    if not isinstance(row["message_semantically_correct"], bool):
        raise ValueError("message_semantically_correct must be boolean")
    if not isinstance(row["critical_hallucination"], bool):
        raise ValueError("critical_hallucination must be boolean")
    if not isinstance(row["decision_rationale"], str) or not row[
        "decision_rationale"
    ].strip():
        raise ValueError("semantic adjudication decision_rationale is required")
    if row["evidence_rechecked_via_adapter"] is not True:
        raise ValueError("semantic adjudication evidence must be rechecked")
    resolved_at = row["resolved_at"]
    if not isinstance(resolved_at, str) or not resolved_at.strip():
        raise ValueError("semantic adjudication resolved_at is required")
    try:
        timestamp = datetime.fromisoformat(resolved_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("semantic adjudication resolved_at must be ISO-8601") from error
    if timestamp.tzinfo is None:
        raise ValueError("semantic adjudication resolved_at must include timezone")


def prepare_semantic_output_annotations(
    items: list[dict[str, Any]],
    prediction_rows: list[dict[str, Any]],
    semantic_rows: list[dict[str, Any]],
    *,
    method_ids: list[str],
) -> dict[tuple[str, str], dict[str, Any]]:
    """Require complete blind review for every eligible positive method output."""
    if not method_ids or len(method_ids) != len(set(method_ids)):
        raise ValueError("semantic adjudication requires unique method_ids")
    method_set = set(method_ids)
    items_by_pilot: dict[str, dict[str, Any]] = {}
    for item in items:
        identity = item.get("identity", {})
        pilot_id = identity.get("pilot_item_id")
        if not isinstance(pilot_id, str):
            raise ValueError("semantic adjudication item is missing pilot_item_id")
        if pilot_id in items_by_pilot:
            raise ValueError(f"duplicate semantic item pilot_item_id: {pilot_id}")
        items_by_pilot[pilot_id] = item

    predictions: dict[tuple[str, str], dict[str, Any]] = {}
    for row in prediction_rows:
        method_id = row.get("method_id")
        if method_id not in method_set:
            continue
        pilot_id = row.get("pilot_item_id")
        if pilot_id not in items_by_pilot:
            raise ValueError(f"semantic prediction has unknown pilot_item_id: {pilot_id}")
        key = (pilot_id, method_id)
        if key in predictions:
            raise ValueError(f"duplicate frozen prediction for semantic review: {key}")
        predictions[key] = row
    expected_prediction_keys = {
        (pilot_id, method_id)
        for pilot_id in items_by_pilot
        for method_id in method_ids
    }
    missing_predictions = sorted(expected_prediction_keys - set(predictions))
    if missing_predictions:
        raise ValueError(f"missing frozen prediction rows: {missing_predictions}")

    expected_semantic_keys: set[tuple[str, str]] = set()
    for key, prediction in predictions.items():
        pilot_id, _ = key
        labels = items_by_pilot[pilot_id]["message_judgment"]["labels"]
        if (
            labels.get("popup_present_gt") is True
            and labels.get("message_text_observability") == "complete"
            and prediction.get("status") == "judged"
            and prediction.get("popup_present_pred") is True
        ):
            expected_semantic_keys.add(key)

    validated_rows: dict[tuple[str, str], dict[str, Any]] = {}
    for row in semantic_rows:
        _validate_semantic_row(row)
        key = (row["pilot_item_id"], row["method_id"])
        if key not in expected_semantic_keys:
            raise ValueError(f"unknown or ineligible semantic adjudication: {key}")
        if key in validated_rows:
            raise ValueError(f"duplicate semantic adjudication: {key}")
        expected_hash = prediction_row_sha256(predictions[key])
        if row["prediction_row_sha256"] != expected_hash:
            raise ValueError(f"prediction_row_sha256 mismatch for {key}")
        validated_rows[key] = row

    missing_semantic = sorted(expected_semantic_keys - set(validated_rows))
    if missing_semantic:
        raise ValueError(f"missing semantic adjudication: {missing_semantic}")

    return {
        (items_by_pilot[pilot_id]["identity"]["item_id"], method_id): {
            "message_semantically_correct": row["message_semantically_correct"],
            "critical_hallucination": row["critical_hallucination"],
            "prediction_row_sha256": row["prediction_row_sha256"],
            "adjudicator_id_pseudonymous": row["adjudicator_id_pseudonymous"],
            "evidence_rechecked_via_adapter": True,
        }
        for (pilot_id, method_id), row in validated_rows.items()
    }
