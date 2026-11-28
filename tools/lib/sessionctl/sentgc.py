"""舊哨兵殘骸 GC（WP-SW D-SW-10／REQ-CTL-58；DES §24.5）。

立案（暴露證據）：`AutoSDD_Sentinel_406454ea-…` 殘骸（`NextRunTime` 空、`LastTaskResult=1`）無人 GC，
`sessionctl status` 一直顯示「過期哨兵」。誰、何時拆：`handoff --ack` 成功後（`ackhook.after_handoff`）——ack 是
「新 session 已接手、舊 session 的舊物該退場」的唯一機器可驗事件；`status` 維持唯讀（診斷動詞不得變成副作用站點）。

候選＝同時滿足：①`NextRunTime` 為空（排程器自報「不會再響」）②sid ≠ acker ③`LastTaskResult∉{0,267009,267011}`
或任務書 `state∈{abandoned,disarmed,superseded}` ④不在執行中：排程器自報 `State != Running` **且** `LastRunTime`
距今 ≥ `min_idle_s`（哨兵用 `-Once` 單次觸發、tick 進行中 `NextRunTime` 為空且結果 267009——沒有④會把**活著、正在跑的
別人哨兵**拆掉）；`State`／`LastRunTime` 任一讀不到 ⇒ 不拆。`NextRunTime` 非空者一律不動。每次 ack 至多
`SENTGC_MAX_PER_ACK`（5）個。移除只經既有站點 `schedule_backend.select().disarm`，本檔不含任何排程器原語。

**範圍化**（QA P2-5①）：`job_table` 在**列舉階段**依 `sandbox_scope.sandbox_home(repo_root)` 濾名稱——正式 checkout
⇒ 全部 `AutoSDD_Sentinel_*`；沙盒 repo ⇒ 只留以 `AutoSDD_Sentinel_<沙盒身分檔 sid>` 為前綴者。真實殘骸因此
結構上進不了候選與摘要，不靠清理時小心。`ackevents.summary` 與 `sweep` 共用同一次列舉。
"""  # noqa: E501
from __future__ import annotations

import re
import tempfile
from datetime import datetime
from pathlib import Path

from . import switch

PREFIX = "AutoSDD_Sentinel_"
SENTGC_MAX_PER_ACK = 5
#: 不當「已崩潰／已死」證據的 LastTaskResult：成功、執行中（267009）、尚未執行過（267011，Win32 SCHED_S_TASK_HAS_NOT_RUN）  # noqa: E501
_NOT_DEAD_RESULTS = (0, 267009, 267011)
_DEAD_PLAN_STATES = ("abandoned", "disarmed", "superseded")
_IDENT = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


def _sandbox_sid(repo_root) -> str | None:
    import sandbox_scope  # noqa: PLC0415

    home = sandbox_scope.sandbox_home(repo_root)
    if home is None:
        return None
    try:
        return str(sandbox_scope._read_identity(home).get("sid") or "")  # noqa: SLF001
    except Exception:  # noqa: BLE001 — 沙盒但身分檔讀不出：範圍空集合（寧可不看、不可放大到真實殘骸）
        return ""


def job_table(env=None, *, repo_root, backend=None) -> list[dict] | None:
    """範圍化排程列舉縫：回每筆 `{name, sid, state, last_run, last_result, next_run}`；`None`＝量不到。"""  # noqa: E501
    if backend is None:
        import schedule_backend  # noqa: PLC0415

        backend = schedule_backend.select()
    rows = getattr(backend, "job_states", lambda _p: None)(PREFIX)
    if rows is None:
        return None
    scope = _sandbox_sid(repo_root)
    out = []
    for row in rows:
        name = str(row.get("name") or "")
        if not name.startswith(PREFIX):
            continue
        if scope is not None and not (scope and name.startswith(PREFIX + scope)):
            continue  # 沙盒 repo：只看本沙盒名稱集合（真實殘骸在列舉階段就被濾掉）
        out.append({**row, "sid": name.removeprefix(PREFIX)})
    return out


