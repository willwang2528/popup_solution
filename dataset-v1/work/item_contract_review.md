# Dataset v1 item contract 与质量门审阅

> 状态：`provisional contract review`。本文件只审阅 schema、字段清单与采样/切分契约；未创建、补写或推断任何真实 episode。

## 1. 审阅对象与结论

审阅对象：

- `schema/item.schema.json`
- `DATASET_CARD.md`
- `work/literature_field_union.json` 与对应审计
- `work/our_method_fields.json` 与对应审计

结论分两层：

1. **概念容纳性通过**：90 个文献字段与 165 个我方方法字段，原则上都能落到一个完整 episode 的 `scenario/environment/observations/candidates/decision/action_attempts/verification/annotations/provenance` 链路中，不需要把截图、节点或动作拆成独立统计样本。
2. **冻结质量门未通过**：当前 JSON Schema 主要验证对象形状，尚不能独立强制字段级缺失原因、跨字段推导、安全决策、引用完整性、真实/fixture 隔离和 group 防泄漏。正式采集前必须由 `qa_rules.json` 对这些跨字段与数据集级不变量做二次校验；否则不能继续使用“冻结结构契约”或“schema-complete”作为无条件结论。

## 2. 字段并集到一个 episode 的落点

| 字段来源 | episode 内落点 | 审阅结论 |
|---|---|---|
| 任务、触发、合法动作集合、安全边界 | `scenario` | 可落入；必须区分普通低风险、敏感仅 abstain、out-of-scope。 |
| 平台、设备、App、随机化状态 | `environment` | 可落入；Android、iOS、mobile Web 需保留真实宿主与设备语境。 |
| TalkBack/VoiceOver 配置与可观测性 | `assistive_technology`、`observations[].screen_reader_state` | 可落入；框架 page source 不得冒充 AT 焦点/朗读。 |
| 原始树、DOM、协议、视觉与弱代理 | `observations[]` | 可落入；观察必须有 phase、时间同步、artifact 与 provenance。 |
| 跨平台公共候选 | `candidates[].normalized` | 可落入；它只是决策投影，不能覆盖或替代平台 raw。 |
| Android/iOS/DOM/视觉原始字段 | `observations[].structured_representation.*_raw`、`candidates[].*_raw` | 可落入；不适用通道必须为 null 并给出 `not_applicable`，不是空对象。 |
| 文献规则、视觉变化、持久化等信号 | `observations[].literature_signals`、`verification.weak_proxies/persistence` | 可落入；只能作为基线信号，不能单独生成 D、C 或 T。 |
| 门控、排序、安全策略、视觉兜底 | `decision` | 可落入；需要跨字段公式验证，schema 本身尚未编码。 |
| 真实动作和一次替代尝试 | `action_attempts[]` | 可落入；当前 schema 缺少显式 retry budget 与 exhausted 字段，需外部规则限制。 |
| D、C_tech、C_a11y、T 与成本 | `verification` | 可落入；所有汇总值必须从证据充分的原子值确定性派生。 |
| 人工真值、目标用户验证和裁决 | `annotations[]` | 可落入；目标用户验证与普通研究者标注不能互换。 |

## 3. 当前 schema 的阻断缺口

以下缺口不否定当前结构草案，但会阻断正式数据冻结或主指标统计。

### B1. 缺失值语义没有覆盖整个 item

`presence` 目前只在 `assistive_technology`、`observations[]` 和 `candidates[]` 中出现；`scenario`、`environment`、`decision`、`action_attempts[]` 与 `verification` 仍包含大量 nullable 字段，却没有统一的逐字段状态表。JSON Schema 也不要求 presence 覆盖每个 nullable JSON Pointer。

质量门必须保证：

- 非 null 字段对应 `observed/derived/annotated`；
- null 字段对应 `not_available/not_applicable/not_observable/collection_failed/redacted/unknown`；
- `false`、空字符串、空对象和零不得代替“未知”；
- “测量失败”不应写成科学真值 `false`。

在 schema 增加 episode 级 observability 之前，验证器需生成外部字段状态审计表，或拒绝缺少原因的 nullable 关键字段。

### B2. 165 个方法字段没有一份显式 schema crosswalk

字段清单中的 `episode.*`、`task_context.*`、`capability_profile.*`、`feedback.*`、`observability.*` 与 `provenance.*` 并不都按同名路径存在于 item schema。部分信息被折叠到 `identity/scenario/assistive_technology/decision/quality`，但以下内容仍缺少无损、可检查的直接落点：

