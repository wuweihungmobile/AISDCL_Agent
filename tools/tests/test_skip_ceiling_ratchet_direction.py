#!/usr/bin/env python
"""`tools/lib/skip_group_policy.py::_RUNTIME_SKIP_CEILING_MAX` 的方向鎖（DEF-200-160）。

WHY：該表上方散文自陳「天花板只准降」，但當回合實查全 repo **無對應的 `_FROZEN_CEILING_MAX`
常數、無方向鎖**——唯一守它的判準只比「基線（`_RUNTIME_SKIP_CEILING`）vs 天花板
（`_RUNTIME_SKIP_CEILING_MAX`）」，兩者一起加大即無判準可擋。本檔補上凍結對照：
把 `_RUNTIME_SKIP_CEILING_MAX` 的落地當回合快照凍結下來，任何一格數字比凍結值更大即紅。

放在測試檔而非 `tools/lib/skip_group_policy.py` 本體：該檔是 `guardrail_lib<=400`
零餘裕棘輪（當回合實查 398/400，僅餘 2 行），塞不下一份完整的凍結表字面；而這道鎖的
唯一消費端就是測試本身，不像 `_RUNTIME_SKIP_CEILING_MAX` 本身在生產路徑上被
`ceiling_problems()` 等函式讀取，放測試檔不影響任何生產行為。
"""
from __future__ import annotations

import copy
import subprocess
import sys
import unittest
from collections.abc import Sequence
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import skip_group_policy as S  # noqa: E402

#: tools/tests/ → tools/ → monorepo 根（同檔案家族 `test_negative_existence_claims_r82.py`
#: 既有寫法）。P1-6 共同變更鎖的 `_origin_main_head_diff()` 用它定位 `git` cwd。round-label-ok
_REPO_ROOT = Path(__file__).resolve().parents[2]

