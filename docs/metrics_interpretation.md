# Deliberation 质量指标解读

本项目在每轮 `deliberation.round` 事件中记录 `quality_metrics`，用于快速判断一轮讨论是否满足结构化要求与治理门槛。

## 每轮指标

- `obligation_completeness`：义务完整度，范围 `[0,1]`。
  - 计算方式：`已满足的 required obligations / required obligations 总数`。
  - 越接近 1，表示该 arena 的必选步骤越完整。

- `critique_independence`：批评独立度，范围 `{0.0, 1.0}`。
  - `1.0` 代表至少两条批评在攻击点/挑战字段/推理路径上足够独立。
  - `0.0` 代表批评高度重叠或批评数量不足。

- `diversity_score`：面板多样性分数，范围 `[0,1]`。
  - 基于 agent 的 human-base 与 module 权重向量距离计算。
  - 分数越高，表示角色/视角越多元。

- `dissent_retained`：异议留存情况，布尔值。
  - `True`：无未解决异议，或未解决异议已被持久化保存。
  - `False`：存在未解决异议但未保存，通常会阻止 commit。

## Session 趋势聚合

可对一个 session 的 round 事件调用 `summarize_session_quality_trends(events)`，得到：

- `round_count`：统计到的 round 数。
- `series`：每轮时间序列（四个指标）。
- `averages`：整体平均值（含 `dissent_retained_ratio`）。

建议关注：

1. **完整度趋势**持续下降：说明流程可能反复跳过关键步骤。
2. **独立度长期为 0**：说明双评审形同重复，需要调整 critique 分工。
3. **diversity_score 偏低**：可改进 seat 分配或 agent 组合。
4. **dissent_retained 出现 False**：应优先修复留存流程，避免丢失争议上下文。
