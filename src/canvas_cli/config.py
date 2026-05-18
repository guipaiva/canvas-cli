"""Config loader — 4-layer resolution: config file → env var → CLI flag."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore


@dataclass
class Config:
    base_url: str = ""
    token: str = ""
    aliases: dict[str, int] = field(default_factory=dict)


def _find_project_config(start: Path | None = None) -> Path | None:
    """Walk up from start (default cwd) looking for .canvas.toml."""
    current = (start or Path.cwd()).resolve()
    for directory in [current, *current.parents]:
        candidate = directory / ".canvas.toml"
        if candidate.exists():
            return candidate
    return None


def _load_toml(path: Path) -> dict:
    if tomllib is None:
        print(
            f"Warning: cannot parse {path} (tomllib not available; install tomli on Python <3.11)",
            file=sys.stderr,
        )
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def load_config(args=None) -> Config:
    """
    Resolution order (high → low priority):
    1. CLI flags (args.base_url, args.token)
    2. Env vars (CANVAS_BASE_URL, CANVAS_API_TOKEN)
    3. Project config (.canvas.toml walking up from cwd)
    4. User config (~/.config/canvas-cli/config.toml)
    """
    cfg = Config()

    # --- Layer 4: user config ---
    user_cfg_path = Path.home() / ".config" / "canvas-cli" / "config.toml"
    if user_cfg_path.exists():
        data = _load_toml(user_cfg_path)
        cfg.base_url = data.get("canvas", {}).get("base_url", "")
        cfg.aliases.update({k.upper(): v for k, v in data.get("aliases", {}).items()})

    # --- Layer 3: project config ---
    proj_cfg_path = _find_project_config()
    if proj_cfg_path:
        data = _load_toml(proj_cfg_path)
        canvas_section = data.get("canvas", {})
        if canvas_section.get("base_url"):
            cfg.base_url = canvas_section["base_url"]
        cfg.aliases.update({k.upper(): v for k, v in data.get("aliases", {}).items()})

    # --- Layer 2: env vars ---
    if os.environ.get("CANVAS_BASE_URL"):
        cfg.base_url = os.environ["CANVAS_BASE_URL"]
    if os.environ.get("CANVAS_API_TOKEN"):
        cfg.token = os.environ["CANVAS_API_TOKEN"]

    # --- Layer 1: CLI flags ---
    if args is not None:
        if getattr(args, "base_url", None):
            cfg.base_url = args.base_url
        if getattr(args, "token", None):
            cfg.token = args.token

    return cfg
