#!/usr/bin/env python3
"""Verify a frozen private visual bank and project only pre-gold prediction fields."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any


EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(EXPERIMENT_ROOT))

from popup_eval.visual_freeze import finalize_visual_evidence_bank


PROJECTION_VERSION = "pmj-heuristic-visual-pregold-projection/1.0.1"


class AdapterBlocked(RuntimeError):
    pass


class DuplicateKeyError(ValueError):
    pass


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _canonical_jsonl(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(_canonical_json(row) + b"\n" for row in rows)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_pairs)
    except Exception as error:  # noqa: BLE001
        raise AdapterBlocked(f"{path.name}: invalid JSON: {error}") from error
    if not isinstance(value, dict):
        raise AdapterBlocked(f"{path.name}: JSON root must be an object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            row = json.loads(line, object_pairs_hook=_strict_pairs)
        except Exception as error:  # noqa: BLE001
            raise AdapterBlocked(f"{path.name}:{line_number}: {error}") from error
        if not isinstance(row, dict):
            raise AdapterBlocked(f"{path.name}:{line_number}: row must be an object")
        rows.append(row)
    if not rows:
        raise AdapterBlocked(f"{path.name}: input is empty")
    return rows


def _image_map(manifest_rows: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in manifest_rows:
        pilot_id = row.get("pilot_item_id")
        if not isinstance(pilot_id, str) or pilot_id in result:
            raise AdapterBlocked("input manifest has invalid or duplicate pilot_item_id")
        artifacts = row.get("artifacts")
        if not isinstance(artifacts, list):
            raise AdapterBlocked(f"{pilot_id}: artifacts must be an array")
        screenshots = [
            artifact
            for artifact in artifacts
            if isinstance(artifact, dict)
            and artifact.get("role") == "popsweeper_screenshot"
        ]
        if len(screenshots) != 1:
            raise AdapterBlocked(f"{pilot_id}: screenshot mapping is not one-to-one")
        image_sha = screenshots[0].get("sha256")
        if not isinstance(image_sha, str) or len(image_sha) != 64:
            raise AdapterBlocked(f"{pilot_id}: screenshot SHA-256 is invalid")
        result[pilot_id] = image_sha.lower()
    return result


def _verify_public_summary(
    computed: dict[str, Any], published: dict[str, Any]
) -> None:
    for key, value in computed.items():
        if published.get(key) != value:
            raise AdapterBlocked(f"public visual summary mismatch: {key}")


def _project(
    rows: list[dict[str, Any]], computed_summary: dict[str, Any]
) -> list[dict[str, Any]]:
    projected: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda value: value["pilot_item_id"]):
        judged = row["status"] == "judged"
        projected.append(
            {
                "action_policy": "no_action",
                "confidence": row["presence_confidence"] if judged else None,
                "critical_facts_pred": row["critical_facts_pred"] if judged else [],
                "evidence_kind": "frozen_private_visual_evidence_bank",
                "fixed_threshold_heuristic_adaptation": True,
                "human_gold_used": False,
                "message_text_pred": row["message_text_pred"] if judged else None,
                "model_config_sha256": row["model_config_sha256"],
                "repeat_execution_byte_identical_on_fixed_host": True,
                "cross_os_or_device_model_identity_reproducible": "not_verified",
                "paper_result_eligible": False,
                "pilot_item_id": row["pilot_item_id"],
                "popup_present_pred": row["popup_present_pred"] if judged else None,
                "projection_version": PROJECTION_VERSION,
                "protocol_sha256": computed_summary["protocol_sha256"],
                "scored": False,
                "status": row["status"],
                "visual_bank_sha256": computed_summary["visual_bank_sha256"],
            }
        )
    return projected


def _atomic_write(path: Path, payload: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if mode == 0o600:
        path.parent.chmod(0o700)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(payload)
    temporary.chmod(mode)
    temporary.replace(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--visual-bank", type=Path, required=True)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--public-summary", type=Path, required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--projection-summary", type=Path, required=True)
    return parser


def run(args: argparse.Namespace) -> int:
    private_output = args.private_output.resolve()
    projection_summary = args.projection_summary.resolve()
    if private_output.parent.name != "private" or not private_output.name.endswith(
        ".private.jsonl"
    ):
        raise AdapterBlocked("projected visual rows require private/*.private.jsonl")
    if private_output.exists() or projection_summary.exists():
        raise AdapterBlocked("projection output already exists")
    try:
        protocol = _read_json(args.protocol.resolve(strict=True))
        bank_rows = _read_jsonl(args.visual_bank.resolve(strict=True))
        manifest_rows = _read_jsonl(args.input_manifest.resolve(strict=True))
        published = _read_json(args.public_summary.resolve(strict=True))
        computed = finalize_visual_evidence_bank(
            protocol, _image_map(manifest_rows), bank_rows
        )
        _verify_public_summary(computed, published)
        projected = _project(bank_rows, computed)
        projected_payload = _canonical_jsonl(projected)
        summary = {
            "status": "frozen_heuristic_visual_pregold_projection",
            "projection_version": PROJECTION_VERSION,
            "item_count": len(projected),
            "judged_count": sum(row["status"] == "judged" for row in projected),
            "abstain_count": sum(row["status"] == "abstain" for row in projected),
            "protocol_sha256": computed["protocol_sha256"],
            "visual_bank_sha256": computed["visual_bank_sha256"],
            "projected_predictions_sha256": _sha256(projected_payload),
            "fixed_threshold_heuristic_adaptation": True,
            "repeat_execution_byte_identical_on_fixed_host": True,
            "cross_os_or_device_model_identity_reproducible": "not_verified",
            "source_manifest_fields_used": [
                "pilot_item_id",
                "artifacts[].role",
                "artifacts[].sha256",
            ],
            "other_known_manifest_fields_ignored": True,
            "unknown_manifest_fields_fail_closed": True,
            "human_gold_used": False,
            "scored": False,
            "paper_result_eligible": False,
        }
        _atomic_write(private_output, projected_payload, 0o600)
        _atomic_write(
            projection_summary,
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True).encode(
                "utf-8"
            )
            + b"\n",
            0o644,
        )
        return 0
    except Exception as error:
        for path in (private_output, projection_summary):
            if path.exists():
                path.unlink()
        if isinstance(error, AdapterBlocked):
            raise
        raise AdapterBlocked(str(error)) from error


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except AdapterBlocked as error:
        print(f"blocked: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
