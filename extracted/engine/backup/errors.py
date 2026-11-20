"""Errors that carry a class so callers never treat a rate limit as a full disk."""

from __future__ import annotations


class NightshiftError(Exception):
    """kind is one of: auth, transient, storage, permanent, unknown, config."""

    def __init__(self, message: str, kind: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.kind = kind
        self.exit_code = exit_code


class LockHeld(NightshiftError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "lock", exit_code=0)


class ConfigError(NightshiftError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "config", exit_code=2)