#: 🔴 DEF-200-160 二審修復（QA 親測證偽原版）：原版寫成
#: `copy.deepcopy(S._RUNTIME_SKIP_CEILING_MAX)`——那是**每次測試行程啟動時從當下即時模組值
#: 現算出來的快照**，不是寫死在磁碟上的歷史字面。QA 親自把 `_RUNTIME_SKIP_CEILING_MAX
#: ['tools/tests@win32']['platform']` 從 41 改成 999（放大 24 倍）重跑本檔，全數通過、
#: 完全沒抓到——因為「快照」與「現值」永遠是同一個物件的兩份拷貝，比較恆為套套邏輯。
#: 修法比照同目錄 `skip_tag_policy._POSIX_TAG_RATCHET_CEILING` 的既有做法：把落地當回合
#: 的真值**逐字抄成原始碼字面 dict**，不得再用 `copy.deepcopy(即時匯入值)` 或任何從
#: `S._RUNTIME_SKIP_CEILING_MAX` 推導的形式（那樣兩者恆等，方向鎖structurally 不可能觸發）。
#:
#: **只准新增鍵、既有鍵的值只准調小**（同 `ledger_rotation.py` 史料封印的精神：這是凍結
#: 前綴，不是「與現值相等」的斷言，否則會變成砸溫度計）。下修天花板時本表**不動**；
#: 上修則必須先在缺陷帳本具名理由，才把對應鍵的值也調大——那一行 diff 就是
#: 「有人在放寬」的可見痕跡。
_FROZEN_CEILING_MAX: dict[str, dict[str, int]] = {
    "AutoClaude/tests@win32+nopg+nested": {
        S.SKIP_GROUP_PLATFORM: 17,
        S.SKIP_GROUP_TOOL_ABSENCE: 0,
        S.SKIP_GROUP_ENV_DISABLED: 1,
        S.SKIP_GROUP_STRUCTURAL: 0,
        S.SKIP_GROUP_DEBT: 0,
        S.SKIP_GROUP_UNTAGGED: 118,
    },
    "AutoClaude/tests@win32+pg+nested": {
        S.SKIP_GROUP_PLATFORM: 5,
        S.SKIP_GROUP_TOOL_ABSENCE: 0,
        S.SKIP_GROUP_ENV_DISABLED: 12,
        S.SKIP_GROUP_STRUCTURAL: 1,
        S.SKIP_GROUP_DEBT: 6,
        S.SKIP_GROUP_UNTAGGED: 0,
    },
    "AutoClaude/tests@darwin+pg+nested": {
        S.SKIP_GROUP_PLATFORM: 53,
        S.SKIP_GROUP_TOOL_ABSENCE: 3,
        S.SKIP_GROUP_ENV_DISABLED: 2,
        S.SKIP_GROUP_STRUCTURAL: 1,
        S.SKIP_GROUP_DEBT: 3,
        S.SKIP_GROUP_UNTAGGED: 0,
    },
    "tools/tests@win32": {
        S.SKIP_GROUP_PLATFORM: 41,
        S.SKIP_GROUP_TOOL_ABSENCE: 0,
        S.SKIP_GROUP_ENV_DISABLED: 2,
        S.SKIP_GROUP_STRUCTURAL: 0,
        S.SKIP_GROUP_DEBT: 0,
        S.SKIP_GROUP_UNTAGGED: 0,
    },
    "tools/tests@darwin": {
        S.SKIP_GROUP_PLATFORM: 45,  # R115 round-label-ok：provenance 見 policy 主表同鍵段
        S.SKIP_GROUP_TOOL_ABSENCE: 0,
        S.SKIP_GROUP_ENV_DISABLED: 0,
        S.SKIP_GROUP_STRUCTURAL: 0,
        S.SKIP_GROUP_DEBT: 0,
        S.SKIP_GROUP_UNTAGGED: 0,
    },
    "tools/tests@linux": {
        S.SKIP_GROUP_PLATFORM: 78,  # R115 round-label-ok：provenance 見 policy 主表同鍵段
        S.SKIP_GROUP_TOOL_ABSENCE: 2,
        S.SKIP_GROUP_ENV_DISABLED: 0,
        S.SKIP_GROUP_STRUCTURAL: 0,
        S.SKIP_GROUP_DEBT: 0,
        S.SKIP_GROUP_UNTAGGED: 0,
    },
}


def ceiling_max_direction_problems(
    live: dict[str, dict[str, int]] | None = None,
) -> list[str]:
    """`live`（預設現讀 `S._RUNTIME_SKIP_CEILING_MAX`）逐格與凍結快照比對，回問題清單。

    只判**既有鍵**（凍結快照裡有的 profile／group）；新增的 profile 或 group 不受限制
    ——它們沒有凍結值可比，方向鎖管不到「首次登記給多少」，只管「登記過的能不能無聲調大」。
    """
    live = S._RUNTIME_SKIP_CEILING_MAX if live is None else live
    problems: list[str] = []
    for profile, groups in _FROZEN_CEILING_MAX.items():
        live_groups = live.get(profile)
        if live_groups is None:
            continue  # profile 被整個移除不在本鎖射程（那是另一種變更，另案處理）
        for group, frozen_val in groups.items():
            live_val = live_groups.get(group)
            if live_val is not None and live_val > frozen_val:
                problems.append(
                    f"_RUNTIME_SKIP_CEILING_MAX['{profile}']['{group}'] "
                    f"= {live_val} > 凍結值 {frozen_val}（只准變小）")
    return problems


