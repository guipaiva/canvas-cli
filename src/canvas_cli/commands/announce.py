"""canvas announce — post a course announcement."""

from __future__ import annotations

import argparse

from canvas_cli.client import CanvasClient
from canvas_cli.config import Config


def add_arguments(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--course", required=True, help="Course code or numeric ID")
    sub.add_argument("--title", required=True)
    sub.add_argument("--body", required=True)


def run(args, client: CanvasClient, config: Config) -> int:
    cid = client.resolve_course(args.course)
    payload = {
        "title": args.title,
        "message": args.body,
        "is_announcement": True,
        "published": True,
    }
    result = client.post(f"/courses/{cid}/discussion_topics", payload)
    print(f"Announcement posted: '{args.title}' (id={result.get('id')})")
    return 0
