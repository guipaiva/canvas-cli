"""Markdown → Canvas HTML conversion."""

import markdown as _md


def md_to_html(text: str) -> str:
    return _md.markdown(text, extensions=["tables", "fenced_code"])
