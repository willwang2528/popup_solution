#!/usr/bin/env python3
"""Serve a loopback-only, metadata-blind viewer for popup annotation evidence."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import html
import ipaddress
import json
import os
import re
import secrets
import stat
import sys
import tempfile
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit


SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from calculate_agreement import (  # noqa: E402 - local protocol module
    ANNOTATION_KEYS,
    ProtocolError,
    validate_completed_annotation,
)


ITEM_PATTERN = re.compile(r"PMJ-PILOT-[0-9]{3}")
TEMPLATE_KEYS = set(ANNOTATION_KEYS)
FORM_FIELD_TARGETS = {
    "presence_label": "presence_label",
    "out_of_scope_reason": "out_of_scope_reason",
    "message_text": "message_text",
    "message_observability": "message_observability",
    "semantic_slots_json": "semantic_slots",
    "confidence": "confidence",
    "region_or_node_notes": "evidence",
    "notes": "notes",
    "peer_labels_unseen": "blindness_attestation",
    "source_class_unseen": "blindness_attestation",
    "model_output_unseen": "blindness_attestation",
}
if not set(FORM_FIELD_TARGETS.values()).issubset(TEMPLATE_KEYS):
    raise RuntimeError("form fields are not bound to the shared annotation contract")
FORM_KEYS = set(FORM_FIELD_TARGETS)
MAX_FORM_BYTES = 64 * 1024


class ViewerError(ValueError):
    """Raised when the viewer cannot preserve its blinding boundary."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise ViewerError(f"duplicate JSON key: {key}")
        output[key] = value
    return output


def validate_bind_host(host: str) -> None:
    if host == "localhost":
        return
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise ViewerError("viewer bind host must be a loopback address") from exc
    if not address.is_loopback:
        raise ViewerError("viewer bind host must be a loopback address")


def sniff_image_content_type(body: bytes) -> str:
    """Return the image media type from a minimal, explicit signature allowlist."""

    if body.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if body.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    raise ViewerError("unsupported image format")


def _regular_file_within(path: Path, root: Path) -> Path:
    if path.is_symlink():
        raise ViewerError(f"symlink evidence is forbidden: {path.name}")
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, ValueError) as exc:
        raise ViewerError(f"evidence is missing or outside adapter root: {path.name}") from exc
    if not stat.S_ISREG(resolved.stat().st_mode):
        raise ViewerError(f"evidence is not a regular file: {path.name}")
    return resolved


