# FastMCP API Gateway

A small, stateless gateway that exposes an existing Spring Boot OpenAPI API and
GraphQL endpoint through one MCP endpoint. It also serves ConfigMap-mounted
agent skills as MCP resources.

## What this first version provides

- FastMCP 4.0.0 and MCP 2026-07-28 sessionless HTTP support.
- OpenAPI operations exposed as namespaced MCP tools through FastMCP's native
  OpenAPI provider.
- Two GraphQL tools: `graphql_introspect_schema` and `graphql_query`.
- Request-scoped forwarding of authentication and business headers to both
  REST and GraphQL backends.
- Skills exposed from `SKILL.md` directories as `skill://` MCP resources.
- No database, persistent MCP session, Vault integration, or stored backend
  credentials.

The MCP endpoint is `POST /mcp`; the health endpoint is `GET /healthz`.

## Header behavior

All end-to-end business and authentication headers are forwarded with their
values, including `SSO-token`, `SSO-ENV`, `Authorization`, cookies and trace
headers. The gateway does not inspect or persist their values.

The following cannot safely be forwarded because they describe the MCP/HTTP
envelope rather than the upstream API request:

- HTTP hop-by-hop fields such as `Connection`, `Transfer-Encoding`, `TE` and
  `Upgrade`.
- Request framing/representation fields such as `Host`, `Content-Length`,
  `Content-Type`, `Accept` and `Accept-Encoding`; the upstream HTTP client
  calculates these for the actual REST or GraphQL request.
- MCP fields beginning with `Mcp-`, plus `Last-Event-ID`.
- Any field named by the incoming `Connection` header.

Add company-specific exclusions through `FORWARD_HEADER_DENYLIST`, for example:

```text
FORWARD_HEADER_DENYLIST=x-internal-proxy,x-untrusted-identity
```

The ingress must remove or replace spoofable proxy identity fields such as
`Forwarded` and `X-Forwarded-For` if a backend trusts them.

## Configuration

| Variable | Required | Meaning |
| --- | --- | --- |
| `OPENAPI_SPEC` | With `OPENAPI_BASE_URL` | Local JSON/YAML path or unauthenticated HTTP(S) URL |
| `OPENAPI_BASE_URL` | With `OPENAPI_SPEC` | REST backend base URL |
| `GRAPHQL_ENDPOINT` | No | GraphQL backend endpoint |
| `ALLOW_GRAPHQL_MUTATIONS` | No | Defaults to `false` |
| `SKILLS_DIR` | No | Defaults to `/app/skills` |
| `HTTP_TIMEOUT_SECONDS` | No | Defaults to `60` |
| `HTTP_TRUST_ENV` | No | Defaults to `false`; enable only when outbound calls must use Pod proxy variables |
| `TLS_VERIFY` | No | Defaults to `true` |
| `FORWARD_HEADER_DENYLIST` | No | Comma-separated additional exclusions |

If `/v3/api-docs` requires authentication, mount its downloaded OpenAPI file
from a ConfigMap. The gateway intentionally has no startup credential with
which to download a protected document. Runtime tool calls still forward the
current user's request headers to the backend.

## Run locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'

export OPENAPI_SPEC=examples/openapi.json
export OPENAPI_BASE_URL=http://localhost:8081
export GRAPHQL_ENDPOINT=http://localhost:8081/graphql
export SKILLS_DIR=examples/skills

uvicorn fastmcp_api_gateway.app:app --host 0.0.0.0 --port 8080
```

Connect Roo Code or another MCP client to:

```text
http://localhost:8080/mcp
```

The client must include `SSO-token` and any other required headers on every MCP
HTTP request. With MCP 2026-07-28 each request is independent. FastMCP also
uses stateless handling for legacy Streamable HTTP clients.

## Build and deploy

### Pull the prebuilt test image

The `main` branch is published only after tests pass, the amd64 image is below
2 GiB, and Trivy reports no Critical vulnerabilities:

```bash
docker pull ghcr.io/ryanpeng1111/fastmcp-api-gateway:0.1.0
```

The first GHCR package created by GitHub may be private even when this source
repository is public. In that case, change the package visibility to Public in
GitHub before pulling it anonymously from the company network.

To mirror the verified image into Harbor:

```bash
docker tag ghcr.io/ryanpeng1111/fastmcp-api-gateway:0.1.0 \
  harbor.example.local/ai/fastmcp-api-gateway:0.1.0
docker push harbor.example.local/ai/fastmcp-api-gateway:0.1.0
```

### Build locally

```bash
docker build -t fastmcp-api-gateway:0.1.0 .
docker run --rm -p 8080:8080 \
  -e OPENAPI_SPEC=/config/openapi.json \
  -e OPENAPI_BASE_URL=http://host.docker.internal:8081 \
  -e GRAPHQL_ENDPOINT=http://host.docker.internal:8081/graphql \
  -v "$PWD/examples/openapi.json:/config/openapi.json:ro" \
  -v "$PWD/examples/skills:/app/skills:ro" \
  fastmcp-api-gateway:0.1.0
```

Edit the image and backend URLs in `deploy/k8s.yaml`, then apply it:

```bash
kubectl apply -f deploy/k8s.yaml
```

No PVC or sticky session is required. The example starts two replicas.

## Skills compatibility

Each directory under `SKILLS_DIR` containing `SKILL.md` becomes a discoverable
MCP resource, for example:

```text
skill://rest-api/SKILL.md
skill://graphql-api/SKILL.md
```

The MCP client must support resources/Skills discovery to inject these into its
model context. A server cannot force an arbitrary client to read a resource.

## Verification

Run unit tests:

```bash
pytest
```

Fail the pipeline if the exact built image has a Critical vulnerability:

```bash
scripts/trivy-scan.sh fastmcp-api-gateway:0.1.0
```

The project cannot guarantee future CVE status. Scan every rebuilt image in the
company Harbor pipeline and block promotion when this command fails.

## First-version limitations

- GraphQL uses two generic tools rather than generating one tool per operation.
- OpenAPI components are generated at startup, so protected specs must be
  mounted locally.
- Skills are delivered as MCP resources; automatic model injection depends on
  the company's MCP client implementation.
- The gateway itself does not authenticate callers. Backend authorization still
  protects API execution, but tool schemas and Skills are visible to any caller
  that can reach the MCP endpoint. Restrict it with Kubernetes NetworkPolicy or
  add gateway authentication if those definitions are sensitive.
