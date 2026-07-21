#!/usr/bin/env python3
"""integration_gate_core.py — AISDCL_Agent 整合層薄聚合閘門單一核心（macOS / Linux / Windows 共用）。

DEF-101-068(b) 收斂案（R16 架構最佳化建議 B）：原 tools/integration_gate.{sh,ps1} 為雙實作
（bash / PowerShell 各長一份業務邏輯），本檔將全部段落語意收斂為單一 Python 核心，兩支同名
.sh / .ps1 降為「確認直譯器 → 轉呼叫本檔 → 傳遞 exit code」的薄殼——模式對齊
tools/dev_start.{py,sh,ps1} 與 AutoClaude/tools/local_ci_gate.{py,sh,ps1}（R12 已收斂先例）。

設計原則：不另立第三真相源，僅依序呼叫兩專案既有單一真相源再跑整合煙霧測試。
  [1/5] AutoClaude   : tools/local_ci_gate.{sh,ps1}
  [2/5] AISDLC_SDD   : scripts/ci-gate.sh（Windows 端經 Git Bash 執行）
  [3/5] 整合測試     : pytest tests/integration/test_sdd_bridge/ -q
  [4/5] 回退驗證     : pytest tests/integration/test_sdd_bridge/test_rollback_compat.py -q
  [5/5] cc-switch A/B: 多模型後端對比（未安裝 CLI → SKIP）

用法（一般經薄殼呼叫；直接呼叫亦可）：
  python tools/integration_gate_core.py                # 完整
  python tools/integration_gate_core.py --skip-full     # 僅跑 [3]+[4]+[5]（快速迴圈）
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # monorepo 根（tools/ 的上一層）

_CC_CLI_NAMES = ("cc-switch", "cc-switch-cli", "ccs")


def parse_args(argv: list[str]) -> bool:
    """回傳 skip_full（介面對等收斂前 `--skip-full` / `-SkipFull`）。"""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--skip-full", action="store_true", dest="skip_full")
    ns, _unknown = parser.parse_known_args(argv)
    return ns.skip_full


def _hooks_liveness_advisory() -> None:
    """git hooks liveness 偵測（警告不擋）。

    repo 搬移/改名或未安裝時 dispatcher hooks 會靜默失效（實證）；CI 環境（CI 有值）
    跳過（GitHub/act 環境無 hooks 屬正常）。偵測邏輯抽共用（S11）：見
    tools/check_hooks_liveness.py（單一真相源，供本檔與 AutoClaude/tools/local_ci_gate.py
    共用呼叫）；advisory：任何探測失敗都不得影響閘門本體。
    """
    if os.environ.get("CI"):
        return
    script = ROOT / "tools" / "check_hooks_liveness.py"
    if not script.is_file():
        return
    try:
        subprocess.run([sys.executable, str(script)])
    except OSError:
        pass


def find_git_bash() -> str | None:
    """Windows 上尋找真正的 Git Bash（bash.exe），排除 WSL 的 System32 佔位。

    port 自 tools/lib/Find-GitBash.ps1（S11 抽出的共用邏輯）：標準 Git for Windows
    安裝預設只把 Git\\cmd 加進 PATH，Git\\bin\\bash.exe 本來就不在 PATH，單查 PATH
    會對絕大多數標準安裝誤報「找不到 Git Bash」；PATH 上找到的 bash 若位於
    System32（WSL 佔位）亦不可用（那是 Linux 環境，無本 repo 的 Windows venv/依賴）。
    """
    found = shutil.which("bash")
    if found and "system32" not in found.lower():
        return found
    for env_var in ("ProgramFiles", "ProgramFiles(x86)", "LocalAppData"):
        base = os.environ.get(env_var)
        if not base:
            continue
        sub = "Programs\\Git\\bin\\bash.exe" if env_var == "LocalAppData" else "Git\\bin\\bash.exe"
        cand = Path(base) / sub
        if cand.is_file():
            return str(cand)
    return None


# ---------------------------------------------------------------------------
# 各 section（名稱字串與順序為凍結介面——與收斂前 .sh/.ps1 輸出逐字對齊）
# ---------------------------------------------------------------------------

def sec_autoclaude() -> int:
    """[1/5] AutoClaude local_ci_gate。"""
    cwd = ROOT / "AutoClaude"
    if os.name == "nt":
        cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", "tools/local_ci_gate.ps1"]
    else:
        cmd = ["bash", "tools/local_ci_gate.sh"]
    return subprocess.run(cmd, cwd=cwd).returncode


def sec_sdd() -> int:
    """[2/5] AISDLC_SDD ci-gate.sh（Windows 端需先找到 Git Bash）。"""
    cwd = ROOT / "AISDLC_SDD"
    if os.name == "nt":
        bash_exe = find_git_bash()
        if bash_exe is None:
            print(
                "❌ 找不到 Git Bash（bash.exe）→ 無法執行 scripts/ci-gate.sh。"
                "請安裝 Git for Windows（https://git-scm.com/download/win）後重跑。",
                flush=True,
            )
            return 1
        cmd = [bash_exe, "scripts/ci-gate.sh"]
    else:
        cmd = ["bash", "scripts/ci-gate.sh"]
    return subprocess.run(cmd, cwd=cwd).returncode


def sec_bridge() -> int:
    """[3/5] SDD bridge 整合煙霧。"""
    cwd = ROOT / "AutoClaude"
    return subprocess.run(
        [sys.executable, "-m", "pytest", "tests/integration/test_sdd_bridge/", "-q"], cwd=cwd
    ).returncode


def sec_rollback() -> int:
    """[4/5] 回退驗證（v0.01/v0.02 真品 FSM 狀態）。"""
    cwd = ROOT / "AutoClaude"
    return subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "tests/integration/test_sdd_bridge/test_rollback_compat.py", "-q",
        ],
        cwd=cwd,
    ).returncode


# ---------------------------------------------------------------------------
# 閘門編排
# ---------------------------------------------------------------------------

def run_section(
    label: str, fn: Callable[[], int],
    failures: list[str], counters: dict[str, int],
) -> None:
    """執行單一 section 並收集結果（逐項收集不中斷，對齊收斂前 run_section/Invoke-Section）。

    section 執行失敗（例外）判 FAIL 不炸——對齊 .ps1 的 Continue 語意。
    """
    print(f"\n==> {label}", flush=True)
    try:
        rc = int(fn() or 0)
    except Exception as exc:
        print(f"[{label}] 例外：{exc}", flush=True)
        rc = 1
    if rc != 0:
        failures.append(f"{label} (exit={rc})")
        print(f"❌ {label} FAILED (exit={rc})", flush=True)
    else:
        counters["pass"] += 1
        print(f"✅ {label} PASS", flush=True)


def _run_cc_switch_section(counters: dict[str, int]) -> None:
    """[5/5] cc-switch 多模型 A/B 驗收（不經 run_section——本段從未產生 FAIL，只有 PASS/SKIP）。"""
    print("\n==> [5/5] cc-switch 多模型 A/B 驗收", flush=True)
    cc_cli_path: str | None = None
    for name in _CC_CLI_NAMES:
        found = shutil.which(name)
        if found:
            cc_cli_path = found
            break

    smoke_pb = ROOT / "AutoClaude" / "scripts" / "sdd_bridge_smoke.yaml"
    pb_rel = (
        "scripts/sdd_bridge_smoke.yaml"
        if smoke_pb.is_file()
        else "⚠️載具缺失:scripts/sdd_bridge_smoke.yaml(DEF-10-001a)"
    )

    if cc_cli_path is None:
        counters["skip"] += 1
        print(
            "⚠️  SKIP：未偵測到 cc-switch CLI"
            "（DEF-01-007，AutoSDD_Defect_Log.md）。"
            "注意：farion1231/cc-switch 為 GUI app 不上 PATH；"
            "headless A/B 需 CLI 變體（SaladDay/cc-switch-cli）。"
            "裝好 CLI 後於 AutoClaude/ 執行："
            f"cc-switch use <profile-A> && autoclaude {pb_rel} --fresh"
            "（換 profile-B 再跑一次），"
            "對比指標：一次通過率 / CORRECTION 次數 / "
            "SDD_CONTRACT_VIOLATION 次數 / token 峰值",
            flush=True,
        )
    else:
        counters["pass"] += 1
        print(
            f"cc-switch CLI 已偵測（{cc_cli_path}）："
            f"於 AutoClaude/ 對 {pb_rel} 切換 profile 各跑一次 "
            f"--fresh，依 {pb_rel} 檔頭程序收集 A/B 四指標"
            "（一次通過率 / CORRECTION 次數 / "
            "SDD_CONTRACT_VIOLATION 次數 / token 峰值）",
            flush=True,
        )


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass
    os.environ["PYTHONUTF8"] = "1"

    skip_full = parse_args(sys.argv[1:] if argv is None else argv)
    _hooks_liveness_advisory()

    failures: list[str] = []
    counters = {"pass": 0, "skip": 0}

    if not skip_full:
        run_section("[1/5] AutoClaude local_ci_gate", sec_autoclaude, failures, counters)
        run_section("[2/5] AISDLC_SDD ci-gate.sh", sec_sdd, failures, counters)
    run_section("[3/5] SDD bridge 整合煙霧", sec_bridge, failures, counters)
    run_section(
        "[4/5] 回退驗證（v0.01/v0.02 真品 FSM 狀態）",
        sec_rollback, failures, counters,
    )

    _run_cc_switch_section(counters)

    if failures:
        joined = "; ".join(failures)
        print(f"\n❌ 整合閘門未通過：{joined}")
        return 1
    print(f"\n✅ 整合閘門通過（{counters['pass']} PASS / {counters['skip']} SKIP）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