def _read_template_rows(template_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        Path(template_path).read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        try:
            row = json.loads(line, object_pairs_hook=_strict_object)
        except (json.JSONDecodeError, ViewerError) as exc:
            raise ViewerError(f"template line {line_number}: {exc}") from exc
        if not isinstance(row, dict) or set(row) != TEMPLATE_KEYS:
            raise ViewerError(f"template line {line_number}: unexpected annotation fields")
        rows.append(row)
    if not rows:
        raise ViewerError("blind template contains no items")
    return rows


def load_blind_items(template_path: Path, adapter_root: Path) -> list[dict[str, Any]]:
    """Resolve canonical handles without opening coordinator-only metadata files."""

    template_path = Path(template_path)
    adapter_root = Path(adapter_root).resolve(strict=True)
    if not adapter_root.is_dir():
        raise ViewerError("adapter root is not a directory")

    rows: list[dict[str, Any]] = []
    for line_number, row in enumerate(_read_template_rows(template_path), 1):
        item_id = row["pilot_item_id"]
        if not isinstance(item_id, str) or ITEM_PATTERN.fullmatch(item_id) is None:
            raise ViewerError(f"template line {line_number}: invalid pilot item")
        expected_handle = f"adapter://popsweeper/pilot/{item_id}"
        if row["adapter_item_handle"] != expected_handle:
            raise ViewerError(f"template line {line_number}: adapter handle is not canonical")
        order = row["annotation_order"]
        if isinstance(order, bool) or not isinstance(order, int) or order < 1:
            raise ViewerError(f"template line {line_number}: invalid annotation order")
        if row["annotator_role"] not in {"A", "B"}:
            raise ViewerError(f"template line {line_number}: invalid annotator role")

        item_root = adapter_root / item_id
        if item_root.is_symlink():
            raise ViewerError(f"{item_id}: symlink item directory is forbidden")
        try:
            item_root.resolve(strict=True).relative_to(adapter_root)
        except (FileNotFoundError, ValueError) as exc:
            raise ViewerError(f"{item_id}: adapter item directory is missing") from exc
        image_path = _regular_file_within(
            item_root / "popsweeper-screenshot.jpg", adapter_root
        )
        rows.append(
            {
                "pilot_item_id": item_id,
                "annotation_order": order,
                "annotator_role": row["annotator_role"],
                "image_path": image_path,
            }
        )

    if not rows:
        raise ViewerError("blind template contains no items")
    if len({row["pilot_item_id"] for row in rows}) != len(rows):
        raise ViewerError("blind template contains duplicate pilot items")
    if len({row["annotation_order"] for row in rows}) != len(rows):
        raise ViewerError("blind template contains duplicate annotation order")
    if len({row["annotator_role"] for row in rows}) != 1:
        raise ViewerError("blind template mixes annotator roles")
    rows.sort(key=lambda row: row["annotation_order"])
    if [row["annotation_order"] for row in rows] != list(range(1, len(rows) + 1)):
        raise ViewerError("blind template annotation order is not contiguous")
    return rows


def _optional_text(value: str) -> str | None:
    stripped = value.strip()
    return stripped or None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class AnnotationStore:
    """Atomically persist human-only completed rows beside the private template."""

    def __init__(
        self,
        *,
        template_rows: list[dict[str, Any]],
        output_path: Path,
        session_id: str,
        annotator_pseudonym: str,
    ) -> None:
        if not annotator_pseudonym.strip():
            raise ViewerError("annotator pseudonym must be non-empty")
        self.output_path = Path(output_path)
        if self.output_path.parent.name != "private" or self.output_path.suffix != ".jsonl":
            raise ViewerError("working output must be private/*.jsonl")
        if self.output_path.is_symlink() or self.output_path.parent.is_symlink():
            raise ViewerError("working output symlinks are forbidden")
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self.output_path.parent, 0o700)
        self.session_id = session_id
        self.annotator_pseudonym = annotator_pseudonym.strip()
        self._templates: dict[str, dict[str, Any]] = {}
        for row in template_rows:
            if not isinstance(row, dict) or set(row) != TEMPLATE_KEYS:
                raise ViewerError("annotation store received an invalid template row")
            item_id = row.get("pilot_item_id")
            if not isinstance(item_id, str) or ITEM_PATTERN.fullmatch(item_id) is None:
                raise ViewerError("annotation store received an invalid pilot item")
            if item_id in self._templates:
                raise ViewerError("annotation store received duplicate pilot items")
            self._templates[item_id] = deepcopy(row)
        if not self._templates:
            raise ViewerError("annotation store received no template rows")
        self._records = deepcopy(self._templates)
        self._started_at: dict[str, str] = {}
        self._lock = threading.Lock()
        if self.output_path.exists():
            self._load_existing()
        self._write()

    def _load_existing(self) -> None:
        rows: list[dict[str, Any]] = []
        for line_number, line in enumerate(
            self.output_path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if not line.strip():
                continue
            try:
                row = json.loads(line, object_pairs_hook=_strict_object)
            except (json.JSONDecodeError, ViewerError) as exc:
                raise ViewerError(
                    f"working output line {line_number}: invalid JSON"
                ) from exc
            if not isinstance(row, dict) or set(row) != TEMPLATE_KEYS:
                raise ViewerError(
                    f"working output line {line_number}: unexpected fields"
                )
            rows.append(row)
        by_id = {row.get("pilot_item_id"): row for row in rows}
        if len(by_id) != len(rows) or set(by_id) != set(self._templates):
            raise ViewerError("working output item set does not match template")
        for item_id, row in by_id.items():
            template = self._templates[item_id]
            for key in (
                "protocol_version",
                "batch_id",
                "pilot_item_id",
                "annotation_order",
                "adapter_item_handle",
                "annotator_role",
            ):
                if row.get(key) != template.get(key):
                    raise ViewerError(f"working output identity mismatch: {item_id}")
            if row.get("record_status") == "completed":
                try:
                    validate_completed_annotation(
                        row, expected_role=template["annotator_role"]
                    )
                except ProtocolError as exc:
                    raise ViewerError(f"invalid completed working row: {item_id}") from exc
                if row["annotator_id_pseudonymous"] != self.annotator_pseudonym:
                    raise ViewerError("working output annotator pseudonym mismatch")
                self._started_at[item_id] = row["annotation_started_at"]
            elif row.get("record_status") != "blank":
                raise ViewerError(f"working output row has invalid status: {item_id}")
        self._records = by_id

    def _write(self) -> None:
        ordered = sorted(
            self._records.values(), key=lambda row: row["annotation_order"]
        )
        payload = "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            for row in ordered
        ).encode("utf-8")
        with tempfile.NamedTemporaryFile(
            dir=self.output_path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.output_path)

    def mark_viewed(self, item_id: str) -> None:
        with self._lock:
            if item_id not in self._templates:
                raise ViewerError("unknown annotation item")
            self._started_at.setdefault(item_id, _utc_now())

    def progress(self) -> tuple[int, int]:
        with self._lock:
            completed = sum(
                row["record_status"] == "completed" for row in self._records.values()
            )
            return completed, len(self._records)

    def submit(self, item_id: str, fields: dict[str, str]) -> None:
        unknown = sorted(set(fields) - FORM_KEYS)
        if unknown:
            raise ViewerError(f"unknown form fields: {unknown}")
        missing = sorted(FORM_KEYS - set(fields))
        if missing:
            raise ViewerError(f"missing form fields: {missing}")
        with self._lock:
            if item_id not in self._templates:
                raise ViewerError("unknown annotation item")
            if self._records[item_id]["record_status"] == "completed":
                raise ViewerError("completed annotation is immutable")
            started_at = self._started_at.setdefault(item_id, _utc_now())
            row = deepcopy(self._templates[item_id])
            presence = fields["presence_label"]
            if presence not in {
                "popup",
                "no_popup",
                "uncertain",
                "unusable",
                "out_of_scope",
            }:
                raise ViewerError("invalid presence label")
            reason = _optional_text(fields["out_of_scope_reason"])
            observability = fields["message_observability"]
            message = _optional_text(fields["message_text"])
            try:
                confidence = int(fields["confidence"])
            except ValueError as exc:
                raise ViewerError("confidence must be 1..5") from exc
            if presence == "popup":
                if observability not in {"complete", "partial", "not_observable"}:
                    raise ViewerError("popup observability is invalid")
                if observability in {"complete", "partial"} and message is None:
                    raise ViewerError("observable popup requires message text")
                if observability == "not_observable":
                    message = None
                    slots: list[dict[str, Any]] = []
                else:
                    try:
                        slots = json.loads(fields["semantic_slots_json"] or "[]")
                    except json.JSONDecodeError as exc:
                        raise ViewerError("semantic slots must be valid JSON") from exc
            elif presence == "out_of_scope":
                if reason is None:
                    raise ViewerError("out-of-scope reason is required")
                observability = "not_applicable"
                message = None
                slots = []
            elif presence == "no_popup":
                reason = None
                observability = "not_applicable"
                message = None
                slots = []
            else:
                reason = None
                observability = "not_observable"
                message = None
                slots = []
            if presence != "out_of_scope":
                reason = None
            if not isinstance(slots, list):
                raise ViewerError("semantic slots must be a JSON array")
            attestations = {
                key: fields[key] in {"yes", "on", "true", "1"}
                for key in (
                    "peer_labels_unseen",
                    "source_class_unseen",
                    "model_output_unseen",
                )
            }
            row.update(
                {
                    "annotator_id_pseudonymous": self.annotator_pseudonym,
                    "record_status": "completed",
                    "presence_label": presence,
                    "out_of_scope_reason": reason,
                    "message_text": message,
                    "message_observability": observability,
                    "semantic_slots": slots,
                    "confidence": confidence,
                    "evidence": {
                        "adapter_viewed": True,
                        "view_session_id": self.session_id,
                        "region_or_node_notes": _optional_text(
                            fields["region_or_node_notes"]
                        ),
                        "raw_image_copied": False,
                    },
                    "blindness_attestation": attestations,
                    "annotation_started_at": started_at,
                    "annotation_completed_at": _utc_now(),
                    "notes": _optional_text(fields["notes"]),
                }
            )
            try:
                validate_completed_annotation(
                    row, expected_role=row["annotator_role"]
                )
            except ProtocolError as exc:
                raise ViewerError(str(exc)) from exc
            self._records[item_id] = row
            self._write()


