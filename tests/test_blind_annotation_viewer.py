from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIEWER = (
    ROOT
    / "dataset-v1"
    / "annotation-pilot"
    / "scripts"
    / "serve_blind_viewer.py"
)


def load_module():
    if not VIEWER.is_file():
        raise AssertionError("blind annotation viewer must exist")
    spec = importlib.util.spec_from_file_location("blind_annotation_viewer", VIEWER)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load blind annotation viewer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def blind_template_row(item_id: str = "PMJ-PILOT-001") -> dict:
    return {
        "protocol_version": "1.0.0",
        "batch_id": "popsweeper-message-pilot-30-v1",
        "pilot_item_id": item_id,
        "annotation_order": 1,
        "adapter_item_handle": f"adapter://popsweeper/pilot/{item_id}",
        "annotator_role": "A",
        "annotator_id_pseudonymous": None,
        "record_status": "blank",
        "presence_label": None,
        "message_text": None,
        "message_observability": None,
        "semantic_slots": [],
        "confidence": None,
        "evidence": {
            "adapter_viewed": False,
            "view_session_id": None,
            "region_or_node_notes": None,
            "raw_image_copied": False,
        },
        "blindness_attestation": {
            "peer_labels_unseen": False,
            "source_class_unseen": False,
            "model_output_unseen": False,
        },
        "annotation_started_at": None,
        "annotation_completed_at": None,
        "notes": None,
    }


class BlindAnnotationViewerTests(unittest.TestCase):
    def test_image_content_type_uses_magic_bytes_not_filename_suffix(self) -> None:
        module = load_module()

        self.assertEqual(
            module.sniff_image_content_type(b"\xff\xd8\xff\xe0jpeg-payload"),
            "image/jpeg",
        )
        self.assertEqual(
            module.sniff_image_content_type(b"\x89PNG\r\n\x1a\npng-payload"),
            "image/png",
        )

    def test_unknown_image_content_is_rejected(self) -> None:
        module = load_module()

        with self.assertRaisesRegex(module.ViewerError, "unsupported image format"):
            module.sniff_image_content_type(b"not-an-image")

    def test_view_model_never_reads_or_renders_coordinator_metadata(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            adapter_root = root / "annotation-media"
            item_root = adapter_root / "PMJ-PILOT-001"
            item_root.mkdir(parents=True)
            (item_root / "popsweeper-screenshot.jpg").write_bytes(b"jpeg-test")
            (item_root / "candidate.json").write_text(
                json.dumps(
                    {
                        "source_sampling_label": "ads",
                        "popup_present_gt": True,
                        "model_prediction": "SECRET_MODEL_OUTPUT",
                    }
                ),
                encoding="utf-8",
            )
            template = root / "annotator-a.jsonl"
            template.write_text(json.dumps(blind_template_row()) + "\n", encoding="utf-8")

            items = module.load_blind_items(template, adapter_root)
            html = module.render_item_page(
                items=items,
                item_number=1,
                token="viewer-token",
                session_id="view-session-123",
            )

            self.assertEqual(len(items), 1)
            self.assertEqual(
                set(items[0]),
                {"pilot_item_id", "annotation_order", "annotator_role", "image_path"},
            )
            self.assertNotIn("ads", html)
            self.assertNotIn("popup_present_gt", html)
            self.assertNotIn("SECRET_MODEL_OUTPUT", html)
            self.assertNotIn(str(adapter_root), html)
            self.assertNotIn("candidate.json", html)
            self.assertIn("view-session-123", html)
            self.assertIn("/viewer-token/media/1", html)

    def test_noncanonical_adapter_handle_is_rejected(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            adapter_root = root / "annotation-media"
            adapter_root.mkdir()
            row = blind_template_row("PMJ-PILOT-001")
            row["adapter_item_handle"] = "adapter://popsweeper/pilot/../../secret"
            template = root / "annotator-a.jsonl"
            template.write_text(json.dumps(row) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(module.ViewerError, "adapter handle"):
                module.load_blind_items(template, adapter_root)

    def test_viewer_refuses_non_loopback_bind(self) -> None:
        module = load_module()
        for host in ("0.0.0.0", "::", "192.168.1.10"):
            with self.subTest(host=host):
                with self.assertRaisesRegex(module.ViewerError, "loopback"):
                    module.validate_bind_host(host)


if __name__ == "__main__":
    unittest.main()
