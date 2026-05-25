---
description: Remove worklog entries — shows today's rows as a checkbox picker when no id is given
argument-hint: "(empty for checkbox picker)  OR  #<id>  OR  task #<id>"
---

Remove worklog entries.

## Behaviour

| Input               | What happens                                                                |
|---------------------|-----------------------------------------------------------------------------|
| Empty `$ARGUMENTS`  | Show today's entries as a multi-select checklist; delete the ticked rows    |
| `#N` or `N`         | Remove timesheet entry `N` directly                                         |
| `task #N` or `task N` | Remove task entry `N` directly                                            |

## Steps

### When `$ARGUMENTS` is empty — interactive picker

1. Fetch today's entries as JSON so you have ids and labels:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog show today --format json
   ```

   The JSON has `tasks: [{id, project, task, status, …}]` and
   `timesheet: [{id, since, upto, duration, project, task, source}]`.

2. Build **one or more** `AskUserQuestion` calls with `multiSelect: true`.

   Each option corresponds to one row. Label format:

   - Timesheet row: `TS #<id>  HH:MM-HH:MM  (DUR)  <project>: <task>`
   - Task row: `TASK #<id>  [<status>]  <project>: <task>`

   `AskUserQuestion` allows max 4 options per question. If the day has
   more than 4 rows, split across multiple questions (e.g.
   "Rows 1-4 of 7", "Rows 5-7 of 7"). Keep ordering: timesheet rows
   first (sorted by `since`), then tasks.

   Carry each option's *kind* (`time` vs `task`) and *id* with you so
   you can invoke the right CLI subcommand for each selected option.

3. Run the CLI delete per ticked option:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog remove time <id>   # for TS rows
   python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog remove task <id>   # for TASK rows
   ```

   If the user ticked nothing, print "Nothing removed." and stop.

4. Print a summary table:

   ```
   | Kind      | Id  | Description                          | Result    |
   |-----------|-----|--------------------------------------|-----------|
   | timesheet | #2  | Meetings: HCLTech <> CloudPe (15:00) | removed   |
   | timesheet | #3  | Meetings: Daily meet (18:30)         | removed   |
   ```

   …followed by a one-line total: `N removed.`.

### When `$ARGUMENTS` is provided — direct delete

- Starts with `task` → `worklog remove task <id>`.
- Otherwise (bare number with optional `#`) → `worklog remove time <id>`.

Echo the CLI's confirmation line. If "not found", suggest
`/worklog:show <date>` to look up the correct id.

## Examples

```
/worklog:remove              # picker for today
/worklog:remove 5            # delete timesheet #5
/worklog:remove #5           # same
/worklog:remove task #3      # delete tasks #3
```
