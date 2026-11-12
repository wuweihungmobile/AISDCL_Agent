"""SelfImproving OS 任務載具封裝：`sched arm`／`sched disarm`
（TCS-SelfImproving-P4 R161 (d)(e)；P7 加推送任務）。

能力類別 `exec`：外呼一律經注入的 `run_argv`（預設 `runner.run_argv`，明示環境）。
Windows＝呼叫 `tools/install_windows_nightly.ps1`（整組任務）並以
`Get-ScheduledTask … NextRunTime` 為憑證；macOS＝自寫 launchd plist 並以 `launchctl`
rc 與 plist 回讀為憑證（macOS 未實機驗證）。**憑證是值，不是 rc**：取不到憑證＝rc 1，
輸出不得宣稱已排程。本檔不 import、不改續航排程後端；啟用旗標（`sched.set`）與 OS 任務
相互獨立：本檔不寫任何事件。單平台外部執行檔（`powershell.exe`、`schtasks`、
`launchctl`）的 argv 字面只住 `sys.platform` 守衛分支內（根 CLAUDE.md 鐵律三）。

**第二支任務 `AutoSDD_SI_Push`（P7；`sched_auto_push` 為 true 時）**：互動登入型
（`Interactive`，不是 `S4U`）——S4U 拿不到 Git Credential Manager 的憑證保管庫，且
S4U 註冊在非提權 session 回「存取被拒」；代價是使用者未登入時整輪不跑（快照
`waiting-login`）。動作直接呼叫 `pythonw.exe … push-run`（無 console 視窗、無新
.ps1）；推送任務**不納入** `scheduled_task_expectations.json` 與
`install_windows_nightly.ps1`（該 SSOT 專屬需提權的 S4U 任務，ADR-SI-19）。推送段與
巡邏段獨立：巡邏段因權限失敗時推送段仍會嘗試；`--push-only` 只處理推送任務。
"""

from __future__ import annotations

import json
import os
import plistlib
import re
import sys
from datetime import datetime
from pathlib import Path

from . import events as si_events
from . import params as si_params
from . import runner, sched
from . import writeverbs as wv
from .git import Git, arm_record, resolve_git, safe_path

LABEL = sched.ARMED_TASK
PUSH_LABEL = "AutoSDD_SI_Push"
_ENV_KEYS = ("PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME", "USERPROFILE", "APPDATA",
             "LOCALAPPDATA", "USERNAME", "USERDOMAIN", "LANG", "LC_ALL")
_ELEVATION_RE = re.compile(r"(?i)access is denied|administrator|elevat|拒絕存取|系統管理員|提權")
_INSTALLER_REL = "tools/install_windows_nightly.ps1"
_TICK_REL = "tools/si_patrol_tick.ps1"
_TIMEOUT = 180


def _env() -> dict[str, str]:
    return {k: os.environ[k] for k in _ENV_KEYS if k in os.environ}


def _params(repo: Path) -> dict:
    return wv.params_for(repo, *si_params.SCHED_KEYS)


def _heartbeat_minutes(repo: Path) -> int:
    return _params(repo)["sched_heartbeat_minutes"]


def _installer_argv(repo: Path) -> list[str]:
    """Windows：呼叫安裝器的 argv（單平台字面，只在 Windows 分支內組出）。"""
    if sys.platform.startswith("win"):
        return ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                str(repo / _INSTALLER_REL)]
    return []


def _ps(script: str) -> list[str]:
    """Windows：`powershell.exe -Command <script>` 的 argv（單平台字面，只在 Windows 分支內
    組出）。"""
    if sys.platform.startswith("win"):
        return ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script]
    return []


def _remove_argv(label: str = LABEL) -> list[str]:
    return _ps(f"Unregister-ScheduledTask -TaskName '{label}' -Confirm:$false")


def _plist_path(plist_dir: Path | None, label: str = LABEL) -> Path:
    return (plist_dir or Path.home() / "Library" / "LaunchAgents") / f"{label}.plist"


def _launchctl(*args: str) -> list[str]:
    """macOS：`launchctl` 的 argv（單平台字面，只在非 Windows 分支內組出）。"""
    if not sys.platform.startswith("win"):
        return ["launchctl", *args]
    return []


def _uid() -> str:
    """launchd 的 gui 網域用 uid；Windows 沒有 `os.getuid`（launchctl 路徑只在 macOS 走）。"""
    return str(getattr(os, "getuid", lambda: 0)())


