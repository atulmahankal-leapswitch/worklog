---
description: Remove a timesheet entry by id (or a task entry with `task #N`)
argument-hint: "#<id>   (or `task #<id>` to remove from the tasks table)"
---

Remove a worklog entry by id from `$ARGUMENTS`.

## Parsing

- If `$ARGUMENTS` looks like `#<N>` or just `<N>` → remove from the
  **timesheet** table (the default for the manual `/worklog:add` flow).
- If `$ARGUMENTS` starts with `task` (e.g. `task #5`) → remove from the
  **tasks** table instead.

If you're not sure which id the user means, first run
`python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog show today` (or the relevant
date) — both tables show ids — and confirm with the user.

## Run

For a timesheet entry:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog remove time <id>
```

For a task entry:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog remove task <id>
```

Echo the CLI's confirmation line. If the id wasn't found, suggest running
`/worklog:show <date>` to find the correct id.
