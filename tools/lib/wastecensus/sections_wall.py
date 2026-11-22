"""額度牆續航量測：M-K7／M-K8／M-K9 與 `--calibrate-quotawall` 的判準（R218 Q5）。

設計 QuotaWall_CacheContinuity_Design §15、S-3／S-4／S-15；TCS-QuotaWall REQ-QW-50～53。
全是純函式（輸入皆已讀入的 list／dict，不碰家目錄、不寫任何檔）；讀檔與印出在 `keep_load.py`。
- M-K7：撞牆後回來的冷重寫（主控兩筆真 usage 之間有牆，且後一筆 cache_creation ≥ 0.5×
  前一筆上下文）；`sections_keep.idle_gaps` 以 `wall_between` 標記同一批間隔，M-K1 不再
  重複計（MU-QW-11）。
- M-K8：每個 keepwarm 保溫 run 的 chain／single 次數、跨重置是否保住快取（reset 後首筆
  cache_read ≥ 0.9× 上下文）、省下加權單位（2c − Σp）、備援觸發／讓路、牆前無觸發、靜音 Stop。
- M-K9：park 到點結局普查（fired／skipped／failed 依原因）＋「宣稱已排程但未續上」。
- 校準：只印三鍵建議值，不寫回任何設定檔（S-4）；任一鍵的量測區間 < `MIN_INTERVALS`
  ⇒ 未校準。

🔴 誠實劃界：keepwarm 痕跡目前沒有 `mode`／`reset` 欄。run 的 chain／single 由「終結前有無
付費 ping」推得；(sid, reset) 的 reset 取 run 帶的欄位（若有）、否則同 sid 最近的 `park_armed`
／`keepwarm_early_reset`、再否則空。舊資料的 park 失敗沒有終態痕跡，原因由 oldwin 痕跡（同
sid、job 開始後 5 分鐘內的 close_refused／close_failed）對應。事件名只有
`session_switch_spawning` 來自 `qw_schema`（其餘是字面，兩邊相等由
`test_waste_census_wall.py` 斷言，REQ-SS-21 同款）。
"""
from __future__ import annotations

import math
import re

from lib.sessionctl import qw_calc, qw_schema

from .annotate import units
from .pace_metrics import hour_key, short_samples
from .reader import W_CC1

EV_KW_VERDICT, EV_KW_PING_COST = "keepwarm_verdict", "keepwarm_ping_cost"
EV_KW_EARLY_RESET = "keepwarm_early_reset"
EV_ARMED, EV_CANCELLED, EV_DONE = "park_armed", "park_cancelled", "park_done"
EV_JOB_START, EV_ROUTE = "park_job_start", "park_route"
EV_RESUMED, EV_SPAWNED = "park_resumed", "park_spawned"
EV_RESUME_FAILED, EV_SPAWN_FAILED = "park_resume_failed", "park_spawn_failed"
EV_SKIPPED, EV_YIELD = "handoff_spawn_skipped", "park_yield_primary"
EV_CHAIN_FAILED, EV_STOP_BLOCK = "park_chain_failed", "park_stop_block"
EV_STOP_MUTED, EV_SPAWNED_SWITCH = "quotawall_stop_muted", "session_switch_spawned"
#: close_degraded 之後流程會繼續，所以不算失敗原因。
OLDWIN_FAIL_EVENTS = ("oldwin_close_refused", "oldwin_close_failed")

CUT_MARK = "continuing automatically at"
WALL_TEXT_RE = re.compile(r"hit your|usage limit", re.IGNORECASE)  # 同 sessionctl/qw_wall
MIN_CC_FRAC = 0.5      # M-K7：後一筆 cache_creation ≥ 這個比例 × 前一筆上下文
CROSS_HIT = 0.9        # M-K8：reset 後首筆 cache_read ≥ 這個比例 × 前一筆上下文
NOT_RESUMED_MIN = 30   # M-K9：reset 後這麼久內該 sid 與其 fork／FRESH 皆無 assistant 記錄
WALL_LOOKBACK_H = 6    # 牆前這麼久（略大於一個五小時窗）內沒有任何觸發 ⇒ 無觸發
WALL_DEDUP_MIN = 10    # 同 sid 十分鐘內的連續牆記錄算同一面牆
JOB_WINDOW_S = 3600    # park job 結局的搜尋窗上限（下一次同 sid job 開始即截斷）
OLDWIN_WINDOW_S = 300  # 舊資料失敗原因：job 開始後這麼久內的 oldwin 失敗痕跡
OLDWIN_SLACK_S = 5     # oldwin 時間戳只到秒（會比同一秒內的 job 開始早）；容許這麼久的回溯
INTERVAL_DT_MIN, INTERVAL_DT_MAX = 1.0, 20.0  # 燒速取樣：相鄰樣本間隔（分）
LEGACY_READ_S = 180.0  # 舊資料：ping 後這麼久內的第一筆 Stop 讀數視為 ping 後讀數
PING_PAIR_MAX_S = 3 * 3600.0
AGENT_TAIL_TURNS = 4   # 在飛代理收尾預估：該代理最後幾回合的加權單位
MIN_INTERVALS = 8      # REQ-QW-52：量測區間不足 ⇒ 未校準
KEY_PP, KEY_BURN, KEY_AGENT = qw_calc.KEY_PP, qw_calc.KEY_BURN, qw_calc.KEY_AGENT
_PING_VERDICTS = ("ping", "resume", "cap", "handed_over")


