"""`--pace` 標題的短窗最高帶欄（QW W11b 前半，REQ-QW-78）；`quota_messages.pace_line` 呼叫。

只動呈現層：不改 `quota_policy._binding_key`、不改 band 判定（R59 語意靠平手規則）
"""
from __future__ import annotations

import quota_policy

_BAND_RANK = {b: i for i, b in enumerate((quota_policy.BAND_FREE, quota_policy.BAND_NOTICE,
                                          quota_policy.BAND_CONVERGE, quota_policy.BAND_PREPARE,
                                          quota_policy.BAND_HALT))}
SHORT_KINDS = ("five_hour", "session", "5h")


def short_window_note(decision: quota_policy.Decision) -> str:
    """短窗帶高於 binding 帶時回「｜短窗=<band> <kind> <pct>% 剩 N 分」，否則空字串。

    WHY：平手時 `_binding_key` 取 horizon 較長者（週軸）；標題只講 binding 會把「五小時窗已在
    converge」藏起來（2026-11-23 10:02 事故）。短窗不高於 binding 帶、量不到 ⇒ 不補。
    """
    shorts = [r for r in decision.per_axis if r.axis.kind in SHORT_KINDS and r.band in _BAND_RANK]
    if not shorts or decision.band not in _BAND_RANK:
        return ""
    top = max(shorts, key=lambda r: (_BAND_RANK[r.band], r.axis.pct))
    if _BAND_RANK[top.band] <= _BAND_RANK[decision.band]:
        return ""
    when = f"剩 {int(top.minutes)} 分" if top.minutes is not None else "reset 距離不明"
    return f"｜短窗={top.band} {top.axis.kind} {top.axis.pct:g}% {when}"
