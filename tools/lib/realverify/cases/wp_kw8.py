# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""RV-KW8（long）：保溫真的保住快取（E2E-SS-04／E2E-WP-10）。由 OIR 驅動器（E1②）跑，不縮參數代跑。

載具：兩個沙盒 A（輕觸組）與 B（對照組）各一個真 `claude -p --model haiku` session（同樣的大前綴）。
時間軸（1 小時快取層，實測 2026-11-20 `-p` 的 usage 為 `ephemeral_1h_input_tokens`）：
  t0 兩組建立；t0＋45 分 A 輕觸（`-r`）；t0＋70 分 B 才第一次 `-r`（>60 分 ⇒ 快取應已過期）；
  t0＋100 分 A 第三次回合（距上次輕觸 55 分 <60 ⇒ 快取應命中）。
斷言：A 第三次 `cache_read ≥ 0.9×` 前一回合上下文；B 的 t0＋70 回合 `cache_read < 0.1×` 前一回合上下文。
層別：首回合 usage 若非 1h 層（`ephemeral_5m_input_tokens` > 0 且 1h＝0），改量 5m 版（輕觸 t0＋4、
再 t0＋8；對照 t0＋7）。各段實際等待秒數寫進證據 `waits_seconds`，供驅動器對 `DESIGNED_WAIT_SECONDS` 核對。
"""  # noqa: E501

from __future__ import annotations

import time

from . import CaseContext, case
from .prd_px_lib import ev

MIN_WALL_SECONDS = 6000
DESIGNED_WAIT_SECONDS = 6000  # 45 分 ＋ 55 分（對照組 t0＋70 分夾在其中，不另加）
# WHY：同 wp_kw9——逾時牆取宣告值最大者，只宣告設計等待秒數＝案例必在牆之後才收尾。WALL_SECONDS 為真上限（餘裕 20 分）。
WALL_SECONDS = DESIGNED_WAIT_SECONDS + 20 * 60

FILLER = "Reference text, remember it. " + " ".join(f"alpha{i} bravo{i} charlie{i}" for i in range(900))


def last_usage(tr) -> dict:
    last = None
    for r in tr.recs:
        m = r.data.get("message")
        if r.data.get("type") == "assistant" and isinstance(m, dict) and isinstance(m.get("usage"), dict) and m.get("model") != "<synthetic>":  # noqa: E501
            last = m["usage"]
    if last is None:
        raise AssertionError("逐字稿沒有帶 usage 的 assistant 記錄")
    return last


def ctx_tokens(u: dict) -> int:
    return int(u.get("input_tokens", 0)) + int(u.get("cache_creation_input_tokens", 0)) + int(u.get("cache_read_input_tokens", 0))  # noqa: E501


def tier_of(u: dict) -> str:
    cc = u.get("cache_creation") or {}
    return "1h" if int(cc.get("ephemeral_1h_input_tokens", 0)) > 0 or not int(cc.get("ephemeral_5m_input_tokens", 0)) else "5m"  # noqa: E501


def sleep_until(t_abs: float, waits: list[float]) -> None:
    t0 = time.monotonic()
    while time.monotonic() < t_abs:
        time.sleep(min(30.0, max(0.0, t_abs - time.monotonic())))
    waits.append(time.monotonic() - t0)


@case("RV-KW8", "workprogress", refs=("E2E-WP-10", "REQ-WP-45", "E2E-SS-04"), long=True)
def rv_kw8(ctx: CaseContext) -> None:
    a, b = ctx.sandbox(probe_hooks=False), ctx.sandbox(probe_hooks=False)
    for sb in (a, b):
        r = ctx.run_claude(sb, FILLER + "\nReply with exactly: ok")
        ctx.check(r.rc == 0, f"建立 session rc={r.rc} {r.stderr[:200]}")
    t0 = time.monotonic()
    u0 = last_usage(ctx.transcript(a))
    tier = tier_of(u0)
    ctx.check(ctx_tokens(u0) >= 4096, f"上下文不足 4,096：{ctx_tokens(u0)}")
    touch, control, third = (45 * 60, 70 * 60, 100 * 60) if tier == "1h" else (4 * 60, 7 * 60, 8 * 60)
    waits: list[float] = []
    sleep_until(t0 + touch, waits)
    r1 = ctx.run_claude(a, "Reply with exactly: ok", resume=True)
    ctx.check(r1.rc == 0, f"輕觸 rc={r1.rc}")
    sleep_until(t0 + control, waits)
    rb = ctx.run_claude(b, "Reply with exactly: ok", resume=True)
    ctx.check(rb.rc == 0, f"對照組 rc={rb.rc}")
    ub, ub_prev = last_usage(ctx.transcript(b)), u0  # B 前一回合上下文＝t0 的上下文量級
    prev_b = ctx_tokens(ub_prev)
    ctx.check(int(ub.get("cache_read_input_tokens", 0)) < 0.1 * prev_b, f"對照組（{control // 60} 分未輕觸）cache_read 應 <10%：{ub.get('cache_read_input_tokens')}／{prev_b}")  # noqa: E501
    u1 = last_usage(ctx.transcript(a))
    sleep_until(t0 + third, waits)
    r3 = ctx.run_claude(a, "Reply with exactly: ok", resume=True)
    ctx.check(r3.rc == 0, f"第三次回合 rc={r3.rc}")
    u3 = last_usage(ctx.transcript(a))
    prev_a = ctx_tokens(u1)
    ctx.check(int(u3.get("cache_read_input_tokens", 0)) >= 0.9 * prev_a, f"輕觸組第三次 cache_read 應 ≥90%：{u3.get('cache_read_input_tokens')}／{prev_a}")  # noqa: E501
    ev(ctx, "tier", tier)
    ev(ctx, "touched_cache_read", f"{u3.get('cache_read_input_tokens')}／前一回合 {prev_a}＝{int(u3.get('cache_read_input_tokens', 0)) / prev_a:.2f}")  # noqa: E501
    ev(ctx, "control_cache_read", f"{ub.get('cache_read_input_tokens')}／{prev_b}＝{int(ub.get('cache_read_input_tokens', 0)) / prev_b:.2f}")  # noqa: E501
    ev(ctx, "waits_seconds", f"{sum(waits):.0f}（{[round(w) for w in waits]}）")
