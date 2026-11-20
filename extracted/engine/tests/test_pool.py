import asyncio
from pathlib import Path

from backup.pool import place_file, rank_accounts
from backup.providers.base import UploadResult
from tests.fakes import ScriptedAccount, make_probe


def _run(coro):
    return asyncio.run(coro)


def test_ranks_most_free_space_and_refuses_unknown_or_small():
    probes = [
        make_probe("small", "gdrive", 500),
        make_probe("big", "mega", 5_000),
        make_probe("unknown", "gdrive", None),
        make_probe("dead", "mega", 9_000, auth_ok=False, available=False, error_class="auth"),
        make_probe("work", "gdrive", None, unlimited=True),
    ]
    ranked = rank_accounts(probes, file_size=800, margin=0)
    assert [item.name for item in ranked] == ["work", "big"]


def test_margin_and_max_file_are_respected():
    probes = [
        make_probe("exact", "gdrive", 1_000),
        make_probe("capped", "mega", 9_000, max_file_bytes=500),
    ]
    assert [item.name for item in rank_accounts(probes, 1_000, margin=1)] == []
    assert [item.name for item in rank_accounts(probes, 400, margin=0)] == ["capped", "exact"]


def test_storage_full_switches_account_and_rate_limit_does_not():
    sleeps: list[float] = []

    async def sleeper(delay: float) -> None:
        sleeps.append(delay)

    archive = ScriptedAccount(
        "archive",
        "gdrive",
        make_probe("archive", "gdrive", 20_000),
        script=[UploadResult(ok=False, error="storageQuotaExceeded", error_class="storage")],
    )
    primary = ScriptedAccount("primary", "mega", make_probe("primary", "mega", 5_000))
    probes = {archive.name: archive._probe, primary.name: primary._probe}
    placement = _run(
        place_file([archive, primary], probes, Path("clip.mp4"), "101_clip.mp4", 800, 0, sleeper, retry_attempts=3)
    )
    assert placement.ok is True
    assert placement.account == "primary"
    assert archive.uploads == ["101_clip.mp4"]
    assert primary.uploads == ["101_clip.mp4"]
    assert archive._probe.available is False
    assert sleeps == []

    home = ScriptedAccount(
        "home",
        "gdrive",
        make_probe("home", "gdrive", 9_000),
        script=[UploadResult(ok=False, error="userRateLimitExceeded", error_class="transient")],
    )
    other = ScriptedAccount("other", "mega", make_probe("other", "mega", 8_000))
    probes = {home.name: home._probe, other.name: other._probe}
    sleeps.clear()
    placement = _run(
        place_file([home, other], probes, Path("clip.mp4"), "102_clip.mp4", 100, 0, sleeper, retry_attempts=3)
    )
    assert placement.ok is True
    assert placement.account == "home"
    assert other.uploads == []
    assert home.uploads == ["102_clip.mp4", "102_clip.mp4"]
    assert sleeps == [2.0]
    assert home._probe.available is True
    assert home._probe.free_bytes == 8_900


def test_existing_remote_file_is_not_uploaded_again():
    account = ScriptedAccount(
        "home",
        "gdrive",
        make_probe("home", "gdrive", 5_000),
        existing="drive-file-1",
    )
    probes = {account.name: account._probe}
    placement = _run(
        place_file([account], probes, Path("clip.mp4"), "5_clip.mp4", 100, 0, lambda _d: _async_none(), 2)
    )
    assert placement.ok is True
    assert placement.deduped is True
    assert placement.file_id == "drive-file-1"
    assert account.uploads == []


async def _async_none(_delay: float = 0) -> None:
    return None


def test_all_accounts_failing_is_not_success():
    full = ScriptedAccount(
        "full",
        "mega",
        make_probe("full", "mega", 50),
        script=[UploadResult(ok=False, error="EOVERQUOTA", error_class="storage")],
    )
    dead = ScriptedAccount(
        "dead",
        "gdrive",
        make_probe("dead", "gdrive", None, auth_ok=False, available=False, error_class="auth"),
    )
    probes = {full.name: full._probe, dead.name: dead._probe}
    placement = _run(place_file([full, dead], probes, Path("c.mp4"), "9_c.mp4", 80, 0, _async_none, 2))
    assert placement.ok is False
    assert placement.file_id is None
    assert placement.error_class == "storage"


def test_list_failure_does_not_upload_blind():
    shaky = ScriptedAccount(
        "shaky",
        "gdrive",
        make_probe("shaky", "gdrive", 5_000),
        existing=TimeoutError("timed out"),
    )
    backup = ScriptedAccount("backup", "mega", make_probe("backup", "mega", 4_000))
    probes = {shaky.name: shaky._probe, backup.name: backup._probe}
    placement = _run(
        place_file([shaky, backup], probes, Path("c.mp4"), "3_c.mp4", 10, 0, _async_none, retry_attempts=2)
    )
    assert shaky.uploads == []
    assert placement.account == "backup"
    assert placement.ok is True
