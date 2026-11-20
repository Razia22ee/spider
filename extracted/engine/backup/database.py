"""Atomic JSON ledger plus a lock file that dies with the process."""

from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path

from .errors import LockHeld
from .records import empty_db


class Database:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_path = self.path.with_name(self.path.name + ".lock")
        self._lock_fh = None
        self._held = False

    def acquire_process_lock(self) -> None:
        self._lock_fh = open(self._lock_path, "a+", encoding="utf-8")
        try:
            fcntl.flock(self._lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise LockHeld("another process is already using the backup ledger") from exc
        self._held = True

    def release_process_lock(self) -> None:
        if self._lock_fh is None:
            return
        if self._held:
            fcntl.flock(self._lock_fh.fileno(), fcntl.LOCK_UN)
            self._held = False
        self._lock_fh.close()
        self._lock_fh = None

    def load(self) -> dict:
        if not self.path.exists():
            return empty_db()
        raw = self.path.read_text(encoding="utf-8")
        if not raw.strip():
            return empty_db()
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError(f"ledger {self.path} is not a JSON object")
        data.setdefault("version", 1)
        data.setdefault("lock", None)
        data.setdefault("scan", {})
        data.setdefault("videos", {})
        data.setdefault("runs", [])
        return data

    def save(self, data: dict) -> None:
        payload = json.dumps(data, indent=2, sort_keys=True) + "\n"
        tmp = self.path.with_name(self.path.name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, self.path)
