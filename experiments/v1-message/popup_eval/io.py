"""Strict JSONL I/O and the frozen annotation-pilot adapter."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any


class DuplicateKeyError(ValueError):
    pass


ADJUDICATION_KEYS = {
    "protocol_version",
    "batch_id",
    "pilot_item_id",
    "record_status",
    "adjudicator_id_pseudonymous",
    "adjudication_status",
    "presence_label_final",
    "message_text_final",
    "message_observability_final",
    "semantic_slots_final",
    "decision_rationale",
    "evidence_rechecked_via_adapter",
    "resolved_at",
}
SLOT_TYPES = {
    "amount",
    "date_time",
    "duration_deadline",
    "action_choice",
    "object_target",
    "permission_data",
    "restriction_negation",
    "consequence",
    "other_critical",
}
SLOT_POLARITIES = {"affirmed", "negated", "conditional", "unknown"}


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line, object_pairs_hook=_strict_pairs)
        except Exception as error:  # noqa: BLE001 - retain file and line context
            raise ValueError(f"{path}:{line_number}: {error}") from error
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number}: JSONL row must be an object")
        rows.append(row)
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )
    path.write_text(payload, encoding="utf-8")


def _adapt_pilot_manifest_row(row: dict[str, Any]) -> dict[str, Any]:
    pilot_item_id = row["pilot_item_id"]
    return {
        "identity": {
            "item_id": pilot_item_id,
            "pilot_item_id": pilot_item_id,
            "record_kind": "annotation_pilot_candidate",
            "split": "unassigned",
        },
        "message_judgment": {
            "profile": "popup_message_judgment_v1",
            "labels": {
                "popup_present_gt": None,
                "message_text_gt": None,
                "critical_facts_gt": [],
                "message_text_observability": None,
                "semantic_slots_gt": [],
            },
        },
        "observations": [],
        "candidates": [],
        "decision": {"policy": {"decision": "no_action"}},
        "action_attempts": [],
        "pilot_manifest": deepcopy(row),
        "evaluation_exclusion_reasons": ["adjudicated_gold_missing"],
    }


def _adapt_item_row(row: dict[str, Any]) -> dict[str, Any]:
    if "identity" in row:
        return deepcopy(row)
    if "pilot_item_id" in row and "source_kind" in row:
        return _adapt_pilot_manifest_row(row)
    raise ValueError("item row must be a union item or frozen annotation-pilot manifest row")


def _pilot_item_id(item: dict[str, Any]) -> str | None:
    identity = item["identity"]
    return identity.get("pilot_item_id") or (
        identity["item_id"] if identity["item_id"].startswith("PMJ-PILOT-") else None
    )


def _adjudication_error(message: str) -> ValueError:
    return ValueError(f"adjudication output is invalid: {message}")


def _validate_adjudication_row(row: dict[str, Any]) -> None:
    """Validate the frozen completed-output contract before treating it as gold."""
    missing = sorted(ADJUDICATION_KEYS - set(row))
    unexpected = sorted(set(row) - ADJUDICATION_KEYS)
    if missing or unexpected:
        raise _adjudication_error(
            f"missing={missing or 'none'} unexpected={unexpected or 'none'}"
        )
    if row["protocol_version"] != "1.0.0":
        raise _adjudication_error("unsupported protocol_version")
    if row["batch_id"] != "popsweeper-message-pilot-30-v1":
        raise _adjudication_error("unexpected batch_id")
    pilot_id = row["pilot_item_id"]
    if not isinstance(pilot_id, str) or re.fullmatch(r"PMJ-PILOT-\d{3}", pilot_id) is None:
        raise _adjudication_error("invalid pilot_item_id")
    if row["record_status"] != "completed":
        raise _adjudication_error("non-blank row must be completed")
    adjudicator = row["adjudicator_id_pseudonymous"]
    if not isinstance(adjudicator, str) or not adjudicator.strip():
        raise _adjudication_error("adjudicator identity is required")
    if row["adjudication_status"] not in {"resolved", "cannot_resolve"}:
        raise _adjudication_error("completed row has invalid adjudication_status")
    rationale = row["decision_rationale"]
    if not isinstance(rationale, str) or not rationale.strip():
        raise _adjudication_error("decision_rationale is required")
    if row["evidence_rechecked_via_adapter"] is not True:
        raise _adjudication_error("evidence_rechecked_via_adapter must be true")
    resolved_at = row["resolved_at"]
    if not isinstance(resolved_at, str) or not resolved_at.strip():
        raise _adjudication_error("resolved_at is required")
    try:
        timestamp = datetime.fromisoformat(resolved_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise _adjudication_error("resolved_at must be ISO-8601") from error
    if timestamp.tzinfo is None:
        raise _adjudication_error("resolved_at must include a timezone")

    presence = row["presence_label_final"]
    if presence not in {"popup", "no_popup", "uncertain", "unusable", None}:
        raise _adjudication_error("invalid presence_label_final")
    observability = row["message_observability_final"]
    if observability not in {"complete", "partial", "not_observable", "not_applicable", None}:
        raise _adjudication_error("invalid message_observability_final")
    message = row["message_text_final"]
    slots = row["semantic_slots_final"]
    if not isinstance(slots, list):
        raise _adjudication_error("semantic_slots_final must be an array")
    seen_slots: set[str] = set()
    for index, slot in enumerate(slots):
        if not isinstance(slot, dict) or set(slot) != {"slot_type", "value", "polarity"}:
            raise _adjudication_error(f"semantic_slots_final[{index}] has invalid keys")
        if slot["slot_type"] not in SLOT_TYPES:
            raise _adjudication_error(f"semantic_slots_final[{index}] has invalid slot_type")
        if not isinstance(slot["value"], str) or not slot["value"].strip():
            raise _adjudication_error(f"semantic_slots_final[{index}] has empty value")
        if slot["polarity"] not in SLOT_POLARITIES:
            raise _adjudication_error(f"semantic_slots_final[{index}] has invalid polarity")
        serialized = json.dumps(slot, ensure_ascii=False, sort_keys=True)
        if serialized in seen_slots:
            raise _adjudication_error("semantic_slots_final contains a duplicate")
        seen_slots.add(serialized)

    if row["adjudication_status"] == "cannot_resolve":
        if presence is not None or message is not None or observability is not None or slots:
            raise _adjudication_error(
                "cannot_resolve row cannot carry final presence or message labels"
            )
    elif row["adjudication_status"] == "resolved":
        if presence == "popup":
            if observability not in {"complete", "partial", "not_observable"}:
                raise _adjudication_error("popup observability is inconsistent")
            if observability in {"complete", "partial"}:
                if not isinstance(message, str) or not message.strip():
                    raise _adjudication_error("observable popup requires message_text_final")
            elif message is not None or slots:
                raise _adjudication_error("unobservable popup cannot carry message semantics")
        elif presence == "no_popup":
            if message is not None or observability != "not_applicable" or slots:
                raise _adjudication_error("no_popup cannot carry message semantics")


def finalize_adjudication_batch(
    items: list[dict[str, Any]], annotation_rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Validate an exact frozen-item/adjudication bijection and hash the private batch.

    The returned rows contain human labels and must remain private.  The summary
    contains only counts and a content hash, so callers can publish it after
    applying their normal privacy review.
    """
    expected_ids: list[str] = []
    for raw_item in items:
        pilot_id = _pilot_item_id(_adapt_item_row(raw_item))
        if pilot_id is None:
            raise _adjudication_error("frozen item is missing pilot_item_id")
        expected_ids.append(pilot_id)
    duplicate_item_ids = sorted(
        pilot_id for pilot_id in set(expected_ids) if expected_ids.count(pilot_id) > 1
    )
    if duplicate_item_ids:
        raise _adjudication_error(f"duplicate frozen pilot_item_id values: {duplicate_item_ids}")

    rows_by_id: dict[str, dict[str, Any]] = {}
    duplicate_row_ids: set[str] = set()
    for row in annotation_rows:
        if row.get("record_status") == "blank":
            raise _adjudication_error("blank row cannot finalize a batch")
        _validate_adjudication_row(row)
        pilot_id = row["pilot_item_id"]
        if pilot_id in rows_by_id:
            duplicate_row_ids.add(pilot_id)
        else:
            rows_by_id[pilot_id] = deepcopy(row)
    if duplicate_row_ids:
        raise _adjudication_error(
            f"duplicate adjudication pilot_item_id values: {sorted(duplicate_row_ids)}"
        )

    expected_set = set(expected_ids)
    actual_set = set(rows_by_id)
    unknown_ids = sorted(actual_set - expected_set)
    if unknown_ids:
        raise _adjudication_error(f"unknown pilot_item_id values: {unknown_ids}")
    missing_ids = sorted(expected_set - actual_set)
    if missing_ids:
        raise _adjudication_error(f"missing pilot_item_id values: {missing_ids}")

    finalized_rows = [rows_by_id[pilot_id] for pilot_id in sorted(expected_set)]
    canonical_payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in finalized_rows
    ).encode("utf-8")
    resolved_count = sum(
        row["adjudication_status"] == "resolved" for row in finalized_rows
    )
    metric_eligible_count = sum(
        row["adjudication_status"] == "resolved"
        and row["presence_label_final"] in {"popup", "no_popup"}
        for row in finalized_rows
    )
    summary = {
        "status": "finalized_human_adjudication_batch",
        "protocol_version": "1.0.0",
        "batch_id": "popsweeper-message-pilot-30-v1",
        "item_count": len(finalized_rows),
        "resolved_count": resolved_count,
        "cannot_resolve_count": len(finalized_rows) - resolved_count,
        "metric_eligible_count": metric_eligible_count,
        "batch_sha256": hashlib.sha256(canonical_payload).hexdigest(),
    }
    return finalized_rows, summary


