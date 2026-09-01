from __future__ import annotations

import copy
import importlib
from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


MG_PU = "mg-pu-k50-v1"
SEEDED_RANDOM = "seeded-random-k50-v1"
ITEM_SET_SHA256 = "3b90fdbae9c70edbc6ee3859e58f17400d9c45a1e78ac38a3eca9f3e56f793cf"
MG_PU_SELECTION_SHA256 = "2408580c580c3891127268c50b844633d66f3194cc5c83328258a6eee3c77735"
RANDOM_SELECTION_SHA256 = "3993096b62920dbf697f533a5fdd877f0e4c07bae84e9df709b639202e4a8ea9"


def effect(point: float, lower: float, upper: float) -> dict:
    return {
        "point_estimate_difference": point,
        "confidence_interval_95": {"lower": lower, "upper": upper},
        "ci_status": "available",
    }


def paired_report() -> dict:
    method_summary = {
        "adjudication_batch_sha256": "b" * 64,
        "metric_item_set_sha256": ITEM_SET_SHA256,
        "evaluated_item_count": 6,
        "metrics": {"vpma": {"mode": "adjudicated"}},
    }
    return {
        "comparison_contract_version": "popup-message-paired-comparison-v1.0",
        "action_policy": "no_action",
        "method_ids": [MG_PU, SEEDED_RANDOM],
        "proposed_method_id": MG_PU,
        "strongest_baseline_method_id": SEEDED_RANDOM,
        "paired_item_count": 6,
        "metric_item_set_sha256": ITEM_SET_SHA256,
        "adjudication_batch_sha256": "b" * 64,
        "group_map_sha256": "c" * 64,
        "methods": {
            MG_PU: copy.deepcopy(method_summary),
            SEEDED_RANDOM: copy.deepcopy(method_summary),
        },
        "paired_effects": {
            "direction": "proposed_minus_reference",
            "bootstrap_unit": "group",
            "shared_draws_across_methods": True,
            "metrics": {
                "vpma_overall_success_rate": effect(0.05, 0.01, 0.09),
                "coverage": effect(0.0, 0.0, 0.0),
                "critical_hallucination_rate": effect(0.0, 0.0, 0.0),
            },
        },
        "bootstrap": {
            "unit": "group",
            "group_count": 5,
            "replicates": 10_000,
            "seed": 20260901,
        },
    }


def predictions() -> list[dict]:
    rows = []
    for method_id, selected_indexes in (
        (MG_PU, {1, 2, 3}),
        (SEEDED_RANDOM, {4, 5, 6}),
    ):
        for index in range(1, 7):
            rows.append(
                {
                    "method_id": method_id,
                    "pilot_item_id": f"PMJ-PILOT-{index:03d}",
                    "visual_called": index in selected_indexes,
                    "human_gold_used": False,
                    "scored": False,
                    "paper_result_eligible": False,
                    "action_policy": "no_action",
                }
            )
    return rows


