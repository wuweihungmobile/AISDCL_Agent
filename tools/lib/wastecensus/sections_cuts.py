"""5／6／7 節：額度牆切斷、出聲後續做、git push。

每節吃同一個 `cx`（見 `report.main`），輸出文字與原探針逐字相同。
"""
from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from types import SimpleNamespace

from .annotate import ctx, units
from .metrics import fmt_pct
from .reader import W_CC5, W_CR, iso


def sec_cuts(cx: SimpleNamespace) -> None:
    """5 子代理被額度牆切斷。"""
    rows, data, keep, all_sub_turns, total_tokens, rank = (
        cx.rows,
        cx.data,
        cx.keep,
        cx.all_sub_turns,
        cx.total_tokens,
        cx.rank,
    )
    # ---- 5 子代理被額度牆切斷 ------------------------------------------------------
    print("\n== 5 子代理被額度牆切斷（isApiErrorMessage 且 error=rate_limit）==")
    sub_cuts = []
    for sid, _p, t in data["sub"]:
        rl = [c for c in t["cuts"] if c["error"] == "rate_limit" and keep(c["ts"])]
        if not rl or not t["turns"]:
            continue
        first = rl[0]
        before = [x for x in t["turns"] if x["ts_first"] and x["ts_first"] <= first["ts"]]
        used = sum(x["inp"] + x["cc"] + x["cr"] + x["out"] for x in before)
        used_u = sum(units(x) for x in before)
        spawn = t["first_ts"]
        resume = next(
            (x for x in t["turns"] if x["ts_first"] and x["ts_first"] > first["ts"] + 5), None
        )
        wr = [(ts_, p_) for ts_, p_ in t["writes"] if ts_ and ts_ <= first["ts"]]
        sub_cuts.append(
            {
                "writes_before_cut": len(wr),
                "scratch_writes_before_cut": sum(
                    1 for _t, p_ in wr if "scratchpad" in p_.replace("\\", "/")
                ),
                "writes_total": len(t["writes"]),
                "resume_gap_min": round((resume["ts_first"] - first["ts"]) / 60, 1)
                if resume
                else None,
                "resume_cc": resume["cc"] if resume else None,
                "resume_rewrite_tokens": resume["rewrite_tokens"] if resume else None,
                "resume_cause": resume["cause"] if resume else None,
                "resume_ctx": ctx(resume) if resume else None,
                "kind": "subagent_cut",
                "sid": sid,
                "agent": _p.stem,
                "desc": (t.get("meta") or {}).get("description"),
                "model": (t.get("meta") or {}).get("model"),
                "spawn": iso(spawn),
                "cut": iso(first["ts"]),
                "spawn_to_cut_min": round((first["ts"] - spawn) / 60, 1) if spawn else None,
                "turns_before": len(before),
                "tokens_before": used,
                "units_before": used_u,
                "limit_text": first["text"],
                "cut_events": len(rl),
                "wrote_after_cut": any(
                    x["ts_first"] and x["ts_first"] > first["ts"] + 5 for x in t["turns"]
                ),
            }
        )
    rows += sub_cuts
    print(
        f"   次數 {len(sub_cuts)}（涉及 "
        f"{len({c['cut'][:13] if c['cut'] else '' for c in sub_cuts})} 個不同小時的撞線事件）；"
        f"切斷前已耗 token 合計 {sum(c['tokens_before'] for c in sub_cuts):,}"
        "（占子代理 tok "
        f"{fmt_pct(sum(c['tokens_before'] for c in sub_cuts), total_tokens(all_sub_turns))}）"
    )
    if sub_cuts:
        spans = sorted(c["spawn_to_cut_min"] for c in sub_cuts if c["spawn_to_cut_min"] is not None)
        print(f"   派出→切斷分鐘：min {spans[0]}／中位 {statistics.median(spans)}／max {spans[-1]}")
        print(
            "   切斷前 token：中位 "
            f"{statistics.median(c['tokens_before'] for c in sub_cuts):,.0f}／最大 "
            f"{max(c['tokens_before'] for c in sub_cuts):,}"
        )
        print(
            f"   切斷後仍有寫入（同檔續跑）：{sum(1 for c in sub_cuts if c['wrote_after_cut'])} 支"
        )
        print(
            "   切斷前已 Write／Edit 過檔案的子代理 "
            f"{sum(1 for c in sub_cuts if c['writes_before_cut'])}／{len(sub_cuts)} 支"
            "（其中寫進 scratchpad 的 "
            f"{sum(1 for c in sub_cuts if c['scratch_writes_before_cut'])} 支）；"
            f"切斷前零寫入 {sum(1 for c in sub_cuts if not c['writes_before_cut'])} 支"
        )
        rs = [c for c in sub_cuts if c["resume_cc"] is not None]
        rank.append(
            (
                "子代理：被額度牆切斷後續跑的第一回合重寫",
                len(rs),
                sum((c["resume_rewrite_tokens"] or 0) * W_CC5 for c in rs),
                f"{sum(c['resume_rewrite_tokens'] or 0 for c in rs):,} tok（切斷前的已做工作不計）",
            )
        )
        print(
            f"   續跑後第一回合（{len(rs)} 支）：間隔中位 "
            f"{statistics.median(c['resume_gap_min'] for c in rs):.0f} 分；"
            f"cache_creation 合計 {sum(c['resume_cc'] for c in rs):,} tok（中位 "
            f"{statistics.median(c['resume_cc'] for c in rs):,.0f}）；"
            f"重寫 {sum(c['resume_rewrite_tokens'] or 0 for c in rs):,} tok；起因 "
            f"{dict(Counter(c['resume_cause'] for c in rs))}"
        )
    main_cuts = []
    for sid, _p, t in data["main"]:
        for c in t["cuts"]:
            if keep(c["ts"]):
                main_cuts.append(
                    {
                        "kind": "main_cut",
                        "sid": sid,
                        "ts": iso(c["ts"]),
                        "error": c["error"],
                        "text": c["text"],
                    }
                )
    rows += main_cuts
    print(
        f"   （對照）主控自己撞到的 synthetic 錯誤 {len(main_cuts)} 筆："
        f"{dict(Counter(c['error'] for c in main_cuts))}"
    )


