# tests

Smoke + integration tests for the `worklog` plugin.

## Run

From the repo root:

```bash
python3 -m pytest tests/ -q
```

If `pytest` isn't installed:

```bash
pip install --user --break-system-packages pytest
```

(Or use a venv.)

## What's covered

- `test_db.py` — schema/DAO round-trips (`tasks`, `timesheet`, `projects`),
  `find_project_by_path` (incl. longest-prefix), `auto_log` toggling,
  dedupe rules, and deletes.
- `test_hook.py` — invokes `hooks/log_session.py` as a real subprocess
  (the way Claude Code does), feeding fabricated transcripts and payloads.
  Covers: unregistered cwd skip, registered cwd logs, `auto_log=0` skip,
  and the 2-minute minimum.

## Isolation

`conftest.py` sets `WORKLOG_HOME` to a temp dir per test, so the user's
real `~/.worklog/worklog.db` is never touched.
