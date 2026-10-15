"""DB 模式整合測試：只在 BRIDGE_TEST_DSN 指向一個可寫的 PostgreSQL 時才跑（否則整組跳過）。

每個測試在自己的臨時 schema 內建立 PRD §6.2 的三張表（外加 projects／tasks 的最小替身），
結束時整個 schema 一併丟棄；`public` 裡另放同名誘餌表，證明 Bridge 的 SQL 一律用 schema 限定名。
"""
from __future__ import annotations

import os
import time
import uuid
from collections.abc import Callable, Iterator
from dataclasses import replace
from typing import Any

import psycopg
import pytest
from psycopg import sql

import app.runner as runner_module
from app.db import BridgeDb
from app.locks import AdvisoryLock, LockBusy, make_lock_key
from tests.conftest import TERMINAL, mock_playbook

DSN = os.environ.get("BRIDGE_TEST_DSN", "")
pytestmark = [
    pytest.mark.db,
    pytest.mark.skipif(not DSN, reason="未設定 BRIDGE_TEST_DSN（只在有 PostgreSQL 時跑）"),
]

_DDL = """
CREATE SCHEMA {s};
CREATE TABLE {s}.projects (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name TEXT);
CREATE TABLE {s}.tasks (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), title TEXT);
CREATE TABLE {s}.execution_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES {s}.projects(id),
    run_number INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'INITIALIZING'
        CHECK (status IN ('INITIALIZING','RUNNING','PAUSED','COMPLETED','FAILED','CANCELLED')),
    autonomy_level INTEGER NOT NULL, scope JSONB NOT NULL,
    total_tokens_used BIGINT DEFAULT 0, token_budget BIGINT,
    advisory_lock_key BIGINT, subprocess_pid INTEGER, bridge_instance VARCHAR(100),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(), completed_at TIMESTAMP WITH TIME ZONE,
    dag JSONB, UNIQUE (project_id, run_number));
CREATE TABLE {s}.execution_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES {s}.execution_runs(id),
    task_id UUID NOT NULL REFERENCES {s}.tasks(id),
    step_number INTEGER NOT NULL, action VARCHAR(500) NOT NULL, status VARCHAR(20) NOT NULL,
    input JSONB, output TEXT, tokens_used BIGINT, error_message TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW());
CREATE TABLE {s}.checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES {s}.execution_runs(id),
    name VARCHAR(200) NOT NULL, state_snapshot JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(), is_automatic BOOLEAN DEFAULT TRUE);
"""
_DECOY = ("execution_runs", "execution_steps", "checkpoints")


class Pg:
    def __init__(self, schema: str):
        self.schema = schema

    def q(self, query: str, *params: Any) -> list[tuple]:
        with psycopg.connect(DSN, autocommit=True) as conn:
            return conn.execute(query.replace("{s}", self.schema), params).fetchall()

    def exec(self, query: str, *params: Any) -> None:
        with psycopg.connect(DSN, autocommit=True) as conn:
            conn.execute(query.replace("{s}", self.schema), params)

    def seed_run(self, run_id: str, n_tasks: int = 3) -> list[str]:
        project, tasks = uuid.uuid4(), [uuid.uuid4() for _ in range(n_tasks)]
        self.exec("INSERT INTO {s}.projects (id, name) VALUES (%s, 'p')", project)
        for t in tasks:
            self.exec("INSERT INTO {s}.tasks (id, title) VALUES (%s, 't')", t)
        self.exec("INSERT INTO {s}.execution_runs "
                  "(id, project_id, run_number, autonomy_level, scope) "
                  "VALUES (%s, %s, 1, 3, '{}')", uuid.UUID(run_id), project)
        return [str(t) for t in tasks]

    def run_row(self, run_id: str) -> dict[str, Any]:
        cols = ("status", "subprocess_pid", "bridge_instance", "advisory_lock_key",
                "total_tokens_used", "completed_at")
        row = self.q(f"SELECT {', '.join(cols)} FROM {{s}}.execution_runs WHERE id = %s",
                     uuid.UUID(run_id))[0]
        return dict(zip(cols, row, strict=True))


