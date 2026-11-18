# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""sentinel 家族：RV-N1 arm／N2 patrol tick／N3 撞線後 resume／N4 superseded 自我解除／N5 park 讓路。

全部用「工具副本沙盒」（見 `sessionctl_park` 模組 docstring）：被測的是沙盒內逐位元相同的
`tools/session_resume_planner.py`；tick 由本案例**手動叫起**（等同排程器叫的那一支，env 洗成沙盒）。
真排程名 `AutoSDD_Sentinel_<沙盒 sid>` 不在 RV 前綴下 ⇒ 一律經 `park_cleanup` 依完整沙盒 sid 精確移除。
絕不 tick／拆主控 session 或任何非沙盒 sid 的哨兵。不開任何互動視窗（N3 的續跑是無頭 `claude -p -r`，限 haiku）。
"""  # noqa: E501

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

from ..sandbox import Sandbox
from . import CaseContext, case
from .sessionctl_park import (
    PY,
    axis,
    ctl,
    ctl_env,
    get_task,
    install_tools,
    iso_in,
    make_package,
    park_cleanup,
    run,
    seed_session,
    write_quota,
)

PLANNER_REL = Path("tools") / "session_resume_planner.py"


def _env(sb: Sandbox, **extra) -> dict:
    e = ctl_env(sb, extra=extra)
    tmp = sb.root / "tmp"
    tmp.mkdir(exist_ok=True)
    e["TEMP"] = e["TMP"] = str(tmp)
    e["AUTOSDD_PLAN_DIR"] = str(tmp)  # 任務書落沙盒，不落真 ~/.autosdd/plans（planner 以 endurance_env.plan_dir() 解析）  # noqa: E501
    return e


def planner(sb: Sandbox, *args: str, timeout: int = 180, **extra) -> subprocess.CompletedProcess:
    return run([PY, str(sb.root / PLANNER_REL), *args], cwd=sb.root, env=_env(sb, **extra), timeout=timeout)  # noqa: E501


def task_name(sb: Sandbox) -> str:
    return f"AutoSDD_Sentinel_{sb.sid}"


def arm(ctx: CaseContext, sb: Sandbox, tp: Path) -> Path:
    r = planner(sb, "--arm-sentinel", "--session-id", sb.sid, "--transcript", str(tp))
    ctx.check(r.returncode == 0, f"--arm-sentinel rc={r.returncode}\n{r.stdout[-400:]}{r.stderr[-400:]}")  # noqa: E501
    plans = sorted((sb.root / "tmp").glob(f"*{sb.sid}*.md"))
    ctx.check(len(plans) == 1, f"找不到唯一的任務書（沙盒 tmp）：{plans}")
    return plans[0]


def tick(sb: Sandbox, plan: Path, **extra) -> subprocess.CompletedProcess:
    return planner(sb, "--sentinel-tick", "--plan", str(plan), "--task-name", task_name(sb), timeout=900, **extra)  # noqa: E501


def log_events(sb: Sandbox) -> list[dict]:
    out = []
    for p in (sb.root / "tmp").glob("autosdd_resume_log_*.jsonl"):
        for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                out.append(json.loads(ln))
            except ValueError:
                pass
    return out


def _stamps(path: Path) -> list[float]:
    out = []
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            ts = json.loads(ln).get("timestamp")
        except (ValueError, AttributeError):
            continue
        if isinstance(ts, str):
            out.append(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp())
    return out


def append_limit_event(tp: Path, at: datetime, text: str) -> None:
    """在沙盒逐字稿尾端植入 harness 的撞線記錄形狀（`type=assistant`、`message.model=<synthetic>`）。"""  # noqa: E501
    last = [json.loads(ln) for ln in tp.read_text(encoding="utf-8").splitlines() if ln.strip().startswith("{")][-1]  # noqa: E501
    rec = {"type": "assistant", "uuid": "00000000-0000-4000-8000-0000000000e1", "parentUuid": last.get("uuid"),  # noqa: E501
           "sessionId": last.get("sessionId"), "cwd": last.get("cwd"), "isSidechain": False,
           "timestamp": at.astimezone().isoformat(),
           "message": {"model": "<synthetic>", "role": "assistant", "content": [{"type": "text", "text": text}]}}  # noqa: E501
    with tp.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


@case("RV-N1", "sentinel", refs=(), sched=True)
def rv_n1(ctx: CaseContext) -> None:
    """`--arm-sentinel` 綁沙盒 sid ⇒ 排程器回讀 NextRunTime 值；`--remove-schtasks` 之後 Get-ScheduledTask 查不到。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    with park_cleanup(sb):
        tp = seed_session(ctx, sb)
        arm(ctx, sb, tp)
        t = get_task(task_name(sb))
        ctx.check(t is not None and bool(t["next_run_time"]), f"排程器查不到 {task_name(sb)} 或無 NextRunTime：{t}")  # noqa: E501
        nrt = datetime.fromisoformat(t["next_run_time"])
        ctx.check(timedelta(0) < nrt - datetime.now().astimezone() < timedelta(minutes=40), f"NextRunTime 不在預期巡邏間隔內：{nrt}")  # noqa: E501
        rm = planner(sb, "--remove-schtasks", "--task-name", task_name(sb))
        ctx.check(rm.returncode == 0 and get_task(task_name(sb)) is None, f"移除後仍查得到：rc={rm.returncode} {rm.stdout[-200:]}")  # noqa: E501
        ctx.evidence(f"RV-N1 {task_name(sb)} NextRunTime={t['next_run_time']}；--remove-schtasks 後查不到")  # noqa: E501


