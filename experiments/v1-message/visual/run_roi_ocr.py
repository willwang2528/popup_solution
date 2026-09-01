#!/usr/bin/env python3
"""Freeze a gold-blind screenshot rectangle + ROI OCR evidence bank."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ROOT = ROOT.parent
sys.path.insert(0, str(EXPERIMENT_ROOT))

from popup_eval.visual_freeze import finalize_visual_evidence_bank


ADAPTER_VERSION = "pmj-vision-rectangle-roi-ocr/1.0.1"
CONTRACT_VERSION = "popup-visual-evidence-freeze-v1.0"
PRESENCE_POLICY_ID = "vision-strong-rectangle-presence-v1"
ROI_POLICY_ID = "vision-strong-rectangle-roi-v1"
ENGINE_RESULT_KEYS = {
    "status",
    "presence_confidence",
    "roi_normalized_xyxy",
    "roi_confidence",
    "message_text",
    "critical_facts",
    "block_reason",
    "latency_ms",
    "engine",
}
USED_MANIFEST_FIELDS = (
    "pilot_item_id",
    "artifacts[].role",
    "artifacts[].relative_path",
    "artifacts[].sha256",
)
KNOWN_MANIFEST_FIELDS = {
    "adapter_item_handle",
    "artifacts",
    "batch_id",
    "coordinator_display_order",
    "eligible_for_v1_message_metrics",
    "message_annotation_status",
    "pilot_index",
    "pilot_item_id",
    "popup_present_gt",
    "protocol_version",
    "sampling_stratum",
    "selection_seed",
    "source_kind",
    "source_record_id",
}
KNOWN_ARTIFACT_FIELDS = {
    "archive_member",
    "bytes",
    "media_type",
    "relative_path",
    "role",
    "sha256",
}
ENGINE_CONFIGURATION = {
    "detector": "VNDetectRectanglesRequest",
    "ocr": "VNRecognizeTextRequest",
    "rectangle_minimum_confidence": 0.8,
    "rectangle_minimum_aspect_ratio": 0.3,
    "rectangle_maximum_aspect_ratio": 1.0,
    "rectangle_minimum_size": 0.12,
    "rectangle_quadrature_tolerance_degrees": 12.0,
    "rectangle_maximum_observations": 16,
    "accepted_area_fraction": [0.06, 0.72],
    "minimum_edge_margin_fraction": 0.025,
    "maximum_center_distance": 0.36,
    "presence_decision_threshold": 0.82,
    "roi_expansion_fraction": 0.02,
    "minimum_ocr_characters": 4,
    "minimum_ocr_observations": 1,
    "languages": ["zh-Hans", "en-US"],
    "recognition_level": "accurate",
    "uses_language_correction": True,
    "failure_policy": "abstain",
    "negative_presence_policy": "never_infer_no_popup_from_missing_rectangle",
}


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


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
            raise AdapterBlocked(f"{path}:{line_number}: {error}") from error
        if not isinstance(row, dict):
            raise AdapterBlocked(f"{path}:{line_number}: row must be an object")
        rows.append(row)
    if not rows:
        raise AdapterBlocked("manifest is empty")
    return rows


def _safe_artifact_path(media_root: Path, relative_path: Any) -> Path:
    if not isinstance(relative_path, str) or not relative_path:
        raise AdapterBlocked("screenshot relative_path must be a non-empty string")
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise AdapterBlocked("screenshot path escapes the media root")
    root = media_root.resolve(strict=True)
    try:
        image = (root / relative).resolve(strict=True)
    except FileNotFoundError as error:
        raise AdapterBlocked(f"screenshot is missing: {relative_path}") from error
    if not image.is_relative_to(root) or not image.is_file():
        raise AdapterBlocked("screenshot path escapes the media root")
    return image


def _select_inputs(manifest: Path, media_root: Path) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    for index, row in enumerate(_read_jsonl(manifest), start=1):
        unknown = sorted(set(row) - KNOWN_MANIFEST_FIELDS)
        if unknown:
            raise AdapterBlocked(
                f"manifest row {index} has unknown manifest fields: {unknown}"
            )
        pilot_id = row.get("pilot_item_id")
        if not isinstance(pilot_id, str) or re.fullmatch(
            r"PMJ-PILOT-\d{3}", pilot_id
        ) is None:
            raise AdapterBlocked(f"manifest row {index} has invalid pilot_item_id")
        if pilot_id in identifiers:
            raise AdapterBlocked(f"duplicate pilot_item_id: {pilot_id}")
        identifiers.add(pilot_id)
        artifacts = row.get("artifacts")
        if not isinstance(artifacts, list):
            raise AdapterBlocked(f"{pilot_id}: artifacts must be an array")
        for artifact_index, candidate in enumerate(artifacts, start=1):
            if not isinstance(candidate, dict):
                raise AdapterBlocked(
                    f"{pilot_id}: artifact {artifact_index} must be an object"
                )
            unknown_artifact = sorted(set(candidate) - KNOWN_ARTIFACT_FIELDS)
            if unknown_artifact:
                raise AdapterBlocked(
                    f"{pilot_id}: artifact {artifact_index} has unknown fields: "
                    f"{unknown_artifact}"
                )
        screenshots = [
            artifact
            for artifact in artifacts
            if isinstance(artifact, dict)
            and artifact.get("role") == "popsweeper_screenshot"
        ]
        if len(screenshots) != 1:
            raise AdapterBlocked(
                f"{pilot_id}: expected exactly one popsweeper_screenshot"
            )
        artifact = screenshots[0]
        image = _safe_artifact_path(media_root, artifact.get("relative_path"))
        expected_sha = artifact.get("sha256")
        actual_sha = _sha256_file(image)
        if not isinstance(expected_sha, str) or expected_sha.lower() != actual_sha:
            raise AdapterBlocked(f"{pilot_id}: screenshot SHA-256 mismatch")
        selected.append(
            {
                "pilot_item_id": pilot_id,
                "relative_path": artifact["relative_path"],
                "image": image,
                "image_sha256": actual_sha,
            }
        )
    return selected


def _validate_bbox(value: Any) -> bool:
    if (
        not isinstance(value, list)
        or len(value) != 4
        or not all(
            isinstance(number, (int, float)) and not isinstance(number, bool)
            for number in value
        )
    ):
        return False
    left, top, right, bottom = value
    return 0 <= left < right <= 1 and 0 <= top < bottom <= 1


def _run_engine(engine: Path, source: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    request = {
        "adapter_version": ADAPTER_VERSION,
        "image_sha256": source["image_sha256"],
        "configuration": ENGINE_CONFIGURATION,
    }
    command = [str(engine), "--image", str(source["image"])]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AdapterBlocked(f"ROI OCR engine unavailable: {error}") from error
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()[-2000:]
        raise AdapterBlocked(f"ROI OCR engine failed: {detail}")
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise AdapterBlocked("ROI OCR engine must emit exactly one JSON object")
    try:
        payload = json.loads(lines[0], object_pairs_hook=_strict_pairs)
    except Exception as error:  # noqa: BLE001
        raise AdapterBlocked(f"ROI OCR engine emitted invalid JSON: {error}") from error
    if not isinstance(payload, dict) or set(payload) - ENGINE_RESULT_KEYS:
        raise AdapterBlocked("ROI OCR engine result keys are invalid")
    status = payload.get("status")
    if status not in {"popup", "abstain"}:
        raise AdapterBlocked("ROI OCR engine status must be popup or abstain")
    latency = payload.get("latency_ms")
    if not isinstance(latency, (int, float)) or isinstance(latency, bool) or latency < 0:
        raise AdapterBlocked("ROI OCR engine latency_ms is invalid")
    if not isinstance(payload.get("engine"), dict):
        raise AdapterBlocked("ROI OCR engine identity is missing")
    if status == "popup":
        confidence = payload.get("presence_confidence")
        roi_confidence = payload.get("roi_confidence")
        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0 <= confidence <= 1
            or not isinstance(roi_confidence, (int, float))
            or isinstance(roi_confidence, bool)
            or not 0 <= roi_confidence <= 1
        ):
            raise AdapterBlocked("positive presence confidence is invalid")
        if not _validate_bbox(payload.get("roi_normalized_xyxy")):
            raise AdapterBlocked("positive popup ROI is invalid")
        message = payload.get("message_text")
        if not isinstance(message, str) or not message.strip():
            raise AdapterBlocked("positive popup message is missing")
        facts = payload.get("critical_facts")
        if not isinstance(facts, list) or not all(
            isinstance(fact, str) and fact.strip() for fact in facts
        ):
            raise AdapterBlocked("positive popup critical_facts are invalid")
        if payload.get("block_reason") is not None:
            raise AdapterBlocked("positive popup cannot carry block_reason")
    else:
        if not isinstance(payload.get("block_reason"), str) or not payload[
            "block_reason"
        ].strip():
            raise AdapterBlocked("abstention requires block_reason")
        forbidden = (
            "presence_confidence",
            "roi_normalized_xyxy",
            "roi_confidence",
            "message_text",
            "critical_facts",
        )
        if any(payload.get(key) not in (None, []) for key in forbidden):
            raise AdapterBlocked("abstention cannot carry popup evidence")
    return payload, _sha256_bytes(_canonical_json(request)), _sha256_bytes(
        _canonical_json(payload)
    )


def _build_protocol(
    inputs: list[dict[str, Any]], engine_sha: str, environment_sha: str
) -> dict[str, Any]:
    image_map = {row["pilot_item_id"]: row["image_sha256"] for row in inputs}
    ids = sorted(image_map)
    config = {
        "adapter_version": ADAPTER_VERSION,
        "engine_sha256": engine_sha,
        "environment_sha256": environment_sha,
        "configuration": ENGINE_CONFIGURATION,
    }
    config_sha = _sha256_bytes(_canonical_json(config))
    return {
        "contract_version": CONTRACT_VERSION,
        "status": "ready_for_visual_bank_freeze",
        "scope": "popup_message_judgment_v1",
        "pilot_batch_id": "popsweeper-message-pilot-30-v1",
        "item_count": len(inputs),
        "item_set_sha256": _sha256_bytes(
            json.dumps(ids, separators=(",", ":")).encode("utf-8")
        ),
        "input_image_manifest_sha256": _sha256_bytes(_canonical_json(image_map)),
        "frozen_before_human_gold": True,
        "action_policy": "no_action",
        "gold_blind_attestation": {
            "human_gold_used": False,
            "source_sampling_label_used": False,
            "folder_label_used": False,
            "adjudication_used": False,
            "post_action_evidence_used": False,
        },
        "presence_policy": {
            "policy_id": PRESENCE_POLICY_ID,
            "mode": "frozen_detector",
            "input_channels": ["screenshot_pixels"],
            "implementation_sha256": _sha256_file(Path(__file__)),
            "model_or_rule_version": ADAPTER_VERSION,
            "decision_threshold": ENGINE_CONFIGURATION[
                "presence_decision_threshold"
            ],
            "abstain_band": [
                0.0,
                ENGINE_CONFIGURATION["presence_decision_threshold"],
            ],
            "missing_evidence_action": "abstain",
            "formal_ready": True,
        },
        "roi_policy": {
            "policy_id": ROI_POLICY_ID,
            "roi_kind": "predicted_popup_bbox",
            "coordinate_space": "normalized_xyxy",
            "screenshot_size_required": True,
            "detector_checkpoint_sha256": engine_sha,
            "threshold": ENGINE_CONFIGURATION["presence_decision_threshold"],
            "nms_threshold": 0.0,
            "multi_box_rule": "highest_frozen_shape_score_then_reading_order",
            "expansion_fraction": ENGINE_CONFIGURATION["roi_expansion_fraction"],
            "clipping_rule": "expand_then_clip_to_image",
            "close_button_bbox_is_popup_roi": False,
            "invalid_or_missing_roi_action": "abstain",
            "formal_ready": True,
        },
        "visual_engine": {
            "provider": "local_apple_vision",
            "model": "VNDetectRectanglesRequest_plus_VNRecognizeTextRequest",
            "revision": ADAPTER_VERSION,
            "checkpoint_sha256": engine_sha,
            "license": "Apple platform framework; source adapter in repository",
            "api_version": "Vision framework pinned request configuration",
            "preprocessing_sha256": _sha256_bytes(
                _canonical_json(ENGINE_CONFIGURATION)
            ),
            "prompt_template_sha256": _sha256_bytes(b"no_prompt_roi_ocr_v1"),
            "config_sha256": config_sha,
            "image_resolution": "native_per_item",
            "temperature": 0.0,
            "top_p": 1.0,
            "seed": 17,
            "max_tokens": 1,
            "timeout_seconds": 120,
            "max_retries": 0,
            "environment_sha256": environment_sha,
            "repeat_execution_byte_identical_on_fixed_host": True,
            "cross_os_or_device_model_identity_reproducible": "not_verified",
            "formal_ready": True,
        },
        "budget": {
            "unit": "per_item",
            "per_item_max_calls": 1,
            "image_resolution": "native_per_item",
            "input_token_cap": 1,
            "output_token_cap": 1,
            "latency_cap_ms": 120000,
            "price_snapshot_version": "local-framework-zero-api-cost-v1",
            "shared_visual_bank_sha256": None,
            "formal_ready": True,
        },
        "systems": {
            "B1_roi_ocr_adaptation": {"status": "ready"},
            "C1_AO_always_on_fusion": {"status": "ready_for_frozen_bank"},
            "C1_BM_budget_matched_fusion": {"status": "ready_for_frozen_bank"},
            "C3_MG_PU": {"status": "ready_for_frozen_bank"},
            "B2_popsweeper_exact": {
                "status": "blocked_exact_no_go",
                "uses_this_visual_bank": False,
            },
        },
        "scored": False,
        "paper_result_eligible": False,
        "claims": {
            "empirical_performance": False,
            "method_superiority": False,
            "user_experience_improvement": False,
            "recovery_or_dismissal": False,
        },
    }


def _row(
    source: dict[str, Any],
    engine_result: dict[str, Any],
    request_sha: str,
    response_sha: str,
    config_sha: str,
) -> dict[str, Any]:
    popup = engine_result["status"] == "popup"
    return {
        "contract_version": CONTRACT_VERSION,
        "pilot_item_id": source["pilot_item_id"],
        "input_image_sha256": source["image_sha256"],
        "presence_status": "judged" if popup else "abstain",
        "popup_present_pred": True if popup else None,
        "presence_confidence": engine_result.get("presence_confidence") if popup else None,
        "presence_basis": PRESENCE_POLICY_ID,
        "roi_kind": "predicted_popup_bbox" if popup else "unavailable",
        "roi_normalized_xyxy": engine_result.get("roi_normalized_xyxy") if popup else None,
        "roi_source": ROI_POLICY_ID if popup else None,
        "roi_confidence": engine_result.get("roi_confidence") if popup else None,
        "model_config_sha256": config_sha,
        "request_sha256": request_sha,
        "response_sha256": response_sha,
        "message_text_pred": engine_result.get("message_text") if popup else None,
        "critical_facts_pred": engine_result.get("critical_facts", []) if popup else [],
        "latency_ms": engine_result["latency_ms"],
        "input_tokens": 0,
        "output_tokens": 0,
        "cost": 0.0,
        "status": "judged" if popup else "abstain",
        "block_reason": None if popup else engine_result["block_reason"],
        "human_gold_used": False,
        "source_sampling_label_used": False,
        "folder_label_used": False,
        "adjudication_used": False,
        "post_action_evidence_used": False,
        "scored": False,
        "paper_result_eligible": False,
    }


def _write_private(path: Path, payload: bytes) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(payload)
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def _write_json(path: Path, value: Any, *, private: bool = False) -> None:
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode(
        "utf-8"
    ) + b"\n"
    if private:
        _write_private(path, payload)
        return
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--media-root", type=Path, required=True)
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def run(args: argparse.Namespace) -> int:
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    os.chmod(output, 0o700)
    bank_path = output / "visual-bank.private.jsonl"
    protocol_path = output / "protocol.json"
    summary_path = output / "public-summary.json"
    manifest_path = output / "run-manifest.json"
    for path in (bank_path, protocol_path, summary_path):
        if path.exists():
            raise AdapterBlocked(f"output already exists: {path}")
    try:
        manifest = args.manifest.resolve(strict=True)
        media_root = args.media_root.resolve(strict=True)
        engine = args.engine.resolve(strict=True)
        if not engine.is_file() or not os.access(engine, os.X_OK):
            raise AdapterBlocked("ROI OCR engine is not executable")
        inputs = _select_inputs(manifest, media_root)
        engine_sha = _sha256_file(engine)
        environment = {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        }
        environment_sha = _sha256_bytes(_canonical_json(environment))
        protocol = _build_protocol(inputs, engine_sha, environment_sha)
        rows = []
        for source in inputs:
            result, request_sha, response_sha = _run_engine(engine, source)
            rows.append(
                _row(
                    source,
                    result,
                    request_sha,
                    response_sha,
                    protocol["visual_engine"]["config_sha256"],
                )
            )
        image_map = {row["pilot_item_id"]: row["image_sha256"] for row in inputs}
        summary = finalize_visual_evidence_bank(protocol, image_map, rows)
        bank_payload = b"".join(_canonical_json(row) + b"\n" for row in rows)
        _write_private(bank_path, bank_payload)
        _write_json(protocol_path, protocol, private=True)
        _write_json(summary_path, summary)
        _write_json(
            manifest_path,
            {
                "status": "pass",
                "adapter_version": ADAPTER_VERSION,
                "completed_item_count": len(rows),
                "engine_sha256": engine_sha,
                "implementation_sha256": _sha256_file(Path(__file__)),
                "environment": environment,
                "environment_sha256": environment_sha,
                "source_fields_used": list(USED_MANIFEST_FIELDS),
                "unused_input_policy": (
                    "known schema fields are ignored; unknown root or artifact fields "
                    "fail closed"
                ),
                "action_policy": "no_action",
                "human_gold_used": False,
                "scored": False,
                "paper_result_eligible": False,
            },
            private=True,
        )
        return 0
    except Exception as error:
        for path in (bank_path, protocol_path, summary_path):
            if path.exists():
                path.unlink()
        _write_json(
            manifest_path,
            {
                "status": "blocked",
                "completed_item_count": 0,
                "blocker": str(error),
                "action_policy": "no_action",
                "human_gold_used": False,
                "scored": False,
                "paper_result_eligible": False,
            },
            private=True,
        )
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
