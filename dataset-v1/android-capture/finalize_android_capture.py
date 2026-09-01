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
import re
import struct
from typing import Any
import zlib


CAPTURE_SCHEMA_VERSION = "1.0.0"
COLLECTOR_CAPTURE_SCHEMA_VERSION = "1.1.0"
SNAPSHOT_SCHEMA_VERSION = "1.0.0"
MAX_SYNCHRONIZATION_DELTA_MS = 3000
ALLOWED_STRATA = {
    "popup_candidate",
    "no_popup_candidate",
    "boundary_candidate",
}

WINDOW_CANONICAL_FIELDS = (
    "display_id",
    "window_id",
    "type",
    "layer",
    "title",
    "active",
    "focused",
    "accessibility_focused",
    "bounds_in_screen",
)
NODE_CANONICAL_FIELDS = (
    "window_id",
    "package",
    "class",
    "view_id",
    "text",
    "content_description",
    "hint_text",
    "state_description",
    "pane_title",
    "tooltip_text",
    "bounds_in_screen",
    "visible_to_user",
    "enabled",
    "clickable",
    "long_clickable",
    "focusable",
    "focused",
    "accessibility_focused",
    "checkable",
    "checked",
    "selected",
    "scrollable",
    "dismissable",
    "heading",
    "password",
    "actions",
)


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

    def contains_forbidden_key(value: Any) -> bool:
        if isinstance(value, dict):
            return bool(forbidden.intersection(value)) or any(
                contains_forbidden_key(child) for child in value.values()
            )
        if isinstance(value, list):
            return any(contains_forbidden_key(child) for child in value)
        return False

    _require(
        not contains_forbidden_key(snapshot),
        "snapshot must not contain gold labels or predictions",
    )
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


def _read_json_file(path: Path, name: str) -> dict[str, Any]:
    _require(path.is_file() and not path.is_symlink(), f"{name} does not exist or is a symlink")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{name} must be valid UTF-8 JSON") from error
    return _object(value, name)


def _contains_key_recursive(value: Any, forbidden: set[str]) -> bool:
    if isinstance(value, dict):
        return bool(forbidden.intersection(value)) or any(
            _contains_key_recursive(child, forbidden) for child in value.values()
        )
    if isinstance(value, list):
        return any(_contains_key_recursive(child, forbidden) for child in value)
    return False


def _validate_collector_request(request: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "capture_id",
        "item_id",
        "source_group_id",
        "popup_template_family_id",
        "intended_stratum",
        "expected_target_package",
        "request_nonce",
    }
    _require(set(request) == required, "collector request must contain exactly the V1.1 keys")
    _require(request.get("schema_version") == "1.1", "collector request schema must be 1.1")
    for field in required.difference({"schema_version"}):
        _nonempty_string(request.get(field), f"request.{field}")
    _require(
        request.get("intended_stratum") in ALLOWED_STRATA,
        "request.intended_stratum is outside the frozen V1 strata",
    )


def _validate_machine_artifact(
    bundle_root: Path,
    artifacts: dict[str, Any],
    key: str,
    expected_filename: str,
) -> tuple[Path, bytes]:
    record = _object(artifacts.get(key), f"machine.artifacts.{key}")
    _require(
        record.get("filename") == expected_filename,
        f"machine.artifacts.{key}.filename mismatch",
    )
    path = _resolve_artifact(bundle_root, expected_filename, expected_filename)
    data = path.read_bytes()
    _require(record.get("bytes") == len(data), f"{expected_filename} byte count mismatch")
    _require(record.get("sha256") == _sha256(data), f"{expected_filename} sha256 mismatch")
    return path, data


