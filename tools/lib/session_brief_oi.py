"""SessionStart 簡報的兩段附註（R217 A5）：OIR 掌舵者目視清單、舊窗關閉出聲。

從 `session_brief.py` 抽出（根層護欄層 LOC 分級：該檔逼近上限）。與主檔同紀律：唯讀、零子行程、
任何例外＝不印，簡報失敗不得反過來擋 SessionStart。兩個來源各住自己的套件（openitems／sessionctl），
本檔只是組合點，兩套件彼此不互 import。
"""
from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path


def _tools_on_path() -> None:
    tools = str(Path(__file__).resolve().parent.parent)
    if tools not in sys.path:
        sys.path.insert(0, tools)


def openitems_line() -> str:
    """掌舵者目視清單（DES §5.3）：`listed`＋`escalated` 前 `human_cap` 項＋「另 k 項」。"""
    try:
        _tools_on_path()
        from lib.openitems import gate  # noqa: PLC0415 — 呼叫當下才付 import 成本
        lines = gate.human_lines(gate.load_state())
    except Exception:  # noqa: BLE001 — fail-open
        return ""
    return f" 掌舵者目視清單（OIR）：{'；'.join(lines)}。" if lines else ""


def oldwin_line(sid: str | None) -> str:
    """舊窗關閉出聲（DES §7.1）：本 session 未讀 notice（讀過即標已讀）＋「只提醒」的舊窗 pid。"""
    try:
        _tools_on_path()
        from lib.sessionctl import oldwin  # noqa: PLC0415
        parts = ([oldwin.take_unread_notice(sid)] if sid else []) + oldwin.reminder_lines()
    except Exception:  # noqa: BLE001 — fail-open
        return ""
    text = " ".join(" ".join(p.split()) for p in parts if p)
    return f" {text}" if text else ""


def extra(sid: str | None, openitems: Callable[[], str] | None = None,
          oldwin: Callable[[str | None], str] | None = None) -> str:
    """兩段附註串接（注入縫給測試；缺席＝真取數）。"""
    return (openitems or openitems_line)() + (oldwin or oldwin_line)(sid)
