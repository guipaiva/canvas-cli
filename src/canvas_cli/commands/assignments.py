"""canvas assignments — list all assignments in a course."""

from __future__ import annotations

import argparse

from canvas_cli.client import CanvasClient
from canvas_cli.config import Config


def add_arguments(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--course", required=True, help="Course code or numeric ID")


def run(args, client: CanvasClient, config: Config) -> int:
    cid = client.resolve_course(args.course)
    asns = client.get_all(f"/courses/{cid}/assignments", params={"per_page": 100})
    print(f"Assignments — {args.course} (course {cid})\n")
    for a in sorted(asns, key=lambda x: x.get("position", 999)):
        due = a.get("due_at", "")[:10] if a.get("due_at") else "no due"
        pts = a.get("points_possible", "?")
        pub = "✓" if a.get("published") else "○"
        print(f"  {pub} [{a['id']}] {a['name']:<55} due:{due}  pts:{pts}")
    return 0
