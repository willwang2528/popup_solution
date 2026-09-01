from __future__ import annotations

import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


PREGOLD_DIR = Path(__file__).resolve().parents[1]
SCRIPT = PREGOLD_DIR / "freeze_operating_points.py"
TIMESTAMP = "2026-09-01T09:30:00Z"


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def feature_row(
    item_id: str,
    *,
    gap_reason: str | None = None,
    ambiguous: bool = False,
    missing: bool = False,
) -> dict:
    popup_scoped = not ambiguous
    text = None if missing else f"message-{item_id}"
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
                    "ancestors": ["android.app.Dialog"] if popup_scoped else ["root"],
                    "resource_id": None,
                    "text": text,
                    "component_label": "Modal" if popup_scoped else None,
                    "icon_class": None,
                    "text_button_class": None,
                    "gap_reasons": [gap_reason] if gap_reason else [],
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


def method_row(item_id: str, *, visual_called: bool) -> dict:
    return {
        "action_policy": "no_action",
        "confidence": None,
        "critical_facts_pred": [],
        "human_gold_used": False,
        "message_text_pred": None,
        "method_id": "mg-pu-gated-union-v1",
        "paper_result_eligible": False,
        "pilot_item_id": item_id,
        "popup_present_pred": None,
        "route_reason": (
            "visual_evidence_missing_or_unstable"
            if visual_called
            else "popup_scoped_structure_sufficient"
        ),
        "scored": False,
        "status": "abstain" if visual_called else "judged",
        "visual_called": visual_called,
    }


def visual_row(item_id: str) -> dict:
    return {
        "pilot_item_id": item_id,
        "human_gold_used": False,
        "scored": False,
        "paper_result_eligible": False,
        "status": "abstain",
        "model_config_sha256": "b" * 64,
        "protocol_sha256": "c" * 64,
        "visual_bank_sha256": "d" * 64,
    }


