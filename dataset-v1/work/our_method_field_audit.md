# Actionability-Gap-Gated Recovery 字段审计

## 结论

our_method_fields.json 把单个评测单元固定为完整 popup episode，而不是单张截图。字段覆盖任务上下文、平台与辅助技术、同步观察、结构化与视觉候选、门控、低风险决策与逐次执行、D/C_tech/C_a11y/T、abstain/handoff、安全性、provenance 和可观测性；原始焦点与朗读 trace 通过 URI 保留。

本清单是方法规格字段，不是已完成的平台能力声明。尤其是 iOS：ios_raw、XCUI 动作、VoiceOver 焦点和朗读只有在目标设备与目标 OS 的 capability probe 通过后才进入相应 required_if 或 required_if_observable 分支。框架 page source 可读不等于 VoiceOver 可观察，也不等于量产辅助能力。

## 来源映射

| 字段组 | 主要依据 | 审计结论 |
|---|---|---|
| task_context、platform_context、structured/visual 输入和 decision/verification 输出 | popup-solution/method/METHOD_SPEC.md 第 48–92 行 | 已逐项落为 episode 内路径，并补充 label source 与缺失策略。 |
| UnifiedActionCandidate、原始字段、presence mask、provenance | METHOD_SPEC 第 94–120 行；DATASET_SCHEMA 第 20–32、94–132 行 | 公共层仅做决策投影；android_raw、ios_raw、dom_raw、visual_raw 保留。 |
| tree/screenshot 同步与工具失败 | METHOD_SPEC 第 143–166 行；RESEARCH_BRIEF 第 27–39 行 | stale/mismatch/tool_failure 不得标为平台暴露缺陷。 |
| actionability gate、tau/delta、owner、执行性、安全性、gap reasons | METHOD_SPEC 第 168–200 行；RESEARCH_BRIEF 第 41–74 行 | 不允许只用“树为空”触发视觉；记录 pre/post score、margin、全部必要条件和路由状态。 |
| selective visual completion 与执行优先级 | METHOD_SPEC 第 202–226 行 | 仅门控触发 OCR/detector/frozen VLM；VLM 只产候选，敏感动作由策略拒绝。 |
| D、C_tech、C_a11y、T | METHOD_SPEC 第 228–260 行；DATASET_SCHEMA 第 152–187 行；RESEARCH_BRIEF 第 61–72 行 | VTR-tech 与 A-VTR 分开；C_tech 绝不替代 C_a11y。 |
| episode/scenario/observation/action/outcome/annotation 基础实体 | DATASET_SCHEMA 第 34–202 行 | 字段路径兼容现有实体含义，并把方法新增的 gate、capability、safety、feedback、observability 作为 episode 子对象。 |
| iOS 证据边界 | DATASET_SCHEMA 第 225–248 行；RESEARCH_BRIEF 第 90–96、144–151 行 | iOS 字段仅为待实测工程候选；跨平台技术或用户恢复主张必须分别通过对应闭环。 |
| 安全边界与 abstain/handoff | METHOD_SPEC 第 38–46、214–226 行；RESEARCH_BRIEF 第 20–25 行 | CAPTCHA、风控、认证、支付、安装、删除、设备管理、正向授权、未知语义和无安全出口均记录为拒绝条件。 |

## 必需性规则审计

1. required 字段用于主键、固定任务契约、平台/AT 配置、门控决策、策略版本、安全结果、技术回证和 provenance。缺少时拒绝记录，或明确阻断成功声明。
2. required_if 字段只在事件真实发生或能力已经验证时强制，例如 visual_raw、action_attempt、iOS raw、坐标与 handoff。
3. required_if_observable 只用于屏幕阅读器焦点和朗读。pending_capability_probe、not_observable 与 tool_failure 是不同状态，不能合并成 null。
4. recommended 字段不阻断记录解析，但缺失会限制框架分层、同步诊断或复现实验。

## 关键不变量

- structured_sufficient 只有在 top1 分数达到 tau、margin 达到 delta、owner/context 正确、动作受支持且可执行、属于低风险策略、capture 新鲜同步时才可为 true。
- visual_fallback_triggered 只能由明确 gap 触发；visual candidate 仍需统一表示、重评分和策略检查。
- action attempt 最多允许一个预注册替代重试；达到预算后必须 abstain/handoff。
- D = visual_popup_gone AND semantic_popup_gone。
- C_tech = owner_context_restored AND blocked_target_operable。
- C_a11y = C_tech AND focus_restored；spoken_context_consistent 仅在朗读可观测时加入。若焦点不可观测，C_a11y 与 A-VTR 必须为 not_observable，除非有合规的目标用户验证。
- T = task_postcondition_satisfied。
- verified_technical_task_recovery = D AND C_tech AND T。
- accessible_verified_task_recovery = D AND C_a11y AND T，绝不由 VTR-tech 推断。
- no-popup 负样本发生任何无必要动作时，必须进入 false_intervention 判定。
- 敏感、破坏性、正向授权或未知动作不得由 VLM 直接决定；安全信息不全时默认 abstain。

## Provenance 与因果标签审计

- 每个 normalized candidate 都必须带 field_presence_mask、field_provenance 和 raw_ref。
- 黑盒观察不到独立节点时只能标 not_separately_exposed。merged_confirmed、filtered_confirmed、developer_defect_confirmed 等因果标签必须有 fixture、参考树或源码证据。
- episode 级 evidence_level 区分 target_device_verified、target_user_validated、fixture_verified、framework_only、pending_capability_probe 和 unverified。
- 每个缺失字段必须由 observability.field_status 给出 not_observable、not_collected、not_applicable、tool_failure 或 pending_capability_probe；禁止无语义 null。

## 尚未由本字段清单证明的事项

- 未证明任何 iOS/VoiceOver 焦点、朗读或闭环能力已经可用。
- 未证明 D/C_tech/T 或 D/C_a11y/T 已在任何平台跑通。
- 未证明方法优于 tree-only、always-on fusion 或其他基线。
- 未证明真实视障用户体验改善；没有目标用户研究时只能报告技术结果与可观测的 AT 子指标。

## 建议的 schema 落地检查

- 对 our_method_fields.json 做 JSON 解析和字段键完整性检查。
- 实际 episode schema 应把所有 nullable 结果改为 value 加 missing reason，或由 observability.field_status 统一约束。
- 训练/测试切分前冻结 scorer_version、calibration_version、tau、delta、policy version 和 retry budget。
- iOS schema 冻结前先运行目标设备 capability probe，并把证据写入 capability_profile.evidence_refs。
