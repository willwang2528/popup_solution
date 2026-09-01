# V1 查新证据包：移动弹窗存在与消息判断

**检索日期**：2026-09-01
**范围**：移动端、视障／屏幕阅读器、弹窗存在与可见消息判断；V1 不执行点击、关闭或 Recovery。
**对象**：cross-family jury 排名前三的研究主线：缺口普查、四族同预算对照、消息槽覆盖门。
**状态**：供独立 novelty reviewer 复核；不是“第一个”或性能结论。

## 1. 需要查新的核心主张

1. **问题主张**：移动弹窗的屏幕可见消息与屏幕阅读器可获得结构之间存在可测的 observability gap。
2. **数据主张**：公开 item 同步保存 screenshot、平台原始结构、规范字段、人工弹窗存在／消息／关键事实 gold 和 gap taxonomy。
3. **评测主张**：在同一冻结 observation 上比较 structure-only、vision-only、always-on fusion、gap-gated fusion，并约束视觉调用、像素和延迟预算。
4. **方法主张**：只用结构证据计算 message-slot sufficiency，并仅在不足时调用视觉；与 empty-tree、random-K 和 always-on 对照。

## 2. 直接反例与最近邻

| 工作 | 已核实内容 | 对本项目的影响 |
|---|---|---|
| [Pop-Up Focus Functional Specification (2021)](https://home.cs.colorado.edu/~DrG/Microsoft-SCOPE-2021/pop-ups.html) | 基于屏幕阅读器用户调研，明确提出识别 Web pop-up，并告知存在、类型、退出机制；还给出数据采集与标签设计 | **直接否定“第一个提出弹窗对屏幕阅读器用户造成阻断／需要检测”**。差异仅可落在原生移动端、消息 gold、结构—像素 gap 与正式实验 |
| [Help-Seeking Situations Related to Visual Interactions on Mobile Platforms (2024)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11355365/) | 记录移动端视障用户在多窗口／弹窗中因 screen-reader focus 未被限制而误解当前状态 | 再次否定“第一个发现移动弹窗无障碍问题”；支持问题动机但不是自动 benchmark |
| [A11yPuppetry, CHI 2023](https://doi.org/10.1145/3544548.3580679) | 使用 TalkBack record-and-replay 检测移动 accessibility 问题；论文明确讨论节点分组、不可聚焦元素和屏幕变化不易被盲人察觉 | 与“真实屏幕阅读器行为不能由静态 checker 完全替代”高度重叠；本项目必须说明 V1 只评消息 observability，而非通用可访问性测试 |
| [Screen Recognition, CHI 2021](https://arxiv.org/abs/2101.04893) | 从 77,637 个 iPhone screen 的像素生成 accessibility metadata，并通过 9 名 screen-reader users 验证 | 直接覆盖“结构不足时用视觉补元数据”；本项目不能把视觉兜底本身当创新 |
| [ScreenAudit, CHI 2025](https://arxiv.org/abs/2504.02110) | 遍历移动屏幕、抽取 metadata 与 screen-reader transcripts，用 LLM 找传统 checker 漏掉的问题；6 名专家评估 14 个 screen | 最接近“结构／朗读差异测量”；本项目的可能 delta 是 popup-message item、人工消息与关键事实 gold、结构—像素 gap taxonomy 和同预算方法对照 |
| [Bridging the Gap Between Automated Intervention and Actual User Experience, CHI 2026](https://doi.org/10.1145/3772318.3791293) | 系统综述 31 篇移动 screen-reader 自动干预论文，并以 4 个 Android App、20 次盲人用户研究构建 MCAG；归纳 22 类 labeling／navigation／activation／dynamic-change 问题及用户影响 | 强化“移动无障碍问题与自动检测之间的 gap 已被系统研究”；本项目只能收窄到 popup-message observation 与 paired benchmark，不能声称首次建立移动 screen-reader issue taxonomy |
| [Insight (2026 preprint)](https://arxiv.org/abs/2605.09803) | Android accessibility service 为 BVI 用户提供自然语言屏幕摘要并与 TalkBack 做用户实验 | 邻近“把屏幕内容变为自然语言消息”；但不是 popup-specific benchmark 或结构—视觉 gate |
| [MCP-Driven Accessibility Tree Standardization (2026 preprint)](https://arxiv.org/abs/2608.24898) | 讨论跨平台 accessibility API schema、截图与树的语义／延迟权衡；没有经验实现 | 否定“跨平台结构标准化从未提出”；未解决平台从未暴露的可见消息，也没有 popup experiment |
| [WhisperTest, CCS 2025](https://doi.org/10.1145/3719027.3765183) | iOS 采集 screenshot、accessibility dump、OCR／OmniParser；论文展示 ATT prompt 的 a11y 与 OCR 表示 | 直接覆盖 iOS 多模态采集与感知级联；本项目 delta 必须是 message gold、gap 判定和固定预算评测，而不是采集三种表示 |
| [VLM-Fuzz, EMSE 2026](https://doi.org/10.1007/s10664-026-10816-4) | 结合 Android GUI hierarchy 与按需 VLM，按组件复杂度分配测试预算 | 直接覆盖 on-demand VLM／预算分配的机制邻域；本项目必须证明 message sufficiency gate 与 GUI testing heuristic 不同 |
| [AndroidWorld (2024)](https://arxiv.org/abs/2405.14573) | observation 同时包含 screenshot 与 accessibility tree，并处理异步 UI 状态稳定 | 支持树图同步、同 observation 评测；任务是 agent action，不是屏幕阅读器消息 |
| [Abra Mobile Accessibility Snapshots (2025)](https://abra.ai/blog/capture-android-and-ios-accessibility-hierarchy-using-abra-snapshots) | 产品工具已能在 Android／iOS 第三方 App 上同步查看 screenshot、hierarchy 与节点属性，并直接观察节点合并问题 | 进一步否定“跨平台同步采集 screenshot + tree”本身的新颖性；研究 delta 必须是公开 popup-message gold、协议与结果 |
| [The OK Is Not Enough, USENIX Security 2023](https://www.usenix.org/conference/usenixsecurity23/presentation/koch) | 跨 Android／iOS 检测并分析移动 consent dialogs，抽取对话结构并比较选择 | 对消息槽和跨平台 popup 结构构成最近邻；局限在 privacy consent，不评屏幕阅读器可见消息 gap |
| [TCF A(A)ID (2026 preprint)](https://arxiv.org/abs/2602.20222) | 自动识别、交互并评估 Android TCF banners 及选择持久化 | 覆盖 consent banner 自动化与业务状态，但超出 V1；不能作为消息可访问性 gold |

## 3. 最近六个月检查

2026-03-01 至 2026-09-01 的定向查询命中：

- CHI 2026 mixed-method study：31 篇自动干预 SLR + 20 次盲人用户研究 + MCAG；
- Insight（2026-05）：Android BVI screen summarization；
- MCP-Driven Accessibility Tree Standardization（2026-07）：跨平台树 schema 与 tree/screenshot trade-off；
- VLM-Fuzz version of record（2026-02，略早于六个月边界但仍纳入）：按需 VLM + hierarchy；
- TCF A(A)ID（2026-02，略早于边界但纳入）：Android consent banner 自动化；
- 未检索到同时公开“原生移动 popup screenshot + 原始 accessibility tree + 双人 message/critical-fact gold + gap taxonomy + four-family equal-budget results”的论文或数据集。

补充检索 ASSETS 2024–2026、W4A 2024–2026 以及 `modal`／`overlay`／`dialog` 同义词后，没有检索到上述 exact combination；但命中 CHI 2026 的系统综述与 Abra 的跨平台 snapshot 产品，说明通用 issue taxonomy 和 screenshot+tree 采集均已有直接先例。

最后一句只表示本轮查询未命中 exact combination，不证明全球首创。

## 4. 查询记录（代表性）

每一核心主张至少使用三种措辞，并检查 arXiv、ACM／作者 PDF、USENIX／官方项目页：

1. `mobile popup accessibility tree screen reader visible message benchmark 2024 2025 2026`
2. `mobile screen reader popup dialog accessibility tree missing text`
3. `mobile UI screenshot accessibility metadata screen reader transcript benchmark`
4. `mobile GUI accessibility tree screenshot conditional VLM invocation gate`
5. `accessibility tree screenshot fusion mobile UI benchmark cost latency`
6. `mobile GUI agent accessibility tree screenshot fusion conditional visual`
7. `mobile consent dialog semantic fields popup message accessibility tree`
8. `mobile popup message screen reader critical information negation consequence`
9. `accessibility tree missing popup text mobile screenshot OCR message`
10. `pop-up screen reader unable to detect dataset algorithm`
11. `mobile GUI accessibility tree visual fallback gated fusion popup message`（最近 184 天）
12. `Android iOS popup message accessibility dataset blind users`（最近 184 天）

## 5. 执行者的 provisional 结论

| 主张 | 初步 novelty risk | 当前可用表述 |
|---|---|---|
| 第一个提出弹窗对屏幕阅读器用户造成问题 | **LOW / 已有直接反例** | 删除“第一个”；写为已有 Web 和移动 accessibility 研究记录了该问题，本工作把它操作化为 popup-message observability benchmark |
| 第一个公开移动 popup-message gap 数据集 | **MEDIUM** | 只能写“本轮未找到 exact combination”；待来源／许可／人工 gold／公开发布完成后再判断 |
| 四族同预算 popup-message 对照 | **MEDIUM** | 按需视觉、tree+pixel 和预算分配均有先例；潜在 delta 是屏幕阅读器 popup-message 任务、同 observation 与多预算口径 |
| message-slot sufficiency gate | **LOW–MEDIUM** | consent-dialog 字段抽取和简单级联是强先例；应先作为可证伪 gate proposal／消融，不作为已证实的新方法 |
| 改善视障用户体验 | **无当前证据** | V1 不主张；必须另做目标用户研究 |

## 6. 给独立 reviewer 的问题

1. 上述 direct collision 是否足以判定“第一个提出背景／问题”为不可用？
2. 数据集 exact combination 是否仍有可辩护的特定 delta，还是 ScreenAudit／A11yPuppetry 已实质覆盖？
3. 四族同预算比较的贡献更像 benchmark protocol、经验 finding，还是 method？
4. message-slot gate 是否因 The OK Is Not Enough／consent-slot parsing 与 VLM-Fuzz 的按需视觉而只剩工程组合？
5. 最安全的论文定位、kill condition 与查新残余风险是什么？
