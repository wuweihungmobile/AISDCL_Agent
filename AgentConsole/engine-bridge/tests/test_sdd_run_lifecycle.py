"""BR-31（生命週期面）：終態同步、回收點、`resume`／`restore` 的重驗與權杖、孤兒、RunRecord 與子行
程環境。

真引擎＋mock claude＋假 SDD 樹。ADR-XPLAT-016 §10.1（終態對映）、§10.3（回收點）、D-115-15／
D-115-18。
🔴 `delegate-exit --decision done` 的語意是「委派交還控制權、未升級」，不是「成功」：完成與取消都
是 `done`，只有引擎升級型失敗是 `failed`（進阻塞態 ESCALATION，恢復留在 SDD session）；基礎設施故
障一律不動FSM，留給下一個批次的回收點。
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

import pytest

from app import procutil, sdd_run
from app.runner import RunHandle, RunManager
from app.runstate import RunPaths, RunRecord, load_record, save_record
from app.sdd_sync import RunFacts
from tests.conftest import TERMINAL
from tests.fake_sdd import read_calls
from tests.sdd_run_support import (
    FSM_REL,
    TCS_NAME,
    TCS_TEXT,
    TOKEN,
    argv_of,
    audit_entries,
    contracts_dir,
    digest_of,
    flag,
    fsm_state,
    post,
    sdd_block,
    sdd_body,
    seed_frozen,
    trace_calls,
    verbs,
    wait_fsm,
    wait_sync,
    workspace_has,
)


def _wait_trace(trace: Path, n: int = 1, timeout: float = 40.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if len(trace_calls(trace)) >= n:
            return
        time.sleep(0.05)
    raise AssertionError(f"{timeout:g}s 內 mock claude 沒有被呼叫 {n} 次")


def _record(live, rid: str) -> dict[str, Any]:
    """終態後的 run.json——等到 `sdd.sync` 落盤才回（它在 FSM 回寫之後才 persist；見 wait_sync）。"""
    return wait_sync(live.settings.engine_workspace / rid)


def _start_long(live, run_body, proj: Path, tmp_path: Path, **kw: Any) -> tuple[str, Path]:
    """起一個跑得很久的 SDD 批次（mock claude 每次 30 秒），等到引擎真的在跑。"""
    trace = tmp_path / f"trace-{uuid.uuid4().hex[:6]}.jsonl"
    body = sdd_body(run_body, proj, delay="30", env={"MOCK_CLAUDE_TRACE": str(trace)}, **kw)
    resp = post(live, body)
    assert resp.status_code == 201, resp.text
    _wait_trace(trace)
    return resp.json()["run_id"], trace


# ── 終態對映（§10.1）：完成與取消＝done；引擎升級＝failed ─────────────────────────────────────
def test_cancelling_a_running_batch_hands_control_back_with_done_not_failed(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body, tmp_path: Path) -> None:
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    rid, _ = _start_long(sdd_live, run_body, sdd_proj, tmp_path)
    assert fsm_state(sdd_proj)["current_state"] == "AUTOCLAUDE_DELEGATED"
    assert sdd_live.client.post(f"/autoclaude/runs/{rid}:stop").status_code == 202
    assert sdd_live.wait_status(rid, {"CANCELLED"})["status"] == "CANCELLED"
    final = wait_fsm(sdd_proj, "IMPLEMENTATION")
    assert final["escalation_history"] == [], "取消不是阻塞態"
    leave = argv_of(sdd_fake, "delegate-exit")
    assert (flag(leave, "--decision"), flag(leave, "--reason")) == (
        "done", f"console-run run={rid} CANCELLED")
    assert verbs(sdd_fake) == ["delegate-enter", "delegate-exit"]
    assert _record(sdd_live, rid)["sdd"]["sync"]["exit"] == "done"


def test_an_engine_escalation_is_the_only_failure_that_blocks_the_fsm(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    seed_frozen(sdd_proj, "SPEC_FROZEN")
    body = sdd_body(run_body, sdd_proj, fail_step=2, delay="0.2")
    rid = post(sdd_live, body).json()["run_id"]
    final = sdd_live.wait_status(rid, TERMINAL)
    assert final["status"] == "FAILED" and final["reason"].startswith("引擎升級（ESCALATION）")
    state = wait_fsm(sdd_proj, "ESCALATION")
    leave = argv_of(sdd_fake, "delegate-exit")
    assert flag(leave, "--decision") == "failed"
    assert flag(leave, "--reason").startswith(
        f"console-run run={rid} ENGINE-ESCALATION step=sdd-greenfield-at-001-1-2: ")
    assert "\n" not in flag(leave, "--reason")
    assert state["escalation_provenance"]["source"] == "autoclaude_delegated_failed"
    assert state["escalation_history"][-1]["resolved_at"] is None
    assert state["autoclaude_delegated_tracking"]["playbook_ref"] == f"run:{rid}", \
        "哪個 run 失敗的，Console 讀 tracking.playbook_ref"
    assert _record(sdd_live, rid)["sdd"]["sync"]["exit"] == "failed"

    # Console 看得到：ESCALATION 的阻塞態、provenance、可複製的恢復指令（恢復只有人能做、留在 SDD
    # session）
    view = sdd_live.client.get("/sdd/fsm/alpha", params={"root": str(sdd_proj)}).json()
    assert view["current_state"] == "ESCALATION"
    assert view["phase"] == {"name": "BLOCKED", "order": 0, "blocking": True,
                             "observation": False}, "阻塞態：BLOCKED／0／blocking（契約 §3.1.5）"
    assert view["escalation_provenance"]["source"] == "autoclaude_delegated_failed"
    assert view["recovery"]["target"] == "IMPLEMENTATION"
    # 下一個批次被擋（Bridge 沒有恢復動詞，也不碰 ESCALATION）；零副作用
    again = sdd_body(run_body, sdd_proj)
    calls_before = len(read_calls(sdd_fake))
    resp = post(sdd_live, again)
    assert (resp.status_code, resp.json()["reason"], resp.json()["current_state"]) == (
        409, "fsm_state_conflict", "ESCALATION")
    assert len(read_calls(sdd_fake)) == calls_before
    assert not workspace_has(sdd_live, again["run_id"])
    # 人在 SDD session 恢復後（這裡以 seed 扮演），下一個批次可直接啟動
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    assert post(sdd_live, sdd_body(run_body, sdd_proj, delay="0.1")).status_code == 201


# ── 暫停、續跑：委派在暫停期間仍開著；續跑不重新 enter ─────────────────────────────────────────
def test_pause_keeps_the_delegation_open_and_resume_continues_it_without_a_new_enter(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    body = sdd_body(run_body, sdd_proj, delay="0.8", count=3)
    rid = post(sdd_live, body).json()["run_id"]
    assert sdd_live.client.post(f"/autoclaude/runs/{rid}:pause").status_code == 202
    sdd_live.wait_status(rid, {"PAUSED"})
    assert verbs(sdd_fake) == ["delegate-enter"], "PAUSED 非終態：不動 FSM"
    assert fsm_state(sdd_proj)["current_state"] == "AUTOCLAUDE_DELEGATED"
    resumed = sdd_live.client.post(f"/autoclaude/runs/{rid}:resume",
                                   headers={"X-Bridge-Token": TOKEN})
    assert resumed.status_code == 202, resumed.text
    assert sdd_live.wait_status(rid, TERMINAL)["status"] == "COMPLETED"
    wait_fsm(sdd_proj, "IMPLEMENTATION")
    assert verbs(sdd_fake) == ["delegate-enter", "delegate-exit"], "續跑沿用同一個委派"


def test_cancelling_a_paused_batch_also_hands_control_back(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    rid = post(sdd_live, sdd_body(run_body, sdd_proj, delay="0.8", count=3)).json()["run_id"]
    assert sdd_live.client.post(f"/autoclaude/runs/{rid}:pause").status_code == 202
    sdd_live.wait_status(rid, {"PAUSED"})
    assert sdd_live.client.post(f"/autoclaude/runs/{rid}:stop").status_code == 202
    assert sdd_live.wait_status(rid, {"CANCELLED"})["status"] == "CANCELLED"
    wait_fsm(sdd_proj, "IMPLEMENTATION")
    leave = argv_of(sdd_fake, "delegate-exit")
    assert flag(leave, "--reason") == f"console-run run={rid} CANCELLED"


# ── 基礎設施故障不動 FSM；回收點讓下一個批次自己解開陳舊委派（§10.3）──────────────────────────────
def test_an_abnormal_exit_leaves_the_delegation_and_the_next_batch_reclaims_it(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body, tmp_path: Path) -> None:
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    first, _ = _start_long(sdd_live, run_body, sdd_proj, tmp_path)
    procutil.begin_terminate(sdd_live.get_run(first)["pid"])          # 引擎被外力殺掉
    failed = sdd_live.wait_status(first, {"FAILED"})
    assert not failed["reason"].startswith("引擎升級"), "不是引擎升級型失敗"
    # 給（不該發生的）同步一點時間
    time.sleep(1.5)
    assert verbs(sdd_fake) == ["delegate-enter"], "基礎設施故障不得映成 FSM 的任何動作"
    state = fsm_state(sdd_proj)
    assert state["current_state"] == "AUTOCLAUDE_DELEGATED"
    assert state["autoclaude_delegated_tracking"]["playbook_ref"] == f"run:{first}"

    second_body = sdd_body(run_body, sdd_proj, delay="0.1")
    resp = post(sdd_live, second_body)
    assert resp.status_code == 201, resp.text
    second = resp.json()["run_id"]
    assert sdd_live.wait_status(second, TERMINAL)["status"] == "COMPLETED"
    wait_fsm(sdd_proj, "IMPLEMENTATION")
    assert verbs(sdd_fake) == ["delegate-enter", "delegate-exit", "delegate-enter", "delegate-exit"]
    reclaim = argv_of(sdd_fake, "delegate-exit", 0)
    assert (flag(reclaim, "--decision"), flag(reclaim, "--reason")) == (
        "done", f"console-run run={first} RECLAIMED old_status=FAILED by={second}")
    assert flag(argv_of(sdd_fake, "delegate-enter", 1), "--playbook-ref") == f"run:{second}"
    notes = [e for e in audit_entries(sdd_live) if e.get("verb") == "reclaim"]
    assert [(e["old_run_id"], e["old_status"], e["run_id"]) for e in notes] == [
        (first, "FAILED", second)], "回收在 Bridge audit 記一筆（含舊 run id 與舊終態）"
    hops = [(t["from"], t["to"]) for t in fsm_state(sdd_proj)["decision_trace"]]
    enter = ("IMPLEMENTATION", "AUTOCLAUDE_DELEGATED")
    leave = ("AUTOCLAUDE_DELEGATED", "IMPLEMENTATION")
    assert hops == [enter, leave, enter, leave]


def test_an_active_batch_blocks_another_batch_of_the_same_fsm_project(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body, tmp_path: Path) -> None:
    """不同的 Console 專案（不同 execution_path → advisory lock 不互擋）指向同一個 (狀態目錄, FSM
    專案)：由回收點第 4 條回 409（帶 run_id 與 run_status）。這是 Bridge 側的縱深（Backend 的部分
    唯一索引是第一道）。"""
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    first, _ = _start_long(sdd_live, run_body, sdd_proj, tmp_path, project="ProjA")
    sub = sdd_proj / "sub"
    sub.mkdir()
    body = sdd_body(run_body, sdd_proj, project="ProjB", execution_path=sub)
    calls_before = len(read_calls(sdd_fake))
    resp = post(sdd_live, body)
    assert (resp.status_code, resp.json()["reason"]) == (409, "fsm_state_conflict")
    got = resp.json()
    assert (got["current_state"], got["run_id"], got["run_status"]) == (
        "AUTOCLAUDE_DELEGATED", first, "RUNNING")
    assert got["detail"]["run_id"] == first and got["detail"]["run_status"] == "RUNNING"
    assert len(read_calls(sdd_fake)) == calls_before and not workspace_has(sdd_live, body["run_id"])
    assert sdd_live.client.post(f"/autoclaude/runs/{first}:stop").status_code == 202
    sdd_live.wait_status(first, {"CANCELLED"})
    wait_fsm(sdd_proj, "IMPLEMENTATION")
    assert post(sdd_live, body).status_code == 201, "舊批次取消後，同一個請求可通過"


@pytest.mark.parametrize("tracking", [
    {},                                                                   # 缺 playbook_ref
    {"playbook_ref": "manual-note"},                                      # 不以 run: 開頭
    {"playbook_ref": "spec:docs/x.md"},
], ids=["no-ref", "manual-note", "path-style"])
def test_a_delegation_the_bridge_did_not_start_is_never_touched(
        tracking: dict, sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    """外來委派（人在 SDD session 進入的）：Bridge 不碰，解卡由人在 SDD session `delegate-exit`。"""
    seed_frozen(sdd_proj, "AUTOCLAUDE_DELEGATED",
                autoclaude_delegated_tracking={"entered_at": "t", "resume_state": "IMPLEMENTATION",
                                               **tracking})
    body = sdd_body(run_body, sdd_proj)
    resp = post(sdd_live, body)
    assert (resp.status_code, resp.json()["reason"]) == (409, "fsm_state_conflict")
    assert resp.json()["detail"]["reason"] == "foreign_delegation"
    assert read_calls(sdd_fake) == [] and not workspace_has(sdd_live, body["run_id"])
    assert fsm_state(sdd_proj)["current_state"] == "AUTOCLAUDE_DELEGATED"


def test_a_delegation_pointing_at_a_run_the_bridge_never_heard_of_is_reclaimed_as_missing(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    ghost = str(uuid.uuid4())
    seed_frozen(sdd_proj, "AUTOCLAUDE_DELEGATED",
                autoclaude_delegated_tracking={"entered_at": "t", "resume_state": "IMPLEMENTATION",
                                               "playbook_ref": f"run:{ghost}"})
    resp = post(sdd_live, sdd_body(run_body, sdd_proj, delay="0.1"))
    assert resp.status_code == 201, resp.text
    rid = resp.json()["run_id"]
    sdd_live.wait_status(rid, TERMINAL)
    wait_fsm(sdd_proj, "IMPLEMENTATION")
    assert verbs(sdd_fake) == ["delegate-exit", "delegate-enter", "delegate-exit"]
    assert flag(argv_of(sdd_fake, "delegate-exit", 0), "--reason") == (
        f"console-run run={ghost} RECLAIMED old_status=missing by={rid}")


def test_a_run_of_another_fsm_project_is_foreign_even_when_it_is_long_finished(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    """回收點第 3 條：引用的 run 屬於別的 FSM 專案，不是我們能判斷的——就算它早已終態也不回收。"""
    seed_frozen(sdd_proj, "IMPLEMENTATION", key="alpha")
    done = post(sdd_live, sdd_body(run_body, sdd_proj, delay="0.1")).json()["run_id"]
    sdd_live.wait_status(done, TERMINAL)
    wait_fsm(sdd_proj, "IMPLEMENTATION", key="alpha")
    seed_frozen(sdd_proj, "AUTOCLAUDE_DELEGATED", key="beta",
                autoclaude_delegated_tracking={"entered_at": "t", "resume_state": "IMPLEMENTATION",
                                               "playbook_ref": f"run:{done}"})
    calls_before = len(read_calls(sdd_fake))
    body = sdd_body(run_body, sdd_proj, sdd=sdd_block(sdd_proj, key="beta"))
    resp = post(sdd_live, body)
    assert (resp.status_code, resp.json()["detail"]["reason"]) == (409, "foreign_delegation")
    assert len(read_calls(sdd_fake)) == calls_before


def test_the_tracking_ref_left_behind_after_an_exit_is_ignored_in_implementation(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    """🔴 tracking 在 exit 後**不清除**（歷史殘留欄）：IMPLEMENTATION 上的 `playbook_ref` 不得影響
    判斷。"""
    seed_frozen(sdd_proj, "IMPLEMENTATION",
                autoclaude_delegated_tracking={"playbook_ref": "manual-note-from-long-ago"})
    resp = post(sdd_live, sdd_body(run_body, sdd_proj, delay="0.1"))
    assert resp.status_code == 201, resp.text
    sdd_live.wait_status(resp.json()["run_id"], TERMINAL)
    wait_fsm(sdd_proj, "IMPLEMENTATION")
    assert verbs(sdd_fake) == ["delegate-enter", "delegate-exit"]


# ── resume／restore（§10.1 末列；D-115-18）：重驗、FSM 前置、權杖 ─────────────────────────────────
def _paused_batch(live, run_body, proj: Path, **kw: Any) -> str:
    body = sdd_body(run_body, proj, delay="0.8", count=3, **kw)
    rid = post(live, body).json()["run_id"]
    assert live.client.post(f"/autoclaude/runs/{rid}:pause").status_code == 202
    live.wait_status(rid, {"PAUSED"})
    return rid


def test_resuming_a_batch_whose_spec_changed_while_paused_is_409_and_spawns_nothing(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body, tmp_path: Path) -> None:
    """舊狀態檔（凍結時沒摘要）：只剩「匯入時＝現檔」那一點——暫停期間改檔，resume 就是 409
    import_vs_file。"""
    seed_frozen(sdd_proj, "IMPLEMENTATION", digests=False)
    trace = tmp_path / "trace.jsonl"
    rid = _paused_batch(sdd_live, run_body, sdd_proj, env={"MOCK_CLAUDE_TRACE": str(trace)})
    spawned = len(trace_calls(trace))
    calls = len(read_calls(sdd_fake))
    spec = contracts_dir(sdd_proj) / TCS_NAME
    spec.write_text(TCS_TEXT + "\n<!-- 暫停期間被改 -->\n", encoding="utf-8", newline="")
    resp = sdd_live.client.post(f"/autoclaude/runs/{rid}:resume", headers={"X-Bridge-Token": TOKEN})
    assert (resp.status_code, resp.json()["reason"]) == (409, "spec_digest_changed")
    assert resp.json()["pair"] == "import_vs_file"
    assert sdd_live.get_run(rid)["status"] == "PAUSED", "不合就不 spawn：run 仍是 PAUSED"
    assert len(trace_calls(trace)) == spawned and len(read_calls(sdd_fake)) == calls
    spec.write_text(TCS_TEXT, encoding="utf-8", newline="")
    assert sdd_live.client.post(f"/autoclaude/runs/{rid}:resume",
                                headers={"X-Bridge-Token": TOKEN}).status_code == 202
    assert sdd_live.wait_status(rid, TERMINAL)["status"] == "COMPLETED"


def test_resuming_after_the_frozen_spec_was_edited_is_409_frozen_vs_file(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    seed_frozen(sdd_proj, "IMPLEMENTATION", digests=True)
    rid = _paused_batch(sdd_live, run_body, sdd_proj)
    (contracts_dir(sdd_proj) / TCS_NAME).write_text(TCS_TEXT + "\n<!-- 改 -->\n", encoding="utf-8",
                                                    newline="")
    resp = sdd_live.client.post(f"/autoclaude/runs/{rid}:resume", headers={"X-Bridge-Token": TOKEN})
    assert (resp.status_code, resp.json()["reason"], resp.json()["pair"]) == (
        409, "spec_digest_changed", "frozen_vs_file")
    assert sdd_live.get_run(rid)["status"] == "PAUSED"


def test_resuming_while_the_fsm_is_blocked_is_409_and_the_run_stays_paused(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    rid = _paused_batch(sdd_live, run_body, sdd_proj)
    # 人（或別的 session）把 FSM 推走了
    seed_frozen(sdd_proj, "ESCALATION")
    calls = len(read_calls(sdd_fake))
    resp = sdd_live.client.post(f"/autoclaude/runs/{rid}:resume", headers={"X-Bridge-Token": TOKEN})
    assert (resp.status_code, resp.json()["reason"], resp.json()["current_state"]) == (
        409, "fsm_state_conflict", "ESCALATION")
    assert resp.json()["expected_state"] == ["AUTOCLAUDE_DELEGATED", "IMPLEMENTATION"]
    assert sdd_live.get_run(rid)["status"] == "PAUSED" and len(read_calls(sdd_fake)) == calls


def test_resuming_after_a_human_left_the_delegation_re_enters_it(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    rid = _paused_batch(sdd_live, run_body, sdd_proj)
    # 人在 SDD session 手動 exit 了
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    resumed = sdd_live.client.post(f"/autoclaude/runs/{rid}:resume",
                                   headers={"X-Bridge-Token": TOKEN})
    assert resumed.status_code == 202, resumed.text
    assert sdd_live.wait_status(rid, TERMINAL)["status"] == "COMPLETED"
    wait_fsm(sdd_proj, "IMPLEMENTATION")
    assert verbs(sdd_fake) == ["delegate-enter", "delegate-enter", "delegate-exit"]
    assert flag(argv_of(sdd_fake, "delegate-enter", 1), "--playbook-ref") == f"run:{rid}"


@pytest.mark.parametrize("header", [None, "", "wrong", TOKEN + "x"])
def test_resume_of_an_sdd_run_needs_the_write_token(
        header: str | None, sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    """D-115-18：它會 delegate-enter＝FSM 寫入，與建立同一個權杖規則。缺／錯＝403，run 仍是
    PAUSED、沒有任何 FSM 動作。"""
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    rid = _paused_batch(sdd_live, run_body, sdd_proj)
    calls = len(read_calls(sdd_fake))
    headers = {} if header is None else {"X-Bridge-Token": header}
    resp = sdd_live.client.post(f"/autoclaude/runs/{rid}:resume", headers=headers)
    assert (resp.status_code, resp.json()) == (403, {"code": 403, "reason": "sdd_write_forbidden"})
    assert sdd_live.get_run(rid)["status"] == "PAUSED" and len(read_calls(sdd_fake)) == calls
    rejected = [e for e in audit_entries(sdd_live) if e.get("verb") == "resume"]
    assert rejected[-1]["result"] == "rejected:sdd_write_forbidden"
    assert rejected[-1]["run_id"] == rid
    assert TOKEN not in json.dumps(rejected)


def test_resume_of_an_sdd_run_is_503_when_the_bridge_has_no_token(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    rid = _paused_batch(sdd_live, run_body, sdd_proj)
    # Settings 是 frozen dataclass
    object.__setattr__(sdd_live.settings, "sdd_write_token", None)
    try:
        resp = sdd_live.client.post(f"/autoclaude/runs/{rid}:resume",
                                    headers={"X-Bridge-Token": TOKEN})
    finally:
        object.__setattr__(sdd_live.settings, "sdd_write_token", TOKEN)
    assert (resp.status_code, resp.json()["reason"]) == (503, "sdd_write_disabled")
    assert sdd_live.get_run(rid)["status"] == "PAUSED"


def test_resume_of_an_ordinary_run_never_asks_for_a_token(sdd_live, run_body) -> None:
    body = run_body(delay="0.6")
    rid = sdd_live.post_run(body).json()["run_id"]
    assert sdd_live.client.post(f"/autoclaude/runs/{rid}:pause").status_code == 202
    sdd_live.wait_status(rid, {"PAUSED"})
    assert sdd_live.client.post(f"/autoclaude/runs/{rid}:resume").status_code == 202, \
        "不帶 sdd 的 run 照舊：續跑不需要權杖"
    assert sdd_live.wait_status(rid, TERMINAL)["status"] == "COMPLETED"


def test_restore_of_a_finished_sdd_batch_re_enters_the_delegation_and_needs_the_token(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    rid = post(sdd_live, sdd_body(run_body, sdd_proj, delay="0.2")).json()["run_id"]
    assert sdd_live.wait_status(rid, TERMINAL)["status"] == "COMPLETED"
    wait_fsm(sdd_proj, "IMPLEMENTATION")
    listing = sdd_live.client.get(f"/autoclaude/runs/{rid}/checkpoints").json()
    checkpoint = listing[0]["checkpoint_id"]
    url, payload = f"/autoclaude/runs/{rid}/restore", {"checkpoint_id": checkpoint}
    for headers in ({}, {"X-Bridge-Token": "wrong"}):
        resp = sdd_live.client.post(url, json=payload, headers=headers)
        assert (resp.status_code, resp.json()["reason"]) == (403, "sdd_write_forbidden")
    assert sdd_live.get_run(rid)["status"] == "COMPLETED", "被拒的 restore 沒動 run"
    assert verbs(sdd_fake) == ["delegate-enter", "delegate-exit"]
    ok = sdd_live.client.post(url, json=payload, headers={"X-Bridge-Token": TOKEN})
    assert ok.status_code == 202, ok.text
    time.sleep(0.3)
    assert sdd_live.wait_status(rid, TERMINAL)["status"] == "COMPLETED"
    wait_fsm(sdd_proj, "IMPLEMENTATION")
    assert verbs(sdd_fake) == ["delegate-enter", "delegate-exit", "delegate-enter", "delegate-exit"]
    assert flag(argv_of(sdd_fake, "delegate-enter", 1), "--playbook-ref") == f"run:{rid}"
    rows = [e for e in audit_entries(sdd_live) if e.get("verb") == "restore"]
    assert [r["result"] for r in rows] == ["rejected:sdd_write_forbidden",
                                           "rejected:sdd_write_forbidden", "ok"]


def test_restore_is_refused_while_another_batch_of_the_same_fsm_project_is_active(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body, tmp_path: Path) -> None:
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    first_body = sdd_body(run_body, sdd_proj, delay="0.2", project="ProjA")
    old = post(sdd_live, first_body).json()["run_id"]
    sdd_live.wait_status(old, TERMINAL)
    wait_fsm(sdd_proj, "IMPLEMENTATION")
    listing = sdd_live.client.get(f"/autoclaude/runs/{old}/checkpoints").json()
    checkpoint = listing[0]["checkpoint_id"]
    sub = sdd_proj / "sub"
    sub.mkdir()
    newer, _ = _start_long(sdd_live, run_body, sdd_proj, tmp_path, project="ProjB",
                           execution_path=sub)
    before = sdd_live.get_run(old)
    resp = sdd_live.client.post(
        f"/autoclaude/runs/{old}/restore", json={"checkpoint_id": checkpoint},
        headers={"X-Bridge-Token": TOKEN})
    assert (resp.status_code, resp.json()["reason"]) == (409, "fsm_state_conflict")
    assert (resp.json()["run_id"], resp.json()["run_status"]) == (newer, "RUNNING")
    after = sdd_live.get_run(old)
    assert (after["status"], after["completed_at"], after["exit_code"]) == (
        before["status"], before["completed_at"], before["exit_code"]), "不合就不改動終態 run"
    assert sdd_live.client.post(f"/autoclaude/runs/{newer}:stop").status_code == 202
    sdd_live.wait_status(newer, {"CANCELLED"})


# ── Bridge 重啟：孤兒不動 FSM、交給回收點（§10.1 孤兒列）────────────────────────────────────────
def _orphan_manager(settings, sdd_fake: Path, sdd_proj: Path, tmp_path: Path):
    from app.locks import AdvisoryLock
    from app.security import AuditLog

    mgr = RunManager(settings, locks=AdvisoryLock(None), audit=AuditLog(tmp_path / "audit.jsonl"))
    rid = str(uuid.uuid4())
    ctx = sdd_run.SddContext(
        spec_dir=contracts_dir(sdd_proj).resolve(), spec_file=None, fsm_project="alpha",
        root=sdd_proj.resolve(), state_dir=(sdd_proj / FSM_REL).resolve(), approver="operator")
    paths = RunPaths(settings.engine_workspace / rid)
    paths.run_dir.mkdir(parents=True)
    paths.playbook.write_text("tasks: []\n", encoding="utf-8")
    rec = RunRecord(run_id=rid, project="ProjA", execution_path=str(sdd_proj), status="RUNNING",
                    pid=None, sdd=ctx.record())
    save_record(paths, rec)
    return mgr, rid, ctx


def test_reconcile_marks_an_orphaned_sdd_run_failed_without_touching_the_fsm(
        settings, sdd_fake: Path, sdd_proj: Path, tmp_path: Path) -> None:
    from dataclasses import replace

    cfg = replace(settings, sdd_root=sdd_fake, sdd_write_token=TOKEN)
    seed_frozen(sdd_proj, "AUTOCLAUDE_DELEGATED")
    mgr, rid, ctx = _orphan_manager(cfg, sdd_fake, sdd_proj, tmp_path)
    assert mgr.reconcile() == [rid]
    handle = mgr.get(rid)
    assert handle is not None and handle.rec.status == "FAILED" and "orphaned" in handle.rec.reason
    assert handle.rec.sdd is not None and handle.rec.sdd["fsm_project"] == "alpha"
    assert read_calls(sdd_fake) == [], "孤兒不動 FSM（留給回收點）"
    facts = mgr.sdd_facts(rid)
    assert facts == RunFacts(status="FAILED", state_dir=ctx.state_key, fsm_project="alpha")
    assert mgr.sdd_facts(str(uuid.uuid4())) is None
    # 回收點看得到它：委派指著這個孤兒 run ⇒ 以終態 FAILED 回收
    state = {"current_state": "AUTOCLAUDE_DELEGATED",
             "autoclaude_delegated_tracking": {"playbook_ref": f"run:{rid}"}}
    plan = sdd_run.plan_delegation(state, ctx=ctx, run_id=str(uuid.uuid4()), mode="create",
                                   lookup=mgr.sdd_facts)
    assert plan.reclaim and plan.verdict is not None
    assert (plan.verdict.old_run_id, plan.verdict.old_status) == (rid, "FAILED")


def test_a_cancelling_orphan_is_cancelled_and_still_not_synced(
        settings, sdd_fake: Path, sdd_proj: Path, tmp_path: Path) -> None:
    from dataclasses import replace

    cfg = replace(settings, sdd_root=sdd_fake, sdd_write_token=TOKEN)
    seed_frozen(sdd_proj, "AUTOCLAUDE_DELEGATED")
    mgr, rid, _ = _orphan_manager(cfg, sdd_fake, sdd_proj, tmp_path)
    handle_paths = RunPaths(cfg.engine_workspace / rid)
    rec = load_record(handle_paths.run_json)
    assert rec is not None
    rec.status = "CANCELLING"
    save_record(handle_paths, rec)
    assert mgr.reconcile() == [rid]
    handle = mgr.get(rid)
    assert handle is not None and handle.rec.status == "CANCELLED"
    assert read_calls(sdd_fake) == [], "孤兒被標成 CANCELLED 也不動 FSM"


# ── RunRecord.sdd：往返、舊檔相容、無機密（§10.3）──────────────────────────────────────────────
def test_run_record_sdd_round_trips_and_old_files_without_it_load_with_the_default(
        tmp_path: Path) -> None:
    paths = RunPaths(tmp_path / "r1")
    sdd = {"spec_dir": "/s", "spec_file": None, "fsm_project": "alpha", "root": "/r",
           "state_dir": "/r/build/reports/fsm", "approver": "operator", "sync": None}
    rec = RunRecord(run_id="r1", project="p", execution_path="/e", sdd=sdd)
    save_record(paths, rec)
    assert load_record(paths.run_json).sdd == sdd
    legacy = rec.to_dict()
    del legacy["sdd"]                                                  # 舊 run.json 沒有這個鍵
    assert RunRecord.from_dict(legacy).sdd is None
    future = {**rec.to_dict(), "something_from_a_newer_bridge": 1}
    assert RunRecord.from_dict(future).sdd == sdd, "未知鍵一律忽略（schema_version 不變）"
    assert RunRecord(run_id="r2", project="p", execution_path="/e").sdd is None


def test_the_sdd_context_record_has_exactly_the_documented_keys_and_no_secret(
        tmp_path: Path) -> None:
    ctx = sdd_run.SddContext(spec_dir=tmp_path / "d", spec_file=tmp_path / "d" / "t.md",
                             fsm_project="alpha", root=tmp_path, state_dir=tmp_path / "s",
                             approver="op")
    record = ctx.record()
    assert set(record) == {"spec_dir", "spec_file", "fsm_project", "root", "state_dir", "approver",
                           "sync"}
    assert sdd_run.SddContext.from_record(record) == ctx
    assert sdd_run.SddContext.from_record({**record, "spec_file": None}).spec_file is None
    assert sdd_run.SddContext.from_record({**record, "approver": None}).approver == "console"


# ── 引擎子行程環境（§9「剝除」列；F-7 的單元面）─────────────────────────────────────────────────
def _handle(settings, tmp_path: Path, sdd: dict | None, env: dict | None = None) -> RunHandle:
    from app.locks import AdvisoryLock
    from app.security import AuditLog

    mgr = RunManager(settings, locks=AdvisoryLock(None), audit=AuditLog(None))
    rec = RunRecord(run_id="r1", project="p", execution_path=str(tmp_path), sdd=sdd)
    return RunHandle(mgr, rec, RunPaths(tmp_path / "r1"), [], request_env=env)


def test_child_env_never_inherits_the_write_surface_names_and_only_sdd_runs_get_the_project(
        settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRIDGE_SDD_WRITE_TOKEN", TOKEN)
    monkeypatch.setenv("SDD_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("SDD_PROJECT", "someone-elses-project")
    monkeypatch.setenv("MINIMAX_API_KEY", "engine-needs-this")
    plain = _handle(settings, tmp_path, None, {"MOCK_CLAUDE_DELAY": "0.1"})._child_env()
    upper = {k.upper(): v for k, v in plain.items()}
    for name in ("BRIDGE_SDD_WRITE_TOKEN", "SDD_STATE_DIR", "SDD_PROJECT"):
        assert name not in upper, f"不含 sdd 的 run：{name} 不得出現"
    assert upper["MINIMAX_API_KEY"] == "engine-needs-this", "引擎需要的環境照舊繼承"
    assert upper["MOCK_CLAUDE_DELAY"] == "0.1" and upper["PYTHONUTF8"] == "1"
    assert TOKEN not in json.dumps(plain)

    sdd = {"spec_dir": "/s", "spec_file": None, "fsm_project": "alpha", "root": "/r",
           "state_dir": "/r/build/reports/fsm", "approver": "op", "sync": None}
    with_sdd = {k.upper(): v for k, v in _handle(settings, tmp_path, sdd)._child_env().items()}
    assert with_sdd["SDD_PROJECT"] == "alpha", "含 sdd 的 run：只有 SDD_PROJECT，值是本批次的鍵"
    assert "SDD_STATE_DIR" not in with_sdd and "BRIDGE_SDD_WRITE_TOKEN" not in with_sdd


def test_the_digests_used_by_these_tests_are_the_documented_algorithm() -> None:
    """對照組：本檔與 sdd_run_support 的獨立摘要實作＝ADR §4.3 的算法（換行正規化的 UTF-8
    sha256）。"""
    import hashlib

    expected = "sha256:" + hashlib.sha256(TCS_TEXT.encode("utf-8")).hexdigest()
    assert digest_of(TCS_TEXT) == digest_of(TCS_TEXT.replace("\n", "\r\n")) == expected
