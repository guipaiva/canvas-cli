"""canvas module-item-add — add an item to a module.

Item types map 1:1 onto Canvas's `module_item[type]`, and each type takes
exactly one content reference (or none, for SubHeader). Passing a reference the
type doesn't use is an error rather than being ignored — silently landing a
broken item in a module is worse than a refusal.
"""

from __future__ import annotations

import argparse
import sys

import requests

from canvas_cli.client import CanvasClient
from canvas_cli.config import Config

_TYPES = ("SubHeader", "File", "Assignment", "Page", "ExternalUrl")

_ALIASES = {t.lower(): t for t in _TYPES}
_ALIASES.update(
    {"sub-header": "SubHeader", "external-url": "ExternalUrl", "url": "ExternalUrl",
     "link": "ExternalUrl"}
)

# Which content flag each type requires; None means "takes no content reference".
_CONTENT_FLAG = {
    "SubHeader":   None,
    "File":        "--content-id",
    "Assignment":  "--content-id",
    "Page":        "--page-url",
    "ExternalUrl": "--url",
}

_MAX_INDENT = 5


def add_arguments(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--course", required=True, help="Course code or numeric ID")
    sub.add_argument(
        "--module", required=True, help="Module ID, or part of the module name (e.g. 'Bloco A')"
    )
    sub.add_argument(
        "--type", required=True, type=_norm_type, choices=_TYPES,
        help="Item type: SubHeader, File, Assignment, Page or ExternalUrl",
    )
    sub.add_argument("--title", required=True, help="Item label shown in the module")
    sub.add_argument(
        "--content-id", dest="content_id", type=int,
        help="Canvas file or assignment ID (--type File, Assignment)",
    )
    sub.add_argument("--page-url", dest="page_url", help="Page URL slug (--type Page)")
    sub.add_argument("--url", help="Target URL (--type ExternalUrl)")
    sub.add_argument(
        "--indent", type=int, default=0, help=f"Indent level 0-{_MAX_INDENT} (default: 0)"
    )
    sub.add_argument(
        "--position", type=int, help="1-based position in the module (default: append)"
    )
    sub.add_argument(
        "--new-tab", dest="new_tab", action="store_true",
        help="Open in a new tab (--type ExternalUrl only)",
    )


def run(args, client: CanvasClient, config: Config) -> int:
    cid = client.resolve_course(args.course)

    modules = client.get_all(f"/courses/{cid}/modules", params={"per_page": 100})
    module = _pick_module(args.module, modules)
    payload = _build_item(args)

    _check_content_exists(client, cid, args)

    # The only place the CLI can surface this: an item dropped into an already
    # published module is visible to students the moment it is created.
    if module.get("published"):
        print(
            f"Warning: module '{module.get('name')}' is published — "
            "this item becomes visible to students immediately."
        )

    result = client.post(f"/courses/{cid}/modules/{module['id']}/items", payload)

    base = config.base_url.rstrip("/")
    # SubHeader items have no html_url at all, and an ExternalUrl's html_url is
    # an /api/v1 redirect that is useless in a browser — link the module page
    # for both, and the item itself otherwise.
    if args.type in ("SubHeader", "ExternalUrl") or not result.get("html_url"):
        link = f"{base}/courses/{cid}/modules#context_module_{module['id']}"
    else:
        link = result["html_url"]

    print(f"Module item added: '{args.title}'")
    print(f"  ID     : {result.get('id')}")
    print(f"  Module : {module.get('name')} ({module['id']})")
    print(f"  Type   : {args.type}")
    print(f"  Indent : {args.indent}")
    print(f"  Canvas : {link}")
    return 0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _norm_type(value: str) -> str:
    """Case/dash-insensitive type name. Unknown values pass through unchanged so
    that argparse's own `choices` produces the error message."""
    return _ALIASES.get(value.strip().lower().replace("_", "-"), value)


def _pick_module(ref: str, modules: list) -> dict:
    """Accept a numeric module ID or a case-insensitive name substring.

    Substring rather than exact: the real modules are named things like
    'Bloco A — Dart' with an em dash, and --module "Bloco A" should just work.
    Deliberately not utils/fuzzy — that is tuned for typo'd student names, and
    landing an item in the wrong module is worse than an error.
    """
    if ref.isdigit():
        match = next((m for m in modules if m["id"] == int(ref)), None)
        if not match:
            sys.exit(f"No module with ID {ref} in this course")
        return match
    matches = [m for m in modules if ref.lower() in m.get("name", "").lower()]
    if not matches:
        names = [m.get("name") for m in modules]
        sys.exit(f"No module matching '{ref}'.\nAvailable: {names}")
    if len(matches) > 1:
        sys.exit(f"Ambiguous module '{ref}' — matches: {[m['name'] for m in matches]}")
    return matches[0]


def _build_item(args) -> dict:
    """Map flags onto a module_item payload, failing loudly on mismatches.

    Note the nesting: CanvasClient sends json=, so Canvas needs a real
    {"module_item": {...}} object. Rails bracket keys ("module_item[title]")
    are ignored in a JSON body and the request 400s with no explanation.
    """
    if not 0 <= args.indent <= _MAX_INDENT:
        sys.exit(f"--indent must be between 0 and {_MAX_INDENT} (got {args.indent})")

    given = {"--content-id": args.content_id, "--page-url": args.page_url, "--url": args.url}
    expected = _CONTENT_FLAG[args.type]

    extras = [flag for flag, val in given.items() if val is not None and flag != expected]
    if extras:
        sys.exit(f"--type {args.type} does not take {', '.join(extras)}")
    if expected and given[expected] is None:
        sys.exit(f"--type {args.type} requires {expected}")
    if args.new_tab and args.type != "ExternalUrl":
        sys.exit("--new-tab only applies to --type ExternalUrl")

    item: dict = {"title": args.title, "type": args.type, "indent": args.indent}
    if args.type in ("File", "Assignment"):
        item["content_id"] = args.content_id
    elif args.type == "Page":
        item["page_url"] = args.page_url  # Page uses page_url, not content_id
    elif args.type == "ExternalUrl":
        if not args.url.startswith(("http://", "https://")):
            sys.exit(f"--url must start with http:// or https:// (got '{args.url}')")
        item["external_url"] = args.url
        item["new_tab"] = args.new_tab

    if args.position is not None:
        item["position"] = args.position
    return {"module_item": item}


def _check_content_exists(client: CanvasClient, cid: int, args) -> None:
    """Fail before creating an item that points at nothing."""
    probes = {
        "File": f"/files/{args.content_id}",
        "Assignment": f"/courses/{cid}/assignments/{args.content_id}",
        "Page": f"/courses/{cid}/pages/{args.page_url}",
    }
    path = probes.get(args.type)
    if not path:
        return
    ref = args.content_id if args.type != "Page" else args.page_url
    try:
        client.get(path)
    except requests.HTTPError:
        sys.exit(f"No {args.type} '{ref}' found in course {cid}")
