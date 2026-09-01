# Popup Solution Research Manifest

> Updated: 2026-09-01
>
> Scope: 当前可公开、可追踪的研究协议与数据契约。`provisional` 不等于论文结论已经成立；synthetic fixture 不等于 empirical dataset。
>
> Authority: 对 `popup-solution/` 的发布状态，以本文件为准；项目根 `outputs/MANIFEST.md` 只保留索引与历史快照，不覆盖这里的实时状态。

## 当前权威入口

| Artifact | Role | Status |
|---|---|---|
| `README.md` | 仓库入口、v1 边界与当前完成度 | current |
| `RESEARCH_RULES.md` | 飞书 revision 46 原文，保持原样 | protected source |
| `RESEARCH_RULES_AMENDMENT_V1.md` | 用户最新的 message-only v1 修订 | current override |
| `RESEARCH_RULES_PROVENANCE.json` | 飞书 URL、revision、文档 ID 与原文 SHA-256 | verified provenance |
| `AGENTS.md` | 仓库研究执行约束 | current |
| `RESEARCH_BRIEF.md` | v1 问题、假设、指标和贡献口径 | current / provisional |
| `sources/PPT_SLIDE_14_EVIDENCE.md` | PPT 五级回证证据锚与 v1/进阶分层 | verified source note |
| `sources/SOURCE_LEDGER.md` | PopSweeper/RICO 校验、join、许可与发布边界 | verified source ledger |
| `method/METHOD_SPEC.md` | MG-PU 方法规格；v1 无动作 | current / provisional |
| `data-collection/papers.jsonl` | 14 篇 PPT 论文的机器可读方法证据 | collected / source-bounded |
| `data-collection/papers.csv` | 上述证据的表格视图 | derived |
| `data-collection/README.md` | 文献纳入边界与复核规则 | current |
| `data-collection/collection.schema.json` | 单篇文献记录 schema | current |
| `data-collection/FIELD_UNION.md` | 文献方法与我方方法的字段并集说明 | current / provisional |
| `data-collection/COLLECTION_SUMMARY.json` | 文献采集统计与边界 | current |
| `data-collection/slr-expansion/EXPANSION_QUEUE.md` | CHI 2026、A11yScan、TIMESTUMP 的直接邻近扩展候选 | candidate only / frozen 255 union unchanged |
| `DATASET_SCHEMA.md` | 跨平台 union schema 说明 | current / provisional |
| `dataset-v1/README.md` | v1 数据结构、生成与验证入口 | current |
| `dataset-v1/DATASET_CARD.md` | v1 数据集卡；明确 empirical collection pending | current / provisional |
| `dataset-v1/DATASET_MANIFEST.json` | v1 数据契约、cohort 和校验摘要 | current / provisional |
| `dataset-v1/ANNOTATION_GUIDE.md` | popup presence/message/gap 标注协议 | current / provisional |
| `dataset-v1/data/item.template.json` | 单 item 模板与 v1 no-action 示例 | generated source template |
| `dataset-v1/schema/item.schema.json` | 单 item JSON Schema | current / provisional |
| `dataset-v1/schema/source_to_item_crosswalk.json` | 90 文献字段 + 165 我方字段 = 255 映射 | generated / validated |
| `dataset-v1/schema/field_catalog.json` | union 字段目录 | generated / validated |
| `dataset-v1/schema/qa_rules.json` | union QA 契约 | current |
| `dataset-v1/schema/qa_implementation_coverage.json` | 29 个 QA 门禁的实现覆盖映射 | generated / validated |
| `dataset-v1/schema/v1_message_qa_rules.json` | v1 message-only QA 契约 | current |
| `dataset-v1/provenance/paper_method_coverage.json` | 14 篇论文到 union 字段/用途的覆盖 | generated / source-bounded |
| `dataset-v1/data/items.schema-fixture.jsonl` | 3 条非经验 schema fixture | synthetic / not for metrics |
| `dataset-v1/candidates/popsweeper_candidates_n120.jsonl` | 120 条真实来源候选；按来源目录分层为 60 `ads` / 60 `no_ads`，不是人工 presence gold | frozen / message annotation pending |
| `dataset-v1/candidates/popsweeper_candidates_n120.summary.json` | 2105 张来源图清点与抽样配额 | generated / verified |
| `dataset-v1/annotation-pilot/README.md` | 30 条 pilot、双人盲标、一致性与裁决协议 | current / human labels pending |
| `dataset-v1/annotation-pilot/manifests/pilot_batch_30.jsonl` | 按来源目录分层为 15 `ads` / 15 `no_ads` 的固定 adapter-only pilot | frozen / no human presence/message gold |
| `dataset-v1/annotation-pilot/schemas/annotation_record.schema.json` | A/B 盲标记录 schema | current / tested |
| `dataset-v1/annotation-pilot/schemas/adjudication_input.schema.json` | 分歧裁决输入 schema | current / tested |
| `dataset-v1/annotation-pilot/schemas/adjudication_output.schema.json` | 最终金标输出 schema | current / blank template only |
| `dataset-v1/annotation-pilot/schemas/gap_independent_audit_record.schema.json` | A/B 独立 structure–visual gap 记录、真人声明与结构 candidate 绑定 schema | current / no human values |
| `dataset-v1/annotation-pilot/schemas/gap_adjudication_output.schema.json` | message gold 后、method-blind 的结构—视觉 gap 最终裁决 schema | current / no human values |
| `dataset-v1/annotation-pilot/STRUCTURE_VISUAL_GAP_AUDIT.md` | 两人独立 gap audit、第三人仲裁与输入隔离协议 | current / audit pending |
| `dataset-v1/annotation-pilot/PILOT_PROTOCOL_FREEZE.json` | 人工会话前阈值、全量第三人复核、媒体与协议哈希冻结 | frozen / no human outputs yet |
| `dataset-v1/annotation-pilot/HUMAN_ANNOTATION_READINESS.json` | 路径脱敏的人工开标 readiness 结果 | ready for real human annotation only |
| `dataset-v1/annotation-pilot/MEDIA_QA.json` | 30-item 媒体 magic/hash/EXIF 技术审计 | pass / not privacy or license approval |
| `dataset-v1/annotation-pilot/scripts/check_human_annotation_readiness.py` | 协议、ID、blank、权限、Git ignore、媒体哈希 fail-closed 门 | tested / 21 readiness tests |
| `dataset-v1/annotation-pilot/scripts/build_pilot_bundle.py` | 再现固定 pilot 与 A/B 盲标模板 | tested generator |
| `dataset-v1/annotation-pilot/scripts/calculate_agreement.py` | κ、消息一致性、semantic-slot Jaccard 与分歧导出 | tested / no human values yet |
| `dataset-v1/empirical-pilot/materialize_pending_union.py` | 30 条 pending item 物化为完整 union，保留稳定 pilot join key、186 个 raw pixel bounds 与 pending gap container | tested / private text-bearing output |
| `dataset-v1/empirical-pilot/PUBLIC_PENDING_UNION_SUMMARY.json` | 30/22/8/186 聚合、hash 与负向声明 | current / unscored |
| `dataset-v1/android-capture/CAPTURE_CONTRACT_V1.json` | 正式 Android 同步 screenshot + AccessibilityService snapshot 的 fail-closed CAP-001 合同 | current / real capture pending |
| `dataset-v1/android-capture/finalize_android_capture.py` | 单条终结与 5-group/3-template/3-strata 聚合可行性门 | tested / tooling only |
| `dataset-v1/android-capture/PUBLIC_FEASIBILITY_STATUS.json` | 不含私有内容的 CAP-001 当前状态 | blocked / real capture count 0 |
| `dataset-v1/android-capture/tests/test_capture_finalizer.py` | 截图完整性、provenance、同步、稳定性、无动作、递归标签泄漏、artifact-refinalizing 聚合、重复和 coverage 回归 | 12 tests passing |
| `dataset-v1/scripts/build_crosswalk.py` | 生成 255 条 source-field crosswalk | tested generator |
| `dataset-v1/scripts/materialize_schema_fixture.py` | 生成 3 条非经验 fixture | tested generator |
| `dataset-v1/scripts/build_popsweeper_candidate_manifest.py` | 只读 ZIP 元数据并分层抽取来源候选 | tested generator |
| `dataset-v1/scripts/export_annotation_media.py` | 固定归档哈希与 member 后导出本地、Git 忽略的标注媒体 | tested / real local export pass |
| `dataset-v1/scripts/validate_dataset.py` | schema 与可自动化 QA 验证器 | tested |
| `dataset-v1/scripts/popsweeper_source_audit.py` | 下载归档完整性与安全清点器；不解压 | tested |
| `tests/test_popsweeper_source_audit.py` | source auditor 单元测试 | 9 tests passing |
| `tests/test_popsweeper_candidate_manifest.py` | 候选发现、去重、RICO join、分层抽样与 CLI 测试 | 7 tests passing |
| `tests/test_annotation_pilot_protocol.py` | 固定批次、盲法、显式范围排除与无金标泄漏测试 | 6 tests passing |
| `tests/test_annotation_agreement.py` | agreement、配对、范围排除、规范化与分歧导出测试 | 6 tests passing |
| `tests/test_export_annotation_media.py` | 归档/member/CRC/RICO join/gitignore/冻结 pilot 测试 | 8 tests passing |
| `dataset-v1/validation-result.json` | 当前 synthetic fixture 验证结果 | pass / non-empirical |
| `dataset-v1/VALIDATION_REPORT_V1_MESSAGE.md` | v1 schema/fixture/negative mutation 验证说明 | pass / non-empirical |
| `dataset-v1/work/literature_field_union.json` | 90 条文献原子字段工作集 | generated evidence |
| `dataset-v1/work/literature_field_audit.md` | 文献字段并集审计 | same-family provisional |
| `dataset-v1/work/our_method_fields.json` | 165 条我方方法原子字段工作集 | generated evidence |
| `dataset-v1/work/our_method_field_audit.md` | 我方字段集合审计 | same-family provisional |
| `dataset-v1/work/item_contract_review.md` | item 契约复核 | same-family provisional |
| `dataset-v1/work/qa_coverage_map.md` | 29 个 QA 门禁的自动化/人工覆盖 | verified mapping |
| `dataset-v1/work/final_dataset_audit.md` | v1 契约修复后复核 | same-family PASS / provisional |
| `dataset-v1/work/v1_message_contract_proposal.md` | v1 no-action 契约变更设计记录 | implemented design record |
| `dataset-v1/work/MODEL_PREANNOTATION_STATUS.md` | A/B 模型预标注范围、描述性一致和禁用口径 | current / non-human / not metric eligible |
| `dataset-v1/work/model-preannotation-a-summary.md` | 模型 A 范围、聚合分布与资格说明 | current / non-human / item JSONL withheld |
| `dataset-v1/work/model-preannotation-b-summary.md` | 模型 B 范围、聚合分布与资格说明 | current / non-human / item JSONL withheld |
| `dataset-v1/work/popsweeper_source_audit.json` | 266,010,362-byte 归档的 MD5、安全与成员清点 | pass |
| `dataset-v1/work/rico_semantic_source_audit.json` | 66,261 JSON/PNG 对的 RICO 归档安全清点 | pass |
| `experiments/v1-message/README.md` | v1 输入、方法、指标、命令与证据边界 | current |
| `experiments/v1-message/popup_eval/` | majority、A1/A2、MG-PU、整批 gold finalizer、冻结预测评分、语义复核、gap audit、visual-bank freeze 与 paired comparison | implemented / action-free / no human result |
| `experiments/v1-message/run_eval.py` | 可复现 v1 evaluation CLI | tested / empirical gold required |
| `experiments/v1-message/tests/` | 路由、A1/A2、gold batch、冻结预测、语义/gap hash、visual freeze、group-map 与 paired bootstrap 测试 | 67 tests passing |
| `experiments/v1-message/schemas/semantic_output_adjudication.schema.json` | 绑定逐项 prediction SHA-256 的盲式消息语义复核 | implemented / human values pending |
| `experiments/v1-message/statistics/README.md` | post-gold paired scorer、隐私 group-map 与统计边界 | current / exploratory only |
| `experiments/v1-message/statistics/PUBLIC_GROUP_MAP_SUMMARY.json` | 30 singleton cluster 的无标识聚合与哈希 | current / formal leakage control false |
| `experiments/v1-message/popup_eval/comparison_cli.py` | 同 gold/item 集、预声明 reference、确定性 cluster bootstrap CLI | tested / no empirical run |
| `experiments/v1-message/visual/VISUAL_EVIDENCE_PROTOCOL_V1.json` | B1/C1/MG-PU 共用的 presence/ROI/model/budget freeze 状态 | blocked / no formal visual bank |
| `experiments/v1-message/visual/README.md` | 全屏/close-button box 非 popup ROI、C1-AO/C1-BM 命名与公私边界 | current |
| `experiments/v1-message/popup_eval/visual_freeze.py` | 私有 visual bank ready-state、截图 commitment、exact-bijection、gold-blind、ROI/config/request/response 验证器 | tested / no formal bank rows |
| `experiments/v1-message/popup_eval/gap_adjudication.py` | 绑定真实 message gold、结构 bundle、两份独立 audit record 与最终裁决的 gap finalizer | tested / no human audit rows |
| `experiments/v1-message/results/synthetic-smoke/` | 八种方法的管线 smoke | pass / synthetic / not paper eligible |
| `experiments/v1-message/resources/the-ok/` | 官方 `b618948` 指示词快照、来源与 MIT notice | fixed upstream evidence |
| `experiments/v1-message/B2_POPSWEEPER_REPRODUCIBILITY_GATE.md` | exact B2 的 fail-closed 资产门禁与允许的 reconstruction/adaptation | NO-GO / current artifacts |
| `experiments/v1-message/ocr/README.md` | 本地 macOS Vision OCR 输入、隐私、复现和 claim 边界 | current |
| `experiments/v1-message/ocr/run_ocr.py` | fail-closed manifest/image-hash/OCR adapter | tested |
| `experiments/v1-message/ocr/vision_ocr.swift` | 本地 `VNRecognizeTextRequest` 引擎 | tested on authorized local host |
| `experiments/v1-message/ocr/tests/test_ocr_adapter.py` | 泄漏、路径、哈希、engine、privacy 与真实 Vision gate | 7 tests passing in authorized run |
| `experiments/v1-message/ocr/PUBLIC_RUN_SUMMARY.json` | 30 图私有 OCR run 的无文本聚合摘要 | pass / unscored / privacy-withheld |
| `experiments/v1-message/ocr/compute/` | 可公开、无本机绝对路径的环境 spec 与 ledger | tier-3 reproduced |
| `experiments/v1-message/features/build_pilot_features.py` | 只消费 pilot ID、冻结 RICO 结构特征并隔离来源标签 | tested / gold-blind |
| `experiments/v1-message/features/tests/` | 标签翻转不变性、private ignore/permission、路径逃逸与文本语义测试 | 3 tests passing |
| `experiments/v1-message/features/PUBLIC_FEATURE_SUMMARY.json` | 30-item 私有结构包的无文本计数、契约与哈希 | pass / unscored |
| `experiments/v1-message/pregold/adapt_model_preannotation.py` | 将 AI-only、非金标记录隔离转换为私有视觉候选 | tested / not formal baseline |
| `experiments/v1-message/pregold/freeze_predictions.py` | 在人工 gold 前冻结 A1、A2 与 MG-PU 逐项预测；不评分 | tested / gold-blind / no-action |
| `experiments/v1-message/pregold/tests/` | gold/provenance/盲法拒绝、显式 popup scope、零动作、私有输出与公开摘要测试 | 9 tests passing |
| `experiments/v1-message/pregold/PUBLIC_PREGOLD_SUMMARY.json` | 私有逐项预测的无文本聚合、实现/输入/输出哈希 | pass / unscored / not paper eligible |
| `refine-logs/FINAL_PROPOSAL.md` | 当前问题锚、benchmark 与 MG-PU proposal | provisional |
| `refine-logs/NOVELTY_CHECK.md` | 查新与 contribution claim 边界 | proceed with caution |
| `refine-logs/EXPERIMENT_PLAN.md` | 实验矩阵、统计与 kill criteria | planned |
| `refine-logs/EXPERIMENT_TRACKER.md` | source→pilot→baseline→release 状态 | active |
| `refine-logs/REVIEW_SUMMARY.md` | 三轮 cross-family 评审与处理摘要 | current / proceed with caution |
| `refine-logs/PIPELINE_SUMMARY.md` | ARIS refinement→experiment-plan 汇总 | current |
| `refine-logs/REFINE_STATE.json` | 机器可读 pipeline 状态 | current |
| `reviews/RESEARCH_REVIEW.md` | Claude cross-family 初始三轮研究评审 + 三轮 capture-gate 增量审阅、Codex 反例与任务标识 | accepted review trace / tooling converged / not empirical acceptance |
| `PUBLIC_RELEASE_GATE.json` | 研究文档/代码与经验数据的分离发布闸 | docs/code auditable；empirical dataset blocked |
| `refine-logs/DATA_COLLECTION_LOCAL_AUDIT.md` | 早期文献采集一致性审计 | historical / provisional |
| `refine-logs/PROVISIONAL_LOCAL_REVIEW.md` | 早期本地 proposal review | historical / provisional |
| `refine-logs/REFINEMENT_REPORT.md` | 当前精炼报告 | current / provisional |
| `refine-logs/V1_SCOPE_LOCAL_REVIEW.md` | v1 消息契约独立同家族复核 | PASS / provisional |
| `refine-logs/round-0-initial-proposal.md` | 精炼前 proposal trace | historical trace |
| `refine-logs/round-1-review.md` | round 1 review trace | same-family provisional |
| `refine-logs/round-1-refinement.md` | round 1 refinement trace | current trace |

