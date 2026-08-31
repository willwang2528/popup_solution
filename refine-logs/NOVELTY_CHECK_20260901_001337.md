# Novelty Check：移动弹窗消息可访问性数据集与缺口门控方法

> 日期：2026-09-01
>
> 状态：`PROCEED WITH CAUTION`
>
> 校准：`none`；本次跨模型 Claude 审阅因外部披露授权边界被拒绝，以下为 Codex 同族、证据驱动的 provisional 结论。
>
> 搜索边界：截至 2026-09-01 的论文主页、出版社页面、作者 PDF／代码和官方数据页；覆盖 mobile popup、screen reader、accessibility metadata、screenshot + UI tree、popup benchmark 与视觉补全等关键词。搜索不到不能证明绝对“首次”。

## 1. 拟议工作

面向依赖 TalkBack／VoiceOver 的盲人和低视力用户，建立移动弹窗消息评测数据集：同一动作前状态保存 screenshot、平台结构化 UI／可访问性表示、可选屏幕阅读器输出、弹窗消息真值、关键事实和结构暴露缺口；在其上比较 structure-only、vision-only、always-on fusion 与 message-gap-gated 结构＋视觉方法。V1 不点击、不关闭、不声称任务恢复。

## 2. 核心查新命题

| 命题 | 当前新颖性 | 最近／最强重叠 | 暂定判断 |
|---|---:|---|---|
| C1：首次把移动弹窗对屏幕阅读器用户的“消息不可观测性”作为独立、可测问题 | 低—中 | CHI 2024 已明确记录用户被不可读 popup 困住；CHI 2026 已系统研究 mobile screen-reader accessibility issue 与用户体验；Screen Recognition 已把缺失 accessibility metadata 作为长期问题 | 不能写“首次提出移动无障碍问题”；只能查证更窄的“popup-message observability benchmark”是否首次 |
| C2：首个同时包含 popup-specific screenshot、平台结构树、消息／关键事实真值和暴露缺口标签的公开 benchmark | 中 | RICO／MobileViews 有 screenshot + hierarchy；PopSweeper 有 832 个 app-blocking popup 标注与公开数据；Screen Recognition 有 screenshot + UI/accessibility tree +视觉标注；ScreenAudit 有 TalkBack transcript 与 accessibility-error gold | 尚未发现四类证据在 popup-message 任务上的同一公开 benchmark，但必须继续核对数据许可、字段和 2026 新工作 |
| C3：只在结构消息缺失／合并／矛盾时调用视觉，并以消息语义与关键编造为主指标 | 低—中 | Screen Recognition 已从 pixels 自动补 accessibility metadata；WhisperTest 已组合 A11Y、OCR／OmniParser 与 VLM；ScreenAudit 已用 LLM 分析 TalkBack transcript | “结构＋视觉”本身不新；可能的新意只在 popup-specific gap gate、等预算选择性调用和 VPMA／coverage 的联合评估 |
| C4：以 PPT 第 14 页五级回证边界拆开弱消失证据与真正任务恢复 | 中（评测定位） | PopSweeper、WhisperTest 等多使用截图／日志或坐标命中；D-GARA 等显式任务后置条件更强 | 更像审计与评测贡献，不应冒充新的执行算法 |

## 3. 最接近的已有工作

| 工作 | 年份／场所 | 直接重叠 | 与本课题的关键差异 |
|---|---|---|---|
| Screen Recognition: Creating Accessibility Metadata for Mobile Applications from Pixels | CHI 2021 | 77,637 个 iPhone screens；screenshot、UI／accessibility tree、视觉标注；从 pixels 生成 VoiceOver 可用 metadata | 非 popup-specific；目标是通用 accessibility metadata generation，不以结构暴露缺口、popup message truth 或选择性视觉调用为主评测 |
| ScreenAudit: Detecting Screen Reader Accessibility Errors in Mobile Apps Using Large Language Models | CHI 2025 | TalkBack transcript、LLM accessibility error detection、专家 gold | 评估通用 screen-reader error，不是 popup screenshot-tree-message 配对，也不恢复 popup message |
| Bridging the Gap between Automated Intervention and Actual User Experience | CHI 2026 | 31 篇自动干预 SLR、20 次盲人用户研究、mobile screen-reader issue taxonomy | 很强的背景／问题先例；削弱“第一个提出背景”主张，但未见 popup-message benchmark 与本方法比较 |
| Help-Seeking Situations Related to Visual Interactions on Mobile Platforms | 2024 | 明确报告 screen reader 无法读取 popup、用户被困和多层窗口焦点问题 | 用户研究／设计建议，不是结构—视觉配对 benchmark |
| PopSweeper | 2024／arXiv | 72K+ RICO screens、87 apps、832 个 app-blocking popups；公开 Zenodo 数据 | 面向自动化测试的视觉检测／close-target 定位；不评估屏幕阅读器消息、结构树缺口或无动作消息恢复 |
| WhisperTest | CCS 2025 | iOS A11Y、OCR／OmniParser、VLM、真实设备采集；代码公开 | Voice Control 自动化与安全分析；不是 VoiceOver message benchmark，且弱回证不能证明任务恢复 |
| RICO | UIST 2017 | 66K+ Android screenshot + detailed view hierarchy | 通用 UI 数据，不是 popup/accessibility-message 标注；官方条款要求使用者承担 copyrighted screenshot 风险 |
| Pop-up Focus Functional Specification | 2021，非同行评审 web 规格 | 已提出识别 popup、通知屏幕阅读器用户其存在／类型／退出机制，并设想 ML dataset | Web 导航规格，不是移动原生 app benchmark；但说明“popup + screen reader + dataset”并非全新概念 |

