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
    _RAW_MAX_CONTEXT_PARSE_OK = True
except (TypeError, ValueError):
    _RAW_MAX_CONTEXT = 200000
    _RAW_MAX_CONTEXT_PARSE_OK = False
MAX_CONTEXT = _RAW_MAX_CONTEXT if _RAW_MAX_CONTEXT > 0 else 200000

# DEF-200-275（2026-09-10）：MAX_CONTEXT 沒被操作者顯式釘住時，200000 只是舊
# 模型（Claude 3 世代）200K context window 年代留下的保守預設值——現行模型
# 視窗常是 1,000,000。硬把 ratio = cumulative / MAX_CONTEXT 套這個過時預設，
# 會讓 cumulative 一過 200000 就被誤判成「100% 滿」而擋下整個 session（實測
# cumulative=200994, ratio=1.00；使用者 /context 當場量到真實只有 38%）。
# 比照姊妹守衛 .claude/hooks/context_budget_guard.py 的 resolve_window()
# 同一手法（可證下界推論，見該檔模組 docstring〈context window 判定〉）：
# 本 session 若已實際觀測到 cumulative 超過這個保守預設，代表真實視窗必然
# 大於它，改採已知的下一檔變體；操作者若真的顯式設定 SDD_MAX_CONTEXT，一律
# 尊重其設定值、不做這層推論覆寫（也因此只在 MAX_CONTEXT 剛好等於下面這個
# 具名常數時才觸發——測試裡刻意調小 MAX_CONTEXT 讓門檻好測，不受影響）。
#
# DEF-200-275 第三輪（四方複審 QA/SA 各自獨立發現、SA 判定 REJECT 後訂正，
# 2026-09-10）：原判準只問「環境變數有沒有被設」，操作者打錯字
# （SDD_MAX_CONTEXT=abc/1.5/12k/空字串/0/-5）也會讓這裡讀到 True——即使上面
# 那段 try/except 已經正確把 _RAW_MAX_CONTEXT fallback 回 200000，這裡卻誤判
# 成「操作者刻意選了這個值」，於是 190000（真實 1,000,000 視窗下僅 19% 用量）
# 會被當成已確認分母去硬鎖 ESCALATION——與 DEF-200-275 原始 bug 同一種「未經
# 確認的分母被拿去硬擋」路徑重演。比照姊妹守衛
# .claude/hooks/context_budget_guard.py 的 `_positive_int(raw) > 0`：一個值
# 要算「已指定」，必須解析成功**且**是正整數，不能只憑「有沒有設」猜。這裡不
# 重新猜一次，直接掛鉤上面 try/except 已經算出的解析結果
# （_RAW_MAX_CONTEXT_PARSE_OK 且 _RAW_MAX_CONTEXT > 0）。
_SDD_MAX_CONTEXT_PINNED = (
    os.environ.get("SDD_MAX_CONTEXT") is not None
    and _RAW_MAX_CONTEXT_PARSE_OK
    and _RAW_MAX_CONTEXT > 0
)
_CONSERVATIVE_DEFAULT_MAX_CONTEXT = 200_000
WIDE_MAX_CONTEXT = 1_000_000


def _effective_max_context(cumulative: int) -> int:
    """DEF-200-275：見上方常數區塊註解——可證下界推論，避免拿舊模型 200K
    常數誤判現行大視窗模型已 100% 滿。"""
    if (
        not _SDD_MAX_CONTEXT_PINNED
        and MAX_CONTEXT == _CONSERVATIVE_DEFAULT_MAX_CONTEXT
        and cumulative > _CONSERVATIVE_DEFAULT_MAX_CONTEXT
    ):
        return WIDE_MAX_CONTEXT
    return MAX_CONTEXT


