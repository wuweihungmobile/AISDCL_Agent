#!/usr/bin/env python3
"""交叉一致性鎖：Windows Store App Execution Alias（WindowsApps 空殼）排除
guard 第 4 個獨立實作缺測試覆蓋（R34 Architect 架構深度評估發現的缺口）。

同一條規則（排除 WindowsApps 底下的 python.exe/python3.exe 空殼別名，未真裝
Python 時 `Get-Command python` 仍會找到它，執行只會跳出 Microsoft Store 提示）
目前有三處獨立實作：
  - `tools/bootstrap.ps1`（DEF-101-273/279）—— 已有
    `tools/tests/test_bootstrap_ps1.py::TestBootstrapWindowsAppsGuard` 回歸鎖。
  - `tools/bootstrap_core.py::_is_windows_apps_stub()`（DEF-101-281，對稱補齊）
    —— 已有既有單元測試覆蓋。
  - `tools/dev_start.ps1`（第 38-41 行）—— 本檔動工前**零測試覆蓋**：
    `tools/tests/test_dev_start.py` 只測 Python 核心 `tools/dev_start.py`，
    完全未觸及 `.ps1` 薄殼的直譯器選取分支；`check_wrapper_thinness.py` 只釘
    SHA256（偵測「有沒有改」），不驗證語意正確性。

三處保持獨立實作是既有架構決策（dev_start.ps1 需在呼叫 Python 核心「之前」
自行找到直譯器，屬 bootstrapping 先有雞或蛋的限制，不能合併成單一函式）。
本檔比照 `test_windows_forbidden_filename_parity.py`（DEF-101-295）同款手法，
只負責「漂移即知」：① 補 dev_start.ps1 的行為回歸鎖（比照
`test_bootstrap_ps1.py` 既有寫法）；② 靜態文字擷取交叉核對三處 guard 語意
一致（皆排除路徑中含 `WindowsApps` 區段的裸名 python/python3 候選）。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BOOTSTRAP_PS1 = _REPO_ROOT / "tools" / "bootstrap.ps1"
_DEV_START_PS1 = _REPO_ROOT / "tools" / "dev_start.ps1"
_BOOTSTRAP_CORE_PY = _REPO_ROOT / "tools" / "bootstrap_core.py"


def _windows_pwsh_available() -> bool:
    """同 `test_bootstrap_ps1.py::_windows_pwsh_available()`：僅供依賴 Windows
    PATHEXT／`.cmd` 解析語意的測試使用；本檔目前無此類情境（dev_start.ps1 無
    python3 候選、無「空殼排前面仍選到真直譯器」的優先序測試），保留此函式僅為
    未來若擴充同類情境時沿用同款判準，避免下次又漏寫。
    """
    return sys.platform.startswith("win") and (
        shutil.which("powershell") is not None or shutil.which("pwsh") is not None
    )


# ---------------------------------------------------------------------------
# 靜態交叉一致性：三處 guard 皆須表達「排除路徑含 WindowsApps 區段」同一語意
# ---------------------------------------------------------------------------
class TestWindowsAppsGuardStaticParity(unittest.TestCase):
    def test_bootstrap_ps1_and_dev_start_ps1_use_same_notlike_pattern(self) -> None:
        """兩份 .ps1 對裸名 python 候選皆須用 `-notlike '*\\WindowsApps\\*'`
        排除 `.Source`——非要求逐字相同程式碼（候選清單本就刻意不同，見兩檔
        docstring），只鎖住「排除語意的字面 pattern」不得漂移。
        """
        pattern = re.compile(r"-notlike\s+'\*\\WindowsApps\\\*'")
        bootstrap_text = _BOOTSTRAP_PS1.read_text(encoding="utf-8")
        dev_start_text = _DEV_START_PS1.read_text(encoding="utf-8")
        self.assertTrue(
            pattern.search(bootstrap_text),
            "tools/bootstrap.ps1 找不到 WindowsApps -notlike 排除 pattern——guard 是否被改寫或移除？",
        )
        self.assertTrue(
            pattern.search(dev_start_text),
            "tools/dev_start.ps1 找不到 WindowsApps -notlike 排除 pattern——guard 是否被改寫或移除？",
        )

    def test_dev_start_ps1_guard_applies_to_source_property(self) -> None:
        """guard 必須比對 `Get-Command` 結果的 `.Source`（解析後的實際路徑），
        不能誤比對候選名稱字串本身（那樣永遠不會命中，guard 形同虛設）。
        """
        text = _DEV_START_PS1.read_text(encoding="utf-8")
        m = re.search(r"\$PyCand\.Source\s+-notlike\s+'\*\\WindowsApps\\\*'", text)
        self.assertIsNotNone(
            m, "dev_start.ps1 的 WindowsApps guard 未對 $PyCand.Source 做排除比對"
        )

    def test_dev_start_ps1_guard_uses_and_not_or(self) -> None:
        """R34 一審 Architect 用 bug-injection 發現：把 `-and` 改成 `-or`
        （`if ($PyCand -or $PyCand.Source -notlike ...)`）會讓 guard 對任何
        已解析到的候選（含 WindowsApps 空殼本身，因為 `-or` 短路時左側
        `$PyCand` truthy 就足以放行）完全失效，但先前只驗證 `-notlike` 這個
        字面 pattern 存在，抓不到這個布林運算子反轉——比字面上「拔掉整個
        guard」更隱蔽。本測試鎖住 `$PyCand` 與 `$PyCand.Source -notlike ...`
        之間必須是 `-and`。
        """
        text = _DEV_START_PS1.read_text(encoding="utf-8")
        m = re.search(r"\$PyCand\s+(-and|-or)\s+\$PyCand\.Source\s+-notlike", text)
        self.assertIsNotNone(m, "dev_start.ps1 找不到 $PyCand 與 .Source -notlike 之間的布林運算子")
        self.assertEqual(
            m.group(1),
            "-and",
            "dev_start.ps1 guard 的布林運算子須為 -and——-or 會讓 guard 形同虛設"
            "（R34 一審 Architect bug-injection 發現的隱蔽反轉手法）",
        )

    def test_bootstrap_ps1_guard_covers_both_python_and_python3_branches(self) -> None:
        """R34 一審 SD 用 bug-injection 發現：`bootstrap.ps1` 有兩處獨立 guard
        （`python`／`python3` 候選各一），先前的靜態測試用 `re.search()` 只需
        命中一次即通過——只破壞其中一處（如 python3 分支）會被漏放行（假綠）。
        本測試改用 `findall` 確認兩處皆完整存在（`$PyCand`／`$Py3Cand` 各自的
        `-and ... -notlike` 完整語意，非僅字面 pattern 出現次數）。
        """
        text = _BOOTSTRAP_PS1.read_text(encoding="utf-8")
        matches = re.findall(
            r"\$(Py3?Cand)\s+-and\s+\$\1\.Source\s+-notlike\s+'\*\\WindowsApps\\\*'",
            text,
        )
        self.assertEqual(
            sorted(matches),
            ["Py3Cand", "PyCand"],
            "tools/bootstrap.ps1 應恰有兩處完整 guard（python 候選用 $PyCand、"
            f"python3 候選用 $Py3Cand，皆為 -and 語意），實際找到：{matches}",
        )

    def test_dev_start_ps1_guard_condition_closes_immediately_after_windowsapps_check(
        self,
    ) -> None:
        """R34 二審 Architect 用第三輪 bug-injection 發現：在既有 `-notlike`
        子句「後面」疊加一段恆真子句（如 `-notlike '*\\WindowsApps\\*' -or
        $true`）能繞過前兩項測試——它們只錨定運算式「中段」的運算子/pattern，
        未驗證 WindowsApps 排除後條件式是否立即收尾。`-or $true` 在 PowerShell
        中因運算子優先序會讓整條 `if` 判斷式恆真，guard 形同虛設，卻不影響
        `-and`／pattern 存在性的斷言。本測試改錨定整條 `if (...)`：
        `-notlike '*\\WindowsApps\\*'` 之後必須緊接 `)`（僅容許空白），中間
        不得插入任何其他 token。
        """
        text = _DEV_START_PS1.read_text(encoding="utf-8")
        m = re.search(
            r"if\s*\(\$PyCand\s+-and\s+\$PyCand\.Source\s+-notlike\s+'\*\\WindowsApps\\\*'\s*\)",
            text,
        )
        self.assertIsNotNone(
            m,
            "dev_start.ps1 的 guard 條件式在 WindowsApps 排除後未立即收尾——"
            "疑似被追加了額外邏輯（如 -or $true 之類恆真子句）繞過整個 guard",
        )

    def test_bootstrap_ps1_guard_conditions_close_immediately_after_windowsapps_check(
        self,
    ) -> None:
        """同上（R34 二審 Architect 發現），鎖 bootstrap.ps1 兩處（python/python3
        分支）皆須在 WindowsApps 排除後立即收尾，不得被疊加恆真子句繞過。
        """
        text = _BOOTSTRAP_PS1.read_text(encoding="utf-8")
        matches = re.findall(
            r"if\s*\(\$(Py3?Cand)\s+-and\s+\$\1\.Source\s+-notlike\s+'\*\\WindowsApps\\\*'\s*\)",
            text,
        )
        self.assertEqual(
            sorted(matches),
            ["Py3Cand", "PyCand"],
            "tools/bootstrap.ps1 應恰有兩處 guard 條件式在 WindowsApps 排除後"
            f"立即收尾（不得被疊加恆真子句繞過），實際找到：{matches}",
        )

    def test_bootstrap_core_py_has_symmetric_stub_detector(self) -> None:
        """Python 核心側（bootstrap_core.py）須有對稱的 WindowsApps 空殼偵測，
        且比對邏輯為「路徑分段」（非任意子字串），避免 `C:\\FooWindowsAppsBar\\`
        這類非真實 WindowsApps 路徑被誤判命中（DEF-101-281 既有設計）。
        """
        text = _BOOTSTRAP_CORE_PY.read_text(encoding="utf-8")
        self.assertIn("_is_windows_apps_stub", text)
        self.assertIn('part.lower() == "windowsapps"', text)


# ---------------------------------------------------------------------------
# 行為回歸鎖：dev_start.ps1 本身（R34 前零覆蓋的第 4 個獨立實作）
# ---------------------------------------------------------------------------
@unittest.skipIf(
    shutil.which("powershell") is None and shutil.which("pwsh") is None,
    "需要 powershell/pwsh",
)
class TestDevStartPs1WindowsAppsGuard(unittest.TestCase):
    def _run(self, path_dirs: list[Path]) -> subprocess.CompletedProcess:
        # dev_start.ps1 選直譯器前會先檢查 `$Root/.venv/Scripts/python.exe`
        # （$Root 由 $PSScriptRoot 反推）——若直接對本 repo 的真實 dev_start.ps1
        # 下手，本機既有 .venv 會讓 Test-Path 短路成功，guard 分支永遠不會被
        # 執行到。故複製一份到零 .venv 的臨時 fake <root>/tools/ 結構下執行，
        # 讓 $Root 解析到乾淨臨時目錄（同 test_bootstrap_ps1.py 手法的延伸——
        # 該檔的 bootstrap.ps1 本身無 .venv 短路分支，不需此步）。
        exe = shutil.which("powershell") or shutil.which("pwsh")
        with tempfile.TemporaryDirectory() as fake_root_td:
            fake_tools = Path(fake_root_td) / "tools"
            fake_tools.mkdir(parents=True)
            fake_ps1 = fake_tools / "dev_start.ps1"
            fake_ps1.write_text(_DEV_START_PS1.read_text(encoding="utf-8"), encoding="utf-8")
            env = dict(os.environ)
            env["PATH"] = os.pathsep.join(str(p) for p in path_dirs)
            cmd = (
                "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
                f"& '{fake_ps1}'"
            )
            return subprocess.run(
                [exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=30, env=env,
            )

    def test_windowsapps_only_python_stub_is_skipped_and_reports_not_found(self) -> None:
        """PATH 上只有一個位於 WindowsApps 路徑下的 python.exe 空殼、無 py 時，
        dev_start.ps1 必須跳過該空殼並回報「找不到 Python 直譯器」，而不是把
        空殼當真直譯器去呼叫 tools/dev_start.py（那樣只會跳出 Store 提示，
        永遠不會真正整備環境）——與 bootstrap.ps1 既有回歸鎖同款情境。

        已知侷限（bug-injection 驗證時發現，如實揭露）：在 macOS/Linux 上的
        `pwsh`，`Get-Command python` 不會透過 Windows PATHEXT 語意把裸名
        `python` 解析到 `python.exe`——即使把本測試用的 guard 暫時拔掉（改為
        `if ($PyCand) { ... }`），`$PyCand` 在 macOS pwsh 上仍恆為 null，本測試
        會因「本來就找不到任何 python」而通過，並非真的驗證了 guard 邏輯本身
        （`test_bootstrap_ps1.py` 同款寫法的等價測試亦有此侷限）。本測試在真
        Windows PowerShell（PATHEXT 生效）上才具備鑑別力——CI 端
        `windows-compat-ci.yml` 於 `windows-latest` runner 執行，該環境才是本測
        試實際發揮回歸鎖作用之處。
        """
        with tempfile.TemporaryDirectory() as td:
            stub_dir = Path(td) / "WindowsApps"
            stub_dir.mkdir()
            (stub_dir / "python.exe").write_bytes(b"")
            proc = self._run([stub_dir])
            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("找不到", proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
