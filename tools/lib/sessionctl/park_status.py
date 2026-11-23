"""`park --status` 的三列憑證（QuotaWall DES §10；REQ-QW-37；R218 Q3）。

主載具（`keepwarm` 的 holder 記錄）、備援（park 排程憑證）、哨兵各一列，缺席照實印 `absent`：宣稱
「會自動繼續」的人必須能一眼看出三道網各有幾道在。`sessionctl status` 的同款兩列由 Q4 接線時直接
呼叫本檔的 `lines`，不另寫第二份判準。
"""
from __future__ import annotations

import sys

from . import holder, qw_schema


def primary_line(sid: str, *, row=None, live=None) -> str:
    row = holder.read(sid) if row is None else row
    alive = (live or holder.is_live)(row) if row else False
    if not row or not alive:
        return "primary: absent"
    wake = qw_schema.holder_wake(row)
    when = qw_schema.iso(wake.wake_at) if wake and wake.wake_at is not None else "unknown"
    mode = (wake.mode if wake else None) or "unknown"
    return f"primary: live pid={row.get('pid')} wake_at={when} mode={mode}"


def backup_line(marker, *, platform_name: str | None = None) -> str:
    if (platform_name or sys.platform) != "win32":
        return "backup: absent(platform)"
    jobs = [j for j in (marker or {}).get("jobs") or [] if j.get("role") == "primary"]
    if not marker or marker.get("status") != "armed" or not jobs or not jobs[0].get("credential"):
        return "backup: absent"
    return f"backup: next_run={str(jobs[0]['credential']).split('（')[0].strip()}"


def sentinel_line(sid: str, S: dict | None = None) -> str:
    S = S or {}
    try:
        import schedule_backend  # noqa: PLC0415
        import sentinel_lifecycle  # noqa: PLC0415

        task = f"{sentinel_lifecycle.TASK_PREFIX}{sid}"
        jobs = (S.get("jobs") or (S.get("backend") or schedule_backend.select()).list_jobs)(task)
    except Exception:  # noqa: BLE001 — 狀態列是唯讀診斷，量不到照實說
        return "sentinel: unknown"
    if jobs is None:
        return "sentinel: unknown"
    return "sentinel: armed" if task in jobs else "sentinel: absent"


def lines(sid: str, marker, S: dict | None = None, *,
          platform_name: str | None = None) -> list[str]:
    S = S or {}
    return [primary_line(sid, row=S.get("holder_row"), live=S.get("holder_live")),
            backup_line(marker, platform_name=platform_name), sentinel_line(sid, S)]
