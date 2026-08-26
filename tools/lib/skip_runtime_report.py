#!/usr/bin/env python3
"""職責④：runtime 面——讀 `unittest.TestResult`，彙整「本次真的 skip 了什麼」。

與職責②（`skip_static_scan`，讀原始碼）互補：本面看得到**這次執行**的真實 skip（含
函式體內的條件 skip、環境探針、以及 reason 非字面值的站點），代價是它只反映當下這台
機器；②看得到全樹但只看得到寫在原始碼裡的字面值。

政策常數一律取自 `skip_tag_policy`（職責①）。關鍵詞面／豁免面以**參數注入**，理由同
`skip_static_scan` 的檔頭（facade 傳自己命名空間的常數進來，維持既有 mock 注入契約）。
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

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


# ── 職責④之二：**test-id 集合**面（M6 的「可求值」形狀）─────────────────────────
# 立案（R85 QA）：職責⑤（`skip_group_policy`）比的是**計數**⇒ 換掉一支 test-id 而計數不變
# 時恆綠，於是它答不了 M6（「每一支測試都至少在某條軌上跑過一次」）——缺口在判準的定義域、
# 不在量測，所以上 Windows 真機重量也一樣答不了。本面把落款換成 **skip 的 test-id 集合**、
# 判準換成集合關係 `skip(A) ⊆ run(B) ∪ 合法平台專屬集合`（`run(B)`＝「B 的落款裡沒有它」；
# 移項即 `skip(A) ∩ skip(B) − 豁免 = ∅`）。完整 WHY／門檻／誠實劃界的 SSOT＝M6 判準表
# `docs/06_quality/CrossPlatform_Maturity_Criteria.md`，本檔不複寫。
#
# 三態而不是布林（同 `skip_group_policy.declared_skipped` 回 `None` 的既有紀律）：缺互補
# 落款時是**不可求值**，它與通過在型別上就必須分得開——fail-open 的表徵與修好完全相同。
M6_OK, M6_VIOLATION, M6_UNEVALUABLE = "ok", "violation", "unevaluable"

#: 落款的家。刻意住 `docs/` 而非 `tools/`：它是**史料**（每平台各自落款、由 diff 稽核）
#: 不是判準；把數十行資料塞進護欄層是拿判準的行數額度養資料。
SKIP_ID_LEDGER = Path(__file__).resolve().parents[2] / "docs" / "06_quality" / "skip_id_ledger.json"

#: 合法「平台專屬」豁免（id → 為什麼世界上沒有一台機器該跑它）。**今天 0 筆**：現行 44 支
#: `[WINDOWS-NATIVE-ONLY]` 在真 Windows 上跑得到 ⇒ 它們的著落是落款而不是豁免。每加一筆
#: 都等於宣稱「這支測試永遠不會被執行」，那是缺陷不是豁免，故門檻刻意訂得很高。
_M6_EXEMPT: dict[str, str] = {}


def load_skip_id_ledger(path: Path | None = None) -> dict[str, object]:
    """讀落款。檔不存在回 `{}`（一個剖面都沒落款 ⇒ 上層一律走「不可求值」那一支）。"""
    target = path or SKIP_ID_LEDGER
    return json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}


def ledger_ids(ledger: Mapping[str, object], profile: str) -> set[str] | None:
    """某剖面落款的 skip id 集合；**沒落款／格式壞掉回 `None` 而不是 `set()`**——空集合的
    語意是「這個剖面一支都沒 skip」（最健康），與「沒人量過」正好相反。"""
    entry = ledger.get(profile)
    ids = entry.get("skipped") if isinstance(entry, Mapping) else None
    return set(ids) if isinstance(ids, list) else None


# 純函式：M6 的集合關係判準，回 `(三態, 訊息)`；只有 `M6_OK` 是通過。三向各帶方括號標籤
# 讓注入測試斷言「紅的是對的那一款」：①`[漂移]` live 集合 ≠ 本剖面落款集合（**計數相等時
# 照樣說話**＝集合粒度取代計數粒度的理由，且不需要另一個平台就能求值）②`[落款過時]` 互補
# 落款裡有 id 的模組已不在樹上（同一棵樹的落款可從**任一**平台驗證，這是 mac 上唯一抓得到
# Windows 落款腐化的一向）③`[全世界沒跑過]` 交集非空 ⇒ M6 本體被破壞。① 先於 ③：落款與
# 磁碟不符時 ③ 的兩個輸入都不可信（同 `skip_measurement_problems` 對「量測塌掉」的排序）。
#
# 🔴 ③ 是**多邊**交集，不是逐 counterpart 各自判斷後取聯集（R100 修復；此前的臭蟲：linux
# 對 win32、對 darwin 各自求交集，任一非空就報。一支測試只要在**任一** counterpart 上有跑
# （不在它的落款裡）就已經是「有人跑過」的證據；只有在**所有** counterpart 都同樣 skip 掉它
# 時才算「全世界沒跑過」——判準本體 `skip(A) ⊆ run(B) ∪ 合法平台專屬集合` 裡的 B 指的是
# 「任一互補剖面」，移項後 `nowhere` 必須是 `live ∩ counterpart_1 ∩ counterpart_2 ∩ …` 的
# 交集，不是 `(live∩counterpart_1) ∪ (live∩counterpart_2)`）。三剖面真落款驗證：linux 對
# win32 的交集 34 支（win32 專屬測試，家在 darwin）、對 darwin 的交集 44 支（darwin 專屬
# 測試，家在 win32）——這兩組互不相干，都不是「全世界沒跑過」；真正的多邊交集只有 1 支。
#
# 缺 counterpart 落款時的處理：那個 counterpart 對 ③ **跳過**（用「有落款的那些」做交集），
# 不讓整條 ③ 一起退回不可求值——`[缺互補落款]` 已經用 `blocked` 誠實記下這件事，讀者看得到
# 「這是不完整證據」；但已落款的那些互補剖面之間仍能算出目前可求值的最佳交集。誠實劃界：
# 這個方向是**保守偏嚴**（少一個 counterpart 的資料只會讓交集偏大，不會偏小），今天三個
# 剖面都已落款，這個分支在現有資料上不會被觸發，只有注入測試在守它。
def m6_id_set_problems(
    profile: str, live_ids: Sequence[str], counterparts: Sequence[str],
    ledger: Mapping[str, object], *, tests_dir: Path,
    exempt: Mapping[str, str] = _M6_EXEMPT,
) -> tuple[str, list[str]]:
    live, problems, blocked = set(live_ids), [], []
    own = ledger_ids(ledger, profile)
    if own is None:
        blocked.append(f"[未落款] `{profile}` 還沒有 id 落款 ⇒ 它的 skip 集合無從對帳。"
                       "取得＝把下面那份可貼落款填進落款檔")
    elif own != live:
        problems.append(
            f"[漂移] `{profile}` live 集合 ≠ 落款集合（計數 {len(live)} vs {len(own)}）："
            f"落款缺 {sorted(live - own)}／落款多 {sorted(own - live)}——🔴 **兩邊計數相等時"
            "這一向照樣說話**，那正是集合粒度取代計數粒度的理由。合法出口：確認差異是預期的"
            "（新增／改名測試）後把可貼落款重釘進落款檔")
    tree = profile.split("@", 1)[0]
    evaluable_counterparts: list[str] = []
    other_sets: list[set[str]] = []
    for counterpart in counterparts:
        other = ledger_ids(ledger, counterpart)
        if other is None:
            blocked.append(
                f"[缺互補落款] `{counterpart}` 沒有 id 落款 ⇒ M6 對 `{profile}` **不可求值**"
                "（這不是通過）：取得＝在那個剖面上跑一次同一支 runner，把它印出的可貼落款"
                f"填進 {SKIP_ID_LEDGER.name} 的同名鍵")
            continue
        if counterpart.split("@", 1)[0] == tree:
            stale = sorted(i for i in other
                           if not (tests_dir / f"{i.split('.')[0]}.py").is_file())
            if stale:
                problems.append(f"[落款過時] `{counterpart}` 的落款有 {len(stale)} 支 id 的"
                                f"模組已不在樹上：{stale}——那批 id 永遠對不上任何測試，"
                                "③ 的交集因此低報")
        evaluable_counterparts.append(counterpart)
        other_sets.append(other)
    if other_sets:
        nowhere = sorted(set.intersection(live, *other_sets) - set(exempt))
        if nowhere:
            names = "、".join(f"`{cp}`" for cp in evaluable_counterparts)
            problems.append(
                f"[全世界沒跑過] {len(nowhere)} 支在 `{profile}` 與**所有**已落款的互補剖面"
                f"（{names}）都 skip：{nowhere}——M6 的本體是 skip(A) ⊆ run(B) ∪ 合法平台專屬"
                "集合，這幾支落在差集裡 ⇒ 沒有任何機械證據顯示它們在世界上任何一處跑過")
    if problems:
        return M6_VIOLATION, problems + blocked
    return (M6_UNEVALUABLE, blocked) if blocked else (M6_OK, [])


def report_m6_id_sets(
    profile: str, result: unittest.TestResult, counterparts: Sequence[str],
    *, tests_dir: Path, path: Path | None = None,
) -> int:
    """印 M6 三態並回 rc（只有 `M6_VIOLATION` 回 1）。

    🔴 「不可求值」刻意回 0：擋下一個**結構上不可能在本平台補齊**的條件就是把守衛變成常紅，
    而本 repo 判過「擋到讓人無法工作的守衛會被整個關掉」。它與通過的區別落在三態值與措辭
    （逐字「這不是通過」），不在 rc ⇒ 判準的消費面是 `m6_id_set_problems` 的回傳值。
    """
    live = sorted(test_id for test_id, _ in all_skips(result))
    status, messages = m6_id_set_problems(
        profile, live, counterparts, load_skip_id_ledger(path), tests_dir=tests_dir)
    label = {M6_OK: "✅ 集合關係成立", M6_VIOLATION: "❌ 集合關係被破壞",
             M6_UNEVALUABLE: "⚠️  不可求值（**不是**通過）"}[status]
    stream = sys.stderr if status == M6_VIOLATION else sys.stdout
    print(f"[M6 id 集合] {profile}：{label}（本次 skip {len(live)} 支）", file=stream)
    for message in messages:
        print(f"   - {message}", file=stream)
    if status != M6_OK:
        print(f"   本剖面可貼落款（填進 {SKIP_ID_LEDGER}）：\n" + json.dumps(
            {profile: {"measured-at": datetime.now(UTC).isoformat(
                timespec="seconds"), "skipped": live}}, ensure_ascii=False, indent=2),
            file=stream)
    return 1 if status == M6_VIOLATION else 0
