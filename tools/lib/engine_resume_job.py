"""引擎被拒絕的長睡之外部承接：註冊一次性續跑工作（launchd／schtasks），並充當 job 本體。"""
# ─────────────────────────────────────────────────────────────────────────────
# WHY 這支存在（ARCH-01；引擎側鉤子＝`AutoClaude/autoclaude/core/services/external_resume.py`）
# 引擎對 > max_inprocess_wait_seconds 的等待拒絕行程內長睡、rc=1 退出，修前之後**沒有任何元件**
# 重啟它——無人值守時整場 run 在第一次撞週額度就停死。引擎不蓋排程器（importlinter 規則 9），只在
# `AUTOCLAUDE_EXTERNAL_RESUME_CMD` 非空時以範本呼叫本檔一次：
#   <python> tools/lib/engine_resume_job.py --playbook {playbook} --at {resume_at} --cwd {cwd}
# 本檔於 `at`＋`planner.RESET_SKEW_SECONDS`（reset 是滾動視窗，不踩點）註冊**一次性**工作。
#
# 🔴 為什麼是自己的原語、而不是 `schedule_backend.select().arm()`：那支 `arm` 的動作寫死為「叫
#    planner 的 tick」（`_argv`／`endurance_schtasks_script`），且帶 `StartInterval` 巡邏；引擎
#    續跑要的是「到點跑一次 `python -m autoclaude`」。平台由 `select()` 決定（不自問 `os.name`），
#    原語走 `schedule_backend._run`／planner 的 PowerShell 載具（NO_WINDOW、UTF-8 前置、
#    `_SCHTASKS_SETTINGS` 四項設定、單引號跳脫、`NextRunTime` 解析皆取用不抄）；本檔因此是
#    `CarrierPrimitivesHaveOneHomeTest` 的具名豁免（理由寫在該表）。要把它收進
#    `schedule_backend` 需動守衛面，且該檔 LOC 貼頂。
# 🔴 一次性＝**job 本體自拆**：launchd 沒有原生 one-shot，`StartCalendarInterval`（Month/Day/
#    Hour/Minute）一年後會再醒——而醒來重跑 playbook 是意外執行。故 plist 的動作是本檔 `--run`：
#    先確認不是過期的誤觸發（> STALE_FIRE_SECONDS 拒絕）、跑引擎、**跑完才**
#    `backend.disarm(自己)`（自拆走既有的「等父行程退場再 bootout」，不會殺掉還在跑的引擎）。
# 🔴 工作名＝`AutoSDD_EngineResume_<playbook 雜湊>_<觸發分鐘>`：每次註冊一個新名字，所以引擎在
#    job 內再度拒絕長睡、再呼叫本檔時，不會對「正在跑的自己」做 bootout（DEF-200-526 的形狀）。
#    `--run` 把自己的名字放進 `AUTOSDD_ENGINE_RESUME_JOB` 給子孫繼承（launchd 只給 job 本體
#    XPC_SERVICE_NAME），註冊端據此跳過它；同 playbook 的其他舊工作一律取代（同時只該有一個）。
# 🔴 憑證＝排程器自己回報的值：launchd＝`launchctl print` rc＋descriptor 回讀（與請求逐項比對，
#    不符不發憑證、並拆掉剛寫的 plist）；schtasks＝`NextRunTime` 非空。拿不到一律 rc=1，不宣稱
#    已排程。
# 🔴 機密不落地：plist 只帶 `_CARRY_ENV` 白名單（PATH／語系／本鉤子變數，後者讓續跑出來的引擎
#    能再交棒）；`MINIMAX_API_KEY`／DSN 一律不寫進 `~/Library/LaunchAgents`。續跑引擎需要的其他
#    設定請放 config.yaml。
# 🔴 誠實劃界：①睡著的 Mac 不會被喚醒（`endurance_env.warn_if_sleepy` 出聲）；②launchd 對只有
#    StartCalendarInterval 的 job 的 `print` 回讀形態只有合成輸出對過（真機未驗證）；③Windows
#    分支只驗到腳本內容與判準、未實跑；④續跑用的是 cwd 下預設 config.yaml，非預設設定請在範本
#    加 `--config`。
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import plistlib
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import endurance_env
import schedule_backend as sb
import win_spawn
from schedule_backend_calendar import _append_trace, _calendar_of, _descriptor_problems

