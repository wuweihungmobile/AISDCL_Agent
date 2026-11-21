# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""prd_px 家族（S＋R 載具：真排程＋真哨兵巡邏）：RV-PX09／10／18／21／32。

沿用 sentinel 家族的「工具副本沙盒」：被測的是沙盒內逐位元相同的 `session_resume_planner.py`，排程是真
Windows 排程（名稱含沙盒 sid，案例結束經 `park_cleanup` 精確移除）。
🔴 「真排程觸發」的做法（WHY）：排程器自己響起時，被叫起的行程環境是排程器的（真 HOME、真憑證、真額度快取），
不在沙盒內；所以本家族**執行排程器登記的那條 Action 命令列**（`get_task` 回讀的 Execute／Arguments，
`pythonw`→`python` 以便收 stdout），環境洗成沙盒——命令列逐字相同、只差環境。
"""

from __future__ import annotations

import json
import re
import shlex
from datetime import datetime, timedelta
from pathlib import Path

from ..sandbox import Sandbox
from . import CaseContext
from .prd_px_lib import ev, px
from .sentinel import _env, append_limit_event, arm, log_events, planner, task_name, tick
from .sessionctl_park import (  # noqa: E501
    PY,
    age_transcript,
    axis,
    get_task,
    install_tools,
    park_cleanup,
    run,
    seed_session,
    write_quota,
)

RELAY_RE = re.compile(r"<!-- AUTOSDD-RELAY-BEGIN -->.*?<!-- AUTOSDD-RELAY-END -->\n?", re.S)


def limit_text(at: datetime) -> str:
    h12 = at.hour % 12 or 12
    return f"You've hit your session limit · resets {h12}:{at.minute:02d}{'am' if at.hour < 12 else 'pm'}"


def reset_in(minutes: float) -> datetime:
    """下一個整分鐘、且距現在 ≥ `minutes` 分（撞線字樣只有分鐘解析度）。"""
    return (datetime.now().astimezone() + timedelta(minutes=minutes + 1)).replace(second=0, microsecond=0)


def action_argv(name: str) -> list[str]:
    """排程器登記的 Action ⇒ argv（`pythonw`→`python`）；Action 不是 planner 時直接 fail。"""
    t = get_task(name)
    if t is None:
        raise AssertionError(f"排程器查不到 {name}")
    parts = [p.strip('"') for p in shlex.split(t["arguments"], posix=False)]
    if "session_resume_planner.py" not in parts[0]:
        raise AssertionError(f"Action 不是 planner：{t['arguments'][:200]}")
    return [PY, *parts]


def fire(sb: Sandbox, name: str, *extra: str, timeout: int = 900, **env) -> object:
    """執行排程器登記的 Action 命令列（環境洗成沙盒；可附加旗標，如 `--probe-command`）。"""
    return run([*action_argv(name), *extra], cwd=sb.root, env=_env(sb, **env), timeout=timeout)


def events(sb: Sandbox) -> list[dict]:
    return log_events(sb)


def fresh_quota(sb: Sandbox, five: float = 5, seven: float = 5) -> None:
    write_quota(sb, [axis("five_hour", five, 240), axis("seven_day", seven, 5 * 1440)])


@px("RV-PX09", "S＋R", ("arm_reset", "cred_nonempty", "distinct_events", "self_heal"), refs=("§4.5.6",), sched=True)
def px09(ctx: CaseContext) -> None:
    """§4.5.6（TCS:593）：沙盒逐字稿依真格式注入撞線記錄（reset＝now＋3～4 分）⇒ 巡邏判 arm_reset、排程改在
    reset＋skew 醒、NextRunTime 非空；變體刪除任務書狀態塊 ⇒ 哨兵重建狀態塊並續巡（`sentinel_selfhealed`，排程
    未被 unregister）；另跑一個閒置到解除的沙盒 ⇒ `sentinel_disarm`。巡邏／武裝／自癒／解除四種事件名互異。"""
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    fresh_quota(sb)
    with park_cleanup(sb):
        tp = seed_session(ctx, sb)
        plan = arm(ctx, sb, tp)
        r1 = fire(sb, task_name(sb))  # 排程器登記的 Action 命令列（無撞線 ⇒ patrol）
        ctx.check("哨兵判定 patrol" in r1.stdout, f"無撞線應判 patrol：{r1.stdout[-300:]}{r1.stderr[-200:]}")
        reset = reset_in(3)
        append_limit_event(tp, datetime.now().astimezone(), limit_text(reset))
        r2 = tick(sb, plan)
        ctx.check("哨兵判定 arm_reset" in r2.stdout, f"撞線（reset 未到）應判 arm_reset：{r2.stdout[-400:]}{r2.stderr[-300:]}")
        t = get_task(task_name(sb))
        ctx.check(t is not None and bool(t["next_run_time"]), f"arm_reset 後排程應在且 NextRunTime 非空：{t}")
        diff = (datetime.fromisoformat(t["next_run_time"]) - reset).total_seconds()
        ctx.check(0 <= diff <= 180, f"NextRunTime 應在 reset＋skew 附近（差 {diff:.0f}s）")
        decided = [e for e in events(sb) if e["event"] == "sentinel_decided"]
        acts = [e["action"] for e in decided]
        ctx.check("arm_reset" in acts and "patrol" in acts, f"痕跡 sentinel_decided.action={acts}")
        ev(ctx, "arm_reset", f"sentinel_decided.action={acts}；reset={reset:%H:%M}")
        ev(ctx, "cred_nonempty", f"{task_name(sb)} NextRunTime={t['next_run_time']}（reset＋{diff:.0f}s，排程器自報）")
        # 變體：狀態塊被砸
        text = plan.read_text(encoding="utf-8")
        plan.write_text(RELAY_RE.sub("", text), encoding="utf-8", newline="\n")
        ctx.check("AUTOSDD-RELAY-BEGIN" not in plan.read_text(encoding="utf-8"), "未能刪除狀態塊")
        r3 = tick(sb, plan)
        names = [e["event"] for e in events(sb)]
        ctx.check("sentinel_selfhealed" in names, f"刪除狀態塊後應 sentinel_selfhealed：{names}\n{r3.stdout[-300:]}{r3.stderr[-300:]}")
        ctx.check("AUTOSDD-RELAY-BEGIN" in plan.read_text(encoding="utf-8"), "自癒後任務書應重建狀態塊")
        t3 = get_task(task_name(sb))
        ctx.check(t3 is not None and "sentinel_aborted" not in names and "sentinel_heal_failed" not in names, f"自癒後排程應仍在、不得 unregister：{t3} {names}")
        ev(ctx, "self_heal", f"刪除狀態塊 ⇒ sentinel_selfhealed；狀態塊重建；排程仍在 NextRunTime={t3['next_run_time']}")
    # 解除變體：另一沙盒，閒置 6 小時、無撞線 ⇒ disarm
    sb2 = ctx.sandbox(probe_hooks=False)
    install_tools(sb2)
    with park_cleanup(sb2):
        tp2 = seed_session(ctx, sb2)
        age_transcript(tp2, 6 * 3600)
        plan2 = arm(ctx, sb2, tp2)
        r4 = tick(sb2, plan2)
        names2 = [e["event"] for e in events(sb2)]
        ctx.check("sentinel_disarm" in names2 and get_task(task_name(sb2)) is None, f"閒置應解除並拆排程：{names2}\n{r4.stdout[-300:]}")
    kinds = {"patrol": "sentinel_decided/patrol", "arm": "sentinel_decided/arm_reset", "heal": "sentinel_selfhealed", "disarm": "sentinel_disarm"}
    ctx.check(len(set(kinds.values())) == 4, f"四種事件名須互異：{kinds}")
    ev(ctx, "distinct_events", f"巡邏={kinds['patrol']} 武裝={kinds['arm']} 自癒={kinds['heal']} 解除={kinds['disarm']}（四者皆在痕跡出現且互異）")


@px("RV-PX10", "S＋R＋K", ("idle_seconds", "notice_by_patrol", "no_skeleton"), refs=("§4.5.7",), sched=True)
def px10(ctx: CaseContext) -> None:
    """§4.5.7（TCS:594）：主控閒置盲區預防提醒。沙盒逐字稿最後 assistant 事件在 40 分前、無撞線；門檻鍵（ENV_SPEC 已登記的
    四錨點整組下修）使真實短窗讀數落 prepare 帶 ⇒ 巡邏那一次 tick 的 `sentinel_decided` 帶 `controller_idle_seconds`（與注入時差
    ≤60 s）、`quota_band=prepare`、`prepare_notify_rc`（通知由巡邏行程在該次 tick 內呼叫；桌面通知預設關閉＝rc −1，與 TCS 對
    PX13 的處置同：不在開發機彈真氣球）；任務書除狀態塊外未被改寫、沒有新的任務書檔（不寫骨架）。"""
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    fresh_quota(sb, five=30, seven=5)
    keys = {"AUTOSDD_QUOTA_NOTICE_PCT": "1", "AUTOSDD_QUOTA_CONVERGE_PCT": "2", "AUTOSDD_QUOTA_PREPARE_PCT": "6", "AUTOSDD_QUOTA_HALT_PCT": "100"}
    with park_cleanup(sb):
        tp = seed_session(ctx, sb)
        age_transcript(tp, 2400)
        last = max(datetime.fromisoformat(json.loads(ln)["timestamp"].replace("Z", "+00:00")).timestamp()
                   for ln in tp.read_text(encoding="utf-8").splitlines()
                   if ln.startswith("{") and '"type":"assistant"' in ln.replace(" ", ""))
        plan = arm(ctx, sb, tp)
        body_before = RELAY_RE.sub("", plan.read_text(encoding="utf-8"))
        plans_before = sorted(p.name for p in (sb.root / "tmp").glob("autosdd_resume_plan_*.md"))
        fresh_quota(sb, five=30, seven=5)
        t0 = datetime.now().timestamp()
        r = tick(sb, plan, **keys)
        ctx.check("哨兵判定 patrol" in r.stdout, f"應判 patrol：{r.stdout[-400:]}{r.stderr[-300:]}")
        dec = [e for e in events(sb) if e["event"] == "sentinel_decided"][-1]
        idle = dec.get("controller_idle_seconds")
        ctx.check(isinstance(idle, (int, float)) and abs(idle - (t0 - last)) <= 60, f"閒置秒數 {idle} 與注入時差 {t0 - last:.0f} 相差 >60：{dec}")
        ev(ctx, "idle_seconds", f"controller_idle_seconds={idle:.0f} 注入時差={t0 - last:.0f}（差 ≤60）")
        ctx.check(dec.get("quota_band") == "prepare" and "prepare_notify_rc" in dec, f"應落 prepare 帶並呼叫通知：{dec}")
        ev(ctx, "notice_by_patrol", f"sentinel_decided（本次 --sentinel-tick 行程所寫）quota_band=prepare prepare_notify_rc={dec['prepare_notify_rc']}（桌面通知預設關閉）")
        body_after = RELAY_RE.sub("", plan.read_text(encoding="utf-8"))
        plans_after = sorted(p.name for p in (sb.root / "tmp").glob("autosdd_resume_plan_*.md"))
        ctx.check(body_before == body_after and plans_before == plans_after, "任務書除狀態塊外被改寫，或多出新任務書檔")
        ev(ctx, "no_skeleton", f"任務書狀態塊外內容逐位元不變（{len(body_after)} 字）、任務書檔數={len(plans_after)} 前後相同")


@px("RV-PX21", "S＋P", ("no_side_effect", "argv_from_params"), refs=("§12 命令執行",), sched=True)
def px21(ctx: CaseContext) -> None:
    """§12 命令執行（TCS:605）：命令來自設定、state 無可執行字串。沙盒任務書狀態塊某欄塞入 `& echo pwned > x`，
    執行排程器登記的 Action ⇒ 沙盒 `x` 不存在、被執行命令列（排程 Action 快照）不含該字樣。"""
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    fresh_quota(sb)
    with park_cleanup(sb):
        tp = seed_session(ctx, sb)
        plan = arm(ctx, sb, tp)
        evil = "& echo pwned > x"
        text = plan.read_text(encoding="utf-8")
        m = re.search(r"```json\n(.*?)\n```", text, re.S)
        st = json.loads(m.group(1))
        st["reset_source"], st["note"] = evil, evil
        plan.write_text(text.replace(m.group(1), json.dumps(st, ensure_ascii=False, indent=2)), encoding="utf-8", newline="\n")
        argv = action_argv(task_name(sb))
        r = fire(sb, task_name(sb))
        ctx.check(not (sb.root / "x").exists() and not (sb.root / "tools" / "x").exists(), "沙盒出現 x：命令被執行了")
        ev(ctx, "no_side_effect", f"state 欄位塞入 {evil!r} 後執行排程 Action rc={r.returncode}；沙盒 x 不存在")
        ctx.check(all("pwned" not in a and "echo" not in a for a in argv), f"spawn 命令列含注入字樣：{argv}")
        ev(ctx, "argv_from_params", f"Action argv={[Path(a).name for a in argv]}（僅 planner／--sentinel-tick／--plan／--task-name，無 state 字串）")


@px("RV-PX32", "S＋P＋K", ("fresh_on_weekly", "resume_below"), refs=("§4.5.4",), sched=True)
def px32(ctx: CaseContext) -> None:
    """§4.5.4（TCS:616）：週軸讀數 ≥ converge 一律 FRESH。兩變體（sandbox 額度快取週軸 50%，四錨點整組下修）：converge＝20
    （讀數在其上）⇒ 選路 FRESH 且痕跡理由含週軸；converge＝60（讀數在其下）⇒ 不因週軸改路（RESUME）。
    被叫起的 `claude` 以 `--probe-command` 換成不做事的 .cmd（本案例只驗選路，不花真 claude）。"""
    outs = {}
    for label, conv in (("above", "20"), ("below", "60")):
        sb = ctx.sandbox(probe_hooks=False)
        install_tools(sb)
        shim = sb.root / "noop_claude.cmd"
        shim.write_text("@echo off\r\nexit /b 0\r\n", encoding="utf-8", newline="")
        keys = {"AUTOSDD_QUOTA_NOTICE_PCT": str(int(conv) - 10), "AUTOSDD_QUOTA_CONVERGE_PCT": conv,
                "AUTOSDD_QUOTA_PREPARE_PCT": str(int(conv) + 20), "AUTOSDD_QUOTA_HALT_PCT": "100"}
        with park_cleanup(sb):
            tp = seed_session(ctx, sb)
            age_transcript(tp, 3 * 3600)
            target = (datetime.now().astimezone() - timedelta(minutes=100)).replace(minute=0, second=0, microsecond=0)
            append_limit_event(tp, target - timedelta(minutes=30), limit_text(target))
            plan = arm(ctx, sb, tp)
            fresh_quota(sb, five=5, seven=50)
            r = planner(sb, "--sentinel-tick", "--plan", str(plan), "--task-name", task_name(sb), "--probe-command", str(shim), timeout=300, **keys)
            route = [e for e in events(sb) if e["event"] == "route_chosen"]
            ctx.check(bool(route), f"[{label}] 沒有 route_chosen：{[e['event'] for e in events(sb)]}\n{r.stdout[-400:]}{r.stderr[-300:]}")
            outs[label] = route[0]
    a, b = outs["above"], outs["below"]
    ctx.check(a["strategy"] == "FRESH_SESSION" or "FRESH" in str(a["strategy"]), f"讀數在 converge 之上應 FRESH：{a}")
    ctx.check("週" in str(a["why"]) or "weekly" in str(a["why"]).lower(), f"FRESH 理由應含週軸：{a['why']}")
    ev(ctx, "fresh_on_weekly", f"converge=20、週軸 50% ⇒ strategy={a['strategy']} why={str(a['why'])[:80]}")
    ctx.check("FRESH" not in str(b["strategy"]) or "週" not in str(b["why"]), f"讀數在 converge 之下不應因週軸改路：{b}")
    ev(ctx, "resume_below", f"converge=60、週軸 50% ⇒ strategy={b['strategy']} why={str(b['why'])[:80]}")
