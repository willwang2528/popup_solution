# Experiment Tracker：PMAB + MG-PU

> Updated：2026-09-01 03:45 +08:00
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
| SRC-008 | M0 | RICO semantic archive audit | tested ZIP auditor | official 150 MB source | paired JSON/PNG + safety | MUST | DONE | 66261 pairs; schema contains some `text` but no human popup-message gold or complete accessibility `content-desc` |
| DAT-001 | M1 | candidate sampling | source-first sampler | Android source pilot | N=120 candidate manifest | MUST | DONE | 72/24/24 audit strata; source directory 60 `ads`/60 `no_ads`; not human gold; content/group dedup |
| INFRA-ANN | M1 | annotation protocol + media | blind A/B + adjudication + fail-closed adapter | fixed 30-item pilot | 30 screenshots + 44 RICO artifacts; 33 tests | MUST | DONE | local media Git ignored; no human gold; pilot SHA b44f475... |
| INFRA-MODEL | M1 | model-only protocol QA | independent model A/B | fixed 30-item pilot | 30+30 preannotations | SHOULD | DONE | 29/30 descriptive presence concordance; non-human, metric-ineligible, never shown to human annotators |
| INFRA-EVAL | M2 | evaluation implementation | 7 action-free methods/ablations | synthetic fixtures | 26 tests + 7 smoke runs | MUST | DONE | all smoke outputs paper_result_eligible=false; fake/source/model gold fails closed |
| INFRA-OCR | M2 | local OCR adapter | macOS Vision, full-screen OCR | fixed 30-item pilot | 7/7 authorized Vision tests; 30 private outputs | SHOULD | DONE | 30/30 text observed but all presence abstain; public aggregate only; derived text withheld pending privacy review |
| INFRA-FEATURE | M2 | pre-gold feature freeze | ID-only adapter + RICO semantic | fixed 30-item pilot | 22 available / 8 missing / 186 nodes; 3 tests | MUST | DONE | source labels/paths ignored; private bundle Git ignored, 0600 under 0700 directory; public aggregate only |
| INFRA-PREGOLD | M2 | pre-gold prediction freeze | structure-only + MG-PU candidate | fixed 30-item pilot | 9 tests; predictions persisted before human gold | MUST | DONE | no metrics; structure 15 judged/15 abstain; MG-PU 2 structured/28 visual; Model-B visual evidence is not a formal reproducible baseline |
| DAT-002 | M1 | source item materialization | union item builder | N=120 candidates | schema-valid empirical observations | MUST | TODO | lawful local screenshot access is ready; human message annotation and union-item materialization remain |
| ANN-001 | M1 | annotation pilot round 1 | 2 human annotators | 30 of frozen 120 | κ/F1/semantic gates | MUST | TODO | protocol/media ready; real A/B human labels not started; model preannotations cannot substitute |
| ANN-002 | M1 | adjudication | third reviewer | disputed items | final gold + ambiguity | MUST | TODO | depends ANN-001 |
| ANN-003 | M1 | protocol repair | guide revision | 30 new/re-labeled | gates | MUST | TODO | run only if ANN-001 fails |
| BASE-001 | M2 | majority sanity | no-input | dev | presence/VPMA | MUST | TODO | implementation tested; empirical run waits for adjudicated gold |
| BASE-002 | M2 | structure-only | flattened hierarchy | dev/test | VPMA, coverage, cost | MUST | TODO | 30 pre-gold outputs frozen (15 judged/15 abstain); empirical scoring still waits for union items and adjudicated gold |
| BASE-003 | M2 | text-rule baseline | Appium-style rules | dev/test | VPMA, facts | MUST | TODO | implementation tested; empirical run waits for union items and gold |
| BASE-004 | M2 | OCR-only | popup/full screenshot | dev/test | VPMA, OCR coverage | MUST | TODO | local Vision runtime and private 30-image evidence ready; empirical scoring waits for human gold and a frozen popup-presence/ROI policy |
| BASE-005 | M2 | PopSweeper + OCR | detector + ROI OCR | dev/test | presence + message | MUST | TODO | source code/model availability audit first |
| BASE-006 | M2 | screenshot-only VLM | frozen VLM | dev/test | VPMA, hallucination, cost | MUST | BLOCKED_EXTERNAL | model/API not frozen |
| FUSE-001 | M3 | always-on fusion | same backbone | dev/test | VPMA, cost | MUST | TODO | routing implementation tested; empirical prediction input pending |
| FUSE-002 | M3 | fixed cascade | WhisperTest-style perception | dev/test | VPMA, calls | SHOULD | TODO | no Voice Control/action |
| MGPU-001 | M3 | full method | MG-PU | dev | VPMA, coverage, calls | MUST | TODO | pre-gold candidate frozen with explicit scope gate (2 structure/28 visual); no score; formal visual backbone and any threshold tuning still pending dev gold |
| MGPU-002 | M4 | frozen main run | MG-PU | test | pre-registered primary comparison | MUST | TODO | test once |
| ABL-001 | M4 | empty-tree gate | MG-PU ablation | test | VPMA/calls | MUST | TODO | implementation tested; empirical test waits for frozen split |
| ABL-002 | M4 | random matched calls | MG-PU ablation | test | VPMA/calls | MUST | TODO | exact-K seeded implementation tested; empirical test waits for frozen split |
| ABL-003 | M4 | shuffled gap reasons | MG-PU ablation | test | VPMA | MUST | TODO | novelty isolation |
| ABL-004 | M4 | no critical guard | MG-PU ablation | test | hallucination | MUST | TODO | safety/quality |
| GEN-001 | M5 | held-out apps | best systems | Android holdout | group metrics | SHOULD | TODO | after main result |
| GEN-002 | M5 | iOS capability | collector only | iOS | field availability | MUST | BLOCKED_EXTERNAL | no device/simctl |
| GEN-003 | M5 | iOS evaluation | best systems | iOS test | VPMA breakdown | SHOULD | BLOCKED_EXTERNAL | depends GEN-002 |
| QA-001 | M6 | dataset validator | schema + QA | release | 0 critical errors | MUST | TODO | empirical items only |
| QA-002 | M6 | license/privacy audit | source ledger | release | all items releasable/adapter-only | MUST | TODO | human gate |
| QA-003 | M6 | reproduction | clean checkout | release | commands reproduce tables | MUST | TODO | no hidden cache |
| PUB-001 | M6 | public release | GitHub + DOI candidate | release | remote SHA/readback | MUST | TODO | only after QA gates |
