"""監督與換手量測 M-W1～W4、M-F1～F3、M-S1～S3（ARCH §1.10／§2.8／§9；量測探針，不接閘門 rc）。

WHY：「背景子代理有沒有人看管」「換 session 有沒有自動接好」上線後，只能靠可重跑的數字回答
「有沒有變好」。基線（2026-11-16 逐字稿普查）：無看管區間 671 筆／176.7 小時、背景叫醒冷重寫 23 次、
冷真人重寫 15 次、手貼接續 13/22、包過時最大 442 分。本檔全是純函式：輸入＝supervision_load 已解析
的輕量記錄（`{t, type, sub, ok, ...}`，t 為 epoch 秒），不自己讀家目錄；I/O 在 supervision_load。
痕跡事件名集中在下方常數，後續工作包照這些名字寫痕跡；事件不存在時對應指標印 0 並標「尚無資料」。
"""
from __future__ import annotations

import math
import statistics
from collections import Counter
from collections.abc import Callable

# ── 痕跡事件名（autosdd_session_switch.jsonl 的 event 欄；後續工作包依此命名寫入）
EV_SUPERVISE_STOP_BLOCK = "supervise_stop_block"  # M-W3：監督閘推回
EV_WATCH_VERDICT = "watch_verdict"  # M-W4：watch 判決（stall／overrun／budget…）喚醒主控
EV_FORWARD_SPAWNED = "forward_spawned"  # M-F2
EV_FORWARD_FAILED = "forward_spawn_failed"  # M-F2
EV_FORWARD_PASS = "forward_pass"  # M-F2（放行；含第一個不成立條件編號）
EV_SESSION_SPAWNED = "session_switch_spawned"  # M-F3：包已 spawn（sid＝被交棒的舊 session）
EV_SEAL_STOP_BLOCK = "seal_stop_block"  # M-S1：封存閘推回
NEW_EVENTS = (EV_SUPERVISE_STOP_BLOCK, EV_WATCH_VERDICT, EV_FORWARD_SPAWNED, EV_FORWARD_FAILED,
              EV_FORWARD_PASS, EV_SEAL_STOP_BLOCK)
NO_DATA = "尚無資料"

COLD_IDLE_S = 60 * 60  # 快取壽命實測 1 小時（普查 2c）
COLD_MIN_CTX = 100_000  # 上一刻上下文 ≥ 此值的喚醒才算冷重寫
MIN_WAKE_IDLE_S = 5 * 60
R1_DEFAULT = 250_000  # 換 session 提醒門檻（預設；入口可由 switch.threshold 現查後傳入）
PASTE_MIN_CHARS = 1500  # 第一則真人提示超過此字數視為手貼上輪總結
PASTE_HINTS = ("以下是上輪", "上輪資訊", "上輪總結", "上一輪")
MACHINE_FIRST = ("按交接包繼續：", "按磁碟任務書繼續：")
STOP_VOICE = "本回合結束時仍有"
_INJECTED = ("<system-reminder>", "<command-", "<local-command-", "<task-notification>")
HOOK_MERGE_S = 10.0  # turn_duration 與 Stop 出聲相距這麼近視為同一事件

NoCredential = Callable[[dict], bool]


def _no_credential(_event: dict) -> bool:
    """待 WP-4 接上 supervise.credential；在那之前一律視為無憑證。"""
    return False


def quantiles(values: list[float]) -> dict:
    v = sorted(x for x in values if x is not None)
    if not v:
        return {"n": 0}
    pick = lambda p: v[min(len(v) - 1, max(0, math.ceil(p * len(v)) - 1))]  # noqa: E731
    return {"n": len(v), "p50": round(statistics.median(v), 1), "p90": round(pick(0.9), 1),
            "max": round(v[-1], 1)}


def _is_real_assistant(r: dict) -> bool:
    return r["type"] == "assistant" and r.get("model") != "<synthetic>"


def ctx_of(use: dict | None) -> int:
    return sum(int(v) for k, v in (use or {}).items() if k != "output_tokens" and type(v) is int)


