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

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _stdio_utf8 as m  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
