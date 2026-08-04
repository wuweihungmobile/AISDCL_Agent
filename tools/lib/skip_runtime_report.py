#!/usr/bin/env python3
"""職責④：runtime 面——讀 `unittest.TestResult`，彙整「本次真的 skip 了什麼」。

與職責②（`skip_static_scan`，讀原始碼）互補：本面看得到**這次執行**的真實 skip（含
函式體內的條件 skip、環境探針、以及 reason 非字面值的站點），代價是它只反映當下這台
機器；②看得到全樹但只看得到寫在原始碼裡的字面值。

政策常數一律取自 `skip_tag_policy`（職責①）。關鍵詞面／豁免面以**參數注入**，理由同
`skip_static_scan` 的檔頭（facade 傳自己命名空間的常數進來，維持既有 mock 注入契約）。
"""
from __future__ import annotations

import os
import sys
import unittest
from collections.abc import Mapping, Sequence

from skip_tag_policy import (
    _WINDOWS_LIKE_SKIP_HINTS,
    _WINDOWS_SKIP_TAG_EXEMPT,
    ALL_SKIP_TAGS,
    WINDOWS_NATIVE_SKIP_TAG,
)


def all_skips(result: unittest.TestResult) -> list[tuple[str, str]]:
    """純函式（無 I/O 副作用）：回傳本次全部 skip 的 `(test_id, reason)`，
    含已被 `WINDOWS_NATIVE_SKIP_TAG` 標記者。"""
    return [(test.id(), reason) for test, reason in result.skipped]


def windows_native_skips(result: unittest.TestResult) -> list[str]:
    """純函式（無 I/O 副作用）：從 `result.skipped` 篩出帶 `[WINDOWS-NATIVE-ONLY]`
    標籤者，回傳測試 id 清單。

    與 `report_windows_native_skips` 分離（R43 二審 SA 複查揪出：原本印出副作用寫在
    同一函式內，導致自測時把 fixture 用的假測試 id 也印到真實終端輸出裡，混淆複審者
    對「本次是否真有 Windows 專屬測試未驗證」的判讀——測試應只斷言回傳值，不該觸發
    生產端的列印副作用）。
    """
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


def report_all_skips(
    result: unittest.TestResult, *, tags: Sequence[str] = ALL_SKIP_TAGS
) -> list[tuple[str, str]]:
    """印出本次**全部** skip 的 id 與理由。

    WHY（DEF-101-510，R59 於真 Windows 11 實機量到）：`report_windows_native_skips`
    只照亮**一個方向**——「這支測試只在原生 Windows 才有驗證價值，這次環境不符」。
    反方向（**因為我們正跑在 Windows，所以失去了某些覆蓋**）完全沒有標籤、沒有摘要、
    沒有計數，只會併進 `unittest` 預設的 `skipped=N` 一個數字裡。R59 實測：本 runner
    在 Windows 11 上 `skipped=11`，**11 支全部無標籤**，其中兩支是真正的覆蓋損失而非
    平台語意使然——
      ① `test_install_windows_nightly` 的語法解析因當時那台機器缺 pwsh 7 而 skip
         （DEF-101-509）。🔴 R73 訂正（DEF-101-777）：引擎可用性是**機器屬性**，
         一律現查 `tools/tests/_ps_engine.py::available_engines()`，不得寫成常數。
      ② `test_env_changed_removes_cache_dir_and_symlink` 因無 symlink 權限
         （`[WinError 1314]`，標準未提權 Windows 11 的預設狀態）而 skip。

    設計取捨（刻意選最笨的做法）：不發明第二套標籤分類，改為**全部印出來**，把分類交給
    讀取者。成本是每輪多 N 行輸出，換到的是「任何 skip 都不可能再隱形」——與紀律 #2
    「log 必須含完整統計，不信任預設 dump」同一精神。

    R74：`[已標籤]` 原本只認 Windows 側標籤，於是在 Windows 上跑時整批 POSIX 專屬 skip
    一律顯示 `[未標籤]`——字面上正確、實際上誤導：它讓「作者已標明這是 POSIX 側覆蓋
    損失」與「完全沒人分類過」長得一樣。
    R75：`tags` 預設擴為 `ALL_SKIP_TAGS`（含 `[TOOL-ABSENCE]`）——靜態面新增的第三種
    語意在 runtime 面也要認得，否則同一支 skip 在兩份報表上分類會不一致。
    """
    entries = all_skips(result)
    if entries:
        print(f"ℹ️  本次 skip 明細（共 {len(entries)} 支；DEF-101-510 要求全列不得只印計數）：")
        for test_id, reason in entries:
            tag = next((t for t in tags if t in reason), None)
            mark = f"[已標籤 {tag}]" if tag else "[未標籤]"
            print(f"   - {mark} {test_id}\n       理由：{reason}")
    return entries


def untagged_windows_like_skips(
    result: unittest.TestResult,
    *,
    on_windows: bool | None = None,
    hints: Sequence[str] = _WINDOWS_LIKE_SKIP_HINTS,
    exempt: Mapping[str, str] = _WINDOWS_SKIP_TAG_EXEMPT,
    tag: str = WINDOWS_NATIVE_SKIP_TAG,
) -> list[tuple[str, str, str]]:
    """純函式（無 I/O 副作用）：reason 講的是 Windows 語意、卻沒帶標籤的 skip。

    回傳 `(test_id, 命中的關鍵詞, reason)`。

    **只在非 Windows 平台上說話**（`on_windows` 預設取 `os.name == "nt"`，參數化僅
    供測試注入）。理由不是「Windows 上不想管」，而是標籤語意在那裡不適用：
    `[WINDOWS-NATIVE-ONLY]` 說的是「這支測試只在原生 Windows 才有驗證價值，**這次
    環境不符所以沒跑**」——在 Windows 上這類測試根本不會 skip。反過來，Windows 上
    真正會 skip 的是 POSIX-only 測試，而它們的 reason 十之八九也會提到 "Windows"
    （例如「Windows 無 symlink 權限」），照掃必然假紅。

    🔴 R72：這個早退**不是**可以刪掉的（刪了就是整片假紅），但它讓三道 Windows 側
    閘門成為同一個瞎點的三份複本。補位的是 `skip_static_scan` 的**靜態方向感知掃描**
    ——那一面不看當前平台，故在 Windows 上照樣會說話。
    """
    if on_windows is None:
        on_windows = os.name == "nt"
    if on_windows:
        return []
    out: list[tuple[str, str, str]] = []
    for test_id, reason in all_skips(result):
        if tag in reason or test_id in exempt:
            continue
        lowered = reason.lower()
        hit = next((kw for kw in hints if kw in lowered), None)
        if hit is not None:
            out.append((test_id, hit, reason))
    return sorted(out)


def report_untagged_windows_like_skips(
    result: unittest.TestResult, **kwargs: object
) -> list[tuple[str, str, str]]:
    """印出漏標籤者並回傳清單（非空 ⇒ 呼叫端須讓 rc 為 1，見 `run_with_floor`）。"""
    offenders = untagged_windows_like_skips(result, **kwargs)  # type: ignore[arg-type]
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
