"""ESCALATION 的人工恢復提示——印出**一行可直接複製執行的指令**（DEF-200-275 第四輪 D6／C10）。

WHY：此前 SessionStart 的 BLOCK 訊息只說「必須人工介入並執行 Session 恢復流程」，恢復流程住在
`AISDLC_SDD_INIT.md` 的 yaml 敘述裡，沒有可執行的 CLI；context budget 誤觸的 ESCALATION 又是
專案級、跨 session 黏著（根因 C），使用者開新視窗照樣被擋、卻拿不到一條能跑的指令。

R-9.5 只規範「進入 ESCALATION 後**禁止自動**恢復」；本模組產出的是給**人**在終端執行的指令，
走既有合法邊 `ESCALATION→RESUME_VERIFICATION→<resume_state>`，零新增狀態／邊、不碰 TLA。
`-m tools.fsm_runtime.fsm_runtime` 是唯一可跑形態（直跑檔案會因相對 import 而 ImportError）。
"""
from __future__ import annotations

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
                  source: Optional[str] = None) -> str:
    """給 session_start.py 與 pre hook 的 BLOCK／deny 訊息用：來源 session、類別、原因、時間、
    目前真實水位、兩殼各一行指令（bash/zsh 與 PowerShell）。

    D16（DEF-200-275 第五輪 SA-02）：`measurement`（`context_window.Measurement` 或 None，用
    duck-typing 讀 `.used` 避免此模組反過來 import context_window）／`window`／`source` 三個
    optional 關鍵字參數，由呼叫端（pre hook／session_start）把它們已經量測過的真實水位傳進來——
    本函式只負責印出，不重新量測。三者皆有預設值 None，既有呼叫簽名（不傳這三個新參數）零改動
    即可繼續運作；量不到（measurement 為 None、或 `.used` 為 None、或缺 window）時印「尚無可用
    usage」而非硬湊假數字。"""
    history = state.root.get("escalation_history") or []
    last = history[-1] if history and isinstance(history[-1], dict) else {}
    category = classify_escalation(last)
    session_id = last.get("session_id") if isinstance(last, dict) else None
    trigger_reason = (last.get("trigger_reason") if isinstance(last, dict) else None) or _UNRECORDED
    triggered_at = (last.get("triggered_at") if isinstance(last, dict) else None) or _UNRECORDED
    target, fallback = resume_target(state)
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
    lines = [
        f"[SDD-FSM][RECOVERY] 此 ESCALATION 來源 session={session_id or _UNRECORDED}；"
        f"類別={category}（{'context budget 誤觸／耗盡' if category == CATEGORY_CONTEXT_BUDGET else '結構性升級'}）；"
        f"原因={trigger_reason}；時間={triggered_at}",
        f"  目標={target}" + ("（resume_state 不在合法出口，fallback 為 SPEC_DRAFTING）" if fallback else ""),
        water_line,
        "  人工恢復（R-9.5：需人類在終端執行；依你的殼複製對應那一整行）：",
        f"  bash/zsh   : {posix_cmd}",
        f"  PowerShell : {ps_cmd}",
        "  修好後請自 ~/.zshrc（PowerShell 為 $PROFILE）移除 SDD_HOOKS_DRY_RUN=1（暫時繞過已無必要）。",
    ]
    return "\n".join(lines)
