"""Cross-platform advisory file lock used by CONTEXT-LEDGER writers.

M2 QA Round-2 P1-1 fix — Pre/Post hooks both perform read-modify-write on
`build/reports/fsm/CONTEXT-LEDGER-{date}.yaml`. Without a mutex, parallel tool
calls or pre/post interleaving let the later writer overwrite the earlier one
based on a stale `cumulative_tokens` read, silently losing a tokens entry and
delaying the 90/95% budget gate.

Design:
- Advisory (sentinel-file) lock implemented via ``os.open(..., O_CREAT|O_EXCL)``
  so it works identically on Windows and POSIX without needing ``fcntl`` or
  ``msvcrt``.
- Poll interval 50ms; raises ``TimeoutError`` after ``timeout`` seconds.
- Stale-lock recovery: if a sentinel has been untouched for > 30s (process
  crashed / was killed mid-write) it is forcibly removed before retrying.
- Best-effort: lock file carries `{pid, host, ts}` for post-mortem, but the
  protocol doesn't rely on those being readable.
"""
from __future__ import annotations

import contextlib
import datetime as _dt
import os
import socket
import time
from pathlib import Path
from typing import Iterator

_POLL_INTERVAL_SEC = 0.05
_STALE_AFTER_SEC = 30.0


def _write_sentinel(path: Path) -> None:
    payload = (
        f"pid={os.getpid()} "
        f"host={socket.gethostname()} "
        f"ts={_dt.datetime.now(_dt.timezone.utc).isoformat(timespec='seconds')}\n"
    ).encode("utf-8")
    fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)


def _try_unlink(path: Path) -> bool:
    """Best-effort sentinel removal. Returns True when the file is gone.

    R60 A-02 (Windows): both removal sites used to catch only
    ``FileNotFoundError``. On Windows ``unlink`` raises ``PermissionError``
    ([WinError 32]) whenever a third party holds the sentinel open — an AV
    scanner, the search indexer, a backup agent, or the very "post-mortem
    reader" this module's docstring invites. That escaped the context manager
    (an undocumented exception type for callers) *and* leaked the sentinel, so
    the next writer was blocked until the 30s stale threshold. Swallowing it
    here keeps the advisory protocol's own recovery path (``_is_stale``) in
    charge, mirroring ``tools/dev_start.py::_release_bootstrap_lock``'s
    ``except OSError: pass`` precedent for the same "releasing a lock must not
    fail the caller" situation.
    """
    try:
        path.unlink()
    except FileNotFoundError:
        return True   # already gone (another writer reclaimed it) — same as success
    except OSError:
        return False  # still held open by a third party; caller must not spin
    return True


def _is_stale(path: Path) -> bool:
    """Return True if the sentinel is older than _STALE_AFTER_SEC.

    QA Round-3 P2-10: use ``abs()`` so a wall-clock regression (NTP sync,
    Docker snapshot restore, manual clock change) cannot produce a negative
    delta that keeps the sentinel perpetually "fresh" and deadlocks new
    writers. A large negative age is, operationally, even more suspicious
    than a large positive one — both qualify as stale.
    """
    try:
        mtime = path.stat().st_mtime
    except FileNotFoundError:
        return False
    return abs(time.time() - mtime) > _STALE_AFTER_SEC


@contextlib.contextmanager
def file_lock(lock_path: Path, timeout: float = 5.0) -> Iterator[Path]:
    """Acquire an advisory lock on ``lock_path``.

    ``lock_path`` is the sentinel file (not the resource being protected). All
    cooperating processes must pass the SAME path.
    """
    lock_path = Path(lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + max(0.0, timeout)
    while True:
        try:
            _write_sentinel(lock_path)
            break  # acquired
        except FileExistsError:
            # Forcefully remove a stale sentinel — safe because > 30s with
            # no updater implies the holder is dead. If the removal itself
            # fails (Windows: sentinel held open elsewhere) we must NOT retry
            # immediately: `continue` skips the deadline check and the sleep
            # below, so an unremovable stale sentinel would spin at 100% CPU
            # forever. Falling through instead keeps `timeout` authoritative —
            # callers already handle TimeoutError (both CONTEXT-LEDGER hooks
            # have an append-only sidecar fallback for it).
            if _is_stale(lock_path) and _try_unlink(lock_path):
                continue
            if time.time() >= deadline:
                raise TimeoutError(
                    f"file_lock timeout after {timeout:.2f}s on {lock_path}"
                )
            time.sleep(_POLL_INTERVAL_SEC)
    try:
        yield lock_path
    finally:
        _try_unlink(lock_path)


__all__ = ["file_lock"]
