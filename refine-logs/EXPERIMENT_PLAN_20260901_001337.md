# Experiment Plan：PMAB + MG-PU

**Problem**：移动弹窗的屏幕可见消息没有完整暴露给屏幕阅读器可读取的结构化表示
**Method Thesis**：只在结构化消息不足、合并、矛盾或过期时调用视觉补全，能在同预算下提高正确消息覆盖并降低关键编造／视觉成本
**Date**：2026-09-01
**Stage**：source-ingestion in progress；尚无 empirical result
**Scope**：V1 message-only，所有系统 `no_action`

## 1. Claim Map

| Claim | 为什么重要 | 最低可信证据 | Blocks |
|---|---|---|---|
| C1 — PMAB 测到真实 popup message observability gap | 决定数据集贡献是否成立 | 真实 screenshot + platform structure + message gold；双人标注；group-disjoint split；真实 gap prevalence | B0, B1 |
| C2 — MG-PU 的 gap gate 改善 accuracy–coverage–cost | 决定方法贡献是否成立 | 同 frozen observation、同输入资格、同预算；VPMA 提升 ≥5 points；cluster-bootstrap 95% CI 不跨 0 | B2, B3 |
| Anti-C1 — 数据不是为 MG-PU 定制 | 防止 circular benchmark | source-first sampling；标注者看不到方法预测；split 在实现方法前冻结 | B0, B1 |
| Anti-C2 — 收益不只是更多视觉／更大模型／更多 abstain | 防止错误归因 | always-on、等调用预算、shuffled gate、risk–coverage 与成本表 | B3 |
| Boundary — 消息准确率不是完整 Recovery | 避免违反 PPT 第 14 页 | 不执行动作；不报告 D/C/B/T；advanced 结果单独 profile | 所有 blocks |

## 2. Paper Storyline

### Main paper must prove

1. popup-specific message gap 在真实移动 UI 中存在、可标注、可分层测量；
2. PMAB 的 item、source、license、split 和 gold 可被第三方复现；
3. MG-PU 相对 strongest deployable baseline 在预注册主比较中更好；
4. 提升不来自泄漏、额外预算、synthetic-only 或高 abstention。

### Appendix can support

- 更多 gap taxonomy；
- OCR／VLM prompt 和版本；
- per-owner／per-framework qualitative cases；
- synthetic corruption stress test；
- advanced Recovery 五级字段兼容。

### Intentionally cut

- 点击、关闭、Accept／Reject 选择；
- CAPTCHA／风控／支付／认证；
- end-to-end RL；
- 新 OCR／VLM backbone 训练；
- 把 weak disappearance proxy 写成任务恢复；
- 第三个以上平台；
- 没有真实数据的用户体验结论。

## 3. Data Specification

### 3.1 Tier P1：public-derived Android pilot

Primary candidate source：

- PopSweeper Zenodo record：`13754620`
- License：`CC-BY-4.0`
- Archive：`app-blocking pop-ups_basic.zip`
- Expected size：`266010362`
- Expected MD5：`46a0fe5c4eeab2bd119aed800b7a81f3`

Join source：

- RICO official screenshot + detailed view hierarchy；
- source IDs 和 copyright terms 必须保留；
- 如果原图再分发受限，公开 annotation、source ID、hash 和 downloader/adaptor，不复制受限图片。

### 3.2 Tier P2：controlled Android

从 permissive open-source app／自建 fixture 采集：

- screenshot；
- raw UI hierarchy／AccessibilityNodeInfo dump；
- popup owner／window／layer；
- TalkBack utterance／focus sequence（可行时）；
- stable state fingerprint；
- source commit、APK hash、OS/device、locale。

当前主机没有 `adb` 或 emulator；P2 为硬阻塞门，不以 P1 替代。

### 3.3 Tier P3：iOS

真实 iPhone：

- screenshot；
- XCUI/A11Y snapshot；
- label/value/traits/element type/bounds；
- VoiceOver utterance／focus（可行时）；
- iOS/device/app version。

当前无 `simctl` 或 iOS device channel；P3 未完成前不做 cross-platform 主张。

### 3.4 Pilot sampling

`N=120` Android candidates：

| Stratum | Positive | Negative | Notes |
|---|---:|---:|---|
| tree-complete／high exposure | 20 | 20 | 测 structure-only ceiling |
| partial／merged／ambiguous | 20 | 20 | 核心 gap |
| visual-only／tree-missing candidate | 20 | 20 | 视觉兜底压力层 |
| Total | 60 | 60 | App/template group-disjoint |

Sampling 在任何 MG-PU prediction 产生前冻结。若 source archive 无法支持上述分层，则降低为 capability pilot，并重新估计正式 N，不伪造平衡数据。

### 3.5 Annotation pilot

先解锁 30 items：

- 2 名独立标注者；
- 不可见 method prediction；
- 标注 popup presence、blocking、message、critical facts、gap、evidence；
- 第三人裁决；
- 记录耗时和 ambiguity。

Gate：

