from __future__ import annotations

import importlib
import importlib.util
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def item(index: int, *, popup: bool, message: str | None, group: str) -> dict:
    pilot_id = f"PMJ-PILOT-{index:03d}"
    return {
        "identity": {
            "item_id": f"pmj.pending.{index:03d}",
            "pilot_item_id": pilot_id,
            "record_kind": "real_app",
            "scenario_group_id": group,
        },
        "message_judgment": {
            "profile": "popup_message_judgment_v1",
            "labels": {
                "popup_present_gt": popup,
                "message_text_gt": message,
                "critical_facts_gt": [],
                "message_text_observability": "complete" if popup else "not_applicable",
            },
        },
        "observations": [{"observation_id": f"obs.{index}", "phase": "pre_action"}],
        "candidates": [],
        "decision": {"policy": {"decision": "no_action"}},
        "action_attempts": [],
        "adjudication_provenance": {
            "protocol_version": "1.0.0",
            "batch_id": "popsweeper-message-pilot-30-v1",
            "pilot_item_id": pilot_id,
            "adjudication_status": "resolved",
            "evidence_rechecked_via_adapter": True,
            "adjudication_batch_sha256": "a" * 64,
        },
    }


def prediction(index: int, method: str, *, present: bool, message: str | None) -> dict:
    return {
        "action_policy": "no_action",
        "confidence": 0.8,
        "critical_facts_pred": [],
        "human_gold_used": False,
        "message_text_pred": message,
        "method_id": method,
        "paper_result_eligible": False,
        "pilot_item_id": f"PMJ-PILOT-{index:03d}",
        "popup_present_pred": present,
        "route_reason": "frozen_fixture",
        "scored": False,
        "status": "judged",
        "visual_called": method == "mg-pu-gated-union-v1",
    }


def adjudication(index: int, *, popup: bool, message: str | None) -> dict:
    return {
        "protocol_version": "1.0.0",
        "batch_id": "popsweeper-message-pilot-30-v1",
        "pilot_item_id": f"PMJ-PILOT-{index:03d}",
        "record_status": "completed",
        "adjudicator_id_pseudonymous": "adj-1",
        "adjudication_status": "resolved",
        "presence_label_final": "popup" if popup else "no_popup",
        "out_of_scope_reason_final": None,
        "message_text_final": message,
        "message_observability_final": "complete" if popup else "not_applicable",
        "semantic_slots_final": [],
        "decision_rationale": "Evidence rechecked.",
        "evidence_rechecked_via_adapter": True,
        "resolved_at": "2026-09-01T00:00:00Z",
    }


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


