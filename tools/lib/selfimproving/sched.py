"""SelfImproving 排程模型：日曆格折疊、七種跳過的純判準、`status.schedule`（TCS-SelfImproving-P4
R142～R145、R158）。

能力類別 `ro`：只讀事件與 git 狀態、不寫、不 import `runner`／`schedwrite`；時間一律由呼叫端注入
（`now` 須帶 offset，缺＝`ValueError`），不讀系統時鐘。外部查詢（OS 任務、額度、對話時刻、`claude`
路徑）一律以參數注入，測試不碰真機。
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from shutil import which as _which

from lib import transcript_activity

from . import events as si_events
from . import fold as si_fold
from . import transcript as si_transcript
from .git import Git

ARMED_TASK = "AutoSDD_SI_Patrol"
NE_PREFIX = "NOT-EVALUABLE："
EXPORT_ARMED = NE_PREFIX + "export-reads-no-home"
SOP_REL = "docs/05_development/SelfImproving_Operations_SOP.md"
OBS_LEDGER_PREFIX = "docs/06_quality/SelfImproving_Observation_Ledger"
_OWN_PREFIXES = (si_events.LEDGER_REL, si_events.PROPOSALS_REL + "/", OBS_LEDGER_PREFIX)
_PS_QUERY = (f"$t = Get-ScheduledTask -TaskName '{ARMED_TASK}' -ErrorAction SilentlyContinue; "
             "if (-not $t) { 'ABSENT'; exit 0 }; $i = $t | Get-ScheduledTaskInfo; "
             "if ($i.NextRunTime) { $i.NextRunTime.ToString('o') } else { 'NONEXT' }")
_ENV_KEYS = ("PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME", "USERPROFILE")
_HM_RE = re.compile(r"^(\d\d):(\d\d)$")


def aware(now: datetime) -> datetime:
    """`now` 須帶 offset（鐵律三）；naive＝`ValueError`（CLI 為 rc 3）。"""
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now 須為帶 offset 的 datetime")
    return now


def _t(text: str) -> datetime:
    return datetime.fromisoformat(text)


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def line1(text, limit: int = 120) -> str:
    """單行、≤120 code point、非空（換行改空白、超長截斷）；供 `sched.skip.detail`。"""
    out = " ".join(str(text).split())[:limit].strip()
    return out or "-"


# ── 折疊（R142）──────────────────────────────────────────────────────────────
def walk(events: list[dict], default_period: int) -> list[tuple[dict, bool, int, bool]]:
    """依序走 `sched.set`：回 [(事件, enabled, period, 是否重置事件)]。重置＝false（或尚無設定）轉
    true，或 enabled 為 true 而週期與前一筆生效值不同（D-QA-6）；值不變的重送不重置。"""
    out, enabled, period = [], False, default_period
    for e in events:
        if e.get("kind") != "sched.set":
            continue
        en, per = e["enabled"], e["period_minutes"]
        out.append((e, en, per, en and (not enabled or per != period)))
        enabled, period = en, per
    return out


@dataclass
class State:
    enabled: bool
    period: int
    last_set: dict | None
    origin: dict | None  # 最近一次重置事件

    @property
    def origin_dt(self) -> datetime | None:
        return _t(self.origin["t"]) if self.origin else None


def state_of(events: list[dict], default_period: int, before_seq: int | None = None) -> State:
    """折疊出（可選：某 seq 之前的）排程狀態。"""
    pool = [e for e in events if before_seq is None or e["seq"] < before_seq]
    steps = walk(pool, default_period)
    if not steps:
        return State(False, default_period, None, None)
    resets = [e for e, _, _, r in steps if r]
    return State(steps[-1][1], steps[-1][2], steps[-1][0], resets[-1] if resets else None)


def cell_bounds(state: State, now: datetime) -> tuple[datetime, datetime] | None:
    """`now` 所在格 [起, 終)；停用、無 origin、`now` 早於 origin（時鐘倒退）＝None。"""
    origin = state.origin_dt
    if not state.enabled or origin is None or aware(now) < origin:
        return None
    step = timedelta(minutes=state.period)
    k = (now - origin) // step
    return origin + k * step, origin + (k + 1) * step


def _in(ev: dict, cell: tuple[datetime, datetime]) -> bool:
    return cell[0] <= _t(ev["t"]) < cell[1]


def cell_events(events: list[dict], kind: str, cell, *, trigger: str | None = None) -> list[dict]:
    return [e for e in events if e.get("kind") == kind and _in(e, cell)
            and (trigger is None or e.get("trigger") == trigger)]


def schedule_obj(events: list[dict] | None, params: dict, now: datetime, *, armed=None) -> dict:
    """R158 的 `schedule` 物件（鍵序固定）；`events` 為 None＝事件帳本不在場（量不到，非停用）。"""
    now = aware(now)
    hb = params["sched_heartbeat_minutes"]
    default = params["sched_period_minutes_default"]
    seen = [e for e in events or [] if _t(e["t"]) <= now]  # 折疊只看 now 當下已發生的事件
    backwards = bool(events) and not any(e["kind"] == "sched.set" for e in seen) and any(
        e["kind"] == "sched.set" for e in events)  # 第一筆設定都在 now 之後＝時鐘倒退（R142 (d)）
    st = state_of(events if backwards else seen, default)
    cell = None if events is None or backwards else cell_bounds(st, now)
    ls = st.last_set
    ran = skip = overdue = None
    if events is None or backwards:
        pass
    elif not st.enabled:
        overdue = False
    elif cell is not None:
        ran = bool(cell_events(events, "run.open", cell, trigger="f"))
        skips = cell_events(events, "sched.skip", cell)
        skip = skips[-1] if skips else None
        overdue = not ran and skip is None and now - cell[0] > timedelta(minutes=2 * hb)
    return {
        "enabled": st.enabled, "period_minutes": st.period,
        "period_min": params["sched_period_minutes_min"],
        "period_max": params["sched_period_minutes_max"], "heartbeat_minutes": hb,
        "last_set": {"at": ls["t"], "by": ls["by"], "carrier": ls["carrier"]} if ls else None,
        "cell_start": iso(cell[0]) if cell else None, "cell_end": iso(cell[1]) if cell else None,
        "ran_this_cell": ran,
        "last_skip": ({"at": skip["t"], "reason": skip["reason"], "detail": skip["detail"]}
                      if skip else None),
        "overdue": overdue,
        "armed": armed if armed is not None else {
            "task": ARMED_TASK, "present": None, "credential": NE_PREFIX + "not-queried"},
    }


# ── 跳過（R143、R144）──────────────────────────────────────────────────────────
@dataclass
class Inputs:
    """七項跳過條件的注入值（預設皆不成立）；`details` 以原因名為鍵，供事件 `detail`。"""

    enabled: bool = True
    blackout: bool = False
    quota_skip: bool = False
    other_driver: bool = False
    dirty: bool = False
    run_open: bool = False
    spawn_problem: str | None = None
    details: dict | None = None


def decide_skip(inp: Inputs) -> str | None:
    """判序固定 disabled→blackout→quota-band→other-driver→dirty-tree→run-open→spawn-failed。"""
    order = ((not inp.enabled, "disabled"), (inp.blackout, "blackout"),
             (inp.quota_skip, "quota-band"), (inp.other_driver, "other-driver"),
             (inp.dirty, "dirty-tree"), (inp.run_open, "run-open"),
             (inp.spawn_problem is not None, "spawn-failed"))
    return next((name for hit, name in order if hit), None)


def skip_plan(events: list[dict], now: datetime, reason: str, detail: str,
              params: dict) -> dict | None:
    """要追加的 `sched.skip`（不含 seq／t）或 None：同一格同一 reason 只寫一筆（去重鍵＝格＋reason，
    只看非 Console 載體）；停用或無格＝None（不嘗試）。"""
    st = state_of(events, params["sched_period_minutes_default"])
    cell = cell_bounds(st, now)
    if cell is None:
        return None
    dup = [e for e in cell_events(events, "sched.skip", cell)
           if e.get("reason") == reason and "carrier" not in e]
    if dup:
        return None
    return {"kind": "sched.skip", "by": "patrol", "due_at": iso(cell[0]), "reason": reason,
            "detail": line1(detail)}


def attempt_plan(events: list[dict], now: datetime, inp: Inputs, params: dict) -> dict | None:
    """到期嘗試的寫入計畫：停用不嘗試；原因成立＝回 skip 事件（已記過回 None）；皆不成立＝None。"""
    st = state_of(events, params["sched_period_minutes_default"])
    if not st.enabled:
        return None
    reason = decide_skip(inp)
    if reason is None:
        return None
    return skip_plan(events, now, reason, (inp.details or {}).get(reason, reason), params)


def local_hm(now: datetime) -> str:
    """R143 (b) 唯一的本機時分來源（測試換成替身）：`now.astimezone()` 的 `HH:MM`。"""
    local = now.astimezone()
    return f"{local.hour:02d}:{local.minute:02d}"


def _minutes(hm: str) -> int:
    m = _HM_RE.match(hm)
    return int(m.group(1)) * 60 + int(m.group(2))


def blackout_hit(hm: str, ranges: list[str]) -> bool:
    """黑窗：起點含、終點不含、起＞迄＝跨午夜、多區間聯集、空清單＝無黑窗。"""
    cur = _minutes(hm)
    for rng in ranges:
        lo, hi = (_minutes(x) for x in rng.split("-"))
        if (lo <= cur < hi) if lo < hi else (cur >= lo or cur < hi):
            return True
    return False


def in_blackout(now: datetime, params: dict) -> bool:
    return blackout_hit(local_hm(now), params["sched_blackout_local"])


def quota_verdict(state) -> dict:
    """額度帶判讀：準備、停止、量不到（及任何不認得的帶）跳過（fail-closed）；注意與收斂照跑但降載。"""
    band = getattr(state, "band", None)
    return {"skip": band not in ("free", "notice", "converge"),
            "degrade": band in ("notice", "converge")}


def measured_state(now: datetime, read=None, refresh=None):
    """額度快取的「讀，量不到就補量一次再讀」唯一入口（TCS-P4 D-IMP-11）。無人操作時快取必過期
    （只有互動視窗 statusLine 刷新、TTL 180 秒），只讀會讓無人運轉永遠判 `unmeasured`；補量＝
    `quota_gate.refresh_quota_blocking()`（HTTP 一次、零 token、fail-soft）。已有軸不補量；補量
    失敗或仍無軸＝回無軸狀態，由 `decide` 照舊判 `unmeasured`（fail-closed）。`read`／`refresh`
    為注入縫。"""
    if read is None or refresh is None:
        from lib import quota_gate  # 延遲：只有真讀額度才載入

        read = quota_gate.read_quota if read is None else read
        refresh = quota_gate.refresh_quota_blocking if refresh is None else refresh
    state = read(now)
    if not state.axes and refresh():
        state = read(now)
    return state


def quota_check(now: datetime, read=None) -> dict:
    """`quota_gate.read_quota(now)` 的帶判讀（`read` 為注入縫，回帶 `.band` 的物件）；讀取或判讀
    的任何例外＝fail-closed（跳過）。預設以 `quota_policy.DEFAULT_POLICY` 取帶。"""
    try:
        if read is not None:
            return quota_verdict(read(now))
        from lib import quota_policy  # 延遲：只有真讀額度才載入

        state = measured_state(now)
        return quota_verdict(quota_policy.decide(state, now, quota_policy.DEFAULT_POLICY))
    except Exception:  # noqa: BLE001  # 量不到＝跳過（fail-closed），不當機
        return {"skip": True, "degrade": False}


def other_driver(repo: Path, now: datetime, params: dict) -> bool:
    """逐字稿目錄最近 `sched_driver_quiet_minutes` 內有**對話記錄**（記錄時間戳，不是 mtime）；
    嚴格小於才成立；目錄不存在、無對話記錄＝False。"""
    folder = si_transcript.transcript_dir(repo)
    try:
        paths = sorted(folder.glob("*.jsonl"))
    except OSError:
        return False
    newest = transcript_activity.newest_conversation_at(paths)
    return newest is not None and aware(now).timestamp() - newest < params[
        "sched_driver_quiet_minutes"] * 60


def dirty_paths(repo: Path) -> list[str]:
    """`git status --porcelain`（含未追蹤）除 SI 自有路徑（事件帳本、OBS 帳本、提案目錄）外的條目；
    改名兩端皆判；git 不可用＝以哨兵條目回傳（fail-closed 視為髒）。"""
    cp = Git(repo).run("-c", "core.quotepath=false", "status", "--porcelain", "-z",
                       "--untracked-files=all")
    if cp is None or cp.returncode != 0:
        return ["<git-unavailable>"]
    toks, out, i = cp.stdout.split("\0"), [], 0
    while i < len(toks):
        tok = toks[i]
        i += 1
        if len(tok) < 4:
            continue
        paths = [tok[3:]]
        if tok[0] in "RC" or tok[1] in "RC":
            paths.append(toks[i] if i < len(toks) else "")
            i += 1
        out += [p for p in paths if p and not p.startswith(_OWN_PREFIXES)]
    return out


def open_runs(events: list[dict], exclude: str | None = None) -> list[str]:
    """本運轉以外的未關運轉（任何 trigger）。"""
    f = si_fold.fold(events)
    return [r.id for r in f.runs.values() if r.closed_seq is None and r.id != exclude]


def spawn_problem(repo: Path, *, which=None, preflight=None, template_problems=None) -> str | None:
    """R143 (g)：預檢字串、claude 不在 PATH、SOP 範本結構判準不過；全正常回 None。"""
    if preflight is None:
        from lib import resume_route  # 延遲：只有真預檢才載入

        preflight = resume_route.preflight_problem
    why = preflight()
    if why:
        return f"preflight:{why}"
    if (which or _which)("claude") is None:
        return "claude-not-found"
    if template_problems is None:
        try:
            from . import patrolbrief
        except ImportError:
            return "sop-template:PATROLBRIEF-UNAVAILABLE"
        template_problems = patrolbrief.template_problems
    try:
        text = (repo / SOP_REL).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        text = ""
    probs = template_problems(text)
    return f"sop-template:{probs[0]}" if probs else None


def armed_value(run_argv, *, argv: list[str] | None = None) -> dict:
    """OS 任務的現查（R158）：憑證是 NextRunTime 這個**值**，不是 rc。`run_argv(argv, env=,
    timeout=, cwd=)` 由呼叫端注入（回含 `rc`、`out`、`timed_out`）；查詢失敗＝present null 並帶
    NOT-EVALUABLE 碼。預設只支援 Windows；其他平台由呼叫端傳入 `argv`（macOS 住 `schedarm`）。"""
    if argv is None:
        if not sys.platform.startswith("win"):
            return {"task": ARMED_TASK, "present": None,
                    "credential": NE_PREFIX + "platform-unsupported"}
        argv = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _PS_QUERY]
    env = {k: os.environ[k] for k in _ENV_KEYS if k in os.environ}
    try:
        res = run_argv(argv, env=env, timeout=20, cwd=None)
    except Exception as exc:  # noqa: BLE001  # 現查失敗一律量不到、不當機
        return {"task": ARMED_TASK, "present": None,
                "credential": NE_PREFIX + type(exc).__name__}
    text = (getattr(res, "out", "") or "").strip()
    if getattr(res, "timed_out", False) or getattr(res, "rc", 1) != 0 or not text:
        return {"task": ARMED_TASK, "present": None, "credential": NE_PREFIX + (
            "timeout" if getattr(res, "timed_out", False) else f"rc-{getattr(res, 'rc', '?')}")}
    value = text.splitlines()[-1].strip()
    if value == "ABSENT":
        return {"task": ARMED_TASK, "present": False, "credential": "-"}
    return {"task": ARMED_TASK, "present": True,
            "credential": NE_PREFIX + "no-next-run-time" if value == "NONEXT" else value}
