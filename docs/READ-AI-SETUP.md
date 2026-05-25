# Setting up Read.ai with Google Meet

`/worklog:sync-calendar` can enrich each meeting row with Read.ai's
**actual** start/end time and attendance — but only if Read.ai is set up
to join your meetings in the first place. This guide is the one-time
configuration outside the plugin.

> **TL;DR** — Read.ai is a separate service. The worklog plugin only
> *consumes* what Read.ai produces. Setting up Read.ai is a one-time
> dashboard click-through.

---

## 1. Sign in to Read.ai

- Go to [read.ai](https://read.ai).
- Sign in with **Google SSO** (use the same Google account whose Calendar
  / Meet you want covered).
- Free tier is fine; paid tiers add longer recap history.

## 2. Connect Google Calendar

In Read.ai:

1. **Settings → Integrations → Google Calendar**.
2. Click **Connect** → grant the requested scopes (read calendar events,
   send notifications).
3. After connecting, Read.ai shows your next few upcoming meetings as a
   sanity check.

If you use multiple Google accounts, connect each one separately under
Read.ai's "Workspaces / Accounts" section.

## 3. Set auto-join rules

**Settings → Meeting Settings (or "Notetaker rules")**. Common picks:

| Rule                            | When to use                                      |
|---------------------------------|--------------------------------------------------|
| Meetings I organise             | Conservative; bot only joins yours               |
| Internal meetings               | Recommended; matches @your-company.com attendees |
| All accepted meetings           | Broadest; bot joins anything you've said yes to  |
| External meetings only          | Sales / customer calls                           |

You can also blocklist specific calendar event titles ("Stand-up",
"1:1 — manager") if you don't want a bot in personal/sensitive meetings.

## 4. Verify the bot can actually join

The first meeting after setup is the test. Watch for:

- A new participant in the meeting tile: **"Read Notetaker"** (or similar
  named bot, depending on Read.ai version).
- A Read.ai banner in the meeting saying the meeting is being recorded.

If the bot **doesn't** join, the most common causes:

| Symptom                                   | Fix                                                            |
|-------------------------------------------|----------------------------------------------------------------|
| Bot waits in lobby forever                | Meet "Quick access" or "Host management" is blocking it       |
| Org policy: "Only invited people can join"| Ask Workspace admin to allowlist the bot's domain              |
| Calendar event has no Meet link           | Add a Meet link to the event (Calendar → Add conferencing)     |
| Meeting started ad-hoc, no calendar event | Read.ai relies on Calendar; create the event to capture it     |

## 5. The recap email — what worklog reads

Within ~5–15 min of the meeting ending, Read.ai emails a recap to you (and
optionally other invitees) from `noreply@read.ai` (or
`reports@read.ai` — varies by region). The recap contains:

| Field                  | Used by worklog?               |
|------------------------|--------------------------------|
| Meeting title          | Matched against the Calendar event title |
| Actual start time      | Becomes `Since` in the timesheet         |
| Actual end time        | Becomes `Upto`                           |
| Duration               | (computed; sanity-checked)               |
| **Participants list**  | "Did the user attend?" yes/no            |
| Action items, summary  | Not stored today; could become tasks later |

Verify the recap is reaching your Gmail with this search:

```
from:(read.ai OR noreply@read.ai OR reports@read.ai)
```

If you see recaps, you're set.

## 6. How `/worklog:sync-calendar` uses Read.ai today

1. Lists today's accepted calendar events (via Google Calendar MCP).
2. For each, searches Gmail for the matching Read.ai recap.
3. Extracts actual times + attendance from the recap.
4. Shows you a multi-select picker — pre-ticking only events Read.ai
   confirms you attended.
5. Logs whichever rows you tick.

> **Current limitation** — the Gmail MCP only exposes
> `authenticate` / `complete_authentication` today, so the recap lookup
> degrades to "calendar-scheduled times only" until either:
> - Gmail MCP gets `search_messages` / `get_message_body` tools, or
> - Read.ai ships data-read MCP tools (planned — see
>   `docs/INTEGRATIONS.md` §3), or
> - You add a `WORKLOG_READ_AI_KEY` env var that lets the plugin call
>   Read.ai's REST API directly. **Not built yet.**
>
> So at this moment `/worklog:sync-calendar` is a "calendar +
> manual-confirmation" tool. The Read.ai branch will light up
> automatically once any of the above lands.

## 7. Troubleshooting

| Problem                                          | Try                                                              |
|--------------------------------------------------|------------------------------------------------------------------|
| No recap email arrived                           | Did the bot actually join? Check the meeting recording. Then look in Spam. |
| Recap arrived but `/worklog:sync-calendar` doesn't see it | Currently expected — see "current limitation" above.  |
| Read.ai joined a sensitive meeting               | Add the event title to Read.ai's blocklist; remove the recap email |
| Multiple Google accounts, only one has the bot   | Connect each account separately in Read.ai's Workspaces section  |

## 8. Privacy notes

- Read.ai is a third-party service; granting Calendar access lets them
  read meeting metadata even before you attend.
- Anyone in the meeting can see the bot. Some participants find this
  intrusive — consider announcing "this meeting will be recorded by
  Read.ai" up front.
- Worklog never sees the meeting recording or transcript. It only reads
  the recap email metadata (and only after the planned Gmail-MCP-tools
  land).
