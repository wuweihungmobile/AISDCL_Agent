"""
桌面通知工具（Windows Toast / macOS 通知中心）。
優先使用 plyer；不可用時依平台 fallback：darwin 走 osascript、win32 走 win10toast；
再不行就只寫 log（最後手段）。

註：plyer 的 darwin 後端需要 pyobjus（notifications extra 未宣告，刻意不加重依賴），
故 macOS 實務上由 osascript 分支承接 ESCALATION 桌面通知。
"""
from __future__ import annotations

import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autoclaude.utils.config import AppConfig

logger = logging.getLogger("autoclaude.utils.notifier")


def notify_escalation(title: str, message: str, dump_path: str, cfg: AppConfig) -> None:
    """
    ESCALATION 級別的強化通知。

    無論 notification.enabled 是否開啟，永遠寫入 escalation_alert.log。
    若設定了 webhook_url，目前僅記錄警告 — webhook HTTP 發送尚待實作，
    詳見 docs/05_development/Phase6_P1_Backlog.md「其他技術 TODO」段落。
    """
    notify(title, message, enabled=cfg.notification.enabled)

    # 永遠寫入 escalation_alert.log（無論通知是否啟用）
    alert_log = Path(cfg.checkpoint_dir) / "escalation_alert.log"
    try:
        alert_log.parent.mkdir(parents=True, exist_ok=True)
        with alert_log.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} | {title} | {message} | dump={dump_path}\n")
        logger.info("ESCALATION 已記錄至 %s", alert_log)
    except Exception as exc:
        logger.warning("escalation_alert.log 寫入失敗: %s", exc)

    # Webhook 通知（webhook_url 設定後待實作 HTTP POST 發送，目前僅記錄警告）
    if cfg.notification.webhook_url:
        logger.warning(
            "Webhook 通知尚未實作，跳過 webhook_url=%s", cfg.notification.webhook_url
        )


def notify(title: str, message: str, duration: int = 10, enabled: bool = True) -> None:
    """
    在桌面右下角彈出通知泡泡。失敗時靜默降級為 log。

    enabled=False 時，僅寫入 log 而不嘗試呼叫平台通知 API
    （對應 config.notification.enabled=False）。
    """
    if not enabled:
        logger.debug("[NOTIFY-disabled] %s | %s", title, message)
        return
    if _try_plyer(title, message, duration):
        return
    if sys.platform == "darwin" and _try_osascript(title, message):
        return
    if _try_win10toast(title, message, duration):
        return
    logger.info("[NOTIFY] %s | %s", title, message)


class Notifier:
    """
    通知器物件包裝，由 PlaybookRunner 在初始化時注入。
    可從 AppConfig 統一讀取 enabled 狀態，避免每個呼叫端各自判斷。
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def __call__(self, title: str, message: str, duration: int = 10) -> None:
        notify(title, message, duration=duration, enabled=self.enabled)


def _try_plyer(title: str, message: str, duration: int) -> bool:
    try:
        from plyer import notification  # type: ignore
        notification.notify(
            title=title,
            message=message,
            timeout=duration,
            app_name="AutoClaude",
        )
        return True
    except Exception as exc:
        logger.debug("plyer 通知失敗: %s", exc)
        return False


#: osascript 參數化腳本 — title/message 走 argv 傳入（獨立 process 參數），
#: 不做字串插值，杜絕單引號跳脫 / AppleScript 注入問題。
_OSASCRIPT_NOTIFY = (
    "on run argv\n"
    "  display notification (item 1 of argv) with title (item 2 of argv)\n"
    "end run"
)


def _try_osascript(title: str, message: str) -> bool:
    """macOS 通知中心 fallback（darwin 專用；display notification 不支援 duration）。"""
    try:
        subprocess.run(
            ["osascript", "-e", _OSASCRIPT_NOTIFY, message, title],
            check=True,
            capture_output=True,
            timeout=10,
        )
        return True
    except Exception as exc:
        logger.debug("osascript 通知失敗: %s", exc)
        return False


def _try_win10toast(title: str, message: str, duration: int) -> bool:
    try:
        from win10toast import ToastNotifier  # type: ignore
        toaster = ToastNotifier()
        toaster.show_toast(title, message, duration=duration, threaded=True)
        return True
    except Exception as exc:
        logger.debug("win10toast 通知失敗: %s", exc)
        return False
