"""halt 標記檔（DEF-200-278／INV-H1c）的落盤與讀回——從 `quota_gate` 抽出的三支函式。"""
# 🔴 為何抽出：`quota_gate.py` 是 hub tier（預算 500，餘裕 0）；配速床接線（ADR-XPLAT-004 §2.15）
# 需要在 gate 內加數行。依「不調高預算、先抽出等量程式」原則，把最獨立的一族（標記檔路徑／寫／讀，
# 只依賴 `endurance_env` 的目錄 SSOT 與 json）搬到這裡；`quota_gate` 以單行 re-export，既有消費端
# （`quota_gate.write_halt_marker` 等，含 sentinel、planner、測試）零改動。
# 🔴 刻意沒有第二份路徑知識：目錄一律 `endurance_env.trace_dir()`（同哨兵痕跡的家）。
from __future__ import annotations

import json
from pathlib import Path

import endurance_env


def halt_marker_path(sid: str) -> Path:
    """DEF-200-278／INV-H1c 落盤處，SSOT＝`endurance_env.trace_dir()`（同哨兵痕跡的家）。"""
    return endurance_env.trace_dir() / f"halt_{sid}.json"


def write_halt_marker(sid: str, data: dict) -> Path:
    """落一份持久 halt 標記，供哨兵下一輪巡邏讀（`halt_verdict()`）。寫檔失敗吞掉——
    標記是輔助憑證而非安全煞車（fail-open 是 P0）。"""
    path = halt_marker_path(sid)
    try:
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8", newline="\n")
    except OSError:
        pass
    return path


def read_halt_marker(sid: str) -> dict | None:
    """讀不出來（沒有 sid／檔不存在／壞 JSON）一律回 `None`，呼叫端據此落回既有判定。"""
    if not sid:
        return None
    try:
        return json.loads(halt_marker_path(sid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
