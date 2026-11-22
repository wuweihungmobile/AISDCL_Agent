"""換 session 成本量測三旗標（--switch-metrics／--replay-switch／--calibrate-switch）的 I/O 層。

判準在 sections_keep；本檔只負責讀逐字稿、母體快照、輸出。

零 token、只讀逐字稿與痕跡；母體可存成快照 JSON（`--dump-population`）並以 `--population`
重放，讓 CI（沒有真實逐字稿）與本機跑同一組判準：快照只留 usage／時間戳／起因，不含對話內容。
"""
from __future__ import annotations

import json
from pathlib import Path

from . import sections_keep as sk
from . import sections_wall as sw
from .reader import SYNTHETIC_MODEL, collect, parse_ts

_TURN_KEYS = ("ts_first", "ts_last", "inp", "cc", "cr", "out", "cc5", "cc1", "cause", "tools")
_FIRST_PROMPT_CHARS = 400
_SNAPSHOT_SCHEMA = "autosdd.wastecensus.population/1"


def _slim(turns: list) -> list[dict]:
    return [{k: t[k] for k in _TURN_KEYS} for t in turns if t["ts_first"]]


def _first_prompt(rec: dict) -> str:
    content = (rec.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    return " ".join(str(b.get("text", "")) for b in content or [] if isinstance(b, dict))


def _compaction(rec: dict, last: float | None) -> dict | None:
    meta = rec.get("compactMetadata") if isinstance(rec, dict) else None
    ts = parse_ts(rec.get("timestamp")) if isinstance(rec, dict) else None
    if not isinstance(meta, dict) or ts is None:
        return None
    idle = None if last is None else round((ts - last) / 60, 1)
    return {"ts": ts, "trigger": meta.get("trigger"), "pre": meta.get("preTokens"),
            "idle_min": idle}


def scan_main_file(path: Path) -> tuple[str, list[dict]]:
    """主逐字稿的第二趟輕掃：首則 user 提示（≤400 字，只供判斷是否交棒開場，不進快照）＋每次壓縮前
    的閒置分鐘（距上一筆非側鏈 assistant 記錄；無前一筆 ⇒ None）。壞行略過。"""
    first, comps, last = "", [], None
    try:
        handle = path.open(encoding="utf-8", errors="replace")
    except OSError:
        return first, comps
    with handle:
        for line in handle:
            if '"type":"user"' in line and not first:
                try:
                    first = _first_prompt(json.loads(line)).strip()[:_FIRST_PROMPT_CHARS]
                except (ValueError, AttributeError):
                    pass
            is_boundary = '"compact_boundary"' in line
            if not is_boundary and not ('"type":"assistant"' in line
                                        and '"isSidechain":true' not in line):
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if is_boundary:
                comp = _compaction(rec, last)
                if comp:
                    comps.append(comp)
                continue
            ts = parse_ts(rec.get("timestamp")) if isinstance(rec, dict) else None
            if ts is not None and rec.get("type") == "assistant":
                last = ts
    return first, comps


def scan_walls(path: Path) -> list[dict]:
    """主逐字稿裡的額度牆記錄 `[{ts, kind}]`（時間序）：`cut`＝harness 切斷通知（system，內文含
    `continuing automatically at`）、`synthetic`＝主鏈 `<synthetic>` assistant 且內文含限額字樣
    （同 sessionctl/qw_wall 的 ①②；③短窗讀數逐字稿裡沒有）。只認這兩個字樣，壞行略過。"""
    walls: list[dict] = []
    try:
        handle = path.open(encoding="utf-8", errors="replace")
    except OSError:
        return walls
    with handle:
        for line in handle:
            if sw.CUT_MARK not in line and "<synthetic>" not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            ts = parse_ts(rec.get("timestamp")) if isinstance(rec, dict) else None
            if ts is None:
                continue
            if rec.get("type") == "system" and sw.CUT_MARK in str(rec.get("content") or ""):
                walls.append({"ts": ts, "kind": "cut"})
            elif (rec.get("type") == "assistant" and rec.get("isSidechain") is not True
                  and (rec.get("message") or {}).get("model") == SYNTHETIC_MODEL
                  and sw.WALL_TEXT_RE.search(_first_prompt(rec))):
                walls.append({"ts": ts, "kind": "synthetic"})
    return sorted(walls, key=lambda w: w["ts"])


def load_population(base: Path, since_days: float) -> dict:
    data = collect(base, since_days, None)
    mains = []
    for sid, path, thread in data["main"]:
        turns = _slim(thread["turns"])
        if len(turns) < 2:
            continue
        first, comps = scan_main_file(path)
        mains.append({"sid": sid, "handoff_start": sk.is_handoff_start(first), "turns": turns,
                      "compactions": comps, "kw_calls": thread.get("kw_calls") or [],
                      "walls": scan_walls(path)})
    subs = [{"sid": sid, "turns": _slim(thread["turns"]), "kw_calls": thread.get("kw_calls") or []}
            for sid, _path, thread in data["sub"]]
    return {"schema": _SNAPSHOT_SCHEMA, "since_days": since_days, "main": mains, "sub": subs}


def read_population(path: Path) -> dict:
    pop = json.loads(path.read_text(encoding="utf-8"))
    if pop.get("schema") != _SNAPSHOT_SCHEMA:
        raise ValueError(f"快照 schema 不符：{pop.get('schema')!r}（要 {_SNAPSHOT_SCHEMA}）")
    return pop


def write_population(pop: dict, path: Path) -> None:
    path.write_text(json.dumps(pop, ensure_ascii=False), encoding="utf-8", newline="\n")


def _jsonl(path: Path | None) -> list[dict]:
    if path is None:
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    rows = []
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


# ───────────────────────────────────────────────────────────────────────────── 輸出
def _u(x) -> str:
    return "—" if x is None else f"{x:,.0f}"


def print_metrics(got: dict, pop: dict) -> None:
    k1, k2, k3, k4, k5, k6 = (got[f"m_k{i}"] for i in range(1, 7))
    n_main, n_sub = len(pop["main"]), len(pop["sub"])
    print(f"== 換 session 成本量測 M-K1～M-K9（母體：主控 {n_main}／子代理 {n_sub}；"
          f"近 {pop.get('since_days', '?')} 天）==")
    print(f"   M-K1 主控可保溫閒置後重寫：{k1['count']} 件／{k1['tokens']:,} tok"
          "（基線 21 件，目標 ≤2）")
    print(f"   M-K2 主控閒置自動壓縮（閒置 {sk.IDLE_COMPACT_LO}～{sk.IDLE_COMPACT_HI} 分）："
          f"{k2['count']} 次／量得到閒置的 auto 壓縮共 {k2['auto_total']} 次"
          f"（基線 9，目標 0）；壓縮前 {k2['pre_tokens']}")
    print(f"   M-K3 子代理執行中長等待重寫：{k3['count']} 件／{k3['tokens']:,} tok（基線 77 件）")
    print(f"   M-K4 子代理冷續棒重寫：{k4['count']} 件／{k4['tokens']:,} tok（目標：不升）")
    print(f"   M-K5 保溫自身成本：{k5['calls']} 次指令／{_u(k5['units'])} 單位"
          f"（對 M-K1 重寫單位比 {k5['ratio_vs_k1']}；目標 ≤0.5）")
    paid = k6["f_paid"]
    print(f"   M-K6 換手 {k6['spawns']} 次；新 session 前 {sk.F_TURNS} 回合實付 "
          f"n={k6['f_paid_n']} 中位 {_u(paid['median'])} 單位")
    print(f"   機制自身痕跡：{got['trace']}（0＝尚無資料或機制沒觸發，不是好消息）")
    print_wall_metrics(got)


def print_wall_metrics(got: dict) -> None:
    k7, k8, k9 = got["m_k7"], got["m_k8"], got["m_k9"]
    print(f"   M-K7 額度牆冷重寫：{k7['count']} 件／{k7['tokens']:,} tok／{_u(k7['units'])} 單位"
          "（牆後回來整份重寫；M-K1 不再重複計）")
    print(f"   M-K8 保溫成效：run {len(k8['runs'])}（(sid, reset) {k8['windows']} 組）：chain "
          f"{k8['chain']}／single {k8['single']}／periodic {k8['periodic']}／已交棒 "
          f"{k8['handed_over']}／未終結 {k8['open']}；跨重置保住快取 {k8['cross_ok']}、沒保住 "
          f"{k8['cross_fail']}、量不到 {k8['cross_unknown']}；省下 {_u(k8['saved_units'])} 單位")
    print(f"        備援觸發 {k8['fired']}／讓路 {k8['yield']}；牆 {k8['walls']} 面中牆前無觸發 "
          f"{k8['no_trigger_walls']}；牆中靜音 Stop {k8['stop_muted']} 次")
    failed, lost = k9["failed"], k9["not_resumed"]
    print(f"   M-K9 park 到點結局：job {k9['jobs']}＝fired {k9['fired']}／skipped {k9['skipped']}／"
          f"failed {failed['count']} {failed['reasons']}／無終態 {k9['unresolved']}")
    for item in failed["items"]:
        print(f"        failed：{item['sid']} {item['at']} 原因 {item['reasons']}")
    print(f"        宣稱已排程但未續上 {lost['count']} 件（已判 {lost['judged']}、reset＋"
          f"{sw.NOT_RESUMED_MIN} 分未到而待判 {lost['pending']}）")
    for item in lost["items"]:
        print(f"        未續上：{item['sid']} 排程於 {item['armed_at']}"
              f"（reset {item['reset_at']}）")


def print_replay(r: dict) -> None:
    p1, p3, s = r["p1"], r["p3"], r["subs"]
    window = f"閒置 {sk.IDLE_COMPACT_LO}～{sk.IDLE_COMPACT_HI} 分"
    print(f"== 重放（設計 §7；F＝{_u(r['f_cost'])} 單位、B＝{_u(r['b'])} tokens，n={r['f_n']}）==")
    print(f"P1 主控保溫（每 {p1['ping_min']:g} 分、動態 n*）：間隔≥55 分 {p1['idle_ge_55']} 件；"
          f"可保溫 {p1['keepable']} 件（重寫 {p1['rewrites']}）；基線 {_u(p1['base'])} → "
          f"{_u(p1['cost'])}（省 {_u(p1['saved'])}）；保溫 {p1['pings']} 次；"
          f"仍過期 {p1['still_expired']}")
    print(f"P1 附：閒置自動壓縮 {r['m_k2']['count']} 次（{window}）")
    for row in p3:
        print(f"P3 額度續跑選路（q={row['q']:g}）：{row['events']} 件中判 FRESH "
              f"{row['fresh']} 件；淨省 {_u(row['net'])}")
    print("P4b 邊界軟線掃描（史料；軟線依裁決不實作；只用 11-14 前 session）：")
    for row in r["p4b"]:
        n = row["net"]
        print(f"  T={row['T']:,}：跨越 {row['crossed']} 支；剩餘回合 中位 {row['rem_median']}"
              f"／最小 {row['rem_min']}／最大 {row['rem_max']}；"
              f"淨省 q=0 {_u(n[0])}｜q=1 {_u(n[1])}｜q=2 {_u(n[2])}")
    g150, gcost = s["s1_gate_150k"], s["s1_cost_gate"]
    print(f"S1 冷續棒：{s['s1_events']} 件／{s['s1_tokens']:,} tok；現行 150k 閘擋 {g150[0]} 件"
          f"（淨省 {_u(g150[1])}）；成本式擋 {gcost[0]} 件（淨省 {_u(gcost[1])}）；"
          f"F_a＝{_u(s['f_a'])}")
    print(f"S2 子代理分段等待：{s['s2_events']} 件；{_u(s['s2_base'])} → {_u(s['s2_cost'])}；"
          f"分段 {s['s2_polls']} 次；仍過期 {s['s2_still_expired']}；"
          f"等待間隔中位 {_u(s['s2_gap_median'])} 分／p90 {_u(s['s2_gap_p90'])} 分")


def print_calibration(c: dict) -> None:
    f, b, rc, pf = c["f"], c["b"], c["resume_cost"], c["p_fix"]
    print("== 校準建議值（皆量測值，改 env 前先重跑；出廠 F=480,000／B=150,000／P_fix=4,500）==")
    print(f"   F 接手成本（單位）：n={f['n']} p25={_u(f['p25'])} 中位={_u(f['median'])} "
          f"p75={_u(f['p75'])}")
    print(f"   B 接手後穩定上下文（tokens）：中位={_u(b['median'])}")
    print(f"   N_lo（跨 45 萬後的剩餘回合；只餵未實作的軟線 F3）：{c['n_lo_450k']}")
    print(f"   P_fix 保溫每次固定成本（不含讀快取）：實測 {_u(pf['measured_units_per_call'])} "
          f"單位／次（{pf['calls']} 次 keepwarm／waitfor 指令；0 次＝尚無實測，"
          f"沿用推估 {pf['factory']:,}）")
    print(f"   SESSION_RESUME 首回合實付（autosdd_resume_cost.jsonl）：n={rc['n']} "
          f"中位={_u(rc['units']['median'])} 單位；冷窗 {rc['cold_n']} 筆中寫入占比≥80% 的 "
          f"{rc['write_share_ge_80pct_cold']} 筆")


def print_wall_calibration(c: dict) -> None:
    """三鍵建議值；輸出只含輸入的函式（無時間、無路徑），同輸入兩次逐位元組相同（REQ-QW-52）。"""
    print(f"== 額度牆校準建議值（量測值；不寫任何設定檔，寫入須人審後另行 commit；"
          f"區間 < {c['min_n']} ⇒ 未校準）==")
    rows = (("PP", sw.KEY_PP, c["pp"], "{:.4f}", "pp／每千加權單位（一次保溫＝p(c)/1000×此值）"),
            ("BURN", sw.KEY_BURN, c["burn"], "{:.3f}", "pp／分（活躍區間 p75）"),
            ("AGENT", sw.KEY_AGENT, c["agent"], "{:.2f}", "pp（在飛代理收尾預估，p75）"))
    for _name, key, item, fmt, note in rows:
        if item["rec"] is None:
            print(f"   {key}：未校準（{item['reason']}）")
        else:
            print(f"   {key}={fmt.format(item['rec'])}  區間 n={item['n']}；{note}")
    print(f"   PP 區間來源：{c['pp']['sources']}；Δ 合計 {c['pp']['sum_delta']:g} pp")


def run(args, base: Path, trace_file: Path) -> int:
    """四個旗標共用的進入點；`args` 來自 report 的 parser。回 rc（量測探針，成功恆 0）。"""
    if args.population:
        pop = read_population(Path(args.population))
    else:
        pop = load_population(base, args.since_days)
    if args.dump_population:
        write_population(pop, Path(args.dump_population))
        print(f"母體快照已寫：{args.dump_population}")
    traces = _jsonl(trace_file)
    body: dict = {}
    if args.switch_metrics:
        oldwin = _jsonl(Path(args.oldwin_file) if args.oldwin_file
                        else trace_file.parent / "oldwin" / "events.jsonl")
        body["metrics"] = sk.switch_metrics(pop, traces, oldwin)
        print_metrics(body["metrics"], pop)
    if args.calibrate_quotawall:
        burn = _jsonl(Path(args.burn_file) if args.burn_file
                      else trace_file.parent / "quota_burn.jsonl")
        body["calibrate_quotawall"] = sw.calibrate_quotawall(pop, traces, burn)
        print_wall_calibration(body["calibrate_quotawall"])
    if args.replay_switch:
        body["replay"] = sk.replay_all(pop, args.ping_min)
        print_replay(body["replay"])
    if args.calibrate_switch:
        cost = Path(args.resume_cost_file) if args.resume_cost_file else None
        if cost is None:
            import endurance_env  # noqa: PLC0415 — lazy

            cost = endurance_env.trace_dir_peek()[0] / "autosdd_resume_cost.jsonl"
        body["calibrate"] = sk.calibrate(pop, _jsonl(cost), args.ping_min)
        print_calibration(body["calibrate"])
    if args.out:
        Path(args.out).write_text(
            json.dumps({"kind": "switch_metrics", **body}, ensure_ascii=False, default=str) + "\n",
            encoding="utf-8", newline="\n")
    return 0
