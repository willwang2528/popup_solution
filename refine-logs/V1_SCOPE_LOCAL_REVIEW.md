# v1 Message Scope：本地同模型家族复核

> 日期：2026-08-31
> Reviewer：Codex sub-agent `/root/v1_final_review`
> 独立性：same-family local review
> 状态：PASS / provisional
> 外部披露：not sent

本复核不是 Claude cross-family review，不能作为 ARIS 的 cross-family acceptance。项目现有自动外部披露授权不覆盖本弹窗研究，因此本轮只做仓库内、只读的同模型家族审计。

## 初审

初审为 FAIL，发现：

1. `REFINEMENT_REPORT.md` 仍把 Recovery 与 `D ∧ C ∧ T` 当作当前主线；
2. 零动作只由 validator 强制，JSON Schema 仍允许非空 action attempts 与 execute；
3. `message_judgment`、legacy decision 和 summary 的 visual-call 计数不一致。

## 修复

- 将 `REFINEMENT_REPORT.md` 完整改为 v1 message-only 当前报告；
- 在 schema 中设置 `action_attempts.maxItems=0`，decision 仅允许 `no_action/abstain`；
- 对齐三层 visual trace，并在 validator 增加 flag/count/summary 跨层断言；
- 新增相应负向变异测试。

## 复审证据

复审为 PASS：

- current brief、method、proposal、refinement report 均以 MG-PU、消息判断、VPMA 和零动作为主线；
- 三条 fixture 的 visual call 分别为 1/0/1，三层记录逐条一致；
- execute、非空 action attempts 与 visual-count mismatch 均被拒绝；
- canonical materialize + validate：3 items、0 errors、PASS；
- 90 literature + 165 our-method = 255 crosswalk 保持完整；
- manifest 中 6 个 artifact hash 与文件逐项一致；
- `RESEARCH_RULES.md` SHA-256 仍为 `cd5cbb25a8197b021a9f133c1c6c41495d94fd0555fba6cf0ce0a54a86916dd2`。

## 保留意见

- Schema 与方法仍为 provisional；
- 只有 synthetic fixtures，没有 real-app 或 iOS item；
- 人工语义／关键编造裁决、隐私权限与公开发布门尚未完成；
- 本 PASS 只表示当前 artifact contract 内部一致，不表示方法有效、数据集已公开或用户体验已改善。
