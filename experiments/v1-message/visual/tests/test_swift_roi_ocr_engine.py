from __future__ import annotations

import json
from pathlib import Path
import platform
import subprocess
import tempfile
import unittest


VISUAL_DIR = Path(__file__).resolve().parents[1]
SOURCE = VISUAL_DIR / "vision_popup_roi_ocr.swift"


@unittest.skipUnless(platform.system() == "Darwin", "Apple Vision requires macOS")
class SwiftRoiOcrEngineTests(unittest.TestCase):
    def test_witness_detects_popup_rectangle_and_reads_visible_message(self) -> None:
        """Break caught: detector/OCR source or its positive ROI path is not runnable."""
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "vision-popup-roi-ocr"
            module_cache = Path(directory) / "module-cache"
            build = subprocess.run(
                [
                    "xcrun",
                    "--sdk",
                    "macosx",
                    "swiftc",
                    "-module-cache-path",
                    str(module_cache),
                    "-O",
                    str(SOURCE),
                    "-o",
                    str(binary),
                ],
                capture_output=True,
                text=True,
                timeout=180,
            )
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run(
                [str(binary), "--witness"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            payload = json.loads(run.stdout)

        self.assertEqual(payload["status"], "popup")
        self.assertGreaterEqual(payload["presence_confidence"], 0.82)
        left, top, right, bottom = payload["roi_normalized_xyxy"]
        self.assertTrue(0 <= left < right <= 1)
        self.assertTrue(0 <= top < bottom <= 1)
        self.assertIn("VISIBLE", payload["message_text"].upper())
        self.assertIn("OFFER", payload["message_text"].upper())
        self.assertEqual(payload["critical_facts"], [])
        self.assertEqual(payload["engine"]["cli_version"], "pmj-vision-popup-roi-ocr/1.0.0")


if __name__ == "__main__":
    unittest.main()
