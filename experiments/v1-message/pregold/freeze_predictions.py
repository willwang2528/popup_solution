#!/usr/bin/env python3
"""Freeze gold-blind, action-free, unscored popup-message predictions."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Iterable

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

from popup_eval.the_ok_baseline import (  # noqa: E402 - direct-script import path
    TheOkTextBaseline,
    UPSTREAM_REVISION as THE_OK_UPSTREAM_REVISION,
)
from popup_eval.metrics import normalize_text  # noqa: E402 - shared A1 contract

CONTRACT_VERSION = "popup-message-pregold-v1.0"
METHOD_IDS = (
    "structured-only-v1",
    "the-ok-text-rule",
    "c1-always-on-fusion-v1",
    "c1-budget-matched-fusion-v1",
    "mg-pu-gated-union-v1",
)
C1_BUDGET_MATCH_SEED = 17
ITEM_ID_PATTERN = re.compile(r"PMJ-PILOT-\d{3}")
GAP_REASONS = {
    "ambiguous",
    "contradictory",
    "merged",
    "missing",
    "non_actionable",
    "owner_mismatch",
    "stale",
    "unknown",
    "visual_only_text",
}
SAFE_ATTESTATIONS = {
    "gold_blind": True,
    "gold_used": False,
    "human_gold_used": False,
    "scored": False,
    "paper_result_eligible": False,
}
FORBIDDEN_EXACT_KEYS = {
    "adjudicator_id_pseudonymous",
    "annotations",
    "archive_member",
    "archive_member_path",
    "artifacts",
    "batch_id",
    "content_key",
    "eligible_for_v1_message_metrics",
    "eligible_for_v1_presence_metric",
    "eligibility",
    "labels",
    "message_annotation_status",
    "metric_eligible",
    "not_human_gold",
    "official_split",
    "official_split_audit_stratum",
    "presence_label",
    "provenance",
    "record_status",
    "sampling_stratum",
    "source_label",
    "source_kind",
    "source_provenance",
    "source_record_id",
    "source_sampling_label",
    "group_key",
}


class ContractError(ValueError):
    """Raised when an input could contaminate the pre-gold freeze."""


class DuplicateKeyError(ContractError):
    """Raised for ambiguous JSON objects."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line, object_pairs_hook=_strict_object)
        except Exception as error:  # retain local line context without echoing content
            raise ContractError(f"{path.name}:{line_number}: invalid JSON: {error}") from error
        if not isinstance(row, dict):
            raise ContractError(f"{path.name}:{line_number}: row must be an object")
        rows.append(row)
    if not rows:
        raise ContractError(f"{path.name}: input is empty")
    return rows


