#!/usr/bin/env python3
"""Dependency-free validator for Popup Episode Union Dataset v1.

The validator checks the JSON Schema subset used by this project and the
cross-field item/dataset invariants that JSON Schema alone cannot express.
Collector-supplied `quality` booleans are never accepted as proof.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable, Iterator


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data" / "items.schema-fixture.jsonl"
SCHEMA_PATH = ROOT / "schema" / "item.schema.json"
CROSSWALK_PATH = ROOT / "schema" / "source_to_item_crosswalk.json"
FIELD_CATALOG_PATH = ROOT / "schema" / "field_catalog.json"
QA_RULES_PATH = ROOT / "schema" / "qa_rules.json"
QA_COVERAGE_PATH = ROOT / "schema" / "qa_implementation_coverage.json"
RESULT_PATH = ROOT / "validation-result.json"

EXPECTED_PAPERS = {
    "whispertest_2025",
    "abandon_all_hope_2024",
    "the_ok_is_not_enough_2023",
    "freely_given_consent_2022",
    "vlm_fuzz_2026",
    "tcf_aaid_2026",
    "cookieverse_bannerclick",
    "ssldetecter_2019",
    "poker_sneaky_popups",
    "popsweeper_2024",
    "dynamic_ios_privacy_2021",
    "hotmobile_ad_policy_2018",
    "ios_applications_testing_2018",
    "dios_2014"
}

PRESENT_CODES = {"observed", "derived", "annotated"}
ABSENT_CODES = {
    "not_available",
    "not_applicable",
    "not_observable",
    "collection_failed",
    "redacted",
    "unknown"
}
ALL_PRESENCE_CODES = PRESENT_CODES | ABSENT_CODES
LOW_RISK_ACTIONS = {
    "close",
    "cancel",
    "later",
    "skip",
    "acknowledge",
    "verified_back",
    "verified_outside_tap"
}


class DuplicateKeyError(ValueError):
    pass


def strict_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_object_pairs)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    items = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line, object_pairs_hook=strict_object_pairs)
        except Exception as exc:  # noqa: BLE001 - preserve exact parse context
            raise ValueError(f"{path}:{line_number}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: item must be an object")
        items.append(value)
    return items


def resolve_ref(schema_root: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported non-local schema reference: {ref}")
    current: Any = schema_root
    for token in ref[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        current = current[token]
    if not isinstance(current, dict):
        raise ValueError(f"schema reference does not resolve to an object: {ref}")
    return current


def instance_type_matches(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    return True


def validate_schema(value: Any, schema: dict[str, Any], root: dict[str, Any], path: str = "$") -> list[str]:
    if "$ref" in schema:
        return validate_schema(value, resolve_ref(root, schema["$ref"]), root, path)

    if "oneOf" in schema:
        branch_errors = [validate_schema(value, branch, root, path) for branch in schema["oneOf"]]
        matching = sum(1 for errors in branch_errors if not errors)
        if matching != 1:
            return [f"{path}: expected exactly one oneOf branch, matched {matching}"]
        return []

    errors: list[str] = []
    expected_type = schema.get("type")
    if expected_type is not None:
        allowed = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(instance_type_matches(value, item) for item in allowed):
            return [f"{path}: expected type {allowed}, got {type(value).__name__}"]

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}, got {value!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} is not in enum")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: string shorter than minLength")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            errors.append(f"{path}: string does not match {schema['pattern']}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: number is below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: number is above maximum")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: array shorter than minItems")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: array longer than maxItems")
        if schema.get("uniqueItems"):
            serialized = [json.dumps(item, sort_keys=True, ensure_ascii=False) for item in value]
            if len(serialized) != len(set(serialized)):
                errors.append(f"{path}: array items are not unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(validate_schema(item, item_schema, root, f"{path}[{index}]"))

    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required property {key!r}")
        properties = schema.get("properties", {})
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in properties:
                errors.extend(validate_schema(child, properties[key], root, child_path))
            else:
                additional = schema.get("additionalProperties", True)
                if additional is False:
                    errors.append(f"{path}: unexpected property {key!r}")
                elif isinstance(additional, dict):
                    errors.extend(validate_schema(child, additional, root, child_path))
    return errors


def schema_pointer_exists(schema_root: dict[str, Any], pointer: str) -> bool:
    if not pointer.startswith("/"):
        return False
    current: dict[str, Any] = schema_root
    for raw_part in pointer[1:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        while "$ref" in current:
            current = resolve_ref(schema_root, current["$ref"])
        if part == "*":
            item_schema = current.get("items")
            if not isinstance(item_schema, dict):
                return False
            current = item_schema
            continue
        properties = current.get("properties")
        if not isinstance(properties, dict) or part not in properties:
            return False
        current = properties[part]
    return True


def pointer_escape(part: str) -> str:
    return part.replace("~", "~0").replace("/", "~1")


def iter_leaves(value: Any, prefix: str = "") -> Iterator[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"presence", "field_provenance", "field_status", "measurement_channel"}:
                continue
            path = f"{prefix}/{pointer_escape(str(key))}"
            if isinstance(child, dict) and child:
                yield from iter_leaves(child, path)
            elif isinstance(child, list) and child and any(isinstance(item, (dict, list)) for item in child):
                yield from iter_leaves(child, path)
            else:
                yield path, child
    elif isinstance(value, list):
        for index, child in enumerate(value):
            path = f"{prefix}/{index}"
            if isinstance(child, (dict, list)):
                yield from iter_leaves(child, path)
            else:
                yield path, child
    else:
        yield prefix or "/", value


def tri_and(*values: bool | None) -> bool | None:
    if any(value is False for value in values):
        return False
    if all(value is True for value in values):
        return True
    return None


def check_local_presence(obj: dict[str, Any], object_path: str) -> list[str]:
    errors: list[str] = []
    presence = obj.get("presence", {})
    provenance = obj.get("field_provenance", {})
    for path, value in iter_leaves(obj):
        status = presence.get(path)
        if status not in ALL_PRESENCE_CODES:
            errors.append(f"{object_path}{path}: missing or invalid local presence status")
            continue
        if value is None and status not in ABSENT_CODES:
            errors.append(f"{object_path}{path}: null value uses present-value status {status!r}")
        if value is not None and status not in PRESENT_CODES:
            errors.append(f"{object_path}{path}: present value uses absent-value status {status!r}")
        if value is not None:
            source = provenance.get(path)
            if not isinstance(source, dict) or not source.get("source_kind") or not source.get("source_ref"):
                errors.append(f"{object_path}{path}: present value lacks field provenance")
    return errors


def check_global_observability(item: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    status_map = item.get("observability", {}).get("field_status", {})
    channel_map = item.get("observability", {}).get("measurement_channel", {})
    for path, value in iter_leaves(item):
        status = status_map.get(path)
        if status not in ALL_PRESENCE_CODES:
            errors.append(f"{path}: missing episode-level field status")
            continue
        if value is None and status not in ABSENT_CODES:
            errors.append(f"{path}: null value has incompatible field status {status!r}")
        if value is not None and status not in PRESENT_CODES:
            errors.append(f"{path}: present value has incompatible field status {status!r}")
        if path not in channel_map or not channel_map[path]:
            errors.append(f"{path}: missing measurement channel")
    return errors


def check_item(item: dict[str, Any], index: int) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    prefix = f"item[{index}]"

    observations = item["observations"]
    candidates = item["candidates"]
    attempts = item["action_attempts"]
    obs_ids = [row["observation_id"] for row in observations]
    cand_ids = [row["candidate_id"] for row in candidates]
    attempt_ids = [row["attempt_id"] for row in attempts]
    for name, values in (("observation", obs_ids), ("candidate", cand_ids), ("attempt", attempt_ids)):
        if len(values) != len(set(values)):
            errors.append(f"{prefix}: duplicate {name} ids")

    obs_set, cand_set = set(obs_ids), set(cand_ids)
    for candidate in candidates:
        if candidate["observation_id"] not in obs_set:
            errors.append(f"{prefix}: candidate {candidate['candidate_id']} references missing observation")
    for candidate_id in item["decision"]["candidate_input_ids"]:
        if candidate_id not in cand_set:
            errors.append(f"{prefix}: decision references missing candidate {candidate_id}")
    for attempt in attempts:
        if attempt["observation_before_id"] not in obs_set:
            errors.append(f"{prefix}: attempt references missing before observation")
        if attempt["observation_after_id"] is not None and attempt["observation_after_id"] not in obs_set:
            errors.append(f"{prefix}: attempt references missing after observation")
        if attempt["target_candidate_id"] is not None and attempt["target_candidate_id"] not in cand_set:
            errors.append(f"{prefix}: attempt references missing candidate")

    timestamps = [obs["timestamp"] for obs in observations if obs["timestamp"] is not None]
    if timestamps != sorted(timestamps):
        errors.append(f"{prefix}: observation timestamps are not nondecreasing")
    if attempts:
        phases = {obs["phase"] for obs in observations}
        if not ({"popup", "pre_action"} & phases):
            errors.append(f"{prefix}: executed action lacks popup/pre_action observation")
        if not ({"post_action", "task_check"} & phases):
            errors.append(f"{prefix}: executed action lacks post_action/task_check observation")

    errors.extend(check_global_observability(item))
    errors.extend(check_local_presence(item["assistive_technology"], f"{prefix}.assistive_technology"))
    for obs_index, observation in enumerate(observations):
        errors.extend(check_local_presence(observation, f"{prefix}.observations[{obs_index}]"))
    for cand_index, candidate in enumerate(candidates):
        errors.extend(check_local_presence(candidate, f"{prefix}.candidates[{cand_index}]"))

    platform = item["environment"]["platform"]
    if platform == "android":
        if not any(obs["structured_representation"]["android_raw"] is not None for obs in observations):
            errors.append(f"{prefix}: Android item has no Android raw structured observation")
        if item["assistive_technology"]["name"] != "talkback" and item["verification"]["metrics"]["A_VTR"] is not None:
            errors.append(f"{prefix}: Android A-VTR item does not use TalkBack")
    elif platform == "ios":
        if not any(obs["structured_representation"]["ios_raw"] is not None for obs in observations):
            errors.append(f"{prefix}: iOS item has no iOS raw structured observation")
        if item["capability_profile"]["ios_field_status"] != "verified_on_target":
            warnings.append(f"{prefix}: iOS field capability is not verified on target")
        if item["assistive_technology"]["name"] != "voiceover" and item["verification"]["metrics"]["A_VTR"] is not None:
            errors.append(f"{prefix}: iOS A-VTR item does not use VoiceOver")
    elif platform == "mobile_web":
        if not any(obs["structured_representation"]["dom_raw"] is not None for obs in observations):
            errors.append(f"{prefix}: mobile Web item has no DOM raw observation")

    scenario = item["scenario"]
    decision = item["decision"]
    if scenario["scope_label"] == "ordinary_low_risk_popup":
        if scenario["unsafe_context_gt"] or scenario["safety_category_gt"] != "ordinary_exit":
            errors.append(f"{prefix}: ordinary scope conflicts with unsafe/sensitive ground truth")
        if not set(scenario["allowed_action_set_gt"]).issubset(LOW_RISK_ACTIONS):
            errors.append(f"{prefix}: ordinary scope contains a non-low-risk allowed action")
    else:
        if decision["policy"]["decision"] not in {"abstain", "handoff", "no_action"}:
            errors.append(f"{prefix}: sensitive/out-of-scope item did not abstain")
        autonomous = [attempt for attempt in attempts if attempt["execution_channel"] not in {"human", "none"}]
        if autonomous:
            errors.append(f"{prefix}: sensitive/out-of-scope item has autonomous action attempts")

    gate = decision["gate"]
    if decision["method_family"] == "ours":
        if gate["structured_sufficient"]:
            if gate["top1_score"] is None or gate["top1_score"] < gate["threshold_tau"]:
                errors.append(f"{prefix}: structured-sufficient gate is below tau")
            if gate["margin"] is None or gate["margin"] < gate["margin_delta"]:
                errors.append(f"{prefix}: structured-sufficient gate is below delta")
            if not all((gate["owner_consistent"], gate["action_executable"], gate["low_risk_policy_satisfied"], gate["capture_fresh_and_synchronized"])):
                errors.append(f"{prefix}: structured-sufficient gate violates a required condition")
            if gate["gap_reasons"]:
                errors.append(f"{prefix}: structured-sufficient gate still records gaps")
        if decision["visual_fallback"]["used"]:
            if not decision["visual_fallback"]["trigger_reasons"]:
                errors.append(f"{prefix}: visual fallback used without a trigger reason")
            selected_id = decision["selection"]["target_candidate_id_pred"]
            selected = next((candidate for candidate in candidates if candidate["candidate_id"] == selected_id), None)
            if selected is None or selected["visual_raw"] is None:
                errors.append(f"{prefix}: visual fallback did not select a visual candidate")
            elif not selected["ground_truth"]["is_safe_to_execute_gt"]:
                errors.append(f"{prefix}: visual fallback selected an unsafe candidate")

    indexes = [attempt["attempt_index"] for attempt in attempts]
    if indexes != list(range(len(indexes))):
        errors.append(f"{prefix}: attempt indexes are not contiguous from zero")
    if len([a for a in attempts if a["execution_channel"] not in {"human", "none"}]) > 2:
        errors.append(f"{prefix}: more than two autonomous attempts")
    safety = item["verification"]["safety"]
    if safety["retry_count"] != sum(attempt["retry_count"] for attempt in attempts):
        errors.append(f"{prefix}: retry_count does not match action attempts")
    if safety["retry_count"] > safety["retry_budget"]:
        errors.append(f"{prefix}: retry budget exceeded")

    verification = item["verification"]
    dismissal = verification["dismissal"]
    technical = verification["technical_context_recovery"]
    accessible = verification["accessible_context_recovery"]
    task = verification["task"]
    metrics = verification["metrics"]

    expected_d = tri_and(dismissal["visual_popup_gone"], dismissal["semantic_popup_gone"])
    expected_ctech = tri_and(technical["owner_context_restored"], technical["blocked_target_operable"])
    utterance_observable = item["assistive_technology"]["utterance_observability"] != "not_observable"
    focus_observable = item["assistive_technology"]["focus_observability"] != "not_observable"
    if focus_observable:
        ca11y_terms: list[bool | None] = [expected_ctech, accessible["focus_restored_to_blocked_target_or_successor"]]
        if utterance_observable:
            ca11y_terms.append(accessible["spoken_context_consistent"])
        expected_ca11y = tri_and(*ca11y_terms)
    else:
        expected_ca11y = None
    expected_t = task["task_postcondition_satisfied"] if task["postcondition_verifiable"] else None
    expected_vtr = tri_and(expected_d, expected_ctech, expected_t)
    expected_avtr = tri_and(expected_d, expected_ca11y, expected_t)
    checks = [
        ("D", dismissal["D"], expected_d),
        ("C_tech", technical["C_tech"], expected_ctech),
        ("C_a11y", accessible["C_a11y"], expected_ca11y),
        ("T", task["T"], expected_t),
        ("VTR_tech", metrics["VTR_tech"], expected_vtr),
        ("A_VTR", metrics["A_VTR"], expected_avtr)
    ]
    for label, actual, expected in checks:
        if actual is not expected:
            errors.append(f"{prefix}: {label}={actual!r}, expected three-valued derivation {expected!r}")
    for label, section in (
        ("D", dismissal),
        ("C_tech", technical),
        ("C_a11y", accessible),
        ("T", task)
    ):
        truth_key = {"D": "D", "C_tech": "C_tech", "C_a11y": "C_a11y", "T": "T"}[label]
        if section[truth_key] is True and not section["evidence_uris"]:
            errors.append(f"{prefix}: {label}=true has no evidence URI")

    kind = item["identity"]["record_kind"]
    eligibility = verification["eligibility"]
    if kind == "synthetic_schema_fixture":
        if item["identity"]["split"] != "schema_fixture" or item["provenance"]["source_origin"] != "synthetic_schema_fixture":
            errors.append(f"{prefix}: synthetic fixture isolation is invalid")
        if any((eligibility["eligible_for_training"], eligibility["eligible_for_main_metric"], eligibility["eligible_for_user_experience_claim"])):
            errors.append(f"{prefix}: synthetic fixture is eligible for empirical use")
        if set(item["provenance"]["paper_method_ids"]) != EXPECTED_PAPERS:
            errors.append(f"{prefix}: schema fixture does not carry all 14 design-provenance paper ids")
    if kind == "paper_reconstruction" and (item["provenance"]["source_origin"] != "paper_artifact" or item["identity"]["split"] not in {"unassigned", "schema_fixture"}):
        errors.append(f"{prefix}: paper reconstruction isolation is invalid")
    if kind == "controlled_fixture" and item["provenance"]["source_origin"] != "controlled_fixture":
        errors.append(f"{prefix}: controlled fixture origin mismatch")
    if eligibility["eligible_for_user_experience_claim"]:
        if kind != "real_app" or item["environment"]["device_kind"] != "physical" or accessible["observability"] != "human":
            errors.append(f"{prefix}: user-experience eligibility lacks real-device human evidence")
        if not any(annotation["annotator_role"] == "target_user" for annotation in item["annotations"]):
            errors.append(f"{prefix}: user-experience eligibility lacks target-user annotation")

    if metrics["action_attempt_count"] != len(attempts):
        errors.append(f"{prefix}: action_attempt_count does not match attempts")
    if metrics["visual_call_count"] != decision["visual_fallback"]["call_count"]:
        errors.append(f"{prefix}: visual_call_count does not match decision trace")
    return errors, warnings


def check_dataset(items: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    ids = [item["identity"]["item_id"] for item in items]
    if len(ids) != len(set(ids)):
        errors.append("dataset: duplicate item ids")

    split_items = [item for item in items if item["identity"]["split"] in {"train", "validation", "test"}]
    group_fields = [
        "scenario_group_id",
        "app_group_id",
        "popup_template_group_id",
        "sdk_or_cmp_group_id",
        "os_family_group_id",
        "near_duplicate_group_id"
    ]
    for field in group_fields:
        assignments: dict[str, set[str]] = {}
        for item in split_items:
            value = item["identity"][field]
            if value is None:
                errors.append(f"dataset: {field} is null for assigned item {item['identity']['item_id']}")
                continue
            assignments.setdefault(value, set()).add(item["identity"]["split"])
        for value, splits in assignments.items():
            if len(splits) > 1:
                errors.append(f"dataset: leakage group {field}={value!r} spans {sorted(splits)}")

    if not any(item["identity"]["record_kind"] == "real_app" for item in items):
        warnings.append("dataset contains no empirical real-app episodes yet")
    if not any(item["environment"]["platform"] == "ios" for item in items):
        warnings.append("dataset contains no iOS capability or episode record yet")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("data", nargs="?", type=Path, default=DEFAULT_DATA)
    args = parser.parse_args()

    resolved_data_path = args.data.resolve()
    try:
        reported_data_path = str(resolved_data_path.relative_to(ROOT))
    except ValueError:
        reported_data_path = str(resolved_data_path)

    schema = load_json(SCHEMA_PATH)
    crosswalk = load_json(CROSSWALK_PATH)
    field_catalog = load_json(FIELD_CATALOG_PATH)
    qa_rules = load_json(QA_RULES_PATH)
    qa_coverage = load_json(QA_COVERAGE_PATH)
    items = load_jsonl(args.data)

    errors: list[str] = []
    warnings: list[str] = []
    if crosswalk["source_counts"] != {"literature_14": 90, "our_method": 165, "total": 255}:
        errors.append("crosswalk source counts are not 90 + 165 = 255")
    if len(crosswalk["entries"]) != 255:
        errors.append("crosswalk does not contain 255 entries")
    source_keys = [(entry["source_namespace"], entry["source_field_path"]) for entry in crosswalk["entries"]]
    if len(source_keys) != len(set(source_keys)):
        errors.append("crosswalk contains duplicate source field keys")
    for entry in crosswalk["entries"]:
        if not entry["canonical_item_pointers"]:
            errors.append(f"unmapped source field: {entry['source_namespace']}:{entry['source_field_path']}")
        for pointer in entry["canonical_item_pointers"]:
            if not schema_pointer_exists(schema, pointer):
                errors.append(f"crosswalk pointer does not exist in schema: {pointer}")

    counts = field_catalog["counts"]
    if counts != {"literature_atomic_fields": 90, "our_method_atomic_fields": 165, "source_records_total": 255}:
        errors.append("field catalog counts are not 90 + 165 = 255")
    if len(qa_rules["item_gates"]) != 23 or len(qa_rules["dataset_gates"]) != 6:
        errors.append("QA contract does not contain the expected 23 item and 6 dataset gates")
    contract_gate_ids = {
        gate["id"] for gate in qa_rules["item_gates"] + qa_rules["dataset_gates"]
    }
    coverage_gate_ids = (
        qa_coverage["automated_full"]
        + qa_coverage["automated_partial"]
        + qa_coverage["manual_release"]
    )
    if len(coverage_gate_ids) != len(set(coverage_gate_ids)):
        errors.append("QA implementation coverage contains duplicate gate ids")
    if set(coverage_gate_ids) != contract_gate_ids:
        missing = sorted(contract_gate_ids - set(coverage_gate_ids))
        extra = sorted(set(coverage_gate_ids) - contract_gate_ids)
        errors.append(f"QA implementation coverage mismatch: missing={missing}, extra={extra}")
    calculated_coverage_counts = {
        "automated_full": len(qa_coverage["automated_full"]),
        "automated_partial": len(qa_coverage["automated_partial"]),
        "manual_release": len(qa_coverage["manual_release"]),
        "total": len(coverage_gate_ids)
    }
    if calculated_coverage_counts != qa_coverage["counts"]["all"]:
        errors.append("QA implementation coverage counts do not match classified gate ids")

    for index, item in enumerate(items):
        schema_errors = validate_schema(item, schema, schema, f"item[{index}]")
        errors.extend(schema_errors)
        if not schema_errors:
            item_errors, item_warnings = check_item(item, index)
            errors.extend(item_errors)
            warnings.extend(item_warnings)
    dataset_errors, dataset_warnings = check_dataset(items)
    errors.extend(dataset_errors)
    warnings.extend(dataset_warnings)

    result = {
        "status": "pass" if not errors else "fail",
        "data_file": reported_data_path,
        "item_count": len(items),
        "schema_version": "1.0.0-provisional",
        "source_field_counts": {"literature": 90, "our_method": 165, "crosswalk_total": 255},
        "qa_contract_counts": {"item_gates": 23, "dataset_gates": 6},
        "qa_implementation_coverage": qa_coverage["counts"]["all"],
        "validation_scope": "schema_shape_and_documented_automated_assertions_only",
        "manual_release_gate_ids": qa_coverage["manual_release"],
        "errors": errors,
        "warnings": warnings,
        "empirical_status": "pending_real_device_collection"
    }
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
