#!/usr/bin/env python3
"""`[WINDOWS-NATIVE-ONLY]` skip 標籤的可見度與完整性判準（R43／R67-F11／R72）。

🔴 為何獨立成模組而不是留在 `tools/run_root_unittests.py`（同 `tools/lib/ci_liveness.py`
的先例，理由同構）：
  ① **內聚**——本模組的全部內容是同一件事：「哪些 skip 在這次沒被驗證、哪些該被標記
     卻沒被標記」。runtime 面（讀 `unittest.TestResult`）與靜態面（讀原始碼 AST）是
     同一個判準的兩種載具，共用同一份標籤／關鍵詞／述詞常數，放在一起才不會各自漂移。
  ② **LOC**——`tools/run_root_unittests.py` 受
     `AutoClaude/tools/check_loc_budget.py` 的 SPECIAL_FILES 棘輪管制（R69 P3 納管，
     門檻＝納管當下行數、只准往下改），R72 動工前實測**恰好卡滿**。該棘輪的
     override_reason 逐字寫著「先刪死碼／抽共用模組（先例：tools/lib/ci_liveness.py）」
     ——本模組即依該指示抽出，不是為了繞過門檻而搬家。

判準的兩個面（互補，缺一即有結構性瞎點）：
  · **runtime**（`untagged_windows_like_skips`）：看本次真的 skip 了什麼。只在**非**
    Windows 上說話，理由見該函式 docstring（在 Windows 上照掃必然假紅）。
  · **靜態**（`untagged_windows_skip_decorators`）：讀原始碼、看 skip 條件的**方向**，
    與「現在跑在哪個平台」無關 ⇒ 三個平台都說話，補上 runtime 面在 Windows 的早退。
"""
from __future__ import annotations

import ast
import os
import re
import sys
import unittest
from collections.abc import Mapping
from pathlib import Path
from typing import NamedTuple

# R43 Architect P1（DEF-101-348 方向①）：DEF-101-343~345 揪出 5 支 Windows 專屬
# 回歸測試連續 5+ 輪「全 APPROVE」卻從未在原生 Windows 上真正跑過——`unittest`
# 預設摘要（`skipped=N`）不區分「一般性 skip」與「這支測試的驗證價值僅在原生
# Windows 上成立、這次環境不符沒跑」，是造成該漏洞連續多輪未被發現的根因之一。
# 凡 skip 理由帶此標籤的測試，於摘要末另印一段醒目清單，供複審者一眼辨識。
WINDOWS_NATIVE_SKIP_TAG = "[WINDOWS-NATIVE-ONLY]"

# ── R74：反方向的對稱標籤（PKG-4 E／F；使用者第 3 點的「反之亦然」那一向）─────────
#
# 🔴 WHY 非上不可：`WINDOWS_NATIVE_SKIP_TAG` 這一整套（標籤 ＋ 可見度摘要 ＋ 漏標
# 完整性鎖 ＋ 靜態方向判準）**只照亮一個方向**。R59 就已在 `report_all_skips` 的
# docstring 記下反方向的存在（「因為我們正跑在 Windows，所以失去了某些覆蓋」），
# 當時的處置是「全部印出來、把分類交給讀取者」——那解決了可見度，但沒解決**可判讀性**：
# 在 Windows 上跑時 skip 的那一批，複審者無法分辨哪幾筆是「POSIX 語意本來就不適用，
# 不是損失」、哪幾筆是「真的少驗了東西」。R74 實查：Windows 側的 skip 站點**一筆標籤
# 都沒有**，而 Windows 專屬那一側有整套機械物 ⇒ 兩個方向的待遇不對稱，且不對稱的
# 那一側正好是這台開發機每天在跑的那一側。
#
# 標籤語意（與 Windows 側嚴格對偶）：
#   `[POSIX-NATIVE-ONLY]`＝這支測試的驗證價值只在非 Windows（POSIX）平台成立，
#                          **這次跑在 Windows 上所以沒跑**。
#   `[MAC-NATIVE-ONLY]`  ＝更窄的 darwin 專屬版（`brew`／`launchd`／BSD `ps` 這類）。
# 兩者都被視為「已標籤」——判準只問「作者有沒有標明這是哪一側的覆蓋損失」，
# 不強迫把 macOS 專屬硬寫成 POSIX 通則。
POSIX_NATIVE_SKIP_TAG = "[POSIX-NATIVE-ONLY]"
MAC_NATIVE_SKIP_TAG = "[MAC-NATIVE-ONLY]"
NON_WINDOWS_SKIP_TAGS: tuple[str, ...] = (POSIX_NATIVE_SKIP_TAG, MAC_NATIVE_SKIP_TAG)

# R67-F11：標籤**完整性**前瞻鎖的關鍵詞面。
#
# WHY（為何光有上面那個標籤還不夠）：`report_windows_native_skips` 只看得到「已經
# 帶標籤」的 skip，對「該帶而沒帶」結構性盲目——它就是那個低報的來源本身。R67
# 動工時實測：macOS 上 15 支 skip **全數**為 Windows 專屬，標題卻只印 10，低報 33%；
# 其中 4 支由 R65（`01fd8c3`）、1 支由 R66（`8654975`）落地時漏標。R59 已在
# `tools/tests/test_install_windows_nightly.py` 逐字記過同一形態（「因該 skip 未帶
# `[WINDOWS-NATIVE-ONLY]` 標籤而被 run_root_unittests.py 的可見度機制漏掉」），
# 兩輪後原地復發 ⇒ 這是持續性漏洞，不是一次性疏失，**必須有機械物**。
#
# 判準邊界（誠實劃界）：關鍵詞掃描是啟發式，抓的是「reason 講的明明是 Windows 語意
# 卻沒帶標籤」。它抓不到「reason 完全沒提任何 Windows 字眼的 Windows-only skip」
# （例：只寫「需要具名核心物件」）——那半邊仍是人審責任。
_WINDOWS_LIKE_SKIP_HINTS = ("windows", "win32", "pathext", "bash.exe", "mutex", "ntfs")

