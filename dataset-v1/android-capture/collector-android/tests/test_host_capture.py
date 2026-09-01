from __future__ import annotations

from contextlib import redirect_stderr
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import host_capture


class HostCaptureContractTests(unittest.TestCase):
    def test_rejection_reason_allowlist_matches_collector_source(self):
        collector_root = Path(__file__).resolve().parents[1]
        coordinator = (
            collector_root
            / "app/src/main/java/org/pmab/collector/CaptureCoordinator.java"
        ).read_text(encoding="utf-8")
        timing_gate = (
            collector_root
            / "app/src/main/java/org/pmab/collector/core/CaptureTimingGate.java"
        ).read_text(encoding="utf-8")
        static_reasons = set(
            re.findall(r'reject(?:AndRelease)?\(request, "([a-z0-9_]+)"', coordinator)
        )
        static_reasons.update(
            re.findall(r'new TimingDecision\(false, "([a-z0-9_]+)"', timing_gate)
        )
        static_reasons.discard("screenshot_error_")
        self.assertEqual(static_reasons, set(host_capture.REJECTED_MACHINE_REASONS))
        self.assertIn('"screenshot_error_" + errorCode', coordinator)
        self.assertIsNotNone(host_capture.SCREENSHOT_ERROR_REASON.fullmatch("screenshot_error_2"))
        self.assertIsNone(host_capture.SCREENSHOT_ERROR_REASON.fullmatch("screenshot_error_-1"))

    def test_request_validation_matches_apk_contract_and_rejects_labels(self):
        request = self.valid_request()
        host_capture.validate_request(request)

        request["prediction"] = "popup"
        with self.assertRaisesRegex(ValueError, "exactly"):
            host_capture.validate_request(request)

        request = self.valid_request()
        request["capture_id"] = "../escape"
        with self.assertRaisesRegex(ValueError, "capture_id"):
            host_capture.validate_request(request)

    def test_complete_bundle_is_hash_bound_and_machine_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            payloads = {
                "tree-before.json": b'{"before":true}',
                "tree-after.json": b'{"after":true}',
                "screenshot.png": b"\x89PNG\r\n\x1a\nfixture",
            }
            for filename, content in payloads.items():
                (root / filename).write_bytes(content)
            machine = {
                "schema_version": "1.1",
                "machine_status": "complete",
                "machine_reason": "accepted",
                "request": self.valid_request(),
                "artifacts": {
                    key: {
                        "filename": filename,
                        "bytes": len(payloads[filename]),
                        "sha256": hashlib.sha256(payloads[filename]).hexdigest(),
                    }
                    for key, filename in {
                        "tree_before": "tree-before.json",
                        "tree_after": "tree-after.json",
                        "screenshot": "screenshot.png",
                    }.items()
                },
            }
            (root / "machine-capture.json").write_text(json.dumps(machine))
            host_capture.verify_pulled_bundle(root, self.valid_request())

            machine["privacy_review_status"] = "passed"
            (root / "machine-capture.json").write_text(json.dumps(machine))
            with self.assertRaisesRegex(ValueError, "human decision"):
                host_capture.verify_pulled_bundle(root, self.valid_request())

    def test_tampered_artifact_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "tree-before.json").write_bytes(b"changed")
            machine = {
                "schema_version": "1.1",
                "machine_status": "complete",
                "machine_reason": "accepted",
                "request": self.valid_request(),
                "artifacts": {
                    "tree_before": {
                        "filename": "tree-before.json",
                        "bytes": 7,
                        "sha256": "0" * 64,
                    }
                },
            }
            (root / "machine-capture.json").write_text(json.dumps(machine))
            with self.assertRaisesRegex(ValueError, "sha256"):
                host_capture.verify_pulled_bundle(root, self.valid_request())

    def test_rejected_bundle_fails_closed_without_publishing_success_path(self):
        request = self.valid_request()
        machine = {
            "schema_version": "1.1",
            "machine_status": "rejected",
            "machine_reason": "expected_target_package_absent",
            "request": request,
            "artifacts": {},
        }
        machine_bytes = json.dumps(machine).encode("utf-8")
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "incoming" / request["capture_id"]
            with (
                patch.object(host_capture, "_remote_file_exists", return_value=True),
                patch.object(host_capture, "_read_remote_file", return_value=machine_bytes),
            ):
                with self.assertRaisesRegex(
                    host_capture.CollectorRejectedError,
                    "expected_target_package_absent",
                ):
                    host_capture.pull_bundle(
                        Path("adb"), "serial", request, output, timeout_seconds=0.1
                    )
            self.assertFalse(output.exists())
            self.assertEqual(list(output.parent.glob(".*.partial-*")), [])

    def test_complete_bundle_publishes_atomically_after_hash_verification(self):
        request = self.valid_request()
        payloads = {
            "tree-before.json": b'{"before":true}',
            "tree-after.json": b'{"after":true}',
            "screenshot.png": b"\x89PNG\r\n\x1a\nfixture",
        }
        machine = {
            "schema_version": "1.1",
            "machine_status": "complete",
            "machine_reason": "accepted",
            "request": request,
            "artifacts": {
                key: {
                    "filename": filename,
                    "bytes": len(payloads[filename]),
                    "sha256": hashlib.sha256(payloads[filename]).hexdigest(),
                }
                for key, filename in {
                    "tree_before": "tree-before.json",
                    "tree_after": "tree-after.json",
                    "screenshot": "screenshot.png",
                }.items()
            },
        }
        machine_bytes = json.dumps(machine).encode("utf-8")

        def read_remote(_adb, _serial, remote_path):
            if remote_path.endswith("machine-capture.json"):
                return machine_bytes
            return payloads[Path(remote_path).name]

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "incoming" / request["capture_id"]
            with (
                patch.object(host_capture, "_remote_file_exists", return_value=True),
                patch.object(host_capture, "_read_remote_file", side_effect=read_remote),
            ):
                host_capture.pull_bundle(
                    Path("adb"), "serial", request, output, timeout_seconds=0.1
                )
            self.assertTrue(output.is_dir())
            self.assertEqual(
                (output / "machine-capture.json").read_bytes(), machine_bytes
            )
            for filename, expected in payloads.items():
                self.assertEqual((output / filename).read_bytes(), expected)
            self.assertEqual(list(output.parent.glob(".*.partial-*")), [])

    def test_rejected_bundle_requires_allowlisted_machine_reason(self):
        request = self.valid_request()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for reason in (None, "accepted", "../../unsafe"):
                machine = {
                    "schema_version": "1.1",
                    "machine_status": "rejected",
                    "request": request,
                    "artifacts": {},
                }
                if reason is not None:
                    machine["machine_reason"] = reason
                (root / "machine-capture.json").write_text(json.dumps(machine))
                with self.assertRaisesRegex(ValueError, "machine_reason"):
                    host_capture.verify_pulled_bundle(root, request)

    def test_capture_cli_returns_two_and_reports_rejection_reason(self):
        request = self.valid_request()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request_path = root / "request.json"
            request_path.write_text(json.dumps(request))
            error = io.StringIO()
            with (
                patch.object(host_capture, "inject_request"),
                patch.object(
                    host_capture,
                    "pull_bundle",
                    side_effect=host_capture.CollectorRejectedError(
                        "synchronization_delta_exceeded"
                    ),
                ),
                redirect_stderr(error),
            ):
                result = host_capture.cli(
                    [
                        "--adb",
                        "adb",
                        "--serial",
                        "serial",
                        "capture",
                        "--request-json",
                        str(request_path),
                        "--output",
                        str(root / "output"),
                    ]
                )
            self.assertEqual(result, 2)
            self.assertEqual(
                error.getvalue(),
                "error: collector rejected capture: synchronization_delta_exceeded\n",
            )

    def test_apk_attestation_binds_local_installed_certificate_and_source(self):
        source_revision = "c" * 40
        with tempfile.TemporaryDirectory() as temp_dir:
            apk = Path(temp_dir) / "collector.apk"
            with zipfile.ZipFile(apk, "w") as archive:
                archive.writestr("classes.dex", b"prefix" + source_revision.encode() + b"suffix")
            apk_bytes = apk.read_bytes()
            certificate = "d" * 64
            attestation = host_capture.make_apk_attestation(
                apk,
                apk_bytes,
                f"Signer #1 certificate SHA-256 digest: {certificate}\n",
                source_revision,
                "device-serial",
            )
            self.assertEqual(attestation["status"], "verified")
            self.assertEqual(attestation["local_apk_sha256"], hashlib.sha256(apk_bytes).hexdigest())
            self.assertEqual(attestation["installed_apk_sha256"], attestation["local_apk_sha256"])
            self.assertEqual(attestation["signing_certificate_sha256"], certificate)
            self.assertNotEqual(attestation["device_serial_sha256"], "device-serial")

            with self.assertRaisesRegex(ValueError, "installed APK"):
                host_capture.make_apk_attestation(
                    apk,
                    b"different",
                    f"Signer #1 certificate SHA-256 digest: {certificate}\n",
                    source_revision,
                    "device-serial",
                )

    @staticmethod
    def valid_request() -> dict[str, str]:
        return {
            "schema_version": "1.1",
            "capture_id": "PMAB-A-CAP-001",
            "item_id": "PMAB-0001",
            "source_group_id": "SG-001",
            "popup_template_family_id": "PF-dialog",
            "intended_stratum": "no_popup_candidate",
            "expected_target_package": "org.example.target",
            "request_nonce": "bd33d879debc4c38",
        }


if __name__ == "__main__":
    unittest.main()
