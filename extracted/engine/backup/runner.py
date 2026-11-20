"""One Nightshift run: index the channel, take up to five oldest videos, place each once."""

from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

from .database import Database
from .errors import LockHeld, NightshiftError
from .gitpersist import persist_ledger
from .media import DiscoverBatch
from .pool import place_file
from .providers.base import Probe, StorageAccount
from .records import (
    append_run,
    mark_needs_attention,
    mark_pending,
    mark_success,
    note_discovered,
    scan_cursor,
    select_pending,
    set_scan_cursor,
)


class VideoSource(Protocol):
    async def connect(self) -> None: ...

    async def close(self) -> None: ...

    async def discover(self, indexed_until_id: int, limit: int) -> DiscoverBatch: ...

    async def download(self, record: dict, dest_dir: Path) -> Path: ...


class Logger(Protocol):
    def event(self, level: str, event: str, **fields: object) -> None: ...


def _parse_iso(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def take_run_lock(data: dict, *, run_id: str, now: datetime, ttl_hours: float, force: bool) -> bool:
    lock = data.get("lock")
    if isinstance(lock, dict) and lock.get("run_id") and not force:
        started = _parse_iso(str(lock.get("started_at") or ""))
        if started is not None and now - started < timedelta(hours=ttl_hours):
            return False
    data["lock"] = {"run_id": run_id, "started_at": now.isoformat()}
    return True


def release_run_lock(data: dict, run_id: str) -> None:
    lock = data.get("lock")
    if isinstance(lock, dict) and lock.get("run_id") == run_id:
        data["lock"] = None


def _disk_allows(directory: Path, file_size: int) -> bool:
    directory.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(directory).free
    # Leave the runner enough room for the OS, the interpreter and the upload read.
    reserve = 1_500_000_000
    if file_size <= 0:
        return free > reserve
    return free >= file_size + reserve


async def _probe_all(accounts: list[StorageAccount], logger: Logger) -> dict[str, Probe]:
    probes: dict[str, Probe] = {}
    for account in accounts:
        probe = await account.probe()
        probes[account.name] = probe
        logger.event(
            "info" if probe.available else "warning",
            "account_probed",
            account=account.name,
            provider=probe.provider,
            available=probe.available,
            auth_ok=probe.auth_ok,
            free_bytes=probe.free_bytes,
            unlimited=probe.unlimited,
            error_class=probe.error_class,
            error=probe.error,
        )
    return probes


async def execute(
    *,
    settings,
    source: VideoSource,
    accounts: list[StorageAccount],
    logger: Logger,
    sleeper=None,
    now: datetime | None = None,
    persist=None,
) -> int:
    """Run one backup. Returns a process exit code. Never marks a failed upload successful."""
    if sleeper is None:
        import asyncio

        sleeper = asyncio.sleep
    clock = now or datetime.now(timezone.utc)

    def _default_persist(message: str) -> bool:
        return persist_ledger(settings.git_commit, settings.db_path, message, logger)

    if persist is None:
        persist = _default_persist

    db = Database(settings.db_path)
    try:
        db.acquire_process_lock()
    except LockHeld:
        logger.event("warning", "process_lock_held")
        return 0

    owned = False
    persist_failed = False
    exit_code = 0
    download_dir = Path(settings.download_dir)
    download_dir.mkdir(parents=True, exist_ok=True)

    def _persist(message: str) -> None:
        nonlocal persist_failed
        ok = persist(message)
        # A later successful push means the remote caught up.
        persist_failed = not ok

    try:
        data = db.load()
        if not take_run_lock(
            data,
            run_id=settings.run_id,
            now=clock,
            ttl_hours=settings.lock_ttl_hours,
            force=settings.force_unlock,
        ):
            logger.event("warning", "ledger_lock_held", run_id=settings.run_id)
            return 0
        owned = True
        db.save(data)
        _persist(f"chore(ledger): start run {settings.run_id}")

        summary = {
            "run_id": settings.run_id,
            "started_at": clock.isoformat(),
            "dry_run": settings.dry_run,
            "discovered": 0,
            "needs_attention": 0,
            "selected": 0,
            "succeeded": 0,
            "pending": 0,
            "skipped_non_video": 0,
        }
        try:
            await source.connect()
            logger.event("info", "telegram_connected", channel=settings.channel)
            channel_id = getattr(source, "channel_id", None)
            if channel_id is None:
                channel_id = _only_channel(data)
            cursor = scan_cursor(data, int(channel_id)) if channel_id else 0
            batch = await source.discover(cursor, settings.history_scan_limit)
            summary["discovered"] = len(batch.videos)
            summary["skipped_non_video"] = batch.skipped_non_video
            logger.event(
                "info",
                "channel_scanned",
                channel_id=batch.channel_id,
                scanned=batch.scanned,
                videos=len(batch.videos),
                skipped_non_video=batch.skipped_non_video,
                indexed_until_id=batch.indexed_until_id,
            )
            for video in batch.videos:
                outcome = note_discovered(
                    data["videos"],
                    video,
                    clock.isoformat(),
                    settings.max_runner_file_bytes,
                )
                if outcome == "needs_attention":
                    summary["needs_attention"] += 1
                    logger.event(
                        "warning",
                        "runner_disk_block",
                        message_id=video.message_id,
                        file_size=video.file_size,
                    )
            set_scan_cursor(data, batch.channel_id, batch.indexed_until_id)
            chosen = select_pending(data["videos"], settings.daily_limit)
            summary["selected"] = len(chosen)
            logger.event(
                "info",
                "videos_selected",
                count=len(chosen),
                message_ids=[row["message_id"] for row in chosen],
                daily_limit=settings.daily_limit,
            )
            probes: dict[str, Probe] = {}
            if chosen:
                probes = await _probe_all(accounts, logger)
            if chosen and not accounts:
                logger.event("error", "no_accounts", detail="configure GDRIVE_ACCOUNTS_JSON or MEGA_ACCOUNTS_JSON")

            for row in chosen:
                when = datetime.now(timezone.utc).isoformat()
                file_size = int(row.get("file_size") or 0)
                if settings.dry_run:
                    from .pool import rank_accounts

                    ranked = rank_accounts(list(probes.values()), file_size, settings.margin_bytes)
                    logger.event(
                        "info",
                        "dry_run_plan",
                        message_id=row["message_id"],
                        filename=row["filename"],
                        file_size=file_size,
                        would_use=ranked[0].name if ranked else None,
                    )
                    continue
                if file_size and file_size > settings.max_runner_file_bytes:
                    mark_needs_attention(
                        row,
                        when=when,
                        error="file exceeds the GitHub runner size limit",
                        error_class="runner_disk",
                    )
                    summary["needs_attention"] += 1
                    db.save(data)
                    _persist(f"chore(ledger): flag {row['message_id']} over runner limit")
                    continue
                if file_size and not _disk_allows(download_dir, file_size):
                    mark_pending(
                        row,
                        when=when,
                        error="GitHub runner does not have enough free disk for this video tonight",
                        error_class="transient",
                    )
                    summary["pending"] += 1
                    logger.event("warning", "runner_disk_pressure", message_id=row["message_id"], file_size=file_size)
                    db.save(data)
                    _persist(f"chore(ledger): defer {row['message_id']} for disk space")
                    continue
                local: Path | None = None
                try:
                    local = await source.download(row, download_dir)
                    actual = local.stat().st_size if local.exists() else 0
                    if actual:
                        row["file_size"] = actual
                        file_size = actual
                    if file_size > settings.max_runner_file_bytes:
                        mark_needs_attention(
                            row,
                            when=when,
                            error="downloaded file exceeds the GitHub runner size limit",
                            error_class="runner_disk",
                        )
                        summary["needs_attention"] += 1
                        db.save(data)
                        _persist(f"chore(ledger): flag {row['message_id']} over runner limit")
                        continue
                    placement = await place_file(
                        accounts,
                        probes,
                        local,
                        row["remote_filename"],
                        file_size,
                        settings.margin_bytes,
                        sleeper,
                        settings.retry_attempts,
                    )
                except NightshiftError as exc:
                    if exc.kind == "permanent":
                        mark_needs_attention(row, when=when, error=str(exc), error_class=exc.kind)
                        summary["needs_attention"] += 1
                    else:
                        mark_pending(row, when=when, error=str(exc), error_class=exc.kind)
                        summary["pending"] += 1
                    logger.event(
                        "error",
                        "video_not_stored",
                        message_id=row["message_id"],
                        error_class=exc.kind,
                        error=str(exc)[:300],
                    )
                    db.save(data)
                    _persist(f"chore(ledger): keep {row['message_id']} {row['status']}")
                    if exc.exit_code == 2:
                        exit_code = 2
                        break
                    continue
                except Exception as exc:
                    mark_pending(row, when=when, error=str(exc), error_class="unknown")
                    summary["pending"] += 1
                    logger.event(
                        "error",
                        "video_not_stored",
                        message_id=row["message_id"],
                        error_class="unknown",
                        error=str(exc)[:300],
                    )
                    db.save(data)
                    _persist(f"chore(ledger): keep {row['message_id']} pending")
                    continue
                finally:
                    if local is not None:
                        try:
                            local.unlink(missing_ok=True)
                        except OSError as exc:
                            logger.event("warning", "cleanup_failed", path=str(local), error=str(exc)[:200])

                if placement.ok and placement.file_id and placement.account and placement.provider:
                    note = "already on the account; recorded without a second upload" if placement.deduped else "uploaded"
                    mark_success(
                        row,
                        provider=placement.provider,
                        account=placement.account,
                        file_id=placement.file_id,
                        when=when,
                        note=note,
                    )
                    summary["succeeded"] += 1
                    logger.event(
                        "info",
                        "video_stored",
                        message_id=row["message_id"],
                        account=placement.account,
                        provider=placement.provider,
                        file_id=placement.file_id,
                        deduped=placement.deduped,
                    )
                else:
                    mark_pending(
                        row,
                        when=when,
                        error=placement.error or "no account accepted the upload",
                        error_class=placement.error_class or "unknown",
                        account=placement.attempts[-1].account if placement.attempts else None,
                    )
                    summary["pending"] += 1
                    logger.event(
                        "error",
                        "video_not_stored",
                        message_id=row["message_id"],
                        error_class=placement.error_class,
                        error=placement.error,
                        attempts=[
                            {"account": item.account, "error_class": item.error_class, "tries": item.tries}
                            for item in placement.attempts
                        ],
                    )
                db.save(data)
                _persist(
                    f"chore(ledger): {row['status']} {row['message_id']} "
                    f"{row.get('account') or row.get('error_class') or ''}"
                )

            stored_nothing = summary["succeeded"] == 0 and (summary["pending"] or summary["needs_attention"])
            if summary["selected"] and stored_nothing and not settings.dry_run:
                exit_code = exit_code or 1
            elif summary["selected"] and not accounts and not settings.dry_run:
                exit_code = 1
        except NightshiftError as exc:
            logger.event("error", "run_failed", error_class=exc.kind, error=str(exc)[:400])
            exit_code = exc.exit_code or 1
        except Exception as exc:
            logger.event("error", "run_failed", error_class="unknown", error=str(exc)[:400])
            exit_code = 1
        finally:
            try:
                await source.close()
            except Exception as exc:
                logger.event("warning", "telegram_close_failed", error=str(exc)[:200])
            summary["finished_at"] = datetime.now(timezone.utc).isoformat()
            summary["exit_code"] = exit_code
            append_run(data, summary)
            if owned:
                release_run_lock(data, settings.run_id)
            db.save(data)
            _persist(f"chore(ledger): finish run {settings.run_id}")
            logger.event("info", "run_finished", **summary)
    finally:
        db.release_process_lock()

    if persist_failed:
        return 4
    return exit_code


def _only_channel(data: dict) -> int | None:
    scan = data.get("scan") or {}
    if len(scan) == 1:
        key = next(iter(scan))
        try:
            return int(key)
        except (TypeError, ValueError):
            return None
    return None
