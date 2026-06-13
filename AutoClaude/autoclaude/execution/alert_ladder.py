"""
AlertLadder — F-B1 漸進式告警階梯（Improving_012 Phase 2，ADR-AGT-004）。

收斂升級信號（ConvergenceReport.recommendation == "escalate"）不再單級跳
ESCALATION，先經 WARNING（記錄）→ HINT（注入本地修正提示）→ ESCALATE 三階梯。
僅於 config.alert_ladder.enabled=True 時由 _impl.py 攔截點啟用；flag off 時
本模組不被呼叫，escalation 控制流與既有行為完全一致。

設計約束（SRD_AGT_Phase2_Closedloop §1）：
  - 階梯不增加 attempt 預算：WARNING/HINT 後回到既有 for-attempt 迴圈，
    max_retries / ErrorBudget 保底不受影響。
  - HINT 為本地文字生成（不呼叫 Brain），經既有 strategy_hint 通道注入。
  - bypass：environment_error（AutoClaude 無法修復）與 F-B2 無改善 streak
    達門檻（提前升級）直接 ESCALATE。
  - 計數持久化：snapshot()/restore() 對接 PlaybookCheckpoint.alert_ladder。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .convergence_monitor import ConvergenceReport

logger = logging.getLogger("autoclaude.execution.alert_ladder")

# 不入梯、直接 ESCALATE 的收斂趨勢（SRD §1.2 bypass 1）
_BYPASS_TRENDS = frozenset({"environment_error"})


def build_from_config(cfg, restore_state: dict | None) -> tuple[AlertLadder, bool]:
    """自 AppConfig 建構 AlertLadder 並恢復 checkpoint 狀態。

    回傳 (ladder, enabled)。防 Mock cfg 誤判：enabled 必須是 bool True 才啟用
    （getattr 對 Mock 回傳 truthy Mock）；threshold 非 int 時回退預設 2。
    """
    ladder_cfg = getattr(cfg, "alert_ladder", None)
    enabled = getattr(ladder_cfg, "enabled", False) is True
    try:
        threshold = int(getattr(ladder_cfg, "no_improve_escalate_threshold", 2))
    except (TypeError, ValueError):
        threshold = 2
    ladder = AlertLadder(threshold_no_improve=threshold)
    ladder.restore(restore_state)
    return ladder, enabled


@dataclass
class LadderDecision:
    """intercept() 回傳值。action ∈ {"warning", "hint", "escalate"}。"""
    action: str
    hint_text: str = ""
    reasoning: str = ""


def _build_hint_text(report: ConvergenceReport) -> str:
    """HINT 階本地提示模板（不呼叫 Brain；「code 能答就 code 答」）。"""
    return (
        "## ⚠️ 收斂告警（AlertLadder HINT 階）\n"
        f"收斂監測連續判定無法收斂（trend={report.trend}）：{report.reasoning}\n"
        "先前的修正方向已證實無效。請徹底改變修法：\n"
        "1. 不要重複先前的修改位置與思路；\n"
        "2. 重新閱讀完整錯誤輸出，質疑先前對根因的假設；\n"
        "3. 若多次修改實作仍同錯，檢查測試檔／環境設定本身是否有誤。"
    )


class AlertLadder:
    """per-step 三階梯狀態機。

    計數結構（snapshot/restore 與 checkpoint 對接）：
      {step_id: {"warning": int, "hint": int, "no_improve_streak": int}}

    no_improve_streak 由 CorrectionVerifier（F-B2）維護，與階梯計數同 dict
    持久化（SRD §2.1）；本類提供讀寫介面，判定邏輯在 correction_verifier.py。
    """

    def __init__(self, threshold_no_improve: int = 2):
        self._threshold = threshold_no_improve
        self._counts: dict[str, dict[str, int]] = {}

    # ── 持久化對接（PlaybookCheckpoint.alert_ladder）──────────────

    def snapshot(self) -> dict:
        """回傳可序列化計數快照（深複製，防呼叫端誤改內部狀態）。"""
        return {sid: dict(c) for sid, c in self._counts.items()}

    def restore(self, state: dict | None) -> None:
        """自 checkpoint 恢復（舊 checkpoint 缺欄位時傳 None/{} 等價空白）。"""
        self._counts = {
            str(sid): {k: int(v) for k, v in c.items()}
            for sid, c in (state or {}).items()
            if isinstance(c, dict)
        }

    # ── F-B2 streak 讀寫介面 ──────────────────────────────────────

    def get_no_improve_streak(self, step_id: str) -> int:
        return self._counts.get(step_id, {}).get("no_improve_streak", 0)

    def set_no_improve_streak(self, step_id: str, value: int) -> None:
        self._counts.setdefault(step_id, {})["no_improve_streak"] = max(0, value)

    # ── 三階梯判定 ────────────────────────────────────────────────

    def intercept(
        self,
        step_id: str,
        report: ConvergenceReport,
        no_improve_streak: int | None = None,
    ) -> LadderDecision:
        """收斂升級信號攔截：依該步驟既往階梯計數回傳 warning/hint/escalate。

        Args:
            step_id: 當前步驟 ID。
            report: ConvergenceMonitor 評估結果（recommendation 應為 "escalate"）。
            no_improve_streak: F-B2 無改善連續次數；None 時讀內部計數。
        """
        streak = (
            no_improve_streak if no_improve_streak is not None
            else self.get_no_improve_streak(step_id)
        )
        # bypass 2（SRD §2.3）：F-B2 無改善達門檻 → 穿透剩餘階梯提前升級
        if streak >= self._threshold:
            return LadderDecision(
                action="escalate",
                reasoning=(
                    f"F-B2: 同 error signature 連續 {streak} 次修正無改善"
                    f"（門檻 {self._threshold}），提前升級。{report.reasoning}"
                ),
            )
        # bypass 1（SRD §1.2）：環境錯誤緩階無意義
        if report.trend in _BYPASS_TRENDS:
            return LadderDecision(action="escalate", reasoning=report.reasoning)

        counts = self._counts.setdefault(step_id, {})
        if counts.get("warning", 0) == 0:
            counts["warning"] = counts.get("warning", 0) + 1
            logger.warning(
                "=== F-B1 AlertLadder | [%s] WARNING 階（1/3）: trend=%s %s ===",
                step_id, report.trend, report.reasoning,
            )
            return LadderDecision(action="warning", reasoning=report.reasoning)
        if counts.get("hint", 0) == 0:
            counts["hint"] = counts.get("hint", 0) + 1
            logger.warning(
                "=== F-B1 AlertLadder | [%s] HINT 階（2/3）: 注入本地修正提示 ===",
                step_id,
            )
            return LadderDecision(
                action="hint",
                hint_text=_build_hint_text(report),
                reasoning=report.reasoning,
            )
        logger.error(
            "=== F-B1 AlertLadder | [%s] ESCALATE 階（3/3）: 階梯耗盡 ===", step_id,
        )
        return LadderDecision(action="escalate", reasoning=report.reasoning)
