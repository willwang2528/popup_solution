#!/usr/bin/env python3
"""Materialize private formal metric items from completed human G1/G2 outputs.

This module composes the existing G1 and G2 finalizers.  It does not infer,
repair, or synthesize human labels, and it never consumes predictions.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Mapping, Sequence


V1_ROOT = Path(__file__).resolve().parents[1]
if str(V1_ROOT) not in sys.path:
    sys.path.insert(0, str(V1_ROOT))

from popup_eval.formal_k50_runner import (  # noqa: E402
    _validate_adjudicated_items,
)
from popup_eval.gap_adjudication import (  # noqa: E402
    finalize_structure_visual_gap_audit,
)
from popup_eval.io import prepare_finalized_pilot_items, read_jsonl  # noqa: E402


CONTRACT_VERSION = "formal-adjudicated-metric-items-v1.1"
PILOT_ID_PATTERN = re.compile(r"PMJ-PILOT-\d{3}")
CAPTURE_ID_PATTERN = re.compile(r"PMAB-A-CAP-\d{3}")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
ACTION_BEARING_KEYS = {
    "action",
    "action_semantics",
    "click",
    "coordinate",
    "dismiss",
    "execution_channel",
    "selector",
    "target",
    "target_candidate_id",
}
PASSIVE_VALUES = {None, False, "", "not_applicable", "not_observable"}


class FormalItemMaterializerError(ValueError):
    """Raised when private human outputs cannot form a formal metric snapshot."""


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _canonical_jsonl(rows: Sequence[Mapping[str, Any]]) -> bytes:
    return b"".join(_canonical_json(row) + b"\n" for row in rows)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _is_passive(value: Any) -> bool:
    if isinstance(value, Mapping):
        return all(_is_passive(child) for child in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return all(_is_passive(child) for child in value)
    try:
        return value in PASSIVE_VALUES
    except TypeError:
        return False


def _reject_active_action_or_recovery(value: Any, context: str = "$") -> None:
    """Reject nested executable fields and any non-passive Recovery payload.

    Full union source items may contain passive, schema-required recovery
    containers whose leaves are null/not-observable.  They are accepted only
    as inert lifecycle placeholders and are omitted from the output projection.
    """

    if isinstance(value, Mapping):
        for key, child in value.items():
            lowered = key.casefold()
            child_context = f"{context}.{key}"
            if lowered in ACTION_BEARING_KEYS:
                raise FormalItemMaterializerError(
                    f"{child_context}: action or Recovery field is forbidden"
                )
            if "recovery" in lowered:
                if not _is_passive(child):
                    raise FormalItemMaterializerError(
                        f"{child_context}: action or Recovery field is forbidden"
                    )
                continue
            if lowered == "action_attempts" and child != []:
                raise FormalItemMaterializerError(
                    f"{child_context}: action or Recovery field is forbidden"
                )
            if lowered in {"action_policy", "action_mode"} and child != "no_action":
                raise FormalItemMaterializerError(
                    f"{child_context}: action or Recovery field is forbidden"
                )
            _reject_active_action_or_recovery(child, child_context)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, child in enumerate(value):
            _reject_active_action_or_recovery(child, f"{context}[{index}]")


def _pending_gap_skeleton() -> dict[str, Any]:
    return {
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
    }


def _capture_binding(raw_item: Mapping[str, Any], item_id: str) -> dict[str, Any]:
    provenance = raw_item.get("provenance")
    if not isinstance(provenance, Mapping):
        raise FormalItemMaterializerError(
            "formal metric source requires full-device CAP-001 provenance"
        )
    if (
        provenance.get("evidence_level") != "full_device_evidence"
        or provenance.get("source_origin") not in {"real_device", "emulator"}
        or provenance.get("privacy_review_status") != "passed"
    ):
        raise FormalItemMaterializerError(
            "formal metric source requires full-device CAP-001 provenance"
        )
    capture_id = provenance.get("collection_session_id")
    if not isinstance(capture_id, str) or CAPTURE_ID_PATTERN.fullmatch(capture_id) is None:
        raise FormalItemMaterializerError("formal metric source CAP-001 capture_id is invalid")

    raw_hashes = provenance.get("raw_capture_hashes")
    if not isinstance(raw_hashes, Mapping):
        raise FormalItemMaterializerError("formal metric source capture hashes are missing")
    required_hashes: dict[str, str] = {}
    for key in (
        "finalized_capture_record_sha256",
        "screenshot_sha256",
        "accessibility_snapshot_sha256",
    ):
        value = raw_hashes.get(key)
        if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
            raise FormalItemMaterializerError(
                f"formal metric source {key} must be a lowercase sha256"
            )
        required_hashes[key] = value

    versions = provenance.get("collector_and_model_versions")
    if not isinstance(versions, Mapping):
        raise FormalItemMaterializerError("formal metric source collector binding is missing")
    delta_ms = versions.get("capture_delta_ms")
    maximum_delta_ms = versions.get("maximum_delta_ms")
    if (
        versions.get("capture_schema_version") != "1.1.0"
        or versions.get("capture_status") != "eligible_for_capture_feasibility"
        or versions.get("collector_mode") != "accessibilityservice_node_snapshot"
        or versions.get("capture_item_id") != item_id
        or not isinstance(delta_ms, int)
        or isinstance(delta_ms, bool)
        or not isinstance(maximum_delta_ms, int)
        or isinstance(maximum_delta_ms, bool)
        or maximum_delta_ms != 3000
        or not 0 <= delta_ms <= maximum_delta_ms
        or versions.get("stable_state_verified") is not True
    ):
        raise FormalItemMaterializerError(
            "formal metric source does not satisfy the finalized CAP-001 collector binding"
        )

    expected_uri = f"capture-record://{capture_id}"
    artifacts = provenance.get("source_artifacts")
    if not isinstance(artifacts, list):
        raise FormalItemMaterializerError("formal metric source capture-record artifact is missing")
    matching = [
        artifact
        for artifact in artifacts
        if isinstance(artifact, Mapping)
        and artifact.get("uri") == expected_uri
        and artifact.get("capture_channel")
        == "android_accessibilityservice_finalized_record"
    ]
    if len(matching) != 1:
        raise FormalItemMaterializerError("formal metric source capture-record artifact is missing")
    if matching[0].get("sha256") != required_hashes["finalized_capture_record_sha256"]:
        raise FormalItemMaterializerError("formal metric source capture-record hash mismatch")

    return {
        "capture_id": capture_id,
        "capture_schema_version": "1.1.0",
        "capture_status": "eligible_for_capture_feasibility",
        "collector_mode": "accessibilityservice_node_snapshot",
        "source_origin": provenance["source_origin"],
        "privacy_review_status": "passed",
        "finalized_capture_record_sha256": required_hashes[
            "finalized_capture_record_sha256"
        ],
        "screenshot_sha256": required_hashes["screenshot_sha256"],
        "accessibility_snapshot_sha256": required_hashes[
            "accessibility_snapshot_sha256"
        ],
        "capture_delta_ms": delta_ms,
        "maximum_delta_ms": maximum_delta_ms,
        "stable_state_verified": True,
    }


def _sanitize_source_items(
    source_items: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if not isinstance(source_items, Sequence) or isinstance(
        source_items, (str, bytes)
    ) or not source_items:
        raise FormalItemMaterializerError("source item batch is empty")
    sanitized: list[dict[str, Any]] = []
    seen_pilot_ids: set[str] = set()
    seen_item_ids: set[str] = set()
    capture_bindings: dict[str, dict[str, Any]] = {}
    allowed_pending_reasons = {
        "adjudicated_gold_missing",
        "pending_human_annotation",
    }
    for index, raw_item in enumerate(source_items):
        if not isinstance(raw_item, Mapping):
            raise FormalItemMaterializerError(f"source_items[{index}] must be an object")
        _reject_active_action_or_recovery(raw_item, f"source_items[{index}]")
        identity = raw_item.get("identity")
        if not isinstance(identity, Mapping):
            raise FormalItemMaterializerError(f"source_items[{index}].identity is missing")
        item_id = identity.get("item_id")
        pilot_id = identity.get("pilot_item_id")
        if not isinstance(item_id, str) or not item_id:
            raise FormalItemMaterializerError("source item_id is missing")
        if (
            not isinstance(pilot_id, str)
            or PILOT_ID_PATTERN.fullmatch(pilot_id) is None
        ):
            raise FormalItemMaterializerError("source pilot_item_id is invalid")
        if identity.get("record_kind") != "real_app":
            raise FormalItemMaterializerError(
                "formal metric source must be a non-synthetic real_app item"
            )
        if item_id in seen_item_ids or pilot_id in seen_pilot_ids:
            raise FormalItemMaterializerError("source item identities are duplicated")
        seen_item_ids.add(item_id)
        seen_pilot_ids.add(pilot_id)
        capture_bindings[pilot_id] = _capture_binding(raw_item, item_id)

        if raw_item.get("action_attempts") != []:
            raise FormalItemMaterializerError("source item must be action-free")
        if raw_item.get("decision", {}).get("policy", {}).get("decision") != "no_action":
            raise FormalItemMaterializerError("source item decision must be no_action")
        source_reasons = raw_item.get("evaluation_exclusion_reasons", [])
        if (
            not isinstance(source_reasons, list)
            or not all(isinstance(reason, str) for reason in source_reasons)
            or not set(source_reasons) <= allowed_pending_reasons
        ):
            raise FormalItemMaterializerError(
                "source item has a non-annotation metric exclusion"
            )
        judgment = raw_item.get("message_judgment")
        if (
            not isinstance(judgment, Mapping)
            or judgment.get("profile") != "popup_message_judgment_v1"
        ):
            raise FormalItemMaterializerError("source item message profile is invalid")
        observations = raw_item.get("observations")
        if not isinstance(observations, list) or not observations:
            raise FormalItemMaterializerError("source item requires pre-action evidence")
        projected_observations: list[dict[str, Any]] = []
        for observation in observations:
            if not isinstance(observation, Mapping) or observation.get("phase") != "pre_action":
                raise FormalItemMaterializerError(
                    "source item accepts pre_action observations only"
                )
            observation_id = observation.get("observation_id")
            if not isinstance(observation_id, str) or not observation_id:
                raise FormalItemMaterializerError("source observation_id is missing")
            projected_observations.append(
                {"observation_id": observation_id, "phase": "pre_action"}
            )

        sanitized.append(
            {
                "identity": {
                    "item_id": item_id,
                    "pilot_item_id": pilot_id,
                    "record_kind": "real_app",
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
                    "gap_ground_truth": _pending_gap_skeleton(),
                },
                "observations": projected_observations,
                "candidates": [],
                "decision": {"policy": {"decision": "no_action"}},
                "action_attempts": [],
                "evaluation_exclusion_reasons": ["adjudicated_gold_missing"],
            }
        )
    return sanitized, capture_bindings


def _project_formal_item(
    item: Mapping[str, Any],
    *,
    g1_hash: str,
    g2_hash: str,
    structured_hash: str,
    capture_binding: Mapping[str, Any],
) -> dict[str, Any]:
    provenance = deepcopy(item["adjudication_provenance"])
    provenance.update(
        {
            "adjudication_batch_sha256": g1_hash,
            "gap_audit_batch_sha256": g2_hash,
            "structured_bundle_sha256": structured_hash,
            "gold_hash_scope": "human_finalization_rows_only",
            "prediction_independent": True,
            "capture_binding": deepcopy(dict(capture_binding)),
        }
    )
    return {
        "identity": deepcopy(item["identity"]),
        "message_judgment": {
            "profile": "popup_message_judgment_v1",
            "labels": deepcopy(item["message_judgment"]["labels"]),
            "gap_ground_truth": deepcopy(
                item["message_judgment"]["gap_ground_truth"]
            ),
        },
        "observations": deepcopy(item["observations"]),
        "candidates": [],
        "decision": {"policy": {"decision": "no_action"}},
        "action_attempts": [],
        "evaluation_exclusion_reasons": [],
        "adjudication_provenance": provenance,
    }


def materialize_formal_metric_items(
    *,
    source_items: Sequence[Mapping[str, Any]],
    g1_adjudication_rows: Sequence[Mapping[str, Any]],
    structured_feature_rows: Sequence[Mapping[str, Any]],
    expected_structured_bundle_sha256: str,
    g2_independent_audit_records: Sequence[Mapping[str, Any]],
    g2_adjudication_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return a full-coverage, message-only snapshot and aggregate private summary."""

    for label, rows in (
        ("g1_adjudication_rows", g1_adjudication_rows),
        ("structured_feature_rows", structured_feature_rows),
        ("g2_independent_audit_records", g2_independent_audit_records),
        ("g2_adjudication_rows", g2_adjudication_rows),
    ):
        if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
            raise FormalItemMaterializerError(f"{label} is empty")
        _reject_active_action_or_recovery(rows, label)

    sanitized, capture_bindings = _sanitize_source_items(source_items)
    try:
        g1_items, _, g1_summary = prepare_finalized_pilot_items(
            sanitized, [deepcopy(dict(row)) for row in g1_adjudication_rows]
        )
    except ValueError as error:
        raise FormalItemMaterializerError(str(error)) from error
    item_count = len(sanitized)
    if (
        g1_summary.get("item_count") != item_count
        or g1_summary.get("resolved_count") != item_count
        or g1_summary.get("metric_eligible_count") != item_count
        or g1_summary.get("out_of_scope_count") != 0
    ):
        raise FormalItemMaterializerError(
            "all G1 rows must be resolved popup/no_popup and metric-eligible"
        )

    if any(
        row.get("g1_gold_discrepancy_flag") is True
        for row in g2_independent_audit_records
    ) or any(
        row.get("g1_gold_discrepancy_detected") is True
        for row in g2_adjudication_rows
    ):
        raise FormalItemMaterializerError(
            "G2 found a G1 discrepancy; versioned G1 correction and full G2 restart are required"
        )

    try:
        g2_items, g2_summary = finalize_structure_visual_gap_audit(
            items=g1_items,
            message_gold_rows=[deepcopy(dict(row)) for row in g1_adjudication_rows],
            structured_feature_rows=[
                deepcopy(dict(row)) for row in structured_feature_rows
            ],
            expected_structured_bundle_sha256=expected_structured_bundle_sha256,
            independent_audit_records=[
                deepcopy(dict(row)) for row in g2_independent_audit_records
            ],
            adjudication_rows=[deepcopy(dict(row)) for row in g2_adjudication_rows],
        )
    except ValueError as error:
        raise FormalItemMaterializerError(str(error)) from error
    if g2_summary.get("item_count") != item_count:
        raise FormalItemMaterializerError("G2 finalization does not cover every source item")

    g1_hash = g1_summary["batch_sha256"]
    g2_hash = g2_summary["gap_audit_batch_sha256"]
    structured_hash = g2_summary["structured_bundle_sha256"]
    projected = [
        _project_formal_item(
            item,
            g1_hash=g1_hash,
            g2_hash=g2_hash,
            structured_hash=structured_hash,
            capture_binding=capture_bindings[item["identity"]["pilot_item_id"]],
        )
        for item in sorted(
            g2_items, key=lambda row: row["identity"]["pilot_item_id"]
        )
    ]
    _reject_active_action_or_recovery(projected, "formal_metric_items")
    try:
        validated_by_pilot, validated_gold_hash, validated_batch_id = (
            _validate_adjudicated_items(projected)
        )
    except ValueError as error:
        raise FormalItemMaterializerError(
            f"formal runner rejected materialized items: {error}"
        ) from error
    if len(validated_by_pilot) != item_count or validated_gold_hash != g1_hash:
        raise FormalItemMaterializerError("formal runner coverage or gold hash mismatch")

    payload = _canonical_jsonl(projected)
    capture_binding_rows = [
        {
            "pilot_item_id": pilot_id,
            **binding,
        }
        for pilot_id, binding in sorted(capture_bindings.items())
    ]
    summary = {
        "contract_version": CONTRACT_VERSION,
        "status": "formal_adjudicated_metric_items_ready",
        "scope": "popup_message_judgment_v1_no_action",
        "item_count": item_count,
        "metric_eligible_count": item_count,
        "coverage": {
            "source_items": item_count,
            "g1_final_rows": len(g1_adjudication_rows),
            "g2_independent_rows": len(g2_independent_audit_records),
            "g2_final_rows": len(g2_adjudication_rows),
            "g1_complete": True,
            "g2_complete": True,
        },
        "hashes": {
            "g1_human_finalization_sha256": g1_hash,
            "g2_human_finalization_sha256": g2_hash,
            "structured_bundle_sha256": structured_hash,
            "formal_metric_items_sha256": _sha256(payload),
            "capture_bindings_sha256": _sha256(
                _canonical_jsonl(capture_binding_rows)
            ),
        },
        "hash_scope": {
            "g1_human_finalization_sha256": (
                "canonical G1 final-adjudication rows only"
            ),
            "g2_human_finalization_sha256": (
                "canonical G2 final-adjudication rows bound to G1 and structure hashes"
            ),
            "formal_metric_items_sha256": "canonical projected metric-item rows",
            "capture_bindings_sha256": (
                "canonical pilot-item to finalized CAP-001 binding rows"
            ),
        },
        "g1_batch_id": validated_batch_id,
        "g2_status_counts": {
            "adjudicated": g2_summary["adjudicated_count"],
            "cannot_resolve": g2_summary["cannot_resolve_count"],
            "not_applicable": g2_summary["not_applicable_count"],
        },
        "predictions_used": False,
        "source_item_payload_used_in_gold_hashes": False,
        "action_policy": "no_action",
        "recovery_evaluated": False,
        "scored": False,
        "paper_result_eligible": False,
        "claims": {
            "empirical_performance": False,
            "method_superiority": False,
            "user_experience_improvement": False,
            "recovery_or_dismissal": False,
        },
    }
    return projected, summary


