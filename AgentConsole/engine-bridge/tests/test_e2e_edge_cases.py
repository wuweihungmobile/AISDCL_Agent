"""邊界情境：最後一步時 pause、零延遲競態、併發建立、日誌格式失效的退路、單行處理容錯。"""
from __future__ import annotations

import re
import threading
import uuid
from pathlib import Path

import pytest

import app.logparse as logparse
from app.runner import RunHandle
from tests.conftest import TERMINAL, mock_playbook


def _alerts(bridge, rid) -> list[str]:
    return [e["code"] for e in bridge.events(rid) if e["event"] == "alert"]


def test_pausing_during_the_last_step_ends_as_completed_not_paused(bridge, run_body) -> None:
    one_step = mock_playbook()
    one_step["tasks"] = one_step["tasks"][:1]
    rid = bridge.post_run(run_body(playbook=one_step, delay="0.8")).json()["run_id"]
    assert bridge.client.post(f"/autoclaude/runs/{rid}:pause").status_code == 202
    final = bridge.wait_status(rid, TERMINAL)
    assert final["status"] == "COMPLETED", "沒有下一個邊界可停：pause 來不及生效，run 照常完成"
    assert final["completed_steps"] == 1
    statuses = [e["status"] for e in bridge.events(rid) if e["event"] == "status"]
    assert statuses.index("PAUSING") < statuses.index("COMPLETED")


def test_zero_delay_steps_race_the_pause_but_the_outcome_is_always_consistent(
        bridge, run_body, tmp_path) -> None:
    from tests.test_e2e_lifecycle import _count

    trace = tmp_path / "trace.jsonl"
    rid = bridge.post_run(run_body(trace=trace, delay="0")).json()["run_id"]
    bridge.client.post(f"/autoclaude/runs/{rid}:pause")
    state = bridge.wait_status(rid, {"PAUSED", "COMPLETED"})
    if state["status"] == "PAUSED":
        assert 1 <= state["completed_steps"] < 3
        bridge.client.post(f"/autoclaude/runs/{rid}:resume")
        state = bridge.wait_status(rid, TERMINAL)
    assert state["status"] == "COMPLETED"
    assert state["completed_steps"] == 3
    steps = [(e["step_id"], e["status"]) for e in bridge.events(rid) if e["event"] == "step"]
    for step_id in ("T01", "T02", "T03"):
        assert steps.count((step_id, "COMPLETED")) == 1, steps
    assert _count(trace, "[INIT_DONE]") == 1


def test_concurrent_creates_with_the_same_run_id_yield_exactly_one_run(
        bridge, run_body) -> None:
    body = run_body(delay="0.5")
    results: list[int] = []

    def post() -> None:
        results.append(bridge.post_run(body).status_code)

    threads = [threading.Thread(target=post) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results) == [201, 409, 409, 409, 409, 409]
    assert bridge.wait_status(body["run_id"], TERMINAL)["status"] == "COMPLETED"


def test_losing_creators_never_release_the_winners_lock(bridge, run_body) -> None:
    winner = run_body(delay="1.5")
    assert bridge.post_run(winner).status_code == 201
    assert bridge.post_run(winner).status_code == 409                    # 同 run_id：run_exists
    rival = run_body(delay="0.1")                                         # 不同 run_id、同鎖鍵
    clash = bridge.post_run(rival)
    assert clash.status_code == 409
    assert clash.json()["reason"] == "advisory_lock_held"


def test_when_the_engine_log_format_stops_matching_the_run_degrades_to_log_events_only(
        bridge, run_body, monkeypatch) -> None:
    monkeypatch.setattr(logparse, "_START_RE", re.compile(r"(?!)"))     # 永遠不匹配
    rid = bridge.post_run(run_body(delay="0.2")).json()["run_id"]
    final = bridge.wait_status(rid, TERMINAL)
    assert final["status"] == "COMPLETED"
    assert final["completed_steps"] == 3, "計數以引擎結束結果為準，不是 0"
    events = bridge.events(rid)
    assert not [e for e in events if e["event"] == "step"], "解析不到就不發步驟事件"
    assert [e for e in events if e["event"] == "log"], "但 log 事件照發"
    assert "STEP_TRACKING_GAP" in _alerts(bridge, rid), "必須大聲說明步驟追蹤有缺口"


