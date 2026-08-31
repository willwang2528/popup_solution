from __future__ import annotations

import json
import hashlib
from pathlib import Path
import subprocess
import stat
import sys
import tempfile
import unittest


PREGOLD_DIR = Path(__file__).resolve().parents[1]
SCRIPT = PREGOLD_DIR / "freeze_predictions.py"


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def manifest_rows(count: int, *, flip_leakage: bool = False) -> list[dict]:
    rows = []
    for index in range(1, count + 1):
        rows.append(
            {
                "pilot_item_id": f"PMJ-PILOT-{index:03d}",
                "popup_present_gt": (index % 2 == 0) ^ flip_leakage,
                "sampling_stratum": "changed" if flip_leakage else "original",
                "eligible_for_v1_message_metrics": flip_leakage,
                "message_annotation_status": "changed" if flip_leakage else "pending",
                "source_record_id": f"ignored-{index}",
            }
        )
    return rows


def structured_feature(
    item_id: str,
    *,
    text: str | None,
    gap_reasons: list[str] | None = None,
    ancestors: list[str] | None = None,
) -> dict:
    candidates = []
    if text is not None:
        candidates.append(
            {
                "candidate_id": f"{item_id}-node-1",
                "source_channel": "structured",
                "normalized": {
                    "name_or_text": text,
                    "value_or_hint": None,
                    "visible": True,
                },
                "features": {
                    "node_index": 1,
                    "depth": 2,
                    "class": "android.widget.TextView",
                    "bounds": [10, 20, 100, 50],
                    "clickable": False,
                    "ancestors": ["android.app.Dialog"] if ancestors is None else ancestors,
                    "resource_id": None,
                    "text": text,
                    "component_label": None,
                    "icon_class": None,
                    "text_button_class": None,
                    "gap_reasons": gap_reasons or [],
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
                    "availability": "available" if text is not None else "missing",
                    "representation_kind": "rico-semantic-json",
                    "node_count": 1 if text is not None else 0,
                    "artifact_sha256": "a" * 64 if text is not None else None,
                },
            }
        ],
        "candidates": candidates,
        "action_attempts": [],
        "decision": {"policy": {"decision": "no_action"}},
        "metadata": {
            "contract_version": "pregold-feature-v1",
            "gold_blind": True,
            "gold_used": False,
            "scored": False,
            "paper_result_eligible": False,
            "action_mode": "no_action",
        },
    }


