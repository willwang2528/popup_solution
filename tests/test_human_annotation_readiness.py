from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READINESS_SCRIPT = (
    ROOT
    / "dataset-v1"
    / "annotation-pilot"
    / "scripts"
    / "check_human_annotation_readiness.py"
)


def load_module():
    if not READINESS_SCRIPT.is_file():
        raise AssertionError("human annotation readiness checker must exist")
    spec = importlib.util.spec_from_file_location(
        "human_annotation_readiness", READINESS_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load human annotation readiness checker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blank_record(item_number: int, role: str, order: int) -> dict:
    item_id = f"PMJ-PILOT-{item_number:03d}"
    return {
        "protocol_version": "1.0.0",
        "batch_id": "popsweeper-message-pilot-30-v1",
        "pilot_item_id": item_id,
        "annotation_order": order,
        "adapter_item_handle": f"adapter://popsweeper/pilot/{item_id}",
        "annotator_role": role,
        "annotator_id_pseudonymous": None,
        "record_status": "blank",
        "presence_label": None,
        "message_text": None,
        "message_observability": None,
        "semantic_slots": [],
        "confidence": None,
        "evidence": {
            "adapter_viewed": None,
            "view_session_id": None,
            "region_or_node_notes": None,
            "raw_image_copied": False,
        },
        "blindness_attestation": {
            "peer_labels_unseen": None,
            "source_class_unseen": None,
            "model_output_unseen": None,
        },
        "annotation_started_at": None,
        "annotation_completed_at": None,
        "notes": None,
    }


def make_ready_fixture(root: Path) -> tuple[Path, Path, Path]:
    repo_root = root / "popup-solution"
    pilot_root = repo_root / "dataset-v1" / "annotation-pilot"
    private_root = pilot_root / "private"
    adapter_root = (
        repo_root / "dataset-v1" / "work" / "annotation-media" / "pilot-batch-30"
    )

    manifest = pilot_root / "manifests" / "pilot_batch_30.jsonl"
    write_jsonl(
        manifest,
        [
            {"pilot_item_id": "PMJ-PILOT-001"},
            {"pilot_item_id": "PMJ-PILOT-002"},
        ],
    )
    template_a = pilot_root / "templates" / "annotator_a.jsonl"
    template_b = pilot_root / "templates" / "annotator_b.jsonl"
    rows_a = [blank_record(1, "A", 1), blank_record(2, "A", 2)]
    rows_b = [blank_record(2, "B", 1), blank_record(1, "B", 2)]
    write_jsonl(template_a, rows_a)
    write_jsonl(template_b, rows_b)

    schema = pilot_root / "schemas" / "annotation_record.schema.json"
    schema.parent.mkdir(parents=True, exist_ok=True)
    schema.write_text('{"type":"object"}\n', encoding="utf-8")
    guide = repo_root / "dataset-v1" / "ANNOTATION_GUIDE.md"
    guide.write_text("# Human annotation guide\n", encoding="utf-8")
    amendment = repo_root / "RESEARCH_RULES_AMENDMENT_V1.md"
    amendment.write_text("# v1 message-only, no action\n", encoding="utf-8")
    gitignore = repo_root / ".gitignore"
    gitignore.write_text(
        "dataset-v1/work/annotation-media/\n"
        "dataset-v1/annotation-pilot/private/\n",
        encoding="utf-8",
    )

    private_root.mkdir(parents=True)
    os.chmod(private_root, 0o700)
    working_a = private_root / "annotator_a.working.jsonl"
    working_b = private_root / "annotator_b.working.jsonl"
    write_jsonl(working_a, rows_a)
    write_jsonl(working_b, rows_b)
    os.chmod(working_a, 0o600)
    os.chmod(working_b, 0o600)

    for item_id in ("PMJ-PILOT-001", "PMJ-PILOT-002"):
        item_root = adapter_root / item_id
        item_root.mkdir(parents=True)
        (item_root / "popsweeper-screenshot.jpg").write_bytes(b"jpeg-fixture")
    (adapter_root / "export-summary.json").write_text(
        '{"pilot_count":2}\n', encoding="utf-8"
    )
    write_jsonl(
        adapter_root / "pilot-manifest.jsonl",
        [
            {"pilot_item_id": "PMJ-PILOT-001"},
            {"pilot_item_id": "PMJ-PILOT-002"},
        ],
    )
    os.chmod(adapter_root, 0o700)

    frozen_files = {
        "dataset-v1/annotation-pilot/manifests/pilot_batch_30.jsonl": sha256(manifest),
        "dataset-v1/annotation-pilot/templates/annotator_a.jsonl": sha256(template_a),
        "dataset-v1/annotation-pilot/templates/annotator_b.jsonl": sha256(template_b),
        "dataset-v1/annotation-pilot/schemas/annotation_record.schema.json": sha256(schema),
        "dataset-v1/ANNOTATION_GUIDE.md": sha256(guide),
        "RESEARCH_RULES_AMENDMENT_V1.md": sha256(amendment),
        ".gitignore": sha256(gitignore),
    }
    freeze = {
        "freeze_version": "1.0.0",
        "protocol_version": "1.0.0",
        "batch_id": "popsweeper-message-pilot-30-v1",
        "batch_size": 2,
        "scope": "popup_presence_and_message_judgment_no_action",
        "canonical_media_root": "dataset-v1/work/annotation-media/pilot-batch-30",
        "decision_authority": "user_authorized_aris_auto_proceed",
        "human_gold_status": "pending_real_human_annotation",
        "frozen_before_human_outputs": True,
        "acceptance_thresholds": {
            "presence_observed_agreement_min": 0.90,
            "presence_cohen_kappa_min": 0.80,
            "undefined_kappa_passes": False,
            "jointly_popup_comparable_items_min": 1,
            "message_normalized_agreement_min": 0.85,
            "message_exact_agreement_min": 0.70,
            "semantic_slot_exact_set_min": 0.75,
            "semantic_slot_mean_jaccard_min": 0.85,
            "uncertain_or_unusable_max_per_annotator": 1,
            "cannot_resolve_max": 1,
        },
        "adjudication_policy": {
            "all_items_require_third_human_review": True,
            "disagreements_require_evidence_recheck": True,
            "agreements_require_evidence_recheck": True,
            "cannot_resolve_excluded_from_metrics": True,
        },
        "frozen_files_sha256": frozen_files,
        "media_files_sha256": {
            "export-summary.json": sha256(adapter_root / "export-summary.json"),
            "pilot-manifest.jsonl": sha256(adapter_root / "pilot-manifest.jsonl"),
            "PMJ-PILOT-001/popsweeper-screenshot.jpg": sha256(
                adapter_root / "PMJ-PILOT-001" / "popsweeper-screenshot.jpg"
            ),
            "PMJ-PILOT-002/popsweeper-screenshot.jpg": sha256(
                adapter_root / "PMJ-PILOT-002" / "popsweeper-screenshot.jpg"
            ),
        },
    }
    freeze_path = pilot_root / "PILOT_PROTOCOL_FREEZE.json"
    freeze_path.write_text(
        json.dumps(freeze, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return repo_root, adapter_root, private_root


class HumanAnnotationReadinessTests(unittest.TestCase):
    def test_blank_frozen_pair_is_ready_only_for_real_human_annotation(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            repo_root, adapter_root, private_root = make_ready_fixture(Path(directory))

            report = module.audit_readiness(
                repo_root=repo_root,
                adapter_root=adapter_root,
                private_root=private_root,
            )

        self.assertEqual(report["status"], "ready_for_real_human_annotation")
        self.assertEqual(report["batch_size"], 2)
        self.assertEqual(report["human_gold_status"], "pending_real_human_annotation")
        self.assertFalse(report["scored"])
        self.assertFalse(report["paper_result_eligible"])
        self.assertFalse(report["user_experience_claim_eligible"])
        self.assertIs(report.get("recovery_claim_eligible"), False)
        self.assertEqual(report["checks_failed"], [])
        self.assertNotIn(str(repo_root), json.dumps(report))
        self.assertNotIn(str(adapter_root), json.dumps(report))

    def test_changed_frozen_artifact_blocks_annotation_start(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            repo_root, adapter_root, private_root = make_ready_fixture(Path(directory))
            guide = repo_root / "dataset-v1" / "ANNOTATION_GUIDE.md"
            guide.write_text("# outcome-driven protocol edit\n", encoding="utf-8")

            report = module.audit_readiness(
                repo_root=repo_root,
                adapter_root=adapter_root,
                private_root=private_root,
            )

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(
            report["checks_failed"],
            ["frozen_file_hash_mismatch:dataset-v1/ANNOTATION_GUIDE.md"],
        )

    def test_prefilled_private_record_blocks_pre_annotation_freeze_claim(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            repo_root, adapter_root, private_root = make_ready_fixture(Path(directory))
            working_a = private_root / "annotator_a.working.jsonl"
            rows = [json.loads(line) for line in working_a.read_text(encoding="utf-8").splitlines()]
            rows[0]["record_status"] = "completed"
            write_jsonl(working_a, rows)
            os.chmod(working_a, 0o600)

            report = module.audit_readiness(
                repo_root=repo_root,
                adapter_root=adapter_root,
                private_root=private_root,
            )

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(
            report["checks_failed"],
            ["nonblank_human_working_record:A:PMJ-PILOT-001"],
        )

    def test_world_readable_private_working_copy_is_blocked(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            repo_root, adapter_root, private_root = make_ready_fixture(Path(directory))
            os.chmod(private_root / "annotator_a.working.jsonl", 0o644)

            report = module.audit_readiness(
                repo_root=repo_root,
                adapter_root=adapter_root,
                private_root=private_root,
            )

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(
            report["checks_failed"],
            ["unsafe_private_file_permissions:A:expected_0600"],
        )

    def test_action_or_recovery_scope_cannot_unlock_v1_annotation(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            repo_root, adapter_root, private_root = make_ready_fixture(Path(directory))
            freeze_path = (
                repo_root
                / "dataset-v1"
                / "annotation-pilot"
                / "PILOT_PROTOCOL_FREEZE.json"
            )
            freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
            freeze["scope"] = "dismissal_and_task_recovery"
            freeze_path.write_text(json.dumps(freeze) + "\n", encoding="utf-8")

            report = module.audit_readiness(
                repo_root=repo_root,
                adapter_root=adapter_root,
                private_root=private_root,
            )

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["checks_failed"], ["scope_not_v1_message_only"])

    def test_missing_preregistered_threshold_blocks_annotation_start(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            repo_root, adapter_root, private_root = make_ready_fixture(Path(directory))
            freeze_path = (
                repo_root
                / "dataset-v1"
                / "annotation-pilot"
                / "PILOT_PROTOCOL_FREEZE.json"
            )
            freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
            del freeze["acceptance_thresholds"]["presence_cohen_kappa_min"]
            freeze_path.write_text(json.dumps(freeze) + "\n", encoding="utf-8")

            report = module.audit_readiness(
                repo_root=repo_root,
                adapter_root=adapter_root,
                private_root=private_root,
            )

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(
            report["checks_failed"],
            ["acceptance_threshold_missing:presence_cohen_kappa_min"],
        )

    def test_agreed_items_must_still_receive_third_human_evidence_review(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            repo_root, adapter_root, private_root = make_ready_fixture(Path(directory))
            freeze_path = (
                repo_root
                / "dataset-v1"
                / "annotation-pilot"
                / "PILOT_PROTOCOL_FREEZE.json"
            )
            freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
            freeze["adjudication_policy"]["agreements_require_evidence_recheck"] = False
            freeze_path.write_text(json.dumps(freeze) + "\n", encoding="utf-8")

            report = module.audit_readiness(
                repo_root=repo_root,
                adapter_root=adapter_root,
                private_root=private_root,
            )

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(
            report["checks_failed"],
            ["adjudication_policy_not_fully_human_rechecked"],
        )

    def test_a_and_b_must_not_receive_the_same_annotation_order(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            repo_root, adapter_root, private_root = make_ready_fixture(Path(directory))
            pilot_root = repo_root / "dataset-v1" / "annotation-pilot"
            template_b = pilot_root / "templates" / "annotator_b.jsonl"
            same_order_b = [blank_record(1, "B", 1), blank_record(2, "B", 2)]
            write_jsonl(template_b, same_order_b)
            write_jsonl(private_root / "annotator_b.working.jsonl", same_order_b)
            os.chmod(private_root / "annotator_b.working.jsonl", 0o600)
            freeze_path = pilot_root / "PILOT_PROTOCOL_FREEZE.json"
            freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
            freeze["frozen_files_sha256"][
                "dataset-v1/annotation-pilot/templates/annotator_b.jsonl"
            ] = sha256(template_b)
            freeze_path.write_text(json.dumps(freeze) + "\n", encoding="utf-8")

            report = module.audit_readiness(
                repo_root=repo_root,
                adapter_root=adapter_root,
                private_root=private_root,
            )

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(
            report["checks_failed"],
            ["annotator_orders_not_independently_randomized"],
        )

    def test_missing_adapter_screenshot_is_reported_as_blocking(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            repo_root, adapter_root, private_root = make_ready_fixture(Path(directory))
            (adapter_root / "PMJ-PILOT-002" / "popsweeper-screenshot.jpg").unlink()

            try:
                report = module.audit_readiness(
                    repo_root=repo_root,
                    adapter_root=adapter_root,
                    private_root=private_root,
                )
            except FileNotFoundError as exc:
                self.fail(f"missing evidence must be a readiness failure, not an exception: {exc}")

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(
            report["checks_failed"],
            ["adapter_evidence_missing:PMJ-PILOT-002"],
        )

    def test_each_annotator_must_receive_exactly_the_frozen_item_set(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            repo_root, adapter_root, private_root = make_ready_fixture(Path(directory))
            pilot_root = repo_root / "dataset-v1" / "annotation-pilot"
            template_a = pilot_root / "templates" / "annotator_a.jsonl"
            one_item_a = [blank_record(1, "A", 1)]
            write_jsonl(template_a, one_item_a)
            write_jsonl(private_root / "annotator_a.working.jsonl", one_item_a)
            os.chmod(private_root / "annotator_a.working.jsonl", 0o600)
            freeze_path = pilot_root / "PILOT_PROTOCOL_FREEZE.json"
            freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
            freeze["frozen_files_sha256"][
                "dataset-v1/annotation-pilot/templates/annotator_a.jsonl"
            ] = sha256(template_a)
            freeze_path.write_text(json.dumps(freeze) + "\n", encoding="utf-8")

            report = module.audit_readiness(
                repo_root=repo_root,
                adapter_root=adapter_root,
                private_root=private_root,
            )

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["checks_failed"], ["annotator_item_set_mismatch:A"])

    def test_private_root_must_not_be_accessible_to_other_users(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            repo_root, adapter_root, private_root = make_ready_fixture(Path(directory))
            os.chmod(private_root, 0o755)

            report = module.audit_readiness(
                repo_root=repo_root,
                adapter_root=adapter_root,
                private_root=private_root,
            )

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(
            report["checks_failed"],
            ["unsafe_private_directory_permissions:expected_0700"],
        )

    def test_legacy_media_directory_cannot_replace_the_frozen_canonical_root(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            repo_root, adapter_root, private_root = make_ready_fixture(Path(directory))
            legacy_root = adapter_root.parent / "pilot-30"
            adapter_root.rename(legacy_root)

            report = module.audit_readiness(
                repo_root=repo_root,
                adapter_root=legacy_root,
                private_root=private_root,
            )

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["checks_failed"], ["adapter_root_not_canonical"])

    def test_changed_screenshot_cannot_pass_the_frozen_media_inventory(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            repo_root, adapter_root, private_root = make_ready_fixture(Path(directory))
            image_path = (
                adapter_root / "PMJ-PILOT-001" / "popsweeper-screenshot.jpg"
            )
            image_path.write_bytes(b"different-screenshot")

            report = module.audit_readiness(
                repo_root=repo_root,
                adapter_root=adapter_root,
                private_root=private_root,
            )

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(
            report["checks_failed"],
            [
                "media_file_hash_mismatch:"
                "PMJ-PILOT-001/popsweeper-screenshot.jpg"
            ],
        )

    def test_blank_status_cannot_hide_prefilled_human_content(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            repo_root, adapter_root, private_root = make_ready_fixture(Path(directory))
            working_a = private_root / "annotator_a.working.jsonl"
            rows = [json.loads(line) for line in working_a.read_text(encoding="utf-8").splitlines()]
            rows[0]["message_text"] = "already viewed output"
            write_jsonl(working_a, rows)
            os.chmod(working_a, 0o600)

            report = module.audit_readiness(
                repo_root=repo_root,
                adapter_root=adapter_root,
                private_root=private_root,
            )

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(
            report["checks_failed"],
            ["prefilled_human_field:A:PMJ-PILOT-001:message_text"],
        )

    def test_template_role_must_match_the_assigned_annotator(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            repo_root, adapter_root, private_root = make_ready_fixture(Path(directory))
            pilot_root = repo_root / "dataset-v1" / "annotation-pilot"
            template_b = pilot_root / "templates" / "annotator_b.jsonl"
            rows = [json.loads(line) for line in template_b.read_text(encoding="utf-8").splitlines()]
            for row in rows:
                row["annotator_role"] = "A"
            write_jsonl(template_b, rows)
            write_jsonl(private_root / "annotator_b.working.jsonl", rows)
            os.chmod(private_root / "annotator_b.working.jsonl", 0o600)
            freeze_path = pilot_root / "PILOT_PROTOCOL_FREEZE.json"
            freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
            freeze["frozen_files_sha256"][
                "dataset-v1/annotation-pilot/templates/annotator_b.jsonl"
            ] = sha256(template_b)
            freeze_path.write_text(json.dumps(freeze) + "\n", encoding="utf-8")

            report = module.audit_readiness(
                repo_root=repo_root,
                adapter_root=adapter_root,
                private_root=private_root,
            )

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["checks_failed"], ["annotator_role_mismatch:B"])

    def test_private_working_copy_must_start_byte_identical_to_frozen_template(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            repo_root, adapter_root, private_root = make_ready_fixture(Path(directory))
            working_a = private_root / "annotator_a.working.jsonl"
            rows = [json.loads(line) for line in working_a.read_text(encoding="utf-8").splitlines()]
            write_jsonl(working_a, list(reversed(rows)))
            os.chmod(working_a, 0o600)

            report = module.audit_readiness(
                repo_root=repo_root,
                adapter_root=adapter_root,
                private_root=private_root,
            )

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(
            report["checks_failed"],
            ["working_copy_not_frozen_template:A"],
        )

    def test_annotation_order_must_be_unique_and_contiguous_per_role(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            repo_root, adapter_root, private_root = make_ready_fixture(Path(directory))
            pilot_root = repo_root / "dataset-v1" / "annotation-pilot"
            template_a = pilot_root / "templates" / "annotator_a.jsonl"
            rows = [blank_record(1, "A", 1), blank_record(2, "A", 1)]
            write_jsonl(template_a, rows)
            write_jsonl(private_root / "annotator_a.working.jsonl", rows)
            os.chmod(private_root / "annotator_a.working.jsonl", 0o600)
            freeze_path = pilot_root / "PILOT_PROTOCOL_FREEZE.json"
            freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
            freeze["frozen_files_sha256"][
                "dataset-v1/annotation-pilot/templates/annotator_a.jsonl"
            ] = sha256(template_a)
            freeze_path.write_text(json.dumps(freeze) + "\n", encoding="utf-8")

            report = module.audit_readiness(
                repo_root=repo_root,
                adapter_root=adapter_root,
                private_root=private_root,
            )

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["checks_failed"], ["annotation_order_invalid:A"])

    def test_freeze_must_explicitly_precede_all_human_outputs(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            repo_root, adapter_root, private_root = make_ready_fixture(Path(directory))
            freeze_path = (
                repo_root
                / "dataset-v1"
                / "annotation-pilot"
                / "PILOT_PROTOCOL_FREEZE.json"
            )
            freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
            freeze["frozen_before_human_outputs"] = False
            freeze_path.write_text(json.dumps(freeze) + "\n", encoding="utf-8")

            report = module.audit_readiness(
                repo_root=repo_root,
                adapter_root=adapter_root,
                private_root=private_root,
            )

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(
            report["checks_failed"],
            ["freeze_not_confirmed_before_human_outputs"],
        )

    def test_cli_writes_a_public_path_free_readiness_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo_root, adapter_root, private_root = make_ready_fixture(root)
            report_path = root / "readiness.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(READINESS_SCRIPT),
                    "--repo-root",
                    str(repo_root),
                    "--adapter-root",
                    str(adapter_root),
                    "--private-root",
                    str(private_root),
                    "--report",
                    str(report_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(report_path.is_file(), "CLI must write the readiness report")
            report = json.loads(report_path.read_text(encoding="utf-8"))
            serialized = json.dumps(report)

        self.assertEqual(report["status"], "ready_for_real_human_annotation")
        self.assertNotIn(str(repo_root), serialized)
        self.assertNotIn(str(adapter_root), serialized)
        self.assertIn('"status": "ready_for_real_human_annotation"', completed.stdout)

    def test_private_and_media_roots_must_remain_git_ignored(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            repo_root, adapter_root, private_root = make_ready_fixture(Path(directory))
            gitignore = repo_root / ".gitignore"
            gitignore.write_text(
                "dataset-v1/work/annotation-media/\n", encoding="utf-8"
            )
            freeze_path = (
                repo_root
                / "dataset-v1"
                / "annotation-pilot"
                / "PILOT_PROTOCOL_FREEZE.json"
            )
            freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
            freeze["frozen_files_sha256"][".gitignore"] = sha256(gitignore)
            freeze_path.write_text(json.dumps(freeze) + "\n", encoding="utf-8")

            report = module.audit_readiness(
                repo_root=repo_root,
                adapter_root=adapter_root,
                private_root=private_root,
            )

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(
            report["checks_failed"],
            ["gitignore_missing:dataset-v1/annotation-pilot/private/"],
        )

    def test_canonical_adapter_root_must_be_coordinator_only(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            repo_root, adapter_root, private_root = make_ready_fixture(Path(directory))
            os.chmod(adapter_root, 0o755)

            report = module.audit_readiness(
                repo_root=repo_root,
                adapter_root=adapter_root,
                private_root=private_root,
            )

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(
            report["checks_failed"],
            ["unsafe_adapter_directory_permissions:expected_0700"],
        )


if __name__ == "__main__":
    unittest.main()
