"""`sessionctl park` 的 reset 時刻解析（自 `park_cli._cmd_park` 搬出，行為逐字不變）。

為何獨立成檔：`park_cli.py` 貼著 guardrail_lib 400 行線，S2（副作用隔離）要在 `_cmd_park` 加登記前
L1 判準、`--claude` 與沙盒自毀時刻，淨增行數只能靠把「短窗軸／`--at` 解析」這一整段搬出去換。
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
    """`--at`：`(reset, 錯誤)`。須帶 `--why`（≥8 字）、aware、在未來、≤8 天。"""
    if len((opts.why or "").strip()) < park.MIN_WHY_CHARS:
        return None, f"❌ --at 需要 --why（至少 {park.MIN_WHY_CHARS} 字的原因）。"
    try:
        at = datetime.fromisoformat(opts.at)
    except ValueError:
        return None, "❌ --at 須為 ISO 8601 且帶 offset。"
    if at.tzinfo is None or at <= now or (at - now).total_seconds() > park.AT_MAX_SECONDS:
        return None, "❌ --at 須帶 offset、在未來、且不超過 8 天。"
    return at, ""


def _close_stage(S: dict, sid: str, state, env, now: datetime) -> bool:
    """QW §7.1：額度牆 plan 判 `close`（校準後的 V 帶）也算前置成立，不必先爬到準備門檻。
    縫：`S["plan"]`；任何例外 ⇒ 不成立（照舊走準備門檻判準）。"""
    try:
        from . import quotawall  # noqa: PLC0415 — lazy：park 頂層不得 import quotawall 家族

        fn = S.get("plan") or quotawall.plan
        return fn(sid, None, env, now, read_quota=lambda _n: state).stage == quotawall.CLOSE
    except Exception:  # noqa: BLE001
        return False


def resolve(opts, sid: str, S: dict, now: datetime, env=None):
    """`(reset, axis, skew, rc)`；`--at` 走明示時刻，否則取短窗軸達準備門檻者（或 plan 判 `close`）
    的 reset。"""
    if opts.at:
        reset, text = _reset_from_at(opts, now)
        if reset is None:
            _err(text)
            return None, None, 0, _RC_PRECOND
        return reset, None, 0, 0
    import quota_gate  # noqa: PLC0415
    import quota_policy  # noqa: PLC0415

    state = (S.get("quota") or quota_gate.pace_state)(now)
    pol = (S.get("policy") or (lambda: quota_policy.load_policy(quota_gate.policy_env())[0]))()
    hits = park.prepare_hits(state, pol, now)
    why_ok = len((opts.why or "").strip()) >= park.MIN_WHY_CHARS
    if hits == [] and not why_ok and _close_stage(S, sid, state, env, now):
        hits = park.measured_short(state, now)
    if hits == [] and why_ok:
        hits = park.measured_short(state, now)  # 未達門檻但主控判斷下一棒放不下
    reset = park.reset_of(hits) if hits else None
    # 已達標但 reset 解不出＝reset 不明，不是沒達標
    high = [a for a in park.short_axes(state.axes)
            if park._real_pct(a.pct) and a.pct >= pol.prepare_pct]
    if hits is None or (not hits and (high or why_ok)):
        text = ("❌ park 拒絕：量不到短窗軸的 reset 時刻（"
                f"{state.source}／{state.reason}）。reset 是滾動視窗、只能觀測不能算，"
                "本工具不假設 5 小時。請稍後重試，或明示 --at <ISO> --why \"<WHY>\"。")
    elif not hits:
        text = (f"❌ park 拒絕：沒有短窗軸達準備門檻（{pol.prepare_pct:.0f}pp）。"
                "若判斷下一棒這一窗放不下，加 --why \"<WHY≥8字>\"（reset 取短窗觀測值）；"
                "若因週額度等停工，請明示 --at <ISO> --why \"<WHY≥8字>\"（上限 8 天）。")
    else:
        text = ""
    if text:
        _err(text)
        switch.trace("park_refused", sid=sid, why=text, code=_RC_REFUSED)
        return None, None, 0, _RC_REFUSED
    top = max(hits, key=lambda a: a.pct)
    import quota_messages  # noqa: PLC0415

    return reset, {"kind": top.kind, "pct": top.pct}, quota_messages.HALT_RESET_SKEW_SECONDS, 0
