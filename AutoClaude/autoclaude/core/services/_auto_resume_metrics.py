"""AutoResumeMetrics — SD_Improving_05 W5 批3-C / M-9。

獨立於 auto_resume.py 以維持 ≤ 250 LOC 預算精神（單一檔案職責原則）。

W5 三方審查修復（Critical / Major / Minor 全部）：
  - C-A1+SD1: `_make_stub_playbook()` 每次新建，避免跨呼叫污染
  - C-A2: except 收斂為 (OSError, ValueError, RuntimeError)，HookContractViolation 必須冒泡
  - C-SD3: LOC 口徑與 wc -l 對齊（≤ 250 budget）
  - M-A2: bus=None 改 logger.error（記錄 wiring 異常）
  - M-SA1: 補 failed_emits 計數；wake_kinds 保留 deque(maxlen=200) 防 memory leak
  - M-SA2: kind 改 Literal + 未知 kind raise ValueError
  - M-SD5: kind/scheduled_at/wait_secs 改 keyword-only 避免誤傳
  - M-A3: 演化 wait_secs 由 caller 用 seconds_until_resume(result.scheduled_resume_at) 計算
  - Minor-SD3: datetime.now(timezone.utc) 統一時區
"""
from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal, Optional

from ...models.playbook import GlobalInvariants, Playbook
from ..hookspec import HookContext, HookContractViolation, KernelPhase

if TYPE_CHECKING:
    from ..event_bus import EventBus

logger = logging.getLogger("autoclaude.core.services.auto_resume_metrics")

# C-A1+SD1: ON_AUTO_RESUME_WAKE 為 service-level event；ctx.playbook 用「每次新建」
# stub 占位以避免跨呼叫污染（Pydantic v2 Playbook 預設非 frozen，模組級單例
# 會被 plugin `ctx.playbook.tasks.append(...)` 永久污染）。
def _make_stub_playbook() -> Playbook:
    return Playbook(
        version="1.0", project="__auto_resume_wake__",
        global_invariants=GlobalInvariants(), tasks=[],
    )


# M-SA2: 限縮 kind 為 Literal，靜態檢查可捕捉拼字錯誤
# SD_08 W4 / T4-F12：擴展 wake_kinds 至 5 種，覆蓋 esc_f12 + manual 兩個遺漏來源
#   - "halt"             : Token HALT 後的自動恢復（既有）
#   - "evolution"        : Playbook 自演化重啟（既有）
#   - "checkpoint_resume": 從 scheduled_resume_at 喚醒（既有）
#   - "esc_f12"          : 使用者 ESC+F12 中斷後恢復（W4 新增；對應 HotkeyPlugin）
#   - "manual"           : CLI / API 顯式觸發恢復（W4 新增；對應 dry-run / 測試）
WakeKind = Literal["halt", "evolution", "checkpoint_resume", "esc_f12", "manual"]
_VALID_KINDS = frozenset({
    "halt", "evolution", "checkpoint_resume", "esc_f12", "manual",
})
_WAKE_KINDS_MAXLEN = 200  # M-SA1: 防 long-running session memory leak


