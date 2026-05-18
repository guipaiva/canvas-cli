# canvas-cli

A generic Canvas LMS CLI for teachers. Supports listing submissions, downloading student work, bulk grading, creating pages and assignments from markdown, and posting announcements.

## Install

```bash
pip install -e .
```

Or from GitHub:

```bash
pip install git+https://github.com/guipaiva/canvas-cli
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
