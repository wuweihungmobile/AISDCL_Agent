"""spawn 重複判準（SEC-7；自 `handoff.py` 搬出，行為逐字不變）。"""
# 為何獨立成檔：`handoff.py` 貼著 guardrail_lib 400 行線，S2（副作用隔離）要在 `spawn` 加 L1 判準與
# `--claude`，淨增行數只能靠把「判準與檔案偵測」搬出去換；`handoff` 以同名 re-export 保留既有
# 呼叫座標（`handoff._duplicate_refusals`／`handoff._new_files`／`handoff.SPAWN_DEDUP_SECONDS`）。
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import endurance_env

from . import procstop

#: 同一交接包的 spawn 痕跡在這個窗內視為「剛開過」，拒絕再開（SEC-7）。WHY 10 分鐘：新視窗首個逐字稿
#: 落檔最慢也在數十秒內（`handoff.SPAWN_WAIT_SECONDS`），逾此仍沒人接手＝真的失敗，才准重試；行程若
#: 仍活著則不論多久都拒。
SPAWN_DEDUP_SECONDS = 600


def _duplicate_refusals(path: Path, now: datetime, alive, created_of=None) -> list[str]:
    """SEC-7：已 ack、或同一交接包已有 spawn 痕跡且（pid 仍活著或痕跡在 `SPAWN_DEDUP_SECONDS` 內）
    ⇒ 拒絕再開（驗不到時間也當剛開過）。讀痕跡失敗＝沒有痕跡（不擋）。
    R217 REQ-WP-59：「pid 仍活著」改看身分——現行行程建立時刻晚於痕跡 `at` 超過 30 秒＝pid 被別的行程
    重用，不再誤拒正當的 spawn（`created_of` 是測試縫，缺省走 GetProcessTimes）。"""
    if path.with_suffix(".ack").exists():
        return ["交接包已 ack（已被接手）⇒ 不再開新視窗"]
    out = []
    try:
        lines = (endurance_env.trace_dir() / "autosdd_session_switch.jsonl").read_text(
            encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return out
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if not (isinstance(rec, dict) and rec.get("event") == "session_switch_spawned"
                and rec.get("handoff") == str(path)):
            continue
        at, pid = rec.get("at"), rec.get("pid")
        age = now.timestamp() - (procstop.parse_iso(at) or now.timestamp())  # 驗不到時間＝剛開過
        live = alive(pid) and not procstop.pid_reused(pid, at, created_of)
        if rec.get("ok") is False:  # S-21：失敗列只在行程仍活時才擋；行程已死＝可再試（哨兵接手）
            if live:
                out.append(f"同一交接包已 spawn 過（pid={pid}，at={at}）⇒ 先檢視既有新視窗")
            continue
        if live or age < SPAWN_DEDUP_SECONDS:
            out.append(f"同一交接包已 spawn 過（pid={pid}，at={at}）⇒ 先檢視既有新視窗")
    return out


def _new_files(proj: Path, before: set[str]) -> list[str]:
    if not proj.is_dir():
        return []
    return sorted(p.name for p in proj.glob("*.jsonl") if p.name not in before)
