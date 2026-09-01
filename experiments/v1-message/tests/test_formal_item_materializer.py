from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def canonical_row(row: dict) -> bytes:
    return json.dumps(
        row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_jsonl(rows: list[dict], key) -> bytes:
    return b"".join(canonical_row(row) + b"\n" for row in sorted(rows, key=key))


def source_item(index: int, *, prediction_text: str = "pregold-a") -> dict:
    pilot_id = f"PMJ-PILOT-{index:03d}"
    item_id = f"pmj.pending.{index:03d}"
    capture_id = f"PMAB-A-CAP-{index:03d}"
    record_hash = f"{index + 100:064x}"
    screenshot_hash = f"{index + 200:064x}"
    snapshot_hash = f"{index + 300:064x}"
    return {
        "identity": {
            "item_id": item_id,
            "pilot_item_id": pilot_id,
            "record_kind": "real_app",
        },
        "provenance": {
            "collection_session_id": capture_id,
            "source_origin": "real_device",
            "source_artifacts": [
                {
                    "uri": f"capture-record://{capture_id}",
                    "sha256": record_hash,
                    "media_type": "application/json",
                    "redaction_status": "not_needed",
                    "capture_channel": "android_accessibilityservice_finalized_record",
                }
            ],
            "raw_capture_hashes": {
                "finalized_capture_record_sha256": record_hash,
                "screenshot_sha256": screenshot_hash,
                "accessibility_snapshot_sha256": snapshot_hash,
            },
            "collector_and_model_versions": {
                "capture_schema_version": "1.1.0",
                "capture_status": "eligible_for_capture_feasibility",
                "collector_mode": "accessibilityservice_node_snapshot",
                "capture_item_id": item_id,
                "capture_delta_ms": 400,
                "maximum_delta_ms": 3000,
                "stable_state_verified": True,
            },
            "evidence_level": "full_device_evidence",
            "privacy_review_status": "passed",
        },
        "message_judgment": {
            "profile": "popup_message_judgment_v1",
            "labels": {
                "popup_present_gt": None,
                "message_text_gt": None,
                "critical_facts_gt": [],
                "message_text_observability": "pending_annotation",
            },
            "gap_ground_truth": {
                "status": "pending_audit",
                "structured_evidence_available": None,
                "structured_message_text_gt": None,
                "structured_message_complete_gt": None,
                "gap_reasons_gt": [],
                "critical_facts_missing_from_structure_gt": [],
                "host_text_contamination_gt": None,
                "tree_screenshot_synchronized_gt": None,
                "auditor_blind_to_method_outputs": None,
                "message_gold_batch_sha256": None,
                "structured_bundle_sha256": None,
                "gap_audit_batch_sha256": None,
                "evidence_uris": [],
            },
            "prediction": {
                "status": "judged",
                "message_text_pred": prediction_text,
                "paper_result_eligible": False,
            },
        },
        "observations": [
            {"observation_id": f"obs.{index:03d}", "phase": "pre_action"}
        ],
        "candidates": [],
        "decision": {"policy": {"decision": "no_action"}},
        "action_attempts": [],
        "evaluation_exclusion_reasons": ["pending_human_annotation"],
        "verification": {
            "technical_context_recovery": {
                "C_tech": None,
                "observability": "not_observable",
            }
        },
    }


def g1_row(index: int, *, popup: bool = True) -> dict:
    return {
        "protocol_version": "1.0.0",
        "batch_id": "popsweeper-message-pilot-30-v1",
        "pilot_item_id": f"PMJ-PILOT-{index:03d}",
        "record_status": "completed",
        "adjudicator_id_pseudonymous": "g1-adjudicator",
        "adjudication_status": "resolved",
        "presence_label_final": "popup" if popup else "no_popup",
        "out_of_scope_reason_final": None,
        "message_text_final": f"Private visible message {index}" if popup else None,
        "message_observability_final": "complete" if popup else "not_applicable",
        "semantic_slots_final": (
            [
                {
                    "slot_type": "duration_deadline",
                    "value": f"deadline-{index}",
                    "polarity": "affirmed",
                }
            ]
            if popup
            else []
        ),
        "decision_rationale": "Third human rechecked the frozen screenshot.",
        "evidence_rechecked_via_adapter": True,
        "resolved_at": "2026-09-01T10:00:00Z",
    }


def structured_row(index: int) -> dict:
    pilot_id = f"PMJ-PILOT-{index:03d}"
    return {
        "identity": {
            "item_id": pilot_id,
            "pilot_item_id": pilot_id,
            "record_kind": "unscored_pregold_input",
        },
        "observations": [
            {
                "observation_id": f"{pilot_id}-pre-action-structured",
                "phase": "pre_action",
                "structured_representation": {
                    "availability": "available",
                    "representation_kind": "android-accessibility-tree",
                    "node_count": 1,
                    "artifact_sha256": f"{index:064x}",
                },
            }
        ],
        "candidates": [
            {
                "candidate_id": f"{pilot_id}-structured-0000",
                "source_channel": "structured",
                "normalized": {
                    "name_or_text": f"Private structured fragment {index}",
                    "value_or_hint": None,
                    "visible": True,
                },
                "features": {"node_index": 0, "depth": 0, "gap_reasons": []},
            }
        ],
        "action_attempts": [],
        "decision": {"policy": {"decision": "no_action"}},
        "metadata": {
            "contract_version": "pmj-pilot-structured-features-v1.0",
            "gold_blind": True,
            "gold_used": False,
            "scored": False,
            "paper_result_eligible": False,
            "action_mode": "no_action",
        },
    }


def g1_hash(rows: list[dict]) -> str:
    return hashlib.sha256(
        canonical_jsonl(rows, key=lambda row: row["pilot_item_id"])
    ).hexdigest()


def structured_hash(rows: list[dict]) -> str:
    return hashlib.sha256(
        canonical_jsonl(rows, key=lambda row: row["identity"]["pilot_item_id"])
    ).hexdigest()


def g2_audit_row(
    index: int,
    *,
    slot: str,
    auditor: str,
    message_hash: str,
    bundle_hash: str,
    popup: bool = True,
) -> dict:
    pilot_id = f"PMJ-PILOT-{index:03d}"
    return {
        "contract_version": "popup-structure-visual-gap-audit-record-v1.0",
        "batch_id": "popsweeper-message-pilot-30-gap-v1",
        "pilot_item_id": pilot_id,
        "record_status": "completed",
        "auditor_slot": slot,
        "auditor_id_pseudonymous": auditor,
        "human_auditor_attestation": True,
        "independent_of_peer_attestation": True,
        "auditor_blind_to_method_outputs": True,
        "g1_gold_discrepancy_flag": False,
        "g1_gold_discrepancy_notes": None,
        "message_gold_batch_sha256": message_hash,
        "structured_bundle_sha256": bundle_hash,
        "audit_status": "adjudicated" if popup else "not_applicable",
        "structured_evidence_available": True if popup else None,
        "structured_candidate_ids": (
            [f"{pilot_id}-structured-0000"] if popup else []
        ),
        "structured_message_text": (
            f"Private structured fragment {index}" if popup else None
        ),
        "structured_message_complete": False if popup else None,
        "gap_reasons": ["merged"] if popup else [],
        "critical_facts_missing_from_structure": (
            [f"deadline-{index}"] if popup else []
        ),
        "host_text_contamination": False if popup else None,
        "tree_screenshot_synchronized": True if popup else None,
        "decision_rationale": "Compared structure with frozen G1 gold.",
        "evidence_uris": [
            "evidence://private/structure",
            "evidence://private/screenshot",
        ],
        "completed_at": "2026-09-01T11:00:00Z",
    }


def g2_final_row(
    index: int,
    *,
    audit_pair: list[dict],
    message_hash: str,
    bundle_hash: str,
    popup: bool = True,
) -> dict:
    return {
        "contract_version": "popup-structure-visual-gap-adjudication-v1.0",
        "batch_id": "popsweeper-message-pilot-30-gap-v1",
        "pilot_item_id": f"PMJ-PILOT-{index:03d}",
        "record_status": "completed",
        "adjudicator_id_pseudonymous": "g2-adjudicator",
        "independent_audit_record_sha256": [
            hashlib.sha256(canonical_row(row)).hexdigest() for row in audit_pair
        ],
        "audit_status": "adjudicated" if popup else "not_applicable",
        "structured_evidence_available": True if popup else None,
        "structured_message_text_final": (
            f"Private structured fragment {index}" if popup else None
        ),
        "structured_message_complete_final": False if popup else None,
        "gap_reasons_final": ["merged"] if popup else [],
        "critical_facts_missing_from_structure_final": (
            [f"deadline-{index}"] if popup else []
        ),
        "host_text_contamination_final": False if popup else None,
        "tree_screenshot_synchronized_final": True if popup else None,
        "decision_rationale": "Adjudicated both independent G2 records.",
        "evidence_uris": [
            "evidence://private/structure",
            "evidence://private/screenshot",
        ],
        "auditor_blind_to_method_outputs": True,
        "g1_gold_discrepancy_detected": False,
        "message_gold_batch_sha256": message_hash,
        "structured_bundle_sha256": bundle_hash,
        "adjudicated_at": "2026-09-01T12:00:00Z",
    }


def bundle() -> dict:
    items = [source_item(1), source_item(2)]
    g1_rows = [g1_row(1), g1_row(2, popup=False)]
    structured = [structured_row(1), structured_row(2)]
    message_hash = g1_hash(g1_rows)
    bundle_hash = structured_hash(structured)
    audits: list[dict] = []
    finals: list[dict] = []
    for index, popup in ((1, True), (2, False)):
        pair = [
            g2_audit_row(
                index,
                slot="A",
                auditor="g2-auditor-a",
                message_hash=message_hash,
                bundle_hash=bundle_hash,
                popup=popup,
            ),
            g2_audit_row(
                index,
                slot="B",
                auditor="g2-auditor-b",
                message_hash=message_hash,
                bundle_hash=bundle_hash,
                popup=popup,
            ),
        ]
        audits.extend(pair)
        finals.append(
            g2_final_row(
                index,
                audit_pair=pair,
                message_hash=message_hash,
                bundle_hash=bundle_hash,
                popup=popup,
            )
        )
    return {
        "items": items,
        "g1_rows": g1_rows,
        "structured_rows": structured,
        "g2_audits": audits,
        "g2_rows": finals,
        "structured_bundle_sha256": bundle_hash,
    }


def contains_forbidden_action_or_recovery(value) -> bool:
    forbidden = {
        "action",
        "action_semantics",
        "click",
        "coordinate",
        "dismiss",
        "execution_channel",
        "selector",
        "target",
        "target_candidate_id",
    }
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = key.casefold()
            if lowered in forbidden or "recovery" in lowered:
                return True
            if contains_forbidden_action_or_recovery(child):
                return True
    elif isinstance(value, list):
        return any(contains_forbidden_action_or_recovery(child) for child in value)
    return False


class FormalItemMaterializerTests(unittest.TestCase):
    def module(self):
        try:
            return importlib.import_module("popup_eval.formal_item_materializer")
        except ModuleNotFoundError as error:
            self.fail(f"formal item materializer is missing: {error}")

    def materialize(self, values: dict | None = None):
        data = values or bundle()
        return self.module().materialize_formal_metric_items(
            source_items=data["items"],
            g1_adjudication_rows=data["g1_rows"],
            structured_feature_rows=data["structured_rows"],
            expected_structured_bundle_sha256=data["structured_bundle_sha256"],
            g2_independent_audit_records=data["g2_audits"],
            g2_adjudication_rows=data["g2_rows"],
        )

    def test_materializes_complete_g1_g2_snapshot_accepted_by_formal_runner(self):
        items, summary = self.materialize()

        self.assertEqual(summary["status"], "formal_adjudicated_metric_items_ready")
        self.assertEqual(summary["item_count"], 2)
        self.assertEqual(summary["metric_eligible_count"], 2)
        self.assertTrue(summary["coverage"]["g1_complete"])
        self.assertTrue(summary["coverage"]["g2_complete"])
        self.assertEqual(
            summary["hash_scope"]["g1_human_finalization_sha256"],
            "canonical G1 final-adjudication rows only",
        )
        self.assertEqual(
            summary["hash_scope"]["g2_human_finalization_sha256"],
            "canonical G2 final-adjudication rows bound to G1 and structure hashes",
        )
        self.assertFalse(summary["predictions_used"])
        self.assertFalse(summary["paper_result_eligible"])
        self.assertEqual(
            [item["identity"]["pilot_item_id"] for item in items],
            ["PMJ-PILOT-001", "PMJ-PILOT-002"],
        )
        for item in items:
            self.assertEqual(item["identity"]["record_kind"], "real_app")
            self.assertEqual(item["action_attempts"], [])
            self.assertEqual(item["decision"], {"policy": {"decision": "no_action"}})
            self.assertEqual(item["evaluation_exclusion_reasons"], [])
            self.assertFalse(contains_forbidden_action_or_recovery(item))
            provenance = item["adjudication_provenance"]
            self.assertEqual(
                provenance["adjudication_batch_sha256"],
                summary["hashes"]["g1_human_finalization_sha256"],
            )
            self.assertEqual(
                provenance["gap_audit_batch_sha256"],
                summary["hashes"]["g2_human_finalization_sha256"],
            )
            self.assertTrue(provenance["prediction_independent"])
            capture_binding = provenance["capture_binding"]
            self.assertEqual(
                capture_binding["capture_status"],
                "eligible_for_capture_feasibility",
            )
            self.assertEqual(
                capture_binding["collector_mode"],
                "accessibilityservice_node_snapshot",
            )
            self.assertTrue(capture_binding["stable_state_verified"])
        self.assertIn("capture_bindings_sha256", summary["hashes"])
        runner = importlib.import_module("popup_eval.formal_k50_runner")
        _, gold_hash, _ = runner._validate_adjudicated_items(items)
        self.assertEqual(gold_hash, summary["hashes"]["g1_human_finalization_sha256"])

    def test_gold_hashes_and_metric_items_are_independent_of_source_predictions(self):
        first = bundle()
        second = deepcopy(first)
        for item in second["items"]:
            item["message_judgment"]["prediction"]["message_text_pred"] = "changed"

        first_items, first_summary = self.materialize(first)
        second_items, second_summary = self.materialize(second)

        self.assertEqual(first_items, second_items)
        self.assertEqual(first_summary["hashes"], second_summary["hashes"])

    def test_rejects_archived_partial_real_app_source_without_cap001_binding(self):
        data = bundle()
        source = data["items"][0]
        source["provenance"].update(
            {
                "collection_session_id": "pending-empirical-pilot-v1",
                "source_origin": "paper_artifact",
                "source_artifacts": [],
                "raw_capture_hashes": {
                    "structured_artifact_sha256": "a" * 64,
                },
                "collector_and_model_versions": {
                    "materializer": "pending-empirical-union-v1.0",
                },
                "evidence_level": "partial_device_evidence",
                "privacy_review_status": "restricted",
            }
        )

        with self.assertRaisesRegex(ValueError, "full-device CAP-001"):
            self.materialize(data)

    def test_rejects_tampered_cap001_record_binding(self):
        data = bundle()
        data["items"][0]["provenance"]["source_artifacts"][0]["sha256"] = "f" * 64

        with self.assertRaisesRegex(ValueError, "capture-record hash mismatch"):
            self.materialize(data)

    def test_rejects_incomplete_or_non_metric_eligible_g1_without_subsetting(self):
        incomplete = bundle()
        incomplete["g1_rows"] = incomplete["g1_rows"][:1]
        with self.assertRaisesRegex(ValueError, "missing pilot_item_id"):
            self.materialize(incomplete)

        unresolved = bundle()
        unresolved_row = unresolved["g1_rows"][0]
        unresolved_row.update(
            {
                "adjudication_status": "cannot_resolve",
                "presence_label_final": None,
                "message_text_final": None,
                "message_observability_final": None,
                "semantic_slots_final": [],
            }
        )
        with self.assertRaisesRegex(ValueError, "all G1 rows.*metric-eligible"):
            self.materialize(unresolved)

    def test_recursively_rejects_active_action_or_recovery_payloads(self):
        action = bundle()
        action["items"][0]["nested"] = {"level": {"coordinate": [1, 2]}}
        with self.assertRaisesRegex(ValueError, "action or Recovery"):
            self.materialize(action)

        recovery = bundle()
        recovery["items"][0]["nested"] = {
            "task_recovery": {"status": "restored"}
        }
        with self.assertRaisesRegex(ValueError, "action or Recovery"):
            self.materialize(recovery)

    def test_rejects_g2_g1_discrepancy_even_when_gap_row_is_cannot_resolve(self):
        data = bundle()
        target_audits = [
            row for row in data["g2_audits"] if row["pilot_item_id"] == "PMJ-PILOT-001"
        ]
        for row in target_audits:
            row.update(
                {
                    "g1_gold_discrepancy_flag": True,
                    "g1_gold_discrepancy_notes": "Screenshot fact requires G1 restart.",
                    "audit_status": "cannot_resolve",
                    "structured_evidence_available": None,
                    "structured_candidate_ids": [],
                    "structured_message_text": None,
                    "structured_message_complete": None,
                    "gap_reasons": [],
                    "critical_facts_missing_from_structure": [],
                    "host_text_contamination": None,
                    "tree_screenshot_synchronized": None,
                }
            )
        final = data["g2_rows"][0]
        final.update(
            {
                "independent_audit_record_sha256": [
                    hashlib.sha256(canonical_row(row)).hexdigest()
                    for row in target_audits
                ],
                "audit_status": "cannot_resolve",
                "structured_evidence_available": None,
                "structured_message_text_final": None,
                "structured_message_complete_final": None,
                "gap_reasons_final": [],
                "critical_facts_missing_from_structure_final": [],
                "host_text_contamination_final": None,
                "tree_screenshot_synchronized_final": None,
                "g1_gold_discrepancy_detected": True,
            }
        )

        with self.assertRaisesRegex(ValueError, "versioned G1 correction"):
            self.materialize(data)


class FormalItemMaterializerCliTests(unittest.TestCase):
    def write_jsonl(self, path: Path, rows: list[dict]) -> None:
        path.write_bytes(canonical_jsonl(rows, key=lambda row: json.dumps(row, sort_keys=True)))

    def test_cli_writes_private_0600_no_overwrite_outputs(self):
        data = bundle()
        with tempfile.TemporaryDirectory() as directory:
            private = Path(directory) / "private"
            private.mkdir()
            paths = {
                "items": private / "source.private.jsonl",
                "g1": private / "g1.private.jsonl",
                "structured": private / "structured.private.jsonl",
                "g2_audits": private / "g2-audits.private.jsonl",
                "g2": private / "g2.private.jsonl",
            }
            for key, rows in (
                ("items", data["items"]),
                ("g1", data["g1_rows"]),
                ("structured", data["structured_rows"]),
                ("g2_audits", data["g2_audits"]),
                ("g2", data["g2_rows"]),
            ):
                self.write_jsonl(paths[key], rows)
            output_items = private / "formal-items.private.jsonl"
            output_summary = private / "formal-items-summary.private.json"
            script = (
                Path(__file__).resolve().parents[1]
                / "popup_eval"
                / "formal_item_materializer.py"
            )
            command = [
                sys.executable,
                str(script),
                "--source-items",
                str(paths["items"]),
                "--g1-adjudications",
                str(paths["g1"]),
                "--structured-features",
                str(paths["structured"]),
                "--structured-bundle-sha256",
                data["structured_bundle_sha256"],
                "--g2-independent-audits",
                str(paths["g2_audits"]),
                "--g2-adjudications",
                str(paths["g2"]),
                "--output-items",
                str(output_items),
                "--output-summary",
                str(output_summary),
                "--expected-count",
                "2",
            ]

            first = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(stat.S_IMODE(private.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(output_items.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(output_summary.stat().st_mode), 0o600)
            original = output_items.read_bytes()

            second = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(second.returncode, 2)
            self.assertIn("already exists", second.stderr)
            self.assertEqual(output_items.read_bytes(), original)

    def test_pair_writer_rolls_back_its_first_file_on_second_path_race(self):
        """Catches a half-written snapshot when another process wins summary creation."""
        module = importlib.import_module("popup_eval.formal_item_materializer")
        with tempfile.TemporaryDirectory() as directory:
            private = Path(directory) / "private"
            private.mkdir()
            items = private / "formal-items.private.jsonl"
            summary = private / "formal-items-summary.private.json"
            original_write = module._write_private_new
            calls = 0

            def racing_write(path: Path, payload: bytes) -> None:
                nonlocal calls
                calls += 1
                if calls == 1:
                    original_write(path, payload)
                    return
                path.write_bytes(b"other-process-summary")
                raise module.FormalItemMaterializerError("simulated output race")

            with mock.patch.object(module, "_write_private_new", side_effect=racing_write):
                with self.assertRaisesRegex(ValueError, "simulated output race"):
                    module._write_private_pair_new(
                        items,
                        b"items\n",
                        summary,
                        b"summary\n",
                    )

            self.assertFalse(items.exists())
            self.assertEqual(summary.read_bytes(), b"other-process-summary")


if __name__ == "__main__":
    unittest.main()