class TestCeilingMaxDirectionLock(unittest.TestCase):
    def test_the_real_table_does_not_regress_against_its_own_snapshot(self) -> None:
        """真表當回合實測必須零違規——快照就是照現值拍的，這是前提，不是巧合。"""
        self.assertEqual(ceiling_max_direction_problems(), [])

    def test_raising_an_existing_cell_is_caught(self) -> None:
        """紅綠自證：把任一格調大，方向鎖必須有牙。"""
        mutated = copy.deepcopy(S._RUNTIME_SKIP_CEILING_MAX)
        profile = next(iter(mutated))
        group = next(iter(mutated[profile]))
        mutated[profile][group] += 1
        problems = ceiling_max_direction_problems(mutated)
        self.assertTrue(problems, "調大單一格竟未被判紅 ⇒ 這條鎖沒有承重")
        self.assertIn(profile, problems[0])
        self.assertIn(group, problems[0])

    def test_lowering_an_existing_cell_is_allowed(self) -> None:
        """收緊（調小）永遠合法，不該被本鎖誤擋。"""
        mutated = copy.deepcopy(S._RUNTIME_SKIP_CEILING_MAX)
        profile = next(iter(mutated))
        group = next(iter(mutated[profile]))
        if mutated[profile][group] > 0:
            mutated[profile][group] -= 1
            self.assertEqual(ceiling_max_direction_problems(mutated), [])

    def test_a_brand_new_profile_is_not_blocked(self) -> None:
        """新增剖面（凍結快照裡沒有的鍵）不受方向鎖限制——首次登記給多少是另一件事。"""
        mutated = copy.deepcopy(S._RUNTIME_SKIP_CEILING_MAX)
        mutated["brand/new@profile"] = {S.SKIP_GROUP_PLATFORM: 999}
        self.assertEqual(ceiling_max_direction_problems(mutated), [])

    def test_the_snapshot_actually_has_multiple_entries(self) -> None:
        """快照若意外變成空字典，上面幾支測試會全部虛假通過（零迭代恆綠）——釘住非空。"""
        self.assertGreaterEqual(len(_FROZEN_CEILING_MAX), 4)
        total_cells = sum(len(g) for g in _FROZEN_CEILING_MAX.values())
        self.assertGreaterEqual(total_cells, 20)

    def test_both_raised_together_is_still_caught(self) -> None:
        """立案情境本身：`_RUNTIME_SKIP_CEILING` 與 `_RUNTIME_SKIP_CEILING_MAX` 兩張表一起
        加大時，既有判準（比較基線 vs 天花板）看不出異狀——但本鎖只看天花板 vs 它自己的
        凍結快照，兩表一起動一樣抓得到。"""
        mutated_ceiling = copy.deepcopy(S._RUNTIME_SKIP_CEILING)
        mutated_max = copy.deepcopy(S._RUNTIME_SKIP_CEILING_MAX)
        profile = next(iter(mutated_max))
        group = next(iter(mutated_max[profile]))
        mutated_ceiling[profile][group] = mutated_max[profile][group] + 5
        mutated_max[profile][group] += 5
        with mock.patch.object(S, "_RUNTIME_SKIP_CEILING", mutated_ceiling):
            self.assertTrue(ceiling_max_direction_problems(mutated_max))


# ── P1-6：skip 天花板①②③ 與 M6 落款④ 的共同變更鎖 ───────────────────────────── round-label-ok
#: WHY：R115 落地 `_RUNTIME_SKIP_CEILING`／`_RUNTIME_SKIP_CEILING_MAX`／本檔 round-label-ok
#: `_FROZEN_CEILING_MAX` 三張表的平台互補上修（commit `7f8c96a`）時漏補第四層
#: M6 落款 `docs/06_quality/skip_id_ledger.json`——直到下一個 commit `5d5dd37`
#: 才補上。四層座標、已否決形態（層與層互相派生／「① 總和 vs ④ 列表長度」靜態
#: 互查——後者判準是 `total_got > total_cap` 的上限語意，漏補只會讓 ④ 更小，對
#: 目標痛點恆綠）逐項見 `docs/04_planning/R118_HANDOFF.md` 的 P1-6 節，此處不重複。round-label-ok
#:
#: 判準語意：**若某次變更動了①②③任一檔案，④ 也必須在同一次變更中被動過**，
#: 否則紅。刻意是**檔案級**而非「剖面鍵值」級——R118_HANDOFF.md 給的反事實素材 round-label-ok
#: （commit `7f8c96a`／`5d5dd37`）本身就是以檔案集合為顆粒度提供的，檔案級判準
#: 已足以擋下立案的那個具體缺陷；再往下切到剖面鍵值需解析 diff hunk，複雜度換不到
#: 額外鑑別力（①②③三個檔是 skip 天花板家族專用檔，改它們幾乎不可能是為了別的事）。
#:
#: 誠實劃界：本鎖擋不到「①②③與④兩邊都改了、但④改錯／改漏某個剖面」——那仍須
#: `skip_runtime_report.m6_id_set_problems()` 在該平台 CI 實跑才驗得出來。本鎖只管
#: 「有沒有同動」，不管「動得對不對」。
_CO_CHANGE_SOURCE_PATHS = frozenset({
    "tools/lib/skip_group_policy.py",
    "tools/tests/test_skip_ceiling_ratchet_direction.py",
})
_CO_CHANGE_LEDGER_PATH = "docs/06_quality/skip_id_ledger.json"


