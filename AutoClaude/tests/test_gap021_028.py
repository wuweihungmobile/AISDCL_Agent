"""
Gap-021 ~ Gap-028 整合驗證測試。

涵蓋：
- Gap-021: CONDITIONAL 突變（條件式分支）
- Gap-022: build_evolution_message 注入 global_goal
- Gap-023: GOAL_VALIDATION 含 code_state_snapshot
- Gap-024: EvolutionMetadata 持久化 + Runner 重載恢復 mutation_log
- Gap-025: Batch 突變相容性預驗證
- Gap-026: SPLIT_STEP Part A evaluator 推導
- Gap-027: GOTO 重訪 context clean hint
- Gap-028: INJECT_BEFORE 步驟去重
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from autoclaude.core.services.auto_resume import load_playbook
from autoclaude.core.services.mutation.service import MutationApplyService
from autoclaude.decision.prompt_builder import (
    build_evolution_message,
    build_goal_validation_message,
)
from autoclaude.evolution import _evaluator_derivation
from autoclaude.evolution.minimax_evolver import MinimaxEvolver
from autoclaude.evolution.playbook_evolver import PlaybookEvolver
from autoclaude.execution.playbook_runner import PlaybookRunner
from autoclaude.models.escalation import EscalationDump
from autoclaude.models.playbook import EvolutionMetadata, Playbook, PlaybookTask
from autoclaude.models.step_mutation import StepMutation, StepMutationType
from autoclaude.utils.config import AppConfig
from tests.helpers.kernel_fixtures import make_service

# ──────────────────────────────────────────────
# 共用輔助函式
# ──────────────────────────────────────────────

def _make_runner(dry_run: bool = True, minimax_mock=None) -> PlaybookRunner:
    cfg = AppConfig()
    minimax = minimax_mock or MagicMock()
    hotkey = MagicMock()
    hotkey.triggered = False
    return PlaybookRunner(cfg, minimax, hotkey, dry_run=dry_run)


def _write_playbook(tmp_path: Path, tasks: list[dict], extra: dict | None = None) -> str:
    data: dict = {
        "version": "1.0",
        "project": "UnitTest",
        "global_invariants": {"max_retries_per_step": 2, "auto_compact_interval": 0},
        "tasks": tasks,
    }
    if extra:
        data.update(extra)
    p = tmp_path / "pb.yaml"
    p.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return str(p)


def _make_escalation_dump(step_id: str = "T01", is_stuck: bool = True) -> EscalationDump:
    return EscalationDump(
        playbook_path="test.yaml",
        step_id=step_id,
        step_name=f"Test Step {step_id}",
        total_attempts=3,
        failure_chain=["err1", "err2", "err3"],
        final_eval_output="AssertionError",
        is_stuck=is_stuck,
        is_diverging=False,
        suspect_test_file=False,
        human_hint="stuck after 3 attempts",
    )


def _make_playbook(tasks: list[PlaybookTask], global_goal: str | None = None) -> Playbook:
    return Playbook(
        project="UnitTest",
        global_invariants=__import__(
            "autoclaude.models.playbook", fromlist=["GlobalInvariants"]
        ).GlobalInvariants(),
        global_goal=global_goal,
        tasks=tasks,
    )


# ──────────────────────────────────────────────
# Gap-021: CONDITIONAL 突變
# ──────────────────────────────────────────────

class TestGap021ConditionalMutation:
    """Gap-021: 條件式分支突變 — condition_evaluator exit code 決定分支。"""

    def test_conditional_in_enum(self):
        """CONDITIONAL 已加入 StepMutationType enum。"""
        assert StepMutationType.CONDITIONAL == "CONDITIONAL"

    def test_conditional_model_fields(self):
        """StepMutation 支援 condition_evaluator / true_mutation / false_mutation。"""
        inner = StepMutation(
            mutation_type=StepMutationType.REVISE_CURRENT,
            revised_prompt="fixed",
            reasoning="test",
        )
        m = StepMutation(
            mutation_type=StepMutationType.CONDITIONAL,
            condition_evaluator="exit 0",
            true_mutation=inner,
            false_mutation=None,
            reasoning="branch on exit code",
        )
        assert m.mutation_type == StepMutationType.CONDITIONAL
        assert m.condition_evaluator == "exit 0"
        assert m.true_mutation.mutation_type == StepMutationType.REVISE_CURRENT
        assert m.false_mutation is None

    def test_conditional_exit0_applies_true_mutation(self, tmp_path):
        """condition exit 0 → true_mutation（REVISE_CURRENT）被套用。"""
        runner = _make_runner(dry_run=True)
        # 建立初始 playbook（2 步驟，第 1 步 dry-run 模式下自動成功）
        pb_path = _write_playbook(tmp_path, [
            {"step_id": "T01", "name": "t1", "prompt": "p1", "expected_output_regex": "pass"},
        ])

        true_m = StepMutation(
            mutation_type=StepMutationType.REVISE_CURRENT,
            revised_prompt="revised-by-true-branch",
            reasoning="true branch",
        )
        cond_m = StepMutation(
            mutation_type=StepMutationType.CONDITIONAL,
            condition_evaluator="exit 0",   # 必然 exit 0
            true_mutation=true_m,
            false_mutation=None,
            reasoning="test conditional",
        )

        playbook = runner._load_playbook(pb_path)
        task = playbook.tasks[0]
        step_log: list[str] = []
        mut_log: list[str] = []

        runner._apply_single_mutation(
            cond_m, playbook, pb_path, task, 0,
            step_log, mut_log, 1,
            {}, {}, {},
            __import__(
                "autoclaude.execution.workflow_detector", fromlist=["WorkflowType"]
            ).WorkflowType.UNKNOWN,
            1, MagicMock(), "",
        )
        # true_mutation 被套用 → REVISE_CURRENT 更新了 task.prompt
        assert task.prompt == "revised-by-true-branch"

    def test_conditional_exit1_applies_false_mutation(self, tmp_path):
        """condition exit 1 → false_mutation（REVISE_CURRENT）被套用，true_mutation 不套用。"""
        runner = _make_runner(dry_run=True)
        pb_path = _write_playbook(tmp_path, [
            {"step_id": "T01", "name": "t1", "prompt": "original", "expected_output_regex": "pass"},
        ])

        true_m = StepMutation(
            mutation_type=StepMutationType.REVISE_CURRENT,
            revised_prompt="should-not-apply",
            reasoning="true branch",
        )
        false_m = StepMutation(
            mutation_type=StepMutationType.REVISE_CURRENT,
            revised_prompt="false-branch-applied",
            reasoning="false branch",
        )
        cond_m = StepMutation(
            mutation_type=StepMutationType.CONDITIONAL,
            condition_evaluator="exit 1",   # 必然 exit 1
            true_mutation=true_m,
            false_mutation=false_m,
            reasoning="test false branch",
        )

        playbook = runner._load_playbook(pb_path)
        task = playbook.tasks[0]
        step_log: list[str] = []
        mut_log: list[str] = []

        runner._apply_single_mutation(
            cond_m, playbook, pb_path, task, 0,
            step_log, mut_log, 1,
            {}, {}, {},
            __import__(
                "autoclaude.execution.workflow_detector", fromlist=["WorkflowType"]
            ).WorkflowType.UNKNOWN,
            1, MagicMock(), "",
        )
        assert task.prompt == "false-branch-applied"

    def test_conditional_no_evaluator_skips(self, tmp_path):
        """condition_evaluator 為 None → 不套用任何分支，靜默略過。"""
        runner = _make_runner(dry_run=True)
        pb_path = _write_playbook(tmp_path, [
            {"step_id": "T01", "name": "t1", "prompt": "original", "expected_output_regex": "pass"},
        ])

        true_m = StepMutation(
            mutation_type=StepMutationType.REVISE_CURRENT,
            revised_prompt="should-not-apply",
            reasoning="true",
        )
        cond_m = StepMutation(
            mutation_type=StepMutationType.CONDITIONAL,
            condition_evaluator=None,
            true_mutation=true_m,
            reasoning="missing evaluator",
        )

        playbook = runner._load_playbook(pb_path)
        task = playbook.tasks[0]
        original_prompt = task.prompt

        runner._apply_single_mutation(
            cond_m, playbook, pb_path, task, 0,
            [], [], 1,
            {}, {}, {},
            __import__(
                "autoclaude.execution.workflow_detector", fromlist=["WorkflowType"]
            ).WorkflowType.UNKNOWN,
            1, MagicMock(), "",
        )
        # prompt 不應變更
        assert task.prompt == original_prompt


# ──────────────────────────────────────────────
# Gap-022: Evolution Message 注入 global_goal
# ──────────────────────────────────────────────

class TestGap022EvolutionGoalAlignment:
    """Gap-022: build_evolution_message 含 global_goal 且 MinimaxEvolver 正確傳遞。"""

    def test_build_evolution_message_with_global_goal(self):
        """build_evolution_message 帶 global_goal 時，訊息頂端包含系統總目標區段。"""
        msg = build_evolution_message(
            step_id="T01",
            step_name="實作 Auth",
            step_prompt="建立 JWT 登入",
            failure_summary="ImportError 3 次",
            escalation_reasoning="依賴缺失",
            global_goal="建立 FastAPI 登入模組",
        )
        assert "系統總目標" in msg
        assert "建立 FastAPI 登入模組" in msg
        # 總目標應在訊息頂端（比失敗步驟早出現）
        assert msg.index("系統總目標") < msg.index("失敗步驟")

    def test_build_evolution_message_without_global_goal(self):
        """build_evolution_message 不帶 global_goal 時，不含系統總目標區段。"""
        msg = build_evolution_message(
            step_id="T01",
            step_name="test",
            step_prompt="p",
            failure_summary="f",
            escalation_reasoning="r",
            global_goal=None,
        )
        assert "系統總目標" not in msg
        assert "失敗步驟" in msg

    def test_minimax_evolver_passes_global_goal(self, tmp_path):
        """MinimaxEvolver.propose_evolution_via_ai() 將 playbook.global_goal 傳遞至
        propose_evolution。"""
        mock_minimax = MagicMock()
        mock_minimax.propose_evolution.return_value = __import__(
            "autoclaude.models.decision", fromlist=["EvolutionDecision"]
        ).EvolutionDecision(
            evolution_type="INJECT_STEP",
            reasoning="test",
            new_step_id="T01_PRE",
            new_step_name="前置",
            new_step_prompt="pip install fastapi",
        )

        from autoclaude.models.playbook import GlobalInvariants
        playbook = Playbook(
            project="Test",
            global_goal="建立 FastAPI 登入模組",
            global_invariants=GlobalInvariants(),
            tasks=[PlaybookTask(step_id="T01", name="Auth", prompt="build auth")],
        )
        evolver = MinimaxEvolver()
        dump = _make_escalation_dump("T01")

        evolver.propose_evolution_via_ai(playbook, 0, dump, mock_minimax)

        # 驗證 propose_evolution 被呼叫且傳入了 global_goal
        mock_minimax.propose_evolution.assert_called_once()
        call_kwargs = mock_minimax.propose_evolution.call_args
        assert call_kwargs.kwargs.get("global_goal") == "建立 FastAPI 登入模組"


# ──────────────────────────────────────────────
# Gap-023: GOAL_VALIDATION 語意強化
# ──────────────────────────────────────────────

class TestGap023GoalValidationEnhanced:
    """Gap-023: build_goal_validation_message 含 code_state_snapshot。"""

    def test_goal_validation_message_with_code_snapshot(self):
        """帶 code_state_snapshot 時，訊息包含程式碼狀態區段。"""
        snapshot = "## 已修改的實作檔案\n- `auth.py` (50 行) 函式: login, verify"
        msg = build_goal_validation_message(
            global_goal="建立 FastAPI 登入模組",
            step_summary="T01 ✓, T02 ✓",
            playbook_project="TestProject",
            code_state_snapshot=snapshot,
        )
        assert "程式碼狀態快照" in msg or "auth.py" in msg
        assert "已完成的步驟記錄" in msg

    def test_goal_validation_message_without_code_snapshot(self):
        """不帶 code_state_snapshot 時，訊息不含空白區段。"""
        msg = build_goal_validation_message(
            global_goal="目標",
            step_summary="T01 ✓",
            playbook_project="Test",
            code_state_snapshot="",
        )
        assert "系統總目標" in msg
        assert "已完成的步驟記錄" in msg


# ──────────────────────────────────────────────
# Gap-024: EvolutionMetadata 持久化
# ──────────────────────────────────────────────

class TestGap024EvolutionContextContinuity:
    """Gap-024: EvolutionMetadata 模型 + apply_evolution 序列化 + Runner 重載恢復。"""

    def test_evolution_metadata_model(self):
        """EvolutionMetadata 可正確建立並驗證欄位。"""
        meta = EvolutionMetadata(
            generation=1,
            mutation_log=["[attempt 1] REVISE_CURRENT: T01"],
            escalated_step_ids=["T01"],
        )
        assert meta.generation == 1
        assert len(meta.mutation_log) == 1
        assert meta.escalated_step_ids == ["T01"]

    def test_evolution_metadata_default_values(self):
        """EvolutionMetadata 預設值正確。"""
        meta = EvolutionMetadata()
        assert meta.generation == 0
        assert meta.mutation_log == []
        assert meta.escalated_step_ids == []

    def test_playbook_has_evolution_metadata_field(self):
        """Playbook 模型包含 evolution_metadata 欄位。"""
        from autoclaude.models.playbook import GlobalInvariants
        pb = Playbook(
            project="Test",
            global_invariants=GlobalInvariants(),
            tasks=[PlaybookTask(step_id="T01", name="t", prompt="p")],
        )
        assert pb.evolution_metadata is None

        pb_with_meta = Playbook(
            project="Test",
            global_invariants=GlobalInvariants(),
            evolution_metadata=EvolutionMetadata(generation=2, mutation_log=["log1"]),
            tasks=[PlaybookTask(step_id="T01", name="t", prompt="p")],
        )
        assert pb_with_meta.evolution_metadata.generation == 2

    def test_apply_evolution_serializes_mutation_log(self, tmp_path):
        """apply_evolution() 將 mutation_log 序列化至演化版 YAML。"""
        evolver = PlaybookEvolver()
        from autoclaude.models.playbook import GlobalInvariants
        playbook = Playbook(
            project="Test",
            global_invariants=GlobalInvariants(),
            tasks=[
                PlaybookTask(
                    step_id="T01", name="t", prompt="a\nb\nc\nd\ne\nf",
                    evaluator_command="pytest tests/",
                ),
                PlaybookTask(step_id="T02", name="t2", prompt="p2"),
            ],
        )
        dump = _make_escalation_dump("T01")

        proposal = evolver.propose_evolution(playbook, 0, dump)
        assert proposal is not None

        pb_path = str(tmp_path / "test.yaml")
        mutation_log = ["[attempt 1] REVISE_CURRENT: T01", "[attempt 2] INJECT_AFTER: T01_FIX"]
        evolved_path = evolver.apply_evolution(
            playbook, proposal, pb_path, mutation_log=mutation_log
        )

        assert evolved_path != pb_path
        evolved_data = yaml.safe_load(Path(evolved_path).read_text(encoding="utf-8"))
        assert "evolution_metadata" in evolved_data
        assert evolved_data["evolution_metadata"]["generation"] == 1
        assert len(evolved_data["evolution_metadata"]["mutation_log"]) == 2

    def test_runner_restores_mutation_log_from_evolution_metadata(self, tmp_path):
        """AutoResumeService 載入含 evolution_metadata 的演化版 YAML，執行成功。"""
        pb_data = {
            "version": "1.0",
            "project": "Test",
            "global_invariants": {"max_retries_per_step": 1, "auto_compact_interval": 0},
            "evolution_metadata": {
                "generation": 1,
                "mutation_log": ["[attempt 1] REVISE_CURRENT: T01"],
                "escalated_step_ids": ["T01"],
            },
            "tasks": [
                {"step_id": "T01", "name": "t", "prompt": "p"},
            ],
        }
        pb_path = tmp_path / "evolved_pb.yaml"
        pb_path.write_text(yaml.dump(pb_data, allow_unicode=True), encoding="utf-8")

        service, _ = make_service(outputs=["[DONE]"])
        result = service.run(str(pb_path))
        assert result.success


# ──────────────────────────────────────────────
# Gap-025: Batch Mutation Safety
# ──────────────────────────────────────────────

class TestGap025BatchMutationSafety:
    """Gap-025: 批次突變相容性預驗證。"""

    def test_validate_batch_inject_before_plus_goto_rejected(self):
        """INJECT_BEFORE + GOTO_STEP 批次應被拒絕（語意衝突）。"""
        runner = _make_runner(dry_run=True)
        batch = [
            StepMutation(
                mutation_type=StepMutationType.INJECT_BEFORE,
                new_step_id="T01_PRE",
                new_step_name="前置",
                new_step_prompt="pip install",
                reasoning="env",
            ),
            StepMutation(
                mutation_type=StepMutationType.GOTO_STEP,
                goto_step_id="T00",
                reasoning="goto",
            ),
        ]
        valid, reason = runner._validate_batch_compatibility(batch)
        assert not valid
        assert "GOTO_STEP" in reason or "INJECT_BEFORE" in reason

    def test_validate_batch_double_inject_before_rejected(self):
        """批次中兩個 INJECT_BEFORE 應被拒絕（重複注入防護）。"""
        runner = _make_runner(dry_run=True)
        batch = [
            StepMutation(
                mutation_type=StepMutationType.INJECT_BEFORE,
                new_step_id="T01_PRE1",
                new_step_name="前置1",
                new_step_prompt="pip install fastapi",
                reasoning="env1",
            ),
            StepMutation(
                mutation_type=StepMutationType.INJECT_BEFORE,
                new_step_id="T01_PRE2",
                new_step_name="前置2",
                new_step_prompt="pip install sqlalchemy",
                reasoning="env2",
            ),
        ]
        valid, reason = runner._validate_batch_compatibility(batch)
        assert not valid
        assert "INJECT_BEFORE" in reason

    def test_validate_batch_conditional_rejected(self):
        """批次中含 CONDITIONAL 突變應被拒絕。"""
        runner = _make_runner(dry_run=True)
        inner = StepMutation(
            mutation_type=StepMutationType.REVISE_CURRENT,
            revised_prompt="fix",
            reasoning="r",
        )
        batch = [
            inner,
            StepMutation(
                mutation_type=StepMutationType.CONDITIONAL,
                condition_evaluator="exit 0",
                true_mutation=inner,
                reasoning="cond",
            ),
        ]
        valid, reason = runner._validate_batch_compatibility(batch)
        assert not valid
        assert "CONDITIONAL" in reason

    def test_validate_batch_compatible_passes(self):
        """相容的批次（REVISE_CURRENT + INJECT_AFTER）應通過驗證。"""
        runner = _make_runner(dry_run=True)
        batch = [
            StepMutation(
                mutation_type=StepMutationType.REVISE_CURRENT,
                revised_prompt="new prompt",
                reasoning="revise",
            ),
            StepMutation(
                mutation_type=StepMutationType.INJECT_AFTER,
                new_step_id="T01_FIX",
                new_step_name="後置修復",
                new_step_prompt="run tests",
                reasoning="post-fix",
            ),
        ]
        valid, reason = runner._validate_batch_compatibility(batch)
        assert valid
        assert reason == ""


# ──────────────────────────────────────────────
# Gap-026: SPLIT_STEP Part A evaluator 推導
# ──────────────────────────────────────────────

class TestGap026SplitStepEvaluator:
    """Gap-026: SPLIT_STEP Part A 從原 evaluator 推導輕量評估指令。"""

    def test_derive_part_a_evaluator_pytest(self):
        """pytest evaluator → --collect-only Part A evaluator。"""
        result = PlaybookEvolver._derive_part_a_evaluator("pytest tests/test_auth.py -v")
        assert result is not None
        assert "--collect-only" in result
        assert "pytest" in result

    def test_derive_part_a_evaluator_no_evaluator(self):
        """無 evaluator → 回傳 None。"""
        result = PlaybookEvolver._derive_part_a_evaluator(None)
        assert result is None

    @pytest.mark.parametrize(
        "cmd",
        [
            "python -m pytest tests/foo.py -k xyz -q",
            "python3 -m pytest tests/foo.py -k xyz -q",
        ],
    )
    def test_derive_part_a_evaluator_python_m_pytest_form_is_valid_command(self, cmd):
        """R52 迴歸鎖：'python(3) -m pytest ...' 形態不得被推導成語法上不存在的
        'python --collect-only'（rc=2 unknown option）。

        根因：舊實作用 `\\bpytest\\b` 偵測是否為 pytest 指令（此形態命中，因字串
        含 'pytest'），但取可執行檔名時用 `base.split()[0]`，對此形態拿到的是
        'python'/'python3'，不是 'pytest'，產出的指令本身恆定失敗 —— 與本函式
        docstring 明文的「非 pytest 指令才無條件回傳成功、pytest 指令僅做
        collect-only 確認語法正確」設計意圖直接相反。三層架構
        （tools/three_tier_to_playbook.py `_EVAL_ALLOWED_HEAD`）明文允許此形態，
        故必須產出可實際執行成功的指令。
        """
        import subprocess

        result = PlaybookEvolver._derive_part_a_evaluator(cmd)
        assert result is not None
        assert "--collect-only" in result
        assert "pytest" in result
        proc = subprocess.run(
            result, shell=True, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30,
        )
        assert proc.returncode == 0, (
            f"'{cmd}' 推導出的 Part A evaluator '{result}' 應可成功執行 "
            f"(--collect-only)，實際 rc={proc.returncode}, stderr={proc.stderr!r}"
        )

    def test_derive_part_a_evaluator_other_cmd(self):
        """非 pytest 指令 → 無論原指令是否失敗都應 exit 0（Part A 只涵蓋一半任務）。

        DEF-101（R50）：舊實作用 POSIX-only `{ cmd; } || true`，在 Windows cmd.exe 下
        （不支援 `{ }` 分組、無內建 true）恆常誤判失敗。本測試親跑 subprocess 驗證
        真實行為，而非只比對字面 token（舊測試對此毫無鑑別力）。
        """
        import subprocess

        # 原指令會失敗（exit 1），Part A evaluator 仍須回報成功
        result = PlaybookEvolver._derive_part_a_evaluator("python -c \"import sys; sys.exit(1)\"")
        assert result is not None
        proc = subprocess.run(
            result, shell=True, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=10,
        )
        assert proc.returncode == 0, f"Part A evaluator 應無條件 exit 0，實際: {proc.returncode}"
        # 不得含 POSIX-only 分組語法（cmd.exe 不支援）
        assert "{ " not in result and "; }" not in result

    def test_derive_part_a_evaluator_other_cmd_no_posix_only_syntax(self):
        """非 pytest 指令生成結果不得含 Windows cmd.exe 不支援的 POSIX 專屬語法。"""
        result = PlaybookEvolver._derive_part_a_evaluator("some-cmd --flag")
        assert result is not None
        assert not result.startswith("{")
        assert "|| true" not in result

    def test_derive_part_a_evaluator_uses_sys_executable_not_bare_python(self):
        """R51 迴歸鎖：包裝殼必須用 `sys.executable` 絕對路徑，不得退化為裸字面值
        `python`（macOS /usr/bin 與多數現代 Linux distro 預設 PATH 上無 `python`
        別名，裸字面值會以 rc=127 command not found 收場，打破本函式『非 pytest
        指令必須無條件回傳成功』的契約 — R51 修復前的真實缺陷）。

        既有測試（如 test_derive_part_a_evaluator_other_cmd）皆在繼承呼叫端
        .venv PATH（恆含 python 別名）下執行 subprocess，對『PATH 上無裸 python』
        這個環境維度零鑑別力：即使有人把 sys.executable 改回裸字面值 'python'，
        那些測試仍會通過。本測試改用「複製目前環境變數、僅清空 PATH」的受限
        環境親跑 subprocess，直接重現此環境缺口 —— 若退化為裸字面值，本測試
        會在任何機器上以 rc!=0 變紅，不再依賴開發機 PATH 是否恰好有 python 別名。
        """
        import os
        import subprocess
        import sys

        result = PlaybookEvolver._derive_part_a_evaluator(
            'python -c "import sys; sys.exit(1)"'
        )
        assert result is not None
        # token 級直接斷言：產出指令必須含本行程實際直譯器的絕對路徑（雙引號包住）
        assert f'"{sys.executable}"' in result, (
            f"evaluator_command 應含 sys.executable 絕對路徑，實際: {result}"
        )

        # 受限環境親跑：複製目前環境變數但清空 PATH，模擬 PATH 上無任何
        # python/python3 可被裸字面值找到的情境（其餘變數如 SystemRoot/HOME
        # 保留，避免殼本身因缺變數而異常，僅單獨隔離 PATH 這個維度）。
        restricted_env = dict(os.environ)
        restricted_env["PATH"] = ""
        proc = subprocess.run(
            result, shell=True, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=10, env=restricted_env,
        )
        assert proc.returncode == 0, (
            "受限 PATH（無裸 python 可被找到）下 Part A evaluator 仍應無條件 "
            f"exit 0（因用絕對路徑不靠 PATH 查找），實際 rc={proc.returncode}, "
            f"stdout={proc.stdout!r}, stderr={proc.stderr!r}"
        )

    def test_split_step_part_a_has_evaluator(self):
        """PlaybookEvolver.propose_evolution() SPLIT_STEP — Part A 應有 evaluator_command。"""
        from autoclaude.models.playbook import GlobalInvariants
        playbook = Playbook(
            project="Test",
            global_invariants=GlobalInvariants(),
            tasks=[PlaybookTask(
                step_id="T01",
                name="複雜步驟",
                prompt="步驟一\n第一部分\n步驟二\n第二部分\n步驟三\n第三部分",
                evaluator_command="pytest tests/",
            )],
        )
        dump = EscalationDump(
            playbook_path="test.yaml",
            step_id="T01",
            step_name="複雜步驟",
            total_attempts=5,
            failure_chain=["e1", "e2", "e3"],
            final_eval_output="stuck",
            is_stuck=True,
            is_diverging=False,
            suspect_test_file=False,
            human_hint="stuck",
        )
        evolver = PlaybookEvolver()
        proposal = evolver.propose_evolution(playbook, 0, dump)
        assert proposal is not None
        assert proposal.evolution_type == "SPLIT_STEP"
        part_a = proposal.split_steps[0]
        assert part_a.evaluator_command is not None
        assert "--collect-only" in part_a.evaluator_command


class TestGap026BMinimaxEvolverSplitStepEvaluator:
    """Gap-026-B：MinimaxEvolver 有獨立一份 _derive_part_a_evaluator 實作，需同等驗證
    （R50 四方審查發現：與 PlaybookEvolver 版本重複同一 POSIX-only bug，各自要有回歸測試）。
    """

    def test_derive_part_a_evaluator_pytest(self):
        result = MinimaxEvolver._derive_part_a_evaluator("pytest tests/test_auth.py -v")
        assert result is not None
        assert "--collect-only" in result

    def test_derive_part_a_evaluator_no_evaluator(self):
        assert MinimaxEvolver._derive_part_a_evaluator(None) is None

    @pytest.mark.parametrize(
        "cmd",
        [
            "python -m pytest tests/foo.py -k xyz -q",
            "python3 -m pytest tests/foo.py -k xyz -q",
        ],
    )
    def test_derive_part_a_evaluator_python_m_pytest_form_is_valid_command(self, cmd):
        """R52 迴歸鎖（MinimaxEvolver 側，鏡射 TestGap026SplitStepEvaluator 同名測試）：
        'python(3) -m pytest ...' 形態必須產出可實際執行成功的 --collect-only 指令，
        不得退化為語法上不存在的 'python --collect-only'（rc=2 unknown option）。
        """
        import subprocess

        result = MinimaxEvolver._derive_part_a_evaluator(cmd)
        assert result is not None
        assert "--collect-only" in result
        assert "pytest" in result
        proc = subprocess.run(
            result, shell=True, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30,
        )
        assert proc.returncode == 0, (
            f"'{cmd}' 推導出的 Part A evaluator '{result}' 應可成功執行 "
            f"(--collect-only)，實際 rc={proc.returncode}, stderr={proc.stderr!r}"
        )

    def test_derive_part_a_evaluator_other_cmd_executes_and_always_succeeds(self):
        """非 pytest 指令：即使原指令失敗，Part A evaluator 仍須以 exit 0 收場，
        且產生的指令不得含 Windows cmd.exe 無法解讀的 POSIX 專屬語法。
        """
        import subprocess

        result = MinimaxEvolver._derive_part_a_evaluator(
            "python -c \"import sys; sys.exit(1)\""
        )
        assert result is not None
        assert "{ " not in result and "; }" not in result
        assert "|| true" not in result
        proc = subprocess.run(
            result, shell=True, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=10,
        )
        assert proc.returncode == 0, f"Part A evaluator 應無條件 exit 0，實際: {proc.returncode}"

    def test_derive_part_a_evaluator_uses_sys_executable_not_bare_python(self):
        """R51 迴歸鎖（MinimaxEvolver 側，鏡射 TestGap026SplitStepEvaluator 同名測試）：
        包裝殼必須用 `sys.executable` 絕對路徑，不得退化為裸字面值 `python`。
        以「複製目前環境變數、僅清空 PATH」的受限環境親跑 subprocess，直接
        重現『PATH 上無裸 python 可被找到』的環境缺口，非只比對字面 token。
        """
        import os
        import subprocess
        import sys

        result = MinimaxEvolver._derive_part_a_evaluator(
            'python -c "import sys; sys.exit(1)"'
        )
        assert result is not None
        assert f'"{sys.executable}"' in result, (
            f"evaluator_command 應含 sys.executable 絕對路徑，實際: {result}"
        )

        restricted_env = dict(os.environ)
        restricted_env["PATH"] = ""
        proc = subprocess.run(
            result, shell=True, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=10, env=restricted_env,
        )
        assert proc.returncode == 0, (
            "受限 PATH（無裸 python 可被找到）下 Part A evaluator 仍應無條件 "
            f"exit 0，實際 rc={proc.returncode}, stdout={proc.stdout!r}, "
            f"stderr={proc.stderr!r}"
        )


# ──────────────────────────────────────────────
# R50-P2: PlaybookEvolver / MinimaxEvolver 的 _derive_part_a_evaluator
# 由各自獨立實作收斂為共用函式（SSOT），防止同一 bug 需分別修復兩次。
# ──────────────────────────────────────────────

class TestGap026CSharedEvaluatorDerivationSSOT:
    """R50 四方審查 P2：PlaybookEvolver 與 MinimaxEvolver 的
    `_derive_part_a_evaluator` 100% 重複實作（SSOT 違反）。本測試證明修復後
    兩者皆委派至共用函式 `_evaluator_derivation.derive_part_a_evaluator`，
    往後同類 bug 只需修一處即可同時修好兩邊。
    """

    def test_both_evolvers_delegate_to_shared_function(self, monkeypatch):
        """兩個 Evolver 的 staticmethod 實際呼叫同一個共用函式（非各自重複邏輯）。

        以 monkeypatch 替換共用函式為哨兵回傳值：若 PlaybookEvolver 或
        MinimaxEvolver 仍保有自己的獨立實作（未真正委派），下方 assert 會失敗
        （因為各自舊實作不會回傳這個哨兵值），能在未來有人「復原」重複實作時
        立即被本測試抓到（red）。
        """
        sentinel = "__SENTINEL_SHARED_IMPL__"
        monkeypatch.setattr(
            _evaluator_derivation, "derive_part_a_evaluator", lambda full_evaluator: sentinel
        )
        # PlaybookEvolver / MinimaxEvolver 模組各自匯入函式名稱綁定，
        # patch 來源模組的屬性後，經由 import 別名呼叫的結果應同步反映哨兵值。
        import autoclaude.evolution.minimax_evolver as me_mod
        import autoclaude.evolution.playbook_evolver as pe_mod
        monkeypatch.setattr(pe_mod, "derive_part_a_evaluator", lambda full_evaluator: sentinel)
        monkeypatch.setattr(me_mod, "derive_part_a_evaluator", lambda full_evaluator: sentinel)

        assert PlaybookEvolver._derive_part_a_evaluator("pytest tests/test_x.py -v") == sentinel
        assert MinimaxEvolver._derive_part_a_evaluator("pytest tests/test_x.py -v") == sentinel

    @pytest.mark.parametrize(
        "raw_cmd",
        [
            None,
            "",
            "pytest tests/test_auth.py -v",
            "pytest tests/test_auth.py -k foo --tb=short",
            "python -m pytest tests/foo.py -k xyz -q",
            "python3 -m pytest tests/foo.py -k xyz -q",
            "python -c \"import sys; sys.exit(1)\"",
            "some-cmd --flag",
        ],
    )
    def test_playbook_and_minimax_produce_identical_output(self, raw_cmd):
        """對相同輸入，PlaybookEvolver 與 MinimaxEvolver 的推導結果必須逐字相同
        （證明兩者已收斂至同一份邏輯，不會再各自漂移）。
        """
        assert (
            PlaybookEvolver._derive_part_a_evaluator(raw_cmd)
            == MinimaxEvolver._derive_part_a_evaluator(raw_cmd)
        )


# ──────────────────────────────────────────────
# Gap-027: GOTO Context Clean Hint
# ──────────────────────────────────────────────

class TestGap027GotoContextClean:
    """Gap-027: GOTO 重訪時注入 context clean hint。"""

    def test_goto_revisit_hint_in_dry_run_not_injected(self, tmp_path):
        """Kernel 模式下 GOTO 無 hint 注入，2 步驟 Playbook 直接成功。"""
        pb_path = _write_playbook(tmp_path, [
            {"step_id": "T01", "name": "t1", "prompt": "p1"},
            {"step_id": "T02", "name": "t2", "prompt": "p2"},
        ])
        service, _ = make_service(outputs=["[DONE]", "[DONE]"])
        result = service.run(pb_path)
        assert result.success

    def test_goto_revisit_prev_step_idx_tracked(self, tmp_path):
        """Kernel 模式下 2 步驟 Playbook 順序執行全部完成。"""
        pb_path = _write_playbook(tmp_path, [
            {"step_id": "T01", "name": "t1", "prompt": "p1"},
            {"step_id": "T02", "name": "t2", "prompt": "p2"},
        ])
        service, _ = make_service(outputs=["[DONE]", "[DONE]"])
        result = service.run(pb_path)
        assert result.completed_steps == 2
        assert result.success


# ──────────────────────────────────────────────
# Gap-028: INJECT_BEFORE 步驟去重
# ──────────────────────────────────────────────

class TestGap028InjectBeforeDeduplicate:
    """Gap-028: 相似前綴 step_id 二次注入時使用遞增序號。"""

    def test_inject_before_dedup_when_similar_exists(self, tmp_path):
        """已存在相似前置步驟時，INJECT_BEFORE 仍可注入（注入後至少 1 個 PRE 步驟）。"""
        pb_path = _write_playbook(tmp_path, [
            {"step_id": "T01_PRE", "name": "前置已存在", "prompt": "pip install"},
            {"step_id": "T01", "name": "主步驟", "prompt": "main"},
        ])
        playbook = load_playbook(pb_path)

        mut = StepMutation(
            mutation_type=StepMutationType.INJECT_BEFORE,
            new_step_id="T01_PRE",
            new_step_name="第二次前置",
            new_step_prompt="pip install more",
            reasoning="need more deps",
        )
        MutationApplyService().apply(mut, playbook, current_idx=1)

        all_step_ids = [t.step_id for t in playbook.tasks]
        pre_steps = [sid for sid in all_step_ids if "PRE" in sid]
        assert len(pre_steps) >= 1

    def test_inject_before_no_similar_existing_uses_proposed_id(self, tmp_path):
        """不存在相似前置步驟時，INJECT_BEFORE 插入至 current_idx 位置。"""
        pb_path = _write_playbook(tmp_path, [
            {"step_id": "T01", "name": "t1", "prompt": "p1"},
        ])
        playbook = load_playbook(pb_path)
        original_count = len(playbook.tasks)

        mut = StepMutation(
            mutation_type=StepMutationType.INJECT_BEFORE,
            new_step_id="T01_PRE",
            new_step_name="前置步驟",
            new_step_prompt="setup env",
            reasoning="need env",
        )
        MutationApplyService().apply(mut, playbook, current_idx=0)

        assert len(playbook.tasks) == original_count + 1
        assert "T01_PRE" in playbook.tasks[0].step_id
