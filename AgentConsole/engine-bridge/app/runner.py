"""RunManager／RunHandle：spawn `python -m autoclaude`、監督、pause／resume／stop／restore。

設計重點（每一條都有 2026-10-14 對真引擎的實證，細節見 app/logparse.py、app/checkpoints.py 檔頭）：
  · 引擎 stdout 寫進 `<run>/engine-N.log`（不是 pipe）：Bridge 重啟、孫行程繼承 pipe 都不會讓
    讀取端卡死；監督執行緒 tail 該檔、逐行解析。
  · 引擎不寫步驟級 checkpoint ⇒ 步驟邊界由「下一步驟的啟動行」推得；pause 在邊界終止
    引擎整棵行程樹，Bridge 以引擎自己的 FileStateRepository 寫入 checkpoint，resume／restore
    不帶 --fresh 重啟，由引擎的 `_resolve_start` 從 step_idx 接續。剛 spawn 的下一步驟
    claude 會被一併終止、續跑時重做。
  · 狀態寫入單一寫者：每個 spawn 一條監督執行緒；API 呼叫只設旗標與（短暫）改狀態，
    都在 handle.lock 內。
  · 事件先 append、欄位後更新（SSE 以「狀態終態 ＋ 游標已追上」判定串流結束，
    順序反了會漏最後一則）。
"""
from __future__ import annotations

import contextvars
import copy
import json
import logging
import os
import subprocess
import sys
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from . import procutil, sdd_run, security
from .checkpoints import (
    CheckpointHistory,
    build_checkpoint_state,
    load_engine_checkpoint,
    write_engine_checkpoint,
)
from .db import BridgeDb
from .errors import ApiError, invalid_state, lock_held, not_found, unprocessable
from .events import EventStore
from .locks import AdvisoryLock, LockBusy, LockUnavailable
from .logparse import LineParser, ParsedLine, StepDef, StepTracker
from .models import DB_STATUS, TERMINAL_STATUSES, RunCreateIn, RunStatus
from .resources import ResourceSampler
from .runstate import RunPaths, RunRecord, load_record, save_record
from .sdd_sync import (
    RunFacts,
    reason_exit_cancelled,
    reason_exit_completed,
    reason_exit_failed,
    reason_exit_spawn_failed,
    terminal_decision,
)
from .settings import Settings

logger = logging.getLogger("bridge.runner")

#: 引擎子行程環境要先剝除的、繼承自 Bridge 自己環境的名字（ADR-XPLAT-016 §9「剝除」列）。開發機先
#: 在 SDD session 匯出再起 Bridge 是常態；不剝的話引擎子行程會悄悄拿到寫入權杖、狀態目錄指標與別的
#: 專案鍵（子行程內的 AI 步驟就能自己呼叫「核准凍結」）。之後只有含 `sdd` 區塊的 run 才設
#: `SDD_PROJECT`。
_CHILD_ENV_STRIPPED = frozenset({"BRIDGE_SDD_WRITE_TOKEN", "SDD_STATE_DIR", "SDD_PROJECT"})

_POLL_SECONDS = 0.05
#: 單則 log 事件的字元上限：引擎的「啟動行」會把整份 prompt 印出來（可達數十 KB），
#: 原樣進 events.jsonl／SSE 會讓串流與磁碟被少數幾行撐爆。解析用的是完整原文。
MAX_LOG_LINE_CHARS = 8000
_USAGE_KEYS = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens",
               "output_tokens")
_NO_PLAYBOOK_DUMP_WIDTH = 10**9
_KILL_GIVE_UP_SECONDS = 15.0
_ACTIVE_STATUSES = {RunStatus.INITIALIZING.value, RunStatus.RUNNING.value,
                    RunStatus.PAUSING.value, RunStatus.CANCELLING.value}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _yaml_dump(data: Any) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False,
                          width=_NO_PLAYBOOK_DUMP_WIDTH)


def materialize_config(overrides: dict[str, Any], paths: RunPaths) -> dict[str, Any]:
    """config_overrides ＋ Bridge 管控的鍵。引擎的狀態目錄一律在 run 工作區，不污染 execution_path；
    儲存後端固定 yaml_only（Bridge 的 pause／resume／restore 靠檔案式 checkpoint）。"""
    cfg = {k: copy.deepcopy(v) for k, v in overrides.items()
           if k not in security.MANAGED_KEYS}
    cfg["checkpoint_dir"] = str(paths.checkpoints)
    cfg["log_dir"] = str(paths.logs)
    cfg["backup_dir"] = str(paths.backups)
    cfg["scripts_dir"] = str(paths.scripts)
    cfg["storage"] = {"mode": "yaml_only"}
    return cfg


def _sanitized_log_name(step_id: str) -> str:
    # 引擎自己的檔名淨化（單一真相源）：raw log 檔名由它決定，不能在這裡另抄一份規則。
    from autoclaude.utils.logger import _sanitize_log_filename

    return _sanitize_log_filename(step_id)


def _load_steps(paths: RunPaths, rec: RunRecord) -> list[StepDef]:
    """重啟後從 run 工作區的 playbook.yaml 還原步驟（含 prompt：邊界判定要靠它比對）。"""
    try:
        doc = yaml.safe_load(paths.playbook.read_text(encoding="utf-8")) or {}
        return [StepDef(t["step_id"], t.get("name", t["step_id"]), t.get("prompt", ""),
                        t.get("goal_task_id")) for t in doc.get("tasks", [])]
    except (OSError, yaml.YAMLError, KeyError, TypeError):
        logger.warning("無法讀回 %s，改用 run.json 內的步驟摘要（沒有 prompt，邊界判定較不精確）",
                       paths.playbook)
        return [StepDef(s["step_id"], s.get("name", s["step_id"]), "", s.get("goal_task_id"))
                for s in rec.steps]


