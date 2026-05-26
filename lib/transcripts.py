"""Helpers for reading Claude Code session transcripts (JSONL).

Used by both the SessionEnd hook (`hooks/log_session.py`) and the
`worklog backfill` CLI subcommand. A Claude Code transcript can be
resumed across days, so the whole file is NOT one session — we have to
chunk it by idle gaps.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional


SESSION_GAP_MINUTES = 30
"""Idle gap that separates two sessions inside one JSONL transcript."""

_NOISE_PREFIXES = (
    "<local-command-caveat>",
    "<command-name>",
    "<command-message>",
    "<system-reminder>",
    "Caveat:",
)


def encoded_project_dir(abs_path: str) -> str:
    """Map an absolute path to the Claude Code projects-dir name.

    Claude Code stores each project's transcripts under
    `~/.claude/projects/<encoded>` where `<encoded>` is the absolute path
    with `/` and ` ` replaced by `-`.

        /home/atul/Documents/Projects/Hostbill Modules/modules/Hosting/quickpost
        → -home-atul-Documents-Projects-Hostbill-Modules-modules-Hosting-quickpost
    """
    return abs_path.replace("/", "-").replace(" ", "-")


def transcript_dir(project_path: str) -> Path:
    """Directory holding `*.jsonl` transcripts for a registered project."""
    return Path.home() / ".claude" / "projects" / encoded_project_dir(project_path)


def read_transcript(path: str | Path) -> list[dict]:
    events: list[dict] = []
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


def get_timestamps(events: Iterable[dict]) -> list[datetime]:
    stamps: list[datetime] = []
    for e in events:
        t = e.get("timestamp")
        if not t:
            continue
        try:
            stamps.append(datetime.fromisoformat(t.replace("Z", "+00:00")))
        except ValueError:
            continue
    return stamps


def _is_noise(text: str) -> bool:
    return text.lstrip().startswith(_NOISE_PREFIXES)


def _event_text(e: dict) -> str:
    msg = e.get("message") or {}
    if msg.get("role") != "user":
        return ""
    c = msg.get("content")
    if isinstance(c, str):
        return c.strip()
    if isinstance(c, list):
        for x in c:
            if isinstance(x, dict) and x.get("type") == "text":
                return (x.get("text") or "").strip()
    return ""


def first_user_prompt(events: Iterable[dict]) -> str:
    """First non-noise user prompt from the events (truncated to 200 chars).

    Skips command caveats, slash-command markers, and system reminders so
    the task title reflects what the user actually typed."""
    for e in events:
        text = _event_text(e)
        if not text or _is_noise(text):
            continue
        return text.splitlines()[0][:200]
    return ""


@dataclass
class SessionChunk:
    start: datetime
    end: datetime
    events: list[dict]
    transcript: Path

    @property
    def minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)

    @property
    def first_prompt(self) -> str:
        return first_user_prompt(self.events) or "Claude Code session"


def chunk_sessions(transcript_path: str | Path,
                   gap_minutes: int = SESSION_GAP_MINUTES) -> list[SessionChunk]:
    """Split a transcript into contiguous-session chunks separated by idle gaps."""
    p = Path(transcript_path)
    events = read_transcript(p)
    pairs: list[tuple[datetime, dict]] = []
    for e in events:
        t = e.get("timestamp")
        if not t:
            continue
        try:
            dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
        except ValueError:
            continue
        pairs.append((dt, e))
    if not pairs:
        return []
    pairs.sort(key=lambda x: x[0])

    gap = timedelta(minutes=gap_minutes)
    chunks: list[SessionChunk] = []
    cur: list[tuple[datetime, dict]] = [pairs[0]]
    for prev, curp in zip(pairs, pairs[1:]):
        if (curp[0] - prev[0]) > gap:
            chunks.append(SessionChunk(
                start=cur[0][0], end=cur[-1][0],
                events=[e for _, e in cur], transcript=p,
            ))
            cur = [curp]
        else:
            cur.append(curp)
    chunks.append(SessionChunk(
        start=cur[0][0], end=cur[-1][0],
        events=[e for _, e in cur], transcript=p,
    ))
    return chunks


def latest_session(transcript_path: str | Path,
                   gap_minutes: int = SESSION_GAP_MINUTES) -> Optional[SessionChunk]:
    """The most recent contiguous chunk in the transcript (or None if empty)."""
    chunks = chunk_sessions(transcript_path, gap_minutes=gap_minutes)
    return chunks[-1] if chunks else None
