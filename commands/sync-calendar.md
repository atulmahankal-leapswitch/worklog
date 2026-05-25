---
description: Sync Google Calendar events into the worklog timesheet, enriched with Read AI actual attendance
argument-hint: "[today|yesterday|YYYY-MM-DD]"
---

Sync Google Calendar events for `$ARGUMENTS` (default `today`) into the
worklog timesheet, **enriched with actual attendance from Read AI recap
emails in Gmail** when available.

## Steps

### 1. List calendar events

Call `mcp__claude_ai_Google_Calendar__list_events` against the primary
calendar for the target date (`timeMin` = 00:00 local, `timeMax` = 23:59
local).

Keep only events where:
- `status == "confirmed"`
- user's `responseStatus` is `accepted` or `tentative` (skip `declined`)
- not all-day (has `start.dateTime`, not just `start.date`)

### 2. Enrich with Read AI recap (when Gmail MCP available)

For each event, search Gmail for the matching Read AI recap email:

- Query: `from:(read.ai OR noreply@read.ai OR reports@read.ai) subject:"<event title>" after:<date> before:<date+2>`
- If a recap is found, extract from the body:
  - Actual start time ("Started at HH:MM …")
  - Actual end time / duration
  - Whether the user's name appears in Participants — if NOT, **skip this
    event entirely** (you didn't attend).

Fall back to the calendar's scheduled times when no recap is found, and tag
the source accordingly.

### 3. Append to worklog

For each kept event run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog add time \
  --date <date> --project "Meetings" --task "<event title>" \
  --since <HH:MM> --upto <HH:MM> --ref "<recap-link or meet-link>" \
  --source <read-ai|calendar>
```

The CLI dedupes by `(date, since, task)`, so repeated runs are safe.

### 4. Summary

Print a table of events with source (read-ai vs calendar) and action
(appended vs skipped-not-attended vs skipped-duplicate), and a one-line
total.

## Notes

- Read-only against Calendar and Gmail. Only the worklog CLI writes.
- If the Gmail MCP is not connected, run with calendar-only times and tell
  the user — `/worklog:doctor` will say which MCPs are healthy.
