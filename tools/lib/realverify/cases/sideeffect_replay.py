# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""sideeffect 家族（一）：RV-SE01＝E2E-SE-01「重放本案（證明一）」全部變體 (a)(b)(c)(c′)(d)(e1)(e2)(e3)(f)(g)(h)(i)。

事故形狀：沙盒內 `park --at` 登記了真 schtasks（argv0 在沙盒內），到點排程器以登入者的真環境起 job。
本案例把同一形狀做成十二個沙盒、**同一分鐘**到點，之後逐一斷言：L1 拒絕是終局（沒有 `park_route`／讓路／
失敗鏈／handback／佇列）、假 claude 呼叫次數（＝真正會開窗的那一步）、標記狀態、工作自拆或被 sweep 撤掉。
全部只打假 claude（`fakeclaude`，D-14）；沒有任何真 claude 行程、沒有可見視窗。
`park_attempt` 事件（QW Q3 才有）目前一律 0 筆；QW Q3 同 commit 把 `PARK_ATTEMPTS` 改成 1。
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from lib import sandbox_scope

from .. import fakeclaude, sched
from ..sandbox import REPO, projects_dir, slug_of
from . import CaseContext, case
from .sessionctl_park import get_task
from .sideeffect_lib import (
    arm_park,
    calls,
    endurance_env,
    events,
    flip_task_arg,
    iso_at,
    kill_pid,
    kills_runners,
    marker_of,
    names,
    new_box,
    now,
    pick_resume_ctx,
    pid_alive,
    refusal,
    rmtree,
    spawn_runner,
    sweep_clean,
    task_result,
    task_xml,
    wait_gone,
    wait_ready,
    window_problems,
)

PARK_ATTEMPTS = 0  # QW Q3 前 0 筆；Q3 落地後每次 spawn 嘗試 1 筆（TCS §4 r4 共通②），由 Q3 同 commit 改成 1
_AUTO = {"AUTOSDD_SESSION_SWITCH_MODE": "auto"}
_FORBIDDEN_AFTER_REFUSE = ("park_route", "park_yield_primary", "park_attempt", "park_chain_failed",
                           "park_resumed", "park_spawned", "park_resume_failed", "park_spawn_failed")


def _minute_after(seconds: float) -> datetime:
    t = now() + timedelta(seconds=seconds)
    return (t + timedelta(minutes=1)).replace(second=0, microsecond=0)


def _sideless(ctx: CaseContext, tag: str, sb) -> None:
    """沒有 handback 檔、沒有通知佇列檔（L1 拒絕＝終局：不寫 handback、不入佇列）。"""
    hb = Path(sb.home) / "handback"
    files = [p.name for p in hb.iterdir()] if hb.is_dir() else []
    ctx.check(not files, f"{tag}：沙盒 handback 目錄不該有檔：{files}")
    ctx.check(not (Path(sb.home) / "traces" / "autosdd_notify_queue.json").exists(), f"{tag}：通知佇列檔不該被建立")


def _refused(ctx: CaseContext, tag: str, sb, reason: str, *, task: str | None = None, marker: bool = True) -> None:
    ref = refusal(sb)
    ctx.check(ref is not None and ref.get("reason") == reason, f"{tag}：要 sideeffect_refused reason={reason}，實得 {ref}")
    ev = names(sb)
    ctx.check("park_job_start" in ev, f"{tag}：沒有 park_job_start（到點 job 根本沒跑？）{ev}")
    bad = [n for n in ev if n in _FORBIDDEN_AFTER_REFUSE]
    ctx.check(not bad, f"{tag}：L1 拒絕應是終局，卻出現 {bad}")
    ctx.check(not calls(sb), f"{tag}：假 claude 不該被呼叫：{calls(sb)}")
    _sideless(ctx, tag, sb)
    if marker:
        mk = marker_of(sb)
        ctx.check(mk is not None and mk["status"] == "refused", f"{tag}：標記應為 refused：{mk and mk['status']}")
    if task:
        ctx.check(get_task(task) is None, f"{tag}：工作 {task} 應已自拆")


