"""`park_cli.spawn_resume` 開窗後的驗證與記帳（QuotaWall DES §7.4、S-20；R218 Q3）。

`spawn_resume` 是 `sandbox_scope.SITES` 的 spawn 站點（runner 呼叫與 L1 都留在那裡）；runner
之後「怎樣才算
成功、成功後記什麼」搬到這裡：
· 普通 `claude -r <sid>`（無活窗）：成功憑證＝行程存活且原逐字稿變大（或專案目錄出現新檔）——既有
  `grew()` 不變；成功後 `seal.mark_resumed`（同 session 自續跑不算交棒）。
· fork（`--fork-session`，同 sid 有活著的互動舊窗）：成功憑證**只認** spawn 之後出現的、stem ≠ 原
sid 的新
  逐字稿 ∧ 行程仍活；原逐字稿變大**不算**（fork 的前提就是舊窗還活著、會自己寫原逐字稿，否則舊窗一寫
  就是假成功，兩個視窗都沒起來＝零駕駛）。成功寫 `session_switch_spawned`（`ok=True`、`new_sid`、
  `route=fork`）、**不**呼叫 `mark_resumed`（fork 是交棒）。
"""
from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

from . import handoff, switch


def finish(sid: str, pkg, pid: int, *, fork: bool, proj: Path, tpath: Path, size0: int,
           before: set, started: datetime, alive=None, sleep=None,
           wait_seconds: float = handoff.SPAWN_WAIT_SECONDS) -> int:
    """runner 起了行程之後：等憑證、落痕跡、回 rc。"""
    sleep, alive = sleep or time.sleep, alive or handoff._alive

    def fresh() -> list[str]:
        names = handoff._new_files(proj, before)
        return [n for n in names if Path(n).stem != sid] if fork else names

    def grew() -> bool:
        if fork:
            return bool(fresh())
        return (tpath.is_file() and tpath.stat().st_size > size0) or bool(fresh())

    deadline = time.monotonic() + wait_seconds
    ok = grew()
    while not ok and time.monotonic() < deadline and alive(pid):
        sleep(1)
        ok = grew()
    up = alive(pid)
    switch.trace("session_resume_spawned", sid=sid, pid=pid, handoff=str(pkg), ok=ok and up,
                 fork=fork)
    if not (ok and up):
        what = "新逐字稿未出現" if fork else "逐字稿未增長"
        print(f"❌ 已起行程 pid={pid} 但{what if up else '行程已不在'}"
              f"（{wait_seconds:g}s 內）⇒ 不報成功；請自行檢視新視窗。", file=sys.stderr)
        return 1
    if fork:
        stem = Path(fresh()[0]).stem
        switch.trace("session_switch_spawned", at=started.isoformat(), pid=pid, sid=sid,
                     handoff=str(pkg), spawned_at=started.isoformat(), ok=True, new_sid=stem,
                     route="fork")
        print(f"✅ 已 fork 出新 session（pid={pid}，新 sid {stem[:8]}；舊視窗保留）。")
        return 0
    from . import seal  # noqa: PLC0415

    seal.mark_resumed(pkg)  # 同 sid 自續跑不算交棒：作廢封存（失敗不影響續跑結果，見 mark_resumed）
    print(f"✅ 已續跑原 session（pid={pid}，claude -r {sid[:8]}）。")
    return 0
