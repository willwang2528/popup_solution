from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest


VISUAL_DIR = Path(__file__).resolve().parents[1]
EXPERIMENT_DIR = VISUAL_DIR.parent
sys.path.insert(0, str(VISUAL_DIR))
sys.path.insert(0, str(EXPERIMENT_DIR))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class RoiOcrAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.media = self.root / "media"
        self.media.mkdir()
        self.images: dict[str, bytes] = {
            "PMJ-PILOT-001": b"fixture-image-one",
            "PMJ-PILOT-002": b"fixture-image-two",
        }
        self.manifest_rows = []
        for index, (pilot_id, payload) in enumerate(self.images.items(), start=1):
            item_dir = self.media / pilot_id
            item_dir.mkdir()
            image = item_dir / "popsweeper-screenshot.jpg"
            image.write_bytes(payload)
            self.manifest_rows.append(
                {
                    "pilot_item_id": pilot_id,
                    "popup_present_gt": index == 1,
                    "sampling_stratum": "forbidden/source/label",
                    "source_record_id": f"private-source-{index}",
                    "artifacts": [
                        {
                            "role": "popsweeper_screenshot",
                            "relative_path": f"{pilot_id}/popsweeper-screenshot.jpg",
                            "sha256": sha256_bytes(payload),
                            "archive_member": "must-not-reach-engine.jpg",
                        }
                    ],
                }
            )
        self.manifest = self.root / "pilot-manifest.jsonl"
        self.manifest.write_text(
            "".join(json.dumps(row) + "\n" for row in self.manifest_rows),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_engine(self, source: str) -> Path:
        engine = self.root / "engine.py"
        engine.write_text("#!/usr/bin/env python3\n" + source, encoding="utf-8")
        engine.chmod(engine.stat().st_mode | stat.S_IXUSR)
        return engine

    def run_adapter(
        self, engine: Path, output: Path, manifest: Path | None = None
    ) -> tuple[dict, list[dict], dict]:
        from run_roi_ocr import build_parser, run

        args = build_parser().parse_args(
            [
                "--manifest",
                str(manifest or self.manifest),
                "--media-root",
                str(self.media),
                "--engine",
                str(engine),
                "--output-dir",
                str(output),
            ]
        )
        self.assertEqual(run(args), 0)
        protocol = json.loads((output / "protocol.json").read_text(encoding="utf-8"))
        rows = [
            json.loads(line)
            for line in (output / "visual-bank.private.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        summary = json.loads((output / "public-summary.json").read_text(encoding="utf-8"))
        return protocol, rows, summary

    def test_freezes_gold_blind_popup_roi_and_abstain_rows(self) -> None:
        """Break caught: source labels leak or missing ROI is promoted to a judgment."""
        engine = self.write_engine(
            """
import hashlib, json, pathlib, sys
image = pathlib.Path(sys.argv[sys.argv.index('--image') + 1])
payload = image.read_bytes()
if payload.endswith(b'one'):
    result = {
        'status': 'popup',
        'presence_confidence': 0.91,
        'roi_normalized_xyxy': [0.1, 0.2, 0.9, 0.8],
        'roi_confidence': 0.93,
        'message_text': 'Visible offer ends today',
        'critical_facts': [],
        'latency_ms': 12.5,
        'engine': {'name': 'fixture-engine', 'revision': 'r1'},
    }
else:
    result = {
        'status': 'abstain',
        'block_reason': 'no_strong_popup_rectangle',
        'latency_ms': 8.0,
        'engine': {'name': 'fixture-engine', 'revision': 'r1'},
    }
print(json.dumps(result, sort_keys=True))
"""
        )
        protocol, rows, summary = self.run_adapter(engine, self.root / "out")

        self.assertEqual(protocol["status"], "ready_for_visual_bank_freeze")
        self.assertEqual(protocol["presence_policy"]["mode"], "frozen_detector")
        self.assertTrue(
            protocol["visual_engine"][
                "repeat_execution_byte_identical_on_fixed_host"
            ]
        )
        self.assertEqual(
            protocol["visual_engine"][
                "cross_os_or_device_model_identity_reproducible"
            ],
            "not_verified",
        )
        self.assertEqual(rows[0]["status"], "judged")
        self.assertTrue(rows[0]["popup_present_pred"])
        self.assertEqual(rows[0]["roi_normalized_xyxy"], [0.1, 0.2, 0.9, 0.8])
        self.assertEqual(rows[0]["message_text_pred"], "Visible offer ends today")
        self.assertEqual(rows[1]["status"], "abstain")
        self.assertIsNone(rows[1]["popup_present_pred"])
        self.assertIsNone(rows[1]["message_text_pred"])
        serialized = json.dumps({"protocol": protocol, "rows": rows, "summary": summary})
        self.assertNotIn("popup_present_gt", serialized)
        self.assertNotIn("sampling_stratum", serialized)
        self.assertNotIn("private-source", serialized)
        self.assertEqual(summary["judged_count"], 1)
        self.assertEqual(summary["abstain_count"], 1)
        self.assertFalse(summary["paper_result_eligible"])

        from popup_eval.visual_freeze import finalize_visual_evidence_bank

        image_map = {
            pilot_id: sha256_bytes(payload) for pilot_id, payload in self.images.items()
        }
        self.assertEqual(
            finalize_visual_evidence_bank(protocol, image_map, rows), summary
        )

    def test_ignored_gold_fields_cannot_change_predictions_or_bank_hash(self) -> None:
        """Break caught: adapter behavior depends on a forbidden manifest field."""
        engine = self.write_engine(
            """
import json
print(json.dumps({
  'status': 'abstain',
  'block_reason': 'no_strong_popup_rectangle',
  'latency_ms': 1.0,
  'engine': {'name': 'fixture-engine', 'revision': 'r1'},
}, sort_keys=True))
"""
        )
        _, first_rows, first_summary = self.run_adapter(engine, self.root / "first")
        for row in self.manifest_rows:
            row["popup_present_gt"] = not row["popup_present_gt"]
            row["sampling_stratum"] = "changed/forbidden/label"
            row["source_record_id"] = "changed-private-source"
        self.manifest.write_text(
            "".join(json.dumps(row) + "\n" for row in self.manifest_rows),
            encoding="utf-8",
        )
        _, second_rows, second_summary = self.run_adapter(engine, self.root / "second")

        self.assertEqual(first_rows, second_rows)
        self.assertEqual(
            first_summary["visual_bank_sha256"], second_summary["visual_bank_sha256"]
        )

    def test_redacted_manifest_is_identical_and_unknown_schema_drift_blocks(self) -> None:
        """Break caught: label presence or a newly added label-like field affects input."""
        engine = self.write_engine(
            """
import json
print(json.dumps({
  'status': 'abstain',
  'block_reason': 'no_strong_popup_rectangle',
  'latency_ms': 1.0,
  'engine': {'name': 'fixture-engine', 'revision': 'r1'},
}, sort_keys=True))
"""
        )
        _, full_rows, full_summary = self.run_adapter(engine, self.root / "full")

        redacted = self.root / "redacted.jsonl"
        redacted_rows = []
        for source in self.manifest_rows:
            row = dict(source)
            for key in ("popup_present_gt", "sampling_stratum", "source_record_id"):
                row.pop(key, None)
            redacted_rows.append(row)
        redacted.write_text(
            "".join(json.dumps(row) + "\n" for row in redacted_rows),
            encoding="utf-8",
        )
        _, redacted_output, redacted_summary = self.run_adapter(
            engine, self.root / "redacted-out", redacted
        )
        self.assertEqual(full_rows, redacted_output)
        self.assertEqual(
            full_summary["visual_bank_sha256"],
            redacted_summary["visual_bank_sha256"],
        )

        drifted = self.root / "drifted.jsonl"
        drifted_rows = [dict(row) for row in redacted_rows]
        drifted_rows[0]["future_popup_label"] = True
        drifted.write_text(
            "".join(json.dumps(row) + "\n" for row in drifted_rows),
            encoding="utf-8",
        )
        from run_roi_ocr import AdapterBlocked, build_parser, run

        output = self.root / "drifted-out"
        args = build_parser().parse_args(
            [
                "--manifest",
                str(drifted),
                "--media-root",
                str(self.media),
                "--engine",
                str(engine),
                "--output-dir",
                str(output),
            ]
        )
        with self.assertRaisesRegex(AdapterBlocked, "unknown manifest fields"):
            run(args)
        self.assertFalse((output / "visual-bank.private.jsonl").exists())

    def test_invalid_positive_roi_blocks_the_whole_batch(self) -> None:
        """Break caught: malformed detector output leaves a partial private bank."""
        engine = self.write_engine(
            """
import json
print(json.dumps({
  'status': 'popup',
  'presence_confidence': 0.9,
  'roi_normalized_xyxy': [0.2, 0.2, 1.4, 0.8],
  'roi_confidence': 0.9,
  'message_text': 'bad box',
  'critical_facts': [],
  'latency_ms': 1.0,
  'engine': {'name': 'fixture-engine', 'revision': 'r1'},
}, sort_keys=True))
"""
        )
        from run_roi_ocr import AdapterBlocked, build_parser, run

        output = self.root / "blocked"
        args = build_parser().parse_args(
            [
                "--manifest",
                str(self.manifest),
                "--media-root",
                str(self.media),
                "--engine",
                str(engine),
                "--output-dir",
                str(output),
            ]
        )
        with self.assertRaisesRegex(AdapterBlocked, "ROI"):
            run(args)
        self.assertFalse((output / "visual-bank.private.jsonl").exists())
        blocker = json.loads((output / "run-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(blocker["status"], "blocked")
        self.assertEqual(blocker["completed_item_count"], 0)

    def test_verified_bank_projects_to_pregold_without_audit_or_label_fields(self) -> None:
        """Break caught: MG-PU consumes an unverified bank or forbidden audit keys."""
        engine = self.write_engine(
            """
import json, pathlib, sys
image = pathlib.Path(sys.argv[sys.argv.index('--image') + 1])
if image.read_bytes().endswith(b'one'):
    result = {
      'status': 'popup', 'presence_confidence': 0.91,
      'roi_normalized_xyxy': [0.1, 0.2, 0.9, 0.8], 'roi_confidence': 0.93,
      'message_text': 'Visible offer ends today', 'critical_facts': [],
      'latency_ms': 2.0, 'engine': {'name': 'fixture-engine', 'revision': 'r1'},
    }
else:
    result = {
      'status': 'abstain', 'block_reason': 'no_strong_popup_rectangle',
      'latency_ms': 1.0, 'engine': {'name': 'fixture-engine', 'revision': 'r1'},
    }
print(json.dumps(result, sort_keys=True))
"""
        )
        source_dir = self.root / "source"
        self.run_adapter(engine, source_dir)

        from export_pregold_visual_bank import build_parser, run

        private_output = self.root / "private" / "formal-visual.private.jsonl"
        projection_summary = self.root / "projection-summary.json"
        args = build_parser().parse_args(
            [
                "--protocol",
                str(source_dir / "protocol.json"),
                "--visual-bank",
                str(source_dir / "visual-bank.private.jsonl"),
                "--input-manifest",
                str(self.manifest),
                "--public-summary",
                str(source_dir / "public-summary.json"),
                "--private-output",
                str(private_output),
                "--projection-summary",
                str(projection_summary),
            ]
        )
        self.assertEqual(run(args), 0)
        projected = [
            json.loads(line)
            for line in private_output.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(projected[0]["status"], "judged")
        self.assertEqual(projected[0]["confidence"], 0.91)
        self.assertEqual(
            projected[0]["evidence_kind"], "frozen_private_visual_evidence_bank"
        )
        self.assertTrue(projected[0]["fixed_threshold_heuristic_adaptation"])
        self.assertTrue(
            projected[0]["repeat_execution_byte_identical_on_fixed_host"]
        )
        self.assertEqual(
            projected[0]["cross_os_or_device_model_identity_reproducible"],
            "not_verified",
        )
        self.assertEqual(projected[1]["status"], "abstain")
        serialized = json.dumps(projected)
        self.assertNotIn("source_sampling_label_used", serialized)
        self.assertNotIn("folder_label_used", serialized)
        self.assertNotIn("adjudication_used", serialized)
        self.assertNotIn("roi_normalized_xyxy", serialized)

        from pregold.freeze_predictions import _rows_by_visual_id

        normalized = _rows_by_visual_id(projected, set(self.images))
        self.assertEqual(normalized["PMJ-PILOT-001"]["status"], "judged")
        self.assertEqual(normalized["PMJ-PILOT-002"]["status"], "abstain")

    def test_pregold_projection_rejects_tampered_bank_without_partial_output(self) -> None:
        """Break caught: a bank row changes after freeze and still reaches MG-PU."""
        engine = self.write_engine(
            """
import json
print(json.dumps({
  'status': 'abstain', 'block_reason': 'no_strong_popup_rectangle',
  'latency_ms': 1.0, 'engine': {'name': 'fixture-engine', 'revision': 'r1'},
}, sort_keys=True))
"""
        )
        source_dir = self.root / "source"
        self.run_adapter(engine, source_dir)
        rows = [
            json.loads(line)
            for line in (source_dir / "visual-bank.private.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        rows[0]["input_image_sha256"] = "f" * 64
        (source_dir / "visual-bank.private.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )

        from export_pregold_visual_bank import AdapterBlocked, build_parser, run

        private_output = self.root / "private" / "formal-visual.private.jsonl"
        args = build_parser().parse_args(
            [
                "--protocol",
                str(source_dir / "protocol.json"),
                "--visual-bank",
                str(source_dir / "visual-bank.private.jsonl"),
                "--input-manifest",
                str(self.manifest),
                "--public-summary",
                str(source_dir / "public-summary.json"),
                "--private-output",
                str(private_output),
                "--projection-summary",
                str(self.root / "projection-summary.json"),
            ]
        )
        with self.assertRaisesRegex(AdapterBlocked, "image hash"):
            run(args)
        self.assertFalse(private_output.exists())


if __name__ == "__main__":
    unittest.main()
