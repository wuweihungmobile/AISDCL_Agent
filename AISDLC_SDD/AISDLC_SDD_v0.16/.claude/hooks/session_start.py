"""SessionStart Hook — reconcile CI-EVENT + inject FSM status (ACT-011).

Wiring (.claude/settings.json):
    "hooks": {
      "SessionStart": [{ "hooks": [{
         "type": "command",
         "command": "python AISDLC_SDD_v0.01/.claude/hooks/session_start.py"
      }] }]
    }

Output: JSON to stdout → Claude Code injects as additionalContext.
Never raises; on failure emits a WARN line so sessions still start.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

# Allow `import tools.fsm_runtime...` when invoked from anywhere.
_SDD_ROOT = Path(__file__).resolve().parents[2]
if str(_SDD_ROOT) not in sys.path:
    sys.path.insert(0, str(_SDD_ROOT))


def _rule_lines(state: str) -> list:
    """Phase 2 (2a)：逐態揭露 — 回傳當前 FSM 狀態命中的治理規則摘要行。

    把 governance/rules/R-*.yaml 依當前狀態 lazy-surface 注入 session context，
    取代 CLAUDE.md Rule 9 的 eager-load（落實 Phase H ACT-051 漸進式揭露）。
    純函式（只依賴 state 字串），便於單元測試；任何例外回空列表、絕不阻斷 session。
    """
    try:
        from tools.fsm_runtime import rule_loader  # type: ignore
        rules = rule_loader.load_for_state(state)
    except Exception:  # noqa: BLE001 — never block session start
        return []
    if not rules:
        return []
    out = [
        "",
        f"[SDD-RULES] 當前狀態 {state} 命中 {len(rules)} 條治理規則（細節見 governance/rules/）：",
    ]
    for r in rules:
        out.append(f"  - [{r.id}] {r.title}（{r.severity}）")
    out.append("  完整地圖：governance/RULES_INDEX.md")
    return out


def _build_context() -> dict:
    if os.environ.get("SDD_HOOKS_DISABLE") == "1":
        return {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": "[SDD-FSM] hooks disabled via SDD_HOOKS_DISABLE=1",
            }
        }
    try:
        from tools.fsm_runtime.fsm_runtime import FSMRuntime  # type: ignore
    except Exception as exc:  # noqa: BLE001
        return {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": (
                    f"[SDD-FSM][WARN] fsm_runtime not importable: {exc!r}. "
                    "PyYAML 可能尚未安裝 — 執行 `pip install pyyaml` 後重啟 session。"
                ),
            }
        }

    try:
        rt = FSMRuntime.bootstrap()
        applied = rt.reconcile_ci_events()
    except Exception as exc:  # noqa: BLE001
        return {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": f"[SDD-FSM][ERROR] bootstrap failed: {exc!r}",
            }
        }

    # ACT-023: HUMAN_PENDING wall-clock timeout check (72h reminder / 168h escalate).
    timeout_info = None
    try:
        from tools.fsm_runtime.timeout_checker import (  # type: ignore
            evaluate_human_pending,
            mark_entered_now,
            mark_reminder_sent,
        )
        verdict = evaluate_human_pending(rt.state)
        if verdict["outcome"] == "NO_TIMESTAMP":
            mark_entered_now(rt.state)
            from tools.fsm_runtime.state_loader import save_state  # type: ignore
            save_state(rt.state)
            timeout_info = "[SDD-FSM][HUMAN-PENDING] 補打時戳（entered_at=now），後續將正常計時。"
        elif verdict["outcome"] == "REMINDER":
            tracking = rt.state.root.get("human_pending_tracking") or {}
            if not tracking.get("reminder_sent_at"):
                mark_reminder_sent(rt.state)
                from tools.fsm_runtime.state_loader import save_state  # type: ignore
                save_state(rt.state)
            tracking = rt.state.root.get("human_pending_tracking") or {}
            reminder_ts = tracking.get("reminder_sent_at") or "just-now"
            timeout_info = (
                f"[SDD-FSM][HUMAN-PENDING][REMINDER] 已等待 {verdict['elapsed_hours']}h "
                f"(>{verdict['reminder_hours']}h) — 請儘速完成確認，"
                f"超過 {verdict['escalation_hours']}h 將自動 ESCALATION。"
                f"\n  reminder_sent_at={reminder_ts}（此訊息不會重送，下次警告即 ESCALATION）"
            )
        elif verdict["outcome"] == "ESCALATION":
            reason = (
                f"HUMAN_PENDING 逾時 {verdict['elapsed_hours']}h "
                f"(≥{verdict['escalation_hours']}h)，自動進入 ESCALATION (ACT-023)"
            )
            # W-37-1：委派 runtime 單一入口（record_escalation + R-9.7 catch 歸因同落點）。
            rt.escalate_human_pending_timeout(reason=reason)
            from tools.fsm_runtime.state_loader import save_state  # type: ignore
            save_state(rt.state)
            try:
                from tools.fsm_runtime.snapshot import save_abort_report  # type: ignore
                abort_path = save_abort_report(
                    rt.state,
                    reason=reason,
                    category="human-pending-timeout",
                    extra_context={
                        "elapsed_hours": verdict["elapsed_hours"],
                        "escalation_hours": verdict["escalation_hours"],
                        "entered_at": verdict.get("entered_at"),
                    },
                )
                timeout_info = (
                    f"[SDD-FSM][HUMAN-PENDING][ESCALATION] {reason}\n"
                    f"  Abort Report: {abort_path}"
                )
            except Exception as exc:  # noqa: BLE001
                timeout_info = (
                    f"[SDD-FSM][HUMAN-PENDING][ESCALATION] {reason} "
                    f"(abort report failed: {exc!r})"
                )
    except Exception as exc:  # noqa: BLE001
        timeout_info = f"[SDD-FSM][HUMAN-PENDING][WARN] timeout_checker failed: {exc!r}"

    # ACT-027 (M3): Production Feedback Layer — scan inbox for SLO events.
    # Non-blocking: failure here must never prevent session startup.
    prod_info = None
    try:
        from tools.fsm_runtime.production_monitor import scan_inbox  # type: ignore

        report = scan_inbox()
        # Update FSM-STATE production_signal_tracking lazily.
        tracking = rt.state.root.setdefault("production_signal_tracking", {})
        import datetime as _dt
        tracking["last_scan_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        tracking["events_ingested_count"] = int(tracking.get("events_ingested_count", 0)) + report.applied
        tracking["events_quarantined_count"] = int(tracking.get("events_quarantined_count", 0)) + report.quarantined
        if report.drift_reports:
            existing = list(tracking.get("drift_reports_written") or [])
            for p in report.drift_reports:
                if p not in existing:
                    existing.append(p)
            tracking["drift_reports_written"] = existing
        if report.scanned:
            from tools.fsm_runtime.state_loader import save_state  # type: ignore
            save_state(rt.state)
            parts = [
                f"[SDD-PROD] SLO inbox scan: scanned={report.scanned}",
                f"applied={report.applied}",
                f"quarantined={report.quarantined}",
            ]
            if report.drift_reports:
                parts.append(f"drift_reports={len(report.drift_reports)}")
            prod_info = " ".join(parts)
            if report.drift_reports:
                prod_info += (
                    "\n  PBS-DRIFT reports:\n    - "
                    + "\n    - ".join(report.drift_reports)
                )
            if report.quarantined:
                prod_info += (
                    "\n  ⚠️ 有 {q} 件事件進入 quarantine（簽章或 schema 失敗），"
                    "請檢視 data/slo_events/quarantine/"
                ).format(q=report.quarantined)
    except Exception as exc:  # noqa: BLE001
        prod_info = f"[SDD-PROD][WARN] SLO inbox scan failed: {exc!r}"

    # ACT-030 (Phase F M2 D-30.11): Cross-Project Learning Hub auto-pull.
    # Behaviour: respect 24h cache (sync_policy.pull.cache_ttl_hours); failure
    # is non-blocking (HUB-GOVERNANCE-SPEC §捌). Disabled when SDD_HUB_DISABLE=1
    # or when registry has no allowed_endpoints (default fresh install).
    hub_info: Optional[str] = None
    if os.environ.get("SDD_HUB_DISABLE") != "1":
        try:
            from tools.fsm_runtime.hub_sync import HubSyncClient, HubConfigError  # type: ignore
            client = HubSyncClient()
            policy = (client.registry.get("sync_policy") or {}).get("pull", {})
            if policy.get("auto_pull_on_session_start") and client.endpoints:
                # Use first registered endpoint when only one is allow-listed.
                ep = next(iter(client.endpoints.values()))
                pull_res = client.pull(ep.id)
                if pull_res.error:
                    hub_info = (
                        f"[SDD-HUB][WARN] auto-pull failed (non-blocking): {pull_res.error}"
                    )
                else:
                    hub_info = (
                        f"[SDD-HUB] endpoint={ep.id} cache_fresh={pull_res.cache_was_fresh} "
                        f"files={len(pull_res.pulled_files)}"
                    )
        except HubConfigError as exc:
            hub_info = f"[SDD-HUB][WARN] {exc}"
        except Exception as exc:  # noqa: BLE001 — never block session start
            hub_info = f"[SDD-HUB][WARN] auto-pull error: {exc!r}"

    cum = rt.state.cumulative()
    total_retries = int(cum.get("total_scg_retries_all_time", 0))
    warnings = []
    if timeout_info:
        warnings.append(timeout_info)
    if prod_info:
        warnings.append(prod_info)
    if hub_info:
        warnings.append(hub_info)
    if total_retries > 10:
        warnings.append(
            f"[SDD-FSM][WARN] total_scg_retries_all_time={total_retries} (>10). "
            "建議進入 SPEC_AUDIT 檢查規格是否有系統性矛盾。"
        )
    if rt.state.current in {"ESCALATION", "ESCALATION_FINAL", "TERMINATED", "TOKEN_BUDGET_CRITICAL"}:
        warnings.append(
            f"[SDD-FSM][BLOCK] 當前狀態 {rt.state.current} — 所有工具呼叫將被 PreToolUse 阻擋，"
            "必須人工介入並執行 Session 恢復流程。"
        )
    if rt.state.current == "AUTO_COMPACT_PENDING":
        auto = rt.state.root.get("auto_compact_state", {}) or {}
        resume_state = auto.get("resume_state", "<unknown>")
        snapshot = auto.get("snapshot_path", "<none>")
        # QA Round-5 P1: verify snapshot file actually exists on disk.
        # If the PostToolUse hook failed mid-write (disk full / permission),
        # state may read AUTO_COMPACT_PENDING while the referenced snapshot
        # is missing — stage-compaction would then fail with an opaque read
        # error. Surface this explicitly so operators can recover manually.
        snapshot_missing = False
        if snapshot and snapshot != "<none>":
            try:
                snapshot_missing = not Path(snapshot).exists()
            except OSError:
                snapshot_missing = True
        missing_note = (
            "\n  ⚠️ Snapshot 檔案不存在於磁碟 — PostToolUse hook 可能寫入失敗，"
            "請手動檢查 build/reports/abort/ 並重建 Snapshot 後再呼叫 stage-compaction。"
            if snapshot_missing
            else ""
        )
        warnings.append(
            f"[SDD-FSM][AUTO-COMPACT] 上次 Session 於 90% Token 中止（resume_state={resume_state}）。\n"
            f"  Snapshot: {snapshot}{missing_note}\n"
            "  🔴 必須立即呼叫 Skill: stage-compaction 完成壓縮；完成後會自動回到 resume_state 繼續執行。"
        )

    lines = [
        "[SDD-FSM] Session bootstrap",
        f"- project: {rt.state.root.get('project', '<unknown>')}",
        f"- current_state: {rt.state.current}",
        f"- applied_ci_events: {len(applied)}"
        + (f" ({', '.join(applied)})" if applied else ""),
        f"- total_scg_retries_all_time: {total_retries}",
    ]

    # ACT-025: inject last 5 decision trace entries so resuming sessions
    # can make consistent decisions without re-reading the full FSM-STATE.
    try:
        trace = rt.state.root.get("decision_trace") or []
        if trace:
            lines.append("")
            lines.append("[SDD-FSM][DECISION-TRACE] 最近 5 筆狀態轉換：")
            for e in trace[-5:]:
                ts = e.get("ts", "?")
                frm = e.get("from", "?")
                to = e.get("to", "?")
                reason = e.get("reason") or ""
                trg = e.get("trigger") or ""
                lines.append(f"  - {ts} {frm}->{to} [{trg}] {reason}")
    except Exception:  # noqa: BLE001 — never block session start
        pass

    # Phase 2 (2a): 逐態揭露當前狀態命中的治理規則（lazy-surface 取代 eager-load）。
    lines.extend(_rule_lines(rt.state.current))

    if warnings:
        lines.append("")
        lines.extend(warnings)

    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n".join(lines),
        }
    }


def main() -> int:
    try:
        payload = _build_context()
    except Exception as exc:  # noqa: BLE001
        payload = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": f"[SDD-FSM][ERROR] {exc!r}",
            }
        }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
