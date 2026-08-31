# v1 弹窗消息标注指南

## 1. 标注对象

一个标注对象是动作前 frozen observation。标注者只回答：

1. 当前是否存在目标范围内的弹窗？
2. 若存在，弹窗向用户表达了什么消息？
3. 哪些是不能遗漏或编造的关键事实？

不要点击、关闭或继续原任务。不要标注 D/C/T/VTR；这些属于 advanced profile。

## 2. 范围判定

纳入普通 App／系统／浏览器／WebView 弹窗。CAPTCHA、风控、身份认证、支付确认、权限安全控制、人工审核等标为 out-of-scope，不进入 v1 主指标。

`popup_present_gt=true` 需要有独立于宿主内容、打断或覆盖当前交互上下文的界面证据。单一通道没找到不能直接标成 no-popup。

无弹窗时：

```text
blocking_gt = null
message_text_gt = null
critical_facts_gt = []
message_text_observability = not_applicable
```

## 3. 消息转录

按用户合理阅读顺序转录 title、body、list/option、警告和理解所需的按钮文案。遵守：

- 忠实保留原语言，不翻译；
- Unicode 与空白可规范化，但不改写语义；
- 不删除否定词；
- 不改写金额、日期、单位、对象、条件、后果；
- 不补写截图／树中不可观察的应用意图；
- 宿主页面文本不得混入弹窗消息。

`complete` 表示可观察内容足以重建完整消息；`partial` 表示有可读片段但明显缺失；`not_observable` 表示无法可靠转录。

## 4. 关键事实

`critical_facts_gt[]` 使用简短、可比较的规范短语，覆盖会改变用户理解或决策的信息，例如：金额、日期／倒计时、操作对象、权限／数据对象、不可逆后果、否定或限制条件。

不要把普通修辞、品牌装饰或无关宿主文本列为关键事实。

## 5. Evidence

每个 presence/message gold 至少有一个动作前 evidence URI。文本片段应可追溯到 screenshot/OCR、accessibility tree、DOM 或经授权的屏幕阅读器 utterance。多通道冲突时保留各原始值并提交裁决，不能静默选择方便的一个。

负样本 evidence 应覆盖稳定后的完整屏幕／结构上下文。

## 6. Prediction 标注与裁决

模型 prediction 必须在 gold 解锁前持久化。标注者对其独立判断：

- `message_semantically_correct`：是否忠实表达弹窗核心消息；
- `critical_hallucination`：是否加入了会改变用户理解／决策的未证实关键内容；
- 关键事实集合用于重算 `critical_information_recall`。

正式 validation/test 至少两名标注者独立标注；分歧由第三人或预先指定 adjudicator 裁决。标注者不知道方法名称。

## 7. VPMA

```text
positive popup: presence_correct
                AND message_semantically_correct
                AND NOT critical_hallucination
no-popup:       presence_correct
abstain:        null, not success
```

字符串 Exact Match／Character F1 是辅助指标，不能替代语义与关键编造裁决。

## 8. Eligibility

进入 v1 presence/message 经验指标还需：real-app 或 controlled-fixture 来源、证据可解析、权限与隐私通过、冻结模型版本、无动作、split/group 检查通过。synthetic schema fixture 和 paper reconstruction 永远不进入经验指标。

`eligible_for_user_experience_claim` 在 v1 默认 false。即使消息判断正确，也不等于弹窗消失、焦点／页面／任务恢复或真实体验改善。

## 9. 质检清单

- [ ] prediction 来自动作前 observation；
- [ ] `action_attempts=[]`；
- [ ] presence 与 blocking/message 条件关系正确；
- [ ] 消息未混入宿主文本；
- [ ] 否定、金额、日期、对象、条件和后果已核对；
- [ ] evidence 可解析且 hash 一致；
- [ ] 双标与裁决完成；
- [ ] v1 D/C/T/VTR 均为 null；
- [ ] synthetic/real/target-user 证据没有混用。
