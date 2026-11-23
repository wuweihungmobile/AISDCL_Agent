"""park 到點的「失敗鏈」：F4 選的路 → 另一條路 → 終局（QuotaWall DES §7.4～§7.5；R218 Q3）。

WHY（2026-11-20 22:42 真事件）：到點只試一條路、失敗就靜默結束，主控斷線也沒有人知道。本檔把「每一次
spawn 嘗試」收成同一個流程：先寫 `session_switch_spawning` 意圖、呼叫 spawn 函式、落 `park_attempt`
痕跡（實際值，**不寫字面 rc**，MU-QW-21）、失敗再寫同 attempt 的失敗列（`seal._spawned`
據此不算交棒）、
換另一條路。spawn 函式回 `sandbox_scope.RC_SIDEEFFECT_REFUSED`（L1 拒絕）＝終局，
不走另一路（§7.5-1a）。
spawn 的 runner 呼叫仍住在 `park_cli.spawn_resume`／`handoff.spawn`（站點本體，各自先過 L1）；
本檔只做
編排，所以不含任何開窗形態（站點普查不需要為它另開一列）。

意圖欄位：`handoff`＝包路徑只給「會交棒」的路（FRESH、fork）；普通 `-r`（同 session 自續跑，
不是交棒）
改記 `pkg`——否則 `seal.handed_over` 會在 TTL 內把剛續跑的 session 自己判成「已交棒」
（mark_resumed 不清
意圖列）。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, NamedTuple

import endurance_env
import sandbox_scope

from . import handoff, park, qw_schema, switch

EV_ATTEMPT = "park_attempt"
TRACE_NAME = "autosdd_session_switch.jsonl"
DONE_EVENT = {park.FIRE_RESUME: "park_resumed", park.FIRE_FRESH: "park_spawned"}


class Outcome(NamedTuple):
    """`kind`：fired｜failed｜refused｜skipped；`attempts`：逐筆實際值；`event`：成功時的終態痕跡名；
    `reason`：skipped 的原因。"""
    kind: str
    attempts: list
    event: str = ""
    reason: str = ""


def other_route(route: str) -> str:
    return park.FIRE_FRESH if route == park.FIRE_RESUME else park.FIRE_RESUME


def trace_rows(*events: str) -> list[dict]:
    """`autosdd_session_switch.jsonl` 的列（唯讀；讀不到 ⇒ 空）。`events` 空＝全部。"""
    try:
        lines = (endurance_env.trace_dir_peek()[0] / TRACE_NAME).read_text(
            encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict) and (not events or rec.get("event") in events):
            out.append(rec)
    return out


def _pkg_of(rec: dict):
    return rec.get("handoff") or rec.get("pkg")


def next_attempt(pkg) -> int:
    """同一個交接包已用過的 attempt 最大值＋1（job 與哨兵接手共用同一本帳，序號不重複，
    否則舊失敗列會把新意圖誤判成已失敗）。"""
    used = [r.get(qw_schema.SPAWN_ATTEMPT_KEY) for r in trace_rows(qw_schema.EV_SPAWNING)
            if str(_pkg_of(r)) == str(pkg)]
    return 1 + max((n for n in used if type(n) is int), default=0)


def write_intent(sid: str, pkg, attempt: int, route: str, fork: bool) -> None:
    """spawn 呼叫**之前**寫（先於任何呼叫，才沒有「窗已開、痕跡還沒落」的競態窗）。"""
    owner = "handoff" if (route == park.FIRE_FRESH or fork) else "pkg"
    switch.trace(qw_schema.EV_SPAWNING, sid=sid, route=route, fork=fork,
                 **{owner: str(pkg), qw_schema.SPAWN_ATTEMPT_KEY: attempt})


def write_failed(sid: str, pkg, attempt: int, route: str, fork: bool, rc) -> None:
    """同 attempt 的失敗列（`qw_schema.is_failure_row` 認）。"""
    owner = "handoff" if (route == park.FIRE_FRESH or fork) else "pkg"
    switch.trace(qw_schema.EV_SPAWNING, sid=sid, route=route, fork=fork, ok=False, rc=rc,
                 **{owner: str(pkg), qw_schema.SPAWN_ATTEMPT_KEY: attempt})


def _record(sid: str, attempts: list, attempt: int, route: str, attempted: bool, rc, reason: str,
            fork: bool) -> None:
    row = {"route": route, "attempted": attempted, "rc": rc, "reason": reason, "fork": fork}
    attempts.append(row)
    switch.trace(EV_ATTEMPT, sid=sid, **{qw_schema.SPAWN_ATTEMPT_KEY: attempt}, **row)


def _preflight(S: dict, pkg) -> list[str]:
    """FRESH 的 spawn 前置預演（未 finalize／工作樹髒且無 wip tag／有在飛代理）。換掉整個 spawn
    的測試縫
    （`S["spawn"]`）自己負責前置，除非另給 `S["preflight"]`。"""
    fn = S.get("preflight") or (None if S.get("spawn") else handoff.spawn_preflight)
    return list(fn(pkg, runner=S.get("runner"), roster_mod=S.get("roster")) or []) if fn else []


def run(sid: str, pkg, first: str, *, claude: str | None, env, S: dict, clock,
        stuck_close: bool = False) -> Outcome:
    """依序嘗試 `first` → 另一條；任一次成功即 `fired`。非 win32 不呼叫任何 spawn（S-14）。"""
    from . import oldwin_park, park_cli  # noqa: PLC0415 — lazy：兩者反向呼叫本檔

    attempts: list = []
    attempt = next_attempt(pkg)
    if (S.get("platform") or sys.platform) != "win32":
        _record(sid, attempts, attempt, first, False, None, "platform_unsupported", False)
        return Outcome("failed", attempts)
    kw = {"claude": claude} if claude else {}
    for route in (first, other_route(first)):
        fork = False
        if route == park.FIRE_RESUME:
            gate = oldwin_park.resume_gate(sid, pkg, env, clock(), S, stuck_close=stuck_close)
            if gate["act"] == "skip":
                return Outcome("skipped", attempts, reason=gate["reason"])
            fork = gate["act"] == "fork"
        else:
            refused = _preflight(S, pkg)
            if refused:
                _record(sid, attempts, attempt, route, False, None, "; ".join(refused), False)
                attempt += 1
                continue
        write_intent(sid, pkg, attempt, route, fork)
        if route == park.FIRE_RESUME:
            fn = S.get("resume") or park_cli.spawn_resume
            rc = fn(sid, pkg, env=env, **({"fork": True} if fork else {}), **kw)
        else:
            rc = (S.get("spawn") or handoff.spawn)(pkg, **kw)
        if rc == sandbox_scope.RC_SIDEEFFECT_REFUSED:  # L1 拒絕＝終局：不算失敗、不走另一路
            write_failed(sid, pkg, attempt, route, fork, rc)
            _record(sid, attempts, attempt, route, True, rc, "sideeffect_refused", fork)
            return Outcome("refused", attempts)
        if rc == 0:
            _record(sid, attempts, attempt, route, True, rc, "", fork)
            return Outcome("fired", attempts, DONE_EVENT[route])
        write_failed(sid, pkg, attempt, route, fork, rc)
        _record(sid, attempts, attempt, route, True, rc,
                "resume_failed" if route == park.FIRE_RESUME else "spawn_failed", fork)
        attempt += 1
    return Outcome("failed", attempts)


def settle(marker: dict, status: str, event: str, attempts: list | None = None,
           **detail: Any) -> None:
    """標記改終態＋outcome（含逐筆 `attempts`）；寫不進去不拋（痕跡已落）。"""
    outcome = {"at": datetime.now().astimezone().isoformat(), "event": event,
               "detail": str(detail)}
    if attempts is not None:
        outcome["attempts"] = attempts
    park.write_marker(dict(marker, status=status, outcome=outcome))


def pkg_of_marker(marker: dict) -> Path | None:
    return Path(marker["pkg"]) if marker.get("pkg") else None