def is_human(r: dict) -> bool:
    return (r["type"] == "user" and not r.get("meta") and r.get("ok") == "human"
            and not r.get("tool_result") and bool(r.get("text", "").strip())
            and not r["text"].strip().startswith(_INJECTED))


# ───────────────────────── M-W1：無看管區間
def _pending_turn(r: dict) -> bool:
    return r["type"] == "system" and r.get("sub") == "turn_duration" and (r.get("pending") or 0) > 0


def _voice_kind(content: str) -> str:
    """WP-SW REQ-CTL-56：Stop 出聲含「支背景代理」⇒ `agent`（兩者皆含也算 agent）；只含「個背景 shell」⇒ `shell`。
    `STOP_VOICE` 同時命中兩者（W1 把背景 shell 也算成無看管，w1_detail 29 筆 >30 分中 17 筆其實是 shell）。"""  # noqa: E501
    return "agent" if "支背景代理" in content or "個背景 shell" not in content else "shell"


def stop_events(recs: list[dict]) -> list[dict]:
    """回合結束時仍有背景工作的事件：A＝Stop hook 出聲（含「仍有 N 支背景代理」）、B＝harness 自記
    的 turn_duration.pendingBackgroundAgentCount>0（與 A 相距 <10 秒者併入 A）。每筆帶到主控下一筆
    assistant 的間隔 `gap_s`（None＝再也沒回來）。"""
    ev: list[dict] = []
    for i, r in enumerate(recs):
        if r["type"] == "attachment" and r.get("hook_event") == "Stop" \
                and STOP_VOICE in r.get("content", ""):
            ev.append({"i": i, "t": r["t"], "src": "A", "kind": _voice_kind(r.get("content", ""))})
    for i, r in enumerate(recs):
        if _pending_turn(r):
            if not any(abs(e["t"] - r["t"]) < HOOK_MERGE_S for e in ev):
                ev.append({"i": i, "t": r["t"], "src": "B", "kind": "agent"})  # pendingBackgroundAgentCount>0＝子代理  # noqa: E501
    ev.sort(key=lambda e: e["t"])
    for e in ev:
        nxt = next((r for r in recs[e["i"] + 1:] if _is_real_assistant(r)), None)
        e["gap_s"] = (nxt["t"] - e["t"]) if nxt else None
    return ev


def m_w1(sessions: list[dict], credential: NoCredential = _no_credential) -> dict:
    """無看管區間：有在飛背景工作、且 `credential(event)` 為假的 Stop→下一筆 assistant。"""
    events = []
    for s in sessions:
        for e in stop_events(s["recs"]):
            e["sid"] = s["sid"]
            if not credential(e):
                events.append(e)
    gaps = [e["gap_s"] / 60 for e in events if e["gap_s"] is not None]
    voiced = [e for e in events if e["src"] == "A"]
    return {"n": len(events), "n_hook_voiced": len(voiced),
            "total_hours": round(sum(gaps) / 60, 1), "gap_min": quantiles(gaps),
            "gt_60min": sum(1 for g in gaps if g > 60),
            "never_returned": sum(1 for e in events if e["gap_s"] is None),
            # WP-SW REQ-CTL-56：既有鍵逐字不變；另列只計子代理／只計 shell 的子集（agent.n + shell.n == n）  # noqa: E501
            "agent": _subset([e for e in events if e.get("kind", "agent") == "agent"]),
            "shell": _subset([e for e in events if e.get("kind", "agent") == "shell"])}


def _subset(events: list[dict]) -> dict:
    gaps = [e["gap_s"] / 60 for e in events if e["gap_s"] is not None]
    return {"n": len(events), "total_hours": round(sum(gaps) / 60, 1),
            "gt_30min": sum(1 for g in gaps if g > 30), "gt_60min": sum(1 for g in gaps if g > 60),
            "max_min": round(max(gaps), 1) if gaps else 0.0,
            "never_returned": sum(1 for e in events if e["gap_s"] is None)}

