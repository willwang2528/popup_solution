#!/usr/bin/env python3
"""Validate catalog-only Android fixture scenarios without creating capture records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any


ALLOWED_STRATA = {
    "popup_candidate": "present",
    "no_popup_candidate": "absent",
    "boundary_candidate": "ambiguous",
}
CONTROLLED_PACKAGE = re.compile(r"org\.pmab\.fixture\.[a-z][a-z0-9_]*\Z")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def object_value(value: Any, name: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{name} must be an object")
    return value


def nonempty_string(value: Any, name: str) -> str:
    require(isinstance(value, str) and bool(value.strip()), f"{name} must be a non-empty string")
    return value


def exact_fields(value: dict[str, Any], expected: set[str], name: str) -> None:
    require(set(value) == expected, f"{name} field set mismatch")


def validate_catalog(
    catalog: dict[str, Any],
    implementation_contract: dict[str, Any],
    source_root: Path,
) -> dict[str, Any]:
    exact_fields(
        catalog,
        {
            "catalog_schema_version",
            "catalog_id",
            "record_kind",
            "purpose",
            "implementation_status",
            "installation_prerequisites_ready",
            "device_capture_validated",
            "verification_status",
            "eligibility",
            "required_runtime_evidence",
            "source_app_groups",
            "template_families",
            "scenarios",
        },
        "catalog",
    )
    require(catalog["catalog_schema_version"] == "1.0.0", "catalog schema must be 1.0.0")
    catalog_id = nonempty_string(catalog["catalog_id"], "catalog_id")
    require(
        catalog["record_kind"] == "controlled_fixture_scenario_catalog",
        "catalog must remain a scenario definition, not a capture record",
    )
    require(catalog["purpose"] == "capture_pipeline_dry_run_only", "catalog purpose mismatch")
    require(
        catalog["implementation_status"] == "android_target_implemented",
        "catalog implementation status must match the Android target",
    )
    require(
        catalog["installation_prerequisites_ready"] is True,
        "installation_prerequisites_ready must be true",
    )
    require(
        catalog["device_capture_validated"] is False,
        "device_capture_validated must be false until runtime evidence is audited",
    )
    verification = object_value(catalog["verification_status"], "verification_status")
    exact_fields(
        verification,
        {
            "real_device_accessibility_verified",
            "real_capture_bundle_count",
            "human_privacy_reviews_completed",
        },
        "verification_status",
    )
    require(
        verification["real_device_accessibility_verified"] is False,
        "real-device accessibility evidence must remain unverified",
    )
    require(
        verification["real_capture_bundle_count"] == 0,
        "real capture bundle count must remain zero",
    )
    require(
        verification["human_privacy_reviews_completed"] is False,
        "human privacy review must remain incomplete",
    )

    eligibility = object_value(catalog["eligibility"], "eligibility")
    exact_fields(
        eligibility,
        {
            "is_capture_record",
            "cap001_eligible",
            "paper_result_eligible",
            "human_gold_eligible",
            "human_gold_count",
        },
        "eligibility",
    )
    for field in (
        "is_capture_record",
        "cap001_eligible",
        "paper_result_eligible",
        "human_gold_eligible",
    ):
        require(eligibility[field] is False, f"eligibility.{field} must be false")
    require(eligibility["human_gold_count"] == 0, "eligibility.human_gold_count must be zero")

    evidence = object_value(catalog["required_runtime_evidence"], "required_runtime_evidence")
    exact_fields(
        evidence,
        {
            "android_api_min",
            "collector_mode",
            "screen_reader_enabled",
            "screenshot",
            "tree_before",
            "tree_after",
            "human_privacy_review",
        },
        "required_runtime_evidence",
    )
    require(
        isinstance(evidence["android_api_min"], int)
        and not isinstance(evidence["android_api_min"], bool)
        and evidence["android_api_min"] >= 30,
        "required Android API must be 30 or newer",
    )
    require(
        evidence["collector_mode"] == "accessibilityservice_node_snapshot",
        "future evidence must be a real AccessibilityService node snapshot",
    )
    for field in (
        "screen_reader_enabled",
        "screenshot",
        "tree_before",
        "tree_after",
        "human_privacy_review",
    ):
        require(evidence[field] is True, f"required_runtime_evidence.{field} must be true")

    raw_groups = catalog["source_app_groups"]
    require(isinstance(raw_groups, list) and len(raw_groups) >= 5, "at least 5 source/app groups are required")
    groups: dict[str, dict[str, str]] = {}
    app_group_ids: set[str] = set()
    packages: set[str] = set()
    for index, raw_group in enumerate(raw_groups):
        group = object_value(raw_group, f"source_app_groups[{index}]")
        exact_fields(
            group,
            {
                "source_group_id",
                "app_group_id",
                "target_package",
                "implementation_status",
            },
            f"source_app_groups[{index}]",
        )
        source_id = nonempty_string(group["source_group_id"], f"source_app_groups[{index}].source_group_id")
        app_id = nonempty_string(group["app_group_id"], f"source_app_groups[{index}].app_group_id")
        package = nonempty_string(group["target_package"], f"source_app_groups[{index}].target_package")
        require(source_id not in groups, "source_group_id values must be unique")
        require(app_id not in app_group_ids, "app_group_id values must be unique")
        require(package not in packages, "target_package values must be unique")
        require(CONTROLLED_PACKAGE.fullmatch(package) is not None, "target packages must use the controlled fixture namespace")
        require(
            group["implementation_status"] == "android_flavor_implemented",
            "source/app group must be implemented as an Android flavor",
        )
        groups[source_id] = {"app_group_id": app_id, "target_package": package}
        app_group_ids.add(app_id)
        packages.add(package)

    raw_families = catalog["template_families"]
    require(isinstance(raw_families, list) and len(raw_families) >= 3, "at least 3 template families are required")
    families: set[str] = set()
    for index, raw_family in enumerate(raw_families):
        family = object_value(raw_family, f"template_families[{index}]")
        exact_fields(
            family,
            {"template_family_id", "ui_primitive", "accessibility_expectation", "implementation_status"},
            f"template_families[{index}]",
        )
        family_id = nonempty_string(family["template_family_id"], f"template_families[{index}].template_family_id")
        require(family_id not in families, "template_family_id values must be unique")
        nonempty_string(family["ui_primitive"], f"template_families[{index}].ui_primitive")
        nonempty_string(
            family["accessibility_expectation"],
            f"template_families[{index}].accessibility_expectation",
        )
        require(
            family["implementation_status"] == "activity_renderer_implemented",
            "template family must be implemented by the Activity renderer",
        )
        families.add(family_id)

    raw_scenarios = catalog["scenarios"]
    require(isinstance(raw_scenarios, list) and bool(raw_scenarios), "scenarios must be a non-empty list")
    scenario_ids: set[str] = set()
    coverage = {source_id: set() for source_id in groups}
    used_families: set[str] = set()
    for index, raw_scenario in enumerate(raw_scenarios):
        scenario = object_value(raw_scenario, f"scenarios[{index}]")
        exact_fields(
            scenario,
            {
                "scenario_id",
                "source_group_id",
                "app_group_id",
                "target_package",
                "template_family_id",
                "intended_stratum",
                "launch",
                "expected_observation",
                "definition_only",
                "formal_data_eligible",
                "human_gold_eligible",
            },
            f"scenarios[{index}]",
        )
        scenario_id = nonempty_string(scenario["scenario_id"], f"scenarios[{index}].scenario_id")
        require(scenario_id not in scenario_ids, "scenario_id values must be unique")
        scenario_ids.add(scenario_id)
        source_id = nonempty_string(scenario["source_group_id"], f"scenarios[{index}].source_group_id")
        require(source_id in groups, "scenario references an unknown source group")
        group = groups[source_id]
        require(scenario["app_group_id"] == group["app_group_id"], "scenario app_group_id mismatch")
        require(scenario["target_package"] == group["target_package"], "scenario target_package mismatch")
        family_id = nonempty_string(scenario["template_family_id"], f"scenarios[{index}].template_family_id")
        require(family_id in families, "scenario references an unknown template family")
        used_families.add(family_id)
        stratum = scenario["intended_stratum"]
        require(stratum in ALLOWED_STRATA, "scenario intended_stratum is invalid")
        require(stratum not in coverage[source_id], "source/app group has a duplicate stratum")
        coverage[source_id].add(stratum)
        require(scenario["definition_only"] is True, "scenario must remain definition_only")
        require(scenario["formal_data_eligible"] is False, "scenario formal_data_eligible must be false")
        require(scenario["human_gold_eligible"] is False, "scenario human_gold_eligible must be false")

        launch = object_value(scenario["launch"], f"scenarios[{index}].launch")
        exact_fields(launch, {"component", "extras"}, f"scenarios[{index}].launch")
        require(
            launch["component"]
            == f"{group['target_package']}/org.pmab.fixture.FixtureActivity",
            "scenario launch component must target its controlled package",
        )
        extras = object_value(launch["extras"], f"scenarios[{index}].launch.extras")
        exact_fields(extras, {"scenario_id"}, f"scenarios[{index}].launch.extras")
        require(extras["scenario_id"] == scenario_id, "scenario launch extra must bind its scenario_id")

        observation = object_value(scenario["expected_observation"], f"scenarios[{index}].expected_observation")
        exact_fields(
            observation,
            {
                "popup_presence",
                "accessibility_profile",
                "real_accessibility_snapshot_required",
                "screenshot_required",
                "screen_reader_required",
            },
            f"scenarios[{index}].expected_observation",
        )
        require(observation["popup_presence"] == ALLOWED_STRATA[stratum], "popup presence does not match stratum")
        nonempty_string(observation["accessibility_profile"], f"scenarios[{index}].accessibility_profile")
        for field in (
            "real_accessibility_snapshot_required",
            "screenshot_required",
            "screen_reader_required",
        ):
            require(observation[field] is True, f"scenarios[{index}].{field} must be true")

    for source_id, strata in coverage.items():
        require(strata == set(ALLOWED_STRATA), f"source/app group {source_id} must cover all three strata")
    require(used_families == families, "every template family must be used by at least one scenario")

    contract = object_value(implementation_contract, "implementation contract")
    exact_fields(
        contract,
        {
            "contract_schema_version",
            "gradle_project_path",
            "activity_class",
            "scenario_router_class",
            "flavor_dimension",
            "source_slugs",
            "application_ids",
            "template_families",
            "strata",
            "min_sdk",
            "target_sdk",
            "automatic_actions",
            "emits_gold",
            "requires_real_accessibility_validation",
            "source_files",
        },
        "implementation contract",
    )
    require(contract["contract_schema_version"] == "1.0.0", "implementation contract schema mismatch")
    require(contract["gradle_project_path"] == ":fixtureTarget", "Gradle project path mismatch")
    require(contract["activity_class"] == "org.pmab.fixture.FixtureActivity", "Activity class mismatch")
    require(
        contract["scenario_router_class"] == "org.pmab.fixture.core.ScenarioRouter",
        "scenario router class mismatch",
    )
    require(contract["flavor_dimension"] == "sourceApp", "flavor dimension mismatch")
    expected_slugs = {package.rsplit(".", 1)[-1] for package in packages}
    require(
        isinstance(contract["source_slugs"], list)
        and set(contract["source_slugs"]) == expected_slugs
        and len(contract["source_slugs"]) == len(expected_slugs),
        "implementation source slugs do not match source/app groups",
    )
    require(
        isinstance(contract["application_ids"], list)
        and set(contract["application_ids"]) == packages
        and len(contract["application_ids"]) == len(packages),
        "implementation application IDs do not match the catalog",
    )
    require(
        isinstance(contract["template_families"], list)
        and set(contract["template_families"]) == families
        and len(contract["template_families"]) == len(families),
        "implementation template families do not match the catalog",
    )
    require(
        isinstance(contract["strata"], list)
        and set(contract["strata"]) == set(ALLOWED_STRATA)
        and len(contract["strata"]) == len(ALLOWED_STRATA),
        "implementation strata do not match the catalog",
    )
    require(contract["min_sdk"] >= 30, "implementation min SDK must be at least 30")
    require(contract["target_sdk"] == 35, "implementation target SDK must be 35")
    require(contract["automatic_actions"] is False, "implementation automatic_actions must be false")
    require(contract["emits_gold"] is False, "implementation emits_gold must be false")
    require(
        contract["requires_real_accessibility_validation"] is True,
        "implementation must retain the real-device accessibility validation gate",
    )
    source_files = contract["source_files"]
    require(isinstance(source_files, list) and bool(source_files), "implementation source_files must be non-empty")
    resolved_root = source_root.resolve()
    for index, raw_path in enumerate(source_files):
        relative = Path(nonempty_string(raw_path, f"implementation source_files[{index}]"))
        require(not relative.is_absolute() and ".." not in relative.parts, "implementation source path must be relative")
        resolved = (resolved_root / relative).resolve()
        require(resolved_root in resolved.parents, "implementation source path escapes target root")
        require(resolved.is_file() and not resolved.is_symlink(), f"implementation source file missing: {relative}")

    return {
        "app_group_count": len(app_group_ids),
        "cap001_eligible": False,
        "catalog_id": catalog_id,
        "installation_prerequisites_ready": True,
        "device_capture_validated": False,
        "human_gold_eligible": False,
        "human_privacy_reviews_completed": False,
        "paper_result_eligible": False,
        "real_capture_bundle_count": 0,
        "real_device_accessibility_verified": False,
        "scenario_count": len(raw_scenarios),
        "source_group_count": len(groups),
        "strata": sorted(ALLOWED_STRATA),
        "target_package_count": len(packages),
        "target_implementation_status": "android_target_implemented",
        "template_family_count": len(families),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the catalog-only Android fixture matrix")
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--implementation-contract", required=True, type=Path)
    parser.add_argument("--summary-json", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        catalog = json.loads(arguments.catalog.read_text(encoding="utf-8"))
        implementation_contract = json.loads(
            arguments.implementation_contract.read_text(encoding="utf-8")
        )
        summary = validate_catalog(
            object_value(catalog, "catalog"),
            object_value(implementation_contract, "implementation contract"),
            Path(__file__).resolve().parent,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        parser.exit(2, f"fixture catalog validation failed: {error}\n")
    if arguments.summary_json:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    else:
        print("fixture catalog valid; definitions remain non-empirical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
