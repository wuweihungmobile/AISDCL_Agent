"""PreToolUse Hook — FSM guardrail + context budget gate (ACT-012).

Wiring (.claude/settings.json):
    "hooks": {
      "PreToolUse": [{
        "matcher": "Write|Edit|Read|Bash|NotebookEdit|Task",
        "hooks": [{ "type": "command",
           "command": "python .claude/hooks/context_ledger_pre.py" }]
      }]
    }

Behaviour:
- Reads tool_name + tool_input from stdin (Claude Code hook protocol).
- Calls FSMRuntime.assert_tool_allowed() — blocks if state forbids.
- Estimates incremental tokens for Read/Write/Edit and appends to ledger.
- If cumulative ≥ 95% of MAX_CONTEXT → emit permissionDecision=deny
  with reason "TOKEN_BUDGET_CRITICAL"; ≥ 85% → warn via additionalContext.
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

# QA Round-5 P0 + DEF-CLDREV-012: guard against operator misconfiguration.
# A zero/negative budget would crash every ratio calculation with
# ZeroDivisionError; a non-numeric value (e.g. "abc", "1.5") would raise
# ValueError at import time and silently disable the whole context-budget gate
# (cumulative tokens stop being recorded, 85% warn / 95% deny / auto-compact
# never fire). Both classes degrade gracefully to the 200000 default.
try:
    _RAW_MAX_CONTEXT = int(os.environ.get("SDD_MAX_CONTEXT", "200000"))
except (TypeError, ValueError):
    _RAW_MAX_CONTEXT = 200000
MAX_CONTEXT = _RAW_MAX_CONTEXT if _RAW_MAX_CONTEXT > 0 else 200000
WARN_RATIO = 0.85
AUTO_COMPACT_RATIO = 0.90
CRIT_RATIO = 0.95
LEDGER_DIR = _SDD_ROOT / "build" / "reports" / "fsm"

_BYPASS_HINT = "緊急繞過：set SDD_HOOKS_DISABLE=1（全關）或 SDD_HOOKS_DRY_RUN=1（改發警告不阻擋）。"


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


def _today_ledger() -> Path:
    date = _dt.date.today().isoformat()
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    return LEDGER_DIR / f"CONTEXT-LEDGER-{date}.yaml"


def _append_ledger(entry: dict) -> int:
    path = _today_ledger()
    try:
        import yaml  # type: ignore
    except Exception:  # noqa: BLE001
        return 0
    # M2 QA Round-2 P1-1: guard read-modify-write with advisory lock so Pre+Post
    # hook interleaving cannot lose token entries. Fall back to append-only on
    # timeout to at least preserve the delta (later merge will reconcile).
    try:
        from tools.fsm_runtime.file_lock import file_lock  # type: ignore
    except Exception:  # noqa: BLE001
        file_lock = None  # type: ignore
    lock_path = path.with_suffix(path.suffix + ".lock")

    def _read_modify_write() -> int:
        existing = {}
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                existing = yaml.safe_load(f) or {}
        entries = existing.get("entries") or []
        entries.append(entry)
        cumulative = int(existing.get("cumulative_tokens", 0)) + int(entry.get("tokens", 0))
        doc = {
            "date": _dt.date.today().isoformat(),
            "cumulative_tokens": cumulative,
            "entries": entries,
        }
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False)
        os.replace(tmp, path)
        return cumulative

    if file_lock is None:
        return _read_modify_write()
    try:
        with file_lock(lock_path, timeout=5.0):
            return _read_modify_write()
    except TimeoutError:
        # Degraded fallback — write an append-only sidecar so the entry is not
        # lost. Merge tooling can reconcile at next idle moment.
        fallback = path.with_suffix(path.suffix + ".append")
        try:
            with fallback.open("a", encoding="utf-8") as f:
                yaml.safe_dump([entry], f, allow_unicode=True, sort_keys=False)
        except Exception:  # noqa: BLE001
            pass
        # Return best-effort cumulative snapshot (no lock → tolerated stale read).
        try:
            if path.exists():
                with path.open("r", encoding="utf-8") as f:
                    doc = yaml.safe_load(f) or {}
                return int(doc.get("cumulative_tokens", 0)) + int(entry.get("tokens", 0))
        except Exception:  # noqa: BLE001
            pass
        return int(entry.get("tokens", 0))


def _read_cumulative() -> int:
    """Read today's cumulative_tokens without writing — used by the tokens==0
    branch so escalation checks still run for zero-delta tool calls (P2-08)."""
    path = _today_ledger()
    if not path.exists():
        return 0
    try:
        import yaml  # type: ignore
        with path.open("r", encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
        return int(doc.get("cumulative_tokens", 0))
    except Exception:  # noqa: BLE001
        return 0


def _estimate_tokens(tool: str, tool_input: dict) -> int:
    """Delegate to conversation_ledger.estimate_tool_tokens (ACT-024).

    Falls back to the legacy size/4 estimate if the helper import fails (e.g.
    conversation_ledger.py temporarily missing during rollout).
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


