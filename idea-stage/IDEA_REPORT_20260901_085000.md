# 移动弹窗消息可访问性：Idea Discovery Report

**Direction**：面向依赖 TalkBack／VoiceOver 的视障人士，研究移动弹窗可见消息与结构化可访问性表示之间的缺口；V1 只判断弹窗存在与消息，不执行关闭或 Recovery。
**Generated**：2026-09-01
**Pipeline**：`research-lit → idea-creator → novelty-check → research-review → research-refine-pipeline`
**Current phase**：Phase 4 独立 cross-family critical review 与 Phase 4.5 refine／experiment plan 已完成；结论为 `PROCEED_WITH_CAUTION`、fatal design flaws=0、readiness=3.5/5。Phase 5 真实同步 Android feasibility/G1/G2 pilot 尚未执行。所有性能主张均为 `not_yet_tested`，数据集 novelty 仅为 `LOW-MEDIUM / provisional`。

## 问题锚点与证据边界

PPT 第 14 页把“弹窗标识消失”和“截图／日志变化”列为弱回证；原目标与 Context、业务持久化、原任务后置条件才是更强回证。因此 V1 不挑战统一弹窗解决器，也不把消息判断写成 Recovery。没有进入 UI／可访问性树的内容，tree-only 方法原则上不可读；视觉只能扩展对屏幕像素的可观察范围，不能证明用户意图、业务状态或原任务恢复。

## Phase 1：文献图谱

### A. 弹窗识别、解除与自动探索

| 工作 | 输入与输出 | 对本研究的作用 | 不能支持的主张 |
|---|---|---|---|
| PopSweeper | 视频帧变化、图像分类、close-button 检测与坐标 | 提供 app-blocking popup 图像来源和视觉检测强邻近基线 | 不输出 popup 消息、可访问性暴露缺口或屏幕阅读器结果；公开资产不足以 exact 复现 |
| Poker / Sneaky Pop-ups | screenshot、XML、几何与探索；收集并解除 popup | 支持 popup 类型、视觉范围与真实 App 采样 | 研究目标是 sneaky pattern，不是结构—可见消息差 |
| VLM-Fuzz | UI hierarchy、Activity/Manifest、按需 VLM 与动作 | 支持按需视觉、owner/context 和探索特征 | 指标是 GUI testing coverage，不是消息可访问性 |
| DiOS / iOS Testing / WhisperTest | iOS UI 自动化、AccessibilityAudit、截图/OCR/OmniParser、Voice Control | 支持 iOS 原始字段、感知级联和平台限制 | Voice Control 不等于 VoiceOver；画面变化不等于 Recovery |

### B. 同意弹窗、广告与业务状态

| 工作 | 输入与输出 | 对本研究的作用 | 边界 |
|---|---|---|---|
| The OK Is Not Enough | Appium 文本与规则识别 consent dialog/choice | 可形成 structure-text baseline 和文本字段 | 研究的是 consent/dark pattern，不是通用 popup message gap |
| Freely Given Consent | screenshot OCR、词表、聚类 | 可形成 OCR-only 消息基线 | 不能替代 popup presence、owner 或 screen-reader message gold |
| TCF A(A)ID / Abandon All Hope | banner 选择、持久化与网络行为 | 为进阶业务回证提供字段 | 超出 V1，只能保留兼容字段 |
| Cookieverse / BannerClick | DOM、iframe、ShadowDOM、词表与按钮操作 | 提供 mobile-web DOM 表示和 banner baseline | Web banner 不能直接外推原生 Android／iOS |
| HotMobile ad policy / SSLDetecter | UI state graph、widget tree、规则与自动遍历 | 提供结构状态、页面范围与规则字段 | 不是屏幕阅读器或消息质量评测 |

### C. 屏幕阅读器与像素补全邻近工作

| 工作 | 已有结论 | 与本研究的关系 |
|---|---|---|
| ScreenAudit (2025) | 用移动屏幕元数据和 screen-reader transcript 发现传统 checker 漏掉的问题 | 最接近“结构信息不足时评估实际朗读”，但不是 popup-message benchmark |
| Screen Recognition (2021) | 从像素推断移动 UI 的 accessibility metadata，并做屏幕阅读器用户研究 | 证明视觉可补充未暴露 accessibility metadata；任务粒度不是 popup 消息与关键事实 |
| Accessibility first (2024) | 视障用户实验记录 modal 打开后焦点仍停留在底层页面等障碍 | 直接支持问题动机，但不是自动数据集或方法对比 |
| MCP-Driven Accessibility Tree Standardization (2026 preprint) | 尝试统一异构 accessibility tree 传输与 schema | 支持跨平台规范层的必要性；标准化不会恢复平台从未暴露的事实 |

