"""Map provider failures onto a small set of classes.

Storage-full is only returned for explicit quota signals. Rate limits, HTTP 5xx,
timeouts and unknown 403s stay retryable and must not zero an account's free space.
"""

from __future__ import annotations

import json

from .errors import NightshiftError

# Drive API reasons that mean the account cannot store more bytes.
_DRIVE_STORAGE = {"storagequotaexceeded"}

# Drive API reasons that mean "slow down", not "disk is full".
# quotaExceeded here is the project's request quota, not storageQuota.
_DRIVE_RATE = {
    "userratelimitexceeded",
    "ratelimitexceeded",
    "dailylimitexceeded",
    "quotaexceeded",
    "downloadquotaexceeded",
    "backenderror",
}

_DRIVE_AUTH = {
    "autherror",
    "insufficientpermissions",
    "insufficientfilepermissions",
    "appnotauthorizedtofile",
}

# MEGA integer codes. See mega.errors.
_MEGA_STORAGE = {-17}  # EOVERQUOTA
_MEGA_AUTH = {-11, -14, -15, -16}  # EACCESS, EKEY, ESID, EBLOCKED
_MEGA_TRANSIENT = {-1, -3, -4, -6, -18, -19}  # internal, again, ratelimit, too many, temp, connections


def classify_drive(status: int, reasons: set[str] | list[str], message: str = "") -> str:
    lowered = {str(r).lower() for r in reasons if r}
    text = (message or "").lower()
    if (
        status == 401
        or "invalid_grant" in text
        or "invalid credentials" in text
        or "autheerror" in text
        or lowered & _DRIVE_AUTH
        or "autherror" in lowered
    ):
        return "auth"
    if lowered & _DRIVE_STORAGE or "storage quota" in text or "storagequotaexceeded" in text:
        return "storage"
    if status in (408, 429, 500, 502, 503, 504) or lowered & _DRIVE_RATE:
        return "transient"
    if status == 404:
        return "permanent"
    if status == 403:
        # A bare 403 is not evidence the disk is full.
        return "unknown"
    if status >= 500 or status == 0:
        return "transient"
    return "permanent"


def classify_mega(code: int | None, message: str = "") -> str:
    text = (message or "").lower()
    if code in _MEGA_STORAGE or "eoverquota" in text or "over quota" in text:
        return "storage"
    if code in _MEGA_AUTH or "esid" in text:
        return "auth"
    if code in _MEGA_TRANSIENT:
        return "transient"
    if code is None:
        if any(s in text for s in ("timeout", "timed out", "connection", "temporar", "reset by peer")):
            return "transient"
        return "unknown"
    return "permanent"


def _drive_from_http_body(status: int, payload: str) -> str:
    reasons: set[str] = set()
    message = payload
    try:
        body = json.loads(payload)
    except (ValueError, TypeError):
        body = None
    if isinstance(body, dict):
        err = body.get("error") or {}
        if isinstance(err, dict):
            message = str(err.get("message") or payload)
            for item in err.get("errors") or []:
                if isinstance(item, dict) and item.get("reason"):
                    reasons.add(str(item["reason"]))
    return classify_drive(status, reasons, message)


def classify_exception(exc: BaseException) -> str:
    if isinstance(exc, NightshiftError):
        return exc.kind
    name = type(exc).__name__
    text = str(exc)[:500]
    lowered = text.lower()
    if name == "RefreshError" or "invalid_grant" in lowered:
        return "auth"
    if name in {"HttpError", "ResumableUploadError"}:
        resp = getattr(exc, "resp", None)
        status = int(getattr(resp, "status", 0) or 0)
        content = getattr(exc, "content", b"") or b""
        if isinstance(content, bytes):
            payload = content.decode("utf-8", "replace")
        else:
            payload = str(content)
        return _drive_from_http_body(status, payload or text)
    code = getattr(exc, "code", None)
    if isinstance(code, int) and code < 0:
        return classify_mega(code, text)
    if name in {"FloodWaitError"}:
        return "transient"
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return "transient"
    if any(s in lowered for s in ("timeout", "timed out", "connection reset", "temporarily unavailable")):
        return "transient"
    return "unknown"