def attestations() -> dict:
    common = {
        "metric_item_set_sha256": ITEM_SET_SHA256,
        "adjudication_batch_sha256": "b" * 64,
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
    return {
        MG_PU: {
            **copy.deepcopy(common),
            "selected_item_set_sha256": MG_PU_SELECTION_SHA256,
        },
        SEEDED_RANDOM: {
            **copy.deepcopy(common),
            "selected_item_set_sha256": RANDOM_SELECTION_SHA256,
        },
    }


def formal_group_map() -> dict:
    return {
        "group_map_sha256": "c" * 64,
        "formal_leakage_control_sufficient": True,
        "used_as_model_input": False,
        "frozen_before_gold": True,
        "group_count": 5,
        "app_group_count": 5,
        "popup_template_family_count": 3,
    }


class FormalK50Tests(unittest.TestCase):
    def scorer(self):
        return importlib.import_module("popup_eval.formal_k50")

    def assert_rejected(
        self,
        report: dict | None = None,
        rows: list[dict] | None = None,
        method_evidence: dict | None = None,
        group_evidence: dict | None = None,
    ) -> None:
        formal_k50 = self.scorer()
        with self.assertRaises(formal_k50.FormalK50Error):
            formal_k50.finalize_formal_k50_confirmation(
                report if report is not None else paired_report(),
                rows if rows is not None else predictions(),
                method_evidence if method_evidence is not None else attestations(),
                group_evidence if group_evidence is not None else formal_group_map(),
            )

    def test_valid_formal_pair_continues_superiority(self):
        try:
            formal_k50 = self.scorer()
        except ModuleNotFoundError as exc:
            self.fail(f"formal K50 scorer is missing: {exc}")

        result = formal_k50.finalize_formal_k50_confirmation(
            paired_report(), predictions(), attestations(), formal_group_map()
        )

        self.assertEqual(
            result["primary_pair"],
            {"proposed": MG_PU, "reference": SEEDED_RANDOM},
        )
        self.assertEqual(result["n_items"], 6)
        self.assertEqual(result["k"], 3)
        self.assertEqual(result["primary_endpoint"]["vpma_difference"], 0.05)
        self.assertEqual(
            result["primary_endpoint"]["confidence_interval_95"],
            {"lower": 0.01, "upper": 0.09},
        )
        self.assertEqual(
            result["paired_cluster_bootstrap"],
            {"unit": "group", "group_count": 5, "replicates": 10_000, "seed": 20260901},
        )
        self.assertTrue(result["gates"]["vpma_at_least_plus_2pp"])
        self.assertTrue(result["gates"]["vpma_ci_above_zero"])
        self.assertTrue(result["gates"]["coverage_non_worsening"])
        self.assertTrue(result["gates"]["hallucination_non_worsening"])
        self.assertTrue(result["gates"]["budget_equality"])
        self.assertTrue(result["gates"]["actual_budget_non_worsening"])
        self.assertEqual(
            result["selection_relationship"],
            {
                "same_selected_item_set": False,
                "overlap_count": 0,
                "overlap_fraction_of_k": 0.0,
                "comparison_interpretation": "budget_matched_not_item_matched",
                "caveat": (
                    "equal visual budget does not control which items receive visual evidence"
                ),
            },
        )
        self.assertEqual(result["decision"], "continue")
        self.assertEqual(
            result["blockers"],
            [
                "formal_supplementary_analysis_receipt_pending",
            ],
        )
        self.assertEqual(result["action_policy"], "no_action")
        self.assertFalse(result["recovery_evaluated"])
        self.assertFalse(result["paper_result_eligible"])

    def test_rejects_any_frozen_hash_mismatch(self):
        for field in (
            "metric_item_set_sha256",
            "adjudication_batch_sha256",
            "visual_bank_sha256",
            "visual_config_sha256",
            "budget_spec_sha256",
        ):
            with self.subTest(field=field):
                evidence = attestations()
                evidence[SEEDED_RANDOM][field] = "0" * 64
                self.assert_rejected(method_evidence=evidence)

    def test_rejects_proxy_vpma_or_invalid_bootstrap_contract(self):
        report = paired_report()
        report["methods"][MG_PU]["metrics"]["vpma"]["mode"] = "proxy"
        self.assert_rejected(report=report)

        report = paired_report()
        report["paired_effects"]["shared_draws_across_methods"] = False
        self.assert_rejected(report=report)

        report = paired_report()
        report["bootstrap"]["replicates"] = 9_999
        self.assert_rejected(report=report)

    def test_rejects_insufficient_or_mismatched_formal_group_map(self):
        for field, value in (
            ("formal_leakage_control_sufficient", False),
            ("used_as_model_input", True),
            ("frozen_before_gold", False),
            ("group_count", 4),
            ("app_group_count", 4),
            ("popup_template_family_count", 2),
            ("group_map_sha256", "0" * 64),
        ):
            with self.subTest(field=field):
                evidence = formal_group_map()
                evidence[field] = value
                self.assert_rejected(group_evidence=evidence)

    def test_rejects_predictions_that_are_not_safe_frozen_pregold_rows(self):
        for field, value in (
            ("human_gold_used", True),
            ("scored", True),
            ("paper_result_eligible", True),
            ("action_policy", "dismiss"),
            ("visual_called", 1),
        ):
            with self.subTest(field=field):
                rows = predictions()
                rows[0][field] = value
                self.assert_rejected(rows=rows)

    def test_rejects_undefined_non_worsening_denominator(self):
        report = paired_report()
        metric = report["paired_effects"]["metrics"]["critical_hallucination_rate"]
        metric["point_estimate_difference"] = None
        metric["confidence_interval_95"] = None
        metric["ci_status"] = "unavailable_zero_denominator"
        self.assert_rejected(report=report)

    def test_requires_actual_budget_ledger_and_withdraws_on_cost_worsening(self):
        evidence = attestations()
        del evidence[MG_PU]["actual_budget"]["decoded_pixels"]
        self.assert_rejected(method_evidence=evidence)

        evidence = attestations()
        evidence[MG_PU]["actual_budget"]["monetary_cost_microunits"] = 10001
        result = self.scorer().finalize_formal_k50_confirmation(
            paired_report(), predictions(), evidence, formal_group_map()
        )
        self.assertFalse(result["gates"]["actual_budget_non_worsening"])
        self.assertEqual(result["decision"], "withdraw_superiority")

    def test_malformed_nested_evidence_uses_the_formal_contract_error(self):
        report = paired_report()
        report["methods"][MG_PU]["metrics"] = []
        self.assert_rejected(report=report)

        evidence = attestations()
        evidence[MG_PU] = "not-an-attestation"
        self.assert_rejected(method_evidence=evidence)

    def test_rejects_wrong_pair_or_non_k50_operating_point(self):
        report = paired_report()
        report["method_ids"] = ["mg-pu-gated-union-v1", SEEDED_RANDOM]
        self.assert_rejected(report=report)

        evidence = attestations()
        evidence[MG_PU]["operating_point"] = "K25"
        self.assert_rejected(method_evidence=evidence)

    def test_k_is_ceiling_half_n_and_selected_count_is_exact(self):
        five_item_hash = "85eb18bfcba5e14836c0b4168c72fefaeae046ae48cc3b87246a5fa24a4fd91d"
        report = paired_report()
        report["paired_item_count"] = 5
        report["metric_item_set_sha256"] = five_item_hash
        for method_id in (MG_PU, SEEDED_RANDOM):
            report["methods"][method_id]["evaluated_item_count"] = 5
            report["methods"][method_id]["metric_item_set_sha256"] = five_item_hash

        rows = [row for row in predictions() if row["pilot_item_id"] != "PMJ-PILOT-006"]
        random_third = next(
            row
            for row in rows
            if row["method_id"] == SEEDED_RANDOM and row["pilot_item_id"] == "PMJ-PILOT-003"
        )
        random_third["visual_called"] = True
        evidence = attestations()
        evidence[MG_PU]["metric_item_set_sha256"] = five_item_hash
        evidence[SEEDED_RANDOM]["metric_item_set_sha256"] = five_item_hash
        evidence[SEEDED_RANDOM]["selected_item_set_sha256"] = (
            "283d07ba482991be4e68e1d1bbca44e586de91233b899d749534f06a12923962"
        )

        result = self.scorer().finalize_formal_k50_confirmation(
            report, rows, evidence, formal_group_map()
        )
        self.assertEqual(result["n_items"], 5)
        self.assertEqual(result["k"], 3)

        rows[0]["visual_called"] = False
        self.assert_rejected(
            report=report,
            rows=rows,
            method_evidence=evidence,
        )

    def test_each_failed_superiority_gate_withdraws_claim(self):
        cases = (
            (
                "vpma_at_least_plus_2pp",
                "vpma_overall_success_rate",
                effect(0.019, 0.001, 0.04),
            ),
            (
                "vpma_ci_above_zero",
                "vpma_overall_success_rate",
                effect(0.05, 0.0, 0.09),
            ),
            ("coverage_non_worsening", "coverage", effect(-0.01, -0.02, 0.0)),
            (
                "hallucination_non_worsening",
                "critical_hallucination_rate",
                effect(0.01, 0.0, 0.02),
            ),
        )
        formal_k50 = self.scorer()
        for gate, metric_name, failed_effect in cases:
            with self.subTest(gate=gate):
                report = paired_report()
                report["paired_effects"]["metrics"][metric_name] = failed_effect
                result = formal_k50.finalize_formal_k50_confirmation(
                    report, predictions(), attestations(), formal_group_map()
                )
                self.assertFalse(result["gates"][gate])
                self.assertEqual(result["decision"], "withdraw_superiority")


if __name__ == "__main__":
    unittest.main()
