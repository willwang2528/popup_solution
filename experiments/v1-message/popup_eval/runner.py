"""Reproducible action-free experiment orchestration."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .baselines import (
    MajorityNoInputBaseline,
    MessageGapRouter,
    PredictionAdapter,
    StructuredTextRuleBaseline,
    select_random_matched_ids,
)
from .metrics import evaluate_predictions


METHODS = {
    "majority",
    "structured",
    "visual-adapter",
    "mg-pu",
    "always-visual",
    "empty-tree",
    "random-matched",
}
FORBIDDEN_PREDICTION_KEYS = {
    "action",
    "action_semantics",
    "coordinate",
    "selector",
    "target",
    "target_candidate_id",
    "execution_channel",
}


class ContractError(ValueError):
    pass


def validate_frozen_items(items: list[dict[str, Any]]) -> None:
    if not items:
        raise ContractError("evaluation input is empty")
    ids: list[str] = []
    for item in items:
        identity = item.get("identity", {})
        item_id = identity.get("item_id")
        if not item_id:
            raise ContractError("every item requires identity.item_id")
        ids.append(item_id)
        profile = item.get("message_judgment", {}).get("profile")
        if profile not in {None, "popup_message_judgment_v1"}:
            raise ContractError(f"{item_id}: unsupported non-v1 profile {profile!r}")
        if item.get("action_attempts") != []:
            raise ContractError(f"{item_id}: v1 evaluation is strictly action-free")
        phases = {observation.get("phase") for observation in item.get("observations", [])}
        if phases & {"post_action", "task_check"}:
            raise ContractError(f"{item_id}: v1 accepts only pre-action observations")
        decision = item.get("decision", {}).get("policy", {}).get("decision")
        if decision not in {None, "no_action", "abstain"}:
            raise ContractError(f"{item_id}: action decision is forbidden in v1")
    if len(ids) != len(set(ids)):
        raise ContractError("evaluation item ids must be unique")


def _partition_metric_items(
    items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    def has_nonempty_evidence_uri(value: Any) -> bool:
        return isinstance(value, list) and any(
            isinstance(reference, dict)
            and isinstance(reference.get("uri"), str)
            and bool(reference["uri"].strip())
            for reference in value
        )

    def has_human_adjudication(
        item: dict[str, Any], pointer: str, label_name: str, expected_value: Any
    ) -> bool:
        for annotation in item.get("annotations", []):
            if (
                annotation.get("target_json_pointer") == pointer
                and annotation.get("label_name") == label_name
                and annotation.get("label_value") == expected_value
                and annotation.get("annotator_role")
                in {"researcher", "target_user", "accessibility_expert"}
                and annotation.get("adjudication_status") == "adjudicated"
                and isinstance(annotation.get("adjudicator_id_pseudonymous"), str)
                and bool(annotation["adjudicator_id_pseudonymous"].strip())
                and has_nonempty_evidence_uri(annotation.get("evidence_uris"))
            ):
                return True
        return False

    eligible: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for item in items:
        labels = item.get("message_judgment", {}).get("labels", {})
        reasons = list(item.get("evaluation_exclusion_reasons", []))
        popup_present = labels.get("popup_present_gt")
        if not isinstance(popup_present, bool):
            reasons.append("resolved_presence_gold_missing")
        else:
            record_kind = item.get("identity", {}).get("record_kind")
            if record_kind == "synthetic_schema_fixture":
                pass
            elif record_kind == "annotation_pilot_candidate":
                provenance = item.get("adjudication_provenance", {})
                if (
                    provenance.get("adjudication_status") != "resolved"
                    or provenance.get("evidence_rechecked_via_adapter") is not True
                ):
                    reasons.append("verified_pilot_adjudication_missing")
            else:
                judgment = item.get("message_judgment", {})
                metric_eligibility = judgment.get("eligibility", {})
                if metric_eligibility.get("eligible_for_v1_presence_metric") is not True:
                    reasons.append("presence_metric_eligibility_not_verified")
                if metric_eligibility.get("exclusion_reasons"):
                    reasons.append("item_has_metric_exclusion_reasons")
                if not has_nonempty_evidence_uri(labels.get("evidence_uris")):
                    reasons.append("human_label_evidence_missing")
                if not has_human_adjudication(
                    item,
                    "/message_judgment/labels/popup_present_gt",
                    "popup_present_gt",
                    popup_present,
                ):
                    reasons.append("human_presence_adjudication_missing")
                if popup_present:
                    if metric_eligibility.get("eligible_for_v1_message_metric") is not True:
                        reasons.append("message_metric_eligibility_not_verified")
                    message_text = labels.get("message_text_gt")
                    if not has_human_adjudication(
                        item,
                        "/message_judgment/labels/message_text_gt",
                        "message_text_gt",
                        message_text,
                    ):
                        reasons.append("human_message_adjudication_missing")
                    critical_facts = labels.get("critical_facts_gt", [])
                    if critical_facts and not has_human_adjudication(
                        item,
                        "/message_judgment/labels/critical_facts_gt",
                        "critical_facts_gt",
                        critical_facts,
                    ):
                        reasons.append("human_critical_facts_adjudication_missing")
        if reasons:
            excluded.append({"item_id": item["identity"]["item_id"], "reasons": sorted(set(reasons))})
        else:
            eligible.append(item)
    return eligible, excluded


def _make_baseline(
    method: str,
    items: list[dict[str, Any]],
    *,
    fit_items: list[dict[str, Any]] | None,
    prediction_rows: list[dict[str, Any]] | None,
    seed: int,
):
    structured = StructuredTextRuleBaseline()
    visual = PredictionAdapter.from_rows(prediction_rows or [])
    if method == "majority":
        if not fit_items:
            raise ContractError("majority requires an explicit, disjoint --fit-items split")
        overlap = {item["identity"]["item_id"] for item in items} & {
            item["identity"]["item_id"] for item in fit_items
        }
        if overlap:
            raise ContractError(f"majority fit/evaluation item ids overlap: {sorted(overlap)}")
        return MajorityNoInputBaseline.fit(fit_items), {}
    if method == "structured":
        return structured, {}
    if method == "visual-adapter":
        return visual, {}
    if method in {"mg-pu", "always-visual", "empty-tree"}:
        return MessageGapRouter(structured, visual, mode=method), {}

    mgpu = MessageGapRouter(structured, visual, mode="mg-pu")
    matched_count = sum(mgpu.predict(item)["visual_call_count"] for item in items)
    selected = select_random_matched_ids(items, matched_count, seed)
    return (
        MessageGapRouter(structured, visual, mode="random-matched", random_call_ids=selected),
        {"matched_visual_call_count": matched_count, "random_call_item_ids": sorted(selected)},
    )


def _evidence_level(items: list[dict[str, Any]]) -> str:
    if all(item["identity"].get("record_kind") == "synthetic_schema_fixture" for item in items):
        return "synthetic_pipeline_fixture"
    if any(item["identity"].get("record_kind") == "annotation_pilot_candidate" for item in items):
        return "adjudicated_annotation_pilot"
    return "technical_dataset_evaluation"


def run_experiment(
    items: list[dict[str, Any]],
    method: str,
    seed: int = 0,
    *,
    fit_items: list[dict[str, Any]] | None = None,
    prediction_rows: list[dict[str, Any]] | None = None,
    semantic_annotations: dict[tuple[str, str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if method not in METHODS:
        raise ContractError(f"unknown method {method!r}; expected one of {sorted(METHODS)}")
    validate_frozen_items(items)
    if fit_items:
        validate_frozen_items(fit_items)
    metric_items, excluded = _partition_metric_items(items)
    if not metric_items:
        raise ContractError("no items have resolved, metric-eligible presence gold")

    baseline, method_config = _make_baseline(
        method,
        metric_items,
        fit_items=fit_items,
        prediction_rows=prediction_rows,
        seed=seed,
    )
    predictions = [baseline.predict(item) for item in metric_items]
    for prediction in predictions:
        forbidden = FORBIDDEN_PREDICTION_KEYS & set(prediction)
        if forbidden:
            raise ContractError(f"action-bearing prediction keys are forbidden: {sorted(forbidden)}")

    metrics = evaluate_predictions(metric_items, predictions, semantic_annotations)
    evidence_level = _evidence_level(metric_items)
    for prediction in predictions:
        prediction["evidence_level"] = evidence_level
        prediction["paper_result_eligible"] = False
    metrics["evidence_level"] = evidence_level
    metrics["paper_result_eligible"] = False
    route_counts = Counter(prediction["route_reason"] for prediction in predictions)
    run = {
        "experiment_contract_version": "popup-message-eval-v1.0",
        "method": method,
        "seed": seed,
        "action_policy": "no_action",
        "input_item_count": len(items),
        "evaluated_item_count": len(metric_items),
        "excluded_item_count": len(excluded),
        "excluded_items": excluded,
        "method_config": method_config,
        "route_counts": dict(sorted(route_counts.items())),
        "evidence_level": evidence_level,
        "paper_result_eligible": False,
        "claims": {
            "empirical_performance": False,
            "user_experience_improvement": False,
            "recovery_or_dismissal": False,
        },
    }
    return {"run": run, "metrics": metrics, "predictions": predictions}
