#!/usr/bin/env bash
# worklog installer: prepare SQLite DB and print a setup checklist.
#
# The actual MCP integration health checks (ClickUp/Calendar/Slack/Gmail)
# happen inside Claude Code via `/worklog:doctor` because MCP connectors are
# only reachable from Claude sessions.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKLOG_HOME="${WORKLOG_HOME:-$HOME/.worklog}"

bold() { printf "\033[1m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }
red() { printf "\033[31m%s\033[0m\n" "$*"; }

bold "1/3  Checking Python"
if ! command -v python3 >/dev/null; then
  red "    python3 not found. Install Python 3.9+ first."
  exit 1
fi
green "    $(python3 --version)"

bold "2/3  Initialising SQLite database at ${WORKLOG_HOME}/worklog.db"
mkdir -p "${WORKLOG_HOME}"
python3 "${REPO_DIR}/bin/worklog" init

bold "3/3  Marking scripts executable"
chmod +x "${REPO_DIR}/bin/worklog" "${REPO_DIR}/hooks/log_session.py"
green "    done"

cat <<EOF

$(bold "Next steps:")

1. Enable the plugin in Claude Code:

     $(yellow "/plugin install ${REPO_DIR}")

   or, if you cloned to a marketplace path Claude already knows, enable from
   the plugin UI.

2. Inside Claude Code, validate integrations:

     $(yellow "/worklog:doctor")

   - $(bold "ClickUp")          — REQUIRED for /worklog:push
   - $(bold "Google Calendar")  — needed if you use /worklog:sync-calendar
   - $(bold "Gmail")            — needed to enrich calendar sync with Read AI data
   - $(bold "Slack")            — needed only if you later enable Slack notifications

   For any FAIL, run /mcp inside Claude Code and connect the missing service.

3. Try it:

     /worklog:add "LeapBuilder: fix login redirect, PR#42"
     /worklog:show today
     /worklog:push today

EOF
