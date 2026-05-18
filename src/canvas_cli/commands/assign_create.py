"""canvas assign-create — create a Canvas assignment from a markdown file (draft)."""

from __future__ import annotations

import argparse
from pathlib import Path

from canvas_cli.client import CanvasClient
from canvas_cli.config import Config
from canvas_cli.utils.dates import parse_due
from canvas_cli.utils.markdown import md_to_html


def add_arguments(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--course", required=True, help="Course code or numeric ID")
    sub.add_argument("--title", required=True)
    sub.add_argument("--from-file", required=True, dest="from_file")
    sub.add_argument("--points", required=True, type=float)
    sub.add_argument("--due", help="Due date: 'YYYY-MM-DD HH:MM'")
    sub.add_argument("--lock", help="Lock date: 'YYYY-MM-DD HH:MM' (defaults to --due)")


def run(args, client: CanvasClient, config: Config) -> int:
    cid = client.resolve_course(args.course)
    content = Path(args.from_file).read_text(encoding="utf-8")
    body = md_to_html(content)
    due_iso = parse_due(args.due) if args.due else None
    lock_iso = parse_due(args.lock) if args.lock else due_iso

    payload: dict = {
        "assignment": {
            "name": args.title,
            "description": body,
            "points_possible": args.points,
            "submission_types": ["online_upload"],
            "published": False,
        }
    }
    if due_iso:
        payload["assignment"]["due_at"] = due_iso
    if lock_iso:
        payload["assignment"]["lock_at"] = lock_iso

    result = client.post(f"/courses/{cid}/assignments", payload)
    aid = result.get("id", "?")
    base = config.base_url.rstrip("/")
    print(f"Assignment created (draft): '{args.title}'")
    print(f"  ID     : {aid}")
    print(f"  Canvas : {base}/courses/{cid}/assignments/{aid}")
    return 0
