"""生命週期 E2E：真引擎（`python -m autoclaude`）＋ mock claude，經真 HTTP／SSE。"""
from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path

import psutil

from tests.conftest import TERMINAL, mock_playbook, read_trace
from tests.timing import SPAWN_TIMEOUT, wait_until


def test_lifecycle_three_steps_complete_and_stream_is_finite(bridge, run_body, tmp_path) -> None:
    trace = tmp_path / "trace.jsonl"
    body = run_body(trace=trace)
    created = bridge.post_run(body)
    assert created.status_code == 201, created.text
    info = created.json()
    assert info["run_id"] == body["run_id"]
    assert info["status"] == "RUNNING"
    assert isinstance(info["pid"], int)
    assert info["bridge_instance"] == "test-bridge"
    workspace = Path(info["workspace"])

    events = bridge.sse(info["run_id"])                       # 串流會在終態自行結束
    steps = [e["data"] for e in events if e["event"] == "step"]
    completed = [s["step_id"] for s in steps if s["status"] == "COMPLETED"]
    assert completed == ["T01", "T02", "T03"]
    assert [s["step_number"] for s in steps if s["status"] == "STARTED"] == [1, 2, 3]
    statuses = [e["data"]["status"] for e in events if e["event"] == "status"]
    assert statuses[0] == "INITIALIZING"
    assert statuses[-1] == "COMPLETED"
    assert [e["id"] for e in events] == list(range(1, len(events) + 1)), "seq 必須連續單調"
    assert any(e["event"] == "token" for e in events)
    assert any(e["event"] == "log" and "子行程" not in e["data"]["line"] for e in events)

    final = bridge.get_run(info["run_id"])
    assert final["status"] == "COMPLETED"
    assert (final["exit_code"], final["pid"]) == (0, None)
    assert (final["completed_steps"], final["total_steps"]) == (3, 3)
    assert final["tokens_used"] == 3 * (1200 + 40)
    assert final["last_event_seq"] == events[-1]["id"]
    assert final["completed_at"] and final["started_at"]

    assert (workspace / "run.json").is_file()
    on_disk = [json.loads(x) for x in (workspace / "events.jsonl").read_text("utf-8").splitlines()]
    assert [e["seq"] for e in on_disk] == [e["id"] for e in events]
    run_json = json.loads((workspace / "run.json").read_text(encoding="utf-8"))
    assert run_json["status"] == "COMPLETED"
    assert "MOCK_CLAUDE_DELAY" in run_json["env_keys"]
    assert "0.3" not in json.dumps(run_json["env_keys"]), "env 的值不得落盤"
    assert len(_calls(trace)) == 3, read_trace(trace)


def _calls(trace: Path) -> list[dict]:
    return [t for t in read_trace(trace) if t["keywords"]]


def _count(trace: Path, keyword: str) -> int:
    """mock claude 被「帶著這個步驟關鍵字」呼叫的次數（獨立於 Bridge 自己的帳）。"""
    return sum(keyword in t["keywords"] for t in _calls(trace))


def _wait_trace(trace: Path, n: int, timeout: float = SPAWN_TIMEOUT) -> list[dict]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        calls = _calls(trace)
        if len(calls) >= n:
            return calls
        time.sleep(0.05)
    raise AssertionError(f"{timeout:g}s 內 mock claude 沒有被呼叫 {n} 次：{read_trace(trace)}")


def _statuses(events: list[dict]) -> list[str]:
    return [e["status"] for e in events if e["event"] == "status"]


