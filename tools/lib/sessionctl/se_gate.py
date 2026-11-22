"""sessionctl 站點的 L1 副作用隔離接線（DES RealVerify_SideEffect_Isolation §3.4／§4.2；S2）。"""
# 立案：2026-11-20 幽靈 session 57d0ccad（DEF-200-632）——驗證案例的 park 排程在沙盒外到點、
# 開了真視窗跑 `claude -r`。判準本體住 `sandbox_scope`（只吃目標自帶資料，不讀 env、不開行程）；
# 本檔只是 sessionctl 站點（park fire／spawn／登記、舊窗重試登記、handoff spawn）的共用接點，
# 讓同一份拒絕痕跡、stderr 文字與 rc 只有一個家（park_cli／handoff／oldwin_*／都經這裡）：
#   · `check`：到點／spawn 站點首判；拒絕＝落痕跡＋stderr，由呼叫端決定終局（fire 站點寫標記
#     `refused`、spawn 站點回 `RC_SIDEEFFECT_REFUSED`）。拒絕是終局：不進讓路觀察、
#     不寫 handback、不入佇列。
#   · `register`：登記站點首判；放行時同時決定 job 環境轉送（`sandbox` 取自判決，D-20，站點不自行
#     推斷）與 OS 自毀時刻；拒絕＝rc 4（判準）或 2（job 環境值不合法）、不登記。
#   · `refused_notes`：SessionStart 公告「到點被產品面拒絕」（標記 `refused`；不是失敗）。
# 🔴 守衛面（根 CLAUDE.md〈守衛面准入〉）：暴露證據同 DES §1（幽靈 session 57d0ccad、A6f 鑑定）。
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

import endurance_env
import sandbox_scope
import sched_isolation

from . import park, switch

RC_REGISTER_REFUSED = sched_isolation.RC_REGISTER_REFUSED


class Registration(NamedTuple):
    """登記判決：`rc` 非 0 ＝拒絕（不登記）；`extra`＝併進 job argv 的 `--job-env`／`--claude`；
    `expire`＝沙盒目標的 OS 自毀時刻（正式目標 None ⇒ 登記內容與修改前逐字相同）。"""

    rc: int
    extra: list[str]
    expire: datetime | None


def _now() -> datetime:
    return datetime.now().astimezone()


def _refuse(site: str, reason: str, roots, **fields) -> None:
    switch.trace("sideeffect_refused", site=site, reason=reason, roots=list(roots), **fields)
    print(f"❌ 副作用隔離拒絕（{site}）：{reason}", file=sys.stderr)  # pythonw：stderr None 靜默


def check(site: str, *, repo, pkg, sid: str, claude: str | None, projects_dir=None,
          **fields) -> sandbox_scope.Verdict | None:
    """到點／spawn 站點首判；`None`＝放行。`exe`＝這一次要用的 `claude`（未給 `--claude` ⇒
    `"claude"`，D-18）；逐字稿路徑只用於 slug 判斷（由 repo 的專案目錄＋sid 算出，不讀檔）。"""
    try:
        from . import handoff  # noqa: PLC0415 — lazy：handoff 反向 import 本檔
        proj = Path(projects_dir) if projects_dir is not None else handoff._project_dir(Path(repo))
        transcript = proj / f"{sid}.jsonl"
    except Exception:  # noqa: BLE001 — 算不出路徑 ⇒ 不給 transcript（判準仍看 cwd／pkg）
        transcript = None
    verdict = sandbox_scope.target_verdict(cwd=repo, pkg=pkg, transcript=transcript,
                                           exe=claude or "claude", now=_now())
    if verdict.allow:
        return None
    _refuse(site, verdict.reason, verdict.roots, sid=sid, **fields)
    return verdict


def register(site: str, *, repo, pkg, fire: datetime, env, sid: str = "",
             claude: str | None = None) -> Registration:
    """登記前首判（沙盒時 `fire > allow_until` ⇒ `lease_shorter_than_fire`）。"""
    now = _now()
    verdict = sandbox_scope.register_verdict(cwd=repo, pkg=pkg, fire_at=fire, now=now)
    if not verdict.allow:
        _refuse(site, verdict.reason, verdict.roots, sid=sid)
        return Registration(RC_REGISTER_REFUSED, [], None)
    sandbox = verdict.reason == "sandbox_lease"
    try:
        extra = endurance_env.job_env_argv(env, sandbox=sandbox)
    except endurance_env.JobEnvValueError as exc:
        _refuse(site, f"job_env:{exc}", verdict.roots, sid=sid)
        return Registration(exc.rc, [], None)
    if claude:
        extra += ["--claude", claude]
    home = sandbox_scope.sandbox_home(repo) if sandbox else None
    return Registration(0, extra, sandbox_scope.job_expiry(home, now))


def refused_notes(sid: str) -> list[str]:
    """本 session 的 park 標記為 `refused` ⇒ 一行公告；其餘（含讀不到）空。**不是失敗**：沒有任何
    事需要處置，所以不用警示詞、不指路修復。"""
    try:
        marker = park.read_marker(sid) if sid else None
    except Exception:  # noqa: BLE001 — 公告是唯讀診斷
        return []
    if not marker or marker.get("status") != "refused":
        return []
    detail = (marker.get("outcome") or {}).get("detail", "")
    return [f"ℹ️ park 到點被產品面拒絕（副作用隔離；目標是驗證沙盒、不是正式 session）{detail}"]
