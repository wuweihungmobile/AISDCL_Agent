"""Bridge 設計所依賴的「引擎事實」鎖（2026-10-14 對 AutoClaude 實測）。

這些測試守的不是 Bridge 的行為，而是 Bridge 的**前提**：引擎哪天改了，這裡先紅，
提醒維護者回頭檢視 app/logparse.py、app/checkpoints.py 的設計（可能反而能簡化）。
"""
from __future__ import annotations

import threading
import time

from tests.conftest import TERMINAL


def test_the_engine_does_not_write_step_level_checkpoints(bridge, run_body) -> None:
    """前提一：引擎只在 HALT／中斷／演化時才寫 checkpoint，步驟結束時不寫（所以 Bridge 自己記）。"""
    rid = bridge.post_run(run_body(delay="0.6")).json()["run_id"]
    checkpoint_dir = bridge.settings.engine_workspace / rid / "engine" / "checkpoints"
    seen: list[str] = []
    stop = threading.Event()

    def watch() -> None:
        while not stop.is_set():
            seen.extend(p.name for p in checkpoint_dir.glob("*.checkpoint.json"))
            time.sleep(0.03)

    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    try:
        assert bridge.wait_status(rid, TERMINAL)["status"] == "COMPLETED"
    finally:
        stop.set()
        watcher.join(timeout=5)
    assert seen == [], f"引擎開始自己寫步驟級 checkpoint 了：{seen}——重新評估 checkpoint 設計"
    assert list(checkpoint_dir.glob("*.checkpoint.json")) == [], "成功收尾時引擎也不留 checkpoint"


def test_claude_command_is_a_single_executable_not_a_shell_line(bridge, run_body) -> None:
    """前提二：`claude.command` 不做 shlex 切分，含空白的指令列會被當成檔名而啟動失敗。"""
    command = "python -u /nonexistent/x.py"
    body = run_body(delay="0.1", overrides={"claude": {"command": command}})
    rid = bridge.post_run(body).json()["run_id"]
    final = bridge.wait_status(rid, TERMINAL)
    assert final["status"] == "FAILED"
    assert final["exit_code"] == 1
    assert "FileNotFoundError" in final["reason"], final["reason"]
    steps = [e for e in bridge.events(rid) if e["event"] == "step"]
    assert steps == [], "spawn 本身就失敗＝引擎連『步驟啟動』都沒印，所以沒有任何步驟事件"


def test_the_engine_prints_the_markers_the_bridge_parses(bridge, run_body) -> None:
    """前提三：引擎 stdout 帶有步驟啟動行與 token 峰值行（logparse 的輸入契約）。"""
    rid = bridge.post_run(run_body(delay="0.1")).json()["run_id"]
    bridge.wait_status(rid, TERMINAL)
    lines = [e["line"] for e in bridge.events(rid) if e["event"] == "log"]
    assert sum("模式啟動：" in x for x in lines) == 3
    assert sum("=== STEP_TOKEN_PEAK | step=" in x for x in lines) == 3
    assert sum("Playbook 結束 | KernelResult(success=True" in x for x in lines) == 1
