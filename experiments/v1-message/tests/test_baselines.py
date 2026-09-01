from pathlib import Path
from collections import Counter
from copy import deepcopy
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from popup_eval.baselines import (
    MajorityNoInputBaseline,
    MessageGapRouter,
    PopupScopedStructuredTextBaseline,
    PredictionAdapter,
    StructuredTextRuleBaseline,
    select_random_matched_ids,
)
import popup_eval.baselines as popup_baselines
from popup_eval.the_ok_baseline import TheOkTextBaseline
from pregold.freeze_predictions import _structured_prediction as pregold_structured_prediction


def item(item_id, popup_gt, message_gt=None, candidates=None, node_count=1, sync="synchronized"):
    return {
        "identity": {"item_id": item_id, "record_kind": "synthetic_schema_fixture"},
        "message_judgment": {
            "labels": {
                "popup_present_gt": popup_gt,
                "message_text_gt": message_gt,
                "critical_facts_gt": [],
            }
        },
        "action_attempts": [],
        "observations": [
            {
                "observation_id": "obs.before",
                "phase": "pre_action",
                "synchronization": {"tree_screenshot_sync_status": sync},
                "structured_representation": {"available": True, "node_count": node_count},
            }
        ],
        "candidates": candidates or [],
    }


def candidate(source, text, value=None, gaps=None, host=False, inside=True, visible=True):
    return {
        "source_channel": source,
        "normalized": {
            "role_or_class": "group",
            "name_or_text": text,
            "value_or_hint": value,
            "visible": visible,
        },
        "features": {
            "inside_popup_roi": inside,
            "belongs_to_host_page": host,
            "owner_consistent": True,
            "gap_reasons": gaps or [],
        },
    }


def visual_row(item_id, present=True, message="Full visual message"):
    return {
        "item_id": item_id,
        "status": "judged",
        "popup_present_pred": present,
        "message_text_pred": message if present else None,
        "critical_facts_pred": [],
        "confidence": 0.9,
        "source_observation_id": "obs.before",
    }


class MajorityBaselineTests(unittest.TestCase):
    def test_majority_baseline_uses_only_fit_labels(self):
        # Break caught: no-input baseline leaks evaluation observations or gold.
        fit_items = [
            item("t1", True, "Maintenance notice"),
            item("t2", True, "Maintenance notice"),
            item("t3", False),
        ]
        evaluation_item = item(
            "e1",
            False,
            candidates=[candidate("accessibility", "Evaluation-only secret")],
        )

        result = MajorityNoInputBaseline.fit(fit_items).predict(evaluation_item)

        self.assertEqual(result["popup_present_pred"], True)
        self.assertEqual(result["message_text_pred"], "Maintenance notice")
        self.assertEqual(result["visual_call_count"], 0)


