"""EndBoundary 自刪探針（DES RealVerify_SideEffect_Isolation §0.4-4／D-5）：只量測，不接任何閘門。

問題：Windows 工作排程器對「從未執行就過了 `EndBoundary`、且 `DeleteExpiredTaskAfter=PT0S`」的一次性
工作（含被停用者），多久之後會把它自己刪掉？DES 的 OS 自毀（D-5）與 E2E-SE-04(c) 的判準來源。

做法：登記一支停用的 `AutoSDD_RV_probe_<id>`（Action＝`pythonw -c pass`，永不干擾任何真工作）→
輪詢 `Get-ScheduledTask` 直到消失或逾時 → finally 一律解除登記並回讀確認。登記**之前**先寫 L2 帳列
（`~/.autosdd/realverify_leases/<run_id>.jsonl`，格式同 DES §5.1；本棒時 `leases.py` 尚未落地，
所以這裡自帶兩個最小寫入函式，格式相容，S5 落地後以 `leases.replay` 讀得懂）。

末行 `ENDBOUNDARY_VERDICT=deleted seconds=<N>`｜`kept after=<N>`｜`error reason=<…>`，rc 恆 0。
用法：python tools/probe/sandbox_scope_endboundary.py [--max-wait-sec 900] [--poll-sec 15]
（超過 5 分鐘：以 `sessionctl runlong` 背景跑、`waitfor` 分段等）。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import win_spawn  # noqa: E402 — 無 console 載具的 SSOT（quiet_python）

PROBE_PREFIX = "AutoSDD_RV_probe_"
LEASE_DIR_PARTS = (".autosdd", "realverify_leases")
#: 首次觸發與 EndBoundary 相距（秒）：EndBoundary 必須晚於 StartBoundary，排程器以分鐘為粒度。
START_AHEAD_SEC = 60
END_AFTER_START_SEC = 60
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _q(text: str) -> str:
    return text.replace("'", "''")


def register_script(name: str, start: datetime, end: datetime) -> str:
    """登記腳本（PowerShell 5.1）。EndBoundary／DeleteExpiredTaskAfter 以屬性賦值寫入。"""
    python = _q(win_spawn.quiet_python())  # 載具走 SSOT（無 console 的 pythonw）
    return (
        "$ErrorActionPreference = 'Stop'\n"
        f"$a = New-ScheduledTaskAction -Execute '{python}' -Argument '-c pass'\n"
        f"$t = New-ScheduledTaskTrigger -Once -At '{start:%Y-%m-%d %H:%M:%S}'\n"
        f"$t.EndBoundary = '{end:%Y-%m-%dT%H:%M:%S}'\n"
        "$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries "
        "-DontStopIfGoingOnBatteries\n"
        "$s.DeleteExpiredTaskAfter = 'PT0S'\n"
        "$p = New-ScheduledTaskPrincipal -UserId \"$env:USERDOMAIN\\$env:USERNAME\" "
        "-LogonType Interactive -RunLevel Limited\n"
        f"Register-ScheduledTask -TaskName '{_q(name)}' -Action $a -Trigger $t -Settings $s "
        "-Principal $p -Force | Out-Null\n"
        f"Disable-ScheduledTask -TaskName '{_q(name)}' | Out-Null\n"
        f"(Export-ScheduledTask -TaskName '{_q(name)}')\n")


def exists_script(name: str) -> str:
    return (f"if (Get-ScheduledTask -TaskName '{_q(name)}' -ErrorAction SilentlyContinue) "
            "{ 'PRESENT' } else { 'ABSENT' }\n")


def unregister_script(name: str) -> str:
    return (f"Unregister-ScheduledTask -TaskName '{_q(name)}' -Confirm:$false "
            "-ErrorAction SilentlyContinue\n" + exists_script(name))


def run_ps(script: str, timeout: int = 90) -> tuple[int, str]:
    """以 powershell.exe（5.1）跑一段腳本；BOM＋CRLF 落檔（同 planner.run_powershell）。"""
    if os.name != "nt":  # 作用域內平台守衛：powershell.exe（5.1）是 Windows 專屬載具
        return 127, "not windows"
    folder = Path(tempfile.mkdtemp(prefix="autosdd_rvprobe_"))
    path = folder / "run.ps1"
    path.write_bytes(("﻿" + script.replace("\r\n", "\n").replace("\n", "\r\n")).encode("utf-8"))
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(path)],
            capture_output=True, encoding="utf-8", errors="replace", timeout=timeout,
            check=False, creationflags=_NO_WINDOW)
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, str(exc)
    finally:
        try:
            path.unlink()
            folder.rmdir()
        except OSError:
            pass


def _ledger_path(run_id: str) -> Path:
    return Path.home().joinpath(*LEASE_DIR_PARTS) / f"{run_id}.jsonl"


def ledger_append(run_id: str, ident: str, state: str, undo: str, now: datetime) -> None:
    path = _ledger_path(run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"at": now.astimezone().isoformat(timespec="seconds"), "kind": "sched_job",
           "ident": ident, "undo": undo, "owner_pid": os.getpid(), "owner_started": "",
           "expires_at": None, "state": state}
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _python_w() -> str:
    return win_spawn.quiet_python()


def _register_via_product(name: str, start: datetime, end: datetime, run_fn) -> tuple[int, str]:
    """E2E 形態：走產品的登記原語 `engine_resume_job.arm_oneshot(expire_at=…)`（沙盒前綴工作名），
    再停用並匯出 XML 取證。Action＝`pythonw -c pass`（無害）。"""
    import engine_resume_job as erj  # noqa: PLC0415 — 只有這個模式才需要產品原語

    rc, cred = erj.arm_oneshot(name, [_python_w(), "-c", "pass"], os.getcwd(), start,
                               expire_at=end)
    if rc != 0:
        return rc, f"arm_oneshot rc={rc}"
    run_fn(f"Disable-ScheduledTask -TaskName '{_q(name)}' | Out-Null\n")
    rc2, xml = run_fn(f"Export-ScheduledTask -TaskName '{_q(name)}'\n")
    return rc2, f"{cred}\n{xml}"


def measure(max_wait: int, poll: int, *, now_fn=datetime.now, sleep_fn=time.sleep,
            run_fn=run_ps, via_product: bool = False) -> tuple[str, dict]:
    """量一次。回 `(判決, 細節)`；finally 一律解除登記。時鐘與 PowerShell 皆可注入。"""
    run_id = f"probe-{uuid.uuid4().hex[:8]}"
    name = f"{PROBE_PREFIX if not via_product else 'AutoSDD_RV_sbx_s1e2e_'}{run_id.split('-')[1]}"
    start = now_fn() + timedelta(seconds=START_AHEAD_SEC)
    end = start + timedelta(seconds=END_AFTER_START_SEC)
    info: dict = {"name": name, "start": f"{start:%H:%M:%S}", "end_boundary": f"{end:%H:%M:%S}"}
    ledger_append(run_id, name, "intent", f"Unregister-ScheduledTask {name}", now_fn())
    try:
        if via_product:
            rc, out = _register_via_product(name, start.astimezone(), end.astimezone(), run_fn)
        else:
            rc, out = run_fn(register_script(name, start, end))
        if rc != 0:
            return "error", {**info, "reason": f"register rc={rc}: {out[:200]}"}
        ledger_append(run_id, name, "made", f"Unregister-ScheduledTask {name}", now_fn())
        info["xml_has_end_boundary"] = "EndBoundary" in out
        info["xml_has_delete_expired"] = "DeleteExpiredTaskAfter" in out
        deadline = time.monotonic() + max_wait
        t_end = end
        while time.monotonic() < deadline:
            sleep_fn(poll)
            rc, out = run_fn(exists_script(name))
            if rc == 0 and "ABSENT" in out:
                return "deleted", {**info, "seconds": int((now_fn() - t_end).total_seconds())}
        return "kept", {**info, "after": max_wait}
    finally:
        rc, out = run_fn(unregister_script(name))
        ledger_append(run_id, name, "revoked" if "ABSENT" in out else "unverified",
                      f"Unregister-ScheduledTask {name}", now_fn())
        if "ABSENT" in out:
            ledger_append(run_id, name, "closed", "", now_fn())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--max-wait-sec", type=int, default=900)
    ap.add_argument("--poll-sec", type=int, default=15)
    ap.add_argument("--via-product", action="store_true",
                    help="走產品登記原語 arm_oneshot(expire_at=…)（E2E-S1-02），不是探針自帶腳本")
    opts = ap.parse_args(argv)
    if os.name != "nt":
        print("ENDBOUNDARY_VERDICT=error reason=not_windows")
        return 0
    verdict, info = measure(opts.max_wait_sec, opts.poll_sec, via_product=opts.via_product)
    print(json.dumps(info, ensure_ascii=False))
    detail = " ".join(f"{k}={info[k]}" for k in ("seconds", "after", "reason") if k in info)
    print(f"ENDBOUNDARY_VERDICT={verdict} {detail}".rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
