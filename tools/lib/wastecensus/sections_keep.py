"""換 session 成本模型的量測與重放（R216 WP-G；設計 SessionSwitch_CostModel_Design §2／§3.2／§7）。

三個入口共用同一份「母體」（population，純 JSON 可序列化）：
- `--switch-metrics`：M-K1～M-K6（目標達成與否的指標；量測探針，不接閘門 rc）＋額度牆的
  M-K7～M-K9（判準在 `sections_wall.py`，R218 Q5）；
- `--replay-switch`：把新判準套回真實逐字稿，重現設計 §7 全表（P1 保溫／P3 額度續跑 F4／
  P4b 邊界軟線掃描／S1 冷續棒／S2 分段等待）；
- `--calibrate-switch`：由逐字稿與 `autosdd_resume_cost.jsonl` 重算 F、B、N_lo、P_fix 建議值。
本檔只有純函式（輸入皆已讀入的 list／dict，不碰家目錄）；讀檔在 `keep_load.py`。

母體形狀：`{"main": [{sid, handoff_start, turns, compactions, kw_calls}], "sub": [{sid, turns,
kw_calls}]}`；`turns` 的每筆只留 ts_first／ts_last／inp／cc／cr／out／cc5／cc1／cause／tools。
🔴 誠實劃界：加權單位是公開價格比的推估（見 reader 檔頭）；P_fix 是推估值，M-K5 上線後以實測回寫；
P4b 是「每 session 只換一次」的下界模型，且 11-14 後的 session 已被舊 R1 截斷（倖存者偏差），
故只用 `P4B_CUT` 之前的 session。軟線 `T_soft` 依掌舵者裁決（D-1＝③）不實作，P4b 僅作史料對照。
"""
from __future__ import annotations

import statistics
import time

from . import sections_wall as sw
from .annotate import units
from .reader import W_CC1, W_CC5, W_CR

#: 痕跡事件名（字面同 sessionctl 的 keepwarm／longwait／watch／handoff 常數；wastecensus 不 import
#: 守衛碼，兩邊相等由 `test_waste_census_keep.py` 斷言，REQ-SS-21）。
EV_KEEPWARM_VERDICT = "keepwarm_verdict"
EV_KEEPWARM_STOP_BLOCK = "keepwarm_stop_block"
EV_WATCH_QUOTA_LATCHED = "watch_quota_latched"
EV_LONGWAIT_BLOCK = "longwait_block"
EV_SESSION_SPAWNED = "session_switch_spawned"

KEEPABLE = frozenset({"human", "task_notification", "peer_handback", "other_user"})
HANDOFF_WORDS = ("交接包", "handoff", "handback")
IDLE_MIN_MIN = 55  # 主控閒置 ≥ 此分鐘數才算「閒置間隔」（1h TTL 前約 5 分鐘）
IDLE_COMPACT_LO, IDLE_COMPACT_HI = 50, 60  # M-K2 觀測窗（設計 §1.4-1：實測 54.6～56.5 分）
REWRITE_MIN_PREV_CTX = 30_000
HARD_COMPACT_BELOW = 0.6  # 上下文掉到前一回合的這個比例以下＝壓縮／重置，之後不再算（P4b）
P4B_CUT = "2026-11-14"  # 舊 R1 截斷前後的分界（本機時區）
P4B_THRESHOLDS = (250_000, 300_000, 350_000, 400_000, 450_000, 500_000, 600_000, 700_000)
PING_TURNS, PING_FIXED, PING_GROWTH = 2, 4500, 1500  # P_fix 推估（設計 §3.2）
SUB_POLL_MIN, SUB_POLL_FIXED = 4, 1500  # 子代理分段等待（設計 §3.3 F2）
SUB_REWRITE_MIN_CTX = 20_000
F_TURNS = 15  # 接手成本取前這麼多回合的加權單位（設計 §1.4-2）


