"""tools/ab_compare_backends.py 單元測試（AutoSDD improving_71 W-71-1/W-71-2）。

驗 pty/sdk A/B 載具的純 log 解析正確性。**不實跑引擎、不花 token**——以合成 log
（錨 production Kernel 真實輸出格式，取自 W-71-2 真跑 log）覆蓋四指標解析與邊界。

Rule 9：每測編碼「為何此指標如此計算」之意圖——
  - 完成/總步數權威源＝最終 KernelResult 行（非數 ✓ 標記，因 escalated 步不入 step_log、
    resume 時 completed 含先前步）；
  - first-pass＝step_log 內 ✓ (attempt 1)；
  - CORRECTION 次數＝Kernel W-71-2 新標記計數；
  - token 峰值＝TOKEN_COMPACT 行。
business logic 改變即應失敗。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.ab_compare_backends import (  # noqa: E402
    format_comparison,
    parse_run_metrics,
)

# 真實 Kernel 輸出格式（取自 W-71-2 真跑 log；前綴 timestamp/level 省略不影響 search）
_PERFECT = (
    "Playbook 結束 | KernelResult(success=True, completed_steps=2, total_steps=2, "
    "reason='完成', step_log=['[S01] TDD First ✓ (attempt 1)', "
    "'[S02] 實作至綠 ✓ (attempt 1)'], completed_step_ids=['S01','S02'], "
    "halted=False, escalated=False)"
)

_ONE_CORRECTION = (
    "=== STATE: CORRECTION | step=S01 attempt=1 ===\n"
    "Playbook 結束 | KernelResult(success=True, completed_steps=2, total_steps=2, "
    "reason='完成', step_log=['[S01] TDD First ✓ (attempt 2)', "
    "'[S02] 實作至綠 ✓ (attempt 1)'], completed_step_ids=['S01','S02'], "
    "halted=False, escalated=False)"
)

# W-71-2 真跑實況：S01 keyword 假通過但無建檔 → S02 evaluator 抓到 → escalated
_ESCALATED = (
    "Playbook 結束 | KernelResult(success=False, completed_steps=1, total_steps=2, "
    "reason='[S02] 評估指令失敗 (exit=4): pytest smoke_add_test.py -q', "
    "step_log=['[S01] TDD First ✓ (attempt 1)'], completed_step_ids=['S01'], "
    "halted=False, escalated=True)"
)


def test_perfect_run_all_first_pass():
    """全步驟 attempt 1 即過 → 一次通過率 1.0、CORRECTION 0、success/未 escalate。"""
    m = parse_run_metrics(_PERFECT, "pty")
    assert m.completed_steps == 2
    assert m.total_steps == 2
    assert m.first_pass_steps == 2
    assert m.first_pass_rate == 1.0
    assert m.correction_count == 0
    assert m.run_succeeded is True
    assert m.escalated is False


def test_correction_lowers_first_pass_rate():
    """一步 attempt 2 才過（經 1 次 CORRECTION）→ 一次通過率 0.5、CORRECTION 1。"""
    m = parse_run_metrics(_ONE_CORRECTION, "sdk")
    assert m.completed_steps == 2
    assert m.first_pass_steps == 1  # 只有 S02 是 attempt 1
    assert m.first_pass_rate == 0.5
    assert m.correction_count == 1


def test_escalated_run_completed_from_kernel_result():
    """escalated：完成步數取 KernelResult 權威值（1），run_succeeded False、escalated True。"""
    m = parse_run_metrics(_ESCALATED, "sdk")
    assert m.completed_steps == 1
    assert m.total_steps == 2
    assert m.first_pass_steps == 1
    assert m.run_succeeded is False
    assert m.escalated is True


def test_kernel_result_completed_is_authoritative_over_marks():
    """completed_steps 以 KernelResult 為權威——resume 時 completed 含先前步，
    可多於本 log 內 ✓ 標記數（防低估）。"""
    log = (
        "KernelResult(success=True, completed_steps=3, total_steps=3, "
        "step_log=['[S03] x ✓ (attempt 1)'], escalated=False, halted=False)"
    )
    m = parse_run_metrics(log)
    assert m.completed_steps == 3  # 權威值，非數 ✓（只 1 個）
    assert m.first_pass_steps == 1


def test_correction_count_multiple():
    """多次 CORRECTION 標記各計一次（諮詢 Minimax 次數＝對比指標）。"""
    log = (
        "=== STATE: CORRECTION | step=S01 attempt=1 ===\n"
        "=== STATE: CORRECTION | step=S01 attempt=2 ===\n"
        "=== STATE: CORRECTION | step=S02 attempt=1 ==="
    )
    assert parse_run_metrics(log).correction_count == 3


def test_sdd_violation_count():
    """SDD-VIOLATION[ 標記逐次計數（契約違反次數）。"""
    log = "SDD-VIOLATION[AT-01] foo\nok\nSDD-VIOLATION[AT-02] bar"
    assert parse_run_metrics(log).sdd_violation_count == 2


def test_peak_token_from_compact_line_takes_max():
    """token 峰值取 TOKEN_COMPACT 行的百分比最大值；非 compact 行的 % 不計入。"""
    log = (
        "Context 30% 一般訊息\n"  # 非 TOKEN_COMPACT → 不計
        "=== STATE: TOKEN_COMPACT | [S01] 85% >=  80% ===\n"
        "=== STATE: TOKEN_COMPACT | [S02] 91% >=  80% ==="
    )
    assert parse_run_metrics(log).peak_token_pct == 91.0


def test_no_token_compact_means_zero_peak():
    """低檔 run 未印 TOKEN_COMPACT → 峰值誠實回 0.0（非崩潰、非臆造）。"""
    assert parse_run_metrics(_PERFECT).peak_token_pct == 0.0


def test_empty_log_no_crash_rate_zero():
    """空 log → 無完成步驟 → 一次通過率 0.0（除零保護）、run 未成功。"""
    m = parse_run_metrics("")
    assert m.completed_steps == 0
    assert m.first_pass_rate == 0.0
    assert m.run_succeeded is False
    assert m.escalated is False


def test_format_comparison_has_both_backends_and_all_metrics():
    """對比表含 pty/sdk 兩欄與四指標標題（報告可讀性契約）。"""
    pty = parse_run_metrics(_PERFECT, "pty")
    sdk = parse_run_metrics(_ESCALATED, "sdk")
    out = format_comparison(pty, sdk)
    assert "| pty | sdk |" in out
    assert "一次通過率" in out
    assert "CORRECTION 次數" in out
    assert "SDD_CONTRACT_VIOLATION 次數" in out
    assert "token 峰值" in out


def test_log_file_roundtrip(tmp_path):
    """從 log 檔讀入解析（實跑後落地 utf-8 log → 解析路徑）。"""
    f = tmp_path / "pty.log"
    f.write_text(_PERFECT, encoding="utf-8")
    m = parse_run_metrics(f.read_text(encoding="utf-8"), "pty")
    assert m.first_pass_rate == 1.0
