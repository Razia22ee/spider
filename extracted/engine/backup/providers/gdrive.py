"""Google Drive accounts. One refresh token per account. No shared upload."""

from __future__ import annotations

import asyncio
from pathlib import Path

from ..classify import classify_exception
from ..config import AccountConfig
from .base import Probe, UploadResult

SCOPES = ["https://www.googleapis.com/auth/drive"]


def _mime_for(filename: str) -> str:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    return {
        "mp4": "video/mp4",
        "m4v": "video/mp4",
        "mov": "video/quicktime",
        "webm": "video/webm",
        "mkv": "video/x-matroska",
        "avi": "video/x-msvideo",
    }.get(ext, "application/octet-stream")


def _escape_query(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


class GoogleDriveAccount:
    provider = "gdrive"

    def __init__(self, config: AccountConfig) -> None:
        self.name = config.name
        self._config = config
        self._service = None

    def _build(self):
        if self._service is not None:
            return self._service
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials(
            token=None,
            refresh_token=self._config.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self._config.client_id,
            client_secret=self._config.client_secret,
            scopes=SCOPES,
        )
        creds.refresh(Request())
        self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return self._service

    def _probe_sync(self) -> Probe:
        service = self._build()
        about = service.about().get(fields="storageQuota").execute()
        quota = about.get("storageQuota") or {}
        usage = int(quota.get("usage") or 0)
        raw_limit = quota.get("limit")
        # Workspace accounts that are truly unlimited omit `limit`. A missing
        # field is the API's signal. A failed call never reaches this branch,
        # so a network error cannot be mistaken for unlimited storage.
        if raw_limit in (None, ""):
            unlimited = True
            free = None
        else:
            unlimited = False
            free = max(0, int(raw_limit) - usage)
        return Probe(
            name=self.name,
            provider=self.provider,
            auth_ok=True,
            available=True,
            free_bytes=free,
            unlimited=unlimited,
            max_file_bytes=self._config.max_file_bytes,
            error=None,
            error_class="ok",
        )

    def _failed_probe(self, exc: Exception) -> Probe:
        self._service = None
        kind = classify_exception(exc)
        return Probe(
            name=self.name,
            provider=self.provider,
            auth_ok=kind != "auth",
            available=False,
            free_bytes=None,
            unlimited=False,
            max_file_bytes=self._config.max_file_bytes,
            error=str(exc)[:300],
            error_class="auth" if kind == "auth" else kind,
        )

    async def probe(self) -> Probe:
        try:
            return await asyncio.to_thread(self._probe_sync)
        except Exception as exc:
            return self._failed_probe(exc)

    def _find_sync(self, filename: str) -> str | None:
        service = self._build()
        clauses = [f"name = '{_escape_query(filename)}'", "trashed = false"]
        if self._config.folder_id:
            clauses.append(f"'{_escape_query(self._config.folder_id)}' in parents")
        listed = (
            service.files()
            .list(q=" and ".join(clauses), fields="files(id,name,size)", pageSize=5, spaces="drive")
            .execute()
        )
        files = listed.get("files") or []
        if not files:
            return None
        return str(files[0]["id"])

    async def find_existing(self, filename: str) -> str | None:
        return await asyncio.to_thread(self._find_sync, filename)

    def _upload_sync(self, path: Path, filename: str, mime: str) -> UploadResult:
        from googleapiclient.http import MediaFileUpload

        service = self._build()
        metadata: dict = {"name": filename}
        if self._config.folder_id:
            metadata["parents"] = [self._config.folder_id]
        media = MediaFileUpload(
            str(path),
            mimetype=mime or "application/octet-stream",
            resumable=True,
            chunksize=8 * 1024 * 1024,
        )
        request = service.files().create(body=metadata, media_body=media, fields="id,name,size")
        response = None
        while response is None:
            _status, response = request.next_chunk()
        file_id = str((response or {}).get("id") or "")
        if not file_id:
            return UploadResult(ok=False, error="Drive did not return a file id", error_class="unknown")
        return UploadResult(ok=True, file_id=file_id, error_class="ok")

    async def upload(self, path: Path, filename: str, file_size: int) -> UploadResult:
        del file_size  # size is taken from the file on disk
        mime = _mime_for(filename)
        try:
            return await asyncio.to_thread(self._upload_sync, path, filename, mime)
        except Exception as exc:
            self._service = None
            kind = classify_exception(exc)
            scope = "account"
            text = str(exc).lower()
            if kind == "storage" and "file" in text and "quota" not in text:
                scope = "file"
            return UploadResult(
                ok=False,
                error=str(exc)[:400],
                error_class=kind,
                storage_scope=scope,
            )
