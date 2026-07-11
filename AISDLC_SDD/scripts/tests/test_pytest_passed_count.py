"""DEF-06-001 取證友善性 — pytest 收斂計數擷取純函式回歸鎖。

WHY（測意圖非僅行為，Rule 9）：
DEF-06-001（P3）= 雙軌 ci-gate 收斂行未印逐軌 `N passed`，零信任取證須另跑
`tee+grep` 補證。修復把「逐軌計數」印進收斂輸出，其解析交給純函式 helper
`scripts/pytest_passed_count.sh`。本測試鎖定該 helper 的擷取意圖，使其退化即紅、
且不必實跑 ~95s 整套 pytest：

  1. 取**最終** summary 的 passed 數（不抓中途進度行 / 多版串接的前一軌數字）。
  2. **subtests 邊界**：真實 pytest 尾行含 `... 14 subtests passed` 第二個 passed
     token，必須仍回主計數（如 1478）而非 14——這是本 helper 最易錯的點。
  3. **fail-soft**：無任何匹配（0 collected / error）時回 0，取證輔助絕不該反害
     ci-gate 退出碼。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts import bash_probe  # isort: skip（首方/三方分組隨 cwd 而異，跳過排序消除歧義）

# scripts/tests/ → scripts/ → AISDLC_SDD（REPO_ROOT）
REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER = REPO_ROOT / "scripts" / "pytest_passed_count.sh"

# WSL 佔位 bash（System32）吃不下 Windows 路徑引數 → 紅燈而非 skip（第五輪 DEF-101 P3）
_BASH = bash_probe.usable_bash()

pytestmark = pytest.mark.skipif(
    _BASH is None, reason="pytest_passed_count.sh 為 bash 腳本，需可用 bash（非 WSL 佔位）"
)


def _count(stdin_text: str) -> str:
    """以 stdin 餵入 pytest 輸出文字，回傳 helper 印出的計數（字串）。"""
    # 以 cwd=REPO_ROOT + 相對 posix 路徑呼叫，繞過 Windows→bash 反斜線路徑屏障
    # （與 test_ci_gate_version_resolution.py 同手法）。
    proc = subprocess.run(
        [_BASH, "scripts/pytest_passed_count.sh"],
        cwd=str(REPO_ROOT),
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert proc.returncode == 0, f"helper 非零退出：{proc.returncode}\n{proc.stderr}"
    return proc.stdout.strip()


def test_helper_exists():
    assert HELPER.is_file(), f"helper 不存在：{HELPER}"


def test_plain_passed():
    assert _count("1478 passed in 24.24s (0:00:24)\n") == "1478"


def test_subtests_boundary_returns_main_count():
    """真實尾行含 `14 subtests passed` 第二 token，須回主計數 1478 非 14。"""
    line = "1478 passed, 4 skipped, 34 deselected, 14 subtests passed in 24.24s\n"
    assert _count(line) == "1478"


def test_picks_final_summary_not_progress():
    """多行輸出（進度行在前、summary 在後）取最終 summary。"""
    out = (
        "........................ [ 50%]\n"
        "........................ [100%]\n"
        "1494 passed, 4 skipped in 23.76s\n"
    )
    assert _count(out) == "1494"


def test_multiple_passed_lines_takes_last():
    """釘住 `tail -1` 防退化語意（QA-1）：輸入含兩個 `N passed` summary（如串流殘留
    前一軌 + 本軌）→ 必回**最後一個**。把 helper 改 head -1 此 case 即紅。"""
    out = "1478 passed in 24.24s\n========\n1494 passed in 23.76s\n"
    assert _count(out) == "1494"


def test_no_match_is_zero():
    """無 passed summary（如 error / 0 collected）回 0（fail-soft，不害硬閘）。"""
    assert _count("no tests ran in 0.01s\n") == "0"
    assert _count("") == "0"


def test_failed_run_still_extracts_passed():
    """即便該行同時含 failed，仍正確擷取 passed 數（helper 只負責計數，不判定綠紅）。"""
    assert _count("3 failed, 1491 passed in 20.0s\n") == "1491"
