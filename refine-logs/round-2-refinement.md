# Round 2 Refinement：PMAB-Android

## Problem Anchor

- **Bottom-line problem**：依赖 TalkBack 的视障人士遇到移动弹窗时，屏幕上可见的消息可能没有完整暴露在 Android 可访问性表示中；V1 只测“是否有目标弹窗、弹窗可见消息是什么”。
- **Must-solve bottleneck**：结构非空仍可能缺失、合并、污染、错序、过期或与像素矛盾，因此 tree-only 不能保证重建可见消息。
- **Non-goals**：点击、关闭、接受／拒绝、焦点／页面／任务 Recovery、CAPTCHA／风控／认证／支付／权限安全控制、用户体验改善主张、跨平台外推。
- **Success condition**：在真实同步 Android screenshot + accessibility representation 上建立可审计 message gold 与 structure-sufficiency audit，并完成同 observation、同 backbone、同预算的强基线比较；结果允许为正、零或负。

## Anchor Check

- 原始瓶颈仍是“可见消息与辅助技术可获得结构之间的可观测缺口”，没有转成通用 popup detector、UI automation 或 Recovery。
- 接受外部 reviewer 对 source mismatch、RICO 非 AccessibilityNodeInfo、popup 边界不足和零实证的批评。
- 不接受把“可关闭性”作为截图 presence gold 的必要条件：单张截图无法可靠观察 dismissibility，强行要求会把隐藏动作推断污染 presence gold。
- 不接受把 VPMA 改成可调权重的复合分数；VPMA 保持预注册布尔合取，分项指标单独报告。
- 不接受“没有目标用户就无法做事实转录 gold”的绝对说法；但若论文声称消息对屏幕阅读器用户充分／有用，必须另做 BVI 用户验证。V1 默认不做 UX claim。

## Simplicity Check

- **Dominant contribution**：PMAB-Android，一个 popup-message measurement benchmark。
- **Supporting contribution**：三种输入族在匹配预算下的经验比较；gap gate 只是一种 engineering allocation policy。
- **删除／降级**：iOS 主张、跨平台 benchmark、通用 taxonomy、视觉兜底新颖性、gate 算法新颖性、Recovery。
- **冻结复用**：现有 OCR／VLM backbone；不训练新视觉模型。
- **硬门**：PopSweeper／RICO 只做 annotation/infrastructure pilot；没有真实同步 Android accessibility capture 就不启动论文主实验。

## Changes Made

### 1. 数据锚从 PopSweeper/RICO 转为真实 Android accessibility observation

- PopSweeper 的 `ads/no_ads` 不再视为 popup label，只用于盲标协议与来源适配 pilot。
- RICO semantic hierarchy 不再被称为 AccessibilityNodeInfo 或 TalkBack 表示。
- 正式 PMAB-Android item 必须来自受控开源 App／可重放 fixture／获授权真实 App，并同步保存 screenshot 与 Android accessibility representation。
- 若无法获得至少 100 个跨 App／template 的真实同步 item，主 benchmark claim 停止；不能用 RICO 补位。

### 2. 弹窗范围已机器可读化

`dataset-v1/annotation-pilot/POPUP_SCOPE_V1.json` 冻结以下截图可观察定义：

> 弹窗是与宿主内容视觉可分离、不是稳定导航或内联宿主内容，并且明显覆盖、遮挡、门控或打断当前宿主上下文的消息界面。

三个可观察条件必须同时成立。纳入 modal dialog、alert、interstitial、阻断式 banner、打断式 bottom sheet、全屏 gate；排除稳定页面／导航、drawer、menu、toast/snackbar、内联错误、键盘和媒体控制 overlay。安全敏感类另标 out-of-scope。无法消除边界歧义时标 `uncertain`，不推断 dismissibility。

### 3. Gold 与 gap audit 分离

- Stage G1：A/B 仅看截图，独立标 presence、visible message、critical facts；第三人重查所有 item 后裁决。
- Stage G2：G1 冻结后，另一组审计者只看结构 + 冻结 gold，标 `structured_message_complete_gt`、缺失事实、污染、错序、过期与矛盾。
- G1 标注者看不到 source label、结构、OCR、模型输出；G2 审计者看不到方法预测。
- 方法开发只用 train/dev，test gold 只在一次正式评分时解锁。
- 这避免用 MG-PU 自己定义 gap，也避免让结构内容反向改写可见消息 gold。

### 4. 用户证据口径收紧

- sighted/method-blind annotators只能建立“截图可见事实”gold，不能证明消息对视障用户充分。
- 技术 benchmark 的主张限定为 factual presence/message correctness，不写 user utility。
- 若目标 venue 需要人本贡献，增加一个独立、非动作的 BVI message-adequacy validation 子研究；它只判断消息是否足以理解弹窗，不涉及点击或 Recovery。
- 未做该子研究时，`eligible_for_user_experience_claim=false`。

## Revised Proposal

### Title

**PMAB-Android: A Benchmark for Popup Message Judgment from Accessibility Observations**

### Research question

在真实、同步的 Android screenshot 与 accessibility representation 上：

1. 有多少视觉上可见的 popup message 无法由结构完整重建？
2. structure-only、vision-only 和 structure+vision 在 presence、critical-fact correctness、hallucination 与成本上如何比较？
3. 一个只依据结构充分性分配视觉预算的简单 gate，是否比 always-on、empty-tree 和 random-K 更好；如果不好，何时 structure-only 或 vision-only 足够？

