# Changelog

## v0.2.0 (2026-05-18)

### Added
- `--host` option to `serve` command for binding to custom addresses
- `--latency` option to `serve` for simulated response delay
- `--watch` option to `serve` for spec file auto-reload
- `--cassette-name` option to `serve` for naming recorded cassettes
- `cassette list` and `cassette info` subcommands for managing recordings
- License gating via `revenueholdings-license` package
- CONTRIBUTING.md with development guidelines
- Ruff linting CI step
- Directory listing badges (Open Source Alternative, LibHunt, Awesome Python)
- Star badge and call-to-action in README header
- Pricing table and Revenue Holdings branding
- CI/CD integration examples in README
- Alternatives comparison table (Prism, WireMock, Mockoon)
- Sibling tool cross-links in README footer

### Changed
- Improved README marketing copy with better CI/CD examples
- Safe fallback import for `revenueholdings-license` (graceful degradation)
- Ruff lint fixes: `datetime.UTC`, `X | None` syntax, suppressed `E501`, `B904`, `F821`
- Removed BOM from config files

### Security
- Sensitive header stripping in VCR recordings (Authorization, Cookie, X-API-Key)

### Build
- Dependabot: bump `actions/checkout` from 4 to 6
- Dependabot: bump `actions/setup-python` from 5 to 6

## v0.1.0 (2024)

- Initial release
- OpenAPI 3.0/3.1 spec parsing
- Mock server with realistic fake data (Faker-powered)
- VCR-style cassette recording and replay
- Scenario system with named response overrides
- CLI commands: serve, record, replay, generate, scenario, cassette, info
- Flask-based mock server with threaded support
- Path parameter resolution
- Property name hinting for realistic data generation
- Sensitive header stripping in recordings
