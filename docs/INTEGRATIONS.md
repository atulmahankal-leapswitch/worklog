# Planned integrations

Design notes for two integrations that are **not yet implemented**. This
doc captures the approach so a future contributor (or future-you) can pick
them up without re-deriving the design.

| Status legend |                                               |
|---------------|-----------------------------------------------|
| 🟢 done       | shipped and documented in README/WORKFLOW.md  |
| 🟡 planned    | designed here, not built                      |
| 🔴 blocked    | needs an external dependency before starting  |

| Feature                                  | Status      | Tracking |
|------------------------------------------|-------------|----------|
| Calendar sync (scheduled times)          | 🟢 done    | `commands/sync-calendar.md` |
| Read AI enrichment via Gmail recap email | 🟢 done    | `commands/sync-calendar.md` |
| Meet link in timesheet `ref`             | 🟢 done    | `commands/sync-calendar.md` (conferenceData parse) |
| **Google Meet actual attendance**        | 🔴 blocked | needs Gmail MCP data tools or Meet REST API |
| **Slack — pick up new tasks**            | 🟢 done    | `commands/slack-inbox.md` |
| **Slack — update task status**           | 🟢 done    | `commands/slack-update.md` |
| Read AI MCP — direct meeting fetch       | 🟡 planned | Section 3 — replaces Gmail-recap path when MCP exposes data tools     |
| Google Calendar MCP — write-back         | 🟡 planned | Section 4 — push response/status changes back to events               |
| Google Meet MCP — attendance via MCP     | 🟡 planned | Section 5 — replaces CSV scraping when an official Meet MCP ships     |

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

## 3. Read AI MCP — direct meeting fetch (when ready)

### Why

Today the Read AI MCP only exposes `authenticate` / `complete_authentication`
— no data-read tools. So `/worklog:sync-calendar` falls back to **scraping
the Read AI recap email out of Gmail**: fragile, slow, and dependent on
the recap actually arriving.

When Read AI's MCP exposes data tools (expected names below — adjust to
real ones at integration time) we can replace the Gmail scrape with a
direct call.

### Expected MCP tools we'll need

| Tool                                          | Used for                                          |
|-----------------------------------------------|---------------------------------------------------|
| `mcp__claude_ai_Read_AI__list_meetings`       | Discover meetings the user attended on a date     |
| `mcp__claude_ai_Read_AI__get_meeting`         | Fetch a single meeting's start/end/participants   |
| `mcp__claude_ai_Read_AI__list_participants`   | (Or embedded in `get_meeting`) confirm attendance |

### Migration plan when ready

1. **Detect availability** — in `/worklog:doctor`, add a check: call
   `list_meetings` with `limit: 1` and a date range; if it succeeds,
   mark Read AI MCP as PASS for *data* (not just auth).
2. **Branch the sync** — `/worklog:sync-calendar` already has a "Read AI
   enrichment" step. Replace its Gmail search with:
   ```
   list_meetings(after=date, before=date+1)
       └── match by event title / start time
       └── get_meeting(id) → start, end, participants
   ```
3. **Keep the Gmail fallback** — if Read AI MCP fails (offline, scope
   missing), fall through to the existing Gmail-recap parser. Never
   regress users who only have email recaps.
4. **Test fixture** — add a mock Read AI MCP response in
   `tests/test_sync_calendar.py` (new file) covering: attended, not
   attended, missing meeting.

### Effort

~0.5 day once the MCP tool names are known. Mostly mechanical — replaces
one helper function in the sync-calendar prompt.

---

## 4. Google Calendar MCP — write-back

### Why

Today we only **read** from Calendar. Two write paths would be useful:

| Use case                                      | Outbound action                                                                     |
|-----------------------------------------------|-------------------------------------------------------------------------------------|
| User confirms attendance in `/worklog:sync-calendar` | Update the event's `attendees[me].responseStatus = "accepted"` if it was `tentative` |
| User declines in the picker                   | Set `responseStatus = "declined"` so the organiser sees the cancellation             |
| Worklog task with `status=done`               | (Optional) Mark the source meeting as ✅ in its description                         |
| Worklog task scheduled to a future slot       | (Optional) Create a calendar event for blocked focus time                            |

### Expected MCP tools

The Google Calendar MCP already exposes write tools (we just don't use
them yet):

- `mcp__claude_ai_Google_Calendar__update_event` — patch a field
- `mcp__claude_ai_Google_Calendar__respond_to_event` — set RSVP status
- `mcp__claude_ai_Google_Calendar__create_event`

### Migration plan when ready

1. Add a `--write-back` flag to `/worklog:sync-calendar`. Default off.
2. When the user finishes the multi-select picker:
   - For ticked events whose current `responseStatus` was `tentative`,
     call `respond_to_event(eventId, "accepted")`.
   - For unticked events, optionally call `respond_to_event(eventId,
     "declined")` (behind an additional confirm prompt — destructive).
3. New slash command `/worklog:calendar-block` for the "create blocked
   focus slot from a task" flow. Out of scope for the first iteration.

### Schema

No DB changes. Calendar event ids are deterministic per event so we don't
need to store them.

### Effort

~0.5 day for response status write-back. Focus-block creation is ~1 more
day if/when needed.

---

## 5. Google Meet MCP — attendance via MCP (when ready)

### Why

Today there is **no Google Meet MCP**. Attendance can only be obtained by
parsing the Workspace admin attendance-report CSV from Gmail — which
itself is blocked because the Gmail MCP doesn't expose
attachment-download tools (see section 1).

If Anthropic ships a Google Meet MCP (or Google's official one) it would
unblock end-to-end actual-attendance tracking.

### Expected MCP tools

Guessing the shape based on Meet's REST API
(`v2.meet.googleapis.com/conferenceRecords/*`):

| Tool                                                | Used for                                          |
|-----------------------------------------------------|---------------------------------------------------|
| `mcp__claude_ai_Google_Meet__list_conference_records` | Find meetings the user attended on a date         |
| `mcp__claude_ai_Google_Meet__list_participants`     | Per-participant join/leave times                  |
| `mcp__claude_ai_Google_Meet__get_recording`         | (Optional) recording URL for the row's `ref`      |

### Migration plan when ready

1. Add a `mcp__claude_ai_Google_Meet__list_conference_records` probe to
   `/worklog:doctor`.
2. Insert as **step 2.5** in `/worklog:sync-calendar`, between Read AI
   enrichment and the multi-select picker:
   - For each accepted calendar event with a Meet link, look up the
     matching conference record (match by `meetCode` extracted from the
     hangout URL).
   - Pull the user's join + leave time; pre-tick the option only if the
     user actually attended.
   - Use the join/leave window as `--since` / `--upto` (overriding
     scheduled times).
3. Order of precedence for actual attendance, highest to lowest:
   - Google Meet MCP (most authoritative)
   - Read AI MCP (when section 3 lands)
   - Read AI recap email via Gmail (current path)
   - Calendar scheduled times (fallback, user confirms via picker)

### Schema

No DB changes — `--source meet` tag is enough.

### Effort

~1 day once the MCP is available. Wraps existing sync-calendar logic.

---

## How to pick this up

1. Read this doc and the existing `commands/sync-calendar.md` (the
   closest existing pattern).
2. Open a branch.
3. For each sub-feature: add the slash command, any CLI subcommand it
   needs in `bin/worklog`, schema migration if applicable, and tests.
4. Update `README.md` command table and `docs/WORKFLOW.md` flow diagrams.
5. Flip the status here from 🟡 planned to 🟢 done before shipping.
