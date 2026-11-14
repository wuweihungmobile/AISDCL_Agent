"""3／8／9 節與排序、額度窗標定：事故重建、孤兒等待、機制成本。

每節吃同一個 `cx`（見 `report.main`），輸出文字與原探針逐字相同。
"""
from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from datetime import UTC, datetime
from types import SimpleNamespace

import quota_limits

from .annotate import ctx, units
from .metrics import fmt_pct
from .reader import W_CC1, W_CC5, iso, parse_iso


def sec_incident(cx: SimpleNamespace) -> None:
    """3 事故重建。"""
    args, rows, data, all_main_turns, all_sub_turns = (
        cx.args,
        cx.rows,
        cx.data,
        cx.all_main_turns,
        cx.all_sub_turns,
    )
    # ---- 3 事故 ---------------------------------------------------------------------
    print(
        f"\n== 3 事故重建 sid {args.incident_sid[:8]} {args.incident_from} ～ {args.incident_to} =="
    )
    t0, t1 = parse_iso(args.incident_from), parse_iso(args.incident_to)
    w0, w1 = parse_iso(args.window_from), parse_iso(args.window_to)
    inc = next((t for s, _p, t in data["main"] if s == args.incident_sid), None)
    win_all = [
        x for x in all_main_turns + all_sub_turns if x["ts_first"] and w0 <= x["ts_first"] < w1
    ]
    u_win = sum(units(x) for x in win_all)
    u_win_fable = sum(units(x) for x in win_all if "fable" in x["model"])
    if inc is None:
        print("   量不到：母體內沒有該 sid 的逐字稿")
    else:
        its = [x for x in inc["turns"] if x["ts_first"] and t0 <= x["ts_first"] <= t1]
        for x in its:
            rows.append(
                {
                    "kind": "incident_turn",
                    "ts": iso(x["ts_first"]),
                    "gap_s": x["gap"],
                    "ctx": ctx(x),
                    "cc": x["cc"],
                    "cr": x["cr"],
                    "out": x["out"],
                    "units": units(x),
                    "cause": x["cause"],
                    "rewrite": x["rewrite"],
                    "rewrite_tokens": x["rewrite_tokens"],
                    "tier": x["tier"],
                    "tools": x["tools"],
                }
            )
        u_inc = sum(units(x) for x in its)
        rw = [x for x in its if x["rewrite"]]
        print(f"   回合 {len(its)}；加權單位 {u_inc:,.0f}；重寫事件 {len(rw)}")
        for x in rw:
            print(
                f"   重寫：{iso(x['ts_first'])} 間隔 {x['gap'] / 60:.1f} 分，前一回合上下文 "
                f"{x['prev_ctx']:,}，本回合 cache_creation {x['cc']:,}"
                f"／cache_read {x['cr']:,}，重寫 {x['rewrite_tokens']:,} tok，TTL={x['tier']}，"
                f"起因={x['cause']}"
            )
            rw_u = x["rewrite_tokens"] * (W_CC1 if x["tier"] == "1h" else W_CC5)
            print(
                f"      該重寫的加權單位 {rw_u:,.0f}＝事故區間 {fmt_pct(rw_u, u_inc)}、"
                f"五小時窗全軸 {fmt_pct(rw_u, u_win)}、窗內 Fable 軸 {fmt_pct(rw_u, u_win_fable)}"
                "（推估）"
            )
        print(
            f"   五小時窗（{args.window_from}～{args.window_to}）全部回合（含所有 session "
            f"的主控與子代理）加權單位 {u_win:,.0f}"
            f"（Fable 軸 {u_win_fable:,.0f}）；事故區間 {fmt_pct(u_inc, u_win)}"
        )
        rest = [x for x in its if not x["rewrite"]]
        print(
            f"   事故區間其餘 {len(rest)} 回合加權單位 {sum(units(x) for x in rest):,.0f}"
            "（cache_read 讀取費）"
        )
        biggest = sorted(its, key=lambda x: -units(x))[:5]
        for x in biggest:
            print(
                f"   前五貴：{iso(x['ts_first'])} ctx {ctx(x):,} cc {x['cc']:,} cr {x['cr']:,} out "
                f"{x['out']:,} 單位 {units(x):,.0f} 起因 {x['cause']} 工具 {x['tools']}"
            )
        win_by_sid = Counter()
        for x in win_all:
            win_by_sid[(x["sid"][:8], x["thread"] if x["thread"] == "main" else "subagents")] += (
                units(x)
            )
        print("   該五小時窗各來源加權單位占比（推估）：")
        for k, v in win_by_sid.most_common(6):
            print(f"     {k[0]} {k[1]:10s} {v:>14,.0f} {fmt_pct(v, u_win)}")


