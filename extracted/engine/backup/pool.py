"""One logical pool. Each video is offered to a single account, largest free space first."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

from .classify import classify_exception
from .errors import NightshiftError
from .providers.base import Probe, StorageAccount, UploadResult


@dataclass
class Attempt:
    account: str
    provider: str
    error_class: str
    error: str
    tries: int


@dataclass
class Placement:
    ok: bool
    provider: str | None = None
    account: str | None = None
    file_id: str | None = None
    deduped: bool = False
    error: str | None = None
    error_class: str | None = None
    attempts: list[Attempt] = field(default_factory=list)


def fits(probe: Probe, file_size: int, margin: int) -> bool:
    if not probe.available or not probe.auth_ok:
        return False
    if probe.error_class == "auth":
        return False
    if probe.max_file_bytes is not None and file_size > probe.max_file_bytes:
        return False
    if probe.unlimited:
        return True
    # Unknown free space is not treated as infinite.
    if probe.free_bytes is None:
        return False
    return probe.free_bytes >= file_size + max(0, margin)


def rank_accounts(probes: list[Probe], file_size: int, margin: int) -> list[Probe]:
    eligible = [probe for probe in probes if fits(probe, file_size, margin)]

    def sort_key(probe: Probe) -> tuple:
        space = math.inf if probe.unlimited else int(probe.free_bytes or 0)
        return (-space, probe.provider, probe.name)

    eligible.sort(key=sort_key)
    return eligible


def _failure_class(attempts: list[Attempt], had_accounts: bool) -> str:
    if not attempts:
        return "storage" if had_accounts else "config"
    classes = [item.error_class for item in attempts]
    if classes and all(item == "storage" for item in classes):
        return "storage"
    if any(item in {"transient", "unknown"} for item in classes):
        return "transient"
    if all(item == "auth" for item in classes):
        return "auth"
    return classes[-1]


async def _upload_with_retries(
    account: StorageAccount,
    path: Path,
    filename: str,
    file_size: int,
    attempts: int,
    sleeper,
) -> UploadResult:
    delay = 2.0
    last = UploadResult(ok=False, error="upload did not run", error_class="unknown")
    tries = max(1, attempts)
    for index in range(tries):
        try:
            result = await account.upload(path, filename, file_size)
        except Exception as exc:  # provider bugs and network errors
            kind = classify_exception(exc)
            message = str(exc)[:400]
            result = UploadResult(ok=False, error=message, error_class=kind)
        result.tries = index + 1
        last = result
        if result.ok and not result.file_id:
            result = UploadResult(ok=False, error="upload did not return a file id", error_class="unknown", tries=index + 1)
            last = result
        if result.ok or result.error_class not in {"transient", "unknown"}:
            return result
        if index == tries - 1:
            return result
        await sleeper(delay)
        delay = min(delay * 2, 60.0)
    return last


async def _find_with_retries(account: StorageAccount, filename: str, attempts: int, sleeper):
    delay = 2.0
    tries = max(1, attempts)
    last_error: Exception | None = None
    for index in range(tries):
        try:
            return await account.find_existing(filename)
        except Exception as exc:
            last_error = exc
            kind = classify_exception(exc)
            if kind not in {"transient", "unknown"} or index == tries - 1:
                raise NightshiftError(str(exc)[:400], kind) from exc
            await sleeper(delay)
            delay = min(delay * 2, 60.0)
    raise NightshiftError(str(last_error or "find failed"), "transient")


def _apply_storage_result(probe: Probe, result: UploadResult, file_size: int) -> None:
    if result.storage_scope == "file":
        current = probe.max_file_bytes
        tightened = max(0, file_size - 1)
        probe.max_file_bytes = tightened if current is None else min(current, tightened)
        return
    # Account-level quota. Stop offering this account more files this run.
    probe.free_bytes = 0
    probe.unlimited = False
    probe.available = False
    probe.error_class = "storage"


async def place_file(
    accounts: list[StorageAccount],
    probes: dict[str, Probe],
    path: Path,
    filename: str,
    file_size: int,
    margin: int,
    sleeper,
    retry_attempts: int = 4,
) -> Placement:
    by_name = {account.name: account for account in accounts}
    gave_up: set[str] = set()
    placement = Placement(ok=False)
    had_accounts = bool(probes)
    safety = 0

    while True:
        safety += 1
        if safety > len(probes) + 3:
            placement.ok = False
            placement.error = "account selection did not converge"
            placement.error_class = "unknown"
            return placement
        ranked = [
            probe
            for probe in rank_accounts(list(probes.values()), file_size, margin)
            if probe.name not in gave_up and probe.name in by_name
        ]
        if not ranked:
            placement.ok = False
            placement.error_class = _failure_class(placement.attempts, had_accounts)
            if placement.attempts:
                placement.error = placement.attempts[-1].error
            elif had_accounts:
                placement.error = "no account has enough free space for this file"
                placement.error_class = "storage"
            else:
                placement.error = "no storage accounts are configured"
                placement.error_class = "config"
            return placement

        probe = ranked[0]
        account = by_name[probe.name]
        try:
            existing = await _find_with_retries(account, filename, retry_attempts, sleeper)
        except NightshiftError as exc:
            placement.attempts.append(
                Attempt(probe.name, probe.provider, exc.kind, str(exc), retry_attempts)
            )
            # Listing failed. Do not upload blind — that can duplicate a file
            # that actually landed before a crash. Try a different account.
            gave_up.add(probe.name)
            continue

        if existing:
            placement.ok = True
            placement.provider = probe.provider
            placement.account = probe.name
            placement.file_id = existing
            placement.deduped = True
            placement.error = None
            placement.error_class = None
            if not probe.unlimited and probe.free_bytes is not None:
                probe.free_bytes = max(0, probe.free_bytes - file_size)
            return placement

        result = await _upload_with_retries(
            account, path, filename, file_size, retry_attempts, sleeper
        )
        if result.ok and result.file_id:
            placement.ok = True
            placement.provider = probe.provider
            placement.account = probe.name
            placement.file_id = result.file_id
            placement.deduped = False
            placement.error = None
            placement.error_class = None
            if not probe.unlimited and probe.free_bytes is not None:
                probe.free_bytes = max(0, probe.free_bytes - file_size)
            return placement

        error_class = result.error_class or "unknown"
        placement.attempts.append(
            Attempt(
                probe.name,
                probe.provider,
                error_class,
                result.error or "upload failed",
                result.tries or 1,
            )
        )
        if error_class == "auth":
            probe.auth_ok = False
            probe.available = False
            probe.error_class = "auth"
            gave_up.add(probe.name)
            continue
        if error_class == "storage":
            _apply_storage_result(probe, result, file_size)
            continue
        # Transient or unknown, already retried with backoff. Do not zero free space.
        gave_up.add(probe.name)
