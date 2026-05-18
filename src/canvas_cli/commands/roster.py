"""canvas roster — list enrolled students."""

from __future__ import annotations

import argparse

from canvas_cli.client import CanvasClient
from canvas_cli.config import Config


def add_arguments(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--course", required=True, help="Course code or numeric ID")


def run(args, client: CanvasClient, config: Config) -> int:
    cid = client.resolve_course(args.course)
    enrollments = client.get_all(
        f"/courses/{cid}/enrollments",
        params={"type[]": "StudentEnrollment", "per_page": 100},
    )
    print(f"Roster — {args.course} (course {cid})  [{len(enrollments)} students]\n")
    for e in sorted(enrollments, key=lambda x: x.get("user", {}).get("name", "")):
        user = e.get("user", {})
        name = user.get("name", "?")
        email = user.get("login_id", "?")
        uid = user.get("id", "?")
        print(f"  [{uid}]  {name:<45} {email}")
    return 0
