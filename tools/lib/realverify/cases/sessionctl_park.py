# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""sessionctl_park 家族：RV-K1～K7（park 的 armed／fire／跳過／done／cancel／why／at／Stop 推回）。

本檔同時是 WP-4 其餘三個家族（quota_rush／sessionctl_status／sentinel）共用的私有 helper 家
（`from .sessionctl_park import …`）；helper 不登記案例。

🔴 「工具副本沙盒」（WHY）：被測的 `tools/sessionctl.py`、`tools/session_resume_planner.py` 以 `__file__`
推導 `_REPO`／`_REPO_ROOT`，並拿它當 spawn 的 cwd、git 工作樹前置（`handoff.spawn_preflight`：工作樹必須乾淨）
與 `-r` 找逐字稿的專案 slug。直接對 repo 跑＝工作樹永遠是髒的（多人並行）而 park 前置必拒，且續跑
`claude -p -r <沙盒 sid>` 因 cwd 是 repo 而找不到沙盒 session。所以把 repo `tools/`（不含 tests／probe）
**逐檔複製**進沙盒、在沙盒內 `git commit`，再跑沙盒內的那份入口——程式碼逐位元相同、只是落點不同。
"""  # noqa: E501

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from lib import sandbox_scope

from .. import leases, sched
from ..driver import EnvMissing
from ..sandbox import LOCAL_EXCLUDES, REPO, Sandbox
from . import CaseContext, case

PY = str(REPO / ".venv" / "Scripts" / "python.exe") if (REPO / ".venv" / "Scripts" / "python.exe").is_file() else sys.executable  # noqa: E501
_NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_COPY_IGNORE = shutil.ignore_patterns("tests", "act", "git-hooks", "__pycache__", ".pytest_cache", ".ruff_cache", "*.pyc")  # noqa: E501
# 由 `sandbox.LOCAL_EXCLUDES`（身分檔、7 居所、bin、替身設定）推得，再加本家族案例自己的暫存樣式（D-23）  # noqa: E501
_EXCLUDES = "\n".join([*LOCAL_EXCLUDES, "debug_*.log", "hook_events.jsonl", "__pycache__/", "*.pyc",
                       ".claude/settings.local.json", "stdin_*.txt", "tmp/"]) + "\n"


# ───────────────────────────────────────────────────────────────── 通用 helper
def ps(script: str, timeout: int = 60) -> tuple[int, str]:
    return sched._ps(script, timeout)


def run(argv: list[str], *, cwd: Path, env: dict, timeout: int = 180) -> subprocess.CompletedProcess:  # noqa: E501
    return subprocess.run(argv, cwd=str(cwd), env=env, capture_output=True, timeout=timeout,  # noqa: S603
                          creationflags=_NOWIN, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)  # noqa: E501


def get_task(name: str) -> dict | None:
    """任意名稱的排程回讀（`sched.read_back` 強制 RV 前綴，park／哨兵的名字不是）；不存在回 None。"""  # noqa: E501
    rc, out = ps(
        f"$t = Get-ScheduledTask -TaskName '{name}' -ErrorAction SilentlyContinue; if (-not $t) {{ exit 0 }}; "  # noqa: E501
        "$i = $t | Get-ScheduledTaskInfo; $a = $t.Actions[0]; "
        "[pscustomobject]@{state=[string]$t.State; next_run_time=if($i.NextRunTime){$i.NextRunTime.ToString('o')}else{''}; "  # noqa: E501
        "logon_type=[string]$t.Principal.LogonType; execute=$a.Execute; arguments=$a.Arguments; "
        "workdir=$a.WorkingDirectory} | ConvertTo-Json -Compress")
    return json.loads(out) if rc == 0 and out.startswith("{") else None


def tasks_like(pattern: str) -> list[str]:
    rc, out = ps(f"Get-ScheduledTask | Where-Object TaskName -like '{pattern}' | Select-Object -ExpandProperty TaskName")  # noqa: E501
    return [x.strip() for x in out.splitlines() if x.strip()] if rc == 0 else []


def remove_tasks_like(pattern: str) -> list[str]:
    """薄殼（REQ-SE-34）：依精確前綴（含沙盒 sid）撤排程——排程撤銷全套件唯一家是 `leases.revoke_sched_like`；
    pattern 必須帶完整 sid 或 sid8，絕不接受寬泛樣式。"""  # noqa: E501
    return leases.revoke_sched_like(pattern)


def claude_procs(sid: str) -> list[dict]:
    """命令列含完整沙盒 sid 的 claude 行程（`{pid, cmd, name}`）。"""
    rc, out = ps("Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'claude*' } | "
                 "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress")
    if rc != 0 or not out:
        return []
    data = json.loads(out)
    rows = [data] if isinstance(data, dict) else data
    return [{"pid": int(r["ProcessId"]), "name": r["Name"], "cmd": r["CommandLine"] or ""}
            for r in rows if sid in (r["CommandLine"] or "")]


def kill_verified(sid: str, *, interactive_only: bool = True) -> list[int]:
    """依 pid＋命令列含沙盒 sid 驗身分後砍行程樹；驗不到不砍。回被砍的 pid。"""
    if os.name != "nt":
        raise EnvMissing("kill_verified 只在 Windows 可跑")
    killed = []
    for p in claude_procs(sid):
        if p["name"].lower() != "claude.exe" or sid not in p["cmd"]:
            continue
        if interactive_only and re.search(r"(^|\s)-p(\s|$)", p["cmd"]):
            continue
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(p["pid"])], capture_output=True, creationflags=_NOWIN)  # noqa: E501
        killed.append(p["pid"])
    return killed


def install_tools(sb: Sandbox) -> None:
    """工具副本沙盒（見模組 docstring）：複製 tools／unattended 姿態檔，commit，之後工作樹必須乾淨。"""  # noqa: E501
    shutil.copytree(REPO / "tools", sb.root / "tools", ignore=_COPY_IGNORE)
    shutil.copytree(REPO / ".claude" / "hooks", sb.root / ".claude" / "hooks", ignore=_COPY_IGNORE)  # planner import 需要  # noqa: E501
    shutil.copy2(REPO / ".claude" / "settings.unattended.json", sb.root / ".claude" / "settings.unattended.json")  # noqa: E501
    ex = sb.root / ".git" / "info" / "exclude"
    ex.write_text(ex.read_text(encoding="utf-8", errors="replace") + "\n" + _EXCLUDES, encoding="utf-8")  # noqa: E501
    for args in (["add", "-A"], ["commit", "-q", "-m", "rv sandbox baseline"]):
        subprocess.run(["git", *args], cwd=str(sb.root), check=True, capture_output=True, creationflags=_NOWIN)  # noqa: E501


def tree_clean(sb: Sandbox) -> str:
    r = subprocess.run(["git", "status", "--short"], cwd=str(sb.root), capture_output=True, creationflags=_NOWIN, encoding="utf-8")  # noqa: E501
    return r.stdout.strip()


def ctl_env(sb: Sandbox, *, arm_sentinel: bool = False, extra: dict | None = None) -> dict:
    """沙盒一律帶 `AUTOSDD_SENTINEL_OFF=1`（D-25：撤除舊的無條件 pop）；需要真武裝沙盒哨兵的案例顯式
    `arm_sentinel=True`，且呼叫點上方三行內必須有 `# WHY` 註解（AT-SE-18 AST 鎖）。居所一律在沙盒家目錄下
    （`real_traces` 已撤，REQ-SE-23）。"""  # noqa: E501
    e = sb.env()
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    if arm_sentinel:
        e.pop("AUTOSDD_SENTINEL_OFF", None)
    e.update(extra or {})
    return e


_NO_REGISTER = ("--done", "--cancel", "--status")


def ensure_fake_claude(sb: Sandbox) -> Path:
    """沙盒的假 `claude`（`<家>/bin/claude.exe`，模式 `fail`）；每個沙盒只編一次。"""
    from .. import fakeclaude  # noqa: PLC0415
    exe = sb.home / fakeclaude.EXE_REL
    if not exe.is_file():
        fakeclaude.build(sb.home)
        fakeclaude.configure(sb.home, "fail")
    return exe


def ctl(sb: Sandbox, *args: str, extra: dict | None = None, timeout: int = 180, lease_min: int = sandbox_scope.LEASE_MAX) -> subprocess.CompletedProcess:  # noqa: E501
    """跑沙盒內的 `sessionctl.py`。會**登記 park 排程**的呼叫（`park` 且非 done／cancel／status）先授與預設
    租約並帶 `--claude <沙盒假 claude>`：沙盒目標預設拒絕（L1），到點 job 的每次 spawn 嘗試都只准打替身
    （D-14／D-18）——案例不得靠真 `claude` 通過。"""  # noqa: E501
    argv = list(args)
    if argv[:1] == ["park"] and not any(a in argv for a in _NO_REGISTER) and "--claude" not in argv:
        now = datetime.now().astimezone()
        sandbox_scope.grant(sb.home, until=now + timedelta(minutes=lease_min), now=now, max_minutes=lease_min)  # noqa: E501
        argv += ["--claude", str(ensure_fake_claude(sb))]
    return run([PY, str(sb.root / "tools" / "sessionctl.py"), *argv], cwd=sb.root,
               env=ctl_env(sb, extra=extra), timeout=timeout)


def write_quota(sb: Sandbox, axes: list[dict]) -> None:
    """沙盒專屬額度快取（`AUTOSDD_QUOTA_CACHE_DIR` 指到這裡；絕不碰主控的真快取）。"""
    now = datetime.now().astimezone()
    d = sb.root / "qcache"
    d.mkdir(exist_ok=True)
    body = {"schema": "autosdd.quota/2", "source": "endpoint", "http_status": 200,
            "measured_at": now.isoformat(timespec="seconds"), "axes": axes}
    (d / "autosdd_quota.json").write_text(json.dumps(body), encoding="utf-8")


def axis(kind: str, pct: float, minutes_left: float, scope_model: str | None = None) -> dict:
    at = datetime.now().astimezone() + timedelta(minutes=minutes_left)
    a = {"kind": kind, "pct": pct, "resets_at": at.isoformat(timespec="seconds"), "via": "rv"}
    if scope_model:
        a["scope_model"] = scope_model
    return a


def transcript_path(sb: Sandbox) -> Path:
    from ..transcript import find_transcript
    p = find_transcript(sb.sid)
    if p is None:
        raise FileNotFoundError(f"沙盒 sid {sb.sid} 沒有逐字稿")
    return p


def age_transcript(path: Path, seconds: float) -> int:
    """把沙盒逐字稿每筆 `timestamp` 往前推（只改沙盒自己的逐字稿；`live_driver`／閒置判準看對話記錄時間戳）。"""  # noqa: E501
    n = 0
    out = []
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            d = json.loads(ln)
        except ValueError:
            out.append(ln)
            continue
        ts = d.get("timestamp") if isinstance(d, dict) else None
        if isinstance(ts, str):
            t = datetime.fromisoformat(ts.replace("Z", "+00:00")) - timedelta(seconds=seconds)
            d["timestamp"] = t.isoformat().replace("+00:00", "Z") if ts.endswith("Z") else t.isoformat()  # noqa: E501
            n += 1
        out.append(json.dumps(d, ensure_ascii=False))
    path.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    return n


def seed_session(ctx: CaseContext, sb: Sandbox) -> Path:
    """真 `claude -p` 建沙盒 session，回逐字稿路徑。"""
    r = ctx.run_claude(sb, "Reply with exactly: ok")
    ctx.check(r.rc == 0 and not r.timed_out, f"沙盒 claude -p rc={r.rc} {r.stderr[:200]}")
    return transcript_path(sb)


def make_package(ctx: CaseContext, sb: Sandbox) -> Path:
    """`handoff --build` ＋ 填滿主控層（機械層是真的）；回交接包路徑（真目錄，檔名以沙盒 sid 開頭）。"""  # noqa: E501
    r = ctl(sb, "handoff", "--build", "--session-id", sb.sid)
    ctx.check(r.returncode == 0, f"handoff --build rc={r.returncode} {r.stderr[:300]}")
    pkg = Path(r.stdout.strip().splitlines()[-1])
    ctx.check(pkg.is_file() and pkg.name.startswith(sb.sid), f"交接包路徑不合：{pkg}")
    text = re.sub(r"TODO:[^\n]*", "realverify 沙盒案例，無實際工作。", pkg.read_text(encoding="utf-8"))  # noqa: E501
    pkg.write_text(text, encoding="utf-8", newline="\n")
    return pkg


def iso_in(seconds: float) -> str:
    return (datetime.now().astimezone() + timedelta(seconds=seconds)).isoformat(timespec="seconds")


def read_marker(sid: str, base: Path) -> dict | None:
    p = base / "park" / f"{sid}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


@contextlib.contextmanager
def park_cleanup(sb: Sandbox):
    """finally：依沙盒 sid 精確撤 park 排程（薄殼，委派 `leases.revoke_sched_like`）、收視窗；居所都在沙盒
    家目錄下，隨沙盒一起刪（不再碰真 `~/.autosdd`，REQ-SE-23／34）。"""  # noqa: E501
    try:
        yield
    finally:
        sid8 = sb.sid[:8]
        remove_tasks_like(f"AutoSDD_HandoffSpawn_{sid8}_*")
        remove_tasks_like(f"AutoSDD_Sentinel_{sb.sid}")
        kill_verified(sb.sid)
        force_rmtree(sb.root / ".git")  # git 物件檔唯讀：核心的 rmtree(ignore_errors) 刪不掉，會留殘骸  # noqa: E501
        force_rmtree(sb.root / "tools")


def force_rmtree(path: Path) -> None:
    import os
    import stat

    def _onerr(func, p, _exc):
        os.chmod(p, stat.S_IWRITE)
        func(p)

    if path.exists():
        shutil.rmtree(path, onerror=_onerr)


def park_arm(ctx: CaseContext, sb: Sandbox, *, lead_s: float = 100, why: str = "realverify 案例：沙盒續航", age_s: float = 0) -> tuple[Path, dict]:  # noqa: E501
    """建 session＋交接包＋`park --at`；回 (交接包, 標記)。工作樹必須乾淨（否則前置必拒，直接 fail 並列出）。
    `age_s`＞0：把沙盒逐字稿時間戳往前推（讓「到點時沒人在動」成立）。"""  # noqa: E501
    tp = seed_session(ctx, sb)
    if age_s:
        age_transcript(tp, age_s)
    pkg = make_package(ctx, sb)
    dirty = tree_clean(sb)
    ctx.check(not dirty, f"沙盒工作樹不乾淨，park 前置會拒：{dirty[:200]}")
    r = ctl(sb, "park", "--session-id", sb.sid, "--at", iso_in(lead_s), "--why", why, "--pkg", str(pkg))  # noqa: E501
    ctx.check(r.returncode == 0, f"park rc={r.returncode} stdout={r.stdout[-300:]} stderr={r.stderr[-400:]}")  # noqa: E501
    base = sb.home / "traces"
    mk = read_marker(sb.sid, base)
    ctx.check(mk is not None and mk["status"] == "armed", f"沒有 armed 標記：{mk}")
    ctx.check("PARK_VERDICT=armed" in r.stdout, f"stdout 缺 PARK_VERDICT=armed：{r.stdout[-300:]}")
    return pkg, mk


def check_armed_task(ctx: CaseContext, mk: dict) -> dict:
    label = mk["jobs"][0]["label"]
    t = get_task(label)
    ctx.check(t is not None and bool(t["next_run_time"]), f"排程器查不到 {label} 或沒有 NextRunTime：{t}")  # noqa: E501
    ctx.check(t["logon_type"] == "Interactive", f"Principal.LogonType={t['logon_type']}（要 Interactive）")  # noqa: E501
    ctx.evidence(f"{label} NextRunTime={t['next_run_time']} LogonType={t['logon_type']} workdir={t.get('workdir')}")  # noqa: E501
    return t


def wait_until(pred, timeout_s: float, step: float = 3.0):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_s:
        v = pred()
        if v:
            return v
        time.sleep(step)
    return None


def trace_lines(base: Path, name: str, needle: str) -> list[dict]:
    p = base / name
    if not p.is_file():
        return []
    out = []
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if needle in ln:
            with contextlib.suppress(ValueError):
                out.append(json.loads(ln))
    return out


# ───────────────────────────────────────────────────────────────────── 案例
@case("RV-K1", "sessionctl_park", refs=("V-PK2", "DEF-200-594"), sched=True)
def rv_k1(ctx: CaseContext) -> None:
    """真 schtasks `park --at`：NextRunTime 值、Principal＝Interactive、Action 命令列（pythonw、`--fire`、
    沙盒 sid、交接包路徑、WorkingDirectory＝沙盒）逐項回讀；cancel 後查不到。

    🔴 劃界（主控 2026-11-18 規定）：新目錄的互動 claude 會卡 folder trust 對話框、且禁止再開窗，
    所以「到點真的開視窗／新逐字稿／cwd」不在本案例（改由 2026-11-16 真機覆蓋＋掌舵者目視）；
    到點行為的另一半（跳過判準）由 RV-K2 真排程觸發驗到。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    with park_cleanup(sb):
        pkg, mk = park_arm(ctx, sb, age_s=7200)
        t = check_armed_task(ctx, mk)
        label = mk["jobs"][0]["label"]
        ctx.check(Path(t["workdir"]).resolve() == sb.root.resolve(), f"job WorkingDirectory={t['workdir']} 不是沙盒根")  # noqa: E501
        args = t["arguments"]
        for needle, why in (("--fire", "job 本體旗標"), (f"--session-id\" \"{sb.sid}", "沙盒 sid"),  # noqa: E501
                            (str(pkg), "交接包路徑"), (label, "job 名")):
            ctx.check(needle in args, f"排程 Action 命令列缺{why}：{args[:300]}")
        ctx.check(str(sb.root / "tools" / "sessionctl.py") in args, "Action 沒指向沙盒內的 sessionctl.py")  # noqa: E501
        ctx.check(Path(t["execute"]).name.lower() == "pythonw.exe", f"載具不是 pythonw：{t['execute']}")  # noqa: E501
        # 撤銷：排程不留（cancel 之後 Get-ScheduledTask 查不到）
        c = ctl(sb, "park", "--cancel", "--session-id", sb.sid)
        ctx.check(c.returncode == 0 and get_task(label) is None, f"cancel 後仍查得到排程 rc={c.returncode}")  # noqa: E501
        ctx.check(not claude_procs(sb.sid), "不該有任何含沙盒 sid 的 claude 行程（本案例不開視窗）")
        ctx.evidence(f"RV-K1 Action 命令列含 --fire／sid／pkg／job 名；execute={Path(t['execute']).name}")  # noqa: E501
        ctx.notes.append("到點真的開出互動視窗／新逐字稿／cwd＝受 folder trust 限制且掌舵者禁止開窗，改由 2026-11-16 真機（f2260ce7→ff1000ed）逐字稿覆蓋；掌舵者目視（非阻塞）")  # noqa: E501