- capability profile 的闭环能力状态与证据引用；
- episode 级 `observability.field_status` 和 measurement channel；
- raw capture hash、episode evidence level 与完整 collector/model registry；
- feedback 状态、实际 delivered 回证和 handoff options；
- retry budget 与 retry exhausted。

正式宣称“165/165 已纳入”前，应建立字段路径 crosswalk；当前只能写“概念覆盖，部分字段需由外部 QA 或后续 schema 字段承载”。

### B3. Schema 不强制低风险边界

当前 enum 允许普通 scope 与敏感 safety category、自动 execute 与高风险动作同时出现。质量门必须阻止以下记录进入自主执行或成功统计：

- CAPTCHA、风控、PIN、生物识别、认证、支付、安装、删除、设备管理；
- 正向隐私/权限授权、同意条款、购买；
- 未知语义、未知 owner、无安全退出路径。

这些样本只可用于 abstain/handoff 与 Harmful Action 测试；自动动作尝试本身即为严重违规信号。

### B4. Schema 不强制 D/C_a11y/T 公式和证据

当前可写出 `A_VTR=true` 但 D、C_a11y 或 T 为 false/null 的结构合法记录。质量门必须用三值逻辑重新计算：

```text
D = visual_popup_gone AND semantic_popup_gone
C_tech = owner_context_restored AND blocked_target_operable
C_a11y = C_tech AND focus_restored
          AND spoken_context_consistent（仅当 utterance 可观测）
T = task_postcondition_satisfied
VTR-tech = D AND C_tech AND T
A-VTR = D AND C_a11y AND T
```

任何 conjunct 未知时，存储真值应保持 null；是否在保守分析中按失败计数属于分析策略，不能篡改原始真值。A-VTR 不得由 VTR-tech 推断。

### B5. Schema 不强制真实数据、fixture 与 paper reconstruction 隔离

`record_kind` 与 `split` 是独立 enum，因此 synthetic fixture 理论上可被标成 train/test。质量门必须覆盖：

- `synthetic_schema_fixture` 只能进入 `schema_fixture`，永不训练、调参或计入指标；
- `paper_reconstruction` 只能做字段/基线复现审阅，不进入经验指标；
- `controlled_fixture` 可用于 capability、因果标签与压力测试，但必须与 real-app cohort 分开报告；
- 真实主结果只来自已审定的 `real_app` cohort；如另报 fixture 主套件，也不得与真实 App 汇总为一个数。

### B6. 防泄漏 group 可为空，且粒度未定义

train/validation/test item 的六类 group ID 当前都可为 null。质量门必须要求其非空，并以六类 group 关系的连通分量作为不可分割分配单元。`os_family_group_id` 还必须预先定义到合理的 OS major/build/OEM/framework 家族；若只填 `android` 或 `ios`，会把整个平台锁进一个 split，失去分层意义。

### B7. `quality` 不能由采集器自证

`schema_valid`、artifact existence、leakage、privacy、annotation 等布尔值只能由独立验证过程回填或核验。记录里写 `true` 不是通过质量门的证据。

## 4. item 级接受门

item 依次通过以下门；前一门失败时不继续升级 eligibility：

1. **G0 解析与版本**：JSON 可解析、无重复键、符合 `1.0.0-provisional`、ID 唯一。
2. **G1 episode 完整性**：引用 ID 存在且唯一；观察 phase、时间顺序和动作前后关系成立。
3. **G2 raw/normalized**：平台 raw 不被公共字段替代；每个 normalized 非空字段有 presence 与 field provenance。
4. **G3 artifact**：主指标所需 artifact 存在、hash 非空、redaction/privacy 状态通过。
5. **G4 平台与 AT**：Android A-VTR 使用已验证 TalkBack；iOS 使用已验证 VoiceOver；mobile Web 记录宿主设备/OS/浏览器与真实 AT，browser fixture 单列。
6. **G5 安全策略**：普通低风险动作才能自动 execute；敏感或未知样本必须 abstain/handoff。
7. **G6 动作链路**：selection 引用候选；attempt 引用前后 observation；最多一次预注册替代动作。
8. **G7 回证**：D/C_tech/C_a11y/T 和 VTR-tech/A-VTR 由原子证据重算；弱代理不能升级为成功。
9. **G8 标注**：主真值完成双人标注和裁决；target-user claim 需目标用户证据及相应伦理/同意材料。
10. **G9 cohort eligibility**：依据 record kind、证据级别和上述门决定训练、主指标与用户体验声明资格。

