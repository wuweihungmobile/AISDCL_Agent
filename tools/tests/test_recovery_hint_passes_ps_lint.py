#!/usr/bin/env python3
"""跨專案回歸鎖（DEF-200-340 修法）：AISDLC_SDD LATEST 的
`tools/fsm_runtime/recovery_hint.py::recovery_command(shell="powershell")` 產出的一行指令，
必須通過根層 `.claude/hooks/lint_powershell_command.py` 的 PowerShell 判準。

WHY（Rule 9）：兩支檔案分屬兩個子專案，彼此刻意不跨 import；`recovery_command()` 印給人在
終端貼上執行的指令，若被同一根 session 的 `lint_powershell_command.py` 判定為裸 `Set-Location`
（任何帶參數的 `Set-Location` 皆擋——鐵律二只放行同一呼叫內成對的
`Push-Location`/`Pop-Location`），使用者會被自己的護欄擋下自己的恢復指令，形同鎖死。
本檔以「正向零命中＋負向有鑑別力」雙格鎖住此修法，任一邊單獨改動即紅。

LATEST 版本一律經 `tools/lib/sdd_latest.py` 的 SSOT 現查，不得寫死版號（版本狀態的唯一出處）。
LATEST 的 `recovery_hint` 內含相對匯入（`from .fsm_runtime import …`），不能單檔
`spec_from_file_location`；也不在本行程 `sys.path.insert` LATEST 根（那會與根層 `tools`
命名空間互撞，且 `AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py` 的
靜態解析面對 `sdd_latest.resolve_latest_root()` 這種呼叫解不出目標）。比照
`test_component_sanitizer_shared_layer_lock.py` 既有手法：子行程以 LATEST 根為 cwd／sys.path
匯入真套件，把產物印回本行程比對。
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
import sdd_latest  # noqa: E402

_SDD_ROOT = sdd_latest.resolve_latest_root(_REPO_ROOT / "AISDLC_SDD")

#: 子行程內跑的一小段：在 LATEST 根匯入真套件，印出 PowerShell 形態的恢復指令。
_CHILD = """
import json, sys
from pathlib import Path
sys.path.insert(0, {root!r})
from tools.fsm_runtime import recovery_hint as rh
cmd = rh.recovery_command(
    sdd_root=Path("C:/x y/AISDLC_SDD"),  # platform-ok: 餵 lint 的 Windows 字面
    python="C:/x/.venv/Scripts/python.exe",  # platform-ok: 餵 lint 的 Windows 字面
    target="SPEC_DRAFTING", reason="test", shell="powershell", exists=lambda p: True)
print(json.dumps(cmd))
"""


def _latest_powershell_recovery_command() -> str:
    """在 LATEST 根以子行程取 `recovery_command(shell="powershell")` 的實際產物。"""
    proc = subprocess.run(
        [sys.executable, "-c", _CHILD.format(root=str(_SDD_ROOT))],
        cwd=str(_SDD_ROOT), capture_output=True, text=True, encoding="utf-8", timeout=60,
        check=False,
    )
    assert proc.returncode == 0, f"子行程失敗 rc={proc.returncode}\n{proc.stderr}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _load_ps_lint_hook():
    """以檔案路徑載入根層 `.claude/hooks/lint_powershell_command.py`（該目錄不是套件；
    比照 `tools/tests/test_pre_commit_dispatcher_sigpipe.py::_load_hook_path_scope` 手法）。"""
    path = _REPO_ROOT / ".claude" / "hooks" / "lint_powershell_command.py"
    assert path.is_file(), f"找不到 lint_powershell_command.py：{path}"
    spec = importlib.util.spec_from_file_location("_recovery_hint_ps_lint_hook", path)
    assert spec is not None and spec.loader is not None, f"無法載入 {path}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ps_lint = _load_ps_lint_hook()


class RecoveryCommandPassesPowerShellLintTests(unittest.TestCase):
    """正向：修好後的 PowerShell 指令必須不再命中 naked-cd 判準；
    負向自證：舊模板字面（`Set-Location` 版）必須仍然命中，證明本鎖有鑑別力
    （不是判準本身失去偵測力而巧合放行）。posix 形態不在此鎖射程——該 hook 只管 PowerShell。
    """

    def test_powershell_recovery_command_has_zero_lint_hits(self) -> None:
        cmd = _latest_powershell_recovery_command()
        self.assertTrue(cmd.startswith('Push-Location "'), cmd)
        self.assertTrue(cmd.endswith("; Pop-Location"), cmd)
        hits = ps_lint.lint_command(cmd)
        self.assertEqual(hits, [], f"修好後仍被 lint 命中：cmd={cmd!r} hits={hits!r}")

    def test_old_set_location_template_is_still_caught_by_lint(self) -> None:
        """負向自證：DEF-200-340 修法前的舊字面模板，餵同一函式必須命中非空——
        證明本鎖確實在偵測「裸 Set-Location」這件事，不是巧合放行。"""
        old_template = (
            'Set-Location "C:/x y/AISDLC_SDD"; & '  # platform-ok: 餵 lint 的 Windows 字面
            '"C:/x/.venv/Scripts/python.exe" '  # platform-ok: 餵 lint 的 Windows 字面
            '-m tools.fsm_runtime.fsm_runtime '
            'resume-from-escalation --to SPEC_DRAFTING --reason "test"'
        )
        hits = ps_lint.lint_command(old_template)
        self.assertNotEqual(hits, [], "舊 Set-Location 模板應被 lint 命中，本鎖才有鑑別力")


if __name__ == "__main__":
    unittest.main()
