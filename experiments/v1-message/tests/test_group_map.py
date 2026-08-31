from __future__ import annotations

import importlib
import importlib.util
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


class PilotGroupMapTests(unittest.TestCase):
    def test_group_map_uses_connected_components_and_keeps_keys_private(self):
        # Break caught: near-duplicate links are split or raw group/content keys are published.
        self.assertIsNotNone(importlib.util.find_spec("popup_eval.group_map"))
        module = importlib.import_module("popup_eval.group_map")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "manifest.jsonl"
            private_output = root / "private" / "group-map.private.jsonl"
            public_summary = root / "PUBLIC_GROUP_MAP_SUMMARY.json"
            write_jsonl(
                manifest,
                [
                    {"pilot_item_id": "PMJ-PILOT-001", "group_key": "source:a", "content_key": "content:x"},
                    {"pilot_item_id": "PMJ-PILOT-002", "group_key": "source:a", "content_key": "content:y"},
                    {"pilot_item_id": "PMJ-PILOT-003", "group_key": "source:b", "content_key": "content:y"},
                    {"pilot_item_id": "PMJ-PILOT-004", "group_key": "source:c", "content_key": "content:z"},
                ],
            )

            result = module.main(
                [
                    "--manifest",
                    str(manifest),
                    "--private-output",
                    str(private_output),
                    "--public-summary",
                    str(public_summary),
                    "--expected-count",
                    "4",
                ]
            )

            self.assertEqual(result, 0)
            rows = [json.loads(line) for line in private_output.read_text().splitlines()]
            clusters = {row["pilot_item_id"]: row["cluster_id"] for row in rows}
            self.assertEqual(clusters["PMJ-PILOT-001"], clusters["PMJ-PILOT-002"])
            self.assertEqual(clusters["PMJ-PILOT-002"], clusters["PMJ-PILOT-003"])
            self.assertNotEqual(clusters["PMJ-PILOT-003"], clusters["PMJ-PILOT-004"])
            self.assertEqual(stat.S_IMODE(private_output.parent.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(private_output.stat().st_mode), 0o600)
            summary_text = public_summary.read_text(encoding="utf-8")
            summary = json.loads(summary_text)
            self.assertEqual(summary["counts"]["items"], 4)
            self.assertEqual(summary["counts"]["clusters"], 2)
            self.assertEqual(summary["counts"]["largest_cluster_items"], 3)
            self.assertNotIn("source:a", summary_text)
            self.assertNotIn("content:y", summary_text)
            self.assertFalse(summary["negative_claims"]["formal_leakage_control_sufficient"])
            self.assertFalse(summary["negative_claims"]["paper_result_eligible"])


if __name__ == "__main__":
    unittest.main()
