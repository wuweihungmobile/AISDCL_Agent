"""restore 失敗時的鎖歸屬（runner 層單元測試：不起引擎、不走 HTTP；檔案模式與假 PG 模式各跑一遍）。

終態 run 的鎖早已放掉：restore 先重取，再寫 checkpoint 等準備，最後才 spawn。重取之後、spawn 之前
的任何失敗，都不得讓一個終態 run 繼續持著那把鎖（洩漏到 Bridge 重啟為止，同 project＋path 的新 run
全部 409）。PAUSED run 的鎖本來就是它的、restore 沒有重取：失敗不得放掉（PAUSED 語意不變）。
"""
from __future__ import annotations

import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

import app.runner as runner_module
from app.checkpoints import build_checkpoint_state
from app.errors import ApiError
from app.locks import AdvisoryLock, LockBusy, make_lock_key
from app.logparse import StepDef
from app.runner import RunHandle, RunManager
from app.runstate import RunPaths, RunRecord
from app.security import AuditLog
from app.settings import Settings
from tests.conftest import FakePg

#: 注入失敗的位置＝重取鎖之後、spawn 之前依序會做的第一件、中間一件、最後一件事。
FAILS_AT = ("_adopt_env", "write_engine_checkpoint", "alert")


class LockEnv:
    """一個鎖後端（檔案模式或假 PG）加上「PG 那頭現在長什麼樣子」的探針（檔案模式恆為空）。"""

    def __init__(self, locks: AdvisoryLock, pg: FakePg | None) -> None:
        self.locks = locks
        self.pg = pg

    def live_connections(self) -> int:
        return self.pg.live_connections() if self.pg else 0

    def pg_owners(self) -> dict[str, Any]:
        return dict(self.pg.owners) if self.pg else {}


@pytest.fixture(params=["file", "fake_pg"])
def lock_env(request: pytest.FixtureRequest) -> LockEnv:
    if request.param == "file":
        return LockEnv(AdvisoryLock(), None)
    return LockEnv(AdvisoryLock("postgresql://fake"), request.getfixturevalue("fake_pg"))


@pytest.fixture
def make_handle(settings: Settings, project_dir: Path) -> Callable[..., tuple[RunHandle, str]]:
    def build(env: LockEnv, *, status: str, holding: bool) -> tuple[RunHandle, str]:
        """一個已有一筆歷史 checkpoint（after-T01）的 run；holding＝它此刻持著鎖。"""
        mgr = RunManager(settings, locks=env.locks, audit=AuditLog(None))
        run_id = str(uuid.uuid4())
        paths = RunPaths(settings.engine_workspace / run_id)
        paths.checkpoints.mkdir(parents=True)
        steps = [StepDef("T01", "一", "請輸出 [ONE_DONE]"),
                 StepDef("T02", "二", "請輸出 [TWO_DONE]")]
        rec = RunRecord(run_id=run_id, project="proj", execution_path=str(project_dir),
                        status=status, total_steps=len(steps), completed_step_ids=["T01"],
                        lock_key=make_lock_key("proj", str(project_dir)))
        handle = RunHandle(mgr, rec, paths, steps)
        state = build_checkpoint_state(
            playbook_path=paths.playbook, project="proj", steps=steps, step_idx=1,
            completed_ids=["T01"], completed_log=["[T01] 一 ✓ (attempt 1)"], peak_token_pct=0.0)
        meta = handle.history.add(name="after-T01", step_idx=1, step_id="T02", state=state)
        if holding:
            env.locks.acquire("proj", str(project_dir), run_id)
        return handle, meta["checkpoint_id"]

    return build


def _inject(monkeypatch: pytest.MonkeyPatch, fails_at: str) -> None:
    def boom(*args: Any, **kwargs: Any) -> None:
        raise OSError("磁碟已滿（測試注入）")

    if fails_at == "write_engine_checkpoint":
        monkeypatch.setattr(runner_module, "write_engine_checkpoint", boom)
    else:
        monkeypatch.setattr(RunHandle, fails_at, boom)


@pytest.mark.parametrize("fails_at", FAILS_AT)
def test_a_failed_restore_of_a_finished_run_releases_the_lock_it_just_retook(
        lock_env: LockEnv, make_handle, monkeypatch, fails_at) -> None:
    handle, checkpoint_id = make_handle(lock_env, status="COMPLETED", holding=False)
    _inject(monkeypatch, fails_at)
    with pytest.raises(OSError, match="測試注入"):
        handle.restore(checkpoint_id)
    assert handle.rec.status == "COMPLETED", "失敗的 restore 不改變終態"
    assert lock_env.locks.holder(handle.rec.lock_key) is None, "登記表：終態 run 不得留著鎖"
    assert lock_env.live_connections() == 0, "PG：剛重取的專用連線要關掉"
    assert lock_env.pg_owners() == {}
    lock_env.locks.acquire("proj", handle.rec.execution_path, "next-run")    # 沒有殘留擋路


@pytest.mark.parametrize("fails_at", FAILS_AT)
def test_a_failed_restore_of_a_paused_run_keeps_the_lock_it_already_held(
        lock_env: LockEnv, make_handle, monkeypatch, fails_at) -> None:
    handle, checkpoint_id = make_handle(lock_env, status="PAUSED", holding=True)
    before = (lock_env.live_connections(), lock_env.pg_owners())
    _inject(monkeypatch, fails_at)
    with pytest.raises(OSError, match="測試注入"):
        handle.restore(checkpoint_id)
    assert handle.rec.status == "PAUSED", "失敗的 restore 不改變 PAUSED"
    assert lock_env.locks.holder(handle.rec.lock_key) == handle.rec.run_id, "PAUSED 仍持鎖"
    assert (lock_env.live_connections(), lock_env.pg_owners()) == before, \
        "沒有放掉、也沒有多開連線"
    with pytest.raises(LockBusy):                                           # 依然擋得住別人
        lock_env.locks.acquire("proj", handle.rec.execution_path, "next-run")


def test_a_spawn_failure_after_restoring_a_finished_run_leaves_no_lock_either(
        lock_env: LockEnv, make_handle, monkeypatch) -> None:
    """spawn 本身失敗由 `_spawn` 自己收尾（FAILED＋放鎖）；與上面兩個合起來，
    重取之後的每個失敗點都不留鎖。"""
    handle, checkpoint_id = make_handle(lock_env, status="COMPLETED", holding=False)

    def cannot_spawn(*args: Any, **kwargs: Any) -> None:
        raise OSError("無法執行（測試注入）")

    monkeypatch.setattr(runner_module.subprocess, "Popen", cannot_spawn)
    with pytest.raises(ApiError) as exc:
        handle.restore(checkpoint_id)
    assert (exc.value.status_code, exc.value.body["reason"]) == (500, "spawn_failed")
    assert handle.rec.status == "FAILED"
    assert lock_env.locks.holder(handle.rec.lock_key) is None
    assert lock_env.live_connections() == 0
    assert lock_env.pg_owners() == {}