## 4. 主证据

- Screen Recognition 论文与 Apple 研究页：
  - https://doi.org/10.1145/3411764.3445186
  - https://machinelearning.apple.com/research/mobile-applications-accessible
- ScreenAudit 官方作者 PDF：
  - https://faculty.washington.edu/wobbrock/pubs/chi-25.02.pdf
- CHI 2026 mixed-methods study：
  - https://doi.org/10.1145/3772318.3791293
- Help-seeking／不可访问 popup 用户证据：
  - https://pmc.ncbi.nlm.nih.gov/articles/PMC11355365/
- PopSweeper：
  - https://arxiv.org/abs/2412.02933
  - https://zenodo.org/records/13754620
- RICO 官方数据页与使用条款：
  - https://dev.interactionmining.org/archive/rico
  - https://dev.interactionmining.org/archive/rico/copyright.txt
- WhisperTest 作者代码：
  - https://github.com/iOSWhisperTest/whispertest
- Pop-up Focus 规格：
  - https://home.cs.colorado.edu/~DrG/Microsoft-SCOPE-2021/pop-ups.html

## 5. 许可与数据可用性核验

- PopSweeper Zenodo record `13754620`：
  - access：`open`
  - license：`CC-BY-4.0`
  - file：`app-blocking pop-ups_basic.zip`
  - size：`266010362`
  - MD5：`46a0fe5c4eeab2bd119aed800b7a81f3`
- RICO：
  - 官方提供 screenshot + detailed view hierarchy；
  - screenshot 可能含第三方 copyrighted work；
  - 可用于研究，但公开再分发必须遵循其 copyright notice，不能直接把全部源图复制进本仓库而忽略条款。

## 6. 总体判断

- **新颖性分数：5.5／10。**
- **建议：PROCEED WITH CAUTION。**
- 最可信的论文定位不是“第一个发现移动无障碍或缺失 metadata”，而是：
  1. **popup-specific measurement**：测量屏幕可见弹窗消息与平台暴露给屏幕阅读器的结构化表示之间的 gap；
  2. **public evaluation package**：公开 annotations、schema、split、评测器和可合法再分发的样本；对受原数据条款限制的源图提供 hash／ID／下载适配器；
  3. **selective fusion result**：检验 message-gap gate 是否在同预算下优于 structure-only、vision-only 与 always-on。
- 最大 prior-art 风险是 Screen Recognition：它已经证明“pixels 可补缺失 accessibility metadata”。本课题必须把贡献压缩到 **popup-message task、gap taxonomy、选择性调用、关键事实防编造和公开评测协议**。
- “第一个公开数据集”只有在正式查重、许可证审计、真实 item 发布和数据卡完成后才能写入摘要。
- “方法更好”只有在冻结 split、同预算 baseline、置信区间和 kill criteria 通过后才能写入论文。

## 7. 下一步查新门

1. 对 CHI 2026 SLR 的 31 篇论文逐篇检查是否存在 popup-specific dataset／message recovery；
2. 检查 Screen Recognition supplementary/data release 是否公开 popup 可筛选标注；
3. 检查 PopSweeper basic archive 的 ID、annotation 和 RICO joinability；
4. 对 2026-03 至 2026-09 arXiv/CHI/DIS/ASSETS 做一次提交前刷新；
5. 任何同构 benchmark 出现时，立即取消“first”并把贡献改为更严格的跨平台／screen-reader-message 评测。
