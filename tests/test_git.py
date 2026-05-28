"""Tests for lib.git — the git-history helper used to title sessions."""
from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta, timezone

import pytest

from lib import git


def _git(repo, *args, env=None):
    e = {"GIT_AUTHOR_NAME": "Tester", "GIT_AUTHOR_EMAIL": "t@example.com",
         "GIT_COMMITTER_NAME": "Tester", "GIT_COMMITTER_EMAIL": "t@example.com",
         **(env or {}), **os.environ}
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, env=e, check=False)


def _init_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Tester")
    return repo


def _commit(repo, msg, when: datetime):
    (repo / "f.txt").write_text(msg)
    _git(repo, "add", "f.txt")
    iso = when.astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    env = {"GIT_AUTHOR_DATE": iso, "GIT_COMMITTER_DATE": iso}
    _git(repo, "commit", "-q", "-m", msg, env=env)


# --- is_git_repo ---

def test_is_git_repo_false_for_plain_dir(tmp_path):
    d = tmp_path / "nope"
    d.mkdir()
    assert git.is_git_repo(str(d)) is False


def test_is_git_repo_true_for_repo(tmp_path):
    repo = _init_repo(tmp_path)
    assert git.is_git_repo(str(repo)) is True


# --- commit_subjects ---

def test_commit_subjects_empty_for_non_repo(tmp_path):
    assert git.commit_subjects(str(tmp_path / "missing"),
                               datetime.now(timezone.utc),
                               datetime.now(timezone.utc)) == []


def test_commit_subjects_returns_in_window(tmp_path):
    repo = _init_repo(tmp_path)
    t = datetime(2026, 5, 28, 10, 0, tzinfo=timezone.utc)
    _commit(repo, "Add new endpoint", t)
    _commit(repo, "Fix tests",         t + timedelta(minutes=5))
    _commit(repo, "Refactor handler",  t + timedelta(minutes=10))
    subs = git.commit_subjects(str(repo), t - timedelta(seconds=1),
                                          t + timedelta(minutes=11))
    assert subs == ["Add new endpoint", "Fix tests", "Refactor handler"]


def test_commit_subjects_buffer_after_minutes(tmp_path):
    repo = _init_repo(tmp_path)
    t = datetime(2026, 5, 28, 10, 0, tzinfo=timezone.utc)
    _commit(repo, "early",  t + timedelta(minutes=2))
    _commit(repo, "in",     t + timedelta(minutes=8))
    _commit(repo, "late",   t + timedelta(minutes=11))   # within +10 buffer
    _commit(repo, "outside", t + timedelta(minutes=30))   # beyond buffer
    subs = git.commit_subjects(str(repo), t, t + timedelta(minutes=5),
                                buffer_after_minutes=10)
    # Window is [10:00, 10:05] + 10-min buffer → up to 10:15. 'outside' excluded.
    assert "outside" not in subs
    assert "early" in subs
    assert "in" in subs
    assert "late" in subs


def test_commit_subjects_skips_merges(tmp_path):
    repo = _init_repo(tmp_path)
    t = datetime(2026, 5, 28, 10, 0, tzinfo=timezone.utc)
    _commit(repo, "base", t)
    _git(repo, "checkout", "-q", "-b", "feat")
    _commit(repo, "feature work", t + timedelta(minutes=2))
    _git(repo, "checkout", "-q", "main")
    iso = (t + timedelta(minutes=5)).astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    _git(repo, "merge", "--no-ff", "-m", "Merge feat", "feat",
         env={"GIT_AUTHOR_DATE": iso, "GIT_COMMITTER_DATE": iso})
    subs = git.commit_subjects(str(repo), t - timedelta(seconds=1),
                                          t + timedelta(minutes=10))
    assert "Merge feat" not in subs
    assert "feature work" in subs


# --- summarise ---

def test_summarise_handles_counts():
    assert git.summarise([]) == ""
    assert git.summarise(["one"]) == "one"
    assert git.summarise(["one", "two"]) == "one; two"
    assert git.summarise(["one", "two", "three", "four"]) \
        == "one; two (+2 more)"


def test_summarise_truncates():
    long_sub = "x" * 250
    assert len(git.summarise([long_sub], max_chars=100)) == 100
