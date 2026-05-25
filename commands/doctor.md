---
description: Health-check worklog plugin — DB, ClickUp (required), Google Calendar / Gmail / Slack (optional)
---

Validate that the worklog plugin is set up correctly.

## Checks (run in parallel where possible)

### 1. SQLite database

Run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog init
```

PASS if the command prints either `Initialised …/worklog.db` (fresh DB)
or `Already initialised at …/worklog.db` (DB already present — the normal
case after first run).

### 2. ClickUp MCP — **REQUIRED** for `/worklog:push`

Call `mcp__claude_ai_ClickUp__clickup_get_workspace_hierarchy`.
PASS if a workspace is returned. FAIL otherwise.

### 3. Google Calendar MCP — optional, for `/worklog:sync-calendar`

Call `mcp__claude_ai_Google_Calendar__list_calendars`. PASS if any
calendar returned.

### 4. Gmail MCP — optional, used to enrich calendar sync with Read AI recaps

Confirm the Gmail connector is listed in the deferred MCP tool list. PASS
if `mcp__claude_ai_Gmail__authenticate` is available, otherwise FAIL with
the hint "connect Gmail via /mcp to enable Read AI enrichment".

### 5. Slack MCP — optional, for future task notifications

Call `mcp__claude_ai_Slack__slack_search_users` with `query: "me"` and
`count: 1`. PASS if it returns without an auth error.

## Output

Print a markdown table:

```
| # | Component       | Required | Status | Notes                       |
|---|-----------------|----------|--------|-----------------------------|
| 1 | SQLite database | yes      | PASS   | /home/.../worklog.db        |
| 2 | ClickUp         | yes      | PASS   | workspace "Leapswitch"      |
| 3 | Google Calendar | no       | PASS   | 3 calendars                 |
| 4 | Gmail (Read AI) | no       | FAIL   | connect via /mcp            |
| 5 | Slack           | no       | PASS   | reachable                   |
```

Then a one-line verdict: `N/5 healthy — required components: <ok|missing>`.

If any **required** component fails, list the exact fix steps. Otherwise the
plugin is ready to use.
