---
description: Register the current working directory as a project for automatic Claude Code session logging
argument-hint: "[project name]   (optional — defaults to the cwd folder name)"
---

Register the **current working directory** as a worklog project so that
every Claude Code session that ends in this directory (or any
subdirectory) gets auto-logged to the timesheet.

## Steps

1. Get the current directory:

   ```bash
   PWD_NOW="$(pwd)"
   ```

2. Project name — use `$ARGUMENTS` if non-empty, else the basename of the
   cwd.

3. Run:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog project register \
     --path "$PWD_NOW" \
     ${ARGUMENTS:+--name "$ARGUMENTS"}
   ```

4. Echo the CLI's confirmation, then suggest:
   - `/worklog:projects` to verify the row.
   - `/worklog:project_remove` to undo if it was a mistake.

If a project at this path already exists, the CLI updates it
(turning auto-log back on if it was off).
