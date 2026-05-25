---
description: Add a worklog entry (task / time / project) from natural language
argument-hint: "free-text entry (task, time slot, or 'register project X at /path')"
---

Add an entry to the worklog database based on `$ARGUMENTS`.

## How to interpret the input

The user will describe one of three kinds of entries. Pick the kind first.

### Kind = `project` — register a project (for auto-logging Claude sessions)

Trigger phrases: "register project", "add project", "track this folder",
"this is project X", or any input mentioning a folder path next to a name.

Extract:
- **Name** (required) — short project name, e.g. `LeapBuilder`.
- **Path** (recommended) — absolute path to the project root. If the user
  says "this folder" / "here", use the current working directory.
- **Coordinator**, **GitRepo** — optional.

Then run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog add project \
  --name "<name>" --path "<absolute path>" \
  [--coordinator "<name>"] [--repo "<url>"] [--no-auto-log]
```

Registering a project with a path is what enables the **Automatic Claude
Code session logging** for that directory (and its subdirectories). Without
registration, sessions in that path are not auto-logged.

### Kind = `time` — a timesheet entry (start/end given)

Triggered when the input contains a time range like `10:00-11:30` or
`14:00 to 15:00`.

Extract:
- **Date** — `today`/`yesterday`/`YYYY-MM-DD` if mentioned, else today.
- **Project** (required) — match casing to existing projects when possible
  (`python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog projects --format json`).
- **Task** (required) — short description.
- **Since / Upto** — `HH:MM` (required).
- **Reference** — PR/issue/URL if mentioned.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog add time \
  --date <date> --project "<project>" --task "<task>" \
  --since <HH:MM> --upto <HH:MM> --ref "<ref>"
```

### Kind = `task` — a task entry (default)

Extract:
- **Date**, **Project** (required), **Task** (required).
- **Reference**, **Status** (`open`|`in_progress`|`done`|`blocked`, default
  `open`), **Remark**.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog add task \
  --date <date> --project "<project>" --task "<task>" \
  --ref "<ref>" --status <status> --remark "<remark>"
```

## After running

Echo a one-line confirmation of what was stored. If any required field was
missing, ask one short clarifying question before running anything.
