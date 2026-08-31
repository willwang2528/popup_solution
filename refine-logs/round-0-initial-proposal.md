# Research Proposal：面向移动无障碍的可操作性缺口感知弹窗恢复

> 状态：初版、未经外部跨模型审阅；`acceptance_status: provisional`

## Problem Anchor

### 用户原始问题（冻结，不改写）

> 移动端设备在无障碍模式下，读取可访问性树时，无法100%消除弹窗问题，导致体验受到极大影响。

### 可测量的操作化定义

- **Bottom-line problem**：在启用 TalkBack、VoiceOver 等屏幕阅读器或辅助技术的移动端场景中，普通、低风险且可合法退出的模态界面可能阻断原任务；平台暴露的结构化可访问性表示又可能遗漏、合并或异构呈现关键操作入口，使仅依赖可访问性树的处理器留下可测的残余失败。
- **Must-solve bottleneck**：当结构化树非空但动作入口未单独暴露、动作语义不明确、不可执行、不可命中或 owner/context 不匹配时，系统仍需找到正确的低风险退出动作，并证明原任务真正恢复。
- **Non-goals**：不处理 CAPTCHA、风控挑战、PIN、生物识别、支付、安装、账号删除、设备管理等安全或人工确认流程；不自动做高风险授权；不把所有移动弹窗统一为同一底层对象。
- **Constraints**：首期限定 Android 与 iOS；研究样本必须覆盖“识别弹窗—执行解除—动作后回证”；Android 与 iOS 的自动化接口能力不对称；算力、标注规模、设备矩阵和目标 venue 尚未冻结。
- **Success condition**：在 App、弹窗模板和系统版本隔离的测试集上，本方法在等动作预算、等模型调用预算下，相比 tree-only、vision-only 与无门控融合取得更高的 Verified Task Recovery，同时不提高 False Intervention 与 Harmful Action，并给出置信区间和跨平台分组结果。

### 人群与体验声明边界

- 若没有目标用户参与，只能写“面向辅助技术或辅助型 GUI Agent 的技术评估”，不能直接声称已改善残障用户体验。
- “长时间无法消除”“极大影响体验”目前是待验证动机，不是本地材料已经证明的事实；需要目标用户研究、可用性实验或真实遥测支持。
- “无障碍模式”不是单一系统状态。数据集必须记录具体辅助技术及配置，例如 TalkBack、VoiceOver、字体缩放和焦点行为。

## Technical Gap

本项目已有可复现普查在 65 篇弹窗相关工作中确认 23 篇移动端工作，其中 6 篇满足“发现—执行—弹窗特异回证”的严格边界；因此不能声称此前没有人处理或评估弹窗。严格 6 篇只覆盖 Android 与移动 Web，没有 iOS 严格闭环证据。当前仓库的派生证据见 [`COLLECTION_SUMMARY.json`](../data-collection/COLLECTION_SUMMARY.json) 与 [`papers.jsonl`](../data-collection/papers.jsonl)。

现有方法已经使用协议对象、结构化 UI／可访问性树、跨上下文路由和视觉方法。WhisperTest、POKER 等也已经组合结构化信息与视觉，所以“读取结构化 UI＋视觉兜底”本身不是新颖贡献。当前仓库的字段与方法证据见 [`FIELD_UNION.md`](../data-collection/FIELD_UNION.md) 与 [`papers.jsonl`](../data-collection/papers.jsonl)。

真正可检验的缺口是：

1. **树非空不等于动作可用**：动作入口可能被合并到父节点、缺少语义、不可点击／不可命中，或与宿主页面候选混在一起。
2. **平台字段不能无损统一**：Android View/Compose、iOS XCUI、DOM 与像素具有不同原始 schema；强行展平会丢失 provenance 与平台特性。
3. **视觉始终开启不是免费午餐**：它可能增加延迟、成本、误干预和坐标竞态；需要证明何时调用视觉比始终融合更好。
4. **弹窗消失不等于任务恢复**：命令无报错、截图变化、候选框命中都不能证明 owner/context 与业务后置条件已经恢复。

### 可操作性暴露缺口 taxonomy

