---
description: Push worklog tasks for a date to ClickUp — create new or update existing
argument-hint: "[today|yesterday|YYYY-MM-DD]"
---

Push the worklog tasks for `$ARGUMENTS` (default `today`) to ClickUp.

## Step 1 — Fetch pending tasks

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog list-pending ${ARGUMENTS:-today}
```

This returns a JSON array of tasks. For each task the JSON has:
`id`, `project`, `task`, `status`, `reference`, `remark`, `clickup_list_id`.

If the array is empty, print "Nothing to push." and exit.

## Step 2 — For each task

### If `clickup_task_id` is present in the local row

(Skip — `list-pending` already filters those out. They are considered
synced; rerun with `--all` in a future version if needed.)

### If the local task has no `clickup_task_id`

Use the ClickUp MCP to **find or create** the task:

1. **Search** ClickUp for an existing open task with the same title:
   - Tool: `mcp__claude_ai_ClickUp__clickup_search` with the task title.
   - If exactly one open match is found, treat it as existing.
2. **If existing match** — update it:
   - Tool: `mcp__claude_ai_ClickUp__clickup_update_task` with:
     - `status` mapped from local status (`done` → "complete",
       `in_progress` → "in progress", `blocked` → "blocked", else "open").
     - Append the local `remark` to the description if non-empty.
3. **If no match** — create a new task:
   - First decide the ClickUp **List** to create it in:
     - If `clickup_list_id` on the local task (from project mapping) is set,
       use that list.
     - Otherwise ASK THE USER. Show the workspace hierarchy:
       ```
       mcp__claude_ai_ClickUp__clickup_get_workspace_hierarchy
       ```
       Present Space → Folder → List as a numbered choice. Once the user
       picks a List, save the mapping for the project so future pushes don't
       re-ask:
       ```bash
       python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog set-project-list \
         "<project>" "<list_id>"
       ```
   - Then create the task:
     ```
     mcp__claude_ai_ClickUp__clickup_create_task
     ```
     with name = local task title, description containing project + reference
     + remark, status mapped as above.
4. **Record the ClickUp task id locally** so it isn't pushed again:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog link-task <local_id> <clickup_id>
   ```

## Step 3 — Summary

Print a table:

```
| # | Project | Task | Action  | ClickUp ID |
|---|---------|------|---------|------------|
```

…and one-line totals: `N tasks pushed (X created, Y updated, Z skipped)`.

## Notes

- If the ClickUp MCP returns an auth error, stop and tell the user to run
  `/worklog:doctor` and reconnect ClickUp via `/mcp`.
- This command never deletes ClickUp tasks.
