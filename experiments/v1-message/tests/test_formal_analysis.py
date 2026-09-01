from __future__ import annotations

from copy import deepcopy
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


def canonical_json(value) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def registry() -> dict:
    return {
        "contract_version": "popup-message-analysis-registry-v1.0",
        "frozen_before_gold": True,
        "primary_endpoint": "vpma_overall_success_rate",
        "secondary_alpha": 0.05,
        "secondary_comparisons": [
            {
                "comparison_id": comparison_id,
                "proposed_method_id": "mg-pu-k50-v1",
                "reference_method_id": reference,
                "proposed_operating_point": "K50",
                "reference_operating_point": operating_point,
            }
            for comparison_id, reference, operating_point in (
                ("s1", "structure-only-v1", "natural"),
                ("s2", "vision-only-v1", "K50"),
                ("s3", "c1-always-on-fusion-v1", "natural"),
            )
        ],
        "subgroup_fdr_q": 0.10,
        "subgroup_tests": [
            {"subgroup_test_id": "g1", "dimension": "gap_tier", "level": "visual_only"},
            {"subgroup_test_id": "g2", "dimension": "popup_type", "level": "modal"},
            {"subgroup_test_id": "g3", "dimension": "message_complexity", "level": "high"},
            {"subgroup_test_id": "g4", "dimension": "gap_tier", "level": "merged"},
        ],
        "subgroup_dimensions": ["gap_tier", "popup_type", "message_complexity"],
        "minimum_inference_groups": 5,
        "pareto_points": [
            {"point_id": "p-a", "method_id": "method-a", "operating_point": "K50"},
            {"point_id": "p-b", "method_id": "method-b", "operating_point": "K100"},
            {"point_id": "p-c", "method_id": "method-c", "operating_point": "K50"},
            {"point_id": "p-d", "method_id": "method-d", "operating_point": "K25"},
        ],
        "pareto_quality_metric": "vpma_overall_success_rate",
        "pareto_coverage_metric": "coverage",
        "pareto_cost_axes": [
            "visual_calls",
            "decoded_pixels",
            "monetary_cost_microunits",
        ],
    }


def formal_k50_result() -> dict:
    return {
        "formal_contract_version": "popup-message-formal-k50-v1.0",
        "decision": "continue",
        "primary_endpoint": {
            "name": "vpma_overall_success_rate",
            "vpma_difference": 0.03,
            "confidence_interval_95": {"lower": 0.01, "upper": 0.05},
        },
        "action_policy": "no_action",
        "recovery_evaluated": False,
        "paper_result_eligible": False,
    }


def secondary_rows() -> list[dict]:
    return [
        {
            "comparison_id": comparison_id,
            "proposed_method_id": "mg-pu-k50-v1",
            "reference_method_id": reference_method_id,
            "proposed_operating_point": "K50",
            "reference_operating_point": reference_operating_point,
            "metric_name": "vpma_overall_success_rate",
            "direction": "proposed_minus_reference",
            "raw_p_value": p_value,
            "effect": effect,
            "confidence_interval_95": {"lower": effect - 0.01, "upper": effect + 0.01},
            "group_count": 6,
        }
        for comparison_id, reference_method_id, reference_operating_point, p_value, effect in (
            ("s1", "structure-only-v1", "natural", 0.01, 0.04),
            ("s2", "vision-only-v1", "K50", 0.03, 0.02),
            ("s3", "c1-always-on-fusion-v1", "natural", 0.04, 0.01),
        )
    ]


def subgroup_rows() -> list[dict]:
    return [
        {
            "subgroup_test_id": test_id,
            "dimension": dimension,
            "level": level,
            "metric_name": "vpma_overall_success_rate",
            "direction": "proposed_minus_reference",
            "raw_p_value": p_value,
            "effect": effect,
            "confidence_interval_95": {"lower": effect - 0.02, "upper": effect + 0.02},
            "group_count": 6,
            "exploratory": True,
        }
        for test_id, dimension, level, p_value, effect in (
            ("g1", "gap_tier", "visual_only", 0.01, 0.05),
            ("g2", "popup_type", "modal", 0.04, 0.03),
            ("g3", "message_complexity", "high", 0.20, 0.01),
            ("g4", "gap_tier", "merged", 0.50, -0.01),
        )
    ]


def pareto_rows() -> list[dict]:
    return [
        {
            "point_id": point_id,
            "method_id": method_id,
            "operating_point": operating_point,
            "vpma_overall_success_rate": vpma,
            "coverage": coverage,
            "actual_budget": {
                "visual_calls": calls,
                "decoded_pixels": calls * 1000,
                "monetary_cost_microunits": calls * 100,
            },
        }
        for point_id, method_id, operating_point, vpma, coverage, calls in (
            ("p-a", "method-a", "K50", 0.80, 0.80, 10),
            ("p-b", "method-b", "K100", 0.82, 0.80, 11),
            ("p-c", "method-c", "K50", 0.79, 0.75, 12),
            ("p-d", "method-d", "K25", 0.80, 0.85, 9),
        )
    ]


