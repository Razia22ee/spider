from backup.classify import classify_drive, classify_exception, classify_mega
from backup.errors import NightshiftError


def test_drive_storage_quota_is_storage_not_rate_limit():
    assert classify_drive(403, {"storageQuotaExceeded"}, "The user has exceeded their Drive storage quota") == "storage"


def test_drive_rate_limits_are_not_storage():
    assert classify_drive(403, {"userRateLimitExceeded"}, "User rate limit exceeded") == "transient"
    assert classify_drive(403, {"rateLimitExceeded"}, "Rate limit") == "transient"
    assert classify_drive(429, {"quotaExceeded"}, "Quota exceeded") == "transient"
    assert classify_drive(403, {"dailyLimitExceeded"}, "Daily limit") == "transient"


def test_bare_403_is_not_storage():
    assert classify_drive(403, set(), "Forbidden") == "unknown"


def test_invalid_grant_is_auth():
    assert classify_drive(400, set(), "invalid_grant") == "auth"
    assert classify_drive(401, set(), "Invalid Credentials") == "auth"


def test_http_5xx_is_transient():
    assert classify_drive(503, set(), "backend error") == "transient"
    assert classify_drive(500, set(), "") == "transient"


def test_mega_overquota_is_storage_and_again_is_transient():
    assert classify_mega(-17, "EOVERQUOTA") == "storage"
    assert classify_mega(-3, "EAGAIN") == "transient"
    assert classify_mega(-4, "ERATELIMIT") == "transient"
    assert classify_mega(-15, "ESID") == "auth"
    assert classify_mega(None, "timed out") == "transient"


def test_exception_wrapper_reads_http_body_without_importing_google():
    class HttpError(Exception):
        def __init__(self):
            super().__init__("boom")
            self.resp = type("R", (), {"status": 403})()
            self.content = b'{"error":{"message":"quota","errors":[{"reason":"userRateLimitExceeded"}]}}'

    assert classify_exception(HttpError()) == "transient"
    assert classify_exception(NightshiftError("no", "storage")) == "storage"
    assert classify_exception(TimeoutError("timed out")) == "transient"
