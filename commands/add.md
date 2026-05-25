---
description: Add a manual timesheet entry — format <project>|<text>|<HH:MM>-<HH:MM>
argument-hint: "<project>|<task text>|<HH:MM>-<HH:MM> [|YYYY-MM-DD]"
---

Add a manual timesheet entry from `$ARGUMENTS`.

## Input format

Pipe-separated fields:

```
<project> | <task text> | <HH:MM>-<HH:MM> [ | YYYY-MM-DD | today | yesterday ]
```

- **project** — short project name (e.g. `LeapBuilder`).
- **task text** — what was done.
- **time range** — start and end as `HH:MM-HH:MM`.
- **date** — optional 4th field; defaults to `today`. Accepts
  `today`, `yesterday`, or `YYYY-MM-DD`.

### Examples

```
/worklog:add LeapBuilder | Fix login redirect | 10:00-11:30
/worklog:add Hostbill | KYC investigation | 14:00-15:45 | yesterday
/worklog:add Worklog | Plugin docs | 09:15-10:00 | 2026-05-24
```

## Steps

1. Split `$ARGUMENTS` on `|` and strip each field.
2. Validate the time range matches `HH:MM-HH:MM`. If not, ask the user
   for the correct format and stop.
3. Parse `<since>` and `<upto>` from the time range.
4. Date = the 4th field if present, else `today`.
5. Run:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog add time \
     --date "<date>" --project "<project>" --task "<task text>" \
     --since "<HH:MM>" --upto "<HH:MM>"
   ```

6. Echo the CLI's one-line confirmation (which includes the new row's id
   and computed duration).
