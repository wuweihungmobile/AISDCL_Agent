"""PreToolUse Hook — FSM guardrail + context budget gate (ACT-012; DEF-200-275 第四／五輪重寫).

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
- **D11（第五輪 F2；複審 R-D11 補防禦）**：AUTO_COMPACT_PENDING 但本次量不到 usage（新 session
  首擊／compact 後尚無新 usage）⇒ 依 C3 放行一次＋`[UNMETERED]` notice，不讓
  `_assert_allowed_under_auto_compact` 白名單擋下這次呼叫（否則新視窗第一擊就被卡死）。
  此放行**只及於非規格檔**：Write/Edit 命中 `fsm_runtime._SPEC_TARGET_PREFIXES`
  （`docs/01_requirements|02_architecture|03_testing`）時，即使量不到 usage 仍 deny（Rule 9.6
  絕對禁令 #3；`rt.is_blocked_spec_write()` 沿用既有常數，不複製第二份清單）。**D12**：量得到仍
  PENDING deny 時，reason 必含真實數字（used=/window=/來源=）＋觸發來源 session／時間＋解除規則
  一句。
- ratio ≥ 95%（分母已確認）⇒ **session 級**拒絕非 compact 工具＋Snapshot（trigger_auto_compact），
  **不再**寫專案級 ESCALATION／TOKEN_BUDGET_CRITICAL（根因 C：context window 是 session 的屬性，
  FSM-STATE 是專案的屬性；舊語意會讓下一個全新視窗一開場就被擋）。**D13（第五輪）**：per-stage
  cap 超限**改為 session 級** `[CAP]` deny（不寫 ESCALATION、不影響其他視窗），只落一次性
  `auto_compact_state.cap_exceeded` 標記；R-9.2 catch 語意仍照記（規則守望的失敗模式真的發生，
  不要求進 project-level ESCALATION）。90~95% ⇒ AUTO_COMPACT_PENDING；≥85% ⇒ WARN。
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
# D17（DEF-200-275 第六輪；F-ARCH-04）：擴到 TOKEN_BUDGET_CRITICAL／TERMINATED——deny 訊息「一律帶
# 真實數字＋恢復指令」的精神（D12/D16）不該因為卡在哪個 blocking 狀態而不同。TOKEN_BUDGET_CRITICAL
# 目前無任何轉入邊（讀碼確認為理論死碼，Architect F-ARCH-04），TERMINATED 是合法終態，但兩者一旦
# 真的被卡住（含未來新增轉入邊、或狀態被人工/測試直接灌入），deny 訊息同樣該有溯源可讀，不留兩套
# 語意。與 fsm_runtime.py 的 `_BLOCKING_STATES`（同 4 態）刻意各自成一份常數：後者是 FSM 核心層
# 「哪些狀態擋工具呼叫」的判準，這裡是 hook 表現層「哪些狀態要多印恢復提示」的判準，語意不同不合併。
_ESCALATION_STATES = frozenset(
    {"ESCALATION", "ESCALATION_FINAL", "TOKEN_BUDGET_CRITICAL", "TERMINATED"}
)


def _is_disabled() -> bool:
    return os.environ.get("SDD_HOOKS_DISABLE") == "1"


def _is_dry_run() -> bool:
    return os.environ.get("SDD_HOOKS_DRY_RUN") == "1"


# D19（DEF-200-275 第六輪；SD-02）：非 owner session 只在 owner 已「陳舊」時才可釋放 PENDING
# ——陳舊窗口預設 30 分鐘，可用 env 覆寫（現查唯一真相源就是這個常數，不複寫成文件敘述）。
_DEFAULT_PENDING_OWNER_STALE_SECONDS = 1800


def _pending_owner_stale_seconds() -> float:
    raw = os.environ.get("SDD_PENDING_OWNER_STALE_SECONDS")
    if raw:
        try:
            return float(raw)
        except ValueError:
            pass
    return float(_DEFAULT_PENDING_OWNER_STALE_SECONDS)


def _owner_is_stale(rt) -> bool:
    """D19：owner 是否已「陳舊」——owner 的 `transcript_path` 不存在，或其 mtime 距今超過
    `SDD_PENDING_OWNER_STALE_SECONDS`。缺 `pending_owner` 記錄本身（沿用舊資料／繞過本輪機制
    直接灌狀態的測試夾具）也視為陳舊——安全的一側：寧可讓非 owner 釋放一個查無記錄的 PENDING，
    也不要因為新機制反而讓它比 D19 之前更難釋放（ARCH-03 的既有行為是「任何 session 都可釋
    放」，本輪只在 owner 記錄清楚且新鮮時才收緊，其餘一律維持舊行為）。"""
    auto = rt.state.root.get("auto_compact_state") or {}
    owner = auto.get("pending_owner")
    if not isinstance(owner, dict):
        return True
    path = owner.get("transcript_path")
    if not path:
        return True
    try:
        p = Path(path)
        if not p.exists():
            return True
        age_seconds = (
            _dt.datetime.now(_dt.timezone.utc).timestamp() - p.stat().st_mtime
        )
        return age_seconds > _pending_owner_stale_seconds()
    except OSError:
        return True


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


def _measure(transcript: object, session_id: str | None = None) -> Measurement | None:
    """量不到一律 None（C3）；任何例外也當量不到——量測本身絕不能成為 deny 的原因。
    D32-4：`session_id` 轉給 `measure()` 讀 status line feed，填 `Measurement.harness_used`。"""
    try:
        return measure(transcript, session_id=session_id)
    except Exception:  # noqa: BLE001
        return None


def _window_for(m: Measurement | None, sid: str | None = None) -> tuple[int | None, str | None]:
    """D32-3：`sid` 轉給 `window_evidence()` 讀 status line feed（harness 回報階）；
    缺席（既有呼叫端未改）時該階單純說不出話，行為與 D32 之前相同。"""
    if m is None or m.used is None:
        return None, None
    try:
        return resolve_window(m.peak, **window_evidence(m.model, session_id=sid))
    except Exception:  # noqa: BLE001
        return None, None


def _label(m: Measurement, window: int, source: str) -> str:
    return (
        f"used={m.used:,} window={window:,} 來源={source} "
        f"compact_boundaries={m.compact_boundaries}"
    )


def _details(sid: str, m: Measurement, window: int, source: str,
            transcript: object = None) -> dict:
    return {
        "session_id": sid,
        "category": "context-budget",
        "used": m.used,
        "window": window,
        "window_source": source,
        # D19（DEF-200-275 第六輪；SD-02）：owner 陳舊判準要讀 transcript 的 mtime——這裡是
        # `trigger_auto_compact()` 唯一知道呼叫端 transcript_path 的入口。非字串（None／畸形
        # payload）一律存 None，不臆測路徑。
        "transcript_path": transcript if isinstance(transcript, str) else None,
        "compact_boundaries": m.compact_boundaries,
    }


def _recovery_hint(rt, m: Measurement | None = None, window: int | None = None,
                   source: str | None = None, sid: str | None = None) -> str:
    try:
        from tools.fsm_runtime.recovery_hint import recovery_hint  # type: ignore
        return recovery_hint(rt.state, sdd_root=_SDD_ROOT, measurement=m, window=window, source=source,
                             caller_session_id=sid)
    except Exception as exc:  # noqa: BLE001
        return f"[SDD-FSM][RECOVERY][WARN] recovery hint unavailable: {exc!r}"


def _pending_unmetered_notice(rt) -> str:
    """D11（C3 補齊；DEF-200-275 第五輪 F2）：AUTO_COMPACT_PENDING 且本次量不到 usage 時的放行
    notice——說清楚是誰、何時觸發了這個 PENDING，讓新視窗第一擊不必猜。"""
    auto = rt.state.root.get("auto_compact_state") or {}
    trigger_details = auto.get("trigger_details") or {}
    trigger_sid = trigger_details.get("session_id") if isinstance(trigger_details, dict) else None
    triggered_at = auto.get("triggered_at")
    return (
        "[SDD-CTX][AUTO-COMPACT][UNMETERED] 本次呼叫量不到 usage"
        "（新 session 首擊／compact 後尚無新 usage）⇒ 依 C3 放行一次；"
        "下一次呼叫依真實 usage 判定（<85% 自動解除 PENDING）。"
        f"PENDING 由 session={trigger_sid or '未知'} 於 {triggered_at or '未知'} 觸發"
    )


def _pending_unmetered_spec_deny_reason(rt) -> str:
    """複審 R-D11（DEF-200-275 第五輪）：D11「PENDING＋量不到 usage ⇒ 放行一次」的 C3 放行只
    及於非規格檔——Write/Edit 命中 `_SPEC_TARGET_PREFIXES`（Rule 9.6 絕對禁令 #3）時，即使量不到
    usage 仍必須 deny，避免「量不到 usage 放行一次」被誤用成繞過規格檔保護的後門（原缺陷：D11
    分支在 `rt.assert_tool_allowed()` 之前就提前 return，連帶跳過了 spec 前綴保護）。"""
    auto = rt.state.root.get("auto_compact_state") or {}
    trigger_details = auto.get("trigger_details") or {}
    trigger_sid = trigger_details.get("session_id") if isinstance(trigger_details, dict) else None
    triggered_at = auto.get("triggered_at")
    return (
        "[SDD-FSM][SPEC-GUARD] state AUTO_COMPACT_PENDING — 本次呼叫量不到 usage，"
        "但量不到 usage 放行只及於非規格檔；規格檔（docs/01_requirements|02_architecture|"
        "03_testing）的 Write/Edit 不因『量不到 usage』而放行（Rule 9.6 絕對禁令 #3）。"
        f"PENDING 由 session={trigger_sid or '未知'} 於 {triggered_at or '未知'} 觸發。"
        "請呼叫 Skill: stage-compaction；真實 usage 回落 <85% 後下一次工具呼叫自動恢復 resume_state。"
    )


def _pending_deny_reason(rt, m: Measurement | None, window: int | None, source: str | None) -> str:
    """D12：PENDING 且量得到仍 deny 時，reason 必含真實數字＋來源 session＋解除規則——不再是
    空泛的「只允許 stage-compaction 相關操作」。

    複審 R-D11（DEF-200-275 第五輪）防禦性補強：呼叫端原本保證 `m` 非 None（量不到的情形已被
    D11 分支攔截並提前 return），但這個保證不該讓本函式對 `m is None` 沒有防呆——量測面任何
    未來變動都不該讓這裡拋 AttributeError。`m is None` 時老實印「量不到」，不猜數字。"""
    auto = rt.state.root.get("auto_compact_state") or {}
    trigger_details = auto.get("trigger_details") or {}
    trigger_sid = trigger_details.get("session_id") if isinstance(trigger_details, dict) else None
    triggered_at = auto.get("triggered_at")
    if m is None:
        label = "量不到 usage（新 session 首擊／compact 後尚無新 usage）"
    elif window and source:
        label = _label(m, window, source)
    else:
        label = f"used={m.used:,} window=未知（分母無法解析）"
    return (
        f"[SDD-FSM] state AUTO_COMPACT_PENDING — 只允許 /stage-compaction 相關操作"
        f"（{label}）。PENDING 由 session={trigger_sid or '未知'} 於 {triggered_at or '未知'} 觸發。"
        "請呼叫 Skill: stage-compaction；真實 usage 回落 <85% 後下一次工具呼叫自動恢復 resume_state。"
    )


def _cap_exceeded_deny_reason(trigger_result: dict) -> str:
    """D13（DEF-200-275 第五輪／ARCH-02／SD-02／QA P0）：per-stage cap 超限的 session 級 deny——
    只擋本 session 的非 compact 工具，不寫專案級 ESCALATION、不影響其他視窗。

    D18（DEF-200-275 第六輪；SD-01）：`trigger_auto_compact()` 的 cap_exceeded 判定已改依「本
    session 自己」的計數（不會再被別的 session 的計數錯誤牽連——見同函式 docstring），所以走到
    這裡時一定是本 session 自己也撞了門檻；`other_session_id` 純粹是措辭資訊：這個 stage 先前是否
    已有『另一個』session 撞過同一個 cap，讓使用者知道這不是這個 stage 第一次出狀況。`session_count`
    是本 session 自己真實的觸發次數（此前誤用 `max_per_stage`——那是門檻常數，不是次數，既有小
    bug，順手一併修正）。"""
    stage_key = trigger_result.get("stage_key", "?")
    n = trigger_result.get("session_count", trigger_result.get("max_per_stage", "?"))
    other_sid = trigger_result.get("other_session_id")
    if other_sid:
        attribution = (
            f"另一 session={other_sid} 已於此 stage 觸發過 cap；本 session 現在自己也達到"
            f"門檻（已 {n} 次）"
        )
    else:
        attribution = f"本 session 於 stage '{stage_key}' 已 {n} 次觸發"
    return (
        f"[SDD-CTX][CRIT][CAP] {attribution} auto-compact 未見有效壓縮 ⇒ 本 session 拒絕非 "
        "compact 工具（不寫 ESCALATION、不影響其他視窗）。"
        "請 /compact 或 claude -r 重啟本 session；真實 usage 回落 <90% 即解除。"
    )


def _cap_exceeded_pass_notice(trigger_result: dict, label: str) -> str:
    stage_key = trigger_result.get("stage_key", "?")
    n = trigger_result.get("max_per_stage", "?")
    return (
        f"[SDD-CTX][CAP] ratio（{label}）— stage '{stage_key}' 已 {n} 次觸發 auto-compact 未見"
        "有效壓縮；本次為 compact 白名單工具，放行。其餘非 compact 工具本 session 仍會被拒絕。"
    )


def _record_audit(entry: dict) -> None:
    """稽核 entry（估算值＋真實 used＋分母來源）；帳本 I/O 任何例外永不到 main()（D5）。"""
    try:
        from tools.fsm_runtime.conversation_ledger import append_ledger_entry  # type: ignore
        append_ledger_entry(LEDGER_DIR, entry)
    except Exception:  # noqa: BLE001
        pass


def main() -> int:
    # D28（DEF-200-275 第七輪 SA-R7-01）：在任何 FSM 呼叫之前先標記「這是真正的 hook 行程」，
    # 供 fsm_runtime._telemetry_writeback_allowed 分辨 session 內 ad-hoc 探針 vs hook 本身。
    # 只用 setdefault：已被上游（例如測試）設過就不覆寫。
    os.environ.setdefault("SDD_FSM_HOOK_ENTRY", "1")
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
    sid = _session_id(inp, transcript)
    m = _measure(transcript, sid)

    # FSM guardrail
    try:
        from tools.fsm_runtime.fsm_runtime import FSMRuntime  # type: ignore
        from tools.fsm_runtime.transition_rules import TransitionError  # type: ignore

        rt = FSMRuntime.bootstrap()
    except Exception as exc:  # noqa: BLE001 — never hard-block on infra fault
        return _emit_pass([f"[SDD-FSM][WARN] guardrail unavailable: {exc!r}"])

    window, source = _window_for(m, sid)
    notices: list[str] = []

    # D4／C5：AUTO_COMPACT_PENDING 而真實 used 已回落 ⇒ 視為 compaction 完成（含 Claude Code 自動 compact）。
    # D19（DEF-200-275 第六輪；SD-02）：釋放者是否為 owner 決定要不要多查一次陳舊——owner 自己
    # 量到回落，直接釋放（現行 D4，零改動）；非 owner 只在 owner 已陳舊（transcript 不存在／
    # 太久沒動）時才可釋放，取代 ARCH-03「任何 session 都可釋放」的乒乓（被否決的另一案）。
    if rt.state.current == "AUTO_COMPACT_PENDING" and m is not None and window \
            and auto_compact_exit_due(m.used, window):
        _pending_owner = (rt.state.root.get("auto_compact_state") or {}).get("pending_owner")
        _owner_sid = _pending_owner.get("session_id") if isinstance(_pending_owner, dict) else None
        if _owner_sid is None or sid == _owner_sid or _owner_is_stale(rt):
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
        # 非 owner 且 owner 未陳舊 ⇒ 不釋放（D19）；不 return——照樣往下走既有 gating，非 owner
        # 已因 assert_tool_allowed 的 D19 owner-scope 判準不受「只准 compact 工具」限制。

    # D11（C3 補齊；DEF-200-275 第五輪 F2）：PENDING 且本次量不到 usage（新 session 首擊／compact
    # 後尚無新 usage）⇒ 不能讓 `_assert_allowed_under_auto_compact` 白名單擋下這次呼叫——那正是
    # 「新視窗一開就被擋」的根因。放行一次＋notice，下一次呼叫依真實 usage 判定。ESCALATION 類
    # 狀態不受本條影響（僅檢查 AUTO_COMPACT_PENDING）。
    if rt.state.current == "AUTO_COMPACT_PENDING" and (m is None or m.used is None):
        # 複審 R-D11（DEF-200-275 第五輪）：C3 放行一次只及於非規格檔——不能讓「量不到 usage」
        # 連帶跳過 Rule 9.6 絕對禁令 #3（IMPLEMENTATION 等非草擬狀態禁止 Write/Edit 規格文件）。
        # 沿用 fsm_runtime 既有的 `_SPEC_TARGET_PREFIXES`／`_STATES_ALLOWING_SPEC_WRITE`，不複製
        # 第二份清單。
        if rt.is_blocked_spec_write(tool, target):
            _emit(_deny_or_warn(_pending_unmetered_spec_deny_reason(rt)))
            return 0
        subagent_notice = _build_subagent_notice(tool, tool_input, runtime=rt)
        notices.append(_pending_unmetered_notice(rt))
        if subagent_notice:
            notices.insert(0, subagent_notice)
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
        return _emit_pass(notices)

    try:
        rt.assert_tool_allowed(tool, target, session_id=sid)
    except TransitionError as err:
        if rt.state.current == "AUTO_COMPACT_PENDING":
            # D12：量得到仍 deny 時，reason 必含真實數字＋來源 session＋解除規則（m 保證非 None，
            # 因為量不到的情形已被上面的 D11 分支攔截並提前 return）。
            reason = _pending_deny_reason(rt, m, window, source)
        else:
            reason = f"[SDD-FSM] {err}"
            if rt.state.current in _ESCALATION_STATES:
                reason += "\n" + _recovery_hint(rt, m, window, source, sid)
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
                    m.used, ratio, details=_details(sid, m, window, source, transcript=transcript)) or {}
            except Exception:  # noqa: BLE001
                pass
            if trigger_result.get("cap_exceeded"):
                # D13（DEF-200-275 第五輪）：per-stage cap 超限只拒絕本 session 的非 compact
                # 工具，不再寫專案級 ESCALATION（不影響其他視窗；根因 C）。
                try:
                    rt._assert_allowed_under_auto_compact(tool, target)
                except TransitionError:
                    _emit(_deny_or_warn(_cap_exceeded_deny_reason(trigger_result)))
                    return 0
                notices.append(_cap_exceeded_pass_notice(trigger_result, label))
                return _emit_pass(notices)
            if trigger_result.get("escalated"):
                # 防禦性保留：目前 trigger_auto_compact 在 assert_tool_allowed 已放行的前提下
                # （即 state 不在 _BLOCKING_STATES）不會再回 escalated=True（per-stage cap 已改走
                # 上面的 cap_exceeded 分支）。保留這支分支是為了不讓未來新增的 escalated 路徑
                # 靜默吞掉——真的發生時仍照舊 deny 並附恢復指令。
                reason = trigger_result.get("reason", "auto-compact suppressed")
                _emit(_deny_or_warn(
                    f"[SDD-CTX][CRIT][ESCALATION] ratio {ratio:.0%}（{label}）— {reason}。"
                    " 後續工具呼叫已被 FSM guardrail 阻擋，必須人工介入。\n" + _recovery_hint(rt, m, window, source, sid)
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
                m.used, ratio, details=_details(sid, m, window, source, transcript=transcript)) or {}
        except Exception:  # noqa: BLE001
            pass
        if trigger_result.get("cap_exceeded"):
            # D13：cap_exceeded 也帶 noop=True，必須先於下面的泛用 [NOOP] 分支檢查，否則
            # cap 超限會被 [NOOP] 分支悄悄放行、遺失 session 級 CAP 拒絕（同一支函式服務
            # CRIT／AUTO_COMPACT 兩分支）。
            try:
                rt._assert_allowed_under_auto_compact(tool, target)
            except TransitionError:
                _emit(_deny_or_warn(_cap_exceeded_deny_reason(trigger_result)))
                return 0
            notices.append(_cap_exceeded_pass_notice(trigger_result, label))
            return _emit_pass(notices)
        if trigger_result.get("noop"):
            # ARCH-06／SD-06：RELEASE 等狀態下 trigger 是 no-op，不得宣稱已進 PENDING。
            notices.append(
                f"[SDD-CTX][AUTO-COMPACT][NOOP] ratio {ratio:.0%}（{label}）— "
                f"{trigger_result.get('reason', 'auto_compact suppressed')}；FSM 未進 PENDING，請手動 /compact。"
            )
            return _emit_pass(notices)
        if trigger_result.get("escalated"):
            # 防禦性保留：見上方 CRIT 分支同名註解，per-stage cap 已改走 cap_exceeded。
            reason = trigger_result.get("reason", "auto-compact suppressed")
            _emit(_deny_or_warn(
                f"[SDD-CTX][AUTO-COMPACT][ESCALATION] ratio {ratio:.0%}（{label}）— {reason}。"
                " 後續工具呼叫已被 FSM guardrail 阻擋，必須人工介入。\n" + _recovery_hint(rt, m, window, source, sid)
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
