import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from popup_eval.cli import main as cli_main
import popup_eval.io as popup_io
import popup_eval.runner as popup_runner
from popup_eval.io import prepare_items
from popup_eval.runner import ContractError, run_experiment, validate_frozen_items


def frozen_item(item_id="e1", popup=True, message="System notice"):
    candidates = []
    if popup:
        candidates = [
            {
                "source_channel": "accessibility",
                "normalized": {
                    "role_or_class": "group",
                    "name_or_text": message,
                    "value_or_hint": None,
                    "visible": True,
                },
                "features": {
                    "inside_popup_roi": True,
                    "belongs_to_host_page": False,
                    "owner_consistent": True,
                    "gap_reasons": [],
                },
            }
        ]
    return {
        "identity": {
            "item_id": item_id,
            "record_kind": "synthetic_schema_fixture",
            "split": "schema_fixture",
        },
        "message_judgment": {
            "profile": "popup_message_judgment_v1",
            "labels": {
                "popup_present_gt": popup,
                "message_text_gt": message if popup else None,
                "critical_facts_gt": [],
                "message_text_observability": "complete" if popup else "not_applicable",
            },
        },
        "observations": [
            {
                "observation_id": "obs.before",
                "phase": "pre_action",
                "synchronization": {"tree_screenshot_sync_status": "synchronized"},
                "structured_representation": {"available": True, "node_count": len(candidates)},
            }
        ],
        "candidates": candidates,
        "decision": {"policy": {"decision": "no_action"}},
        "action_attempts": [],
    }


def adjudication_row(**overrides):
    row = {
        "protocol_version": "1.0.0",
        "batch_id": "popsweeper-message-pilot-30-v1",
        "pilot_item_id": "PMJ-PILOT-007",
        "record_status": "completed",
        "adjudicator_id_pseudonymous": "adj-1",
        "adjudication_status": "resolved",
        "presence_label_final": "popup",
        "out_of_scope_reason_final": None,
        "message_text_final": "Adjudicated label",
        "message_observability_final": "complete",
        "semantic_slots_final": [
            {"slot_type": "object_target", "value": "account", "polarity": "affirmed"}
        ],
        "decision_rationale": "Evidence is legible.",
        "evidence_rechecked_via_adapter": True,
        "resolved_at": "2026-09-01T00:00:00Z",
    }
    row.update(overrides)
    return row


def frozen_prediction_row(**overrides):
    row = {
        "action_policy": "no_action",
        "confidence": 0.75,
        "critical_facts_pred": ["account"],
        "human_gold_used": False,
        "message_text_pred": "Frozen prediction",
        "method_id": "structured-only-v1",
        "paper_result_eligible": False,
        "pilot_item_id": "PMJ-PILOT-007",
        "popup_present_pred": True,
        "route_reason": "structured_full_tree_text",
        "scored": False,
        "status": "judged",
        "visual_called": False,
    }
    row.update(overrides)
    return row


class ContractTests(unittest.TestCase):
    def test_actionful_item_is_rejected_before_evaluation(self):
        # Break caught: an experiment silently evaluates or triggers dismissal behavior.
        actionful = frozen_item()
        actionful["action_attempts"] = [{"action": "tap"}]

        with self.assertRaisesRegex(ContractError, "action-free"):
            validate_frozen_items([actionful])

    def test_post_action_observation_is_rejected(self):
        # Break caught: v1 metrics accidentally consume information after a click.
        post_action = frozen_item()
        post_action["observations"][0]["phase"] = "post_action"

        with self.assertRaisesRegex(ContractError, "pre-action"):
            validate_frozen_items([post_action])


