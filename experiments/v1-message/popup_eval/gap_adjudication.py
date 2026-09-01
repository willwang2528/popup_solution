"""Fail-closed, method-blind structure-versus-visual gap adjudication."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import re
from typing import Any

from .io import finalize_adjudication_batch


CONTRACT_VERSION = "popup-structure-visual-gap-adjudication-v1.0"
AUDIT_CONTRACT_VERSION = "popup-structure-visual-gap-audit-record-v1.0"
BATCH_ID = "popsweeper-message-pilot-30-gap-v1"
STRUCTURED_CONTRACT_VERSION = "pmj-pilot-structured-features-v1.0"
GAP_REASONS = {
    "missing",
    "merged",
    "ambiguous",
    "contradictory",
    "stale",
    "owner_mismatch",
    "visual_only_text",
    "host_text_contamination",
    "unknown",
}
ROW_KEYS = {
    "contract_version",
    "batch_id",
    "pilot_item_id",
    "record_status",
    "adjudicator_id_pseudonymous",
    "independent_audit_record_sha256",
    "audit_status",
    "structured_evidence_available",
    "structured_message_text_final",
    "structured_message_complete_final",
    "gap_reasons_final",
    "critical_facts_missing_from_structure_final",
    "host_text_contamination_final",
    "tree_screenshot_synchronized_final",
    "decision_rationale",
    "evidence_uris",
    "auditor_blind_to_method_outputs",
    "g1_gold_discrepancy_detected",
    "message_gold_batch_sha256",
    "structured_bundle_sha256",
    "adjudicated_at",
}
AUDIT_ROW_KEYS = {
    "contract_version",
    "batch_id",
    "pilot_item_id",
    "record_status",
    "auditor_slot",
    "auditor_id_pseudonymous",
    "human_auditor_attestation",
    "independent_of_peer_attestation",
    "auditor_blind_to_method_outputs",
    "g1_gold_discrepancy_flag",
    "g1_gold_discrepancy_notes",
    "message_gold_batch_sha256",
    "structured_bundle_sha256",
    "audit_status",
    "structured_evidence_available",
    "structured_candidate_ids",
    "structured_message_text",
    "structured_message_complete",
    "gap_reasons",
    "critical_facts_missing_from_structure",
    "host_text_contamination",
    "tree_screenshot_synchronized",
    "decision_rationale",
    "evidence_uris",
    "completed_at",
}
STRUCTURED_TOP_LEVEL_KEYS = {
    "identity",
    "observations",
    "candidates",
    "action_attempts",
    "decision",
    "metadata",
}


def _canonical_row(row: dict[str, Any]) -> bytes:
    return json.dumps(
        row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _canonical_jsonl_hash(rows: list[dict[str, Any]]) -> str:
    payload = b"".join(_canonical_row(row) + b"\n" for row in rows)
    return hashlib.sha256(payload).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _valid_timestamp(value: Any, field_name: str) -> None:
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise ValueError(f"{field_name} must be ISO-8601") from error
    if timestamp.tzinfo is None:
        raise ValueError(f"{field_name} requires timezone")


def _pilot_id(item: dict[str, Any]) -> str:
    pilot_id = item.get("identity", {}).get("pilot_item_id")
    if not isinstance(pilot_id, str) or re.fullmatch(r"PMJ-PILOT-\d{3}", pilot_id) is None:
        raise ValueError("gap audit item is missing a valid pilot_item_id")
    return pilot_id


def _exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    missing = sorted(expected - set(value))
    unexpected = sorted(set(value) - expected)
    if missing or unexpected:
        raise ValueError(f"{label} keys are invalid: missing={missing} unexpected={unexpected}")


def _validate_message_gold(
    items: list[dict[str, Any]], message_gold_rows: list[dict[str, Any]]
) -> tuple[str, dict[str, dict[str, Any]]]:
    try:
        finalized_rows, summary = finalize_adjudication_batch(items, message_gold_rows)
    except ValueError as error:
        raise ValueError(f"message gold batch is invalid: {error}") from error
    if summary["resolved_count"] != len(items):
        raise ValueError("message gold batch must resolve every gap-audit item")
    if any(
        row["presence_label_final"] not in {"popup", "no_popup"}
        for row in finalized_rows
    ):
        raise ValueError("message gold batch requires resolved popup/no-popup labels")
    by_id = {row["pilot_item_id"]: row for row in finalized_rows}
    batch_hash = summary["batch_sha256"]
    for item in items:
        pilot_id = _pilot_id(item)
        row = by_id[pilot_id]
        provenance = item.get("adjudication_provenance", {})
        if (
            provenance.get("adjudication_status") != "resolved"
            or provenance.get("adjudication_batch_sha256") != batch_hash
        ):
            raise ValueError("message gold batch hash does not match finalized items")
        labels = item.get("message_judgment", {}).get("labels", {})
        popup = row["presence_label_final"] == "popup"
        expected_facts = [slot["value"] for slot in row["semantic_slots_final"]]
        if (
            labels.get("popup_present_gt") is not popup
            or labels.get("message_text_gt") != row["message_text_final"]
            or labels.get("message_text_observability")
            != row["message_observability_final"]
            or labels.get("critical_facts_gt") != expected_facts
        ):
            raise ValueError("message gold rows do not match item labels")
    return batch_hash, by_id


def _validate_structured_row(row: dict[str, Any]) -> tuple[str, str, set[str]]:
    if not isinstance(row, dict):
        raise ValueError("structured bundle row must be an object")
    _exact_keys(row, STRUCTURED_TOP_LEVEL_KEYS, "structured bundle row")
    identity = row["identity"]
    _exact_keys(identity, {"item_id", "pilot_item_id", "record_kind"}, "structured identity")
    pilot_id = identity["pilot_item_id"]
    if (
        not isinstance(pilot_id, str)
        or re.fullmatch(r"PMJ-PILOT-\d{3}", pilot_id) is None
        or identity["item_id"] != pilot_id
        or identity["record_kind"] != "unscored_pregold_input"
    ):
        raise ValueError("structured bundle identity is invalid")

    metadata = row["metadata"]
    _exact_keys(
        metadata,
        {
            "contract_version",
            "gold_blind",
            "gold_used",
            "scored",
            "paper_result_eligible",
            "action_mode",
        },
        "structured metadata",
    )
    if metadata != {
        "contract_version": STRUCTURED_CONTRACT_VERSION,
        "gold_blind": True,
        "gold_used": False,
        "scored": False,
        "paper_result_eligible": False,
        "action_mode": "no_action",
    }:
        raise ValueError("structured bundle is not frozen gold-blind no-action evidence")
    if row["action_attempts"] != [] or row["decision"] != {
        "policy": {"decision": "no_action"}
    }:
        raise ValueError("structured bundle contains an action")

    observations = row["observations"]
    if not isinstance(observations, list) or len(observations) != 1:
        raise ValueError("structured bundle requires one pre-action observation")
    observation = observations[0]
    _exact_keys(
        observation,
        {"observation_id", "phase", "structured_representation"},
        "structured observation",
    )
    if observation["phase"] != "pre_action":
        raise ValueError("structured bundle observation must be pre-action")
    representation = observation["structured_representation"]
    _exact_keys(
        representation,
        {"availability", "representation_kind", "node_count", "artifact_sha256"},
        "structured representation",
    )
    availability = representation["availability"]
    if availability not in {"available", "missing"}:
        raise ValueError("structured bundle availability is invalid")

    candidates = row["candidates"]
    if not isinstance(candidates, list) or representation["node_count"] != len(candidates):
        raise ValueError("structured bundle node count is invalid")
    if availability == "missing":
        if candidates or representation["artifact_sha256"] is not None:
            raise ValueError("missing structured evidence cannot carry candidates")
    elif not _is_sha256(representation["artifact_sha256"]):
        raise ValueError("available structured evidence requires an artifact hash")

    candidate_ids: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise ValueError("structured candidate must be an object")
        _exact_keys(
            candidate,
            {"candidate_id", "source_channel", "normalized", "features"},
            "structured candidate",
        )
        candidate_id = candidate["candidate_id"]
        if (
            not isinstance(candidate_id, str)
            or not candidate_id.startswith(f"{pilot_id}-structured-")
            or candidate["source_channel"] != "structured"
            or not isinstance(candidate["normalized"], dict)
            or not isinstance(candidate["features"], dict)
        ):
            raise ValueError("structured candidate identity is invalid")
        if candidate_id in candidate_ids:
            raise ValueError("structured candidate IDs must be unique")
        candidate_ids.add(candidate_id)
    return pilot_id, availability, candidate_ids


def _validate_structured_bundle(
    rows: list[dict[str, Any]],
    expected_ids: set[str],
    expected_sha256: str,
) -> tuple[str, dict[str, tuple[str, set[str]]]]:
    if not _is_sha256(expected_sha256):
        raise ValueError("expected structured bundle commitment is invalid")
    by_id: dict[str, dict[str, Any]] = {}
    metadata: dict[str, tuple[str, set[str]]] = {}
    for raw_row in rows:
        row = deepcopy(raw_row)
        pilot_id, availability, candidate_ids = _validate_structured_row(row)
        if pilot_id in by_id:
            raise ValueError(f"structured bundle has duplicate pilot_item_id: {pilot_id}")
        by_id[pilot_id] = row
        metadata[pilot_id] = (availability, candidate_ids)
    actual_ids = set(by_id)
    if actual_ids - expected_ids:
        raise ValueError(f"structured bundle has unknown pilot_item_id values: {sorted(actual_ids - expected_ids)}")
    if expected_ids - actual_ids:
        raise ValueError(f"structured bundle is missing pilot_item_id values: {sorted(expected_ids - actual_ids)}")
    ordered = [by_id[pilot_id] for pilot_id in sorted(expected_ids)]
    actual_hash = _canonical_jsonl_hash(ordered)
    if actual_hash != expected_sha256:
        raise ValueError("structured bundle commitment does not match actual rows")
    return actual_hash, metadata


def _validate_evidence_fields(row: dict[str, Any], timestamp_field: str) -> None:
    rationale = row["decision_rationale"]
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("gap audit decision rationale is required")
    evidence = row["evidence_uris"]
    if (
        not isinstance(evidence, list)
        or len(evidence) < 2
        or not all(isinstance(uri, str) and uri.strip() for uri in evidence)
    ):
        raise ValueError("gap audit requires structured and visual evidence URIs")
    _valid_timestamp(row[timestamp_field], timestamp_field)


def _validate_payload(
    *,
    source: str,
    status: Any,
    available: Any,
    text: Any,
    complete: Any,
    reasons: Any,
    facts: Any,
    host_contamination: Any,
    synchronized: Any,
    candidate_ids: Any,
    popup: bool,
    gold_facts: list[str],
    bundle_availability: str,
    valid_candidate_ids: set[str],
) -> None:
    if status not in {"adjudicated", "cannot_resolve", "not_applicable"}:
        raise ValueError(f"{source} status is invalid")
    if not isinstance(reasons, list) or len(reasons) != len(set(reasons)) or not set(
        reasons
    ) <= GAP_REASONS:
        raise ValueError(f"{source} gap reasons are invalid")
    if (
        not isinstance(facts, list)
        or len(facts) != len(set(facts))
        or not all(isinstance(value, str) and value.strip() for value in facts)
    ):
        raise ValueError(f"{source} missing critical facts are invalid")
    if not set(facts) <= set(gold_facts):
        raise ValueError(f"{source} missing fact is not in message gold")
    if candidate_ids is not None:
        if (
            not isinstance(candidate_ids, list)
            or len(candidate_ids) != len(set(candidate_ids))
            or not all(isinstance(value, str) and value for value in candidate_ids)
            or not set(candidate_ids) <= valid_candidate_ids
        ):
            raise ValueError(f"{source} structured candidate reference is invalid")

    nullable_values = (available, text, complete, host_contamination, synchronized)
    if status in {"cannot_resolve", "not_applicable"}:
        if any(value is not None for value in nullable_values) or reasons or facts or (
            candidate_ids not in (None, [])
        ):
            raise ValueError(f"{source} {status} cannot carry final labels")
        if status == "not_applicable" and popup:
            raise ValueError(f"{source} not_applicable requires no-popup gold")
        if status == "cannot_resolve" and not popup:
            raise ValueError(f"{source} no-popup gold requires not_applicable")
        return

    if not popup:
        raise ValueError(f"{source} no-popup gold requires not_applicable")
    if not isinstance(available, bool) or not isinstance(complete, bool):
        raise ValueError(f"{source} adjudicated row requires availability and completeness")
    if not isinstance(host_contamination, bool):
        raise ValueError(f"{source} adjudicated row requires host-contamination decision")
    if synchronized is not True:
        raise ValueError(f"{source} unsynchronized evidence must be cannot_resolve")
    expected_available = bundle_availability == "available"
    if available is not expected_available:
        raise ValueError(f"{source} structured availability disagrees with frozen bundle")
    if text is not None and (not isinstance(text, str) or not text.strip()):
        raise ValueError(f"{source} structured message text is invalid")

    if not available:
        if text is not None or complete or candidate_ids not in (None, []) or "missing" not in reasons:
            raise ValueError(f"{source} missing structure labels are inconsistent")
    elif candidate_ids is not None and text is not None and not candidate_ids:
        raise ValueError(f"{source} structured text requires a candidate reference")

    if complete:
        if not available or not isinstance(text, str) or not text.strip():
            raise ValueError(f"{source} complete structured message requires text")
        if candidate_ids is not None and not candidate_ids:
            raise ValueError(f"{source} complete structured message requires a candidate")
        if reasons or facts or host_contamination:
            raise ValueError(f"{source} complete structured message cannot carry gap labels")
    elif not reasons:
        raise ValueError(f"{source} incomplete structured message requires a gap reason")
    if host_contamination and "host_text_contamination" not in reasons:
        raise ValueError(f"{source} host contamination requires its gap reason")


def _validate_audit_record(row: dict[str, Any]) -> None:
    _exact_keys(row, AUDIT_ROW_KEYS, "independent gap audit record")
    if row["contract_version"] != AUDIT_CONTRACT_VERSION or row["batch_id"] != BATCH_ID:
        raise ValueError("independent gap audit contract or batch is invalid")
    if row["record_status"] != "completed" or row["auditor_slot"] not in {"A", "B"}:
        raise ValueError("independent gap audit record status or slot is invalid")
    pilot_id = row["pilot_item_id"]
    if not isinstance(pilot_id, str) or re.fullmatch(r"PMJ-PILOT-\d{3}", pilot_id) is None:
        raise ValueError("independent gap audit pilot_item_id is invalid")
    auditor = row["auditor_id_pseudonymous"]
    if not isinstance(auditor, str) or not auditor.strip():
        raise ValueError("independent gap audit requires an auditor")
    for field in (
        "human_auditor_attestation",
        "independent_of_peer_attestation",
        "auditor_blind_to_method_outputs",
    ):
        if row[field] is not True:
            raise ValueError(f"independent gap audit {field} must be true")
    discrepancy = row["g1_gold_discrepancy_flag"]
    notes = row["g1_gold_discrepancy_notes"]
    if not isinstance(discrepancy, bool):
        raise ValueError("independent gap audit G1 gold discrepancy flag must be boolean")
    if discrepancy:
        if row["audit_status"] != "cannot_resolve":
            raise ValueError("G1 gold discrepancy requires cannot_resolve")
        if not isinstance(notes, str) or not notes.strip():
            raise ValueError("G1 gold discrepancy requires private notes")
    elif notes is not None:
        raise ValueError("G1 gold discrepancy notes require a discrepancy flag")
    if not _is_sha256(row["message_gold_batch_sha256"]):
        raise ValueError("independent gap audit message gold hash is invalid")
    if not _is_sha256(row["structured_bundle_sha256"]):
        raise ValueError("independent gap audit structured bundle hash is invalid")
    _validate_evidence_fields(row, "completed_at")


def _validate_final_row(row: dict[str, Any]) -> None:
    _exact_keys(row, ROW_KEYS, "gap adjudication row")
    if row["contract_version"] != CONTRACT_VERSION or row["batch_id"] != BATCH_ID:
        raise ValueError("gap adjudication contract or batch is invalid")
    if row["record_status"] != "completed":
        raise ValueError("gap adjudication row must be completed")
    pilot_id = row["pilot_item_id"]
    if not isinstance(pilot_id, str) or re.fullmatch(r"PMJ-PILOT-\d{3}", pilot_id) is None:
        raise ValueError("gap adjudication pilot_item_id is invalid")
    adjudicator = row["adjudicator_id_pseudonymous"]
    if not isinstance(adjudicator, str) or not adjudicator.strip():
        raise ValueError("gap adjudication requires an adjudicator")
    audit_hashes = row["independent_audit_record_sha256"]
    if (
        not isinstance(audit_hashes, list)
        or len(audit_hashes) != 2
        or len(set(audit_hashes)) != 2
        or not all(_is_sha256(value) for value in audit_hashes)
    ):
        raise ValueError("gap adjudication requires two independent audit hashes")
    if row["auditor_blind_to_method_outputs"] is not True:
        raise ValueError("gap adjudicator must be blind to method outputs")
    if not isinstance(row["g1_gold_discrepancy_detected"], bool):
        raise ValueError("gap adjudication G1 gold discrepancy flag must be boolean")
    if (
        row["g1_gold_discrepancy_detected"]
        and row["audit_status"] != "cannot_resolve"
    ):
        raise ValueError("G1 gold discrepancy requires cannot_resolve")
    if not _is_sha256(row["message_gold_batch_sha256"]):
        raise ValueError("gap adjudication message gold batch hash is invalid")
    if not _is_sha256(row["structured_bundle_sha256"]):
        raise ValueError("gap adjudication structured bundle hash is invalid")
    _validate_evidence_fields(row, "adjudicated_at")


def finalize_structure_visual_gap_audit(
    *,
    items: list[dict[str, Any]],
    message_gold_rows: list[dict[str, Any]],
    structured_feature_rows: list[dict[str, Any]],
    expected_structured_bundle_sha256: str,
    independent_audit_records: list[dict[str, Any]],
    adjudication_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Bind real gold, structure, two audits and final rows before updating items."""
    item_by_pilot: dict[str, dict[str, Any]] = {}
    for raw_item in items:
        item = deepcopy(raw_item)
        pilot_id = _pilot_id(item)
        if pilot_id in item_by_pilot:
            raise ValueError(f"gap audit has duplicate item pilot_item_id: {pilot_id}")
        item_by_pilot[pilot_id] = item
    if not item_by_pilot:
        raise ValueError("gap audit item batch is empty")
    expected_ids = set(item_by_pilot)

    message_gold_hash, message_by_id = _validate_message_gold(
        list(item_by_pilot.values()), message_gold_rows
    )
    structured_hash, structured_metadata = _validate_structured_bundle(
        structured_feature_rows, expected_ids, expected_structured_bundle_sha256
    )

    audit_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    auditor_ids_by_slot: dict[str, set[str]] = {"A": set(), "B": set()}
    for raw_record in independent_audit_records:
        record = deepcopy(raw_record)
        _validate_audit_record(record)
        key = (record["pilot_item_id"], record["auditor_slot"])
        if key in audit_by_key:
            raise ValueError(f"independent gap audit has duplicate item/slot: {key}")
        audit_by_key[key] = record
        auditor_ids_by_slot[record["auditor_slot"]].add(
            record["auditor_id_pseudonymous"]
        )
    expected_audit_keys = {(pilot_id, slot) for pilot_id in expected_ids for slot in ("A", "B")}
    actual_audit_keys = set(audit_by_key)
    if actual_audit_keys - expected_audit_keys:
        raise ValueError(f"independent gap audit has unknown item/slot values: {sorted(actual_audit_keys - expected_audit_keys)}")
    if expected_audit_keys - actual_audit_keys:
        raise ValueError(f"independent gap audit is missing item/slot values: {sorted(expected_audit_keys - actual_audit_keys)}")
    if any(len(values) != 1 for values in auditor_ids_by_slot.values()) or (
        auditor_ids_by_slot["A"] & auditor_ids_by_slot["B"]
    ):
        raise ValueError("gap audit requires two distinct human auditors across A and B")

    audit_hash_by_key: dict[tuple[str, str], str] = {}
    for key in sorted(expected_audit_keys):
        record = audit_by_key[key]
        pilot_id, _ = key
        if record["message_gold_batch_sha256"] != message_gold_hash:
            raise ValueError("independent audit message gold batch mismatch")
        if record["structured_bundle_sha256"] != structured_hash:
            raise ValueError("independent audit structured bundle mismatch")
        labels = item_by_pilot[pilot_id]["message_judgment"]["labels"]
        availability, candidate_ids = structured_metadata[pilot_id]
        _validate_payload(
            source="independent gap audit",
            status=record["audit_status"],
            available=record["structured_evidence_available"],
            text=record["structured_message_text"],
            complete=record["structured_message_complete"],
            reasons=record["gap_reasons"],
            facts=record["critical_facts_missing_from_structure"],
            host_contamination=record["host_text_contamination"],
            synchronized=record["tree_screenshot_synchronized"],
            candidate_ids=record["structured_candidate_ids"],
            popup=labels["popup_present_gt"],
            gold_facts=labels["critical_facts_gt"],
            bundle_availability=availability,
            valid_candidate_ids=candidate_ids,
        )
        audit_hash_by_key[key] = hashlib.sha256(_canonical_row(record)).hexdigest()

    row_by_pilot: dict[str, dict[str, Any]] = {}
    for raw_row in adjudication_rows:
        row = deepcopy(raw_row)
        _validate_final_row(row)
        pilot_id = row["pilot_item_id"]
        if pilot_id in row_by_pilot:
            raise ValueError(f"gap audit has duplicate pilot_item_id values: {pilot_id}")
        row_by_pilot[pilot_id] = row
    actual_ids = set(row_by_pilot)
    if actual_ids - expected_ids:
        raise ValueError(f"gap audit has unknown pilot_item_id values: {sorted(actual_ids - expected_ids)}")
    if expected_ids - actual_ids:
        raise ValueError(f"gap audit is missing pilot_item_id values: {sorted(expected_ids - actual_ids)}")

    all_auditor_ids = set().union(*auditor_ids_by_slot.values())
    for pilot_id in sorted(expected_ids):
        row = row_by_pilot[pilot_id]
        if row["adjudicator_id_pseudonymous"] in all_auditor_ids:
            raise ValueError("gap adjudicator must be distinct from both human auditors")
        expected_hashes = {
            audit_hash_by_key[(pilot_id, "A")],
            audit_hash_by_key[(pilot_id, "B")],
        }
        if set(row["independent_audit_record_sha256"]) != expected_hashes:
            raise ValueError("gap adjudication independent audit hash mismatch")
        independent_discrepancy = any(
            audit_by_key[(pilot_id, slot)]["g1_gold_discrepancy_flag"]
            for slot in ("A", "B")
        )
        if row["g1_gold_discrepancy_detected"] is not independent_discrepancy:
            raise ValueError(
                "gap adjudication G1 gold discrepancy disagrees with independent audits"
            )
        if row["message_gold_batch_sha256"] != message_gold_hash:
            raise ValueError("gap adjudication message gold batch mismatch")
        if row["structured_bundle_sha256"] != structured_hash:
            raise ValueError("gap adjudication structured bundle mismatch")
        labels = item_by_pilot[pilot_id]["message_judgment"]["labels"]
        availability, candidate_ids = structured_metadata[pilot_id]
        _validate_payload(
            source="gap adjudication",
            status=row["audit_status"],
            available=row["structured_evidence_available"],
            text=row["structured_message_text_final"],
            complete=row["structured_message_complete_final"],
            reasons=row["gap_reasons_final"],
            facts=row["critical_facts_missing_from_structure_final"],
            host_contamination=row["host_text_contamination_final"],
            synchronized=row["tree_screenshot_synchronized_final"],
            candidate_ids=None,
            popup=labels["popup_present_gt"],
            gold_facts=labels["critical_facts_gt"],
            bundle_availability=availability,
            valid_candidate_ids=candidate_ids,
        )

    ordered_rows = [row_by_pilot[pilot_id] for pilot_id in sorted(expected_ids)]
    gap_audit_hash = _canonical_jsonl_hash(ordered_rows)
    independent_batch_hashes = []
    for slot in ("A", "B"):
        slot_rows = [audit_by_key[(pilot_id, slot)] for pilot_id in sorted(expected_ids)]
        independent_batch_hashes.append(_canonical_jsonl_hash(slot_rows))

    updated_items: list[dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()
    gap_present_count = 0
    for pilot_id in sorted(expected_ids):
        item = item_by_pilot[pilot_id]
        row = row_by_pilot[pilot_id]
        gap = item["message_judgment"]["gap_ground_truth"]
        gap.update(
            {
                "status": row["audit_status"],
                "structured_evidence_available": row["structured_evidence_available"],
                "structured_message_text_gt": row["structured_message_text_final"],
                "structured_message_complete_gt": row[
                    "structured_message_complete_final"
                ],
                "gap_reasons_gt": list(row["gap_reasons_final"]),
                "critical_facts_missing_from_structure_gt": list(
                    row["critical_facts_missing_from_structure_final"]
                ),
                "host_text_contamination_gt": row[
                    "host_text_contamination_final"
                ],
                "tree_screenshot_synchronized_gt": row[
                    "tree_screenshot_synchronized_final"
                ],
                "auditor_blind_to_method_outputs": True,
                "message_gold_batch_sha256": message_gold_hash,
                "structured_bundle_sha256": structured_hash,
                "gap_audit_batch_sha256": gap_audit_hash,
                "evidence_uris": [{"uri": uri} for uri in row["evidence_uris"]],
            }
        )
        reason_counts.update(row["gap_reasons_final"])
        gap_present_count += int(
            row["audit_status"] == "adjudicated"
            and (
                row["structured_message_complete_final"] is False
                or row["host_text_contamination_final"] is True
            )
        )
        updated_items.append(item)

    return updated_items, {
        "contract_version": CONTRACT_VERSION,
        "status": "finalized_structure_visual_gap_audit",
        "scope": "popup_message_judgment_v1_subgroup_audit",
        "item_count": len(ordered_rows),
        "adjudicated_count": sum(
            row["audit_status"] == "adjudicated" for row in ordered_rows
        ),
        "cannot_resolve_count": sum(
            row["audit_status"] == "cannot_resolve" for row in ordered_rows
        ),
        "not_applicable_count": sum(
            row["audit_status"] == "not_applicable" for row in ordered_rows
        ),
        "gap_present_count": gap_present_count,
        "gap_reason_counts": dict(sorted(reason_counts.items())),
        "message_gold_batch_sha256": message_gold_hash,
        "structured_bundle_sha256": structured_hash,
        "independent_audit_batch_sha256": independent_batch_hashes,
        "gap_audit_batch_sha256": gap_audit_hash,
        "human_auditor_attestations_recorded": True,
        "method_outputs_used": False,
        "scored": False,
        "paper_result_eligible": False,
        "claims": {
            "empirical_performance": False,
            "method_superiority": False,
            "user_experience_improvement": False,
            "recovery_or_dismissal": False,
        },
    }
