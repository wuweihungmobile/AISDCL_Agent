#!/usr/bin/env python3
"""tools/lib/cpu_budget.py — 跨 leg CPU 平行度預算 SSOT（DEF-200-289）。

WHY：`parallel_shard.worker_count()`（本機 unittest 平行）、AutoClaude
`pyproject.toml` 的 `-n auto`（pytest-xdist 自算）、`AISDLC_SDD/scripts/ci-gate.sh`
與 `tools/git-hooks/pre-push` 各自寫死 `-n auto --dist worksteal`／`cpu-1` 公式，
五套互不知情、無 SSOT（帳本 DEF-200-289）。本檔是唯一算法來源。

CI runner（GitHub Actions）是無人值守 headless：`cpu-1`「保留一核給前景」在這裡
毫無意義，白白少用一核。互動環境（本機開發者終端仍在前景）才保留一核。
headless 判準＝`GITHUB_ACTIONS=true` 或 `AUTOSDD_CPU_HEADLESS=1`。cap 沿用既有
`parallel_shard.worker_count()` 的上限 9（SD 審查列為待量化 HYPOTHESIS，本輪不動）。

今日各 orchestrator（pre-push、ci-gate.sh／.ps1）皆序列跑（n_legs=1）：
`per_leg_budget(1) == total_budget()`，行為與現況相同，只有 CI headless 情境下
多分到 1 個 worker；未來若真的把某個 orchestrator 拆成多個並行 leg，才靠
`per_leg_budget()` 依 leg 數平分預算，避免多個 leg 各自 `-n auto` 疊加超賣核心。
"""
from __future__ import annotations

import argparse
import os
import sys


def total_budget(cpu_count: int | None = None, headless: bool | None = None) -> int:
    """headless 無前景可保留 ⇒ 用滿全部核心；互動環境保留一核給前景。

    cap 沿用 `parallel_shard.worker_count()` 既有上限 `max(1, min(9, ·))`。
    """
    cpu = cpu_count if cpu_count is not None else (os.cpu_count() or 2)
    if headless is None:
        headless = (
            os.environ.get("GITHUB_ACTIONS") == "true"
            or os.environ.get("AUTOSDD_CPU_HEADLESS") == "1"
        )
    raw = cpu if headless else cpu - 1
    return max(1, min(9, raw))


def per_leg_budget(n_legs: int, total: int | None = None) -> int:
    """把 `total_budget()` 依 leg 數平分；`n_legs<=1` 時等於 `total_budget()` 本身。"""
    t = total if total is not None else total_budget()
    return max(1, t // max(1, n_legs))


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="cpu_budget.py",
        description="印出跨 leg CPU 預算（單一 leg 應分配的 worker 數）到 stdout。",
    )
    parser.add_argument("--legs", type=int, required=True, help="平行 leg 數（今日恆為 1）")
    args = parser.parse_args(argv)  # 未知參數：argparse 自行印 usage 至 stderr 並 exit(2)
    print(per_leg_budget(args.legs))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
