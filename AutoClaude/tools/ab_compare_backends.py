"""pty vs sdk 後端 A/B 指標對比載具（AutoSDD improving_71 W-71-1/W-71-2，A 軌）。

純 log 解析：對同一 playbook 以 backend=pty / backend=sdk 各跑一次，從引擎 log 解析
四指標並輸出對比報告。**零行為變更**——只讀既有 log（含 improving_71 W-71-2 為 Kernel
路徑新增的 observability-only CORRECTION 標記），不改執行語意。

🔴 設計史（W-71-2 真跑揭露並訂正）：初版錨定 steps_orchestrator/_impl.py 的
`=== STATE: EXECUTE/EVALUATE ===` 標記，但那是**已棄用的 runner 路徑**；production
**Kernel（core/kernel.py）路徑不發那些標記**——成功標記 `✓ (attempt N)` 僅進 step_log，
最終以 `KernelResult(...)` repr 落 log。本版改錨 Kernel 真實輸出：
  - 最終 `KernelResult(success=.., completed_steps=N, total_steps=M, escalated=.., ...)` 行
  - step_log 內 `✓ (attempt N)`（→ 完成步數 / 一次通過）
  - `=== STATE: CORRECTION | step=.. attempt=.. ===`（W-71-2 為 Kernel 補的計數標記）
  - `SDD-VIOLATION[...]`、`TOKEN_COMPACT ... NN%`

四指標（對齊 AutoSDD_improving_01 §5.2 / DEF-01-007 驗收口徑）：
  first_pass_rate / correction_count / sdd_violation_count / peak_token_pct

成功完成後 checkpoint 會被清除（playbook_runner.py:429 / boot_helper.py），故指標一律
取自 log（非 checkpoint）。Windows console（cp950）會 mangle 中文/✓，故 run 模式改讀
引擎 utf-8 log 檔 `<workdir>/logs/autoclaude.log`，非擷取 stdout。

用法：
  python tools/ab_compare_backends.py --pty-log a.log --sdk-log b.log    # 解析（不花 token）
  python tools/ab_compare_backends.py --run smoke.yaml --workdir <tmp>   # 實跑（需授權 token）
"""
from __future__ import annotations

import argparse
import re
import statistics
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# --- Kernel 真實輸出標記（與 core/kernel.py 對齊）---
_RE_KERNEL_RESULT = re.compile(r"KernelResult\((.*)$")
_RE_SUCCESS_MARK = re.compile(r"✓\s*\(attempt\s*(\d+)\)")
_RE_CORRECTION = re.compile(r"STATE:\s*CORRECTION")
_RE_SDD_VIOLATION = re.compile(r"SDD-VIOLATION\[")
_RE_TOKEN_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
# W-76-1：per-step 歸因——自 TOKEN_COMPACT/✓ 行抽 `[Sxx]` 步驟 id；CORRECTION 行抽 `step=Sxx`。
# 生產碼鐵證：_impl.py:233 `[%s]`、kernel.py:185 `[{step_id}]`、kernel.py:224 `step=%s`。
_RE_STEP_TAG = re.compile(r"\[([A-Za-z0-9_\-]+)\]")
_RE_CORRECTION_STEP = re.compile(r"STATE:\s*CORRECTION\s*\|\s*step=([A-Za-z0-9_\-]+)")
_RE_FIELD_INT = {
    "completed_steps": re.compile(r"completed_steps=(\d+)"),
    "total_steps": re.compile(r"total_steps=(\d+)"),
}
# W-81-1 / DEF-81-001：observer 層真值——KernelResult 印的 peak_token_pct（kernel.py，
# TokenObserver 真跑全程測得的最高 context%）。與載具自掃 marker 行的 peak 是**不同來源**：
# 此為訊號源層（observer 收到的真值），marker 行 peak 為決策層（達門檻才印）。
# 判據（零歧義）：context% = used/max，observer 真在運作則 peak 必 > 0（即使 1%）；
# observer_peak == 0.0 嚴格意味 observer 從未收到任何可解析 token% 事件＝**訊號源未產出**
# （非「context 真的 0%」）。真跑探測實證 pty/sdk 雙 backend 皆 peak_token_pct=0.0。
_RE_FIELD_FLOAT = {
    "peak_token_pct": re.compile(r"peak_token_pct=(\d+(?:\.\d+)?)"),
}
_RE_FIELD_BOOL = {
    "success": re.compile(r"success=(True|False)"),
    "escalated": re.compile(r"escalated=(True|False)"),
    "halted": re.compile(r"halted=(True|False)"),
}


