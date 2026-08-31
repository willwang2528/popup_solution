#!/usr/bin/env python3
"""Regression tests for gold-blind, collected-but-unannotated union items."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "dataset-v1" / "scripts" / "validate_dataset.py"
MATERIALIZER_PATH = ROOT / "dataset-v1" / "scripts" / "materialize_schema_fixture.py"
SCHEMA_PATH = ROOT / "dataset-v1" / "schema" / "item.schema.json"
FIXTURE_PATH = ROOT / "dataset-v1" / "data" / "items.schema-fixture.jsonl"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load dataset validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def refresh_observability(item: dict) -> None:
    materializer = load_module("popup_fixture_materializer", MATERIALIZER_PATH)
    for obj in [item["assistive_technology"], *item["observations"], *item["candidates"]]:
        obj["presence"] = {}
        obj["field_provenance"] = {}
        materializer.populate_local_maps(obj)
    field_status = {}
    measurement_channel = {}
    for path, value in materializer.iter_leaves(item):
        status = materializer.status_for(path, value)
        field_status[path] = status
        measurement_channel[path] = "fixture_oracle" if value is not None else status
    item["observability"] = {
        "field_status": field_status,
        "measurement_channel": measurement_channel,
    }


def pending_item() -> dict:
    item = json.loads(FIXTURE_PATH.read_text(encoding="utf-8").splitlines()[0])
    item = copy.deepcopy(item)
    item["identity"].update(
        record_kind="real_app",
        collection_status="collected",
        split="pilot",
        item_id="pilot.pending-human-gold.0001",
    )
    item["provenance"].update(
        source_origin="paper_artifact",
        source_dataset="public-archived-real-app-source",
        evidence_level="partial_device_evidence",
        annotation_record_ids=[],
    )

    scenario = item["scenario"]
    scenario.update(
        popup_expected_gt=None,
        popup_kind_gt=None,
        popup_owner_type_gt=None,
        popup_owner_gt=None,
        host_owner_gt=None,
        allowed_action_set_gt=[],
        disallowed_action_set_gt=[],
        abstain_allowed_gt=None,
        unsafe_context_gt=None,
        safety_category_gt=None,
        action_topology_gt=None,
        exposure_status_gt=None,
        exposure_cause_gt=None,
        exposure_cause_evidence=[],
    )

    observation = item["observations"][0]
    observation["popup"].update(
        present_gt=None,
        kind_gt=None,
        bbox_gt=None,
        owner_gt=None,
        modal_gt=None,
        blocking_gt=None,
    )
    for candidate in item["candidates"]:
        candidate["ground_truth"] = {
            key: None for key in candidate["ground_truth"]
        }

    judgment = item["message_judgment"]
    judgment["labels"].update(
        popup_present_gt=None,
        blocking_gt=None,
        message_text_gt=None,
        critical_facts_gt=[],
        message_text_observability="pending_annotation",
        evidence_uris=[],
    )
    judgment["prediction"].update(
        status="abstain",
        popup_present_pred=None,
        message_text_pred=None,
        critical_facts_pred=[],
        confidence=None,
        evidence_uris=[],
        model_or_rule_version="not-run",
        latency_ms=None,
    )
    judgment["evaluation"] = {
        "presence_correct": None,
        "message_semantically_correct": None,
        "critical_information_recall": None,
        "critical_hallucination": None,
        "VPMA": None,
    }
    judgment["eligibility"].update(
        eligible_for_v1_presence_metric=False,
        eligible_for_v1_message_metric=False,
        eligible_for_advanced_recovery_metric=False,
        eligible_for_user_experience_claim=False,
        exclusion_reasons=["pending_human_annotation"],
    )
    item["annotations"] = []
    refresh_observability(item)
    return item


class PendingAnnotationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = load_module("popup_dataset_validator", VALIDATOR_PATH)
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_collected_item_can_preserve_unknown_gold_without_fabrication(self) -> None:
        item = pending_item()

        self.assertEqual([], self.validator.validate_schema(item, self.schema, self.schema))
        self.assertEqual([], self.validator.check_message_judgment(item, 0))

    def test_complete_item_checks_accept_pending_scope_without_invented_safety_gold(self) -> None:
        item = pending_item()

        errors, _warnings = self.validator.check_item(item, 0)

        self.assertEqual([], errors)

    def test_archived_real_app_item_can_record_failed_structured_capture(self) -> None:
        item = pending_item()
        item["capability_profile"]["structured_read_status"] = "failed"
        item["candidates"] = []
        item["decision"]["candidate_input_ids"] = []
        item["decision"]["gate"].update(
            top1_candidate_id=None,
            top1_score=None,
            top2_score=None,
            margin=None,
        )
        structured = item["observations"][0]["structured_representation"]
        structured.update(
            available=False,
            source_channels=[],
            node_count=0,
            interactive_node_count=0,
            android_raw=None,
        )
        refresh_observability(item)

        errors, warnings = self.validator.check_item(item, 0)

        self.assertEqual([], errors)
        self.assertTrue(any("structured capture is explicitly unavailable" in warning for warning in warnings))

    def test_pending_item_rejects_source_or_model_values_as_gold(self) -> None:
        item = pending_item()
        item["observations"][0]["popup"]["present_gt"] = True
        item["scenario"]["unsafe_context_gt"] = False

        errors = self.validator.check_message_judgment(item, 0)

        self.assertTrue(any("scenario ground truth" in error for error in errors))
        self.assertTrue(any("observation popup ground truth" in error for error in errors))

    def test_pending_item_is_never_metric_eligible(self) -> None:
        item = pending_item()
        item["message_judgment"]["eligibility"]["eligible_for_v1_presence_metric"] = True
        item["verification"]["eligibility"]["eligible_for_main_metric"] = True

        errors = self.validator.check_message_judgment(item, 0)

        self.assertTrue(any("eligible for a v1 metric" in error for error in errors))
        self.assertTrue(any("eligible for training or a main metric" in error for error in errors))

    def test_pending_gold_is_not_valid_after_annotation_lifecycle_advances(self) -> None:
        item = pending_item()
        item["identity"]["collection_status"] = "adjudicated"

        errors = self.validator.check_message_judgment(item, 0)

        self.assertTrue(any("only allowed for collected real-app items" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
