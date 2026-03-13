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

- `critic_path_overlap_rate`：critic 路径重叠率，范围 `[0,1]`。
  - 基于 `critique_a` / `critique_b` 的 `reasoning_path_labels` 计算交并比。
  - 越低越好：接近 0 表示两条批评路径明显不同；接近 1 表示路径趋同。

- `attack_label_dedupe_rate`：攻击标签去重率，范围 `[0,1]`。
  - 计算方式：`unique(attack_labels) / total(attack_labels)`（合并双 critic）。
  - 越高越好：高值表示攻击标签覆盖面更广、重复更少。

- `repair_coverage_rate`：repair 覆盖率，范围 `[0,1]`。
  - 计算方式：`covered_key_attack_count / required_key_attack_count`。
  - 在当前规则下，若存在独立双批评，repair 至少要覆盖关键攻击点。

- `transfer_effectiveness_rate`：transfer 有效率，范围 `[0,1]`。
  - 由两部分相乘：`transfer payload 合法性` × `repair 对 transfer breakpoints 的回应覆盖率`。
  - transfer 非法或 breakpoints 未被 repair 回应时，该值下降。

- `dissent_retained`：异议留存情况，布尔值。
  - `True`：无未解决异议，或未解决异议已被持久化保存。
  - `False`：存在未解决异议但未保存，通常会阻止 commit。

## Session 趋势聚合

可对一个 session 的 round 事件调用 `summarize_session_quality_trends(events)`，得到：

- `round_count`：统计到的 round 数。
- `series`：每轮时间序列（包含上述连续指标与 `dissent_retained`）。
- `averages`：每轮均值（含 `dissent_retained_ratio`）。
- `trends`：每个连续指标的趋势（首尾 `delta` 与 `direction`）。
- `failure_rounds`：失败回合统计（按规则分类 + 去重后的回合索引）。

建议关注：

1. **完整度趋势持续下降**：说明流程可能反复跳过关键步骤。
2. **独立度长期为 0 或路径重叠率偏高**：双评审可能在“换措辞重复”。
3. **去重率偏低**：攻击标签重复，表明批评覆盖面不足。
4. **repair 覆盖率/transfer 有效率走低**：讨论无法把批评转为有效修补。
5. **dissent_retained 出现 False**：应优先修复留存流程，避免丢失争议上下文。

## 如何判断“同模型”是否真的产生差异视角

当多个 seat 来自同一底层模型时，建议不要只看语言风格差异，而应看结构化指标联动：

1. **先看路径是否分叉**：
   - `critique_independence = 1.0` 且 `critic_path_overlap_rate` 较低（例如 `<0.4`）更可信。
2. **再看攻击集合是否扩展**：
   - `attack_label_dedupe_rate` 接近 1 说明不是围绕同一标签反复改写。
3. **看差异是否产生可操作后果**：
   - 若差异批评能提高 `repair_coverage_rate`，说明不是“伪差异”。
4. **看迁移是否闭环**：
   - `transfer_effectiveness_rate` 高，说明结构迁移与修复响应形成闭环，而非仅修辞对照。

实践中可用一个简单判定：
- 若连续多轮出现 `critique_independence=1`、`critic_path_overlap_rate` 低、`attack_label_dedupe_rate` 高，且修复指标（`repair_coverage_rate` / `transfer_effectiveness_rate`）同步稳定在高位，可认为同模型 seat 已形成“功能性差异视角”。
