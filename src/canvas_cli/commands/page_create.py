"""canvas page-create — create a Canvas page from a markdown file (draft)."""

from __future__ import annotations

import argparse
from pathlib import Path

from canvas_cli.client import CanvasClient
from canvas_cli.config import Config
from canvas_cli.utils.markdown import md_to_html


def add_arguments(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--course", required=True, help="Course code or numeric ID")
    sub.add_argument("--title", required=True)
    sub.add_argument("--from-file", required=True, dest="from_file", help="Path to .md file")


def run(args, client: CanvasClient, config: Config) -> int:
    cid = client.resolve_course(args.course)
    content = Path(args.from_file).read_text(encoding="utf-8")
    body = md_to_html(content)

    payload = {"wiki_page": {"title": args.title, "body": body, "published": False}}
    result = client.post(f"/courses/{cid}/pages", payload)
    url = result.get("url", "")
    base = config.base_url.rstrip("/")
    print(f"Page created (draft): '{args.title}'")
    print(f"  URL slug : {url}")
    print(f"  Canvas   : {base}/courses/{cid}/pages/{url}")
    return 0
