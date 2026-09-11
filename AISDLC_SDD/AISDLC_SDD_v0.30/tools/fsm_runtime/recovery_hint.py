"""ESCALATION 的人工恢復提示——印出**一行可直接複製執行的指令**（DEF-200-275 第四輪 D6／C10）。

WHY：此前 SessionStart 的 BLOCK 訊息只說「必須人工介入並執行 Session 恢復流程」，恢復流程住在
`AISDLC_SDD_INIT.md` 的 yaml 敘述裡，沒有可執行的 CLI；context budget 誤觸的 ESCALATION 又是
專案級、跨 session 黏著（根因 C），使用者開新視窗照樣被擋、卻拿不到一條能跑的指令。

R-9.5 只規範「進入 ESCALATION 後**禁止自動**恢復」；本模組產出的是給**人**在終端執行的指令，
走既有合法邊 `ESCALATION→RESUME_VERIFICATION→<resume_state>`，零新增狀態／邊、不碰 TLA。
`-m tools.fsm_runtime.fsm_runtime` 是唯一可跑形態（直跑檔案會因相對 import 而 ImportError）。
"""
from __future__ import annotations

import datetime as _dt
import re
import sys
from pathlib import Path
from typing import Callable, Optional

# ARCH-04：`RESUME_TARGETS` 的家在核心 `fsm_runtime`（表現層反過來 import，不讓核心依賴表現層）。
from .fsm_runtime import RESUME_TARGETS  # noqa: F401  (re-export for callers/tests)

#: 根層 hook 載具刻意是 GUI 子系統 `pythonw.exe`（exec form，免每次觸發閃 console 視窗）；
#: 人在終端跑的必須是同目錄的 console 版 `python.exe`。POSIX 永不命中（鐵律三：另一平台的值）。
_WINDOWS_GUI_PYTHON = "pythonw.exe"
_WINDOWS_CONSOLE_PYTHON = "python.exe"

CATEGORY_CONTEXT_BUDGET = "context-budget"
CATEGORY_STRUCTURAL = "structural"
#: 舊格式（第四輪前無 details）只能由 trigger_reason 前綴推斷類別。
_CONTEXT_BUDGET_PREFIXES = ("TOKEN_BUDGET_CRITICAL", "auto_compact exceeded")
_UNRECORDED = "未記錄（第四輪前）"
#: D17（DEF-200-275 第六輪）：`escalation_provenance` 三欄缺席時的機讀 sentinel（與人讀 `_UNRECORDED`
#: 分開——前者是 FSM-STATE 持久化的機讀值，後者是給人看的舊格式訊息，兩者語意不同，不可合併）。
_PROVENANCE_UNKNOWN = "unknown"

#: ARCH-R6-01（DEF-200-275 第六輪複審）容錯窗：合法落點是「先呼叫 record_escalation() 落
#: provenance，再呼叫 transition("ESCALATION", ...) 補 decision_trace」——兩次 `_now()` 呼叫
#: 落在同一次 Python 函式呼叫內，理論上同一秒，但若剛好跨過整秒邊界最多差 ~1 秒。用這個容錯窗
#: 吸收該賽跑，避免把「剛寫完、合法」的 provenance 誤判成陳舊；真正陳舊（繞過 record_escalation
#: 的站點）的落差是「上一次已解決事件」的規模（通常分鐘／小時起跳），遠大於此窗。
_STALE_PROVENANCE_GRACE_SECONDS = 5


def _hours_ago(at_iso: Optional[str], *, now: Optional["_dt.datetime"] = None) -> str:
    """D17：把 provenance 的 ISO 時間戳換算成「N 小時前」；解析失敗／缺值一律老實說「時間未知」，
    不臆測（`now` 可注入供測試固定時鐘，預設 UTC now）。"""
    if not at_iso:
        return "時間未知"
    try:
        at = _dt.datetime.fromisoformat(at_iso)
    except (TypeError, ValueError):
        return "時間未知"
    if at.tzinfo is None:
        at = at.replace(tzinfo=_dt.timezone.utc)
    ref = now or _dt.datetime.now(_dt.timezone.utc)
    delta_hours = max(0.0, (ref - at).total_seconds() / 3600)
    return f"{delta_hours:.1f} 小時前"