def sec_voice(cx: SimpleNamespace) -> None:
    """6 hook 出聲換 session 之後。"""
    args, rows, data, keep, rank = cx.args, cx.rows, cx.data, cx.keep, cx.rank
    # ---- 6 出聲換 session 之後 -------------------------------------------------------
    print("\n== 6 hook 出聲「建議換新 session」之後 ==")
    n_voice = 0
    for sid, _p, t in data["main"]:
        for v in t["voices"]:
            if not keep(v["ts"]):
                continue
            n_voice += 1
            after = [x for x in t["turns"] if x["ts_first"] and x["ts_first"] > v["ts"]]
            before = [x for x in t["turns"] if x["ts_first"] and x["ts_first"] <= v["ts"]]
            if not before or not after:
                continue
            ctx0 = ctx(before[-1])
            row = {
                "kind": "voice_aftermath",
                "sid": sid,
                "voice_ts": iso(v["ts"]),
                "ctx_at_voice": ctx0,
                "turns_after": len(after),
                "ctx_end": ctx(after[-1]),
                "ctx_growth": ctx(after[-1]) - ctx0,
                "hours_after": round((after[-1]["ts_last"] - v["ts"]) / 3600, 2),
                "tokens_after": sum(x["inp"] + x["cc"] + x["cr"] + x["out"] for x in after),
                "units_after": sum(units(x) for x in after),
                "rewrites_after": sum(1 for x in after if x["rewrite"]),
                "rewrite_tokens_after": sum(x["rewrite_tokens"] for x in after),
                "units_session_total": sum(units(x) for x in t["turns"]),
            }
            fresh = args.fresh_baseline_ctx
            excess = sum(max(0, x["cr"] - fresh) * W_CR for x in after)
            row["excess_read_units_vs_fresh"] = excess
            rank.append(
                (
                    f"主控：出聲後仍在同 session 工作（{sid[:8]}），多付的讀取費（對照新 session "
                    f"基線 {fresh:,}）",
                    len(after),
                    excess,
                    f"{row['hours_after']} 小時；上下文 +{row['ctx_growth']:,}",
                )
            )
            rows.append(row)
            print(
                f"   sid {sid[:8]} 出聲 {row['voice_ts']}：當時上下文 {ctx0:,}；其後繼續 "
                f"{row['hours_after']} 小時、"
                f"{row['turns_after']} 回合、上下文 +{row['ctx_growth']:,}（至 {row['ctx_end']:,}）"
                "、"
                f"耗 {row['tokens_after']:,} tok（加權單位占該 session "
                f"{fmt_pct(row['units_after'], row['units_session_total'])}）、"
                f"期間重寫 {row['rewrites_after']} 件／{row['rewrite_tokens_after']:,} tok"
            )
    if not n_voice:
        print("   量不到：母體內沒有 hook_additional_context／hook_system_message 帶出聲字樣的記錄")


def sec_push(cx: SimpleNamespace) -> None:
    """7 git push（PowerShell／Bash 工具呼叫字串）。"""
    rows, data, keep = cx.rows, cx.data, cx.keep
    # ---- 7 push ---------------------------------------------------------------------
    print("\n== 7 git push（PowerShell／Bash 工具呼叫字串）==")
    pushes = []
    for sid, _p, t in data["main"]:
        pushes += [p for p in t["pushes"] if keep(p["ts"])]
    pushes.sort(key=lambda p: p["ts"])
    for p in pushes:
        rows.append({"kind": "push", **{k: (iso(v) if k == "ts" else v) for k, v in p.items()}})
    walls = [p["wall_s"] for p in pushes if p["wall_s"] is not None]
    print(
        f"   呼叫 {len(pushes)} 次；結果 {dict(Counter(p['outcome'] for p in pushes))}；背景 "
        f"{sum(1 for p in pushes if p['bg'])}"
    )
    if walls:
        print(
            f"   牆鐘（呼叫→結果／背景則至完成通知）：中位 {statistics.median(walls) / 60:.1f} 分／"
            f"最大 {max(walls) / 60:.1f} 分／合計 {sum(walls) / 60:.0f} 分"
        )
    by_sid = defaultdict(list)
    for p in pushes:
        by_sid[p["sid"]].append(p)
    retry_sids = 0
    retry_wall = 0.0
    for sid, ps in by_sid.items():
        fails = [p for p in ps if p["outcome"] == "fail"]
        if fails and any(p["ts"] > fails[0]["ts"] for p in ps if p is not fails[0]):
            retry_sids += 1
            retry_wall += sum((p["wall_s"] or 0) for p in fails)
    print(
        f"   曾先失敗後又重推的 session：{retry_sids}；失敗那幾次的牆鐘合計 {retry_wall / 60:.0f} "
        "分"
    )
    cx.pushes = pushes
