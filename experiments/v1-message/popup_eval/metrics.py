"""Transparent metrics for the action-free popup-message task."""

from __future__ import annotations

from collections import Counter
import unicodedata
from typing import Any


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def normalize_text(text: str | None) -> str:
    """Apply the frozen agreement normalization without erasing content."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(normalized.split())


def token_f1(reference: str | None, prediction: str | None) -> float:
    reference_tokens = normalize_text(reference).split()
    prediction_tokens = normalize_text(prediction).split()
    if not reference_tokens and not prediction_tokens:
        return 1.0
    if not reference_tokens or not prediction_tokens:
        return 0.0
    overlap = sum((Counter(reference_tokens) & Counter(prediction_tokens)).values())
    precision = overlap / len(prediction_tokens)
    recall = overlap / len(reference_tokens)
    return _safe_div(2 * precision * recall, precision + recall)


def _labels(item: dict[str, Any]) -> dict[str, Any]:
    return item["message_judgment"]["labels"]


def _fact_set(facts: list[str]) -> set[str]:
    return {normalized for fact in facts if (normalized := normalize_text(fact))}


def _proxy_hallucination(labels: dict[str, Any], prediction: dict[str, Any]) -> bool:
    predicted = _fact_set(prediction.get("critical_facts_pred", []))
    gold = _fact_set(labels.get("critical_facts_gt", []))
    return bool(predicted - gold)


def _message_metric_eligible(item: dict[str, Any]) -> bool:
    labels = _labels(item)
    if not labels.get("popup_present_gt"):
        return False
    if labels.get("message_text_observability") != "complete":
        return False
    record_kind = item.get("identity", {}).get("record_kind")
    if record_kind in {"synthetic_schema_fixture", "annotation_pilot_candidate"}:
        return True
    return (
        item.get("message_judgment", {})
        .get("eligibility", {})
        .get("eligible_for_v1_message_metric")
        is True
    )


def _has_complete_adjudication(
    items: list[dict[str, Any]],
    predictions_by_id: dict[str, dict[str, Any]],
    annotations: dict[tuple[str, str], dict[str, Any]],
) -> bool:
    required: list[tuple[str, str]] = []
    for item in items:
        item_id = item["identity"]["item_id"]
        prediction = predictions_by_id[item_id]
        if (
            _labels(item)["popup_present_gt"]
            and _message_metric_eligible(item)
            and prediction["status"] == "judged"
            and prediction["popup_present_pred"] is True
        ):
            required.append((item_id, prediction["method_id"]))
    return bool(required) and all(
        key in annotations
        and isinstance(annotations[key].get("message_semantically_correct"), bool)
        and isinstance(annotations[key].get("critical_hallucination"), bool)
        for key in required
    )


def evaluate_predictions(
    items: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    annotations: dict[tuple[str, str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evaluate one prediction per frozen item without inferring user experience."""
    if not items:
        raise ValueError("evaluation requires at least one item")
    predictions_by_id = {row["item_id"]: row for row in predictions}
    item_ids = [item["identity"]["item_id"] for item in items]
    if len(predictions_by_id) != len(predictions) or set(predictions_by_id) != set(item_ids):
        raise ValueError("predictions must contain exactly one row for every item")

    annotations = annotations or {}
    adjudicated = _has_complete_adjudication(items, predictions_by_id, annotations)
    mode = "adjudicated" if adjudicated else "normalized_exact_proxy"

    tp = tn = fp = fn = abstain_count = 0
    predicted_negative_on_positive = negative_abstain_count = 0
    exact_sum = normalized_sum = token_f1_sum = 0.0
    popup_positive_complete_count = 0
    excluded_partial = excluded_not_observable = excluded_other_observability = 0
    critical_recall_sum = 0.0
    critical_recall_denominator = 0
    hallucination_count = hallucination_denominator = 0
    visual_called_items = visual_call_count = 0
    vpma_values: dict[str, bool | None] = {}

    for item in items:
        item_id = item["identity"]["item_id"]
        labels = _labels(item)
        prediction = predictions_by_id[item_id]
        status = prediction["status"]
        gt_present = labels["popup_present_gt"]
        pred_present = prediction.get("popup_present_pred")

        calls = int(prediction.get("visual_call_count", 0))
        visual_call_count += calls
        visual_called_items += int(bool(prediction.get("visual_called", calls > 0)))

        if status == "abstain" or pred_present is None:
            abstain_count += 1
            if gt_present:
                fn += 1
            else:
                negative_abstain_count += 1
        elif gt_present and pred_present:
            tp += 1
        elif gt_present and not pred_present:
            fn += 1
            predicted_negative_on_positive += 1
        elif not gt_present and pred_present:
            fp += 1
        else:
            tn += 1

        message_metric_eligible = _message_metric_eligible(item)
        if gt_present and message_metric_eligible:
            popup_positive_complete_count += 1
            predicted_message = (
                prediction.get("message_text_pred")
                if status == "judged" and pred_present is True
                else None
            )
            gold_message = labels.get("message_text_gt")
            exact_sum += float(predicted_message is not None and predicted_message == gold_message)
            normalized_sum += float(
                predicted_message is not None
                and normalize_text(predicted_message) == normalize_text(gold_message)
            )
            token_f1_sum += token_f1(gold_message, predicted_message)

            gold_facts = _fact_set(labels.get("critical_facts_gt", []))
            if gold_facts:
                predicted_facts = _fact_set(prediction.get("critical_facts_pred", []))
                critical_recall_sum += len(gold_facts & predicted_facts) / len(gold_facts)
                critical_recall_denominator += 1
        elif gt_present:
            observability = labels.get("message_text_observability")
            excluded_partial += int(observability == "partial")
            excluded_not_observable += int(observability == "not_observable")
            excluded_other_observability += int(
                observability not in {"partial", "not_observable"}
            )

        semantic_correct = False
        hallucinated = False
        if (
            status == "judged"
            and gt_present
            and pred_present is True
            and message_metric_eligible
        ):
            key = (item_id, prediction["method_id"])
            if adjudicated:
                semantic_correct = annotations[key]["message_semantically_correct"]
                hallucinated = annotations[key]["critical_hallucination"]
            else:
                semantic_correct = normalize_text(prediction.get("message_text_pred")) == normalize_text(
                    labels.get("message_text_gt")
                )
                hallucinated = _proxy_hallucination(labels, prediction)
            hallucination_denominator += 1
            hallucination_count += int(hallucinated)

        if status == "abstain" or pred_present is None:
            vpma_values[item_id] = None
        elif not gt_present:
            vpma_values[item_id] = pred_present is False
        elif not message_metric_eligible:
            vpma_values[item_id] = None
        else:
            vpma_values[item_id] = pred_present is True and semantic_correct and not hallucinated

    judged_count = len(items) - abstain_count
    presence_precision = _safe_div(tp, tp + fp)
    presence_recall = _safe_div(tp, tp + fn)
    presence_f1 = _safe_div(2 * presence_precision * presence_recall, presence_precision + presence_recall)
    negative_precision = _safe_div(tn, tn + predicted_negative_on_positive)
    negative_recall = _safe_div(tn, tn + fp + negative_abstain_count)
    negative_f1 = _safe_div(2 * negative_precision * negative_recall, negative_precision + negative_recall)
    vpma_covered = [value for value in vpma_values.values() if value is not None]
    vpma_successes = sum(value is True for value in vpma_covered)

    return {
        "metric_contract_version": "popup-message-v1.1",
        "n_items": len(items),
        "n_judged": judged_count,
        "coverage": judged_count / len(items),
        "presence": {
            "tp": tp,
            "tn": tn,
            "fp": fp,
            "fn": fn,
            "abstain": abstain_count,
            "precision": presence_precision,
            "recall": presence_recall,
            "f1": presence_f1,
            "accuracy_with_abstain_as_incorrect": (tp + tn) / len(items),
            "negative_class_precision": negative_precision,
            "negative_class_recall": negative_recall,
            "negative_class_f1": negative_f1,
            "macro_f1_with_abstain_as_miss": (presence_f1 + negative_f1) / 2,
        },
        "message": {
            "denominator_popup_positive": popup_positive_complete_count,
            "denominator_popup_positive_complete": popup_positive_complete_count,
            "excluded_partial": excluded_partial,
            "excluded_not_observable": excluded_not_observable,
            "excluded_other_observability_or_ineligible": excluded_other_observability,
            "exact_match": _safe_div(exact_sum, popup_positive_complete_count),
            "normalized_exact_match": _safe_div(normalized_sum, popup_positive_complete_count),
            "token_f1": _safe_div(token_f1_sum, popup_positive_complete_count),
        },
        "critical_information_recall": {
            "mean": _safe_div(critical_recall_sum, critical_recall_denominator),
            "denominator": critical_recall_denominator,
        },
        "critical_hallucination": {
            "count": hallucination_count,
            "denominator": hallucination_denominator,
            "rate": _safe_div(hallucination_count, hallucination_denominator),
            "mode": "adjudicated" if adjudicated else "critical_fact_set_proxy",
        },
        "visual_called_items": visual_called_items,
        "visual_call_count": visual_call_count,
        "visual_call_rate": visual_called_items / len(items),
        "vpma": {
            "mode": mode,
            "item_values": vpma_values,
            "success_count": vpma_successes,
            "covered_denominator": len(vpma_covered),
            "null_abstention_count": abstain_count,
            "null_message_unobservable_count": sum(
                _labels(item)["popup_present_gt"]
                and _labels(item).get("message_text_observability")
                == "not_observable"
                and predictions_by_id[item["identity"]["item_id"]]["status"] != "abstain"
                for item in items
            ),
            "null_message_partial_count": sum(
                _labels(item)["popup_present_gt"]
                and _labels(item).get("message_text_observability") == "partial"
                and predictions_by_id[item["identity"]["item_id"]]["status"] != "abstain"
                for item in items
            ),
            "rate_on_covered": _safe_div(vpma_successes, len(vpma_covered)),
            "overall_success_rate": vpma_successes / len(items),
        },
    }
