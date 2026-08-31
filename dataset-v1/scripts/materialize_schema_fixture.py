#!/usr/bin/env python3
"""Materialize positive, no-popup, and abstain v1 schema fixtures as JSONL."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "data" / "item.template.json"
OUTPUT = ROOT / "data" / "items.schema-fixture.jsonl"


def pointer_escape(part: str) -> str:
    return part.replace("~", "~0").replace("/", "~1")


def iter_leaves(value: Any, prefix: str = "", skip_meta: bool = True) -> Iterator[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            if skip_meta and key in {"presence", "field_provenance", "field_status", "measurement_channel"}:
                continue
            path = f"{prefix}/{pointer_escape(str(key))}"
            if isinstance(child, dict) and child:
                yield from iter_leaves(child, path, skip_meta=skip_meta)
            elif isinstance(child, list) and child and any(isinstance(item, (dict, list)) for item in child):
                yield from iter_leaves(child, path, skip_meta=skip_meta)
            else:
                yield path, child
    elif isinstance(value, list):
        for index, child in enumerate(value):
            path = f"{prefix}/{index}"
            if isinstance(child, (dict, list)):
                yield from iter_leaves(child, path, skip_meta=skip_meta)
            else:
                yield path, child
    else:
        yield prefix or "/", value


def status_for(path: str, value: Any) -> str:
    if value is not None:
        if path.endswith("_gt") or "/ground_truth/" in path or "/annotations/" in path:
            return "annotated"
        if any(token in path for token in ("/scores/", "/metrics/", "/verification/", "/decision/gate/")):
            return "derived"
        return "observed"
    if any(token in path for token in ("/ios_raw", "/dom_raw", "/braille_display")):
        return "not_applicable"
    if any(token in path for token in (
        "/verification/weak_proxies/",
        "/verification/dismissal/",
        "/verification/technical_context_recovery/",
        "/verification/accessible_context_recovery/",
        "/verification/task/",
        "/verification/persistence/",
        "/verification/metrics/VTR_tech",
        "/verification/metrics/A_VTR",
        "/verification/metrics/recovery_time_ms",
        "/verification/metrics/extra_navigation_steps_after_dismissal",
        "target_user_validation",
        "relaunch",
        "business_choice",
        "iabtcf"
    )):
        return "not_applicable"
    return "not_available"


def fixture_provenance(path: str, status: str) -> dict[str, Any]:
    return {
        "source_kind": "schema_fixture" if status != "derived" else "derived",
        "source_ref": "fixture-oracle" if status != "derived" else f"fixture-derived:{path}",
        "collector_version": "schema-fixture-v1",
        "timestamp": "2026-08-31T00:00:00Z",
        "notes": "Synthetic schema-validation value; not empirical evidence."
    }


def populate_local_maps(obj: dict[str, Any], include_all_leaves: bool = True) -> None:
    presence = obj.setdefault("presence", {})
    provenance = obj.setdefault("field_provenance", {})
    leaves = list(iter_leaves(obj)) if include_all_leaves else []
    for path, value in leaves:
        status = status_for(path, value)
        presence[path] = status
        if value is not None:
            provenance[path] = fixture_provenance(path, status)


def make_evidence() -> dict[str, Any]:
    digest = hashlib.sha256(b"synthetic popup schema fixture oracle").hexdigest()
    return {
        "uri": "fixture://popup-schema-oracle/v1",
        "sha256": digest,
        "media_type": "application/x-popup-schema-fixture",
        "redaction_status": "not_needed",
        "capture_channel": "fixture_oracle"
    }


def make_variants(base: dict[str, Any]) -> list[dict[str, Any]]:
    positive = deepcopy(base)

    negative = deepcopy(base)
    negative["identity"]["item_id"] = "fixture.android.popup-message.negative.0001"
    negative["identity"]["near_duplicate_group_id"] = "fixture.popup-message-negative-a"
    negative["scenario"]["popup_expected_gt"] = False
    negative["scenario"]["popup_kind_gt"] = None
    negative["scenario"]["popup_owner_gt"] = None
    negative["scenario"]["exposure_status_gt"] = "unknown_cause"
    negative["scenario"]["exposure_cause_gt"] = None
    observation = negative["observations"][0]
    observation["popup"].update({
        "present_gt": False,
        "present_pred": False,
        "kind_gt": None,
        "bbox_gt": None,
        "owner_gt": None,
        "modal_gt": False,
        "blocking_gt": None,
        "overlay_ratio": 0.0,
        "dimming_ratio": 0.0
    })
    observation["visual_representation"].update({
        "popup_prediction_stage1": 0.02,
        "popup_prediction_stage2": 0.01,
        "popup_detector_class": "content",
        "popup_detector_confidence": 0.98,
        "popup_bbox_pred": None,
        "popup_roi": None,
        "ocr_items": [],
        "vlm_output": None
    })
    negative["candidates"] = []
    negative["decision"]["candidate_input_ids"] = []
    negative["decision"]["gate"].update({
        "top1_candidate_id": None,
        "top1_score": None,
        "gap_reasons": [],
        "owner_consistent": None,
        "action_executable": None
    })
    negative["message_judgment"]["labels"].update({
        "popup_present_gt": False,
        "blocking_gt": None,
        "message_text_gt": None,
        "critical_facts_gt": [],
        "message_text_observability": "not_applicable"
    })
    negative["message_judgment"]["prediction"].update({
        "popup_present_pred": False,
        "message_text_pred": None,
        "critical_facts_pred": [],
        "confidence": 0.96
    })
    negative["message_judgment"]["gate"].update({
        "structured_message_complete": True,
        "gap_reasons": [],
        "visual_fallback_used": False,
        "visual_call_count": 0
    })
    negative["decision"]["gate"]["visual_fallback_triggered"] = False
    negative["decision"]["visual_fallback"].update({
        "required": False,
        "used": False,
        "trigger_reasons": [],
        "call_count": 0,
        "latency_ms": 0
    })
    negative["verification"]["metrics"]["visual_call_count"] = 0
    negative["message_judgment"]["evaluation"].update({
        "presence_correct": True,
        "message_semantically_correct": None,
        "critical_information_recall": None,
        "critical_hallucination": None,
        "VPMA": True
    })
    negative["feedback"]["message"] = "No popup detected."
    negative["annotations"][0].update({
        "annotation_id": "ann.fixture.no-popup",
        "target_json_pointer": "/message_judgment/labels/popup_present_gt",
        "label_name": "popup_present_gt",
        "label_value": False
    })
    negative["provenance"]["annotation_record_ids"] = ["ann.fixture.no-popup"]

    abstain = deepcopy(base)
    abstain["identity"]["item_id"] = "fixture.android.popup-message.abstain.0001"
    abstain["identity"]["near_duplicate_group_id"] = "fixture.popup-message-abstain-a"
    abstain["message_judgment"]["prediction"].update({
        "status": "abstain",
        "popup_present_pred": None,
        "message_text_pred": None,
        "critical_facts_pred": [],
        "confidence": None
    })
    abstain["message_judgment"]["gate"].update({
        "structured_message_complete": False,
        "gap_reasons": ["contradictory"],
        "visual_fallback_used": True,
        "visual_call_count": 1
    })
    abstain["message_judgment"]["evaluation"].update({
        "presence_correct": None,
        "message_semantically_correct": None,
        "critical_information_recall": None,
        "critical_hallucination": None,
        "VPMA": None
    })
    abstain["decision"]["policy"]["decision"] = "abstain"
    abstain["decision"]["gate"]["final_state"] = "abstained"
    abstain["decision"]["abstention"].update({
        "abstained": True,
        "handoff_required": False,
        "reason": "critical_message_conflict",
        "user_message": "Unable to determine the popup message reliably."
    })
    abstain["feedback"].update({
        "status": "abstained",
        "message": "Unable to determine the popup message reliably.",
        "delivered": True
    })
    return [positive, negative, abstain]


def materialize(item: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    item["provenance"]["source_artifacts"] = [deepcopy(evidence)]
    item["provenance"]["raw_capture_hashes"] = {"fixture_oracle": evidence["sha256"]}
    item["provenance"]["episode_evidence_uris"] = [deepcopy(evidence)]
    item["capability_profile"]["evidence_refs"] = [deepcopy(evidence)]
    item["message_judgment"]["labels"]["evidence_uris"] = [deepcopy(evidence)]
    item["message_judgment"]["prediction"]["evidence_uris"] = [deepcopy(evidence)]

    for observation in item["observations"]:
        populate_local_maps(observation)
    for candidate in item["candidates"]:
        populate_local_maps(candidate)
    populate_local_maps(item["assistive_technology"])

    for annotation in item["annotations"]:
        annotation["evidence_uris"] = [deepcopy(evidence)]

    field_status: dict[str, str] = {}
    measurement_channel: dict[str, str] = {}
    for path, value in iter_leaves(item):
        status = status_for(path, value)
        field_status[path] = status
        measurement_channel[path] = "fixture_oracle" if value is not None else status
    item["observability"] = {
        "field_status": field_status,
        "measurement_channel": measurement_channel
    }

    return item


def main() -> None:
    base = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    evidence = make_evidence()
    items = [materialize(item, evidence) for item in make_variants(base)]
    payload = "".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n" for item in items)
    OUTPUT.write_text(payload, encoding="utf-8")
    print(f"Wrote {len(items)} non-empirical v1 schema fixtures to {OUTPUT}")


if __name__ == "__main__":
    main()
