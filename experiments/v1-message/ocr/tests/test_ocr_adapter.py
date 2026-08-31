from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import unittest


OCR_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = OCR_ROOT.parents[2]
CLI = OCR_ROOT / "run_ocr.py"
SWIFT_SOURCE = OCR_ROOT / "vision_ocr.swift"
PUBLIC_SUMMARY = OCR_ROOT / "PUBLIC_RUN_SUMMARY.json"
PUBLIC_COMPUTE_SPEC = OCR_ROOT / "compute" / "local-macos-pmj-ocr.env-spec.json"
PUBLIC_COMPUTE_LEDGER = OCR_ROOT / "compute" / "local-macos-pmj-ocr.md"
REAL_MEDIA_ROOT = (
    PROJECT_ROOT
    / "dataset-v1"
    / "work"
    / "annotation-media"
    / "pilot-batch-30"
)
RUN_REAL_VISION = (
    sys.platform == "darwin"
    and shutil.which("xcrun") is not None
    and os.environ.get("PMJ_RUN_REAL_VISION") == "1"
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_fake_engine(root: Path, *, fail: bool = False) -> Path:
    engine = root / "fake-vision-engine"
    if fail:
        source = "#!/bin/sh\necho 'engine unavailable' >&2\nexit 9\n"
    else:
        source = r'''#!/usr/bin/env python3
import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument("--image")
parser.add_argument("--language", action="append", default=[])
parser.add_argument("--recognition-level")
parser.add_argument("--uses-language-correction")
args = parser.parse_args()
payload = open(args.image, "rb").read()
if payload == b"no-text":
    result = {
        "status": "no_text",
        "text": None,
        "confidence": None,
        "observations": [],
    }
else:
    result = {
        "status": "ok",
        "text": "Sign in required",
        "confidence": 0.875,
        "observations": [{
            "text": "Sign in required",
            "confidence": 0.875,
            "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.7, "height": 0.1},
        }],
    }
result.update({
    "engine": {
        "framework": "Vision",
        "request": "VNRecognizeTextRequest",
        "request_revision": 3,
        "recognition_level": args.recognition_level,
        "languages": args.language,
        "uses_language_correction": args.uses_language_correction == "true",
    },
    "latency_ms": 1.25,
})
print(json.dumps(result, sort_keys=True))
'''
    engine.write_text(source, encoding="utf-8")
    engine.chmod(0o755)
    return engine


def write_media_manifest(root: Path) -> tuple[Path, Path]:
    media_root = root / "media"
    rows = []
    for index, payload in enumerate((b"image-with-text", b"no-text"), start=1):
        pilot_item_id = f"PMJ-PILOT-{index:03d}"
        relative_path = f"{pilot_item_id}/popsweeper-screenshot.jpg"
        image = media_root / relative_path
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(payload)
        rows.append(
            {
                "pilot_item_id": pilot_item_id,
                "popup_present_gt": index == 1,
                "source_sampling_label": "ads" if index == 1 else "no_ads",
                "message_gold": "MUST NOT BE READ",
                "artifacts": [
                    {
                        "role": "popsweeper_screenshot",
                        "relative_path": relative_path,
                        "sha256": sha256_bytes(payload),
                        "media_type": "image/jpeg",
                    }
                ],
            }
        )
    manifest = media_root / "pilot-manifest.jsonl"
    manifest.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    return manifest, media_root


def run_cli(
    manifest: Path,
    media_root: Path,
    output_dir: Path,
    engine: Path,
    *extra: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--manifest",
            str(manifest),
            "--media-root",
            str(media_root),
            "--output-dir",
            str(output_dir),
            "--engine",
            str(engine),
            "--language",
            "zh-Hans",
            "--language",
            "en-US",
            "--seed",
            "17",
            *extra,
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )


def compile_swift(binary: Path) -> subprocess.CompletedProcess[str]:
    module_cache = binary.parent / "module-cache"
    module_cache.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        [
            "xcrun",
            "--sdk",
            "macosx15.4",
            "swiftc",
            "-target",
            f"{platform.machine()}-apple-macosx15.4",
            "-module-cache-path",
            str(module_cache),
            "-O",
            str(SWIFT_SOURCE),
            "-o",
            str(binary),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )


class OCRAdapterContractTests(unittest.TestCase):
    def test_public_artifacts_withhold_ocr_text_and_private_paths(self):
        """Catches accidental publication of derived OCR text, PII, or local paths."""
        ignored = subprocess.run(
            [
                "git",
                "check-ignore",
                "--quiet",
                str(OCR_ROOT / "results" / "pilot-batch-30" / "predictions.jsonl"),
            ],
            cwd=PROJECT_ROOT,
        )
        self.assertEqual(ignored.returncode, 0, "ocr/results must be gitignored")
        summary = json.loads(PUBLIC_SUMMARY.read_text(encoding="utf-8"))
        self.assertEqual(summary["privacy_status"], "withheld_pending_privacy_review")
        self.assertFalse(summary["paper_result_eligible"])
        self.assertEqual(summary["item_count"], 30)
        self.assertNotIn("predictions", summary)
        serialized = json.dumps(summary, ensure_ascii=False)
        self.assertNotIn("message_text_pred", serialized)
        self.assertNotIn("observations", serialized)
        self.assertNotIn("/Users/", serialized)
        public_spec = PUBLIC_COMPUTE_SPEC.read_text(encoding="utf-8")
        public_ledger = PUBLIC_COMPUTE_LEDGER.read_text(encoding="utf-8")
        self.assertNotIn("/Users/", public_spec)
        self.assertNotIn("/Users/", public_ledger)

    def test_cli_ignores_gold_and_source_labels_and_never_claims_popup_presence(self):
        """Catches label leakage or OCR text being promoted to popup-presence truth."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, media_root = write_media_manifest(root)
            output_dir = root / "output"
            result = run_cli(manifest, media_root, output_dir, write_fake_engine(root))

            self.assertEqual(result.returncode, 0, result.stderr)
            rows = [
                json.loads(line)
                for line in (output_dir / "predictions.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual(
                [row["pilot_item_id"] for row in rows],
                ["PMJ-PILOT-001", "PMJ-PILOT-002"],
            )
            self.assertEqual(rows[0]["status"], "abstain")
            self.assertIsNone(rows[0]["popup_present_pred"])
            self.assertEqual(rows[0]["message_text_pred"], "Sign in required")
            self.assertEqual(rows[0]["confidence"], 0.875)
            self.assertEqual(rows[0]["ocr_status"], "text_observed")
            self.assertEqual(rows[1]["status"], "abstain")
            self.assertIsNone(rows[1]["popup_present_pred"])
            self.assertIsNone(rows[1]["message_text_pred"])
            self.assertEqual(rows[1]["ocr_status"], "no_text_observed")
            for row in rows:
                self.assertFalse(row["paper_result_eligible"])
                self.assertEqual(row["critical_facts_pred"], [])
                self.assertNotIn("popup_present_gt", row)
                self.assertNotIn("source_sampling_label", row)
                self.assertNotIn("message_gold", row)
                self.assertFalse(
                    {
                        "action",
                        "coordinate",
                        "selector",
                        "target_candidate_id",
                        "execution_channel",
                    }
                    & set(row)
                )
                self.assertEqual(row["ocr"]["framework"], "Vision")
                self.assertEqual(row["ocr"]["languages"], ["zh-Hans", "en-US"])
                self.assertIn("latency_ms", row)
                self.assertEqual(row["evidence"]["artifact_role"], "popsweeper_screenshot")
                self.assertEqual(len(row["evidence"]["image_sha256"]), 64)

            run_manifest = json.loads(
                (output_dir / "run_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(run_manifest["status"], "pass")
            self.assertEqual(run_manifest["item_count"], 2)
            self.assertEqual(run_manifest["action_policy"], "no_action")
            self.assertFalse(run_manifest["paper_result_eligible"])
            self.assertEqual(len(run_manifest["predictions_sha256"]), 64)

    def test_image_path_traversal_blocks_batch_without_predictions(self):
        """Catches a manifest that escapes the authorized annotation-media root."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, media_root = write_media_manifest(root)
            rows = [json.loads(line) for line in manifest.read_text().splitlines()]
            rows[0]["artifacts"][0]["relative_path"] = "../outside.jpg"
            manifest.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )
            output_dir = root / "output"

            result = run_cli(manifest, media_root, output_dir, write_fake_engine(root))

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((output_dir / "predictions.jsonl").exists())
            blocker = json.loads(
                (output_dir / "run_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(blocker["status"], "blocked")
            self.assertIn("outside media root", blocker["blocker"])

    def test_image_hash_mismatch_blocks_batch_before_ocr(self):
        """Catches OCR over bytes other than the frozen artifact named by the manifest."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, media_root = write_media_manifest(root)
            rows = [json.loads(line) for line in manifest.read_text().splitlines()]
            rows[0]["artifacts"][0]["sha256"] = "0" * 64
            manifest.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )
            output_dir = root / "output"

            result = run_cli(manifest, media_root, output_dir, write_fake_engine(root))

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((output_dir / "predictions.jsonl").exists())
            blocker = json.loads(
                (output_dir / "run_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(blocker["status"], "blocked")
            self.assertIn("SHA-256 mismatch", blocker["blocker"])

    def test_engine_failure_is_recorded_without_fabricated_ocr(self):
        """Catches fallback text or partial predictions after Vision is unavailable."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, media_root = write_media_manifest(root)
            output_dir = root / "output"

            result = run_cli(
                manifest, media_root, output_dir, write_fake_engine(root, fail=True)
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((output_dir / "predictions.jsonl").exists())
            blocker = json.loads(
                (output_dir / "run_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(blocker["status"], "blocked")
            self.assertEqual(blocker["completed_item_count"], 0)
            self.assertIn("engine unavailable", blocker["blocker"])

    @unittest.skipUnless(RUN_REAL_VISION, "set PMJ_RUN_REAL_VISION=1 on macOS")
    def test_swift_vision_seeded_witness_dispatches(self):
        """Catches a Swift binary that builds but cannot dispatch VNRecognizeTextRequest."""
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "vision-ocr"
            build = compile_swift(binary)
            self.assertEqual(build.returncode, 0, build.stderr)
            witness = subprocess.run(
                [
                    str(binary),
                    "--witness",
                    "--seed",
                    "17",
                    "--language",
                    "en-US",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(witness.returncode, 0, witness.stderr)
            self.assertRegex(
                witness.stdout.strip(),
                r"^WITNESS vision_ocr seed=17 observations=\d+ revision=\d+$",
            )

    @unittest.skipUnless(
        RUN_REAL_VISION and (REAL_MEDIA_ROOT / "pilot-manifest.jsonl").is_file(),
        "set PMJ_RUN_REAL_VISION=1 with ignored real PMJ media present",
    )
    def test_real_pmj_image_smoke_produces_only_action_free_ocr_evidence(self):
        """Catches real-image decoding/runtime drift hidden by a fake-engine unit test."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / "vision-ocr"
            build = compile_swift(binary)
            self.assertEqual(build.returncode, 0, build.stderr)
            output_dir = root / "output"
            result = run_cli(
                REAL_MEDIA_ROOT / "pilot-manifest.jsonl",
                REAL_MEDIA_ROOT,
                output_dir,
                binary,
                "--limit",
                "1",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = [
                json.loads(line)
                for line in (output_dir / "predictions.jsonl").read_text().splitlines()
            ]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["pilot_item_id"], "PMJ-PILOT-001")
            self.assertEqual(rows[0]["status"], "abstain")
            self.assertIsNone(rows[0]["popup_present_pred"])
            self.assertIn(rows[0]["ocr_status"], {"text_observed", "no_text_observed"})
            self.assertFalse(
                {"action", "coordinate", "selector", "target_candidate_id"}
                & set(rows[0])
            )


if __name__ == "__main__":
    unittest.main()
