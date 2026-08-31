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
| `dataset-v1/candidates/popsweeper_candidates_n120.jsonl` | 120 条真实来源候选；60 popup/60 no-popup | frozen / message annotation pending |
| `dataset-v1/candidates/popsweeper_candidates_n120.summary.json` | 2105 张来源图清点与抽样配额 | generated / verified |
| `dataset-v1/scripts/build_crosswalk.py` | 生成 255 条 source-field crosswalk | tested generator |
| `dataset-v1/scripts/materialize_schema_fixture.py` | 生成 3 条非经验 fixture | tested generator |
| `dataset-v1/scripts/build_popsweeper_candidate_manifest.py` | 只读 ZIP 元数据并分层抽取来源候选 | tested generator |
| `dataset-v1/scripts/validate_dataset.py` | schema 与可自动化 QA 验证器 | tested |
| `dataset-v1/scripts/popsweeper_source_audit.py` | 下载归档完整性与安全清点器；不解压 | tested |
| `tests/test_popsweeper_source_audit.py` | source auditor 单元测试 | 9 tests passing |
| `tests/test_popsweeper_candidate_manifest.py` | 候选发现、去重、RICO join、分层抽样与 CLI 测试 | 7 tests passing |
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
| `dataset-v1/work/popsweeper_source_audit.json` | 266,010,362-byte 归档的 MD5、安全与成员清点 | pass |
| `dataset-v1/work/rico_semantic_source_audit.json` | 66,261 JSON/PNG 对的 RICO 归档安全清点 | pass |
| `refine-logs/FINAL_PROPOSAL.md` | 当前问题锚、benchmark 与 MG-PU proposal | provisional |
| `refine-logs/NOVELTY_CHECK.md` | 查新与 contribution claim 边界 | proceed with caution |
| `refine-logs/EXPERIMENT_PLAN.md` | 实验矩阵、统计与 kill criteria | planned |
| `refine-logs/EXPERIMENT_TRACKER.md` | source→pilot→baseline→release 状态 | active |
| `refine-logs/REVIEW_SUMMARY.md` | 当前评审摘要 | same-family provisional |
| `refine-logs/PIPELINE_SUMMARY.md` | ARIS refinement→experiment-plan 汇总 | current |
| `refine-logs/REFINE_STATE.json` | 机器可读 pipeline 状态 | current |
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

- 真实 popup-message pilot items；
- 双人独立标注与 adjudication；
- Android controlled capture 与 iOS capability records；
- structure-only、OCR/VLM、always-on fusion 和 MG-PU 的冻结 split 结果；
- 目标用户研究；
- cross-family accepted review；
- 带稳定版本号或 DOI 的公开 benchmark release。

在这些证据形成前，不得宣称已有公开 empirical dataset、跨平台验证、方法显著优于基线或真实用户体验已改善。
