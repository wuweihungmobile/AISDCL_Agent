# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""prd_px 家族（真喚醒鏈）：RV-PX11 哨兵漂移自癒、RV-PX18 FRESH 選路、RV-PX26／27 撞線→哨兵→真 `claude -p -r` 喚醒鏈。

沿用 `prd_px_wake` 的「執行排程器登記 Action 命令列、環境洗成沙盒」做法。交接報告目錄一律指到沙盒
（`AUTOSDD_HANDBACK_DIR`），避免 SessionStart 公告把真機的未讀 handback 當成沙盒的而誤標已讀。
真 `claude -p -r` 一律 haiku、限於沙盒 sid。"""

from __future__ import annotations

import json
import re
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from ..sandbox import Sandbox
from . import CaseContext
from .prd_px_lib import ev, px
from .prd_px_wake import events, fresh_quota, limit_text, reset_in
from .sentinel import append_limit_event, arm, planner, task_name, tick
from .sessionctl_park import (
    age_transcript,
    claude_procs,
    get_task,
    install_tools,
    park_cleanup,
    ps,
    remove_tasks_like,
    seed_session,
)

HAIKU = {"AUTOSDD_MODEL_HELMSMAN": "haiku", "AUTOSDD_MODEL_SUBAGENT": "haiku"}


def relay_state(plan: Path) -> dict:
    m = re.search(r"```json\n(.*?)\n```", plan.read_text(encoding="utf-8"), re.S)
    return json.loads(m.group(1)) if m else {}


def _spawn_watch(sb: Sandbox, out: list, stop: threading.Event) -> None:
    while not stop.is_set():
        for p in claude_procs(sb.sid):
            if p["cmd"] not in out:
                out.append(p["cmd"])
        time.sleep(0.5)


# WHY：`claude -p` 一收尾就殺行程樹，hook detached 出去的 planner 武裝要好幾秒，得讓回合多撐一下
_HOLD_PROMPT = (
    "Call the Read tool on a.txt once. Then, with the PowerShell tool in the foreground, run exactly: "
    f"& '{sys.executable}' -c 'import time; time.sleep(30)' and finally reply done."
)
def _hook_lines(sb: Sandbox) -> list[str]:
    """沙盒 `--debug hooks` 日誌裡與 hook 執行有關的行（失敗診斷用）。"""
    out: list[str] = []
    for dbg in sorted(sb.root.glob("debug_*.log")):
        out += [ln[:260] for ln in dbg.read_text(encoding="utf-8", errors="replace").splitlines()
                if "PostToolUse" in ln and ("Hook" in ln or "hook" in ln)]
    return out[-6:]


def _wait_until(ts: float) -> None:
    while time.time() < ts:
        time.sleep(min(20.0, max(0.5, ts - time.time())))


def wake_chain(ctx: CaseContext, sb: Sandbox, *, notify: bool) -> dict:
    """撞線（reset＝now＋3～4 分）→ 巡邏 arm_reset →（可選：造一筆失投通知）→ 等到 reset＋skew →
    巡邏 tick（探針→選路→真 `claude -p -r`）。回各階段取證。"""
    hb = sb.root / "hb"
    hb.mkdir(exist_ok=True)
    base = {**HAIKU, "AUTOSDD_HANDBACK_DIR": str(hb)}
    out: dict = {"hb": hb, "states": []}
    tp = seed_session(ctx, sb)
    plan = arm(ctx, sb, tp)
    out.update(tp=tp, plan=plan)
    out["states"].append(("armed", relay_state(plan).get("state")))
    reset = reset_in(3)
    ev_at = datetime.now().astimezone()
    append_limit_event(tp, ev_at, limit_text(reset))
    out["ev_at"] = ev_at
    fresh_quota(sb)
    r1 = tick(sb, plan, **base)
    ctx.check("哨兵判定 arm_reset" in r1.stdout, f"撞線應判 arm_reset：{r1.stdout[-400:]}{r1.stderr[-300:]}")
    out["states"].append(("after_arm_reset", relay_state(plan).get("state")))
    # WHY：排程器在 reset＋skew 真的會響，被叫起的行程是排程器的環境（真 HOME／真額度快取／預設 sonnet），不是沙盒——
    # 實測它搶先把沙盒 session 用真環境續跑了一次。等待期間先停用該排程（NextRunTime 憑證已在上面取證）；
    # 後面的巡邏 tick 重掛時 `-Force` 會把它重新啟用。
    ps(f"Disable-ScheduledTask -TaskName '{task_name(sb)}' | Out-Null")
    if notify:
        junk = sb.root / "tmp" / "autosdd_resume_plan_00000000-0000-4000-8000-000000000000.md"
        planner(sb, "--sentinel-tick", "--plan", str(junk), "--task-name", "AutoSDD_Sentinel_junk", AUTOSDD_DESKTOP_NOTIFY="1", **base)
        q = sb.root / "traces" / "autosdd_notify_queue.json"
        ctx.check(q.is_file() and len(json.loads(q.read_text(encoding="utf-8"))) == 1, "第一次投遞（無東西可救的 loud 告警）應入列失投佇列")
        out["queued"] = json.loads(q.read_text(encoding="utf-8"))
    _wait_until(reset.timestamp() + 125)  # reset＋skew（120 s）之後
    fresh_quota(sb)  # 刷新 TTL，免得 L0 零成本探針因快取過期而走付費探針
    seen: list = []
    stop = threading.Event()
    th = threading.Thread(target=_spawn_watch, args=(sb, seen, stop), daemon=True)
    th.start()
    extra = {"AUTOSDD_DESKTOP_NOTIFY": "1"} if notify else {}
    t0 = time.time()
    r2 = tick(sb, plan, **base, **extra)
    stop.set()
    th.join(timeout=5)
    out.update(r2=r2, spawn_cmds=seen, t0=t0)
    out["states"].append(("after_wake", relay_state(plan).get("state")))
    return out


def _after_ts(tp: Path, t: float) -> int:
    n = 0
    for ln in tp.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        if d.get("type") == "assistant" and isinstance(d.get("timestamp"), str) \
                and datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00")).timestamp() > t:
            n += 1
    return n


@px("RV-PX26", "S＋C＋R", ("resumed", "prepare_precheck", "notify_redelivered"), refs=("R112 REQ-W1/W3/W4/W5/W7",), long=True, sched=True)
def px26(ctx: CaseContext) -> None:
    """施工圖 A5a（TCS:610）：撞線記錄（reset＝now＋3～4 分）→哨兵 arm_reset→到 reset＋skew 巡邏→探針→真 `claude -p -r --model haiku`；
    第一次通知投遞失敗（無東西可救的 loud 告警 ⇒ 失投佇列，`AUTOSDD_DESKTOP_NOTIFY=1`），下一次巡邏重投並寫出 delivered 憑證。"""
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    with park_cleanup(sb):
        o = wake_chain(ctx, sb, notify=True)
        evs = events(sb)
        names = [e["event"] for e in evs]
        res = [e for e in evs if e["event"] == "resumed"]
        ctx.check(res and res[0].get("rc") == 0, f"續跑應 rc 0：{names}\n{o['r2'].stdout[-500:]}{o['r2'].stderr[-500:]}")
        n_new = _after_ts(o["tp"], o["ev_at"].timestamp() + 60)
        ctx.check(n_new >= 1, "原 sid 逐字稿沒有新增 assistant 記錄")
        ev(ctx, "resumed", f"resumed rc=0；原 sid 逐字稿撞線後新增 assistant 記錄 {n_new} 筆；痕跡={names}")
        i_probe = max((i for i, n in enumerate(names) if n == "probed"), default=-1)
        i_res = names.index("resumed")
        probed = [e for e in evs if e["event"] == "probed"]
        ctx.check(0 <= i_probe < i_res and probed[-1].get("quota_open") is True, f"續跑前應有額度預檢（probed open）：{names}")
        ev(ctx, "prepare_precheck", f"probed(quota_open={probed[-1].get('quota_open')} source={probed[-1].get('source')}) 先於 resumed")
        red = [e for e in evs if e["event"] == "notify_redelivered"]
        ctx.check(red and red[-1].get("delivered") is True, f"第二次巡邏應重投並 delivered：{red}")
        ev(ctx, "notify_redelivered", f"首投入列 {len(o['queued'])} 則（失投）→ notify_redelivered delivered=True rc={red[-1].get('rc')}")


@px("RV-PX27", "S＋C", ("unattended_posture", "handback_visible", "relay_progress", "sentinel_rearmed"), refs=("R113 G1~G4",), long=True, sched=True)
def px27(ctx: CaseContext) -> None:
    """施工圖 A6（TCS:611）：同 A26 的喚醒鏈。spawn 命令列含 `settings.unattended.json`；下一個真 `claude -p` 的 SessionStart 公告該 handback；
    RELAY 狀態依序前進；fire 後新排程 NextRunTime 非空。"""
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    with park_cleanup(sb):
        o = wake_chain(ctx, sb, notify=False)
        evs = events(sb)
        names = [e["event"] for e in evs]
        res = [e for e in evs if e["event"] == "resumed"]
        ctx.check(res and res[0].get("rc") == 0, f"續跑應 rc 0：{names}\n{o['r2'].stdout[-500:]}{o['r2'].stderr[-500:]}")
        cmds = [c for c in o["spawn_cmds"] if "-r" in c]
        ctx.check(cmds and all("settings.unattended.json" in c for c in cmds), f"spawn 命令列應含 settings.unattended.json：{o['spawn_cmds']}")
        ev(ctx, "unattended_posture", f"spawn 命令列含 settings.unattended.json（{len(cmds)} 條）")
        st = [s for _, s in o["states"]]
        ctx.check(st[0] == "armed" and st[1] == "waiting" and st[2] not in ("armed", "waiting", None), f"RELAY 狀態應依序前進：{o['states']}")
        ev(ctx, "relay_progress", f"{' → '.join(f'{k}={v}' for k, v in o['states'])}")
        t = get_task(task_name(sb))
        ctx.check(t is not None and bool(t["next_run_time"]), f"fire 後應重掛哨兵（NextRunTime 非空）：{t}")
        ev(ctx, "sentinel_rearmed", f"{task_name(sb)} NextRunTime={t['next_run_time']}")
        hbs = sorted(Path(o["hb"]).glob("*.md"))
        ctx.check(bool(hbs), f"續跑後沒有 handback 檔：{list(Path(o['hb']).iterdir())}")
        sb.add_repo_hook("SessionStart", ".claude/hooks/context_budget_guard.py")
        r = ctx.run_claude(sb, "Reply with exactly: ok", env_extra={"AUTOSDD_HANDBACK_DIR": str(o["hb"])})
        ctx.check(r.rc == 0, f"下一個 claude -p rc={r.rc} {r.stderr[:200]}")
        raw = ctx.transcript(sb).path.read_text(encoding="utf-8", errors="replace")
        ctx.check(hbs[0].stem in raw and hbs[0].with_suffix(".ack").exists(), f"SessionStart 應公告 handback {hbs[0].name} 並落 .ack")
        ev(ctx, "handback_visible", f"下一個真 claude -p 的 SessionStart 公告 {hbs[0].name}；.ack 已落")


@px("RV-PX18", "S＋P", ("route_fresh", "handback_written"), refs=("§8-10",), sched=True)
def px18(ctx: CaseContext) -> None:
    """§8-10（TCS:602）：喚醒後 context 不可用 ⇒ FRESH。哨兵武裝、撞線（reset 已過），到點前把沙盒逐字稿改名（不可續），執行續航 Action
    （`--resume-tick`）⇒ 痕跡選路 FRESH、handback 檔存在（FRESH 的真 `claude -p` 帶 handback 路徑，haiku）。"""
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    hb = sb.root / "hb"
    hb.mkdir()
    base = {**HAIKU, "AUTOSDD_HANDBACK_DIR": str(hb)}
    with park_cleanup(sb):
        tp = seed_session(ctx, sb)
        age_transcript(tp, 3 * 3600)
        target = (datetime.now().astimezone() - timedelta(minutes=100)).replace(minute=0, second=0, microsecond=0)
        append_limit_event(tp, target - timedelta(minutes=30), limit_text(target))
        plan = arm(ctx, sb, tp)
        try:
            tp.rename(tp.with_suffix(".jsonl.renamed"))  # 到點前改名：不可續
        except OSError as exc:  # Windows 上檔案被別的行程開著會 PermissionError：大聲失敗，不當成產品缺陷
            ctx.check(False, f"沙盒逐字稿改名失敗（無法製造『不可續』前提）：{exc}")
        fresh_quota(sb)
        r = planner(sb, "--resume-tick", "--plan", str(plan), "--task-name", task_name(sb), timeout=900, **base)
        evs = events(sb)
        names = [e["event"] for e in evs]
        route = [e for e in evs if e["event"] == "route_chosen"]
        ctx.check(route and route[0]["strategy"] != "SESSION_RESUME", f"逐字稿不可用應選 FRESH：{route}\n{names}\n{r.stdout[-400:]}{r.stderr[-400:]}")
        ev(ctx, "route_fresh", f"route_chosen strategy={route[0]['strategy']} why={str(route[0].get('why'))[:90]}")
        hbs = sorted(hb.glob("*.md"))
        ctx.check(bool(hbs), f"沒有 handback 檔：{names}\n{r.stdout[-300:]}")
        ev(ctx, "handback_written", f"handback={hbs[0].name}（{hbs[0].stat().st_size} bytes）")


@px("RV-PX11", "S＋H", ("drift_seen", "rearmed"), refs=("§4.5.8",), sched=True)
def px11(ctx: CaseContext) -> None:
    """§4.5.8（TCS:595）：哨兵武裝漂移自癒。真 hook 載具（repo `context_budget_guard.py`，PostToolUse）在夠格 session（≥24 回合、≥600 s）
    武裝沙盒哨兵 ⇒ `Unregister-ScheduledTask` 外力刪除 ⇒ 把重掛節流戳記（`autosdd_sentinel_relatch_<sid>`，節流 900 s）的 mtime 往前推
    ⇒ 再觸發一次真 PostToolUse ⇒ marker 事件 `sentinel_relatched`（relatched_from=armed_but_missing）、同前綴新排程 NextRunTime 非空。
    WHY 推戳記：節流戳記是 `claim_once` 的 mtime，等 15 分鐘與把 mtime 推前 15 分鐘等價；先前「刪排程後立刻觸發」未重掛，成因就是
    這個 900 s 節流（`sentinel_lifecycle_arm.RELATCH_INTERVAL_SECONDS`），不是產品缺陷。"""
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)  # 真 hook 的 repo_root() 解到沙盒（CLAUDE_PROJECT_DIR）：沒有工具副本就找不到 planner、spawn 不出哨兵
    tmp = sb.root / "tmp"
    tmp.mkdir()
    env = {"AUTOSDD_SENTINEL_OFF": "", "TEMP": str(tmp), "TMP": str(tmp), "AUTOSDD_PLAN_DIR": str(tmp)}
    name = task_name(sb)
    with park_cleanup(sb):
        # 本 session 自己要夠格：直接在本沙盒 sid 真跑 30 次 Read，再把時間戳展開
        (sb.root / "a.txt").write_text("rv\n", encoding="utf-8")
        r = ctx.run_claude(sb, "Call the Read tool on a.txt thirty separate times, one call per step, then reply done.", timeout_s=200, extra_args=("--permission-mode", "acceptEdits"), env_extra=env)
        ctx.check(r.rc == 0, f"建立夠格 session rc={r.rc} {r.stderr[:200]}")
        tp = ctx.transcript(sb).path
        recs = [json.loads(ln) for ln in tp.read_text(encoding="utf-8").splitlines() if ln.strip().startswith("{")]
        stamp = lambda x: datetime.fromisoformat(x["timestamp"].replace("Z", "+00:00")).timestamp()  # noqa: E731
        ts = [stamp(x) for x in recs if isinstance(x.get("timestamp"), str)]
        t0, span = min(ts), max(ts) - min(ts)
        k = max(1.0, 900.0 / max(span, 1.0))
        base = datetime.now().timestamp() - 300 - span * k
        for x in recs:
            if isinstance(x.get("timestamp"), str):
                x["timestamp"] = datetime.fromtimestamp(base + (stamp(x) - t0) * k).astimezone().isoformat()
        tp.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in recs) + "\n", encoding="utf-8", newline="\n")
        sb.add_repo_hook("PostToolUse", ".claude/hooks/context_budget_guard.py", timeout=30)
        r1 = ctx.run_claude(sb, _HOLD_PROMPT, extra_args=("--permission-mode", "bypassPermissions"), env_extra=env)
        ctx.check(r1.rc == 0, f"觸發武裝的回合 rc={r1.rc}")
        deadline = time.time() + 40
        while time.time() < deadline and get_task(name) is None:
            time.sleep(1)
        t_first = get_task(name)
        ctx.check(t_first is not None, "真 hook 沒有武裝出沙盒哨兵（PostToolUse 的 maybe_arm 沒 spawn）："
                  f"tmp={sorted(p.name for p in tmp.iterdir())} hook_stderr={_hook_lines(sb)}")
        marker = tmp / f"autosdd_sentinel_armed_{sb.sid}.json"
        ctx.check(marker.is_file() and json.loads(marker.read_text(encoding="utf-8"))["event"] == "sentinel_armed", f"武裝 marker 不對：{marker}")
        remove_tasks_like(f"AutoSDD_Sentinel_{sb.sid}")  # 外力 Unregister
        ctx.check(get_task(name) is None, "外力刪除後排程仍在")
        stamp_f = tmp / f"autosdd_sentinel_relatch_{sb.sid}"
        ctx.check(stamp_f.is_file(), f"沒有重掛節流戳記：{list(tmp.glob('autosdd_sentinel_*'))}")
        import os  # noqa: PLC0415

        old = time.time() - 1000
        os.utime(stamp_f, (old, old))
        r2 = ctx.run_claude(sb, _HOLD_PROMPT, extra_args=("--permission-mode", "bypassPermissions"), env_extra=env)
        ctx.check(r2.rc == 0, f"觸發自癒的回合 rc={r2.rc}")
        deadline = time.time() + 40
        while time.time() < deadline and get_task(name) is None:
            time.sleep(1)
        mk = json.loads(marker.read_text(encoding="utf-8"))
        ctx.check(mk.get("event") == "sentinel_relatched" and mk.get("relatched_from") == "armed_but_missing", f"marker 應記 sentinel_relatched：{mk}")
        ev(ctx, "drift_seen", f"marker event={mk['event']} relatched_from={mk['relatched_from']}")
        t2 = get_task(name)
        ctx.check(t2 is not None and bool(t2["next_run_time"]), f"同前綴新排程應在且 NextRunTime 非空：{t2}")
        ev(ctx, "rearmed", f"{name} 重新武裝 NextRunTime={t2['next_run_time']}（首次 {t_first['next_run_time']}）")
