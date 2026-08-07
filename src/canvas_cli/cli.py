#!/usr/bin/env python3
"""canvas — A generic Canvas LMS CLI for teachers.

Subcommands:
    submissions      List submission status for an assignment
    download         Download submission files locally
    assignments      List assignments in a course
    roster           List enrolled students
    grade            Post a grade to one student
    post-grades      Post grades from a JSON file (bulk)
    page-create      Create a Canvas page from a markdown file (draft)
    page-update      Update title or publish state of an existing page
    assign-create    Create a Canvas assignment from a markdown file (draft)
    modules          List modules and their items
    announce         Post a course announcement

Configuration:
    Set CANVAS_API_TOKEN (env) and create .canvas.toml in your project root:

        [canvas]
        base_url = "https://your-institution.instructure.com"

        [aliases]
        "MY-COURSE" = 12345

    Run 'canvas --help' or 'canvas <subcommand> --help' for details.
"""

import argparse

from canvas_cli import commands
from canvas_cli.config import load_config
from canvas_cli.client import CanvasClient

from canvas_cli.commands import (
    announce,
    assign_create,
    assignments,
    download,
    grade,
    modules,
    page_create,
    page_update,
    post_grades,
    roster,
    submissions,
)

_COMMANDS = {
    "submissions":     submissions,
    "download":        download,
    "assignments":     assignments,
    "roster":          roster,
    "grade":           grade,
    "post-grades":     post_grades,
    "page-create":     page_create,
    "page-update":     page_update,
    "assign-create":   assign_create,
    "modules":         modules,
    "announce":        announce,
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="canvas",
        description="Generic Canvas LMS CLI — resolves course aliases from .canvas.toml",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--base-url", help="Canvas base URL (overrides CANVAS_BASE_URL env)")
    p.add_argument("--token", help="Canvas API token (overrides CANVAS_API_TOKEN env)")

    sub = p.add_subparsers(dest="cmd", required=True)
    for name, mod in _COMMANDS.items():
        s = sub.add_parser(name, help=mod.__doc__.splitlines()[0].strip() if mod.__doc__ else "")
        mod.add_arguments(s)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv(".env")

    config = load_config(args)
    client = CanvasClient.from_config(config)

    mod = _COMMANDS[args.cmd]
    raise SystemExit(mod.run(args, client, config))


if __name__ == "__main__":
    main()
