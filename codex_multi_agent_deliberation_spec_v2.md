# Multi-Agent Deliberation Engine Spec v2

## 0. Document Status

This document is the **second version** of the project specification.

Version 1 defined the stable backbone:
- artifact-centered deliberation
- arena-by-artifact rather than agent-by-step
- HumanBase-first agent composition
- pluggable perspective modules
- structured persistence and continuation
- external soul injection with governance boundaries

Version 2 does **not** replace that backbone.
Version 2 sharpens it using the current engineering summary and adds the next layer of protocol detail needed for long-term growth.

This document is intended to be passed directly to Codex or another engineering agent as the working implementation target.

---

## 1. Executive Summary

The project should remain defined as:

**a HumanBase-first, artifact-centered, panel-based deliberation engine for research ideation and structured reasoning**.

It is **not**:
- a linear workflow where one agent finishes and passes to the next
- a free-form group chat with weak state discipline
- a system ruled by permanent expert identities
- a soul-driven roleplay system that can alter protocol invariants

The engine should support:
- multiple agents discussing the **same artifact** at the **same step**
- structured rounds with explicit obligations
- reusable artifact lineage instead of disposable chat residue
- continuation across sessions
- later expansion into economics, philosophy, psychology, statistics, physics, law, policy, sociology, and other domains
- external API-driven soul injection without protocol corruption

Version 2 adds the missing details that make future expansion smoother:
- protocol invariants matrix
- module contract matrix
- evidence-linking slots
- conflict typing
- seat eligibility layer
- HumanBase subweights
- dual-ledger soul / cognition separation
- discipline-specific payload drawers
- controlled transfer seat for analogy
- manuscript bridge objects

---

## 2. Core Design Position

### 2.1 Canonical design sentence

The system is an **artifact-centered deliberation engine**.

The object being improved is not the transcript.
The object being improved is an **artifact**.

Artifacts enter arenas.
Panels discuss artifacts inside arenas.
Panels produce structured deltas, dissent, repairs, and governance decisions.
The result is new artifact state and lineage, not just more words.

### 2.2 Canonical rejection sentence

The system must never silently slide back into:
- fixed-stage pipelines
- hidden single-agent authority
- expert-only abstraction detached from ordinary human reasoning
- soul payloads overriding commit rules

### 2.3 Canonical unit of work

The minimum meaningful unit is a **micro-deliberation**:
- one artifact
- one arena
- one panel
- one structured round
- one governance decision or park/continue outcome

---

## 3. Non-Negotiable Requirements

1. Every meaningful step must involve **multiple agents** discussing the **same object**.
2. Expert views must remain **plug-in modules**, not fixed life-long agent identities.
3. Every agent must contain a **HumanBase** layer before discipline-heavy reasoning.
4. Outputs must be saved as **structured state objects**, not only natural-language chat.
5. The system must support **continuation** across sessions.
6. The architecture must remain stable while allowing later expansion into additional disciplines.
7. An external API may inject **SoulProfile** into each agent, but soul must never change governance invariants.
8. The system must preserve unresolved dissent instead of fabricating consensus.
9. External tools must connect to **artifacts and evidence slots**, not directly to a specific expert persona.
10. MVP remains small, but interfaces must already be shaped for long-term reuse.

---

## 4. Design Principles Preserved from v1

The following principles remain unchanged from the earlier specification and prior design discussion:

### 4.1 Arena-by-artifact, not agent-by-step

The architecture should stay organized around artifacts moving through arenas.
Agents do not own permanent stages of a production line.
Panels gather around an artifact and work on it together.

### 4.2 Human first, expert second

An economist, philosopher, statistician, physicist, or psychologist is not a pure discipline shell.
Each agent must retain ordinary human judgment about friction, misunderstanding, incentives, fatigue, cost, convenience, and implementation messiness.

### 4.3 Structured memory, not prompt stuffing

The engine should not “continue” by pasting old chats back into the prompt.
It should continue by loading snapshots, unresolved conflict nodes, artifact versions, and relevant event slices.

### 4.4 Soul bounded by governance

Soul is allowed to color expression, temperament, style, tempo, and stance.
Soul is not allowed to weaken or override precommit checks, dissent preservation rules, or seat obligations.

---

## 5. Current Engineering Status Carried into v2

The new specification should acknowledge that the existing codebase has already reached a meaningful MVP layer.

### 5.1 Already implemented or largely implemented

The current engineering summary indicates the following are already present or substantially present:

- canonical enum vocabulary aligned to decision and arena semantics
- backward-compatible enum alias parsing for legacy values
- schema migration chain across storage versions
- structured artifacts / patches / turns / commits / snapshots
- event log, dissent, and artifact head replay support
- governance checks for unique agents, critiques, persona diversity, field-targeted patches, dissent persistence, and soul non-interference
- round-step structure such as proposal -> critique_a -> critique_b -> repair -> decision
- perspective module registry and initial economics / philosophy / psychology modules
- HumanBase enforcement in agent composition
- SoulProvider contract with validation and allowed-field restriction
- continuation pack construction with budget trimming and unresolved dissent preservation

### 5.2 Current objective gaps

The summary also indicates several real gaps that v2 should address explicitly:

