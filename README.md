# canvas-cli

A generic Canvas LMS CLI for teachers. Supports listing submissions, downloading student work, bulk grading, creating pages and assignments from markdown, uploading files, building course modules, and posting announcements.

## Install

### As a Claude Code plugin (recommended)

```shell
# 1. Add the marketplace (one-time)
/plugin marketplace add guipaiva/canvas-cli

# 2. Install the plugin
/plugin install canvas-cli@canvas-cli

# 3. Install the Python package (required for the `canvas` command)
pip install -e ~/.claude/plugins/cache/canvas-cli/canvas-cli/*/

# 4. Reload plugins
/reload-plugins
```

> **Why the pip step?** Claude Code plugins don't auto-install Python packages. The `canvas` command must be on your PATH for the skill to work.

### As a standalone package

```bash
pip install git+https://github.com/guipaiva/canvas-cli
```

Or for local development:

```bash
git clone https://github.com/guipaiva/canvas-cli
pip install -e ./canvas-cli
```

## Setup

1. **API token** — generate at Canvas → Account (avatar, top-left) → Settings → Approved Integrations → + New Access Token. Set it as an env var:

   ```bash
   export CANVAS_API_TOKEN=your_token_here
   ```

   Or add it to a `.env` file at your project root (loaded automatically).

2. **Project config** — create `.canvas.toml` at your project root:

   ```toml
   [canvas]
   base_url = "https://your-institution.instructure.com"

   [aliases]
   "MY-COURSE-P" = 12345
   "MY-COURSE-T" = 12346
   ```

   The CLI walks up from the current directory to find the nearest `.canvas.toml`. `--course` accepts either an alias or a raw numeric Canvas course ID.

## Subcommands

### `submissions`
```bash
canvas submissions --course MY-COURSE-P --assignment 250093
```

### `download`
```bash
canvas download --course MY-COURSE-P --assignment 250093 --out submissions/hw1
```

Downloads all submission files into per-student directories. Emits `students.json` (name → Canvas user ID mapping). Re-running is safe — already-downloaded files are skipped. Handles group assignments correctly.

### `assignments`
```bash
canvas assignments --course MY-COURSE-T
```

### `roster`
```bash
canvas roster --course MY-COURSE-T
```

### `grade`
```bash
canvas grade --course MY-COURSE-P --assignment 250093 --student "Alice Silva" --grade 8.5 --comment "Good work"
canvas grade ... --dry-run   # preview without posting
```

### `post-grades`

Bulk post grades from a JSON file:

```bash
canvas post-grades \
  --course MY-COURSE-P \
  --assignment 250093 \
  --grades grades.json \
  --submissions-dir submissions/hw1 \
  --dry-run
```

**Input schema** (`grades.json`):

```json
[
  {
    "student_name": "Alice Silva",
    "score": 8.5,
    "comment": "Good work. Exercise 3 used map() instead of reduce().",
    "also_post_to": ["Bob Souza"]
  }
]
```

- `comment` — fully-formatted string posted as a Canvas submission comment
- `also_post_to` — list of student names; CLI fuzzy-matches and posts the same grade to each
- Scores `< 0` are skipped (upstream error sentinel)
- `students.json` from `canvas download` must be present in `--submissions-dir`

See `examples/grades.example.json` for a full example.

### `page-create`
```bash
canvas page-create --course MY-COURSE-T --title "Lecture 3 Notes" --from-file notes.md
```
Creates a **draft** page — publish manually in Canvas.

### `page-update`
```bash
canvas page-update --course MY-COURSE-T --page-url "lecture-3-notes" --publish
canvas page-update --course MY-COURSE-T --page-url "lecture-3-notes" --title "New Title"
```

### `assign-create`
```bash
canvas assign-create \
  --course MY-COURSE-P \
  --title "Homework 1" \
  --from-file hw1.md \
  --points 10 \
  --due "2026-05-30 23:59"
```
Creates a **draft** assignment — publish manually at class time.

### `file-upload`
```bash
canvas file-upload --course MY-COURSE-T --file "Lecture 3 slides.pdf" --folder Slides
```
Uploads as **unpublished** (locked) — publish manually in Canvas. The `--folder` path is created if it doesn't exist, nested paths included. `--on-duplicate overwrite` (the default) replaces a same-named file in place, keeping its ID; pass `--on-duplicate rename` to keep both. `--name` overrides the display name.

### `modules`
```bash
canvas modules --course MY-COURSE-T
canvas modules --course MY-COURSE-T --no-items
```
Shows publish state (`✓`/`○`), item type, indent level and content IDs — the IDs you pass to `module-item-add --content-id`.

### `module-create`
```bash
canvas module-create --course MY-COURSE-T --name "Block A — Fundamentals"
```
Creates an **unpublished** module with no prerequisites and no sequential-progress requirement. Refuses to create a second module with the same name.

### `module-item-add`
```bash
canvas module-item-add --course MY-COURSE-T --module "Block A" \
  --type File --title "Lecture 3 slides" --content-id 4224744 --indent 1
```

`--module` accepts a module ID or part of the module name. Each type takes exactly one content reference:

| `--type` | Content flag |
|---|---|
| `SubHeader` | *(none)* |
| `File`, `Assignment` | `--content-id` |
| `Page` | `--page-url` |
| `ExternalUrl` | `--url` (plus optional `--new-tab`) |

Warns when the target module is already published — the item becomes visible to students immediately.

### Weekly workflow

Uploading a lecture's material and filing it under the aula's subheading:

```bash
canvas file-upload      --course MY-COURSE-T --file "Lecture 3.pdf" --folder Slides
canvas assign-create    --course MY-COURSE-T --title "Homework 3" --from-file hw3.md --points 10
canvas module-item-add  --course MY-COURSE-T --module "Block A" --type SubHeader  --title "Lecture 3 — Collections"
canvas module-item-add  --course MY-COURSE-T --module "Block A" --type File       --title "Slides — Lecture 3" --content-id <file id>       --indent 1
canvas module-item-add  --course MY-COURSE-T --module "Block A" --type Assignment --title "Homework 3"         --content-id <assignment id> --indent 1
```

Everything lands unpublished; publish at class time from Canvas.

### `announce`
```bash
canvas announce --course MY-COURSE-T --title "Class cancelled" --body "No class today."
```
Announcements are published immediately and visible to students.

## Global flags

```
--base-url URL    Override CANVAS_BASE_URL env var
--token TOKEN     Override CANVAS_API_TOKEN env var
```

## Claude Code plugin

This repo ships as a Claude Code plugin. Clone it and install as a plugin to get the `canvas` skill in all your Claude Code sessions:

```bash
git clone https://github.com/guipaiva/canvas-cli ~/.claude/plugins/canvas-cli
pip install -e ~/.claude/plugins/canvas-cli
```

## License

MIT
