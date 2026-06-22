"""PostToolUse Hook — record tool result size, detect post-call spikes (ACT-012).

Reads Claude Code hook JSON from stdin. Appends a 'post' entry to the daily
context ledger with result-size token estimate. Emits an additionalContext
warning when cumulative ratio crosses 70% (soft), 85% (hard), 95% (critical).
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

# DEF-CLDREV-002 + DEF-CLDREV-012: symmetric with context_ledger_pre.py —
# guard against operator misconfiguration (env=0 / negative / non-numeric).
# A zero budget would crash the :140 ratio calculation (cumulative / MAX_CONTEXT)
# with ZeroDivisionError; a non-numeric value would raise ValueError at import
# time and disable the gate. Both degrade gracefully to the 200000 default.
try:
    _RAW_MAX_CONTEXT = int(os.environ.get("SDD_MAX_CONTEXT", "200000"))
except (TypeError, ValueError):
    _RAW_MAX_CONTEXT = 200000
MAX_CONTEXT = _RAW_MAX_CONTEXT if _RAW_MAX_CONTEXT > 0 else 200000
SOFT_RATIO = 0.70
WARN_RATIO = 0.85
AUTO_COMPACT_RATIO = 0.90
CRIT_RATIO = 0.95
LEDGER_DIR = _SDD_ROOT / "build" / "reports" / "fsm"


def _ledger_path() -> Path:
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    return LEDGER_DIR / f"CONTEXT-LEDGER-{_dt.date.today().isoformat()}.yaml"


def _append(entry: dict) -> int:
    try:
        import yaml  # type: ignore
    except Exception:  # noqa: BLE001
        return 0
    path = _ledger_path()
    # M2 QA Round-2 P1-1: same advisory lock as pre-hook so concurrent writers
    # don't clobber each other's cumulative_tokens update.
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
        fallback = path.with_suffix(path.suffix + ".append")
        try:
            with fallback.open("a", encoding="utf-8") as f:
                yaml.safe_dump([entry], f, allow_unicode=True, sort_keys=False)
        except Exception:  # noqa: BLE001
            pass
        try:
            if path.exists():
                with path.open("r", encoding="utf-8") as f:
                    doc = yaml.safe_load(f) or {}
                return int(doc.get("cumulative_tokens", 0)) + int(entry.get("tokens", 0))
        except Exception:  # noqa: BLE001
            pass
        return int(entry.get("tokens", 0))


def _estimate_result_tokens(tool_response) -> int:
    try:
        if tool_response is None:
            return 0
        text = tool_response if isinstance(tool_response, str) else json.dumps(
            tool_response, ensure_ascii=False
        )
        return max(1, len(text) // 4)
    except Exception:  # noqa: BLE001
        return 0


def _emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.flush()


def main() -> int:
    if os.environ.get("SDD_HOOKS_DISABLE") == "1":
        _emit({"hookSpecificOutput": {"hookEventName": "PostToolUse"}})
        return 0

    raw = sys.stdin.read() if not sys.stdin.isatty() else "{}"
    try:
        inp = json.loads(raw or "{}")
    except json.JSONDecodeError:
        inp = {}
    tool = inp.get("tool_name", "")
    tool_input = inp.get("tool_input", {}) or {}
    tool_response = inp.get("tool_response")
    target = tool_input.get("file_path") or tool_input.get("path")

    tokens = _estimate_result_tokens(tool_response)
    cumulative = _append({
        "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "phase": "post",
        "tool": tool,
        "target": target,
        "tokens": tokens,
    })

    # ACT-024: merge conversation overhead every N tool calls so the ledger
    # reflects message-level cost, not just file I/O. Silent on failure.
    try:
        from tools.fsm_runtime.conversation_ledger import (  # type: ignore
            merge_conversation_overhead_into_ledger,
        )
        merge_result = merge_conversation_overhead_into_ledger(LEDGER_DIR)
        if merge_result.get("merged"):
            cumulative = int(merge_result.get("cumulative", cumulative))
    except Exception:  # noqa: BLE001
        pass

    ratio = cumulative / MAX_CONTEXT if cumulative else 0.0

    msg = None
    # 90% auto-compact trigger — fires before 95% CRIT to produce a recovery
    # point and force Claude into /stage-compaction.
    if CRIT_RATIO > ratio >= AUTO_COMPACT_RATIO:
        try:
            from tools.fsm_runtime.fsm_runtime import FSMRuntime  # type: ignore
            rt = FSMRuntime.bootstrap()
            result = rt.trigger_auto_compact(cumulative, ratio)
            snapshot_path = result.get("snapshot")
            resume_state = result.get("resume_state", "<unknown>")
            if result.get("escalated"):
                # ACT-026: auto_compact 被拒（per-stage 上限超過 / 已在 ESCALATION）
                reason = result.get("reason", "auto-compact suppressed")
                msg = (
                    f"[SDD-CTX][AUTO-COMPACT][ESCALATION] ratio {ratio:.0%} — {reason}。"
                    " FSM 已進入 ESCALATION，後續工具呼叫將被 PreToolUse 阻擋，"
                    "必須人工介入（檢查是否引用文件過大 / stage 需拆分）。"
                )
            elif result.get("already_pending"):
                msg = (
                    f"[SDD-CTX][AUTO-COMPACT] ratio {ratio:.0%} — 已處於 AUTO_COMPACT_PENDING，"
                    "請立即呼叫 Skill: stage-compaction 完成壓縮。"
                )
            else:
                msg = (
                    f"[SDD-CTX][AUTO-COMPACT] ratio {ratio:.0%} (cumulative={cumulative}). "
                    f"FSM → AUTO_COMPACT_PENDING（resume_state={resume_state}）。"
                    f" Snapshot: {snapshot_path}. "
                    "🔴 下一步必須立即呼叫 Skill: stage-compaction —"
                    " 其餘工具呼叫將被 PreToolUse 阻擋，直到 compact 完成。"
                )
        except Exception as exc:  # noqa: BLE001
            msg = (
                f"[SDD-CTX][AUTO-COMPACT][WARN] ratio {ratio:.0%}，但 FSMRuntime 不可用：{exc!r}。"
                " 請立即手動呼叫 /stage-compaction。"
            )
    elif ratio >= CRIT_RATIO:
        msg = (
            f"[SDD-CTX][CRIT] context ratio {ratio:.0%} (cumulative={cumulative}). "
            "下次 PreToolUse 將拒絕工具呼叫 — 立即執行 /stage-compaction 並考慮 Context Snapshot。"
        )
    elif ratio >= WARN_RATIO:
        msg = (
            f"[SDD-CTX][WARN] context ratio {ratio:.0%}. 應執行 /stage-compaction。"
        )
    elif ratio >= SOFT_RATIO:
        msg = (
            f"[SDD-CTX] context ratio {ratio:.0%}. 開始壓縮輔助文件（改用 ID 清單）。"
        )

    out = {"hookSpecificOutput": {"hookEventName": "PostToolUse"}}
    if msg:
        out["hookSpecificOutput"]["additionalContext"] = msg
    _emit(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
