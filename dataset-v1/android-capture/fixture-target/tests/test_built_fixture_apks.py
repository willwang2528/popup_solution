from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import unittest


EXPECTED_PACKAGES = {
    "commerce": "org.pmab.fixture.commerce",
    "media": "org.pmab.fixture.media",
    "travel": "org.pmab.fixture.travel",
    "productivity": "org.pmab.fixture.productivity",
    "education": "org.pmab.fixture.education",
}


class BuiltFixtureApkContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = os.environ.get("PMAB_FIXTURE_APK_ROOT")
        aapt2 = os.environ.get("PMAB_AAPT2")
        if not root or not aapt2:
            raise unittest.SkipTest("PMAB_FIXTURE_APK_ROOT and PMAB_AAPT2 are required")
        cls.apk_root = Path(root)
        cls.aapt2 = Path(aapt2)

    def test_all_five_apks_have_unique_expected_package_and_launchable_activity(self):
        # Break caught: Gradle flavors collapse to one package or omit the target Activity.
        observed_packages = set()
        for flavor, expected_package in EXPECTED_PACKAGES.items():
            apk = (
                self.apk_root
                / flavor
                / "debug"
                / f"fixtureTarget-{flavor}-debug.apk"
            )
            self.assertTrue(apk.is_file(), f"missing built fixture APK: {apk}")
            result = subprocess.run(
                [str(self.aapt2), "dump", "badging", str(apk)],
                check=True,
                capture_output=True,
                text=True,
            )
            package_match = re.search(r"^package: name='([^']+)'", result.stdout, re.MULTILINE)
            activity_match = re.search(
                r"^launchable-activity: name='([^']+)'", result.stdout, re.MULTILINE
            )
            self.assertIsNotNone(package_match)
            self.assertIsNotNone(activity_match)
            self.assertEqual(package_match.group(1), expected_package)
            self.assertEqual(activity_match.group(1), "org.pmab.fixture.FixtureActivity")
            self.assertIn("minSdkVersion:'30'", result.stdout)
            self.assertIn("targetSdkVersion:'35'", result.stdout)
            observed_packages.add(package_match.group(1))

        self.assertEqual(len(observed_packages), 5)


if __name__ == "__main__":
    unittest.main()
