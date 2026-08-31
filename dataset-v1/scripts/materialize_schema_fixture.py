#!/usr/bin/env python3
"""Materialize the non-empirical schema fixture as one JSONL dataset item."""

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
    if any(token in path for token in ("target_user_validation", "relaunch", "business_choice", "iabtcf")):
        return "not_available"
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


def main() -> None:
    item = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    evidence = make_evidence()

    item["provenance"]["source_artifacts"] = [deepcopy(evidence)]
    item["provenance"]["raw_capture_hashes"] = {"fixture_oracle": evidence["sha256"]}
    item["provenance"]["episode_evidence_uris"] = [deepcopy(evidence)]
    item["capability_profile"]["evidence_refs"] = [deepcopy(evidence)]

    for observation in item["observations"]:
        populate_local_maps(observation)
    for candidate in item["candidates"]:
        populate_local_maps(candidate)
    populate_local_maps(item["assistive_technology"])

    verification = item["verification"]
    for section_name in (
        "dismissal",
        "technical_context_recovery",
        "accessible_context_recovery",
        "task",
        "persistence"
    ):
        verification[section_name]["evidence_uris"] = [deepcopy(evidence)]
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

    OUTPUT.write_text(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote non-empirical schema fixture to {OUTPUT}")


if __name__ == "__main__":
    main()
