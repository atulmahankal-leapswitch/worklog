# Workflow

How a typical day flows through `worklog`. Read this if you want to know
*when* to use which command.

---

## The big picture

```
Morning                                              Evening
   │                                                    │
   ▼                                                    ▼
┌────────────────────┐                          ┌────────────────────┐
│ /worklog:add quick │  ─── work happens ───▶   │ Review & push      │
│  manual entries    │  (meetings, sessions,     │  /worklog:show     │
│                    │   manual edits)           │  /worklog:push     │
└────────────────────┘                          └────────────────────┘
       │                                                  │
       └──────────────── one SQLite file ─────────────────┘
```

Three input streams feed the database:

| Stream             | Where it comes from                              | How                                                      |
|--------------------|--------------------------------------------------|----------------------------------------------------------|
| **Manual entries** | You typing `/worklog:add`                        | Pipe form or interactive prompts → `worklog add time`    |
| **Calendar time**  | Google Calendar (optionally enriched by Read AI) | `/worklog:sync-calendar`                                 |
| **CLI sessions**   | Each Claude Code session ≥ 2 min in a registered project | SessionEnd hook → `db.add_timesheet(source="claude-cli")` |

One output stream:

| Stream         | Destination | How                |
|----------------|-------------|--------------------|
| ClickUp tasks  | ClickUp     | `/worklog:push`    |

---

## Command flow diagrams

### `/worklog:add LeapBuilder | fix login redirect | 10:00-11:30`

```
 user prompt
     │
     ▼
 commands/add.md
   ├── if any field missing → ask the user one by one
   └── split on '|' → project, task, time range, optional date
     │
     ▼
 bin/worklog add time --project … --task … --since 10:00 --upto 11:30
     │
     ▼
 lib.db.add_timesheet() ──▶ INSERT INTO timesheet
     │
     ▼
 echo "timesheet #N added (01:30)"
```

### `/worklog:remove 5`

```
 commands/remove.md
   ├── empty $ARGUMENTS → run `worklog show today`, ask which id
   ├── starts with 'task' → remove from tasks
   └── otherwise → remove from timesheet
     │
     ▼
 bin/worklog remove time 5
     │
     ▼
 lib.db.delete_timesheet(5)
     │
     ▼
 echo "timesheet #5 removed"  (or "not found")
```

### `/worklog:project_add`

```
 commands/project_add.md
   ├── name = $ARGUMENTS  or  basename(cwd)  (user can override)
   └── confirm with the user
     │
     ▼
 bin/worklog project register --path "$(pwd)" --name <chosen>
     │
     ▼
 lib.db.add_project(path=…, auto_log=True)
```

### `/worklog:project_remove`

```
 commands/project_remove.md
     │
     ▼
 bin/worklog project untrack --path "$(pwd)"
     │
     ▼
 lib.db.set_project_auto_log_by_path(cwd, enabled=False)
   (row preserved — only auto_log flips off)
```

### `/worklog:projects`

```
 bin/worklog projects
     │
     ▼
 lib.db.list_projects_with_status() with LEFT JOIN to MAX(date)
     │
     ▼
 markdown table — name, path, path-exists, auto-log, last active
```

### `/worklog:show today`

```
 commands/show.md
     │
     ▼
 bin/worklog show today
     │
     ▼
 lib.db.list_tasks(today) + list_timesheet(today)
     │
     ▼
 markdown sections — tasks, timesheet, totals
```

### `/worklog:push today`

```
 commands/push.md
     │
     ▼
 bin/worklog list-pending today  ──▶  JSON pending tasks
     │
     ▼  for each pending task
 ┌───────────────────────────────────────────────────────┐
 │  ClickUp MCP: clickup_search "<task title>"           │
 │    ├── match found  ─▶ clickup_update_task            │
 │    └── no match     ─▶ create_task                    │
 │                         ├── project has list mapping? │
 │                         │     yes → use it            │
 │                         │     no  → ask user, then    │
 │                         │           set-project-list  │
 └───────────────────────────────────────────────────────┘
     │
     ▼
 bin/worklog link-task <local_id> <clickup_id>
```

