"""realverify 副作用租約帳（L2；DES RealVerify_SideEffect_Isolation §5，工作包 S5）。

WHY：事故（DEF-200-632）＝載具登記了正式前綴排程、代理被額度切斷，`finally`／批次尾掃都沒機會跑，
真排程到點真開幽靈 session。結構正解不是「更勤勞地清」，而是**先登記帳列、後動作**：帳列住在
`~/.autosdd/realverify_leases/<run_id>.jsonl`（只追加），下一次 realverify 執行開頭（`replay`）或
`tools/realverify.py sweep` 都能依帳撤掉「主人行程已死」的孤兒；主人可驗證仍活者永不當孤兒。

帳列種類（`ALL_KINDS`）：sandbox_root、sched_job、transcript_dir、process、worktree、temp_file；狀態
intent／made／revoked／unverified／abandoned／closed。撤銷序＝process → sched_job → worktree → 目錄
（`UNDO_ORDER`）。非排程原語住 `leases_undo.py`；發現式掃描住 `leases_discover.py`。
鎖：realverify 套件內呼叫排程撤銷（`sched.remove`／`backend.disarm`）的函式只准在本檔（見測試）。
`sessionctl status` 的孤兒行（`sessionctl/rv_orphans.py`）只讀本帳的 `kind`／`state`／`owner_*`／
`expires_at` 欄與目錄名，不匯入本檔；那些常數與本檔的相等由測試核對。
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from lib import sandbox_scope

from . import leases_undo, sched

ALL_KINDS = ("sandbox_root", "sched_job", "transcript_dir", "process", "worktree", "temp_file")
#: 舊名保留（相容）：`sessionctl/rv_orphans.py`（`status` 的孤兒行，REQ-SE-36）只讀排程種類，兩者相等由  # noqa: E501
#: `test_sessionctl_se_isolation` 鎖。其餘種類的孤兒由 `sweep`／`run` 開頭處理；`status` 暫不計它們——  # noqa: E501
#: 待 rv_orphans 擴讀全種類後，把本常數改成 `ALL_KINDS`（持有者＝sessionctl 站點包，本包不碰該檔）。
KINDS = ("sched_job",)
UNDO_ORDER = ("process", "sched_job", "worktree", "sandbox_root", "transcript_dir", "temp_file")
_PENDING = ("intent", "made", "unverified")
LEASE_DIR = Path.home() / ".autosdd" / "realverify_leases"  # 測試以 mock.patch.object 換掉
PRUNE_AFTER_S = 24 * 3600  # 已全數結清的帳檔留一天供事後稽核，之後刪（帳不無限長）
SCHED_EXPIRY_MIN = sandbox_scope.LEASE_MAX  # 載具排程的 OS 自毀：觸發後 30 分
ABANDON_WHY_MIN = 8
_NAME_OK = re.compile(r"^[A-Za-z0-9_*.\-]+$")


def _now() -> datetime:
    return datetime.now().astimezone()


def _iso(t: datetime) -> str:
    return t.isoformat(timespec="seconds")


_RUN_ID: str | None = None


def current_run_id() -> str:
    """本行程的 run_id（懶產生；一個 realverify 行程一份帳檔）。"""
    global _RUN_ID  # noqa: PLW0603 — 行程級單例，與帳檔一對一
    if _RUN_ID is None:
        _RUN_ID = f"{time.strftime('%Y%m%dT%H%M%S')}-{os.getpid()}-{uuid.uuid4().hex[:6]}"
    return _RUN_ID


def _path(run_id: str) -> Path:
    return LEASE_DIR / f"{run_id}.jsonl"


def append(run_id: str, kind: str, ident: str, state: str, *, undo: str = "",
           expires_at: datetime | None = None, owner_pid: int | None = None,
           owner_started: str | None = None, meta: dict | None = None) -> None:
    """原子追加一列（單次 O_APPEND 寫入；讀者不會看到半列）。主人預設＝本行程。"""
    if kind not in ALL_KINDS and kind != "run":
        raise ValueError(f"未知帳列種類：{kind}")
    pid = os.getpid() if owner_pid is None else owner_pid
    if owner_started is None and owner_pid is None:
        owner_started = sandbox_scope.proc_probe(pid)[1]
    row = {"at": _iso(_now()), "kind": kind, "ident": ident, "undo": undo,
           "owner_pid": pid, "owner_started": owner_started,
           "expires_at": _iso(expires_at) if expires_at else None, "state": state}
    if meta:
        row["meta"] = meta
    LEASE_DIR.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8")
    fd = os.open(str(_path(run_id)), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)


def read_rows(path: Path) -> list[dict]:
    out: list[dict] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for ln in text.splitlines():
        try:
            row = json.loads(ln)
        except ValueError:
            continue  # 半截／壞列：略過這一列，不讓一列壞掉癱瘓整本帳
        if isinstance(row, dict):
            out.append(row)
    return out


_rows = read_rows


def _pending(rows: list[dict]) -> dict[tuple[str, str], dict]:
    """每個 (kind, ident) 取最後一列；狀態仍在 `_PENDING` 者＝待撤。"""
    last: dict[tuple[str, str], dict] = {}
    for r in rows:
        if r.get("kind") in ALL_KINDS:
            last[(str(r["kind"]), str(r.get("ident")))] = r
    return {k: v for k, v in last.items() if v.get("state") in _PENDING}


def owner_verdict(row: dict, now: datetime) -> str:
    """`alive`（可驗證存活：pid 在且建立時間相符）／`dead`（pid 不在或建立時間不符）／`unknown`
    （存活但驗不到建立時間）。unknown 時由呼叫端以 `expires_at` 已過為準（D-16）。"""
    alive, started = sandbox_scope.proc_probe(row.get("owner_pid"))
    if not alive:
        return "dead"
    recorded = row.get("owner_started")
    if not started or not recorded:
        return "unknown"
    try:
        gap = abs((datetime.fromisoformat(started)
                    - datetime.fromisoformat(recorded)).total_seconds())
    except ValueError:
        return "unknown"
    return "alive" if gap <= sandbox_scope._OWNER_START_TOLERANCE_SEC else "dead"  # noqa: SLF001


def _is_orphan(row: dict, now: datetime) -> bool:
    verdict = owner_verdict(row, now)
    if verdict == "alive":
        return False
    if verdict == "dead":
        return True
    exp = row.get("expires_at")
    try:
        return bool(exp) and datetime.fromisoformat(exp) <= now
    except ValueError:
        return False


# ── 登記（先帳後動作）────────────────────────────────────────────────────────────────────

def track(name: str, *, run_id: str | None = None, expires_at: datetime | None = None) -> str:
    """先寫 `intent` 列，再由呼叫端做動作；回正規化後的工作名。產品代為註冊的排程（案例只知道名字）
    也走這裡，使「誰負責撤」在動作前就在帳上。"""
    name = sched.task_name(name)
    append(run_id or current_run_id(), "sched_job", name, "intent",
           undo=f"Unregister-ScheduledTask {name}", expires_at=expires_at)
    return name


def track_kind(kind: str, ident: str | Path, *, meta: dict | None = None, run_id: str | None = None,
               undo: str = "", state: str = "intent") -> str:
    """任一種類的 `intent`（動作**之前**呼叫）；回 ident 字串。路徑類 ident 原樣記（呼叫端先 resolve）。"""  # noqa: E501
    append(run_id or current_run_id(), kind, str(ident), state, undo=undo or f"undo {kind}", meta=meta)  # noqa: E501
    return str(ident)


def made(kind: str, ident: str | Path, *, run_id: str | None = None) -> None:
    append(run_id or current_run_id(), kind, str(ident), "made")


def settle(kind: str, ident: str | Path, state: str = "revoked", *, run_id: str | None = None) -> None:  # noqa: E501
    """載具自己清完一項後把它結帳（避免帳上永遠掛著已清掉的東西）。"""
    append(run_id or current_run_id(), kind, str(ident), state)


def track_process(keys: list[str], *, pid: int | None = None, run_id: str | None = None) -> str:
    """行程帳列。`keys`＝沙盒 sid 與根路徑（撤銷時命令列含其一才砍）；`pid` 給了只認該行程
    （並記下它的建立時間防 pid 重用）；沒給＝依 key 掃全部行程（涵蓋產品自己開的視窗，D-8）。"""
    meta: dict = {"keys": [k for k in keys if k]}
    if pid is not None:
        meta["pid"] = pid
        meta["pid_started"] = sandbox_scope.proc_probe(pid)[1]
    ident = f"pid:{pid}" if pid is not None else f"sid:{keys[0] if keys else '?'}"
    return track_kind("process", ident, meta=meta, run_id=run_id, undo="kill verified process")


def register_once(name: str, run_at_local_iso: str, arguments: str, *,
                  expire_minutes: int = SCHED_EXPIRY_MIN) -> dict:
    """帳列 intent → 登記（觸發器帶 EndBoundary＋DeleteExpiredTaskAfter，OS 自毀雙保險）→ made。
    登記失敗時帳上留著 intent，replay 會撤（也許半登記）。"""
    fire = datetime.fromisoformat(run_at_local_iso)
    expire_at = fire + timedelta(minutes=expire_minutes)
    name = track(name, expires_at=expire_at.astimezone())  # naive 視為本機時間
    end_local = expire_at.replace(tzinfo=None).isoformat(timespec="seconds")
    rb = sched.register_once(name, run_at_local_iso, arguments, expire_at_local_iso=end_local)
    append(current_run_id(), "sched_job", name, "made", expires_at=None)
    return rb


# ── 排程撤銷（全套件唯一家，REQ-SE-34）────────────────────────────────────────────────────

def revoke_sched(name: str) -> bool:
    """撤排程並回讀確認不存在；回是否真的不存在（Get-ScheduledTask 的 rc 不可信，憑證是回讀值）。"""
    sched.remove(name)
    return sched.read_back(name) is None


def revoke_sched_like(pattern: str) -> list[str]:
    """依樣式（須含 8 碼十六進位：沙盒 sid8，絕不接受寬泛樣式）撤排程；回撤掉的工作名。"""
    if not _NAME_OK.match(pattern) or not re.search(r"[0-9a-f]{8}", pattern):
        raise ValueError(f"拒絕寬泛樣式：{pattern}")
    gone = sorted(sched.list_actions(pattern))
    for name in gone:
        revoke_sched(name)
    return gone


def revoke_oldwin(prefix: str) -> list[str]:
    """沙盒舊視窗重試排程（`oldwin_prefix` 寫的專屬前綴）；回撤不掉的工作名（RESIDUE 來源）。"""
    import schedule_backend  # noqa: PLC0415 — lazy：產品後端（含 macOS launchd）
    backend = schedule_backend.select()
    for name in backend.list_jobs(prefix) or []:
        backend.disarm(name)
    return list(backend.list_jobs(prefix) or [])


# ── 撤銷／重放 ───────────────────────────────────────────────────────────────────────────

@dataclass
class Report:
    revoked: list[str] = field(default_factory=list)
    unrevoked: list[str] = field(default_factory=list)   # 含 unverified（仍待撤）
    info: dict[str, str] = field(default_factory=dict)   # ident → 撤不掉的原因


def _undo_row(row: dict) -> tuple[str, str]:
    """`(revoked|unverified|stuck, 說明)`；任何例外＝stuck（不假裝結清）。"""
    kind, ident = row["kind"], str(row["ident"])
    meta = row.get("meta") or {}
    try:
        if kind == "sched_job":
            return ("revoked", "unregister") if revoke_sched(ident) else ("stuck", "回讀仍在")
        if kind == "process":
            return leases_undo.revoke_process(meta)
        if kind == "worktree":
            ok, why = leases_undo.revoke_worktree(ident, str(meta.get("host") or ""))
        else:
            ok, why = leases_undo.revoke_path(kind, ident)
        return ("revoked", why) if ok else ("stuck", why)
    except Exception as exc:  # noqa: BLE001
        return "stuck", f"{type(exc).__name__}: {exc}"


def _revoke_rows(run_id: str, rows: list[dict], report: Report, *, close: bool = True) -> None:
    pend = _pending(rows)
    if not pend:
        # 全部項目都已個別結清（`settle`／`revoke_items`）：仍須補寫 closed，否則帳永遠停在
        # revoked 而非 closed（RV-SE11「本批所有帳檔都應 closed」；`account_state` 也靠它判）。
        last = rows[-1] if rows else None
        if close and last is not None and not (last.get("kind") == "run" and last.get("state") == "closed"):  # noqa: E501
            append(run_id, "run", "*", "closed")
        return
    ordered = sorted(pend.items(), key=lambda kv: (UNDO_ORDER.index(kv[0][0]), kv[0][1]))
    clean = True
    for (kind, ident), r in ordered:
        result, why = _undo_row(r)
        keep = {"owner_pid": r.get("owner_pid"), "owner_started": r.get("owner_started"),
                "meta": r.get("meta")}
        if result == "revoked":
            append(run_id, kind, ident, "revoked", **keep)
            report.revoked.append(f"{kind} {ident}")
        else:
            clean = False
            if result == "unverified":
                append(run_id, kind, ident, "unverified", **keep)
            report.unrevoked.append(f"{kind} {ident}")
            report.info[f"{kind} {ident}"] = why
    if clean and close:
        append(run_id, "run", "*", "closed")


def revoke_run(run_id: str | None = None) -> list[str]:
    """本 run 的全部待撤項目（案例收尾；我們就是主人，不判存活）。回撤不掉的 ident。"""
    rid = run_id or current_run_id()
    rep = Report()
    _revoke_rows(rid, read_rows(_path(rid)), rep)
    return [i.split(" ", 1)[1] for i in rep.unrevoked]


def revoke_run_kinds(kinds: tuple[str, ...], run_id: str | None = None) -> list[str]:
    """只撤本 run 指定種類（案例中途要先收行程／排程，目錄留到最後）。回撤不掉的 ident。"""
    rid = run_id or current_run_id()
    rows = [r for r in read_rows(_path(rid)) if r.get("kind") in kinds]
    rep = Report()
    _revoke_rows(rid, rows, rep, close=False)
    return [i.split(" ", 1)[1] for i in rep.unrevoked]


def revoke_items(items: list[tuple[str, str]], run_id: str | None = None) -> list[str]:
    """只撤本 run 指定的 `(kind, ident)`（單一沙盒清理用，不波及同 run 其他沙盒）。回撤不掉的 ident。"""  # noqa: E501
    rid = run_id or current_run_id()
    want = {(k, str(i)) for k, i in items}
    rows = [r for r in read_rows(_path(rid)) if (r.get("kind"), str(r.get("ident"))) in want]
    rep = Report()
    _revoke_rows(rid, rows, rep, close=False)
    return [i.split(" ", 1)[1] for i in rep.unrevoked]


def replay_report(now: datetime | None = None) -> Report:
    """掃全部帳檔：主人已死（或存活驗不到且 `expires_at` 已過）的待撤列 ⇒ 撤；主人可驗證存活者
    不動（含別的視窗正在跑的 run）。已結清且逾 `PRUNE_AFTER_S` 的帳檔刪除。"""
    t = now or _now()
    rep = Report()
    if not LEASE_DIR.is_dir():
        return rep
    for p in sorted(LEASE_DIR.glob("*.jsonl")):
        rows = read_rows(p)
        pend = _pending(rows)
        if not pend:
            try:
                if time.time() - p.stat().st_mtime > PRUNE_AFTER_S:
                    p.unlink()
            except OSError:
                pass
            continue
        orphans = {k for k, r in pend.items() if _is_orphan(r, t)}
        if orphans:
            _revoke_rows(p.stem, [r for r in rows if (r.get("kind"), str(r.get("ident"))) in orphans], rep)  # noqa: E501
    return rep


def replay(now: datetime | None = None) -> list[str]:
    """`replay_report` 的精簡版：只回 `unrevoked`（撤不掉）清單的 ident。"""
    return [i.split(" ", 1)[1] for i in replay_report(now).unrevoked]


def orphan_idents(now: datetime | None = None) -> list[str]:
    """唯讀：現在 `replay` 會撤哪些項目（`sweep --dry-run` 用）。"""
    t = now or _now()
    out: list[str] = []
    if LEASE_DIR.is_dir():
        for p in sorted(LEASE_DIR.glob("*.jsonl")):
            out += [f"{k[1]}" for k, r in _pending(read_rows(p)).items() if _is_orphan(r, t)]
    return out


def orphan_rows(now: datetime | None = None) -> list[tuple[str, str]]:
    """唯讀：`(kind, ident)` 清單（含 kind，給 sweep --dry-run 與測試）。"""
    t = now or _now()
    out: list[tuple[str, str]] = []
    if LEASE_DIR.is_dir():
        for p in sorted(LEASE_DIR.glob("*.jsonl")):
            out += [k for k, r in _pending(read_rows(p)).items() if _is_orphan(r, t)]
    return out


def live_idents(now: datetime | None = None, kind: str = "sched_job") -> set[str]:
    """帳上「主人可驗證存活、未結清」的某種類 ident——發現式掃描不得動它們（別的視窗的合法物）。"""
    t = now or _now()
    live: set[str] = set()
    if LEASE_DIR.is_dir():
        for p in LEASE_DIR.glob("*.jsonl"):
            for (k, ident), r in _pending(read_rows(p)).items():
                if k == kind and not _is_orphan(r, t):
                    live.add(ident)
    return live


_live_idents = live_idents


def own_pending(run_id: str, kind: str = "sched_job") -> set[str]:
    return {i for (k, i) in _pending(read_rows(_path(run_id))) if k == kind}


def discover_sweep(now: datetime | None = None, *, dry_run: bool = False,
                   own_run_id: str | None = None) -> list[str]:
    """舊規則的發現式掃描（未登記殘留）：`AutoSDD_RV_*` 排程不在任何「主人存活」帳列內 ⇒ 撤。
    `own_run_id` 的帳列視為已收尾（批次結束時呼叫，仍在的就是漏清）。回被判為殘留的工作名
    （dry_run 時不撤）。沙盒字樣／RVprod 的擴充規則見 `leases_discover.scan`。"""
    keep = live_idents(now)
    if own_run_id:
        keep -= own_pending(own_run_id)
    gone: list[str] = []
    for name in sched.list_rv():
        if name in keep:
            continue
        gone.append(name)
        if not dry_run:
            revoke_sched(name)
    return gone


def account_state(run_id: str, now: datetime | None = None) -> str:
    """`live`（帳主人可驗證存活且未 closed）／`closed`／`dead`／`missing`（RVprod 判孤兒用，D-27）。"""  # noqa: E501
    rows = read_rows(_path(run_id))
    if not rows:
        return "missing"
    if rows[-1].get("kind") == "run" and rows[-1].get("state") == "closed":
        return "closed"
    return "dead" if owner_verdict(rows[0], now or _now()) == "dead" else "live"


# ── abandon（人工出口，D-11）──────────────────────────────────────────────────────────────

def abandon(run_id: str, why: str) -> list[str]:
    """把該帳未完成列記 `abandoned`（附 why）後寫 `closed`；**只動帳**，不砍行程、不刪檔（MU-SE-24）。
    回被放棄的 ident。why 不足 8 字 ⇒ ValueError；帳不存在 ⇒ FileNotFoundError。"""  # noqa: E501
    if len(why.strip()) < ABANDON_WHY_MIN:
        raise ValueError(f"--why 至少 {ABANDON_WHY_MIN} 字")
    rows = read_rows(_path(run_id))
    if not rows:
        raise FileNotFoundError(f"沒有這份帳：{run_id}")
    gone: list[str] = []
    for (kind, ident), r in _pending(rows).items():
        append(run_id, kind, ident, "abandoned", undo=f"abandoned: {why.strip()}",
               owner_pid=r.get("owner_pid"), owner_started=r.get("owner_started"), meta=r.get("meta"))  # noqa: E501
        gone.append(f"{kind} {ident}")
    append(run_id, "run", "*", "closed")
    return gone


def abandoned_paths() -> set[str]:
    """全帳 `abandoned` 的路徑類 ident（正規化後；發現式掃描見到它或其子路徑只記 note）。"""
    out: set[str] = set()
    if not LEASE_DIR.is_dir():
        return out
    for p in LEASE_DIR.glob("*.jsonl"):
        for r in read_rows(p):
            if r.get("state") == "abandoned" and r.get("kind") in ("sandbox_root", "transcript_dir",
                                                                    "temp_file", "worktree"):
                out.add(os.path.normcase(str(Path(str(r["ident"])).resolve())))
    return out
