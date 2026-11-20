"""Ledger rows. Successful rows are never selected again. Failed rows are."""

from __future__ import annotations

from .media import RemoteVideo, remote_filename

DAILY_LIMIT_MAX = 5
SKIP_STATUSES = {"success", "needs_attention"}
ELIGIBLE_STATUSES = {"discovered", "pending", "failed"}


def clamp_daily_limit(value: int) -> int:
    n = int(value)
    if n < 0:
        return 0
    return min(n, DAILY_LIMIT_MAX)


def video_key(channel_id: int, message_id: int) -> str:
    return f"{int(channel_id)}:{int(message_id)}"


def empty_db() -> dict:
    return {"version": 1, "lock": None, "scan": {}, "videos": {}, "runs": []}


def scan_cursor(data: dict, channel_id: int) -> int:
    scan = data.setdefault("scan", {})
    try:
        return int(scan.get(str(channel_id), 0) or 0)
    except (TypeError, ValueError):
        return 0


def set_scan_cursor(data: dict, channel_id: int, message_id: int) -> None:
    scan = data.setdefault("scan", {})
    current = scan_cursor(data, channel_id)
    if int(message_id) > current:
        scan[str(channel_id)] = int(message_id)


def _blank(video: RemoteVideo, now: str, status: str, error: str | None, error_class: str | None) -> dict:
    return {
        "channel_id": video.channel_id,
        "message_id": video.message_id,
        "filename": video.filename,
        "remote_filename": remote_filename(video.message_id, video.filename),
        "file_size": int(video.file_size or 0),
        "mime_type": video.mime_type,
        "message_date": video.message_date,
        "upload_date": None,
        "provider": None,
        "account": None,
        "destination_file_id": None,
        "status": status,
        "attempts": 0,
        "last_error": error,
        "error_class": error_class,
        "updated_at": now,
        "history": [],
    }


def note_discovered(videos: dict, video: RemoteVideo, now: str, max_runner_file_bytes: int) -> str:
    """Insert or refresh a video. Never downgrades success or needs_attention."""
    key = video_key(video.channel_id, video.message_id)
    existing = videos.get(key)
    if existing and existing.get("status") in SKIP_STATUSES:
        return "unchanged"
    too_big = bool(video.file_size) and int(video.file_size) > int(max_runner_file_bytes)
    if too_big:
        row = _blank(
            video,
            now,
            "needs_attention",
            (
                f"File is {video.file_size} bytes, above the GitHub-hosted runner limit "
                f"of {max_runner_file_bytes} bytes. Not uploaded and not marked successful."
            ),
            "runner_disk",
        )
        if existing:
            row["attempts"] = int(existing.get("attempts") or 0)
            row["history"] = list(existing.get("history") or [])
        videos[key] = row
        return "needs_attention"
    if existing:
        existing["filename"] = video.filename
        existing["remote_filename"] = remote_filename(video.message_id, video.filename)
        if video.file_size:
            existing["file_size"] = int(video.file_size)
        if video.mime_type:
            existing["mime_type"] = video.mime_type
        if video.message_date:
            existing["message_date"] = video.message_date
        existing["updated_at"] = now
        if existing.get("status") not in ELIGIBLE_STATUSES:
            existing["status"] = "discovered"
        return "refreshed"
    videos[key] = _blank(video, now, "discovered", None, None)
    return "new"


def select_pending(videos: dict, limit: int) -> list[dict]:
    """Oldest message id first, hard cap of 5, skip success and needs_attention."""
    capped = clamp_daily_limit(limit)
    rows = []
    for row in videos.values():
        if row.get("status") not in ELIGIBLE_STATUSES:
            continue
        rows.append(row)
    rows.sort(key=lambda row: (int(row["message_id"]), int(row["channel_id"])))
    return rows[:capped]


def append_history(row: dict, entry: dict, keep: int = 20) -> None:
    history = list(row.get("history") or [])
    history.append(entry)
    row["history"] = history[-keep:]


def mark_success(row: dict, *, provider: str, account: str, file_id: str, when: str, note: str) -> None:
    row["status"] = "success"
    row["provider"] = provider
    row["account"] = account
    row["destination_file_id"] = file_id
    row["upload_date"] = when
    row["updated_at"] = when
    row["last_error"] = None
    row["error_class"] = None
    row["attempts"] = int(row.get("attempts") or 0) + 1
    append_history(
        row,
        {
            "at": when,
            "result": "success",
            "provider": provider,
            "account": account,
            "file_id": file_id,
            "note": note,
        },
    )


def mark_pending(row: dict, *, when: str, error: str, error_class: str, account: str | None = None) -> None:
    """A failed attempt stays pending. It is never written as success."""
    row["status"] = "pending"
    row["updated_at"] = when
    row["last_error"] = error[:500]
    row["error_class"] = error_class
    row["attempts"] = int(row.get("attempts") or 0) + 1
    # Do not clear a previous destination if we somehow had one; success is the only
    # status allowed to carry a trusted destination. Pending must not look uploaded.
    if row.get("status") != "success":
        row["provider"] = None
        row["account"] = None
        row["destination_file_id"] = None
        row["upload_date"] = None
    append_history(
        row,
        {
            "at": when,
            "result": "error",
            "error_class": error_class,
            "error": error[:300],
            "account": account,
        },
    )


def mark_needs_attention(row: dict, *, when: str, error: str, error_class: str) -> None:
    row["status"] = "needs_attention"
    row["updated_at"] = when
    row["last_error"] = error[:500]
    row["error_class"] = error_class
    row["provider"] = None
    row["account"] = None
    row["destination_file_id"] = None
    row["upload_date"] = None
    append_history(row, {"at": when, "result": "needs_attention", "error_class": error_class, "error": error[:300]})


def append_run(data: dict, summary: dict, keep: int = 90) -> None:
    runs = list(data.get("runs") or [])
    runs.append(summary)
    data["runs"] = runs[-keep:]
