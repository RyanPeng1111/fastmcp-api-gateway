import pytest
from graphql.error import GraphQLSyntaxError

from company_mcp_gateway.graphql_tools import _contains_mutation


def test_detects_mutation() -> None:
    assert _contains_mutation("mutation Update($id: ID!) { update(id: $id) { id } }")


def test_allows_query() -> None:
    assert not _contains_mutation("query Read { viewer { id } }")


def test_rejects_invalid_graphql() -> None:
    with pytest.raises(GraphQLSyntaxError):
        _contains_mutation("query {")

