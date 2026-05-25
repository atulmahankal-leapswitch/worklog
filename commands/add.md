---
description: Add a worklog task or time entry from natural language
argument-hint: "free-text entry (e.g. \"LeapBuilder: fix login redirect, PR#42, status done\")"
---

Add an entry to the worklog database based on `$ARGUMENTS`.

## How to interpret the input

The user will describe an entry in free form. Extract these fields:

- **Kind** — `task` (default) or `time` (if a start/end time is given).
- **Date** — `today`/`yesterday`/`YYYY-MM-DD` if mentioned, else today.
- **Project** — the project/product name (required). If unclear, ask the
  user. Match casing to existing projects in the DB when possible — get the
  list via:
  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog show today --format json
  ```
  (the JSON output includes project names).
- **Task** — short description of the work (required).
- **Reference** — PR/issue/URL if mentioned.
- **Status** — `open` | `in_progress` | `done` | `blocked`. Default `open`.
- **Remark** — any extra note.
- **Since/Upto** — only for `time` kind, in `HH:MM`.

If any required field is missing, ask one short clarifying question.

## Then run

For a task:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog add task \
  --date <date> --project "<project>" --task "<task>" \
  --ref "<ref>" --status <status> --remark "<remark>"
```

For a time entry:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog add time \
  --date <date> --project "<project>" --task "<task>" \
  --since <HH:MM> --upto <HH:MM> --ref "<ref>"
```

After it succeeds, confirm with a one-line summary echoing what was stored.