def ctx(turn: dict) -> int:
    return turn["inp"] + turn["cc"] + turn["cr"]


def _quantiles(values: list[float]) -> dict:
    ordered = sorted(values)
    if not ordered:
        return {"n": 0, "p25": None, "median": None, "p75": None, "p90": None}
    pick = lambda frac: ordered[min(len(ordered) - 1, int(frac * len(ordered)))]  # noqa: E731
    return {"n": len(ordered), "p25": pick(0.25), "median": statistics.median(ordered),
            "p75": pick(0.75), "p90": pick(0.90)}


# ───────────────────────────────────────────────────────────────────── 切片（母體 → 事件）
def idle_gaps(mains: list[dict]) -> list[dict]:
    """主控相鄰回合間隔 ≥ `IDLE_MIN_MIN` 分者；`rew`＝回來整份重寫（cc ≥ 一半上下文且前一回合
    上下文 ≥ 3 萬），`cc`＝重寫 token。`cause`＝本回合起因（reader 歸因）。"""
    out = []
    for main in mains:
        turns = [t for t in main["turns"] if t["ts_first"]]
        for prev, cur in zip(turns, turns[1:]):
            gap = (cur["ts_first"] - (prev["ts_last"] or prev["ts_first"])) / 60
            if gap < IDLE_MIN_MIN:
                continue
            rew = cur["cc"] >= 0.5 * ctx(cur) and ctx(prev) >= REWRITE_MIN_PREV_CTX
            wall = sw.wall_between(main.get("walls"), prev["ts_last"] or prev["ts_first"],
                                   cur["ts_first"])
            out.append({"sid": main["sid"][:8], "gap": gap, "ctx": ctx(prev), "cause": cur["cause"],
                        "rew": rew, "cc": cur["cc"] if rew else 0, "wall": wall})
    return out


def sub_rewrites(subs: list[dict]) -> tuple[list[dict], list[dict]]:
    """子代理冷快取重寫，分兩桶：`(交卷後被續棒, 執行中長等待)`（S1／S2；同 replay 的判準）。"""
    hand, wait = [], []
    for sub in subs:
        turns = [t for t in sub["turns"] if t["ts_first"]]
        for prev, cur in zip(turns, turns[1:]):
            c = ctx(cur)
            if c < SUB_REWRITE_MIN_CTX or cur["cc"] < 0.5 * c or cur["cause"] == "compaction":
                continue
            gap = (cur["ts_first"] - (prev["ts_last"] or prev["ts_first"])) / 60
            last_tool = prev["tools"][-1] if prev["tools"] else "(none)"
            row = {"gap": gap, "ctx": ctx(prev), "cc": cur["cc"], "cause": cur["cause"]}
            (hand if last_tool == "SubagentHandback" or cur["cause"] == "other_user"
             else wait).append(row)
    return hand, wait


# ───────────────────────────────────────────────────────────────────────── M-K1～M-K6
def m_k1(mains: list[dict]) -> dict:
    """主控「可保溫」閒置後重寫（起因人／通知／交卷／其他 user，間隔 ≥55 分）。基線 21 件。
    間隔中有額度牆者改歸 M-K7（`sections_wall.m_k7`），這裡不再重複計（MU-QW-11）。"""
    hits = [g for g in idle_gaps(mains) if g["cause"] in KEEPABLE and g["rew"] and not g["wall"]]
    return {"count": len(hits), "tokens": sum(g["cc"] for g in hits),
            "units": sum(W_CC1 * g["cc"] for g in hits)}


def m_k2(mains: list[dict]) -> dict:
    """主控閒置自動壓縮：auto 壓縮前閒置落在 50～60 分者。閒置 2～3 分的流程內壓縮不計。"""
    idle = [c for m in mains for c in m["compactions"]
            if c["trigger"] == "auto" and c["idle_min"] is not None]
    hits = [c for c in idle if IDLE_COMPACT_LO <= c["idle_min"] <= IDLE_COMPACT_HI]
    return {"count": len(hits), "auto_total": len(idle),
            "pre_tokens": sorted(c["pre"] for c in hits if c["pre"])}


