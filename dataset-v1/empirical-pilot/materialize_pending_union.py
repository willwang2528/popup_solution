#!/usr/bin/env python3
"""Materialize full, gold-blind union items pending human annotation."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "item.schema.json"
VALIDATOR_PATH = ROOT / "scripts" / "validate_dataset.py"
CONTRACT_VERSION = "pending-empirical-union-v1.0"
FEATURE_CONTRACT_VERSION = "pmj-pilot-structured-features-v1.0"
DEFAULT_PREDICTION_METHOD = "mg-pu-gated-union-v1"
PREGOLD_METHOD_IDS = {
    "structured-only-v1",
    "the-ok-text-rule",
    "mg-pu-gated-union-v1",
}
PILOT_ID_PATTERN = re.compile(r"PMJ-PILOT-(\d{3})")

PAPER_METHOD_IDS = [
    "whispertest_2025",
    "abandon_all_hope_2024",
    "the_ok_is_not_enough_2023",
    "freely_given_consent_2022",
    "vlm_fuzz_2026",
    "tcf_aaid_2026",
    "cookieverse_bannerclick",
    "ssldetecter_2019",
    "poker_sneaky_popups",
    "popsweeper_2024",
    "dynamic_ios_privacy_2021",
    "hotmobile_ad_policy_2018",
    "ios_applications_testing_2018",
    "dios_2014",
]

FEATURE_TOP_LEVEL_KEYS = {
    "identity",
    "observations",
    "candidates",
    "action_attempts",
    "decision",
    "metadata",
}
FEATURE_IDENTITY_KEYS = {"item_id", "pilot_item_id", "record_kind"}
FEATURE_OBSERVATION_KEYS = {"observation_id", "phase", "structured_representation"}
FEATURE_REPRESENTATION_KEYS = {
    "availability",
    "representation_kind",
    "node_count",
    "artifact_sha256",
}
FEATURE_CANDIDATE_KEYS = {
    "candidate_id",
    "source_channel",
    "normalized",
    "features",
}
FEATURE_NORMALIZED_KEYS = {"name_or_text", "value_or_hint", "visible"}
FEATURE_VALUE_KEYS = {
    "node_index",
    "depth",
    "class",
    "bounds",
    "clickable",
    "ancestors",
    "resource_id",
    "text",
    "component_label",
    "icon_class",
    "text_button_class",
    "gap_reasons",
    "belongs_to_host_page",
    "inside_popup_roi",
}
FEATURE_METADATA_KEYS = {
    "contract_version",
    "gold_blind",
    "gold_used",
    "scored",
    "paper_result_eligible",
    "action_mode",
}
PREDICTION_KEYS = {
    "action_policy",
    "confidence",
    "critical_facts_pred",
    "human_gold_used",
    "message_text_pred",
    "method_id",
    "paper_result_eligible",
    "pilot_item_id",
    "popup_present_pred",
    "route_reason",
    "scored",
    "status",
    "visual_called",
}
FORBIDDEN_EXACT_KEYS = {
    "annotations",
    "artifacts",
    "labels",
    "manifest",
    "metric_eligible",
    "presence_label",
    "provenance",
    "sampling_stratum",
    "source_kind",
    "source_label",
    "source_record",
    "source_record_id",
}
SAFE_ATTESTATIONS = {
    "gold_blind": True,
    "gold_used": False,
    "human_gold_used": False,
    "scored": False,
    "paper_result_eligible": False,
}


class ContractError(ValueError):
    """Raised when input or output would violate the pending-data contract."""


class DuplicateKeyError(ContractError):
    """Raised when JSON input has ambiguous duplicate keys."""


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_pairs)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line, object_pairs_hook=_strict_pairs)
        except Exception as error:
            raise ContractError(f"{path.name}:{line_number}: invalid JSON: {error}") from error
        if not isinstance(row, dict):
            raise ContractError(f"{path.name}:{line_number}: row must be an object")
        rows.append(row)
    if not rows:
        raise ContractError(f"{path.name}: input is empty")
    return rows


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _canonical_jsonl(rows: Iterable[dict[str, Any]]) -> bytes:
    return b"".join(_canonical_json(row) + b"\n" for row in rows)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _assert_exact_keys(value: Any, allowed: set[str], context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{context}: must be an object")
    unexpected = sorted(set(value) - allowed)
    if unexpected:
        raise ContractError(f"{context}: forbidden or unknown keys: {unexpected}")
    return value


def _reject_forbidden_keys(value: Any, context: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = key.casefold()
            if key in SAFE_ATTESTATIONS:
                if child is not SAFE_ATTESTATIONS[key]:
                    raise ContractError(
                        f"{context}.{key}: safe attestation must be "
                        f"{SAFE_ATTESTATIONS[key]!r}"
                    )
            elif (
                key in FORBIDDEN_EXACT_KEYS
                or lowered.endswith("_gt")
                or "adjudicat" in lowered
                or "ground_truth" in lowered
                or lowered.startswith("eligible_for_")
            ):
                raise ContractError(f"{context}.{key}: forbidden label/gold/metric key")
            _reject_forbidden_keys(child, f"{context}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_keys(child, f"{context}[{index}]")


def _pilot_id(value: Any, context: str) -> tuple[str, str]:
    if not isinstance(value, str):
        raise ContractError(f"{context}: invalid pilot_item_id")
    match = PILOT_ID_PATTERN.fullmatch(value)
    if match is None:
        raise ContractError(f"{context}: invalid pilot_item_id")
    return value, match.group(1)


def _validate_feature_row(row: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    _reject_forbidden_keys(row)
    _assert_exact_keys(row, FEATURE_TOP_LEVEL_KEYS, "feature row")
    identity = _assert_exact_keys(row["identity"], FEATURE_IDENTITY_KEYS, "feature.identity")
    item_id, _ = _pilot_id(identity.get("pilot_item_id"), "feature.identity")
    if identity.get("item_id") != item_id:
        raise ContractError(f"{item_id}: identity.item_id must equal pilot_item_id")
    if identity.get("record_kind") != "unscored_pregold_input":
        raise ContractError(f"{item_id}: feature record_kind is not pre-gold input")

    metadata = _assert_exact_keys(row["metadata"], FEATURE_METADATA_KEYS, f"{item_id}.metadata")
    required_metadata = {
        "contract_version": FEATURE_CONTRACT_VERSION,
        "gold_blind": True,
        "gold_used": False,
        "scored": False,
        "paper_result_eligible": False,
        "action_mode": "no_action",
    }
    for key, expected in required_metadata.items():
        if metadata.get(key) != expected:
            raise ContractError(f"{item_id}: metadata.{key} must be {expected!r}")
    if row.get("action_attempts") != []:
        raise ContractError(f"{item_id}: feature action_attempts must be empty")
    if row.get("decision") != {"policy": {"decision": "no_action"}}:
        raise ContractError(f"{item_id}: feature decision must be no_action")

    observations = row.get("observations")
    if not isinstance(observations, list) or len(observations) != 1:
        raise ContractError(f"{item_id}: exactly one pre_action feature observation is required")
    observation = _assert_exact_keys(
        observations[0], FEATURE_OBSERVATION_KEYS, f"{item_id}.observation"
    )
    if observation.get("phase") != "pre_action":
        raise ContractError(f"{item_id}: feature observation must be pre_action")
    representation = _assert_exact_keys(
        observation.get("structured_representation"),
        FEATURE_REPRESENTATION_KEYS,
        f"{item_id}.structured_representation",
    )
    if representation.get("representation_kind") != "rico-semantic-json":
        raise ContractError(f"{item_id}: unexpected structured representation kind")
    if representation.get("availability") not in {"available", "missing"}:
        raise ContractError(f"{item_id}: invalid structured availability")

    candidates = row.get("candidates")
    if not isinstance(candidates, list):
        raise ContractError(f"{item_id}: feature candidates must be an array")
    for index, candidate in enumerate(candidates):
        candidate = _assert_exact_keys(
            candidate, FEATURE_CANDIDATE_KEYS, f"{item_id}.candidates[{index}]"
        )
        if candidate.get("source_channel") != "structured":
            raise ContractError(f"{item_id}: candidate is not structured evidence")
        _assert_exact_keys(
            candidate.get("normalized"),
            FEATURE_NORMALIZED_KEYS,
            f"{item_id}.candidates[{index}].normalized",
        )
        _assert_exact_keys(
            candidate.get("features"),
            FEATURE_VALUE_KEYS,
            f"{item_id}.candidates[{index}].features",
        )
    if representation.get("node_count") != len(candidates):
        raise ContractError(f"{item_id}: structured node_count does not match candidates")
    return item_id, row


def _feature_rows_by_id(
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


def _validate_prediction_row(row: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    _reject_forbidden_keys(row)
    _assert_exact_keys(row, PREDICTION_KEYS, "pregold prediction")
    item_id, _ = _pilot_id(row.get("pilot_item_id"), "pregold prediction")
    method_id = row.get("method_id")
    if method_id not in PREGOLD_METHOD_IDS:
        raise ContractError(f"{item_id}: unsupported pregold method_id")
    required = {
        "action_policy": "no_action",
        "human_gold_used": False,
        "paper_result_eligible": False,
        "scored": False,
    }
    for key, expected in required.items():
        if row.get(key) != expected:
            raise ContractError(f"{item_id}: prediction.{key} must be {expected!r}")
    if row.get("status") not in {"judged", "abstain"}:
        raise ContractError(f"{item_id}: prediction status is invalid")
    if not isinstance(row.get("visual_called"), bool):
        raise ContractError(f"{item_id}: prediction visual_called must be boolean")
    return item_id, method_id, row


def _selected_predictions(
    rows: list[dict[str, Any]], feature_ids: set[str], method: str
) -> dict[str, dict[str, Any]]:
    all_rows: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        item_id, method_id, validated = _validate_prediction_row(row)
        if item_id not in feature_ids:
            raise ContractError(f"pregold prediction has unknown pilot_item_id: {item_id}")
        key = (method_id, item_id)
        if key in all_rows:
            raise ContractError(f"duplicate pregold prediction: {method_id}/{item_id}")
        all_rows[key] = validated
    return {
        item_id: all_rows[(method, item_id)]
        for item_id in feature_ids
        if (method, item_id) in all_rows
    }


def _resolve_schema(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    while "$ref" in schema:
        ref = schema["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/"):
            raise ContractError(f"unsupported schema reference: {ref!r}")
        current: Any = root
        for raw in ref[2:].split("/"):
            token = raw.replace("~1", "/").replace("~0", "~")
            current = current[token]
        if not isinstance(current, dict):
            raise ContractError(f"schema reference is not an object: {ref}")
        schema = current
    return schema


def _schema_skeleton(schema: dict[str, Any], root: dict[str, Any]) -> Any:
    schema = _resolve_schema(schema, root)
    if "const" in schema:
        return schema["const"]
    if "oneOf" in schema:
        return _schema_skeleton(schema["oneOf"][0], root)
    expected = schema.get("type")
    allowed = expected if isinstance(expected, list) else [expected] if expected else []
    if "null" in allowed:
        return None
    if "enum" in schema:
        return schema["enum"][0]
    if "object" in allowed or "properties" in schema:
        properties = schema.get("properties", {})
        return {
            key: _schema_skeleton(properties[key], root)
            for key in schema.get("required", [])
        }
    if "array" in allowed:
        return []
    if "string" in allowed:
        return ""
    if "boolean" in allowed:
        return False
    if "integer" in allowed or "number" in allowed:
        return 0
    return None


def _schema_object_skeleton(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    """Build the object branch of a nullable object definition."""
    resolved = _resolve_schema(schema, root)
    properties = resolved.get("properties")
    if not isinstance(properties, dict):
        raise ContractError("schema definition has no object properties")
    return {
        key: _schema_skeleton(properties[key], root)
        for key in resolved.get("required", [])
    }


def _set_pending_scenario(item: dict[str, Any], item_number: str) -> None:
    scenario = item["scenario"]
    scenario.update(
        {
            "scenario_id": f"pmj.pending.{item_number}",
            "task_goal": "Judge whether a popup is present and report its message without action.",
            "blocked_step": "Pending human annotation.",
            "trigger_action": "Archived real-app source observation; trigger metadata withheld.",
            "blocked_target_gt": None,
            "task_postcondition_gt": None,
            "scope_label": "ordinary_low_risk_popup",
            "popup_expected_gt": None,
            "popup_kind_gt": None,
            "popup_owner_type_gt": None,
            "popup_owner_gt": None,
            "host_owner_gt": None,
            "allowed_action_set_gt": [],
            "disallowed_action_set_gt": [],
            "abstain_allowed_gt": None,
            "unsafe_context_gt": None,
            "safety_category_gt": None,
            "action_topology_gt": None,
            "exposure_status_gt": None,
            "exposure_cause_gt": None,
            "exposure_cause_evidence": [],
        }
    )


def _candidate_from_feature(
    feature_candidate: dict[str, Any], observation_id: str, schema: dict[str, Any]
) -> dict[str, Any]:
    candidate = _schema_skeleton({"$ref": "#/$defs/candidate"}, schema)
    normalized_input = feature_candidate["normalized"]
    values = feature_candidate["features"]
    ancestors = values.get("ancestors")
    hierarchy = [value for value in ancestors if isinstance(value, str)] if isinstance(ancestors, list) else []
    clickable = values.get("clickable") if isinstance(values.get("clickable"), bool) else None
    candidate.update(
        {
            "candidate_id": str(feature_candidate["candidate_id"]),
            "observation_id": observation_id,
            "source_channel": "uiautomator",
            "raw_ref": str(feature_candidate["candidate_id"]),
            "matched_cross_channel_candidate_ids": [],
        }
    )
    candidate["normalized"].update(
        {
            "owner": None,
            "window_or_context": None,
            "role_or_class": values.get("class") if isinstance(values.get("class"), str) else None,
            "name_or_text": normalized_input.get("name_or_text"),
            "value_or_hint": normalized_input.get("value_or_hint"),
            "stable_id": values.get("resource_id") if isinstance(values.get("resource_id"), str) else None,
            "supported_actions": ["click"] if clickable else [],
            "enabled": None,
            "clickable": clickable,
            "hittable": None,
            "visible": normalized_input.get("visible") if isinstance(normalized_input.get("visible"), bool) else None,
            "focusable": None,
            "scrollable": None,
            "checkable": None,
            "checked_or_toggle": None,
            "selected": None,
            "bounds_normalized": None,
            "z_or_layer": None,
            "hierarchy_path": hierarchy,
            "parent_id": None,
            "children_ids": [],
            "sibling_index": None,
            "tree_depth": values.get("depth") if isinstance(values.get("depth"), int) else None,
        }
    )
    candidate["android_raw"] = _schema_object_skeleton(
        {"$ref": "#/$defs/androidCandidateRaw"}, schema
    )
    candidate["android_raw"].update(
        {
            "source_layer": "view",
            "resource_id": values.get("resource_id") if isinstance(values.get("resource_id"), str) else None,
            "text": values.get("text") if isinstance(values.get("text"), str) else None,
            "class_name": values.get("class") if isinstance(values.get("class"), str) else None,
            "role": values.get("component_label") if isinstance(values.get("component_label"), str) else None,
            "path": hierarchy,
            "clickable": clickable,
            "actions": ["click"] if clickable else [],
            "raw_node_ref": str(feature_candidate["candidate_id"]),
        }
    )
    candidate["ios_raw"] = None
    candidate["dom_raw"] = None
    candidate["visual_raw"] = None
    gap_reasons = values.get("gap_reasons")
    candidate["features"].update(
        {
            "matched_keywords": [],
            "normalized_tokens": [],
            "gap_reasons": [value for value in gap_reasons if isinstance(value, str)]
            if isinstance(gap_reasons, list)
            else [],
            "belongs_to_host_page": values.get("belongs_to_host_page")
            if isinstance(values.get("belongs_to_host_page"), bool)
            else None,
            "inside_popup_roi": values.get("inside_popup_roi")
            if isinstance(values.get("inside_popup_roi"), bool)
            else None,
        }
    )
    candidate["ground_truth"] = {
        key: None for key in candidate["ground_truth"]
    }
    return candidate


def _prediction_is_schema_stable(prediction: dict[str, Any]) -> bool:
    if prediction.get("status") != "judged":
        return False
    present = prediction.get("popup_present_pred")
    confidence = prediction.get("confidence")
    facts = prediction.get("critical_facts_pred")
    if not isinstance(present, bool):
        return False
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        return False
    if not 0 <= confidence <= 1:
        return False
    if not isinstance(facts, list) or not all(isinstance(fact, str) for fact in facts):
        return False
    message = prediction.get("message_text_pred")
    if present:
        return isinstance(message, str) and bool(message.strip())
    return message is None and facts == []


def _iter_leaves(value: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"presence", "field_provenance", "field_status", "measurement_channel"}:
                continue
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            path = f"{prefix}/{escaped}"
            if isinstance(child, dict) and child:
                yield from _iter_leaves(child, path)
            elif isinstance(child, list) and child and any(
                isinstance(item, (dict, list)) for item in child
            ):
                yield from _iter_leaves(child, path)
            else:
                yield path, child
    elif isinstance(value, list):
        for index, child in enumerate(value):
            path = f"{prefix}/{index}"
            if isinstance(child, (dict, list)):
                yield from _iter_leaves(child, path)
            else:
                yield path, child


def _fill_local_observability(value: dict[str, Any], source_ref: str) -> None:
    status: dict[str, str] = {}
    provenance: dict[str, dict[str, Any]] = {}
    for pointer, leaf in _iter_leaves(value):
        if leaf is None:
            status[pointer] = "not_available"
        else:
            status[pointer] = "derived"
            provenance[pointer] = {
                "source_kind": "derived",
                "source_ref": source_ref,
                "collector_version": CONTRACT_VERSION,
                "timestamp": None,
                "notes": "Gold-blind pending union materialization.",
            }
    value["presence"] = status
    value["field_provenance"] = provenance


def _fill_global_observability(item: dict[str, Any]) -> None:
    status: dict[str, str] = {}
    channels: dict[str, str] = {}
    for pointer, leaf in _iter_leaves(item):
        status[pointer] = "not_available" if leaf is None else "derived"
        channels[pointer] = (
            "not_available" if leaf is None else "pending_union_materializer"
        )
    item["observability"] = {
        "field_status": status,
        "measurement_channel": channels,
    }


def _build_item(
    pilot_id: str,
    feature: dict[str, Any],
    prediction: dict[str, Any] | None,
    schema: dict[str, Any],
) -> dict[str, Any]:
    _, item_number = _pilot_id(pilot_id, "feature identity")
    item = _schema_skeleton(schema, schema)
    item_id = f"pmj.pending.{item_number}"
    feature_observation = feature["observations"][0]
    representation = feature_observation["structured_representation"]
    available = representation["availability"] == "available"
    artifact_sha = representation.get("artifact_sha256")
    observation_id = f"obs.pending.{item_number}.pre-action"

    item["identity"].update(
        {
            "item_id": item_id,
            "pilot_item_id": pilot_id,
            "record_kind": "real_app",
            "collection_status": "collected",
            "split": "pilot",
            "scenario_group_id": f"pmj.pending.{item_number}",
            "app_group_id": None,
            "popup_template_group_id": None,
            "sdk_or_cmp_group_id": None,
            "os_family_group_id": "android.archived-source",
            "near_duplicate_group_id": None,
            "randomization_seed": None,
            "started_at": None,
            "ended_at": None,
        }
    )
    item["provenance"].update(
        {
            "paper_method_ids": PAPER_METHOD_IDS,
            "collection_session_id": "pending-empirical-pilot-v1",
            "source_origin": "paper_artifact",
            "source_dataset": "archived-real-app-source",
            "source_artifacts": [],
            "raw_capture_hashes": (
                {"structured_artifact_sha256": artifact_sha}
                if isinstance(artifact_sha, str)
                else {}
            ),
            "collector_and_model_versions": {
                "materializer": CONTRACT_VERSION,
                "feature_contract": FEATURE_CONTRACT_VERSION,
                "prediction_method": prediction.get("method_id") if prediction else None,
                "prediction_gold_blind": True,
                "prediction_scored": False,
                "prediction_paper_result_eligible": False,
            },
            "annotation_record_ids": [],
            "episode_evidence_uris": [],
            "evidence_level": "partial_device_evidence",
            "license_or_permission": None,
            "privacy_review_status": "restricted",
            "notes": [
                "Archived real-app source observation; not a verified real-device episode.",
                "Human popup/message annotation is pending.",
            ],
        }
    )
    _set_pending_scenario(item, item_number)
    item["environment"].update(
        {
            "platform": "android",
            "os_version": None,
            "os_build": None,
            "device_model": None,
            "device_kind": None,
            "screen_size_px": None,
            "app_or_package": None,
            "app_version": None,
            "ui_framework": None,
            "foreground_owner": None,
            "window_or_context": None,
            "locale": None,
            "theme": None,
            "orientation": None,
            "font_scale": None,
            "display_scale": None,
            "viewport_px": None,
            "network_profile": None,
            "device_state": "archived_source_device_unknown",
            "permission_state": {},
            "driver_and_adapter_version": {"materializer": CONTRACT_VERSION},
            "reset_snapshot_id": None,
            "randomized_variant": {},
        }
    )
    item["assistive_technology"].update(
        {
            "name": "none",
            "version": None,
            "enabled": False,
            "speech_rate": None,
            "verbosity": None,
            "touch_exploration": None,
            "focus_navigation_mode": None,
            "braille_display": None,
            "config_uri": None,
            "focus_observability": "not_observable",
            "utterance_observability": "not_observable",
            "observer_kind": "none",
        }
    )
    item["capability_profile"].update(
        {
            "structured_read_status": "partial" if available else "failed",
            "action_execution_status": "not_applicable",
            "screen_reader_focus_observability": "not_observable",
            "utterance_observability": "not_observable",
            "technical_closed_loop_status": "not_applicable",
            "accessible_closed_loop_status": "not_applicable",
            "ios_field_status": "not_applicable",
            "evidence_refs": [],
        }
    )

    stable_prediction = prediction if prediction and _prediction_is_schema_stable(prediction) else None
    prediction_status = "judged" if stable_prediction else "abstain"
    visual_called = bool(prediction and prediction.get("visual_called"))
    item["message_judgment"]["labels"].update(
        {
            "popup_present_gt": None,
            "blocking_gt": None,
            "message_text_gt": None,
            "critical_facts_gt": [],
            "message_text_observability": "pending_annotation",
            "evidence_uris": [],
        }
    )
    item["message_judgment"]["prediction"].update(
        {
            "status": prediction_status,
            "popup_present_pred": stable_prediction.get("popup_present_pred")
            if stable_prediction
            else None,
            "message_text_pred": stable_prediction.get("message_text_pred")
            if stable_prediction
            else None,
            "critical_facts_pred": list(stable_prediction.get("critical_facts_pred", []))
            if stable_prediction
            else [],
            "confidence": stable_prediction.get("confidence") if stable_prediction else None,
            "source_observation_id": observation_id,
            "evidence_uris": [],
            "model_or_rule_version": prediction.get("method_id")
            if prediction
            else "not-run",
            "latency_ms": None,
        }
    )
    item["message_judgment"]["gate"].update(
        {
            "structured_message_complete": None,
            "gap_reasons": ["unknown"] if visual_called else [],
            "visual_fallback_used": visual_called,
            "visual_call_count": 1 if visual_called else 0,
            "tree_screenshot_synchronized": None,
        }
    )
    item["message_judgment"]["evaluation"] = {
        key: None for key in item["message_judgment"]["evaluation"]
    }
    item["message_judgment"]["eligibility"].update(
        {
            "eligible_for_v1_presence_metric": False,
            "eligible_for_v1_message_metric": False,
            "eligible_for_advanced_recovery_metric": False,
            "eligible_for_user_experience_claim": False,
            "exclusion_reasons": ["pending_human_annotation"],
        }
    )

    observation = _schema_skeleton({"$ref": "#/$defs/observation"}, schema)
    observation.update(
        {
            "observation_id": observation_id,
            "phase": "pre_action",
            "timestamp": None,
            "stable_after_ms": None,
        }
    )
    observation["synchronization"].update(
        {
            "tree_screenshot_sync_status": "unknown",
            "capture_delta_ms": None,
            "ui_fingerprint": artifact_sha if isinstance(artifact_sha, str) else None,
            "stale_or_tool_failure": None,
        }
    )
    observation["owner_context"].update(
        {
            "native_or_web": "native",
            "owner_known": None,
        }
    )
    observation["popup"].update(
        {
            "present_gt": None,
            "present_pred": stable_prediction.get("popup_present_pred")
            if stable_prediction
            else None,
            "kind_gt": None,
            "bbox_gt": None,
            "owner_gt": None,
            "modal_gt": None,
            "blocking_gt": None,
        }
    )
    observation["structured_representation"].update(
        {
            "available": available,
            "source_channels": ["rico_semantic"] if available else [],
            "node_count": len(feature["candidates"]),
            "interactive_node_count": sum(
                candidate["features"].get("clickable") is True
                for candidate in feature["candidates"]
            ),
            "state_signature": artifact_sha if isinstance(artifact_sha, str) else None,
            "traversal_state": None,
            "transition_stack": [],
            "replay_path": [],
            "android_raw": (
                _schema_object_skeleton(
                    {"$ref": "#/$defs/androidObservationRaw"}, schema
                )
                if available
                else None
            ),
            "ios_raw": None,
            "dom_raw": None,
        }
    )
    if available:
        observation["structured_representation"]["android_raw"].update(
            {
                "source_layer": "view",
                "accessibility_actions_available": [],
            }
        )
    observation["visual_representation"].update(
        {
            "ocr_items": [],
            "vlm_output": None,
        }
    )
    observation["screen_reader_state"].update(
        {
            "focus_path": [],
            "observable_by": "not_observable",
        }
    )
    observation["literature_signals"].update(
        {
            "matched_keywords": [],
            "normalized_tokens": [],
            "iabtcf_values": {},
            "state_transition": None,
        }
    )
    item["observations"] = [observation]
    item["candidates"] = [
        _candidate_from_feature(candidate, observation_id, schema)
        for candidate in feature["candidates"]
    ]

    decision = item["decision"]
    method_id = prediction.get("method_id") if prediction else "pending-no-prediction-v1"
    decision.update(
        {
            "method_id": method_id,
            "method_version": "pregold-frozen" if prediction else "not-run",
            "method_family": (
                "tree_baseline"
                if method_id in {"structured-only-v1", "the-ok-text-rule"}
                else "ours"
            ),
            "candidate_input_ids": [candidate["candidate_id"] for candidate in item["candidates"]],
            "rationale_trace": [
                "Human gold is pending; the embedded prediction is unscored.",
                "No popup action or recovery operation is permitted in v1.",
            ],
            "model_versions": {
                "prediction_method": method_id,
                "human_gold_used": False,
                "scored": False,
                "paper_result_eligible": False,
            },
        }
    )
    decision["gate"].update(
        {
            "structured_sufficient": None,
            "owner_consistent": None,
            "action_executable": None,
            "low_risk_policy_satisfied": None,
            "capture_fresh_and_synchronized": None,
            "gap_reasons": ["pregold_visual_route"] if visual_called else [],
            "visual_fallback_triggered": visual_called,
            "final_state": "no_action",
            "scorer_version": method_id,
            "calibration_version": None,
        }
    )
    decision["policy"].update(
        {
            "allowed_action_policy_version": "v1-message-no-action",
            "allowed_semantics": [],
            "blocked_semantics": ["all_actions_in_v1"],
            "risk_class": "read_only",
            "decision": "no_action",
        }
    )
    decision["selection"].update(
        {
            "action_semantics_pred": None,
            "target_candidate_id_pred": None,
            "execution_channel_pred": None,
            "confidence": None,
            "alternative_candidate_id": None,
        }
    )
    decision["visual_fallback"].update(
        {
            "required": visual_called,
            "used": visual_called,
            "trigger_reasons": ["pregold_visual_route"] if visual_called else [],
            "call_count": 1 if visual_called else 0,
            "latency_ms": None,
            "estimated_cost": None,
        }
    )
    decision["abstention"].update(
        {
            "abstained": prediction_status == "abstain",
            "handoff_required": False,
            "reason": (
                "pregold_prediction_not_schema_stable_or_not_provided"
                if prediction_status == "abstain"
                else None
            ),
            "user_message": None,
        }
    )
    item["action_attempts"] = []

    verification = item["verification"]
    verification["weak_proxies"] = {
        key: None for key in verification["weak_proxies"]
    }
    verification["dismissal"].update(
        {
            "visual_popup_gone": None,
            "semantic_popup_gone": None,
            "D": None,
            "observability": "not_observable",
            "evidence_uris": [],
        }
    )
    verification["technical_context_recovery"].update(
        {
            "owner_after": None,
            "window_context_after": None,
            "owner_context_restored": None,
            "blocked_target_visible": None,
            "blocked_target_operable": None,
            "C_tech": None,
            "evidence_uris": [],
        }
    )
    verification["accessible_context_recovery"].update(
        {
            "focus_before": None,
            "focus_after": None,
            "focus_restored_to_blocked_target_or_successor": None,
            "utterance_before": None,
            "utterance_after": None,
            "spoken_context_consistent": None,
            "C_a11y": None,
            "observability": "not_observable",
            "target_user_validation": None,
            "evidence_uris": [],
        }
    )
    verification["task"].update(
        {
            "postcondition_verifiable": False,
            "task_postcondition_satisfied": None,
            "T": None,
            "evidence_uris": [],
        }
    )
    verification["persistence"].update(
        {
            "relaunch_performed": False,
            "popup_absent_after_relaunch": None,
            "business_choice_persisted": None,
            "iabtcf_values_after": {},
            "evidence_uris": [],
        }
    )
    verification["safety"].update(
        {
            "sensitive_context_flags": [],
            "safe_exit_exists_gt": None,
            "policy_violation": False,
            "false_intervention": False,
            "harmful_action": False,
            "wrong_action": False,
            "side_effect_detected": False,
            "cross_app_jump": False,
            "task_abandonment": None,
            "user_handoff_required": False,
            "retry_budget": 0,
            "retry_count": 0,
            "retry_exhausted": False,
        }
    )
    verification["metrics"].update(
        {
            "VTR_tech": None,
            "A_VTR": None,
            "recovery_time_ms": None,
            "extra_navigation_steps_after_dismissal": None,
            "action_attempt_count": 0,
            "visual_call_count": 1 if visual_called else 0,
            "total_latency_ms": None,
            "estimated_model_cost": None,
        }
    )
    verification["eligibility"].update(
        {
            "eligible_for_training": False,
            "eligible_for_main_metric": False,
            "eligible_for_user_experience_claim": False,
            "exclusion_reasons": ["pending_human_annotation"],
        }
    )
    item["feedback"].update(
        {
            "status": "not_delivered",
            "message": None,
            "handoff_options": [],
            "delivered": False,
        }
    )
    item["annotations"] = []
    item["quality"].update(
        {
            "schema_valid": True,
            "all_referenced_artifacts_exist": None,
            "field_presence_audited": True,
            "field_provenance_complete": True,
            "cross_platform_raw_fields_preserved": True,
            "dual_annotation_complete": False,
            "adjudication_complete": False,
            "split_leakage_check_passed": None,
            "privacy_review_passed": False,
            "synthetic_or_fixture_disclosed": False,
            "review_status": "provisional",
            "review_notes": [
                "Pending human annotation; no item is metric eligible.",
                "real_app means archived real-app source observation, not verified real-device execution.",
            ],
        }
    )

    _fill_local_observability(
        item["assistive_technology"], "private_gold_blind_feature_bundle"
    )
    _fill_local_observability(observation, "private_gold_blind_feature_bundle")
    for candidate in item["candidates"]:
        _fill_local_observability(candidate, "private_gold_blind_feature_bundle")
    _fill_global_observability(item)
    return item


def _load_validator_module() -> Any:
    spec = importlib.util.spec_from_file_location("pending_union_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise ContractError("could not load project dataset validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _validate_output(items: list[dict[str, Any]], schema: dict[str, Any]) -> None:
    validator = _load_validator_module()
    errors: list[str] = []
    for index, item in enumerate(items):
        schema_errors = validator.validate_schema(item, schema, schema, f"item[{index}]")
        errors.extend(schema_errors)
        if not schema_errors:
            item_errors, _ = validator.check_item(item, index)
            errors.extend(item_errors)
    dataset_errors, _ = validator.check_dataset(items)
    errors.extend(dataset_errors)
    if errors:
        preview = "; ".join(errors[:8])
        raise ContractError(f"materialized union failed project validation: {preview}")


def _atomic_write(path: Path, payload: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ContractError(f"refusing symbolic-link output: {path.name}")
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(payload)
    temporary.chmod(mode)
    temporary.replace(path)
    path.chmod(mode)


def _write_outputs(
    items: list[dict[str, Any]],
    feature_bytes: bytes,
    prediction_bytes: bytes | None,
    private_output: Path,
    public_summary: Path,
    schema: dict[str, Any],
) -> None:
    if (
        private_output.parent.name != "private"
        or not private_output.name.endswith(".private.jsonl")
    ):
        raise ContractError(
            "private union must be under a private/ directory and end with .private.jsonl"
        )
    private_output.parent.mkdir(parents=True, exist_ok=True)
    private_output.parent.chmod(0o700)
    payload = _canonical_jsonl(items)
    _atomic_write(private_output, payload, 0o600)

    counts = {
        "items": len(items),
        "pending_human_annotation": len(items),
        "structured_available": sum(
            item["observations"][0]["structured_representation"]["available"] is True
            for item in items
        ),
        "structured_missing": sum(
            item["observations"][0]["structured_representation"]["available"] is False
            for item in items
        ),
        "structured_candidates": sum(len(item["candidates"]) for item in items),
        "pregold_predictions_connected": sum(
            item["message_judgment"]["prediction"]["model_or_rule_version"] != "not-run"
            for item in items
        ),
        "embedded_judged_predictions": sum(
            item["message_judgment"]["prediction"]["status"] == "judged"
            for item in items
        ),
    }
    summary = {
        "contract": {
            "name": "gold-blind pending empirical union materialization",
            "version": CONTRACT_VERSION,
            "record_semantics": "archived real-app source observation",
            "annotation_lifecycle": "pending_human_annotation",
            "prediction_method": DEFAULT_PREDICTION_METHOD,
        },
        "counts": counts,
        "field_coverage": {
            "source_field_union": {"literature": 90, "our_method": 165, "total": 255},
            "required_top_level_containers": len(schema["required"]),
            "all_required_top_level_containers_materialized": True,
            "full_union_schema_validated": True,
            "project_semantic_validator_passed": True,
        },
        "hashes": {
            "feature_input_sha256": _sha256(feature_bytes),
            "pregold_input_sha256": _sha256(prediction_bytes)
            if prediction_bytes is not None
            else None,
            "private_union_bundle_sha256": _sha256(payload),
            "schema_sha256": _sha256(_canonical_json(schema)),
            "implementation_sha256": _sha256(Path(__file__).read_bytes()),
        },
        "negative_claims": {
            "gold_blind": True,
            "human_gold_used": False,
            "scored": False,
            "paper_result_eligible": False,
            "action_executed": False,
            "advanced_recovery_evaluated": False,
            "real_device_episode_claim": False,
            "user_experience_claim": False,
        },
    }
    _atomic_write(
        public_summary,
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        + b"\n",
        0o644,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--pregold-predictions", type=Path)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--public-summary", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, default=30)
    parser.add_argument(
        "--prediction-method",
        choices=sorted(PREGOLD_METHOD_IDS),
        default=DEFAULT_PREDICTION_METHOD,
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.expected_count <= 0:
            raise ContractError("expected_count must be positive")
        schema = _read_json(SCHEMA_PATH)
        if not isinstance(schema, dict):
            raise ContractError("project item schema must be an object")
        feature_bytes = args.features.read_bytes()
        feature_rows = _read_jsonl(args.features)
        features_by_id = _feature_rows_by_id(feature_rows, args.expected_count)
        prediction_bytes: bytes | None = None
        selected: dict[str, dict[str, Any]] = {}
        if args.pregold_predictions is not None:
            prediction_bytes = args.pregold_predictions.read_bytes()
            selected = _selected_predictions(
                _read_jsonl(args.pregold_predictions),
                set(features_by_id),
                args.prediction_method,
            )
        items = [
            _build_item(item_id, features_by_id[item_id], selected.get(item_id), schema)
            for item_id in sorted(features_by_id)
        ]
        _validate_output(items, schema)
        _write_outputs(
            items,
            feature_bytes,
            prediction_bytes,
            args.private_output,
            args.public_summary,
            schema,
        )
    except (ContractError, OSError, KeyError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
