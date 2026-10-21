"""SelfImproving 探針子行程出口（TCS-SelfImproving-P2 R87；PRD §9.4）：整個套件除 `git.py` 外
唯一出現行程外呼的檔（能力類別 `exec`）。

`Popen`＋`communicate(timeout)`、`shell=False`；環境白名單（不繼承 `AUTOSDD_*` 與其他機密）；
`PYTHONPATH` 只有沙盒樹根（不帶 `-I`／`-P`，否則載具自證失效）；逾時殺行程樹並回收；輸出只留
sha256、位元組數與遮蔽後的末段（≤300 位元組），原始輸出全文不入 git、不落任何檔。
"""

from __future__ import annotations

import hashlib
import os
import re
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_ENV_KEYS = ("PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME", "USERPROFILE", "LANG", "LC_ALL")
TAIL_BYTES = 300
_MASKS = (
    (re.compile(r"Bearer\s+\S+"), "Bearer [REDACTED]"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{8,}"), "[REDACTED]"),
    (re.compile(r"(?i)Authorization:[^\r\n]*"), "Authorization: [REDACTED]"),
    (re.compile(r"://[^/\s:@]+:[^/\s@]+@"), "://[REDACTED]@"),
)


@dataclass
class ProbeResult:
    rc: int | None
    timed_out: bool
    out_sha256: str
    out_bytes: int
    tail: str


def mask(text: str) -> str:
    for rx, repl in _MASKS:
        text = rx.sub(repl, text)
    return text


def _tail(raw: bytes) -> str:
    masked = mask(raw.decode("utf-8", errors="replace")).encode("utf-8")
    cut = masked[-TAIL_BYTES:]
    while cut and (cut[0] & 0xC0) == 0x80:  # 依 UTF-8 邊界截斷，不切半個字元
        cut = cut[1:]
    return cut.decode("utf-8", errors="replace")


def _env(sandbox_root: Path) -> dict[str, str]:
    env = {k: os.environ[k] for k in _ENV_KEYS if k in os.environ}
    env.update(PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(sandbox_root))
    return env


def _kill_tree(proc: subprocess.Popen) -> None:
    """殺行程樹（含孫行程）；兩條各在平台守衛作用域內。"""
    if sys.platform.startswith("win"):
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], check=False,
                       capture_output=True)
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    proc.kill()


def expand(argv: list[str], sandbox_root: Path) -> list[str]:
    """`{python}`→`sys.executable`、`{sandbox}`→沙盒樹根（`{heldout}` 由呼叫端先換）。"""
    out = [a.replace("{sandbox}", str(sandbox_root)) for a in argv]
    out[0] = sys.executable if out[0] == "{python}" else out[0]
    return out


def run_probe(argv: list[str], *, cwd: Path, sandbox_root: Path, timeout: float) -> ProbeResult:
    """執行一個探針；回 `ProbeResult`（逾時時 `rc` 為 None、`timed_out` 為 True）。"""
    flags: dict = {}
    if sys.platform.startswith("win"):
        flags["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        flags["start_new_session"] = True
    proc = subprocess.Popen(
        expand(argv, sandbox_root), cwd=str(cwd), env=_env(sandbox_root), shell=False,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, **flags)
    timed_out = False
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_tree(proc)
        out, err = proc.communicate()
    raw = (out or b"") + (err or b"")
    return ProbeResult(None if timed_out else proc.returncode, timed_out,
                       "sha256:" + hashlib.sha256(raw).hexdigest(), len(raw), _tail(raw))