def _body(res) -> str:
    """安裝／移除動作的輸出（stdout 加 stderr，供辨識 elevation 不足）。"""
    out, err = getattr(res, "out", "") or "", getattr(res, "err", "") or ""
    return out + ("" if not err else ("\n" if out else "") + err)


def _reject(repo: Path, code: str, detail: str, as_json: bool, verb: str) -> tuple[int, str]:
    res = wv.reject(repo, f"sched {verb}", [(code, detail)], as_json)
    return res.rc, res.text


def _ok(verb: str, detail: dict, as_json: bool) -> tuple[int, str]:
    if as_json:
        return 0, json.dumps({"ok": True, "kind": f"sched.{verb}", **detail},
                             ensure_ascii=False) + "\n"
    return 0, f"ok sched {verb} " + " ".join(f"{k}={v}" for k, v in detail.items()) + "\n"


# ── 現查 ──────────────────────────────────────────────────────────────────────
def _mac_value(run_argv, plist_dir: Path | None, label: str = LABEL) -> dict:
    """macOS 憑證＝`launchctl list` rc 與 plist 回讀（launchd 從不報下次幾點跑）。"""
    res = run_argv(_launchctl("list", label), env=_env(), timeout=30, cwd=None)
    if getattr(res, "timed_out", False):
        return {"task": label, "present": None, "credential": sched.NE_PREFIX + "timeout"}
    rc = getattr(res, "rc", None)
    if rc == 113:
        return {"task": label, "present": False, "credential": "-"}
    if rc != 0:
        return {"task": label, "present": None, "credential": f"{sched.NE_PREFIX}rc-{rc}"}
    try:
        with open(_plist_path(plist_dir, label), "rb") as fh:
            interval = plistlib.load(fh).get("StartInterval")
    except (OSError, ValueError):
        interval = None
    if not interval:
        return {"task": label, "present": None,
                "credential": sched.NE_PREFIX + "plist-unreadable"}
    return {"task": label, "present": True,
            "credential": f"launchctl-rc-0 StartInterval={interval}"}


def armed(run_argv=runner.run_argv, *, plist_dir: Path | None = None) -> dict:
    """`status.schedule.armed` 的平台分派（Windows 走 `sched.armed_value`）。"""
    if sys.platform.startswith("win"):
        return sched.armed_value(run_argv)
    if sys.platform == "darwin":
        try:
            return _mac_value(run_argv, plist_dir)
        except Exception as exc:  # noqa: BLE001  # 現查失敗一律量不到
            return {"task": LABEL, "present": None,
                    "credential": sched.NE_PREFIX + type(exc).__name__}
    return {"task": LABEL, "present": None, "credential": sched.NE_PREFIX + "platform-unsupported"}


def _push_query_argv() -> list[str]:
    """Windows：推送任務現查（NextRunTime 值與註冊的 Principal.UserId）；不存在印 ABSENT。"""
    return _ps(f"$t = Get-ScheduledTask -TaskName '{PUSH_LABEL}' -ErrorAction SilentlyContinue; "
               "if (-not $t) { 'ABSENT'; exit 0 }; $i = $t | Get-ScheduledTaskInfo; "
               "if ($i.NextRunTime) { 'NEXT=' + $i.NextRunTime.ToString('o') } "
               "else { 'NEXT=NONEXT' }; 'USER=' + $t.Principal.UserId; "
               "try { 'SID=' + (New-Object Security.Principal.NTAccount($t.Principal.UserId))"
               ".Translate([Security.Principal.SecurityIdentifier]).Value } catch {}")


