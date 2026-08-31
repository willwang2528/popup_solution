import hashlib
import json
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "dataset-v1" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def load_audit_archive():
    try:
        from popsweeper_source_audit import audit_archive
    except (ImportError, ModuleNotFoundError) as exc:
        raise AssertionError("popsweeper_source_audit.audit_archive is missing") from exc
    return audit_archive


class PopSweeperSourceAuditTests(unittest.TestCase):
    def test_valid_archive_reports_hash_and_inventory(self):
        """Catches a parser that accepts a ZIP but omits integrity or inventory data."""
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "sample.zip"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("images/001.png", b"png-bytes")
                zf.writestr("labels/001.json", b'{"popup": true}')

            expected_md5 = hashlib.md5(archive.read_bytes()).hexdigest()
            audit_archive = load_audit_archive()
            result = audit_archive(
                archive,
                expected_size=archive.stat().st_size,
                expected_md5=expected_md5,
            )

            self.assertEqual("pass", result["status"])
            self.assertEqual(expected_md5, result["archive"]["md5"])
            self.assertEqual(2, result["inventory"]["member_count"])
            self.assertEqual({".json": 1, ".png": 1}, result["inventory"]["extension_counts"])
            self.assertIn("top_level_counts", result["inventory"])
            self.assertEqual({"images": 1, "labels": 1}, result["inventory"]["top_level_counts"])
            self.assertIn("sample_members", result["inventory"])
            self.assertEqual(
                ["images/001.png", "labels/001.json"],
                result["inventory"]["sample_members"],
            )
            self.assertEqual([], result["errors"])

    def test_integrity_mismatch_fails_the_audit(self):
        """Catches a source auditor that records expected values but never enforces them."""
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "sample.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("images/001.png", b"png-bytes")

            audit_archive = load_audit_archive()
            result = audit_archive(
                archive,
                expected_size=archive.stat().st_size + 1,
                expected_md5="0" * 32,
            )

            self.assertEqual("fail", result["status"])
            self.assertIn("size_mismatch", result["errors"])
            self.assertIn("md5_mismatch", result["errors"])

    def test_path_traversal_member_fails_the_audit(self):
        """Catches an extractor audit that permits a member to escape its target directory."""
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "traversal.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("../escape.txt", b"unsafe")

            audit_archive = load_audit_archive()
            result = audit_archive(archive)

            self.assertEqual("fail", result["status"])
            self.assertIn("unsafe_member_path", result["errors"])
            self.assertEqual(["../escape.txt"], result["safety"]["unsafe_paths"])

    def test_symlink_member_fails_the_audit(self):
        """Catches an audit that would later extract a symbolic link from untrusted input."""
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "symlink.zip"
            link = zipfile.ZipInfo("images/link")
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr(link, "../outside")

            audit_archive = load_audit_archive()
            result = audit_archive(archive)

            self.assertEqual("fail", result["status"])
            self.assertIn("unsafe_symlink", result["errors"])
            self.assertEqual(["images/link"], result["safety"]["symlinks"])

    def test_uncompressed_size_limit_fails_the_audit(self):
        """Catches an audit that trusts compressed size and misses archive expansion risk."""
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "large.zip"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("payload.txt", b"a" * 1024)

            audit_archive = load_audit_archive()
            try:
                result = audit_archive(archive, max_total_uncompressed_bytes=100)
            except TypeError as exc:
                self.fail(f"archive expansion limit is not implemented: {exc}")

            self.assertEqual("fail", result["status"])
            self.assertIn("uncompressed_size_limit", result["errors"])
            self.assertEqual(1024, result["safety"]["total_uncompressed_bytes"])

    def test_member_count_limit_fails_the_audit(self):
        """Catches an audit that permits pathological numbers of archive members."""
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "many.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                for index in range(3):
                    zf.writestr(f"items/{index}.txt", b"x")

            audit_archive = load_audit_archive()
            try:
                result = audit_archive(archive, max_members=2)
            except TypeError as exc:
                self.fail(f"archive member limit is not implemented: {exc}")

            self.assertEqual("fail", result["status"])
            self.assertIn("member_count_limit", result["errors"])
            self.assertEqual(3, result["inventory"]["member_count"])

    def test_expansion_ratio_limit_fails_the_audit(self):
        """Catches a compressed payload whose total bytes fit but expansion is suspicious."""
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "ratio.zip"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("payload.txt", b"a" * 100_000)

            audit_archive = load_audit_archive()
            try:
                result = audit_archive(archive, max_expansion_ratio=10.0)
            except TypeError as exc:
                self.fail(f"archive expansion ratio limit is not implemented: {exc}")

            self.assertEqual("fail", result["status"])
            self.assertIn("expansion_ratio_limit", result["errors"])
            self.assertGreater(result["safety"]["expansion_ratio"], 10.0)

    def test_cli_writes_json_report_and_returns_success(self):
        """Catches a library-only implementation that cannot produce the durable audit artifact."""
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "sample.zip"
            output = Path(tmp) / "audit.json"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("labels/001.json", b"{}")
            md5 = hashlib.md5(archive.read_bytes()).hexdigest()
            script = SCRIPTS_DIR / "popsweeper_source_audit.py"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    str(archive),
                    "--expected-size",
                    str(archive.stat().st_size),
                    "--expected-md5",
                    md5,
                    "--output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertTrue(output.exists())
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual("pass", report["status"])

    def test_non_zip_file_returns_a_failed_report(self):
        """Catches a malformed download that would otherwise crash before writing evidence."""
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "broken.zip"
            archive.write_bytes(b"not a zip")

            audit_archive = load_audit_archive()
            try:
                result = audit_archive(archive)
            except zipfile.BadZipFile as exc:
                self.fail(f"malformed ZIP was not converted to an audit result: {exc}")

            self.assertEqual("fail", result["status"])
            self.assertIn("invalid_zip", result["errors"])


if __name__ == "__main__":
    unittest.main()
