"""SessionEnd hook integration tests.

We invoke `hooks/log_session.py` as a real subprocess (the way Claude Code
would), feeding a fabricated transcript and payload, and assert what landed
in the SQLite DB.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from lib import db

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "hooks" / "log_session.py"


def _write_transcript(tmp_path, *,
                      start_iso="2026-01-01T10:00:00+00:00",
                      end_iso="2026-01-01T10:30:00+00:00",
                      first_prompt="implement OTP"):
    p = tmp_path / "transcript.jsonl"
    lines = [
        {"timestamp": start_iso, "message": {"role": "user", "content": first_prompt}},
        {"timestamp": end_iso,   "message": {"role": "assistant", "content": "done"}},
    ]
    p.write_text("\n".join(json.dumps(line) for line in lines) + "\n")
    return str(p)


def _run_hook(payload, tmp_path):
    env = {**os.environ, "WORKLOG_HOME": str(tmp_path)}
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload).encode(),
        capture_output=True,
        env=env,
    )


def test_hook_skips_unregistered_cwd(tmp_path):
    proc = _run_hook(
        {"transcript_path": _write_transcript(tmp_path),
         "cwd": "/tmp/definitely-not-registered",
         "reason": "prompt_input_exit"},
        tmp_path,
    )
    assert proc.returncode == 0
    assert db.list_timesheet("2026-01-01") == []


def test_hook_logs_when_cwd_matches_registered_project(tmp_path):
    cwd = tmp_path / "myrepo"
    cwd.mkdir()
    db.add_project(name="MyRepo", path=str(cwd))

    proc = _run_hook(
        {"transcript_path": _write_transcript(tmp_path),
         "cwd": str(cwd),
         "reason": "prompt_input_exit"},
        tmp_path,
    )
    assert proc.returncode == 0, proc.stderr
    rows = db.list_timesheet("2026-01-01")
    assert len(rows) == 1
    row = rows[0]
    assert row["task"] == "implement OTP"
    assert row["minutes"] == 30
    assert row["ref"] == "claude-cli:prompt_input_exit"
    assert row["source"] == "claude-cli"


def test_hook_skips_when_auto_log_disabled(tmp_path):
    cwd = tmp_path / "untracked"
    cwd.mkdir()
    db.add_project(name="Untracked", path=str(cwd), auto_log=False)

    proc = _run_hook(
        {"transcript_path": _write_transcript(tmp_path),
         "cwd": str(cwd),
         "reason": "logout"},
        tmp_path,
    )
    assert proc.returncode == 0
    assert db.list_timesheet("2026-01-01") == []


def test_hook_skips_sessions_under_2_minutes(tmp_path):
    cwd = tmp_path / "fast"
    cwd.mkdir()
    db.add_project(name="Fast", path=str(cwd))

    transcript = _write_transcript(
        tmp_path,
        start_iso="2026-01-01T10:00:00+00:00",
        end_iso="2026-01-01T10:01:30+00:00",  # 90 s
    )
    proc = _run_hook(
        {"transcript_path": transcript, "cwd": str(cwd),
         "reason": "prompt_input_exit"},
        tmp_path,
    )
    assert proc.returncode == 0
    assert db.list_timesheet("2026-01-01") == []
