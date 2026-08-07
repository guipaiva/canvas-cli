"""canvas file-upload — upload a local file into a course's Files (unpublished).

Canvas uploads are a three-step handshake, and only the first and last steps are
Canvas API calls — the middle one goes to a pre-signed storage URL on another
host, with a multipart body and no Authorization header. That is why the flow
lives here as plain `requests` calls instead of on CanvasClient (same shape as
`download.py`, which also talks to absolute inst-fs URLs directly).

There is no --publish flag, matching page-create and assign-create: content is
created as a draft and published by hand in Canvas.
"""

from __future__ import annotations

import argparse
import mimetypes
import sys
from pathlib import Path

import requests

from canvas_cli.client import CanvasClient
from canvas_cli.config import Config


def add_arguments(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--course", required=True, help="Course code or numeric ID")
    # --file, not --from-file: elsewhere in this CLI --from-file means "read
    # markdown out of this and turn it into a body". Here the file *is* the
    # object being created.
    sub.add_argument("--file", required=True, help="Path to the local file to upload")
    sub.add_argument(
        "--folder",
        help="Canvas folder path under course files, e.g. 'Slides' (created if missing)",
    )
    sub.add_argument("--name", help="Display name in Canvas (default: the local filename)")
    sub.add_argument(
        "--on-duplicate",
        dest="on_duplicate",
        choices=["overwrite", "rename"],
        default="overwrite",
        help="What to do if a file with the same name exists (default: overwrite)",
    )


def run(args, client: CanvasClient, config: Config) -> int:
    cid = client.resolve_course(args.course)

    path = Path(args.file).expanduser()
    if not path.is_file():
        sys.exit(f"Error: file not found: {path}")
    size = path.stat().st_size
    if size == 0:
        sys.exit(f"Error: {path} is empty — Canvas rejects zero-byte uploads")

    display_name = args.name or path.name
    folder = _normalize_folder(args.folder)

    uploaded = _upload(client, cid, path, display_name, folder, args.on_duplicate)
    fid = uploaded.get("id")
    if not fid:
        sys.exit(f"Upload finished but Canvas returned no file id: {uploaded}")

    base = config.base_url.rstrip("/")

    # Repo rule: never publish programmatically. locked+hidden together pin the
    # state to "unpublished" regardless of what an overwritten file looked like.
    # /files/:id takes flat params — no namespace wrapper, unlike modules.
    try:
        client.put(f"/files/{fid}", {"locked": True, "hidden": False})
    except requests.HTTPError as e:
        print(f"File uploaded (id={fid}) but could NOT be left unpublished: {_error_body(e)}")
        print("  It is currently VISIBLE to students — lock it manually in Canvas.")
        return 1

    print(f"File uploaded (unpublished): '{display_name}'")
    print(f"  ID     : {fid}")
    print(f"  Folder : {uploaded.get('folder_path') or folder or 'course files'}")
    print(f"  Size   : {_human_size(size)}")
    print(f"  Canvas : {base}/courses/{cid}/files/{fid}")
    return 0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _upload(
    client: CanvasClient,
    cid: int,
    path: Path,
    display_name: str,
    folder: str | None,
    on_duplicate: str,
) -> dict:
    """Run the three-step Canvas upload. Returns the final file object."""
    payload: dict = {
        "name": display_name,
        "size": path.stat().st_size,
        "content_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        "on_duplicate": on_duplicate,
    }
    if folder:
        payload["parent_folder_path"] = folder  # created automatically if missing

    # Step 1 — announce the file; Canvas hands back a pre-signed target.
    try:
        ticket = client.post(f"/courses/{cid}/files", payload)
    except requests.HTTPError as e:
        sys.exit(f"Canvas rejected the upload request: {_error_body(e)}")

    upload_url = ticket.get("upload_url")
    upload_params = ticket.get("upload_params") or {}
    file_param = ticket.get("file_param") or "file"
    if not upload_url:
        sys.exit(f"Canvas returned no upload_url: {ticket}")

    # Step 2 — POST the bytes to the pre-signed URL.
    #   * no Authorization header: the URL is already signed, and sending one
    #     makes some storage backends reject the request outright;
    #   * allow_redirects=False: on the legacy path a 3xx *is* the success
    #     signal, and following it would drop the auth needed in step 3.
    with path.open("rb") as fh:
        r = requests.post(
            upload_url,
            data=upload_params,
            files={file_param: (display_name, fh)},
            allow_redirects=False,
        )
    if r.status_code >= 400:
        sys.exit(f"Upload failed ({r.status_code}): {r.text[:500]}")

    # Step 3 — confirm. inst-fs answers 201 with the file object already in the
    # body; the legacy path answers 3xx and the Location must be fetched *with*
    # the Canvas token.
    if 300 <= r.status_code < 400:
        location = r.headers.get("Location")
        if not location:
            sys.exit(f"Upload returned {r.status_code} with no Location header")
        confirm = requests.get(
            location, headers={"Authorization": f"Bearer {client.token}"}
        )
        confirm.raise_for_status()
        return confirm.json()
    return r.json()


def _normalize_folder(folder: str | None) -> str | None:
    """'/Slides/' -> 'Slides'. Nested paths pass through and are auto-created."""
    if folder is None:
        return None
    cleaned = folder.strip().strip("/")
    return cleaned or None


def _human_size(num: int) -> str:
    size = float(num)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def _error_body(e: requests.HTTPError) -> str:
    return (e.response.text or str(e))[:500] if e.response is not None else str(e)
