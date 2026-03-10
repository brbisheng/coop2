# Multi-Agent Deliberation Engine Spec

## 1. Purpose

This document defines a Python-first multi-agent deliberation engine for research ideation and structured discussion.

The target system is **not** a pipeline in which one agent fetches data, another cleans data, and another writes a summary. Instead, multiple agents discuss the **same object** at the **same step**. They propose, attack, reframe, repair, and escalate the same artifact until the artifact becomes sharper, more testable, and more executable.

The first production target is **research idea generation and refinement**, but the architecture must be reusable later for other collaborative reasoning tasks.

---

## 2. Core Design Position

### 2.1 What this system is

This system is an **artifact-centered deliberation engine**.

The central object is not a chat transcript and not a task queue. The central object is an **artifact**: for example, a research question card, a mechanism card, a data plan card, a critique card, or an evidence card.

The system runs by sending an artifact into an **arena**. Inside the arena, a **panel** of agents discusses that same artifact. The panel does not split the artifact into independent jobs. The panel argues over the same card.

### 2.2 What this system is not

This system is not:
- a linear workflow where agent A finishes a block and passes it to agent B
- a free-form group chat with no state discipline
- a set of permanent expert identities that dominate all reasoning
- a prompt-only persona wrapper with no structural constraints

---

## 3. Non-Negotiable Requirements

1. **Every step must involve multiple agents discussing the same object.**
2. **Expert views must be plug-in modules, not fixed life-long agent identities.**
3. **Each agent must have a common human layer before any expert layer.**
4. **Discussion results must be stored as structured artifacts, not only natural-language chat.**
5. **The system must support continuation.** Previous results must be reusable in future sessions.
6. **The system must support future expansion** into additional disciplines such as statistics, physics, law, sociology, policy, or engineering.
7. **An external API must be able to inject “soul” into each agent** without controlling the core reasoning protocol.
8. **MVP first, architecture stable.** The first implementation must be small but the interfaces must already support later expansion.

---

## 4. Conceptual Model

### 4.1 The correct mental picture

Imagine one wooden table.

At the center of the table lies one card: a research idea card.
Next to it lies a second sheet: a variable sketch.
Beside it lies a third sheet: a data-source note.
Several agents sit around the table. They all look at the same card. They do not walk away with separate pieces.

One agent proposes.
Another attacks.
Another reframes.
Another repairs.
Another records dissent.
A governor decides whether the card should be accepted, branched, parked, or sent into another arena.

This is the intended behavior.

### 4.2 The correct unit of work

The smallest meaningful work unit is **not** a single agent.
The smallest meaningful work unit is a **micro-deliberation**:
- one artifact
- one arena
- one panel
- one structured round of propose / critique / repair / commit decision

---

## 5. System Layers

## 5.1 Layer A: Artifact Layer

Artifacts are the objects being discussed.

Examples:
- `ResearchQuestionCard`
- `MechanismCard`
- `DataPlanCard`
- `EvidenceItem`
- `CritiqueCard`
- `RepairCard`
- `DissentCard`
- `Snapshot`

All important system progress must be expressible as artifacts.

## 5.2 Layer B: Arena Layer

An **arena** is a discussion environment with a specific purpose.

Examples:
- `problem_framing`
- `mechanism`
- `empirical_grounding`
- `counterexample_search`
- `decision`
- `writing_prep`

An arena defines:
- what artifact types it accepts
- what seats must be present
- what output actions are allowed
- what commit conditions must be satisfied

## 5.3 Layer C: Panel Layer

A **panel** is the group of agents currently discussing one artifact inside one arena.

A panel is the minimum required discussion unit.

Default requirement:
- at least 3 agents
- preferably 4 agents for richer conflict and repair

## 5.4 Layer D: Seat Layer

A **seat** is a functional discussion obligation, not an expert identity.

Examples:
- `proposer`
- `critic`
- `reframer`
- `repairer`
- `synthesizer`
- `governor`
- `dissent_recorder`

A seat answers the question: **what kind of move is this participant required to make in this round?**

