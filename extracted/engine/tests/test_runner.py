import asyncio
from datetime import datetime, timezone

from backup.config import Settings
from backup.database import Database
from backup.providers.base import UploadResult
from backup.records import video_key
from backup.runner import execute
from tests.fakes import FakeSource, ListLog, ScriptedAccount, make_probe, video


def settings(tmp_path, **overrides) -> Settings:
    values = dict(
        api_id=1,
        api_hash="hash",
        string_session="session",
        channel="@channel",
        db_path=tmp_path / "backup_db.json",
        download_dir=tmp_path / "downloads",
        log_path=tmp_path / "nightshift.jsonl",
        daily_limit=5,
        history_scan_limit=1000,
        max_runner_file_bytes=10_000_000,
        margin_bytes=0,
        dry_run=False,
        git_commit=False,
        force_unlock=False,
        retry_attempts=3,
        lock_ttl_hours=6,
        accounts=[],
        run_id="run-test",
    )
    values.update(overrides)
    return Settings(**values)


def _account(name, free, provider="gdrive", script=None):
    return ScriptedAccount(name, provider, make_probe(name, provider, free), script=script)


def test_daily_cap_oldest_first_failover_and_no_duplicate(tmp_path):
    # ids 1 and 2 are older. 1 already stored. 2 will hit a full account then land on mega.
    # 3..8 are newer. Cap is 5, so 8 waits. Photo is not a video.
    messages = [
        video(1, 100),
        video(2, 100),
        video(3, 100, name="photo.jpg", is_video=False),
        video(4, 100),
        video(5, 100),
        video(6, 100),
        video(7, 5000),  # nobody can hold this; stays pending
        video(8, 100),
    ]
    source = FakeSource(messages)
    archive = _account(
        "archive",
        10_000,
        script=[UploadResult(ok=False, error="storageQuotaExceeded", error_class="storage")],
    )
    mega = _account("mega-1", 1_000, provider="mega")
    dead = ScriptedAccount(
        "mega-dead",
        "mega",
        make_probe("mega-dead", "mega", 50_000, auth_ok=False, available=False, error_class="auth"),
    )
    log = ListLog()
    code = asyncio.run(
        execute(
            settings=settings(tmp_path),
            source=source,
            accounts=[archive, mega, dead],
            logger=log,
            sleeper=_async_none,
            now=datetime(2026, 1, 3, tzinfo=timezone.utc),
            persist=lambda _message: True,
        )
    )
    assert code == 0
    # Oldest five videos. The photo is ignored. 7 and 8 stay on the backlog.
    assert source.downloads == [1, 2, 4, 5, 6]
    data = Database(tmp_path / "backup_db.json").load()
    stored = [row["message_id"] for row in data["videos"].values() if row["status"] == "success"]
    assert sorted(stored) == [1, 2, 4, 5, 6]
    assert all(row["destination_file_id"] for row in data["videos"].values() if row["status"] == "success")
    assert data["videos"][video_key(-1001, 2)]["account"] == "mega-1"
    assert data["videos"][video_key(-1001, 7)]["status"] == "discovered"
    assert data["videos"][video_key(-1001, 8)]["status"] == "discovered"
    assert video_key(-1001, 3) not in data["videos"]
    assert data["lock"] is None
    assert archive.uploads == ["1_clip-1.mp4"]
    assert len(mega.uploads) == 5
    assert dead.uploads == []
    assert list((tmp_path / "downloads").glob("*")) == []

    # Second night uses fresh probes, the way a new Actions runner would.
    # Only the backlog is downloaded. Message 1 is not fetched again.
    source.downloads.clear()
    fresh_archive = _account("archive", 10_000)
    fresh_mega = _account("mega-1", 1_000, provider="mega")
    code = asyncio.run(
        execute(
            settings=settings(tmp_path, run_id="run-2"),
            source=source,
            accounts=[fresh_archive, fresh_mega],
            logger=ListLog(),
            sleeper=_async_none,
            now=datetime(2026, 1, 4, tzinfo=timezone.utc),
            persist=lambda _message: True,
        )
    )
    assert code == 0
    assert source.downloads == [7, 8]
    again = Database(tmp_path / "backup_db.json").load()
    assert again["videos"][video_key(-1001, 1)]["status"] == "success"
    assert again["videos"][video_key(-1001, 1)]["attempts"] == 1
    assert again["videos"][video_key(-1001, 7)]["status"] == "success"
    assert again["videos"][video_key(-1001, 7)]["account"] == "archive"
    assert again["videos"][video_key(-1001, 8)]["status"] == "success"
    assert 1 not in source.downloads