### Item contract

每个正式 item 必须包含：

- immutable `item_id`、source/app/template group、license/release class；
- Android device／OS／app／locale／capture tool version；
- 同一稳定状态的 screenshot hash、capture timestamp、state fingerprint；
- 原始 Android accessibility representation 与采集错误；
- 公共规范字段，但保留 raw provenance；
- G1 popup presence/message/critical-fact gold；
- G2 structure-sufficiency/gap audit；
- split/group、prediction、cost 与 eligibility；
- `action_attempts=[]`，所有 Recovery 字段为 null/not-applicable。

### Minimum viable data

正式规模由 pilot 方差与 group structure 决定，不把 reviewer 的 200 当无依据常数。启动门：

- 至少 100 个真实同步 Android item；
- 至少 5 个 App/source groups 与 3 个 popup template families；
- 正负样本和边界样本均存在；
- 每个 test group 与 train/dev 在 App/template/near-duplicate 上隔离；
- 先做 30-item 协议 pilot；presence κ、message／slot agreement 与 uncertain cap 通过后再扩展；
- 真实 non-synthetic gap positives 至少 20 个且不由单一 group 贡献；
- 许可／隐私／EXIF／redaction 与 public release class 逐 item 可审计。

若这些门未过，PMAB 只保留 capability pilot，不写 benchmark paper。

### Compared families

核心只保留三族：

1. **Structure-only**：规则 flatten + 同一冻结语言 backbone；
2. **Vision-only**：OCR-only 与 screenshot-only frozen VLM；
3. **Fusion/allocation**：always-on、empty-tree gate、random-K、message-sufficiency gate。

同一 backbone 的比较共享系统 prompt、输出 schema、temperature、max tokens、retry policy、timeout、OCR version 与解析器。不同模态固有的输入适配单独公开，不伪称 prompt 字符串完全相同。

### Budget parity

每个预算点同时冻结并报告：

- visual calls/item；
- decoded pixels/item；
- input/output tokens；
- retry count与失败处理；
- wall-clock p50/p95；
- API／compute cost；
- abstention policy。

always-on 在其自然预算上报告；在 matched-K 分析中，所有条件视觉策略用同一 K 或同一像素／成本上限。主比较优先报告 quality–coverage–cost Pareto，而不是只匹配“调用次数”。

### Metrics

- Presence Macro-F1；
- Critical-fact precision／recall；
- Critical hallucination rate；
- message semantic correctness；
- coverage／selective risk；
- VPMA：positive item 上为 `presence_correct AND message_semantically_correct AND NOT critical_hallucination`；negative item 为 `presence_correct`；
- visual-call／pixel／token／latency／cost。

VPMA 不加可调权重。字符串 Exact／Character F1 只作辅助。

### Core experiment blocks

**B0 Data validity**：真实同步 capture、来源分布、许可、G1 IAA、G2 agreement、gap prevalence。
**B1 Strong family comparison**：structure-only vs vision-only vs always-on，在冻结 test 上给出质量—成本基线。
**B2 Allocation isolation**：message-sufficiency gate vs empty-tree vs random-K，在同预算点做配对比较。
**B3 Failure/negative analysis**：按真实 gap tier、popup type、App/template、message complexity 分析，并预注册四种叙事出口。

不为追逐正结果增加更多模型或模块。

### Outcome-to-claim matrix

| 结果 | 可主张 | 不可主张 |
|---|---|---|
| gate 在同预算显著优于 strongest baseline，hallucination/coverage 不恶化 | PMAB measurement + conditional allocation 的经验收益 | 新 VLM、UX 改善、Recovery |
| null | PMAB + “在本数据范围内 gate 无额外收益” | 方法 superiority |
| vision-only 胜 | PMAB + “当前结构不足，vision-first 更强” | structure-first/gate superiority |
| structure-only 近 ceiling，gap <10% | PMAB/progress measurement 或短论文；何时结构足够 | 高影响方法贡献 |
| gap 仅单一 source／synthetic | capability case study | 独立 benchmark |
| G1/G2 agreement 失败 | 协议失败报告 | gold、benchmark、方法结果 |

### Stop conditions

- 无真实同步 AccessibilityNodeInfo/AccessibilityService capture：停止主实验；
- G1 presence κ <0.70，经过两次预先编号的协议修订仍失败：停止 benchmark；
- G2 structure-sufficiency agreement <0.70：不能把 gap 当 gold，只能做消息数据；
- 真实 gap positives <20 或 gap prevalence <10%：停止方法贡献，转 structure-sufficiency measurement；
- gate 相对 strongest baseline <2 VPMA points，或 CI 跨 0 且无 Pareto 优势：停止方法 superiority；
- 增益来自额外像素／tokens／retries／更低 coverage：主比较无效；
- 许可或隐私门未过：不公开对应 media／gold；
- iOS 未就绪：标题、数据和结论保持 Android-only。

### Current evidence status

- schema/crosswalk、source adaptation、annotation bundle、pre-gold code：工程基础；
- PopSweeper/RICO 30-item：协议与媒体 QA pilot；
- 正式 PMAB-Android empirical item：0；
- 人工 gold：0；
- 正式 baseline result：0；
- 当前结论：`REVISE / pre-empirical`，任何“better/first/released benchmark”主张都未获得。
