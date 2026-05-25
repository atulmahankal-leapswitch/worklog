# worklog

A Claude Code plugin to track your daily worklog — tasks, time entries, and
meetings — in a local SQLite database, with one-command push to ClickUp.

Designed for personal use: nothing is uploaded anywhere unless you explicitly
push it.

---

## What it gives you

| Command                          | What it does                                                   |
|----------------------------------|----------------------------------------------------------------|
| `/worklog:show [date]`           | Show tasks and time entries for a date                         |
| `/worklog:add <free-text>`       | Add a task, time entry, or **register a project** from a sentence |
| `/worklog:projects`              | List registered projects with path, existence, auto-log, last active |
| `/worklog:push [date]`           | Push that day's tasks to ClickUp (create new / update existing)|
| `/worklog:sync-calendar [date]`  | Pull Google Calendar events into the timesheet (Read AI aware) |
| `/worklog:doctor`                | Check that required integrations are healthy                   |

Plus an automatic **SessionEnd hook** that logs each Claude Code session
(≥ 2 min) as a single timesheet row tagged `claude-cli` when you exit
(Ctrl+D, close VS Code window, `/clear`, `/logout`).

**Auto-logging is opt-in per directory.** Only sessions whose working
directory falls under a registered project's `path` are logged. Register a
folder with:

```
/worklog:add register project "LeapBuilder" at /home/atul/Documents/LeapBuilder
```

…or pass `--no-auto-log` when registering to keep the project but skip
the auto-log (useful for sandbox/testing folders).

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

### 1. Clone the repo

Clone to **any location you like** — the plugin uses `${CLAUDE_PLUGIN_ROOT}`
so it works from wherever Claude Code registers it:

```bash
git clone https://github.com/atulmahankal-leapswitch/worklog.git
cd worklog
./install.sh
```

`install.sh` creates `~/.worklog/worklog.db` (override with `WORKLOG_HOME=…`)
and prints the next steps.

### 2. Enable as a Claude Code plugin

Inside Claude Code, point `/plugin install` at the directory you cloned:

```
/plugin install <path-to-cloned-repo>
```

This registers the slash commands (`/worklog:show`, `/worklog:add`,
`/worklog:push`, `/worklog:sync-calendar`, `/worklog:doctor`) and the Stop
hook.

### 3. Connect required integrations

Inside Claude Code, run:

```
/worklog:doctor
```

It tells you exactly what's connected and what's missing. For anything
missing, run `/mcp` and connect the service.

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

## Further reading

See [`docs/`](docs/README.md) for:

- Repository layout
- Architecture (internal design)
- Daily workflow walkthrough

---

## Uninstall

Inside Claude Code:

```
/plugin uninstall worklog
```

Then optionally remove the data and the cloned repo:

```bash
rm -rf ~/.worklog        # local database
rm -rf <repo-path>       # wherever you cloned it
```

---

## License

MIT. See `LICENSE` (add one before publishing if needed).