class PairedComparisonTests(unittest.TestCase):
    def test_bootstrap_default_seed_is_frozen_to_protocol(self):
        # Break caught: omitted seed silently changes the published bootstrap draws.
        comparison = importlib.import_module("popup_eval.comparison")
        self.assertEqual(comparison.DEFAULT_BOOTSTRAP_SEED, 20260901)
        items = [
            item(1, popup=False, message=None, group="g1"),
            item(2, popup=False, message=None, group="g2"),
        ]
        rows = [
            prediction(index, method, present=False, message=None)
            for method in ("structured-only-v1", "mg-pu-gated-union-v1")
            for index in (1, 2)
        ]
        group_rows = [
            {
                "pilot_item_id": f"PMJ-PILOT-{index:03d}",
                "cluster_id": f"cluster:g{index}",
            }
            for index in (1, 2)
        ]

        report = comparison.compare_frozen_methods(
            items,
            rows,
            group_rows,
            method_ids=["structured-only-v1", "mg-pu-gated-union-v1"],
            proposed_method_id="mg-pu-gated-union-v1",
            strongest_baseline_method_id="structured-only-v1",
            bootstrap_replicates=5,
        )

        self.assertEqual(report["bootstrap"]["seed"], 20260901)

    def test_zero_secondary_denominator_remains_explicitly_undefined(self):
        # Break caught: a zero critical-fact/hallucination denominator is reported as 0.
        comparison = importlib.import_module("popup_eval.comparison")
        items = [
            item(1, popup=False, message=None, group="g1"),
            item(2, popup=False, message=None, group="g2"),
        ]
        rows = [
            prediction(index, method, present=False, message=None)
            for method in ("structured-only-v1", "mg-pu-gated-union-v1")
            for index in (1, 2)
        ]
        group_rows = [
            {
                "pilot_item_id": f"PMJ-PILOT-{index:03d}",
                "cluster_id": f"cluster:g{index}",
                "cluster_source": "frozen_test_group_map",
            }
            for index in (1, 2)
        ]

        report = comparison.compare_frozen_methods(
            items,
            rows,
            group_rows,
            method_ids=["structured-only-v1", "mg-pu-gated-union-v1"],
            proposed_method_id="mg-pu-gated-union-v1",
            strongest_baseline_method_id="structured-only-v1",
            bootstrap_replicates=25,
            seed=9,
        )

        metrics = report["paired_effects"]["metrics"]
        for name in (
            "critical_information_recall",
            "critical_hallucination_rate",
        ):
            self.assertIsNone(metrics[name]["point_estimate_difference"])
            self.assertEqual(metrics[name]["valid_replicates"], 0)
            self.assertIsNone(metrics[name]["confidence_interval_95"])
            self.assertEqual(metrics[name]["ci_status"], "undefined_point_estimate")

    def test_comparison_bootstraps_predeclared_secondary_effects(self):
        # Break caught: the report exposes only VPMA and silently drops required trade-offs.
        comparison = importlib.import_module("popup_eval.comparison")
        items = [
            item(1, popup=True, message="A", group="g1"),
            item(2, popup=True, message="B", group="g2"),
            item(3, popup=False, message=None, group="g3"),
            item(4, popup=False, message=None, group="g4"),
        ]
        items[0]["message_judgment"]["labels"]["critical_facts_gt"] = ["fact-a"]
        rows = [
            prediction(1, "structured-only-v1", present=False, message=None),
            prediction(2, "structured-only-v1", present=True, message="B"),
            prediction(3, "structured-only-v1", present=False, message=None),
            prediction(4, "structured-only-v1", present=True, message="False alert"),
            prediction(1, "mg-pu-gated-union-v1", present=True, message="A"),
            prediction(2, "mg-pu-gated-union-v1", present=True, message="B"),
            prediction(3, "mg-pu-gated-union-v1", present=False, message=None),
            prediction(4, "mg-pu-gated-union-v1", present=False, message=None),
        ]
        rows[0]["critical_facts_pred"] = []
        rows[4]["critical_facts_pred"] = ["fact-a"]
        rows[5].update(
            {
                "status": "abstain",
                "popup_present_pred": None,
                "message_text_pred": None,
                "critical_facts_pred": [],
                "confidence": None,
            }
        )
        group_rows = [
            {
                "pilot_item_id": f"PMJ-PILOT-{index:03d}",
                "cluster_id": f"cluster:g{index}",
                "cluster_source": "frozen_test_group_map",
            }
            for index in range(1, 5)
        ]

        report = comparison.compare_frozen_methods(
            items,
            rows,
            group_rows,
            method_ids=["structured-only-v1", "mg-pu-gated-union-v1"],
            proposed_method_id="mg-pu-gated-union-v1",
            strongest_baseline_method_id="structured-only-v1",
            bootstrap_replicates=200,
            seed=31,
        )

        effects = report["paired_effects"]
        self.assertEqual(effects["direction"], "proposed_minus_reference")
        self.assertEqual(effects["bootstrap_unit"], "group")
        metrics = effects["metrics"]
        self.assertAlmostEqual(
            metrics["vpma_overall_success_rate"]["point_estimate_difference"],
            0.25,
        )
        self.assertAlmostEqual(
            metrics["coverage"]["point_estimate_difference"], -0.25
        )
        self.assertAlmostEqual(
            metrics["presence_macro_f1"]["point_estimate_difference"], 1 / 3
        )
        self.assertAlmostEqual(
            metrics["critical_information_recall"]["point_estimate_difference"],
            1.0,
        )
        self.assertAlmostEqual(
            metrics["critical_hallucination_rate"]["point_estimate_difference"],
            0.0,
        )
        self.assertAlmostEqual(
            metrics["visual_call_rate"]["point_estimate_difference"], 1.0
        )
        for metric in metrics.values():
            self.assertEqual(metric["bootstrap_replicates"], 200)
            self.assertIn("valid_replicates", metric)
            self.assertIn("confidence_interval_95", metric)

    def test_comparison_cli_writes_only_aggregate_hashed_evidence(self):
        # Break caught: the paired runner is not reproducible from frozen private inputs.
        self.assertIsNotNone(importlib.util.find_spec("popup_eval.comparison_cli"))
        comparison_cli = importlib.import_module("popup_eval.comparison_cli")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw_items = [
                item(1, popup=True, message="Gold secret A", group="g1"),
                item(2, popup=False, message=None, group="g2"),
            ]
            for raw in raw_items:
                raw.pop("adjudication_provenance")
                raw["message_judgment"]["labels"].update(
                    {
                        "popup_present_gt": None,
                        "message_text_gt": None,
                        "message_text_observability": "pending_annotation",
                    }
                )
            predictions = [
                prediction(1, "structured-only-v1", present=True, message="Baseline A"),
                prediction(2, "structured-only-v1", present=False, message=None),
                prediction(1, "mg-pu-gated-union-v1", present=True, message="Proposed A"),
                prediction(2, "mg-pu-gated-union-v1", present=False, message=None),
            ]
            items_path = root / "items.jsonl"
            annotations_path = root / "annotations.jsonl"
            predictions_path = root / "predictions.jsonl"
            semantic_path = root / "semantic.jsonl"
            group_map_path = root / "group-map.jsonl"
            output_path = root / "comparison.json"
            write_jsonl(items_path, raw_items)
            write_jsonl(
                annotations_path,
                [
                    adjudication(1, popup=True, message="Gold secret A"),
                    adjudication(2, popup=False, message=None),
                ],
            )
            write_jsonl(predictions_path, predictions)
            write_jsonl(
                group_map_path,
                [
                    {
                        "pilot_item_id": "PMJ-PILOT-001",
                        "cluster_id": "cluster:g1",
                        "cluster_source": "frozen_test_group_map",
                    },
                    {
                        "pilot_item_id": "PMJ-PILOT-002",
                        "cluster_id": "cluster:g2",
                        "cluster_source": "frozen_test_group_map",
                    },
                ],
            )
            write_jsonl(
                semantic_path,
                [
                    {
                        "contract_version": "popup-message-output-adjudication-v1.0",
                        "batch_id": "popsweeper-message-pilot-30-v1",
                        "pilot_item_id": row["pilot_item_id"],
                        "method_id": row["method_id"],
                        "prediction_row_sha256": hashlib.sha256(
                            json.dumps(
                                row,
                                ensure_ascii=False,
                                sort_keys=True,
                                separators=(",", ":"),
                            ).encode("utf-8")
                        ).hexdigest(),
                        "record_status": "completed",
                        "adjudicator_id_pseudonymous": "semantic-adj-1",
                        "message_semantically_correct": True,
                        "critical_hallucination": False,
                        "decision_rationale": "Blind output review completed.",
                        "evidence_rechecked_via_adapter": True,
                        "resolved_at": "2026-09-01T00:00:00Z",
                    }
                    for row in predictions
                    if row["pilot_item_id"] == "PMJ-PILOT-001"
                ],
            )

            result = comparison_cli.main(
                [
                    "--items",
                    str(items_path),
                    "--annotations",
                    str(annotations_path),
                    "--predictions",
                    str(predictions_path),
                    "--semantic-annotations",
                    str(semantic_path),
                    "--group-map",
                    str(group_map_path),
                    "--method-id",
                    "structured-only-v1",
                    "--method-id",
                    "mg-pu-gated-union-v1",
                    "--proposed-method-id",
                    "mg-pu-gated-union-v1",
                    "--strongest-baseline-method-id",
                    "structured-only-v1",
                    "--bootstrap-replicates",
                    "50",
                    "--seed",
                    "5",
                    "--output",
                    str(output_path),
                ]
            )

            self.assertEqual(result, 0)
            report_text = output_path.read_text(encoding="utf-8")
            report = json.loads(report_text)
            self.assertEqual(report["paired_item_count"], 2)
            self.assertEqual(report["adjudication_batch"]["item_count"], 2)
            self.assertEqual(
                set(report["input_sha256"]),
                {
                    "items",
                    "annotations",
                    "predictions",
                    "semantic_annotations",
                    "group_map",
                },
            )
            self.assertEqual(
                {
                    method["metrics"]["vpma"]["mode"]
                    for method in report["methods"].values()
                },
                {"adjudicated"},
            )
            self.assertNotIn("item_values", report_text)
            self.assertNotIn("Gold secret A", report_text)
            self.assertFalse(report["paper_result_eligible"])

    def test_comparison_is_paired_seeded_group_atomic_and_nonclaiming(self):
        # Break caught: methods use different items, item bootstrap, or test-set winner selection.
        self.assertIsNotNone(importlib.util.find_spec("popup_eval.comparison"))
        comparison = importlib.import_module("popup_eval.comparison")
        items = [
            item(1, popup=True, message="A", group="g1"),
            item(2, popup=True, message="B", group="g1"),
            item(3, popup=False, message=None, group="g2"),
            item(4, popup=False, message=None, group="g3"),
        ]
        rows = []
        for index, gold_message in ((1, "A"), (2, "B"), (3, None), (4, None)):
            rows.append(
                prediction(
                    index,
                    "structured-only-v1",
                    present=index != 4,
                    message=(gold_message if index in {1, 2} else "False alert")
                    if index != 4
                    else None,
                )
            )
            rows.append(
                prediction(
                    index,
                    "mg-pu-gated-union-v1",
                    present=index in {1, 2},
                    message=gold_message if index in {1, 2} else None,
                )
            )

        group_rows = [
            {
                "pilot_item_id": f"PMJ-PILOT-{index:03d}",
                "cluster_id": f"cluster:{group}",
                "cluster_source": "frozen_test_group_map",
            }
            for index, group in ((1, "g1"), (2, "g1"), (3, "g2"), (4, "g3"))
        ]

        first = comparison.compare_frozen_methods(
            items,
            rows,
            group_rows,
            method_ids=["structured-only-v1", "mg-pu-gated-union-v1"],
            proposed_method_id="mg-pu-gated-union-v1",
            strongest_baseline_method_id="structured-only-v1",
            bootstrap_replicates=200,
            seed=17,
        )
        second = comparison.compare_frozen_methods(
            list(reversed(items)),
            list(reversed(rows)),
            list(reversed(group_rows)),
            method_ids=["structured-only-v1", "mg-pu-gated-union-v1"],
            proposed_method_id="mg-pu-gated-union-v1",
            strongest_baseline_method_id="structured-only-v1",
            bootstrap_replicates=200,
            seed=17,
        )

        self.assertEqual(first, second)
        self.assertEqual(first["paired_item_count"], 4)
        self.assertEqual(first["bootstrap"]["unit"], "group")
        self.assertEqual(first["bootstrap"]["group_count"], 3)
        self.assertEqual(first["bootstrap"]["replicates"], 200)
        self.assertEqual(
            first["strongest_baseline_selection"],
            "caller_predeclared_exploratory_reference_not_test_selected",
        )
        self.assertIsNone(first["primary_pair"])
        self.assertFalse(first["paper_result_eligible"])
        self.assertFalse(first["claims"]["method_superiority"])
        self.assertFalse(first["claims"]["user_experience_improvement"])
        self.assertFalse(first["claims"]["recovery_or_dismissal"])


if __name__ == "__main__":
    unittest.main()
