#!/usr/bin/env python3
"""tools/_stdio_utf8.py 的單元測試（R4 複審 QA P3：補齊零測試覆蓋缺口）。

背景：`reconfigure_stdio_utf8()` 是 `dev_start.py` / `check_ntfs_paths.py` /
`check_script_parity.py` 三支根層 CLI 工具共用的 Windows 非 UTF-8 終端崩潰防護
（DEF-101-069），卻從未有任何單元測試鎖住其行為契約：
  1. 對沒有 `reconfigure` 屬性的 stream（如測試用 `io.StringIO()`）必須安全跳過，
     不可拋 AttributeError。
  2. `reconfigure()` 拋 `OSError`/`ValueError` 時必須被吞掉，不可向外傳播（例如被導向
     的 stdout 在某些平台上 reconfigure 會失敗）。
  3. 正常情況下（stream 有 `reconfigure` 且成功）必須真的呼叫到，且帶正確參數
     （`encoding="utf-8", errors="replace"`）。

R58 補充第 4 條（DEF-101-511）：上述 1~3 全為 in-process mock，**沒有任何 case 真的
在 legacy（非 UTF-8）locale 下跑過一支腳本**。而本 session 的 `.claude/settings.json`
注入 `env.PYTHONUTF8=1` 到所有子行程，於是每一次驗證都在 UTF-8 mode 下進行——與使用者
真實情境（雙擊開 Windows PowerShell 5.1、直接跑 `.venv\\Scripts\\python.exe tools\\xxx.py`，
ACP=950）不等價。後果與 DEF-101-506 認定的缺陷同型：**綠得沒有鑑別力**，任何依賴
locale 預設編碼的退化（例如有人把 `import _stdio_utf8` 那行刪掉）在 session 內驗證
永遠不會翻紅。`TestLegacyLocaleDiscrimination` 補上這條真的會紅的路徑。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import io
import locale
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _stdio_utf8 as m  # noqa: E402

_TOOLS_DIR = Path(__file__).resolve().parents[1]
# legacy locale 載具的取證對象＝真的 `import _stdio_utf8` 的根層 CLI 工具之一。
# 選它的理由：唯讀、快、零副作用（dev_start.py 會真的啟動東西，不適合當載具）。
_CARRIER = _TOOLS_DIR / "check_defect_log_crossref.py"
# 探針故意印 cp950 等 legacy 碼頁編不出來的符號（與本 repo CLI 實際輸出的 ✅/❌/⚠️
# 同族）。傳給 `-c` 的原始碼一律以 `ascii()` 轉成純 ASCII 字面值：argv 在 POSIX 是
# 依 filesystem encoding 解碼的，legacy locale 下夾 raw 非 ASCII 會把「載具自己的
# 編碼問題」混進被測結果。
_PROBE_EXPECTED = "✅ ❌ ⚠️ 中文"
_PROBE_UNGUARDED = f"print({ascii(_PROBE_EXPECTED)})"
_PROBE_GUARDED = (
    f"import sys; sys.path.insert(0, {ascii(str(_TOOLS_DIR))}); import _stdio_utf8; "
    f"print({ascii(_PROBE_EXPECTED)})"
)
_PROBE_GUARDED_STDERR = (
    f"import sys; sys.path.insert(0, {ascii(str(_TOOLS_DIR))}); import _stdio_utf8; "
    f"sys.stderr.write({ascii(_PROBE_EXPECTED)})"
)


def _legacy_env() -> dict[str, str]:
    """把 session 注入的 UTF-8 強制設定拔掉，還原「使用者裸終端」的環境。"""
    env = os.environ.copy()
    env.pop("PYTHONUTF8", None)
    env.pop("PYTHONIOENCODING", None)
    return env


def _run_legacy(args: list[str]) -> subprocess.CompletedProcess[bytes]:
    """以 legacy locale（`-X utf8=0` + 拔掉 PYTHONUTF8/PYTHONIOENCODING）跑子行程。

    刻意**不**用 `text=True`：要拿原始 bytes 自行判讀編碼，否則載具自身的解碼行為
    會蓋掉被測對象真正吐出的位元組（那正是本測試要看的東西）。
    """
    return subprocess.run(
        [sys.executable, "-X", "utf8=0", *args],
        capture_output=True,
        env=_legacy_env(),
    )


class TestReconfigureStdioUtf8(unittest.TestCase):
    def test_stream_without_reconfigure_skipped_safely(self) -> None:
        """StringIO 沒有 reconfigure 屬性 —— hasattr 守門必須讓函式安全跳過，零副作用、
        不拋 AttributeError（docstring 明文承諾的守門行為）。"""
        fake_stdout = io.StringIO()
        fake_stderr = io.StringIO()
        self.assertFalse(hasattr(fake_stdout, "reconfigure"))
        with mock.patch.object(sys, "stdout", fake_stdout), \
                mock.patch.object(sys, "stderr", fake_stderr):
            m.reconfigure_stdio_utf8()  # 不應拋例外

    def test_reconfigure_oserror_swallowed(self) -> None:
        """reconfigure() 拋 OSError 時必須被吞掉，不向外傳播。"""
        fake_stdout = mock.Mock()
        fake_stdout.reconfigure.side_effect = OSError("boom")
        fake_stderr = mock.Mock()
        fake_stderr.reconfigure.side_effect = OSError("boom")
        with mock.patch.object(sys, "stdout", fake_stdout), \
                mock.patch.object(sys, "stderr", fake_stderr):
            m.reconfigure_stdio_utf8()  # 不應拋例外
        fake_stdout.reconfigure.assert_called_once()
        fake_stderr.reconfigure.assert_called_once()

    def test_reconfigure_valueerror_swallowed(self) -> None:
        """reconfigure() 拋 ValueError 時同樣必須被吞掉，不向外傳播。"""
        fake_stdout = mock.Mock()
        fake_stdout.reconfigure.side_effect = ValueError("boom")
        fake_stderr = mock.Mock()
        fake_stderr.reconfigure.side_effect = ValueError("boom")
        with mock.patch.object(sys, "stdout", fake_stdout), \
                mock.patch.object(sys, "stderr", fake_stderr):
            m.reconfigure_stdio_utf8()  # 不應拋例外
        fake_stdout.reconfigure.assert_called_once()
        fake_stderr.reconfigure.assert_called_once()

    def test_reconfigure_called_with_utf8_when_available(self) -> None:
        """正常情況（stream 有 reconfigure 且成功）必須真的呼叫到，且帶
        encoding="utf-8", errors="replace"（防未來重構悄悄改掉參數）。"""
        fake_stdout = mock.Mock()
        fake_stderr = mock.Mock()
        with mock.patch.object(sys, "stdout", fake_stdout), \
                mock.patch.object(sys, "stderr", fake_stderr):
            m.reconfigure_stdio_utf8()
        fake_stdout.reconfigure.assert_called_once_with(encoding="utf-8", errors="replace")
        fake_stderr.reconfigure.assert_called_once_with(encoding="utf-8", errors="replace")


class TestLegacyLocaleDiscrimination(unittest.TestCase):
    """legacy（非 UTF-8）locale 下的真實行為鎖（DEF-101-511）。

    WHY：`.claude/settings.json` 的 `env.PYTHONUTF8=1` 會注入本 session 所有子行程，
    使 session 內每一次驗證都跑在 UTF-8 mode；使用者裸開 Windows PowerShell 5.1
    （ACP=950）直接跑腳本時沒有這個變數。上方 1~3 條 in-process mock 測的是
    `reconfigure_stdio_utf8()` 的呼叫契約，**不涉及真實 locale**，因此
    「有人把某支 CLI 的 `import _stdio_utf8` 刪掉」這類退化在 session 內恆綠。
    本類以「拔掉 PYTHONUTF8/PYTHONIOENCODING + `-X utf8=0`」重跑子行程補上該路徑。

    涵蓋面（三段式，實測依據見各 case）：
      - **已實測涵蓋**：stdout/stderr 被導向（pipe／檔案）時，legacy locale 下印
        ✅/❌/⚠️ 的崩潰與否；有無 `import _stdio_utf8` 的紅綠對照；真 CLI
        （`check_defect_log_crossref.py`）production 路徑。
      - **已實測不涵蓋**：附著在**真實 console handle** 上的情境。PEP 528 起 Windows
        console 的 `sys.stdout.encoding` 恆為 utf-8（與碼頁無關），故 console 下本來
        就不會 UnicodeEncodeError；而 unittest 載具永遠拿不到真 console handle，
        無法在此驗。真正會炸的是**導向**情境（nightly 把輸出寫檔、CI 擷取、`>` 重導）
        ——那正是本類覆蓋的面。
      - **未窮舉**：`open()`／`read_text()` 漏 `encoding=` 這類「檔案讀寫端」的 locale
        依賴不在本類職責內（`locale.getpreferredencoding()` 在 console 下同樣是
        cp950，故該類缺陷 console／導向兩情境都會發作）；那需要各腳本自己的
        legacy locale case，本類只鎖 stdio 輸出端。
    """

    @classmethod
    def _legacy_preferred_encoding(cls) -> str:
        proc = _run_legacy(
            ["-c", "import locale; print(locale.getpreferredencoding(False))"]
        )
        if proc.returncode != 0:
            raise AssertionError(
                f"legacy locale 探針自身失敗（rc={proc.returncode}）："
                f"{proc.stderr.decode('utf-8', 'replace')}"
            )
        return proc.stdout.decode("ascii", "replace").strip()

    def _require_discriminating_platform(self) -> str:
        """回傳 legacy 預設編碼；若本平台 legacy 亦為 UTF-8（Linux/macOS 常態）
        則 skip——**明說沒守到**，不假裝綠燈有意義（Rule 12 fail loud）。"""
        legacy = self._legacy_preferred_encoding()
        if legacy.lower().replace("-", "").replace("_", "") in {"utf8", "cp65001"}:
            self.skipTest(
                f"本平台 legacy locale 預設編碼已是 UTF-8（{legacy}），"
                "不存在 cp950 型情境可鑑別；此鎖只在 non-UTF-8 locale 平台生效"
            )
        return legacy

    def test_legacy_env_really_differs_from_session_default(self) -> None:
        """載具自證①：拔掉 PYTHONUTF8 後預設編碼真的變了。

        若這條都不成立，底下所有 legacy locale 斷言都只是在重跑 UTF-8 mode
        （＝DEF-101-506 同型的「綠得沒有鑑別力」）。
        """
        legacy = self._require_discriminating_platform()
        in_session = locale.getpreferredencoding(False)
        self.assertNotEqual(
            legacy.lower(), in_session.lower(),
            "session 內外預設編碼相同 → 本類的 legacy locale 載具無鑑別力",
        )

    def test_unguarded_print_crashes_under_legacy_locale(self) -> None:
        """載具自證②（紅對照）：**沒有** `import _stdio_utf8` 的腳本在 legacy locale
        下印 ✅ 必須 UnicodeEncodeError 崩潰。這是整組鎖的鑑別力來源——若此案不紅，
        下方「有保護就不崩」的綠燈毫無意義。"""
        legacy = self._require_discriminating_platform()
        proc = _run_legacy(["-c", _PROBE_UNGUARDED])
        stderr = proc.stderr.decode("utf-8", "replace")
        self.assertNotEqual(
            proc.returncode, 0,
            f"無保護腳本在 {legacy} 下竟未崩潰 → 本平台無此缺陷面，鎖失去鑑別力",
        )
        self.assertIn("UnicodeEncodeError", stderr, stderr)

    def test_stdio_utf8_import_survives_legacy_locale(self) -> None:
        """綠對照：只多一行 `import _stdio_utf8`，同一段 print 就必須成功，
        且吐出的位元組是**合法 UTF-8**（不是 cp950 亂碼）。"""
        self._require_discriminating_platform()
        proc = _run_legacy(["-c", _PROBE_GUARDED])
        self.assertEqual(
            proc.returncode, 0,
            f"stderr={proc.stderr.decode('utf-8', 'replace')}",
        )
        # strict 解碼：亂碼（cp950 位元組）會在此拋 UnicodeDecodeError 而非靜默通過
        self.assertEqual(proc.stdout.decode("utf-8").strip(), _PROBE_EXPECTED)

    def test_stdio_utf8_also_guards_stderr_under_legacy_locale(self) -> None:
        """stderr 同樣受保護——本 repo 的 ❌/⚠️ 訊息大多走 stderr，只鎖 stdout 等於
        漏掉實際最常用的輸出通道。"""
        self._require_discriminating_platform()
        proc = _run_legacy(["-c", _PROBE_GUARDED_STDERR])
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        self.assertEqual(proc.stderr.decode("utf-8").strip(), _PROBE_EXPECTED)

    def test_real_cli_tool_survives_legacy_locale(self) -> None:
        """production 路徑鎖：真的 CLI（`check_defect_log_crossref.py`）在 legacy
        locale + 輸出被導向的情境下必須 rc=0、輸出為合法 UTF-8。

        移掉該檔的 `import _stdio_utf8` 這行，本案即紅（in-process mock 測不到）。
        額外斷言「輸出真的含 legacy 碼頁編不出來的字元」：若哪天有人把 ✅ 全換成
        ASCII，這條鎖會失去鑑別力而恆綠——寧可當下 fail loud 提醒改載具。
        """
        legacy = self._require_discriminating_platform()
        self.assertIn(
            "import _stdio_utf8", _CARRIER.read_text(encoding="utf-8"),
            f"{_CARRIER.name} 已非 _stdio_utf8 消費者 → 請改挑其他載具，勿留無效鎖",
        )
        proc = _run_legacy([str(_CARRIER)])
        stderr = proc.stderr.decode("utf-8", "replace")
        self.assertNotIn("UnicodeEncodeError", stderr, stderr)
        self.assertEqual(proc.returncode, 0, f"stderr={stderr}")
        out = proc.stdout.decode("utf-8")  # strict：亂碼會在此爆
        undecodable = sorted({
            ch for ch in out if not _encodable(ch, legacy)
        })
        self.assertTrue(
            undecodable,
            f"{_CARRIER.name} 的輸出已無 {legacy} 編不出來的字元 → 本鎖失去鑑別力，"
            "請改挑仍會輸出 ✅/❌/⚠️ 的載具",
        )


def _encodable(ch: str, encoding: str) -> bool:
    try:
        ch.encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return False
    return True


if __name__ == "__main__":
    unittest.main()
