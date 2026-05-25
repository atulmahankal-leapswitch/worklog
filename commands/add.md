---
description: Add a manual timesheet entry — prompts for missing fields, or accepts <project>|<text>|<HH:MM>-<HH:MM>[|date]
argument-hint: "(empty for interactive)  OR  <project>|<task>|<HH:MM>-<HH:MM> [|date]"
---

Add a timesheet entry. Works in two modes:

| Input               | What happens                                                  |
|---------------------|---------------------------------------------------------------|
| Empty `$ARGUMENTS`  | Interactively ask the user for each field                     |
| Complete pipe form  | Parse and run immediately, no prompts                         |
| Partial input       | Parse what's there, ask only for what's missing               |

## Pipe format (when provided)

```
<project> | <task text> | <HH:MM>-<HH:MM> [ | YYYY-MM-DD | today | yesterday ]
```

## Fields

| Field    | Required | Default     |
|----------|----------|-------------|
| project  | yes      | —           |
| task     | yes      | —           |
| since    | yes      | —           |
| upto     | yes      | —           |
| date     | no       | today       |

## Steps

1. **Parse `$ARGUMENTS`** by splitting on `|` and stripping. Map fields by
   position: `project`, `task`, time range, date.
2. **Resolve missing fields by asking the user**, one question at a time:
   - "Which project?" — if you can show existing options, fetch them first
     with:
     ```bash
     python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog projects --format json
     ```
     Then list the names so the user can pick one or type a new name.
   - "What did you work on?"
   - "What time range? (HH:MM-HH:MM)"
   - Don't ask for date — assume today unless the user mentioned one.
3. **Validate** the time range matches `HH:MM-HH:MM`. If parse fails,
   re-ask just for the time.
4. **Run** once you have all four fields:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog add time \
     --date "<date>" --project "<project>" --task "<task>" \
     --since "<HH:MM>" --upto "<HH:MM>"
   ```

5. Echo the CLI's one-line confirmation.

## Examples

```
/worklog:add                                        # full interactive
/worklog:add LeapBuilder                            # asks: task? time?
/worklog:add LeapBuilder | Fix login redirect       # asks: time?
/worklog:add LeapBuilder | Fix login | 10:00-11:30  # runs immediately
/worklog:add LeapBuilder | Fix login | 10:00-11:30 | yesterday
```