class FreezePredictionsCliTest(unittest.TestCase):
    def run_cli(
        self,
        root: Path,
        *,
        features: Path,
        manifest: Path | None = None,
        visual: Path | None = None,
        suffix: str = "run",
        expected_count: int,
    ) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
        private_output = root / "private" / f"{suffix}.private.jsonl"
        public_summary = root / f"{suffix}.summary.json"
        command = [
            sys.executable,
            str(SCRIPT),
            "--structured-features",
            str(features),
            "--private-output",
            str(private_output),
            "--public-summary",
            str(public_summary),
            "--expected-count",
            str(expected_count),
        ]
        if manifest is not None:
            command.extend(["--manifest", str(manifest)])
        if visual is not None:
            command.extend(["--visual-predictions", str(visual)])
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        return result, private_output, public_summary

    def test_manifest_label_status_and_stratum_changes_do_not_change_outputs(self) -> None:
        """Catches any future consumption or hashing of source-label leakage."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_a = root / "manifest-a.jsonl"
            manifest_b = root / "manifest-b.jsonl"
            features = root / "features.jsonl"
            write_jsonl(manifest_a, manifest_rows(2, flip_leakage=False))
            write_jsonl(manifest_b, manifest_rows(2, flip_leakage=True))
            write_jsonl(
                features,
                [
                    structured_feature("PMJ-PILOT-001", text="Network unavailable"),
                    structured_feature("PMJ-PILOT-002", text=None),
                ],
            )

            run_a, private_a, summary_a = self.run_cli(
                root,
                features=features,
                manifest=manifest_a,
                suffix="a",
                expected_count=2,
            )
            run_b, private_b, summary_b = self.run_cli(
                root,
                features=features,
                manifest=manifest_b,
                suffix="b",
                expected_count=2,
            )

            self.assertEqual(run_a.returncode, 0, run_a.stderr)
            self.assertEqual(run_b.returncode, 0, run_b.stderr)
            self.assertEqual(private_a.read_bytes(), private_b.read_bytes())
            self.assertEqual(summary_a.read_bytes(), summary_b.read_bytes())

    def test_freezes_structured_and_gated_union_without_scoring_or_actions(self) -> None:
        """Catches routing, unsafe action output, and accidental metric production."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.jsonl"
            features = root / "features.jsonl"
            visual = root / "visual.jsonl"
            write_jsonl(manifest, manifest_rows(3))
            write_jsonl(
                features,
                [
                    structured_feature("PMJ-PILOT-001", text="Update available"),
                    structured_feature(
                        "PMJ-PILOT-002", text="Sign in", gap_reasons=["merged"]
                    ),
                    structured_feature("PMJ-PILOT-003", text=None),
                ],
            )
            write_jsonl(
                visual,
                [
                    {
                        "pilot_item_id": "PMJ-PILOT-002",
                        "status": "judged",
                        "popup_present_pred": True,
                        "message_text_pred": "Session expired. Sign in again.",
                        "critical_facts_pred": ["Session expired"],
                        "confidence": 0.8,
                    },
                    {
                        "pilot_item_id": "PMJ-PILOT-003",
                        "status": "judged",
                        "popup_present_pred": True,
                        "message_text_pred": None,
                        "critical_facts_pred": [],
                        "confidence": 0.9,
                    },
                ],
            )

            result, private_output, public_summary = self.run_cli(
                root,
                features=features,
                manifest=manifest,
                visual=visual,
                expected_count=3,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            predictions = read_jsonl(private_output)
            self.assertEqual(stat.S_IMODE(private_output.parent.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(private_output.stat().st_mode), 0o600)
            self.assertEqual(len(predictions), 9)
            by_key = {(row["method_id"], row["pilot_item_id"]): row for row in predictions}
            self.assertEqual(
                by_key[("structured-only-v1", "PMJ-PILOT-001")]["message_text_pred"],
                "Update available",
            )
            self.assertEqual(
                by_key[("mg-pu-gated-union-v1", "PMJ-PILOT-002")]["message_text_pred"],
                "Session expired. Sign in again.",
            )
            self.assertEqual(
                by_key[("mg-pu-gated-union-v1", "PMJ-PILOT-003")]["status"],
                "abstain",
            )
            self.assertEqual(
                by_key[("the-ok-text-rule", "PMJ-PILOT-003")]["status"],
                "abstain",
            )
            for row in predictions:
                self.assertFalse(row["human_gold_used"])
                self.assertFalse(row["scored"])
                self.assertFalse(row["paper_result_eligible"])
                self.assertEqual(row["action_policy"], "no_action")
                self.assertNotIn("action", row)
                self.assertNotIn("metrics", row)

            summary = json.loads(public_summary.read_text(encoding="utf-8"))
            self.assertFalse(summary["human_gold_used"])
            self.assertFalse(summary["scored"])
            self.assertFalse(summary["paper_result_eligible"])
            self.assertEqual(summary["action_policy"], "no_action")
            self.assertEqual(summary["input_item_count"], 3)
            self.assertEqual(
                set(summary["methods"]),
                {
                    "structured-only-v1",
                    "mg-pu-gated-union-v1",
                    "the-ok-text-rule",
                },
            )
            self.assertRegex(summary["predictions_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(summary["implementation_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(summary["the_ok_implementation_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(
                summary["the_ok_upstream_revision"],
                "b618948c0d24b917b3a46a88f5c1cf6ff84571cd",
            )
            self.assertEqual(
                summary.get("feature_builder_implementation_sha256"),
                hashlib.sha256(
                    (PREGOLD_DIR.parent / "features" / "build_pilot_features.py").read_bytes()
                ).hexdigest(),
            )
            self.assertEqual(
                summary.get("visual_adapter_implementation_sha256"),
                hashlib.sha256((PREGOLD_DIR / "adapt_model_preannotation.py").read_bytes()).hexdigest(),
            )
            self.assertEqual(summary.get("visual_evidence_is_formal_baseline"), False)
            self.assertEqual(summary.get("visual_model_identity_reproducible"), False)
            self.assertEqual(
                summary.get("visual_evidence_role"),
                "visual-evidence-without-model-reproducibility-attestation",
            )
            serialized = public_summary.read_text(encoding="utf-8")
            self.assertNotIn("Update available", serialized)
            self.assertNotIn("Session expired", serialized)
            self.assertNotIn(str(root.resolve()), serialized)
            self.assertNotIn("metrics", summary)

    def test_gated_union_requires_explicit_popup_scope_before_using_structure(self) -> None:
        """Catches host-page flattening being mistaken for popup-scoped evidence."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            features = root / "features.jsonl"
            visual = root / "visual.jsonl"
            write_jsonl(
                features,
                [
                    structured_feature(
                        "PMJ-PILOT-001", text="Host page title", ancestors=[]
                    ),
                    structured_feature(
                        "PMJ-PILOT-002", text="Dialog message", ancestors=["Dialog"]
                    ),
                ],
            )
            write_jsonl(
                visual,
                [
                    {
                        "pilot_item_id": "PMJ-PILOT-001",
                        "status": "judged",
                        "popup_present_pred": True,
                        "message_text_pred": "Visual popup message",
                        "critical_facts_pred": [],
                        "confidence": None,
                    }
                ],
            )

            result, private_output, _ = self.run_cli(
                root,
                features=features,
                visual=visual,
                expected_count=2,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            rows = {
                (row["method_id"], row["pilot_item_id"]): row
                for row in read_jsonl(private_output)
            }
            self.assertEqual(
                rows[("structured-only-v1", "PMJ-PILOT-001")]["message_text_pred"],
                "Host page title",
            )
            self.assertEqual(
                rows[("mg-pu-gated-union-v1", "PMJ-PILOT-001")]["message_text_pred"],
                "Visual popup message",
            )
            self.assertTrue(
                rows[("mg-pu-gated-union-v1", "PMJ-PILOT-001")]["visual_called"]
            )
            self.assertEqual(
                rows[("mg-pu-gated-union-v1", "PMJ-PILOT-002")]["message_text_pred"],
                "Dialog message",
            )
            self.assertFalse(
                rows[("mg-pu-gated-union-v1", "PMJ-PILOT-002")]["visual_called"]
            )

    def test_rejects_gold_or_metric_keys_in_feature_and_visual_inputs(self) -> None:
        """Catches acceptance of adjudication, gold, or metric-eligibility leakage."""
        cases = [
            (
                "feature-gold",
                "structured",
                {
                    **structured_feature("PMJ-PILOT-001", text="Hello"),
                    "message_judgment": {"labels": {"popup_present_gt": True}},
                },
            ),
            (
                "visual-metric",
                "visual",
                {
                    "pilot_item_id": "PMJ-PILOT-001",
                    "presence_label": "popup",
                    "metric_eligible": False,
                },
            ),
        ]
        for name, kind, unsafe_row in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                manifest = root / "manifest.jsonl"
                unsafe = root / "unsafe.jsonl"
                valid_features = root / "valid-features.jsonl"
                write_jsonl(manifest, manifest_rows(1))
                write_jsonl(unsafe, [unsafe_row])
                write_jsonl(
                    valid_features,
                    [structured_feature("PMJ-PILOT-001", text="Safe input")],
                )
                result, private_output, public_summary = self.run_cli(
                    root,
                    features=unsafe if kind == "structured" else valid_features,
                    manifest=manifest,
                    visual=unsafe if kind == "visual" else None,
                    expected_count=1,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("forbidden", result.stderr.lower())
                self.assertFalse(private_output.exists())
                self.assertFalse(public_summary.exists())

    def test_rejects_action_bearing_or_non_blind_structured_contract(self) -> None:
        """Catches action execution fields or a false gold-blind attestation."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.jsonl"
            features = root / "features.jsonl"
            row = structured_feature("PMJ-PILOT-001", text="Hello")
            row["action_attempts"] = [{"action": "tap"}]
            row["metadata"]["gold_blind"] = False
            write_jsonl(manifest, manifest_rows(1))
            write_jsonl(features, [row])

            result, private_output, public_summary = self.run_cli(
                root,
                features=features,
                manifest=manifest,
                expected_count=1,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("gold_blind", result.stderr)
            self.assertFalse(private_output.exists())
            self.assertFalse(public_summary.exists())

    def test_rejects_private_predictions_outside_a_private_directory(self) -> None:
        """Catches accidental placement of text-bearing predictions in publishable paths."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            features = root / "features.jsonl"
            write_jsonl(features, [structured_feature("PMJ-PILOT-001", text="Hello")])
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--structured-features",
                    str(features),
                    "--private-output",
                    str(root / "predictions.private.jsonl"),
                    "--public-summary",
                    str(root / "summary.json"),
                    "--expected-count",
                    "1",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("private", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
