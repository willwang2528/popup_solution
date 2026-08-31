# QA 门禁自动化覆盖图

审查对象：`schema/qa_rules.json` 与 `scripts/validate_dataset.py`。本表按“规则全部断言是否由当前验证器独立执行”保守分类；通用 JSON Schema 只验证形状、类型、枚举或必填项时，不视为完成语义门禁。

- `automated_full`：当前脚本直接、完整执行该门禁的全部断言。
- `automated_partial`：至少一个核心断言有自动检查，但仍有未覆盖或仅信任上游布尔值的部分。
- `manual_release`：当前脚本没有针对该门禁的实质语义检查，发布前需人工或新增独立工具执行。

## Item gates

| Gate | 分类 | 当前代码证据与未覆盖点 |
|---|---|---|
| ITEM-001 | `automated_full` | `load_jsonl(..., object_pairs_hook=strict_object_pairs)` 拒绝重复键；`validate_schema` 执行版本/非空约束；`check_dataset` 检查 `item_id` 全局唯一。 |
| ITEM-002 | `automated_full` | `check_item` 检查 observation/candidate/attempt ID 唯一，并逐项解析 candidate→observation、decision→candidate、attempt before/after→observation、target→candidate 的全部引用。 |
| ITEM-003 | `automated_partial` | 已检查 observation 时间戳非递减、存在动作时具有前后 phase；未验证前后 observation 与每次动作的真实时序，未强制 verified recovery 同时具有 `post_action` 与 `task_check`，也未证明 frame/retry/relaunch 没有跨 episode。条件 `collection_status` 亦未按规则实现。 |
| ITEM-004 | `automated_partial` | `check_local_presence` 与 `check_global_observability` 检查 presence、非空 provenance 和 measurement channel；未验证 raw 是否确实被完整保留、normalized 是否替换 raw，`derived` 也未被要求列出公式/上游 pointers。 |
| ITEM-005 | `manual_release` | 当前脚本不解析 artifact URI，不检查文件可解析性、SHA-256、media/capture/redaction、privacy review 或 withheld access policy；JSON Schema 形状检查不足以通过该门。 |
| ITEM-006 | `automated_partial` | `check_item` 按平台要求至少出现一种 Android/iOS/DOM raw，Schema 约束平台枚举；未限定“primary structured observation”、未核验 collection-failure 例外、混合/WebView channel provenance，以及不适用 raw 必须为 `null + not_applicable`。 |
| ITEM-007 | `automated_partial` | A-VTR 非空时检查 Android→TalkBack、iOS→VoiceOver；未覆盖 `eligible_for_main_metric=true` 但 A-VTR 为空的分支，未强制 AT enabled、focus evidence，也未禁止用 framework hierarchy 充当屏幕阅读器焦点证据。 |
| ITEM-008 | `manual_release` | mobile-web 分支只检查 DOM raw（属于 ITEM-006）；没有核验 host OS/version、device/browser fixture identity、browser/driver version、fixture cohort，或 target-device A-VTR 必须来自 physical device + actual screen reader。 |
| ITEM-009 | `automated_partial` | ordinary scope 已检查 unsafe=false、`ordinary_exit` 和 allowed action 为低风险集合；未在 `policy.decision == execute` 时独立验证 owner/actionability/low-risk 三项均真。 |
| ITEM-010 | `automated_partial` | 非 ordinary 分支检查 policy 为 abstain/handoff/no_action，且无非 human/none 的自主动作；未检查 abstention/handoff 标志、main-metric eligibility=false，也未限制只能进入指定安全评估 cohort。 |
| ITEM-011 | `automated_partial` | ours+structured_sufficient 时检查 tau、delta、owner、executable、low-risk、`capture_fresh_and_synchronized` 和空 gaps；同步性仅信任上游布尔值，没有由 timestamp/tolerance 独立重算。 |
| ITEM-012 | `automated_partial` | 已检查 trigger 非空、被选 candidate 含 `visual_raw` 且 safe GT；未证明 trigger 对应已记录 gap/stale state、visual candidate 已重新评分并通过同一 policy，也未禁止仅凭 VLM 输出授权/宣告成功。 |
| ITEM-013 | `automated_partial` | 已检查 attempt index 连续、自主尝试不超过 2、retry count/budget；未核验第二次尝试恰为预注册 alternative candidate，也未在 alternative 失败后强制 abstain/handoff。 |
| ITEM-014 | `automated_partial` | 独立重算 `D = tri_and(visual_popup_gone, semantic_popup_gone)`，且 D=true 时要求 evidence URI；未审计两个输入是否仅由 coordinate hit/command/screen/tree change 等弱代理生成。 |
| ITEM-015 | `automated_partial` | 独立重算 `C_tech` 且 true 时要求 evidence URI；未把 blocked target identity 与 `scenario.blocked_target_gt` 做一致性比对。 |
| ITEM-016 | `automated_partial` | 根据 focus/utterance observability 重算 `C_a11y`，并要求 true 有 evidence；未实现“focus 不可观测但经同意的 target-user validation”例外，observability 本身也未与证据独立核对。 |
| ITEM-017 | `automated_partial` | 按 `postcondition_verifiable` 重算 T，且 T=true 时要求 evidence URI；未核验该 evidence 确实对应 `scenario.task_postcondition_gt`。 |
| ITEM-018 | `automated_full` | `check_item` 用三值 `tri_and` 独立重算 `VTR_tech(D,C_tech,T)` 与 `A_VTR(D,C_a11y,T)`；任一未知 conjunct 会传播为 null，且不从 VTR-tech 复制 A-VTR。 |
| ITEM-019 | `manual_release` | 当前脚本没有系统检查 GT evidence、双人独立标注、disagreement adjudication、fixture oracle 限域或 target-user 去身份化；仅 ITEM-022 的单个 `target_user` role 检查不能替代本门。 |
| ITEM-020 | `automated_partial` | 已检查 synthetic 的 origin/split/全部 empirical eligibility、paper reconstruction 的 origin/split、controlled fixture origin；未禁止 paper reconstruction 的 training/metric eligibility，也未验证 controlled fixture 与 real-app 的发布指标分 cohort。 |
| ITEM-021 | `automated_full` | `check_dataset` 对 train/validation/test 项逐一要求六个 leakage group ID 非空；Schema 负责基本类型/非空形状，满足该门的 ID presence 断言。 |
| ITEM-022 | `automated_partial` | eligible UX 时已检查 real_app、physical、human observability 和存在 target_user annotation；未检查 source_origin=real_device、annotation 已 adjudicated、伦理/同意/补偿/隐私证据、A-VTR 非空，以及自动日志不得替代真人证据。 |
| ITEM-023 | `automated_partial` | 脚本确实不读取 `item.quality` true 作为通过依据，而是执行独立检查；但不会重算并写回 quality booleans，也不验证 accepted 仅在 blockers 全过后设置，或 review_notes 完整记录 warnings/exclusions。 |

