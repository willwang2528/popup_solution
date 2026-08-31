#!/usr/bin/env python3
"""Safely materialize local-only PopSweeper annotation media.

The adapter is deliberately fail-closed. It pins both source archives by
SHA-256, audits every ZIP member path, verifies every frozen candidate member
against the ZIP central directory, and only then writes a deterministic pilot
inside a Git-ignored directory. Raw third-party media remains local.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, BinaryIO, Iterable


MAX_ARCHIVE_MEMBERS = 200_000
MAX_TOTAL_UNCOMPRESSED_BYTES = 5 * 1024 * 1024 * 1024
MAX_EXPANSION_RATIO = 1_000.0
MAX_EXPORTED_MEMBER_BYTES = 50 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024

POP_MEMBER_PATTERN = re.compile(
    r"^app-blocking pop-ups/basic/"
    r"(?P<split>train|valid|test)/"
    r"(?P<label>ads|no_ads)/"
    r"(?P<filename>[^/]+\.jpg)$"
)
RICO_MEMBER_PATTERN = re.compile(
    r"^semantic_annotations/(?P<source_id>\d+)\.(?P<extension>json|png)$"
)
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")
CRC32_PATTERN = re.compile(r"^[0-9a-fA-F]{8}$")


class AdapterError(RuntimeError):
    """A fail-closed validation or export error."""


def _sha256_stream(stream: BinaryIO) -> str:
    digest = hashlib.sha256()
    stream.seek(0)
    for chunk in iter(lambda: stream.read(CHUNK_BYTES), b""):
        digest.update(chunk)
    stream.seek(0)
    return digest.hexdigest()


def _verify_sha256(stream: BinaryIO, expected: str, label: str) -> str:
    if SHA256_PATTERN.fullmatch(expected) is None:
        raise AdapterError(f"{label}: expected SHA-256 must be 64 hexadecimal digits")
    observed = _sha256_stream(stream)
    if observed != expected.lower():
        raise AdapterError(
            f"{label}: SHA-256 mismatch (expected {expected.lower()}, observed {observed})"
        )
    return observed


def _unsafe_member_path(filename: str) -> bool:
    if not filename or "\x00" in filename or "\\" in filename:
        return True
    trimmed = filename[:-1] if filename.endswith("/") else filename
    if not trimmed or trimmed.startswith("/"):
        return True
    parts = trimmed.split("/")
    return (
        any(part in {"", ".", ".."} for part in parts)
        or ":" in parts[0]
    )


def _inspect_archive(
    archive: zipfile.ZipFile,
    *,
    label: str,
) -> dict[str, zipfile.ZipInfo]:
    infos = archive.infolist()
    if len(infos) > MAX_ARCHIVE_MEMBERS:
        raise AdapterError(
            f"{label}: member count exceeds {MAX_ARCHIVE_MEMBERS}"
        )

    index: dict[str, zipfile.ZipInfo] = {}
    total_uncompressed = 0
    total_compressed = 0
    for info in infos:
        if _unsafe_member_path(info.filename):
            raise AdapterError(f"{label}: unsafe member path: {info.filename!r}")
        if info.filename in index:
            raise AdapterError(f"{label}: duplicate member name: {info.filename!r}")
        if stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK:
            raise AdapterError(f"{label}: symbolic-link member: {info.filename!r}")
        if info.flag_bits & 0x1:
            raise AdapterError(f"{label}: encrypted member is unsupported: {info.filename!r}")
        index[info.filename] = info
        if not info.is_dir():
            total_uncompressed += info.file_size
            total_compressed += info.compress_size

    if total_uncompressed > MAX_TOTAL_UNCOMPRESSED_BYTES:
        raise AdapterError(
            f"{label}: uncompressed archive size exceeds "
            f"{MAX_TOTAL_UNCOMPRESSED_BYTES} bytes"
        )
    ratio = total_uncompressed / max(total_compressed, 1)
    if ratio > MAX_EXPANSION_RATIO:
        raise AdapterError(
            f"{label}: archive expansion ratio {ratio:.2f} exceeds "
            f"{MAX_EXPANSION_RATIO:.2f}"
        )
    return index


def _load_candidates(path: Path) -> tuple[list[dict[str, Any]], str]:
    if not path.is_file():
        raise AdapterError(f"candidate manifest not found: {path}")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_members: set[str] = set()
    for line_number, raw_line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not raw_line.strip():
            continue
        try:
            row = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise AdapterError(
                f"candidate manifest line {line_number} is not valid JSON: {exc.msg}"
            ) from exc
        if not isinstance(row, dict):
            raise AdapterError(f"candidate manifest line {line_number} is not an object")
        source_id = row.get("source_record_id")
        member = row.get("archive_member_path")
        if not isinstance(source_id, str) or not source_id:
            raise AdapterError(f"candidate manifest line {line_number} lacks source_record_id")
        if not isinstance(member, str) or not member:
            raise AdapterError(f"candidate {source_id} lacks archive_member_path")
        if source_id in seen_ids:
            raise AdapterError(f"duplicate candidate source_record_id: {source_id}")
        if member in seen_members:
            raise AdapterError(f"duplicate candidate archive member: {member}")
        seen_ids.add(source_id)
        seen_members.add(member)
        rows.append(row)
    if not rows:
        raise AdapterError("candidate manifest is empty")
    return rows, digest


def _load_frozen_pilot(
    path: Path,
    *,
    candidates: Iterable[dict[str, Any]],
    expected_count: int,
) -> tuple[list[dict[str, Any]], str]:
    """Resolve a frozen pilot to the full candidate rows without resampling."""
    if not path.is_file():
        raise AdapterError(f"frozen pilot manifest not found: {path}")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    pilot_rows: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not raw_line.strip():
            continue
        try:
            row = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise AdapterError(
                f"frozen pilot line {line_number} is not valid JSON: {exc.msg}"
            ) from exc
        if not isinstance(row, dict):
            raise AdapterError(f"frozen pilot line {line_number} is not an object")
        pilot_rows.append(row)
    if len(pilot_rows) != expected_count:
        raise AdapterError(
            f"frozen pilot has {len(pilot_rows)} rows; expected {expected_count}"
        )

    candidate_by_id = {row["source_record_id"]: row for row in candidates}
    try:
        pilot_rows.sort(key=lambda row: row["coordinator_display_order"])
    except KeyError as exc:
        raise AdapterError("frozen pilot lacks coordinator_display_order") from exc

    joined: list[dict[str, Any]] = []
    seen_source_ids: set[str] = set()
    seen_pilot_ids: set[str] = set()
    batch_ids: set[str] = set()
    protocol_versions: set[str] = set()
    selection_seeds: set[str] = set()
    field_pairs = {
        "archive_member_crc32": "archive_member_crc32",
        "archive_member_path": "archive_member_path",
        "archive_member_uncompressed_bytes": "archive_member_uncompressed_bytes",
        "content_key": "content_key",
        "group_key": "group_key",
        "official_split_audit_stratum": "official_split",
        "raw_image_distribution": "raw_image_distribution",
        "source_kind": "source_kind",
        "source_record_id": "source_record_id",
        "source_sampling_label": "source_label",
    }
    for display_order, pilot_row in enumerate(pilot_rows, 1):
        pilot_id = pilot_row.get("pilot_item_id")
        expected_pilot_id = f"PMJ-PILOT-{display_order:03d}"
        if pilot_id != expected_pilot_id:
            raise AdapterError(
                f"frozen pilot item {pilot_id!r} is not {expected_pilot_id}"
            )
        if pilot_row.get("coordinator_display_order") != display_order:
            raise AdapterError(
                f"frozen pilot {pilot_id}: coordinator display order is not contiguous"
            )
        expected_handle = f"adapter://popsweeper/pilot/{pilot_id}"
        if pilot_row.get("adapter_item_handle") != expected_handle:
            raise AdapterError(f"frozen pilot {pilot_id}: adapter handle mismatch")
        if pilot_id in seen_pilot_ids:
            raise AdapterError(f"duplicate frozen pilot_item_id: {pilot_id}")
        seen_pilot_ids.add(pilot_id)

        source_id = pilot_row.get("source_record_id")
        if not isinstance(source_id, str) or source_id not in candidate_by_id:
            raise AdapterError(
                f"frozen pilot {pilot_id}: source_record_id is absent from candidates"
            )
        if source_id in seen_source_ids:
            raise AdapterError(f"frozen pilot {pilot_id}: duplicate source_record_id")
        seen_source_ids.add(source_id)
        candidate = candidate_by_id[source_id]
        for pilot_field, candidate_field in field_pairs.items():
            if pilot_row.get(pilot_field) != candidate.get(candidate_field):
                raise AdapterError(
                    f"frozen pilot {pilot_id} does not match candidate "
                    f"field {pilot_field}"
                )
        if pilot_row.get("eligible_for_message_metrics") is not False:
            raise AdapterError(f"frozen pilot {pilot_id}: metrics eligibility must be false")
        if pilot_row.get("human_message_gold_status") != "pending":
            raise AdapterError(f"frozen pilot {pilot_id}: message gold is not pending")
        if (
            pilot_row.get("source_label_role")
            != "sampling_only_not_human_message_gold"
        ):
            raise AdapterError(f"frozen pilot {pilot_id}: source label role mismatch")

        batch_ids.add(str(pilot_row.get("batch_id")))
        protocol_versions.add(str(pilot_row.get("protocol_version")))
        selection_seeds.add(str(pilot_row.get("selection_seed")))
        resolved = dict(candidate)
        resolved.update(
            {
                "pilot_item_id": pilot_id,
                "adapter_item_handle": expected_handle,
                "batch_id": pilot_row["batch_id"],
                "coordinator_display_order": display_order,
                "protocol_version": pilot_row["protocol_version"],
                "selection_seed": pilot_row["selection_seed"],
                "human_message_gold_status": "pending",
            }
        )
        joined.append(resolved)

    if len(batch_ids) != 1 or "None" in batch_ids:
        raise AdapterError("frozen pilot must have one non-null batch_id")
    if len(protocol_versions) != 1 or "None" in protocol_versions:
        raise AdapterError("frozen pilot must have one non-null protocol_version")
    if len(selection_seeds) != 1 or "None" in selection_seeds:
        raise AdapterError("frozen pilot must have one non-null selection_seed")
    return joined, digest


def _require_string(row: dict[str, Any], field: str, source_id: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value:
        raise AdapterError(f"candidate {source_id}: {field} must be a non-empty string")
    return value


def _require_nonnegative_int(
    row: dict[str, Any], field: str, source_id: str
) -> int:
    value = row.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AdapterError(f"candidate {source_id}: {field} must be a non-negative integer")
    return value


def _validate_candidates(
    rows: Iterable[dict[str, Any]],
    *,
    pop_index: dict[str, zipfile.ZipInfo],
    rico_index: dict[str, zipfile.ZipInfo],
) -> None:
    for row in rows:
        source_id = _require_string(row, "source_record_id", "<unknown>")
        member = _require_string(row, "archive_member_path", source_id)
        if _unsafe_member_path(member):
            raise AdapterError(f"candidate {source_id}: unsafe member path")
        info = pop_index.get(member)
        if info is None or info.is_dir():
            raise AdapterError(f"candidate {source_id}: missing exact PopSweeper member: {member}")

        match = POP_MEMBER_PATTERN.fullmatch(member)
        if match is None:
            raise AdapterError(
                f"candidate {source_id}: PopSweeper member is outside the canonical image path"
            )
        split = match.group("split")
        label = match.group("label")
        basename = match.group("filename")[:-4]
        expected_source_id = f"popsweeper:{split}:{label}:{basename}"
        if source_id != expected_source_id:
            raise AdapterError(
                f"candidate {source_id}: source_record_id does not exactly match member path"
            )
        if row.get("official_split") != split or row.get("source_label") != label:
            raise AdapterError(f"candidate {source_id}: split/label does not match member path")
        if row.get("source_basename") != basename:
            raise AdapterError(f"candidate {source_id}: source_basename does not match member path")
        if row.get("popup_present_gt") is not (label == "ads"):
            raise AdapterError(f"candidate {source_id}: popup_present_gt contradicts folder label")

        crc_text = _require_string(row, "archive_member_crc32", source_id)
        if CRC32_PATTERN.fullmatch(crc_text) is None:
            raise AdapterError(f"candidate {source_id}: archive_member_crc32 is malformed")
        if int(crc_text, 16) != info.CRC:
            raise AdapterError(f"candidate {source_id}: CRC32 mismatch")
        compressed = _require_nonnegative_int(
            row, "archive_member_compressed_bytes", source_id
        )
        uncompressed = _require_nonnegative_int(
            row, "archive_member_uncompressed_bytes", source_id
        )
        if compressed != info.compress_size:
            raise AdapterError(f"candidate {source_id}: compressed-size mismatch")
        if uncompressed != info.file_size:
            raise AdapterError(f"candidate {source_id}: uncompressed-size mismatch")
        expected_content_key = f"crc32:{info.CRC:08x}:bytes:{info.file_size}"
        if row.get("content_key") != expected_content_key:
            raise AdapterError(f"candidate {source_id}: content_key mismatch")
        if row.get("raw_image_distribution") != "adapter_only_not_redistributed":
            raise AdapterError(f"candidate {source_id}: raw-media policy mismatch")

        source_kind = row.get("source_kind")
        expected_kind = (
            "rico_numeric_candidate" if basename.isdigit() else "recorded_app_frame"
        )
        if source_kind != expected_kind:
            raise AdapterError(f"candidate {source_id}: source_kind does not match basename")
        expected_stratum = f"{split}/{label}/{expected_kind}"
        if row.get("sampling_stratum") != expected_stratum:
            raise AdapterError(f"candidate {source_id}: sampling_stratum mismatch")

        if expected_kind == "rico_numeric_candidate":
            if row.get("rico_join_status") != "verified_json_png":
                raise AdapterError(f"candidate {source_id}: RICO join is not verified")
            expected_json = f"semantic_annotations/{basename}.json"
            expected_png = f"semantic_annotations/{basename}.png"
            for field, expected_member in (
                ("rico_semantic_json_member", expected_json),
                ("rico_semantic_png_member", expected_png),
            ):
                referenced = row.get(field)
                if referenced != expected_member:
                    raise AdapterError(
                        f"candidate {source_id}: {field} does not exactly match source ID"
                    )
                rico_info = rico_index.get(expected_member)
                if rico_info is None or rico_info.is_dir():
                    raise AdapterError(
                        f"candidate {source_id}: missing exact RICO member: {expected_member}"
                    )
                if RICO_MEMBER_PATTERN.fullmatch(expected_member) is None:
                    raise AdapterError(
                        f"candidate {source_id}: non-canonical RICO member path"
                    )
        elif row.get("rico_join_status") != "not_applicable":
            raise AdapterError(f"candidate {source_id}: named frame has unexpected RICO join")


def select_pilot(
    rows: Iterable[dict[str, Any]], *, pilot_count: int, seed: int
) -> list[dict[str, Any]]:
    """Select a deterministic proportional pilot using largest remainders."""
    candidates = list(rows)
    if pilot_count <= 0:
        raise AdapterError("pilot_count must be positive")
    if pilot_count > len(candidates):
        raise AdapterError(
            f"pilot_count {pilot_count} exceeds {len(candidates)} candidates"
        )

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        source_id = row.get("source_record_id", "<unknown>")
        stratum = row.get("sampling_stratum")
        if not isinstance(stratum, str) or not stratum:
            raise AdapterError(f"candidate {source_id}: sampling_stratum is missing")
        groups[stratum].append(row)

    total = len(candidates)
    quotas: dict[str, int] = {}
    remainders: list[tuple[float, str]] = []
    for stratum, population in groups.items():
        ideal = pilot_count * len(population) / total
        floor = math.floor(ideal)
        quotas[stratum] = floor
        remainders.append((ideal - floor, stratum))
    remaining = pilot_count - sum(quotas.values())
    for _, stratum in sorted(remainders, key=lambda value: (-value[0], value[1])):
        if remaining == 0:
            break
        if quotas[stratum] < len(groups[stratum]):
            quotas[stratum] += 1
            remaining -= 1
    if remaining:
        raise AdapterError("unable to allocate the requested pilot across strata")

    selected: list[dict[str, Any]] = []
    for stratum in sorted(groups):
        population = sorted(
            groups[stratum], key=lambda row: row["source_record_id"]
        )
        count = quotas[stratum]
        if count == 0:
            continue
        rng = random.Random(f"{seed}:{stratum}")
        selected.extend(rng.sample(population, count))
    return sorted(
        selected,
        key=lambda row: (row["sampling_stratum"], row["source_record_id"]),
    )


def _assert_gitignored(output_dir: Path) -> None:
    resolved = output_dir.resolve()
    existing = resolved
    while not existing.exists() and existing != existing.parent:
        existing = existing.parent
    completed = subprocess.run(
        ["git", "-C", str(existing), "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AdapterError(f"output directory is not inside a Git worktree: {output_dir}")
    git_root = Path(completed.stdout.strip()).resolve()
    try:
        resolved.relative_to(git_root)
    except ValueError as exc:
        raise AdapterError(f"output directory is outside the Git worktree: {output_dir}") from exc
    probe = resolved / ".annotation-media-ignore-probe"
    ignored = subprocess.run(
        [
            "git",
            "-C",
            str(git_root),
            "check-ignore",
            "--quiet",
            "--no-index",
            "--",
            str(probe),
        ],
        check=False,
    )
    if ignored.returncode != 0:
        raise AdapterError(f"output directory is not gitignored: {output_dir}")


def _export_member(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    destination: Path,
) -> dict[str, Any]:
    if info.file_size > MAX_EXPORTED_MEMBER_BYTES:
        raise AdapterError(
            f"selected member exceeds {MAX_EXPORTED_MEMBER_BYTES} bytes: {info.filename}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    written = 0
    with archive.open(info, "r") as source, destination.open("xb") as target:
        for chunk in iter(lambda: source.read(CHUNK_BYTES), b""):
            written += len(chunk)
            if written > info.file_size or written > MAX_EXPORTED_MEMBER_BYTES:
                raise AdapterError(f"member expanded beyond declared size: {info.filename}")
            digest.update(chunk)
            target.write(chunk)
    if written != info.file_size:
        raise AdapterError(
            f"member size changed while reading: {info.filename} "
            f"({written} != {info.file_size})"
        )
    return {"bytes": written, "sha256": digest.hexdigest()}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def export_annotation_media(
    *,
    candidates_path: Path,
    pilot_manifest_path: Path | None = None,
    popsweeper_archive: Path,
    popsweeper_sha256: str,
    rico_archive: Path,
    rico_sha256: str,
    output_dir: Path,
    pilot_count: int = 30,
    seed: int = 20260901,
) -> dict[str, Any]:
    """Preflight all sources and atomically export a local annotation pilot."""
    candidates_path = Path(candidates_path)
    popsweeper_archive = Path(popsweeper_archive)
    rico_archive = Path(rico_archive)
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise AdapterError(f"refusing to overwrite existing output directory: {output_dir}")
    for label, path in (
        ("PopSweeper archive", popsweeper_archive),
        ("RICO archive", rico_archive),
    ):
        if not path.is_file():
            raise AdapterError(f"{label} not found: {path}")

    with (
        popsweeper_archive.open("rb") as pop_stream,
        rico_archive.open("rb") as rico_stream,
    ):
        observed_pop_sha = _verify_sha256(
            pop_stream, popsweeper_sha256, "PopSweeper archive"
        )
        observed_rico_sha = _verify_sha256(rico_stream, rico_sha256, "RICO archive")
        try:
            pop_zip = zipfile.ZipFile(pop_stream)
            rico_zip = zipfile.ZipFile(rico_stream)
        except zipfile.BadZipFile as exc:
            raise AdapterError(f"invalid source ZIP: {exc}") from exc
        with pop_zip, rico_zip:
            pop_index = _inspect_archive(pop_zip, label="PopSweeper archive")
            rico_index = _inspect_archive(rico_zip, label="RICO archive")
            candidates, candidate_sha = _load_candidates(candidates_path)
            _validate_candidates(
                candidates,
                pop_index=pop_index,
                rico_index=rico_index,
            )
            pilot_manifest_sha = None
            if pilot_manifest_path is not None:
                selected, pilot_manifest_sha = _load_frozen_pilot(
                    Path(pilot_manifest_path),
                    candidates=candidates,
                    expected_count=pilot_count,
                )
                selection_mode = "frozen_pilot_manifest"
            else:
                selected = select_pilot(
                    candidates, pilot_count=pilot_count, seed=seed
                )
                selection_mode = "candidate_sample"
            _assert_gitignored(output_dir)

            output_dir.parent.mkdir(parents=True, exist_ok=True)
            temporary = Path(
                tempfile.mkdtemp(
                    prefix=f".{output_dir.name}.tmp-",
                    dir=output_dir.parent,
                )
            )
            try:
                manifest_rows: list[dict[str, Any]] = []
                for index, row in enumerate(selected, 1):
                    item_name = row.get("pilot_item_id", f"item-{index:03d}")
                    item_dir = temporary / item_name
                    item_dir.mkdir()
                    pop_info = pop_index[row["archive_member_path"]]
                    screenshot_path = item_dir / "popsweeper-screenshot.jpg"
                    screenshot = _export_member(pop_zip, pop_info, screenshot_path)
                    artifacts = [
                        {
                            "role": "popsweeper_screenshot",
                            "relative_path": str(
                                screenshot_path.relative_to(temporary)
                            ),
                            "archive_member": row["archive_member_path"],
                            "media_type": "image/jpeg",
                            **screenshot,
                        }
                    ]

                    if row["source_kind"] == "rico_numeric_candidate":
                        for role, field, filename, media_type in (
                            (
                                "rico_semantic_json",
                                "rico_semantic_json_member",
                                "rico-semantic.json",
                                "application/json",
                            ),
                            (
                                "rico_semantic_png",
                                "rico_semantic_png_member",
                                "rico-semantic.png",
                                "image/png",
                            ),
                        ):
                            member = row[field]
                            destination = item_dir / filename
                            exported = _export_member(
                                rico_zip, rico_index[member], destination
                            )
                            artifacts.append(
                                {
                                    "role": role,
                                    "relative_path": str(
                                        destination.relative_to(temporary)
                                    ),
                                    "archive_member": member,
                                    "media_type": media_type,
                                    **exported,
                                }
                            )

                    local_row = {
                        "pilot_index": index,
                        "source_record_id": row["source_record_id"],
                        "popup_present_gt": row["popup_present_gt"],
                        "source_kind": row["source_kind"],
                        "sampling_stratum": row["sampling_stratum"],
                        "message_annotation_status": row[
                            "message_annotation_status"
                        ],
                        "eligible_for_v1_message_metrics": False,
                        "artifacts": artifacts,
                    }
                    for field in (
                        "pilot_item_id",
                        "adapter_item_handle",
                        "batch_id",
                        "coordinator_display_order",
                        "protocol_version",
                        "selection_seed",
                    ):
                        if field in row:
                            local_row[field] = row[field]
                    _write_json(item_dir / "candidate.json", local_row)
                    manifest_rows.append(local_row)

                manifest_path = temporary / "pilot-manifest.jsonl"
                with manifest_path.open("x", encoding="utf-8") as handle:
                    for row in manifest_rows:
                        handle.write(
                            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                        )
                report = {
                    "status": "pass",
                    "purpose": "local_annotation_only",
                    "candidate_count": len(manifest_rows),
                    "sampling_seed": seed,
                    "selection_mode": selection_mode,
                    "candidate_manifest_sha256": candidate_sha,
                    "pilot_manifest_sha256": pilot_manifest_sha,
                    "popsweeper_archive_sha256": observed_pop_sha,
                    "rico_archive_sha256": observed_rico_sha,
                    "raw_media_policy": "adapter_only_not_redistributed",
                    "message_annotation_status": "pending",
                    "eligible_for_v1_message_metrics": False,
                    "artifact_count": sum(
                        len(row["artifacts"]) for row in manifest_rows
                    ),
                }
                _write_json(temporary / "export-summary.json", report)
                temporary.rename(output_dir)
            except Exception:
                shutil.rmtree(temporary, ignore_errors=True)
                raise
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--pilot-manifest", type=Path)
    selection.add_argument(
        "--candidate-sample",
        action="store_true",
        help="sample candidates instead of using the frozen pilot (diagnostic only)",
    )
    parser.add_argument("--popsweeper-archive", type=Path, required=True)
    parser.add_argument("--popsweeper-sha256", required=True)
    parser.add_argument("--rico-archive", type=Path, required=True)
    parser.add_argument("--rico-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pilot-count", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20260901)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = export_annotation_media(
            candidates_path=args.candidates,
            pilot_manifest_path=args.pilot_manifest,
            popsweeper_archive=args.popsweeper_archive,
            popsweeper_sha256=args.popsweeper_sha256,
            rico_archive=args.rico_archive,
            rico_sha256=args.rico_sha256,
            output_dir=args.output_dir,
            pilot_count=args.pilot_count,
            seed=args.seed,
        )
    except AdapterError as exc:
        sys.stderr.write(f"annotation-media export failed: {exc}\n")
        return 2
    sys.stdout.write(json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
