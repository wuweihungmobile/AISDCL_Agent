"""`tools/lib/cpu_budget.py` 的機械物（DEF-200-289：跨 leg CPU 預算 SSOT；
DEF-200-327 實體核優先）。

WHY（測意圖非僅行為，Rule 9）：`parallel_shard.worker_count()`、AutoClaude
`pyproject.toml` 的 `-n auto`、`AISDLC_SDD/scripts/ci-gate.sh`／`.ps1` 與
`tools/git-hooks/pre-push` 各自寫死 CPU 平行度公式，五套互不知情、無 SSOT。
本檔鎖住唯一算法來源本身（headless／互動兩分支、cap、floor、per_leg 切分、
CLI 契約、實體核偵測退化路徑）；GAP-E 另鎖 AutoClaude `pyproject.toml` 的
`-n auto --dist worksteal` 必須存在，防止「本檔算出的預算沒有任何已知消費端
會用到」的退化。互動分支測試一律 mock `_detect_physical_count()`（本機真的裝了
psutil，不 mock 就會被真實硬體核心數污染，測試在不同機器上得到不同答案）。

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
    """`total_budget()` 的 headless（邏輯核）／互動（實體核）兩分支＋cap／floor。"""

    def setUp(self) -> None:
        # 隔離本機真實 psutil：互動分支未顯式給 physical_count 時一律視為偵測失敗。
        patcher = mock.patch.object(cb, "_detect_physical_count", return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_interactive_reserves_one_physical_core(self) -> None:
        cases = {1: 1, 10: 9, 14: 13, 20: 16}
        for physical, expected in cases.items():
            self.assertEqual(
                cb.total_budget(physical_count=physical, headless=False), expected,
                f"互動 physical={physical} 應得 {expected}（max(1, min(16, physical-1))）")

    def test_headless_uses_all_logical_cores(self) -> None:
        cases = {1: 1, 4: 4, 9: 9, 16: 16, 20: 16, 100: 16}
        for cpu, expected in cases.items():
            self.assertEqual(
                cb.total_budget(cpu_count=cpu, headless=True), expected,
                f"headless cpu={cpu} 應得 {expected}（max(1, min(16, cpu)))）")

    def test_headless_gets_one_more_worker_than_interactive_below_cap(self) -> None:
        """本輪核心行為：cap 以下，headless（邏輯核 N）應比互動（實體核 N）多 1 個
        worker——CI headless 不再白白保留前景那一核（DEF-200-289 收益本體）。"""
        for cores in (2, 4, 8):
            self.assertEqual(
                cb.total_budget(cpu_count=cores, headless=True),
                cb.total_budget(physical_count=cores, headless=False) + 1,
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
            self.assertEqual(cb.total_budget(cpu_count=4), 3, "兩變數皆缺席應判互動，退回邏輯核")

    def test_explicit_headless_param_wins_over_env(self) -> None:
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=False):
            self.assertEqual(
                cb.total_budget(cpu_count=4, headless=False), 3,
                "顯式傳入的 headless 參數應勝過環境變數偵測",
            )

    def test_interactive_uses_physical_headless_uses_logical(self) -> None:
        """同一組 (logical, physical) 下，互動只看 physical、headless 只看 logical。"""
        self.assertEqual(cb.total_budget(cpu_count=4, physical_count=14, headless=False), 13)
        self.assertEqual(cb.total_budget(cpu_count=4, physical_count=14, headless=True), 4)


class ParseIntLineTest(unittest.TestCase):
    """`_parse_int_line()`：`sysctl -n hw.physicalcpu` 這類單行數字輸出的容錯解析。"""

    def test_parses_trailing_newline(self) -> None:
        self.assertEqual(cb._parse_int_line("10\n"), 10)

    def test_strips_surrounding_whitespace(self) -> None:
        self.assertEqual(cb._parse_int_line("  10  \n"), 10)

    def test_non_numeric_returns_none(self) -> None:
        self.assertIsNone(cb._parse_int_line("sysctl: unknown oid 'hw.physicalcpu'\n"))

    def test_empty_or_blank_returns_none(self) -> None:
        self.assertIsNone(cb._parse_int_line(""))
        self.assertIsNone(cb._parse_int_line("\n   \n"))


def _two_socket_smt_cpuinfo(sockets: int = 2, cores_per_socket: int = 4,
                             threads_per_core: int = 2) -> str:
    """合成 `/proc/cpuinfo`：`sockets` 顆 CPU、每顆 `cores_per_socket` 實體核、
    每核 `threads_per_core` 條 SMT 執行緒——用來驗證「processor 數 != 實體核數」
    （預設 2×4×2=16 processor、應算出 8 個實體核）。"""
    lines: list[str] = []
    processor = 0
    for socket in range(sockets):
        for core in range(cores_per_socket):
            for _thread in range(threads_per_core):
                lines += [
                    f"processor\t: {processor}",
                    f"physical id\t: {socket}",
                    f"core id\t: {core}",
                    "",
                ]
                processor += 1
    return "\n".join(lines)


#: 真實 ARM `/proc/cpuinfo` 常見樣本：無 `physical id`／`core id` 兩鍵。
_ARM_CPUINFO_SAMPLE = (
    "processor\t: 0\n"
    "model name\t: ARM Cortex-A72\n"
    "BogoMIPS\t: 108.00\n"
    "\n"
    "processor\t: 1\n"
    "model name\t: ARM Cortex-A72\n"
    "BogoMIPS\t: 108.00\n"
)


class ParseProcCpuinfoTest(unittest.TestCase):
    """`_parse_proc_cpuinfo()`：以 physical id×core id 找實體核，兩鍵缺席回 None。"""

    def test_two_socket_four_core_smt_counts_eight_physical_cores(self) -> None:
        records = cb._parse_proc_cpuinfo(_two_socket_smt_cpuinfo())
        self.assertEqual(cb._count_processor_cores(records), 8)

    def test_arm_sample_without_id_keys_returns_none(self) -> None:
        self.assertIsNone(cb._parse_proc_cpuinfo(_ARM_CPUINFO_SAMPLE))


class CountProcessorCoresTest(unittest.TestCase):
    """`_count_processor_cores()`：對注入 records 去重計數，空／None 回 None。"""

    def test_dedupes_repeated_pairs(self) -> None:
        records = [(0, 0), (0, 0), (0, 1), (1, 0), (1, 1)]
        self.assertEqual(cb._count_processor_cores(records), 4)

    def test_none_input_returns_none(self) -> None:
        self.assertIsNone(cb._count_processor_cores(None))

    def test_empty_list_returns_none(self) -> None:
        self.assertIsNone(cb._count_processor_cores([]))


class PlatformPhysicalCountDispatchTest(unittest.TestCase):
    """`_platform_physical_count()`：依 `sys.platform` 分派的免第三方依賴退化路徑
    （darwin／linux 可在任何機器上以 mock 驗證；win32 的 ctypes 分支需要真實
    Windows 上的 kernel32，見任務 NOTES，本檔僅以本機可行的手段覆蓋前兩者與
    「其他平台」分支）。"""

    def test_darwin_uses_sysctl(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["sysctl", "-n", "hw.physicalcpu"], returncode=0, stdout="10\n", stderr="")
        with mock.patch.object(sys, "platform", "darwin"), \
                mock.patch.object(cb.subprocess, "run", return_value=completed) as run_mock:
            self.assertEqual(cb._platform_physical_count(), 10)
        args, kwargs = run_mock.call_args
        self.assertEqual(args[0], ["sysctl", "-n", "hw.physicalcpu"])
        self.assertEqual(kwargs.get("encoding"), "utf-8")

    def test_darwin_subprocess_exception_returns_none(self) -> None:
        with mock.patch.object(sys, "platform", "darwin"), \
                mock.patch.object(cb.subprocess, "run", side_effect=OSError("no sysctl")):
            self.assertIsNone(cb._platform_physical_count())

    def test_darwin_nonzero_returncode_returns_none(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["sysctl"], returncode=1, stdout="", stderr="err")
        with mock.patch.object(sys, "platform", "darwin"), \
                mock.patch.object(cb.subprocess, "run", return_value=completed):
            self.assertIsNone(cb._platform_physical_count())

    def test_linux_reads_proc_cpuinfo(self) -> None:
        text = _two_socket_smt_cpuinfo()
        with mock.patch.object(sys, "platform", "linux"), \
                mock.patch("builtins.open", mock.mock_open(read_data=text)):
            self.assertEqual(cb._platform_physical_count(), 8)

    def test_linux_missing_proc_cpuinfo_returns_none(self) -> None:
        with mock.patch.object(sys, "platform", "linux"), \
                mock.patch("builtins.open", side_effect=OSError("no such file")):
            self.assertIsNone(cb._platform_physical_count())

    def test_unknown_platform_returns_none(self) -> None:
        with mock.patch.object(sys, "platform", "aix"):
            self.assertIsNone(cb._platform_physical_count())


class DetectPhysicalCountTest(unittest.TestCase):
    """`_detect_physical_count()`：psutil 優先、否則平台分支、否則 None 的三段
    分派（2026-09-20 DEF-200-347：psutil 不是本 repo 任何宣告依賴，
    乾淨環境 import 必炸，此前恆回 None ⇒ 互動預算恆退回邏輯核-1，SMT 機器算錯
    實體核心數）。"""

    def test_psutil_available_short_circuits_platform_branch(self) -> None:
        fake_psutil = mock.Mock()
        fake_psutil.cpu_count.return_value = 8
        with mock.patch.dict(sys.modules, {"psutil": fake_psutil}), \
                mock.patch.object(cb, "_platform_physical_count") as platform_mock:
            self.assertEqual(cb._detect_physical_count(), 8)
            fake_psutil.cpu_count.assert_called_once_with(logical=False)
            platform_mock.assert_not_called()

    def test_psutil_absent_falls_back_to_platform_branch(self) -> None:
        with mock.patch.dict(sys.modules, {"psutil": None}), \
                mock.patch.object(cb, "_platform_physical_count", return_value=6) as m:
            self.assertEqual(cb._detect_physical_count(), 6)
            m.assert_called_once_with()

    def test_psutil_returns_falsy_falls_back_to_platform_branch(self) -> None:
        fake_psutil = mock.Mock()
        fake_psutil.cpu_count.return_value = None
        with mock.patch.dict(sys.modules, {"psutil": fake_psutil}), \
                mock.patch.object(cb, "_platform_physical_count", return_value=4):
            self.assertEqual(cb._detect_physical_count(), 4)

    def test_platform_branch_exception_returns_none(self) -> None:
        with mock.patch.dict(sys.modules, {"psutil": None}), \
                mock.patch.object(cb, "_platform_physical_count",
                                   side_effect=RuntimeError("boom")):
            self.assertIsNone(cb._detect_physical_count())

    def test_platform_branch_none_falls_back_total_budget_to_logical_minus_one(
            self) -> None:
        with mock.patch.dict(sys.modules, {"psutil": None}), \
                mock.patch.object(cb, "_platform_physical_count", return_value=None):
            self.assertIsNone(cb._detect_physical_count())
            self.assertEqual(cb.total_budget(cpu_count=8, headless=False), 7)

    def test_live_smoke_returns_none_or_plausible_core_count(self) -> None:
        """不 mock：本機真實偵測結果須為 None，或落在 `[1, os.cpu_count()]` 之間
        （這台 mac 應為 10；不同機器上這是量測值，本測試刻意不寫死）。"""
        detected = cb._detect_physical_count()
        if detected is not None:
            self.assertGreaterEqual(detected, 1)
            self.assertLessEqual(detected, os.cpu_count() or detected)


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
