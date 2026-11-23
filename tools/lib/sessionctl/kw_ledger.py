"""保溫帳（`trace_dir()/keepwarm/<sid>.json`）：`pings`／`n*`、真人提示與「主控真工作」兩個歸零標記、
ping 實測 Δ（R218 Q2；DES §5.2、S-24、S-25；REQ-QW-65／66）。

自 `keepwarm.py` 抽出（LOC 分級；`keepwarm` 重新匯出本檔公開名，既有呼叫端與測試不變）。
歸零（S-24）＝真人提示（`human_mark`）∨ 主控真工作記錄（`work_mark`）∨ 視窗翻新（`clear`）；
任一歸零一併清空 `last_ping_*`（區間內有真工作／真人提示／換窗者不得算 Δ）。`ping_costs` 是量測
史料，歸零不清。欄名（`last_ping_pct`／`last_ping_at`／`ping_costs`）只 import `qw_schema`。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import endurance_env
import quota_limits
import transcript_activity

from . import control, midwork, qw_schema

#: /2（W11c③）：`ping_costs` 每筆 `{pp, clean}`；/1 檔的樣本一律不乾淨（讀回 `[]`），
#: `pings`／`last_ping_*` 照舊保留（升版只汰除污染樣本，不吞既有保溫進度）。
SCHEMA = "autosdd.keepwarm/2"
#: 非跨包欄名（只有保溫帳自己讀寫）：真工作標記、上一次 ping 時的 reset（同窗判準用）。
_WORK, _LAST_RESET = "work", "last_ping_reset"


def _warn(msg: str) -> None:
    print(f"⚠️ {msg}", file=sys.stderr)


def ledger_path(sid: str, *, write: bool = False) -> Path:
    root = endurance_env.trace_dir() if write else endurance_env.trace_dir_peek()[0]
    return root / "keepwarm" / f"{sid}.json"


def human_mark(transcript) -> str:
    """最後一則**可轉送真人提示**的標記（`時戳|行號`）；`<task-notification>` 等機器注入不算。"""
    last = ""
    for p in transcript_activity.all_human_prompts(Path(transcript)):
        if transcript_activity.is_forwardable_prompt(p["text"]):
            last = f"{p['at']}|{p['line']}"
    return last


def _is_work(record: dict) -> bool:
    """主控這筆記錄算「真工作」：主鏈 assistant 含至少一個非唯讀、非監督的 `tool_use`
    （監督文法單一家＝`control.is_supervision_call`，不另寫指令正則）；或 auto-continuation 開啟
    的新回合。判不出的指令算真工作（偏歸零＝偏少花：多歸零只會讓 periodic 的 cap 晚一點到）。"""
    if record.get("type") == "user":
        return transcript_activity._origin_kind(record) == quota_limits.RESUME_ORIGIN
    msg = record.get("message")
    blocks = msg.get("content") if isinstance(msg, dict) else None
    return (record.get("type") == "assistant" and not record.get("isSidechain")
            and isinstance(blocks, list)
            and any(isinstance(b, dict) and b.get("type") == "tool_use"
                    and b.get("name") not in midwork.READONLY_TOOLS
                    and not control.is_supervision_call(b) for b in blocks))


def work_mark(transcript) -> str:
    """最後一筆「真工作」記錄的標記（`時戳|行號`）；沒有／讀不到 ⇒ `""`。全檔掃描（只解析含
    `tool_use`／`origin` 字面的行），只在帳上已有 ping 或要寫帳時才呼叫。"""
    last = ""
    try:
        with Path(transcript).open(encoding="utf-8", errors="replace") as handle:
            for number, line in enumerate(handle, 1):
                if '"tool_use"' not in line and '"origin"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if isinstance(rec, dict) and _is_work(rec):
                    last = f"{rec.get('timestamp') or ''}|{number}"
    except OSError:
        return ""
    return last


def read_ledger(sid: str) -> dict:
    """`{pings, human, work, last, last_n, last_reset, costs}`；缺檔＝零；壞檔／結構不符＝零並出聲。
    `costs`＝乾淨樣本 pp；非 /2 檔一律 `[]`。"""
    path, empty = ledger_path(sid), {"pings": 0, "human": "", "work": "", "last": None,
                                     "last_n": None, "last_reset": None, "costs": []}
    try:
        row = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(row, dict) and type(row.get("pings")) is int and row["pings"] >= 0:
            reset = row.get(_LAST_RESET)
            return {"pings": row["pings"], "human": str(row.get("human") or ""),
                    "work": str(row.get(_WORK) or ""), "last": qw_schema.last_ping(row),
                    "last_n": qw_schema.last_ping_n(row),
                    "last_reset": reset if type(reset) in (int, float) else None,
                    "costs": qw_schema.ping_costs(row) if row.get("schema") == SCHEMA else []}
        _warn(f"保溫帳 {path} 結構不符 ⇒ 當作零")
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as exc:
        _warn(f"保溫帳 {path} 讀不動（{type(exc).__name__}）⇒ 當作零")
    return empty


def load_ledger(sid: str, transcript) -> dict:
    """讀帳並套用歸零：帳上已有 ping 且（最後真人提示標記變了 ∨ 真工作標記變了）⇒ pings 歸零、
    `last_ping_*` 清空。"""
    row = read_ledger(sid)
    if row["pings"] > 0 and (human_mark(transcript) != row["human"]
                             or work_mark(transcript) != row["work"]):
        row.update(pings=0, last=None, last_n=None, last_reset=None)
    return row


def record_ping(sid: str, pings: int, ctx: int, star: int, mark: str, *, work: str = "",
                last=None, costs=(), last_reset=None) -> bool:
    """寫帳（pings 為新值）；`last`＝`(pct, at_epoch[, n_live])｜None`（None＝清空）；`costs`＝乾淨
    樣本 pp；寫不進去回 `False`（呼叫端判 cap）。"""
    path = ledger_path(sid, write=True)
    pct, at, n_live = (tuple(last) + (None,))[:3] if last else (None, None, None)
    row = {"schema": SCHEMA, "sid": sid, "pings": pings, "n_star": star, "ctx": ctx, "human": mark,
           _WORK: work, **qw_schema.ledger_extra(pct, at, costs, n_live),
           _LAST_RESET: last_reset if last else None}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(row, ensure_ascii=False), encoding="utf-8", newline="\n")
    except OSError as exc:
        _warn(f"保溫帳寫不進 {path}（{type(exc).__name__}）⇒ 判 cap（不保溫，退回沒有保溫的現況）")
        return False
    return True


def clear(sid: str, transcript, ctx: int = 0, star: int = 0) -> bool:
    """視窗翻新（`resume`／`keepwarm_early_reset`）：pings 歸零、清 `last_ping_*`；`ping_costs`
    留。"""
    row = read_ledger(sid)
    return record_ping(sid, 0, ctx, star, human_mark(transcript), work=work_mark(transcript),
                       costs=row["costs"])
