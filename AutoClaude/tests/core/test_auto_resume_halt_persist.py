"""AutoResumeService token HALT checkpoint 持久化測試（improving_78 W-78-1 / DEF-78-001 / RTM-78-3）。

驗證意圖（Rule 9）：DEF-78-001 修復後，Kernel 會以 result.halted + halt_step_idx 表達 token
HALT；但 Kernel 純 DAG 不持有 path，故 halt checkpoint 必須由握 path 的 AutoResumeService 存。
此測試守「halt → checkpoint 落地（step_idx=halt_step_idx）→ resume 解析得到該點」這條 resume 鏈，
否則 halt 後 resume 會從頭跑（start_idx=0），編排形同未接線。
"""
from __future__ import annotations

from pathlib import Path

from autoclaude.core.kernel_state import KernelResult
from autoclaude.core.services.auto_resume import AutoResumeService
from autoclaude.infra.repositories.in_memory_state_repository import (
    InMemoryStateRepository,
)
from autoclaude.utils.config import AppConfig

FIXTURES_DIR = Path(__file__).parent.parent / "equivalence" / "fixtures"
SIMPLE_PB = str(FIXTURES_DIR / "01_simple_2_step.yaml")


class _HaltOnceKernel:
    """回傳 halted result（auto_resume 關閉時 run() 存 checkpoint 後即 return）。"""

    def __init__(self, result: KernelResult):
        self.calls: list[int] = []
        self._result = result

    def run(self, playbook, start_idx: int = 0) -> KernelResult:
        self.calls.append(start_idx)
        return self._result


def _playbook_id_for(path: str, cfg: AppConfig) -> str:
    from autoclaude.infra.repositories.factory import canonical_playbook_id
    return canonical_playbook_id(path, mode=cfg.storage.mode)


def _halted_result() -> KernelResult:
    return KernelResult.halted_(
        completed_steps=1, total_steps=2,
        step_log=["[T01] done ✓ (attempt 1)"],
        completed_step_ids=["T01"],
        halt_step_idx=1, peak_token_pct=93.0,
    )


def _cfg_no_autoresume() -> AppConfig:
    cfg = AppConfig()
    cfg.token_guard.auto_resume = False  # 關閉自動恢復迴圈，僅驗持久化
    return cfg


def test_halt_persists_checkpoint_at_halt_step_idx():
    """token HALT → 存 checkpoint，step_idx=halt_step_idx、peak 正確。"""
    cfg = _cfg_no_autoresume()
    repo = InMemoryStateRepository()
    svc = AutoResumeService(_HaltOnceKernel(_halted_result()), cfg, state_repository=repo)

    result = svc.run(SIMPLE_PB, fresh=True)

    assert result.halted is True
    ck = repo.load_checkpoint(_playbook_id_for(SIMPLE_PB, cfg))
    assert ck is not None
    assert ck.step_idx == 1
    assert ck.step_id == "T02"          # playbook.tasks[1].step_id
    assert ck.peak_token_pct == 93.0
    assert ck.completed_step_ids == ["T01"]


def test_halt_checkpoint_resolves_resume_point():
    """存檔後 _resolve_start（fresh=False）應解析回 halt_step_idx（resume 鏈閉合）。"""
    cfg = _cfg_no_autoresume()
    repo = InMemoryStateRepository()
    svc = AutoResumeService(_HaltOnceKernel(_halted_result()), cfg, state_repository=repo)
    svc.run(SIMPLE_PB, fresh=True)

    start_idx, log, has_ck, _sched = svc._resolve_start(SIMPLE_PB, fresh=False)
    assert has_ck is True
    assert start_idx == 1


def test_halt_no_state_repo_is_noop():
    """state_repository=None（dry-run / 舊測試）→ 不存、不崩，維持向後相容。"""
    cfg = _cfg_no_autoresume()
    svc = AutoResumeService(_HaltOnceKernel(_halted_result()), cfg, state_repository=None)
    result = svc.run(SIMPLE_PB, fresh=True)
    assert result.halted is True  # 無 repo 仍正常回傳 halted result


def test_halt_without_halt_step_idx_does_not_clobber_existing_checkpoint():
    """🔴 防退化（test_kernel_resume_multi_halt 回歸）：halted 但 halt_step_idx is None
    （既有/其他 halt 路徑，checkpoint 已由別處自存）→ 本持久化必須 no-op，
    不可用 step_idx=0 覆蓋既有 checkpoint。"""
    from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint
    cfg = _cfg_no_autoresume()
    repo = InMemoryStateRepository()
    pid = _playbook_id_for(SIMPLE_PB, cfg)
    # 既有 checkpoint（如他路徑寫的 step_idx=1）
    repo.save_checkpoint(pid, PlaybookCheckpoint(
        playbook_path=SIMPLE_PB, step_idx=1, step_id="T02", total_steps=2,
    ))
    # 回傳 halted 但無 halt_step_idx（直接建構，模擬非 token-observer 路徑）
    legacy_halt = KernelResult(
        success=False, completed_steps=1, total_steps=2, halted=True, reason="halted",
    )
    svc = AutoResumeService(_HaltOnceKernel(legacy_halt), cfg, state_repository=repo)
    svc.run(SIMPLE_PB, fresh=True)

    ck = repo.load_checkpoint(pid)
    assert ck.step_idx == 1  # 未被覆蓋為 0
