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
# 刻意刪減測試時同步下修；新增測試在 `RATCHET_STALE_RATIO` 倍以內不需動（下限
# 語意），超過即**必須**重釘，否則保鮮期斷言會讓閘門變紅（見下方兩層設計說明）。
MIN_TESTS = 616  # R57 收尾重釘（動工前為 R15 釘的 290，對當時實況 530 已鑑別力失效 45%＝可靜默蒸發 240 支仍綠）。本值由主控在**所有並行修復包與四方複審 agent 全部停工後**，於最終工作樹實跑 `python3 tools/run_root_unittests.py` 取其印出的「發現 N 個測試」直接填入，不做任何加減推算——R57 過程中兩度用算式推得 552／558，兩次都當場就與實況不符（SD-R57-01／QA-R57-07 抓出），故本行的重釘判準明定為「填實測值」

# R57 修正：「人工 ratchet」本身就是缺陷來源——R15 釘完後連續 11 輪沒人重釘，
# 下限與實況愈拉愈開、鑑別力單調衰減，而且**沒有任何訊號**提醒該重釘（下限語意
# 天生只在往下掉時說話）。故設**兩層**、且刻意用**不同**門檻：
#   ① WARN 層（本檔 `warn_ratchet_drift`，只印不擋）：實況 > 下限 × 1.10 即在
#      終端印一行「該重釘了」。這一層才是真正的「只 WARN 不 fail」。
#   ② 保鮮期層（`tools/tests/test_run_root_unittests.py::
#      test_current_pin_is_not_already_stale`，會讓閘門變紅）：實況 > 下限 ×
#      1.25 即 FAIL。純 WARN 擋不住「11 輪沒人重釘」的心理機制（常亮的警告＝
#      背景噪音），必須有一道會紅的線。
# 兩層門檻必須不同，否則 WARN 一響就等於閘門已紅，①的存在毫無意義——R57
# round 1（ARCH-06）實測 `ratchet_drift_message(698, 558)` 非 None ⇒ 當時單一
# 1.25 門檻下「只 WARN 不 fail」的註解與行為互相打臉。現行設計給的是 [1.10,
# 1.25] 這段緩衝：先被提醒、還沒被擋，收輪時順手重釘即可。
# 代價（明說）：累積新增超過 MIN_TESTS × 0.25 支測試就**必須**重釘，這是刻意
# 承受的維護負擔，換到的是下限不會再腐化 11 輪。
RATCHET_WARN_RATIO = 1.10
RATCHET_STALE_RATIO = 1.25

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
    warn_ratchet_drift(count, min_tests)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    report_windows_native_skips(result)
    if not result.wasSuccessful():
        dump_failure_detail(result)
    return 0 if result.wasSuccessful() else 1


def ratchet_drift_message(
    count: int, min_tests: int, ratio: float = RATCHET_WARN_RATIO
) -> str | None:
    """純函式（無 I/O 副作用，比照 `windows_native_skips` 慣例）：實況相對下限
    漂移超過 `ratio` 倍時回傳提醒字串，否則 None。R57 新增，WHY 見
    `RATCHET_WARN_RATIO`。`ratio` 參數化是為了讓兩層共用同一段判定與訊息：
    runner 用預設的 WARN 倍數，保鮮期斷言傳 `RATCHET_STALE_RATIO`。"""
    if count <= min_tests * ratio:
        return None
    return (
        f"⚠️  測試數量下限已過期：實況 {count} 個 > 下限 {min_tests} × "
        f"{ratio}——下限的鑑別力只剩「可靜默蒸發 {count - min_tests} "
        f"個測試仍不紅」，請把 tools/run_root_unittests.py 的 MIN_TESTS 重釘為 {count}"
    )


def warn_ratchet_drift(count: int, min_tests: int) -> str | None:
    msg = ratchet_drift_message(count, min_tests)
    if msg is not None:
        print(msg)
    return msg


# R57 round 3 ARCH-R57R3-03：Architect 獨立重跑本 runner 14 次，其中 **1 次**出現
# `Ran 610 tests / FAILED (failures=4, skipped=4)`，其餘 13 次全綠；三種針對性重現
# （連跑 6 次／兩實例並行／8 顆 CPU 燒滿）皆未重現，而**本 runner 不保留失敗細節**，
# 該次的失敗測試名隨 process 消失，故無法歸因。方向為 fail-closed（假紅、不放行缺陷），
# 但「下次再發生仍然無法診斷」本身是可以現在就消除的缺口。
# 落檔而非改判邏輯：不動 rc、不動任何斷言，只在已經要回 1 的路徑上多寫一份明細。
_FAILURE_LOG = Path(__file__).resolve().parent / ".last_failure.log"


def dump_failure_detail(result: unittest.TestResult, path: Path | None = None) -> Path:
    """把失敗/錯誤的 test id 與 traceback 落檔，供下次非決定性翻紅時定位。

    只在 `wasSuccessful()` 為 False 時被呼叫。回傳寫入的路徑（測試用）。
    寫檔失敗不得影響 runner 的 rc——診斷輔助不應反過來變成新的失敗來源。
    """
    target = path or _FAILURE_LOG
    # R57 round 4 SA-R57R4-01：`wasSuccessful()` 在 `unexpectedSuccesses` 非空時
    # 也回 False，原版只讀 failures/errors ⇒ 該模式下 rc=1 卻落一份**不指名任何
    # 測試的空明細**，正是本機制立意要消除的「無法歸因」狀態（實測產出僅 60 bytes
    # 的 `（0 failures / 0 errors）` 標頭）。三個 bucket 一併納入。
    unexpected = list(getattr(result, "unexpectedSuccesses", ()) or ())
    lines = [f"# run_root_unittests 失敗明細（{len(result.failures)} failures / "
             f"{len(result.errors)} errors / {len(unexpected)} unexpected successes）"]
    for label, bucket in (("FAIL", result.failures), ("ERROR", result.errors)):
        for test, tb in bucket:
            lines.append(f"\n===== {label}: {test.id()} =====\n{tb}")
    for test in unexpected:
        # unexpectedSuccesses 沒有 traceback，只有測試本身（標了 expectedFailure 卻通過）
        tid = test.id() if hasattr(test, "id") else str(test)
        lines.append(f"\n===== UNEXPECTED SUCCESS: {tid} =====\n"
                     "（標記 expectedFailure 但實際通過——該缺陷可能已修好，請移除標記）")
    return _write_failure_log(target, "\n".join(lines))


def _write_failure_log(target: Path, body: str) -> Path:
    """落檔並回報。與 `dump_failure_detail` 分離＝比照本檔 `windows_native_skips`／
    `report_windows_native_skips` 的既有慣例（R57 round 4 SA-R57R4-02／QA-R57R4-02：
    print 副作用寫在被單元測試直接呼叫的函式內，會讓每次**全綠**執行的終端輸出混入
    fixture 產生的落檔訊息與 ⚠️ 警告，混淆複審者對「本次是否真有失敗」的判讀——與
    R43 二審 SA 對 `windows_native_skips` 揪出的問題同型）。"""
    try:
        target.write_text(body, encoding="utf-8")
        print(f"🔍 失敗明細已落檔：{target}（供非決定性翻紅時定位，見 DEF-101-499）")
    except OSError as exc:  # 診斷輔助失敗不得升級為 runner 失敗
        print(f"⚠️  失敗明細落檔失敗（{exc}）——不影響 rc", file=sys.stderr)
    return target


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
