---
name: canvas
description: Use the `canvas` CLI to interact with Canvas LMS — list/download submissions, post grades, create pages/assignments, upload files, build course modules, send announcements. Use whenever the user mentions Canvas, assignments, submissions, grades, modules, or wants to interact with their Canvas LMS instance. Also use when the user asks who submitted something, wants to download student work, needs to post a grade or announcement, wants to upload slides or a PDF to a course, or wants to organize course content into modules or blocks.
---

# Canvas CLI

Pre-installed command: `canvas` (from canvas-cli plugin).
Run from a directory containing `.canvas.toml` so course aliases and base URL are resolved automatically.

## Subcommands

| Subcommand | What it does | Key flags |
|---|---|---|
| `submissions` | List submitted vs. missing | `--course --assignment` |
| `download` | Download files + emit `students.json` | `--course --assignment [--out DIR]` |
| `assignments` | List all assignments | `--course` |
| `roster` | List enrolled students (name, email, ID) | `--course` |
| `grade` | Post grade to one student | `--course --assignment --student --grade [--comment] [--dry-run]` |
| `post-grades` | Bulk post from JSON file | `--course --assignment --grades FILE --submissions-dir DIR [--dry-run]` |
| `page-create` | Create page from markdown (draft) | `--course --title --from-file` |
| `page-update` | Publish/rename existing page | `--course --page-url [--title] [--publish\|--unpublish]` |
| `assign-create` | Create assignment from markdown (draft) | `--course --title --from-file --points [--due] [--lock]` |
| `file-upload` | Upload a file into course Files (unpublished) | `--course --file [--folder] [--name] [--on-duplicate]` |
| `modules` | List modules, items, indents and content IDs | `--course [--no-items]` |
| `module-create` | Create a module (unpublished) | `--course --name [--position]` |
| `module-item-add` | Add an item to a module | `--course --module --type --title [--content-id\|--page-url\|--url] [--indent] [--new-tab]` |
| `announce` | Post a course announcement | `--course --title --body` |

`--course` accepts either an alias from `.canvas.toml` `[aliases]` or a raw numeric Canvas course ID.

## `post-grades` input schema

The `--grades` JSON file must use this generic schema:

```json
[
  {
    "student_name": "Alice Silva",
    "score": 8.5,
    "comment": "Formatted feedback string (optional)",
    "also_post_to": ["Bob Souza"]
  }
]
```

- `also_post_to` propagates the same grade to additional students via fuzzy name matching
- Scores < 0 are skipped (error sentinel from upstream graders)
- `students.json` from `canvas download` must be present in `--submissions-dir`

## Configuration

Create `.canvas.toml` in your project root:

```toml
[canvas]
base_url = "https://your-institution.instructure.com"

[aliases]
"MY-COURSE-P" = 12345
"MY-COURSE-T" = 12346
```

Token is read from `CANVAS_API_TOKEN` env var or `.env` file.

## Weekly material workflow

Uploading a lecture's material and filing it under the aula's subheading:

```bash
canvas file-upload     --course MY-COURSE --file "Lecture 3.pdf" --folder Slides
canvas assign-create   --course MY-COURSE --title "Homework 3" --from-file hw3.md --points 10
canvas module-item-add --course MY-COURSE --module "Block A" --type SubHeader  --title "Lecture 3 — Collections"
canvas module-item-add --course MY-COURSE --module "Block A" --type File       --title "Slides — Lecture 3" --content-id <id> --indent 1
canvas module-item-add --course MY-COURSE --module "Block A" --type Assignment --title "Homework 3"         --content-id <id> --indent 1
```

`module-item-add` needs the IDs printed by `file-upload` and `assign-create` — or run `canvas modules` to find them.

## Rules

- Pages, assignments, files and modules are always created as **draft/unpublished** — never auto-published. The professor publishes manually at class time
- Always confirm with the user before posting announcements or grades (students will see them)
- Before creating a page, assignment, module or file, check if it already exists (`canvas modules`, `canvas assignments`) — update, don't duplicate
- Modules are created with **no progression policy** — no prerequisites, no sequential-progress requirement. This is deliberate; never add one
- Adding an item to an **already-published** module makes it visible to students immediately. The CLI warns; confirm with the user before proceeding
- `canvas download` re-running is safe — already-downloaded files are skipped