def _ctx(turn: dict) -> int:
    return turn["inp"] + turn["cc"] + turn["cr"]


def _at(row: dict) -> float | None:
    return qw_schema.parse_epoch(row.get("at"))


def _pick(values: list[float], frac: float) -> float | None:
    """nearest-rank 分位數（決定性；空 ⇒ None）。"""
    ordered = sorted(values)
    if not ordered:
        return None
    return ordered[min(len(ordered) - 1, max(0, math.ceil(frac * len(ordered)) - 1))]


def _turns(main: dict | None) -> list[dict]:
    return [t for t in (main or {"turns": []})["turns"] if t["ts_first"]]


# ─────────────────────────────────────────────────────────────── 牆標記（M-K7）
def wall_between(walls, start: float | None, end: float | None) -> bool:
    """`walls`（`[{ts, kind}]`）中有任何一筆落在 [start, end]。"""
    if start is None or end is None:
        return False
    return any(start <= w["ts"] <= end for w in walls or ())


def wall_events(main: dict) -> list[float]:
    """同 sid 相鄰 `WALL_DEDUP_MIN` 分鐘內的牆記錄合併成一面牆，回各面牆的第一筆時刻。"""
    out: list[float] = []
    for ts in sorted(w["ts"] for w in main.get("walls") or ()):
        if not out or ts - out[-1] > WALL_DEDUP_MIN * 60:
            out.append(ts)
    return out


def m_k7(mains: list[dict]) -> dict:
    """額度牆冷重寫：主控相鄰兩筆真 usage 之間有牆，且後一筆 `cc ≥ 0.5×` 前一筆上下文。"""
    hits = []
    for main in mains:
        turns = _turns(main)
        for prev, cur in zip(turns, turns[1:]):
            end = prev["ts_last"] or prev["ts_first"]
            if (wall_between(main.get("walls"), end, cur["ts_first"])
                    and _ctx(prev) > 0 and cur["cc"] >= MIN_CC_FRAC * _ctx(prev)):
                hits.append({"sid": main["sid"][:8], "ctx": _ctx(prev), "cc": cur["cc"],
                             "gap_min": round((cur["ts_first"] - end) / 60, 1)})
    return {"count": len(hits), "tokens": sum(h["cc"] for h in hits),
            "units": sum(W_CC1 * h["cc"] for h in hits), "hits": hits}


# ─────────────────────────────────────────────────────────────── M-K8
def _norm_reset(raw) -> str | None:
    """reset 取整到整點（伺服器在 :59:59.9／:00:00.1 之間抖動）後的 ISO；解不出 ⇒ None。"""
    key = hour_key(raw) if raw else None
    return None if key is None else qw_schema.iso(key)


def _reset_for(sid: str, at: float, traces: list[dict]) -> str | None:
    """run 的 reset：同 sid、不晚於 `at` 的最近一筆 park_armed／keepwarm_early_reset 帶的值。"""
    best = None
    for row in traces:
        event = row.get("event")
        if row.get("sid") != sid or event not in (EV_ARMED, EV_KW_EARLY_RESET):
            continue
        when = _at(row)
        raw = row.get("reset_at") if event == EV_ARMED else row.get("reset")
        if when is not None and when <= at and raw and (best is None or when > best[0]):
            best = (when, raw)
    return _norm_reset(best[1]) if best else None


