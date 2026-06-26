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

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.ab_compare_backends import (  # noqa: E402
    _fmt_token_peak,
    _load_log_or_raise,
    _resolve_invocation_path,
    aggregate_runs,
    format_aggregate_comparison,
    format_comparison,
    format_step_comparison,
    main,
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


# ── W-72-2：多輪統計聚合測試（improving_72，完整統計 A/B）────────────
def test_aggregate_empty_is_zero_no_crash():
    """空輸入（無樣本）→ n=0 全零，誠實表「無樣本」而非崩潰或臆造。"""
    a = aggregate_runs([], "pty")
    assert a.n == 0
    assert a.first_pass_rate_mean == 0.0
    assert a.success_count == 0
    assert a.escalated_count == 0
    assert a.total_steps == 0
    # W-75（audit_75 SA-SD P1-2）：新指標在空輸入下亦須 default 0（不靠 max([]) 崩潰、不臆造）
    assert a.compact_count_total == 0
    assert a.halted_count == 0


def test_aggregate_single_run_degenerates_to_value_stdev_zero():
    """N=1：均值＝該輪值、母體 stdev=0（單樣本無離散），意圖：多輪載具退化到單輪不失真。"""
    a = aggregate_runs([parse_run_metrics(_PERFECT, "pty")], "pty")
    assert a.n == 1
    assert a.first_pass_rate_mean == 1.0
    assert a.first_pass_rate_stdev == 0.0
    assert a.first_pass_rate_min == 1.0
    assert a.first_pass_rate_max == 1.0
    assert a.success_count == 1
    assert a.escalated_count == 0


def test_aggregate_mean_stdev_range_across_runs():
    """N=2 混合（完美 + 半通過）→ 均值 0.75、min 0.5/max 1.0、母體 stdev=0.25。

    Rule 9：意圖＝多輪統計須真實反映輪間離散（一次通過率波動），非取首輪或末輪。
    """
    runs = [parse_run_metrics(_PERFECT, "sdk"),
            parse_run_metrics(_ONE_CORRECTION, "sdk")]
    a = aggregate_runs(runs, "sdk")
    assert a.n == 2
    assert a.first_pass_rate_mean == 0.75  # (1.0 + 0.5) / 2
    assert a.first_pass_rate_min == 0.5
    assert a.first_pass_rate_max == 1.0
    assert abs(a.first_pass_rate_stdev - 0.25) < 1e-9  # 母體 stdev of {1.0,0.5}
    assert a.correction_count_total == 1  # 僅 _ONE_CORRECTION 有 1 次
    assert a.correction_count_mean == 0.5


def test_aggregate_success_escalated_counts():
    """成功 / escalated 以輪計數（N=3：2 成功 + 1 escalated）——統計 A/B 的完成度口徑。"""
    runs = [parse_run_metrics(_PERFECT, "pty"),
            parse_run_metrics(_ONE_CORRECTION, "pty"),
            parse_run_metrics(_ESCALATED, "pty")]
    a = aggregate_runs(runs, "pty")
    assert a.n == 3
    assert a.success_count == 2
    assert a.escalated_count == 1
    assert a.total_steps == 2


def test_aggregate_backend_defaults_to_first_run():
    """backend 未指定時取首輪 backend（標籤不漏）。"""
    a = aggregate_runs([parse_run_metrics(_PERFECT, "sdk")])
    assert a.backend == "sdk"


def test_format_aggregate_has_both_backends_and_sample_size():
    """多輪對比表含 pty/sdk 兩欄、樣本數 N、均值±stdev 欄位（報告可讀性契約）。"""
    pty = aggregate_runs([parse_run_metrics(_PERFECT, "pty"),
                          parse_run_metrics(_ESCALATED, "pty")], "pty")
    sdk = aggregate_runs([parse_run_metrics(_PERFECT, "sdk")], "sdk")
    out = format_aggregate_comparison(pty, sdk)
    assert "| pty | sdk |" in out
    assert "樣本數 N" in out
    assert "mean" in out
    assert "run 成功 / escalated" in out


# ── improving_75 W-75：compaction-cost 量測補強 ───────────────────────
# 兩次壓縮的長 run（peak 達 91% 但壓了兩次→churn 高）；對照 _PERFECT（壓 0 次、peak 0）
# 可見：peak 飽和時，compact_count 才分得出 churn 成本差（W-75-1 設計意圖）。
_TWO_COMPACTS = (
    "=== STATE: TOKEN_COMPACT | [S01] 82% >=  80% ===\n"
    "=== STATE: TOKEN_COMPACT | [S02] 91% >=  80% ===\n"
    "Playbook 結束 | KernelResult(success=True, completed_steps=2, total_steps=2, "
    "step_log=['[S01] x ✓ (attempt 1)', '[S02] y ✓ (attempt 1)'], "
    "halted=False, escalated=False)"
)

# token 失控撞 ≥90% halt 門檻 → KernelResult halted=True（compact 的孿生升級訊號）
_HALTED = (
    "=== STATE: TOKEN_COMPACT | [S01] 85% >=  80% ===\n"
    "Playbook 結束 | KernelResult(success=False, completed_steps=1, total_steps=2, "
    "reason='token halt', step_log=['[S01] x ✓ (attempt 1)'], "
    "halted=True, escalated=False)"
)


def test_compact_count_counts_token_compact_lines():
    """W-75-1：compact_count＝TOKEN_COMPACT 行數（churn 次數）。

    Rule 9：peak 取最高水位（此處 91%），但「壓了幾次」才反映 token 重整成本——
    長 playbook 下兩後端可能 peak 同為 ~80% 卻壓縮次數天差地別，compact_count 才分得出。
    """
    m = parse_run_metrics(_TWO_COMPACTS, "pty")
    assert m.compact_count == 2
    assert m.peak_token_pct == 91.0  # peak 仍取最大值，與次數正交


def test_no_compact_means_zero_count():
    """未觸發壓縮的 run → compact_count 誠實回 0（非崩潰、非臆造），與 peak=0 對稱。"""
    m = parse_run_metrics(_PERFECT)
    assert m.compact_count == 0
    assert m.peak_token_pct == 0.0


def test_halted_parsed_from_kernel_result():
    """W-75-3（DEF-75-001）：halted=True 須寫回 RunMetrics.halted（修 dead-parse）。

    Rule 9：halt（≥90%）是比 compact（≥80%）更嚴重的 token 失控訊號（需 checkpoint 暫停），
    既有載具 regex 已解析卻丟棄；補回使 compaction 成本圖譜完整。
    """
    m = parse_run_metrics(_HALTED, "sdk")
    assert m.halted is True
    assert m.run_succeeded is False


def test_perfect_run_not_halted():
    """halted=False 的正常 run → m.halted is False（對稱守界，防把預設誤判為 True）。"""
    assert parse_run_metrics(_PERFECT).halted is False


def test_halted_absent_field_defaults_false():
    """W-75-3（audit_75 SA-SD P1-1）：KernelResult repr 完全無 `halted=` 子串時，
    `bools.get("halted", False)` 兜底回 False（不 KeyError、不誤判）——守舊版 log 相容。"""
    log = "KernelResult(success=True, completed_steps=1, total_steps=1)"
    assert parse_run_metrics(log).halted is False


def test_aggregate_compact_count_mean_total_max():
    """W-75-2：壓縮次數多輪聚合——mean（平均每輪）/ total（總和）/ max（最壞單輪）。

    Rule 9：N=2（壓 2 次 + 壓 0 次）→ mean 1.0 / total 2 / max 2，真實反映輪間 churn 離散，
    非取首輪或末輪。
    """
    runs = [parse_run_metrics(_TWO_COMPACTS, "pty"),
            parse_run_metrics(_PERFECT, "pty")]
    a = aggregate_runs(runs, "pty")
    assert a.compact_count_mean == 1.0  # (2 + 0) / 2
    assert a.compact_count_total == 2
    assert a.compact_count_max == 2


def test_aggregate_halted_count():
    """W-75-3：halted 以輪計數（對稱 success_count / escalated_count）。

    N=3（1 halted + 2 未 halt）→ halted_count == 1，統計 A/B 完成度口徑納入 token 失控輪。
    """
    runs = [parse_run_metrics(_HALTED, "pty"),
            parse_run_metrics(_PERFECT, "pty"),
            parse_run_metrics(_TWO_COMPACTS, "pty")]
    a = aggregate_runs(runs, "pty")
    assert a.halted_count == 1


def test_format_comparison_has_compact_and_halted():
    """單輪對比表含「壓縮次數」與 halted 標題（報告可讀性契約）。"""
    pty = parse_run_metrics(_TWO_COMPACTS, "pty")
    sdk = parse_run_metrics(_HALTED, "sdk")
    out = format_comparison(pty, sdk)
    assert "壓縮次數" in out
    assert "halted" in out


def test_format_aggregate_has_compact():
    """多輪對比表含「壓縮次數 (mean / total / max)」標題（報告可讀性契約）。"""
    pty = aggregate_runs([parse_run_metrics(_TWO_COMPACTS, "pty")], "pty")
    sdk = aggregate_runs([parse_run_metrics(_PERFECT, "sdk")], "sdk")
    out = format_aggregate_comparison(pty, sdk)
    assert "壓縮次數" in out
    assert "halted" in out


# ── improving_76 W-76：逐步驟（per-step）指標歸因 + 有界渲染 ─────────────
# 「長 playbook」合成 log：多步、逐步驟不同 compact/correction 樣態（錨 production
# 標記格式：TOKEN_COMPACT `[Sxx] NN%`、CORRECTION `step=Sxx`）。
# 意圖：整輪總和分不出「哪步驟」驅動成本，per-step 才定位得到。
_PER_STEP_LOG = (
    "=== STATE: TOKEN_COMPACT | [S01] 82% >=  80% ===\n"
    "=== STATE: CORRECTION | step=S01 attempt=1 ===\n"
    "=== STATE: TOKEN_COMPACT | [S02] 85% >=  80% ===\n"
    "=== STATE: TOKEN_COMPACT | [S02] 88% >=  80% ===\n"
    "=== STATE: CORRECTION | step=S02 attempt=1 ===\n"
    "=== STATE: CORRECTION | step=S02 attempt=2 ===\n"
    "Playbook 結束 | KernelResult(success=True, completed_steps=2, total_steps=2, "
    "step_log=['[S01] a ✓ (attempt 2)', '[S02] b ✓ (attempt 3)'], "
    "halted=False, escalated=False)"
)


def _long_log(n_steps: int) -> str:
    """n_steps 步、每步一次 TOKEN_COMPACT（[Sii] (80+i)%）的合成長 playbook log。"""
    lines = [
        f"=== STATE: TOKEN_COMPACT | [S{i:02d}] {80 + i}% >=  80% ==="
        for i in range(1, n_steps + 1)
    ]
    lines.append(
        f"Playbook 結束 | KernelResult(success=True, completed_steps={n_steps}, "
        f"total_steps={n_steps}, halted=False, escalated=False)"
    )
    return "\n".join(lines)


def test_per_step_compact_and_peak_attribution():
    """W-76-1：TOKEN_COMPACT 行的 `[Sxx]` 把壓縮次數/峰值歸到各步驟。

    Rule 9：意圖＝長 playbook 下「哪步驟壓最多次」才可行動——S02 壓 2 次 peak 88%、
    S01 壓 1 次 peak 82%，整輪總和（壓 3 次 peak 88%）看不出此分布。
    """
    m = parse_run_metrics(_PER_STEP_LOG, "pty")
    assert m.per_step["S01"].compact_count == 1
    assert m.per_step["S01"].peak_token_pct == 82.0
    assert m.per_step["S02"].compact_count == 2
    assert m.per_step["S02"].peak_token_pct == 88.0  # 取該步最高水位（非門檻 80）


def test_per_step_correction_attribution():
    """W-76-2：CORRECTION 行的 `step=Sxx` 把 CORRECTION 次數歸到各步驟。

    Rule 9：意圖＝定位「哪步驟最常被 Minimax CORRECTION」——S02 被 CORRECTION 2 次、
    S01 1 次；整輪 correction_count=3 看不出此分布。
    """
    m = parse_run_metrics(_PER_STEP_LOG, "sdk")
    assert m.per_step["S01"].correction_count == 1
    assert m.per_step["S02"].correction_count == 2


def test_per_step_sum_equals_whole_invariant():
    """W-76-3：per_step 為整輪總和的精確拆分——生產格式（每筆標記皆帶步驟 id）下，
    逐步驟和 == 整輪值（不變式，防 per-step 與整輪語意漂移）。"""
    m = parse_run_metrics(_PER_STEP_LOG, "pty")
    assert sum(s.compact_count for s in m.per_step.values()) == m.compact_count == 3
    assert sum(s.correction_count for s in m.per_step.values()) == m.correction_count == 3


def test_per_step_empty_when_no_markers():
    """無任何步驟標記的 run → per_step 為空 dict（誠實表「無 per-step 資訊」，非崩潰、非臆造）。"""
    m = parse_run_metrics(_PERFECT, "pty")  # _PERFECT 無 TOKEN_COMPACT/CORRECTION 標記
    assert m.per_step == {}


def test_format_step_comparison_shows_both_backends_and_steps():
    """逐步驟對比表含 pty/sdk 兩欄與步驟列（報告可讀性契約）。"""
    pty = parse_run_metrics(_PER_STEP_LOG, "pty")
    sdk = parse_run_metrics(_PER_STEP_LOG, "sdk")
    out = format_step_comparison(pty, sdk)
    assert "| 步驟 |" in out
    assert "pty (compact/peak/corr)" in out
    assert "| S01 |" in out
    assert "| S02 |" in out


def test_format_step_comparison_missing_step_zero_filled():
    """A/B 兩後端步驟集不同時，缺一邊的步驟以 `0 / 0% / 0` 補位（誠實表「此後端此步無標記」）。"""
    pty = parse_run_metrics(
        "=== STATE: TOKEN_COMPACT | [S01] 82% >=  80% ===", "pty")
    sdk = parse_run_metrics(
        "=== STATE: TOKEN_COMPACT | [S09] 91% >=  80% ===", "sdk")
    out = format_step_comparison(pty, sdk)
    lines = out.splitlines()
    s01 = next(ln for ln in lines if ln.startswith("| S01 |"))
    s09 = next(ln for ln in lines if ln.startswith("| S09 |"))
    assert s01.endswith("| 0 / 0% / 0 |")   # sdk 在 S01 無標記
    assert "| 0 / 0% / 0 |" in s09           # pty 在 S09 無標記


def test_format_step_comparison_bounded_truncation():
    """W-76-2（防彈渲染器）：步驟數超 max_steps → 只印前 max_steps 步 + 省略數一行，
    尾部步驟不出現（杜絕長 playbook 報告無限長/Token 爆炸）。

    Rule 9：意圖＝有界截斷必須真截斷——8 步 max_steps=5 → 含「(3 more steps elided)」、
    含 S05、不含 S06/S08；行數有界（不隨步數線性膨脹至全列）。
    """
    pty = parse_run_metrics(_long_log(8), "pty")
    sdk = parse_run_metrics(_long_log(8), "sdk")
    out = format_step_comparison(pty, sdk, max_steps=5)
    assert "(3 more steps elided)" in out
    assert "| S05 |" in out
    assert "| S06 |" not in out
    assert "| S08 |" not in out
    # 行數＝表頭 2 + 5 步 + 1 省略行 = 8（有界，不隨 8 步全列膨脹）
    assert len(out.splitlines()) == 8


def test_format_step_comparison_no_truncation_when_within_limit():
    """步驟數未超 max_steps → 全列顯示、無省略行（截斷僅在超限時觸發，不誤截）。"""
    pty = parse_run_metrics(_long_log(3), "pty")
    sdk = parse_run_metrics(_long_log(3), "sdk")
    out = format_step_comparison(pty, sdk, max_steps=30)
    assert "elided" not in out
    assert "| S03 |" in out


def test_format_step_comparison_max_steps_zero_all_elided():
    """W-76-3（audit_76 SA-SD P2）：max_steps=0 → 0 步列出 + 全進省略行，不崩潰（守 `max(0,..)` 負索引契約）。"""
    pty = parse_run_metrics(_long_log(3), "pty")
    sdk = parse_run_metrics(_long_log(3), "sdk")
    out = format_step_comparison(pty, sdk, max_steps=0)
    assert "(3 more steps elided)" in out
    assert "| S01 |" not in out
    assert len(out.splitlines()) == 3  # 表頭 2 + 省略行 1（有界，不崩潰）


def test_format_step_comparison_both_empty_header_only():
    """W-76-3（audit_76 SA-SD P3）：兩後端皆無 per-step 標記 → 純表頭、無資料列、無省略行
    （誠實表「無 per-step 資訊」，對齊 test_per_step_empty_when_no_markers 的渲染端對稱）。"""
    pty = parse_run_metrics(_PERFECT, "pty")  # _PERFECT 無 token/CORRECTION 標記
    sdk = parse_run_metrics(_PERFECT, "sdk")
    out = format_step_comparison(pty, sdk)
    assert "| 步驟 |" in out
    assert "elided" not in out
    assert len(out.splitlines()) == 2  # 純表頭，無資料列


# ── W-76-2 / DEF-76-001：載具納入 production token marker（TOKEN_HALT）─────────
# 🔴 production 唯一正式路徑＝Kernel（main.py:123），**不印 TOKEN_COMPACT**（只棄用 _impl.py:233 印）；
# Kernel 端 token 壓力以 TOKEN_HALT（≥90%，_token_halt.py:46，帶 [Sxx] context NN%）表達。
# 載具原僅認 TOKEN_COMPACT → production peak/compact 恆 0（DEF-76-001）。本輪納入 TOKEN_HALT。
_HALT_MARKER_LOG = (
    "=== STATE: TOKEN_HALT | [S03] context 92% >=  halt 門檻 90% ===\n"
    "Playbook 結束 | KernelResult(success=False, completed_steps=2, total_steps=3, "
    "halted=True, escalated=False)"
)

# CORRECTION 兩路徑混合：Kernel 帶 step=（kernel.py:224）+ 已棄用 _impl.py:437 不帶 step=
_MIXED_CORRECTION_LOG = (
    "=== STATE: CORRECTION | step=S01 attempt=1 ===\n"
    "=== STATE: CORRECTION | 諮詢 Minimax ===\n"
    "Playbook 結束 | KernelResult(success=True, completed_steps=1, total_steps=1, "
    "halted=False, escalated=False)"
)


def test_token_halt_marker_feeds_peak_and_per_step():
    """W-76-2（DEF-76-001）：TOKEN_HALT（production ≥90% marker）的 % 餵入 peak + per-step peak。

    Rule 9：意圖＝載具不能只認棄用路徑的 TOKEN_COMPACT——production Kernel 真跑發 TOKEN_HALT，
    若不解析則 peak 在真跑恆 0。peak 取行內最高（context 92%，非門檻 90%）；歸到 S03。
    halt≠compact churn → compact_count 不計入（仍 0），但 peak 反映 token 失控水位。
    """
    m = parse_run_metrics(_HALT_MARKER_LOG, "pty")
    assert m.peak_token_pct == 92.0           # TOKEN_HALT 行的 context %（非門檻 90）
    assert m.per_step["S03"].peak_token_pct == 92.0
    assert m.per_step["S03"].compact_count == 0  # halt 不計入 compact churn
    assert m.compact_count == 0                # 無 TOKEN_COMPACT 行
    assert m.halted is True


def test_per_step_correction_is_lower_bound_for_untagged():
    """W-76-1（audit_76 SA-SD P1）：CORRECTION 有兩 emit site——Kernel 帶 step=、已棄用
    _impl.py:437 不帶。per-step correction 對不帶 step= 者不歸因 → sum(per_step) ≤ 整輪（**下界**），
    等號僅在 log 全為 Kernel 路徑（production 真跑）時成立。誠實固化此邊界，防把「皆帶 step=」當全稱真理。"""
    m = parse_run_metrics(_MIXED_CORRECTION_LOG, "sdk")
    assert m.correction_count == 2  # _RE_CORRECTION 中兩行（含「諮詢 Minimax」）
    assert sum(s.correction_count for s in m.per_step.values()) == 1  # 僅 step=S01 歸因（下界）
    assert m.per_step["S01"].correction_count == 1


# ── W-77-1 / DEF-77-001：real-run 路徑 resolve + fail-loud（improving_77，A 軌）─────
def test_resolve_invocation_path_relative_becomes_absolute():
    """RTM-77-1：相對路徑對呼叫端 cwd resolve 成絕對。

    Rule 9：意圖＝real-run 以子目錄為 subprocess cwd，相對 playbook/config 會在子目錄
    解析失敗 → autoclaude 啟動即失敗 → 靜默 0/0（DEF-77-001 原貌）。故 main 須在 cwd 仍為
    使用者 cwd 時先轉絕對。若此函式退化回原樣傳遞，相對路徑真跑會重現 DEF-77-001。
    """
    abs_p = _resolve_invocation_path("scripts/sdd_bridge_smoke.yaml")
    assert abs_p is not None
    assert Path(abs_p).is_absolute()
    assert Path(abs_p).name == "sdd_bridge_smoke.yaml"


def test_resolve_invocation_path_none_passes_through():
    """RTM-77-1：無 config 時 None 透傳（不誤轉成 cwd 的絕對路徑）。"""
    assert _resolve_invocation_path(None) is None


def test_resolve_invocation_path_absolute_is_idempotent(tmp_path):
    """RTM-77-1：已絕對路徑 resolve 冪等（main 轉一次 + run_backend_n 再轉一次不出錯）。"""
    p = str(tmp_path / "x.yaml")
    once = _resolve_invocation_path(p)
    assert Path(once).is_absolute()
    assert _resolve_invocation_path(once) == once  # 冪等


def test_load_log_missing_raises_fail_loud(tmp_path):
    """RTM-77-2：log 不存在＝autoclaude 啟動即失敗 → raise，不再靜默回空字串。

    Rule 9：意圖＝Fail Loud（工程紀律第 12 條）。DEF-77-001 原貌＝log 缺失時回 ""→
    parse_run_metrics("") 全 0 → 偽裝「成功的平淡 A/B」回 exit 0。若此函式退化回 return ""，
    使用者會拿到假的全 0 報告而不知真跑根本沒跑。raise 訊息須含 backend/returncode/stderr 以利診斷。
    """
    missing = tmp_path / "logs" / "autoclaude.log"
    with pytest.raises(RuntimeError) as ei:
        _load_log_or_raise(missing, "pty", returncode=2, stderr="playbook 不存在：找不到檔案")
    msg = str(ei.value)
    assert "pty" in msg
    assert "returncode=2" in msg
    assert "找不到檔案" in msg  # stderr 尾段被帶出（可診斷）


def test_load_log_existing_returns_content_unchanged(tmp_path):
    """RTM-77-3：log 存在時照常回內容、語意與舊版完全一致（含 escalated 輪本就有 log，不誤 raise）。"""
    log_file = tmp_path / "logs" / "autoclaude.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text(_ESCALATED, encoding="utf-8")
    out = _load_log_or_raise(log_file, "sdk", returncode=1, stderr="")
    assert out == _ESCALATED
    # 解析語意不變：escalated 輪（returncode≠0 但有 log）照常解析、不誤 raise
    m = parse_run_metrics(out, "sdk")
    assert m.escalated is True
    assert m.run_succeeded is False


# ── W-81-1 / DEF-81-001：真跑 token% 訊號源 fail-loud 護欄 ─────────────────
# 真跑探測實證：pty（claude -p 不吐 context%）/sdk（get_context_usage 無 percentage）
# 雙 backend 真跑 KernelResult 皆 peak_token_pct=0.0、無 TOKEN_COMPACT/HALT marker。
# 護欄須在報告層區分「訊號源未產出」vs「context 真的 0%」，杜絕下輪誤宣稱取到真值。

# production KernelResult 含 observer 真值 peak_token_pct（真跑探測實況：恆 0.0）。
_REALRUN_NO_SIGNAL = (
    "INFO autoclaude: 執行器後端：Claude Agent SDK\n"
    "Playbook 結束 | KernelResult(success=True, completed_steps=2, total_steps=2, "
    "reason='success', step_log=['[S01] x ✓ (attempt 1)', '[S02] y ✓ (attempt 1)'], "
    "completed_step_ids=['S01','S02'], halted=False, escalated=False, "
    "halt_step_idx=None, peak_token_pct=0.0)"
)
# 假想「訊號源已修復」：observer 測得非 0（未達 80% compact 門檻、無 marker）。
_REALRUN_OBSERVER_SIGNAL = (
    "Playbook 結束 | KernelResult(success=True, completed_steps=2, total_steps=2, "
    "step_log=['[S01] x ✓ (attempt 1)'], halted=False, escalated=False, "
    "peak_token_pct=12.5)"
)


def test_rtm_81_1_parse_observer_peak_from_kernel_result():
    """RTM-81-1：自 KernelResult 解析 observer 層 peak_token_pct → observer_peak_token_pct，
    且不覆寫載具自掃 marker 行的 peak_token_pct（兩者不同來源）。"""
    m = parse_run_metrics(_REALRUN_OBSERVER_SIGNAL, "sdk")
    assert m.observer_peak_token_pct == 12.5
    assert m.peak_token_pct == 0.0  # 無 marker 行 → 載具掃出的 peak 仍 0，未被 observer 值汙染


def test_rtm_81_1_no_kernel_result_observer_peak_zero():
    """RTM-81-1：半途 log 無 KernelResult 行 → observer_peak_token_pct 維持 0.0（誠實，不臆造）。"""
    m = parse_run_metrics("=== STATE: CORRECTION | step=S01 attempt=1 ===", "pty")
    assert m.observer_peak_token_pct == 0.0


def test_rtm_81_2_signal_absent_when_both_zero():
    """RTM-81-2：observer 真值 0 且無 marker → token_signal_observed False（訊號源未產出）。
    意圖＝這正是真跑探測的真實情形，必須與「context 真的 0%」區分。"""
    m = parse_run_metrics(_REALRUN_NO_SIGNAL, "sdk")
    assert m.observer_peak_token_pct == 0.0
    assert m.peak_token_pct == 0.0
    assert m.token_signal_observed is False


def test_rtm_81_2_signal_present_via_observer():
    """RTM-81-2：observer 真值 > 0（即使未達門檻、無 marker）→ signal_observed True。"""
    m = parse_run_metrics(_REALRUN_OBSERVER_SIGNAL, "sdk")
    assert m.token_signal_observed is True


def test_rtm_81_2_signal_present_via_marker():
    """RTM-81-2：有 TOKEN_COMPACT marker（達門檻）→ 即使無 observer 欄位也 signal True。"""
    log = "=== STATE: TOKEN_COMPACT | [S01] 85% >= 80% ==="
    m = parse_run_metrics(log, "pty")
    assert m.peak_token_pct == 85.0
    assert m.token_signal_observed is True


def test_rtm_81_3_format_flags_absent_signal():
    """RTM-81-3：單輪報告——訊號源未產出時 token 峰值標「⚠ 訊號源未產出」+ 訊號源狀態列。"""
    pty = parse_run_metrics(_REALRUN_NO_SIGNAL, "pty")
    sdk = parse_run_metrics(_REALRUN_NO_SIGNAL, "sdk")
    out = format_comparison(pty, sdk)
    assert "訊號源未產出" in out
    assert "token 訊號源" in out
    assert "未產出" in out


def test_rtm_81_3_format_unchanged_when_signal_present():
    """RTM-81-3 零退化：有訊號（marker 85%）→ token 峰值照常渲染 85%、不標警示。"""
    log = "=== STATE: TOKEN_COMPACT | [S01] 85% >= 80% ===\n" + _PERFECT
    m = parse_run_metrics(log, "pty")
    out = format_comparison(m, m)
    assert "85%" in out
    assert "訊號源未產出" not in out
    assert "已觀測" in out  # 訊號源狀態列標「已觀測」


def test_rtm_81_4_aggregate_signal_count():
    """RTM-81-4：aggregate_runs 聚合 token_signal_observed_count（多輪中有訊號的輪數）。"""
    runs = [
        parse_run_metrics(_REALRUN_NO_SIGNAL, "sdk"),       # 無訊號
        parse_run_metrics(_REALRUN_OBSERVER_SIGNAL, "sdk"),  # 有訊號
    ]
    a = aggregate_runs(runs, "sdk")
    assert a.token_signal_observed_count == 1
    assert a.n == 2


def test_rtm_81_4_aggregate_format_flags_all_absent():
    """RTM-81-4：多輪皆無訊號 → 多輪報告 token 峰值列標「N 輪皆無訊號」。"""
    runs = [parse_run_metrics(_REALRUN_NO_SIGNAL, "sdk") for _ in range(3)]
    pty = aggregate_runs([parse_run_metrics(_REALRUN_NO_SIGNAL, "pty")], "pty")
    sdk = aggregate_runs(runs, "sdk")
    out = format_aggregate_comparison(pty, sdk)
    assert "輪皆無訊號" in out
    assert "token 訊號源" in out


# ── DEF-82-001：報表 fail-loud ⚠ 在 Windows cp950 console print 不炸（improving_82 dogfooding）──
def test_main_parse_mode_renders_failloud_on_cp950_stdout(tmp_path, monkeypatch):
    """DEF-82-001：format 含 fail-loud「⚠」（W-81-1），模擬 cp950 console stdout，
    main 應先 reconfigure utf-8 → 正常 print 不拋 UnicodeEncodeError。

    驗證意圖（Rule 9）：守的是「真跑兩 backend 跑完卻在 print 階段炸」這個觀測缺陷的修復——
    fake stdout 用 cp950 編碼（⚠ 不可編碼）；若移除 main 開頭 reconfigure，print ⚠ 即
    UnicodeEncodeError 紅。peak_token_pct=0.0 + 無 marker → token_signal_observed False → 渲染 ⚠。"""
    import io

    kr = ("Playbook 結束 | KernelResult(success=True, completed_steps=2, total_steps=2, "
          "reason='ok', completed_step_ids=['S01','S02'], halted=False, escalated=False, "
          "peak_token_pct=0.0)\n")
    pty_log = tmp_path / "pty.log"
    sdk_log = tmp_path / "sdk.log"
    pty_log.write_text(kr, encoding="utf-8")
    sdk_log.write_text(kr, encoding="utf-8")

    fake = io.TextIOWrapper(io.BytesIO(), encoding="cp950")  # 模擬 Windows console
    monkeypatch.setattr(sys, "stdout", fake)

    rc = main(["--pty-log", str(pty_log), "--sdk-log", str(sdk_log)])
    assert rc == 0
    fake.flush()
    rendered = fake.buffer.getvalue().decode("utf-8")
    assert "訊號源未產出" in rendered  # fail-loud ⚠ 報表確實輸出（utf-8 後）


# ── W-83-1 / DEF-83-001：載具「token 峰值」報 observer 真實峰值（非 marker-only 盲報）──
# 真跑鐵證：smoke 雙 backend KernelResult.peak_token_pct=6.2006(pty)/2.0(sdk)、未撞門檻無
# marker → observer>0 但 marker=0。修前 _fmt_token_peak 印 marker（0%）與「已觀測」矛盾、
# 藏掉真實 A/B token 差異。修後改報 effective=max(observer,marker)。
# 真跑 KernelResult（observer peak=2.0，無任何 TOKEN_COMPACT/HALT marker）——複現 SDK 真跑情形。
_REALRUN_SDK_PEAK_2 = (
    "INFO autoclaude: 執行器後端：Claude Agent SDK\n"
    "Playbook 結束 | KernelResult(success=True, completed_steps=2, total_steps=2, "
    "reason='success', step_log=['[S01] x ✓ (attempt 1)', '[S02] y ✓ (attempt 1)'], "
    "completed_step_ids=['S01','S02'], halted=False, escalated=False, "
    "halt_step_idx=None, peak_token_pct=2.0)"
)


def test_effective_peak_is_max_of_observer_and_marker():
    """RTM-83-4：effective_peak_token_pct = max(observer, marker)。意圖＝真實峰值須涵蓋
    訊號層 observer 與決策層 marker 兩來源，任一改動（去 observer / 去 marker / 改 min）皆破壞。"""
    m = parse_run_metrics(_REALRUN_OBSERVER_SIGNAL, "sdk")  # observer 12.5, marker 0
    assert m.observer_peak_token_pct == 12.5
    assert m.peak_token_pct == 0.0
    assert m.effective_peak_token_pct == 12.5  # max(12.5, 0)


def test_def_83_001_observer_peak_shown_when_no_marker():
    """RTM-83-1（DEF-83-001 核心）：observer>0 且無 marker → 「token 峰值」報 observer 真值
    （12%），非盲報 0%。修前印 m.peak_token_pct=0 → '0%'；修後印 effective=12.5 → '12%'。"""
    m = parse_run_metrics(_REALRUN_OBSERVER_SIGNAL, "sdk")
    cell = _fmt_token_peak(m)
    assert cell == "12%"  # round(12.5)→12（.0f）
    assert cell != "0%"


def test_def_83_001_marker_peak_shown_when_no_observer():
    """RTM-83-2 零退化：observer=0 且 marker>0（既有語意）→ 報 marker 值（85%）。
    effective=max(0,85)=85 → 顯示不變，保住 W-81-1 既有行為。"""
    log = "=== STATE: TOKEN_COMPACT | [S01] 85% >= 80% ===\n" + _PERFECT
    m = parse_run_metrics(log, "pty")
    assert m.observer_peak_token_pct == 0.0
    assert m.peak_token_pct == 85.0
    assert _fmt_token_peak(m) == "85%"


def test_def_83_001_effective_peak_takes_max():
    """RTM-83-3：observer>0 且 marker>0 → 報兩者最大（marker 91 > observer 12.5 → 91%）。
    意圖＝改 max→min 即紅。"""
    log = (
        "=== STATE: TOKEN_HALT | [S01] context 91% >= 90% ===\n"
        "Playbook 結束 | KernelResult(success=True, completed_steps=1, total_steps=1, "
        "halted=True, escalated=False, peak_token_pct=12.5)"
    )
    m = parse_run_metrics(log, "pty")
    assert m.observer_peak_token_pct == 12.5
    assert m.peak_token_pct == 91.0
    assert m.effective_peak_token_pct == 91.0
    assert _fmt_token_peak(m) == "91%"


def test_def_83_001_realrun_kernelresult_peak_rendered():
    """RTM-83-5（真跑錨定）：複現 SDK 真跑（KernelResult peak=2.0、無 marker），
    format_comparison 的 token 峰值列須顯示 2%，非 0%、非「訊號源未產出」。
    這正是本輪真跑揭露的盲報缺陷之回歸鎖。"""
    sdk = parse_run_metrics(_REALRUN_SDK_PEAK_2, "sdk")
    pty = parse_run_metrics(_REALRUN_SDK_PEAK_2, "pty")
    out = format_comparison(pty, sdk)
    assert "2%" in out
    assert "訊號源未產出" not in out  # 訊號已觀測（peak=2.0>0）
    assert "已觀測" in out


def test_def_83_001_aggregate_effective_peak():
    """RTM-83-6：aggregate 以 effective（observer 真值）聚合；多輪 format 不藏真值。
    兩輪 observer peak=12.5（無 marker）→ effective mean/max=12.5 → 報 12%，非 0%。"""
    runs = [parse_run_metrics(_REALRUN_OBSERVER_SIGNAL, "sdk") for _ in range(2)]
    a = aggregate_runs(runs, "sdk")
    assert a.effective_peak_token_pct_mean == 12.5
    assert a.effective_peak_token_pct_max == 12.5
    pty = aggregate_runs([parse_run_metrics(_REALRUN_NO_SIGNAL, "pty")], "pty")
    out = format_aggregate_comparison(pty, a)
    assert "12%" in out  # sdk 真實峰值現身，非 marker-only 的 0%