def _collector_tree_commitment(tree: dict[str, Any]) -> dict[str, Any]:
    """Reconstruct the collector commitment and derivable top-level summaries."""

    entries: list[tuple[str, str, dict[str, str | None], list[str]]] = []
    packages: list[str] = []
    focus_tokens: list[str] = []
    password_node_present = False
    boolean_fields = {
        "visible_to_user",
        "enabled",
        "clickable",
        "long_clickable",
        "focusable",
        "focused",
        "accessibility_focused",
        "checkable",
        "checked",
        "selected",
        "scrollable",
        "dismissable",
        "heading",
        "password",
    }

    def node_fields(node: dict[str, Any], path: str) -> dict[str, str | None]:
        expected = {"id", "children", *NODE_CANONICAL_FIELDS}
        _require(set(node) == expected, f"{path} field set does not match the collector")
        fields: dict[str, str | None] = {}
        for field in NODE_CANONICAL_FIELDS:
            value = node.get(field)
            _require(
                value is None or isinstance(value, str),
                f"{path}.{field} must be a string or null",
            )
            if field in boolean_fields:
                _require(value in {"true", "false"}, f"{path}.{field} has an invalid boolean value")
            if field == "actions":
                _require(value is not None, f"{path}.actions must be a string")
                _require(
                    re.fullmatch(r"(?:\d+(?:,\d+)*)?", value) is not None,
                    f"{path}.actions must be a sorted comma-separated integer list",
                )
                action_ids = [] if not value else [int(part) for part in value.split(",")]
                _require(
                    action_ids == sorted(action_ids),
                    f"{path}.actions must be sorted",
                )
            fields[field] = value
        return fields

    def visit_node(
        raw_node: Any,
        path: str,
        expected_id: str,
        expected_window_id: int,
    ) -> str:
        nonlocal password_node_present
        node = _object(raw_node, path)
        node_id = _nonempty_string(node.get("id"), f"{path}.id")
        _require(node_id == expected_id, f"{path}.id does not match the collector path")
        fields = node_fields(node, path)
        _require(
            fields["window_id"] == str(expected_window_id),
            f"{path}.window_id does not match its window",
        )
        package_name = fields["package"]
        if package_name is not None and package_name not in packages:
            packages.append(package_name)
        if fields["accessibility_focused"] == "true" or fields["focused"] == "true":
            focus_tokens.append(
                f"{node_id}:a={fields['accessibility_focused']}:i={fields['focused']}"
            )
        password_node_present |= fields["password"] == "true"
        children = node.get("children")
        _require(isinstance(children, list), f"{path}.children must be a list")
        child_ids = [
            visit_node(
                child,
                f"{path}.children[{index}]",
                f"{node_id}.{index}",
                expected_window_id,
            )
            for index, child in enumerate(children)
        ]
        entries.append(("node", node_id, fields, child_ids))
        return node_id

    windows = tree.get("windows")
    _require(isinstance(windows, list), "collector tree windows must be a list")
    window_order: list[tuple[int, int, int]] = []
    for index, raw_window in enumerate(windows):
        path = f"collector tree windows[{index}]"
        window = _object(raw_window, path)
        expected = {"id", "root", *WINDOW_CANONICAL_FIELDS}
        _require(set(window) == expected, f"{path} field set does not match the collector")
        window_id = _nonempty_string(window.get("id"), f"{path}.id")
        fields: dict[str, str | None] = {}
        for field in WINDOW_CANONICAL_FIELDS:
            value = window.get(field)
            if field in {"display_id", "window_id", "type", "layer"}:
                _require(
                    isinstance(value, int) and not isinstance(value, bool),
                    f"{path}.{field} must be an integer",
                )
                fields[field] = str(value)
            elif field in {"active", "focused", "accessibility_focused"}:
                _require(isinstance(value, bool), f"{path}.{field} must be boolean")
                fields[field] = "true" if value else "false"
            else:
                _require(
                    value is None or isinstance(value, str),
                    f"{path}.{field} must be a string or null",
                )
                fields[field] = value
        expected_window_id = f"w:{window['display_id']}:{window['window_id']}"
        _require(
            window_id == expected_window_id,
            f"{path}.id does not match the collector window path",
        )
        window_order.append((window["display_id"], window["layer"], window["window_id"]))
        root = window.get("root")
        child_ids = [] if root is None else [
            visit_node(
                root,
                f"{path}.root",
                f"{window_id}/n:0",
                window["window_id"],
            )
        ]
        entries.append(("window", window_id, fields, child_ids))
    _require(window_order == sorted(window_order), "collector tree windows are not in collector order")

    serialized: list[str] = []

    def append(label: str, value: str | None) -> None:
        if value is None:
            serialized.append(f"{label}:null\n")
            return
        serialized.append(f"{label}:string:{len(value.encode('utf-8'))}:{value}\n")

    for kind, entry_id, fields, child_ids in sorted(
        entries, key=lambda entry: (entry[0], entry[1])
    ):
        append("entry-kind", kind)
        append("entry-id", entry_id)
        for key in sorted(fields):
            append("field-key", key)
            append("field-value", fields[key])
        for child_id in child_ids:
            append("child", child_id)
        serialized.append("entry-end\n")
    return {
        "sha256": _sha256("".join(serialized).encode("utf-8")),
        "target_packages": packages,
        "focus_token": "<none>" if not focus_tokens else "|".join(sorted(focus_tokens)),
        "password_node_present": password_node_present,
    }


