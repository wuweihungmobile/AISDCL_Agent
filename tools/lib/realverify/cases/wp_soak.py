# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""soak 案例共用 helper（不登記案例）：真排程哨兵的痕跡讀取與保活。案例在 wp_sk1.py／wp_sk2.py。
"""  # noqa: E501

from __future__ import annotations

import glob
import json
import tempfile
from datetime import datetime
from pathlib import Path

from .sentinel import append_limit_event

SENTINEL_INTERVAL_S = 900  # session_resume_planner.SENTINEL_INTERVAL_SECONDS（schedule_backend 以它登記重複間隔）


def real_log_events(sid: str) -> list[dict]:
    """真排程觸發的哨兵行程環境是排程器的（真 TEMP）：稽核痕跡在真暫存目錄，檔名含沙盒 sid。"""
    out = []
    for p in glob.glob(str(Path(tempfile.gettempdir()) / f"autosdd_resume_log_*{sid}*.jsonl")):
        for ln in Path(p).read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                out.append(json.loads(ln))
            except ValueError:
                pass
    return out


def touch_alive(tp: Path) -> None:
    """哨兵以對話記錄時間戳判 session 活著（閒置逾一個額度窗即自我解除）：每小時追加一筆合成 assistant 記錄，
    不花 token。內容無撞線字樣，不會被當撞線事件。"""
    append_limit_event(tp, datetime.now().astimezone(), "RV soak keepalive (no limit)")


