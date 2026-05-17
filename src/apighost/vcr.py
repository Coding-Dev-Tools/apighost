"""VCR-style cassette recording and replay for APIGhost."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .schema import Cassette, CassetteInteraction

CASSETTE_DIR = Path.home() / ".apighost" / "cassettes"


def _ensure_dir() -> Path:
    """Ensure the cassette storage directory exists."""
    CASSETTE_DIR.mkdir(parents=True, exist_ok=True)
    return CASSETTE_DIR


def list_cassettes() -> list[dict]:
    """List all saved cassettes with metadata."""
    _ensure_dir()
    cassettes = []
    for f in sorted(CASSETTE_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            cassettes.append({
                "name": f.stem,
                "path": str(f),
                "interactions": len(data.get("interactions", [])),
                "spec": data.get("spec", ""),
                "size": f.stat().st_size,
            })
        except (json.JSONDecodeError, OSError):
            continue
    return cassettes


def save_cassette(name: str, interactions: list[CassetteInteraction], spec_path: str = "") -> str:
    """Save recorded interactions to a cassette file."""
    _ensure_dir()
    safe_name = name.replace(" ", "_").replace("/", "-")
    path = CASSETTE_DIR / f"{safe_name}.json"

    data = {
        "name": safe_name,
        "spec": spec_path,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "interactions": [
            {
                "request": {
                    "method": i.request_method,
                    "path": i.request_path,
                    "headers": i.request_headers,
                    "body": i.request_body,
                },
                "response": {
                    "status": i.response_status,
                    "headers": i.response_headers,
                    "body": i.response_body,
                },
            }
            for i in interactions
        ],
    }

    path.write_text(json.dumps(data, indent=2))
    return str(path)


def load_cassette(name_or_path: str) -> Cassette:
    """Load a cassette by name or path."""
    path = Path(name_or_path)
    if not path.exists():
        path = CASSETTE_DIR / f"{name_or_path}.json"
    if not path.exists():
        raise FileNotFoundError(f"Cassette not found: {name_or_path}")

    data = json.loads(path.read_text())
    interactions = [
        CassetteInteraction(
            request_method=i["request"]["method"],
            request_path=i["request"]["path"],
            request_headers=i["request"].get("headers", {}),
            request_body=i["request"].get("body"),
            response_status=i["response"]["status"],
            response_headers=i["response"].get("headers", {}),
            response_body=i["response"]["body"],
        )
        for i in data.get("interactions", [])
    ]

    return Cassette(
        name=data.get("name", name_or_path),
        interactions=interactions,
        spec_path=data.get("spec", ""),
    )


class Recorder:
    """Records HTTP interactions during mock server operation."""

    def __init__(self):
        self.interactions: list[CassetteInteraction] = []

    def record(self, request_method: str, request_path: str,
               request_headers: dict, request_body: str | None,
               response_status: int, response_headers: dict,
               response_body: str) -> None:
        """Record a single HTTP interaction."""
        # Strip sensitive headers
        safe_headers = {k: v for k, v in request_headers.items()
                        if k.lower() not in ("authorization", "cookie", "set-cookie", "x-api-key")}

        self.interactions.append(CassetteInteraction(
            request_method=request_method,
            request_path=request_path,
            request_headers=safe_headers,
            request_body=request_body,
            response_status=response_status,
            response_headers=response_headers,
            response_body=response_body,
        ))

    def save(self, name: str, spec_path: str = "") -> str:
        """Save recorded interactions."""
        return save_cassette(name, self.interactions, spec_path)

    def clear(self) -> None:
        """Clear recorded interactions."""
        self.interactions = []

    @property
    def count(self) -> int:
        return len(self.interactions)
