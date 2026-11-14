"""逐字稿讀取層：串流解析、回合去重、起因歸因、快取重寫標記、喚醒鏈（零 token、只讀逐字稿）。

量到什麼、量不到什麼（誠實劃界）
- 逐字稿的 `usage` 有 input／cache_creation／cache_read／output 與 5m／1h 兩種 TTL 寫入量，
  故「快取重寫」與「壽命邊界」是直接量到的。
- 額度百分比逐字稿裡沒有；凡標「加權單位」者是用公開價格比換算的推估，只拿來排序與估佔比。
- 回合間隔以「前一則訊息最後一筆記錄 → 本則訊息第一筆記錄」計，含本則的首 token 延遲。
"""

from __future__ import annotations

import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path

import quota_limits

SYNTHETIC_MODEL = quota_limits.SYNTHETIC_MODEL


#: 價格比（推估用；見檔頭）
W_IN, W_OUT, W_CR, W_CC5, W_CC1 = 1.0, 5.0, 0.1, 1.25, 2.0
#: hook 出聲換 session 的字樣（context_budget_guard.switch_advice）
VOICE_MARKS = ("續跑成本已高", "建議收斂到可重啟點後換新 session")
CAUSE_PRIO = {
    "compaction": 6,
    "quota_resume": 5,
    "human": 4,
    "peer_handback": 3,
    "task_notification": 2,
    "other_user": 1,
    "tool_result": 0,
}
CTX_BUCKETS = [
    (0, 100_000, "<100k"),
    (100_000, 200_000, "100-200k"),
    (200_000, 300_000, "200-300k"),
    (300_000, 10**12, ">=300k"),
]
GAP_BUCKETS = [
    (0, 60, "<=1m"),
    (60, 300, "1-5m"),
    (300, 600, "5-10m"),
    (600, 1800, "10-30m"),
    (1800, 3300, "30-55m"),
    (3300, 3900, "55-65m"),
    (3900, 5400, "65-90m"),
    (5400, 10**9, ">90m"),
]
_PUSH_RE = re.compile(r"(?<![\w-])git\s+(?:-C\s+\S+\s+)?push\b")


def parse_ts(raw: object) -> float | None:
    if not isinstance(raw, str):
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def iso(epoch: float | None) -> str | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch, tz=UTC).astimezone().isoformat(timespec="seconds")


def parse_iso(raw: str) -> float:
    return datetime.fromisoformat(raw).timestamp()


def bucket(value: float, table) -> str:
    for lo, hi, name in table:
        if lo <= value < hi:
            return name
    return table[-1][2]


def _result_text(block: dict) -> str:
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(str(x.get("text", "")) for x in content if isinstance(x, dict))
    return ""


class Turn(dict):
    """一則 assistant 訊息（以 message.id 去重）。"""