class StructuredBaselineTests(unittest.TestCase):
    def test_structured_rule_reads_accessibility_text_and_excludes_visual_candidate(self):
        # Break caught: structure-only baseline accidentally consumes detector/VLM text.
        example = item(
            "e1",
            True,
            "unused gold",
            candidates=[
                candidate("accessibility", "Update available", "Security fixes"),
                candidate("detector", "Close", "x icon"),
            ],
        )

        result = StructuredTextRuleBaseline().predict(example)

        self.assertEqual(result["popup_present_pred"], True)
        self.assertEqual(result["message_text_pred"], "Update available Security fixes")
        self.assertEqual(result["visual_call_count"], 0)

    def test_structured_rule_does_not_read_gold_when_structure_is_empty(self):
        # Break caught: rule baseline obtains a perfect message from annotation leakage.
        example = item("e1", True, "Gold must stay hidden", candidates=[], node_count=0)

        result = StructuredTextRuleBaseline().predict(example)

        self.assertEqual(result["status"], "abstain")
        self.assertIsNone(result["popup_present_pred"])
        self.assertIsNone(result["message_text_pred"])
        self.assertIsNone(result["confidence"])

    def test_structured_rule_is_full_tree_flatten_without_popup_scope_oracle(self):
        # Break caught: A1 uses gold-derived popup ROI/host ownership unavailable to the baseline.
        example = item(
            "e1",
            True,
            candidates=[
                candidate("accessibility", "Host heading", host=True, inside=False),
                candidate("accessibility", "Popup notice"),
            ],
        )

        result = StructuredTextRuleBaseline().predict(example)

        self.assertEqual(result["message_text_pred"], "Host heading Popup notice")
        self.assertEqual(result["route_reason"], "structured_full_tree_text")

    def test_formal_a1_matches_pregold_on_nonempty_and_empty_structure(self):
        # Break caught: the frozen pre-gold A1 and formal evaluator assign different statuses.
        for text in ("Network unavailable", None):
            with self.subTest(text=text):
                candidates = [] if text is None else [candidate("structured", text)]
                example = item("e1", True, candidates=candidates, node_count=len(candidates))
                formal = StructuredTextRuleBaseline().predict(example)
                feature = {
                    "candidates": candidates,
                    "observations": [
                        {
                            "structured_representation": {
                                "availability": "available" if candidates else "missing",
                                "node_count": len(candidates),
                            }
                        }
                    ],
                }
                pregold, _ = pregold_structured_prediction("e1", feature)

                self.assertEqual(formal["status"], pregold["status"])
                self.assertEqual(formal["popup_present_pred"], pregold["popup_present_pred"])
                self.assertEqual(formal["message_text_pred"], pregold["message_text_pred"])

    def test_formal_a1_matches_pregold_nfkc_deduplication(self):
        # Break caught: full-width and ASCII-equivalent fragments are deduplicated
        # differently before and after gold unlock.
        candidates = [
            candidate("structured", "Ａ"),
            candidate("structured", "A"),
        ]
        example = item("e1", True, candidates=candidates, node_count=2)
        feature = {
            "candidates": candidates,
            "observations": [
                {
                    "structured_representation": {
                        "availability": "available",
                        "node_count": 2,
                    }
                }
            ],
        }

        formal = StructuredTextRuleBaseline().predict(example)
        pregold, _ = pregold_structured_prediction("e1", feature)

        self.assertEqual(formal["message_text_pred"], "Ａ")
        self.assertEqual(formal["message_text_pred"], pregold["message_text_pred"])


class TheOkBaselineTests(unittest.TestCase):
    def test_the_ok_reads_raw_android_text_from_union_candidate(self):
        # Break caught: union conversion moves Appium-like raw text and A2 abstains on every item.
        example = item(
            "e1",
            True,
            candidates=[
                {
                    "source_channel": "uiautomator",
                    "normalized": {
                        "role_or_class": "android.widget.TextView",
                        "name_or_text": "We use cookies",
                        "value_or_hint": None,
                        "visible": True,
                    },
                    "features": {
                        "inside_popup_roi": None,
                        "belongs_to_host_page": None,
                        "owner_consistent": None,
                        "gap_reasons": [],
                    },
                    "android_raw": {"text": "We use cookies"},
                }
            ],
        )

        result = TheOkTextBaseline().predict(example)

        self.assertEqual(result["status"], "judged")
        self.assertTrue(result["popup_present_pred"])
        self.assertEqual(result["message_text_pred"], "We use cookies")