@pytest.fixture
def pg() -> Iterator[Pg]:
    schema = f"bridge_t_{uuid.uuid4().hex[:8]}"
    handle = Pg(schema)
    handle.exec(_DDL.replace("{s}", schema))
    for table in _DECOY:                        # 誘餌：public 裡同名的表（引擎自己的 alembic 也有）
        handle.exec(f"CREATE TABLE IF NOT EXISTS public.{table} (id UUID, note TEXT)")
    yield handle
    handle.exec(f"DROP SCHEMA {schema} CASCADE")
    for table in _DECOY:
        handle.exec(f"DELETE FROM public.{table}")


@pytest.fixture
def db_bridge(make_bridge, settings, pg) -> Callable[..., Any]:
    cfg = replace(settings, db_dsn=DSN, db_schema=pg.schema)
    return lambda **kw: make_bridge(cfg, **kw)


def test_deep_health_pings_the_real_database(db_bridge, pg: Pg) -> None:
    """契約 §3.1.1：設了 BRIDGE_DB_DSN 才 ping，通過時 `db.ok` 為 true
    （沒設時是 null，見 test_health_deep）。"""
    live = db_bridge()
    body = live.client.get("/health/deep").json()      # git 是否在這台機器上不是本測試的主題
    assert body["checks"]["db"] == {"ok": True}
    assert body["checks"]["workspace"] == {"ok": True}


def _wait(pred: Callable[[], Any], timeout: float = 30.0) -> Any:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        got = pred()
        if got:
            return got
        time.sleep(0.1)
    raise AssertionError("等待逾時")


def _advisory_holders(pg: Pg, key: str) -> list[int]:
    """持有這把 advisory lock（hashtext(key)）的 PG 後端 pid；沒人持有＝空清單。session 級鎖綁連線：
    pid 還在＝那條專用連線還活著、鎖還在；清單變空才代表鎖真的釋放。key 在 pg_locks 裡拆成
    classid（高 32 位）＋objid（低 32 位）。"""
    rows = pg.q("SELECT pid FROM pg_locks WHERE locktype = 'advisory' AND objsubid = 1 "
                "AND ((classid::bigint << 32) | objid::bigint) = hashtext(%s)::bigint "
                "ORDER BY pid", key)
    return [r[0] for r in rows]


def _backend_alive(pg: Pg, pid: int) -> bool:
    return pg.q("SELECT count(*) FROM pg_stat_activity WHERE pid = %s", pid)[0][0] > 0


def _disk_full(*args: Any, **kwargs: Any) -> None:
    raise OSError("磁碟已滿（測試注入）")


def _body(run_body, task_ids: list[str] | None, **kw):
    playbook = mock_playbook()
    for task, tid in zip(playbook["tasks"], task_ids or [], strict=False):
        task["goal_task_id"] = tid
    return run_body(playbook=playbook, **kw)