# 具名豁免：reason 命中關鍵詞但**確實不是** Windows 專屬的 skip（鍵＝test id，
# 值＝理由）。現況為空集合。刻意保留這個空常數而非省略——例外必須逐支具名並附
# 理由，不接受「整批略過」的通用開關（同 `_COLLECTION_EXEMPT` 既有慣例）。
_WINDOWS_SKIP_TAG_EXEMPT: dict[str, str] = {}


def all_skips(result: unittest.TestResult) -> list[tuple[str, str]]:
    """純函式（無 I/O 副作用，比照 `windows_native_skips` 慣例）：回傳本次全部
    skip 的 `(test_id, reason)`，含已被 `WINDOWS_NATIVE_SKIP_TAG` 標記者。"""
    return [(test.id(), reason) for test, reason in result.skipped]


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


def report_all_skips(result: unittest.TestResult) -> list[tuple[str, str]]:
    """印出本次**全部** skip 的 id 與理由。

    WHY（DEF-101-510，R59 於真 Windows 11 實機量到）：`report_windows_native_skips`
    只照亮**一個方向**——「這支測試只在原生 Windows 才有驗證價值，這次環境不符」。
    反方向（**因為我們正跑在 Windows，所以失去了某些覆蓋**）完全沒有標籤、沒有摘要、
    沒有計數，只會併進 `unittest` 預設的 `skipped=N` 一個數字裡。R59 實測：本 runner
    在 Windows 11 上 `skipped=11`，**11 支全部無標籤**，其中兩支是真正的覆蓋損失而非
    平台語意使然——
      ① `test_install_windows_nightly` 的語法解析因**當時那台機器只裝了 5.1、沒有
         pwsh 7** 而 skip（DEF-101-509，一支 Windows 專屬腳本的語法閘門恰在 Windows
         上不跑）。🔴 **R73 訂正（DEF-101-777）**：這句原本把量測當時那台機器缺 pwsh 7
         這件事寫成了本檔的常數。2026-08-04 該機器裝上 PowerShell 7.6.4 後此前提為假、
         該項也不再 skip，而讀者仍會照舊句以為它還在 skip。
         引擎可用性是**機器屬性**，一律現查 `tools/tests/_ps_engine.py::available_engines()`。
      ② `test_env_changed_removes_cache_dir_and_symlink` 因無 symlink 權限
         （`[WinError 1314]`，標準未提權 Windows 11 的預設狀態）而 skip。
    這正是 DEF-101-343~345 那條「Windows 專屬測試連續 5+ 輪全 APPROVE 卻從未真的在
    Windows 跑過」的缺陷類別，只是方向相反；R43 只補了一半。

    設計取捨（刻意選最笨的做法）：不再發明第二套標籤分類（那需要為每一支 skip 判定
    「by-design 平台語意」vs「環境降級」，判準本身就會成為新的漂移來源），改為**全部
    印出來**，把分類交給讀取者。成本是每輪多 N 行輸出（實測 11 行），換到的是
    「任何 skip 都不可能再隱形」——與紀律 #2「log 必須含完整統計，不信任預設 dump」
    同一精神，也等於把 pytest `-rs` 早就免費提供的東西補進這個 unittest runner。
    """
    entries = all_skips(result)
    if entries:
        print(f"ℹ️  本次 skip 明細（共 {len(entries)} 支；DEF-101-510 要求全列不得只印計數）：")
        for test_id, reason in entries:
            # R74：`[已標籤]` 原本只認 Windows 側標籤，於是在 Windows 上跑時整批
            # POSIX 專屬 skip 一律顯示 `[未標籤]`——那個字面上正確、實際上誤導：
            # 它讓「作者已標明這是 POSIX 側覆蓋損失」與「完全沒人分類過」長得一樣。
            tag = next(
                (t for t in (WINDOWS_NATIVE_SKIP_TAG, *NON_WINDOWS_SKIP_TAGS) if t in reason),
                None,
            )
            mark = f"[已標籤 {tag}]" if tag else "[未標籤]"
            print(f"   - {mark} {test_id}\n       理由：{reason}")
    return entries


def untagged_windows_like_skips(
    result: unittest.TestResult, *, on_windows: bool | None = None
) -> list[tuple[str, str, str]]:
    """純函式（無 I/O 副作用）：reason 講的是 Windows 語意、卻沒帶標籤的 skip。

    回傳 `(test_id, 命中的關鍵詞, reason)`。

    **只在非 Windows 平台上說話**（`on_windows` 預設取 `os.name == "nt"`，參數化僅
    供測試注入）。理由不是「Windows 上不想管」，而是標籤語意在那裡不適用：
    `[WINDOWS-NATIVE-ONLY]` 說的是「這支測試只在原生 Windows 才有驗證價值，**這次
    環境不符所以沒跑**」——在 Windows 上這類測試根本不會 skip。反過來，Windows 上
    真正會 skip 的是 POSIX-only 測試，而它們的 reason 十之八九也會提到 "Windows"
    （例如「Windows 無 symlink 權限」），照掃必然假紅。反方向的可見度由
    `report_all_skips`（DEF-101-510，全列不分類）承接，不在本鎖射程內。

    🔴 R72：這個早退**不是**可以刪掉的（刪了就是整片假紅），但它讓三道 Windows 側
    閘門成為同一個瞎點的三份複本。補位的是本模組下半部的**靜態方向感知掃描**——
    那一面不看當前平台，故在 Windows 上照樣會說話。
    """
    if on_windows is None:
        on_windows = os.name == "nt"
    if on_windows:
        return []
    out: list[tuple[str, str, str]] = []
    for test_id, reason in all_skips(result):
        if WINDOWS_NATIVE_SKIP_TAG in reason or test_id in _WINDOWS_SKIP_TAG_EXEMPT:
            continue
        lowered = reason.lower()
        hit = next((kw for kw in _WINDOWS_LIKE_SKIP_HINTS if kw in lowered), None)
        if hit is not None:
            out.append((test_id, hit, reason))
    return sorted(out)


