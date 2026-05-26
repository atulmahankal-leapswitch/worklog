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
    path            TEXT,
    coordinator     TEXT,
    git_repo        TEXT,
    clickup_list_id TEXT,
    auto_log        INTEGER DEFAULT 1,
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


def _migrate(c: sqlite3.Connection):
    """Idempotent ALTER TABLE migrations for older DBs."""
    cols = {r["name"] for r in c.execute("PRAGMA table_info(projects)")}
    if "path" not in cols:
        c.execute("ALTER TABLE projects ADD COLUMN path TEXT")
    if "auto_log" not in cols:
        c.execute("ALTER TABLE projects ADD COLUMN auto_log INTEGER DEFAULT 1")
    c.execute("CREATE INDEX IF NOT EXISTS idx_projects_path ON projects(path)")

    task_cols = {r["name"] for r in c.execute("PRAGMA table_info(tasks)")}
    if "slack_message_ts" not in task_cols:
        c.execute("ALTER TABLE tasks ADD COLUMN slack_message_ts TEXT")
    if "slack_last_notified" not in task_cols:
        c.execute("ALTER TABLE tasks ADD COLUMN slack_last_notified TEXT")
    c.execute("CREATE INDEX IF NOT EXISTS idx_tasks_reference ON tasks(reference)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_tasks_source ON tasks(source)")

    if "clickup_space_id" not in cols:
        c.execute("ALTER TABLE projects ADD COLUMN clickup_space_id TEXT")
    if "clickup_workspace_id" not in cols:
        c.execute("ALTER TABLE projects ADD COLUMN clickup_workspace_id TEXT")
    if "clickup_space_name" not in cols:
        c.execute("ALTER TABLE projects ADD COLUMN clickup_space_name TEXT")
    if "clickup_folder_id" not in cols:
        c.execute("ALTER TABLE projects ADD COLUMN clickup_folder_id TEXT")
    if "clickup_folder_name" not in cols:
        c.execute("ALTER TABLE projects ADD COLUMN clickup_folder_name TEXT")
    if "clickup_list_name" not in cols:
        c.execute("ALTER TABLE projects ADD COLUMN clickup_list_name TEXT")


def init():
    with connect() as c:
        c.executescript(SCHEMA)
        _migrate(c)


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


_CLICKUP_COLUMN = {
    "workspace_id":  "clickup_workspace_id",
    "space_id":      "clickup_space_id",
    "space_name":    "clickup_space_name",
    "folder_id":     "clickup_folder_id",
    "folder_name":   "clickup_folder_name",
    "list_id":       "clickup_list_id",
    "list_name":     "clickup_list_name",
}


def set_project_clickup_mapping(project: str, **fields):
    """Set any of: workspace_id, space_id, space_name, folder_id,
    folder_name, list_id, list_name. Only fields that are not None get
    written; pass an empty string to clear one explicitly."""
    payload = {k: v for k, v in fields.items() if v is not None}
    if not payload:
        return
    unknown = set(payload) - set(_CLICKUP_COLUMN)
    if unknown:
        raise ValueError(f"unknown clickup mapping fields: {sorted(unknown)}")
    cols = [_CLICKUP_COLUMN[k] for k in payload]
    vals = [(v or None) for v in payload.values()]
    with connect() as c:
        pid = get_or_create_project(project, conn=c)
        c.execute(
            f"UPDATE projects SET {', '.join(f'{col}=?' for col in cols)} "
            f"WHERE id=?",
            (*vals, pid),
        )


def get_project(name: str) -> Optional[sqlite3.Row]:
    with connect() as c:
        return c.execute("SELECT * FROM projects WHERE name=?", (name,)).fetchone()


