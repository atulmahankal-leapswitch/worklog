---
description: Rewrite auto-logged session titles into concise summaries of what was actually done, by reading each session's real prompts
argument-hint: "[today|yesterday|YYYY-MM-DD]"
---

Upgrade the task titles of auto-logged (`claude-cli`) timesheet rows for
`$ARGUMENTS` (default `today`) from raw first-prompt text into short,
meaningful summaries of what was actually accomplished.

The SessionEnd hook can only grab the first real prompt, which is often
a pasted data block or a vague opener. This command reads each session's
full set of real prompts and lets you (the model) write a proper title.

## Steps

### 1. Pull the sessions and their prompts

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog session-prompts ${ARGUMENTS:-today}
```

This returns a JSON array; each element is:

```json
{
  "id": 15,
  "project": "hostbill_tds_mode",
  "since": "12:42",
  "upto": "13:11",
  "current_task": "Client: #25 - Supriya Mahankal",
  "prompts": ["Client: #25 - Supriya Mahankal\nTDS Percentage: 2 …",
              "Always compute TDS on invoice subtotal", "…"]
}
```

If the array is empty, print "No auto-logged sessions for <date>." and stop.

### 2. Summarise each session

For every element, read its `prompts` array and write a **concise task
title** — what the session actually accomplished, in the user's own
terms where possible:

- Aim for ≤ 10 words, imperative or noun-phrase (e.g. "Always compute
  TDS on invoice subtotal", "Squash-merge backup-billing to main").
- Prefer the prompt(s) that describe the *goal* or *change*, not pasted
  data, logs, or yes/no replies.
- If several prompts cover distinct tasks, join the top 2 with "; ".
- If the prompts genuinely contain no actionable intent, keep the
  existing `current_task` (or use "Claude Code session").

### 3. Show the proposed retitles for confirmation

Present a compact before/after table:

```
| #   | Project            | Old title                       | New title                              |
|-----|--------------------|---------------------------------|----------------------------------------|
| 15  | hostbill_tds_mode  | Client: #25 - Supriya Mahankal  | Always compute TDS on invoice subtotal |
```

Ask the user: "Apply these retitles?" (Yes / Edit some / No). If the
user wants to edit, let them adjust individual titles before applying.

### 4. Apply

For each confirmed row:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog retitle time <id> "<new title>"
```

### 5. Show the result

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog show ${ARGUMENTS:-today}
```

Render as-is.

## Notes

- This only touches `claude-cli` rows — manual entries and calendar rows
  are left alone.
- Idempotent in spirit: re-running lets you refine titles further; it
  never creates or deletes rows.
- For a purely mechanical pass (no model summarisation — just strip
  Claude Code boilerplate and fall back to the first real prompt), use
  `worklog rescan-titles <date>` instead.
