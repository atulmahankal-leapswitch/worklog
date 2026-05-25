"""Shared test fixtures.

Each test runs against a fresh isolated SQLite DB in a temp dir. We do this
by setting WORKLOG_HOME to a per-test directory before any `lib.db` call.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKLOG_HOME", str(tmp_path))
    from lib import db  # noqa: WPS433 — re-import after env var
    db.init()
    yield tmp_path
