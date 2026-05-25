from datetime import date

from lib import db


def test_add_task_creates_project_and_row():
    db.add_task(project="LeapBuilder", task="fix login")
    proj = db.get_project("LeapBuilder")
    assert proj is not None
    rows = db.list_tasks(date.today().isoformat())
    assert len(rows) == 1
    assert rows[0]["task"] == "fix login"
    assert rows[0]["status"] == "open"


def test_add_task_status_done_sets_status_date():
    db.add_task(project="P", task="t", status="done", date="2026-01-01")
    rows = db.list_tasks("2026-01-01")
    assert rows[0]["status_date"] == "2026-01-01"


def test_add_timesheet_dedupes_on_date_since_task():
    kwargs = dict(date="2026-01-01", since="10:00", upto="11:00",
                  minutes=60, project="P", task="t")
    first = db.add_timesheet(**kwargs)
    second = db.add_timesheet(**kwargs)
    assert first == second
    assert len(db.list_timesheet("2026-01-01")) == 1


def test_find_project_by_path_matches_subdir(tmp_path):
    root = tmp_path / "myproj"
    root.mkdir()
    db.add_project(name="MyProj", path=str(root))
    sub = root / "src" / "deep"
    sub.mkdir(parents=True)
    match = db.find_project_by_path(str(sub))
    assert match is not None
    assert match["name"] == "MyProj"


def test_find_project_by_path_no_match(tmp_path):
    assert db.find_project_by_path(str(tmp_path / "unregistered")) is None


def test_find_project_by_path_longest_prefix_wins(tmp_path):
    outer = tmp_path / "outer"
    inner = outer / "inner"
    inner.mkdir(parents=True)
    db.add_project(name="Outer", path=str(outer))
    db.add_project(name="Inner", path=str(inner))
    match = db.find_project_by_path(str(inner / "deeper"))
    assert match["name"] == "Inner"


def test_set_project_auto_log_by_path_toggles(tmp_path):
    root = tmp_path / "p"
    root.mkdir()
    db.add_project(name="P", path=str(root))
    row = db.set_project_auto_log_by_path(str(root), enabled=False)
    assert row["auto_log"] == 0
    row = db.set_project_auto_log_by_path(str(root), enabled=True)
    assert row["auto_log"] == 1


def test_set_project_auto_log_by_path_no_match_returns_none(tmp_path):
    assert db.set_project_auto_log_by_path(str(tmp_path), enabled=False) is None


def test_delete_timesheet_and_task():
    tsid = db.add_timesheet(date="2026-01-01", since="09:00", upto="10:00",
                             minutes=60, project="P", task="ts")
    tid = db.add_task(project="P", task="t")
    assert db.delete_timesheet(tsid) is True
    assert db.delete_timesheet(99999) is False
    assert db.delete_task(tid) is True
    assert db.delete_task(99999) is False


def test_list_projects_with_status_shows_last_active(tmp_path):
    root = tmp_path / "p"
    root.mkdir()
    db.add_project(name="P", path=str(root))
    db.add_timesheet(date="2026-03-15", since="09:00", upto="10:00",
                     minutes=60, project="P", task="t")
    rows = db.list_projects_with_status()
    assert len(rows) == 1
    assert rows[0]["last_active"] == "2026-03-15"
    assert rows[0]["auto_log"] == 1
