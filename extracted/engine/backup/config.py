"""Settings from the environment. Secrets stay in the environment, never in the ledger."""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from .errors import ConfigError
from .records import clamp_daily_limit

_NAME = re.compile(r"^[A-Za-z0-9._-]{1,40}$")
_TRUE = {"1", "true", "yes", "y", "on"}


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in _TRUE


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer") from exc


@dataclass
class AccountConfig:
    name: str
    provider: str
    max_file_bytes: int | None = None
    client_id: str | None = None
    client_secret: str | None = None
    refresh_token: str | None = None
    folder_id: str | None = None
    email: str | None = None
    password: str | None = None
    folder: str | None = None

    def __repr__(self) -> str:
        return f"AccountConfig(name={self.name!r}, provider={self.provider!r})"


@dataclass
class Settings:
    api_id: int
    api_hash: str
    string_session: str
    channel: str
    db_path: Path
    download_dir: Path
    log_path: Path
    daily_limit: int
    history_scan_limit: int
    max_runner_file_bytes: int
    margin_bytes: int
    dry_run: bool
    git_commit: bool
    force_unlock: bool
    retry_attempts: int
    lock_ttl_hours: float
    accounts: list[AccountConfig]
    run_id: str

    def __repr__(self) -> str:
        return (
            f"Settings(channel={self.channel!r}, daily_limit={self.daily_limit}, "
            f"accounts={len(self.accounts)}, dry_run={self.dry_run}, run_id={self.run_id!r})"
        )


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(f"missing {name}")
    return value


def _optional_bytes(item: dict, label: str) -> int | None:
    raw = item.get("max_file_bytes")
    if raw in (None, "", 0, "0"):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{label} max_file_bytes must be an integer or null") from exc
    if value < 0:
        raise ConfigError(f"{label} max_file_bytes cannot be negative")
    return value


def _account_name(item: dict, label: str) -> str:
    name = str(item.get("name") or "").strip()
    if not _NAME.match(name):
        raise ConfigError(f"{label} name must match {_NAME.pattern}")
    return name


def _parse_gdrive(raw: str) -> list[AccountConfig]:
    try:
        data = json.loads(raw or "[]")
    except json.JSONDecodeError as exc:
        raise ConfigError("GDRIVE_ACCOUNTS_JSON is not valid JSON") from exc
    if not isinstance(data, list):
        raise ConfigError("GDRIVE_ACCOUNTS_JSON must be a JSON array")
    accounts = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ConfigError(f"Google Drive account #{index} must be an object")
        label = f"Google Drive account #{index}"
        name = _account_name(item, label)
        client_id = str(item.get("client_id") or "").strip()
        client_secret = str(item.get("client_secret") or "").strip()
        refresh_token = str(item.get("refresh_token") or "").strip()
        if not client_id or not client_secret or not refresh_token:
            raise ConfigError(f"{label} ({name}) needs client_id, client_secret and refresh_token")
        folder_id = str(item.get("folder_id") or "").strip() or None
        accounts.append(
            AccountConfig(
                name=name,
                provider="gdrive",
                max_file_bytes=_optional_bytes(item, label),
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
                folder_id=folder_id,
            )
        )
    return accounts


def _parse_mega(raw: str) -> list[AccountConfig]:
    try:
        data = json.loads(raw or "[]")
    except json.JSONDecodeError as exc:
        raise ConfigError("MEGA_ACCOUNTS_JSON is not valid JSON") from exc
    if not isinstance(data, list):
        raise ConfigError("MEGA_ACCOUNTS_JSON must be a JSON array")
    accounts = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ConfigError(f"MEGA account #{index} must be an object")
        label = f"MEGA account #{index}"
        name = _account_name(item, label)
        email = str(item.get("email") or "").strip()
        password = str(item.get("password") or "")
        if not email or not password:
            raise ConfigError(f"{label} ({name}) needs email and password")
        folder = str(item.get("folder") or "Nightshift").strip() or "Nightshift"
        accounts.append(
            AccountConfig(
                name=name,
                provider="mega",
                max_file_bytes=_optional_bytes(item, label),
                email=email,
                password=password,
                folder=folder,
            )
        )
    return accounts


def load_accounts() -> list[AccountConfig]:
    drive = _parse_gdrive(os.environ.get("GDRIVE_ACCOUNTS_JSON", "[]"))
    mega = _parse_mega(os.environ.get("MEGA_ACCOUNTS_JSON", "[]"))
    names = [item.name for item in drive + mega]
    if len(names) != len(set(names)):
        raise ConfigError("account names must be unique across Google Drive and MEGA")
    return drive + mega


def load_settings() -> Settings:
    api_id_raw = _require("TELEGRAM_API_ID")
    try:
        api_id = int(api_id_raw)
    except ValueError as exc:
        raise ConfigError("TELEGRAM_API_ID must be an integer") from exc
    scan = _int("HISTORY_SCAN_LIMIT", 2000)
    scan = min(max(scan, 1), 10000)
    retries = _int("RETRY_ATTEMPTS", 4)
    retries = min(max(retries, 1), 8)
    return Settings(
        api_id=api_id,
        api_hash=_require("TELEGRAM_API_HASH"),
        string_session=_require("TELEGRAM_STRING_SESSION"),
        channel=_require("TELEGRAM_CHANNEL"),
        db_path=Path(os.environ.get("BACKUP_DB_PATH", "data/backup_db.json")),
        download_dir=Path(os.environ.get("DOWNLOAD_DIR", "downloads")),
        log_path=Path(os.environ.get("LOG_PATH", "logs/nightshift.jsonl")),
        daily_limit=clamp_daily_limit(_int("DAILY_LIMIT", 5)),
        history_scan_limit=scan,
        max_runner_file_bytes=_int("MAX_RUNNER_FILE_BYTES", 10 * 1024**3),
        margin_bytes=max(0, _int("STORAGE_MARGIN_BYTES", 1024**2)),
        dry_run=_flag("DRY_RUN", False),
        git_commit=_flag("NIGHTSHIFT_GIT_COMMIT", False),
        force_unlock=_flag("FORCE_UNLOCK", False),
        retry_attempts=retries,
        lock_ttl_hours=float(_int("LOCK_TTL_HOURS", 6)),
        accounts=load_accounts(),
        run_id=uuid.uuid4().hex[:12],
    )
