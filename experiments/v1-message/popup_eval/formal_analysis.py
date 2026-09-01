#!/usr/bin/env python3
"""Finalize preregistered Holm, BH-FDR, and quality-cost Pareto analyses.

This private-only receipt is downstream of the formal K50 result.  It does not
read UI evidence, gold labels, or predictions and never authorizes a paper
claim by itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Mapping, Sequence


CONTRACT_VERSION = "popup-message-formal-supplementary-analysis-v1.0"
REGISTRY_VERSION = "popup-message-analysis-registry-v1.0"
K50_CONTRACT_VERSION = "popup-message-formal-k50-v1.0"
SECONDARY_ALPHA = 0.05
SUBGROUP_Q = 0.10
MINIMUM_INFERENCE_GROUPS = 5
SUBGROUP_DIMENSIONS = {"gap_tier", "popup_type", "message_complexity"}
PARETO_COST_AXES = {
    "visual_calls",
    "decoded_pixels",
    "monetary_cost_microunits",
}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
ACTION_KEYS = {
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


class FormalAnalysisError(ValueError):
    """Raised when supplementary formal evidence violates the frozen plan."""


class DuplicateKeyError(FormalAnalysisError):
    """Raised when a JSON object contains an ambiguous duplicate key."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _canonical_jsonl(rows: Sequence[Mapping[str, Any]]) -> bytes:
    return b"".join(_canonical_json(row) + b"\n" for row in rows)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise FormalAnalysisError(message)


def _number(value: Any, label: str) -> float:
    _require(type(value) in (int, float) and math.isfinite(value), f"{label} must be finite")
    return float(value)


def _probability(value: Any, label: str) -> float:
    probability = _number(value, label)
    _require(0.0 <= probability <= 1.0, f"{label} must be in [0, 1]")
    return probability


def _positive_integer(value: Any, label: str, *, minimum: int = 1) -> int:
    _require(
        isinstance(value, int) and not isinstance(value, bool) and value >= minimum,
        f"{label} must be an integer >= {minimum}",
    )
    return value


