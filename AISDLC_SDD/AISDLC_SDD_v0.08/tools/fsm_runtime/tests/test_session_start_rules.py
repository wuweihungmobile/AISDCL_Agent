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
