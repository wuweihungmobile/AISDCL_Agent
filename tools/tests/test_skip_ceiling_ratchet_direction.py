#!/usr/bin/env python
"""`tools/lib/skip_group_policy.py::_RUNTIME_SKIP_CEILING_MAX` 的方向鎖（DEF-200-160）。

WHY：該表上方散文自陳「天花板只准降」，但當回合實查全 repo **無對應的 `_FROZEN_` 常數、
無方向鎖**——唯一守它的判準只比「基線（`_RUNTIME_SKIP_CEILING`）vs 天花板
（`_RUNTIME_SKIP_CEILING_MAX`）」，兩者一起加大即無判準可擋。本檔補上凍結對照：
把 `_RUNTIME_SKIP_CEILING_MAX` 的落地當回合快照凍結下來，任何一格數字比凍結值更大即紅。

放在測試檔而非 `tools/lib/skip_group_policy.py` 本體：該檔是 `guardrail_lib<=400`
零餘裕棘輪（當回合實查 398/400，僅餘 2 行），塞不下一份完整的凍結表字面；而這道鎖的
唯一消費端就是測試本身，不像 `_RUNTIME_SKIP_CEILING_MAX` 本身在生產路徑上被
`ceiling_problems()` 等函式讀取，放測試檔不影響任何生產行為。
"""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import skip_group_policy as S  # noqa: E402

#: 🔴 落地當回合（本輪）對 `S._RUNTIME_SKIP_CEILING_MAX` 的逐字快照——**只准新增鍵、
#: 既有鍵的值只准調小**（同 `ledger_rotation.py` 史料封印的精神：這是凍結前綴，不是
#: 「與現值相等」的斷言，否則會變成砸溫度計）。下修天花板時本表**不動**；上修則必須先
#: 在缺陷帳本具名理由，才把對應鍵的值也調大——那一行 diff 就是「有人在放寬」的可見痕跡。
_FROZEN_CEILING_MAX: dict[str, dict[str, int]] = copy.deepcopy(S._RUNTIME_SKIP_CEILING_MAX)


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


if __name__ == "__main__":
    unittest.main()