def _parse_iso(at_iso: Optional[str]) -> Optional["_dt.datetime"]:
    """ARCH-R6-01：ISO 時間戳 → aware datetime；解析失敗／缺值回 None（不臆測，呼叫端自行決定
    fallback）。naive 字串一律當 UTC（與 `_hours_ago` 同假設）。"""
    if not at_iso:
        return None
    try:
        at = _dt.datetime.fromisoformat(at_iso)
    except (TypeError, ValueError):
        return None
    if at.tzinfo is None:
        at = at.replace(tzinfo=_dt.timezone.utc)
    return at


def _entered_escalation_at(state) -> Optional["_dt.datetime"]:
    """ARCH-R6-01（DEF-200-275 第六輪複審）：算出『本次』轉入 ESCALATION 的時間戳，供
    recovery_hint() 比對 `escalation_provenance.at` 是否陳舊（屬於更早、已解除的事件）。

    優先讀 `decision_trace` 最後一筆 `to == "ESCALATION"` 的 `ts`——`FSMRuntime.transition()`
    無論呼叫端有沒有先呼叫 `record_escalation()` 都會無條件寫這筆，是偵測「繞過
    record_escalation 直接轉態」最準的訊號。量不到（decision_trace 缺席／未含這筆／時間戳解析
    失敗）時退回 state 檔本身的 mtime 兜底——`record_escalation()`／`transition()` 的呼叫端幾乎
    都會在同一次呼叫內接著 `save_state()`，mtime 因此是「最後一次寫狀態」的保守代理值。兩者皆
    量不到時回 None，呼叫端此時沒有比較基準、不得斷言陳舊（fail-open，寧可少提醒也不亂報）。
    """
    trace = state.root.get("decision_trace")
    if isinstance(trace, list):
        for entry in reversed(trace):
            if isinstance(entry, dict) and entry.get("to") == "ESCALATION":
                parsed = _parse_iso(entry.get("ts"))
                if parsed is not None:
                    return parsed
                break  # 最新一筆轉入紀錄時間戳解壞——不採信更早的舊紀錄，直接落 mtime 兜底
    path = getattr(state, "path", None)
    if path is None:
        return None
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    return _dt.datetime.fromtimestamp(mtime, tz=_dt.timezone.utc)


def classify_escalation(entry: dict | None) -> str:
    """`details.category` 優先；否則以 trigger_reason 前綴推斷：context-budget 或 structural。"""
    if not isinstance(entry, dict):
        return CATEGORY_STRUCTURAL
    category = entry.get("category")
    if isinstance(category, str) and category:
        return category
    reason = str(entry.get("trigger_reason") or "")
    if reason.startswith(_CONTEXT_BUDGET_PREFIXES):
        return CATEGORY_CONTEXT_BUDGET
    return CATEGORY_STRUCTURAL


def resume_target(state) -> tuple[str, bool]:
    """`(目標狀態, 是否 fallback)`：`auto_compact_state.resume_state` ∈ RESUME_TARGETS 就用它，
    否則 SPEC_DRAFTING（fallback=True，訊息會註明）。"""
    auto = state.root.get("auto_compact_state") or {}
    candidate = auto.get("resume_state") if isinstance(auto, dict) else None
    if isinstance(candidate, str) and candidate in RESUME_TARGETS:
        return candidate, False
    return "SPEC_DRAFTING", True


def console_python(python: str, *, exists: Optional[Callable[[Path], bool]] = None) -> str:
    """F3（ARCH-01／SA-R4-04）：hook 行程的 `sys.executable` 若是 `pythonw.exe`，換成同目錄 `python.exe`
    （存在才換；不存在照印原值，誠實）。`exists` 可注入，讓非 Windows 也能測到這條分支。"""
    p = Path(python)
    if p.name.lower() != _WINDOWS_GUI_PYTHON:
        return python
    console = p.with_name(_WINDOWS_CONSOLE_PYTHON)
    check = exists or (lambda q: q.exists())
    try:
        return str(console) if check(console) else python
    except OSError:
        return python


