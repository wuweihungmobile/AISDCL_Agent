"""QuotaWall 讀數與牆偵測：讀數年齡（S-23）與 `wall_state`（R218 Q1；DES §3、REQ-QW-05／64）。

讀數年齡：短窗讀數帶 `reading_at`（伺服器回應時刻＝`QuotaState.measured_at`）。年齡超過
`TTL＋watch POLL`（210 秒）⇒ 同步補量一次（零 token 的 `/api/oauth/usage`）；補不到 ⇒ 呼叫端以
`R_eff` 保守外推並標 `stale`；讀數所屬視窗的 reset 已過 ⇒ 舊窗讀數＝量不到（不外推）。
全部縫可注入（`read_quota`／`refresh`），不開任何測試用環境變數。
"""
from __future__ import annotations

import math
import re
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

import transcript_activity

from . import qw_calc, qw_schema, roster

CUT, SYNTHETIC, QUOTA = "cut", "synthetic", "quota"
CACHE_LIFE_SEC = 3600  # 主控快取壽命（1 小時層）：cold_at＝最後一筆真 usage ＋ 此值
_WALL_TEXT_RE = re.compile(r"hit your|usage limit", re.IGNORECASE)


class Reading(NamedTuple):
    """`state` 為 None ⇒ 量不到（`reason` 說明：unmeasured｜no_reset｜stale_window｜error）。"""

    state: object | None
    reading_at: float | None
    age: float | None
    stale: bool          # True＝補量失敗，數值已過期（呼叫端須外推）
    reason: str
    refreshed: bool


def default_read(now: datetime):
    from . import park  # noqa: PLC0415 — park 不 import 本模組；lazy 只為縮小匯入面

    return park._pace_state(now)


def default_refresh(now: datetime):
    """補量一次（鏡像 `quota_gate.pace_state` 的補量半段；零 token）。失敗拋例外。"""
    import quota_gate  # noqa: PLC0415

    if quota_gate.quota_meter is None:
        raise RuntimeError("quota_meter 不可用")
    if won := quota_gate.claim_refresh_slot():
        reading = quota_gate.quota_meter.measure_detail(quota_gate.QUOTA_SYNC_TIMEOUT_SECONDS)[0]
        if reading is None:
            raise RuntimeError("補量沒有讀數")
        quota_gate.quota_meter.write_cache(reading, quota_gate.quota_cache_path())
    return quota_gate.settled_quota(won)


def _reset_epoch(axis) -> float | None:
    return qw_schema.parse_epoch(axis.resets_at)


def short_view(state) -> tuple[list, list]:
    """`(有限讀數的短窗軸, 其中 reset 可解析者)`；同 `park.measured_short`，不看 reset 是否未過。"""
    from . import park  # noqa: PLC0415

    real = [a for a in park.short_axes(state.axes) if park._real_pct(a.pct)]
    return real, [a for a in real if _reset_epoch(a) is not None]


def _classify(state, now: datetime) -> tuple[str, list]:
    """`("ok"｜"unmeasured"｜"no_reset"｜"dead", 未過期的短窗軸)`。"""
    if state is None or not getattr(state, "axes", ()):
        return "unmeasured", []
    real, parsed = short_view(state)
    if not real:
        return "unmeasured", []
    if not parsed:
        return "no_reset", []
    live = [a for a in parsed if _reset_epoch(a) > now.timestamp()]
    return ("ok", live) if live else ("dead", [])


def _age(state, now: datetime) -> tuple[float | None, float | None]:
    at = qw_schema.parse_epoch(getattr(state, "measured_at", None))
    return at, None if at is None else max(0.0, now.timestamp() - at)


def fresh_reading(read_quota, refresh, now: datetime) -> Reading:
    """S-23①～④：讀 → 判年齡／視窗 → 必要時補量一次 → 回 `Reading`。任何例外 ⇒ `reason=error`。"""
    try:
        state = (read_quota or default_read)(now)
        verdict, live = _classify(state, now)
        at, age = _age(state, now)
        old = verdict == "ok" and age is not None and age > qw_calc.stale_age_seconds()
        if verdict in ("unmeasured", "no_reset") or not (old or verdict == "dead"):
            return Reading(state if verdict == "ok" else None, at, age, False,
                           "" if verdict == "ok" else verdict, False)
        try:  # 補量一次
            new = (refresh or default_refresh)(now)
            verdict2, _ = _classify(new, now)
            at2, age2 = _age(new, now)
            if verdict2 == "ok":
                again = age2 is not None and age2 > qw_calc.stale_age_seconds()
                return Reading(new, at2, age2, again, "", True)
            return Reading(None, at, age, False,
                           "stale_window" if verdict2 == "dead" else verdict2, True)
        except Exception:  # noqa: BLE001 — 補量失敗＝外推或舊窗（呼叫端決定）
            if verdict == "dead":
                return Reading(None, at, age, False, "stale_window", False)
            return Reading(state, at, age, True, "", False)
    except Exception:  # noqa: BLE001 — fail-open：量不到
        return Reading(None, None, None, False, "error", False)


