"""canvas module-create — create a module in a course (unpublished).

Deliberately minimal. There is no --publish (Canvas rejects `module[published]`
on create, and modules are created unpublished anyway), and no flag for
prerequisites, sequential progress, unlock dates or completion requirements:
omitting those is exactly what leaves the module free of any progression
policy, which is the intended behaviour.
"""

from __future__ import annotations

import argparse
import sys

from canvas_cli.client import CanvasClient
from canvas_cli.config import Config


def add_arguments(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--course", required=True, help="Course code or numeric ID")
    # --name, not --title: Canvas calls this field `module[name]`, and it is
    # what `module-item-add --module` matches against.
    sub.add_argument("--name", required=True, help="Module name")
    sub.add_argument(
        "--position", type=int, help="1-based position in the module list (default: append)"
    )


def run(args, client: CanvasClient, config: Config) -> int:
    cid = client.resolve_course(args.course)

    existing = client.get_all(f"/courses/{cid}/modules", params={"per_page": 100})
    clash = next(
        (m for m in existing if m.get("name", "").lower() == args.name.lower()), None
    )
    if clash:
        sys.exit(
            f"Module '{args.name}' already exists (id={clash['id']}) — nothing created."
        )

    # The client sends json=, so Canvas needs a real nested object here.
    # Rails bracket keys ("module[name]") are ignored in a JSON body and 400.
    payload: dict = {"module": {"name": args.name}}
    if args.position is not None:
        payload["module"]["position"] = args.position

    result = client.post(f"/courses/{cid}/modules", payload)
    mid = result.get("id")
    base = config.base_url.rstrip("/")
    print(f"Module created (unpublished): '{args.name}'")
    print(f"  ID     : {mid}")
    print(f"  Canvas : {base}/courses/{cid}/modules#context_module_{mid}")
    return 0
