"""GraphQL MCP tool registration and execution."""

from __future__ import annotations

from typing import Any

import httpx
from fastmcp import FastMCP
from graphql import OperationType, get_introspection_query, parse

from .config import Settings
from .headers import build_forward_headers


def _contains_mutation(query: str) -> bool:
    document = parse(query)
    return any(
        getattr(definition, "operation", None) == OperationType.MUTATION
        for definition in document.definitions
    )


async def _execute(
    settings: Settings,
    query: str,
    variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if settings.graphql_endpoint is None:
        raise RuntimeError("GRAPHQL_ENDPOINT is not configured")

    headers = build_forward_headers(extra_denylist=settings.extra_header_denylist)
    headers["Content-Type"] = "application/json"
    async with httpx.AsyncClient(
        timeout=settings.http_timeout_seconds,
        verify=settings.tls_verify,
        follow_redirects=False,
        trust_env=settings.http_trust_env,
    ) as client:
        response = await client.post(
            settings.graphql_endpoint,
            headers=headers,
            json={"query": query, "variables": variables or {}},
        )
        response.raise_for_status()
        payload = response.json()

    if not isinstance(payload, dict):
        raise RuntimeError("GraphQL backend returned a non-object response")
    return payload


def register_graphql_tools(mcp: FastMCP, settings: Settings) -> None:
    if settings.graphql_endpoint is None:
        return

    @mcp.tool(
        name="graphql_introspect_schema",
        description=(
            "Read the GraphQL schema. Call this before graphql_query when the schema "
            "is not already known. Incoming authentication and business headers are "
            "forwarded to the GraphQL backend."
        ),
        tags={"graphql", "schema", "read-only"},
    )
    async def introspect_schema() -> dict[str, Any]:
        return await _execute(settings, get_introspection_query(descriptions=True))

    @mcp.tool(
        name="graphql_query",
        description=(
            "Execute a GraphQL query with optional variables. Incoming authentication "
            "and business headers are forwarded to the GraphQL backend."
        ),
        tags={"graphql"},
    )
    async def query_graphql(
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if _contains_mutation(query) and not settings.allow_graphql_mutations:
            raise ValueError("GraphQL mutations are disabled by ALLOW_GRAPHQL_MUTATIONS")
        return await _execute(settings, query, variables)