- documentation lag versus implementation depth
- arena execution and seat policy still partially simplified
- module reasoning still heuristic and not yet strongly evidence-grounded
- no formal external API service facade yet
- analytics and evaluation not yet fully exposed

Version 2 is designed to close the conceptual half of these gaps before service hardening begins.

---

## 6. System Layers

The system should now be understood as eight explicit layers.

### 6.1 Artifact Layer

Artifacts are the primary objects under discussion.
Examples:
- `ResearchQuestionCard`
- `MechanismCard`
- `VariableSketchCard`
- `DataPlanCard`
- `EvidenceItem`
- `CritiqueCard`
- `RepairCard`
- `DissentCard`
- `ContinuationPack`
- `Snapshot`
- `ManuscriptCard`

### 6.2 Arena Layer

An arena is a purpose-constrained discussion environment.
Examples:
- `problem_framing`
- `mechanism`
- `empirical_grounding`
- `counterexample_search`
- `decision`
- `writing_prep`

### 6.3 Panel Layer

A panel is the set of agents currently discussing one artifact inside one arena.
Minimum recommendation:
- at least 3 unique agents
- preferably 4 to 5 when conflict richness is desired

### 6.4 Seat Layer

A seat is a round-specific obligation, not a permanent identity.
Examples:
- `proposer`
- `critic`
- `repairer`
- `reframer`
- `synthesizer`
- `dissent_recorder`
- `governor`
- `transfer_seat`

### 6.5 HumanBase Layer

Common human reasoning prior to specialist lenses.
This layer is mandatory.

### 6.6 Perspective Layer

Pluggable domain lenses such as economics, philosophy, psychology, statistics, physics, and future additions.

### 6.7 Soul Layer

External soul injection affecting style and temperament only.

### 6.8 Persistence & Service Layer

Storage, migration, continuation, replay, and future API facade.

---

## 7. Canonical Agent Formula (Updated)

Version 1 used a high-level formula.
Version 2 makes it more explicit.

Canonical agent formula:

`AgentInstance = HumanBase + PerspectiveBundle + SeatPolicy + MemoryView + SoulProfile`

This formula still stands, but v2 clarifies each part.

### 7.1 HumanBase

Mandatory common layer.

### 7.2 PerspectiveBundle

One or more plug-in discipline modules with weights.
No agent is required to be purely single-discipline.

### 7.3 SeatPolicy

Determines what obligation the agent may fulfill in a specific round.
Seat is not lifetime identity.

### 7.4 MemoryView

Defines what historical material is visible to the agent in the current context window.

### 7.5 SoulProfile

Optional external temperament profile with hard governance boundaries.

---

## 8. HumanBase v2: From One Weight to Four Sub-Valves

Version 1 established that every expert must first be human.
Version 2 makes HumanBase more granular so that future expansion and soul injection become more meaningful.

### 8.1 Why a single human weight is too coarse

A single number like `human_weight = 0.4` is useful but not expressive enough.
Two agents may both be “human-heavy” while differing in important ways:
- one notices time cost and implementation burden
- another notices social misreading and trust friction
- another notices attention limits and shortcuts
- another notices plain everyday cause-and-effect mismatch

### 8.2 HumanBase sub-valves

HumanBase should be decomposed into four sub-weights:

1. `practical_friction`
   - time cost
   - effort cost
   - implementation burden
   - coordination messiness
   - fatigue and delay

2. `social_interpretation`
   - trust
   - face-saving
   - defensiveness
   - signaling
   - misunderstanding in human interaction

3. `bounded_attention`
   - memory limits
   - information overload
   - shortcuts
   - neglected details
   - distraction and laziness

4. `ordinary_causality_sense`
   - everyday causal plausibility
   - common-sense sequencing
   - practical mechanism sanity checking

### 8.3 Example representation

```json
{
  "human_base": {
    "practical_friction": 0.35,
    "social_interpretation": 0.20,
    "bounded_attention": 0.15,
    "ordinary_causality_sense": 0.20
  },
  "perspectives": {
    "economics": 0.60,
    "psychology": 0.15
  }
}
```

### 8.4 Why this matters

This decomposition allows:
- finer differentiation across agents with similar discipline weights
- more interpretable soul injection later
- better seat eligibility based on conflict type
- stronger realism in discussion behavior

---

## 9. Perspective Modules v2

### 9.1 Principle

Perspective modules remain plug-in lenses, not whole persons.
They must not define the full agent by themselves.

### 9.2 Initial expected module families

The engine should continue to support and extend:
- `EconomicsModule`
- `PhilosophyModule`
- `PsychologyModule`
- `StatisticsModule`
- `PhysicsModule`
- later: `LawModule`, `PolicyModule`, `SociologyModule`, `EngineeringModule`, and others

### 9.3 Stable interface requirement

Every perspective module must consume the same core inputs:
- current artifact
- local context
- unresolved conflicts
- arena metadata
- optional evidence bundle

Every perspective module must produce the same outer envelope:
- `observations`
- `criticisms`
- `revisions`
- `risks`
- `questions`
- `evidence_needs`
- `confidence`

### 9.4 Discipline-specific payload drawer

In addition to the common outer envelope, a module may return a `discipline_payload` drawer.
This is how future module growth happens without breaking the core protocol.

