from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _boolean(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false")


def _positive_float(name: str, default: float) -> float:
    value = float(os.getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    mcp_name: str
    openapi_spec: str | None
    openapi_base_url: str | None
    graphql_endpoint: str | None
    allow_graphql_mutations: bool
    skills_dir: Path
    http_timeout_seconds: float
    http_trust_env: bool
    tls_verify: bool
    extra_header_denylist: frozenset[str]

    @classmethod
    def from_env(cls) -> "Settings":
        openapi_spec = os.getenv("OPENAPI_SPEC") or None
        openapi_base_url = os.getenv("OPENAPI_BASE_URL") or None
        graphql_endpoint = os.getenv("GRAPHQL_ENDPOINT") or None
        extra_denylist = frozenset(
            item.strip().lower()
            for item in os.getenv("FORWARD_HEADER_DENYLIST", "").split(",")
            if item.strip()
        )

        if bool(openapi_spec) != bool(openapi_base_url):
            raise ValueError(
                "OPENAPI_SPEC and OPENAPI_BASE_URL must either both be set or both be omitted"
            )

        return cls(
            mcp_name=os.getenv("MCP_NAME", "company-api-gateway"),
            openapi_spec=openapi_spec,
            openapi_base_url=openapi_base_url,
            graphql_endpoint=graphql_endpoint,
            allow_graphql_mutations=_boolean("ALLOW_GRAPHQL_MUTATIONS", False),
            skills_dir=Path(os.getenv("SKILLS_DIR", "/app/skills")),
            http_timeout_seconds=_positive_float("HTTP_TIMEOUT_SECONDS", 60.0),
            http_trust_env=_boolean("HTTP_TRUST_ENV", False),
            tls_verify=_boolean("TLS_VERIFY", True),
            extra_header_denylist=extra_denylist,
        )