def test_pause_stops_at_the_step_boundary_and_resume_continues_from_the_checkpoint(
        bridge, run_body, tmp_path) -> None:
    trace = tmp_path / "trace.jsonl"
    body = run_body(trace=trace, delay="0.8")
    info = bridge.post_run(body).json()
    rid, engine_pid = info["run_id"], info["pid"]

    resp = bridge.client.post(f"/autoclaude/runs/{rid}:pause")
    assert (resp.status_code, resp.json()) == (202, {"status": "PAUSING"})
    assert bridge.get_run(rid)["status"] == "PAUSING"      # 第一步至少 0.8s：PAUSING 一定先被看到

    paused = bridge.wait_status(rid, {"PAUSED"})
    assert paused["completed_steps"] == 1, "邊界＝第一步完成之後、第二步開始之前"
    assert paused["pid"] is None
    assert wait_until(lambda: not psutil.pid_exists(engine_pid)), "PAUSED 時引擎行程必須已退出"
    seen = _statuses(bridge.events(rid))
    assert seen.index("PAUSING") < seen.index("PAUSED")

    workspace = Path(info["workspace"])
    checkpoints = bridge.client.get(f"/autoclaude/runs/{rid}/checkpoints").json()
    assert [(c["name"], c["step_idx"], c["step_id"]) for c in checkpoints] == [
        ("after-T01", 1, "T02")]
    engine_cp = json.loads(
        (workspace / "engine" / "checkpoints" / "playbook.checkpoint.json").read_text("utf-8"))
    assert (engine_cp["step_idx"], engine_cp["completed_step_ids"]) == (1, ["T01"])
    assert len(engine_cp["checksum_sha256"]) == 64, "必須經引擎自己的 writer（帶 checksum）"

    resumed = bridge.client.post(f"/autoclaude/runs/{rid}:resume")
    assert (resumed.status_code, resumed.json()) == (202, {"status": "RUNNING"})
    final = bridge.wait_status(rid, TERMINAL)
    assert final["status"] == "COMPLETED"
    assert final["completed_steps"] == 3

    logs = [e["line"] for e in bridge.events(rid) if e["event"] == "log"]
    assert any("已載入檢查點: step_idx=1 [T02]" in line for line in logs), \
        "引擎自己的日誌證明它是從 checkpoint 接續、不是從頭"
    step_events = [(e["step_id"], e["status"]) for e in bridge.events(rid) if e["event"] == "step"]
    assert step_events.count(("T01", "COMPLETED")) == 1
    assert step_events.count(("T01", "STARTED")) == 1, "T01 不得被重做"
    assert _count(trace, "[INIT_DONE]") == 1
    assert _count(trace, "[PONG]") == 1
    assert _count(trace, "[TEST_CREATED]") >= 1


def test_stop_cancels_and_leaves_no_child_processes(bridge, run_body, tmp_path) -> None:
    trace = tmp_path / "trace.jsonl"
    info = bridge.post_run(run_body(trace=trace, delay="60")).json()
    rid, engine_pid = info["run_id"], info["pid"]
    child_pid = _wait_trace(trace, 1)[0]["pid"]
    assert psutil.pid_exists(child_pid)

    resp = bridge.client.post(f"/autoclaude/runs/{rid}:stop")
    assert (resp.status_code, resp.json()) == (202, {"status": "CANCELLING"})
    final = bridge.wait_status(rid, {"CANCELLED"})
    assert final["completed_at"] and final["pid"] is None
    assert wait_until(lambda: not psutil.pid_exists(engine_pid))
    assert wait_until(lambda: not psutil.pid_exists(child_pid)), \
        "引擎把 claude 放在自己的 session：只殺引擎會留下孤兒"
    seen = _statuses(bridge.events(rid))
    assert seen.index("CANCELLING") < seen.index("CANCELLED")


def test_a_child_that_ignores_sigterm_is_force_killed_after_the_grace_period(
        bridge, run_body, tmp_path) -> None:
    trace = tmp_path / "trace.jsonl"
    body = run_body(trace=trace, delay="60", env={"MOCK_CLAUDE_IGNORE_TERM": "1"})
    rid = bridge.post_run(body).json()["run_id"]
    child_pid = _wait_trace(trace, 1)[0]["pid"]
    time.sleep(0.5)                                   # 讓替身裝好 SIGTERM 忽略

    began = time.monotonic()
    bridge.client.post(f"/autoclaude/runs/{rid}:stop")
    bridge.wait_status(rid, {"CANCELLED"})
    elapsed = time.monotonic() - began
    assert wait_until(lambda: not psutil.pid_exists(child_pid))
    alerts = [e for e in bridge.events(rid) if e["event"] == "alert"]
    if sys.platform != "win32":
        # POSIX 行為＝SIGTERM 被忽略，必須等滿寬限期（測試設 3s）後升級 SIGKILL，並留下 alert。
        # Windows 行為＝terminate 即 TerminateProcess，沒有忽略這回事，所以不會有 FORCE_KILL。
        assert elapsed >= 2.5
        assert any(a["code"] == "FORCE_KILL" for a in alerts)


