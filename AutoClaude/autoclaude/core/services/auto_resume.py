"""AutoResumeService — Layer 2 Coordinator（SD_03 §2.3 W3）。

外層自動恢復迴圈，從 _runner_impl.run():136~250 搬移而來。

職責：
  - 載入 Playbook（from path）
  - 呼叫 PlaybookKernel.run(playbook, start_idx)
  - 處理 evolution restart（切換至演化版 Playbook）
  - 處理 Token HALT → 等待排程時間後自動恢復（auto_resume 迴圈）
  - W2-T9（SD_04）：從 checkpoint 解析 start_idx（_resolve_start 實裝）

設計原則：
  - 不持有步驟級業務邏輯（全在 Kernel + Plugin）
  - 行數 ≤ 250（行數預算 CI 強制）
  - 與 PlaybookKernel 解耦：僅透過 run() 介面通訊
  - core/ 不可 import infra/：state_repository 透過建構式注入；
    canonical_playbook_id 在使用點 lazy import，避免破壞分層
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import yaml

from ...models.playbook import Playbook
from ..kernel_state import KernelResult
from ._auto_resume_metrics import AutoResumeMetrics, record_wake_and_emit

if TYPE_CHECKING:
    from ...utils.config import AppConfig
    from ..kernel import PlaybookKernel

logger = logging.getLogger("autoclaude.core.services.auto_resume")

# SD_05 W5 批3-C / M-9：對外 re-export AutoResumeMetrics 維持向後相容
__all__ = ["AutoResumeService", "AutoResumeMetrics", "load_playbook", "seconds_until_resume"]


class AutoResumeService:
    """外層自動恢復協調器（Layer 2，Kernel 之上）。"""

    def __init__(
        self,
        kernel: "PlaybookKernel",
        config: "AppConfig",
        *,
        state_repository: Optional[Any] = None,
    ):
        """初始化 AutoResumeService。

        Args:
            kernel: PlaybookKernel 實例
            config: AppConfig
            state_repository: 可選的 IStateRepository 實例（W2-T9 新增）；
                              未提供時 _resolve_start 永遠回 (0, [], False, None)
                              以維持向後相容（舊測試 / dry-run）
        """
        self._kernel = kernel
        self._cfg = config
        self._state_repo = state_repository
        # SD_05 W5 批3-C / M-9：metrics observability
        self._metrics = AutoResumeMetrics()

    @property
    def metrics(self) -> dict:
        """供測試 / monitoring 取得 metrics snapshot（dict，防外部污染）。

        W5 三方審查 Major-A1：原本回 _metrics 物件參照導致外部可寫入，
        改回 snapshot() 淺拷貝以強制封裝。
        """
        return self._metrics.snapshot()

    @property
    def _metrics_object(self) -> AutoResumeMetrics:
        """internal helper：取得 mutable AutoResumeMetrics 物件（供測試斷言內部狀態）。"""
        return self._metrics

    def _emit_auto_resume_wake(
        self,
        scheduled_at: Optional[str],
        kind: str,
        wait_secs: float,
    ) -> None:
        """SD_05 W5 批3-C / M-9：委派至 _auto_resume_metrics.record_wake_and_emit。

        kernel 無 bus 屬性時（如測試用 _FakeKernel）跳過 EventBus emit，
        仍記錄 metrics（observability 不應受測試 fake 影響）。
        """
        bus = getattr(self._kernel, "bus", None)
        record_wake_and_emit(
            self._metrics, bus,
            kind=kind, scheduled_at=scheduled_at, wait_secs=wait_secs,
        )

    @property
    def kernel(self) -> "PlaybookKernel":
        """供 PlaybookRunner M1 shim 存取底層 Kernel。"""
        return self._kernel

    def _resolve_start(
        self, playbook_path: str, fresh: bool
    ) -> tuple[int, list[str], bool, Optional[str]]:
        """從 checkpoint 解析下次執行起點。

        Args:
            playbook_path: Playbook YAML 路徑
            fresh: True = 忽略 checkpoint 從步驟 0 開始

        Returns:
            (start_idx, step_log, has_checkpoint, scheduled_resume_at)

        策略：
          - fresh=True → (0, [], False, None)
          - state_repository=None → (0, [], False, None)（向後相容）
          - checkpoint 不存在 → (0, [], False, None)
          - checkpoint 存在 → (ck.step_idx, ck.completed_step_log, True,
                              ck.scheduled_resume_at)
        """
        if fresh:
            return 0, [], False, None
        if self._state_repo is None:
            return 0, [], False, None

        # lazy import 避免 core/ → infra/ 反向依賴；
        # canonical_playbook_id 為純函式，不引入 infra 重型依賴
        from ...infra.repositories.factory import canonical_playbook_id
        playbook_id = canonical_playbook_id(
            playbook_path, mode=self._cfg.storage.mode
        )
        try:
            ck = self._state_repo.load_checkpoint(playbook_id)
        except (FileNotFoundError, ValueError, OSError) as exc:
            # SD_04 W2 三方審查 Dev-W2-Min-1：將 except Exception 收斂為
            # 具體可預期型別，避免吞噬非預期錯誤（如 KeyboardInterrupt / TypeError）
            logger.warning(
                "AutoResumeService | load_checkpoint 失敗（視為無 checkpoint）: %s", exc
            )
            return 0, [], False, None
        if ck is None:
            return 0, [], False, None
        return (
            ck.step_idx,
            list(ck.completed_step_log),
            True,
            ck.scheduled_resume_at,
        )

    def run(self, playbook_path: str, fresh: bool = False) -> KernelResult:
        """執行含自動恢復的完整 Playbook 生命週期。"""
        _current_path = playbook_path
        _evolution_count = 0
        _max_evolutions = self._cfg.playbook.max_evolutions
        auto_resume_count = 0
        max_resumes = self._cfg.token_guard.max_auto_resumes
        _fresh = fresh

        while True:
            # W2-T9：每輪迴圈重新解析 start_idx（演化重載後 path 變更需重新計算）
            start_idx, _step_log, has_ck, sched = self._resolve_start(
                _current_path, _fresh
            )

            # W2-T10 邊界 3：若 checkpoint 帶有 scheduled_resume_at，
            # 計算剩餘秒數；過期或 ≤ 0 立即執行，未過期則 sleep 後繼續
            if has_ck and sched:
                wait_secs = seconds_until_resume(sched)
                # SD_05 W5 / M-9：checkpoint resume 也記錄一筆 metrics
                self._emit_auto_resume_wake(sched, "checkpoint_resume", wait_secs)
                if wait_secs > 0:
                    logger.info(
                        "AutoResumeService | checkpoint scheduled_resume_at "
                        "等待 %.0fs", wait_secs,
                    )
                    time.sleep(wait_secs)
                else:
                    logger.info(
                        "AutoResumeService | checkpoint scheduled_resume_at 已過期，立即繼續"
                    )

            playbook = load_playbook(_current_path)
            result = self._kernel.run(playbook, start_idx=start_idx)

            # 演化後自動重載演化版 Playbook
            if result.evolved_playbook_path and _evolution_count < _max_evolutions:
                _evolution_count += 1
                logger.info(
                    "AutoResumeService | 自動重載演化版 Playbook #%d: %s",
                    _evolution_count, result.evolved_playbook_path,
                )
                # SD_05 W5 / M-9 / Major-A3：evolution restart metrics
                # wait_secs 由 result.scheduled_resume_at 計算（演化也可能帶恢復時間）；
                # 若無則為 0（立即重啟）
                evo_wait = seconds_until_resume(result.scheduled_resume_at)
                self._emit_auto_resume_wake(
                    result.scheduled_resume_at, "evolution", evo_wait,
                )
                _current_path = result.evolved_playbook_path
                _fresh = result.evolution_fresh_required
                auto_resume_count = 0
                continue

            # Token HALT → 等待排程時間後自動恢復
            if (
                result.halted
                and self._cfg.token_guard.auto_resume
                and auto_resume_count < max_resumes
            ):
                auto_resume_count += 1
                wait_secs = seconds_until_resume(result.scheduled_resume_at)
                logger.info(
                    "AutoResumeService | AUTO_RESUME #%d/%d | 等待 %.0fs 後繼續",
                    auto_resume_count, max_resumes, wait_secs,
                )
                # SD_05 W5 / M-9：halt resume metrics + ON_AUTO_RESUME_WAKE
                self._emit_auto_resume_wake(
                    result.scheduled_resume_at, "halt", wait_secs,
                )
                if wait_secs > 0:
                    time.sleep(wait_secs)
                # halt 後不重設 _fresh；下輪 _resolve_start 會讀新 checkpoint
                continue

            return result


def load_playbook(path: str) -> Playbook:
    """從 YAML 路徑載入 Playbook。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Playbook 不存在: {path}")
    with p.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Playbook(**data)


def seconds_until_resume(scheduled_resume_at: "str | None") -> float:
    """回傳距排程恢復的剩餘秒數；未設定或已過期則回傳 0.0。

    例外處理：
        SD_04 W2 三方審查 Arch-W2-Min-1：將 except 範圍擴大至
        ValueError + TypeError（後者涵蓋外部傳入 list / dict / int 等
        無 fromisoformat 介面的型別），統一回退至 0.0 並 warning。
    """
    if not scheduled_resume_at:
        return 0.0
    try:
        resume_at = datetime.fromisoformat(scheduled_resume_at)
        return max(0.0, (resume_at - datetime.now()).total_seconds())
    except (ValueError, TypeError) as exc:
        logger.warning(
            "seconds_until_resume | 無法解析 scheduled_resume_at=%r: %s",
            scheduled_resume_at, exc,
        )
        return 0.0
