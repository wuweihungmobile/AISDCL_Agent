"""Phase M M-M2 / ACT-099 — Capability Trajectory Monitor（自我演化進步性監測）.

對應藍圖：SDD_improving_Automation_13.md §1.3 / §3.1 ACT-099 / Rule 9.25.4 / 9.25.7。

`META_FSM`（Phase L）證了「不抖動」（ChurnBounded），卻**沒證「真進步」**——一個
`ChurnBounded` 成立、能力卻原地踏步的系統照樣失敗（「穩定地平庸」）。本模組是
`ChurnBounded` 的**對偶**：跨 session 測「淨能力軌跡」，偵測「有界但停滯」的高原。

淨能力 = 加權（OQS 品質 × (1 - escalation 率) × scaffold ROI）。churn 不直接計入能力分數，
而是高原判據（有 churn 卻能力平坦 = 白忙）。評分強度凍結於 `TRAJECTORY_PROFILE_VERSION`，
調權重須 bump（Rule 9.25.4，比照 SCORER_VERSION，防評分器自我放水）。

advisory（Rule 9.25.4 / 9.25.7）：plateau/regression 訊號**絕不自動觸發典範轉移或任何
spec/規則/鷹架變更**，只導人類舵手（提示「引導人類提供缺失工具、維持掌舵者高度」）。
純離線、可重現、零 LLM。
"""
from __future__ import annotations

import datetime as _dt
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .state_loader import REPO_ROOT

TRAJECTORY_REPORT_DIR = REPO_ROOT / "build" / "reports" / "trajectory"

# === 凍結評分強度（Rule 9.25.4：調整須 bump version）===
TRAJECTORY_PROFILE_VERSION = "v1.0"
_WEIGHTS = {
    "oqs": 0.50,          # 輸出品質（越高越好）
    "low_escalation": 0.30,  # (1 - escalation 率)（escalation 越少越好）
    "scaffold_roi": 0.20,    # 鷹架 ROI 平均（越高越好）
}

_DEFAULT_WINDOW = 3
_WINDOW_CLAMP = (2, 10)
_SLOPE_EPSILON = 0.02   # |斜率| ≤ epsilon 視為平坦


def trajectory_window() -> int:
    """讀 SDD_TRAJECTORY_WINDOW（env 可調），clamp[2,10]，預設 3。"""
    raw = os.environ.get("SDD_TRAJECTORY_WINDOW")
    if not raw:
        return _DEFAULT_WINDOW
    try:
        val = int(raw)
    except ValueError:
        return _DEFAULT_WINDOW
    lo, hi = _WINDOW_CLAMP
    return max(lo, min(hi, val))


@dataclass
class CapabilitySample:
    """單一 session 的能力觀測（由 caller 從既有落盤訊號彙整）。"""
    session_id: str
    oqs_avg: float = 0.0          # 0~1
    escalation_rate: float = 0.0  # 0~1
    scaffold_roi_avg: float = 0.0  # 0~1
    churn: int = 0                # 該期 meta-loop churn 次數（>0 = 仍在 add↔retire）

    def net_capability(self) -> float:
        v = (_WEIGHTS["oqs"] * _clamp01(self.oqs_avg)
             + _WEIGHTS["low_escalation"] * (1.0 - _clamp01(self.escalation_rate))
             + _WEIGHTS["scaffold_roi"] * _clamp01(self.scaffold_roi_avg))
        return round(v, 4)


@dataclass
class TrajectoryReport:
    verdict: str               # "RISING" | "PLATEAU" | "REGRESSION" | "CONVERGED" | "INSUFFICIENT"
    slope: float
    window: int
    net_series: List[float] = field(default_factory=list)
    churn_in_window: int = 0
    profile_version: str = TRAJECTORY_PROFILE_VERSION
    advisory: str = ""


def _clamp01(x: float) -> float:
    try:
        return max(0.0, min(1.0, float(x)))
    except (TypeError, ValueError):
        return 0.0


def classify_trajectory(samples: List[CapabilitySample], *,
                        window: Optional[int] = None) -> TrajectoryReport:
    """判定自我演化是否真在進步（RISING / PLATEAU / REGRESSION / CONVERGED）。

    - RISING：斜率 > epsilon（淨能力上升，健康）
    - REGRESSION：斜率 < -epsilon（淨能力下降，高優先告警）
    - PLATEAU：|斜率| ≤ epsilon **且** 窗內仍有 churn（有界但停滯＝白忙，引導人類）
    - CONVERGED：|斜率| ≤ epsilon **且** 窗內零 churn（已乾淨收斂，健康）
    - INSUFFICIENT：樣本不足
    """
    w = window or trajectory_window()
    if len(samples) < w:
        return TrajectoryReport(verdict="INSUFFICIENT", slope=0.0, window=w,
                                net_series=[s.net_capability() for s in samples],
                                advisory="樣本不足，無法判定軌跡（保守不告警）。")
    win = samples[-w:]
    series = [s.net_capability() for s in win]
    slope = round((series[-1] - series[0]) / (w - 1), 4)
    churn_in_window = sum(int(s.churn) for s in win)

    if slope > _SLOPE_EPSILON:
        verdict, advisory = "RISING", "淨能力上升中，自我演化健康（純記錄）。"
    elif slope < -_SLOPE_EPSILON:
        verdict, advisory = "REGRESSION", (
            "⚠️ 淨能力下降——自我演化退步。請人類舵手檢視近期變更（高優先；不自動回滾）。")
    elif churn_in_window > 0:
        verdict, advisory = "PLATEAU", (
            "⚠️ 高原：ChurnBounded 成立但淨能力平坦——有界卻停滯（白忙）。"
            "請人類舵手注入新工具/典範或移除天花板鷹架（advisory，不自動處置）。")
    else:
        verdict, advisory = "CONVERGED", "淨能力平坦且零 churn——已乾淨收斂（健康）。"

    return TrajectoryReport(verdict=verdict, slope=slope, window=w, net_series=series,
                            churn_in_window=churn_in_window, advisory=advisory)


def trajectory_markdown(report: TrajectoryReport) -> str:
    """產出 markdown 軌跡報告（advisory，餵 steersman；不阻塞、不自動處置）。"""
    lines = [
        "## 📈 自我演化進步性軌跡（Capability Trajectory — advisory，Rule 9.25.4/9.25.7）",
        "",
        f"- profile_version：`{report.profile_version}`（凍結；調權重須 bump）",
        f"- 判定：**{report.verdict}**（斜率 {report.slope}，窗 {report.window}，"
        f"窗內 churn {report.churn_in_window}）",
        f"- 淨能力序列：{report.net_series}",
        "",
        f"> {report.advisory}",
        "",
        "> advisory：plateau/regression 一律導人類舵手，**絕不自動 paradigm-shift / 退役 / 改排序**（Rule 9.25.7）。",
    ]
    return "\n".join(lines) + "\n"


def write_report(report: TrajectoryReport, *, out_dir: Optional[Path] = None,
                 today: Optional[str] = None) -> Path:
    """落盤 build/reports/trajectory/TRAJECTORY-{date}.md（§2.1 承諾產物）。"""
    target_dir = out_dir or TRAJECTORY_REPORT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    date = today or _dt.datetime.now(_dt.timezone.utc).date().isoformat()
    path = target_dir / f"TRAJECTORY-{date}.md"
    path.write_text(trajectory_markdown(report), encoding="utf-8")
    return path
