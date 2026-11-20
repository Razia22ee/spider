"""JSON-lines log. Field names that look like secrets are redacted."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_SENSITIVE = ("token", "secret", "password", "session", "hash", "authorization", "credential")


def _redact(fields: dict) -> dict:
    clean = {}
    for key, value in fields.items():
        if any(part in str(key).lower() for part in _SENSITIVE):
            clean[key] = "***"
        else:
            clean[key] = value
    return clean


class RunLog:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def event(self, level: str, event: str, **fields: object) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "event": event,
            **_redact(fields),
        }
        line = json.dumps(record, default=str, sort_keys=True)
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
