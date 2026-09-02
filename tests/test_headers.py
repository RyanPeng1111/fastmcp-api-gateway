import httpx
import pytest

from fastmcp_api_gateway.headers import build_forward_headers, create_forwarding_hook


def test_forwards_business_and_auth_headers() -> None:
    result = build_forward_headers(
        [
            ("SSO-token", "user-jwt"),
            ("SSO-ENV", "prod"),
            ("Authorization", "Bearer client-token"),
            ("X-Trace-Id", "trace-1"),
        ]
    )

    assert result == {
        "SSO-token": "user-jwt",
        "SSO-ENV": "prod",
        "Authorization": "Bearer client-token",
        "X-Trace-Id": "trace-1",
    }


def test_removes_http_and_mcp_control_headers() -> None:
    result = build_forward_headers(
        [
            ("Host", "gateway.internal"),
            ("Content-Type", "application/json"),
            ("Content-Length", "123"),
            ("Mcp-Protocol-Version", "2026-07-28"),
            ("Mcp-Method", "tools/call"),
            ("X-Business", "kept"),
        ]
    )

    assert result == {"X-Business": "kept"}


def test_removes_fields_named_by_connection_header() -> None:
    result = build_forward_headers(
        [
            ("Connection", "X-Internal-Hop, keep-alive"),
            ("X-Internal-Hop", "remove-me"),
            ("X-Business", "keep-me"),
        ]
    )

    assert result == {"X-Business": "keep-me"}


def test_preserves_repeated_header_values() -> None:
    result = build_forward_headers(
        [("X-Role", "reader"), ("X-Role", "writer"), ("Cookie", "a=1"), ("Cookie", "b=2")]
    )

    assert result["X-Role"] == "reader, writer"
    assert result["Cookie"] == "a=1; b=2"


def test_applies_configured_extra_denylist() -> None:
    result = build_forward_headers(
        [("X-Remove", "secret"), ("X-Keep", "value")],
        extra_denylist={"x-remove"},
    )

    assert result == {"X-Keep": "value"}


@pytest.mark.asyncio
async def test_outbound_hook_removes_provider_mcp_metadata() -> None:
    request = httpx.Request(
        "GET",
        "https://backend.example/api",
        headers={
            "Mcp-Protocol-Version": "2026-07-28",
            "Mcp-Method": "tools/call",
            "Mcp-Name": "rest_backendHealth",
        },
    )

    await create_forwarding_hook()(request)

    assert not any(name.lower().startswith("mcp-") for name in request.headers)
