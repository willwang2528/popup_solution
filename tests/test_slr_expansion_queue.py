import json
import unittest
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data-collection" / "slr-expansion" / "sources.jsonl"


class SlrExpansionQueueContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.records = [
            json.loads(line)
            for line in QUEUE.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.by_id = {record["source_id"]: record for record in self.records}

    def test_required_chi2026_expansion_sources_are_queued(self) -> None:
        self.assertEqual(
            set(self.by_id),
            {
                "chi2026_mobile_screen_reader_mixed_methods",
                "a11yscan_2025",
                "timestump_2025",
            },
        )

    def test_queue_is_fail_closed_against_the_frozen_union(self) -> None:
        for record in self.records:
            self.assertEqual(record["union_status"], "candidate_not_in_frozen_union")
            self.assertFalse(record["included_in_255_field_contract"])
            self.assertIn(record["source_role"], {"slr_index", "direct_field_source"})
            self.assertGreaterEqual(len(record["evidence_locators"]), 1)

        self.assertEqual(self.by_id["chi2026_mobile_screen_reader_mixed_methods"]["source_role"], "slr_index")
        self.assertEqual(self.by_id["chi2026_mobile_screen_reader_mixed_methods"]["field_candidates"], [])

        for source_id in ("a11yscan_2025", "timestump_2025"):
            self.assertEqual(self.by_id[source_id]["source_role"], "direct_field_source")
            self.assertGreater(len(self.by_id[source_id]["field_candidates"]), 0)

    def test_public_sources_and_field_candidates_are_auditable(self) -> None:
        allowed_channels = {"structure", "visual", "context", "temporal", "taxonomy"}
        for record in self.records:
            for source in record["public_sources"]:
                parsed = urlparse(source["url"])
                self.assertEqual(parsed.scheme, "https")
                self.assertTrue(parsed.netloc)
                self.assertIn(
                    source["kind"],
                    {
                        "publisher",
                        "official_repository",
                        "official_project",
                        "author_manuscript",
                    },
                )

            for field in record["field_candidates"]:
                self.assertIn(field["channel"], allowed_channels)
                self.assertTrue(field["normalized_field"])
                self.assertTrue(field["evidence_locator"])
                self.assertIn(
                    field["v1_relevance"],
                    {"direct", "supporting", "advanced_only"},
                )
                self.assertEqual(field["evidence_status"], "full_text_candidate")


if __name__ == "__main__":
    unittest.main()