def sec_orphans(cx: SimpleNamespace) -> None:
    """8 孤兒背景等待。"""
    rows, data, keep = cx.rows, cx.data, cx.keep
    print(
        "\n== 8 孤兒背景等待（run_in_background 的 shell 指令，逐字稿無對應完成通知；成功判準 1 "
        "的偵測對象）=="
    )
    orphans = []
    nbg = 0
    for sid, _p, t in data["main"]:
        mt_turns = t["turns"]
        for c in t["bg_calls"]:
            if not keep(c["ts"]):
                continue
            nbg += 1
            if c["notified"]:
                continue
            nxt = next(
                (
                    x
                    for x in mt_turns
                    if x["ts_first"] and x["ts_first"] > c["ts"] and x["gap"] and x["gap"] > 1200
                ),
                None,
            )
            idle = round(nxt["gap"] / 60, 1) if nxt else None
            orphans.append(
                {
                    "kind": "orphan_bg",
                    "sid": sid,
                    "ts": iso(c["ts"]),
                    "cmd": c["cmd"],
                    "next_idle_gap_min": idle,
                    "next_idle_is_rewrite": bool(nxt and nxt["rewrite"]),
                }
            )
    print(
        f"   背景 shell 指令 {nbg} 條；無完成通知 {len(orphans)} 條；其中其後出現 >20 分閒置的 "
        f"{sum(1 for o in orphans if o['next_idle_gap_min'])} 條；"
        f"該閒置回合為整份重寫的 {sum(1 for o in orphans if o['next_idle_is_rewrite'])} 條"
    )
    for o in orphans:
        if o["next_idle_gap_min"]:
            print(
                f"     {o['sid'][:8]} {o['ts']} 其後閒置 {o['next_idle_gap_min']} 分 "
                f"重寫={o['next_idle_is_rewrite']}  {o['cmd'][:90]}"
            )
    rows += orphans


def sec_mech(cx: SimpleNamespace) -> None:
    """9 既有機制自身成本基線與 push 失敗排序列。"""
    rows, data, all_main_turns, rank, pushes = (
        cx.rows,
        cx.data,
        cx.all_main_turns,
        cx.rank,
        cx.pushes,
    )
    print("\n== 9 既有機制自身成本基線（hook 延遲／注入字元；成功判準 5 的對照）==")
    ms = defaultdict(list)
    chars: list[int] = []
    for sid, _p, t in data["main"]:
        for name, v in t["hook_ms"]:
            ms[name.split(":")[0] + ":" + (name.split(":")[1] if ":" in name else "")].append(v)
        chars += t["hook_ctx_chars"]
    allv = [v for vs in ms.values() for v in vs]
    if allv:
        srt = sorted(allv)
        print(
            f"   主控 hook_success {len(allv)} 筆；每筆 durationMs 中位 "
            f"{statistics.median(allv):.0f}／p95 {srt[int(0.95 * (len(srt) - 1))]:.0f}／最大 "
            f"{srt[-1]:.0f}；"
            f"合計 {sum(allv) / 1000:.0f} 秒（約 "
            f"{sum(allv) / 1000 / max(1, len(all_main_turns)):.2f} 秒／主控回合）"
        )
        for name, vs in sorted(ms.items(), key=lambda kv: -sum(kv[1]))[:5]:
            print(
                f"     {name:28s} n={len(vs):5d} 中位 {statistics.median(vs):.0f} ms 合計 "
                f"{sum(vs) / 1000:.0f} s"
            )
    print(
        f"   注入上下文的 hook 訊息 {len(chars)} 則，合計 {sum(chars):,} 字元（約 "
        f"{sum(chars) // 3:,} tok 以 3 字元/tok 推估）；"
        f"平均 {sum(chars) / max(1, len(all_main_turns)):.0f} 字元／主控回合"
    )
    rows.append(
        {
            "kind": "mech_cost",
            "hook_calls": len(allv),
            "hook_ms_median": statistics.median(allv) if allv else None,
            "hook_ms_total": sum(allv),
            "ctx_msgs": len(chars),
            "ctx_chars": sum(chars),
            "main_turns": len(all_main_turns),
        }
    )
    pushfail = [p for p in pushes if p["outcome"] == "fail"]
    rank.append(
        (
            "push：失敗後重推（牆鐘為主，token 另計）",
            len(pushfail),
            0.0,
            f"失敗 {len(pushfail)} 次／牆鐘 {sum((p['wall_s'] or 0) for p in pushfail) / 60:.0f} "
            "分；token 量不到（失敗輸出在背景檔）",
        )
    )


