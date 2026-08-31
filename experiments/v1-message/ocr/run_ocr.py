#!/usr/bin/env python3
"""Freeze action-free macOS Vision OCR rows for an annotation-media manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parent
SWIFT_SOURCE = ROOT / "vision_ocr.swift"
ADAPTER_VERSION = "pmj-local-vision-ocr/1.0.0"
USED_MANIFEST_FIELDS = (
    "pilot_item_id",
    "artifacts[].role",
    "artifacts[].relative_path",
    "artifacts[].sha256",
)
FORBIDDEN_OUTPUT_KEYS = {
    "action",
    "action_semantics",
    "coordinate",
    "selector",
    "target",
    "target_candidate_id",
    "execution_channel",
}


class AdapterBlocked(RuntimeError):
    pass


class DuplicateKeyError(ValueError):
    pass


def strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    os.replace(temporary, path)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
        for row in rows
    )
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    os.replace(temporary, path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            row = json.loads(line, object_pairs_hook=strict_pairs)
        except Exception as error:  # noqa: BLE001 - retain exact input context
            raise AdapterBlocked(f"{path}:{line_number}: {error}") from error
        if not isinstance(row, dict):
            raise AdapterBlocked(f"{path}:{line_number}: row must be an object")
        rows.append(row)
    if not rows:
        raise AdapterBlocked("manifest is empty")
    return rows


def safe_artifact_path(media_root: Path, relative_path: Any) -> Path:
    if not isinstance(relative_path, str) or not relative_path:
        raise AdapterBlocked("screenshot relative_path must be a non-empty string")
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise AdapterBlocked(f"artifact path is outside media root: {relative_path}")
    root = media_root.resolve(strict=True)
    try:
        candidate = (root / relative).resolve(strict=True)
    except FileNotFoundError as error:
        raise AdapterBlocked(f"artifact is missing: {relative_path}") from error
    if not candidate.is_relative_to(root):
        raise AdapterBlocked(f"artifact path is outside media root: {relative_path}")
    if not candidate.is_file():
        raise AdapterBlocked(f"artifact is not a file: {relative_path}")
    return candidate


def select_inputs(
    manifest_rows: list[dict[str, Any]], media_root: Path, limit: int | None
) -> list[dict[str, Any]]:
    selected_rows = manifest_rows[:limit] if limit is not None else manifest_rows
    if not selected_rows:
        raise AdapterBlocked("--limit selected zero manifest rows")
    inputs: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    for index, row in enumerate(selected_rows, start=1):
        pilot_item_id = row.get("pilot_item_id")
        if not isinstance(pilot_item_id, str) or not pilot_item_id:
            raise AdapterBlocked(f"manifest row {index} lacks pilot_item_id")
        if pilot_item_id in identifiers:
            raise AdapterBlocked(f"duplicate pilot_item_id: {pilot_item_id}")
        identifiers.add(pilot_item_id)
        artifacts = row.get("artifacts")
        if not isinstance(artifacts, list):
            raise AdapterBlocked(f"{pilot_item_id}: artifacts must be an array")
        screenshots = [
            artifact
            for artifact in artifacts
            if isinstance(artifact, dict)
            and artifact.get("role") == "popsweeper_screenshot"
        ]
        if len(screenshots) != 1:
            raise AdapterBlocked(
                f"{pilot_item_id}: expected exactly one popsweeper_screenshot artifact"
            )
        artifact = screenshots[0]
        image = safe_artifact_path(media_root, artifact.get("relative_path"))
        expected_sha = artifact.get("sha256")
        if not isinstance(expected_sha, str) or len(expected_sha) != 64:
            raise AdapterBlocked(f"{pilot_item_id}: screenshot SHA-256 is invalid")
        actual_sha = sha256_file(image)
        if actual_sha.lower() != expected_sha.lower():
            raise AdapterBlocked(
                f"{pilot_item_id}: screenshot SHA-256 mismatch; "
                f"expected={expected_sha.lower()} actual={actual_sha}"
            )
        inputs.append(
            {
                "pilot_item_id": pilot_item_id,
                "image_path": image,
                "relative_path": artifact["relative_path"],
                "image_sha256": actual_sha,
            }
        )
    return inputs


def build_default_engine() -> Path:
    if sys.platform != "darwin":
        raise AdapterBlocked("macOS Vision requires Darwin; no fallback OCR is allowed")
    if not SWIFT_SOURCE.is_file():
        raise AdapterBlocked(f"Swift source is missing: {SWIFT_SOURCE}")
    source_sha = sha256_file(SWIFT_SOURCE)
    build_root = ROOT / ".build"
    build_root.mkdir(parents=True, exist_ok=True)
    binary = build_root / f"vision-ocr-{source_sha[:12]}"
    if binary.is_file() and os.access(binary, os.X_OK):
        return binary
    machine = platform.machine()
    if machine not in {"arm64", "x86_64"}:
        raise AdapterBlocked(f"unsupported macOS architecture for Swift Vision: {machine}")
    module_cache = build_root / "module-cache"
    module_cache.mkdir(parents=True, exist_ok=True)
    command = [
        "xcrun",
        "--sdk",
        "macosx15.4",
        "swiftc",
        "-target",
        f"{machine}-apple-macosx15.4",
        "-module-cache-path",
        str(module_cache),
        "-O",
        str(SWIFT_SOURCE),
        "-o",
        str(binary),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        raise AdapterBlocked(f"Swift Vision build unavailable: {error}") from error
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()[-4000:]
        raise AdapterBlocked(f"Swift Vision build failed: {detail}")
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise AdapterBlocked("Swift Vision build returned success without an executable")
    return binary


def resolve_engine(engine: Path | None) -> Path:
    resolved = engine.resolve(strict=True) if engine is not None else build_default_engine()
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise AdapterBlocked(f"OCR engine is not executable: {resolved}")
    return resolved


def run_engine(
    engine: Path,
    image: Path,
    languages: list[str],
    recognition_level: str,
    uses_language_correction: bool,
) -> dict[str, Any]:
    command = [
        str(engine),
        "--image",
        str(image),
        "--recognition-level",
        recognition_level,
        "--uses-language-correction",
        "true" if uses_language_correction else "false",
    ]
    for language in languages:
        command.extend(["--language", language])
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AdapterBlocked(f"Vision OCR engine unavailable: {error}") from error
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()[-4000:]
        raise AdapterBlocked(
            f"Vision OCR engine failed with exit {result.returncode}: {detail}"
        )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise AdapterBlocked("Vision OCR engine must emit exactly one JSON object")
    try:
        payload = json.loads(lines[0], object_pairs_hook=strict_pairs)
    except Exception as error:  # noqa: BLE001 - preserve engine boundary context
        raise AdapterBlocked(f"Vision OCR engine emitted invalid JSON: {error}") from error
    if not isinstance(payload, dict):
        raise AdapterBlocked("Vision OCR engine output must be an object")
    status = payload.get("status")
    if status not in {"ok", "no_text"}:
        raise AdapterBlocked(f"Vision OCR engine returned unsupported status: {status!r}")
    observations = payload.get("observations")
    engine_metadata = payload.get("engine")
    latency = payload.get("latency_ms")
    if not isinstance(observations, list) or not isinstance(engine_metadata, dict):
        raise AdapterBlocked("Vision OCR output lacks observations or engine metadata")
    if not isinstance(latency, (int, float)) or isinstance(latency, bool) or latency < 0:
        raise AdapterBlocked("Vision OCR output has invalid latency_ms")
    text = payload.get("text")
    confidence = payload.get("confidence")
    if status == "ok":
        if not isinstance(text, str) or not text.strip():
            raise AdapterBlocked("Vision OCR ok result requires non-empty text")
        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0.0 <= float(confidence) <= 1.0
        ):
            raise AdapterBlocked("Vision OCR ok result has invalid confidence")
    elif text is not None or confidence is not None or observations:
        raise AdapterBlocked("Vision OCR no_text result must not carry text observations")
    return payload


def prediction_row(
    source: dict[str, Any], engine_result: dict[str, Any], manifest_sha256: str
) -> dict[str, Any]:
    text_observed = engine_result["status"] == "ok"
    row = {
        "pilot_item_id": source["pilot_item_id"],
        "status": "abstain",
        "popup_present_pred": None,
        "message_text_pred": engine_result["text"] if text_observed else None,
        "critical_facts_pred": [],
        "confidence": engine_result["confidence"] if text_observed else None,
        "source_observation_id": "popsweeper_screenshot",
        "ocr_status": "text_observed" if text_observed else "no_text_observed",
        "presence_basis": "not_inferred_from_full_screen_ocr",
        "evidence": {
            "artifact_role": "popsweeper_screenshot",
            "artifact_relative_path": source["relative_path"],
            "image_sha256": source["image_sha256"],
            "input_manifest_sha256": manifest_sha256,
            "observations": engine_result["observations"],
        },
        "ocr": engine_result["engine"],
        "latency_ms": engine_result["latency_ms"],
        "adapter_version": ADAPTER_VERSION,
        "evidence_level": "local_full_screen_vision_ocr_no_human_gold",
        "paper_result_eligible": False,
    }
    forbidden = FORBIDDEN_OUTPUT_KEYS & set(row)
    if forbidden:
        raise AdapterBlocked(f"action-bearing prediction keys are forbidden: {sorted(forbidden)}")
    return row


def base_run_manifest(args: argparse.Namespace, manifest_sha: str | None) -> dict[str, Any]:
    return {
        "adapter_contract_version": ADAPTER_VERSION,
        "status": "blocked",
        "seed": args.seed,
        "seed_semantics": "recorded_for_pipeline_reproduction; Vision OCR does not sample",
        "recognition_level": args.recognition_level,
        "recognition_languages": args.language,
        "uses_language_correction": args.uses_language_correction,
        "input_manifest_sha256": manifest_sha,
        "source_fields_used": list(USED_MANIFEST_FIELDS),
        "ignored_input_policy": "all manifest fields outside source_fields_used are ignored",
        "action_policy": "no_action",
        "paper_result_eligible": False,
        "claims": {
            "human_message_gold": False,
            "popup_presence": False,
            "method_effectiveness": False,
            "dismissal_or_recovery": False,
        },
        "host": {
            "system": platform.system(),
            "machine": platform.machine(),
            "release": platform.release(),
        },
    }


def run(args: argparse.Namespace) -> int:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = output_dir / "predictions.jsonl"
    run_manifest_path = output_dir / "run_manifest.json"
    if predictions_path.exists() and not args.overwrite:
        blocker = f"output already exists; pass --overwrite explicitly: {predictions_path}"
        manifest = base_run_manifest(args, None)
        manifest.update({"blocker": blocker, "completed_item_count": 0})
        write_json(run_manifest_path, manifest)
        print(blocker, file=sys.stderr)
        return 2
    if predictions_path.exists():
        predictions_path.unlink()

    manifest_sha: str | None = None
    manifest = base_run_manifest(args, manifest_sha)
    try:
        manifest_path = args.manifest.resolve(strict=True)
        media_root = args.media_root.resolve(strict=True)
        manifest_sha = sha256_file(manifest_path)
        manifest = base_run_manifest(args, manifest_sha)
        rows = read_jsonl(manifest_path)
        if args.limit is not None and args.limit < 1:
            raise AdapterBlocked("--limit must be at least 1")
        inputs = select_inputs(rows, media_root, args.limit)
        engine = resolve_engine(args.engine)
        engine_sha = sha256_file(engine)
        predictions = []
        for source in inputs:
            result = run_engine(
                engine,
                source["image_path"],
                args.language,
                args.recognition_level,
                args.uses_language_correction,
            )
            predictions.append(prediction_row(source, result, manifest_sha))
        write_jsonl(predictions_path, predictions)
        manifest.update(
            {
                "status": "pass",
                "freeze_status": "frozen_canonical_jsonl",
                "input_item_count": len(rows),
                "item_count": len(predictions),
                "completed_item_count": len(predictions),
                "engine_sha256": engine_sha,
                "swift_source_sha256": sha256_file(SWIFT_SOURCE),
                "predictions_sha256": sha256_file(predictions_path),
                "ocr_status_counts": {
                    status: sum(row["ocr_status"] == status for row in predictions)
                    for status in ("text_observed", "no_text_observed")
                },
                "total_latency_ms": sum(row["latency_ms"] for row in predictions),
            }
        )
        write_json(run_manifest_path, manifest)
        print(
            json.dumps(
                {
                    "status": "pass",
                    "item_count": len(predictions),
                    "predictions": str(predictions_path),
                    "sha256": manifest["predictions_sha256"],
                },
                sort_keys=True,
            )
        )
        return 0
    except Exception as error:  # noqa: BLE001 - every failure must emit blocker evidence
        blocker = str(error)
        if predictions_path.exists():
            predictions_path.unlink()
        manifest.update({"status": "blocked", "blocker": blocker, "completed_item_count": 0})
        write_json(run_manifest_path, manifest)
        print(f"OCR adapter blocked: {blocker}", file=sys.stderr)
        return 2


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Freeze action-free macOS Vision OCR for PMJ annotation media."
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--media-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--engine", type=Path)
    parser.add_argument("--language", action="append", default=[])
    parser.add_argument(
        "--recognition-level", choices=("accurate", "fast"), default="accurate"
    )
    parser.add_argument(
        "--uses-language-correction",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    if not args.language:
        args.language = ["zh-Hans", "en-US"]
    return args


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
