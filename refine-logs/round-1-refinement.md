# Round 1 Refinement

## Anchor Check

- 原始瓶颈：屏幕可见 popup message 没有完整暴露给屏幕阅读器可读的结构化表示。
- 保持方式：V1 只做动作前 presence/message 判断；视觉只补可观察消息。
- 拒绝的漂移：统一弹窗解决器、自动点击、从弱变化证据推导完整 Recovery。

## Simplicity Check

- Dominant contribution：PMAB popup-message measurement/benchmark。
- Supporting contribution：MG-PU message-gap-gated selective fusion。
- 删除：多层 action policy、用户意图推断、end-to-end RL、跨平台统一执行器。
- 保留理由：一个数据集贡献 + 一个最小方法足以直接检验 problem anchor。

## Revised Proposal

# Research Proposal：When Pop-ups Go Silent

> 副标题：面向屏幕阅读器用户的移动弹窗消息可观测性评测与缺口门控恢复
>
> 当前版本：2026-09-01，ARIS refinement round 1
>
> 状态：`REVISE / provisional`
>
> 审阅状态：Codex 同族本地精炼；外部 Claude 调用因本课题披露授权边界被主机拒绝，不能标记为 cross-family accepted
>
> 最重要范围依据：[`../sources/PPT_SLIDE_14_EVIDENCE.md`](../sources/PPT_SLIDE_14_EVIDENCE.md)
>
> 查新：[`NOVELTY_CHECK.md`](./NOVELTY_CHECK.md)，当前建议 `PROCEED WITH CAUTION`

## 1. Problem Anchor

### Bottom-line problem

依赖 TalkBack、VoiceOver 等屏幕阅读器的盲人和低视力用户，在移动端遇到弹窗时，可能因为弹窗内容没有被完整暴露到平台可访问性树／UI 结构中，无法及时知道“出现了什么、要求什么、关键事实是什么”，从而长时间被阻断。

### Must-solve bottleneck

屏幕上可见的 popup message 与平台暴露给辅助技术的结构化表示之间存在 **message observability gap**：

- 弹窗节点完全缺失；
- 系统或框架合并节点；
- 标题、正文、金额、时间、对象、否定或后果缺失；
- popup 与宿主页面文本混在一起；
- reading order 不可靠；
- screenshot 与结构树不同步或互相矛盾；
- Android／iOS 对 role、name、label、text、value、hint 的暴露不一致。

如果事实没有出现在结构化表示中，tree-only 方法原则上读不到；不能用更复杂的推理假装恢复不存在的证据。

### Non-goals

V1 明确不做：

- 统一解决所有移动弹窗；
- 绕过 CAPTCHA、风控、认证、支付、权限安全控制或人工审核；
- 自动点击、关闭、接受、拒绝或替用户做选择；
- 从节点消失、截图变化或日志变化推导完整 Recovery；
- 在没有盲人／低视力用户研究时声称真实体验已改善；
- 把通用 OCR、VLM、accessibility metadata generation 或 UI grounding 冒充新贡献。

### Constraints

- 移动端、普通弹窗、获授权的只读采集；
- V1 输入只能是同一动作前状态的 screenshot 与结构化 UI／可访问性表示；
- 所有方法在同一冻结 observation、同一 split 和等预算下评估；
- 真实数据与 synthetic corruption 分层，不能混成一个结果；
- App、popup template、SDK/CMP、UI framework、OS family 和 near duplicate 不跨 split；
- 当前主机无 `adb`、Android emulator 或可用 `simctl`，所以设备采集仍是未满足门；
- PopSweeper CC-BY-4.0 数据可作真实截图种子；RICO screenshot 的再分发必须遵守官方 copyright notice；
- iOS 结论必须由真实 iOS capability／data 支持，不能由 Android 或文档外推。

### Success condition

以下证据同时成立才算 V1 达成：

1. 发布含真实 item 的 popup-message benchmark，而不是只有 schema 或 synthetic fixture；
2. 每个 item 可追溯到 screenshot、平台结构化表示、message gold、critical facts、observability gap 和 split group；
3. 正式 validation/test 由双人独立标注与裁决；
4. MG-PU 在冻结 test 上，以同预算相对最强 deployable baseline 提升预注册主指标，95% CI 支持正向差异；
5. 增益不能由更多视觉调用、更多 tokens、数据泄漏、过度 abstain 或人工 corruption 单独解释；
6. 论文只在已采集平台和已验证范围内做结论。

