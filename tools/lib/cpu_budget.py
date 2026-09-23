#!/usr/bin/env python3
"""tools/lib/cpu_budget.py — 跨 leg CPU 平行度預算 SSOT（DEF-200-289；DEF-200-327 實體核優先；
2026-09-20 DEF-200-347：實體核偵測改免 psutil 依賴）。

`parallel_shard.worker_count()`／AutoClaude pytest `-n auto`／`ci-gate.sh`／`pre-push`
共用本檔算法，唯一算法來源（帳本 DEF-200-289）。

headless（CI）＝`max(1, min(CAP, 邏輯核))`，不變（CI vCPU 皆 <=10，4/4/3 零回歸）。

互動環境公式：`max(1, min(CAP, (實體核-1) + floor((邏輯核-實體核)/2)))`——實體核
-1 為基礎（前台保留一核），SMT 兄弟執行緒（邏輯核超出實體核的部分）不是白工，
給**半信用**再加回來，比「當成獨立核心」更貼近實測、也比「完全不計」更接近
觀察到的最佳點。`physical` 量不到時退回 `logical`（此時算式退化為
`logical-1`，與修法前行為位元級相同）。

2026-09-23 QA 六輪交錯掃描實測（i5-14600K，14P/20L，Windows，每個 worker 數
（W）跑兩輪取中位數；W=14/15/17/18 未測＝HYPOTHESIS）：

| W  | wall 中位數 | 平均 CPU | 穩態 CPU |
|----|------------|---------|---------|
| 13 | 189.4s     | 58.8%   | 74.9%   |
| 16 | 163.7s     | 74.0%   | 88.9%（最佳點）|
| 20 | 176.5s     | 72.2%   | 98.9%（S 膨脹，被單一最長單位卡成 max_unit-bound）|

`(14-1) + floor((20-14)/2) = 13+3 = 16`——與實測最佳點吻合。CAP 維持 16
（>16 實體核仍是 HYPOTHESIS，未實測）。10 核筆電（8P+2E）的既有校準點「9」是
舊公式（純 physical-1）算出的值，未知其確切邏輯核數（P-core 是否啟用 SMT），
新公式在該機型上會算出什麼尚未重新實測，本檔誠實標記為 HYPOTHESIS，不臆測
新值。

舊校準句「w=9 196.5s／w=14 166.8s／w=19 173.7s」已作廢：那組數字量測時全套被
單一 166.6s 的離群單位（`test_archive_defect_log` 的一支重測試）綁死，不論
worker 數怎麼加，makespan 都卡在那支測試附近，對「加 worker 有沒有用」這個
問題零鑑別力（該單位已於後續輪次自動細分掉）。

`_detect_physical_count()` 三段式偵測（2026-09-20 起；Q3「自動偵測」的結構缺口）：
① psutil 若可 import 且回正整數就用（涵蓋面最廣，第一順位 optional 依賴，沿用舊行為）；
② 否則 `_platform_physical_count()`（依 `sys.platform` 分派、免第三方依賴）；
③ 否則 None（呼叫端 `total_budget()` 退回邏輯核，舊行為不變）。
任一段拋出的任何例外一律吞下回 None——fail-open 契約不變。

事實根據：psutil 不是本 repo 任何宣告依賴（pyproject／requirements／bootstrap 全庫
零命中），根層單一 .venv 內 `import psutil` 恆 `ModuleNotFoundError`；三段式之前
`_detect_physical_count()` 因此在乾淨環境**恆**回 None，互動預算恆退回「邏輯核-1」。
本機（M1 Max，10P=10L）巧合正確；在有 SMT 的機器（i5-14600K 14P/20L）沒 psutil
會算成 `min(16, 19)=16` 而非正確的 13。

`_platform_physical_count()` 每平台一支子路徑，平台專屬字面只住在該分支內（鐵律三）：
  - darwin：`sysctl -n hw.physicalcpu`（spawn 一個短命子行程，互動終端可接受）。
  - linux：讀 `/proc/cpuinfo`，以 `physical id`×`core id` 的唯一組合數為實體核數；
    兩鍵任一在全文都沒出現（ARM 常見）回 None——不臆測、不猜 CPU 拓撲。
  - win32：**不 spawn 任何行程**（GUI 子系統載具下 spawn console 執行檔會閃視窗，
    同根層 CLAUDE.md〈hook 載具〉一節的顧慮）；改用 ctypes 呼叫 kernel32
    `GetLogicalProcessorInformation`，數 `Relationship == RelationProcessorCore`
    （值 0）的筆數。
    已知劃界（2026-09-20 複審 Architect）：本 API 只回報呼叫執行緒所屬 processor group，
    >64 邏輯核（多 group）機器會靜默低估；CAP=16 下無影響，需支援時改用
    `GetLogicalProcessorInformationEx`。
  - 其他平台（BSD 等）：回 None。

誠實劃界：cgroup／容器 CPU 配額與「這台機器有幾顆實體核」是兩個不同的量，本檔
只回答後者（前者是 headless 分支已經在管的「CI vCPU」，語意不同、不要混用）；
CAP 16 以上的機器仍是 HYPOTHESIS，未實測。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

_CAP = 16


def _parse_int_line(text: str) -> int | None:
    """取字串第一個非空行、去除頭尾空白後轉 int；空白或非數字一律回 None
    （`sysctl` 失敗時的錯誤訊息、空輸出皆屬此類，不得讓 `ValueError` 外洩）。"""
    stripped = text.strip()
    if not stripped:
        return None
    first_line = stripped.splitlines()[0].strip()
    if not first_line:
        return None
    try:
        return int(first_line)
    except ValueError:
        return None


def _parse_proc_cpuinfo(text: str) -> list[tuple[int, int]] | None:
    """解析 `/proc/cpuinfo` 文字，抽出每個 `processor` block 的
    `(physical id, core id)`。`physical id`／`core id` 兩鍵只要有一個在**全文**
    一次都沒出現（ARM 常見無此兩鍵）即回 None；否則回傳 tuple 列表（含 SMT 造成
    的重複，交給 `_count_processor_cores()` 去重）。"""
    physical_id: int | None = None
    core_id: int | None = None
    records: list[tuple[int, int]] = []
    saw_physical_key = False
    saw_core_key = False

    for line in text.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if key == "processor":
            if physical_id is not None and core_id is not None:
                records.append((physical_id, core_id))
            physical_id = None
            core_id = None
        elif key == "physical id":
            saw_physical_key = True
            try:
                physical_id = int(value)
            except ValueError:
                physical_id = None
        elif key == "core id":
            saw_core_key = True
            try:
                core_id = int(value)
            except ValueError:
                core_id = None

    if physical_id is not None and core_id is not None:
        records.append((physical_id, core_id))

    if not saw_physical_key or not saw_core_key:
        return None
    return records


def _count_processor_cores(records: list[tuple[int, int]] | None) -> int | None:
    """對 `(physical_id, core_id)` tuple 列表去重計數；`records` 為 `None` 或空
    list（兩鍵有出現但一筆完整配對都湊不出來）一律回 None。"""
    if not records:
        return None
    return len(set(records))


def _platform_physical_count() -> int | None:
    """依 `sys.platform` 分派的免第三方依賴實體核偵測（見檔頭〈`_platform_
    physical_count()`〉一節）。任何例外一律回 None，呼叫端 `_detect_physical_
    count()` 再退回邏輯核，fail-open 契約不變。"""
    if sys.platform == "darwin":
        try:
            proc = subprocess.run(
                ["sysctl", "-n", "hw.physicalcpu"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=2,
            )
        except Exception:
            return None
        if proc.returncode != 0:
            return None
        return _parse_int_line(proc.stdout)

    if sys.platform == "linux":
        try:
            with open("/proc/cpuinfo", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            return None
        return _count_processor_cores(_parse_proc_cpuinfo(text))

    if sys.platform == "win32":
        import ctypes

        class _SystemLogicalProcessorInformation(ctypes.Structure):
            _fields_ = [
                ("ProcessorMask", ctypes.c_void_p),
                ("Relationship", ctypes.c_int),
                # 對應官方 union 內 ULONGLONG Reserved[2]；撐出正確對齊（offset=16），內容不讀。
                ("_union", ctypes.c_ulonglong * 2),
            ]

        _RELATION_PROCESSOR_CORE = 0
        try:
            kernel32 = ctypes.windll.kernel32
            ret_len = ctypes.c_ulong(0)
            kernel32.GetLogicalProcessorInformation(None, ctypes.byref(ret_len))
            if ret_len.value == 0:
                return None
            buf = (ctypes.c_byte * ret_len.value)()
            ok = kernel32.GetLogicalProcessorInformation(
                ctypes.cast(buf, ctypes.POINTER(_SystemLogicalProcessorInformation)),
                ctypes.byref(ret_len),
            )
            if not ok:
                return None
        except Exception:
            return None
        entry_size = ctypes.sizeof(_SystemLogicalProcessorInformation)
        count = ret_len.value // entry_size if entry_size else 0
        records_ptr = ctypes.cast(buf, ctypes.POINTER(_SystemLogicalProcessorInformation))
        cores = sum(
            1 for i in range(count)
            if records_ptr[i].Relationship == _RELATION_PROCESSOR_CORE
        )
        return cores or None

    return None


def _detect_physical_count() -> int | None:
    """三段式實體核偵測（見檔頭）：psutil 優先，缺席或失敗退 `_platform_
    physical_count()`，再失敗回 None（呼叫端退回邏輯核）。"""
    try:
        import psutil
    except ImportError:
        psutil = None
    if psutil is not None:
        try:
            count = psutil.cpu_count(logical=False)
        except Exception:
            count = None
        if isinstance(count, int) and count > 0:
            return count

    try:
        count = _platform_physical_count()
    except Exception:
        return None
    if isinstance(count, int) and count > 0:
        return count
    return None


def total_budget(
    cpu_count: int | None = None,
    headless: bool | None = None,
    physical_count: int | None = None,
) -> int:
    """headless 用邏輯核心（不變）；互動用「實體核心 -1 ＋ SMT 兄弟執行緒半信用」
    （見檔頭 WHY 與 2026-09-23 QA 實測表）。"""
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
    smt_credit = (logical - physical) // 2
    return max(1, min(_CAP, (physical - 1) + smt_credit))


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
