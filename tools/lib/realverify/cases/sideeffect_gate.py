# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""sideeffect 家族（三）：登記／spawn 站點的 L1 判準真機 E2E——RV-SE04（租約與自毀）、RV-SE05（spawn 站點拒絕是終局）。

載具：沙盒內的真 `sessionctl.py`（工具副本）＋真 schtasks＋假 claude（D-14）。RV-SE05 的「spawn 前才撤租約」用
一支放在**沙盒外**的 spy 包裝腳本（`runpy` 跑同一支 `sessionctl.py`，只在 fire 站點放行後撤租約），產品碼本身不動。
"""
from __future__ import annotations

import re
import time
import uuid
from datetime import timedelta
from pathlib import Path

from lib import sandbox_scope

from . import CaseContext, case
from .sessionctl_park import PY, ctl_env, get_task, ps, run, tasks_like
from .sideeffect_lib import (
    arm_park,
    calls,
    control_dir,
    endurance_env,
    iso_at,
    lease_allow_until,
    marker_of,
    names,
    new_box,
    now,
    pick_resume_ctx,
    plain_env,
    prep_pkg,
    refusal,
    sessionctl,
    task_xml,
    wait_gone,
    wait_until_time,
)

_AUTO = {"AUTOSDD_SESSION_SWITCH_MODE": "auto"}


def _minute_after(seconds: float):
    return (now() + timedelta(seconds=seconds) + timedelta(minutes=1)).replace(second=0, microsecond=0)


@case("RV-SE04", "sideeffect", refs=("E2E-SE-04",), sched=True, lease_minutes=300)
def rv_se04(ctx: CaseContext) -> None:
    """(a) 租約 30 分、`park --at +3`、登記後 revoke：XML `EndBoundary` ≥ `StartBoundary`＝租約；到點 `sandbox_no_lease`、自拆、假 claude 0 次。
    (b) 租約 30 分、`park --at +40`：rc 4＋stderr `lease_shorter_than_fire`＋痕跡 `sideeffect_refused`、排程器無新工作。
    (c) 租約縮短（+6 分，到點仍在其內）、登記後 `Disable-ScheduledTask`、等過 EndBoundary 輪詢 15 分：工作被 OS 刪除（實測秒數入帳）。
    (d) 案例宣告 `lease_minutes=300`：`grant(200 分)`／`grant(400 分)` 各存 +200／+300。"""
    resume_ctx, _why = pick_resume_ctx()
    # (d) 最快，先驗
    sb_d, _ = new_box(ctx, tools=False)
    for want_min, ask in ((200, 200), (300, 400)):
        t0 = now()
        ctx.grant_side_effects(sb_d, minutes=ask, window=False)
        gap = (lease_allow_until(sb_d) - t0).total_seconds()
        ctx.check(abs(gap - want_min * 60) <= 20, f"(d) grant({ask} 分) 應存 +{want_min} 分，實得 {gap / 60:.1f} 分")
    # (b) 租約 30、+40 分 ⇒ lease_shorter_than_fire
    sb_b, exe_b = new_box(ctx, mode="resume_ok")
    pkg_b = prep_pkg(ctx, sb_b, ctx_tokens=resume_ctx)
    ctx.grant_side_effects(sb_b, minutes=30, window=False)
    rb = sessionctl(sb_b, "park", "--session-id", sb_b.sid, "--at", iso_at(now() + timedelta(minutes=40)), "--why", "realverify SE04 租約短於到點",
                    "--pkg", str(pkg_b), "--claude", str(exe_b), extra_env=_AUTO)
    ctx.check(rb.returncode == 4 and "lease_shorter_than_fire" in rb.stderr, f"(b) 應 rc 4 且 stderr 帶 lease_shorter_than_fire：rc={rb.returncode} {rb.stderr[-300:]}")
    ref = refusal(sb_b)
    ctx.check(ref is not None and ref.get("reason") == "lease_shorter_than_fire", f"(b) 痕跡應有 sideeffect_refused lease_shorter_than_fire：{ref}")
    ctx.check(not tasks_like(f"AutoSDD_HandoffSpawn_{sb_b.sid[:8]}_*"), "(b) 排程器不該有新工作")
    # (a) 登記後 revoke
    at = _minute_after(170)
    sb_a, exe_a = new_box(ctx, mode="resume_ok")
    arm_a = arm_park(ctx, sb_a, exe_a, at=at, ctx_tokens=resume_ctx, extra_env=_AUTO, grant_minutes=30)
    xml = task_xml(arm_a.label)
    end, start = re.search(r"<EndBoundary>([^<]+)<", xml), re.search(r"<StartBoundary>([^<]+)<", xml)
    ctx.check(bool(end and start) and end.group(1) >= start.group(1), f"(a) 工作 XML 要有 EndBoundary 且 ≥ StartBoundary：{end and end.group(1)} {start and start.group(1)}")
    sandbox_scope.revoke(sb_a.home)
    # (c) 租約縮短、登記後停用、等 EndBoundary
    sb_c, exe_c = new_box(ctx, mode="resume_ok")
    arm_c = arm_park(ctx, sb_c, exe_c, at=at, ctx_tokens=resume_ctx, extra_env=_AUTO, grant_minutes=6)
    end_c = lease_allow_until(sb_c)
    rc, out = ps(f"Disable-ScheduledTask -TaskName '{arm_c.label}' | Out-Null")
    ctx.check(rc == 0, f"(c) Disable-ScheduledTask rc={rc} {out[:200]}")
    # (a) 到點
    wait_until_time(arm_a.fire_at, 75)
    left = wait_gone([arm_a.label], 60)
    ctx.check(not left, f"(a) 到點後工作應自拆：{left}")
    ref = refusal(sb_a)
    ctx.check(ref is not None and ref.get("reason") == "sandbox_no_lease", f"(a) 要 sandbox_no_lease：{ref} {names(sb_a)}")
    ctx.check(not calls(sb_a) and "park_route" not in names(sb_a), f"(a) 假 claude 應 0 次、無 park_route：{calls(sb_a)} {names(sb_a)}")
    # (c) 等 OS 自毀：EndBoundary 之後最多 15 分
    wait_until_time(end_c)
    t_end, deleted_after = time.monotonic(), None
    while time.monotonic() - t_end < 900:
        if get_task(arm_c.label) is None:
            deleted_after = time.monotonic() - t_end
            break
        time.sleep(5)
    ctx.check(deleted_after is not None, f"(c) 過 EndBoundary 15 分仍未被 OS 刪除（DES §0.4-4）：{get_task(arm_c.label)}")
    ctx.check(not calls(sb_c), f"(c) 停用的工作不該執行（假 claude 0 次）：{calls(sb_c)}")
    ctx.evidence(f"(a) no_lease 自拆、(b) rc4 lease_shorter_than_fire、(c) 停用工作 EndBoundary 後 {deleted_after:.0f}s 被 OS 刪除、(d) grant 200→+200／400→+300")


_SPY = '''\
import runpy
import sys

TOOLS = {tools!r}
sys.path[:0] = [TOOLS, TOOLS + "/lib"]
import lib.sessionctl  # noqa: F401  # 與 sessionctl.py 同一條匯入路徑
import sandbox_scope
from lib.sessionctl import se_gate

_orig = se_gate.check


def _spy(site, **kw):
    verdict = _orig(site, **kw)
    if site == "park_cli._cmd_fire":
        sandbox_scope.revoke({home!r})  # fire 站點放行後、spawn 站點前撤租約
    return verdict


se_gate.check = _spy
sys.argv = ["sessionctl.py", *{args!r}]
runpy.run_path(TOOLS + "/sessionctl.py", run_name="__main__")
'''


@case("RV-SE05", "sideeffect", refs=("E2E-SE-05",), sched=True)
def rv_se05(ctx: CaseContext) -> None:
    """(1) 沙盒無租約、模式 auto：真跑沙盒內 `handoff --spawn <pkg> --claude <假>` ⇒ rc 10（`RC_SIDEEFFECT_REFUSED`）、stderr 帶 `sandbox_no_lease`、
    痕跡 `sideeffect_refused`、假 claude 0 次、無 `.resumed`／`.spawned`。(2) `park --fire` 走到 spawn 站點：有效租約通過 `_cmd_fire`、spawn 前 revoke
    （spy 包裝腳本）⇒ 標記 `refused`、無 handback、無另一路嘗試、job rc 0、工作自拆。"""
    resume_ctx, _why = pick_resume_ctx()
    # (1) handoff --spawn（FRESH 形狀的交接包；沒給租約）
    sb, exe = new_box(ctx, mode="fresh_ok")
    pkg = prep_pkg(ctx, sb, ctx_tokens=None)
    argv = [PY, str(sb.root / "tools" / "sessionctl.py"), "handoff", "--spawn", str(pkg), "--claude", str(exe)]  # 不是 claude 視窗：refusal 在 runner 前，且 --claude 是假替身
    r = run(argv, cwd=sb.root, env=ctl_env(sb, extra=_AUTO), timeout=120)
    ctx.check(r.returncode == sandbox_scope.RC_SIDEEFFECT_REFUSED, f"(1) rc 應為 RC_SIDEEFFECT_REFUSED={sandbox_scope.RC_SIDEEFFECT_REFUSED}：rc={r.returncode} {r.stderr[-300:]}")
    ctx.check("sandbox_no_lease" in r.stderr, f"(1) stderr 應帶 sandbox_no_lease：{r.stderr[-300:]}")
    ref = refusal(sb)
    ctx.check(ref is not None and ref.get("reason") == "sandbox_no_lease", f"(1) 痕跡 sideeffect_refused：{ref} {names(sb)}")
    ctx.check(not calls(sb), f"(1) 假 claude 應 0 次：{calls(sb)}")
    ctx.check(not pkg.with_suffix(".resumed").exists() and not pkg.with_suffix(".spawned").exists(), "(1) 不得寫 .resumed／.spawned")
    # (2) park --fire 走到 spawn 站點（RESUME 形狀：spawn_resume 站點）
    sb2, exe2 = new_box(ctx, mode="resume_ok")
    armed = arm_park(ctx, sb2, exe2, at=now() + timedelta(minutes=10), ctx_tokens=resume_ctx, extra_env=_AUTO, grant_minutes=30)
    spy = control_dir(ctx) / "spy_fire.py"
    fire_args = ["park", "--fire", "--job", armed.label, "--session-id", sb2.sid, "--pkg", str(armed.pkg), "--fire-at", armed.fire_at.isoformat(), "--claude", str(exe2)]
    spy.write_text(_SPY.format(tools=str(sb2.root / "tools"), home=str(sb2.home), args=fire_args), encoding="utf-8", newline="\n")
    r2 = run([PY, str(spy)], cwd=sb2.root, env=ctl_env(sb2, extra=_AUTO), timeout=240)
    ctx.check(r2.returncode == 0, f"(2) job rc 應為 0（終局拒絕不當失敗）：rc={r2.returncode} {r2.stderr[-400:]}")
    mk = marker_of(sb2)
    ctx.check(mk is not None and mk["status"] == "refused", f"(2) 標記應為 refused：{mk and mk['status']}")
    ev = names(sb2)
    ctx.check(not [n for n in ev if n in ("park_resume_failed", "park_spawn_failed", "park_chain_failed", "park_attempt")], f"(2) 不得走失敗鏈／另一路：{ev}")
    ref2 = refusal(sb2)
    ctx.check(ref2 is not None and ref2.get("site") in ("park_cli.spawn_resume", "handoff.spawn"), f"(2) 拒絕站點應為 spawn 站點：{ref2}")
    ctx.check(not calls(sb2) and not list((sb2.home / "handback").glob("*")), f"(2) 假 claude 0 次、無 handback：{calls(sb2)}")
    ctx.check(get_task(armed.label) is None, "(2) job 應自拆")
    ctx.evidence(f"(1) rc={r.returncode} stderr 帶 sandbox_no_lease；(2) spy 在 fire 站點後撤租約 ⇒ 站點 {ref2.get('site')} 拒絕、標記 refused、job rc 0；events={ev}")


@case("RV-SE10", "sideeffect", refs=("E2E-SE-10",), sched=True)
def rv_se10(ctx: CaseContext) -> None:
    """job 環境允許表：沙盒 `park --at`（居所／通知空／哨兵 1、模式 auto）後讀 Action 引數：7 居所＋3 開關各一個 `--job-env`、居所值在沙盒下；
    到點事件全落沙盒痕跡；repo 本體以乾淨環境跑 `park --status` rc 0；三個非法 `--job-env` 皆 rc 2；沙盒行程環境把通知設為開啟後
    再 `park --at` ⇒ 登記時就 rc 2、stderr 點名 `AUTOSDD_DESKTOP_NOTIFY`、無新工作。"""
    keys = endurance_env().JOB_ENV_KEYS
    resume_ctx, _why = pick_resume_ctx()
    at = _minute_after(170)
    sb, exe = new_box(ctx, mode="fail")
    armed = arm_park(ctx, sb, exe, at=at, ctx_tokens=resume_ctx, extra_env=_AUTO, grant_minutes=30)
    args = (get_task(armed.label) or {}).get("arguments", "")
    pairs = re.findall(r'--job-env"?\s+"?([A-Z_]+)=([^"\s]*)"?', args)
    got = {k: v for k, v in pairs}
    ctx.check(set(got) == set(keys), f"Arguments 應含 10 個 --job-env 鍵（7 居所＋3 開關）：缺 {set(keys) - set(got)} 多 {set(got) - set(keys)}")
    ctx.check(all(str(sb.home).lower() in v.lower() for k, v in got.items() if k in endurance_env().RESIDENCE_KEYS), f"7 個居所值都應在沙盒下：{got}")
    ctx.check(got["AUTOSDD_DESKTOP_NOTIFY"] == "" and got["AUTOSDD_SENTINEL_OFF"] == "1" and got["AUTOSDD_SESSION_SWITCH_MODE"] == "auto", f"3 開關值不符：{got}")
    # 非法 --job-env（repo 本體、乾淨環境）
    tools = str(Path(__file__).resolve().parents[3] / "sessionctl.py")
    ok = run([PY, tools, "park", "--status", "--session-id", str(uuid.uuid4())], cwd=Path(tools).parent.parent, env=plain_env(), timeout=120)
    ctx.check(ok.returncode == 0, f"乾淨環境 park --status 應 rc 0：rc={ok.returncode} {ok.stderr[-200:]}")
    for bad in (("FOO_DIR=x",), ("AUTOSDD_DESKTOP_NOTIFY=1",), ("AUTOSDD_SESSION_SWITCH_MODE=xyz",)):
        r = run([PY, tools, "--job-env", bad[0], "status"], cwd=Path(tools).parent.parent, env=plain_env(), timeout=120)
        ctx.check(r.returncode == 2, f"--job-env {bad[0]} 應 rc 2：rc={r.returncode} {r.stderr[-200:]}")
    # 通知開啟的沙盒行程環境 ⇒ 登記時就 rc 2
    sb2, exe2 = new_box(ctx, mode="fail")
    pkg2 = prep_pkg(ctx, sb2, ctx_tokens=resume_ctx)
    ctx.grant_side_effects(sb2, minutes=30, window=False)
    r = sessionctl(sb2, "park", "--session-id", sb2.sid, "--at", iso_at(now() + timedelta(minutes=5)), "--why", "realverify SE10 通知開啟值", "--pkg", str(pkg2),
                   "--claude", str(exe2), extra_env={**_AUTO, "AUTOSDD_DESKTOP_NOTIFY": "1"})
    ctx.check(r.returncode == 2 and "AUTOSDD_DESKTOP_NOTIFY" in r.stderr, f"通知開啟值登記應 rc 2 並點名 AUTOSDD_DESKTOP_NOTIFY：rc={r.returncode} {r.stderr[-300:]}")
    ctx.check(not tasks_like(f"AutoSDD_HandoffSpawn_{sb2.sid[:8]}_*"), "通知開啟值登記不該有新工作（登記時就失敗，不等到點）")
    # 到點：事件全落沙盒痕跡
    wait_until_time(armed.fire_at, 75)
    ctx.check(wait_gone([armed.label], 60) == [], "到點後工作應自拆")
    ctx.check("park_job_start" in names(sb), f"到點事件應落沙盒痕跡：{names(sb)}")
    ctx.evidence("Arguments 10 個 --job-env（居所在沙盒下、通知空、哨兵 1、模式 auto）；乾淨環境 status rc 0；三個非法值 rc 2；通知開啟值登記 rc 2；到點事件落沙盒")
