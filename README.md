# APIGhost

**OpenAPI spec → mock server with VCR recording**

[![PyPI](https://img.shields.io/pypi/v/apighost)](https://pypi.org/project/apighost/)
[![Python](https://img.shields.io/pypi/pyversions/apighost)](https://pypi.org/project/apighost/)
[![License](https://img.shields.io/pypi/l/apighost)](https://github.com/Coding-Dev-Tools/apighost/blob/main/LICENSE)

**Why APIGhost?** Mocking APIs shouldn't require standing up a separate server or hand-crafting responses. APIGhost reads your OpenAPI 3.0/3.1 spec and instantly becomes a running mock server with realistic fake data. Need to test error handling? Use scenarios to override any endpoint's response. Need deterministic tests? Record interactions to VCR cassettes and replay them. No configuration files, no Docker containers — just a spec and a single command.

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

## CI/CD Integration

```bash
# Start mock server, run tests, then tear down
apighost serve spec.yaml -p 3000 &
pytest integration/
kill %1

# Record real interactions, replay in CI
apighost record spec.yaml --output test-cassette
# Commit test-cassette/ — replay anywhere:
apighost replay test-cassette -p 3000
```

## Pricing

APIGhost is one of eight tools in the Revenue Holdings suite. One license covers all CLI tools.

| Plan | Price | Best For |
|------|-------|----------|
| **Free** | $0 | Individual devs, OSS — CLI only, 5 scenarios |
| **APIGhost Individual** | **$12/mo** ($10 billed annually) | Professional devs — unlimited scenarios, VCR recording |
| **Suite (all 8 tools)** | **$49/mo** ($39 billed annually) | Full Revenue Holdings toolkit — 40% savings |
| **Team** | **$79/mo** ($63 billed annually) | Up to 5 devs — shared scenarios, team dashboard, alerts |
| **Enterprise** | Custom | SSO, RBAC, compliance reports, dedicated support |

🔹 **No lock-in**: CLI works fully offline on the free tier — no telemetry, no phone-home.
🔹 **Annual billing**: Save 20%.

### Per-Tier Features

| Feature | Free | Individual | Suite | Team | Enterprise |
|---------|:----:|:----------:|:-----:|:----:|:----------:|
| CLI: serve, replay | ✓ | ✓ | ✓ | ✓ | ✓ |
| Unlimited endpoints | — | ✓ | ✓ | ✓ | ✓ |
| VCR recording / replay | — | ✓ | ✓ | ✓ | ✓ |
| Custom scenarios | 5 | Unlimited | Unlimited | Unlimited | Unlimited |
| Faker-powered mock data | — | ✓ | ✓ | ✓ | ✓ |
| Shared team scenarios | — | — | — | ✓ | ✓ |
| Dashboard & analytics | — | — | — | ✓ | ✓ |
| Compliance reports | — | — | — | — | ✓ |
| RBAC / SSO / SAML / OIDC | — | — | — | — | ✓ |
| Priority support | Community | 24h | 24h | 8h | Dedicated |

---

<p align="center">
  <sub>Part of <a href="https://coding-dev-tools.github.io/revenueholdings.dev/">Revenue Holdings</a> — CLI tools built by autonomous AI.</sub>
</p>

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

## License

MIT — see [LICENSE](LICENSE)
