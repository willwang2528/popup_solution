#!/usr/bin/env python3
"""Serve a loopback-only, metadata-blind viewer for popup annotation evidence."""

from __future__ import annotations

import argparse
import html
import ipaddress
import json
import re
import secrets
import stat
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ITEM_PATTERN = re.compile(r"PMJ-PILOT-[0-9]{3}")
TEMPLATE_KEYS = {
    "protocol_version",
    "batch_id",
    "pilot_item_id",
    "annotation_order",
    "adapter_item_handle",
    "annotator_role",
    "annotator_id_pseudonymous",
    "record_status",
    "presence_label",
    "message_text",
    "message_observability",
    "semantic_slots",
    "confidence",
    "evidence",
    "blindness_attestation",
    "annotation_started_at",
    "annotation_completed_at",
    "notes",
}


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


def load_blind_items(template_path: Path, adapter_root: Path) -> list[dict[str, Any]]:
    """Resolve canonical handles without opening coordinator-only metadata files."""

    template_path = Path(template_path)
    adapter_root = Path(adapter_root).resolve(strict=True)
    if not adapter_root.is_dir():
        raise ViewerError("adapter root is not a directory")

    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(template_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line, object_pairs_hook=_strict_object)
        except (json.JSONDecodeError, ViewerError) as exc:
            raise ViewerError(f"template line {line_number}: {exc}") from exc
        if not isinstance(row, dict) or set(row) != TEMPLATE_KEYS:
            raise ViewerError(f"template line {line_number}: unexpected annotation fields")
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


def render_item_page(
    *,
    items: list[dict[str, Any]],
    item_number: int,
    token: str,
    session_id: str,
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
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Blind popup annotation viewer</title>
<style>body{{font-family:system-ui,sans-serif;max-width:960px;margin:24px auto;padding:0 16px;background:#111;color:#eee}}nav{{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}}a{{color:#8cc8ff}}img{{display:block;max-width:100%;height:auto;margin:auto;border:1px solid #555}}code{{user-select:all}}</style>
</head><body>
<nav>{previous_link}<strong>{html.escape(item['pilot_item_id'])} ({item_number}/{len(items)})</strong>{next_link}</nav>
<p>Annotator {html.escape(item['annotator_role'])} · view_session_id: <code>{html.escape(session_id)}</code></p>
<img src="/{token}/media/{item_number}" alt="待标注移动端截图">
<p>本查看器只展示冻结截图。请在私有 annotation 工作副本中记录结果；不要复制图像。</p>
</body></html>"""


def make_handler(*, items: list[dict[str, Any]], token: str, session_id: str):
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
                    page = render_item_page(
                        items=items,
                        item_number=number,
                        token=token,
                        session_id=session_id,
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

        def log_message(self, _format: str, *_args: Any) -> None:
            return

    return BlindViewerHandler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations-template", type=Path, required=True)
    parser.add_argument("--adapter-root", type=Path, required=True)
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validate_bind_host(args.bind)
    if not 0 <= args.port <= 65535:
        raise ViewerError("port must be between 0 and 65535")
    items = load_blind_items(args.annotations_template, args.adapter_root)
    token = secrets.token_urlsafe(24)
    session_id = f"view-{uuid.uuid4().hex}"
    handler = make_handler(items=items, token=token, session_id=session_id)
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
