#!/usr/bin/env python3
"""Build a deterministic, adapter-only PopSweeper candidate manifest.

The script reads ZIP metadata only. It never extracts or redistributes images and
does not claim that PopSweeper's presence labels are popup-message annotations.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


MEMBER_PATTERN = re.compile(
    r"^app-blocking pop-ups/basic/"
    r"(?P<split>train|valid|test)/"
    r"(?P<label>ads|no_ads)/"
    r"(?P<filename>[^/]+\.jpg)$"
)
SOURCE_DOI = "10.5281/zenodo.13754620"
RICO_SOURCE_URL = "https://www.interactionmining.org/archive/rico"
SPLIT_PRIORITY = {"train": 0, "valid": 1, "test": 2}


def discover_candidates(archive_path: Path) -> list[dict[str, Any]]:
    """Return one source candidate per real JPG member in the basic archive."""

    candidates: list[dict[str, Any]] = []
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            match = MEMBER_PATTERN.fullmatch(info.filename)
            if match is None or info.is_dir():
                continue
            split = match.group("split")
            label = match.group("label")
            filename = match.group("filename")
            basename = filename[:-4]
            source_kind = (
                "rico_numeric_candidate"
                if basename.isdigit()
                else "recorded_app_frame"
            )
            group_key = (
                f"rico:{basename}"
                if source_kind == "rico_numeric_candidate"
                else "recording:" + re.sub(r"_frame\d+$", "", basename)
            )
            candidates.append(
                {
                    "source_record_id": f"popsweeper:{split}:{label}:{basename}",
                    "source_dataset": "PopSweeper basic",
                    "source_record": 13754620,
                    "source_doi": SOURCE_DOI,
                    "archive_member_path": info.filename,
                    "archive_member_crc32": f"{info.CRC:08x}",
                    "archive_member_compressed_bytes": info.compress_size,
                    "archive_member_uncompressed_bytes": info.file_size,
                    "official_split": split,
                    "source_label": label,
                    "popup_present_gt": label == "ads",
                    "source_basename": basename,
                    "source_kind": source_kind,
                    "source_kind_provenance": "inferred_from_filename_and_reported_counts",
                    "content_key": f"crc32:{info.CRC:08x}:bytes:{info.file_size}",
                    "group_key": group_key,
                    "rico_join_status": (
                        "candidate_id_unverified"
                        if source_kind == "rico_numeric_candidate"
                        else "not_applicable"
                    ),
                    "message_annotation_status": "pending",
                    "eligible_for_v1_message_metrics": False,
                    "raw_image_distribution": "adapter_only_not_redistributed",
                }
            )
    return sorted(candidates, key=lambda row: row["source_record_id"])


def deduplicate_candidates(
    candidates: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Keep one deterministic record per content and per source group."""

    ordered = sorted(
        candidates,
        key=lambda row: (
            SPLIT_PRIORITY.get(row.get("official_split", ""), 99),
            row["source_record_id"],
        ),
    )
    seen_content: set[str] = set()
    content_unique: list[dict[str, Any]] = []
    removed_exact_content = 0
    for row in ordered:
        content_key = row.get("content_key", row["source_record_id"])
        if content_key in seen_content:
            removed_exact_content += 1
            continue
        seen_content.add(content_key)
        content_unique.append(row)

    seen_groups: set[str] = set()
    group_unique: list[dict[str, Any]] = []
    removed_group_leakage = 0
    for row in content_unique:
        group_key = row.get("group_key", row["source_record_id"])
        if group_key in seen_groups:
            removed_group_leakage += 1
            continue
        seen_groups.add(group_key)
        group_unique.append(row)

    return sorted(group_unique, key=lambda row: row["source_record_id"]), {
        "input_candidates": len(ordered),
        "removed_exact_content": removed_exact_content,
        "removed_group_leakage": removed_group_leakage,
        "deduplicated_candidates": len(group_unique),
    }


def n120_audit_quotas() -> dict[tuple[str, str, str], int]:
    """Freeze the audit-balanced 72/24/24 split-label-kind allocation."""

    quotas: dict[tuple[str, str, str], int] = {}
    for split, numeric, named in (
        ("train", 27, 9),
        ("valid", 9, 3),
        ("test", 9, 3),
    ):
        for label in ("ads", "no_ads"):
            quotas[(split, label, "rico_numeric_candidate")] = numeric
            quotas[(split, label, "recorded_app_frame")] = named
    return quotas


def load_complete_rico_ids(archive_path: Path) -> set[str]:
    """Return RICO IDs that have both semantic JSON and semantic PNG members."""

    extensions_by_id: dict[str, set[str]] = defaultdict(set)
    pattern = re.compile(r"^semantic_annotations/(?P<id>\d+)\.(?P<ext>json|png)$")
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            match = pattern.fullmatch(info.filename)
            if match is not None and not info.is_dir():
                extensions_by_id[match.group("id")].add(match.group("ext"))
    return {
        source_id
        for source_id, extensions in extensions_by_id.items()
        if extensions == {"json", "png"}
    }