@dataclass
class StepMetrics:
    """單一步驟的成本/churn 指標（W-76-1，整輪指標的逐步驟拆分；純資料、無方法）。

    三維皆既有整輪指標的 per-step 拆分：壓縮次數 / token 峰值 / CORRECTION 次數。
    長 playbook 下整輪總和無法定位「哪步驟」驅動 pty/sdk 分歧，per-step 才分得出。
    """

    step_id: str = ""
    compact_count: int = 0
    peak_token_pct: float = 0.0
    correction_count: int = 0


@dataclass
class RunMetrics:
    """單一後端一次 run 的指標（純 log 解析，錨 Kernel 路徑輸出）。"""

    backend: str = ""
    completed_steps: int = 0
    total_steps: int = 0
    first_pass_steps: int = 0
    correction_count: int = 0
    sdd_violation_count: int = 0
    peak_token_pct: float = 0.0
    compact_count: int = 0
    run_succeeded: bool = False
    escalated: bool = False
    halted: bool = False
    # W-81-1 / DEF-81-001：observer 層真值（KernelResult.peak_token_pct）。預設 0.0＝真跑
    # 無訊號（fail-loud：與「context 真的 0%」區分，見 token_signal_observed property）。
    observer_peak_token_pct: float = 0.0
    # W-76-1：per-step 歸因（step_id → StepMetrics）。空 dict＝log 無步驟標記（誠實表「無 per-step 資訊」）。
    per_step: dict[str, "StepMetrics"] = field(default_factory=dict)

    @property
    def first_pass_rate(self) -> float:
        """一次通過率＝attempt 1 即成功的步驟 / 已完成步驟（無完成步驟回 0.0）。"""
        if self.completed_steps == 0:
            return 0.0
        return self.first_pass_steps / self.completed_steps

    @property
    def token_signal_observed(self) -> bool:
        """token% 訊號源本次 run 是否產出過任何值（W-81-1 / DEF-81-001 fail-loud 判據）。

        observer 層真值（KernelResult.peak_token_pct）或載具自掃 marker 行 % 任一 > 0
        即「有訊號」。皆 0 → False＝訊號源未產出（非「context 真的 0%」）：真跑探測實證
        pty（claude -p 不吐 context%）/sdk（get_context_usage 無 percentage 靜默跳過）雙
        backend 皆落此情形，compact/halt 在真實負載從未觸發。報告層據此 fail-loud 標記。
        """
        return self.observer_peak_token_pct > 0.0 or self.peak_token_pct > 0.0


