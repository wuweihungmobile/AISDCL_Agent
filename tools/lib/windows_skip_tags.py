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
        tagged = set(windows_native_skips(result))
        print(f"ℹ️  本次 skip 明細（共 {len(entries)} 支；DEF-101-510 要求全列不得只印計數）：")
        for test_id, reason in entries:
            mark = "[已標籤]" if test_id in tagged else "[未標籤]"
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
    "_ps_windows_with_engine()",   # tools/tests/_ps_engine.windows_with_engine 的就地別名
    "_ps_windows_native_51()",     # 同上，windows_with_native_ps51 的就地別名
    "windows_with_native_ps51()",
    "_windows_pwsh_available()",   # tools/tests/test_bootstrap_ps1.py 的就地別名
)

# 「看起來像 Windows 述詞」的粗網。**只**用來抓上表的漏登記，不參與任何判紅／放行
# 決策——粗網天生會有偽陽性，讓它直接判紅會把本鎖變成噪音來源。
_WINDOWS_PREDICATE_SUSPECT_RE = re.compile(r"windows|win32|\bnt\b", re.IGNORECASE)

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


def skip_decorator_sites(sources: Mapping[str, str]) -> list[SkipSite]:
    """純函式（無 I/O 副作用，比照 `windows_native_skips` 慣例）：從
    `{檔名: 原始碼}` 抽出所有 reason 為**字面字串**的 skip decorator 站點。

    reason 取不到字面值時（變數、f-string、`.format()`）**略過而不猜**——本掃描
    判的是「寫在原始碼裡的那串話」，取不到就沒有可判的東西。這是刻意的判準邊界，
    不是遺漏：那類站點的可見度仍由 runtime 的 `report_all_skips` 承接。
    """
    sites: list[SkipSite] = []
    for name, src in sorted(sources.items()):
        tree = ast.parse(src, filename=name)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            for deco in node.decorator_list:
                if not isinstance(deco, ast.Call) or len(deco.args) < 2:
                    continue
                func = deco.func
                kind = getattr(func, "attr", None) or getattr(func, "id", None)
                if kind not in ("skipUnless", "skipIf"):
                    continue
                try:
                    reason = ast.literal_eval(deco.args[1])
                except Exception:  # noqa: BLE001 — 非字面值一律略過，見 docstring
                    continue
                if not isinstance(reason, str):
                    continue
                sites.append(SkipSite(
                    file=name,
                    lineno=deco.lineno,
                    target=node.name,
                    decorator=str(kind),
                    condition=ast.get_source_segment(src, deco.args[0]) or "",
                    reason=reason,
                ))
    return sites


def _is_windows_predicate(condition: str) -> bool:
    return any(marker in condition for marker in _WINDOWS_SKIP_PREDICATE_MARKERS)


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
        if site.decorator != "skipUnless" or not _is_windows_predicate(site.condition):
            continue
        if WINDOWS_NATIVE_SKIP_TAG in site.reason:
            continue
        lowered = site.reason.lower()
        hit = next((kw for kw in _WINDOWS_LIKE_SKIP_HINTS if kw in lowered), None)
        if hit is not None:
            out.append((site.label(), hit, site.reason))
    return sorted(out)


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


def report_untagged_windows_skip_decorators(tests_dir: Path, pattern: str) -> list[str]:
    """跑靜態掃描並印出問題；回傳問題描述清單（非空 ⇒ 呼叫端須讓 rc 為 1）。

    掃到 0 份檔案時 fail-closed（掃描面消失本身就是失敗，同 `collection_gaps` 精神）。
    """
    problems: list[str] = []
    sources = read_test_sources(tests_dir, pattern)
    if not sources:
        problems.append(f"掃描面為空：{tests_dir} 底下找不到任何 {pattern}")
    unregistered = unregistered_windows_like_predicates(sources)
    offenders = untagged_windows_skip_decorators(sources)
    problems += [f"未登記的 Windows 述詞：{label} 條件 {cond!r}" for label, cond in unregistered]
    problems += [f"漏標：{label}（命中關鍵詞 {hit!r}）" for label, hit, _ in offenders]
    if not problems:
        return []
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
