"""Paired, group-bootstrap comparison for exact pre-gold prediction snapshots."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from typing import Any

from .metrics import _fact_set, _message_metric_eligible, _proxy_hallucination
from .runner import ContractError, run_frozen_prediction_experiment


DEFAULT_BOOTSTRAP_SEED = 20260901


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


def _item_contributions(
    items: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    vpma_values: dict[str, bool | None],
    vpma_mode: str,
    semantic_annotations: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, dict[str, float | int]]:
    predictions_by_id = {row["item_id"]: row for row in predictions}
    contributions: dict[str, dict[str, float | int]] = {}
    for item in items:
        item_id = item["identity"]["item_id"]
        prediction = predictions_by_id[item_id]
        labels = item["message_judgment"]["labels"]
        gt_present = labels["popup_present_gt"]
        status = prediction["status"]
        pred_present = prediction.get("popup_present_pred")
        abstained = status == "abstain" or pred_present is None

        tp = tn = fp = fn = 0
        predicted_negative_on_positive = negative_abstain = 0
        if abstained:
            if gt_present:
                fn = 1
            else:
                negative_abstain = 1
        elif gt_present and pred_present:
            tp = 1
        elif gt_present and not pred_present:
            fn = 1
            predicted_negative_on_positive = 1
        elif not gt_present and pred_present:
            fp = 1
        else:
            tn = 1

        critical_recall_sum = 0.0
        critical_recall_denominator = 0
        if gt_present and _message_metric_eligible(item):
            gold_facts = _fact_set(labels.get("critical_facts_gt", []))
            if gold_facts:
                predicted_facts = _fact_set(prediction.get("critical_facts_pred", []))
                critical_recall_sum = len(gold_facts & predicted_facts) / len(gold_facts)
                critical_recall_denominator = 1

        hallucination_count = hallucination_denominator = 0
        if (
            not abstained
            and gt_present
            and pred_present is True
            and _message_metric_eligible(item)
        ):
            key = (item_id, prediction["method_id"])
            hallucinated = (
                semantic_annotations[key]["critical_hallucination"]
                if vpma_mode == "adjudicated"
                else _proxy_hallucination(labels, prediction)
            )
            hallucination_count = int(hallucinated)
            hallucination_denominator = 1

        contributions[item_id] = {
            "n": 1,
            "judged": int(not abstained),
            "tp": tp,
            "tn": tn,
            "fp": fp,
            "fn": fn,
            "predicted_negative_on_positive": predicted_negative_on_positive,
            "negative_abstain": negative_abstain,
            "critical_recall_sum": critical_recall_sum,
            "critical_recall_denominator": critical_recall_denominator,
            "hallucination_count": hallucination_count,
            "hallucination_denominator": hallucination_denominator,
            "visual_called": int(
                bool(
                    prediction.get(
                        "visual_called", prediction.get("visual_call_count", 0)
                    )
                )
            ),
            "vpma_success": int(vpma_values[item_id] is True),
        }
    return contributions


def _sum_field(
    contributions: dict[str, dict[str, float | int]],
    item_ids: list[str],
    field: str,
) -> float:
    return float(sum(contributions[item_id][field] for item_id in item_ids))


def _safe_zero_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _aggregate_contributions(
    contributions: dict[str, dict[str, float | int]], item_ids: list[str]
) -> dict[str, float | None]:
    n_items = _sum_field(contributions, item_ids, "n")
    tp = _sum_field(contributions, item_ids, "tp")
    tn = _sum_field(contributions, item_ids, "tn")
    fp = _sum_field(contributions, item_ids, "fp")
    fn = _sum_field(contributions, item_ids, "fn")
    predicted_negative = _sum_field(
        contributions, item_ids, "predicted_negative_on_positive"
    )
    negative_abstain = _sum_field(contributions, item_ids, "negative_abstain")
    positive_precision = _safe_zero_div(tp, tp + fp)
    positive_recall = _safe_zero_div(tp, tp + fn)
    positive_f1 = _safe_zero_div(
        2 * positive_precision * positive_recall,
        positive_precision + positive_recall,
    )
    negative_precision = _safe_zero_div(tn, tn + predicted_negative)
    negative_recall = _safe_zero_div(tn, tn + fp + negative_abstain)
    negative_f1 = _safe_zero_div(
        2 * negative_precision * negative_recall,
        negative_precision + negative_recall,
    )
    critical_denominator = _sum_field(
        contributions, item_ids, "critical_recall_denominator"
    )
    hallucination_denominator = _sum_field(
        contributions, item_ids, "hallucination_denominator"
    )
    return {
        "vpma_overall_success_rate": _sum_field(
            contributions, item_ids, "vpma_success"
        )
        / n_items,
        "coverage": _sum_field(contributions, item_ids, "judged") / n_items,
        "presence_macro_f1": (positive_f1 + negative_f1) / 2,
        "critical_information_recall": (
            _sum_field(contributions, item_ids, "critical_recall_sum")
            / critical_denominator
            if critical_denominator
            else None
        ),
        "critical_hallucination_rate": (
            _sum_field(contributions, item_ids, "hallucination_count")
            / hallucination_denominator
            if hallucination_denominator
            else None
        ),
        "visual_call_rate": _sum_field(contributions, item_ids, "visual_called")
        / n_items,
    }


def _paired_effect_summary(
    point_estimate: float | None,
    replicate_values: list[float | None],
) -> dict[str, Any]:
    valid = [value for value in replicate_values if value is not None]
    minimum_valid = math.ceil(0.95 * len(replicate_values))
    confidence_interval = None
    if len(valid) >= minimum_valid:
        confidence_interval = {
            "lower": _percentile(valid, 0.025),
            "upper": _percentile(valid, 0.975),
        }
    return {
        "point_estimate_difference": point_estimate,
        "bootstrap_replicates": len(replicate_values),
        "valid_replicates": len(valid),
        "minimum_valid_replicates_for_ci": minimum_valid,
        "confidence_interval_95": confidence_interval,
        "ci_status": (
            "undefined_point_estimate"
            if point_estimate is None
            else (
                "available"
                if confidence_interval is not None
                else "insufficient_valid_replicates"
            )
        ),
    }


def compare_frozen_methods(
    items: list[dict[str, Any]],
    prediction_rows: list[dict[str, Any]],
    group_rows: list[dict[str, Any]],
    *,
    method_ids: list[str],
    proposed_method_id: str,
    strongest_baseline_method_id: str,
    bootstrap_replicates: int = 10_000,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
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
    run_adjudication_hashes = {
        result["run"]["adjudication_batch_sha256"] for result in runs.values()
    }
    if len(run_adjudication_hashes) != 1:
        raise ContractError("comparison methods use different adjudication batches")
    run_metric_item_hashes = {
        result["run"]["metric_item_set_sha256"] for result in runs.values()
    }
    if len(run_metric_item_hashes) != 1:
        raise ContractError("comparison methods use different metric item sets")

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

    semantic_annotations = semantic_annotations or {}
    contribution_maps = {
        method_id: _item_contributions(
            paired_items,
            result["predictions"],
            value_maps[method_id],
            result["metrics"]["vpma"]["mode"],
            semantic_annotations,
        )
        for method_id, result in runs.items()
    }

    def sampled_item_ids(sampled_groups: list[str]) -> list[str]:
        return [item_id for group_id in sampled_groups for item_id in groups[group_id]]

    def paired_difference(sampled_groups: list[str]) -> float:
        sampled_ids = sampled_item_ids(sampled_groups)
        if not sampled_ids:
            raise ContractError("bootstrap sample is empty")
        proposed_successes = sum(proposed_values[item_id] is True for item_id in sampled_ids)
        baseline_successes = sum(baseline_values[item_id] is True for item_id in sampled_ids)
        return (proposed_successes - baseline_successes) / len(sampled_ids)

    point_estimate = paired_difference(ordered_group_ids)
    sampled_group_batches = [
        [
            _bootstrap_group_id(ordered_group_ids, seed, replicate_index, draw_index)
            for draw_index in range(len(ordered_group_ids))
        ]
        for replicate_index in range(bootstrap_replicates)
    ]
    replicate_differences = [
        paired_difference(sampled_groups) for sampled_groups in sampled_group_batches
    ]

    metric_names = (
        "vpma_overall_success_rate",
        "coverage",
        "presence_macro_f1",
        "critical_information_recall",
        "critical_hallucination_rate",
        "visual_call_rate",
    )

    def metric_difference(item_ids: list[str], metric_name: str) -> float | None:
        proposed = _aggregate_contributions(
            contribution_maps[proposed_method_id], item_ids
        )[metric_name]
        baseline = _aggregate_contributions(
            contribution_maps[strongest_baseline_method_id], item_ids
        )[metric_name]
        if proposed is None or baseline is None:
            return None
        return proposed - baseline

    full_item_ids = sampled_item_ids(ordered_group_ids)
    paired_effect_metrics: dict[str, dict[str, Any]] = {}
    for metric_name in metric_names:
        point = metric_difference(full_item_ids, metric_name)
        replicates = [
            metric_difference(sampled_item_ids(sampled_groups), metric_name)
            for sampled_groups in sampled_group_batches
        ]
        paired_effect_metrics[metric_name] = _paired_effect_summary(point, replicates)

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
    adjudication_batch_sha256 = next(iter(adjudication_hashes))
    if adjudication_batch_sha256 != next(iter(run_adjudication_hashes)):
        raise ContractError("comparison gold batch hash disagrees with frozen runs")
    if metric_item_set_sha256 != next(iter(run_metric_item_hashes)):
        raise ContractError("comparison metric item hash disagrees with frozen runs")

    method_summaries: dict[str, dict[str, Any]] = {}
    for method_id in sorted(runs):
        result = runs[method_id]
        metrics = deepcopy(result["metrics"])
        metrics["vpma"].pop("item_values", None)
        method_summaries[method_id] = {
            "frozen_prediction_sha256": result["run"]["frozen_prediction_sha256"],
            "adjudication_batch_sha256": result["run"][
                "adjudication_batch_sha256"
            ],
            "metric_item_set_sha256": result["run"]["metric_item_set_sha256"],
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
        "adjudication_batch_sha256": adjudication_batch_sha256,
        "group_map_sha256": group_map_sha256,
        "evidence_level": next(iter(evidence_levels)),
        "methods": method_summaries,
        "paired_effects": {
            "direction": "proposed_minus_reference",
            "bootstrap_unit": "group",
            "shared_draws_across_methods": True,
            "minimum_valid_replicate_fraction_for_ci": 0.95,
            "metrics": paired_effect_metrics,
        },
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
