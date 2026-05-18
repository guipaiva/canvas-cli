"""canvas post-grades — bulk grade posting from a generic JSON file.

Input JSON schema:
[
  {
    "student_name": "Alice Silva",
    "score": 8.5,
    "comment": "Formatted comment string (optional)",
    "also_post_to": ["Bob Souza"]   // names to fuzzy-match + post same grade (optional)
  }
]

students.json (produced by `canvas download`) must be present in --submissions-dir.
Grades with score < 0 are skipped (error sentinel from upstream graders).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from canvas_cli.client import CanvasClient
from canvas_cli.config import Config
from canvas_cli.utils.fuzzy import MATCH_CONFIDENT, find_match


def add_arguments(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--course", required=True, help="Course code or numeric ID")
    sub.add_argument("--assignment", required=True, type=int)
    sub.add_argument("--grades", required=True, help="Path to grades JSON file")
    sub.add_argument(
        "--submissions-dir",
        required=True,
        dest="submissions_dir",
        help="Directory containing students.json (produced by 'canvas download')",
    )
    sub.add_argument("--dry-run", action="store_true")


def run(args, client: CanvasClient, config: Config) -> int:
    cid = client.resolve_course(args.course)

    students_file = Path(args.submissions_dir) / "students.json"
    if not students_file.exists():
        sys.exit(f"Error: {students_file} not found — run 'canvas download' first")

    students = json.loads(students_file.read_text())
    user_id_map: dict[str, int] = {
        s["name"]: s["user_id"] for s in students if s.get("user_id")
    }
    group_entries: set[str] = {s["name"] for s in students if s.get("group_id")}

    entries = json.loads(Path(args.grades).read_text())

    if args.dry_run:
        print("DRY RUN — no grades will be posted\n")

    errors, skipped, posted = [], [], []

    for entry in entries:
        name = entry["student_name"]
        score = entry.get("score", 0)
        comment: str | None = entry.get("comment") or None
        also_post_to: list[str] = [
            p for p in (entry.get("also_post_to") or [])
            if p and name not in group_entries  # Canvas handles group propagation
        ]

        if score < 0:
            print(f"  SKIP {name} — error row (score={score})")
            skipped.append(name)
            continue

        user_id = user_id_map.get(name)
        if not user_id:
            print(f"  SKIP {name} — not found in students.json")
            skipped.append(name)
            continue

        if args.dry_run:
            print(f"  WOULD POST {name} → {score}")
            if comment:
                print(f"    Comment: {comment}")
            posted.append(name)
            for partner_name in also_post_to:
                _report_partner(partner_name, user_id_map, score, dry_run=True)
            continue

        if _post_one(client, cid, args.assignment, user_id, score, comment, name):
            posted.append(name)
        else:
            errors.append(name)
            continue

        for partner_name in also_post_to:
            p_uid, matched, match_score = find_match(partner_name, user_id_map)
            if p_uid is None:
                print(
                    f"    PARTNER NOT FOUND: '{partner_name}'"
                    f" (best: '{matched}' score={match_score:.2f})"
                )
            else:
                conf = "confident" if match_score >= MATCH_CONFIDENT else "low-confidence"
                label = f"partner {matched} [{conf} match={match_score:.2f}]"
                if _post_one(client, cid, args.assignment, p_uid, score, comment, label):
                    posted.append(matched)
                else:
                    errors.append(matched)

    print(
        f"\nSummary: {len(posted)} posted | {len(skipped)} skipped | {len(errors)} errors"
    )
    if errors:
        print(f"Failed: {', '.join(errors)}")
        return 1
    return 0


def _post_one(
    client: CanvasClient,
    cid: int,
    assignment_id: int,
    user_id: int,
    score: float,
    comment: str | None,
    label: str,
) -> bool:
    payload: dict = {"submission": {"posted_grade": str(score)}}
    if comment:
        payload["comment"] = {"text_comment": comment}
    try:
        client.put(
            f"/courses/{cid}/assignments/{assignment_id}/submissions/{user_id}", payload
        )
        print(f"  Posted {label} → {score}")
        return True
    except Exception as e:
        print(f"  ERROR {label}: {e}")
        return False


def _report_partner(
    partner_name: str, user_id_map: dict, score: float, *, dry_run: bool
) -> None:
    p_uid, matched, match_score = find_match(partner_name, user_id_map)
    if p_uid is None:
        print(
            f"    PARTNER NOT FOUND: '{partner_name}'"
            f" (best: '{matched}' score={match_score:.2f})"
        )
    else:
        conf = "confident" if match_score >= MATCH_CONFIDENT else "low-confidence"
        print(
            f"    WOULD POST partner {matched} → {score}"
            f"  [{conf} match={match_score:.2f}]"
        )
