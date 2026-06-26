"""Auto Context Snapshot writer — triggered by context_ledger_post.py at 90%.

Produces build/reports/abort/CONTEXT-SNAPSHOT-{date}-auto.md without needing
Claude in the loop. This guarantees a persisted recovery point even if the
subsequent /stage-compaction fails or the session dies.
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Optional

from .state_loader import FSMState, REPO_ROOT

SNAPSHOT_DIR = REPO_ROOT / "build" / "reports" / "abort"


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _fmt_list(items) -> str:
    if not items:
        return "  - (無)"
    return "\n".join(f"  - {it}" for it in items)


def _fmt_frozen_stages(stages) -> str:
    if not stages:
        return "| (無) | — | — |"
    lines = []
    for s in stages:
        stage = s.get("stage", "?")
        frozen_at = s.get("frozen_at", "?")
        report = s.get("compaction_report") or "—"
        lines.append(f"| {stage} | {frozen_at} | {report} |")
    return "\n".join(lines)


def _fmt_decision_trace(trace, limit: int = 20) -> str:
    """ACT-025: render the last `limit` decision trace entries as a table."""
    if not trace:
        return "| (無) | — | — | — | — |"
    rows = trace[-limit:]
    lines = []
    for e in rows:
        ts = e.get("ts", "?")
        frm = e.get("from", "?")
        to = e.get("to", "?")
        reason = (e.get("reason") or "").replace("|", "\\|")
        refs = ", ".join(e.get("spec_refs") or []) or "—"
        trg = e.get("trigger") or "—"
        lines.append(f"| {ts} | {frm} | {to} | {trg} | {reason} | {refs} |")
    return "\n".join(lines)


def save_auto_snapshot(
    state: FSMState,
    *,
    cumulative_tokens: int,
    ratio: float,
    resume_state: str,
    reason: str = "auto_90_percent",
    out_dir: Optional[Path] = None,
    compact_index: Optional[int] = None,
) -> Path:
    """Write an auto-triggered Context Snapshot. Returns the written path.

    P1-C：檔名帶 ``-{compact_index:02d}`` 後綴，避免同 stage 連續 N 次
    auto-compact 時 Snapshot 互相 overwrite（ACT-026 允許單 stage 最多 3
    次 compact）。``compact_index`` 預設由呼叫端傳入；若未傳，從
    ``state.auto_compact_state.count_per_stage`` 推算「本次」index。
    """
    date = _dt.date.today().isoformat()
    target_dir = out_dir or SNAPSHOT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    if compact_index is None:
        auto_state = state.root.get("auto_compact_state") or {}
        compact_index = int(auto_state.get("count_per_stage", 0)) + 1
    path = target_dir / f"CONTEXT-SNAPSHOT-{date}-auto-{compact_index:02d}.md"

    root = state.root
    cum = state.cumulative()
    frozen = root.get("frozen_stages") or []
    retry_scg = root.get("retry_history", {}).get("SCG_VALIDATION", {}).get("current_count", 0)
    retry_pr = root.get("retry_history", {}).get("PR_REVIEW", {}).get("current_count", 0)
    retry_rtm = root.get("retry_history", {}).get("RTM_VERIFY", {}).get("current_count", 0)

    content = f"""# SDD Context Snapshot (Auto-Generated at 90%)

**建立時間**: {_now_iso()}
**觸發原因**: {reason}（Token ratio = {ratio:.2%}, cumulative = {cumulative_tokens}）
**產生者**: context_ledger_post.py hook（非 Claude 主動產出）

---

## 當前 FSM 狀態

- **current_state**: `AUTO_COMPACT_PENDING`
- **resume_state**（compact 完成後回到）: `{resume_state}`
- **project**: {root.get('project', '<unknown>')}
- **session_id**: {root.get('session_id', '<unknown>')}

## 已完成 Stage（凍結）

| Stage | 凍結時間 | Compaction 報告 |
|-------|---------|----------------|
{_fmt_frozen_stages(frozen)}

## 當前 Retry 計數

- SCG_VALIDATION: {retry_scg}
- PR_REVIEW: {retry_pr}
- RTM_VERIFY: {retry_rtm}

## 累積歷史

- total_scg_retries_all_time: {cum.get('total_scg_retries_all_time', 0)}
- total_spec_frozen_count: {cum.get('total_spec_frozen_count', 0)}
- escalation_count: {cum.get('escalation_count', 0)}

## Pending CI Events

{_fmt_list(root.get('ci_events_pending') or [])}

## 最近 20 筆 Decision Trace（ACT-025）

| ts | from | to | trigger | reason | spec_refs |
|----|------|----|---------|--------|-----------|
{_fmt_decision_trace(root.get('decision_trace') or [], limit=20)}

---

## 恢復指引

### 情境 A：同 session 內恢復（Auto-Compact 成功）

1. Claude 會自動看到 `additionalContext` 指示
2. 立即呼叫 Skill: `stage-compaction`
3. Skill 完成後，FSMRuntime.complete_auto_compact() 自動執行：
   - 歸零當日 CONTEXT-LEDGER cumulative_tokens
   - FSM 轉回 `{resume_state}`
4. 繼續原工作

### 情境 B：跨 session 恢復（Auto-Compact 失敗 / session 中止）

1. 新 conversation 讀取 `AISDLC_SDD_INIT.md`
2. 偵測到本 snapshot 存在，進入 `session_resume` 流程
3. 讀取此 Snapshot + 最新 Stage Summary
4. 轉入 `RESUME_VERIFICATION` 閘，人工確認後從 `{resume_state}` 繼續

