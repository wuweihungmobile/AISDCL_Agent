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
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from .platform_caps import is_macos, is_windows

# 🔴 R82（ACC-01）：彈窗預設停留秒數由 10 降到 3。
# WHY：plyer 的 Windows 後端把 balloon_tip 丟進一個**非 daemon** 執行緒並 `time.sleep(timeout)`，
# 非 daemon 執行緒會拖住 process exit ⇒ 這個數字就是「跑完之後行程還要多活多久」。
# 獨立實測（未觸發任何彈窗）：主程式印完 `main_done daemon= False` 後，外層碼錶仍量到
# wall_ms=3038（sleep 3s 的非 daemon 執行緒）——行程確實等滿。
# 這裡刻意**不**把 plyer 的呼叫包進自己的 daemon thread：plyer 內部那個非 daemon 執行緒還在，
# 外層 daemon 化解決不了，只會多一層假象。真正有效的兩件事是「預設不彈」＋「縮短 timeout」。
# `duration=0` 未採用：balloontip.py 的 `if timeout:` 會跳過 sleep，但物件隨即可能被 GC 而
# `__del__` 立刻移除氣泡＝使用者根本看不到——該行為未實測，不照抄。
DEFAULT_DURATION_SECONDS = 3

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


def notify(
    title: str, message: str,
    duration: int = DEFAULT_DURATION_SECONDS, enabled: bool = True,
) -> None:
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
    if is_macos() and _try_osascript(title, message):
        return
    # R82（ACC-01）：補平台守門。win10toast 是 Windows 專屬（內部拉 win32 API），
    # 此前對非 Windows 也會呼叫、只靠 import 失敗兜底——那是「靠例外當控制流」。
    if is_windows() and _try_win10toast(title, message, duration):
        return
    logger.info("[NOTIFY] %s | %s", title, message)


# 🔴 R82（ACQ-03 的等量減法之一）：此處原有一個 `Notifier` 類別，docstring 寫「由
# PlaybookRunner 在初始化時注入」——實查全庫**零建構點、零 import**（`Notifier(` 只命中
# 測試裡的 `_SpyNotifier` 與 win10toast 的 `ToastNotifier`，是同名子字串不是它）。
# 它是死碼；`notify()` 這個模組級函式才是所有呼叫端真正在用的入口。刪除以讓出 LOC 預算。
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
