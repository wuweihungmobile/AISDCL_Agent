"""R68 回歸鎖：perception 層的兩筆平台誠實性/韌性缺陷。

[A] HotkeyHandler.register()（macOS，真機取證）
    keyboard.add_hotkey() 把 listen() 丟進背景 daemon thread 後立即返回；macOS
    非 root 時 `_darwinkeyboard.listen()` 首行 `os.geteuid() != 0` 即 raise
    OSError 13（**與 TCC「輔助使用」授權無關**，授權了也一樣失敗；是 10/10
    確定性失敗，不是 race）。修復前 register() 在該執行緒已死的情況下仍印
    「已註冊」並把 _registered 設 True ＝ 靜默失效。

[B] _build_cmd_shim_line 長度守門（Windows，靜態分析）
    .cmd/.bat shim 路徑把整個 prompt 組進單一 `cmd /d /s /c "…"` 字串，撞
    cmd.exe 8191 字元硬上限；POSIX 側走 argv（本機 ARG_MAX 實測 1048576）無此
    界線。修復前全樹零長度守門，超限只會拿到難以歸因的
    "The input line is too long."。⚠️ 本輪無 Windows 真機，8191 為文件層知識，
    未取得機器證據——本鎖驗的是「守門存在且會 fail-loud」，不是 cmd.exe 行為。
"""
from __future__ import annotations

import os
import sys
import threading
from unittest.mock import MagicMock, patch

import pytest

from autoclaude.perception import hotkey_handler
from autoclaude.perception.hotkey_handler import HotkeyHandler
from autoclaude.perception.pty_wrapper import _CMD_LINE_MAX_CHARS, _build_cmd_shim_line

# ──────────────────────────────────────────────
# [A] Hotkey：背景執行緒已死 → 不得宣稱已註冊
# ──────────────────────────────────────────────

class TestHotkeyRegisterHonesty:
    def setup_method(self):
        self._original_hook = threading.excepthook
        hotkey_handler._excepthook_installed = False

    def teardown_method(self):
        threading.excepthook = self._original_hook
        hotkey_handler._excepthook_installed = False

    def test_dead_listener_thread_must_not_report_registered(self, caplog):
        fake_keyboard = MagicMock()
        dead_thread = threading.Thread(target=lambda: None)
        dead_thread.start()
        dead_thread.join()
        assert dead_thread.is_alive() is False
        fake_keyboard._listener.listening_thread = dead_thread
        with patch.object(hotkey_handler, "_KEYBOARD_AVAILABLE", True), \
             patch.object(hotkey_handler, "keyboard", fake_keyboard, create=True), \
             caplog.at_level("INFO", logger="autoclaude.perception"):
            handler = HotkeyHandler()
            handler.register()
        assert handler._registered is False, (
            "背景監聽執行緒已死卻回報已註冊 ＝ 靜默失效（R68 缺陷復發）"
        )
        messages = [r.getMessage() for r in caplog.records]
        assert not any("已註冊" in m for m in messages), f"不得宣稱已註冊：{messages}"
        assert any("不可用" in m for m in messages), f"必須誠實自報不可用：{messages}"

    def test_live_listener_thread_still_registers(self):
        """有牙的鎖不能把正常路徑一起打死：執行緒存活時仍須註冊成功。"""
        fake_keyboard = MagicMock()
        stop = threading.Event()
        live = threading.Thread(target=stop.wait, daemon=True)
        live.start()
        fake_keyboard._listener.listening_thread = live
        try:
            with patch.object(hotkey_handler, "_KEYBOARD_AVAILABLE", True), \
                 patch.object(hotkey_handler, "keyboard", fake_keyboard, create=True):
                handler = HotkeyHandler()
                handler.register()
            assert handler._registered is True
        finally:
            stop.set()
            live.join(timeout=2)


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS 真機專屬（非 Darwin 上 skip 而非恆綠）")
@pytest.mark.skipif(
    not hotkey_handler._KEYBOARD_AVAILABLE, reason="keyboard 套件未安裝"
)
@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0, reason="root 下 keyboard 可正常監聽"
)
def test_macos_non_root_register_reports_unavailable_for_real():
    """非 mock 常駐測試：macOS 非 root 時 register() 必須自報不可用。

    keyboard 0.13.5 `_darwinkeyboard.listen()` 首行即 `os.geteuid() != 0` →
    OSError 13，故此處為確定性行為，非 flaky。
    """
    original_hook = threading.excepthook
    hotkey_handler._excepthook_installed = False
    try:
        handler = HotkeyHandler()
        handler.register()
        assert handler._registered is False, (
            "macOS 非 root 下 keyboard 監聽執行緒必定死亡，register() 不得宣稱成功"
        )
    finally:
        threading.excepthook = original_hook
        hotkey_handler._excepthook_installed = False


# ──────────────────────────────────────────────
# [B] cmd.exe 8191 字元守門
# ──────────────────────────────────────────────

class TestCmdShimLineLengthGuard:
    def test_oversized_prompt_fails_loud_before_hitting_cmd_limit(self):
        prompt = "x" * (_CMD_LINE_MAX_CHARS + 100)
        with pytest.raises(RuntimeError) as exc:
            _build_cmd_shim_line(r"C:\npm\claude.cmd", ["-p", prompt])
        msg = str(exc.value)
        assert "8191" in msg and str(_CMD_LINE_MAX_CHARS) in msg, msg
        assert "stdin" in msg or "檔案" in msg, f"錯誤訊息必須指路可行解法：{msg}"

    def test_guard_threshold_is_below_the_hard_limit(self):
        assert 0 < _CMD_LINE_MAX_CHARS < 8191, (
            "守門閾值必須嚴格低於 cmd.exe 8191 硬上限，才能在超限前攔下"
        )

    def test_line_at_threshold_still_builds(self):
        """邊界內不得誤擋（否則守門本身變成新的缺陷）。

        🔴 overhead 以**非空** prompt 量：空字串參數在組行時不佔它自己的位置
        （實測差 2 字元），拿它當基準會讓「剛好等於閾值」的斷言恆差 2——那是量法
        的 off-by-N，不是守門的行為。改以 1 字元 prompt 取基準再回推，基準與目標
        用同一條路徑組出來，量法本身就不會引入偏差。
        """
        base = len(_build_cmd_shim_line(r"C:\npm\claude.cmd", ["-p", "x"]))
        prompt = "x" * (_CMD_LINE_MAX_CHARS - base + 1)
        line = _build_cmd_shim_line(r"C:\npm\claude.cmd", ["-p", prompt])
        assert len(line) == _CMD_LINE_MAX_CHARS
        assert line.startswith('cmd /d /s /c "') and line.endswith('"')
