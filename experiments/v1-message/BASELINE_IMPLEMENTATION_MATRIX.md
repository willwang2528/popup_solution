# v1 基线实现与论文方法忠实性矩阵

冻结日期：2026-09-01

本表只回答“仓库目前究竟实现到了哪里”。`runnable` 仅表示工程链路能在冻结的 30-item pre-gold 输入上运行；它不等于论文方法级复现，也不等于已有可报告的实验结果。当前没有任何一篇论文方法已经完成正式复现，所有真实 30-item 输出都未使用人工 gold、未评分、不可写入论文主结果。

## 14 篇论文到 v1 的映射

| 论文方法 | 论文输入 → 输出 | v1 允许保留的零动作切片 | 对应 system | 当前硬状态 |
|---|---|---|---|---|
| WhisperTest | iOS A11Y + screenshot/OCR/OmniParser/VLM → Voice Control command、弱截图变化 | A11Y-first 感知级联，禁用动作 | C2；组件 B1/B3 | `interface-only`, `model-missing`, `out-of-v1` |
| Abandon All Hope | native View/WebView、checkbox、consent text → Accept/Reject、重启持久性 | native/WebView 消息与 checkbox 状态规则 | A2 variant | `source-missing`, `interface-only`, `out-of-v1` |
| The OK Is Not Enough | Appium text + privacy regex → notice/dialog 分类与按钮候选 | Appium text/regex message baseline | A2 | `runnable-paper-constrained-adaptation`；官方 `b618948` 规则已冻结；不复现动作/隐私合规研究 |
| Freely Given Consent | screenshot → OCR、privacy lexicon、TF-IDF/cluster → consent notice | OCR + 固定文本规则，禁用点击 | B1 + A2 variant | OCR 引擎 `runnable`；完整管线 `interface-only` |
| VLM-Fuzz | XML/Activity diff、几何、可选 VLM → transient popup、ADB event、host return | tree diff/owner/scope 特征 | A1 proxy | `interface-only`, `out-of-v1`；不能称为 MG-PU baseline |
| TCF A(A)ID | Appium tree + IABTCF + MiniLM → CMP 操作与持久选择 | MiniLM 文本候选匹配，禁用操作 | A2 semantic variant | `interface-only`, `model-missing`, `out-of-v1` |
| Cookieverse/BannerClick | DOM/iframe/z-index/多语词表 → banner/button、点击后截图 | DOM text/geometry banner detector | A2 DOM variant | `interface-only`, `source-missing`, `out-of-v1` |
| SSLDetecter | Activity/tree/geometry/text → overlay 类型与 Cancel/Close 规则 | 结构化 overlay/message 规则 | A1/A2 proxy | `source-missing`, `out-of-v1` |
| POKER | screenshot + YOLO box + shadow ratio + XML → popup/action box、dismiss 交互数 | popup detector + ROI OCR，禁用点击 | B2-family | `model-missing`, `interface-only`, `out-of-v1`；不等同 PopSweeper |
| PopSweeper | frame gate + ResNet50/MobileNetV2 → popup score；YOLO-World → close-button bbox/coordinate | popup classifier + full-screen OCR；若另造 popup ROI 必须标为本研究 adaptation | B2 exact target | **exact NO-GO**：仅数据源具备；代码、权重、阈值、时序帧、close-bbox 标注缺失，且论文不输出 popup ROI |
| Dynamic iOS Privacy | XCUI Alert/button label → OK/Allow tap | iOS Alert text-rule perception | A2 iOS variant | `source-missing`, `interface-only`, `out-of-v1` |
| HotMobile Ad Policy | View tree/state graph/geometry → ad state、Back destination | advertisement scope/结构消息特征 | A1 structured-state proxy | `interface-only`, `out-of-v1` |
| iOS Applications' Testing | UIAElement/frame → center-coordinate tap | raw element/frame | A1 raw-element proxy | `source-missing`, `out-of-v1` |
| DiOS | UI hierarchy + Alert callback/origin → handler/target label/tap | Alert owner、hierarchy、label 提取 | A1/A2 iOS proxy | `interface-only`, `out-of-v1`；原私有运行环境不可用 |

