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
