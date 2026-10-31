"""孤兒回收與重啟存活（PRD §0.2.2）：重啟後 RUNNING 但無存活 PID 的 run → FAILED(orphaned)。"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import psutil

from app.locks import make_lock_key
from app.runstate import RunPaths, RunRecord, save_record
from tests.conftest import TERMINAL, mock_playbook, read_trace
from tests.timing import SPAWN_TIMEOUT, wait_until

SLEEPER = [sys.executable, "-c", "import time; time.sleep(120)"]


def _seed(settings, project_dir: Path, *, status: str, pid: int | None,
          create_time: float | None, lock: bool = False) -> str:
    """手工寫一個 run.json（模擬 Bridge 崩潰前留下的狀態）。"""
    run_id = str(uuid.uuid4())
    paths = RunPaths(settings.engine_workspace / run_id)
    paths.run_dir.mkdir(parents=True)
    rec = RunRecord(
        run_id=run_id, project="mock-proj", execution_path=str(project_dir), status=status,
        pid=pid, last_pid=pid, pid_create_time=create_time, bridge_instance="old-bridge",
        created_at=datetime.now(UTC).isoformat(), total_steps=3,
        lock_key=make_lock_key("mock-proj", str(project_dir)) if lock else None)
    save_record(paths, rec)
    return run_id


def _dead_pid() -> int:
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    return proc.pid


def test_a_running_run_with_a_dead_pid_becomes_failed_orphaned(
        make_bridge, settings, project_dir) -> None:
    rid = _seed(settings, project_dir, status="RUNNING", pid=_dead_pid(),
                create_time=time.time() - 1000)
    bridge = make_bridge()
    run = bridge.get_run(rid)
    assert run["status"] == "FAILED"
    assert "orphaned" in run["reason"]
    assert run["pid"] is None
    assert run["completed_at"]
    statuses = [e for e in bridge.events(rid) if e["event"] == "status"]
    assert statuses[-1]["status"] == "FAILED"
    saved = json.loads((settings.engine_workspace / rid / "run.json").read_text(encoding="utf-8"))
    assert saved["status"] == "FAILED"
    audit = (settings.engine_workspace / "_audit.jsonl").read_text(encoding="utf-8")
    assert "run_orphaned" in audit


def test_every_active_status_is_reaped_and_cancelling_ends_as_cancelled(
        make_bridge, settings, project_dir) -> None:
    ids = {s: _seed(settings, project_dir, status=s, pid=_dead_pid(), create_time=1.0)
           for s in ("INITIALIZING", "RUNNING", "PAUSING", "CANCELLING")}
    done = _seed(settings, project_dir, status="COMPLETED", pid=None, create_time=None)
    bridge = make_bridge()
    got = {s: bridge.get_run(rid)["status"] for s, rid in ids.items()}
    assert got == {"INITIALIZING": "FAILED", "RUNNING": "FAILED", "PAUSING": "FAILED",
                   "CANCELLING": "CANCELLED"}
    assert bridge.get_run(done)["status"] == "COMPLETED", "終態不得被動"


def test_a_still_living_engine_is_terminated_before_the_run_is_marked(
        make_bridge, settings, project_dir) -> None:
    stray = subprocess.Popen(SLEEPER)
    try:
        created = psutil.Process(stray.pid).create_time()
        rid = _seed(settings, project_dir, status="RUNNING", pid=stray.pid, create_time=created)
        bridge = make_bridge()
        assert bridge.get_run(rid)["status"] == "FAILED"
        stray.wait(timeout=10)                       # 已被 Bridge 終止
        assert not psutil.pid_exists(stray.pid) or stray.poll() is not None
    finally:
        if stray.poll() is None:
            stray.kill()
            stray.wait()


def test_a_reused_pid_is_never_killed(make_bridge, settings, project_dir) -> None:
    """pid 被作業系統重用給別的行程時，create_time 對不上——絕不能誤殺陌生行程。"""
    stranger = subprocess.Popen(SLEEPER)
    try:
        rid = _seed(settings, project_dir, status="RUNNING", pid=stranger.pid,
                    create_time=time.time() - 5000)
        bridge = make_bridge()
        assert bridge.get_run(rid)["status"] == "FAILED"
        assert stranger.poll() is None, "身分對不上的行程不得被終止"
    finally:
        stranger.kill()
        stranger.wait()


def test_a_paused_run_keeps_its_lock_across_a_restart(
        make_bridge, settings, project_dir, run_body) -> None:
    rid = _seed(settings, project_dir, status="PAUSED", pid=None, create_time=None, lock=True)
    bridge = make_bridge()
    assert bridge.get_run(rid)["status"] == "PAUSED"
    clash = bridge.post_run(run_body(delay="0.1"))
    assert clash.status_code == 409
    assert clash.json()["holder_run_id"] == rid
    assert bridge.client.post(f"/autoclaude/runs/{rid}:stop").status_code == 202
    assert bridge.get_run(rid)["status"] == "CANCELLED"
    assert bridge.post_run(run_body(delay="0.1")).status_code == 201


def test_a_paused_run_can_be_resumed_by_a_new_bridge_process(
        make_bridge, run_body, tmp_path) -> None:
    trace = tmp_path / "trace.jsonl"
    first = make_bridge()
    body = run_body(trace=trace, delay="0.8", env={"MINIMAX_API_KEY": "sk-lost-on-restart"})
    info = first.post_run(body).json()
    rid = info["run_id"]
    first.client.post(f"/autoclaude/runs/{rid}:pause")
    first.wait_status(rid, {"PAUSED"})
    first.stop()                                      # Bridge「重啟」：記憶體全部消失

    second = make_bridge()
    assert second.get_run(rid)["status"] == "PAUSED"
    assert len(second.client.get(f"/autoclaude/runs/{rid}/checkpoints").json()) == 1
    resp = second.client.post(f"/autoclaude/runs/{rid}:resume")
    assert resp.status_code == 202, resp.text
    final = second.wait_status(rid, TERMINAL)
    assert final["status"] == "COMPLETED"
    assert final["completed_steps"] == 3
    codes = [e["code"] for e in second.events(rid) if e["event"] == "alert"]
    assert "ENV_LOST" in codes, "請求層 env（機密）不落盤，重啟後遺失必須大聲說"
    seqs = [e["seq"] for e in second.events(rid)]
    assert seqs == list(range(1, len(seqs) + 1)), "重啟後 seq 必須延續、不重來"
    assert sum("[INIT_DONE]" in t["keywords"] for t in read_trace(trace)) == 1


def test_shutting_the_bridge_down_terminates_running_engines(
        make_bridge, run_body, tmp_path) -> None:
    trace = tmp_path / "trace.jsonl"
    bridge = make_bridge()
    body = run_body(trace=trace, delay="60", playbook=mock_playbook())
    info = bridge.post_run(body).json()
    deadline = time.monotonic() + SPAWN_TIMEOUT
    while not [t for t in read_trace(trace) if t["keywords"]]:
        assert time.monotonic() < deadline
        time.sleep(0.05)
    child_pid = [t for t in read_trace(trace) if t["keywords"]][0]["pid"]
    bridge.stop()
    assert wait_until(lambda: not psutil.pid_exists(info["pid"]))
    assert wait_until(lambda: not psutil.pid_exists(child_pid))
    saved = json.loads((Path(info["workspace"]) / "run.json").read_text(encoding="utf-8"))
    assert saved["status"] == "FAILED"
    assert "Bridge 關閉" in saved["reason"]