SCHEMA = "autosdd.engine_resume/1"
JOB_PREFIX = "AutoSDD_EngineResume_"
#: `--run` 放進子行程環境的「我是哪個 job」。
JOB_ENV = "AUTOSDD_ENGINE_RESUME_JOB"
#: 字面兩個家：引擎 `core/services/external_resume.py` 的同名常數（跨 importlinter 只能這樣接，
#: 由 tools/probe/engine_resume_job_sim.py 讀兩邊原始碼比對）。
EXTERNAL_RESUME_CMD_ENV = "AUTOCLAUDE_EXTERNAL_RESUME_CMD"
TRACE_NAME = "autosdd_engine_resume.jsonl"
#: 觸發時刻至少落在「現在＋這麼久」之後（過去的 calendar 一年後才會再醒）。
MIN_LEAD_SECONDS = 90
#: 比預定觸發晚這麼久才醒＝一年後的 calendar 重發／誤觸發，不是補跑睡過頭的 Mac。
STALE_FIRE_SECONDS = 30 * 86400
#: plist 的環境變數白名單。刻意不含任何機密。
_CARRY_ENV = ("PATH", "PYTHONUTF8", "LANG", "LC_ALL", EXTERNAL_RESUME_CMD_ENV)
_REPO = Path(__file__).resolve().parents[2]
_KNOWN = ("--playbook", "--at", "--cwd", "--config", "--remove", "--run", "--job", "--fire-at",
          "--help")


def _trace(event: str, **fields) -> None:
    row = {"schema": SCHEMA, "event": event, **fields}
    _append_trace(endurance_env.trace_dir() / TRACE_NAME, row)


def _engine_importable() -> bool:
    return importlib.util.find_spec("autoclaude") is not None


def job_prefix(playbook: str) -> str:
    digest = hashlib.sha256(os.path.abspath(playbook).encode("utf-8")).hexdigest()
    return f"{JOB_PREFIX}{digest[:10]}_"


def _mine(backend, prefix: str) -> list[str] | None:
    """該 playbook 的待命續跑工作；`None`＝列舉量不到。多一道前綴過濾：絕不誤拆別族工作。"""
    jobs = backend.list_jobs(prefix)
    return None if jobs is None else [job for job in jobs if job.startswith(prefix)]


def fire_time(at: datetime, skew_seconds: int, now: datetime) -> datetime:
    """觸發時刻＝`at`＋緩衝，不早於 `now`＋MIN_LEAD；向後取整到分鐘（只准晚）。"""
    due = max(at.astimezone() + timedelta(seconds=skew_seconds),
              now.astimezone() + timedelta(seconds=MIN_LEAD_SECONDS))
    return (due + timedelta(seconds=59)).replace(second=0, microsecond=0)


def _job_argv(label: str, playbook: str, cwd: str, config: str | None, fire: datetime) -> list[str]:
    argv = [win_spawn.quiet_python(), str(Path(__file__).resolve()), "--run", "--job", label,
            "--playbook", playbook, "--cwd", cwd, "--fire-at", fire.isoformat(timespec="seconds")]
    return argv + (["--config", config] if config else [])


def _engine_python() -> str:
    exe = Path(sys.executable)           # Windows 的 job 本體是 pythonw：引擎要有（隱藏的）console
    console = exe.with_name("python.exe")
    quiet = exe.name.lower() == "pythonw.exe"
    return str(console) if quiet and console.is_file() else sys.executable


def _manual_hint(playbook: str, cwd: str, at: datetime) -> str:
    return (f"手動重跑：於 {at.astimezone():%Y-%m-%d %H:%M} 之後在 {cwd} 執行 "
            f"`{sys.executable} -m autoclaude {playbook}`（checkpoint 已落地，會從斷點續跑）")


def _arm_launchd(backend, label: str, argv: list[str], cwd: str, fire: datetime) -> tuple[int, str]:
    endurance_env.warn_if_sleepy(sb._run)
    cal, dom = _calendar_of(fire, 0), f"gui/{getattr(os, 'getuid', lambda: 0)()}"
    plist = sb.LAUNCH_AGENTS_DIR / f"{label}.plist"
    log = endurance_env.trace_dir() / f"autosdd_engine_resume_{label}.log"
    body = {"Label": label, "ProgramArguments": argv, "WorkingDirectory": cwd, "RunAtLoad": False,
            "StartCalendarInterval": cal, "StandardOutPath": str(log),
            "StandardErrorPath": str(log),
            "EnvironmentVariables": {k: os.environ[k] for k in _CARRY_ENV if k in os.environ}}
    try:
        plist.parent.mkdir(parents=True, exist_ok=True)
        plist.write_bytes(plistlib.dumps(body))
    except OSError as exc:
        print(f"❌ plist 寫不進去：{plist}（{exc}）", file=sys.stderr)
        return 1, ""
    rc, out = sb._run(["plutil", "-lint", str(plist)])
    live = None
    if rc == 0:
        sb._run(["launchctl", "bootout", f"{dom}/{label}"])            # 同名殘留先拆（冪等覆寫）
        sb._run(["launchctl", "bootstrap", dom, str(plist)])
        live = backend._readback(label)
    problems = ([f"plutil -lint 未通過：{out.strip()}"] if rc else
                ["launchctl print 取不到（rc != 0）"] if live is None else
                _descriptor_problems(live, argv, None, str(plist), cal))
    if problems:
        sb._run(["launchctl", "bootout", f"{dom}/{label}"])
        plist.unlink(missing_ok=True)
        print("❌ launchd 武裝沒有成立：" + "；".join(problems), file=sys.stderr)
        return 1, ""
    return 0, (f"launchd {dom}/{label}｜launchctl print rc=0｜StartCalendarInterval = {cal}"
               f"〔launchd 自報〕｜argv 回讀 {len(live['argv'])} 項與請求逐項相符｜plist = {plist}"
               "｜🔴 這**不是** NextRunTime（launchd 不報下次幾點跑），也不證明睡著的 Mac 會醒")