def report_untagged_windows_like_skips(result: unittest.TestResult) -> list[tuple[str, str, str]]:
    """印出漏標籤者並回傳清單（非空 ⇒ 呼叫端須讓 rc 為 1，見 `run_with_floor`）。"""
    offenders = untagged_windows_like_skips(result)
    if offenders:
        print(
            f"❌ {len(offenders)} 支 skip 的理由講的是 Windows 專屬語意，卻沒帶 "
            f"{WINDOWS_NATIVE_SKIP_TAG} 標籤——上面那行「N 個 Windows 專屬測試未在原生 "
            f"Windows 環境驗證」會因此**低報**，複審者會低估本輪未被驗證的 Windows 面"
            f"（R67-F11：實測曾低報 33%）：",
            file=sys.stderr,
        )
        for test_id, hit, reason in offenders:
            print(f"   - {test_id}（命中關鍵詞 {hit!r}）\n       理由：{reason}", file=sys.stderr)
        print(
            f"   修法：把 {WINDOWS_NATIVE_SKIP_TAG} 加在該 skip reason 的最前面。若它"
            "**確實不是** Windows 專屬，請把 test id 具名加入 "
            "run_root_unittests._WINDOWS_SKIP_TAG_EXEMPT 並註明理由。",
            file=sys.stderr,
        )
    return offenders


# ── 靜態（不分平台）方向感知掃描 ─────────────────────────────────────────────
#
# 「條件為真 ⇒ 執行環境是 Windows」的述詞登記表。判準：
#   · `skipUnless(<Windows 述詞>)` → 非 Windows 才 skip → 正是標籤語意 ⇒ **該**帶
#   · `skipIf(<Windows 述詞>)`     → Windows 才 skip（POSIX-only 測試）⇒ **不該**帶
# 方向由 decorator 種類 ＋ 條件表達式的原始碼文字判定，與「現在跑在哪個平台」無關。
# 實測：加方向判準前，同一份樹報 7 筆假紅（全是 `skipIf(os.name == "nt")` 的
# POSIX-only 測試）；加之後歸零——方向不是精緻化，它是這道鎖能否存在的前提。
#
# 🔴 **漏登記＝fail-open**：述詞沒登記在本表 ⇒ 方向判不出來 ⇒ 該站點靜默不報。
# 這個 fail-open 由 `unregistered_windows_like_predicates()` 收口——凡條件文字
# 看起來像 Windows（`_WINDOWS_PREDICATE_SUSPECT_RE`）卻未登記者一律點名並判紅，
# 所以新增一種判斷 Windows 的寫法時，忘了登記會當場紅、不會靜默漏掉。
_WINDOWS_SKIP_PREDICATE_MARKERS: tuple[str, ...] = (
    'os.name == "nt"', "os.name == 'nt'",
    'platform.system() == "Windows"', "platform.system() == 'Windows'",
    'sys.platform == "win32"', "sys.platform == 'win32'",
    'sys.platform.startswith("win")', "sys.platform.startswith('win')",
    "_ps_windows_with_engine()",   # tools/tests/_ps_engine.windows_with_engine 的就地別名
    "_ps_windows_native_51()",     # 同上，windows_with_native_ps51 的就地別名
    "windows_with_native_ps51()",
    "windows_with_engine()",
    "_windows_pwsh_available()",   # tools/tests/test_bootstrap_ps1.py 的就地別名
)

# 「條件在 **Windows 上** 求值為 False」的述詞（R74 新增）。
#
# 🔴 WHY 判準要重寫成「這個述詞在 Windows 上是什麼值」，而不是「它是不是 Windows
# 述詞」：R72 的兩極模型（只有一張「是 Windows 述詞」的表）對否定形態**方向會算反**。
# R74 落地時當場實測到一筆：`skipif(not _windows_pwsh_available())` 的條件文字含有
# 已登記的 Windows 述詞，於是被判成「Windows 上會 skip」，而它實際的語意恰恰相反
# （非 Windows 才 skip，它是 Windows 專屬測試、且已正確帶 Windows 標籤）。方向算反
# 比判不出方向更糟：它會要求作者貼上**錯的**標籤。
# 改成「在 Windows 上的值」之後，`!=`／`not`／darwin 三類全部自然歸位：
#   `sys.platform != "darwin"` 在 Windows 上為真 ⇒ 屬 TRUE 表（並非判不出來）。
_NON_WINDOWS_SKIP_PREDICATE_MARKERS: tuple[str, ...] = (
    'os.name != "nt"', "os.name != 'nt'",
    'platform.system() != "Windows"', "platform.system() != 'Windows'",
    'sys.platform != "win32"', "sys.platform != 'win32'",
    'sys.platform == "darwin"', "sys.platform == 'darwin'",
    'platform.system() == "Darwin"', "platform.system() == 'Darwin'",
)

