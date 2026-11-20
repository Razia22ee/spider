"""Entry point used by GitHub Actions: python -m backup"""

from __future__ import annotations

import asyncio
import sys

from .config import load_settings
from .errors import ConfigError, NightshiftError
from .log import RunLog
from .providers.gdrive import GoogleDriveAccount
from .providers.mega_provider import MegaAccount
from .runner import execute
from .telegram_source import TelegramSource


def build_accounts(settings):
    accounts = []
    for config in settings.accounts:
        if config.provider == "gdrive":
            accounts.append(GoogleDriveAccount(config))
        elif config.provider == "mega":
            accounts.append(MegaAccount(config))
        else:
            raise ConfigError(f"unknown provider {config.provider}")
    return accounts


async def _async_main(settings, logger) -> int:
    source = TelegramSource(
        settings.api_id,
        settings.api_hash,
        settings.string_session,
        settings.channel,
    )
    accounts = build_accounts(settings)
    logger.event(
        "info",
        "run_start",
        run_id=settings.run_id,
        dry_run=settings.dry_run,
        daily_limit=settings.daily_limit,
        accounts=[item.name for item in accounts],
    )
    return await execute(settings=settings, source=source, accounts=accounts, logger=logger)


def main() -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:
        sys.stderr.write(f"configuration error: {exc}\n")
        return 2
    logger = RunLog(settings.log_path)
    try:
        return asyncio.run(_async_main(settings, logger))
    except NightshiftError as exc:
        logger.event("error", "fatal", error_class=exc.kind, error=str(exc)[:400])
        return exc.exit_code or 1
    except Exception as exc:
        logger.event("error", "fatal", error_class="unknown", error=str(exc)[:400])
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
