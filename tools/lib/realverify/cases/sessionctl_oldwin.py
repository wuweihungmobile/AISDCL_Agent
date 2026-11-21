# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""sessionctl_oldwin 家族（R217 F7；掌舵者 2026-11-21 真機：交棒後舊視窗沒有自動關閉）：RV-OW1。

真行程、真逐字稿、真 `sessionctl handoff --ack`。環境隔離＝`USERPROFILE`／`HOME` 指向沙盒，使
`~/.claude/sessions`（登記檔）與 `~/.claude/projects`（逐字稿）都落在沙盒；痕跡目錄與舊窗重試排程前綴
也是沙盒的。**替身行程**＝把 `cmd.exe` 複製成 `claude.exe.old.<數字>.<pid>`（自動更新改名後的真實映像名
形態）並真的跑起來，登記檔 `procStart` 取該行程真實建立時刻。不殺任何沙盒以外的行程。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..driver import EnvMissing
from ..sandbox import REPO
from . import CaseContext, case
from .prd_px_lib import ev
from .sessionctl_park import PY, run

_NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
IMAGE = "claude.exe.old.1795116108051.41752"
SLEEPER = 'Start-Sleep -Seconds 305; "timer-done"'


def _iso(minutes_ago: float) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutes_ago)).isoformat().replace("+00:00", "Z")


def _jsonl(path: Path, recs: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs), encoding="utf-8", newline="\n")


def _old_transcript(*, stopped: bool) -> list[dict]:
    """舊視窗逐字稿（真逐字稿形態）：人 30 分前打過字、起了一支背景計時 shell、啟動 tool_result；
    `stopped`＝之後被 `TaskStop` 結束（tool_result `Successfully stopped task`）。"""
    recs: list[dict] = [
        {"type": "user", "timestamp": _iso(30), "origin": {"kind": "human"}, "message": {"role": "user", "content": "繼續"}},
        {"type": "assistant", "timestamp": _iso(29), "message": {"content": [
            {"type": "tool_use", "id": "toolu_bg", "name": "PowerShell", "input": {"command": SLEEPER, "run_in_background": True}}]}},
        {"type": "user", "timestamp": _iso(29), "message": {"role": "user", "content": [
            {"tool_use_id": "toolu_bg", "type": "tool_result", "content": "Command running in background with ID: b53oeig8w. Output is being written to: x"}]}},
    ]
    if stopped:
        body = json.dumps({"message": f"Successfully stopped task: b53oeig8w ({SLEEPER})", "task_id": "b53oeig8w", "task_type": "local_bash"})
        recs.append({"type": "user", "timestamp": _iso(20), "message": {"role": "user", "content": [
            {"tool_use_id": "toolu_stop", "type": "tool_result", "content": body}]}})
    return recs


def _fake_claude(ctx: CaseContext, sb, name: str) -> subprocess.Popen:
    """真的跑起來的替身：`cmd.exe` 複製成家族映像名（沙盒內），底下掛一支 ping 當子孫。"""
    src = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "cmd.exe"  # platform-ok: Windows 專屬真機載具，SystemRoot 預設值
    if sys.platform != "win32" or not src.is_file():
        raise EnvMissing("本案例需要 Windows 與 System32\\cmd.exe（舊視窗自動關閉只在 Windows 實作）")
    exe = sb.root / "bin" / name
    exe.parent.mkdir(exist_ok=True)
    shutil.copyfile(src, exe)
    proc = subprocess.Popen([str(exe), "/c", "ping -n 300 127.0.0.1 >nul"], cwd=str(sb.root), stdin=subprocess.DEVNULL,  # noqa: S603
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=_NOWIN)
    sb.procs.append(proc)
    return proc


