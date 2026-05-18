"""Smoke tests — verify the CLI wires up correctly without hitting Canvas."""

import pytest
from canvas_cli.cli import build_parser
from canvas_cli.config import load_config
from canvas_cli.client import CanvasClient


EXPECTED_COMMANDS = {
    "submissions", "download", "assignments", "roster", "grade",
    "post-grades", "page-create", "page-update", "assign-create", "announce",
}


def test_parser_builds():
    p = build_parser()
    assert p is not None


def test_all_subcommands_registered():
    p = build_parser()
    subactions = next(a for a in p._actions if hasattr(a, "_name_parser_map"))
    registered = set(subactions._name_parser_map.keys())
    assert registered == EXPECTED_COMMANDS


def test_config_loads_defaults():
    cfg = load_config()
    assert isinstance(cfg.aliases, dict)
    assert isinstance(cfg.base_url, str)


def test_client_resolve_alias():
    client = CanvasClient(
        base_url="https://example.instructure.com",
        token="fake",
        aliases={"MY-COURSE": 99999},
    )
    assert client.resolve_course("MY-COURSE") == 99999
    assert client.resolve_course("99999") == 99999


def test_client_resolve_raw_id():
    client = CanvasClient(
        base_url="https://example.instructure.com",
        token="fake",
        aliases={},
    )
    assert client.resolve_course("12345") == 12345


def test_client_unknown_alias_exits():
    client = CanvasClient(
        base_url="https://example.instructure.com",
        token="fake",
        aliases={},
    )
    with pytest.raises(SystemExit):
        client.resolve_course("UNKNOWN-COURSE")
