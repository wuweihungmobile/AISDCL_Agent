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
import re
import subprocess
import sys
import unittest
from collections.abc import Mapping, Sequence
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
#: 🔴 R119 修復包 round-label-ok：判準粒度由**檔案級**改為**剖面鍵值級**。原版寫成「①②③任一
#: 檔案出現在變更清單即紅」，落地當回合就抓到了自己——本鎖自身的程式碼就住在
#: `_CO_CHANGE_SOURCE_PATHS` 其中一個檔案裡，commit `a1fbbba`（新增本節程式碼）
#: 只是在幫這道鎖本身加程式碼，`_FROZEN_CEILING_MAX` 一個字元都沒有動過，檔案級
#: 判準卻照樣要求同動 ④——往後任何對這兩個檔案的無關改動（加註解、加測試、修
#: typo）都會被誤擋，而「擋到讓人無法工作的守衛會被整個關掉，比沒有守衛更糟」
#: 正是 `block_destructive_git.py` 檔頭自己講的道理，不該只在那一支鎖上算數。
#:
#: 新判準：**只有當①②③所轄的剖面鍵值 dict（`_RUNTIME_SKIP_CEILING`／
#: `_RUNTIME_SKIP_CEILING_MAX`／`_FROZEN_CEILING_MAX`）字面本身在 `origin/main..HEAD`
#: 之間有實質差異（正規化掉註解與空白後逐字比對），才要求同動 ④**；純粹 touch
#: 檔案（新增程式碼、改註解、加測試）不觸發。取數方式＝`git show <rev>:<path>`
#: 拿兩版原始碼文字、以括號配對切出目標 dict 賦值的字面區塊（`_extract_dict_literal`）。
#: 找不到證據（檔案在某一版不存在、擷取不到賦值、`origin/main` 解不出來）一律保守
#: 判定為「已變動」——寧可多要求一次同動 ④，不可在沒有證據時判定為綠，同
#: `_origin_main_head_diff` 對無法解析時回 `None` 的既有紀律。
#:
#: 誠實劃界：本鎖擋不到「①②③與④兩邊都改了、但④改錯／改漏某個剖面」——那仍須
#: `skip_runtime_report.m6_id_set_problems()` 在該平台 CI 實跑才驗得出來。本鎖只管
#: 「剖面鍵值有沒有真的變、有變的話有沒有同動④」，不管「動得對不對」。
_CO_CHANGE_SOURCE_PATHS = frozenset({
    "tools/lib/skip_group_policy.py",
    "tools/tests/test_skip_ceiling_ratchet_direction.py",
})
_CO_CHANGE_LEDGER_PATH = "docs/06_quality/skip_id_ledger.json"

#: `_CO_CHANGE_SOURCE_PATHS` 各檔所轄的「剖面鍵值」dict 賦值名稱——判準只在這些
#: 具名 dict 的字面上比對，不是整個檔案的逐位元組差異。
_CO_CHANGE_DICT_NAMES: dict[str, tuple[str, ...]] = {
    "tools/lib/skip_group_policy.py": ("_RUNTIME_SKIP_CEILING", "_RUNTIME_SKIP_CEILING_MAX"),
    "tools/tests/test_skip_ceiling_ratchet_direction.py": ("_FROZEN_CEILING_MAX",),
}


