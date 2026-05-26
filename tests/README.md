# tests

Smoke + integration tests for the `worklog` plugin.

## Run

From the repo root, using [`uv`](https://docs.astral.sh/uv/) (recommended
— creates an isolated venv automatically):

```bash
uv run --group dev pytest
```

If you don't have `uv` yet:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

`pytest` is declared as a [PEP 735](https://peps.python.org/pep-0735/)
dev-dependency group in the root `pyproject.toml`; the runtime itself
has zero external dependencies.

## What's covered

- `test_db.py` — schema/DAO round-trips (`tasks`, `timesheet`, `projects`),
  `find_project_by_path` (incl. longest-prefix), `auto_log` toggling,
  dedupe rules, deletes, and project upsert-by-path / delete-status logic.
- `test_hook.py` — invokes `hooks/log_session.py` as a real subprocess
  (the way Claude Code does), feeding fabricated transcripts and payloads.
  Covers: unregistered cwd skip, registered cwd logs, `auto_log=0` skip,
  and the 2-minute minimum.
- `test_transcripts.py` — chunk-by-idle-gap, longest-prefix path encoding,
  noise / resume-prompt filtering.

## Isolation

`conftest.py` sets `WORKLOG_HOME` to a temp dir per test, so the user's
real `~/.worklog/worklog.db` is never touched.