def test_a_bug_in_per_line_handling_does_not_kill_the_run(bridge, run_body, monkeypatch) -> None:
    def boom(self, parsed) -> None:
        raise RuntimeError("synthetic bug")

    monkeypatch.setattr(RunHandle, "_on_token_peak", boom)
    rid = bridge.post_run(run_body(delay="0.2")).json()["run_id"]
    final = bridge.wait_status(rid, TERMINAL)
    assert final["status"] == "COMPLETED", "事件處理的 bug 不得連坐終止引擎"
    assert final["completed_steps"] == 3
    assert "BRIDGE_INTERNAL" in _alerts(bridge, rid)


def test_an_invalid_run_id_in_the_path_is_just_not_found(bridge) -> None:
    for bad in ("not-a-uuid", "../../etc", uuid.uuid4().hex[:8]):
        assert bridge.client.get(f"/autoclaude/runs/{bad}").status_code == 404


@pytest.mark.parametrize("fresh", [True, False])
def test_the_fresh_flag_is_accepted_for_a_brand_new_run(bridge, run_body, fresh) -> None:
    body = run_body(delay="0.1")
    body["fresh"] = fresh
    rid = bridge.post_run(body).json()["run_id"]
    assert bridge.wait_status(rid, TERMINAL)["status"] == "COMPLETED"
    first_log = [e["line"] for e in bridge.events(rid) if e["event"] == "log"
                 and "Playbook 模式啟動" in e["line"]][0]
    assert f"fresh={fresh}" in first_log, "--fresh 旗標必須真的傳給引擎"


def test_huge_log_lines_are_truncated_in_events_but_still_parsed(bridge, run_body) -> None:
    from app.runner import MAX_LOG_LINE_CHARS

    playbook = mock_playbook()
    playbook["tasks"] = playbook["tasks"][:2]
    playbook["tasks"][0]["prompt"] = "請完成第一步 [INIT_DONE] " + "長" * 50_000
    rid = bridge.post_run(run_body(playbook=playbook, delay="0.1")).json()["run_id"]
    final = bridge.wait_status(rid, TERMINAL)
    assert final["status"] == "COMPLETED"
    assert final["completed_steps"] == 2, "步驟追蹤用的是完整原文，不受截斷影響"
    lines = [e["line"] for e in bridge.events(rid) if e["event"] == "log"]
    assert max(len(x) for x in lines) <= MAX_LOG_LINE_CHARS + 40
    assert any("已截斷，原長" in x for x in lines)


def test_resume_revalidates_the_execution_path(bridge, run_body, tmp_path, project_dir) -> None:
    import shutil

    outside = tmp_path / "outside"
    outside.mkdir()
    rid = bridge.post_run(run_body(delay="0.8")).json()["run_id"]
    bridge.client.post(f"/autoclaude/runs/{rid}:pause")
    bridge.wait_status(rid, {"PAUSED"})
    shutil.rmtree(project_dir)
    try:
        project_dir.symlink_to(outside, target_is_directory=True)     # 暫停期間被換成逃逸的 symlink
    except (OSError, NotImplementedError):
        pytest.skip("此環境無法建立 symlink（Windows 需開發人員模式或系統管理員）")
    resp = bridge.client.post(f"/autoclaude/runs/{rid}:resume")
    assert resp.status_code == 422, resp.text
    assert resp.json()["violations"][0]["rule"] == "outside_allowed_roots"
    assert bridge.get_run(rid)["status"] == "PAUSED", "被拒絕的續跑不得改動狀態"
    assert not list(outside.iterdir()), "引擎不得在白名單外落任何檔案"


def test_a_stop_that_arrives_after_the_engine_already_finished_does_not_rewrite_history(
        bridge, run_body, monkeypatch) -> None:
    """終止訊號沒生效（模擬：begin_terminate 什麼都沒殺）、引擎自然成功收尾 ⇒ 事實是 COMPLETED。"""
    import app.runner as runner_module

    monkeypatch.setattr(runner_module.procutil, "begin_terminate", lambda pid: [])
    rid = bridge.post_run(run_body(delay="0.8")).json()["run_id"]
    assert bridge.client.post(f"/autoclaude/runs/{rid}:stop").status_code == 202
    final = bridge.wait_status(rid, TERMINAL)
    assert final["status"] == "COMPLETED"
    assert final["exit_code"] == 0
    statuses = [e["status"] for e in bridge.events(rid) if e["event"] == "status"]
    assert statuses.index("CANCELLING") < statuses.index("COMPLETED")


