"""sessionctl 模型平衡建議（ADR-XPLAT-004 §2.13.7 D8；AT-SC-81～84）：只出聲、不改任何派工參數。

對 `weekly_all` 與主控家族的模型專屬週軸各算 `ratio = 用量比 ÷ 時間流逝比`：`elapsed = 1 −
(resets_at − now)/7d`，夾在 [0.05, 1]；`resets_at` 缺 ⇒ 該軸不判（印「量不到」，不猜）。軸物件
用屬性取值（`kind`／`pct`／`resets_at`／`scope_model`），`quota_policy.Axis` 與測試替身皆可。
"""
from __future__ import annotations

from datetime import datetime

from .procstop import parse_iso

WEEK_SECONDS = 7 * 86400
GAP = 0.15  # 兩軸 ratio 差達此值才說誰超前
WIDE = 0.8  # 兩軸 ratio 皆低於此值 ⇒ 兩軸皆寬
_ALL_KINDS = ("weekly_all", "seven_day")
_SCOPED_KINDS = ("weekly_scoped", "seven_day_opus", "seven_day_sonnet")
_CLAMP_LOW = 0.05


def _ratio(axis, now: datetime) -> tuple[float | None, str]:
    """`(ratio, 量不到原因)`。"""
    reset = parse_iso(getattr(axis, "resets_at", None))
    if reset is None:
        return None, f"{axis.kind} 缺 resets_at，該軸不判"
    left = max(0.0, reset - now.timestamp())
    elapsed = min(1.0, max(_CLAMP_LOW, 1.0 - left / WEEK_SECONDS))
    return float(axis.pct) / 100.0 / elapsed, ""


def _pick(axes, kinds, family: str | None):
    """第一個 kind 吻合（且專屬軸的 `scope_model` 含主控家族）的軸；沒有回 `None`。"""
    for axis in axes:
        if getattr(axis, "kind", "") not in kinds:
            continue
        if family is not None:
            scope = str(getattr(axis, "scope_model", "") or "").lower()
            if family not in scope:  # 專屬軸看不出是哪個模型 ⇒ 不猜
                continue
        return axis
    return None


def advice_line(axes, *, now: datetime | None = None, family: str = "fable") -> str:
    """一行模型建議（含「模型建議：」前綴）。四種情境：專屬軸超前／全模型超前／兩軸皆寬／平衡；
    任一軸量不到 ⇒ 寫「量不到：<原因>」，不拋。"""
    now = now or datetime.now().astimezone()
    name = family.capitalize()
    both = _pick(axes, _ALL_KINDS, None)
    scoped = _pick(axes, _SCOPED_KINDS, family.lower())
    notes: list[str] = []
    ratios: dict[str, float] = {}
    for label, axis in (("全模型", both), (name, scoped)):
        if axis is None:
            notes.append(f"{label}軸缺席")
            continue
        value, why = _ratio(axis, now)
        if value is None:
            notes.append(why)
        else:
            ratios[label] = value
    if len(ratios) < 2:
        return f"模型建議：量不到：{'；'.join(notes) or '兩軸皆無讀數'}（不比較、不建議）"
    gap = round(ratios[name] - ratios["全模型"], 9)  # 浮點誤差不得讓恰 0.15 的邊界掉到另一側
    if gap >= GAP:
        return f"模型建議：{name} 超前：多外派、主控只做判斷／派工／親驗"
    if gap <= -GAP:
        return ("模型建議：全模型超前：子代理降級（Opus→Sonnet→Haiku）、短任務書、禁續棒；"
                "判斷性工作主控可自做")
    if max(ratios.values()) < WIDE:
        return "模型建議：兩軸皆寬：深度審查可用 Opus"
    return "模型建議：平衡"


def pace_line(quota_gate, family: str | None = None, now: datetime | None = None) -> str:
    """`--pace` 接線用：讀額度快取（唯讀、不連網）→ 一行建議（含換行）；任何失敗收成「量不到」。"""
    try:
        now = now or datetime.now().astimezone()
        state = quota_gate.read_quota(now)
        if not state.axes:
            return f"模型建議：量不到：額度快取不可用（{state.reason}）\n"
        return advice_line(state.axes, now=now, family=family or "fable") + "\n"
    except Exception as exc:  # noqa: BLE001 — 診斷行不得擋 --pace 本體
        return f"模型建議：量不到（{type(exc).__name__}）\n"
