"""Commit the ledger back to the private repository between videos.

GitHub-hosted runners are disposable. The file in the repo is the database.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_SPACE = re.compile(r"\s+")


def one_line(text: str) -> str:
    return _SPACE.sub(" ", text).strip()[:140]


def repo_root() -> Path | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return Path(out.strip())


def persist_ledger(enabled: bool, db_path: Path, message: str, logger) -> bool:
    """Push the ledger. True when the remote already has this content or the push worked."""
    if not enabled:
        return True
    root = repo_root()
    if root is None:
        logger.event("error", "git_skip", reason="not a git checkout; ledger would be lost")
        return False
    try:
        rel = str(Path(db_path).resolve().relative_to(root))
    except ValueError:
        rel = str(db_path)
    message = one_line(message)
    add = subprocess.run(
        ["git", "add", "--", rel],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if add.returncode != 0:
        logger.event("error", "git_add_failed", detail=(add.stderr or "")[-400:])
        return False
    diff = subprocess.run(["git", "diff", "--cached", "--quiet", "--", rel], cwd=root)
    if diff.returncode == 0:
        return True
    commit = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if commit.returncode != 0:
        logger.event("error", "git_commit_failed", detail=(commit.stderr or "")[-400:])
        return False
    push = subprocess.run(["git", "push"], cwd=root, capture_output=True, text=True)
    if push.returncode != 0:
        logger.event("error", "git_push_failed", detail=(push.stderr or "")[-400:])
        return False
    logger.event("info", "ledger_pushed", message=message)
    return True