def kw_runs(traces: list[dict]) -> tuple[list[dict], list[dict]]:
    """keepwarm 保溫 run：同 sid 的 `ping` 累積，遇 `resume`／`cap`／`handed_over` 終結。
    `skip` 不是 run（沒有掛上）。回 `(已終結 runs, 尚未終結且有 ping 的 runs)`。"""
    stamped = [(_at(r), r) for r in traces if r.get("event") == EV_KW_VERDICT]
    runs, live = [], {}
    for at, row in sorted((x for x in stamped if x[0] is not None), key=lambda x: x[0]):
        sid = str(row.get("sid") or "")
        cur = live.setdefault(sid, {"sid": sid, "pings": [], "mode": None, "reset": None})
        cur["mode"] = row.get("mode") if row.get("mode") in qw_schema.MODES else cur["mode"]
        cur["reset"] = row.get("reset") or cur["reset"]
        verdict = row.get("verdict")
        if verdict == "ping":
            cur["pings"].append((at, row))
        elif verdict in ("resume", "cap", "handed_over"):
            cur.update(end=verdict, end_at=at)
            live.pop(sid)
            if verdict != "cap" or cur["pings"]:  # 無 ping 的 cap＝上限已記過（真資料 12 秒重複）
                runs.append(cur)
    return runs, [r for r in live.values() if r["pings"]]


def _mode_of(run: dict) -> str:
    if run["end"] == "resume":
        return run["mode"] or ("chain" if run["pings"] else "single")
    return "periodic" if run["end"] == "cap" else run["end"]


def _cross(run: dict, by_sid: dict) -> tuple[bool | None, float | None, int | None]:
    """`resume` 後的跨重置結果：`(成功?, hit, 該回合前上下文)`；量不到 ⇒ `(None, None, None)`。"""
    turns = _turns(by_sid.get(run["sid"]))
    prev = [t for t in turns if t["ts_first"] < run["end_at"]]
    after = [t for t in turns if t["ts_first"] >= run["end_at"]]
    if not prev or not after or _ctx(prev[-1]) <= 0:
        return None, None, None
    hit = after[0]["cr"] / _ctx(prev[-1])
    return hit >= CROSS_HIT, round(hit, 3), _ctx(prev[-1])


def _triggered(sid: str, wall: float, traces: list[dict]) -> bool:
    lo = wall - WALL_LOOKBACK_H * 3600
    for row in traces:
        event, at = row.get("event"), _at(row)
        if row.get("sid") != sid or at is None or not lo <= at <= wall:
            continue
        if event in (EV_ARMED, EV_JOB_START):
            return True
        if event == EV_KW_VERDICT and row.get("verdict") != "skip":
            return True
    return False


def _job_window(job: dict, jobs: list[dict]) -> tuple[float, float]:
    start = _at(job) or 0.0
    later = [x for x in (_at(j) for j in jobs if j.get("sid") == job.get("sid")) if x and x > start]
    return start, min(later) if later else start + JOB_WINDOW_S


def _job_has_yield(job: dict, jobs: list[dict], yields: list[dict]) -> bool:
    lo, hi = _job_window(job, jobs)
    return any(y.get("sid") == job.get("sid") and lo <= (_at(y) or -1) < hi for y in yields)


def _run_row(run: dict, by_sid: dict, traces: list[dict]) -> dict:
    mode, ok, hit, ctx0 = _mode_of(run), None, None, None
    if run["end"] == "resume":
        ok, hit, ctx0 = _cross(run, by_sid)
    cost = sum(qw_calc.p_of(r.get("ctx") or ctx0) for _a, r in run["pings"])
    gain = W_CC1 * ctx0 - cost if ok and ctx0 else None
    reset = _norm_reset(run["reset"]) or _reset_for(run["sid"], run["end_at"], traces)
    return {"sid": run["sid"][:8], "reset": reset, "mode": mode, "pings": len(run["pings"]),
            "end": run["end"], "cross_ok": ok, "hit": hit, "saved": gain}


