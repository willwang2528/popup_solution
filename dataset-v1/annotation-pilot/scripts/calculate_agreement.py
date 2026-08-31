#!/usr/bin/env python3
"""Validate paired blind annotations and compute protocol agreement metrics."""

from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


PROTOCOL_VERSION = "1.0.0"
BATCH_ID = "popsweeper-message-pilot-30-v1"
PRESENCE_CATEGORIES = ("popup", "no_popup", "uncertain", "unusable")
MESSAGE_OBSERVABILITY = (
    "complete",
    "partial",
    "not_observable",
    "not_applicable",
)
SLOT_TYPES = (
    "amount",
    "date_time",
    "duration_deadline",
    "action_choice",
    "object_target",
    "permission_data",
    "restriction_negation",
    "consequence",
    "other_critical",
)
POLARITIES = ("affirmed", "negated", "conditional", "unknown")
ANNOTATION_KEYS = {
    "protocol_version",
    "batch_id",
    "pilot_item_id",
    "annotation_order",
    "adapter_item_handle",
    "annotator_role",
    "annotator_id_pseudonymous",
    "record_status",
    "presence_label",
    "message_text",
    "message_observability",
    "semantic_slots",
    "confidence",
    "evidence",
    "blindness_attestation",
    "annotation_started_at",
    "annotation_completed_at",
    "notes",
}


class ProtocolError(ValueError):
    """Raised when annotation input violates the frozen pilot protocol."""


def normalize_message(value: str) -> str:
    """Normalize representation only; preserve punctuation and critical tokens."""

    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(normalized.split())


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise ProtocolError(f"duplicate JSON key: {key}")
        output[key] = value
    return output


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line, object_pairs_hook=strict_object)
            except (json.JSONDecodeError, ProtocolError) as exc:
                raise ProtocolError(f"{path}:{line_number}: {exc}") from exc
            if not isinstance(row, dict):
                raise ProtocolError(f"{path}:{line_number}: expected object")
            rows.append(row)
    if not rows:
        raise ProtocolError(f"{path}: no annotation records")
    return rows


def require_exact_keys(value: Any, expected: set[str], path: str) -> None:
    if not isinstance(value, dict):
        raise ProtocolError(f"{path}: expected object")
    keys = set(value)
    missing = sorted(expected - keys)
    unexpected = sorted(keys - expected)
    if missing or unexpected:
        raise ProtocolError(
            f"{path}: missing={missing or 'none'} "
            f"unexpected={unexpected or 'none'}"
        )


