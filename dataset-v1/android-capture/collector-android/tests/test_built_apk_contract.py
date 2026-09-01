from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import unittest
import zipfile


class BuiltCollectorApkContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.apk = Path(os.environ.get("PMAB_COLLECTOR_APK", ""))
        cls.aapt2 = Path(os.environ.get("PMAB_AAPT2", ""))
        cls.expected_source_revision = os.environ.get("PMAB_EXPECTED_SOURCE_REVISION", "")
        if not cls.apk.is_file() or not cls.aapt2.is_file():
            raise AssertionError(
                "PMAB_COLLECTOR_APK and PMAB_AAPT2 must name built host artifacts"
            )
        if not re.fullmatch(r"[0-9a-f]{40}", cls.expected_source_revision):
            raise AssertionError("PMAB_EXPECTED_SOURCE_REVISION must be a 40-character Git SHA")

    @classmethod
    def dump_xml(cls, path: str) -> str:
        completed = subprocess.run(
            [str(cls.aapt2), "dump", "xmltree", "--file", path, str(cls.apk)],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stderr)
        return completed.stdout

    def test_manifest_exposes_only_the_system_bound_accessibility_service(self):
        # Break caught: the system cannot bind, or collector gains network/UI surface.
        manifest = self.dump_xml("AndroidManifest.xml")

        self.assertIn("E: service", manifest)
        self.assertIn("org.pmab.collector.PmabCaptureService", manifest)
        self.assertIn("android.permission.BIND_ACCESSIBILITY_SERVICE", manifest)
        self.assertIn("android.accessibilityservice", manifest)
        self.assertRegex(manifest, r"exported[^\n]*=true")
        self.assertNotIn("android.permission.INTERNET", manifest)
        self.assertNotIn("android.permission.SYSTEM_ALERT_WINDOW", manifest)
        self.assertNotIn("E: activity", manifest)

    def test_service_config_can_read_windows_and_screenshot_but_not_act(self):
        # Break caught: build requests gesture/key/touch capabilities outside action-free V1.
        config = self.dump_xml("res/xml/accessibility_service_config.xml")

        for required in (
            "canRetrieveWindowContent",
            "canTakeScreenshot",
            "isAccessibilityTool",
        ):
            self.assertIn(required, config)
        # aapt2 resolves flagRetrieveInteractiveWindows (0x40) and
        # flagReportViewIds (0x10) to their compiled bitmask.
        self.assertIn("accessibilityFlags", config)
        self.assertIn("=0x00000050", config)
        for forbidden_true in (
            "canPerformGestures",
            "canRequestTouchExplorationMode",
            "canRequestFilterKeyEvents",
        ):
            self.assertNotRegex(config, rf"{forbidden_true}[^\n]*=true")

    def test_dex_contains_capture_pipeline_and_no_action_invocations(self):
        # Break caught: compiled collector can click, gesture, globally navigate, or draw overlays.
        with zipfile.ZipFile(self.apk) as archive:
            dex = b"".join(
                archive.read(name)
                for name in archive.namelist()
                if name.startswith("classes") and name.endswith(".dex")
            )
        for required in (
            b"Lorg/pmab/collector/PmabCaptureService;",
            b"Lorg/pmab/collector/CaptureCoordinator;",
            b"Lorg/pmab/collector/AccessibilitySnapshotter;",
            b"takeScreenshot",
            b"scanPendingRequests",
            b"postDelayed",
        ):
            self.assertIn(required, dex)
        for forbidden in (
            b"performAction",
            b"performGlobalAction",
            b"dispatchGesture",
            b"getAccessibilityButtonController",
            b"TYPE_ACCESSIBILITY_OVERLAY",
        ):
            self.assertNotIn(forbidden, dex)
        self.assertIn(self.expected_source_revision.encode(), dex)
        self.assertNotIn(b"uncommitted", dex)


if __name__ == "__main__":
    unittest.main()
