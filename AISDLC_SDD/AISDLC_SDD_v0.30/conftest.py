"""版本樹 rootdir conftest：把共用層的 `[WINDOWS-NATIVE-ONLY]` skip 可見度機制
接進**官方閘門實際走的那條路徑**（R67-F27）。

WHY（這支檔案為何非存在不可）：
`AISDLC_SDD/conftest.py`（共用層）自己的 docstring 就寫明——`cd vX && pytest`
（＝ `scripts/ci-gate.sh` 的呼叫形態）時 rootdir=vX，共用層 conftest 落在
confcutdir **之上**，「不載入/不干擾」。而 R44 把 `pytest_terminal_summary`
掛在那支共用層 conftest 上，於是該機制對版本樹**結構上不可達**：官方閘門每天
跑的 v0.01／LATEST 兩軌完全看不到 `WINDOWS-NATIVE-ONLY SKIPS` 區塊，只有
`scripts/tests/` 那一軌看得到。實測佐證（同一支探針檔複製到兩棵樹、唯一變因是
所在樹）：`scripts/tests/` 印出區塊、版本樹零區塊；而 LATEST 樹裡本來就住著一支
未被彙整的真 Windows-only skip（`tools/fsm_runtime/tests/test_file_lock.py`
的 `skipUnless(sys.platform == "win32")`）。

為何用 rootdir conftest 而不是改 `scripts/ci-gate.sh` 加 `-p` 外掛：
  1. 載入時機由 pytest 自身保證——只要 rootdir 是本目錄，**任何**呼叫形態都會
     載入（含開發者手打的 `cd vX && pytest tools/fsm_runtime/tests/xxx.py`），
     不必每個呼叫點都記得帶旗標；閘門腳本漏帶旗標＝機制再次靜默消失。
  2. Copy-on-Evolve（ADR-XPLAT-001）以 `git archive HEAD:<LATEST>` 複製整棵樹，
     本檔會自動隨新版傳播，不需要有人記得為 v0.31 再接一次線。

為何**不**同步補進凍結基線 `AISDLC_SDD_v0.01/`：ADR-XPLAT-001 明令凍結版不得
原地修改。且實查該樹的 Windows 條件式 skip 為**零筆**（回歸鎖
`scripts/tests/test_conftest_windows_native_skip_report.py::
test_frozen_baseline_has_no_windows_conditional_skips` 機械守住這件事），故未接線
在該樹上的實際曝險為 0；凍結版永不新增測試，該前提不會腐化。

實作刻意只借用共用層的**函式**（不 re-export `pytest_configure`）：那支是
DEF-02-001 跨版同跑 guard，語意屬於「bare 呼叫」情境，與本檔無關。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SHARED_CONFTEST = Path(__file__).resolve().parent.parent / "conftest.py"

# 以唯一模組名載入共用層：不能用 `from conftest import ...`——在 pytest 的
# prepend import 模式下，無 `__init__.py` 的 conftest.py 會以模組名 `conftest`
# 註冊，直接 import 同名模組必然互撞。
_spec = importlib.util.spec_from_file_location("_sdd_shared_conftest", _SHARED_CONFTEST)
if _spec is None or _spec.loader is None:  # pragma: no cover - 只有共用層被刪才會發生
    raise RuntimeError(f"共用層 conftest 不存在或無法載入：{_SHARED_CONFTEST}")
_shared = importlib.util.module_from_spec(_spec)
# 共用層 conftest 於載入期會 `sys.path.insert(0, .../scripts)`（DEF-02-001 guard
# 的相依）。本檔只要它的函式，不要那個副作用外溢進版本樹 session 的 import 解析，
# 故 exec 前後快照/還原 sys.path——版本樹的測試自有其 sys.path 佈署慣例。
_saved_sys_path = list(sys.path)
try:
    _spec.loader.exec_module(_shared)
finally:
    sys.path[:] = _saved_sys_path

WINDOWS_NATIVE_SKIP_TAG = _shared.WINDOWS_NATIVE_SKIP_TAG
windows_native_skips = _shared.windows_native_skips
pytest_terminal_summary = _shared.pytest_terminal_summary
