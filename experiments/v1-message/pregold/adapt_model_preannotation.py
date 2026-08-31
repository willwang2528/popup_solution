#!/usr/bin/env python3
"""Isolate label-shaped AI preannotations from the gold-blind freeze contract."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

from freeze_predictions import (
    ContractError,
    _atomic_write,
    _canonical_jsonl,
    _validate_item_id,
    read_jsonl,
)


ALLOWED_ROOT_KEYS = {
    "adapter_item_handle",
    "ambiguity",
    "annotation_order",
    "annotator_id_pseudonymous",
    "annotator_type",
    "blindness_attestation",
    "blocking_label",
    "evidence",
    "message_observability",
    "message_text",
    "metric_eligible",
    "not_human_gold",
    "not_metric_eligible",
    "notes",
    "pilot_item_id",
    "presence_label",
    "record_status",
    "semantic_slots",
}


def _refuse(message: str) -> ContractError:
    return ContractError(f"adapter refuses input: {message}")


def _reject_hidden_gold(value: Any, context: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = key.casefold()
            if (
                "adjudicat" in lowered
                or "ground_truth" in lowered
                or lowered.endswith("_gt")
                or "metric_eligible" in lowered
                or "human_gold" in lowered
            ):
                raise _refuse(f"hidden unsafe field at {context}.{key}")
            _reject_hidden_gold(child, f"{context}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_hidden_gold(child, f"{context}[{index}]")


def _critical_facts(slots: Any) -> list[str] | None:
    if not isinstance(slots, list):
        return None
    result: list[str] = []
    for slot in slots:
        if not isinstance(slot, dict) or set(slot) != {"slot_type", "value", "polarity"}:
            return None
        value = slot.get("value")
        if not isinstance(value, str) or not value.strip():
            return None
        result.append(value.strip())
    return result


def adapt_row(row: dict[str, Any]) -> dict[str, Any]:
    unexpected = sorted(set(row) - ALLOWED_ROOT_KEYS)
    if unexpected:
        raise _refuse(f"unknown or unsafe root fields: {unexpected}")
    for key, value in row.items():
        if key not in {
            "presence_label",
            "metric_eligible",
            "not_human_gold",
            "not_metric_eligible",
        }:
            _reject_hidden_gold(value, f"$.{key}")
    if row.get("annotator_type") != "AI model":
        raise _refuse("annotator_type must be exactly 'AI model'")
    if row.get("not_human_gold") is not True:
        raise _refuse("not_human_gold must be true")
    if row.get("metric_eligible") is not False:
        raise _refuse("metric_eligible must be false")
    if "not_metric_eligible" in row and row["not_metric_eligible"] is not True:
        raise _refuse("not_metric_eligible must be true when present")
    if row.get("record_status") != "completed":
        raise _refuse("record_status must be completed")
    blindness_attestation = row.get("blindness_attestation")
    required_blindness = {
        "model_output_unseen",
        "peer_labels_unseen",
        "source_class_unseen",
    }
    if not isinstance(blindness_attestation, dict) or any(
        blindness_attestation.get(key) is not True for key in required_blindness
    ):
        raise _refuse(
            "blindness_attestation must set model_output_unseen, "
            "peer_labels_unseen, and source_class_unseen to true"
        )

    item_id = _validate_item_id(row.get("pilot_item_id"), "model preannotation")
    presence = row.get("presence_label")
    message = row.get("message_text")
    facts = _critical_facts(row.get("semantic_slots"))
    stable = presence in {"popup", "no_popup"} and facts is not None
    if presence == "popup":
        stable = stable and isinstance(message, str) and bool(message.strip())
    elif presence == "no_popup":
        stable = stable and message in {None, ""} and facts == []

    adapted = {
        "confidence": None,
        "critical_facts_pred": [],
        "evidence_kind": "model_workflow_visual_candidate",
        "formal_baseline": False,
        "human_gold_used": False,
        "message_text_pred": None,
        "model_identity_reproducible": False,
        "paper_result_eligible": False,
        "pilot_item_id": item_id,
        "popup_present_pred": None,
        "scored": False,
        "status": "abstain",
    }
    if stable:
        adapted.update(
            {
                "critical_facts_pred": facts if presence == "popup" else [],
                "message_text_pred": message.strip() if presence == "popup" else None,
                "popup_present_pred": presence == "popup",
                "status": "judged",
            }
        )
    return adapted


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Project AI-only, non-gold preannotations to private visual evidence."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if (
            args.private_output.parent.name != "private"
            or not args.private_output.name.endswith(".private.jsonl")
        ):
            raise _refuse(
                "private output must be under a private/ directory and end with .private.jsonl"
            )
        adapted = [adapt_row(row) for row in read_jsonl(args.input)]
        ids = [row["pilot_item_id"] for row in adapted]
        if len(ids) != len(set(ids)):
            raise _refuse("duplicate pilot_item_id")
        adapted.sort(key=lambda row: row["pilot_item_id"])
        _atomic_write(args.private_output, _canonical_jsonl(adapted))
    except (ContractError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
