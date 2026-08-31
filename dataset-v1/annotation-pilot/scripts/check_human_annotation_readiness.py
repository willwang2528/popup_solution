#!/usr/bin/env python3
"""Audit whether the frozen pilot can be handed to real human annotators."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
from pathlib import Path
from typing import Any


REQUIRED_THRESHOLDS = (
    "presence_observed_agreement_min",
    "presence_cohen_kappa_min",
    "undefined_kappa_passes",
    "jointly_popup_comparable_items_min",
    "message_normalized_agreement_min",
    "message_exact_agreement_min",
    "semantic_slot_exact_set_min",
    "semantic_slot_mean_jaccard_min",
    "uncertain_or_unusable_max_per_annotator",
    "cannot_resolve_max",
)

REQUIRED_ADJUDICATION_POLICY = (
    "all_items_require_third_human_review",
    "disagreements_require_evidence_recheck",
    "agreements_require_evidence_recheck",
    "cannot_resolve_excluded_from_metrics",
)

REQUIRED_GITIGNORE_LINES = (
    "dataset-v1/work/annotation-media/",
    "dataset-v1/annotation-pilot/private/",
)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path.name}")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"expected JSON objects: {path.name}")
    return rows


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _first_prefilled_field(row: dict[str, Any]) -> str | None:
    expected = {
        "annotator_id_pseudonymous": None,
        "presence_label": None,
        "message_text": None,
        "message_observability": None,
        "semantic_slots": [],
        "confidence": None,
        "annotation_started_at": None,
        "annotation_completed_at": None,
        "notes": None,
    }
    for key, blank_value in expected.items():
        if row.get(key) != blank_value:
            return key
    evidence = row.get("evidence", {})
    evidence_expected = {
        "adapter_viewed": (None, False),
        "view_session_id": (None,),
        "region_or_node_notes": (None,),
        "raw_image_copied": (False,),
    }
    for key, blank_values in evidence_expected.items():
        if evidence.get(key) not in blank_values:
            return f"evidence.{key}"
    attestation = row.get("blindness_attestation", {})
    for key in (
        "peer_labels_unseen",
        "source_class_unseen",
        "model_output_unseen",
    ):
        if attestation.get(key) not in (None, False):
            return f"blindness_attestation.{key}"
    return None


def audit_readiness(
    *, repo_root: Path, adapter_root: Path, private_root: Path
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    adapter_root = Path(adapter_root)
    private_root = Path(private_root)
    pilot_root = repo_root / "dataset-v1" / "annotation-pilot"
    freeze = _read_json(pilot_root / "PILOT_PROTOCOL_FREEZE.json")
    checks_failed = []
    if freeze.get("frozen_before_human_outputs") is not True:
        checks_failed.append("freeze_not_confirmed_before_human_outputs")
    if freeze.get("scope") != "popup_presence_and_message_judgment_no_action":
        checks_failed.append("scope_not_v1_message_only")
    canonical_media_root = repo_root / freeze.get("canonical_media_root", "")
    if adapter_root.resolve() != canonical_media_root.resolve():
        checks_failed.append("adapter_root_not_canonical")
    if stat.S_IMODE(adapter_root.stat().st_mode) != 0o700:
        checks_failed.append("unsafe_adapter_directory_permissions:expected_0700")
    for relative, expected in freeze.get("media_files_sha256", {}).items():
        media_path = adapter_root / relative
        if not media_path.is_file() and relative.endswith(
            "/popsweeper-screenshot.jpg"
        ):
            continue
        if (
            not media_path.is_file()
            or media_path.is_symlink()
            or _sha256(media_path) != expected
        ):
            checks_failed.append(f"media_file_hash_mismatch:{relative}")
    thresholds = freeze.get("acceptance_thresholds", {})
    for key in REQUIRED_THRESHOLDS:
        if key not in thresholds:
            checks_failed.append(f"acceptance_threshold_missing:{key}")
    adjudication_policy = freeze.get("adjudication_policy", {})
    if not all(
        adjudication_policy.get(key) is True
        for key in REQUIRED_ADJUDICATION_POLICY
    ):
        checks_failed.append("adjudication_policy_not_fully_human_rechecked")
    for relative, expected in freeze["frozen_files_sha256"].items():
        if _sha256(repo_root / relative) != expected:
            checks_failed.append(f"frozen_file_hash_mismatch:{relative}")
    gitignore_lines = {
        line.strip()
        for line in (repo_root / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    for required_line in REQUIRED_GITIGNORE_LINES:
        if required_line not in gitignore_lines:
            checks_failed.append(f"gitignore_missing:{required_line}")
    manifest = _read_jsonl(pilot_root / "manifests" / "pilot_batch_30.jsonl")
    item_ids = [row["pilot_item_id"] for row in manifest]
    manifest_item_set = set(item_ids)
    template_paths = {
        "A": pilot_root / "templates" / "annotator_a.jsonl",
        "B": pilot_root / "templates" / "annotator_b.jsonl",
    }
    templates_by_role = {
        role: _read_jsonl(path) for role, path in template_paths.items()
    }
    if [row.get("pilot_item_id") for row in templates_by_role["A"]] == [
        row.get("pilot_item_id") for row in templates_by_role["B"]
    ]:
        checks_failed.append("annotator_orders_not_independently_randomized")
    for role, rows in templates_by_role.items():
        row_ids = [row.get("pilot_item_id") for row in rows]
        if len(row_ids) != len(manifest_item_set) or set(row_ids) != manifest_item_set:
            checks_failed.append(f"annotator_item_set_mismatch:{role}")
        if {row.get("annotator_role") for row in rows} != {role}:
            checks_failed.append(f"annotator_role_mismatch:{role}")
        orders = [row.get("annotation_order") for row in rows]
        if not all(type(order) is int for order in orders) or sorted(orders) != list(
            range(1, len(rows) + 1)
        ):
            checks_failed.append(f"annotation_order_invalid:{role}")
    working_paths = {
        "A": private_root / "annotator_a.working.jsonl",
        "B": private_root / "annotator_b.working.jsonl",
    }
    if stat.S_IMODE(private_root.stat().st_mode) != 0o700:
        checks_failed.append("unsafe_private_directory_permissions:expected_0700")
    working_by_role = {
        role: _read_jsonl(path) for role, path in working_paths.items()
    }
    for role, path in working_paths.items():
        if stat.S_IMODE(path.stat().st_mode) != 0o600:
            checks_failed.append(
                f"unsafe_private_file_permissions:{role}:expected_0600"
            )
    for role, rows in working_by_role.items():
        contains_human_content = False
        for row in rows:
            if row.get("record_status") != "blank":
                contains_human_content = True
                checks_failed.append(
                    f"nonblank_human_working_record:{role}:{row.get('pilot_item_id')}"
                )
                continue
            prefilled = _first_prefilled_field(row)
            if prefilled is not None:
                contains_human_content = True
                checks_failed.append(
                    f"prefilled_human_field:{role}:{row.get('pilot_item_id')}:{prefilled}"
                )
        if (
            not contains_human_content
            and working_paths[role].read_bytes() != template_paths[role].read_bytes()
        ):
            checks_failed.append(f"working_copy_not_frozen_template:{role}")

    for item_id in item_ids:
        image_path = adapter_root / item_id / "popsweeper-screenshot.jpg"
        if not image_path.is_file() or image_path.is_symlink():
            checks_failed.append(f"adapter_evidence_missing:{item_id}")

    return {
        "status": (
            "blocked" if checks_failed else "ready_for_real_human_annotation"
        ),
        "batch_id": freeze["batch_id"],
        "batch_size": len(item_ids),
        "human_gold_status": "pending_real_human_annotation",
        "scored": False,
        "paper_result_eligible": False,
        "user_experience_claim_eligible": False,
        "recovery_claim_eligible": False,
        "checks_failed": checks_failed,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--adapter-root", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = audit_readiness(
        repo_root=args.repo_root,
        adapter_root=args.adapter_root,
        private_root=args.private_root,
    )
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    args.report.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0 if report["status"] == "ready_for_real_human_annotation" else 1


if __name__ == "__main__":
    raise SystemExit(main())
