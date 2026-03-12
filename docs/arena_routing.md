# Arena 输入 Artifact 与下一跳规则

本文档定义 `run_micro_deliberation` 可用 arena 的输入 artifact 类型，以及推荐的下一跳（`next_recommended_arena`）流转规则。

## Arena I/O 与路由

| Arena | 输入 artifact 类型（accepted_artifact_types） | 目标输出 | 推荐下一跳 |
| --- | --- | --- | --- |
| `problem_framing` | `research_idea`, `question_card` | `patch`/`dissent`/`merge` | `counterexample_search` |
| `counterexample_search` | `research_idea`, `counterexample_card` | `patch`/`dissent`/`merge` | `mechanism` |
| `mechanism` | `research_idea`, `mechanism_card` | `patch`/`dissent`/`merge` | `empirical_grounding` |
| `empirical_grounding` | `research_idea`, `data_plan_card` | `patch`/`dissent`/`merge` | `decision` |
| `decision` | `research_idea`, `decision_card` | `patch`/`dissent`/`merge` | `writing_prep` |
| `writing_prep` | `research_idea`, `writing_brief` | `patch`/`dissent`/`merge` | `problem_framing`（下一轮新议题） |

## 规则说明

1. 每个 arena 都要求完整 micro-round：`proposal -> critique_a -> critique_b -> repair -> decision`。
2. obligation 校验以 `config/arenas.yaml` 的 `required_obligations` 为准，未满足时仅允许 `park/continue`。
3. `next_recommended_arena` 在当前实现中默认写入“本轮 arena”；上表提供的是上层编排推荐策略，可由调度器在下一轮覆写。
