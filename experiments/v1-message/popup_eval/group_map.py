"""Build a private pilot cluster map from frozen source and content keys."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from .io import read_jsonl


PILOT_ID_PATTERN = re.compile(r"PMJ-PILOT-\d{3}")
CLUSTER_SOURCE = "pilot_manifest_group_content_connected_components_v1"


class GroupMapError(ValueError):
    pass


def _atomic_write(path: Path, payload: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if "private" in path.name or path.parent.name == "private":
        path.parent.chmod(0o700)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.chmod(mode)
    os.replace(temporary, path)


def _canonical_jsonl(rows: list[dict[str, Any]]) -> bytes:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    ).encode("utf-8")


def _build(rows: list[dict[str, Any]], expected_count: int) -> tuple[list[dict[str, str]], dict[str, Any]]:
    if len(rows) != expected_count:
        raise GroupMapError(
            f"manifest item count {len(rows)} does not match expected_count {expected_count}"
        )
    by_id: dict[str, dict[str, str]] = {}
    for row in rows:
        pilot_id = row.get("pilot_item_id")
        group_key = row.get("group_key")
        content_key = row.get("content_key")
        if not isinstance(pilot_id, str) or PILOT_ID_PATTERN.fullmatch(pilot_id) is None:
            raise GroupMapError("manifest row has invalid pilot_item_id")
        if pilot_id in by_id:
            raise GroupMapError(f"duplicate manifest pilot_item_id: {pilot_id}")
        if not isinstance(group_key, str) or not group_key.strip():
            raise GroupMapError(f"{pilot_id}: group_key is required")
        if not isinstance(content_key, str) or not content_key.strip():
            raise GroupMapError(f"{pilot_id}: content_key is required")
        by_id[pilot_id] = {"group_key": group_key, "content_key": content_key}

    parent = {pilot_id: pilot_id for pilot_id in by_id}

    def find(pilot_id: str) -> str:
        while parent[pilot_id] != pilot_id:
            parent[pilot_id] = parent[parent[pilot_id]]
            pilot_id = parent[pilot_id]
        return pilot_id

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    first_by_group: dict[str, str] = {}
    first_by_content: dict[str, str] = {}
    for pilot_id in sorted(by_id):
        group_key = by_id[pilot_id]["group_key"]
        content_key = by_id[pilot_id]["content_key"]
        if group_key in first_by_group:
            union(pilot_id, first_by_group[group_key])
        else:
            first_by_group[group_key] = pilot_id
        if content_key in first_by_content:
            union(pilot_id, first_by_content[content_key])
        else:
            first_by_content[content_key] = pilot_id

    members_by_root: dict[str, list[str]] = {}
    for pilot_id in sorted(by_id):
        members_by_root.setdefault(find(pilot_id), []).append(pilot_id)
    cluster_by_pilot: dict[str, str] = {}
    for members in members_by_root.values():
        member_digest = hashlib.sha256("\n".join(sorted(members)).encode("ascii")).hexdigest()
        cluster_id = f"cluster:{member_digest[:16]}"
        for pilot_id in members:
            cluster_by_pilot[pilot_id] = cluster_id

    private_rows = [
        {
            "pilot_item_id": pilot_id,
            "cluster_id": cluster_by_pilot[pilot_id],
            "cluster_source": CLUSTER_SOURCE,
        }
        for pilot_id in sorted(by_id)
    ]
    cluster_sizes = Counter(cluster_by_pilot.values())
    group_counts = Counter(value["group_key"] for value in by_id.values())
    content_counts = Counter(value["content_key"] for value in by_id.values())
    summary = {
        "contract_version": "popup-message-pilot-group-map-v1.0",
        "algorithm": CLUSTER_SOURCE,
        "counts": {
            "items": len(private_rows),
            "clusters": len(cluster_sizes),
            "largest_cluster_items": max(cluster_sizes.values()),
            "shared_group_keys": sum(count > 1 for count in group_counts.values()),
            "shared_content_keys": sum(count > 1 for count in content_counts.values()),
        },
        "negative_claims": {
            "used_as_model_input": False,
            "formal_leakage_control_sufficient": False,
            "paper_result_eligible": False,
        },
    }
    return private_rows, summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--public-summary", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, default=30)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        manifest_bytes = args.manifest.read_bytes()
        private_rows, summary = _build(read_jsonl(args.manifest), args.expected_count)
        private_payload = _canonical_jsonl(private_rows)
        summary["hashes"] = {
            "input_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "private_group_map_sha256": hashlib.sha256(private_payload).hexdigest(),
        }
        _atomic_write(args.private_output, private_payload, 0o600)
        _atomic_write(
            args.public_summary,
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
            + b"\n",
            0o644,
        )
    except (GroupMapError, OSError, ValueError) as error:
        print(f"error: {error}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
