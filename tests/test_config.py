import pytest

from fastmcp_api_gateway.config import Settings


def test_openapi_settings_must_be_paired(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAPI_SPEC", "/config/openapi.json")
    monkeypatch.delenv("OPENAPI_BASE_URL", raising=False)

    with pytest.raises(ValueError, match="must either both be set"):
        Settings.from_env()


def test_minimal_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("OPENAPI_SPEC", "OPENAPI_BASE_URL", "GRAPHQL_ENDPOINT"):
        monkeypatch.delenv(key, raising=False)

    settings = Settings.from_env()

    assert settings.mcp_name == "fastmcp-api-gateway"
    assert settings.allow_graphql_mutations is False
