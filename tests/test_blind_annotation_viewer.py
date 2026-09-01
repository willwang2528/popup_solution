from __future__ import annotations

import importlib.util
import json
import os
import re
import tempfile
import threading
import unittest
from pathlib import Path
from urllib import parse, request


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
        "out_of_scope_reason": None,
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
    def test_rendered_form_fields_are_bound_to_shared_annotation_contract(self) -> None:
        """Break caught: the HTML form becomes a third drifting field allowlist."""
        module = load_module()
        item = {
            "pilot_item_id": "PMJ-PILOT-001",
            "annotation_order": 1,
            "annotator_role": "A",
            "image_path": Path("unused.jpg"),
        }
        template_row = blind_template_row()
        with tempfile.TemporaryDirectory() as directory:
            store = module.AnnotationStore(
                template_rows=[template_row],
                output_path=Path(directory) / "private" / "annotator_a.working.jsonl",
                session_id="view-session-123",
                annotator_pseudonym="human-a",
            )
            page = module.render_item_page(
                items=[item],
                item_number=1,
                token="viewer-token",
                session_id="view-session-123",
                annotation_store=store,
            )

        form_html = page.split("<form", 1)[1].split("</form>", 1)[0]
        rendered_names = set(re.findall(r'name="([^"]+)"', form_html))
        self.assertEqual(rendered_names, module.FORM_KEYS)
        self.assertEqual(set(module.FORM_FIELD_TARGETS), module.FORM_KEYS)
        self.assertTrue(
            set(module.FORM_FIELD_TARGETS.values()).issubset(module.TEMPLATE_KEYS)
        )

    def test_committed_a_and_b_templates_are_consumable(self) -> None:
        """Break caught: committed template schema drifts from the viewer consumer."""
        module = load_module()
        template_root = ROOT / "dataset-v1" / "annotation-pilot" / "templates"

        rows_a = module._read_template_rows(template_root / "annotator_a.jsonl")
        rows_b = module._read_template_rows(template_root / "annotator_b.jsonl")

        self.assertEqual(len(rows_a), 30)
        self.assertEqual(len(rows_b), 30)
        self.assertEqual({row["annotator_role"] for row in rows_a}, {"A"})
        self.assertEqual({row["annotator_role"] for row in rows_b}, {"B"})

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

    def test_real_template_shape_with_out_of_scope_field_is_accepted(self) -> None:
        """Break caught: the viewer rejects the committed annotation template schema."""
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            adapter_root = root / "annotation-media"
            item_root = adapter_root / "PMJ-PILOT-001"
            item_root.mkdir(parents=True)
            (item_root / "popsweeper-screenshot.jpg").write_bytes(
                b"\xff\xd8\xff\xe0fixture"
            )
            template = root / "annotator-a.jsonl"
            template.write_text(
                json.dumps(blind_template_row()) + "\n", encoding="utf-8"
            )

            items = module.load_blind_items(template, adapter_root)

            self.assertEqual(items[0]["pilot_item_id"], "PMJ-PILOT-001")
            self.assertNotIn("out_of_scope_reason", items[0])

    def test_loopback_form_writes_a_valid_private_completed_record(self) -> None:
        """Break caught: annotators can view images but cannot safely persist labels."""
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            adapter_root = root / "annotation-media"
            item_root = adapter_root / "PMJ-PILOT-001"
            item_root.mkdir(parents=True)
            (item_root / "popsweeper-screenshot.jpg").write_bytes(
                b"\xff\xd8\xff\xe0fixture"
            )
            template_row = blind_template_row()
            template = root / "annotator-a.jsonl"
            template.write_text(json.dumps(template_row) + "\n", encoding="utf-8")
            items = module.load_blind_items(template, adapter_root)
            output = root / "private" / "annotator_a.working.jsonl"
            store = module.AnnotationStore(
                template_rows=[template_row],
                output_path=output,
                session_id="view-session-123",
                annotator_pseudonym="human-a",
            )
            token = "viewer-token"
            handler = module.make_handler(
                items=items,
                token=token,
                session_id="view-session-123",
                annotation_store=store,
            )
            server = module.ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                body = parse.urlencode(
                    {
                        "presence_label": "popup",
                        "out_of_scope_reason": "",
                        "message_observability": "complete",
                        "message_text": "Offer ends today",
                        "semantic_slots_json": json.dumps(
                            [
                                {
                                    "slot_type": "duration_deadline",
                                    "value": "today",
                                    "polarity": "affirmed",
                                }
                            ]
                        ),
                        "confidence": "4",
                        "region_or_node_notes": "centered card",
                        "notes": "",
                        "peer_labels_unseen": "yes",
                        "source_class_unseen": "yes",
                        "model_output_unseen": "yes",
                    }
                ).encode("utf-8")
                with request.urlopen(
                    request.Request(
                        f"http://127.0.0.1:{server.server_port}/{token}/item/1",
                        data=body,
                        method="POST",
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                    )
                ) as response:
                    self.assertEqual(response.status, 200)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

            rows = [
                json.loads(line)
                for line in output.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(rows), 1)
            completed = rows[0]
            self.assertEqual(completed["record_status"], "completed")
            self.assertEqual(completed["annotator_id_pseudonymous"], "human-a")
            self.assertEqual(completed["message_text"], "Offer ends today")
            self.assertEqual(completed["evidence"]["view_session_id"], "view-session-123")
            self.assertTrue(completed["blindness_attestation"]["peer_labels_unseen"])
            self.assertEqual(os.stat(output).st_mode & 0o777, 0o600)
            serialized = json.dumps(completed)
            self.assertNotIn("source_sampling_label", serialized)
            self.assertNotIn("model_prediction", serialized)

    def test_completed_annotation_cannot_be_overwritten_by_replayed_post(self) -> None:
        """Break caught: replaying a token can silently replace a human label."""
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "private" / "annotator_a.working.jsonl"
            store = module.AnnotationStore(
                template_rows=[blind_template_row()],
                output_path=output,
                session_id="view-session-123",
                annotator_pseudonym="human-a",
            )
            fields = {
                "presence_label": "popup",
                "out_of_scope_reason": "",
                "message_observability": "complete",
                "message_text": "Offer ends today",
                "semantic_slots_json": "[]",
                "confidence": "4",
                "region_or_node_notes": "centered card",
                "notes": "",
                "peer_labels_unseen": "yes",
                "source_class_unseen": "yes",
                "model_output_unseen": "yes",
            }
            store.submit("PMJ-PILOT-001", fields)
            frozen_bytes = output.read_bytes()
            replay = dict(fields, message_text="Replacement text")

            with self.assertRaisesRegex(module.ViewerError, "immutable"):
                store.submit("PMJ-PILOT-001", replay)

            self.assertEqual(output.read_bytes(), frozen_bytes)

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
