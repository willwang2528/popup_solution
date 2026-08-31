"""Paired, group-bootstrap comparison for exact pre-gold prediction snapshots."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any

from .runner import ContractError, run_frozen_prediction_experiment


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


def _prepare_group_map(
    items: list[dict[str, Any]], group_rows: list[dict[str, Any]]
) -> tuple[dict[str, str], str]:
    expected_ids = {
        item["identity"].get("pilot_item_id") for item in items
    }
    if None in expected_ids or not all(isinstance(value, str) for value in expected_ids):
        raise ContractError("group-map comparison requires pilot_item_id on every item")
    by_pilot: dict[str, str] = {}
    canonical_rows: list[dict[str, Any]] = []
    for row in group_rows:
        if set(row) not in (
            {"pilot_item_id", "cluster_id"},
            {"pilot_item_id", "cluster_id", "cluster_source"},
        ):
            raise ContractError("group-map row has invalid keys")
        pilot_id = row.get("pilot_item_id")
        cluster_id = row.get("cluster_id")
        cluster_source = row.get("cluster_source")
        if not isinstance(pilot_id, str) or not isinstance(cluster_id, str) or not cluster_id.strip():
            raise ContractError("group-map row has invalid pilot_item_id or cluster_id")
        if cluster_source is not None and (
            not isinstance(cluster_source, str) or not cluster_source.strip()
        ):
            raise ContractError("group-map cluster_source must be a non-empty string")
        if pilot_id not in expected_ids:
            raise ContractError(f"group-map has unknown pilot_item_id: {pilot_id}")
        if pilot_id in by_pilot:
            raise ContractError(f"group-map has duplicate pilot_item_id: {pilot_id}")
        by_pilot[pilot_id] = cluster_id
        canonical_rows.append(deepcopy(row))
    missing = sorted(expected_ids - set(by_pilot))
    if missing:
        raise ContractError(f"group-map is missing pilot_item_id values: {missing}")
    canonical_payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in sorted(canonical_rows, key=lambda row: row["pilot_item_id"])
    ).encode("utf-8")
    return by_pilot, hashlib.sha256(canonical_payload).hexdigest()


def _bootstrap_group_id(
    group_ids: list[str], seed: int, replicate_index: int, draw_index: int
) -> str:
    digest = hashlib.sha256(
        f"{seed}:{replicate_index}:{draw_index}".encode("ascii")
    ).digest()
    index = int.from_bytes(digest[:8], "big") % len(group_ids)
    return group_ids[index]


def compare_frozen_methods(
    items: list[dict[str, Any]],
    prediction_rows: list[dict[str, Any]],
    group_rows: list[dict[str, Any]],
    *,
    method_ids: list[str],
    proposed_method_id: str,
    strongest_baseline_method_id: str,
    bootstrap_replicates: int = 10_000,
    seed: int = 0,
    semantic_annotations: dict[tuple[str, str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compare methods on one exact item set with a predeclared baseline.

    The primary bootstrap statistic is the paired difference in VPMA overall
    success rate, where null/abstention is a failure.  Groups, not individual
    rows, are sampled with replacement.
    """
    if len(method_ids) < 2 or len(method_ids) != len(set(method_ids)):
        raise ContractError("comparison requires at least two unique method_ids")
    if proposed_method_id not in method_ids:
        raise ContractError("proposed_method_id must be included in method_ids")
    if strongest_baseline_method_id not in method_ids:
        raise ContractError("strongest_baseline_method_id must be included in method_ids")
    if proposed_method_id == strongest_baseline_method_id:
        raise ContractError("proposed method and strongest baseline must differ")
    if not isinstance(bootstrap_replicates, int) or bootstrap_replicates <= 0:
        raise ContractError("bootstrap_replicates must be a positive integer")

    ordered_items = sorted(items, key=lambda item: item["identity"]["item_id"])
    group_by_pilot, group_map_sha256 = _prepare_group_map(ordered_items, group_rows)
    runs = {
        method_id: run_frozen_prediction_experiment(
            ordered_items,
            prediction_rows,
            method_id,
            semantic_annotations=semantic_annotations,
        )
        for method_id in method_ids
    }
    paired_item_ids: list[str] | None = None
    value_maps: dict[str, dict[str, bool | None]] = {}
    evidence_levels: set[str] = set()
    vpma_modes: set[str] = set()
    for method_id, result in runs.items():
        prediction_ids = [row["item_id"] for row in result["predictions"]]
        if paired_item_ids is None:
            paired_item_ids = prediction_ids
        elif prediction_ids != paired_item_ids:
            raise ContractError(f"{method_id}: comparison item order or coverage differs")
        values = result["metrics"]["vpma"]["item_values"]
        if set(values) != set(paired_item_ids):
            raise ContractError(f"{method_id}: VPMA item coverage differs")
        value_maps[method_id] = values
        evidence_levels.add(result["run"]["evidence_level"])
        vpma_modes.add(result["metrics"]["vpma"]["mode"])
    if len(evidence_levels) != 1:
        raise ContractError("comparison methods have inconsistent evidence levels")
    if len(vpma_modes) != 1:
        raise ContractError("comparison methods have mixed VPMA modes")
    if paired_item_ids is None or not paired_item_ids:
        raise ContractError("comparison has no paired metric items")

    item_by_id = {item["identity"]["item_id"]: item for item in ordered_items}
    paired_items = [item_by_id[item_id] for item_id in paired_item_ids]
    groups: dict[str, list[str]] = {}
    for item in paired_items:
        pilot_id = item["identity"]["pilot_item_id"]
        groups.setdefault(group_by_pilot[pilot_id], []).append(item["identity"]["item_id"])
    ordered_group_ids = sorted(groups)
    if len(ordered_group_ids) < 2:
        raise ContractError("cluster bootstrap requires at least two groups")
    proposed_values = value_maps[proposed_method_id]
    baseline_values = value_maps[strongest_baseline_method_id]

    def paired_difference(sampled_groups: list[str]) -> float:
        sampled_item_ids = [
            item_id for group_id in sampled_groups for item_id in groups[group_id]
        ]
        if not sampled_item_ids:
            raise ContractError("bootstrap sample is empty")
        proposed_successes = sum(proposed_values[item_id] is True for item_id in sampled_item_ids)
        baseline_successes = sum(baseline_values[item_id] is True for item_id in sampled_item_ids)
        return (proposed_successes - baseline_successes) / len(sampled_item_ids)

    point_estimate = paired_difference(ordered_group_ids)
    replicate_differences = [
        paired_difference(
            [
                _bootstrap_group_id(ordered_group_ids, seed, replicate_index, draw_index)
                for draw_index in range(len(ordered_group_ids))
            ]
        )
        for replicate_index in range(bootstrap_replicates)
    ]

    metric_item_set_sha256 = hashlib.sha256(
        json.dumps(
            sorted(item["identity"]["pilot_item_id"] for item in paired_items),
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    adjudication_hashes = {
        item.get("adjudication_provenance", {}).get("adjudication_batch_sha256")
        for item in paired_items
        if item.get("adjudication_provenance", {}).get("adjudication_status") == "resolved"
    }
    if len(adjudication_hashes) != 1 or not all(
        isinstance(value, str) and len(value) == 64 for value in adjudication_hashes
    ):
        raise ContractError("comparison items do not share one adjudication batch hash")

    method_summaries: dict[str, dict[str, Any]] = {}
    for method_id in sorted(runs):
        result = runs[method_id]
        metrics = deepcopy(result["metrics"])
        metrics["vpma"].pop("item_values", None)
        method_summaries[method_id] = {
            "frozen_prediction_sha256": result["run"]["frozen_prediction_sha256"],
            "evaluated_item_count": result["run"]["evaluated_item_count"],
            "metrics": metrics,
        }

    return {
        "comparison_contract_version": "popup-message-paired-comparison-v1.0",
        "status": "exploratory_pilot_comparison",
        "scope": "popup_message_judgment_v1",
        "action_policy": "no_action",
        "analysis_tier": "exploratory_pilot",
        "method_ids": sorted(method_ids),
        "proposed_method_id": proposed_method_id,
        "strongest_baseline_method_id": strongest_baseline_method_id,
        "strongest_baseline_selection": "caller_predeclared_exploratory_reference_not_test_selected",
        "primary_pair": None,
        "exploratory_reference_pair": {
            "candidate_method_id": proposed_method_id,
            "reference_method_id": strongest_baseline_method_id,
        },
        "paired_item_count": len(paired_items),
        "metric_item_set_sha256": metric_item_set_sha256,
        "adjudication_batch_sha256": next(iter(adjudication_hashes)),
        "group_map_sha256": group_map_sha256,
        "evidence_level": next(iter(evidence_levels)),
        "methods": method_summaries,
        "bootstrap": {
            "metric": "vpma.overall_success_rate_null_as_failure.paired_difference",
            "unit": "group",
            "group_source": "explicit_private_group_map",
            "group_count": len(ordered_group_ids),
            "replicates": bootstrap_replicates,
            "seed": seed,
            "draw_algorithm": "sha256-counter-mod-v1",
            "confidence_interval": "percentile_95_type7",
            "point_estimate": point_estimate,
            "replicate_mean": sum(replicate_differences) / bootstrap_replicates,
            "confidence_interval_95": {
                "lower": _percentile(replicate_differences, 0.025),
                "upper": _percentile(replicate_differences, 0.975),
            },
        },
        "paper_result_eligible": False,
        "claims": {
            "empirical_performance": False,
            "method_superiority": False,
            "user_experience_improvement": False,
            "recovery_or_dismissal": False,
        },
    }