@case("RV-N2", "sentinel", refs=(), sched=True)
def rv_n2(ctx: CaseContext) -> None:
    """真 tick＋沙盒真逐字稿（剛有對話、無撞線）⇒ 判 patrol、重排下一次、不探測不 spawn。"""
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    with park_cleanup(sb):
        tp = seed_session(ctx, sb)
        plan = arm(ctx, sb, tp)
        r = tick(sb, plan)
        ctx.check(r.returncode == 0 and "哨兵判定 patrol" in r.stdout, f"應判 patrol：rc={r.returncode}\n{r.stdout[-500:]}{r.stderr[-300:]}")  # noqa: E501
        ev = {e["event"] for e in log_events(sb)}
        ctx.check("sentinel_woken" in ev and "sentinel_rearmed" in ev, f"痕跡缺 woken／rearmed：{ev}")  # noqa: E501
        ctx.check(not ({"probed", "resumed", "route_chosen"} & ev), f"patrol 不該探測／續跑：{ev}")
        t = get_task(task_name(sb))
        ctx.check(t is not None and bool(t["next_run_time"]), "patrol 後排程應仍在且有 NextRunTime")
        ctx.evidence(f"RV-N2 patrol；重排 NextRunTime={t['next_run_time']}；痕跡 {sorted(ev)}")


