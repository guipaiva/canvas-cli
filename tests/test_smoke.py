"""Smoke tests — verify the CLI wires up correctly without hitting Canvas."""

import pytest
from canvas_cli.cli import build_parser
from canvas_cli.config import load_config
from canvas_cli.client import CanvasClient
from canvas_cli.commands.file_upload import _human_size, _normalize_folder
from canvas_cli.commands.module_item_add import _build_item, _pick_module
from canvas_cli.commands.modules import _truncate


EXPECTED_COMMANDS = {
    "submissions", "download", "assignments", "roster", "grade",
    "post-grades", "page-create", "page-update", "assign-create", "announce",
    "modules", "module-create", "file-upload", "module-item-add",
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


# ---------------------------------------------------------------------------
# file-upload / modules / module-create / module-item-add
#
# The HTTP is exercised against real Canvas every week; what is worth pinning
# here is the pure logic — payload nesting, type dispatch, module lookup — none
# of which needs mocking.
# ---------------------------------------------------------------------------


def _parse(argv):
    return build_parser().parse_args(argv)


def test_file_upload_defaults():
    a = _parse(["file-upload", "--course", "C", "--file", "deck.pdf"])
    assert a.on_duplicate == "overwrite"
    assert a.folder is None
    assert a.name is None


def test_file_upload_requires_file():
    with pytest.raises(SystemExit):
        _parse(["file-upload", "--course", "C"])


def test_normalize_folder():
    assert _normalize_folder("/Slides/") == "Slides"
    assert _normalize_folder("Slides/Bloco A") == "Slides/Bloco A"
    assert _normalize_folder("  ") is None
    assert _normalize_folder(None) is None


def test_human_size():
    assert _human_size(512) == "512 B"
    assert _human_size(1170886) == "1.1 MB"


def test_modules_defaults():
    assert _parse(["modules", "--course", "C"]).no_items is False
    assert _parse(["modules", "--course", "C", "--no-items"]).no_items is True


def test_module_create_defaults():
    assert _parse(["module-create", "--course", "C", "--name", "Bloco A"]).position is None


def test_truncate():
    assert _truncate("short", 60) == "short"
    long = "x" * 100
    assert len(_truncate(long, 60)) == 60
    assert _truncate(long, 60).endswith("…")


def test_item_type_normalisation():
    assert _parse(_item_argv(["--type", "subheader"])).type == "SubHeader"
    assert _parse(_item_argv(["--type", "external-url", "--url", "https://a.b"])).type == "ExternalUrl"


def test_item_rejects_unknown_type():
    with pytest.raises(SystemExit):
        _parse(_item_argv(["--type", "Quiz"]))


def test_build_item_subheader():
    args = _parse(_item_argv(["--type", "SubHeader"]))
    assert _build_item(args) == {
        "module_item": {"title": "T", "type": "SubHeader", "indent": 0}
    }


def test_build_item_file_is_nested():
    """Regression guard: the client sends json=, so Canvas needs a real nested
    object. Rails bracket keys ('module_item[title]') 400 with no explanation."""
    args = _parse(_item_argv(["--type", "File", "--content-id", "42", "--indent", "1"]))
    assert _build_item(args) == {
        "module_item": {"title": "T", "type": "File", "indent": 1, "content_id": 42}
    }


def test_build_item_page_uses_page_url():
    args = _parse(_item_argv(["--type", "Page", "--page-url", "aula-1"]))
    assert _build_item(args)["module_item"]["page_url"] == "aula-1"
    assert "content_id" not in _build_item(args)["module_item"]


def test_build_item_external_url():
    args = _parse(_item_argv(["--type", "ExternalUrl", "--url", "https://dart.dev", "--new-tab"]))
    item = _build_item(args)["module_item"]
    assert item["external_url"] == "https://dart.dev"
    assert item["new_tab"] is True


@pytest.mark.parametrize("extra", [
    ["--type", "File"],                                    # missing --content-id
    ["--type", "SubHeader", "--url", "https://a.b"],       # flag the type ignores
    ["--type", "Page", "--content-id", "1"],               # Page takes --page-url
    ["--type", "SubHeader", "--indent", "9"],              # out of range
    ["--type", "ExternalUrl", "--url", "ftp://a.b"],       # not http(s)
    ["--type", "File", "--content-id", "1", "--new-tab"],  # new-tab is url-only
])
def test_build_item_rejects_bad_combinations(extra):
    with pytest.raises(SystemExit):
        _build_item(_parse(_item_argv(extra)))


_MODULES = [
    {"id": 153360, "name": "Bloco A — Dart"},
    {"id": 153361, "name": "Bloco B — Flutter"},
    {"id": 153362, "name": "Bloco C — Firebase"},
]


def test_pick_module_by_id():
    assert _pick_module("153361", _MODULES)["name"] == "Bloco B — Flutter"


def test_pick_module_by_substring_without_em_dash():
    assert _pick_module("bloco a", _MODULES)["id"] == 153360


@pytest.mark.parametrize("ref", ["999999", "Bloco", "nao-existe"])
def test_pick_module_failures(ref):
    """Unknown id, ambiguous substring, and no match all exit rather than guess."""
    with pytest.raises(SystemExit):
        _pick_module(ref, _MODULES)


def _item_argv(extra):
    return ["module-item-add", "--course", "C", "--module", "M", "--title", "T"] + extra
