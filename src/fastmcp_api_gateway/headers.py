"""Request-scoped upstream header forwarding."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterable
from contextvars import ContextVar
from typing import Any

import httpx

# RFC 9110/9112 hop-by-hop fields plus HTTP representation and MCP envelope
# fields that belong to the MCP request, not to the upstream API request.
DEFAULT_DENYLIST = frozenset(
    {
        "accept",
        "accept-encoding",
        "connection",
        "content-length",
        "content-type",
        "host",
        "keep-alive",
        "last-event-id",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)

_incoming_headers: ContextVar[tuple[tuple[str, str], ...]] = ContextVar(
    "incoming_mcp_headers", default=()
)


def current_incoming_headers() -> tuple[tuple[str, str], ...]:
    return _incoming_headers.get()


def build_forward_headers(
    incoming: Iterable[tuple[str, str]] | None = None,
    extra_denylist: Iterable[str] = (),
) -> dict[str, str]:
    """Return safe end-to-end headers while preserving all values.

    Repeated fields are combined according to common HTTP rules. Cookie uses
    semicolon separation; all other repeated fields use commas. Fields named by
    the Connection header are also removed as required by HTTP.
    """

    source = tuple(incoming if incoming is not None else current_incoming_headers())
    blocked = set(DEFAULT_DENYLIST)
    blocked.update(name.lower() for name in extra_denylist)
    blocked.update(name.lower() for name, _ in source if name.lower().startswith("mcp-"))

    for name, value in source:
        if name.lower() == "connection":
            blocked.update(token.strip().lower() for token in value.split(",") if token.strip())

    grouped: dict[str, list[str]] = defaultdict(list)
    original_case: dict[str, str] = {}
    for name, value in source:
        lowered = name.lower()
        if lowered in blocked:
            continue
        original_case.setdefault(lowered, name)
        grouped[lowered].append(value)

    result: dict[str, str] = {}
    for lowered, values in grouped.items():
        separator = "; " if lowered == "cookie" else ", "
        result[original_case[lowered]] = separator.join(values)
    return result


class IncomingHeaderContextMiddleware:
    """Capture request headers in a concurrency-safe ContextVar."""

    def __init__(self, app: Callable[..., Awaitable[Any]]) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        headers = tuple(
            (name.decode("latin-1"), value.decode("latin-1"))
            for name, value in scope.get("headers", [])
        )
        token = _incoming_headers.set(headers)
        try:
            await self.app(scope, receive, send)
        finally:
            _incoming_headers.reset(token)


def create_forwarding_hook(
    extra_denylist: Iterable[str] = (),
) -> Callable[[httpx.Request], Awaitable[None]]:
    denylist = tuple(extra_denylist)

    async def forward_headers(request: httpx.Request) -> None:
        # FastMCP's OpenAPI provider may mirror modern MCP routing metadata to
        # the generated upstream tool request. The Spring backend is not an MCP
        # hop, so remove that envelope metadata at the final outbound boundary.
        for name in tuple(request.headers.keys()):
            lowered = name.lower()
            if lowered.startswith("mcp-") or lowered == "last-event-id":
                del request.headers[name]

        for name, value in build_forward_headers(extra_denylist=denylist).items():
            request.headers[name] = value

    return forward_headers