def _abs(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    return str(Path(path).expanduser().resolve())


def add_project(
    *,
    name: str,
    path: Optional[str] = None,
    coordinator: str = "",
    git_repo: str = "",
    auto_log: bool = True,
) -> int:
    """Register or update a project. Path is treated as the unique key — if a
    project already exists at this absolute path, it's updated in place
    (renamed if `name` differs) rather than a duplicate row being created.

    If the path is new but the name is already taken by another project,
    falls back to updating by name (lets the user move a project to a new
    path). Conflicts (path and name resolve to *different* rows) raise."""
    abs_path = _abs(path)
    with connect() as c:
        path_match = None
        if abs_path:
            path_match = c.execute(
                "SELECT id, name FROM projects WHERE path = ?", (abs_path,)
            ).fetchone()
        name_match = c.execute(
            "SELECT id, name, path FROM projects WHERE name = ?", (name,)
        ).fetchone()

        if path_match and name_match and path_match["id"] != name_match["id"]:
            raise ValueError(
                f"conflict: path '{abs_path}' is already registered under "
                f"project '{path_match['name']}' (#{path_match['id']}), and "
                f"name '{name}' is already used by another project "
                f"(#{name_match['id']} at '{name_match['path']}'). Remove "
                f"one of them first with `worklog project remove --id <id>`."
            )

        existing = path_match or name_match
        if existing:
            c.execute(
                """UPDATE projects
                   SET name        = ?,
                       path        = COALESCE(?, path),
                       coordinator = COALESCE(NULLIF(?, ''), coordinator),
                       git_repo    = COALESCE(NULLIF(?, ''), git_repo),
                       auto_log    = ?
                   WHERE id = ?""",
                (name, abs_path, coordinator, git_repo,
                 1 if auto_log else 0, existing["id"]),
            )
            return existing["id"]
        cur = c.execute(
            """INSERT INTO projects(name, path, coordinator, git_repo, auto_log)
               VALUES (?, ?, ?, ?, ?)""",
            (name, abs_path, coordinator, git_repo, 1 if auto_log else 0),
        )
        return cur.lastrowid


def get_project_by_path(abs_path: str):
    """Exact path match. None if not registered."""
    with connect() as c:
        return c.execute(
            "SELECT * FROM projects WHERE path = ?", (_abs(abs_path),)
        ).fetchone()


def delete_project(project_id: int) -> str:
    """Returns one of: 'deleted', 'not_found', 'in_use'."""
    with connect() as c:
        if not c.execute(
            "SELECT 1 FROM projects WHERE id = ?", (project_id,)
        ).fetchone():
            return "not_found"
        refs = c.execute(
            "SELECT (SELECT COUNT(*) FROM tasks WHERE project_id = ?) "
            "       + (SELECT COUNT(*) FROM timesheet WHERE project_id = ?)",
            (project_id, project_id),
        ).fetchone()[0]
        if refs:
            return "in_use"
        c.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        return "deleted"


def find_project_by_path(cwd: str) -> Optional[sqlite3.Row]:
    """Find a registered project whose path equals or is a parent of cwd.
    Longest-prefix match wins so nested registrations work."""
    target = Path(_abs(cwd))
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM projects WHERE path IS NOT NULL AND path != ''"
        ).fetchall()
    best: Optional[sqlite3.Row] = None
    best_len = -1
    for r in rows:
        try:
            p = Path(r["path"])
        except Exception:
            continue
        if target == p or p in target.parents:
            if len(str(p)) > best_len:
                best = r
                best_len = len(str(p))
    return best


def list_projects_with_status() -> list[sqlite3.Row]:
    """Projects with their last activity date (max of tasks.date and timesheet.date)."""
    with connect() as c:
        return c.execute(
            """SELECT p.id, p.name, p.path, p.coordinator, p.git_repo,
                      p.auto_log,
                      p.clickup_workspace_id,
                      p.clickup_space_id, p.clickup_space_name,
                      p.clickup_folder_id, p.clickup_folder_name,
                      p.clickup_list_id, p.clickup_list_name,
                      p.created_at,
                      (
                        SELECT MAX(d) FROM (
                          SELECT MAX(date) AS d FROM tasks      WHERE project_id = p.id
                          UNION ALL
                          SELECT MAX(date) AS d FROM timesheet  WHERE project_id = p.id
                        )
                      ) AS last_active
               FROM projects p
               ORDER BY p.name"""
        ).fetchall()


def set_project_auto_log(name: str, enabled: bool):
    with connect() as c:
        c.execute("UPDATE projects SET auto_log=? WHERE name=?",
                  (1 if enabled else 0, name))


