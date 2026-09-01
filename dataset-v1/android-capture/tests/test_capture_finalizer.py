from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import struct
import sys
import tempfile
import unittest
import zlib


CAPTURE_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = CAPTURE_ROOT / "finalize_android_capture.py"
CONTRACT_PATH = CAPTURE_ROOT / "CAPTURE_CONTRACT_V1.json"
PUBLIC_STATUS_PATH = CAPTURE_ROOT / "PUBLIC_FEASIBILITY_STATUS.json"


def load_module():
    if not MODULE_PATH.is_file():
        raise AssertionError("finalize_android_capture.py must be implemented")
    spec = importlib.util.spec_from_file_location("android_capture_finalizer", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load capture finalizer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_png(width: int = 2, height: int = 2) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    scanlines = b"".join(b"\x00" + (b"\x00\x00\x00" * width) for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(scanlines))
        + chunk(b"IEND", b"")
    )


def write_capture_fixture(root: Path, *, suffix: str = "001") -> tuple[Path, bytes, bytes]:
    screenshot = make_png(width=2 + int(suffix), height=2)
    accessibility = {
        "snapshot_schema_version": "1.0.0",
        "windows": [
            {
                "window_id": 7,
                "window_type": "TYPE_APPLICATION",
                "layer": 0,
                "active": True,
                "focused": True,
                "root_node_id": "n0",
            }
        ],
        "nodes": [
            {
                "node_id": "n0",
                "parent_id": None,
                "window_id": 7,
                "class_name": "android.widget.FrameLayout",
                "package_name": "org.example.fixture",
                "text": None,
                "content_description": None,
                "hint_text": None,
                "pane_title": None,
                "state_description": None,
                "view_id_resource_name": "org.example.fixture:id/root",
                "bounds_in_screen": [0, 0, 1080, 2400],
                "visible_to_user": True,
                "important_for_accessibility": True,
                "enabled": True,
                "clickable": False,
                "focusable": False,
                "accessibility_focused": False,
                "actions": [],
                "child_ids": ["n1"],
            },
            {
                "node_id": "n1",
                "parent_id": "n0",
                "window_id": 7,
                "class_name": "android.widget.TextView",
                "package_name": "org.example.fixture",
                "text": f"Private fixture message {suffix}",
                "content_description": None,
                "hint_text": None,
                "pane_title": None,
                "state_description": None,
                "view_id_resource_name": "org.example.fixture:id/message",
                "bounds_in_screen": [120, 800, 960, 1040],
                "visible_to_user": True,
                "important_for_accessibility": True,
                "enabled": True,
                "clickable": False,
                "focusable": True,
                "accessibility_focused": True,
                "actions": ["ACTION_FOCUS"],
                "child_ids": [],
            },
        ],
    }
    accessibility_bytes = (
        json.dumps(accessibility, ensure_ascii=False, sort_keys=True) + "\n"
    ).encode("utf-8")

    (root / "screen.png").write_bytes(screenshot)
    (root / "accessibility.json").write_bytes(accessibility_bytes)
    metadata = {
        "capture_schema_version": "1.0.0",
        "capture_id": f"PMAB-A-CAP-{suffix}",
        "item_id": f"PMAB-A-ITEM-{suffix}",
        "source_group_id": f"group-{suffix}",
        "popup_template_family_id": f"template-{int(suffix) % 3}",
        "intended_stratum": "popup_candidate",
        "observation_phase": "pre_action",
        "action_attempts": [],
        "screenshot_path": "screen.png",
        "accessibility_snapshot_path": "accessibility.json",
        "screenshot_captured_at": "2026-09-01T01:00:00.100Z",
        "accessibility_captured_at": "2026-09-01T01:00:00.500Z",
        "stable_state_token_before": f"state-{suffix}",
        "stable_state_token_after": f"state-{suffix}",
        "device": {
            "manufacturer": "AOSP",
            "model": "controlled-fixture",
            "android_release": "15",
            "api_level": 35,
            "display_width_px": 1080,
            "display_height_px": 2400,
        },
        "app": {
            "package_name": "org.example.fixture",
            "version_name": "1.0",
            "version_code": 1,
        },
        "locale": "en-US",
        "collector": {
            "name": "pmab-accessibility-collector",
            "version": "1.0.0",
            "mode": "accessibilityservice_node_snapshot",
            "service_package": "org.example.pmabcollector",
            "service_flags": ["FLAG_RETRIEVE_INTERACTIVE_WINDOWS"],
            "window_retrieval_enabled": True,
        },
        "authorization": {
            "collection_authorized": True,
            "basis": "controlled open-source fixture",
            "privacy_review_status": "passed",
            "redistribution_status": "adapter_only",
        },
        "gold_labels_present": False,
        "method_predictions_present": False,
    }
    metadata_path = root / "capture.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return metadata_path, screenshot, accessibility_bytes


