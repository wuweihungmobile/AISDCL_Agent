"""AdvisoryLock 檔案模式（DB 模式見 tests/test_db_integration.py，需 BRIDGE_TEST_DSN）。"""
from __future__ import annotations

import os
import threading

import pytest

from app.locks import AdvisoryLock, LockBusy, make_lock_key


def test_second_acquirer_gets_busy_with_the_holder_id() -> None:
    locks = AdvisoryLock()
    info = locks.acquire("proj", "/work/a", "run-1")
    with pytest.raises(LockBusy) as exc:
        locks.acquire("proj", "/work/a", "run-2")
    assert exc.value.holder_run_id == "run-1"
    locks.release(info.key, "run-1")
    locks.acquire("proj", "/work/a", "run-2")          # 釋放後可再取


def test_different_project_or_path_do_not_collide() -> None:
    locks = AdvisoryLock()
    locks.acquire("p1", "/work/a", "r1")
    locks.acquire("p2", "/work/a", "r2")
    locks.acquire("p1", "/work/b", "r3")


def test_only_the_holder_can_release() -> None:
    locks = AdvisoryLock()
    info = locks.acquire("p", "/w", "r1")
    locks.release(info.key, "someone-else")
    assert locks.holder(info.key) == "r1"
    locks.release(info.key, "r1")
    assert locks.holder(info.key) is None


def test_same_run_may_reacquire_idempotently() -> None:
    locks = AdvisoryLock()
    locks.acquire("p", "/w", "r1")
    locks.acquire("p", "/w", "r1")


def test_exactly_one_of_many_concurrent_acquirers_wins() -> None:
    locks = AdvisoryLock()
    wins: list[str] = []
    busy: list[str] = []

    def work(i: int) -> None:
        try:
            locks.acquire("p", "/w", f"r{i}")
            wins.append(f"r{i}")
        except LockBusy:
            busy.append(f"r{i}")

    threads = [threading.Thread(target=work, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(wins) == 1
    assert len(busy) == 19


def test_key_follows_the_prd_shape_and_normcases_the_path() -> None:
    key = make_lock_key("my-proj", os.path.join("X", "Y"))
    assert key == f"my-proj:{os.path.normcase(os.path.join('X', 'Y'))}"
    assert key.startswith("my-proj:")


def test_file_mode_never_touches_the_database() -> None:
    locks = AdvisoryLock(None)
    assert locks.db_mode is False
    assert locks.acquire("p", "/w", "r").db_key is None


def test_unicode_normalization_forms_of_the_same_path_collide() -> None:
    nfc, nfd = "/work/caf\u00e9", "/work/cafe\u0301"
    assert nfc != nfd
    locks = AdvisoryLock()
    locks.acquire("p", nfc, "r1")
    with pytest.raises(LockBusy):
        locks.acquire("p", nfd, "r2")
