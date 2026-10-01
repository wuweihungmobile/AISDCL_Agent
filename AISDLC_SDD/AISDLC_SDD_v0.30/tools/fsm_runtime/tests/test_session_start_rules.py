"""Phase 2 (2a) — session_start.py 逐態揭露治理規則的接線測試。

驗證 rule_loader 已接進 session 生命週期（裁剪 CLAUDE.md 前的前置條件）：
當前 FSM 狀態命中的 R-*.yaml 會被注入 additionalContext。
"""
from __future__ import annotations

import contextlib
import importlib.util
from pathlib import Path

import pytest

FRAMEWORK_ROOT = Path(__file__).resolve().parents[3]
HOOK = FRAMEWORK_ROOT / ".claude" / "hooks" / "session_start.py"
PRE_HOOK = FRAMEWORK_ROOT / ".claude" / "hooks" / "context_ledger_pre.py"


def _load_hook():
    spec = importlib.util.spec_from_file_location("sdd_session_start_under_test", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def test_rule_lines_surfaces_state_specific_rules():
    mod = _load_hook()
    lines = mod._rule_lines("EXECUTION_EVALUATION")
    joined = "\n".join(lines)
    assert "[SDD-RULES]" in joined
    assert "R-9.20" in joined  # Phase H gate 規則命中 EXECUTION_EVALUATION


def test_rule_lines_escalation_excludes_phase_h_gate():
    mod = _load_hook()
    joined = "\n".join(mod._rule_lines("ESCALATION"))
    assert "R-9.14" in joined        # self-healing 命中 ESCALATION
    assert "R-9.20" not in joined    # phase-h gate 不應命中 ESCALATION


def test_rule_lines_returns_list_never_raises():
    mod = _load_hook()
    # 不存在的狀態 → 可能命中 "*" 全域規則或空，但不可丟例外
    out = mod._rule_lines("DOES_NOT_EXIST_STATE")
    assert isinstance(out, list)


# ── DEF-200-275 第四輪（C10）：BLOCK 訊息帶一行可執行恢復指令；一開場印量測來源 ──
def _isolated_runtime(tmp_path):
    import os
    from unittest.mock import patch
    from types import SimpleNamespace
    import tools.fsm_runtime.fsm_runtime as fsm_rt_mod
    import tools.fsm_runtime.production_monitor as pm
    from tools.fsm_runtime.fsm_runtime import FSMRuntime
    from tools.fsm_runtime.state_loader import load_state

    state = load_state("ss-proj", path=tmp_path / "FSM-STATE-ss.yaml")
    rt = FSMRuntime(state)
    env = dict(os.environ)
    for k in ("SDD_MAX_CONTEXT", "AUTOSDD_CONTEXT_WINDOW", "CLAUDE_CODE_AUTO_COMPACT_WINDOW"):
        env.pop(k, None)
    env.update({"SDD_HOOKS_DISABLE": "", "SDD_HUB_DISABLE": "1", "HOME": str(tmp_path),
                "USERPROFILE": str(tmp_path), "CLAUDE_PROJECT_DIR": str(tmp_path)})
    patches = [
        patch.object(fsm_rt_mod.FSMRuntime, "bootstrap", classmethod(lambda cls, project=None: rt)),
        patch.object(pm, "scan_inbox", lambda: SimpleNamespace(scanned=0, applied=0, quarantined=0, drift_reports=[])),
        patch.dict(os.environ, env, clear=True),
    ]
    return rt, patches


def test_block_message_carries_recovery_command_for_escalation(tmp_path):
    rt, patches = _isolated_runtime(tmp_path)
    for p in patches:
        p.start()
    try:
        rt.state.record_escalation("TOKEN_BUDGET_CRITICAL: cumulative=993581 ratio=0.99",
                                   details={"session_id": "s-old"})
        mod = _load_hook()
        ctx = mod._build_context({})["hookSpecificOutput"]["additionalContext"]
    finally:
        for p in patches:
            p.stop()
    assert "[SDD-FSM][BLOCK]" in ctx
    assert "resume-from-escalation --to SPEC_DRAFTING" in ctx
    assert "session=s-old" in ctx
    assert "類別=context-budget" in ctx


def test_bootstrap_prints_measurement_source_line(tmp_path):
    import json as _json
    rt, patches = _isolated_runtime(tmp_path)
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(_json.dumps({"type": "assistant", "message": {
        "model": "claude-fable-5-1", "usage": {"input_tokens": 97184, "cache_creation_input_tokens": 0,
                                               "cache_read_input_tokens": 0}}}) + "\n", encoding="utf-8")
    for p in patches:
        p.start()
    try:
        rt.state.current = "SPEC_DRAFTING"
        mod = _load_hook()
        with_t = mod._build_context({"transcript_path": str(transcript)})["hookSpecificOutput"]["additionalContext"]
        without = mod._build_context({})["hookSpecificOutput"]["additionalContext"]
    finally:
        for p in patches:
            p.stop()
    assert "[SDD-CTX] 量測＝逐字稿 API usage；transcript_path=有；used=97,184；window=1,000,000（查表值" in with_t
    assert "transcript_path=無" in without
    assert "[SDD-FSM][BLOCK]" not in with_t


# ── R158 P3：DECISION-TRACE 呈現層陳舊紅字澄清（CrossPlatform R158 Q1/Q2 分析路徑 5）── round-label-ok
def test_decision_trace_shows_staleness_note_after_human_resume(tmp_path):
    """record_escalation 後經 `resume-from-escalation` 人工恢復回 SPEC_DRAFTING：
    最近 5 筆 trace 仍含 ESCALATION 字樣，但 current_state 已非阻斷態 ⇒ 必須印澄清句，
    且不得再印 [SDD-FSM][BLOCK]（那是真的被擋才印的橫幅，此刻不成立）。"""
    rt, patches = _isolated_runtime(tmp_path)
    for p in patches:
        p.start()
    try:
        rt.state.record_escalation("TOKEN_BUDGET_CRITICAL: cumulative=993581 ratio=0.99",
                                    details={"session_id": "s-old"})
        rt.resume_from_escalation(to="SPEC_DRAFTING", reason="human resume after context-budget escalation")
        mod = _load_hook()
        ctx = mod._build_context({})["hookSpecificOutput"]["additionalContext"]
    finally:
        for p in patches:
            p.stop()
    assert "ℹ️ 以下 DECISION-TRACE 為歷史紀錄" in ctx
    assert "current_state=SPEC_DRAFTING" in ctx
    assert "阻斷已於" in ctx and "解除" in ctx
    assert "python tools/session_resume_planner.py --check" in ctx
    assert "[SDD-FSM][BLOCK]" not in ctx


def test_decision_trace_omits_staleness_note_while_still_blocked(tmp_path):
    """current_state 仍在阻斷集合內（未人工恢復）：不應印澄清句——[SDD-FSM][BLOCK] 橫幅
    本身就是正確、即時的訊號，疊加澄清句反而互相矛盾。"""
    rt, patches = _isolated_runtime(tmp_path)
    for p in patches:
        p.start()
    try:
        rt.state.record_escalation("TOKEN_BUDGET_CRITICAL: cumulative=993581 ratio=0.99",
                                    details={"session_id": "s-old"})
        mod = _load_hook()
        ctx = mod._build_context({})["hookSpecificOutput"]["additionalContext"]
    finally:
        for p in patches:
            p.stop()
    assert "[SDD-FSM][BLOCK]" in ctx
    assert "ℹ️ 以下 DECISION-TRACE 為歷史紀錄" not in ctx


def test_decision_trace_staleness_note_pure_function_no_stale_hit():
    """`_decision_trace_staleness_note` 是純函式：current_state 不在阻斷集合、且最近 5
    筆 trace 也完全不含阻斷態字樣時，回 None（不應無中生有印澄清句）。"""
    mod = _load_hook()
    blocking = frozenset({"ESCALATION", "ESCALATION_FINAL", "TERMINATED", "TOKEN_BUDGET_CRITICAL"})
    trace = [{"ts": "2026-01-01T00:00:00+00:00", "from": "INIT", "to": "SPEC_DRAFTING",
              "trigger": "transition", "reason": "normal start"}]
    assert mod._decision_trace_staleness_note(trace, "SPEC_DRAFTING", blocking) is None


def test_decision_trace_staleness_note_guard_clause_blocks_while_still_blocking(tmp_path):
    """D（S1(d) 鑑別力補洞）：`test_decision_trace_omits_staleness_note_while_still_blocked`
    走 `_build_context()` 全流程，而 `record_escalation()` 本身不寫 `decision_trace`——於是
    該測試對 guard clause（`if current_state in blocking_states: return None`）零鑑別力：
    就算把 guard clause 整段砍掉，`_build_context()` 那條路徑上 `trace` 永遠是空的，
    `stale_hit` 恆為 False，函式一樣回 None，測試一樣綠。

    本測試直接呼叫純函式、餵一筆*非空*且 reason 含 `TOKEN_BUDGET_CRITICAL` 字樣的
    decision_trace，`current_state="ESCALATION"`（在 blocking_states 內）——guard clause
    健在時應立即回 None（阻斷態本身就是正確訊號，不疊加澄清句）；guard clause 被砍掉時
    會落入下方迴圈命中 `stale_hit=True` 而回傳非 None 字串，兩者可分辨。"""
    mod = _load_hook()
    blocking = frozenset({"ESCALATION", "ESCALATION_FINAL", "TERMINATED", "TOKEN_BUDGET_CRITICAL"})
    trace = [{"ts": "2026-01-01T00:00:00+00:00", "from": "SPEC_DRAFTING", "to": "ESCALATION",
              "trigger": "transition", "reason": "TOKEN_BUDGET_CRITICAL: cumulative=993581 ratio=0.99"}]
    assert mod._decision_trace_staleness_note(trace, "ESCALATION", blocking) is None


# ── DEF-200-454：AUTO_COMPACT_PENDING 殘留橫幅必須與 PreToolUse 的實際放行一致 ──────────────────
# WHY：PENDING 是**專案級**狀態，會跨視窗殘留；舊橫幅對任何新視窗一律寫「🔴 必須立即呼叫 Skill:
# stage-compaction」，但 PreToolUse 實際只對「owner（或查無 owner 記錄）且水位 ≥85%」的視窗限制
# 工具（D19／D-c）；首擊量不到 usage 放行並附 [UNMETERED]（D11）；水位 <85% 自動釋放（D4）。橫幅
# 說會被擋、行為卻放行，就是模型「新視窗一開就說自己被擋」的活樣本。本組測試把橫幅釘在行為上：
# parity 測試真的跑 `context_ledger_pre.main()`，橫幅寫「必須」若且唯若該 hook 對非 compact 工具 deny
# ——日後 D19／D11／D4 任一條語意被改，橫幅沒跟著改就會紅，而不是靜默再說一次假話。
_OWNER_SID = "ownr0001-aaaa-bbbb-cccc-000000000001"
_OTHER_SID = "othr0002-aaaa-bbbb-cccc-000000000002"
_MUST_COMPACT = "必須立即呼叫 Skill: stage-compaction"
_PINNED_WINDOW = 100_000  # SDD_MAX_CONTEXT 釘值：used／1000 即千分比，斷言不依賴 Models API 查表值


@contextlib.contextmanager
def _pending_runtime(tmp_path, *, owner_sid):
    """隔離 runtime ＋ 把 FSM 灌成 AUTO_COMPACT_PENDING；`owner_sid=None` ＝ 狀態檔查無 owner 記錄。

    除 `_isolated_runtime` 的隔離外，另把 SNAPSHOT_DIR／state_loader.REPO_ROOT 指到 tmp——parity 測試
    會真的跑 PreToolUse hook，其 D4 釋放分支會 `complete_auto_compact`（寫狀態與帳本），不隔離就會
    碰到 repo 真實的 build/ 目錄。分母以 SDD_MAX_CONTEXT 釘住（橫幅與 hook 讀同一份環境）。
    """
    import os
    from unittest.mock import patch
    import tools.fsm_runtime.snapshot as snap_mod
    import tools.fsm_runtime.state_loader as sl_mod

    rt, patches = _isolated_runtime(tmp_path)
    patches += [
        patch.object(snap_mod, "SNAPSHOT_DIR", tmp_path / "abort"),
        patch.object(sl_mod, "REPO_ROOT", tmp_path / "repo"),
        patch.dict(os.environ, {"SDD_MAX_CONTEXT": str(_PINNED_WINDOW)}),
    ]
    snapshot = tmp_path / "CONTEXT-SNAPSHOT-test.md"
    snapshot.write_text("snapshot", encoding="utf-8")  # 檔存在 ⇒ 不出「Snapshot 不存在」附註
    started = []
    try:
        for p in patches:
            p.start()
            started.append(p)
        rt.state.current = "AUTO_COMPACT_PENDING"
        auto = rt.state.root.setdefault("auto_compact_state", {})
        auto.update({"resume_state": "INIT", "snapshot_path": str(snapshot),
                     "triggered_at": "2026-09-10T01:17:04+00:00"})
        if owner_sid is not None:
            auto["pending_owner"] = {"session_id": owner_sid, "at": "2026-09-10T01:17:04+00:00",
                                     "transcript_path": None}
        yield rt
    finally:
        for p in reversed(started):
            p.stop()


def _usage_transcript(tmp_path, used, *, compacted_after=False):
    """單筆 assistant usage 的逐字稿；`compacted_after` ＝ compact_boundary 落在該筆 usage 之後
    （measure() 會判 stale_after_compact ⇒ used=None，即「剛 compact 完、尚無新 usage」）。"""
    import json
    lines = [json.dumps({"type": "assistant", "message": {"model": "claude-fable-5-1", "usage": {
        "input_tokens": used, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}}})]
    if compacted_after:
        lines.append(json.dumps({"type": "system", "subtype": "compact_boundary"}))
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _pending_banner_text(caller_sid, transcript=None):
    """SessionStart 注入內容中 `[SDD-FSM][AUTO-COMPACT]` 起的橫幅段（它是 warnings 區，位於最後）。"""
    payload = {"session_id": caller_sid}
    if transcript is not None:
        payload["transcript_path"] = str(transcript)
    ctx = _load_hook()._build_context(payload)["hookSpecificOutput"]["additionalContext"]
    assert "[SDD-FSM][AUTO-COMPACT]" in ctx, ctx
    return ctx[ctx.index("[SDD-FSM][AUTO-COMPACT]"):]


def _run_pre_hook(tmp_path, *, caller_sid, transcript=None):
    """真的跑 PreToolUse hook（`context_ledger_pre.main()`）對一個『非 compact 工具』（Edit src/app.py）
    的裁決，回 hookSpecificOutput——橫幅要對齊的行為真相源。"""
    import io
    import json
    import os
    import sys
    from unittest.mock import patch

    spec = importlib.util.spec_from_file_location("sdd_pre_hook_under_test", PRE_HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    mod.LEDGER_DIR = tmp_path / "ledger"
    payload = {"tool_name": "Edit", "session_id": caller_sid,
               "tool_input": {"file_path": "src/app.py", "old_string": "a", "new_string": "b"}}
    if transcript is not None:
        payload["transcript_path"] = str(transcript)

    class _Stdin(io.StringIO):
        def isatty(self) -> bool:
            return False

    out = io.StringIO()
    prior = os.environ.get("SDD_FSM_HOOK_ENTRY")
    try:
        with patch.object(sys, "stdin", _Stdin(json.dumps(payload))), patch.object(sys, "stdout", out):
            assert mod.main() == 0
    finally:
        # main() 以 setdefault 標記「這是 hook 行程」——不得外溢到同 session 其他測試。
        if prior is None:
            os.environ.pop("SDD_FSM_HOOK_ENTRY", None)
        else:
            os.environ["SDD_FSM_HOOK_ENTRY"] = prior
    raw = out.getvalue().strip()
    return json.loads(raw).get("hookSpecificOutput", {}) if raw else {}


def test_pending_banner_owner_over_threshold_keeps_must_compact_wording(tmp_path):
    """(i) owner 且實測 ≥85%：PreToolUse 真的只放行 compact 相關操作，「必須」語氣是真話，保留；
    並印出判斷依據（實測數字），讓讀者能自己核對「為什麼這次是真的」。"""
    with _pending_runtime(tmp_path, owner_sid=_OWNER_SID):
        banner = _pending_banner_text(_OWNER_SID, _usage_transcript(tmp_path, 90_000))
    assert _MUST_COMPACT in banner
    assert "PENDING owner" in banner
    assert "used=90,000" in banner and "90%" in banner


def test_pending_banner_legacy_state_without_owner_record_stays_conservative(tmp_path):
    """查無 owner 記錄（舊版狀態檔）且實測 ≥85%：`assert_tool_allowed` 保守 fail-closed 視同 owner、
    真的會擋——橫幅不能因為「不是已知 owner」就改口說不受限。"""
    with _pending_runtime(tmp_path, owner_sid=None):
        banner = _pending_banner_text(_OTHER_SID, _usage_transcript(tmp_path, 90_000))
    assert _MUST_COMPACT in banner
    assert "查無 owner 記錄" in banner


@pytest.mark.parametrize("used", [90_000, 40_000], ids=["other-window-high", "other-window-low"])
def test_pending_banner_other_window_says_pending_does_not_restrict_it(tmp_path, used):
    """(ii) PENDING 殘留來自他窗：本視窗不是 owner，D19 不套「只准 compact 工具」——不論本視窗水位
    高低，橫幅都不得叫它「必須立即 compaction」，也不得暗示工具會被 PENDING 擋。"""
    with _pending_runtime(tmp_path, owner_sid=_OWNER_SID):
        banner = _pending_banner_text(_OTHER_SID, _usage_transcript(tmp_path, used))
    assert "他窗" in banner and "owner=ownr0001" in banner
    assert "不是 owner" in banner and "工具照常放行" in banner
    assert "必須立即" not in banner
    assert _MUST_COMPACT not in banner


def test_pending_banner_unmetered_new_window_says_first_strike_passes(tmp_path):
    """(iii) 全新視窗首擊（payload 無 transcript_path ⇒ 量不到 usage）：D11 放行並附 [UNMETERED]，
    橫幅必須說「首擊放行、之後依實測水位決定」，不得說必須立即 compaction。"""
    with _pending_runtime(tmp_path, owner_sid=_OWNER_SID):
        banner = _pending_banner_text(_OTHER_SID)
    assert "尚無 usage 量測" in banner and "首擊放行" in banner and "UNMETERED" in banner
    assert "必須立即" not in banner
    assert _MUST_COMPACT not in banner


def test_pending_banner_unmetered_owner_right_after_its_own_compaction(tmp_path):
    """owner 自己剛 compact 完（逐字稿最後的 compact_boundary 在最後一筆 usage 之後 ⇒ used=None）：
    同樣是 D11 首擊放行，與是不是 owner 無關——量不到就不 gating，owner 也一樣。"""
    with _pending_runtime(tmp_path, owner_sid=_OWNER_SID):
        banner = _pending_banner_text(
            _OWNER_SID, _usage_transcript(tmp_path, 95_000, compacted_after=True))
    assert "尚無 usage 量測" in banner and "UNMETERED" in banner
    assert "必須立即" not in banner


def test_pending_banner_owner_below_threshold_says_auto_release(tmp_path):
    """owner（或查無 owner）且實測 <85%：D4 在第一次工具呼叫即自動釋放 PENDING，無須 stage-compaction
    ——舊橫幅對這一格也寫「必須立即」，同樣是假話。"""
    with _pending_runtime(tmp_path, owner_sid=_OWNER_SID):
        banner = _pending_banner_text(_OWNER_SID, _usage_transcript(tmp_path, 40_000))
    assert "自動釋放" in banner and "無須 stage-compaction" in banner
    assert "必須立即" not in banner


# parity 表：(owner 記錄, 本視窗 session_id, 本視窗 used［None＝量不到］, 該不該被 PENDING 擋)。
# 刻意不含「非 owner 且 ≥95%」：那是 session 級（本視窗自身水位）的 deny，與 PENDING 殘留無關，
# 橫幅對它只陳述規則（≥95% 起擋非 compact 工具），不歸在「PENDING 擋住你」的宣稱裡。
_PARITY_CASES = [
    pytest.param(_OWNER_SID, _OWNER_SID, 90_000, True, id="owner-high"),
    pytest.param(None, _OTHER_SID, 90_000, True, id="legacy-no-owner-record-high"),
    pytest.param(_OWNER_SID, _OTHER_SID, 90_000, False, id="other-window-high"),
    pytest.param(_OWNER_SID, _OTHER_SID, 40_000, False, id="other-window-low"),
    pytest.param(_OWNER_SID, _OWNER_SID, 40_000, False, id="owner-low"),
    pytest.param(_OWNER_SID, _OTHER_SID, None, False, id="other-window-unmetered"),
    pytest.param(_OWNER_SID, _OWNER_SID, None, False, id="owner-unmetered"),
]


@pytest.mark.parametrize("owner_sid, caller_sid, used, restricted", _PARITY_CASES)
def test_pending_banner_says_must_compact_iff_pre_hook_denies(
        tmp_path, owner_sid, caller_sid, used, restricted):
    """橫幅寫「必須立即 stage-compaction」若且唯若真的跑 PreToolUse hook 時它對非 compact 工具 deny
    （DEF-200-454）。兩個斷言：橫幅＝行為（防橫幅與行為再度脫鉤）、且都等於 `restricted`
    （把本表的預期也釘住，避免兩邊一起漂移時悄悄過關）。"""
    transcript = None if used is None else _usage_transcript(tmp_path, used)
    with _pending_runtime(tmp_path, owner_sid=owner_sid):
        banner = _pending_banner_text(caller_sid, transcript)
        verdict = _run_pre_hook(tmp_path, caller_sid=caller_sid, transcript=transcript)
    says_must = _MUST_COMPACT in banner
    denies = verdict.get("permissionDecision") == "deny"
    assert says_must == denies == restricted, (
        f"橫幅說必須={says_must}／PreToolUse deny={denies}／預期={restricted}\n"
        f"banner=\n{banner}\nverdict={verdict}")


def test_pending_banner_unknown_caller_is_fail_closed_like_assert_tool_allowed(tmp_path):
    """payload 沒帶 session_id（只有合成呼叫會這樣；真 hook 一律有）：`assert_tool_allowed(session_id=None)`
    保守 fail-closed 視同 owner 套限制。橫幅對這格不得改口說「不是 owner／不受限」——兩邊同一個保守方向，
    且要老實講「session id 不明」，不謊稱自己是 owner。"""
    from tools.fsm_runtime.transition_rules import TransitionError
    with _pending_runtime(tmp_path, owner_sid=_OWNER_SID) as rt:
        transcript = _usage_transcript(tmp_path, 90_000)
        ctx = _load_hook()._build_context({"transcript_path": str(transcript)}
                                          )["hookSpecificOutput"]["additionalContext"]
        with pytest.raises(TransitionError):
            rt.assert_tool_allowed("Edit", "src/app.py", session_id=None)
    banner = ctx[ctx.index("[SDD-FSM][AUTO-COMPACT]"):]
    assert _MUST_COMPACT in banner
    assert "session id 不明" in banner
    assert "為 PENDING owner" not in banner


def test_pending_banner_tolerates_dirty_owner_record(tmp_path):
    """髒資料（pending_owner 不是 dict、payload 的 session_id 不是字串）：橫幅只能老實印「不明」，
    不得拋例外——SessionStart 注入一旦崩潰，整份 FSM 狀態注入就蒸發（hook 的『never raises』承諾）。"""
    with _pending_runtime(tmp_path, owner_sid=None) as rt:
        rt.state.root["auto_compact_state"]["pending_owner"] = "oops-not-a-dict"
        ctx = _load_hook()._build_context({"session_id": 12345})["hookSpecificOutput"]["additionalContext"]
    assert "[SDD-FSM][AUTO-COMPACT]" in ctx
    assert "owner=不明" in ctx
