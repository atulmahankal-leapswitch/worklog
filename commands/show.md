---
description: Show worklog tasks and time entries for a date, with ClickUp list + push state; offers to fix any wrong task description
argument-hint: "[today|yesterday|YYYY-MM-DD]"
---

Show the worklog for `$ARGUMENTS` (defaults to `today` if empty).

## 1. Render

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog show ${ARGUMENTS:-today}
```

Render the output as-is — it's already markdown. Each timesheet row shows:

```
#<id>  <source>  <since>–<upto> (<dur>)  <project> → <ClickUp list>  [new|cu:<id>] | <task>
```

- `→ <ClickUp list>` is the project's mapped ClickUp List (or
  `unmapped` if the project has no mapping yet — set one with
  `/worklog:project_add`).
- `[new]` = not yet pushed to ClickUp; `[cu:<id>]` = already pushed.

If the database isn't initialised (you'll see an error), run
`python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog init` and retry.

## 2. Offer to fix wrong task descriptions

After rendering, ask the user **once**:

> "Any task description to fix? (reply with e.g. `15: better summary`, or
> `no`)"

- If they reply `no` / nothing → stop.
- If they give one or more `&lt;id&gt;: &lt;new text&gt;` pairs, apply each:

  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog retitle time <id> "<new text>"
  ```

  Then re-render (step 1) so they see the corrected worklog.

For bulk, model-written summaries of a whole day, suggest
`/worklog:retitle <date>` instead.