## Dataset gates

| Gate | 分类 | 当前代码证据与未覆盖点 |
|---|---|---|
| DATASET-001 | `automated_full` | `check_dataset` 对六个 leakage group 字段建立 value→split 集合，任一值跨 train/validation/test 即报错。 |
| DATASET-002 | `automated_partial` | synthetic fixture 被强制无 training/main-metric/UX eligibility；paper reconstruction 仅检查 origin/split，未强制其 training 与 empirical metric eligibility 均为 false。 |
| DATASET-003 | `manual_release` | 当前脚本不计算或读取发布聚合结果，无法证明 real-app 与 controlled-fixture 指标分开计算和发布。 |
| DATASET-004 | `manual_release` | 仅生成“无 iOS/无 real-app”数据存在性 warning；没有按 platform×AT 输出 A-VTR coverage/capability exclusions，也无法审计 outcome-based complete-case filtering。 |
| DATASET-005 | `manual_release` | 没有结果分层、cluster-aware uncertainty 或 platform/app-template/exposure/popup-kind/safety-stratum 报告检查。 |
| DATASET-006 | `manual_release` | 没有 release artifact inventory，也不验证每个发布 artifact 的 permission、privacy/redaction、hash、provenance 与 access disposition。 |

## 汇总

| 范围 | automated_full | automated_partial | manual_release | 合计 |
|---|---:|---:|---:|---:|
| Item | 4 | 16 | 3 | 23 |
| Dataset | 1 | 1 | 4 | 6 |
| 总计 | 5 | 17 | 7 | 29 |

结论：当前 `validation-result.json` 的 `pass` 只能解释为“已实现检查及结构契约通过”，不能解释为 29 个 QA 门禁全部自动通过。正式 empirical release 前至少仍需完成 7 个 `manual_release` 门禁，并补齐 17 个 partial 门禁的未覆盖断言。
