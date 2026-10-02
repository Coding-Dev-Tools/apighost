# apighost

## Purpose
CLI tool that reads an OpenAPI spec and spawns a realistic mock API server with VCR cassette recording and replay — OpenAPI spec → mock server with VCR recording.

## Build & Test Commands
- Install: `pip install -e .` or `pip install git+https://github.com/Coding-Dev-Tools/apighost.git`
- Test: `pytest tests/` (or `python -m pytest tests/ -v --tb=short`)
- Lint: `ruff check src/ tests/`
- Build: `pip install build twine && python -m build && twine check dist/*`
- CLI check: `apighost --help`

## Architecture
Key directories:
- `src/apighost/` — Main package (CLI, OpenAPI parser, mock server, VCR recorder, scenarios)
- `tests/` — Test suite
- `.github/workflows/` — CI/CD (auto-code-review.yml, ci.yml, pages.yml, publish.yml)
- `dist/` — Built distributions

## Conventions
- Language: Python 3.10+
- Test framework: pytest
- CI: GitHub Actions (lint job + test job with matrix: Python 3.10, 3.11, 3.12, 3.13)
- Linting: ruff (line-length 120, target py310)
- Formatting: ruff
- Package layout: src/ layout with setuptools
- Dependencies: click, pyyaml, faker, flask, rich, requests, jsonschema, werkzeug
- CLI entry point: apighost.cli:cli
- Master branch: master