# 在 Windows 上求值為 True 的述詞（`_WINDOWS_SKIP_PREDICATE_MARKERS` ＋ darwin 的否定）。
_TRUE_ON_WINDOWS_MARKERS: tuple[str, ...] = (
    *_WINDOWS_SKIP_PREDICATE_MARKERS,
    'sys.platform != "darwin"', "sys.platform != 'darwin'",
    'platform.system() != "Darwin"', "platform.system() != 'Darwin'",
)

# 依 marker 長度遞減排序後逐一比對——**長度序是判準的一部分**，不是實作細節：
# `not sys.platform.startswith("win")` 內含 `sys.platform.startswith("win")`，
# 若比對順序不定，同一份原始碼可能被判成相反的方向。`not ` 前綴另由
# `_predicate_value_on_windows` 剝除並翻轉，故本表不必逐條登記否定形。
_PREDICATE_WINDOWS_VALUE: tuple[tuple[str, bool], ...] = tuple(
    sorted(
        [(m, True) for m in _TRUE_ON_WINDOWS_MARKERS]
        + [(m, False) for m in _NON_WINDOWS_SKIP_PREDICATE_MARKERS],
        key=lambda item: -len(item[0]),
    )
)

# 「看起來像 Windows 述詞」的粗網。**只**用來抓上表的漏登記，不參與任何判紅／放行
# 決策——粗網天生會有偽陽性，讓它直接判紅會把本鎖變成噪音來源。
_WINDOWS_PREDICATE_SUSPECT_RE = re.compile(r"windows|win32|\bnt\b|darwin", re.IGNORECASE)

# 掃描面的快取目錄（不進版控，列進來會讓兩邊基準不同）。
_CACHE_DIR_NAMES = frozenset({"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"})


class SkipSite(NamedTuple):
    """原始碼裡的一個 `@skipUnless`／`@skipIf` 站點（靜態抽取，未執行任何測試）。"""

    file: str        # 相對掃描根的檔名
    lineno: int      # decorator 所在行
    target: str      # 被裝飾的 class／function 名
    decorator: str   # "skipUnless" 或 "skipIf"
    condition: str   # 條件表達式的原始碼文字（判方向用）
    reason: str      # skip reason 的字面字串

    def label(self) -> str:
        return f"{self.file}:{self.lineno} {self.target}"


# skip 機制的呼叫名 → 「條件為真時是否 skip」。
#   `skipIf`／pytest 的 `skipif`：條件為真 ⇒ skip。
#   `skipUnless`：條件為真 ⇒ **不** skip。
# 🔴 R74 把 pytest 形態納入（PKG-4 D）：R72 建立的方向感知判準只認 `unittest` 的
# decorator，實測「同一個缺陷改寫成 `@pytest.mark.skipif(...)` 即零訊號」——而本 repo
# 三棵測試樹裡 pytest 形態並非邊角料（R74 實測 337 支測試檔／90 個 skip 站點中，
# `pytest.mark.skipif` 佔 22 個，且其中 11 個條件就是平台判斷）。一道只認一種測試
# 框架的方向判準，對「換框架寫同一個缺陷」完全沒有防護力。
_SKIP_CALL_SKIPS_WHEN_TRUE: dict[str, bool] = {
    "skipIf": True,
    "skipif": True,       # pytest.mark.skipif（reason 走 keyword，見 `_skip_reason_of`）
    "skipUnless": False,
}


def _call_name(func: ast.AST) -> str:
    return str(getattr(func, "attr", None) or getattr(func, "id", None) or "")


def _skip_reason_of(call: ast.Call) -> str | None:
    """取 skip 的 reason 字面字串；取不到（變數／f-string／`.format()`）回 None。

    `unittest` 把 reason 放在**位置引數**、pytest 放在 **`reason=` keyword**——
    R72 版只讀 `args[1]`，於是每一個 pytest 站點都在 `len(deco.args) < 2` 那行被
    整個丟掉（連「未登記述詞」的漏登記守衛都看不到它）。兩種形態都要認。
    """
    candidates: list[ast.AST] = list(call.args[1:2])
    for kw in call.keywords:
        if kw.arg == "reason":
            candidates = [kw.value]
    if not candidates:
        return None
    try:
        reason = ast.literal_eval(candidates[0])
    except Exception:  # noqa: BLE001 — 非字面值一律略過，見 docstring
        return None
    return reason if isinstance(reason, str) else None


def _enclosing_target(tree: ast.Module, node: ast.AST) -> str:
    """`node` 最近的外層 class／function 名；模組層 skip 則回賦值目標名或 `<module>`。

    WHY 不再只走 `decorator_list`（R74）：本 repo 實際存在三種等價寫法——直接當
    decorator、先存成模組常數再當 decorator（`_WINDOWS_PATHEXT_SKIP = pytest.mark.
    skipif(...)`，`AISDLC_SDD/scripts/tests/` 就是這樣寫的）、以及模組級
    `pytestmark = pytest.mark.skipif(...)`（整檔 skip，覆蓋面最大的那一種）。
    只走 decorator_list 會漏掉後兩種，而後兩種的**射程比 decorator 大**。
    """
    best: tuple[int, str] | None = None
    for parent in ast.walk(tree):
        if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            end = getattr(parent, "end_lineno", None) or parent.lineno
            # 🔴 起點必須含 decorator 行：`FunctionDef.lineno` 指的是 `def` 那一行，
            # **不含** decorator，於是 decorator 上的 skip 呼叫（最常見的形態）落在
            # 區間外、被歸成 `<module>`。實測後果＝訊息指不到那支測試，複審者拿到
            # 站點標籤卻找不到對象。
            start = min([parent.lineno, *(d.lineno for d in parent.decorator_list)])
            if start <= node.lineno <= end:
                if best is None or start > best[0]:
                    best = (start, parent.name)
    if best is not None:
        return best[1]
    for stmt in ast.walk(tree):
        if isinstance(stmt, ast.Assign) and stmt.value is node:
            names = [t.id for t in stmt.targets if isinstance(t, ast.Name)]
            if names:
                return names[0]
    return "<module>"


