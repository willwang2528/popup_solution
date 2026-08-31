#!/usr/bin/env python3
"""Freeze gold-blind structured features for the 30-item PMJ pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable


CONTRACT_VERSION = "pmj-pilot-structured-features-v1.0"
PILOT_ID_PATTERN = re.compile(r"PMJ-PILOT-\d{3}")
MANIFEST_ALLOWLIST = {"pilot_item_id"}
FORBIDDEN_FIELDS_NOT_CONSUMED = [
    "adapter_item_handle",
    "archive_member",
    "archive_member_path",
    "artifacts",
    "batch_id",
    "content",
    "content_group",
    "content_label",
    "coordinator_display_order",
    "eligible_for_v1_message_metrics",
    "group",
    "group_label",
    "message_annotation_status",
    "official_split",
    "official_split_label",
    "official_split_name",
    "pilot_index",
    "popup_present_gt",
    "protocol_version",
    "sampling_stratum",
    "selection_seed",
    "source_kind",
    "source_label",
    "source_record",
    "source_record_id",
    "source_sampling_label",
]
SOURCE_TO_FEATURE = {
    "class": "class",
    "bounds": "bounds",
    "clickable": "clickable",
    "ancestors": "ancestors",
    "resource-id": "resource_id",
    "text": "text",
    "componentLabel": "component_label",
    "iconClass": "icon_class",
    "textButtonClass": "text_button_class",
}


class DuplicateKeyError(ValueError):
    """Raised when a JSON object contains a duplicate key."""


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(text: str) -> Any:
    return json.loads(text, object_pairs_hook=_strict_pairs)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _manifest_ids(manifest_path: Path) -> list[str]:
    item_ids: list[str] = []
    for line_number, line in enumerate(
        manifest_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        row = _load_json(line)
        if not isinstance(row, dict):
            raise ValueError(f"manifest line {line_number} must be a JSON object")
        # Strict allowlist: no other manifest field is copied, inspected, or routed on.
        selected = {key: row[key] for key in MANIFEST_ALLOWLIST if key in row}
        item_id = selected.get("pilot_item_id")
        if not isinstance(item_id, str) or PILOT_ID_PATTERN.fullmatch(item_id) is None:
            raise ValueError(f"manifest line {line_number} has invalid pilot_item_id")
        item_ids.append(item_id)
    if not item_ids:
        raise ValueError("manifest has no pilot items")
    if len(item_ids) != len(set(item_ids)):
        raise ValueError("manifest pilot_item_id values must be unique")
    return sorted(item_ids)


def _node_values(node: dict[str, Any]) -> dict[str, Any]:
    return {target: node.get(source) for source, target in SOURCE_TO_FEATURE.items()}


def _is_visible(bounds: Any) -> bool:
    return (
        isinstance(bounds, list)
        and len(bounds) == 4
        and all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in bounds)
        and bounds[2] > bounds[0]
        and bounds[3] > bounds[1]
    )


def _display_text(features: dict[str, Any]) -> str | None:
    for key in ("text", "text_button_class", "icon_class"):
        value = features.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _flatten_nodes(root: dict[str, Any]) -> Iterable[tuple[int, dict[str, Any]]]:
    stack: list[tuple[int, dict[str, Any]]] = [(0, root)]
    while stack:
        depth, node = stack.pop()
        yield depth, node
        children = node.get("children", [])
        if isinstance(children, list):
            stack.extend(
                (depth + 1, child)
                for child in reversed(children)
                if isinstance(child, dict)
            )


def _build_candidates(item_id: str, semantic: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for node_index, (depth, node) in enumerate(_flatten_nodes(semantic)):
        features = _node_values(node)
        features.update(
            {
                "node_index": node_index,
                "depth": depth,
                "gap_reasons": [],
            }
        )
        candidates.append(
            {
                "candidate_id": f"{item_id}-structured-{node_index:04d}",
                "source_channel": "structured",
                "normalized": {
                    "name_or_text": _display_text(features),
                    "value_or_hint": None,
                    "visible": _is_visible(features["bounds"]),
                },
                "features": features,
            }
        )
    return candidates


def _build_item(item_id: str, batch_dir: Path) -> dict[str, Any]:
    semantic_path = batch_dir / item_id / "rico-semantic.json"
    resolved_batch_dir = batch_dir.resolve()
    resolved_semantic_path = semantic_path.resolve()
    if semantic_path.exists() and not resolved_semantic_path.is_relative_to(resolved_batch_dir):
        raise ValueError(f"{item_id}: rico-semantic.json escapes the manifest batch directory")
    if semantic_path.is_file():
        semantic_bytes = resolved_semantic_path.read_bytes()
        semantic = _load_json(semantic_bytes.decode("utf-8"))
        if not isinstance(semantic, dict):
            raise ValueError(f"{item_id}: rico-semantic.json root must be an object")
        candidates = _build_candidates(item_id, semantic)
        availability = "available"
        artifact_sha256: str | None = _sha256_bytes(semantic_bytes)
    else:
        candidates = []
        availability = "missing"
        artifact_sha256 = None

    observation_id = f"{item_id}-pre-action-structured"
    return {
        "identity": {
            "item_id": item_id,
            "pilot_item_id": item_id,
            "record_kind": "unscored_pregold_input",
        },
        "observations": [
            {
                "observation_id": observation_id,
                "phase": "pre_action",
                "structured_representation": {
                    "availability": availability,
                    "representation_kind": "rico-semantic-json",
                    "node_count": len(candidates),
                    "artifact_sha256": artifact_sha256,
                },
            }
        ],
        "candidates": candidates,
        "action_attempts": [],
        "decision": {"policy": {"decision": "no_action"}},
        "metadata": {
            "contract_version": CONTRACT_VERSION,
            "gold_blind": True,
            "gold_used": False,
            "scored": False,
            "paper_result_eligible": False,
            "action_mode": "no_action",
        },
    }


def _git_command(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _require_gitignored_private_output(manifest_path: Path, private_output: Path) -> None:
    repository = subprocess.run(
        ["git", "-C", str(manifest_path.parent), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if repository.returncode != 0:
        raise ValueError("manifest must be inside a Git worktree")
    repo_root = Path(repository.stdout.strip()).resolve()
    resolved_output = private_output.resolve()
    if not resolved_output.is_relative_to(repo_root):
        raise ValueError("--private-output must be inside the manifest Git worktree")
    if private_output.is_symlink():
        raise ValueError("--private-output must not be a symbolic link")

    output_relative = resolved_output.relative_to(repo_root).as_posix()
    if _git_command(repo_root, "ls-files", "--error-unmatch", "--", output_relative).returncode == 0:
        raise ValueError("--private-output must be gitignored and untracked")
    if (
        _git_command(
            repo_root,
            "check-ignore",
            "--quiet",
            "--no-index",
            "--",
            output_relative,
        ).returncode
        != 0
    ):
        raise ValueError("--private-output must be gitignored")

    private_output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    resolved_parent = private_output.parent.resolve()
    if not resolved_parent.is_relative_to(repo_root) or resolved_parent == repo_root:
        raise ValueError("--private-output requires a dedicated private directory")
    parent_relative = resolved_parent.relative_to(repo_root).as_posix()
    if (
        _git_command(
            repo_root,
            "check-ignore",
            "--quiet",
            "--no-index",
            "--",
            parent_relative,
        ).returncode
        != 0
    ):
        raise ValueError("--private-output directory must be gitignored")
    resolved_parent.chmod(0o700)


def _write_private(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(payload)
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _write_outputs(
    rows: list[dict[str, Any]], private_output: Path, public_summary: Path
) -> None:
    private_payload = b"".join(_canonical_bytes(row) + b"\n" for row in rows)
    _write_private(private_output, private_payload)

    availability = [
        row["observations"][0]["structured_representation"]["availability"]
        for row in rows
    ]
    node_count = sum(len(row["candidates"]) for row in rows)
    contract = {
        "name": "gold-blind pilot structured feature bundle",
        "version": CONTRACT_VERSION,
        "manifest_field_allowlist": sorted(MANIFEST_ALLOWLIST),
        "private_record_top_level_keys": [
            "identity",
            "observations",
            "candidates",
            "action_attempts",
            "decision",
            "metadata",
        ],
        "structured_source": "rico-semantic-json",
        "private_output_contains_ui_text": True,
        "public_output_contains_ui_text": False,
    }
    summary = {
        "contract": contract,
        "counts": {
            "items": len(rows),
            "structured_available": availability.count("available"),
            "structured_missing": availability.count("missing"),
            "structured_nodes": node_count,
        },
        "hashes": {
            "contract_sha256": _sha256_bytes(_canonical_bytes(contract)),
            "private_bundle_sha256": _sha256_bytes(private_payload),
        },
        "forbidden_fields_not_consumed": FORBIDDEN_FIELDS_NOT_CONSUMED,
        "gold_blind": True,
        "gold_used": False,
        "scored": False,
        "paper_result_eligible": False,
        "action_mode": "no_action",
    }
    public_summary.parent.mkdir(parents=True, exist_ok=True)
    public_summary.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--public-summary", type=Path, required=True)
    args = parser.parse_args()

    _require_gitignored_private_output(args.manifest, args.private_output)
    item_ids = _manifest_ids(args.manifest)
    rows = [_build_item(item_id, args.manifest.parent) for item_id in item_ids]
    _write_outputs(rows, args.private_output, args.public_summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
