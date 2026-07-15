"""W3 DoD：AutoResumeService + PlaybookKernel dry_run 端對端測試（SD_03 W3）。

驗證 AutoResumeService.run(playbook_path) 在 DryRunExecutor 模式下：
  1. 成功執行並回傳 KernelResult（completed_steps 正確）
  2. halt_for_token → 不無限等待（mock time.sleep）
  3. evolution_playbook_path → 切換至演化版並執行
  4. evolution + auto_resume 計數器上限不超過
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml as _yaml

from autoclaude.core.kernel_state import KernelResult
from autoclaude.core.services.auto_resume import (
    AutoResumeService,
    load_playbook,
    seconds_until_resume,
)
from autoclaude.core.wiring import build_kernel
from autoclaude.infra.adapters.dry_run_executor import DryRunExecutor
from autoclaude.infra.adapters.shell_evaluator import ShellEvaluator
from autoclaude.utils.config import AppConfig, PlaybookConfig

FIXTURES_DIR = Path(__file__).parent.parent / "equivalence" / "fixtures"


def _make_executor_from_fixture(fixture_path: str) -> DryRunExecutor:
    """依 fixture YAML 中各 task 的 expected_output_regex 建立 DryRunExecutor。"""
    with open(fixture_path, encoding="utf-8") as f:
        raw = _yaml.safe_load(f)
    step_outputs: dict[str, str] = {}
    for task in raw.get("tasks", []):
        step_id = task.get("step_id", "")
        regex = task.get("expected_output_regex")
        step_outputs[step_id] = DryRunExecutor.keyword_from_regex(regex)
    return DryRunExecutor(step_outputs)


def _make_service(
    fixture_path: str | None = None, cfg: AppConfig | None = None
) -> AutoResumeService:
    cfg = cfg or AppConfig()
    # 測試不應觸發真實桌面通知：NotificationPlugin 訂閱 POST_RUN/ON_AUTO_RESUME_WAKE，
    # notify() 在 Windows 經 plyer 產生背景執行緒（win32 balloon tip），其內部
    # time.sleep(timeout) 與其他測試 `patch(".../time.sleep")` 共享同一個 stdlib
    # time 模組物件（非各自獨立 mock），導致殘留背景執行緒的 sleep 呼叫可能競態
    # 落入「另一個」測試的 mock 視窗內，造成與本測試邏輯無關的 flaky 斷言失敗。
    cfg.notification.enabled = False
    if fixture_path:
        executor = _make_executor_from_fixture(fixture_path)
    else:
        executor = DryRunExecutor()
    evaluator = ShellEvaluator(PlaybookConfig())
    kernel = build_kernel(cfg, executor=executor, evaluator=evaluator)
    return AutoResumeService(kernel, cfg)


class TestAutoResumeServiceDryRun:
    """AutoResumeService dry_run 端對端測試。"""

    def test_simple_2_step_fixture_success(self):
        """01_simple_2_step.yaml 在 Kernel 路徑應成功完成 2 步驟。"""
        fixture_path = str(FIXTURES_DIR / "01_simple_2_step.yaml")
        svc = _make_service(fixture_path)
        result = svc.run(fixture_path)
        assert isinstance(result, KernelResult)
        assert result.success is True
        assert result.completed_steps == 2

    def test_step_log_format_matches_semantic_regex(self):
        """step_log 每行須符合 semantic-level regex（SD_03 §2.4 Stage A）。"""
        import re
        PATTERN = re.compile(r"^\[[\w_-]+\] .+(attempt[ =]\d+|\[FAIL\])")
        fixture_path = str(FIXTURES_DIR / "01_simple_2_step.yaml")
        svc = _make_service(fixture_path)
        result = svc.run(fixture_path)
        for line in result.step_log:
            assert PATTERN.match(line), (
                f"step_log 行不符合 semantic regex: {line!r}"
            )

    def test_completed_step_ids_populated(self):
        """completed_step_ids 應包含所有成功步驟 ID。"""
        fixture_path = str(FIXTURES_DIR / "01_simple_2_step.yaml")
        svc = _make_service(fixture_path)
        result = svc.run(fixture_path)
        assert "T01" in result.completed_step_ids
        assert "T02" in result.completed_step_ids

    def test_halt_triggers_auto_resume(self):
        """KernelResult(halted=True) 觸發 auto_resume，但到達上限後回傳。"""
        cfg = AppConfig()
        cfg.token_guard.auto_resume = True
        cfg.token_guard.max_auto_resumes = 2
        # 避免真實通知背景執行緒污染 time.sleep mock（見上方 _make_service）
        cfg.notification.enabled = False

        # mock kernel: 前 2 次 halted=True，第 3 次 success=True
        call_count = {"n": 0}

        def mock_kernel_run(playbook, start_idx: int = 0):
            call_count["n"] += 1
            if call_count["n"] <= 2:
                return KernelResult(
                    success=False, completed_steps=0, total_steps=2,
                    halted=True, reason="halted",
                )
            return KernelResult(
                success=True, completed_steps=2, total_steps=2,
                reason="success",
            )

        executor = DryRunExecutor()
        evaluator = ShellEvaluator(PlaybookConfig())
        kernel = build_kernel(cfg, executor=executor, evaluator=evaluator)
        kernel.run = mock_kernel_run

        svc = AutoResumeService(kernel, cfg)
        fixture_path = str(FIXTURES_DIR / "01_simple_2_step.yaml")

        with patch("autoclaude.core.services.auto_resume.time.sleep") as mock_sleep:
            result = svc.run(fixture_path)

        # 前 2 次 halt → 2 次 auto_resume → 第 3 次 success
        assert result.success is True
        assert call_count["n"] == 3
        # sleep 被呼叫 2 次（兩次 auto_resume）
        assert mock_sleep.call_count == 0  # scheduled_resume_at=None → 0 秒 → 不 sleep

    def test_auto_resume_stops_at_limit(self):
        """auto_resume 達到 max_resumes 後不再重試，回傳最後一次 halted result。"""
        cfg = AppConfig()
        cfg.token_guard.auto_resume = True
        cfg.token_guard.max_auto_resumes = 2
        # 避免真實通知背景執行緒污染 time.sleep mock（見上方 _make_service）
        cfg.notification.enabled = False

        def always_halt(playbook, start_idx: int = 0):
            return KernelResult(
                success=False, completed_steps=0, total_steps=2,
                halted=True, reason="halted",
            )

        executor = DryRunExecutor()
        evaluator = ShellEvaluator(PlaybookConfig())
        kernel = build_kernel(cfg, executor=executor, evaluator=evaluator)
        kernel.run = always_halt

        svc = AutoResumeService(kernel, cfg)
        fixture_path = str(FIXTURES_DIR / "01_simple_2_step.yaml")

        with patch("autoclaude.core.services.auto_resume.time.sleep"):
            result = svc.run(fixture_path)

        assert result.halted is True
        assert result.success is False

    def test_evolution_path_switch(self, tmp_path):
        """evolved_playbook_path 非空時，下一輪切換至演化版 Playbook。"""
        import shutil
        # 複製 fixture 到 tmp_path 作為「演化版」
        evolved = tmp_path / "evolved.yaml"
        shutil.copy(str(FIXTURES_DIR / "01_simple_2_step.yaml"), str(evolved))

        cfg = AppConfig()
        cfg.playbook.max_evolutions = 1
        # 避免真實通知背景執行緒污染 time.sleep mock（見上方 _make_service）
        cfg.notification.enabled = False

        call_count = {"n": 0}

        def evolving_kernel_run(playbook, start_idx: int = 0):
            call_count["n"] += 1
            if call_count["n"] == 1:
                # 第一次：回傳 evolved_playbook_path
                return KernelResult(
                    success=False, completed_steps=1, total_steps=2,
                    evolved_playbook_path=str(evolved),
                    reason="evolved",
                )
            # 第二次（演化版）：成功
            return KernelResult(
                success=True, completed_steps=2, total_steps=2,
                reason="success",
            )

        executor = DryRunExecutor()
        evaluator = ShellEvaluator(PlaybookConfig())
        kernel = build_kernel(cfg, executor=executor, evaluator=evaluator)
        kernel.run = evolving_kernel_run

        svc = AutoResumeService(kernel, cfg)
        result = svc.run(str(FIXTURES_DIR / "01_simple_2_step.yaml"))

        assert result.success is True
        assert call_count["n"] == 2

    def test_13_fixtures_all_succeed(self):
        """Stage A 語意等價測試：13 個 golden fixture 在 Kernel 路徑下全執行完畢。"""
        golden = [
            "01_simple_2_step.yaml", "02_with_correction.yaml", "03_with_mutation.yaml",
            "04_token_halt_resume.yaml", "05_evolution_inject.yaml", "06_goal_synthesis.yaml",
            "07_goto_step.yaml", "08_skip_to.yaml", "09_conditional.yaml",
            "10_full_e2e_dry_run.yaml", "11_goto_counter_token_halt.yaml",
            "12_evolution_counter_esc_f12.yaml", "13_max_goto_per_step_override.yaml",
        ]
        for name in golden:
            path = str(FIXTURES_DIR / name)
            svc = _make_service(path)
            result = svc.run(path)
            assert isinstance(result, KernelResult), f"{name}: 回傳非 KernelResult"
            assert result.total_steps > 0, f"{name}: total_steps=0"


class TestAutoResumeHelpers:
    """AutoResumeService helpers 單元測試。"""

    def test_load_playbook_raises_for_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_playbook("/nonexistent/path/playbook.yaml")

    def test_seconds_until_resume_none(self):
        assert seconds_until_resume(None) == 0.0

    def test_seconds_until_resume_past(self):
        from datetime import datetime, timedelta
        past = (datetime.now() - timedelta(minutes=5)).isoformat(timespec="seconds")
        assert seconds_until_resume(past) == 0.0

    def test_seconds_until_resume_future(self):
        from datetime import datetime, timedelta
        future = (datetime.now() + timedelta(minutes=10)).isoformat(timespec="seconds")
        secs = seconds_until_resume(future)
        assert secs > 500  # > 8.3 min

    def test_seconds_until_resume_invalid(self):
        assert seconds_until_resume("not-a-date") == 0.0
