#!/usr/bin/env python3
"""Integrity and inventory audit for a PopSweeper source ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_unsafe_member_path(filename: str) -> bool:
    normalized = filename.replace("\\", "/")
    path = PurePosixPath(normalized)
    return (
        path.is_absolute()
        or ".." in path.parts
        or (path.parts and ":" in path.parts[0])
    )


def audit_archive(
    archive_path: str | Path,
    *,
    expected_size: int | None = None,
    expected_md5: str | None = None,
    max_total_uncompressed_bytes: int = 50 * 1024 * 1024 * 1024,
    max_members: int = 1_000_000,
    max_expansion_ratio: float = 1_000.0,
) -> dict[str, Any]:
    """Return source integrity and member inventory without extracting the ZIP."""
    archive = Path(archive_path)
    size = archive.stat().st_size
    md5 = _md5(archive)
    errors: list[str] = []
    if expected_size is not None and size != expected_size:
        errors.append("size_mismatch")
    if expected_md5 is not None and md5.lower() != expected_md5.lower():
        errors.append("md5_mismatch")

    try:
        with zipfile.ZipFile(archive) as zf:
            members = [item for item in zf.infolist() if not item.is_dir()]
    except zipfile.BadZipFile:
        members = []
        errors.append("invalid_zip")
    total_uncompressed_bytes = sum(item.file_size for item in members)
    total_compressed_bytes = sum(item.compress_size for item in members)
    expansion_ratio = total_uncompressed_bytes / max(total_compressed_bytes, 1)
    unsafe_paths = sorted(
        item.filename for item in members if _is_unsafe_member_path(item.filename)
    )
    symlinks = sorted(
        item.filename
        for item in members
        if stat.S_IFMT(item.external_attr >> 16) == stat.S_IFLNK
    )
    if unsafe_paths:
        errors.append("unsafe_member_path")
    if symlinks:
        errors.append("unsafe_symlink")
    if total_uncompressed_bytes > max_total_uncompressed_bytes:
        errors.append("uncompressed_size_limit")
    if len(members) > max_members:
        errors.append("member_count_limit")
    if expansion_ratio > max_expansion_ratio:
        errors.append("expansion_ratio_limit")

    extensions = Counter(Path(item.filename).suffix.lower() for item in members)
    top_levels = Counter(
        PurePosixPath(item.filename.replace("\\", "/")).parts[0]
        for item in members
        if PurePosixPath(item.filename.replace("\\", "/")).parts
    )
    sample_members = sorted(item.filename for item in members)[:20]
    return {
        "status": "fail" if errors else "pass",
        "archive": {
            "path": str(archive),
            "size": size,
            "md5": md5,
            "expected_size": expected_size,
            "expected_md5": expected_md5,
        },
        "inventory": {
            "member_count": len(members),
            "extension_counts": dict(sorted(extensions.items())),
            "top_level_counts": dict(sorted(top_levels.items())),
            "sample_members": sample_members,
        },
        "safety": {
            "unsafe_paths": unsafe_paths,
            "symlinks": symlinks,
            "total_uncompressed_bytes": total_uncompressed_bytes,
            "total_compressed_bytes": total_compressed_bytes,
            "expansion_ratio": expansion_ratio,
            "max_total_uncompressed_bytes": max_total_uncompressed_bytes,
            "max_members": max_members,
            "max_expansion_ratio": max_expansion_ratio,
        },
        "errors": errors,
        "warnings": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit a PopSweeper source ZIP without extracting it."
    )
    parser.add_argument("archive", type=Path)
    parser.add_argument("--expected-size", type=int)
    parser.add_argument("--expected-md5")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--max-total-uncompressed-bytes",
        type=int,
        default=50 * 1024 * 1024 * 1024,
    )
    parser.add_argument("--max-members", type=int, default=1_000_000)
    parser.add_argument("--max-expansion-ratio", type=float, default=1_000.0)
    args = parser.parse_args(argv)

    result = audit_archive(
        args.archive,
        expected_size=args.expected_size,
        expected_md5=args.expected_md5,
        max_total_uncompressed_bytes=args.max_total_uncompressed_bytes,
        max_members=args.max_members,
        max_expansion_ratio=args.max_expansion_ratio,
    )
    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