def _is_passive(value: Any) -> bool:
    if isinstance(value, Mapping):
        return all(_is_passive(child) for child in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return all(_is_passive(child) for child in value)
    try:
        return value in PASSIVE_VALUES
    except TypeError:
        return False


def _reject_action_or_recovery(value: Any, context: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            lowered = key.casefold()
            child_context = f"{context}.{key}"
            if lowered in ACTION_KEYS:
                raise FormalAnalysisError(
                    f"{child_context}: Action or Recovery is outside V1"
                )
            if "recovery" in lowered:
                if not _is_passive(child):
                    raise FormalAnalysisError(
                        f"{child_context}: Action or Recovery is outside V1"
                    )
                continue
            if lowered == "action_policy" and child != "no_action":
                raise FormalAnalysisError(
                    f"{child_context}: Action or Recovery is outside V1"
                )
            _reject_action_or_recovery(child, child_context)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, child in enumerate(value):
            _reject_action_or_recovery(child, f"{context}[{index}]")


def _unique_ids(values: Any, label: str) -> list[str]:
    _require(
        isinstance(values, list)
        and values
        and all(isinstance(value, str) and value for value in values),
        f"{label} must be a non-empty string list",
    )
    _require(len(values) == len(set(values)), f"{label} contains duplicate IDs")
    return list(values)


def _frozen_records(
    values: Any,
    *,
    id_key: str,
    required_keys: set[str],
    label: str,
) -> dict[str, dict[str, Any]]:
    _require(isinstance(values, list) and values, f"{label} must be a non-empty list")
    records: dict[str, dict[str, Any]] = {}
    for index, value in enumerate(values):
        _require(isinstance(value, Mapping), f"{label}[{index}] must be an object")
        _require(set(value) == required_keys, f"{label}[{index}] keys are incomplete or unexpected")
        identifier = value.get(id_key)
        _require(isinstance(identifier, str) and identifier, f"{label}[{index}] ID is missing")
        _require(identifier not in records, f"{label} contains duplicate IDs")
        records[identifier] = dict(value)
    return records


def _validate_registry(
    registry: Mapping[str, Any], expected_sha256: str
) -> dict[str, Any]:
    expected_keys = {
        "contract_version",
        "frozen_before_gold",
        "primary_endpoint",
        "secondary_alpha",
        "secondary_comparisons",
        "subgroup_fdr_q",
        "subgroup_tests",
        "subgroup_dimensions",
        "minimum_inference_groups",
        "pareto_points",
        "pareto_quality_metric",
        "pareto_coverage_metric",
        "pareto_cost_axes",
    }
    _require(isinstance(registry, Mapping), "analysis registry must be an object")
    _require(
        isinstance(expected_sha256, str)
        and SHA256_PATTERN.fullmatch(expected_sha256) is not None,
        "expected registry hash must be a lowercase sha256",
    )
    _require(_sha256(_canonical_json(registry)) == expected_sha256, "analysis registry hash mismatch")
    _require(set(registry) == expected_keys, "analysis registry keys are incomplete or unexpected")
    _require(registry.get("contract_version") == REGISTRY_VERSION, "analysis registry version mismatch")
    _require(registry.get("frozen_before_gold") is True, "analysis registry was not frozen before gold")
    _require(
        registry.get("primary_endpoint") == "vpma_overall_success_rate",
        "analysis primary endpoint drifted",
    )
    _require(registry.get("secondary_alpha") == SECONDARY_ALPHA, "secondary alpha must be 0.05")
    _require(registry.get("subgroup_fdr_q") == SUBGROUP_Q, "subgroup BH-FDR q must be 0.10")
    _require(
        registry.get("minimum_inference_groups") == MINIMUM_INFERENCE_GROUPS,
        "minimum inference groups must be 5",
    )
    dimensions = _unique_ids(registry.get("subgroup_dimensions"), "subgroup_dimensions")
    _require(set(dimensions) == SUBGROUP_DIMENSIONS, "subgroup dimensions differ from the frozen plan")
    cost_axes = _unique_ids(registry.get("pareto_cost_axes"), "pareto_cost_axes")
    _require(set(cost_axes) == PARETO_COST_AXES, "Pareto cost axes differ from the frozen plan")
    _require(
        registry.get("pareto_quality_metric") == "vpma_overall_success_rate"
        and registry.get("pareto_coverage_metric") == "coverage",
        "Pareto quality or coverage metric drifted",
    )
    secondary_specs = _frozen_records(
        registry.get("secondary_comparisons"),
        id_key="comparison_id",
        required_keys={
            "comparison_id",
            "proposed_method_id",
            "reference_method_id",
            "proposed_operating_point",
            "reference_operating_point",
        },
        label="secondary_comparisons",
    )
    for identifier, spec in secondary_specs.items():
        for key in (
            "proposed_method_id",
            "reference_method_id",
            "proposed_operating_point",
            "reference_operating_point",
        ):
            _require(
                isinstance(spec.get(key), str) and bool(spec[key]),
                f"secondary_comparisons.{identifier}.{key} is missing",
            )
    subgroup_specs = _frozen_records(
        registry.get("subgroup_tests"),
        id_key="subgroup_test_id",
        required_keys={"subgroup_test_id", "dimension", "level"},
        label="subgroup_tests",
    )
    for identifier, spec in subgroup_specs.items():
        _require(
            spec.get("dimension") in dimensions,
            f"subgroup_tests.{identifier} subgroup dimension is not preregistered",
        )
        _require(
            isinstance(spec.get("level"), str) and bool(spec["level"]),
            f"subgroup_tests.{identifier}.level is missing",
        )
    pareto_specs = _frozen_records(
        registry.get("pareto_points"),
        id_key="point_id",
        required_keys={"point_id", "method_id", "operating_point"},
        label="pareto_points",
    )
    for identifier, spec in pareto_specs.items():
        _require(
            isinstance(spec.get("method_id"), str)
            and bool(spec["method_id"])
            and isinstance(spec.get("operating_point"), str)
            and bool(spec["operating_point"]),
            f"pareto_points.{identifier} method binding is missing",
        )
    result = {
        "secondary_ids": list(secondary_specs),
        "secondary_specs": secondary_specs,
        "subgroup_ids": list(subgroup_specs),
        "subgroup_specs": subgroup_specs,
        "pareto_ids": list(pareto_specs),
        "pareto_specs": pareto_specs,
        "dimensions": dimensions,
        "cost_axes": cost_axes,
    }
    return result


def _validate_k50_result(result: Mapping[str, Any]) -> str:
    _require(isinstance(result, Mapping), "formal K50 result must be an object")
    _reject_action_or_recovery(result, "formal_k50_result")
    _require(
        result.get("formal_contract_version") == K50_CONTRACT_VERSION,
        "formal K50 contract version mismatch",
    )
    _require(result.get("decision") in {"continue", "withdraw_superiority"}, "formal K50 decision is invalid")
    _require(result.get("action_policy") == "no_action", "formal K50 result is not no-action")
    _require(result.get("recovery_evaluated") is False, "formal K50 result evaluated Recovery")
    _require(result.get("paper_result_eligible") is False, "formal K50 input must remain private and ineligible")
    endpoint = result.get("primary_endpoint")
    _require(
        isinstance(endpoint, Mapping)
        and endpoint.get("name") == "vpma_overall_success_rate",
        "formal K50 primary endpoint mismatch",
    )
    return str(result["decision"])


def _validate_effect_row(row: Mapping[str, Any], *, context: str) -> dict[str, Any]:
    metric_name = row.get("metric_name")
    _require(metric_name == "vpma_overall_success_rate", f"{context} metric is not preregistered")
    _require(row.get("direction") == "proposed_minus_reference", f"{context} direction mismatch")
    group_count = _positive_integer(row.get("group_count"), f"{context}.group_count")
    raw_p_value = row.get("raw_p_value")
    if group_count >= MINIMUM_INFERENCE_GROUPS:
        p_value: float | None = _probability(
            raw_p_value, f"{context}.raw_p_value"
        )
        adjustment_input = p_value
        inference_status = "cluster_inference_available"
    else:
        _require(
            raw_p_value is None,
            f"{context}.raw_p_value must be null below minimum inference groups",
        )
        p_value = None
        adjustment_input = 1.0
        inference_status = "descriptive_only_insufficient_groups"
    effect = _number(row.get("effect"), f"{context}.effect")
    ci = row.get("confidence_interval_95")
    _require(isinstance(ci, Mapping) and set(ci) == {"lower", "upper"}, f"{context} CI is invalid")
    lower = _number(ci.get("lower"), f"{context}.ci.lower")
    upper = _number(ci.get("upper"), f"{context}.ci.upper")
    _require(lower <= upper, f"{context} CI bounds are inverted")
    return {
        "metric_name": metric_name,
        "direction": "proposed_minus_reference",
        "raw_p_value": p_value,
        "adjustment_input_p_value": adjustment_input,
        "inference_status": inference_status,
        "effect": effect,
        "confidence_interval_95": {"lower": lower, "upper": upper},
        "group_count": group_count,
    }


def _rows_by_frozen_id(
    rows: Sequence[Mapping[str, Any]],
    *,
    id_key: str,
    expected_ids: Sequence[str],
    label: str,
) -> dict[str, Mapping[str, Any]]:
    _require(
        isinstance(rows, Sequence) and not isinstance(rows, (str, bytes)),
        f"{label} must be a sequence",
    )
    by_id: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        _require(isinstance(row, Mapping), f"every {label} row must be an object")
        identifier = row.get(id_key)
        _require(isinstance(identifier, str) and identifier, f"{label} ID is missing")
        _require(identifier not in by_id, f"{label} contains duplicate IDs")
        by_id[identifier] = row
    _require(set(by_id) == set(expected_ids), f"{label} coverage mismatch")
    return by_id


def _holm(rows: dict[str, dict[str, Any]], alpha: float) -> list[dict[str, Any]]:
    ordered = sorted(
        rows.items(), key=lambda item: (item[1]["adjustment_input_p_value"], item[0])
    )
    count = len(ordered)
    running = 0.0
    output: dict[str, dict[str, Any]] = {}
    for rank, (identifier, row) in enumerate(ordered, 1):
        adjusted = min(
            1.0, row["adjustment_input_p_value"] * (count - rank + 1)
        )
        running = max(running, adjusted)
        public_row = {
            key: value
            for key, value in row.items()
            if key != "adjustment_input_p_value"
        }
        ci = public_row["confidence_interval_95"]
        effect = public_row["effect"]
        ci_excludes_zero = (
            (effect > 0 and ci["lower"] > 0)
            or (effect < 0 and ci["upper"] < 0)
        )
        output[identifier] = {
            "comparison_id": identifier,
            **public_row,
            "adjusted_p_value": running,
            "reject_at_alpha_0_05": running <= alpha,
            "unadjusted_ci_excludes_zero_in_effect_direction": ci_excludes_zero,
            "secondary_claim_gate_passed": running <= alpha and ci_excludes_zero,
            "ci_adjustment_status": "unadjusted_per_comparison_cluster_bootstrap_95ci",
            "correction": "holm",
            "family_size": count,
        }
    return [output[identifier] for identifier in sorted(output)]


def _bh(rows: dict[str, dict[str, Any]], q: float) -> list[dict[str, Any]]:
    ordered = sorted(
        rows.items(), key=lambda item: (item[1]["adjustment_input_p_value"], item[0])
    )
    count = len(ordered)
    adjusted_by_id: dict[str, float] = {}
    running = 1.0
    for reverse_index in range(count - 1, -1, -1):
        identifier, row = ordered[reverse_index]
        rank = reverse_index + 1
        candidate = min(1.0, row["adjustment_input_p_value"] * count / rank)
        running = min(running, candidate)
        adjusted_by_id[identifier] = running
    output = []
    for identifier in sorted(rows):
        adjusted = adjusted_by_id[identifier]
        public_row = {
            key: value
            for key, value in rows[identifier].items()
            if key != "adjustment_input_p_value"
        }
        output.append(
            {
                "subgroup_test_id": identifier,
                **public_row,
                "adjusted_p_value": adjusted,
                "discovery_at_q_0_10": adjusted <= q,
                "correction": "benjamini_hochberg",
                "fdr_q": q,
                "family_size": count,
                "exploratory": True,
            }
        )
    return output


def _dominates(first: Mapping[str, Any], second: Mapping[str, Any], axis: str) -> bool:
    not_worse = (
        first["vpma_overall_success_rate"] >= second["vpma_overall_success_rate"]
        and first["coverage"] >= second["coverage"]
        and first["actual_budget"][axis] <= second["actual_budget"][axis]
    )
    strictly_better = (
        first["vpma_overall_success_rate"] > second["vpma_overall_success_rate"]
        or first["coverage"] > second["coverage"]
        or first["actual_budget"][axis] < second["actual_budget"][axis]
    )
    return not_worse and strictly_better


def _pareto(
    rows: dict[str, dict[str, Any]], cost_axes: Sequence[str]
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for axis in cost_axes:
        frontier: list[str] = []
        dominated: list[str] = []
        for identifier, point in rows.items():
            if any(
                other_id != identifier and _dominates(other, point, axis)
                for other_id, other in rows.items()
            ):
                dominated.append(identifier)
            else:
                frontier.append(identifier)
        result[axis] = {
            "objectives": {
                "maximize": ["vpma_overall_success_rate", "coverage"],
                "minimize": [axis],
            },
            "frontier_point_ids": sorted(frontier),
            "dominated_point_ids": sorted(dominated),
        }
    return result


def finalize_formal_analysis(
    *,
    analysis_registry: Mapping[str, Any],
    expected_registry_sha256: str,
    formal_k50_result: Mapping[str, Any],
    secondary_results: Sequence[Mapping[str, Any]],
    subgroup_results: Sequence[Mapping[str, Any]],
    pareto_points: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build a private, hash-bound supplementary-analysis receipt."""

    for label, value in (
        ("analysis_registry", analysis_registry),
        ("formal_k50_result", formal_k50_result),
        ("secondary_results", secondary_results),
        ("subgroup_results", subgroup_results),
        ("pareto_points", pareto_points),
    ):
        _reject_action_or_recovery(value, label)
    registry = _validate_registry(analysis_registry, expected_registry_sha256)
    primary_decision = _validate_k50_result(formal_k50_result)

    raw_secondary = _rows_by_frozen_id(
        secondary_results,
        id_key="comparison_id",
        expected_ids=registry["secondary_ids"],
        label="secondary results",
    )
    secondary: dict[str, dict[str, Any]] = {}
    for identifier, row in raw_secondary.items():
        spec = registry["secondary_specs"][identifier]
        for key in (
            "proposed_method_id",
            "reference_method_id",
            "proposed_operating_point",
            "reference_operating_point",
        ):
            _require(
                row.get(key) == spec[key],
                f"secondary_results.{identifier} method binding mismatch",
            )
        secondary[identifier] = {
            key: spec[key]
            for key in (
                "proposed_method_id",
                "reference_method_id",
                "proposed_operating_point",
                "reference_operating_point",
            )
        }
        secondary[identifier].update(
            _validate_effect_row(row, context=f"secondary_results.{identifier}")
        )

    raw_subgroups = _rows_by_frozen_id(
        subgroup_results,
        id_key="subgroup_test_id",
        expected_ids=registry["subgroup_ids"],
        label="subgroup results",
    )
    subgroups: dict[str, dict[str, Any]] = {}
    for identifier, row in raw_subgroups.items():
        _require(row.get("exploratory") is True, "subgroup result must be exploratory")
        spec = registry["subgroup_specs"][identifier]
        dimension = row.get("dimension")
        _require(dimension in registry["dimensions"], "subgroup dimension is not preregistered")
        level = row.get("level")
        _require(isinstance(level, str) and level, "subgroup level is missing")
        _require(
            dimension == spec["dimension"] and level == spec["level"],
            "subgroup dimension or level binding mismatch",
        )
        subgroups[identifier] = {
            "dimension": dimension,
            "level": level,
            **_validate_effect_row(row, context=f"subgroup_results.{identifier}"),
        }

    raw_pareto = _rows_by_frozen_id(
        pareto_points,
        id_key="point_id",
        expected_ids=registry["pareto_ids"],
        label="Pareto points",
    )
    pareto: dict[str, dict[str, Any]] = {}
    for identifier, row in raw_pareto.items():
        spec = registry["pareto_specs"][identifier]
        method_id = row.get("method_id")
        operating_point = row.get("operating_point")
        _require(isinstance(method_id, str) and method_id, "Pareto method_id is missing")
        _require(isinstance(operating_point, str) and operating_point, "Pareto operating_point is missing")
        _require(
            method_id == spec["method_id"]
            and operating_point == spec["operating_point"],
            "Pareto method binding mismatch",
        )
        budget = row.get("actual_budget")
        _require(isinstance(budget, Mapping), "Pareto actual_budget is missing")
        _require(set(budget) == set(registry["cost_axes"]), "Pareto cost axes are incomplete or unexpected")
        pareto[identifier] = {
            "method_id": method_id,
            "operating_point": operating_point,
            "vpma_overall_success_rate": _probability(
                row.get("vpma_overall_success_rate"), "Pareto VPMA"
            ),
            "coverage": _probability(row.get("coverage"), "Pareto coverage"),
            "actual_budget": {
                axis: _positive_integer(budget.get(axis), f"Pareto {axis}", minimum=0)
                for axis in registry["cost_axes"]
            },
        }

    ordered_secondary = [dict(raw_secondary[key]) for key in sorted(raw_secondary)]
    ordered_subgroups = [dict(raw_subgroups[key]) for key in sorted(raw_subgroups)]
    ordered_pareto = [dict(raw_pareto[key]) for key in sorted(raw_pareto)]
    return {
        "formal_analysis_contract_version": CONTRACT_VERSION,
        "status": "formal_supplementary_analysis_ready",
        "primary_decision": primary_decision,
        "secondary_holm": _holm(secondary, SECONDARY_ALPHA),
        "subgroup_bh_fdr": _bh(subgroups, SUBGROUP_Q),
        "pareto_frontiers": _pareto(pareto, registry["cost_axes"]),
        "hashes": {
            "analysis_registry_sha256": expected_registry_sha256,
            "formal_k50_result_sha256": _sha256(_canonical_json(formal_k50_result)),
            "secondary_results_sha256": _sha256(_canonical_jsonl(ordered_secondary)),
            "subgroup_results_sha256": _sha256(_canonical_jsonl(ordered_subgroups)),
            "pareto_points_sha256": _sha256(_canonical_jsonl(ordered_pareto)),
        },
        "multiplicity_contract": {
            "primary_endpoint_correction": "none_single_preregistered_endpoint",
            "secondary": {"method": "holm", "alpha": SECONDARY_ALPHA},
            "subgroups": {
                "method": "benjamini_hochberg",
                "q": SUBGROUP_Q,
                "exploratory": True,
            },
        },
        "superiority_claim_authorized": False,
        "paper_result_eligible": False,
        "action_policy": "no_action",
        "recovery_evaluated": False,
        "claims": {
            "dataset_complete": False,
            "empirical_superiority": False,
            "user_experience_improvement": False,
            "dismissal_or_recovery": False,
        },
    }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FormalAnalysisError(f"{path.name}: invalid JSON: {error}") from error
    _require(isinstance(value, dict), f"{path.name}: expected a JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise FormalAnalysisError(f"{path.name}: cannot read JSONL: {error}") from error
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line, object_pairs_hook=_strict_object)
        except json.JSONDecodeError as error:
            raise FormalAnalysisError(
                f"{path.name}:{line_number}: invalid JSON: {error}"
            ) from error
        _require(isinstance(value, dict), f"{path.name}:{line_number}: row must be an object")
        rows.append(value)
    _require(bool(rows), f"{path.name}: input is empty")
    return rows


def _require_private_input(path: Path, suffix: str) -> None:
    _require("private" in path.parts and path.name.endswith(suffix), f"{path.name} must be private {suffix}")
    _require(path.is_file() and not path.is_symlink(), f"{path.name} does not exist or is a symlink")


def _write_private_new(path: Path, payload: bytes) -> None:
    _require(path.parent.name == "private", "output must be directly under a private directory")
    _require(path.name.endswith(".private.json"), "output must end with .private.json")
    _require(not path.exists(), f"output {path.name} already exists; replacement is forbidden")
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
            raise FormalAnalysisError(
                f"output {path.name} already exists; replacement is forbidden"
            ) from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-registry", required=True, type=Path)
    parser.add_argument("--expected-registry-sha256", required=True)
    parser.add_argument("--formal-k50-result", required=True, type=Path)
    parser.add_argument("--secondary-results", required=True, type=Path)
    parser.add_argument("--subgroup-results", required=True, type=Path)
    parser.add_argument("--pareto-points", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        for path, suffix in (
            (args.analysis_registry, ".private.json"),
            (args.formal_k50_result, ".private.json"),
            (args.secondary_results, ".private.jsonl"),
            (args.subgroup_results, ".private.jsonl"),
            (args.pareto_points, ".private.jsonl"),
        ):
            _require_private_input(path, suffix)
        result = finalize_formal_analysis(
            analysis_registry=_read_json(args.analysis_registry),
            expected_registry_sha256=args.expected_registry_sha256,
            formal_k50_result=_read_json(args.formal_k50_result),
            secondary_results=_read_jsonl(args.secondary_results),
            subgroup_results=_read_jsonl(args.subgroup_results),
            pareto_points=_read_jsonl(args.pareto_points),
        )
        _write_private_new(
            args.output,
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
            + b"\n",
        )
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "status": result["status"],
                "primary_decision": result["primary_decision"],
                "superiority_claim_authorized": False,
                "paper_result_eligible": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