def test_the_bridge_mirrors_state_steps_and_checkpoints_into_the_console_schema(
        db_bridge, pg, run_body) -> None:
    body = _body(run_body, None, delay="0.2")
    task_ids = pg.seed_run(body["run_id"])
    body = _body(run_body, task_ids, delay="0.2", run_id=body["run_id"])
    live = db_bridge()
    health = live.client.get("/health").json()
    assert health["db"] == {"enabled": True, "schema": pg.schema, "ok": True}

    created = live.post_run(body)
    assert created.status_code == 201, created.text
    rid = body["run_id"]
    final = live.wait_status(rid, TERMINAL)
    assert final["status"] == "COMPLETED"
    row = _wait(lambda: (r := pg.run_row(rid)) and r["status"] == "COMPLETED" and r)
    assert row["completed_at"] is not None
    assert row["subprocess_pid"] is None, "行程結束後 PID 要清掉（孤兒回收用）"
    assert row["bridge_instance"] == "test-bridge"
    assert isinstance(row["advisory_lock_key"], int)
    assert row["total_tokens_used"] == 3 * 1240

    step_rows = pg.q("SELECT step_number, status, action, input FROM {s}.execution_steps "
                     "WHERE run_id = %s ORDER BY step_number", uuid.UUID(rid))
    events = [e for e in live.events(rid) if e["event"] == "step"]
    assert [r[0] for r in step_rows] == [e["seq"] for e in events], \
        "execution_steps.step_number 對應 SSE 事件序（PRD §7.1.7）"
    assert [r[1] for r in step_rows] == [e["status"] for e in events]
    assert step_rows[0][2].startswith("T01: ")
    assert step_rows[0][3]["position"] == 1

    cps = live.client.get(f"/autoclaude/runs/{rid}/checkpoints").json()
    db_cps = pg.q("SELECT id, name, is_automatic, state_snapshot->>'step_idx' "
                  "FROM {s}.checkpoints WHERE run_id = %s ORDER BY created_at", uuid.UUID(rid))
    assert [str(r[0]) for r in db_cps] == [c["checkpoint_id"] for c in cps]
    assert [r[1] for r in db_cps] == ["after-T01", "after-T02", "after-T03"]
    assert [int(r[3]) for r in db_cps] == [1, 2, 3]

    for table in _DECOY:
        assert pg.q(f"SELECT count(*) FROM public.{table}")[0][0] == 0, \
            f"public.{table} 不得被碰：SQL 必須用 schema 限定名"


def test_transient_states_are_folded_into_the_six_states_the_check_constraint_allows(
        db_bridge, pg, run_body) -> None:
    body = run_body(delay="0.8")
    pg.seed_run(body["run_id"])
    live = db_bridge()
    live.post_run(body)
    rid = body["run_id"]
    live.client.post(f"/autoclaude/runs/{rid}:pause")
    assert live.get_run(rid)["status"] == "PAUSING"
    assert pg.run_row(rid)["status"] == "RUNNING", "PAUSING 寫進 PG 時折回 RUNNING"
    live.wait_status(rid, {"PAUSED"})
    assert _wait(lambda: pg.run_row(rid)["status"] == "PAUSED")
    live.client.post(f"/autoclaude/runs/{rid}:resume")
    live.client.post(f"/autoclaude/runs/{rid}:stop")
    assert pg.run_row(rid)["status"] in {"RUNNING", "CANCELLED"}, "CANCELLING 折回 RUNNING"
    live.wait_status(rid, {"CANCELLED"})
    assert _wait(lambda: pg.run_row(rid)["status"] == "CANCELLED")
    assert pg.run_row(rid)["completed_at"] is not None


def test_a_run_without_a_db_row_still_completes_and_nothing_is_written(
        db_bridge, pg, run_body) -> None:
    body = run_body(delay="0.1")                       # 沒有 seed：execution_runs 沒有這一列
    live = db_bridge()
    live.post_run(body)
    assert live.wait_status(body["run_id"], TERMINAL)["status"] == "COMPLETED"
    for table in ("execution_runs", "execution_steps", "checkpoints"):
        assert pg.q(f"SELECT count(*) FROM {{s}}.{table}")[0][0] == 0