def test_stop_during_pausing_wins_over_the_pending_pause(bridge, run_body) -> None:
    rid = bridge.post_run(run_body(delay="1.0")).json()["run_id"]
    bridge.client.post(f"/autoclaude/runs/{rid}:pause")
    assert bridge.get_run(rid)["status"] == "PAUSING"
    resp = bridge.client.post(f"/autoclaude/runs/{rid}:stop")
    assert (resp.status_code, resp.json()) == (202, {"status": "CANCELLING"})
    assert bridge.wait_status(rid, TERMINAL)["status"] == "CANCELLED"


def test_pause_and_stop_are_idempotent(bridge, run_body) -> None:
    rid = bridge.post_run(run_body(delay="1.0")).json()["run_id"]
    first = bridge.client.post(f"/autoclaude/runs/{rid}:pause")
    again = bridge.client.post(f"/autoclaude/runs/{rid}:pause")
    assert first.json() == again.json() == {"status": "PAUSING"}
    bridge.client.post(f"/autoclaude/runs/{rid}:stop")
    assert bridge.client.post(f"/autoclaude/runs/{rid}:stop").json() == {"status": "CANCELLING"}
    bridge.wait_status(rid, TERMINAL)


def test_run_ids_are_found_regardless_of_uuid_spelling(bridge, run_body) -> None:
    rid = bridge.post_run(run_body(delay="0.1")).json()["run_id"]
    for spelling in (rid.upper(), rid.replace("-", "")):
        resp = bridge.client.get(f"/autoclaude/runs/{spelling}")
        assert resp.status_code == 200, spelling
        assert resp.json()["run_id"] == rid
    bridge.wait_status(rid, TERMINAL)


def test_tricky_prompts_survive_the_yaml_roundtrip_to_the_engine_and_the_claude_argv(
        bridge, run_body, tmp_path) -> None:
    from tests.conftest import read_trace

    tricky = ("第一行：含冒號與 'single' 與 \"double\" 引號\n- 看起來像 YAML 清單的一行\n"
              "# 看起來像註解\n\t縮排與 Tab、emoji 🚀、反斜線 C:\\path\\to、花括號 {x: 1}、"
              "百分號 %s %d\n結尾 [ZETA_DONE]")
    playbook = mock_playbook()
    playbook["tasks"] = [{"step_id": "Z01", "name": "怪字元", "prompt": tricky,
                          "expected_output_regex": "\\[ZETA_DONE\\]"}]
    trace = tmp_path / "trace.jsonl"
    rid = bridge.post_run(run_body(playbook=playbook, trace=trace, delay="0.1")).json()["run_id"]
    assert bridge.wait_status(rid, TERMINAL)["status"] == "COMPLETED"
    calls = [t for t in read_trace(trace) if t["keywords"]]
    assert len(calls) == 1
    assert calls[0]["prompt_tail"] == tricky[-120:], "prompt 尾端必須逐字原樣抵達 claude 的 argv"
    steps = [(e["step_id"], e["status"]) for e in bridge.events(rid) if e["event"] == "step"]
    assert ("Z01", "COMPLETED") in steps


def test_bridge_managed_overrides_are_ignored_with_an_alert_and_never_honored(
        bridge, run_body, tmp_path) -> None:
    """ConfigMaterializer 會帶 storage.*（autoclaude.dalBackend→both）：不得 422，也不得被採用。"""
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    overrides = {"checkpoint_dir": str(elsewhere / "ck"), "log_dir": str(elsewhere / "lg"),
                 "storage": {"mode": "both", "dual_read_resolution": "db_wins"}}
    body = run_body(delay="0.1", overrides=overrides,
                    env={"AUTOCLAUDE_DB_DSN": "postgresql://u:<YOUR_PASSWORD>@db.invalid/x"})
    info = bridge.post_run(body).json()
    rid = info["run_id"]
    assert bridge.wait_status(rid, TERMINAL)["status"] == "COMPLETED"
    notices = [e for e in bridge.events(rid) if e["event"] == "alert"
               and e["code"] == "CONFIG_OVERRIDE_IGNORED"]
    assert len(notices) == 1
    for key in ("checkpoint_dir", "log_dir", "storage"):
        assert key in notices[0]["message"]
    assert list(elsewhere.iterdir()) == [], "被忽略的路徑不得有任何檔案落地"
    config = (Path(info["workspace"]) / "config.yaml").read_text(encoding="utf-8")
    assert "mode: yaml_only" in config
    assert "db_wins" not in config
    assert str(Path(info["workspace"]) / "engine" / "checkpoints") in config
