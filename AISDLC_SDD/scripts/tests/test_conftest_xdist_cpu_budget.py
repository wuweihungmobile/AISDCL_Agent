"""DEF-200-353／F-SD-01（多 CPU 第十八輪）回歸鎖：AISDLC_SDD 側 xdist `-n auto` worker 數
必須吃到根層 `tools/lib/cpu_budget.py` 的實體核心預算，而非 xdist 內建的邏輯核
演算法（見 `AISDLC_SDD/conftest.py` 該節 docstring 的立案說明；對稱
`AutoClaude/tests/conftest.py` B1／DEF-200-328）。

WHY（Rule 9，測意圖非僅行為）：純函式 `_cpu_budget_workers()` 好測，但真正容易
被改壞而不被發現的是「版本樹 rootdir conftest 真的有 re-export 這三個 hook 名字」
與「官方閘門實際呼叫形態（`-n auto`／`-p no:xdist`）下真的印得出／不印錯」——
純函式綠、接線斷掉或版本樹沒接線是本 repo 最常見的假綠形狀（同
`test_conftest_windows_native_skip_report.py::
test_latest_version_tree_has_the_summary_hook_wired` 的既有判例）。故本檔分
三層鎖：① 純函式（fake runner，涵蓋優先序四分支）；② 接線（AST 讀 LATEST 版
conftest.py 原文，斷言三個 hook 名字皆以 `= _shared.<name>` 形態出現、
`pytest_configure` 不在其列）；③ 行為（真跑 subprocess pytest，涵蓋 env 覆寫
／無覆寫回退／`-p no:xdist` 不炸三種官方呼叫形態）。

行為鎖刻意用固定小 worker 數（env 覆寫＝2）或挑最小測試模組，避免本檔自身在
`ci-gate.sh`／pre-push 的 `-n auto` 下被平行執行時，於某個 xdist worker 內再
巢狀 spawn 大量 pytest 子行程造成資源爆炸。
"""
from __future__ import annotations

import ast
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

from scripts import sdd_version  # isort: skip（同 test_sdd_version.py 既有慣例）

REPO_ROOT = Path(__file__).resolve().parents[2]  # AISDLC_SDD/
MONOREPO_ROOT = REPO_ROOT.parent
SHARED_CONFTEST = REPO_ROOT / "conftest.py"
CPU_BUDGET_SCRIPT = MONOREPO_ROOT / "tools" / "lib" / "cpu_budget.py"
_LATEST = sdd_version.latest_version_name(REPO_ROOT, warn=lambda _m: None)
LATEST_DIR = REPO_ROOT / str(_LATEST)
TARGET_TEST_REL = str(Path("tools") / "fsm_runtime" / "tests" / "test_cli_utf8_reconfigure.py")


