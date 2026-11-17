"""`--supervision-metrics` 的 I/O 層：主逐字稿、交接包、痕跡 → supervision.py 的輕量記錄並印表。

判準單一家：起因 kind 取 `transcript_activity._origin_kind`（同一份 origin 判斷，不自創第二套）。
零 token、只讀檔；壞行略過。
"""
from __future__ import annotations

import json
import re
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import transcript_activity as ta

from . import supervision as sv

_HOOK_KEEP = 800  # Stop 出聲內容只留前這麼多字（判準只看開頭字樣）


def _epoch(raw) -> float | None:
    if not isinstance(raw, str):
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _blocks(rec: dict) -> list[dict]:
    msg = rec.get("message")
    content = msg.get("content") if isinstance(msg, dict) else None
    return [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []


def light(rec: dict) -> dict | None:
    """一筆原始記錄縮成判準要用的欄位；無時戳回 None。"""
    t, typ = _epoch(rec.get("timestamp")), rec.get("type")
    if t is None:
        return None
    out = {"t": t, "type": typ, "sub": rec.get("subtype"), "ok": ta._origin_kind(rec),
           "meta": bool(rec.get("isMeta"))}
    msg = rec.get("message") if isinstance(rec.get("message"), dict) else {}
    if typ == "assistant":
        use = msg.get("usage") if isinstance(msg.get("usage"), dict) else None
        out["model"] = msg.get("model")
        out["use"] = ({k: v for k, v in use.items() if type(v) is int} if use else None)
        out["tools"] = [b.get("name") for b in _blocks(rec) if b.get("type") == "tool_use"]
    elif typ == "user":
        text = ta._text_of(rec)
        out["tool_result"] = text is None
        out["text"] = (text or "")[:3000]
        out["textlen"] = len(text or "")
    elif typ == "attachment":
        att = rec.get("attachment") if isinstance(rec.get("attachment"), dict) else {}
        if att.get("type") == "hook_system_message":
            out["hook_event"] = att.get("hookEvent")
            out["content"] = str(att.get("content") or "")[:_HOOK_KEEP]
    elif typ == "system" and rec.get("subtype") == "turn_duration":
        out["pending"] = rec.get("pendingBackgroundAgentCount")
    return out


def load_sessions(base: Path, since_days: float) -> list[dict]:
    floor, out = time.time() - since_days * 86400, []
    for path in sorted(base.glob("*.jsonl")):
        try:
            if path.stat().st_mtime < floor:
                continue
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        recs, eps = [], Counter()
        for line in lines:
            try:
                raw = json.loads(line)
            except ValueError:
                continue
            if not isinstance(raw, dict):
                continue
            if raw.get("entrypoint"):
                eps[raw["entrypoint"]] += 1
            if (r := light(raw)) is not None:
                recs.append(r)
        interactive = bool(eps) and eps.get("cli", 0) >= max(eps.values())
        out.append({"sid": path.stem, "recs": recs, "interactive": interactive})
    return out


def load_packs(handoff_dir: Path) -> list[dict]:
    """交接包 → `{sid, built_at, finalized, todo}`；finalized＝有「主控層」且無 `TODO:`（唯讀近似，
    不呼叫 handoff.finalize，避免量測探針依賴會變動的寫入面）。"""
    packs = []
    for path in sorted(handoff_dir.glob("*_????????T??????Z.md")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        head = text.splitlines()[0] if text else ""
        sid, at = re.search(r"sid=(\S+)", head), re.search(r"at=(\S+)", head)
        todo = text.count("TODO:")
        packs.append({"sid": sid.group(1) if sid else path.stem.rsplit("_", 1)[0],
                      "built_at": _epoch(at.group(1)) if at else None,
                      "finalized": "主控層" in text and todo == 0, "todo": todo})
    return packs


def load_trace(trace_file: Path) -> list[dict]:
    rows = []
    try:
        lines = trace_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return rows
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            row["_at"] = _epoch(row.get("at"))
            rows.append(row)
    return rows


def run(base: Path, since_days: float, trace_file: Path, handoff_dir: Path, out: str | None,
        r1: int = sv.R1_DEFAULT) -> int:
    got = sv.compute(load_sessions(base, since_days), load_packs(handoff_dir),
                     load_trace(trace_file), r1=r1)
    w1, w2, f1 = got["m_w1"], got["m_w2"], got["m_f1"]
    s1, s2, s3 = got["m_s1"], got["m_s2"], got["m_s3"]
    print(f"== 監督與換手量測（近 {since_days:g} 天；R1={r1:,}）==")
    print(f"   M-W1 無看管區間：{w1['n']} 筆（hook 出聲 {w1['n_hook_voiced']}）合計 "
          f"{w1['total_hours']} 小時；中位 {w1['gap_min'].get('p50')} 分、P90 "
          f"{w1['gap_min'].get('p90')}、最大 {w1['gap_min'].get('max')}；>60 分 {w1['gt_60min']}；"
          f"沒回來 {w1['never_returned']}（憑證判準待 WP-4 接上＝目前恆無憑證）")
    print(f"   M-W2 背景叫醒冷重寫：{w2['n']} 次／{w2['tokens']:,} tok")
    w3, w4, f2 = got["m_w3"], got["m_w4"], got["m_f2"]
    print(f"   M-W3 監督推回：{w3['supervise_stop_block']} 件／派工波 {w3['dispatch_waves']}"
          f"{'（' + w3['note'] + '）' if w3['note'] else ''}")
    print(f"   M-W4 watch 判決：{w4['watch_verdicts']} 件（{w4['note']}）")
    print(f"   M-F1 冷真人重寫：{f1['n']} 次／{f1['tokens']:,} tok")
    print(f"   M-F2 轉送：spawned {f2[sv.EV_FORWARD_SPAWNED]}／failed {f2[sv.EV_FORWARD_FAILED]}"
          f"／pass {f2[sv.EV_FORWARD_PASS]}{'（' + f2['note'] + '）' if f2['note'] else ''}")
    print(f"   M-F3 舊視窗再打字：spawn {got['m_f3']['spawned']} 次、其後真人提示 "
          f"{got['m_f3']['human_prompts_after_spawn']} 件")
    print(f"   M-S1 無封存回合結束：{s1['without_finalized_pack']}／{s1['turn_ends_ge_r1']}"
          f"（封存閘推回 {s1['seal_stop_block']}）")
    print(f"   M-S2 手貼接續：{s2['pasted']}／{s2['n_interactive']} 互動 session；{s2['by_class']}")
    print(f"   M-S3 包過時（分）：n={s3['n_packs']} {s3['lag_min']}")
    if out:
        Path(out).write_text(json.dumps({"kind": "supervision_metrics", **got}, ensure_ascii=False,
                                        default=str) + "\n", encoding="utf-8", newline="\n")
    return 0