### D. 现有研究留下的结构性空位

截至本轮检索，没有已核实工作同时满足以下四项：

1. 研究对象是移动弹窗在屏幕上可见、但对屏幕阅读器结构化表示缺失／合并／矛盾的消息；
2. item 同步保存 screenshot、平台原始结构、规范字段、消息真值、关键事实和 gap 真值；
3. 比较 structure-only、vision-only、always-on fusion 与 gap-gated fusion；
4. 用消息正确性、关键事实召回、关键编造、coverage 与视觉成本做同预算配对评测。

这只是查新候选空位，不足以证明“第一个”。最接近的反例族是 ScreenAudit、Screen Recognition、PopSweeper、WhisperTest 和移动 consent-dialog 测量；后续 novelty check 必须逐项说明差异，且需要检索最近 3–6 个月并保存查询范围。

## 数据与工程现状

- PPT 边界内 14 篇记录已完成结构化采集；14/14 现有公开主来源，逐字段证据等级未因补 URL 自动升级。
- 文献原子字段 90 个、已有方法／工程字段 165 个，共 255 个 item 合同字段；这是 schema coverage，不是 empirical dataset 规模。
- 120 个 PopSweeper real-source candidates 与 30-item pilot observation 已冻结；人工消息 gold 为 0。
- A1/A2/C3 有真实但未评分 pre-gold prediction；B1 有真实全屏 OCR，但 presence 全部 abstain。
- 正式 visual evidence bank、B2 exact、C1 equal-budget、Android controlled capture 与 iOS capture 均未解锁。

## 当前可证伪主张

| Claim | 最低可信证据 | 当前状态 |
|---|---|---|
| 移动 popup message observability gap 可测 | screenshot + 同步 structure + 双人消息 gold + 独立 gap audit | `not_yet_tested` |
| 公开 item union 可复现 | schema、field catalog、source crosswalk、公开来源与真实非空 item | 合同已就绪；empirical gold 未就绪 |
| MG-PU 在同预算下优于 strongest baseline | frozen split、同视觉 bank、同 backbone、paired cluster bootstrap | `not_yet_tested` |
| 改善视障用户体验 | 合规目标用户研究 | `out_of_current_evidence` |
| Recovery 成功 | 动作后 D/C/B/T 分层回证 | `out_of_v1` |

## Phase 2 入口

候选 idea 必须围绕同一个数据锚点展开，不生成“统一关闭所有弹窗”方向。可接受的候选贡献类型只有：

- popup-message observability gap 的诊断与公开 benchmark；
- message-sufficiency gate 的可证伪方法；
- 对结构／视觉何时互补、何时冲突的经验发现；
- 在固定消息任务上的成本—coverage—hallucination 分析。

Phase 2 将通过多 lens 只读生成候选；生成 shard 不排名，合并后先机械去重，再交独立 reviewer。尚无 pilot 结果时不得出现 “POSITIVE” 或 “recommended because it works”。

## 公开来源入口

- [WhisperTest, ACM CCS 2025](https://doi.org/10.1145/3719027.3765183)
- [The OK Is Not Enough, USENIX Security 2023](https://www.usenix.org/conference/usenixsecurity23/presentation/koch)
- [PopSweeper, arXiv:2412.02933](https://arxiv.org/abs/2412.02933)
- [Understanding the Sneaky Patterns of Pop-up Windows, arXiv:2505.12056](https://arxiv.org/abs/2505.12056)
- [VLM-Fuzz, Empirical Software Engineering 2026](https://link.springer.com/article/10.1007/s10664-026-10816-4)
- [ScreenAudit, arXiv:2504.02110](https://arxiv.org/abs/2504.02110)
- [Screen Recognition, arXiv:2101.04893](https://arxiv.org/abs/2101.04893)
- [Accessibility first, Universal Access in the Information Society](https://link.springer.com/article/10.1007/s10209-023-01053-3)
- [MCP-Driven Accessibility Tree Standardization, arXiv:2608.24898](https://arxiv.org/abs/2608.24898)

## Pipeline checklist

- [x] Phase 0：读取 `RESEARCH_BRIEF.md` 与 PPT 第 14 页
- [x] Phase 1：本地 14 篇 + 公开来源 + 相邻查新图谱
- [x] Phase 2：多 lens idea generation 与机械去重
- [x] Phase 3：逐 idea novelty check
- [x] Phase 4：独立 critical review
- [x] Phase 4.5：refine + experiment plan 更新
- [ ] Phase 5：只运行当前可解锁、预先定义成功门的 pilot
