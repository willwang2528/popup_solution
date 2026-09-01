from __future__ import annotations

import copy
import hashlib
import importlib
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

MG_PU = "mg-pu-k50-v1"
SEEDED_RANDOM = "seeded-random-k50-v1"
METHODS = (MG_PU, SEEDED_RANDOM)
GOLD_SHA256 = "b" * 64


def canonical_row_sha256(row: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def canonical_jsonl_sha256(rows: list[dict]) -> str:
    payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
        for row in rows
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def selected_item_hash(item_ids: list[str]) -> str:
    return hashlib.sha256(("\n".join(sorted(item_ids)) + "\n").encode("utf-8")).hexdigest()


def item_set_hash(item_ids: list[str]) -> str:
    return hashlib.sha256(
        json.dumps(sorted(item_ids), separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def adjudicated_item(index: int) -> dict:
    pilot_id = f"PMJ-PILOT-{index:03d}"
    return {
        "identity": {
            "item_id": f"formal.item.{index:03d}",
            "pilot_item_id": pilot_id,
            "record_kind": "real_app",
        },
        "message_judgment": {
            "profile": "popup_message_judgment_v1",
            "labels": {
                "popup_present_gt": True,
                "message_text_gt": f"gold-{index}",
                "critical_facts_gt": [],
                "message_text_observability": "complete",
            },
        },
        "observations": [
            {"observation_id": f"obs.{index}", "phase": "pre_action"}
        ],
        "candidates": [],
        "decision": {"policy": {"decision": "no_action"}},
        "action_attempts": [],
        "evaluation_exclusion_reasons": [],
        "adjudication_provenance": {
            "protocol_version": "1.0.0",
            "batch_id": "formal-message-batch-v1",
            "pilot_item_id": pilot_id,
            "adjudication_status": "resolved",
            "evidence_rechecked_via_adapter": True,
            "adjudication_batch_sha256": GOLD_SHA256,
            "capture_binding": {
                "capture_id": f"PMAB-A-CAP-{index:03d}",
                "capture_schema_version": "1.1.0",
                "capture_status": "eligible_for_capture_feasibility",
                "collector_mode": "accessibilityservice_node_snapshot",
                "source_origin": "real_device",
                "privacy_review_status": "passed",
                "finalized_capture_record_sha256": f"{index + 100:064x}",
                "screenshot_sha256": f"{index + 200:064x}",
                "accessibility_snapshot_sha256": f"{index + 300:064x}",
                "capture_delta_ms": 400,
                "maximum_delta_ms": 3000,
                "stable_state_verified": True,
            },
        },
    }


def frozen_prediction(index: int, method_id: str) -> dict:
    selected = index <= 3 if method_id == MG_PU else index >= 4
    return {
        "action_policy": "no_action",
        "confidence": 0.9,
        "critical_facts_pred": [],
        "human_gold_used": False,
        "message_text_pred": f"prediction-{index}",
        "method_id": method_id,
        "paper_result_eligible": False,
        "pilot_item_id": f"PMJ-PILOT-{index:03d}",
        "popup_present_pred": True,
        "route_reason": "frozen_k50_fixture",
        "scored": False,
        "status": "judged",
        "visual_called": selected,
    }


def semantic_row(prediction: dict, *, correct: bool) -> dict:
    return {
        "contract_version": "popup-message-output-adjudication-v1.0",
        "batch_id": "formal-message-batch-v1",
        "pilot_item_id": prediction["pilot_item_id"],
        "method_id": prediction["method_id"],
        "prediction_row_sha256": canonical_row_sha256(prediction),
        "record_status": "completed",
        "adjudicator_id_pseudonymous": "semantic-adj-1",
        "message_semantically_correct": correct,
        "critical_hallucination": False,
        "decision_rationale": "Blind output review completed.",
        "evidence_rechecked_via_adapter": True,
        "resolved_at": "2026-09-01T10:00:00Z",
    }


def group_rows() -> list[dict]:
    return [
        {
            "pilot_item_id": f"PMJ-PILOT-{index:03d}",
            "cluster_id": f"cluster:g{index}",
            "cluster_source": "formal_app_template_groups_v1",
        }
        for index in range(1, 7)
    ]


def receipt_bundle(predictions: list[dict], groups: list[dict]) -> tuple[dict, dict]:
    pilot_ids = [f"PMJ-PILOT-{index:03d}" for index in range(1, 7)]
    common = {
        "metric_item_set_sha256": item_set_hash(pilot_ids),
        "adjudication_batch_sha256": GOLD_SHA256,
        "visual_bank_sha256": "d" * 64,
        "visual_config_sha256": "e" * 64,
        "budget_spec_sha256": "f" * 64,
        "operating_point": "K50",
        "actual_budget": {
            "visual_calls": 3,
            "decoded_pixels": 3000,
            "input_tokens": 600,
            "output_tokens": 120,
            "monetary_cost_microunits": 10000,
        },
    }
    receipts = {}
    for method_id in METHODS:
        method_rows = sorted(
            [row for row in predictions if row["method_id"] == method_id],
            key=lambda row: row["pilot_item_id"],
        )
        selected = [row["pilot_item_id"] for row in method_rows if row["visual_called"]]
        receipts[method_id] = {
            **copy.deepcopy(common),
            "selected_item_set_sha256": selected_item_hash(selected),
            "frozen_prediction_sha256": canonical_jsonl_sha256(method_rows),
        }
    group_hash = canonical_jsonl_sha256(sorted(groups, key=lambda row: row["pilot_item_id"]))
    group_attestation = {
        "group_map_sha256": group_hash,
        "formal_leakage_control_sufficient": True,
        "used_as_model_input": False,
        "frozen_before_gold": True,
        "group_count": 6,
        "app_group_count": 5,
        "popup_template_family_count": 3,
    }
    return receipts, group_attestation


def fixture_bundle() -> tuple[list[dict], list[dict], list[dict], list[dict], dict, dict]:
    items = [adjudicated_item(index) for index in range(1, 7)]
    predictions = [
        frozen_prediction(index, method_id)
        for method_id in METHODS
        for index in range(1, 7)
    ]
    semantics = [
        semantic_row(
            row,
            correct=not (
                row["method_id"] == SEEDED_RANDOM
                and row["pilot_item_id"] == "PMJ-PILOT-001"
            ),
        )
        for row in predictions
    ]
    groups = group_rows()
    receipts, group_attestation = receipt_bundle(predictions, groups)
    return items, predictions, semantics, groups, receipts, group_attestation


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


class FormalK50RunnerTests(unittest.TestCase):
    def runner(self):
        try:
            return importlib.import_module("popup_eval.formal_k50_runner")
        except ModuleNotFoundError as error:
            self.fail(f"formal K50 paired-report runner is missing: {error}")

    def build(self, bundle=None):
        inputs = bundle if bundle is not None else fixture_bundle()
        return self.runner().build_formal_k50_paired_report(*inputs)

    def test_builds_a_report_accepted_by_the_formal_k50_finalizer(self) -> None:
        """Catches an upstream report shape that the formal finalizer cannot consume."""
        bundle = fixture_bundle()

        report = self.build(bundle)
        decision = importlib.import_module(
            "popup_eval.formal_k50"
        ).finalize_formal_k50_confirmation(
            report,
            bundle[1],
            bundle[4],
            bundle[5],
        )

        self.assertEqual(report["status"], "formal_k50_paired_report_ready")
        self.assertEqual(
            report["primary_pair"],
            {"proposed": MG_PU, "reference": SEEDED_RANDOM},
        )
        self.assertEqual(report["paired_item_count"], 6)
        self.assertEqual(report["bootstrap"]["replicates"], 10_000)
        self.assertEqual(report["bootstrap"]["seed"], 20260901)
        for method_id in METHODS:
            self.assertEqual(report["methods"][method_id]["metrics"]["vpma"]["mode"], "adjudicated")
        for metric_name in ("coverage", "critical_hallucination_rate"):
            effect = report["paired_effects"]["metrics"][metric_name]
            self.assertEqual(effect["ci_status"], "available")
            self.assertIsNotNone(effect["point_estimate_difference"])
            self.assertIsNotNone(effect["confidence_interval_95"])
        self.assertEqual(decision["n_items"], 6)
        self.assertEqual(decision["k"], 3)
        self.assertEqual(report["action_policy"], "no_action")
        self.assertFalse(report["recovery_evaluated"])
        self.assertFalse(report["paper_result_eligible"])

    def test_rejects_unresolved_gold(self) -> None:
        """Catches scoring before every gold item has final adjudication."""
        bundle = list(fixture_bundle())
        bundle[0][0]["adjudication_provenance"]["adjudication_status"] = "pending"

        with self.assertRaisesRegex(ValueError, "gold is not fully adjudicated"):
            self.build(tuple(bundle))

    def test_rejects_gold_without_finalized_cap001_capture_binding(self) -> None:
        """Catches archived or hand-labeled rows entering the formal runner."""
        bundle = list(fixture_bundle())
        del bundle[0][0]["adjudication_provenance"]["capture_binding"]

        with self.assertRaisesRegex(ValueError, "CAP-001 capture binding"):
            self.build(tuple(bundle))

    def test_rejects_missing_hallucination_adjudication(self) -> None:
        """Catches silently substituting proxy hallucination for blind human review."""
        bundle = list(fixture_bundle())
        bundle[2] = bundle[2][:-1]

        with self.assertRaisesRegex(ValueError, "semantic adjudication coverage mismatch"):
            self.build(tuple(bundle))

    def test_rejects_prediction_coverage_mismatch(self) -> None:
        """Catches a paired report built from incomplete method predictions."""
        bundle = list(fixture_bundle())
        bundle[1] = bundle[1][:-1]

        with self.assertRaisesRegex(ValueError, "prediction coverage mismatch"):
            self.build(tuple(bundle))

    def test_rejects_frozen_prediction_hash_mismatch(self) -> None:
        """Catches budget receipts bound to a different prediction snapshot."""
        bundle = list(fixture_bundle())
        bundle[4][MG_PU]["frozen_prediction_sha256"] = "0" * 64

        with self.assertRaisesRegex(ValueError, "frozen prediction hash mismatch"):
            self.build(tuple(bundle))

    def test_rejects_action_or_recovery_fields(self) -> None:
        """Catches expansion from message judgment into action or recovery evaluation."""
        for location in ("gold", "prediction"):
            with self.subTest(location=location):
                bundle = list(fixture_bundle())
                if location == "gold":
                    bundle[0][0]["recovery_status"] = "recovered"
                else:
                    bundle[1][0]["target"] = "close_button"
                with self.assertRaisesRegex(ValueError, "action or Recovery field"):
                    self.build(tuple(bundle))

    def test_cli_writes_a_private_noneligible_report(self) -> None:
        """Catches a CLI that omits an input or publishes a formal report by default."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = fixture_bundle()
            items_path = root / "items.jsonl"
            predictions_path = root / "predictions.jsonl"
            semantics_path = root / "semantics.jsonl"
            group_path = root / "groups.jsonl"
            receipts_path = root / "receipts.json"
            group_attestation_path = root / "group-attestation.json"
            output = root / "private" / "formal-k50-report.private.json"
            write_jsonl(items_path, bundle[0])
            write_jsonl(predictions_path, bundle[1])
            write_jsonl(semantics_path, bundle[2])
            write_jsonl(group_path, bundle[3])
            receipts_path.write_text(json.dumps(bundle[4]), encoding="utf-8")
            group_attestation_path.write_text(json.dumps(bundle[5]), encoding="utf-8")
            script = (
                Path(__file__).resolve().parents[1]
                / "popup_eval"
                / "formal_k50_runner.py"
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--adjudicated-items",
                    str(items_path),
                    "--predictions",
                    str(predictions_path),
                    "--semantic-adjudications",
                    str(semantics_path),
                    "--group-map",
                    str(group_path),
                    "--budget-receipts",
                    str(receipts_path),
                    "--group-map-attestation",
                    str(group_attestation_path),
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "formal_k50_paired_report_ready")
            self.assertFalse(report["paper_result_eligible"])
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