def test_the_advisory_lock_excludes_across_bridge_instances_and_names_the_holder(
        make_bridge, settings, pg, run_body, tmp_path) -> None:
    cfg_a = replace(settings, db_dsn=DSN, db_schema=pg.schema, bridge_instance="bridge-a")
    cfg_b = replace(cfg_a, bridge_instance="bridge-b",
                    engine_workspace=tmp_path / "workspace-b")
    first, second = make_bridge(cfg_a), make_bridge(cfg_b)
    body_a = run_body(delay="1.5")
    pg.seed_run(body_a["run_id"])
    assert first.post_run(body_a).status_code == 201

    body_b = run_body(delay="0.1")                     # 同 project＋同 execution_path
    clash = second.post_run(body_b)
    assert clash.status_code == 409, clash.text
    assert clash.json() == {"code": 409, "reason": "advisory_lock_held",
                            "holder_run_id": body_a["run_id"]}

    first.wait_status(body_a["run_id"], TERMINAL)
    assert _wait(lambda: second.post_run(run_body(delay="0.1")).status_code == 201)


def test_advisory_lock_connection_loss_releases_the_lock(pg) -> None:
    holder = BridgeDb(DSN, pg.schema)
    holder.open()
    first = AdvisoryLock(DSN, holder_lookup=holder.find_lock_holder)
    info = first.acquire("proj", "/work", "run-1")
    other = AdvisoryLock(DSN)
    with pytest.raises(LockBusy):
        other.acquire("proj", "/work", "run-2")
    first.release(info.key, "run-1")
    other.acquire("proj", "/work", "run-2")
    other.close()
    first.close()
    holder.close()


# ── AR-01：PAUSED 的 run restore 不得撞上自己的 PG 鎖 ─────────────────────────────
def test_in_db_mode_the_same_holder_reacquires_idempotently_without_a_second_connection(
        pg, monkeypatch) -> None:
    opened: list[str] = []
    real_connect = psycopg.connect

    def counting_connect(*args: Any, **kwargs: Any) -> psycopg.Connection:
        opened.append("connect")
        return real_connect(*args, **kwargs)

    path = f"/work/{uuid.uuid4().hex}"                 # 每個測試各用一把鎖（xdist 互不干擾）
    locks, successor = AdvisoryLock(DSN), AdvisoryLock(DSN)
    monkeypatch.setattr(psycopg, "connect", counting_connect)
    try:
        first = locks.acquire("proj", path, "run-1")
        holders = _advisory_holders(pg, first.key)
        assert len(holders) == 1
        before = len(opened)
        again = locks.acquire("proj", path, "run-1")   # PAUSED 的 run 做 restore，走的就是這一步
        assert len(opened) == before, "同 holder 重取不得新開連線（新連線只會被自己的舊連線擋下）"
        assert again == first
        assert _advisory_holders(pg, first.key) == holders, "仍是同一條連線持有、而且只有一條"

        locks.release(first.key, "run-1")              # 放一次就乾淨：沒有殘留的第二條連線
        assert _wait(lambda: not _advisory_holders(pg, first.key))
        assert _wait(lambda: not _backend_alive(pg, holders[0])), "專用連線要關掉，不只是解鎖"
        successor.acquire("proj", path, "run-2")
    finally:
        successor.close()
        locks.close()


def test_in_db_mode_a_different_run_is_still_excluded_after_the_holder_reacquired(pg) -> None:
    path = f"/work/{uuid.uuid4().hex}"
    locks, other_instance = AdvisoryLock(DSN), AdvisoryLock(DSN)
    try:
        first = locks.acquire("proj", path, "run-1")
        locks.acquire("proj", path, "run-1")
        holders = _advisory_holders(pg, first.key)
        assert len(holders) == 1
        with pytest.raises(LockBusy) as same_instance:
            locks.acquire("proj", path, "run-2")
        assert same_instance.value.holder_run_id == "run-1"
        with pytest.raises(LockBusy):                  # 另一個 Bridge 實例：由 PG 擋下
            other_instance.acquire("proj", path, "run-3")
        assert locks.holder(first.key) == "run-1", "失敗的取鎖不得讓持有者脫離登記"
        assert _advisory_holders(pg, first.key) == holders, "持有者的連線與鎖原封不動"

        locks.release(first.key, "run-1")
        assert _wait(lambda: not _advisory_holders(pg, first.key))
        other_instance.acquire("proj", path, "run-3")  # 釋放後才換別人
    finally:
        other_instance.close()
        locks.close()


