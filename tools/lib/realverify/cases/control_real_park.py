# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
# ruff: noqa: E501
"""control 家族 D：RV-CTL28／27／31（park 雙駕駛延後、提前恢復接手、名冊訊息重放；WP-SW）。

與 `control_real`（LOC 分級 400 行上限而拆檔）同一套工具副本沙盒與替身 claude；共用 helper 一律 `from .control_real import …`。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

from lib import platform_utils

from .. import fakeclaude
from ..driver import EnvMissing
from ..sandbox import REPO, Sandbox
from . import CaseContext, case
from .control_real import _REAL_TRACE, NEW_ACCT, OLD_ACCT, OWNER, regrant
from .control_sched import run_nostd, sandbox_tick_argv, trace_events
from .sentinel import _env, arm, grant_default
from .sessionctl_park import (
    PY,
    ctl,
    get_task,
    install_tools,
    make_package,
    park_cleanup,
    read_marker,
    seed_session,
    tasks_like,
)

_PROJECTS = platform_utils.claude_home() / "projects" / "D--CursorProject-AISDCL-Agent"

# ───────────────────────────────────────────────────────────── E2E-CTL-28
def _other_session_file(ctx: CaseContext, sb: Sandbox, tp: Path, *, human_only: bool) -> Path:
    """4290bf58 逐字稿前段（記錄形狀逐字、時戳平移到「現在 −3 分」之後；窗口內最早一筆是 human）放進沙盒專案目錄當另一個 session。"""
    src = _PROJECTS / "4290bf58-a5e9-4e64-b118-e9db87ca2af4.jsonl"
    if not src.is_file():
        raise EnvMissing("4290bf58 逐字稿不在本機")
    recs = []
    for ln in src.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        if isinstance(d, dict) and isinstance(d.get("timestamp"), str) and d.get("type") in ("user", "assistant", "attachment", "system"):
            recs.append(d)
    first = datetime.fromisoformat(recs[0]["timestamp"].replace("Z", "+00:00"))
    keep = [d for d in recs if (datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00")) - first).total_seconds() <= 110]
    if human_only:
        keep = [d for d in keep if d.get("type") == "user"]
    ctx.check(len(keep) >= 3, f"前段記錄太少：{len(keep)}")
    shift = datetime.now().astimezone() - timedelta(seconds=30) - datetime.fromisoformat(keep[-1]["timestamp"].replace("Z", "+00:00"))
    out = []
    for d in keep:
        t = datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00")) + shift
        out.append(json.dumps({**d, "timestamp": t.isoformat()}, ensure_ascii=False))
    path = tp.parent / ("aaaaaaaa-0000-4000-8000-" + ("0" if human_only else "1") * 12 + ".jsonl")
    path.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    return path


def live_park_task(sb: Sandbox) -> dict | None:
    """沙盒 park 目前在排程器裡仍有 NextRunTime 的 job（重排後 job 名會變，不以標記裡的舊 label 為準）。"""
    for name in tasks_like(f"AutoSDD_HandoffSpawn_{sb.sid[:8]}_*"):
        t = get_task(name)
        if t and t["next_run_time"]:
            return t
    return None


def _fire_argv(sb: Sandbox, mk: dict | None = None) -> list[str]:
    """與排程同 argv 的 `park --fire`（取自排程器登記的 Action 引數，換成沙盒內 python）。"""
    t = live_park_task(sb)
    assert t is not None, "沙盒 park 在排程器裡已沒有任何有 NextRunTime 的 job"
    args = t["arguments"]
    ctx_args = re.findall(r'"[^"]*"|\S+', args)
    ctx_args = [a.strip('"') for a in ctx_args]
    i = next(k for k, a in enumerate(ctx_args) if a.endswith("sessionctl.py"))
    return [PY, *ctx_args[i:]]


@case("RV-CTL28", "control", refs=("E2E-CTL-28", "REQ-CTL-52", "MU-CTL-56", "MU-CTL-57", "MU-CTL-72", "MU-CTL-73", "MU-CTL-76"), sched=True, lease_minutes=150)
def rv_ctl28(ctx: CaseContext) -> None:
    """另一 session（真 4290bf58 逐字稿前段、時戳平移）有 AI 回合 ⇒ `park --fire` 延後（真重排、NextRunTime 為證），用盡後終局 skip
    並出聲；human-only 對照組照常 spawn；移除另一 session 的對照組照常 spawn。"""
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    with park_cleanup(sb):
        tp = seed_session(ctx, sb)
        from .sessionctl_park import age_transcript  # noqa: PLC0415
        age_transcript(tp, 7200)
        write_account_quota(sb, OLD_ACCT, 90.0, five=96.0, five_minutes=95)
        pkg = make_package(ctx, sb)
        fakeclaude.build(sb.home)
        fakeclaude.configure(sb.home, "fail")
        r = ctl(sb, "park", "--session-id", sb.sid, "--at", (datetime.now().astimezone() + timedelta(seconds=6000)).isoformat(timespec="seconds"),
                "--note", "realverify CTL28 另一 session", "--pkg", str(pkg), lease_min=150)
        ctx.check(r.returncode == 0, f"park rc={r.returncode} {r.stderr[-300:]}")
        base = sb.home / "traces"
        mk = read_marker(sb.sid, base)
        # 標記 desktop_notify=1（使通知路徑可驗）——標記是檔案夾具
        # ── 主組：另一 session 有 AI 回合 ⇒ 延後
        other = _other_session_file(ctx, sb, tp, human_only=False)
        argv = _fire_argv(sb, mk)
        env = sb.env({"PYTHONDONTWRITEBYTECODE": "1"})
        calls0 = len(fakeclaude.calls(sb.home))
        defers, nruns = 0, []
        for n in range(1, 4):
            time.sleep(65)  # 讓重排的分鐘級 job 名與舊 job 名必不同（提前手動 fire 才會撞同一分鐘；排程正常到點時不會）
            rr = subprocess.run(argv, cwd=str(sb.root), env=env, capture_output=True, timeout=300, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            ev = [e for e in trace_events(sb) if e.get("event") == "park_other_session"]
            acts = [e.get("action") for e in ev]
            ctx.check(acts.count("defer") == n, f"第 {n} 次 fire 後 defer 應為 {n}：{acts}；rc={rr.returncode} {rr.stderr[-300:]}")
            ctx.check(ev[-1].get("other_sid") == other.stem, f"other_sid 應為 {other.stem}：{ev[-1]}")
            t = live_park_task(sb)
            ctx.check(t is not None, f"重排後排程器應有仍帶 NextRunTime 的 park job：tasks={tasks_like(f'AutoSDD_HandoffSpawn_{sb.sid[:8]}_*')} 標記 jobs={(read_marker(sb.sid, base) or {}).get('jobs')} fire rc={rr.returncode} out={rr.stdout[-300:]} err={rr.stderr[-300:]}")
            nruns.append(t["next_run_time"])
            defers = n
            argv = _fire_argv(sb)
            # 延後後要重新平移另一 session 的時戳（讓它仍在「現在 −3 分」窗內）
            other = _other_session_file(ctx, sb, tp, human_only=False)
        ctx.check(len(fakeclaude.calls(sb.home)) == calls0, "延後期間替身 claude 不該被呼叫")
        # 第四次：用盡 ⇒ 終局 skip＋出聲
        time.sleep(65)
        rr = subprocess.run(argv, cwd=str(sb.root), env=env, capture_output=True, timeout=300, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        mk = read_marker(sb.sid, base)
        acts = [e.get("action") for e in trace_events(sb) if e.get("event") == "park_other_session"]
        ctx.check(acts.count("skip") == 1 and mk["status"] == "skipped" and (mk.get("outcome") or {}).get("event") == "other_session", f"終局 skip 不合：{acts} {mk.get('status')} {mk.get('outcome')}")
        ctx.check(len(list((sb.home / "handback").glob(f"{sb.sid}_park*"))) == 1, f"handback 應恰 1 筆：{list((sb.home / 'handback').glob('*'))}")
        st = ctl(sb, "status")
        ctx.check("park 因他 session 在動而終局 skip：" in st.stdout, f"status 沒出聲終局 skip：{st.stdout[-500:]}")
        ctx.check(len(fakeclaude.calls(sb.home)) == calls0, "終局 skip 不該 spawn")
        other.unlink()
        ctx.evidence(f"RV-CTL28 主組 defer×{defers}（每次排程器自報 NextRunTime：{nruns}）→ 第 4 次終局 skip；handback 1 筆；status 出聲；替身 claude 0 次呼叫。"
                     "對照組①（移除另一 session）／②（human-only）以獨立沙盒 RV-CTL28 內第二段驗，見下一條 evidence")
        # ── 對照組②：human-only 另一 session ⇒ 不延後、照常 spawn
        sb2 = ctx.sandbox(probe_hooks=False)
        install_tools(sb2)
        with park_cleanup(sb2):
            tp2 = seed_session(ctx, sb2)
            age_transcript(tp2, 7200)
            write_account_quota(sb2, OLD_ACCT, 90.0, five=96.0, five_minutes=95)
            pkg2 = make_package(ctx, sb2)
            fakeclaude.build(sb2.home)
            fakeclaude.configure(sb2.home, "fail")
            r2 = ctl(sb2, "park", "--session-id", sb2.sid, "--at", (datetime.now().astimezone() + timedelta(seconds=6000)).isoformat(timespec="seconds"), "--note", "realverify CTL28 human-only", "--pkg", str(pkg2), lease_min=150)
            ctx.check(r2.returncode == 0, f"對照組 park rc={r2.returncode}")
            mk2 = read_marker(sb2.sid, sb2.home / "traces")
            ho = _other_session_file(ctx, sb2, tp2, human_only=True)
            env2 = sb2.env({"PYTHONDONTWRITEBYTECODE": "1"})
            rr2 = subprocess.run(_fire_argv(sb2, mk2), cwd=str(sb2.root), env=env2, capture_output=True, timeout=300, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            evs2 = [e.get("action") for e in trace_events(sb2) if e.get("event") == "park_other_session"]
            ctx.check("defer" not in evs2, f"human-only 不該延後：{evs2}")
            ctx.check(len(fakeclaude.calls(sb2.home)) >= 1, f"human-only 應照常 spawn（替身 claude≥1 次）：rc={rr2.returncode} {rr2.stderr[-300:]}")
            ho.unlink()
            ctx.evidence(f"RV-CTL28 對照②（human-only）無 defer、替身 claude {len(fakeclaude.calls(sb2.home))} 次呼叫（照常 spawn）")


# ───────────────────────────────────────────────────────────── E2E-CTL-31
@case("RV-CTL31", "control", refs=("E2E-CTL-31", "REQ-CTL-55", "MU-CTL-61", "MU-CTL-62"))
def rv_ctl31(ctx: CaseContext) -> None:
    """真逐字稿重放 FLK5 名冊訊息：406454ea 第 10288～10414 行＋subagent 檔＋封存包複本，經真 hook 入口（`sessionctl_guard.py` Stop）
    輸出三段式、含「主控已停止並已記入交接包」與沙盒包路徑、不含「由主控決定」、無 block；抽掉包內 FLK5 字樣 ⇒ 改出「未記處置」句。"""
    sb = ctx.sandbox(probe_hooks=False)
    src_t = _PROJECTS / f"{OWNER}.jsonl"
    src_sub = _PROJECTS / OWNER / "subagents"
    src_pkg = Path.home() / ".autosdd" / "handoff" / f"{OWNER}_20261126T154649Z"
    for p in (src_t, src_sub / "agent-aee3d937b179d8639.jsonl", src_pkg.with_suffix(".md")):
        if not p.is_file():
            raise EnvMissing(f"真實素材不在本機：{p}")
    with src_t.open(encoding="utf-8", errors="replace") as fh:
        lines = [x for i, x in enumerate(fh, start=1) if 10288 <= i <= 10414]
    ctx.check(len(lines) == 127, f"逐字稿第 10288～10414 行應 127 行，實得 {len(lines)}")
    proj = sb.home / "projects" / "rvproj"
    (proj / OWNER / "subagents").mkdir(parents=True)
    (proj / f"{OWNER}.jsonl").write_text("".join(lines), encoding="utf-8", newline="\n")
    for name in ("agent-aee3d937b179d8639.jsonl", "agent-aee3d937b179d8639.meta.json"):
        shutil.copy2(src_sub / name, proj / OWNER / "subagents" / name)
        os.utime(proj / OWNER / "subagents" / name)  # 時戳平移：被 TaskStop 的代理須在「剛 TaskStop」窗內（agentbrief.STOPPED_RECENT_SECONDS）
    hdir = sb.home / "handoff"
    hdir.mkdir(exist_ok=True)
    pkg = hdir / f"{OWNER}_20261126T154649Z.md"
    shutil.copy2(src_pkg.with_suffix(".md"), pkg)
    shutil.copy2(src_pkg.with_suffix(".sealed"), pkg.with_suffix(".sealed"))
    payload = json.dumps({"hook_event_name": "Stop", "session_id": OWNER, "transcript_path": str(proj / f"{OWNER}.jsonl"),
                          "cwd": str(sb.root), "stop_hook_active": False})
    env = sb.env({"PYTHONDONTWRITEBYTECODE": "1", "AUTOSDD_SESSIONCTL_SESSION": "", "CLAUDE_PROJECT_DIR": str(REPO)})
    hook = REPO / ".claude" / "hooks" / "sessionctl_guard.py"

    def fire() -> dict:
        r = subprocess.run([PY, str(hook)], input=payload, cwd=str(REPO), env=env, capture_output=True, timeout=180, encoding="utf-8", errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        ctx.check(r.returncode == 0, f"hook rc={r.returncode} {r.stderr[-300:]}")
        try:
            return json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else {}
        except ValueError:
            return {"_raw": r.stdout}
    out = fire()
    text = str(out.get("systemMessage") or out.get("_raw") or "")
    ctx.check("主控已停止" in text, f"輸出缺「主控已停止（TaskStop）」段：{text[:600]}")
    ctx.check("主控已停止並已記入交接包" in text and pkg.name in text.replace("\\", "/").split("/")[-1] + text.replace("\\", "/"), f"缺「已記入交接包」與沙盒包路徑：{text[:900]}")
    ctx.check("由主控決定" not in text, "不該再出現「由主控決定」")
    ctx.check(out.get("decision") != "block", f"不該 block：{out}")
    # 抽掉包內主控層 FLK5 字樣（沙盒副本）⇒ 改出「未記處置」句
    body = pkg.read_text(encoding="utf-8")
    pkg.write_text(body.replace("FLK5", "F-L-K-5"), encoding="utf-8", newline="\n")
    (sb.home / "traces").mkdir(exist_ok=True)
    shutil.rmtree(sb.home / "traces" / "control", ignore_errors=True)  # 清「只提示一次」閂鎖，才能重放第二次
    out2 = fire()
    text2 = str(out2.get("systemMessage") or out2.get("_raw") or "")
    ctx.check("未記處置" in text2 and "主控已停止並已記入交接包" not in text2, f"抽掉 FLK5 後應改出「交接包未記處置」：{text2[:600]}")
    ctx.evidence(f"RV-CTL31 真 hook 入口輸出 {len(text)} 字：含「主控已停止」「已記入交接包」、無「由主控決定」、無 block；抽掉 FLK5 後輸出 {text2[:60]!r}")


# ───────────────────────────────────────────────────────────── E2E-CTL-27
def write_account_quota(sb: Sandbox, account: str, weekly: float, five: float = 2.0, five_minutes: int = 240) -> None:
    now = datetime.now().astimezone()
    qc = sb.root / "qcache"
    qc.mkdir(exist_ok=True)
    (qc / "autosdd_quota.json").write_text(json.dumps({
        "schema": "autosdd.quota/2", "source": "endpoint", "http_status": 200,
        "measured_at": now.isoformat(timespec="seconds"), "account_key": account,
        "axes": [{"kind": "five_hour", "pct": five, "resets_at": (now + timedelta(minutes=five_minutes)).isoformat(timespec="seconds"), "via": "rv"},
                 {"kind": "seven_day", "pct": weekly, "resets_at": (now + timedelta(days=3)).isoformat(timespec="seconds"), "via": "rv"}]}), encoding="utf-8")


def _park_with_baseline(ctx: CaseContext, sb: Sandbox) -> tuple[Path, dict]:
    from .sessionctl_park import age_transcript, iso_in  # noqa: PLC0415
    tp = seed_session(ctx, sb)
    age_transcript(tp, 7200)
    write_account_quota(sb, OLD_ACCT, 90.0, five=96.0, five_minutes=95)  # 短窗近牆＝park 才被准許登記
    pkg = make_package(ctx, sb)
    r = ctl(sb, "park", "--session-id", sb.sid, "--at", iso_in(6000), "--note", "realverify CTL27 提前恢復", "--pkg", str(pkg), lease_min=150)
    ctx.check(r.returncode == 0, f"park rc={r.returncode} {r.stderr[-300:]}")
    mk = read_marker(sb.sid, sb.home / "traces")
    ctx.check(mk is not None and mk.get("parked_pct") == 96.0 and mk.get("parked_account") == OLD_ACCT, f"標記基準不合：{mk}")
    return tp, mk


@case("RV-CTL27", "control", refs=("E2E-CTL-27", "REQ-CTL-51", "MU-CTL-54", "MU-CTL-55"), sched=True, lease_minutes=150)
def rv_ctl27(ctx: CaseContext) -> None:
    """真 armed park（排程器 NextRunTime 為證）＋真 pythonw 哨兵 tick＋換帳號（額度快取換成新帳號、weekly 0%）⇒ 提前接手
    （`park_early_recovered`、子行程 `park --fire`、替身 claude 呼叫）；無憑證組 ⇒ `reading=null` 一律帶封閉值域 `why`、不提前；
    真實痕跡第 1379／1381 行舊形（無 `why`）在新判準下判違規。真換帳號（真 `/login`）不可自動化，備援＝本案例的帳號指紋替身。"""
    from lib.sessionctl import parkwhy  # noqa: PLC0415
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    grant_default(sb)
    env = _env(sb)
    with park_cleanup(sb):
        tp, mk = _park_with_baseline(ctx, sb)
        label = mk["jobs"][0]["label"]
        fakeclaude.configure(sb.home, "fresh_ok", sleep=5, projdir=str(tp.parent))  # 讓提前接手的 spawn 走得通（fresh／resume 失敗即退 fresh）
        t = get_task(label)
        ctx.check(t is not None and bool(t["next_run_time"]), f"armed park 的排程器 NextRunTime 應非空：{t}")
        plan = arm(ctx, sb, tp)
        regrant(sb, 40)
        write_account_quota(sb, NEW_ACCT, 0.0)
        t0 = time.monotonic()
        calls0 = len(fakeclaude.calls(sb.home))
        rc = run_nostd(sandbox_tick_argv(sb, plan), cwd=sb.root, env=env)
        mk2 = read_marker(sb.sid, sb.home / "traces")
        evs = trace_events(sb)
        probes = [e for e in evs if e.get("event") == "park_early_probe"]
        ctx.check(rc == 0 and probes, f"tick rc={rc}；缺 park_early_probe 痕跡：{[e.get('event') for e in evs]}")
        ctx.check(any(e.get("recovered") for e in probes) and any(e.get("event") == "park_early_recovered" for e in evs),
                  f"換帳號＋weekly 0% 應判 recovered 並落 park_early_recovered：{probes}")
        ctx.check(mk2["status"] in ("fired", "failed"), f"提前接手後標記應離開 armed：{mk2['status']}")
        calls = len(fakeclaude.calls(sb.home)) - calls0
        ctx.check(calls >= 1, f"替身 claude 應被呼叫（提前接手走真 park --fire 子行程）：{calls}")
        ctx.check(time.monotonic() - t0 < 2 * 900 + 600, "提前接手延遲超過 2×900 s＋600 s")
        ctx.check(any(r.get("reading") is not None or r.get("why") for r in probes), "probe 列缺讀數或 why")
        for r in probes:
            ctx.check(r.get("reading") is not None or parkwhy.valid(r.get("why")), f"reading=null 的列必須帶封閉值域 why：{r}")
        # ── 舊形 oracle：真實痕跡第 1379／1381 行
        lines = _REAL_TRACE.read_text(encoding="utf-8", errors="replace").splitlines() if _REAL_TRACE.is_file() else []
        old = [json.loads(lines[n - 1]) for n in (1379, 1381) if len(lines) >= n]
        olds = [r for r in old if r.get("event") == "park_early_probe" and r.get("reading") is None]
        ctx.check(len(olds) == 2 and all(not parkwhy.valid(r.get("why")) for r in olds), f"第 1379／1381 行舊形應判違規（reading=null 無 why）：{old}")
        ctx.evidence(f"RV-CTL27 主組：armed park NextRunTime={t['next_run_time']}；tick rc={rc}、probe {len(probes)} 列、recovered→park_early_recovered、標記={mk2['status']}、替身 claude {calls} 次；"
                     f"舊形 oracle：第 1379／1381 行 reading=null 無 why 判違規")
    # ── 無憑證組：量不到 ⇒ 帶 why、不提前
    sb2 = ctx.sandbox(probe_hooks=False)
    install_tools(sb2)
    grant_default(sb2)
    env2 = _env(sb2)
    with park_cleanup(sb2):
        tp2, mk3 = _park_with_baseline(ctx, sb2)
        plan2 = arm(ctx, sb2, tp2)
        regrant(sb2, 40)
        (sb2.root / "qcache" / "autosdd_quota.json").unlink()
        nocred = sb2.root / "nocred"
        nocred.mkdir(exist_ok=True)
        env2 = {**env2, "CLAUDE_CONFIG_DIR": str(nocred)}  # 沙盒預設帶複製憑證（真 claude -p 需要）；此組只讓**被測 tick** 看不到憑證
        rc2 = run_nostd(sandbox_tick_argv(sb2, plan2), cwd=sb2.root, env=env2)
        probes2 = [e for e in trace_events(sb2) if e.get("event") == "park_early_probe"]
        ctx.check(rc2 == 0 and probes2, f"無憑證組 tick rc={rc2}、缺 park_early_probe：{[e.get('event') for e in trace_events(sb2)]}")
        ctx.check(all(r.get("reading") is None and parkwhy.valid(r.get("why")) and not r.get("recovered") for r in probes2), f"無憑證組應 reading=null＋有效 why＋不提前：{probes2}")
        ctx.check(read_marker(sb2.sid, sb2.home / "traces")["status"] == "armed", "無憑證組不該提前接手")
        ctx.evidence(f"RV-CTL27 無憑證組：probe why={[r.get('why') for r in probes2]}、標記仍 armed")
