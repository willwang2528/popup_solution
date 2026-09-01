from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


PREGOLD_DIR = Path(__file__).resolve().parents[1]
PREDICTION_FREEZER = PREGOLD_DIR / "freeze_predictions.py"
LEDGER_FREEZER = PREGOLD_DIR / "freeze_operating_points.py"
SCRIPT = PREGOLD_DIR / "freeze_k50_predictions.py"
TIMESTAMP = "2026-09-01T11:00:00Z"
METHODS = ("mg-pu-k50-v1", "seeded-random-k50-v1")


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_jsonl(rows: list[dict]) -> bytes:
    return b"".join(canonical_json(row) + b"\n" for row in rows)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def formal_selected_item_hash(item_ids: set[str]) -> str:
    return sha256(("\n".join(sorted(item_ids)) + "\n").encode("utf-8"))


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_bytes(canonical_jsonl(rows))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def feature_row(index: int, *, gap: str | None) -> dict:
    item_id = f"PMJ-PILOT-{index:03d}"
    text = f"message-{index}"
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
                    "availability": "available",
                    "representation_kind": "test-structure",
                    "node_count": 1,
                    "artifact_sha256": "a" * 64,
                },
            }
        ],
        "candidates": [
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
                    "ancestors": ["android.app.Dialog"],
                    "resource_id": None,
                    "text": text,
                    "component_label": "Modal",
                    "icon_class": None,
                    "text_button_class": None,
                    "gap_reasons": [gap] if gap else [],
                },
            }
        ],
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


def visual_row(index: int) -> dict:
    return {
        "action_policy": "no_action",
        "confidence": 0.8,
        "critical_facts_pred": [],
        "human_gold_used": False,
        "message_text_pred": f"visual-message-{index}",
        "model_config_sha256": "b" * 64,
        "paper_result_eligible": False,
        "pilot_item_id": f"PMJ-PILOT-{index:03d}",
        "popup_present_pred": True,
        "protocol_sha256": "c" * 64,
        "scored": False,
        "status": "judged",
        "visual_bank_sha256": "d" * 64,
    }


