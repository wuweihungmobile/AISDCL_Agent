"""浪費帳入口：參數解析、各節輸出編排、指標摘要、jsonl 寫出、門檻取值重放（量測探針，不接閘門 rc）。

WHY 這支存在：2026-11-14 掌舵者回報「閒置後回來又多燒約 20% 五小時窗」，而根 CLAUDE.md 與主控
都曾把「36 萬 token 重寫快取吃 18%」當事實引用，卻沒有可重跑的量測。本套件把七類浪費的次數／
token 寫成可 diff 的 jsonl＋人讀摘要；每個數字都是量測值、不是常數，要對照就重跑。
入口薄殼＝`tools/probe/waste_census.py`，判準全在本套件（`reader`／`metrics`／`replay`／`sections`）。

用法（經入口薄殼）::

    python tools/probe/waste_census.py [--since-days 14] [--sid <sid>] [--out <jsonl>]
    python tools/probe/waste_census.py --replay-hard-ctx [--r1 250000] [--candidates 260000,290000]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

import platform_utils

from . import metrics, replay, resume, sections_cache, sections_cuts, sections_misc
from .annotate import annotate, units
from .reader import collect

TRACE_NAME = "autosdd_session_switch.jsonl"
_REPO = Path(__file__).resolve().parents[3]


def _default_base() -> Path:
    """專案逐字稿目錄：`~/.claude/projects/<repo 路徑把非英數換成 - 的 slug>`。"""
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(_REPO))
    return platform_utils.claude_home() / "projects" / slug


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="waste_census.py",
        allow_abbrev=False,
        description="等待與續跑 Token 浪費帳（逐字稿，零 token）",
    )
    ap.add_argument(
        "--base",
        default=str(_default_base()),
        help="專案逐字稿目錄（預設 ~/.claude/projects/<此 repo slug>）",
    )
    ap.add_argument("--since-days", type=float, default=14.0)
    ap.add_argument("--sid", default=None, help="只量這個 session（含其子代理）")
    ap.add_argument("--out", default=None, help="逐筆 jsonl（預設系統暫存）")
    ap.add_argument(
        "--fresh-baseline-ctx",
        type=int,
        default=92_522,
        help="新 session 開場上下文基線（實測：sid 680d8411 讀完交接包後第一回合）",
    )
    ap.add_argument("--incident-sid", default="680d8411-58ac-4adb-9e23-521f6a7bb557")
    ap.add_argument("--incident-from", default="2026-11-14T20:52:00+08:00")
    ap.add_argument("--incident-to", default="2026-11-14T22:30:00+08:00")
    ap.add_argument(
        "--window-from",
        default="2026-11-14T18:00:00+08:00",
        help="事故所在五小時窗起點（撞線字樣 resets 11pm ⇒ 18:00～23:00）",
    )
    ap.add_argument("--window-to", default="2026-11-14T23:00:00+08:00")
    ap.add_argument(
        "--replay-hard-ctx",
        action="store_true",
        help="只做收斂硬門檻 H 的取值重放（TCS §7），不出整份浪費帳",
    )
    ap.add_argument("--r1", type=int, default=250_000, help="重放用的 R1（出聲門檻）")
    ap.add_argument("--candidates", default=None, help="重放候選 H，逗號分隔（預設內建九個）")
    ap.add_argument(
        "--resume-metrics",
        action="store_true",
        help="續航量測 M-R1～M-R4（ADR-XPLAT-004 §2.17.7）",
    )
    ap.add_argument(
        "--supervision-metrics",
        action="store_true",
        help="監督與換手量測 M-W1～W4／M-F1～F3／M-S1～S3（ARCH §9）",
    )
    ap.add_argument(
        "--wake-metrics",
        action="store_true",
        help="叫醒量測 M-WB1／M-WB2（DES WorkProgress_Axis_Design §6.4；零 token、不接閘門）",
    )
    ap.add_argument(
        "--pace-metrics",
        action="store_true",
        help="配速床量測 M-P1／P3／P4／P7／M-C1（ADR-XPLAT-004 §2.15.7）",
    )
    ap.add_argument(
        "--replay-pace-floor",
        action="store_true",
        help="AC-7：把真實 quota_burn 各列跑有床／無床兩次對照（ADR-XPLAT-004 §2.15.7）",
    )
    ap.add_argument("--halt-dir", default=None, help="halt 標記目錄（預設持久痕跡目錄）")
    ap.add_argument("--pace-file", default=None, help="autosdd_pace_floor.jsonl（預設痕跡目錄下）")
    ap.add_argument(
        "--switch-metrics",
        action="store_true",
        help="換 session 成本量測 M-K1～M-K6（設計 SessionSwitch_CostModel_Design §2）",
    )
    ap.add_argument(
        "--replay-switch",
        action="store_true",
        help="把新判準套回真實逐字稿，重現設計 §7 全表（零 token）",
    )
    ap.add_argument(
        "--calibrate-switch",
        action="store_true",
        help="重算 F、B、N_lo、P_fix 建議值（讀逐字稿與 autosdd_resume_cost.jsonl）",
    )
    ap.add_argument("--ping-min", type=float, default=45.0, help="重放／校準用的主控保溫間隔（分）")
    ap.add_argument("--population", default=None, help="讀母體快照 JSON，不讀逐字稿（CI 用）")
    ap.add_argument("--dump-population", default=None, help="母體存成快照 JSON（只含 usage）")
    ap.add_argument("--resume-cost-file", default=None, help="resume_cost 痕跡檔（預設痕跡目錄）")
    ap.add_argument("--handoff-dir", default=None, help="交接包目錄（預設 ~/.autosdd/handoff）")
    ap.add_argument("--burn-file", default=None, help="quota_burn.jsonl（預設痕跡目錄下）")
    ap.add_argument(
        "--trace-file",
        default=None,
        help=f"M3d 讀的痕跡檔（預設 endurance_env.trace_dir()/{TRACE_NAME}）",
    )
    return ap


def _trace_path(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    import endurance_env  # noqa: PLC0415 — lazy：只有算 M3d 預設路徑時才需要

    return endurance_env.trace_dir() / TRACE_NAME


def _print_metrics(cx: SimpleNamespace) -> dict:
    """指標摘要（M1／M2b／M2c／M2d／M3a／M3d／M4／M5）；回傳整包供寫 jsonl。"""
    from lib.sessionctl import switch  # noqa: PLC0415 — lazy：與 tools 同層的套件，路徑由入口設定

    limit = switch.threshold(switch.AGENT_TOKENS_KEY)[0]
    rows = cx.rows
    types = metrics.agent_types(cx.data)
    got = {
        "m1": metrics.m1(rows),
        "m2b": metrics.m2b(rows, limit),
        "m2c": metrics.m2c(rows, types),
        "m2d": metrics.m2d(metrics.turns_by_agent(cx.data), types),
        "m3a": metrics.m3a(rows),
        "m3d": metrics.m3d(_trace_path(cx.args.trace_file)),
        "m4": metrics.m4(rows),
        "m5": metrics.m5(rows),
    }
    print("\n== 指標摘要（可重跑量測值；M2b 的門檻取自 AUTOSDD_RESUME_AGENT_TOKENS）==")
    print(
        f"   M1  主控閒置>1h 且 prev_ctx>=250k 的重寫：{got['m1']['count']} 件／"
        f"{got['m1']['tokens']:,} tok"
    )
    b = got["m2b"]
    print(
        f"   M2b 子代理他人續棒（prev_ctx>={limit:,}）重寫：{b['count']} 件（<=60 分 "
        f"{b['le60min']}）／{b['tokens']:,} tok"
    )
    c = got["m2c"]
    print(
        f"   M2c 子代理 tool_result／通知喚醒（<=60 分）重寫：{c['count']} 件（間隔<5 分 "
        f"{c['gap_lt_ttl']}）；按型別 {c['by_type']}"
    )
    d = got["m2d"]
    print(f"   M2d long-runner 代理 {d['agents']} 支；全程無長等待占比 {d['zero_wait_share']}")
    a = got["m3a"]
    print(
        f"   M3a 子代理被額度牆切斷：{a['count']} 支；續跑第一回合重寫 "
        f"{a['resume_rewrite_tokens']:,} tok"
    )
    t = got["m3d"]
    print(
        f"   M3d 機制自身：續棒阻斷 {t['blocked']}／逃生放行 {t['overridden']}／收斂閘阻斷 "
        f"{t['converge_blocked']}"
    )
    p = got["m4"]
    print(
        f"   M4  push 呼叫 {p['calls']} 次，失敗 {p['fail']} 次，失敗牆鐘 "
        f"{p['fail_wall_s'] / 60:.0f} 分"
    )
    e = got["m5"]
    print(
        f"   M5  hook 呼叫 {e['hook_calls']} 筆，延遲中位 {e['hook_ms_median']} ms；注入 "
        f"{e['ctx_chars']} 字元"
    )
    return got


def _run_replay(args: argparse.Namespace, base: Path) -> int:
    cands = (
        tuple(int(x) for x in args.candidates.split(","))
        if args.candidates
        else replay.DEFAULT_CANDIDATES
    )
    table = replay.replay_hard_ctx(
        base,
        args.r1,
        cands,
        incident_sid=args.incident_sid,
        incident_ts=args.incident_from,
        since_days=args.since_days,
    )
    print(
        f"收斂硬門檻重放：R1={args.r1:,}；近 {args.since_days:g} 天；事故 {args.incident_sid[:8]} "
        f"@ {args.incident_from}"
    )
    head = (
        "H",
        "reach_H",
        "room_med",
        "room_p25",
        "blocked_disp",
        "disp_after_R1",
        "incident_blocked",
    )
    print("{:>9} {:>8} {:>9} {:>9} {:>13} {:>14} {:>17}".format(*head))
    for r in table:
        print(
            "{:>9,} {:>8} {:>9} {:>9} {:>13} {:>14} {:>17}".format(
                r["H"],
                r["sessions_reaching_H"],
                r["room_turns_median"],
                r["room_turns_p25"],
                r["blocked_dispatches"],
                r["dispatches_after_r1"],
                str(r["incident_blocked"]),
            )
        )
    if args.out:
        body = "\n".join(
            json.dumps({"kind": "hard_ctx_replay", **r}, ensure_ascii=False) for r in table
        )
        Path(args.out).write_text(body + "\n", encoding="utf-8", newline="\n")
    return 0


def main(argv: list[str]) -> int:
    args = _build_parser().parse_args(argv)
    base = Path(args.base)
    if args.switch_metrics or args.replay_switch or args.calibrate_switch:
        from . import keep_load  # noqa: PLC0415 — lazy

        if not args.population and not base.is_dir():
            print(f"逐字稿目錄不存在：{base}（或改用 --population 快照）", file=sys.stderr)
            return 1
        return keep_load.run(args, base, _trace_path(args.trace_file))
    if not base.is_dir():
        print(f"逐字稿目錄不存在：{base}", file=sys.stderr)
        return 1
    if args.replay_hard_ctx:
        return _run_replay(args, base)
    if args.wake_metrics:
        from . import sections_wake  # noqa: PLC0415 — lazy

        return sections_wake.run(base, args.since_days, args.sid, args.out)
    if args.pace_metrics or args.replay_pace_floor:
        import endurance_env  # noqa: PLC0415 — lazy：只有取痕跡目錄預設值時才需要

        trace_dir = endurance_env.trace_dir_peek()[0]
        halt_dir = Path(args.halt_dir) if args.halt_dir else trace_dir
        burn_path = Path(args.burn_file) if args.burn_file else trace_dir / "quota_burn.jsonl"
        if args.replay_pace_floor:
            from . import pace_replay  # noqa: PLC0415

            return pace_replay.run(burn_path, halt_dir, args.since_days, args.out)
        from . import pace_metrics  # noqa: PLC0415

        pace_file = (Path(args.pace_file) if args.pace_file
                     else trace_dir / "autosdd_pace_floor.jsonl")
        return pace_metrics.run(base, args.since_days, halt_dir, burn_path, pace_file, args.out)
    if args.supervision_metrics:
        from . import supervision_load  # noqa: PLC0415 — lazy

        handoff_dir = (Path(args.handoff_dir) if args.handoff_dir
                       else Path.home() / ".autosdd" / "handoff")
        trace = _trace_path(args.trace_file)
        return supervision_load.run(base, args.since_days, trace, handoff_dir, args.out)
    if args.resume_metrics:
        trace = _trace_path(args.trace_file)
        return resume.run(base, args.since_days, trace, args.burn_file, args.out)
    out = Path(args.out) if args.out else Path(tempfile.gettempdir()) / "autosdd_waste_census.jsonl"
    since = time.time() - args.since_days * 86400
    data = collect(base, args.since_days, args.sid)
    rows: list[dict] = []

    def keep(ts):
        return ts is not None and ts >= since

    def total_tokens(ts):
        return sum(x["inp"] + x["cc"] + x["cr"] + x["out"] for x in ts)

    all_main_turns: list = []
    all_sub_turns: list = []
    for _sid, _p, t in data["main"]:
        annotate(t["turns"])
        all_main_turns += [x for x in t["turns"] if keep(x["ts_first"])]
    for _sid, _p, t in data["sub"]:
        annotate(t["turns"])
        all_sub_turns += [x for x in t["turns"] if keep(x["ts_first"])]
    print(
        f"母體：主控逐字稿 {len(data['main'])} 支／子代理 {len(data['sub'])} 支；近 "
        f"{args.since_days:g} 天；"
        f"主控回合 {len(all_main_turns)}／子代理回合 {len(all_sub_turns)}"
    )
    u_main = sum(units(x) for x in all_main_turns)
    u_sub = sum(units(x) for x in all_sub_turns)
    print(
        f"加權單位（推估）主控 {u_main:,.0f}／子代理 {u_sub:,.0f}；"
        f"原始 token 主控 {total_tokens(all_main_turns):,}／子代理 {total_tokens(all_sub_turns):,}"
    )
    cx = SimpleNamespace(
        args=args,
        data=data,
        rows=rows,
        rank=[],
        keep=keep,
        total_tokens=total_tokens,
        all_main_turns=all_main_turns,
        all_sub_turns=all_sub_turns,
        u_main=u_main,
        u_sub=u_sub,
    )
    for section in (
        sections_cache.sec_rewrites,
        sections_cache.sec_chains,
        sections_cuts.sec_cuts,
        sections_cuts.sec_voice,
        sections_cuts.sec_push,
        sections_misc.sec_incident,
        sections_misc.sec_orphans,
        sections_misc.sec_mech,
        sections_misc.sec_rank,
        sections_misc.sec_quota,
    ):
        section(cx)
    got = _print_metrics(cx)
    rows.append({"kind": "metrics", **got})
    skipped = sum(t.get("skipped", 0) for _s, _p, t in data["main"] + data["sub"])
    rows.append(
        {
            "kind": "summary",
            "main_turns": len(all_main_turns),
            "sub_turns": len(all_sub_turns),
            "units_main": u_main,
            "units_sub": u_sub,
            "skipped_lines": skipped,
        }
    )
    out.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, default=str) for r in rows) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"\n逐筆明細 {out}（{len(rows)} 列）")
    return 0