# ───────────────────────── M-W2／M-F1：冷重寫（依喚醒者分）
def cold_wakes(recs: list[dict]) -> list[dict]:
    """互動 session 內「閒置 ≥ MIN_WAKE_IDLE_S 後被喚醒」的事件；首回合以 cache_creation 為主者
    `rewrite=True`。woke＝human／task-notification／peer／auto-continuation。"""
    out, prev = [], None
    for i, r in enumerate(recs):
        if _is_real_assistant(r) and r.get("use"):
            prev = r
        woke = None
        if r["type"] == "user" and not r.get("meta") and not r.get("tool_result"):
            if is_human(r):
                woke = "human"
            elif r.get("ok") in ("task-notification", "auto-continuation"):
                woke = r["ok"]
        elif r["type"] == "user" and r.get("ok") == "peer":
            woke = "peer"
        if not woke or prev is None or r["t"] - prev["t"] < MIN_WAKE_IDLE_S:
            continue
        nxt = next((x for x in recs[i + 1:] if _is_real_assistant(x) and x.get("use")), None)
        if nxt is None:
            continue
        use = nxt["use"]
        cc, cr = use.get("cache_creation_input_tokens", 0), use.get("cache_read_input_tokens", 0)
        out.append({"woke": woke, "idle_s": r["t"] - prev["t"], "prev_ctx": ctx_of(prev["use"]),
                    "cc": cc, "cr": cr, "rewrite": cc > cr})
    return out


def _cold(wakes: list[dict], kinds: tuple[str, ...]) -> dict:
    sel = [w for w in wakes if w["woke"] in kinds and w["idle_s"] >= COLD_IDLE_S
           and w["prev_ctx"] >= COLD_MIN_CTX and w["rewrite"]]
    return {"n": len(sel), "tokens": sum(w["cc"] for w in sel)}


def m_w2_f1(sessions: list[dict]) -> tuple[dict, dict]:
    """(M-W2 背景叫醒冷重寫＝task-notification／peer，M-F1 冷真人重寫)；只計互動 session。"""
    wakes = [w for s in sessions if s.get("interactive") for w in cold_wakes(s["recs"])]
    return _cold(wakes, ("task-notification", "peer")), _cold(wakes, ("human",))


# ───────────────────────── M-F3／M-S1／M-S2／M-S3 與痕跡計數
def m_f3(sessions: list[dict], trace: list[dict]) -> dict:
    """包已 spawn 後該 sid（舊視窗）再出現真人提示的件數（TH-1 量測）。"""
    by_sid = {s["sid"]: s for s in sessions}
    spawns = [(e.get("sid"), e["_at"]) for e in trace if e.get("event") == EV_SESSION_SPAWNED
              and e.get("_at") is not None]
    hits = 0
    for sid, at in spawns:
        s = by_sid.get(sid)
        hits += sum(1 for r in (s["recs"] if s else []) if r["t"] > at and is_human(r))
    return {"spawned": len(spawns), "human_prompts_after_spawn": hits}


def m_s1(sessions: list[dict], packs: list[dict], r1: int = R1_DEFAULT,
         since: float | None = None) -> dict:
    """回合結束時上下文 ≥ R1、無在飛代理、且當時沒有已 finalize 的交接包（封存閘上線後應為 0）。
    `since`＝機制第一次留下痕跡的時刻；只計其後（之前機制不存在，計入會把「沒有」誤當缺口）。"""
    total = without = 0
    for s in sessions:
        if not s.get("interactive"):
            continue
        mine = [p for p in packs if p["sid"] == s["sid"]]
        last_ctx = None
        for r in s["recs"]:
            if _is_real_assistant(r) and r.get("use"):
                last_ctx = ctx_of(r["use"])
            if r["type"] == "system" and r.get("sub") == "turn_duration" and last_ctx is not None:
                before = since is not None and r["t"] < since
                if before or last_ctx < r1 or (r.get("pending") or 0) > 0:
                    continue
                total += 1
                if not any(p["finalized"] and p["built_at"] is not None and p["built_at"] <= r["t"]
                           for p in mine):
                    without += 1
    return {"turn_ends_ge_r1": total, "without_finalized_pack": without}


