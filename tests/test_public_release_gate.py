from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PublicReleaseGateTests(unittest.TestCase):
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