Examples:

#### Economics payload
- `actors`
- `incentives`
- `constraints`
- `information_asymmetry`
- `equilibrium_tension`

#### Psychology payload
- `decision_bottleneck`
- `bias_risk`
- `attention_failure`
- `emotion_trigger`

#### Statistics payload
- `estimand`
- `identification_risk`
- `measurement_error_source`
- `sampling_concern`
- `confounders`
- `minimum_data_shape`

#### Physics payload
- `state_variables`
- `boundary_conditions`
- `conservation_like_constraints`
- `stability_condition`
- `breakdown_regime`

### 9.5 Why this matters

This design lets future disciplines attach their own drawers to the same cabinet instead of forcing the cabinet to be rebuilt every time.

---

## 10. Artifacts v2

### 10.1 Core artifact principle

Artifacts are the discussion center.
External modules should inject artifacts or evidence into the system, not whisper directly to one expert agent.

### 10.2 Minimum artifact objects

The implementation should keep or support the following object families:
- `ArtifactCard`
- `DeltaPatch`
- `DebateTurn`
- `CommitRecord`
- `DissentRecord`
- `Snapshot`
- `ContinuationPack`
- `ManuscriptCard`

### 10.3 Example ArtifactCard

```json
{
  "artifact_id": "idea_001",
  "type": "research_idea",
  "title": "...",
  "question": "...",
  "mechanism": "...",
  "unit_of_analysis": "...",
  "candidate_explanations": [],
  "outcome_vars": [],
  "open_issues": [],
  "evidence_refs": [],
  "status": "draft",
  "parent_ids": [],
  "version": 3
}
```

### 10.4 Example DeltaPatch

```json
{
  "patch_id": "patch_017",
  "target_artifact_id": "idea_001",
  "target_fields": ["mechanism", "open_issues"],
  "proposed_changes": {},
  "reasons": [],
  "supported_by": [],
  "opposed_by": [],
  "confidence": 0.63
}
```

### 10.5 ManuscriptCard

Version 2 introduces `ManuscriptCard` as a writing bridge object.
This object is not the main discussion target, but a structured outlet that turns lineage into writing-ready components.

Examples:
- `research_question_card`
- `mechanism_card`
- `evidence_gap_card`
- `alternative_explanations_card`
- `design_implication_card`

This avoids a future situation where dozens of JSON files must be manually translated into a paper outline at the last minute.

---

## 11. Arena Model v2

### 11.1 Arena purpose

An arena determines:
- accepted artifact types
- allowed move types
- required obligations
- commit thresholds
- conflict types it specializes in

### 11.2 Recommended initial arenas

1. `problem_framing`
2. `mechanism`
3. `empirical_grounding`
4. `counterexample_search`
5. `decision`
6. `writing_prep`

### 11.3 Arena specialization by conflict type

Arenas should also advertise which conflict categories they are best suited to resolve.
For example:
- `problem_framing` handles definition and scope conflict
- `mechanism` handles causal and structural conflict
- `empirical_grounding` handles measurement and evidence conflict
- `counterexample_search` handles robustness conflict
- `decision` handles accept / branch / park choices
- `writing_prep` handles explanation and document-shaping conflict

---

## 12. Panel and Round Protocol v2

### 12.1 Round protocol must stay explicit

The structured sequence should continue to resemble:
- `proposal`
- `critique_a`
- `critique_b`
- `repair`
- `decision`

This does not force the same named agents to do the same steps every time.
It only requires that the obligations be satisfied.

### 12.2 Obligation layer vs eligibility layer

Version 2 formally splits seat logic into two layers.

#### Obligation layer
What must happen this round?
- at least 1 proposal
- at least 2 independent critiques
- at least 1 repair or merge
- explicit decision or park/continue
- dissent carried forward if unresolved

#### Eligibility layer
Who is allowed or preferred to fill that obligation in this round?
This depends on conflict type, module mix, human-base profile, and session history.

### 12.3 Why this split matters

Without the eligibility layer, the system may silently drift into a hidden mini-pipeline where the same agent always proposes and the same two always critique.
The split keeps the protocol stable while keeping participation adaptive.

---

## 13. Conflict Typing v2

### 13.1 Why conflict typing is needed

Continuation is much more useful when unresolved conflict is not stored as one generic “dissent pile.”
It should be classified.

### 13.2 Conflict types

Recommended first taxonomy:
- `definition_conflict`
- `mechanism_conflict`
- `evidence_conflict`
- `measurement_conflict`
- `scope_conflict`
- `policy_conflict`
- `execution_conflict`

### 13.3 Use of conflict type

Conflict type should influence:
- next arena routing
- seat eligibility
- panel composition
- continuation pack prioritization
- evidence retrieval priority

### 13.4 Example

If the unresolved conflict type is `measurement_conflict`, the system should prefer:
- statistics-heavy seats
- HumanBase agents with strong `practical_friction`
- an arena such as `empirical_grounding`

If the unresolved conflict type is `definition_conflict`, the system should prefer:
- philosophy-heavy or generalist-heavy seats
- `problem_framing` arena

---

## 14. Seat Eligibility v2

### 14.1 Seat is not a fixed profession

