"""Telegram message shape helpers. No Telethon import, so they stay unit-testable."""

from __future__ import annotations

import re
from dataclasses import dataclass

_UNSAFE = re.compile(r"[^A-Za-z0-9._ -]+")


@dataclass
class RemoteVideo:
    channel_id: int
    message_id: int
    filename: str
    file_size: int
    mime_type: str
    message_date: str
    is_video: bool = True


@dataclass
class DiscoverBatch:
    channel_id: int
    videos: list[RemoteVideo]
    indexed_until_id: int
    scanned: int
    skipped_non_video: int


def sanitize_filename(name: str, fallback: str) -> str:
    base = (name or "").replace("\\", "/").split("/")[-1]
    base = _UNSAFE.sub("_", base).strip(" .")
    if not base or base in {".", ".."}:
        base = fallback
    if len(base) > 140:
        stem, dot, ext = base.rpartition(".")
        if dot and 0 < len(ext) <= 8:
            base = stem[:120] + "." + ext
        else:
            base = base[:140]
    return base


def remote_filename(message_id: int, filename: str) -> str:
    """Stable object name. The message id makes crash-recovery lookups exact."""
    return f"{message_id}_{filename}"


def is_video_message(message: object) -> bool:
    """True for real videos. Photos, GIFs, stickers, audio and plain files are ignored."""
    if getattr(message, "gif", None) or getattr(message, "sticker", None):
        return False
    if getattr(message, "video", None):
        return True
    doc = getattr(message, "document", None)
    if doc is None:
        return False
    mime = str(getattr(doc, "mime_type", "") or "").lower()
    if mime.startswith("video/"):
        return True
    attrs = getattr(doc, "attributes", None) or []
    return any(type(attr).__name__ == "DocumentAttributeVideo" for attr in attrs)


def message_to_remote(message: object, channel_id: int) -> RemoteVideo | None:
    if not is_video_message(message):
        return None
    file = getattr(message, "file", None)
    raw_name = getattr(file, "name", None) if file else None
    ext = getattr(file, "ext", None) if file else None
    if not ext:
        ext = ".mp4"
    ext = ext if str(ext).startswith(".") else f".{ext}"
    message_id = int(getattr(message, "id"))
    fallback = f"video_{message_id}{ext}"
    filename = sanitize_filename(str(raw_name or fallback), fallback)
    size = int(getattr(file, "size", 0) or 0) if file else 0
    mime = ""
    if file is not None and getattr(file, "mime_type", None):
        mime = str(file.mime_type)
    elif getattr(message, "document", None) is not None:
        mime = str(getattr(message.document, "mime_type", "") or "")
    date = getattr(message, "date", None)
    message_date = date.isoformat() if hasattr(date, "isoformat") else str(date or "")
    return RemoteVideo(
        channel_id=channel_id,
        message_id=message_id,
        filename=filename,
        file_size=size,
        mime_type=mime or "video/mp4",
        message_date=message_date,
    )
