"""OpenAPI document loading and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml


def _parse_spec(content: str, source: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content) if source.lower().endswith(".json") else yaml.safe_load(content)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ValueError(f"Unable to parse OpenAPI document from {source}: {exc}") from exc

    if not isinstance(parsed, dict) or "openapi" not in parsed:
        raise ValueError(f"{source} is not an OpenAPI 3 document")
    return parsed


def load_openapi_spec(
    source: str,
    timeout: float,
    verify: bool,
    trust_env: bool = False,
) -> dict[str, Any]:
    parsed_uri = urlparse(source)
    if parsed_uri.scheme in {"http", "https"}:
        with httpx.Client(
            timeout=timeout,
            verify=verify,
            follow_redirects=False,
            trust_env=trust_env,
        ) as client:
            response = client.get(source)
            response.raise_for_status()
            return _parse_spec(response.text, source)

    path = Path(source)
    if not path.is_file():
        raise FileNotFoundError(f"OpenAPI document not found: {path}")
    return _parse_spec(path.read_text(encoding="utf-8"), str(path))
