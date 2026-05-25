---
description: Sync Google Calendar events into the worklog timesheet — asks which events you actually attended (enriched with Read AI when available)
argument-hint: "[today|yesterday|YYYY-MM-DD]"
---

Sync Google Calendar events for `$ARGUMENTS` (default `today`) into the
worklog timesheet. Calendar only knows what was *scheduled* — you confirm
which events you *attended* before anything is logged.

## Steps

### 1. List calendar events

Call `mcp__claude_ai_Google_Calendar__list_events` against the primary
calendar for the target date (`timeMin` = 00:00 local,
`timeMax` = 23:59 local).

Keep only events where:
- `status == "confirmed"`
- user's `responseStatus` is `accepted` or `tentative` (skip `declined`)
- not all-day (has `start.dateTime`, not just `start.date`)

For each kept event, also extract the **Google Meet link** if present:
- `event.hangoutLink`, or
- `event.conferenceData.entryPoints[].uri` where `entryPointType == "video"`.

This URL becomes the row's `--ref` so the timesheet entry links back to the
meeting. The Calendar MCP cannot tell us *actual* attendance — that needs
Read AI (step 2) or a Workspace admin attendance report (see
`docs/INTEGRATIONS.md`).

### 2. Enrich with Read AI recap (when Gmail MCP available)

For each event, search Gmail for the matching Read AI recap email:

- Query: `from:(read.ai OR noreply@read.ai OR reports@read.ai) subject:"<event title>" after:<date> before:<date+2>`
- If a recap is found, extract:
  - Actual start time ("Started at HH:MM …")
  - Actual end time / duration
  - Whether the user's name appears in Participants

Use Read AI's actual times when present. Pre-select attendance for events
where Read AI confirmed the user's presence; leave Read-AI-says-not-present
events unchecked. Where there's no recap, leave the box unchecked and tag
the times as `scheduled`.

### 3. Ask the user which events to log

Build a single multi-select question using `AskUserQuestion` with
`multiSelect: true`. One option per event, label format:

```
HH:MM-HH:MM  <Event title>  (calendar|read-ai)
```

The `description` field should clarify the source — e.g.
`"Scheduled time only — you did/didn't attend?"` or `"Read AI confirmed
attendance"`. Pre-tick boxes only when Read AI confirms attendance.

If the list would exceed `AskUserQuestion`'s 4-option limit, batch into
multiple questions (or fall back to a numbered list and ask the user to
reply with comma-separated numbers — e.g. `1, 3`).

If `$ARGUMENTS` includes the literal `--all`, **skip the confirmation
step** and append every kept event. Useful for unattended re-syncs.

### 4. Append only the selected events

For each event the user ticked, run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog add time \
  --date <date> --project "Meetings" --task "<event title>" \
  --since <HH:MM> --upto <HH:MM> --ref "<recap-link or meet-link>" \
  --source <read-ai|calendar>
```

The CLI dedupes by `(date, since, task)`, so repeated runs are safe.

### 5. Summary

Print a table of every event with:

| Column   | Values                                                        |
|----------|---------------------------------------------------------------|
| Event    | event title                                                   |
| Time     | start–end                                                     |
| Source   | `read-ai` / `calendar`                                        |
| Action   | `appended (#id)` / `skipped (not selected)` / `skipped (duplicate)` |

End with one-line totals: `N selected, A appended, S skipped, R via Read AI`.

Remind the user that `/worklog:remove <id>` deletes any row appended by
mistake.

## Notes

- Read-only against Calendar and Gmail. Only the worklog CLI writes.
- If the Gmail MCP is not connected, the command still runs but every row
  shows as `scheduled` — the user will be confirming purely from memory.