def _canonical_collector_tree_sha256(tree: dict[str, Any]) -> str:
    """Recompute the Android collector's CanonicalStateHasher commitment."""

    return _collector_tree_commitment(tree)["sha256"]


def _validate_collector_tree(
    tree: dict[str, Any],
    *,
    expected_hash: str,
    expected_package: str,
    expected_start: int,
    expected_end: int,
    expected_focus: str,
    name: str,
) -> tuple[int, int]:
    expected_top_level = {
        "schema_version",
        "clock",
        "start_uptime_ms",
        "end_uptime_ms",
        "canonical_tree_sha256",
        "focus_token",
        "node_count",
        "contains_sensitive_node",
        "truncated",
        "target_packages",
        "windows",
    }
    _require(set(tree) == expected_top_level, f"{name} field set does not match the collector")
    _require(tree.get("schema_version") == "1.1", f"{name} schema must be 1.1")
    _require(
        tree.get("clock") == "android.os.SystemClock.uptimeMillis",
        f"{name} must use the collector monotonic clock",
    )
    _require(tree.get("start_uptime_ms") == expected_start, f"{name} start time mismatch")
    _require(tree.get("end_uptime_ms") == expected_end, f"{name} end time mismatch")
    reported_hash = _sha256_string(
        tree.get("canonical_tree_sha256"), f"{name}.canonical_tree_sha256"
    )
    _require(tree.get("contains_sensitive_node") is False, f"{name} contains sensitive nodes")
    _require(tree.get("truncated") is False, f"{name} is truncated")
    packages = tree.get("target_packages")
    _require(isinstance(packages, list), f"{name}.target_packages must be a list")
    forbidden = {
        "gold_label",
        "gold_labels",
        "prediction",
        "predictions",
        "method_prediction",
        "privacy_review_status",
        "paper_result_eligible",
    }
    _require(
        not _contains_key_recursive(tree, forbidden),
        f"{name} contains a human decision or prediction",
    )
    windows = tree.get("windows")
    _require(isinstance(windows, list) and windows, f"{name} must contain windows")
    node_ids: list[str] = []

    def visit(node: Any, path: str) -> None:
        node = _object(node, path)
        node_ids.append(_nonempty_string(node.get("id"), f"{path}.id"))
        children = node.get("children")
        _require(isinstance(children, list), f"{path}.children must be a list")
        for index, child in enumerate(children):
            visit(child, f"{path}.children[{index}]")

    for index, raw_window in enumerate(windows):
        window = _object(raw_window, f"{name}.windows[{index}]")
        _nonempty_string(window.get("id"), f"{name}.windows[{index}].id")
        _require(window.get("root") is not None, f"{name}.windows[{index}] has no root")
        visit(window.get("root"), f"{name}.windows[{index}].root")
    _require(len(node_ids) == len(set(node_ids)), f"{name} contains duplicate node ids")
    node_count = tree.get("node_count")
    _require(
        isinstance(node_count, int)
        and not isinstance(node_count, bool)
        and node_count == len(node_ids)
        and node_count > 0,
        f"{name} node_count mismatch",
    )
    commitment = _collector_tree_commitment(tree)
    recomputed_hash = commitment["sha256"]
    _require(
        recomputed_hash == reported_hash,
        f"{name} recomputed canonical tree hash does not match its self-report",
    )
    _require(
        recomputed_hash == expected_hash,
        f"{name} recomputed canonical tree hash does not match machine timing",
    )
    _require(
        packages == commitment["target_packages"],
        f"{name} target_packages do not match node packages",
    )
    _require(expected_package in packages, f"{name} does not contain the expected target package")
    _require(
        tree.get("focus_token") == commitment["focus_token"] == expected_focus,
        f"{name} focus token does not match focused nodes or machine timing",
    )
    _require(
        commitment["password_node_present"] is False,
        f"{name} contains a password node despite a negative sensitive-node summary",
    )
    return node_count, len(windows)


