# Workflow

How a typical day flows through `worklog`. Read this if you want to know
*when* to use which command.

---

## The big picture

```
Morning                                           Evening
   │                                                 │
   ▼                                                 ▼
┌────────────────────┐                       ┌────────────────────┐
│ Plan: /worklog:add │  ── work happens ──▶  │ Review & push to   │
│   task entries     │  (calendar meetings,  │ ClickUp            │
│                    │   Claude sessions,    │  /worklog:show     │
│                    │   manual edits)       │  /worklog:push     │
└────────────────────┘                       └────────────────────┘
       │                                              │
       └──────────── one SQLite file ─────────────────┘
```

Three input streams feed the database:

| Stream            | Where it comes from                          | How                                  |
|-------------------|----------------------------------------------|--------------------------------------|
| **Tasks**         | You typing `/worklog:add <text>`             | Claude parses → `worklog add task`   |
| **Calendar time** | Google Calendar (optionally Read AI)         | `/worklog:sync-calendar`             |
| **CLI sessions**  | Each Claude Code session that lasts ≥ 2 min  | SessionEnd hook → `add_timesheet()`        |

One output stream:

| Stream         | Destination | How                |
|----------------|-------------|--------------------|
| ClickUp tasks  | ClickUp     | `/worklog:push`    |

---

## Command flow diagrams

### `/worklog:add "LeapBuilder: fix login redirect, PR#42, status done"`

```
 user prompt
     │
     ▼
 commands/add.md          ── extract fields ──▶  project, task, date,
 (Claude parses)                                  ref, status, remark
     │
     ▼
 bin/worklog add task --project … --task … --status done
     │
     ▼
 lib.db.add_task() ──▶ INSERT INTO tasks (…)
     │
     ▼
 echo "task #N added"
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
 markdown table (rendered in Claude Code)
```

### `/worklog:push today`

```
 commands/push.md
     │
     ▼
 bin/worklog list-pending today   ──▶  JSON: [{id, project, task, …}, …]
     │
     ▼  for each pending task
 ┌───────────────────────────────────────────────────────┐
 │  ClickUp MCP: clickup_search "<task title>"           │
 │     ├── match found  ─▶ clickup_update_task           │
 │     └── no match     ─▶ need a List                   │
 │                         ├── project has list mapping? │
 │                         │     yes → use it            │
 │                         │     no  → ask user, then    │
 │                         │           set-project-list  │
 │                         └── clickup_create_task       │
 └───────────────────────────────────────────────────────┘
     │
     ▼
 bin/worklog link-task <local_id> <clickup_id>
     │
     ▼
 summary table
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
 │     ├── found ─▶ extract actual start/end, attended?  │
 │     │              not attended → skip                │
 │     └── not found ─▶ use scheduled times              │
 └───────────────────────────────────────────────────────┘
     │
     ▼
 bin/worklog add time --since … --upto … --project Meetings …
     │
     ▼
 lib.db.add_timesheet() with source="read-ai" or "calendar"
   (dedupe on (date, since, task))
```

### SessionEnd hook (automatic)

```
 user exits Claude Code (Ctrl+D / window close / /clear / /logout)
     │
     ▼  JSON payload on stdin
 hooks/log_session.py
     │
     ├── parse transcript JSONL
     ├── skip if duration < 2 min
     ├── extract first user prompt as task title
     └── project = basename(cwd)
     │
     ▼
 lib.db.add_timesheet(source="claude-cli")
```

---

## A sample day

| Time   | Action                                                | Effect                                     |
|--------|-------------------------------------------------------|--------------------------------------------|
| 09:00  | `/worklog:sync-calendar today`                        | Today's accepted meetings appear in timesheet |
| 09:30  | Standup meeting happens (15 min)                      | Already in timesheet from sync             |
| 10:00  | `/worklog:add "LeapBuilder: implement OTP, status in_progress"` | Task added                       |
| 10:00  | Claude Code session begins on LeapBuilder repo        | (SessionEnd hook runs at end)                    |
| 11:45  | Claude session ends after 1h 45m                      | Auto-logged to timesheet                   |
| 13:00  | `/worklog:add "LeapBuilder: OTP done, PR#88"`         | Task updated/added; mark done              |
| 17:30  | `/worklog:show today`                                 | Review the day                             |
| 17:45  | `/worklog:push today`                                 | Tasks synced to ClickUp                    |

End of day: ClickUp is up to date; SQLite has the full history; nothing
was retyped twice.

---

## When to use which

| Use case                                  | Command                       |
|-------------------------------------------|-------------------------------|
| Quick capture of a TODO                   | `/worklog:add`                |
| Mark a task done                          | `/worklog:add` again with `status done` (Claude updates if matched) |
| See what you did                          | `/worklog:show today` / `yesterday` / `2026-05-24` |
| Sync the day's work to ClickUp            | `/worklog:push today`         |
| Auto-log meeting attendance               | `/worklog:sync-calendar`      |
| Set up a new project's ClickUp target     | first `/worklog:push` asks; or `bin/worklog set-project-list <p> <list_id>` |
| Verify everything's connected             | `/worklog:doctor`             |

---

## Gotchas

- **Push is one-way.** Status changes you make later in ClickUp aren't
  pulled back into SQLite. Re-edit locally and re-push if needed.
- **Read AI enrichment depends on Gmail.** If Gmail MCP is disconnected,
  `/worklog:sync-calendar` falls back to scheduled (not actual) times.
- **SessionEnd hook fires on Ctrl+D, window close, `/clear`, and `/logout`** —
  but not on `kill -9` or terminal crashes. Add any missed entry manually
  with `/worklog:add`.
- **Dedup is on `(date, since, task)`.** Re-running `sync-calendar` for the
  same day is safe; renaming a calendar event will create a second row.
