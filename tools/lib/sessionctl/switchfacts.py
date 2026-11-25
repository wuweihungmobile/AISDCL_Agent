"""換手決策表的事實讀取器（Control_Handover DES §7.1、§7.4；W5）。

WHY 與 `switchplan` 分兩檔：`handoff.advise_once` 要呼叫 `switchplan`，而讀取事實（封存、交接包、
逐字稿、額度）必須 import `seal`／`handoff`——放在同一檔會成環（handoff → switchplan → seal →
handoff）。本檔向各真相源取值、不重寫判準：封存四值 `seal.effective`、已交棒 `seal.handed_over`、
硬線 `switch.threshold`、快取冷熱 `cachestate`、額度 `park._pace_state`／`qw_plan`；量不到一律保守值
（`None`／`unknown`），不猜。`watch` 與 `controlfacts` 共用 `pending_state`。
"""
from __future__ import annotations

import json
import os
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

from . import (
    cachestate,
    control,
    handoff,
    park,
    parkprobe,
    qw_plan,
    roster,
    seal,
    switch,
    switchplan,
)


def _guard(fn, default):
    try:
        return fn()
    except Exception:  # noqa: BLE001 — 唯讀診斷：量不到落回保守值，不拋
        return default


def ctx_of(transcript) -> int | None:
    if transcript is None or not Path(transcript).is_file():
        return None
    return _guard(lambda: roster._scan(Path(transcript), False)["ctx_tokens"], None)


def compactions(transcript) -> int:
    """逐字稿 `system／compact_boundary` 的累計次數（與 hook 的 `compact_boundary_count` 同判準；
    該函式住 `.claude/hooks/`，不可 import，這裡自帶一份）。讀不到 ⇒ 0。"""
    count = 0
    try:
        with Path(transcript).open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if '"compact_boundary"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if isinstance(rec, dict) and rec.get("type") == "system" \
                        and rec.get("subtype") == "compact_boundary":
                    count += 1
    except (OSError, TypeError):
        return 0
    return count


def sealed_of(sid: str, transcript, env) -> str:
    """本 sid 最新包的封存四值；沒有包 ⇒ `none`（從未封存）。"""
    pkg = _guard(lambda: seal.latest_package(sid, env), None)
    if not isinstance(pkg, dict):
        return control.SEAL_NONE
    return _guard(lambda: seal.effective(pkg["path"], transcript), control.SEAL_UNREADABLE)


def pending_state(sid: str, transcript, agents: int, env: Mapping | None = None,
                  now: datetime | None = None, base: Path | None = None) -> dict | None:
    """惰性建立＋讀取有效的 pending 標記（`watch` 輪詢與 `control_state`／`switch-plan` 兩個呼叫點，
    DES §7.4）。任何例外 ⇒ `None`（提示類功能不得反過來擋住監督迴圈）。"""
    env = os.environ if env is None else env
    try:
        ctx = ctx_of(transcript)
        hard = switch.threshold(switch.HARD_CTX_KEY, env)[0]
        if switchplan.ensure_pending(sid, ctx=ctx, hard=hard, agents=agents, now=now,
                                     base=base) is None:
            return None  # 沒有標記：不必再讀封存／交接包（watch 每輪都走這裡，省 I/O）
        return switchplan.read_pending(
            sid, ctx=ctx, hard=hard, sealed=sealed_of(sid, transcript, env),
            handed_over=_guard(lambda: seal.handed_over(sid, env), None) is not None, base=base)
    except Exception:  # noqa: BLE001
        return None


def watch_state(sid: str, transcript, agents: int, env: Mapping | None = None):
    """`watch` 輪詢的一行掛點：回 `(有效 pending｜None, switch_due 明細｜None)`。"""
    pend = pending_state(sid, transcript, agents, env)
    return pend, switchplan.due_text(pend, agents)


def takeover_min(sid: str, env, now: datetime) -> float | None:
    """本 sid 是某包的接手者（`.ack` 內 `sid=` 為本 sid）⇒ 最近 `.ack` 距今分鐘；否則 `None`。"""
    best = None
    for row in _guard(lambda: handoff.list_handoffs(None, None, env), []):
        path = Path(row["path"])
        if seal.acker_sid(path) != sid:
            continue
        try:
            parts = path.with_suffix(".ack").read_text(encoding="utf-8").split()
            stamp = datetime.fromisoformat(parts[1]).timestamp()
        except (OSError, ValueError, IndexError):
            continue
        best = stamp if best is None else max(best, stamp)
    return None if best is None else max(0.0, (now.timestamp() - best) / 60)


def quota_facts(sid: str, transcript, env, now: datetime, S: Mapping | None = None):
    """額度面輸入（QVD §3.5 C13 ④）：由 `ruling_io` 取**判決**組 `Quota`，本檔不自讀門檻。
    縫：`S["state"](now)` 換讀數、`S["plan"]` 換計畫（只取 `d_min`／`stale`）。取數失敗 ⇒
    `action=None`（`_wall` 回 None，與量不到偏續跑同向）。"""
    from . import ruling_io  # noqa: PLC0415 — lazy：ruling_io 依賴 qw_plan／keepwarm

    S = S or {}

    def _snap():
        if S.get("state") is None:
            return ruling_io.gather(sid, transcript, env=_merged(env), now=now)
        import quota_gate  # noqa: PLC0415

        state = S["state"](now)
        seam = S["plan"](sid, transcript, env, now) if S.get("plan") else None
        dec = quota_gate.dispatch_decision(state, now, _merged(env), peek=True)
        return ruling_io.compose(state, dec, now, sid=sid, transcript=transcript,
                                 env=_merged(env), plan=seam)

    snap = _guard(_snap, None)
    r = getattr(snap, "ruling", None)
    # 診斷／排程用（QVD §3.5.3 白名單）：只取 d_min／stale 供輪詢形態，不據以決定五類。
    plan = _guard(lambda: (S.get("plan") or qw_plan.plan)(sid, transcript, env, now), None)
    marker = _guard(lambda: park.read_marker(sid), None)
    cred = bool(_guard(lambda: park.credential_ok(marker, now)[0], False))
    return switchplan.Quota(
        action=getattr(r, "action", None), win=getattr(r, "win", None),
        wk=getattr(r, "wk", None), vid=getattr(r, "vid", None), credential=cred,
        stale=bool(getattr(plan, "stale", False)), wait_min=getattr(plan, "d_min", None))


def _merged(env) -> dict:
    import quota_gate  # noqa: PLC0415

    out = dict(quota_gate.policy_env())
    out.update(env or {})
    return out

def account_changed(sid: str, now: datetime, S: Mapping | None = None) -> bool:
    """park 標記的 `parked_account` 與當下快取 `account_key` 皆非空且不同才為真（量不到＝假）。
    沒有 park 標記就不讀額度（基準只存在於 park 標記，DES §7.1）。"""
    marker = _guard(lambda: park.read_marker(sid), None)
    if not isinstance(marker, dict) or not marker.get(parkprobe.MK_PARKED_ACCOUNT):
        return False
    state = _guard(lambda: ((S or {}).get("state") or park._pace_state)(now), None)  # noqa: SLF001
    return parkprobe.account_changed(marker, getattr(state, "account_key", None))


def cache_of(transcript, now: datetime) -> str:
    info = _guard(lambda: cachestate.cache_state(transcript, now), {}) if transcript else {}
    if info.get("idle_s") is None:
        return "unknown"
    return "cold" if info.get("cold") else "hot"
