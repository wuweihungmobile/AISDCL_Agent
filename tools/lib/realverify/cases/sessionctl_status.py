# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""sessionctl_status 家族：RV-T1（status 名冊）、RV-T2（stop --window 身分驗證）、RV-T3（--pace 模型建議）。

不開任何互動視窗：T2 的「視窗」是真 `claude -p --input-format stream-json`（stdin 開著、零 token、命令列含沙盒 sid）。
"""  # noqa: E501

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timedelta

from ..sandbox import REPO, Sandbox
from . import CaseContext, case
from .sessionctl_park import (  # noqa: E501
    PY,
    axis,
    claude_procs,
    ctl,
    force_rmtree,
    install_tools,
    park_cleanup,
    ps,
    run,
    write_quota,
)

_NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _pace_env(sb: Sandbox) -> dict:
    e = sb.env()
    tmp = sb.root / "tmp"
    tmp.mkdir(exist_ok=True)
    e.update({"AUTOSDD_QUOTA_CACHE_DIR": str(sb.root / "qcache"), "TEMP": str(tmp), "TMP": str(tmp), "PYTHONDONTWRITEBYTECODE": "1"})  # noqa: E501
    return e


@case("RV-T3", "sessionctl_status", refs=("V7",))
def rv_t3(ctx: CaseContext) -> None:
    """`--pace` 末段模型建議：兩週軸（全模型 vs fable 專屬）依 ratio 差判「Fable 超前」／「全模型超前」／「平衡」，
    數字與 `--pace` 同源快取；`sessionctl advice` 與 `--pace` 同一結論。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    planner = str(REPO / "tools" / "session_resume_planner.py")
    ctlpy = str(REPO / "tools" / "sessionctl.py")

    def line(all_pct: float, scoped_pct: float) -> tuple[str, str]:
        write_quota(sb, [axis("five_hour", 20, 150), axis("seven_day", all_pct, 3.5 * 1440),
                         axis("seven_day_opus", scoped_pct, 3.5 * 1440, scope_model="fable")])
        r = run([PY, planner, "--pace", "--model", "fable"], cwd=sb.root, env=_pace_env(sb), timeout=120)  # noqa: E501
        ctx.check(r.returncode == 0, f"--pace rc={r.returncode} {r.stderr[-300:]}")
        got = [ln for ln in r.stdout.splitlines() if ln.startswith("模型建議：")]
        ctx.check(len(got) == 1, f"--pace 應恰有一行模型建議：{r.stdout[-400:]}")
        a = run([PY, ctlpy, "advice", "--family", "fable"], cwd=sb.root, env=_pace_env(sb), timeout=60)  # noqa: E501
        ctx.check(a.stdout.strip() == got[0], f"advice 與 --pace 不一致：{a.stdout!r} vs {got[0]!r}")  # noqa: E501
        return got[0], r.stdout

    ahead, _ = line(50, 80)  # ratio 1.0 vs 1.6：專屬軸超前
    ctx.check("Fable 超前" in ahead, ahead)
    behind, _ = line(80, 50)
    ctx.check("全模型超前" in behind, behind)
    bal, _ = line(50, 52)
    ctx.check("平衡" in bal, bal)
    ctx.evidence("RV-T3 Fable 超前／全模型超前／平衡 三態皆與 advice 子指令一致")


