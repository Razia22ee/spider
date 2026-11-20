"""Storage account contract. Implementations must not raise for ordinary API failures
when they can return a Probe or UploadResult instead. place_file still guards with
classify_exception if they do.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class Probe:
    name: str
    provider: str
    auth_ok: bool
    available: bool
    free_bytes: int | None
    unlimited: bool
    max_file_bytes: int | None
    error: str | None
    error_class: str


@dataclass
class UploadResult:
    ok: bool
    file_id: str | None = None
    error: str | None = None
    error_class: str = "ok"
    # "account" zeros the rest of the run. "file" only blocks files this large.
    storage_scope: str = "account"
    tries: int = 1


class StorageAccount(Protocol):
    name: str
    provider: str

    async def probe(self) -> Probe: ...

    async def find_existing(self, filename: str) -> str | None: ...

    async def upload(self, path: Path, filename: str, file_size: int) -> UploadResult: ...