def _strip_line_comments(text: str) -> str:
    """逐行砍掉第一個 `#` 之後的內容——本檔三張目標 dict 的字面只有 int／模組
    常數鍵，不含帶 `#` 的字串值，故逐行砍尾是安全的。在括號配對之前先跑這一步，
    讓註解裡偶然出現的 `{`／`}`（例：provenance 說明文字）不會污染配對深度。"""
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def _extract_dict_literal(text: str, name: str) -> str | None:
    """從原始碼字面文字中擷取 `name: dict[...] = {...}` 這個頂層賦值的完整字典
    字面（含左右大括號）。用括號配對找右邊界；找不到該賦值（名稱不存在、或右邊界
    配對不完整）時回 `None`——呼叫端須把它與『內容相同』分開處理。"""
    stripped = _strip_line_comments(text)
    match = re.search(
        rf"^{re.escape(name)}\s*:\s*dict\[[^\n]*?\]\s*=\s*\{{", stripped, re.MULTILINE)
    if match is None:
        return None
    start = match.end() - 1  # 指向那個開括號 `{`
    depth = 0
    for i in range(start, len(stripped)):
        ch = stripped[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return stripped[start:i + 1]
    return None


def _normalize_dict_literal(literal: str) -> str:
    """去掉空白行與行首尾空白（註解已在 `_strip_line_comments` 階段砍掉），
    只留下對字典內容有意義的字元——縮排調整、空行增減不構成「值變了」。"""
    return "\n".join(line.strip() for line in literal.splitlines() if line.strip())


def _dict_literal_changed(old_text: str | None, new_text: str | None, name: str) -> bool:
    """單一 dict 賦值字面在兩版之間是否有實質差異（正規化掉註解／空白後比對）。

    任一版本的文字缺席、或擷取不到該賦值 ⇒ 保守回 `True`（「找不到證據」不等於
    「沒有變化」——同 `_origin_main_head_diff` 對 `origin/main` 解不出時回 `None`
    的既有紀律：結構上不可求值時，寧可多要求一次同動 ④，不可判定為綠）。
    """
    if old_text is None or new_text is None:
        return True
    old_literal = _extract_dict_literal(old_text, name)
    new_literal = _extract_dict_literal(new_text, name)
    if old_literal is None or new_literal is None:
        return True
    return _normalize_dict_literal(old_literal) != _normalize_dict_literal(new_literal)


def _source_path_value_changed(path: str, old_text: str | None, new_text: str | None) -> bool:
    """`path`（`_CO_CHANGE_SOURCE_PATHS` 之一）在兩版之間，其所轄的剖面鍵值 dict
    是否真的變了——判準核心：把「檔案被 touch」與「剖面鍵值有實質變動」分開。
    未登記於 `_CO_CHANGE_DICT_NAMES` 的路徑沒有已知 dict 可比對，保守回 `True`。
    """
    names = _CO_CHANGE_DICT_NAMES.get(path, ())
    if not names:
        return True
    return any(_dict_literal_changed(old_text, new_text, name) for name in names)


def skip_ledger_co_change_problems(
    changed_paths: Sequence[str],
    value_changed: Mapping[str, bool] | None = None,
) -> list[str]:
    """純函式：`changed_paths`（repo 相對 posix 路徑清單）若含 `_CO_CHANGE_SOURCE_PATHS`
    任一檔、且該檔所轄的剖面鍵值**真的變動**（見 `value_changed`），
    `_CO_CHANGE_LEDGER_PATH` 也必須在同一份清單裡，否則回問題清單。

    純函式（不碰 git）是刻意的：反事實測試只需要餵字面清單即可驗證鑑別力，不必真的
    重演 commit（同本檔上方 `ceiling_max_direction_problems` 的既有設計慣例——取數
    與判定分離）。真實接線（怎麼拿到 `changed_paths`／`value_changed`）見
    `_origin_main_head_diff`／`_co_change_value_changed_map`。

    `value_changed`：`_CO_CHANGE_SOURCE_PATHS` 各檔在本次變更中，其所轄的剖面鍵值
    dict 是否真的變動（由 `_source_path_value_changed` 解 git 內容後填入）。缺省
    （`None`）或漏了某個 touched 路徑的鍵時，該路徑保守視為「已變動」——判準由
    檔案級過渡到剖面鍵值級時，向下相容的安全預設：呼叫端沒有能力算出剖面鍵值
    有沒有變時，不得因此把紅判成綠。
    """
    changed = set(changed_paths)
    touched = sorted(changed & _CO_CHANGE_SOURCE_PATHS)
    if not touched:
        return []
    value_changed = value_changed or {}
    materially_touched = [p for p in touched if value_changed.get(p, True)]
    if materially_touched and _CO_CHANGE_LEDGER_PATH not in changed:
        return [
            f"變更了 {materially_touched}（剖面鍵值有實質變動）卻未同動 "
            f"{_CO_CHANGE_LEDGER_PATH}（R115 red-4 同型漏補：skip 天花板①②③與 "
            "M6 落款④須同一次變更；見 docs/04_planning/R118_HANDOFF.md 的 P1-6 節）"
        ]
    return []


def _merge_base_with_origin_main(repo_root: Path) -> str | None:
    """`merge-base(origin/main, HEAD)` 的 sha；解不出時（全新 clone 未 fetch main、
    或本機從未 `git fetch origin`）回 `None`——與 `_origin_main_head_diff` 共用同一
    份誠實劃界，見該函式 docstring。"""
    try:
        result = subprocess.run(
            ["git", "merge-base", "origin/main", "HEAD"],
            cwd=repo_root, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return result.stdout.strip()


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

    🔴 R119 round-label-ok：`_co_change_value_changed_map` 用同一個 merge-base（見
    `_merge_base_with_origin_main`）逐檔取兩版內容，判斷「剖面鍵值有沒有真的變」
    ——那才是決定要不要同動 ④ 的依據，本函式只負責「哪些檔案被動過」這一半。
    """
    base = _merge_base_with_origin_main(repo_root)
    if base is None:
        return None
    try:
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


def _show_file_at_rev(repo_root: Path, rev: str, path: str) -> str | None:
    """`git show <rev>:<path>` 的內容；檔案在該版不存在或 git 出錯時回 `None`
    （呼叫端＝`_dict_literal_changed` 對缺席內容保守回「已變動」，不宣稱「沒變」）。
    """
    try:
        result = subprocess.run(
            ["git", "-c", "core.quotepath=false", "show", f"{rev}:{path}"],
            cwd=repo_root, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _co_change_value_changed_map(
    repo_root: Path, base: str, touched: Sequence[str],
) -> dict[str, bool]:
    """production 接線：對 `touched`（`_CO_CHANGE_SOURCE_PATHS` 與變更清單的交集）
    逐檔取 `base`（merge-base）與 `HEAD` 兩版內容，交給 `_source_path_value_changed`
    判定剖面鍵值是否真的變了。"""
    return {
        path: _source_path_value_changed(
            path, _show_file_at_rev(repo_root, base, path),
            _show_file_at_rev(repo_root, "HEAD", path))
        for path in touched
    }


class TestSkipLedgerCoChangeLock(unittest.TestCase):
    """反事實五格 round-label-ok（第 1~4 格見 R118_HANDOFF.md P1-6 節；第 5 格＝R119 修復包自證，
    判準粒度必須是「剖面鍵值是否真的變動」而非「檔案是否被 touch」——原版檔案級
    判準連自己新增這道鎖的那次變更（`a1fbbba`）都會誤判為違規）。"""

    def test_skip_ledger_co_change_catches_the_r115_red4_commit_alone(self) -> None:
        """`7f8c96a` 單獨重演，餵真實 diff 內容（該棒真的改了剖面鍵值：darwin
        44→45、linux 77→78）：只動①②③，未動④ ⇒ 必須紅。"""
        touched = [
            "tools/lib/skip_group_policy.py",
            "tools/tests/test_skip_ceiling_ratchet_direction.py",
        ]
        value_changed = {
            path: _source_path_value_changed(
                path,
                _show_file_at_rev(_REPO_ROOT, "7f8c96a^", path),
                _show_file_at_rev(_REPO_ROOT, "7f8c96a", path))
            for path in touched
        }
        self.assertEqual(
            value_changed, dict.fromkeys(touched, True),
            "前提檢查：7f8c96a 對兩檔都應判為「剖面鍵值有變」，否則下面的紅斷言"
            "沒有意義（見 commit 訊息：darwin 44→45／linux 77→78）")
        problems = skip_ledger_co_change_problems(touched, value_changed)
        self.assertTrue(problems, "R115 red-4 的真實 diff 竟未被判紅 ⇒ 這條鎖沒有承重")

    def test_skip_ledger_co_change_is_clean_once_the_ledger_joins(self) -> None:
        """`7f8c96a` ∪ `5d5dd37`：①②③④ 同一次變更全部到齊 ⇒ 必須綠。"""
        touched = [
            "tools/lib/skip_group_policy.py",
            "tools/tests/test_skip_ceiling_ratchet_direction.py",
        ]
        value_changed = {
            path: _source_path_value_changed(
                path,
                _show_file_at_rev(_REPO_ROOT, "7f8c96a^", path),
                _show_file_at_rev(_REPO_ROOT, "7f8c96a", path))
            for path in touched
        }
        problems = skip_ledger_co_change_problems(
            [*touched, _CO_CHANGE_LEDGER_PATH], value_changed)
        self.assertEqual(problems, [])

    def test_skip_ledger_co_change_allows_touching_only_the_ledger(self) -> None:
        """單獨補落款（不動①②③）不是違規——本鎖管的是「①②③動了卻沒帶④」，非反向。"""
        self.assertEqual(skip_ledger_co_change_problems([_CO_CHANGE_LEDGER_PATH]), [])

    def test_skip_ledger_co_change_has_zero_crosstalk_on_unrelated_files(self) -> None:
        """完全無關的變更 ⇒ 零串音。"""
        self.assertEqual(
            skip_ledger_co_change_problems(["README.md", "tools/lib/other_module.py"]), [])

    def test_skip_ledger_co_change_ignores_a_touch_with_no_value_change(self) -> None:
        """🔴 第 5 格 round-label-ok（R119 核心）：層③檔案被 touch，但 `_FROZEN_CEILING_MAX`
        字面本身零變動（本輪 `a1fbbba` 的真實形態——只是新增這道鎖自己的程式碼）
        ⇒ 判準不得要求同動④。重演對象＝真實 `origin/main..HEAD` 對本檔的 diff：
        只新增 import／新函式／新 class，`_FROZEN_CEILING_MAX` 一個字元都沒有動過。
        """
        path = "tools/tests/test_skip_ceiling_ratchet_direction.py"
        old_text = _show_file_at_rev(_REPO_ROOT, "origin/main", path)
        new_text = _show_file_at_rev(_REPO_ROOT, "HEAD", path)
        if old_text is None or new_text is None:
            self.skipTest(
                "origin/main 或 HEAD 對本檔的內容取不到——本鎖真正的執行點是本機"
                " pre-push，見 `_origin_main_head_diff` docstring 的誠實劃界")
        self.assertFalse(
            _dict_literal_changed(old_text, new_text, "_FROZEN_CEILING_MAX"),
            "前提檢查：本輪對 _FROZEN_CEILING_MAX 字面應該零變動，若這裡變 True，"
            "代表本輪真的動了剖面鍵值，下面的綠斷言就不成立了")
        value_changed = {path: _source_path_value_changed(path, old_text, new_text)}
        problems = skip_ledger_co_change_problems([path], value_changed)
        self.assertEqual(problems, [], "\n".join(problems))

    def test_skip_ledger_co_change_defaults_to_conservative_when_value_changed_omitted(
        self,
    ) -> None:
        """未提供 `value_changed`（呼叫端沒有能力算出剖面鍵值有沒有變，例如舊呼叫
        點）時必須保守視為「已變動」——找不到證據不能判定為綠，這是本鎖由檔案級
        判準過渡到剖面鍵值級判準時，向下相容的安全預設。"""
        problems = skip_ledger_co_change_problems([
            "tools/lib/skip_group_policy.py",
            "tools/tests/test_skip_ceiling_ratchet_direction.py",
        ])
        self.assertTrue(problems)

    def test_skip_ledger_co_change_against_the_real_push_range(self) -> None:
        """生產接線：對真實 `origin/main..HEAD` 跑一次（見 `_origin_main_head_diff`
        docstring 的誠實劃界——CI 上結構性 no-op，真正的執行點是本機 pre-push）。
        剖面鍵值是否真變動，逐檔以 `_show_file_at_rev` 解兩版內容判定——這是
        R119 修復的核心 round-label-ok：檔案級判準會把「只 touch 沒改值」誤判為違規（見上面
        `test_skip_ledger_co_change_ignores_a_touch_with_no_value_change`）。"""
        base = _merge_base_with_origin_main(_REPO_ROOT)
        changed = _origin_main_head_diff(_REPO_ROOT)
        if base is None or changed is None:
            self.skipTest(
                "origin/main 無法解析（全新 clone 未 fetch main，或本機未曾 "
                "`git fetch origin`）——本鎖真正的執行點是本機 pre-push，"
                "見 `_origin_main_head_diff` docstring 的誠實劃界")
        touched = sorted(set(changed) & _CO_CHANGE_SOURCE_PATHS)
        value_changed = _co_change_value_changed_map(_REPO_ROOT, base, touched)
        problems = skip_ledger_co_change_problems(changed, value_changed)
        self.assertEqual(problems, [], "\n".join(problems))


if __name__ == "__main__":
    unittest.main()
