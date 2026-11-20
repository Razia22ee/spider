from __future__ import annotations

from pathlib import Path

from backup.errors import NightshiftError
from backup.media import DiscoverBatch, RemoteVideo
from backup.providers.base import Probe, UploadResult


class ListLog:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def event(self, level: str, event: str, **fields: object) -> None:
        self.events.append({"level": level, "event": event, **fields})


class FakeSource:
    def __init__(self, messages: list[RemoteVideo], channel_id: int = -1001) -> None:
        self.messages = sorted(messages, key=lambda item: item.message_id)
        self.channel_id = channel_id
        self.downloads: list[int] = []
        self.fail_ids: set[int] = set()
        self.permanent_ids: set[int] = set()
        self.connected = False

    async def connect(self) -> None:
        self.connected = True

    async def close(self) -> None:
        self.connected = False

    async def discover(self, indexed_until_id: int, limit: int) -> DiscoverBatch:
        pending = [item for item in self.messages if item.message_id > indexed_until_id]
        chunk = pending[:limit]
        videos = [item for item in chunk if item.is_video]
        skipped = sum(1 for item in chunk if not item.is_video)
        highest = chunk[-1].message_id if chunk else indexed_until_id
        return DiscoverBatch(
            channel_id=self.channel_id,
            videos=videos,
            indexed_until_id=highest,
            scanned=len(chunk),
            skipped_non_video=skipped,
        )

    async def download(self, record: dict, dest_dir: Path) -> Path:
        message_id = int(record["message_id"])
        if message_id in self.permanent_ids:
            raise NightshiftError("message is gone", "permanent")
        if message_id in self.fail_ids:
            raise NightshiftError("timeout talking to Telegram", "transient")
        self.downloads.append(message_id)
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / record["remote_filename"]
        path.write_bytes(b"x" * 64)
        return path


class ScriptedAccount:
    def __init__(
        self,
        name: str,
        provider: str,
        probe: Probe,
        script: list | None = None,
        existing: str | None | Exception = None,
    ) -> None:
        self.name = name
        self.provider = provider
        self._probe = probe
        self.script = list(script or [])
        self.existing = existing
        self.uploads: list[str] = []
        self.finds: list[str] = []

    async def probe(self) -> Probe:
        return self._probe

    async def find_existing(self, filename: str) -> str | None:
        self.finds.append(filename)
        if isinstance(self.existing, Exception):
            raise self.existing
        return self.existing

    async def upload(self, path: Path, filename: str, file_size: int) -> UploadResult:
        del path, file_size
        self.uploads.append(filename)
        if self.script:
            item = self.script.pop(0)
            if isinstance(item, Exception):
                raise item
            return item
        return UploadResult(ok=True, file_id=f"{self.name}:{filename}")


def make_probe(name: str, provider: str, free: int | None, **kwargs) -> Probe:
    return Probe(
        name=name,
        provider=provider,
        auth_ok=kwargs.get("auth_ok", True),
        available=kwargs.get("available", True),
        free_bytes=free,
        unlimited=kwargs.get("unlimited", False),
        max_file_bytes=kwargs.get("max_file_bytes"),
        error=kwargs.get("error"),
        error_class=kwargs.get("error_class", "ok"),
    )


def video(message_id: int, size: int = 100, name: str | None = None, is_video: bool = True) -> RemoteVideo:
    return RemoteVideo(
        channel_id=-1001,
        message_id=message_id,
        filename=name or f"clip-{message_id}.mp4",
        file_size=size,
        mime_type="video/mp4" if is_video else "image/jpeg",
        message_date=f"2026-01-{(message_id % 27) + 1:02d}T00:00:00+00:00",
        is_video=is_video,
    )
