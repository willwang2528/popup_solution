# v1 基线实现与论文方法忠实性矩阵

冻结日期：2026-09-01

本表只回答“仓库目前究竟实现到了哪里”。`runnable` 仅表示工程链路能在冻结的 30-item pre-gold 输入上运行；它不等于论文方法级复现，也不等于已有可报告的实验结果。当前没有任何一篇论文方法已经完成正式复现，所有真实 30-item 输出都未使用人工 gold、未评分、不可写入论文主结果。

## 14 篇论文到 v1 的映射

| 论文方法 | 论文输入 → 输出 | v1 允许保留的零动作切片 | 对应 system | 当前硬状态 |
|---|---|---|---|---|
| WhisperTest | iOS A11Y + screenshot/OCR/OmniParser/VLM → Voice Control command、弱截图变化 | A11Y-first 感知级联，禁用动作 | C2；组件 B1/B3 | `interface-only`, `model-missing`, `out-of-v1` |
| Abandon All Hope | native View/WebView、checkbox、consent text → Accept/Reject、重启持久性 | native/WebView 消息与 checkbox 状态规则 | A2 variant | `source-missing`, `interface-only`, `out-of-v1` |
| The OK Is Not Enough | Appium text + privacy regex → notice/dialog 分类与按钮候选 | Appium text/regex message baseline | A2 | `interface-only`；论文实现未落地 |
| Freely Given Consent | screenshot → OCR、privacy lexicon、TF-IDF/cluster → consent notice | OCR + 固定文本规则，禁用点击 | B1 + A2 variant | OCR 引擎 `runnable`；完整管线 `interface-only` |
| VLM-Fuzz | XML/Activity diff、几何、可选 VLM → transient popup、ADB event、host return | tree diff/owner/scope 特征 | A1 proxy | `interface-only`, `out-of-v1`；不能称为 MG-PU baseline |
| TCF A(A)ID | Appium tree + IABTCF + MiniLM → CMP 操作与持久选择 | MiniLM 文本候选匹配，禁用操作 | A2 semantic variant | `interface-only`, `model-missing`, `out-of-v1` |
| Cookieverse/BannerClick | DOM/iframe/z-index/多语词表 → banner/button、点击后截图 | DOM text/geometry banner detector | A2 DOM variant | `interface-only`, `source-missing`, `out-of-v1` |
| SSLDetecter | Activity/tree/geometry/text → overlay 类型与 Cancel/Close 规则 | 结构化 overlay/message 规则 | A1/A2 proxy | `source-missing`, `out-of-v1` |
| POKER | screenshot + YOLO box + shadow ratio + XML → popup/action box、dismiss 交互数 | popup detector + ROI OCR，禁用点击 | B2-family | `model-missing`, `interface-only`, `out-of-v1`；不等同 PopSweeper |
| PopSweeper | frame gate + ResNet50/MobileNetV2 + YOLO-World → popup score、close bbox/coordinate | detector 生成 popup ROI，再接相同 OCR | B2 exact target | 数据源已具备；`model-missing`, `human-gold-missing`, `out-of-v1-action` |
| Dynamic iOS Privacy | XCUI Alert/button label → OK/Allow tap | iOS Alert text-rule perception | A2 iOS variant | `source-missing`, `interface-only`, `out-of-v1` |
| HotMobile Ad Policy | View tree/state graph/geometry → ad state、Back destination | advertisement scope/结构消息特征 | A1 structured-state proxy | `interface-only`, `out-of-v1` |
| iOS Applications' Testing | UIAElement/frame → center-coordinate tap | raw element/frame | A1 raw-element proxy | `source-missing`, `out-of-v1` |
| DiOS | UI hierarchy + Alert callback/origin → handler/target label/tap | Alert owner、hierarchy、label 提取 | A1/A2 iOS proxy | `interface-only`, `out-of-v1`；原私有运行环境不可用 |

`out-of-v1` 表示论文的动作、dismissal、persistence、focus/page/task recovery 等输出超过本研究 v1 的“只判断 popup presence + message”边界，不是对原论文价值的否定。

## 当前可执行系统

| System | 30-item pre-gold 状态 | 不能宣称什么 |
|---|---|---|
| A1 structure-only | `runnable`；15 judged / 15 abstain | 无人工 gold；还需统一 popup-scope 与 full-tree flatten 定义 |
| B1 OCR-only | `runnable`；30/30 abstain | 当前是全屏 OCR，不是正式 popup-ROI baseline |
| C3 MG-PU candidate | `runnable`；2 项 structure、28 项 visual workflow candidate | visual candidate 精确模型身份不可复现；不是正式方法结果 |

A0、A2、A3、B2、B3、C1、C2、C4 仍只有接口、计划或 synthetic smoke。`always-visual` 只是路由消融，不等于 C1 always-on structure+vision fusion。

## 正式比较的解锁顺序

1. 完成真实 A/B 盲标，并由第三位真实 adjudicator 对全部 30 项输出 final；冻结 group-disjoint split。
2. 正式运行 A1、A2、B1、B2。A2 至少忠实冻结一套论文规则；B1 使用无泄漏 popup scope；B2 固定 PopSweeper 模型、权重、revision、frame gate、分类器、YOLO-World 与官方 split。
3. 实现 C1；C1/C3 使用同一 visual backbone、分辨率和预算。
4. 只有在同一 gold、同一输入资格和同一 evaluator 下，才运行 C3 对 dev-selected strongest deployable baseline 的主比较。

在以上条件完成前，本仓库只报告工程就绪度、abstention、visual-call routing 和可复现性缺口，不报告 accuracy、VPMA 或“优于已有方法”。
