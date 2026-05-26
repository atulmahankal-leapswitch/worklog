---
description: Register the current working directory as a project for automatic Claude Code session logging — argument can be a project name, a ClickUp list id, or a 'Space / Folder / List' breadcrumb
argument-hint: "[<list-id> | 'Space / Folder / List' | project-name]   (optional)"
---

Register the **current working directory** as a worklog project so that
every Claude Code session that ends in this directory (or any
subdirectory) gets auto-logged to the timesheet. The argument is
overloaded — use whichever form fits:

| `$ARGUMENTS` form                          | Effect                                                           |
|--------------------------------------------|------------------------------------------------------------------|
| empty                                      | interactive — pick name, then optionally map ClickUp             |
| plain text (no `/`, not all-digits)        | use as the project's local name; ClickUp mapping is interactive  |
| all digits (e.g. `901611667227`)           | treat as a **ClickUp List id**; resolve hierarchy from ClickUp   |
| contains `/` (e.g. `Core Team / Application Developement / Hostbill`) | treat as a **breadcrumb**: `<Space> / [<Folder> /] <List>` |

The shortcut forms set the ClickUp Space/Folder/List in one go and use
the resolved **list name** as the project's local name (unless a row
already exists at this cwd, in which case the existing name is kept).

Safe to re-run on an existing project — `project register` keys on the
path, so it updates in place and never creates a duplicate.

## Steps

### 1. Resolve cwd and look up any existing project

```bash
PWD_NOW="$(pwd)"
DEFAULT_NAME="$(basename "$PWD_NOW")"
```

Fetch all projects as JSON and search for one whose `path` equals
`$PWD_NOW`:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog projects --format json
```

If a row matches, capture its current `name` and ClickUp fields —
they're the defaults for steps 2 and 6.

### 2. Parse `$ARGUMENTS`

Decide which mode you're in:

- **empty** → `MODE=interactive`
- **all digits** → `MODE=list_id`, `TARGET_LIST_ID="$ARGUMENTS"`
- **contains `/`** → `MODE=breadcrumb`, split on `/` and strip each
  segment. 3 segments = Space/Folder/List, 2 = Space/List.
- else → `MODE=name`, `CHOSEN_NAME="$ARGUMENTS"`

### 3. (modes `list_id` and `breadcrumb`) Resolve via ClickUp MCP

Fetch the full hierarchy once:

```
mcp__claude_ai_ClickUp__clickup_get_workspace_hierarchy
  max_depth: 2
```

Capture `hierarchy.root.id` as `WORKSPACE_ID`.

Walk the tree to resolve:

- **list_id mode** — find any List whose `id == TARGET_LIST_ID`. Read
  its name. Walk up: if its parent is a Folder, capture folder id+name
  and the Folder's parent Space id+name. If its parent is a Space
  directly, capture only Space id+name and leave Folder fields empty.
- **breadcrumb mode** — match Space name (case-insensitive) at depth 1.
  Then either match Folder name + List name (3 segments) or List name
  directly under Space (2 segments). If a name is ambiguous (multiple
  matches), present an `AskUserQuestion` to disambiguate.

If resolution fails (id not found, name doesn't match anything), abort
with a clear error and suggest `/worklog:project_add` with no args.

Set:
- `SPACE_ID`, `SPACE_NAME`
- `FOLDER_ID`, `FOLDER_NAME` (may be empty)
- `LIST_ID`, `LIST_NAME`

### 4. Pick the project's local name

- If `MODE=name` → use `$ARGUMENTS`.
- Else if a row already exists at this cwd → keep the existing name.
- Else if `MODE` resolved a list → use `LIST_NAME` as the default. Ask:
  "Use **`$LIST_NAME`** as the project name? (Enter to accept, or type
  a different name.)"
- Else (interactive, no existing row) → ask:
  "Register this folder as project **`$DEFAULT_NAME`**? (Enter to
  accept, or type a different name.)"

Store the answer as `CHOSEN_NAME`.

### 5. Register (or update) the project

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog project register \
  --path "$PWD_NOW" --name "$CHOSEN_NAME"
```

Echo the CLI's confirmation.

### 6. Map / re-map ClickUp

#### 6a. Shortcut modes (list_id or breadcrumb)

Save the resolved mapping directly:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog project set-clickup \
  --name "$CHOSEN_NAME" --workspace-id "$WORKSPACE_ID" \
  --space-id "$SPACE_ID"   --space-name  "$SPACE_NAME" \
  --folder-id "$FOLDER_ID" --folder-name "$FOLDER_NAME" \
  --list-id "$LIST_ID"     --list-name   "$LIST_NAME"
```

Then jump to step 7.

#### 6b. Interactive / name modes

Display the current ClickUp mapping from step 1 (or "Not mapped yet.")
and ask via `AskUserQuestion` (single-select):

```
question: "Map this project to a ClickUp Space?  (current: <…>)"
options:
  - "Yes — pick a Space (and optionally a List)"
  - "No — leave as-is"
  - "Clear the current mapping"   (only if a mapping exists)
```

If **No** → step 7. If **Clear**:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog project set-clickup \
  --name "$CHOSEN_NAME" \
  --workspace-id "" \
  --space-id "" --space-name "" \
  --folder-id "" --folder-name "" \
  --list-id "" --list-name ""
```

…and step 7. Otherwise drive the Space picker, then (optionally) the
List picker, exactly as in the previous version of this command:

1. `clickup_get_workspace_hierarchy` (`max_depth: 0`) → pick Space →
   capture `WORKSPACE_ID`, `SPACE_ID`, `SPACE_NAME`.
2. Ask "pin a default List?". If yes,
   `clickup_get_workspace_hierarchy` with `space_ids: ["$SPACE_ID"]`
   and `max_depth: 2`, then show each List as
   `<folder name> / <list name>`; capture `FOLDER_*` and `LIST_*`.
3. Save with the same `worklog project set-clickup` call as in 6a.

### 7. Verify & wrap up

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog projects
```

Render the row for this project so the user sees the final state.
Remind them:

- `/worklog:project_remove` to disable auto-logging.
- `/worklog:project_add <new target>` to switch the ClickUp mapping
  later.

## Examples

```
/worklog:project_add                                                    # interactive
/worklog:project_add MyService                                          # set name; no clickup yet
/worklog:project_add 901611667227                                       # map directly to a List id
/worklog:project_add Core Team / Application Developement / Hostbill    # breadcrumb
/worklog:project_add 'Tech / Hostbill'                                  # breadcrumb (no folder)
```

## Notes

- ClickUp mapping is read by `/worklog:push`: a project with both Space
  and List set creates tasks in that List automatically; with only a
  Space set, `/worklog:push` shows a smaller picker (just Lists in that
  Space) per new task.
- If the ClickUp MCP isn't connected, the shortcut modes will fail.
  Run `/worklog:doctor` first.