## 5.5 Layer E: Cognitive Layer

Each agent is built from multiple cognitive layers.

This is critical.

An agent is **not** just “economist” or “philosopher.”
Each agent must have:

1. `HumanBase`
2. `PerspectiveBundle`
3. `SeatPolicy`
4. `MemoryView`
5. `SoulProfile`

This becomes the canonical agent formula:

`AgentInstance = HumanBase + PerspectiveBundle + SeatPolicy + MemoryView + SoulProfile`

## 5.6 Layer F: Persistence Layer

The system must save:
- event log
- artifacts
- commits
- dissent
- snapshots
- configuration used in each session

Without persistence, continuation is fake.

---

## 6. HumanBase: Expert First as Human? No. Human First.

This is a core requirement.

Every agent must first contain a **HumanBase** layer before any expert module is applied.

### 6.1 Why this layer exists

The system should not create agents that only think in pure discipline abstractions.
An economist must still ask ordinary human questions.
A philosopher must still notice ordinary human friction.
A statistician must still notice ordinary constraints in behavior and communication.

### 6.2 What HumanBase represents

HumanBase encodes common everyday reasoning such as:
- people get tired
- organizations hide information
- incentives are mixed
- communication is misunderstood
- time and money are limited
- social pressure changes behavior
- risk aversion matters
- habit and convenience distort action
- implementation is often messier than theory

### 6.3 HumanBase must be weighted

HumanBase is not a binary switch.
It must have a weight.

Example:
- Agent A: `human 0.45 + economics 0.35 + philosophy 0.10 + psychology 0.10`
- Agent B: `human 0.50 + statistics 0.25 + physics 0.15 + economics 0.10`

This weight is required because the user explicitly wants each expert to remain a person with common life experience, not just a discipline shell.

---

## 7. Perspective Modules

Perspective modules are plug-in cognitive lenses.
They are not full agents.
They are not permanent identities.
They are interchangeable modules with stable interfaces.

### 7.1 Initial module families for MVP

Recommended first set:
- `EconomicsModule`
- `PhilosophyModule`
- `PsychologyModule`

### 7.2 Planned later modules

Must be supported without redesign:
- `StatisticsModule`
- `PhysicsModule`
- `LawModule`
- `SociologyModule`
- `PolicyModule`
- `EngineeringModule`
- `HistoryModule`

### 7.3 Plug-in principle

A new module must be addable by implementing the same contract.
No engine rewrite should be needed.

### 7.4 Mandatory module interface

Each module must receive the same inputs and return the same outer schema.

Suggested interface:

```python
class PerspectiveModule(Protocol):
    name: str
    version: str

    def audit(
        self,
        artifact: dict,
        local_context: dict,
        unresolved_conflicts: list[dict],
    ) -> dict:
        ...
```

Mandatory output fields:
- `observations`
- `criticisms`
- `revisions`
- `risks`
- `questions`
- `evidence_needs`
- `confidence`

The internals differ by module, but the external shape stays stable.

### 7.5 Examples of module-specific checks

#### EconomicsModule
Checks:
- incentive structure
- constraints
- information asymmetry
- transaction costs
- strategic responses
- feasibility of observable proxies

#### PhilosophyModule
Checks:
- core claim
- hidden premises
- definition drift
- falsifier
- internal tension between principle and example

#### PsychologyModule
Checks:
- confirmation bias risk
- premature convergence risk
- narrative comfort risk
- unrealistic assumptions about attention, memory, fatigue, fear, status, or trust

#### StatisticsModule (future)
Checks:
- identification logic
- observability
- sampling logic
- model misspecification risk
- measurement error path

#### PhysicsModule (future)
Checks:
- conservation-like constraints
- dynamic stability intuition
- system interaction structure
- scaling behavior
- equilibrium or non-equilibrium framing if relevant

---

## 8. Soul Injection API

The user will later call an external API to give each agent a “soul.”
This must be supported explicitly.

### 8.1 What soul is allowed to affect

