"""Best-effort git introspection for a project's repo.

Used by the SessionEnd hook and `worklog rescan-titles` to pick session
titles from the commits authored during the session window — usually the
cleanest "what got done" signal a developer leaves behind.

All functions degrade gracefully: if `git` isn't installed, the path
isn't a repo, or the subprocess errors, they return an empty result.
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timedelta
from typing import Optional

_TIMEOUT = 5


def is_git_repo(path: str) -> bool:
    try:
        r = subprocess.run(
            ["git", "-C", path, "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=_TIMEOUT,
        )
        return r.returncode == 0 and r.stdout.strip() == "true"
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def commit_subjects(
    path: str,
    since: datetime,
    until: datetime,
    *,
    buffer_after_minutes: int = 10,
    author_email: Optional[str] = None,
    limit: int = 10,
) -> list[str]:
    """Subjects of commits in roughly [since, until + buffer] under path.

    The buffer absorbs "session ended, then commit-pushed a minute later"
    cases. When `author_email` is given, restricts to that author.
    Returns at most `limit` subjects, oldest-first."""
    if not is_git_repo(path):
        return []

    since_iso = since.astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    until_iso = (until + timedelta(minutes=buffer_after_minutes)) \
        .astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")

    cmd = [
        "git", "-C", path, "log",
        "--all",
        "--no-merges",
        "--reverse",                       # oldest-first
        f"--since={since_iso}",
        f"--until={until_iso}",
        "--format=%s",
        f"--max-count={limit}",
    ]
    if author_email:
        cmd.append(f"--author={author_email}")

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=_TIMEOUT)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return []
    if r.returncode != 0:
        return []
    return [s for s in r.stdout.splitlines() if s.strip()]


def summarise(subjects: list[str], max_chars: int = 200) -> str:
    """Compact one-line summary from a list of commit subjects."""
    if not subjects:
        return ""
    if len(subjects) == 1:
        return subjects[0][:max_chars]
    if len(subjects) == 2:
        s = f"{subjects[0]}; {subjects[1]}"
        return s[:max_chars]
    extra = len(subjects) - 2
    s = f"{subjects[0]}; {subjects[1]} (+{extra} more)"
    return s[:max_chars]
