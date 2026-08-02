"""tests/core/test_auto_resume.py — W2-T9 AutoResumeService._resolve_start 單元測試。

涵蓋情境（SD_04 §4 W2）：
  1. fresh=True 永遠回 (0, [], False, None)
  2. state_repository=None 安全回 (0, [], False, None)
  3. checkpoint 不存在 → (0, [], False, None)
  4. checkpoint 存在 → 正確的 step_idx / log / has_ck=True / sched
  5. scheduled_resume_at 透過 _resolve_start 正確回傳
  6. T10 邊界 3：scheduled_resume_at 已過期 → 立即繼續，不 sleep
  7. T10 邊界 3 補：scheduled_resume_at 未過期 → sleep 被呼叫
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from autoclaude.core.kernel_state import KernelResult
from autoclaude.core.services.auto_resume import AutoResumeService
from autoclaude.infra.repositories.in_memory_state_repository import (
    InMemoryStateRepository,
)
from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint
from autoclaude.utils.config import AppConfig

FIXTURES_DIR = Path(__file__).parent.parent / "equivalence" / "fixtures"
SIMPLE_PB = str(FIXTURES_DIR / "01_simple_2_step.yaml")


class _FakeKernel:
    """記錄 run() 收到的 start_idx，並回傳 success result。"""

    def __init__(self, result: KernelResult | None = None):
        self.calls: list[int] = []
        self._result = result or KernelResult(
            success=True, completed_steps=2, total_steps=2, reason="success",
        )

    def run(self, playbook, start_idx: int = 0) -> KernelResult:
        self.calls.append(start_idx)
        return self._result


def _playbook_id_for(path: str, cfg: AppConfig) -> str:
    from autoclaude.infra.repositories.factory import canonical_playbook_id
    return canonical_playbook_id(path, mode=cfg.storage.mode)


def _make_checkpoint(step_idx: int = 3, scheduled: str | None = None) -> PlaybookCheckpoint:
    return PlaybookCheckpoint(
        playbook_path=SIMPLE_PB,
        step_idx=step_idx,
        step_id=f"T{step_idx + 1:02d}",
        total_steps=2,
        completed_step_log=[f"[T{i + 1:02d}] done" for i in range(step_idx)],
        scheduled_resume_at=scheduled,
    )


class TestResolveStart:
    """_resolve_start 4 種情境覆蓋。"""

    def test_resolve_start_fresh_returns_zero(self):
        """fresh=True 永遠回 (0, [], False, None)，即使 checkpoint 存在。"""
        cfg = AppConfig()
        repo = InMemoryStateRepository()
        # 預先放入 checkpoint，確認 fresh=True 仍會忽略
        repo.save_checkpoint(_playbook_id_for(SIMPLE_PB, cfg), _make_checkpoint(step_idx=5))
        svc = AutoResumeService(_FakeKernel(), cfg, state_repository=repo)

        start_idx, log, has_ck, sched = svc._resolve_start(SIMPLE_PB, fresh=True)
        assert (start_idx, log, has_ck, sched) == (0, [], False, None)

    def test_resolve_start_no_repository_returns_zero(self):
        """未注入 state_repository 時安全回 (0, [], False, None)。"""
        cfg = AppConfig()
        svc = AutoResumeService(_FakeKernel(), cfg, state_repository=None)
        assert svc._resolve_start(SIMPLE_PB, fresh=False) == (0, [], False, None)

    def test_resolve_start_no_checkpoint_returns_zero(self):
        """checkpoint 不存在時回 (0, [], False, None)。"""
        cfg = AppConfig()
        repo = InMemoryStateRepository()
        svc = AutoResumeService(_FakeKernel(), cfg, state_repository=repo)
        assert svc._resolve_start(SIMPLE_PB, fresh=False) == (0, [], False, None)

    def test_resolve_start_with_checkpoint_returns_correct_idx(self):
        """checkpoint step_idx=3 → 回 (3, log, True, None)。"""
        cfg = AppConfig()
        repo = InMemoryStateRepository()
        ck = _make_checkpoint(step_idx=3, scheduled=None)
        repo.save_checkpoint(_playbook_id_for(SIMPLE_PB, cfg), ck)
        svc = AutoResumeService(_FakeKernel(), cfg, state_repository=repo)

        start_idx, log, has_ck, sched = svc._resolve_start(SIMPLE_PB, fresh=False)
        assert start_idx == 3
        assert log == ["[T01] done", "[T02] done", "[T03] done"]
        assert has_ck is True
        assert sched is None

    def test_resolve_start_with_scheduled_resume(self):
        """scheduled_resume_at 設定時應正確回傳。"""
        cfg = AppConfig()
        repo = InMemoryStateRepository()
        future = (datetime.now() + timedelta(minutes=5)).isoformat(timespec="seconds")
        ck = _make_checkpoint(step_idx=2, scheduled=future)
        repo.save_checkpoint(_playbook_id_for(SIMPLE_PB, cfg), ck)
        svc = AutoResumeService(_FakeKernel(), cfg, state_repository=repo)

        start_idx, _log, has_ck, sched = svc._resolve_start(SIMPLE_PB, fresh=False)
        assert start_idx == 2
        assert has_ck is True
        assert sched == future


class TestRunWithScheduledResume:
    """T10 邊界 3：scheduled_resume_at 過期 / 未過期分支。"""

    def test_run_with_expired_resume_does_not_sleep(self):
        """checkpoint scheduled_resume_at 已過期 → 立即執行，time.sleep 不被呼叫。"""
        cfg = AppConfig()
        repo = InMemoryStateRepository()
        past = (datetime.now() - timedelta(minutes=10)).isoformat(timespec="seconds")
        ck = _make_checkpoint(step_idx=1, scheduled=past)
        repo.save_checkpoint(_playbook_id_for(SIMPLE_PB, cfg), ck)
        kernel = _FakeKernel()
        svc = AutoResumeService(kernel, cfg, state_repository=repo)

        with patch("autoclaude.core.services.auto_resume.time.sleep") as mock_sleep:
            result = svc.run(SIMPLE_PB, fresh=False)

        assert result.success is True
        assert mock_sleep.call_count == 0
        assert kernel.calls == [1], "Kernel 應以 start_idx=1 被呼叫一次"

    def test_run_with_future_resume_waits(self):
        """checkpoint scheduled_resume_at 未過期 → time.sleep 被呼叫一次。"""
        cfg = AppConfig()
        repo = InMemoryStateRepository()
        future = (datetime.now() + timedelta(minutes=5)).isoformat(timespec="seconds")
        ck = _make_checkpoint(step_idx=1, scheduled=future)
        repo.save_checkpoint(_playbook_id_for(SIMPLE_PB, cfg), ck)
        kernel = _FakeKernel()
        svc = AutoResumeService(kernel, cfg, state_repository=repo)

        with patch("autoclaude.core.services.auto_resume.time.sleep") as mock_sleep:
            result = svc.run(SIMPLE_PB, fresh=False)

        assert result.success is True
        assert mock_sleep.call_count == 1
        # 至少 sleep 了大半分鐘以上（5 分鐘扣除執行 latency 餘裕）
        assert mock_sleep.call_args[0][0] > 60


class TestCheckpointIdentityGuard:
    """R69（DEF-101-702／R68-01）：checkpoint 撞名時必須 fail-loud 降級，不得靜默續跑。

    WHY：`canonical_playbook_id()` 在 yaml_only／both 模式回 `Path(p).stem`，於是
      ① macOS APFS／Windows NTFS（大小寫不敏感）上 `Foo.yaml` 與 `foo.yaml` 落到**同一個**
         checkpoint 檔；
      ② 平台無關地，`a/pb.yaml` 與 `b/pb.yaml` 也共用同一個 id。
    修前 `_resolve_start` 對載回來的 checkpoint 零校驗，會直接拿別支 playbook 的 step_idx
    當起點續跑——已完成的步驟被跳過、狀態錯亂，而且**全程沒有任何訊號**。

    這裡驗的是「意圖」而非「行為細節」：撞名時 checkpoint 必須被判定為不屬於本次執行，
    降級成從頭跑（安全方向），而不是被信任。
    """

    def test_checkpoint_of_a_different_playbook_is_rejected(self, tmp_path):
        """同 stem、不同目錄 ⇒ 同一個 playbook_id，但 checkpoint 不屬於本次執行。"""
        cfg = AppConfig()
        other = tmp_path / "elsewhere"
        other.mkdir()
        impostor = other / Path(SIMPLE_PB).name
        impostor.write_text(Path(SIMPLE_PB).read_text(encoding="utf-8"), encoding="utf-8")

        repo = InMemoryStateRepository()
        ck = _make_checkpoint(step_idx=5)
        ck.playbook_path = str(impostor)          # checkpoint 是「別支」留下的
        repo.save_checkpoint(_playbook_id_for(SIMPLE_PB, cfg), ck)

        svc = AutoResumeService(_FakeKernel(), cfg, state_repository=repo)
        assert svc._resolve_start(SIMPLE_PB, fresh=False) == (0, [], False, None)

    def test_checkpoint_of_the_same_playbook_still_resumes(self):
        """反向：路徑相符時行為完全不變（本修復不得改動正常續跑語意）。"""
        cfg = AppConfig()
        repo = InMemoryStateRepository()
        repo.save_checkpoint(_playbook_id_for(SIMPLE_PB, cfg), _make_checkpoint(step_idx=3))
        svc = AutoResumeService(_FakeKernel(), cfg, state_repository=repo)
        start_idx, _log, has_ck, _sched = svc._resolve_start(SIMPLE_PB, fresh=False)
        assert (start_idx, has_ck) == (3, True)

    def test_case_only_difference_is_rejected_on_any_platform(self, tmp_path):
        """大小寫僅差一字的兩支 playbook：在**任何**平台都不得互相續跑。

        大小寫不敏感 FS（APFS/NTFS）上兩者本來就是同一個檔，此案模擬的是「checkpoint 記的
        路徑與本次執行的路徑大小寫不同、且指向不同檔案」——在大小寫敏感的 Linux CI 上這是
        兩支不同 playbook，判準必須一致地拒絕。
        """
        cfg = AppConfig()
        upper = tmp_path / "PB_CASE.yaml"
        lower = tmp_path / "pb_case_other.yaml"
        body = Path(SIMPLE_PB).read_text(encoding="utf-8")
        upper.write_text(body, encoding="utf-8")
        lower.write_text(body, encoding="utf-8")

        repo = InMemoryStateRepository()
        ck = _make_checkpoint(step_idx=4)
        ck.playbook_path = str(upper)
        repo.save_checkpoint(_playbook_id_for(str(lower), cfg), ck)
        svc = AutoResumeService(_FakeKernel(), cfg, state_repository=repo)
        assert svc._resolve_start(str(lower), fresh=False) == (0, [], False, None)

    def test_legacy_checkpoint_without_path_is_not_broken(self):
        """向後相容：舊 checkpoint 沒記 playbook_path 時無從判定 ⇒ 放行，不製造回歸。"""
        cfg = AppConfig()
        repo = InMemoryStateRepository()
        ck = _make_checkpoint(step_idx=2)
        ck.playbook_path = ""
        repo.save_checkpoint(_playbook_id_for(SIMPLE_PB, cfg), ck)
        svc = AutoResumeService(_FakeKernel(), cfg, state_repository=repo)
        assert svc._resolve_start(SIMPLE_PB, fresh=False)[0] == 2