def render_item_page(
    *,
    items: list[dict[str, Any]],
    item_number: int,
    token: str,
    session_id: str,
    annotation_store: AnnotationStore | None = None,
) -> str:
    if not 1 <= item_number <= len(items):
        raise ViewerError("item number is outside the blind template")
    item = items[item_number - 1]
    previous_link = (
        f'<a href="/{token}/item/{item_number - 1}">上一项</a>'
        if item_number > 1
        else "<span>上一项</span>"
    )
    next_link = (
        f'<a href="/{token}/item/{item_number + 1}">下一项</a>'
        if item_number < len(items)
        else "<span>下一项</span>"
    )
    form = ""
    progress = ""
    if annotation_store is not None:
        completed, total = annotation_store.progress()
        progress = f"<p>已完成：{completed}/{total}</p>"
        form = f"""
<form method="post" action="/{token}/item/{item_number}">
<fieldset><legend>1. 弹窗存在性</legend>
<label><input type="radio" name="presence_label" value="popup" required> popup</label>
<label><input type="radio" name="presence_label" value="no_popup"> no_popup</label>
<label><input type="radio" name="presence_label" value="uncertain"> uncertain</label>
<label><input type="radio" name="presence_label" value="unusable"> unusable</label>
<label><input type="radio" name="presence_label" value="out_of_scope"> out_of_scope</label>
<label>排除原因 <select name="out_of_scope_reason"><option value=""></option>
<option>captcha</option><option>risk_control</option><option>identity_authentication</option>
<option>payment_confirmation</option><option>permission_security_control</option>
<option>manual_review</option><option>other_predefined_exclusion</option></select></label>
</fieldset>
<fieldset><legend>2. 可见消息</legend>
<label>可观察性 <select name="message_observability" required>
<option value="complete">complete</option><option value="partial">partial</option>
<option value="not_observable">not_observable</option><option value="not_applicable">not_applicable</option>
</select></label>
<label>消息原文<textarea name="message_text" rows="4"></textarea></label>
<label>关键槽 JSON 数组<textarea name="semantic_slots_json" rows="5">[]</textarea></label>
</fieldset>
<fieldset><legend>3. 证据与置信度</legend>
<label>置信度 1–5 <input type="number" name="confidence" min="1" max="5" required></label>
<label>区域/节点备注<textarea name="region_or_node_notes" rows="2"></textarea></label>
<label>其他备注<textarea name="notes" rows="2"></textarea></label>
</fieldset>
<fieldset><legend>4. 盲法确认</legend>
<label><input type="checkbox" name="peer_labels_unseen" value="yes" required> 未查看另一标注者结果</label>
<label><input type="checkbox" name="source_class_unseen" value="yes" required> 未查看来源类别</label>
<label><input type="checkbox" name="model_output_unseen" value="yes" required> 未查看模型输出</label>
</fieldset>
<button type="submit">保存本项并继续</button>
</form>"""
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Blind popup annotation viewer</title>
<style>body{{font-family:system-ui,sans-serif;max-width:960px;margin:24px auto;padding:0 16px;background:#111;color:#eee}}nav{{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}}a{{color:#8cc8ff}}img{{display:block;max-width:100%;height:auto;margin:auto;border:1px solid #555}}code{{user-select:all}}fieldset{{margin:16px 0;padding:12px}}label{{display:block;margin:8px 0}}textarea,select,input[type=number]{{box-sizing:border-box;width:100%;margin-top:4px}}button{{padding:10px 16px}}</style>
</head><body>
<nav>{previous_link}<strong>{html.escape(item['pilot_item_id'])} ({item_number}/{len(items)})</strong>{next_link}</nav>
<p>Annotator {html.escape(item['annotator_role'])} · view_session_id: <code>{html.escape(session_id)}</code></p>
{progress}
<img src="/{token}/media/{item_number}" alt="待标注移动端截图">
<p>本查看器只展示冻结截图；不要复制图像。表单只写入本机私有工作副本。</p>
{form}
</body></html>"""


def make_handler(
    *,
    items: list[dict[str, Any]],
    token: str,
    session_id: str,
    annotation_store: AnnotationStore | None = None,
):
    class BlindViewerHandler(BaseHTTPRequestHandler):
        def _base_headers(self, status: int, content_type: str, length: int) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(length))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'",
            )
            self.end_headers()

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self._base_headers(status, content_type, len(body))
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            path = urlsplit(self.path).path
            if path == f"/{token}/":
                self.send_response(302)
                self.send_header("Location", f"/{token}/item/1")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return
            item_match = re.fullmatch(rf"/{re.escape(token)}/item/([0-9]+)", path)
            media_match = re.fullmatch(rf"/{re.escape(token)}/media/([0-9]+)", path)
            if item_match:
                number = int(item_match.group(1))
                try:
                    if annotation_store is not None and 1 <= number <= len(items):
                        annotation_store.mark_viewed(items[number - 1]["pilot_item_id"])
                    page = render_item_page(
                        items=items,
                        item_number=number,
                        token=token,
                        session_id=session_id,
                        annotation_store=annotation_store,
                    ).encode("utf-8")
                except ViewerError:
                    self._send(404, b"not found\n", "text/plain; charset=utf-8")
                    return
                self._send(200, page, "text/html; charset=utf-8")
                return
            if media_match:
                number = int(media_match.group(1))
                if not 1 <= number <= len(items):
                    self._send(404, b"not found\n", "text/plain; charset=utf-8")
                    return
                body = items[number - 1]["image_path"].read_bytes()
                try:
                    content_type = sniff_image_content_type(body)
                except ViewerError:
                    self._send(
                        415,
                        b"unsupported media type\n",
                        "text/plain; charset=utf-8",
                    )
                    return
                self._send(200, body, content_type)
                return
            self._send(404, b"not found\n", "text/plain; charset=utf-8")

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            path = urlsplit(self.path).path
            item_match = re.fullmatch(rf"/{re.escape(token)}/item/([0-9]+)", path)
            if annotation_store is None or item_match is None:
                self._send(404, b"not found\n", "text/plain; charset=utf-8")
                return
            number = int(item_match.group(1))
            if not 1 <= number <= len(items):
                self._send(404, b"not found\n", "text/plain; charset=utf-8")
                return
            if self.headers.get("Content-Type", "").split(";", 1)[0] != (
                "application/x-www-form-urlencoded"
            ):
                self._send(415, b"unsupported form type\n", "text/plain; charset=utf-8")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if not 0 < length <= MAX_FORM_BYTES:
                self._send(413, b"invalid form size\n", "text/plain; charset=utf-8")
                return
            try:
                parsed = parse_qs(
                    self.rfile.read(length).decode("utf-8"),
                    keep_blank_values=True,
                    strict_parsing=True,
                )
                if any(len(values) != 1 for values in parsed.values()):
                    raise ViewerError("duplicate form fields")
                fields = {key: values[0] for key, values in parsed.items()}
                annotation_store.submit(items[number - 1]["pilot_item_id"], fields)
            except (UnicodeDecodeError, ValueError, ViewerError) as exc:
                body = f"invalid annotation: {exc}\n".encode("utf-8")
                self._send(400, body, "text/plain; charset=utf-8")
                return
            next_number = number + 1 if number < len(items) else number
            self.send_response(303)
            self.send_header("Location", f"/{token}/item/{next_number}")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        def log_message(self, _format: str, *_args: Any) -> None:
            return

    return BlindViewerHandler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations-template", type=Path, required=True)
    parser.add_argument("--adapter-root", type=Path, required=True)
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--working-output", type=Path)
    parser.add_argument("--annotator-pseudonym")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validate_bind_host(args.bind)
    if not 0 <= args.port <= 65535:
        raise ViewerError("port must be between 0 and 65535")
    template_rows = _read_template_rows(args.annotations_template)
    items = load_blind_items(args.annotations_template, args.adapter_root)
    token = secrets.token_urlsafe(24)
    session_id = f"view-{uuid.uuid4().hex}"
    if (args.working_output is None) != (args.annotator_pseudonym is None):
        raise ViewerError(
            "working output and annotator pseudonym must be provided together"
        )
    annotation_store = (
        AnnotationStore(
            template_rows=template_rows,
            output_path=args.working_output,
            session_id=session_id,
            annotator_pseudonym=args.annotator_pseudonym,
        )
        if args.working_output is not None
        else None
    )
    handler = make_handler(
        items=items,
        token=token,
        session_id=session_id,
        annotation_store=annotation_store,
    )
    server = ThreadingHTTPServer((args.bind, args.port), handler)
    host, port = server.server_address[:2]
    print(
        json.dumps(
            {
                "status": "ready",
                "url": f"http://{host}:{port}/{token}/item/1",
                "view_session_id": session_id,
                "item_count": len(items),
                "annotator_role": items[0]["annotator_role"],
                "boundary": "screenshot_only_no_coordinator_metadata",
                "annotation_mode": (
                    "private_form_write" if annotation_store is not None else "view_only"
                ),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ViewerError as exc:
        raise SystemExit(f"viewer error: {exc}") from exc