- presence Cohen’s κ ≥0.80；
- gap-family κ ≥0.70；
- critical-fact span／set F1 ≥0.85；
- semantic message agreement ≥0.80；
- unresolved ≤15%。

未达门：修订 guide 后再试 30 items；第二次仍未达门，停止正式 benchmark claim。

## 4. Compared Systems

### Family A — Structure-first

| ID | System | Input | Purpose |
|---|---|---|---|
| A0 | majority/no-popup sanity | none | 检查类不平衡 |
| A1 | structured flatten | raw tree text/role/order | 最小 structure-only |
| A2 | Appium-text rules | tree text + popup/privacy lexicon | 对齐 The OK Is Not Enough 等文本方法 |
| A3 | transcript analyzer | TalkBack transcript | ScreenAudit-style adjacent baseline；仅 transcript 子集 |

### Family B — Vision-first

| ID | System | Input | Purpose |
|---|---|---|---|
| B1 | OCR-only | screenshot／popup ROI | 对齐 Freely Given Consent 式 OCR |
| B2 | PopSweeper detector + OCR | screenshot + detected ROI | popup-specific visual baseline |
| B3 | screenshot-only VLM | screenshot | 强视觉 baseline |

### Family C — Fusion

| ID | System | Input | Purpose |
|---|---|---|---|
| C1 | always-on fusion | tree + screenshot every item | 检验 gate 是否必要 |
| C2 | fixed cascade | A11Y → OCR/OmniParser → VLM | WhisperTest-style perception cascade，禁用动作 |
| C3 | MG-PU | tree + conditional visual ROI | proposed |
| C4 | oracle gate upper bound | gold gap chooses channel | 仅上界，不是 deployable baseline |

所有系统输出同一 schema：presence、message、critical facts、confidence、abstain、evidence、latency、cost。所有系统不得点击。

## 5. Metrics

### 5.1 Primary

Positive popup：

```text
VPMA = presence_correct
       AND message_semantically_correct
       AND NOT critical_hallucination
```

No-popup：`VPMA = presence_correct`。Abstain：`VPMA = null`，必须和 coverage 一起报告。

Primary table：

- VPMA；
- coverage；
- Popup Presence Macro-F1；
- Critical Information Recall；
- Critical Hallucination Rate。

### 5.2 Secondary

- Message Semantic Correctness；
- Exact Match／Character F1；
- false-notification rate；
- visual-call rate；
- p50/p95 latency；
- input/output tokens；
- model/API cost；
- calibration／selective risk；
- per-platform／gap／owner／language／framework breakdown。

### 5.3 Statistics

- App/package/popup-template group 为 cluster；
- cluster bootstrap 10,000 resamples；
- 主比较只有一个：C3 vs dev-selected strongest deployable baseline；
- 报告 absolute difference、95% CI 和 paired item table；
- 阈值只在 validation 选择；
- test 只运行一次；
- 其余对比明确 exploratory 或做多重检验校正。

## 6. Experiment Blocks

### Block 0：Source Integrity and Joinability

- **Claim**：P1 source 可合法、完整、稳定地转为候选 item。
- **Checks**：
  - Zenodo metadata／license；
  - archive MD5；
  - archive bomb/path traversal scan；
  - file inventory、extension、count；
  - annotation format；
  - RICO/source ID join rate；
  - screenshot hash duplicate rate；
  - PII／sensitive screen audit。
- **Success**：
  - checksum match；
  - unsafe archive members = 0；
  - source ID 可解析率 ≥95%；
  - positive label 与 image 对齐抽查 ≥98%；
  - 可 join hierarchy 的 positive candidates ≥60。
- **Failure**：
  - join <60：P1 只作 visual pilot；正式 benchmark 转 P2 controlled；
  - license 不清楚：不再分发，仅本地分析；
  - source label 不可解释：停止复用。
- **Priority**：MUST-RUN。
- **Target**：Dataset Table 1。

### Block 1：Message-Gap Census and Annotation Reliability

- **Claim**：真实 popup 中存在可测 message gap。
- **Data**：30-item annotation pilot → 120-item Android pilot。
- **Outputs**：
  - gap prevalence；
  - tree vs screenshot text coverage；
  - omitted critical facts；
  - owner/context contamination；
  - IAA 和裁决率。
- **Success**：
  - annotation gates 全过；
  - 至少 20 个真实非-synthetic gap positives；
  - gap 不只由一个 App/template 贡献。
- **Failure**：
  - gap <10%：不建立独立 method claim；
  - gap 仅单一 App：扩大来源或改为 case study。
- **Priority**：MUST-RUN。
- **Target**：Main Table 1 + Figure 1。

### Block 2：Baseline Reproduction

- **Claim**：评测器、输入封装和 baseline 输出可靠。
- **Data**：development split。
- **Runs**：A1、A2、B1、B2；条件允许再跑 A3、B3。
- **Sanity**：
  - no gold leakage；
  - deterministic replay；
  - output schema 100% valid；
  - manual trace audit 20 items；
  - latency/call accounting complete。