def _require_private_input(path: Path) -> None:
    if "private" not in path.parts or not path.name.endswith(".private.jsonl"):
        raise FormalItemMaterializerError(
            f"input {path.name} must be a *.private.jsonl file under a private directory"
        )


def _require_private_output(path: Path, suffix: str) -> None:
    if path.parent.name != "private" or not path.name.endswith(suffix):
        raise FormalItemMaterializerError(
            f"output {path.name} must end with {suffix} under a private directory"
        )
    if path.exists():
        raise FormalItemMaterializerError(
            f"output {path.name} already exists; replacement is forbidden"
        )


def _write_private_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o600)
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise FormalItemMaterializerError(
                f"output {path.name} already exists; replacement is forbidden"
            ) from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _write_private_pair_new(
    items_path: Path,
    items_payload: bytes,
    summary_path: Path,
    summary_payload: bytes,
) -> None:
    _require_private_output(items_path, ".private.jsonl")
    _require_private_output(summary_path, ".private.json")
    created_items = False
    try:
        _write_private_new(items_path, items_payload)
        created_items = True
        _write_private_new(summary_path, summary_payload)
    except Exception:
        if created_items:
            items_path.unlink(missing_ok=True)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-items", required=True, type=Path)
    parser.add_argument("--g1-adjudications", required=True, type=Path)
    parser.add_argument("--structured-features", required=True, type=Path)
    parser.add_argument("--structured-bundle-sha256", required=True)
    parser.add_argument("--g2-independent-audits", required=True, type=Path)
    parser.add_argument("--g2-adjudications", required=True, type=Path)
    parser.add_argument("--output-items", required=True, type=Path)
    parser.add_argument("--output-summary", required=True, type=Path)
    parser.add_argument("--expected-count", required=True, type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.expected_count <= 0:
            raise FormalItemMaterializerError("expected-count must be positive")
        input_paths = (
            args.source_items,
            args.g1_adjudications,
            args.structured_features,
            args.g2_independent_audits,
            args.g2_adjudications,
        )
        for path in input_paths:
            _require_private_input(path)
        _require_private_output(args.output_items, ".private.jsonl")
        _require_private_output(args.output_summary, ".private.json")
        items, summary = materialize_formal_metric_items(
            source_items=read_jsonl(args.source_items),
            g1_adjudication_rows=read_jsonl(args.g1_adjudications),
            structured_feature_rows=read_jsonl(args.structured_features),
            expected_structured_bundle_sha256=args.structured_bundle_sha256,
            g2_independent_audit_records=read_jsonl(args.g2_independent_audits),
            g2_adjudication_rows=read_jsonl(args.g2_adjudications),
        )
        if len(items) != args.expected_count:
            raise FormalItemMaterializerError(
                f"expected {args.expected_count} items, materialized {len(items)}"
            )
        _write_private_pair_new(
            args.output_items,
            _canonical_jsonl(items),
            args.output_summary,
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True).encode(
                "utf-8"
            )
            + b"\n",
        )
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "status": summary["status"],
                "item_count": summary["item_count"],
                "metric_eligible_count": summary["metric_eligible_count"],
                "predictions_used": False,
                "paper_result_eligible": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
