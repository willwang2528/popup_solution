# Dataset Card

## 名称与版本

- 名称：`Popup Episode Union Dataset`
- schema：`1.0.0-provisional`
- 目标人群：使用 TalkBack、VoiceOver 等屏幕阅读器的盲人及低视力用户
- 平台：Android、iOS、mobile Web
- 当前状态：字段并集、crosswalk、schema、QA 与采集模板已产出；真实设备数据尚待采集，schema 待 capability pilot 后冻结

## 研究问题

结构化可访问性表示可能非空，却仍无法提供语义明确、可执行、owner/context 正确的低风险退出路径。本数据集用于测量这种 `accessibility actionability gap`，并评估结构优先、按需视觉补全的方法能否安全恢复原任务。

## 范围

自动处理普通、低风险、可合法退出的弹窗，例如 `close`、`cancel`、`later`、`skip`、`acknowledge`，以及经过预验证的 `back` 或 `outside_tap`。

以下样本只能标注为 `abstain/handoff`，不能作为自主执行成功：CAPTCHA、风控、PIN、生物识别、身份认证、支付、安装、删除、设备管理、正向隐私/权限授权，以及语义未知的敏感动作。

## 数据单元

每个 item 是一条 episode，不是一张截图：

```text
scenario + environment + assistive technology
+ synchronized observations
+ structured / visual / protocol candidates
+ gate and policy decision
+ real action attempts
+ dismissal, context, accessibility and task verification
```

## 字段来源

- 既有方法侧：PPT 中 14 篇工作；其中 6 篇为 core experimental seed，8 篇仅提供 schema/method reference。
- 我方方法侧：任务上下文、gold action set、actionability gap、candidate ranking、owner consistency、安全策略、selective vision、abstention、`D/C_tech/C_a11y/T` 与成本指标。
- 严格论文并集当前只有 Android 与 mobile Web 闭环；iOS 原始字段需 capability probe 后再冻结。

字段来源通过 `schema/field_catalog.json` 与 `provenance/paper_method_coverage.json` 审计。字段可进入 schema 不代表相应论文已经验证完整任务恢复。

当前字段账本包含 90 个论文侧原子字段与 165 个我方方法字段，共 255 条 source-field 记录；同义语义通过 `schema/source_to_item_crosswalk.json` 映射到 canonical item，平台 raw 字段不因规范化而删除。

## 采样与 Randomization × N

正式采集按下列层分层：

```text
platform × popup_owner × popup_kind × exposure_tier × action_topology
```

每个 scenario 对所有方法做配对运行，运行前恢复相同设备快照和 App 状态。可控扰动包括 locale、主题、方向、字体缩放、按钮顺序、视觉样式和异步延迟。

`N` 由 capability pilot 的失败率、方差和功效分析决定；当前不凭经验任意填写。

## Split 防泄漏

按以下 group 联合约束划分：

- `scenario_group_id`
- `app_group_id`
- `popup_template_group_id`
- `sdk_or_cmp_group_id`
- `os_family_group_id`
- `near_duplicate_group_id`

任意一个 group 相同的 item 不得跨 train/validation/test。帧、动作尝试和 relaunch 观察必须跟随 episode 所属 split。

## 主标签与指标

```text
D = visual_popup_gone ∧ semantic_popup_gone
C_tech = owner_context_restored ∧ blocked_target_operable
C_a11y = C_tech ∧ focus_restored ∧ spoken_context_consistent（若可观测）
T = task_postcondition_satisfied
VTR-tech = D ∧ C_tech ∧ T
A-VTR = D ∧ C_a11y ∧ T
```

同时报告 valid-action recall、False Intervention、Harmful Action、abstention/coverage、视觉调用率、动作次数、恢复时延和额外屏幕阅读器导航步数。

## 缺失与不可观测

不使用一个无语义的 `null` 统一表示缺失。每个关键对象包含 `presence`：

```text
observed | derived | annotated | not_available | not_applicable
| not_observable | collection_failed | redacted | unknown
```

黑盒树中没有控件时只能标注可观察缺口；只有 fixture、参考树、源码或平台证据充分时，才可归因为 framework merge、platform filtering 或 developer defect。

## 隐私、授权与发布

正式发布前必须：确认 App/截图/树/日志的采集和再分发权利；移除账号、通知、输入内容和设备标识等个人数据；对语音或目标用户记录完成伦理、知情同意和可访问性审查。无法合法公开的原始 artifact 只发布派生标签或受控访问版本。

## 已知限制

- 当前只有 schema fixture，没有真实 episode 规模与统计结果。
- 当前 QA 契约的 29 个门中仅 5 个完整自动化、17 个部分自动化、7 个需人工或发布流程检查；验证器 pass 不是完整发布验收。
- XCTest/Appium 可读取字段不等同于 VoiceOver 用户实际焦点和朗读内容。
- 自动化焦点日志不能替代真实视障用户实验。
- 既有论文的弱视觉/日志变化指标被保留为 baseline signal，但不能直接生成 A-VTR 真值。
