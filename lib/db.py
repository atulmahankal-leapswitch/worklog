"""SQLite storage for the worklog plugin.

Database location: $WORKLOG_HOME/worklog.db (default: ~/.worklog/worklog.db).

Schema:
  projects   — list of projects/products
  tasks      — work items with status, used by /worklog:show, :add, :push
  timesheet  — time entries (auto-logged sessions, calendar meetings, manual)
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import date as _date
from pathlib import Path
from typing import Iterable, Optional


def _home() -> Path:
    base = os.environ.get("WORKLOG_HOME")
    return Path(base) if base else Path.home() / ".worklog"


def db_path() -> Path:
    p = _home()
    p.mkdir(parents=True, exist_ok=True)
    return p / "worklog.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    coordinator     TEXT,
    git_repo        TEXT,
    clickup_list_id TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tasks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT NOT NULL,
    project_id      INTEGER REFERENCES projects(id),
    task            TEXT NOT NULL,
    reference       TEXT,
    assigned        TEXT,
    status          TEXT DEFAULT 'open',
    status_date     TEXT,
    remark          TEXT,
    source          TEXT DEFAULT 'manual',
    clickup_task_id TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tasks_date   ON tasks(date);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

CREATE TABLE IF NOT EXISTS timesheet (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL,
    since       TEXT NOT NULL,
    upto        TEXT NOT NULL,
    minutes     INTEGER NOT NULL,
    project_id  INTEGER REFERENCES projects(id),
    task        TEXT,
    ref         TEXT,
    source      TEXT DEFAULT 'manual',
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_timesheet_date ON timesheet(date);
"""


@contextmanager
def connect():
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init():
    with connect() as c:
        c.executescript(SCHEMA)


def get_or_create_project(name: str, conn: Optional[sqlite3.Connection] = None) -> int:
    def _do(c: sqlite3.Connection) -> int:
        row = c.execute("SELECT id FROM projects WHERE name = ?", (name,)).fetchone()
        if row:
            return row["id"]
        cur = c.execute("INSERT INTO projects(name) VALUES (?)", (name,))
        return cur.lastrowid

    if conn is not None:
        return _do(conn)
    with connect() as c:
        return _do(c)


def add_task(
    *,
    project: str,
    task: str,
    date: Optional[str] = None,
    reference: str = "",
    assigned: str = "",
    status: str = "open",
    remark: str = "",
    source: str = "manual",
) -> int:
    date = date or _date.today().isoformat()
    with connect() as c:
        pid = get_or_create_project(project, conn=c)
        cur = c.execute(
            """INSERT INTO tasks(date, project_id, task, reference, assigned,
                                 status, status_date, remark, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (date, pid, task, reference, assigned, status,
             date if status != "open" else None, remark, source),
        )
        return cur.lastrowid


def list_tasks(date: str) -> list[sqlite3.Row]:
    """Tasks where date == given OR status_date == given (i.e. recorded or closed on that day)."""
    with connect() as c:
        return c.execute(
            """SELECT t.*, p.name AS project, p.clickup_list_id
               FROM tasks t LEFT JOIN projects p ON p.id = t.project_id
               WHERE t.date = ? OR t.status_date = ?
               ORDER BY t.created_at""",
            (date, date),
        ).fetchall()


def list_timesheet(date: str) -> list[sqlite3.Row]:
    with connect() as c:
        return c.execute(
            """SELECT ts.*, p.name AS project
               FROM timesheet ts LEFT JOIN projects p ON p.id = ts.project_id
               WHERE ts.date = ?
               ORDER BY ts.since""",
            (date,),
        ).fetchall()


def add_timesheet(
    *,
    date: str,
    since: str,
    upto: str,
    minutes: int,
    project: str,
    task: str,
    ref: str = "",
    source: str = "manual",
) -> int:
    with connect() as c:
        pid = get_or_create_project(project, conn=c)
        # dedupe: skip if same (date, since, task)
        existing = c.execute(
            "SELECT id FROM timesheet WHERE date=? AND since=? AND task=?",
            (date, since, task),
        ).fetchone()
        if existing:
            return existing["id"]
        cur = c.execute(
            """INSERT INTO timesheet(date, since, upto, minutes, project_id, task, ref, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (date, since, upto, minutes, pid, task, ref, source),
        )
        return cur.lastrowid


def update_task_clickup_id(task_id: int, clickup_task_id: str):
    with connect() as c:
        c.execute(
            "UPDATE tasks SET clickup_task_id=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (clickup_task_id, task_id),
        )


def set_project_clickup_list(project: str, list_id: str):
    with connect() as c:
        pid = get_or_create_project(project, conn=c)
        c.execute("UPDATE projects SET clickup_list_id=? WHERE id=?", (list_id, pid))


def get_project(name: str) -> Optional[sqlite3.Row]:
    with connect() as c:
        return c.execute("SELECT * FROM projects WHERE name=?", (name,)).fetchone()