def finalize_collector_bundle(bundle_root: Path) -> dict[str, Any]:
    """Validate a V1.1 app-private collector bundle plus separate human review."""

    bundle_root = Path(bundle_root)
    _require(bundle_root.is_dir() and not bundle_root.is_symlink(), "collector bundle must be a directory")
    request = _read_json_file(bundle_root / "request.json", "request.json")
    machine = _read_json_file(bundle_root / "machine-capture.json", "machine-capture.json")
    review = _read_json_file(bundle_root / "review.json", "review.json")
    attestation = _read_json_file(
        bundle_root / "collector-attestation.json", "collector-attestation.json"
    )
    _validate_collector_request(request)

    forbidden_machine = {
        "privacy_review_status",
        "gold_label",
        "gold_labels",
        "prediction",
        "predictions",
        "method_prediction",
        "paper_result_eligible",
    }
    _require(
        not _contains_key_recursive(machine, forbidden_machine),
        "machine capture contains a human decision or prediction",
    )
    _require(machine.get("schema_version") == "1.1", "machine schema must be 1.1")
    _require(machine.get("collector") == "pmab-android-accessibilityservice", "unexpected collector")
    _require(machine.get("machine_status") == "complete", "machine capture is not complete")
    _require(machine.get("machine_reason") == "accepted", "machine capture was not accepted")
    _require(machine.get("request") == request, "machine request binding mismatch")
    _require(
        machine.get("clock") == "android.os.SystemClock.uptimeMillis",
        "machine capture must use the collector monotonic clock",
    )

    runtime = _object(machine.get("runtime"), "machine.runtime")
    capabilities = runtime.get("service_capabilities")
    flags = runtime.get("service_flags")
    _require(isinstance(capabilities, int) and not isinstance(capabilities, bool), "service capabilities missing")
    _require(capabilities & 0x01 and capabilities & 0x80, "collector lacks tree or screenshot capability")
    _require(isinstance(flags, int) and not isinstance(flags, bool), "service flags missing")
    _require(flags & 0x10 and flags & 0x40, "collector lacks window or view-id flags")
    source_revision = _nonempty_string(runtime.get("source_revision"), "runtime.source_revision")
    _require(
        len(source_revision) == 40
        and all(character in "0123456789abcdef" for character in source_revision),
        "collector source revision must be a 40-character Git commit",
    )
    device = _object(runtime.get("device"), "runtime.device")
    for field in ("manufacturer", "model", "android_release"):
        _nonempty_string(device.get(field), f"runtime.device.{field}")
    for field in ("display_width_px", "display_height_px"):
        _positive_integer(device.get(field), f"runtime.device.{field}")
    target_app = _object(runtime.get("target_app"), "runtime.target_app")
    _require(
        target_app.get("package_name") == request["expected_target_package"],
        "runtime target app does not match the request",
    )
    _nonempty_string(target_app.get("version_name"), "runtime.target_app.version_name")
    target_version_code = target_app.get("version_code")
    _require(
        isinstance(target_version_code, int)
        and not isinstance(target_version_code, bool)
        and target_version_code >= 0,
        "runtime.target_app.version_code must be non-negative",
    )
    collector_app = _object(runtime.get("collector_app"), "runtime.collector_app")
    _require(
        collector_app.get("package_name") == "org.pmab.collector",
        "runtime collector app package mismatch",
    )
    _nonempty_string(collector_app.get("version_name"), "runtime.collector_app.version_name")
    collector_version_code = collector_app.get("version_code")
    _require(
        isinstance(collector_version_code, int)
        and not isinstance(collector_version_code, bool)
        and collector_version_code >= 0,
        "runtime.collector_app.version_code must be non-negative",
    )
    _nonempty_string(runtime.get("locale"), "runtime.locale")

    timing = _object(machine.get("timing"), "machine.timing")
    time_fields = (
        "tree_before_start_uptime_ms",
        "tree_before_end_uptime_ms",
        "screenshot_request_uptime_ms",
        "screenshot_result_uptime_ms",
        "screenshot_callback_uptime_ms",
        "tree_after_start_uptime_ms",
        "tree_after_end_uptime_ms",
    )
    times = [timing.get(field) for field in time_fields]
    _require(
        all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in times),
        "collector timing fields must be non-negative integers",
    )
    _require(times == sorted(times), "collector timing has invalid monotonic order")
    before_hash = _sha256_string(timing.get("tree_before_sha256"), "tree_before_sha256")
    after_hash = _sha256_string(timing.get("tree_after_sha256"), "tree_after_sha256")
    _require(before_hash == after_hash, "tree hash drift detected")
    _require(
        timing.get("event_sequence_before") == timing.get("event_sequence_after"),
        "accessibility event sequence drift detected",
    )
    _require(
        timing.get("focus_token_before") == timing.get("focus_token_after"),
        "screen-reader focus drift detected",
    )
    before_distance = timing["screenshot_result_uptime_ms"] - timing["tree_before_end_uptime_ms"]
    after_distance = timing["tree_after_start_uptime_ms"] - timing["screenshot_result_uptime_ms"]
    delta_ms = max(before_distance, after_distance)
    _require(
        delta_ms <= MAX_SYNCHRONIZATION_DELTA_MS,
        f"synchronization delta exceeds {MAX_SYNCHRONIZATION_DELTA_MS} ms",
    )

    artifacts = _object(machine.get("artifacts"), "machine.artifacts")
    _require(
        set(artifacts) == {"tree_before", "tree_after", "screenshot"},
        "machine artifact set mismatch",
    )
    _, before_bytes = _validate_machine_artifact(
        bundle_root, artifacts, "tree_before", "tree-before.json"
    )
    _, after_bytes = _validate_machine_artifact(
        bundle_root, artifacts, "tree_after", "tree-after.json"
    )
    _, screenshot_bytes = _validate_machine_artifact(
        bundle_root, artifacts, "screenshot", "screenshot.png"
    )
    _validate_screenshot(screenshot_bytes)
    try:
        before_tree = _object(json.loads(before_bytes.decode("utf-8")), "tree-before.json")
        after_tree = _object(json.loads(after_bytes.decode("utf-8")), "tree-after.json")
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("collector trees must be valid UTF-8 JSON") from error
    before_count, before_windows = _validate_collector_tree(
        before_tree,
        expected_hash=before_hash,
        expected_package=request["expected_target_package"],
        expected_start=timing["tree_before_start_uptime_ms"],
        expected_end=timing["tree_before_end_uptime_ms"],
        expected_focus=timing["focus_token_before"],
        name="tree-before.json",
    )
    after_count, after_windows = _validate_collector_tree(
        after_tree,
        expected_hash=after_hash,
        expected_package=request["expected_target_package"],
        expected_start=timing["tree_after_start_uptime_ms"],
        expected_end=timing["tree_after_end_uptime_ms"],
        expected_focus=timing["focus_token_after"],
        name="tree-after.json",
    )
    _require(
        before_count == after_count and before_windows == after_windows,
        "tree summary drift detected",
    )

    _require(review.get("schema_version") == "1.1", "review schema must be 1.1")
    _require(review.get("capture_id") == request["capture_id"], "review capture binding mismatch")
    _nonempty_string(review.get("reviewer_id"), "review.reviewer_id")
    _parse_time(review.get("reviewed_at"), "review.reviewed_at")
    _require(review.get("collection_authorized") is True, "collection must be authorized")
    _nonempty_string(review.get("basis"), "review.basis")
    _require(review.get("privacy_review_status") == "passed", "privacy review must be passed")
    redistribution = review.get("redistribution_status")
    _require(
        redistribution in {"public_media", "adapter_only"},
        "redistribution_status must be public_media or adapter_only",
    )
    screen_reader = _object(review.get("screen_reader"), "review.screen_reader")
    _require(screen_reader.get("enabled") is True, "screen reader must be enabled")
    screen_reader_name = _nonempty_string(screen_reader.get("name"), "screen_reader.name")
    screen_reader_version = _nonempty_string(screen_reader.get("version"), "screen_reader.version")
    _require(review.get("human_gold_added") is False, "review must not add human gold")
    _require(review.get("method_predictions_added") is False, "review must not add predictions")
    apk_sha256 = _sha256_string(review.get("collector_apk_sha256"), "collector_apk_sha256")
    certificate_sha256 = _sha256_string(
        review.get("collector_signing_certificate_sha256"),
        "collector_signing_certificate_sha256",
    )
    _require(
        not _contains_key_recursive(attestation, forbidden_machine),
        "collector attestation contains a human decision or prediction",
    )
    _require(attestation.get("schema_version") == "1.1", "attestation schema must be 1.1")
    _require(attestation.get("status") == "verified", "collector attestation is not verified")
    _require(
        attestation.get("capture_id") == request["capture_id"],
        "collector attestation capture binding mismatch",
    )
    _require(
        attestation.get("source_revision") == source_revision,
        "collector attestation source binding mismatch",
    )
    local_apk_sha256 = _sha256_string(
        attestation.get("local_apk_sha256"), "attestation.local_apk_sha256"
    )
    installed_apk_sha256 = _sha256_string(
        attestation.get("installed_apk_sha256"), "attestation.installed_apk_sha256"
    )
    attested_certificate_sha256 = _sha256_string(
        attestation.get("signing_certificate_sha256"),
        "attestation.signing_certificate_sha256",
    )
    _sha256_string(
        attestation.get("device_serial_sha256"), "attestation.device_serial_sha256"
    )
    _parse_time(attestation.get("verified_at"), "attestation.verified_at")
    _require(
        local_apk_sha256 == installed_apk_sha256 == apk_sha256,
        "collector APK review/attestation hashes do not match",
    )
    _require(
        attested_certificate_sha256 == certificate_sha256,
        "collector signing-certificate review/attestation hashes do not match",
    )

    return {
        "capture_schema_version": COLLECTOR_CAPTURE_SCHEMA_VERSION,
        "status": "eligible_for_capture_feasibility",
        "capture_id": request["capture_id"],
        "item_id": request["item_id"],
        "source_group_id": request["source_group_id"],
        "popup_template_family_id": request["popup_template_family_id"],
        "intended_stratum": request["intended_stratum"],
        "collector_mode": "accessibilityservice_node_snapshot",
        "authorization_summary": {
            "collection_authorized": True,
            "privacy_review_status": "passed",
            "redistribution_status": redistribution,
        },
        "screen_reader_summary": {
            "enabled": True,
            "name": screen_reader_name,
            "version": screen_reader_version,
        },
        "collector_attestation": {
            "source_revision": source_revision,
            "apk_sha256": apk_sha256,
            "signing_certificate_sha256": certificate_sha256,
        },
        "synchronization": {
            "delta_ms": delta_ms,
            "maximum_delta_ms": MAX_SYNCHRONIZATION_DELTA_MS,
            "stable_state_verified": True,
            "tree_hash_verified": True,
            "event_sequence_verified": True,
            "focus_verified": True,
            "clock": "android.os.SystemClock.uptimeMillis",
        },
        "artifacts": {
            "screenshot_sha256": _sha256(screenshot_bytes),
            "screenshot_size_bytes": len(screenshot_bytes),
            "accessibility_snapshot_sha256": before_hash,
            "accessibility_snapshot_size_bytes": len(before_bytes) + len(after_bytes),
            "tree_before_file_sha256": _sha256(before_bytes),
            "tree_after_file_sha256": _sha256(after_bytes),
        },
        "accessibility_summary": {
            "node_count": before_count,
            "window_count": before_windows,
        },
        "paper_result_eligible": False,
        "human_gold_count": 0,
    }


