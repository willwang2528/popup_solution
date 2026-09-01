from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "CLAIM_BOUNDARY_V1.json"
IDEA_REPORT_PATH = ROOT / "idea-stage" / "IDEA_REPORT.md"
CONTRACT_PATH = ROOT / "idea-stage" / "docs" / "research_contract.md"
STATUS_PATH = ROOT / "dataset-v1" / "android-capture" / "PUBLIC_FEASIBILITY_STATUS.json"


class ResearchClaimBoundaryTest(unittest.TestCase):
    def load_policy(self) -> dict:
        self.assertTrue(POLICY_PATH.is_file(), "machine-readable claim boundary is required")
        return json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    def test_v1_is_message_judgment_and_not_universal_recovery(self):
        policy = self.load_policy()
        self.assertEqual(policy["task_profile"], "popup_message_judgment_v1")
        self.assertEqual(policy["primary_scope"], ["popup_presence", "visible_message"])
        self.assertFalse(policy["claims"]["universal_popup_solution"])
        self.assertFalse(policy["claims"]["dismissal_or_recovery"])
        self.assertFalse(policy["claims"]["user_experience_improved"])

    def test_observability_ceiling_requires_abstention_without_any_evidence(self):
        policy = self.load_policy()
        ceiling = policy["observability_ceiling"]
        self.assertEqual(ceiling["tree_absent_or_incomplete"], "tree_only_cannot_recover_missing_facts")
        self.assertEqual(ceiling["visible_pixels_available"], "visual_message_fallback_allowed")
        self.assertEqual(ceiling["no_authorized_channel_exposes_fact"], "must_abstain")

    def test_first_and_superiority_claims_remain_unestablished(self):
        policy = self.load_policy()
        self.assertEqual(policy["claims"]["first_problem_formulation"], "contradicted_by_prior_work")
        self.assertEqual(policy["claims"]["first_exact_benchmark"], "provisional_not_established")
        self.assertEqual(policy["claims"]["method_superiority"], "not_tested")

    def test_machine_state_and_human_documents_agree(self):
        policy = self.load_policy()
        status = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(status["real_capture_count"], policy["evidence_counts"]["real_android_captures"])
        self.assertEqual(status["human_gold_count"], policy["evidence_counts"]["human_gold"])
        self.assertFalse(status["paper_result_eligible"])

        idea_report = IDEA_REPORT_PATH.read_text(encoding="utf-8")
        contract = CONTRACT_PATH.read_text(encoding="utf-8")
        for phrase in (
            "若结构、像素和其他获授权观察均未提供该事实",
            "第一个提出弹窗问题",
            "正式 Android capture 为 0",
        ):
            self.assertIn(phrase, idea_report)
        self.assertIn("系统必须 `abstain`", contract)
        self.assertIn("real capture=0；human gold=0；paper result=0", contract)


if __name__ == "__main__":
    unittest.main()