def skip_decorator_sites(sources: Mapping[str, str]) -> list[SkipSite]:
    """純函式（無 I/O 副作用，比照 `windows_native_skips` 慣例）：從
    `{檔名: 原始碼}` 抽出所有 reason 為**字面字串**的 skip 站點。

    reason 取不到字面值時（變數、f-string、`.format()`）**略過而不猜**——本掃描
    判的是「寫在原始碼裡的那串話」，取不到就沒有可判的東西。這是刻意的判準邊界，
    不是遺漏：那類站點的可見度仍由 runtime 的 `report_all_skips` 承接。

    R74：改走「全樹找 skip 呼叫」而非「走 decorator_list」，理由見
    `_enclosing_target`；`decorator` 欄對 pytest 的 `skipif` 保留原名，方向由
    `_SKIP_CALL_SKIPS_WHEN_TRUE` 決定（不改名成 `skipIf`——訊息要能對回原始碼）。
    """
    sites: list[SkipSite] = []
    for name, src in sorted(sources.items()):
        tree = ast.parse(src, filename=name)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            kind = _call_name(node.func)
            if kind not in _SKIP_CALL_SKIPS_WHEN_TRUE:
                continue
            reason = _skip_reason_of(node)
            if reason is None:
                continue
            sites.append(SkipSite(
                file=name,
                lineno=node.lineno,
                target=_enclosing_target(tree, node),
                decorator=kind,
                condition=ast.get_source_segment(src, node.args[0]) or "",
                reason=reason,
            ))
    return sorted(sites, key=lambda s: (s.file, s.lineno))


def _predicate_value_on_windows(condition: str) -> bool | None:
    """該述詞在 **Windows 上** 求值為 True／False；未登記則 None（fail-open，由
    `unregistered_windows_like_predicates` 收口）。

    先剝 `not `／`not (` 前綴並翻轉，再以長度序比對登記表（見
    `_PREDICATE_WINDOWS_VALUE` 的 WHY）。
    """
    text = condition.strip()
    flip = False
    while text.startswith("not "):
        flip = not flip
        text = text[len("not ") :].strip()
        if text.startswith("(") and text.endswith(")"):
            text = text[1:-1].strip()
    for marker, value in _PREDICATE_WINDOWS_VALUE:
        if marker in text:
            return (not value) if flip else value
    return None


def _is_windows_predicate(condition: str) -> bool:
    """「這個述詞的方向判得出來嗎」——`unregistered_*` 的「已登記」判準。

    名稱沿用 R72（大量既有引用與訊息文字指向它）；語意自 R74 起是「已登記」而非
    「指向 Windows」，因為登記表現在同時容納兩種值（見 `_predicate_value_on_windows`）。
    """
    return _predicate_value_on_windows(condition) is not None


def skipped_platform(site: SkipSite) -> str | None:
    """這個站點**在哪個平台上會被 skip**：`"windows"`／`"non-windows"`／None（判不出）。

    方向＝「述詞在 Windows 上的值」×「這個 skip 機制是條件為真時 skip 還是為假時
    skip」。這是 R72 方向感知判準的完整化：R72 只有「skipUnless × 是 Windows 述詞」
    一格，其餘三格靜默判不出方向（fail-open），而 fail-open 正是這套機械物存在的理由。
    """
    value_on_windows = _predicate_value_on_windows(site.condition)
    if value_on_windows is None:
        return None
    skips_when_true = _SKIP_CALL_SKIPS_WHEN_TRUE.get(site.decorator)
    if skips_when_true is None:
        return None
    skipped_on_windows = value_on_windows == skips_when_true
    return "windows" if skipped_on_windows else "non-windows"


