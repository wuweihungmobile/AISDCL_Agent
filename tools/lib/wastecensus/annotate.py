"""逐字稿回合的衍生量：加權單位、上下文、TTL 型別、快取重寫標記、喚醒鏈（純函式，零 token）。"""
from __future__ import annotations

from collections import Counter

from .reader import W_CC1, W_CC5, W_CR, W_IN, W_OUT, Turn


def units(turn: dict) -> float:
    cc1, cc5 = turn["cc1"], turn["cc5"]
    rest = max(0, turn["cc"] - cc1 - cc5)
    return (
        turn["inp"] * W_IN
        + turn["out"] * W_OUT
        + turn["cr"] * W_CR
        + cc1 * W_CC1
        + cc5 * W_CC5
        + rest * W_CC5
    )


def ctx(turn: dict) -> int:
    return turn["inp"] + turn["cc"] + turn["cr"]


def tier(turn: dict) -> str | None:
    if turn["cc5"] and not turn["cc1"]:
        return "5m"
    if turn["cc1"] and not turn["cc5"]:
        return "1h"
    if turn["cc1"] and turn["cc5"]:
        return "mixed"
    return None


def annotate(turns: list[Turn]) -> None:
    """為每個回合填 gap／prev_ctx／prefix_hit／rewrite 標記（同一執行緒內）。"""
    default_tier = Counter(tier(t) for t in turns if tier(t)).most_common(1)
    thread_tier = default_tier[0][0] if default_tier else None
    prev = None
    for turn in turns:
        turn["tier"] = tier(turn) or thread_tier
        if prev is None:
            turn.update(gap=None, prev_ctx=0, prefix_hit=None, rewrite=False, rewrite_tokens=0)
        else:
            gap = (
                (turn["ts_first"] - prev["ts_last"])
                if turn["ts_first"] and prev["ts_last"]
                else None
            )
            pctx = ctx(prev)
            hit = min(1.0, turn["cr"] / pctx) if pctx >= 20_000 else None
            incr = max(0, ctx(turn) - pctx)
            lost = max(0, turn["cc"] - incr)
            rewrite = bool(
                pctx >= 30_000 and hit is not None and hit < 0.5 and turn["cause"] != "compaction"
            )
            turn.update(
                gap=gap,
                prev_ctx=pctx,
                prefix_hit=hit,
                rewrite=rewrite,
                rewrite_tokens=lost if rewrite else 0,
                prev_tools=list(prev["tools"]),
                prev_stop=prev["stop"],
            )
        prev = turn


def chains(turns: list[Turn]) -> list[dict]:
    """喚醒鏈＝從一個「非 tool_result 起因」的回合開始，連同其後的 tool_result 回合。"""
    out: list[dict] = []
    cur = None
    for turn in turns:
        if cur is None or turn["cause"] != "tool_result":
            cur = {
                "sid": turn["sid"],
                "thread": turn["thread"],
                "cause": turn["cause"],
                "ts": turn["ts_first"],
                "ctx_start": ctx(turn),
                "gap": turn.get("gap"),
                "turns": 0,
                "units": 0.0,
                "out": 0,
                "tokens": 0,
                "rewrite": bool(turn.get("rewrite")),
                "rewrite_tokens": turn.get("rewrite_tokens", 0),
                "bg_before": turn["bg_before"],
                "first_units": units(turn),
            }
            out.append(cur)
        cur["turns"] += 1
        cur["units"] += units(turn)
        cur["out"] += turn["out"]
        cur["tokens"] += turn["inp"] + turn["cc"] + turn["cr"] + turn["out"]
    return out
