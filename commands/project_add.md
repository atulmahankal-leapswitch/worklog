---
description: Register the current working directory as a project for automatic Claude Code session logging — also offers to map a ClickUp Space (re-runnable to reconfigure)
argument-hint: "[project name]   (optional — defaults to the cwd folder name)"
---

Register the **current working directory** as a worklog project so that
every Claude Code session that ends in this directory (or any
subdirectory) gets auto-logged to the timesheet. Also offers to map the
project to a ClickUp Space (and optionally a default List) so
`/worklog:push` knows where new tasks should land.

Safe to re-run on an existing project — use it to update the ClickUp
mapping without re-registering.

## Steps

### 1. Resolve cwd and look up any existing project

```bash
PWD_NOW="$(pwd)"
DEFAULT_NAME="$(basename "$PWD_NOW")"
```

Fetch all projects as JSON and search for one whose `path` equals
`$PWD_NOW` (paths are stored absolute):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog projects --format json
```

If a row matches, this is a **reconfigure**: capture its current
`name`, `clickup_workspace_id`, `clickup_space_name`,
`clickup_folder_name`, `clickup_list_name`, and `auto_log` so you can
surface them in the next steps. Otherwise treat as a fresh registration.

### 2. Pick the project name

- If `$ARGUMENTS` is non-empty → use it as the new name.
- Else if a row already exists for this path → ask:
  "Keep current name **`<existing_name>`**?  (Enter to keep, or type a
  new name.)"  Blank = keep existing.
- Else → ask: "Register this folder as project
  **`<DEFAULT_NAME>`**? (Enter to accept, or type a different name.)"

### 3. Register (or update) the project

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog project register \
  --path "$PWD_NOW" --name "<chosen name>"
```

`project register` uses **path as the unique key**, so re-running on an
already-registered folder just updates the existing row (renaming it if
you typed a new name). It never creates a duplicate.

Echo the CLI's confirmation.

### 4. Show current ClickUp mapping (if any)

You already captured this in step 1. Display it back to the user, e.g.:

```
Current ClickUp mapping: Core Team / Application Developement / CloudPe Admin
```

…or "Not mapped yet." if all clickup fields are empty.

### 5. Ask whether to (re)map ClickUp

Use `AskUserQuestion` (single-select):

```
question: "Map this project to a ClickUp Space?  (current: <current or 'none'>)"
options:
  - "Yes — pick a Space (and optionally a List)"
  - "No — leave as-is"          (skip step 6 entirely)
  - "Clear the current mapping" (only if a mapping exists)
```

If the user picks **No**, skip to step 7. If **Clear**, run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog project set-clickup \
  --name "<name>" \
  --workspace-id "" \
  --space-id "" --space-name "" \
  --folder-id "" --folder-name "" \
  --list-id "" --list-name ""
```

…and skip to step 7.

### 6. Drive the ClickUp pickers

#### 6a. Pick a Space

```
mcp__claude_ai_ClickUp__clickup_get_workspace_hierarchy
  max_depth: 0
```

The response carries `hierarchy.root.id` — that's the **workspace id**.
Save it as `WORKSPACE_ID`; we'll need it to build clickable Space/List
URLs in `/worklog:projects`.

Build an `AskUserQuestion` from the returned Spaces (≤ 4 per question;
batch if needed). Each option's `description` should include the Space
id so the user can sanity-check.

Store the user's chosen Space id as `SPACE_ID` **and its name as
`SPACE_NAME`** (lift it from the same node in the hierarchy). The name is
what `/worklog:projects` will display.

#### 6b. (Optional) Drill into a default List

Ask: "Pin a default List for new tasks under this Space?  
(`Yes — pick a List` / `No — keep Space-only, ask per task at push time`)"

If **No**, set the mapping with just the Space:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog project set-clickup \
  --name "<name>" --workspace-id "$WORKSPACE_ID" \
  --space-id "$SPACE_ID" --space-name "$SPACE_NAME" \
  --folder-id "" --folder-name "" \
  --list-id "" --list-name ""
```

If **Yes**, fetch Folders + Lists in that Space:

```
mcp__claude_ai_ClickUp__clickup_get_workspace_hierarchy
  space_ids: ["$SPACE_ID"]
  max_depth: 2
```

Present every reachable List as an `AskUserQuestion` (label
`<folder name> / <list name>` so the user sees the hierarchy). When the
user picks one, also capture its parent **folder id + name** (if the
List lives directly under the Space with no Folder, leave folder fields
empty) and the **list name** itself. Save:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog project set-clickup \
  --name "<name>" --workspace-id "$WORKSPACE_ID" \
  --space-id "$SPACE_ID" --space-name "$SPACE_NAME" \
  --folder-id "$FOLDER_ID" --folder-name "$FOLDER_NAME" \
  --list-id "$LIST_ID" --list-name "$LIST_NAME"
```

(Pass empty strings for folder-* when the chosen List has no Folder.)

### 7. Verify & wrap up

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog projects
```

Render the row for this project so the user sees the final state. Then
suggest:

- `/worklog:project_remove` to undo / disable auto-logging.
- `/worklog:project_add` (again) to change the ClickUp mapping later.

## Notes

- ClickUp mapping is read by `/worklog:push`: a project with both Space
  and List set creates tasks in that List automatically; with only a
  Space set, `/worklog:push` shows a smaller picker (just Lists in that
  Space) per new task.
- If the ClickUp MCP isn't connected, step 6 will fail. Skip the
  mapping step or run `/worklog:doctor` first.
