---
description: Show worklog tasks and time entries for a date (today/yesterday/YYYY-MM-DD)
argument-hint: "[today|yesterday|YYYY-MM-DD]"
---

Show the worklog for `$ARGUMENTS` (defaults to `today` if empty).

Run this command:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog show ${ARGUMENTS:-today}
```

Render the output as-is — it is already formatted as markdown.

If the database hasn't been initialised yet (you'll see an error), run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog init
```

then retry.
