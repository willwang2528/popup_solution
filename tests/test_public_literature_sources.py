import json
import csv
import unittest
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]


class PublicLiteratureSourceContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.records = [
            json.loads(line)
            for line in (ROOT / "data-collection" / "papers.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]

    def test_every_record_has_a_public_primary_source(self) -> None:
        missing = []
        invalid = []
        allowed_kinds = {
            "publisher",
            "official_repository",
            "official_project",
            "author_manuscript",
            "preprint",
            "dataset",
        }

        for record in self.records:
            sources = record.get("public_sources", [])
            if not sources:
                missing.append(record["paper_id"])
                continue
            for source in sources:
                parsed = urlparse(source.get("url", ""))
                if (
                    source.get("kind") not in allowed_kinds
                    or parsed.scheme != "https"
                    or not parsed.netloc
                    or source.get("evidence_scope")
                    not in {"identity", "abstract", "full_text", "artifact"}
                ):
                    invalid.append(record["paper_id"])

        self.assertEqual(missing, [], f"missing public sources: {missing}")
        self.assertEqual(invalid, [], f"invalid public sources: {invalid}")

    def test_public_source_summary_covers_all_records(self) -> None:
        summary = json.loads(
            (ROOT / "data-collection" / "COLLECTION_SUMMARY.json").read_text(
                encoding="utf-8"
            )
        )
        coverage = summary.get("public_source_coverage")
        self.assertIsNotNone(coverage, "public_source_coverage is missing")
        self.assertEqual(coverage["paper_count"], 14)
        self.assertEqual(coverage["papers_with_source"], 14)
        self.assertEqual(coverage["papers_without_source"], 0)

    def test_csv_exposes_the_same_primary_source(self) -> None:
        with (ROOT / "data-collection" / "papers.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            csv_rows = {row["paper_id"]: row for row in csv.DictReader(handle)}

        self.assertEqual(set(csv_rows), {record["paper_id"] for record in self.records})
        for record in self.records:
            primary_url = csv_rows[record["paper_id"]].get("primary_source_url")
            self.assertTrue(primary_url, f"missing CSV source: {record['paper_id']}")
            self.assertEqual(
                primary_url,
                record.get("public_sources", [{}])[0].get("url"),
            )


if __name__ == "__main__":
    unittest.main()
