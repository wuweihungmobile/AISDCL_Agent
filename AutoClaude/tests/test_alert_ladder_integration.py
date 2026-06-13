"""F-B1/F-B2 orchestrator 整合測試（Improving_012 Phase 2 / ADR-AGT-004）。

測試意圖（Rule 9）：
  - flag on 時三階梯必須在 run_steps 主迴圈真實生效（WARNING 緩階、HINT 經
    strategy_hint 注入 _get_correction、F-B2 streak 提前升級），而非只在
    單元層成立——這是 SCG-1 SRD「擴充點實證」的執行期對應。
  - flag off（預設）時 escalation 時序與既有行為一致（凍結驗收「零回歸」）。
"""
from __future__ import annotations

import itertools
from unittest.mock import MagicMock

from autoclaude.execution.playbook_runner import PlaybookRunner
from autoclaude.execution.types import _StepOutput
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.utils.config import AlertLadderConfig, AppConfig


def _make_runner(tmp_path, ladder_enabled: bool, knowledge_base=None) -> PlaybookRunner:
    cfg = AppConfig(
        alert_ladder=AlertLadderConfig(enabled=ladder_enabled),
        checkpoint_dir=str(tmp_path / "checkpoints"),
        log_dir=str(tmp_path / "logs"),
    )
    cfg.notification.enabled = False
    minimax = MagicMock()
    hotkey = MagicMock()
    hotkey.triggered = False
    runner = PlaybookRunner(
        cfg, minimax, hotkey, dry_run=False, knowledge_base=knowledge_base,
    )

    runner._execute_prompt = MagicMock(return_value=_StepOutput(text="executed"))
    _n = itertools.count()
    runner._get_correction = MagicMock(side_effect=lambda *a, **k: (
        f"請修正 foo.py 中的斷言錯誤（第 {next(_n)} 輪嘗試）。"
        "步驟：1. 重新閱讀完整錯誤輸出與 traceback；2. 檢查 compute() 回傳值型別"
        "與測試期望是否一致；3. 改用不同切入點重寫該函式並補上邊界條件處理；"
        "4. 完成後執行 pytest tests/test_foo.py -v 確認全綠。",
        "理由", None, None,
    ))
    runner._verify_correction_applied = MagicMock(return_value=None)
    # 隔離演化鏈（非本測試標的；None → 直接回 PlaybookResult）
    runner._minimax_evolver.propose_evolution_via_ai = MagicMock(return_value=None)
    runner._evolver.propose_evolution = MagicMock(return_value=None)
    return runner


def _playbook(max_retries: int) -> Playbook:
    return Playbook(
        version="1.0",
        project="LadderIT",
        global_invariants=GlobalInvariants(max_retries_per_step=max_retries),
        tasks=[PlaybookTask(step_id="T01", name="task", prompt="do it",
                            max_retries=max_retries)],
    )


def _run(runner, playbook, eval_outputs: list[str], path: str):
    """每次 attempt 依序回傳 eval_outputs 的失敗輸出（耗盡後重複末筆）。"""
    seq = iter(eval_outputs)
    last = eval_outputs[-1]

    def _eval(task, text):
        out = next(seq, last)
        return ("失敗", out, 1)

    runner._evaluate = MagicMock(side_effect=_eval)
    return runner._run_steps(playbook, path, 0, [], True, "auto", 1)


class TestFlagOnStuck:
    def test_fb2_early_escalation_after_warning(self, tmp_path):
        """同 signature 無改善：attempt2 WARNING 緩階 → attempt3 streak=2 提前升級。"""
        runner = _make_runner(tmp_path, ladder_enabled=True)
        result = _run(runner, _playbook(max_retries=6),
                      ["AssertionError: same"] * 7, str(tmp_path / "pb.yaml"))
        assert result.success is False
        assert "F-B2" in result.reason          # 提前升級 reasoning 來自 ladder bypass
        # WARNING 緩階給了 1 次額外修正機會：corrections = attempt0 + attempt1(緩階後)
        assert runner._get_correction.call_count == 2


class TestFlagOnOscillation:
    def test_hint_injected_via_strategy_hint(self, tmp_path):
        """ABAB 振盪（signature 持續改變 → F-B2 不觸發）走滿三階梯，
        HINT 文字必須經 strategy_hint 注入 _get_correction。"""
        runner = _make_runner(tmp_path, ladder_enabled=True)
        outputs = ["TypeError: alpha", "ValueError: beta"] * 4
        result = _run(runner, _playbook(max_retries=8), outputs,
                      str(tmp_path / "pb.yaml"))
        assert result.success is False
        hints = [
            c.kwargs.get("strategy_hint", "")
            for c in runner._get_correction.call_args_list
        ]
        assert any("AlertLadder" in h for h in hints), (
            f"HINT 未經 strategy_hint 注入；實際 hints={hints}"
        )


