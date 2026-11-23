# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""sideeffect 家族共用 helper（RealVerify_SideEffect_Isolation TCS §4 的真機 E2E；不登記案例）。

載具：沿用 `sessionctl_park` 的「工具副本沙盒」（`install_tools`）；到點 job 的每一次 spawn 嘗試都只打
`<家>/bin/claude.exe` 假替身（DES D-14）；逐字稿以**合成**方式落到沙盒 slug（事故逐字稿 T57 已不在本機，
且 TCS 鐵令「不得燒真額度」——不跑真 `claude -p` 種 session）。
判準全是真的：真 schtasks、真行程（pythonw 跑沙盒內 `sessionctl.py park --fire`）、真痕跡檔、真逐字稿。
"""
from __future__ import annotations

import functools
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from lib import sandbox_scope

from .. import fakeclaude, leases, sched
from ..sandbox import REPO, Sandbox, projects_dir, slug_of
from . import CaseContext
from .sessionctl_park import (
    PY,
    ctl_env,
    force_rmtree,
    get_task,
    install_tools,
    iso_in,
    make_package,
    ps,
    run,
    trace_lines,
    tree_clean,
)

NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
SWITCH_TRACE = "autosdd_session_switch.jsonl"
CTL_PREFIX = "AutoSDD_RV_ctl_"  # 主人行程與案例交換控制檔的 %TEMP% 目錄（不含沙盒前綴；先登記後建）


# ───────────────────────────────────────────────────────────── 時間／等待
def now() -> datetime:
    return datetime.now().astimezone()


def iso_at(when: datetime) -> str:
    return when.isoformat(timespec="seconds")


def wait_until_time(when: datetime, extra_s: float = 0.0, step: float = 3.0) -> None:
    """睡到 `when + extra_s`（每步檢查，最長不超過 3 步）。"""
    end = when + timedelta(seconds=extra_s)
    while now() < end:
        time.sleep(min(step, max(0.2, (end - now()).total_seconds())))


# ───────────────────────────────────────────────────────────── 合成逐字稿（T57 形狀）
def synth_transcript(sb: Sandbox, *, ctx_tokens: int | None, age_s: float, lines: int = 27) -> Path:
    """寫 `~/.claude/projects/<沙盒 slug>/<sid>.jsonl`：`lines` 行 user／assistant 交錯、時間戳往前推
    `age_s`（讓快取冷、「有人在動」判準不成立）；`ctx_tokens=None` ⇒ 全部 assistant 記錄不帶 usage
    （上下文量不到 ⇒ F4 判 FRESH，TCS E2E-SE-01(e3)）。只動沙盒自己的 slug 目錄（已由 `reserve_home` 登記）。"""
    proj = projects_dir() / slug_of(sb.root)
    proj.mkdir(parents=True, exist_ok=True)
    base = datetime.now(UTC) - timedelta(seconds=age_s + lines)
    rows = []
    for i in range(lines):
        stamp = (base + timedelta(seconds=i)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        common = {"sessionId": sb.sid, "cwd": str(sb.root), "timestamp": stamp, "uuid": str(uuid.uuid4())}
        if i % 2 == 0:
            rows.append({**common, "type": "user", "message": {"role": "user", "content": f"rv sideeffect L{i + 1}"}})
            continue
        msg = {"id": f"msg_rvse_{i:04d}", "role": "assistant", "model": "claude-haiku-4-5",
               "content": [{"type": "text", "text": f"ok L{i + 1}"}]}
        if ctx_tokens is not None:
            msg["usage"] = {"input_tokens": 1, "cache_read_input_tokens": ctx_tokens - 1,
                            "cache_creation_input_tokens": 0, "output_tokens": 5}
        rows.append({**common, "type": "assistant", "message": msg})
    path = proj / f"{sb.sid}.jsonl"
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8", newline="\n")
    return path


def endurance_env():
    """lazy 匯入 ndurance_env（它頂層用裸名匯入 platform_utils，需要 	ools/lib 在 sys.path）。"""
    import sys  # noqa: PLC0415
    lib = str(REPO / "tools" / "lib")
    if lib not in sys.path:
        sys.path.insert(0, lib)
    import endurance_env as env  # noqa: PLC0415
    return env


def pick_resume_ctx(env: dict | None = None) -> tuple[int, str]:
    """依真產品選路 `park.fire_route` 預算：由 200,000 起往小試，取第一個判 RESUME 的上下文（快取已冷）。
    回 (上下文, 理由)；試到 5,000 仍非 RESUME ⇒ AssertionError（載具問題，不是被測物問題）。"""
    from lib.sessionctl import park  # noqa: PLC0415 — lazy：只在要預算選路時才需要產品模組
    held = 200_000
    while held >= 5_000:
        route, why = park.fire_route(held, True, env if env is not None else {})
        if route == park.FIRE_RESUME:
            return held, why
        held //= 2
    raise AssertionError("F4 預算不出 RESUME 的上下文（fire_route 對 5,000 以上都判 FRESH）")


# ───────────────────────────────────────────────────────────── 沙盒＋假 claude＋交接包＋park
@dataclass
class Armed:
    sb: Sandbox
    exe: Path
    pkg: Path
    label: str
    fire_at: datetime
    marker: dict
    projdir: Path


def new_box(ctx: CaseContext, *, mode: str = "fail", sleep: int = 60, tools: bool = True) -> tuple[Sandbox, Path]:
    """沙盒（先帳後建、身分檔第一動作）＋（可選）工具副本＋假 `claude`；之後 porcelain 必須為空（D-23）。"""
    sb = ctx.sandbox(probe_hooks=False)
    if tools:
        install_tools(sb)
    proj = projects_dir() / slug_of(sb.root)
    exe = ctx.fake_claude(sb, mode, sleep=sleep, projdir=proj)
    dirty = tree_clean(sb) if tools else ""  # 無工具副本＝沒有基線 commit，porcelain 無意義（.claude/ 恆為未追蹤）
    ctx.check(not dirty, f"沙盒髒（D-23：建好居所與替身後 porcelain 必須為空）：{dirty[:200]}")
    return sb, exe


def sessionctl(sb: Sandbox, *args: str, extra_env: dict | None = None, timeout: int = 180) -> subprocess.CompletedProcess:
    """跑沙盒內的 `sessionctl.py`（不自動授租約、不自動帶 `--claude`——本家族要精確控制）。"""
    return run([PY, str(sb.root / "tools" / "sessionctl.py"), *args], cwd=sb.root,
               env=ctl_env(sb, extra=extra_env), timeout=timeout)


def prep_pkg(ctx: CaseContext, sb: Sandbox, *, ctx_tokens: int | None, age_s: float = 10_800) -> Path:
    """合成逐字稿＋handoff --build＋補齊主控層；回交接包路徑（沙盒工作樹仍乾淨）。"""
    synth_transcript(sb, ctx_tokens=ctx_tokens, age_s=age_s)
    return make_package(ctx, sb)


def arm_park(ctx: CaseContext, sb: Sandbox, exe: Path, *, at: datetime, ctx_tokens: int | None,
             age_s: float = 10_800, extra_env: dict | None = None, claude: str | None = None,
             grant_minutes: int | None = 30, why: str = "realverify sideeffect 沙盒續航", track: bool = True) -> Armed:
    """合成逐字稿→`handoff --build`→主控層補齊→（授租約）→`park --at`；回 Armed。park 前置不成立 ⇒ fail。"""
    pkg = prep_pkg(ctx, sb, ctx_tokens=ctx_tokens, age_s=age_s)
    if grant_minutes is not None:
        ctx.grant_side_effects(sb, minutes=grant_minutes, window=False)
    r = sessionctl(sb, "park", "--session-id", sb.sid, "--at", iso_at(at), "--why", why, "--pkg", str(pkg),
                   "--claude", claude or str(exe), extra_env=extra_env)
    ctx.check(r.returncode == 0, f"park rc={r.returncode} stdout={r.stdout[-300:]} stderr={r.stderr[-400:]}")
    mk = marker_of(sb)
    ctx.check(mk is not None and mk["status"] == "armed", f"沒有 armed 標記：{mk}")
    label = mk["jobs"][0]["label"]
    if track:
        ctx.sched_track(label)  # 排程已由產品登記；案例改把名字記上帳，收尾由帳撤銷（發現式掃描另兜底）
    return Armed(sb, exe, pkg, label, datetime.fromisoformat(mk["fire_at"]), mk,
                 projects_dir() / slug_of(sb.root))


# ───────────────────────────────────────────────────────────── 讀沙盒痕跡
def marker_of(sb: Sandbox) -> dict | None:
    p = sb.home / "traces" / "park" / f"{sb.sid}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def events(sb: Sandbox, sid: str | None = None) -> list[dict]:
    """沙盒 `traces/autosdd_session_switch.jsonl` 中含該 sid 的事件列。"""
    return trace_lines(sb.home / "traces", SWITCH_TRACE, sid or sb.sid)


def names(sb: Sandbox) -> list[str]:
    return [e.get("event", "") for e in events(sb)]


def calls(sb: Sandbox) -> list[dict]:
    return fakeclaude.calls(sb.home)


def refusal(sb: Sandbox) -> dict | None:
    rows = [e for e in events(sb) if e.get("event") == "sideeffect_refused"]
    return rows[-1] if rows else None


# ───────────────────────────────────────────────────────────── 行程／視窗／排程探針
def _procs_json(script: str) -> list[dict]:
    rc, out = sched._ps(script, 60)  # noqa: SLF001 — 同一支 PowerShell 載具
    if rc != 0 or not out.startswith(("{", "[")):
        return []
    data = json.loads(out)
    return [data] if isinstance(data, dict) else data


def window_problems(boxes: list[Sandbox]) -> list[str]:
    """一次量全部沙盒（單次 CIM＋單次 Get-Process，輪詢才不會慢到錯過窗口）：命令列含任一沙盒 sid 的**真** claude
    （執行檔不在任何沙盒家目錄之下）行程，與執行檔位於沙盒家目錄之下、主視窗句柄非 0 的可見視窗（假 claude 是
    GUI 子系統、不建視窗；有＝開了窗）。回問題清單（空＝沒事）。"""
    homes = [str(b.home.resolve()).lower() for b in boxes]
    out: list[str] = []
    for r in _procs_json("Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'claude*' -or $_.Name -like 'node*' } | "
                         "Select-Object ProcessId,Name,CommandLine,ExecutablePath | ConvertTo-Json -Compress"):
        cmd, exe = (r.get("CommandLine") or ""), (r.get("ExecutablePath") or "").lower()
        hit = next((b for b in boxes if b.sid in cmd), None)
        if hit is not None and not any(exe.startswith(h) for h in homes):
            out.append(f"真 claude 行程 pid={r['ProcessId']} 命令列含沙盒 sid {hit.sid[:8]}")
    for r in _procs_json("Get-Process | Where-Object { $_.MainWindowHandle -ne 0 -and $_.Path -like '*AutoSDD_RV*' } | "
                         "Select-Object Id,ProcessName,Path | ConvertTo-Json -Compress"):
        if any(str(r.get("Path") or "").lower().startswith(h) for h in homes):
            out.append(f"沙盒家目錄下的可見視窗 pid={r['Id']} {r.get('ProcessName')}")
    return out


def watch_no_window(ctx: CaseContext, boxes: list[Sandbox], until: datetime, step: float = 2.0) -> int:
    """睡到 `until`，期間每 `step` 秒查一次 `window_problems`（TCS「沒有開窗」判準）。回輪詢次數（入證據）。"""
    n = 0
    while now() < until:
        bad = window_problems(boxes)
        ctx.check(not bad, "；".join(bad))
        n += 1
        time.sleep(step)
    return n


def task_result(name: str) -> dict | None:
    """排程最近一次執行結果：`{result, last_run, state}`；工作已不在回 None。"""
    rows = _procs_json(f"$t = Get-ScheduledTask -TaskName '{name}' -ErrorAction SilentlyContinue; if (-not $t) {{ exit 0 }}; "
                       "$i = $t | Get-ScheduledTaskInfo; [pscustomobject]@{result=[int64]$i.LastTaskResult; "
                       "last_run=if($i.LastRunTime){$i.LastRunTime.ToString('o')}else{''}; state=[string]$t.State} | ConvertTo-Json -Compress")
    return rows[0] if rows else None


def flip_task_arg(name: str, old: str, new: str) -> str:
    """把已登記工作 Action 引數裡的 old 文字換成
