# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""RV-SK1（KIND="soak"，由 OIR 驅動器走 soak 通道；真牆鐘＋真 schtasks 哨兵，不縮參數代跑）。"""  # noqa: E501

from __future__ import annotations

import time

from . import CaseContext, case
from .prd_px_lib import ev
from .sentinel import arm, task_name
from .sessionctl_park import (
    axis,
    claude_procs,
    get_task,
    install_tools,
    park_cleanup,
    seed_session,
    write_quota,
)
from .wp_soak import SENTINEL_INTERVAL_S, real_log_events, touch_alive

KIND = "soak"
MIN_WALL_SECONDS = 21_600
DESIGNED_WAIT_SECONDS = 21_600
SECS = 21_600
# WHY：驅動器逾時牆＝宣告值最大者。只宣告 SECS 時案例在 t0＋SECS（外加建立 session、武裝、最後一次 60 秒取樣）
# 才收尾，必晚於牆被 `subprocess.run(timeout)` 殺掉（rc 124、finally 不跑 ⇒ 哨兵排程 `AutoSDD_Sentinel_<沙盒 sid>`
# 與沙盒目錄遺留）。WALL_SECONDS 是真上限，餘裕 30 分（設計等待本身不縮）。
WALL_SECONDS = SECS + 30 * 60


@case("RV-SK1", "workprogress", refs=("E2E-WP-57", "REQ-WP-87", "§11.1"), sched=True, long=True)
def rv_sk1(ctx: CaseContext) -> None:
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    write_quota(sb, [axis("five_hour", 5, 240), axis("seven_day", 5, 5 * 1440)])
    secs = SECS
    with park_cleanup(sb):
        tp = seed_session(ctx, sb)
        arm(ctx, sb, tp)
        t = get_task(task_name(sb))
        ctx.check(t is not None and bool(t["next_run_time"]), f"哨兵排程不在或無 NextRunTime：{t}")
        t0 = time.monotonic()
        last_alive, spawned = t0, []
        n_records0 = len(tp.read_text(encoding="utf-8").splitlines())
        while time.monotonic() - t0 < secs:
            time.sleep(60)
            if claude_procs(sb.sid):
                spawned += [p["pid"] for p in claude_procs(sb.sid)]
            if time.monotonic() - last_alive >= 3600:
                touch_alive(tp)
                last_alive = time.monotonic()
        wall = time.monotonic() - t0
        evs = real_log_events(sb.sid)
        woken = [e for e in evs if e.get("event") == "sentinel_woken"]
        need = int(secs / SENTINEL_INTERVAL_S) - 1
        ctx.check(len(woken) >= need, f"巡邏 tick 數 {len(woken)} < {need}（6h÷{SENTINEL_INTERVAL_S}s−1）；事件={sorted({e.get('event') for e in evs})}")  # noqa: E501
        ctx.check(not spawned, f"期間出現含沙盒 sid 的 claude 行程：{spawned}")
        paid = [e for e in evs if e.get("event") in ("probed", "route_chosen", "resumed") or e.get("action") == "probe"]
        ctx.check(not paid, f"痕跡有付費探針／續跑記錄：{paid[:2]}")
        recs = tp.read_text(encoding="utf-8").splitlines()
        real_new = [ln for ln in recs[n_records0:] if "keepalive" not in ln]
        ctx.check(not real_new, "沙盒逐字稿出現非保活的新記錄（有人花了 token？）")
        ev(ctx, "patrol_ticks", f"sentinel_woken={len(woken)}（≥{need}）wall={wall:.0f}s")
        ev(ctx, "claude_spawned", "0（每 60 秒取樣含沙盒 sid 的 claude 行程）")
        ev(ctx, "no_paid_probe", f"痕跡 {len(evs)} 筆無 probed／route_chosen／resumed")
        ev(ctx, "waits_seconds", f"{wall:.0f}")


