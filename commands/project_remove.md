---
description: Stop auto-logging Claude Code sessions for the current working directory
---

Turn off **automatic Claude Code session logging** for the current
working directory. The project row is preserved (so historical timesheet
and task entries still point to it) — only `auto_log` is set to `0`.

## Steps

1. Get the current directory:

   ```bash
   PWD_NOW="$(pwd)"
   ```

2. Run:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog project untrack --path "$PWD_NOW"
   ```

3. Echo the CLI's confirmation.

If no registered project covers this path, the CLI says so — nothing was
ever being tracked here.

To re-enable auto-logging, run `/worklog:project_add` again.
