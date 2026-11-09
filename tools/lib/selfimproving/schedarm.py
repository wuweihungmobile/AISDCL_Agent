"""SelfImproving OS 任務載具封裝：`sched arm`／`sched disarm`（TCS-SelfImproving-P4 R161 (d)(e)）。

能力類別 `exec`：外呼一律經注入的 `run_argv`（預設 `runner.run_argv`，明示環境）。Windows＝呼叫
`tools/install_windows_nightly.ps1`（整組任務）並以 `Get-ScheduledTask … NextRunTime` 為
憑證；macOS＝
自寫 launchd plist 並以 `launchctl` rc 與 plist 回讀為憑證（macOS 未實機驗證）。**憑證是值，不是
rc**：取不到憑證＝rc 1，輸出不得宣稱已排程。本檔不 import、不改續航排程後端；啟用旗標（`sched.set`）
與 OS 任務相互獨立：本檔不寫任何事件。
單平台外部執行檔（`powershell.exe`、`schtasks`、`launchctl`）的 argv 字面只住 `sys.platform` 守衛
分支內（根 CLAUDE.md 鐵律三）。
"""

from __future__ import annotations

import json
import os
import plistlib
import re
import sys
from pathlib import Path

from . import events as si_events
from . import params as si_params
from . import runner, sched
from . import writeverbs as wv

LABEL = sched.ARMED_TASK
_ENV_KEYS = ("PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME", "USERPROFILE", "APPDATA",
             "LOCALAPPDATA", "USERNAME", "USERDOMAIN", "LANG", "LC_ALL")
_ELEVATION_RE = re.compile(r"(?i)access is denied|administrator|elevat|拒絕存取|系統管理員|提權")
_INSTALLER_REL = "tools/install_windows_nightly.ps1"
_TICK_REL = "tools/si_patrol_tick.ps1"
_TIMEOUT = 180


def _env() -> dict[str, str]:
    return {k: os.environ[k] for k in _ENV_KEYS if k in os.environ}


def _heartbeat_minutes(repo: Path) -> int:
    return wv.params_for(repo, *si_params.SCHED_KEYS)["sched_heartbeat_minutes"]


def _installer_argv(repo: Path) -> list[str]:
    """Windows：呼叫安裝器的 argv（單平台字面，只在 Windows 分支內組出）。"""
    if sys.platform.startswith("win"):
        return ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                str(repo / _INSTALLER_REL)]
    return []


def _remove_argv() -> list[str]:
    if sys.platform.startswith("win"):
        return ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                f"Unregister-ScheduledTask -TaskName '{LABEL}' -Confirm:$false"]
    return []


