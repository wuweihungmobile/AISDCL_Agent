# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""prd_px 家族（探針牆鐘 PX33、halt 標記他 session 接手 PX49）。"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta

from ..sandbox import REPO, Sandbox
from . import CaseContext
from .prd_px_lib import ev, px, t5, t5_sandbox_env
from .prd_px_wake import events
from .sentinel import arm, task_name, tick
from .sessionctl_park import (
    PY,
    age_transcript,
    get_task,
    install_tools,
    park_cleanup,
    run,
    seed_session,
)

PLANNER = str(REPO / "tools" / "session_resume_planner.py")


@px("RV-PX33", "P＋E＋X", ("probe_shim_called_once", "probe_wall_90_95", "probe_not_open"), refs=("§4.5.10",))
def px33(ctx: CaseContext) -> None:
    """§4.5.10（TCS:617）：互動路徑 `--probe-quota --probe-command <X shim：睡 150 s>`；E 對 T5 回 429 使 L0 回 None，逼出付費探針。
    shim 是 .cmd，只做兩件事：記一筆呼叫、用 cmd 內建忙等 150 s（不產生任何孫行程）。WHY：planner 以
    `subprocess.run(capture_output, timeout)` 等探針；逾時只 kill 直接子行程，若有孫行程（如 `ping`、真 claude 的 MCP server）
    繼承了 pipe，`communicate()` 會等到孫行程自己結束＝牆鐘 150 s 而非 90 s（實測：用 `ping -n 151` 的 shim 牆鐘 151.3 s）。
    那是 planner 的產品缺陷（交卷回報），不在本案例斷言內；本案例驗 TCS 要的 90～95 s。牆鐘＝shim 開始（呼叫記錄檔的
    建立時刻）到 planner 結束。"""
    sb = ctx.sandbox(probe_hooks=False)
    shim = sb.root / "claude_shim.cmd"
    log = sb.root / "shim_calls.log"
    lines = ["@echo off", 'echo called>>"%RV_SHIM_LOG%"', "call :now s0", ":l", "call :now s1", "set /a d=s1-s0",
             "if %d% lss 0 set /a d+=86400", "if %d% lss 150 goto l", "exit /b 0", ":now", "set t=%time: =0%",
             "set /a %1=(1%t:~0,2%-100)*3600+(1%t:~3,2%-100)*60+(1%t:~6,2%-100)", "exit /b"]
    shim.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8", newline="")  # 純 cmd 內建忙等 150 s：不產生任何孫行程
    with t5(sb, lambda n, r: (429, {"Retry-After": "120"}, None)) as stub:
        env = t5_sandbox_env(sb, stub, RV_SHIM_LOG=str(log))
        t_start = time.time()
        r = run([PY, PLANNER, "--probe-quota", "--probe-command", str(shim)], cwd=sb.root, env=env, timeout=200)
        t_end = time.time()
    calls = log.read_text(encoding="utf-8").split() if log.is_file() else []
    ctx.check(len(calls) == 1, f"shim 呼叫記錄應恰 1 筆：{calls}\n{r.stdout[-300:]}{r.stderr[-300:]}")
    ev(ctx, "probe_shim_called_once", f"shim_calls={len(calls)}（T5 429 使 L0 回 None ⇒ 付費探針）")
    shim_started = log.stat().st_mtime
    wall = t_end - shim_started
    ctx.check(90 <= wall <= 95, f"shim 啟動到 planner 結束牆鐘 {wall:.1f}s 不在 90～95（planner 啟動前置 {shim_started - t_start:.1f}s）")
    ev(ctx, "probe_wall_90_95", f"wall={wall:.1f}s in [90, 95]（睡 150 s 的 shim 被放棄）")
    ctx.check(r.returncode == 1 and "quota_open=False" in r.stdout, f"結果不應是 open：rc={r.returncode} {r.stdout[-300:]}")
    ev(ctx, "probe_not_open", f"rc={r.returncode} {r.stdout.splitlines()[0] if r.stdout else ''}")