def test_restoring_a_paused_run_reuses_its_pg_lock_and_releases_it_at_the_terminal_state(
        db_bridge, pg, run_body) -> None:
    body = run_body(delay="0.8")
    rid = body["run_id"]
    pg.seed_run(rid)
    live = db_bridge()
    assert live.post_run(body).status_code == 201
    assert live.client.post(f"/autoclaude/runs/{rid}:pause").status_code == 202
    paused = live.wait_status(rid, {"PAUSED"})
    key = make_lock_key(body["project"], paused["execution_path"])
    holders = _advisory_holders(pg, key)
    assert len(holders) == 1, f"PAUSED 期間持鎖（設計）：恰好一條專用連線；實得 {holders}"

    checkpoint = live.client.get(f"/autoclaude/runs/{rid}/checkpoints").json()[0]
    resp = live.client.post(f"/autoclaude/runs/{rid}/restore",
                            json={"checkpoint_id": checkpoint["checkpoint_id"]})
    assert resp.status_code == 202, resp.text          # 修復前：409（holder 是自己）
    assert resp.json() == {"status": "RUNNING"}
    assert _advisory_holders(pg, key) == holders, "restore 沿用原本那條連線：沒有第二條、也沒有換手"

    final = live.wait_status(rid, TERMINAL)
    assert (final["status"], final["completed_steps"]) == ("COMPLETED", 3)
    assert _wait(lambda: not _advisory_holders(pg, key)), "終態：PG 鎖要放掉"
    assert _wait(lambda: not _backend_alive(pg, holders[0])), "終態：專用連線要關掉，不只是解鎖"
    assert _wait(lambda: pg.run_row(rid)["status"] == "COMPLETED")

    again = run_body(delay="0.1")                      # 鎖沒有洩漏：同 project＋path 可再開
    assert live.post_run(again).status_code == 201
    live.wait_status(again["run_id"], TERMINAL)


def test_restoring_a_finished_run_retakes_the_pg_lock_and_releases_it_again(
        db_bridge, pg, run_body) -> None:
    """另一個分支：終態的 run 已放鎖，restore 要真的重取（新連線），再跑到終態時放掉。"""
    body = run_body(delay="0.4")
    rid = body["run_id"]
    pg.seed_run(rid)
    live = db_bridge()
    assert live.post_run(body).status_code == 201
    done = live.wait_status(rid, TERMINAL)
    assert done["status"] == "COMPLETED"
    key = make_lock_key(body["project"], done["execution_path"])
    assert _wait(lambda: not _advisory_holders(pg, key)), "終態：PG 鎖已放"

    checkpoint = live.client.get(f"/autoclaude/runs/{rid}/checkpoints").json()[0]
    resp = live.client.post(f"/autoclaude/runs/{rid}/restore",
                            json={"checkpoint_id": checkpoint["checkpoint_id"]})
    assert resp.status_code == 202, resp.text
    holders = _advisory_holders(pg, key)
    assert len(holders) == 1, f"終態 restore 重新取得 PG 鎖：恰好一條專用連線；實得 {holders}"

    final = live.wait_status(rid, {"COMPLETED"})
    assert final["completed_steps"] == 3
    assert _wait(lambda: not _advisory_holders(pg, key)), "再度終態：PG 鎖要放掉"
    assert _wait(lambda: not _backend_alive(pg, holders[0])), "再度終態：專用連線要關掉"