def untagged_windows_skip_decorators(
    sources: Mapping[str, str],
) -> list[tuple[str, str, str]]:
    """純函式：靜態找出「該帶 `[WINDOWS-NATIVE-ONLY]` 而沒帶」的 skip decorator。

    回傳 `(站點, 命中的關鍵詞, reason)`，形狀刻意與 runtime 的
    `untagged_windows_like_skips` 一致（同一個判準的兩種載具，訊息與讀法可共用）。

    判準三條同時成立才算違規：
      ① `skipUnless(<已登記的 Windows 述詞>)`——方向對（非 Windows 才 skip）；
      ② reason 命中 `_WINDOWS_LIKE_SKIP_HINTS`——講的確實是 Windows 語意；
      ③ reason 未帶 `WINDOWS_NATIVE_SKIP_TAG`。
    `skipIf(<Windows 述詞>)`（POSIX-only 測試）**不**在射程內——那類 reason 幾乎
    必然提到 Windows，照掃就是 runtime 那道鎖在 Windows 上早退所要避開的假紅。

    為何**不**另設具名豁免面（與 `_WINDOWS_SKIP_TAG_EXEMPT` 的取捨差異）：三條判準
    合起來已經等同「這支測試只在原生 Windows 才有驗證價值」的定義本身，偽陽性空間
    近乎為零；先開一個沒有已知用例的逃生門，只會多一個沒人看守的靜默出口。真的撞到
    偽陽性時，正確的修法是改述詞或改 reason 措辭，而不是把它登記成例外。
    """
    out: list[tuple[str, str, str]] = []
    for site in skip_decorator_sites(sources):
        # R74：判準由「`skipUnless` ＋ Windows 述詞」改為「**方向算出來是「非 Windows
        # 上才 skip」**」——等價於原判準，但同時涵蓋 `skipif(<非 Windows 述詞>)`
        # 這個 pytest 側的等價寫法（原判準對它零訊號）。
        if skipped_platform(site) != "non-windows":
            continue
        if WINDOWS_NATIVE_SKIP_TAG in site.reason:
            continue
        lowered = site.reason.lower()
        hit = next((kw for kw in _WINDOWS_LIKE_SKIP_HINTS if kw in lowered), None)
        if hit is not None:
            out.append((site.label(), hit, site.reason))
    return sorted(out)


def untagged_non_windows_skip_decorators(
    sources: Mapping[str, str],
) -> list[tuple[str, str]]:
    """純函式：靜態找出「在 Windows 上會 skip、卻沒標明是哪一側覆蓋損失」的站點。

    回傳 `(站點, reason)`。這是 `untagged_windows_skip_decorators` 的**對稱物**
    （R74／PKG-4 E‧F）。

    🔴 判準刻意**不**加關鍵詞條件（與 Windows 側的取捨差異，必須寫下來）：Windows 側
    要求 reason 命中 `_WINDOWS_LIKE_SKIP_HINTS` 才判違規，是因為那一側的動機是「reason
    講的明明是 Windows 語意卻沒帶標籤」。本側的動機不同——複審者的問題是「在 Windows
    上跑掉的這一批，哪幾筆是真的少驗了東西」，而**方向本身就是判準**：只要方向是
    「Windows 上會 skip」，作者就有義務標明它屬於哪一類。加關鍵詞只會讓「reason 寫得
    含糊」變成免責條款，而 reason 寫得含糊正是要治的病。
    """
    return sorted(
        (site.label(), site.reason)
        for site in skip_decorator_sites(sources)
        if skipped_platform(site) == "windows"
        and not any(tag in site.reason for tag in NON_WINDOWS_SKIP_TAGS)
    )


def unregistered_windows_like_predicates(
    sources: Mapping[str, str],
) -> list[tuple[str, str]]:
    """純函式：條件文字**看起來像** Windows 述詞、卻沒登記在
    `_WINDOWS_SKIP_PREDICATE_MARKERS` 的站點。回傳 `(站點, 條件源碼)`。

    這是 `untagged_windows_skip_decorators` 唯一靜默失效路徑的封口：未登記的述詞
    會讓方向判不出來、該站點靜默不報，而「靜默不報」正是本鎖存在的理由本身。
    """
    return sorted(
        (site.label(), site.condition)
        for site in skip_decorator_sites(sources)
        if _WINDOWS_PREDICATE_SUSPECT_RE.search(site.condition)
        and not _is_windows_predicate(site.condition)
    )


def read_test_sources(tests_dir: Path, pattern: str) -> dict[str, str]:
    """I/O 層（與上面三個純函式分離，比照本模組 `windows_native_skips`／`report_*`
    的既有分離慣例）：回傳 `{相對路徑: 原始碼}`。

    `pattern` **不給預設值**：掃描面必須與呼叫端的 discovery pattern 是同一個值
    （`run_root_unittests._PATTERN`），在這裡另立一份預設等於製造第二個會漂移的
    真相源。**遞迴**列舉並跳過快取目錄：非遞迴 glob 對「新增子目錄裡的鎖檔」是漏的，
    `test_adr_xplat001_c1c2_lock.guard_files_in_worktree` 已為同一個不對稱付過代價
    （改 top-level 檔→紅、新增子目錄檔→綠），本掃描沒有理由再引進一次。
    """
    return {
        p.relative_to(tests_dir).as_posix(): p.read_text(encoding="utf-8")
        for p in sorted(tests_dir.rglob(pattern))
        if not _CACHE_DIR_NAMES & set(p.parts)
    }


# ── R74：掃描面從「一棵樹」擴到「三棵活測試樹」（PKG-4 D 的射程面）───────────────
#
# 🔴 為何非擴不可：R72 建立方向判準時射程只有 `tools/tests/`（R74 實測 53 支檔），
# 而 repo 的活測試檔共 337 支——**84% 的測試檔不在任何方向判準的射程內**。判準的價值
# 是「同一個缺陷換個寫法／換棵樹就必紅」，射程只圈一棵樹等於把成本降到「寫在另一個
# 目錄」。這與 `DEF-101-757`／`DEF-101-777` 是同一個病（已知缺口只以劃界結案），
# 本輪的指派就是治射程。
#
# 射程＝三棵**會被閘門真的執行**的測試樹（相對 monorepo 根）：
#   `tools/tests`（root-infra／windows-smoke／macos-smoke 的 unittest leg）
#   `AutoClaude/tests`（autoclaude-ci `test` job）
#   `AISDLC_SDD/scripts/tests`（sdd ci-gate）
# 刻意**不含**的兩處，各有理由（誠實劃界，不是遺漏）：
#   ❌ `AISDLC_SDD/AISDLC_SDD_v0.NN/`（含 LATEST 的 `tools/fsm_runtime/tests`）——
#      Copy-on-Evolve 政策下凍結版與中間版一律不可改，把它們納入等於一上線就要求
#      修改不可改的樹；LATEST 版單獨納入則會讓射程隨版本目錄改名而漂移，需先把
#      `tools/lib/sdd_latest.py` 的解析接進本模組，屬另一件事（見回報的 out-of-scope）。
#   ❌ `AutoClaude/tests` 以外的 pytest 樹（無）。
_EXTRA_SCAN_TREES: tuple[str, ...] = (
    "AutoClaude/tests",
    "AISDLC_SDD/scripts/tests",
)

