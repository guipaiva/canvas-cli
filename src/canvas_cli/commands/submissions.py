"""canvas submissions — list who submitted vs. who's missing."""

from __future__ import annotations

import argparse

from canvas_cli.client import CanvasClient
from canvas_cli.config import Config


def add_arguments(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--course", required=True, help="Course code or numeric ID")
    sub.add_argument("--assignment", required=True, type=int, help="Canvas assignment ID")


def run(args, client: CanvasClient, config: Config) -> int:
    cid = client.resolve_course(args.course)
    subs = client.get_all(
        f"/courses/{cid}/assignments/{args.assignment}/submissions",
        params={"include[]": "user", "per_page": 100},
    )
    submitted = [s for s in subs if s.get("workflow_state") != "unsubmitted"]
    missing = [s for s in subs if s.get("workflow_state") == "unsubmitted"]

    print(f"Assignment {args.assignment} — {args.course} (course {cid})")
    print(f"  {len(submitted)} submitted / {len(subs)} enrolled\n")

    if submitted:
        print("SUBMITTED:")
        for s in submitted:
            name = s.get("user", {}).get("name", "?")
            at = s.get("submitted_at", "")[:16] if s.get("submitted_at") else "—"
            print(f"  ✓  {name:<40} {at}")

    if missing:
        print("\nMISSING:")
        for s in missing:
            name = s.get("user", {}).get("name", "?")
            print(f"  ✗  {name}")

    return 0
