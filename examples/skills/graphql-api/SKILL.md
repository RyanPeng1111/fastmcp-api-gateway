---
description: Guidance for discovering and querying the company GraphQL API.
---

# GraphQL API guidance

1. Call `graphql_introspect_schema` when the relevant schema is unknown.
2. Build the smallest GraphQL selection set needed for the user request.
3. Pass dynamic values through GraphQL variables rather than interpolating them into the query.
4. Use mutations only when the user clearly requests a data change.
5. When the backend returns GraphQL errors, report them instead of inventing missing data.

