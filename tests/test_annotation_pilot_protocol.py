from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = ROOT / "dataset-v1" / "annotation-pilot"
CANDIDATES = (
    ROOT
    / "dataset-v1"
    / "candidates"
    / "popsweeper_candidates_n120.jsonl"
)
BUILDER = (
    ROOT
    / "dataset-v1"
    / "annotation-pilot"
    / "scripts"
    / "build_pilot_bundle.py"
)


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class AnnotationPilotProtocolArtifactTests(unittest.TestCase):
    def test_popup_scope_is_observable_and_does_not_require_inferred_dismissibility(self):
        scope_path = PILOT_ROOT / "POPUP_SCOPE_V1.json"
        self.assertTrue(scope_path.is_file(), "machine-readable popup scope must exist")
        scope = json.loads(scope_path.read_text(encoding="utf-8"))

        self.assertEqual(scope["decision_basis"], "screenshot_observable_only")
        self.assertFalse(scope["requires_dismissibility_observation"])
        self.assertIn("interruptive_bottom_sheet", scope["included_examples"])
        self.assertIn("navigation_drawer", scope["excluded_examples"])
        self.assertIn("toast_or_snackbar", scope["excluded_examples"])
        self.assertIn("permission_security_control", scope["out_of_scope_examples"])
        self.assertEqual(
            scope["ambiguous_policy"],
            "uncertain_with_reason_not_forced_binary",
        )
        self.assertIn("visual_separability_rule", scope)

    def test_out_of_scope_is_explicit_and_cannot_be_hidden_as_uncertain(self):
        schema_path = PILOT_ROOT / "schemas" / "annotation_record.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        self.assertIn(
            "out_of_scope",
            schema["properties"]["presence_label"]["enum"],
        )
        self.assertIn("out_of_scope_reason", schema["required"])
        self.assertIn("out_of_scope_reason", schema["properties"])
        reason_values = set(schema["properties"]["out_of_scope_reason"]["enum"])
        self.assertIn("captcha", reason_values)
        self.assertIn("permission_security_control", reason_values)

    def test_fixed_manifest_is_a_balanced_candidate_subset_without_human_gold(self):
        manifest_path = PILOT_ROOT / "manifests" / "pilot_batch_30.jsonl"
        self.assertTrue(
            manifest_path.is_file(),
            "the fixed 30-item pilot manifest must be materialized",
        )

        rows = load_jsonl(manifest_path)
        candidate_ids = {
            row["source_record_id"] for row in load_jsonl(CANDIDATES)
        }

        self.assertEqual(len(rows), 30)
        self.assertEqual(len({row["pilot_item_id"] for row in rows}), 30)
        self.assertEqual(len({row["source_record_id"] for row in rows}), 30)
        self.assertTrue(
            {row["source_record_id"] for row in rows}.issubset(candidate_ids)
        )
        self.assertEqual(
            Counter(row["source_sampling_label"] for row in rows),
            Counter({"ads": 15, "no_ads": 15}),
        )
        self.assertEqual(
            Counter(row["official_split_audit_stratum"] for row in rows),
            Counter({"train": 18, "valid": 6, "test": 6}),
        )
        self.assertEqual(
            Counter(row["source_kind"] for row in rows),
            Counter({"rico_numeric_candidate": 22, "recorded_app_frame": 8}),
        )
        for row in rows:
            self.assertFalse(any(key.endswith("_gt") for key in row))
            self.assertEqual(row["human_message_gold_status"], "pending")
            self.assertFalse(row["eligible_for_message_metrics"])
            self.assertEqual(
                row["raw_image_distribution"],
                "adapter_only_not_redistributed",
            )
            self.assertNotIn("raw_image", row)
            self.assertNotIn("message_text", row)

    def test_blind_templates_cover_all_items_without_source_or_peer_leakage(self):
        manifest_path = PILOT_ROOT / "manifests" / "pilot_batch_30.jsonl"
        self.assertTrue(
            manifest_path.is_file(),
            "the manifest must exist before blind templates can be audited",
        )
        manifest = load_jsonl(manifest_path)
        manifest_ids = {row["pilot_item_id"] for row in manifest}
        orders: dict[str, list[str]] = {}

        for role in ("a", "b"):
            path = PILOT_ROOT / "templates" / f"annotator_{role}.jsonl"
            self.assertTrue(path.is_file(), f"missing blind template {path.name}")
            rows = load_jsonl(path)
            self.assertEqual(len(rows), 30)
            self.assertEqual({row["pilot_item_id"] for row in rows}, manifest_ids)
            self.assertEqual({row["annotator_role"] for row in rows}, {role.upper()})
            orders[role] = [row["pilot_item_id"] for row in rows]

            for row in rows:
                self.assertEqual(row["record_status"], "blank")
                self.assertIsNone(row["presence_label"])
                self.assertIsNone(row["out_of_scope_reason"])
                self.assertIsNone(row["message_text"])
                self.assertIsNone(row["message_observability"])
                self.assertEqual(row["semantic_slots"], [])
                self.assertFalse(row["evidence"]["raw_image_copied"])
                serialized = json.dumps(row, ensure_ascii=False)
                self.assertNotIn("source_record_id", serialized)
                self.assertNotIn("archive_member", serialized)
                self.assertNotIn("source_sampling_label", serialized)
                self.assertNotIn("peer_annotation", serialized)
                self.assertNotIn("model_prediction", serialized)

        self.assertNotEqual(orders["a"], orders["b"])

    def test_machine_readable_schemas_and_adjudication_templates_exist(self):
        expected = [
            PILOT_ROOT / "schemas" / "annotation_record.schema.json",
            PILOT_ROOT / "schemas" / "adjudication_input.schema.json",
            PILOT_ROOT / "schemas" / "adjudication_output.schema.json",
            PILOT_ROOT / "schemas" / "gap_independent_audit_record.schema.json",
            PILOT_ROOT / "schemas" / "gap_adjudication_output.schema.json",
            PILOT_ROOT / "templates" / "adjudication_input.template.json",
            PILOT_ROOT / "templates" / "adjudication_output.template.json",
        ]
        for path in expected:
            self.assertTrue(path.is_file(), f"missing protocol artifact {path}")
            parsed = json.loads(path.read_text(encoding="utf-8"))
            self.assertIsInstance(parsed, dict)

    def test_builder_reproduces_the_committed_fixed_batch_and_blind_templates(self):
        self.assertTrue(BUILDER.is_file(), "the pilot bundle builder must exist")
        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory) / "annotation-pilot"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(BUILDER),
                    "--candidates",
                    str(CANDIDATES),
                    "--output-root",
                    str(output_root),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            for relative in (
                Path("manifests/pilot_batch_30.jsonl"),
                Path("templates/annotator_a.jsonl"),
                Path("templates/annotator_b.jsonl"),
            ):
                self.assertEqual(
                    (output_root / relative).read_bytes(),
                    (PILOT_ROOT / relative).read_bytes(),
                )


if __name__ == "__main__":
    unittest.main()