def bundle() -> dict:
    frozen_registry = registry()
    return {
        "registry": frozen_registry,
        "registry_sha256": hashlib.sha256(canonical_json(frozen_registry)).hexdigest(),
        "formal_k50_result": formal_k50_result(),
        "secondary_rows": secondary_rows(),
        "subgroup_rows": subgroup_rows(),
        "pareto_rows": pareto_rows(),
    }


class FormalAnalysisTests(unittest.TestCase):
    def module(self):
        try:
            return importlib.import_module("popup_eval.formal_analysis")
        except ModuleNotFoundError as error:
            self.fail(f"formal analysis module is missing: {error}")

    def finalize(self, values: dict | None = None):
        data = values or bundle()
        return self.module().finalize_formal_analysis(
            analysis_registry=data["registry"],
            expected_registry_sha256=data["registry_sha256"],
            formal_k50_result=data["formal_k50_result"],
            secondary_results=data["secondary_rows"],
            subgroup_results=data["subgroup_rows"],
            pareto_points=data["pareto_rows"],
        )

    def test_committed_registry_freezes_named_families_before_gold(self):
        path = Path(__file__).resolve().parents[1] / "FORMAL_ANALYSIS_REGISTRY_V1.json"
        frozen = json.loads(path.read_text(encoding="utf-8"))
        digest = hashlib.sha256(canonical_json(frozen)).hexdigest()

        validated = self.module()._validate_registry(frozen, digest)
        self.assertEqual(len(validated["secondary_ids"]), 5)
        self.assertEqual(len(validated["subgroup_ids"]), 10)
        self.assertEqual(len(validated["pareto_ids"]), 18)
        self.assertIn("mgpu-k50_vs_c1-always-on-natural", validated["secondary_ids"])
        self.assertIn("c1-always-on-natural", validated["pareto_ids"])
        self.assertIn("seeded-random-k50", validated["pareto_ids"])

    def test_applies_holm_and_bh_with_frozen_exact_coverage(self):
        result = self.finalize()

        holm = {row["comparison_id"]: row for row in result["secondary_holm"]}
        self.assertAlmostEqual(holm["s1"]["adjusted_p_value"], 0.03)
        self.assertAlmostEqual(holm["s2"]["adjusted_p_value"], 0.06)
        self.assertAlmostEqual(holm["s3"]["adjusted_p_value"], 0.06)
        self.assertTrue(holm["s1"]["reject_at_alpha_0_05"])
        self.assertTrue(holm["s1"]["unadjusted_ci_excludes_zero_in_effect_direction"])
        self.assertTrue(holm["s1"]["secondary_claim_gate_passed"])
        self.assertEqual(
            holm["s1"]["ci_adjustment_status"],
            "unadjusted_per_comparison_cluster_bootstrap_95ci",
        )
        self.assertFalse(holm["s2"]["reject_at_alpha_0_05"])
        self.assertFalse(holm["s2"]["secondary_claim_gate_passed"])

        bh = {row["subgroup_test_id"]: row for row in result["subgroup_bh_fdr"]}
        self.assertAlmostEqual(bh["g1"]["adjusted_p_value"], 0.04)
        self.assertAlmostEqual(bh["g2"]["adjusted_p_value"], 0.08)
        self.assertAlmostEqual(bh["g3"]["adjusted_p_value"], 0.26666666666666666)
        self.assertAlmostEqual(bh["g4"]["adjusted_p_value"], 0.5)
        self.assertTrue(bh["g1"]["discovery_at_q_0_10"])
        self.assertTrue(bh["g2"]["discovery_at_q_0_10"])
        self.assertFalse(bh["g3"]["discovery_at_q_0_10"])
        self.assertTrue(all(row["exploratory"] for row in bh.values()))

    def test_emits_pareto_frontier_for_each_frozen_cost_axis(self):
        result = self.finalize()

        for axis in registry()["pareto_cost_axes"]:
            frontier = result["pareto_frontiers"][axis]
            self.assertEqual(frontier["frontier_point_ids"], ["p-b", "p-d"])
            self.assertEqual(frontier["dominated_point_ids"], ["p-a", "p-c"])
            self.assertEqual(frontier["objectives"], {
                "maximize": ["vpma_overall_success_rate", "coverage"],
                "minimize": [axis],
            })

    def test_rejects_post_hoc_missing_duplicate_or_unknown_hypotheses(self):
        for key, rows_key, id_key in (
            ("secondary_comparisons", "secondary_rows", "comparison_id"),
            ("subgroup_tests", "subgroup_rows", "subgroup_test_id"),
            ("pareto_points", "pareto_rows", "point_id"),
        ):
            with self.subTest(kind=key):
                missing = bundle()
                missing[rows_key] = missing[rows_key][:-1]
                with self.assertRaisesRegex(ValueError, "coverage mismatch"):
                    self.finalize(missing)

                duplicate = bundle()
                duplicate[rows_key][-1][id_key] = duplicate[rows_key][0][id_key]
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    self.finalize(duplicate)

    def test_rejects_registry_drift_scope_creep_and_invalid_inference(self):
        drift = bundle()
        drift["registry"]["secondary_alpha"] = 0.10
        with self.assertRaisesRegex(ValueError, "registry hash mismatch"):
            self.finalize(drift)

        action = bundle()
        action["secondary_rows"][0]["action"] = "dismiss"
        with self.assertRaisesRegex(ValueError, "Action or Recovery"):
            self.finalize(action)

        low_groups = bundle()
        low_groups["secondary_rows"][0]["group_count"] = 4
        low_groups["secondary_rows"][0]["raw_p_value"] = None
        descriptive = self.finalize(low_groups)
        low_group_row = next(
            row for row in descriptive["secondary_holm"]
            if row["comparison_id"] == "s1"
        )
        self.assertEqual(
            low_group_row["inference_status"],
            "descriptive_only_insufficient_groups",
        )
        self.assertIsNone(low_group_row["raw_p_value"])
        self.assertEqual(low_group_row["adjusted_p_value"], 1.0)
        self.assertFalse(low_group_row["reject_at_alpha_0_05"])

        invalid_low_groups = bundle()
        invalid_low_groups["secondary_rows"][0]["group_count"] = 4
        with self.assertRaisesRegex(ValueError, "raw_p_value must be null"):
            self.finalize(invalid_low_groups)

        subgroup_dimension = bundle()
        subgroup_dimension["subgroup_rows"][0]["dimension"] = "post_hoc_slice"
        with self.assertRaisesRegex(ValueError, "subgroup dimension"):
            self.finalize(subgroup_dimension)

        method_swap = bundle()
        method_swap["secondary_rows"][0]["reference_method_id"] = "another-method"
        with self.assertRaisesRegex(ValueError, "method binding mismatch"):
            self.finalize(method_swap)

    def test_receipt_is_hash_bound_private_and_never_paper_eligible(self):
        result = self.finalize()

        self.assertEqual(result["status"], "formal_supplementary_analysis_ready")
        self.assertEqual(result["primary_decision"], "continue")
        self.assertFalse(result["superiority_claim_authorized"])
        self.assertFalse(result["paper_result_eligible"])
        self.assertEqual(result["action_policy"], "no_action")
        self.assertFalse(result["recovery_evaluated"])
        for key in (
            "analysis_registry_sha256",
            "formal_k50_result_sha256",
            "secondary_results_sha256",
            "subgroup_results_sha256",
            "pareto_points_sha256",
        ):
            self.assertRegex(result["hashes"][key], r"^[0-9a-f]{64}$")


