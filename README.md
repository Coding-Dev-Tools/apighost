# APIGhost

[![GitHub stars](https://img.shields.io/github/stars/Coding-Dev-Tools/apighost?style=social)](https://github.com/Coding-Dev-Tools/apighost/stargazers)

**OpenAPI spec → mock server with VCR recording**

> ⭐ **Star this repo** if you build or test APIs — it helps others discover APIGhost!

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://github.com/Coding-Dev-Tools/apighost)
[![License](https://img.shields.io/github/license/Coding-Dev-Tools/apighost)](https://github.com/Coding-Dev-Tools/apighost/blob/main/LICENSE)
[![CI](https://github.com/Coding-Dev-Tools/apighost/actions/workflows/ci.yml/badge.svg)](https://github.com/Coding-Dev-Tools/apighost/actions/workflows/ci.yml)
[![Open Source Alternative](https://img.shields.io/badge/Open_Source_Alternative-%E2%87%92-blue?logo=opensourceinitiative)](https://www.opensourcealternative.to/project/apighost)
[![PyPI](https://img.shields.io/pypi/v/apighost)](https://pypi.org/project/apighost/)

## Why APIGhost?

Every frontend and integration test needs a mock API. Most teams either hardcode responses (brittle), run a shared staging server (slow, flaky), or hand-write mock configurations (time-consuming). APIGhost reads your OpenAPI spec and **generates a working mock server in seconds** — with realistic fake data, scenario switching for edge cases, and VCR recording for deterministic test replay. When your API spec changes, your mock server updates automatically.

## Installation

**pip (Python):**
```bash
pip install git+https://github.com/Coding-Dev-Tools/apighost.git
```

**Homebrew (macOS/Linux):**
```bash
brew tap Coding-Dev-Tools/tap
brew install apighost
```

**Scoop (Windows):**
```bash
scoop bucket add Coding-Dev-Tools https://github.com/Coding-Dev-Tools/scoop-bucket
scoop install apighost
```

## Quick Start

```bash
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

## CI/CD Integration

```yaml
# GitHub Actions — start mock API for integration tests
- name: Start mock API
  run: |
    apighost serve api-spec.yaml -p 8080 &
    sleep 2

- name: Run integration tests against mock
  run: pytest tests/integration/
```

```bash
# Deterministic replay — no flaky tests
apighost record petstore.yaml                    # Record once
apighost replay my-recording -p 8080            # Replay forever, same responses
```

## Alternatives Comparison

| Feature | APIGhost | Prism | WireMock | Mockoon |
|---------|----------|-------|----------|---------|
| OpenAPI ? mock server | ? | ? | ? | ? |
| VCR record/replay | ? | ? | ? | ? |
| Scenario switching | ? | ? | ? | ? |
| Realistic fake data | ? | ? | ? | ? |
| Zero-config from spec | ? | ? | ? | ? |
| CLI-first (no GUI) | ? | ? | ? | ? |
| Spec change auto-sync | ? | ? | ? | ? |

**APIGhost vs Prism**: Prism generates mock responses but can't record/replay or switch scenarios. APIGhost adds VCR cassettes and scenario presets.

**APIGhost vs WireMock**: WireMock requires hand-coded stubs. APIGhost generates everything from your OpenAPI spec — zero config.

**APIGhost vs Mockoon**: Mockoon needs a GUI. APIGhost is CLI-first — perfect for CI and headless environments.

## Pricing

| Tier | Price | Features |
|------|-------|----------|
| **Free** | $0 | Unlimited local use, 100 requests/session |
| **Pro** | $12/mo ($119/yr) | Unlimited requests, VCR cassettes, CI/CD integration |
| **Suite** | $49/mo ($39 billed annually) | All tools in the Coding-Dev-Tools ecosystem under one license |

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

<sub>Part of the [Coding-Dev-Tools](https://github.com/Coding-Dev-Tools) ecosystem — a suite of developer CLI tools. Also check out [API Contract Guardian](https://github.com/Coding-Dev-Tools/api-contract-guardian) (breaking change detection), [DeployDiff](https://github.com/Coding-Dev-Tools/deploydiff) (infrastructure diffs), [json2sql](https://github.com/Coding-Dev-Tools/json2sql) (JSON → SQL), [ConfigDrift](https://github.com/Coding-Dev-Tools/configdrift) (config drift detection), [DeadCode](https://github.com/Coding-Dev-Tools/deadcode) (dead code cleanup), [Envault](https://github.com/Coding-Dev-Tools/envault) (env sync), [SchemaForge](https://github.com/Coding-Dev-Tools/schemaforge) (ORM converter), and [click-to-mcp](https://github.com/Coding-Dev-Tools/click-to-mcp) (CLI → MCP server).</sub>

# CI Trigger
# CI trigger