def parse_run_metrics(log_text: str, backend: str = "") -> RunMetrics:
    """從一次 run 的引擎 log 文字解析指標（純函式，無副作用）。

    優先以最終 KernelResult 行取 completed/total/success/escalated（權威）；
    first-pass 由 step_log 的 `✓ (attempt N)` 推導；correction 由 CORRECTION 標記計數。
    """
    m = RunMetrics(backend=backend)
    m.correction_count = len(_RE_CORRECTION.findall(log_text))
    m.sdd_violation_count = len(_RE_SDD_VIOLATION.findall(log_text))

    # W-76-1：per-step CORRECTION 歸因（CORRECTION 行帶 `step=Sxx`）。
    # 整輪 correction_count 維持以 _RE_CORRECTION 計（語意不變）；per-step 以 step= 旁路歸因。
    # 🔴 誠實邊界（audit_76 SA-SD P1）：CORRECTION 有兩個 emit site——production 唯一正式路徑
    # Kernel `kernel.py:224` 帶 `step=`（W-71-2 為載具補；per-step 在真跑有效、不變式成立）；
    # 已棄用 PlaybookRunner 直連路徑 `_impl.py:437` 印 `諮詢 Minimax` **不帶 step=**。故 per-step
    # correction 對「不帶 step= 的 CORRECTION 行」不歸因＝**下界**（sum(per_step) ≤ 整輪），
    # 等號僅在 log 全為 Kernel 路徑（production 真跑）時成立。
    for sid in _RE_CORRECTION_STEP.findall(log_text):
        _step_of(m, sid).correction_count += 1

    # first-pass：step_log 內每個 ✓ (attempt N)；N==1 即一次通過
    attempts = [int(n) for n in _RE_SUCCESS_MARK.findall(log_text)]
    completed_from_marks = len(attempts)
    m.first_pass_steps = sum(1 for n in attempts if n == 1)

    # KernelResult 權威欄位（取最後一個 match）
    kr_blob = None
    for mt in _RE_KERNEL_RESULT.finditer(log_text):
        kr_blob = mt.group(1)
    if kr_blob is not None:
        for field, rgx in _RE_FIELD_INT.items():
            mm = rgx.search(kr_blob)
            if mm:
                setattr(m, field, int(mm.group(1)))
        bools = {}
        for field, rgx in _RE_FIELD_BOOL.items():
            mm = rgx.search(kr_blob)
            if mm:
                bools[field] = mm.group(1) == "True"
        m.run_succeeded = bools.get("success", False)
        m.escalated = bools.get("escalated", False)
        m.halted = bools.get("halted", False)  # DEF-75-001：修 dead-parse（原解析進 bools 卻丟棄）
        # W-81-1 / DEF-81-001：observer 層真值。KernelResult 欄名 peak_token_pct → 載具
        # observer_peak_token_pct（與載具自掃 marker 行的 m.peak_token_pct 是不同來源，勿覆寫）。
        # 無此欄 / 半途 log → 維持 0.0 = 無訊號（誠實）。
        mm_obs = _RE_FIELD_FLOAT["peak_token_pct"].search(kr_blob)
        if mm_obs:
            m.observer_peak_token_pct = float(mm_obs.group(1))
    # 無 KernelResult 行（半途 log）→ 退回以 ✓ 標記計完成步數
    if m.completed_steps == 0:
        m.completed_steps = completed_from_marks

    # token 峰值＋壓縮次數：掃 token 壓力標記行（達門檻才印），兩種 marker 皆認——
    #   TOKEN_COMPACT（≥80% 壓縮，`_impl.py:233`，帶 `[Sxx]`）+ TOKEN_HALT（≥90% halt，
    #   `plugins/checkpoint/_token_halt.py:46`，帶 `[Sxx] context NN%`）。
    #   peak = 行內 % 最大值（最高水位）；compact_count = TOKEN_COMPACT 行數（≥80% churn 次數，
    #   W-75-1 差異維度）——halt 不計入 compact_count（halt≠compact churn），但其 % 計入 peak。
    #   🔴 W-76-2 / DEF-76-001 / DEF-78-001：原僅認 TOKEN_COMPACT，但該 marker 只在**已棄用**
    #   `_impl.py` 路徑印；DEF-78-001 揭露 production Kernel 路徑原本根本沒接 token-guard 編排
    #   （compact/halt 全死碼），故 improving_71/75 的 peak/compact 在 production 真跑恆 0。
    #   ✅ improving_78 W-78-1 已為 production Kernel **halt** 路徑接線並補真誠 TOKEN_HALT marker
    #   （`core/kernel.py` `_consult_token_guard`，≥90% 真實 token% 觸發）→ halt 維度轉真值。
    #   ✅ improving_79 W-78-2 已為 production Kernel **compact** 路徑接線：≥80% 真實 token% →
    #   `_handle_compact` 經 `core/_token_compactor.perform_compact` 真送 /compact + 印真誠
    #   TOKEN_COMPACT marker（並接 Gap-008-E：連續失敗 2 次 → TOKEN_HALT）→ **compact 維度
    #   （compact_count / peak）此後在 production 真跑為真值**（本載具掃 TOKEN_COMPACT 即計入）。
    #   DEF-78-001 halt + compact 雙子路徑至此全接線、全閉合。
    #   未印→0/0 誠實表「無 token 壓力標記」（smoke playbook 過短不觸發門檻時為此情形）。
    peak = 0.0
    compact_count = 0
    for line in log_text.splitlines():
        is_compact = "TOKEN_COMPACT" in line
        is_halt = "TOKEN_HALT" in line
        if not (is_compact or is_halt):
            continue
        line_peak = 0.0
        for pct in _RE_TOKEN_PCT.findall(line):
            line_peak = max(line_peak, float(pct))
        peak = max(peak, line_peak)
        # W-76-1：per-step peak/compact 歸因（兩種 marker 皆帶 `[Sxx]`）。
        tag = _RE_STEP_TAG.search(line)
        sm = _step_of(m, tag.group(1)) if tag else None
        if is_compact:
            compact_count += 1
            if sm is not None:
                sm.compact_count += 1
        if sm is not None:
            sm.peak_token_pct = max(sm.peak_token_pct, line_peak)
    m.peak_token_pct = peak
    m.compact_count = compact_count
    return m


