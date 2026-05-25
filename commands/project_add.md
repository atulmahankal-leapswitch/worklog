---
description: Register the current working directory as a project for automatic Claude Code session logging — confirms the name
argument-hint: "[project name]   (optional — defaults to the cwd folder name)"
---

Register the **current working directory** as a worklog project so that
every Claude Code session that ends in this directory (or any
subdirectory) gets auto-logged to the timesheet.

## Steps

1. Get the cwd and a proposed name:

   ```bash
   PWD_NOW="$(pwd)"
   DEFAULT_NAME="$(basename "$PWD_NOW")"
   ```

2. **Pick the name:**
   - If `$ARGUMENTS` is non-empty → use it as the name.
   - Else, **ask the user**: "Register this folder as project
     **`<DEFAULT_NAME>`**? (Enter a different name to override, or just
     confirm.)" Wait for the answer; if blank/confirm, use `$DEFAULT_NAME`.

3. Run:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog project register \
     --path "$PWD_NOW" --name "<chosen name>"
   ```

4. Echo the CLI's confirmation. Suggest:
   - `/worklog:projects` to verify the row.
   - `/worklog:project_remove` to undo if needed.

If a project at this path already exists, the CLI updates it
(turning auto-log back on if it was off).
