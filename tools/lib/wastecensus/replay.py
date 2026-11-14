"""收斂硬門檻 H 的取值重放（零 token、只讀主控逐字稿；TCS-TokenWaste-20261114 §7）。

兩個視角合併成一張表（每個候選 H 一列）：
- 工作空間：每個 session 從首次上下文 >= R1 的回合，走到首次 >= H 的回合數（越大越從容）；
- 派工事件：收斂閘擋的是 Agent／Task／Workflow 呼叫，故另數「首次 >= R1 之後、派工當下
  上下文 >= H」的派工次數（會被擋的次數）。
事故 session 在事故時刻的上下文 >= H ⇒ `incident_blocked` 為 True（H 必須擋得到事故）。
"""

from __future__ import annotations

import json
import statistics
import time
from datetime import datetime
from pathlib import Path

EXPAND_TOOLS = frozenset({"Agent", "Task", "Workflow"})
DEFAULT_CANDIDATES = (
    260_000,
    270_000,
    280_000,
    290_000,
    294_000,
    300_000,
    320_000,
    350_000,
    400_000,
)
_CTX_KEYS = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")


def _epoch(raw: object) -> float | None:
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _ctx(usage: dict) -> int:
    return sum(int(usage.get(k) or 0) for k in _CTX_KEYS)


def _records(path: Path):
    """逐行讀逐字稿的 assistant 記錄（壞行略過；非主控鏈 isSidechain 略過）。"""
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"assistant"' not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if (
                isinstance(rec, dict)
                and rec.get("type") == "assistant"
                and not rec.get("isSidechain")
            ):
                yield rec


def main_turns(path: Path) -> list[tuple[float, int]]:
    """[(ts_epoch, ctx)]；同 message.id 取最後一筆，依時間排序。"""
    last: dict[str, tuple[float, int]] = {}
    order: list[str] = []
    for rec in _records(path):
        msg = rec.get("message") or {}
        usage = msg.get("usage")
        ts = _epoch(rec.get("timestamp"))
        if not isinstance(usage, dict) or ts is None:
            continue
        key = str(msg.get("id") or f"{ts}")
        if key not in last:
            order.append(key)
        last[key] = (ts, _ctx(usage))
    return sorted(last[k] for k in order)


def dispatch_events(path: Path) -> tuple[list[tuple[float, int, str]], list[tuple[float, int]]]:
    """依檔案順序回 ([(ts, 派工前上下文, 工具名)], [(ts, ctx)])。"""
    ctx_now = 0
    disp: list[tuple[float, int, str]] = []
    turns: list[tuple[float, int]] = []
    seen: set = set()
    for rec in _records(path):
        msg = rec.get("message") or {}
        ts = _epoch(rec.get("timestamp"))
        if ts is None:
            continue
        for blk in msg.get("content") or []:
            is_call = isinstance(blk, dict) and blk.get("type") == "tool_use"
            if is_call and blk.get("name") in EXPAND_TOOLS and blk.get("id") not in seen:
                seen.add(blk.get("id"))
                disp.append((ts, ctx_now, blk["name"]))
        usage = msg.get("usage")
        if isinstance(usage, dict):
            ctx_now = _ctx(usage)
            turns.append((ts, ctx_now))
    return disp, turns


def replay_hard_ctx(
    base: Path,
    r1: int,
    candidates=DEFAULT_CANDIDATES,
    incident_sid: str | None = None,
    incident_ts: str | None = None,
    since_days: float = 14,
) -> list[dict]:
    """對每個候選 H 回一列 `{H, sessions_reaching_H, room_turns_median, room_turns_p25,
    blocked_dispatches, dispatches_after_r1, incident_blocked}`。"""
    cutoff = time.time() - since_days * 86400
    files = [p for p in sorted(Path(base).glob("*.jsonl")) if p.stat().st_mtime >= cutoff]
    turns_by_sid = {p.stem: main_turns(p) for p in files}
    turns_by_sid = {k: v for k, v in turns_by_sid.items() if v}
    first_r1 = {}
    for sid, tr in turns_by_sid.items():
        idx = next((i for i, (_, c) in enumerate(tr) if c >= r1), None)
        if idx is not None:
            first_r1[sid] = idx
    # 派工視角：每個檔自己的回合序列決定「首次 >= R1」的時刻
    after: dict[str, list[tuple[float, int]]] = {}
    for p in files:
        disp, turns = dispatch_events(p)
        t1 = next((t for t, c in turns if c >= r1), None)
        if t1 is not None:
            after[p.stem] = [(t, c) for (t, c, _name) in disp if t >= t1]
    total_after = sum(len(v) for v in after.values())
    inc_ctx = None
    if incident_sid and incident_ts and incident_sid in turns_by_sid:
        limit_ts = _epoch(incident_ts)
        prior = [c for t, c in turns_by_sid[incident_sid] if limit_ts is not None and t <= limit_ts]
        inc_ctx = prior[-1] if prior else None
    out = []
    for h in candidates:
        rooms = []
        for sid, i1 in first_r1.items():
            tr = turns_by_sid[sid]
            ih = next((i for i, (_, c) in enumerate(tr) if i >= i1 and c >= h), None)
            if ih is not None:
                rooms.append(ih - i1)
        srt = sorted(rooms)
        out.append(
            {
                "H": h,
                "sessions_reaching_r1": len(first_r1),
                "sessions_reaching_H": len(rooms),
                "room_turns_median": statistics.median(rooms) if rooms else None,
                "room_turns_p25": srt[len(srt) // 4] if srt else None,
                "blocked_dispatches": sum(1 for v in after.values() for _t, c in v if c >= h),
                "dispatches_after_r1": total_after,
                "incident_blocked": None if inc_ctx is None else inc_ctx >= h,
            }
        )
    return out
