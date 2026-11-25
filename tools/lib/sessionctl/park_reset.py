"""`sessionctl park` 的前置：當下重算單一權威判決，取 reset 時刻（QVD §3.5 C6、§5；R-4.1.6-5）。

park 只在判決 `PARK｜HALT_WEEKLY` 時登記；其餘一律 rc 4 並印判決行（訊息與判決動作一致）。
`--why` 已退役（只留給 `--done`），改 `--next-est <pp>`：缺省＝`cal_agent × max(1, n_plan)`，
給的值低於缺省取缺省（只能往上調）。`--at` 保留，但判決須為 `HALT_WEEKLY` 或 `PARK`。
回 `(reset, axis, skew, rc)`：`rc` 非 0 ＝拒絕（文字已印到 stderr、`park_refused` 痕跡已落）。
"""
from __future__ import annotations

import sys
from datetime import datetime

from . import park, switch

_RC_PRECOND, _RC_REFUSED = 2, 4


def _err(text: str) -> None:
    print(text, file=sys.stderr)


def _reset_from_at(opts, now: datetime):
    """`--at`：`(reset, 錯誤)`。aware、在未來、≤8 天（自由文字理由改 `--note`，只進痕跡）。"""
    try:
        at = datetime.fromisoformat(opts.at)
    except ValueError:
        return None, "❌ --at 須為 ISO 8601 且帶 offset。"
    if at.tzinfo is None or at <= now or (at - now).total_seconds() > park.AT_MAX_SECONDS:
        return None, "❌ --at 須帶 offset、在未來、且不超過 8 天。"
    return at, ""


def ruling_for(sid: str, S: dict, now: datetime, env=None, next_est: float | None = None, *,
               default_est: bool = True):
    """當下判決（縫：`S["quota"](now)` 取讀數、`S["plan"]` 取計畫；缺＝`ruling_io.gather`）。
    park 前置的 `next_est` 一律取 `max(給的值, 缺省值)`（F-25：方向保守，多 park、不少 park）；
    提前恢復（C21）不帶下一棒估計（`default_est=False`）。"""
    import quota_gate  # noqa: PLC0415

    from . import ruling_io  # noqa: PLC0415 — lazy：park 頂層不 import 判決取數

    run_env = dict(quota_gate.policy_env())
    run_env.update(env or {})
    if S.get("quota"):
        state = S["quota"](now)
        dec = quota_gate.dispatch_decision(state, now, run_env, peek=True)
        plan = (S["plan"](sid, None, run_env, now, read_quota=lambda _n: state)
                if S.get("plan") else None)
        snap = ruling_io.compose(state, dec, now, sid=sid, env=run_env, plan=plan)
    else:
        snap = ruling_io.gather(sid, env=run_env, now=now)
    est = (max(float(next_est or 0.0), ruling_io.default_next_est(snap.plan, run_env))
           if default_est else next_est)
    return ruling_io.compose(snap.state, snap.decision, now, sid=sid, env=run_env,
                             plan=snap.plan, next_est=est)


def _refuse(sid: str, text: str) -> tuple:
    _err(text)
    switch.trace("park_refused", sid=sid, why=text, code=_RC_REFUSED)
    return None, None, 0, _RC_REFUSED


def resolve(opts, sid: str, S: dict, now: datetime, env=None):
    """`(reset, axis, skew, rc)`。判決非 `PARK｜HALT_WEEKLY` ⇒ rc 4（訊息附判決行）。"""
    import quota_ruling as QR  # noqa: PLC0415

    snap = ruling_for(sid, S, now, env, getattr(opts, "next_est", None))
    r = snap.ruling
    line = QR.line(r)
    if r.action not in (QR.PARK, QR.HALT_WEEKLY):
        hint = {QR.WAIT_RESET: "短窗即將重置：掛 `sessionctl keepwarm` 等重置，不 park。",
                QR.NODISPATCH: "不派新、在飛照跑；短窗 reset 量不到一律拒絕，不假設 5 小時。",
                QR.CONTINUE: "判決准許續跑，不需要 park；下一棒放不下請帶 `--next-est <pp>`。"}
        if r.degraded:  # 量不到讀數：不是「額度夠」，是「量不到就不登記」（不假設 5 小時）
            hint[QR.CONTINUE] = "額度量不到：照降級上限續跑、不 park（量不到 reset 不假設 5 小時）"
        return _refuse(sid, f"❌ park 拒絕：判決 {r.action}。{hint[r.action]}\n{line}")
    if opts.at:
        reset, text = _reset_from_at(opts, now)
        if reset is None:
            _err(text)
            return None, None, 0, _RC_PRECOND
        switch.trace("park_at_note", sid=sid, note=getattr(opts, "note", None), vid=r.vid)
        return reset, None, 0, 0
    reset = QR._aware(r.win if r.action == QR.PARK else r.wk)  # noqa: SLF001
    if reset is None:
        return _refuse(sid, "❌ park 拒絕：判決沒有可等的 reset（月度支出上限要人提額，"
                            f"不是等重置）。\n{line}")
    hits = park.measured_short(snap.state, now)
    top = max(hits, key=lambda a: a.pct) if hits else None
    import quota_messages  # noqa: PLC0415

    axis = {"kind": top.kind, "pct": top.pct} if top is not None else None
    return reset, axis, quota_messages.HALT_RESET_SKEW_SECONDS, 0
