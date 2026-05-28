#!/usr/bin/env python3
"""SessionEnd hook: log the most-recent Claude Code session to worklog.

Claude Code invokes SessionEnd hooks with a JSON payload on stdin:
  session_id, transcript_path, cwd, hook_event_name, reason

A single transcript file can span many calendar days when the user
resumes the same session, so we cannot treat the whole file as one
session. We chunk by idle gap (>30 min = new session) and only log the
LATEST chunk — that's "the session that just ended".

Only fires when cwd matches a registered project (with auto_log=1).
Sessions shorter than 2 minutes are skipped.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import db, git, transcripts  # noqa: E402

MIN_DURATION_SEC = 120


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    transcript_path = payload.get("transcript_path", "")
    cwd = payload.get("cwd", "") or os.getcwd()
    reason = payload.get("reason", "other")

    chunk = transcripts.latest_session(transcript_path)
    if not chunk or chunk.minutes * 60 < MIN_DURATION_SEC:
        return 0

    try:
        db.init()
    except Exception as e:
        print(f"worklog log_session: {e}", file=sys.stderr)
        return 0

    match = db.find_project_by_path(cwd)
    if not match or not match["auto_log"]:
        return 0
    project = match["name"]

    start = chunk.start.astimezone()
    end = chunk.end.astimezone()

    # Prefer git commit subjects from this session window as the title —
    # it's the cleanest "what got done" signal. Fall back to the first
    # real user prompt only when no commits exist.
    commits = git.commit_subjects(match["path"], start, end) if match["path"] else []
    task = git.summarise(commits) or chunk.first_prompt
    ref = f"claude-cli:{reason}" + (":git" if commits else "")

    try:
        db.add_timesheet(
            date=start.date().isoformat(),
            since=start.strftime("%H:%M"),
            upto=end.strftime("%H:%M"),
            minutes=chunk.minutes,
            project=project,
            task=task,
            ref=ref,
            source="claude-cli",
        )
    except Exception as e:
        print(f"worklog log_session: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
