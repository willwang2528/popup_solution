# Source Ledger

> Updated: 2026-09-01
>
> Rule: raw third-party screenshots remain in local source caches or are re-fetched through adapters. This repository publishes provenance, checksums, candidate IDs and annotations only when permitted; it does not silently relicense source images.

## PopSweeper basic archive

- Official record: <https://doi.org/10.5281/zenodo.13754620>
- Record page: <https://zenodo.org/records/13754620>
- Associated paper: <https://arxiv.org/abs/2412.02933>
- Archive: `app-blocking pop-ups_basic.zip`
- License recorded by Zenodo: `CC-BY-4.0`
- Expected and observed bytes: `266010362`
- Expected and observed MD5: `46a0fe5c4eeab2bd119aed800b7a81f3`
- Observed SHA-256: `90b7c5cfe3e78bfd8e19b0fda0884cd1f6b03086cb31c91d57eaadbe4d1b942c`
- Safety audit: [`../dataset-v1/work/popsweeper_source_audit.json`](../dataset-v1/work/popsweeper_source_audit.json), status `pass`

The ZIP contains 2,105 real JPG members under `basic/{train,valid,test}/{ads,no_ads}` after excluding AppleDouble `__MACOSX/._*` entries:

| Split | `ads` | `no_ads` | Total |
|---|---:|---:|---:|
| train | 500 | 765 | 1265 |
| valid | 164 | 255 | 419 |
| test | 167 | 254 | 421 |
| total | 831 | 1274 | 2105 |

This differs from the paper's reported 832 popup and 1,275 non-popup originals by one item in each class. The archive has no CSV/JSON/XML label manifest, popup message labels or UI tree. `ads/no_ads` is only a folder-level popup-presence label.

Filename interpretation is explicitly inferential:

- 1,956 numeric basenames align with the paper's RICO-source counts and are treated only as candidate RICO screenshot IDs until joined;
- 149 named basenames align with recorded popular-app frames and are not RICO-joinable from this source;
- the ZIP itself provides no provenance mapping table.

CRC32 plus uncompressed byte size yielded 33 extra exact-content copies. A subsequent source-group gate removed 64 further records sharing a numeric RICO candidate ID or named recording group. The upstream split is therefore retained as an audit stratum, not accepted as the final leakage-safe benchmark split.

## RICO semantic annotations

- Official source and data description: <https://www.interactionmining.org/archive/rico>
- Official copyright notice: <https://www.interactionmining.org/legal/copyright>
- Download used: `semantic_annotations.zip` from the official RICO Google Cloud bucket
- Observed bytes: `157800634`
- Observed MD5: `5dd3372e2d99b342958136e394d4de79`
- Observed SHA-256: `c5c11d750cb9505e45a0ee57f2bb6186d6448f005bd8731615181310aeea0d70`
- Safety audit: [`../dataset-v1/work/rico_semantic_source_audit.json`](../dataset-v1/work/rico_semantic_source_audit.json), status `pass`
- Inventory: 66,261 `semantic_annotations/<id>.json` and 66,261 paired PNG files

Join result after PopSweeper content/group deduplication:

- 1,923/1,923 numeric candidates have both RICO semantic JSON and PNG;
- all 90 numeric records in the frozen N=120 audit sample join successfully;
- the 30 named recorded-app frames are correctly marked `not_applicable`.

The semantic JSON is a limited structural representation. An inspected joined item exposed `ancestors`, `bounds`, `children`, `class`, `clickable` and `componentLabel`, but not message `text`, `content-desc` or an actual TalkBack accessibility tree. It supports ID/provenance and structure joinability, not v1 popup-message gold or a complete structure-only message baseline.

RICO's official notice states that screenshots may contain copyrighted work. Consequently, the frozen candidate manifest records RICO member paths and IDs but does not redistribute RICO screenshots or semantic PNGs.

## Frozen N=120 audit candidate manifest

- Manifest: [`../dataset-v1/candidates/popsweeper_candidates_n120.jsonl`](../dataset-v1/candidates/popsweeper_candidates_n120.jsonl)
- Summary: [`../dataset-v1/candidates/popsweeper_candidates_n120.summary.json`](../dataset-v1/candidates/popsweeper_candidates_n120.summary.json)
- Seed: `20260901`
- Allocation: train/valid/test = 72/24/24; popup/no-popup = 60/60; within each label, numeric/named = 45/15
- Leakage controls before sampling: exact content key and source group uniqueness
- Published raw-media policy: `adapter_only_not_redistributed`
- Message annotation: `pending`
- Eligible for VPMA/message metrics: `false`

This is a real-source candidate manifest, not yet an empirical popup-message dataset item collection. It becomes eligible only after the screenshot evidence is lawfully accessible, message gold and critical facts are independently annotated, and the union item contract passes the v1 QA gates.
