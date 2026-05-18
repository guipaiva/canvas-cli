"""Filesystem utilities."""

import re


def safe_dirname(name: str) -> str:
    """Sanitize a student/group name for use as a directory name."""
    return re.sub(r"[^\w\s-]", "", name).strip().replace(" ", "_")
