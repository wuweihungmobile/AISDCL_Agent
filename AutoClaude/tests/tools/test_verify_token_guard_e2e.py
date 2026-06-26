"""verify_token_guard_e2e 載具單元測試（AutoSDD improving_84 W-84-2，C 軌）。

驗證端到端斷言邏輯（assert_compact_fired / assert_halt_fired）對「真觸發 / 未觸發」log
的判定，以及 fail-loud（log 缺席）與 CLI exit 碼。fixture log 取真實 Kernel marker 格式
（core/_token_compactor.py:58 TOKEN_COMPACT、core/kernel.py:304 TOKEN_HALT、KernelResult
repr 含 halted= / peak_token_pct=）。

🔴 Rule 9（測試驗證 intent 非 behavior）：核心是 test_no_trigger_*——「預設 80/90 門檻、
真跑未撞門檻」的 log（無 marker、halted=False）必須讓兩斷言**回 False**。這證明斷言不是
恆真的空殼：唯有編排真的觸發、marker/halted 真的出現，斷言才 PASS。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.ab_compare_backends import parse_run_metrics  # noqa: E402
from tools.verify_token_guard_e2e import (  # noqa: E402
    _load_log_or_raise,
    assert_compact_fired,
    assert_halt_fired,
    main,
)

# --- fixture log（真實 Kernel marker 格式）---------------------------------

# compact 觸發：TOKEN_COMPACT marker 出現、run 仍完成（halted=False）。
_COMPACT_FIRED = (
    "=== STATE: TOKEN_COMPACT | [S01] context 6% >= compact 門檻 ===\n"
    "Playbook 結束 | KernelResult(success=True, completed_steps=2, total_steps=2, "
    "reason='完成', step_log=['[S01] TDD First ✓ (attempt 1)', "
    "'[S02] 實作至綠 ✓ (attempt 1)'], completed_step_ids=['S01','S02'], "
    "peak_token_pct=6.2, halted=False, escalated=False)"
)

# halt 觸發：TOKEN_HALT marker 出現、KernelResult.halted=True（halt 先判，無 TOKEN_COMPACT）。
_HALT_FIRED = (
    "=== STATE: TOKEN_HALT | [S01] context 6% >= halt 門檻 ===\n"
    "Playbook 結束 | KernelResult(success=False, completed_steps=0, total_steps=2, "
    "reason='token halt', step_log=[], completed_step_ids=[], "
    "peak_token_pct=6.2, halted=True, escalated=False)"
)

# 未觸發（預設 80/90 門檻、真跑峰值 ~6% 未撞門檻）：無任何 marker、halted=False。
_NO_TRIGGER = (
    "Playbook 結束 | KernelResult(success=True, completed_steps=2, total_steps=2, "
    "reason='完成', step_log=['[S01] TDD First ✓ (attempt 1)', "
    "'[S02] 實作至綠 ✓ (attempt 1)'], completed_step_ids=['S01','S02'], "
    "peak_token_pct=6.2, halted=False, escalated=False)"
)


# --- assert_compact_fired -------------------------------------------------

def test_compact_fired_log_passes_compact_assert():
    ok, reason = assert_compact_fired(parse_run_metrics(_COMPACT_FIRED, "pty"))
    assert ok is True
    assert "已端到端觸發" in reason


def test_compact_fired_log_fails_halt_assert():
    """compact 觸發但未 halt → halt 斷言須回 False（交叉防誤報）。"""
    ok, _ = assert_halt_fired(parse_run_metrics(_COMPACT_FIRED, "pty"))
    assert ok is False


# --- assert_halt_fired ----------------------------------------------------

def test_halt_fired_log_passes_halt_assert():
    ok, reason = assert_halt_fired(parse_run_metrics(_HALT_FIRED, "pty"))
    assert ok is True
    assert "halted=True" in reason


def test_halt_fired_log_fails_compact_assert():
    """halt 先判 skip compact → 無 TOKEN_COMPACT → compact 斷言須回 False。"""
    ok, _ = assert_compact_fired(parse_run_metrics(_HALT_FIRED, "pty"))
    assert ok is False


# --- Rule 9：未觸發 log 必須讓兩斷言失敗（證明斷言非空殼）-------------------

def test_no_trigger_log_fails_compact_assert():
    ok, reason = assert_compact_fired(parse_run_metrics(_NO_TRIGGER, "pty"))
    assert ok is False
    assert "未觸發" in reason


def test_no_trigger_log_fails_halt_assert():
    ok, reason = assert_halt_fired(parse_run_metrics(_NO_TRIGGER, "pty"))
    assert ok is False
    assert "未觸發" in reason


# --- fail-loud：log 缺席 ---------------------------------------------------

def test_load_log_missing_raises(tmp_path):
    """RTM-84-4：log 不存在 → fail-loud（RuntimeError），不靜默回空字串騙過斷言。"""
    with pytest.raises(RuntimeError, match="log 檔不存在"):
        _load_log_or_raise(tmp_path / "nonexistent.log")


# --- CLI main exit 碼（--parse-log 離線模式）------------------------------

def _write(tmp_path: Path, name: str, text: str) -> str:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_main_parse_log_compact_pass_exit0(tmp_path):
    log = _write(tmp_path, "compact.log", _COMPACT_FIRED)
    assert main(["--parse-log", log, "--expect", "compact"]) == 0


def test_main_parse_log_compact_on_no_trigger_exit1(tmp_path):
    """未觸發 log 期待 compact → exit 1（fail-loud，CLI 層亦能失敗）。"""
    log = _write(tmp_path, "none.log", _NO_TRIGGER)
    assert main(["--parse-log", log, "--expect", "compact"]) == 1


def test_main_parse_log_halt_pass_exit0(tmp_path):
    log = _write(tmp_path, "halt.log", _HALT_FIRED)
    assert main(["--parse-log", log, "--expect", "halt"]) == 0


def test_main_parse_log_halt_on_no_trigger_exit1(tmp_path):
    log = _write(tmp_path, "none.log", _NO_TRIGGER)
    assert main(["--parse-log", log, "--expect", "halt"]) == 1


def test_main_parse_log_without_expect_returns2(tmp_path):
    log = _write(tmp_path, "x.log", _NO_TRIGGER)
    assert main(["--parse-log", log]) == 2


def test_main_no_args_returns2():
    assert main([]) == 2