## 2. 第 14 页硬边界

PPT 第 14 页把验证分为五层：

1. 弹窗标识消失——弱证据；
2. 截图／日志变化——弱证据；
3. 原目标与 Context 恢复——强证据；
4. 业务选择与持久化状态——强证据；
5. 原任务后置条件——强证据。

这意味着：

- V1 的 `VPMA` 只证明 message-level accessibility recovery；
- 它不证明 popup 已消失、焦点已恢复、业务选择已保存或原任务已完成；
- 未来 `dismissal_recovery_advanced` 必须分别报告 `D`、`C_tech`、`C_a11y`、`B`、`T`，不能压成一个 success bit；
- 任何论文结果都不得把 PopSweeper／WhisperTest 的截图变化或坐标命中改写为完整任务恢复。

## 3. Technical Gap

已有工作分别覆盖：

- RICO／MobileViews：大规模 screenshot + UI hierarchy；
- Screen Recognition：从 pixels 生成或补充 accessibility metadata；
- ScreenAudit：从 TalkBack transcript 发现通用 accessibility error；
- PopSweeper：视觉识别 app-blocking popup 和 close target；
- WhisperTest：iOS A11Y、OCR／OmniParser、VLM 与 Voice Control 自动化；
- consent-dialog studies：文本／OCR 规则、Accept／Reject 交互和大规模应用测量。

尚未被当前检索证据覆盖的组合是：

> 对 popup message 这一具体任务，把同一动作前状态的视觉事实、平台结构化暴露、屏幕阅读器可获得信息、message/critical-fact gold 和 exposure-gap taxonomy 放进同一个公开评测协议，并检验“只在结构证据不足时调用视觉”是否比 structure-only、vision-only 和 always-on fusion 更好。

这个组合仍是待验证的 research gap，不是已经证明的 novelty。

## 4. Method Thesis

方法名：**Message-Gap-Gated Popup Understanding（MG-PU）**。

> 在冻结的 popup observation 上，先以平台结构化表示重建消息；只有当 popup scope、主体消息、关键事实、reading order、owner/context、同步或通道一致性不满足可审计 sufficiency contract 时，才调用 popup ROI 的视觉补全；关键冲突仍无法解决时弃答。相较始终视觉或只看结构，这种选择性证据分配应在同预算下提高正确消息覆盖并降低关键编造与视觉成本。

MG-PU 是更广义 **Actionability-Gap-Gated Recovery** 研究路线的 V1 perception/message 子层；V1 不包含 action 或 Recovery 执行。

## 5. Contribution Focus

### Dominant contribution

**Popup Message Accessibility Benchmark（PMAB）**：一个 popup-specific、证据可追溯的公开评测包，包含：

- Android／iOS 原始平台字段与公共规范层；
- screenshot、popup ROI、OCR／视觉候选；
- platform hierarchy／accessibility snapshot；
- 可选 TalkBack／VoiceOver utterance／focus observation；
- popup presence、message text、critical facts、observability gap；
- provenance、license、hash、redaction、group split；
- prediction、abstention、latency、visual-call 和 VPMA evaluation。

公开包必须区分：

- 可直接再分发的 CC-BY／自建 controlled item；
- 只能发布 annotation、source ID、hash 和 downloader/adaptor 的受条款约束 item。

### Supporting contribution

MG-PU 及其等预算选择性视觉评估：证明或否定“message-gap gate”是否能在 PMAB 上获得更好的 accuracy–coverage–cost trade-off。

### Explicit non-contributions

- “首次发现移动无障碍问题”；
- 通用 accessibility metadata generation；
- 通用 popup detection／dismissal；
- 新 OCR／VLM backbone；
- 用户意图推断或授权决策；
- 完整任务 Recovery；
- 绝对安全或 100% 覆盖。

## 6. Dataset Design

### 6.1 Item unit

一个 V1 item 是一个动作前、只读、冻结的 observation：