def m_k8(mains: list[dict], traces: list[dict]) -> dict:
    """保溫成效。`saved`＝跨重置成功的 run 以 `2c − Σp` 計（c＝reset 前上下文、p＝一次 ping）。"""
    by_sid = {m["sid"]: m for m in mains}
    runs, open_runs = kw_runs(traces)
    rows = [_run_row(run, by_sid, traces) for run in runs]
    count = lambda name: sum(1 for r in rows if r["mode"] == name)  # noqa: E731
    jobs = [r for r in traces if r.get("event") == EV_JOB_START]
    yields = [r for r in traces if r.get("event") == EV_YIELD]
    walls = [(m["sid"], w) for m in mains for w in wall_events(m)]
    return {"runs": rows, "windows": len({(r["sid"], r["reset"]) for r in rows}),
            "chain": count("chain"), "single": count("single"), "periodic": count("periodic"),
            "handed_over": count("handed_over"), "open": len(open_runs),
            "cross_ok": sum(1 for r in rows if r["cross_ok"] is True),
            "cross_fail": sum(1 for r in rows if r["cross_ok"] is False),
            "cross_unknown": sum(1 for r in rows
                                 if r["mode"] in ("chain", "single") and r["cross_ok"] is None),
            "saved_units": sum(r["saved"] or 0.0 for r in rows), "yield": len(yields),
            "fired": sum(1 for j in jobs if not _job_has_yield(j, jobs, yields)),
            "walls": len(walls),
            "no_trigger_walls": sum(1 for sid, w in walls if not _triggered(sid, w, traces)),
            "stop_muted": sum(1 for r in traces if r.get("event") == EV_STOP_MUTED)}


# ─────────────────────────────────────────────────────────────── M-K9
def _oldwin_reasons(sid: str, start: float, oldwin: list[dict]) -> list[str]:
    out = set()
    for row in oldwin:
        at = _at(row)
        if (row.get("event") in OLDWIN_FAIL_EVENTS and sid in (row.get("old"), row.get("new"))
                and at is not None and start - OLDWIN_SLACK_S <= at <= start + OLDWIN_WINDOW_S
                and row.get("reason")):
            out.add(str(row["reason"]))
    return sorted(out)


def _job_outcome(job: dict, rows: list[dict], oldwin: list[dict]) -> tuple[str, list[str]]:
    """`(fired|skipped|failed|unresolved, 原因們)`；先看確定終態，最後才看「到過選路卻無終態」。"""
    sid, start = job.get("sid"), _at(job) or 0.0

    def by(*names):
        return [r for r in rows if r.get("event") in names]

    if any(r.get("rc") in (0, None) for r in by(EV_RESUMED, EV_SPAWNED)):
        return "fired", []
    chain = by(EV_CHAIN_FAILED)
    if chain:
        reasons = {str(a.get("reason")) for r in chain for a in r.get("attempts") or ()
                   if isinstance(a, dict) and a.get("reason")}
        return "failed", sorted(reasons) or ["chain_failed"]
    failed = by(EV_RESUME_FAILED, EV_SPAWN_FAILED) or [
        r for r in rows if qw_schema.is_failure_row(r)]
    if failed:
        first = failed[0]
        label = f"rc={first['rc']}" if "rc" in first else "spawn_failed"
        return "failed", _oldwin_reasons(sid, start, oldwin) or [label]
    if by(EV_SKIPPED):
        return "skipped", sorted({str(r.get("reason") or "unknown") for r in by(EV_SKIPPED)})
    if by(EV_YIELD):
        return "skipped", ["yield_primary"]
    if by(EV_ROUTE):  # 舊資料：到過選路、之後沒有任何終態痕跡（22:42 事件的形狀）
        return "failed", _oldwin_reasons(sid, start, oldwin) or ["no_terminal"]
    return "unresolved", []


def _kin(sid: str, born: float, traces: list[dict]) -> set[str]:
    """原 sid 與它 armed 之後 spawn 出的 fork／FRESH 新 sid。"""
    kin = {sid}
    for row in traces:
        if (row.get("event") == EV_SPAWNED_SWITCH and row.get("sid") == sid
                and (_at(row) or 0) >= born):
            kin.update(str(n).removesuffix(".jsonl") for n in row.get("new_transcripts") or ())
            if row.get("new_sid"):
                kin.add(str(row["new_sid"]))
    return kin