@case("RV-N3", "sentinel", refs=(), sched=True)
def rv_n3(ctx: CaseContext) -> None:
    """沙盒逐字稿植入撞線記錄（reset 已過）⇒ tick 判 probe→探針通→route RESUME→真 `claude -p -r`（限 haiku、無頭）續跑；
    續跑後逐字稿在撞線記錄之後出現新的真 assistant 回應。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    write_quota(sb, [axis("five_hour", 5, 240), axis("seven_day", 5, 5 * 1440)])
    with park_cleanup(sb):
        tp = seed_session(ctx, sb)
        from .sessionctl_park import age_transcript
        age_transcript(tp, 3 * 3600)
        target = (datetime.now().astimezone() - timedelta(minutes=100)).replace(minute=0, second=0, microsecond=0)  # noqa: E501
        h12 = target.hour % 12 or 12
        ev_at = target - timedelta(minutes=30)
        append_limit_event(tp, ev_at, f"You've hit your session limit · resets {h12}{'am' if target.hour < 12 else 'pm'}")  # noqa: E501
        plan = arm(ctx, sb, tp)
        write_quota(sb, [axis("five_hour", 5, 240), axis("seven_day", 5, 5 * 1440)])  # 刷新 TTL
        r = tick(sb, plan, AUTOSDD_MODEL_HELMSMAN="haiku", AUTOSDD_MODEL_SUBAGENT="haiku")
        out = r.stdout + r.stderr
        evs = log_events(sb)
        names = [e["event"] for e in evs]
        ctx.check("哨兵判定 probe" in r.stdout, f"應判 probe：\n{out[-700:]}")
        probed = [e for e in evs if e["event"] == "probed"]
        ctx.check(probed and probed[0].get("quota_open") is True, f"探針應回額度通：{probed}")
        route = [e for e in evs if e["event"] == "route_chosen"]
        ctx.check(route and route[0].get("strategy") == "SESSION_RESUME", f"選路應為 RESUME：{route}")  # noqa: E501
        resumed = [e for e in evs if e["event"] == "resumed"]
        ctx.check(resumed and resumed[0].get("rc") == 0, f"續跑應 rc 0：{resumed} 痕跡={names}\n{out[-500:]}")  # noqa: E501
        after = [s for s in _stamps(tp) if s > ev_at.timestamp() + 60]
        ctx.check(len(after) >= 2, "續跑後沙盒逐字稿沒有撞線記錄之後的新記錄")
        ctx.evidence(f"RV-N3 probe→RESUME→resumed rc=0；逐字稿撞線後新增 {len(after)} 筆；痕跡 {names}")  # noqa: E501


@case("RV-N4", "sentinel", refs=("V2",), sched=True)
def rv_n4(ctx: CaseContext) -> None:
    """V2：撞線事件＋本 session 閒置逾門檻＋同專案另一 session（真 haiku 跑出 ≥24 回合、時間戳展開成 ≥600s）
    於其後有活動 ⇒ tick 判 superseded：痕跡 `sentinel_superseded`、無 `probed`、排程查不到。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    (sb.root / "a.txt").write_text("rv\n", encoding="utf-8")
    with park_cleanup(sb):
        tp = seed_session(ctx, sb)
        from .sessionctl_park import age_transcript
        age_transcript(tp, 4 * 3600)
        last = max(_stamps(tp))
        append_limit_event(tp, datetime.fromtimestamp(last + 60).astimezone(), "You've hit your session limit · resets 9am")  # noqa: E501
        plan = arm(ctx, sb, tp)
        # 另一個真 session B（同專案、同 cwd）：真跑出 ≥24 個 assistant 回合
        sb2 = Sandbox(root=sb.root)
        r = ctx.run_claude(sb2, "Call the Read tool on a.txt thirty separate times, one call per step, then reply done.",  # noqa: E501
                           timeout_s=200, extra_args=("--permission-mode", "acceptEdits"))
        ctx.check(r.rc == 0, f"B session rc={r.rc} {r.stderr[:200]}")
        from ..transcript import find_transcript
        tb = find_transcript(sb2.sid)
        ctx.check(tb is not None, "B session 沒有逐字稿")
        recs = [json.loads(ln) for ln in tb.read_text(encoding="utf-8").splitlines() if ln.strip().startswith("{")]  # noqa: E501
        ts = [datetime.fromisoformat(r_["timestamp"].replace("Z", "+00:00")).timestamp() for r_ in recs if isinstance(r_.get("timestamp"), str)]  # noqa: E501
        t0, span = min(ts), max(ts) - min(ts)
        k = max(1.0, 900.0 / max(span, 1.0))
        base = datetime.now().timestamp() - 3600
        for r_ in recs:
            if isinstance(r_.get("timestamp"), str):
                t = datetime.fromisoformat(r_["timestamp"].replace("Z", "+00:00")).timestamp()
                r_["timestamp"] = datetime.fromtimestamp(base + (t - t0) * k).astimezone().isoformat()  # noqa: E501
        tb.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in recs) + "\n", encoding="utf-8", newline="\n")  # noqa: E501
        turns = sum(1 for x in recs if x.get("type") == "assistant")
        ctx.check(turns >= 24, f"B session 只有 {turns} 個 assistant 回合（需 ≥24）")
        res = tick(sb, plan, AUTOSDD_STALE_SESSION_HOURS="1")
        names = [e["event"] for e in log_events(sb)]
        ctx.check("sentinel_superseded" in names, f"痕跡缺 sentinel_superseded：{names}\n{res.stdout[-500:]}{res.stderr[-300:]}")  # noqa: E501
        ctx.check("probed" not in names and "resumed" not in names, f"superseded 不該探測／續跑：{names}")  # noqa: E501
        ctx.check(get_task(task_name(sb)) is None, "superseded 後排程應查不到")
        ctx.evidence(f"RV-N4 B session {turns} 回合；痕跡 sentinel_superseded；排程已拆")


@case("RV-N5", "sentinel", refs=(), sched=True)
def rv_n5(ctx: CaseContext) -> None:
    """park armed ⇒ 哨兵 tick 一律 patrol 讓路（即使本 session 已閒置到本該 disarm）；park 取消後同一份逐字稿
    再 tick ⇒ 恢復原判準（disarm，排程查不到）。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    with park_cleanup(sb):
        tp = seed_session(ctx, sb)
        from .sessionctl_park import age_transcript
        age_transcript(tp, 6 * 3600)
        pkg = make_package(ctx, sb)
        plan = arm(ctx, sb, tp)
        p = ctl(sb, "park", "--session-id", sb.sid, "--pkg", str(pkg), "--at", iso_in(1500), "--why", "realverify N5 讓路",  # noqa: E501
                extra={"TEMP": str(sb.root / "tmp"), "TMP": str(sb.root / "tmp")})
        ctx.check(p.returncode == 0, f"park rc={p.returncode} {p.stderr[-300:]}")
        r1 = tick(sb, plan)
        ctx.check("哨兵判定 patrol" in r1.stdout and "park 排程待命" in r1.stdout, f"park armed 時應 patrol 讓路：\n{r1.stdout[-500:]}")  # noqa: E501
        ctx.check(get_task(task_name(sb)) is not None, "讓路時哨兵排程應仍在")
        c = ctl(sb, "park", "--cancel", "--session-id", sb.sid)
        ctx.check(c.returncode == 0, f"park --cancel rc={c.returncode}")
        r2 = tick(sb, plan)
        ctx.check("哨兵判定 disarm" in r2.stdout, f"park 取消後應恢復 disarm：\n{r2.stdout[-500:]}")
        ctx.check(get_task(task_name(sb)) is None, "disarm 後排程應查不到")
        time.sleep(0)
        ctx.evidence("RV-N5 park armed⇒patrol（讓路）；cancel 後⇒disarm、哨兵排程拆除")
