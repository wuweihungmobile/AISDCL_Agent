"""AdvisoryLock：檔案模式，以及用假 PG（tests/conftest.py 的 `fake_pg`）跑的 DB 模式邏輯
（真 PG 版見 tests/test_db_integration.py，需 BRIDGE_TEST_DSN）。"""
from __future__ import annotations

import os
import threading

import pytest

from app.locks import AdvisoryLock, LockBusy, LockUnavailable, make_lock_key
from tests.conftest import FakePg


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


# ── DB 模式（假 PG：只模擬 session 級鎖屬於「連線」那一小塊語意，見 tests/conftest.py）──────
def test_db_mode_the_same_run_reacquires_idempotently_on_its_existing_connection(
        fake_pg: FakePg) -> None:
    locks = AdvisoryLock("postgresql://fake")
    first = locks.acquire("p", "/w", "r1")
    again = locks.acquire("p", "/w", "r1")      # PAUSED 的 run 做 restore，走的就是這一步（AR-01）
    assert first.db_key is not None
    assert again == first
    assert len(fake_pg.connections) == 1, "冪等：不新開連線——新連線只會被自己的舊連線擋下"
    assert locks.holder(first.key) == "r1"


def test_db_mode_a_different_run_stays_excluded_and_its_failed_attempt_changes_nothing(
        fake_pg: FakePg) -> None:
    locks = AdvisoryLock("postgresql://fake")
    first = locks.acquire("p", "/w", "r1")
    locks.acquire("p", "/w", "r1")
    with pytest.raises(LockBusy) as exc:
        locks.acquire("p", "/w", "r2")
    assert exc.value.holder_run_id == "r1"
    assert locks.holder(first.key) == "r1", "別的 run 失敗的取鎖不得動到持有者的登記"
    assert fake_pg.owners == {first.key: fake_pg.connections[0]}
    assert len(fake_pg.connections) == 1
    with pytest.raises(LockBusy):               # 另一個實例（獨立的 AdvisoryLock）被 PG 擋下
        AdvisoryLock("postgresql://fake").acquire("p", "/w", "r3")


def test_db_mode_release_after_a_reacquire_closes_the_connection_and_frees_the_lock(
        fake_pg: FakePg) -> None:
    locks = AdvisoryLock("postgresql://fake")
    first = locks.acquire("p", "/w", "r1")
    locks.acquire("p", "/w", "r1")
    locks.release(first.key, "r1")
    assert fake_pg.connections[0].closed
    assert fake_pg.owners == {}
    assert locks.holder(first.key) is None
    locks.acquire("p", "/w", "r2")              # 釋放後別的 run 取得


def test_db_mode_release_still_closes_the_connection_when_the_registration_is_already_gone(
        fake_pg: FakePg) -> None:
    """縱深：登記表與連線表一旦不同步（AR-01 洩漏的成因），
    release 不得再因登記表早退而讓連線永遠不關。"""
    locks = AdvisoryLock("postgresql://fake")
    first = locks.acquire("p", "/w", "r1")
    locks._table.release(first.key, "r1")       # 白箱：人為製造不同步
    locks.release(first.key, "r1")
    assert fake_pg.connections[0].closed
    assert fake_pg.owners == {}


def test_db_mode_a_failed_first_acquire_leaves_no_registration_behind(fake_pg: FakePg) -> None:
    fake_pg.down = True
    locks = AdvisoryLock("postgresql://fake")
    with pytest.raises(LockUnavailable):
        locks.acquire("p", "/w", "r1")
    assert locks.holder(make_lock_key("p", "/w")) is None, "DB 層失敗：行程內那層不得留著"
    fake_pg.down = False
    locks.acquire("p", "/w", "r2")              # 沒有殘留登記擋路


def test_db_mode_a_failed_attempt_never_removes_a_registration_it_did_not_add(
        fake_pg: FakePg) -> None:
    locks = AdvisoryLock("postgresql://fake")
    first = locks.acquire("p", "/w", "r1")
    locks.close()                               # 連線全關（如 Bridge 關閉）、登記表沒動
    fake_pg.down = True
    with pytest.raises(LockUnavailable):
        locks.acquire("p", "/w", "r1")
    assert locks.holder(first.key) == "r1", "登記不是這次呼叫新增的：失敗不得撤掉"
    fake_pg.down = False
    assert locks.acquire("p", "/w", "r1").key == first.key    # DB 回來就補上連線
    assert len(fake_pg.connections) == 2
    assert fake_pg.owners == {first.key: fake_pg.connections[1]}


def test_db_mode_a_busy_pg_lock_rolls_back_only_the_registration_this_call_added(
        fake_pg: FakePg) -> None:
    other_instance = AdvisoryLock("postgresql://fake")
    held = other_instance.acquire("p", "/w", "r1")
    mine = AdvisoryLock("postgresql://fake")
    with pytest.raises(LockBusy):               # 同實例的登記表是空的，真正擋人的是 PG
        mine.acquire("p", "/w", "r2")
    assert mine.holder(held.key) is None, "被 PG 擋下：這次新增的登記要撤回"
    assert fake_pg.owners == {held.key: fake_pg.connections[0]}, "對方的鎖與連線不受影響"
    other_instance.release(held.key, "r1")
    mine.acquire("p", "/w", "r2")
