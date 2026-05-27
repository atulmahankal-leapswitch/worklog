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

**The project name mirrors its ClickUp List** — the command does not
ask for a separate name. Whatever List you map (by id, breadcrumb, or
picker) becomes the project's local name, so `/worklog:projects` and
`/worklog:push` line up 1:1 with ClickUp. A name is only invented (from
the cwd folder) when you deliberately register a folder *without* a
ClickUp mapping.

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

### 4. Decide the project's local name

**The project name mirrors the ClickUp List — don't ask for it
separately.** Resolve `CHOSEN_NAME` in this order, no prompt:

1. A ClickUp List was resolved (any mode that produced `LIST_NAME`, or
   the interactive picker in step 6) → `CHOSEN_NAME = LIST_NAME`.
2. `MODE=name` (user passed plain text and no list) → use `$ARGUMENTS`.
3. A row already exists at this cwd → keep its existing name.
4. Nothing else → fall back to `$DEFAULT_NAME` (the cwd folder name).

Only the no-ClickUp fallback (#3/#4) uses a non-list name. Whenever a
List is chosen, the project is named exactly after it — so
`/worklog:projects` and `/worklog:push` line up 1:1 with ClickUp.

> Note: in the interactive picker path (step 6b) the List isn't known
> until after the picker runs. In that case do step 5's register with a
> temporary name (`$DEFAULT_NAME`), then **rename** to the chosen List
> name as part of the `set-clickup` step by calling `project register`
> again with `--name "$LIST_NAME"` (register keys on path, so it just
> renames in place).

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

#### 6b. Interactive / name modes — auto-match by name

Display the current ClickUp mapping from step 1 (or "Not mapped yet.").
If the user wants to keep the existing mapping, jump to step 7.
Otherwise, **before showing any picker**, try to auto-match the
project's local name to an existing ClickUp List.

Fetch the full hierarchy once:

```
mcp__claude_ai_ClickUp__clickup_get_workspace_hierarchy
  max_depth: 2
```

Save `hierarchy.root.id` as `WORKSPACE_ID`. Walk the tree to find every
List whose `name` matches `$CHOSEN_NAME` case-insensitively. For each
match capture its Space id/name and Folder id/name (Folder may be empty).

Then take **one of three branches** below depending on the match count.

##### Exactly one match — confirm and save

```
question: "Found ClickUp List '<space>/<folder?>/<list>'. Use it?"
options:
  - "Yes — use this mapping"
  - "No — pick a different List"
  - "Clear / skip ClickUp mapping for now"
```

If **Yes** → save the resolved mapping with the same
`worklog project set-clickup` call from 6a and jump to step 7.

##### Multiple matches — disambiguate

Build an `AskUserQuestion` listing every match as
`<space name> / <folder name> / <list name>` so the user can pick the
intended one. Then save and jump to step 7. (Also offer
"Pick a different List" and "Clear / skip" as in the single-match case.)

##### Zero matches — pick existing or create new

```
question: "No ClickUp List named '$CHOSEN_NAME' found. What do you want to do?"
options:
  - "Create a new List in ClickUp with this name"
  - "Pick an existing List (different name)"
  - "Skip ClickUp mapping for now"
```

If **Skip** → jump to step 7.

If **Pick an existing List**, fall through to the "pick from picker"
flow at the bottom of this section.

If **Create**, drive the picker for the *destination*:

1. `clickup_get_workspace_hierarchy` (`max_depth: 1`) → ask which
   **Space** the new List should live in. Capture `SPACE_ID`,
   `SPACE_NAME`.
2. Ask: "Place the new List inside a Folder?"
   - **No** → Folder fields stay empty. Create directly under the Space:
     ```
     mcp__claude_ai_ClickUp__clickup_create_list
       space_id: "$SPACE_ID"
       name: "$CHOSEN_NAME"
     ```
   - **Yes** → fetch `clickup_get_workspace_hierarchy` with
     `space_ids: ["$SPACE_ID"]` and `max_depth: 1`, pick a Folder
     (capture `FOLDER_ID`, `FOLDER_NAME`), then:
     ```
     mcp__claude_ai_ClickUp__clickup_create_list_in_folder
       folder_id: "$FOLDER_ID"
       name: "$CHOSEN_NAME"
     ```
3. Read back the new List's `id` as `LIST_ID` and use `$CHOSEN_NAME` as
   `LIST_NAME`.
4. Save the mapping via the same `worklog project set-clickup` call
   from 6a. Jump to step 7.

##### "Pick an existing List" — manual picker

(Reached from any of the branches above when the user wants to choose
manually.)

1. `clickup_get_workspace_hierarchy` (`max_depth: 0`) → ask which
   Space. Capture `SPACE_ID`, `SPACE_NAME`.
2. `clickup_get_workspace_hierarchy` with `space_ids: ["$SPACE_ID"]`
   and `max_depth: 2`. Present every reachable List as a single
   `AskUserQuestion` labelled `<folder name> / <list name>` (or just
   `<list name>` for direct-under-Space Lists). Capture `FOLDER_ID`,
   `FOLDER_NAME` (empty if no Folder), and `LIST_ID`, `LIST_NAME`.
3. Save with the same `worklog project set-clickup` call from 6a.

##### "Clear" branch

If the user picks "Clear / skip" anywhere and there was an existing
mapping, run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog project set-clickup \
  --name "$CHOSEN_NAME" \
  --workspace-id "" \
  --space-id "" --space-name "" \
  --folder-id "" --folder-name "" \
  --list-id "" --list-name ""
```

If there was no mapping to begin with, just jump to step 7.

### 7. Verify & wrap up

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/bin/worklog project show --name "$CHOSEN_NAME"
```

This prints a focused summary — name + path + auto-log status + ClickUp
breadcrumb, with each segment of the ClickUp breadcrumb rendered as a
clickable link (same format `/worklog:projects` uses). Render the
output as-is.

Then remind the user:

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
