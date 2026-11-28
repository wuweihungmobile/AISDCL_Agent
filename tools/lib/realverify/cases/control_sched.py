# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
# ruff: noqa: E501
"""control 家族 B：RV-CTL25（真 pythonw 重現 G-1）等需要沙盒哨兵／真排程／真行程的 WP-SW 案例。

沿用 sentinel 家族的「工具副本沙盒」（`install_tools`）；哨兵一律 `AutoSDD_Sentinel_<沙盒 sid>`，收尾經
`park_cleanup` 依完整沙盒 sid 精確拆除，絕不碰真實 `AutoSDD_Sentinel_*`（406454ea／4290bf58 殘骸＝證據）。
`pythonw` 載具：不傳 std handle（`close_fds`、不指定 stdin／stdout／stderr、`DETACHED_PROCESS`）⇒ 子行程
`sys.stderr is None`，與排程器起的行程同形。
"""

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

from ..driver import EnvMissing
from ..sandbox import REPO, Sandbox
from . import CaseContext, case
from .sentinel import _env, arm, grant_default, log_events, task_name
from .sessionctl_park import (  # noqa: F401
    PY,
    force_rmtree,
    get_task,
    install_tools,
    park_cleanup,
    seed_session,
)

OLD_ACCT, NEW_ACCT = "eaf5241f6fe2", "34cd3507237f"
_DETACHED = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)


def pythonw() -> str:
    exe = Path(PY).with_name("pythonw.exe")
    if not exe.is_file():
        raise EnvMissing(f"沒有 pythonw.exe（只在 Windows 的 venv 才有）：{exe}")
    return str(exe)


def run_nostd(argv: list[str], *, cwd: Path, env: dict, timeout: float = 240) -> int:
    """以「沒有 std handle」的方式跑行程並等它結束，回 rc（pythonw 的 `sys.stderr is None` 形狀）。"""
    proc = subprocess.Popen(argv, cwd=str(cwd), env=env, creationflags=_DETACHED, close_fds=True)  # noqa: S603
    try:
        return proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise


def stderr_is_none_probe(sb: Sandbox, env: dict) -> bool:
    """前提自證：同一種載具下 `sys.stderr` 真的是 None（不是 console 殘留）。"""
    out = sb.root / "tmp" / "stderr_probe.txt"
    out.parent.mkdir(exist_ok=True)
    code = f"import sys;open(r'{out}','w').write(str(sys.stderr is None)+','+str(sys.stdout is None))"
    run_nostd([pythonw(), "-c", code], cwd=sb.root, env=env, timeout=60)
    return out.read_text(encoding="utf-8").strip() == "True,True"


def write_old_account_world(sb: Sandbox) -> Path:
    """真實 halt 標記形狀（舊帳號 `eaf5241f6fe2`）＋快取新帳號 `34cd3507237f`、weekly 20%：tick 的判決會作廢舊標記。"""
    now = datetime.now().astimezone()
    traces = sb.home / "traces"
    traces.mkdir(parents=True, exist_ok=True)
    marker = traces / f"halt_{sb.sid}.json"
    marker.write_text(json.dumps({
        "sid": sb.sid, "band": "halt", "binding": "seven_day",
        "reset_at": (now + timedelta(days=3)).isoformat(), "at": (now - timedelta(hours=2)).isoformat(),
        "transcript": "<projects>/rv.jsonl", "resolved_source": "payload", "account": OLD_ACCT}), encoding="utf-8")
    qc = sb.root / "qcache"
    qc.mkdir(exist_ok=True)
    (qc / "autosdd_quota.json").write_text(json.dumps({
        "schema": "autosdd.quota/2", "source": "endpoint", "http_status": 200,
        "measured_at": now.isoformat(timespec="seconds"), "account_key": NEW_ACCT,
        "axes": [{"kind": "five_hour", "pct": 5.0, "resets_at": (now + timedelta(hours=4)).isoformat(timespec="seconds"), "via": "rv"},
                 {"kind": "seven_day", "pct": 20.0, "resets_at": (now + timedelta(days=4)).isoformat(timespec="seconds"), "via": "rv"}]}),
        encoding="utf-8")
    return marker


