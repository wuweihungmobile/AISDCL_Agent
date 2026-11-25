"""單一權威額度判決（QVD §3；PRD §4.1.6 R-4.1.6-1～8）——純函式＋判決行。

停工、park、續跑、等重置、可派數五類決定全部由 `ruling()` 一次算出，輸出唯一動作
（`CONTINUE｜NODISPATCH｜WAIT_RESET｜PARK｜HALT_WEEKLY`）與一行 `QUOTA_VERDICT=`。
本檔不讀檔、不讀環境、不讀牆鐘（`now`／`env` 全經參數）；只 import `quota_policy`
（扁平共用單檔，QVD §8：扁平消費端與 SelfImproving 都需要一個不屬任何套件的判決家）。
取數住 `sessionctl/ruling_io.py`；消費端改接表與白名單見 QVD §3.5。
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from datetime import datetime, timedelta

import quota_policy

CONTINUE, NODISPATCH, WAIT_RESET, PARK, HALT_WEEKLY = (
    "CONTINUE", "NODISPATCH", "WAIT_RESET", "PARK", "HALT_WEEKLY")
ACTIONS = (CONTINUE, NODISPATCH, WAIT_RESET, PARK, HALT_WEEKLY)
PREFIX = "QUOTA_VERDICT="
DEG_UNMEASURED = "unmeasured"
#: 與 `quota_gate.QUOTA_CACHE_TTL_SECONDS` 同值（本檔不得 import hub；parity 由 QV 測試釘住）。
TTL_SECONDS = 180
#: QVD §3.2：`QV_WAIT_RESET_MIN` 是保溫分鐘數的**別名**（同一個數、不另設鍵）。
WAIT_RESET_KEY = "AUTOSDD_KEEPWARM_MINUTES"
SHORT_KINDS = frozenset({"session", "five_hour", "5h"})
SHORT_MINUTES, WEEK_MINUTES = 300.0, 10080.0
WEEKLY_KINDS = frozenset({"seven_day", "weekly_all"})
#: 模式非 auto／保溫關閉時 WAIT_RESET 沒有程式載具：理由句照實寫（QVD §3.6 第三列）。
NO_CARRIER_NOTE = "人已關閉自動換手／保溫：本視窗不會在重置後自動叫醒"
BILLING = ("subscription_only", "credits_fallback", "api_key", "unknown")


@dataclass(frozen=True)
class Ruling:
    action: str
    acct: str | None
    win: str | None          # 短窗 reset（ISO，帶 offset）
    wk: str | None           # 週 reset（ISO）
    cap: int
    measured_at: str | None
    expires_at: str
    vid: str
    mdl: str
    degraded: bool
    band: str
    reason: str
    billing: str = "unknown"
    voided: int = 0

    def line(self) -> str:
        return line(self)

    def expired(self, now: datetime) -> bool:
        return expired({"expires_at": self.expires_at}, now)


def _aware(text) -> datetime | None:
    if text is None or text == "":
        return None
    try:
        when = datetime.fromisoformat(str(text).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return when if when.tzinfo is not None else None


def _iso(when: datetime | None, now: datetime) -> str | None:
    return None if when is None else when.astimezone(now.tzinfo).isoformat(timespec="seconds")


def _real(pct) -> bool:
    return type(pct) in (int, float) and math.isfinite(pct)


def wait_reset_min(env) -> float:
    """`QV_WAIT_RESET_MIN`＝`AUTOSDD_KEEPWARM_MINUTES`（同一宣告的範圍；壞值退出廠值）。"""
    import quota_policy_env  # noqa: PLC0415 — quota_policy 的宣告表（同一個家）

    spec = next(s for s in quota_policy_env.ENV_SPEC if s.name == WAIT_RESET_KEY)
    try:
        value = float(str((env or {}).get(WAIT_RESET_KEY, "")).strip() or spec.default)
    except ValueError:
        return float(spec.default)
    if not math.isfinite(value) or not spec.lo <= value <= spec.hi:
        return float(spec.default)
    return value


def classify(state, now: datetime) -> dict:
    """軸分類：`spend`（保險軸）／`short`／`weekly`；只收 reset 未過（或無 reset 的保險軸）者。"""
    axes = tuple(getattr(state, "axes", ()) or ())
    wins = quota_policy.W.windows(tuple((a.kind, a.resets_at) for a in axes))
    out = {"spend": [], "short": [], "weekly": []}
    for axis, win in zip(axes, wins):
        if not _real(axis.pct):
            continue
        reset = _aware(axis.resets_at)
        if axis.kind in quota_policy.FALLBACK_KINDS:
            out["spend"].append(axis)
        elif reset is None or reset <= now:
            continue
        elif axis.kind in quota_policy.MODEL_SCOPED_KINDS or axis.kind in WEEKLY_KINDS \
                or win == WEEK_MINUTES:
            out["weekly"].append(axis)
        elif axis.kind in SHORT_KINDS or win == SHORT_MINUTES:
            out["short"].append(axis)
    return out


def _model_weekly(axis, model) -> bool:
    """第 2 列只看與 `model` 相關的週軸（F-06；同 DEF-200-436「只擋指名模型」）。"""
    if axis.kind not in quota_policy.MODEL_SCOPED_KINDS:
        return True
    return quota_policy._model_active(axis, model)  # noqa: SLF001 — 同一判準，不寫第二份


def _marker_rows(markers, acct, now: datetime) -> tuple[list, list]:
    """同帳號（或舊格式無帳號欄）且 reset 未過的 halt 標記，分（週軸, 短窗）兩組 reset 時刻。"""
    weekly, short = [], []
    for m in markers or ():
        if not isinstance(m, dict):
            continue
        owner = m.get("account")
        if owner and acct and owner != acct:
            continue  # 帳號不符＝交 §7 作廢流程，不當輸入
        reset = _aware(m.get("reset_at"))
        if reset is None or reset <= now:
            continue
        kind = str(m.get("binding") or "")
        is_weekly = kind in quota_policy.MODEL_SCOPED_KINDS or kind in WEEKLY_KINDS or \
            quota_policy.W.window_minutes(kind) == WEEK_MINUTES
        (weekly if is_weekly else short).append(reset)
    return weekly, short


def _retry_seconds(raw, now: datetime) -> float:
    if raw in (None, ""):
        return 0.0
    try:
        return max(0.0, float(str(raw).strip()))
    except ValueError:
        when = _aware(raw)
        return 0.0 if when is None else max(0.0, (when - now).total_seconds())


def _three_way(win: datetime | None, now: datetime, wait_min: float) -> str:
    """第 3／5 列共用：reset 量不到 ⇒ NODISPATCH；D ≤ 等待上限 ⇒ WAIT_RESET；否則 PARK。"""
    if win is None:
        return NODISPATCH
    return WAIT_RESET if (win - now).total_seconds() / 60.0 <= wait_min else PARK


def ruling(state, decision, *, model, policy, now: datetime, markers=(), plan=None,
           next_est: float | None = None, wait_min: float = 45.0, ttl: int = TTL_SECONDS,
           billing: str = "unknown", voided: int = 0, no_carrier: bool = False) -> Ruling:
    """QVD §3.2 決策表（由上而下第一個命中即短路）。`decision`＝`quota_gate.dispatch_decision()`
    的輸出（cap 唯一來源）；`plan`＝`qw_plan.Plan`（只經第 3～5 列影響動作，從不影響 cap）。"""
    acct = getattr(state, "account_key", None) or None
    usable = bool(getattr(state, "axes", ())) and state.usable()
    axes = classify(state, now)
    m_week, m_short = _marker_rows(markers, acct, now)
    stage = getattr(plan, "stage", None)
    plan_reset = getattr(plan, "reset", None)
    plan_win = None if plan_reset is None else datetime.fromtimestamp(plan_reset, now.tzinfo)
    shorts = [_aware(a.resets_at) for a in axes["short"]]
    win_any = max(shorts) if shorts else plan_win
    wk_hits = [a for a in axes["weekly"]
               if a.pct >= policy.halt_pct and _model_weekly(a, model)]
    s_hits = [a for a in axes["short"] if a.pct >= policy.prepare_pct]
    win, wk, why = win_any, None, ""
    if any(a.pct >= 100 for a in axes["spend"]):
        action, why = HALT_WEEKLY, "月度支出上限：沒有 reset 可等"
    elif wk_hits or m_week:
        resets = [_aware(a.resets_at) for a in wk_hits] + m_week
        action, wk = HALT_WEEKLY, max(resets)
        why = "週額度已達停止門檻（或同帳號週軸 halt 標記未過期）：等週重置"
    elif s_hits or m_short or stage in ("close", "wall"):
        win = (max(_aware(a.resets_at) for a in s_hits) if s_hits
               else max(m_short) if m_short else plan_win)
        action = _three_way(win, now, wait_min)
        top = max((a.pct for a in s_hits), default=None)
        src = (f"短窗 {top:.0f}%" if top is not None else
               "同帳號短窗 halt 標記未過期" if m_short else f"額度牆 stage={stage}")
        why = _short_reason(action, src, win, now, wait_min)
    elif stage == "nodispatch":
        action, why = NODISPATCH, "額度牆 stage=nodispatch：在飛照跑、不派新"
    elif (next_est is not None and getattr(plan, "r", None) is not None
          and getattr(plan, "v", None) is not None and next_est >= plan.r - plan.v):
        action = _three_way(win_any, now, wait_min)
        why = _short_reason(action, f"下一棒估 {next_est:g}pp ≥ R−V={plan.r - plan.v:.1f}pp",
                            win_any, now, wait_min)
    else:
        action = CONTINUE
        why = ("量不到額度讀數：照降級上限續跑（不是鎖死）" if not usable else "額度足夠：照常續跑")
    if action == WAIT_RESET and no_carrier:
        why += f"；{NO_CARRIER_NOTE}"
    degraded = action == CONTINUE and not usable
    cap = 0
    if action == CONTINUE:
        cap = decision.cap if decision.cap is not None else policy.max_fanout
    measured = getattr(state, "measured_at", None) if usable else None
    m_at = _aware(measured)
    if usable and m_at is not None:
        ends = [m_at + timedelta(seconds=ttl)] + ([win_any] if win_any is not None else [])
        expires = min(ends)
    else:
        retry = _retry_seconds(getattr(state, "retry_after", None), now)
        expires = now + timedelta(seconds=max(ttl, retry))
    if voided:
        why += f"；已作廢 {voided} 個舊帳號標記"
    fam = quota_policy.family_key(model) or "none"
    fields = (action, (acct or "none")[:12], _iso(win, now) or "none", _iso(wk, now) or "none",
              str(cap), _iso(m_at, now) or "none", fam, DEG_UNMEASURED if degraded else "")
    vid = hashlib.sha256("|".join(fields).encode("utf-8")).hexdigest()[:8]
    return Ruling(action, acct, _iso(win, now), _iso(wk, now), int(cap), _iso(m_at, now),
                  _iso(expires, now), vid, fam, degraded,
                  str(getattr(decision, "band", "") or ""), why, billing, voided)


def _short_reason(action: str, src: str, win, now: datetime, wait_min: float) -> str:
    if action == NODISPATCH:
        return f"{src}，但短窗 reset 時刻量不到：不派新、不 park（park 對量不到 reset 一律拒絕）"
    mins = int(max(0.0, (win - now).total_seconds()) // 60)
    if action == WAIT_RESET:
        return f"{src}、{mins} 分後重置（≤ {wait_min:g} 分）：保溫等重置，不 park"
    return f"{src}、{mins} 分後才重置（> {wait_min:g} 分）：封存後 park"


def head(r: Ruling) -> str:
    """判決行（前八欄＝PRD R-4.1.6-2 字面；`mdl=`／`deg=` 為尾端附加欄）。"""
    text = (f"{PREFIX}{r.action} acct={(r.acct or 'none')[:12]} win={r.win or 'none'} "
            f"wk={r.wk or 'none'} cap={r.cap} measured_at={r.measured_at or 'none'} "
            f"expires_at={r.expires_at} vid={r.vid} mdl={r.mdl}")
    return text + (f" deg={DEG_UNMEASURED}" if r.degraded else "")


def line(r: Ruling) -> str:
    """判決行＋第二行白話理由。"""
    return f"{head(r)}\n  {r.reason}"


def parse(text: str) -> dict | None:
    """從任意文字取**最後一個**判決行的欄位（以鍵取值，不以位置）；沒有 ⇒ None。"""
    found = None
    for raw in str(text or "").splitlines():
        pos = raw.find(PREFIX)
        if pos < 0:
            continue
        parts = raw[pos + len(PREFIX):].split()
        if not parts or parts[0] not in ACTIONS:
            continue
        fields = {"action": parts[0]}
        for part in parts[1:]:
            key, sep, value = part.partition("=")
            if sep:
                fields[key] = value
        found = fields
    return found


def expired(fields: dict | None, now: datetime) -> bool:
    """過期（或缺 `expires_at`）一律視為過期：消費端須重算，不據以行動（QVD §4）。"""
    when = _aware((fields or {}).get("expires_at"))
    return when is None or when <= now


def as_json(r: Ruling) -> dict:
    """`--json` 形狀（判決行欄位＋`band`／`reason`／`billing`）。"""
    return {"line": head(r), "action": r.action, "acct": r.acct, "win": r.win, "wk": r.wk,
            "cap": r.cap, "measured_at": r.measured_at, "expires_at": r.expires_at,
            "vid": r.vid, "mdl": r.mdl, "deg": DEG_UNMEASURED if r.degraded else None,
            "band": r.band, "reason": r.reason, "billing": r.billing, "voided": r.voided}


def block_message(r: Ruling, tool: str) -> str:
    """派工閘（C1）擋展開型派工的訊息：附判決行，致動器只此一處（QVD §3.5 C1／C2）。"""
    return (f"🔴 額度判決 {r.action}：`{tool}` 這類展開型派工本次不執行（在飛照跑）。\n"
            f"{line(r)}\n"
            "   收斂型工作（讀檔／寫檔／跑測試）照常；判決過期後下一次工具呼叫自動重算。\n")


def brief_line(r: Ruling | None) -> str:
    """SessionStart 簡報的額度行（C10）：判決行在前、理由在後；取不到判決照實說。"""
    if r is None:
        return "額度判決：取不到（判決取數失敗；派工前跑 `python tools/sessionctl.py quota`）"
    return f"額度判決：{head(r)}（{r.reason}）"


def billing_from_posture(posture) -> str:
    """計費姿態四值（QVD §3.3；`quota_messages.posture_line()` 同一推導）。欄位缺或形狀不對 ⇒
    `unknown`；API key 模式 ⇒ `api_key`；無 credits 或 credits 不可用 ⇒ `subscription_only`。"""
    if not isinstance(posture, dict) or "credits_present" not in posture:
        return "unknown"
    if str(posture.get("source") or posture.get("auth") or "").lower() in ("api_key", "apikey"):
        return "api_key"
    if posture.get("credits_present") and posture.get("fallback_available"):
        return "credits_fallback"
    return "subscription_only"


__all__ = ["Ruling", "ruling", "line", "head", "parse", "expired", "as_json", "brief_line",
           "billing_from_posture", "classify", "wait_reset_min", "ACTIONS", "CONTINUE",
           "NODISPATCH", "WAIT_RESET", "PARK", "HALT_WEEKLY", "PREFIX", "NO_CARRIER_NOTE"]