def set_project_auto_log_by_path(path: str, enabled: bool) -> Optional[sqlite3.Row]:
    """Find the registered project covering `path` and toggle its auto_log.
    Returns the matched project row (after the update) or None if no match."""
    match = find_project_by_path(path)
    if not match:
        return None
    with connect() as c:
        c.execute("UPDATE projects SET auto_log=? WHERE id=?",
                  (1 if enabled else 0, match["id"]))
        return c.execute("SELECT * FROM projects WHERE id=?", (match["id"],)).fetchone()


def delete_timesheet(ts_id: int) -> bool:
    with connect() as c:
        cur = c.execute("DELETE FROM timesheet WHERE id=?", (ts_id,))
        return cur.rowcount > 0


def update_timesheet_task(ts_id: int, task: str) -> bool:
    with connect() as c:
        cur = c.execute("UPDATE timesheet SET task=? WHERE id=?", (task, ts_id))
        return cur.rowcount > 0


def update_task_text(task_id: int, task: str) -> bool:
    with connect() as c:
        cur = c.execute(
            f"UPDATE tasks SET task=?, updated_at={_NOW_MS} WHERE id=?",
            (task, task_id),
        )
        return cur.rowcount > 0


def delete_task(task_id: int) -> bool:
    with connect() as c:
        cur = c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        return cur.rowcount > 0


def list_tasks_by_source(source: str) -> list[sqlite3.Row]:
    """All tasks (any date) matching the given source tag."""
    with connect() as c:
        return c.execute(
            """SELECT t.*, p.name AS project
               FROM tasks t LEFT JOIN projects p ON p.id = t.project_id
               WHERE t.source = ?
               ORDER BY t.id""",
            (source,),
        ).fetchall()


def get_task_by_reference(reference: str) -> Optional[sqlite3.Row]:
    with connect() as c:
        return c.execute(
            "SELECT * FROM tasks WHERE reference = ?", (reference,)
        ).fetchone()


_NOW_MS = "strftime('%Y-%m-%d %H:%M:%f', 'now')"
# Sub-second precision so the (updated_at, slack_last_notified) ordering
# survives rapid sequences in tests and in real-world quick edits.


def update_task_status(task_id: int, status: str, remark: Optional[str] = None):
    """Update status (and optionally remark). status_date set to today."""
    today = _date.today().isoformat()
    with connect() as c:
        if remark is not None:
            c.execute(
                f"""UPDATE tasks
                    SET status=?, status_date=?, remark=?, updated_at={_NOW_MS}
                    WHERE id=?""",
                (status, today, remark, task_id),
            )
        else:
            c.execute(
                f"""UPDATE tasks
                    SET status=?, status_date=?, updated_at={_NOW_MS}
                    WHERE id=?""",
                (status, today, task_id),
            )


def set_task_slack_notified(task_id: int, message_ts: str):
    """Record that this task's status was relayed to Slack at message_ts.

    Deliberately does NOT touch updated_at so the queue logic
    (`updated_at > slack_last_notified`) only re-fires when the *user*
    changes status, not the notification itself."""
    with connect() as c:
        c.execute(
            f"""UPDATE tasks
                SET slack_message_ts=?, slack_last_notified={_NOW_MS}
                WHERE id=?""",
            (message_ts, task_id),
        )


def list_tasks_needing_slack_update() -> list[sqlite3.Row]:
    """Slack-sourced tasks whose status has progressed past 'open' AND either
    have never been notified, or have been updated since the last notification.

    Newly-imported open tasks are deliberately excluded — Slack only hears
    back about *status changes*, not the import itself."""
    with connect() as c:
        return c.execute(
            """SELECT t.*, p.name AS project
               FROM tasks t LEFT JOIN projects p ON p.id = t.project_id
               WHERE t.source = 'slack'
                 AND t.reference IS NOT NULL AND t.reference != ''
                 AND t.status != 'open'
                 AND (
                       t.slack_last_notified IS NULL
                       OR t.updated_at > t.slack_last_notified
                     )
               ORDER BY t.id"""
        ).fetchall()
