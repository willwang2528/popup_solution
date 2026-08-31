# Provisional Local Review

```yaml
review_independence: same-family
acceptance_status: provisional
calibration: none
external_disclosure: not_sent
```

## 结论

方向值得继续，但尚未达到可宣称“顶会就绪”或“首个工作”的程度。最强版本不是“结构化 UI＋视觉兜底”，而是：**针对非空但不可操作的可访问性表示，用缺口门控按需调用视觉，并用原任务后置条件回证恢复**。

外部 Claude 审阅未执行：项目中的自动披露授权只覆盖 ProbeBeforeReuse，不覆盖本次弹窗研究。未经用户新增授权，本地材料不得发送到外部审阅服务。

## 未锚定评分

| 维度 | 权重 | 分数 / 10 | 判断 |
|---|---:|---:|---|
| Problem Fidelity | 15% | 9.0 | 已从泛化“关弹窗”收紧到 accessibility actionability gap |
| Method Specificity | 25% | 7.5 | 推理路径和回证明确，门控模型与阈值仍需 pilot 具体化 |
| Contribution Quality | 25% | 6.5 | 方法可形成主贡献，但“结构化＋视觉”已有直接先例 |
| Frontier Leverage | 15% | 7.0 | 冻结 VLM 的按需使用合理，不应为了现代性继续堆模块 |
| Feasibility | 10% | 6.0 | Android 可行；iOS 执行能力、真实闭环和人类体验外推风险高 |
| Validation Focus | 5% | 8.5 | VTR、等预算对照、消融与否证条件较清楚 |
| Venue Readiness | 5% | 6.0 | 需要查新、pilot、真实 iOS 数据和更强的用户动机证据 |

**OVERALL SCORE**：7.1 / 10（同模型家族预审，不能作为验收）
**CALIBRATION**：none
**VERDICT**：REVISE / PROVISIONAL

**GAP**：没有项目提供的 3 个 known-good 与 3 个 known-bad proposal anchors，因此该分数未校准。相对当前本地文献，方案已经避开“只找坐标”和“只看画面变化”，但方法新颖性仍取决于门控是否能可靠识别非空结构中的 merged、ambiguous、non-actionable 与 owner-mismatch 缺口；若最终只实现“树为空就调用 VLM”，将与现有分层系统过近。

## 关键审阅意见

### 1. 用户问题、技术问题和论文贡献必须分层

- 用户动机：弹窗可能增加辅助技术用户的恢复时间、错误操作或任务放弃。
- 技术问题：结构化表示中的 actionable exit path 不完整或不一致。
- 论文贡献：缺口门控的按需视觉恢复及 `D ∧ C ∧ T` 证书。

没有真实用户研究时，只验证了技术代理，不等于验证真实残障用户体验。

### 2. “结构化＋视觉”不是创新点

现有 PPT 已列出 WhisperTest、POKER、PopSweeper 等结构化与视觉路径。初版已将唯一主机制改为 Actionability-Gap-Gated Recovery，并要求门控识别非空但不可操作的结构。

### 3. 三个“第一个”当前均不能成立

- POKER、PopSweeper 已经提出弹窗阻断和体验问题。
- PopSweeper 已有公开 Zenodo 数据。
- 结构化＋视觉已有工作。

安全表述只能是“形式化”“计划构建并公开”“检验是否优于”。“据我们所知首个”需另做系统查新，并附精确限定词。

### 4. 严格 6 篇没有 iOS

严格文献并集不能支撑跨 Android/iOS 的已验证 schema。iOS 字段必须标为工程候选，并经真实设备、目标系统与 `D ∧ C ∧ T` 重新验证。

### 5. 数据集应以 episode 为单位

“字段并集＋随机化 × N”会混淆 observation、attribute、label 和 outcome。已改为七实体 schema、平台原始层＋公共规范层、presence mask、provenance，以及 App/模板/OS 隔离切分。

### 6. 回证必须是主指标的一部分

主指标冻结为：

\[
\mathrm{VTR}=P(D \land C \land T)
\]

任何只报告 coordinate hit、click sent、截图变化或弹窗节点消失的结果，均不能替代 Verified Task Recovery。

## 仍需解决的阻塞项

1. **iOS feasibility gate**：能否在目标场景合法获取所需结构、执行动作并获得真实 T 回证。
2. **user-impact evidence**：若论文以盲人或低视力用户体验为中心，必须加入目标用户研究或可靠遥测。
3. **novelty gate**：系统查新是否支持“跨平台＋可访问性缺口＋原任务回证”的精确优先权主张。
4. **pilot gate**：tree-only residual failure 是否足够大；门控是否优于 always-on fusion。
5. **release gate**：截图、树文本、App 内容与标注的隐私、版权和许可证是否允许公开。

## 下一轮审阅输入

- 完整 Proposal：[`round-0-initial-proposal.md`](./round-0-initial-proposal.md)
- 数据 schema：[`../DATASET_SCHEMA.md`](../DATASET_SCHEMA.md)
- 最需要外部审阅的问题：主机制是否足够区别于已有级联方法；iOS 能力边界是否使跨平台主张失真；数据集和方法是否造成双主贡献。
