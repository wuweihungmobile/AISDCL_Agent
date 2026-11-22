"""排程後端與排程批次列舉快取（DES §4.5、§5.2；REQ-WP-10／26）。

兩件事、一個家：
  · 後端（`WindowsBackend`／`LaunchdBackend`）：註冊一次性工作並**當場回讀憑證**（Windows＝
    排程器自報的 `NextRunTime` 值；macOS＝launchd rc＋plist 路徑，launchd 從不報下次時刻）、
    撤銷並驗證真的不見、
    以**一次**批次列舉取回 `task_prefix` 下全部工作。Windows 的 PowerShell 載具、單引號跳脫、
四項補跑
    設定一律沿用 `session_resume_planner`（排程知識只有一個家，本檔不抄第二份）。
  · 快取 `trace_dir()/openitems/sched_cache.json`：完成閘只讀它、不開子行程；
    逾 TTL、前綴／平台對不上、
    讀不到一律回 `None`（＝量不到，fold 依帳本視為有效，觸發後的對帳會抓到）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from lib import endurance_env, win_spawn

from .ledger import parse_ts

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_LIST_SCRIPT = (
    "Get-ScheduledTask -TaskName '{prefix}*' -ErrorAction SilentlyContinue | ForEach-Object {{ "
    "$i = $_ | Get-ScheduledTaskInfo; $_.TaskName + [char]9 + "
    "$(if ($i.NextRunTime) {{ $i.NextRunTime.ToString('o') }} else {{ '' }}) }}\n")
_UNREGISTER_SCRIPT = (
    "Unregister-ScheduledTask -TaskName '{task}' -Confirm:$false -ErrorAction SilentlyContinue\n"
    "if (Get-ScheduledTask -TaskName '{task}' -ErrorAction SilentlyContinue) "
    "{{ Write-Output 'STILL-PRESENT' }} else {{ Write-Output 'REMOVED' }}\n")


def cache_path() -> Path:
    return endurance_env.trace_dir() / "openitems" / "sched_cache.json"


def planner():
    tools = str(Path(__file__).resolve().parents[2])
    if tools not in sys.path:
        sys.path.insert(0, tools)
    import session_resume_planner  # noqa: PLC0415 — lazy：planner 會被 hook 鏈 import，模組層易成環
    return session_resume_planner


class WindowsBackend:
    """Windows：`powershell.exe`（5.1）＋ planner 的註冊腳本骨架。憑證＝`NextRunTime` **值**。"""

    name = "schtasks"

    def register(self, task: str, at: datetime, argv: list[str], cwd: str, *,
                 expire_at: datetime | None = None) -> str | None:
        pl = planner()
        q = pl._ps_single_quote
        # 沙盒目標的 OS 自毀（DES S3、§5.4）：EndBoundary＋DeleteExpiredTaskAfter；正式目標兩段皆空
        from engine_resume_job import (
            expiry_ps,  # noqa: PLC0415 — 頂層名；planner() 已把 tools/lib 放進 sys.path
        )
        end_trigger, end_settings = expiry_ps(at.astimezone(), expire_at)
        # 載具一律由 SSOT 算（pythonw、無 console）；argv[0] 只是呼叫端的同源預填，不另信。
        python = q(win_spawn.quiet_python())
        argument = " ".join(f'"{a}"' for a in argv[1:])
        stamp = at.astimezone().strftime("%Y-%m-%dT%H:%M:%S")  # 排程器吃本地 naive 時刻
        script = (
            "$ErrorActionPreference = 'Stop'\n"
            f"$action = New-ScheduledTaskAction -Execute '{python}'-Argument '{q(argument)}' "
            f"-WorkingDirectory '{q(cwd)}'\n"
            f"$trigger = New-ScheduledTaskTrigger -Once -At ([datetime]'{stamp}')\n{end_trigger}"
            f"$settings = {pl._SCHTASKS_SETTINGS}\n{end_settings}"
            f"$principal = {pl._SCHTASKS_PRINCIPAL}\n"
            f"$common = @{{TaskName='{q(task)}'; Action=$action; Trigger=$trigger; "
            "Settings=$settings; Force=$true}\n"
            "try { Register-ScheduledTask @common -Principal $principal -EA Stop | Out-Null }\n"
            "catch { Register-ScheduledTask @common | Out-Null }\n"
            f"{pl._EVIDENCE_TEMPLATE.format(task=q(task))}\n")
        proc = pl.run_powershell(script)
        moment = pl.next_run_time(proc.stdout or "")
        return moment if proc.returncode == 0 and moment else None

    def unregister(self, task: str) -> bool:
        pl = planner()
        proc = pl.run_powershell(_UNREGISTER_SCRIPT.format(task=pl._ps_single_quote(task)))
        return "REMOVED" in (proc.stdout or "")

    def list_tasks(self, prefix: str) -> dict[str, str] | None:
        pl = planner()
        proc = pl.run_powershell(_LIST_SCRIPT.format(prefix=pl._ps_single_quote(prefix)))
        if proc.returncode != 0:
            return None
        out: dict[str, str] = {}
        for line in (proc.stdout or "").splitlines():
            name, _, nxt = line.strip().partition("\t")
            if name.startswith(prefix):
                out[name] = nxt.strip()
        return out


class LaunchdBackend:
    """macOS：使用者網域 LaunchAgent（`StartCalendarInterval`）。憑證＝`launchctl print` rc 0
    ＋ plist 路徑
    （launchd 從不報下次時刻，所以判準不靠它；DES §3.3 兩平台同一張表）。"""

    name = "launchd"

    def _domain(self) -> str:
        return f"gui/{os.getuid()}" if hasattr(os, "getuid") else ""

    def _plist(self, task: str) -> Path:
        return Path.home() / "Library" / "LaunchAgents" / f"{task}.plist"

    def _launchctl(self, *args: str) -> tuple[int, str]:
        if sys.platform != "darwin":  # 鐵律三：launchctl 只存在於 macOS，別的平台明說做不到
            return 127, "launchctl 只在 macOS 成立"
        try:
            p = subprocess.run(["launchctl", *args], capture_output=True, text=True, timeout=60,
                               encoding="utf-8", errors="replace", check=False)
        except (OSError, subprocess.SubprocessError) as exc:
            return 127, str(exc)
        return p.returncode, (p.stdout or "") + (p.stderr or "")

    def register(self, task: str, at: datetime, argv: list[str], cwd: str, *,
                 expire_at: datetime | None = None) -> str | None:
        # launchd 無 EndBoundary 對等物，`expire_at` 刻意忽略（DES 誠實劃界：靠 L1 首判＋L2 清掃）
        local = at.astimezone()
        items = "".join(f"<string>{a}</string>" for a in argv)
        plist = (
            '<?xml version="1.0" encoding="UTF-8"?><plist version="1.0"><dict>'
            f"<key>Label</key><string>{task}</string>"
            f"<key>ProgramArguments</key><array>{items}</array>"
            f"<key>WorkingDirectory</key><string>{cwd}</string>"
            "<key>StartCalendarInterval</key><dict>"
            f"<key>Month</key><integer>{local.month}</integer>"
            f"<key>Day</key><integer>{local.day}</integer>"
            f"<key>Hour</key><integer>{local.hour}</integer>"
            f"<key>Minute</key><integer>{local.minute}"
            "</integer></dict></dict></plist>")
        path = self._plist(task)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(plist, encoding="utf-8")
        self._launchctl("bootout", f"{self._domain()}/{task}")
        rc, _ = self._launchctl("bootstrap", self._domain(), str(path))
        rc2, _ = self._launchctl("print", f"{self._domain()}/{task}")
        return f"launchd rc={rc2} label={task} plist={path}" if rc == 0 and rc2 == 0 else None

    def unregister(self, task: str) -> bool:
        self._launchctl("bootout", f"{self._domain()}/{task}")
        self._plist(task).unlink(missing_ok=True)
        return self._launchctl("print", f"{self._domain()}/{task}")[0] != 0

    def list_tasks(self, prefix: str) -> dict[str, str] | None:
        rc, out = self._launchctl("list")
        if rc != 0:
            return None
        return {cols[-1]: "" for line in out.splitlines() if (cols := line.split())
                and cols[-1].startswith(prefix)}


def select_backend(platform_name: str | None = None):
    """平台對應的後端；沒有載具（例如 Linux）回 `None`——呼叫端必須 fail-loud，不假裝排程成功。"""
    plat = platform_name or sys.platform
    if plat.startswith("win"):
        return WindowsBackend()
    return LaunchdBackend() if plat == "darwin" else None


def refresh(params: dict, backend, now: datetime) -> dict[str, str] | None:
    """一次批次列舉→寫快取；列舉失敗（量不到）回 `None` 且**不覆蓋**舊快取。"""
    if backend is None:
        return None
    tasks = backend.list_tasks(params["task_prefix"])
    if tasks is None:
        return None
    path = cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"at": now.isoformat(timespec="seconds"), "platform": backend.name,
            "prefix": params["task_prefix"], "tasks": tasks}
    path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")  # 撕裂讀＝量不到
    return tasks


def note(params: dict, backend, now: datetime, *, add: dict[str, str] | None = None,
         drop: str | None = None, path: Path | None = None) -> bool:
    """寫入排程的一方同步快取（`drive` 登記成功、重掛作廢舊工作之後）。

    只併進**仍有效**（`read` 認得：TTL 內、前綴相符）且平台相符的快取；沒有有效快取（沒檔、逾
    TTL、壞檔）⇒ 什麼都不做、回 False——那時完成閘讀到的本來就是「量不到」，fold 依帳本判
    （量不到 ≠ 存在，不得把「量不到」寫成「存在」，也不憑空造一份快取）。`at`（拍快取的時刻）
    原樣保留，不延長 TTL。
    """
    target = path or cache_path()
    tasks = read(params, now, target)
    if tasks is None:
        return False
    try:
        body = json.loads(target.read_text(encoding="utf-8"))
        if body.get("platform") != getattr(backend, "name", body.get("platform")):
            return False
        body["tasks"] = {**{k: v for k, v in tasks.items() if k != drop}, **(add or {})}
        target.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    except (OSError, ValueError, AttributeError, TypeError):
        return False
    return True


def read(params: dict, now: datetime, path: Path | None = None) -> dict[str, str] | None:
    """快取內容；逾 `sched_cache_ttl_seconds`、前綴對不上、壞檔、不存在一律回 `None`（量不到）。"""
    try:
        body = json.loads((path or cache_path()).read_text(encoding="utf-8"))
        stamp = parse_ts(body["at"])
        fresh = stamp is not None and 0 <= (now - stamp).total_seconds() <= params[
            "sched_cache_ttl_seconds"]
        if fresh and body["prefix"] == params["task_prefix"] and isinstance(body["tasks"], dict):
            return body["tasks"]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def exists_fn(params: dict, now: datetime, path: Path | None = None):
    """餵給 `fold` 的 `sched_exists`：快取可用才答真假，否則恆 `None`。"""
    tasks = read(params, now, path)
    return (lambda task: task in tasks) if tasks is not None else (lambda _task: None)