- **Success**：至少 structure-only、OCR-only、visual detector+OCR 三个 deployable baselines 可复现。
- **Priority**：MUST-RUN。
- **Target**：Appendix implementation table。

### Block 3：Main Equal-Budget Result

- **Claim**：MG-PU 优于 strongest baseline。
- **Data**：frozen group-disjoint test。
- **Systems**：dev-selected strongest A/B baseline、C1 always-on、C3 MG-PU、C4 oracle upper bound。
- **Budget**：
  - 相同 screenshot resolution；
  - 相同 model/backbone；
  - 相同最大视觉 calls；
  - 同 token／latency cap；
  - 3 seeds 仅用于 stochastic model；deterministic system 单次 replay。
- **Success**：
  - VPMA +5 points；
  - 95% CI 不跨 0；
  - hallucination 不恶化；
  - coverage 门通过；
  - 两个以上真实 gap tier 同方向。
- **Failure**：
  - <2 points：kill method claim；
  - 2–5 points：仅在 cost/coverage 明显占优时保留；
  - always-on 占优：删除 gate novelty。
- **Priority**：MUST-RUN。
- **Target**：Main Table 2 + risk–coverage–cost curve。

### Block 4：Novelty Isolation

- **Claim**：收益来自 gap-conditioned allocation。
- **Ablations**：
  - empty-tree-only gate；
  - always visual；
  - random visual calls with matched rate；
  - shuffled gap reason；
  - no owner/context；
  - no sync check；
  - no contradiction check；
  - no critical-fact guard。
- **Success**：full gate 优于 empty-tree/random/shuffled；critical guard 降低 hallucination。
- **Failure**：generic gate 追平则收窄贡献到 benchmark／engineering。
- **Priority**：MUST-RUN。
- **Target**：Main Table 3。

### Block 5：Generalization and Failure Analysis

- **Data**：held-out App/template/framework；iOS 只在 P3 ready 后加入。
- **Outputs**：
  - per-gap confusion；
  - false notification；
  - dropped negation／amount/date/object；
  - stale fusion；
  - unnecessary visual call；
  - avoidable abstention。
- **Priority**：NICE-TO-HAVE，不能延迟 Android anchor。
- **Target**：Figure 3 + Appendix。

## 7. Run Order and Decision Gates

| Milestone | Goal | Runs | Go gate | Stop gate | Cost |
|---|---|---|---|---|---|
| M0 | source integrity | D001–D005 | archive/hash/format/join pass | license/checksum/unsafe archive fail | CPU，<1 day after download |
| M1 | annotation reliability | A001–A003 | IAA gates pass | two failed pilot rounds | 2 annotators × 30 items |
| M2 | deterministic baselines | R001–R004 | 3 deployable baselines | evaluator or input contract invalid | CPU/OCR |
| M3 | MG-PU pilot | R005–R009 | ≥5-point candidate gain without harm | <2-point or always-on wins | VLM/API capped |
| M4 | frozen main result | R010–R014 | CI + robustness gates | main CI crosses 0 | 3 seeds if stochastic |
| M5 | platform expansion | R015+ | real iOS data ready | no device → Android-only paper | device-dependent |
| M6 | release | QA001–QA010 | license/privacy/repro all pass | any critical release gate fails | CPU + human audit |

## 8. Compute and Data Budget

- Download currently authorized：PopSweeper 266 MB；
- RICO full screenshot+hierarchy archive：约 6 GB，只有 P1 join 需要时再下载；
- RICO semantic archive：约 150 MB，可先检查是否含可用 hierarchy；
- CPU storage target：<20 GB；
- VLM/API：pilot 硬上限 120 items × systems × calls；在模型确定后写金额 cap；
- Human annotation：30-item pilot；正式规模由 pilot time/IAA 冻结；
- GPU：V1 不训练新 backbone；优先 frozen/local/API inference；
- 当前缺失：OCR runtime、PIL、Android/iOS device tooling。依赖只能装入项目 `.venv` 或项目目录，不做全局安装。

## 9. Reproducibility Contract

每个 run 必须保存：

- `run_id`、git commit、schema version；
- source item hashes；
- split manifest；
- model ID／revision、prompt hash、temperature、seed；
- dependency lock；
- command；
- stdout/stderr；
- raw prediction；
- validated metric JSON；
- cost/latency；
- status：`planned/running/complete/failed/invalid`。

任何失败 run 不静默删除；重试产生新 run ID。

## 10. Final Checklist

- [x] Problem Anchor 与 PPT 第 14 页一致
- [x] 真实数据和 synthetic fixture 分层
- [x] “first/better” 保持 provisional
- [x] 主比较与 kill criteria 已定义
- [x] source license gate 已定义
- [ ] PopSweeper archive 下载与 MD5
- [ ] archive inventory／RICO join
- [ ] 30-item 双人 annotation pilot
- [ ] Android controlled capture
- [ ] iOS capability/data
- [ ] deployable baselines
- [ ] MG-PU implementation
- [ ] frozen test result
- [ ] public release audit