def finalized_record(index: int, stratum: str) -> dict:
    return {
        "capture_schema_version": "1.0.0",
        "status": "eligible_for_capture_feasibility",
        "capture_id": f"PMAB-A-CAP-{index:03d}",
        "item_id": f"PMAB-A-ITEM-{index:03d}",
        "source_group_id": f"group-{index}",
        "popup_template_family_id": f"template-{index % 3}",
        "intended_stratum": stratum,
        "collector_mode": "accessibilityservice_node_snapshot",
        "authorization_summary": {
            "collection_authorized": True,
            "privacy_review_status": "passed",
            "redistribution_status": "adapter_only",
        },
        "synchronization": {
            "delta_ms": 400,
            "maximum_delta_ms": 3000,
            "stable_state_verified": True,
        },
        "artifacts": {
            "screenshot_sha256": f"{index:064x}",
            "screenshot_size_bytes": 100 + index,
            "accessibility_snapshot_sha256": f"{index + 10:064x}",
            "accessibility_snapshot_size_bytes": 200 + index,
        },
        "accessibility_summary": {"node_count": 2, "window_count": 1},
        "paper_result_eligible": False,
        "human_gold_count": 0,
    }


def write_collector_bundle_fixture(root: Path) -> tuple[Path, dict, dict]:
    request = {
        "schema_version": "1.1",
        "capture_id": "PMAB-A-CAP-101",
        "item_id": "PMAB-A-ITEM-101",
        "source_group_id": "group-101",
        "popup_template_family_id": "template-dialog",
        "intended_stratum": "popup_candidate",
        "expected_target_package": "org.example.fixture",
        "request_nonce": "bd33d879debc4c38",
    }
    canonical_hash = "1" * 64

    def tree(start: int, end: int) -> dict:
        return {
            "schema_version": "1.1",
            "clock": "android.os.SystemClock.uptimeMillis",
            "start_uptime_ms": start,
            "end_uptime_ms": end,
            "canonical_tree_sha256": canonical_hash,
            "focus_token": "w:0:7/n:0.0:a=true:i=false",
            "node_count": 2,
            "contains_sensitive_node": False,
            "truncated": False,
            "target_packages": ["org.example.fixture"],
            "windows": [
                {
                    "id": "w:0:7",
                    "window_id": 7,
                    "root": {
                        "id": "w:0:7/n:0",
                        "text": None,
                        "children": [
                            {
                                "id": "w:0:7/n:0.0",
                                "text": "Private collector fixture message",
                                "children": [],
                            }
                        ],
                    },
                }
            ],
        }

    screenshot = make_png(3, 2)
    artifacts = {
        "tree-before.json": json.dumps(tree(100, 120), sort_keys=True).encode(),
        "tree-after.json": json.dumps(tree(170, 190), sort_keys=True).encode(),
        "screenshot.png": screenshot,
    }
    for filename, data in artifacts.items():
        (root / filename).write_bytes(data)
    artifact_records = {
        key: {
            "filename": filename,
            "bytes": len(artifacts[filename]),
            "sha256": hashlib.sha256(artifacts[filename]).hexdigest(),
        }
        for key, filename in {
            "tree_before": "tree-before.json",
            "tree_after": "tree-after.json",
            "screenshot": "screenshot.png",
        }.items()
    }
    machine = {
        "schema_version": "1.1",
        "collector": "pmab-android-accessibilityservice",
        "machine_status": "complete",
        "machine_reason": "accepted",
        "clock": "android.os.SystemClock.uptimeMillis",
        "request": request,
        "runtime": {
            "sdk_int": 35,
            "build_fingerprint": "fixture/fingerprint",
            "source_revision": "c" * 40,
            "service_capabilities": 129,
            "service_flags": 80,
            "service_event_types": 4229160,
            "service_feedback_type": 16,
            "device": {
                "manufacturer": "AOSP",
                "model": "controlled-fixture",
                "android_release": "15",
                "display_width_px": 3,
                "display_height_px": 2,
            },
            "target_app": {
                "package_name": "org.example.fixture",
                "version_name": "1.0",
                "version_code": 1,
            },
            "collector_app": {
                "package_name": "org.pmab.collector",
                "version_name": "0.1.0",
                "version_code": 1,
            },
            "locale": "en-US",
        },
        "timing": {
            "tree_before_start_uptime_ms": 100,
            "tree_before_end_uptime_ms": 120,
            "screenshot_request_uptime_ms": 130,
            "screenshot_result_uptime_ms": 150,
            "screenshot_callback_uptime_ms": 160,
            "tree_after_start_uptime_ms": 170,
            "tree_after_end_uptime_ms": 190,
            "tree_before_sha256": canonical_hash,
            "tree_after_sha256": canonical_hash,
            "event_sequence_before": 5,
            "event_sequence_after": 5,
            "focus_token_before": "w:0:7/n:0.0:a=true:i=false",
            "focus_token_after": "w:0:7/n:0.0:a=true:i=false",
        },
        "artifacts": artifact_records,
    }
    review = {
        "schema_version": "1.1",
        "capture_id": request["capture_id"],
        "reviewer_id": "reviewer-01",
        "reviewed_at": "2026-09-01T12:00:00+08:00",
        "collection_authorized": True,
        "basis": "controlled fixture collection",
        "privacy_review_status": "passed",
        "redistribution_status": "adapter_only",
        "screen_reader": {
            "enabled": True,
            "name": "TalkBack",
            "version": "15.2",
        },
        "collector_apk_sha256": "a" * 64,
        "collector_signing_certificate_sha256": "b" * 64,
        "human_gold_added": False,
        "method_predictions_added": False,
    }
    (root / "request.json").write_text(json.dumps(request), encoding="utf-8")
    (root / "machine-capture.json").write_text(json.dumps(machine), encoding="utf-8")
    (root / "review.json").write_text(json.dumps(review), encoding="utf-8")
    attestation = {
        "schema_version": "1.1",
        "status": "verified",
        "capture_id": request["capture_id"],
        "source_revision": "c" * 40,
        "local_apk_sha256": "a" * 64,
        "installed_apk_sha256": "a" * 64,
        "signing_certificate_sha256": "b" * 64,
        "device_serial_sha256": "d" * 64,
        "verified_at": "2026-09-01T12:00:00+08:00",
    }
    (root / "collector-attestation.json").write_text(
        json.dumps(attestation), encoding="utf-8"
    )
    return root, machine, review


