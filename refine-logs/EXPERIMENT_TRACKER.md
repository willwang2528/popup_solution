# Experiment Tracker：PMAB + MG-PU

> Updated：2026-09-01 09:15 +08:00
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
| INFRA-ANN | M1 | annotation protocol + media | blind A/B + adjudication + fail-closed adapter | fixed 30-item pilot | 30 screenshots + 44 RICO artifacts; readiness pass | MUST | DONE | explicit out_of_scope reason；G1/G2 correction/restart；local media Git ignored；no human gold；freeze 1.0.5 |
| INFRA-MODEL | M1 | model-only protocol QA | independent model A/B | fixed 30-item pilot | 30+30 preannotations | SHOULD | DONE | 29/30 descriptive presence concordance; non-human, metric-ineligible, never shown to human annotators |
| INFRA-EVAL | M2 | evaluation implementation | 8 action-free methods/ablations | synthetic fixtures | 38 evaluator tests + 8 smoke runs | MUST | DONE | all smoke outputs paper_result_eligible=false; fake/source/model gold fails closed |
| INFRA-OCR | M2 | local OCR adapter | macOS Vision, full-screen OCR | fixed 30-item pilot | 7/7 authorized Vision tests; 30 private outputs | SHOULD | DONE | 30/30 text observed but all presence abstain; public aggregate only; derived text withheld pending privacy review |
| INFRA-FEATURE | M2 | pre-gold feature freeze | ID-only adapter + RICO semantic | fixed 30-item pilot | 22 available / 8 missing / 186 nodes; 3 tests | MUST | DONE | source labels/paths ignored; private bundle Git ignored, 0600 under 0700 directory; public aggregate only |
| INFRA-PREGOLD | M2 | pre-gold prediction freeze | A1 structure-only + A2 The OK + MG-PU candidate | fixed 30-item pilot | 9 tests; predictions persisted before human gold | MUST | DONE | no metrics; A1 15 judged/15 abstain；A2 10 rule-no-match/20 raw-text-missing abstain；MG-PU 2 structured/28 visual；Model-B visual evidence is not a formal reproducible baseline |
| INFRA-MEDIA-QA | M1 | frozen media technical audit | magic bytes + hash + EXIF presence | fixed 30-item pilot | 30/30 frozen hashes; format inventory | MUST | DONE | 27 JPEG + 3 PNG-under-.jpg；viewer sniffs content；PMJ-PILOT-026 has EXIF；technical pass is not privacy/license approval |
| LIT-EXPAND | M0 | residual direct-neighbor queue | CHI 2026 + A11yScan + TIMESTUMP | source review | 13 candidate fields | SHOULD | DONE | candidate-only expansion queue；frozen 255 union unchanged pending adjudicated inclusion |
| REVIEW-001 | M0 | independent design review | Claude Sonnet 5, 3 rounds | proposal/protocol/plan | fatal flaws=0; readiness=3.5/5 | MUST | DONE | PROCEED_WITH_CAUTION；review acceptance is not empirical acceptance；complete local trace saved |
| REVIEW-002 | M1 | Android capture gate adversarial review | Claude Sonnet 5 + Codex counteraudit, 3 incremental rounds | contract/finalizer/tests/status | nested leak + forged record + unbound random-hash paths closed | MUST | DONE | TOOLING_GATE_CONVERGED；malicious-collector/process trust remains external；empirical claim change NONE |
| DAT-002 | M1 | pilot union item materialization | union item builder | fixed 30-item pilot | 30 schema-valid pending observations | MUST | DONE | 255-field union materialized privately；22 structure / 8 missing / 186 nodes；all gold null and 0 metric eligible |
| INFRA-CAPTURE | M1 | Android capture finalization gate | fail-closed offline finalizer + artifact-refinalizing coverage audit | synthetic test bundles only | 12 finalizer tests；recursive label-leak rejection；record-only CLI disabled；5-group/3-template/3-strata contract | MUST | DONE | tooling only；current host has no adb/emulator/appium；paper_result_eligible=false |
| CAP-001 | M1 | formal Android capture feasibility | synchronized screenshot + AccessibilityService representation | ≥5 groups / ≥3 template families / 3 strata | sync/provenance/license/privacy gate | MUST | TODO | tooling_ready_no_device；real capture=0；PopSweeper/RICO/UIAutomator cannot substitute |
| ANN-001 | M1 | G1 annotation pilot | 2 human screenshot-only annotators | real synchronized Android pilot | κ/message/slot gates | MUST | TODO | starts only after CAP-001；current PopSweeper 30 is protocol pilot, not formal benchmark gold |
| ANN-002 | M1 | adjudication | third reviewer | disputed items | final gold + ambiguity | MUST | TODO | depends ANN-001 |
| ANN-003 | M1 | G2 structure-sufficiency audit | 2 method-blind auditors + third adjudicator | frozen G1 + raw structure | gap agreement / cannot_resolve | MUST | TODO | G2 cannot rewrite G1；substantive G1 error triggers versioned correction and full G2 restart |
| BASE-001 | M2 | majority sanity | no-input | dev | presence/VPMA | MUST | TODO | implementation tested; empirical run waits for adjudicated gold |
| BASE-002 | M2 | structure-only | flattened hierarchy | dev/test | VPMA, coverage, cost | MUST | TODO | 30 pre-gold outputs frozen (15 judged/15 abstain); empirical scoring still waits for union items and adjudicated gold |
| BASE-003 | M2 | text-rule baseline | The OK official Appium-style rules | dev/test | VPMA, facts | MUST | TODO | official `b618948` rules frozen；30 pre-gold outputs frozen (10 rule-no-match/20 raw-text-missing abstain)；matched-text message is v1 adaptation；scoring waits for gold |
| BASE-004 | M2 | OCR-only | popup/full screenshot | dev/test | VPMA, OCR coverage | MUST | TODO | local Vision runtime and private 30-image evidence ready; empirical scoring waits for human gold and a frozen popup-presence/ROI policy |
| BASE-005 | M2 | PopSweeper reconstruction + OCR | popup classifier + full-screen OCR | dev/test | presence + message | MUST | BLOCKED_EXTERNAL | exact NO-GO until code/weights/thresholds/temporal frames/close-bbox assets exist；paper outputs close-button bbox, not popup ROI；custom ROI is separate B2A adaptation |
| BASE-006 | M2 | screenshot-only VLM | frozen VLM | dev/test | VPMA, hallucination, cost | MUST | BLOCKED_EXTERNAL | model/API not frozen |
| FUSE-001 | M3 | always-on fusion | same backbone | dev/test | VPMA, cost | MUST | TODO | routing implementation tested; empirical prediction input pending |
| FUSE-002 | M3 | fixed cascade | WhisperTest-style perception | dev/test | VPMA, calls | SHOULD | TODO | no Voice Control/action |
| MGPU-001 | M3 | full method | MG-PU | dev | VPMA, coverage, calls | MUST | TODO | pre-gold candidate frozen with explicit scope gate (2 structure/28 visual); no score; formal visual backbone and any threshold tuning still pending dev gold |
| MGPU-002 | M4 | frozen main run | MG-PU vs seeded random-K at K50 | test | primary paired comparison | MUST | TODO | K=ceil(0.50×N) visual calls；test once；secondary comparisons Holm-corrected |
| ABL-001 | M4 | empty-tree gate | MG-PU ablation | test | VPMA/calls | MUST | TODO | implementation tested; empirical test waits for frozen split |
| ABL-002 | M4 | random matched calls | MG-PU ablation | test | VPMA/calls | MUST | TODO | exact-K seeded implementation tested; empirical test waits for frozen split |
| ABL-003 | M4 | shuffled gap reasons | MG-PU ablation | test | VPMA | MUST | TODO | novelty isolation |
| ABL-004 | M4 | no critical guard | MG-PU ablation | test | hallucination | MUST | TODO | safety/quality |
| GEN-001 | M5 | held-out apps | best systems | Android holdout | group metrics | SHOULD | TODO | after main result |
| GEN-002 | M5 | iOS capability | collector only | iOS | field availability | MUST | BLOCKED_EXTERNAL | no device/simctl |
| GEN-003 | M5 | iOS evaluation | best systems | iOS test | VPMA breakdown | SHOULD | BLOCKED_EXTERNAL | depends GEN-002 |
| QA-001 | M6 | dataset validator | schema + QA | release | 0 critical errors | MUST | TODO | empirical items only |
| QA-002 | M6 | license/privacy audit | source ledger + PUBLIC_RELEASE_GATE | release | all items releasable/adapter-only | MUST | BLOCKED_EXTERNAL | docs/code may be pushed after clean-clone audit；empirical dataset blocked by 0 human gold, per-item redistribution/privacy review, and unresolved EXIF item |
| QA-003 | M6 | reproduction | isolated public-repository checkout | docs/code release | 180 run / 178 pass / 2 host-authorized skips | MUST | DONE | post-review artifact-binding hardening passes in publish checkout；staged audit and remote readback remain PUB-001 checks |
| PUB-001 | M6 | public research-material release | GitHub | docs/code/protocol | remote SHA/readback | MUST | DONE | authorized public push；empirical dataset remains separately blocked by QA-002 |