| 缺口 | 可观察定义 | 因果归因边界 |
|---|---|---|
| `missing` | 未观察到与金标准动作对应的节点 | 黑盒条件下不能直接归因为开发者缺陷或系统过滤 |
| `merged` | 有相关节点，但动作入口未作为独立可执行对象暴露 | 需参考树、可控 fixture 或源码才能确认机制 |
| `ambiguous` | 节点存在，但 role/name/action 无法唯一确定合法退出动作 | 可以通过多标注者与任务上下文标注 |
| `non_actionable` | 节点存在，但不支持目标动作或不可点击／不可命中 | 需记录工具与平台状态，避免把采集失败当平台缺陷 |
| `owner_mismatch` | 候选属于错误 package/bundle/window/context | 可从前景 owner 与窗口元数据回证 |
| `stale_or_tool_failure` | 树与当前画面不同步或采集接口失败 | 单列，不并入平台暴露缺陷 |
| `unknown` | 只能确认缺口存在，不能确认类型 | 保留不确定性，不强制归因 |

## Method Thesis

- **One-sentence thesis**：Actionability-Gap-Gated Recovery 先判断结构化表示是否提供语义明确、可执行且 owner/context 正确的低风险退出路径；只有在缺失、合并、歧义或不可操作时才按需调用冻结的视觉 grounding，并以 `D ∧ C ∧ T` 证书判定恢复成功。
- **Why this is the smallest adequate intervention**：只新增一个可操作性缺口门控／候选排序器；平台执行器、OCR/VLM 与验证探针尽量复用，不训练新的端到端大模型。
- **Why timely**：冻结 VLM 能覆盖结构化表示的长尾，但研究重点转向“何时值得调用视觉、怎样避免误点、如何证明恢复”，而不是重新训练通用视觉模型。

## Contribution Focus

- **Dominant contribution**：针对非空但不可操作的结构化表示，提出缺口感知、按需视觉且可回证的弹窗恢复机制。
- **Supporting contribution**：构建并计划公开一个成对保存结构化表示、截图、合法动作集合与 `D ∧ C ∧ T` 回证的 Android/iOS benchmark；公开发布仍取决于授权、隐私、版权与复现检查。
- **Empirical result, not an independent contribution**：检验等预算下是否优于 tree-only、vision-only 与 naive always-on fusion；只有实验完成后才能报告改善值。
- **Explicit non-contributions**：不是首个发现弹窗阻断体验的工作；不是首个弹窗数据集；不是新 VLM；不解决所有弹窗；没有用户研究时不声称改善真实残障用户体验。

## Proposed Method

### Complexity Budget

- **Frozen / reused**：平台协议与 watcher、Android/iOS 自动化适配器、UI tree 采集器、OCR、视觉检测器或 VLM、输入执行接口、任务后置条件探针。
- **New trainable component**：一个共享的可操作性候选评分器，既用于判断 tree candidates 是否足够，也用于视觉补充后重新排序和 abstain。
- **Intentionally excluded**：新的端到端 GUI 大模型、多智能体规划器、通用权限决策器、持续后台全屏视觉轮询、高风险自动 Allow。

### System Overview

```text
原任务状态 + 触发动作
        ↓
协议事件 / window-context / accessibility tree
        ↓
平台原始字段 + 公共规范字段 + presence mask
        ↓
Actionability scorer
   ├─ 足够：选择结构化候选
   └─ 缺口/歧义：截取弹窗区域 → OCR/VLM grounding → 合并候选重排
        ↓
低风险动作策略：close / cancel / later / skip / acknowledge / abstain
        ↓
协议动作 > 元素动作 > grounded coordinate tap
        ↓
D（弹窗解除）∧ C（owner/context 与原目标恢复）∧ T（任务后置条件成立）
        ↓
成功 / 一次替代动作 / abstain-handoff
```

### Core Mechanism

#### Input / output

- 输入：任务上下文、前景 owner/context、平台原始结构化表示、规范化候选、presence mask；仅在门控触发时加入弹窗区域截图及视觉候选。
- 输出：`{action_semantics, target, execution_channel, confidence}` 或 `abstain`。

#### Actionability scorer