# DEF-200-275 第二輪（四方複審 REJECT 後訂正，2026-09-10）：第一版只切了分母，沒有
# 切「這個分母能不能拿去硬擋」。CRIT_RATIO=0.95、0.95×200000=190000——比切換點
# 200001 早了一萬。cumulative 是單調爬升的，任何 session 必然先經過
# 190000~200000 這個窗口才可能到 200001，於是在切換生效之前就已經被 190000 那個
# ratio=0.95 鎖進 ESCALATION（真實 1,000,000 視窗下僅 19% 用量）——分母切換邏輯
# 從未有機會執行到，同一個缺陷只是把觸發點從 ~100% 移到 ~95%，本質重演。
#
# 比照姊妹守衛 .claude/hooks/context_budget_guard.py 的 may_block(source) 語意：
# 硬擋／記 ESCALATION 只在「分母來源已確認」時才准——確認＝①操作者顯式設定
# SDD_MAX_CONTEXT（信任其選擇，即使值恰好等於保守預設）；②已觀測到 cumulative
# 超過保守預設（_effective_max_context 因此已切到 WIDE，這是可證的下界推論，
# 不再是純猜測，對應姊妹守衛的 SOURCE_INFERRED_WIDE）。唯一「不確認」的情形是
# 姊妹守衛的 SOURCE_INFERRED_FLOOR 等價物：未顯式設定、且 cumulative 仍未超過
# 200000——此刻 200000 純粹是「還沒證據」的保守猜測，不得拿來鎖 ESCALATION。
def _max_context_confirmed(cumulative: int) -> bool:
    """分母來源是否已確認到可以拿來硬擋／記 ESCALATION（見上方 WHY）。"""
    if _SDD_MAX_CONTEXT_PINNED:
        return True
    return _effective_max_context(cumulative) != _CONSERVATIVE_DEFAULT_MAX_CONTEXT


def _unconfirmed_notice(cumulative: int, ratio: float, tier: str) -> str:
    """CRIT／AUTO_COMPACT 門檻在分母尚未確認時的降級提示（見 `_max_context_confirmed`
    docstring）。只出聲，不呼叫 record_escalation、不 deny、不 trigger_auto_compact。"""
    return (
        f"[SDD-CTX][WARN][UNCONFIRMED-DENOM] {tier} 門檻在保守預設分母"
        f"（{_CONSERVATIVE_DEFAULT_MAX_CONTEXT:,}）下已達 ratio={ratio:.2f}"
        f"（cumulative={cumulative}），但此分母尚未確認——未顯式設定 SDD_MAX_CONTEXT，"
        f"且本 session 尚未觀測到用量超過 {_CONSERVATIVE_DEFAULT_MAX_CONTEXT:,}。"
        f"現行模型視窗常是 {WIDE_MAX_CONTEXT:,}，若貿然硬擋／記 ESCALATION 可能在"
        "真實用量僅一到兩成時就誤鎖整個 session（DEF-200-275）。本次僅示警，FSM 狀態"
        "不變。若這是操作者刻意選擇的小視窗，請顯式設定 SDD_MAX_CONTEXT 以啟用正常防護。"
    )


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
        existing_ratio = existing_cum / _effective_max_context(existing_cum) if existing_cum else 0.0
        existing_confirmed = _max_context_confirmed(existing_cum)
        if existing_ratio >= CRIT_RATIO:
            if not existing_confirmed:
                ac = _unconfirmed_notice(existing_cum, existing_ratio, "CRIT")
                if subagent_notice:
                    ac = f"{subagent_notice}\n{ac}"
                _emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": ac}})
                return 0
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
            if not existing_confirmed:
                ac = _unconfirmed_notice(existing_cum, existing_ratio, "AUTO_COMPACT")
                if subagent_notice:
                    ac = f"{subagent_notice}\n{ac}"
                _emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": ac}})
                return 0
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
    ratio = cumulative / _effective_max_context(cumulative)
    confirmed = _max_context_confirmed(cumulative)

    if ratio >= CRIT_RATIO:
        if not confirmed:
            ac = _unconfirmed_notice(cumulative, ratio, "CRIT")
            if subagent_notice:
                ac = f"{subagent_notice}\n{ac}"
            _emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": ac}})
            return 0
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
        if not confirmed:
            ac = _unconfirmed_notice(cumulative, ratio, "AUTO_COMPACT")
            if subagent_notice:
                ac = f"{subagent_notice}\n{ac}"
            _emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": ac}})
            return 0
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