def _push_value(run_argv, plist_dir: Path | None) -> dict:
    """推送任務現查：`{task, present, credential, user}`（憑證是 NextRunTime 值；mac 為
    rc＋plist 回讀）。"""
    if sys.platform == "darwin":
        return {**_mac_value(run_argv, plist_dir, PUSH_LABEL), "user": None}
    try:
        res = run_argv(_push_query_argv(), env=_env(), timeout=30, cwd=None)
    except Exception as exc:  # noqa: BLE001  # 現查失敗一律量不到
        return {"task": PUSH_LABEL, "present": None, "user": None,
                "credential": sched.NE_PREFIX + type(exc).__name__}
    lines = [ln.strip() for ln in (getattr(res, "out", "") or "").splitlines() if ln.strip()]
    if getattr(res, "timed_out", False) or getattr(res, "rc", 1) != 0 or not lines:
        return {"task": PUSH_LABEL, "present": None, "user": None, "credential": sched.NE_PREFIX + (
            "timeout" if getattr(res, "timed_out", False) else f"rc-{getattr(res, 'rc', '?')}")}
    if lines[-1] == "ABSENT":
        return {"task": PUSH_LABEL, "present": False, "credential": "-", "user": None}
    kv = dict(ln.split("=", 1) for ln in lines if "=" in ln)
    nxt = kv.get("NEXT", lines[-1])
    cred = sched.NE_PREFIX + "no-next-run-time" if nxt == "NONEXT" else nxt
    return {"task": PUSH_LABEL, "present": True, "credential": cred, "user": kv.get("USER"),
            "sid": kv.get("SID")}


# ── arm ───────────────────────────────────────────────────────────────────────
def _write_plist(repo: Path, plist_dir: Path | None, *, label: str = LABEL, verb: str = "patrol",
                 logs: bool = True) -> Path:
    py, script = str(repo / ".venv" / "bin" / "python"), str(repo / "tools" / "selfimproving.py")
    plist = {"Label": label, "RunAtLoad": False,
             "StartInterval": _heartbeat_minutes(repo) * 60,
             "ProgramArguments": [py, script, verb, "--repo", str(repo)],
             "WorkingDirectory": str(repo)}
    if logs:
        folder = si_events.si_dir() / "patrol"
        folder.mkdir(parents=True, exist_ok=True)
        plist["StandardOutPath"] = str(folder / "launchd.out.log")
        plist["StandardErrorPath"] = str(folder / "launchd.err.log")
    else:  # 推送 agent：launchd 預設 PATH 只有系統目錄，找不到 Homebrew 的 git（審查 F-16）
        plist["EnvironmentVariables"] = {
            "PATH": safe_path() or "/usr/bin:/bin:/usr/sbin:/sbin",
            "AUTOSDD_SI_DIR": str(si_events.si_dir())}
    path = _plist_path(plist_dir, label)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as fh:
        plistlib.dump(plist, fh)
    return path


def _arm_mac(repo: Path, run_argv, plist_dir: Path | None, *, label: str = LABEL,
             verb: str = "patrol", logs: bool = True):
    path = _write_plist(repo, plist_dir, label=label, verb=verb, logs=logs)
    uid = _uid()
    run_argv(_launchctl("bootout", f"gui/{uid}/{label}"), env=_env(), timeout=30, cwd=None)
    res = run_argv(_launchctl("bootstrap", f"gui/{uid}", str(path)), env=_env(), timeout=30,
                   cwd=None)
    return res, _launchctl("bootstrap", f"gui/{uid}", str(path))


def _arm_patrol(repo: Path, run_argv, plist_dir: Path | None, win: bool) -> tuple[str | None, str]:
    """巡邏任務安裝並以憑證驗證：回（失敗碼或 None, 詳情或憑證值）。"""
    if win:
        argv = _installer_argv(repo)
        res = run_argv(argv, env=_env(), timeout=_TIMEOUT, cwd=repo)
    else:
        res, argv = _arm_mac(repo, run_argv, plist_dir)
    body = _body(res)
    if getattr(res, "timed_out", False) or getattr(res, "rc", 1) != 0:
        if _ELEVATION_RE.search(body):
            return "SCHED-ELEVATION-REQUIRED", "請以系統管理員身分重跑：" + " ".join(argv)
        return "SCHED-NO-CREDENTIAL", (f"安裝動作失敗（rc={getattr(res, 'rc', None)}）；"
                                       + " ".join(body.split())[:200])
    value = armed(run_argv, plist_dir=plist_dir)
    cred = value["credential"]
    if value["present"] is not True or cred.startswith(sched.NE_PREFIX) or not cred.strip():
        return "SCHED-NO-CREDENTIAL", f"任務現查拿不到憑證（{cred}）；不得宣稱任務已建立"
    return None, cred