def extrapolate(r: float, age: float | None, burn: float) -> float:
    """補量失敗時保守外推：`R_eff＝max(0, R − ceil(age/60)·burn)`（只往收緊方向）。"""
    return max(0.0, r - math.ceil((age or 0) / 60) * burn)


# ───────────────────────────────────────────────────────────── wall_state
def _real_usage_after(path: Path, since: float) -> bool:
    """`since` 之後有任何主鏈、非 `<synthetic>`、帶 usage 的 assistant 記錄（＝續上了）。"""
    for rec in roster._records(path, tail=True):
        msg = rec.get("message")
        if (rec.get("isSidechain") or roster._usage(rec) is None
                or (isinstance(msg, dict) and msg.get("model") == "<synthetic>")):
            continue
        stamp = qw_schema.parse_epoch(rec.get("timestamp"))
        if stamp is not None and stamp > since:
            return True
    return False


def _synthetic_wall(path: Path) -> bool:
    """主鏈**最後一筆** assistant 記錄是 `<synthetic>` 且內文含限額字樣。"""
    for rec in reversed(list(roster._records(path, tail=True))):
        if rec.get("type") != "assistant" or rec.get("isSidechain"):
            continue
        msg = rec.get("message") if isinstance(rec.get("message"), dict) else {}
        if msg.get("model") != "<synthetic>":
            return False
        blocks = msg.get("content")
        text = " ".join(b.get("text", "") for b in blocks if isinstance(b, dict)) \
            if isinstance(blocks, list) else str(blocks or "")
        return _WALL_TEXT_RE.search(text) is not None
    return False


def _cutoff(path: Path, now: datetime) -> tuple[bool, float | None]:
    """①最後一筆切斷記錄之後無續接、無新真 usage ⇒ `(True, 切斷通知自報的下次續接 epoch｜None)`。"""
    sig = transcript_activity.usage_limit_signals(path)
    cut = qw_schema.parse_epoch(sig["cutoff_at"])
    if cut is None:
        return False, None
    resumed = qw_schema.parse_epoch(sig["reset_notice_at"])
    if (resumed is not None and resumed > cut) or _real_usage_after(path, cut):
        return False, None
    import quota_limits  # noqa: PLC0415

    when = quota_limits.parse_reset_at(sig["cutoff_text"],
                                       datetime.fromtimestamp(cut, now.tzinfo))
    return True, None if when is None else when.timestamp()


def _anchor_cold(path: Path) -> float | None:
    from . import keepwarm  # noqa: PLC0415 — Q2 起 keepwarm import quotawall

    at = keepwarm.anchor(path)
    return None if at is None else at + CACHE_LIFE_SEC


def wall_state(transcript, now: datetime, *, read_quota=None) -> dict:
    """§3：三條件任一即牆，回 `{wall, reset(epoch｜None), cold_at(epoch｜None), source}`。
    ①最後切斷後無續接無新 usage（`cut`）；②主鏈最後一筆 assistant 為 `<synthetic>` 限額記錄
    （`synthetic`）；③短窗讀數 ≥100 且 reset 在未來（`quota`）。例外一律「不是牆」（fail-open）。"""
    out = {"wall": False, "reset": None, "cold_at": None, "source": ""}
    path = Path(transcript) if transcript is not None else None
    try:
        reset = None
        if path is not None and path.is_file():
            hit, reset = _cutoff(path, now)
            src = CUT if hit else (SYNTHETIC if _synthetic_wall(path) else "")
            if src:
                return {"wall": True, "reset": reset or _quota_reset(read_quota, now),
                        "cold_at": _anchor_cold(path), "source": src}
        verdict, live = _classify((read_quota or default_read)(now), now)
        full = [a for a in live if a.pct >= 100]
        if verdict == "ok" and full:
            return {"wall": True, "reset": max(_reset_epoch(a) for a in full),
                    "cold_at": _anchor_cold(path) if path is not None and path.is_file() else None,
                    "source": QUOTA}
    except Exception:  # noqa: BLE001 — fail-open
        pass
    return out


def _quota_reset(read_quota, now: datetime) -> float | None:
    try:
        verdict, live = _classify((read_quota or default_read)(now), now)
        return max(_reset_epoch(a) for a in live) if verdict == "ok" else None
    except Exception:  # noqa: BLE001
        return None