def parse_timestamp(value: Any, path: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ProtocolError(f"{path}: expected non-empty ISO-8601 timestamp")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProtocolError(f"{path}: invalid ISO-8601 timestamp") from exc


def normalize_slot(slot: dict[str, Any]) -> tuple[str, str, str]:
    return (
        slot["slot_type"],
        normalize_message(slot["value"]),
        slot["polarity"],
    )


def validate_completed_annotation(
    record: dict[str, Any], *, expected_role: str | None = None
) -> None:
    item = record.get("pilot_item_id", "<unknown>")
    require_exact_keys(record, ANNOTATION_KEYS, str(item))
    if record["protocol_version"] != PROTOCOL_VERSION:
        raise ProtocolError(f"{item}: unsupported protocol_version")
    if record["batch_id"] != BATCH_ID:
        raise ProtocolError(f"{item}: unexpected batch_id")
    if not isinstance(item, str) or re.fullmatch(r"PMJ-PILOT-\d{3}", item) is None:
        raise ProtocolError(f"{item}: invalid pilot_item_id")
    expected_handle = f"adapter://popsweeper/pilot/{item}"
    if record["adapter_item_handle"] != expected_handle:
        raise ProtocolError(f"{item}: adapter handle does not match item")
    order = record["annotation_order"]
    if isinstance(order, bool) or not isinstance(order, int) or not 1 <= order <= 30:
        raise ProtocolError(f"{item}: annotation_order must be 1..30")
    role = record["annotator_role"]
    if role not in {"A", "B"} or (expected_role and role != expected_role):
        raise ProtocolError(f"{item}: unexpected annotator role {role!r}")
    pseudonym = record["annotator_id_pseudonymous"]
    if not isinstance(pseudonym, str) or not pseudonym.strip():
        raise ProtocolError(f"{item}: annotator pseudonym is required")
    if record["record_status"] != "completed":
        raise ProtocolError(f"{item}: blank records cannot enter agreement")

    presence = record["presence_label"]
    if presence not in PRESENCE_CATEGORIES:
        raise ProtocolError(f"{item}: invalid presence_label")
    observability = record["message_observability"]
    if observability not in MESSAGE_OBSERVABILITY:
        raise ProtocolError(f"{item}: invalid message_observability")
    message = record["message_text"]
    slots = record["semantic_slots"]
    if not isinstance(slots, list):
        raise ProtocolError(f"{item}: semantic_slots must be an array")

    if presence == "popup":
        if observability not in {"complete", "partial", "not_observable"}:
            raise ProtocolError(f"{item}: popup observability is inconsistent")
        if observability in {"complete", "partial"}:
            if not isinstance(message, str) or not message.strip():
                raise ProtocolError(f"{item}: observable popup requires message_text")
        elif message is not None or slots:
            raise ProtocolError(
                f"{item}: unobservable popup cannot carry message semantics"
            )
    elif presence == "no_popup":
        if message is not None or observability != "not_applicable" or slots:
            raise ProtocolError(f"{item}: no_popup cannot carry message semantics")
    else:
        if message is not None or observability != "not_observable" or slots:
            raise ProtocolError(
                f"{item}: uncertain/unusable records cannot carry message semantics"
            )

    seen_slots: set[tuple[str, str, str]] = set()
    for index, semantic_slot in enumerate(slots):
        require_exact_keys(
            semantic_slot,
            {"slot_type", "value", "polarity"},
            f"{item}.semantic_slots[{index}]",
        )
        if semantic_slot["slot_type"] not in SLOT_TYPES:
            raise ProtocolError(f"{item}: invalid semantic slot type")
        value = semantic_slot["value"]
        if not isinstance(value, str) or not value.strip():
            raise ProtocolError(f"{item}: semantic slot value is empty")
        if semantic_slot["polarity"] not in POLARITIES:
            raise ProtocolError(f"{item}: invalid semantic slot polarity")
        canonical = normalize_slot(semantic_slot)
        if canonical in seen_slots:
            raise ProtocolError(f"{item}: duplicate normalized semantic slot")
        seen_slots.add(canonical)

    confidence = record["confidence"]
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, int)
        or not 1 <= confidence <= 5
    ):
        raise ProtocolError(f"{item}: confidence must be an integer 1..5")

    evidence = record["evidence"]
    require_exact_keys(
        evidence,
        {
            "adapter_viewed",
            "view_session_id",
            "region_or_node_notes",
            "raw_image_copied",
        },
        f"{item}.evidence",
    )
    if evidence["adapter_viewed"] is not True:
        raise ProtocolError(f"{item}: adapter evidence was not inspected")
    if evidence["raw_image_copied"] is not False:
        raise ProtocolError(f"{item}: raw image copying is forbidden")
    if not isinstance(evidence["view_session_id"], str) or not evidence[
        "view_session_id"
    ].strip():
        raise ProtocolError(f"{item}: view_session_id is required")
    notes = evidence["region_or_node_notes"]
    if notes is not None and not isinstance(notes, str):
        raise ProtocolError(f"{item}: evidence notes must be string or null")

    blindness = record["blindness_attestation"]
    require_exact_keys(
        blindness,
        {"peer_labels_unseen", "source_class_unseen", "model_output_unseen"},
        f"{item}.blindness_attestation",
    )
    if any(value is not True for value in blindness.values()):
        raise ProtocolError(f"{item}: blindness attestation is incomplete")

    started = parse_timestamp(record["annotation_started_at"], f"{item}.started")
    completed = parse_timestamp(
        record["annotation_completed_at"], f"{item}.completed"
    )
    if completed < started:
        raise ProtocolError(f"{item}: completion precedes start")
    if record["notes"] is not None and not isinstance(record["notes"], str):
        raise ProtocolError(f"{item}: notes must be string or null")