def test_failed_upload_stays_pending_and_retries_next_run(tmp_path):
    source = FakeSource([video(9, 200)])
    full = _account(
        "only",
        10,
        script=[UploadResult(ok=False, error="EOVERQUOTA", error_class="storage")],
    )
    code = asyncio.run(
        execute(
            settings=settings(tmp_path),
            source=source,
            accounts=[full],
            logger=ListLog(),
            sleeper=_async_none,
            persist=lambda _message: True,
        )
    )
    assert code == 1
    row = Database(tmp_path / "backup_db.json").load()["videos"][video_key(-1001, 9)]
    assert row["status"] == "pending"
    assert row["destination_file_id"] is None
    assert row["error_class"] == "storage"
    assert row["attempts"] == 1

    source.downloads.clear()
    recovered = _account("only", 5_000)
    code = asyncio.run(
        execute(
            settings=settings(tmp_path, run_id="retry"),
            source=source,
            accounts=[recovered],
            logger=ListLog(),
            sleeper=_async_none,
            persist=lambda _message: True,
        )
    )
    assert code == 0
    assert source.downloads == [9]
    row = Database(tmp_path / "backup_db.json").load()["videos"][video_key(-1001, 9)]
    assert row["status"] == "success"
    assert row["account"] == "only"
    assert row["destination_file_id"]


def test_download_failure_does_not_mark_success_and_deleted_message_needs_attention(tmp_path):
    source = FakeSource([video(3), video(4)])
    source.fail_ids.add(3)
    source.permanent_ids.add(4)
    account = _account("home", 5_000)
    code = asyncio.run(
        execute(
            settings=settings(tmp_path),
            source=source,
            accounts=[account],
            logger=ListLog(),
            sleeper=_async_none,
            persist=lambda _message: True,
        )
    )
    assert code == 1
    data = Database(tmp_path / "backup_db.json").load()["videos"]
    assert data[video_key(-1001, 3)]["status"] == "pending"
    assert data[video_key(-1001, 4)]["status"] == "needs_attention"
    assert account.uploads == []
    assert source.downloads == []


def test_dry_run_does_not_download_or_mark_success(tmp_path):
    source = FakeSource([video(11), video(12)])
    account = _account("home", 5_000)
    code = asyncio.run(
        execute(
            settings=settings(tmp_path, dry_run=True),
            source=source,
            accounts=[account],
            logger=ListLog(),
            sleeper=_async_none,
            persist=lambda _message: True,
        )
    )
    assert code == 0
    assert source.downloads == []
    assert account.uploads == []
    rows = Database(tmp_path / "backup_db.json").load()["videos"]
    assert {row["status"] for row in rows.values()} == {"discovered"}


def test_runner_sized_out_video_does_not_consume_the_five(tmp_path):
    messages = [video(1, size=50_000)] + [video(i, size=10) for i in range(2, 8)]
    source = FakeSource(messages)
    account = _account("home", 5_000)
    asyncio.run(
        execute(
            settings=settings(tmp_path, max_runner_file_bytes=1_000),
            source=source,
            accounts=[account],
            logger=ListLog(),
            sleeper=_async_none,
            persist=lambda _message: True,
        )
    )
    data = Database(tmp_path / "backup_db.json").load()["videos"]
    assert data[video_key(-1001, 1)]["status"] == "needs_attention"
    assert 1 not in source.downloads
    assert source.downloads == [2, 3, 4, 5, 6]
    assert data[video_key(-1001, 7)]["status"] == "discovered"


def test_ledger_lock_blocks_a_second_live_run(tmp_path):
    import subprocess
    import sys

    path = tmp_path / "backup_db.json"
    Database(path).save({"version": 1, "lock": None, "scan": {}, "videos": {}, "runs": []})
    lock_path = tmp_path / "backup_db.json.lock"
    holder = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import fcntl,time,sys; fh=open(sys.argv[1],'a+'); fcntl.flock(fh.fileno(), fcntl.LOCK_EX|fcntl.LOCK_NB); sys.stdout.write('held\\n'); sys.stdout.flush(); time.sleep(30)",
            str(lock_path),
        ],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert holder.stdout.readline().strip() == "held"
        source = FakeSource([video(1)])
        code = asyncio.run(
            execute(
                settings=settings(tmp_path),
                source=source,
                accounts=[_account("home", 1000)],
                logger=ListLog(),
                sleeper=_async_none,
                persist=lambda _message: True,
            )
        )
        assert code == 0
        assert source.downloads == []
    finally:
        holder.terminate()
        holder.wait(timeout=5)


async def _async_none(_delay: float = 0) -> None:
    return None