def _step_of(m: RunMetrics, step_id: str) -> StepMetrics:
    """取得（或建立）m.per_step 中該步驟的 StepMetrics（per-step 歸因 helper）。"""
    sm = m.per_step.get(step_id)
    if sm is None:
        sm = StepMetrics(step_id=step_id)
        m.per_step[step_id] = sm
    return sm


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def _fmt_token_peak(m: RunMetrics) -> str:
    """token 峰值渲染（W-81-1 / DEF-81-001 fail-loud）。

    訊號源未產出時不裸印 0%（會被誤讀為「context 真的 0%」），而標明訊號缺失。
    """
    if not m.token_signal_observed:
        return "0%（⚠ 訊號源未產出，非真值）"
    return f"{m.peak_token_pct:.0f}%"


def format_comparison(pty: RunMetrics, sdk: RunMetrics) -> str:
    """產出 Markdown 對比表（pty vs sdk 四指標 + 完成狀態）。"""
    rows = [
        ("一次通過率", _fmt_pct(pty.first_pass_rate), _fmt_pct(sdk.first_pass_rate)),
        ("CORRECTION 次數", str(pty.correction_count), str(sdk.correction_count)),
        ("SDD_CONTRACT_VIOLATION 次數",
         str(pty.sdd_violation_count), str(sdk.sdd_violation_count)),
        ("token 峰值", _fmt_token_peak(pty), _fmt_token_peak(sdk)),
        ("token 訊號源（W-81-1）",
         "已觀測" if pty.token_signal_observed else "未產出",
         "已觀測" if sdk.token_signal_observed else "未產出"),
        ("壓縮次數（compact）", str(pty.compact_count), str(sdk.compact_count)),
        ("完成步驟 / 總步驟",
         f"{pty.completed_steps}/{pty.total_steps}",
         f"{sdk.completed_steps}/{sdk.total_steps}"),
        ("run 成功 / escalated / halted",
         f"{pty.run_succeeded} / {pty.escalated} / {pty.halted}",
         f"{sdk.run_succeeded} / {sdk.escalated} / {sdk.halted}"),
    ]
    out = ["| 指標 | pty | sdk |", "|------|-----|-----|"]
    out += [f"| {name} | {a} | {b} |" for name, a, b in rows]
    return "\n".join(out)