class AnnotationTests(unittest.TestCase):
    def test_adjudication_batch_rejects_duplicate_missing_and_unknown_ids(self):
        # Break caught: a partial or ambiguous gold batch is silently treated as final.
        items = [frozen_item(item_id="i7"), frozen_item(item_id="i8")]
        items[0]["identity"]["pilot_item_id"] = "PMJ-PILOT-007"
        items[1]["identity"]["pilot_item_id"] = "PMJ-PILOT-008"
        row_7 = adjudication_row(pilot_item_id="PMJ-PILOT-007")
        row_8 = adjudication_row(pilot_item_id="PMJ-PILOT-008")
        row_9 = adjudication_row(pilot_item_id="PMJ-PILOT-009")

        self.assertTrue(hasattr(popup_io, "finalize_adjudication_batch"))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            popup_io.finalize_adjudication_batch(items, [row_7, row_7, row_8])
        with self.assertRaisesRegex(ValueError, "missing"):
            popup_io.finalize_adjudication_batch(items, [row_7])
        with self.assertRaisesRegex(ValueError, "unknown"):
            popup_io.finalize_adjudication_batch(items, [row_7, row_8, row_9])

    def test_adjudication_batch_hash_is_order_independent_and_counts_are_explicit(self):
        # Break caught: file row order changes the frozen-gold identity or hides exclusions.
        items = [frozen_item(item_id="i7"), frozen_item(item_id="i8")]
        items[0]["identity"]["pilot_item_id"] = "PMJ-PILOT-007"
        items[1]["identity"]["pilot_item_id"] = "PMJ-PILOT-008"
        row_7 = adjudication_row(pilot_item_id="PMJ-PILOT-007")
        row_8 = adjudication_row(
            pilot_item_id="PMJ-PILOT-008",
            adjudication_status="cannot_resolve",
            presence_label_final=None,
            message_text_final=None,
            message_observability_final=None,
            semantic_slots_final=[],
        )

        rows_a, summary_a = popup_io.finalize_adjudication_batch(items, [row_8, row_7])
        rows_b, summary_b = popup_io.finalize_adjudication_batch(items, [row_7, row_8])

        self.assertEqual(
            [row["pilot_item_id"] for row in rows_a],
            ["PMJ-PILOT-007", "PMJ-PILOT-008"],
        )
        self.assertEqual(rows_a, rows_b)
        self.assertEqual(summary_a["batch_sha256"], summary_b["batch_sha256"])
        self.assertEqual(summary_a["item_count"], 2)
        self.assertEqual(summary_a["resolved_count"], 1)
        self.assertEqual(summary_a["cannot_resolve_count"], 1)
        self.assertEqual(summary_a["metric_eligible_count"], 1)

    def test_cannot_resolve_adjudication_cannot_carry_final_labels(self):
        # Break caught: an unresolved row leaks ambiguous labels into a frozen gold batch.
        items = [frozen_item(item_id="i7")]
        items[0]["identity"]["pilot_item_id"] = "PMJ-PILOT-007"
        invalid = adjudication_row(adjudication_status="cannot_resolve")

        with self.assertRaisesRegex(ValueError, "cannot_resolve"):
            popup_io.finalize_adjudication_batch(items, [invalid])

    def test_out_of_scope_adjudication_is_resolved_but_never_metric_eligible(self):
        item = frozen_item(item_id="i7")
        item["identity"]["pilot_item_id"] = "PMJ-PILOT-007"
        row = adjudication_row(
            presence_label_final="out_of_scope",
            out_of_scope_reason_final="permission_security_control",
            message_text_final=None,
            message_observability_final="not_applicable",
            semantic_slots_final=[],
        )

        _, summary = popup_io.finalize_adjudication_batch([item], [row])
        prepared, _ = popup_io.prepare_items([item], [row])

        self.assertEqual(summary["resolved_count"], 1)
        self.assertEqual(summary["out_of_scope_count"], 1)
        self.assertEqual(summary["metric_eligible_count"], 0)
        self.assertIn(
            "out_of_scope:permission_security_control",
            prepared[0]["evaluation_exclusion_reasons"],
        )

    def test_finalized_gold_join_preserves_private_structured_features(self):
        # Break caught: human gold and archived UI structure cannot inhabit the same item.
        items = [frozen_item(item_id="pmj.pending.007")]
        items[0]["identity"]["record_kind"] = "real_app"
        items[0]["identity"]["pilot_item_id"] = "PMJ-PILOT-007"
        items[0]["candidates"][0]["source_channel"] = "uiautomator"
        items[0]["candidates"][0]["android_raw"] = {
            "text": "Archived structured message"
        }

        self.assertTrue(hasattr(popup_io, "prepare_finalized_pilot_items"))
        prepared, semantic, summary = popup_io.prepare_finalized_pilot_items(
            items, [adjudication_row()]
        )

        self.assertEqual(prepared[0]["identity"]["pilot_item_id"], "PMJ-PILOT-007")
        self.assertEqual(
            prepared[0]["candidates"][0]["android_raw"]["text"],
            "Archived structured message",
        )
        self.assertEqual(
            prepared[0]["message_judgment"]["labels"]["message_text_gt"],
            "Adjudicated label",
        )
        self.assertEqual(semantic, {})
        self.assertEqual(summary["item_count"], 1)
        self.assertEqual(summary["metric_eligible_count"], 1)

    def test_pilot_adjudication_output_aligns_by_pilot_item_id(self):
        # Break caught: frozen pilot gold is joined by display order or source label.
        items = [frozen_item(message="Embedded label")]
        items[0]["identity"]["pilot_item_id"] = "PMJ-PILOT-007"
        rows = [adjudication_row()]

        prepared, semantic = prepare_items(items, rows)

        self.assertEqual(
            prepared[0]["message_judgment"]["labels"]["message_text_gt"],
            "Adjudicated label",
        )
        self.assertEqual(
            prepared[0]["message_judgment"]["labels"]["critical_facts_gt"],
            ["account"],
        )
        self.assertEqual(semantic, {})

    def test_incomplete_or_unrechecked_adjudication_is_rejected(self):
        # Break caught: a fabricated minimally resolved row is accepted as adjudicated gold.
        items = [frozen_item()]
        items[0]["identity"]["pilot_item_id"] = "PMJ-PILOT-007"
        invalid_rows = [
            adjudication_row(evidence_rechecked_via_adapter=False),
            adjudication_row(adjudicator_id_pseudonymous=None),
        ]

        for row in invalid_rows:
            with self.subTest(row=row):
                with self.assertRaisesRegex(ValueError, "adjudication"):
                    prepare_items(items, [row])

    def test_blank_pilot_adjudication_template_is_ignored(self):
        # Break caught: an untouched frozen template row aborts a partially completed batch.
        items = [frozen_item()]
        items[0]["identity"]["pilot_item_id"] = "PMJ-PILOT-007"
        blank = {
            "protocol_version": "1.0.0",
            "batch_id": "popsweeper-message-pilot-30-v1",
            "pilot_item_id": None,
            "record_status": "blank",
            "adjudication_status": "pending",
            "presence_label_final": None,
        }

        prepared, _ = prepare_items(items, [blank])

        self.assertEqual(
            prepared[0]["message_judgment"]["labels"]["message_text_gt"],
            "System notice",
        )


