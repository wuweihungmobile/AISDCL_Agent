"""tests/integration/test_kernel_resume_multi_halt.py — W2-T10 邊界 1 整合測試。

驗證 resumed playbook 中途再次 halt → 再次 resume 的多層 rescue 場景：
  - AutoResumeService 在每輪迴圈呼叫 _resolve_start 從 checkpoint 讀 start_idx
  - Kernel.run(playbook, start_idx=N) 從正確的步驟繼續，不會倒回已完成步驟
  - 多次 halt 後最終仍能執行完成

使用 InMemoryStateRepository 模擬持久化，stateful mock kernel 模擬「執行→halt→
再執行→halt→成功」的時序。
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from autoclaude.core.kernel_state import KernelResult
from autoclaude.core.services.auto_resume import AutoResumeService
from autoclaude.infra.repositories.in_memory_state_repository import (
    InMemoryStateRepository,
)
from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint
from autoclaude.utils.config import AppConfig

FIXTURES_DIR = Path(__file__).parent.parent / "equivalence" / "fixtures"
PLAYBOOK_PATH = str(FIXTURES_DIR / "01_simple_2_step.yaml")


def _playbook_id(cfg: AppConfig) -> str:
    from autoclaude.infra.repositories.factory import canonical_playbook_id
    return canonical_playbook_id(PLAYBOOK_PATH, mode=cfg.storage.mode)


class _MultiHaltKernel:
    """Stateful mock：第 1 次回傳 halted（step_idx=1），第 2 次再 halt（step_idx=2），
    第 3 次回傳 success。每次 halt 都會將 checkpoint 寫入 repo，模擬真實
    CheckpointPlugin 行為。
    """

    def __init__(self, repo: InMemoryStateRepository, playbook_id: str, schedule: list[int]):
        """schedule: 每次 kernel.run 應回傳的 step_idx 進度；最後一次寫 success。"""
        self._repo = repo
        self._pb_id = playbook_id
        self._schedule = schedule
        self._call_count = 0
        self.received_start_indices: list[int] = []

    def run(self, playbook, start_idx: int = 0) -> KernelResult:
        self.received_start_indices.append(start_idx)
        self._call_count += 1
        if self._call_count <= len(self._schedule):
            # 中途 halt：模擬 CheckpointPlugin 寫入 checkpoint
            new_step_idx = self._schedule[self._call_count - 1]
            self._repo.save_checkpoint(
                self._pb_id,
                PlaybookCheckpoint(
                    playbook_path=PLAYBOOK_PATH,
                    step_idx=new_step_idx,
                    step_id=f"T{new_step_idx + 1:02d}",
                    total_steps=2,
                    completed_step_log=[
                        f"[T{i + 1:02d}] done" for i in range(new_step_idx)
                    ],
                    completed_step_ids=[f"T{i + 1:02d}" for i in range(new_step_idx)],
                ),
            )
            return KernelResult(
                success=False, completed_steps=new_step_idx, total_steps=2,
                halted=True, reason="halted",
            )
        # 最後一輪：完整成功
        return KernelResult(
            success=True, completed_steps=2, total_steps=2,
            completed_step_ids=["T01", "T02"], reason="success",
        )


class TestKernelResumeMultiHalt:
    """W2-T10 邊界 1：resumed playbook 中途再次 halt → 再次 resume。"""

    def test_resumed_playbook_can_halt_again_and_resume(self):
        """模擬：第 1 輪 halt at step_idx=1 → 第 2 輪從 1 開始再 halt at step_idx=2
        → 第 3 輪從 2 開始完成。
        """
        cfg = AppConfig()
        cfg.token_guard.auto_resume = True
        cfg.token_guard.max_auto_resumes = 5
        repo = InMemoryStateRepository()
        kernel = _MultiHaltKernel(repo, _playbook_id(cfg), schedule=[1, 2])
        svc = AutoResumeService(kernel, cfg, state_repository=repo)

        with patch("autoclaude.core.services.auto_resume.time.sleep"):
            result = svc.run(PLAYBOOK_PATH, fresh=False)

        assert result.success is True
        assert result.completed_step_ids == ["T01", "T02"]
        # 三輪呼叫；start_idx 依序為 0 → 1 → 2
        assert kernel.received_start_indices == [0, 1, 2]

    def test_multi_halt_advances_step_idx_correctly(self):
        """確認多次 halt 不會倒回已完成步驟（start_idx 嚴格單調不減）。"""
        cfg = AppConfig()
        cfg.token_guard.auto_resume = True
        cfg.token_guard.max_auto_resumes = 5
        repo = InMemoryStateRepository()
        # schedule = [1, 1, 2] → 第 1 / 2 輪都 halt at step_idx=1（模擬同步驟反覆 halt），
        # 第 3 輪 halt at step_idx=2，第 4 輪 success
        kernel = _MultiHaltKernel(repo, _playbook_id(cfg), schedule=[1, 1, 2])
        svc = AutoResumeService(kernel, cfg, state_repository=repo)

        with patch("autoclaude.core.services.auto_resume.time.sleep"):
            result = svc.run(PLAYBOOK_PATH, fresh=False)

        assert result.success is True
        # 4 輪：第 1 輪從 0，後續從 checkpoint 讀
        observed = kernel.received_start_indices
        assert observed == [0, 1, 1, 2]
        # 嚴格單調不減
        for i in range(1, len(observed)):
            assert observed[i] >= observed[i - 1], (
                f"start_idx 倒退：{observed}"
            )
