# Experiment Tracker：PMAB + MG-PU

> Updated：2026-09-01 00:57 +08:00
>
> Status vocabulary：`DONE` / `RUNNING` / `TODO` / `BLOCKED_EXTERNAL` / `INVALID`
>
> V1 invariant：所有 run 都是 `no_action`。

| Run ID | Milestone | Purpose | System / Variant | Split / Source | Metrics / Gate | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| SRC-001 | M0 | source metadata | Zenodo record 13754620 | PopSweeper | access/license/file/checksum metadata | MUST | DONE | open, CC-BY-4.0, 266010362 bytes, MD5 46a0fe... |
| SRC-002 | M0 | download archive | curl resumable | PopSweeper basic | byte size | MUST | DONE | 266010362 bytes; terminal exit 0; local transient cache |
| SRC-003 | M0 | checksum | md5 | downloaded archive | exact MD5 match | MUST | DONE | 46a0fe5c4eeab2bd119aed800b7a81f3 |
| SRC-004 | M0 | archive safety/inventory | tested ZIP auditor | archive | unsafe members=0; file counts | MUST | DONE | 4109 members; no traversal/symlink; 2105 real JPG after AppleDouble exclusion |
| SRC-005 | M0 | label schema audit | deterministic parser | archive | every real image has folder label | MUST | DONE | 831 ads + 1274 no_ads; no message labels/tree; paper/archive differ by 2 originals |
| SRC-006 | M0 | source-ID join | PopSweeper ↔ RICO semantic | deduplicated numeric candidates | joinable positives ≥60 | MUST | DONE | 1923/1923 numeric candidates and 90/90 sampled numeric records have JSON+PNG pairs |
| SRC-007 | M0 | RICO license adapter | source IDs + ledger | RICO | terms and attribution complete | MUST | DONE | adapter-only; no screenshot redistribution; see sources/SOURCE_LEDGER.md |
| SRC-008 | M0 | RICO semantic archive audit | tested ZIP auditor | official 150 MB source | paired JSON/PNG + safety | MUST | DONE | 66261 pairs; semantic JSON lacks message text/content-desc |
| DAT-001 | M1 | candidate sampling | source-first sampler | Android source pilot | N=120 candidate manifest | MUST | DONE | 72/24/24 audit strata; 60/60 labels; content/group dedup; message gold pending |
| DAT-002 | M1 | source item materialization | union item builder | N=120 candidates | schema-valid empirical observations | MUST | TODO | requires lawful screenshot access + message annotation; current candidate manifest is not metric-eligible |
| ANN-001 | M1 | annotation pilot round 1 | 2 annotators | 30 of frozen 120 | κ/F1/semantic gates | MUST | TODO | next gate; gold locked from methods |
| ANN-002 | M1 | adjudication | third reviewer | disputed items | final gold + ambiguity | MUST | TODO | depends ANN-001 |
| ANN-003 | M1 | protocol repair | guide revision | 30 new/re-labeled | gates | MUST | TODO | run only if ANN-001 fails |
| BASE-001 | M2 | majority sanity | no-input | dev | presence/VPMA | MUST | TODO | class imbalance |
| BASE-002 | M2 | structure-only | flattened hierarchy | dev/test | VPMA, coverage, cost | MUST | TODO | deployable |
| BASE-003 | M2 | text-rule baseline | Appium-style rules | dev/test | VPMA, facts | MUST | TODO | deployable |
| BASE-004 | M2 | OCR-only | popup/full screenshot | dev/test | VPMA, OCR coverage | MUST | BLOCKED_EXTERNAL | OCR runtime absent |
| BASE-005 | M2 | PopSweeper + OCR | detector + ROI OCR | dev/test | presence + message | MUST | TODO | source code/model availability audit first |
| BASE-006 | M2 | screenshot-only VLM | frozen VLM | dev/test | VPMA, hallucination, cost | MUST | BLOCKED_EXTERNAL | model/API not frozen |
| FUSE-001 | M3 | always-on fusion | same backbone | dev/test | VPMA, cost | MUST | TODO | strong comparison |
| FUSE-002 | M3 | fixed cascade | WhisperTest-style perception | dev/test | VPMA, calls | SHOULD | TODO | no Voice Control/action |
| MGPU-001 | M3 | full method | MG-PU | dev | VPMA, coverage, calls | MUST | TODO | threshold tuning only on dev |
| MGPU-002 | M4 | frozen main run | MG-PU | test | pre-registered primary comparison | MUST | TODO | test once |
| ABL-001 | M4 | empty-tree gate | MG-PU ablation | test | VPMA/calls | MUST | TODO | tests naive gate |
| ABL-002 | M4 | random matched calls | MG-PU ablation | test | VPMA/calls | MUST | TODO | equal visual rate |
| ABL-003 | M4 | shuffled gap reasons | MG-PU ablation | test | VPMA | MUST | TODO | novelty isolation |
| ABL-004 | M4 | no critical guard | MG-PU ablation | test | hallucination | MUST | TODO | safety/quality |
| GEN-001 | M5 | held-out apps | best systems | Android holdout | group metrics | SHOULD | TODO | after main result |
| GEN-002 | M5 | iOS capability | collector only | iOS | field availability | MUST | BLOCKED_EXTERNAL | no device/simctl |
| GEN-003 | M5 | iOS evaluation | best systems | iOS test | VPMA breakdown | SHOULD | BLOCKED_EXTERNAL | depends GEN-002 |
| QA-001 | M6 | dataset validator | schema + QA | release | 0 critical errors | MUST | TODO | empirical items only |
| QA-002 | M6 | license/privacy audit | source ledger | release | all items releasable/adapter-only | MUST | TODO | human gate |
| QA-003 | M6 | reproduction | clean checkout | release | commands reproduce tables | MUST | TODO | no hidden cache |
| PUB-001 | M6 | public release | GitHub + DOI candidate | release | remote SHA/readback | MUST | TODO | only after QA gates |