def _real_tools_task(ctx: CaseContext, tag: str, at: datetime, *, delete_pkg: bool = False, delete_home: bool = False):
    """(c)(c′)(h)：以 **repo 本體** 的 `tools/sessionctl.py park --fire`（真 tools）經 `AutoSDD_RV_` 前綴真排程觸發；
    argv 帶 `--job-env`（7 居所指向沙盒、通知空、哨兵 1）、沙盒 pkg、`--claude <假>`。回 (sb, 工作名, pkg)。"""
    sb, exe = new_box(ctx, tools=False)
    ctx.grant_side_effects(sb, minutes=30, window=False)
    pkg = sb.home / "handoff" / f"{sb.sid}_rvse.md"
    pkg.parent.mkdir(parents=True, exist_ok=True)
    pkg.write_text(f"# rv sideeffect 合成交接包\n- repo 根：{sb.root}\n", encoding="utf-8", newline="\n")
    name = sched.rv_name(f"SE01{tag}_{sb.sid[:8]}")
    job_env = endurance_env().job_env_argv(sb.env(), sandbox=True)
    args = " ".join([f'"{REPO / "tools" / "sessionctl.py"}"', *job_env, "park", "--fire", "--job", name, "--session-id", sb.sid,
                     "--pkg", f'"{pkg}"', "--fire-at", iso_at(at), "--claude", f'"{exe}"'])
    ctx.sched_register(name, at.replace(tzinfo=None).isoformat(timespec="seconds"), args)
    if delete_pkg:
        pkg.unlink()
    if delete_home:
        rmtree(sb.root)
    return sb, name, pkg


def _end_boundary_ok(ctx: CaseContext, label: str, sb) -> str:
    xml = task_xml(label)
    end = re.search(r"<EndBoundary>([^<]+)</EndBoundary>", xml)
    start = re.search(r"<StartBoundary>([^<]+)</StartBoundary>", xml)
    ctx.check(bool(end and start), f"工作 XML 缺 EndBoundary／StartBoundary：{xml[:300]}")
    e, s = (datetime.fromisoformat(end.group(1)).astimezone(), datetime.fromisoformat(start.group(1)).astimezone())  # XML 為本機時間（可能不帶 offset）
    ctx.check(e >= s, f"EndBoundary {e} 早於 StartBoundary {s}")
    allow = datetime.fromisoformat(json.loads((sb.home / sandbox_scope.IDENTITY_NAME).read_text(encoding="utf-8"))["allow_until"])
    ctx.check(abs((e - allow).total_seconds()) <= 61, f"EndBoundary {e} 不等於租約 allow_until {allow}")
    return f"EndBoundary={e.isoformat()} allow_until={allow.isoformat()}"


