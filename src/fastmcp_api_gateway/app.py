"""FastMCP API Gateway ASGI application."""

from __future__ import annotations

from pathlib import Path

import httpx2
from fastmcp import FastMCP
from fastmcp.server.providers.skills import SkillsDirectoryProvider
from starlette.requests import Request
from starlette.responses import JSONResponse

from .config import Settings
from .graphql_tools import register_graphql_tools
from .headers import IncomingHeaderContextMiddleware, create_forwarding_hook
from .spec import load_openapi_spec


def create_mcp(settings: Settings) -> FastMCP:
    gateway = FastMCP(settings.mcp_name)

    if settings.openapi_spec and settings.openapi_base_url:
        spec = load_openapi_spec(
            settings.openapi_spec,
            timeout=settings.http_timeout_seconds,
            verify=settings.tls_verify,
            trust_env=settings.http_trust_env,
        )
        api_client = httpx2.AsyncClient(
            base_url=settings.openapi_base_url,
            timeout=settings.http_timeout_seconds,
            verify=settings.tls_verify,
            follow_redirects=False,
            trust_env=settings.http_trust_env,
            event_hooks={
                "request": [create_forwarding_hook(settings.extra_header_denylist)]
            },
        )
        rest_server = FastMCP.from_openapi(
            openapi_spec=spec,
            client=api_client,
            name="OpenAPI",
        )
        gateway.mount(rest_server, namespace="rest")

    register_graphql_tools(gateway, settings)

    skills_root = Path(settings.skills_dir)
    if skills_root.is_dir():
        gateway.add_provider(
            SkillsDirectoryProvider(
                roots=skills_root,
                supporting_files="template",
                reload=True,
            )
        )

    @gateway.custom_route("/healthz", methods=["GET"])
    async def healthz(_: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return gateway


settings = Settings.from_env()
mcp = create_mcp(settings)
_mcp_app = mcp.http_app(
    path="/mcp",
    stateless_http=True,
    json_response=True,
)
app = IncomingHeaderContextMiddleware(_mcp_app)
