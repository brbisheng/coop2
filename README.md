# coop2

Python-first skeleton for a multi-agent deliberation engine focused on artifact-centered continuation.

## Current capabilities

- Unified model validation primitives (`src/artifacts.py`, `src/protocol.py`).
- Precommit governance checks for independent critique, persona diversity, unique-agent minimum, field-targeted patches, and unresolved dissent handling (`src/governor.py`).
- Continuation retrieval pack construction with lineage-aware filtering and budget trimming (`src/memory.py`, `src/engine.py`).
- Runnable CLI for continuation pack inspection.
- Demo session data for reproducible local runs.

## Quick start

### 1) Run tests

```bash
python -m pytest -q
```

### 2) Run continuation demo (summary)

```bash
python -m src.engine \
  --session-dir data/sessions/demo_session \
  --goal resolve_specific_conflict \
  --target-artifact-id artifact_main_v3 \
  --recent-k 5 \
  --entry-budget 12
```

### 3) Run continuation demo (full JSON)

```bash
python -m src.engine \
  --session-dir data/sessions/demo_session \
  --goal resolve_specific_conflict \
  --target-artifact-id artifact_main_v3 \
  --recent-k 5 \
  --entry-budget 12 \
  --json
```

## Demo dataset

See `docs/demo_continuation.md` and `data/sessions/demo_session/`.

## Config loading smoke test

```bash
python -m pytest -q
```

This includes config-level checks for:
- `config/agents.yaml` -> `src.agents.build_agent_from_config`
- `config/arenas.yaml` -> `src.arenas.load_arenas`

## Git branch sync check (local vs `origin/main`)

When validating whether your working branch matches GitHub `main`, run this sequence from a clone that has `origin` configured:

```bash
git fetch origin
git checkout main
git pull origin main
git checkout <your-branch>
git diff --name-status origin/main...HEAD
```

Optional commit-level comparison:

```bash
git log --oneline --left-right --cherry-pick origin/main...HEAD
```