def _arm_schtasks(planner, label: str, argv: list[str], cwd: str,
                  fire: datetime) -> tuple[int, str]:
    q = planner._ps_single_quote
    python = q(win_spawn.quiet_python())              # 載具＝pythonw（無 console；同 argv[0]）
    args = " ".join(f'"{a}"' for a in argv[1:])
    script = (
        "$ErrorActionPreference = 'Stop'\n"
        f"$action = New-ScheduledTaskAction -Execute '{python}' -Argument '{q(args)}' "
        f"-WorkingDirectory '{q(cwd)}'\n"
        f"$trigger = New-ScheduledTaskTrigger -Once -At '{fire:%Y-%m-%d %H:%M:%S}'\n"
        f"$settings = {planner._SCHTASKS_SETTINGS}\n$principal = {planner._SCHTASKS_PRINCIPAL}\n"
        f"$common = @{{TaskName='{q(label)}'; Action=$action; Trigger=$trigger; "
        "Settings=$settings; Force=$true}\n"
        "try { Register-ScheduledTask @common -Principal $principal -EA Stop | Out-Null }\n"
        "catch { Register-ScheduledTask @common | Out-Null"
        "; Write-Output 'PRINCIPAL-FALLBACK=default-interactive' }\n\n"
        f"{planner._EVIDENCE_TEMPLATE.format(task=q(label))}\n")
    proc = planner.run_powershell(script)
    print(proc.stdout, end="")
    moment = planner.next_run_time(proc.stdout)
    if proc.returncode != 0 or not moment:
        print(f"❌ 排程沒有成立（rc={proc.returncode}，NextRunTime 取不到）⇒ 本工具**不會**說它"
              "已排程。\n" + (proc.stderr or ""), file=sys.stderr)
        return 1, ""
    return 0, f"NextRunTime = {moment}（排程器自報；憑證，宣稱『已排程』時必須連它一起貼）"


def _refusal(backend, planner, playbook: str, cwd: str) -> str:
    if backend.name not in ("launchd", "schtasks"):
        return (f"本平台沒有已實作的排程載具（載具＝{backend.name}）："
                "Windows 走 schtasks、macOS 走 launchd")
    if planner is None:
        return "planner 不可達（排程原語與緩衝常數住在那裡）"
    for ok, why in ((Path(playbook).is_file(), f"playbook 不存在：{playbook}"),
                    (Path(cwd).is_dir(), f"工作目錄不存在：{cwd}"),
                    (_engine_importable(), "這個直譯器 import 不到 autoclaude ⇒ 掛了也跑不起來")):
        if not ok:
            return why
    return ""


def arm(playbook: str, at: datetime, *, cwd: str, config: str | None = None,
        now: datetime | None = None) -> tuple[int, str]:
    """註冊一次性續跑工作並取證。回 `(rc, 憑證字串)`；拿不到憑證一律 rc=1、憑證空。"""
    pb, now = os.path.abspath(playbook), now or datetime.now().astimezone()
    backend, planner = sb.select(), sb._planner()
    why = _refusal(backend, planner, pb, cwd)
    if why:
        print(f"❌ 拒絕註冊：{why}\n{_manual_hint(pb, cwd, at)}", file=sys.stderr)
        _trace("refused", playbook=pb, why=why)
        return 1, ""
    fire, prefix = fire_time(at, planner.RESET_SKEW_SECONDS, now), job_prefix(pb)
    label, inside = f"{prefix}{fire:%Y%m%d%H%M}", os.environ.get(JOB_ENV, "")
    for old in _mine(backend, prefix) or []:         # None＝量不到：寧可多一支也不要沒有
        if old not in (label, inside):
            backend.disarm(old)
            _trace("superseded", old=old, label=label)
    argv = _job_argv(label, pb, cwd, config, fire)
    rc, cred = (_arm_launchd(backend, label, argv, cwd, fire) if backend.name == "launchd"
                else _arm_schtasks(planner, label, argv, cwd, fire))
    _trace("armed" if rc == 0 else "arm_failed", label=label, playbook=pb, backend=backend.name,
           fire_at=fire.isoformat(timespec="seconds"), cwd=cwd)
    return rc, cred


