#!/usr/bin/env python3
"""Attach public primary-source identities to the frozen 14-paper collection."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


SOURCES = {
    "whispertest_2025": {
        "persistent_ids": {"doi": "10.1145/3719027.3765183"},
        "public_sources": [
            {
                "kind": "publisher",
                "url": "https://doi.org/10.1145/3719027.3765183",
                "evidence_scope": "identity",
                "supports": "Peer-reviewed paper identity and ACM CCS 2025 publication record.",
            },
            {
                "kind": "author_manuscript",
                "url": "https://gunesacar.net/assets/whisper-test-ios-automation-ccs-25.pdf",
                "evidence_scope": "full_text",
                "supports": "Public author manuscript for method and experiment re-audit.",
            },
            {
                "kind": "official_project",
                "url": "https://github.com/iOSWhisperTest/whispertest",
                "evidence_scope": "artifact",
                "supports": "Official implementation repository linked to the paper.",
            },
        ],
    },
    "abandon_all_hope_2024": {
        "public_sources": [
            {
                "kind": "publisher",
                "url": "https://www.usenix.org/conference/usenixsecurity24/presentation/arkalakis",
                "evidence_scope": "abstract",
                "supports": "USENIX publication record, abstract, BibTeX, and official paper link.",
            },
            {
                "kind": "publisher",
                "url": "https://www.usenix.org/system/files/usenixsecurity24-arkalakis.pdf",
                "evidence_scope": "full_text",
                "supports": "Official open-access USENIX paper.",
            },
        ],
    },
    "the_ok_is_not_enough_2023": {
        "public_sources": [
            {
                "kind": "publisher",
                "url": "https://www.usenix.org/conference/usenixsecurity23/presentation/koch",
                "evidence_scope": "abstract",
                "supports": "USENIX publication record, abstract, BibTeX, and official paper link.",
            },
            {
                "kind": "publisher",
                "url": "https://www.usenix.org/system/files/usenixsecurity23-koch.pdf",
                "evidence_scope": "full_text",
                "supports": "Official open-access USENIX paper.",
            },
        ],
    },
    "freely_given_consent_2022": {
        "persistent_ids": {"doi": "10.1145/3548606.3560564"},
        "public_sources": [
            {
                "kind": "publisher",
                "url": "https://doi.org/10.1145/3548606.3560564",
                "evidence_scope": "identity",
                "supports": "ACM CCS 2022 publication identity.",
            },
            {
                "kind": "author_manuscript",
                "url": "https://publications.cispa.saarland/3754/2/221015_GDPR_Consent_CCS22.pdf",
                "evidence_scope": "full_text",
                "supports": "Public institutional author manuscript for method re-audit.",
            },
        ],
    },
    "vlm_fuzz_2026": {
        "persistent_ids": {
            "doi": "10.1007/s10664-026-10816-4",
            "arxiv": "2504.11675",
        },
        "public_sources": [
            {
                "kind": "publisher",
                "url": "https://link.springer.com/article/10.1007/s10664-026-10816-4",
                "evidence_scope": "full_text",
                "supports": "Peer-reviewed Empirical Software Engineering article.",
            },
            {
                "kind": "preprint",
                "url": "https://arxiv.org/abs/2504.11675",
                "evidence_scope": "full_text",
                "supports": "Public versioned preprint and paper metadata.",
            },
            {
                "kind": "official_project",
                "url": "https://github.com/biniamf/VLM-Fuzz",
                "evidence_scope": "artifact",
                "supports": "Official implementation repository cited by the paper record.",
            },
        ],
    },
    "tcf_aaid_2026": {
        "persistent_ids": {"arxiv": "2602.20222"},
        "public_sources": [
            {
                "kind": "preprint",
                "url": "https://arxiv.org/abs/2602.20222",
                "evidence_scope": "full_text",
                "supports": "Versioned public preprint for method and result re-audit.",
            }
        ],
    },
    "cookieverse_bannerclick": {
        "persistent_ids": {"arxiv": "2302.05353"},
        "public_sources": [
            {
                "kind": "preprint",
                "url": "https://arxiv.org/abs/2302.05353",
                "evidence_scope": "full_text",
                "supports": "Versioned public preprint describing BannerClick and its evaluation.",
            }
        ],
    },
    "ssldetecter_2019": {
        "persistent_ids": {"doi": "10.1155/2019/7193684"},
        "public_sources": [
            {
                "kind": "publisher",
                "url": "https://onlinelibrary.wiley.com/doi/10.1155/2019/7193684",
                "evidence_scope": "full_text",
                "supports": "Publisher full text and stable DOI record.",
            }
        ],
    },
    "poker_sneaky_popups": {
        "persistent_ids": {"arxiv": "2505.12056"},
        "public_sources": [
            {
                "kind": "preprint",
                "url": "https://arxiv.org/abs/2505.12056",
                "evidence_scope": "full_text",
                "supports": "Versioned public preprint describing Poker and popup-pattern analysis.",
            }
        ],
    },
    "popsweeper_2024": {
        "persistent_ids": {
            "arxiv": "2412.02933",
            "zenodo": "10.5281/zenodo.13754620",
        },
        "public_sources": [
            {
                "kind": "preprint",
                "url": "https://arxiv.org/abs/2412.02933",
                "evidence_scope": "full_text",
                "supports": "Versioned public preprint for architecture and reported metrics.",
            },
            {
                "kind": "dataset",
                "url": "https://zenodo.org/records/13754620",
                "evidence_scope": "artifact",
                "supports": "Official public dataset record, archive metadata, checksum, and DOI.",
            },
        ],
    },
    "dynamic_ios_privacy_2021": {
        "persistent_ids": {
            "doi": "10.34726/hss.2021.92880",
            "handle": "20.500.12708/19197",
        },
        "public_sources": [
            {
                "kind": "official_repository",
                "url": "https://repositum.tuwien.at/handle/20.500.12708/19197",
                "evidence_scope": "full_text",
                "supports": "TU Wien repository record and public thesis full text.",
            }
        ],
    },
    "hotmobile_ad_policy_2018": {
        "persistent_ids": {"doi": "10.1145/3177102.3177113"},
        "public_sources": [
            {
                "kind": "publisher",
                "url": "https://doi.org/10.1145/3177102.3177113",
                "evidence_scope": "identity",
                "supports": "ACM HotMobile 2018 publication identity.",
            },
            {
                "kind": "author_manuscript",
                "url": "https://lilicoding.github.io/papers/dong2018mobile.pdf",
                "evidence_scope": "full_text",
                "supports": "Public author manuscript for method re-audit.",
            },
        ],
    },
    "ios_applications_testing_2018": {
        "persistent_ids": {"doi": "10.22364/bjmc.2018.6.1.05"},
        "public_sources": [
            {
                "kind": "publisher",
                "url": "https://www.bjmc.lu.lv/en/contents/vol-62018-no-1/",
                "evidence_scope": "identity",
                "supports": "Official journal issue and paper identity.",
            },
            {
                "kind": "publisher",
                "url": "https://www.bjmc.lu.lv/fileadmin/user_upload/lu_portal/projekti/bjmc/Contents/6_1_05_Kulesovs.pdf",
                "evidence_scope": "full_text",
                "supports": "Official journal-hosted full text.",
            },
        ],
    },
    "dios_2014": {
        "persistent_ids": {"handle": "opus4-fau:4755"},
        "public_sources": [
            {
                "kind": "official_project",
                "url": "https://www.cs1.tf.fau.de/research/forensic-computing-group/dios/",
                "evidence_scope": "abstract",
                "supports": "Official FAU project page with report and source-code links.",
            },
            {
                "kind": "official_repository",
                "url": "https://opus4.kobv.de/opus4-fau/frontdoor/index/index/docId/4755",
                "evidence_scope": "full_text",
                "supports": "Official FAU repository record for the technical report.",
            },
        ],
    },
}


def main() -> None:
    jsonl_path = ROOT / "papers.jsonl"
    records = [
        json.loads(line)
        for line in jsonl_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    record_ids = {record["paper_id"] for record in records}
    if record_ids != set(SOURCES):
        raise SystemExit(
            f"source map mismatch: missing={sorted(record_ids - set(SOURCES))}, "
            f"extra={sorted(set(SOURCES) - record_ids)}"
        )

    for record in records:
        source = SOURCES[record["paper_id"]]
        record.pop("persistent_ids", None)
        if "persistent_ids" in source:
            record["persistent_ids"] = source["persistent_ids"]
        record["public_sources"] = source["public_sources"]

    jsonl_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )

    csv_path = ROOT / "papers.csv"
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if "primary_source_url" not in fieldnames:
        fieldnames.append("primary_source_url")
    source_by_id = {
        record["paper_id"]: record["public_sources"][0]["url"] for record in records
    }
    for row in rows:
        row["primary_source_url"] = source_by_id[row["paper_id"]]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
