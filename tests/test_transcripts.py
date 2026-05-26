"""Tests for lib.transcripts — session chunking and prompt filtering."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from lib import transcripts


def _write_transcript(tmp_path, events):
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    return p


def _ts(year, month, day, hour, minute):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc).isoformat()


def _user(text):
    return {"message": {"role": "user", "content": text}}


def test_encoded_project_dir_handles_spaces_and_slashes():
    p = "/home/atul/Documents/Projects/Hostbill Modules/modules/Hosting/quickpost"
    expected = "-home-atul-Documents-Projects-Hostbill-Modules-modules-Hosting-quickpost"
    assert transcripts.encoded_project_dir(p) == expected


def test_transcript_dir_is_under_claude_projects():
    d = transcripts.transcript_dir("/home/atul/Documents/__Personal/worklog")
    assert d.name == "-home-atul-Documents-__Personal-worklog"
    assert ".claude/projects" in str(d)


def test_chunk_sessions_splits_on_idle_gap(tmp_path):
    events = [
        # All within 30-min gaps → one chunk
        {"timestamp": _ts(2026, 5, 26, 9, 41), **_user("start of session 1")},
        {"timestamp": _ts(2026, 5, 26, 9, 50), **_user("more in session 1")},
        {"timestamp": _ts(2026, 5, 26, 10, 15), **_user("still session 1")},
        # 46-minute idle gap → new session starts
        {"timestamp": _ts(2026, 5, 26, 11, 1), **_user("start of session 2")},
        {"timestamp": _ts(2026, 5, 26, 11, 5), **_user("end of session 2")},
    ]
    p = _write_transcript(tmp_path, events)
    chunks = transcripts.chunk_sessions(p)
    assert len(chunks) == 2
    assert chunks[0].minutes == 34  # 09:41 -> 10:15
    assert chunks[1].minutes == 4   # 11:01 -> 11:05


def test_chunk_sessions_spanning_days(tmp_path):
    """A resumed transcript is correctly chunked, not collapsed."""
    events = [
        {"timestamp": _ts(2026, 4, 27, 15, 6), **_user("April session")},
        {"timestamp": _ts(2026, 4, 27, 15, 20), **_user("more April")},
        # 29-day gap
        {"timestamp": _ts(2026, 5, 26, 9, 41), **_user("May session")},
        {"timestamp": _ts(2026, 5, 26, 10, 5), **_user("end of May session")},
    ]
    p = _write_transcript(tmp_path, events)
    chunks = transcripts.chunk_sessions(p)
    assert len(chunks) == 2
    assert chunks[0].start.date().isoformat() == "2026-04-27"
    assert chunks[1].start.date().isoformat() == "2026-05-26"
    assert chunks[1].minutes == 24


def test_latest_session_returns_most_recent_chunk(tmp_path):
    events = [
        {"timestamp": _ts(2026, 4, 27, 10, 0), **_user("old session")},
        {"timestamp": _ts(2026, 5, 26, 11, 0), **_user("new session")},
        {"timestamp": _ts(2026, 5, 26, 11, 5), **_user("ending")},
    ]
    p = _write_transcript(tmp_path, events)
    chunk = transcripts.latest_session(p)
    assert chunk is not None
    assert chunk.start.date().isoformat() == "2026-05-26"
    assert chunk.minutes == 5


def test_first_user_prompt_skips_resume_prompts(tmp_path):
    events = [
        {"timestamp": _ts(2026, 5, 26, 9, 41),
         "message": {"role": "user", "content": "Continue from where you left off."}},
        {"timestamp": _ts(2026, 5, 26, 9, 42),
         "message": {"role": "user", "content": "continue"}},
        {"timestamp": _ts(2026, 5, 26, 9, 43),
         "message": {"role": "user", "content": "deploy main branch to production"}},
    ]
    p = _write_transcript(tmp_path, events)
    chunk = transcripts.latest_session(p)
    assert chunk.first_prompt == "deploy main branch to production"


def test_first_user_prompt_skips_command_noise(tmp_path):
    events = [
        {"timestamp": _ts(2026, 5, 26, 9, 41),
         "message": {"role": "user", "content": "<local-command-caveat>blah</local-command-caveat>"}},
        {"timestamp": _ts(2026, 5, 26, 9, 42),
         "message": {"role": "user", "content": "<command-name>worklog:show</command-name>"}},
        {"timestamp": _ts(2026, 5, 26, 9, 43),
         "message": {"role": "user", "content": "deploy main branch to production"}},
    ]
    p = _write_transcript(tmp_path, events)
    chunk = transcripts.latest_session(p)
    assert chunk.first_prompt == "deploy main branch to production"


def test_first_user_prompt_skips_is_meta_events(tmp_path):
    """isMeta=True events are Claude-Code-injected (auto-resume prompts,
    slash-command body templates) — never user-typed."""
    events = [
        {"timestamp": _ts(2026, 5, 26, 9, 41), "isMeta": True,
         "message": {"role": "user", "content": "Continue from where you left off."}},
        {"timestamp": _ts(2026, 5, 26, 9, 41), "isMeta": True,
         "message": {"role": "user",
                     "content": "Register the **current working directory** as a worklog project so that"}},
        {"timestamp": _ts(2026, 5, 26, 9, 42), "isMeta": False,
         "message": {"role": "user", "content": "deploy main branch to prod"}},
    ]
    p = _write_transcript(tmp_path, events)
    chunk = transcripts.latest_session(p)
    assert chunk.first_prompt == "deploy main branch to prod"


def test_first_user_prompt_skips_interrupt_and_compaction_markers(tmp_path):
    events = [
        {"timestamp": _ts(2026, 5, 26, 9, 41),
         "message": {"role": "user",
                     "content": "[Request interrupted by user for tool use]"}},
        {"timestamp": _ts(2026, 5, 26, 9, 42),
         "message": {"role": "user",
                     "content": "This session is being continued from a previous conversation that ran out of context. The summary…"}},
        {"timestamp": _ts(2026, 5, 26, 9, 43),
         "message": {"role": "user",
                     "content": "<local-command-stdout>Compacted (ctrl+o to see full summary)</local-command-stdout>"}},
        {"timestamp": _ts(2026, 5, 26, 9, 44),
         "message": {"role": "user", "content": "fix OAuth redirect"}},
    ]
    p = _write_transcript(tmp_path, events)
    chunk = transcripts.latest_session(p)
    assert chunk.first_prompt == "fix OAuth redirect"


def test_first_user_prompt_handles_block_content(tmp_path):
    events = [
        {"timestamp": _ts(2026, 5, 26, 9, 41),
         "message": {"role": "user",
                     "content": [{"type": "text", "text": "look at PR#42"}]}},
    ]
    p = _write_transcript(tmp_path, events)
    chunk = transcripts.latest_session(p)
    assert chunk.first_prompt == "look at PR#42"


def test_empty_transcript_returns_none(tmp_path):
    p = tmp_path / "empty.jsonl"
    p.write_text("")
    assert transcripts.latest_session(p) is None
    assert transcripts.chunk_sessions(p) == []
