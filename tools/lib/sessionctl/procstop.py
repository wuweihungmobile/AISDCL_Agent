"""sessionctl 的行程面：列舉 claude 行程、驗身分、停視窗（ADR-XPLAT-004 §2.13.6 D7）。

WHY 獨立一檔：`roster.py` 只做「看見」（純讀檔）；會動行程的部分（砍樹）安全敏感，單獨成檔、
單獨測。**先驗身分再砍，驗不到就不砍**——pid 會被重用、命令列可能是別人的，砍錯＝砍掉掌舵者
手上的互動視窗。身分判準兩條缺一不可：①命令列含該 sid；②行程建立時刻與痕跡記錄的 spawn 時刻
相差 ≤ `CREATED_TOLERANCE` 秒（pid 重用的新行程建立時刻對不上）。外部執行檔（`powershell.exe`／
`ps`／`taskkill`／`kill`）一律經注入的 `runner`，且只在對應平台分支內組 argv（鐵律三）；測試
只傳假 runner，不砍真行程。誠實劃界：視窗內子代理只能由擁有者 TaskStop，本檔不碰。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

#: 命令列含 sid 之外，行程建立時刻與痕跡記錄 spawn 時刻的容許差（秒；ADR §2.13.6 步驟 2）。
CREATED_TOLERANCE = 120.0
SENTINEL_PREFIX = "AutoSDD_Sentinel_"
_SID_RE = re.compile(r"^[0-9A-Za-z][0-9A-Za-z_-]{6,63}$")
_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
_PRINT_RE = re.compile(r"(^|\s)-p(\s|$)")
_PS_ROW = re.compile(r"^\s*(\d+)\s+(\d+)\s+(\w{3}\s+\w{3}\s+\d+\s+\d\d:\d\d:\d\d\s+\d{4})\s+(.*)$")
#: Windows 取數：只取名稱 claude* 的行程；CreationDate 轉 UTC ISO 再外送（不依賴本機區域格式）。
_PS_SCRIPT = (
    "[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);"
    "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'claude*' } | "
    "Select-Object ProcessId,ParentProcessId,Name,CommandLine,"
    "@{n='Created';e={$_.CreationDate.ToUniversalTime().ToString('o')}} | "
    "ConvertTo-Json -Compress")
_TRACE_NAME = "autosdd_window_stop.jsonl"
_ANCHOR_EVENTS = ("session_switch_spawned", "relay_snapshot_before")
_ANCHOR_KEYS = ("at", "ts", "spawned_at", "created_at")


def default_runner(argv):
    """真外呼（測試一律注入假 runner）：不開視窗、UTF-8、30 秒上限。"""
    return subprocess.run(argv, capture_output=True, encoding="utf-8", errors="replace",
                          timeout=30, check=False,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def _taskkill_exe() -> str:
    root = os.environ.get("SystemRoot") or os.environ.get("SYSTEMROOT")
    return str(Path(root) / "System32" / "taskkill.exe") if root else "taskkill"


def parse_iso(raw: object) -> float | None:
    """ISO 8601（含 CIM 的 7 位小數與 `Z`）→ epoch 秒；認不出回 `None`。"""
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = re.sub(r"(\.\d{6})\d+", r"\1", raw.strip().replace("Z", "+00:00"))
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return None


def _parse_windows(text: str) -> list[dict]:
    data = json.loads(text) if text.strip() else []
    rows = [data] if isinstance(data, dict) else list(data)
    out = []
    for row in rows:
        if not isinstance(row, dict) or not str(row.get("ProcessId") or "").isdigit():
            continue
        out.append({"pid": int(row["ProcessId"]), "ppid": int(row.get("ParentProcessId") or 0),
                    "created": parse_iso(row.get("Created")),
                    "cmd": str(row.get("CommandLine") or ""), "name": str(row.get("Name") or "")})
    return out


def _parse_posix(text: str) -> list[dict]:
    out = []
    for line in text.splitlines():
        match = _PS_ROW.match(line)
        if not match:
            continue
        try:  # lstart 是本地時間、無 offset：只拿來與痕跡做相等比對，不持久化
            created = datetime.strptime(" ".join(match.group(3).split()),
                                        "%a %b %d %H:%M:%S %Y").astimezone().timestamp()
        except ValueError:
            created = None
        cmd = match.group(4)
        out.append({"pid": int(match.group(1)), "ppid": int(match.group(2)), "created": created,
                    "cmd": cmd, "name": Path(cmd.split(" ", 1)[0]).name})
    return out


def list_processes(runner=None, platform_name=None) -> list[dict] | None:
    """行程清單（`pid/ppid/created/cmd/name`）；列舉失敗回 `None`（＝量不到，呼叫端不得砍）。
    Windows 只列名稱 claude* 者；POSIX 列全部（砍樹要走 ppid）。"""
    run = runner or default_runner
    try:
        if (platform_name or sys.platform).startswith("win"):
            res = run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _PS_SCRIPT])
            return _parse_windows(res.stdout or "") if res.returncode == 0 else None
        res = run(["ps", "-axo", "pid=,ppid=,lstart=,command="])
        return _parse_posix(res.stdout or "") if res.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def is_claude(proc: dict) -> bool:
    return str(proc.get("name") or "").lower().removesuffix(".exe") == "claude"


def sid_of(cmd: str) -> str:
    """命令列裡的第一個 UUID（`-r <sid>`、交接／handback 路徑皆含 sid）；沒有回空字串。"""
    match = _UUID_RE.search(cmd or "")
    return match.group(0) if match else ""


def _trace_dir() -> Path:
    """唯讀解析（不 mkdir）：`AUTOSDD_TRACE_DIR` 或 `~/.autosdd/traces`。"""
    override = os.environ.get("AUTOSDD_TRACE_DIR", "").strip()
    return Path(override) if override else Path.home() / ".autosdd" / "traces"


def _event_stamps(path: Path, sid: str, per_sid_file: bool) -> list[float]:
    """`per_sid_file`＝檔名已含 sid（續跑日誌；其行內沒有 sid 欄）⇒ 不再逐行比對 sid。"""
    found: list[float] = []
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not any(ev in line for ev in _ANCHOR_EVENTS):
                    continue
                if not (per_sid_file or sid in line):
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if isinstance(rec, dict) and rec.get("event") in _ANCHOR_EVENTS:
                    stamps = [parse_iso(rec.get(k)) for k in _ANCHOR_KEYS if rec.get(k)]
                    found.extend(s for s in stamps[:1] if s is not None)
    except OSError:
        pass
    return found


def trace_anchors(sid: str, trace_dir: Path | None = None,
                  tmp_dir: Path | None = None) -> list[float]:
    """痕跡裡該 sid 的 spawn 時刻（epoch 秒）：續跑日誌 `relay_snapshot_before`（spawn 前一刻落）
    ＋持久痕跡目錄裡的 `session_switch_spawned`。都沒有回空清單（⇒ 身分驗不到、不砍）。"""
    found: list[float] = []
    try:
        logs = list((tmp_dir or Path(tempfile.gettempdir())).glob(
            f"autosdd_resume_log_*{sid}*.jsonl"))
        traces = list((trace_dir or _trace_dir()).glob("*.jsonl"))
    except OSError:
        return []
    for path in logs:
        found.extend(_event_stamps(path, sid, True))
    for path in traces:
        found.extend(_event_stamps(path, sid, False))
    return found


def verify(procs: list[dict], sid: str, anchors: list[float]) -> tuple[list[dict], list[str]]:
    """`(通過身分驗證者, 拒絕理由列)`。claude 行程且命令列含 sid 且建立時刻吻合任一錨點才通過。"""
    ok: list[dict] = []
    notes: list[str] = []
    for proc in procs:
        if not is_claude(proc):
            continue
        has_sid = sid in proc["cmd"]
        near = bool(anchors and proc["created"] is not None
                    and any(abs(proc["created"] - a) <= CREATED_TOLERANCE for a in anchors))
        if has_sid and near:
            ok.append(proc)
        elif has_sid:
            why = ("痕跡沒有 spawn 時刻記錄" if not anchors
                   else "建立時刻與痕跡不符（疑似 pid 重用）")
            notes.append(f"pid {proc['pid']}：命令列含 sid 但{why} ⇒ 不砍")
        elif near:
            notes.append(f"pid {proc['pid']}：建立時刻吻合但命令列不含 sid ⇒ 不砍")
    return ok, notes


def _descendants(procs: list[dict], root: int) -> list[int]:
    """root 的子孫 pid，葉在前（POSIX 無 /T，逐個砍要先砍葉）。"""
    kids: dict[int, list[int]] = {}
    for proc in procs:
        kids.setdefault(proc["ppid"], []).append(proc["pid"])
    order: list[int] = []
    stack = [root]
    while stack:
        cur = stack.pop()
        order.append(cur)
        stack.extend(kids.get(cur, []))
    return list(reversed(order))


def _kill(proc: dict, procs: list[dict], run, windows: bool) -> int:
    if windows:
        return int(run([_taskkill_exe(), "/T", "/F", "/PID", str(proc["pid"])]).returncode)
    rcs = [int(run(["kill", "-KILL", str(pid)]).returncode)
           for pid in _descendants(procs, proc["pid"])]
    return max(rcs or [1])


def _default_disarm(sid: str) -> int:
    import schedule_backend  # noqa: PLC0415 — lazy：只有真的停視窗時才需要

    return int(schedule_backend.select().disarm(f"{SENTINEL_PREFIX}{sid}"))


def _default_trace(record: dict) -> None:
    import endurance_env  # noqa: PLC0415 — lazy

    try:
        with (endurance_env.trace_dir() / _TRACE_NAME).open("a", encoding="utf-8",
                                                            newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass  # 痕跡寫不進去不得讓停止動作失敗


def stop_window(session_id: str, *, runner=None, platform_name=None, now=None, anchors=None,
                disarm=None, trace=None, procs=None) -> int:
    """停某 session 的視窗行程樹（先驗身分）。rc：0＝已停或沒有東西要停；1＝驗不到／砍失敗。
    `anchors`／`disarm`／`trace`／`procs` 是測試縫（缺席走真實痕跡、真排程、真列舉）。"""
    sid = str(session_id or "")
    if not _SID_RE.match(sid):
        print("❌ session id 格式不合，拒絕（只收英數與 -_）", file=sys.stderr)
        return 2
    run = runner or default_runner
    windows = (platform_name or sys.platform).startswith("win")
    procs = procs if procs is not None else list_processes(run, platform_name)
    if procs is None:
        print("❌ 量不到：行程列舉失敗 ⇒ 不砍（量不到≠沒有）", file=sys.stderr)
        return 1
    ok, notes = verify(procs, sid, trace_anchors(sid) if anchors is None else anchors)
    for note in notes:
        print(f"⚠️ {note}", file=sys.stderr)
    if not ok:
        print("沒有通過身分驗證的視窗行程。" if notes else f"沒有找到 session {sid} 的執行中視窗。")
        return 1 if notes else 0
    rcs = []
    for proc in ok:
        rcs.append(_kill(proc, procs, run, windows))
        print(f"已停 pid {proc['pid']}（taskkill /T /F／kill 樹；rc={rcs[-1]}）")
    disarm_rc = (disarm or _default_disarm)(sid)
    stamp = (now or datetime.now().astimezone()).isoformat(timespec="seconds")
    (trace or _default_trace)({"event": "window_stopped", "session": sid, "at": stamp,
                               "pids": [p["pid"] for p in ok], "kill_rc": rcs,
                               "basis": "cmdline-sid+created-time", "disarm_rc": disarm_rc})
    return 0 if all(rc == 0 for rc in rcs) else 1


def stop_all_unattended(*, runner=None, platform_name=None, **seams) -> int:
    """停所有無人視窗（claude -p 且命令列含 sid）；逐 sid 各自驗身分。無則 rc 0。"""
    procs = list_processes(runner, platform_name)
    if procs is None:
        print("❌ 量不到：行程列舉失敗 ⇒ 不砍", file=sys.stderr)
        return 1
    sids = sorted({sid_of(p["cmd"]) for p in procs if is_claude(p) and _PRINT_RE.search(p["cmd"])}
                  - {""})
    if not sids:
        print("沒有執行中的無人視窗。")
        return 0
    rcs = [stop_window(sid, runner=runner, platform_name=platform_name, procs=procs, **seams)
           for sid in sids]
    return 0 if all(rc == 0 for rc in rcs) else 1
