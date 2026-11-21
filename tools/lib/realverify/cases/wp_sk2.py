# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""RV-SK2（KIND="soak"，由 OIR 驅動器走 soak 通道；真牆鐘＋真 schtasks 哨兵，不縮參數代跑）。"""  # noqa: E501

from __future__ import annotations

import json
import time
from datetime import datetime

from . import CaseContext, case
from .prd_px_lib import ev
from .prd_px_wake import limit_text, reset_in
from .sentinel import append_limit_event, arm
from .sessionctl_park import (
    axis,
    install_tools,
    park_cleanup,
    seed_session,
    write_quota,
)
from .wp_soak import SENTINEL_INTERVAL_S, real_log_events

KIND = "soak"
MIN_WALL_SECONDS = 86_400
DESIGNED_WAIT_SECONDS = 86_400
SECS = 86_400
# WHY：同 wp_sk1——逾時牆取宣告值最大者，只宣告 SECS 則案例必在牆之後才收尾（rc 124、哨兵排程與沙盒遺留）。
# WALL_SECONDS 為真上限，餘裕 60 分（設計等待本身不縮）。
WALL_SECONDS = SECS + 60 * 60


@case("RV-SK2", "workprogress", refs=("E2E-WP-58", "REQ-WP-88", "§11.8"), sched=True, long=True)
def rv_sk2(ctx: CaseContext) -> None:
    """每約 5 小時注入一筆真格式撞線記錄（reset＝now＋3～4 分），真哨兵＋真 schtasks 在 reset 後以
    `claude -p -r --model haiku` 續跑；4 次續跑都在原逐字稿寫出新的 assistant 記錄，且每次距 reset ≤ 一個巡邏間隔。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    # WHY：排程器叫起的 tick 吃的是機器環境，不是本案例的子行程環境（`AUTOSDD_MODEL_*` 傳不過去）；沙盒副本的
    # `quota_env_layers` 以自己的根讀 `.env`，所以把模型角色寫進沙盒 `.env`，續跑與付費探針才確定是 haiku
    # （否則 4 次真續跑落在使用者預設模型）。`.env` 排除出 git，免得動到沙盒工作樹乾淨判準。
    (sb.root / ".env").write_text("AUTOSDD_MODEL_HELMSMAN=haiku\nAUTOSDD_MODEL_SUBAGENT=haiku\nAUTOSDD_MODEL_DOWNGRADE=haiku\n", encoding="utf-8", newline="\n")
    with (sb.root / ".git" / "info" / "exclude").open("a", encoding="utf-8", newline="\n") as fh:
        fh.write("\n.env\n")
    write_quota(sb, [axis("five_hour", 5, 240), axis("seven_day", 5, 5 * 1440)])
    secs, cycles = SECS, 4
    with park_cleanup(sb):
        tp = seed_session(ctx, sb)
        arm(ctx, sb, tp)
        t0 = time.monotonic()
        gaps, resumed_after = [], []
        for i in range(cycles):
            due = t0 + i * (secs / cycles)
            while time.monotonic() < due:
                time.sleep(30)
            reset = reset_in(3)
            n0 = len(tp.read_text(encoding="utf-8").splitlines())
            append_limit_event(tp, datetime.now().astimezone(), limit_text(reset))

            def new_assistant() -> datetime | None:
                for ln in tp.read_text(encoding="utf-8", errors="replace").splitlines()[n0:]:
                    try:
                        d = json.loads(ln)
                    except ValueError:
                        continue
                    m = d.get("message") if isinstance(d, dict) else None
                    if d.get("type") == "assistant" and isinstance(m, dict) and m.get("model") != "<synthetic>":
                        return datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00"))
                return None

            deadline = time.monotonic() + (3 + 25) * 60
            got = None
            while time.monotonic() < deadline and got is None:
                time.sleep(20)
                got = new_assistant()
            ctx.check(got is not None, f"第 {i + 1} 次 reset 後 {28} 分內逐字稿沒有續跑寫出的新 assistant 記錄（哨兵沒續跑？）；事件={sorted({e.get('event') for e in real_log_events(sb.sid)})}")  # noqa: E501
            gap = (got - reset.astimezone()).total_seconds()
            ctx.check(gap <= SENTINEL_INTERVAL_S, f"第 {i + 1} 次續跑距 reset {gap:.0f}s > 一個巡邏間隔 {SENTINEL_INTERVAL_S}s")
            gaps.append(gap)
            resumed_after.append(got.isoformat(timespec="seconds"))
        while time.monotonic() - t0 < secs:
            time.sleep(30)
        ev(ctx, "resumes_written", f"{len(gaps)} 次續跑皆寫出新 assistant 記錄：{resumed_after}")
        ev(ctx, "gap_within_interval", f"各次距 reset 秒數={[round(g) for g in gaps]}（≤{SENTINEL_INTERVAL_S}）")
        ev(ctx, "waits_seconds", f"{time.monotonic() - t0:.0f}")
