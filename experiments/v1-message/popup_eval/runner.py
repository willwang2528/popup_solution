"""Reproducible action-free experiment orchestration."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
from typing import Any

from .baselines import (
    build_shuffled_gap_permutation,
    MajorityNoInputBaseline,
    MessageGapRouter,
    PopupScopedStructuredTextBaseline,
    PredictionAdapter,
    StructuredTextRuleBaseline,
    select_random_matched_ids,
)
from .metrics import evaluate_predictions
from .the_ok_baseline import INDICATORS_SHA256, TheOkTextBaseline, UPSTREAM_REVISION


METHODS = {
    "majority",
    "structured",
    "the-ok",
    "visual-adapter",
    "mg-pu",
    "always-visual",
    "empty-tree",
    "random-matched",
    "shuffled-gap",
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
FROZEN_PREDICTION_KEYS = {
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
            identity = item.get("identity", {})
            record_kind = identity.get("record_kind")
            provenance = item.get("adjudication_provenance", {})
            is_finalized_pilot = (
                isinstance(identity.get("pilot_item_id"), str)
                and provenance.get("adjudication_status") == "resolved"
                and provenance.get("evidence_rechecked_via_adapter") is True
                and isinstance(provenance.get("adjudication_batch_sha256"), str)
                and len(provenance["adjudication_batch_sha256"]) == 64
            )
            if record_kind == "synthetic_schema_fixture":
                pass
            elif record_kind == "annotation_pilot_candidate" or is_finalized_pilot:
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
                if (
                    popup_present
                    and labels.get("message_text_observability") == "complete"
                    and metric_eligibility.get("eligible_for_v1_message_metric") is True
                ):
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
    popup_scoped_structured = PopupScopedStructuredTextBaseline()
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
    if method == "the-ok":
        return TheOkTextBaseline(), {
            "upstream_revision": UPSTREAM_REVISION,
            "vendored_indicators_sha256": INDICATORS_SHA256,
            "adaptation": "matched_appium_element_text_projection",
        }
    if method == "visual-adapter":
        return visual, {}
    if method in {"mg-pu", "always-visual", "empty-tree"}:
        return MessageGapRouter(popup_scoped_structured, visual, mode=method), {}

    mgpu = MessageGapRouter(popup_scoped_structured, visual, mode="mg-pu")
    matched_count = sum(mgpu.predict(item)["visual_call_count"] for item in items)
    if method == "shuffled-gap":
        assignments = build_shuffled_gap_permutation(
            items, popup_scoped_structured, seed
        )
        shuffled_count = sum(
            bool(assignment["gap_reasons"])
            for assignment in assignments.values()
        )
        if shuffled_count != matched_count:
            raise ContractError("shuffled-gap visual-call budget differs from MG-PU")
        permutation = [
            {
                "item_id": item_id,
                "source_item_id": assignments[item_id]["source_item_id"],
                "gap_reasons": list(assignments[item_id]["gap_reasons"]),
            }
            for item_id in sorted(assignments)
        ]
        return (
            MessageGapRouter(
                popup_scoped_structured,
                visual,
                mode="shuffled-gap",
                shuffled_gap_assignments=assignments,
            ),
            {
                "matched_visual_call_count": matched_count,
                "shuffle_seed": seed,
                "shuffled_gap_permutation": permutation,
            },
        )
    selected = select_random_matched_ids(items, matched_count, seed)
    return (
        MessageGapRouter(
            popup_scoped_structured,
            visual,
            mode="random-matched",
            random_call_ids=selected,
        ),
        {"matched_visual_call_count": matched_count, "random_call_item_ids": sorted(selected)},
    )


def _evidence_level(items: list[dict[str, Any]]) -> str:
    if all(item["identity"].get("record_kind") == "synthetic_schema_fixture" for item in items):
        return "synthetic_pipeline_fixture"
    if any(
        item["identity"].get("record_kind") == "annotation_pilot_candidate"
        or "adjudication_batch_sha256" in item.get("adjudication_provenance", {})
        for item in items
    ):
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


def _validate_frozen_prediction_row(
    row: dict[str, Any], method_id: str
) -> None:
    if set(row) != FROZEN_PREDICTION_KEYS:
        missing = sorted(FROZEN_PREDICTION_KEYS - set(row))
        unexpected = sorted(set(row) - FROZEN_PREDICTION_KEYS)
        raise ContractError(
            f"frozen prediction keys are invalid: missing={missing} unexpected={unexpected}"
        )
    if row["method_id"] != method_id:
        raise ContractError("frozen prediction method_id mismatch")
    if row["action_policy"] != "no_action":
        raise ContractError("frozen prediction must be action-free")
    if row["human_gold_used"] is not False or row["scored"] is not False:
        raise ContractError("frozen prediction must be gold-blind and unscored")
    if row["paper_result_eligible"] is not False:
        raise ContractError("pre-gold prediction cannot claim paper-result eligibility")
    if not isinstance(row["pilot_item_id"], str) or not row["pilot_item_id"].startswith(
        "PMJ-PILOT-"
    ):
        raise ContractError("frozen prediction requires pilot_item_id")
    if not isinstance(row["visual_called"], bool):
        raise ContractError("frozen prediction visual_called must be boolean")
    if row["status"] not in {"judged", "abstain"}:
        raise ContractError("frozen prediction status is invalid")
    facts = row["critical_facts_pred"]
    if not isinstance(facts, list) or not all(isinstance(fact, str) for fact in facts):
        raise ContractError("frozen prediction critical facts must be strings")
    confidence = row["confidence"]
    if confidence is not None and (
        not isinstance(confidence, (int, float))
        or isinstance(confidence, bool)
        or not 0 <= confidence <= 1
    ):
        raise ContractError("frozen prediction confidence is invalid")
    present = row["popup_present_pred"]
    message = row["message_text_pred"]
    if row["status"] == "abstain":
        if present is not None or message is not None or facts or confidence is not None:
            raise ContractError("abstaining frozen prediction must not carry an answer")
    elif not isinstance(present, bool):
        raise ContractError("judged frozen prediction requires boolean presence")
    elif present:
        if not isinstance(message, str) or not message.strip():
            raise ContractError("positive frozen prediction requires a message")
    elif message is not None or facts:
        raise ContractError("negative frozen prediction cannot carry message semantics")


def run_frozen_prediction_experiment(
    items: list[dict[str, Any]],
    prediction_rows: list[dict[str, Any]],
    method_id: str,
    *,
    semantic_annotations: dict[tuple[str, str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Score one exact pre-gold method snapshot without rerunning its implementation."""
    validate_frozen_items(items)
    metric_items, excluded = _partition_metric_items(items)
    if not metric_items:
        raise ContractError("no items have resolved, metric-eligible presence gold")

    adjudication_hashes = {
        item.get("adjudication_provenance", {}).get("adjudication_batch_sha256")
        for item in items
    }
    if len(adjudication_hashes) != 1:
        raise ContractError("frozen scoring requires one adjudication batch hash")
    adjudication_batch_sha256 = next(iter(adjudication_hashes))
    if not isinstance(adjudication_batch_sha256, str) or len(
        adjudication_batch_sha256
    ) != 64:
        raise ContractError("frozen scoring requires one adjudication batch hash")

    all_items_by_pilot: dict[str, dict[str, Any]] = {}
    for item in items:
        pilot_id = item.get("identity", {}).get("pilot_item_id")
        if not isinstance(pilot_id, str):
            raise ContractError("frozen prediction scoring requires pilot_item_id on every item")
        if pilot_id in all_items_by_pilot:
            raise ContractError(f"duplicate input pilot_item_id: {pilot_id}")
        all_items_by_pilot[pilot_id] = item

    selected: dict[str, dict[str, Any]] = {}
    for raw_row in prediction_rows:
        if raw_row.get("method_id") != method_id:
            continue
        row = deepcopy(raw_row)
        _validate_frozen_prediction_row(row, method_id)
        pilot_id = row["pilot_item_id"]
        if pilot_id not in all_items_by_pilot:
            raise ContractError(f"frozen prediction has unknown pilot_item_id: {pilot_id}")
        if pilot_id in selected:
            raise ContractError(f"duplicate frozen prediction: {method_id}/{pilot_id}")
        selected[pilot_id] = row
    missing = sorted(set(all_items_by_pilot) - set(selected))
    if missing:
        raise ContractError(f"missing frozen predictions for {method_id}: {missing}")

    sorted_rows = [selected[pilot_id] for pilot_id in sorted(selected)]
    canonical_payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in sorted_rows
    ).encode("utf-8")
    prediction_sha256 = hashlib.sha256(canonical_payload).hexdigest()

    metric_item_pilot_ids = sorted(
        item["identity"]["pilot_item_id"] for item in metric_items
    )
    metric_item_set_sha256 = hashlib.sha256(
        json.dumps(metric_item_pilot_ids, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    predictions: list[dict[str, Any]] = []
    for item in metric_items:
        pilot_id = item["identity"]["pilot_item_id"]
        frozen = selected[pilot_id]
        observation_id = (
            item["observations"][0].get("observation_id")
            if item.get("observations")
            else None
        )
        predictions.append(
            {
                "item_id": item["identity"]["item_id"],
                "method_id": method_id,
                "status": frozen["status"],
                "popup_present_pred": frozen["popup_present_pred"],
                "message_text_pred": frozen["message_text_pred"],
                "critical_facts_pred": deepcopy(frozen["critical_facts_pred"]),
                "confidence": frozen["confidence"],
                "visual_called": frozen["visual_called"],
                "visual_call_count": int(frozen["visual_called"]),
                "route_reason": frozen["route_reason"],
                "source_observation_id": observation_id,
            }
        )

    metrics = evaluate_predictions(metric_items, predictions, semantic_annotations)
    evidence_level = _evidence_level(metric_items)
    for prediction in predictions:
        prediction["evidence_level"] = evidence_level
        prediction["paper_result_eligible"] = False
    metrics["evidence_level"] = evidence_level
    metrics["paper_result_eligible"] = False
    run = {
        "experiment_contract_version": "popup-message-eval-v1.0",
        "method": method_id,
        "prediction_source": "pregold_frozen_snapshot",
        "frozen_prediction_sha256": prediction_sha256,
        "adjudication_batch_sha256": adjudication_batch_sha256,
        "metric_item_set_sha256": metric_item_set_sha256,
        "action_policy": "no_action",
        "input_item_count": len(items),
        "evaluated_item_count": len(metric_items),
        "excluded_item_count": len(excluded),
        "excluded_items": excluded,
        "route_counts": dict(
            sorted(Counter(row["route_reason"] for row in predictions).items())
        ),
        "evidence_level": evidence_level,
        "paper_result_eligible": False,
        "claims": {
            "empirical_performance": False,
            "user_experience_improvement": False,
            "recovery_or_dismissal": False,
        },
    }
    return {"run": run, "metrics": metrics, "predictions": predictions}