A seat is an empty chair with a task attached, not a career identity.
Who sits there should depend on current need.

### 14.2 Eligibility inputs

Seat eligibility may depend on:
- conflict type
- current arena
- unresolved evidence holes
- recent seat repetition frequency
- perspective diversity requirements
- HumanBase subweights
- prior round performance

### 14.3 Example seat preference mapping

If conflict is about realism of behavior:
- prefer psychology-heavy + HumanBase social_interpretation or bounded_attention

If conflict is about feasibility of data collection:
- prefer statistics-heavy + HumanBase practical_friction

If conflict is about stable mechanism structure:
- prefer physics-heavy or economics-heavy depending artifact domain

### 14.4 Anti-repetition rule

No single agent should monopolize the same obligation across too many consecutive rounds unless explicitly justified.
This protects the system from hidden role ossification.

---

## 15. Evidence Linking Contract v2

### 15.1 Why this is needed

Modules should not only produce opinions.
They should indicate where evidence is missing and what kind of evidence is needed.

### 15.2 Support slot requirement

Every criticism, revision, or risk should be allowed or required to carry a `support_slot`.

Example:

```json
{
  "claim_id": "crit_psy_004",
  "text": "The current mechanism over-assumes stable borrower expected-value calculation.",
  "support_slot": {
    "status": "missing",
    "needed_evidence_type": "behavioral_observation",
    "priority": "high"
  }
}
```

### 15.3 Allowed evidence types

Recommended initial values:
- `cited_paper`
- `survey`
- `behavioral_observation`
- `experimental_result`
- `data_pattern`
- `policy_text`
- `interface_trace`
- `expert_note`

### 15.4 Benefits

This contract allows later retrieval, note systems, data search, and web parsing modules to connect to a specific missing-evidence hole instead of blindly flooding the engine with text.

---

## 16. Governance Invariants Matrix

Version 2 requires a machine-checkable matrix mapping design principles to enforceable rules.

### 16.1 Example matrix

| Design principle | Machine-checkable invariant |
|---|---|
| Every step is multi-agent deliberation | `min_unique_agents >= 3` |
| No fake consensus | `independent_critiques >= 2` before accept/branch |
| Repair must target substance | `patch.target_fields not empty` |
| Dissent cannot disappear silently | unresolved dissent persisted unless explicitly resolved |
| Perspectives must not collapse to one lens | persona / perspective diversity threshold enforced |
| Soul must not override protocol | soul fields restricted; governance override blocked |
| Continuation must be replayable | artifact version references + snapshot heads required |

### 16.2 Implementation note

This matrix should live both in documentation and in code-level validation.
Do not let it remain a prose-only aspiration.

---

## 17. Module Contract Matrix

Version 2 also requires a matrix for modules.

### 17.1 Example matrix

| Module family | Required outer envelope | Allowed discipline drawer |
|---|---|---|
| Economics | observations, criticisms, revisions, risks, questions, evidence_needs, confidence | actors, incentives, constraints, information_asymmetry, equilibrium_tension |
| Philosophy | same outer envelope | hidden_premises, definition_shift_risk, falsifier, non_falsifiable_part |
| Psychology | same outer envelope | decision_bottleneck, bias_risk, attention_failure, emotion_trigger |
| Statistics | same outer envelope | estimand, identification_risk, confounders, measurement_error_source |
| Physics | same outer envelope | state_variables, boundary_conditions, stability_condition, breakdown_regime |

### 17.2 Purpose

This prevents future module growth from becoming ad hoc and incompatible.

---

## 18. Soul v2: Bounded Injection + Dual Ledger

### 18.1 What remains true

Soul may be injected externally through API.
Soul may influence:
- tone
- style
- verbal texture
- caution vs boldness
- pacing
- expressive density
- preference for concrete vs abstract framing

Soul may not influence:
- commit threshold
- dissent retention rule
- required critiques
- seat obligation count
- artifact replay semantics
- migration logic

### 18.2 Why boundary alone is not enough

Even with field restriction, future analysis becomes confusing if cognitive reasoning and soul coloration are mixed into one opaque text block.

### 18.3 Dual ledger design

Each agent turn should be recorded as two linked layers:

1. `cognitive_output`
   - structured claims, critiques, revisions, risks, questions, evidence needs

2. `soul_trace`
   - temperament markers, style signals, rhetorical bias, cautiousness, boldness, abstraction preference

### 18.4 Example event link

```json
{
  "turn_id": "turn_089",
  "agent_id": "agent_3",
  "cognitive_output_ref": "cog_017.json",
  "soul_trace_ref": "soul_017.json"
}
```

### 18.5 Benefits

This allows:
- auditing whether a patch won because it was stronger or merely more persuasive in style
- ablation tests where the same cognitive core runs with different soul overlays
- governance that reads the brain ledger while keeping the soul ledger transparent but secondary

---

## 19. Continuation v2

### 19.1 Continuation remains artifact-based

To continue a session, the system should load:
- latest snapshot
- selected artifact versions
- unresolved dissent nodes
- relevant event slices
- evidence holes
- budget-trimmed context bundle

### 19.2 Continuation pack should include conflict typing

Each unresolved conflict must carry:
- conflict type
- originating arena
- affected artifact fields
- unresolved evidence needs
- priority