def trace_events(sb: Sandbox, name: str = "autosdd_session_switch.jsonl") -> list[dict]:
    p = sb.home / "traces" / name
    out = []
    if p.is_file():
        for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                out.append(json.loads(ln))
            except ValueError:
                pass
    return out


def sandbox_tick_argv(sb: Sandbox, plan: Path, *, name: str | None = None) -> list[str]:
    from .sessionctl_park import ensure_fake_claude  # noqa: PLC0415
    return [pythonw(), str(sb.root / "tools" / "session_resume_planner.py"), "--sentinel-tick", "--plan", str(plan),
            "--task-name", name or task_name(sb), "--claude", str(ensure_fake_claude(sb))]


@case("RV-CTL25", "control", refs=("E2E-CTL-25", "REQ-CTL-49", "REQ-CTL-51", "MU-CTL-50"), sched=True)
def rv_ctl25(ctx: CaseContext) -> None:
    """真 pythonw（無 std handle）重現 G-1：修後 tick 走完判決（account_switch／sentinel_decided／sentinel_rearmed、
    排程器 NextRunTime 非空、rc 0）；oracle＝沙盒內換回修前 `_stdio_utf8.py` 重跑 ⇒ rc 1、有 woken、無 decided。"""
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    grant_default(sb)
    env = _env(sb)
    with park_cleanup(sb):
        ctx.check(stderr_is_none_probe(sb, env), "前提不成立：這個載具下 pythonw 的 sys.stderr 不是 None")
        tp = seed_session(ctx, sb)
        plan = arm(ctx, sb, tp)
        # ── 修後
        write_old_account_world(sb)
        rc = run_nostd(sandbox_tick_argv(sb, plan), cwd=sb.root, env=env)
        ev = {e["event"] for e in log_events(sb)}
        sw = [e for e in trace_events(sb) if e.get("event") == "account_switch"]
        t = get_task(task_name(sb))
        ctx.check(rc == 0, f"修後 pythonw tick rc={rc}（應 0）；痕跡 {sorted(ev)}")
        ctx.check({"sentinel_woken", "sentinel_decided", "sentinel_rearmed"} <= ev, f"修後痕跡缺 woken／decided／rearmed：{sorted(ev)}")
        ctx.check(any(e.get("old") == OLD_ACCT and e.get("new") == NEW_ACCT for e in sw), f"缺 account_switch {OLD_ACCT}→{NEW_ACCT}：{sw}")
        ctx.check(t is not None and bool(t["next_run_time"]), f"修後排程器 NextRunTime 應非空：{t}")
        after_nrt = t["next_run_time"]
        # ── oracle：修前碼（git show 取 a7cba8c2 之前的 `_stdio_utf8.py`，沙盒內覆蓋）
        import subprocess as sp  # noqa: PLC0415
        old_src = sp.run(["git", "-C", str(REPO), "show", "a7cba8c2:tools/_stdio_utf8.py"], capture_output=True, check=True).stdout  # noqa: S603, S607
        (sb.root / "tools" / "_stdio_utf8.py").write_bytes(old_src)
        for f in sb.root.glob("tmp/autosdd_resume_log_*.jsonl"):
            f.unlink()
        for f in (sb.home / "traces").glob("acct_probe.json"):
            f.unlink()
        write_old_account_world(sb)
        rc0 = run_nostd(sandbox_tick_argv(sb, plan), cwd=sb.root, env=env)
        ev0 = {e["event"] for e in log_events(sb)}
        ctx.check(rc0 == 1, f"oracle（修前碼）rc={rc0}（應 1，重現 406454ea 10:21:52）；痕跡 {sorted(ev0)}")
        ctx.check("sentinel_woken" in ev0 and "sentinel_decided" not in ev0, f"oracle 應有 woken 無 decided：{sorted(ev0)}")
        ctx.evidence(f"RV-CTL25 pythonw stderr=None 前提成立；修後 rc=0 痕跡 {sorted(ev)} NextRunTime={after_nrt}；"
                     f"oracle rc={rc0} 痕跡 {sorted(ev0)}（與 ARCH-Q34 G-1 證據 2 同形）")
        time.sleep(0)