def test_a_second_run_stays_excluded_while_the_first_is_paused_restored_and_until_it_stops(
        db_bridge, pg, run_body) -> None:
    body = run_body(delay="0.8")
    rid = body["run_id"]
    pg.seed_run(rid)
    live = db_bridge()
    assert live.post_run(body).status_code == 201
    assert live.client.post(f"/autoclaude/runs/{rid}:pause").status_code == 202
    paused = live.wait_status(rid, {"PAUSED"})
    key = make_lock_key(body["project"], paused["execution_path"])
    rival = run_body(delay="0.1")                      # 同 project＋同 execution_path
    held = {"code": 409, "reason": "advisory_lock_held", "holder_run_id": rid}

    clash = live.post_run(rival)
    assert (clash.status_code, clash.json()) == (409, held), "PAUSED 期間持鎖"
    checkpoint = live.client.get(f"/autoclaude/runs/{rid}/checkpoints").json()[0]
    restored = live.client.post(f"/autoclaude/runs/{rid}/restore",
                                json={"checkpoint_id": checkpoint["checkpoint_id"]})
    assert restored.status_code == 202, restored.text
    clash = live.post_run(rival)
    assert (clash.status_code, clash.json()) == (409, held), "restore 之後仍持鎖"

    assert live.client.post(f"/autoclaude/runs/{rid}:stop").status_code == 202
    live.wait_status(rid, {"CANCELLED"})
    assert _wait(lambda: not _advisory_holders(pg, key)), "stop：PG 鎖要放掉"
    assert live.post_run(rival).status_code == 201, "鎖放掉之後同 project＋path 可再開"
    live.wait_status(rival["run_id"], TERMINAL)


def test_a_failed_restore_of_a_finished_run_releases_the_pg_lock_it_just_retook(
        db_bridge, pg, run_body) -> None:
    """終態 run 重取鎖之後、spawn 之前失敗：run 維持終態、鎖與連線都放掉，再 restore 一次可成功。"""
    body = run_body(delay="0.4")
    rid = body["run_id"]
    pg.seed_run(rid)
    live = db_bridge()
    assert live.post_run(body).status_code == 201
    done = live.wait_status(rid, TERMINAL)
    assert done["status"] == "COMPLETED"
    key = make_lock_key(body["project"], done["execution_path"])
    assert _wait(lambda: not _advisory_holders(pg, key)), "終態：PG 鎖已放"
    checkpoint = live.client.get(f"/autoclaude/runs/{rid}/checkpoints").json()[0]
    request = {"checkpoint_id": checkpoint["checkpoint_id"]}

    with pytest.MonkeyPatch.context() as patch:        # 只在這個區塊內讓寫 checkpoint 失敗
        patch.setattr(runner_module, "write_engine_checkpoint", _disk_full)
        failed = live.post_on_fresh_connection(f"/autoclaude/runs/{rid}/restore", json=request)
    assert failed.status_code == 500, failed.text
    assert live.get_run(rid)["status"] == "COMPLETED", "失敗的 restore 不改變終態"
    assert _advisory_holders(pg, key) == [], "剛重取的 PG 鎖要在回 500 之前就放掉"
    assert live.app.state.runs.locks.holder(key) is None, "登記表也要乾淨"

    again = live.client.post(f"/autoclaude/runs/{rid}/restore", json=request)
    assert again.status_code == 202, again.text
    holders = _advisory_holders(pg, key)
    assert len(holders) == 1, f"這次 restore 重新取得 PG 鎖：恰好一條專用連線；實得 {holders}"
    final = live.wait_status(rid, {"COMPLETED"})
    assert final["completed_steps"] == 3
    assert _wait(lambda: not _advisory_holders(pg, key)), "再度終態：PG 鎖要放掉"
    assert _wait(lambda: not _backend_alive(pg, holders[0])), "再度終態：專用連線要關掉"


