from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from popup_eval.the_ok_baseline import TheOkTextBaseline


def candidate(node_index, text=None, *, normalized_fallback=None, source_channel="structured"):
    return {
        "source_channel": source_channel,
        "normalized": {
            "name_or_text": normalized_fallback,
            "value_or_hint": None,
            "visible": True,
        },
        "features": {"node_index": node_index, "text": text},
    }


def item(candidates):
    return {
        "identity": {"item_id": "e1", "record_kind": "synthetic_schema_fixture"},
        "message_judgment": {
            "labels": {
                "popup_present_gt": True,
                "message_text_gt": "gold must stay hidden",
                "critical_facts_gt": [],
                "message_text_observability": "complete",
            }
        },
        "observations": [{"observation_id": "obs.before", "phase": "pre_action"}],
        "candidates": candidates,
        "action_attempts": [],
        "decision": {"policy": {"decision": "no_action"}},
    }


class TheOkTextBaselineTests(unittest.TestCase):
    def setUp(self):
        self.baseline = TheOkTextBaseline()

    def test_official_dialog_rule_detects_and_returns_only_contributing_elements(self):
        # Break caught: the baseline drops the official rules or leaks unrelated host text.
        example = item(
            [
                candidate(3, "Home account balance"),
                candidate(2, "We use cookies for analytics"),
            ]
        )

        result = self.baseline.predict(example)

        self.assertEqual(result["status"], "judged")
        self.assertIs(result["popup_present_pred"], True)
        self.assertEqual(result["message_text_pred"], "We use cookies for analytics")
        self.assertEqual(result["route_reason"], "the_ok_consent_rule_match")
        self.assertFalse(result["visual_called"])

    def test_no_rule_match_is_a_judged_negative_when_raw_text_exists(self):
        # Break caught: a runnable paper detector is converted into an unscorable interface.
        result = self.baseline.predict(item([candidate(1, "Weather tomorrow")]))

        self.assertEqual(result["status"], "judged")
        self.assertIs(result["popup_present_pred"], False)
        self.assertIsNone(result["message_text_pred"])

    def test_missing_raw_appium_text_abstains_and_ignores_normalized_semantic_fallback(self):
        # Break caught: icon/class fallbacks are presented as Appium element text.
        result = self.baseline.predict(
            item([candidate(1, text=None, normalized_fallback="Privacy policy")])
        )

        self.assertEqual(result["status"], "abstain")
        self.assertIsNone(result["popup_present_pred"])
        self.assertEqual(result["route_reason"], "the_ok_raw_element_text_missing")

    def test_non_appium_dom_or_protocol_text_is_not_consumed(self):
        # Break caught: a cross-platform Appium baseline silently expands to DOM/protocol.
        result = self.baseline.predict(
            item([candidate(1, "We use cookies", source_channel="dom")])
        )

        self.assertEqual(result["status"], "abstain")
        self.assertIsNone(result["popup_present_pred"])

    def test_official_regular_and_half_keyword_threshold_is_preserved(self):
        # The upstream fixed configuration uses threshold=1: one regular keyword or
        # two half-keyword matches are sufficient.
        regular = self.baseline.predict(item([candidate(1, "Analytics")]))
        two_halves = self.baseline.predict(
            item([candidate(1, "Consent"), candidate(2, "IP address")])
        )

        self.assertIs(regular["popup_present_pred"], True)
        self.assertIs(two_halves["popup_present_pred"], True)

    def test_output_is_invariant_to_gold_and_candidate_input_order(self):
        # Break caught: source labels or input traversal order influence a frozen baseline.
        first = item(
            [candidate(9, "Analytics"), candidate(2, "We use cookies for analytics")]
        )
        second = deepcopy(first)
        second["candidates"].reverse()
        second["message_judgment"]["labels"] = {
            "popup_present_gt": False,
            "message_text_gt": None,
            "critical_facts_gt": ["injected"],
            "message_text_observability": "not_applicable",
        }

        result_a = self.baseline.predict(first)
        result_b = self.baseline.predict(second)

        self.assertEqual(result_a, result_b)


if __name__ == "__main__":
    unittest.main()