@dataclass
class AutoResumeMetrics:
    """AutoResumeService 執行 metrics（observability / monitoring 用）。

    `wake_kinds` 區分喚醒來源（bounded deque 防 memory leak）：
      - "halt": Token HALT 後的自動恢復
      - "evolution": Playbook 自演化重啟
      - "checkpoint_resume": 從 scheduled_resume_at 喚醒
      - "esc_f12": 使用者 ESC+F12 中斷後恢復（SD_08 W4 新增）
      - "manual": CLI / API 顯式觸發恢復（SD_08 W4 新增）
    """
    total_wakes: int = 0
    halt_resumes: int = 0
    evolution_restarts: int = 0
    checkpoint_resumes: int = 0
    # SD_08 W4 / T4-F12：新增 2 種 wake 計數
    esc_f12_resumes: int = 0
    manual_resumes: int = 0
    failed_emits: int = 0  # M-SA1: emit 失敗計數（observability）
    total_wait_seconds: float = 0.0
    last_wake_at: Optional[str] = None
    last_scheduled_resume_at: Optional[str] = None
    wake_kinds: deque = field(
        default_factory=lambda: deque(maxlen=_WAKE_KINDS_MAXLEN),
    )

    def snapshot(self) -> dict:
        """淺拷貝 metrics 供測試 / 序列化使用。"""
        return {
            "total_wakes": self.total_wakes,
            "halt_resumes": self.halt_resumes,
            "evolution_restarts": self.evolution_restarts,
            "checkpoint_resumes": self.checkpoint_resumes,
            # SD_08 W4 / T4-F12
            "esc_f12_resumes": self.esc_f12_resumes,
            "manual_resumes": self.manual_resumes,
            "failed_emits": self.failed_emits,
            "total_wait_seconds": self.total_wait_seconds,
            "last_wake_at": self.last_wake_at,
            "last_scheduled_resume_at": self.last_scheduled_resume_at,
            "wake_kinds": list(self.wake_kinds),
        }


def record_wake_and_emit(
    metrics: AutoResumeMetrics,
    bus: Optional["EventBus"],
    *,
    kind: WakeKind,
    scheduled_at: Optional[str],
    wait_secs: float,
) -> None:
    """每次喚醒記錄 metrics + emit ON_AUTO_RESUME_WAKE。

    參數（keyword-only 強制）：
      - kind: Literal["halt", "evolution", "checkpoint_resume"]，違反 raise ValueError
      - scheduled_at: ISO 8601 timestamp
      - wait_secs: 等待秒數（負值會被夾到 0.0）

    契約：
      - PHASE_RESULT_CONTRACT 允許 ScheduleResumeResult；無 plugin 訂閱時為 no-op
      - bus=None 時 logger.error 記錄 wiring 異常但仍累計 metrics（供測試 FakeKernel）
      - HookContractViolation 必須冒泡（W0 fail-fast 契約），其他預期例外降為 warning
    """
    if kind not in _VALID_KINDS:
        raise ValueError(
            f"record_wake_and_emit: 不支援的 kind={kind!r}，"
            f"必須是 {sorted(_VALID_KINDS)}"
        )

    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    metrics.total_wakes += 1
    metrics.total_wait_seconds += max(0.0, wait_secs)
    metrics.last_wake_at = now_iso
    metrics.last_scheduled_resume_at = scheduled_at
    metrics.wake_kinds.append(kind)
    if kind == "halt":
        metrics.halt_resumes += 1
    elif kind == "evolution":
        metrics.evolution_restarts += 1
    elif kind == "checkpoint_resume":
        metrics.checkpoint_resumes += 1
    # SD_08 W4 / T4-F12：新增 wake_kinds
    elif kind == "esc_f12":
        metrics.esc_f12_resumes += 1
    elif kind == "manual":
        metrics.manual_resumes += 1

    if bus is None:
        logger.error(
            "record_wake_and_emit | bus=None；ON_AUTO_RESUME_WAKE 無法 emit "
            "（可能 wiring 異常或測試 FakeKernel）"
        )
        return
    try:
        bus.emit(HookContext(
            phase=KernelPhase.ON_AUTO_RESUME_WAKE,
            playbook=_make_stub_playbook(),
            payload={
                "kind": kind,
                "wait_seconds": max(0.0, wait_secs),
                "scheduled_at": scheduled_at,
                "wake_at": now_iso,
                "metrics_snapshot": metrics.snapshot(),
            },
        ))
    except HookContractViolation:
        # W0 fail-fast 契約：型別違規必須冒泡，不可被 metrics 路徑吞噬
        metrics.failed_emits += 1
        raise
    except (OSError, ValueError, RuntimeError) as exc:
        # 預期可恢復例外降為 warning，繼續主流程
        metrics.failed_emits += 1
        logger.warning(
            "record_wake_and_emit | ON_AUTO_RESUME_WAKE emit 失敗"
            "（以 warning 紀錄並繼續主流程）: %s", exc,
        )
