---
description: Pull recent Slack mentions / DMs as a multi-select picker; ticked items become tasks. Resolves thread roots and lets the user edit task text before saving.
argument-hint: "[hours]   (look-back window, default 24)"
---

Surface recent Slack messages that might be action items and let the user
tick which ones should become tasks. Each candidate is **resolved to its
thread root** so the picker shows the original ask (not someone's reply),
and the user can **edit the task text** before it's saved.

Already-imported messages (by Slack permalink) are filtered out.

## Steps

### 1. Compute the look-back window

```
HOURS=${ARGUMENTS:-24}
```

### 2. Identify the current Slack user

Call `mcp__claude_ai_Slack__slack_search_users` with `query: "me"` to
resolve the user's Slack user id. Cache it for the rest of the run.

### 3. Gather candidate messages from Slack

Make these calls in parallel:

| Source                  | MCP call                                                                                            |
|-------------------------|-----------------------------------------------------------------------------------------------------|
| Direct mentions         | `mcp__claude_ai_Slack__slack_search_public_and_private` with `query: "<@<USER_ID>> after:<DATE>"`   |
| DMs to user             | `mcp__claude_ai_Slack__slack_search_public_and_private` with `query: "is:dm to:<@<USER_ID>> after:<DATE>"` |
| Saved-for-later         | `mcp__claude_ai_Slack__slack_search_public_and_private` with `query: "has::bookmark from:<@<USER_ID>> after:<DATE>"` |

Merge results; dedupe on `permalink`.

For each candidate keep: `permalink`, `text`, `user` (name + id),
`channel` (name + id), `ts` (message timestamp), `thread_ts` (if any).

### 4. Resolve thread roots (IMPORTANT)

A candidate may itself be a **reply** in a thread (e.g. someone wrote
"sure, give this to Atul" replying to a real task message above). The
picker MUST show the **root** of the thread, not the reply, otherwise the
user picks based on the wrong text.

For each candidate:

- If `thread_ts` is present and `thread_ts != ts`, this is a reply.
  Fetch the thread:
  ```
  mcp__claude_ai_Slack__slack_read_thread
      channel: <channel_id>
      thread_ts: <thread_ts>
      limit: 1     # only need the first message
  ```
  Replace the candidate's `text` with the root message's text. Keep the
  reply text aside as `reply_excerpt` for context. Update `permalink`
  to point at the root (use the thread's first message permalink if
  returned; otherwise leave the original).
- If `thread_ts` is absent or equals `ts`, the candidate **is** the root —
  no extra call needed.

### 5. Filter out already-imported messages

Get existing Slack-sourced task references:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog tasks-by-source slack
```

Drop candidates whose root permalink is already in the JSON output's
`reference` set. If nothing remains, print "Slack inbox is empty for the
last $HOURS hours." and stop.

### 6. Best-guess project per candidate

Heuristic, in order:

1. Channel name matches a registered project name (case-insensitive) —
   fetched via `python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog projects --format json`.
2. Message text mentions a registered project name.
3. Default: `Inbox`.

### 7. Multi-select — pick which messages to import

`AskUserQuestion` with `multiSelect: true`. One option per candidate.

**Label** format (≤ 80 chars; truncate root text with `…`):

```
#<channel>  @<sender_name>: <ROOT message text>
```

**Description** must include:

1. The Slack permalink (raw URL — let the user click).
2. The thread reply (if any), prefixed `↳ reply:` so the user sees the
   secondary context.
3. The best-guess project name.

Example description:

```
https://leapswitch.slack.com/archives/C123/p1700000000123456
↳ reply by @Ishan: "give this to Atul he can assign it…"
Guessed project: Hostbill
```

If > 4 candidates, batch into multiple sequential `AskUserQuestion`
calls (Claude Code caps each question at 4 options).

Keep `kind=task` plus the root permalink, project guess, and *full root
text* associated with each option so step 8 can use them.

### 8. Per-ticked: confirm / edit the task text

For **each** option the user ticked, ask one focused free-text question
before saving:

```
AskUserQuestion {
  question: "Task text for <permalink>?  (Edit or press Enter to accept)"
  header: "Edit task"
  multiSelect: false
  options: [
    { label: "<one-line summary derived from root text>",
      description: "From: #<channel> @<sender_name>. Original:\n<full root text>" },
    { label: "Skip — don't add this one",
      description: "Drop it; you can re-pick it on a future /worklog:slack-inbox run." }
  ]
}
```

`AskUserQuestion` always offers an **"Other"** input — the user can type
a completely custom task title there. So they get three real choices:

- accept the auto-summary (option 1),
- skip (option 2), or
- type their own task text ("Other").

Use whatever they chose as the task title. The original root text always
goes into `--remark` for full context.

### 9. Append the confirmed items

For each retained candidate:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog add task \
  --project "<guessed project>" \
  --task "<final task text from step 8>" \
  --reference "<slack root permalink>" \
  --remark "$(printf 'from #%s by @%s\n\n%s' "<channel>" "<sender>" "<full root text>")" \
  --status open \
  --source slack
```

(Use shell printf so the remark preserves newlines.)

### 10. Summary

Print a markdown table:

```
| #   | Project | Task                                  | From          | Link                 | Action  |
|-----|---------|---------------------------------------|---------------|----------------------|---------|
| #5  | Hostbill| Hostbill module: suspend on non-pay   | #infra @akar  | https://…/p170000…   | added   |
```

End with totals: `N selected, A added, S skipped (already imported or
user-skipped)`.

Remind the user about `/worklog:remove task #<id>` and
`/worklog:slack-update` for status reply-backs.

## Notes

- The thread-root resolution in step 4 is the fix for the bug where the
  picker showed a reply ("give this to Atul…") instead of the actual ask
  ("we need a Hostbill module that suspends…").
- The edit step in step 8 means the row in the DB reflects what the
  *user thinks* the task is, while `--remark` preserves the verbatim
  Slack text for audit.
- Dedup is by **root permalink**. Re-runs are safe.
