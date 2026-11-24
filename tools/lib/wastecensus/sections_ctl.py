"""換手與掌控量測 M-W1（修正）、M-C1～M-C6 與換手決策重放（Control_Handover DES §10、§7.6；W5）。

零 token、只讀、不接閘門 rc。全是純函式：輸入是已讀入的輕量記錄（`supervision_load`／`keep_load`
的形狀，加 `ctl_load` 供的交接包／park 標記／額度讀數），I/O 在 `ctl_load.py`。

🔴 判準函式即實作函式（REQ-CTL-42）：重放一律呼叫 `switchplan.decide`、`park.recovered`、
`costmodel.fresh_is_cheaper`、`control.sealed_effective` 的判準，本檔**不另寫第二份**判準；
差異只在「輸入怎麼從歷史逐字稿近似出來」，近似處都在函式 docstring 與輸出備註裡標明。
"""
from __future__ import annotations

import statistics
from collections import Counter
from datetime import datetime
from types import SimpleNamespace

import transcript_activity

from lib.sessionctl import cachestate, control, parkprobe, switch, switchplan

from . import supervision as sv
from .sections_keep import ctx as turn_ctx

FOLLOW_MIN = 30  # M-C4：提示（`switch_advise`）後這麼久之內出現 spawn 算「跟進」
REREAD_WINDOW_S = 3600  # M-C2：新 session 的「第一小時」
COLD_GAP_MIN = (cachestate.TTL_SECONDS["1h"] - cachestate.CACHE_MARGIN_SECONDS) / 60
_NO_WORK = frozenset(transcript_activity.READ_ONLY_TOOLS) | control.SUPERVISION_TOOLS
UPPER_BOUND = "上界（舊口徑：恆無憑證）"


# ───────────────────────────────────────────────────────── M-W1（修正）
def credential_intervals(recs: list[dict]) -> list[tuple[float, float, str]]:
    """逐字稿能還原的歷史憑證：Stop 出聲含「看管中」＝該刻 payload 憑證有效（`supervise` 只在憑證
    valid 時改這個字樣）。心跳／watchlock 的區間由 `ctl_load` 另供（它們不在逐字稿裡）。"""
    return [(r["t"] - sv.HOOK_MERGE_S, r["t"] + sv.HOOK_MERGE_S, "payload") for r in recs
            if r["type"] == "attachment" and r.get("hook_event") == "Stop"
            and "看管中" in r.get("content", "")]


def m_w1_dual(sessions: list[dict], extra: dict | None = None) -> dict:
    """修正版（讀真實憑證）與舊口徑（恆無憑證，只當**上界**）並行出數；兩者不相減（口徑不同）。
    `extra`＝`{sid: [(t0, t1, kind), …]}` 的心跳／watchlock 區間。"""
    spans = {s["sid"]: credential_intervals(s["recs"]) + list((extra or {}).get(s["sid"], []))
             for s in sessions}

    def covered(event: dict) -> bool:
        return any(a <= event["t"] <= b for a, b, _k in spans.get(event["sid"], ()))

    kinds = Counter(k for items in spans.values() for _a, _b, k in items)

    def over_30(cred) -> int:  # SA REQ-A1 的口徑：無看管且主控 >30 分沒回來
        return sum(1 for s in sessions for e in sv.stop_events(s["recs"])
                   if e["gap_s"] is not None and e["gap_s"] > 1800
                   and not cred(dict(e, sid=s["sid"])))

    return {"corrected": dict(sv.m_w1(sessions, covered), gt_30min=over_30(covered)),
            "upper_bound": dict(sv.m_w1(sessions), label=UPPER_BOUND,
                                gt_30min=over_30(lambda _e: False)),
            "credential_spans": dict(kinds)}


# ───────────────────────────────────────────────────────── M-C1（A4 回歸率）
def m_c1(trace: list[dict], judge) -> dict:
    """痕跡 `finalized_wake_block` 中、推回當下封存已失效（`judge(row)=="invalidated"`）者＝A4 病灶
    （修前 14 天基線 12 件）；`control_cold_wake_exempt`（冷叫醒閘因封存失效而放行）為分母事件。
    `regression`＝首筆 exempt 之後仍出現的病灶推回（目標 0）；尚無 exempt 事件 ⇒ `None`（機制還沒
    留痕，不是好消息）。"""
    blocks = [r for r in trace if r.get("event") == "finalized_wake_block"]
    exempt = [r for r in trace if r.get("event") == control.EV_COLD_WAKE_EXEMPT]
    bad = [r for r in blocks if judge(r) == control.SEAL_INVALIDATED]
    since = min((r["_at"] for r in exempt if r.get("_at") is not None), default=None)
    regress = (None if since is None else
               sum(1 for r in bad if r.get("_at") is not None and r["_at"] >= since))
    return {"blocks": len(blocks), "after_seal_work": len(bad), "exempt": len(exempt),
            "since_w1": since, "regression": regress, "target": 0,
            "note": sv.NO_DATA if not exempt else None}


