#!/usr/bin/env python3
"""Host-side trigger and readback for the action-free PMAB Android collector."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid
from typing import Any
import zipfile


PACKAGE = "org.pmab.collector"
SERVICE = f"{PACKAGE}/.PmabCaptureService"
REQUIRED_REQUEST_KEYS = {
    "schema_version",
    "capture_id",
    "item_id",
    "source_group_id",
    "popup_template_family_id",
    "intended_stratum",
    "expected_target_package",
    "request_nonce",
}
SAFE_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
PACKAGE_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+\Z")
NONCE = re.compile(r"[A-Fa-f0-9]{16,64}\Z")
HUMAN_DECISION_KEYS = {
    "privacy_review_status",
    "gold_label",
    "gold_labels",
    "prediction",
    "predictions",
    "method_prediction",
    "paper_result_eligible",
}
COMPLETE_ARTIFACTS = {
    "tree_before": "tree-before.json",
    "tree_after": "tree-after.json",
    "screenshot": "screenshot.png",
}


def validate_request(request: dict[str, Any]) -> None:
    if set(request) != REQUIRED_REQUEST_KEYS:
        raise ValueError("request must contain exactly the V1.1 machine-trigger keys")
    if not all(isinstance(value, str) for value in request.values()):
        raise ValueError("request values must all be strings")
    if request["schema_version"] != "1.1":
        raise ValueError("unsupported schema_version")
    for key in ("capture_id", "item_id", "source_group_id", "popup_template_family_id"):
        if not SAFE_IDENTIFIER.fullmatch(request[key]):
            raise ValueError(f"invalid {key}")
    if request["intended_stratum"] not in {
        "popup_candidate",
        "no_popup_candidate",
        "boundary_candidate",
    }:
        raise ValueError("intended_stratum is outside the frozen V1 strata")
    if not PACKAGE_NAME.fullmatch(request["expected_target_package"]):
        raise ValueError("invalid expected_target_package")
    if not NONCE.fullmatch(request["request_nonce"]):
        raise ValueError("invalid request_nonce")


def _contains_human_decision(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            key in HUMAN_DECISION_KEYS or _contains_human_decision(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_human_decision(child) for child in value)
    return False


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_apk_attestation(
    collector_apk: Path,
    installed_apk_bytes: bytes,
    apksigner_output: str,
    source_revision: str,
    device_serial: str,
    capture_id: str | None = None,
) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", source_revision):
        raise ValueError("source revision must be a 40-character Git SHA")
    if not collector_apk.is_file() or collector_apk.is_symlink():
        raise ValueError("collector APK must be a regular local file")
    local_apk_bytes = collector_apk.read_bytes()
    local_hash = hashlib.sha256(local_apk_bytes).hexdigest()
    installed_hash = hashlib.sha256(installed_apk_bytes).hexdigest()
    if local_hash != installed_hash:
        raise ValueError("installed APK does not match the local collector APK")
    with zipfile.ZipFile(collector_apk) as archive:
        dex = b"".join(
            archive.read(name)
            for name in archive.namelist()
            if name.startswith("classes") and name.endswith(".dex")
        )
    if source_revision.encode() not in dex or b"uncommitted" in dex:
        raise ValueError("collector APK is not bound to the expected source revision")
    certificate_match = re.search(
        r"Signer #1 certificate SHA-256 digest:\s*([0-9a-fA-F]{64})",
        apksigner_output,
    )
    if certificate_match is None:
        raise ValueError("apksigner did not report a signer certificate SHA-256 digest")
    attestation: dict[str, Any] = {
        "schema_version": "1.1",
        "status": "verified",
        "source_revision": source_revision,
        "local_apk_sha256": local_hash,
        "installed_apk_sha256": installed_hash,
        "signing_certificate_sha256": certificate_match.group(1).lower(),
        "device_serial_sha256": hashlib.sha256(device_serial.encode()).hexdigest(),
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }
    if capture_id is not None:
        if not SAFE_IDENTIFIER.fullmatch(capture_id):
            raise ValueError("invalid capture_id")
        attestation["capture_id"] = capture_id
    return attestation


def verify_pulled_bundle(bundle: Path, request: dict[str, str]) -> None:
    validate_request(request)
    machine_path = bundle / "machine-capture.json"
    if not machine_path.is_file():
        raise ValueError("machine-capture.json missing")
    machine = json.loads(machine_path.read_text(encoding="utf-8"))
    if _contains_human_decision(machine):
        raise ValueError("machine output contains a human decision or prediction")
    if machine.get("schema_version") != "1.1":
        raise ValueError("machine schema mismatch")
    if machine.get("request") != request:
        raise ValueError("machine request binding mismatch")
    status = machine.get("machine_status")
    if status not in {"complete", "rejected"}:
        raise ValueError("invalid machine_status")
    artifacts = machine.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("artifacts must be an object")

    for key, record in artifacts.items():
        if key not in COMPLETE_ARTIFACTS or not isinstance(record, dict):
            raise ValueError("unexpected artifact record")
        filename = record.get("filename")
        if filename != COMPLETE_ARTIFACTS[key]:
            raise ValueError("artifact filename mismatch")
        artifact_path = bundle / filename
        if not artifact_path.is_file():
            raise ValueError(f"artifact missing: {filename}")
        if artifact_path.stat().st_size != record.get("bytes"):
            raise ValueError(f"artifact byte count mismatch: {filename}")
        if _sha256(artifact_path) != record.get("sha256"):
            raise ValueError(f"artifact sha256 mismatch: {filename}")

    if status == "complete" and artifacts != {
        key: artifacts.get(key) for key in COMPLETE_ARTIFACTS
    }:
        raise ValueError("complete bundle artifact set mismatch")
    if status == "complete" and set(artifacts) != set(COMPLETE_ARTIFACTS):
        raise ValueError("complete bundle artifact set mismatch")
    if status == "rejected" and artifacts:
        raise ValueError("rejected bundle must not contain capture artifacts")


def _adb(
    adb: Path,
    serial: str,
    arguments: list[str],
    *,
    input_bytes: bytes | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        [str(adb), "-s", serial, *arguments],
        input=input_bytes,
        capture_output=True,
        check=False,
    )
    if check and completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"adb command failed: {stderr or completed.returncode}")
    return completed


def doctor(adb: Path, serial: str) -> dict[str, Any]:
    state = _adb(adb, serial, ["get-state"]).stdout.decode().strip()
    package = _adb(adb, serial, ["shell", "pm", "path", PACKAGE], check=False)
    run_as = _adb(
        adb,
        serial,
        ["shell", "run-as", PACKAGE, "sh", "-c", "test -d files"],
        check=False,
    )
    enabled = _adb(
        adb,
        serial,
        ["shell", "settings", "get", "secure", "enabled_accessibility_services"],
        check=False,
    ).stdout.decode("utf-8", errors="replace")
    return {
        "serial": serial,
        "device_state": state,
        "package_installed": package.returncode == 0 and b"package:" in package.stdout,
        "debug_run_as_ready": run_as.returncode == 0,
        "collector_service_enabled": SERVICE in enabled,
    }


def inject_request(adb: Path, serial: str, request: dict[str, str]) -> None:
    validate_request(request)
    stem = f"{request['capture_id']}.{request['request_nonce']}"
    temporary = f"files/capture_requests/{stem}.tmp"
    destination = f"files/capture_requests/{stem}.request"
    script = (
        "umask 077; mkdir -p files/capture_requests; "
        f"dd of={temporary} status=none; mv {temporary} {destination}"
    )
    payload = json.dumps(request, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    _adb(
        adb,
        serial,
        ["exec-in", "run-as", PACKAGE, "sh", "-c", script],
        input_bytes=payload,
    )


def _remote_file_exists(adb: Path, serial: str, path: str) -> bool:
    completed = _adb(
        adb,
        serial,
        ["shell", "run-as", PACKAGE, "sh", "-c", f"test -f {path}"],
        check=False,
    )
    return completed.returncode == 0


def _read_remote_file(adb: Path, serial: str, path: str) -> bytes:
    return _adb(
        adb,
        serial,
        ["exec-out", "run-as", PACKAGE, "cat", path],
    ).stdout


def pull_bundle(
    adb: Path,
    serial: str,
    request: dict[str, str],
    output: Path,
    timeout_seconds: float,
) -> None:
    validate_request(request)
    if output.exists():
        raise ValueError("output directory already exists")
    remote_root = f"files/capture_bundles/{request['capture_id']}"
    remote_machine = f"{remote_root}/machine-capture.json"
    deadline = time.monotonic() + timeout_seconds
    while not _remote_file_exists(adb, serial, remote_machine):
        if time.monotonic() >= deadline:
            raise TimeoutError("collector bundle did not appear before timeout")
        time.sleep(0.25)

    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.parent / f".{output.name}.partial-{uuid.uuid4().hex}"
    partial.mkdir()
    try:
        machine_bytes = _read_remote_file(adb, serial, remote_machine)
        (partial / "machine-capture.json").write_bytes(machine_bytes)
        machine = json.loads(machine_bytes.decode("utf-8"))
        artifacts = machine.get("artifacts", {})
        if not isinstance(artifacts, dict):
            raise ValueError("remote artifacts field is invalid")
        for key, record in artifacts.items():
            if key not in COMPLETE_ARTIFACTS or not isinstance(record, dict):
                raise ValueError("remote artifact is not allowlisted")
            filename = record.get("filename")
            if filename != COMPLETE_ARTIFACTS[key]:
                raise ValueError("remote artifact filename mismatch")
            (partial / filename).write_bytes(
                _read_remote_file(adb, serial, f"{remote_root}/{filename}")
            )
        (partial / "request.json").write_text(
            json.dumps(request, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        verify_pulled_bundle(partial, request)
        os.replace(partial, output)
    except Exception:
        shutil.rmtree(partial, ignore_errors=True)
        raise


def attest_installed_apk(
    adb: Path,
    serial: str,
    request: dict[str, str],
    collector_apk: Path,
    apksigner: Path,
    source_revision: str,
) -> dict[str, Any]:
    validate_request(request)
    package_paths = _adb(adb, serial, ["shell", "pm", "path", PACKAGE]).stdout.decode(
        "utf-8", errors="replace"
    )
    paths = [line.removeprefix("package:").strip() for line in package_paths.splitlines() if line.startswith("package:")]
    if not paths:
        raise ValueError("installed collector APK path was not reported")
    base_path = next((path for path in paths if path.endswith("/base.apk")), paths[0])
    installed_bytes = _read_remote_file(adb, serial, base_path)
    signer = subprocess.run(
        [str(apksigner), "verify", "--print-certs", str(collector_apk)],
        check=False,
        capture_output=True,
        text=True,
    )
    if signer.returncode != 0:
        raise RuntimeError(f"apksigner verification failed: {signer.stderr.strip()}")
    return make_apk_attestation(
        collector_apk,
        installed_bytes,
        signer.stdout,
        source_revision,
        serial,
        request["capture_id"],
    )


def _load_request(path: Path) -> dict[str, str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("request JSON must be an object")
    validate_request(value)
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", type=Path, default=Path("adb"))
    parser.add_argument("--serial", required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor")
    request = subparsers.add_parser("request")
    request.add_argument("--request-json", type=Path, required=True)
    capture = subparsers.add_parser("capture")
    capture.add_argument("--request-json", type=Path, required=True)
    capture.add_argument("--output", type=Path, required=True)
    capture.add_argument("--timeout-seconds", type=float, default=30.0)
    attest = subparsers.add_parser("attest")
    attest.add_argument("--request-json", type=Path, required=True)
    attest.add_argument("--collector-apk", type=Path, required=True)
    attest.add_argument("--apksigner", type=Path, required=True)
    attest.add_argument("--source-revision", required=True)
    attest.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        result = doctor(args.adb, args.serial)
        print(json.dumps(result, indent=2))
        return 0 if all(result.values()) else 2
    request = _load_request(args.request_json)
    if args.command == "request":
        inject_request(args.adb, args.serial, request)
        return 0
    if args.command == "attest":
        if args.output.exists():
            raise ValueError("attestation output already exists")
        attestation = attest_installed_apk(
            args.adb,
            args.serial,
            request,
            args.collector_apk,
            args.apksigner,
            args.source_revision,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(attestation, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return 0
    inject_request(args.adb, args.serial, request)
    pull_bundle(args.adb, args.serial, request, args.output, args.timeout_seconds)
    print(str(args.output.resolve()))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, TimeoutError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
