# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""sideeffect 家族（四）：各產品站點的 L1 判準真機 E2E——RV-SE06（登記／headless 站點）、RV-SE07（哨兵到點）、
RV-SE08（通知與 openitems 到點入口）。

載具：沙盒內的工具副本（逐位元相同的產品碼）＋真行程＋真 schtasks＋假 claude。沒有 CLI 的站點（`oldwin_sched.schedule_retry`、
`quota_escalation.alert／patrol_housekeeping`）以**沙盒內的真行程**直接呼叫該產品函式（`python -c`，匯入的是沙盒的 tools 副本）。
"""
from __future__ import annotations

import json
import re
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path

from lib import sandbox_scope

from .. import fakeclaude, leases, sched
from ..sandbox import REPO, projects_dir, slug_of, write_excludes
from . import CaseContext, case
from .sentinel import _env as sentinel_env
from .sentinel import append_limit_event
from .sessionctl_park import PY, ctl_env, get_task, ps, run
from .sideeffect_lib import (
    calls,
    control_dir,
    iso_at,
    new_box,
    now,
    pick_resume_ctx,
    prep_pkg,
    sessionctl,
    task_xml,
    window_problems,
)

_AUTO = {"AUTOSDD_SESSION_SWITCH_MODE": "auto"}
_OI_PROTOCOL = Path("docs") / "06_quality" / "OpenItems_Protocol"


def tasks_with(root: Path) -> list[str]:
    """Action 含該沙盒根的全部 `AutoSDD_*` 排程（產品替沙盒登記的工作都在這；不靠名字猜）。"""
    r = str(root).lower()
    return sorted(n for n, action in sched.list_actions("AutoSDD_*").items() if r in action.lower())


def refused_rows(sb) -> list[dict]:
    """沙盒 `traces/` 下全部 jsonl 中 `event=sideeffect_refused` 的列（各站點痕跡檔名不同：session_switch／engine／sideeffect_refused）。"""
    out: list[dict] = []
    for p in sorted((Path(sb.home) / "traces").rglob("*.jsonl")):
        for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if '"sideeffect_refused"' in ln:
                try:
                    out.append(json.loads(ln))
                except ValueError:
                    pass
    return out


def product_call(sb, code: str, env: dict | None = None):
    """沙盒內真行程呼叫產品函式（匯入的是沙盒 `tools/` 副本；先 `import lib.sessionctl` 備妥 sys.path）。"""
    tools = sb.root / "tools"
    pre = f"import sys; sys.path[:0]=[{str(tools)!r},{str(tools / 'lib')!r}]; import lib.sessionctl\n"
    return run([PY, "-c", pre + code], cwd=sb.root, env=env or ctl_env(sb), timeout=180)


def _setup(ctx: CaseContext, *, tools: bool = True):
    resume_ctx, _why = pick_resume_ctx()
    sb, exe = new_box(ctx, mode="fail", tools=tools)
    pkg = prep_pkg(ctx, sb, ctx_tokens=resume_ctx)
    tp = projects_dir() / slug_of(sb.root) / f"{sb.sid}.jsonl"
    write_excludes(sb.root, ("/docs/",))  # openitems 帳寫在沙盒 docs/，不得弄髒 park 的 spawn 前置（工作樹乾淨）
    shutil.copytree(REPO / _OI_PROTOCOL, sb.root / _OI_PROTOCOL)
    return sb, exe, pkg, tp


def _open_item(ctx: CaseContext, sb) -> str:
    r = run([PY, str(sb.root / "tools" / "openitems.py"), "--root", str(sb.root), "open", "--title", "rv sideeffect", "--source", "docs/03_testing/contracts/TCS-SideEffectIsolation-20261120.md#E2E-SE-06",
             "--scope", "sandbox", "--kind", "auto", "--check", json.dumps({"argv": ["python", "-c", "pass"], "pass": "rc0"}), "--by", "human"],
            cwd=sb.root, env=ctl_env(sb), timeout=120)
    m = re.search(r"OI-[0-9A-Za-z\-]+", r.stdout)
    ctx.check(r.returncode == 0 and m is not None, f"openitems open 失敗 rc={r.returncode} {r.stdout[-200:]} {r.stderr[-300:]}")
    return m.group(0)


def _six_sites(ctx: CaseContext, sb, exe, pkg, tp, oid: str, at: datetime, pb: Path) -> dict:
    """六個登記站點各跑一次；回 `{站點: CompletedProcess}`（oldwin 為 product_call）。"""
    old_sid, new_sid = "aaaaaaaa-0000-4000-8000-000000000001", "bbbbbbbb-0000-4000-8000-000000000002"
    sb.oldwin_prefix()  # 沙盒專屬重試排程前綴：收尾由 Sandbox.cleanup 撤
    return {
        "park": sessionctl(sb, "park", "--session-id", sb.sid, "--at", iso_at(at), "--why", "realverify SE06 登記站點", "--pkg", str(pkg),
                           "--claude", str(exe), extra_env=_AUTO),
        "oldwin": product_call(sb, f"import time; from lib.sessionctl import oldwin_sched; rc, cred = oldwin_sched.schedule_retry({old_sid!r}, {new_sid!r}, {str(pkg)!r}, time.time()+900); sys.exit(rc)"),
        "sentinel": run([PY, str(sb.root / "tools" / "session_resume_planner.py"), "--arm-sentinel", "--session-id", sb.sid, "--transcript", str(tp), "--claude", str(exe)],
                        cwd=sb.root, env=sentinel_env(sb), timeout=180),
        "engine": run([PY, str(sb.root / "tools" / "lib" / "engine_resume_job.py"), "--playbook", str(pb), "--at", iso_at(at), "--cwd", str(sb.root)],
                      cwd=sb.root, env=ctl_env(sb), timeout=180),
        "openitems": run([PY, str(sb.root / "tools" / "openitems.py"), "--root", str(sb.root), "drive", oid, "--at", iso_at(at)],
                         cwd=sb.root, env=ctl_env(sb), timeout=180),
        "si": run([PY, str(sb.root / "tools" / "selfimproving.py"), "sched", "arm"], cwd=sb.root, env=ctl_env(sb), timeout=180),
    }


_SITE_NAMES = {"park": "park_cli._cmd_park", "oldwin": "oldwin_sched.schedule_retry", "sentinel": "_register_and_record",
               "engine": "engine_resume_job.arm", "openitems": "openitems.drive", "si": "selfimproving.sched_arm"}


@case("RV-SE06", "sideeffect", refs=("E2E-SE-06",), sched=True)
def rv_se06(ctx: CaseContext) -> None:
    """(a) 沙盒無租約：六個登記站點（park／oldwin 重試／哨兵武裝／engine resume／openitems drive／SI sched arm）各被拒（stderr 帶站點與
    `sandbox_no_lease`、痕跡 `sideeffect_refused` 帶站點）、沒有新工作。(b) 有租約：除 SI（Windows 巡邏任務由安裝器註冊，帶不進
    job 環境／自毀 ⇒ 依產品設計 `sandbox_installer_no_job_env` 拒絕）外，五站點都登記成功，工作 XML 帶 `EndBoundary`、引數含 `--job-env`，
    撤後查無。(c) headless 站點：`session_resume_planner.py --probe-quota` 三組（無租約＋沙盒替身／有租約＋家外替身／有租約＋沙盒替身）、
    `selfimproving.py patrol` 前兩組。"""
    sb, exe, pkg, tp = _setup(ctx)
    oid = _open_item(ctx, sb)
    d = control_dir(ctx)
    pb = d / "pb.yaml"
    pb.write_text("name: rv-sideeffect\n", encoding="utf-8", newline="\n")
    at = now() + timedelta(minutes=10)
    # (a) 無租約
    res = _six_sites(ctx, sb, exe, pkg, tp, oid, at, pb)
    for key, r in res.items():
        site = _SITE_NAMES[key]
        ctx.check(r.returncode != 0 and "sandbox_no_lease" in (r.stderr + r.stdout) and site in (r.stderr + r.stdout), f"(a) {key}：應被拒（非 0、帶 {site} 與 sandbox_no_lease）：rc={r.returncode} {r.stderr[-300:]}{r.stdout[-200:]}")  # noqa: E501
        if key not in ("si",):
            ctx.check(r.returncode == 4, f"(a) {key}：登記站點拒絕的 rc 應為 4，實得 {r.returncode}")
    rows = refused_rows(sb)
    hit = {str(x.get("site")) for x in rows}
    for key in ("park", "oldwin", "sentinel", "engine", "openitems", "si"):
        ctx.check(any(_SITE_NAMES[key] in s or s.endswith(_SITE_NAMES[key].split(".")[-1]) for s in hit), f"(a) 痕跡缺 sideeffect_refused site={_SITE_NAMES[key]}：{sorted(hit)}")
    ctx.check(not tasks_with(sb.root) and get_task(f"AutoSDD_Sentinel_{sb.sid}") is None, f"(a) 無租約不得有任何新工作：{tasks_with(sb.root)}")
    # (b) 有租約
    ctx.grant_side_effects(sb, minutes=30, window=False)
    res = _six_sites(ctx, sb, exe, pkg, tp, oid, at, pb)
    made = tasks_with(sb.root)
    for name in made:
        ctx.sched_track(name)
    for key in ("park", "oldwin", "sentinel", "engine", "openitems"):
        r = res[key]
        ctx.check(r.returncode == 0, f"(b) {key} 有租約應登記成功 rc 0：rc={r.returncode} {r.stderr[-300:]}{r.stdout[-200:]}")
    ctx.check(res["si"].returncode != 0 and "sandbox_installer_no_job_env" in res["si"].stdout, f"(b) SI 在 Windows 應因 sandbox_installer_no_job_env 拒絕：{res['si'].stdout[-300:]}")
    ctx.check(len(made) >= 5, f"(b) 應有 ≥5 支工作（park／oldwin／哨兵／engine／openitems）：{made}")
    for name in made:
        xml, task = task_xml(name), get_task(name)
        ctx.check("<EndBoundary>" in xml, f"(b) {name} 的 XML 缺 EndBoundary")
        ctx.check(task is not None and "--job-env" in task["arguments"], f"(b) {name} 的 Action 引數應含 --job-env：{task and task['arguments'][:200]}")
    for name in made:
        leases.revoke_sched(name)
    ctx.check(not tasks_with(sb.root), f"(b) 撤後應查無：{tasks_with(sb.root)}")
    # (c) headless 站點：probe-quota 三組＋patrol 兩組
    sandbox_scope.revoke(sb.home)
    planner = str(sb.root / "tools" / "session_resume_planner.py")
    out_home = fakeclaude.outside_home()
    out_exe = fakeclaude.build(out_home)
    fakeclaude.configure(out_home, "fail")
    penv = ctl_env(sb, extra={"HTTPS_PROXY": "http://127.0.0.1:9"})  # 擋掉真額度端點（L0 讀不到 ⇒ 才會走付費探測＝起 --claude；同時不對真端點發請求）
    g1 = run([PY, planner, "--probe-quota", "--claude", str(exe)], cwd=sb.root, env=penv, timeout=180)
    ctx.grant_side_effects(sb, minutes=30, window=False)
    g2 = run([PY, planner, "--probe-quota", "--claude", str(out_exe)], cwd=sb.root, env=penv, timeout=180)
    g3 = run([PY, planner, "--probe-quota", "--claude", str(exe)], cwd=sb.root, env=penv, timeout=180)
    ctx.check(g1.returncode == sandbox_scope.RC_SIDEEFFECT_REFUSED and "sandbox_no_lease" in g1.stderr, f"(c) probe-quota 組1（無租約）應 rc {sandbox_scope.RC_SIDEEFFECT_REFUSED}＋sandbox_no_lease：rc={g1.returncode} {g1.stderr[-200:]}")  # noqa: E501
    ctx.check(g2.returncode == sandbox_scope.RC_SIDEEFFECT_REFUSED and "sandbox_real_exe" in g2.stderr, f"(c) probe-quota 組2（家外替身）應 rc {sandbox_scope.RC_SIDEEFFECT_REFUSED}＋sandbox_real_exe：rc={g2.returncode} {g2.stderr[-200:]}")  # noqa: E501
    ctx.check(len(calls(sb)) == 1 and not fakeclaude.calls(out_home), f"(c) 替身記錄：沙盒替身應恰 1 行（只有組3放行並用 --claude）、家外替身 0 行：{len(calls(sb))} {len(fakeclaude.calls(out_home))}")  # noqa: E501
    ctx.check(g3.returncode != sandbox_scope.RC_SIDEEFFECT_REFUSED, f"(c) probe-quota 組3 不該被 L1 拒：rc={g3.returncode} {g3.stderr[-200:]}")
    sandbox_scope.revoke(sb.home)
    p1 = run([PY, str(sb.root / "tools" / "selfimproving.py"), "patrol", "--claude", str(exe)], cwd=sb.root, env=ctl_env(sb), timeout=180)
    ctx.grant_side_effects(sb, minutes=30, window=False)
    p2 = run([PY, str(sb.root / "tools" / "selfimproving.py"), "patrol", "--claude", str(out_exe)], cwd=sb.root, env=ctl_env(sb), timeout=180)
    pr = {(str(x.get("site")), str(x.get("reason"))) for x in refused_rows(sb)}
    ctx.check(("selfimproving.patrol", "sandbox_no_lease") in pr and ("selfimproving.patrol", "sandbox_real_exe") in pr, f"(c) patrol 兩組痕跡應含 sandbox_no_lease／sandbox_real_exe：{sorted(pr)}")
    ctx.check(p1.returncode == 0 and p2.returncode == 0 and not fakeclaude.calls(out_home), f"(c) patrol 拒絕時 rc 0（SI 一次性語意）、家外替身 0 行：{p1.returncode} {p2.returncode}")
    ctx.check(not window_problems([sb]), f"(c) 不得有真 claude 行程或視窗：{window_problems([sb])}")
    ctx.evidence("六站點：(a) 全拒（5 個 rc 4、SI rc≠0 帶 SCHED-SIDEEFFECT-REFUSED）；(b) 五支登記成功帶 EndBoundary＋--job-env、SI 因安裝器拒絕；"
                 "(c) probe-quota 三組 rc10／rc10／放行且沙盒替身恰 1 行；patrol 兩組 sandbox_no_lease／sandbox_real_exe。"
                 "誠實劃界：SI patrol 第三組（有租約＋沙盒替身會走到 patrolrun.launch）需要 SI 帳有已到期運轉，載具未種 SI 帳，未跑")


@case("RV-SE07", "sideeffect", refs=("E2E-SE-07",), sched=True)
def rv_se07(ctx: CaseContext) -> None:
    """沙盒有租約武裝哨兵後 revoke；逐字稿植入已過 reset 的撞線記錄，使 tick 要 probe／resume；由**真排程器**（`Start-ScheduledTask`）
    觸發 tick：沒有 `claude -p` 行程、哨兵自我解除（工作查無）、沙盒痕跡 `sideeffect_refused`（站點 `_sentinel_tick`）、替身 0 次。"""
    sb, exe, _pkg, tp = _setup(ctx)
    ctx.grant_side_effects(sb, minutes=30, window=False)
    target = (now() - timedelta(minutes=100)).replace(minute=0, second=0, microsecond=0)
    append_limit_event(tp, target - timedelta(minutes=30), f"You've hit your session limit · resets {target.hour % 12 or 12}{'am' if target.hour < 12 else 'pm'}")
    r = run([PY, str(sb.root / "tools" / "session_resume_planner.py"), "--arm-sentinel", "--session-id", sb.sid, "--transcript", str(tp), "--claude", str(exe)],
            cwd=sb.root, env=sentinel_env(sb), timeout=180)
    ctx.check(r.returncode == 0, f"--arm-sentinel rc={r.returncode} {r.stderr[-300:]}")
    name = f"AutoSDD_Sentinel_{sb.sid}"
    ctx.sched_track(name)
    ctx.check(get_task(name) is not None, "哨兵應已登記")
    sandbox_scope.revoke(sb.home)
    rc, out = ps(f"Start-ScheduledTask -TaskName '{name}'")
    ctx.check(rc == 0, f"真排程器觸發 tick 失敗 rc={rc} {out[:200]}")
    end = time.monotonic() + 120
    while time.monotonic() < end and get_task(name) is not None:
        ctx.check(not window_problems([sb]), f"tick 期間不得有真 claude 行程：{window_problems([sb])}")
        time.sleep(2)
    ctx.check(get_task(name) is None, "哨兵 tick 被拒後應自我解除（工作查無）")
    rows = [x for x in refused_rows(sb) if "sentinel" in str(x.get("site"))]
    ctx.check(rows and rows[-1].get("reason") == "sandbox_no_lease", f"沙盒痕跡應有 sideeffect_refused site=_sentinel_tick reason=sandbox_no_lease：{refused_rows(sb)}")
    ctx.check(not calls(sb), f"替身應 0 次：{calls(sb)}")
    ctx.evidence(f"真排程器觸發 tick → {rows[-1].get('site')} {rows[-1].get('reason')}、哨兵自拆、替身 0 次")


@case("RV-SE08", "sideeffect", refs=("E2E-SE-08",), sched=True)
def rv_se08(ctx: CaseContext) -> None:
    """沙盒行程環境把通知鍵設為開啟（`AUTOSDD_DESKTOP_NOTIFY=1`）、無租約：沙盒內真行程呼叫 `quota_escalation.alert`／`patrol_housekeeping`
    ⇒ 回 `sideeffect_refused`、不出 toast、不入通知佇列（沙盒痕跡 `site=alert`／`site=patrol_housekeeping`）；openitems 到點入口
    （`run-driver`）對無租約的沙盒項目：不執行案例、工作自拆、痕跡 `openitems.run_driver`。誠實劃界：toast 本身量不到。"""
    sb, _exe, _pkg, tp = _setup(ctx)
    oid = _open_item(ctx, sb)
    notify_env = ctl_env(sb, extra={"AUTOSDD_DESKTOP_NOTIFY": "1"})  # 刻意開啟：驗判準先於 toast
    log = sb.home / "traces" / "rv_se08_hk.jsonl"
    r = product_call(sb, "import json, pathlib\nfrom datetime import datetime\nimport quota_escalation as qe\n"
                         f"st = {{'transcript': {str(tp)!r}, 'log_path': {str(log)!r}, 'session_id': 's'}}\n"
                         "a = qe.alert('rv sideeffect', st, loud=True, dead_agents=2)\n"
                         f"h = qe.patrol_housekeeping(pathlib.Path({str(tp)!r}), None, datetime.now().astimezone(), {{}}, 600.0, 't', pathlib.Path({str(log)!r}))\n"
                         "print(json.dumps({'alert': a, 'hk': h}))", env=notify_env)
    ctx.check(r.returncode == 0, f"alert／patrol_housekeeping 呼叫失敗 rc={r.returncode} {r.stderr[-400:]}")
    got = json.loads(r.stdout.strip().splitlines()[-1])
    ctx.check(got["alert"] == {"sideeffect_refused": True, "notify_queued": False} and got["hk"] == {"sideeffect_refused": True}, f"兩個通知站點都應回 sideeffect_refused：{got}")
    sites = {json.loads(ln).get("site") for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip()}
    ctx.check({"alert", "patrol_housekeeping"} <= sites, f"痕跡應含 site=alert／patrol_housekeeping：{sites}")
    ctx.check(not (sb.home / "traces" / "autosdd_notify_queue.json").exists(), "通知佇列檔不該被建立")
    # openitems 到點入口：有租約時登記驅動器，revoke 後以排程帶的同一條命令列跑 run-driver
    ctx.grant_side_effects(sb, minutes=30, window=False)
    at = now() + timedelta(minutes=10)
    dr = run([PY, str(sb.root / "tools" / "openitems.py"), "--root", str(sb.root), "drive", oid, "--at", iso_at(at)], cwd=sb.root, env=ctl_env(sb), timeout=180)
    ctx.check(dr.returncode == 0, f"drive 有租約應成功：rc={dr.returncode} {dr.stderr[-300:]}")
    task = re.search(r"task=(\S+)", dr.stdout).group(1)
    ctx.sched_track(task)
    sandbox_scope.revoke(sb.home)
    rd = run([PY, str(sb.root / "tools" / "openitems.py"), "--root", str(sb.root), "run-driver", oid, "--task", task], cwd=sb.root, env=ctl_env(sb), timeout=180)
    ctx.check(rd.returncode == sandbox_scope.RC_SIDEEFFECT_REFUSED, f"run-driver 應 rc {sandbox_scope.RC_SIDEEFFECT_REFUSED}：rc={rd.returncode} {rd.stderr[-300:]}")
    ctx.check(get_task(task) is None, "到點入口被拒後驅動器工作應自拆")
    ois = [x for x in refused_rows(sb) if x.get("site") == "openitems.run_driver"]
    ctx.check(bool(ois) and ois[-1].get("reason") == "sandbox_no_lease", f"痕跡應有 openitems.run_driver sandbox_no_lease：{refused_rows(sb)[-3:]}")
    ctx.evidence("alert／patrol_housekeeping 皆 sideeffect_refused（不 toast、不入佇列）；run-driver rc10、工作自拆。誠實劃界：toast 本身量不到")