def skip_ledger_co_change_problems(changed_paths: Sequence[str]) -> list[str]:
    """純函式：`changed_paths`（repo 相對 posix 路徑清單）若含 `_CO_CHANGE_SOURCE_PATHS`
    任一檔，`_CO_CHANGE_LEDGER_PATH` 也必須在同一份清單裡，否則回問題清單。

    純函式（不碰 git）是刻意的：反事實測試只需要餵字面清單即可驗證鑑別力，不必真的
    重演 commit（同本檔上方 `ceiling_max_direction_problems` 的既有設計慣例——取數
    與判定分離）。真實接線（怎麼拿到 `changed_paths`）見 `_origin_main_head_diff`。
    """
    changed = set(changed_paths)
    touched = sorted(changed & _CO_CHANGE_SOURCE_PATHS)
    if touched and _CO_CHANGE_LEDGER_PATH not in changed:
        return [
            f"變更了 {touched} 卻未同動 {_CO_CHANGE_LEDGER_PATH}"
            "（R115 red-4 同型漏補：skip 天花板①②③與 M6 落款④須同一次變更；"
            "見 docs/04_planning/R118_HANDOFF.md 的 P1-6 節）"
        ]
    return []


def _origin_main_head_diff(repo_root: Path) -> list[str] | None:
    """取數半邊（與上面的判準分離，見本節 WHY）：`git diff --name-only` 介於
    `merge-base(origin/main, HEAD)` 與 `HEAD` 之間——也就是「這次 push 即將帶給
    origin/main 的全部檔案改動」。

    比較基準選 `origin/main`、不選「工作樹 vs HEAD」：後者只在 **commit 前** 有
    鑑別力，一旦 commit 完成、工作樹回到乾淨狀態就恆綠——而 R115 red-4 的實際發生 round-label-ok
    時點正是「commit 完 `7f8c96a` 之後、push 之前」，工作樹比較基準在那個時點已經
    看不到問題。`origin/main..HEAD` 涵蓋「本次 push 要帶出去的全部 commit」，命中
    的正是這個窗口（落地執行點＝本機 `tools/run_root_unittests.py`，由
    `tools/git-hooks/pre-push` 在 push 前呼叫；push 範圍含根層檔時必跑，見該檔
    `run_rootinfra` 判定）。

    誠實劃界（CI fresh clone 上的行為，現查後訂正）：`windows-compat-ci.yml`／
    `macos-compat-ci.yml` 是 push 事件**之後**才觸發（`on: push: branches: [main]`），
    此時 HEAD 已經是新的 origin/main 本身，`origin/main..HEAD` 結構上必為空 diff
    ⇒ 本函式在 CI 上是**結構性 no-op**（不是假綠——它從未宣稱在那個時點抓得到
    東西）。真正的執行點是本機 pre-push：那時 `origin/main`（remote-tracking ref）
    仍是 push 前的舊狀態、HEAD 才是即將被推的 commit，兩者之間才有真實 diff 可比，
    這也正是 R115 red-4（`7f8c96a` 單獨被推）原本應該被攔下的時間點。round-label-ok

    `origin/main` 解不出時（全新 clone 未 fetch 過 main、或本機從未 `git fetch
    origin`）回傳 `None`——呼叫端必須把它與空清單分開處理（`None` ⇒ 結構上不可
    求值，不得判定為綠；見 `TestSkipLedgerCoChangeLock` 的 wiring 測試 `skipTest`）。
    """
    try:
        merge_base = subprocess.run(
            ["git", "merge-base", "origin/main", "HEAD"],
            cwd=repo_root, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=15,
        )
        if merge_base.returncode != 0 or not merge_base.stdout.strip():
            return None
        base = merge_base.stdout.strip()
        diff = subprocess.run(
            ["git", "-c", "core.quotepath=false", "diff", "--name-only",
             "--no-renames", base, "HEAD"],
            cwd=repo_root, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=15,
        )
        if diff.returncode != 0:
            return None
    except (OSError, subprocess.SubprocessError):
        return None
    return [line.strip().replace("\\", "/") for line in diff.stdout.splitlines() if line.strip()]


