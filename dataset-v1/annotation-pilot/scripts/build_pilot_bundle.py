#!/usr/bin/env python3
"""Materialize the frozen 30-item adapter-only annotation pilot bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


PROTOCOL_VERSION = "1.0.0"
BATCH_ID = "popsweeper-message-pilot-30-v1"
SELECTION_SEED = "pmj-pilot30-v1"
DISPLAY_SEED = "pmj-display-v1"
ROLE_ORDER_SEEDS = {"A": "pmj-annotator-A-v1", "B": "pmj-annotator-B-v1"}
QUOTAS = {
    (split, label, kind): count
    for label in ("ads", "no_ads")
    for split, counts in (
        ("train", (7, 2)),
        ("valid", (2, 1)),
        ("test", (2, 1)),
    )
    for kind, count in zip(
        ("rico_numeric_candidate", "recorded_app_frame"), counts, strict=True
    )
}


def stable_digest(seed: str, value: str) -> str:
    return hashlib.sha256(f"{seed}|{value}".encode("utf-8")).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: expected JSON object")
            rows.append(row)
    return rows


def select_fixed_batch(candidates: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {
        key: [] for key in QUOTAS
    }
    for candidate in candidates:
        key = (
            candidate.get("official_split"),
            candidate.get("source_label"),
            candidate.get("source_kind"),
        )
        if key in groups:
            groups[key].append(candidate)

    selected: list[dict[str, Any]] = []
    for key, requested in sorted(QUOTAS.items()):
        population = sorted(
            groups[key],
            key=lambda row: stable_digest(SELECTION_SEED, row["source_record_id"]),
        )
        if len(population) < requested:
            raise ValueError(
                f"insufficient candidates for {key}: "
                f"requested {requested}, available {len(population)}"
            )
        selected.extend(population[:requested])

    return sorted(
        selected,
        key=lambda row: stable_digest(DISPLAY_SEED, row["source_record_id"]),
    )


def build_manifest_rows(
    selected: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, candidate in enumerate(selected, start=1):
        pilot_item_id = f"PMJ-PILOT-{index:03d}"
        rows.append(
            {
                "protocol_version": PROTOCOL_VERSION,
                "batch_id": BATCH_ID,
                "pilot_item_id": pilot_item_id,
                "coordinator_display_order": index,
                "source_record_id": candidate["source_record_id"],
                "adapter_item_handle": f"adapter://popsweeper/pilot/{pilot_item_id}",
                "archive_member_path": candidate["archive_member_path"],
                "archive_member_crc32": candidate["archive_member_crc32"],
                "archive_member_uncompressed_bytes": candidate[
                    "archive_member_uncompressed_bytes"
                ],
                "content_key": candidate["content_key"],
                "group_key": candidate["group_key"],
                "official_split_audit_stratum": candidate["official_split"],
                "source_sampling_label": candidate["source_label"],
                "source_label_role": "sampling_only_not_human_message_gold",
                "source_kind": candidate["source_kind"],
                "selection_seed": f"sha256:{SELECTION_SEED}",
                "human_message_gold_status": "pending",
                "eligible_for_message_metrics": False,
                "raw_image_distribution": "adapter_only_not_redistributed",
            }
        )
    return rows


def build_blank_template_rows(
    manifest_rows: Iterable[dict[str, Any]], role: str
) -> list[dict[str, Any]]:
    if role not in ROLE_ORDER_SEEDS:
        raise ValueError("annotator role must be A or B")
    ordered = sorted(
        manifest_rows,
        key=lambda row: stable_digest(
            ROLE_ORDER_SEEDS[role], row["pilot_item_id"]
        ),
    )
    rows: list[dict[str, Any]] = []
    for annotation_order, manifest in enumerate(ordered, start=1):
        rows.append(
            {
                "protocol_version": PROTOCOL_VERSION,
                "batch_id": BATCH_ID,
                "pilot_item_id": manifest["pilot_item_id"],
                "annotation_order": annotation_order,
                "adapter_item_handle": manifest["adapter_item_handle"],
                "annotator_role": role,
                "annotator_id_pseudonymous": None,
                "record_status": "blank",
                "presence_label": None,
                "message_text": None,
                "message_observability": None,
                "semantic_slots": [],
                "confidence": None,
                "evidence": {
                    "adapter_viewed": None,
                    "view_session_id": None,
                    "region_or_node_notes": None,
                    "raw_image_copied": False,
                },
                "blindness_attestation": {
                    "peer_labels_unseen": None,
                    "source_class_unseen": None,
                    "model_output_unseen": None,
                },
                "annotation_started_at": None,
                "annotation_completed_at": None,
                "notes": None,
            }
        )
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    candidates = load_jsonl(args.candidates)
    selected = select_fixed_batch(candidates)
    manifest = build_manifest_rows(selected)
    write_jsonl(
        args.output_root / "manifests" / "pilot_batch_30.jsonl", manifest
    )
    for role in ("A", "B"):
        write_jsonl(
            args.output_root
            / "templates"
            / f"annotator_{role.lower()}.jsonl",
            build_blank_template_rows(manifest, role),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