### 19.3 Continuation goals

Recommended values:
- `deepen_mechanism`
- `find_counterexamples`
- `improve_empirical_design`
- `add_new_discipline_view`
- `resolve_specific_conflict`
- `prepare_for_writing`

### 19.4 Why this matters

Continuation should not mean “resume the old conversation.”
It should mean “resume work on the correct unresolved object with the correct panel and the correct evidence needs.”

---

## 20. TransferSeat: Controlled Analogy as Innovation Channel

### 20.1 Why this exists

The project values cross-domain thinking, but free analogizing can become decorative nonsense.
Version 2 introduces a constrained form of analogy.

### 20.2 TransferSeat definition

`TransferSeat` is a special optional seat.
It does not own proposal or final decision.
It introduces controlled cross-domain mapping.

### 20.3 Required output shape

The seat must output exactly four boxes:
- `source_domain_mechanism`
- `structural_mapping`
- `breakpoints`
- `new_testable_implications`

### 20.4 Example behavior

If the target issue is borrower choice under different interface conditions, a transfer seat may map a simplified physical system or ecological system onto the discussion.
But it must also explicitly record where the analogy breaks because humans interpret, anticipate, hide information, or respond to norms.

### 20.5 Why this is useful

This seat provides innovation while keeping analogical reasoning accountable and falsifiable.

---

## 21. Persistence, Replay, and Storage

### 21.1 Persistence requirement

The system must preserve:
- snapshots
- event log
- artifact heads
- artifact versions
- commit records
- dissent records
- module config used
- soul metadata used

### 21.2 Replay requirement

Artifact versions must be replayable independently of full transcript loading.
The engine should be able to load a specific artifact version and reconstruct relevant lineage context.

### 21.3 Migration requirement

Storage schema must remain versioned and migration-aware.
Canonical enums and compatibility aliases should stay centralized.

---

## 22. External Integration Rule

External tools, search systems, parsers, note stores, and knowledge systems must integrate by injecting:
- `ArtifactCard`
- `EvidenceItem`
- `ContinuationPack`
- `DissentRecord`
- `ManuscriptCard`

They should **not** directly target a specific agent identity as the main integration surface.
The engine decides which panel should process the injected object.

This rule protects the architecture from turning into a tangle of expert-specific shortcuts.

---

## 23. API Contract v1 (Recommended Next Service Layer)

A future service layer should expose a small stable contract rather than leaking internal implementation detail.

Recommended endpoints or function-equivalents:
- `run_round`
- `build_continuation_pack`
- `load_artifact_version`
- `register_perspective_module`
- `register_soul_provider`
- `replay_commit`
- `list_unresolved_conflicts`

Minimal return objects should remain structured, versioned, and machine-checkable.

---

## 24. Analytics and Evaluation

### 24.1 Why this is needed

As the engine becomes more complex, intuition will not be enough to decide whether the protocol is improving.

### 24.2 Suggested metrics

- dissent resolution rate
- branch usefulness rate
- fake-consensus prevention rate
- artifact improvement depth
- evidence-hole closure rate
- seat diversity across rounds
- soul influence separation score
- continuation efficiency under budget limits

### 24.3 Offline evaluation direction

Build a small evaluation harness where the same artifact set is run under:
- no conflict typing vs conflict typing
- coarse HumanBase vs decomposed HumanBase
- no support slots vs evidence-linking support slots
- no dual ledger vs dual ledger

This will give evidence for spec evolution instead of relying on impressionistic judgment.

---

## 25. Recommended File Structure (Updated)

A possible Python-first structure:

```text
project/
  protocol.py
  storage.py
  artifacts.py
  arenas.py
  agents.py
  perspectives.py
  humanbase.py
  soul.py
  governor.py
  engine.py
  continuation.py
  api.py
  eval/
  sessions/
```

Recommended additions beyond the earlier version:
- `humanbase.py` for the decomposed HumanBase model
- `continuation.py` for conflict-typed pack logic
- `api.py` for future FastAPI or service wrapper
- `eval/` for offline protocol experiments

---

## 26. Recommended Next Milestone Order

This order is intentionally different from a naive “just build the API first” plan.

### Milestone 1
Implement and document the **Protocol Invariants Matrix**.

### Milestone 2
Implement the **Evidence Linking Contract** with support slots.

### Milestone 3
Implement **Conflict Typing** and connect it to arena routing and seat eligibility.

### Milestone 4
Decompose **HumanBase** into the four sub-valves.

### Milestone 5
Implement **Soul Dual Ledger**.

### Milestone 6
Only after the above, build the external **API facade** and richer telemetry.

This order strengthens the table legs before adding polished service layers.

---

## 27. Implementation Notes for Codex

Codex should interpret this document as:

1. Preserve the existing architecture direction.
2. Do not rewrite the system into a pipeline framework.
3. Do not collapse perspective modules into fixed character identities.
4. Do not allow soul payloads to reach governance rules.
5. Add the new v2 structures incrementally with backward compatibility where practical.
6. Prefer explicit contracts and typed validation over hidden prompt tricks.
7. Keep all new extensions artifact-centered.

---

## 28. Final Project Definition (v2)

The project should now be defined as:

**A HumanBase-first, artifact-centered, panel-based deliberation engine with structured persistence, replayable lineage, conflict-aware continuation, pluggable discipline modules, and externally injectable but protocol-bounded soul profiles.**

Its goal is not to generate more chat.
Its goal is to create reusable, criticizable, replayable research-state objects that can improve across rounds and across sessions.

That is the stable backbone.
Version 2 adds the missing drawers, valves, hooks, and ledgers needed so that future growth into statistics, physics, law, writing support, and API-driven soul injection can happen without warping the original design.



---
Below are some intermediary thoughts and additional information.

这份工程总结整体上是有价值的，而且方向基本没有背离你的原始核心约束。

最重要的好消息是：项目已经不再是最早那种“几个 agent 分守几段流水线”的形态，而是已经落到 **HumanBase-first、artifact-centered、structured micro-deliberation、governance invariants、continuation、pluggable perspectives、soul guardrails** 这条线上了。工程师已经补上了几块最容易塌的地基：协议枚举统一与迁移链、artifact 版本回放、回合步骤结构化、模块注册机制、以及 soul 不得越权改治理规则。这个判断不是空话，摘要里明确写了 canonical enum、v1→v2→v3 migration、artifact_heads、ROUND_STEPS、registry-based modules、SoulProvider validation 和 governance override protection。 

所以我的总判断是：**这不是推倒重来项目，而是“保持原框架不变，进入第二阶段精化”的项目。** 现在最不该做的事情，是因为看到还有缺口，就重新发明一整套新框架；最该做的，是把现有骨架上几处还比较粗的连接口、阀门、抽屉隔板做细。工程总结自己也承认了当前缺口集中在 seat policy 仍偏简化、模块推理仍偏 heuristic、缺 API facade、缺 analytics 与 eval 闭环。 

下面我直接说，在**不改变你原有原则**的前提下，我认为最值得加入的细化与创新。

---

## 一、原有原则不要变，但要再“钉死”成两张表

你原本的根原则其实已经很清楚了：

不是 agent-by-step，而是 arena-by-artifact；
不是固定人格岗位，而是 seat + 可插 perspective；
不是聊天堆积，而是 artifact lineage；
不是灵魂决定制度，而是 soul 只能影响风格和气质。 

但现在还差两张特别关键的表。

第一张叫 **Protocol Invariants Matrix**。
这张表不是解释理念，而是把理念逐格变成机器可检查的规则。比如：

“每步多人讨论” 对应 `min_unique_agents >= 3`
“不能假共识” 对应 `independent_critiques >= 2`
“不能空泛修补” 对应 `patch must target artifact fields`
“少数意见不能丢” 对应 `unresolved dissent persisted before accept/branch`

工程总结里已经明确建议把这个矩阵写进下一版 spec，这个建议我完全赞成，而且我认为优先级比 FastAPI 还高。因为没有这张表，后面的 API 只是把含糊规则包成 HTTP 接口而已。

第二张叫 **Module Contract Matrix**。
这张表专门服务你未来要加统计学、物理学、法律、社会学这些模块。不要只写“可插拔”，要写清楚每个模块必须交什么格子。比如桌上一张白卡片上写着一个研究问题，任何模块都必须至少吐出：

`observations`
`criticisms`
`revisions`
`risks`
`questions`
`evidence_needs`
`confidence`

然后再允许各学科加自己的专属抽屉。这样以后加 physics module 时，它不会破坏主循环，只是在统一铁柜里多塞一个小抽屉。

---

## 二、真正还缺的，不是“更多模块”，而是“模块输出和证据的钩子”

工程总结已经指出模块推理还是 heuristic MVP，尚未变成 evidence-grounded strategy engine，并建议增加 evidence linking contract。这里我认为他说对了，但还说得不够细。

我建议你把每次模块输出，从“只是一个观点包”升级成“观点 + 证据挂钩点”。

具体做法很简单：

每条 criticism、revision、risk，不允许只是文字，必须至少带一个 `support_slot`。
这个 `support_slot` 不是必须马上有证据，而是先预留插口，形状固定，比如：

```json
{
  "claim_id": "crit_psy_004",
  "text": "当前机制过度假设借款人稳定计算预期收益",
  "support_slot": {
    "status": "missing",
    "needed_evidence_type": "behavioral_observation | survey | experimental_result | cited_paper | data_pattern",
    "priority": "high"
  }
}
```

这样模块不再只是围着白板说话，而是会在白板旁边贴一张黄色便签：
“这里需要一篇论文摘要”
“这里需要一列真实借款行为数据”
“这里需要一个 UI 界面 A/B 的结果”

这会直接改善两个东西。
一是 continuation pack 更有用，因为续跑时不只是带 unresolved dissent，还能带 unresolved evidence holes。
二是以后外部功能接入时，检索模块、网页解析模块、论文笔记模块都知道自己该往哪个洞里塞东西，而不是盲目往系统里扔一摞纸。原始框架里已经强调“外部功能接 artifact，不接 agent”，而 evidence slot 会把这个思想再推进一步，变成“外部功能接 artifact 上的具体孔位”。 

---

## 三、Seat policy 现在还太像固定椅子，建议升级成“义务 + 资格”的双层制度