def _positive_integer(value: Any, name: str) -> int:
    _require(
        isinstance(value, int) and not isinstance(value, bool) and value > 0,
        f"{name} must be a positive integer",
    )
    return value


def _sha256_string(value: Any, name: str) -> str:
    digest = _nonempty_string(value, name)
    _require(
        len(digest) == 64 and all(character in "0123456789abcdef" for character in digest),
        f"{name} must be a lowercase SHA-256 digest",
    )
    return digest


def _validate_finalized_record(record: dict[str, Any], index: int) -> None:
    prefix = f"records[{index}]"
    _require(
        record.get("capture_schema_version")
        in {CAPTURE_SCHEMA_VERSION, COLLECTOR_CAPTURE_SCHEMA_VERSION},
        f"{prefix} has an invalid capture schema version",
    )
    _require(
        record.get("status") == "eligible_for_capture_feasibility",
        f"{prefix} is not capture-feasibility eligible",
    )
    for field in (
        "capture_id",
        "item_id",
        "source_group_id",
        "popup_template_family_id",
    ):
        _nonempty_string(record.get(field), f"{prefix}.{field}")
    _require(
        record.get("intended_stratum") in ALLOWED_STRATA,
        f"{prefix}.intended_stratum is outside the frozen V1 strata",
    )
    _require(
        record.get("collector_mode") == "accessibilityservice_node_snapshot",
        f"{prefix} must originate from an AccessibilityService snapshot",
    )
    _require(
        record.get("paper_result_eligible") is False,
        f"{prefix} must remain paper-result ineligible",
    )
    _require(record.get("human_gold_count") == 0, f"{prefix} must have zero human-gold labels")

    authorization = _object(record.get("authorization_summary"), f"{prefix}.authorization_summary")
    _require(
        authorization.get("collection_authorized") is True
        and authorization.get("privacy_review_status") == "passed"
        and authorization.get("redistribution_status") in {"public_media", "adapter_only"},
        f"{prefix} does not satisfy the authorization and privacy gate",
    )
    synchronization = _object(record.get("synchronization"), f"{prefix}.synchronization")
    delta_ms = synchronization.get("delta_ms")
    _require(
        isinstance(delta_ms, int)
        and not isinstance(delta_ms, bool)
        and 0 <= delta_ms <= MAX_SYNCHRONIZATION_DELTA_MS
        and synchronization.get("maximum_delta_ms") == MAX_SYNCHRONIZATION_DELTA_MS
        and synchronization.get("stable_state_verified") is True,
        f"{prefix} does not satisfy the synchronization gate",
    )
    artifacts = _object(record.get("artifacts"), f"{prefix}.artifacts")
    _sha256_string(artifacts.get("screenshot_sha256"), f"{prefix}.screenshot_sha256")
    _sha256_string(
        artifacts.get("accessibility_snapshot_sha256"),
        f"{prefix}.accessibility_snapshot_sha256",
    )
    _positive_integer(artifacts.get("screenshot_size_bytes"), f"{prefix}.screenshot_size_bytes")
    _positive_integer(
        artifacts.get("accessibility_snapshot_size_bytes"),
        f"{prefix}.accessibility_snapshot_size_bytes",
    )
    summary = _object(record.get("accessibility_summary"), f"{prefix}.accessibility_summary")
    _positive_integer(summary.get("node_count"), f"{prefix}.node_count")
    _positive_integer(summary.get("window_count"), f"{prefix}.window_count")