class AndroidCaptureFinalizerTests(unittest.TestCase):
    def test_public_status_stays_blocked_until_real_capture_gate_passes(self):
        # Break caught: tooling readiness is published as empirical-data readiness.
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        status = json.loads(PUBLIC_STATUS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(contract["capture_schema_version"], "1.1.0")
        self.assertEqual(contract["minimum_source_groups"], 5)
        self.assertEqual(contract["minimum_popup_template_families"], 3)
        self.assertEqual(status["status"], "blocked_no_real_android_captures")
        self.assertEqual(status["real_capture_count"], 0)
        self.assertEqual(status["human_gold_count"], 0)
        self.assertFalse(status["paper_result_eligible"])

    def test_collector_bundle_uses_monotonic_bracket_and_separate_review(self):
        # Break caught: the real collector bundle cannot enter CAP-001 without legacy tokens.
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root, _, _ = write_collector_bundle_fixture(Path(directory))
            record = module.finalize_collector_bundle(root)

        self.assertEqual(record["capture_schema_version"], "1.1.0")
        self.assertEqual(record["status"], "eligible_for_capture_feasibility")
        self.assertEqual(record["synchronization"]["delta_ms"], 30)
        self.assertTrue(record["synchronization"]["event_sequence_verified"])
        self.assertTrue(record["synchronization"]["focus_verified"])
        self.assertEqual(
            record["artifacts"]["accessibility_snapshot_sha256"], "1" * 64
        )
        self.assertNotIn("Private collector fixture", json.dumps(record))

    def test_collector_bundle_fails_on_drift_or_machine_injected_review(self):
        # Break caught: arbitrary tokens, drift, or self-approved privacy bypass finalization.
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root, machine, _ = write_collector_bundle_fixture(Path(directory))
            machine["timing"]["event_sequence_after"] = 6
            (root / "machine-capture.json").write_text(json.dumps(machine))
            with self.assertRaisesRegex(ValueError, "event sequence"):
                module.finalize_collector_bundle(root)

            _, machine, _ = write_collector_bundle_fixture(root)
            machine["privacy_review_status"] = "passed"
            (root / "machine-capture.json").write_text(json.dumps(machine))
            with self.assertRaisesRegex(ValueError, "human decision"):
                module.finalize_collector_bundle(root)

    def test_collector_bundle_requires_screen_reader_and_human_privacy_review(self):
        # Break caught: collection outside the target screen-reader condition is admitted.
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root, _, review = write_collector_bundle_fixture(Path(directory))
            review["screen_reader"]["enabled"] = False
            (root / "review.json").write_text(json.dumps(review))
            with self.assertRaisesRegex(ValueError, "screen reader"):
                module.finalize_collector_bundle(root)

            review["screen_reader"]["enabled"] = True
            review["privacy_review_status"] = "pending"
            (root / "review.json").write_text(json.dumps(review))
            with self.assertRaisesRegex(ValueError, "privacy review"):
                module.finalize_collector_bundle(root)

    def test_collector_bundle_requires_runtime_device_and_target_app_provenance(self):
        # Break caught: an unbound APK or unknown target app is treated as a real capture.
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root, machine, _ = write_collector_bundle_fixture(Path(directory))
            machine["runtime"].pop("device")
            (root / "machine-capture.json").write_text(json.dumps(machine))
            with self.assertRaisesRegex(ValueError, "runtime.device"):
                module.finalize_collector_bundle(root)

            _, machine, _ = write_collector_bundle_fixture(root)
            machine["runtime"]["target_app"]["package_name"] = "org.other"
            (root / "machine-capture.json").write_text(json.dumps(machine))
            with self.assertRaisesRegex(ValueError, "target app"):
                module.finalize_collector_bundle(root)

    def test_collector_bundle_cross_checks_apk_attestation(self):
        # Break caught: a reviewer can type arbitrary well-shaped APK/cert hashes.
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root, _, review = write_collector_bundle_fixture(Path(directory))
            review["collector_apk_sha256"] = "e" * 64
            (root / "review.json").write_text(json.dumps(review))
            with self.assertRaisesRegex(ValueError, "attestation"):
                module.finalize_collector_bundle(root)

    def test_collector_cli_writes_minimized_record(self):
        # Break caught: the documented V1.1 collector command is not executable.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "bundle"
            root.mkdir()
            write_collector_bundle_fixture(root)
            output = Path(directory) / "record.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "finalize-collector",
                    "--bundle",
                    str(root),
                    "--output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            text = output.read_text(encoding="utf-8")
            self.assertNotIn("Private collector fixture", text)
            self.assertEqual(json.loads(text)["capture_schema_version"], "1.1.0")

    def test_valid_pre_action_accessibility_snapshot_is_finalized_with_hashes(self):
        # Break caught: a real, synchronized, action-free snapshot cannot enter CAP-001.
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            metadata_path, screenshot, accessibility = write_capture_fixture(
                Path(directory)
            )
            record = module.finalize_capture(metadata_path)

        self.assertEqual(record["status"], "eligible_for_capture_feasibility")
        self.assertEqual(record["synchronization"]["delta_ms"], 400)
        self.assertEqual(
            record["artifacts"]["screenshot_sha256"],
            hashlib.sha256(screenshot).hexdigest(),
        )
        self.assertEqual(
            record["artifacts"]["accessibility_snapshot_sha256"],
            hashlib.sha256(accessibility).hexdigest(),
        )
        self.assertEqual(record["accessibility_summary"]["node_count"], 2)
        self.assertEqual(record["accessibility_summary"]["window_count"], 1)
        self.assertFalse(record["paper_result_eligible"])
        self.assertEqual(record["human_gold_count"], 0)
        self.assertNotIn("Private fixture message", json.dumps(record))

    def test_actionful_or_post_action_capture_is_rejected(self):
        # Break caught: dismissal/recovery evidence silently enters the V1 input set.
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata_path, _, _ = write_capture_fixture(root)
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            for mutation in (
                {"observation_phase": "post_action"},
                {"action_attempts": [{"action": "tap", "x": 10, "y": 20}]},
            ):
                candidate = deepcopy(metadata)
                candidate.update(mutation)
                metadata_path.write_text(json.dumps(candidate), encoding="utf-8")
                with self.subTest(mutation=mutation):
                    with self.assertRaisesRegex(ValueError, "pre_action|action-free"):
                        module.finalize_capture(metadata_path)

    def test_non_accessibilityservice_or_drifted_snapshot_is_rejected(self):
        # Break caught: UIAutomator/RICO or a changed state is mislabeled formal accessibility evidence.
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata_path, _, _ = write_capture_fixture(root)
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

            wrong_mode = deepcopy(metadata)
            wrong_mode["collector"]["mode"] = "uiautomator_dump"
            metadata_path.write_text(json.dumps(wrong_mode), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "AccessibilityService"):
                module.finalize_capture(metadata_path)

            drifted = deepcopy(metadata)
            drifted["stable_state_token_after"] = "different-state"
            metadata_path.write_text(json.dumps(drifted), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "state drift"):
                module.finalize_capture(metadata_path)

            stale = deepcopy(metadata)
            stale["accessibility_captured_at"] = "2026-09-01T01:00:04.500Z"
            metadata_path.write_text(json.dumps(stale), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "synchronization delta"):
                module.finalize_capture(metadata_path)

    def test_truncated_image_and_missing_capture_provenance_are_rejected(self):
        # Break caught: a magic-byte stub or provenance-free row is called a real capture.
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata_path, _, _ = write_capture_fixture(root)
            (root / "screen.png").write_bytes(b"\x89PNG\r\n\x1a\ntruncated")
            with self.assertRaisesRegex(ValueError, "valid PNG"):
                module.finalize_capture(metadata_path)

            write_capture_fixture(root)
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            for missing_field in ("device", "app", "locale"):
                candidate = deepcopy(metadata)
                candidate.pop(missing_field)
                metadata_path.write_text(json.dumps(candidate), encoding="utf-8")
                with self.subTest(missing_field=missing_field):
                    with self.assertRaisesRegex(ValueError, missing_field):
                        module.finalize_capture(metadata_path)

    def test_missing_nodes_gold_leakage_or_unreviewed_privacy_is_rejected(self):
        # Break caught: an empty tree, leaked label, or unreviewed content unlocks CAP-001.
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata_path, _, _ = write_capture_fixture(root)
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

            tree_path = root / "accessibility.json"
            tree = json.loads(tree_path.read_text(encoding="utf-8"))
            tree["nodes"] = []
            tree_path.write_text(json.dumps(tree), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "at least one node"):
                module.finalize_capture(metadata_path)

            _, _, _ = write_capture_fixture(root)
            leaked = deepcopy(metadata)
            leaked["gold_labels_present"] = True
            metadata_path.write_text(json.dumps(leaked), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "gold labels"):
                module.finalize_capture(metadata_path)

            private = deepcopy(metadata)
            private["authorization"]["privacy_review_status"] = "pending"
            metadata_path.write_text(json.dumps(private), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "privacy review"):
                module.finalize_capture(metadata_path)

    def test_nested_label_or_prediction_key_is_rejected_from_snapshot(self):
        # Break caught: labels hidden inside a node bypass the top-level leakage check.
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata_path, _, _ = write_capture_fixture(root)
            tree_path = root / "accessibility.json"
            tree = json.loads(tree_path.read_text(encoding="utf-8"))
            tree["nodes"][1]["prediction"] = {"popup_present": True}
            tree_path.write_text(json.dumps(tree), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "gold labels or predictions"):
                module.finalize_capture(metadata_path)

    def test_feasibility_gate_requires_five_groups_three_templates_and_all_strata(self):
        # Break caught: a narrow or one-sided capture set is declared formal-data ready.
        module = load_module()
        records = []
        strata = [
            "popup_candidate",
            "no_popup_candidate",
            "boundary_candidate",
            "popup_candidate",
            "no_popup_candidate",
        ]
        for index, stratum in enumerate(strata, start=1):
            records.append(finalized_record(index, stratum))

        report = module.audit_feasibility(records)

        self.assertEqual(report["status"], "ready_for_real_g1_pilot")
        self.assertEqual(report["capture_count"], 5)
        self.assertEqual(report["source_group_count"], 5)
        self.assertEqual(report["popup_template_family_count"], 3)
        self.assertFalse(report["paper_result_eligible"])
        self.assertEqual(report["human_gold_count"], 0)

        with self.assertRaisesRegex(ValueError, "at least 5 source groups"):
            module.audit_feasibility(records[:4])

    def test_feasibility_gate_rejects_duplicate_capture_or_media_hash(self):
        # Break caught: duplicated states inflate group/template coverage.
        module = load_module()
        records = []
        for index in range(1, 6):
            records.append(
                finalized_record(
                    index,
                    "boundary_candidate"
                    if index == 1
                    else "popup_candidate"
                    if index % 2
                    else "no_popup_candidate",
                )
            )

        duplicate_id = deepcopy(records)
        duplicate_id[-1]["capture_id"] = duplicate_id[0]["capture_id"]
        with self.assertRaisesRegex(ValueError, "duplicate capture_id"):
            module.audit_feasibility(duplicate_id)

        duplicate_media = deepcopy(records)
        duplicate_media[-1]["artifacts"]["screenshot_sha256"] = duplicate_media[0][
            "artifacts"
        ]["screenshot_sha256"]
        with self.assertRaisesRegex(ValueError, "duplicate screenshot"):
            module.audit_feasibility(duplicate_media)

    def test_feasibility_gate_rejects_forged_or_incomplete_finalized_record(self):
        # Break caught: hand-written status-only rows bypass finalization and unlock G1.
        module = load_module()
        records = [
            finalized_record(
                index,
                "boundary_candidate"
                if index == 1
                else "popup_candidate"
                if index % 2
                else "no_popup_candidate",
            )
            for index in range(1, 6)
        ]
        mutations = (
            ("paper_result_eligible", True, "paper-result"),
            ("human_gold_count", 1, "human-gold"),
            ("collector_mode", "uiautomator_dump", "AccessibilityService"),
        )
        for field, value, error_pattern in mutations:
            forged = deepcopy(records)
            forged[0][field] = value
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, error_pattern):
                    module.audit_feasibility(forged)

        incomplete = deepcopy(records)
        incomplete[0].pop("authorization_summary")
        with self.assertRaisesRegex(ValueError, "authorization"):
            module.audit_feasibility(incomplete)

    def test_cli_writes_minimized_record_without_private_message_text(self):
        # Break caught: the documented capture finalization command is not reproducible.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata_path, _, _ = write_capture_fixture(root)
            output_path = root / "finalized.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "finalize",
                    "--metadata",
                    str(metadata_path),
                    "--output",
                    str(output_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            record_text = output_path.read_text(encoding="utf-8")
            self.assertNotIn("Private fixture message", record_text)
            self.assertEqual(
                json.loads(record_text)["status"],
                "eligible_for_capture_feasibility",
            )

    def test_audit_cli_refinalizes_private_bundles_and_rejects_record_only_input(self):
        # Break caught: a fake record with random hash strings unlocks G1 without artifacts.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata_relpaths = []
            strata = [
                "boundary_candidate",
                "popup_candidate",
                "no_popup_candidate",
                "popup_candidate",
                "no_popup_candidate",
            ]
            for index, stratum in enumerate(strata, start=1):
                bundle = root / f"bundle-{index}"
                bundle.mkdir()
                metadata_path, _, _ = write_capture_fixture(bundle, suffix=f"{index:03d}")
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                metadata["intended_stratum"] = stratum
                metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
                metadata_relpaths.append(str(metadata_path.relative_to(root)))

            metadata_list = root / "metadata-list.json"
            metadata_list.write_text(json.dumps(metadata_relpaths), encoding="utf-8")
            output_path = root / "audit.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "audit",
                    "--metadata-list",
                    str(metadata_list),
                    "--output",
                    str(output_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(
                json.loads(output_path.read_text(encoding="utf-8"))["status"],
                "ready_for_real_g1_pilot",
            )

            forged_records = root / "forged-records.json"
            forged_records.write_text(
                json.dumps([finalized_record(index, stratum) for index, stratum in enumerate(strata, 1)]),
                encoding="utf-8",
            )
            rejected = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "audit",
                    "--records",
                    str(forged_records),
                    "--output",
                    str(output_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("--metadata-list", rejected.stderr)


if __name__ == "__main__":
    unittest.main()
