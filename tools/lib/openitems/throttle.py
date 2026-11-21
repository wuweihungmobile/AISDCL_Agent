"""驅動器的花費與併發上限（DES §5.1 第 2～4 步、§5.4；REQ-WP-12／13／19／28／97）。

一個判準一個函式，全部可不碰磁碟測：
  · 全域互斥鎖 `driver.lock`／soak 專用 `soak.lock`（`O_CREAT|O_EXCL` 原子建立＋讀回驗證；
    持有者判活＝
    pid 存在且行程建立時間相符，**且**未逾 `budget_minutes`，卡死的 driver 不得永久佔鎖）。
  · 每窗次數上限＋先進先出（排隊鍵＝`(open.ts, id)`；`R + O < max_runs_per_window` 才拿到名額）。
  · 排程錯開：`pick_slot` 找第一個與所有其他 driven 列相距 ≥ `stagger_minutes` 的時槽。
  · 讓路（互動 session 在一個巡邏間隔內有對話記錄）與額度（`--pace` 解析，量不到＝保守 deferred）。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from lib import endurance_env, platform_utils, quota_limits, quota_messages, transcript_activity

from . import schedcache
from .ledger import parse_ts

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_TOOLS = Path(__file__).resolve().parents[2]
LOCK_FILES = {"normal": "driver.lock", "soak": "soak.lock"}
#: `--pace` 逐軸明細的四條「短窗／週窗」軸（保險池 extra_usage／spend 不進判準，同
#: quota_policy 的 gate 排除）。
SHORT_AXES = ("session", "five_hour")
WEEK_AXES = ("weekly_all", "seven_day")
BANDS_BLOCKING = ("converge", "prepare", "halt", "unmeasured")
_AXIS_RE = re.compile(r"kind=(\w+) [\d.]+% (?:剩 (\d+) 分鐘|reset 距離不明) band=(\w+)")
_DISPATCH_RE = re.compile(r"現在可派 (\d+) 個")


def oi_dir() -> Path:
    return endurance_env.trace_dir() / "openitems"


def console_python() -> str:
    """子行程用的直譯器：`pythonw.exe` 不能接 stdout，換同目錄的 `python.exe`（找不到退回原值）。"""
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe" and (exe.with_name("python.exe")).is_file():
        return str(exe.with_name("python.exe"))
    return sys.executable


def proc_identity(pid: int) -> str | None:
    """行程建立時間（UTC ISO 或 `ps lstart` 字串）；行程不存在或量不到回 `None`。"""
    if not isinstance(pid, int) or pid <= 0:
        return None
    if sys.platform.startswith("win"):
        proc = schedcache.planner().run_powershell(
            f"$p = Get-Process -Id {pid} -ErrorAction SilentlyContinue; "
            "if ($p) { $p.StartTime.ToUniversalTime().ToString('o') }\n")
        out = (proc.stdout or "").strip().splitlines()
        return out[-1].strip() if proc.returncode == 0 and out else None
    try:
        proc = subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=30,
                              check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    text = proc.stdout.strip()
    return text if proc.returncode == 0 and text else None


def holder_alive(info: dict, now: datetime, identity=proc_identity) -> bool:
    """鎖持有者是否仍有效：未逾預算，且 pid 存在、建立時間與記錄相符（記錄無時間只比 pid）。"""
    started = parse_ts(info.get("started_at"))
    budget = info.get("budget_minutes")
    if started is None or not isinstance(budget, int) or now >= started + timedelta(minutes=budget):
        return False
    live = identity(info.get("pid"))
    return live is not None and (not info.get("proc_start") or live == info["proc_start"])


def _read_lock(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def acquire(kind: str, item_id: str, budget_minutes: int, now: datetime, *, identity=proc_identity,
            pid: int | None = None) -> bool:
    """取 `driver.lock`（kind=normal）或 `soak.lock`（kind=soak）；拿到回 `True`。持有者死亡或逾預算
    ⇒ 接手（刪除後重搶一次，仍搶輸＝別人先接手，回 `False`）。"""
    path = oi_dir() / LOCK_FILES[kind]
    path.parent.mkdir(parents=True, exist_ok=True)
    me = pid if pid is not None else os.getpid()
    body = json.dumps({"pid": me, "proc_start": identity(me) or "", "id": item_id,
                       "started_at": now.isoformat(timespec="seconds"),
                       "budget_minutes": budget_minutes}).encode("utf-8")
    for _ in range(2):
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            info = _read_lock(path)
            if info is not None and holder_alive(info, now, identity):
                return False
            try:
                path.unlink()
            except OSError:
                return False
            continue
        try:
            os.write(fd, body)
        finally:
            os.close(fd)
        mine = _read_lock(path)
        return bool(mine and mine.get("pid") == me and mine.get("id") == item_id)
    return False


def release(kind: str, pid: int | None = None) -> None:
    """只釋放自己持有的鎖（pid 相符才刪），別人接手後的鎖不動。"""
    path = oi_dir() / LOCK_FILES[kind]
    info = _read_lock(path)
    if info is not None and info.get("pid") == (pid if pid is not None else os.getpid()):
        path.unlink(missing_ok=True)


def runs_path() -> Path:
    return oi_dir() / "window_runs.jsonl"


def record_run(now: datetime, item_id: str) -> None:
    path = runs_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps({"at": now.isoformat(timespec="seconds"), "id": item_id}) + "\n")


def window(now: datetime, reset_at: datetime | None,
           params: dict) -> tuple[datetime, datetime | None]:
    """當前窗 `(起點, 終點)`：量到短窗 reset ⇒ `(reset − cap_window, reset)`；量不到 ⇒ 滾動區間
    `(now − cap_window, None)`（限速口徑，不是預測 reset；DES §5.4-2）。"""
    span = timedelta(minutes=params["cap_window_minutes"])
    if reset_at is not None and reset_at > now:
        return reset_at - span, reset_at
    return now - span, None


def runs_in_window(start: datetime, path: Path | None = None) -> int:
    count = 0
    try:
        lines = (path or runs_path()).read_text(encoding="utf-8").splitlines()
    except OSError:
        return 0
    for line in lines:
        try:
            stamp = parse_ts(json.loads(line).get("at"))
        except (ValueError, AttributeError):
            continue
        count += 1 if stamp is not None and stamp >= start else 0
    return count


def queue_key(item: dict) -> tuple[str, str]:
    return item["opened"], item["id"]


def ahead_in_queue(me: dict, items: dict[str, dict], end: datetime | None, now: datetime) -> int:
    """`O`：排隊鍵比自己小、目前有效 driven、`d.at` 落在本窗、且本窗尚無 `start` 的列數。"""
    horizon = end if end is not None else now
    count = 0
    for other in items.values():
        if other["id"] == me["id"] or other["state"] != "driven" or other["undriven"]:
            continue
        at = parse_ts(other["drive"].get("at")) if other["drive"] else None
        if (queue_key(other) < queue_key(me) and other["start"] is None and at is not None
                and at < horizon):
            count += 1
    return count


def window_slot(me: dict, items: dict[str, dict], runs: int, end: datetime | None, now: datetime,
                params: dict) -> bool:
    """先進先出名額：`R + O < max_runs_per_window` 才拿到（中途新開的列不得插隊）。"""
    return runs + ahead_in_queue(me, items, end, now) < params["max_runs_per_window"]


def pick_slot(desired: datetime, taken: list[datetime], stagger_minutes: int) -> datetime:
    """從 `desired` 起找第一個與 `taken` 每一格都相距 ≥ stagger 的時槽（有界收斂）。"""
    gap, slot = timedelta(minutes=stagger_minutes), desired
    for _ in range(len(taken) + 1):
        clash = [t for t in taken if abs(t - slot) < gap]
        if not clash:
            return slot
        slot = max(clash) + gap
    return slot


def taken_slots(items: dict[str, dict], except_id: str | None = None) -> list[datetime]:
    out = []
    for item in items.values():
        if item["id"] != except_id and item["state"] == "driven" and item["drive"]:
            at = parse_ts(item["drive"].get("at"))
            if at is not None:
                out.append(at)
    return out


@dataclass
class Pace:
    ok: bool
    dispatchable: int | None = None
    bands: dict[str, str] = field(default_factory=dict)
    short_reset_min: float | None = None
    reason: str = ""

    def deferral(self) -> str:
        """非空＝該 deferred(quota) 的原因（PRD §1.2 原則 3 雙軸、原則 5 失效即保守）。"""
        if not self.ok:
            return self.reason or "pace_unreadable"
        if self.dispatchable is None or self.dispatchable < 1:
            return "dispatchable<1"
        hot = [k for k, b in self.bands.items() if b in BANDS_BLOCKING]
        return f"band:{','.join(sorted(hot))}" if hot else ""


def parse_pace(text: str, now: datetime) -> Pace:
    """`--pace` 全文→`Pace`；缺可派數或缺任何短窗／週窗軸＝讀不到（保守）。"""
    match = _DISPATCH_RE.search(text)
    bands: dict[str, str] = {}
    short: list[float] = []
    for kind, minutes, band in _AXIS_RE.findall(text):
        if kind in SHORT_AXES + WEEK_AXES:
            bands[kind] = band
            if kind in SHORT_AXES and minutes:
                short.append(float(minutes))
    seen = lambda axes: any(k in bands for k in axes)  # noqa: E731
    if not match or not seen(SHORT_AXES) or not seen(WEEK_AXES):
        return Pace(False, reason="pace_unreadable")
    return Pace(True, int(match.group(1)), bands, min(short) if short else None)


def read_pace(now: datetime) -> Pace:
    """跑 `python tools/session_resume_planner.py --pace`（零 token）；rc≠0／逾時＝讀不到。"""
    try:
        argv = [console_python(), str(_TOOLS / "session_resume_planner.py"), "--pace"]
        proc = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=120, check=False,
                              creationflags=_NO_WINDOW, cwd=str(_TOOLS.parent))
    except (OSError, subprocess.SubprocessError):
        return Pace(False, reason="pace_failed")
    return parse_pace(proc.stdout, now) if proc.returncode == 0 else Pace(False, reason="pace_rc")


def interactive_active(root: Path, now: datetime, projects_dir: Path | None = None,
                       interval_seconds: int = quota_messages.HALT_QUIESCE_SECONDS) -> bool:
    """同專案有互動 session 在 `interval_seconds` 內做過真實工作（判準＝`transcript_activity`
    的對話記錄，與哨兵雙駕駛同一家；檔案 mtime 只作成本預篩）。目錄讀不到＝當作沒有。"""
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(Path(root).resolve()))
    base = (projects_dir if projects_dir is not None
            else platform_utils.claude_home() / "projects" / slug)
    cutoff = now.timestamp() - interval_seconds
    try:
        files = [p for p in base.glob("*.jsonl") if p.stat().st_mtime >= cutoff]
    except OSError:
        return False
    for path in files:
        stamp = transcript_activity.newest_conversation_at(quota_limits.session_transcripts(path))
        if stamp is not None and stamp >= cutoff:
            return True
    return False