def _apply_pilot_adjudication(item: dict[str, Any], row: dict[str, Any]) -> None:
    reasons = item.setdefault("evaluation_exclusion_reasons", [])
    if row.get("record_status") != "completed" or row.get("adjudication_status") != "resolved":
        if "adjudication_not_resolved" not in reasons:
            reasons.append("adjudication_not_resolved")
        return
    presence = row.get("presence_label_final")
    if presence not in {"popup", "no_popup"}:
        if "presence_uncertain_or_unusable" not in reasons:
            reasons.append("presence_uncertain_or_unusable")
        return

    labels = item["message_judgment"]["labels"]
    labels["popup_present_gt"] = presence == "popup"
    labels["message_text_gt"] = row.get("message_text_final") if presence == "popup" else None
    slots = row.get("semantic_slots_final", []) if presence == "popup" else []
    labels["critical_facts_gt"] = [slot["value"] for slot in slots]
    labels["message_text_observability"] = row.get("message_observability_final")
    labels["semantic_slots_gt"] = deepcopy(slots)
    item["adjudication_provenance"] = {
        "protocol_version": row.get("protocol_version"),
        "batch_id": row.get("batch_id"),
        "pilot_item_id": row.get("pilot_item_id"),
        "adjudication_status": row.get("adjudication_status"),
        "evidence_rechecked_via_adapter": row.get("evidence_rechecked_via_adapter"),
    }
    item["evaluation_exclusion_reasons"] = [
        reason for reason in reasons if reason != "adjudicated_gold_missing"
    ]