### `/worklog:sync-calendar today`

```
 commands/sync-calendar.md
     │
     ▼
 Google Calendar MCP: list_events(today)
     │
     ▼  for each accepted, non-all-day event
 ┌───────────────────────────────────────────────────────┐
 │  Gmail MCP: search Read AI recap for this meeting     │
 │    ├── found ─▶ extract actual start/end, attended?   │
 │    │              not attended → skip                 │
 │    └── not found ─▶ use scheduled times               │
 └───────────────────────────────────────────────────────┘
     │
     ▼
 bin/worklog add time --since … --upto … --project Meetings …
   (dedup on date+since+task — safe to re-run)
```

### SessionEnd hook (automatic, opt-in)

```
 user exits Claude Code (Ctrl+D / window close / /clear / /logout)
     │
     ▼  JSON payload on stdin
 hooks/log_session.py
   ├── parse transcript JSONL for first/last timestamps
   ├── skip if duration < 2 min
   ├── lookup db.find_project_by_path(cwd)
   │     └── no match OR auto_log=0 → exit silently
   └── task title = first user prompt of the session
     │
     ▼
 lib.db.add_timesheet(source="claude-cli", ref="claude-cli:<reason>")
```

---

## A sample day

| Time   | Action                                                      | Effect                                       |
|--------|-------------------------------------------------------------|----------------------------------------------|
| 08:55  | `cd ~/Documents/LeapBuilder && /worklog:project_add`        | Enables auto-log for this folder             |
| 09:00  | `/worklog:sync-calendar today`                              | Meetings appear in timesheet                 |
| 09:30  | Standup happens (15 min)                                    | Already logged from sync                     |
| 10:00  | Claude Code session begins in LeapBuilder                   | (SessionEnd hook will run later)             |
| 11:45  | Claude session ends after 1h 45m                            | Auto-logged to timesheet                     |
| 13:00  | `/worklog:add LeapBuilder \| OTP done, PR#88 \| 12:30-13:00` | Manual timesheet row                         |
| 17:30  | `/worklog:show today`                                       | Review the day                               |
| 17:35  | `/worklog:remove 7`                                         | Drop a row that was logged by mistake        |
| 17:45  | `/worklog:push today`                                       | Tasks synced to ClickUp                      |

End of day: ClickUp is current; SQLite has the full history; nothing was
retyped twice.

---

## When to use which

| Use case                                       | Command                                       |
|------------------------------------------------|-----------------------------------------------|
| Log time you just worked                       | `/worklog:add` (pipe or interactive)          |
| Drop an entry you didn't actually do           | `/worklog:remove <id>`                        |
| Turn on auto-log for the current folder        | `/worklog:project_add`                        |
| Stop auto-log for the current folder           | `/worklog:project_remove`                     |
| See registered projects and their last activity| `/worklog:projects`                           |
| See today's worklog                            | `/worklog:show today`                         |
| Sync attended meetings                         | `/worklog:sync-calendar`                      |
| Push to ClickUp                                | `/worklog:push today`                         |
| Health-check integrations                      | `/worklog:doctor`                             |

---

## Gotchas

- **Auto-log is opt-in per folder.** Sessions in folders that aren't
  registered (or have `auto_log=0`) are silently skipped. Use
  `/worklog:projects` to audit.
- **Push is one-way.** Status changes you make later in ClickUp aren't
  pulled back into SQLite. Re-edit locally and re-push if needed.
- **Read AI enrichment depends on Gmail.** If Gmail MCP is disconnected,
  `/worklog:sync-calendar` falls back to scheduled (not actual) times.
- **SessionEnd hook fires on Ctrl+D, window close, `/clear`, and
  `/logout`** — but not on `kill -9` or terminal crashes. Add any missed
  entry manually with `/worklog:add`.
- **Dedup is on `(date, since, task)`.** Re-running `sync-calendar` for
  the same day is safe; renaming a calendar event will create a second
  row.