def sec_rank(cx: SimpleNamespace) -> None:
    """浪費排序。"""
    rows, rank, u_main, u_sub = cx.rows, cx.rank, cx.u_main, cx.u_sub
    print("\n== 浪費排序（加權單位為推估；占比＝占全軸（主控＋子代理）加權單位）==")
    tot_u = u_main + u_sub
    for label, n, un, note in sorted(rank, key=lambda r: -r[2]):
        print(f"   {un:>14,.0f} {fmt_pct(un, tot_u):>6s} ×{n:<5d} {label}｜{note}")
        rows.append(
            {
                "kind": "rank",
                "label": label,
                "count": n,
                "units": un,
                "share_all_axes": (un / tot_u if tot_u else None),
                "note": note,
            }
        )


def sec_quota(cx: SimpleNamespace) -> None:
    """額度窗標定。"""
    data, keep, rows, all_main_turns, all_sub_turns = (
        cx.data,
        cx.keep,
        cx.rows,
        cx.all_main_turns,
        cx.all_sub_turns,
    )
    # ---- 額度窗標定（撞線窗內的加權單位；用來判「推估單位 ≈ 額度」夠不夠準）----------
    print("\n== 額度窗標定：每個 5 小時撞線窗（reset−5h～reset）內各模型軸的加權單位 ==")
    wins = {}
    for sid, _p, t in data["main"] + data["sub"]:
        for c in t["cuts"]:
            if c["error"] == "rate_limit" and "5-hour" in c["text"] and keep(c["ts"]):
                anchor = datetime.fromtimestamp(c["ts"], tz=UTC).astimezone()
                reset = quota_limits.parse_reset_at(c["text"], anchor)
                if reset:
                    wins.setdefault(reset.timestamp(), []).append(c["ts"])
    alls = all_main_turns + all_sub_turns
    for reset in sorted(wins):
        lo, hi = reset - 5 * 3600, reset
        ts = [x for x in alls if x["ts_first"] and lo <= x["ts_first"] < hi]
        fam = Counter()
        for x in ts:
            name = (
                "fable"
                if "fable" in x["model"]
                else (
                    "sonnet"
                    if "sonnet" in x["model"]
                    else (
                        "opus"
                        if "opus" in x["model"]
                        else ("haiku" if "haiku" in x["model"] else "other")
                    )
                )
            )
            fam[name] += units(x)
        first_hit = min(wins[reset])
        until_hit = sum(units(x) for x in ts if x["ts_first"] <= first_hit)
        print(
            f"   {iso(lo)}～{iso(hi)}：首次撞線 {iso(first_hit)}；撞線前加權單位 {until_hit:,.0f}；"
            f"全窗 {sum(fam.values()):,.0f}；各軸 { {k: round(v) for k, v in fam.items()} }"
        )
        rows.append(
            {
                "kind": "quota_window",
                "from": iso(lo),
                "to": iso(hi),
                "first_hit": iso(first_hit),
                "units_until_hit": until_hit,
                "units_by_family": dict(fam),
            }
        )
