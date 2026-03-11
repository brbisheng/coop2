# Continuation Demo (Task 4)

This demo provides a ready-to-run session directory for the continuation CLI.

## Demo data location

- `data/sessions/demo_session/snapshot.json`
- `data/sessions/demo_session/commits.jsonl`
- `data/sessions/demo_session/event_log.jsonl`
- `data/sessions/demo_session/dissent/d-001.json`

## Run

```bash
python -m src.engine \
  --session-dir data/sessions/demo_session \
  --goal resolve_specific_conflict \
  --target-artifact-id artifact_main_v3 \
  --recent-k 5 \
  --entry-budget 12
```

## Run with full JSON output

```bash
python -m src.engine \
  --session-dir data/sessions/demo_session \
  --goal resolve_specific_conflict \
  --target-artifact-id artifact_main_v3 \
  --recent-k 5 \
  --entry-budget 12 \
  --json
```

## Expected behavior

- `arena` should resolve to `mechanism` from snapshot.
- `target_lineage` should include `artifact_main_v1..v3`.
- unresolved dissent should include `d-001`.