# ───────────────────────────────────────────────────────── M-C2／M-C3／M-C4
def _reread_count(recs: list[dict], pattern) -> int:
    first = next((r for r in recs if sv.is_human(r)), None)
    if first is None:
        return 0
    return sum(1 for r in recs
               if r["type"] == "assistant" and r["t"] - first["t"] <= REREAD_WINDOW_S
               for text in r.get("reads", ()) if pattern.search(text))


def m_c2(sessions: list[dict], pattern) -> dict:
    """接續完整度：M-S2 手貼接續比率（基線 9／37＝24%，目標 ≤5%）與機器交接開場的新 session 第一
    小時回頭讀舊資料次數（基線中位 2.5、非零 18／26，目標中位 ≤1）。`pattern`＝舊資料路徑樣式。"""
    s2 = sv.m_s2(sessions)
    fresh = [s for s in sessions if s.get("interactive") and s["recs"]
             and sv.first_prompt_class(s["recs"]) == "machine_handoff_prompt"]
    counts = [_reread_count(s["recs"], pattern) for s in fresh]
    return {"pasted": s2["pasted"], "n_interactive": s2["n_interactive"],
            "paste_pct": round(100 * s2["pasted"] / s2["n_interactive"], 1)
            if s2["n_interactive"] else None,
            "machine_start": len(fresh),
            "reread_median": statistics.median(counts) if counts else None,
            "reread_nonzero": sum(1 for c in counts if c)}


def m_c3(trace: list[dict]) -> dict:
    """park 提前恢復：`park_early_recovered` 件數與 `saved_min` 合計；`park_early_probe` 的
    `unmeasured` 比率（量不到比率高＝探針沒有在工作）。"""
    rec = [r for r in trace if r.get("event") == control.EV_PARK_EARLY_RECOVERED]
    probe = [r for r in trace if r.get("event") == control.EV_PARK_EARLY_PROBE]
    miss = sum(1 for r in probe if r.get("reason") == parkprobe.REASON_UNMEASURED)
    return {"recovered": len(rec), "saved_min": round(sum(
        r["saved_min"] for r in rec if isinstance(r.get("saved_min"), (int, float))), 1),
        "probes": len(probe), "unmeasured": miss,
        "unmeasured_ratio": round(miss / len(probe), 3) if probe else None}


def trigger_sources(trace: list[dict], window_min: float = 360) -> dict:
    """每筆成功 spawn（`session_switch_spawned` ok）的觸發源：`forward`（同包有
    `forward_spawned`）、
    `seal_gate`（同 sid 近 `window_min` 內有 `seal_stop_block`）、`advise`（有 `switch_advise`）、
    `park`（列帶 park 路徑欄）、其餘 `manual`。判準只看痕跡，不看逐字稿。"""
    def near(row: dict, event: str) -> bool:
        return any(r.get("event") == event and r.get("sid") == row.get("sid")
                   and r.get("_at") is not None and row.get("_at") is not None
                   and 0 <= row["_at"] - r["_at"] <= window_min * 60 for r in trace)

    out: Counter = Counter()
    fwd = {r.get("handoff") for r in trace if r.get("event") == "forward_spawned"}
    spawned = (r for r in trace if r.get("event") == sv.EV_SESSION_SPAWNED and r.get("ok") is True)
    for row in spawned:
        kind = ("forward" if row.get("handoff") in fwd else "park" if row.get("route") else
                "seal_gate" if near(row, "seal_stop_block") else
                "advise" if near(row, control.EV_SWITCH_ADVISE) else "manual")
        out[kind] += 1
    return dict(out)