def _spawn_idle_claude(sb: Sandbox) -> subprocess.Popen:
    """真 claude -p，stdin 開著不寫（零 token），命令列含沙盒 sid。"""
    exe = shutil.which("claude")
    if not exe:
        from ..driver import EnvMissing
        raise EnvMissing("找不到 claude 執行檔")
    p = subprocess.Popen([exe, "-p", "--model", "haiku", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose", "--session-id", sb.sid],  # noqa: E501
                         cwd=str(sb.root), env=sb.env(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=_NOWIN)  # noqa: E501
    sb.procs.append(p)
    return p


def _created_iso(pid: int) -> str:
    rc, out = ps(f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CreationDate.ToUniversalTime().ToString('o')")  # noqa: E501
    return out.strip()


@case("RV-T2", "sessionctl_status", refs=("V6",))
def rv_t2(ctx: CaseContext) -> None:
    """`stop --window <sid>`：身分驗證通過才砍（命令列含完整 sid ∧ 痕跡 pid 與建立時刻吻合）。三變體：
    ①無痕跡 ⇒ 不砍；②痕跡 pid 不符 ⇒ 不砍；③痕跡吻合 ⇒ 砍樹、行程消失。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    p = _spawn_idle_claude(sb)
    time.sleep(4)
    try:
        ctx.check(p.poll() is None, f"閒置 claude 行程提早結束 rc={p.returncode}")
        procs = [x for x in claude_procs(sb.sid) if x["name"].lower() == "claude.exe"]
        ctx.check(bool(procs), "找不到命令列含沙盒 sid 的 claude 行程")
        pid = procs[0]["pid"]
        trace = sb.root / "traces" / "autosdd_session_switch.jsonl"
        trace.parent.mkdir(exist_ok=True)

        def alive() -> bool:
            return any(x["pid"] == pid for x in claude_procs(sb.sid))

        r1 = ctl(sb, "stop", "--window", sb.sid)
        ctx.check(r1.returncode == 1 and alive(), f"①無痕跡應不砍（rc 1、行程仍在）：rc={r1.returncode} {r1.stdout}{r1.stderr}")  # noqa: E501
        created = _created_iso(pid)
        rec = {"event": "session_switch_spawned", "sid": sb.sid, "at": created}
        trace.write_text(json.dumps({**rec, "pid": pid + 7}) + "\n", encoding="utf-8")
        r2 = ctl(sb, "stop", "--window", sb.sid)
        ctx.check(r2.returncode == 1 and alive(), f"②痕跡 pid 不符應不砍：rc={r2.returncode} {r2.stdout}{r2.stderr}")  # noqa: E501
        trace.write_text(json.dumps({**rec, "pid": pid}) + "\n", encoding="utf-8")
        r3 = ctl(sb, "stop", "--window", sb.sid)
        ctx.check(r3.returncode == 0 and f"已停 pid {pid}" in r3.stdout, f"③應砍：rc={r3.returncode} {r3.stdout}{r3.stderr}")  # noqa: E501
        ctx.check(bool(wait_gone(pid)), "③之後行程仍在")
        ctx.evidence(f"RV-T2 pid {pid}：無痕跡／pid 不符不砍；吻合才砍（taskkill /T /F）")
    finally:
        if os.name == "nt" and p.poll() is None:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True, creationflags=_NOWIN)  # noqa: E501
        time.sleep(1)
        force_rmtree(sb.root / ".git")
        force_rmtree(sb.root / "tools")


def wait_gone(pid: int, timeout_s: float = 15) -> bool:
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_s:
        if not any(x["pid"] == pid for x in claude_procs("")):
            return True
        time.sleep(1)
    return False


@case("RV-T1", "sessionctl_status", refs=("V1",), sched=True)
def rv_t1(ctx: CaseContext) -> None:
    """沙盒有真背景代理（haiku 子代理逐步 Read、主行程被砍＝meta 無 finished）＋真排程 ⇒ `status` 都列出來；
    排程的 NextRunTime 值由排程器回讀（D-4：status 唯讀零外呼、值由 `--verify-schtasks` 取證，兩者各自斷言）。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    with park_cleanup(sb):
        _t1_body(ctx, sb)


def _t1_body(ctx: CaseContext, sb: Sandbox) -> None:
    (sb.root / "a.txt").write_text("rv\n", encoding="utf-8")
    run_at = (datetime.now().astimezone() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:00")
    rb = ctx.sched_register("T1_" + sb.sid[:8], run_at, "-c pass")
    ctx.check(bool(rb["next_run_time"]), f"註冊後沒有 NextRunTime：{rb}")
    prompt = ("Use the Agent tool exactly once with description 'rv-t1-worker' and prompt: 'Call the Read tool on a.txt "  # noqa: E501
              "thirty separate times, one call per step, then reply done.' Do nothing else; wait for it.")  # noqa: E501
    r = ctx.run_claude(sb, prompt, timeout_s=40, extra_args=("--permission-mode", "acceptEdits"))
    ctx.check(r.timed_out, f"本案例要求主行程在子代理途中被砍（timeout 40s），實際 rc={r.rc} 已自然結束（子代理太快？）")  # noqa: E501
    st = ctl(sb, "status", "--session", sb.sid)
    out = st.stdout
    ctx.check(st.returncode == 0, f"status rc={st.returncode} {st.stderr[-200:]}")
    ctx.check("rv-t1-worker" in out, f"status 沒列出沙盒背景代理：\n{out[-800:]}")
    name = "AutoSDD_RV_T1_" + sb.sid[:8]
    ctx.check(name in out, f"status 沒列出沙盒排程 {name}：\n{out[-800:]}")
    v = run([PY, str(REPO / "tools" / "session_resume_planner.py"), "--verify-schtasks", "--task-name", name], cwd=sb.root, env=_pace_env(sb), timeout=90)  # noqa: E501
    ctx.check(v.returncode == 0 and re.search(r"\d{4}[-/]\d{2}[-/]\d{2}", v.stdout) is not None, f"--verify-schtasks 沒印 NextRunTime 值：rc={v.returncode} {v.stdout[-300:]}")  # noqa: E501
    ctx.evidence(f"RV-T1 status 列出代理 rv-t1-worker 與排程 {name}；NextRunTime={rb['next_run_time']}")  # noqa: E501
