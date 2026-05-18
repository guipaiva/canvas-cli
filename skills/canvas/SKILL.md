---
name: canvas
description: Use the `canvas` CLI to interact with Canvas LMS — list/download submissions, post grades, create pages/assignments, send announcements. Use whenever the user mentions Canvas, assignments, submissions, grades, or wants to interact with their Canvas LMS instance. Also use when the user asks who submitted something, wants to download student work, or needs to post a grade or announcement.
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

## Rules

- Pages and assignments are always created as **draft** — never auto-published
- Always confirm with the user before posting announcements or grades (students will see them)
- Before creating a page or assignment, check if it already exists — update, don't duplicate
- `canvas download` re-running is safe — already-downloaded files are skipped
