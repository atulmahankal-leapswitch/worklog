# worklog

A Claude Code plugin to track your daily worklog — tasks, time entries, and
meetings — in a local SQLite database, with one-command push to ClickUp.

Designed for personal use: nothing is uploaded anywhere unless you explicitly
push it.

---

## What it gives you

| Command                          | What it does                                                   |
|----------------------------------|----------------------------------------------------------------|
| `/worklog:show [date]`                                   | Show tasks and time entries for a date                                 |
| `/worklog:add <project>\|<task>\|<HH:MM>-<HH:MM>[\|date]` | Add a manual timesheet entry                                           |
| `/worklog:remove #<id>`                                  | Remove a timesheet entry (or `task #<id>` for the tasks table)         |
| `/worklog:project_add [name]`                            | Register the current directory as a project for auto-logging           |
| `/worklog:project_remove`                                | Turn off auto-logging for the current directory (keeps history)        |
| `/worklog:projects`                                      | List registered projects — path, exists, auto-log, last active         |
| `/worklog:backfill [date]`                               | Scan transcripts and insert missing rows for that date (use after a session that never cleanly exited) |
| `/worklog:push [date]`                                   | Push that day's tasks to ClickUp (create new / update existing)        |
| `/worklog:sync-calendar [date]`                          | Pull Google Calendar events into the timesheet (Read AI aware, asks before append) |
| `/worklog:doctor`                                        | Check that required integrations are healthy                           |

> **Slack integration is paused.** First-pass `/worklog:slack-inbox` and
> `/worklog:slack-update` are kept in `commands.disabled/` until the
> filtering and project-guess heuristics are reworked — see
> [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md) for the known issues.

Plus an automatic **SessionEnd hook** that logs each Claude Code session
(≥ 2 min) as a single timesheet row tagged `claude-cli` when you exit
(Ctrl+D, close VS Code window, `/clear`, `/logout`).

**Auto-logging is opt-in per directory.** Only sessions whose working
directory falls under a registered project's `path` are logged. To
enable it for a folder:

```
cd /path/to/your/project
/worklog:project_add               # uses cwd; project name defaults to folder name
/worklog:project_add LeapBuilder   # override the name
```

To stop auto-logging (e.g. for testing/sandbox folders) without losing
history:

```
/worklog:project_remove
```

Run `/worklog:projects` to see the current status.

`date` accepts `today`, `yesterday`, or `YYYY-MM-DD`.

---

## Requirements

| Component        | Required | Used for                                  |
|------------------|----------|-------------------------------------------|
| Python 3.9+      | yes      | All CLI operations                        |
| Claude Code      | yes      | Slash commands and the SessionEnd hook          |
| ClickUp MCP      | yes      | `/worklog:push`                           |
| Google Calendar MCP | no    | `/worklog:sync-calendar`                  |
| Gmail MCP        | no       | Enrich calendar sync with Read AI recaps  |
| Slack MCP        | no       | Future task notifications                 |

SQLite ships with the Python stdlib — no extra install.

---

## Install

### 1. Install the plugin

Inside Claude Code:

```
/plugin marketplace add atulmahankal-leapswitch/worklog
/plugin install worklog
```

Then **restart Claude Code (or open a new session)** so the SessionEnd
hook and slash commands load.

This registers `/worklog:show`, `/worklog:add`, `/worklog:remove`,
`/worklog:project_add`, `/worklog:project_remove`, `/worklog:projects`,
`/worklog:push`, `/worklog:sync-calendar`, `/worklog:doctor` and the
SessionEnd hook.

### 2. Initialise & check

Inside Claude Code:

```
/worklog:doctor
```

This creates `~/.worklog/worklog.db` on first call and reports which
integrations are connected. For any FAIL row, run `/mcp` and connect that
service.

Override the DB location with the `WORKLOG_HOME` env var if you want it
somewhere else.

---

## Usage

### Show today's worklog

```
/worklog:show
/worklog:show yesterday
/worklog:show 2026-05-24
```

