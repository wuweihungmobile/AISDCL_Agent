#!/usr/bin/env python3
"""tools/lib/cpu_budget.py — 跨 leg CPU 平行度預算 SSOT（DEF-200-289；DEF-200-327 實體核優先）。

`parallel_shard.worker_count()`／AutoClaude pytest `-n auto`／`ci-gate.sh`／`pre-push`
共用本檔算法，唯一算法來源（帳本 DEF-200-289）。

headless（CI）＝`max(1, min(CAP, 邏輯核))`，不變（CI vCPU 皆 <=10，4/4/3 零回歸）。
互動環境改用**實體核 -1**：i5-14600K 14P/20L 實測 w=9 196.5s／w=14 166.8s／
w=19 173.7s，邏輯核 SMT/E-core 超額訂閱互動情境反而拖慢；10 核筆電 8P+2E → 9 是
既有校準點。CAP 9→16（>16 實體核未量測＝HYPOTHESIS）。`physical_count` 未給時
`_detect_physical_count()` optional import psutil；缺席或回 None 退回邏輯核（舊行為）。
"""
from __future__ import annotations

import argparse
import os
import sys

_CAP = 16


def _detect_physical_count() -> int | None:
    """optional psutil 探測實體核心數；缺席或例外一律回 None（呼叫端退回邏輯核）。"""
    try:
        import psutil
    except ImportError:
        return None
    try:
        return psutil.cpu_count(logical=False)
    except Exception:
        return None


def total_budget(
    cpu_count: int | None = None,
    headless: bool | None = None,
    physical_count: int | None = None,
) -> int:
    """headless 用邏輯核心（不變）；互動用實體核心 -1（見檔頭 WHY）。"""
    logical = cpu_count if cpu_count is not None else (os.cpu_count() or 2)
    if headless is None:
        headless = (
            os.environ.get("GITHUB_ACTIONS") == "true"
            or os.environ.get("AUTOSDD_CPU_HEADLESS") == "1"
        )
    if headless:
        return max(1, min(_CAP, logical))

    physical = physical_count if physical_count is not None else _detect_physical_count()
    if not physical:
        physical = logical
    return max(1, min(_CAP, physical - 1))


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