def recovery_command(*, sdd_root: Path, python: str, target: str, reason: str,
                     shell: str = "posix", exists: Optional[Callable[[Path], bool]] = None) -> str:
    """一行可複製的恢復指令。`shell`＝`posix`（bash／zsh：`cd … ;`）或 `powershell`
    （`Set-Location …; & "<py>" …`——`&` 必須緊貼直譯器路徑前，不是整行最前）。`-m` 是唯一可跑
    形態。理由裡的雙引號、`$`、反引號、反斜線一律換成 `'`（SA-R4-09／SD-R2-04）：兩殼的雙引號字串都會
    對 `$`／反引號插值、對反斜線逸出；reason 目前是機器字串，仍不假設它永遠乾淨。"""
    safe_reason = re.sub(r'["$`\\]', "'", reason)
    py = console_python(python, exists=exists)
    tail = (
        f'"{py}" -m tools.fsm_runtime.fsm_runtime '
        f'resume-from-escalation --to {target} --reason "{safe_reason}"'
    )
    if shell == "powershell":
        return f'Set-Location "{sdd_root}"; & {tail}'
    return f'cd "{sdd_root}" ; {tail}'


def recovery_hint(state, *, sdd_root: Path, python: str = sys.executable,
                  exists: Optional[Callable[[Path], bool]] = None,
                  measurement: object = None, window: Optional[int] = None,
                  source: Optional[str] = None,
                  caller_session_id: Optional[str] = None,
                  _now: Optional["_dt.datetime"] = None) -> str:
    """給 session_start.py 與 pre hook 的 BLOCK／deny 訊息用：來源 session、類別、原因、時間、
    目前真實水位、兩殼各一行指令（bash/zsh 與 PowerShell）。

    D16（DEF-200-275 第五輪 SA-02）：`measurement`（`context_window.Measurement` 或 None，用
    duck-typing 讀 `.used` 避免此模組反過來 import context_window）／`window`／`source` 三個
    optional 關鍵字參數，由呼叫端（pre hook／session_start）把它們已經量測過的真實水位傳進來——
    本函式只負責印出，不重新量測。三者皆有預設值 None，既有呼叫簽名（不傳這三個新參數）零改動
    即可繼續運作；量不到（measurement 為 None、或 `.used` 為 None、或缺 window）時印「尚無可用
    usage」而非硬湊假數字。

    D17（DEF-200-275 第六輪／DEF-200-283；F-ARCH-01／QA-C1）：`caller_session_id` 是**這次**呼叫
    hook 的 session（由呼叫端從 payload 的 session_id 傳入），用來回答「這個 ESCALATION 是不是我
    這個 session 觸發的」——讀 `state.root["escalation_provenance"]`（`record_escalation()` 寫入，
    D17 新欄位）算出「N 小時前」＋是否同一 session。provenance 缺席（極舊 state／繞過
    record_escalation 手動灌狀態）時老實印「時間未知」「無法確認」，不臆測。`_now` 只供測試固定
    時鐘，非公開契約的一部分（前置底線）。此段與既有 `session=<X>；類別=…` 那行**並存**（新增，非
    取代）——既有測試斷言那行原樣照舊，這裡多印一行讓「是不是我觸發的」有機讀依據可指。首擊
    `measurement=None`（量不到 usage）時本段一樣印出，不依賴 measurement（EscalationRecoveryHintTests
    此前只覆蓋 m 有值的情境）。"""
    history = state.root.get("escalation_history") or []
    last = history[-1] if history and isinstance(history[-1], dict) else {}
    category = classify_escalation(last)
    session_id = last.get("session_id") if isinstance(last, dict) else None
    trigger_reason = (last.get("trigger_reason") if isinstance(last, dict) else None) or _UNRECORDED
    triggered_at = (last.get("triggered_at") if isinstance(last, dict) else None) or _UNRECORDED
    target, fallback = resume_target(state)

    # D17：溯源（escalation_provenance）——與上面沿用舊格式的 `history[-1]` 派生值分開讀，
    # 因為 provenance 是本輪新欄位，缺席時不得讓整段 crash（老 state／chaos_runner 直接灌
    # current="ESCALATION" 而不經 record_escalation 的情形，見同檔上方 chaos_runner 引用）。
    provenance = state.root.get("escalation_provenance")
    provenance = provenance if isinstance(provenance, dict) else {}
    prov_session = provenance.get("session_id") or _PROVENANCE_UNKNOWN
    prov_reason = provenance.get("reason") or trigger_reason
    prov_rule = provenance.get("rule_id") or _PROVENANCE_UNKNOWN
    prov_at = provenance.get("at")
    ago = _hours_ago(prov_at, now=_now)
    at_label = prov_at or _UNRECORDED

    # ARCH-R6-01（DEF-200-275 第六輪複審）：即使寫入面 4 個繞過站點已修好（見 fsm_runtime.py
    # record_dispatch_rejection／exit_trajectory_predicted／exit_learning_commit／
    # exit_autoclaude_delegated），仍加這道讀取面防呆——provenance 可能是「更早、已解除的事件」
    # 留下的舊快照（未來若再出現繞過站點、或 state 遭手動竄改）。比對 provenance.at 與「本次轉入
    # ESCALATION」的時間戳（`_entered_escalation_at`：decision_trace 最後一筆轉入紀錄，量不到退回
    # state 檔 mtime 兜底），早於後者超過容錯窗即判定陳舊：溯源不可信，且不得沿用舊
    # reason／trigger_reason 去餵恢復指令的 --reason。
    prov_at_dt = _parse_iso(prov_at)
    entered_at = _entered_escalation_at(state)
    is_stale = (
        prov_at_dt is not None
        and entered_at is not None
        and (entered_at - prov_at_dt).total_seconds() > _STALE_PROVENANCE_GRACE_SECONDS
    )

    if is_stale:
        # 不得沿用 trigger_reason／prov_reason（皆屬前一次已解除事件）；恢復指令的 --reason
        # 一律換成不帶舊原因的通用措辭。
        auto_reason = (
            "human resume after escalation "
            "(溯源陳舊，未採用舊原因；resume 前請人工核實本次實際觸發原因)"
        )
    else:
        auto_reason = (
            f"human resume after {category} escalation ({trigger_reason[:60]})"
            if trigger_reason != _UNRECORDED else f"human resume after {category} escalation"
        )
    root = Path(sdd_root).resolve()
    posix_cmd = recovery_command(sdd_root=root, python=python, target=target, reason=auto_reason,
                                 shell="posix", exists=exists)
    ps_cmd = recovery_command(sdd_root=root, python=python, target=target, reason=auto_reason,
                              shell="powershell", exists=exists)
    used = getattr(measurement, "used", None) if measurement is not None else None
    if used is not None and window:
        water_line = f"  目前本 session 真實 used={used:,} window={window:,} 來源={source or '未知'}"
    else:
        water_line = "  目前本 session 尚無可用 usage（新 session 首擊或 compact 後）"

    if is_stale:
        entered_label = (
            entered_at.isoformat(timespec="seconds") if entered_at is not None else _UNRECORDED
        )
        provenance_line = (
            f"  溯源不可信：現有溯源屬於較早、已解除的事件（session={prov_session} 於 {at_label}"
            f"（{ago}）因 {prov_reason} 寫入；rule_id={prov_rule}）；"
            f"本次 ESCALATION（轉入於 {entered_label}）未留溯源。"
        )
    else:
        if prov_session == _PROVENANCE_UNKNOWN or not caller_session_id:
            verdict = "無法確認是否為觸發者（來源 session 或本 session 身分未記錄）"
        elif prov_session == caller_session_id:
            verdict = "是觸發者"
        else:
            verdict = "不是觸發者"
        provenance_line = (
            f"  溯源：此 ESCALATION 由 session={prov_session} 於 {at_label}（{ago}）"
            f"因 {prov_reason} 寫入（rule_id={prov_rule}）；"
            f"本 session={caller_session_id or _UNRECORDED}（{verdict}）"
        )

    lines = [
        f"[SDD-FSM][RECOVERY] 此 ESCALATION 來源 session={session_id or _UNRECORDED}；"
        f"類別={category}（{'context budget 誤觸／耗盡' if category == CATEGORY_CONTEXT_BUDGET else '結構性升級'}）；"
        f"原因={trigger_reason}；時間={triggered_at}",
        provenance_line,
        f"  目標={target}" + ("（resume_state 不在合法出口，fallback 為 SPEC_DRAFTING）" if fallback else ""),
        water_line,
        "  人工恢復（R-9.5：需人類在終端執行；依你的殼複製對應那一整行）：",
        f"  bash/zsh   : {posix_cmd}",
        f"  PowerShell : {ps_cmd}",
        "  修好後請自 ~/.zshrc（PowerShell 為 $PROFILE）移除 SDD_HOOKS_DRY_RUN=1（暫時繞過已無必要）。",
    ]
    return "\n".join(lines)