工程师总结说 seat policy 还比较简化，这个判断很关键。

现在最容易出现的问题是：虽然名义上不是流水线了，但运行时仍可能暗暗退化成固定座位剧本。比如 proposal 永远由 A 来做，critique 永远由 B 和 C 来做，repair 永远由 D 来做。这样久了以后，系统会像会议室里四张贴着名字的椅子，形式上有 panel，实质上仍是小流水线。

我建议你把 seat policy 再分成两层。

第一层是 **obligation layer**。
本轮必须完成什么动作：proposal、critique_a、critique_b、repair、decision。这个你们已经有了。 

第二层是 **eligibility layer**。
谁在本轮有资格坐这个椅子，不是固定写死，而是按当前冲突类型动态决定。

例如：

如果当前 unresolved conflict 是 “定义含糊”，优先给 philosophy-heavy 或 generalist-heavy seat。
如果当前 unresolved conflict 是 “变量不可测”，优先给 statistics-heavy seat。
如果当前 unresolved conflict 是 “机制不符合现实行为”，优先给 psychology-heavy + HumanBase-heavy seat。
如果当前 unresolved conflict 是 “存在硬约束或守恒式关系”，优先给 physics-heavy seat。

也就是说，seat 不是固定岗位，而是一个空椅子；谁来坐，要看桌上那张卡片最缺哪只手。这样就和你说的“专家首先是人，同时带自己的共通生活经验”更一致，因为 seat 不再是职业工位，而是讨论中的临时职责位。

---

## 四、HumanBase 现在虽然“必须存在”，但还太粗，建议拆成四个小阀门

总结里说 HumanBase 已经被强制在 agent composition 里，这是对的。 
但“有”不等于“够细”。

你最早强调的不是单纯要一个 generalist，而是每个专家首先是人，要有“共通的生活经验”并且可调权重。这个要求如果只用一个 `human_base: 0.4` 的数字来表示，还是太粗。

我建议把 HumanBase 再拆成四个可调子阀门：

`practical_friction`
看现实执行麻烦、成本、拖延、误解、疲劳。

`social_interpretation`
看人际互动、信任、面子、防御、沟通落差。

`bounded_attention`
看注意力、记忆限制、信息过载、偷懒捷径。

`ordinary_causality_sense`
看日常因果直觉，避免专家在空中兜圈子。

这样一个 economics-heavy agent 不再只是：

`HumanBase 0.4 + Economics 0.6`

而会更具体：

```json
{
  "human_base": {
    "practical_friction": 0.35,
    "social_interpretation": 0.20,
    "bounded_attention": 0.15,
    "ordinary_causality_sense": 0.20
  },
  "perspectives": {
    "economics": 0.60,
    "psychology": 0.15
  }
}
```

这个设计的好处很实在。
同样是两位 economics agent，一个可能更像盯预算表和合同条款的人，另一个可能更像懂人情、知道用户会怎么偷懒的人。你以后给 agent 注入 soul 时，也更容易让“灵魂”真正落在这些细节上，而不是只会调语气词和风格颜色。

---

## 五、Soul 现在防越权做得对，但还缺“魂与脑分离账本”

现在 soul 防越权这部分做得是正确的：只能影响 style/temperament，不能碰 governance。

但如果你未来真的要通过 API 给每位 agent 赋予“灵魂”，仅仅限制字段还不够，还需要**双账本**。

我建议把每次 agent 发言拆成两层记录：

`cognitive_output`
这层记录结构化观点、批评、修补、风险、证据需求。这是“脑”。

`soul_trace`
这层只记录风格偏向、气质张力、表达节奏、倾向保守还是冒险、倾向具体还是抽象。这是“魂”。

然后在事件日志里分开写：

```json
{
  "turn_id": "...",
  "agent_id": "...",
  "cognitive_output_ref": "cog_017.json",
  "soul_trace_ref": "soul_017.json"
}
```

这样有三个好处。

第一，你以后可以单独回看“这个 patch 是因为论证更强，还是因为某个灵魂更会说话”。
第二，你可以做 soul ablation test，把同一 cognitive core 配不同 soul，看回合结果变化。
第三，最关键的是，治理层看的是脑，不看魂；魂只能影响表达温度和视角色彩，不能通过绕路污染 commit gate。

这一步对你这种“API 注魂”项目特别重要，因为它会把灵魂从一团雾，变成一个可比较、可记录、可拔掉的透明零件。

---

## 六、continuation 现在有了，但还缺“冲突分型打包”

工程总结里 continuation 已经能做 snapshot-priority extraction、lineage-aware filtering、budget trimming，并且会保留 unresolved dissent nodes。这个很不错。 

但我建议再走一步：
不要只打包“未解决异议”，还要给异议**分型**。

也就是 continuation pack 里，每个 unresolved node 必须多一个字段：

`conflict_type`

例如：

`definition_conflict`
`mechanism_conflict`
`evidence_conflict`
`measurement_conflict`
`scope_conflict`
`policy_conflict`
`execution_conflict`

这样下一轮 panel 组装就不再靠模糊直觉，而是会更像从文件柜里抽出一张红色卡片，上面写着“measurement_conflict”，系统立刻知道应该叫 statistics-heavy 和 HumanBase-practical-heavy 的 agent 先上桌。

