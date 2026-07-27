#!/usr/bin/env python3
"""nightly 載具的直譯器必須「決定性 + 可取證」（DEF-101-506，紀律 #14 延伸）。

WHY（2026-07-27 真機事故）：`run_local_nightly.ps1` 把直譯器存成字面 token
`$script:PyExe = 'python'`，每個呼叫點都由 PATH **現場解析**。於是同一支 nightly：

  - schtasks 排程下 → pyenv-win 的 python（`python.bat` shim，且裝了 psycopg2）
  - 已啟用 monorepo .venv 的終端機／agent 下 → `.venv\\Scripts\\python.exe`
    （真 .exe，且**未**裝 `[postgres,pgvector]` 選配）

兩者跑出來的紅綠不可互相比較：實測一次以 .venv 跑出 `pg-e2e=1`（psycopg2 缺席）
與 `perf=1` 兩個假紅並寫進 `nightly_latest.log`；更隱蔽的是它讓 DEF-101-503
（`%` 被 batch shim 吃掉）的修復「綠得沒有鑑別力」——真 .exe 本來就不觸發該 bug，
沒修也會綠。而 log 當時只印字面 token「python」，事後完全無法指認是哪一顆。

本檔鎖三件事（皆為行級靜態檢查，不執行載具）：
  A. `.ps1` 必須有「已啟用 venv → 自本行程 PATH 移除其 Scripts」的正規化區塊，
     且必須有「移除後找不到 python 就還原」的降級分支（載具正規化不得讓整晚
     驗證開天窗）。
  B. 兩支載具都必須把**解析後的直譯器路徑**寫進 log（禁止只印字面 token）。
  C. mac 側必須維持「絕對路徑釘死」而非 PATH 現場解析。

刻意不鎖「兩平台必須用同一顆直譯器」：mac 釘 `.venv/bin/python`、Windows 走
pyenv，是各自既有且各自綠的政策；本缺陷要根治的是「**同一平台上因啟動方式不同
而漂移**」，不是強推跨平台統一（那會讓 Windows 排程失去 psycopg2）。
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PS1 = _ROOT / "AutoClaude" / "tools" / "run_local_nightly.ps1"
_SH = _ROOT / "AutoClaude" / "tools" / "run_local_nightly.sh"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


class TestCarrierFilesExist(unittest.TestCase):
    def test_both_carriers_present(self):
        """檔案改名/搬家時本檔其餘斷言會全部靜默失效，先釘存在性。"""
        self.assertTrue(_PS1.is_file(), f"找不到 {_PS1}")
        self.assertTrue(_SH.is_file(), f"找不到 {_SH}")


class TestWindowsInterpreterNormalization(unittest.TestCase):
    """A：Windows 側必須主動把「已啟用 venv」正規化掉，使解析與 schtasks 等價。"""

    def test_has_virtual_env_detection(self):
        self.assertRegex(
            _read(_PS1), r"if\s*\(\s*\$env:VIRTUAL_ENV\s*\)",
            "run_local_nightly.ps1 必須偵測 $env:VIRTUAL_ENV——否則已啟用 venv 的終端機/"
            "agent 跑出來的紅綠與 schtasks 排程不可比較（DEF-101-506）")

    def test_removes_active_venv_scripts_from_path(self):
        text = _read(_PS1)
        self.assertIn("$env:PATH -split ';'", text,
                      "必須實際重組 PATH 以移除 venv Scripts，不能只印警告了事")
        self.assertRegex(text, r"Join-Path\s+\$env:VIRTUAL_ENV\s+'Scripts'",
                         "必須以 VIRTUAL_ENV 推導出要移除的 Scripts 目錄")

    def test_post_strip_check_uses_real_python_guard(self):
        """移除 venv 後的『還有沒有 python』判斷必須用 Test-IsRealPython：若用裸
        Get-Command，PATH 上只剩 WindowsApps 空殼時會誤判為可用而不還原。"""
        text = _read(_PS1)
        strip_block = text.split("if ($env:VIRTUAL_ENV)", 1)[-1].split("try {", 1)[0]
        self.assertIn("Test-IsRealPython -CandidateName 'python'", strip_block,
                      "正規化區塊必須以 Test-IsRealPython 判斷，不可用裸 Get-Command")
        # guard SSOT 必須在正規化區塊之前 dot-source，否則上面那行是未定義函式
        self.assertLess(
            text.index("tools/lib/WindowsAppsGuard.ps1"), text.index("if ($env:VIRTUAL_ENV)"),
            "WindowsAppsGuard.ps1 必須在 venv 正規化區塊之前載入")

    def test_has_restore_fallback_when_no_other_python(self):
        """降級分支：移除後若沒有其他 python，必須還原，不可讓整晚驗證開天窗。"""
        text = _read(_PS1)
        self.assertIn("$pathBefore", text, "必須保留還原用的 PATH 快照")
        self.assertRegex(
            text, r"\$env:PATH\s*=\s*\$pathBefore",
            "必須有『找不到其他 python 就還原 PATH』的降級路徑（DEF-101-506）")


class TestInterpreterIsForensicallyLogged(unittest.TestCase):
    """B：兩支載具都要把解析後的直譯器寫進 log；只印字面 token 等於沒印。"""

    def test_ps1_logs_resolved_path_not_bare_token(self):
        text = _read(_PS1)
        # 必須解析出絕對路徑，且必須用**兩步式**取 .Source——鏈式
        # `(Get-Command ... -ErrorAction SilentlyContinue).Source` 在 StrictMode 3.0
        # 下 $null.Source 會拋例外（紀律 #14 後半，另有 test_run_local_nightly_static
        # 的機械鎖；本修復初稿即因寫成鏈式被它攔下）。
        # 用 $script:PyExe 而非裸 `python` 字面值：test_windowsapps_guard_cross_consistency
        # 的呼叫點層級判準要求檔內不得有裸字面值 python 呼叫（本修復初稿寫成
        # `Get-Command python` 而被它攔下）。
        self.assertRegex(
            text, r"\$pyCmd\s*=\s*Get-Command\s+\$script:PyExe",
            "run_local_nightly.ps1 必須解析出 python 絕對路徑供取證（DEF-101-506）")
        self.assertRegex(
            text, r"\$pyResolved\s*=\s*if\s*\(\s*\$pyCmd\s*\)",
            "取 .Source 必須兩步式（先存變數再判 $null），不可鏈式存取（紀律 #14）")
        self.assertRegex(
            text, r"可用性驗證通過[^\n]*\$pyResolved",
            "驗證通過的 log 行必須帶上解析後路徑 $pyResolved")
        # 反向鎖：不可退回舊寫法「python 可用性驗證通過…：$script:PyExe」
        self.assertNotRegex(
            text, r"可用性驗證通過[^\n]*：\$script:PyExe\"",
            "log 不可只印字面 token $script:PyExe（值恆為 'python'，無取證價值）")

    def test_sh_logs_resolved_path(self):
        self.assertRegex(
            _read(_SH), r"python 直譯器：",
            "run_local_nightly.sh 必須印出解析後的直譯器路徑，與 .ps1 側取證對稱")


class TestMacInterpreterStaysPinned(unittest.TestCase):
    """C：mac 側的「絕對路徑釘死」是它不受本缺陷影響的原因，不可被改回現場解析。"""

    def test_pins_venv_absolute_path(self):
        self.assertRegex(
            _read(_SH), r'PY="\$ROOT/\.venv/bin/python"',
            "run_local_nightly.sh 必須維持絕對路徑釘死；改回裸 `python` 會把 Windows "
            "側的啟動方式漂移問題複製到 mac（DEF-101-506）")


class TestDetectorItself(unittest.TestCase):
    """紀律「驗證鏡子自身要被驗證」：確認上面的反向鎖真的抓得到舊寫法。"""

    def test_old_bare_token_pattern_would_be_caught(self):
        legacy = 'Log "python 可用性驗證通過（非 WindowsApps 空殼）：$script:PyExe"'
        self.assertTrue(
            re.search(r"可用性驗證通過[^\n]*：\$script:PyExe\"", legacy),
            "反向鎖的 regex 必須能命中修復前的舊寫法，否則該斷言是空殼")


if __name__ == "__main__":
    unittest.main()
