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

## Android capture gate 增量审阅

公开实现完成后，又在同一 Claude thread 中进行了三次最小化增量审阅。最终结论为 `TOOLING_GATE_CONVERGED`，但只针对 CAP-001 离线软件门，经验主张变化为 `NONE`。

审阅过程保留了一次重要纠错：Claude 首轮认可工具门后，Codex 反向检查发现 nested node 中的 label/prediction key 可绕过顶层检查，且聚合器仅凭手写 `eligible` record 可放行。新增失败测试后，代码改为递归拒绝标签／预测键，并完整校验每条终结记录。Claude 随后给出 `VERIFIED_FIX`，但又过度声称“随机 SHA-256 无法伪造”；Codex 指出任意 64 位十六进制串都能通过形状检查。正式 CLI 因此再次收紧为只接受私有 metadata 路径清单、逐 bundle 重新读取 artifact bytes、重新终结并重算哈希，彻底移除 `--records` 入口。

最终审阅确认：路径穿越、直接 symlink、目录 symlink escape、重复 resolved path、重复 capture ID、重复截图哈希和重复结构哈希均 fail closed；12 条 capture gate 测试通过。它同时明确软件门的能力边界：它能证明当前磁盘 artifact 存在、格式与声明一致，不能密码学证明 collector、授权、时间戳、稳定状态 token 或 AccessibilityService 来源声明真实。后者需要开源 collector、可复现构建、运行日志和人工／流程审计。

因此当前状态仍是：真实 capture=0、human gold=0、paper result=0。增量审阅不允许提前宣称 capture feasibility 已实证通过。

## 真实 Android collector 增量审阅

在离线门之后实现了 Android 30+ `AccessibilityService` 采集器、app-private request/readback、`tree-before → screenshot → tree-after` 单调时钟回证，以及机器记录与人工 `review.json` 分离的 V1.1 终结协议。

第 7 次 reviewer 调用尝试让 Claude 限定读取采集器源码和测试，但 600 秒后明确超时，没有返回任何审阅文本；该次调用保持 `provisional/failed_timeout`，不能算 cross-family 接受。随后第 8 次调用改成不使用 repository tools 的自包含 bounded design/contract review，Claude 明确声明这不是 fresh source-level verification，并给出 `PROCEED_TO_ONE_DRY_RUN`。

该结论只允许在一台已授权 Android 设备上做一个 dry run，不能直接进入 5-group gate。Claude 认为 dry run 前没有已识别的 fatal blocker，同时要求 5-group gate 前关闭以下问题：完成或重跑 Android lint；独立计算并核对实际安装 APK 与签名证书哈希；把 Git SHA/可复现构建继续视为信任边界；记录 TalkBack 导致的 `focus_drift` 拒绝率；为 FileObserver 事件遗漏增加可靠性策略；在真实 OEM/Android 设备上核对 runtime capability/flag bits。

审阅后已进一步加入三项不依赖设备的修复：服务用同一 worker 每 2 秒扫描 app-private pending request，兜底 FileObserver 事件遗漏；主机新增 `attest` 命令，逐字节比较本地与已安装 APK、核对 DEX source revision、从 `apksigner` 读取证书哈希，V1.1 finalizer 再与人工 review 交叉绑定；Android lint 的 3 条 warning 修复后重新运行正常 exit 0，最终为 `No issues found`。真实 OEM capability、TalkBack focus drift 和设备端安装 APK 读取仍需 dry run 实证。

经验主张变化仍为 `NONE`。真实 capture=0、human gold=0、method metrics=0；`PROCEED_TO_ONE_DRY_RUN` 只说明设计合同足以尝试一次安全、授权的真实采集。

## 视觉 bank 与等预算基线增量审阅

第 9 次调用只披露 V1 边界、固定阈值协议、聚合计数、哈希、重放结果和五方法路由／调用计数；没有发送截图、OCR 原文、逐项 ID、私有 prediction 或人工标签。Claude 给出 `PROCEED_WITH_MANDATORY_FIXES`：没有发现已证实的泄漏或正确性致命缺陷，但要求公开推送前去掉两个过强命名。

修正后，Apple Vision 证据只声明 `repeat_execution_byte_identical_on_fixed_host=true`，跨 OS／设备模型身份保持 `not_verified`；方法只称为冻结的固定阈值、positive-or-abstain 启发式 adaptation，不再称为 formal/canonical/validated baseline。C1-BM 明确只匹配调用成本，不匹配 item 集或难度；MG-PU 的“28 次视觉调用”也拆成 4 次形成视觉正判断、24 次视觉 adapter 弃答。

同时新增两类 fail-closed 回归：物理删除 `popup_present_gt`、stratum、source ID 后输出必须不变；新增未登记 manifest／artifact 字段则整批拒绝。修正后的 30 项本机重放仍为 4 judged、26 abstain，逐项决定／ROI／消息在排除运行时字段后相同。经验主张变化仍为 `NONE`。

## Trace metadata

- Review thread：`3d76b654-220f-41c8-965d-424b0be7c2c8`
- Round 1 job：`579cc0159bd8439486de5670c8fb2631`
- Round 2 job：`d1015d7c106d4593a85be63da5d359e8`
- Round 3 job：`1c4fe530e2c841fe9ce7a6505397ac9b`
- Android gate review job：`8939bb2d516544ba9cebdd2126da555c`
- Fail-closed recheck job：`5cc4019879de44d2a9b9b10b06c39fda`
- Artifact-binding final job：`9c58eb567dd9407b9e7aa10c4949d726`
- Real collector source-reading job（timeout/provisional）：`48b3db97d19b433796ec20462c8a5ead`
- Bounded collector review job：`5a97eb92f2c04a1fb9c682440950bca0`
- Visual bank / C1 fatal-gate job：`762b47f9867245b18f082a33d2b16164`
- Local complete trace：`.aris/traces/research-review/2026-09-01_run01/`

完整请求／回复／模型／时间／任务标识保存在本地 trace；本公开文档只保留最小化、可审计的研究结论与标识。
