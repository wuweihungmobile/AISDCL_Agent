"""浪費帳指標（純函式；輸入皆為 reader 產出的 list[dict]，不讀家目錄、不打外部）。

指標編號沿用 SA 浪費帳（TCS-TokenWaste-20261114 §1 FR-TW-09）：
- M1  主控閒置超過一小時、上下文 >= 25 萬後整份重寫（快取壽命邊界的浪費）；
- M2b 子代理被「其他人」續棒（cause=other_user）且上下文 >= 續棒門檻的重寫（G1 的分子）；
- M2c 子代理在 tool_result／通知喚醒、一小時內的重寫，按代理型別分組（G3 的分子）；
- M2d long-runner 型別代理中「全程無長等待」者占比（G3 選錯型別的溢價監看）；
- M3a 子代理被額度牆切斷後續跑的件數與重寫量；M3d 機制自身的阻斷／逃生使用量；
- M4  push 呼叫的成敗與失敗牆鐘；M5 hook 自身成本（延遲／注入字元）。
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from .annotate import annotate, ctx
from .reader import iso

#: M1 的判準：閒置超過一小時（1h 快取壽命）且上下文達此值才算「大額重寫」
M1_GAP_S = 3600
M1_MIN_PREV_CTX = 250_000
#: M2c 的「一小時內」上界與 5 分鐘 TTL 線（gap 小於 TTL 卻重寫＝成因不在 TTL，G3 消不掉）
M2C_MAX_GAP_S = 3600
TTL_5M_S = 300
M2C_CAUSES = ("tool_result", "task_notification")
AXIS_MAIN, AXIS_SUB = "主控", "子代理"
LONG_RUNNER = "long-runner"


def fmt_pct(a: float, b: float) -> str:
    return f"{(100.0 * a / b):.1f}%" if b else "n/a"


def median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def rewrite_rows(axis: str, turns: list[dict]) -> list[dict]:
    """一條軸（主控／子代理）上被標為重寫的回合 ⇒ jsonl 的 `rewrite` 列。"""
    return [
        {
            "kind": "rewrite",
            "axis": axis,
            "sid": x["sid"],
            "thread": x["thread"],
            "ts": iso(x["ts_first"]),
            "model": x["model"],
            "tier": x["tier"],
            "gap_s": x["gap"],
            "ctx": ctx(x),
            "prev_ctx": x["prev_ctx"],
            "cc": x["cc"],
            "cr": x["cr"],
            "rewrite_tokens": x["rewrite_tokens"],
            "cause": x["cause"],
            "bg_pending_before": x["bg_before"],
        }
        for x in turns
        if x["rewrite"]
    ]


def rewrites(data: dict, since: float | None = None) -> list[dict]:
    """`reader.collect` 的結果 ⇒ 兩條軸的重寫列（主控在前、子代理在後；`since`＝epoch 下限）。"""
    out: list[dict] = []
    for axis, key in ((AXIS_MAIN, "main"), (AXIS_SUB, "sub")):
        turns: list[dict] = []
        for _sid, _path, thread in data[key]:
            annotate(thread["turns"])
            turns += [
                x
                for x in thread["turns"]
                if since is None or (x["ts_first"] is not None and x["ts_first"] >= since)
            ]
        out += rewrite_rows(axis, turns)
    return out


def agent_types(data: dict) -> dict[str, str]:
    """{thread: agentType}（取自 agent-*.meta.json；缺＝unknown）。"""
    out: dict[str, str] = {}
    for _sid, path, thread in data["sub"]:
        meta = thread.get("meta") or {}
        kind = meta.get("agentType") if isinstance(meta, dict) else None
        out[path.stem] = kind if isinstance(kind, str) and kind else "unknown"
    return out


def turns_by_agent(data: dict) -> dict[str, list[dict]]:
    """{thread: 已標註的回合列}（供 m2d 看回合間隔）。"""
    out: dict[str, list[dict]] = {}
    for _sid, path, thread in data["sub"]:
        annotate(thread["turns"])
        out[path.stem] = thread["turns"]
    return out


def m1(rows: list[dict]) -> dict:
    hit = [
        r
        for r in rows
        if r.get("axis") == AXIS_MAIN
        and (r.get("gap_s") or 0) > M1_GAP_S
        and (r.get("prev_ctx") or 0) >= M1_MIN_PREV_CTX
    ]
    return {"count": len(hit), "tokens": sum(r["rewrite_tokens"] for r in hit)}


def m2b(rows: list[dict], limit: int) -> dict:
    """G1 的分子：子代理 ∧ 他人續棒 ∧ 上下文 >= `limit`（呼叫端傳續棒門檻，不在此寫死）。"""
    hit = [
        r
        for r in rows
        if r.get("axis") == AXIS_SUB
        and r.get("cause") == "other_user"
        and (r.get("prev_ctx") or 0) >= limit
    ]
    le60 = [r for r in hit if r.get("gap_s") is not None and r["gap_s"] <= M2C_MAX_GAP_S]
    return {
        "count": len(hit),
        "le60min": len(le60),
        "tokens": sum(r["rewrite_tokens"] for r in hit),
    }


def m2c(rows: list[dict], types: dict[str, str]) -> dict:
    """G3 的分子：tool_result／通知喚醒、一小時內的子代理重寫，按代理型別分組。

    `gap_lt_ttl`＝其中間隔小於 5 分鐘 TTL 者（成因不在快取過期，1 小時 TTL 消不掉，
    列出來免得高估 G3 的效益）。
    """
    hit = [
        r
        for r in rows
        if r.get("axis") == AXIS_SUB
        and r.get("cause") in M2C_CAUSES
        and r.get("gap_s") is not None
        and r["gap_s"] <= M2C_MAX_GAP_S
    ]
    by_type: dict[str, int] = {}
    for r in hit:
        kind = types.get(r.get("thread"), "unknown")
        by_type[kind] = by_type.get(kind, 0) + 1
    return {
        "count": len(hit),
        "by_type": by_type,
        "gap_lt_ttl": sum(1 for r in hit if r["gap_s"] < TTL_5M_S),
    }


def m2d(by_agent: dict[str, list[dict]], types: dict[str, str], wait_gap_s: float = 360) -> dict:
    """long-runner 代理中「全程無 > wait_gap_s 回合間隔」者占比（無此型別 ⇒ share 為 None）。"""
    agents = [t for t in by_agent if types.get(t) == LONG_RUNNER]
    if not agents:
        return {"agents": 0, "zero_wait_share": None}
    zero = sum(1 for t in agents if not any((x.get("gap") or 0) > wait_gap_s for x in by_agent[t]))
    return {"agents": len(agents), "zero_wait_share": zero / len(agents)}


def m3a(rows: list[dict]) -> dict:
    cuts = [r for r in rows if r.get("kind") == "subagent_cut"]
    return {
        "count": len(cuts),
        "resume_rewrite_tokens": sum(r.get("resume_rewrite_tokens") or 0 for r in cuts),
    }


def m3d(trace_path: str | Path) -> dict:
    """機制自身效果與逃生口使用量；缺檔／壞行＝0，不拋。"""
    counts = {"resume_gate_block": 0, "resume_gate_override": 0, "converge_block": 0}
    try:
        text = Path(trace_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    for line in text.splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        event = rec.get("event") if isinstance(rec, dict) else None
        if event in counts:
            counts[event] += 1
    return {
        "blocked": counts["resume_gate_block"],
        "overridden": counts["resume_gate_override"],
        "converge_blocked": counts["converge_block"],
    }


def m4(rows: list[dict]) -> dict:
    pushes = [r for r in rows if r.get("kind") == "push"]
    fails = [r for r in pushes if r.get("outcome") == "fail"]
    return {
        "calls": len(pushes),
        "fail": len(fails),
        "fail_wall_s": sum(r.get("wall_s") or 0 for r in fails),
    }


def m5(rows: list[dict]) -> dict:
    cost = next((r for r in rows if r.get("kind") == "mech_cost"), {})
    return {k: cost.get(k) for k in ("hook_calls", "hook_ms_median", "ctx_msgs", "ctx_chars")}