def apply_rico_join(
    candidates: Iterable[dict[str, Any]], rico_ids: set[str]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Attach verified RICO semantic-member availability to numeric candidates."""

    joined: list[dict[str, Any]] = []
    counts = Counter()
    for candidate in candidates:
        row = dict(candidate)
        if row["source_kind"] != "rico_numeric_candidate":
            row["rico_join_status"] = "not_applicable"
            counts["not_applicable"] += 1
        elif row["source_basename"] in rico_ids:
            source_id = row["source_basename"]
            row["rico_join_status"] = "verified_json_png"
            row["rico_semantic_json_member"] = (
                f"semantic_annotations/{source_id}.json"
            )
            row["rico_semantic_png_member"] = f"semantic_annotations/{source_id}.png"
            row["rico_source_url"] = RICO_SOURCE_URL
            row["rico_raw_distribution"] = "adapter_only_not_redistributed"
            counts["numeric_verified"] += 1
        else:
            row["rico_join_status"] = "not_found"
            counts["numeric_not_found"] += 1
        joined.append(row)
    return joined, dict(sorted(counts.items()))


def stratified_sample(
    candidates: Iterable[dict[str, Any]],
    *,
    per_stratum: dict[tuple[str, ...], int],
    seed: int,
    key_fields: tuple[str, ...] = ("source_label", "source_kind"),
) -> list[dict[str, Any]]:
    """Sample exact label/source-kind quotas, independent of input order."""

    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        key = tuple(candidate[field] for field in key_fields)
        groups[key].append(candidate)

    selected: list[dict[str, Any]] = []
    for key in sorted(per_stratum):
        requested = per_stratum[key]
        population = sorted(groups.get(key, []), key=lambda row: row["source_record_id"])
        if len(population) < requested:
            raise ValueError(
                "insufficient candidates for "
                f"{key[0]}/{key[1]}: requested {requested}, available {len(population)}"
            )
        rng = random.Random(f"{seed}:" + ":".join(key))
        for candidate in rng.sample(population, requested):
            row = dict(candidate)
            row["sampling_seed"] = seed
            row["sampling_stratum"] = "/".join(key)
            row["stratum_available_after_deduplication"] = len(population)
            row["stratum_selected"] = requested
            row["selection_probability"] = requested / len(population)
            row["sampling_weight"] = len(population) / requested
            selected.append(row)

    return sorted(selected, key=lambda row: row["source_record_id"])


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--per-label", type=int, default=60)
    parser.add_argument("--named-per-label", type=int, default=12)
    parser.add_argument("--seed", type=int, default=20260901)
    parser.add_argument(
        "--profile",
        choices=("label_kind", "n120_audit"),
        default="label_kind",
    )
    parser.add_argument("--rico-archive", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.per_label <= 0:
        raise SystemExit("--per-label must be positive")
    if args.named_per_label < 0 or args.named_per_label > args.per_label:
        raise SystemExit("--named-per-label must be between 0 and --per-label")

    discovered = discover_candidates(args.archive)
    candidates, deduplication = deduplicate_candidates(discovered)
    rico_join_inventory = None
    if args.rico_archive is not None:
        rico_ids = load_complete_rico_ids(args.rico_archive)
        candidates, rico_join_inventory = apply_rico_join(candidates, rico_ids)
    if args.profile == "n120_audit":
        quotas = n120_audit_quotas()
        key_fields = ("official_split", "source_label", "source_kind")
    else:
        numeric_per_label = args.per_label - args.named_per_label
        quotas = {
            (label, kind): count
            for label in ("ads", "no_ads")
            for kind, count in (
                ("rico_numeric_candidate", numeric_per_label),
                ("recorded_app_frame", args.named_per_label),
            )
        }
        key_fields = ("source_label", "source_kind")
    selected = stratified_sample(
        candidates,
        per_stratum=quotas,
        seed=args.seed,
        key_fields=key_fields,
    )
    if args.rico_archive is not None:
        _, rico_join_selected = apply_rico_join(selected, rico_ids)
    else:
        rico_join_selected = None
    write_jsonl(args.output, selected)

    inventory_counts = Counter(
        f"{row['source_label']}/{row['source_kind']}" for row in candidates
    )
    selected_counts = Counter(
        f"{row['source_label']}/{row['source_kind']}" for row in selected
    )
    summary = {
        "source_dataset": "PopSweeper basic",
        "source_record": 13754620,
        "source_doi": SOURCE_DOI,
        "source_archive": args.archive.name,
        "archive_image_count": len(discovered),
        "inventory_count_after_deduplication": len(candidates),
        "inventory_by_label_and_kind": dict(sorted(inventory_counts.items())),
        "deduplication": deduplication,
        "rico_join_inventory": rico_join_inventory,
        "rico_join_selected": rico_join_selected,
        "rico_source_url": RICO_SOURCE_URL if args.rico_archive is not None else None,
        "candidate_count": len(selected),
        "selected_by_label_and_kind": dict(sorted(selected_counts.items())),
        "sampling_seed": args.seed,
        "sampling_profile": args.profile,
        "sampling_purpose": "audit_balanced_not_natural_prevalence",
        "official_split_usage": "audit_stratum_only_not_final_leakage_safe_split",
        "use_sampling_weights_for_source_population_estimates": True,
        "per_label": args.per_label,
        "named_per_label": 15 if args.profile == "n120_audit" else args.named_per_label,
        "raw_image_distribution": "adapter_only_not_redistributed",
        "message_annotation_status": "pending",
        "empirical_message_dataset_complete": False,
        "eligible_for_v1_message_metrics": False,
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