对每个候选 (c) 计算：

```text
score(c) = f(task context,
             owner/context consistency,
             role/name/value,
             supported action and state,
             geometry/hierarchy,
             field-presence mask,
             source provenance)
```

门控不只判断“树是否为空”，还必须覆盖：

- 正确控件被合并但无独立动作；
- name/role 存在但动作语义歧义；
- 节点不可点击、不可命中或动作能力缺失；
- 弹窗候选与宿主页面候选混入；
- owner/context 与受阻任务不一致；
- 多候选分数接近，无法可靠选择。

#### Training signal

- 正样本：任务条件下可接受的低风险退出动作集合，不强制唯一按钮。
- hard negatives：宿主页面控件、正向授权／订阅按钮、仅视觉相似的非弹窗元素、不可执行的合并节点、错误 owner 候选。
- 建议损失：候选 pairwise ranking loss + calibrated abstention loss；阈值在 validation split 上冻结。
- 视觉 backbone 保持冻结，避免把贡献变成训练更大模型。

#### Inference path

1. 优先查询协议对象与结构化通道。
2. 评分最高候选高于阈值且满足 owner/action constraints 时，直接执行结构化动作。
3. 低于阈值或存在冲突时，仅对弹窗候选区域调用 OCR/VLM。
4. 将视觉候选映射到同一 actionability schema，重新排序。
5. 若仍低置信或不在低风险白名单，`abstain`。
6. 执行后获取新树、新截图、owner/context 与任务探针，计算 `D ∧ C ∧ T`。
7. 验证失败时最多尝试一个预注册替代动作，随后 handoff。

### Verification Contract

- **D — Dismissal**：弹窗的视觉标识与语义窗口／节点均不再存在；只满足其中一项不足以计成功。
- **C — Context recovery**：前景 package/bundle/window/context 正确，原被阻断目标重新可见且可操作。
- **T — Task postcondition**：原任务的领域后置条件成立；若任务没有可观测后置条件，该 episode 不进入主 VTR 分母或单独报告为 unverifiable。

主指标：

\[
\mathrm{VTR}=P(D \land C \land T)
\]

### Failure Modes and Diagnostics

| Failure mode | Detection | Fallback |
|---|---|---|
| 树与截图不同步 | 时间戳、hash、稳定窗口检查 | 重新采集一次；仍不一致则 abstain |
| 视觉候选漂移 | 点击前复核 ROI 与候选 fingerprint | 放弃坐标动作 |
| 多个合法动作 | gold action set 与策略优先级 | 选择预注册低风险动作或 abstain |
| owner/context 不可读 | 平台 adapter 报告 unknown | 不执行跨 owner 动作 |
| D 成立但 C/T 失败 | 完整 verification trace | 重观察或恢复原任务，不计成功 |
| iOS 能力不足 | adapter capability manifest | 作为评测环境限制报告，不等同于 Android 部署能力 |

## Dataset and Benchmark Design

数据单元不是单张截图，而是一次完整的 `popup episode`：原任务触发 → 弹窗出现 → 观察 → 动作 → 回证。

采用七类实体：`scenario`、`episode`、`observation`、`element_item`、`action_attempt`、`outcome`、`annotation`。保存平台原始层与公共规范层，不把 Android、iOS、DOM 和视觉字段硬展平为一个超宽表。详细 schema 见 [`DATASET_SCHEMA.md`](../DATASET_SCHEMA.md)。

### Literature-derived field policy

- 严格 6 篇的字段并集可作为 Android＋移动 Web 的 seed schema。
- iOS 严格闭环证据为零；WhisperTest 等只能提供工程候选字段，必须通过真实 iOS 采集验证后才能进入 frozen schema。
- `merged`、`filtered`、`developer_defect` 等根因只有在可控 fixture、参考树或源码证据下才能确认；黑盒样本最多标注 `not_separately_exposed`。

### Randomization × N