def test_a_failed_restore_of_a_paused_run_keeps_its_pg_lock(db_bridge, pg, run_body) -> None:
    """PAUSED run 的鎖本來就是它的（restore 沒有重取）：restore 失敗不得放掉，PAUSED 語意不變。"""
    body = run_body(delay="0.8")
    rid = body["run_id"]
    pg.seed_run(rid)
    live = db_bridge()
    assert live.post_run(body).status_code == 201
    assert live.client.post(f"/autoclaude/runs/{rid}:pause").status_code == 202
    paused = live.wait_status(rid, {"PAUSED"})
    key = make_lock_key(body["project"], paused["execution_path"])
    holders = _advisory_holders(pg, key)
    assert len(holders) == 1, f"PAUSED 期間持鎖（設計）：恰好一條專用連線；實得 {holders}"
    checkpoint = live.client.get(f"/autoclaude/runs/{rid}/checkpoints").json()[0]
    request = {"checkpoint_id": checkpoint["checkpoint_id"]}

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(runner_module, "write_engine_checkpoint", _disk_full)
        failed = live.post_on_fresh_connection(f"/autoclaude/runs/{rid}/restore", json=request)
    assert failed.status_code == 500, failed.text
    assert live.get_run(rid)["status"] == "PAUSED", "失敗的 restore 不改變 PAUSED"
    assert _advisory_holders(pg, key) == holders, "仍是同一條專用連線持著同一把 PG 鎖"
    assert live.app.state.runs.locks.holder(key) == rid
    clash = live.post_run(run_body(delay="0.1"))       # 同 project＋同 execution_path
    assert (clash.status_code, clash.json()["holder_run_id"]) == (409, rid), "依然擋得住別人"

    again = live.client.post(f"/autoclaude/runs/{rid}/restore", json=request)
    assert again.status_code == 202, again.text
    assert _advisory_holders(pg, key) == holders
    final = live.wait_status(rid, {"COMPLETED"})
    assert final["completed_steps"] == 3
    assert _wait(lambda: not _advisory_holders(pg, key)), "終態：PG 鎖要放掉"


def test_reconcile_mirrors_an_orphan_into_the_database(
        make_bridge, settings, pg, project_dir) -> None:
    from app.runstate import RunPaths, RunRecord, save_record

    run_id = str(uuid.uuid4())
    pg.seed_run(run_id)
    pg.exec("UPDATE {s}.execution_runs SET status = 'RUNNING', subprocess_pid = 999999 "
            "WHERE id = %s", uuid.UUID(run_id))
    paths = RunPaths(settings.engine_workspace / run_id)
    paths.run_dir.mkdir(parents=True)
    save_record(paths, RunRecord(
        run_id=run_id, project="mock-proj", execution_path=str(project_dir), status="RUNNING",
        pid=999999, pid_create_time=1.0, lock_key=make_lock_key("mock-proj", str(project_dir))))
    make_bridge(replace(settings, db_dsn=DSN, db_schema=pg.schema))
    row = _wait(lambda: (r := pg.run_row(run_id)) and r["status"] == "FAILED" and r)
    assert row["completed_at"] is not None
    assert row["subprocess_pid"] is None


def test_the_db_layer_refuses_to_write_columns_it_does_not_own(pg) -> None:
    db = BridgeDb(DSN, pg.schema)
    db.open()
    try:
        with pytest.raises(ValueError, match="不可寫入"):
            db.update_run(str(uuid.uuid4()), project_id=str(uuid.uuid4()))
        with pytest.raises(ValueError, match="不可寫入"):
            db.update_run(str(uuid.uuid4()), run_number=7)
    finally:
        db.close()


def test_the_schema_name_is_quoted_as_an_identifier_never_interpolated(pg) -> None:
    db = BridgeDb(DSN, 'x"; DROP TABLE public.checkpoints; --')   # 繞過 Settings 的最後防線
    db.open()
    try:
        assert db.update_run(str(uuid.uuid4()), status="RUNNING") is False
        assert pg.q("SELECT to_regclass('public.checkpoints')")[0][0] is not None
    finally:
        db.close()


def test_sql_composition_uses_identifier_quoting() -> None:
    q = sql.SQL("{}.{}").format(sql.Identifier("console"), sql.Identifier("execution_runs"))
    with psycopg.connect(DSN) as conn:
        assert q.as_string(conn) == '"console"."execution_runs"'
