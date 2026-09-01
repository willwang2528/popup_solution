#!/usr/bin/env python3
"""Audit frozen annotation screenshots without exposing absolute media paths."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sniff_format(data: bytes) -> str:
    if data.startswith(JPEG_MAGIC):
        return "jpeg"
    if data.startswith(PNG_MAGIC):
        return "png"
    return "unknown"


def _expected_images(freeze: dict[str, Any]) -> dict[str, str]:
    return {
        relative: expected
        for relative, expected in freeze.get("media_files_sha256", {}).items()
        if relative.endswith("/popsweeper-screenshot.jpg")
    }


def audit_media(adapter_root: Path, freeze_path: Path) -> dict[str, Any]:
    adapter_root = Path(adapter_root)
    freeze = json.loads(Path(freeze_path).read_text(encoding="utf-8"))
    expected_images = _expected_images(freeze)
    items = []
    missing_items = []
    symlink_items = []
    hash_mismatches = []
    unknown_format_items = []
    extension_mismatches = []
    format_counts: Counter[str] = Counter()
    exif_items = []

    for relative, expected_hash in sorted(expected_images.items()):
        image_path = adapter_root / relative
        item_id = Path(relative).parts[0]
        if not image_path.is_file():
            missing_items.append(item_id)
            continue
        if image_path.is_symlink():
            symlink_items.append(item_id)
            continue

        data = image_path.read_bytes()
        detected_format = sniff_format(data)
        actual_hash = hashlib.sha256(data).hexdigest()
        hash_matches = actual_hash == expected_hash
        if not hash_matches:
            hash_mismatches.append(item_id)
        if detected_format == "unknown":
            unknown_format_items.append(item_id)
        else:
            format_counts[detected_format] += 1

        extension = image_path.suffix.lower()
        expected_extension = ".jpg" if detected_format == "jpeg" else ".png"
        if detected_format != "unknown" and extension != expected_extension:
            extension_mismatches.append(
                {
                    "pilot_item_id": item_id,
                    "extension": extension,
                    "detected_format": detected_format,
                }
            )

        has_exif = detected_format == "jpeg" and b"Exif\x00\x00" in data
        if has_exif:
            exif_items.append(item_id)
        items.append(
            {
                "pilot_item_id": item_id,
                "detected_format": detected_format,
                "extension": extension,
                "bytes": len(data),
                "sha256": actual_hash,
                "frozen_hash_matches": hash_matches,
                "contains_exif_segment": has_exif,
            }
        )

    item_count_matches_freeze = len(expected_images) == freeze.get("batch_size")
    blockers = bool(
        missing_items
        or symlink_items
        or hash_mismatches
        or unknown_format_items
        or not item_count_matches_freeze
    )
    return {
        "status": "blocked" if blockers else "passed",
        "batch_id": freeze.get("batch_id"),
        "expected_item_count": freeze.get("batch_size"),
        "audited_item_count": len(items),
        "item_count_matches_freeze": item_count_matches_freeze,
        "format_counts": dict(sorted(format_counts.items())),
        "extension_mismatches": extension_mismatches,
        "exif_items": exif_items,
        "missing_items": missing_items,
        "symlink_items": symlink_items,
        "hash_mismatches": hash_mismatches,
        "unknown_format_items": unknown_format_items,
        "items": items,
        "privacy_scope": (
            "Technical media integrity only. This report does not approve "
            "privacy, copyright, licensing, or public release."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter-root", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = audit_media(args.adapter_root, args.freeze)
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    args.report.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