这会把 continuation 和 adaptive panel composition 真正连起来，而不是只停留在“以后可以自适应”的口号层。工程总结里已经把 adaptive panel composition 和 dissent portfolio ranking 列为战略扩展，我的建议是把这两件事合并：**先做 conflict typing，再做 adaptive composition**。 

---

## 七、给统计学、物理学这些未来模块，先把“专属抽屉”预留好

你已经明确说了，经济学、哲学、心理学只是例子，未来还会有统计学、物理学，甚至更多。那就不要等模块来了再想字段。

现在就预留一层 `discipline_payload`。

统一输出外壳不变，但允许每个模块带一个小抽屉。例如：

统计学模块可以带：

`estimand`
`identification_risk`
`measurement_error_source`
`sampling_concern`
`confounders`
`minimum_data_shape`

物理学模块可以带：

`state_variables`
`boundary_conditions`
`conservation_like_constraints`
`stability_condition`
`breakdown_regime`

心理学模块可以带：

`decision_bottleneck`
`bias_risk`
`attention_failure`
`emotion_trigger`

经济学模块可以带：

`actors`
`incentives`
`constraints`
`information_asymmetry`
`equilibrium_tension`

这样未来加模块时，不需要推翻统一壳，只是在抽屉柜里多装一个小木盒。

---

## 八、最值得加的一个创新：受约束的“类比迁移席位”!!!!!!!!! 重要

这点是我最想补给你的创新，而且和你原本喜欢跨学科迁移很合。

你之前就隐含表达过，不希望专家只在本学科里打转，而希望他们有平移能力。但自由平移容易变成漂亮口号。原始讨论里其实已经出现过 `Analogical Transfer Agent` 的想法。

我建议把它正式化成一个可选 seat，不是模块。

叫 `TransferSeat`。
它不负责直接 proposal，也不负责最终 decision。
它专门做“受约束类比”，输出固定四格：

`source_domain_mechanism`
`structural_mapping`
`breakpoints`
`new_testable_implications`

举个很具体的白板例子。
桌上的卡片写着：“平台是否通过信息界面设计改变借款人风险选择？”
一个 physics-heavy + psychology-light 的 TransferSeat 不允许只说“这像势阱”这种空话。它必须写：

源域机制：粒子在不同势阱之间切换
结构映射：借款人注意力和风险展示像势场变化
断裂点：人不是粒子，会解释、会防御、会受面子影响
新可检验推论：如果界面降低局部注意负担，风险选择转移应在信息密度过高组更明显

这类 seat 的价值很大，因为它能带来创新，但又被四格铁框卡住，不会胡飘。

---

## 九、研究写作桥接要尽早设计，不要等最后再拼论文

工程总结把 “artifact lineage -> structured manuscript outline” 放进战略扩展，这个方向我同意，而且我建议比他们说的更早做。

原因很简单：你这个系统不是做聊天玩具，而是想做能沉淀研究资产的机器。那产物最好一开始就考虑怎么变成论文、报告、proposal，而不是最后才拿一大箱 JSON 拼稿子。

最实用的做法是，在 artifact 旁边再加一种对象：

`ManuscriptCard`

它不是讨论主对象，而是写作用的整理卡。比如：

`research_question_card`
`mechanism_card`
`evidence_gap_card`
`alternative_explanations_card`
`design_implication_card`

每次 commit 或 branch 后，系统不一定马上生成整段 prose，但可以更新这些写作卡。
这样到后面写 project note、thesis memo、proposal 或 paper outline 时，你打开的不是一摞日志，而是一叠已经分好类别的卡片。

---

## 十、我给你的最终建议顺序

如果你现在要在“原有框架不变”的前提下继续推进，我建议顺序不是工程师给的原样顺序，而是微调成下面这个次序：

先做 **Protocol Invariants Matrix**。
再做 **Evidence Linking Contract**。
再做 **Conflict Typing + Adaptive Seat Eligibility**。
再做 **HumanBase 子阀门拆分**。
再做 **Soul 双账本**。
然后才做 **FastAPI facade**、**telemetry dashboard**、**offline eval suite**。

原因很直接：前五项是在加厚桌子腿和抽屉隔板，后几项更像给桌子刷漆、装玻璃门、挂标签。没有前面的结构细化，后面的服务层和面板只是把半成品更漂亮地暴露出去。

---

## 十一、最短的结论

这位工程师的总结，值得保留的部分很多，尤其是他已经把你最早那些危险点处理掉了：口径漂移、soul 越权、日志不可回放、回合不可审计、单模块 stub 扩展差。

但如果你现在想在**不改原理**的前提下继续向前，真正该补的不是“再多三个模块”，而是这五样更细的底层件：

**证据挂钩点**
**冲突分型**
**seat 资格层**
**HumanBase 子阀门**
**魂脑双账本**

这五样一旦补上，你后面接统计学、物理学、法律模块，接 API 注魂，接论文写作桥，都会顺得多。

如果你下一步愿意贴代码，最值得先看的六个文件是：`engine.py`, `governor.py`, `perspectives.py`, `protocol.py`, `agents.py`, `soul.py`。这样就能把上面这些建议压成函数级修改方案，而不是继续停在原则层。







