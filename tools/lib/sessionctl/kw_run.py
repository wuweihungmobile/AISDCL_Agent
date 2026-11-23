"""`sessionctl keepwarm` 指令本體（R218 Q2；DES §5）：session 內背景等待＝主載具。

自 `keepwarm.py` 抽出（LOC 分級；`keepwarm.run` 是委派本檔的薄殼）。阻塞到叫醒時刻才結束，一律
rc 0、判決看末行 `KEEPWARM_VERDICT=`（DEF-200-622）。啟動時印首行
`KEEPWARM_PLAN mode=… wake_at=… k=… target_source=… early=…`（D-K 憑證之一），holder 列同步寫
`wake_at`／`mode`／`target_source`（只呼叫 `holder.acquire(extra=)`）。有目標（`wake_target`）時
`no_usage`／`small_ctx`／付不起都退成「單跳到目標、零付費」，不是不掛（D-C、REQ-QW-21）。
牆鐘輪詢：每輪 `sleep(min(POLL, due−now))`，`now` 取牆鐘 epoch，凍結／睡眠跨過截止後一輪內結束。
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path

from . import holder, kw_ledger, kw_wake, qw_calc, qw_schema, roster, seal, switch


def _stamp(epoch: float) -> str:
    return datetime.fromtimestamp(epoch).astimezone().isoformat(timespec="seconds")


def mark_resumed_if_owner(sid: str, env) -> bool:
    """DES §8 觸發 1：判 `resume` 且本 sid 最新包 live ∧ 已封存 ∧ 未交棒 ⇒ 記續跑（作廢封存）。"""
    try:
        row = seal.latest_package(sid, env)
        if (row is None or row["state"] != "live" or not seal.sealed_path(row["path"]).exists()
                or seal.handed_over(sid, env) is not None):
            return False
        return seal.mark_resumed(row["path"])
    except Exception:  # noqa: BLE001 — 記續跑失敗不得影響叫醒本身
        return False


def run(sid: str, transcript, *, t_kw_min: float, env=None, now_fn=time.time, sleep_fn=time.sleep,
        poll_sec: float | None = None, out=None, pid: int | None = None,
        idle_min: float | None = None, heartbeat_min: float | None = None, read_quota=None,
        refresh=None, platform_name: str | None = None) -> int:
    """見檔頭。縫（全可注入，不開任何測試用環境變數）：`now_fn`／`sleep_fn`／`read_quota`
    （短窗讀數）／`refresh`（補量）／`platform_name`（darwin 心跳與 `backup=absent(platform)`）。"""
    from . import keepwarm  # noqa: PLC0415

    env, out = os.environ if env is None else env, out or sys.stdout
    poll = keepwarm.POLL_SECONDS if poll_sec is None else poll_sec
    plat = sys.platform if platform_name is None else platform_name
    idle = qw_calc.IDLE_LIMIT_MIN if idle_min is None else min(idle_min, qw_calc.IDLE_LIMIT_MIN)

    def finish(verdict: str, tail: str, detail: str, **fields) -> int:
        print(f"[{_stamp(now_fn())}] {verdict}：{detail}", file=out)
        print(f"處置：{keepwarm.DISPOSAL[verdict]}", file=out)
        switch.trace(keepwarm.EV_VERDICT, sid=sid, verdict=verdict, **fields)
        print(f"KEEPWARM_VERDICT={verdict} {tail}".rstrip(), file=out, flush=True)
        return 0

    ctx = roster._scan(Path(transcript), False)["ctx_tokens"] if transcript is not None else None
    why = "no_transcript" if transcript is None else keepwarm.skip_reason(sid, env, ctx=ctx)
    if why and (why in kw_wake.HARD_SKIPS or why == "no_transcript"):
        return finish("skip", f"reason={why}", f"不掛保溫（{why}）", reason=why)
    car = kw_wake.begin(sid, transcript, env, now_fn(), t_kw_min, idle, soft=why,
                        read_quota=read_quota, refresh=refresh)
    if why and car.periodic:  # no_usage／small_ctx 且沒有目標：沒有東西值得等
        return finish("skip", f"reason={why}", f"不掛保溫（{why}）", reason=why)
    row, star = kw_ledger.load_ledger(sid, transcript), keepwarm.n_star(ctx)
    if car.periodic and row["pings"] >= star:
        return finish("cap", f"k={star}", f"保溫帳已達上限 {star} 次", k=star, n_star=star)
    me = os.getpid() if pid is None else pid
    due = kw_wake.next_due(car)
    # REQ-WP-31：同 sid 只准一個保溫持有者（watch 或另一個 keepwarm）；活著的別人持有 ⇒ 立即結束
    if not holder.acquire(sid, me, extra=kw_wake.holder_extra(car, due)):
        return finish("skip", "reason=holder_running",
                      "同一 sid 已有保溫持有者（watch 或 keepwarm）在叫醒，不重複叫醒",
                      reason="holder_running")
    try:
        f = kw_wake.plan_fields(car, due)
        print(f"KEEPWARM_PLAN mode={f['mode']} wake_at="
              f"{'none' if f['when'] is None else qw_schema.iso(f['when'])} k={f['k']} "
              f"target_source={f['source']} early={f['early']}"
              + ("" if plat == "win32" else " backup=absent(platform)"), file=out, flush=True)
        beat_every = min(heartbeat_min or qw_calc.MAC_HEARTBEAT_MIN, qw_calc.MAC_HEARTBEAT_MIN) * 60
        beat_at = now_fn()
        while True:
            due, now = kw_wake.next_due(car), now_fn()
            if due is None:
                return finish("skip", "reason=no_usage", "逐字稿尾端找不到帶 usage 的記錄",
                              reason="no_usage")
            oc = None
            if now >= due:
                oc = kw_wake.at_due(car, now, due)
                if oc.kind == "defer":
                    switch.trace(kw_wake.EV_DEFER, sid=sid, reason=oc.detail, wake_at=car.target)
                    print(f"KEEPWARM_DEFER wake_at={qw_schema.iso(car.target)} {oc.detail}",
                          file=out, flush=True)
                    holder.acquire(sid, me, extra=kw_wake.holder_extra(car, due))
                    continue
            else:
                oc = kw_wake.poll_early(car, now)
            if oc is not None and oc.kind not in ("wait", "defer"):
                break
            if plat == "darwin" and now - beat_at >= beat_every:
                beat_at = now
                print(f"KEEPWARM_HEARTBEAT {_stamp(now)}", file=out, flush=True)
            # 已過截止卻還不能結束（牆內 reset 不明）⇒ 睡一整輪再判，不得空轉
            sleep_fn(poll if now >= due else max(min(poll, due - now), 0.0))
        return _conclude(sid, transcript, env, car, oc, now_fn(), finish, ctx)
    finally:
        holder.release(sid, me)


def _conclude(sid, transcript, env, car, oc, now, finish, ctx0) -> int:
    from . import keepwarm  # noqa: PLC0415

    ctx = roster._scan(Path(transcript), False)["ctx_tokens"] or ctx0
    if oc.kind == "handed_over":  # 不計 pings、不呼叫 mark_resumed（S-13）
        return finish("handed_over", "", oc.detail, reason="handed_over")
    if oc.kind in ("early", "resume"):  # 視窗翻新：帳歸零、記原主人續跑（DES §8 觸發 1）
        if oc.kind == "early":
            switch.trace(kw_wake.EV_EARLY_RESET, sid=sid, reset=getattr(oc.plan, "reset", None))
        kw_ledger.clear(sid, transcript, ctx, keepwarm.n_star(ctx))
        resumed = mark_resumed_if_owner(sid, env)
        return finish("resume", "", oc.detail, source=car.source, early=oc.kind == "early",
                      resumed=resumed)
    star, row = keepwarm.n_star(ctx), kw_ledger.load_ledger(sid, transcript)
    k = row["pings"] + 1
    last, costs, last_reset = kw_wake.ping_cost(sid, row, oc.plan, now, transcript=transcript)
    saved = kw_ledger.record_ping(sid, k, ctx, star, kw_ledger.human_mark(transcript),
                                  work=kw_ledger.work_mark(transcript), last=last, costs=costs,
                                  last_reset=last_reset)
    if (car.periodic and k >= star) or not saved:
        return finish("cap", f"k={star}", f"第 {k} 次、上限 {star}（寫帳成功＝{saved}）",
                      k=k, n_star=star, ctx=ctx)
    return finish("ping", f"k={k} n={star}",
                  f"距主控最後一筆記錄已 ≥ {car.t_kw:g} 分，第 {k}／{star} 次",
                  k=k, n_star=star, ctx=ctx)