def m_c4(trace: list[dict]) -> dict:
    """換手判定分佈（`switch_plan`，按動作／原因計）＋提示跟進率（`switch_advise` 後 `FOLLOW_MIN`
    分內同 sid 出現 spawn 的比例）＋M-K6 觸發源。"""
    plans = [r for r in trace if r.get("event") == control.EV_SWITCH_PLAN]
    advise = [r for r in trace if r.get("event") == control.EV_SWITCH_ADVISE]
    spawns = [r for r in trace if r.get("event") == sv.EV_SESSION_SPAWNED and r.get("ok") is True]
    followed = sum(1 for a in advise if any(
        s.get("sid") == a.get("sid") and a.get("_at") is not None and s.get("_at") is not None
        and 0 <= s["_at"] - a["_at"] <= FOLLOW_MIN * 60 for s in spawns))
    return {"plans": len(plans),
            "by_action": dict(Counter(r.get("action") for r in plans)),
            "by_reason": dict(Counter(f"{r.get('action')}:{r.get('reason')}" for r in plans)),
            "advise": len(advise), "advise_followed": followed,
            "follow_pct": round(100 * followed / len(advise), 1) if advise else None,
            "triggers": trigger_sources(trace)}


# ───────────────────────────────────────────────────────── 歷史重放的輸入近似（母體 → Inputs）
def sealed_state(sid: str, at: float, packs: list[dict], turns: list[dict]) -> str:
    """`at` 時刻本 sid 的封存四值（`control.sealed_effective` 判準，近似輸入）：取 `sealed_at ≤ at`
    最新的包；戳之後到 `at` 的回合若有非唯讀、非監督工具名 ⇒ `invalidated`。母體只存工具名、沒有
    指令內容，故 Bash／PowerShell 一律算「工作」（偏保守＝多判失效）。無包 ⇒ `none`。"""
    stamps = [p["sealed_at"] for p in packs
              if p["sid"] == sid and p.get("sealed_at") is not None and p["sealed_at"] <= at]
    if not stamps:
        return control.SEAL_NONE
    since = max(stamps)
    worked = any(since < t["ts_first"] <= at and any(n not in _NO_WORK for n in t["tools"])
                 for t in turns if t["ts_first"])
    return control.SEAL_INVALIDATED if worked else control.SEAL_EFFECTIVE


def _spans(subs: list[dict]) -> dict[str, list[tuple[float, float]]]:
    out: dict[str, list[tuple[float, float]]] = {}
    for sub in subs:
        stamps = [t["ts_first"] for t in sub["turns"] if t["ts_first"]]
        ends = [t["ts_last"] or t["ts_first"] for t in sub["turns"] if t["ts_first"]]
        if stamps:
            out.setdefault(sub["sid"], []).append((min(stamps), max(ends)))
    return out


def _agents_at(spans: dict, sid: str, at: float) -> int:
    return sum(1 for a, b in spans.get(sid, ()) if a <= at <= b)


def _decide(env, **kw):
    return switchplan.decide(switchplan.Inputs(env=env, mode="auto", **kw))


def cold_returns(mains: list[dict]) -> list[dict]:
    """閒置 ≥ 快取壽命（1 小時減餘裕）後的回來：`{sid, at, ctx（回來前）, gap}`。"""
    rows = []
    for main in mains:
        turns = [t for t in main["turns"] if t["ts_first"]]
        for prev, cur in zip(turns, turns[1:]):
            gap = (cur["ts_first"] - (prev["ts_last"] or prev["ts_first"])) / 60
            if gap >= COLD_GAP_MIN and turn_ctx(prev) > 0:
                rows.append({"sid": main["sid"], "at": cur["ts_first"], "ctx": turn_ctx(prev),
                             "gap": gap})
    return rows


def m_c5(pop: dict, env=None) -> dict:
    """F′：冷回、F4 判換新、但當時封存無效（無載具＝TH-5）的件數（基線 8／14 天）。判準＝
    `switchplan.decide` 的 `cold_unsealed` 列。"""
    packs = (pop.get("ctl") or {}).get("packs", [])
    by_sid = {m["sid"]: m["turns"] for m in pop["main"]}
    cold = cold_returns(pop["main"])
    f4 = unsealed = 0
    for row in cold:
        state = sealed_state(row["sid"], row["at"], packs, by_sid[row["sid"]])
        got = _decide(env, ctx=row["ctx"], cache="cold", sealed=state)
        f4 += got.reason.startswith(("cold_fresh", "cold_unsealed"))
        unsealed += got.reason == "cold_unsealed"
    return {"cold_returns": len(cold), "f4_fresh": f4, "f_prime": unsealed}


