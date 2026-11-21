"""叫醒量測 M-WB1／M-WB2（DES WorkProgress_Axis_Design §6.4／REQ-WP-33；量測探針，不接閘門 rc）。

WHY：R217 起因 ARC E3——sid 31ea79d4 在 14.5 小時內被監督／保溫叫醒 21 次，其中 8 次是
harness 已送過「Agent finished」通知後 7～30 秒內 watch 又退出一次（純重複），每次叫醒主控又回
約 3 個回合、冷讀 40 萬～99 萬 cache_read。DES §6.1 以「watch 不再因 all_done 退出」機械消除
重複，本模組負責在真逐字稿上**重量**它：
  M-WB1：每次監督／保溫叫醒之後，主控 assistant 回合數（**資訊欄**，觀察目標 ≤1；取決於 LLM 行為，
         不作任何閘門或結案條件）。
  M-WB2：子代理完成通知之後 60 秒內，又有監督／保溫類通知的件數（目標 0；由 §6.1 機械保證）。
判準全是純函式，輸入是 `load_events` 讀出的事件序列；`run` 才讀檔。
叫醒＝背景指令通知（非「Agent … finished」）且摘要含監督／保溫字樣；字樣單一家＝`WAKE_RE`。
"""
from __future__ import annotations

import json
import re
import statistics
import time
from datetime import datetime
from pathlib import Path

DUP_WINDOW_S = 60.0  # M-WB2：子代理完成通知後這麼久內的叫醒算重複
AGENT_DONE_RE = re.compile(r'^Agent\s+".*"\s+(finished|completed)', re.S)
WAKE_RE = re.compile(
    r"supervise|re-arm|keepwarm|keep-warm|sessionctl[^\"]*(watch|keepwarm)|保溫|監督", re.I)
_TID_RE = re.compile(r"<task-id>(.*?)</task-id>")
_SUMMARY_RE = re.compile(r"<summary>(.*?)</summary>", re.S)