# ── W-76-2：逐步驟 A/B 對比 + 有界渲染（improving_76，長 playbook 量測使能）──
def _step_cell(sm: StepMetrics | None) -> str:
    """單格＝「壓縮次數 / token 峰值 / CORRECTION 次數」。該後端此步無標記→0/0%/0（誠實補位）。"""
    if sm is None:
        return "0 / 0% / 0"
    return f"{sm.compact_count} / {sm.peak_token_pct:.0f}% / {sm.correction_count}"


def format_step_comparison(pty: RunMetrics, sdk: RunMetrics, max_steps: int = 30) -> str:
    """產出逐步驟 pty vs sdk 對比表（每格 compact/peak/correction），含有界截斷。

    步驟順序＝兩後端 step_id 聯集之穩定（lexical）排序；缺一邊的步驟以 0 補位（誠實表
    「該後端此步未留標記」）。**有界渲染（防彈渲染器）**：超過 max_steps 只印前 max_steps
    步 + `… (N more steps elided)` 一行，杜絕長 playbook（數十步）報告無限長/Token 爆炸。
    """
    step_ids = sorted(set(pty.per_step) | set(sdk.per_step))
    out = [
        "| 步驟 | pty (compact/peak/corr) | sdk (compact/peak/corr) |",
        "|------|------|------|",
    ]
    shown = step_ids[: max(0, max_steps)]
    for sid in shown:
        out.append(f"| {sid} | {_step_cell(pty.per_step.get(sid))} | {_step_cell(sdk.per_step.get(sid))} |")
    elided = len(step_ids) - len(shown)
    if elided > 0:
        out.append(f"| … | … ({elided} more steps elided) | … |")
    return "\n".join(out)


# ── W-72-2：多輪統計聚合（improving_72，完整統計 A/B）─────────────────
@dataclass
class AggregateMetrics:
    """同一後端 N 輪 run 的指標聚合（純統計，無副作用）。

    N=1 退化為單輪值（stdev=0）；N=0（空輸入）全回 0，誠實表「無樣本」。
    一次通過率取 mean/stdev/min/max；CORRECTION / SDD 違反取 mean + total；
    token 峰值取 mean/max；完成度以 success/escalated 計數 + completed_steps 均值表達。
    """

    backend: str = ""
    n: int = 0
    first_pass_rate_mean: float = 0.0
    first_pass_rate_stdev: float = 0.0
    first_pass_rate_min: float = 0.0
    first_pass_rate_max: float = 0.0
    correction_count_mean: float = 0.0
    correction_count_total: int = 0
    sdd_violation_count_total: int = 0
    peak_token_pct_mean: float = 0.0
    peak_token_pct_max: float = 0.0
    compact_count_mean: float = 0.0
    compact_count_total: int = 0
    compact_count_max: int = 0
    completed_steps_mean: float = 0.0
    total_steps: int = 0
    success_count: int = 0
    escalated_count: int = 0
    halted_count: int = 0
    # W-81-1 / DEF-81-001：N 輪中 token% 訊號源產出過的輪數（0＝多輪皆無訊號，報告 fail-loud）。
    token_signal_observed_count: int = 0
    per_run: list[RunMetrics] = field(default_factory=list)