def m_c6(sessions: list[dict]) -> dict:
    """無人窗口 session 中子代理被終止件數（`<status>killed</status>` 的任務通知；互動不計；
    只讀既有逐字稿；目標 0，觀察口徑，不接閘門）。"""
    hits = [s["sid"] for s in sessions if not s.get("interactive") for r in s["recs"]
            if r["type"] == "user" and r.get("ok") == "task-notification"
            and "<status>killed</status>" in r.get("text", "")]
    return {"killed": len(hits), "sessions": len(set(hits)), "target": 0}


def ctl_metrics(sessions: list[dict], trace: list[dict], pattern, judge, extra=None) -> dict:
    """`--supervision-metrics` 併出的一組：M-W1 修正（並行上界）、M-C1、M-C6、M-C2。"""
    return {"m_w1": m_w1_dual(sessions, extra), "m_c1": m_c1(trace, judge),
            "m_c2": m_c2(sessions, pattern), "m_c6": m_c6(sessions)}


def switch_ctl_metrics(pop: dict, trace: list[dict], env=None) -> dict:
    """`--switch-metrics` 併出的一組：M-C3、M-C4（含 M-K6 觸發源）、M-C5。"""
    return {"m_c3": m_c3(trace), "m_c4": m_c4(trace), "m_c5": m_c5(pop, env)}


# ───────────────────────────────────────────────────────── --replay-plan（DES §7.6 同形表）
def _dt(at: float) -> datetime:
    return datetime.fromtimestamp(at).astimezone()


def _burn_state(rows: list[dict], at: float):
    """`at` 之前最近一筆 `quota_burn` 讀數（≤1 小時內）→ 假 `QuotaState`（axes＋account_key）；
    沒有 ⇒ `None`。`fp` 內 `account=<指紋>` 是帳號鍵（同組織換使用者可能漏看，DES §7.6 限制③）。"""
    best = None
    for row in rows:
        stamp = _stamp(row)
        if stamp is not None and stamp <= at and at - stamp <= 3600 and (
                best is None or stamp > best[0]):
            best = (stamp, row)
    if best is None:
        return None
    row = best[1]
    axes = tuple(SimpleNamespace(kind=k, pct=v, resets_at=(row.get("resets_at") or {}).get(k))
                 for k, v in (row.get("pct") or {}).items())
    key = next((str(x).split("=", 1)[1] for x in row.get("fp") or ()
                if str(x).startswith("account=")), None)
    return SimpleNamespace(axes=axes, account_key=key)


def _stamp(row: dict) -> float | None:
    try:
        return datetime.fromisoformat(str(row.get("ts"))).timestamp()
    except ValueError:
        return None


def replay_park_early(parks: list[dict], burn: list[dict], policy, grid_min: float = 15) -> dict:
    """每個 park 標記在 `parked_at ＋ n×格點` 上以 `park.recovered`（經 `parkprobe.evaluate`）重放；
    基準＝登記當下最近一筆讀數（舊標記沒有 `parked_pct`，重放時由 `quota_burn` 補）。
    提前量 `saved_min` 是**下界**（`quota_burn` 讀數可能晚於額度實際恢復）。"""
    hits = []
    for marker in parks:
        try:
            parked = datetime.fromisoformat(str(marker["parked_at"])).timestamp()
            fire = datetime.fromisoformat(str(marker["fire_at"])).timestamp()
        except (KeyError, ValueError):
            continue
        base = _burn_state(burn, parked)
        pct0 = parkprobe.reading(base) if base is not None else None
        if pct0 is None:
            continue
        seeded = dict(marker, **{parkprobe.MK_PARKED_PCT: pct0,
                                 parkprobe.MK_PARKED_ACCOUNT: base.account_key})
        at = parked + grid_min * 60
        while at < fire - parkprobe.EARLY_MIN_WAIT_MIN * 60:
            state = _burn_state(burn, at)
            verdict = (parkprobe.evaluate(seeded, state, policy, _dt(at))
                       if state is not None else {})
            if verdict.get("recovered"):
                hits.append({"sid": marker.get("sid"), "at": _dt(at).isoformat(),
                             "saved_min_ge": round((fire - at) / 60, 1),
                             "account_changed": parkprobe.account_changed(
                                 seeded, getattr(state, "account_key", None))})
                break
            at += grid_min * 60
    return {"markers": len(parks), "hits": hits}


