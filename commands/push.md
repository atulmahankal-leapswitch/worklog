---
description: Push a day's timesheet entries to ClickUp — shows the worklog and asks for confirmation before creating anything
argument-hint: "[today|yesterday|YYYY-MM-DD]"
---

Push the worklog **timesheet** entries for `$ARGUMENTS` (default `today`)
to ClickUp. For each unpushed entry, create (or find) a task in the
project's mapped ClickUp List and add a time entry for the duration.

## Step 1 — Show the worklog first

Always render the day before touching ClickUp:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog show ${ARGUMENTS:-today}
```

Render it as-is. Rows marked `[new]` will be pushed; rows marked
`[cu:<id>]` are already in ClickUp and will be skipped.

## Step 2 — Confirm BEFORE pushing

Fetch the precise push set:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog list-timesheet-pending ${ARGUMENTS:-today}
```

Each element: `id`, `since`, `upto`, `duration`, `minutes`, `project`,
`task`, `clickup_list_id`, `clickup_list_name`.

If the array is empty → print "Nothing new to push." and stop.

Otherwise show a confirmation table and **ask the user to approve**:

```
| #  | Project → List          | Dur   | Task                                   |
|----|-------------------------|-------|----------------------------------------|
| 15 | hostbill_tds_mode → Hostbill | 00:28 | Always compute TDS on invoice subtotal |
```

Ask: "Push these N entries to ClickUp?" (Yes / pick which / No).
**Do not create anything in ClickUp until the user says yes.** If they
pick a subset, only push those ids.

For any row whose `clickup_list_id` is empty (project not mapped), tell
the user to map it first with `/worklog:project_add` and skip that row
(don't dump it into a random list).

## Step 3 — Push each approved entry

For each approved row:

1. **Find or create the task** in the project's List (`clickup_list_id`):
   - Search for an existing open task with the same title via
     `mcp__claude_ai_ClickUp__clickup_search`.
   - Exactly one match → reuse it. No match → create with
     `mcp__claude_ai_ClickUp__clickup_create_task`
     (`list_id` = `clickup_list_id`, `name` = the task text).
2. **Add the time entry** for the session duration:
   - `mcp__claude_ai_ClickUp__clickup_add_time_entry` on that task,
     with start = the entry's date + `since`, duration = `minutes`.
3. **Record it locally** so the row flips from `[new]` to `[cu:<id>]`:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog link-timesheet <id> <clickup_task_id>
   ```

## Step 4 — Summary + re-show

Print a table: `# | Project → List | Task | Action (created/reused) | ClickUp id`,
then a one-liner `N pushed (X created, Y reused, Z skipped)`. Finally
re-run step 1's `worklog show` so the user sees every pushed row now
marked `[cu:<id>]`.

## Notes

- Confirmation in step 2 is mandatory — this command never writes to
  ClickUp without an explicit yes.
- If the ClickUp MCP returns an auth error, stop and tell the user to run
  `/worklog:doctor` and reconnect ClickUp via `/mcp`.
- Never deletes ClickUp tasks. Re-running only pushes rows still marked
  `[new]`.
