---
description: List all registered projects with path, path-exists, auto-log status, and last activity date
---

Show every project registered in the worklog database, with:

- **Path** — the registered absolute path (or `—` if none).
- **Path exists** — whether the directory still exists on disk
  (`yes` / **`no`** / `—`).
- **Auto-log** — whether SessionEnd auto-logging is enabled for sessions
  whose `cwd` falls under this project's path.
- **Last active** — most recent date the project shows up in `tasks` or
  `timesheet`.

Run this and render the output as-is (it's already a markdown table):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog projects
```

If the list is empty, suggest:

```
/worklog:add register project "<name>" at "<absolute-path>"
```

so Claude Code sessions in that folder start being auto-logged.
