"""PostToolUse Hook — record tool result size, detect post-call spikes (ACT-012; DEF-200-275 第四輪重寫).

Reads Claude Code hook JSON from stdin. Appends a 'post' audit entry to the daily
context ledger（估算值，零決策權）並在**同一把鎖**內做 conv-overhead 合併；判級以本 session 逐字稿
API usage 的真實 ratio（`context_window.measure`）：70%（soft）／85%（warn）／90%（AUTO_COMPACT
→ trigger_auto_compact）／95%（CRIT，只出聲——deny 是 PreToolUse 的事）。量不到 ⇒ 不出聲（C3）。
AUTO_COMPACT_PENDING 且真實 used 回落 <85% ⇒ 自動 complete_auto_compact（D4／C5）。

Matcher note (A6-02, by-design — do NOT add `Task` here): the PostToolUse matcher
is `Write|Edit|Read|Bash|NotebookEdit` WITHOUT `Task`, deliberately asymmetric
with PreToolUse (which adds `Task` purely for the ACT-020 subagent-contract
injection hint, not for accounting). A subagent runs in its own context window,
so its result tokens must NOT be charged to the main session's ledger.
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

# DEF-200-275 第四輪：symmetric with context_ledger_pre.py — 門檻／量測／分母鏈只住 context_window.py。
from tools.fsm_runtime.context_window import (  # noqa: E402
    Measurement,
    auto_compact_exit_due,
    may_block,
    measure,
    ratio_tier,
    resolve_window,
    unconfirmed_notice,
    window_evidence,
)

LEDGER_DIR = _SDD_ROOT / "build" / "reports" / "fsm"


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


def _emit_msgs(msgs: list[str]) -> int:
    out = {"hookSpecificOutput": {"hookEventName": "PostToolUse"}}
    if msgs:
        out["hookSpecificOutput"]["additionalContext"] = "\n".join(msgs)
    _emit(out)
    return 0


def _session_id(inp: dict, transcript: object) -> str:
    sid = inp.get("session_id")
    if isinstance(sid, str) and sid.strip():
        return sid.strip()
    if isinstance(transcript, str) and transcript.strip():
        return Path(transcript).stem
    return "unknown"


def _measure(transcript: object) -> Measurement | None:
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


def _record_audit_and_merge(entry: dict) -> None:
    """append＋merge 在同一把 advisory lock 內（A-2）；逾時**直接**落 sidecar（F2：絕不再進
    `append_ledger_entry`／`ledger_lock` 取第二次鎖——5s+5s=10s 會撞 router 8s child timeout）；
    任何例外永不到 main()（D5）。"""
    try:
        from tools.fsm_runtime.conversation_ledger import (  # type: ignore
            append_ledger_entry,
            ledger_lock,
            merge_conversation_overhead_into_ledger,
            write_sidecar,
        )
        try:
            with ledger_lock(LEDGER_DIR):
                append_ledger_entry(LEDGER_DIR, entry, lock_held=True)
                merge_conversation_overhead_into_ledger(LEDGER_DIR, lock_held=True)
        except TimeoutError:
            write_sidecar(LEDGER_DIR, entry)
    except Exception:  # noqa: BLE001
        pass


def main() -> int:
    # D28（DEF-200-275 第七輪 SA-R7-01）：在任何 FSM 呼叫之前先標記「這是真正的 hook 行程」，
    # 供 fsm_runtime._telemetry_writeback_allowed 分辨 session 內 ad-hoc 探針 vs hook 本身。
    # 只用 setdefault：已被上游（例如測試）設過就不覆寫。
    os.environ.setdefault("SDD_FSM_HOOK_ENTRY", "1")
    if os.environ.get("SDD_HOOKS_DISABLE") == "1":
        return _emit_msgs([])

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
    # DEF-CLDREV-025：與 pre hook 對稱 — 頂層 payload / tool_input 非 dict（如 `[1,2,3]`）
    # 時 `.get()` 會拋 AttributeError 致 hook 非零退出。非 dict 一律正規化為 {}。
    if not isinstance(inp, dict):
        inp = {}
    tool = inp.get("tool_name", "")
    if not isinstance(tool, str):
        tool = ""
    tool_input = inp.get("tool_input", {})
    if not isinstance(tool_input, dict):
        tool_input = {}
    tool_response = inp.get("tool_response")
    target = tool_input.get("file_path") or tool_input.get("path")

    transcript = inp.get("transcript_path")
    m = _measure(transcript)
    sid = _session_id(inp, transcript)
    window, source = _window_for(m)

    _record_audit_and_merge({
        "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "phase": "post",
        "tool": tool,
        "target": target,
        "tokens": _estimate_result_tokens(tool_response),
        "session_id": sid,
        "observed_used": None if m is None else m.used,
        "window": window,
        "window_source": source,
    })

    # C3：量不到 ⇒ 不出聲、不判級。
    if m is None or m.used is None or not window or not source:
        return _emit_msgs([])

    msgs: list[str] = []
    rt = None
    rt_error: Exception | None = None
    try:
        from tools.fsm_runtime.fsm_runtime import FSMRuntime  # type: ignore
        rt = FSMRuntime.bootstrap()
    except Exception as exc:  # noqa: BLE001
        rt_error = exc

    label = _label(m, window, source)
    # D4／C5：PENDING 而真實 used 已回落 ⇒ compaction 完成。
    if rt is not None and rt.state.current == "AUTO_COMPACT_PENDING" \
            and auto_compact_exit_due(m.used, window):
        try:
            done = rt.complete_auto_compact(observed_effective=True, released_by=sid)
            msgs.append(
                f"[SDD-CTX][AUTO-COMPACT][DONE] {label} resume→{done.get('resumed_to')} "
                f"released_by_session={done.get('released_by_session')} "
                f"triggered_by_session={done.get('triggered_by_session')}"
            )
        except Exception as exc:  # noqa: BLE001
            msgs.append(f"[SDD-CTX][AUTO-COMPACT][DONE][WARN] complete_auto_compact failed: {exc!r}")

    ratio = m.used / window
    confirmed = may_block(source)
    tier = ratio_tier(m.used, window)

    if tier == "crit":
        if not confirmed:
            msgs.append(unconfirmed_notice(m.used, ratio, "CRIT", source))
        else:
            msgs.append(
                f"[SDD-CTX][CRIT] context ratio {ratio:.0%}（{label}）. "
                "下次 PreToolUse 將拒絕非 compact 工具 — 立即 /compact 或 Skill: stage-compaction。"
            )
    elif tier == "auto_compact":
        if not confirmed:
            msgs.append(unconfirmed_notice(m.used, ratio, "AUTO_COMPACT", source))
        elif rt is None:
            msgs.append(
                f"[SDD-CTX][AUTO-COMPACT][WARN] ratio {ratio:.0%}（{label}），但 FSMRuntime 不可用："
                f"{rt_error!r}。請立即手動呼叫 /stage-compaction。"
            )
        elif rt.state.current == "AUTO_COMPACT_PENDING":
            msgs.append(
                f"[SDD-CTX][AUTO-COMPACT] ratio {ratio:.0%}（{label}）— 已處於 AUTO_COMPACT_PENDING，"
                "請立即呼叫 Skill: stage-compaction 完成壓縮。"
            )
        else:
            try:
                result = rt.trigger_auto_compact(m.used, ratio, details={
                    "session_id": sid, "category": "context-budget", "used": m.used,
                    "window": window, "window_source": source,
                    "compact_boundaries": m.compact_boundaries,
                })
                if result.get("cap_exceeded"):
                    # D13（DEF-200-275 第五輪；同 pre hook 語意）：per-stage cap 超限不再進
                    # project-level ESCALATION，改為 session 級一次性標記——PreToolUse 側才會真的
                    # deny 非 compact 工具；這裡（PostToolUse）只出聲，不重複判定邏輯。cap_exceeded
                    # 也帶 noop=True，必須先於下面的泛用 [NOOP] 分支檢查，否則會被那支分支悄悄
                    # 蓋掉（同 pre hook 的排序理由）。
                    stage_key = result.get("stage_key", "?")
                    # D18（DEF-200-275 第六輪；同 pre hook _cap_exceeded_deny_reason 語意）：
                    # session_count 是本 session 自己真實的觸發次數；此前誤用 max_per_stage
                    # （那是門檻常數，不是次數）順手一併修正，兩支 hook 的措辭同步。
                    n = result.get("session_count", result.get("max_per_stage", "?"))
                    other_sid = result.get("other_session_id")
                    other_note = f"（另一 session={other_sid} 先前也於此 stage 觸發過 cap）" if other_sid else ""
                    msgs.append(
                        f"[SDD-CTX][AUTO-COMPACT][CAP] ratio {ratio:.0%}（{label}）— 本 session 於"
                        f" stage '{stage_key}' 已 {n} 次觸發 auto-compact 未見有效壓縮{other_note}；"
                        "PreToolUse 將對本 session 拒絕非 compact 工具（不寫 ESCALATION、不影響其他視窗）。"
                    )
                elif result.get("noop"):
                    # ARCH-06／SD-06：FSM 在 RELEASE 等不可 compact 狀態 ⇒ trigger 是 no-op，
                    # 不得再說「已進 PENDING／回落即恢復」。
                    msgs.append(
                        f"[SDD-CTX][AUTO-COMPACT][NOOP] ratio {ratio:.0%}（{label}）— "
                        f"{result.get('reason', 'auto_compact suppressed')}；FSM 未進 PENDING，請手動 /compact。"
                    )
                elif result.get("escalated"):
                    # 防禦性保留：見 context_ledger_pre.py 同名註解，per-stage cap 已改走
                    # cap_exceeded 分支；理論上不再可達，保留給未來新增的 escalated 路徑。
                    reason = result.get("reason", "auto-compact suppressed")
                    msgs.append(
                        f"[SDD-CTX][AUTO-COMPACT][ESCALATION] ratio {ratio:.0%}（{label}）— {reason}。"
                        " FSM 已進入 ESCALATION，後續工具呼叫將被 PreToolUse 阻擋，"
                        "必須人工介入（檢查是否引用文件過大 / stage 需拆分）。"
                    )
                elif result.get("already_pending"):
                    msgs.append(
                        f"[SDD-CTX][AUTO-COMPACT] ratio {ratio:.0%} — 已處於 AUTO_COMPACT_PENDING，"
                        "請立即呼叫 Skill: stage-compaction 完成壓縮。"
                    )
                else:
                    msgs.append(
                        f"[SDD-CTX][AUTO-COMPACT] ratio {ratio:.0%}（{label}）. "
                        f"FSM → AUTO_COMPACT_PENDING（resume_state={result.get('resume_state', '<unknown>')}）。"
                        f" Snapshot: {result.get('snapshot')}. "
                        "🔴 下一步必須立即呼叫 Skill: stage-compaction —"
                        " 其餘工具呼叫將被 PreToolUse 阻擋，直到真實 usage 回落 <85%。"
                    )
            except Exception as exc:  # noqa: BLE001
                msgs.append(
                    f"[SDD-CTX][AUTO-COMPACT][WARN] ratio {ratio:.0%}，但 trigger_auto_compact 失敗：{exc!r}。"
                    " 請立即手動呼叫 /stage-compaction。"
                )
    elif tier == "warn":
        msgs.append(f"[SDD-CTX][WARN] context ratio {ratio:.0%}（{label}）. 應執行 /stage-compaction。")
    elif tier == "soft":
        msgs.append(f"[SDD-CTX] context ratio {ratio:.0%}（{label}）. 開始壓縮輔助文件（改用 ID 清單）。")

    return _emit_msgs(msgs)


if __name__ == "__main__":
    sys.exit(main())
