from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


EMPIRICAL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = EMPIRICAL_DIR / "materialize_pending_union.py"
DATASET_DIR = EMPIRICAL_DIR.parent
SCHEMA_PATH = DATASET_DIR / "schema" / "item.schema.json"
VALIDATOR_PATH = DATASET_DIR / "scripts" / "validate_dataset.py"


def canonical_jsonl(rows: list[dict]) -> bytes:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
        for row in rows
    ).encode("utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_bytes(canonical_jsonl(rows))


def feature_row(index: int) -> dict:
    item_id = f"PMJ-PILOT-{index:03d}"
    candidates = []
    if index % 2:
        candidates.append(
            {
                "candidate_id": f"{item_id}-structured-0000",
                "source_channel": "structured",
                "normalized": {
                    "name_or_text": f"PRIVATE UI TEXT {index}",
                    "value_or_hint": None,
                    "visible": True,
                },
                "features": {
                    "node_index": 0,
                    "depth": 1,
                    "class": "android.widget.TextView",
                    "bounds": [10, 20, 100, 80],
                    "clickable": False,
                    "ancestors": ["android.app.Dialog"],
                    "resource_id": f"private:id/message_{index}",
                    "text": f"PRIVATE UI TEXT {index}",
                    "component_label": "Modal",
                    "icon_class": None,
                    "text_button_class": None,
                    "gap_reasons": [],
                },
            }
        )
    return {
        "identity": {
            "item_id": item_id,
            "pilot_item_id": item_id,
            "record_kind": "unscored_pregold_input",
        },
        "observations": [
            {
                "observation_id": f"{item_id}-pre-action-structured",
                "phase": "pre_action",
                "structured_representation": {
                    "availability": "available" if candidates else "missing",
                    "representation_kind": "rico-semantic-json",
                    "node_count": len(candidates),
                    "artifact_sha256": (f"{index:064x}" if candidates else None),
                },
            }
        ],
        "candidates": candidates,
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


def prediction_rows(count: int) -> list[dict]:
    rows: list[dict] = []
    for index in range(1, count + 1):
        item_id = f"PMJ-PILOT-{index:03d}"
        for method_id in (
            "structured-only-v1",
            "the-ok-text-rule",
            "mg-pu-gated-union-v1",
        ):
            visual_called = method_id == "mg-pu-gated-union-v1" and index % 2 == 0
            rows.append(
                {
                    "action_policy": "no_action",
                    "confidence": 0.75,
                    "critical_facts_pred": [f"PRIVATE FACT {index}"],
                    "human_gold_used": False,
                    "message_text_pred": f"PRIVATE PREDICTION {index}",
                    "method_id": method_id,
                    "paper_result_eligible": False,
                    "pilot_item_id": item_id,
                    "popup_present_pred": True,
                    "route_reason": (
                        "visual_frozen_prediction"
                        if visual_called
                        else "popup_scoped_structure_sufficient"
                    ),
                    "scored": False,
                    "status": "judged",
                    "visual_called": visual_called,
                }
            )
    return rows


def load_validator():
    spec = importlib.util.spec_from_file_location("pending_union_validator", VALIDATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PendingUnionMaterializerCliTest(unittest.TestCase):
    def run_cli(
        self,
        root: Path,
        *,
        features: Path,
        predictions: Path | None = None,
        expected_count: int = 30,
    ) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
        private_output = root / "private" / "pilot.pending-union.private.jsonl"
        public_summary = root / "PUBLIC_PENDING_UNION_SUMMARY.json"
        command = [
            sys.executable,
            str(SCRIPT),
            "--features",
            str(features),
            "--private-output",
            str(private_output),
            "--public-summary",
            str(public_summary),
            "--expected-count",
            str(expected_count),
        ]
        if predictions is not None:
            command.extend(["--pregold-predictions", str(predictions)])
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        return result, private_output, public_summary

    def test_materializes_30_pending_union_items_without_gold_actions_or_recovery(self) -> None:
        """Catches label fabrication, executable output, or advanced recovery promotion."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            features = root / "features.private.jsonl"
            predictions = root / "predictions.private.jsonl"
            write_jsonl(features, [feature_row(index) for index in range(1, 31)])
            write_jsonl(predictions, prediction_rows(30))

            result, private_output, public_summary = self.run_cli(
                root, features=features, predictions=predictions
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            rows = [json.loads(line) for line in private_output.read_text().splitlines()]
            self.assertEqual(len(rows), 30)
            self.assertEqual(len({row["identity"]["item_id"] for row in rows}), 30)
            self.assertEqual(
                {row["identity"]["pilot_item_id"] for row in rows},
                {f"PMJ-PILOT-{index:03d}" for index in range(1, 31)},
            )
            self.assertEqual(stat.S_IMODE(private_output.parent.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(private_output.stat().st_mode), 0o600)
            first_candidate = rows[0]["candidates"][0]
            self.assertEqual(
                first_candidate["android_raw"]["bounds"], [10, 20, 100, 80]
            )
            self.assertEqual(first_candidate["android_raw"]["size"], [90, 60])
            self.assertEqual(first_candidate["android_raw"]["position"], [10, 20])
            self.assertIsNone(first_candidate["normalized"]["bounds_normalized"])
            for row in rows:
                identity = row["identity"]
                self.assertEqual(identity["record_kind"], "real_app")
                self.assertEqual(identity["collection_status"], "collected")
                self.assertEqual(identity["split"], "pilot")
                self.assertIsNone(row["environment"]["device_kind"])
                labels = row["message_judgment"]["labels"]
                self.assertIsNone(labels["popup_present_gt"])
                self.assertIsNone(labels["blocking_gt"])
                self.assertIsNone(labels["message_text_gt"])
                self.assertEqual(labels["critical_facts_gt"], [])
                self.assertEqual(
                    labels["message_text_observability"], "pending_annotation"
                )
                self.assertEqual(labels["evidence_uris"], [])
                gap_gold = row["message_judgment"]["gap_ground_truth"]
                self.assertEqual(gap_gold["status"], "pending_audit")
                self.assertIsNone(gap_gold["structured_evidence_available"])
                self.assertIsNone(gap_gold["structured_message_complete_gt"])
                self.assertEqual(gap_gold["gap_reasons_gt"], [])
                self.assertEqual(
                    gap_gold["critical_facts_missing_from_structure_gt"], []
                )
                self.assertEqual(gap_gold["evidence_uris"], [])
                self.assertEqual(row["annotations"], [])
                self.assertEqual(row["action_attempts"], [])
                self.assertEqual(row["decision"]["policy"]["decision"], "no_action")
                self.assertTrue(row["provenance"]["collector_and_model_versions"]["prediction_gold_blind"])
                self.assertFalse(row["provenance"]["collector_and_model_versions"]["prediction_scored"])
                self.assertFalse(
                    row["provenance"]["collector_and_model_versions"][
                        "prediction_paper_result_eligible"
                    ]
                )
                message_eligibility = row["message_judgment"]["eligibility"]
                self.assertFalse(message_eligibility["eligible_for_v1_presence_metric"])
                self.assertFalse(message_eligibility["eligible_for_v1_message_metric"])
                self.assertEqual(
                    message_eligibility["exclusion_reasons"],
                    ["pending_human_annotation"],
                )
                verification = row["verification"]
                self.assertIsNone(verification["dismissal"]["D"])
                self.assertIsNone(verification["technical_context_recovery"]["C_tech"])
                self.assertIsNone(verification["accessible_context_recovery"]["C_a11y"])
                self.assertIsNone(verification["task"]["T"])
                self.assertIsNone(verification["metrics"]["VTR_tech"])
                self.assertIsNone(verification["metrics"]["A_VTR"])
                self.assertEqual(verification["dismissal"]["observability"], "not_observable")
                self.assertEqual(
                    verification["accessible_context_recovery"]["observability"],
                    "not_observable",
                )
                self.assertEqual(
                    verification["eligibility"]["exclusion_reasons"],
                    ["pending_human_annotation"],
                )
                self.assertEqual(
                    row["message_judgment"]["prediction"]["model_or_rule_version"],
                    "mg-pu-gated-union-v1",
                )
            self.assertTrue(public_summary.exists())

    def test_materialized_rows_validate_against_the_full_union_schema(self) -> None:
        """Catches incomplete union containers or pending values outside the schema contract."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            features = root / "features.private.jsonl"
            write_jsonl(features, [feature_row(index) for index in range(1, 31)])

            result, private_output, _ = self.run_cli(root, features=features)

            self.assertEqual(result.returncode, 0, result.stderr)
            validator = load_validator()
            schema = validator.load_json(SCHEMA_PATH)
            rows = validator.load_jsonl(private_output)
            schema_errors = [
                error
                for index, row in enumerate(rows)
                for error in validator.validate_schema(row, schema, schema, f"item[{index}]")
            ]
            self.assertEqual(schema_errors, [])
            semantic_errors = [
                error
                for index, row in enumerate(rows)
                for error in validator.check_item(row, index)[0]
            ]
            self.assertEqual(semantic_errors, [])

    def test_rejects_label_bearing_feature_or_pregold_input(self) -> None:
        """Catches accidental raw manifest, source-label, human-gold, or metric leakage."""
        unsafe_cases = []
        feature = feature_row(1)
        feature["popup_present_gt"] = True
        unsafe_cases.append(("feature", feature))
        prediction = prediction_rows(1)[0]
        prediction["annotations"] = [{"annotator_role": "researcher"}]
        unsafe_cases.append(("prediction", prediction))

        for kind, unsafe_row in unsafe_cases:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                features = root / "features.private.jsonl"
                predictions = root / "predictions.private.jsonl"
                write_jsonl(
                    features,
                    [unsafe_row] if kind == "feature" else [feature_row(1)],
                )
                if kind == "prediction":
                    write_jsonl(predictions, [unsafe_row])
                result, private_output, public_summary = self.run_cli(
                    root,
                    features=features,
                    predictions=predictions if kind == "prediction" else None,
                    expected_count=1,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("forbidden", result.stderr.casefold())
                self.assertFalse(private_output.exists())
                self.assertFalse(public_summary.exists())

    def test_public_summary_contains_only_aggregate_nonclaim_evidence(self) -> None:
        """Catches publication of item identities, UI text, filesystem paths, or scores."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            features = root / "features.private.jsonl"
            predictions = root / "predictions.private.jsonl"
            write_jsonl(features, [feature_row(index) for index in range(1, 31)])
            write_jsonl(predictions, prediction_rows(30))

            result, private_output, public_summary = self.run_cli(
                root, features=features, predictions=predictions
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            summary_text = public_summary.read_text(encoding="utf-8")
            summary = json.loads(summary_text)
            self.assertNotIn("PMJ-PILOT", summary_text)
            self.assertNotIn("PRIVATE UI TEXT", summary_text)
            self.assertNotIn("PRIVATE PREDICTION", summary_text)
            self.assertNotIn(str(root.resolve()), summary_text)
            self.assertEqual(
                set(summary),
                {
                    "contract",
                    "counts",
                    "field_coverage",
                    "hashes",
                    "negative_claims",
                },
            )
            self.assertEqual(summary["counts"]["items"], 30)
            self.assertEqual(summary["counts"]["pending_human_annotation"], 30)
            self.assertEqual(
                summary["hashes"]["private_union_bundle_sha256"],
                hashlib.sha256(private_output.read_bytes()).hexdigest(),
            )
            self.assertTrue(summary["negative_claims"]["gold_blind"])
            self.assertFalse(summary["negative_claims"]["scored"])
            self.assertFalse(summary["negative_claims"]["paper_result_eligible"])
            self.assertFalse(summary["negative_claims"]["real_device_episode_claim"])
            self.assertFalse(summary["negative_claims"]["user_experience_claim"])


if __name__ == "__main__":
    unittest.main()