def aggregate_runs(runs: list[RunMetrics], backend: str = "") -> AggregateMetrics:
    """把同一後端 N 輪 RunMetrics 聚合為統計指標（純函式）。

    空 list → n=0 全零（誠實表無樣本）。stdev 用母體標準差（pstdev，n=1→0.0）。
    backend 未指定時取首輪的 backend。
    """
    agg = AggregateMetrics(backend=backend or (runs[0].backend if runs else ""))
    agg.n = len(runs)
    if not runs:
        return agg
    fpr = [r.first_pass_rate for r in runs]
    corr = [r.correction_count for r in runs]
    tok = [r.peak_token_pct for r in runs]
    cmp_ = [r.compact_count for r in runs]
    comp = [r.completed_steps for r in runs]
    agg.first_pass_rate_mean = statistics.mean(fpr)
    agg.first_pass_rate_stdev = statistics.pstdev(fpr)  # n=1 → 0.0
    agg.first_pass_rate_min = min(fpr)
    agg.first_pass_rate_max = max(fpr)
    agg.correction_count_mean = statistics.mean(corr)
    agg.correction_count_total = sum(corr)
    agg.sdd_violation_count_total = sum(r.sdd_violation_count for r in runs)
    agg.peak_token_pct_mean = statistics.mean(tok)
    agg.peak_token_pct_max = max(tok)
    agg.compact_count_mean = statistics.mean(cmp_)   # 平均每輪壓縮次數（churn 代理）
    agg.compact_count_total = sum(cmp_)
    agg.compact_count_max = max(cmp_)                # 最壞單輪壓縮次數
    agg.completed_steps_mean = statistics.mean(comp)
    agg.total_steps = max(r.total_steps for r in runs)
    agg.success_count = sum(1 for r in runs if r.run_succeeded)
    agg.escalated_count = sum(1 for r in runs if r.escalated)
    agg.halted_count = sum(1 for r in runs if r.halted)  # 撞 ≥90% halt 的輪數（compact 孿生）
    # W-81-1 / DEF-81-001：訊號源產出輪數（0 → 報告標「N 輪皆無訊號」fail-loud）
    agg.token_signal_observed_count = sum(1 for r in runs if r.token_signal_observed)
    agg.per_run = list(runs)
    return agg


def format_aggregate_comparison(pty: AggregateMetrics, sdk: AggregateMetrics) -> str:
    """產出多輪統計 Markdown 對比表（pty vs sdk，含均值 ± 母體標準差 / 範圍 / 成功計數）。"""

    def _fpr(a: AggregateMetrics) -> str:
        return f"{_fmt_pct(a.first_pass_rate_mean)} ±{a.first_pass_rate_stdev * 100:.0f}% [{_fmt_pct(a.first_pass_rate_min)}~{_fmt_pct(a.first_pass_rate_max)}]"

    def _fmt_agg_token_peak(a: AggregateMetrics) -> str:
        # W-81-1 / DEF-81-001：N 輪皆無訊號 → 不裸印 0%，標明訊號缺失
        base = f"{a.peak_token_pct_mean:.0f}% / {a.peak_token_pct_max:.0f}%"
        if a.n > 0 and a.token_signal_observed_count == 0:
            return f"{base}（⚠ {a.n} 輪皆無訊號）"
        return base

    rows = [
        (f"樣本數 N", str(pty.n), str(sdk.n)),
        ("一次通過率 (mean ±stdev [min~max])", _fpr(pty), _fpr(sdk)),
        ("CORRECTION 次數 (mean / total)",
         f"{pty.correction_count_mean:.1f} / {pty.correction_count_total}",
         f"{sdk.correction_count_mean:.1f} / {sdk.correction_count_total}"),
        ("SDD_CONTRACT_VIOLATION (total)",
         str(pty.sdd_violation_count_total), str(sdk.sdd_violation_count_total)),
        ("token 峰值 (mean / max)",
         _fmt_agg_token_peak(pty), _fmt_agg_token_peak(sdk)),
        ("token 訊號源 (有訊號輪數 / N)",
         f"{pty.token_signal_observed_count} / {pty.n}",
         f"{sdk.token_signal_observed_count} / {sdk.n}"),
        ("壓縮次數 (mean / total / max)",
         f"{pty.compact_count_mean:.1f} / {pty.compact_count_total} / {pty.compact_count_max}",
         f"{sdk.compact_count_mean:.1f} / {sdk.compact_count_total} / {sdk.compact_count_max}"),
        ("完成步驟均值 / 總步驟",
         f"{pty.completed_steps_mean:.1f}/{pty.total_steps}",
         f"{sdk.completed_steps_mean:.1f}/{sdk.total_steps}"),
        ("run 成功 / escalated / halted (計數)",
         f"{pty.success_count} / {pty.escalated_count} / {pty.halted_count}",
         f"{sdk.success_count} / {sdk.escalated_count} / {sdk.halted_count}"),
    ]
    out = ["| 指標 | pty | sdk |", "|------|-----|-----|"]
    out += [f"| {name} | {a} | {b} |" for name, a, b in rows]
    return "\n".join(out)


