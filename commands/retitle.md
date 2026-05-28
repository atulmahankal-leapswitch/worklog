---
description: Rewrite auto-logged session titles into concise one-line summaries — prefers git commit subjects, falls back to real user prompts
argument-hint: "[today|yesterday|YYYY-MM-DD]"
---

Upgrade the task titles of auto-logged (`claude-cli`) timesheet rows for
`$ARGUMENTS` (default `today`) into short, meaningful summaries of what
was actually accomplished.

The SessionEnd hook concatenates the session's git commit subjects
(`A; B (+N more)`); for sessions with many commits or long subjects
that's noisy. This command reads the **full list of commit subjects +
real user prompts** for each session and lets you (the model) write a
true one-line summary.

## Steps

### 1. Pull the sessions with their commits + prompts

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog session-prompts ${ARGUMENTS:-today}
```

Each element looks like:

```json
{
  "id": 19,
  "project": "CloudPe Website",
  "since": "17:58",
  "upto": "18:03",
  "current_task": "Move /resources/compare → /compare …; Bind wrangler …",
  "commits": [
    "Move /resources/compare → /compare with -alternative slugs + home Product schema",
    "Bind wrangler dev to 0.0.0.0 in npm run preview for LAN access",
    "Fix flaky preview port"
  ],
  "prompts": ["is local repo clean?", "remove the duplicated…", "…"]
}
```

If the array is empty, print "No auto-logged sessions for <date>." and stop.

### 2. Write a true one-line summary per session

For every element, **prefer commits over prompts** when summarising:

- **If `commits` is non-empty** — read all commit subjects and write a
  single ≤ 12-word summary that captures the *overall theme* of the
  session. Examples:
  - 3 commits about `/compare` routing → "Move /resources/compare to /compare with home schema"
  - mixed bag (route move + LAN binding + flaky-port fix) →
    "Compare-page rework and dev-server LAN binding"
  - one commit → reuse its subject verbatim if it's already concise,
    else compress.
- **Else if `prompts` has actionable content** — summarise from there.
- **Else** — keep `current_task` (or use "Claude Code session").

Rules:
- ≤ 12 words, no markdown, no trailing punctuation, no quotes around
  the title.
- Use the user's terminology (paths, feature names, ids) verbatim where
  possible.
- Don't invent details that aren't in commits or prompts.

### 3. Show the proposed retitles for confirmation

Present a compact before/after table:

```
| #   | Project          | Old title                                | New title                                |
|-----|------------------|------------------------------------------|------------------------------------------|
| 19  | CloudPe Website  | Move /resources/compare → /compare …; …  | Move compare routes and bind dev to LAN  |
```

Ask the user: "Apply these retitles?" (Yes / Edit some / No). If they
want to edit, let them adjust individual titles before applying.

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

- Only touches `claude-cli` rows; manual entries and calendar rows are
  left alone.
- Idempotent — re-running lets you refine titles further; it never
  creates or deletes rows.
- For a purely mechanical pass (just refresh from git commits or strip
  Claude Code boilerplate, no model summarisation), use
  `worklog rescan-titles <date>` instead.