def test_restore_replays_from_a_chosen_checkpoint(bridge, run_body, tmp_path) -> None:
    trace = tmp_path / "trace.jsonl"
    info = bridge.post_run(run_body(trace=trace)).json()
    rid = info["run_id"]
    bridge.wait_status(rid, {"COMPLETED"})

    checkpoints = bridge.client.get(f"/autoclaude/runs/{rid}/checkpoints").json()
    assert [c["name"] for c in checkpoints] == ["after-T01", "after-T02", "after-T03"]
    assert [c["step_idx"] for c in checkpoints] == [1, 2, 3]
    assert all(c["is_automatic"] for c in checkpoints)
    target = checkpoints[0]

    resp = bridge.client.post(f"/autoclaude/runs/{rid}/restore",
                              json={"checkpoint_id": target["checkpoint_id"]})
    assert resp.status_code == 202, resp.text
    assert bridge.get_run(rid)["status"] in {"RUNNING", "COMPLETED"}
    final = bridge.wait_status(rid, {"COMPLETED"})
    assert final["completed_steps"] == 3

    assert _count(trace, "[INIT_DONE]") == 1, "T01 在還原點之前，不得重做"
    assert _count(trace, "[TEST_CREATED]") == 2
    assert _count(trace, "[PONG]") == 2
    alerts = [e for e in bridge.events(rid) if e["event"] == "alert"]
    assert any(a["code"] == "RESTORE" for a in alerts)
    assert len(bridge.client.get(f"/autoclaude/runs/{rid}/checkpoints").json()) > 3


def test_a_paused_run_can_be_restored_to_the_first_checkpoint_and_runs_to_completion(
        bridge, run_body, tmp_path) -> None:
    """restore 收 PAUSED（Console 的 GOAL_COMPLETED→RETRY 依賴它；AR-01 的檔案模式對照）。
    PAUSED 期間 run 仍持鎖：restore 前後同 project＋path 的新 run 都被擋，終態才放。"""
    trace = tmp_path / "trace.jsonl"
    rid = bridge.post_run(run_body(trace=trace, delay="0.8")).json()["run_id"]
    assert bridge.client.post(f"/autoclaude/runs/{rid}:pause").status_code == 202
    paused = bridge.wait_status(rid, {"PAUSED"})
    assert paused["completed_steps"] == 1, "邊界＝第一步完成之後、第二步開始之前"
    checkpoints = bridge.client.get(f"/autoclaude/runs/{rid}/checkpoints").json()
    assert [c["name"] for c in checkpoints] == ["after-T01"]
    first = checkpoints[0]

    rival = run_body(delay="0.1")
    clash = bridge.post_run(rival)
    assert (clash.status_code, clash.json()["holder_run_id"]) == (409, rid), "PAUSED 期間持鎖"
    resp = bridge.client.post(f"/autoclaude/runs/{rid}/restore",
                              json={"checkpoint_id": first["checkpoint_id"]})
    assert (resp.status_code, resp.json()) == (202, {"status": "RUNNING"})
    clash = bridge.post_run(rival)
    assert (clash.status_code, clash.json()["holder_run_id"]) == (409, rid), "restore 之後仍持鎖"

    final = bridge.wait_status(rid, {"COMPLETED"})
    assert (final["completed_steps"], final["exit_code"], final["pid"]) == (3, 0, None)
    seen = _statuses(bridge.events(rid))
    assert seen[seen.index("PAUSED"):] == ["PAUSED", "RUNNING", "COMPLETED"]
    assert any(e["code"] == "RESTORE" for e in bridge.events(rid) if e["event"] == "alert")
    assert _count(trace, "[INIT_DONE]") == 1, "T01 在還原點之前，不得重做"
    assert _count(trace, "[TEST_CREATED]") >= 1
    assert _count(trace, "[PONG]") == 1

    assert bridge.post_run(rival).status_code == 201, "終態已放鎖：同 project＋path 可再開"
    bridge.wait_status(rival["run_id"], TERMINAL)


def test_second_run_on_the_same_project_and_path_is_409_until_the_first_ends(
        bridge, run_body) -> None:
    first = run_body(delay="1.0")
    rid1 = bridge.post_run(first).json()["run_id"]
    second = run_body(delay="0.2")
    clash = bridge.post_run(second)
    assert clash.status_code == 409
    assert clash.json() == {"code": 409, "reason": "advisory_lock_held", "holder_run_id": rid1}
    assert bridge.client.get(f"/autoclaude/runs/{second['run_id']}").status_code == 404

    bridge.wait_status(rid1, TERMINAL)
    again = bridge.post_run(second)
    assert again.status_code == 201, again.text
    assert bridge.wait_status(second["run_id"], TERMINAL)["status"] == "COMPLETED"


