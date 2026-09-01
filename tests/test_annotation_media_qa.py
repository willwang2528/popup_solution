from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "dataset-v1"
    / "annotation-pilot"
    / "scripts"
    / "audit_annotation_media.py"
)


def load_module():
    if not SCRIPT.is_file():
        raise AssertionError("annotation media QA script must exist")
    spec = importlib.util.spec_from_file_location("annotation_media_qa", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load annotation media QA script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AnnotationMediaQaTests(unittest.TestCase):
    def test_magic_bytes_drive_format_and_extension_mismatch_is_nonblocking(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            item_a = root / "PMJ-PILOT-001"
            item_b = root / "PMJ-PILOT-002"
            item_a.mkdir()
            item_b.mkdir()
            jpeg = item_a / "popsweeper-screenshot.jpg"
            png_under_jpg = item_b / "popsweeper-screenshot.jpg"
            jpeg.write_bytes(b"\xff\xd8\xff\xe0fixture-jpeg\xff\xd9")
            png_under_jpg.write_bytes(
                b"\x89PNG\r\n\x1a\n" + b"fixture-png"
            )
            freeze = {
                "batch_id": "fixture",
                "batch_size": 2,
                "media_files_sha256": {
                    "PMJ-PILOT-001/popsweeper-screenshot.jpg": sha256(jpeg),
                    "PMJ-PILOT-002/popsweeper-screenshot.jpg": sha256(png_under_jpg),
                },
            }
            freeze_path = root / "freeze.json"
            freeze_path.write_text(json.dumps(freeze), encoding="utf-8")

            report = module.audit_media(root, freeze_path)

        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["format_counts"], {"jpeg": 1, "png": 1})
        self.assertEqual(
            report["extension_mismatches"],
            [
                {
                    "pilot_item_id": "PMJ-PILOT-002",
                    "extension": ".jpg",
                    "detected_format": "png",
                }
            ],
        )
        self.assertEqual(report["hash_mismatches"], [])
        self.assertNotIn(str(root), json.dumps(report))

    def test_unknown_magic_or_hash_mismatch_blocks_media_qa(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            item = root / "PMJ-PILOT-001"
            item.mkdir()
            image = item / "popsweeper-screenshot.jpg"
            image.write_bytes(b"not-an-image")
            freeze_path = root / "freeze.json"
            freeze_path.write_text(
                json.dumps(
                    {
                        "batch_id": "fixture",
                        "batch_size": 1,
                        "media_files_sha256": {
                            "PMJ-PILOT-001/popsweeper-screenshot.jpg": "0" * 64
                        },
                    }
                ),
                encoding="utf-8",
            )

            report = module.audit_media(root, freeze_path)

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["unknown_format_items"], ["PMJ-PILOT-001"])
        self.assertEqual(report["hash_mismatches"], ["PMJ-PILOT-001"])


if __name__ == "__main__":
    unittest.main()
