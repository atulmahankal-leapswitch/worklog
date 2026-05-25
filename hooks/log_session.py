#!/usr/bin/env python3
"""SessionEnd hook: log a Claude Code session to the worklog SQLite database.

Claude Code invokes SessionEnd hooks with a JSON payload on stdin:
  session_id, transcript_path, cwd, hook_event_name, reason

Reason is one of: "logout", "clear", "prompt_input_exit", "other".
All reasons are treated as session-ended and logged the same way.

Start time  = first event timestamp in the transcript JSONL.
End time    = last event timestamp (or wall-clock now if missing).
Project     = basename of cwd.
Task        = first user prompt of the session (truncated).

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

from lib import db  # noqa: E402

MIN_DURATION_SEC = 120


def read_transcript(path: str):
    events = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        pass
    return events


def first_user_prompt(events) -> str:
    for e in events:
        msg = e.get("message") or {}
        if msg.get("role") == "user":
            content = msg.get("content")
            if isinstance(content, str):
                return content.strip().splitlines()[0][:200]
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "text":
                        return c.get("text", "").strip().splitlines()[0][:200]
    return ""


def get_timestamps(events):
    ts = []
    for e in events:
        t = e.get("timestamp")
        if not t:
            continue
        try:
            ts.append(datetime.fromisoformat(t.replace("Z", "+00:00")))
        except ValueError:
            continue
    return ts


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    transcript_path = payload.get("transcript_path", "")
    cwd = payload.get("cwd", "") or os.getcwd()
    reason = payload.get("reason", "other")

    events = read_transcript(transcript_path)
    stamps = get_timestamps(events)
    if not stamps:
        # No transcript to anchor a start time — nothing useful to log.
        return 0

    start = stamps[0].astimezone()
    # End = last transcript event if present, else wall-clock now.
    end = stamps[-1].astimezone() if len(stamps) > 1 else datetime.now().astimezone()
    dur_sec = (end - start).total_seconds()
    if dur_sec < MIN_DURATION_SEC:
        return 0

    try:
        db.init()
    except Exception as e:
        print(f"worklog log_session: {e}", file=sys.stderr)
        return 0

    # Only log if cwd is a registered project with auto_log enabled.
    match = db.find_project_by_path(cwd)
    if not match or not match["auto_log"]:
        return 0
    project = match["name"]

    task = first_user_prompt(events) or "Claude Code session"
    mins = int(dur_sec // 60)

    try:
        db.add_timesheet(
            date=start.date().isoformat(),
            since=start.strftime("%H:%M"),
            upto=end.strftime("%H:%M"),
            minutes=mins,
            project=project,
            task=task,
            ref=f"claude-cli:{reason}",
            source="claude-cli",
        )
    except Exception as e:
        print(f"worklog log_session: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