Output shows tasks (with status checkboxes) and time entries with totals.

### Add a task or time entry

Describe the entry in natural language — Claude parses it:

```
/worklog:add LeapBuilder: fix login redirect, PR#42, status done
/worklog:add 14:00-15:30 LeapBuilder: design review
/worklog:add Hostbill module: investigate kyc failure (in_progress)
```

You can pass `today` / `yesterday` / a date in the text; default is today.

### Push to ClickUp

```
/worklog:push today
```

For each unpushed task:
- Searches ClickUp for an existing open task with the same title → updates
  status/description if found.
- Otherwise creates a new task. **For the first task in a project**, you'll
  be asked which Space → Folder → List to create it under. The plugin
  remembers your choice per project for next time.

Already-pushed tasks (which have a stored ClickUp id) are skipped.

### Sync calendar meetings

```
/worklog:sync-calendar today
```

Pulls today's accepted events from Google Calendar. If Gmail is connected
and Read AI sent a recap for the meeting, the **actual** start/end/duration
is used and meetings you didn't attend are skipped. Otherwise the
**scheduled** times are used.

### Automatic Claude Code session logging

You don't need to do anything. Every Claude Code session that lasts ≥ 2
minutes is appended to the timesheet when it ends, tagged `claude-cli`. The
project is taken from the working directory and the task is the first
prompt of the session.

---

## Data & privacy

- The database lives at `~/.worklog/worklog.db` (override with
  `WORKLOG_HOME=/path` env var).
- It is **never** committed — see `.gitignore`.
- Nothing is sent anywhere except when you explicitly run `/worklog:push`
  or `/worklog:sync-calendar`.

### Schema

```
projects   id, name, coordinator, git_repo, clickup_list_id
tasks      id, date, project_id, task, reference, assigned,
           status, status_date, remark, source, clickup_task_id
timesheet  id, date, since, upto, minutes, project_id, task, ref, source
```

`source` values: `manual`, `calendar`, `read-ai`, `claude-cli`.

---

## CLI usage (without Claude Code)

The slash commands are thin wrappers around `bin/worklog`. You can use the
CLI directly from inside the cloned repo:

```bash
./bin/worklog init
./bin/worklog add task --project "LeapBuilder" --task "fix login" --status done
./bin/worklog add time --project "LeapBuilder" --task "design review" \
                      --since 14:00 --upto 15:30
./bin/worklog show today
./bin/worklog show 2026-05-24 --format json
```

Tip — symlink or alias it for convenience:

```bash
ln -s "$(pwd)/bin/worklog" ~/.local/bin/worklog
# then anywhere:
worklog show today
```

Run `bin/worklog -h` for the full reference.

---

## Uninstall

Inside Claude Code:

```
/plugin uninstall worklog
/plugin marketplace remove worklog
```

Then optionally remove the local database:

```bash
rm -rf ~/.worklog
```

---

## Further reading

See [`docs/`](docs/README.md) for:

- Repository layout
- Architecture (internal design)
- Daily workflow walkthrough
- Planned integrations (Google Meet, Slack)

---

## Development

Runtime is **stdlib-only** — no `pip install` is needed to *use* the
plugin. The only external dependency anywhere in the project is
`pytest`, and it's declared as a [PEP 735](https://peps.python.org/pep-0735/)
dev-only group in `pyproject.toml`.

Run the test suite with [`uv`](https://docs.astral.sh/uv/) (creates an
isolated venv, doesn't touch your system Python):

```bash
# one-time, if you don't have uv installed:
curl -LsSf https://astral.sh/uv/install.sh | sh

# run the tests
uv run --group dev pytest
```

Plain `pytest` also works if you already have it on your PATH.

Tests use a temp directory for `WORKLOG_HOME`, so your real
`~/.worklog/` database is untouched.

The `uv.lock` is committed so test runs are reproducible. Re-resolve
after editing `pyproject.toml`:

```bash
uv lock
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for internal design.

---

## License

MIT — see [LICENSE](LICENSE).
