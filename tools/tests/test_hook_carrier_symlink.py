#!/usr/bin/env python3
"""tools/lib/hook_carrier_symlink.py 的單元測試（DEF-200-316 方案 B）。

全程 `tempfile.TemporaryDirectory()` 合成樹，不碰真 `.venv`（同鄰檔
test_single_venv_identity.py 的既有風格：純函式／純檔案系統操作即可驗紅驗綠，
不需要真正建置的環境）。

執行：python -m unittest tools.tests.test_hook_carrier_symlink -v
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

from _platform_helpers import create_symlink_or_skip

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _symlink():
    """延後 import 唯一真相源（同鄰檔既有慣例）。"""
    sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
    import hook_carrier_symlink  # noqa: PLC0415

    return hook_carrier_symlink


class TestEnsureWindowsIsNoOp(unittest.TestCase):
    def test_windows_never_touches_disk(self) -> None:
        """`is_windows=True` 直接回 `True`，且完全不建立任何路徑——Windows 原生
        已有 `pythonw.exe`，沒有半邊可建（同 `stray_venv.enforce()` no-op 慣例）。"""
        emitted: list[str] = []
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ok = _symlink().ensure(root, True, emitted.append)
        self.assertTrue(ok)
        self.assertEqual(emitted, [])
        self.assertFalse((root / ".venv" / "Scripts" / "pythonw.exe").exists())


def _make_target(root: Path) -> None:
    """在合成樹裡建出連結目標 `.venv/bin/python`（一個普通檔即可，`ensure()`
    只檢查存在性，不檢查是否可執行）。"""
    target = root / ".venv" / "bin" / "python"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("", encoding="utf-8")


class TestEnsurePosixCreation(unittest.TestCase):
    """本類兩支測試都是 (b) 類情境（見 `_platform_helpers.py` docstring 第①類收納
    判準）：驗證的正是 `ensure()` 在磁碟真的建立符號連結的行為，不是可用替身規避
    的邏輯分支。Windows 未開啟開發人員模式時 `os.symlink` 會拋 `WinError 1314`
    （R81 包 F 實查，非缺件），故 `setUp` 先用既有 SSOT `create_symlink_or_skip`
    探一次同一項權限，無權限時比照既有慣例整類 skip，而非誤判成 `ensure()` 邏輯
    有缺陷。"""

    def setUp(self) -> None:
        self._probe_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._probe_dir.cleanup)
        probe_root = Path(self._probe_dir.name)
        probe_target = probe_root / "target"
        probe_target.write_text("", encoding="utf-8")
        create_symlink_or_skip(self, probe_root / "link", probe_target)

    def test_missing_link_is_created(self) -> None:
        """連結不存在、目標存在 ⇒ 建立目錄＋建立連結，`emit` 一行含「已建立」，
        回 `True`；事後 `readlink` 精確等於 `../bin/python`。"""
        emitted: list[str] = []
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_target(root)
            ok = _symlink().ensure(root, False, emitted.append)
            link = root / ".venv" / "Scripts" / "pythonw.exe"
            self.assertTrue(ok)
            self.assertEqual(len(emitted), 1, emitted)
            self.assertIn("已建立", emitted[0])
            self.assertTrue(link.is_symlink())
            self.assertEqual(Path(os.readlink(link)), Path("../bin/python"))

    def test_a_healthy_existing_link_is_silent_and_idempotent(self) -> None:
        """連結已存在且身分正確 ⇒ 靜默回 `True`（不呼叫 `emit`），且不重建
        （冪等：第二次呼叫的結果與第一次呼叫後的磁碟狀態一致）。"""
        symlink = _symlink()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_target(root)
            first: list[str] = []
            symlink.ensure(root, False, first.append)
            second: list[str] = []
            ok = symlink.ensure(root, False, second.append)
        self.assertTrue(ok)
        self.assertEqual(second, [], "已健康的連結不該再次 emit")


class TestEnsureFailLoud(unittest.TestCase):
    def test_a_symlink_to_the_wrong_target_is_not_overwritten(self) -> None:
        """符號連結存在但指到別處（使用者手動改過）⇒ **不覆寫**，`emit` 訊息含
        「不覆寫」，回 `False`；且事後 `readlink` 仍是使用者設的那個錯誤目標——
        驗證「不覆寫」不是空話。

        這是測試 fixture 自己要在磁碟建一顆「使用者手動建錯」的既有符號連結
        （(a) 類：不是驗證 `ensure()` 的建立行為），Windows 無 symlink 權限時
        比照既有慣例（`_platform_helpers.create_symlink_or_skip`）skip，而非
        算失敗。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            link = root / ".venv" / "Scripts" / "pythonw.exe"
            link.parent.mkdir(parents=True)
            create_symlink_or_skip(self, link, "/usr/bin/python3")
            emitted: list[str] = []
            ok = _symlink().ensure(root, False, emitted.append)
            self.assertFalse(ok)
            self.assertEqual(len(emitted), 1, emitted)
            self.assertIn("不覆寫", emitted[0])
            self.assertEqual(os.readlink(link), "/usr/bin/python3")  # posix-abs-ok: 任意字面

    def test_a_non_symlink_regular_file_is_not_overwritten(self) -> None:
        """該路徑存在但**不是**符號連結（舊版殘留的普通檔案）⇒ 不覆寫、`emit`
        錯誤、回 `False`；檔案內容保持不變。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            link = root / ".venv" / "Scripts" / "pythonw.exe"
            link.parent.mkdir(parents=True)
            link.write_text("not a symlink", encoding="utf-8")
            emitted: list[str] = []
            ok = _symlink().ensure(root, False, emitted.append)
            self.assertFalse(ok)
            self.assertEqual(len(emitted), 1, emitted)
            self.assertIn("不是符號連結", emitted[0])
            self.assertEqual(link.read_text(encoding="utf-8"), "not a symlink")

    def test_a_missing_target_is_not_linked_to_a_dangling_path(self) -> None:
        """目標 `.venv/bin/python` 不存在（.venv 尚未 bootstrap）⇒ **不建立**
        `Scripts/pythonw.exe`（不建 dangling symlink），`emit` 錯誤訊息含目標
        路徑與「bootstrap」修法，回 `False`。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            emitted: list[str] = []
            ok = _symlink().ensure(root, False, emitted.append)
            link = root / ".venv" / "Scripts" / "pythonw.exe"
            self.assertFalse(ok)
            self.assertEqual(len(emitted), 1, emitted)
            self.assertIn(str(root / ".venv" / "bin" / "python"), emitted[0])
            self.assertIn("bootstrap", emitted[0])
            self.assertFalse(link.exists())
            self.assertFalse(link.is_symlink())


if __name__ == "__main__":
    unittest.main()
