"""OIR 事件帳本：schema 驗證、讀取（壞行計數）、寫入鎖內配號與追加。
DES §3.1／§3.2；REQ-WP-01／02／06／07。

append-only 的 JSONL（UTF-8、LF、一行一事件）。WHY：無人驅動器與互動 session 可能同時寫，追加比改寫
衝突面小；fold 以 `(ts, seq)` 排序，`seq`＝該行在檔內的行號（1 起算），所以事件不必自帶序號。
鎖＝獨佔建檔鎖（`lib.apply_lock`，不用 `msvcrt`／`fcntl`），鎖檔住 `trace_dir()/openitems/locks/`
（不住 repo，免得把工作樹弄髒）。壞行（非 JSON／缺共通欄／ev 不認得）讀取時跳過並計入 `bad`，
不讓一行壞資料拖垮整本帳。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from lib import apply_lock, endurance_env

from . import params as oi_params

ID_RE = re.compile(r"^OI-(\d{8})-(\d{3,})$")
KINDS = ("auto", "observe", "human", "k1")
EVENTS = ("open", "drive", "start", "attempt", "close", "escalate", "convert", "retire")
RESULTS = ("pass", "fail", "deferred")
DEFER_REASONS = ("interactive", "quota", "busy", "window_cap", "interrupted")
WHY_MIN_CHARS = 8
LOCK_TIMEOUT_SECONDS = 30.0
LOCK_STALE_SECONDS = 120.0


class Reject(Exception):
    """事件不合 schema／範圍：`problems` 逐條列出；呼叫端 rc 2、帳本不變。"""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("；".join(problems))
        self.problems = problems


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def parse_ts(raw: object) -> datetime | None:
    """帶 offset 的 ISO 時間→aware datetime；缺 offset 或不是字串回 `None`（不猜時區）。"""
    if not isinstance(raw, str):
        return None
    try:
        out = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return out if out.tzinfo is not None else None


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _int(value: object) -> bool:
    return type(value) is int


def _check_spec_problems(check: object) -> list[str]:
    if not isinstance(check, dict):
        return ["check 必須是物件"]
    if "realverify" in check:
        return [] if _nonempty(check["realverify"]) and set(check) == {"realverify"} \
            else ["check.realverify 必須是非空字串且不得夾帶其他鍵"]
    argv, rule = check.get("argv"), check.get("pass")
    if not (isinstance(argv, list) and argv and all(_nonempty(a) for a in argv)):
        return ["check 必須是 {realverify} 或 {argv:[…], pass}"]
    if rule == "rc0":
        return []
    if isinstance(rule, str) and rule.startswith("regex:") and len(rule) > 6:
        try:
            re.compile(rule[6:])
        except re.error:
            return ["check.pass 的正規式不合法"]
        return []
    return ["check.pass 必須是 rc0 或 regex:<式>"]


def _open_problems(ev: dict, params: dict) -> list[str]:
    out = [f"open 缺 `{k}`" for k in ("title", "source", "scope") if not _nonempty(ev.get(k))]
    kind = ev.get("kind")
    if kind not in KINDS:
        return [*out, f"kind 必須是 {'／'.join(KINDS)}"]
    source = ev.get("source") if _nonempty(ev.get("source")) else ""
    norm = source.replace("\\", "/")
    allowed = norm.startswith(tuple(params["source_prefixes"]))
    if source and (".." in norm.split("/") or not allowed):
        out.append("source 必須指向 TCS／缺陷帳本／ADR／PRD 等已立案文件的座標（收件範圍白名單，"
                   "REQ-WP-06）")
    if kind in ("auto", "observe"):
        out += _check_spec_problems(ev.get("check")) if "check" in ev else [f"{kind} 必有 check"]
    if kind == "observe" and parse_ts(ev.get("due")) is None:
        out.append("observe 必有 due（帶 offset 的 ISO 時間）")
    if kind == "human" and (not _nonempty(ev.get("why_not_auto"))
                            or len(ev["why_not_auto"].strip()) < WHY_MIN_CHARS):
        out.append(f"human 必有 why_not_auto（至少 {WHY_MIN_CHARS} 字）")
    return out


def _attempt_problems(ev: dict) -> list[str]:
    out = []
    if not _int(ev.get("n")) or ev["n"] < 0:
        out.append("attempt 缺 n")
    if ev.get("result") not in RESULTS:
        out.append("attempt.result 必須是 pass／fail／deferred")
    if ev.get("result") == "deferred" and ev.get("reason") not in DEFER_REASONS:
        out.append("deferred 必有 reason（interactive／quota／busy／window_cap／interrupted）")
    if not _int(ev.get("drive_seq")):
        out.append("attempt 缺 drive_seq")
    return out


def event_problems(ev: object, params: dict) -> list[str]:
    """單一事件的 schema 問題清單（空＝合格）。共通欄＋各 `ev` 的專屬必填欄（DES §3.2）。"""
    if not isinstance(ev, dict):
        return ["事件必須是 JSON 物件"]
    kind = ev.get("ev")
    out: list[str] = []
    if kind not in EVENTS:
        return [f"ev 必須是 {'／'.join(EVENTS)}"]
    if parse_ts(ev.get("ts")) is None:
        out.append("ts 必須是帶 offset 的 ISO 時間")
    if not (isinstance(ev.get("id"), str) and ID_RE.match(ev["id"])):
        out.append("id 必須是 OI-<YYYYMMDD>-<NNN>")
    by = ev.get("by")
    if not (isinstance(by, str) and (by == "human" or (
            by.partition(":")[0] in ("sid", "driver") and by.partition(":")[2].strip()))):
        out.append("by 必須是 human／sid:<id>／driver:<名>")
    if kind == "open":
        out += _open_problems(ev, params)
    elif kind == "drive":
        out += [f"drive 缺 `{k}`" for k in ("task", "credential") if not _nonempty(ev.get(k))]
        if parse_ts(ev.get("at")) is None:
            out.append("drive.at 必須是帶 offset 的 ISO 時間")
    elif kind == "start":
        out += [f"start 缺 `{k}`" for k in ("drive_seq", "pid", "budget_minutes")
                if not _int(ev.get(k))]
        if "proc_start" not in ev:
            out.append("start 缺 proc_start")
    elif kind == "attempt":
        out += _attempt_problems(ev)
    elif kind == "close":
        out += [] if _nonempty(ev.get("evidence")) else ["close 缺 evidence"]
    elif kind == "escalate":
        out += [] if _nonempty(ev.get("reason")) else ["escalate 缺 reason"]
    elif kind == "convert":
        if ev.get("kind") not in KINDS:
            out.append("convert.kind 必須是四型之一")
        out += [] if _nonempty(ev.get("why")) else ["convert 缺 why"]
        out += _check_spec_problems(ev["check"]) if "check" in ev else []
        if "due" in ev and parse_ts(ev["due"]) is None:
            out.append("convert.due 必須是帶 offset 的 ISO 時間")
    elif kind == "retire":
        out += [f"retire 缺 `{k}`" for k in ("why", "basis") if not _nonempty(ev.get(k))]
    return out


def read_events(path: Path) -> tuple[list[dict], int]:
    """`(事件清單, 壞行數)`。每個事件附 `seq`（行號，1 起算）；壞行跳過。檔不存在＝空帳。"""
    try:
        raw = Path(path).read_bytes()
    except FileNotFoundError:
        return [], 0
    events, bad = [], 0
    for seq, line in enumerate(raw.decode("utf-8", errors="replace").split("\n"), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            bad += 1
            continue
        if not (isinstance(obj, dict) and obj.get("ev") in EVENTS and parse_ts(obj.get("ts"))
                and isinstance(obj.get("id"), str) and ID_RE.match(obj["id"])):
            bad += 1
            continue
        obj["seq"] = seq
        events.append(obj)
    return events, bad


def next_id(events: list[dict], day: datetime | None = None) -> str:
    """當日最大號＋1（呼叫端必須在寫入鎖內呼叫，REQ-WP-07）。"""
    stamp = (day or datetime.now().astimezone()).strftime("%Y%m%d")
    top = 0
    for ev in events:
        m = ID_RE.match(ev["id"])
        if m and m.group(1) == stamp:
            top = max(top, int(m.group(2)))
    return f"OI-{stamp}-{top + 1:03d}"


def lock_path_for(ledger: Path) -> Path:
    key = hashlib.sha256(os.path.realpath(ledger).encode("utf-8")).hexdigest()[:16]
    return endurance_env.trace_dir() / "openitems" / "locks" / f"{key}.lock"


def append(root: Path, make: Callable[[list[dict]], list[dict]], *, lock_path: Path | None = None) \
        -> list[dict]:
    """全部寫事件動詞的唯一追加路徑。在鎖內讀現有事件→`make(events)` 回傳要追加的事件（可不帶
    `ts`，缺則補現在）→逐一驗 schema（任一不合整批拒收，帳本不變）→以單次寫入追加。回寫入的事件。"""
    root = Path(root)
    params = oi_params.load(root)
    ledger = oi_params.ledger_path(root)
    lock = lock_path or lock_path_for(ledger)
    lock.parent.mkdir(parents=True, exist_ok=True)
    with apply_lock.acquire(lock, LOCK_TIMEOUT_SECONDS, LOCK_STALE_SECONDS):
        events, _bad = read_events(ledger)
        new = [dict(e) for e in make(events)]
        problems: list[str] = []
        for ev in new:
            ev.setdefault("ts", now_iso())
            problems += [f"{ev.get('ev')}/{ev.get('id')}：{p}" for p in event_problems(ev, params)]
        if problems:
            raise Reject(problems)
        if not new:
            return []
        ledger.parent.mkdir(parents=True, exist_ok=True)
        payload = "".join(json.dumps(e, ensure_ascii=False, separators=(",", ":")) + "\n"
                          for e in new).encode("utf-8")
        # 撕裂的末行（上次寫到一半、沒有 LF）先補一個換行，讓它自成一行壞行、不黏住新事件
        if ledger.exists() and ledger.stat().st_size and not _ends_with_lf(ledger):
            payload = b"\n" + payload
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0)
        fd = os.open(str(ledger), flags, 0o644)
        try:
            view = memoryview(payload)
            while view:
                view = view[os.write(fd, view):]
            os.fsync(fd)
        finally:
            os.close(fd)
    return new


def _ends_with_lf(path: Path) -> bool:
    with path.open("rb") as handle:
        handle.seek(-1, os.SEEK_END)
        return handle.read(1) == b"\n"