The soul layer may affect:
- tone
- temperament
- tolerance for ambiguity
- patience level
- conversational sharpness
- narrative style
- priority preferences among equally valid moves

### 8.2 What soul is not allowed to control

Soul must not override:
- commit rules
- minimum critique requirements
- artifact schema
- persistence rules
- safety rules
- arena protocol

### 8.3 Soul contract

```python
class SoulProvider(Protocol):
    def get_soul_profile(self, agent_id: str) -> dict:
        ...
```

Example `SoulProfile` fields:
- `voice_style`
- `temperament`
- `ambiguity_tolerance`
- `assertiveness`
- `conflict_style`
- `curiosity_bias`
- `repair_bias`
- `patience`

### 8.4 Separation rule

Soul must be treated as a late-stage personalization layer.
It must sit on top of HumanBase and PerspectiveBundle, not replace them.

---

## 9. Core Objects

## 9.1 ArtifactCard

```python
{
  "artifact_id": "idea_001",
  "type": "research_idea",
  "title": "...",
  "question": "...",
  "mechanism": "...",
  "unit_of_analysis": "...",
  "outcome_vars": ["..."],
  "candidate_explanations": ["..."],
  "evidence_refs": ["..."] ,
  "open_issues": ["..."],
  "status": "draft|active|branched|parked|accepted",
  "parent_ids": ["..."],
  "version": 1
}
```

## 9.2 DeltaPatch

```python
{
  "patch_id": "patch_017",
  "target_artifact_id": "idea_001",
  "proposed_changes": {"mechanism": "..."},
  "reasons": ["..."],
  "supported_by": ["agent_A"],
  "opposed_by": ["agent_B"],
  "confidence": 0.64
}
```

## 9.3 DebateTurn

```python
{
  "turn_id": "turn_089",
  "arena": "mechanism",
  "seat": "critic",
  "agent_id": "agent_B",
  "persona_mix": {"human": 0.4, "economics": 0.4, "philosophy": 0.2},
  "input_artifact_id": "idea_001",
  "output_type": "critique",
  "output_ref": "patch_017",
  "timestamp": "..."
}
```

## 9.4 CommitRecord

```python
{
  "commit_id": "commit_021",
  "artifact_id": "idea_001",
  "decision": "accept|branch|park|reject",
  "accepted_patch_ids": ["patch_017"],
  "dissent_patch_ids": ["patch_019"],
  "judge_notes": "...",
  "why_not_others": ["..."]
}
```

## 9.5 Snapshot

```python
{
  "snapshot_id": "snap_009",
  "session_id": "session_003",
  "active_artifacts": ["idea_001", "idea_004"],
  "priority_open_issues": ["..."],
  "latest_commits": ["commit_021"],
  "next_recommended_arena": ["empirical_grounding"]
}
```

---

## 10. Arena Spec

An arena must be configured explicitly.

Example:

```python
{
  "arena_name": "mechanism",
  "accepted_artifact_types": ["research_idea", "mechanism_card"],
  "required_obligations": {
    "propose": 1,
    "independent_critiques": 2,
    "repair_or_merge": 1
  },
  "min_unique_agents": 3,
  "min_persona_diversity": 2,
  "allowed_outputs": ["patch", "dissent", "merge"],
  "commit_threshold": {
    "response_to_critiques_required": true,
    "dissent_must_be_saved": true
  }
}
```

### 10.1 Recommended initial arenas

MVP should start with only 3 arenas:
- `problem_framing`
- `mechanism`
- `empirical_grounding`

Later add:
- `counterexample_search`
- `policy_translation`
- `writing_prep`
- `decision`

---

## 11. Seats and Obligations

Seats are not ordered assembly-line stations.
They are obligations that must be satisfied inside a micro-deliberation.

Recommended obligation set:
- `propose >= 1`
- `independent_critiques >= 2`
- `repair_or_merge >= 1`
- `dissent_recorded >= 1 if disagreement persists`

This is better than a fixed sequence because it guarantees real discussion without forcing the same rigid ordering every time.

### 11.1 Recommended seat types for MVP