# ── W-77-1：DEF-77-001 real-run 路徑 resolve + fail-loud（improving_77，A 軌）─────
def _resolve_invocation_path(path: str | None) -> str | None:
    """把 real-run 的 playbook / config 相對路徑對「呼叫端 cwd」resolve 成絕對字串。

    real-run 以子目錄為 subprocess cwd（run_backend），相對路徑會在子目錄解析失敗
    （DEF-77-001：傳 `scripts/x.yaml` 時 autoclaude 在 workdir 子目錄找不到 → 啟動即
    失敗未建 log → 解析成全 0 偽裝成功）。故須在 cwd 仍為使用者 cwd 時（main 解析 args
    後立即）先轉絕對。None 透傳（無 config 時）。resolve() 對已絕對路徑為冪等。
    """
    if path is None:
        return None
    return str(Path(path).resolve())


def _load_log_or_raise(log_file: Path, backend: str, returncode: int, stderr: str) -> str:
    """讀 real-run 引擎 log；log 不存在＝autoclaude 啟動即失敗 → fail loud（DEF-77-001）。

    舊版 log 不存在時回空字串 → `parse_run_metrics("")` 全 0 → 偽裝「成功的平淡 A/B」
    回 exit 0，把啟動失敗靜默吞掉（違反工程紀律第 12 條 Fail Loud）。本 helper 改為
    raise RuntimeError（含 backend/returncode/stderr 尾），使真跑失敗顯式可見。log 存在
    時（含 escalated/halted 輪本就有 log）照常回內容、解析語意與舊版完全一致。
    """
    if log_file.exists():
        return log_file.read_text(encoding="utf-8", errors="replace")
    tail = (stderr or "").strip()[-500:]
    raise RuntimeError(
        f"[{backend}] real-run 未產生引擎 log（{log_file}）；autoclaude 啟動即失敗"
        f"（returncode={returncode}）。請確認 playbook/config 路徑正確。stderr 尾段：{tail}"
    )


def run_backend(playbook: str, backend: str, workdir: Path, config_path: str | None = None) -> tuple[str, RunMetrics]:
    """以指定 backend 實跑 playbook（subprocess），回傳 (log_text, RunMetrics)。

    需授權 token：實際呼叫 Claude。讀引擎 utf-8 log 檔（非 stdout，避免 Windows cp950
    mangle）；backend 透過 config_path（executor.backend）切換，由呼叫端提供對應 config。
    🔴 playbook/config 須為絕對路徑（cwd=子目錄）——由 main 經 _resolve_invocation_path
    先轉絕對（DEF-77-001）。log 不存在即 fail loud，不再靜默回 0/0（DEF-77-001）。
    """
    workdir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "autoclaude", playbook, "--fresh"]
    if config_path:
        cmd += ["--config", config_path]
    proc = subprocess.run(cmd, cwd=str(workdir), capture_output=True, text=True, timeout=900)
    log_file = workdir / "logs" / "autoclaude.log"
    log_text = _load_log_or_raise(log_file, backend, proc.returncode, proc.stderr)
    return log_text, parse_run_metrics(log_text, backend=backend)


