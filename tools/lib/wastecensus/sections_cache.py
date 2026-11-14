"""1／2／4 節：快取重寫、壽命邊界與喚醒鏈的人讀輸出與 jsonl 列。

每節吃同一個 `cx`（見 `report.main`），輸出文字與原探針逐字相同。
"""
from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from types import SimpleNamespace

from .annotate import chains, units
from .metrics import fmt_pct, median, rewrite_rows
from .reader import CTX_BUCKETS, GAP_BUCKETS, W_CC1, W_CC5, bucket, iso


def sec_rewrites(cx: SimpleNamespace) -> None:
    """1／2 快取重寫、壽命邊界與起因分類。"""
    rows, rank, all_main_turns, all_sub_turns = (
        cx.rows,
        cx.rank,
        cx.all_main_turns,
        cx.all_sub_turns,
    )
    # ---- 1／2 快取重寫 -------------------------------------------------------------
    print("\n== 1 快取重寫（prev ctx>=30k 且 cache_read 不足前一回合上下文的 50%；排除壓縮後） ==")
    for label, ts in (("主控", all_main_turns), ("子代理", all_sub_turns)):
        rw = [x for x in ts if x["rewrite"]]
        rwt = sum(x["rewrite_tokens"] for x in rw)
        rwu = sum(x["rewrite_tokens"] * (W_CC1 if x["tier"] == "1h" else W_CC5) for x in rw)
        base_u = sum(units(x) for x in ts)
        print(
            f"{label}：事件 {len(rw)}／重寫 token {rwt:,}（占該軸 cache_creation 總量 "
            f"{fmt_pct(rwt, sum(x['cc'] for x in ts))}；占加權單位 {fmt_pct(rwu, base_u)}）"
        )
        for tr in ("1h", "5m", "mixed", None):
            sub = [x for x in rw if x["tier"] == tr]
            if sub:
                gaps = sorted(x["gap"] for x in sub if x["gap"] is not None)
                print(
                    f"   TTL={tr}: {len(sub)} 件，重寫 {sum(x['rewrite_tokens'] for x in sub):,} "
                    "tok；"
                    f"間隔 中位 {median(gaps) and round(median(gaps) / 60, 1)} 分／最小 "
                    f"{gaps and round(gaps[0] / 60, 1)} 分"
                )
        rows += rewrite_rows(label, ts)
    print("\n   重寫事件按「間隔桶」（主控）：")
    mrw = [x for x in all_main_turns if x["rewrite"]]
    cnt = Counter(bucket(x["gap"], GAP_BUCKETS) for x in mrw if x["gap"] is not None)
    tok = Counter()
    for x in mrw:
        if x["gap"] is not None:
            tok[bucket(x["gap"], GAP_BUCKETS)] += x["rewrite_tokens"]
    for _lo, _hi, name in GAP_BUCKETS:
        if cnt[name]:
            print(f"     {name:>7}: {cnt[name]:4d} 件 {tok[name]:>12,} tok")

    # ---- 快取壽命邊界 --------------------------------------------------------------
    print("\n== 快取壽命邊界：prefix_hit＝cache_read／前一回合上下文（>=20k），按 TTL 與間隔桶 ==")
    for label, ts in (("主控", all_main_turns), ("子代理", all_sub_turns)):
        for tr in ("1h", "5m"):
            sub = [
                x
                for x in ts
                if x["tier"] == tr
                and x["prefix_hit"] is not None
                and x["gap"] is not None
                and x["cause"] != "compaction"
            ]
            if not sub:
                continue
            print(f"{label} TTL={tr}（n={len(sub)}）")
            for _lo, _hi, name in GAP_BUCKETS:
                b = [x["prefix_hit"] for x in sub if bucket(x["gap"], GAP_BUCKETS) == name]
                if b:
                    miss = sum(1 for v in b if v < 0.5)
                    print(
                        f"     {name:>7}: n={len(b):5d} 中位命中 {statistics.median(b):.2f} "
                        f"失效(<0.5) {miss} ({fmt_pct(miss, len(b))})"
                    )
            rows.append(
                {
                    "kind": "cache_ttl_curve",
                    "axis": label,
                    "tier": tr,
                    "n": len(sub),
                    "buckets": {
                        name: [
                            x["prefix_hit"] for x in sub if bucket(x["gap"], GAP_BUCKETS) == name
                        ].__len__()
                        for _a, _b, name in GAP_BUCKETS
                    },
                }
            )

    print("\n   邊界精確值（間隔含本則首 token 延遲；hit>=0.9 視為命中、<0.1 視為失效）：")
    for label, ts in (("主控", all_main_turns), ("子代理", all_sub_turns)):
        for tr in ("1h", "5m"):
            sub = [
                x
                for x in ts
                if x["tier"] == tr
                and x["prefix_hit"] is not None
                and x["gap"] is not None
                and x["cause"] != "compaction"
            ]
            hits = [x for x in sub if x["prefix_hit"] >= 0.9]
            miss = [x for x in sub if x["prefix_hit"] < 0.1]
            if hits and miss:
                ttl = 300 if tr == "5m" else 3600
                print(
                    f"     {label} TTL={tr}：命中的最大間隔 {max(x['gap'] for x in hits) / 60:.1f} "
                    "分；"
                    f"失效的最小間隔 {min(x['gap'] for x in miss) / 60:.1f} 分；"
                    f"間隔>{ttl // 60}分者 {sum(1 for x in sub if x['gap'] > ttl)} 件中失效 "
                    f"{sum(1 for x in miss if x['gap'] > ttl)}；間隔<={ttl // 60}分者 "
                    f"{sum(1 for x in sub if x['gap'] <= ttl)} 件中失效 "
                    f"{sum(1 for x in miss if x['gap'] <= ttl)}"
                )
    early = [
        x for x in all_main_turns if x["rewrite"] and x["gap"] is not None and x["gap"] <= 3300
    ]
    print(
        f"   主控在 TTL 內仍重寫的事件 {len(early)} 件（非閒置過期；"
        f"起因={dict(Counter(x['cause'] for x in early))}）："
    )
    for x in early:
        print(
            f"     {x['sid'][:8]} {iso(x['ts_first'])} 間隔 {x['gap'] / 60:.1f} 分 prev_ctx "
            f"{x['prev_ctx']:,} cc {x['cc']:,} 起因 {x['cause']}"
        )

    # ---- 2 起因分類 ----------------------------------------------------------------
    print("\n== 2 重寫事件的起因（主控）==")
    by_cause = defaultdict(lambda: [0, 0, 0.0])
    for x in mrw:
        c = by_cause[x["cause"]]
        c[0] += 1
        c[1] += x["rewrite_tokens"]
        c[2] += x["rewrite_tokens"] * (W_CC1 if x["tier"] == "1h" else W_CC5)
    tot_rw = sum(v[1] for v in by_cause.values())
    for cause, (n, tk, un) in sorted(by_cause.items(), key=lambda kv: -kv[1][1]):
        print(f"   {cause:18s} {n:4d} 件 {tk:>12,} tok（{fmt_pct(tk, tot_rw)}）")
    print("   重寫前一回合結束狀態（主控）：", dict(Counter(x.get("prev_stop") for x in mrw)))
    srw = [x for x in all_sub_turns if x["rewrite"]]
    hand = [x for x in srw if (x.get("prev_tools") or [""])[-1] == "SubagentHandback"]
    other = [x for x in srw if x not in hand]
    rank.append(
        (
            "主控：閒置超過 TTL 後整份重寫",
            len(mrw),
            sum(x["rewrite_tokens"] * (W_CC1 if x["tier"] == "1h" else W_CC5) for x in mrw),
            f"{sum(x['rewrite_tokens'] for x in mrw):,} tok",
        )
    )
    rank.append(
        (
            "子代理：已交卷（SubagentHandback）後被續棒、閒置>5m 重寫",
            len(hand),
            sum(x["rewrite_tokens"] * W_CC5 for x in hand),
            f"{sum(x['rewrite_tokens'] for x in hand):,} tok；上下文中位 "
            f"{statistics.median(x['prev_ctx'] for x in hand) if hand else 0:,.0f}",
        )
    )
    rank.append(
        (
            "子代理：執行中長指令／等待>5m 後重寫",
            len(other),
            sum(x["rewrite_tokens"] * W_CC5 for x in other),
            f"{sum(x['rewrite_tokens'] for x in other):,} tok",
        )
    )
    print(
        "   子代理重寫（TTL=5m）前一回合的工具：",
        dict(Counter((x.get("prev_tools") or ["(無工具)"])[-1] for x in srw).most_common(6)),
    )
    print(
        "   子代理重寫起因：",
        dict(Counter(x["cause"] for x in srw)),
        "；間隔桶：",
        dict(Counter(bucket(x["gap"], GAP_BUCKETS) for x in srw if x["gap"] is not None)),
    )
    print(
        "   子代理重寫上下文中位 {:,.0f}／最大 {:,}".format(
            statistics.median(x["prev_ctx"] for x in srw) if srw else 0,
            max((x["prev_ctx"] for x in srw), default=0),
        )
    )
    bgn = [x for x in mrw if x["bg_before"] > 0]
    print(
        "   其中前一回合結束時仍有背景任務／代理在跑"
        f"（turn_duration.pendingBackgroundAgentCount>0）：{len(bgn)} 件 "
        f"{sum(x['rewrite_tokens'] for x in bgn):,} tok"
    )
    comp = [x for x in all_main_turns if x["cause"] == "compaction" and x["gap"] is not None]
    print(
        f"   （另）壓縮後第一回合 {len(comp)} 件，cache_creation 合計 "
        f"{sum(x['cc'] for x in comp):,} tok——"
        "壓縮重寫是必要成本，不計入浪費"
    )