@case("RV-K2", "sessionctl_park", refs=("V-PK3",), sched=True)
def rv_k2(ctx: CaseContext) -> None:
    """到點前沙盒 session 有人在動（真 `claude -p -r` 寫新對話記錄）⇒ job 跳過（live_driver）、不 spawn、自拆。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    with park_cleanup(sb):
        seed_session(ctx, sb)
        age_transcript(transcript_path(sb), 7200)  # 先老化：證明「跳過」是下一句話造成的、不是本來就老  # noqa: E501
        pkg = make_package(ctx, sb)
        r = ctl(sb, "park", "--session-id", sb.sid, "--at", iso_in(100), "--why", "realverify K2 有人在動", "--pkg", str(pkg))  # noqa: E501
        ctx.check(r.returncode == 0, f"park rc={r.returncode} {r.stderr[-300:]}")
        mk = read_marker(sb.sid, sb.home / "traces")
        label = mk["jobs"][0]["label"]
        r2 = ctx.run_claude(sb, "Reply with exactly: still here")
        ctx.check(r2.rc == 0, f"到點前的 -r 呼叫 rc={r2.rc}")
        ctx.check(get_task(label) is not None, "到點前排程不該已消失")

        def done():
            return get_task(label) is None and (read_marker(sb.sid, sb.home / "traces") or {}).get("status") != "armed"  # noqa: E501

        ctx.check(bool(wait_until(done, 330, 3.0)), "到點後 job 沒自拆")
        mk2 = read_marker(sb.sid, sb.home / "traces")
        skips = [r for r in trace_lines(sb.home / "traces", "autosdd_session_switch.jsonl", sb.sid) if r.get("event") == "handoff_spawn_skipped"]  # noqa: E501
        ctx.check(any(s.get("reason") == "live_driver" for s in skips), f"痕跡沒有 handoff_spawn_skipped reason=live_driver：{skips}")  # noqa: E501
        ctx.check(mk2["status"] == "skipped", f"標記應為 skipped：{mk2['status']}")
        ctx.check(not claude_procs(sb.sid), "跳過案例不該開出任何視窗")
        ctx.evidence(f"RV-K2 skip={skips[0].get('driver_kind')}@{skips[0].get('driver_at')} 標記={mk2['status']}")  # noqa: E501


@case("RV-K3", "sessionctl_park", refs=())
def rv_k3(ctx: CaseContext) -> None:
    """`park --done --why`：寫 DONE 標記（armed、有效期內）；缺 --why ⇒ rc 2、不寫標記（反向）。"""
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    with park_cleanup(sb):
        bad = ctl(sb, "park", "--done", "--session-id", sb.sid)
        ctx.check(bad.returncode == 2, f"缺 --why 應 rc 2，實得 {bad.returncode}")
        ctx.check(read_marker(sb.sid, sb.root / "traces") is None, "缺 --why 不該寫標記")
        r = ctl(sb, "park", "--done", "--session-id", sb.sid, "--why", "realverify K3 無剩餘工作")
        ctx.check(r.returncode == 0, f"--done rc={r.returncode} {r.stderr[-200:]}")
        mk = read_marker(sb.sid, sb.root / "traces")
        ctx.check(mk and mk["route"] == "DONE" and mk["status"] == "armed" and mk["jobs"] == [], f"DONE 標記不合：{mk}")  # noqa: E501
        ctx.check(datetime.fromisoformat(mk["valid_until"]) > datetime.now().astimezone(), "valid_until 已過期")  # noqa: E501
        ctx.check(not tasks_like(f"AutoSDD_HandoffSpawn_{sb.sid[:8]}_*"), "--done 不該登記排程")
        st = ctl(sb, "park", "--status", "--session-id", sb.sid)
        ctx.check("route=DONE status=armed" in st.stdout, f"--status 輸出不符：{st.stdout}")
        ctx.evidence(f"RV-K3 valid_until={mk['valid_until']}")


@case("RV-K4", "sessionctl_park", refs=(), sched=True)
def rv_k4(ctx: CaseContext) -> None:
    """`park --cancel`：armed 之後撤銷 ⇒ 排程器查不到該 job、標記 cancelled；再 --status 顯示 cancelled。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    with park_cleanup(sb):
        _pkg, mk = park_arm(ctx, sb, lead_s=300)
        label = mk["jobs"][0]["label"]
        check_armed_task(ctx, mk)
        r = ctl(sb, "park", "--cancel", "--session-id", sb.sid)
        ctx.check(r.returncode == 0 and "park 已取消" in r.stdout, f"--cancel rc={r.returncode} {r.stdout}{r.stderr}")  # noqa: E501
        ctx.check(get_task(label) is None, "cancel 後 Get-ScheduledTask 仍查得到")
        ctx.check(read_marker(sb.sid, sb.root / "traces")["status"] == "cancelled", "標記應為 cancelled")  # noqa: E501
        st = ctl(sb, "park", "--status", "--session-id", sb.sid)
        ctx.check("status=cancelled" in st.stdout, f"--status：{st.stdout}")
        again = ctl(sb, "park", "--status", "--verify", "--session-id", sb.sid)
        ctx.check(again.returncode == 0, "--status --verify rc 非 0")


