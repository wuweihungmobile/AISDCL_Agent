"""背景代理監督程序 `sessionctl watch`（R3 WP-4A；ARCH §1.2／§1.3／§1.5／§1.8）。

主控派出背景子代理後常直接結束回合，沒有人看管。本程序**阻塞到「有事發生」才結束**：主控把它當
背景任務掛著，它一結束 harness 就叫醒主控——這就是會主動叫醒主控的事件源（鐵律六）。

分層：`decide`（純函式、判準）／`resolve_cfg`（門檻解析）／`run`（迴圈；時鐘、sleep、名冊、額度
一律參數注入，不開任何測試用環境變數）。本檔不 import `wastecensus`（守衛面不依賴量測探針）。
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import endurance_env
import unattended_authz

from . import cutvoice, holder, keepwarm, procstop, qw_plan, roster, switch, watch_wake, watchlock

#: 痕跡事件名；測試斷言它等於 supervision 的 `EV_WATCH_VERDICT`（兩邊各自定義、不互 import）。
EV_WATCH_VERDICT = "watch_verdict"
SCHEMA = "autosdd.watch/1"
#: 判決一律 rc 0、事件只看末行 `WATCH_VERDICT=`（DEF-200-622：harness 把背景指令的任何非 0 結束
#: 都顯示成「failed」，掌舵者真機看到十多次「exit code 5／6」以為是錯誤；叫醒事件是設計內的正常
#: 結果）。非 0 只留給真錯誤（缺 --sid＝2、內部例外）。
#: 同一輪多事件並存時的先後：quota（跨代理、不可逆的額度牆）＞ budget（每多一輪都更貴）＞
#: stall（代理已死，繼續等純浪費）＞ overrun（慢但可能仍在做事）＞ 保溫族（keepwarm／cap／idle，
#: 純保溫，任何實質事件都比它重要；三者互斥，由叫醒預算決定是哪一個）。
#: REQ-WP-30：**沒有 `all_done`**——harness 對每支背景子代理完成都會送 task-notification，watch
#: 再因「全部交卷」退出＝同一事件叫醒主控兩次（M-WB2：14 天 21 次，每次冷讀 40 萬～99 萬 token）。
#: R218 Q2：`handed_over`（本視窗已交棒，別的 session 在動工作樹）最優先；`resume`（主載具到預定
#: 時刻）排在保溫族之前——它不是保溫，是「該接著做事了」。
ORDER = ("handed_over", "quota", "budget", "stall", "overrun", "resume", "keepwarm", "cap", "idle")
KEEPWARM_FAMILY = ("keepwarm", "cap", "idle")
#: 保溫點＝主控**最後一筆帶 usage 的 assistant 記錄**＋45 分（R216：早於閒置約 55 分的自動壓縮與
#: 1 小時快取壽命；錨點不是 watch 啟動時刻）。數字與錨點函式唯一的家＝`keepwarm.py`。
KEEPWARM_MINUTES = keepwarm.DEFAULT_MINUTES
_KEEPWARM_MARGIN_MINUTES = 5  # 無人窗口：離 harness 背景等待上限至少留這麼多分鐘
STALL_FLOOR_MINUTES = 11  # 前景工具逾時 600 秒＋餘裕
STALL_DEFAULT_MINUTES = 15
WALL_DEFAULT_MINUTES = 120
POLL_SECONDS = 30.0
#: 判決後主控該做什麼（ARCH §1.5 處置表；R217 §6.4）；判決行之後印對應那一列。
#: 代理交卷不在此表：它由 harness 的子代理完成通知叫醒主控（根 CLAUDE.md〈派背景代理〉）。
DISPOSAL = {
    "keepwarm": "重掛同一指令並結束回合，不做任何判斷（重掛的是 watch；`python tools/sessionctl.py status` 也不必跑；本回合輸出 ≤ 50 token）",  # noqa: E501
    "cap": "已到保溫損益點（再保溫比放冷重寫更貴）：不重掛、直接結束回合讓快取過期；若仍有背景子代理在跑，才重掛 watch（它不再為保溫叫醒）",  # noqa: E501
    "idle": "本情形不需要保溫（無人窗口／模式非 auto／已交棒／上下文太小…）：不重掛 keepwarm、結束回合；若仍有背景子代理在跑，才重掛 watch",  # noqa: E501
    "stall": "`sessionctl status` 看該代理最後一筆；確定卡住 ⇒ TaskStop 它、派新代理＋短任務書（指向它的 HB 檔；不得 SendMessage 冷續，`resume_gate` 也會擋）；重掛 watch",  # noqa: E501
    "overrun": "讀它的 HB：快完成 ⇒ 重掛 watch 並 `--wall-min <現值+30>`（每支至多一次）；否則 TaskStop＋拆小重派",  # noqa: E501
    "budget": "TaskStop（續下去每輪都更貴）＋派新代理接它的 HB",
    "quota": "先 `python tools/sessionctl.py quota` 重算（判決過期一律重算），再依新 ACTION 查 watch_wake.QUOTA_DISPOSAL 對應列",  # noqa: E501
    "resume": keepwarm.DISPOSAL["resume"],
    "handed_over": keepwarm.DISPOSAL["handed_over"],
    "switch_due": "到換手點（硬線待換、在飛代理已全數交卷）：寫完交接包主控層 → `handoff --finalize <包>` → `--spawn`；不再派新代理",  # noqa: E501
    # 入口判決（不是 decide 的事件，ORDER 不含它）：同 sid 已有活 watch。
    "duplicate": "已有同 sid 的 watch 在掛：不需重掛，繼續本回合或結束回合",
}
UNKNOWN_DISPOSAL = "watch 自己壞了（rc≠0 或無判決行）：重掛；連兩次 ⇒ 依 watch 輸出檔立案"


@dataclass(frozen=True)
class Cfg:
    stall_min: float = STALL_DEFAULT_MINUTES
    wall_min: float = WALL_DEFAULT_MINUTES
    ctx_max: int = 700000
    keepwarm_min: float = KEEPWARM_MINUTES


def keepwarm_minutes(env=None) -> float:
    """`T_kw`（`keepwarm.t_kw_minutes`：出廠 45、env 只准下修）；無人窗口（`AUTOSDD_UNATTENDED`）＝
    min(T_kw, harness 背景等待上限分鐘−5)。"""
    env = os.environ if env is None else env
    base = keepwarm.t_kw_minutes(env)
    if env.get("AUTOSDD_UNATTENDED"):
        ceiling = unattended_authz.RESUME_BG_WAIT_CEILING_SECONDS / 60
        return min(base, ceiling - _KEEPWARM_MARGIN_MINUTES)
    return base


def _num(raw) -> float | None:
    try:
        return float(str(raw).strip())
    except ValueError:
        return None


def _stall(raw, label: str) -> float:
    val = _num(raw)
    if val is None or val < STALL_FLOOR_MINUTES:
        print(f"⚠️ {label}={raw!r} 低於下限 {STALL_FLOOR_MINUTES}（前景工具逾時上限 10 分鐘＋餘裕）"
              f"⇒ 退回 {STALL_DEFAULT_MINUTES}", file=sys.stderr)
        return float(STALL_DEFAULT_MINUTES)
    return val


def resolve_cfg(env=None, *, stall_min=None, wall_min=None, ctx_max=None) -> Cfg:
    """env 缺席＝出廠值；CLI 值蓋過 env。stall 下限 11（兩個入口同規則）；ctx 只准下修（CLI 值不得
    大於 env 生效值，否則退回該生效值並出聲）。"""
    env = os.environ if env is None else env
    raw_stall = str(env.get(switch.WATCH_STALL_KEY) or "").strip()
    stall = _stall(raw_stall, switch.WATCH_STALL_KEY) if raw_stall else float(STALL_DEFAULT_MINUTES)
    if stall_min is not None:
        stall = _stall(stall_min, "--stall-min")
    raw_wall = str(env.get(switch.WATCH_WALL_KEY) or "").strip()
    wall = _num(raw_wall) if raw_wall else None
    if raw_wall and (wall is None or wall <= 0):
        print(f"⚠️ {switch.WATCH_WALL_KEY}={raw_wall!r} 是病態值 ⇒ 退回 {WALL_DEFAULT_MINUTES}",
              file=sys.stderr)
    wall = wall if wall and wall > 0 else float(WALL_DEFAULT_MINUTES)
    if wall_min is not None and wall_min > 0:
        wall = float(wall_min)
    ctx = switch.threshold(switch.WATCH_CTX_KEY, env)[0]
    if ctx_max is not None:
        if ctx_max > ctx or ctx_max < 1:
            print(f"⚠️ --ctx-max={ctx_max} 不得大於生效值 {ctx:,}（只准下修）⇒ 沿用 {ctx:,}",
                  file=sys.stderr)
        else:
            ctx = int(ctx_max)
    return Cfg(stall, wall, ctx, keepwarm_minutes(env))


def _epoch(iso) -> float | None:
    return procstop.parse_iso(iso)


def _label(agent: dict) -> str:
    return (f"{str(agent.get('id'))[:10]} {agent.get('model') or '?'}"
            f"｜{agent.get('description') or '?'}")


def decide(agents: list[dict], now: float, started_at: float, cfg: Cfg, quota_hit: bool | str, *,
           kw_anchor: float | None = None, kw_enabled: bool = True,
           kw_verdict=None, kw_due: float | None = None) -> tuple[str, str] | None:
    """純函式：回 `(事件, 明細)`；無事件 ⇒ `None`。`agents`＝**未交卷**代理（名冊
    `finished!=true`），每項可帶 `end_turn: bool`（最後一筆是 assistant end_turn＝在等自己的
    背景 shell，FR-W3 不判 stall）。`now`／`started_at` 為 epoch 秒；多事件先後見 `ORDER`。
    `kw_anchor`＝主控最後一筆帶 usage 的 assistant 記錄時刻（`keepwarm.anchor`）；保溫點＝它＋
    `keepwarm_min`，量不到（`None`）才退回 `started_at`（舊行為，只會更晚）。

    保溫族（REQ-WP-30／36）：到保溫點才問 `kw_verdict()`（`keepwarm`｜`cap`｜`idle`；未給＝
    `keepwarm`）。`keepwarm`（還有預算、保溫適用）與 `idle`（保溫不適用）一律退出；`cap`（預算
    用完）**只在沒有未交卷代理時**退出——代理還在跑時再為保溫叫醒主控，只是白付一次冷讀。
    `kw_enabled=False`（別的行程持有保溫錨）⇒ 整個保溫族不判，避免兩個行程重複叫醒。
    `kw_due`（R218 Q2：主載具有目標時的排程第一個叫醒時刻）蓋過「錨點＋keepwarm_min」；
    `kw_verdict()` 回 `None`＝本輪不判（牆內延後）、`resume`／`handed_over`＝無論有無代理都退出。"""
    found: dict[str, str] = {}
    if quota_hit:  # 字串＝依來源分開的文案（watch_wake.quota_detail）；裸 True 不知來源，不冒稱
        found["quota"] = quota_hit if isinstance(quota_hit, str) else "額度事件成立（短窗額度）"
    over = [a for a in agents if isinstance(a.get("ctx_tokens"), int)
            and a["ctx_tokens"] >= cfg.ctx_max]
    if over:
        rows = "\n".join(f"  - {_label(a)}｜{a['ctx_tokens']:,} token" for a in over)
        found["budget"] = f"上下文達 {cfg.ctx_max:,}：\n{rows}"
    stalled = []
    for a in agents:
        last = _epoch(a.get("last_at"))
        if last is not None and now - last >= cfg.stall_min * 60 and not a.get("end_turn"):
            stalled.append((a, (now - last) / 60))
    if stalled:
        rows = "\n".join(f"  - {_label(a)}｜靜默 {m:.1f} 分" for a, m in stalled)
        found["stall"] = f"最後一筆記錄距今 ≥ {cfg.stall_min:g} 分：\n{rows}"
    late = []
    for a in agents:
        began = _epoch(a.get("started_at"))
        if began is not None and now - began >= cfg.wall_min * 60:
            late.append((a, (now - began) / 60))
    if late:
        rows = "\n".join(f"  - {_label(a)}｜已跑 {m:.1f} 分" for a, m in late)
        found["overrun"] = f"自啟動起已 ≥ {cfg.wall_min:g} 分仍未交卷：\n{rows}"
    ref = started_at if kw_anchor is None else kw_anchor
    due = ref + cfg.keepwarm_min * 60 if kw_due is None else kw_due
    if kw_enabled and now >= due:
        kind = kw_verdict() if kw_verdict is not None else "keepwarm"
        if kind in ("keepwarm", "idle", "resume", "handed_over") or (kind and not agents):
            found[kind] = (f"距主控最後一筆記錄已 ≥ {cfg.keepwarm_min:g} 分"
                           "（主控快取壽命 1 小時，保溫點）") if kw_due is None else (
                f"主載具到預定叫醒時刻（{_stamp(due)}）")
    for name in ORDER:
        if name in found:
            return name, found[name]
    return None


def heartbeat_path(sid: str, pid: int | None = None) -> Path:
    """心跳檔：`trace_dir()/watch/<sid>.<pid>.json`（pid 化，W6-W2：各 watch 只動自己的檔）；
    `pid=None` 回舊格式 `<sid>.json`（只供讀端相容舊檔；唯一的路徑解析處）。"""
    name = f"{sid}.json" if pid is None else f"{sid}.{pid}.json"
    return endurance_env.trace_dir() / "watch" / name


def _stamp(epoch: float) -> str:
    return datetime.fromtimestamp(epoch).astimezone().isoformat(timespec="seconds")


def write_heartbeat(sid: str, cfg: Cfg, started_at: float, now: float, pid: int,
                    kw_anchor: float | None = None, kw_due: float | None = None) -> None:
    """每輪覆寫；時間戳帶 offset。不用 os.replace（非原子，同 `park.write_marker`／`quota_rush`）：
    讀端解析失敗一律當「讀不動」fail-open，不會因撕裂讀取而誤判。`keepwarm_at`＝保溫錨點
    （`kw_anchor`，量不到退回 `started_at`）＋保溫分鐘數；主載具有目標時（`kw_due`）＝排程的
    下一個叫醒時刻。"""
    ref = started_at if kw_anchor is None else kw_anchor
    nxt = ref + cfg.keepwarm_min * 60 if kw_due is None else kw_due
    row = {"schema": SCHEMA, "pid": pid, "started_at": _stamp(started_at),
           "heartbeat_at": _stamp(now), "keepwarm_at": _stamp(nxt),
           "stall_min": cfg.stall_min, "wall_min": cfg.wall_min, "ctx_max": cfg.ctx_max}
    try:
        path = heartbeat_path(sid, pid)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(row, ensure_ascii=False), encoding="utf-8", newline="\n")
    except OSError:
        pass


def _drop_heartbeat(sid: str, pid: int) -> None:
    try:
        heartbeat_path(sid, pid).unlink()
    except OSError:
        pass


def ended_turn(sid: str, agent_id: str, projects_dir=None) -> bool:
    """代理逐字稿最後一筆 user／assistant 記錄是 assistant 且 `stop_reason=="end_turn"`
    （只讀尾端）。讀不到 ⇒ False（不豁免，寧可多報 stall 也不漏）。"""
    path = roster._agent_path(sid, agent_id, projects_dir)
    last = None
    for rec in roster._records(path, tail=True) if path else ():
        if rec.get("type") in ("assistant", "user"):
            last = rec
    msg = last.get("message") if isinstance(last, dict) else None
    return (isinstance(last, dict) and last.get("type") == "assistant" and isinstance(msg, dict)
            and msg.get("stop_reason") == "end_turn")


def quota_keys_now(sid: str, transcript, env, now: float | None = None, plan=None,
                   read_quota=None) -> list[tuple]:
    """額度事件閂鎖鍵（單一判決序列，至多一把）；判準住 `watch_wake.quota_keys`（QVD C4）。"""
    return watch_wake.quota_keys(sid, transcript, env, now, plan, read_quota)


def _anchor_reader(sid: str, projects_dir):
    """每輪讀主控逐字稿尾端的保溫錨點；逐字稿路徑找到就快取（找不到每輪再找）。"""
    found: list[Path | None] = [None]

    def read() -> float | None:
        if found[0] is None:
            found[0] = keepwarm.find_transcript(sid, projects_dir)
        return keepwarm.anchor(found[0])
    return read


def _kw_resolver(budget, state: dict):
    """`decide` 的 `kw_verdict`：到保溫點才讀叫醒預算（讀逐字稿與帳不便宜，不每輪做）。結果依
    錨點快取——錨點沒變（主控沒動）時預算不會變，`cap`／`idle` 在代理還在跑的輪詢裡不重讀。"""
    def resolve() -> str:
        if "kind" not in state or state.get("anchor_key") != state.get("anchor"):
            why, pings, star, ctx = budget.check()
            state.update(why=why, pings=pings, star=star, ctx=ctx, anchor_key=state.get("anchor"),
                         kind="idle" if why else "cap" if pings >= star else "keepwarm")
        return state["kind"]
    return resolve


def run(sid: str, cfg: Cfg, *, now_fn=time.time, sleep_fn=time.sleep,
        poll_sec: float = POLL_SECONDS, roster_fn=None, end_turn_fn=None, quota_fn=None,
        out=None, pid: int | None = None, projects_dir=None, anchor_fn=None,
        budget=None, plan_fn=None, read_quota=None, refresh=None, env=None) -> int:
    """阻塞輪詢；第一個事件成立即印明細、處置表對應列、`WATCH_VERDICT=` 末行並回 rc。
    縫（全可注入）：now_fn()->epoch、sleep_fn(sec)、roster_fn()->未交卷代理 list、
    end_turn_fn(agent)->bool、quota_fn()->None｜(帶級, reset 分鐘)｜True（True＝無鍵的 prepare）、
    anchor_fn()->主控最後一筆 usage 記錄的 epoch｜None、budget＝叫醒預算（`keepwarm.WakeBudget`
    形狀：`check()`／`charge()`）、plan_fn(now)->額度牆 `Plan`、read_quota／refresh（短窗讀數與
    補量，餵預設的 plan_fn 與主載具計畫）。額度事件過閂鎖（`keepwarm.quota_latch`）：同 reset 窗
    同帶只觸發一次，之後該輪視為未命中；事件前印 `plan_lines`，處置依階段。

    叫醒預算（REQ-WP-30～32）：watch 持有保溫錨（`holder`）時才判保溫族；別的行程持有 ⇒ 每輪
    重試取得，取得前只看實質事件。`keepwarm` 事件才記一次叫醒（與 `keepwarm` 指令共用帳）；記不進
    帳 ⇒ 改判 `cap`（失效往少花走）。R218 Q2（REQ-QW-17／18／29）：額度牆 `wall` 階段不判任何事件、
    不記帳、只寫心跳；持錨者有目標（`wake_target`）時用同一份 schedule／牆內延後／resume／交棒重判
    （`watch_wake.WakeCtl`），無目標時照 R216 periodic。"""
    out, env = out or sys.stdout, os.environ if env is None else env
    roster_fn = roster_fn or (
        lambda: roster.snapshot(sid, projects_dir=projects_dir, full=False)["agents"])
    end_turn_fn = end_turn_fn or (lambda a: ended_turn(sid, str(a.get("id")), projects_dir))
    anchor_fn = anchor_fn or _anchor_reader(sid, projects_dir)
    budget = budget or keepwarm.WakeBudget(sid, projects_dir)
    found_tx: list = []

    def transcript():
        if not found_tx or found_tx[0] is None:
            found_tx[:] = [keepwarm.find_transcript(sid, projects_dir)]
        return found_tx[0]
    plan_fn = plan_fn or (lambda t: qw_plan.plan(
        sid, transcript(), env, datetime.fromtimestamp(t).astimezone(), read_quota=read_quota,
        refresh=refresh))
    plans = watch_wake.PlanCache(plan_fn)
    quota_fn = quota_fn or (lambda: quota_keys_now(sid, transcript(), env, now_fn(),
                                                   plans.get(now_fn()), read_quota))
    wctl = watch_wake.WakeCtl(sid, transcript, env, cfg, budget, anchor_fn, read_quota=read_quota,
                              refresh=refresh)
    pid = os.getpid() if pid is None else pid
    if not watchlock.acquire(sid, pid):  # 單例（DES §5）：同 sid 已有活 watch ⇒ 本支不跑
        print(f"處置：{DISPOSAL['duplicate']}\nWATCH_VERDICT=duplicate n=0", file=out, flush=True)
        switch.trace(EV_WATCH_VERDICT, sid=sid, verdict="duplicate", agents=0)
        watch_wake.due_suffix(sid, "duplicate", None, [])  # 另落 watch_duplicate 痕跡
        return 0
    started, latched, holding, state, band = now_fn(), False, False, {}, "NODISPATCH"
    tail = ""
    resolver = _kw_resolver(budget, state)
    try:
        while True:
            now = now_fn()
            agents = [dict(a) for a in roster_fn()]
            for a in agents:  # 只對靜默夠久者讀尾端（省 I/O）
                last = _epoch(a.get("last_at"))
                if last is not None and now - last >= cfg.stall_min * 60:
                    a["end_turn"] = bool(end_turn_fn(a))
            hit, anchor = quota_fn(), anchor_fn()
            state["anchor"] = anchor
            if not holding and holder.acquire(sid, pid):
                holding = True
                wctl.start(now, pid)
            if plans.get(now).stage == qw_plan.WALL:  # REQ-QW-18：牆中不判事件、不記帳、只寫心跳
                write_heartbeat(sid, cfg, started, now, pid, anchor, wctl.due())
                sleep_fn(poll_sec)
                continue
            quota_hit: bool | str = False
            hits = watch_wake.norm_hits(hit)
            if hits:  # 單一序列閂鎖 (acct, ACTION, win)（QVD C5）；在飛代理數 N 做新派工重判
                fired = watch_wake.fire_hits(sid, hits, getattr(plans.get(now), "n_live", None))
                if fired:
                    band = watch_wake.top_band(fired)
                    quota_hit = watch_wake.quota_detail(fired, plans.get(now))
                    tail = watch_wake.verdict_tail(fired)
                elif not latched:  # 同一個 run 只落一次痕跡，免得每輪洗版
                    latched = True
                    switch.trace(keepwarm.EV_QUOTA_LATCHED, sid=sid, band=watch_wake.top_band(hits),
                                 reset=hits[0][1])
            verdict = decide(agents, now, started, cfg, quota_hit, kw_anchor=anchor,
                             kw_enabled=holding, kw_due=wctl.due() if holding else None,
                             kw_verdict=lambda: wctl.classify(now, state, resolver))
            pend, verdict = watch_wake.due_merge(sid, transcript(), agents, env, verdict,
                                                 KEEPWARM_FAMILY)  # DES §7.4 switch_due
            if verdict is not None:
                event, detail = verdict
                extra: dict = {}
                if event == "quota":
                    print("\n".join(qw_plan.plan_lines(plans.get(now, force=True))), file=out)
                elif event in KEEPWARM_FAMILY:
                    extra = {"pings": state["pings"], "n_star": state["star"]}
                    if wctl.settle(event, now, state) != event:
                        event, detail = "cap", "叫醒帳寫不進去 ⇒ 不再保溫（失效往少花走）"
                elif event == "resume":
                    wctl.settle(event, now, state)
                    wctl.trace_early(now, state)
                print(f"[{_stamp(now)}] {event}：{detail}", file=out)
                how = DISPOSAL[event]
                if event == "quota":
                    how = watch_wake.quota_disposal(band) or how
                print(f"處置：{how}", file=out)
                out.write(cutvoice.watch_text(agents, sid, transcript(), projects_dir))  # CTL-20
                out.write(watch_wake.due_suffix(sid, event, pend, agents))  # 待換逾期字尾
                switch.trace(EV_WATCH_VERDICT, sid=sid, verdict=event, agents=len(agents), **extra)
                tail = tail if event == "quota" else ""
                print(f"WATCH_VERDICT={event}{tail} n={len(agents)}", file=out, flush=True)
                return 0
            write_heartbeat(sid, cfg, started, now, pid, anchor, wctl.due() if holding else None)
            sleep_fn(poll_sec)
    finally:
        _drop_heartbeat(sid, pid)
        holder.release(sid, pid)
        watchlock.release(sid, pid)

def cli(argv: list[str]) -> int:
    import argparse  # noqa: PLC0415

    ap = argparse.ArgumentParser(prog="sessionctl watch")
    ap.add_argument("--sid")
    ap.add_argument("--stall-min", type=float)
    ap.add_argument("--wall-min", type=float)
    ap.add_argument("--ctx-max", type=int)
    ap.add_argument("--poll-sec", type=float, default=POLL_SECONDS)
    ap.add_argument("--projects-dir", help="逐字稿根目錄（預設＝Claude home 的 projects；測試用）")
    args = ap.parse_args(argv)
    sid = args.sid or os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    if not sid:
        print("sessionctl watch：缺 --sid，且環境變數 CLAUDE_CODE_SESSION_ID 未設 "
              "⇒ 無法判定要看管哪個 session", file=sys.stderr)
        return 2
    cfg = resolve_cfg(stall_min=args.stall_min, wall_min=args.wall_min, ctx_max=args.ctx_max)
    return run(sid, cfg, poll_sec=args.poll_sec, projects_dir=args.projects_dir)