def sec_chains(cx: SimpleNamespace) -> None:
    """4 喚醒鏈成本。"""
    rows, u_main, all_main_turns, total_tokens, data, keep, rank = (
        cx.rows,
        cx.u_main,
        cx.all_main_turns,
        cx.total_tokens,
        cx.data,
        cx.keep,
        cx.rank,
    )
    # ---- 4 喚醒鏈 ------------------------------------------------------------------
    print("\n== 4 喚醒鏈成本（主控；一個非 tool_result 起因＋其後 tool_result 連續回合）==")
    all_chains: list[dict] = []
    for sid, _p, t in data["main"]:
        for c in chains([x for x in t["turns"]]):
            if keep(c["ts"]):
                all_chains.append(c)
    gb = defaultdict(list)
    for c in all_chains:
        gb[c["cause"]].append(c)
    print(
        f"   {'起因':18s} {'鏈數':>5s} {'回合/鏈':>8s} {'tok/鏈(中位)':>13s} {'tok合計':>14s} "
        f"{'占主控tok':>9s} {'輸出tok/鏈中位':>12s}"
    )
    mt = total_tokens(all_main_turns)
    for cause, cs in sorted(gb.items(), key=lambda kv: -sum(c["tokens"] for c in kv[1])):
        tk = sum(c["tokens"] for c in cs)
        print(
            f"   {cause:18s} {len(cs):5d} {sum(c['turns'] for c in cs) / len(cs):8.1f} "
            f"{statistics.median(c['tokens'] for c in cs):13,.0f} {tk:14,} {fmt_pct(tk, mt):>9s} "
            f"{statistics.median(c['out'] for c in cs):12,.0f}"
        )
    ack = [
        c
        for c in all_chains
        if c["cause"] in ("task_notification", "peer_handback")
        and c["turns"] <= 2
        and c["out"] <= 600
    ]
    print(
        f"   純確認型通知鏈（<=2 回合且輸出<=600 tok；單純被喚醒又睡回去）：{len(ack)} 鏈／"
        f"{sum(c['turns'] for c in ack)} 回合／{sum(c['tokens'] for c in ack):,} tok／加權單位 "
        f"{sum(c['units'] for c in ack):,.0f}"
        f"（占主控加權單位 {fmt_pct(sum(c['units'] for c in ack), u_main)}）"
    )
    nots = [c for c in all_chains if c["cause"] in ("task_notification", "peer_handback")]
    print(
        f"   通知類鏈共 {len(nots)} 條，加權單位 {sum(c['units'] for c in nots):,.0f}"
        f"（占主控加權單位 {fmt_pct(sum(c['units'] for c in nots), u_main)}）；"
        f"其中起始即重寫 {sum(1 for c in nots if c['rewrite'])} 條"
    )
    first_u = sum(c["first_units"] for c in nots)
    print(
        "   通知類鏈「第一個回合」的加權單位（被喚醒就必須付的最低成本＝整份上下文讀一遍＋輸出）："
        f"{first_u:,.0f}"
        f"（占主控加權單位 {fmt_pct(first_u, u_main)}）；此值扣掉其中的重寫即為純喚醒讀取費"
    )
    rank.append(
        (
            "主控：通知類喚醒的第一回合（讀整份上下文）",
            len(nots),
            first_u,
            "下界；其後的工作回合不算浪費",
        )
    )
    print("   通知類起因（task_notification＋peer_handback）依起始上下文大小分桶：")
    notif = [c for c in all_chains if c["cause"] in ("task_notification", "peer_handback")]
    for lo, hi, name in CTX_BUCKETS:
        b = [c for c in notif if lo <= c["ctx_start"] < hi]
        if b:
            print(
                f"     {name:>9}: {len(b):4d} 鏈 {sum(c['turns'] for c in b):5d} 回合 "
                f"{sum(c['tokens'] for c in b):>14,} tok "
                f"（單鏈中位 {statistics.median(c['tokens'] for c in b):,.0f}；其中單回合鏈 "
                f"{sum(1 for c in b if c['turns'] == 1)}）"
            )
    for c in all_chains:
        if c["cause"] != "tool_result":
            rows.append(
                {"kind": "chain", **{k: (iso(v) if k == "ts" else v) for k, v in c.items()}}
            )
