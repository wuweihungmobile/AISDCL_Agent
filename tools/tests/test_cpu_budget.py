"""`tools/lib/cpu_budget.py` 的機械物（DEF-200-289：跨 leg CPU 預算 SSOT）。

WHY（測意圖非僅行為，Rule 9）：`parallel_shard.worker_count()`、AutoClaude
`pyproject.toml` 的 `-n auto`、`AISDLC_SDD/scripts/ci-gate.sh`／`.ps1` 與
`tools/git-hooks/pre-push` 各自寫死 CPU 平行度公式，五套互不知情、無 SSOT。
本檔鎖住唯一算法來源本身（headless／互動兩分支、cap、floor、per_leg 切分、
CLI 契約）；GAP-E 另鎖 AutoClaude `pyproject.toml` 的 `-n auto --dist worksteal`
必須存在，防止「本檔算出的預算沒有任何已知消費端會用到」的退化。

執行：python -m unittest test_cpu_budget -v   （cwd＝tools/tests）
"""
from __future__ import annotations

import os
import subprocess
import sys
import tomllib
import unittest
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
import cpu_budget as cb  # noqa: E402


class TotalBudgetFormulaTest(unittest.TestCase):
    """`total_budget()` 的 headless／互動兩分支＋cap／floor。"""

    def test_interactive_reserves_one_core(self) -> None:
        cases = {1: 1, 2: 1, 9: 8, 10: 9, 100: 9}
        for cpu, expected in cases.items():
            self.assertEqual(
                cb.total_budget(cpu_count=cpu, headless=False), expected,
                f"互動 cpu={cpu} 應得 {expected}（max(1, min(9, cpu-1))）")

    def test_headless_uses_all_cores(self) -> None:
        cases = {1: 1, 2: 2, 9: 9, 10: 9, 100: 9}
        for cpu, expected in cases.items():
            self.assertEqual(
                cb.total_budget(cpu_count=cpu, headless=True), expected,
                f"headless cpu={cpu} 應得 {expected}（max(1, min(9, cpu)))）")

    def test_headless_gets_one_more_worker_than_interactive_below_cap(self) -> None:
        """本輪核心行為變化：cap 以下，headless 應比互動多 1 個 worker——這正是
        DEF-200-289 的收益本體（CI headless 不再白白保留前景那一核）。"""
        for cpu in (2, 4, 8):
            self.assertEqual(
                cb.total_budget(cpu_count=cpu, headless=True),
                cb.total_budget(cpu_count=cpu, headless=False) + 1,
            )

    def test_floor_is_one_even_with_single_core(self) -> None:
        self.assertEqual(cb.total_budget(cpu_count=1, headless=False), 1)
        self.assertEqual(cb.total_budget(cpu_count=0, headless=False), 1)

    def test_headless_env_detection_github_actions(self) -> None:
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=False):
            os.environ.pop("AUTOSDD_CPU_HEADLESS", None)
            self.assertEqual(cb.total_budget(cpu_count=4), 4, "GITHUB_ACTIONS=true 應判 headless")

    def test_headless_env_detection_autosdd_flag(self) -> None:
        with mock.patch.dict(os.environ, {"AUTOSDD_CPU_HEADLESS": "1"}, clear=False):
            os.environ.pop("GITHUB_ACTIONS", None)
            self.assertEqual(
                cb.total_budget(cpu_count=4), 4, "AUTOSDD_CPU_HEADLESS=1 應判 headless")

    def test_interactive_when_neither_env_set(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITHUB_ACTIONS", None)
            os.environ.pop("AUTOSDD_CPU_HEADLESS", None)
            self.assertEqual(cb.total_budget(cpu_count=4), 3, "兩變數皆缺席應判互動")

    def test_explicit_headless_param_wins_over_env(self) -> None:
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=False):
            self.assertEqual(
                cb.total_budget(cpu_count=4, headless=False), 3,
                "顯式傳入的 headless 參數應勝過環境變數偵測",
            )


class PerLegBudgetTest(unittest.TestCase):
    """`per_leg_budget()`：依 leg 數平分預算，floor=1。"""

    def test_single_leg_equals_total(self) -> None:
        self.assertEqual(cb.per_leg_budget(1, total=9), 9)

    def test_multiple_legs_divide_evenly(self) -> None:
        self.assertEqual(cb.per_leg_budget(3, total=9), 3)

    def test_uneven_division_floors(self) -> None:
        self.assertEqual(cb.per_leg_budget(4, total=9), 2)

    def test_floor_is_one_even_when_legs_exceed_total(self) -> None:
        self.assertEqual(cb.per_leg_budget(20, total=9), 1)

    def test_non_positive_legs_treated_as_one(self) -> None:
        self.assertEqual(cb.per_leg_budget(0, total=9), 9)
        self.assertEqual(cb.per_leg_budget(-3, total=9), 9)

    def test_uses_total_budget_when_total_omitted(self) -> None:
        self.assertEqual(cb.per_leg_budget(1), cb.total_budget())


class CliContractTest(unittest.TestCase):
    """CLI：`--legs N` 只印一個整數到 stdout、rc=0；未知參數 rc≠0。"""

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(  # child-encoding-ok: 只印 ASCII 整數或 argparse 英文訊息
            [sys.executable, str(_REPO_ROOT / "tools" / "lib" / "cpu_budget.py"), *args],
            capture_output=True, text=True, encoding="utf-8",
        )

    def test_legs_one_prints_single_integer_rc_zero(self) -> None:
        proc = self._run("--legs", "1")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertRegex(proc.stdout.strip(), r"^\d+$", f"stdout 應恰為一個整數：{proc.stdout!r}")

    def test_legs_two_still_prints_single_integer(self) -> None:
        proc = self._run("--legs", "2")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertRegex(proc.stdout.strip(), r"^\d+$")

    def test_unknown_argv_nonzero_rc(self) -> None:
        proc = self._run("--bogus")
        self.assertNotEqual(proc.returncode, 0)

    def test_missing_required_legs_nonzero_rc(self) -> None:
        proc = self._run()
        self.assertNotEqual(proc.returncode, 0)


class GapEAutoClaudeAddoptsTest(unittest.TestCase):
    """GAP-E：AutoClaude `pyproject.toml` 的 `-n auto --dist worksteal` 全庫過去
    無任何測試直接斷言其存在——本鎖只讀該檔（不碰 AutoClaude/ 任何其他檔案）。"""

    def test_pyproject_addopts_declares_xdist_auto_worksteal(self) -> None:
        pyproject_path = _REPO_ROOT / "AutoClaude" / "pyproject.toml"
        with pyproject_path.open("rb") as f:
            data = tomllib.load(f)
        addopts = data.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("addopts", [])
        self.assertIn("-n", addopts, f"addopts 缺 -n：{addopts!r}")
        self.assertIn("--dist", addopts, f"addopts 缺 --dist：{addopts!r}")
        n_idx = addopts.index("-n")
        self.assertEqual(
            addopts[n_idx + 1] if n_idx + 1 < len(addopts) else None, "auto",
            f"`-n` 之後應緊接 `auto`，實得：{addopts!r}",
        )
        dist_idx = addopts.index("--dist")
        self.assertEqual(
            addopts[dist_idx + 1] if dist_idx + 1 < len(addopts) else None, "worksteal",
            f"`--dist` 之後應緊接 `worksteal`，實得：{addopts!r}",
        )


if __name__ == "__main__":
    unittest.main()