def main() -> int:
    raw = sys.stdin.read() if not sys.stdin.isatty() else "{}"
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
        out = {"hookSpecificOutput": {"hookEventName": "PreToolUse"}}
        if notice:
            out["hookSpecificOutput"]["additionalContext"] = notice
        _emit(out)
        return 0

    # FSM guardrail
    try:
        from tools.fsm_runtime.fsm_runtime import FSMRuntime  # type: ignore
        from tools.fsm_runtime.transition_rules import TransitionError  # type: ignore

        rt = FSMRuntime.bootstrap()
        try:
            rt.assert_tool_allowed(tool, target)
        except TransitionError as err:
            _emit(_deny_or_warn(f"[SDD-FSM] {err}"))
            return 0
    except Exception as exc:  # noqa: BLE001 — never hard-block on infra fault
        _emit({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": f"[SDD-FSM][WARN] guardrail unavailable: {exc!r}",
            }
        })
        return 0

    # ACT-020 Subagent Dispatch Contract — for Task tool with registered agent,
    # attach a reminder so the subagent re-reads FSM state before acting.
    subagent_notice = _build_subagent_notice(tool, tool_input, runtime=rt)

    # Context budget ledger
    tokens = _estimate_tokens(tool, tool_input)
    if tokens == 0:
        # P2-08 fix: even zero-delta tool calls must honour escalation /
        # AUTO_COMPACT thresholds — otherwise a caller can starve out the
        # budget gate by spamming zero-cost tools while cumulative is
        # already past 95%. Read existing cumulative and short-circuit
        # before the normal entry-appending path.
        existing_cum = _read_cumulative()
        existing_ratio = existing_cum / MAX_CONTEXT if existing_cum else 0.0
        if existing_ratio >= CRIT_RATIO:
            try:
                rt.state.record_escalation(
                    f"TOKEN_BUDGET_CRITICAL: cumulative={existing_cum} "
                    f"ratio={existing_ratio:.2f} (zero-delta tool)"
                )
                from tools.fsm_runtime.state_loader import save_state  # type: ignore
                save_state(rt.state)
            except Exception:  # noqa: BLE001
                pass
            _emit(_deny_or_warn(
                f"[SDD-CTX] TOKEN_BUDGET_CRITICAL (cumulative={existing_cum}, "
                f"ratio={existing_ratio:.2f}). 必須立即執行 /stage-compaction 並產出 Context Snapshot。"
            ))
            return 0
        if (
            AUTO_COMPACT_RATIO <= existing_ratio < CRIT_RATIO
            and rt.state.current != "AUTO_COMPACT_PENDING"
        ):
            trigger_result: dict = {}
            try:
                trigger_result = rt.trigger_auto_compact(existing_cum, existing_ratio) or {}
            except Exception:  # noqa: BLE001
                pass
            if trigger_result.get("escalated"):
                reason = trigger_result.get("reason", "auto-compact suppressed")
                _emit(_deny_or_warn(
                    f"[SDD-CTX][AUTO-COMPACT][ESCALATION] ratio {existing_ratio:.0%} — {reason}。"
                    " 後續工具呼叫已被 FSM guardrail 阻擋，必須人工介入。"
                ))
                return 0
            ac = (
                f"[SDD-CTX][AUTO-COMPACT] ratio {existing_ratio:.0%} "
                f"(cumulative={existing_cum}). FSM → AUTO_COMPACT_PENDING。"
                " 🔴 下一步必須立即呼叫 Skill: stage-compaction。"
            )
            if subagent_notice:
                ac = f"{subagent_notice}\n{ac}"
            _emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": ac}})
            return 0
        out_no_tokens = {"hookSpecificOutput": {"hookEventName": "PreToolUse"}}
        if subagent_notice:
            out_no_tokens["hookSpecificOutput"]["additionalContext"] = subagent_notice
        _emit(out_no_tokens)
        return 0

    cumulative = _append_ledger({
        "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "phase": "pre",
        "tool": tool,
        "target": target,
        "tokens": tokens,
        "fsm_state": rt.state.current,
    })
    ratio = cumulative / MAX_CONTEXT

    if ratio >= CRIT_RATIO:
        try:
            rt.state.record_escalation(
                f"TOKEN_BUDGET_CRITICAL: cumulative={cumulative} ratio={ratio:.2f}"
            )
            from tools.fsm_runtime.state_loader import save_state  # type: ignore
            save_state(rt.state)
        except Exception:  # noqa: BLE001
            pass
        _emit(_deny_or_warn(
            f"[SDD-CTX] TOKEN_BUDGET_CRITICAL (cumulative={cumulative}, "
            f"ratio={ratio:.2f}). 必須立即執行 /stage-compaction 並產出 Context Snapshot。"
        ))
        return 0
    # 90% auto-compact: trigger here too (defensive; post hook triggers primarily).
    # Once in AUTO_COMPACT_PENDING, assert_tool_allowed() above已經把非 compact 工具擋下來。
    if AUTO_COMPACT_RATIO <= ratio < CRIT_RATIO and rt.state.current != "AUTO_COMPACT_PENDING":
        trigger_result: dict = {}
        try:
            trigger_result = rt.trigger_auto_compact(cumulative, ratio) or {}
        except Exception:  # noqa: BLE001
            pass
        if trigger_result.get("escalated"):
            reason = trigger_result.get("reason", "auto-compact suppressed")
            _emit(_deny_or_warn(
                f"[SDD-CTX][AUTO-COMPACT][ESCALATION] ratio {ratio:.0%} — {reason}。"
                " 後續工具呼叫已被 FSM guardrail 阻擋，必須人工介入。"
            ))
            return 0
        ac = (
            f"[SDD-CTX][AUTO-COMPACT] ratio {ratio:.0%} (cumulative={cumulative}). "
            "FSM → AUTO_COMPACT_PENDING。Context Snapshot 已持久化。"
            " 🔴 下一步必須立即呼叫 Skill: stage-compaction。"
        )
        if subagent_notice:
            ac = f"{subagent_notice}\n{ac}"
        _emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": ac}})
        return 0
    if ratio >= WARN_RATIO:
        ac = (
            f"[SDD-CTX][WARN] context usage {ratio:.0%} (~{cumulative} tokens). "
            "建議立即執行 /stage-compaction 清理已凍結 Stage 詳細內容。"
        )
        if subagent_notice:
            ac = f"{subagent_notice}\n{ac}"
        _emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": ac}})
        return 0

    out_final = {"hookSpecificOutput": {"hookEventName": "PreToolUse"}}
    if subagent_notice:
        out_final["hookSpecificOutput"]["additionalContext"] = subagent_notice
    _emit(out_final)
    return 0


if __name__ == "__main__":
    sys.exit(main())
