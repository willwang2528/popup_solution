import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from popup_eval.metrics import evaluate_predictions, normalize_text, token_f1


def gold_item(item_id, popup_present, message=None, facts=None):
    return {
        "identity": {"item_id": item_id, "record_kind": "synthetic_schema_fixture"},
        "message_judgment": {
            "labels": {
                "popup_present_gt": popup_present,
                "message_text_gt": message,
                "critical_facts_gt": facts or [],
            }
        },
    }


def prediction(
    item_id,
    status,
    popup_present=None,
    message=None,
    facts=None,
    visual_called=False,
):
    return {
        "item_id": item_id,
        "method_id": "test-method",
        "status": status,
        "popup_present_pred": popup_present,
        "message_text_pred": message,
        "critical_facts_pred": facts or [],
        "confidence": 1.0 if status == "judged" else None,
        "visual_called": visual_called,
        "visual_call_count": 1 if visual_called else 0,
        "route_reason": "fixture",
        "source_observation_id": "obs.before",
    }


class TextMetricTests(unittest.TestCase):
    def test_normalize_text_preserves_punctuation_and_collapses_case_whitespace(self):
        # Break caught: punctuation is silently erased despite the frozen annotation protocol.
        self.assertEqual(normalize_text("  PAY—Now!\n"), "pay—now!")

    def test_token_f1_uses_token_overlap(self):
        # Break caught: token F1 accidentally behaves like exact match.
        self.assertTrue(math.isclose(token_f1("Pay now", "Pay later"), 0.5))


class AggregateMetricTests(unittest.TestCase):
    def test_metrics_count_positive_abstention_as_uncovered_not_correct(self):
        # Break caught: selective abstention inflates presence recall or overall VPMA.
        items = [
            gold_item("p1", True, "Offer ends today", ["offer"]),
            gold_item("n1", False),
            gold_item("p2", True, "Update required", ["update required"]),
        ]
        predictions = [
            prediction("p1", "judged", True, "Offer ends today", ["offer", "invented"], True),
            prediction("n1", "judged", False),
            prediction("p2", "abstain"),
        ]

        metrics = evaluate_predictions(items, predictions)

        self.assertEqual(metrics["n_items"], 3)
        self.assertTrue(math.isclose(metrics["coverage"], 2 / 3))
        self.assertEqual(metrics["presence"]["tp"], 1)
        self.assertEqual(metrics["presence"]["tn"], 1)
        self.assertEqual(metrics["presence"]["fn"], 1)
        self.assertEqual(metrics["presence"]["abstain"], 1)
        self.assertTrue(math.isclose(metrics["presence"]["recall"], 0.5))
        self.assertTrue(math.isclose(metrics["message"]["exact_match"], 0.5))
        self.assertTrue(math.isclose(metrics["message"]["normalized_exact_match"], 0.5))
        self.assertTrue(math.isclose(metrics["message"]["token_f1"], 0.5))
        self.assertTrue(math.isclose(metrics["visual_call_rate"], 1 / 3))
        self.assertEqual(metrics["critical_hallucination"]["count"], 1)
        self.assertEqual(metrics["critical_hallucination"]["denominator"], 1)
        self.assertEqual(metrics["vpma"]["mode"], "normalized_exact_proxy")
        self.assertTrue(math.isclose(metrics["vpma"]["rate_on_covered"], 0.5))
        self.assertTrue(math.isclose(metrics["vpma"]["overall_success_rate"], 1 / 3))

    def test_complete_human_annotations_switch_vpma_to_adjudicated_mode(self):
        # Break caught: semantic adjudication is ignored in favor of string equality.
        items = [gold_item("p1", True, "Do not continue", ["do not continue"])]
        predictions = [prediction("p1", "judged", True, "Stop here", ["do not continue"])]
        annotations = {
            ("p1", "test-method"): {
                "message_semantically_correct": True,
                "critical_hallucination": False,
            }
        }

        metrics = evaluate_predictions(items, predictions, annotations)

        self.assertEqual(metrics["vpma"]["mode"], "adjudicated")
        self.assertEqual(metrics["vpma"]["rate_on_covered"], 1.0)
        self.assertEqual(metrics["message"]["normalized_exact_match"], 0.0)

    def test_positive_abstention_is_not_a_predicted_negative_for_macro_f1(self):
        # Break caught: positive abstain incorrectly lowers negative-class precision.
        items = [gold_item("n1", False), gold_item("p1", True, "Popup")]
        predictions = [
            prediction("n1", "judged", False),
            prediction("p1", "abstain"),
        ]

        metrics = evaluate_predictions(items, predictions)

        self.assertEqual(metrics["presence"]["negative_class_precision"], 1.0)
        self.assertEqual(metrics["presence"]["negative_class_recall"], 1.0)
        self.assertEqual(metrics["presence"]["macro_f1_with_abstain_as_miss"], 0.5)


if __name__ == "__main__":
    unittest.main()
