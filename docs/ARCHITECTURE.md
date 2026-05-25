# Architecture

How the `worklog` plugin is wired internally. Read this if you want to
modify the plugin, add a command, or understand why a piece exists.

---

## Design goals

1. **Local-first** — all data lives in a single SQLite file on the user's
   machine. Nothing leaves unless an explicit `push`/`sync` command is run.
2. **Location-agnostic** — the plugin works no matter where the repo is
   cloned. Paths resolve via `${CLAUDE_PLUGIN_ROOT}` (injected by Claude
   Code) and `WORKLOG_HOME` (defaults to `~/.worklog`).
3. **Thin slash commands** — each `/worklog:*` is a small markdown prompt
   that delegates to one CLI binary or one MCP tool. The CLI is the single
   source of truth for data operations.
4. **No external runtime deps** — Python 3.9+ stdlib only. SQLite ships
   with Python. ClickUp/Calendar/Gmail/Slack access is **borrowed** from
   Claude Code's MCP connectors — the plugin never holds those secrets.

---

## Component overview

```
                    ┌──────────────────────────────┐
                    │       Claude Code CLI        │
                    │  (user runs /worklog:show…)  │
                    └────────────────┬─────────────┘
                                     │
                ┌────────────────────┼────────────────────┐
                ▼                    ▼                    ▼
      ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
      │   commands/*.md  │  │  hooks/log_…py   │  │   MCP servers    │
      │ (slash commands) │  │ (SessionEnd hook │  │ ClickUp, GCal,   │
      └────────┬─────────┘  │  auto-logs work) │  │ Gmail, Slack     │
               │            └────────┬─────────┘  └────────┬─────────┘
               │  shells out          │ writes via                │
               ▼  via Bash            ▼ lib.db                    │
      ┌──────────────────┐  ┌──────────────────┐                  │
      │    bin/worklog   │─▶│      lib/db      │                  │
      │  argparse + ops  │  │  schema + DAO    │                  │
      └────────┬─────────┘  └────────┬─────────┘                  │
               │                     │                            │
               └─────────┬───────────┘                            │
                         ▼                                        │
                ┌──────────────────┐                              │
                │  ~/.worklog/     │                              │
                │   worklog.db     │◀─── ClickUp ids stored ──────┘
                │   (SQLite)       │
                └──────────────────┘
```

---

## Layers

### 1. Slash commands (`commands/*.md`)

Each markdown file is a prompt template. Claude reads it when the user
invokes `/worklog:<name>`, replaces `$ARGUMENTS`, and executes the steps
described. The patterns are:

- **CLI-backed commands** (`show`, `add`): shell out to
  `python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog …` and render output.
- **MCP-backed commands** (`push`, `sync-calendar`, `doctor`): orchestrate
  ClickUp / Calendar / Gmail / Slack MCP tool calls, persisting results via
  the same CLI.

Keeping data ops in the CLI means the same code path is used by Claude
Code commands, the SessionEnd hook, and any user running `bin/worklog` from a
terminal.

### 2. CLI (`bin/worklog`)

Argparse with subcommands:

| Subcommand          | Purpose                                            |
|---------------------|----------------------------------------------------|
| `init`              | Create the DB schema (idempotent)                  |
| `add task|time`     | Insert a task or timesheet row                     |
| `show [date]`       | Render markdown or JSON for a date                 |
| `list-pending [d]`  | Print tasks lacking a ClickUp id (JSON, for /push) |
| `link-task`         | Record a ClickUp id against a local task          |
| `set-project-list`  | Map a project → default ClickUp list id           |

The CLI uses absolute imports of `lib/` via a `sys.path.insert(0, ROOT)`
trick at the top, so it runs whether invoked as `bin/worklog` or
`python3 bin/worklog`.

### 3. Data layer (`lib/db.py`)

Plain `sqlite3`. Three tables:

```
projects   id, name UNIQUE, coordinator, git_repo, clickup_list_id, created_at
tasks      id, date, project_id FK→projects, task, reference,
           assigned, status, status_date, remark, source,
           clickup_task_id, created_at, updated_at
timesheet  id, date, since, upto, minutes, project_id FK→projects,
           task, ref, source, created_at
```

`source` is a free-text tag — values used today: `manual`, `calendar`,
`read-ai`, `claude-cli`.

DAO functions wrap connections in a `connect()` context manager, enabling
WAL-friendly short transactions. Foreign keys are on. There is no
migration system yet — `init()` is idempotent for the current schema.

**Why no `users` table?** Single-user tool by design.

### 4. SessionEnd hook (`hooks/log_session.py`)

Claude Code fires SessionEnd hooks with a JSON payload on stdin:
`{session_id, transcript_path, cwd, …}`. The hook:

1. Parses the transcript JSONL for the first/last timestamps.
2. Skips if duration < 2 minutes (avoid accidental entries).
3. Extracts the first user prompt as the task title.
4. Calls `lib.db.add_timesheet(...)` with `source="claude-cli"`.

It exits 0 even on failure so Claude Code is never blocked.

### 5. Plugin manifest (`.claude-plugin/plugin.json`)

Declares plugin name (`worklog`), version, and registers the SessionEnd hook
using `${CLAUDE_PLUGIN_ROOT}` for portability. Commands are auto-discovered
from `commands/`.

---

## Why these choices

| Decision                       | Why                                                              |
|--------------------------------|------------------------------------------------------------------|
| SQLite over xlsx               | Concurrent safe, queryable, no external libs                     |
| MCP for ClickUp/Calendar/etc.  | Leverage existing Claude Code auth; no secrets stored in plugin  |
| Markdown command files         | Native plugin format; commands are themselves prompt templates   |
| Single CLI binary              | One code path for all data ops (Claude, hook, terminal user)     |
| `~/.worklog/` not repo dir     | Data survives `git clean -fdx`; lets repo be reinstalled cleanly |
| `WORKLOG_HOME` env override    | Multiple databases (e.g. `personal` vs `work`) on one machine    |

---

## Extending

Add a new command:

1. Drop `commands/<name>.md` with frontmatter `description:` + `argument-hint:`.
2. Either shell out to `bin/worklog` (add a subcommand if needed) or call
   MCP tools directly from the prompt.

Add a new field to a table:

1. Edit `SCHEMA` in `lib/db.py`.
2. Add an `ALTER TABLE … ADD COLUMN` line conditional on its absence, or
   bump a tracked `schema_version` row — there's no migration runner yet,
   so keep changes additive and backward-compatible for now.

Add a new integration:

1. Confirm it's available as a Claude Code MCP connector (check
   `/worklog:doctor` for the existing pattern).
2. Add a `commands/*.md` that calls its MCP tools and persists via the
   CLI.