`out-of-v1` 表示论文的动作、dismissal、persistence、focus/page/task recovery 等输出超过本研究 v1 的“只判断 popup presence + message”边界，不是对原论文价值的否定。

## 当前可执行系统

| System | 30-item pre-gold 状态 | 不能宣称什么 |
|---|---|---|
| A1 structure-only | `runnable`；15 judged / 15 abstain | full-tree flatten 已与 pre-gold 对齐；无人工 gold、未评分 |
| A2 The OK text rule | `runnable`；10 judged rule-no-match / 20 raw-text-missing abstain | 官方文本规则已固定；matched-text message 是 v1 adaptation；无人工 gold、未评分 |
| B1 OCR-only | `runnable`；30/30 abstain | 当前是全屏 OCR，不是正式 popup-ROI baseline |
| C3 MG-PU candidate | `runnable`；2 项 structure、28 项 visual workflow candidate | visual candidate 精确模型身份不可复现；不是正式方法结果 |

A0、A3、B2、B3、C1、C2、C4 仍只有接口、计划或 synthetic smoke。A2 是 paper-constrained v1 adaptation，不是原论文完整系统复现。`always-visual` 只是路由消融，不等于 C1 always-on structure+vision fusion。统一视觉冻结协议已经定义，但当前状态仍为 `blocked_missing_reproducible_presence_roi_visual_bank`。

## 正式比较的解锁顺序

1. 完成真实 A/B 盲标，并由第三位真实 adjudicator 对全部 30 项输出 final；冻结 group-disjoint split。
2. 正式运行 A1、A2、B1；B1 使用无泄漏 popup scope。B2 只有在取得 PopSweeper 代码、权重、revision、frame gate、分类器阈值、时序帧与 close-button 标注后才能解锁 exact；自建 popup ROI 必须作为单独 adaptation。
3. 实现 C1；C1/C3 使用同一冻结 visual bank、backbone、分辨率和单次调用配置。真正 always-on 的 `C1-AO` 只用于 accuracy-cost frontier；与 MG-PU 匹配总调用数的控制必须命名为 `C1-BM`，不能称为 always-on。
4. 只有在同一 gold、同一输入资格和同一 evaluator 下，才运行 C3 对 dev-selected strongest deployable baseline 的主比较。

在以上条件完成前，本仓库只报告工程就绪度、abstention、visual-call routing 和可复现性缺口，不报告 accuracy、VPMA 或“优于已有方法”。

## 当前 post-gold 评分链

工程链已经能在真实人工输出到位后执行以下 fail-closed 步骤，但目前没有真人
gold，因此没有运行结果：

1. finalizer 要求 adjudication 与冻结 pilot item 严格一对一，拒绝重复、未知、
   缺失和夹带 final label 的 `cannot_resolve`；
2. gold 通过稳定 `pilot_item_id` 连接到 30-item pending-union 的私有结构特征；
3. A1、A2、MG-PU 直接评分 gold 前冻结的 prediction snapshot，不在 gold 解锁后
   重跑方法；
4. 可选消息语义复核绑定逐条 prediction SHA-256，并要求比较方法完整覆盖；
5. 独立、method-blind 的 structure–visual gap audit 绑定两个审计记录、message-gold batch 和 structured bundle hash，只用于分层分析；
6. paired scorer 使用显式私有 group-map、预声明 reference baseline 和确定性
   10,000 次 cluster bootstrap，并同时报告 VPMA、coverage、Presence Macro-F1、critical-information recall、critical-hallucination rate 与 visual-call rate 的配对差。

当前 pilot group-map 是 30 个 singleton cluster，仅能支撑 exploratory pipeline
检查，不能声称正式 near-duplicate/app/template leakage control。B1 popup-ROI、
B2 exact、C1 equal-budget 和可复现视觉模型身份仍是独立硬门。
