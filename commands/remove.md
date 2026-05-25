---
description: Remove a timesheet (or task) entry by id — shows today's entries and asks if no id given
argument-hint: "(empty to pick interactively)  OR  #<id>  OR  task #<id>"
---

Remove a worklog entry.

## Behaviour

| Input              | What happens                                                       |
|--------------------|--------------------------------------------------------------------|
| Empty `$ARGUMENTS` | Show today's entries, ask which id to remove                       |
| `#N` or `N`        | Remove timesheet entry id `N`                                      |
| `task #N`          | Remove task entry id `N`                                           |

## Steps

1. **If `$ARGUMENTS` is empty:**

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog show today
   ```

   Then ask: "Which entry to remove? (e.g. `5` for timesheet, `task 3`
   for a task)." Re-enter step 1 with the user's reply.

2. **Parse `$ARGUMENTS`:**
   - Starts with `task` → remove from the tasks table.
   - Otherwise (a bare number with optional `#`) → remove from timesheet.

3. **Run:**

   For a timesheet entry:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog remove time <id>
   ```

   For a task entry:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog remove task <id>
   ```

4. Echo the CLI's confirmation. If "not found", suggest
   `/worklog:show <date>` to look up the correct id.

## Examples

```
/worklog:remove           # show + ask
/worklog:remove 5         # delete timesheet #5
/worklog:remove #5        # same
/worklog:remove task #3   # delete tasks #3
```
