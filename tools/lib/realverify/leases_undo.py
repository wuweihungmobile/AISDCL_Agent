"""租約帳（L2）的非排程撤銷原語：行程、worktree、目錄／暫存檔（DES RealVerify_SideEffect_Isolation §5.3）。

排程撤銷（`sched.remove`）刻意**不**在這裡——REQ-SE-34 的 AST 鎖要求排程撤銷只住 `leases.py`。
所有「危險動作」都在動手前先驗身分：行程要命令列含沙盒 sid／根才砍（驗不到不砍，D-8，與
`procstop` 的先驗行程身分同原則）；目錄要名稱帶載具前綴才刪（帳被改壞也不會刪到別人的東西）。
縫（測試以 `mock.patch.object` 換掉）：`list_procs`、`kill_pid`、`run_git`。
"""  # noqa: E501

from __future__ import annotations

import json
import os
import signal
import subprocess
from pathlib import Path

from lib import sandbox_scope

from . import sched

#: 目錄／暫存檔名稱必須帶其一才准刪（防帳列被竄改後 rmtree 到不相干的路徑）。
SAFE_NAME_MARKERS = ("AutoSDD_RV_sbx_", "AutoSDD_RVprod_", "AutoSDD_RVout_", "AutoSDD_RV_",
                     "AutoSDD-RV-sbx-", "AutoSDD-RVprod-")
_NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def name_is_ours(path: Path | str) -> bool:
    """路徑的**任一段**帶載具前綴即算「是我們的」（含 `…\\AutoSDD_RV_sbx_x\\wt` 這種子目錄）。"""
    return any(m.lower() in part.lower() for part in Path(path).parts for m in SAFE_NAME_MARKERS)


def list_procs() -> list[tuple[int, str, str]]:
    """全部行程 `(pid, 名稱, 命令列)`；讀不到回空（呼叫端把「空」當成驗不到，不砍）。"""
    if os.name == "nt":
        rc, out = sched._ps("Get-CimInstance Win32_Process | Select-Object ProcessId,Name,CommandLine "  # noqa: E501
                            "| ConvertTo-Json -Compress", timeout=90)  # noqa: E501
        if rc != 0 or not out:
            return []
        data = json.loads(out)
        rows = [data] if isinstance(data, dict) else data
        return [(int(r["ProcessId"]), str(r["Name"] or ""), str(r["CommandLine"] or "")) for r in rows]  # noqa: E501
    pr = subprocess.run(["ps", "-A", "-o", "pid=,comm=,args="], capture_output=True, text=True,  # noqa: S603,S607
                        timeout=30, check=False)
    rows = []
    for line in pr.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) >= 2 and parts[0].isdigit():
            rows.append((int(parts[0]), parts[1], parts[2] if len(parts) > 2 else ""))
    return rows


def kill_pid(pid: int) -> None:
    """連樹砍（Windows `taskkill /T /F`；POSIX SIGKILL）。永不砍自己。"""
    if pid == os.getpid():
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True,  # noqa: S603,S607
                       creationflags=_NOWIN, check=False)
    else:
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass


def revoke_process(meta: dict) -> tuple[str, str]:
    """`(結果, 說明)`；結果 ∈ revoked／unverified／stuck。

    `meta["keys"]`＝沙盒 sid 與根路徑；命令列含其一的行程才算「驗過身分」。`meta["pid"]` 給了就只認該
    pid（但命令列仍須含 key，否則 `unverified`）；沒給＝依 key 掃全行程（涵蓋產品自己開的視窗，D-8）。"""  # noqa: E501
    keys = [str(k).lower() for k in meta.get("keys") or [] if k]
    pid = meta.get("pid")
    procs = list_procs()
    if pid is not None:
        alive, started = sandbox_scope.proc_probe(pid)
        want = meta.get("pid_started")
        if not alive or (want and started and started != want):
            return "revoked", f"pid {pid} 已不在"
        cmd = next((c for p, _n, c in procs if p == pid), None)
        if cmd is None or not any(k in cmd.lower() for k in keys):
            return "unverified", f"pid {pid} 命令列驗不出沙盒身分，不砍"
        victims = [pid]
    else:
        victims = [p for p, _n, c in procs if p != os.getpid() and any(k in c.lower() for k in keys)]  # noqa: E501
    for victim in victims:
        kill_pid(victim)
    left = [p for p, _n, c in list_procs() if p in victims]
    return ("stuck", f"行程仍在 {left}") if left else ("revoked", f"已砍 {len(victims)} 支")


def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True,  # noqa: S603,S607
                          encoding="utf-8", errors="replace", creationflags=_NOWIN, timeout=60,
                          check=False)


def revoke_worktree(path: str, host: str) -> tuple[bool, str]:
    """`git worktree remove --force`＋`prune`；宿主本身不動。回（已不在登記, 說明）。"""
    if not name_is_ours(path):
        return False, f"拒絕處理非載具前綴的 worktree：{path}"
    run_git(["worktree", "remove", "--force", path], Path(host))
    run_git(["worktree", "prune"], Path(host))
    listed = run_git(["worktree", "list", "--porcelain"], Path(host)).stdout
    norm = lambda s: os.path.normcase(str(s).replace("\\", "/")).rstrip("/")  # noqa: E731
    return norm(path) not in norm(listed.replace("\n", " ")), "worktree"


def revoke_path(kind: str, path: str) -> tuple[bool, str]:
    """目錄／暫存檔：名稱帶載具前綴才刪；刪完驗證真的不在。回（已不在, 說明）。"""
    from .sandbox import _remove_tree  # noqa: PLC0415 — lazy：sandbox 頂層 import leases
    target = Path(path)
    if not name_is_ours(target):
        return False, f"拒絕刪除非載具前綴的路徑：{path}"
    if target.is_dir():
        notes = _remove_tree(target, kind)
        return not notes, "; ".join(notes) or "rmtree"
    try:
        target.unlink(missing_ok=True)
    except OSError as exc:
        return False, f"{type(exc).__name__}: {exc}"
    return not target.exists(), "unlink"