def first_prompt_class(recs: list[dict]) -> str:
    first = next((r for r in recs if is_human(r)), None)
    if first is None:
        return "no_human_prompt"
    text = first["text"]
    if text.startswith(MACHINE_FIRST):
        return "machine_handoff_prompt"
    long_text = first.get("textlen", len(text)) > PASTE_MIN_CHARS
    if long_text or any(h in text[:600] for h in PASTE_HINTS):
        return "human_pasted_prior_summary"
    return "fresh_short_prompt"


def m_s2(sessions: list[dict]) -> dict:
    inter = [s for s in sessions if s.get("interactive") and s["recs"]]
    kinds = Counter(first_prompt_class(s["recs"]) for s in inter)
    return {"n_interactive": len(inter), "pasted": kinds.get("human_pasted_prior_summary", 0),
            "by_class": dict(kinds)}


def m_s3(sessions: list[dict], packs: list[dict]) -> dict:
    """機械層產生時刻落後 session 最後一筆對話記錄的分鐘數。"""
    talk = ("human", "auto-continuation")
    last = {s["sid"]: max((r["t"] for r in s["recs"]
                           if r["type"] == "assistant" or r.get("ok") in talk), default=None)
            for s in sessions}
    lags = [(last[p["sid"]] - p["built_at"]) / 60 for p in packs
            if last.get(p["sid"]) and p["built_at"] and last[p["sid"]] >= p["built_at"]]
    return {"n_packs": len(packs), "lag_min": quantiles(lags)}


def count_events(trace: list[dict], names: tuple[str, ...]) -> dict:
    c = Counter(e.get("event") for e in trace)
    return {n: c.get(n, 0) for n in names}


def dispatch_waves(sessions: list[dict]) -> int:
    """派工波數＝主控含 Agent／Task tool_use 的 assistant 回合數（M-W3 分母）。"""
    spawn = ("Agent", "Task")
    return sum(1 for s in sessions for r in s["recs"]
               if r["type"] == "assistant" and any(t in spawn for t in r.get("tools", ())))


def compute(sessions: list[dict], packs: list[dict], trace: list[dict], *,
            r1: int = R1_DEFAULT, credential: NoCredential = _no_credential) -> dict:
    """彙整全部指標；事件不存在的指標標 NO_DATA（量到 0 與「機制還沒寫痕跡」是兩回事）。"""
    since = min((e["_at"] for e in trace if e.get("_at") is not None), default=None)
    w2, f1 = m_w2_f1(sessions)
    ev = count_events(trace, NEW_EVENTS)
    waves = dispatch_waves(sessions)
    nodata = lambda name: NO_DATA if ev[name] == 0 else None  # noqa: E731
    fwd = {k: ev[k] for k in (EV_FORWARD_SPAWNED, EV_FORWARD_FAILED, EV_FORWARD_PASS)}
    return {
        "m_w1": m_w1(sessions, credential), "m_w2": w2,
        "m_w3": {"supervise_stop_block": ev[EV_SUPERVISE_STOP_BLOCK], "dispatch_waves": waves,
                 "note": nodata(EV_SUPERVISE_STOP_BLOCK)},
        "m_w4": {"watch_verdicts": ev[EV_WATCH_VERDICT], "note": nodata(EV_WATCH_VERDICT)
                 or "未 TaskStop 比例需逐字稿對照，待 WP-4 痕跡帶欄位"},
        "m_f1": f1,
        "m_f2": {**fwd, "note": NO_DATA if not any(fwd.values()) else None},
        "m_f3": m_f3(sessions, trace),
        "m_s1": {**m_s1(sessions, packs, r1, since), "seal_stop_block": ev[EV_SEAL_STOP_BLOCK],
                 "since": since},
        "m_s2": m_s2(sessions), "m_s3": m_s3(sessions, packs),
    }