class RunnerTests(unittest.TestCase):
    def test_frozen_run_binds_one_gold_batch_and_exact_metric_item_set(self):
        # Break caught: a scored snapshot can be detached from the exact gold batch/items.
        sources = [
            frozen_item(item_id="pmj.pending.007"),
            frozen_item(item_id="pmj.pending.008"),
        ]
        sources[0]["identity"].update(
            {"record_kind": "real_app", "pilot_item_id": "PMJ-PILOT-007"}
        )
        sources[1]["identity"].update(
            {"record_kind": "real_app", "pilot_item_id": "PMJ-PILOT-008"}
        )
        prepared, _, adjudication_summary = popup_io.prepare_finalized_pilot_items(
            sources,
            [
                adjudication_row(pilot_item_id="PMJ-PILOT-007"),
                adjudication_row(pilot_item_id="PMJ-PILOT-008"),
            ],
        )

        result = popup_runner.run_frozen_prediction_experiment(
            prepared,
            [
                frozen_prediction_row(pilot_item_id="PMJ-PILOT-007"),
                frozen_prediction_row(pilot_item_id="PMJ-PILOT-008"),
            ],
            "structured-only-v1",
        )

        self.assertEqual(
            result["run"]["adjudication_batch_sha256"],
            adjudication_summary["batch_sha256"],
        )
        self.assertEqual(len(result["run"]["metric_item_set_sha256"]), 64)
        self.assertEqual(
            result["run"]["metric_item_set_sha256"],
            hashlib.sha256(
                json.dumps(
                    ["PMJ-PILOT-007", "PMJ-PILOT-008"],
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
        )
        self.assertNotIn("metric_item_pilot_ids", result["run"])

    def test_gold_mutation_cannot_change_frozen_prediction_hash_or_output(self):
        # Break caught: after gold unlock, a method is rerun or its frozen output mutates.
        source = frozen_item(item_id="pmj.pending.007", message="Archived message")
        source["identity"]["record_kind"] = "real_app"
        source["identity"]["pilot_item_id"] = "PMJ-PILOT-007"
        gold_a = adjudication_row(message_text_final="Gold A")
        gold_b = adjudication_row(message_text_final="Gold B")
        items_a, _, _ = popup_io.prepare_finalized_pilot_items([source], [gold_a])
        items_b, _, _ = popup_io.prepare_finalized_pilot_items([source], [gold_b])

        self.assertTrue(hasattr(popup_runner, "run_frozen_prediction_experiment"))
        result_a = popup_runner.run_frozen_prediction_experiment(
            items_a, [frozen_prediction_row()], "structured-only-v1"
        )
        result_b = popup_runner.run_frozen_prediction_experiment(
            items_b, [frozen_prediction_row()], "structured-only-v1"
        )

        self.assertEqual(
            result_a["run"]["frozen_prediction_sha256"],
            result_b["run"]["frozen_prediction_sha256"],
        )
        self.assertEqual(result_a["predictions"], result_b["predictions"])
        self.assertEqual(result_a["predictions"][0]["message_text_pred"], "Frozen prediction")
        self.assertEqual(
            result_a["metrics"]["message"]["denominator_popup_positive_complete"],
            1,
        )
        self.assertFalse(result_a["run"]["paper_result_eligible"])

    def test_frozen_prediction_scoring_requires_exact_metric_item_coverage(self):
        # Break caught: a partial, duplicate, or foreign prediction set is scored as complete.
        sources = [
            frozen_item(item_id="pmj.pending.007"),
            frozen_item(item_id="pmj.pending.008"),
        ]
        sources[0]["identity"].update(
            {"record_kind": "real_app", "pilot_item_id": "PMJ-PILOT-007"}
        )
        sources[1]["identity"].update(
            {"record_kind": "real_app", "pilot_item_id": "PMJ-PILOT-008"}
        )
        gold = [
            adjudication_row(pilot_item_id="PMJ-PILOT-007"),
            adjudication_row(pilot_item_id="PMJ-PILOT-008"),
        ]
        prepared, _, _ = popup_io.prepare_finalized_pilot_items(sources, gold)
        row_7 = frozen_prediction_row(pilot_item_id="PMJ-PILOT-007")
        row_8 = frozen_prediction_row(pilot_item_id="PMJ-PILOT-008")
        row_9 = frozen_prediction_row(pilot_item_id="PMJ-PILOT-009")

        with self.assertRaisesRegex(ContractError, "missing frozen predictions"):
            popup_runner.run_frozen_prediction_experiment(
                prepared, [row_7], "structured-only-v1"
            )
        with self.assertRaisesRegex(ContractError, "duplicate frozen prediction"):
            popup_runner.run_frozen_prediction_experiment(
                prepared, [row_7, row_7, row_8], "structured-only-v1"
            )
        with self.assertRaisesRegex(ContractError, "unknown pilot_item_id"):
            popup_runner.run_frozen_prediction_experiment(
                prepared, [row_7, row_8, row_9], "structured-only-v1"
            )

    def test_frozen_prediction_hash_covers_batch_while_unresolved_gold_is_excluded(self):
        # Break caught: a pre-gold row becomes "unknown" only because its human gold is unresolved.
        sources = [
            frozen_item(item_id="pmj.pending.007"),
            frozen_item(item_id="pmj.pending.008"),
        ]
        sources[0]["identity"].update(
            {"record_kind": "real_app", "pilot_item_id": "PMJ-PILOT-007"}
        )
        sources[1]["identity"].update(
            {"record_kind": "real_app", "pilot_item_id": "PMJ-PILOT-008"}
        )
        gold = [
            adjudication_row(pilot_item_id="PMJ-PILOT-007"),
            adjudication_row(
                pilot_item_id="PMJ-PILOT-008",
                adjudication_status="cannot_resolve",
                presence_label_final=None,
                message_text_final=None,
                message_observability_final=None,
                semantic_slots_final=[],
            ),
        ]
        prepared, _, _ = popup_io.prepare_finalized_pilot_items(sources, gold)

        result = popup_runner.run_frozen_prediction_experiment(
            prepared,
            [
                frozen_prediction_row(pilot_item_id="PMJ-PILOT-007"),
                frozen_prediction_row(pilot_item_id="PMJ-PILOT-008"),
            ],
            "structured-only-v1",
        )

        self.assertEqual(result["run"]["input_item_count"], 2)
        self.assertEqual(result["run"]["evaluated_item_count"], 1)
        self.assertEqual(result["run"]["excluded_item_count"], 1)
        self.assertEqual(len(result["run"]["frozen_prediction_sha256"]), 64)

    def test_non_synthetic_union_item_requires_human_adjudication_provenance(self):
        # Break caught: model/source labels in a real_app-shaped item enter metrics as gold.
        item = frozen_item()
        item["identity"]["record_kind"] = "real_app"

        with self.assertRaisesRegex(ContractError, "metric-eligible presence gold"):
            run_experiment([item], method="structured")

    def test_human_adjudicated_union_item_can_enter_technical_metrics(self):
        item = frozen_item()
        item["identity"]["record_kind"] = "real_app"
        item["message_judgment"]["labels"]["evidence_uris"] = [
            {"uri": "evidence://human/real-1"}
        ]
        item["message_judgment"]["eligibility"] = {
            "eligible_for_v1_presence_metric": True,
            "eligible_for_v1_message_metric": True,
            "exclusion_reasons": [],
        }
        item["annotations"] = [
            {
                "target_json_pointer": "/message_judgment/labels/popup_present_gt",
                "annotator_role": "accessibility_expert",
                "label_name": "popup_present_gt",
                "label_value": True,
                "evidence_uris": [{"uri": "evidence://human/real-1"}],
                "adjudication_status": "adjudicated",
                "adjudicator_id_pseudonymous": "adj-1",
            },
            {
                "target_json_pointer": "/message_judgment/labels/message_text_gt",
                "annotator_role": "accessibility_expert",
                "label_name": "message_text_gt",
                "label_value": "System notice",
                "evidence_uris": [{"uri": "evidence://human/real-1"}],
                "adjudication_status": "adjudicated",
                "adjudicator_id_pseudonymous": "adj-1",
            },
        ]

        result = run_experiment([item], method="structured")

        self.assertEqual(result["run"]["evaluated_item_count"], 1)
        self.assertEqual(result["run"]["evidence_level"], "technical_dataset_evaluation")
        self.assertFalse(result["run"]["paper_result_eligible"])

    def test_finalized_real_app_pilot_enters_exploratory_metrics_via_batch_provenance(self):
        # Break caught: a complete human-gold batch joins features but remains unscorable.
        source = frozen_item(item_id="pmj.pending.007", message="Archived message")
        source["identity"]["record_kind"] = "real_app"
        source["identity"]["pilot_item_id"] = "PMJ-PILOT-007"
        prepared, _, _ = popup_io.prepare_finalized_pilot_items(
            [source], [adjudication_row()]
        )

        result = run_experiment(prepared, method="structured")

        self.assertEqual(result["run"]["evaluated_item_count"], 1)
        self.assertEqual(result["run"]["evidence_level"], "adjudicated_annotation_pilot")
        self.assertFalse(result["run"]["paper_result_eligible"])
        self.assertFalse(result["run"]["claims"]["user_experience_improvement"])

    def test_presence_eligible_real_popup_is_not_dropped_when_message_is_unobservable(self):
        # Break caught: full-union representation loses presence evidence because only the
        # conditional message metric is ineligible.
        item = frozen_item(message=None)
        item["identity"]["record_kind"] = "real_app"
        labels = item["message_judgment"]["labels"]
        labels["message_text_observability"] = "not_observable"
        labels["evidence_uris"] = [{"uri": "evidence://human/real-hidden"}]
        item["message_judgment"]["eligibility"] = {
            "eligible_for_v1_presence_metric": True,
            "eligible_for_v1_message_metric": False,
            "exclusion_reasons": [],
        }
        item["annotations"] = [
            {
                "target_json_pointer": "/message_judgment/labels/popup_present_gt",
                "annotator_role": "accessibility_expert",
                "label_name": "popup_present_gt",
                "label_value": True,
                "evidence_uris": [{"uri": "evidence://human/real-hidden"}],
                "adjudication_status": "adjudicated",
                "adjudicator_id_pseudonymous": "adj-1",
            }
        ]

        result = run_experiment([item], method="structured")

        self.assertEqual(result["run"]["evaluated_item_count"], 1)
        self.assertEqual(result["metrics"]["presence"]["fn"], 1)
        self.assertEqual(
            result["metrics"]["message"]["denominator_popup_positive_complete"],
            0,
        )

    def test_empty_evidence_uri_cannot_make_union_gold_eligible(self):
        # Break caught: truthy evidence containers with empty URI objects bypass provenance.
        item = frozen_item()
        item["identity"]["record_kind"] = "real_app"
        item["message_judgment"]["labels"]["evidence_uris"] = [{}]
        item["message_judgment"]["eligibility"] = {
            "eligible_for_v1_presence_metric": True,
            "eligible_for_v1_message_metric": True,
            "exclusion_reasons": [],
        }
        item["annotations"] = [
            {
                "target_json_pointer": "/message_judgment/labels/popup_present_gt",
                "annotator_role": "accessibility_expert",
                "label_name": "popup_present_gt",
                "label_value": True,
                "evidence_uris": [{}],
                "adjudication_status": "adjudicated",
                "adjudicator_id_pseudonymous": "adj-1",
            },
            {
                "target_json_pointer": "/message_judgment/labels/message_text_gt",
                "annotator_role": "accessibility_expert",
                "label_name": "message_text_gt",
                "label_value": "System notice",
                "evidence_uris": [{"uri": ""}],
                "adjudication_status": "adjudicated",
                "adjudicator_id_pseudonymous": "adj-1",
            },
        ]

        with self.assertRaisesRegex(ContractError, "metric-eligible presence gold"):
            run_experiment([item], method="structured")

    def test_run_experiment_emits_action_free_predictions_and_metrics(self):
        # Break caught: result rows gain executable targets or omit required metrics.
        result = run_experiment([frozen_item()], method="structured", seed=11)

        self.assertEqual(result["run"]["action_policy"], "no_action")
        self.assertEqual(result["run"]["seed"], 11)
        self.assertEqual(result["metrics"]["presence"]["f1"], 1.0)
        self.assertEqual(result["metrics"]["vpma"]["overall_success_rate"], 1.0)
        self.assertEqual(result["predictions"][0]["evidence_level"], "synthetic_pipeline_fixture")
        self.assertFalse(result["predictions"][0]["paper_result_eligible"])
        self.assertFalse(
            {"action", "target", "coordinate", "selector"}
            & set(result["predictions"][0])
        )

    def test_the_ok_method_is_available_through_the_same_evaluator(self):
        # Break caught: A2 is a standalone demo and cannot enter the common comparison.
        example = frozen_item(message="We use cookies for analytics")
        example["candidates"][0]["source_channel"] = "structured"
        example["candidates"][0]["features"]["text"] = "We use cookies for analytics"
        example["candidates"][0]["features"]["node_index"] = 1

        result = run_experiment([example], method="the-ok")

        self.assertEqual(result["run"]["method"], "the-ok")
        self.assertEqual(result["predictions"][0]["method_id"], "the-ok-text-rule")
        self.assertEqual(result["metrics"]["presence"]["tp"], 1)

    def test_shuffled_gap_method_is_reproducible_budget_matched_and_output_safe(self):
        # Break caught: ABL-003 is unavailable through the common runner, changes
        # budget, depends on row/gold order, or leaks action/Recovery/gold fields.
        self.assertIn("shuffled-gap", popup_runner.METHODS)
        examples = [frozen_item(item_id=f"e{i}", message=f"Message {i}") for i in range(4)]
        examples[1]["candidates"][0]["features"]["gap_reasons"] = ["merged"]
        examples[2]["candidates"][0]["features"]["owner_consistent"] = False
        examples[3]["observations"][0]["synchronization"][
            "tree_screenshot_sync_status"
        ] = "unsynchronized"
        visual_rows = [
            {
                "item_id": f"e{i}",
                "status": "judged",
                "popup_present_pred": True,
                "message_text_pred": f"Visual {i}",
                "critical_facts_pred": [],
                "confidence": 0.9,
                "source_observation_id": "obs.before",
            }
            for i in range(4)
        ]
        mutated = json.loads(json.dumps(examples))
        for example in mutated:
            example["message_judgment"]["labels"].update(
                {
                    "popup_present_gt": False,
                    "message_text_gt": None,
                    "critical_facts_gt": ["changed gold"],
                }
            )
            example["advanced"] = {
                "Recovery": {"action": "dismiss", "target": "forbidden"}
            }

        mgpu = run_experiment(examples, method="mg-pu", seed=17, prediction_rows=visual_rows)
        first = run_experiment(
            examples,
            method="shuffled-gap",
            seed=17,
            prediction_rows=visual_rows,
        )
        second = run_experiment(
            list(reversed(mutated)),
            method="shuffled-gap",
            seed=17,
            prediction_rows=visual_rows,
        )

        self.assertEqual(first["run"]["method"], "shuffled-gap")
        self.assertEqual(first["run"]["method_config"], second["run"]["method_config"])
        self.assertEqual(first["run"]["method_config"], {
            "matched_visual_call_count": 3,
            "shuffle_seed": 17,
            "shuffled_gap_permutation": [
                {"item_id": "e0", "source_item_id": "e2", "gap_reasons": ["owner_mismatch"]},
                {"item_id": "e1", "source_item_id": "e3", "gap_reasons": ["stale"]},
                {"item_id": "e2", "source_item_id": "e1", "gap_reasons": ["merged"]},
                {"item_id": "e3", "source_item_id": "e0", "gap_reasons": []},
            ],
        })
        self.assertEqual(
            sum(row["visual_call_count"] for row in first["predictions"]),
            sum(row["visual_call_count"] for row in mgpu["predictions"]),
        )
        self.assertEqual(
            {row["method_id"] for row in first["predictions"]},
            {"shuffled-gap-reasons-v1"},
        )
        self.assertEqual(
            sorted(first["predictions"], key=lambda row: row["item_id"]),
            sorted(second["predictions"], key=lambda row: row["item_id"]),
        )

        def nested_keys(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    yield key.casefold()
                    yield from nested_keys(child)
            elif isinstance(value, list):
                for child in value:
                    yield from nested_keys(child)

        forbidden = {"action", "recovery", "gold"}
        self.assertFalse(forbidden & set(nested_keys(first["predictions"])))
        self.assertFalse(forbidden & set(nested_keys(first["run"]["method_config"])))


class CliTests(unittest.TestCase):
    def test_cli_scores_the_named_frozen_method_without_rerunning_it(self):
        # Break caught: formal CLI ignores the pre-gold snapshot and reruns a mutable rule.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = frozen_item(item_id="pmj.pending.007", message="Archived message")
            source["identity"].update(
                {"record_kind": "real_app", "pilot_item_id": "PMJ-PILOT-007"}
            )
            items_path = root / "items.jsonl"
            annotations_path = root / "annotations.jsonl"
            predictions_path = root / "predictions.jsonl"
            items_path.write_text(json.dumps(source) + "\n", encoding="utf-8")
            annotations_path.write_text(
                json.dumps(adjudication_row(), ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            predictions_path.write_text(
                json.dumps(frozen_prediction_row(), ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            output = root / "output"

            self.assertEqual(
                cli_main(
                    [
                        "--items",
                        str(items_path),
                        "--annotations",
                        str(annotations_path),
                        "--predictions",
                        str(predictions_path),
                        "--method",
                        "frozen-prediction",
                        "--frozen-prediction-method-id",
                        "structured-only-v1",
                        "--output-dir",
                        str(output),
                    ]
                ),
                0,
            )

            manifest = json.loads(
                (output / "run_manifest.json").read_text(encoding="utf-8")
            )
            predictions = [
                json.loads(line)
                for line in (output / "predictions.jsonl").read_text().splitlines()
            ]
            self.assertEqual(manifest["method"], "structured-only-v1")
            self.assertEqual(manifest["prediction_source"], "pregold_frozen_snapshot")
            self.assertEqual(len(manifest["frozen_prediction_sha256"]), 64)
            self.assertEqual(predictions[0]["message_text_pred"], "Frozen prediction")

    def test_cli_requires_and_records_a_complete_finalized_pilot_batch(self):
        # Break caught: CLI accepts partial adjudication and emits results without a gold hash.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = frozen_item(item_id="pmj.pending.007", message="Archived message")
            source["identity"]["record_kind"] = "real_app"
            source["identity"]["pilot_item_id"] = "PMJ-PILOT-007"
            items_path = root / "items.jsonl"
            annotations_path = root / "annotations.jsonl"
            items_path.write_text(json.dumps(source) + "\n", encoding="utf-8")
            annotations_path.write_text(
                json.dumps(adjudication_row(), ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            output = root / "output"

            self.assertEqual(
                cli_main(
                    [
                        "--items",
                        str(items_path),
                        "--annotations",
                        str(annotations_path),
                        "--method",
                        "structured",
                        "--output-dir",
                        str(output),
                    ]
                ),
                0,
            )

            manifest = json.loads(
                (output / "run_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                set(manifest["adjudication_batch"]),
                {
                    "status",
                    "protocol_version",
                    "batch_id",
                    "item_count",
                    "resolved_count",
                    "cannot_resolve_count",
                    "metric_eligible_count",
                    "out_of_scope_count",
                    "batch_sha256",
                },
            )
            self.assertEqual(manifest["adjudication_batch"]["item_count"], 1)
            self.assertEqual(len(manifest["adjudication_batch"]["batch_sha256"]), 64)
            self.assertNotIn("Adjudicated label", json.dumps(manifest))

    def test_cli_is_reproducible_and_labels_synthetic_output_non_empirical(self):
        # Break caught: run output depends on wall clock/path or looks like an empirical result.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            items_path = root / "items.jsonl"
            items_path.write_text(
                json.dumps(frozen_item(), ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            first = root / "first"
            second = root / "second"

            self.assertEqual(
                cli_main(["--items", str(items_path), "--method", "structured", "--output-dir", str(first), "--seed", "7"]),
                0,
            )
            self.assertEqual(
                cli_main(["--items", str(items_path), "--method", "structured", "--output-dir", str(second), "--seed", "7"]),
                0,
            )

            self.assertEqual((first / "metrics.json").read_bytes(), (second / "metrics.json").read_bytes())
            self.assertEqual((first / "run_manifest.json").read_bytes(), (second / "run_manifest.json").read_bytes())
            manifest = json.loads((first / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["evidence_level"], "synthetic_pipeline_fixture")
            self.assertEqual(manifest["action_policy"], "no_action")
            self.assertFalse(manifest["paper_result_eligible"])
            self.assertFalse(manifest["claims"]["empirical_performance"])
            self.assertFalse(manifest["claims"]["user_experience_improvement"])
            self.assertEqual(
                set(manifest["implementation_sha256"]),
                {
                    "baselines.py",
                    "cli.py",
                    "io.py",
                    "metrics.py",
                    "resources/the-ok/indicators.json",
                    "runner.py",
                    "the_ok_baseline.py",
                },
            )
            self.assertTrue(all(len(value) == 64 for value in manifest["implementation_sha256"].values()))
            metrics = json.loads((first / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["evidence_level"], "synthetic_pipeline_fixture")
            self.assertFalse(metrics["paper_result_eligible"])


if __name__ == "__main__":
    unittest.main()