def m_k3(subs: list[dict]) -> dict:
    """子代理執行中長等待後重寫（基線 77 件）。"""
    wait = sub_rewrites(subs)[1]
    return {"count": len(wait), "tokens": sum(r["cc"] for r in wait),
            "units": sum(W_CC5 * r["cc"] for r in wait)}


def m_k4(subs: list[dict]) -> dict:
    """子代理冷續棒重寫（交卷後被續；既有 150k 閘已擋，目標：不升）。"""
    hand = sub_rewrites(subs)[0]
    return {"count": len(hand), "tokens": sum(r["cc"] for r in hand),
            "units": sum(W_CC5 * r["cc"] for r in hand)}


def _kw_indices(turns: list[dict], calls: list[dict]) -> set[int]:
    """保溫類指令佔用的回合索引：背景 keepwarm＝叫醒回合與其後重掛的 tool_result 回合（兩回合）；
    前景（waitfor）＝發出指令的回合與讀結果的下一回合。沒有叫醒記錄的背景指令不計（尚在跑，
    它的發出回合屬於前一條鏈）。"""
    used: set[int] = set()
    for call in calls:
        if call["bg"]:
            if call["notif_ts"] is None:
                continue
            wake = call["notif_ts"]
            start = next((i for i, t in enumerate(turns) if t["ts_first"] >= wake), None)
        else:
            started = [i for i, t in enumerate(turns) if t["ts_first"] <= call["ts"]]
            start = started[-1] if started else None
        if start is not None:
            used.update(i for i in range(start, start + PING_TURNS) if i < len(turns))
    return used


def m_k5(mains: list[dict], subs: list[dict], k1_units: float = 0.0) -> dict:
    """保溫自身成本（keepwarm＋waitfor 回合的加權單位）。成本入帳：不得用「快取命中」掩蓋保溫
    花掉的錢。`ratio_vs_k1`＝保溫單位 ÷ 同期 M-K1 重寫單位（僅參照：被避免掉的重寫量不到）。"""
    calls = units_sum = fixed = 0
    for group in (mains, subs):
        for item in group:
            turns = [t for t in item["turns"] if t["ts_first"]]
            kws = item.get("kw_calls") or []
            calls += len(kws)
            for i in _kw_indices(turns, kws):
                units_sum += units(turns[i])
                fixed += units(turns[i]) - W_CR * turns[i]["cr"]  # 扣掉讀快取那一份＝P_fix 的對象
    return {"calls": calls, "units": units_sum, "fixed_units": fixed,
            "ratio_vs_k1": round(units_sum / k1_units, 3) if k1_units else None}


def is_handoff_start(first_prompt: str) -> bool:
    """首則提示（前 300 字）含交接包／handoff／handback ⇒ 這是交棒開場的 session。"""
    head = (first_prompt or "")[:300]
    return any(w in head or w in head.lower() for w in HANDOFF_WORDS)


def f_rows(mains: list[dict]) -> list[dict]:
    """以交接包／handoff／handback 開場的主控 session：前 `F_TURNS` 回合加權單位（接手成本 F）。
    母體只存 `handoff_start` 旗標，不存提示原文（快照不含對話內容）。"""
    rows = []
    for main in mains:
        turns = [t for t in main["turns"] if t["ts_first"]]
        if len(turns) < 2 or not main.get("handoff_start"):
            continue
        k = min(F_TURNS, len(turns))
        rows.append({"sid": main["sid"], "f": sum(units(t) for t in turns[:k]),
                     "b": ctx(turns[k - 1])})
    return rows


