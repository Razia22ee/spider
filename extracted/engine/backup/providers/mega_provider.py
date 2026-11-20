"""MEGA accounts via the mega.py client.

Storage numbers come from get_storage_space() (used and total bytes).
mega.py's get_quota() returns the plan size, not free space, so it is not used.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from ..classify import classify_exception, classify_mega
from ..config import AccountConfig
from ..errors import NightshiftError
from .base import Probe, UploadResult


def _file_id_from_upload(data: object) -> str | None:
    if isinstance(data, dict):
        files = data.get("f")
        if isinstance(files, list) and files and isinstance(files[0], dict) and files[0].get("h"):
            return str(files[0]["h"])
        for key in ("h", "id"):
            if data.get(key):
                return str(data[key])
        return json.dumps(data, default=str)[:180]
    if data:
        return str(data)[:180]
    return None


class MegaAccount:
    provider = "mega"

    def __init__(self, config: AccountConfig) -> None:
        self.name = config.name
        self._config = config
        self._mega = None
        self._folder_id = None

    def _login(self):
        if self._mega is not None:
            return self._mega
        from mega import Mega
        from mega.errors import RequestError

        client = Mega()
        try:
            self._mega = client.login(self._config.email, self._config.password)
        except RequestError as exc:
            kind = classify_mega(getattr(exc, "code", None), str(exc))
            raise NightshiftError(f"MEGA login failed for {self.name}: {exc}", "auth" if kind == "unknown" else kind) from exc
        except Exception as exc:
            kind = classify_exception(exc)
            if kind == "unknown":
                kind = "auth"
            raise NightshiftError(f"MEGA login failed for {self.name}: {exc}", kind) from exc
        self._folder_id = self._resolve_folder(self._mega, self._config.folder or "Nightshift")
        return self._mega

    def _resolve_folder(self, client, folder_name: str):
        found = client.find(folder_name)
        if isinstance(found, tuple) and len(found) >= 2 and isinstance(found[1], dict):
            if found[1].get("t") == 1:
                return found[0]
            folder_name = f"{folder_name}-videos"
            found = client.find(folder_name)
            if isinstance(found, tuple) and len(found) >= 2 and isinstance(found[1], dict) and found[1].get("t") == 1:
                return found[0]
        elif found:
            return found[0] if isinstance(found, tuple) else found
        created = client.create_folder(folder_name)
        if isinstance(created, dict) and created:
            return list(created.values())[-1]
        raise NightshiftError(f"could not open MEGA folder {folder_name}", "permanent")

    def _probe_sync(self) -> Probe:
        client = self._login()
        space = client.get_storage_space()
        if not isinstance(space, dict) or "total" not in space or "used" not in space:
            raise NightshiftError("MEGA did not return storage totals", "unknown")
        total = int(space["total"])
        used = int(space["used"])
        free = max(0, total - used)
        return Probe(
            name=self.name,
            provider=self.provider,
            auth_ok=True,
            available=True,
            free_bytes=free,
            unlimited=False,
            max_file_bytes=self._config.max_file_bytes,
            error=None,
            error_class="ok",
        )

    async def probe(self) -> Probe:
        try:
            return await asyncio.to_thread(self._probe_sync)
        except Exception as exc:
            self._mega = None
            kind = exc.kind if isinstance(exc, NightshiftError) else classify_exception(exc)
            return Probe(
                name=self.name,
                provider=self.provider,
                auth_ok=False if kind == "auth" else True,
                available=False,
                free_bytes=None,
                unlimited=False,
                max_file_bytes=self._config.max_file_bytes,
                error=str(exc)[:300],
                error_class=kind if kind != "ok" else "unknown",
            )

    def _find_sync(self, filename: str) -> str | None:
        client = self._login()
        found = client.find(filename)
        if not found:
            return None
        if isinstance(found, tuple):
            handle, node = found[0], found[1] if len(found) > 1 else None
            if isinstance(node, dict) and node.get("t") not in (None, 0):
                return None
            return str(handle)
        return str(found)

    async def find_existing(self, filename: str) -> str | None:
        return await asyncio.to_thread(self._find_sync, filename)

    def _upload_sync(self, path: Path, filename: str) -> UploadResult:
        client = self._login()
        data = client.upload(str(path), dest=self._folder_id, dest_filename=filename)
        file_id = _file_id_from_upload(data)
        if not file_id:
            return UploadResult(ok=False, error="MEGA upload did not return a file id", error_class="unknown")
        return UploadResult(ok=True, file_id=file_id, error_class="ok")

    async def upload(self, path: Path, filename: str, file_size: int) -> UploadResult:
        del file_size
        try:
            return await asyncio.to_thread(self._upload_sync, path, filename)
        except Exception as exc:
            self._mega = None
            kind = exc.kind if isinstance(exc, NightshiftError) else classify_exception(exc)
            return UploadResult(
                ok=False,
                error=str(exc)[:400],
                error_class=kind,
                storage_scope="account",
            )
