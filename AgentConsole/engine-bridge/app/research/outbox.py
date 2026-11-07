"""檔案 outbox 與持久化協定（ADR-003 D2；Architecture §10.4；TCS AT-960-2-5、2-6）。

協定：**寫檔**（原子 replace，重用 `fsutil.write_text_atomic`，不新增 `os.replace`／
`rename`／`move` 站點）→ **outbox 記錄** → **DB 交易**（資料列＋`research_events`＋
`last_event_seq`）→ **標完成**。任一步之後中斷，重啟 `replay()` 都收斂到一致：outbox 有記錄而
DB 尚未套用＝補套用（檔早已在）；DB 已套用而尚未標完成＝重放時被操作的自然鍵／狀態等值擋下
（不重複列、不重複事件）；從不會出現「DB 有列而檔案不存在」（檔先於列）。僅有的必然窗口是
「檔寫了、outbox 還沒記」：留下的是孤立檔案（有檔無列），由 `:reconcile` 報告、不修復。

outbox 是 append-only 的 JSONL：每個操作一行（`kind`＋payload＋要驗證存在的檔案），完成時
另追加一行 `{"done": <op_id>}`。重放永遠依檔案順序、一次一筆（FIFO）：同一時刻至多一筆
「已套用未標完成」，所以操作只需對自己冪等。DB 不可用時，stage run 轉 `BLOCKED_DB` 並發
`research.alert`（兩者一併落 outbox，恢復後重放可見）；無法套用的「毒藥」記錄（應用層衝突、
檔案缺失）標 `rejected` 後略過，不堵住佇列。
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .. import fsutil
from . import layout
from .db import (
    OPS,
    ResearchConflict,
    ResearchDb,
    ResearchDbError,
    ResearchGuardError,
    jsonable,
    utc_now,
)
from .gates.reconcile import derive_flow_status

OUTBOX_VERSION = 1
#: 重放完成後 outbox 檔案超過這個大小且沒有待處理記錄時，整檔壓縮（重寫為空）。
COMPACT_BYTES = 256 * 1024
STEPS = ("file", "outbox", "db", "done")


def backoff_seconds(attempt: int, *, base: float = 1.0, cap: float = 60.0) -> float:
    """DB 不可用時的重試退避（指數、有上限）；`attempt` 從 0 起。"""
    return float(min(cap, base * (2 ** max(attempt, 0))))


@dataclass(frozen=True)
class FileRef:
    """操作依賴的檔案：重放前驗證它存在且位元組的 sha256 相符（絕不先有列、後有檔）。"""

    workspace: str
    rel: str
    sha256: str


@dataclass(frozen=True)
class FileWrite:
    workspace: Path
    rel: str
    text: str
    overwrite: bool = True


@dataclass(frozen=True)
class Op:
    kind: str
    research_id: str
    payload: dict[str, Any]
    files: tuple[FileRef, ...] = ()
    op_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: str = field(default_factory=lambda: utc_now().isoformat())

    def to_record(self) -> dict[str, Any]:
        return {"v": OUTBOX_VERSION, "op_id": self.op_id, "kind": self.kind,
                "research_id": self.research_id, "payload": jsonable(self.payload),
                "files": [{"workspace": f.workspace, "rel": f.rel, "sha256": f.sha256}
                          for f in self.files], "created_at": self.created_at}

    @staticmethod
    def from_record(rec: dict[str, Any]) -> Op:
        return Op(kind=rec["kind"], research_id=rec["research_id"], payload=rec["payload"],
                  files=tuple(FileRef(**f) for f in rec.get("files", [])), op_id=rec["op_id"],
                  created_at=rec["created_at"])


class DbBlocked(Exception):
    """DB 不可用：記錄留在 outbox 待重放（呼叫端回 503 `db_blocked`）。"""

    def __init__(self, op: Op, cause: ResearchDbError) -> None:
        super().__init__(f"db blocked at {op.kind}: {cause}")
        self.op = op
        self.cause = cause


class Outbox:
    """append-only JSONL。單行程假設（L-R9）：以執行緒鎖序列化；每次追加 flush＋fsync。"""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()

    def _append_line(self, record: dict[str, Any]) -> None:
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            torn = False
            if self.path.is_file() and self.path.stat().st_size > 0:
                with self.path.open("rb") as probe:
                    probe.seek(-1, os.SEEK_END)
                    torn = probe.read(1) != b"\n"
            with self.path.open("a", encoding="utf-8", newline="\n") as fh:
                if torn:                       # 上次寫到一半（沒有換行）：隔開，壞行讀取時略過
                    fh.write("\n")
                fh.write(line)
                fh.flush()
                os.fsync(fh.fileno())

    def append(self, op: Op) -> None:
        self._append_line(op.to_record())

    def mark_done(self, op_id: str, *, rejected: str | None = None) -> None:
        record: dict[str, Any] = {"v": OUTBOX_VERSION, "done": op_id, "at": utc_now().isoformat()}
        if rejected is not None:
            record["rejected"] = rejected
        self._append_line(record)

    def read_all(self) -> list[dict[str, Any]]:
        """全部可解析的記錄（壞行略過；檔案不存在回空）。"""
        with self._lock:
            if not self.path.is_file():
                return []
            text = self.path.read_text(encoding="utf-8", errors="replace")
        records = []
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict):
                records.append(rec)
        return records

    def pending(self) -> list[Op]:
        records = self.read_all()
        done = {r["done"] for r in records if "done" in r}
        return [Op.from_record(r) for r in records if "op_id" in r and r["op_id"] not in done]

    def compact(self, *, force: bool = False) -> bool:
        """沒有待處理記錄時整檔重寫為空（原子）；有待處理則只保留它們。回是否真的重寫。"""
        with self._lock:
            if not self.path.is_file():
                return False
            if not force and self.path.stat().st_size < COMPACT_BYTES:
                return False
            keep = self.pending()
            text = "".join(json.dumps(op.to_record(), ensure_ascii=False,
                                      separators=(",", ":")) + "\n" for op in keep)
            fsutil.write_text_atomic(self.path, text)
            return True


@dataclass
class ReplayReport:
    applied: list[str] = field(default_factory=list)          # 這次真的寫進 DB 的 op_id
    already_applied: list[str] = field(default_factory=list)  # DB 早已有（只補標完成）
    rejected: list[tuple[str, str]] = field(default_factory=list)   # (op_id, 規則／原因)
    blocked: str | None = None                                # 卡在哪個 op_id（DB 不可用）


def _stage_run_of(op: Op) -> str | None:
    """操作綁定的 stage run（DB 不可用時要把它標 BLOCKED_DB）。"""
    p = op.payload
    if op.kind.startswith("stage_run."):
        return p.get("stage_run_id")
    found = p.get("stage_run_id") or (p.get("round") or {}).get("stage_run_id")
    return str(found) if found else None


class DurableWriter:
    """驅動「檔→outbox→DB 交易→標完成」。`after_step(step, op)` 供測試在四步之後注入中斷。"""

    def __init__(self, db: ResearchDb, outbox: Outbox, *,
                 after_step: Callable[[str, Op], None] | None = None) -> None:
        self._db = db
        self._outbox = outbox
        self._after = after_step
        self._lock = threading.RLock()
        self._project_locks: dict[str, threading.RLock] = {}
        self._project_guard = threading.Lock()
        self._fsm_state_of: Callable[[Mapping[str, Any]], str | None] | None = None
        self._unsettled: set[str] = set()

    @property
    def outbox(self) -> Outbox:
        return self._outbox

    @property
    def db(self) -> ResearchDb:
        return self._db

    def project_lock(self, research_id: str) -> threading.RLock:
        """每專案一把行程內鎖：呼叫端用它包住「前置檢查→persist」（樂觀鎖、避免寫檔互踩）。
        鎖順序恆為 專案鎖 → 全域鎖。"""
        with self._project_guard:
            return self._project_locks.setdefault(str(research_id), threading.RLock())

    def has_pending(self, research_id: str | None = None) -> bool:
        return any(research_id is None or op.research_id == str(research_id)
                   for op in self._outbox.pending())

    # ── 內部 ─────────────────────────────────────────────────────────────────────────────
    def _step(self, step: str, op: Op) -> None:
        if self._after is not None:
            self._after(step, op)

    def _file_problem(self, op: Op) -> bool:
        for ref in op.files:
            found = layout.file_digest(Path(ref.workspace), ref.rel)
            if found is None or found[0] != ref.sha256:
                return True
        return False

    def _block(self, op: Op) -> None:
        """DB 不可用：把綁定的 stage run 標 BLOCKED_DB 並發 `research.alert`，兩者只落 outbox
        （同一 stage run 只排一次）。"""
        run_id = _stage_run_of(op)
        if run_id is None:
            return
        for rec in self._outbox.pending():
            if rec.kind == "stage_run.update" and rec.payload.get("stage_run_id") == run_id and (
                    rec.payload.get("status") == "BLOCKED_DB"):
                return
        self._outbox.append(Op("stage_run.update", op.research_id, {
            "stage_run_id": run_id, "status": "BLOCKED_DB", "exit_reason": "db_blocked",
            "finished_at": utc_now().isoformat(), "actor": "bridge"}))
        self._outbox.append(Op("event.append", op.research_id, {
            "research_id": op.research_id, "event_type": "research.alert", "actor": "bridge",
            "payload": {"kind": "BLOCKED_DB", "detail": f"{op.kind} 無法寫入資料庫"},
            "ref_kind": "alert", "ref_id": uuid.uuid4().hex}))

    def _drain(self, report: ReplayReport, *, stop_after: str | None = None) -> dict[str, Any]:
        """依序套用待處理記錄，直到全部完成或某筆失敗。回 {op_id: 結果}。"""
        results: dict[str, Any] = {}
        for op in self._outbox.pending():
            if self._file_problem(op):          # 檔案缺或被改：永遠套用不了＝毒藥，標 rejected 略過
                report.rejected.append((op.op_id, "file_missing"))
                self._outbox.mark_done(op.op_id, rejected="file_missing")
                results[op.op_id] = ResearchGuardError("file_missing", op.op_id)
                if op.op_id == stop_after:
                    break
                continue
            try:
                result = self._db.apply(op.kind, op.payload)
            except ResearchDbError as exc:
                report.blocked = op.op_id
                self._block(op)
                raise DbBlocked(op, exc) from exc
            except (ResearchConflict, ResearchGuardError) as exc:
                rule = getattr(exc, "reason", None) or getattr(exc, "rule", "rejected")
                report.rejected.append((op.op_id, str(rule)))
                self._outbox.mark_done(op.op_id, rejected=str(rule))
                results[op.op_id] = exc
                if op.op_id == stop_after:
                    break
                continue
            self._step("db", op)
            (report.applied if result.get("applied", True) else report.already_applied).append(
                op.op_id)
            self._outbox.mark_done(op.op_id)
            self._step("done", op)
            results[op.op_id] = result
            if op.op_id == stop_after:
                break
        return results

    # ── 公開 ─────────────────────────────────────────────────────────────────────────────
    def persist(self, op: Op, *, writes: Sequence[FileWrite] = ()) -> dict[str, Any]:
        """檔→outbox→DB 交易→標完成。回這個操作的 DB 結果；應用層衝突／守衛拒絕原樣拋出
        （記錄已標 `rejected`）；DB 不可用拋 `DbBlocked`（記錄留在 outbox）。"""
        with self._lock:
            written = [layout.write_workspace_file(w.workspace, w.rel, w.text,
                                                   overwrite=w.overwrite) for w in writes]
            for w, done in zip(writes, written, strict=True):
                ref = next((f for f in op.files if Path(f.workspace) == w.workspace
                            and f.rel == w.rel), None)
                if ref is not None and ref.sha256 != done.sha256 and w.overwrite:
                    raise ValueError(f"操作宣告的 sha256 與實際寫入不符：{w.rel}")
            self._step("file", op)
            self._outbox.append(op)
            self._step("outbox", op)
            results = self._drain(ReplayReport(), stop_after=op.op_id)
            outcome = results.get(op.op_id)
            if isinstance(outcome, Exception):
                raise outcome
            if outcome is None:
                raise ResearchGuardError("not_applied", op.op_id)
            return outcome

    def bind_fsm_reader(self, reader: Callable[[Mapping[str, Any]], str | None]) -> None:
        """注入「專案列 → 外環 FSM 現態」讀取器（由 orchestrator 建構時綁定）。綁定當下補校正
        「重放時尚無讀取器」而累積的專案（`_unsettled`）。"""
        with self._lock:
            self._fsm_state_of = reader
            ids, self._unsettled = sorted(self._unsettled), set()
            if ids and not self._outbox.pending():
                self._settle_cursors(ids)

    def _settle_cursors(self, research_ids: Sequence[str]) -> None:
        """D-128：重放完成那一刻，對每個受影響專案以 `derive_flow_status`（進行中 stage run＋FSM
        現態）重新衍生 `flow_status`，在**同一個資料庫交易**內鎖專案列、讀 stage run、經既有
        `project.cursor` 操作寫回（與現值相同就跳過、不發事件）。FSM 讀取（子行程）在交易之外先做，
        不讓子行程握著列鎖。既有 `FAILED` 不被重放洗掉（沿 `derive_flow_status` 的語意：只有後續
        成功收尾才把它衍生掉）。"""
        reader = self._fsm_state_of
        assert reader is not None
        for rid in research_ids:
            row0 = self._db.get_project(rid)
            if row0 is None:
                continue
            fsm_state = reader(row0)
            with self._db.transaction() as tx:
                row = tx.lock_project(rid)
                runs = tx.rows("SELECT status FROM {s}.research_stage_runs WHERE research_id = %s "
                               "AND status IN ('QUEUED', 'RUNNING')", (rid,))
                # 進行中的分流列（PENDING／RUNNING）與進行中的 stage run 同屬「RUNNING」
                routes = tx.rows("SELECT status FROM {s}.research_route_decisions WHERE "
                                 "research_id = %s AND status IN ('PENDING', 'RUNNING')", (rid,))
                status = derive_flow_status(
                    [r["status"] for r in runs] + ["RUNNING" for _ in routes], fsm_state,
                    last_run_failed=row["flow_status"] == "FAILED")
                flow = {"step": row["flow_step"], "phase": row["flow_phase"], "status": status,
                        "detail": row["flow_detail"]}
                OPS["project.cursor"](tx, {"research_id": rid, "actor": "bridge", "flow": flow})

    def replay(self) -> ReplayReport:
        """重放全部待處理記錄（重啟時、DB 復原後、或定期重試）。可重複呼叫、冪等。重放把 outbox
        清空的那一次，順手校正受影響專案的游標（D-128；BLOCKED_DB 期間游標不重新衍生）。"""
        report = ReplayReport()
        with self._lock:
            affected = sorted({op.research_id for op in self._outbox.pending()})
            try:
                self._drain(report)
            except DbBlocked:
                return report
            if not self._outbox.pending():
                self._outbox.compact()
                if affected and report.applied:
                    if self._fsm_state_of is None:
                        self._unsettled.update(affected)
                    else:
                        self._settle_cursors(affected)
        return report