def _plan_state(sid: str) -> str | None:
    """任務書狀態塊的 `state`（讀不到 ⇒ `None`）；任務書住系統暫存、檔名 `<PLAN_PREFIX><sid>.md`。"""  # noqa: E501
    try:
        import quota_escalation  # noqa: PLC0415

        import session_resume_planner as planner  # noqa: PLC0415

        path = Path(tempfile.gettempdir()) / f"{quota_escalation.guard.PLAN_PREFIX}{sid}.md"
        state = planner.parse_relay(path.read_text(encoding="utf-8"))
        return str((state or {}).get("state") or "") or None
    except Exception:  # noqa: BLE001
        return None


def _age_s(stamp, now: datetime) -> float | None:
    try:
        return (now - datetime.fromisoformat(str(stamp))).total_seconds() if stamp else None
    except ValueError:
        return None


def candidates(table: list[dict], acker_sid: str, *, min_idle_s: float, now: datetime,
               plan_state=None) -> list[dict]:
    plan_state = plan_state or _plan_state
    out = []
    for row in table:
        if row.get("next_run") != "" or row.get("sid") == acker_sid:
            continue  # ①NextRunTime 必須是排程器自報的「空」（None＝量不到、非空＝活著，一律不動）②
        dead = (row.get("last_result") not in _NOT_DEAD_RESULTS and row.get("last_result") is not None  # noqa: E501
                or plan_state(row["sid"]) in _DEAD_PLAN_STATES)
        age = _age_s(row.get("last_run"), now)
        idle = row.get("state") not in (None, "", "Running") and age is not None and age >= min_idle_s  # noqa: E501
        if dead and idle:
            out.append(row)
    return out


def sweep(acker_sid: str, env=None, *, repo_root, min_idle_s: float, table=..., backend=None,
          now: datetime | None = None, plan_state=None, say=None) -> list[str]:
    """拆除符合者（至多 5 個）；回已拆名稱。`table`＝已列舉的範圍化表（`...`＝自己列舉）；`None` ⇒ 零動作只出聲。
    不拋：任何失敗只出聲。"""  # noqa: E501
    say = say or (lambda text: print(text, file=__import__("sys").stderr))
    now = now or datetime.now().astimezone()
    try:
        if backend is None:
            import schedule_backend  # noqa: PLC0415

            backend = schedule_backend.select()
        if table is ...:
            table = job_table(env, repo_root=repo_root, backend=backend)
        if table is None:
            say("⚠️ 舊哨兵 GC：排程器狀態量不到（job_states 回 None）⇒ 本次不拆")
            return []
        if any(r.get("last_run") is None for r in table if r.get("next_run") == ""):
            say("ℹ️ 舊哨兵 GC：此平台量不到 LastRunTime ⇒ 讀不到不拆（誠實劃界，不假裝清了）")
        removed = []
        for row in candidates(table, acker_sid, min_idle_s=min_idle_s, now=now,
                              plan_state=plan_state)[:SENTGC_MAX_PER_ACK]:
            try:
                rc = backend.disarm(row["name"])  # 唯一移除站點（既有 `sentinel_lifecycle._remove_task` 同一條）  # noqa: E501
            except Exception as exc:  # noqa: BLE001 — 其餘殘骸照處理
                say(f"⚠️ 舊哨兵 GC：移除 {row['name']} 失敗（{type(exc).__name__}）")
                continue
            if rc != 0:
                say(f"⚠️ 舊哨兵 GC：移除 {row['name']} 回 rc={rc}")
                continue
            removed.append(row["name"])
            switch.trace("sentinel_gc", sid=row["sid"], task=row["name"], reason="next_run_empty_and_dead",  # noqa: E501
                         next_run="", last_result=row.get("last_result"), last_run=row.get("last_run"),  # noqa: E501
                         state=row.get("state"), acker=acker_sid)
        return removed
    except Exception as exc:  # noqa: BLE001
        say(f"⚠️ 舊哨兵 GC 失敗（不影響 ack）：{type(exc).__name__}")
        return []
