"""`park` 登記時的 QuotaWall 增量（DES §7.1；R218 Q3；自 `park_cli._cmd_park` 搬出以守 LOC 線）。

· `marker_fields`：標記併入的五個欄位（欄名住 `qw_schema`；偏好取自**登記行程**的環境，job
是排程器以
  真環境跑起來的，行程環境帶不過去，所以必須在登記時存進標記）。
· `ensure_sentinel`：嘗試武裝本 sid 的哨兵（既有 `--arm-sentinel` 路；`AUTOSDD_SENTINEL_OFF` 有設
⇒ 不呼叫
  任何排程器，`absent reason=sentinel_off`，X-19）；拒絕時照實回 `absent` 與原因，不假裝。
· `verdict_lines`：貼憑證的兩行（§10：主載具與備援兩份憑證缺一就照實寫「缺席」）。
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from . import qw_schema
from .qw_calc import BACKUP_GRACE_MIN

CLOSE_STUCK_ENV = "AUTOSDD_PARK_CLOSE_STUCK_WINDOW"
ARM_TIMEOUT_SECONDS = 120


def backup_time(primary: datetime) -> datetime:
    """備援排程到點＝主載具預定醒來＋寬限。"""
    return primary + timedelta(minutes=BACKUP_GRACE_MIN)


def marker_fields(primary: datetime, backup: datetime, *, at_mode: bool, env) -> dict:
    """`primary_source`：`--at` ⇒ `at`，其餘（短窗 reset，含 `--why`）⇒ `reset`
    （S-19 據此判是否適用）。"""
    import quota_escalation  # noqa: PLC0415

    return qw_schema.marker_extra(
        primary.timestamp(), "at" if at_mode else "reset", backup.timestamp(),
        env.get(CLOSE_STUCK_ENV) == "1", env.get(quota_escalation.NOTIFY_ENV))


def _run_planner(sid: str, transcript, claude, env) -> int:
    import win_spawn  # noqa: PLC0415

    planner = Path(__file__).resolve().parents[2] / "session_resume_planner.py"
    argv = [win_spawn.quiet_python(), str(planner), "--arm-sentinel", "--session-id", sid]
    if transcript is not None:
        argv += ["--transcript", str(transcript)]
    if claude:
        argv += ["--claude", claude]
    try:
        return subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=ARM_TIMEOUT_SECONDS, check=False,
                              env=dict(env), creationflags=win_spawn.NO_WINDOW).returncode
    except (OSError, subprocess.SubprocessError):
        return 127


def ensure_sentinel(sid: str, env, S: dict, *, transcript=None, claude: str | None = None
                    ) -> tuple[str, str]:
    """回 `("armed", "")` 或 `("absent", 原因)`。已武裝就不重複武裝。"""
    import quota_escalation  # noqa: PLC0415
    import schedule_backend  # noqa: PLC0415
    import sentinel_lifecycle  # noqa: PLC0415

    if env.get(quota_escalation.guard.SENTINEL_OFF_ENV):
        return "absent", "sentinel_off"
    backend = S.get("backend") or schedule_backend.select()
    task = f"{sentinel_lifecycle.TASK_PREFIX}{sid}"

    def armed() -> bool:
        jobs = (S.get("jobs") or backend.list_jobs)(task)
        return jobs is not None and task in jobs

    if armed():
        return "armed", ""
    if S.get("arm_sentinel") is None and "backend" in S:
        # 注入了假後端（測試）卻沒給武裝縫：真 planner 只會註冊到真排程器，絕不呼叫（圍籬）
        return "absent", "injected_backend"
    rc = (S.get("arm_sentinel") or _run_planner)(sid, transcript, claude, env)
    return ("armed", "") if armed() else ("absent", f"arm_rc_{rc}")


def verdict_lines(sid: str, primary: datetime, backup: datetime, cred, sentinel: tuple[str, str],
                  *, platform_name: str | None = None) -> list[str]:
    """貼憑證提示一行＋末行 `PARK_VERDICT=armed …`；非 win32 末行 `route=` 後加
    `backup=absent(platform)`。"""
    state, why = sentinel
    mark = "armed" if state == "armed" else f"absent reason={why}"
    off = " backup=absent(platform)" if (platform_name or sys.platform) != "win32" else ""
    hint = ("宣稱「會自動繼續」時請同時貼：①主載具＝`sessionctl keepwarm` 首行 "
            "`KEEPWARM_PLAN … wake_at=`（背景任務 id）；②備援＝下一行 `PARK_VERDICT` 的 "
            "`next_run=`；缺哪一份就照實寫缺席。")
    last = (f"PARK_VERDICT=armed route=H{off} sid={sid[:8]} "
            f"primary_wake_at={primary.isoformat(timespec='seconds')} "
            f"backup_fire_at={backup.isoformat(timespec='seconds')} "
            f"next_run={str(cred).split('（')[0].strip()} sentinel={mark}")
    return [hint, last]