class RunHandle:
    """單一 run 的記憶體狀態與監督邏輯。"""

    def __init__(self, mgr: RunManager, rec: RunRecord, paths: RunPaths,
                 steps: list[StepDef], request_env: dict[str, str] | None = None):
        self.mgr = mgr
        self.rec = rec
        self.paths = paths
        self.steps = steps
        self.request_env = dict(request_env or {})
        self.lock = threading.RLock()
        self.history = CheckpointHistory(paths.history)
        self.tracker = StepTracker(steps, rec.completed_step_ids)
        self.completed_log: list[str] = []
        self.proc: subprocess.Popen[bytes] | None = None
        self.supervisor: threading.Thread | None = None
        self.pause_requested = False
        self.stop_requested = False
        self.shutting_down = False
        self._boundary_hit = False
        self._deferred_start: int | None = None
        self._spawn_completed = 0
        self._end: Any = None
        self._last_error = ""
        self._escalation = ""
        self._escalation_step = ""
        #: 建立時放行但值得出聲的事（`POST /autoclaude/runs` 的 201 `warnings`；不落盤）。
        self.create_warnings: list[dict[str, Any]] = []
        self._store: EventStore | None = None

    # ── 事件／狀態 ───────────────────────────────────────────────────────────
    @property
    def store(self) -> EventStore:
        if self._store is None:
            self._store = self.mgr.store_for_handle(self)
        return self._store

    def emit(self, event: str, **payload: Any) -> dict[str, Any]:
        return self.store.append(event, payload)

    def alert(self, level: str, code: str, message: str, **extra: Any) -> None:
        self.emit("alert", level=level, code=code, message=message, **extra)

    def persist(self) -> None:
        try:
            save_record(self.paths, self.rec)
        except OSError as exc:
            logger.error("run.json 寫入失敗（%s）：%s", self.rec.run_id, exc)

    def set_status(self, status: RunStatus, reason: str = "", **updates: Any) -> None:
        with self.lock:
            self.emit("status", status=status.value, reason=reason)    # 事件先、欄位後
            self.rec.status = status.value
            self.rec.reason = reason
            for key, value in updates.items():
                setattr(self.rec, key, value)
            self.persist()
            db_fields: dict[str, Any] = {"status": DB_STATUS[status]}
            if status in TERMINAL_STATUSES:
                db_fields["completed_at"] = datetime.fromisoformat(self.rec.completed_at) \
                    if self.rec.completed_at else None
            self.mgr.mirror(self.rec.run_id, **db_fields)

    def live_engine_pid(self) -> int | None:
        """引擎行程樹的根 pid；引擎沒有在跑（尚未 spawn、PAUSED、終態、剛結束）＝None。"""
        with self.lock:
            proc = self.proc
            if proc is None or proc.poll() is not None:
                return None
            return proc.pid

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            rec = self.rec
            pid = self.live_engine_pid()
            # 資源：只讀取樣器最近一筆（請求路徑不取樣、不阻塞）；引擎不在跑、還沒有第一筆、
            # 或最近一筆已過期（超過 15 秒）都是 None（契約 v1.3 §3.1.2）。
            resources = None if pid is None else self.mgr.sampler.latest(rec.run_id, pid)
            return {
                "run_id": rec.run_id, "status": rec.status, "pid": rec.pid,
                "started_at": rec.started_at, "completed_at": rec.completed_at,
                "exit_code": rec.exit_code, "current_step": rec.current_step,
                "completed_steps": len(rec.completed_step_ids), "total_steps": rec.total_steps,
                "tokens_used": rec.tokens_used, "last_event_seq": self.store.last_seq,
                "reason": rec.reason, "project": rec.project,
                "execution_path": rec.execution_path, "bridge_instance": rec.bridge_instance,
                "current_step_number": rec.current_step_number, "attempt": rec.attempt,
                "resources": resources,
            }

    # ── 啟動 ─────────────────────────────────────────────────────────────────
    def start(self, *, fresh: bool, ignored_overrides: list[str] | None = None) -> None:
        with self.lock:
            self.set_status(RunStatus.INITIALIZING, "run 已建立，準備啟動引擎")
            if ignored_overrides:
                self.alert("warning", "CONFIG_OVERRIDE_IGNORED",
                           "這些 config_overrides 由 Bridge 管控、未被採用（引擎狀態一律放在 run "
                           f"工作區、儲存後端固定 yaml_only）：{', '.join(ignored_overrides)}")
            self._spawn(fresh=fresh)

    def _child_env(self) -> dict[str, str]:
        # 先剝除繼承自 Bridge 的 SDD 寫入面名字（比對一律照大寫：Windows 的 os.environ 鍵恆為大
        # 寫）。
        env = {k: v for k, v in os.environ.items() if k.upper() not in _CHILD_ENV_STRIPPED}
        for key, value in self.request_env.items():
            # Windows 行為＝環境變數名不分大小寫，且 os.environ 以大寫保存；統一轉大寫免得重複。
            env[key.upper() if sys.platform == "win32" else key] = value
        # 引擎輸出含中文與符號：不論主機 locale（Windows cp950）一律 UTF-8，且不緩衝。
        env.update({"PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
        if self.rec.sdd:
            # 只有含 `sdd` 區塊的 run 才有 SDD_PROJECT（adapter 靠它在多專案共處的狀態目錄選對檔）。
            # 不注入 SDD_STATE_DIR：引擎沒有任何讀者需要它，給了只會讓子行程內的 AI 步驟拿到
            # 「直接呼叫 FSM CLI 簽自己」的現成指向（ADR §7.3）。
            env["SDD_PROJECT"] = str(self.rec.sdd["fsm_project"])
        return env

    def _spawn(self, *, fresh: bool) -> None:
        rec = self.rec
        index = rec.spawn_count + 1
        log_path = self.paths.engine_log(index)
        argv = [sys.executable, "-m", "autoclaude", str(self.paths.playbook),
                "--config", str(self.paths.config)]
        if fresh:
            argv.append("--fresh")
        self._boundary_hit = False
        self._deferred_start = None
        self._spawn_completed = 0
        self._end = None
        self._last_error = ""
        self._escalation = ""
        self._escalation_step = ""
        try:
            with log_path.open("wb") as log_fh:
                proc = subprocess.Popen(
                    argv, cwd=rec.execution_path, env=self._child_env(), stdin=subprocess.DEVNULL,
                    stdout=log_fh, stderr=subprocess.STDOUT, **procutil.popen_platform_kwargs())
        except OSError as exc:
            rec.completed_at = _now()
            self.set_status(RunStatus.FAILED, f"無法啟動引擎：{exc}", pid=None, exit_code=None)
            self.mgr.release_lock(self)
            raise ApiError(500, "spawn_failed", detail=str(exc)) from exc
        self.proc = proc
        rec.spawn_count = index
        rec.pid = proc.pid
        rec.last_pid = proc.pid
        rec.pid_create_time = procutil.process_create_time(proc.pid)
        rec.bridge_instance = self.mgr.settings.bridge_instance
        if rec.started_at is None:
            rec.started_at = _now()
        self.mgr.mirror(rec.run_id, subprocess_pid=proc.pid,
                        bridge_instance=rec.bridge_instance, advisory_lock_key=rec.db_lock_key)
        self.set_status(RunStatus.RUNNING, f"引擎已啟動（pid={proc.pid}，第 {index} 次 spawn）")
        # 監督執行緒沿用「觸發這次 spawn 的請求」的 trace id：contextvars 不會自動傳進新執行緒，
        # 所以在這裡複製當下的 context 讓它在其中執行（契約 §3.1.1；日誌行的 trace_id 由此而來）。
        ctx = contextvars.copy_context()
        self.supervisor = threading.Thread(
            target=ctx.run, args=(self._supervise, proc, log_path), daemon=True,
            name=f"bridge-run-{rec.run_id[:8]}-{index}")
        self.supervisor.start()
        self.mgr.sampler.request_sample()          # 讓第一次輪詢就有值（CPU 0.0）；只喚醒、不阻塞

    # ── 監督迴圈 ─────────────────────────────────────────────────────────────
    def _supervise(self, proc: subprocess.Popen[bytes], log_path: Path) -> None:
        try:
            self._supervise_loop(proc, log_path)
        except Exception as exc:                                  # noqa: BLE001
            logger.exception("監督執行緒崩潰（run=%s）", self.rec.run_id)
            self._abort_after_supervisor_crash(proc, exc)

    def _supervise_loop(self, proc: subprocess.Popen[bytes], log_path: Path) -> None:
        parser = LineParser()
        partial = b""
        victims: list[Any] = []
        kill_deadline = 0.0
        escalated = False
        with log_path.open("rb") as fh:
            while True:
                exited = proc.poll() is not None      # 先取快照再讀檔：確保結束後一定讀乾淨
                chunk = fh.read(1 << 20)
                if chunk:
                    *lines, partial = (partial + chunk).split(b"\n")
                    for raw in lines:
                        self._on_line(parser, raw)
                if not victims and (self.stop_requested or self._boundary_hit):
                    victims = procutil.begin_terminate(proc.pid)
                    kill_deadline = time.monotonic() + self.mgr.settings.stop_grace_seconds
                if victims:
                    left = procutil.survivors(victims, exclude_pid=proc.pid)
                    if left and not escalated and time.monotonic() >= kill_deadline:
                        killed = procutil.force_kill(left)
                        escalated = True
                        grace = self.mgr.settings.stop_grace_seconds
                        self.alert("warning", "FORCE_KILL",
                                   f"終止訊號後 {grace:g}s 仍未退出，已強制終止 pid={killed}")
                    give_up = time.monotonic() >= kill_deadline + _KILL_GIVE_UP_SECONDS
                    if exited and not chunk and (not left or give_up):
                        break
                elif exited and not chunk:
                    break
                if not chunk:
                    time.sleep(_POLL_SECONDS)
        if partial:
            self._on_line(parser, partial)
        proc.wait()
        self._finalize(proc.returncode)

    def _on_line(self, parser: LineParser, raw: bytes) -> None:
        text = raw.decode("utf-8", errors="replace").rstrip("\r")
        parsed = parser.parse(text)
        shown = text if len(text) <= MAX_LOG_LINE_CHARS else (
            text[:MAX_LOG_LINE_CHARS] + f"…（已截斷，原長 {len(text)} 字元）")
        with self.lock:
            self.emit("log", level=parsed.level, line=shown)
            if parsed.level in ("ERROR", "CRITICAL"):
                self._last_error = text
            try:
                self._dispatch(parsed)
            except Exception:                                     # noqa: BLE001
                # 事件解析／鏡像的 bug 不得讓整個 run 被連坐終止：記下來、發 alert，引擎照跑。
                logger.exception("處理引擎輸出行失敗（run=%s）：%s", self.rec.run_id, text[:200])
                self.alert("warning", "BRIDGE_INTERNAL",
                           "Bridge 處理一行引擎輸出時出錯，已略過該行的步驟事件（引擎不受影響）")

    def _dispatch(self, parsed: ParsedLine) -> None:
        if self._deferred_start is not None and parsed.kind in (
                "attempt_start", "token_peak", "run_end"):
            # 邊界之後引擎仍在推進（終止訊號到達前的毫秒級視窗）⇒ 邊界步驟確實跑了：補發 STARTED。
            self.tracker.begin(self._deferred_start)
            self._emit_step(self._deferred_start, "STARTED", 1)
            self._deferred_start = None
        if parsed.kind == "attempt_start":
            self._on_attempt_start(parsed)
        elif parsed.kind == "token_peak":
            self._on_token_peak(parsed)
        elif parsed.kind == "state":
            self._on_state(parsed)
        elif parsed.kind == "run_end":
            self._end = parsed.end

    # ── 步驟事件 ─────────────────────────────────────────────────────────────
    def _emit_step(self, idx: int, status: str, attempt: int, error: str | None = None) -> None:
        step = self.steps[idx]
        rec = self.rec
        if status in ("STARTED", "RETRYING"):
            rec.current_step, rec.current_step_number, rec.attempt = step.step_id, idx + 1, attempt
        else:
            rec.current_step, rec.current_step_number, rec.attempt = None, None, 0
        env = self.emit("step", step_id=step.step_id, step_number=idx + 1, status=status,
                        attempt=attempt, name=step.name, total_steps=len(self.steps))
        self.persist()
        # execution_steps.step_number 對應 SSE 事件序（PRD §7.1.7），位置放進 input。
        self.mgr.mirror_step(
            run_id=rec.run_id, task_id=step.goal_task_id, seq=env["seq"],
            action=f"{step.step_id}: {step.name}", status=status,
            input_data={"step_id": step.step_id, "position": idx + 1, "attempt": attempt},
            error=error)

    def _on_attempt_start(self, parsed: ParsedLine) -> None:
        tracker = self.tracker
        decision = tracker.classify_start(parsed.prompt)
        if decision is None:
            return
        if decision.retry:
            self._emit_step(decision.idx, "RETRYING", tracker.retry())
            return
        if decision.completes is not None:
            self._complete_current_step()
            if self.pause_requested and self._spawn_completed >= 1:
                # 邊界：步驟 k 已完成、步驟 k+1 剛 spawn 就被我們終止。STARTED 先不發——
                # 若引擎在被終止前真的又往前跑了，_dispatch 會補發；沒有就是被中止的 spawn，
                # 續跑時由引擎重做。
                self._boundary_hit = True
                self._deferred_start = decision.idx
                return
        tracker.begin(decision.idx)
        self._emit_step(decision.idx, "STARTED", 1)

    def _complete_current_step(self) -> None:
        done = self.tracker.complete_current()
        if done is None:
            return
        idx, attempt = done
        step = self.steps[idx]
        self.completed_log.append(f"[{step.step_id}] {step.name} ✓ (attempt {attempt})")
        self._spawn_completed += 1
        self.rec.completed_step_ids = list(self.tracker.completed)
        self._emit_step(idx, "COMPLETED", attempt)
        self._snapshot_after(step)

    def _snapshot_after(self, step: StepDef) -> None:
        nxt = self.tracker.next_idx
        state = build_checkpoint_state(
            playbook_path=self.paths.playbook, project=self.rec.project, steps=self.steps,
            step_idx=nxt, completed_ids=self.tracker.completed, completed_log=self.completed_log,
            peak_token_pct=self.rec.peak_token_pct)
        meta = self.history.add(name=f"after-{step.step_id}", step_idx=nxt,
                                step_id=state["step_id"], state=state)
        self.mgr.mirror_checkpoint(self.rec.run_id, meta, state)

    def _on_token_peak(self, parsed: ParsedLine) -> None:
        rec = self.rec
        pct = parsed.pct or 0.0
        rec.peak_token_pct = max(rec.peak_token_pct, pct)
        rec.tokens_used += self._tokens_of_last_attempt(parsed.step_id or "")
        self.emit("token", pct=pct, tokens_used=rec.tokens_used)
        self.persist()
        self.mgr.mirror(rec.run_id, total_tokens_used=rec.tokens_used)

    def _tokens_of_last_attempt(self, step_id: str) -> int:
        """從引擎寫的原始輸出（`playbook_<step>.log`，每 attempt 一行 JSON）取最後一筆 usage。"""
        path = self.paths.logs / f"playbook_{_sanitized_log_name(step_id)}.log"
        try:
            with path.open("rb") as fh:
                fh.seek(0, os.SEEK_END)
                fh.seek(max(0, fh.tell() - (1 << 20)))
                tail = fh.read().decode("utf-8", errors="replace")
        except OSError:
            return 0
        for line in reversed(tail.splitlines()):
            try:
                usage = json.loads(line).get("usage")
            except (ValueError, AttributeError):
                continue
            if isinstance(usage, dict):
                return sum(int(usage.get(k, 0) or 0) for k in _USAGE_KEYS
                           if isinstance(usage.get(k, 0), (int, float)))
        return 0

    def _on_state(self, parsed: ParsedLine) -> None:
        if parsed.state == "ESCALATION":
            self._escalation = parsed.detail
            self._escalation_step = parsed.step_id or ""        # 終態同步的 reason 要記是哪一步
            failed = self.tracker.fail_current()
            if failed is not None:
                self._emit_step(failed[0], "FAILED", failed[1], error=parsed.detail)
            self.alert("error", "ESCALATION", parsed.detail, step_id=parsed.step_id)
        elif parsed.state in ("TOKEN_HALT", "LIMIT_RETRY"):
            self.alert("warning", parsed.state, parsed.detail, step_id=parsed.step_id)

    # ── 結束 ─────────────────────────────────────────────────────────────────
    def _finalize(self, returncode: int | None) -> None:
        with self.lock:
            rec = self.rec
            self.proc = None
            common: dict[str, Any] = {"pid": None, "pid_create_time": None}
            self.mgr.mirror(rec.run_id, subprocess_pid=None)
            # 取消要求來得太晚（引擎在終止訊號生效前已自然成功收尾，rc=0 且有成功結尾行）⇒
            # 事實是 COMPLETED，不是 CANCELLED；被終止的引擎 rc 一定非 0，不會被誤判成這種情況。
            finished_first = returncode == 0 and self._end is not None and self._end.success
            if self.stop_requested and not finished_first:
                rec.completed_at = _now()
                status = RunStatus.FAILED if self.shutting_down else RunStatus.CANCELLED
                reason = "Bridge 關閉：引擎已終止" if self.shutting_down else "使用者取消"
                self.tracker.fail_current()
                self.set_status(status, reason, exit_code=returncode, **common)
                self.mgr.release_lock(self)
            elif self._boundary_hit and not (self._end is not None and self._end.success):
                self._finish_pause(common)
            else:
                self._finish_normally(returncode, common)
            self.store.close()
            self.persist()
        # 終態事件已先發布；現在（handle.lock 之外）才對 FSM 做委派同步——CLI 最壞 20 秒，不該卡住
        # snapshot()。代價是「終態事件」到「FSM 回 IMPLEMENTATION」之間約 0.1 秒的視窗。
        self._sdd_sync_terminal()

    # ── SDD 委派同步（ADR-XPLAT-016 §10）─────────────────────────────────────────────────────
    def _sdd_context(self) -> sdd_run.SddContext | None:
        return sdd_run.SddContext.from_record(self.rec.sdd) if self.rec.sdd else None

    def _record_sdd_sync(self, result: dict[str, Any]) -> None:
        with self.lock:
            if self.rec.sdd is not None:
                self.rec.sdd["sync"] = result
                self.persist()

    def _sdd_exit(self, decision: str, reason: str) -> dict[str, Any]:
        """對 FSM 做一次 `delegate-exit`，回傳要記進 `RunRecord.sdd.sync` 的結果；**永不丟例外**
        （終態同步失敗只記 alert，不改 run 狀態、不重試；監督執行緒的例外會把已終態的 run 誤標成崩
        潰）。rc 3（FSM 已不在 AUTOCLAUDE_DELEGATED，例如人工已處理）＝視為「已就位」，記
        `SDD_SYNC_STATE_DRIFT` 警告，不算失敗。"""
        ctx = self._sdd_context()
        result: dict[str, Any] = {"exit": decision, "ok": True, "at": _now()}
        if ctx is None:
            return result
        try:
            sdd_run.exit_delegation(ctx, self.rec.run_id, decision=decision, reason=reason,
                                    sdd_root=self.mgr.settings.sdd_root, audit=self.mgr.audit)
        except ApiError as exc:
            if exc.status_code == 409 and exc.body.get("reason") == "fsm_state_conflict":
                result["drift"] = True
                self.alert("warning", "SDD_SYNC_STATE_DRIFT",
                           f"終態同步時 FSM 已不在 AUTOCLAUDE_DELEGATED（現況 "
                           f"{exc.body.get('current_state')}），視為已就位，未再動 FSM")
            else:
                result.update(ok=False, error=str(exc.body.get("reason")))
                self.alert("error", "SDD_FSM_SYNC_FAILED",
                           f"終態同步（delegate-exit {decision}）失敗：{exc.body.get('reason')}；"
                           "FSM 留在原態，由下一個批次的回收點或人工處理")
        except Exception as exc:                                  # noqa: BLE001
            logger.exception("SDD 終態同步發生未預期的錯誤（run=%s）", self.rec.run_id)
            result.update(ok=False, error=type(exc).__name__)
            self.alert("error", "SDD_FSM_SYNC_FAILED",
                       f"終態同步（delegate-exit {decision}）發生未預期的錯誤："
                       f"{type(exc).__name__}")
        return result

    def _sdd_sync_terminal(self, *, orphan: bool = False) -> None:
        """終態對映（§10.1，純函式 `sdd_sync.terminal_decision`）：完成與使用者取消＝`done`（交還
        控制權，不是「成功」）、引擎升級型失敗＝`failed`；其餘（額度停機、異常、被訊號終止、spawn
        失敗、Bridge 關閉、孤兒、暫停）不動 FSM，留給下一個批次的回收點。"""
        try:
            rec = self.rec
            if not rec.sdd:
                return
            decision = terminal_decision(
                rec.status, escalation=self._escalation, stop_requested=self.stop_requested,
                shutting_down=self.shutting_down, orphan=orphan)
            if decision is None:
                return
            if decision == "failed":
                reason = reason_exit_failed(rec.run_id, self._escalation_step, self._escalation)
            elif rec.status == RunStatus.CANCELLED.value:
                reason = reason_exit_cancelled(rec.run_id)
            else:
                reason = reason_exit_completed(rec.run_id)
            self._record_sdd_sync(self._sdd_exit(decision, reason))
        except Exception:                                         # noqa: BLE001
            logger.exception("SDD 終態同步失敗（run=%s）", self.rec.run_id)

    def sdd_compensate_spawn_failure(self) -> None:
        """spawn 失敗的補償：`delegate-enter` 已做、委派從未開始，以 `done` 離開（回
        IMPLEMENTATION＝「沒有進行中的委派」）。🔴 不得用 `failed`——那會進阻塞態 ESCALATION，不可
        把基礎設施故障映成它。
        補償本身失敗只記 ERROR 與 alert，不改變對呼叫端的錯誤回應。"""
        try:
            self._record_sdd_sync(self._sdd_exit("done", reason_exit_spawn_failed(self.rec.run_id)))
        except Exception:                                         # noqa: BLE001
            logger.exception("SDD 補償失敗（run=%s）", self.rec.run_id)

    def _sdd_continue(self) -> bool:
        """`resume`／`restore` 的 SDD 重驗與 FSM 前置（§10.1 末列）：重跑 `load_spec`（凍結＝現檔）
        並比對匯入時的任務摘要（不符＝409 `spec_digest_changed`）；FSM 為 AUTOCLAUDE_DELEGATED 且
        `playbook_ref` 就是本 run⇒直接續；為 IMPLEMENTATION⇒`delegate-enter` 重進；引用別的 run⇒
        走回收點判定；其餘（含 ESCALATION）⇒409 並**不 spawn**。回傳這次呼叫是否做了
        `delegate-enter`（之後失敗要補償）。"""
        ctx = self._sdd_context()
        if ctx is None:
            return False
        sdd_run.revalidate(ctx, self.paths.playbook)
        outcome = sdd_run.execute_delegation(
            ctx, self.rec.run_id, mode="continue", sdd_root=self.mgr.settings.sdd_root,
            audit=self.mgr.audit, lookup=self.mgr.sdd_facts)
        return bool(outcome["entered"])

    def _finish_pause(self, common: dict[str, Any]) -> None:
        self.tracker.fail_current()          # 邊界之後才開始的步驟是被中止的 spawn：靜默丟棄
        self.rec.current_step = None
        self.rec.current_step_number = None
        self.rec.attempt = 0
        latest = self.history.latest()
        try:
            if latest is None:
                raise OSError("沒有可用的歷史快照")
            write_engine_checkpoint(self.paths.checkpoints, self.paths.playbook, latest["state"])
        except Exception as exc:                                  # noqa: BLE001
            self.rec.completed_at = _now()
            self.set_status(RunStatus.FAILED, f"暫停時無法寫入引擎 checkpoint：{exc}",
                            exit_code=None, **common)
            self.mgr.release_lock(self)
            return
        state = latest["state"]
        nxt = state["step_id"] or "（已無下一步）"
        done = len(state["completed_step_ids"])
        self.set_status(RunStatus.PAUSED, f"在步驟邊界暫停（已完成 {done} 步，續跑點：{nxt}）",
                        exit_code=None, **common)

    def _finish_normally(self, returncode: int | None, common: dict[str, Any]) -> None:
        rec = self.rec
        rec.completed_at = _now()
        if returncode == 0:
            self._complete_current_step()
            self._reconcile_step_gap()
            self.set_status(RunStatus.COMPLETED, "引擎正常結束", exit_code=0, **common)
        else:
            failed = self.tracker.fail_current()
            reason = self._failure_reason(returncode)
            if failed is not None:
                self._emit_step(failed[0], "FAILED", failed[1], error=reason)
            self.set_status(RunStatus.FAILED, reason, exit_code=returncode, **common)
        self.mgr.release_lock(self)

    def _reconcile_step_gap(self) -> None:
        """引擎說整份跑完了、但步驟事件不完整（啟動行格式變了／解析不到）⇒ 計數以引擎為準並大聲說，
        不讓 GET 顯示 COMPLETED 卻 completed_steps=0。"""
        if len(self.tracker.completed) >= len(self.steps):
            return
        missing = [s.step_id for s in self.steps if s.step_id not in self.tracker.completed]
        self.alert("warning", "STEP_TRACKING_GAP",
                   f"引擎已正常結束，但 Bridge 沒有觀察到這些步驟的完成訊號：{missing}；"
                   "計數以引擎結果為準（可能是引擎日誌格式改了，見 app/logparse.py）")
        self.tracker.completed.extend(missing)
        self.rec.completed_step_ids = list(self.tracker.completed)
        self.persist()

    def _failure_reason(self, returncode: int | None) -> str:
        end = self._end
        if self._escalation:
            return f"引擎升級（ESCALATION）：{self._escalation}"[:500]
        if end is not None and end.halted:
            return "引擎因 token／額度門檻停機（halted），未自動續跑"
        if self._last_error:
            return f"引擎異常結束（exit={returncode}）：{self._last_error}"[:500]
        if returncode is not None and returncode < 0:
            return f"引擎被訊號 {-returncode} 終止（exit={returncode}）"
        return f"引擎異常結束（exit={returncode}）"

    def _abort_after_supervisor_crash(self, proc: subprocess.Popen[bytes], exc: Exception) -> None:
        victims = procutil.begin_terminate(proc.pid)
        try:
            proc.wait(timeout=self.mgr.settings.stop_grace_seconds)
        except subprocess.TimeoutExpired:
            procutil.force_kill(victims)
        with self.lock:
            self.proc = None
            self.rec.completed_at = _now()
            self.set_status(RunStatus.FAILED, f"Bridge 監督執行緒錯誤：{type(exc).__name__}: {exc}",
                            pid=None, exit_code=proc.returncode)
            self.mgr.release_lock(self)

    # ── 對外操作 ─────────────────────────────────────────────────────────────
    def pause(self) -> str:
        with self.lock:
            status = self.rec.status
            if status == RunStatus.PAUSING:
                return RunStatus.PAUSING.value
            if status != RunStatus.RUNNING:
                raise invalid_state(self.rec.run_id, status, "pause")
            self.pause_requested = True
            self.set_status(RunStatus.PAUSING, "已要求暫停：下一個步驟邊界生效")
            return RunStatus.PAUSING.value

    def stop(self) -> str:
        with self.lock:
            status = self.rec.status
            if status == RunStatus.CANCELLING:
                return RunStatus.CANCELLING.value
            if status in (RunStatus.RUNNING, RunStatus.PAUSING):
                self.stop_requested = True
                self.set_status(RunStatus.CANCELLING, "已要求取消：終止引擎行程樹")
                return RunStatus.CANCELLING.value
            if status != RunStatus.PAUSED:
                raise invalid_state(self.rec.run_id, status, "stop")
            # PAUSED：沒有行程可終止，直接收尾
            self.set_status(RunStatus.CANCELLING, "已要求取消（暫停中，無行程）")
            self.rec.completed_at = _now()
            self.set_status(RunStatus.CANCELLED, "使用者取消", completed_at=self.rec.completed_at)
            self.mgr.release_lock(self)
            self.store.close()
        # 暫停中取消也是終態：委派交還控制權（`done`）。在 handle.lock 之外呼叫（CLI 最壞 20 秒）。
        self._sdd_sync_terminal()
        return RunStatus.CANCELLING.value

    def _recheck_path(self) -> None:
        """續跑前重驗 execution_path：暫停期間目錄可能被換成指向白名單外的 symlink（TOCTOU）。"""
        _, violations = security.check_path(
            self.rec.execution_path, self.mgr.settings.allowed_path_roots, field="execution_path")
        if violations:
            raise unprocessable(violations)

    def resume(self, env: dict[str, str] | None = None) -> str:
        with self.lock:
            if self.rec.status != RunStatus.PAUSED:
                raise invalid_state(self.rec.run_id, self.rec.status, "resume")
            self._recheck_path()
            # SDD 批次：重驗（凍結＝現檔＝匯入）與 FSM 前置；不合就 409／422 並**不 spawn**（run
            # 仍是 PAUSED）。
            entered = self._sdd_continue()
            try:
                self._adopt_env(env)
                checkpoint = load_engine_checkpoint(self.paths.checkpoints, self.paths.playbook)
                if checkpoint is None:                   # 引擎 checkpoint 被刪：用最新歷史快照補寫
                    latest = self.history.latest()
                    if latest is None:
                        raise ApiError(409, "no_checkpoint", detail="找不到可續跑的 checkpoint")
                    write_engine_checkpoint(self.paths.checkpoints, self.paths.playbook,
                                            latest["state"])
                    checkpoint = load_engine_checkpoint(self.paths.checkpoints,
                                                        self.paths.playbook)
                self._rewind_to(list(checkpoint.completed_step_ids),
                                list(checkpoint.completed_step_log))
                self._spawn(fresh=False)
            except BaseException:
                if entered:                              # 這次呼叫剛 enter 的委派：失敗就補償退出
                    self.sdd_compensate_spawn_failure()
                raise
            return RunStatus.RUNNING.value

    def restore(self, checkpoint_id: str, env: dict[str, str] | None = None) -> None:
        with self.lock:
            status = self.rec.status
            if status not in (RunStatus.PAUSED, *TERMINAL_STATUSES):
                raise invalid_state(self.rec.run_id, status, "restore")
            snap = self.history.get(checkpoint_id)
            if snap is None:
                raise not_found("checkpoint_not_found", checkpoint_id=checkpoint_id)
            self._recheck_path()
            self.mgr.reacquire_lock(self)                # PAUSED 持鎖＝略過；終態重取：可能 409
            entered = False
            try:
                # SDD 批次：重驗與 FSM 前置放在第一步（還沒動任何東西），不合就 409／422 並不
                # spawn。
                entered = self._sdd_continue()
                self._adopt_env(env)
                state = snap["state"]
                write_engine_checkpoint(self.paths.checkpoints, self.paths.playbook, state)
                self._rewind_to(list(state["completed_step_ids"]),
                                list(state["completed_step_log"]))
                self.rec.completed_at = None
                self.rec.exit_code = None
                self.mgr.mirror(self.rec.run_id, completed_at=None)
                self.alert("info", "RESTORE", f"從 checkpoint「{snap['name']}」（step_idx="
                           f"{snap['step_idx']}）還原並續跑", checkpoint_id=checkpoint_id)
            except BaseException:
                # 重取之後、spawn 之前失敗：終態 run 的鎖是剛重取的、run 仍是終態 ⇒ 放掉再丟，
                # 否則終態 run 會一直持著它（同 project＋path 的新 run 全 409，直到 Bridge 重啟）。
                # PAUSED run 的鎖本來就是它的、沒有重取：不動。spawn 本身的失敗由 _spawn 自己收尾。
                if entered:                              # 這次剛 enter 的委派：失敗就補償退出
                    self.sdd_compensate_spawn_failure()
                if status in TERMINAL_STATUSES:
                    self.mgr.release_lock(self)
                raise
            try:
                self._spawn(fresh=False)
            except BaseException:
                if entered:
                    self.sdd_compensate_spawn_failure()
                raise

    def _adopt_env(self, env: dict[str, str] | None) -> None:
        if env:
            self.request_env = dict(env)
        elif not self.request_env and self.rec.env_keys:
            # Bridge 重啟後請求層 env（可能含機密）已遺失——機密從不落盤。大聲說，別靜默降級。
            self.alert("warning", "ENV_LOST",
                       "此 run 建立時帶有請求層 env（" + ", ".join(self.rec.env_keys)
                       + "），Bridge 重啟後已遺失；僅使用 Bridge 行程環境續跑。需要的話在 "
                       "resume／restore 的 body 重新提供 env。")

    def _rewind_to(self, completed_ids: list[str], completed_log: list[str]) -> None:
        self.tracker = StepTracker(self.steps, completed_ids)
        self.completed_log = completed_log
        self.rec.completed_step_ids = list(completed_ids)
        self.rec.current_step = None
        self.rec.current_step_number = None
        self.rec.attempt = 0
        self.pause_requested = False
        self.stop_requested = False

    def terminate_for_shutdown(self) -> None:
        with self.lock:
            if self.proc is None:
                return
            self.shutting_down = True
            self.stop_requested = True
        thread = self.supervisor
        if thread is not None:
            thread.join(timeout=self.mgr.settings.stop_grace_seconds + _KILL_GIVE_UP_SECONDS + 5)


class RunManager:
    def __init__(self, settings: Settings, *, locks: AdvisoryLock, audit: security.AuditLog,
                 db: BridgeDb | None = None):
        self.settings = settings
        self.locks = locks
        self.audit = audit
        self.db = db
        self._runs: dict[str, RunHandle] = {}
        self._stores: dict[str, EventStore] = {}
        self._creating: set[str] = set()
        self._mutex = threading.RLock()
        # 資源取樣器（D-12）：這裡只建物件、不開執行緒；執行緒由 create_app 的 lifespan 啟動。
        self.sampler = ResourceSampler(self.engine_pids)

    def engine_pids(self) -> dict[str, int]:
        """{run_id: 引擎根 pid}，只含引擎行程樹存活的 run（取樣器每一輪來問一次）。"""
        with self._mutex:
            handles = list(self._runs.values())
        pids = ((h.rec.run_id, h.live_engine_pid()) for h in handles)
        return {run_id: pid for run_id, pid in pids if pid is not None}

    # ── 取得 ─────────────────────────────────────────────────────────────────
    def get(self, run_id: str) -> RunHandle | None:
        try:
            run_id = str(uuid.UUID(run_id))        # 大寫／無連字號的 UUID 寫法也要找得到
        except ValueError:
            pass
        with self._mutex:
            return self._runs.get(run_id)

    def require(self, run_id: str) -> RunHandle:
        handle = self.get(run_id)
        if handle is None:
            raise not_found("run_not_found", run_id=run_id)
        return handle

    def store_for_handle(self, handle: RunHandle) -> EventStore:
        with self._mutex:
            store = self._stores.get(handle.rec.run_id)
            if store is None:
                store = EventStore(handle.paths.events)
                self._stores[handle.rec.run_id] = store
            return store

    # ── DB 鏡射（沒設 DSN 時全是 no-op）───────────────────────────────────────
    def mirror(self, run_id: str, **fields: Any) -> None:
        if self.db is not None and fields:
            self.db.update_run(run_id, **fields)

    def mirror_step(self, *, run_id: str, task_id: str | None, seq: int, action: str, status: str,
                    input_data: dict[str, Any], error: str | None) -> None:
        if self.db is not None:
            self.db.insert_step(run_id=run_id, task_id=task_id, step_number=seq, action=action,
                                status=status, input_data=input_data, error_message=error)

    def mirror_checkpoint(self, run_id: str, meta: dict[str, Any], state: dict[str, Any]) -> None:
        if self.db is not None:
            self.db.insert_checkpoint(
                run_id=run_id, checkpoint_id=meta["checkpoint_id"], name=meta["name"],
                state_snapshot=state, created_at=datetime.fromisoformat(meta["created_at"]),
                is_automatic=meta["is_automatic"])

    # ── 鎖 ───────────────────────────────────────────────────────────────────
    def release_lock(self, handle: RunHandle) -> None:
        if handle.rec.lock_key:
            self.locks.release(handle.rec.lock_key, handle.rec.run_id)

    def reacquire_lock(self, handle: RunHandle) -> None:
        """restore 前確保 run 持著鎖。已持鎖（PAUSED 期間本來就持著，resume 也不重搶）⇒ 直接略過，
        不開新連線、不動登記（新連線只會撞上自己的舊連線而 409，失敗路徑還會讓舊連線洩漏，AR-01）；
        沒持鎖（終態已放）才真的重取，可能 409；重取後 restore 若在 spawn 前失敗，
        由 restore 放掉。"""
        if handle.rec.lock_key and self.locks.holder(handle.rec.lock_key) == handle.rec.run_id:
            return
        try:
            info = self.locks.acquire(handle.rec.project, handle.rec.execution_path,
                                      handle.rec.run_id)
        except LockBusy as busy:
            raise lock_held(busy.holder_run_id) from busy
        except LockUnavailable as exc:
            raise ApiError(503, "lock_backend_unavailable", detail=str(exc)) from exc
        handle.rec.lock_key, handle.rec.db_lock_key = info.key, info.db_key

    # ── 建立 ─────────────────────────────────────────────────────────────────
    def create(self, req: RunCreateIn) -> RunHandle:
        run_id = str(req.run_id)
        with self._mutex:                       # 原子保留：同一個 run_id 的併發建立只有一個會過
            if (run_id in self._runs or run_id in self._creating
                    or (self.settings.engine_workspace / run_id).exists()):
                raise ApiError(409, "run_exists", run_id=run_id)
            self._creating.add(run_id)
        try:
            return self._create(req, run_id)
        finally:
            with self._mutex:
                self._creating.discard(run_id)

    def _create(self, req: RunCreateIn, run_id: str) -> RunHandle:
        exec_path = self._validate(req, run_id)
        # 1 SDD 唯讀預檢（路徑閘→規格與凍結→三點摘要→FSM 狀態）：4xx、零副作用，先於取鎖
        plan = self._sdd_precheck(req, run_id, exec_path) if req.sdd is not None else None
        try:
            info = self.locks.acquire(req.project, str(exec_path), run_id)
        except LockBusy as busy:
            raise lock_held(busy.holder_run_id) from busy
        except LockUnavailable as exc:
            raise ApiError(503, "lock_backend_unavailable", detail=str(exc)) from exc
        entered = False
        try:
            if plan is not None:
                # 3 FSM 寫入（依預檢表）：在 _materialize 之前，失敗時才不會留下半成品 run 目錄
                # （否則 reconcile 下次啟動會把它當「活躍而無行程」的孤兒標成 FAILED，憑空多一筆假
                # 紀錄）
                outcome = sdd_run.execute_delegation(
                    plan.ctx, run_id, mode="create", sdd_root=self.settings.sdd_root,
                    audit=self.audit, lookup=self.sdd_facts, spec_rel=plan.spec_rel,
                    digest=plan.spec.digest)
                entered = bool(outcome["entered"])
            handle = self._materialize(req, run_id, exec_path, info, plan)
        except BaseException:
            # 4 _materialize 失敗：補償 delegate-exit done
            if entered and plan is not None:
                self._sdd_compensate_without_handle(plan.ctx, run_id)
            self.locks.release(info.key, run_id)
            raise
        with self._mutex:
            self._runs[run_id] = handle
        if plan is not None:
            handle.create_warnings = list(plan.warnings)
        try:
            handle.start(fresh=req.fresh,
                         ignored_overrides=security.ignored_managed_keys(req.config_overrides))
        except ApiError as exc:
            if entered and exc.body.get("reason") == "spawn_failed":
                handle.sdd_compensate_spawn_failure()    # 5 spawn 失敗：補償（handle.lock 之外）
            raise
        return handle

    def _sdd_precheck(self, req: RunCreateIn, run_id: str, exec_path: Path) -> sdd_run.SddPrecheck:
        """§10.2 步驟 1 的 SDD 部分（權杖已在路由檢查）：全部唯讀，任何一關不過就 4xx、不取鎖、不
        寫 FSM、不 spawn。FSM 狀態在這裡只判不寫（寫入前會在 `state_guard` 內重讀重判，防
        TOCTOU）。"""
        assert req.sdd is not None
        ctx = sdd_run.build_context(self.settings, req.sdd, exec_path)
        check = sdd_run.precheck_spec(ctx, req.playbook)
        state = sdd_run.read_snapshot(ctx)                    # 沒有狀態檔＝404（Bridge 不 init）
        sdd_run.plan_delegation(state, ctx=ctx, run_id=run_id, mode="create", lookup=self.sdd_facts)
        return check

    def sdd_facts(self, run_id: str) -> RunFacts | None:
        """回收點判定（§10.3）要的事實：Bridge 登錄裡（含重啟後由 `run.json` 還原的）該 run 的狀態與
        所屬 FSM 專案；查無此 run＝None。"""
        handle = self.get(run_id)
        if handle is None:
            return None
        rec = handle.rec
        sdd = rec.sdd or {}
        state_dir = sdd.get("state_dir")
        return RunFacts(status=rec.status,
                        state_dir=os.path.normcase(state_dir) if state_dir else None,
                        fsm_project=sdd.get("fsm_project"))

    def _sdd_compensate_without_handle(self, ctx: sdd_run.SddContext, run_id: str) -> None:
        """`_materialize` 失敗時（還沒有 handle）的補償：`delegate-enter` 已做、run 從未建立，以
        `done`退出。失敗只記 ERROR 與稽核，不改變對呼叫端的錯誤回應。"""
        try:
            sdd_run.exit_delegation(ctx, run_id, decision="done",
                                    reason=reason_exit_spawn_failed(run_id),
                                    sdd_root=self.settings.sdd_root, audit=self.audit)
        except Exception as exc:                              # noqa: BLE001
            logger.error("SDD 補償失敗（run=%s）：%s", run_id, exc)
            self.audit.record("sdd_write", verb="compensate", project=ctx.fsm_project,
                              result=f"error:{type(exc).__name__}", run_id=run_id)

    def _validate(self, req: RunCreateIn, run_id: str) -> Path:
        allow = self.settings.outbound_allowlist
        ctx = {"run_id": run_id}
        exec_path, violations = security.check_path(
            req.execution_path, self.settings.allowed_path_roots, field="execution_path")
        violations += security.validate_playbook(req.playbook)
        violations += security.validate_env(req.env, allow, audit=self.audit, context=ctx)
        violations += security.validate_config_overrides(
            req.config_overrides, allow, audit=self.audit, context=ctx)
        violations += self._effective_minimax_violations(req, allow, ctx)
        if violations or exec_path is None:
            raise unprocessable(violations)
        return exec_path

    def _effective_minimax_violations(self, req: RunCreateIn, allow: tuple[str, ...],
                                      ctx: dict[str, Any]) -> list[dict[str, Any]]:
        """引擎的優先序是 env MINIMAX_BASE_URL > config；真的會呼叫 Brain（有金鑰）時，
        **實際生效**的 URL 也要過白名單——包含「完全沒設、走預設」的情況。"""
        from autoclaude.utils.config import AppConfig

        def pick(name: str) -> str:
            return req.env.get(name) or os.environ.get(name, "")

        enabled = bool((req.config_overrides.get("minimax") or {}).get("enable_kernel_brain"))
        if not (pick("MINIMAX_API_KEY") or enabled):
            return []
        override = (req.config_overrides.get("minimax") or {}).get("base_url", "")
        effective = pick("MINIMAX_BASE_URL") or override or AppConfig().minimax.base_url
        if req.env.get("MINIMAX_BASE_URL") or override:
            return []                   # 已由 validate_env／validate_config_overrides 驗過
        return security._check_url_field(effective, "effective.minimax.base_url", allow,
                                         self.audit, ctx)

    def _materialize(self, req: RunCreateIn, run_id: str, exec_path: Path, info: Any,
                     plan: sdd_run.SddPrecheck | None = None) -> RunHandle:
        paths = RunPaths(self.settings.engine_workspace / run_id)
        paths.run_dir.mkdir(parents=True, exist_ok=False)
        for sub in (paths.checkpoints, paths.logs, paths.backups, paths.scripts):
            sub.mkdir(parents=True, exist_ok=True)
        # 含 `sdd` 區塊：伺服端把 workflow_type 覆寫成 aisdlc_sdd、workflow_path 設成已驗證的
        # realpath（外部契約不開 workflow_*；D-115-06）。沒有 `sdd` 的請求行為與 v1.4 完全相同。
        workflow_path = str(plan.ctx.workflow_path) if plan is not None else None
        paths.playbook.write_text(
            _yaml_dump(req.playbook.to_engine_dict(sdd_workflow_path=workflow_path)),
            encoding="utf-8", newline="\n")
        paths.config.write_text(_yaml_dump(materialize_config(req.config_overrides, paths)),
                                encoding="utf-8", newline="\n")
        steps = [StepDef(t.step_id, t.name, t.prompt, t.goal_task_id) for t in req.playbook.tasks]
        rec = RunRecord(
            run_id=run_id, project=req.project, execution_path=str(exec_path),
            bridge_instance=self.settings.bridge_instance, created_at=_now(),
            total_steps=len(steps), lock_key=info.key, db_lock_key=info.db_key,
            steps=[{"step_id": s.step_id, "name": s.name, "goal_task_id": s.goal_task_id}
                   for s in steps],
            env_keys=sorted(req.env),
            sdd=plan.ctx.record() if plan is not None else None)
        handle = RunHandle(self, rec, paths, steps, request_env=req.env)
        handle.persist()
        return handle

    # ── 啟動時的 reconciliation（PRD §0.2.2）─────────────────────────────────
    def reconcile(self) -> list[str]:
        """掃工作區：RUNNING 但沒有存活 PID 的 run 標 FAILED(orphaned) 並釋放鎖；
        PAUSED 的 run 重新登記鎖；仍存活（身分比對相符）的引擎行程無法再被監督 ⇒ 終止後同樣標記。"""
        workspace = self.settings.engine_workspace
        workspace.mkdir(parents=True, exist_ok=True)
        orphaned: list[str] = []
        for run_json in sorted(workspace.glob("*/run.json")):
            rec = load_record(run_json)
            if rec is None:
                logger.warning("略過無法讀取的 run.json：%s", run_json)
                continue
            paths = RunPaths(run_json.parent)
            handle = RunHandle(self, rec, paths, _load_steps(paths, rec))
            with self._mutex:
                self._runs[rec.run_id] = handle
            if rec.status in _ACTIVE_STATUSES:
                self._reap_orphan(handle)
                orphaned.append(rec.run_id)
            elif rec.status == RunStatus.PAUSED and rec.lock_key:
                self._reclaim_paused_lock(handle)
        return orphaned

    def _reap_orphan(self, handle: RunHandle) -> None:
        rec = handle.rec
        was_cancelling = rec.status == RunStatus.CANCELLING
        alive = procutil.pid_alive(rec.pid, rec.pid_create_time)
        detail = "Bridge 重啟時子程序已不存在"
        if alive and rec.pid is not None:
            victims = procutil.begin_terminate(rec.pid)
            deadline = time.monotonic() + self.settings.stop_grace_seconds
            while procutil.survivors(victims) and time.monotonic() < deadline:
                time.sleep(_POLL_SECONDS)
            procutil.force_kill(procutil.survivors(victims))
            detail = "Bridge 重啟時子程序仍存活、無法再監督，已終止"
        with handle.lock:
            rec.completed_at = _now()
            if was_cancelling:
                handle.set_status(RunStatus.CANCELLED, f"取消中遇到 Bridge 重啟：{detail}",
                                  pid=None, pid_create_time=None)
            else:
                handle.set_status(RunStatus.FAILED, f"orphaned：{detail}",
                                  pid=None, pid_create_time=None)
            self.mirror(rec.run_id, subprocess_pid=None)
            self.release_lock(handle)
            handle.store.close()
        self.audit.record("run_orphaned", run_id=rec.run_id, pid=rec.last_pid, killed=alive)

    def _reclaim_paused_lock(self, handle: RunHandle) -> None:
        rec = handle.rec
        try:
            info = self.locks.acquire(rec.project, rec.execution_path, rec.run_id)
            rec.lock_key, rec.db_lock_key = info.key, info.db_key
        except (LockBusy, LockUnavailable) as exc:
            logger.warning("PAUSED run %s 重新登記鎖失敗：%s", rec.run_id, exc)

    # ── 關閉 ─────────────────────────────────────────────────────────────────
    def shutdown(self) -> None:
        self.sampler.stop()
        with self._mutex:
            handles = list(self._runs.values())
        for handle in handles:
            handle.terminate_for_shutdown()
        with self._mutex:
            stores = list(self._stores.values())
        for store in stores:
            store.close()
        self.locks.close()