def m_k6(mains: list[dict], traces: list[dict]) -> dict:
    """換手次數與 F 實付：痕跡 `session_switch_spawned`（ok）逐筆配新 session 前 `F_TURNS` 回合
    的加權單位（找不到該逐字稿＝None）。決策表邊界歸屬屬人工判讀，這裡只量事實。"""
    by_sid = {m["sid"]: m for m in mains}
    paid = []
    spawns = [r for r in traces if r.get("event") == EV_SESSION_SPAWNED and r.get("ok") is True]
    for row in spawns:
        for name in row.get("new_transcripts") or []:
            main = by_sid.get(str(name).removesuffix(".jsonl"))
            turns = [t for t in (main or {}).get("turns", []) if t["ts_first"]]
            if turns:
                paid.append(sum(units(t) for t in turns[:F_TURNS]))
    return {"spawns": len(spawns), "f_paid": _quantiles(paid), "f_paid_n": len(paid)}


def trace_counts(traces: list[dict]) -> dict:
    """新機制自身的痕跡事件件數（0＝尚無資料或機制沒觸發；不是「好消息」）。"""
    names = (EV_KEEPWARM_VERDICT, EV_KEEPWARM_STOP_BLOCK, EV_WATCH_QUOTA_LATCHED, EV_LONGWAIT_BLOCK)
    return {n: sum(1 for r in traces if r.get("event") == n) for n in names}


def switch_metrics(pop: dict, traces: list[dict], oldwin: list[dict] | None = None,
                   now: float | None = None) -> dict:
    """M-K1～M-K9。M-K7／M-K8／M-K9（額度牆，R218 Q5）判準在 `sections_wall`；`oldwin` 是
    oldwin 痕跡列（舊資料 park 失敗原因的對應來源）、`now` 供「reset＋30 分」判斷（缺省取現在）。"""
    k1 = m_k1(pop["main"])
    return {"m_k1": k1, "m_k2": m_k2(pop["main"]), "m_k3": m_k3(pop["sub"]),
            "m_k4": m_k4(pop["sub"]), "m_k5": m_k5(pop["main"], pop["sub"], k1["units"]),
            "m_k6": m_k6(pop["main"], traces), "trace": trace_counts(traces),
            **sw.switch_wall_metrics(pop, traces, oldwin or [],
                                     time.time() if now is None else now)}


