---
description: Pull recent Slack mentions / DMs as a multi-select picker; ticked items become tasks
argument-hint: "[hours]   (look-back window, default 24)"
---

Surface recent Slack messages that might be action items and let the user
tick which ones should become tasks. Already-imported messages (by Slack
permalink) are filtered out automatically.

## Steps

### 1. Compute the look-back window

```
HOURS=${ARGUMENTS:-24}
```

### 2. Identify the current Slack user

Call `mcp__claude_ai_Slack__slack_search_users` with `query: "me"` to
resolve the user's Slack user id. Cache it for the rest of the run.

(Alternative if your Slack MCP advertises `me` differently: use the env
`SLACK_USER_ID` if you have one; otherwise prompt the user.)

### 3. Gather candidate messages from Slack

Make these calls in parallel:

| Source                  | MCP call                                                                                            |
|-------------------------|-----------------------------------------------------------------------------------------------------|
| Direct mentions         | `mcp__claude_ai_Slack__slack_search_public_and_private` with `query: "<@<USER_ID>> after:<DATE>"`   |
| DMs (with anyone)       | `mcp__claude_ai_Slack__slack_search_public_and_private` with `query: "is:dm to:<@<USER_ID>> after:<DATE>"` |
| Saved-for-later (best effort) | `mcp__claude_ai_Slack__slack_search_public_and_private` with `query: "has::bookmark from:<@<USER_ID>> after:<DATE>"` |

Merge results; dedupe on `permalink`.

For each candidate keep: `permalink`, `text`, `user` (name + id),
`channel` (name + id), `ts` (message timestamp), `thread_ts` (if any).

### 4. Filter out already-imported messages

Get the list of existing Slack-sourced tasks:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog tasks-by-source slack
```

Build a set of references from the JSON output. Drop any candidate whose
`permalink` is in that set.

If nothing remains, print "Slack inbox is empty for the last $HOURS hours."
and exit.

### 5. Show a multi-select picker

Build `AskUserQuestion` with `multiSelect: true`. One option per
candidate. Label format (≤ 80 chars; truncate text with `…`):

```
#<channel>  @<sender_name>: <message text, truncated>
```

Description field: include the message timestamp ("3 h ago") and a hint
about which project the message looks like it belongs to (see step 6).

If more than 4 candidates, split into multiple sequential questions
(`AskUserQuestion` caps at 4 options each).

### 6. Best-guess project per message

Heuristic, in order:

1. Channel name maps to a registered project? Look up via
   `python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog projects --format json` and
   match channel name (case-insensitive) against project names.
2. Does the message text mention a registered project name? Use that.
3. Default: `Inbox`. The user can edit the task later.

Surface the guess in the option's description so the user can object.

### 7. Append the ticked items as tasks

For each ticked option:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog add task \
  --project "<guessed project>" \
  --task "<message text, truncated to 200 chars>" \
  --reference "<slack permalink>" \
  --remark "from #<channel> by @<sender_name>" \
  --status open \
  --source slack
```

### 8. Summary

Print a markdown table:

```
| #  | Project | Task                                  | From                  | Action   |
|----|---------|---------------------------------------|-----------------------|----------|
| #5 | Inbox   | "can you look at PR#42?"              | #infra @alice         | added    |
```

End with a one-liner: `N selected, A added, S skipped (already imported)`.

Remind the user that `/worklog:remove task #<id>` deletes any task added
by mistake, and `/worklog:slack-update` (Phase 2) will reply in-thread
when its status changes.

## Notes

- Read-only against Slack. Only `bin/worklog` writes.
- If the Slack MCP isn't connected, `/worklog:doctor` will show that —
  this command won't be functional until it's healthy.
- Dedup is by **permalink**. Renaming a channel changes the permalink and
  may cause a re-import; that's acceptable.
