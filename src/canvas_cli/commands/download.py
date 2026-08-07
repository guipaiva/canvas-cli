"""canvas download — download submission files + emit students.json."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import requests

from canvas_cli.client import CanvasClient
from canvas_cli.config import Config
from canvas_cli.utils.fs import safe_dirname


def add_arguments(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--course", required=True, help="Course code or numeric ID")
    sub.add_argument("--assignment", required=True, type=int)
    sub.add_argument(
        "--out",
        help="Output directory (default: downloads/<course>/assignment-<id>)",
    )


def run(args, client: CanvasClient, config: Config) -> int:
    cid = client.resolve_course(args.course)
    dest = Path(args.out or f"downloads/{args.course}/assignment-{args.assignment}")
    dest.mkdir(parents=True, exist_ok=True)

    asn = client.get(f"/courses/{cid}/assignments/{args.assignment}")
    group_category_id = asn.get("group_category_id")

    include_params = ["user", "submission_comments"]
    if group_category_id:
        include_params.append("group")

    subs = client.get_all(
        f"/courses/{cid}/assignments/{args.assignment}/submissions",
        params={"include[]": include_params, "per_page": 100},
    )

    if group_category_id:
        print(f"Group assignment (category {group_category_id}) — one submission per group")
        groups = _fetch_groups(client, group_category_id)
        students = _download_group_subs(subs, groups, dest, client)
    else:
        students = _download_individual_subs(subs, dest, client)

    (dest / "students.json").write_text(
        json.dumps(students, indent=2, ensure_ascii=False)
    )
    submitted = sum(1 for s in students if s["submitted"])
    print(f"\n{submitted} submitted / {len(students)} enrolled — saved to {dest}")
    return 0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_groups(client: CanvasClient, group_category_id: int) -> dict:
    groups_raw = client.get_all(
        f"/group_categories/{group_category_id}/groups",
        params={"per_page": 100},
    )
    groups = {}
    for g in groups_raw:
        gid = g["id"]
        members_raw = client.get_all(f"/groups/{gid}/users", params={"per_page": 100})
        groups[gid] = {
            "name": g["name"],
            "members": [{"name": u["name"], "user_id": u["id"]} for u in members_raw],
        }
    return groups


def _download_files(
    s: dict, dest_dir: Path, token: str, label: str
) -> bool:
    atts = s.get("attachments") or []
    sub_url = s.get("url") or ""
    sub_body = s.get("body") or ""
    sub_type = s.get("submission_type") or ""
    comments = [
        c.get("comment", "")
        for c in (s.get("submission_comments") or [])
        if c.get("comment")
    ]

    if not (atts or sub_url or sub_body):
        return False

    dest_dir.mkdir(exist_ok=True)
    headers = {"Authorization": f"Bearer {token}"}

    for att in atts:
        local = dest_dir / att["filename"]
        if not local.exists():
            r = requests.get(att["url"], headers=headers)
            r.raise_for_status()
            local.write_bytes(r.content)
            print(f"  ↓  {label} / {att['filename']}")

    if sub_url:
        url_file = dest_dir / "submission-url.txt"
        if not url_file.exists():
            url_file.write_text(sub_url, encoding="utf-8")
            print(f"  ↓  {label} / submission-url.txt ({sub_url})")

    if sub_body and sub_type == "online_text_entry":
        text_clean = re.sub(r"<[^>]+>", "", sub_body).strip()
        text_file = dest_dir / "submission-text.txt"
        if not text_file.exists():
            text_file.write_text(text_clean, encoding="utf-8")
            print(f"  ↓  {label} / submission-text.txt")

    if comments:
        (dest_dir / "submission-comments.txt").write_text(
            "\n".join(comments), encoding="utf-8"
        )

    return True


def _download_individual_subs(
    subs: list, dest: Path, client: CanvasClient
) -> list:
    students = []
    for s in subs:
        user = s.get("user", {})
        name = user.get("name", "Unknown")
        uid = user.get("id")
        comments = [
            c.get("comment", "")
            for c in (s.get("submission_comments") or [])
            if c.get("comment")
        ]
        submitted = _download_files(s, dest / safe_dirname(name), client.token, name)
        students.append(
            {"name": name, "user_id": uid, "submitted": submitted, "comments": comments}
        )
    return students


def _download_group_subs(
    subs: list, groups: dict, dest: Path, client: CanvasClient
) -> list:
    group_subs: dict = {gid: [] for gid in groups}
    ungrouped: list = []
    for s in subs:
        gid = (s.get("group") or {}).get("id")
        if gid in group_subs:
            group_subs[gid].append(s)
        else:
            ungrouped.append(s)

    students = []
    seen_uids: set = set()

    for gid, g in groups.items():
        members = g["members"]
        if not members:
            continue
        for m in members:
            seen_uids.add(m["user_id"])

        group_name = g["name"]
        group_label = safe_dirname(group_name)
        rep_sub = next(
            (
                sub
                for sub in group_subs[gid]
                if sub.get("attachments") or sub.get("url") or sub.get("body")
            ),
            None,
        )
        submitter_uid = members[0]["user_id"]
        comments = []
        if rep_sub:
            submitter_uid = (rep_sub.get("user") or {}).get("id", submitter_uid)
            comments = [
                c.get("comment", "")
                for c in (rep_sub.get("submission_comments") or [])
                if c.get("comment")
            ]
        submitted = (
            _download_files(rep_sub, dest / group_label, client.token, group_name)
            if rep_sub
            else False
        )
        students.append(
            {
                "name": group_name,
                "group_id": gid,
                "members": members,
                "user_id": submitter_uid,
                "submitted": submitted,
                "comments": comments,
            }
        )

    for s in ungrouped:
        uid = (s.get("user") or {}).get("id")
        if uid in seen_uids:
            continue
        seen_uids.add(uid)
        name = (s.get("user") or {}).get("name", "Unknown")
        comments = [
            c.get("comment", "")
            for c in (s.get("submission_comments") or [])
            if c.get("comment")
        ]
        submitted = _download_files(s, dest / safe_dirname(name), client.token, name)
        students.append(
            {"name": name, "user_id": uid, "submitted": submitted, "comments": comments}
        )

    return students