def index_annotations(
    records: Iterable[dict[str, Any]], role: str
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for record in records:
        validate_completed_annotation(record, expected_role=role)
        item = record["pilot_item_id"]
        if item in indexed:
            raise ProtocolError(f"duplicate annotation for {item} role {role}")
        indexed[item] = record
    return indexed


def pair_annotations(
    records_a: Iterable[dict[str, Any]], records_b: Iterable[dict[str, Any]]
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    indexed_a = index_annotations(records_a, "A")
    indexed_b = index_annotations(records_b, "B")
    if set(indexed_a) != set(indexed_b):
        missing_a = sorted(set(indexed_b) - set(indexed_a))
        missing_b = sorted(set(indexed_a) - set(indexed_b))
        raise ProtocolError(
            f"annotator item sets differ: missing_A={missing_a}, missing_B={missing_b}"
        )
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for item in sorted(indexed_a):
        a = indexed_a[item]
        b = indexed_b[item]
        if a["annotator_id_pseudonymous"] == b["annotator_id_pseudonymous"]:
            raise ProtocolError(f"{item}: A and B must be independent annotators")
        pairs.append((a, b))
    return pairs


def semantic_slot_set(record: dict[str, Any]) -> set[tuple[str, str, str]]:
    return {normalize_slot(slot) for slot in record["semantic_slots"]}


def safe_rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def compute_agreement(
    records_a: Iterable[dict[str, Any]], records_b: Iterable[dict[str, Any]]
) -> dict[str, Any]:
    pairs = pair_annotations(records_a, records_b)
    total = len(pairs)
    if total == 0:
        raise ProtocolError("no paired annotations")

    confusion = {
        category_a: {category_b: 0 for category_b in PRESENCE_CATEGORIES}
        for category_a in PRESENCE_CATEGORIES
    }
    marginal_a: Counter[str] = Counter()
    marginal_b: Counter[str] = Counter()
    presence_matches = 0
    for a, b in pairs:
        label_a = a["presence_label"]
        label_b = b["presence_label"]
        confusion[label_a][label_b] += 1
        marginal_a[label_a] += 1
        marginal_b[label_b] += 1
        presence_matches += int(label_a == label_b)
    observed = presence_matches / total
    expected = sum(
        (marginal_a[category] / total) * (marginal_b[category] / total)
        for category in PRESENCE_CATEGORIES
    )
    kappa = None if math.isclose(expected, 1.0) else (observed - expected) / (1 - expected)

    message_pairs = [
        (a, b)
        for a, b in pairs
        if a["presence_label"] == b["presence_label"] == "popup"
        and isinstance(a["message_text"], str)
        and isinstance(b["message_text"], str)
    ]
    exact_count = sum(a["message_text"] == b["message_text"] for a, b in message_pairs)
    normalized_count = sum(
        normalize_message(a["message_text"])
        == normalize_message(b["message_text"])
        for a, b in message_pairs
    )
    slot_exact = 0
    jaccards: list[float] = []
    for a, b in message_pairs:
        slots_a = semantic_slot_set(a)
        slots_b = semantic_slot_set(b)
        slot_exact += int(slots_a == slots_b)
        union = slots_a | slots_b
        jaccards.append(1.0 if not union else len(slots_a & slots_b) / len(union))

    warnings: list[str] = []
    if kappa is None:
        warnings.append(
            "presence Cohen kappa is undefined because expected agreement is 1"
        )
    if not message_pairs:
        warnings.append("no jointly-popup text-observable pairs for message agreement")

    return {
        "protocol_version": PROTOCOL_VERSION,
        "batch_id": BATCH_ID,
        "status": "agreement_computed_not_adjudicated_gold",
        "paired_items": total,
        "presence": {
            "categories": list(PRESENCE_CATEGORIES),
            "observed_agreement": observed,
            "expected_agreement": expected,
            "cohen_kappa": kappa,
            "confusion_matrix_a_rows_b_columns": confusion,
        },
        "message": {
            "comparison_scope": "both_annotators_popup_and_message_text_observable",
            "comparable_items": len(message_pairs),
            "exact_agreement_count": exact_count,
            "exact_agreement_rate": safe_rate(exact_count, len(message_pairs)),
            "normalized_agreement_count": normalized_count,
            "normalized_agreement_rate": safe_rate(
                normalized_count, len(message_pairs)
            ),
            "normalization": "Unicode NFKC + casefold + whitespace collapse; no token deletion",
        },
        "semantic_slots": {
            "comparison_scope": "same jointly-popup text-observable pairs",
            "comparable_items": len(message_pairs),
            "exact_set_count": slot_exact,
            "exact_set_agreement_rate": safe_rate(slot_exact, len(message_pairs)),
            "mean_jaccard": (
                sum(jaccards) / len(jaccards) if jaccards else None
            ),
        },
        "excluded_from_message_comparison": total - len(message_pairs),
        "warnings": warnings,
    }


def disagreement_reasons(
    annotation_a: dict[str, Any], annotation_b: dict[str, Any]
) -> list[str]:
    if annotation_a["presence_label"] != annotation_b["presence_label"]:
        return ["presence"]
    if annotation_a["presence_label"] != "popup":
        return []
    reasons: list[str] = []
    message_a = annotation_a["message_text"]
    message_b = annotation_b["message_text"]
    if message_a != message_b:
        reasons.append("message_exact")
    if (message_a is None) != (message_b is None) or (
        isinstance(message_a, str)
        and isinstance(message_b, str)
        and normalize_message(message_a) != normalize_message(message_b)
    ):
        reasons.append("message_normalized")
    if annotation_a["message_observability"] != annotation_b[
        "message_observability"
    ]:
        reasons.append("message_observability")
    if semantic_slot_set(annotation_a) != semantic_slot_set(annotation_b):
        reasons.append("semantic_slots")
    return reasons


def build_adjudication_inputs(
    records_a: Iterable[dict[str, Any]], records_b: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for annotation_a, annotation_b in pair_annotations(records_a, records_b):
        reasons = disagreement_reasons(annotation_a, annotation_b)
        output.append(
            {
                "protocol_version": PROTOCOL_VERSION,
                "batch_id": BATCH_ID,
                "pilot_item_id": annotation_a["pilot_item_id"],
                "record_status": "ready",
                "disagreement_reasons": reasons,
                "annotation_a": annotation_a,
                "annotation_b": annotation_b,
                "adjudication_status": "pending",
            }
        )
    return output


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations-a", type=Path, required=True)
    parser.add_argument("--annotations-b", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--adjudication-input", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records_a = load_jsonl(args.annotations_a)
    records_b = load_jsonl(args.annotations_b)
    report = compute_agreement(records_a, records_b)
    final_review_inputs = build_adjudication_inputs(records_a, records_b)
    write_json(args.report, report)
    write_jsonl(args.adjudication_input, final_review_inputs)
    print(
        json.dumps(
            {
                "status": report["status"],
                "paired_items": report["paired_items"],
                "adjudication_items": len(final_review_inputs),
                "report": str(args.report),
                "adjudication_input": str(args.adjudication_input),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProtocolError as exc:
        raise SystemExit(f"protocol error: {exc}") from exc
