"""AutoResumeService：--fresh 只管第一輪，halt 後的續跑輪必須讀剛存的 checkpoint（DEF-200-511）。

驗證意圖（Rule 9）：`--fresh` 的語意是「這次啟動不採信**啟動前就存在**的 checkpoint」，只對第一輪
有意義。`run()` 在迴圈外 `_fresh = fresh`、迴圈內每輪 `_resolve_start(path, _fresh)`，而 `_fresh`
之後從不重設——於是 `--fresh` ＋ TOKEN_HALT ＋ auto_resume 時，halt 後的續跑輪仍以 fresh=True 解析，
無視剛存的 halt checkpoint，從 step 0 重來：已完成的步驟被重跑；halt 點若固定，會在
max_auto_resumes 內反覆從頭跑。舊 PlaybookRunner 在 `_resolve_start` 之後有 `fresh = False`，
service 移植時漏了；原註解「halt 後不重設 _fresh；下輪 _resolve_start 會讀新 checkpoint」
與程式矛盾。
本檔守三件事：
  ① fresh=True：第一輪仍忽略啟動前就存在的 checkpoint（既有語意），halt 後的續跑輪從**剛存的**
     checkpoint 接——不是 0（沒歸 False），也不是啟動前那份舊的（歸得太早）；
  ② fresh=False 既有行為不變：第一輪讀既有 checkpoint、halt 後讀新的；
  ③ 演化重載那一輪仍照 `evolution_fresh_required` 的值，再下一輪才歸 False。
  （③ 只能用假 kernel 測：生產 Kernel 目前不會產生 evolved_playbook_path，那條分支只有假 kernel
   與舊 runner 結果走得到。）
共用夾具直接取自 DEF-200-510 那支測試檔（同一組真 Kernel＋假 executor＋File repository 場景）。
"""
from __future__ import annotations

import pytest

from autoclaude.core.kernel_state import KernelResult
from autoclaude.core.services.auto_resume import AutoResumeService
from autoclaude.infra.repositories.file_state_repository import FileStateRepository
from tests.core.test_auto_resume_clears_checkpoint_on_success import (
    _cfg,
    _ok,
    _real_kernel,
    _ScriptKernel,
    _seed,
    _TokenScriptExecutor,
    _write_playbook,
)


class TestFreshAppliesToTheFirstRoundOnly:
    def test_fresh_run_that_halts_resumes_from_the_checkpoint_it_just_saved(self, tmp_path):
        """--fresh ＋ HALT ＋ 自動續跑：第一輪無視啟動前的舊 checkpoint、續跑輪接剛存的那份。

        修前：start_idxs=[0, 0]、executed 多出一次 T01（續跑輪無視剛存的 halt checkpoint）。
        """
        cfg = _cfg(auto_resume=True)
        repo = FileStateRepository(str(tmp_path / "ck"))
        playbook = _write_playbook(tmp_path)
        _seed(repo, playbook, cfg, step_idx=2)         # 啟動前就存在的舊 checkpoint（昨天的殘留）
        executor = _TokenScriptExecutor([None, 95.0])  # T01 無訊號；T02 首次嘗試 95% ⇒ halt
        kernel = _real_kernel(executor)

        result = AutoResumeService(kernel, cfg, state_repository=repo).run(playbook, fresh=True)

        assert result.success is True
        assert kernel.start_idxs[0] == 0, "--fresh 第一輪必須忽略啟動前就存在的 checkpoint"
        assert kernel.start_idxs == [0, 1], (
            "halt 後的續跑輪必須從剛存的 halt checkpoint（step_idx=1）接：\n"
            "0＝--fresh 沒有只管第一輪、已完成步驟被重跑；\n"
            "2＝連啟動前的舊 checkpoint 都讀了"
        )
        assert executor.calls == ["T01", "T02", "T02", "T03"], "T01 不得因 halt 被重跑第二次"

    def test_non_fresh_run_reads_the_existing_checkpoint_then_the_one_it_saves(self, tmp_path):
        """fresh=False 既有行為不變：第一輪接啟動前的 checkpoint、halt 後接新存的。"""
        cfg = _cfg(auto_resume=True)
        repo = FileStateRepository(str(tmp_path / "ck"))
        playbook = _write_playbook(tmp_path)
        _seed(repo, playbook, cfg, step_idx=1)         # 啟動前就存在的 checkpoint：第一輪要接它
        executor = _TokenScriptExecutor([None, 95.0])  # 從 T02 起：T02 無訊號；T03 首次 95% ⇒ halt
        kernel = _real_kernel(executor)

        result = AutoResumeService(kernel, cfg, state_repository=repo).run(playbook, fresh=False)

        assert result.success is True
        assert kernel.start_idxs == [1, 2], "第一輪讀既有 checkpoint（1），halt 後讀新存的（2）"
        assert executor.calls == ["T02", "T03", "T03"]

    @pytest.mark.parametrize("fresh_required, expected_start_idxs", [
        (True, [0, 0, 2]),    # 演化版那輪照 fresh 忽略其 checkpoint；其後歸 False 讀新存的
        (False, [0, 1, 2]),   # 演化版那輪讀其 checkpoint；其後讀 halt 新存的
    ], ids=["evolution_fresh_required", "evolution_resumes_from_checkpoint"])
    def test_evolution_round_follows_evolution_fresh_required_and_the_next_round_resets(
        self, tmp_path, fresh_required, expected_start_idxs,
    ):
        cfg = _cfg(auto_resume=True)
        repo = FileStateRepository(str(tmp_path / "ck"))
        original = _write_playbook(tmp_path, "pb.yaml")
        evolved = _write_playbook(tmp_path, "pb.mutated.yaml")

        def save_evolution_resume_point(call_no: int) -> None:
            if call_no == 1:  # 模擬 EvolutionPlugin 為演化版存的「演化後 checkpoint」
                _seed(repo, evolved, cfg, step_idx=1)

        evolved_result = KernelResult(
            success=False, completed_steps=1, total_steps=3, reason="escalated",
            escalated=True, evolved_playbook_path=evolved,
            evolution_fresh_required=fresh_required,
        )
        halted = KernelResult.halted_(
            1, 3, ["[T01] ✓"], ["T01"], halt_step_idx=2, peak_token_pct=93.0)
        kernel = _ScriptKernel(evolved_result, halted, _ok(), on_run=save_evolution_resume_point)

        result = AutoResumeService(kernel, cfg, state_repository=repo).run(original)

        assert result.success is True
        assert kernel.start_idxs == expected_start_idxs, (
            "演化重載那一輪必須照 evolution_fresh_required 的值；其後的 halt 續跑輪一律歸 False、"
            "讀剛存的 checkpoint（fresh 殘留＝這裡會是 0）"
        )