@case("RV-K5", "sessionctl_park", refs=(), sched=True)
def rv_k5(ctx: CaseContext) -> None:
    """`park --why`（無 --at）：額度未達準備門檻、但主控判斷放不下 ⇒ reset 取短窗觀測值；不帶 --why ⇒ rc 4（反向）。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    with park_cleanup(sb):
        seed_session(ctx, sb)
        pkg = make_package(ctx, sb)
        write_quota(sb, [axis("five_hour", 30, 120)])
        no = ctl(sb, "park", "--session-id", sb.sid, "--pkg", str(pkg))
        ctx.check(no.returncode == 4, f"未達門檻且無 --why 應 rc 4，實得 {no.returncode} {no.stderr[-200:]}")  # noqa: E501
        ctx.check(read_marker(sb.sid, sb.root / "traces") is None and not tasks_like(f"AutoSDD_HandoffSpawn_{sb.sid[:8]}_*"), "拒絕時不該留標記／排程")  # noqa: E501
        r = ctl(sb, "park", "--session-id", sb.sid, "--pkg", str(pkg), "--why", "realverify K5 下一棒放不下")  # noqa: E501
        ctx.check(r.returncode == 0, f"--why rc={r.returncode} {r.stderr[-300:]}")
        mk = read_marker(sb.sid, sb.root / "traces")
        ctx.check(mk["axis"]["kind"] == "five_hour" and mk["status"] == "armed", f"標記不合：{mk}")
        reset = datetime.fromisoformat(mk["reset_at"])
        ctx.check(abs((reset - datetime.now().astimezone()).total_seconds() - 7200) < 400, f"reset_at 不是短窗觀測值（約 +120 分）：{mk['reset_at']}")  # noqa: E501
        t = check_armed_task(ctx, mk)
        ctx.evidence(f"RV-K5 reset_at={mk['reset_at']} fire_at={mk['fire_at']} NextRunTime={t['next_run_time']}")  # noqa: E501
        ctl(sb, "park", "--cancel", "--session-id", sb.sid)


@case("RV-K6", "sessionctl_park", refs=(), sched=True)
def rv_k6(ctx: CaseContext) -> None:
    """`park --at`：註冊值與排程器 NextRunTime 一致；過去時刻／缺 --why ⇒ rc 2（反向）；再 park 取代舊排程不雙掛。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    with park_cleanup(sb):
        pkg, mk = park_arm(ctx, sb, lead_s=600)
        t = check_armed_task(ctx, mk)
        fire = datetime.fromisoformat(mk["fire_at"])
        nrt = datetime.fromisoformat(t["next_run_time"])
        ctx.check(abs((nrt - fire).total_seconds()) < 60, f"NextRunTime {nrt} 與標記 fire_at {fire} 不一致")  # noqa: E501
        past = ctl(sb, "park", "--session-id", sb.sid, "--pkg", str(pkg), "--at", iso_in(-60), "--why", "realverify K6 過去時刻")  # noqa: E501
        ctx.check(past.returncode == 2, f"過去時刻應 rc 2，實得 {past.returncode}")
        nowhy = ctl(sb, "park", "--session-id", sb.sid, "--pkg", str(pkg), "--at", iso_in(900))
        ctx.check(nowhy.returncode == 2, f"--at 缺 --why 應 rc 2，實得 {nowhy.returncode}")
        r = ctl(sb, "park", "--session-id", sb.sid, "--pkg", str(pkg), "--at", iso_in(1200), "--why", "realverify K6 改期")  # noqa: E501
        ctx.check(r.returncode == 0, f"改期 rc={r.returncode} {r.stderr[-300:]}")
        left = tasks_like(f"AutoSDD_HandoffSpawn_{sb.sid[:8]}_*")
        ctx.check(len(left) == 1 and left[0] != mk["jobs"][0]["label"], f"改期後應只剩新排程：{left}")  # noqa: E501
        ctx.evidence(f"RV-K6 NextRunTime={t['next_run_time']} 改期後={left}")
        ctl(sb, "park", "--cancel", "--session-id", sb.sid)