class FreezeOperatingPointsCliTest(unittest.TestCase):
    def fixture_rows(self) -> tuple[list[dict], list[dict], list[dict]]:
        items = [
            feature_row("PMJ-PILOT-001", gap_reason="contradictory"),
            feature_row("PMJ-PILOT-002", gap_reason="stale"),
            feature_row("PMJ-PILOT-003", missing=True),
            feature_row("PMJ-PILOT-004", gap_reason="visual_only_text"),
            feature_row("PMJ-PILOT-005", ambiguous=True),
            feature_row("PMJ-PILOT-006", gap_reason="merged"),
            feature_row("PMJ-PILOT-007", gap_reason="non_actionable"),
            feature_row("PMJ-PILOT-008"),
        ]
        methods = [
            method_row(
                row["identity"]["pilot_item_id"],
                visual_called=index < 7,
            )
            for index, row in enumerate(items)
        ]
        visuals = [visual_row(row["identity"]["pilot_item_id"]) for row in items]
        return items, methods, visuals

    def run_cli(
        self,
        root: Path,
        *,
        items: list[dict] | None = None,
        methods: list[dict] | None = None,
        visuals: list[dict] | None = None,
        timestamp: str = TIMESTAMP,
        seed: int = 17,
        precreate_output: bool = False,
    ) -> tuple[subprocess.CompletedProcess[str], Path]:
        default_items, default_methods, default_visuals = self.fixture_rows()
        item_path = root / "items.jsonl"
        method_path = root / "methods.jsonl"
        visual_path = root / "visual.jsonl"
        output = root / "private" / "operating-points.private.json"
        write_jsonl(item_path, default_items if items is None else items)
        write_jsonl(method_path, default_methods if methods is None else methods)
        write_jsonl(visual_path, default_visuals if visuals is None else visuals)
        if precreate_output:
            output.parent.mkdir(parents=True)
            output.write_text("do not replace\n", encoding="utf-8")
        command = [
            sys.executable,
            str(SCRIPT),
            "--items",
            str(item_path),
            "--visual-bank",
            str(visual_path),
            "--method-results",
            str(method_path),
            "--seed",
            str(seed),
            "--freeze-timestamp",
            timestamp,
            "--output",
            str(output),
        ]
        return subprocess.run(command, capture_output=True, text=True, check=False), output

    def test_freezes_exact_operating_points_with_explicit_rankings_and_hashes(
        self,
    ) -> None:
        """Catch floor rounding, implicit ranking, unstable random selection,
        or missing hashes.
        """
        with tempfile.TemporaryDirectory() as directory:
            items, methods, visuals = self.fixture_rows()
            result, output = self.run_cli(
                Path(directory),
                items=items[:7],
                methods=methods[:7],
                visuals=visuals[:7],
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            ledger = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(ledger["contract_version"], "popup-operating-point-freeze-v1.0")
            self.assertEqual(ledger["policy_status"], "proposed_operating_point_policy")
            self.assertEqual(ledger["freeze_timestamp"], TIMESTAMP)
            self.assertIsNone(ledger["gold_release_id"])
            self.assertIs(ledger["human_gold_used"], False)
            self.assertIs(ledger["scored"], False)
            self.assertIs(ledger["paper_result_eligible"], False)
            self.assertEqual(ledger["seed"], 17)
            self.assertEqual(ledger["item_count"], 7)
            self.assertEqual(
                ledger["policy"]["mg_pu_ranking"],
                "gap_severity_score_desc_then_item_id_asc",
            )
            self.assertEqual(
                ledger["policy"]["seeded_random_ranking"],
                "sha256_seed_item_id_asc_then_item_id_asc",
            )
            self.assertEqual(
                ledger["operating_points"]["K25"]["k"],
                2,
            )
            self.assertEqual(ledger["operating_points"]["K50"]["k"], 4)
            self.assertEqual(ledger["operating_points"]["K100"]["k"], 7)
            self.assertEqual(
                ledger["operating_points"]["K25"]["mg_pu"]["selected_item_ids"],
                ["PMJ-PILOT-001", "PMJ-PILOT-002"],
            )
            self.assertEqual(
                ledger["operating_points"]["K50"]["mg_pu"]["selected_item_ids"],
                [
                    "PMJ-PILOT-001",
                    "PMJ-PILOT-002",
                    "PMJ-PILOT-003",
                    "PMJ-PILOT-004",
                ],
            )
            self.assertEqual(
                ledger["operating_points"]["K25"]["seeded_random"]["selected_item_ids"],
                ["PMJ-PILOT-003", "PMJ-PILOT-006"],
            )
            self.assertEqual(
                ledger["operating_points"]["K50"]["seeded_random"]["selected_item_ids"],
                [
                    "PMJ-PILOT-003",
                    "PMJ-PILOT-006",
                    "PMJ-PILOT-002",
                    "PMJ-PILOT-004",
                ],
            )
            self.assertEqual(
                ledger["operating_points"]["K50"]["selection_relationship"],
                {
                    "same_selected_item_set": False,
                    "overlap_count": 3,
                    "overlap_fraction_of_k": "0.750000",
                    "comparison_interpretation": "budget_matched_not_item_matched",
                },
            )
            self.assertEqual(
                ledger["operating_points"]["K100"]["selection_relationship"],
                {
                    "same_selected_item_set": True,
                    "overlap_count": 7,
                    "overlap_fraction_of_k": "1.000000",
                    "comparison_interpretation": "budget_and_item_matched",
                },
            )
            first_ranked = ledger["operating_points"]["K25"]["mg_pu"]["selected"][0]
            self.assertEqual(
                first_ranked,
                {
                    "gap_reasons": ["contradictory"],
                    "gap_severity_score": 4,
                    "item_id": "PMJ-PILOT-001",
                    "rank": 1,
                },
            )
            for key in (
                "item_identity_sha256",
                "input_bundle_sha256",
                "config_sha256",
                "implementation_sha256",
                "budget_ledger_sha256",
            ):
                self.assertRegex(ledger["hashes"][key], r"^[0-9a-f]{64}$")
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)

    def test_rejects_method_route_that_disagrees_with_derived_gap(self) -> None:
        """Catches silently ranking a different item set than the frozen MG-PU route."""
        with tempfile.TemporaryDirectory() as directory:
            items, methods, visuals = self.fixture_rows()
            methods[0]["visual_called"] = False
            methods[0]["route_reason"] = "popup_scoped_structure_sufficient"

            result, output = self.run_cli(
                Path(directory), items=items, methods=methods, visuals=visuals
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("disagrees with derived gap route", result.stderr)
            self.assertFalse(output.exists())

    def test_invisible_scoped_text_is_ranked_as_missing(self) -> None:
        """Catches divergence from the existing MG-PU route when scoped text is invisible."""
        with tempfile.TemporaryDirectory() as directory:
            items, methods, visuals = self.fixture_rows()
            items[7]["candidates"][0]["normalized"]["visible"] = False
            methods[7] = method_row("PMJ-PILOT-008", visual_called=True)

            result, output = self.run_cli(
                Path(directory), items=items, methods=methods, visuals=visuals
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            ledger = json.loads(output.read_text(encoding="utf-8"))
            ranked = ledger["operating_points"]["K100"]["mg_pu"]["selected"]
            item = next(row for row in ranked if row["item_id"] == "PMJ-PILOT-008")
            self.assertEqual(item["gap_reasons"], ["missing"])
            self.assertEqual(item["gap_severity_score"], 3)

    def test_missing_structured_representation_opens_the_gap(self) -> None:
        """Catches divergence from MG-PU when a scoped message sits in a missing representation."""
        with tempfile.TemporaryDirectory() as directory:
            items, methods, visuals = self.fixture_rows()
            representation = items[7]["observations"][0]["structured_representation"]
            representation["availability"] = "missing"
            representation["node_count"] = 0
            methods[7] = method_row("PMJ-PILOT-008", visual_called=True)

            result, output = self.run_cli(
                Path(directory), items=items, methods=methods, visuals=visuals
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            ledger = json.loads(output.read_text(encoding="utf-8"))
            ranked = ledger["operating_points"]["K100"]["mg_pu"]["selected"]
            item = next(row for row in ranked if row["item_id"] == "PMJ-PILOT-008")
            self.assertEqual(item["gap_reasons"], ["missing"])
            self.assertEqual(item["gap_severity_score"], 3)

    def test_rejects_any_human_label_shaped_input(self) -> None:
        """Catches accidental gold or adjudication consumption before the freeze."""
        with tempfile.TemporaryDirectory() as directory:
            items, methods, visuals = self.fixture_rows()
            visuals[0]["presence_label_final"] = "popup"

            result, output = self.run_cli(
                Path(directory), items=items, methods=methods, visuals=visuals
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("forbidden label/gold/metric key", result.stderr)
            self.assertFalse(output.exists())

    def test_rejects_item_coverage_mismatch(self) -> None:
        """Catches hashing partial visual or method inputs as a complete operating-point freeze."""
        with tempfile.TemporaryDirectory() as directory:
            items, methods, visuals = self.fixture_rows()

            result, output = self.run_cli(
                Path(directory), items=items, methods=methods[:-1], visuals=visuals
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("method-results item coverage mismatch", result.stderr)
            self.assertFalse(output.exists())

    def test_rejects_non_utc_timestamp(self) -> None:
        """Catches ambiguous local-time commitments that cannot order freeze and gold release."""
        with tempfile.TemporaryDirectory() as directory:
            result, output = self.run_cli(
                Path(directory), timestamp="2026-09-01 09:30:00"
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("freeze timestamp must be canonical UTC", result.stderr)
            self.assertFalse(output.exists())

    def test_refuses_to_replace_an_existing_frozen_ledger(self) -> None:
        """Catches silent post-freeze replacement of a selected-ID commitment."""
        with tempfile.TemporaryDirectory() as directory:
            result, output = self.run_cli(Path(directory), precreate_output=True)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("output already exists", result.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), "do not replace\n")


if __name__ == "__main__":
    unittest.main()
