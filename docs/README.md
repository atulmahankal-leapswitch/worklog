# worklog — docs

Index of documentation for the `worklog` Claude Code plugin.

| Document                              | What it covers                                                |
|---------------------------------------|---------------------------------------------------------------|
| [ARCHITECTURE.md](ARCHITECTURE.md)    | Internal design — storage, commands, hooks, integrations      |
| [WORKFLOW.md](WORKFLOW.md)            | End-to-end daily workflow and per-command data flow           |
| This file                             | Repository layout (below) + index of the docs                 |

For installation and basic usage see the top-level [README](../README.md).

---

## Repository layout

```
worklog/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest (name, version, SessionEnd hook)
├── commands/
│   ├── show.md                  # /worklog:show            — list day's work
│   ├── add.md                   # /worklog:add             — manual timesheet entry
│   ├── remove.md                # /worklog:remove          — delete by id
│   ├── project_add.md           # /worklog:project_add     — track cwd for auto-log
│   ├── project_remove.md        # /worklog:project_remove  — untrack cwd
│   ├── projects.md              # /worklog:projects        — list projects + status
│   ├── push.md                  # /worklog:push            — sync to ClickUp
│   ├── sync-calendar.md         # /worklog:sync-calendar   — pull Calendar/Read AI
│   └── doctor.md                # /worklog:doctor          — health check
├── hooks/
│   └── log_session.py           # SessionEnd hook → appends a timesheet row
├── lib/
│   ├── __init__.py
│   └── db.py                    # SQLite schema + DAO helpers
├── bin/
│   └── worklog                  # Single CLI used by all commands and the hook
├── docs/
│   ├── README.md                # ← you are here
│   ├── ARCHITECTURE.md          # Internal design
│   └── WORKFLOW.md              # Daily workflow walkthrough
├── tests/
│   ├── conftest.py              # Per-test isolated SQLite DB in tmp_path
│   ├── test_db.py               # DAO + schema round-trips
│   ├── test_hook.py             # SessionEnd hook subprocess integration
│   └── README.md                # How to run the suite
├── install.sh                   # Initialises ~/.worklog/worklog.db + setup hints
├── LICENSE                      # MIT
├── README.md                    # Quick start / install / usage
└── .gitignore                   # Excludes *.db (no personal data in git)
```

---

## Where data lives

| Location                      | Purpose                                              |
|-------------------------------|------------------------------------------------------|
| `~/.worklog/worklog.db`       | All tasks, time entries, projects (SQLite)           |
| `$WORKLOG_HOME/worklog.db`    | Override location (for multiple profiles)            |
| `${CLAUDE_PLUGIN_ROOT}/…`     | The plugin code, resolved by Claude Code at runtime  |

No personal data ever lives inside the repo — `.gitignore` excludes
`*.db`. The repo is safe to share publicly.
