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
            if _is_stale(lock_path):
                # Forcefully remove a stale sentinel — safe because > 30s with
                # no updater implies the holder is dead.
                try:
                    lock_path.unlink()
                except FileNotFoundError:
                    pass
                continue
            if time.time() >= deadline:
                raise TimeoutError(
                    f"file_lock timeout after {timeout:.2f}s on {lock_path}"
                )
            time.sleep(_POLL_INTERVAL_SEC)
    try:
        yield lock_path
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


__all__ = ["file_lock"]
