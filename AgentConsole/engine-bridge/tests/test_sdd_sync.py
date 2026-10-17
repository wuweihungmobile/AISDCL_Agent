"""`app/sdd_sync.py` 的純函式：reason 組字、輸入清理、終態對映、預檢表、回收點判定（ADR-XPLAT-016
§4.4、§10）。

對映表因為是純函式，可以不起任何子行程就窮舉。這裡每一格都對應 ADR 的一個決定；測試名稱寫的是「為
什麼」，因為這些格子被改錯的代價是：把基礎設施故障映成阻塞態（人要出來解卡）、或把別人的委派誤回
收。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app import sdd_run, sdd_sync
from app.errors import ApiError
from app.models import RunStatus
from app.sdd_sync import (
    ACTIVE_RUN_STATUSES,
    RunFacts,
    clean_approver,
    clean_user_reason,
    judge_delegation,
    terminal_decision,
)

NEW = "11111111-1111-4111-8111-111111111111"
OLD = "22222222-2222-4222-8222-222222222222"
STATE_DIR = "c:/proj/build/reports/fsm"


# ── 終態對映（§10.1）：done＝交還控制權（不是成功）；只有引擎升級型失敗是 failed ────────────────
@pytest.mark.parametrize(("status", "escalation", "flags", "expected"), [
    ("COMPLETED", "", {}, "done"),                                         # 正常走完
    ("CANCELLED", "", {}, "done"),                                         # D-115-15：取消也是交還
    ("FAILED", "retries exhausted at T02", {}, "failed"),                  # 引擎升級型（唯一）
    # 額度停機／異常／被訊號終止
    ("FAILED", "", {}, None),
    ("FAILED", "x", {"shutting_down": True}, None),                        # Bridge 關閉：不動
    ("FAILED", "x", {"orphan": True}, None),                               # 孤兒：留給回收點
    # 孤兒被標 CANCELLED 也不動
    ("CANCELLED", "", {"orphan": True}, None),
    ("COMPLETED", "", {"orphan": True}, None),
    ("PAUSED", "", {}, None),                                              # 委派仍開著，可 :resume
    ("PAUSING", "", {}, None), ("RUNNING", "", {}, None), ("INITIALIZING", "", {}, None),
    ("CANCELLING", "", {}, None),
])
def test_terminal_decision_follows_the_adr_table(
        status: str, escalation: str, flags: dict, expected: str | None) -> None:
    assert terminal_decision(status, escalation=escalation, **flags) == expected


def test_infrastructure_failures_are_never_mapped_to_the_blocking_state() -> None:
    """`failed` 會進阻塞態 ESCALATION（只有人能解）：額度停機、異常結束、被訊號終止、spawn 失敗、
    Bridge 關閉、孤兒都不是引擎在說「我撐不下去」，不得映成它。窮舉所有組合：failed 只在
    「FAILED＋有升級訊息＋非孤兒＋非關閉＋沒被要求停止」同時成立時出現。"""
    for status in (s.value for s in RunStatus):
        for escalation in ("", "esc"):
            for stop in (False, True):
                for shutting in (False, True):
                    for orphan in (False, True):
                        got = terminal_decision(status, escalation=escalation, stop_requested=stop,
                                                shutting_down=shutting, orphan=orphan)
                        if got == "failed":
                            assert (status, escalation, stop, shutting, orphan) == (
                                "FAILED", "esc", False, False, False)
                        if got == "done":
                            assert status in ("COMPLETED", "CANCELLED") and not (shutting or orphan)
                        assert got in ("done", "failed", None)


def test_a_stop_request_turns_an_escalation_failure_into_no_escalation_report() -> None:
    assert terminal_decision("FAILED", escalation="x", stop_requested=True) is None


# ── 六種固定 reason 組字（§4.4）──────────────────────────────────────────────────────────────────
def test_the_six_reason_forms_are_pinned_verbatim() -> None:
    assert sdd_sync.reason_freeze("op", "核准") == "console-freeze approver=op; reason=核准"
    assert sdd_sync.reason_negotiate_enter("op", NEW) == f"console-signoff approver=op; run={NEW}"
    assert sdd_sync.reason_negotiate_exit("op", "docs/TCS-A.md", "sha256:" + "a" * 64) == (
        "console-signoff approver=op; oracle=docs/TCS-A.md@sha256:" + "a" * 64
        + "; basis=import-draft-signoff; r9.20.3=not-satisfied")
    assert sdd_sync.reason_delegate_enter(NEW) == f"console-run run={NEW} START"
    assert sdd_sync.reason_exit_completed(NEW) == f"console-run run={NEW} COMPLETED"
    assert sdd_sync.reason_exit_cancelled(NEW) == f"console-run run={NEW} CANCELLED"
    assert sdd_sync.reason_exit_reclaimed(OLD, "FAILED", NEW) == (
        f"console-run run={OLD} RECLAIMED old_status=FAILED by={NEW}")
    assert sdd_sync.reason_exit_reclaimed(OLD, None, NEW) == (
        f"console-run run={OLD} RECLAIMED old_status=missing by={NEW}")
    assert sdd_sync.reason_exit_spawn_failed(NEW) == (
        f"console-run run={NEW} SPAWN-FAILED delegation not started")
    assert sdd_sync.reason_exit_failed(NEW, "T02", "retries exhausted") == (
        f"console-run run={NEW} ENGINE-ESCALATION step=T02: retries exhausted")
    assert sdd_sync.reason_exit_failed(NEW, "", "x").endswith("step=-: x")


def test_every_reason_starts_with_console_and_uses_semicolon_separated_pairs() -> None:
    reasons = [sdd_sync.reason_freeze("a", "r"), sdd_sync.reason_negotiate_enter("a", NEW),
               sdd_sync.reason_negotiate_exit("a", "p", "d"), sdd_sync.reason_delegate_enter(NEW),
               sdd_sync.reason_exit_completed(NEW), sdd_sync.reason_exit_cancelled(NEW),
               sdd_sync.reason_exit_reclaimed(OLD, "FAILED", NEW),
               sdd_sync.reason_exit_spawn_failed(NEW), sdd_sync.reason_exit_failed(NEW, "s", "d")]
    assert all(r.startswith("console-") for r in reasons)


def test_the_engine_escalation_detail_is_one_line_and_cut_at_200_characters() -> None:
    nasty = "第一行\n第二行\r\n第三行\t" + "x" * 400 + "\x00"
    reason = sdd_sync.reason_exit_failed(NEW, "T01", nasty)
    detail = reason.split(": ", 1)[1]
    assert len(detail) == 200 and "\n" not in detail and "\r" not in detail and "\x00" not in detail
    assert detail.startswith("第一行 第二行  第三行 ")


def test_playbook_ref_and_default_stage_formats() -> None:
    assert sdd_sync.playbook_ref(NEW) == f"run:{NEW}", \
        "帶 run: 前綴，與文件路徑型的 spec_refs 可區分"
    assert [sdd_sync.default_stage(n) for n in (0, 1, 7)] == ["Stage-1", "Stage-2", "Stage-8"]


# ── 輸入清理（§4.4）：不靜默截斷、不替換 ───────────────────────────────────────────────────────
def test_clean_approver_defaults_to_the_service_identity_and_rejects_ambiguous_values() -> None:
    assert clean_approver(None) == "console"
    assert clean_approver("operator") == "operator" and clean_approver("a" * 100) == "a" * 100
    assert clean_approver("王小明") == "王小明"
    for bad, rule in (("", "empty"), ("  ", "empty"), ("a;b", "semicolon"), ("x" * 101, "too_long"),
                      ("a\nb", "control_chars"), (" a", "surrounding_whitespace")):
        with pytest.raises(ApiError) as caught:
            clean_approver(bad)
        error = caught.value
        assert (error.status_code, error.body["reason"]) == (422, "sdd_invalid_argument")
        assert (error.body["field"], error.body["rule"]) == ("approver", rule)


def test_clean_user_reason_strips_but_never_truncates_or_rewrites() -> None:
    assert clean_user_reason("  核准  ") == "核准"
    assert clean_user_reason("x" * 500) == "x" * 500
    for bad, rule in (("", "empty"), (" \t ", "empty"), ("x" * 501, "too_long"),
                      ("a\nb", "control_chars"), ("a\x00b", "control_chars")):
        with pytest.raises(ApiError) as caught:
            clean_user_reason(bad)
        assert (caught.value.body["field"], caught.value.body["rule"]) == ("reason", rule)


# ── 回收點判定（§10.3 五條，依序）─────────────────────────────────────────────────────────────
def _facts(status: str, state_dir: str | None = STATE_DIR, project: str | None = "alpha"):
    return RunFacts(status=status, state_dir=state_dir, fsm_project=project)


def _judge(ref: str | None, runs: dict[str, RunFacts]):
    return judge_delegation(ref, new_run_id=NEW, state_dir=STATE_DIR, fsm_project="alpha",
                            lookup=runs.get)


def test_row0_a_delegation_that_names_this_very_run_is_ours_to_continue() -> None:
    verdict = _judge(f"run:{NEW}", {})
    assert verdict.action == "own"


@pytest.mark.parametrize("ref", [None, "", "manual-note", "RUN:" + OLD, OLD, "spec:docs/x.md"])
def test_row1_a_foreign_delegation_is_never_touched_by_the_bridge(ref: str | None) -> None:
    """外來委派（人在 SDD session 進入的）：缺 playbook_ref 或不以 `run:` 開頭。解卡由人在 SDD
    session 做。"""
    verdict = _judge(ref, {OLD: _facts("COMPLETED")})
    assert (verdict.action, verdict.sub_reason) == ("conflict", "foreign_delegation")


def test_row2_a_referenced_run_the_bridge_has_never_heard_of_is_reclaimed_as_missing() -> None:
    verdict = _judge(f"run:{OLD}", {})
    assert (verdict.action, verdict.old_run_id, verdict.old_status) == ("reclaim", OLD, "missing")


@pytest.mark.parametrize("other", [
    _facts("FAILED", state_dir="c:/another/build/reports/fsm"),           # 別的狀態目錄
    _facts("FAILED", project="beta"),                                     # 別的 FSM 專案
    # 不是 SDD run（沒有 sdd 記錄）
    _facts("RUNNING", state_dir=None),
    _facts("RUNNING", project=None),
])
def test_row3_a_run_of_another_fsm_project_is_foreign_even_if_it_looks_dead_or_alive(
        other: RunFacts) -> None:
    verdict = _judge(f"run:{OLD}", {OLD: other})
    assert (verdict.action, verdict.sub_reason) == ("conflict", "foreign_delegation")
    assert verdict.run_id is None, "不回報別的專案的 run id"


@pytest.mark.parametrize("status", sorted(ACTIVE_RUN_STATUSES))
def test_row4_an_active_run_blocks_the_new_batch_with_its_id_and_status(status: str) -> None:
    """活躍＝INITIALIZING／RUNNING／PAUSING／PAUSED／CANCELLING（過渡態隨時可能繼續寫）。"""
    verdict = _judge(f"run:{OLD}", {OLD: _facts(status)})
    assert (verdict.action, verdict.run_id, verdict.run_status) == ("conflict", OLD, status)
    assert verdict.sub_reason is None
    assert sdd_sync.conflict_fields(verdict) == {"run_id": OLD, "run_status": status}


@pytest.mark.parametrize("status", ["COMPLETED", "FAILED", "CANCELLED"])
def test_row5_a_terminal_run_is_reclaimed_with_its_final_status(status: str) -> None:
    verdict = _judge(f"run:{OLD}", {OLD: _facts(status)})
    assert (verdict.action, verdict.old_run_id, verdict.old_status) == ("reclaim", OLD, status)


def test_active_statuses_are_exactly_the_non_terminal_ones() -> None:
    assert ACTIVE_RUN_STATUSES == {s.value for s in RunStatus} - sdd_sync.TERMINAL_RUN_STATUSES


# ── 預檢表（§10.2）：FSM 現況 → 要依序呼叫的動詞 ──────────────────────────────────────────────
@pytest.fixture
def ctx(tmp_path: Path) -> sdd_run.SddContext:
    return sdd_run.SddContext(
        spec_dir=tmp_path / "docs", spec_file=None, fsm_project="alpha", root=tmp_path,
        state_dir=tmp_path / "build" / "reports" / "fsm", approver="op")


def _plan(ctx, state: str, *, mode: str = "create", **extra):
    return sdd_run.plan_delegation({"current_state": state, **extra}, ctx=ctx, run_id=NEW,
                                   mode=mode, lookup=lambda _id: None)


@pytest.mark.parametrize(("state", "verbs"), [
    ("IMPLEMENTATION", ("delegate-enter",)),
    ("TEST_CONTRACT_NEGOTIATED", ("negotiate-exit", "delegate-enter")),          # 自癒
    ("SPEC_FROZEN", ("negotiate-enter", "negotiate-exit", "delegate-enter")),   # 首次批次
])
def test_the_create_preflight_table(ctx, state: str, verbs: tuple[str, ...]) -> None:
    assert _plan(ctx, state).verbs == verbs


@pytest.mark.parametrize("state", [
    "INIT", "SPEC_DRAFTING", "SCG_VALIDATION", "HUMAN_PENDING", "ESCALATION",
    "ESCALATION_FINAL", "PR_REVIEW", "RELEASE", None, 7])
def test_every_other_state_is_a_409_naming_where_the_fsm_is(ctx, state) -> None:
    with pytest.raises(ApiError) as caught:
        _plan(ctx, state)
    body = caught.value.body
    assert (caught.value.status_code, body["reason"]) == (409, "fsm_state_conflict")
    assert body["current_state"] == state
    assert body["expected_state"] == ["IMPLEMENTATION", "SPEC_FROZEN"]


@pytest.mark.parametrize("state", ["SPEC_FROZEN", "TEST_CONTRACT_NEGOTIATED", "HUMAN_PENDING",
                                   "ESCALATION", "INIT"])
def test_resume_and_restore_never_negotiate_and_never_get_past_a_blocking_state(
        ctx, state: str) -> None:
    """`:resume`／`/restore` 只有 DELEGATED（本 run 的委派）與 IMPLEMENTATION（enter 重進）；其餘
    含 ESCALATION一律 409 並不 spawn。談判屬首次批次，不在續跑路徑上補做。"""
    with pytest.raises(ApiError) as caught:
        _plan(ctx, state, mode="continue")
    assert caught.value.body["expected_state"] == ["AUTOCLAUDE_DELEGATED", "IMPLEMENTATION"]


def test_resume_from_implementation_just_reenters_the_delegation(ctx) -> None:
    assert _plan(ctx, "IMPLEMENTATION", mode="continue").verbs == ("delegate-enter",)


def test_a_delegated_state_goes_through_the_reclaim_judgement(ctx) -> None:
    own = _plan(ctx, "AUTOCLAUDE_DELEGATED", mode="continue",
                autoclaude_delegated_tracking={"playbook_ref": f"run:{NEW}"})
    assert own.own and own.verbs == () and not own.reclaim
    stale = _plan(ctx, "AUTOCLAUDE_DELEGATED",
                  autoclaude_delegated_tracking={"playbook_ref": f"run:{OLD}"})
    assert stale.reclaim and stale.verbs == ("delegate-exit", "delegate-enter")
    with pytest.raises(ApiError) as caught:
        # 沒有 playbook_ref＝外來
        _plan(ctx, "AUTOCLAUDE_DELEGATED")
    assert caught.value.body["detail"]["reason"] == "foreign_delegation"
    assert caught.value.body["current_state"] == "AUTOCLAUDE_DELEGATED"


def test_the_tracking_ref_is_ignored_unless_the_fsm_is_currently_delegated(ctx) -> None:
    """🔴 tracking 在 exit 後**不清除**（歷史殘留欄）：IMPLEMENTATION 上的 `playbook_ref` 不得影響
    任何判斷。"""
    plan = _plan(ctx, "IMPLEMENTATION",
                 autoclaude_delegated_tracking={"playbook_ref": f"run:{OLD}"})
    assert plan.verdict is None and plan.verbs == ("delegate-enter",)