def _plist_path(plist_dir: Path | None) -> Path:
    return (plist_dir or Path.home() / "Library" / "LaunchAgents") / f"{LABEL}.plist"


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
def _mac_value(run_argv, plist_dir: Path | None) -> dict:
    """macOS 憑證＝`launchctl list` rc 與 plist 回讀（launchd 從不報下次幾點跑）。"""
    res = run_argv(_launchctl("list", LABEL), env=_env(), timeout=30, cwd=None)
    if getattr(res, "timed_out", False):
        return {"task": LABEL, "present": None, "credential": sched.NE_PREFIX + "timeout"}
    rc = getattr(res, "rc", None)
    if rc == 113:
        return {"task": LABEL, "present": False, "credential": "-"}
    if rc != 0:
        return {"task": LABEL, "present": None, "credential": f"{sched.NE_PREFIX}rc-{rc}"}
    try:
        with open(_plist_path(plist_dir), "rb") as fh:
            interval = plistlib.load(fh).get("StartInterval")
    except (OSError, ValueError):
        interval = None
    if not interval:
        return {"task": LABEL, "present": None,
                "credential": sched.NE_PREFIX + "plist-unreadable"}
    return {"task": LABEL, "present": True,
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


# ── arm ───────────────────────────────────────────────────────────────────────
def _write_plist(repo: Path, plist_dir: Path | None) -> Path:
    si = si_events.si_dir()
    logs = si / "patrol"
    logs.mkdir(parents=True, exist_ok=True)
    plist = {"Label": LABEL, "RunAtLoad": False,
             "StartInterval": _heartbeat_minutes(repo) * 60,
             "ProgramArguments": [str(repo / ".venv" / "bin" / "python"),
                                  str(repo / "tools" / "selfimproving.py"), "patrol",
                                  "--repo", str(repo)],
             "WorkingDirectory": str(repo),
             "StandardOutPath": str(logs / "launchd.out.log"),
             "StandardErrorPath": str(logs / "launchd.err.log")}
    path = _plist_path(plist_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as fh:
        plistlib.dump(plist, fh)
    return path


def _arm_mac(repo: Path, run_argv, plist_dir: Path | None):
    path = _write_plist(repo, plist_dir)
    uid = _uid()
    run_argv(_launchctl("bootout", f"gui/{uid}/{LABEL}"), env=_env(), timeout=30, cwd=None)
    res = run_argv(_launchctl("bootstrap", f"gui/{uid}", str(path)), env=_env(), timeout=30,
                   cwd=None)
    return res, _launchctl("bootstrap", f"gui/{uid}", str(path))


def arm(repo: Path, run_argv=runner.run_argv, *, as_json: bool = False,
        plist_dir: Path | None = None) -> tuple[int, str]:
    """安裝 OS 任務並以憑證（值）驗證；回 (rc, 輸出)。"""
    win = sys.platform.startswith("win")
    if not win and sys.platform != "darwin":
        return _reject(repo, "SCHED-NO-CREDENTIAL", "此平台沒有 OS 任務載具", as_json, "arm")
    if win:
        argv = _installer_argv(repo)
        res = run_argv(argv, env=_env(), timeout=_TIMEOUT, cwd=repo)
    else:
        res, argv = _arm_mac(repo, run_argv, plist_dir)
    body = _body(res)
    if getattr(res, "timed_out", False) or getattr(res, "rc", 1) != 0:
        if _ELEVATION_RE.search(body):
            hint = "請以系統管理員身分重跑：" + " ".join(argv)
            return _reject(repo, "SCHED-ELEVATION-REQUIRED", hint, as_json, "arm")
        return _reject(repo, "SCHED-NO-CREDENTIAL",
                       f"安裝動作失敗（rc={getattr(res, 'rc', None)}）；"
                       + " ".join(body.split())[:200],
                       as_json, "arm")
    value = armed(run_argv, plist_dir=plist_dir)
    cred = value["credential"]
    if value["present"] is not True or cred.startswith(sched.NE_PREFIX) or not cred.strip():
        return _reject(repo, "SCHED-NO-CREDENTIAL",
                       f"任務現查拿不到憑證（{cred}）；不得宣稱任務已建立", as_json, "arm")
    return _ok("arm", {"task": LABEL, "credential": cred}, as_json)


# ── disarm ────────────────────────────────────────────────────────────────────
def disarm(repo: Path, run_argv=runner.run_argv, *, as_json: bool = False,
           plist_dir: Path | None = None) -> tuple[int, str]:
    """只移除 `AutoSDD_SI_Patrol` 一支並驗證它真的不見（不是安裝器的整組解除）。"""
    win = sys.platform.startswith("win")
    if not win and sys.platform != "darwin":
        return _reject(repo, "SCHED-NO-CREDENTIAL", "此平台沒有 OS 任務載具", as_json, "disarm")
    if win:
        argv = _remove_argv()
    else:
        argv = _launchctl("bootout", f"gui/{_uid()}/{LABEL}")
    res = run_argv(argv, env=_env(), timeout=_TIMEOUT, cwd=repo)
    body = _body(res)
    gone_ok = getattr(res, "rc", 1) == 0 or (not win and getattr(res, "rc", 1) in (3, 113, 36))
    if not gone_ok and _ELEVATION_RE.search(body):
        hint = "請以系統管理員身分重跑：" + " ".join(argv)
        return _reject(repo, "SCHED-ELEVATION-REQUIRED", hint, as_json, "disarm")
    value = armed(run_argv, plist_dir=plist_dir)
    if value["present"] is False:
        if not win:
            try:
                _plist_path(plist_dir).unlink()
            except OSError:
                pass
        return _ok("disarm", {"task": LABEL, "present": False}, as_json)
    why = "移除後現查任務仍在" if value["present"] else f"移除後無法確認（{value['credential']}）"
    return _reject(repo, "SCHED-NO-CREDENTIAL", f"{why}；{LABEL} 未確認已移除", as_json, "disarm")


def run(repo: Path, cmd: str, as_json: bool) -> tuple[int, str]:
    """入口 `sched arm|disarm` 的分派（授權閘已在入口通過）。"""
    if cmd == "arm":
        return arm(repo, runner.run_argv, as_json=as_json)
    return disarm(repo, runner.run_argv, as_json=as_json)