class FormalAnalysisCliTests(unittest.TestCase):
    def test_cli_writes_private_0600_no_overwrite_receipt(self):
        data = bundle()
        with tempfile.TemporaryDirectory() as directory:
            private = Path(directory) / "private"
            private.mkdir()
            paths = {
                "registry": private / "registry.private.json",
                "k50": private / "k50.private.json",
                "secondary": private / "secondary.private.jsonl",
                "subgroups": private / "subgroups.private.jsonl",
                "pareto": private / "pareto.private.jsonl",
            }
            paths["registry"].write_text(json.dumps(data["registry"]), encoding="utf-8")
            paths["k50"].write_text(json.dumps(data["formal_k50_result"]), encoding="utf-8")
            for key, rows in (
                ("secondary", data["secondary_rows"]),
                ("subgroups", data["subgroup_rows"]),
                ("pareto", data["pareto_rows"]),
            ):
                paths[key].write_text(
                    "".join(json.dumps(row) + "\n" for row in rows),
                    encoding="utf-8",
                )
            output = private / "formal-analysis.private.json"
            script = (
                Path(__file__).resolve().parents[1]
                / "popup_eval"
                / "formal_analysis.py"
            )
            command = [
                sys.executable,
                str(script),
                "--analysis-registry",
                str(paths["registry"]),
                "--expected-registry-sha256",
                data["registry_sha256"],
                "--formal-k50-result",
                str(paths["k50"]),
                "--secondary-results",
                str(paths["secondary"]),
                "--subgroup-results",
                str(paths["subgroups"]),
                "--pareto-points",
                str(paths["pareto"]),
                "--output",
                str(output),
            ]

            first = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(stat.S_IMODE(private.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)

            second = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(second.returncode, 2)
            self.assertIn("already exists", second.stderr)


if __name__ == "__main__":
    unittest.main()
