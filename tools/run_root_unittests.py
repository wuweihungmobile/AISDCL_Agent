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
產出：`tools/platform_native_verified.json`（**tracked**，機器自動維護的**平台對稱**
  驗證帳本，見下方「平台對稱驗證帳本」段）、`tools/.last_failure.log`（gitignored
  診斷落檔，只在有失敗時產生）。
"""
from __future__ import annotations

import ast
import hashlib
import json
import platform
import subprocess
import sys
import unittest
from collections.abc import Iterator
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌) 防崩潰保護

_TESTS_DIR = Path(__file__).resolve().parent / "tests"

# 下限釘選：低於此數＝測試大規模靜默消失（目錄/pattern/路徑壞掉），紅燈。
# 刻意刪減測試時同步下修；新增測試在 `RATCHET_STALE_RATIO` 倍以內不需動（下限
# 語意），超過即**必須**重釘，否則保鮮期斷言會讓閘門變紅（見下方兩層設計說明）。
MIN_TESTS = 781  # R58 收尾重釘 616→781（本輪新增測試 165 支：golden 差分 11、能力門檻 8、行為層鎖 7、平台帳本／skip 對帳、保留名前瞻掃描、schtasks 行為層、encoding hygiene 等）；R57 收尾重釘 290→616（動工前為 R15 釘的 290，對當時實況 530 已鑑別力失效 45%＝可靜默蒸發 240 支仍綠）。**重釘時**由主控在**所有並行修復包與四方複審 agent 全部停工後**，於最終工作樹實跑 `python3 tools/run_root_unittests.py` 取其印出的「發現 N 個測試」直接填入，不做任何加減推算——R57 過程中兩度用算式推得 552／558，兩次都當場就與實況不符（SD-R57-01／QA-R57-07 抓出），故本行的重釘判準明定為「填實測值」。🔴 **R58 round 7 SA-R58R7 P3 訂正**：上句原寫「本值由主控…直接填入」，讀起來像在斷言**現值**就是最終實測值——而 R58 收輪實測值早已超過 781（**現行值查 ONBOARDING §7**——本處刻意不寫死：round 7 寫 835、round 8 改 837，兩次都在同輪內被自己新增的測試寫成過期，**這個位置每輪都會過期，唯一根治是不寫數字**）、現值 781 是輪次中途值之一（**round 8 SA-R58R8-01 訂正**：本句 round 7 寫下時填 835，而同輪自己新增的 2 支斷言當場把它變成 837——**為修「前提被同輪後續動作推翻」而寫的訂正句，自己就是下一個實例**，同構形態第 4 次復發）。該句其實只約束「**重釘那一次**要填什麼」，不約束「不重釘時現值等於實測值」（下限語意：實況高於下限屬正常，重釘門檻見上方兩層設計說明；R58 未重釘的決定與依據記在 ONBOARDING §7）。已改寫為「重釘時…」以免這條 R57 教訓的判準句自己成為反例

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
    # 🔴 取證資料必須在 run() **之前**算：`unittest.TestSuite.run()` 每跑完一支就把它
    # 從 `_tests` 釋放成 None（CPython `_removeTestAtIndex` 的記憶體回收），事後再走
    # 一遍 suite 只會拿到一串 None，取證恆為空集合（會是靜默的假綠，不是紅燈）。
    facts = windows_native_tagged_facts(suite)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    report_windows_native_skips(result)
    record_native_verification(facts)
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


# ---------------------------------------------------------------------------
# 平台對稱驗證帳本（DEF-101-348 方向① 補完；本輪由「僅 Windows」一般化為兩平台對稱）
#
# 為何 `report_windows_native_skips()` 不夠：它印的是「**本次**這幾支沒跑」——
# 瞬時事實。DEF-101-348 記載的實害卻是跨輪事實：「這批 Windows 專屬測試**有史
# 以來從未**在原生 Windows 上跑過，而四方複審連續多輪全 APPROVE」。用瞬時警告
# 防跨輪事實在結構上不可能成功：在 macOS 上那段警告每輪必印 → 訊號值隨輪次遞減
# 成背景噪音（與 MIN_TESTS 連續 11 輪沒人重釘同一個心理機制）；而在原生 Windows
# 上它**什麼都不印**（沒 skip 就沒清單）——恰恰是「這次真的跑到了」這個唯一有
# 價值的正面事實完全沒被留下。實證：該機制上線後那幾支仍是靠「本輪剛好有台
# Windows」才第一次真的跑到。
#
# 故改記正面事實：把「本次真的在原生環境跑到的標籤測試 id + 平台指紋 + 被驗測試
# 檔的源碼 sha」寫進一份 tracked 帳本，機器寫、機器查。
#
# 設計上刻意避開本 repo 兩個已知的翻車形態：
#   ① **不得需要人工維護**：MIN_TESTS 靠人記得回填，於是連續 11 輪沒人回填、鎖的
#      鑑別力歸零。本帳本所有欄位一律由 runner 自動寫入，人只需要 commit，沒有
#      任何一格要手填、也沒有任何一格需要人記得同步。
#   ② **新鮮度判準綁源碼變動、不綁日曆天數**（ADR-SD09-011 教訓：把「源碼演進
#      證據」綁死成「日曆天數」會讓每日重測同一份源碼零增益、空轉數週）。本帳本
#      記源碼 sha：同一份源碼再驗一百次也不算新證據（帳本不動、零 diff），源碼一改
#      舊證據立即自動失效。
#
# 本輪（使用者核心質疑「為何切回 Windows 就一堆問題？日後還會發生嗎？」）補上的第三
# 件事：**把帳本一般化成平台對稱**。原版只有 Windows 一份、且只在 Windows 上跑到時
# 才說話——在 macOS 上完全沉默，於是「Windows 側的證據已落後 N 個 commit」這筆欠債
# 在你真的開機到 Windows 之前**沒有任何地方看得到**。R1~R57 全在 macOS 上模擬
# Windows、Windows 側每輪真驗次數≈0（DEF-101-348 known-gap），切平台當天一次領出
# 積欠存貨——問題不是「弄壞了東西」，是「不對稱沒有被顯示出來」。
#
# 故帳本改成 `platforms.<平台鍵>` 兩平台各一區塊，**同一個檔案**：兩平台都寫自己那
# 塊、也都讀得到對方那塊（拆成兩個檔案雖無合併衝突，但「A 平台讀 B 平台欠債」這個
# 唯一目的會退化成要記得去看另一個檔案）。每塊記：
#   * `head`      ＝該平台最後一次真的跑到平台閘門測試時的 HEAD commit（量化積欠的
#                   唯一硬事實：對方平台沒看過的 commit 數 = rev-list <head>..HEAD）。
#   * `last_run_on`＝那次的平台指紋（哪台機器、哪個 OS 版本取得的）。
#   * `verified`  ＝那次真的跑到的平台閘門測試 id ＋ 其所在檔的源碼 sha。
# 平台鍵刻意用 `sys.platform`（win32/darwin/linux）：與同檔 `is_native_windows()` 同
# 一詞彙，且 OS 版本升級不會生出新鍵（用 `platform.version()` 當鍵會讓帳本每次小版
# 更新就多長一塊、永遠對不上）。OS 版本仍記在 `last_run_on` 值裡，只是不當鍵。
#
# 已知代價（明說，不假裝沒有）：`head` 每前進一個 commit 就會在這份 tracked 檔產生
# 一行 diff，兩台機器各自 push 時該行會**文字衝突**。這是刻意換來的：head 是唯一能
# 量化「對方平台落後多少」的事實，屬資訊量非零的 diff（與被刻意壓抑的平台指紋噪音
# 不同類）。衝突解法固定且機械：**取兩邊 platforms 各自的區塊聯集**（兩塊語意獨立，
# 各平台只寫自己那塊，不存在真正的語意衝突）。
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
NATIVE_LEDGER = Path(__file__).resolve().parent / "platform_native_verified.json"
NATIVE_LEDGER_SCHEMA = 2
WINDOWS_PLATFORM_KEY = "win32"
# 正規對照平台：在某平台開工時「該去看誰的欠債」。linux 只在 CI 出現，它要看的是
# 本 repo 真正缺證據的那一側（Windows），不是 mac。
CANONICAL_PEER = {"win32": "darwin", "darwin": "win32", "linux": "win32"}
_NATIVE_LEDGER_WHY = (
    "機器自動維護，勿手改：平台對稱驗證帳本。platforms.<sys.platform> 各一區塊，記該平台"
    "最後一次真的跑到平台閘門測試時的 HEAD commit（head）、平台指紋（last_run_on）、"
    "以及那次真的跑到的測試 id 與其所在檔的源碼 sha256（CRLF 已正規化為 LF）。"
    "由 tools/run_root_unittests.py::record_native_verification 寫入、"
    "tools/tests/test_run_root_unittests.py::WindowsNativeVerificationLedgerTest 查核、"
    "tools/dev_start.py [6/7] 讀取後印出「對方平台證據落後多少」advisory。"
    "sha 與現況不符＝上次的原生驗證是對舊源碼做的（DEF-101-348 方向①）。"
    "合併衝突解法：取兩邊 platforms 區塊的聯集（各平台只寫自己那塊）。"
)


def is_native_windows() -> bool:
    """是否為原生 Windows 上的 CPython（Git Bash 下仍是 win32；WSL 內的 Linux
    直譯器是 'linux'，依定義不算原生 Windows，故不會被誤判）。"""
    return sys.platform == WINDOWS_PLATFORM_KEY


def platform_key() -> str:
    """本平台的帳本鍵。用 `sys.platform`（win32/darwin/linux）——見上方區塊註解：
    穩定、與 `is_native_windows()` 同詞彙、不隨 OS 版本升級長出新鍵。"""
    return sys.platform


def peer_platform_keys(current: str, ledger_keys: object) -> list[str]:
    """純函式（無 I/O）：在 `current` 平台上該回報哪些「對方平台」的欠債。

    ＝帳本內所有非本平台的鍵 ∪ 本平台的正規對照平台（後者即使帳本裡查無也要回報，
    因為「查無紀錄」本身就是要印出來的欠債——當成落後 0 才是假綠）。
    """
    keys = {k for k in (ledger_keys or ()) if isinstance(k, str) and k != current}
    peer = CANONICAL_PEER.get(current)
    if peer is not None and peer != current:
        keys.add(peer)
    return sorted(keys)


def native_platform_fingerprint() -> str:
    """平台指紋：記錄「這份原生證據是在哪個環境取得的」，供跨輪複審判讀。"""
    return f"{sys.platform} / {platform.version()}"


def head_sha() -> str | None:
    """當前 HEAD 的完整 sha；非 git repo／無 git／逾時皆回 None（＝誠實的未知）。

    絕不拋：帳本是取證輔助，不得反過來成為 runner 的新失敗來源（同 `_write_failure_log`
    的降級哲學）。回 None 時 `merge_native_ledger` 會**保留**帳本裡既有的 head，
    不用未知覆蓋已知。
    """
    try:
        r = subprocess.run(
            ["git", "-C", str(_REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    sha = (r.stdout or "").strip()
    return sha if r.returncode == 0 and sha else None


def source_fingerprint(text: str) -> str:
    """源碼 sha256。刻意先把 CRLF 正規化成 LF 再算：Windows checkout 若
    `core.autocrlf=true`，同一個 commit 的工作檔位元組與 macOS 不同——不正規化會讓
    帳本在兩平台之間**永遠**對不上，把 advisory 變成常亮噪音（本 repo 最怕的形態）。"""
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def tagged_decorator_qualnames(source: str, tag: str = WINDOWS_NATIVE_SKIP_TAG) -> set[str]:
    """純函式（無 I/O）：AST 解析一份測試模組原始碼，回傳「decorator 參數內含 tag
    的字串常數」之 class／function qualname 集合（class 級標籤代表其下所有測試）。

    為何走 AST 而非整檔字串搜尋：`test_run_root_unittests.py::
    ReportWindowsNativeSkipsTest._run_fixture` 在**函式 body 內**造一個帶標籤的假
    skip reason，整檔字串搜尋會把該檔所有測試誤記成「已原生驗證」——正好是本機制
    最不能出的錯（記錄不實的正面事實比不記錄更糟）。只看 `decorator_list` 子樹裡的
    字串常數，語意上正好對齊「這支測試被標籤化的 skip 裝飾器管著」。

    刻意不遞迴進 function body：unittest 的 test id 只有 `模組.類別.方法` 三層，
    巢狀在函式內的 class 永遠不會被 discover 成測試。

    已實測涵蓋：`@unittest.skipUnless(cond, "…")` 字面值（含相鄰字串隱式串接、
    f-string 的字面片段）、方法級與 class 級標籤、標籤只出現在函式 body 內時不誤判。
    已實測不涵蓋：reason 寫成模組級變數／函式回傳值（AST 只看得到 Name，看不到值）
    ——現行帶標籤的測試皆為字面值寫法。其他寫法未窮舉。
    """
    out: set[str] = set()

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if not isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            qual = f"{prefix}{child.name}"
            if any(
                isinstance(const, ast.Constant)
                and isinstance(const.value, str)
                and tag in const.value
                for dec in child.decorator_list
                for const in ast.walk(dec)
            ):
                out.add(qual)
            if isinstance(child, ast.ClassDef):
                walk(child, f"{qual}.")

    walk(ast.parse(source), "")
    return out


def _iter_test_cases(suite: unittest.TestSuite) -> Iterator[unittest.TestCase]:
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _iter_test_cases(item)
        elif item is not None:  # run() 後的 suite 內是 None（見 run_with_floor 的註解）
            yield item


def _module_tag_index(mod_name: str, tag: str) -> tuple[set[str], str, str] | None:
    """讀一個已被 discover import 的測試模組，回傳 (帶標籤 qualname 集合, repo 相對
    路徑, 源碼 sha)。模組沒有 `__file__`（動態產生）或讀不到源碼時回 None。"""
    path = getattr(sys.modules.get(mod_name), "__file__", None)
    if path is None:
        return None
    resolved = Path(path).resolve()
    try:
        source = resolved.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        rel = resolved.relative_to(_REPO_ROOT).as_posix()
    except ValueError:  # fixture 造在系統暫存目錄的模組不在 repo 內
        rel = resolved.as_posix()
    if tag not in source:
        # 絕大多數測試模組不帶標籤，先做一次廉價字串排除再解 AST／算 sha
        # （帶標籤者是少數，其餘模組不必付 parse 成本）。
        return set(), rel, ""
    return tagged_decorator_qualnames(source, tag), rel, source_fingerprint(source)


def windows_native_tagged_facts(
    suite: unittest.TestSuite, tag: str = WINDOWS_NATIVE_SKIP_TAG
) -> list[dict[str, object]]:
    """把 suite 內「原始碼被 tag 標籤管著」的測試整理成本環境事實清單。

    每筆：`{"id", "file"（repo 相對 posix 路徑）, "source_sha256", "skipped_here"}`。

    `skipped_here` 讀的是 `__unittest_skip__`：`skipUnless(False, …)` 會在函式／類別
    上設這個屬性，條件為真時則原封不動回傳被裝飾對象（沒有該屬性）——因此不必真的
    跑測試就能得知「這支在本環境會不會被 skip」，本函式故可（且必須）在 run() 前呼叫。

    🔴 呼叫時機見 `run_with_floor` 內的註解：務必在 `TestSuite.run()` 之前。
    """
    facts: list[dict[str, object]] = []
    per_module: dict[str, tuple[set[str], str, str] | None] = {}
    for test in _iter_test_cases(suite):
        cls = type(test)
        if cls.__module__ not in per_module:
            per_module[cls.__module__] = _module_tag_index(cls.__module__, tag)
        index = per_module[cls.__module__]
        if index is None:
            continue
        tagged_quals, rel, sha = index
        method_name = getattr(test, "_testMethodName", "")
        if not ({cls.__qualname__, f"{cls.__qualname__}.{method_name}"} & tagged_quals):
            continue
        method = getattr(cls, method_name, None)
        facts.append(
            {
                "id": test.id(),
                "file": rel,
                "source_sha256": sha,
                "skipped_here": bool(
                    getattr(cls, "__unittest_skip__", False)
                    or getattr(method, "__unittest_skip__", False)
                ),
            }
        )
    return facts


def platform_block(ledger: dict, key: str) -> dict | None:
    """純函式（無 I/O）：取某平台的帳本區塊；查無回 None（≠空區塊，見 `peer_platform_keys`
    的理由：「查無紀錄」是誠實的未知，當成落後 0 是假綠）。

    schema 1（僅 Windows、頂層 `verified`、無 head）自動視為 win32 區塊且 head=None：
    舊帳本不會因為升 schema 而讓已取得的原生證據一夜歸零，而 head 缺席如實回報未知。
    """
    plats = ledger.get("platforms") if isinstance(ledger, dict) else None
    if isinstance(plats, dict) and isinstance(plats.get(key), dict):
        return plats[key]
    if key == WINDOWS_PLATFORM_KEY and isinstance((ledger or {}).get("verified"), list):
        return {"head": None, "last_run_on": "", "verified": ledger["verified"]}
    return None


def platform_entries(ledger: dict, key: str) -> dict[str, dict]:
    """純函式（無 I/O）：某平台區塊內 `verified` 的 id → 條目對照表（壞格式條目略過）。"""
    block = platform_block(ledger, key) or {}
    return {
        entry["id"]: entry
        for entry in (block.get("verified") or [])
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }


def merge_native_ledger(
    existing: dict,
    facts: list[dict[str, object]],
    fingerprint: str,
    head: str | None = None,
    key: str | None = None,
) -> dict:
    """純函式（無 I/O）：把本次事實併進既有帳本的**本平台區塊**，回傳合併後內容。

    **合併而非覆寫**：某台 Windows 機器若缺 pwsh，只有部分標籤測試跑得到——覆寫
    會把其他幾支「先前確實取得過」的原生證據刪掉，跨輪累積就此歸零。同理，寫本平台
    區塊時**絕不碰其他平台的區塊**（對方平台的欠債紀錄不是本平台能代為宣稱的事實）。

    **同一份源碼＋同一個 commit 再跑一次不改帳本**：條目的 (file, source_sha256) 與
    head 都與既有完全相同時，整個區塊原封不動保留（連 `last_run_on` 都留舊值）。這是
    刻意的——否則平台指紋每次 OS 小版更新都讓帳本產生一筆零資訊量的 diff，「每次跑
    測試都出現 diff」的噪音會讓人開始無視這個檔案（本 repo 已在 MIN_TESTS 上付過這種
    學費）。反之 head 前進了就更新（那筆 diff 資訊量非零：它就是量化積欠的依據）。

    `head=None`（非 git repo／git 不可用）時**保留既有 head**：不用未知覆蓋已知。
    """
    key = key or platform_key()
    plats = {
        k: v
        for k, v in ((existing.get("platforms") or {}) if isinstance(existing, dict) else {}).items()
        if isinstance(v, dict)
    }
    old_block = platform_block(existing or {}, key) or {}
    entries = dict(platform_entries(existing or {}, key))
    changed = False
    for fact in facts:
        if fact["skipped_here"]:  # 本環境沒跑到＝本次產不出正面證據，不動既有條目
            continue
        old = entries.get(fact["id"])
        if (
            old is not None
            and old.get("file") == fact["file"]
            and old.get("source_sha256") == fact["source_sha256"]
        ):
            continue
        entries[fact["id"]] = {
            "id": fact["id"],
            "file": fact["file"],
            "source_sha256": fact["source_sha256"],
            "verified_on": fingerprint,
        }
        changed = True
    new_head = head if head is not None else old_block.get("head")
    if changed or new_head != old_block.get("head") or not old_block:
        plats[key] = {
            "head": new_head,
            "last_run_on": fingerprint,
            "verified": [entries[i] for i in sorted(entries)],
        }
    else:
        plats[key] = old_block
    return {
        "schema": NATIVE_LEDGER_SCHEMA,
        "_why": _NATIVE_LEDGER_WHY,
        "platforms": {k: plats[k] for k in sorted(plats)},
    }


def record_native_verification(
    facts: list[dict[str, object]], path: Path | None = None
) -> bool:
    """把本次真的跑到的平台閘門測試 ＋ 當時的 HEAD 寫入帳本；回傳「是否真的寫檔」。

    帳本語意精確定義：記的是「這支測試在本平台上**真的被執行**（沒被 skip）、當時的
    源碼 sha 為 X」，**不是**「通過」——刻意不看 result 的成敗，因為執行失敗時 runner
    的 rc 已經是 1、不可能被靜默忽略，而 DEF-101-348 的實害恰恰是「連跑都沒跑到卻全
    APPROVE」。把成敗混進來只會讓「跑到了」這個唯一要留存的事實變得難判讀；更實際的
    理由是：平台一旦轉紅（R57 開機到 Windows 當天就是這情形）帳本會從此停止前進，
    「沒跑」與「跑了但紅」被混成同一個訊號，而後者的 rc=1 本來就擋得住任何閘門。

    **兩平台都寫**（本輪由「只在 Windows 寫」改為對稱）：mac 側依定義產不出 Windows
    專屬測試的正面證據（那幾支在 mac 上必然 skip、`verified` 會是空的），但 mac 這塊
    的 `head` 本身就是「mac 最後一次跑全套是在哪個 commit」——那是 Windows 側開工時
    唯一能反向量化 mac 欠債的事實。只寫單邊等於讓不對稱永遠只能單向可見。

    內容無實質變化（sha、id 集合、head 都沒動）時不寫。寫檔失敗只印警告、不拋、不影響
    rc——沿用本檔 `_write_failure_log` 的既有慣例：取證輔助不得反過來變成新的失敗來源。
    """
    target = path or NATIVE_LEDGER
    if not facts:
        # `not facts`＝這批測試裡沒有任何標籤測試 ⇒ 沒有正面事實可記，不必動檔。
        # 這條同時堵住一個實測到的污染：`run_with_floor` 自己的 fixture 自測
        # （`RunRootUnittestsTest`，跑的是系統暫存目錄裡零標籤的假測試）會走完整條
        # runner 路徑，若不短路，它會把一份空帳本（本輪＝只有 head 的區塊）寫到
        # **真正**的帳本路徑上（實測：先刪掉帳本再單跑 test_at_floor_runs_and_passes，
        # 檔案確實被重建成空帳本）。本輪拿掉了 `is_native_windows()` 那半個守衛
        # （改為兩平台都寫），這半條守衛因此從「其中一道」升格為**唯一**的污染防線。
        return False
    existing: dict = {}
    if target.is_file():
        try:
            loaded = json.loads(target.read_text(encoding="utf-8"))
            existing = loaded if isinstance(loaded, dict) else {}
        except (OSError, ValueError) as exc:
            print(f"⚠️  平台驗證帳本讀取失敗（{exc}）——本次視為空帳本重建", file=sys.stderr)
    merged = merge_native_ledger(
        existing, facts, native_platform_fingerprint(), head_sha(), platform_key()
    )
    if merged == existing:
        return False
    try:
        # newline="\n"：Windows 文字模式預設寫 CRLF，會讓這份 tracked 檔在兩平台間
        # 反覆換行符 diff（正是上面刻意避免的噪音來源）。
        target.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"🪟 平台驗證帳本已更新：{target}（{platform_key()} 區塊，見 DEF-101-348 方向①）")
        return True
    except OSError as exc:
        print(f"⚠️  平台驗證帳本落檔失敗（{exc}）——不影響 rc", file=sys.stderr)
        return False


def native_evidence_gaps(
    facts: list[dict[str, object]], ledger: dict, native_now: bool
) -> list[str]:
    """純函式（無 I/O）：回傳「當前源碼缺少原生 Windows 驗證證據」的可行動訊息清單。

    判準綁源碼 sha、不綁日期（ADR-SD09-011）：
      * 本環境就是原生 Windows 且該測試在此**不會被 skip** ⇒ 它此刻正在真跑，證據
        新鮮，不查帳本。這一條是刻意的：帳本由 runner 在測試跑完後才寫，同一次執行
        內查到的必然是**上一次**的帳本——若這裡也查帳本，任何一次測試檔改動都會製造
        「同一份源碼要跑兩次才會綠」的假紅，而 windows CI 從乾淨 checkout 起跑更是
        永遠自我修不好（它不會 commit 帳本）。
      * 否則查帳本：查無該 id ⇒ 從未在原生 Windows 上驗證過（DEF-101-348 的原始
        實害）；有該 id 但 sha 不同 ⇒ 上次的原生驗證是對**舊源碼**做的。
    """
    # 標籤本身寫的是 `[WINDOWS-NATIVE-ONLY]`，故只有 win32 區塊能提供這批測試的證據
    # （mac 上那幾支必然 skip，mac 區塊的 verified 對它們永遠是空的）。
    recorded = platform_entries(ledger, WINDOWS_PLATFORM_KEY)
    gaps: list[str] = []
    for fact in sorted(facts, key=lambda f: str(f["id"])):
        if native_now and not fact["skipped_here"]:
            continue
        entry = recorded.get(fact["id"])
        if entry is None:
            gaps.append(
                f"{fact['id']}：帳本查無此測試 ⇒ 從未在原生 Windows 上真的跑過"
                f"（{WINDOWS_NATIVE_SKIP_TAG} 測試的驗證價值只在原生 Windows 上成立）"
            )
        elif entry.get("source_sha256") != fact["source_sha256"]:
            gaps.append(
                f"{fact['id']}：帳本記載的原生驗證針對 {fact['file']} 的舊源碼"
                f"（帳本 sha {str(entry.get('source_sha256'))[:12]} ≠ 現況 "
                f"{str(fact['source_sha256'])[:12]}）⇒ 現行源碼尚無原生驗證證據"
            )
    return gaps


def main() -> int:
    if not _TESTS_DIR.is_dir():
        print(f"❌ 測試目錄不存在：{_TESTS_DIR}", file=sys.stderr)
        return 1
    return run_with_floor(_TESTS_DIR, MIN_TESTS)


if __name__ == "__main__":
    sys.exit(main())
