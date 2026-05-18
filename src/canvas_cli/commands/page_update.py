"""canvas page-update — update title or publish state of an existing page."""

from __future__ import annotations

import argparse
import sys

from canvas_cli.client import CanvasClient
from canvas_cli.config import Config


def add_arguments(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--course", required=True, help="Course code or numeric ID")
    sub.add_argument("--page-url", required=True, dest="page_url", help="Canvas page URL slug")
    sub.add_argument("--title", help="New title")
    sub.add_argument("--publish", action="store_true")
    sub.add_argument("--unpublish", action="store_true")


def run(args, client: CanvasClient, config: Config) -> int:
    cid = client.resolve_course(args.course)
    changes: dict = {}
    if args.title:
        changes["title"] = args.title
    if args.publish:
        changes["published"] = True
    if args.unpublish:
        changes["published"] = False
    if not changes:
        sys.exit("Nothing to update — pass --title, --publish, or --unpublish")

    client.put(f"/courses/{cid}/pages/{args.page_url}", {"wiki_page": changes})
    print(f"Page '{args.page_url}' updated: {changes}")
    return 0