class FreezeK50PredictionsCliTest(unittest.TestCase):
    def prepare(
        self,
        root: Path,
        *,
        tamper_source_message: bool = False,
        unsafe_visual_action: bool = False,
    ) -> tuple[Path, Path, Path, Path]:
        items = root / "items.jsonl"
        visual = root / "visual.jsonl"
        source = root / "private" / "source.private.jsonl"
        source_summary = root / "source-summary.json"
        ledger = root / "private" / "operating-points.private.json"
        root.joinpath("private").mkdir(mode=0o700)
        write_jsonl(
            items,
            [
                feature_row(1, gap="contradictory"),
                feature_row(2, gap="stale"),
                feature_row(3, gap="missing"),
                feature_row(4, gap="merged"),
                feature_row(5, gap="non_actionable"),
                feature_row(6, gap=None),
            ],
        )
        visual_rows = [visual_row(index) for index in range(1, 7)]
        if unsafe_visual_action:
            visual_rows[0]["debug"] = {"action": "tap"}
        write_jsonl(visual, visual_rows)
        prediction_result = subprocess.run(
            [
                sys.executable,
                str(PREDICTION_FREEZER),
                "--structured-features",
                str(items),
                "--visual-predictions",
                str(visual),
                "--private-output",
                str(source),
                "--public-summary",
                str(source_summary),
                "--expected-count",
                "6",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(prediction_result.returncode, 0, prediction_result.stderr)
        if tamper_source_message:
            rows = read_jsonl(source)
            target = next(
                row
                for row in rows
                if row["method_id"] == "mg-pu-gated-union-v1"
                and row["pilot_item_id"] == "PMJ-PILOT-001"
            )
            target["message_text_pred"] = "tampered-but-ledger-bound"
            write_jsonl(source, rows)
        ledger_result = subprocess.run(
            [
                sys.executable,
                str(LEDGER_FREEZER),
                "--items",
                str(items),
                "--visual-bank",
                str(visual),
                "--method-results",
                str(source),
                "--seed",
                "17",
                "--freeze-timestamp",
                TIMESTAMP,
                "--output",
                str(ledger),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(ledger_result.returncode, 0, ledger_result.stderr)
        return items, visual, source, ledger

    def run_cli(
        self,
        root: Path,
        *,
        prepared: tuple[Path, Path, Path, Path] | None = None,
        precreate_predictions: bool = False,
    ) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
        items, visual, source, ledger = prepared or self.prepare(root)
        predictions = root / "private" / "formal-k50.predictions.private.jsonl"
        commitment = root / "private" / "formal-k50.commitment.private.json"
        if precreate_predictions:
            predictions.write_text("do not replace\n", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--items",
                str(items),
                "--visual-bank",
                str(visual),
                "--method-results",
                str(source),
                "--operating-point-ledger",
                str(ledger),
                "--private-output",
                str(predictions),
                "--private-commitment",
                str(commitment),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return result, predictions, commitment

    def test_freezes_both_complete_k50_methods_with_verifiable_bindings(self) -> None:
        """Catches incomplete coverage, wrong selected IDs, or unbound input snapshots."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepared = self.prepare(root)
            result, predictions_path, commitment_path = self.run_cli(
                root, prepared=prepared
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            rows = read_jsonl(predictions_path)
            commitment = json.loads(commitment_path.read_text(encoding="utf-8"))
            ledger = json.loads(prepared[3].read_text(encoding="utf-8"))
            self.assertEqual(len(rows), 12)
            self.assertEqual({row["method_id"] for row in rows}, set(METHODS))
            expected_ids = {f"PMJ-PILOT-{index:03d}" for index in range(1, 7)}
            for method_id, ledger_key in (
                ("mg-pu-k50-v1", "mg_pu"),
                ("seeded-random-k50-v1", "seeded_random"),
            ):
                method_rows = [row for row in rows if row["method_id"] == method_id]
                self.assertEqual({row["pilot_item_id"] for row in method_rows}, expected_ids)
                selected = {
                    row["pilot_item_id"] for row in method_rows if row["visual_called"]
                }
                self.assertEqual(
                    selected,
                    set(
                        ledger["operating_points"]["K50"][ledger_key][
                            "selected_item_ids"
                        ]
                    ),
                )
                self.assertEqual(len(selected), 3)
                sorted_rows = sorted(method_rows, key=lambda row: row["pilot_item_id"])
                self.assertEqual(
                    commitment["methods"][method_id]["frozen_prediction_sha256"],
                    sha256(canonical_jsonl(sorted_rows)),
                )
                self.assertEqual(
                    commitment["methods"][method_id]["selected_item_set_sha256"],
                    formal_selected_item_hash(selected),
                )
                self.assertEqual(
                    commitment["methods"][method_id][
                        "operating_point_selected_item_set_sha256"
                    ],
                    ledger["operating_points"]["K50"][ledger_key][
                        "selected_item_set_sha256"
                    ],
                )
                receipt_binding = commitment["methods"][method_id][
                    "formal_receipt_hash_binding"
                ]
                self.assertEqual(
                    receipt_binding["selected_item_set_sha256"],
                    formal_selected_item_hash(selected),
                )
                self.assertEqual(
                    receipt_binding["frozen_prediction_sha256"],
                    sha256(canonical_jsonl(sorted_rows)),
                )
                self.assertNotIn("actual_budget", receipt_binding)
                for row in method_rows:
                    binding = row["freeze_binding"]
                    self.assertEqual(binding["operating_point"], "K50")
                    self.assertEqual(
                        binding["source_method_snapshot_sha256"],
                        sha256(prepared[2].read_bytes()),
                    )
                    self.assertEqual(
                        binding["visual_bank_input_sha256"],
                        sha256(prepared[1].read_bytes()),
                    )
                    self.assertEqual(
                        binding["budget_sha256"],
                        ledger["operating_points"]["K50"]["budget_sha256"],
                    )
                    self.assertEqual(
                        binding["operating_point_selected_item_set_sha256"],
                        ledger["operating_points"]["K50"][ledger_key][
                            "selected_item_set_sha256"
                        ],
                    )
                    self.assertEqual(
                        binding["formal_selected_item_set_sha256"],
                        formal_selected_item_hash(selected),
                    )
                    self.assertEqual(row["action_policy"], "no_action")
                    self.assertFalse(row["human_gold_used"])
                    self.assertFalse(row["scored"])
                    self.assertFalse(row["paper_result_eligible"])
                    serialized = json.dumps(row, sort_keys=True).casefold()
                    self.assertNotIn("metrics", serialized)
                    self.assertNotIn("recovery", serialized)
            self.assertEqual(commitment["status"], "frozen_pregold_k50_prediction_pair")
            self.assertFalse(commitment["formal_budget_receipt_ready"])
            self.assertFalse(commitment["paper_result_eligible"])
            self.assertEqual(stat.S_IMODE(predictions_path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(commitment_path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(predictions_path.parent.stat().st_mode), 0o700)

    def test_rejects_visual_bank_changed_after_ledger_freeze(self) -> None:
        """Catches prediction generation from a visual bank not committed by the ledger."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepared = list(self.prepare(root))
            rows = read_jsonl(prepared[1])
            rows[0]["message_text_pred"] = "changed after ledger"
            write_jsonl(prepared[1], rows)

            result, predictions, commitment = self.run_cli(
                root, prepared=tuple(prepared)
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("visual bank input hash mismatch", result.stderr.lower())
            self.assertFalse(predictions.exists())
            self.assertFalse(commitment.exists())

    def test_rejects_a_ledger_bound_but_recomputed_method_snapshot_mismatch(self) -> None:
        """Catches a ledger binding arbitrary MG-PU text rather than the shared freezer output."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepared = self.prepare(root, tamper_source_message=True)

            result, predictions, commitment = self.run_cli(root, prepared=prepared)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("source method snapshot does not match", result.stderr.lower())
            self.assertFalse(predictions.exists())
            self.assertFalse(commitment.exists())

    def test_rejects_tampered_selected_id_commitment(self) -> None:
        """Catches selected rows diverging from the ledger's selected-ID hash."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepared = list(self.prepare(root))
            ledger = json.loads(prepared[3].read_text(encoding="utf-8"))
            ledger["operating_points"]["K50"]["mg_pu"]["selected_item_ids"].reverse()
            prepared[3].write_bytes(canonical_json(ledger) + b"\n")

            result, predictions, commitment = self.run_cli(
                root, prepared=tuple(prepared)
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("selected ledger", result.stderr.lower())
            self.assertFalse(predictions.exists())
            self.assertFalse(commitment.exists())

    def test_rejects_hidden_action_payload_even_when_upstream_ledgers_bind_it(self) -> None:
        """Catches an action-bearing extension that older pregold validators ignore."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepared = self.prepare(root, unsafe_visual_action=True)

            result, predictions, commitment = self.run_cli(root, prepared=prepared)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("action or recovery field", result.stderr.lower())
            self.assertFalse(predictions.exists())
            self.assertFalse(commitment.exists())

    def test_refuses_to_replace_any_existing_private_output(self) -> None:
        """Catches silent replacement of a frozen prediction commitment."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepared = self.prepare(root)

            result, predictions, commitment = self.run_cli(
                root, prepared=prepared, precreate_predictions=True
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("output already exists", result.stderr.lower())
            self.assertEqual(predictions.read_text(encoding="utf-8"), "do not replace\n")
            self.assertFalse(commitment.exists())


if __name__ == "__main__":
    unittest.main()