class TestSkipLedgerCoChangeLock(unittest.TestCase):
    """反事實四格（動工前必做的證偽，見 R118_HANDOFF.md P1-6 節）：以 commit round-label-ok
    `7f8c96a`（R115 漏補④）／`5d5dd37`（補回④）的真實檔案集合重演。round-label-ok"""

    def test_skip_ledger_co_change_catches_the_r115_red4_commit_alone(self) -> None:
        """`7f8c96a` 單獨重演：只動①②，未動④ ⇒ 必須紅。"""
        problems = skip_ledger_co_change_problems([
            "tools/lib/skip_group_policy.py",
            "tools/tests/test_skip_ceiling_ratchet_direction.py",
        ])
        self.assertTrue(problems, "R115 red-4 的檔案集合竟未被判紅 ⇒ 這條鎖沒有承重")

    def test_skip_ledger_co_change_is_clean_once_the_ledger_joins(self) -> None:
        """`7f8c96a` ∪ `5d5dd37`：①②③④ 同一次變更全部到齊 ⇒ 必須綠。"""
        problems = skip_ledger_co_change_problems([
            "tools/lib/skip_group_policy.py",
            "tools/tests/test_skip_ceiling_ratchet_direction.py",
            _CO_CHANGE_LEDGER_PATH,
        ])
        self.assertEqual(problems, [])

    def test_skip_ledger_co_change_allows_touching_only_the_ledger(self) -> None:
        """單獨補落款（不動①②③）不是違規——本鎖管的是「①②③動了卻沒帶④」，非反向。"""
        self.assertEqual(skip_ledger_co_change_problems([_CO_CHANGE_LEDGER_PATH]), [])

    def test_skip_ledger_co_change_has_zero_crosstalk_on_unrelated_files(self) -> None:
        """完全無關的變更 ⇒ 零串音。"""
        self.assertEqual(
            skip_ledger_co_change_problems(["README.md", "tools/lib/other_module.py"]), [])

    def test_skip_ledger_co_change_against_the_real_push_range(self) -> None:
        """生產接線：對真實 `origin/main..HEAD` 跑一次（見 `_origin_main_head_diff`
        docstring 的誠實劃界——CI 上結構性 no-op，真正的執行點是本機 pre-push）。"""
        changed = _origin_main_head_diff(_REPO_ROOT)
        if changed is None:
            self.skipTest(
                "origin/main 無法解析（全新 clone 未 fetch main，或本機未曾 "
                "`git fetch origin`）——本鎖真正的執行點是本機 pre-push，"
                "見 `_origin_main_head_diff` docstring 的誠實劃界")
        problems = skip_ledger_co_change_problems(changed)
        self.assertEqual(problems, [], "\n".join(problems))


if __name__ == "__main__":
    unittest.main()