def replay_plan(pop: dict, *, env=None, policy=None) -> dict:
    """近 N 天母體的決策重放（DES §7.6 同形表）。每列 `{name, hits, note}`；原始分項在 `detail`。"""
    ctl, mains = pop.get("ctl") or {}, pop["main"]
    hard = switch.threshold(switch.HARD_CTX_KEY, env)[0]
    r2 = switch.threshold(switch.R2_KEY, env)[0]
    spans, packs = _spans(pop["sub"]), ctl.get("packs", [])
    h_rows, r2_rows = [], []
    for main in mains:
        turns = [t for t in main["turns"] if t["ts_first"]]
        first = next((t for t in turns if turn_ctx(t) >= hard), None)
        if first is not None:
            n = _agents_at(spans, main["sid"], first["ts_first"])
            got = _decide(env, ctx=turn_ctx(first), hard=hard, agents=n)
            h_rows.append({"sid": main["sid"], "agents": n, "action": got.action})
        k = len(main.get("compactions") or [])
        if k >= r2 and turns:
            got = _decide(env, ctx=turn_ctx(turns[-1]), hard=None, compactions=k, r2=r2)
            r2_rows.append({"sid": main["sid"], "k": k, "action": got.action,
                            "prefer_fresh": got.flags.prefer_fresh})
    cold = m_c5(pop, env)
    gaps = _takeover_gaps(packs)
    debounced = [g for g in gaps if _decide(env, ctx=hard, hard=hard, since_takeover_min=g
                                            ).reason == "debounce"]
    park = replay_park_early(ctl.get("parks", []), ctl.get("burn", []),
                             policy or SimpleNamespace(prepare_pct=_prepare_pct(env)))
    drain = sum(1 for r in h_rows if r["action"] == switchplan.Action.SWITCH_AFTER_DRAIN)
    rows = [
        {"name": "H：ctx ≥ 硬線", "hits": len(h_rows),
         "note": f"其中 {drain} 個當下有在飛代理 ⇒ SWITCH_AFTER_DRAIN；"
                 f"{len(h_rows) - drain} 個 ⇒ SWITCH_NOW"},
        {"name": f"R2：壓縮 ≥ {r2}", "hits": len(r2_rows),
         "note": f"只設 prefer_fresh、無推回：{sum(1 for r in r2_rows if r['prefer_fresh'] and r['action'] == switchplan.Action.STAY)}"},  # noqa: E501
        {"name": "冷回（閒置 ≥ 快取壽命後有新 assistant）", "hits": cold["cold_returns"],
         "note": f"其中 F4 判換新 {cold['f4_fresh']}；無封存載具（F′）{cold['f_prime']}"},
        {"name": "D：防抖（接手後 30 分內又要換）", "hits": len(debounced),
         "note": f"包鏈接手→下一封存間隔 {len(gaps)} 筆，最短 "
                 f"{f'{min(gaps):.1f} 分' if gaps else '無'}"},
        {"name": "park 提前恢復", "hits": len(park["hits"]),
         "note": f"{park['markers']} 個標記中；提前量為下界："
                 + "；".join(f"{h['sid'][:8]}≥{h['saved_min_ge']} 分"
                             f"{'（換帳號）' if h['account_changed'] else ''}"
                             for h in park["hits"])},
    ]
    return {"rows": rows, "detail": {"h": h_rows, "r2": r2_rows, "cold": cold, "park": park,
                                      "debounce_gaps": gaps}}


def _takeover_gaps(packs: list[dict]) -> list[float]:
    """包鏈「接手（`.ack`）→ 接手者自己下一次封存」的間隔分鐘（只取非負、兩端皆有時刻者）。"""
    gaps = []
    for first in packs:
        if first.get("acker") is None or first.get("acked_at") is None:
            continue
        for second in packs:
            if second["sid"] == first["acker"] and second.get("sealed_at") is not None \
                    and second["sealed_at"] >= first["acked_at"]:
                gaps.append(round((second["sealed_at"] - first["acked_at"]) / 60, 1))
    return sorted(gaps)


def _prepare_pct(env) -> float:
    try:
        import quota_policy  # noqa: PLC0415 — lazy

        return float(quota_policy.load_policy(env if env is not None else {})[0].prepare_pct)
    except Exception:  # noqa: BLE001 — 讀不到 ⇒ 用出廠準備門檻
        return 85.0