def prepare_items(
    items: list[dict[str, Any]], annotation_rows: list[dict[str, Any]] | None = None
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    """Adapt union/pilot items and join frozen adjudication outputs by pilot_item_id."""
    prepared = [_adapt_item_row(row) for row in items]
    by_pilot_id = {
        pilot_id: item
        for item in prepared
        if (pilot_id := _pilot_item_id(item)) is not None
    }
    for row in annotation_rows or []:
        if "presence_label_final" not in row:
            raise ValueError("annotation rows must follow adjudication_output.schema.json")
        if row.get("record_status") == "blank" and row.get("pilot_item_id") is None:
            continue
        _validate_adjudication_row(row)
        pilot_id = row.get("pilot_item_id")
        if not pilot_id or pilot_id not in by_pilot_id:
            raise ValueError(f"adjudication pilot_item_id has no frozen item: {pilot_id!r}")
        _apply_pilot_adjudication(by_pilot_id[pilot_id], row)
    return prepared, {}


def prepare_finalized_pilot_items(
    items: list[dict[str, Any]], annotation_rows: list[dict[str, Any]]
) -> tuple[
    list[dict[str, Any]],
    dict[tuple[str, str], dict[str, Any]],
    dict[str, Any],
]:
    """Finalize a complete pilot gold batch, then join it to private feature items."""
    finalized_rows, summary = finalize_adjudication_batch(items, annotation_rows)
    prepared, semantic_annotations = prepare_items(items, finalized_rows)
    for item in prepared:
        provenance = item.get("adjudication_provenance")
        if provenance is not None:
            provenance["adjudication_batch_sha256"] = summary["batch_sha256"]
    return prepared, semantic_annotations, summary