def audit_feasibility(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Audit only capture coverage; this cannot unlock paper-result claims."""

    _require(isinstance(records, list), "records must be a list")
    _require(records, "at least one capture record is required")
    for index, record in enumerate(records):
        _require(isinstance(record, dict), f"records[{index}] must be an object")
        _validate_finalized_record(record, index)

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


def audit_metadata_bundles(metadata_list_path: Path) -> dict[str, Any]:
    """Re-finalize private bundles before applying the aggregate coverage gate."""

    metadata_list_path = Path(metadata_list_path)
    _require(metadata_list_path.is_file(), "metadata list does not exist")
    try:
        entries = json.loads(metadata_list_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("metadata list must be valid UTF-8 JSON") from error
    _require(isinstance(entries, list) and entries, "metadata list must be a non-empty JSON array")
    root = metadata_list_path.resolve().parent
    paths = [
        _resolve_artifact(root, entry, f"metadata_list[{index}]")
        for index, entry in enumerate(entries)
    ]
    _require(len(paths) == len(set(paths)), "metadata list contains duplicate bundle paths")
    return audit_feasibility([finalize_capture(path) for path in paths])


def audit_collector_bundles(bundle_list_path: Path) -> dict[str, Any]:
    """Re-finalize V1.1 collector directories before the aggregate gate."""

    bundle_list_path = Path(bundle_list_path)
    _require(bundle_list_path.is_file(), "bundle list does not exist")
    try:
        entries = json.loads(bundle_list_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("bundle list must be valid UTF-8 JSON") from error
    _require(isinstance(entries, list) and entries, "bundle list must be a non-empty JSON array")
    root = bundle_list_path.resolve().parent
    resolved_root = root.resolve()
    paths: list[Path] = []
    for index, entry in enumerate(entries):
        relative = Path(_nonempty_string(entry, f"bundle_list[{index}]"))
        _require(not relative.is_absolute(), f"bundle_list[{index}] must be relative")
        _require(".." not in relative.parts, f"bundle_list[{index}] must not escape its root")
        path = root / relative
        _require(not path.is_symlink(), f"bundle_list[{index}] must not be a symlink")
        resolved = path.resolve()
        _require(resolved_root in resolved.parents, f"bundle_list[{index}] escapes its root")
        _require(resolved.is_dir(), f"bundle_list[{index}] is not a bundle directory")
        paths.append(resolved)
    _require(len(paths) == len(set(paths)), "bundle list contains duplicate paths")
    return audit_feasibility([finalize_collector_bundle(path) for path in paths])


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
    collector_parser = subparsers.add_parser(
        "finalize-collector", help="finalize one V1.1 collector bundle"
    )
    collector_parser.add_argument("--bundle", required=True, type=Path)
    collector_parser.add_argument("--output", required=True, type=Path)
    audit_parser = subparsers.add_parser(
        "audit", help="re-finalize private bundles and audit aggregate coverage"
    )
    audit_parser.add_argument("--metadata-list", required=True, type=Path)
    audit_parser.add_argument("--output", required=True, type=Path)
    collector_audit_parser = subparsers.add_parser(
        "audit-collector", help="re-finalize V1.1 collector bundles and audit coverage"
    )
    collector_audit_parser.add_argument("--bundle-list", required=True, type=Path)
    collector_audit_parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args(argv)

    try:
        if arguments.command == "finalize":
            result = finalize_capture(arguments.metadata)
        elif arguments.command == "finalize-collector":
            result = finalize_collector_bundle(arguments.bundle)
        elif arguments.command == "audit":
            result = audit_metadata_bundles(arguments.metadata_list)
        else:
            result = audit_collector_bundles(arguments.bundle_list)
        _write_json(arguments.output, result)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        parser.exit(2, f"capture finalization failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
