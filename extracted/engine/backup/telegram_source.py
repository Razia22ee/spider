"""Telethon channel reader. Session string only — no interactive login on the runner."""

from __future__ import annotations

import asyncio
from pathlib import Path

from .errors import NightshiftError
from .media import DiscoverBatch, message_to_remote


class TelegramSource:
    def __init__(self, api_id: int, api_hash: str, string_session: str, channel: str) -> None:
        self._api_id = api_id
        self._api_hash = api_hash
        self._string_session = string_session
        self._channel = channel
        self._client = None
        self._entity = None
        self._channel_id: int | None = None

    async def connect(self) -> None:
        from telethon import TelegramClient
        from telethon.errors import (
            AccessTokenInvalidError,
            ApiIdInvalidError,
            AuthKeyUnregisteredError,
        )
        from telethon.sessions import StringSession

        self._client = TelegramClient(StringSession(self._string_session), self._api_id, self._api_hash)
        try:
            await self._client.connect()
        except (OSError, ConnectionError, TimeoutError) as exc:
            raise NightshiftError(f"Telegram connection failed: {exc}", "transient", exit_code=3) from exc
        except (ApiIdInvalidError, AccessTokenInvalidError, AuthKeyUnregisteredError) as exc:
            raise NightshiftError(f"Telegram credentials rejected: {exc}", "auth", exit_code=2) from exc
        if not await self._client.is_user_authorized():
            raise NightshiftError(
                "Telegram StringSession is not authorized. Generate a new one and update the secret.",
                "auth",
                exit_code=2,
            )
        try:
            self._entity = await self._client.get_entity(self._channel)
        except (ValueError, TypeError) as exc:
            raise NightshiftError(f"Cannot open channel {self._channel}: {exc}", "permanent", exit_code=2) from exc
        except Exception as exc:
            name = type(exc).__name__
            if name in {"ChannelPrivateError", "UsernameInvalidError", "UsernameNotOccupiedError", "ChannelInvalidError"}:
                raise NightshiftError(f"Cannot open channel {self._channel}: {exc}", "auth", exit_code=2) from exc
            raise NightshiftError(f"Cannot open channel {self._channel}: {exc}", "transient", exit_code=3) from exc
        from telethon import utils

        self._channel_id = int(utils.get_peer_id(self._entity))

    @property
    def channel_id(self) -> int | None:
        return self._channel_id

    async def close(self) -> None:
        if self._client is not None:
            await self._client.disconnect()
            self._client = None

    async def discover(self, indexed_until_id: int, limit: int) -> DiscoverBatch:
        if self._client is None or self._channel_id is None:
            raise NightshiftError("Telegram is not connected", "permanent", exit_code=3)
        from telethon.errors import FloodWaitError

        delay = 2.0
        last: Exception | None = None
        for attempt in range(4):
            try:
                return await self._discover_once(indexed_until_id, limit)
            except FloodWaitError as exc:
                last = exc
                if exc.seconds > 900 or attempt == 3:
                    raise NightshiftError(
                        f"Telegram rate limit: wait {exc.seconds}s",
                        "transient",
                        exit_code=3,
                    ) from exc
                await asyncio.sleep(exc.seconds + 1)
            except (OSError, ConnectionError, TimeoutError) as exc:
                last = exc
                if attempt == 3:
                    raise NightshiftError(f"Telegram read failed: {exc}", "transient", exit_code=3) from exc
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60.0)
        raise NightshiftError(f"Telegram read failed: {last}", "transient", exit_code=3)

    async def _discover_once(self, indexed_until_id: int, limit: int) -> DiscoverBatch:
        videos = []
        scanned = 0
        skipped = 0
        highest = int(indexed_until_id)
        async for message in self._client.iter_messages(
            self._entity,
            min_id=int(indexed_until_id),
            reverse=True,
            limit=int(limit),
        ):
            scanned += 1
            message_id = int(getattr(message, "id", 0) or 0)
            if message_id > highest:
                highest = message_id
            video = message_to_remote(message, self._channel_id or 0)
            if video is None:
                if getattr(message, "media", None) is not None or getattr(message, "photo", None):
                    skipped += 1
                continue
            videos.append(video)
        return DiscoverBatch(
            channel_id=self._channel_id or 0,
            videos=videos,
            indexed_until_id=highest,
            scanned=scanned,
            skipped_non_video=skipped,
        )

    async def download(self, record: dict, dest_dir: Path) -> Path:
        if self._client is None or self._entity is None:
            raise NightshiftError("Telegram is not connected", "permanent", exit_code=3)
        from telethon.errors import FloodWaitError

        message_id = int(record["message_id"])
        try:
            message = await self._client.get_messages(self._entity, ids=message_id)
        except FloodWaitError as exc:
            if exc.seconds > 900:
                raise NightshiftError(f"Telegram rate limit during download: {exc.seconds}s", "transient") from exc
            await asyncio.sleep(exc.seconds + 1)
            message = await self._client.get_messages(self._entity, ids=message_id)
        except (OSError, ConnectionError, TimeoutError) as exc:
            raise NightshiftError(f"download failed: {exc}", "transient") from exc
        if message is None:
            raise NightshiftError(f"message {message_id} is gone", "permanent")
        video = message_to_remote(message, int(record["channel_id"]))
        if video is None:
            raise NightshiftError(f"message {message_id} is no longer a video", "permanent")
        dest_dir.mkdir(parents=True, exist_ok=True)
        target = dest_dir / str(record["remote_filename"])
        try:
            saved = await self._client.download_media(message, file=str(target))
        except FloodWaitError as exc:
            raise NightshiftError(f"Telegram rate limit during download: {exc.seconds}s", "transient") from exc
        except (OSError, ConnectionError, TimeoutError) as exc:
            raise NightshiftError(f"download failed: {exc}", "transient") from exc
        if not saved:
            raise NightshiftError(f"Telegram returned no file for {message_id}", "transient")
        return Path(saved)
