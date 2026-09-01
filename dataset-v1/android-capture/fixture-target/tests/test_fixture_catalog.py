from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


FIXTURE_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = FIXTURE_ROOT / "SCENARIO_CATALOG_V1.json"
VALIDATOR_PATH = FIXTURE_ROOT / "validate_fixture_catalog.py"
BUILD_CONTRACT_PATH = FIXTURE_ROOT / "TARGET_BUILD_CONTRACT_V1.json"
FINALIZER_PATH = FIXTURE_ROOT.parents[0] / "finalize_android_capture.py"


def run_validator(
    catalog_path: Path,
    implementation_contract_path: Path = BUILD_CONTRACT_PATH,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(VALIDATOR_PATH),
            "--catalog",
            str(catalog_path),
            "--implementation-contract",
            str(implementation_contract_path),
            "--summary-json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def load_catalog() -> dict:
    if not CATALOG_PATH.is_file():
        raise AssertionError("fixture scenario catalog must exist")
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def write_catalog(root: Path, catalog: dict) -> Path:
    path = root / "catalog.json"
    path.write_text(json.dumps(catalog), encoding="utf-8")
    return path


class FixtureCatalogContractTest(unittest.TestCase):
    def test_catalog_covers_five_apps_three_templates_and_all_strata(self):
        # Break caught: a catalog-only dry run silently loses required routing coverage.
        result = run_validator(CATALOG_PATH)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {
                "app_group_count": 5,
                "cap001_eligible": False,
                "catalog_id": "PMAB-CONTROLLED-FIXTURE-CATALOG-V1",
                "installation_prerequisites_ready": True,
                "device_capture_validated": False,
                "human_gold_eligible": False,
                "human_privacy_reviews_completed": False,
                "paper_result_eligible": False,
                "real_capture_bundle_count": 0,
                "real_device_accessibility_verified": False,
                "scenario_count": 15,
                "source_group_count": 5,
                "strata": [
                    "boundary_candidate",
                    "no_popup_candidate",
                    "popup_candidate",
                ],
                "target_package_count": 5,
                "target_implementation_status": "android_target_implemented",
                "template_family_count": 3,
            },
        )

    def test_catalog_rejects_any_formal_data_or_human_gold_eligibility(self):
        # Break caught: controlled fixture definitions are promoted into paper evidence.
        catalog = load_catalog()
        for field in ("cap001_eligible", "paper_result_eligible", "human_gold_eligible"):
            mutated = deepcopy(catalog)
            mutated["eligibility"][field] = True
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                result = run_validator(write_catalog(Path(directory), mutated))
                self.assertEqual(result.returncode, 2)
                self.assertIn("must be false", result.stderr)

    def test_catalog_rejects_incomplete_app_group_matrix(self):
        # Break caught: five labels are claimed while fewer than five routable packages exist.
        catalog = load_catalog()
        removed = catalog["source_app_groups"].pop()
        catalog["scenarios"] = [
            scenario
            for scenario in catalog["scenarios"]
            if scenario["source_group_id"] != removed["source_group_id"]
        ]
        with tempfile.TemporaryDirectory() as directory:
            result = run_validator(write_catalog(Path(directory), catalog))

        self.assertEqual(result.returncode, 2)
        self.assertIn("at least 5 source/app groups", result.stderr)

    def test_catalog_requires_real_accessibilityservice_capture_evidence(self):
        # Break caught: a UIAutomator/synthetic tree is accepted as the future capture anchor.
        catalog = load_catalog()
        catalog["required_runtime_evidence"]["collector_mode"] = "uiautomator_dump"
        with tempfile.TemporaryDirectory() as directory:
            result = run_validator(write_catalog(Path(directory), catalog))

        self.assertEqual(result.returncode, 2)
        self.assertIn("AccessibilityService", result.stderr)

    def test_ready_catalog_requires_matching_source_and_build_contract(self):
        # Break caught: readiness is asserted from catalog labels without implementation evidence.
        contract = json.loads(BUILD_CONTRACT_PATH.read_text(encoding="utf-8"))
        contract["application_ids"].pop()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.json"
            path.write_text(json.dumps(contract), encoding="utf-8")
            result = run_validator(CATALOG_PATH, path)

        self.assertEqual(result.returncode, 2)
        self.assertIn("application IDs", result.stderr)

    def test_ready_catalog_rejects_automatic_actions_or_gold_emission(self):
        # Break caught: a fixture silently acts on a popup or emits labels while marked ready.
        contract = json.loads(BUILD_CONTRACT_PATH.read_text(encoding="utf-8"))
        for field in ("automatic_actions", "emits_gold"):
            mutated = deepcopy(contract)
            mutated[field] = True
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "contract.json"
                path.write_text(json.dumps(mutated), encoding="utf-8")
                result = run_validator(CATALOG_PATH, path)
                self.assertEqual(result.returncode, 2)
                self.assertIn("must be false", result.stderr)

    def test_catalog_cannot_claim_device_validation_without_runtime_evidence(self):
        # Break caught: source/build readiness is mislabeled as real-device validation.
        catalog = load_catalog()
        catalog["device_capture_validated"] = True
        with tempfile.TemporaryDirectory() as directory:
            result = run_validator(write_catalog(Path(directory), catalog))

        self.assertEqual(result.returncode, 2)
        self.assertIn("device_capture_validated must be false", result.stderr)

    def test_capture_finalizer_cannot_treat_catalog_as_capture_metadata(self):
        # Break caught: scenario definitions bypass real bundle and human-review gates.
        spec = importlib.util.spec_from_file_location("capture_finalizer", FINALIZER_PATH)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with self.assertRaisesRegex(ValueError, "capture_schema_version"):
            module.finalize_capture(CATALOG_PATH)


if __name__ == "__main__":
    unittest.main()