def _ps_str(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def _push_register_argv(repo: Path, minutes: int) -> list[str]:
    """Windows：註冊 `AutoSDD_SI_Push`（互動登入型、非提權、隱藏視窗、每心跳一次、
    IgnoreNew、PT3H、不喚醒睡眠機器）；`-UserId` 取呼叫端
    `$env:USERDOMAIN\\$env:USERNAME`。動作參數的雙引號以 `[char]34` 組出，避免命令列轉義。
    先移除同名舊任務再註冊（重跑 `sched arm` 冪等）。"""
    script, R, join, _q = str(repo / "tools" / "selfimproving.py"), str(repo), os.path.join, _ps_str
    return _ps("; ".join([
        "$ErrorActionPreference = 'Stop'",
        r'$u = "$env:USERDOMAIN\$env:USERNAME"',
        f"$a = New-ScheduledTaskAction -Execute {_q(join(R,'.venv','Scripts','pythonw.exe'))}"
        " -Argument ([char]34 + "
        f"{_ps_str(script)} + [char]34 + ' push-run') -WorkingDirectory {_ps_str(str(repo))}",
        "$t = New-ScheduledTaskTrigger -Daily -At '00:00'",
        "$t.Repetition = (New-ScheduledTaskTrigger -Once -At '00:00' -RepetitionInterval "
        f"(New-TimeSpan -Minutes {int(minutes)}) "
        "-RepetitionDuration (New-TimeSpan -Days 1)).Repetition",
        "$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries "
        "-DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 3) "
        "-MultipleInstances IgnoreNew",
        "$s.DisallowStartIfOnBatteries = $false; $s.StopIfGoingOnBatteries = $false",
        "$p = New-ScheduledTaskPrincipal -UserId $u -LogonType Interactive -RunLevel Limited",
        f"if (Get-ScheduledTask -TaskName '{PUSH_LABEL}' -ErrorAction SilentlyContinue) "
        f"{{ Unregister-ScheduledTask -TaskName '{PUSH_LABEL}' -Confirm:$false }}",
        f"Register-ScheduledTask -TaskName '{PUSH_LABEL}' -Action $a -Trigger $t -Settings $s "
        "-Principal $p | Out-Null"]))


def _expected_user() -> str | None:
    dom, name = os.environ.get("USERDOMAIN"), os.environ.get("USERNAME")
    return f"{dom}\\{name}" if dom and name else None


def _same_user(a: str | None, b: str | None) -> bool:
    """帳號比對：不分大小寫；兩邊都帶網域才比網域（`Principal.UserId` 對本機帳號可能不帶網域）。"""
    if not a or not b:
        return False
    (da, _, na), (db, _, nb) = (x.rpartition("\\") for x in (a.lower(), b.lower()))
    return na == nb and (not da or not db or da == db)


def _session_argv() -> list[str]:
    """Windows：身分現查一次問完（SID 比對，審查 F-15／TCS-P7 E-25）：互動桌面（`explorer.exe`）
    擁有者的帳號與 SID（以另一個管理員帳號提權執行時，環境變數是那個管理員，桌面擁有者仍是真正
    登入的使用者）、本指令行程的 SID、已安裝的巡邏任務主體的 SID（不存在則無該行）。"""
    sid = "[Security.Principal.SecurityIdentifier]"
    return _ps("$cur = [System.Diagnostics.Process]::GetCurrentProcess().SessionId; "
               "'SESSIONID=' + $cur; "
               "Get-CimInstance Win32_Process -Filter \"Name='explorer.exe'\" | "
               "Where-Object { $_.SessionId -eq $cur } | ForEach-Object { "
               "$n = $_ | Invoke-CimMethod -MethodName GetOwner; "
               "$s = $_ | Invoke-CimMethod -MethodName GetOwnerSid; "
               "if ($n -and $n.User) { 'NAME=' + $n.Domain + '\\' + $n.User }; "
               "if ($s -and $s.Sid) { 'OWNERSID=' + $s.Sid } }; "
               "'MINESID=' + [Security.Principal.WindowsIdentity]::GetCurrent().User.Value; "
               f"$p = Get-ScheduledTask -TaskName '{LABEL}' -ErrorAction SilentlyContinue; "
               "if ($p) { try { 'PATROLSID=' + (New-Object Security.Principal.NTAccount("
               f"$p.Principal.UserId)).Translate({sid}).Value }} catch {{}} }}")


def _session(run_argv) -> dict:
    """`_session_argv` 的結果：`OWNERSIDS`／`NAMES`（本行程工作階段內每個 `explorer.exe` 的擁有者，
    可多筆）加 `SESSIONID`、`MINESID`、`PATROLSID`；量不到＝空 dict（呼叫端 fail-closed，E-38）。"""
    try:
        res = run_argv(_session_argv(), env=_env(), timeout=30, cwd=None)
    except Exception:  # noqa: BLE001
        return {}
    if getattr(res, "rc", 1) != 0:
        return {}
    out: dict = {"OWNERSIDS": [], "NAMES": []}
    for line in (getattr(res, "out", "") or "").splitlines():
        key, _, val = line.strip().partition("=")
        if not val.strip():
            continue
        if key == "OWNERSID":
            out["OWNERSIDS"].append(val.strip())
        elif key == "NAME":
            out["NAMES"].append(val.strip())
        else:
            out[key] = val.strip()
    return out


def _rollback_push(repo: Path, run_argv, plist_dir: Path | None, win: bool, why: str) -> str:
    """註冊後驗證失敗：同一呼叫內移除並現查不見，才說「已回復為未安裝」（審查 F-15）。"""
    _gone(repo, run_argv, plist_dir, win, PUSH_LABEL)
    gone = _push_value(run_argv, plist_dir)["present"] is False
    if gone:
        (si_events.si_dir() / "push" / "armed.json").unlink(missing_ok=True)
    return f"{why}；" + ("推送任務已回復為未安裝" if gone else
                         "回復失敗：推送任務可能仍存在，請手動 sched disarm --push-only")


def _arm_push(repo: Path, run_argv, plist_dir: Path | None, win: bool, minutes: int
              ) -> tuple[str | None, str]:
    """推送任務安裝並驗證：回（失敗碼或 None, 詳情或憑證值）；憑證是值（NextRunTime／
    mac 的 rc＋plist）。驗證失敗一律回復成未安裝；以另一個帳號提權執行（桌面擁有者與目前使用者
    不同）時拒絕註冊——推送任務必須屬於登入使用者，才拿得到他的憑證保管庫。"""
    want, who = _expected_user(), {}
    record, why_not = arm_record(repo)  # 乙類鍵（憑證輔助程式、CA、ssh 命令）的有效值，E-48
    if record is None:  # 在 repo 層出現、或憑證輔助程式不在安全清單：不註冊、不留 armed.json
        return "SCHED-PUSH-CONFIG-UNSAFE", (
            "git 設定含不允許的項目（憑證輔助程式請改用 manager 或系統鑰匙圈，"
            f"且這類設定不可放在 repo 層），請修正後重跑（{why_not}）")
    if win:
        who = _session(run_argv)
        owners = set(who.get("OWNERSIDS") or [])
        if who.get("SESSIONID") in (None, "0") or len(owners) != 1:  # fail-closed（E-38）
            return "SCHED-PUSH-USER-MISMATCH", "無法判定當前互動工作階段的擁有者"
        owner, mine, patrol = next(iter(owners)), who.get("MINESID"), who.get("PATROLSID")
        if owner != mine or (patrol and owner != patrol):
            return "SCHED-PUSH-USER-MISMATCH", (
                "推送任務必須由互動登入的同一個使用者安裝；請以該使用者提權後的同一帳號重跑"
                f"（登入的使用者是 {(who.get('NAMES') or ['未知'])[0]}）")
        who["OWNERSID"] = owner
        res = run_argv(_push_register_argv(repo, minutes), env=_env(), timeout=_TIMEOUT, cwd=repo)
    else:
        res, _ = _arm_mac(repo, run_argv, plist_dir, label=PUSH_LABEL, verb="push-run", logs=False)
    body = _body(res)
    if getattr(res, "timed_out", False) or getattr(res, "rc", 1) != 0:
        if _ELEVATION_RE.search(body):
            return "SCHED-ELEVATION-REQUIRED", (
                "以系統管理員身分重跑 sched arm（任務主體仍為目前使用者的互動登入型）")
        return "SCHED-PUSH-TASK-FAILED", (f"推送任務註冊失敗（rc={getattr(res, 'rc', None)}）；"
                                          + " ".join(body.split())[:200]
                                          + "；先前的推送任務（若有）已被移除，不會保留")
    value = _push_value(run_argv, plist_dir)
    cred = value["credential"]
    if value["present"] is not True or cred.startswith(sched.NE_PREFIX) or not cred.strip():
        why = _rollback_push(repo, run_argv, plist_dir, win,
                             f"推送任務現查拿不到憑證（{cred}）；不得宣稱任務已建立")
        return "SCHED-NO-CREDENTIAL", why
    expect_sid = who.get("OWNERSID")  # 以 SID 比（本機帳號回讀常不帶網域）
    if win and ((expect_sid and value.get("sid") and value["sid"] != expect_sid)
                or (not (expect_sid and value.get("sid")) and want
                    and not _same_user(value["user"], want))):
        return "SCHED-PUSH-USER-MISMATCH", _rollback_push(
            repo, run_argv, plist_dir, win, "推送任務的使用者與互動登入的使用者不同")
    try:
        _write_armed(repo, record)
    except OSError as exc:
        why = _rollback_push(repo, run_argv, plist_dir, win,
                             f"armed.json 寫入失敗（{type(exc).__name__}）")
        return "SCHED-PUSH-TASK-FAILED", why
    return None, cred


def _write_armed(repo: Path, record: dict | None = None) -> None:
    """記下安裝當下的遠端網址、git 絕對路徑與乙類鍵的有效值 `config_pins`（`push/armed.json`）：
    守門之後比對網址、git 路徑與乙類鍵是否被改（審查 F-04、E-33、E-49），推送以記錄值釘定。"""
    cp = Git(repo).run("config", "--get", "remote.origin.url")
    url = cp.stdout.strip() if cp is not None and cp.returncode == 0 else ""
    url = re.sub(r"(://)[^/@\s]*@", r"\1", url)  # 去 userinfo（帳密不落地）
    doc = {"remote_url": url, "git": resolve_git(os.environ),
           "armed_at": sched.iso(sched.aware(datetime.now().astimezone())),
           "config_pins": dict(record or {})}
    path = si_events.si_dir() / "push" / "armed.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def _mac_env_detail() -> dict[str, str]:
    """macOS 推送任務帶進 launchd 的環境（現查輸出列出）：`PATH` 只列目錄個數與前 3 段。"""
    if sys.platform != "darwin":
        return {}
    dirs = [d for d in safe_path().split(os.pathsep) if d]
    return {"push_task_path": f"{len(dirs)}-dirs:" + os.pathsep.join(dirs[:3]),
            "push_task_si_dir": str(si_events.si_dir())}


def _remove_push_if_present(repo: Path, run_argv, plist_dir: Path | None, win: bool
                            ) -> tuple[str | None, str]:
    """`sched_auto_push=false`：現查任務存在才移除（回失敗碼或 None）。"""
    value = _push_value(run_argv, plist_dir)
    if value["present"] is False:
        return None, "-"
    _gone(repo, run_argv, plist_dir, win, PUSH_LABEL)
    after = _push_value(run_argv, plist_dir)
    if after["present"] is False:
        return None, "removed"
    return "SCHED-PUSH-TASK-FAILED", "sched_auto_push=false，但推送任務移除後現查仍在或無法確認"


def arm(repo: Path, run_argv=runner.run_argv, *, as_json: bool = False,
        plist_dir: Path | None = None, push_only: bool = False) -> tuple[int, str]:
    """安裝 OS 任務並以憑證（值）驗證；回 (rc, 輸出)。`sched_auto_push` 為 true 時另裝推送任務
    （與巡邏段獨立，互不牽連）；`push_only` 只裝推送任務。"""
    win = sys.platform.startswith("win")
    if not win and sys.platform != "darwin":
        return _reject(repo, "SCHED-NO-CREDENTIAL", "此平台沒有 OS 任務載具", as_json, "arm")
    params = _params(repo)
    enabled = params.get("sched_auto_push") is True
    minutes = params["sched_heartbeat_minutes"]
    if push_only:
        if not enabled:
            return _reject(repo, "SCHED-PUSH-OFF",
                           "sched_auto_push 為 false（預設關閉），不安裝推送任務。要開啟：先讀 "
                           "SOP〈自動推送（P7）〉的殘餘風險；再把 docs/06_quality/"
                           "SelfImproving_Protocol/params.json 的 sched_auto_push 改成 true "
                           "並提交（屬 T1／PRD 修訂的參數）；再重跑 sched arm --push-only",
                           as_json, "arm")
        code, detail = _arm_push(repo, run_argv, plist_dir, win, minutes)
        if code:
            return _reject(repo, code, detail, as_json, "arm")
        return _ok("arm", {"task": PUSH_LABEL, "push_task_credential": detail,
                           **_mac_env_detail()}, as_json)
    p_code, p_detail = _arm_patrol(repo, run_argv, plist_dir, win)
    s_code, s_detail = (_arm_push(repo, run_argv, plist_dir, win, minutes) if enabled
                        else _remove_push_if_present(repo, run_argv, plist_dir, win))
    patrol_line = "巡邏任務：" + (p_code or "已建立")
    push_line = "推送任務：" + (s_code or ("已建立" if enabled else "未啟用"))
    if p_code:
        extra = f"（push_task_credential={s_detail}）" if enabled and not s_code else ""
        both = f"{p_detail}；{patrol_line}；{push_line}{extra}"
        return _reject(repo, p_code, both, as_json, "arm")
    if s_code:
        note = f"{s_detail}；巡邏任務已安裝（憑證 {p_detail}）"
        return _reject(repo, s_code, note, as_json, "arm")
    detail = {"task": LABEL, "credential": p_detail}
    if enabled:
        detail.update(push_task_credential=s_detail, **_mac_env_detail())
    else:
        detail["push"] = "自動推送未啟用，未安裝推送任務"
    return _ok("arm", detail, as_json)


# ── disarm ────────────────────────────────────────────────────────────────────
def _gone(repo: Path, run_argv, plist_dir: Path | None, win: bool, label: str):
    """執行移除動作；回（rc 為 0 或 launchctl 的「不存在」rc, 輸出, argv）。"""
    argv = _remove_argv(label) if win else _launchctl("bootout", f"gui/{_uid()}/{label}")
    res = run_argv(argv, env=_env(), timeout=_TIMEOUT, cwd=repo)
    ok = getattr(res, "rc", 1) == 0 or (not win and getattr(res, "rc", 1) in (3, 113, 36))
    return ok, _body(res), argv


def _disarm_one(repo: Path, run_argv, plist_dir: Path | None, win: bool, label: str
                ) -> tuple[str, str]:
    """移除一支任務並現查：回（'gone'｜'elevation'｜'present'｜'unknown', 說明）。"""
    ok, body, argv = _gone(repo, run_argv, plist_dir, win, label)
    if not ok and _ELEVATION_RE.search(body):
        return "elevation", "請以系統管理員身分重跑：" + " ".join(argv)
    value = (_push_value(run_argv, plist_dir) if label == PUSH_LABEL
             else armed(run_argv, plist_dir=plist_dir))
    if value["present"] is False:
        if not win:
            try:
                _plist_path(plist_dir, label).unlink()
            except OSError:
                pass
        return "gone", "-"
    if value["present"]:
        return "present", f"移除後現查任務仍在；{label} 未確認已移除"
    return "unknown", f"移除後無法確認（{value['credential']}）；{label} 未確認已移除"


def disarm(repo: Path, run_argv=runner.run_argv, *, as_json: bool = False,
           plist_dir: Path | None = None, push_only: bool = False) -> tuple[int, str]:
    """移除 `AutoSDD_SI_Patrol` 與 `AutoSDD_SI_Push` 兩支並驗證都真的不見（不是安裝器的整組
    解除）；`push_only` 只移除推送任務。"""
    win = sys.platform.startswith("win")
    if not win and sys.platform != "darwin":
        return _reject(repo, "SCHED-NO-CREDENTIAL", "此平台沒有 OS 任務載具", as_json, "disarm")
    labels = (PUSH_LABEL,) if push_only else (LABEL, PUSH_LABEL)
    got = {lb: _disarm_one(repo, run_argv, plist_dir, win, lb) for lb in labels}
    for state, detail in got.values():
        if state == "elevation":
            return _reject(repo, "SCHED-ELEVATION-REQUIRED", detail, as_json, "disarm")
    for state, detail in got.values():
        if state != "gone":
            return _reject(repo, "SCHED-NO-CREDENTIAL", detail, as_json, "disarm")
    ok = {"task": PUSH_LABEL if push_only else LABEL, "present": False}
    if not push_only:
        ok["push_task_present"] = False
    return _ok("disarm", ok, as_json)


def run(repo: Path, cmd: str, as_json: bool, push_only: bool = False) -> tuple[int, str]:
    """入口 `sched arm|disarm` 的分派（授權閘已在入口通過）。"""
    if cmd == "arm":
        return arm(repo, runner.run_argv, as_json=as_json, push_only=push_only)
    return disarm(repo, runner.run_argv, as_json=as_json, push_only=push_only)
