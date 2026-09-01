"""Fail-closed finalizer for the preregistered formal K50 comparison.

This module consumes an already-produced paired cluster-bootstrap report.  It
does not read annotations or gold records and never performs popup actions.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
import re
from typing import Any, Mapping, Sequence

from .comparison import DEFAULT_BOOTSTRAP_SEED


MG_PU_METHOD_ID = "mg-pu-k50-v1"
SEEDED_RANDOM_METHOD_ID = "seeded-random-k50-v1"
DEFERRED_BLOCKERS = [
    "holm_secondary_not_implemented",
    "bh_q_0_10_subgroups_not_implemented",
    "pareto_frontier_not_implemented",
]
COMPARISON_CONTRACT_VERSION = "popup-message-paired-comparison-v1.0"
FORMAL_CONTRACT_VERSION = "popup-message-formal-k50-v1.0"
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = DEFAULT_BOOTSTRAP_SEED
HASH_FIELDS = (
    "metric_item_set_sha256",
    "adjudication_batch_sha256",
    "visual_bank_sha256",
    "visual_config_sha256",
    "budget_spec_sha256",
)
BUDGET_FIELDS = (
    "visual_calls",
    "decoded_pixels",
    "input_tokens",
    "output_tokens",
    "monetary_cost_microunits",
)
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


class FormalK50Error(ValueError):
    """Raised when evidence is incomplete or violates the formal contract."""


def _item_set_hash(item_ids: Sequence[str]) -> str:
    encoded = json.dumps(sorted(item_ids), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _selected_item_set_hash(item_ids: Sequence[str]) -> str:
    encoded = ("\n".join(sorted(item_ids)) + "\n").encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise FormalK50Error(message)


def _require_sha256(value: Any, label: str) -> str:
    _require(isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None, f"{label} must be a lowercase sha256")
    return value


def _require_int(value: Any, label: str, *, minimum: int) -> int:
    _require(type(value) is int and value >= minimum, f"{label} must be an integer >= {minimum}")
    return value


def _require_number(value: Any, label: str) -> float:
    _require(type(value) in (int, float) and math.isfinite(value), f"{label} must be a finite number")
    return float(value)


def _validated_effect(metrics: Mapping[str, Any], metric_name: str) -> tuple[float, dict[str, float]]:
    metric = metrics[metric_name]
    _require(isinstance(metric, Mapping), f"{metric_name} effect must be an object")
    _require(metric.get("ci_status") == "available", f"{metric_name} CI is unavailable")
    point = _require_number(metric.get("point_estimate_difference"), f"{metric_name} difference")
    ci = metric.get("confidence_interval_95")
    _require(isinstance(ci, Mapping), f"{metric_name} CI must be defined")
    lower = _require_number(ci.get("lower"), f"{metric_name} CI lower")
    upper = _require_number(ci.get("upper"), f"{metric_name} CI upper")
    _require(lower <= upper, f"{metric_name} CI bounds are inverted")
    return point, {"lower": lower, "upper": upper}


def _validate_report(paired_report: Mapping[str, Any]) -> tuple[int, str, str, str]:
    _require(
        paired_report.get("comparison_contract_version") == COMPARISON_CONTRACT_VERSION,
        "unsupported paired comparison contract",
    )
    _require(paired_report.get("action_policy") == "no_action", "formal v1 is no-action only")

    method_ids = paired_report.get("method_ids")
    _require(
        isinstance(method_ids, Sequence)
        and not isinstance(method_ids, (str, bytes))
        and len(method_ids) == 2
        and set(method_ids) == {MG_PU_METHOD_ID, SEEDED_RANDOM_METHOD_ID},
        "formal comparison must contain exactly the K50 pair",
    )
    _require(
        paired_report.get("proposed_method_id") == MG_PU_METHOD_ID,
        "formal proposed method must be mg-pu-k50-v1",
    )
    _require(
        paired_report.get("strongest_baseline_method_id") == SEEDED_RANDOM_METHOD_ID,
        "formal reference must be seeded-random-k50-v1",
    )

    n_items = _require_int(paired_report.get("paired_item_count"), "paired_item_count", minimum=1)
    item_hash = _require_sha256(paired_report.get("metric_item_set_sha256"), "report item-set hash")
    gold_hash = _require_sha256(paired_report.get("adjudication_batch_sha256"), "report adjudication hash")
    group_hash = _require_sha256(paired_report.get("group_map_sha256"), "report group-map hash")

    method_summaries = paired_report.get("methods")
    _require(
        isinstance(method_summaries, Mapping)
        and set(method_summaries) == {MG_PU_METHOD_ID, SEEDED_RANDOM_METHOD_ID},
        "paired report methods must be exactly the formal pair",
    )
    for method_id in (MG_PU_METHOD_ID, SEEDED_RANDOM_METHOD_ID):
        summary = method_summaries[method_id]
        _require(isinstance(summary, Mapping), f"{method_id} summary must be an object")
        _require(summary.get("evaluated_item_count") == n_items, f"{method_id} evaluated count mismatch")
        _require(summary.get("metric_item_set_sha256") == item_hash, f"{method_id} item hash mismatch")
        _require(summary.get("adjudication_batch_sha256") == gold_hash, f"{method_id} gold hash mismatch")
        summary_metrics = summary.get("metrics")
        _require(isinstance(summary_metrics, Mapping), f"{method_id} metrics must be an object")
        vpma = summary_metrics.get("vpma")
        _require(isinstance(vpma, Mapping), f"{method_id} VPMA summary must be an object")
        _require(vpma.get("mode") == "adjudicated", f"{method_id} VPMA must be adjudicated")

    paired = paired_report.get("paired_effects")
    _require(isinstance(paired, Mapping), "paired_effects must be an object")
    _require(paired.get("direction") == "proposed_minus_reference", "paired effect direction mismatch")
    _require(paired.get("bootstrap_unit") == "group", "paired effects must use group bootstrap")
    _require(paired.get("shared_draws_across_methods") is True, "bootstrap draws must be shared")

    bootstrap = paired_report.get("bootstrap")
    _require(isinstance(bootstrap, Mapping), "bootstrap metadata must be an object")
    _require(bootstrap.get("unit") == "group", "bootstrap unit must be group")
    _require(
        bootstrap.get("replicates") == BOOTSTRAP_REPLICATES,
        f"bootstrap must use exactly {BOOTSTRAP_REPLICATES} replicates",
    )
    _require(bootstrap.get("seed") == BOOTSTRAP_SEED, f"bootstrap seed must be {BOOTSTRAP_SEED}")
    _require_int(bootstrap.get("group_count"), "bootstrap group_count", minimum=5)
    return n_items, item_hash, gold_hash, group_hash


def _validate_attestations(
    method_attestations: Mapping[str, Mapping[str, Any]],
    *,
    item_hash: str,
    gold_hash: str,
) -> dict[str, dict[str, int]]:
    _require(
        set(method_attestations) == {MG_PU_METHOD_ID, SEEDED_RANDOM_METHOD_ID},
        "method attestations must be exactly the formal pair",
    )
    values: dict[str, list[str]] = {field: [] for field in HASH_FIELDS}
    actual_budgets: dict[str, dict[str, int]] = {}
    for method_id in (MG_PU_METHOD_ID, SEEDED_RANDOM_METHOD_ID):
        attestation = method_attestations[method_id]
        _require(isinstance(attestation, Mapping), f"{method_id} attestation must be an object")
        _require(attestation.get("operating_point") == "K50", f"{method_id} operating point must be K50")
        for field in HASH_FIELDS:
            values[field].append(_require_sha256(attestation.get(field), f"{method_id} {field}"))
        _require_sha256(attestation.get("selected_item_set_sha256"), f"{method_id} selected-item hash")
        actual_budget = attestation.get("actual_budget")
        _require(isinstance(actual_budget, Mapping), f"{method_id} actual_budget must be an object")
        _require(
            set(actual_budget) == set(BUDGET_FIELDS),
            f"{method_id} actual_budget field set is incomplete or unexpected",
        )
        actual_budgets[method_id] = {
            field: _require_int(
                actual_budget.get(field),
                f"{method_id} actual_budget.{field}",
                minimum=0,
            )
            for field in BUDGET_FIELDS
        }
    for field, field_values in values.items():
        _require(len(set(field_values)) == 1, f"formal methods have different {field}")
    _require(values["metric_item_set_sha256"][0] == item_hash, "attested item hash differs from report")
    _require(values["adjudication_batch_sha256"][0] == gold_hash, "attested gold hash differs from report")
    return actual_budgets


def _validate_group_map(
    paired_report: Mapping[str, Any],
    group_map_attestation: Mapping[str, Any],
    *,
    group_hash: str,
) -> None:
    _require(
        _require_sha256(group_map_attestation.get("group_map_sha256"), "attested group-map hash")
        == group_hash,
        "group-map hash differs from paired report",
    )
    _require(
        group_map_attestation.get("formal_leakage_control_sufficient") is True,
        "group map is not sufficient for formal leakage control",
    )
    _require(group_map_attestation.get("used_as_model_input") is False, "group map was used as model input")
    _require(group_map_attestation.get("frozen_before_gold") is True, "group map was not frozen before gold")
    group_count = _require_int(group_map_attestation.get("group_count"), "formal group_count", minimum=5)
    _require_int(group_map_attestation.get("app_group_count"), "formal app_group_count", minimum=5)
    _require_int(
        group_map_attestation.get("popup_template_family_count"),
        "formal popup_template_family_count",
        minimum=3,
    )
    _require(group_count == paired_report["bootstrap"]["group_count"], "formal and bootstrap group counts differ")


def _validate_predictions(
    prediction_rows: Sequence[Mapping[str, Any]],
    method_attestations: Mapping[str, Mapping[str, Any]],
    *,
    expected_n: int,
    expected_item_hash: str,
) -> tuple[int, int, dict[str, Any]]:
    _require(
        isinstance(prediction_rows, Sequence) and not isinstance(prediction_rows, (str, bytes)),
        "prediction_rows must be a sequence",
    )
    rows_by_method: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in prediction_rows:
        _require(isinstance(row, Mapping), "each prediction row must be an object")
        method_id = row.get("method_id")
        _require(method_id in {MG_PU_METHOD_ID, SEEDED_RANDOM_METHOD_ID}, "unexpected prediction method")
        _require(type(row.get("visual_called")) is bool, "visual_called must be boolean")
        _require(row.get("human_gold_used") is False, "prediction row used human gold")
        _require(row.get("scored") is False, "prediction row was scored before confirmation")
        _require(row.get("paper_result_eligible") is False, "pregold prediction was marked paper eligible")
        _require(row.get("action_policy") == "no_action", "formal v1 prediction must be no-action")
        pilot_item_id = row.get("pilot_item_id")
        _require(isinstance(pilot_item_id, str) and bool(pilot_item_id), "pilot_item_id must be non-empty")
        rows_by_method[method_id].append(row)

    _require(set(rows_by_method) == {MG_PU_METHOD_ID, SEEDED_RANDOM_METHOD_ID}, "prediction pair is incomplete")
    proposed_ids = [row["pilot_item_id"] for row in rows_by_method[MG_PU_METHOD_ID]]
    _require(len(proposed_ids) == expected_n, "proposed prediction count differs from paired report")
    _require(len(set(proposed_ids)) == expected_n, "proposed predictions contain duplicate items")
    _require(_item_set_hash(proposed_ids) == expected_item_hash, "prediction item hash differs from report")
    k = math.ceil(0.5 * expected_n)

    selected_by_method: dict[str, set[str]] = {}
    for method_id in (MG_PU_METHOD_ID, SEEDED_RANDOM_METHOD_ID):
        rows = rows_by_method[method_id]
        item_ids = [row["pilot_item_id"] for row in rows]
        _require(len(item_ids) == expected_n, f"{method_id} prediction count mismatch")
        _require(len(set(item_ids)) == expected_n, f"{method_id} predictions contain duplicate items")
        _require(set(item_ids) == set(proposed_ids), "both methods must cover the identical item set")
        selected = [row["pilot_item_id"] for row in rows if row["visual_called"]]
        selected_by_method[method_id] = set(selected)
        _require(len(selected) == k, f"{method_id} must select exactly K={k} items")
        _require(
            _selected_item_set_hash(selected) == method_attestations[method_id]["selected_item_set_sha256"],
            f"{method_id} selected-item hash mismatch",
        )
    proposed_selected = selected_by_method[MG_PU_METHOD_ID]
    reference_selected = selected_by_method[SEEDED_RANDOM_METHOD_ID]
    overlap_count = len(proposed_selected.intersection(reference_selected))
    same_selected_item_set = proposed_selected == reference_selected
    return expected_n, k, {
        "same_selected_item_set": same_selected_item_set,
        "overlap_count": overlap_count,
        "overlap_fraction_of_k": overlap_count / k,
        "comparison_interpretation": (
            "budget_and_item_matched"
            if same_selected_item_set
            else "budget_matched_not_item_matched"
        ),
        "caveat": (
            None
            if same_selected_item_set
            else "equal visual budget does not control which items receive visual evidence"
        ),
    }


def finalize_formal_k50_confirmation(
    paired_report: Mapping[str, Any],
    prediction_rows: Sequence[Mapping[str, Any]],
    method_attestations: Mapping[str, Mapping[str, Any]],
    group_map_attestation: Mapping[str, Any],
) -> dict[str, Any]:
    """Finalize the formal K50 superiority decision from frozen evidence."""
    try:
        _require(isinstance(paired_report, Mapping), "paired_report must be an object")
        _require(isinstance(method_attestations, Mapping), "method_attestations must be an object")
        _require(isinstance(group_map_attestation, Mapping), "group_map_attestation must be an object")

        n_items, item_hash, gold_hash, group_hash = _validate_report(paired_report)
        actual_budgets = _validate_attestations(
            method_attestations, item_hash=item_hash, gold_hash=gold_hash
        )
        _validate_group_map(paired_report, group_map_attestation, group_hash=group_hash)
        n_items, k, selection_relationship = _validate_predictions(
            prediction_rows,
            method_attestations,
            expected_n=n_items,
            expected_item_hash=item_hash,
        )

        metrics = paired_report["paired_effects"].get("metrics")
        _require(isinstance(metrics, Mapping), "paired metric effects must be an object")
        vpma_point, vpma_ci = _validated_effect(metrics, "vpma_overall_success_rate")
        coverage_point, coverage_ci = _validated_effect(metrics, "coverage")
        hallucination_point, hallucination_ci = _validated_effect(metrics, "critical_hallucination_rate")

        proposed_budget = actual_budgets[MG_PU_METHOD_ID]
        reference_budget = actual_budgets[SEEDED_RANDOM_METHOD_ID]
        budget_equality = (
            proposed_budget["visual_calls"]
            == reference_budget["visual_calls"]
            == k
            and proposed_budget["decoded_pixels"]
            == reference_budget["decoded_pixels"]
        )
        actual_budget_non_worsening = all(
            proposed_budget[field] <= reference_budget[field]
            for field in (
                "input_tokens",
                "output_tokens",
                "monetary_cost_microunits",
            )
        )

        gates = {
            "vpma_at_least_plus_2pp": vpma_point >= 0.02,
            "vpma_ci_above_zero": vpma_ci["lower"] > 0,
            "coverage_non_worsening": coverage_point >= 0 and coverage_ci["lower"] >= 0,
            "hallucination_non_worsening": hallucination_point <= 0 and hallucination_ci["upper"] <= 0,
            "budget_equality": budget_equality,
            "actual_budget_non_worsening": actual_budget_non_worsening,
        }

        return {
            "formal_contract_version": FORMAL_CONTRACT_VERSION,
            "primary_pair": {
                "proposed": MG_PU_METHOD_ID,
                "reference": SEEDED_RANDOM_METHOD_ID,
            },
            "n_items": n_items,
            "k": k,
            "primary_endpoint": {
                "name": "vpma_overall_success_rate",
                "vpma_difference": vpma_point,
                "confidence_interval_95": vpma_ci,
            },
            "paired_cluster_bootstrap": {
                "unit": paired_report["bootstrap"]["unit"],
                "group_count": paired_report["bootstrap"]["group_count"],
                "replicates": paired_report["bootstrap"]["replicates"],
                "seed": paired_report["bootstrap"]["seed"],
            },
            "actual_budget": {
                "proposed": proposed_budget,
                "reference": reference_budget,
            },
            "selection_relationship": selection_relationship,
            "gates": gates,
            "decision": "continue" if all(gates.values()) else "withdraw_superiority",
            "blockers": list(DEFERRED_BLOCKERS),
            "action_policy": "no_action",
            "recovery_evaluated": False,
            "paper_result_eligible": False,
        }
    except FormalK50Error:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise FormalK50Error(f"malformed formal K50 evidence: {exc}") from exc
