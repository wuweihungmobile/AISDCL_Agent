"""realverify 排程租約帳（L2；DES RealVerify_SideEffect_Isolation §5，工作包 S5）。

WHY：事故（DEF-200-632）＝載具登記了正式前綴排程、代理被額度切斷，`finally`／批次尾掃都沒機會跑，
真排程到點真開幽靈 session。結構正解不是「更勤勞地清」，而是**先登記帳列、後動作**：帳列住在
`~/.autosdd/realverify_leases/<run_id>.jsonl`（只追加），下一次 realverify 執行開頭（`replay`）或
`tools/realverify.py sweep` 都能依帳撤掉「主人行程已死」的孤兒；主人可驗證仍活者永不當孤兒。

本模組目前承擔 `sched_job` 一種帳列（`AutoSDD_RV_*` 排程）；其他種類（沙盒家、行程…）由 S5 其餘
部分加入時擴 `KINDS` 與 `_undo`——未知種類在 `append` 即拒，不靜默吞。
鎖：realverify 套件內呼叫排程撤銷（`sched.remove`）的函式只准在本檔（見測試）。
"""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from lib import sandbox_scope

from . import sched

KINDS = ("sched_job",)
_PENDING = ("intent", "made", "unverified")
LEASE_DIR = Path.home() / ".autosdd" / "realverify_leases"  # 測試以 mock.patch.object 換掉
PRUNE_AFTER_S = 24 * 3600  # 已全數結清的帳檔留一天供事後稽核，之後刪（帳不無限長）
SCHED_EXPIRY_MIN = sandbox_scope.LEASE_MAX  # 載具排程的 OS 自毀：觸發後 30 分


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
           owner_started: str | None = None) -> None:
    """原子追加一列（單次 O_APPEND 寫入；讀者不會看到半列）。主人預設＝本行程。"""
    if kind not in KINDS and kind != "run":
        raise ValueError(f"未知帳列種類：{kind}")
    pid = os.getpid() if owner_pid is None else owner_pid
    if owner_started is None and owner_pid is None:
        owner_started = sandbox_scope.proc_probe(pid)[1]
    row = {"at": _iso(_now()), "kind": kind, "ident": ident, "undo": undo,
           "owner_pid": pid, "owner_started": owner_started,
           "expires_at": _iso(expires_at) if expires_at else None, "state": state}
    LEASE_DIR.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8")
    fd = os.open(str(_path(run_id)), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)


def _rows(path: Path) -> list[dict]:
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


def _pending(rows: list[dict]) -> dict[str, dict]:
    """每個 ident 取最後一列；狀態仍在 `_PENDING` 者＝待撤。"""
    last: dict[str, dict] = {}
    for r in rows:
        if r.get("kind") == "sched_job":
            last[str(r.get("ident"))] = r
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


def _undo_sched(name: str) -> bool:
    """撤排程並回讀確認不存在；回是否真的不存在（Get-ScheduledTask 的 rc 不可信，憑證是回讀值）。"""
    sched.remove(name)
    return sched.read_back(name) is None


def _revoke_rows(run_id: str, rows: list[dict]) -> list[str]:
    """逐列撤銷；回撤不掉的 ident。成功寫 `revoked`，全部結清再寫 `closed`。"""
    stuck: list[str] = []
    pend = _pending(rows)
    if not pend:
        return stuck
    for ident, r in pend.items():
        if _undo_sched(ident):
            append(run_id, "sched_job", ident, "revoked", owner_pid=r.get("owner_pid"),
                   owner_started=r.get("owner_started"))
        else:
            stuck.append(ident)
    if not stuck:
        append(run_id, "run", "*", "closed")
    return stuck


# ── 登記（先帳後動作）────────────────────────────────────────────────────────────────────

def track(name: str, *, run_id: str | None = None, expires_at: datetime | None = None) -> str:
    """先寫 `intent` 列，再由呼叫端做動作；回正規化後的工作名。產品代為註冊的排程（案例只知道名字）
    也走這裡，使「誰負責撤」在動作前就在帳上。"""
    name = sched.rv_name(name)
    append(run_id or current_run_id(), "sched_job", name, "intent",
           undo=f"Unregister-ScheduledTask {name}", expires_at=expires_at)
    return name


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


# ── 撤銷／重放／發現式掃描 ───────────────────────────────────────────────────────────────

def revoke_run(run_id: str | None = None) -> list[str]:
    """本 run 的全部待撤排程（案例收尾；我們就是主人，不判存活）。回撤不掉的 ident。"""
    rid = run_id or current_run_id()
    return _revoke_rows(rid, _rows(_path(rid)))


def replay(now: datetime | None = None) -> list[str]:
    """掃全部帳檔：主人已死（或存活驗不到且 `expires_at` 已過）的待撤列 ⇒ 撤；主人可驗證存活者
    不動（含別的視窗正在跑的 run）。回 `unrevoked`（撤不掉）清單。已結清且逾 `PRUNE_AFTER_S`
    的帳檔刪除。"""
    t = now or _now()
    unrevoked: list[str] = []
    if not LEASE_DIR.is_dir():
        return unrevoked
    for p in sorted(LEASE_DIR.glob("*.jsonl")):
        rows = _rows(p)
        pend = _pending(rows)
        if not pend:
            try:
                if time.time() - p.stat().st_mtime > PRUNE_AFTER_S:
                    p.unlink()
            except OSError:
                pass
            continue
        orphans = [r for r in pend.values() if _is_orphan(r, t)]
        if not orphans:
            continue
        ids = {o["ident"] for o in orphans}
        unrevoked += _revoke_rows(p.stem, [r for r in rows if r.get("ident") in ids])
    return unrevoked


def orphan_idents(now: datetime | None = None) -> list[str]:
    """唯讀：現在 `replay` 會撤哪些排程（`sweep --dry-run` 用）。"""
    t = now or _now()
    out: list[str] = []
    if LEASE_DIR.is_dir():
        for p in sorted(LEASE_DIR.glob("*.jsonl")):
            out += [i for i, r in _pending(_rows(p)).items() if _is_orphan(r, t)]
    return out


def _live_idents(now: datetime) -> set[str]:
    """帳上「主人可驗證存活、未結清」的排程名——發現式掃描不得動它們（別的視窗的合法排程）。"""
    live: set[str] = set()
    if not LEASE_DIR.is_dir():
        return live
    for p in LEASE_DIR.glob("*.jsonl"):
        for ident, r in _pending(_rows(p)).items():
            if not _is_orphan(r, now):
                live.add(ident)
    return live


def discover_sweep(now: datetime | None = None, *, dry_run: bool = False,
                   own_run_id: str | None = None) -> list[str]:
    """發現式掃描（未登記殘留）：`AutoSDD_RV_*` 排程不在任何「主人存活」帳列內 ⇒ 撤。`own_run_id`
    的帳列視為已收尾（批次結束時呼叫，仍在的就是漏清）。回被判為殘留的工作名（dry_run 時不撤）。"""
    t = now or _now()
    keep = _live_idents(t)
    if own_run_id:
        mine = {i for i in _pending(_rows(_path(own_run_id)))}
        keep -= mine
    gone: list[str] = []
    for name in sched.list_rv():
        if name in keep:
            continue
        gone.append(name)
        if not dry_run:
            _undo_sched(name)
    return gone
