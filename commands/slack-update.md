---
description: Reply in the original Slack thread when a Slack-sourced task changes status
argument-hint: "(no args — processes everything pending)"
---

For each Slack-sourced task whose status has progressed past `open` since
the last Slack notification (or was never notified), post a reply in the
**original Slack thread** with the new status, then record that we
notified so we don't double-post next time.

## Steps

### 1. Fetch the queue

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog list-slack-pending
```

Parse the JSON array. If empty, print "No Slack status updates pending."
and stop.

### 2. For each pending task

The local row carries `reference` — a Slack message permalink — and the
new `status` + optional `remark`. Plan:

1. **Parse the permalink** into channel id + ts. Slack permalink format:
   `https://<workspace>.slack.com/archives/<CHANNEL_ID>/p<TS_NO_DOT>`
   where `TS_NO_DOT` is the message timestamp with the `.` removed
   (e.g. `p1700000000123456` → ts `1700000000.123456`).
   - Channel id = the segment after `/archives/`.
   - Ts = insert a `.` six digits before the end of the `p…` segment.
2. **Compose the message** based on status:

   | Status        | Message                                                          |
   |---------------|------------------------------------------------------------------|
   | `done`        | ✅ Done — `<task title>` [worklog #<id>]<br>_<remark if any>_     |
   | `in_progress` | 👀 Working on it — `<task title>` [worklog #<id>]                |
   | `blocked`     | 🛑 Blocked — `<task title>` [worklog #<id>]<br>_<remark if any>_  |
   | anything else | `<status>` — `<task title>` [worklog #<id>]                      |
3. **Post the reply** via `mcp__claude_ai_Slack__slack_send_message`
   with `channel: <CHANNEL_ID>`, `text: <composed>`, and
   `thread_ts: <parsed ts>` so it threads under the original message.
4. **Record the notification** locally so this task drops out of the
   queue:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog link-slack <task_id> <returned_message_ts>
   ```
   Use the `ts` returned by `slack_send_message`. If the API doesn't
   return one, fall back to the current epoch time.

### 3. Summary

Print:

```
| #  | Task                          | New status   | Thread          | Action     |
|----|-------------------------------|--------------|-----------------|------------|
| #1 | look at PR#42                 | done         | #infra @alice   | replied    |
```

End with a one-line total: `N replied, F failed.`

If any reply failed (Slack rate limit, deleted channel, etc.), include
the error in the row's Action column but **do not** call `link-slack` —
that way the task stays in the queue and the next run will retry.

## Notes

- Read-only `list-slack-pending` and `link-slack` against the local DB;
  the only outbound write is `slack_send_message`.
- The plugin **never** posts unsolicited status updates — only when a
  task's status was actually changed after import (e.g. via
  `/worklog:add` with `status done`, or
  `python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog update-status <id> <status>`).
- If you want to *suppress* a particular task from ever notifying back
  to Slack, clear its `reference` (use `update-status` after a future
  schema change, or edit the DB directly). A cleaner CLI for this can
  be added later.
