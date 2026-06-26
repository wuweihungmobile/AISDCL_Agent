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
_RE_FIELD_INT = {
    "completed_steps": re.compile(r"completed_steps=(\d+)"),
    "total_steps": re.compile(r"total_steps=(\d+)"),
}
_RE_FIELD_BOOL = {
    "success": re.compile(r"success=(True|False)"),
    "escalated": re.compile(r"escalated=(True|False)"),
    "halted": re.compile(r"halted=(True|False)"),
}


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

    @property
    def first_pass_rate(self) -> float:
        """一次通過率＝attempt 1 即成功的步驟 / 已完成步驟（無完成步驟回 0.0）。"""
        if self.completed_steps == 0:
            return 0.0
        return self.first_pass_steps / self.completed_steps


def parse_run_metrics(log_text: str, backend: str = "") -> RunMetrics:
    """從一次 run 的引擎 log 文字解析指標（純函式，無副作用）。

    優先以最終 KernelResult 行取 completed/total/success/escalated（權威）；
    first-pass 由 step_log 的 `✓ (attempt N)` 推導；correction 由 CORRECTION 標記計數。
    """
    m = RunMetrics(backend=backend)
    m.correction_count = len(_RE_CORRECTION.findall(log_text))
    m.sdd_violation_count = len(_RE_SDD_VIOLATION.findall(log_text))

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
    # 無 KernelResult 行（半途 log）→ 退回以 ✓ 標記計完成步數
    if m.completed_steps == 0:
        m.completed_steps = completed_from_marks

    # token 峰值＋壓縮次數：掃 TOKEN_COMPACT 行（達門檻才印）。
    #   peak = 行內 % 最大值（最高水位）；compact_count = 行數（churn 次數，W-75-1 差異維度——
    #   兩後端撞同一門檻時 peak 雙雙飽和分不出，壓縮次數才反映重整成本差）。未印→0/0 誠實表「無壓縮」。
    peak = 0.0
    compact_count = 0
    for line in log_text.splitlines():
        if "TOKEN_COMPACT" not in line:
            continue
        compact_count += 1
        for pct in _RE_TOKEN_PCT.findall(line):
            peak = max(peak, float(pct))
    m.peak_token_pct = peak
    m.compact_count = compact_count
    return m


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def format_comparison(pty: RunMetrics, sdk: RunMetrics) -> str:
    """產出 Markdown 對比表（pty vs sdk 四指標 + 完成狀態）。"""
    rows = [
        ("一次通過率", _fmt_pct(pty.first_pass_rate), _fmt_pct(sdk.first_pass_rate)),
        ("CORRECTION 次數", str(pty.correction_count), str(sdk.correction_count)),
        ("SDD_CONTRACT_VIOLATION 次數",
         str(pty.sdd_violation_count), str(sdk.sdd_violation_count)),
        ("token 峰值", f"{pty.peak_token_pct:.0f}%", f"{sdk.peak_token_pct:.0f}%"),
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
    agg.per_run = list(runs)
    return agg


def format_aggregate_comparison(pty: AggregateMetrics, sdk: AggregateMetrics) -> str:
    """產出多輪統計 Markdown 對比表（pty vs sdk，含均值 ± 母體標準差 / 範圍 / 成功計數）。"""

    def _fpr(a: AggregateMetrics) -> str:
        return f"{_fmt_pct(a.first_pass_rate_mean)} ±{a.first_pass_rate_stdev * 100:.0f}% [{_fmt_pct(a.first_pass_rate_min)}~{_fmt_pct(a.first_pass_rate_max)}]"

    rows = [
        (f"樣本數 N", str(pty.n), str(sdk.n)),
        ("一次通過率 (mean ±stdev [min~max])", _fpr(pty), _fpr(sdk)),
        ("CORRECTION 次數 (mean / total)",
         f"{pty.correction_count_mean:.1f} / {pty.correction_count_total}",
         f"{sdk.correction_count_mean:.1f} / {sdk.correction_count_total}"),
        ("SDD_CONTRACT_VIOLATION (total)",
         str(pty.sdd_violation_count_total), str(sdk.sdd_violation_count_total)),
        ("token 峰值 (mean / max)",
         f"{pty.peak_token_pct_mean:.0f}% / {pty.peak_token_pct_max:.0f}%",
         f"{sdk.peak_token_pct_mean:.0f}% / {sdk.peak_token_pct_max:.0f}%"),
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


def run_backend(playbook: str, backend: str, workdir: Path, config_path: str | None = None) -> tuple[str, RunMetrics]:
    """以指定 backend 實跑 playbook（subprocess），回傳 (log_text, RunMetrics)。

    需授權 token：實際呼叫 Claude。讀引擎 utf-8 log 檔（非 stdout，避免 Windows cp950
    mangle）；backend 透過 config_path（executor.backend）切換，由呼叫端提供對應 config。
    """
    workdir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "autoclaude", playbook, "--fresh"]
    if config_path:
        cmd += ["--config", config_path]
    subprocess.run(cmd, cwd=str(workdir), capture_output=True, text=True, timeout=900)
    log_file = workdir / "logs" / "autoclaude.log"
    log_text = log_file.read_text(encoding="utf-8", errors="replace") if log_file.exists() else ""
    return log_text, parse_run_metrics(log_text, backend=backend)


def run_backend_n(playbook: str, backend: str, base_workdir: Path, n: int,
                  config_path: str | None = None) -> tuple[list[str], list[RunMetrics]]:
    """以指定 backend 連跑 N 次（每輪獨立乾淨子目錄 run_1..run_N），回傳 (logs, metrics)。

    需授權 token：每輪實際呼叫 Claude。**每輪獨立子目錄**是必要的——smoke 會建檔
    （smoke_add_test.py / smoke_add.py），同目錄重跑會使 S01「先別建 smoke_add.py」前提
    被前一輪殘留檔破壞，污染 A/B。config_path 轉絕對路徑（subprocess cwd=子目錄）。
    """
    abs_cfg = str(Path(config_path).resolve()) if config_path else None
    logs: list[str] = []
    metrics: list[RunMetrics] = []
    for i in range(1, n + 1):
        run_dir = base_workdir / f"run_{i}"
        log_text, m = run_backend(playbook, backend, run_dir, abs_cfg)
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
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)
    if args.pty_log and args.sdk_log:
        pty = parse_run_metrics(Path(args.pty_log).read_text(encoding="utf-8", errors="replace"), "pty")
        sdk = parse_run_metrics(Path(args.sdk_log).read_text(encoding="utf-8", errors="replace"), "sdk")
        print(format_comparison(pty, sdk))
    elif args.run and args.workdir:
        base = Path(args.workdir)
        n = max(1, args.n)
        if n == 1:
            _, pty = run_backend(args.run, "pty", base / "pty", args.pty_config)
            _, sdk = run_backend(args.run, "sdk", base / "sdk", args.sdk_config)
            print(format_comparison(pty, sdk))
        else:
            _, pty_runs = run_backend_n(args.run, "pty", base / "pty", n, args.pty_config)
            _, sdk_runs = run_backend_n(args.run, "sdk", base / "sdk", n, args.sdk_config)
            print(format_aggregate_comparison(
                aggregate_runs(pty_runs, "pty"), aggregate_runs(sdk_runs, "sdk")))
    else:
        print("需提供 --pty-log+--sdk-log（解析）或 --run+--workdir（實跑）", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