ew（Set-ScheduledTask -Action）；回換完後的引數。
    用途：park 在登記時就拒絕 AUTOSDD_SESSION_SWITCH_MODE=notify（政策閘），所以 e2 以 auto 登記、再把工作 argv 的模式改成 notify，
    驗「模式經 --job-env 帶到 job 並被 job 尊重」。換不到（old 不在引數內，例如 job_env_argv 沒轉送模式鍵）⇒ AssertionError。"""
    task = get_task(name)
    if task is None or old not in task["arguments"]:
        raise AssertionError(f"工作 {name} 的 Action 引數不含 {old!r}：{task and task['arguments'][:300]}")
    q = lambda x: x.replace("'", "''")  # noqa: E731
    # 以匯出的工作 XML 原樣重新登記（Principal／Settings／Trigger 全部保留；`Set-ScheduledTask -Action` 會把主體重設，之後自拆就刪不掉）
    rc, out = ps(f"$x = [string](Export-ScheduledTask -TaskName '{name}'); $x = $x.Replace('{q(old)}', '{q(new)}'); Register-ScheduledTask -TaskName '{name}' -Xml $x -Force | Out-Null")
    back = get_task(name)
    if rc != 0 or back is None or new not in back["arguments"]:
        raise AssertionError(f"改寫工作 {name} 引數失敗 rc={rc} {out[:200]}")
    return back["arguments"]


def task_xml(name: str) -> str:
    rc, out = sched._ps(f"Export-ScheduledTask -TaskName '{name}'", 60)  # noqa: SLF001
    return out if rc == 0 else ""


def wait_gone(names_: list[str], timeout_s: float, step: float = 3.0) -> list[str]:
    """等這些排程都消失（job 自拆）；回仍在者。"""
    t0 = time.monotonic()
    left = list(names_)
    while left and time.monotonic() - t0 < timeout_s:
        left = [n for n in left if get_task(n) is not None]
        if left:
            time.sleep(step)
    return left


def sweep_clean(ctx: CaseContext) -> str:
    """每個 E2E 結尾：`python tools/realverify.py sweep` 並斷言末行 `SWEEP_VERDICT=clean`（或本案自己的 revoked）。"""
    r = run([PY, str(REPO / "tools" / "realverify.py"), "sweep"], cwd=REPO, env=_plain_env(), timeout=300)
    last = (r.stdout.strip().splitlines() or [""])[-1]
    ctx.check(r.returncode == 0 and last.startswith("SWEEP_VERDICT="), f"sweep rc={r.returncode} 末行={last!r} {r.stderr[-200:]}")
    return last


def _plain_env() -> dict:
    import os  # noqa: PLC0415
    e = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "AUTOSDD_UNATTENDED")}
    e["PYTHONUTF8"] = "1"
    return e


def plain_env() -> dict:
    return _plain_env()


def rmtree(path: Path) -> None:
    force_rmtree(Path(path))


def reserve_mark(kind: str, ident: str | Path) -> str:
    """案例自己建的暫存物：先登記帳列（收尾由帳撤銷），再回 ident。"""
    return leases.track_kind(kind, ident)


def lease_allow_until(sb: Sandbox) -> datetime:
    return datetime.fromisoformat(json.loads((sb.home / sandbox_scope.IDENTITY_NAME).read_text(encoding="utf-8"))["allow_until"])


def in_s(seconds: float) -> str:
    return iso_in(seconds)


# ───────────────────────────────────────────────────────────── 主人行程（子 runner）協定
SPEC_ENV = "RV_SE_SPEC"


@dataclass
class Runner:
    proc: subprocess.Popen
    ctl_dir: Path
    ready_path: Path
    out_path: Path
    info: dict | None = None


def control_dir(ctx: CaseContext) -> Path:
    """父案例與子 runner 交換規格／ready／輸出的暫存目錄（`%TEMP%\\AutoSDD_RV_ctl_*`；先登記後建）。"""
    d = Path(tempfile.gettempdir()).resolve() / f"{CTL_PREFIX}{leases.current_run_id()}-{uuid.uuid4().hex[:4]}"
    leases.track_kind("temp_file", d)
    d.mkdir(parents=True)
    ctx.notes.append(f"控制目錄 {d}")
    return d


def spawn_runner(ctx: CaseContext, case_id: str, spec: dict, *, env_extra: dict | None = None,
                 env_base: dict | None = None) -> Runner:
    """背景起 `python tools/realverify.py run --case <case_id>`（輔助案例；規格經 `RV_SE_SPEC`）。"""
    d = control_dir(ctx)
    ready = d / "ready.json"
    (d / "spec.json").write_text(json.dumps({**spec, "ready": str(ready)}, ensure_ascii=False), encoding="utf-8", newline="\n")
    env = dict(env_base if env_base is not None else plain_env())
    env[SPEC_ENV] = str(d / "spec.json")
    env.update(env_extra or {})
    out = d / "runner.out"
    with out.open("wb") as handle:
        proc = subprocess.Popen([PY, str(REPO / "tools" / "realverify.py"), "run", "--case", case_id],  # noqa: S603
                                cwd=str(REPO), env=env, stdout=handle, stderr=subprocess.STDOUT, creationflags=NOWIN)
    runner = Runner(proc, d, ready, out)
    ctx.__dict__.setdefault("rv_runners", []).append(runner)  # kills_runners 收尾用
    return runner


def wait_ready(ctx: CaseContext, runner: Runner, timeout_s: float = 420.0) -> dict:
    """輪詢 ready 檔；子 runner 提前結束 ⇒ 判 fail 並附輸出尾端。讀到後把子沙盒的字樣併入本案快照比對。"""
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_s:
        if runner.ready_path.is_file():
            runner.info = json.loads(runner.ready_path.read_text(encoding="utf-8"))
            ctx.extra_tokens += [str(runner.info[k]) for k in ("sid", "root", "home", "run_id") if runner.info.get(k)]
            return runner.info
        if runner.proc.poll() is not None:
            tail = runner.out_path.read_text(encoding="utf-8", errors="replace")[-600:]
            raise AssertionError(f"子 runner 在 ready 之前結束 rc={runner.proc.returncode}：{tail}")
        time.sleep(1.0)
    raise AssertionError(f"子 runner {timeout_s:.0f}s 內沒有寫 ready")


def kill_pid(pid: int) -> None:
    """強殺 `pid`（**不帶 /T**：只殺主人行程本身，TCS E2E-SE-02）。Windows＝`taskkill /F /PID`；
    POSIX＝`SIGKILL`（`taskkill` 在對面平台是 FileNotFoundError，故平台分支）。"""
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, creationflags=NOWIN, check=False)  # noqa: S603,S607
    else:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def pid_alive(pid: int) -> bool:
    return sandbox_scope.proc_probe(pid)[0]


def finish_runner(runner: Runner, timeout_s: float = 30.0) -> str:
    """等子 runner 行程結束（已被殺或自然結束）並回輸出全文；逾時就殺它的 pid。"""
    try:
        runner.proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        if runner.info:
            kill_pid(int(runner.info["pid"]))
        runner.proc.kill()
    return runner.out_path.read_text(encoding="utf-8", errors="replace") if runner.out_path.is_file() else ""


def stop_runner(runner: Runner) -> None:
    """收掉子 runner（已死就不動）：先殺它自己的 pid（ready 檔裡的真直譯器 pid），再殺啟動它的 Popen。"""
    if runner.info is None and runner.ready_path.is_file():
        runner.info = json.loads(runner.ready_path.read_text(encoding="utf-8"))
    if runner.info and runner.info.get("pid") and pid_alive(int(runner.info["pid"])):
        kill_pid(int(runner.info["pid"]))
    if runner.proc.poll() is None:
        runner.proc.kill()
        runner.proc.wait(timeout=15)


def kills_runners(fn):
    """案例裝飾：案例結束（含失敗）時一定收掉它起的子 runner——否則失敗的父案例會留下活著的主人與有效帳列。"""
    @functools.wraps(fn)
    def wrapper(ctx: CaseContext) -> None:
        try:
            fn(ctx)
        finally:
            for runner in getattr(ctx, "rv_runners", []):
                stop_runner(runner)
            if getattr(ctx, "rv_runners", []):
                run([PY, str(REPO / "tools" / "realverify.py"), "sweep"], cwd=REPO, env=_plain_env(), timeout=300)  # 失敗路徑也不留孤兒
    return wrapper


def ledger_rows(run_id: str) -> list[dict]:
    return leases.read_rows(leases.LEASE_DIR / f"{run_id}.jsonl")


# ───────────────────────────────────────────────────────────── 帳／快照輔助（SE-03／11／13／18）
def ledger_names() -> set[str]:
    return {p.name for p in leases.LEASE_DIR.glob("*.jsonl")} if leases.LEASE_DIR.is_dir() else set()


def new_run_tokens(before: set[str]) -> list[str]:
    """`before` 之後新出現的帳檔 ⇒ 本批所有 run 的快照字樣（run_id、沙盒根／家名、sid、逐字稿目錄名）。"""
    out: list[str] = []
    for name in sorted(ledger_names() - before):
        out.append(Path(name).stem)
        for row in leases.read_rows(leases.LEASE_DIR / name):
            ident, kind = str(row.get("ident") or ""), row.get("kind")
            if kind == "sandbox_root":
                out += [ident, Path(ident).name]
            elif kind == "process" and ident.startswith("sid:"):
                out.append(ident[4:])
            elif kind == "transcript_dir":
                out.append(Path(ident).name)
    return list(dict.fromkeys(t for t in out if t))


def unclosed_ledgers(names_: set[str]) -> list[str]:
    """這些帳檔中最後一列不是 `run closed` 者（`closed` 之後不再追加）。"""
    bad = []
    for name in sorted(names_):
        rows = leases.read_rows(leases.LEASE_DIR / name)
        if not rows or not (rows[-1].get("kind") == "run" and rows[-1].get("state") == "closed"):
            bad.append(name)
    return bad


def hash_tree(root: Path, skip_top: tuple[str, ...] = ()) -> dict[str, str]:
    """`root` 下全檔的雜湊清單 `{相對路徑: 摘要}`（≤1 MB 取內容 sha1，其餘取 size＋mtime_ns）；`skip_top` 為略過的第一層名。"""
    import hashlib  # noqa: PLC0415
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if (rel.parts and rel.parts[0] in skip_top) or not p.is_file():
            continue
        try:
            st = p.stat()
            out[rel.as_posix()] = (hashlib.sha1(p.read_bytes()).hexdigest() if st.st_size <= 1_000_000  # noqa: S324
                                   else f"{st.st_size}:{st.st_mtime_ns}")
        except OSError:
            out[rel.as_posix()] = "unreadable"
    return out
