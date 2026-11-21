"""sessionctl 的行程面：列舉 claude 行程、驗身分、停視窗（ADR-XPLAT-004 §2.13.6 D7）。

WHY 獨立一檔：`roster.py` 只做「看見」（純讀檔）；會動行程的部分（砍樹）安全敏感，單獨成檔、
單獨測。**先驗身分再砍，驗不到就不砍**——pid 會被重用、命令列可能是別人的，砍錯＝砍掉掌舵者
手上的互動視窗。身分判準缺一不可：①命令列含該 sid；②行程建立時刻與痕跡記錄的 spawn 時刻
相差 ≤ `CREATED_TOLERANCE` 秒（pid 重用的新行程建立時刻對不上）；③痕跡帶 pid 者要 pid 相符
（SEC-2：同 sid 的接手新視窗不是舊 session），痕跡無 pid 者（續跑日誌）只認 print 模式行程；
`--all-unattended` 另限 print 模式（SEC-1）。外部執行檔（`powershell.exe`／
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


def first_uuid_of(cmd: str) -> str:
    """命令列裡的第一個 UUID；**只供顯示與無人視窗列舉**。🔴 不是行程的 session id：
    `claude "讀 …\\05d1b770-….md"` 的第一個 UUID 是交接包檔名，不是該行程的 sid（DEF-02：舊名
    `sid_of` 被拿去判「擁有者還活著」，把已死的擁有者誤判成活著）。判活用 `owner_sid_of`。"""
    match = _UUID_RE.search(cmd or "")
    return match.group(0) if match else ""


#: 旗標形態：`-r`／`--resume`／`--session-id` 後面**緊接**的 UUID 才是該行程的 sid。
_FLAG_SID_RE = re.compile(
    r"(?:^|\s)(?:-r|--resume|--session-id)(?:\s+|=)[\"']?(" + _UUID_RE.pattern + ")", re.I)
#: CIM `CreationDate` 只到微秒（DMTF 字串），與 GetProcessTimes 差在 100ns 刻度個位數（實測差 5）。
CIM_TOLERANCE_100NS = 10


def sessions_dir() -> Path:
    """`~/.claude/sessions`（harness 的行程登記目錄：`<pid>.json`＝`sessionId`／`procStart`／
    `status`…）。"""
    return Path.home() / ".claude" / "sessions"


def registry_rows(folder: Path | None = None) -> list[dict]:
    """登記檔全部列（壞檔略過）；每列補 `pid`（取檔名，檔內 `pid` 優先）。讀不到回空。"""
    rows: list[dict] = []
    try:
        for path in (folder or sessions_dir()).glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(data, dict):
                pid = data.get("pid") if isinstance(data.get("pid"), int) else (
                    int(path.stem) if path.stem.isdigit() else None)
                rows.append(dict(data, pid=pid))
    except OSError:
        pass
    return rows


def created_filetime(pid) -> int | None:
    """行程建立時刻的 FILETIME（GetProcessTimes，只在 Windows；其餘平台或取不到＝`None`）。"""
    if sys.platform != "win32" or not isinstance(pid, int):
        return None
    from . import winproc  # noqa: PLC0415 — lazy

    api = winproc.WinApi()
    handle = api.open(pid)
    try:
        return api.created(handle)
    finally:
        api.close(handle)


def _stamp_matches(row: dict, exact: int | None, cim: int | None) -> bool:
    """登記檔 `procStart` 與行程建立時刻相符：GetProcessTimes **全等**；它取不到才退用 CIM，
    容差 `CIM_TOLERANCE_100NS`（絕對值嚴格小於）。兩者都取不到 ⇒ 不採信。"""
    try:
        start = int(row.get("procStart"))
    except (TypeError, ValueError):
        return False
    if exact is not None:
        return start == exact
    return cim is not None and abs(start - cim) < CIM_TOLERANCE_100NS


def owner_sid_of(pid, cmd: str, *, cim_created: int | None = None, folder: Path | None = None,
                 created_of=None, platform_name: str | None = None) -> str:
    """行程**自己**的 session id（DEF-02）：①登記檔 `sessionId` 且 `procStart` 相符才採信（只在
    Windows；非 Windows 的 `procStart` 單位時基未現查，不猜 ⇒ 跳過）；②命令列只認 `-r`／
    `--resume`／`--session-id` 緊接的 UUID；③都沒有 ⇒ 空字串（＝不判活，**不是**判死）。
    不讀 `kind`／`entrypoint`（`claude -p` 也寫 `kind=interactive`）。"""
    if (platform_name or sys.platform).startswith("win") and isinstance(pid, int):
        exact = (created_of or created_filetime)(pid)
        for row in registry_rows(folder):
            if row.get("pid") == pid and isinstance(row.get("sessionId"), str) and _stamp_matches(
                    row, exact, cim_created):
                return row["sessionId"]
    match = _FLAG_SID_RE.search(cmd or "")
    return match.group(1) if match else ""


def alive_sids(procs, folder: Path | None = None) -> set[str]:
    """名冊判活：所有 claude 行程各自 `owner_sid_of` 自報的 sid（不再取命令列第一個 UUID，DEF-02）。
    `procs` 的 `created`（epoch 秒，CIM 微秒精度）換成 FILETIME 當 CIM 後備比對值。"""
    from .winproc import epoch_to_filetime  # noqa: PLC0415 — lazy

    return {sid for p in procs if is_claude(p) and (sid := owner_sid_of(
        p["pid"], p["cmd"], folder=folder,
        cim_created=None if p.get("created") is None else epoch_to_filetime(p["created"])))}


def live_windows_of(sid: str, *, folder: Path | None = None, created_of=None) -> list[dict]:
    """某 sid 目前活著的視窗行程（D-8 比對法）：登記檔 `sessionId`＝sid **且** `procStart` 與
    GetProcessTimes **全等**（這裡不退用 CIM——要拿來關視窗，驗不到就當沒有）。同一 sid 可有多列。
    回 `[{pid, procStart, entrypoint, status, cwd}]`。"""
    out = []
    for row in registry_rows(folder):
        pid = row.get("pid")
        if row.get("sessionId") == sid and isinstance(pid, int) and _stamp_matches(
                row, (created_of or created_filetime)(pid), None):
            out.append({k: row.get(k) for k in ("pid", "procStart", "entrypoint", "status", "cwd")})
    return out


def pid_reused(pid, at_iso, created_of=None) -> bool:
    """spawn 痕跡的 pid 是不是已被**別的**行程重用（現行行程建立時刻晚於痕跡 `at` 超過 30 秒）。
    取不到建立時刻或 `at` 解析不了 ⇒ `False`（偏安全：照舊當同一個行程、繼續拒絕重複 spawn）。"""
    stamp, created = parse_iso(at_iso), (created_of or created_filetime)(pid)
    if stamp is None or created is None:
        return False
    return (created - 116444736000000000) / 1e7 > stamp + 30


#: 關閉視窗目標的映像名家族（DES §7.1 第 5 點；QuotaWall DES §9 D-I）：`claude.exe`、自動更新改名後
#: 仍在跑的 `claude.exe.old.<數字>.<pid>`（2026-11-21 真機：`claude.exe.old.1795116108051.41752`
#: 被精確比對擋下）、`node.exe`。身分驗證（procStart 全等、非呼叫者祖先）不放鬆，映像僅縱深防禦。
_IMAGE_FAMILY_RE = re.compile(r"^(claude\.exe(\.old\.\d+\.\d+)?|node\.exe)$", re.I)
TERMINATE_WAIT_SECONDS = 5.0
#: `terminate_tree_verified` 因這兩個理由拒絕時，視窗「關不了」而非「不該關」：可降級為出聲請人關。
DEGRADABLE_REASONS = frozenset({"image_not_allowed", "open_failed"})


def image_allowed(name: str) -> bool:
    """映像名（`winproc.image` 回小寫含副檔名）屬於可關閉的家族。空字串（取不到）＝不允許。"""
    return bool(_IMAGE_FAMILY_RE.match(str(name or "")))


def terminate_tree_verified(pid: int, proc_start: int, *, api, images=image_allowed, self_pid=None,
                            intent=None, recheck=None, sleep=None,
                            wait: float = TERMINATE_WAIT_SECONDS) -> dict:
    """以 **handle** 為基礎砍「視窗行程樹」（DES §7.1「怎麼關」）：開 handle → 在 handle 上驗建立
    時刻＝`proc_start` ∧ 映像在白名單 ∧ 目標不是呼叫者或其祖先 → Toolhelp 快照沿 parent 往下收
    子孫（只收建立時刻 ≥ 父者，每個也開 handle 驗）→ `intent(plan)`（呼叫端在此寫
    `oldwin_close_intent`）→
    `recheck()`（TOCTOU 重驗；回非空字串＝中止）→ 由葉往根 `TerminateProcess`，最後才是本體 → 等
    `TERMINATE_WAIT_SECONDS` 秒確認本體已不在。回 `{ok, reason, pids, killed}`；`reason` 空＝成功。
    之後所有動作都對 handle，不再用 pid ⇒ pid 被重用也砍不到別人。主控台宿主不主動砍。"""
    import os  # noqa: PLC0415
    import time  # noqa: PLC0415

    res: dict = {"ok": False, "reason": "", "pids": [], "killed": []}
    held: list[tuple[int, object]] = []

    def refuse(why: str) -> dict:
        res["reason"] = why
        return res

    try:
        root = api.open(pid)
        if root is None:
            return refuse("open_failed")
        held.append((pid, root))
        born = api.created(root)
        if born is None or born != int(proc_start):
            return refuse("procstart_mismatch")
        image = api.image(root)
        if not (images(image) if callable(images) else image in images):
            return refuse("image_not_allowed")
        me = os.getpid() if self_pid is None else self_pid
        if pid == me or pid in api.ancestors(me):
            return refuse("target_is_caller_or_ancestor")
        kids: dict[int, list[int]] = {}
        for child, parent in api.snapshot():
            kids.setdefault(parent, []).append(child)
        queue, seen = [(pid, born)], {pid}
        while queue:
            cur, cur_born = queue.pop(0)
            for child in kids.get(cur, []):
                handle = api.open(child) if child not in seen else None
                seen.add(child)
                cb = api.created(handle) if handle is not None else None
                if cb is None or cb < cur_born:  # 建立時刻早於父 ⇒ 只是碰巧同 parent pid，不是子孫
                    api.close(handle)
                    continue
                held.append((child, handle))
                queue.append((child, cb))
        res["pids"] = [p for p, _h in held]
        if intent is not None:
            intent({"pid": pid, "proc_start": int(proc_start), "descendants": res["pids"][1:]})
        why = recheck() if recheck is not None else ""
        if why:
            return refuse(why)
        for child, handle in reversed(held):  # BFS 反序＝葉在前、本體最後
            if api.terminate(handle):
                res["killed"].append(child)
        deadline = time.monotonic() + wait
        while api.running(root) and time.monotonic() < deadline:
            (sleep or time.sleep)(0.1)
        if api.running(root):
            return refuse("still_running")
        res["ok"] = True
        return res
    finally:
        for _p, handle in held:
            api.close(handle)


def _trace_dir() -> Path:
    """唯讀解析（不 mkdir）：`AUTOSDD_TRACE_DIR` 或 `~/.autosdd/traces`。"""
    override = os.environ.get("AUTOSDD_TRACE_DIR", "").strip()
    return Path(override) if override else Path.home() / ".autosdd" / "traces"


def _event_stamps(path: Path, sid: str, per_sid_file: bool) -> list[tuple[float, int | None]]:
    """`(時刻, 痕跡記的 pid 或 None)`。`per_sid_file`＝檔名已含 sid（續跑日誌；其行內沒有 sid
    欄）⇒ 不再逐行比對 sid。"""
    found: list[tuple[float, int | None]] = []
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
                    pid = rec.get("pid")
                    pid = pid if isinstance(pid, int) and not isinstance(pid, bool) else None
                    found.extend((s, pid) for s in stamps[:1] if s is not None)
    except OSError:
        pass
    return found


def trace_anchors(sid: str, trace_dir: Path | None = None,
                  tmp_dir: Path | None = None) -> list[float]:
    """痕跡裡該 sid 的 spawn 時刻（epoch 秒；只看時間）。身分驗證用 `trace_records`。"""
    return [stamp for stamp, _pid in trace_records(sid, trace_dir, tmp_dir)]


def trace_records(sid: str, trace_dir: Path | None = None,
                  tmp_dir: Path | None = None) -> list[tuple[float, int | None]]:
    """痕跡裡該 sid 的 spawn 記錄 `(epoch 秒, pid)`：續跑日誌 `relay_snapshot_before`（spawn 前
    一刻落、**無 pid**）＋持久痕跡目錄裡的 `session_switch_spawned`（帶 pid）。都沒有回空清單
    （⇒ 身分驗不到、不砍）。"""
    found: list[tuple[float, int | None]] = []
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


def _norm_anchors(anchors) -> list[tuple[float, int | None]]:
    """錨點正規化：純數字＝只有時刻（續跑日誌那種，無 pid）；`(時刻, pid)` 原樣。"""
    return [a if isinstance(a, tuple) else (a, None) for a in anchors or ()]


def _anchor_match(proc: dict, anchors: list[tuple[float, int | None]]) -> str | None:
    """行程對得上哪種錨點：`"pid"`（痕跡記的 pid 相符且時刻吻合）、`"print"`（無 pid 的錨點時刻
    吻合，且行程是 print 模式——無人續跑的 spawn 痕跡本來就沒有 pid）、否則 `None`。
    互動視窗**只有** pid 相符一條路：命令列帶舊 sid 的接手新視窗（SEC-2）不會被當成舊 session。"""
    if proc["created"] is None:
        return None
    printed = bool(_PRINT_RE.search(proc["cmd"]))
    for stamp, pid in anchors:
        if abs(proc["created"] - stamp) > CREATED_TOLERANCE:
            continue
        if pid is not None and pid == proc["pid"]:
            return "pid"
        if pid is None and printed:
            return "print"
    return None


def _has_sid(cmd: str, sid: str) -> bool:
    """sid 要與命令列裡某個完整 UUID 相等（8 碼前綴不得子字串命中，SEC-3）；harness 的 session id
    一律是 UUID，非 UUID 形＝驗不到＝不砍（只准收緊）。"""
    return bool(_UUID_RE.fullmatch(sid)) and sid.lower() in {
        u.lower() for u in _UUID_RE.findall(cmd or "")}


def verify(procs: list[dict], sid: str, anchors: list,
           require_print: bool = False) -> tuple[list[dict], list[str]]:
    """`(通過身分驗證者, 拒絕理由列)`。claude 行程、命令列含 sid、且 `_anchor_match` 對得上才通過。
    `require_print`（`--all-unattended`）：非 print 模式的行程一律不在集合內（SEC-1）。"""
    ok: list[dict] = []
    notes: list[str] = []
    anchors = _norm_anchors(anchors)
    for proc in procs:
        if not is_claude(proc):
            continue
        if require_print and not _PRINT_RE.search(proc["cmd"]):
            continue
        has_sid = _has_sid(proc["cmd"], sid)
        near = _anchor_match(proc, anchors) is not None
        if has_sid and near:
            ok.append(proc)
        elif has_sid:
            why = ("痕跡沒有 spawn 時刻記錄" if not anchors
                   else "痕跡的 pid 或建立時刻不符（疑似 pid 重用，或同 sid 的別個視窗）")
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
                disarm=None, trace=None, procs=None, require_print: bool = False) -> int:
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
    ok, notes = verify(procs, sid, trace_records(sid) if anchors is None else anchors,
                       require_print)
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
                               "basis": "cmdline-sid+trace-pid+created-time",
                               "disarm_rc": disarm_rc})
    return 0 if all(rc == 0 for rc in rcs) else 1


def stop_all_unattended(*, runner=None, platform_name=None, **seams) -> int:
    """停所有無人視窗（claude -p 且命令列含 sid）；逐 sid 各自驗身分，且驗證集合只收 print 模式行程
    （`require_print`：同 sid 的互動視窗即使時刻吻合也不砍，SEC-1）。無則 rc 0。"""
    procs = list_processes(runner, platform_name)
    if procs is None:
        print("❌ 量不到：行程列舉失敗 ⇒ 不砍", file=sys.stderr)
        return 1
    sids = sorted({first_uuid_of(p["cmd"]) for p in procs
                   if is_claude(p) and _PRINT_RE.search(p["cmd"])} - {""})
    if not sids:
        print("沒有執行中的無人視窗。")
        return 0
    rcs = [stop_window(sid, runner=runner, platform_name=platform_name, procs=procs,
                       require_print=True, **seams) for sid in sids]
    return 0 if all(rc == 0 for rc in rcs) else 1