def remove(playbook: str) -> int:
    """移除該 playbook 的所有待命續跑工作；回讀確認，量不到就不宣稱已移除。"""
    backend, prefix = sb.select(), job_prefix(playbook)
    jobs = _mine(backend, prefix)
    if jobs is None:
        print("❌ 排程器列舉量不到 ⇒ 不宣稱已移除", file=sys.stderr)
        return 1
    failed = [job for job in jobs if backend.disarm(job) != 0]
    left = _mine(backend, prefix) if jobs else []
    ok = not failed and left == []
    _trace("removed" if ok else "remove_failed", playbook=os.path.abspath(playbook), jobs=jobs,
           left=left)
    print(f"{'✅' if ok else '❌'} {prefix}*：移除 {len(jobs)} 支；回讀剩餘 {left}")
    return 0 if ok else 1


def run_job(label: str, playbook: str, cwd: str, config: str | None, fire_at: str) -> int:
    """job 本體：確認不是過期誤觸發 → 跑引擎 → 跑完才自拆。回引擎的 rc。"""
    backend = sb.select()
    try:
        late = (datetime.now().astimezone() - datetime.fromisoformat(fire_at)).total_seconds()
    except ValueError:
        late = float("inf")                          # 解析不出預定時刻＝無法證明不是誤觸發 ⇒ 拒絕
    _trace("job_start", label=label, playbook=playbook, cwd=cwd, fire_at=fire_at, late_seconds=late)
    if late > STALE_FIRE_SECONDS:
        _trace("stale_refused", label=label)
        backend.disarm(label)
        return 3
    argv = [_engine_python(), "-m", "autoclaude", playbook]
    argv += ["--config", config] if config else []
    try:
        rc = subprocess.run(argv, cwd=cwd, env={**os.environ, JOB_ENV: label}, check=False,
                            creationflags=win_spawn.NO_WINDOW).returncode
    except OSError as exc:
        _trace("engine_spawn_failed", label=label, error=str(exc))
        rc = 127
    _trace("job_done", label=label, rc=rc)
    backend.disarm(label)
    return rc


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    sys.path.insert(0, str(_REPO / "tools"))
    import _cli_flags  # noqa: PLC0415 — 只有 CLI 才要；`tools/` 不在 lib 的預設 sys.path
    rejected = _cli_flags.reject_unknown_argv("engine_resume_job.py",
                                              [a for a in args if a.startswith("--")], _KNOWN)
    if rejected is not None:
        return rejected
    ap = argparse.ArgumentParser(prog="engine_resume_job.py", allow_abbrev=False,
                                 description="註冊／移除引擎的一次性續跑工作（--run 為 job 本體）")
    ap.add_argument("--playbook", required=True)
    ap.add_argument("--at", help="ISO 8601 帶 offset 的續跑時刻（註冊時必填）")
    ap.add_argument("--cwd", default=str(_REPO / "AutoClaude"))
    ap.add_argument("--config")
    ap.add_argument("--remove", action="store_true")
    ap.add_argument("--run", action="store_true", help="job 本體（由排程器呼叫，勿手動）")
    ap.add_argument("--job")
    ap.add_argument("--fire-at")
    ns = ap.parse_args(args)
    pb, cwd = os.path.abspath(ns.playbook), os.path.abspath(ns.cwd)
    if ns.remove:
        return remove(pb)
    if ns.run:
        if not (ns.job and ns.fire_at):
            ap.error("--run 需要 --job 與 --fire-at")
        return run_job(ns.job, pb, cwd, ns.config, ns.fire_at)
    try:
        at = datetime.fromisoformat(ns.at or "")
    except ValueError:
        ap.error("--at 必填且須為 ISO 8601（例：2026-10-14T09:05:00+08:00）")
    rc, cred = arm(pb, at, cwd=cwd, config=ns.config)
    print(("✅ " if rc == 0 else "") + cred)
    return rc


if __name__ == "__main__":  # pragma: no cover
    from platform_utils import init_utf8_streams

    init_utf8_streams()
    raise SystemExit(main())