def _arm_variants(ctx: CaseContext, at: datetime, resume_ctx: int) -> dict:
    """依序建十二個沙盒；回 `{變體: 狀態}`（含 OWNER 子行程的資訊）。"""
    v: dict = {}
    # (a) 主人行程：子 runner 建沙盒＋park，之後由本案例殺它
    runner = spawn_runner(ctx, "RV-SE-OWNER", {"mode": "resume_ok", "sleep": 60, "ctx_tokens": resume_ctx,
                                               "at_iso": at.isoformat(), "env": _AUTO})
    v["a"] = wait_ready(ctx, runner)
    # (e1) RESUME 正控（含 grant(120)→存 +30 的驗證與 EndBoundary＝allow_until）
    sb, exe = new_box(ctx, mode="resume_ok", sleep=60)
    t_grant = now()
    v["e1"] = arm_park(ctx, sb, exe, at=at, ctx_tokens=resume_ctx, extra_env=_AUTO, grant_minutes=120)
    gap = (datetime.fromisoformat(json.loads((sb.home / sandbox_scope.IDENTITY_NAME).read_text(encoding="utf-8"))["allow_until"]) - t_grant).total_seconds()
    ctx.check(1700 <= gap <= 1900, f"grant(120 分) 應存成 +30 分（MU-SE-04），實得 {gap:.0f}s")
    v["e1_xml"] = _end_boundary_ok(ctx, v["e1"].label, sb)
    v["e1_lines"] = len((v["e1"].projdir / f"{sb.sid}.jsonl").read_text(encoding="utf-8").splitlines())
    ident_ts = datetime.fromisoformat(json.loads((sb.home / sandbox_scope.IDENTITY_NAME).read_text(encoding="utf-8"))["created_at"])
    git_ts = datetime.fromtimestamp((sb.home / ".git").stat().st_ctime).astimezone()
    ctx.check(ident_ts <= git_ts + timedelta(seconds=1), f"身分檔 created_at {ident_ts} 晚於 .git 建立 {git_ts}（D-1）")
    # (e2) 同 e1 但模式 notify
    sb, exe = new_box(ctx, mode="resume_ok", sleep=60)
    v["e2"] = arm_park(ctx, sb, exe, at=at, ctx_tokens=resume_ctx, extra_env=_AUTO)  # park 政策閘在登記時拒 notify：以 auto 登記、再把工作 argv 的模式改成 notify
    flip_task_arg(v["e2"].label, "AUTOSDD_SESSION_SWITCH_MODE=auto", "AUTOSDD_SESSION_SWITCH_MODE=notify")
    # (e3) FRESH 正控：逐字稿剝掉全部 usage ⇒ F4 判 FRESH
    sb, exe = new_box(ctx, mode="fresh_ok", sleep=60)
    v["e3"] = arm_park(ctx, sb, exe, at=at, ctx_tokens=None, extra_env=_AUTO)
    # (b) 主人活、到點前 revoke
    sb, exe = new_box(ctx, mode="resume_ok", sleep=60)
    v["b"] = arm_park(ctx, sb, exe, at=at, ctx_tokens=resume_ctx, extra_env=_AUTO)
    sandbox_scope.revoke(sb.home)
    # (f) 登記後把租約縮成 +60s（到點時已過期）
    sb, exe = new_box(ctx, mode="resume_ok", sleep=60)
    v["f"] = arm_park(ctx, sb, exe, at=at, ctx_tokens=resume_ctx, extra_env=_AUTO)
    sandbox_scope.grant(sb.home, until=now() + timedelta(seconds=60), now=now())
    # (g) 刪身分檔、保留家目錄
    sb, exe = new_box(ctx, mode="resume_ok", sleep=60)
    v["g"] = arm_park(ctx, sb, exe, at=at, ctx_tokens=resume_ctx, extra_env=_AUTO)
    (sb.home / sandbox_scope.IDENTITY_NAME).unlink()
    # (i) --claude 指向家外替身（D-18：sandbox_real_exe）
    sb, exe = new_box(ctx, mode="resume_ok", sleep=60)
    out_home = fakeclaude.outside_home()
    out_exe = fakeclaude.build(out_home)
    fakeclaude.configure(out_home, "resume_ok", sleep=60, projdir=projects_dir() / slug_of(sb.root))
    v["i"] = arm_park(ctx, sb, exe, at=at, ctx_tokens=resume_ctx, extra_env=_AUTO, claude=str(out_exe))
    v["i_out"] = out_home
    # (d) 到點前刪沙盒家目錄（沙盒 tools 複本）；工作不記帳＝由 sweep 的發現式掃描撤掉
    sb, exe = new_box(ctx, mode="resume_ok", sleep=60)
    v["d"] = arm_park(ctx, sb, exe, at=at, ctx_tokens=resume_ctx, extra_env=_AUTO, track=False)
    rmtree(sb.root)
    # (c)(c′)(h) 真 tools 的 park --fire
    v["c"] = _real_tools_task(ctx, "c", at)
    v["c2"] = _real_tools_task(ctx, "c2", at, delete_pkg=True)
    v["h"] = _real_tools_task(ctx, "h", at, delete_home=True)
    return v