```text
source episode + license
→ screenshot / popup ROI
→ platform structured representation
→ optional screen-reader transcript/focus
→ normalized union fields
→ popup/message/critical-fact gold
→ observability-gap annotation
→ group and split
→ baseline/method predictions
→ atomic metrics + VPMA
```

字段 contract 继续保存已有论文方法 90 个字段与我方 165 个字段的语义并集，共 255 条 crosswalk；`message_judgment` profile 单独计数。

### 6.2 Data tiers

| Tier | 来源 | 作用 | 是否可进入正式主结果 |
|---|---|---|---|
| P0 — synthetic schema fixture | 当前 3 条 positive/no-popup/abstain | 验证 schema 与 QA | 否 |
| P1 — public-derived pilot | PopSweeper CC-BY-4.0 screenshot/annotation；可对齐时连接 RICO hierarchy | 验证 source join、标注协议、gap taxonomy 和 Android baseline | 仅在 provenance／许可／join 通过后 |
| P2 — controlled open-source apps | 自建或 permissive F-Droid app 的 screenshot、hierarchy、TalkBack observation | 提供可重放、可公开的 ground truth | 是，Android 主数据 |
| P3 — iOS capability/data | 真实 iPhone 的 screenshot、XCUI/A11Y snapshot、VoiceOver observation | 支持 iOS 分层结论 | 是；未采集前不得声称跨平台 |

### 6.3 Pilot sample

Android pilot 先冻结 `N=120` candidates：

- 60 popup positives；
- 60 visually similar no-popup／non-blocking negatives；
- positives 按 tree-complete、partial/merged、visual-only 候选分层；
- App/package/template group 隔离；
- 先做 30-item 双人试标，通过协议门后再解锁余下 90。

正式 N 不由任意整数决定。Pilot 后依据真实 gap prevalence、cluster size、配对 VPMA 差异和目标 CI 宽度做 power analysis 冻结。

### 6.4 Gold

最小 gold：

- `popup_present_gt`；
- `blocking_gt`；
- `message_text_gt`；
- `critical_facts_gt[]`；
- `message_text_observability`；
- gap type；
- screenshot／structure／utterance evidence URI；
- 标注者、裁决与不确定性。

屏幕可见但被系统安全策略遮蔽、不可捕获或不可合法公开的内容不猜测，标为 unavailable/out-of-scope。

## 7. MG-PU Mechanism

```text
frozen screenshot + structured UI snapshot
                   │
                   ▼
          popup scope detector
                   │
                   ▼
     structured message reconstructor
                   │
                   ▼
      message sufficiency contract
       ├─ sufficient ───────────────┐
       ├─ gap → visual ROI completer│
       └─ stale/unsafe → abstain    │
                                   ▼
                 evidence aligner + critical-fact guard
                                   │
                                   ▼
        popup presence + message + facts + confidence
```

Sufficiency contract 至少检查：

- popup owner／window／layer／context；
- title/body/option coverage；
- amount/date/object/negation/consequence；
- reading order；
- tree–screenshot timestamp/fingerprint；
- host-text contamination；
- cross-channel contradiction；
- visual-only text cues。

视觉模块只能返回带 ROI/span provenance 的候选文本和图标语义，不生成点击坐标。关键事实冲突时不多数投票，直接 abstain。

## 8. Claims

### C1 — Benchmark/measurement claim

PMAB 能测量通用 UI 数据集或 popup detector 没有分离的 message observability gap，并报告其在 platform、owner、popup kind、framework、language 和 gap tier 上的分布。

最低证据：

- 真实 item，不是 synthetic；
- provenance／license／hash 完整；
- 两名标注者＋裁决；
- inter-annotator agreement 与 ambiguity rate；
- group-disjoint split；
- 至少 Android 主数据；iOS 单独门控。

### C2 — Method claim

在同一 frozen observation 与等视觉／token／latency预算下，MG-PU 相对最强 deployable baseline 提高：

```text
VPMA = presence_correct
       AND message_semantically_correct
       AND NOT critical_hallucination
```

同时报告 coverage，避免靠大量 abstain 获得虚假准确率。

### Anti-claims

实验必须排除：