def test_a_different_project_on_the_same_path_does_not_collide(bridge, run_body) -> None:
    one = run_body(delay="0.6", project="proj-a")
    two = run_body(delay="0.2", project="proj-b")
    assert bridge.post_run(one).status_code == 201
    assert bridge.post_run(two).status_code == 201
    for body in (one, two):
        assert bridge.wait_status(body["run_id"], TERMINAL)["status"] == "COMPLETED"


def test_a_failing_step_retries_then_escalates_and_the_run_fails(bridge, run_body) -> None:
    playbook = mock_playbook()
    playbook["tasks"][1]["prompt"] = "請建立測試案例 FORCE_FAIL，完成後輸出 [TEST_CREATED]"
    body = run_body(playbook=playbook, delay="0.2", env={"MOCK_CLAUDE_FAIL_REGEX": "FORCE_FAIL"})
    rid = bridge.post_run(body).json()["run_id"]
    final = bridge.wait_status(rid, TERMINAL)
    assert final["status"] == "FAILED"
    assert final["exit_code"] == 1
    assert final["completed_steps"] == 1
    assert "ESCALATION" in final["reason"]

    steps = [(e["step_id"], e["status"], e["attempt"]) for e in bridge.events(rid)
             if e["event"] == "step"]
    assert ("T01", "COMPLETED", 1) in steps
    assert ("T02", "STARTED", 1) in steps
    assert ("T02", "RETRYING", 2) in steps
    assert ("T02", "FAILED", 2) in steps
    assert [e["code"] for e in bridge.events(rid) if e["event"] == "alert"] == ["ESCALATION"]
    # 失敗後鎖必須釋放：同 project＋path 可再開一個 run。
    assert bridge.post_run(run_body(delay="0.1")).status_code == 201


def test_invalid_transitions_and_unknown_runs(bridge, run_body) -> None:
    body = run_body(delay="0.2")
    rid = bridge.post_run(body).json()["run_id"]
    resumed = bridge.client.post(f"/autoclaude/runs/{rid}:resume")
    assert resumed.status_code == 409
    assert resumed.json()["reason"] == "invalid_state"
    bridge.wait_status(rid, {"COMPLETED"})
    for action in ("pause", "stop", "resume"):
        resp = bridge.client.post(f"/autoclaude/runs/{rid}:{action}")
        assert resp.status_code == 409, action
        assert resp.json()["status"] == "COMPLETED"
    unknown = {"checkpoint_id": str(uuid.uuid4())}
    bad = bridge.client.post(f"/autoclaude/runs/{rid}/restore", json=unknown)
    assert (bad.status_code, bad.json()["reason"]) == (404, "checkpoint_not_found")

    ghost = str(uuid.uuid4())
    assert bridge.client.get(f"/autoclaude/runs/{ghost}").status_code == 404
    assert bridge.client.get(f"/autoclaude/runs/{ghost}/stream").status_code == 404
    assert bridge.client.get(f"/autoclaude/runs/{ghost}/events").status_code == 404
    assert bridge.client.get(f"/autoclaude/runs/{ghost}/checkpoints").status_code == 404
    for action in ("pause", "resume", "stop"):
        assert bridge.client.post(f"/autoclaude/runs/{ghost}:{action}").status_code == 404
    assert bridge.client.get(f"/autoclaude/runs/{ghost}").json()["reason"] == "run_not_found"


def test_engine_state_stays_out_of_the_execution_path(bridge, run_body, project_dir) -> None:
    rid = bridge.post_run(run_body(delay="0.1")).json()["run_id"]
    bridge.wait_status(rid, TERMINAL)
    assert list(project_dir.iterdir()) == [], "引擎的 checkpoints／logs 不得寫進使用者的專案目錄"


def test_the_run_workspace_holds_only_non_secret_state(bridge, run_body) -> None:
    body = run_body(delay="0.1", env={"MINIMAX_API_KEY": "sk-super-secret"})
    info = bridge.post_run(body).json()
    bridge.wait_status(info["run_id"], TERMINAL)
    leaked = [p for p in Path(info["workspace"]).rglob("*")
              if p.is_file() and "sk-super-secret" in p.read_text("utf-8", errors="replace")]
    assert leaked == [], f"機密不得落盤：{leaked}"