@case("RV-SE01", "sideeffect", refs=("E2E-SE-01",), sched=True)
@kills_runners
def rv_se01(ctx: CaseContext) -> None:
    resume_ctx, why = pick_resume_ctx()
    ctx.evidence(f"F4 預算 RESUME 上下文={resume_ctx}：{why}")
    at = _minute_after(200)
    v = _arm_variants(ctx, at, resume_ctx)
    boxes = [v[k].sb for k in ("e1", "e2", "e3", "b", "f", "g", "i", "d")] + [x[0] for x in (v["c"], v["c2"], v["h"])]
    boxes.append(SimpleNamespace(sid=v["a"]["sid"], home=Path(v["a"]["home"])))
    ctx.check(at > now() + timedelta(seconds=45), f"建置太慢，距到點只剩 {(at - now()).total_seconds():.0f}s")
    ctx.evidence(f"十二變體全部建好（到點 {at.isoformat()}，剩 {(at - now()).total_seconds():.0f}s）；{v['e1_xml']}")
    # (a) 殺主人（不帶 /T）：身分檔 owner_pid 已死、租約未過期
    kill_pid(int(v["a"]["pid"]))
    for _ in range(20):
        if not pid_alive(int(v["a"]["pid"])):
            break
        time.sleep(0.5)
    ctx.check(not pid_alive(int(v["a"]["pid"])), "主人行程殺不掉")
    # 到點前 10 秒至到點後 60 秒每 2 秒查「沒有開窗」（本案例從現在就開始查，涵蓋該區間）
    n = _watch(ctx, boxes, at + timedelta(seconds=75))
    ctx.evidence(f"沒有開窗輪詢 {n} 次（每 2 秒，到點前後）無真 claude 行程、無可見視窗")
    a = SimpleNamespace(sid=v["a"]["sid"], home=Path(v["a"]["home"]))
    # 拒絕變體（a b f g i）與真 tools 的 c／c′ 一定自拆；正控 e1／e2／e3 的 job 是在 spawn 成功／失敗後才拆，且假 claude 子行程仍在 job 物件內時排程器
    # 會延後回收，所以只等它們的標記離開 armed；(h) 的 job 以 rc 9 在居所檢查就結束，來不及自拆，由帳撤。
    left = wait_gone([v["a"]["label"], v["b"].label, v["f"].label, v["g"].label, v["i"].label, v["c"][1], v["c2"][1]], 90)
    for key in ("e1", "e2", "e3"):
        for _ in range(45):
            if (marker_of(v[key].sb) or {}).get("status") != "armed":
                break
            time.sleep(2)
    diag = [(n, task_result(n), (get_task(n) or {}).get("state")) for n in left]
    ctx.check(not left, f"到點後這些工作應已自拆（refused／fired／skipped 都自拆）：{diag}")
    _refused(ctx, "(a)", a, "sandbox_owner_dead", task=v["a"]["label"])
    _refused(ctx, "(b)", v["b"].sb, "sandbox_no_lease")
    _refused(ctx, "(f)", v["f"].sb, "sandbox_lease_expired")
    _refused(ctx, "(g)", v["g"].sb, "sandbox_unreadable", marker=False)
    _refused(ctx, "(i)", v["i"].sb, "sandbox_real_exe")
    ctx.check(not fakeclaude.calls(v["i_out"]), f"(i) 家外替身應 0 行：{fakeclaude.calls(v['i_out'])}")
    for key, reason in (("c", "root_mismatch"), ("c2", "target_missing")):
        sb, name, _pkg = v[key]
        ref = refusal(sb)
        ctx.check(ref is not None and ref.get("reason") == reason, f"({key}) 要 {reason}，實得 {ref}")
        ctx.check(not calls(sb) and "park_route" not in names(sb), f"({key}) 不該有假 claude 或 park_route")
        res = task_result(name)
        ctx.check(res is None or res["result"] == 0, f"({key}) 真 tools 的 job 應 rc 0：{res}")
    sb, name, _pkg = v["h"]
    ctx.check(not sb.root.exists(), "(h) 沙盒家目錄不該被 job 重建")
    res = task_result(name)
    ctx.check(res is not None and res["result"] == endurance_env().RC_RESIDENCE_MISSING, f"(h) LastTaskResult 要 {endurance_env().RC_RESIDENCE_MISSING}（RC_RESIDENCE_MISSING），實得 {res}")
    ctx.check(not events(sb), f"(h) 居所缺席時不得寫任何痕跡：{events(sb)}")
    # (e1) RESUME 正控
    sb = v["e1"].sb
    ev = events(sb)
    route = [e for e in ev if e.get("event") == "park_route"]
    ctx.check(len(route) == 1 and route[0]["route"] == "RESUME", f"(e1) park_route 應為 RESUME：{route}")
    cs = calls(sb)
    ctx.check(len(cs) == 1 and cs[0]["argv"][:2] == ["-r", sb.sid], f"(e1) 假 claude 應恰 1 次且 argv 含 -r <sid>：{cs}")
    ctx.check(Path(cs[0]["cwd"]).resolve() == Path(sb.root).resolve(), f"(e1) cwd 應為沙盒根：{cs[0]['cwd']}")
    after = len((v["e1"].projdir / f"{sb.sid}.jsonl").read_text(encoding="utf-8").splitlines())
    ctx.check(after == v["e1_lines"] + 1, f"(e1) 沙盒逐字稿應多一行替身記錄：{v['e1_lines']}→{after}")
    ctx.check("park_resumed" in names(sb), f"(e1) 缺 park_resumed：{names(sb)}")
    ctx.check((marker_of(sb) or {}).get("status") == "fired", f"(e1) 標記應為 fired：{marker_of(sb)}")
    ctx.check(sum(1 for n in names(sb) if n == "park_attempt") == PARK_ATTEMPTS, f"(e1) park_attempt 應 {PARK_ATTEMPTS} 筆：{names(sb)}")
    ctx.check(not [n for n in names(sb) if n in ("park_resume_failed", "park_chain_failed") or n.startswith("sideeffect")], f"(e1) 不該有失敗鏈／sideeffect_*：{names(sb)}")
    _sideless(ctx, "(e1)", sb)
    # (e2) 模式 notify：有 park_route、因模式拒絕、假 claude 0 次
    sb = v["e2"].sb
    ctx.check("park_route" in names(sb) and not calls(sb), f"(e2) 應有 park_route 且假 claude 0 次（模式由 --job-env 帶到 job）：{names(sb)} {calls(sb)}")
    ctx.check(not [n for n in names(sb) if n.startswith("sideeffect")], f"(e2) 不是 L1 拒絕：{names(sb)}")
    # (e3) FRESH 正控
    sb = v["e3"].sb
    route = [e for e in events(sb) if e.get("event") == "park_route"]
    ctx.check(len(route) == 1 and route[0]["route"] == "FRESH", f"(e3) park_route 應為 FRESH：{route}")
    cs = calls(sb)
    ctx.check(len(cs) == 1 and "-r" not in cs[0]["argv"] and str(v["e3"].pkg) in " ".join(cs[0]["argv"]), f"(e3) 假 claude 應恰 1 次、argv 不含 -r、含交接包路徑：{cs}")
    ctx.check(Path(cs[0]["cwd"]).resolve() == Path(sb.root).resolve(), f"(e3) cwd 應為沙盒根：{cs[0]['cwd']}")
    jl = sorted(p.name for p in v["e3"].projdir.glob("*.jsonl"))
    ctx.check(len(jl) == 2, f"(e3) 沙盒 projects 目錄應多一個新逐字稿：{jl}")
    ctx.check("park_spawned" in names(sb) and (marker_of(sb) or {}).get("status") == "fired", f"(e3) 應 park_spawned 且標記 fired：{names(sb)} {marker_of(sb)}")
    ctx.check(sum(1 for n in names(sb) if n == "park_attempt") == PARK_ATTEMPTS and "park_chain_failed" not in names(sb), f"(e3) park_attempt／失敗鏈不符：{names(sb)}")
    ctx.check(not [n for n in names(sb) if n.startswith("sideeffect")], f"(e3) 不該有 sideeffect_*：{names(sb)}")
    # (d) 家目錄被刪：沒有開窗（已由輪詢保證）、家目錄沒被重建、LastTaskResult≠0、下一次 sweep 撤掉該工作
    d = v["d"]
    res = task_result(d.label)
    ctx.check(res is not None and res["result"] != 0, f"(d) 家目錄被刪，job 應失敗（LastTaskResult≠0）：{res}")
    ctx.check(not d.sb.root.exists(), "(d) 沙盒家目錄不該被 job 重建")
    first = sweep_clean(ctx)
    ctx.check(get_task(d.label) is None, f"(d) 下一次 sweep（{first}）應撤掉該工作")
    # (a) 主人行程留下的帳：sweep 已撤；確認 OWNER 的沙盒根不再存在
    ctx.check(not Path(v["a"]["root"]).exists(), "sweep 後主人行程的沙盒根應已撤")
    ctx.evidence("十二變體全過：(a)owner_dead (b)no_lease (c)root_mismatch (c′)target_missing (d)家被刪＋sweep (e1)RESUME×1 "
                 "(e2)notify拒絕 (e3)FRESH×1 (f)lease_expired (g)unreadable (h)rc=9 (i)real_exe")


def _watch(ctx: CaseContext, boxes: list, until: datetime) -> int:
    n = 0
    while now() < until:
        bad = window_problems(boxes)
        ctx.check(not bad, "；".join(bad))
        n += 1
        time.sleep(2.0)
    return n