def _canonical_jsonl(rows: Iterable[dict[str, Any]]) -> bytes:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    ).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _atomic_write(path: Path, payload: bytes, *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.name == "private" and mode == 0o600:
        path.parent.chmod(0o700)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(payload)
    temporary.chmod(mode)
    temporary.replace(path)


def _validate_item_id(value: Any, context: str) -> str:
    if not isinstance(value, str) or ITEM_ID_PATTERN.fullmatch(value) is None:
        raise ContractError(f"{context}: invalid pilot_item_id")
    return value


def _is_forbidden_key(key: str) -> bool:
    lowered = key.casefold()
    if key in FORBIDDEN_EXACT_KEYS:
        return True
    if key == "component_label":
        return False
    if lowered.endswith("_gt") or "ground_truth" in lowered:
        return True
    if "adjudicat" in lowered:
        return True
    if lowered == "label" or lowered.endswith("_label"):
        return True
    if "stratum" in lowered:
        return True
    if lowered.startswith("eligible_for_") or ("metric" in lowered and "eligible" in lowered):
        return True
    if "gold" in lowered:
        return key not in SAFE_ATTESTATIONS
    return False


def _reject_forbidden_keys(value: Any, context: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_context = f"{context}.{key}"
            if key in SAFE_ATTESTATIONS:
                expected = SAFE_ATTESTATIONS[key]
                if child is not expected:
                    raise ContractError(
                        f"{child_context}: safe attestation must be {expected!r}"
                    )
            elif _is_forbidden_key(key):
                raise ContractError(f"{child_context}: forbidden label/gold/metric key")
            _reject_forbidden_keys(child, child_context)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_keys(child, f"{context}[{index}]")


def _validate_feature_row(row: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    _reject_forbidden_keys(row)
    identity = row.get("identity")
    if not isinstance(identity, dict):
        raise ContractError("feature row requires identity")
    item_id = _validate_item_id(identity.get("pilot_item_id"), "feature identity")
    if identity.get("item_id") != item_id:
        raise ContractError(f"{item_id}: identity.item_id must equal pilot_item_id")
    if identity.get("record_kind") != "unscored_pregold_input":
        raise ContractError(f"{item_id}: record_kind must be unscored_pregold_input")

    metadata = row.get("metadata")
    if not isinstance(metadata, dict):
        raise ContractError(f"{item_id}: metadata is required")
    required_attestations = {
        "gold_blind": True,
        "gold_used": False,
        "scored": False,
        "paper_result_eligible": False,
        "action_mode": "no_action",
    }
    for key, expected in required_attestations.items():
        if metadata.get(key) != expected:
            raise ContractError(f"{item_id}: metadata.{key} must be {expected!r}")

    if row.get("action_attempts") != []:
        raise ContractError(f"{item_id}: action_attempts must be empty")
    decision = row.get("decision", {}).get("policy", {}).get("decision")
    if decision != "no_action":
        raise ContractError(f"{item_id}: decision must be no_action")

    observations = row.get("observations")
    if not isinstance(observations, list):
        raise ContractError(f"{item_id}: observations must be an array")
    for observation in observations:
        if not isinstance(observation, dict) or observation.get("phase") != "pre_action":
            raise ContractError(f"{item_id}: only pre_action observations are allowed")

    candidates = row.get("candidates")
    if not isinstance(candidates, list):
        raise ContractError(f"{item_id}: candidates must be an array")
    for candidate in candidates:
        if not isinstance(candidate, dict) or candidate.get("source_channel") != "structured":
            raise ContractError(f"{item_id}: candidates must be structured evidence")
        if not isinstance(candidate.get("normalized"), dict):
            raise ContractError(f"{item_id}: candidate.normalized must be an object")
        if not isinstance(candidate.get("features", {}), dict):
            raise ContractError(f"{item_id}: candidate.features must be an object")
    return item_id, row


def _rows_by_feature_id(
    rows: list[dict[str, Any]], expected_count: int
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        item_id, validated = _validate_feature_row(row)
        if item_id in result:
            raise ContractError(f"duplicate feature pilot_item_id: {item_id}")
        result[item_id] = validated
    if len(result) != expected_count:
        raise ContractError(
            f"feature item count {len(result)} does not match expected_count {expected_count}"
        )
    return result


def _manifest_ids_only(rows: list[dict[str, Any]]) -> set[str]:
    """Project a raw manifest to IDs; all other fields are deliberately unread."""
    result: set[str] = set()
    for row in rows:
        item_id = _validate_item_id(row.get("pilot_item_id"), "manifest row")
        if item_id in result:
            raise ContractError(f"duplicate manifest pilot_item_id: {item_id}")
        result.add(item_id)
    return result


def _normalize_visual_row(row: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    _reject_forbidden_keys(row)
    item_id = _validate_item_id(
        row.get("pilot_item_id") or row.get("item_id"), "visual prediction"
    )
    status = row.get("status")
    popup_present = row.get("popup_present_pred")
    message = row.get("message_text_pred")
    facts = row.get("critical_facts_pred", [])
    confidence = row.get("confidence")
    stable = status == "judged" and isinstance(popup_present, bool)
    stable = stable and isinstance(facts, list) and all(isinstance(fact, str) for fact in facts)
    stable = stable and (
        confidence is None
        or (
            isinstance(confidence, (int, float))
            and not isinstance(confidence, bool)
            and 0 <= confidence <= 1
        )
    )
    if popup_present is True:
        stable = stable and isinstance(message, str) and bool(message.strip())
    elif popup_present is False:
        stable = stable and message is None and facts == []
    if not stable:
        return item_id, {
            "status": "abstain",
            "popup_present_pred": None,
            "message_text_pred": None,
            "critical_facts_pred": [],
            "confidence": None,
        }
    return item_id, {
        "status": "judged",
        "popup_present_pred": popup_present,
        "message_text_pred": message.strip() if isinstance(message, str) else None,
        "critical_facts_pred": [fact.strip() for fact in facts if fact.strip()],
        "confidence": confidence,
    }


def _rows_by_visual_id(
    rows: list[dict[str, Any]], feature_ids: set[str]
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        item_id, normalized = _normalize_visual_row(row)
        if item_id not in feature_ids:
            raise ContractError(f"visual prediction has unknown pilot_item_id: {item_id}")
        if item_id in result:
            raise ContractError(f"duplicate visual pilot_item_id: {item_id}")
        result[item_id] = normalized
    return result


def _text_key(value: str) -> str:
    return normalize_text(value)


def _structured_message(feature: dict[str, Any]) -> tuple[str | None, list[str]]:
    fragments: list[str] = []
    seen: set[str] = set()
    gap_reasons: set[str] = set()
    for candidate in feature["candidates"]:
        normalized = candidate["normalized"]
        features = candidate.get("features", {})
        if normalized.get("visible") is False:
            continue
        for reason in features.get("gap_reasons", []):
            if reason in GAP_REASONS:
                gap_reasons.add(reason)
        for field in ("name_or_text", "value_or_hint"):
            value = normalized.get(field)
            if not isinstance(value, str) or not value.strip():
                continue
            cleaned = value.strip()
            key = _text_key(cleaned)
            if key not in seen:
                seen.add(key)
                fragments.append(cleaned)
    message = " ".join(fragments) or None
    if message is None:
        gap_reasons.add("missing")
    for observation in feature["observations"]:
        representation = observation.get("structured_representation", {})
        if representation.get("availability") == "missing" or representation.get("node_count") == 0:
            gap_reasons.add("missing")
    return message, sorted(gap_reasons)


def _marker_texts(candidate: dict[str, Any]) -> list[str]:
    features = candidate.get("features", {})
    values: list[str] = []
    for value in (features.get("component_label"), features.get("class")):
        if isinstance(value, str):
            values.append(value)
    ancestors = features.get("ancestors", [])
    if isinstance(ancestors, list):
        for ancestor in ancestors:
            if isinstance(ancestor, str):
                values.append(ancestor)
            elif isinstance(ancestor, dict):
                values.extend(value for value in ancestor.values() if isinstance(value, str))
    return values


def _candidate_has_popup_scope(candidate: dict[str, Any]) -> bool:
    features = candidate.get("features", {})
    component_label = features.get("component_label")
    if isinstance(component_label, str) and component_label.casefold() in {
        "modal",
        "advertisement",
    }:
        return True
    return any(
        marker in value.casefold()
        for value in _marker_texts(candidate)
        for marker in ("dialog", "popup", "overlay")
    )


def _popup_scoped_message(feature: dict[str, Any]) -> tuple[str | None, list[str]]:
    scoped = [candidate for candidate in feature["candidates"] if _candidate_has_popup_scope(candidate)]
    if not scoped:
        return None, ["ambiguous"]
    projected = dict(feature)
    projected["candidates"] = scoped
    message, gaps = _structured_message(projected)
    if message is None and "missing" not in gaps:
        gaps.append("missing")
    return message, sorted(set(gaps))


def _prediction(
    item_id: str,
    method_id: str,
    *,
    status: str,
    popup_present: bool | None,
    message: str | None,
    facts: list[str] | None = None,
    confidence: float | None = None,
    visual_called: bool,
    route_reason: str,
) -> dict[str, Any]:
    return {
        "action_policy": "no_action",
        "confidence": confidence,
        "critical_facts_pred": list(facts or []),
        "human_gold_used": False,
        "message_text_pred": message,
        "method_id": method_id,
        "paper_result_eligible": False,
        "pilot_item_id": item_id,
        "popup_present_pred": popup_present,
        "route_reason": route_reason,
        "scored": False,
        "status": status,
        "visual_called": visual_called,
    }


def _structured_prediction(item_id: str, feature: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    message, gaps = _structured_message(feature)
    if message is None:
        return (
            _prediction(
                item_id,
                "structured-only-v1",
                status="abstain",
                popup_present=None,
                message=None,
                confidence=None,
                visual_called=False,
                route_reason="structured_message_missing",
            ),
            gaps,
        )
    return (
        _prediction(
            item_id,
            "structured-only-v1",
            status="judged",
            popup_present=True,
            message=message,
            confidence=0.65,
            visual_called=False,
            route_reason="structured_message_available",
        ),
        gaps,
    )


def _fusion_prediction(
    item_id: str,
    method_id: str,
    scoped_message: str | None,
    gaps: list[str],
    visual: dict[str, Any] | None,
    *,
    visual_called: bool,
) -> dict[str, Any]:
    if visual_called and visual is not None and visual["status"] == "judged":
        return _prediction(
            item_id,
            method_id,
            status="judged",
            popup_present=visual["popup_present_pred"],
            message=visual["message_text_pred"],
            facts=visual["critical_facts_pred"],
            confidence=visual["confidence"],
            visual_called=True,
            route_reason="visual_frozen_prediction",
        )
    if not gaps and scoped_message is not None:
        return _prediction(
            item_id,
            method_id,
            status="judged",
            popup_present=True,
            message=scoped_message,
            confidence=0.65,
            visual_called=visual_called,
            route_reason=(
                "visual_abstain_structured_fallback"
                if visual_called
                else "budget_not_selected_structured_sufficient"
            ),
        )
    return _prediction(
        item_id,
        method_id,
        status="abstain",
        popup_present=None,
        message=None,
        confidence=None,
        visual_called=visual_called,
        route_reason=(
            "visual_evidence_missing_or_unstable"
            if visual_called
            else "budget_not_selected_structure_insufficient"
        ),
    )


def _c1_budget_selection(item_ids: list[str], k: int) -> set[str]:
    if not 0 <= k <= len(item_ids):
        raise ContractError("C1 budget-match K is outside the item set")
    ordered = sorted(
        item_ids,
        key=lambda item_id: hashlib.sha256(
            f"c1-budget-matched-fusion-v1|{C1_BUDGET_MATCH_SEED}|{item_id}".encode()
        ).hexdigest(),
    )
    return set(ordered[:k])


def freeze_predictions(
    features_by_id: dict[str, dict[str, Any]],
    visual_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    structured_predictions: list[dict[str, Any]] = []
    gated_predictions: list[dict[str, Any]] = []
    the_ok_predictions: list[dict[str, Any]] = []
    contexts: dict[str, tuple[str | None, list[str], dict[str, Any] | None]] = {}
    the_ok = TheOkTextBaseline()
    for item_id in sorted(features_by_id):
        feature = features_by_id[item_id]
        structured, _ = _structured_prediction(item_id, feature)
        structured_predictions.append(structured)
        the_ok_result = the_ok.predict(feature)
        the_ok_predictions.append(
            _prediction(
                item_id,
                "the-ok-text-rule",
                status=the_ok_result["status"],
                popup_present=the_ok_result["popup_present_pred"],
                message=the_ok_result["message_text_pred"],
                confidence=the_ok_result["confidence"],
                visual_called=False,
                route_reason=the_ok_result["route_reason"],
            )
        )
        scoped_message, gaps = _popup_scoped_message(feature)
        visual = visual_by_id.get(item_id)
        contexts[item_id] = (scoped_message, gaps, visual)
        if not gaps:
            gated_predictions.append(
                _prediction(
                    item_id,
                    "mg-pu-gated-union-v1",
                    status="judged",
                    popup_present=True,
                    message=scoped_message,
                    confidence=0.65,
                    visual_called=False,
                    route_reason="popup_scoped_structure_sufficient",
                )
            )
            continue
        if visual is not None and visual["status"] == "judged":
            gated_predictions.append(
                _prediction(
                    item_id,
                    "mg-pu-gated-union-v1",
                    status="judged",
                    popup_present=visual["popup_present_pred"],
                    message=visual["message_text_pred"],
                    facts=visual["critical_facts_pred"],
                    confidence=visual["confidence"],
                    visual_called=True,
                    route_reason="visual_frozen_prediction",
                )
            )
        else:
            gated_predictions.append(
                _prediction(
                    item_id,
                    "mg-pu-gated-union-v1",
                    status="abstain",
                    popup_present=None,
                    message=None,
                    confidence=None,
                    visual_called=True,
                    route_reason="visual_evidence_missing_or_unstable",
                )
            )
    mg_pu_visual_calls = sum(row["visual_called"] for row in gated_predictions)
    selected = _c1_budget_selection(sorted(features_by_id), mg_pu_visual_calls)
    always_on_predictions: list[dict[str, Any]] = []
    budget_matched_predictions: list[dict[str, Any]] = []
    for item_id in sorted(features_by_id):
        scoped_message, gaps, visual = contexts[item_id]
        always_on_predictions.append(
            _fusion_prediction(
                item_id,
                "c1-always-on-fusion-v1",
                scoped_message,
                gaps,
                visual,
                visual_called=True,
            )
        )
        budget_matched_predictions.append(
            _fusion_prediction(
                item_id,
                "c1-budget-matched-fusion-v1",
                scoped_message,
                gaps,
                visual,
                visual_called=item_id in selected,
            )
        )
    return (
        structured_predictions
        + the_ok_predictions
        + always_on_predictions
        + budget_matched_predictions
        + gated_predictions
    )


def _method_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(row["status"] for row in rows)
    route_counts = Counter(row["route_reason"] for row in rows)
    payload = _canonical_jsonl(rows)
    return {
        "abstain_count": status_counts.get("abstain", 0),
        "item_count": len(rows),
        "judged_count": status_counts.get("judged", 0),
        "predictions_sha256": _sha256(payload),
        "route_counts": dict(sorted(route_counts.items())),
        "visual_call_count": sum(bool(row["visual_called"]) for row in rows),
        "visual_adapter_invocation_count": sum(
            bool(row["visual_called"]) for row in rows
        ),
        "visual_informed_positive_judgment_count": sum(
            row["visual_called"]
            and row["status"] == "judged"
            and row["route_reason"] == "visual_frozen_prediction"
            and row["popup_present_pred"] is True
            for row in rows
        ),
    }


def build_public_summary(
    feature_rows: list[dict[str, Any]],
    visual_rows: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
) -> dict[str, Any]:
    feature_ids = sorted(row["identity"]["pilot_item_id"] for row in feature_rows)
    methods = {
        method_id: _method_summary(
            [row for row in predictions if row["method_id"] == method_id]
        )
        for method_id in METHOD_IDS
    }
    budget_rows = [
        row for row in predictions if row["method_id"] == "c1-budget-matched-fusion-v1"
    ]
    selected_ids = sorted(
        row["pilot_item_id"] for row in budget_rows if row["visual_called"]
    )
    if methods["c1-budget-matched-fusion-v1"]["visual_call_count"] != methods[
        "mg-pu-gated-union-v1"
    ]["visual_call_count"]:
        raise ContractError("C1-BM visual-call count does not match MG-PU K")
    model_workflow_candidate = bool(visual_rows) and all(
        row.get("evidence_kind") == "model_workflow_visual_candidate"
        and row.get("fixed_threshold_heuristic_adaptation") is False
        and row.get("repeat_execution_byte_identical_on_fixed_host") is False
        and row.get("cross_os_or_device_model_identity_reproducible")
        == "not_verified"
        for row in visual_rows
    )
    frozen_heuristic_bank = bool(visual_rows) and all(
        row.get("evidence_kind") == "frozen_private_visual_evidence_bank"
        and row.get("fixed_threshold_heuristic_adaptation") is True
        and row.get("repeat_execution_byte_identical_on_fixed_host") is True
        and row.get("cross_os_or_device_model_identity_reproducible")
        == "not_verified"
        and row.get("human_gold_used") is False
        and row.get("scored") is False
        and row.get("paper_result_eligible") is False
        for row in visual_rows
    )
    if frozen_heuristic_bank:
        visual_role = "frozen-private-fixed-threshold-heuristic-evidence-bank"
    elif model_workflow_candidate:
        visual_role = "model-workflow-visual-candidate"
    elif visual_rows:
        visual_role = "visual-evidence-without-model-reproducibility-attestation"
    else:
        visual_role = "no-visual-evidence-provided"
    feature_builder = Path(__file__).resolve().parent.parent / "features" / "build_pilot_features.py"
    visual_adapter = (
        Path(__file__).resolve().parent.parent
        / "visual"
        / "export_pregold_visual_bank.py"
        if frozen_heuristic_bank
        else Path(__file__).resolve().parent / "adapt_model_preannotation.py"
    )
    the_ok_implementation = EXPERIMENT_ROOT / "popup_eval" / "the_ok_baseline.py"
    if (
        not feature_builder.is_file()
        or not visual_adapter.is_file()
        or not the_ok_implementation.is_file()
    ):
        raise ContractError("implementation dependency file is missing")
    return {
        "action_policy": "no_action",
        "contract_version": CONTRACT_VERSION,
        "feature_contract_sha256": _sha256(_canonical_jsonl(feature_rows)),
        "feature_builder_implementation_sha256": _sha256(feature_builder.read_bytes()),
        "human_gold_used": False,
        "implementation_sha256": _sha256(Path(__file__).read_bytes()),
        "input_item_count": len(feature_rows),
        "item_identity_sha256": _sha256(("\n".join(feature_ids) + "\n").encode()),
        "methods": methods,
        "c1_budget_match": {
            "selection_policy": "fixed_hash_top_k",
            "matching_scope": "cost_only_not_item_set_or_difficulty",
            "accuracy_comparison_caveat": (
                "cost-matched only; report inspected-item-set overlap before any "
                "accuracy comparison"
            ),
            "seed": C1_BUDGET_MATCH_SEED,
            "k_source": "mg_pu_visual_call_count",
            "k": len(selected_ids),
            "selected_item_set_sha256": _sha256(
                ("\n".join(selected_ids) + "\n").encode()
            ),
        },
        "paper_result_eligible": False,
        "predictions_sha256": _sha256(_canonical_jsonl(predictions)),
        "scored": False,
        "the_ok_implementation_sha256": _sha256(the_ok_implementation.read_bytes()),
        "the_ok_upstream_revision": THE_OK_UPSTREAM_REVISION,
        "visual_evidence_sha256": (
            _sha256(_canonical_jsonl(visual_rows)) if visual_rows else None
        ),
        "visual_evidence_is_fixed_threshold_heuristic_adaptation": (
            frozen_heuristic_bank
        ),
        "visual_evidence_role": visual_role,
        "visual_repeat_execution_byte_identical_on_fixed_host": (
            frozen_heuristic_bank
        ),
        "visual_cross_os_or_device_model_identity_reproducible": "not_verified",
        "visual_adapter_implementation_sha256": _sha256(visual_adapter.read_bytes()),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Freeze deterministic pre-gold popup-message predictions without scoring."
    )
    parser.add_argument("--structured-features", type=Path, required=True)
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Optional ID-only cross-check; no non-ID field or raw-file hash is consumed.",
    )
    parser.add_argument("--visual-predictions", type=Path)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--public-summary", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, default=30)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.expected_count <= 0:
            raise ContractError("expected_count must be positive")
        if (
            args.private_output.parent.name != "private"
            or not args.private_output.name.endswith(".private.jsonl")
        ):
            raise ContractError(
                "private predictions must be written under a private/ directory "
                "with a .private.jsonl filename"
            )
        feature_rows = read_jsonl(args.structured_features)
        features_by_id = _rows_by_feature_id(feature_rows, args.expected_count)
        if args.manifest is not None:
            manifest_ids = _manifest_ids_only(read_jsonl(args.manifest))
            if manifest_ids != set(features_by_id):
                raise ContractError("manifest ID set does not match structured feature ID set")
        visual_rows = (
            read_jsonl(args.visual_predictions) if args.visual_predictions is not None else []
        )
        visual_by_id = _rows_by_visual_id(visual_rows, set(features_by_id))
        predictions = freeze_predictions(features_by_id, visual_by_id)
        summary = build_public_summary(feature_rows, visual_rows, predictions)
        _atomic_write(args.private_output, _canonical_jsonl(predictions))
        _atomic_write(
            args.public_summary,
            (json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
                "utf-8"
            ),
            mode=0o644,
        )
    except (ContractError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