def run_backend_n(playbook: str, backend: str, base_workdir: Path, n: int,
                  config_path: str | None = None) -> tuple[list[str], list[RunMetrics]]:
    """以指定 backend 連跑 N 次（每輪獨立乾淨子目錄 run_1..run_N），回傳 (logs, metrics)。

    需授權 token：每輪實際呼叫 Claude。**每輪獨立子目錄**是必要的——smoke 會建檔
    （smoke_add_test.py / smoke_add.py），同目錄重跑會使 S01「先別建 smoke_add.py」前提
    被前一輪殘留檔破壞，污染 A/B。config_path 轉絕對路徑（subprocess cwd=子目錄）。
    """
    abs_pb = _resolve_invocation_path(playbook)        # DEF-77-001：playbook 亦須絕對
    abs_cfg = _resolve_invocation_path(config_path)    # 共用 resolve helper（單一路徑）
    logs: list[str] = []
    metrics: list[RunMetrics] = []
    for i in range(1, n + 1):
        run_dir = base_workdir / f"run_{i}"
        log_text, m = run_backend(abs_pb, backend, run_dir, abs_cfg)
        logs.append(log_text)
        metrics.append(m)
    return logs, metrics


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="pty vs sdk 後端 A/B 指標對比")
    p.add_argument("--pty-log", help="既有 pty run log 檔")
    p.add_argument("--sdk-log", help="既有 sdk run log 檔")
    p.add_argument("--run", help="實跑模式：playbook 路徑（需授權 token）")
    p.add_argument("--workdir", help="實跑工作目錄")
    p.add_argument("--pty-config", help="實跑模式：backend=pty 的 config")
    p.add_argument("--sdk-config", help="實跑模式：backend=sdk 的 config")
    p.add_argument("--n", type=int, default=1,
                   help="實跑模式：每後端連跑輪數（多輪統計 A/B；預設 1＝單輪對比）")
    p.add_argument("--max-steps", type=int, default=30,
                   help="逐步驟對比表有界渲染上限（超出截斷並印省略數；預設 30）")
    return p


def main(argv: list[str] | None = None) -> int:
    # DEF-82-001（improving_82 dogfooding 真跑揭露）：報表含 fail-loud「⚠」（W-81-1）/中文，
    # Windows cp950 console 直接 print 會 UnicodeEncodeError 中斷（真跑兩 backend 已跑完卻在
    # print 階段炸）。強制 stdout 走 utf-8（best-effort；非 TextIOWrapper / 不支援時靜默略過）。
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except (AttributeError, OSError):
        pass
    args = _build_argparser().parse_args(argv)
    if args.pty_log and args.sdk_log:
        pty = parse_run_metrics(Path(args.pty_log).read_text(encoding="utf-8", errors="replace"), "pty")
        sdk = parse_run_metrics(Path(args.sdk_log).read_text(encoding="utf-8", errors="replace"), "sdk")
        print(format_comparison(pty, sdk))
        print()
        print(format_step_comparison(pty, sdk, max_steps=args.max_steps))
    elif args.run and args.workdir:
        base = Path(args.workdir)
        n = max(1, args.n)
        # DEF-77-001：cwd 仍為使用者 cwd 時即把 playbook/config 轉絕對，避免子目錄解析失敗
        run_pb = _resolve_invocation_path(args.run)
        pty_cfg = _resolve_invocation_path(args.pty_config)
        sdk_cfg = _resolve_invocation_path(args.sdk_config)
        if n == 1:
            _, pty = run_backend(run_pb, "pty", base / "pty", pty_cfg)
            _, sdk = run_backend(run_pb, "sdk", base / "sdk", sdk_cfg)
            print(format_comparison(pty, sdk))
        else:
            _, pty_runs = run_backend_n(run_pb, "pty", base / "pty", n, pty_cfg)
            _, sdk_runs = run_backend_n(run_pb, "sdk", base / "sdk", n, sdk_cfg)
            print(format_aggregate_comparison(
                aggregate_runs(pty_runs, "pty"), aggregate_runs(sdk_runs, "sdk")))
    else:
        print("需提供 --pty-log+--sdk-log（解析）或 --run+--workdir（實跑）", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
