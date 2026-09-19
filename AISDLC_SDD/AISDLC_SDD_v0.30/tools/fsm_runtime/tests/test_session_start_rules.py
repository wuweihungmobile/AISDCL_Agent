"""Phase 2 (2a) — session_start.py 逐態揭露治理規則的接線測試。

驗證 rule_loader 已接進 session 生命週期（裁剪 CLAUDE.md 前的前置條件）：
當前 FSM 狀態命中的 R-*.yaml 會被注入 additionalContext。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parents[3]
HOOK = FRAMEWORK_ROOT / ".claude" / "hooks" / "session_start.py"


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
