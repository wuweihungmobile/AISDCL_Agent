"""
全域 ESC+F12 中斷處理器。
使用 keyboard 函式庫，在任何視窗前台下監聽熱鍵。
觸發後設定 threading.Event，主迴圈檢查後乾淨退出。
"""
from __future__ import annotations
import logging
import threading

logger = logging.getLogger("autoclaude.perception")

try:
    import keyboard  # type: ignore
    _KEYBOARD_AVAILABLE = True
except ImportError:
    _KEYBOARD_AVAILABLE = False
    logger.warning("keyboard 未安裝，ESC+F12 全域中斷將無法使用")


class HotkeyHandler:
    HOTKEY = "esc+f12"

    def __init__(self):
        self._stop_event = threading.Event()
        self._registered = False

    def register(self) -> None:
        if not _KEYBOARD_AVAILABLE:
            return
        keyboard.add_hotkey(self.HOTKEY, self._on_trigger, suppress=True)
        self._registered = True
        logger.info("全域中斷熱鍵已註冊：%s", self.HOTKEY)

    def _on_trigger(self) -> None:
        logger.warning("偵測到 %s，正在觸發緊急中斷...", self.HOTKEY)
        self._stop_event.set()

    @property
    def stop_event(self) -> threading.Event:
        return self._stop_event

    @property
    def triggered(self) -> bool:
        return self._stop_event.is_set()

    def unregister(self) -> None:
        if _KEYBOARD_AVAILABLE and self._registered:
            try:
                keyboard.remove_hotkey(self.HOTKEY)
            except Exception:
                pass
