# APIGhost

**OpenAPI spec → mock server with VCR recording**

[![PyPI](https://img.shields.io/pypi/v/apighost)](https://pypi.org/project/apighost/)
[![Python](https://img.shields.io/pypi/pyversions/apighost)](https://pypi.org/project/apighost/)
[![License](https://img.shields.io/pypi/l/apighost)](https://github.com/Coding-Dev-Tools/apighost/blob/main/LICENSE)
[![CI](https://github.com/Coding-Dev-Tools/apighost/actions/workflows/test.yml/badge.svg)](https://github.com/Coding-Dev-Tools/apighost/actions/workflows/test.yml)

Turn any OpenAPI 3.0/3.1 spec into a running mock API server with realistic fake data, scenario-based response overrides, and VCR-style cassette recording/replay.

## Why APIGhost?

Every frontend and integration test needs a mock API. Most teams either hardcode responses (brittle), run a shared staging server (slow, flaky), or hand-write mock configurations (time-consuming). APIGhost reads your OpenAPI spec and **generates a working mock server in seconds** — with realistic fake data, scenario switching for edge cases, and VCR recording for deterministic test replay. When your API spec changes, your mock server updates automatically.

## Quick Start

```bash
# Install
pip install apighost

# Start a mock server from an OpenAPI spec
apighost serve petstore.yaml

# Or run directly from a URL
apighost serve https://raw.githubusercontent.com/OAI/OpenAPI-Specification/main/examples/v3.0/petstore.yaml
```

## Commands

### `apighost serve`
Start a mock server from an OpenAPI spec file.

```bash
apighost serve spec.yaml                    # Default port 8080
apighost serve api.json -p 3000             # Custom port
apighost serve spec.yaml --scenario error    # Use error scenario
apighost serve spec.yaml --record            # Record interactions to cassette
```

### `apighost record`
Start a server, make sample requests, and record them to a cassette.

```bash
apighost record petstore.yaml
apighost record spec.yaml --output my-test-cassette
```

### `apighost replay`
Replay a recorded cassette as a deterministic mock server.

```bash
apighost replay my-recording
apighost replay /path/to/cassette.json -p 3000
```

### `apighost scenario`
Manage response scenarios — named sets of overrides.

```bash
apighost scenario create error-test -d "API error scenarios"
apighost scenario edit error-test "GET /users" --status 500 --body '{"error":"oops"}'
apighost scenario list
apighost scenario delete error-test
```

### `apighost generate`
Generate realistic sample data from an OpenAPI spec into a scenario.

```bash
apighost generate petstore.yaml
```

### `apighost info`
Show APIGhost configuration and storage info.

## Features

- **OpenAPI 3.0/3.1 parsing** — full path, parameter, and response parsing
- **Realistic fake data** — Faker-powered with property name hints (emails, names, IDs)
- **VCR recording** — capture real interactions for deterministic replay
- **Scenario system** — named response presets for testing edge cases
- **Path parameter support** — dynamic URL path resolution
- **Status code selection** — picks appropriate response codes per scenario

## Pricing

| Tier | Price | Features |
|------|-------|----------|
| **Free** | $0 | Unlimited local use, 100 requests/session |
| **Pro** | $12/mo ($119/yr) | Unlimited requests, VCR cassettes, CI/CD integration |
| **Suite** | $49/mo ($499/yr) | All 10 Revenue Holdings tools under one license |

## Storage

Cassettes and scenarios are stored in `~/.apighost/`:
- `~/.apighost/cassettes/` — recorded interaction cassettes (JSON)
- `~/.apighost/scenarios/` — response scenario definitions (JSON)

## Roadmap

- [ ] OpenAPI 3.1 full support (JSON Schema draft 2020-12)
- [ ] Webhook simulation
- [ ] Latency simulation with per-endpoint config
- [ ] Dashboard UI for real-time request inspection
- [ ] MCP server integration for AI-assisted testing
- [ ] Docker image

## Development

```bash
git clone https://github.com/Coding-Dev-Tools/apighost.git
cd apighost
pip install -e ".[dev]"
pytest
```

## License

MIT — see [LICENSE](LICENSE)

---

<sub>Part of [Revenue Holdings](https://coding-dev-tools.github.io/revenueholdings.dev/) — a suite of 10 developer CLI tools built by autonomous AI agents. Also check out [API Contract Guardian](https://github.com/Coding-Dev-Tools/api-contract-guardian) (breaking change detection), [DeployDiff](https://github.com/Coding-Dev-Tools/deploydiff) (infrastructure diffs), [json2sql](https://github.com/Coding-Dev-Tools/json2sql) (JSON → SQL), [ConfigDrift](https://github.com/Coding-Dev-Tools/configdrift) (config drift detection), [DeadCode](https://github.com/Coding-Dev-Tools/deadcode) (dead code cleanup), [APIAuth](https://github.com/Coding-Dev-Tools/apiauth) (API key management), [Envault](https://github.com/Coding-Dev-Tools/envault) (env sync), [SchemaForge](https://github.com/Coding-Dev-Tools/schemaforge) (ORM converter), and [click-to-mcp](https://github.com/Coding-Dev-Tools/click-to-mcp) (CLI → MCP server).</sub>
