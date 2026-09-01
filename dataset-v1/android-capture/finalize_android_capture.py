#!/usr/bin/env python3
"""Fail-closed finalization for synchronized Android capture bundles.

This module validates capture feasibility only.  It never produces human-gold
labels, model predictions, benchmark metrics, or a paper-result claim.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import struct
from typing import Any
import zlib


CAPTURE_SCHEMA_VERSION = "1.0.0"
SNAPSHOT_SCHEMA_VERSION = "1.0.0"
MAX_SYNCHRONIZATION_DELTA_MS = 3000
ALLOWED_STRATA = {
    "popup_candidate",
    "no_popup_candidate",
    "boundary_candidate",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _object(value: Any, name: str) -> dict[str, Any]:
    _require(isinstance(value, dict), f"{name} must be an object")
    return value


def _nonempty_string(value: Any, name: str) -> str:
    _require(isinstance(value, str) and bool(value.strip()), f"{name} must be non-empty")
    return value


def _resolve_artifact(bundle_root: Path, relative_value: Any, name: str) -> Path:
    relative = Path(_nonempty_string(relative_value, name))
    _require(not relative.is_absolute(), f"{name} must be relative to the bundle")
    _require(".." not in relative.parts, f"{name} must not escape the bundle")
    target = bundle_root / relative
    _require(not target.is_symlink(), f"{name} must not be a symlink")
    resolved_root = bundle_root.resolve()
    resolved = target.resolve()
    _require(resolved == resolved_root or resolved_root in resolved.parents, f"{name} escapes the bundle")
    _require(resolved.is_file(), f"{name} does not exist")
    return resolved


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_time(value: Any, name: str) -> datetime:
    text = _nonempty_string(value, name)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{name} must be an ISO-8601 timestamp") from error
    _require(parsed.tzinfo is not None, f"{name} must include a timezone")
    return parsed


def _validate_screenshot(data: bytes) -> None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        offset = 8
        chunk_types: list[bytes] = []
        width = height = 0
        while offset + 12 <= len(data):
            length = struct.unpack(">I", data[offset : offset + 4])[0]
            end = offset + 12 + length
            _require(end <= len(data), "screenshot must be a valid PNG")
            chunk_type = data[offset + 4 : offset + 8]
            payload = data[offset + 8 : offset + 8 + length]
            expected_crc = struct.unpack(">I", data[offset + 8 + length : end])[0]
            actual_crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
            _require(expected_crc == actual_crc, "screenshot must be a valid PNG")
            chunk_types.append(chunk_type)
            if chunk_type == b"IHDR":
                _require(length == 13, "screenshot must be a valid PNG")
                width, height = struct.unpack(">II", payload[:8])
            offset = end
            if chunk_type == b"IEND":
                break
        _require(
            chunk_types[:1] == [b"IHDR"]
            and b"IDAT" in chunk_types
            and chunk_types[-1:] == [b"IEND"]
            and width > 0
            and height > 0
            and offset == len(data),
            "screenshot must be a valid PNG",
        )
        return
    _require(
        data.startswith(b"\xff\xd8\xff") and len(data) >= 8 and data.endswith(b"\xff\xd9"),
        "screenshot must be a valid PNG or JPEG",
    )


def _validate_capture_provenance(metadata: dict[str, Any], collector: dict[str, Any]) -> None:
    device = _object(metadata.get("device"), "device")
    for field in ("manufacturer", "model", "android_release"):
        _nonempty_string(device.get(field), f"device.{field}")
    for field in ("api_level", "display_width_px", "display_height_px"):
        value = device.get(field)
        _require(
            isinstance(value, int) and not isinstance(value, bool) and value > 0,
            f"device.{field} must be a positive integer",
        )

    app = _object(metadata.get("app"), "app")
    _nonempty_string(app.get("package_name"), "app.package_name")
    _nonempty_string(app.get("version_name"), "app.version_name")
    version_code = app.get("version_code")
    _require(
        isinstance(version_code, int) and not isinstance(version_code, bool) and version_code >= 0,
        "app.version_code must be a non-negative integer",
    )
    _nonempty_string(metadata.get("locale"), "locale")

    _nonempty_string(collector.get("name"), "collector.name")
    _nonempty_string(collector.get("version"), "collector.version")
    flags = collector.get("service_flags")
    _require(
        isinstance(flags, list) and "FLAG_RETRIEVE_INTERACTIVE_WINDOWS" in flags,
        "collector.service_flags must include FLAG_RETRIEVE_INTERACTIVE_WINDOWS",
    )


def _validate_accessibility_snapshot(snapshot: dict[str, Any]) -> tuple[int, int]:
    _require(
        snapshot.get("snapshot_schema_version") == SNAPSHOT_SCHEMA_VERSION,
        f"snapshot_schema_version must be {SNAPSHOT_SCHEMA_VERSION}",
    )
    windows = snapshot.get("windows")
    nodes = snapshot.get("nodes")
    _require(isinstance(windows, list) and len(windows) > 0, "snapshot must contain at least one window")
    _require(isinstance(nodes, list) and len(nodes) > 0, "snapshot must contain at least one node")

    node_ids: list[str] = []
    for index, raw_node in enumerate(nodes):
        node = _object(raw_node, f"nodes[{index}]")
        node_ids.append(_nonempty_string(node.get("node_id"), f"nodes[{index}].node_id"))
    _require(len(node_ids) == len(set(node_ids)), "snapshot contains duplicate node_id")
    node_id_set = set(node_ids)

    window_ids: list[Any] = []
    for index, raw_window in enumerate(windows):
        window = _object(raw_window, f"windows[{index}]")
        window_id = window.get("window_id")
        _require(window_id is not None, f"windows[{index}].window_id is required")
        window_ids.append(window_id)
        root_id = _nonempty_string(window.get("root_node_id"), f"windows[{index}].root_node_id")
        _require(root_id in node_id_set, f"windows[{index}] references an unknown root node")
    _require(len(window_ids) == len(set(window_ids)), "snapshot contains duplicate window_id")
    window_id_set = set(window_ids)

    for index, raw_node in enumerate(nodes):
        node = _object(raw_node, f"nodes[{index}]")
        _require(node.get("window_id") in window_id_set, f"nodes[{index}] references an unknown window")
        parent_id = node.get("parent_id")
        _require(parent_id is None or parent_id in node_id_set, f"nodes[{index}] references an unknown parent")
        children = node.get("child_ids", [])
        _require(isinstance(children, list), f"nodes[{index}].child_ids must be a list")
        _require(all(child in node_id_set for child in children), f"nodes[{index}] references an unknown child")

    forbidden = {"gold_label", "gold_labels", "prediction", "predictions", "method_prediction"}
    _require(not forbidden.intersection(snapshot), "snapshot must not contain gold labels or predictions")
    return len(nodes), len(windows)


def finalize_capture(metadata_path: Path) -> dict[str, Any]:
    """Validate one private bundle and return a disclosure-minimized record."""

    metadata_path = Path(metadata_path)
    _require(metadata_path.is_file(), "capture metadata does not exist")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("capture metadata must be valid UTF-8 JSON") from error
    metadata = _object(metadata, "capture metadata")
    _require(
        metadata.get("capture_schema_version") == CAPTURE_SCHEMA_VERSION,
        f"capture_schema_version must be {CAPTURE_SCHEMA_VERSION}",
    )

    capture_id = _nonempty_string(metadata.get("capture_id"), "capture_id")
    item_id = _nonempty_string(metadata.get("item_id"), "item_id")
    source_group_id = _nonempty_string(metadata.get("source_group_id"), "source_group_id")
    template_id = _nonempty_string(
        metadata.get("popup_template_family_id"), "popup_template_family_id"
    )
    stratum = _nonempty_string(metadata.get("intended_stratum"), "intended_stratum")
    _require(stratum in ALLOWED_STRATA, "intended_stratum is outside the frozen V1 strata")

    _require(metadata.get("observation_phase") == "pre_action", "observation_phase must be pre_action")
    attempts = metadata.get("action_attempts")
    _require(isinstance(attempts, list) and not attempts, "capture must be action-free")
    _require(metadata.get("gold_labels_present") is False, "capture must not contain gold labels")
    _require(metadata.get("method_predictions_present") is False, "capture must not contain method predictions")

    collector = _object(metadata.get("collector"), "collector")
    _require(
        collector.get("mode") == "accessibilityservice_node_snapshot",
        "collector must use an Android AccessibilityService node snapshot",
    )
    _require(collector.get("window_retrieval_enabled") is True, "AccessibilityService window retrieval must be enabled")
    _nonempty_string(collector.get("service_package"), "collector.service_package")
    _validate_capture_provenance(metadata, collector)

    before = _nonempty_string(metadata.get("stable_state_token_before"), "stable_state_token_before")
    after = _nonempty_string(metadata.get("stable_state_token_after"), "stable_state_token_after")
    _require(before == after, "state drift detected between synchronized artifacts")
    screenshot_at = _parse_time(metadata.get("screenshot_captured_at"), "screenshot_captured_at")
    accessibility_at = _parse_time(
        metadata.get("accessibility_captured_at"), "accessibility_captured_at"
    )
    delta_ms = round(abs((accessibility_at - screenshot_at).total_seconds()) * 1000)
    _require(
        delta_ms <= MAX_SYNCHRONIZATION_DELTA_MS,
        f"synchronization delta exceeds {MAX_SYNCHRONIZATION_DELTA_MS} ms",
    )

    authorization = _object(metadata.get("authorization"), "authorization")
    _require(authorization.get("collection_authorized") is True, "collection must be authorized")
    _nonempty_string(authorization.get("basis"), "authorization.basis")
    _require(authorization.get("privacy_review_status") == "passed", "privacy review must be passed")
    redistribution = authorization.get("redistribution_status")
    _require(
        redistribution in {"public_media", "adapter_only"},
        "redistribution_status must be public_media or adapter_only",
    )

    bundle_root = metadata_path.resolve().parent
    screenshot_path = _resolve_artifact(bundle_root, metadata.get("screenshot_path"), "screenshot_path")
    snapshot_path = _resolve_artifact(
        bundle_root,
        metadata.get("accessibility_snapshot_path"),
        "accessibility_snapshot_path",
    )
    screenshot_bytes = screenshot_path.read_bytes()
    snapshot_bytes = snapshot_path.read_bytes()
    _validate_screenshot(screenshot_bytes)
    try:
        snapshot = json.loads(snapshot_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("accessibility snapshot must be valid UTF-8 JSON") from error
    node_count, window_count = _validate_accessibility_snapshot(_object(snapshot, "accessibility snapshot"))

    return {
        "capture_schema_version": CAPTURE_SCHEMA_VERSION,
        "status": "eligible_for_capture_feasibility",
        "capture_id": capture_id,
        "item_id": item_id,
        "source_group_id": source_group_id,
        "popup_template_family_id": template_id,
        "intended_stratum": stratum,
        "collector_mode": "accessibilityservice_node_snapshot",
        "authorization_summary": {
            "collection_authorized": True,
            "privacy_review_status": "passed",
            "redistribution_status": redistribution,
        },
        "synchronization": {
            "delta_ms": delta_ms,
            "maximum_delta_ms": MAX_SYNCHRONIZATION_DELTA_MS,
            "stable_state_verified": True,
        },
        "artifacts": {
            "screenshot_sha256": _sha256(screenshot_bytes),
            "screenshot_size_bytes": len(screenshot_bytes),
            "accessibility_snapshot_sha256": _sha256(snapshot_bytes),
            "accessibility_snapshot_size_bytes": len(snapshot_bytes),
        },
        "accessibility_summary": {
            "node_count": node_count,
            "window_count": window_count,
        },
        "paper_result_eligible": False,
        "human_gold_count": 0,
    }


def audit_feasibility(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Audit only capture coverage; this cannot unlock paper-result claims."""

    _require(isinstance(records, list), "records must be a list")
    _require(records, "at least one capture record is required")
    for index, record in enumerate(records):
        _require(isinstance(record, dict), f"records[{index}] must be an object")
        _require(
            record.get("status") == "eligible_for_capture_feasibility",
            f"records[{index}] is not capture-feasibility eligible",
        )

    def values(key: str) -> list[str]:
        return [_nonempty_string(record.get(key), f"record.{key}") for record in records]

    capture_ids = values("capture_id")
    groups = values("source_group_id")
    templates = values("popup_template_family_id")
    strata = values("intended_stratum")
    _require(len(capture_ids) == len(set(capture_ids)), "duplicate capture_id detected")

    screenshot_hashes = [
        _nonempty_string(_object(record.get("artifacts"), "record.artifacts").get("screenshot_sha256"), "screenshot_sha256")
        for record in records
    ]
    snapshot_hashes = [
        _nonempty_string(_object(record.get("artifacts"), "record.artifacts").get("accessibility_snapshot_sha256"), "accessibility_snapshot_sha256")
        for record in records
    ]
    _require(len(screenshot_hashes) == len(set(screenshot_hashes)), "duplicate screenshot hash detected")
    _require(len(snapshot_hashes) == len(set(snapshot_hashes)), "duplicate accessibility snapshot hash detected")
    _require(len(set(groups)) >= 5, "at least 5 source groups are required")
    _require(len(set(templates)) >= 3, "at least 3 popup template families are required")
    missing_strata = ALLOWED_STRATA.difference(strata)
    _require(not missing_strata, f"all frozen strata are required; missing: {sorted(missing_strata)}")

    return {
        "status": "ready_for_real_g1_pilot",
        "capture_count": len(records),
        "source_group_count": len(set(groups)),
        "popup_template_family_count": len(set(templates)),
        "strata": sorted(set(strata)),
        "paper_result_eligible": False,
        "human_gold_count": 0,
        "next_gate": "independent_blinded_g1_annotation",
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed Android capture feasibility finalizer"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    finalize_parser = subparsers.add_parser("finalize", help="finalize one private capture bundle")
    finalize_parser.add_argument("--metadata", required=True, type=Path)
    finalize_parser.add_argument("--output", required=True, type=Path)
    audit_parser = subparsers.add_parser("audit", help="audit a JSON list of finalized records")
    audit_parser.add_argument("--records", required=True, type=Path)
    audit_parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args(argv)

    try:
        if arguments.command == "finalize":
            result = finalize_capture(arguments.metadata)
        else:
            raw_records = json.loads(arguments.records.read_text(encoding="utf-8"))
            result = audit_feasibility(raw_records)
        _write_json(arguments.output, result)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        parser.exit(2, f"capture finalization failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
