"""同專案「另一個 session 正在動」判準（WP-SW D-SW-4／REQ-CTL-52；DES §24.4；TH-A 升格）。

立案（暴露證據）：掌舵者真機回報「為何還有另一個視窗、問同樣的問題？……這也會導致混淆或多頭馬車！」
（交接包 `65389f03-…_20261121T095211Z.prompts.md` 第 13 行）；前置情境在真實逐字稿已發生 2 次
（4290bf58 開於 10:11:26、ack 10:13:43；814608d1 同形）。

判準：`project_dir` 直下 `*.jsonl`（子代理檔不算）中 `stem != own_sid` 者，對每個候選迴圈呼叫既有單一判準
`transcript_activity.driver_after`（回窗口內**最早一筆**非合成對話記錄，`kind`＝assistant／human／
auto-continuation；單次呼叫會被「人類提示 → assistant」交錯漏判，QA 複審 P2-N1）：`None` ⇒ 此 sid 沒人在動；
`assistant` ⇒ 命中；其餘 ⇒ 推進 `since` 再呼叫。**只認 AI 回合**：真人 `/login` 換帳號視窗只有人類／本機指令
記錄，不得誤判成「另一個 session 在動」。不看 mtime（harness 的 away_summary／cost-state 會讓它永遠新，
DEF-200-560）、不新寫詞表、不改 `transcript_activity`。fail 方向：目錄讀不動／逐字稿讀不到 ⇒ 沒人在動。

同戳平手（QA P3②）：`driver_after` 以 `stamp < best` 取最小、同戳先到者勝；human 與 assistant 恰同一戳時回 human，
推進 `since` 會跳過同戳的 assistant。故遇非 assistant 回傳時，另以同一把尺（`_driver_kind`）檢查「同戳是否有
assistant」，再推進；真實逐字稿 human 與 assistant 相差 ≥ 毫秒，此路只擋夾具與極端時鐘。
迴圈上限 `OTHER_SESSION_SCAN_MAX_STEPS` 用盡 ⇒ 該 sid 視為沒人在動並落 `park_other_session action=scan_cap`
（fail 方向不變）；痕跡落進持久目錄，`sessionctl status`／簡報以 `status_lines` 對「終局 skip」可見。
"""  # noqa: E501
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from . import qw_schema, switch

OTHER_SESSION_SCAN_MAX_STEPS = 200
OTHER_SESSION_MAX_DEFERS = 3  # 用盡 ⇒ 終局 skip（改 0 即直接終局）；只准不變或下修
DEFERS_KEY = "other_session_defers"  # 住標記，不與 park_yield.RESCHEDULES_KEY 共用
EV = "park_other_session"
SENTINEL_INTERVAL_SECONDS = 900  # 與 planner 同值（本葉不 import planner；AT-CTL-109 以 parity 鎖）


def _same_stamp_assistant(path: Path, stamp: float) -> dict | None:
    """同戳平手：`stamp` 這一刻是否另有 assistant 記錄（沿用 `_driver_kind` 這把尺）。"""
    import quota_limits  # noqa: PLC0415
    import transcript_activity as ta  # noqa: PLC0415

    for sub in quota_limits.session_transcripts(path):
        for rec in ta._records(sub, '"assistant"'):  # noqa: SLF001
            if ta._driver_kind(rec) == "assistant" and ta._epoch(rec.get("timestamp")) == stamp:  # noqa: SLF001
                return {"timestamp": str(rec["timestamp"]), "kind": "assistant"}
    return None


def _touched_since(path: Path, since: float) -> bool:
    """**只是效能預篩，不是判活來源**（判活仍只由 `driver_after` 的對話記錄決定）：檔案只會追加，
    `mtime < since` 的 session 不可能有 `since` 之後的記錄；專案目錄常有數百個舊逐字稿，逐一全檔掃描
    不可行。主檔與近期 subagent 檔取最大 mtime；讀不到 ⇒ 不預篩（偏向照掃）。"""
    import quota_limits  # noqa: PLC0415

    try:
        return max(p.stat().st_mtime for p in quota_limits.session_transcripts(path)) >= since
    except (OSError, ValueError):
        return True


def active(project_dir, own_sid: str, now: datetime, *, interval_s: int = SENTINEL_INTERVAL_SECONDS,
           driver_after=None, max_steps: int | None = None) -> dict | None:
    """回 `{"sid", "at"}`（另一個 session 在 `now−interval_s` 內有 AI 回合）或 `None`。"""
    import transcript_activity as ta  # noqa: PLC0415

    if project_dir is None:
        return None
    probe = driver_after or ta.driver_after
    cap = OTHER_SESSION_SCAN_MAX_STEPS if max_steps is None else max_steps
    try:
        candidates = sorted(p for p in Path(project_dir).glob("*.jsonl")
                            if p.is_file() and p.stem != own_sid)
    except OSError:
        return None
    for path in candidates:
        since, steps = now.timestamp() - interval_s, 0
        if not _touched_since(path, since):
            continue
        while steps < cap:
            steps += 1
            rec = probe(path, since, now)
            if rec is None:
                break
            if rec["kind"] == "assistant":
                return {"sid": path.stem, "at": rec["timestamp"]}
            stamp = ta._epoch(rec["timestamp"])  # noqa: SLF001
            if stamp is None or stamp <= since:
                break
            if (tie := _same_stamp_assistant(path, stamp)) is not None:
                return {"sid": path.stem, "at": tie["timestamp"]}
            since = stamp
        else:
            switch.trace(EV, action="scan_cap", other_sid=path.stem, steps=cap, sid=own_sid)
    return None


def rearm_fields(marker: dict, when: float) -> dict:
    """延後重排時併進標記的欄位：本類延後次數＋新的備援到點。"""
    return {DEFERS_KEY: int(marker.get(DEFERS_KEY) or 0) + 1,
            qw_schema.MK_BACKUP_FIRE_AT: qw_schema.iso(when)}


def trace(action: str, sid: str, other: dict, **extra) -> None:
    switch.trace(EV, action=action, sid=sid, other_sid=other["sid"], other_at=other["at"],
                 line=None, **extra)


def status_lines(env=None) -> list[str]:
    """標記 `status=="skipped"` ∧ `outcome.event=="other_session"` ∧ 包尚無 `.ack` ⇒ 一行（唯讀、
    任何例外回空；判斷全在本葉，status／簡報各掛 ≤3 LOC）。"""
    try:
        from . import park  # noqa: PLC0415

        out = []
        for path in park.marker_path("x").parent.glob("*.json"):
            marker = park.read_marker(path.stem)
            outcome = (marker or {}).get("outcome") or {}
            pkg = (marker or {}).get("pkg")
            if (marker and marker.get("status") == "skipped" and outcome.get("event") == "other_session"  # noqa: E501
                    and pkg and not Path(pkg).with_suffix(".ack").exists()):
                out.append(f"park 因他 session 在動而終局 skip：{pkg}")
        return out
    except Exception:  # noqa: BLE001
        return []


__all__ = ["active", "rearm_fields", "trace", "status_lines", "OTHER_SESSION_SCAN_MAX_STEPS",
           "OTHER_SESSION_MAX_DEFERS", "DEFERS_KEY", "EV"]