# ───────────────────────────────────────────────────────────────────────────── 重放
def _kw_cost(x: dict, cap_min: float, ping_min: float) -> tuple[float, int, bool]:
    n = int(min(x["gap"], cap_min) // ping_min)
    cost, cx = 0.0, x["ctx"]
    for _ in range(n):
        cost += PING_TURNS * W_CR * cx + PING_FIXED
        cx += PING_GROWTH
    expired = x["gap"] > n * ping_min + IDLE_MIN_MIN  # 觀測：閒置約 55 分 harness 自動壓縮
    return cost + (W_CC1 * cx if expired else 0.0), n, expired


def n_star(c: float) -> int:
    """F1：最多保溫次數 `floor(R/p)`，R＝放冷代價 `W_CC1·c`、p＝每次保溫 `2·W_CR·c + P_fix`。"""
    return int(W_CC1 * c / (PING_TURNS * W_CR * c + PING_FIXED))


def replay_p1(mains: list[dict], ping_min: float) -> dict:
    """P1 主控保溫：可保溫子集在「放冷、回來整份重寫」基線 vs 動態 n* 保溫的加權單位。"""
    gaps = idle_gaps(mains)
    kp = [g for g in gaps if g["cause"] in KEEPABLE]
    base = sum(W_CC1 * g["cc"] for g in kp)
    total = pings = missed = 0
    for g in kp:
        cost, n, expired = _kw_cost(g, n_star(g["ctx"]) * ping_min, ping_min)
        total, pings, missed = total + cost, pings + n, missed + expired
    return {"idle_ge_55": len(gaps), "keepable": len(kp),
            "rewrites": sum(g["rew"] for g in kp), "base": base, "cost": total,
            "saved": base - total, "pings": pings, "still_expired": missed,
            "ping_min": ping_min}


def replay_p3(mains: list[dict], f_cost: float, qs=(0.0, 0.5, 1.0)) -> list[dict]:
    """P3 額度續跑選路（F4）：重寫 `W_CC1·c` vs 換新 `F(1+q)`；q＝品質損失係數。"""
    qr = [g for g in idle_gaps(mains) if g["cause"] == "quota_resume" and g["rew"]]
    out = []
    for q in qs:
        fresh = [g for g in qr if W_CC1 * g["ctx"] > f_cost * (1 + q)]
        out.append({"q": q, "events": len(qr), "fresh": len(fresh),
                    "net": sum(W_CC1 * g["cc"] - f_cost for g in fresh)})
    return out


def _remaining(turns: list[dict], threshold: int) -> tuple[int, int] | None:
    """首次跨過 `threshold` 的回合：`(跨越時上下文, 其後到壓縮／結束的回合數)`；沒跨過 ⇒ None。"""
    hit = next((i for i, t in enumerate(turns) if ctx(t) >= threshold), None)
    if hit is None:
        return None
    prev, n = ctx(turns[hit]), 0
    for t in turns[hit + 1:]:
        if ctx(t) < HARD_COMPACT_BELOW * prev:
            break
        prev, n = ctx(t), n + 1
    return ctx(turns[hit]), n


def replay_p4b(mains: list[dict], f_cost: float, b: float, thresholds=P4B_THRESHOLDS,
               cut: str = P4B_CUT) -> list[dict]:
    """P4b 邊界軟線掃描（史料對照；軟線依裁決不實作）：只用 `cut` 之前開場的 session。"""
    cut_ts = time.mktime(time.strptime(cut, "%Y-%m-%d"))
    pre = [[t for t in m["turns"] if t["ts_first"]] for m in mains]
    pre = [t for t in pre if len(t) >= 2 and t[0]["ts_first"] < cut_ts]
    out = []
    for th in thresholds:
        crossed = [r for r in (_remaining(turns, th) for turns in pre) if r]
        rems = [n for _c, n in crossed]
        net = {q: sum(n * W_CR * max(0, c - b) - f_cost * (1 + q) for c, n in crossed)
               for q in (0, 1, 2)}
        out.append({"T": th, "crossed": len(crossed), "rem_min": min(rems, default=None),
                    "rem_median": statistics.median(rems) if rems else None,
                    "rem_max": max(rems, default=None), "net": net, "sessions": len(pre)})
    return out


def f_sub(subs: list[dict]) -> float | None:
    """新子代理接手成本上界 `F_a`：前 10 回合加權單位中位。"""
    vals = [sum(units(t) for t in [x for x in s["turns"] if x["ts_first"]][:10])
            for s in subs if len([x for x in s["turns"] if x["ts_first"]]) >= 10]
    return statistics.median(vals) if vals else None


def replay_subs(subs: list[dict]) -> dict:
    """S1 冷續棒（現行 150k 閘 vs 成本式 `W_CC5·c > F_a`）與 S2 分段等待（每 4 分回來，
    ski-rental 上限）。"""
    hand, wait = sub_rewrites(subs)
    fa = f_sub(subs) or 0.0
    gate = lambda rows, thr: [r for r in rows if r["ctx"] >= thr]  # noqa: E731
    cost = [r for r in hand if W_CC5 * r["ctx"] > fa]
    base = sum(W_CC5 * r["cc"] for r in wait)
    total = polls = missed = 0
    for r in wait:
        nstar = int(W_CC5 * r["ctx"] / (W_CR * r["ctx"] + SUB_POLL_FIXED))
        need = max(0, int(r["gap"] // SUB_POLL_MIN))
        n = min(need, nstar)
        total, polls = total + n * (W_CR * r["ctx"] + SUB_POLL_FIXED), polls + n
        if need > nstar:
            total, missed = total + W_CC5 * r["ctx"], missed + 1
    gaps = sorted(r["gap"] for r in wait)
    return {"f_a": fa, "s1_events": len(hand), "s1_tokens": sum(r["cc"] for r in hand),
            "s1_gate_150k": (len(gate(hand, 150_000)),
                             sum(W_CC5 * r["cc"] - fa for r in gate(hand, 150_000))),
            "s1_cost_gate": (len(cost), sum(W_CC5 * r["cc"] - fa for r in cost)),
            "s2_events": len(wait), "s2_tokens": sum(r["cc"] for r in wait), "s2_base": base,
            "s2_cost": total, "s2_polls": polls, "s2_still_expired": missed,
            "s2_gap_median": statistics.median(gaps) if gaps else None,
            "s2_gap_p90": gaps[int(0.9 * len(gaps))] if gaps else None}


def replay_all(pop: dict, ping_min: float, f_cost: float | None = None) -> dict:
    """設計 §7 全表。`f_cost` 缺省取實測接手成本中位（沒有實測列才退回 DES 出廠 480,000）。"""
    fr = f_rows(pop["main"])
    measured = statistics.median(r["f"] for r in fr) if fr else 480_000
    f_med = f_cost if f_cost is not None else measured
    b_med = statistics.median(r["b"] for r in fr) if fr else 150_000
    return {"f_cost": f_med, "b": b_med, "f_n": len(fr), "p1": replay_p1(pop["main"], ping_min),
            "p3": replay_p3(pop["main"], f_med), "p4b": replay_p4b(pop["main"], f_med, b_med),
            "subs": replay_subs(pop["sub"]), "m_k2": m_k2(pop["main"])}


# ───────────────────────────────────────────────────────────────────────────── 校準
def resume_cost_summary(rows: list[dict]) -> dict:
    """`autosdd_resume_cost.jsonl` 的 measured 列：SESSION_RESUME 首回合的寫入占比與實付加權單位。
    F4 的前提是「過期後續跑≈整份重寫」，這裡用實測驗它（relay_seq＝0 才是冷窗）。"""
    units_, shares = [], []
    for r in rows:
        if not r.get("measured") or not all(type(r.get(k)) is int for k in
                                            ("input_tokens", "cache_creation_input_tokens",
                                             "cache_read_input_tokens")):
            continue
        cc, cr = r["cache_creation_input_tokens"], r["cache_read_input_tokens"]
        if cc + cr <= 0:
            continue
        units_.append(r["input_tokens"] + W_CC1 * cc + W_CR * cr)
        shares.append((cc / (cc + cr), r.get("relay_seq")))
    cold = [s for s, relay in shares if relay in (0, None)]
    return {"n": len(units_), "units": _quantiles(units_),
            "write_share_ge_80pct_cold": sum(1 for s in cold if s >= 0.8), "cold_n": len(cold)}


def calibrate(pop: dict, resume_rows: list[dict], ping_min: float) -> dict:
    """F、B、N_lo、P_fix 的建議值（皆量測值；N_lo 只餵已不實作的軟線 F3，僅供史料）。"""
    fr = f_rows(pop["main"])
    p4 = [r for r in replay_p4b(pop["main"], 480_000, 150_000, (450_000,)) if r["crossed"]]
    mk5 = m_k5(pop["main"], pop["sub"])
    per_call = mk5["fixed_units"] / mk5["calls"] if mk5["calls"] else None
    return {"f": _quantiles([r["f"] for r in fr]), "b": _quantiles([r["b"] for r in fr]),
            "n_lo_450k": {"min": p4[0]["rem_min"], "median": p4[0]["rem_median"],
                          "crossed": p4[0]["crossed"]} if p4 else None,
            "p_fix": {"measured_units_per_call": per_call, "calls": mk5["calls"],
                      "factory": PING_FIXED},
            "resume_cost": resume_cost_summary(resume_rows), "ping_min": ping_min}
