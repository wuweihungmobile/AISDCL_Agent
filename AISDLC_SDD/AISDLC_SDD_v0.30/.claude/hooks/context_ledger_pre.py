"""PreToolUse Hook — FSM guardrail + context budget gate (ACT-012; DEF-200-275 第四輪重寫).

Wiring (.claude/settings.json):
    "hooks": {
      "PreToolUse": [{
        "matcher": "Write|Edit|Read|Bash|NotebookEdit|Task",
        "hooks": [{ "type": "command",
           "command": "python .claude/hooks/context_ledger_pre.py" }]
      }]
    }

Behaviour（實測語意，2026-09-10 起）:
- Reads tool_name + tool_input + transcript_path + session_id from stdin (Claude Code hook protocol).
- **分子＝真實值**：`context_window.measure(transcript_path)` 讀本 session 逐字稿最後一筆 API
  `usage`（＝`/context` 的數字）。量不到（無路徑／檔不存在／全 synthetic／compact 後尚無新 usage）
  ⇒ 零 gating、不出聲（C3）。估算帳本（conversation_ledger）只記稽核 entry，不驅動任何判定。
- **分母鏈**＝`context_window.resolve_window()`（SDD_MAX_CONTEXT → AUTOSDD_CONTEXT_WINDOW →
  harness 旋鈕 → model 標記 → Models API 查表 → 可證下界 → 保守值）；保守值只出聲、永不硬擋。
- FSM guardrail：`assert_tool_allowed()`（ESCALATION 類全擋並附一行人工恢復指令；AUTO_COMPACT_PENDING
  只放 compact 相關）。
- AUTO_COMPACT_PENDING 且真實 used 已回落 <85% window ⇒ `complete_auto_compact(observed_effective=True)`
  自動回 resume_state（Claude Code 自動 compaction 亦算完成；D4／C5）。
- ratio ≥ 95%（分母已確認）⇒ **session 級**拒絕非 compact 工具＋Snapshot（trigger_auto_compact），
  **不再**寫專案級 ESCALATION／TOKEN_BUDGET_CRITICAL（根因 C：context window 是 session 的屬性，
  FSM-STATE 是專案的屬性；舊語意會讓下一個全新視窗一開場就被擋）。per-stage cap 超限仍走既有
  結構性升級（R-9.2 failure_mode 不變）。90~95% ⇒ AUTO_COMPACT_PENDING；≥85% ⇒ WARN。
- `SDD_HOOKS_DISABLE=1` 全關（保留 ACT-020 subagent 注入）；`SDD_HOOKS_DRY_RUN=1` deny 降為警告。
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys
from pathlib import Path

_SDD_ROOT = Path(__file__).resolve().parents[2]
if str(_SDD_ROOT) not in sys.path:
    sys.path.insert(0, str(_SDD_ROOT))

# DEF-200-275 第四輪：門檻常數、分子量測、分母鏈全部只住 tools/fsm_runtime/context_window.py
# （pre/post 兩支 hook 此前各持一份逐字相同的分母邏輯與 200000 字面值）。
from tools.fsm_runtime.context_window import (  # noqa: E402
    AUTO_COMPACT_RATIO,
    CRIT_RATIO,
    WARN_RATIO,
    Measurement,
    auto_compact_exit_due,
    may_block,
    measure,
    resolve_window,
    unconfirmed_notice,
    window_evidence,
)

LEDGER_DIR = _SDD_ROOT / "build" / "reports" / "fsm"

_BYPASS_HINT = "緊急繞過：set SDD_HOOKS_DISABLE=1（全關）或 SDD_HOOKS_DRY_RUN=1（改發警告不阻擋）。"
_ESCALATION_STATES = frozenset({"ESCALATION", "ESCALATION_FINAL"})


def _is_disabled() -> bool:
    return os.environ.get("SDD_HOOKS_DISABLE") == "1"


def _is_dry_run() -> bool:
    return os.environ.get("SDD_HOOKS_DRY_RUN") == "1"


def _deny_or_warn(reason: str) -> dict:
    """Central policy point — respects SDD_HOOKS_DRY_RUN to soften deny to warning."""
    full = f"{reason} {_BYPASS_HINT}"
    if _is_dry_run():
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": f"[SDD-DRY-RUN] would deny: {full}",
            }
        }
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": full,
        }
    }


def _estimate_tokens(tool: str, tool_input: dict) -> int:
    """Delegate to conversation_ledger.estimate_tool_tokens (ACT-024).

    Falls back to the legacy size/4 estimate if the helper import fails (e.g.
    conversation_ledger.py temporarily missing during rollout). 估算值自第四輪起只寫稽核 entry。
    """
    try:
        from tools.fsm_runtime.conversation_ledger import estimate_tool_tokens  # type: ignore
        return estimate_tool_tokens(tool, tool_input or {})
    except Exception:  # noqa: BLE001
        pass
    # Legacy fallback — keep the hook resilient.
    try:
        if tool == "Read":
            p = tool_input.get("file_path")
            if p and Path(p).exists():
                size = Path(p).stat().st_size
                # P1-05 fix: count cat -n prefix (~8 chars / line) so the
                # fallback matches estimate_read_tokens and doesn't silently
                # under-estimate. Try a real line count; if unreadable, use
                # the size-based proxy (≈ 1 line per 80 chars).
                try:
                    with Path(p).open("rb") as f:
                        line_count = sum(1 for _ in f)
                except Exception:  # noqa: BLE001
                    line_count = max(1, size // 80)
                total_chars = size + line_count * 8
                return max(1, total_chars // 4)
            return 0
        if tool in {"Write", "Edit"}:
            text = tool_input.get("content") or tool_input.get("new_string") or ""
            return max(1, len(text) // 4)
        if tool == "Bash":
            cmd = tool_input.get("command", "") or ""
            return max(1, len(cmd) // 4) if cmd else 0
        if tool == "NotebookEdit":
            text = tool_input.get("new_source") or tool_input.get("content") or ""
            return max(1, len(text) // 4) if text else 0
    except Exception:  # noqa: BLE001
        pass
    return 0


def _emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.flush()


def _emit_pass(notices: list[str]) -> int:
    out = {"hookSpecificOutput": {"hookEventName": "PreToolUse"}}
    if notices:
        out["hookSpecificOutput"]["additionalContext"] = "\n".join(notices)
    _emit(out)
    return 0


def _build_subagent_notice(tool: str, tool_input: dict, runtime=None) -> str | None:
    """ACT-020 injection — runs even when SDD_HOOKS_DISABLE=1 so that
    Subagent Contract hints are not accidentally silenced by the ledger kill
    switch. Safe to call without a runtime (best-effort enter_subagent)."""
    if tool != "Task":
        return None
    try:
        from tools.fsm_runtime.subagent_contract import (  # type: ignore
            REGISTERED,
            enter_subagent,
            injection_hint_for_task,
            mode as _sub_mode,
        )
    except Exception as exc:  # noqa: BLE001
        return f"[SDD-SUBAGENT-CONTRACT][WARN] {exc!r}"

    # DEF-CLDREV-020：subagent_type/agent 若為非字串（list/dict/int 等畸形 payload）
    # 不可讓 .strip() 拋 AttributeError 致整支 hook crash（與 DEF-CLDREV-012 非數字
    # SDD_MAX_CONTEXT 同類輸入域防護）。非字串一律退回空字串 → 視為無 agent、graceful。
    _raw_agent = tool_input.get("subagent_type") or tool_input.get("agent") or ""
    agent_name = (_raw_agent if isinstance(_raw_agent, str) else "").strip().lower()
    if not agent_name or _sub_mode() == "off":
        return None
    hint = injection_hint_for_task(agent_name)
    if hint:
        try:
            enter_subagent(agent_name, runtime=runtime)
        except Exception:  # noqa: BLE001
            pass
        return hint
    if agent_name not in REGISTERED:
        return (
            f"[SDD-SUBAGENT-CONTRACT] agent={agent_name} 未註冊 — "
            "未進行 FSM 守門，建議加入 REGISTERED 清單。"
        )
    return None


def _session_id(inp: dict, transcript: object) -> str:
    sid = inp.get("session_id")
    if isinstance(sid, str) and sid.strip():
        return sid.strip()
    if isinstance(transcript, str) and transcript.strip():
        return Path(transcript).stem
    return "unknown"


def _measure(transcript: object) -> Measurement | None:
    """量不到一律 None（C3）；任何例外也當量不到——量測本身絕不能成為 deny 的原因。"""
    try:
        return measure(transcript)
    except Exception:  # noqa: BLE001
        return None


def _window_for(m: Measurement | None) -> tuple[int | None, str | None]:
    if m is None or m.used is None:
        return None, None
    try:
        return resolve_window(m.peak, **window_evidence(m.model))
    except Exception:  # noqa: BLE001
        return None, None


def _label(m: Measurement, window: int, source: str) -> str:
    return (
        f"used={m.used:,} window={window:,} 來源={source} "
        f"compact_boundaries={m.compact_boundaries}"
    )


def _details(sid: str, m: Measurement, window: int, source: str) -> dict:
    return {
        "session_id": sid,
        "category": "context-budget",
        "used": m.used,
        "window": window,
        "window_source": source,
        "compact_boundaries": m.compact_boundaries,
    }


def _recovery_hint(rt) -> str:
    try:
        from tools.fsm_runtime.recovery_hint import recovery_hint  # type: ignore
        return recovery_hint(rt.state, sdd_root=_SDD_ROOT)
    except Exception as exc:  # noqa: BLE001
        return f"[SDD-FSM][RECOVERY][WARN] recovery hint unavailable: {exc!r}"


def _record_audit(entry: dict) -> None:
    """稽核 entry（估算值＋真實 used＋分母來源）；帳本 I/O 任何例外永不到 main()（D5）。"""
    try:
        from tools.fsm_runtime.conversation_ledger import append_ledger_entry  # type: ignore
        append_ledger_entry(LEDGER_DIR, entry)
    except Exception:  # noqa: BLE001
        pass


def main() -> int:
    # zh-TW Windows pipe 預設 cp950：裸 sys.stdin.read() 遇含中文的 UTF-8 payload 會拋
    # UnicodeDecodeError → hook fail-open。改讀 bytes 端以 UTF-8+replace 解碼；
    # 無 buffer（如測試以 StringIO 替身）時回退文字端。
    _stdin_buffer = getattr(sys.stdin, "buffer", None)
    if sys.stdin.isatty():
        raw = "{}"
    elif _stdin_buffer is not None:
        raw = _stdin_buffer.read().decode("utf-8", "replace")
    else:
        raw = sys.stdin.read()
    try:
        inp = json.loads(raw or "{}")
    except json.JSONDecodeError:
        inp = {}
    # DEF-CLDREV-025：頂層 payload 可能是合法 JSON 但非 dict（如 `[1,2,3]` 解析成 list，
    # 不觸發 JSONDecodeError），tool_input 亦可能為 list/str。`.get()` 對非 dict 會拋
    # AttributeError 致整支 hook 非零退出、PreToolUse JSON 被丟棄（與 DEF-CLDREV-012/020
    # 同類型別假設輸入域缺口）。非 dict 一律正規化為 {}，graceful 視為空 payload。
    if not isinstance(inp, dict):
        inp = {}
    tool = inp.get("tool_name", "")
    # DEF-CLDREV-029（SA 鏡 F-03）：非字串 tool_name（list/dict/int）會在
    # `assert_tool_allowed(tool, target)` 處拋 TypeError，被下方寬 except 接住 → 降級為
    # 「guardrail unavailable」warn-pass，使該次工具呼叫**靜默繞過 FSM 守門**。與緊鄰的
    # tool_input 正規化不對稱（同 DEF-CLDREV-020/025 輸入域家族）。非字串退回空字串：
    # 走正常空工具放行路徑，守門對其餘有效欄位仍生效、不墜入例外網。
    if not isinstance(tool, str):
        tool = ""
    tool_input = inp.get("tool_input", {})
    if not isinstance(tool_input, dict):
        tool_input = {}
    target = (
        tool_input.get("file_path")
        or tool_input.get("path")
        or tool_input.get("notebook_path")
    )

    if _is_disabled():
        # HOOKS_DISABLE kills ledger/FSM enforcement but must NOT silence
        # Subagent Contract injection — otherwise a disabled ledger weakens
        # ACT-020 (Rule 9.8.4). Attach the hint if applicable and exit.
        notice = _build_subagent_notice(tool, tool_input)
        return _emit_pass([notice] if notice else [])

    transcript = inp.get("transcript_path")
    m = _measure(transcript)
    sid = _session_id(inp, transcript)

    # FSM guardrail
    try:
        from tools.fsm_runtime.fsm_runtime import FSMRuntime  # type: ignore
        from tools.fsm_runtime.transition_rules import TransitionError  # type: ignore

        rt = FSMRuntime.bootstrap()
    except Exception as exc:  # noqa: BLE001 — never hard-block on infra fault
        return _emit_pass([f"[SDD-FSM][WARN] guardrail unavailable: {exc!r}"])

    window, source = _window_for(m)
    notices: list[str] = []

    # D4／C5：AUTO_COMPACT_PENDING 而真實 used 已回落 ⇒ 視為 compaction 完成（含 Claude Code 自動 compact）。
    if rt.state.current == "AUTO_COMPACT_PENDING" and m is not None and window \
            and auto_compact_exit_due(m.used, window):
        try:
            done = rt.complete_auto_compact(observed_effective=True, released_by=sid)
            notices.append(
                f"[SDD-CTX][AUTO-COMPACT][DONE] {_label(m, window, source)} "
                f"resume→{done.get('resumed_to')} "
                f"released_by_session={done.get('released_by_session')} "
                f"triggered_by_session={done.get('triggered_by_session')}"
                + (f"（原 resume_state={done['remapped_from']} 非合法出口，已 remap）"
                   if done.get("remapped_from") else "")
            )
        except Exception as exc:  # noqa: BLE001
            notices.append(f"[SDD-CTX][AUTO-COMPACT][DONE][WARN] complete_auto_compact failed: {exc!r}")

    try:
        rt.assert_tool_allowed(tool, target)
    except TransitionError as err:
        reason = f"[SDD-FSM] {err}"
        if rt.state.current in _ESCALATION_STATES:
            reason += "\n" + _recovery_hint(rt)
        _emit(_deny_or_warn(reason))
        return 0
    except Exception as exc:  # noqa: BLE001 — never hard-block on infra fault
        return _emit_pass([f"[SDD-FSM][WARN] guardrail unavailable: {exc!r}"])

    # ACT-020 Subagent Dispatch Contract — for Task tool with registered agent,
    # attach a reminder so the subagent re-reads FSM state before acting.
    subagent_notice = _build_subagent_notice(tool, tool_input, runtime=rt)
    if subagent_notice:
        notices.insert(0, subagent_notice)

    # 稽核帳本（估算值＋真實值並列，供校準；tokens=0 也寫，零決策權）。
    _record_audit({
        "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "phase": "pre",
        "tool": tool,
        "target": target,
        "tokens": _estimate_tokens(tool, tool_input),
        "fsm_state": rt.state.current,
        "session_id": sid,
        "observed_used": None if m is None else m.used,
        "window": window,
        "window_source": source,
    })

    # C3：量不到 ⇒ 零 gating、不出聲。
    if m is None or m.used is None or not window or not source:
        return _emit_pass(notices)

    ratio = m.used / window
    confirmed = may_block(source)
    label = _label(m, window, source)

    if ratio >= CRIT_RATIO:
        if not confirmed:
            notices.append(unconfirmed_notice(m.used, ratio, "CRIT", source))
            return _emit_pass(notices)
        if rt.state.current != "AUTO_COMPACT_PENDING":
            trigger_result: dict = {}
            try:
                trigger_result = rt.trigger_auto_compact(
                    m.used, ratio, details=_details(sid, m, window, source)) or {}
            except Exception:  # noqa: BLE001
                pass
            if trigger_result.get("escalated"):
                # per-stage cap 超限＝結構性升級（既有 R-9.2 failure_mode），照舊 deny 並附恢復指令。
                reason = trigger_result.get("reason", "auto-compact suppressed")
                _emit(_deny_or_warn(
                    f"[SDD-CTX][CRIT][ESCALATION] ratio {ratio:.0%}（{label}）— {reason}。"
                    " 後續工具呼叫已被 FSM guardrail 阻擋，必須人工介入。\n" + _recovery_hint(rt)
                ))
                return 0
        # session 級判定：當次工具是否為 compact 相關（不寫 ESCALATION、不寫 TOKEN_BUDGET_CRITICAL）。
        try:
            rt._assert_allowed_under_auto_compact(tool, target)
        except TransitionError:
            # ARCH-06／SD-06：依狀態分句——PENDING 才有「回落即恢復 resume_state」可講；
            # RELEASE 等 no-op 狀態只有 session 級 deny 本身會隨 usage 回落解除。
            if rt.state.current == "AUTO_COMPACT_PENDING":
                tail = "真實 usage 回落 <85% 後下一次工具呼叫即自動恢復 resume_state。"
            else:
                tail = f"FSM={rt.state.current} 不進 PENDING；usage 回落 <95% 後本 deny 即解除。"
            _emit(_deny_or_warn(
                f"[SDD-CTX][CRIT] context ratio {ratio:.0%}（{label}）— 本 session 已達 95%，"
                "拒絕非 compact 工具。請 /compact 或呼叫 Skill: stage-compaction；" + tail
            ))
            return 0
        notices.append(
            f"[SDD-CTX][CRIT] context ratio {ratio:.0%}（{label}）— 只允許 compact 相關操作；"
            "請立即 /compact 或 Skill: stage-compaction。"
        )
        return _emit_pass(notices)

    # 90% auto-compact（≥90% 且 <95%，尚未 PENDING）。
    if AUTO_COMPACT_RATIO <= ratio < CRIT_RATIO and rt.state.current != "AUTO_COMPACT_PENDING":
        if not confirmed:
            notices.append(unconfirmed_notice(m.used, ratio, "AUTO_COMPACT", source))
            return _emit_pass(notices)
        trigger_result = {}
        try:
            trigger_result = rt.trigger_auto_compact(
                m.used, ratio, details=_details(sid, m, window, source)) or {}
        except Exception:  # noqa: BLE001
            pass
        if trigger_result.get("noop"):
            # ARCH-06／SD-06：RELEASE 等狀態下 trigger 是 no-op，不得宣稱已進 PENDING。
            notices.append(
                f"[SDD-CTX][AUTO-COMPACT][NOOP] ratio {ratio:.0%}（{label}）— "
                f"{trigger_result.get('reason', 'auto_compact suppressed')}；FSM 未進 PENDING，請手動 /compact。"
            )
            return _emit_pass(notices)
        if trigger_result.get("escalated"):
            reason = trigger_result.get("reason", "auto-compact suppressed")
            _emit(_deny_or_warn(
                f"[SDD-CTX][AUTO-COMPACT][ESCALATION] ratio {ratio:.0%}（{label}）— {reason}。"
                " 後續工具呼叫已被 FSM guardrail 阻擋，必須人工介入。\n" + _recovery_hint(rt)
            ))
            return 0
        notices.append(
            f"[SDD-CTX][AUTO-COMPACT] ratio {ratio:.0%}（{label}）. "
            "FSM → AUTO_COMPACT_PENDING。Context Snapshot 已持久化。"
            " 🔴 下一步必須立即呼叫 Skill: stage-compaction（或 /compact；真實 usage 回落 <85% 即自動回 resume_state）。"
        )
        return _emit_pass(notices)

    if ratio >= WARN_RATIO:
        notices.append(
            f"[SDD-CTX][WARN] context usage {ratio:.0%}（{label}）. "
            "建議立即執行 /stage-compaction 清理已凍結 Stage 詳細內容。"
        )
        return _emit_pass(notices)

    return _emit_pass(notices)


if __name__ == "__main__":
    sys.exit(main())
