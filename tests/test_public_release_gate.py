from __future__ import annotations

import fnmatch
import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PublicReleaseGateTests(unittest.TestCase):
    def test_dataset_manifest_uses_the_item_schema_version_and_complete_union_counts(self):
        """Break caught: manifest drift hides 44 V1 fields or misstates schema version."""
        manifest = json.loads(
            (ROOT / "dataset-v1" / "DATASET_MANIFEST.json").read_text(
                encoding="utf-8"
            )
        )
        item_schema = json.loads(
            (ROOT / "dataset-v1" / "schema" / "item.schema.json").read_text(
                encoding="utf-8"
            )
        )
        field_catalog = json.loads(
            (ROOT / "dataset-v1" / "schema" / "field_catalog.json").read_text(
                encoding="utf-8"
            )
        )
        crosswalk = json.loads(
            (
                ROOT
                / "dataset-v1"
                / "schema"
                / "source_to_item_crosswalk.json"
            ).read_text(encoding="utf-8")
        )
        schema_version = item_schema["$defs"]["identity"]["properties"][
            "schema_version"
        ]["const"]
        self.assertEqual(manifest["schema_version"], schema_version)
        self.assertEqual(field_catalog["schema_version"], schema_version)
        self.assertEqual(crosswalk["schema_version"], schema_version)
        self.assertEqual(
            manifest["source_field_union"],
            {
                "ppt_papers": 14,
                "core_experimental_seed_papers": 6,
                "schema_method_reference_papers": 8,
                "literature_atomic_fields": 90,
                "our_method_atomic_fields": 165,
                "crosswalk_entries": 255,
                "unmapped_source_fields": 0,
                "v1_profile_extension_fields": 44,
                "combined_traceable_rows": 299,
            },
        )

    def test_manifest_preserves_slide_14_five_level_advanced_boundary(self):
        """Break caught: business persistence B disappears or metric names drift."""
        manifest = json.loads(
            (ROOT / "dataset-v1" / "DATASET_MANIFEST.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            manifest["advanced_only"],
            ["D", "C_tech", "C_a11y", "B", "T", "VTR_tech", "A_VTR"],
        )
        self.assertEqual(
            manifest["advanced_field_bindings"]["B"],
            "/verification/persistence/business_choice_persisted",
        )
        self.assertEqual(
            manifest["advanced_field_bindings"]["VTR_tech"],
            "/verification/metrics/VTR_tech",
        )
        self.assertEqual(
            manifest["advanced_field_bindings"]["A_VTR"],
            "/verification/metrics/A_VTR",
        )

    def test_public_manifest_never_hashes_withheld_private_artifacts(self):
        """Break caught: public manifest references files intentionally not shipped."""
        manifest = json.loads(
            (ROOT / "dataset-v1" / "DATASET_MANIFEST.json").read_text(
                encoding="utf-8"
            )
        )
        forbidden = {
            "work/model-preannotation-*.jsonl",
            "annotation-pilot/private/*",
            "empirical-pilot/private/*",
            "work/annotation-media/*",
            "../experiments/v1-message/features/private/*",
            "../experiments/v1-message/ocr/results/*",
            "../experiments/v1-message/pregold/private/*",
            "../experiments/v1-message/statistics/private/*",
        }
        leaked = sorted(
            path
            for path in manifest["artifact_sha256"]
            if any(fnmatch.fnmatch(path, pattern) for pattern in forbidden)
        )
        self.assertEqual(leaked, [])

    def test_every_public_manifest_artifact_hash_matches_the_shipped_file(self):
        """Break caught: release metadata retains a stale hash after an artifact edit."""
        manifest_path = ROOT / "dataset-v1" / "DATASET_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        dataset_root = manifest_path.parent
        mismatches = []
        for relative_path, expected_sha256 in manifest["artifact_sha256"].items():
            artifact = dataset_root / relative_path
            if not artifact.is_file():
                mismatches.append((relative_path, "missing"))
                continue
            actual_sha256 = hashlib.sha256(artifact.read_bytes()).hexdigest()
            if actual_sha256 != expected_sha256:
                mismatches.append((relative_path, actual_sha256))
        self.assertEqual(mismatches, [])

    def test_all_private_or_text_bearing_work_roots_are_git_ignored(self):
        patterns = {
            line.strip()
            for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        required = {
            "dataset-v1/work/annotation-media/",
            "dataset-v1/annotation-pilot/private/",
            "dataset-v1/empirical-pilot/private/",
            "dataset-v1/work/model-preannotation-*.jsonl",
            "experiments/v1-message/features/private/",
            "experiments/v1-message/ocr/results/",
            "experiments/v1-message/ocr/.build/",
            "experiments/v1-message/pregold/private/",
            "experiments/v1-message/statistics/private/",
            "dataset-v1/android-capture/incoming/",
            "dataset-v1/android-capture/private/",
            "dataset-v1/android-capture/results/",
        }
        self.assertEqual(required - patterns, set())

    def test_docs_can_be_released_while_empirical_dataset_remains_blocked(self):
        gate = json.loads(
            (ROOT / "PUBLIC_RELEASE_GATE.json").read_text(encoding="utf-8")
        )
        self.assertTrue(gate["user_public_push_authorization"]["authorized"])
        self.assertIn(
            gate["release_classes"]["research_docs_and_code"]["status"],
            {"eligible_after_git_content_audit", "released_after_git_content_audit"},
        )
        empirical = gate["release_classes"]["empirical_dataset"]
        self.assertEqual(empirical["status"], "blocked")
        self.assertEqual(empirical["human_gold_count"], 0)
        self.assertFalse(empirical["paper_result_eligible"])


if __name__ == "__main__":
    unittest.main()
