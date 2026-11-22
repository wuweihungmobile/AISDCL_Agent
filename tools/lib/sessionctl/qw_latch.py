"""QuotaWall 主載具憑證與「缺 park」閂鎖（R218 Q1；DES S-18、REQ-QW-43）。

主載具憑證＝payload `background_tasks` 有 running 的 keepwarm／watch shell ∧ 本 sid holder 列活著、
帶未來 `wake_at`、模式屬 chain／single（帶目標；`periodic` 只保溫不續工，維持排除）。成立時它是
「會叫醒主控做事」的事件源：半路停工不判，「缺 park」推回對同一 (sid, 短窗視窗) 至多一次。

閂鎖檔 `trace_dir()/quotawall/<sid>.json`＝`{reset, pct, at, grace_task_ids}`（epoch 秒）。
視窗身分＝`same_window`（不以 reset 精確值當鍵：觀測值本身漂移 ±5 分、+70 分都不算換窗）。
讀失敗 ⇒ 視為未推（寧可多推一次，不漏推）；寫失敗 ⇒ 不記（同樣每次都推）。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import endurance_env

from . import holder, qw_calc, qw_schema, roster

LATCH_DIR = "quotawall"


def latch_path(sid: str, *, write: bool = False) -> Path:
    root = endurance_env.trace_dir() if write else endurance_env.trace_dir_peek()[0]
    return root / LATCH_DIR / f"{sid}.json"


def _read(sid: str) -> dict | None:
    try:
        row = json.loads(latch_path(sid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return row if isinstance(row, dict) else None


def _write(sid: str, row: dict) -> bool:
    try:
        path = latch_path(sid, write=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(row, ensure_ascii=False), encoding="utf-8", newline="\n")
    except OSError:
        return False
    return True


def same_window(latched, reset_now, pct_now, now: float, reading_at: float | None = None) -> bool:
    """S-18：閂鎖時的短窗視窗與現在是不是同一個（`False`＝已翻新）。已翻新 ⇔ 讀數已降
    （同窗伺服器讀數單調不減，降＝換窗）∨ `now ≥ latched.reset＋LATCH_RESET_TOL_MIN`（60 分）。
    讀數量不到（`pct_now` 為 None）時只用後一條。S-23⑥：`reading_at` 早於閂鎖時刻的讀數不參與
    「讀數已降」那一條（陳舊低讀數不得誤判換窗）。`reset_now` 是保留位——**不得**拿它與閂鎖 reset
    比精確值（MU-QW-40）；呼叫端仍傳入以便日後診斷。"""
    if not isinstance(latched, dict):
        return False
    l_reset, l_pct, l_at = latched.get("reset"), latched.get("pct"), latched.get("at")
    if type(l_reset) in (int, float) and now >= l_reset + qw_calc.LATCH_RESET_TOL_MIN * 60:
        return False
    if (pct_now is not None and type(l_pct) in (int, float) and pct_now < l_pct
            and (reading_at is None or type(l_at) not in (int, float) or reading_at >= l_at)):
        return False
    return True


def latch_seen(sid: str, reset, pct, now: float, reading_at: float | None = None) -> bool:
    """本 (sid, 短窗視窗) 是否已推過「缺 park」；讀不到閂鎖 ⇒ False（視為未推）。"""
    return same_window(_read(sid), reset, pct, now, reading_at)


def latch_mark(sid: str, reset: float | None, pct: float | None, now: float) -> bool:
    """記下「已推」；保留 `grace_task_ids`。寫失敗 ⇒ False（之後每次都會再推，不漏推）。"""
    old = _read(sid) or {}
    return _write(sid, {"reset": reset, "pct": pct, "at": now,
                        "grace_task_ids": list(old.get("grace_task_ids") or [])})


def latch_grace(sid: str, task_id) -> bool:
    """競態寬限（QA3 P3-7）：holder 缺席但有 running 的本 sid keepwarm shell ⇒ 同一背景任務 id
    只寬限一次 Stop。首次 ⇒ True 並記入；已寬限過或寫不進 ⇒ False
    （防 holder 永久寫不進而長期壓住推回）。"""
    row = _read(sid) or {}
    ids = [str(x) for x in row.get("grace_task_ids") or []]
    if str(task_id) in ids:
        return False
    row["grace_task_ids"] = [*ids, str(task_id)]
    return _write(sid, row)


def running_supervision(payload: dict) -> list[dict]:
    """payload 內 running 的 keepwarm／watch shell（`roster.is_supervision_shell` 同一判準）。"""
    tasks = roster._tasks(payload) if isinstance(payload, dict) else None
    return [t for t in tasks or [] if roster.is_supervision_shell(t)
            and str(t.get("status") or "running") == "running"]


def primary_live(payload: dict, sid: str, now: datetime, *, row=None,
                 alive=holder.pid_alive, token=holder.start_token) -> bool:
    """S-18 主載具憑證（見檔頭）；任何例外 ⇒ False（維持舊行為＝排除）。"""
    try:
        if not running_supervision(payload):
            return False
        row = holder.read(sid) if row is None else row
        if not holder.is_live(row, alive=alive, token=token):
            return False
        wake = qw_schema.holder_wake(row)
        return (wake is not None and wake.wake_at is not None
                and wake.wake_at > now.timestamp() and wake.mode in ("chain", "single"))
    except Exception:  # noqa: BLE001
        return False