## 版本快照

以下时间戳文件保留研究演化历史，不覆盖当前固定入口：

- `RESEARCH_BRIEF_*.md`
- `DATASET_SCHEMA_*.md`
- `method/METHOD_SPEC_*.md`
- `refine-logs/FINAL_PROPOSAL_*.md`
- `refine-logs/REFINEMENT_REPORT_*.md`
- `refine-logs/REFINE_STATE_*.json`
- `refine-logs/NOVELTY_CHECK_*.md`
- `refine-logs/EXPERIMENT_PLAN_*.md`
- `refine-logs/EXPERIMENT_TRACKER_*.md`
- `refine-logs/REVIEW_SUMMARY_*.md`
- `refine-logs/PIPELINE_SUMMARY_*.md`

## 历史或非发布入口

- `dataset-v1/VALIDATION_REPORT.md`：schema 1.0 阶段的历史验证报告；当前 v1 以 `VALIDATION_REPORT_V1_MESSAGE.md` 为准。
- `dataset-v1/work/qa_rules.json`：QA 契约的工作副本；发布接口以 `dataset-v1/schema/qa_rules.json` 为准。
- `.idea/`、`__pycache__/`、`*.pyc`：本地工具状态，已由 `.gitignore` 排除，不进入公开仓库。

## 尚未形成的证据

- 具有双人消息金标、可进入 VPMA 的 empirical popup-message pilot items；
- 真实双人独立标注与 adjudication；
- 两人独立且第三人仲裁的 structure–visual gap audit；
- Android controlled capture 与 iOS capability records；
- structure-only、OCR/VLM、always-on fusion 和 MG-PU 的 empirical 冻结 split 结果；
- 目标用户研究；
- 基于真实 empirical result 的独立复核与 acceptance（当前 cross-family review 只接受进入 pilot 的设计）；
- 带稳定版本号或 DOI 的公开 benchmark release。

在这些证据形成前，不得宣称已有公开 empirical dataset、跨平台验证、方法显著优于基线或真实用户体验已改善。

`papers.jsonl` 现在为 14/14 篇补齐了 25 个公开主来源入口，覆盖 DOI、arXiv、出版社、机构仓库、作者公开稿、官方项目和数据集。公开 clone 已能重新定位每篇论文；但既有 29 个本地 `source_evidence.path` 仍是冻结的逐字段 locator，只有在公开全文上逐字段复核后才能升级证据等级，不能仅凭新增 URL 自动视为重审完成。
