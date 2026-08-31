# Experiment Tracker：PMAB + MG-PU

> Updated：2026-09-01 00:13 +08:00
>
> Status vocabulary：`DONE` / `RUNNING` / `TODO` / `BLOCKED_EXTERNAL` / `INVALID`
>
> V1 invariant：所有 run 都是 `no_action`。

| Run ID | Milestone | Purpose | System / Variant | Split / Source | Metrics / Gate | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| SRC-001 | M0 | source metadata | Zenodo record 13754620 | PopSweeper | access/license/file/checksum metadata | MUST | DONE | open, CC-BY-4.0, 266010362 bytes, MD5 46a0fe... |
| SRC-002 | M0 | download archive | curl resumable | PopSweeper basic | byte size | MUST | RUNNING | local transient cache; do not claim complete before terminal exit |
| SRC-003 | M0 | checksum | md5 | downloaded archive | exact MD5 match | MUST | TODO | depends SRC-002 |
| SRC-004 | M0 | archive safety/inventory | zipinfo + traversal scan | archive | unsafe members=0; file counts | MUST | TODO | extract only after scan |
| SRC-005 | M0 | label schema audit | deterministic parser | archive | image/label alignment ≥98% sample | MUST | TODO | no assumptions about folder names |
| SRC-006 | M0 | source-ID join | PopSweeper ↔ RICO | positive candidates | joinable positives ≥60 | MUST | TODO | determines whether RICO hierarchy download is justified |
| SRC-007 | M0 | RICO license adapter | source IDs + downloader | RICO | terms and attribution complete | MUST | TODO | do not blindly redistribute RICO screenshots |
| DAT-001 | M1 | candidate sampling | source-first sampler | Android pilot | N=120 candidate manifest | MUST | TODO | freeze before method prediction |
| ANN-001 | M1 | annotation pilot round 1 | 2 annotators | 30 items | κ/F1/semantic gates | MUST | TODO | gold locked from methods |
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