- `proposer`
- `critic`
- `critic`
- `repairer_or_synthesizer`
- `governor`

The governor may be separate or may act after reviewing the structured outputs from the rest.

---

## 12. System Invariants

These invariants must be enforced in code.
They are not optional narrative suggestions.

1. `unique_agents >= 3` before any commit
2. `independent_critiques >= 2` before any accept/branch decision
3. every accepted patch must target explicit artifact fields
4. unresolved dissent must be stored, not discarded
5. no artifact may loop in the same arena more than `N` times without `park` or `branch`
6. panel persona mix cannot remain identical for too many consecutive rounds
7. soul personalization cannot bypass the protocol

---

## 13. Discussion Protocol

### 13.1 MVP round structure

Each micro-deliberation follows this general structure:

1. **Proposal**
   - one participant proposes a patch to the current artifact
2. **Independent critique A**
   - first critic attacks mechanism, assumptions, evidence, or framing
3. **Independent critique B**
   - second critic attacks from a genuinely different angle
4. **Repair / merge**
   - repairer or synthesizer tries to produce improved patch or explicit branch proposal
5. **Governor decision**
   - accept / branch / park / reject
6. **Snapshot update**
   - system updates live state and persistence layer

### 13.2 Why two critiques are mandatory

Without two independent critiques, the system collapses too easily into agreement theater.
One critic is often only a mirror.
Two critics create tension and force more robust repair.

### 13.3 Why dissent must be saved

Many useful future breakthroughs emerge from minority objections that were unresolved in the current round.
Therefore dissent is part of the research asset base.

---

## 14. Commit Policy

A commit policy decides whether the artifact state may change.

Allowed decisions:
- `accept`
- `branch`
- `park`
- `reject`

### 14.1 Meaning of each decision

#### accept
The proposed repair is good enough to become the new main line.

#### branch
There are two plausible directions and it is too early to collapse them into one.
A new child artifact should be created.

#### park
The issue is unresolved and should be stored for later, often because evidence is missing.

#### reject
The proposal is weak enough that it should not survive.

### 14.2 Governor responsibilities

The governor must explicitly answer:
- what changed
- why this change was accepted or branched
- which critiques were answered
- which critiques remain open
- why alternatives were not selected

---

## 15. Continuation and Long-Term Reuse

The system must support continuing prior work without flooding the context window.

### 15.1 Save two things every session

1. `event_log.jsonl`
   - detailed chronological history
2. `snapshot.json`
   - condensed current state

### 15.2 Continuation flow

When continuing a session:
1. load latest snapshot
2. identify continuation goal
3. retrieve only relevant historical events
4. reopen selected artifacts in appropriate arenas

### 15.3 Supported continuation goals

Initial recommended types:
- `deepen_mechanism`
- `find_counterexamples`
- `improve_empirical_design`
- `add_new_discipline_view`
- `resolve_specific_conflict`
- `prepare_for_writing`

---

## 16. Storage Model

Recommended file-level persistence layout:

```text
project_root/
  config/
    agents.yaml
    arenas.yaml
    modules.yaml
    soul_provider.yaml
  src/
    artifacts.py
    agents.py
    human_base.py
    perspectives.py
    soul.py
    arenas.py
    seats.py
    protocol.py
    governor.py
    memory.py
    storage.py
    engine.py
  data/
    sessions/
      session_001/
        snapshot.json
        event_log.jsonl
        commits.jsonl
        artifacts/
          artifact_idea_001_v1.json
          artifact_idea_001_v2.json
          artifact_idea_001_v3.json
        dissent/
          dissent_003.json
  tests/
    test_artifacts.py
    test_protocol.py
    test_governor.py
    test_continuation.py
```

### 16.1 Why artifact lineage matters

This is how the system becomes reusable.
The output of one discussion is not a dead transcript.
It becomes an input object for the next session.

---

## 17. Implementation Plan

## 17.1 Phase 1: Freeze the contracts