class TestFlagOffZeroRegression:
    def test_stuck_escalates_immediately_as_before(self, tmp_path):
        """flag off（預設）：is_stuck(2) 即升級，與 F-B 系列導入前時序一致。"""
        runner = _make_runner(tmp_path, ladder_enabled=False)
        result = _run(runner, _playbook(max_retries=6),
                      ["AssertionError: same"] * 7, str(tmp_path / "pb.yaml"))
        assert result.success is False
        assert "特徵碼連續相同" in result.reason   # 既有 convergence reasoning 原樣
        # 無緩階：僅 attempt0 失敗後諮詢 1 次，attempt1 失敗即 escalate
        assert runner._get_correction.call_count == 1

    def test_environment_error_bypasses_even_with_flag_on(self, tmp_path):
        """環境錯誤不入梯（flag on 也直接升級，不浪費重試）。"""
        runner = _make_runner(tmp_path, ladder_enabled=True)
        result = _run(runner, _playbook(max_retries=6),
                      ["FileNotFoundError: /etc/missing"] * 3,
                      str(tmp_path / "pb.yaml"))
        assert result.success is False
        assert "環境錯誤" in result.reason
        assert runner._get_correction.call_count == 0


class TestBoundedness:
    def test_oscillation_correction_count_never_exceeds_max_retries(self, tmp_path):
        """P2-b 有界性：flag on 持續振盪（每輪 signature 變、F-B2 不觸發）下，
        緩階給予額外修正機會但總 _get_correction 呼叫數仍 ≤ max_retries+1，
        證明階梯不突破 max_retries 保底（SRD §1.2「有界性」）。

        Rule 9：若階梯誤增 attempt 預算（如緩階 reset attempt 計數）→ 呼叫數
        將超過 max_retries+1 → 測試失敗。
        """
        max_retries = 8
        runner = _make_runner(tmp_path, ladder_enabled=True)
        # ABAB 振盪：signature 每輪不同 → F-B2 streak 永遠歸零，走滿三階梯
        outputs = ["TypeError: alpha", "ValueError: beta"] * 6
        result = _run(runner, _playbook(max_retries=max_retries), outputs,
                      str(tmp_path / "pb.yaml"))
        assert result.success is False
        # for attempt in range(0, max_retries+1)：每次失敗（除最後一次 escalate）
        # 呼叫一次 _get_correction；上限為 max_retries+1
        assert runner._get_correction.call_count <= max_retries + 1


class TestFlagOffKbInvariant:
    def test_flag_off_strategy_failure_does_not_change_escalation(self, tmp_path):
        """P2-c：flag off 時 record_strategy_failure（常開副作用）不改變後續
        escalation 時序——即 KB strategy_failure 回寫不污染 flag-off 控制流。

        以真實 FailureKnowledgeBase 預先 seed 一個 successful_strategy，跑 flag off
        stuck 場景：F-B2 常開會回寫 strategy_failure（清除 successful_strategy），
        但 flag off 下 ladder 不 intercept → escalate 時序與導入前一致（is_stuck(2)
        即升級、僅諮詢 1 次）。Rule 9：若 strategy_failure 回寫意外改變 flag-off
        策略選擇路徑 → 呼叫數或 reason 偏離 → 失敗。
        """
        from autoclaude.utils.knowledge_base import FailureKnowledgeBase
        kb = FailureKnowledgeBase(str(tmp_path / "kb.jsonl"))
        # seed：assertion 類曾有成功策略 REWRITE（constructor injection，W1a DoD）
        kb.record_success("assertion:AssertionError: same", "REWRITE", "T01",
                          error_class="assertion")
        runner = _make_runner(tmp_path, ladder_enabled=False, knowledge_base=kb)

        result = _run(runner, _playbook(max_retries=6),
                      ["AssertionError: same"] * 7, str(tmp_path / "pb.yaml"))
        assert result.success is False
        # flag off 時序不變：is_stuck(2) 即升級，僅 attempt0 後諮詢 1 次
        assert "特徵碼連續相同" in result.reason
        assert runner._get_correction.call_count == 1
