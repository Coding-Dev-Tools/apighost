"""Scenario management for APIGhost mock server."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from .schema import Scenario

SCENARIO_DIR = Path.home() / ".apighost" / "scenarios"


def _ensure_dir() -> Path:
    SCENARIO_DIR.mkdir(parents=True, exist_ok=True)
    return SCENARIO_DIR


def list_scenarios() -> list[dict]:
    """List all saved scenarios."""
    _ensure_dir()
    scenarios = []
    for f in sorted(SCENARIO_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            scenarios.append({
                "name": data.get("name", f.stem),
                "description": data.get("description", ""),
                "overrides": len(data.get("overrides", {})),
                "path": str(f),
            })
        except (json.JSONDecodeError, OSError):
            continue
    return scenarios


def save_scenario(name: str, description: str = "",
                  overrides: dict[str, dict] | None = None) -> str:
    """Save a scenario definition."""
    _ensure_dir()
    safe_name = name.replace(" ", "_").replace("/", "-")
    path = SCENARIO_DIR / f"{safe_name}.json"

    data = {
        "name": safe_name,
        "description": description,
        "overrides": overrides or {},
    }
    path.write_text(json.dumps(data, indent=2))
    return str(path)


def load_scenario(name_or_path: str) -> Scenario:
    """Load a scenario by name or path."""
    path = Path(name_or_path)
    if not path.exists():
        path = SCENARIO_DIR / f"{name_or_path}.json"
    if not path.exists():
        raise FileNotFoundError(f"Scenario not found: {name_or_path}")

    data = json.loads(path.read_text())
    return Scenario(
        name=data.get("name", name_or_path),
        description=data.get("description", ""),
        overrides=data.get("overrides", {}),
    )


def delete_scenario(name: str) -> bool:
    """Delete a scenario by name."""
    path = SCENARIO_DIR / f"{name}.json"
    if path.exists():
        path.unlink()
        return True
    return False
