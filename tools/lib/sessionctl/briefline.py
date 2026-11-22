"""SessionStart 簡報的 sessionctl 附註行（DES §6.3、§21；REQ-CTL-14）：本 repo 範圍內上一個 session
留下的未收尾（殘局）背景代理、被額度切斷的代理。

WHY 拆出本檔：`tools/lib/session_brief.py` 397／400 行（DES §21），邏輯一律放這裡、主檔只呼叫。
只回字串（有內容時以空白開頭，直接串在簡報尾端；沒有 ⇒ `""`），唯讀、零子行程、任何例外 ⇒ `""`
（簡報失敗不得反過來擋 SessionStart）。沙盒專案由名冊預設範圍（`rosterscope`）排除，所以不公告。
被切種類（`kind`）由 W4 的 `rosterscope.cut_kind` 提供；名冊列沒有 `kind` 時 M 恆為 0（不猜）。
對 A8（`claude -r` 後在飛代理能否接回，未驗證）只出聲、不假設。
"""
from __future__ import annotations

import os
import time
from collections.abc import Callable, Mapping
from datetime import datetime

from . import roster

ORPHAN_MAX_AGE_SECONDS = roster.RESIDUE_MAX_AGE_SECONDS  # 同名冊：滿壽命的殘局不再公告


def _snapshot(env: Mapping) -> list[dict]:
    return roster.snapshot(None, env=env, full=False)["agents"]


def _fresh(row: dict, at: float) -> bool:
    try:
        age = at - datetime.fromisoformat(row["last_at"]).timestamp()
    except (KeyError, TypeError, ValueError):
        return True  # 量不到時間：寧可公告
    return age <= ORPHAN_MAX_AGE_SECONDS


def orphan_line(sid: str | None, env: Mapping | None = None, *,
                agents_fn: Callable[[Mapping], list[dict]] | None = None,
                now: float | None = None) -> str:
    """殘局／被切公告一行。殘局＝本 repo 範圍內、**別的擁有者**的代理、非 running、最後記錄在
    壽命內。`agents_fn` 是測試注入縫（缺省＝名冊預設範圍快照，不列舉行程）。"""
    try:
        env = os.environ if env is None else env
        at = time.time() if now is None else now
        rows = (agents_fn or _snapshot)(env)
        orphans = [r for r in rows if r.get("state") != "running" and r.get("owner_sid") != sid
                   and not r.get("sandbox") and _fresh(r, at)]
        if not orphans:
            return ""
        cut = sum(1 for r in orphans if r.get("kind") == "usage_limit")
        text = (f"sessionctl：本 repo 上一個 session 有 {len(orphans)} 支背景代理未收尾（殘局，"
                "記錄停在那裡，不是還在燒額度）")
        if cut:
            text += f"，其中 {cut} 支被額度切斷"
        return (f" {text}；看清單：python tools/sessionctl.py status（交接包第 12 欄有細節）。"
                "新 session 不假設 claude -r 能接回在飛代理，要重做請派新代理＋短任務書。")
    except Exception:  # noqa: BLE001 — 見檔頭 fail-open 紀律
        return ""


def join(lines: list[str]) -> str:
    """多段附註串接（W6 的 park 探針行也走這裡，不再碰 `session_brief.py`）。"""
    return "".join(line for line in lines if line)


def lines(sid: str | None, env: Mapping | None = None) -> str:
    return join([orphan_line(sid, env)])
