# Independent Research Review：PMAB-Android V1

> 日期：2026-09-01
> 执行者：Codex / OpenAI family
> 独立 reviewer：Claude Sonnet 5 / Anthropic family
> 状态：cross-family review completed and accepted as a review trace
> 研究结论：`PROCEED_WITH_CAUTION / pre-empirical`
> 注意：评审接受的是研究设计可以进入 pilot，不是接受效果主张；human gold=0、formal benchmark item=0、paper result=0。

## 审阅范围

只提交了 V1 问题边界、可证伪主张、标注协议、G1/G2 gold 分离、方法族和实验计划。没有提交密钥、个人信息、飞书原文、原始媒体、未过隐私闸的派生文本或无关仓库文件。

V1 被严格限定为：在冻结动作前移动状态中判断目标 popup 是否存在，并重建屏幕可见的事实消息。关闭弹窗、焦点／页面／任务 Recovery、用户体验、权限安全控制和多步工作流不在 V1。

## 三轮结论

| Round | Reviewer verdict | Score | 主要问题 | 处理结果 |
|---|---|---:|---|---|
| 1 | `STRONG_REJECT_PRE_EMPIRICAL` | 1.5/5 | 数据锚不匹配、边界／gold／预算不充分、把工程 pilot 写得过强 | proposal 收缩到 PMAB-Android，PopSweeper/RICO 降为协议 pilot |
| 2 | `PROCEED_WITH_CAUTION` | 2.0/5 | 科学锚点被认可；剩余唯一 fatal flaw 是 G2 冲突处理未定义 | 加入 versioned G1 correction + G2 restart + cannot_resolve fail-closed |
| 3 | `PROCEED_WITH_CAUTION` | 3.5/5 | fatal flaws=0；三项非阻断实验修订 | 明确 K 比例、主确认比较与多重比较控制 |

## Round 3 关键判断

### G2 fatal flaw 已关闭

Reviewer 确认以下层级可审计且 fail closed：

1. screenshot 是可见事实来源；
2. G1 是冻结的截图事实 gold；
3. G2 只比较 structure 与 G1，不另造竞争真值；
4. 普通 G2 分歧无法解决则 `cannot_resolve`；
5. G2 发现 G1 实质错误时不能改写，必须退回版本化 G1 修正，生成新 hash 后从头重启 G2；
6. 方法 prediction 与 gate reason 始终不可见。

### 显式 out-of-scope 是正确修复

Reviewer 同意 `out_of_scope + predefined reason` 防止 CAPTCHA、风控、认证、支付、权限安全控制与人工审核被塞入 `uncertain`，从而污染 ambiguity rate 或主指标。它是已裁决 disposition，但永不 metric eligible。

Reviewer 建议进一步说明系统权限对话框边界。根据用户已冻结的 V1 范围，本研究明确：OS 级权限对话框与 App 内权限／安全控制均 `out_of_scope`。这是范围选择，不代表它们不重要。

### 实验计划无剩余 fatal flaw

Reviewer 认为当前计划在 pre-empirical 阶段可执行，理由包括：

- 真实同步 Android capture 硬门；
- 5+ App/source groups、3+ template families；
- pilot 后按 gap prevalence 与 cluster structure 冻结 N；
- G1/G2 双人独立 + 第三人裁决；
- K25/K50/K100 operating points；
- null、vision-win、structure-ceiling 的预注册出口；
- privacy/license release gate。

三项非阻断修订已经落地：

1. K25/K50/K100 明确为冻结 item 集上最多 25%/50%/100% 的视觉调用比例；
2. 主确认比较固定为 MG-PU vs seeded random-K at K50，用于 power/precision 规划；
3. 次级比较采用 Holm，探索性分层采用 BH-FDR `q=0.10`。

## 允许与禁止的主张

允许：

- popup presence 与 visible-message factual correctness；
- structure vs vision 的 matched-budget 比较；
- 真实 gap prevalence 与类别分布；
- 只有实验通过预注册门时，才能报告 gate 的 allocation benefit。

禁止：

- 真实用户体验改善；
- 消息对视障用户决策充分；
- accessibility remediation；
- popup dismissal 或 focus/page/task Recovery；
- 权限／安全控制建议；
- iOS 或跨平台泛化；
- 未运行前宣称方法优于基线、数据集已经发布或研究是 broad first。

建议在论文中固定声明：本 benchmark 测技术事实消息提取准确率，不等于用户体验、可访问性改善或消息可用性；V1 排除关闭、恢复与多步交互。

## 最终执行门

当前可以进入 feasibility pilot，但不得直接扩到正式 N。以下状态保持真实：

- 正式同步 Android item：0；
- 真人 G1/G2 gold：0；
- 正式 baseline/method score：0；
- 公开经验数据集：NO-GO；
- 研究文档、协议与代码：完成发布审计后可公开。

停止／转向条件继续绑定：真实同步 capture 不可行则停止主实验；G1/G2 agreement 不过门则停止相应 gold；真实 gap <10% 或少于 20 个 non-synthetic positives 则转 structure-sufficiency measurement；方法比较不过门则撤销 superiority。

## Trace metadata

- Review thread：`3d76b654-220f-41c8-965d-424b0be7c2c8`
- Round 1 job：`579cc0159bd8439486de5670c8fb2631`
- Round 2 job：`d1015d7c106d4593a85be63da5d359e8`
- Round 3 job：`1c4fe530e2c841fe9ce7a6505397ac9b`
- Local complete trace：`.aris/traces/research-review/2026-09-01_run01/`

完整请求／回复／模型／时间／任务标识保存在本地 trace；本公开文档只保留最小化、可审计的研究结论与标识。
