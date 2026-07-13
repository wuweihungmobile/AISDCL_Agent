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

_excepthook_installed = False


def _install_listener_excepthook() -> None:
    """攔截 keyboard 套件背景監聽執行緒的未捕捉例外，轉為乾淨 warning log。

    四方複審 R1 Architect 發現（實測 keyboard==0.13.5 原始碼＋本機重現）：
    `keyboard.add_hotkey()` 經 `GenericListener.start_if_necessary()`
    （keyboard/_generic.py）把 `listen()` 丟進 daemon thread 背景執行、立即返回；
    macOS 缺 Accessibility 授權時的真實失敗（`_darwinkeyboard.listen()` 的
    `os.geteuid()` 檢查）發生在該背景執行緒內，**不會同步傳回** `add_hotkey()`
    呼叫端——包住呼叫本身的 try/except 攔不到。Python 執行緒未捕捉例外預設只會
    印 traceback 到 stderr、不會讓主程序崩潰（故不存在「炸穿主流程」風險），
    但會留下難懂的原始 traceback。改裝 `threading.excepthook`：只在例外確實
    來自 keyboard 監聽執行緒（用 Thread 物件身分比對，非字串/名稱猜測）時
    轉為 warning log；其餘執行緒例外照舊鏈給前一個 hook，不吞掉不相關的錯誤。

    殘留限制（誠實揭露，非完全解決）：`self._registered` 在 `register()` 內
    仍於 `add_hotkey()` 同步返回後就設 True（存在 race：背景執行緒可能稍後
    才失敗），此為 `keyboard` 套件本身非同步啟動設計的固有限制。
    """
    global _excepthook_installed
    if _excepthook_installed:
        return
    _excepthook_installed = True
    previous_hook = threading.excepthook

    def _hook(args) -> None:
        listener = getattr(keyboard, "_listener", None)
        target_thread = getattr(listener, "listening_thread", None)
        if target_thread is not None and args.thread is target_thread:
            logger.warning(
                "全域中斷熱鍵背景監聽執行緒失敗（%s: %s），ESC+F12 中斷將無法使用",
                args.exc_type.__name__ if args.exc_type else "?",
                args.exc_value,
            )
            return
        previous_hook(args)

    threading.excepthook = _hook


class HotkeyHandler:
    HOTKEY = "esc+f12"

    def __init__(self):
        self._stop_event = threading.Event()
        self._registered = False

    def register(self) -> None:
        if not _KEYBOARD_AVAILABLE:
            return
        _install_listener_excepthook()
        try:
            keyboard.add_hotkey(self.HOTKEY, self._on_trigger, suppress=True)
        except Exception:
            # 防護 add_hotkey() 呼叫當下的同步失敗（如熱鍵字串格式錯誤）。
            # macOS 背景執行緒非同步失敗無法在此攔截，改由 _install_listener_excepthook
            # 轉為乾淨 warning log（見其說明）。
            logger.warning("全域中斷熱鍵註冊失敗（%s），ESC+F12 中斷將無法使用", self.HOTKEY)
            return
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
