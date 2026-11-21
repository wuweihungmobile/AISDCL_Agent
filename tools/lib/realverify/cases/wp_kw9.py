# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""RV-KW9（long；V-SS1／E2E-WP-11）：閒置 3 小時每 45 分輕觸一次，快取持續命中、無壓縮。由 OIR 驅動器跑，不縮參數代跑。

載具：一個沙盒真 `claude -p --model haiku` session（大前綴）；t0 之後每 45 分以 `-r` 輕觸（共 4 次，共 3 小時）。
斷言：每次輕觸 `cache_read ≥ 0.9×` 前一回合上下文；逐字稿全程沒有 `compact_boundary`。
層別：首回合 usage 非 1h 層時改量 5m 版（每 4 分輕觸 4 次）；各段實際等待秒數寫進證據 `waits_seconds`。
"""

from __future__ import annotations

import time

from . import CaseContext, case
from .prd_px_lib import ev
from .wp_kw8 import FILLER, ctx_tokens, last_usage, sleep_until, tier_of

KIND = "long"
MIN_WALL_SECONDS = 10_800
DESIGNED_WAIT_SECONDS = 10_800  # 4 次 × 45 分
# WHY：驅動器的逾時牆＝宣告值最大者；只宣告設計等待秒數時，案例在 t0＋設計等待之後才收尾（外加建立 session 與
# 最後一回合的時間）⇒ 結構上永遠晚於牆被殺（rc 124、finally 不跑）。WALL_SECONDS 是真上限，留 20 分餘裕。
WALL_SECONDS = DESIGNED_WAIT_SECONDS + 20 * 60


@case("RV-KW9", "workprogress", refs=("E2E-WP-11", "REQ-WP-46", "V-SS1"), long=True)
def rv_kw9(ctx: CaseContext) -> None:
    sb = ctx.sandbox(probe_hooks=False)
    r = ctx.run_claude(sb, FILLER + "\nReply with exactly: ok")
    ctx.check(r.rc == 0, f"建立 session rc={r.rc} {r.stderr[:200]}")
    # WHY（2026-11-21 實測，同 RV-W6）：新 session 第一回合與第一次 `-r` 回合的提示前綴渲染不同，緊接著 `-r`
    # 也只讀到約 69%，第二次 `-r` 起才約 100%。先做一個 `-r` 暖身回合，輕觸基線才是同形態，否則第 1 次輕觸必敗。
    rw = ctx.run_claude(sb, "Reply with exactly: ok", resume=True)
    ctx.check(rw.rc == 0, f"暖身 `-r` 回合 rc={rw.rc} {rw.stderr[:200]}")
    t0 = time.monotonic()
    tier = tier_of(last_usage(ctx.transcript(sb)))
    step = 45 * 60 if tier == "1h" else 4 * 60
    waits: list[float] = []
    ratios = []
    for i in range(1, 5):
        prev = ctx_tokens(last_usage(ctx.transcript(sb)))
        sleep_until(t0 + i * step, waits)
        rr = ctx.run_claude(sb, "Reply with exactly: ok", resume=True)
        ctx.check(rr.rc == 0, f"第 {i} 次輕觸 rc={rr.rc} {rr.stderr[:200]}")
        u = last_usage(ctx.transcript(sb))
        cr = int(u.get("cache_read_input_tokens", 0))
        ctx.check(cr >= 0.9 * prev, f"第 {i} 次輕觸 cache_read {cr} < 90%×前一回合 {prev}")
        ratios.append(round(cr / prev, 2))
    tr = ctx.transcript(sb)
    ctx.check(not tr.compact_boundaries(), "逐字稿出現 compact_boundary（保溫沒擋住壓縮）")
    ev(ctx, "cache_hits", f"tier={tier} 四次輕觸 cache_read／前一回合＝{ratios}")
    ev(ctx, "no_compact_boundary", f"逐字稿 {len(tr.recs)} 筆記錄無 compact_boundary")
    ev(ctx, "waits_seconds", f"{sum(waits):.0f}（{[round(w) for w in waits]}）")
