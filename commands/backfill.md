---
description: Scan Claude Code transcripts of registered projects and insert any missing timesheet rows for a date
argument-hint: "[today|yesterday|YYYY-MM-DD]"
---

Backfill the worklog timesheet from Claude Code transcripts for
`$ARGUMENTS` (default `today`).

## When to use this

The SessionEnd hook only logs sessions that **cleanly exit** (Ctrl+D,
window close, `/clear`, `/logout`). Sessions that are still running, or
that were closed before the plugin was installed, leave no row. This
command sweeps every registered project's transcript directory and adds
any missing rows for the chosen date.

## Run

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog backfill ${ARGUMENTS:-today}
```

The output is a pre-formatted markdown table — render it as-is.

## Behaviour

- Iterates over every project registered with `auto_log=1` and a `path`.
- For each project, reads every `*.jsonl` under
  `~/.claude/projects/<encoded-path>/`.
- Splits each transcript into **session chunks** using a 30-minute idle
  gap as the boundary (so a transcript that's been resumed across many
  days is correctly broken up).
- For each chunk that starts on the target date and lasted ≥ 2 min, adds
  a timesheet row.
- Dedup is by `(date, since, task)` — re-running is safe.

## After running

Use `/worklog:show <date>` to review what landed. Remove any
misclassified rows with `/worklog:remove <id>`.