class AdapterTests(unittest.TestCase):
    def test_prediction_adapter_accepts_full_item_prediction_shape(self):
        # Break caught: adapter only accepts a private flat format, not frozen item JSONL.
        source = item("e1", True)
        source["message_judgment"]["prediction"] = visual_row("ignored", True, "OCR text")

        result = PredictionAdapter.from_rows([source]).predict(source)

        self.assertEqual(result["message_text_pred"], "OCR text")
        self.assertEqual(result["method_id"], "ocr-vlm-adapter")
        self.assertTrue(result["visual_called"])

    def test_prediction_adapter_abstains_when_item_is_missing(self):
        # Break caught: a missing external prediction silently becomes no-popup.
        result = PredictionAdapter.from_rows([]).predict(item("missing", False))

        self.assertEqual(result["status"], "abstain")
        self.assertIsNone(result["popup_present_pred"])
        self.assertTrue(result["visual_called"])

    def test_prediction_adapter_joins_flat_rows_by_pilot_item_id(self):
        # Break caught: pilot predictions cannot join the frozen annotation manifest.
        example = item("internal-e1", True)
        example["identity"]["pilot_item_id"] = "PMJ-PILOT-001"
        row = visual_row("unused", True, "Pilot OCR text")
        row.pop("item_id")
        row["pilot_item_id"] = "PMJ-PILOT-001"

        result = PredictionAdapter.from_rows([row]).predict(example)

        self.assertEqual(result["message_text_pred"], "Pilot OCR text")


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.example = item(
            "e1",
            True,
            "unused gold",
            candidates=[candidate("accessibility", "Title", gaps=["merged"])],
        )
        self.structured = PopupScopedStructuredTextBaseline()
        self.visual = PredictionAdapter.from_rows([visual_row("e1")])

    def test_mgpu_routes_nonempty_merged_structure_to_visual(self):
        # Break caught: MG-PU collapses to the empty-tree-only gate.
        result = MessageGapRouter(self.structured, self.visual, mode="mg-pu").predict(self.example)

        self.assertEqual(result["message_text_pred"], "Full visual message")
        self.assertTrue(result["visual_called"])
        self.assertIn("merged", result["route_reason"])

    def test_empty_tree_ablation_keeps_nonempty_merged_structure(self):
        # Break caught: empty-tree ablation accidentally uses the full MG-PU gate.
        result = MessageGapRouter(self.structured, self.visual, mode="empty-tree").predict(self.example)

        self.assertEqual(result["message_text_pred"], "Title")
        self.assertFalse(result["visual_called"])

    def test_mgpu_treats_non_actionable_exposure_as_perception_uplift_gap(self):
        # Break caught: actionability-gap perception uplift only fires on empty text.
        example = item(
            "e1",
            True,
            "unused gold",
            candidates=[candidate("accessibility", "Title", gaps=["non_actionable"])],
        )

        result = MessageGapRouter(self.structured, self.visual, mode="mg-pu").predict(example)

        self.assertTrue(result["visual_called"])
        self.assertIn("non_actionable", result["route_reason"])

    def test_always_visual_ablation_calls_adapter(self):
        # Break caught: always-visual silently inherits a selective gate.
        result = MessageGapRouter(self.structured, self.visual, mode="always-visual").predict(self.example)

        self.assertEqual(result["message_text_pred"], "Full visual message")
        self.assertTrue(result["visual_called"])

    def test_random_matched_call_selection_is_exact_and_seeded(self):
        # Break caught: random ablation changes the visual-call budget or is nondeterministic.
        items = [item(f"e{i}", False) for i in range(10)]

        first = select_random_matched_ids(items, call_count=4, seed=17)
        second = select_random_matched_ids(list(reversed(items)), call_count=4, seed=17)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 4)
        self.assertEqual(first, {"e3", "e4", "e6", "e7"})

    def test_shuffled_gap_permutation_is_seeded_order_independent_and_gold_blind(self):
        # Break caught: ABL-003 shuffles rows nondeterministically, reuses a source,
        # or lets annotation/action/Recovery fields influence the routing permutation.
        self.assertTrue(hasattr(popup_baselines, "build_shuffled_gap_permutation"))
        build = popup_baselines.build_shuffled_gap_permutation
        examples = [
            item("e0", True, "gold-0", candidates=[candidate("accessibility", "Complete")]),
            item(
                "e1",
                True,
                "gold-1",
                candidates=[candidate("accessibility", "Merged", gaps=["merged"])],
            ),
            item(
                "e2",
                False,
                candidates=[candidate("accessibility", "Owner mismatch")],
            ),
            item(
                "e3",
                True,
                "gold-3",
                candidates=[candidate("accessibility", "Stale")],
                sync="unsynchronized",
            ),
        ]
        examples[2]["candidates"][0]["features"]["owner_consistent"] = False
        mutated = deepcopy(examples)
        for example in mutated:
            example["message_judgment"]["labels"] = {
                "popup_present_gt": not example["message_judgment"]["labels"][
                    "popup_present_gt"
                ],
                "message_text_gt": "changed gold",
                "critical_facts_gt": ["changed gold fact"],
            }
            example["advanced"] = {
                "Recovery": {"action": "dismiss", "target": "forbidden"}
            }

        first = build(examples, self.structured, seed=17)
        reversed_order = build(list(reversed(examples)), self.structured, seed=17)
        changed_irrelevant_fields = build(mutated, self.structured, seed=17)

        expected = {
            "e0": {"source_item_id": "e2", "gap_reasons": ["owner_mismatch"]},
            "e1": {"source_item_id": "e3", "gap_reasons": ["stale"]},
            "e2": {"source_item_id": "e1", "gap_reasons": ["merged"]},
            "e3": {"source_item_id": "e0", "gap_reasons": []},
        }
        self.assertEqual(first, expected)
        self.assertEqual(reversed_order, expected)
        self.assertEqual(changed_irrelevant_fields, expected)
        self.assertEqual(
            len({assignment["source_item_id"] for assignment in first.values()}),
            len(examples),
        )
        self.assertTrue(
            all(item_id != assignment["source_item_id"] for item_id, assignment in first.items())
        )

    def test_shuffled_gap_router_preserves_gap_multiset_and_mgpu_visual_budget(self):
        # Break caught: the shuffle changes the number of non-empty gap vectors or
        # reports itself as MG-PU/random rather than an independent ablation.
        self.assertTrue(hasattr(popup_baselines, "build_shuffled_gap_permutation"))
        examples = [
            item("e0", True, candidates=[candidate("accessibility", "Complete")]),
            item(
                "e1",
                True,
                candidates=[candidate("accessibility", "Merged", gaps=["merged"])],
            ),
            item(
                "e2",
                True,
                candidates=[candidate("accessibility", "Owner mismatch")],
            ),
            item(
                "e3",
                True,
                candidates=[candidate("accessibility", "Stale")],
                sync="unsynchronized",
            ),
        ]
        examples[2]["candidates"][0]["features"]["owner_consistent"] = False
        visual = PredictionAdapter.from_rows([visual_row(f"e{i}") for i in range(4)])
        assignments = popup_baselines.build_shuffled_gap_permutation(
            examples, self.structured, seed=17
        )
        shuffled = MessageGapRouter(
            self.structured,
            visual,
            mode="shuffled-gap",
            shuffled_gap_assignments=assignments,
        )
        mgpu = MessageGapRouter(self.structured, visual, mode="mg-pu")

        shuffled_results = [shuffled.predict(example) for example in examples]
        mgpu_results = [mgpu.predict(example) for example in examples]

        self.assertEqual(
            Counter(tuple(row["gap_reasons"]) for row in assignments.values()),
            Counter({(): 1, ("merged",): 1, ("owner_mismatch",): 1, ("stale",): 1}),
        )
        self.assertEqual(
            sum(row["visual_call_count"] for row in shuffled_results),
            sum(row["visual_call_count"] for row in mgpu_results),
        )
        self.assertEqual(
            {row["method_id"] for row in shuffled_results},
            {"shuffled-gap-reasons-v1"},
        )
        self.assertTrue(
            all("shuffled-gap:" in row["route_reason"] for row in shuffled_results)
        )
        forbidden = {"action", "recovery", "gold"}
        for row in shuffled_results:
            self.assertFalse(forbidden & {key.casefold() for key in row})


if __name__ == "__main__":
    unittest.main()
