"""canvas grade — post a grade to a single student."""

from __future__ import annotations

import argparse

from canvas_cli.client import CanvasClient
from canvas_cli.config import Config


def add_arguments(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--course", required=True, help="Course code or numeric ID")
    sub.add_argument("--assignment", required=True, type=int)
    sub.add_argument("--student", required=True, help="Student name (partial match OK)")
    sub.add_argument("--grade", required=True, type=float)
    sub.add_argument("--comment", help="Optional text comment")
    sub.add_argument("--dry-run", action="store_true")


def run(args, client: CanvasClient, config: Config) -> int:
    cid = client.resolve_course(args.course)

    enrollments = client.get_all(
        f"/courses/{cid}/enrollments",
        params={"type[]": "StudentEnrollment", "per_page": 100},
    )
    matches = [
        e
        for e in enrollments
        if args.student.lower() in e.get("user", {}).get("name", "").lower()
    ]
    if not matches:
        import sys
        sys.exit(f"No student matching '{args.student}' found in {args.course}")
    if len(matches) > 1:
        names = [e["user"]["name"] for e in matches]
        import sys
        sys.exit(f"Ambiguous name '{args.student}' — matches: {names}")

    user = matches[0]["user"]
    uid = user["id"]
    name = user["name"]

    if args.dry_run:
        print(f"DRY RUN — would post {args.grade} to {name} (uid={uid})")
        return 0

    payload = {"submission": {"posted_grade": str(args.grade)}}
    if args.comment:
        payload["comment"] = {"text_comment": args.comment}

    client.put(f"/courses/{cid}/assignments/{args.assignment}/submissions/{uid}", payload)
    print(f"Posted {args.grade} → {name}")
    return 0
