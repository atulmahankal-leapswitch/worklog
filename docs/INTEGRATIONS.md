# Planned integrations

Design notes for two integrations that are **not yet implemented**. This
doc captures the approach so a future contributor (or future-you) can pick
them up without re-deriving the design.

| Status legend |                                               |
|---------------|-----------------------------------------------|
| 🟢 done       | shipped and documented in README/WORKFLOW.md  |
| 🟡 planned    | designed here, not built                      |
| 🔴 blocked    | needs an external dependency before starting  |

| Feature                                  | Status   | Tracking |
|------------------------------------------|----------|----------|
| Calendar sync (scheduled times)          | 🟢 done | `commands/sync-calendar.md` |
| Read AI enrichment via Gmail recap email | 🟢 done | `commands/sync-calendar.md` |
| **Google Meet actual attendance**        | 🟡 planned | this doc |
| **Slack — pick up new tasks**            | 🟡 planned | this doc |
| **Slack — update task status**           | 🟡 planned | this doc |

---

## 1. Google Meet — actual attendance and duration

### Why

Calendar tells you what was *scheduled*. Meet tells you what *actually
happened*: who joined, when they joined, when they left, total duration.
This is the only reliable signal for "did I attend this meeting?" when
Read AI isn't in the call.

### Data sources (in order of preference)

| Source                                       | Pros                                 | Cons                                                                |
|----------------------------------------------|--------------------------------------|---------------------------------------------------------------------|
| Google Meet **attendance report** (CSV)      | Most accurate; per-participant times | Workspace admin must enable; lands as a CSV email after the meeting |
| Google Meet REST API (`v2.meet.googleapis`)  | Same data, programmatic              | Requires `meetings.space.readonly` OAuth scope; not in default MCP  |
| Calendar event `conferenceData` field        | Always present for Meet events       | Only the join URL — no attendance info                              |
| Read AI recap email (existing path)          | Already implemented                  | Only present when Read AI bot was in the meeting                    |

### Proposed flow (extending `/worklog:sync-calendar`)

```
list_events  ──▶  for each event:
                   1. Read AI recap (Gmail) → if found, use it (existing)
                   2. Else Meet attendance CSV (Gmail) → parse if found
                   3. Else calendar-scheduled times → mark as "scheduled"
                   ────▶ ask user via multi-select which to log
```

### Attendance CSV format (today's reality)

Workspace sends an email from `meet-recordings-noreply@google.com` with
subject `Attendance report - <Event title>`, attaching a CSV:

```
Name,Email,Duration,Time joined,Time exited
Atul Mahankal,atul.mahankal@leapswitch.com,42m,2026-05-25 11:01:14,2026-05-25 11:43:08
…
```

### Implementation sketch

1. Add a Gmail search step alongside the existing Read AI search:
   `from:meet-recordings-noreply@google.com subject:"Attendance report" after:<date> before:<date+2>`
2. Match the event by `<Event title>` in the subject.
3. Download the CSV attachment via the Gmail MCP, find the row matching
   the user's email, extract `Time joined` and `Time exited`.
4. Use those as `--since` / `--upto`, tag `--source meet`.

### Open questions / blockers

- Workspace **must** be configured to send attendance reports. This is an
  admin toggle, not something the plugin can enable.
- Gmail MCP currently exposes `authenticate`/`complete_authentication`
  only — attachment download may need an additional Gmail tool that the
  connector doesn't yet ship. Verify before building.
- If/when the Meet REST API becomes available as an MCP connector,
  prefer it over CSV scraping.

### Effort

Small — one new branch in `commands/sync-calendar.md`, plus a parser
function that's ~30 lines of Python. Behind a feature flag for users
without Workspace admin support.

---

## 2. Slack — pick up new tasks and update status

Two distinct flows. Build them as **two slash commands**, not one.

### 2a. `/worklog:slack-inbox` — pull new tasks from Slack

#### Why

Action items often arrive as Slack DMs (`"can you look at PR#42?"`),
@-mentions in channels, or saved-for-later messages. Today they get lost
between Slack and the worklog DB.

#### Where to look

| Source                          | How                                                                |
|---------------------------------|--------------------------------------------------------------------|
| **Saved-for-later** items       | Slack's per-user saved list; sync ones with no completion checkmark |
| **Recent mentions**             | Search for `to:<self> after:<yesterday>`                            |
| **Unread DMs**                  | List channels with `is_dm: true` and unread > 0                     |
| **Reactions** (e.g. `:eyes:`)   | Optional power-user shortcut: any message you react with `:todo:` becomes a task |

#### Proposed flow

```
/worklog:slack-inbox
  ├── 1. fetch candidates from all sources above (Slack MCP tools)
  ├── 2. dedupe by permalink — skip messages already linked to a task
  ├── 3. show as multi-select checklist (one per candidate)
  └── 4. for each ticked candidate:
         bin/worklog add task
           --project "<best-guess project>"
           --task "<message text, truncated>"
           --reference "<slack permalink>"
           --source slack
```

#### Best-guess project

Use a small heuristic before falling back to "Inbox":

1. Channel name → look up project mapping in a future
   `projects.slack_channel` column.
2. Mention of a known project name in the message.
3. Default: `Inbox`. The user can edit later.

#### MCP tools available today

- `slack_search_public` — search public messages
- `slack_search_public_and_private` — same, including DMs
- `slack_read_thread`, `slack_read_channel` — read context
- `slack_read_user_profile` — for sender identity
- *(missing)* — no public "list saved items" tool yet; fall back to
  search-based discovery.

### 2b. `/worklog:slack-update` — push status changes to Slack

#### Why

When a task is `done`, the requestor often wants to know. Manually
copy-pasting `"PR#42 merged"` into Slack is friction.

#### Proposed flow

```
/worklog:slack-update [task-id ...]
  ├── 1. for each task whose source=slack and status changed
  │     since last push:
  │      ├── extract the original Slack permalink from `reference`
  │      └── slack_send_message in that thread:
  │           "✅ Done — <task title> [worklog #<id>]"
  ├── 2. for tasks with status=blocked, send a "🛑 blocked"
  │     note with `remark` as the reason
  └── 3. record the Slack message_ts in a new
        tasks.slack_message_ts column to avoid double-notify
```

#### Open questions

- **Where to thread the reply**? If the task came from a DM, reply in
  the DM. If from a channel mention, reply in the thread of the original
  message. The Slack permalink encodes channel + ts so we can route
  correctly.
- **Channel selection** for status broadcasts (e.g. daily summary post)
  belongs to a separate `/worklog:slack-digest` command, not this one.

#### Schema change

```sql
ALTER TABLE tasks ADD COLUMN slack_message_ts TEXT;
ALTER TABLE tasks ADD COLUMN slack_last_notified TEXT;
```

Add to `_migrate()` in `lib/db.py`; bump no version number — additive
columns only.

### Effort

| Sub-feature              | Estimate | Notes                                |
|--------------------------|----------|--------------------------------------|
| `/worklog:slack-inbox`   | 1 day    | New slash command + minor schema use |
| `/worklog:slack-update`  | 1 day    | Schema migration + new slash command |
| Tests for both           | 0.5 day  | Mock Slack MCP responses             |

---

## How to pick this up

1. Read this doc and the existing `commands/sync-calendar.md` (the
   closest existing pattern).
2. Open a branch.
3. For each sub-feature: add the slash command, any CLI subcommand it
   needs in `bin/worklog`, schema migration if applicable, and tests.
4. Update `README.md` command table and `docs/WORKFLOW.md` flow diagrams.
5. Flip the status here from 🟡 planned to 🟢 done before shipping.