Must implement first:
- artifact schema
- arena schema
- seat obligations
- HumanBase contract
- PerspectiveModule interface
- SoulProfile interface
- snapshot format

No UI needed.
No fine-tuning needed.

## 17.2 Phase 2: Build the core engine

Implement:
- artifact creation and versioning
- panel assembly
- one arena loop
- event logging
- commit policy
- snapshot writing

## 17.3 Phase 3: Add three initial modules

Implement:
- EconomicsModule
- PhilosophyModule
- PsychologyModule

## 17.4 Phase 4: Add continuation

Implement:
- load snapshot
- select continuation goal
- retrieve relevant prior events
- reopen artifacts in chosen arena

## 17.5 Phase 5: Add soul API adapter

Implement:
- SoulProvider contract
- SoulProfile validation
- safe merge into agent runtime state

## 17.6 Phase 6: Add more discipline modules

Later modules should plug into the same PerspectiveModule contract.
No engine rewrite should be required.

---

## 18. MVP Scope vs Long-Term Scope

### 18.1 MVP must do only this

Given a research topic or half-formed idea, the system should:
- create one or more initial artifacts
- run panel-based discussion in 3 arenas
- produce revised artifact(s)
- save structured state
- allow continuation later

### 18.2 MVP must not try to do this yet

- universal task orchestration
- automatic web search integration everywhere
- multi-model optimization
- heavy reinforcement learning
- complicated front-end
- auto-writing full papers

### 18.3 Long-term scope

Later expansion may include:
- new discipline modules
- evidence retrieval tools
- document parsing
- planning-to-writing pipelines
- adaptive panel composition
- module-performance analytics
- selective training of critic or governor components

---

## 19. Failure Modes and Safeguards

### Failure mode 1: fake diversity
All agents sound different but produce the same logic.

**Safeguard:** require real output differences, not stylistic differences.

### Failure mode 2: expert domination
One module, such as economics, absorbs everything.

**Safeguard:** HumanBase always present; module weights configurable; persona diversity requirement in panel.

### Failure mode 3: collapse into agreement
Everyone converges too quickly.

**Safeguard:** two independent critiques required; dissent saved.

### Failure mode 4: endless arguing
The system debates forever.

**Safeguard:** loop limit per arena; governor can park or branch.

### Failure mode 5: soul hijacks reasoning
A dramatic personality overrides structure.

**Safeguard:** soul restricted to style, temperament, and local preferences only.

### Failure mode 6: transcript accumulation instead of structured progress
Discussion becomes a pile of text.

**Safeguard:** every important move must point to artifacts, patches, commits, or dissent records.

---

## 20. Canonical Summary

This project should be implemented as:

**a HumanBase-first, artifact-centered, panel-deliberation engine with plug-in perspective modules, structured persistence, continuation support, and external soul injection.**

The system center is not the agent.
The system center is the evolving artifact lineage.

The correct organizational formula is:

`Session = Artifact Lineage + Arena Loop + Panel Deliberation + Commit Policy + Persistence`

The correct runtime formula for each participant is:

`AgentInstance = HumanBase + PerspectiveBundle + SeatPolicy + MemoryView + SoulProfile`

---

## 21. Immediate Instruction for Codex

When generating the first implementation, Codex should:

1. prioritize stable interfaces over feature count
2. build the artifact, arena, protocol, and persistence skeleton first
3. treat HumanBase as mandatory
4. treat perspective modules as plug-ins
5. treat soul as a separate optional adapter layer
6. implement continuation early
7. avoid framework-specific assumptions from AutoGen, LangGraph, or CAMEL
8. keep the first codebase plain Python and testable

---

## 22. Minimum Deliverables for First Coding Pass

Codex should produce at minimum:
- `artifacts.py`
- `agents.py`
- `human_base.py`
- `perspectives.py`
- `arenas.py`
- `protocol.py`
- `governor.py`
- `storage.py`
- `engine.py`
- `config/agents.yaml`
- `config/arenas.yaml`
- `tests/test_protocol.py`
- `tests/test_continuation.py`

This is the correct starting skeleton.
