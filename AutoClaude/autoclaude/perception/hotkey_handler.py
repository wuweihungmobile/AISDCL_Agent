"""
全域 ESC+F12 中斷處理器。
使用 keyboard 函式庫，在任何視窗前台下監聽熱鍵。
觸發後設定 threading.Event，主迴圈檢查後乾淨退出。
"""
from __future__ import annotations

import logging
import threading
import time

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
    macOS 上的真實失敗發生在該背景執行緒內，**不會同步傳回** `add_hotkey()`
    呼叫端——包住呼叫本身的 try/except 攔不到。Python 執行緒未捕捉例外預設只會
    印 traceback 到 stderr、不會讓主程序崩潰（故不存在「炸穿主流程」風險），
    但會留下難懂的原始 traceback。改裝 `threading.excepthook`：只在例外確實
    來自 keyboard 監聽執行緒（用 Thread 物件身分比對，非字串/名稱猜測）時
    轉為 warning log；其餘執行緒例外照舊鏈給前一個 hook，不吞掉不相關的錯誤。
    """
    # R68 真機取證訂正（macOS 26.5.2 / keyboard 0.13.5，非 root、id -u=501）：
    # 上述失敗的判準**不是** TCC「輔助使用」授權，而是 `_darwinkeyboard.listen()`
    # 首行 `if not os.geteuid() == 0: raise OSError("Error 13 - Must be run as
    # administrator")`。授權輔助使用對這條路徑完全無效；非 sudo 執行是 10/10
    # 確定性失敗，不是 race。`register()` 因此改以「背景監聽執行緒是否存活」
    # 為可驗證判準（見 HotkeyHandler._listener_alive），不再無條件宣稱已註冊。
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
        if not self._listener_alive():
            # 誠實性修復（R68）：背景監聽執行緒已死卻回報「已註冊」＝靜默失效。
            logger.warning(
                "全域中斷熱鍵背景監聽執行緒未存活，%s 在本平台不可用"
                "（macOS 的 keyboard 套件要求 euid==0，非 sudo 執行必定失敗；"
                "與『輔助使用』授權無關）",
                self.HOTKEY,
            )
            return
        self._registered = True
        logger.info("全域中斷熱鍵已註冊：%s", self.HOTKEY)

    @staticmethod
    def _listener_alive(grace: float = 0.5) -> bool:
        # add_hotkey() 把 listen() 丟進背景 daemon thread 後立即返回，失敗在那個
        # 執行緒內非同步發生。輪詢 keyboard._listener.listening_thread 的存活狀態
        # 是目前唯一可機械驗證「真的註冊上了嗎」的判準（真機實測：macOS 非 root
        # 時該 thread 於 add_hotkey() 返回後短時間內即 stopped）。觀察到明確死亡
        # 才回 False；grace 內看不到死亡（含測試以 MagicMock 替身）則視為存活。
        deadline = time.monotonic() + grace
        while True:
            listener = getattr(keyboard, "_listener", None)
            thread = getattr(listener, "listening_thread", None)
            if thread is not None and not thread.is_alive():
                return False
            if time.monotonic() >= deadline:
                return True
            time.sleep(0.02)

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
