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
import subprocess
import sys
from dataclasses import dataclass
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
    run_succeeded: bool = False
    escalated: bool = False

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
    # 無 KernelResult 行（半途 log）→ 退回以 ✓ 標記計完成步數
    if m.completed_steps == 0:
        m.completed_steps = completed_from_marks

    # token 峰值：僅取 TOKEN_COMPACT 行的百分比（達門檻才印；未印→0.0，誠實表「低於記錄門檻」）
    peak = 0.0
    for line in log_text.splitlines():
        if "TOKEN_COMPACT" not in line:
            continue
        for pct in _RE_TOKEN_PCT.findall(line):
            peak = max(peak, float(pct))
    m.peak_token_pct = peak
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
        ("完成步驟 / 總步驟",
         f"{pty.completed_steps}/{pty.total_steps}",
         f"{sdk.completed_steps}/{sdk.total_steps}"),
        ("run 成功 / escalated",
         f"{pty.run_succeeded} / {pty.escalated}",
         f"{sdk.run_succeeded} / {sdk.escalated}"),
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


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="pty vs sdk 後端 A/B 指標對比")
    p.add_argument("--pty-log", help="既有 pty run log 檔")
    p.add_argument("--sdk-log", help="既有 sdk run log 檔")
    p.add_argument("--run", help="實跑模式：playbook 路徑（需授權 token）")
    p.add_argument("--workdir", help="實跑工作目錄")
    p.add_argument("--pty-config", help="實跑模式：backend=pty 的 config")
    p.add_argument("--sdk-config", help="實跑模式：backend=sdk 的 config")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)
    if args.pty_log and args.sdk_log:
        pty = parse_run_metrics(Path(args.pty_log).read_text(encoding="utf-8", errors="replace"), "pty")
        sdk = parse_run_metrics(Path(args.sdk_log).read_text(encoding="utf-8", errors="replace"), "sdk")
    elif args.run and args.workdir:
        base = Path(args.workdir)
        _, pty = run_backend(args.run, "pty", base / "pty", args.pty_config)
        _, sdk = run_backend(args.run, "sdk", base / "sdk", args.sdk_config)
    else:
        print("需提供 --pty-log+--sdk-log（解析）或 --run+--workdir（實跑）", file=sys.stderr)
        return 2
    print(format_comparison(pty, sdk))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
