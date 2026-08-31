"""Action-free text baseline derived from The OK Is Not Enough artifact.

This preserves the upstream consent-dialog decision rules and fixed example
configuration.  Projecting matched Appium element text into a v1 message is a
clearly named benchmark adaptation; it is not a reproduction of the original
interaction or privacy-compliance study.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

from .baselines import _prediction


UPSTREAM_REVISION = "b618948c0d24b917b3a46a88f5c1cf6ff84571cd"
INDICATORS_SHA256 = "8b376a5391e76abef6b73b2889129ed36c64b4fd096fa4e1c51d781493bf34c9"
KEYWORD_THRESHOLD = 1
APPIUM_LIKE_CHANNELS = {
    "accessibility",
    "structured",
    "uiautomator",
    "ui_automator",
    "xcui",
    "xctest",
}


def _default_indicators_path() -> Path:
    return Path(__file__).resolve().parents[1] / "resources" / "the-ok" / "indicators.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _compile(expressions: Iterable[str], *, boundaries: bool) -> list[re.Pattern[str]]:
    compiled: list[re.Pattern[str]] = []
    for expression in expressions:
        lowered = expression.lower()
        if boundaries:
            lowered = rf"\b{lowered}\b"
        variants = [lowered, lowered.replace("_", "")] if "_" in lowered else [lowered]
        compiled.extend(re.compile(variant) for variant in variants)
    return compiled


class TheOkTextBaseline:
    """Consent-dialog text detector plus a deterministic matched-text projection."""

    method_id = "the-ok-text-rule"

    def __init__(self, indicators_path: Path | None = None):
        path = indicators_path or _default_indicators_path()
        if _sha256(path) != INDICATORS_SHA256:
            raise ValueError("The OK indicators snapshot hash mismatch")
        indicators = json.loads(path.read_text(encoding="utf-8"))
        self.dialog = _compile(indicators["dialog"], boundaries=False)
        self.link = _compile(indicators["link"], boundaries=True)
        self.regular = _compile(indicators["regularKeywords"], boundaries=False)
        self.half = _compile(indicators["halfKeywords"], boundaries=False)

    @staticmethod
    def _raw_elements(item: dict[str, Any]) -> list[tuple[int, int, str, str]]:
        elements: list[tuple[int, int, str, str]] = []
        for input_index, candidate in enumerate(item.get("candidates", [])):
            if candidate.get("source_channel") not in APPIUM_LIKE_CHANNELS:
                continue
            text = candidate.get("features", {}).get("text")
            if not isinstance(text, str) or not text.strip():
                continue
            stripped = text.strip()
            node_index = candidate.get("features", {}).get("node_index")
            stable_index = node_index if isinstance(node_index, int) else 2**31 - 1
            elements.append((stable_index, input_index, stripped, stripped.lower()))
        return elements

    @staticmethod
    def _matches(
        elements: list[tuple[int, int, str, str]],
        patterns: list[re.Pattern[str]],
    ) -> list[tuple[int, int, str, str]]:
        # The upstream Scala implementation counts every regex-element match.
        return [element for element in elements for pattern in patterns if pattern.search(element[3])]

    @staticmethod
    def _message(matches: list[tuple[int, int, str, str]]) -> str:
        seen: set[str] = set()
        fragments: list[str] = []
        for _, _, original, lowered in sorted(matches, key=lambda row: (row[0], row[2], row[1])):
            key = " ".join(lowered.split())
            if key not in seen:
                seen.add(key)
                fragments.append(original)
        return " ".join(fragments)

    def predict(self, item: dict[str, Any]) -> dict[str, Any]:
        elements = self._raw_elements(item)
        if not elements:
            return _prediction(
                item,
                self.method_id,
                status="abstain",
                popup_present=None,
                message=None,
                confidence=None,
                route_reason="the_ok_raw_element_text_missing",
            )

        clear_matches = self._matches(elements, self.dialog + self.link)
        regular_matches = self._matches(elements, self.regular)
        half_matches = self._matches(elements, self.half)
        detected = bool(clear_matches) or (
            len(regular_matches) + 0.5 * len(half_matches) >= KEYWORD_THRESHOLD
        )
        if not detected:
            return _prediction(
                item,
                self.method_id,
                status="judged",
                popup_present=False,
                message=None,
                confidence=None,
                route_reason="the_ok_consent_rule_no_match",
            )

        contributors = clear_matches or (regular_matches + half_matches)
        return _prediction(
            item,
            self.method_id,
            status="judged",
            popup_present=True,
            message=self._message(contributors),
            confidence=None,
            route_reason="the_ok_consent_rule_match",
        )
