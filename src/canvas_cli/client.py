"""CanvasClient — HTTP + pagination + auth + course resolution."""

import sys

import requests


class CanvasClient:
    def __init__(self, base_url: str, token: str, aliases: dict[str, int]):
        self._base = base_url.rstrip("/") + "/api/v1"
        self._token = token
        self._aliases = aliases

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    def get_all(self, path: str, params: dict | None = None) -> list:
        url = f"{self._base}{path}"
        results = []
        while url:
            r = requests.get(url, headers=self._headers, params=params)
            r.raise_for_status()
            results.extend(r.json())
            url = r.links.get("next", {}).get("url")
            params = None
        return results

    def post(self, path: str, payload: dict) -> dict:
        r = requests.post(f"{self._base}{path}", headers=self._headers, json=payload)
        r.raise_for_status()
        return r.json()

    def put(self, path: str, payload: dict) -> dict:
        r = requests.put(f"{self._base}{path}", headers=self._headers, json=payload)
        r.raise_for_status()
        return r.json()

    def get(self, path: str, params: dict | None = None) -> dict:
        r = requests.get(f"{self._base}{path}", headers=self._headers, params=params)
        r.raise_for_status()
        return r.json()

    def resolve_course(self, code_or_id: str) -> int:
        """Accept an alias from config or a raw numeric Canvas course ID."""
        if code_or_id.isdigit():
            return int(code_or_id)
        cid = self._aliases.get(code_or_id.upper())
        if not cid:
            sys.exit(
                f"Unknown course code '{code_or_id}'.\n"
                f"Add it to your .canvas.toml [aliases] or pass a raw course ID.\n"
                f"Known aliases: {', '.join(self._aliases) or '(none configured)'}"
            )
        return cid

    @classmethod
    def from_config(cls, config: "Config") -> "CanvasClient":  # noqa: F821
        if not config.base_url:
            sys.exit(
                "Error: Canvas base URL not set.\n"
                "Set CANVAS_BASE_URL env var, pass --base-url, or add to .canvas.toml:\n"
                "  [canvas]\n  base_url = \"https://your-institution.instructure.com\""
            )
        if not config.token:
            sys.exit(
                "Error: CANVAS_API_TOKEN not set.\n"
                "Set it in your environment or .env file.\n"
                "Generate at Canvas → Account (avatar) → Settings → Approved Integrations → + New Access Token"
            )
        return cls(config.base_url, config.token, config.aliases)
