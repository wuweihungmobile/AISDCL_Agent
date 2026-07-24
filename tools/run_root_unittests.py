#!/usr/bin/env python3
"""tools/tests 全套 unittest 執行器（含測試數量下限釘選）— R10 QA-2（DEF-101-127）。

為何存在：`python -m unittest discover` 對「發現 0 個測試」回 rc=0
（`Ran 0 tests ... OK`，Python 3.11 實測）。tools/tests/ 目錄改名、測試檔改名
不符 `test_*.py`、或 `-s` 路徑打錯 → 全部回歸鎖同時靜默消失，而四處 gate
（pre-push root-infra leg、root-infra-ci step 8、windows/macos smoke）依然全綠、
無任何 diff 訊號。R9 已給 parity 抽取加 `_MIN_EXTRACT_COUNTS` 下限釘選，同構
風險在 unittest 這裡原本沒有對等防護。

行為：discover 後先斷言 countTestCases() >= MIN_TESTS 再執行；低於下限 exit 1
（測試根本不跑——數量崩塌本身就是失敗）。刻意刪減測試時須同步下修 MIN_TESTS
（比照 check_script_parity._MIN_EXTRACT_COUNTS 的紅燈指路慣例）。
discovery import 失敗由 unittest 轉成 _FailedTest（計入數量且執行必紅），不會
被本工具的計數守門漏掉。

呼叫端（取代裸 `python -m unittest discover -s tools/tests`）：
  tools/git-hooks/pre-push（root-infra leg ②）、.github/workflows/root-infra-ci.yml
  step 8、windows-compat-ci.yml、macos-compat-ci.yml 對應 step。

使用：python tools/run_root_unittests.py（repo 內任意 cwd；路徑以本檔自身定位）
測試：tools/tests/test_run_root_unittests.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌) 防崩潰保護

_TESTS_DIR = Path(__file__).resolve().parent / "tests"

# 下限釘選：低於此數＝測試大規模靜默消失（目錄/pattern/路徑壞掉），紅燈。
# 刻意刪減測試時同步下修；新增測試不需動（下限語意）。
MIN_TESTS = 290  # R15 ratchet：三支新守門（bash32/ps1_bom/onboarding_parity_interlock）落地當下實況 290，直接釘實際數（主控收輪統一重釘）

# R43 Architect P1（DEF-101-348 方向①）：DEF-101-343~345 揪出 5 支 Windows 專屬
# 回歸測試連續 5+ 輪「全 APPROVE」卻從未在原生 Windows 上真正跑過——`unittest`
# 預設摘要（`skipped=N`）不區分「一般性 skip」與「這支測試的驗證價值僅在原生
# Windows 上成立、這次環境不符沒跑」，是造成該漏洞連續多輪未被發現的根因之一。
# 凡 skip 理由帶此標籤的測試，於摘要末另印一段醒目清單，供複審者一眼辨識。
WINDOWS_NATIVE_SKIP_TAG = "[WINDOWS-NATIVE-ONLY]"


def discover_suite(start_dir: Path) -> unittest.TestSuite:
    # 每次新建 TestLoader：defaultTestLoader 有狀態（_top_level_dir 殘留），
    # 同進程第二次對不同目錄 discover 會炸 "Start directory is not importable"。
    return unittest.TestLoader().discover(str(start_dir), pattern="test_*.py")


def run_with_floor(start_dir: Path, min_tests: int) -> int:
    """discover → 數量下限守門 → 執行；回傳 exit code。"""
    suite = discover_suite(start_dir)
    count = suite.countTestCases()
    if count < min_tests:
        print(
            f"❌ unittest 數量下限釘選失敗：{start_dir} 只發現 {count} 個測試 "
            f"< 下限 {min_tests}——測試疑似大規模靜默消失（目錄改名/pattern 不符/"
            f"路徑錯）；若為刻意刪減請同步下修 MIN_TESTS",
            file=sys.stderr,
        )
        return 1
    print(f"✅ unittest 數量下限釘選通過：發現 {count} 個測試（下限 {min_tests}）")
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    report_windows_native_skips(result)
    return 0 if result.wasSuccessful() else 1


def windows_native_skips(result: unittest.TestResult) -> list[str]:
    """純函式（無 I/O 副作用）：從 `result.skipped` 篩出帶 `[WINDOWS-NATIVE-ONLY]`
    標籤者，回傳測試 id 清單。與 `report_windows_native_skips` 分離（R43 二審 SA
    複查揪出：原本印出副作用寫在同一函式內，導致 `test_run_root_unittests.py::
    ReportWindowsNativeSkipsTest` 自測時直接呼叫它，會把 fixture 用的假測試 id
    也印到 `python tools/run_root_unittests.py` 的真實終端輸出裡，混淆複審者
    對「本次是否真有 Windows 專屬測試未驗證」的判讀——測試應只斷言回傳值，不該
    觸發生產端的列印副作用）。"""
    tagged = [test for test, reason in result.skipped if WINDOWS_NATIVE_SKIP_TAG in reason]
    return [test.id() for test in tagged]


def report_windows_native_skips(result: unittest.TestResult) -> list[str]:
    """在一般 `skipped=N` 摘要之外，另印出「僅原生 Windows 上才具驗證價值」
    的 skip 清單（DEF-101-348 方向①）；回傳被標記的測試 id 清單。"""
    tagged_ids = windows_native_skips(result)
    if tagged_ids:
        print(
            f"⚠️  {len(tagged_ids)} 個 Windows 專屬測試本次「未在原生 Windows 環境驗證」"
            f"（非一般 skip，見 DEF-101-348/R43）："
        )
        for test_id in tagged_ids:
            print(f"   - {test_id}")
    return tagged_ids


def main() -> int:
    if not _TESTS_DIR.is_dir():
        print(f"❌ 測試目錄不存在：{_TESTS_DIR}", file=sys.stderr)
        return 1
    return run_with_floor(_TESTS_DIR, MIN_TESTS)


if __name__ == "__main__":
    sys.exit(main())
