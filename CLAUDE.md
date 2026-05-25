# CLAUDE.md — worklog plugin

Project-specific notes for Claude Code sessions started in this directory.
Also read `README.md` for the user-facing intro and `docs/ARCHITECTURE.md`
for the internal design.

---

## What this repo is

A **Claude Code plugin** that tracks the user's daily worklog (tasks, time
entries, meetings) in a local SQLite database and pushes tasks to ClickUp.

- Plugin manifest: `.claude-plugin/plugin.json`
- Marketplace manifest: `.claude-plugin/marketplace.json`
- Database: `~/.worklog/worklog.db` (override via `WORKLOG_HOME`)
- CLI: `bin/worklog` (single source of truth for all data ops)
- Slash commands: `commands/*.md` — auto-discovered by Claude Code
- SessionEnd hook: `hooks/log_session.py` (opt-in per project)

---

## Quick orientation

| Where           | What                                                  |
|-----------------|-------------------------------------------------------|
| `bin/worklog`   | Argparse CLI: `init`, `add`, `remove`, `show`, `projects`, `project register/untrack`, `link-task`, `list-pending`, `set-project-list` |
| `lib/db.py`     | SQLite schema + DAO. `init()` migrates idempotently.  |
| `hooks/log_session.py` | Reads SessionEnd JSON payload from stdin, writes a timesheet row if cwd matches a registered project with auto_log=1 |
| `commands/`     | Slash-command prompt templates                        |
| `tests/`        | pytest suite — run with `python3 -m pytest tests/ -q` |
| `docs/`         | ARCHITECTURE.md, WORKFLOW.md, README.md (docs index)  |

---

## Current state (as of last session)

- Plugin is **installed locally** in this user's Claude Code from this
  directory (`/plugin marketplace add ~/Documents/__Personal/worklog` then
  `/plugin install worklog`).
- After the installation step, the user still needs to **`/reload-plugins`
  or restart Claude Code** for the SessionEnd hook and slash commands to
  activate.
- `~/Documents/__Personal/worklog` is **not yet registered as a project**
  in the worklog DB. Running `/worklog:project_add` from this repo's root
  would enable auto-logging for plugin-development sessions (the user
  may NOT want this — registration is opt-in).
- The repo is published at https://github.com/atulmahankal-leapswitch/worklog.
- Local DB lives at `~/.worklog/worklog.db` (auto-created by `worklog init`
  or first `/worklog:doctor` call).
- `~/.local/bin/worklog` is a symlink to `bin/worklog`, so the CLI is on
  PATH globally.

## Recent commits

```
b52c1d2  Add marketplace.json so /plugin install works
b636ccf  Cleanup pass: LICENSE, tests, DRY parser, finished docs
47b23ce  Slash commands: hybrid interactive prompting
16abe4b  Rework /worklog commands per user spec
2fddb20  Add project registration for opt-in auto-logging
8b24838  Initial commit: worklog Claude Code plugin
```

---

## When the user asks for changes

1. Edit files in this repo — they take effect immediately because the
   plugin is installed via the local marketplace path. **No re-install
   needed.** Just `/reload-plugins` if the change is to plugin.json /
   marketplace.json / hook config.
2. Run tests before committing:
   ```bash
   python3 -m pytest tests/ -q
   ```
3. Smoke-test the CLI from this dir:
   ```bash
   ./bin/worklog show today
   ./bin/worklog projects
   ```
4. Commit. Per global rules: do **not** add Claude co-authorship or
   "Generated with Claude Code" footers.
5. The default workflow has been: regular `git push origin main`. Amend +
   `--force-with-lease` is allowed only when the user explicitly asks.

---

## Design conventions to preserve

- **Local-first** — nothing leaves the machine without an explicit
  `/worklog:push` or `/worklog:sync-calendar`.
- **Plugin code never holds secrets** — all third-party access is
  delegated to Claude Code's MCP connectors (ClickUp / Calendar / Gmail /
  Slack).
- **One CLI, one code path** — slash commands, the hook, and any
  terminal user all go through `bin/worklog` → `lib/db.py`. Don't add a
  second way to write to the DB.
- **Opt-in auto-logging** — only sessions whose cwd matches a registered
  project with `auto_log=1` are logged.
- **Schema migrations are idempotent** — extend `_migrate()` in
  `lib/db.py`; never DROP or rename columns.
- **DRY** — common argparse args live in `_add_entry_common()` in
  `bin/worklog`. Add to that helper rather than copy-pasting.
- **Tests cover the contract**, not the implementation. When you add a
  new public function, add a test in `tests/test_db.py`. New hook
  branches → `tests/test_hook.py`.

---

## Where to start a new feature

- New slash command → add `commands/<name>.md` (auto-discovered) +
  whatever CLI subcommand it needs in `bin/worklog`. Document it in
  README's command table and `docs/WORKFLOW.md`.
- New schema column → ALTER in `_migrate()`, add to `SCHEMA` for fresh
  DBs, update the relevant DAO functions, add a test.
- New MCP integration → mirror the `/worklog:sync-calendar` pattern: a
  read-only check in `/worklog:doctor` first, then a command markdown
  that orchestrates MCP calls and persists via `bin/worklog`.

---

## Things deliberately NOT done

- No external Python deps. SQLite + stdlib only.
- No second storage backend (Postgres, etc.).
- No multi-user / team mode. Single-user by design.
- No web UI. CLI + slash commands only.
- No automatic ClickUp pull-back. Push is one-way; resolve drift by
  re-editing locally and re-pushing.