## 5. 平台与辅助技术规则

- Android 主 A-VTR：`platform=android`、TalkBack enabled、capability 已验证；Android raw 为主，WebView/DOM 可作为额外通道。
- iOS 主 A-VTR：`platform=ios`、VoiceOver enabled、capability 已验证；XCUI/Appium 可见性仅算 framework evidence，除非焦点/朗读另有 AT 或目标用户证据。
- mobile Web：必须记录实际宿主 OS、设备、浏览器/driver 与 TalkBack 或 VoiceOver；`browser_fixture` 只能进入 fixture cohort。
- `assistive_technology.name=none` 可以用于技术 baseline 或负控，但不得进入 A-VTR 或视障用户体验结论。
- 一个 item 可包含多个 raw 通道，例如 Android WebView 同时有 Android raw 与 DOM raw；不适用 raw 保持 null 并标 `not_applicable`。

## 6. 抽样规则

### 6.1 统计单元与 cohort

- 最小统计单元是一次 method-specific episode；帧、候选、重试和 relaunch 观察不得扩增样本量。
- `real_app`、`controlled_fixture`、`synthetic_schema_fixture`、`paper_reconstruction` 四类 cohort 分开保存与报告。
- 同一 scenario 的不同方法运行为配对 episode：共享任务真值、reset snapshot 和随机化 seed，方法执行顺序单独随机化。

### 6.2 分层

正式采集按以下主层联合覆盖：

```text
platform × popup_owner × popup_kind × exposure_tier × action_topology
```

同时预注册 App/template/SDK/OS family 的每组最大 episode 数或采样权重，防止单一 App、CMP 或模板支配结果。无弹窗但视觉相似的负样本单列，用于 False Intervention；敏感弹窗单列用于 abstention safety，不与普通退出成功率混合。

### 6.3 N

当前不填写固定 N。先用 capability pilot 估计：

- 每个平台有效闭环率与不可观测率；
- tree-only residual failure；
- cluster size、组内相关与主要二项指标方差；
- 配对方法差异及 Harmful Action 上界需求。

完成预注册功效分析后冻结每个主层的 scenario 数、每 scenario 重复数、group cap、方法与 action/model budget；不能按观察到的结果补采有利 cell。

## 7. Split 规则

1. 先完成 near-duplicate 识别和六类 group ID，再切分。
2. 把任意 group ID 相同的 item 连成图；每个连通分量整体进入一个 split。
3. 同一 scenario 的不同方法、seed、动作尝试、帧、relaunch 和派生 artifact 永远跟随同一 split。
4. 使用冻结 seed 对连通分量做确定性分配，再在不拆分分量的前提下尽量平衡主层。
5. test group 在调参、threshold/calibration/policy 冻结前不可见；pilot 不得回流为正式 test。
6. synthetic fixture 固定为 `schema_fixture`；paper reconstruction 固定为 `unassigned/schema_fixture`；两者不参与 split 比例。
7. real-app 与 controlled-fixture 即使使用相同 split 名，也必须在报告中保持独立 cohort，禁止池化主指标。

## 8. 指标与缺失值口径

- `A-VTR observable cohort` 必须在运行前根据平台 capability 定义，不能根据动作结果事后选择。
- capability 明确不支持的 item 不进入 A-VTR 分母，但必须报告覆盖率，并进入 VTR-tech 或 capability 结果。
- 已宣称 capability 支持却发生采集失败的 item 不能静默删除；单列 measurement failure，并在预注册保守分析中按约定处理。
- D、C_tech、C_a11y、T 的 evidence URI 为空时，不得声明相应 verified success。
- `eligible_for_user_experience_claim=true` 只允许真实设备、目标用户参与、合规同意/伦理与 A-VTR 证据齐备的 real-app item；自动日志或 fixture 永不满足。

## 9. 当前可接受表述

可以写：

> 当前 schema 已形成一个完整 episode 容器，能够概念性承载文献字段并集与方法字段；正式采集和指标计算仍受字段级 presence/provenance、跨字段质量门、平台 capability、真实/fixture 隔离及 group 防泄漏规则约束。

当前不能写：

- 165 个方法字段已经全部按同名路径无损冻结；
- nullable 字段已经由 JSON Schema 自动保证缺失原因；
- iOS/VoiceOver 或 TalkBack 闭环已经可用；
- fixture 等同真实 App，或 schema fixture 是数据样本；
- 任意 VTR-tech、A-VTR 或用户体验结果已经产生。