def _not_resumed(mains: list[dict], traces: list[dict], now: float) -> dict:
    """「宣稱已排程但未續上」：armed 後 reset＋30 分內，原 sid 與其 fork／FRESH 皆無
    assistant 記錄。逐字稿母體沒有該 sid（太舊）⇒ 不判；已撤銷／標完成 ⇒ 不算；
    reset＋30 分未到 ⇒ 待判。"""
    by_sid = {m["sid"]: m for m in mains}
    lost, judged, pending = [], 0, 0
    for armed in (r for r in traces if r.get("event") == EV_ARMED):
        sid, born = armed.get("sid"), _at(armed)
        reset = qw_schema.parse_epoch(armed.get("reset_at"))
        if born is None or reset is None or sid not in by_sid:
            continue
        end = reset + NOT_RESUMED_MIN * 60
        if any(r.get("event") in (EV_CANCELLED, EV_DONE) and r.get("sid") == sid
               and born <= (_at(r) or -1) <= end for r in traces):
            continue
        if end > now:
            pending += 1
            continue
        judged += 1
        turns = [t for s in _kin(sid, born, traces) for t in _turns(by_sid.get(s))]
        if not any(reset <= t["ts_first"] <= end for t in turns):
            lost.append({"sid": sid[:8], "armed_at": armed.get("at"),
                         "reset_at": armed.get("reset_at")})
    return {"count": len(lost), "judged": judged, "pending": pending, "items": lost}


def m_k9(traces: list[dict], oldwin: list[dict], mains: list[dict], now: float) -> dict:
    """park 到點結局普查：job 開始後同 sid 的終態痕跡（不靠 job 標籤，才對得上舊資料）。"""
    jobs = sorted((r for r in traces if r.get("event") == EV_JOB_START),
                  key=lambda r: _at(r) or 0.0)
    fired, unresolved, skipped, failed = 0, 0, {}, []
    for job in jobs:
        lo, hi = _job_window(job, jobs)
        rows = [r for r in traces if r.get("sid") == job.get("sid") and lo <= (_at(r) or -1) < hi]
        kind, reasons = _job_outcome(job, rows, oldwin)
        if kind == "fired":
            fired += 1
        elif kind == "skipped":
            for reason in reasons:
                skipped[reason] = skipped.get(reason, 0) + 1
        elif kind == "failed":
            failed.append({"sid": str(job.get("sid"))[:8], "at": job.get("at"),
                           "reasons": reasons})
        else:
            unresolved += 1
    by_reason: dict[str, int] = {}
    for item in failed:
        for reason in item["reasons"]:
            by_reason[reason] = by_reason.get(reason, 0) + 1
    return {"jobs": len(jobs), "fired": fired, "skipped": dict(sorted(skipped.items())),
            "failed": {"count": len(failed), "reasons": dict(sorted(by_reason.items())),
                       "items": failed},
            "unresolved": unresolved, "not_resumed": _not_resumed(mains, traces, now)}


# ─────────────────────────────────────────────────────────────── 校準
def _after_reading(sid: str, at: float, traces: list[dict]) -> tuple[float, float | None] | None:
    """`at` 後 `LEGACY_READ_S` 內同 sid 的第一筆 Stop 讀數 `(pct, reset 取整時刻)`。"""
    best = None
    for row in traces:
        when = _at(row)
        if (row.get("event") != EV_STOP_BLOCK or row.get("sid") != sid or when is None
                or not at < when <= at + LEGACY_READ_S or row.get("kind") not in (
                    "session", "five_hour") or type(row.get("pct")) not in (int, float)):
            continue
        if best is None or when < best[0]:
            best = (when, float(row["pct"]), hour_key(row.get("reset_at")))
    return None if best is None else (best[1], best[2])


def _new_intervals(traces: list[dict], pings: dict) -> tuple[list, dict]:
    """新資料：`keepwarm_ping_cost` 的 Δ，ctx 取同 sid 不晚於它 60 秒的最近一筆 ping 判決。"""
    out, cost_at = [], {}
    for row in traces:
        at = _at(row)
        if row.get("event") != EV_KW_PING_COST or at is None:
            continue
        sid = str(row.get("sid"))
        cands = [r for a, r in pings.get(sid, ()) if a <= at + 60 and r.get("verdict") == "ping"]
        delta, ctx = row.get("delta"), (cands[-1].get("ctx") if cands else None)
        if type(delta) in (int, float) and delta >= 0 and type(ctx) is int and ctx > 0:
            out.append((float(delta), ctx))
            cost_at.setdefault(sid, []).append(at)
    return out, cost_at


