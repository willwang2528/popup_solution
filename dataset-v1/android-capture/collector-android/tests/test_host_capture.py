from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import host_capture


class HostCaptureContractTests(unittest.TestCase):
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