# 每棵樹的檔數下限＝R74 實掃數打八折取整（沿用
# `tools/tests/test_platform_neutral_paths.py::_scan_roots` 的 per-tree 下限慣例）。
# 全域總數下限對「單樹靜默縮面」不敏感，逐樹釘選才讓任一樹縮面必紅。
_TREE_FILE_FLOORS: dict[str, int] = {
    "tools/tests": 42,
    "AutoClaude/tests": 204,
    "AISDLC_SDD/scripts/tests": 23,
}

# 🔴 **棘輪基線**：`[POSIX-NATIVE-ONLY]`／`[MAC-NATIVE-ONLY]` 尚未補標的存量站點數
# （鍵＝相對 monorepo 根的樹名，值＝該樹**未標籤**的「Windows 上會 skip」站點數）。
#
# 為何是棘輪而不是直接判紅：本輪落地時實測存量分佈在多支檔案上，其中大部分不在本包的
# 檔案所有權內（跨界改動＝並行包互踩假紅）。棘輪讓「新增未標籤站點」當場紅、同時不
# 假裝存量已清乾淨——它是**可見的欠債**，不是豁免。
# 判準刻意是**相等**而非「不得增加」：任一方向的變動都必須有人回來改這張表，
# 否則它會像 `MIN_TESTS` 那樣腐化（該常數的註記逐字記載了腐化 11 輪的後果）。
# 存量欠債（R74 落地時實測，逐筆列名——「可見的欠債」的意思是看得到是**哪幾筆**）：
#   tools/tests: 1                  · test_dev_start_ps1_lastexitcode.py:235
#   AutoClaude/tests: 6             · test_evaluator_kill_tree.py:56/91/112
#                                   · test_perception.py:412
#                                   · test_perception_platform_honesty.py:84（darwin 專屬）
#                                   · tools/test_run_local_nightly_sh_static.py:186
#   AISDLC_SDD/scripts/tests: 1     · test_install_post_commit_exec_bit.py:29
# 這 8 筆全部落在 PKG-4 的檔案所有權之外（本包已補標的 10 筆都在 tools/tests/
# test_dev_start.py，故該樹由 11 降到 1）。補標＝在 reason 最前面加標籤、並把本表對應
# 數字下修，兩件事同一個 commit 做完，否則棘輪會擋。
_POSIX_TAG_RATCHET: dict[str, int] = {
    "tools/tests": 1,
    "AutoClaude/tests": 6,
    "AISDLC_SDD/scripts/tests": 1,
}


# 本模組住在 `<repo>/tools/lib/`：parents[1]＝tools、parents[2]＝repo 根。
_REPO_ROOT = Path(__file__).resolve().parents[2]
_REPO_TESTS_DIR = _REPO_ROOT / "tools" / "tests"


def scan_tree_sources(repo_root: Path, tests_dir: Path, pattern: str) -> dict[str, dict[str, str]]:
    """回傳 `{樹名: {相對樹的路徑: 原始碼}}`——三棵活測試樹（見 `_EXTRA_SCAN_TREES`）。

    `tests_dir` 仍是呼叫端傳進來的主樹（`tools/tests`），其餘由 `repo_root` 推導：
    這樣呼叫端（`tools/run_root_unittests.py`）的簽名完全不用改。
    """
    trees: dict[str, dict[str, str]] = {
        tests_dir.relative_to(repo_root).as_posix(): read_test_sources(tests_dir, pattern),
    }
    for rel in _EXTRA_SCAN_TREES:
        root = repo_root / rel
        trees[rel] = read_test_sources(root, pattern) if root.is_dir() else {}
    return trees


def _is_repo_main_tests_dir(tests_dir: Path) -> bool:
    """呼叫端傳進來的是不是**這個 repo 真正的** `tools/tests`。

    🔴 WHY 這道判斷不可省（R74 落地時當場被既有測試抓到）：
    `report_untagged_windows_skip_decorators` 除了在閘門上被呼叫，也被
    `tools/tests/test_run_root_unittests.py::StaticWindowsSkipTagScanTest` 拿**合成樹**
    呼叫（造一棵含漏標的假樹、斷言 reporter 回恰 1 筆問題）。若把「三棵活測試樹＋逐樹
    檔數下限＋反方向棘輪」無條件套上去，那些合成樹會突然受 repo 專屬判準管轄——實測
    回 10 筆問題而非 1 筆，合成樹的鑑別力被雜訊淹沒。`tools/run_root_unittests.py`
    的在地註解早就寫下同一個理由（「把 repo 專屬的掃描綁進去會讓那些合成樹莫名其妙地
    受本判準管轄」），R74 第一版沒讀進去、當場付了代價，故就地機械化：
    **只有真的在掃這個 repo 時，才啟用 repo 專屬的那三層。**
    """
    try:
        return tests_dir.resolve() == _REPO_TESTS_DIR.resolve()
    except OSError:  # pragma: no cover - 路徑不可解析時一律當「不是」（保守）
        return False


