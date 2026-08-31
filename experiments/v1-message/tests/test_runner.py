import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from popup_eval.cli import main as cli_main
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


class CliTests(unittest.TestCase):
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
