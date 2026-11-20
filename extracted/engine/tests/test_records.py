from datetime import datetime, timedelta, timezone

from backup.media import is_video_message, message_to_remote, sanitize_filename
from backup.records import (
    clamp_daily_limit,
    empty_db,
    note_discovered,
    select_pending,
    video_key,
)
from backup.runner import take_run_lock
from tests.fakes import video


class Msg:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_ignores_photos_gifs_and_keeps_real_videos():
    photo = Msg(id=1, photo=object(), video=None, gif=None, sticker=None, document=None)
    gif = Msg(id=2, gif=object(), video=None, sticker=None, document=MsgDoc("video/mp4"))
    video_msg = Msg(id=3, video=object(), gif=None, sticker=None, document=None, file=File("lecture.mp4", 10, "video/mp4", ".mp4"), date=None)
    doc = Msg(id=4, video=None, gif=None, sticker=None, document=MsgDoc("video/webm"), file=File("clip.webm", 4, "video/webm", ".webm"), date=None)
    pdf = Msg(id=5, video=None, gif=None, sticker=None, document=MsgDoc("application/pdf"), file=File("a.pdf", 2, "application/pdf", ".pdf"))
    assert is_video_message(photo) is False
    assert is_video_message(gif) is False
    assert message_to_remote(photo, -100) is None
    assert message_to_remote(pdf, -100) is None
    assert message_to_remote(video_msg, -100).filename == "lecture.mp4"
    assert message_to_remote(doc, -100).filename == "clip.webm"


class MsgDoc:
    def __init__(self, mime):
        self.mime_type = mime
        self.attributes = []


class File:
    def __init__(self, name, size, mime, ext):
        self.name = name
        self.size = size
        self.mime_type = mime
        self.ext = ext


def test_sanitize_strips_paths():
    assert sanitize_filename("../etc/passwd", "fallback.mp4") == "passwd"
    assert sanitize_filename("", "fallback.mp4") == "fallback.mp4"
    assert "/" not in sanitize_filename("a/b\\c.mp4", "x")


def test_daily_limit_never_exceeds_five():
    assert clamp_daily_limit(5) == 5
    assert clamp_daily_limit(99) == 5
    assert clamp_daily_limit(0) == 0
    assert clamp_daily_limit(-3) == 0


def test_selects_oldest_pending_and_skips_success():
    db = empty_db()
    now = "2026-01-01T00:00:00+00:00"
    for item in (video(30), video(10), video(20), video(40, is_video=False), video(15)):
        if item.is_video:
            note_discovered(db["videos"], item, now, max_runner_file_bytes=10**12)
    db["videos"][video_key(-1001, 10)]["status"] = "success"
    huge = video(5, size=10**12)
    assert note_discovered(db["videos"], huge, now, max_runner_file_bytes=100) == "needs_attention"
    chosen = select_pending(db["videos"], 99)
    assert [row["message_id"] for row in chosen] == [15, 20, 30]
    assert all(row["status"] != "success" for row in chosen)


def test_failed_row_is_retried_and_success_is_not_downgraded():
    db = empty_db()
    now = "2026-01-01T00:00:00+00:00"
    note_discovered(db["videos"], video(7), now, 10**9)
    row = db["videos"][video_key(-1001, 7)]
    row["status"] = "pending"
    row["attempts"] = 2
    note_discovered(db["videos"], video(7, name="renamed.mp4"), now, 10**9)
    assert row["status"] == "pending"
    assert row["filename"] == "renamed.mp4"
    assert row["attempts"] == 2
    row["status"] = "success"
    row["destination_file_id"] = "abc"
    assert note_discovered(db["videos"], video(7, name="other.mp4"), now, 10**9) == "unchanged"
    assert row["destination_file_id"] == "abc"
    assert select_pending(db["videos"], 5) == []


def test_run_lock_respects_ttl_and_force():
    data = empty_db()
    now = datetime(2026, 1, 2, tzinfo=timezone.utc)
    assert take_run_lock(data, run_id="a", now=now, ttl_hours=6, force=False) is True
    assert take_run_lock(data, run_id="b", now=now + timedelta(hours=1), ttl_hours=6, force=False) is False
    assert take_run_lock(data, run_id="c", now=now + timedelta(hours=1), ttl_hours=6, force=True) is True
    assert data["lock"]["run_id"] == "c"
    assert take_run_lock(data, run_id="d", now=now + timedelta(hours=8), ttl_hours=6, force=False) is True