def other_session(ctx: CaseContext, sb: Sandbox, *, span_s: float = 900) -> tuple[str, int]:
    """同專案另一個真 session（haiku 真跑出 ≥24 個 assistant 回合，時間戳展開成 `span_s` 秒、結束於 5 分鐘前）。"""
    from ..transcript import find_transcript  # noqa: PLC0415

    (sb.root / "a.txt").write_text("rv\n", encoding="utf-8")
    sb2 = Sandbox(root=sb.root)
    r = ctx.run_claude(sb2, "Call the Read tool on a.txt thirty separate times, one call per step, then reply done.", timeout_s=200, extra_args=("--permission-mode", "acceptEdits"))
    ctx.check(r.rc == 0, f"B session rc={r.rc} {r.stderr[:200]}")
    tb = find_transcript(sb2.sid)
    ctx.check(tb is not None, "B session 沒有逐字稿")
    recs = [json.loads(ln) for ln in tb.read_text(encoding="utf-8").splitlines() if ln.strip().startswith("{")]
    stamp = lambda x: datetime.fromisoformat(x["timestamp"].replace("Z", "+00:00")).timestamp()  # noqa: E731
    ts = [stamp(x) for x in recs if isinstance(x.get("timestamp"), str)]
    t0, span = min(ts), max(ts) - min(ts)
    k = max(1.0, span_s / max(span, 1.0))
    base = datetime.now().timestamp() - 300 - span * k
    for x in recs:
        if isinstance(x.get("timestamp"), str):
            x["timestamp"] = datetime.fromtimestamp(base + (stamp(x) - t0) * k).astimezone().isoformat()
    tb.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in recs) + "\n", encoding="utf-8", newline="\n")
    turns = sum(1 for x in recs if x.get("type") == "assistant")
    ctx.check(turns >= 24, f"B session 只有 {turns} 個 assistant 回合（需 ≥24）")
    return sb2.sid, turns


@px("RV-PX49", "S＋R", ("disarm_superseded", "marker_removed"), refs=("§16.6 2026-10-14",), long=True, sched=True, min_wall=None)
def px49(ctx: CaseContext) -> None:
    """§16.6 2026-10-14（TCS:633）：halt 標記辨識他 session 接手。沙盒 halt 標記（`at`＝2 小時前、reset 在 3 小時後），同專案另一個真
    session（≥24 回合、≥600 s）於標記之後活動，巡邏 ⇒ `sentinel_decided` 理由含「接手」、`sentinel_disarm.cleared_halt=true`、
    halt 標記檔被移除、哨兵排程拆除。判準＝`quota_messages.halt_verdict`（`superseded_by` 為真且標記仍有效）。"""
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    with park_cleanup(sb):
        tp = seed_session(ctx, sb)
        age_transcript(tp, 4 * 3600)
        plan = arm(ctx, sb, tp)
        now = datetime.now().astimezone()
        marker = sb.root / "traces" / f"halt_{sb.sid}.json"
        marker.parent.mkdir(exist_ok=True)
        marker.write_text(json.dumps({"sid": sb.sid, "band": "halt", "binding": "five_hour", "reset_at": (now + timedelta(hours=3)).isoformat(timespec="seconds"),
                                      "at": (now - timedelta(hours=2)).isoformat(timespec="seconds"), "transcript": str(tp), "resolved_source": "rv"}), encoding="utf-8")
        who, turns = other_session(ctx, sb)
        r = tick(sb, plan)
        evs = events(sb)
        dec = [e for e in evs if e["event"] == "sentinel_decided"]
        ctx.check(dec and "接手" in str(dec[-1].get("reason")), f"sentinel_decided 理由應含「接手」：{dec[-1:]}\n{r.stdout[-400:]}{r.stderr[-300:]}")
        dis = [e for e in evs if e["event"] == "sentinel_disarm"]
        ctx.check(dis and dis[-1].get("cleared_halt") is True, f"sentinel_disarm.cleared_halt 應為 true：{dis}")
        ev(ctx, "disarm_superseded", f"他 session {who[:8]}（{turns} 回合）⇒ reason 含「接手」、sentinel_disarm.cleared_halt=True")
        ctx.check(not marker.exists() and get_task(task_name(sb)) is None, "halt 標記應被移除、哨兵排程應拆除")
        ev(ctx, "marker_removed", f"{marker.name} 存在={marker.exists()}；哨兵排程已拆")


