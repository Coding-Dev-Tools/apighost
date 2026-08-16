"""Regression test: all GitHub Actions uses: directives must be SHA-pinned.

Mutable tags like @v4 or @main are a supply-chain attack vector: a compromised
upstream tag silently changes what CI runs. Every action reference in
.github/workflows/*.yml must use a 40-char commit SHA (optionally followed by
an inline comment documenting the version).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

# 40 hex chars, optionally followed by whitespace and an inline comment
SHA_PIN_RE = re.compile(r"@[0-9a-f]{40}(\s+#.*)?$")

# Org-internal reusable workflows (same org controls the ref) are exempt.
# Third-party actions always require SHA pins.
EXEMPT_PREFIXES = (
    "Coding-Dev-Tools/",  # same-org reusable workflows
)


def _workflow_files() -> list[Path]:
    if not WORKFLOWS_DIR.is_dir():
        return []
    return sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))


@pytest.mark.parametrize("workflow", _workflow_files(), ids=lambda p: p.name)
def test_all_actions_are_sha_pinned(workflow: Path) -> None:
    """Every uses: directive must reference an immutable 40-char SHA."""
    violations: list[str] = []
    for lineno, raw_line in enumerate(workflow.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line.startswith("uses:"):
            continue
        # Strip the 'uses:' prefix and any inline comment outside the ref
        value = line[len("uses:"):].strip()
        # Skip exempt org-internal reusable workflows
        if any(value.startswith(pfx) for pfx in EXEMPT_PREFIXES):
            continue
        if not SHA_PIN_RE.search(value):
            violations.append(f"{workflow.name}:{lineno}: {raw_line.strip()}")
    assert not violations, (
        "Mutable action references found — pin to a 40-char commit SHA:\n"
        + "\n".join(violations)
    )