@case("RV-K7", "sessionctl_park", refs=("V-PK4", "DEF-200-596"))
def rv_k7(ctx: CaseContext) -> None:
    """真 `claude -p` ＋ repo 的 sessionctl_guard Stop hook：沙盒額度快取短窗 97pp 且無續航憑證 ⇒ 逐字稿
    `hook_blocking_error` 內容含 `sessionctl.py park`；第二次 Stop（stop_hook_active）放行＝只推回一次。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    sb.add_repo_hook("Stop", ".claude/hooks/sessionctl_guard.py")
    write_quota(sb, [axis("five_hour", 97, 60)])
    r = ctx.run_claude(sb, "Reply with exactly: ok", env_extra={
        "AUTOSDD_QUOTA_CACHE_DIR": str(sb.root / "qcache"), "AUTOSDD_SESSION_SWITCH_MODE": "auto"})
    ctx.check(r.rc == 0 and not r.timed_out, f"claude -p rc={r.rc} {r.stderr[:200]}")
    tr = ctx.transcript(sb)
    be = tr.hook_blocking_errors("Stop", "sessionctl.py park")
    ctx.check(bool(be), "逐字稿沒有含 `sessionctl.py park` 的 Stop hook_blocking_error（額度停工守衛沒推回）")  # noqa: E501
    ctx.check(len(tr.hook_blocking_errors("Stop")) == 1, "Stop 推回不只一次（第二次應放行）")
    ctx.evidence(f"RV-K7 {tr.coords(be[0])} 推回含 park 指路；僅 1 次")