def _world(ctx: CaseContext, sb, *, stopped: bool, preseed_retries: int = 0) -> dict:
    """一套沙盒世界：替身舊視窗（登記檔＋逐字稿）、新 session 逐字稿、交接包。回 {proc, pkg, env, old, new}。"""
    import time  # noqa: PLC0415

    sys.path.insert(0, str(REPO / "tools"))
    sys.path.insert(0, str(REPO / "tools" / "lib"))
    from lib.sessionctl import winproc  # noqa: PLC0415

    old, new = f"0ld{os.urandom(4).hex()}-aaaa-4aaa-8aaa-000000000001", f"9ew{os.urandom(4).hex()}-bbbb-4bbb-8bbb-000000000002"
    home = sb.root / "home"
    proc = _fake_claude(ctx, sb, IMAGE)
    time.sleep(0.5)
    api = winproc.WinApi()
    handle = api.open(proc.pid)
    born = api.created(handle)
    api.close(handle)
    ctx.check(born is not None and proc.poll() is None, "替身行程應活著且取得到建立時刻")
    sessions = home / ".claude" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    (sessions / f"{proc.pid}.json").write_text(json.dumps({"pid": proc.pid, "sessionId": old, "procStart": born, "entrypoint": "cli", "status": "idle", "cwd": str(sb.root)}), encoding="utf-8")
    projects = home / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(REPO.resolve()))
    _jsonl(projects / f"{old}.jsonl", _old_transcript(stopped=stopped))
    _jsonl(projects / f"{new}.jsonl", [{"type": "assistant", "timestamp": _iso(1), "message": {"content": []}}])
    hdir = sb.root / "handoff"
    hdir.mkdir(exist_ok=True)
    pkg = hdir / f"{old}_20261121T000000Z.md"
    pkg.write_text(f"sid={old}\n", encoding="utf-8")
    sb.oldwin_prefix()  # 沙盒專屬重試排程前綴（sweep 只看這個前綴，不碰真機）
    if preseed_retries:
        events = sb.root / "traces" / "oldwin"
        events.mkdir(parents=True, exist_ok=True)
        with (events / "events.jsonl").open("a", encoding="utf-8", newline="\n") as fh:
            for _ in range(preseed_retries):
                fh.write(json.dumps({"event": "oldwin_retry_scheduled", "handoff": str(pkg), "old": old, "new": new}) + "\n")
    env = sb.env({"USERPROFILE": str(home), "HOME": str(home), "AUTOSDD_HANDOFF_DIR": str(hdir), "CLAUDE_CODE_SESSION_ID": new,
                  "AUTOSDD_SESSION_SWITCH_MODE": "auto"})
    for key in ("AUTOSDD_UNATTENDED", "AUTOSDD_OLDWIN_AUTOCLOSE_OFF", "CLAUDE_CONFIG_DIR"):
        env.pop(key, None)
    return {"proc": proc, "pkg": pkg, "env": env, "old": old, "new": new}


def _events(sb, name: str) -> list[dict]:
    path = sb.root / "traces" / "oldwin" / "events.jsonl"
    if not path.is_file():
        return []
    rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [r for r in rows if r.get("event") == name]


@case("RV-OW1", "sessionctl_oldwin", refs=("R218-F7", "QuotaWall-D-I", "DEF-OW-TASKSTOP"), sched=True)
def rv_ow1(ctx: CaseContext) -> None:
    """正例：映像名 `claude.exe.old.<數字>.<pid>` 的真替身行程、其逐字稿的背景 shell 已被 TaskStop ⇒
    真 `handoff --ack` 後舊窗被關（行程樹消失、`oldwin_closed`）。
    反例：同形替身但背景 shell 仍在跑（沒有 TaskStop）⇒ 不關、行程仍活、ack 輸出指名 pid 並寫
    「請手動關閉舊視窗」（已預置 3 次重試帳＝直接進放棄分支，不起任何排程）。"""
    sb = ctx.sandbox(probe_hooks=False)
    cli = [PY, str(REPO / "tools" / "sessionctl.py"), "handoff", "--ack"]

    good = _world(ctx, sb, stopped=True)
    r = run([*cli, str(good["pkg"])], cwd=sb.root, env=good["env"], timeout=120)
    ctx.check(r.returncode == 0, f"ack rc={r.returncode}\n{r.stdout[-500:]}{r.stderr[-500:]}")
    try:
        good["proc"].wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass
    ctx.check(good["proc"].poll() is not None, f"TaskStop 過的舊視窗（映像 {IMAGE}）應被關閉，輸出：{r.stdout[-500:]}")
    ctx.check(bool(_events(sb, "oldwin_closed")), "缺 oldwin_closed 事件")
    ctx.check("已關閉舊視窗" in r.stdout, f"ack 輸出應說已關閉：{r.stdout[-300:]}")
    ev(ctx, "closed_image", IMAGE)
    ev(ctx, "closed_pid", good["proc"].pid)

    bad = _world(ctx, sb, stopped=False, preseed_retries=3)
    r2 = run([*cli, str(bad["pkg"])], cwd=sb.root, env=bad["env"], timeout=120)
    ctx.check(r2.returncode == 0, f"ack rc={r2.returncode}\n{r2.stdout[-500:]}{r2.stderr[-500:]}")
    ctx.check(bad["proc"].poll() is None, "背景 shell 仍在跑的舊視窗不得被關")
    ctx.check(f"pid={bad['proc'].pid}" in r2.stdout and "請手動關閉舊視窗" in r2.stdout, f"放棄時要指名 pid 並請手動關閉：{r2.stdout[-500:]}")
    ctx.check(bool(_events(sb, "oldwin_retry_abandoned")), "缺 oldwin_retry_abandoned 事件")
    ev(ctx, "kept_alive_with_running_shell", f"pid={bad['proc'].pid}")