def posix_tag_ratchet_problems(counts: Mapping[str, int]) -> list[str]:
    """純函式：實測未標籤數與棘輪基線的差異；空清單＝合格。"""
    problems: list[str] = []
    for tree in sorted(set(counts) | set(_POSIX_TAG_RATCHET)):
        want = _POSIX_TAG_RATCHET.get(tree)
        got = counts.get(tree)
        if want is None:
            problems.append(
                f"{tree}：出現在掃描面卻不在 _POSIX_TAG_RATCHET 基線表內（實測 {got}）"
                "——新樹必須顯式入表，否則它的欠債靜默不計"
            )
        elif got is None:
            problems.append(f"{tree}：在基線表內卻不在掃描面（基線 {want}）——射程疑似縮小")
        elif got != want:
            verb = "新增了未標籤站點" if got > want else "已補標（請下修基線）"
            problems.append(
                f"{tree}：未標籤的「Windows 上會 skip」站點實測 {got}、基線 {want}"
                f"——{verb}。修法：在該 skip 的 reason 最前面加 "
                f"{POSIX_NATIVE_SKIP_TAG}（darwin 專屬用 {MAC_NATIVE_SKIP_TAG}），"
                f"或把 windows_skip_tags._POSIX_TAG_RATCHET['{tree}'] 改為 {got}"
            )
    return problems


def report_untagged_windows_skip_decorators(tests_dir: Path, pattern: str) -> list[str]:
    """跑靜態掃描並印出問題；回傳問題描述清單（非空 ⇒ 呼叫端須讓 rc 為 1）。

    掃到 0 份檔案時 fail-closed（掃描面消失本身就是失敗，同 `collection_gaps` 精神）。
    R74：射程擴為三棵活測試樹、並同時跑**反方向**（POSIX 側）的標籤棘輪。
    """
    problems: list[str] = []
    repo_mode = _is_repo_main_tests_dir(tests_dir)
    if repo_mode:
        trees = scan_tree_sources(_REPO_ROOT, tests_dir, pattern)
    else:
        # 合成樹（單元測試注入）：維持 R72 的單棵樹契約，不套 repo 專屬的三層。
        trees = {tests_dir.name: read_test_sources(tests_dir, pattern)}
    sources: dict[str, str] = {}
    posix_counts: dict[str, int] = {}
    for tree, tree_sources in trees.items():
        if not tree_sources:
            problems.append(f"掃描面為空：{tree} 底下找不到任何 {pattern}")
        if repo_mode:
            floor = _TREE_FILE_FLOORS.get(tree)
            if floor is None:
                problems.append(f"{tree}：不在 _TREE_FILE_FLOORS 內——新樹必須顯式釘下限")
            elif len(tree_sources) < floor:
                problems.append(
                    f"{tree}：掃描到 {len(tree_sources)} 支 {pattern} < 下限 {floor}"
                    "——該樹掃描面疑似縮小（不得靜默）"
                )
        sources.update({f"{tree}/{rel}": src for rel, src in tree_sources.items()})
        posix_counts[tree] = len(untagged_non_windows_skip_decorators(tree_sources))
    unregistered = unregistered_windows_like_predicates(sources)
    offenders = untagged_windows_skip_decorators(sources)
    problems += [f"未登記的 Windows 述詞：{label} 條件 {cond!r}" for label, cond in unregistered]
    problems += [f"漏標：{label}（命中關鍵詞 {hit!r}）" for label, hit, _ in offenders]
    ratchet = posix_tag_ratchet_problems(posix_counts) if repo_mode else []
    problems += [f"反方向標籤棘輪：{msg}" for msg in ratchet]
    if not problems:
        return []
    if ratchet:
        print(
            f"❌ 反方向（POSIX 側）標籤棘輪 {len(ratchet)} 筆——`{WINDOWS_NATIVE_SKIP_TAG}` "
            f"只照亮「非 Windows 上沒跑到的 Windows 專屬測試」，反方向（**因為跑在 "
            f"Windows 而失去的覆蓋**）此前一個機械物都沒有，複審者無法分辨哪幾筆是真的"
            f"覆蓋損失（R74／PKG-4 E‧F）：",
            file=sys.stderr,
        )
        for msg in ratchet:
            print(f"   - {msg}", file=sys.stderr)
    print(
        f"❌ 靜態標籤掃描（不分平台）發現 {len(problems)} 個問題——本掃描存在的理由是"
        f"「runtime 那道鎖在 Windows 上整組早退」，Windows 側三道閘門若沒有它就是同一個"
        f"瞎點的三份複本（R72）：",
        file=sys.stderr,
    )
    for label, condition in unregistered:
        print(
            f"   - {label}\n       條件 {condition!r} 看起來像 Windows 述詞、卻未登記於 "
            f"windows_skip_tags._WINDOWS_SKIP_PREDICATE_MARKERS ⇒ 方向判不出來、該站點會"
            f"靜默不報。修法：把該述詞加進登記表。",
            file=sys.stderr,
        )
    for label, hit, reason in offenders:
        print(f"   - {label}（命中關鍵詞 {hit!r}）\n       理由：{reason}", file=sys.stderr)
    if offenders:
        print(
            f"   修法：把 {WINDOWS_NATIVE_SKIP_TAG} 加在該 skip reason 的最前面"
            "（判準：`skipUnless(<Windows 述詞>)` ⇒ 非 Windows 才 skip ⇒ 正是本標籤的語意）。",
            file=sys.stderr,
        )
    return problems