- 分层维度：`platform × owner × popup kind × exposure tier × action topology`。
- 受控扰动：locale、主题、方向、字体缩放、异步延迟；fixture 可改变按钮顺序与视觉样式。
- 每个 scenario 对所有方法做配对运行，并在每次运行前恢复相同设备快照和 App 状态。
- 按 App/package、UI framework、CMP/SDK、弹窗模板族和 OS 版本分组切分，禁止同模板近重复泄漏。
- `N` 由 pilot 方差与功效分析决定；不把大量帧当独立样本。
- 主测试集优先真实平台行为；合成树腐蚀只作为压力测试，不替代真实缺口。

## Claim-Driven Validation Sketch

### Claim 1：缺口门控提高可验证恢复

- **Minimal experiment**：在同一批 episode、同一动作预算下比较 tree-only、vision-only、naive always-on fusion 与本方法。
- **Baselines**：无处理器；平台原生协议/watcher；tree rule/model；screenshot-only VLM；always-on fusion；通用移动 GUI Agent；oracle locator/action 上界。
- **Metric**：VTR、valid-close-item recall、False Intervention、Harmful Action、abstention-coverage；按平台、App、缺口类型报告。
- **Expected evidence**：本方法在结构暴露缺口子集和总体集上提高 VTR，且不以更高错误动作率换取覆盖。

### Claim 2：按需视觉比始终视觉更有效率、更稳健

- **Minimal experiment**：固定 VLM、提示、候选和推理预算，对比 gated 与 always-on vision。
- **Ablations**：去掉视觉；去掉门控；门控只检查空树；去掉 owner consistency；只验证画面变化；只验证 D。
- **Metric**：视觉调用率、端到端延迟、VLM cost、False Intervention、VTR 差值。
- **Expected evidence**：gated 方法在 VTR 不显著下降的前提下降低视觉调用、延迟与误干预；若 always-on 明显更优，则门控不构成贡献。

### Pre-registered Falsification / Stop Conditions

- tree-only 与本方法的 VTR 置信区间重叠且成本更低：视觉机制不成立。
- naive always-on fusion 在等预算下稳定优于门控：门控不是贡献。
- 增益在 App／模板隔离切分后消失：存在数据泄漏或过拟合。
- iOS 没有完成真实 `D ∧ C ∧ T` 闭环：不能声称跨 Android/iOS 验证。
- 出现敏感或破坏性误确认：不能声称可自主部署。
- 没有目标用户研究：删除“显著改善用户体验”的结论。

## Novelty and Claim Discipline

当前安全写法：

1. 我们形式化移动端弹窗的 **accessibility actionability gap**，并把成功定义为可验证的任务恢复，而非坐标命中或画面变化。
2. 我们计划构建一个 Android/iOS 配对 benchmark，记录结构化表示、像素、合法动作集合及 `D ∧ C ∧ T` 回证。
3. 我们检验缺口门控在等预算下是否优于 tree-only、vision-only 与 naive fusion。

在完成系统查新、真实采集、授权与公开发布前，不使用以下表述：

- “第一个提出弹窗问题”；
- “第一个公开弹窗数据集”；
- “第一个结构化＋视觉方法”；
- “指标优于其他方法”；
- “显著改善残障人士体验”。

## Experiment Handoff Inputs

- **Must-prove claims**：非空结构化缺口的可检测性；gated vision 对 VTR 的增益；`D ∧ C ∧ T` 相对弱回证的纠错价值。
- **Must-run ablations**：no vision、always vision、empty-tree-only gate、no owner check、D-only verification、visual-change-only verification。
- **Critical dataset requirements**：真实 Android/iOS episode；无弹窗但视觉相似的负样本；App/模板/OS 隔离；原始树与截图；gold action set；任务后置条件。
- **Highest-risk assumptions**：iOS 可执行能力；结构缺口真实频率；任务后置条件可测；公共发布权利；目标用户体验动机缺少直接证据。

## Compute & Timeline Estimate

- **GPU-hours**：未冻结。第一阶段优先使用冻结 OCR/VLM 和小型 ranker；在 pilot 前不承诺 GPU 预算。
- **Data / annotation cost**：未冻结。至少双人标注＋分歧裁决；真实用户研究需另行伦理、可访问性与补偿预算。
- **Timeline**：先完成小规模跨平台可行性 pilot、冻结 schema 与 VTR oracle，再做功效分析和正式数据规模设计。