def _ping_intervals(traces: list[dict]) -> tuple[list[tuple[float, int]], dict]:
    """量測區間 `[(Δpp, ctx)]`：新資料取 `keepwarm_ping_cost`；舊資料取相鄰兩次 ping 後的第一筆
    Stop 讀數差（同 run、同視窗、Δ ≥ 0）。同一次 ping 兩種來源都有時只計新資料。"""
    pings: dict[str, list[tuple[float, dict]]] = {}
    stamped = [(_at(r), r) for r in traces if r.get("event") == EV_KW_VERDICT]
    for at, row in sorted((x for x in stamped if x[0] is not None), key=lambda x: x[0]):
        if row.get("verdict") in _PING_VERDICTS:
            pings.setdefault(str(row.get("sid")), []).append((at, row))
    intervals, cost_at = _new_intervals(traces, pings)
    legacy = 0
    for sid, series in pings.items():
        for (a0, r0), (a1, r1) in zip(series, series[1:]):
            if r0.get("verdict") != "ping" or r1.get("verdict") != "ping":
                continue
            if a1 - a0 > PING_PAIR_MAX_S or any(abs(c - a1) <= 120 for c in cost_at.get(sid, ())):
                continue
            p0, p1 = _after_reading(sid, a0, traces), _after_reading(sid, a1, traces)
            ctx = r0.get("ctx")
            if p0 and p1 and p0[1] == p1[1] and p1[0] >= p0[0] and type(ctx) is int and ctx > 0:
                intervals.append((p1[0] - p0[0], ctx))
                legacy += 1
    return intervals, {"ping_cost": len(intervals) - legacy, "legacy_readings": legacy}


def _burn_rates(burn: list[dict]) -> list[float]:
    rates = []
    windows, _skipped = short_samples(burn)
    for samples in windows.values():
        ordered = sorted(samples)
        for (t0, p0), (t1, p1) in zip(ordered, ordered[1:]):
            minutes = (t1 - t0) / 60.0
            if INTERVAL_DT_MIN <= minutes <= INTERVAL_DT_MAX and p1 > p0:
                rates.append((p1 - p0) / minutes)
    return rates


def _key_row(n: int, rec: float | None, short: str) -> dict:
    return {"n": n, "rec": rec, "reason": "" if rec is not None else short}


def calibrate_quotawall(pop: dict, traces: list[dict], burn: list[dict]) -> dict:
    """三鍵建議值（S-3／S-4／S-15）。每鍵 `{n, rec, reason}`：`n` 為量測區間數，
    < `MIN_INTERVALS` ⇒ `rec=None`（未校準）。
    PP：Σ(Δpp) ÷ Σ(p(c)/1000)（比值之和：整數讀數量化下比逐筆平均穩）；
    BURN：活躍區間（讀數上升）pp／分的 p75；
    AGENT：在飛代理最後 `AGENT_TAIL_TURNS` 回合加權單位 ÷1000 × PP 建議值的 p75（需 PP 先有值）。"""
    intervals, sources = _ping_intervals(traces)
    kunits = sum(qw_calc.p_of(c) / 1000.0 for _d, c in intervals)
    total = sum(d for d, _c in intervals)
    pp_rec, why = None, f"區間 n={len(intervals)} < {MIN_INTERVALS}"
    if len(intervals) >= MIN_INTERVALS:
        why = "Δ 合計為 0（讀數量化吞掉成本）"
        pp_rec = total / kunits if total > 0 and kunits > 0 else None
    pp = {**_key_row(len(intervals), pp_rec, why), "sources": sources, "sum_delta": total}
    rates = _burn_rates(burn)
    burn_rec = _pick(rates, 0.75) if len(rates) >= MIN_INTERVALS else None
    bn = _key_row(len(rates), burn_rec, f"區間 n={len(rates)} < {MIN_INTERVALS}")
    tails = [sum(units(t) for t in _turns(sub)[-AGENT_TAIL_TURNS:]) / 1000.0
             for sub in pop.get("sub", ()) if len(_turns(sub)) >= AGENT_TAIL_TURNS]
    if pp_rec is None:
        ag = _key_row(len(tails), None, "PP_PER_KUNIT 尚無建議值（單位換算不成立）")
    else:
        agent_rec = _pick(tails, 0.75) * pp_rec if len(tails) >= MIN_INTERVALS else None
        ag = _key_row(len(tails), agent_rec, f"區間 n={len(tails)} < {MIN_INTERVALS}")
    return {"min_n": MIN_INTERVALS, "pp": pp, "burn": bn, "agent": ag}


def switch_wall_metrics(pop: dict, traces: list[dict], oldwin: list[dict], now: float) -> dict:
    return {"m_k7": m_k7(pop["main"]), "m_k8": m_k8(pop["main"], traces),
            "m_k9": m_k9(traces, oldwin, pop["main"], now)}