def read_thread(path: Path, sid: str, thread: str) -> dict:
    """串流讀一支逐字稿 ⇒ `{turns, cuts, voices, pushes, notifs}`。"""
    turns: list[Turn] = []
    by_id: dict[str, Turn] = {}
    cuts: list[dict] = []
    voices: list[dict] = []
    tool_calls: dict[str, dict] = {}
    results: dict[str, dict] = {}
    notifs: list[dict] = []
    hook_ms: list[tuple] = []
    hook_ctx_chars: list[int] = []
    pending: set[str] = set()
    pending_bg = 0
    skipped = 0  # 壞 JSON／非物件的行數（真實逐字稿必有壞行，只計數不拋）
    first_ts = None
    try:
        handle = path.open(encoding="utf-8", errors="replace")
    except OSError:
        return {
            "turns": [],
            "cuts": [],
            "voices": [],
            "pushes": [],
            "notifs": [],
            "first_ts": None,
            "skipped": 0,
        }
    with handle:
        for line in handle:
            if '"type":"api-request' in line or '"type":"file-history' in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                skipped += 1
                continue
            if not isinstance(rec, dict):
                skipped += 1
                continue
            kind = rec.get("type")
            ts = parse_ts(rec.get("timestamp"))
            if ts is not None and first_ts is None:
                first_ts = ts
            if kind == "assistant":
                msg = rec.get("message") or {}
                if rec.get("isSidechain") is True and thread == "main":
                    continue
                model = msg.get("model")
                if model == SYNTHETIC_MODEL:
                    body = msg.get("content")
                    text = (
                        body
                        if isinstance(body, str)
                        else " ".join(
                            str(b.get("text", "")) for b in body or [] if isinstance(b, dict)
                        )
                    )
                    cuts.append(
                        {
                            "ts": ts,
                            "error": rec.get("error"),
                            "api_error": bool(rec.get("isApiErrorMessage")),
                            "text": text[:140],
                        }
                    )
                    continue
                mid = msg.get("id") or f"noid-{len(turns)}"
                usage = msg.get("usage") or {}
                cc = usage.get("cache_creation") or {}
                turn = by_id.get(mid)
                if turn is None:
                    cause = "tool_result"
                    if pending:
                        cause = max(pending, key=lambda c: CAUSE_PRIO[c])
                    turn = Turn(
                        sid=sid,
                        thread=thread,
                        id=mid,
                        model=model or "",
                        ts_first=ts,
                        ts_last=ts,
                        inp=0,
                        cc=0,
                        cr=0,
                        out=0,
                        cc5=0,
                        cc1=0,
                        stop=None,
                        tools=[],
                        cause=cause,
                        bg_before=pending_bg,
                        idx=len(turns),
                    )
                    turns.append(turn)
                    by_id[mid] = turn
                    pending = set()
                turn["ts_last"] = ts if ts is not None else turn["ts_last"]
                turn["inp"] = max(turn["inp"], usage.get("input_tokens") or 0)
                turn["cc"] = max(turn["cc"], usage.get("cache_creation_input_tokens") or 0)
                turn["cr"] = max(turn["cr"], usage.get("cache_read_input_tokens") or 0)
                turn["out"] = max(turn["out"], usage.get("output_tokens") or 0)
                turn["cc5"] = max(turn["cc5"], cc.get("ephemeral_5m_input_tokens") or 0)
                turn["cc1"] = max(turn["cc1"], cc.get("ephemeral_1h_input_tokens") or 0)
                turn["stop"] = msg.get("stop_reason") or turn["stop"]
                for block in msg.get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        inp = block.get("input") or {}
                        turn["tools"].append(block.get("name"))
                        tool_calls[block.get("id")] = {
                            "ts": ts,
                            "name": block.get("name"),
                            "sid": sid,
                            "thread": thread,
                            "path": inp.get("file_path") or inp.get("path"),
                            "command": inp.get("command")
                            if isinstance(inp.get("command"), str)
                            else None,
                            "bg": bool(inp.get("run_in_background")),
                        }
            elif kind == "user":
                msg = rec.get("message") or {}
                content = msg.get("content")
                origin = (rec.get("origin") or {}).get("kind")
                blocks = content if isinstance(content, list) else []
                tool_results = [
                    b for b in blocks if isinstance(b, dict) and b.get("type") == "tool_result"
                ]
                if tool_results:
                    for blk in tool_results:
                        results[blk.get("tool_use_id")] = {
                            "ts": ts,
                            "text": _result_text(blk)[:4000],
                        }
                    pending.add("tool_result")
                    continue
                text = (
                    content
                    if isinstance(content, str)
                    else " ".join(str(b.get("text", "")) for b in blocks if isinstance(b, dict))
                )
                if origin == "human":
                    pending.add("human")
                elif origin == "auto-continuation":
                    pending.add("quota_resume")
                elif origin == "peer":
                    pending.add("peer_handback")
                elif origin == "task-notification" or text.startswith("<task-notification>"):
                    pending.add("task_notification")
                elif "This session is being continued" in text[:200]:
                    pending.add("compaction")
                elif origin in ("coordinator",):
                    pending.add("other_user")
                elif not rec.get("isMeta"):
                    pending.add("other_user")
            elif kind == "system":
                sub = rec.get("subtype")
                if sub == "compact_boundary":
                    pending.add("compaction")
                elif sub == "turn_duration":
                    pending_bg = int(rec.get("pendingBackgroundAgentCount") or 0)
            elif kind == "attachment":
                att = rec.get("attachment") or {}
                atype = att.get("type")
                if atype == "hook_success":
                    try:
                        hook_ms.append(
                            (str(att.get("hookName")), float(att.get("durationMs") or 0))
                        )
                    except ValueError:
                        pass
                if atype in ("hook_additional_context", "hook_system_message"):
                    raw = att.get("content")
                    joined = " ".join(raw) if isinstance(raw, list) else str(raw or "")
                    hook_ctx_chars.append(len(joined))
                    if any(mark in joined for mark in VOICE_MARKS):
                        voices.append({"ts": ts, "sid": sid, "text": joined[:160]})
            elif kind == "queue-operation" and rec.get("operation") == "enqueue":
                body = str(rec.get("content") or "")
                if body.startswith("<task-notification>"):
                    tid = re.search(r"<tool-use-id>([^<]+)</tool-use-id>", body)
                    st = re.search(r"<status>([^<]+)</status>", body)
                    notifs.append(
                        {
                            "ts": ts,
                            "tool_use_id": tid.group(1) if tid else None,
                            "status": st.group(1) if st else None,
                        }
                    )
    pushes = []
    notif_by_tool = {n["tool_use_id"]: n for n in notifs if n["tool_use_id"]}
    for tid, call in tool_calls.items():
        cmd = call.get("command")
        if call["name"] not in ("PowerShell", "Bash") or not cmd or not _PUSH_RE.search(cmd):
            continue
        res = results.get(tid) or {}
        end = res.get("ts")
        note = notif_by_tool.get(tid)
        if call["bg"] and note:
            end = note["ts"]
        text = res.get("text", "")
        low = text.lower()
        if (
            "hook declined" in low
            or "failed to push" in low
            or "pre-push" in low
            and "error" in low
        ):
            outcome = "fail"
        elif "->" in text or "everything up-to-date" in low:
            outcome = "ok"
        else:
            outcome = "unknown"
        if call["bg"] and note:
            # 背景工具：前景 tool_result 只是「已啟動」；結果以完成通知的 status 為準
            outcome = {"completed": "ok", "failed": "fail"}.get(note.get("status"), "unknown")
        pushes.append(
            {
                "ts": call["ts"],
                "sid": sid,
                "thread": thread,
                "bg": call["bg"],
                "outcome": outcome,
                "wall_s": (end - call["ts"]) if end and call["ts"] else None,
                "cmd": cmd[:160],
            }
        )
    bg_calls = [
        {
            "ts": c["ts"],
            "name": c["name"],
            "sid": sid,
            "cmd": (c["command"] or "")[:120],
            "notified": tid in notif_by_tool,
        }
        for tid, c in tool_calls.items()
        if c["bg"] and c["name"] in ("PowerShell", "Bash")
    ]
    writes = [
        (c["ts"], c["path"])
        for c in tool_calls.values()
        if c["name"] in ("Write", "Edit", "NotebookEdit") and isinstance(c.get("path"), str)
    ]
    return {
        "turns": turns,
        "cuts": cuts,
        "voices": voices,
        "pushes": pushes,
        "notifs": notifs,
        "first_ts": first_ts,
        "bg_calls": bg_calls,
        "hook_ms": hook_ms,
        "hook_ctx_chars": hook_ctx_chars,
        "writes": writes,
        "skipped": skipped,
    }


def collect(base: Path, since_days: float, only_sid: str | None):
    cutoff = time.time() - since_days * 86400
    mains = []
    for path in sorted(base.glob("*.jsonl")):
        sid = path.stem
        if only_sid and sid != only_sid:
            continue
        if path.stat().st_mtime < cutoff:
            continue
        mains.append((sid, path))
    data = {"main": [], "sub": []}
    for sid, path in mains:
        data["main"].append((sid, path, read_thread(path, sid, "main")))
        subdir = base / sid / "subagents"
        if subdir.is_dir():
            for sub in sorted(subdir.glob("agent-*.jsonl")):
                meta = {}
                meta_path = sub.with_suffix(".meta.json")
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    pass
                thread = sub.stem
                t = read_thread(sub, sid, thread)
                t["meta"] = meta
                data["sub"].append((sid, sub, t))
    return data