- 收益只是更多视觉调用；
- 收益只是 VLM 更大；
- 数据集按 MG-PU 的 gate 人为定制；
- synthetic corruption 驱动全部提升；
- 同 App/template 泄漏；
- 过度 abstain；
- 人工 gold 泄漏进 prompt；
- 把消息准确率升级为用户体验或任务恢复。

## 9. Baseline Families

最多三族，均 no-action：

1. **Structure-first family**
   - platform raw text／role flatten；
   - Appium-text／regex 规则；
   - ScreenAudit-style transcript analysis（有 transcript 的子集）。
2. **Vision-first family**
   - OCR-only；
   - PopSweeper-style popup detector + popup ROI OCR；
   - screenshot-only VLM。
3. **Fusion family**
   - always-on structure + vision；
   - WhisperTest-style fixed cascade；
   - MG-PU gap-gated fusion。

Human-readable-message oracle 只作上界，不是 deployable baseline。

## 10. Primary Evaluation

### Main metric

- `VPMA` 与 coverage；
- popup Presence Macro-F1；
- Message Semantic Correctness；
- Critical Information Recall；
- Critical Hallucination Rate。

### Cost and robustness

- visual-call rate；
- input/output tokens；
- p50/p95 latency；
- model/API cost；
- platform／gap tier／owner／language 分组；
- bootstrap 95% CI，以 App/template group 为 cluster。

### Pre-registered main comparison

`MG-PU vs dev-selected strongest deployable baseline`，在相同 frozen test、相同可用输入和相同预算下比较 VPMA。

继续 method claim 的最低门：

- absolute VPMA 提升至少 5 percentage points；
- cluster bootstrap 95% CI 不跨 0；
- critical hallucination 不恶化；
- coverage 不低于 baseline 5 points 以上，或 risk–coverage 曲线严格占优；
- 至少两个真实 gap tier 同方向；
- 增益在排除 near duplicates 后仍存在。

## 11. Kill Criteria

满足任一项即降级或停止方法 claim：

- structure-only 与 MG-PU 差异 <2 points 且前者更便宜；
- always-on fusion 在等预算下稳定占优；
- 提升只存在于 synthetic corruption；
- 真实 message gap 稀少到无法支持独立任务；
- 增益依赖更高 hallucination 或不可接受 abstention；
- source screenshot 与 hierarchy 无法可靠 join；
- 标注 agreement 未达门且两轮协议修订仍失败；
- formal split 后增益消失；
- iOS 无真实数据却试图声称跨平台；
- 查新发现同构公开 benchmark／方法且本方案没有清晰增量。

若方法 kill 但 benchmark 有效，可保留 measurement／dataset paper；不得继续堆叠新模块挽救方法。

## 12. Feasibility and Current Status

已完成：

- PPT 第 14 页证据锚与五级回证边界；
- 14 篇现有文献方法字段采集；
- 90 + 165 = 255 条 source-field crosswalk；
- schema `1.1.0-provisional`；
- 3 条不可进入经验指标的 synthetic fixtures；
- PopSweeper Zenodo 许可／文件／校验和核验；
- 初步查新。

未完成：

- PopSweeper archive 解包与 RICO ID join；
- 真实 pilot items；
- 双人标注与 adjudication；
- Android controlled capture；
- iOS capability/data；
- baseline 和 MG-PU 可执行实现；
- 冻结 split 上的实验结果；
- cross-family review；
- 公开 benchmark release。

因此当前状态是 **research-ready protocol + active source ingestion**，不是数据集或论文实验已经完成。

## 13. Timeline

1. **M0 source gate（1–2 天）**：下载、校验、解包 PopSweeper；检查 label、ID、RICO join 和许可。
2. **M1 annotation pilot（2–4 天）**：30 items 双人试标；修订 message／gap 协议。
3. **M2 Android pilot（3–7 天）**：冻结 120 candidates；跑 deterministic/OCR baselines。
4. **M3 method gate（3–7 天）**：实现 always-on 与 MG-PU；运行主比较和 kill criteria。
5. **M4 platform expansion**：获得设备后采集 controlled Android 和 iOS；未就绪时只发布 Android pilot，不虚称跨平台。
6. **M5 release**：数据卡、许可、下载适配器、annotations、schema、evaluator、结果表和复现命令一起发布。
