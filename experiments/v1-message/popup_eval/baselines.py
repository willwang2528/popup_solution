"""Deterministic, action-free baselines and perception routers."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
from typing import Any, Iterable

from .metrics import normalize_text


STRUCTURED_CHANNELS = {
    "accessibility",
    "uiautomator",
    "ui_automator",
    "xcui",
    "xctest",
    "dom",
    "protocol",
    "structured",
}
MESSAGE_GAPS = {
    "missing",
    "merged",
    "ambiguous",
    "contradictory",
    "stale",
    "owner_mismatch",
    "visual_only_text",
    "non_actionable",
    "unknown",
}


def _item_id(item: dict[str, Any]) -> str:
    return item["identity"]["item_id"]


def _join_id(item: dict[str, Any]) -> str:
    return item["identity"].get("pilot_item_id") or item.get("pilot_item_id") or _item_id(item)


def _prediction(
    item: dict[str, Any],
    method_id: str,
    *,
    status: str,
    popup_present: bool | None,
    message: str | None,
    facts: list[str] | None = None,
    confidence: float | None = None,
    visual_called: bool = False,
    route_reason: str,
) -> dict[str, Any]:
    observation_id = None
    if item.get("observations"):
        observation_id = item["observations"][0].get("observation_id")
    return {
        "item_id": _item_id(item),
        "method_id": method_id,
        "status": status,
        "popup_present_pred": popup_present,
        "message_text_pred": message,
        "critical_facts_pred": list(facts or []),
        "confidence": confidence,
        "visual_called": visual_called,
        "visual_call_count": 1 if visual_called else 0,
        "route_reason": route_reason,
        "source_observation_id": observation_id,
    }


class MajorityNoInputBaseline:
    """Fit-split prior that never reads evaluation-item observations."""

    method_id = "majority-no-input"

    def __init__(self, popup_present: bool, message: str | None, facts: list[str]):
        self.popup_present = popup_present
        self.message = message
        self.facts = facts

    @classmethod
    def fit(cls, items: list[dict[str, Any]]) -> "MajorityNoInputBaseline":
        if not items:
            raise ValueError("majority baseline requires a non-empty fit split")
        labels = [item["message_judgment"]["labels"] for item in items]
        positives = sum(bool(row["popup_present_gt"]) for row in labels)
        popup_present = positives > len(labels) / 2
        if not popup_present:
            return cls(False, None, [])

        positive_rows = [row for row in labels if row["popup_present_gt"]]
        message_counts = Counter(
            row["message_text_gt"] for row in positive_rows if row.get("message_text_gt")
        )
        message = sorted(message_counts, key=lambda value: (-message_counts[value], normalize_text(value)))[0] if message_counts else None
        facts_counts = Counter(tuple(row.get("critical_facts_gt", [])) for row in positive_rows)
        facts = list(sorted(facts_counts, key=lambda value: (-facts_counts[value], value))[0]) if facts_counts else []
        return cls(True, message, facts)

    def predict(self, item: dict[str, Any]) -> dict[str, Any]:
        return _prediction(
            item,
            self.method_id,
            status="judged",
            popup_present=self.popup_present,
            message=self.message,
            facts=self.facts,
            confidence=None,
            route_reason="fit_split_majority_prior_no_item_input",
        )


def _structured_candidates(
    item: dict[str, Any], *, popup_scoped: bool = False
) -> Iterable[dict[str, Any]]:
    for candidate in item.get("candidates", []):
        if candidate.get("source_channel") not in STRUCTURED_CHANNELS:
            continue
        normalized = candidate.get("normalized", {})
        features = candidate.get("features", {})
        if normalized.get("visible") is False:
            continue
        if popup_scoped:
            if features.get("belongs_to_host_page") is True:
                continue
            if features.get("inside_popup_roi") is False:
                continue
        yield candidate


class StructuredTextRuleBaseline:
    """Full-tree structure-only concatenation; never reads labels or pixels."""

    method_id = "structured-text-rule"

    def predict(self, item: dict[str, Any]) -> dict[str, Any]:
        fragments: list[str] = []
        seen: set[str] = set()
        for candidate in _structured_candidates(item):
            normalized = candidate.get("normalized", {})
            for field in ("name_or_text", "value_or_hint"):
                value = normalized.get(field)
                key = normalize_text(value)
                if key and key not in seen:
                    seen.add(key)
                    fragments.append(value.strip())
        message = " ".join(fragments) or None
        if message is None:
            return _prediction(
                item,
                self.method_id,
                status="abstain",
                popup_present=None,
                message=None,
                confidence=None,
                route_reason="structured_full_tree_missing",
            )
        return _prediction(
            item,
            self.method_id,
            status="judged",
            popup_present=True,
            message=message,
            confidence=0.65,
            route_reason="structured_full_tree_text",
        )


class PopupScopedStructuredTextBaseline(StructuredTextRuleBaseline):
    """Popup-scoped structure component used only inside the proposed router."""

    method_id = "popup-scoped-structured-text-rule"

    def predict(self, item: dict[str, Any]) -> dict[str, Any]:
        scoped = deepcopy(item)
        scoped["candidates"] = list(_structured_candidates(item, popup_scoped=True))
        result = super().predict(scoped)
        result["method_id"] = self.method_id
        result["route_reason"] = (
            "structured_popup_scope_text"
            if result["status"] == "judged"
            else "structured_popup_scope_missing"
        )
        return result


class PredictionAdapter:
    """Adapter for frozen OCR/VLM predictions; it never invokes an external model."""

    method_id = "ocr-vlm-adapter"

    def __init__(self, rows_by_id: dict[str, dict[str, Any]]):
        self.rows_by_id = rows_by_id

    @classmethod
    def from_rows(cls, rows: list[dict[str, Any]]) -> "PredictionAdapter":
        rows_by_id: dict[str, dict[str, Any]] = {}
        for row in rows:
            if "identity" in row and "message_judgment" in row:
                item_id = _join_id(row)
                source = row["message_judgment"].get("prediction", {})
            else:
                item_id = row.get("pilot_item_id") or row.get("item_id")
                if item_id is None:
                    raise ValueError("prediction row requires pilot_item_id or item_id")
                source = row
            if item_id in rows_by_id:
                raise ValueError(f"duplicate prediction adapter item_id: {item_id}")
            rows_by_id[item_id] = deepcopy(source)
        return cls(rows_by_id)

    def predict(self, item: dict[str, Any]) -> dict[str, Any]:
        source = self.rows_by_id.get(_join_id(item))
        if source is None:
            return _prediction(
                item,
                self.method_id,
                status="abstain",
                popup_present=None,
                message=None,
                confidence=None,
                visual_called=True,
                route_reason="missing_frozen_visual_prediction",
            )
        status = source.get("status", "judged")
        popup_present = source.get("popup_present_pred") if status == "judged" else None
        message = source.get("message_text_pred") if status == "judged" else None
        facts = source.get("critical_facts_pred", []) if status == "judged" else []
        confidence = source.get("confidence") if status == "judged" else None
        result = _prediction(
            item,
            self.method_id,
            status=status,
            popup_present=popup_present,
            message=message,
            facts=facts,
            confidence=confidence,
            visual_called=True,
            route_reason="frozen_ocr_vlm_prediction",
        )
        if source.get("source_observation_id") is not None:
            result["source_observation_id"] = source["source_observation_id"]
        return result


def message_gap_reasons(item: dict[str, Any], structured_prediction: dict[str, Any]) -> list[str]:
    reasons: set[str] = set()
    if not structured_prediction.get("message_text_pred"):
        reasons.add("missing")
    for candidate in _structured_candidates(item, popup_scoped=True):
        for reason in candidate.get("features", {}).get("gap_reasons", []):
            if reason in MESSAGE_GAPS:
                reasons.add(reason)
        if candidate.get("features", {}).get("owner_consistent") is False:
            reasons.add("owner_mismatch")
    for observation in item.get("observations", []):
        sync = observation.get("synchronization", {}).get("tree_screenshot_sync_status")
        if sync not in {None, "synchronized"}:
            reasons.add("stale")
    return sorted(reasons)


def build_shuffled_gap_permutation(
    items: list[dict[str, Any]],
    structured: PopupScopedStructuredTextBaseline,
    seed: int,
) -> dict[str, dict[str, Any]]:
    """Permute pre-gold gap vectors one-to-one with a stable seeded rotation."""
    items_by_id: dict[str, dict[str, Any]] = {}
    gaps_by_id: dict[str, list[str]] = {}
    for item in items:
        item_id = _item_id(item)
        if item_id in items_by_id:
            raise ValueError("item ids must be unique")
        items_by_id[item_id] = item
        structured_prediction = structured.predict(item)
        gaps_by_id[item_id] = message_gap_reasons(item, structured_prediction)

    ranked_ids = sorted(
        items_by_id,
        key=lambda item_id: hashlib.sha256(
            f"shuffled-gap-v1:{seed}:{item_id}".encode("utf-8")
        ).hexdigest(),
    )
    source_ids = ranked_ids[1:] + ranked_ids[:1] if ranked_ids else []
    return {
        target_id: {
            "source_item_id": source_id,
            "gap_reasons": list(gaps_by_id[source_id]),
        }
        for target_id, source_id in zip(ranked_ids, source_ids)
    }


class MessageGapRouter:
    """Select between structure and a frozen visual prediction without actions."""

    VALID_MODES = {
        "mg-pu",
        "always-visual",
        "empty-tree",
        "random-matched",
        "shuffled-gap",
    }

    def __init__(
        self,
        structured: StructuredTextRuleBaseline,
        visual: PredictionAdapter,
        mode: str,
        random_call_ids: set[str] | None = None,
        shuffled_gap_assignments: dict[str, dict[str, Any]] | None = None,
    ):
        if mode not in self.VALID_MODES:
            raise ValueError(f"unknown router mode: {mode}")
        self.structured = structured
        self.visual = visual
        self.mode = mode
        self.random_call_ids = random_call_ids or set()
        self.shuffled_gap_assignments = shuffled_gap_assignments or {}

    def _should_call_visual(
        self,
        item: dict[str, Any],
        structured_prediction: dict[str, Any],
        reasons: list[str],
    ) -> bool:
        if self.mode == "always-visual":
            return True
        if self.mode == "mg-pu":
            return bool(reasons)
        if self.mode == "shuffled-gap":
            return bool(reasons)
        if self.mode == "random-matched":
            return _item_id(item) in self.random_call_ids
        observations = item.get("observations", [])
        node_count = sum(
            int(observation.get("structured_representation", {}).get("node_count") or 0)
            for observation in observations
        )
        return node_count == 0 or not structured_prediction.get("message_text_pred")

    def predict(self, item: dict[str, Any]) -> dict[str, Any]:
        structured_prediction = self.structured.predict(item)
        reasons = message_gap_reasons(item, structured_prediction)
        if self.mode == "shuffled-gap":
            assignment = self.shuffled_gap_assignments.get(_item_id(item))
            if assignment is None:
                raise ValueError("shuffled-gap assignment is missing for item")
            reasons = list(assignment["gap_reasons"])
        call_visual = self._should_call_visual(item, structured_prediction, reasons)
        method_id = (
            "shuffled-gap-reasons-v1" if self.mode == "shuffled-gap" else self.mode
        )
        reason_prefix = "shuffled-gap:" if self.mode == "shuffled-gap" else ""
        if call_visual:
            result = self.visual.predict(item)
            result["method_id"] = method_id
            result["route_reason"] = (
                f"visual:{reason_prefix}{','.join(reasons) or self.mode}"
            )
            return result
        result = deepcopy(structured_prediction)
        result["method_id"] = method_id
        result["route_reason"] = (
            f"structured:{reason_prefix}{','.join(reasons) or 'sufficient'}"
        )
        return result


def select_random_matched_ids(
    items: list[dict[str, Any]], call_count: int, seed: int
) -> set[str]:
    """Pick exactly K IDs by stable SHA-256 rank, independent of input order."""
    if call_count < 0 or call_count > len(items):
        raise ValueError("matched call_count must be within the dataset size")
    item_ids = [_item_id(item) for item in items]
    if len(item_ids) != len(set(item_ids)):
        raise ValueError("item ids must be unique")
    ranked = sorted(
        item_ids,
        key=lambda item_id: hashlib.sha256(f"{seed}:{item_id}".encode("utf-8")).hexdigest(),
    )
    return set(ranked[:call_count])
