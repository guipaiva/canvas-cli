"""canvas modules — list a course's modules and their items."""

from __future__ import annotations

import argparse

from canvas_cli.client import CanvasClient
from canvas_cli.config import Config

_TITLE_WIDTH = 60


def add_arguments(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--course", required=True, help="Course code or numeric ID")
    sub.add_argument(
        "--no-items",
        dest="no_items",
        action="store_true",
        help="List modules only, without their items",
    )


def run(args, client: CanvasClient, config: Config) -> int:
    cid = client.resolve_course(args.course)
    params = {"per_page": 100}
    if not args.no_items:
        params["include[]"] = "items"
    mods = client.get_all(f"/courses/{cid}/modules", params=params)

    print(f"Modules — {args.course} (course {cid})\n")
    if not mods:
        print("  (no modules)")
        return 0

    for m in sorted(mods, key=lambda x: x.get("position", 999)):
        pub = "✓" if m.get("published") else "○"
        count = m.get("items_count", 0)
        label = "item" if count == 1 else "items"
        print(f"  {pub} [{m['id']}] {m.get('name', '?'):<55} {count} {label}")

        if args.no_items:
            continue
        for it in _items_of(client, cid, m):
            ipub = "✓" if it.get("published") else "○"
            title = _truncate(it.get("title", "?"), _TITLE_WIDTH)
            pad = "  " * it.get("indent", 0)
            content = f"  ({it['content_id']})" if it.get("content_id") else ""
            print(f"      {ipub} {it.get('type', '?'):<12} {pad}{title}{content}")
    return 0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _items_of(client: CanvasClient, cid: int, module: dict) -> list:
    """Items for one module.

    `include[]=items` is best-effort — Canvas drops it once a course's total
    item count gets large, so fall back to a per-module fetch rather than
    silently printing a module as empty.
    """
    items = module.get("items")
    if items is not None:
        return items
    if not module.get("items_count"):
        return []
    return client.get_all(
        f"/courses/{cid}/modules/{module['id']}/items", params={"per_page": 100}
    )


def _truncate(text: str, width: int) -> str:
    """Clip long titles — a SubHeader can hold a whole paragraph."""
    return text if len(text) <= width else text[: width - 1] + "…"
