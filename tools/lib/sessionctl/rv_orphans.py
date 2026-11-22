"""`sessionctl status` 的一行「realverify 孤兒 n=<k>」（RealVerify SE DES §5.6；REQ-SE-36）。

只讀 realverify 排程租約帳（`~/.autosdd/realverify_leases/*.jsonl`）：不匯入 realverify 套件（套件間
單向相依；格式常數 `SCHED_KIND`／`PENDING`／`LEASE_DIR_PARTS` 由測試核對與
`realverify/leases.py` 相等）、
不撤銷、不改任何檔。孤兒＝待撤列（intent／made／unverified）且主人已死，或主人存活但驗不到
建立時間而 `expires_at` 已過——判準與 `leases._is_orphan` 同形。量不到帳（目錄不在）＝ n=0。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import sandbox_scope

LEASE_DIR_PARTS = (".autosdd", "realverify_leases")
SCHED_KIND = "sched_job"
PENDING = ("intent", "made", "unverified")
LABEL = "realverify 孤兒"


def lease_dir() -> Path:
    return Path.home().joinpath(*LEASE_DIR_PARTS)  # 測試以 mock.patch.object 換掉


def _rows(path: Path) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows = []
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue  # 半截／壞列只略過這一列
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _orphan(row: dict, now: datetime) -> bool:
    alive, started = sandbox_scope.proc_probe(row.get("owner_pid"))
    if not alive:
        return True
    recorded = row.get("owner_started")
    try:
        if started and recorded:
            seen, kept = datetime.fromisoformat(started), datetime.fromisoformat(recorded)
            gap = abs((seen - kept).total_seconds())
            return gap > sandbox_scope._OWNER_START_TOLERANCE_SEC  # noqa: SLF001
        expires = row.get("expires_at")
        return bool(expires) and datetime.fromisoformat(expires) <= now
    except ValueError:
        return False


def orphan_count(now: datetime | None = None) -> int:
    now = now or datetime.now().astimezone()
    total = 0
    try:
        files = sorted(lease_dir().glob("*.jsonl"))
    except OSError:
        return 0
    for path in files:
        last: dict[str, dict] = {}
        for row in _rows(path):
            if row.get("kind") == SCHED_KIND:
                last[str(row.get("ident"))] = row
        pending = [r for r in last.values() if r.get("state") in PENDING]
        total += sum(1 for row in pending if _orphan(row, now))
    return total


def status_line(now: datetime | None = None) -> str:
    return f"{LABEL} n={orphan_count(now)}"
