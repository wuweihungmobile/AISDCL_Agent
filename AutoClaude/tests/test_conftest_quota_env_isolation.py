"""DEF-200-355 巢狀鎖：`tests/conftest.py` 的 `AUTOSDD_QUOTA_*` pin/還原機制。

背景：`autoclaude/utils/config.py` 的 `_quota_env` 讀根層同名環境變數（R82 C3
刻意的跨專案橋接），供 `TokenGuardConfig` 的「`quota_halt_pct` 必須 >
`quota_throttle_pct`」invariant 用。橋接本身合法；缺的是**測試 session 隔離**——
呼叫端殼層只 export 單一鍵（例如 `AUTOSDD_QUOTA_HALT_PCT=1`）而未同時 export 另外
兩鍵時，本場 session 內任何建構 `TokenGuardConfig()` 的測試都會撞
`pydantic.ValidationError`（修前實測：`tests/test_gap009.py` 31 failed/19 passed）。

覆蓋範圍：
  (a) in-process：`conftest._pop_quota_env_leaks()` 真的把洩漏鍵從 `os.environ`
      彈出，且記住原值。
  (b) 同一行程內第二次呼叫是 no-op（capture-once 防線；不設防線會用第二次的空
      字典覆寫掉第一次記住的真原值）。
  (c) `conftest._restore_quota_env_leaks()` 冪等：連續呼叫兩次不炸，原值只回來
      一次且不被第二次呼叫抹掉。
  (d) subprocess 行為鎖：DEF-200-355 本體回歸——單一 `AUTOSDD_QUOTA_HALT_PCT`
      洩入呼叫端環境時，`tests/test_gap009.py` 子行程仍全數通過。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
_AUTOCLAUDE_DIR = _TESTS_DIR.parent
_CONFTEST_PATH = (_TESTS_DIR / "conftest.py").resolve()


def _loaded_conftest():
    """本次 session 真的載進來的 `AutoClaude/tests/conftest.py` 模組物件。

    以 `__file__` 反查而不是 `import conftest`：conftest 的模組名取決於 rootdir 與
    有無 `__init__.py`，寫死名字會在別人調整佈局時變成假綠——沿用
    `tests/tools/test_local_ci_gate.py::_loaded_conftest` 既有慣例，不發明第二種。
    """
    for module in list(sys.modules.values()):
        path = getattr(module, "__file__", None)
        if path and Path(path).resolve() == _CONFTEST_PATH:
            return module
    return None


@pytest.fixture
def conftest():
    module = _loaded_conftest()
    assert module is not None, "找不到已載入的 AutoClaude/tests/conftest.py"
    return module


class TestPopQuotaEnvLeaksInProcess:
    """(a)(b) `_pop_quota_env_leaks()`：真的動作＋capture-once 防線。

    🔴 三個 in-process 測試皆以 `unittest.mock.patch.dict(os.environ, ..., clear=False)`
    包住整段（`test_r82_quota_axis_and_shipped_defaults.py` 既有慣例，不用
    `monkeypatch.setenv/delenv`）：被測函式本身會直接 `os.environ.pop`／`update`
    （backdoor 寫入，不經過 monkeypatch 的 undo-log 追蹤）——若改用 monkeypatch 在
    `finally` 呼叫 `delenv` 收尾，會在「key 存在」的當下註冊一筆「原值＝這個 backdoor
    寫入的值」的假還原點，監視器 fixture teardown 時把它當成本來就有的值寫回去，
    污染同一 xdist worker 之後的測試（本檔開發期間實測撞上
    `test_r82_quota_axis_and_shipped_defaults.py` 三支：`AUTOSDD_QUOTA_CONVERGE_PCT`
    洩漏值 `"42"` 讓 `TokenGuardConfig()` 預設斷言全部失焦）。`patch.dict` 在
    `__exit__` 整份字典級還原，不受呼叫序影響，沒有這個縫。
    """

    def test_pops_leaked_var_and_remembers_original_value(self, conftest):
        saved_module_state = conftest._POPPED_QUOTA_ENV
        # 模擬「本行程尚未 pin 過」：真實 session 早在 pytest_configure 就 pin 過一次
        # （capture-once），此處需重置守衛才能觀察到 pop 這一步本身的行為。
        conftest._POPPED_QUOTA_ENV = None
        try:
            with patch.dict(os.environ, {"AUTOSDD_QUOTA_HALT_PCT": "1"}, clear=False):
                popped = conftest._pop_quota_env_leaks()
                assert popped == {"AUTOSDD_QUOTA_HALT_PCT": "1"}, popped
                assert "AUTOSDD_QUOTA_HALT_PCT" not in os.environ
                assert conftest._POPPED_QUOTA_ENV == {"AUTOSDD_QUOTA_HALT_PCT": "1"}
        finally:
            conftest._POPPED_QUOTA_ENV = saved_module_state

    def test_second_call_in_same_process_is_a_noop(self, conftest):
        """已 pin 過的行程再呼叫一次必須是 no-op：不設防線會讓第二次呼叫用「彈不到
        東西」的空字典覆寫掉第一次記住的真原值（見類別 docstring）。"""
        saved_module_state = conftest._POPPED_QUOTA_ENV
        conftest._POPPED_QUOTA_ENV = {"AUTOSDD_QUOTA_HALT_PCT": "1"}  # 模擬已 pin 過
        try:
            with patch.dict(os.environ, {"AUTOSDD_QUOTA_CONVERGE_PCT": "70"}, clear=False):
                popped = conftest._pop_quota_env_leaks()
                assert popped == {}, popped
                assert os.environ.get("AUTOSDD_QUOTA_CONVERGE_PCT") == "70"  # 完全沒被動到
                # 原記憶未被覆寫：
                assert conftest._POPPED_QUOTA_ENV == {"AUTOSDD_QUOTA_HALT_PCT": "1"}
        finally:
            conftest._POPPED_QUOTA_ENV = saved_module_state


class TestRestoreQuotaEnvLeaksIdempotent:
    """(c) `_restore_quota_env_leaks()` 冪等：連續呼叫兩次不炸、原值只回來一次。"""

    def test_restore_twice_does_not_raise_and_keeps_value(self, conftest):
        saved_module_state = conftest._POPPED_QUOTA_ENV
        conftest._POPPED_QUOTA_ENV = {"AUTOSDD_QUOTA_CONVERGE_PCT": "42"}
        try:
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("AUTOSDD_QUOTA_CONVERGE_PCT", None)
                conftest._restore_quota_env_leaks()
                assert os.environ["AUTOSDD_QUOTA_CONVERGE_PCT"] == "42"
                assert conftest._POPPED_QUOTA_ENV is None

                conftest._restore_quota_env_leaks()  # 第二次（模擬 unconfigure 被呼叫超過一次）
                assert os.environ["AUTOSDD_QUOTA_CONVERGE_PCT"] == "42"  # 沒被動到
                assert conftest._POPPED_QUOTA_ENV is None  # 仍是 no-op
        finally:
            conftest._POPPED_QUOTA_ENV = saved_module_state


class TestGap009SubprocessQuotaEnvLeak:
    """(d) subprocess 行為鎖：DEF-200-355 本體回歸。"""

    def test_gap009_passes_with_leaked_halt_pct_env(self):
        """呼叫端殼層只洩入 `AUTOSDD_QUOTA_HALT_PCT=1`（未同時洩入其餘兩鍵）時，
        修前會撞 `TokenGuardConfig` 的 halt>throttle invariant（31 failed/19
        passed）；修後本檔的 pin 讓子行程的 pytest session 看不到這族洩漏鍵，
        50 支全數通過。"""
        env = {**os.environ, "AUTOSDD_QUOTA_HALT_PCT": "1"}
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_gap009.py",
             "-q", "-p", "no:xdist", "-o", "addopts=", "-p", "no:cacheprovider"],
            cwd=_AUTOCLAUDE_DIR, env=env,
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "50 passed" in result.stdout, result.stdout