def _epoch(raw) -> float | None:
    try:
        return datetime.fromisoformat(str(raw).strip().replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def parse_events(lines: list[str]) -> list[dict]:
    """逐行 jsonl → 事件序列（保持檔內順序）：`enq`（通知入佇列）、`user`（帶 origin 的使用者
    ／機器提示，即一個回合的起點）、`asst`（assistant 回合，同 message id 只算一次）。壞行略過。"""
    out, seen_mid = [], set()
    for idx, line in enumerate(lines):
        if '"queue-operation"' not in line and '"user"' not in line and '"assistant"' not in line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if not isinstance(rec, dict):
            continue
        ts, kind = _epoch(rec.get("timestamp")), rec.get("type")
        content = rec.get("content") if kind == "queue-operation" else None
        if kind == "queue-operation" and rec.get("operation") == "enqueue" \
                and isinstance(content, str) and "<task-notification>" in content:
            tid, summ = _TID_RE.search(content), _SUMMARY_RE.search(content)
            if tid and ts is not None:
                out.append({"e": "enq", "i": idx, "ts": ts, "tid": tid.group(1),
                            "summary": summ.group(1) if summ else ""})
        elif kind == "user" and isinstance(rec.get("origin"), dict) and not rec.get("isMeta"):
            msg = rec.get("message")
            text = msg.get("content") if isinstance(msg, dict) else ""
            tid = _TID_RE.search(text) if isinstance(text, str) else None
            out.append({"e": "user", "i": idx, "ts": ts, "origin": rec["origin"].get("kind"),
                        "tid": tid.group(1) if tid else None})
        elif kind == "assistant" and isinstance(rec.get("message"), dict):
            msg = rec["message"]
            if msg.get("model") == "<synthetic>":
                continue
            mid = msg.get("id") or f"line{idx}"
            if mid not in seen_mid:
                seen_mid.add(mid)
                out.append({"e": "asst", "i": idx, "ts": ts})
    return out


def is_wake(summary: str) -> bool:
    return not AGENT_DONE_RE.match(summary or "") and bool(WAKE_RE.search(summary or ""))


def m_wb2(events: list[dict]) -> dict:
    """子代理完成通知（同 task-id 只算一次）之後 ≤60 秒內入佇列的叫醒通知件數。"""
    notes = sorted({e["tid"]: e for e in events if e["e"] == "enq"}.values(), key=lambda e: e["ts"])
    dones = [e["ts"] for e in notes if AGENT_DONE_RE.match(e["summary"])]
    hits = []
    for e in notes:
        if not is_wake(e["summary"]):
            continue
        prior = [d for d in dones if 0.0 <= e["ts"] - d <= DUP_WINDOW_S]
        if prior:
            hits.append({"tid": e["tid"], "gap_s": round(e["ts"] - max(prior), 1)})
    return {"count": len(hits), "agent_done": len(dones), "hits": hits}


def m_wb1(events: list[dict]) -> dict:
    """每次叫醒送達（機器提示 origin 帶該 task-id）到下一個帶 origin 的提示之間的 assistant 回合數。
    沒有送達記錄的叫醒計入 `undelivered`，不猜。"""
    wakes = {e["tid"] for e in events if e["e"] == "enq" and is_wake(e["summary"])}
    prompts = [e for e in events if e["e"] == "user"]
    turns, undelivered = [], len(wakes)
    for pos, cur in enumerate(prompts):
        if cur["tid"] not in wakes:
            continue
        undelivered -= 1
        stop = prompts[pos + 1]["i"] if pos + 1 < len(prompts) else float("inf")
        turns.append(sum(1 for e in events if e["e"] == "asst" and cur["i"] < e["i"] < stop))
    return {"wakes": len(wakes), "measured": len(turns), "undelivered": max(0, undelivered),
            "turns": turns, "mean": round(statistics.mean(turns), 2) if turns else None,
            "median": statistics.median(turns) if turns else None,
            "ge2": sum(1 for t in turns if t >= 2)}


def load_events(base: Path, since_days: float, sid: str | None) -> list[list[dict]]:
    """專案逐字稿主檔（不含子代理）→ 每檔一份事件序列；只留 `since_days` 內有事件的檔。"""
    floor, out = time.time() - since_days * 86400, []
    for path in sorted(base.glob("*.jsonl")):
        if sid and not path.stem.startswith(sid):
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        events = [e for e in parse_events(lines) if e["ts"] is None or e["ts"] >= floor]
        if events:
            out.append(events)
    return out


def run(base: Path, since_days: float, sid: str | None, out: str | None) -> int:
    per_file = load_events(base, since_days, sid)
    wb1 = [m_wb1(ev) for ev in per_file]
    wb2 = [m_wb2(ev) for ev in per_file]
    turns = [t for w in wb1 for t in w["turns"]]
    got = {"files": len(per_file), "m_wb2": sum(w["count"] for w in wb2),
           "agent_done": sum(w["agent_done"] for w in wb2),
           "m_wb1": {"wakes": sum(w["wakes"] for w in wb1),
                     "measured": len(turns), "undelivered": sum(w["undelivered"] for w in wb1),
                     "mean": round(statistics.mean(turns), 2) if turns else None,
                     "median": statistics.median(turns) if turns else None,
                     "ge2": sum(w["ge2"] for w in wb1)}}
    print(f"== 叫醒量測 M-WB1／M-WB2（近 {since_days:g} 天；逐字稿 {got['files']} 支）==")
    a = got["m_wb1"]
    print(f"   M-WB1 叫醒後主控回合數（資訊欄，觀察目標 ≤1）：叫醒 {a['wakes']} 次、"
          f"已量 {a['measured']}、未送達 {a['undelivered']}；平均 {a['mean']} 中位 {a['median']}；"
          f"≥2 回合 {a['ge2']} 次")
    print(f"   M-WB2 子代理完成通知後 {DUP_WINDOW_S:g} 秒內的重複叫醒（目標 0）：{got['m_wb2']} 件"
          f"（子代理完成通知 {got['agent_done']} 則）")
    if out:
        Path(out).write_text(json.dumps({"kind": "wake_metrics", **got}, ensure_ascii=False) + "\n",
                             encoding="utf-8", newline="\n")
    return 0
