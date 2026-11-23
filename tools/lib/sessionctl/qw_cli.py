"""`sessionctl quotawall` 唯讀動詞與 `sessionctl status` 的憑證列（QuotaWall DES S-9／§10；Q4）。

入口 `tools/sessionctl.py` 只呼叫本檔（薄殼無判準）：
  · `quotawall [--sid <sid>] [--projects-dir <根>]`：印 `quotawall.plan_lines`（人讀一行＋末行
    `QUOTAWALL_PLAN=…`），另一行 `QUOTAWALL_TARGET=…`（`wake_target` 來源與時刻，無則 `none`）。
    唯讀、零 token、只讀額度快取（陳舊時依 S-23 補量一次）；任何情形 rc 0（量不到＝`stage=none`），
    sid 缺席 rc 2。無人窗口印 `stage=none reason=unattended`（plan 自己判）。
  · `status_lines`：`primary:`／`backup:`／`sentinel:` 三列（判準單一家＝`park_status.lines`）。
"""
from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping
from datetime import datetime

from . import keepwarm, park, park_status, qw_plan, qw_schema, roster

USAGE_RC = 2


def _target_line(sid: str, transcript, env, now: datetime, plan: qw_plan.Plan) -> str:
    when, source, _ref = qw_plan.wake_target(sid, transcript, env, now, plan_=plan)
    return (f"QUOTAWALL_TARGET={'none' if when is None else qw_schema.iso(when)} "
            f"source={source}")


def cli(argv: list[str], env: Mapping | None = None, *, now: datetime | None = None,
        out=None, **seams) -> int:
    """見檔頭。`now`／`seams`（`read_quota`／`refresh`／`ledger`／`live_fn`）供測試注入。"""
    env, out = os.environ if env is None else env, out or sys.stdout
    ap = argparse.ArgumentParser(prog="sessionctl quotawall")
    ap.add_argument("--sid")
    ap.add_argument("--projects-dir", help="逐字稿根目錄（預設＝Claude home 的 projects；測試用）")
    args = ap.parse_args(argv)
    sid = args.sid or str(env.get("CLAUDE_CODE_SESSION_ID", "")).strip()
    if not sid or not roster._ID_RE.match(sid):
        print("sessionctl quotawall：缺 --sid（或形態不合），且 CLAUDE_CODE_SESSION_ID 未設",
              file=sys.stderr)
        return USAGE_RC
    now = now or datetime.now().astimezone()
    transcript = keepwarm.find_transcript(sid, args.projects_dir)
    plan = qw_plan.plan(sid, transcript, env, now, **seams)
    for line in qw_plan.plan_lines(plan):
        print(line, file=out)
    print(_target_line(sid, transcript, env, now, plan), file=out)
    return 0


def status_lines(sid: str) -> list[str]:
    """`sessionctl status` 的憑證三列（唯讀）；量不到整體降級成一行說明，不拋。"""
    try:
        return park_status.lines(sid, park.read_marker(sid))
    except Exception as exc:  # noqa: BLE001 — status 是唯讀診斷
        return [f"憑證列：量不到（{type(exc).__name__}）"]