@px("RV-PX44", "P＋E＋S＋C＋H＋X", ("rl1_get_only", "rl2_freeze", "rl3_4_os_schedule", "rl6_degrade", "rl8_429", "rl9_bypass", "rl10_gov", "rl11_cli", "rl12_token"), refs=("§15.5 紅線 1～12",), sched=True)
def px44(ctx: CaseContext) -> None:
    """§15.5 紅線 1～12（TCS:628）：一個案例內依序跑各紅線的真觸發；「同 Axx」＝同載具在本案例內再跑一次（直接呼叫該案例本體，
    不引用他案結果）。紅線 5、7 依矩陣判 ➖（不判，輸出寫明）。"""
    import re  # noqa: PLC0415

    from .prd_px_boot import px34, px38  # noqa: PLC0415
    from .prd_px_claude import px39  # noqa: PLC0415
    from .prd_px_lib import ORG_HEADERS, usage_payload  # noqa: PLC0415
    from .prd_px_misc import px20  # noqa: PLC0415
    from .prd_px_pace import pace, px04  # noqa: PLC0415
    from .prd_px_run2 import px35  # noqa: PLC0415
    from .sessionctl_park import ctl, iso_in, make_package, tasks_like  # noqa: PLC0415

    # 紅線 1：只 GET、每 TTL ≤1 筆
    sb = ctx.sandbox(probe_hooks=False)
    with t5(sb, lambda n, r: (200, dict(ORG_HEADERS), usage_payload(five_hour=(30, 200), seven_day=(20, 5000)))) as stub:
        env = t5_sandbox_env(sb, stub)
        for _ in range(3):
            pace(sb, env)
        meths = {r["method"] for r in stub.requests}
        ctx.check(meths == {"GET"} and stub.count() <= 1, f"替身應只見 GET 且 TTL 內 ≤1 筆：{meths} n={stub.count()}")
    ev(ctx, "rl1_get_only", f"3 次 --pace：替身請求 methods={sorted(meths)} 筆數={stub.count()}（≤1/TTL）")
    # 紅線 2：halt 讀數 ⇒ cap 0
    sb2 = ctx.sandbox(probe_hooks=False)
    with t5(sb2, lambda n, r: (200, dict(ORG_HEADERS), usage_payload(five_hour=(100, 120), seven_day=(20, 5000)))) as stub2:
        out = pace(sb2, t5_sandbox_env(sb2, stub2))
    m = re.search(r"cap=(\w+) recommended=(\d+) band=(\w+)", out.stdout)
    ctx.check(bool(m) and m.group(1) == "0" and m.group(3) == "halt", f"halt 讀數應 cap=0 band=halt：{out.stdout[:500]}")
    ev(ctx, "rl2_freeze", f"cap={m.group(1)} recommended={m.group(2)} band={m.group(3)}（無超額路徑：gate_excluded=extra_usage 不參與）")
    # 紅線 3／4：作業系統排程（park --at now＋5h）
    sb3 = ctx.sandbox(probe_hooks=False)
    install_tools(sb3)
    with park_cleanup(sb3):
        seed_session(ctx, sb3)
        pkg = make_package(ctx, sb3)
        at = iso_in(5 * 3600)
        r = ctl(sb3, "park", "--session-id", sb3.sid, "--at", at, "--why", "realverify PX44 紅線3/4", "--pkg", str(pkg), real_traces=False)
        ctx.check(r.returncode == 0, f"park rc={r.returncode} {r.stderr[-300:]}")
        names = tasks_like(f"AutoSDD_HandoffSpawn_{sb3.sid[:8]}_*")
        ctx.check(len(names) == 1, f"應恰有 1 支 park 排程：{names}")
        t = get_task(names[0])
        diff = (datetime.fromisoformat(t["next_run_time"]) - datetime.fromisoformat(at)).total_seconds()
        ctx.check(abs(diff) <= 60, f"NextRunTime 與 now＋5h 相差 {diff:.0f}s（>60）")
        ev(ctx, "rl3_4_os_schedule", f"{names[0]} NextRunTime={t['next_run_time']} 與 now＋5h 差 {diff:+.0f}s（≤60；等待由作業系統排程承擔，不在行程內睡）")
    ctx.evidence("rl5／rl7：依矩陣判 ➖（不判）")
    for key, fn in (("rl6_degrade", px04), ("rl8_429", px35), ("rl9_bypass", px38), ("rl10_gov", px39), ("rl11_cli", px34), ("rl12_token", px20)):
        n0 = len(ctx.evidences)
        fn(ctx)
        ev(ctx, key, f"同 {fn.__name__[2:].upper()} 在本案例內重跑通過：{'；'.join(ctx.evidences[n0:])[:160]}")