# ──────────────────────────────────────────────────────────────
# ① 純函式鎖
# ──────────────────────────────────────────────────────────────
def _load_shared_conftest():
    """以唯一模組名載入共用層 `AISDLC_SDD/conftest.py`（比照該檔被
    `AISDLC_SDD_v0.30/conftest.py` 借用時的既有手法：唯一模組名避免與 pytest
    自身以 `conftest` 為名載入的真實 conftest 互撞；exec 前後快照/還原
    `sys.path`，因為共用層載入期會 `sys.path.insert` 一個相依路徑）。
    """
    spec = importlib.util.spec_from_file_location(
        "_test_cpu_budget_shared_mirror", SHARED_CONFTEST
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    saved_sys_path = list(sys.path)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = saved_sys_path
    return module


class _FakeCompletedProcess:
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout


def test_env_override_takes_priority_and_skips_runner() -> None:
    """優先序 ① 覆寫最高：runner 完全不該被呼叫。"""
    shared = _load_shared_conftest()
    calls: list[list[str]] = []

    def _runner(argv, **kwargs):  # noqa: ANN001, ARG001
        calls.append(argv)
        raise AssertionError("env 覆寫優先序最高，runner 不該被呼叫")

    result = shared._cpu_budget_workers(
        {"PYTEST_XDIST_AUTO_NUM_WORKERS": "4"}, Path("/definitely/does/not/exist"), _runner
    )
    assert result == 4
    assert calls == []


def test_missing_path_returns_none_without_calling_runner() -> None:
    """優先序 ② path 不存在：fail-open 回 None，runner 不該被呼叫。"""
    shared = _load_shared_conftest()

    def _runner(argv, **kwargs):  # noqa: ANN001, ARG001
        raise AssertionError("path 不存在時不該呼叫 runner")

    result = shared._cpu_budget_workers({}, Path("/definitely/does/not/exist"), _runner)
    assert result is None


def test_runner_stdout_parsed_as_positive_int(tmp_path) -> None:
    """優先序 ③ 正常路徑：runner stdout 為正整數字串即採用。"""
    shared = _load_shared_conftest()
    dummy = tmp_path / "dummy_cpu_budget.py"
    dummy.write_text("", encoding="utf-8")

    def _runner(argv, **kwargs):  # noqa: ANN001, ARG001
        return _FakeCompletedProcess("9\n")

    assert shared._cpu_budget_workers({}, dummy, _runner) == 9


def test_runner_exception_returns_none(tmp_path) -> None:
    """優先序 ④ runner 拋例外：fail-open 回 None，不得外洩例外。"""
    shared = _load_shared_conftest()
    dummy = tmp_path / "dummy_cpu_budget.py"
    dummy.write_text("", encoding="utf-8")

    def _runner(argv, **kwargs):  # noqa: ANN001, ARG001
        raise TimeoutError("模擬子行程逾時")

    assert shared._cpu_budget_workers({}, dummy, _runner) is None


def test_runner_non_numeric_stdout_returns_none(tmp_path) -> None:
    """優先序 ④ 的另一分支：非數字輸出同樣 fail-open 回 None。"""
    shared = _load_shared_conftest()
    dummy = tmp_path / "dummy_cpu_budget.py"
    dummy.write_text("", encoding="utf-8")

    def _runner(argv, **kwargs):  # noqa: ANN001, ARG001
        return _FakeCompletedProcess("not-a-number\n")

    assert shared._cpu_budget_workers({}, dummy, _runner) is None


def test_positive_int_rejects_zero_and_non_numeric() -> None:
    shared = _load_shared_conftest()
    assert shared._positive_int("0") is None
    assert shared._positive_int("abc") is None
    assert shared._positive_int("3") == 3


# ──────────────────────────────────────────────────────────────
# ② 接線鎖
# ──────────────────────────────────────────────────────────────
def _shared_reexports(source: str) -> dict[str, str]:
    """AST 解析：抓出 `<name> = _shared.<attr>` 形態的 re-export 對照表
    （target name -> attr name）。比照
    `test_conftest_windows_native_skip_report.py` 既有的 AST 判準風格
    （不用逐行 regex，避免多行賦值誤判）。
    """
    tree = ast.parse(source)
    result: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        value = node.value
        if (
            isinstance(value, ast.Attribute)
            and isinstance(value.value, ast.Name)
            and value.value.id == "_shared"
        ):
            result[node.targets[0].id] = value.attr
    return result


def test_latest_version_tree_reexports_cpu_budget_hooks() -> None:
    """真樹接線鎖：LATEST 版必須 re-export 三個 cpu_budget hook，且不得
    re-export `pytest_configure`（既有紀律：那支是 DEF-02-001 跨版 guard，語意
    屬 bare 呼叫情境，與本機制無關）。
    """
    conftest = LATEST_DIR / "conftest.py"
    assert conftest.is_file(), f"LATEST 版 {_LATEST} 缺 conftest.py"
    reexports = _shared_reexports(conftest.read_text(encoding="utf-8"))
    for name in (
        "pytest_xdist_auto_num_workers",
        "pytest_xdist_setupnodes",
        "pytest_sessionstart",
    ):
        assert reexports.get(name) == name, (
            f"{name} 未以 `{name} = _shared.{name}` 形態出現於版本樹 conftest.py——"
            "官方閘門實際走的路徑（`cd v0.30 && pytest`）會看不到 cpu_budget hook"
        )
    assert "pytest_configure" not in reexports, (
        "pytest_configure 不得被 re-export（既有紀律，見版本樹 conftest.py 檔頭 WHY 段）"
    )


# ──────────────────────────────────────────────────────────────
# ③ 行為鎖（subprocess 真跑；固定小 worker 數／最小模組，避免資源爆炸）
# ──────────────────────────────────────────────────────────────
_EXCLUDED_ENV_KEYS = frozenset(
    {
        "PYTEST_XDIST_AUTO_NUM_WORKERS",
        "AUTOSDD_PARALLEL_TESTS_WORKERS",
        "AUTOSDD_PARALLEL_TESTS",
    }
)


def _clean_env(overrides: dict[str, str] | None = None) -> dict[str, str]:
    """建構子行程環境：先濾掉會外溢的覆寫／逃生口變數，再套用本測試需要的值
    （不 `{**os.environ}` 直接洩漏，同根層 CLAUDE.md 逃生口洩漏普查紀律）。
    """
    env = {k: v for k, v in os.environ.items() if k not in _EXCLUDED_ENV_KEYS}
    if overrides:
        env.update(overrides)
    return env


def _run_nested_pytest(args: list[str], *, env_overrides: dict[str, str] | None = None):
    return subprocess.run(
        [sys.executable, "-m", "pytest", *args],
        cwd=str(LATEST_DIR),
        env=_clean_env(env_overrides),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


def test_env_override_is_honored_end_to_end() -> None:
    """(i) `PYTEST_XDIST_AUTO_NUM_WORKERS=2` 覆寫：真跑 pytest，worker 數與
    node 數皆須落在覆寫值上。用固定 2（非 `-n <cpu 全量>`）避免資源爆炸。
    """
    proc = _run_nested_pytest(
        [TARGET_TEST_REL, "-n", "auto", "-q", "-p", "no:cacheprovider"],
        env_overrides={"PYTEST_XDIST_AUTO_NUM_WORKERS": "2"},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "[cpu_budget] xdist workers=2 source=env" in proc.stdout, proc.stdout
    assert "[cpu_budget] xdist nodes confirmed=2" in proc.stdout, proc.stdout


_WORKERS_LINE_RE = re.compile(r"\[cpu_budget\] xdist workers=(\d+) source=cpu_budget")


def test_no_override_falls_back_to_cpu_budget_script() -> None:
    """(ii) 無覆寫：worker 數須等於獨立呼叫 `cpu_budget.py --legs 1` 的輸出
    （同一把尺，不是各自算各的）。"""
    proc = _run_nested_pytest([TARGET_TEST_REL, "-n", "auto", "-q", "-p", "no:cacheprovider"])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    match = _WORKERS_LINE_RE.search(proc.stdout)
    assert match, f"未見 source=cpu_budget 行，實得：\n{proc.stdout}"
    observed = int(match.group(1))

    expected_proc = subprocess.run(  # child-encoding-ok: cpu_budget.py 只印一個 ASCII 整數，無 CJK 輸出風險
        [sys.executable, str(CPU_BUDGET_SCRIPT), "--legs", "1"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert expected_proc.returncode == 0, expected_proc.stdout + expected_proc.stderr
    expected = int(expected_proc.stdout.strip())
    assert observed == expected, (
        f"conftest 算出的 worker 數（{observed}）與獨立呼叫 "
        f"cpu_budget.py --legs 1（{expected}）不一致"
    )


def test_no_xdist_does_not_internalerror() -> None:
    """(iii) `-p no:xdist -o addopts=`：hookspec 不存在，`optionalhook=True`
    缺席會讓 pluggy 對未知 hookimpl 拋 PluginValidationError ⇒ INTERNALERROR。
    """
    proc = _run_nested_pytest([TARGET_TEST_REL, "-q", "-p", "no:xdist", "-o", "addopts="])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    combined = proc.stdout + proc.stderr
    assert "INTERNALERROR" not in combined, combined
    assert "[cpu_budget]" not in proc.stdout, proc.stdout