---

**相關文件**：
- `workflow/sdd-context-governor/SDD_CONTEXT_GOVERNOR.md` — Auto-Compact Protocol
- `workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md` — AUTO_COMPACT_PENDING state
- `AISDLC_SDD_INIT.md` — session_resume 流程
"""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)
    return path


def save_abort_report(
    state: FSMState,
    *,
    reason: str,
    category: str,
    extra_context: Optional[dict] = None,
    out_dir: Optional[Path] = None,
    diagnostic=None,
    slv_contradiction: Optional[str] = None,
) -> Path:
    """Write an Abort Report to build/reports/abort/ABORT-{date}-{category}.md.

    Required by CLAUDE.md Rule 9.5 — any ESCALATION must produce a persisted
    Abort Report so the human reviewer has a single point of reference.

    Args:
        state: current FSMState snapshot.
        reason: human-readable trigger reason.
        category: short kebab-case tag (e.g. "human-pending-timeout",
                  "auto-compact-rate-limit") — used in filename.
        extra_context: optional key/value dict appended to the report.
        out_dir: override target directory (for tests).
    """
    date = _dt.date.today().isoformat()
    target_dir = out_dir or SNAPSHOT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"ABORT-{date}-{category}.md"

    root = state.root
    cum = state.cumulative()
    if extra_context:
        extra_lines = "\n".join(f"- **{k}**: {v}" for k, v in extra_context.items())
    else:
        extra_lines = "(無額外欄位)"

    retry_scg = root.get("retry_history", {}).get("SCG_VALIDATION", {}).get("current_count", 0)
    retry_pr = root.get("retry_history", {}).get("PR_REVIEW", {}).get("current_count", 0)
    retry_rtm = root.get("retry_history", {}).get("RTM_VERIFY", {}).get("current_count", 0)

    # Phase H M6 / ACT-057：把 DiagnosticResult 轉成舵手級交接訊息（Rule 9.20.6）。
    # 先前 diagnostic 從未進入 abort 報告 — 人類只收到「retry exhausted」（§G8）。
    steersman_block = ""
    if diagnostic is not None or slv_contradiction is not None:
        try:
            from .steersman_renderer import render_markdown
            steersman_block = "\n" + render_markdown(
                diagnostic, slv_contradiction=slv_contradiction
            ) + "\n---\n"
        except Exception:  # noqa: BLE001 — steersman block is best-effort
            steersman_block = ""

    content = f"""# SDD Abort Report — {category}

**建立時間**: {_now_iso()}
**觸發原因**: {reason}
**current_state**: `{state.current}`
**project**: {root.get('project', '<unknown>')}

---

## 觸發上下文
{extra_lines}
{steersman_block}
## 當前 Retry 計數
- SCG_VALIDATION: {retry_scg}
- PR_REVIEW: {retry_pr}
- RTM_VERIFY: {retry_rtm}

## 累積歷史
- escalation_count: {cum.get('escalation_count', 0)}
- total_scg_retries_all_time: {cum.get('total_scg_retries_all_time', 0)}
- total_spec_frozen_count: {cum.get('total_spec_frozen_count', 0)}

---

## 恢復指引
1. 人工確認 abort 原因（見上）
2. 依 `AISDLC_SDD_INIT.md` §Session 恢復流程進入 `RESUME_VERIFICATION`
3. 修復規格 / 環境 / 運行條件後，呼叫 FSMRuntime 的 resume API

**相關文件**：
- `workflow/sdd-escalation/SDD_ESCALATION_PROTOCOL.md` — ESCALATION / TERMINATED
- `workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md` — FSM 狀態轉換表
"""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)

    # Phase I M3 / ACT-068：修正「同日同 category 覆寫的審計遺失點」。
    # 上面的 ABORT-{date}-{category}.md 是人類入口（attention_router digest 來源），
    # 同日同 category 會 overwrite。此處額外 append 一筆「永不覆寫的 raw 事件」到
    # ABORT-RAW-{date}.yaml（μs 級 timestamp 為唯一鍵），作為底層 audit（PI-7）。
    try:
        _append_raw_abort_event(
            target_dir, date, category=category, reason=reason, state_name=state.current,
            extra_context=extra_context,
        )
    except Exception:  # noqa: BLE001 — raw audit is best-effort, never blocks
        pass
    return path


def _append_raw_abort_event(
    target_dir: Path,
    date: str,
    *,
    category: str,
    reason: str,
    state_name: str,
    extra_context: Optional[dict] = None,
) -> Optional[Path]:
    """Append-only raw abort audit（永不覆寫；修正 ACT-068 審計遺失點）。"""
    try:
        import yaml  # type: ignore
    except Exception:  # noqa: BLE001
        return None
    raw_path = target_dir / f"ABORT-RAW-{date}.yaml"
    doc: dict = {}
    if raw_path.exists():
        try:
            doc = yaml.safe_load(raw_path.read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001
            doc = {}
    events = list(doc.get("events", []))
    events.append({
        # μs 級 timestamp 作唯一鍵 → 同日同 category 多次 abort 不再互相覆寫
        "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="microseconds"),
        "category": category,
        "reason": reason,
        "state": state_name,
        "extra_context_keys": sorted((extra_context or {}).keys()),
    })
    doc["events"] = events
    doc["date"] = date
    tmp = raw_path.with_suffix(raw_path.suffix + ".tmp")
    tmp.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    tmp.replace(raw_path)
    return raw_path
