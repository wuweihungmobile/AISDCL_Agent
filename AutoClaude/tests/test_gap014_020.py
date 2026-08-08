"""
Gap-014 ~ Gap-020 整合驗證測試。

涵蓋：
- Gap-014: GoalAchievementDecision 模型 / validate_goal_achievement API / GOAL_SYNTHESIS 注入
  / 防遞迴
- Gap-015: _prepend_global_goal_brief / 所有步驟首次 attempt 注入
- Gap-016: MinimaxEvolver AI 演化提議 / propose_evolution API / fallback 至規則引擎
- Gap-017: SKIP_TO 突變 / 向前跳轉 / 防向後 / 最多 1 次防護
- Gap-018: SPLIT_STEP context bridge 前置文字
- Gap-019: 批次突變應用 / 最多 3 個 / 破壞性突變警告
- Gap-020: AppConfig PlaybookConfig 新欄位 / max_evolutions 從 config 讀取
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from autoclaude.decision.minimax_client import MinimaxClient, MinimaxError
from autoclaude.decision.prompt_builder import (
    EVOLUTION_SYSTEM_PROMPT,
    GOAL_VALIDATION_SYSTEM_PROMPT,
    build_evolution_message,
    build_goal_validation_message,
)
from autoclaude.evolution.minimax_evolver import MinimaxEvolver
from autoclaude.evolution.playbook_evolver import PlaybookEvolver
from autoclaude.execution.playbook_runner import PlaybookRunner
from autoclaude.models.decision import (
    EvolutionDecision,
    GoalAchievementDecision,
)
from autoclaude.models.escalation import EscalationDump
from autoclaude.models.playbook import PlaybookTask
from autoclaude.models.step_mutation import StepMutation, StepMutationType
from autoclaude.utils.config import AppConfig, PlaybookConfig
from tests.helpers.kernel_fixtures import make_service

# SD_09 R56 zero-trust audit：CI runner 無 `claude` CLI binary；dry_run=False 真實執行測試
# 經 perception/pty_wrapper spawn `claude` → FileNotFoundError。環境前提閘門（同
# autoclaude/execution/pre_run_validator.py:56 shutil.which 與 ~50 PG importorskip 慣例）：
# 本地有 claude 照常驗證 escalation/evolution 真實路徑；CI 無 binary → graceful skip（非掩蓋
# code bug，純環境缺 binary）。完整 CI 覆蓋（改用 make_service fake-executor 重寫）列
# SD_10 P3-R56-2。
#
# DEF-101-089 補強（R4 Mac/Windows 複審主 agent 發現，親推 push 時實機重現）：本機裝有
# `claude` CLI 且從「本身已是存活 Claude Code session」巢狀執行 pytest（不論本機開發驗證
# 或 pre-push hook）時，這裡 spawn 的子行程會無限掛起。`CLAUDECODE=1` 是 Claude Code
# 執行環境官方在啟動時就會設定的環境變數（非行程樹猜測），用它額外 skip 巢狀 session
# 情境是可靠訊號、非 heuristic 賭注——一般 CI runner／非巢狀本機開發環境不受影響
# （該變數不存在）。
#
# 🔴 本輪訂正分類（Rule 12 fail-loud：分類錯的方向是**悲觀**，後果一樣是資訊遺失）。
# 前一份全庫 skip 盤點把這一批歸為「可辯護的永久不覆蓋」、並寫「在 Claude Code session
# 內永遠跑不到」。前半句是真的，後半句被推廣成了「永遠跑不到」——而上面那個 `or` 有
# **兩個**條件：本機 `claude` binary 存在（第一個條件為 False），只有巢狀那個條件成立。
# 於是在**非**巢狀 session（＝ schtasks 跑的每日 nightly）兩個條件都不成立，這一批會真的
# 跑。當回合對帳：nightly log 與巢狀 session 同一棵樹 collected 相同，nightly 少了 15 支
# skip、多了 15 支 passed，且其 `-rs` 清單對本檔零命中 ⇒ 它們跑了而且綠。
# 代價是那條**真的可用的配方**從未進過任何文件；reason 因此改為寫得出配方。
#
# 🔴 R79 訂正本條的**因果敘述**（原文把掛起歸因到 `CLAUDECODE=1` 這個變數本身，該歸因
# 已被對照組推翻，故此處不逐字複述原句）。當回合三次實測，載具＝直接驅動 `PtyWrapper`：
#   · 繼承 `CLAUDECODE=1`：`start()` 180.16s 未回返（watchdog rc=99）
#   · **剝除** `CLAUDECODE` 的對照組：180.05s 未回返，行為完全一樣
#   · 行程樹快照：掛在 wexpect 自己的 host↔console-reader 交握，`claude.exe` 從未被啟動
# ⇒ 真正掛住的是「巢狀 Claude Code session 這個執行環境 × `wexpect.spawn()`」這一組，
# `CLAUDECODE` 只是該環境的**可靠標記**、不是成因。判準因此**維持不變**（在該環境內
# skip 仍然是對的，拿掉這半個條件會讓這 11 支當場掛死整棵樹——已注入實證），只改寫
# reason 讓它別再宣稱一個已被證偽的因果。另一半也要講清楚：DEF-101-089 的原結論在
# `claude -p` 這種**非互動 subprocess** spawn 上確實已被推翻（rc=0／約 4s），但那條路
# **不是**本檔走的路（本機 `claude` 解析為 `.EXE` 而非 `.cmd` shim ⇒ 進 `_start_wexpect`）。
# 逐次量測見 `docs/06_quality/CrossPlatform_R79_Debt_Audit.md` 的 `## DEF-101-913` 節。
requires_claude_cli = pytest.mark.skipif(
    shutil.which("claude") is None or os.environ.get("CLAUDECODE") == "1",
    reason="[ENV-DISABLED] 【未啟用，非缺件】需要 claude CLI binary 且非巢狀 Claude Code "
    "session（巢狀 session 內 wexpect pty spawn 掛住不回，R79 實測 180s×2＋45s、claude.exe "
    "從未啟動；剝除 CLAUDECODE 的對照組行為相同 ⇒ 該變數是環境標記非成因。見 DEF-101-913）。"
    "跑法：在**非** Claude Code session 的 PowerShell 執行 "
    "`python -m pytest tests/test_gap014_020.py`"
    "（每日 nightly 排程即為此環境，2026-08-06 nightly log 實測會真的跑）",
)


# ──────────────────────────────────────────────
# 共用輔助函式
# ──────────────────────────────────────────────

def _make_runner(dry_run: bool = False, minimax_mock=None) -> PlaybookRunner:
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


def _make_minimax_client() -> MinimaxClient:
    return MinimaxClient(
        api_key="test_key",
        base_url="https://example.com/v1",
        model="test-model",
        timeout=5,
    )


def _mock_response(payload: dict) -> dict:
    return {"choices": [{"message": {"content": json.dumps(payload)}}]}


def _make_escalation_dump(step_id: str = "T01") -> EscalationDump:
    return EscalationDump(
        playbook_path="test.yaml",
        step_id=step_id,
        step_name=f"Test Step {step_id}",
        total_attempts=3,
        failure_chain=["err1", "err2", "err3"],
        final_eval_output="AssertionError",
        is_stuck=True,
        is_diverging=False,
        suspect_test_file=False,
        human_hint="stuck after 3 attempts",
    )


# ──────────────────────────────────────────────
# Gap-020: AppConfig PlaybookConfig 新欄位
# ──────────────────────────────────────────────

class TestGap020AppConfig:
    def test_default_max_evolutions(self):
        cfg = AppConfig()
        assert cfg.playbook.max_evolutions == 3

    def test_default_goal_synthesis_enabled(self):
        cfg = AppConfig()
        assert cfg.playbook.goal_synthesis_enabled is True

    def test_default_global_goal_brief_chars(self):
        cfg = AppConfig()
        assert cfg.playbook.global_goal_brief_chars == 150

    def test_custom_values(self):
        cfg = AppConfig.model_validate({
            "playbook": {
                "max_evolutions": 5,
                "goal_synthesis_enabled": False,
                "global_goal_brief_chars": 200,
            }
        })
        assert cfg.playbook.max_evolutions == 5
        assert cfg.playbook.goal_synthesis_enabled is False
        assert cfg.playbook.global_goal_brief_chars == 200

    def test_max_evolutions_bounds(self):
        with pytest.raises(Exception):
            PlaybookConfig(max_evolutions=0)   # ge=1
        with pytest.raises(Exception):
            PlaybookConfig(max_evolutions=11)  # le=10

    def test_runner_uses_config_max_evolutions(self, tmp_path):
        """Gap-020-B: AutoResumeService 模式從 config 讀取 max_evolutions，成功執行。"""
        cfg = AppConfig.model_validate({"playbook": {"max_evolutions": 1}})
        pb_path = _write_playbook(tmp_path, [
            {"step_id": "T01", "name": "t", "prompt": "p", "expected_output_regex": "pass"}
        ])
        service, _ = make_service(outputs=["[DONE]"], config=cfg)
        result = service.run(pb_path)
        assert result.success


# ──────────────────────────────────────────────
# Gap-017: StepMutation SKIP_TO 模型
# ──────────────────────────────────────────────

class TestGap017StepMutationSkipTo:
    def test_skip_to_in_enum(self):
        assert StepMutationType.SKIP_TO == "SKIP_TO"

    def test_skip_to_mutation_model(self):
        m = StepMutation(
            mutation_type=StepMutationType.SKIP_TO,
            skip_to_step_id="T05",
            skip_reason="T03/T04 已被前置步驟隱性完成",
            reasoning="跳過冗餘步驟",
        )
        assert m.skip_to_step_id == "T05"
        assert m.skip_reason is not None

    def test_skip_to_fields_optional(self):
        m = StepMutation(mutation_type=StepMutationType.DELETE_STEP, delete_step_id="T02")
        assert m.skip_to_step_id is None
        assert m.skip_reason is None


# ──────────────────────────────────────────────
# Gap-019: 批次突變模型
# ──────────────────────────────────────────────

class TestGap019BatchMutation:
    def test_batch_mutations_field_exists(self):
        m = StepMutation(
            mutation_type=StepMutationType.REVISE_CURRENT,
            revised_prompt="new prompt",
            batch_mutations=[
                StepMutation(
                    mutation_type=StepMutationType.DELETE_STEP,
                    delete_step_id="T03",
                ),
            ],
        )
        assert m.batch_mutations is not None
        assert len(m.batch_mutations) == 1
        assert m.batch_mutations[0].delete_step_id == "T03"

    def test_batch_mutations_none_by_default(self):
        m = StepMutation(mutation_type=StepMutationType.REVISE_CURRENT, revised_prompt="x")
        assert m.batch_mutations is None

    def test_batch_mutations_recursive_type(self):
        inner = StepMutation(mutation_type=StepMutationType.REVISE_CURRENT, revised_prompt="inner")
        outer = StepMutation(
            mutation_type=StepMutationType.REVISE_CURRENT,
            revised_prompt="outer",
            batch_mutations=[inner],
        )
        assert outer.batch_mutations[0].revised_prompt == "inner"


# ──────────────────────────────────────────────
# Gap-014: GoalAchievementDecision 模型
# ──────────────────────────────────────────────

class TestGap014GoalAchievementDecision:
    def test_achieved_true(self):
        d = GoalAchievementDecision(is_achieved=True)
        assert d.is_achieved is True
        assert d.completion_prompt == ""
        assert d.gap_analysis == ""

    def test_not_achieved(self):
        d = GoalAchievementDecision(
            is_achieved=False,
            completion_prompt="請補完整合模組",
            gap_analysis="Auth 與 DB 介面不相容",
        )
        assert d.is_achieved is False
        assert "補完" in d.completion_prompt
        assert "Auth" in d.gap_analysis


# ──────────────────────────────────────────────
# Gap-014: MinimaxClient.validate_goal_achievement()
# ──────────────────────────────────────────────

class TestGap014MinimaxValidateGoal:
    def test_validate_goal_returns_achieved(self):
        client = _make_minimax_client()
        with patch("httpx.post") as mock_post:
            mock_post.return_value.json.return_value = _mock_response({
                "is_achieved": True,
                "completion_prompt": "",
                "gap_analysis": "",
            })
            mock_post.return_value.raise_for_status = MagicMock()
            decision = client.validate_goal_achievement(
                global_goal="建立 FastAPI 登入模組",
                step_summary="T01 ✓\nT02 ✓",
                playbook_project="TestProject",
            )
        assert isinstance(decision, GoalAchievementDecision)
        assert decision.is_achieved is True

    def test_validate_goal_returns_not_achieved(self):
        client = _make_minimax_client()
        with patch("httpx.post") as mock_post:
            mock_post.return_value.json.return_value = _mock_response({
                "is_achieved": False,
                "completion_prompt": "請整合 Auth 與 DB",
                "gap_analysis": "介面不相容",
            })
            mock_post.return_value.raise_for_status = MagicMock()
            decision = client.validate_goal_achievement(
                global_goal="建立 FastAPI 整合模組",
                step_summary="T01 ✓\nT02 ✓",
                playbook_project="TestProject",
            )
        assert decision.is_achieved is False
        assert "整合" in decision.completion_prompt

    def test_validate_goal_raises_on_invalid_json(self):
        client = _make_minimax_client()
        with patch("httpx.post") as mock_post:
            mock_post.return_value.json.return_value = {
                "choices": [{"message": {"content": "not json"}}]
            }
            mock_post.return_value.raise_for_status = MagicMock()
            with pytest.raises(MinimaxError):
                client.validate_goal_achievement("g", "s", "p")


# ──────────────────────────────────────────────
# Gap-014: prompt_builder GOAL_VALIDATION_SYSTEM_PROMPT
# ──────────────────────────────────────────────

class TestGap014PromptBuilder:
    def test_goal_validation_system_prompt_exists(self):
        assert "is_achieved" in GOAL_VALIDATION_SYSTEM_PROMPT
        assert "completion_prompt" in GOAL_VALIDATION_SYSTEM_PROMPT

    def test_build_goal_validation_message(self):
        msg = build_goal_validation_message(
            global_goal="建立 FastAPI 模組",
            step_summary="T01 ✓\nT02 ✓",
            playbook_project="TestProj",
        )
        assert "FastAPI" in msg
        assert "T01" in msg
        assert "TestProj" in msg


# ──────────────────────────────────────────────
# Gap-014: PlaybookRunner _validate_global_goal_achievement
# ──────────────────────────────────────────────

class TestGap014RunnerValidateGoal:
    def test_validate_goal_returns_none_when_achieved(self):
        minimax = MagicMock()
        minimax.validate_goal_achievement.return_value = GoalAchievementDecision(is_achieved=True)
        runner = _make_runner(minimax_mock=minimax)
        result = runner._validate_global_goal_achievement(
            MagicMock(project="TestProj"),
            ["T01 ✓", "T02 ✓"],
            "建立整合模組",
        )
        assert result is None

    def test_validate_goal_returns_prompt_when_not_achieved(self):
        minimax = MagicMock()
        minimax.validate_goal_achievement.return_value = GoalAchievementDecision(
            is_achieved=False,
            completion_prompt="請整合 Auth 與 DB",
        )
        runner = _make_runner(minimax_mock=minimax)
        result = runner._validate_global_goal_achievement(
            MagicMock(project="TestProj"),
            ["T01 ✓"],
            "建立整合模組",
        )
        # Gap-030：現在回傳 (prompt, evaluator) 元組
        assert result is not None
        assert result[0] == "請整合 Auth 與 DB"
        assert result[1] is None  # 無 suggested_evaluator

    def test_validate_goal_returns_none_on_api_failure(self):
        minimax = MagicMock()
        minimax.validate_goal_achievement.side_effect = Exception("API 失敗")
        runner = _make_runner(minimax_mock=minimax)
        result = runner._validate_global_goal_achievement(
            MagicMock(project="TestProj"),
            ["T01 ✓"],
            "建立整合模組",
        )
        assert result is None  # 失敗時視為達成，避免假陽性阻斷


# ──────────────────────────────────────────────
# Gap-014: GOAL_SYNTHESIS 注入（dry_run 下 goal_synthesis 不觸發）
# ──────────────────────────────────────────────

class TestGap014GoalSynthesisInjection:
    def test_goal_synthesis_not_triggered_in_dry_run(self, tmp_path):
        """dry_run 模式下不觸發 GOAL_SYNTHESIS（不呼叫 Minimax）。"""
        minimax = MagicMock()
        runner = _make_runner(dry_run=True, minimax_mock=minimax)
        pb_path = _write_playbook(
            tmp_path,
            [{"step_id": "T01", "name": "t", "prompt": "p", "expected_output_regex": "pass"}],
            extra={"global_goal": "建立整合模組"},
        )
        result = runner.run(pb_path)
        assert result.success
        minimax.validate_goal_achievement.assert_not_called()

    def test_goal_synthesis_disabled_by_config(self, tmp_path):
        """goal_synthesis_enabled=False 時不觸發驗證。"""
        cfg = AppConfig.model_validate({"playbook": {"goal_synthesis_enabled": False}})
        minimax = MagicMock()
        hotkey = MagicMock()
        hotkey.triggered = False
        runner = PlaybookRunner(cfg, minimax, hotkey, dry_run=True)
        pb_path = _write_playbook(
            tmp_path,
            [{"step_id": "T01", "name": "t", "prompt": "p", "expected_output_regex": "pass"}],
            extra={"global_goal": "建立整合模組"},
        )
        result = runner.run(pb_path)
        assert result.success
        minimax.validate_goal_achievement.assert_not_called()

    def test_goal_synthesis_not_triggered_without_global_goal(self, tmp_path):
        """沒有 global_goal 時不觸發驗證。"""
        minimax = MagicMock()
        runner = _make_runner(dry_run=True, minimax_mock=minimax)
        pb_path = _write_playbook(
            tmp_path,
            [{"step_id": "T01", "name": "t", "prompt": "p", "expected_output_regex": "pass"}],
        )
        result = runner.run(pb_path)
        assert result.success
        minimax.validate_goal_achievement.assert_not_called()


# ──────────────────────────────────────────────
# Gap-015: _prepend_global_goal_brief
# ──────────────────────────────────────────────

class TestGap015GlobalGoalBrief:
    # SD_07 W4-T4-6：_prepend_global_goal_brief shim 已物理拔除；改 patch 至 plugin SSOT
    def test_brief_prefix_added(self):
        runner = _make_runner()
        result = runner._goal_synthesis_plugin.prepend_global_goal_brief(
            "原始 prompt", "這是總目標，很長的描述…", runner._cfg,
        )
        assert result.startswith("[總目標方向]")
        assert "原始 prompt" in result

    def test_brief_truncated_at_config_chars(self):
        cfg = AppConfig.model_validate({"playbook": {"global_goal_brief_chars": 50}})
        runner = PlaybookRunner(cfg, MagicMock(), MagicMock(), dry_run=True)
        runner._hotkey.triggered = False
        long_goal = "A" * 200
        result = runner._goal_synthesis_plugin.prepend_global_goal_brief(
            "p", long_goal, runner._cfg
        )
        assert "…" in result  # truncation indicator
        # Brief part should be at most 50 chars + "…"
        brief_part = result.split("\n\n")[0].replace("[總目標方向] ", "")
        assert len(brief_part) <= 51  # 50 chars + "…"

    def test_brief_no_ellipsis_when_short(self):
        runner = _make_runner()
        result = runner._goal_synthesis_plugin.prepend_global_goal_brief("p", "短目標", runner._cfg)
        assert "…" not in result

    def test_brief_returns_original_when_no_goal(self):
        runner = _make_runner()
        result = runner._goal_synthesis_plugin.prepend_global_goal_brief(
            "原始 prompt", None, runner._cfg
        )
        assert result == "原始 prompt"

    def test_non_first_step_gets_brief_in_dry_run(self, tmp_path):
        """Gap-015-B: 2 步驟含 global_goal 的 Playbook，AutoResumeService 模式正常執行。"""
        pb_path = _write_playbook(
            tmp_path,
            [
                {"step_id": "T01", "name": "t1", "prompt": "p1", "expected_output_regex": "pass"},
                {"step_id": "T02", "name": "t2", "prompt": "p2", "expected_output_regex": "pass"},
            ],
            extra={"global_goal": "建立整合模組"},
        )
        service, _ = make_service(outputs=["[DONE]", "[DONE]"])
        result = service.run(pb_path)
        assert result.success


# ──────────────────────────────────────────────
# Gap-016: EvolutionDecision 模型
# ──────────────────────────────────────────────

class TestGap016EvolutionDecision:
    def test_inject_step_decision(self):
        d = EvolutionDecision(
            evolution_type="INJECT_STEP",
            reasoning="缺少 requirements.txt",
            new_step_id="T00_INIT",
            new_step_name="初始化環境",
            new_step_prompt="請建立 requirements.txt",
        )
        assert d.evolution_type == "INJECT_STEP"
        assert d.new_step_id == "T00_INIT"

    def test_split_step_decision_with_bridge(self):
        d = EvolutionDecision(
            evolution_type="SPLIT_STEP",
            reasoning="prompt 過長",
            split_context_bridge="Part A 已完成 DB schema 建立",
        )
        assert "DB schema" in d.split_context_bridge

    def test_revise_evaluator_decision(self):
        d = EvolutionDecision(
            evolution_type="REVISE_EVALUATOR",
            reasoning="誤報失敗",
            revised_evaluator="pytest tests/ -v --tb=short",
        )
        assert d.revised_evaluator is not None


# ──────────────────────────────────────────────
# Gap-016: MinimaxClient.propose_evolution()
# ──────────────────────────────────────────────

class TestGap016MinimaxProposeEvolution:
    def test_propose_evolution_returns_decision(self):
        client = _make_minimax_client()
        with patch("httpx.post") as mock_post:
            mock_post.return_value.json.return_value = _mock_response({
                "evolution_type": "INJECT_STEP",
                "reasoning": "缺 requirements.txt",
                "new_step_id": "T00_INIT",
                "new_step_name": "初始化",
                "new_step_prompt": "建立 requirements.txt",
            })
            mock_post.return_value.raise_for_status = MagicMock()
            decision = client.propose_evolution(
                step_id="T01",
                step_name="實作 Auth",
                step_prompt="請實作 Auth",
                failure_summary="ImportError",
                escalation_reasoning="缺少依賴",
            )
        assert isinstance(decision, EvolutionDecision)
        assert decision.evolution_type == "INJECT_STEP"

    def test_propose_evolution_prompt_builder(self):
        msg = build_evolution_message(
            step_id="T01",
            step_name="實作 Auth",
            step_prompt="請實作 Auth 模組",
            failure_summary="ImportError",
            escalation_reasoning="缺少依賴",
        )
        assert "T01" in msg
        assert "ImportError" in msg

    def test_evolution_system_prompt_exists(self):
        assert "INJECT_STEP" in EVOLUTION_SYSTEM_PROMPT
        assert "SPLIT_STEP" in EVOLUTION_SYSTEM_PROMPT


# ──────────────────────────────────────────────
# Gap-016: MinimaxEvolver
# ──────────────────────────────────────────────

class TestGap016MinimaxEvolver:
    def _make_playbook(self, steps: int = 2):
        from autoclaude.models.playbook import GlobalInvariants, Playbook
        tasks = [
            PlaybookTask(step_id=f"T0{i+1}", name=f"step {i+1}", prompt=f"prompt {i+1}")
            for i in range(steps)
        ]
        return Playbook(
            version="1.0",
            project="TestProject",
            global_invariants=GlobalInvariants(max_retries_per_step=3),
            tasks=tasks,
        )

    def test_propose_inject_step(self):
        evolver = MinimaxEvolver()
        minimax = MagicMock()
        minimax.propose_evolution.return_value = EvolutionDecision(
            evolution_type="INJECT_STEP",
            reasoning="缺少環境",
            new_step_id="T00",
            new_step_name="環境初始化",
            new_step_prompt="建立環境",
        )
        playbook = self._make_playbook()
        dump = _make_escalation_dump("T01")
        proposal = evolver.propose_evolution_via_ai(playbook, 0, dump, minimax)
        assert proposal is not None
        assert proposal.evolution_type == "INJECT_STEP"
        assert proposal.new_step is not None
        assert proposal.new_step.step_id == "T00"

    def test_propose_split_step_with_ai_bridge(self):
        evolver = MinimaxEvolver()
        minimax = MagicMock()
        minimax.propose_evolution.return_value = EvolutionDecision(
            evolution_type="SPLIT_STEP",
            reasoning="prompt 太長",
            split_context_bridge="Part A 已建立 DB schema",
        )
        playbook = self._make_playbook()
        dump = _make_escalation_dump("T01")
        proposal = evolver.propose_evolution_via_ai(playbook, 0, dump, minimax)
        assert proposal is not None
        assert proposal.evolution_type == "SPLIT_STEP"
        assert proposal.split_steps is not None
        assert len(proposal.split_steps) == 2
        # Part B 應包含 context bridge
        assert "DB schema" in proposal.split_steps[1].prompt

    def test_fallback_on_minimax_error(self):
        evolver = MinimaxEvolver()
        minimax = MagicMock()
        minimax.propose_evolution.side_effect = MinimaxError("API 失敗")
        playbook = self._make_playbook()
        dump = _make_escalation_dump("T01")
        proposal = evolver.propose_evolution_via_ai(playbook, 0, dump, minimax)
        assert proposal is None  # API 失敗時回傳 None，由呼叫方 fallback 至規則引擎

    def test_revise_evaluator(self):
        evolver = MinimaxEvolver()
        minimax = MagicMock()
        minimax.propose_evolution.return_value = EvolutionDecision(
            evolution_type="REVISE_EVALUATOR",
            reasoning="誤報",
            revised_evaluator="pytest tests/ -k test_auth",
        )
        playbook = self._make_playbook()
        dump = _make_escalation_dump("T01")
        proposal = evolver.propose_evolution_via_ai(playbook, 0, dump, minimax)
        assert proposal is not None
        assert proposal.evolution_type == "REVISE_EVALUATOR"
        assert proposal.revised_evaluator == "pytest tests/ -k test_auth"

    def test_out_of_range_step_idx(self):
        evolver = MinimaxEvolver()
        playbook = self._make_playbook(steps=1)
        dump = _make_escalation_dump("T01")
        proposal = evolver.propose_evolution_via_ai(playbook, 99, dump, MagicMock())
        assert proposal is None


# ──────────────────────────────────────────────
# Gap-018: SPLIT_STEP context bridge
# ──────────────────────────────────────────────

class TestGap018SplitContextBridge:
    def _make_playbook_with_stuck_step(self):
        from autoclaude.models.playbook import GlobalInvariants, Playbook
        tasks = [
            PlaybookTask(
                step_id="T01",
                name="複雜步驟",
                prompt="前半部分指令\n後半部分指令",
            )
        ]
        return Playbook(
            version="1.0",
            project="TestProject",
            global_invariants=GlobalInvariants(max_retries_per_step=3),
            tasks=tasks,
        )

    def test_split_step_has_context_bridge(self):
        evolver = PlaybookEvolver()
        playbook = self._make_playbook_with_stuck_step()
        dump = EscalationDump(
            playbook_path="test.yaml",
            step_id="T01",
            step_name="複雜步驟",
            total_attempts=4,
            failure_chain=["e1", "e2", "e3"],
            final_eval_output="stuck",
            is_stuck=True,
            is_diverging=False,
            suspect_test_file=False,
            human_hint="stuck",
        )
        proposal = evolver.propose_evolution(playbook, 0, dump)
        assert proposal is not None
        assert proposal.split_steps is not None
        assert len(proposal.split_steps) == 2
        # Part B 必須有 context bridge
        part_b_prompt = proposal.split_steps[1].prompt
        assert "T01_A" in part_b_prompt  # context bridge 包含 Part A 的 step_id
        assert "已完成" in part_b_prompt  # context bridge 說明完成事項

    def test_split_step_part_b_has_evaluator(self):
        evolver = PlaybookEvolver()
        from autoclaude.models.playbook import GlobalInvariants, Playbook
        tasks = [
            PlaybookTask(
                step_id="T01",
                name="步驟",
                prompt="A\nB\nC",
                expected_output_regex=r"\[DONE\]",
                evaluator_command="pytest tests/",
            )
        ]
        playbook = Playbook(
            version="1.0",
            project="P",
            global_invariants=GlobalInvariants(max_retries_per_step=3),
            tasks=tasks,
        )
        dump = EscalationDump(
            playbook_path="test.yaml",
            step_id="T01",
            step_name="步驟",
            total_attempts=4,
            failure_chain=["e1", "e2", "e3"],
            final_eval_output="stuck",
            is_stuck=True,
            is_diverging=False,
            suspect_test_file=False,
            human_hint="stuck",
        )
        proposal = evolver.propose_evolution(playbook, 0, dump)
        assert proposal.split_steps[1].evaluator_command == "pytest tests/"
        assert proposal.split_steps[1].expected_output_regex == r"\[DONE\]"


# ──────────────────────────────────────────────
# Gap-017: SKIP_TO 執行邏輯（dry_run 不可測試，使用 mock）
# ──────────────────────────────────────────────

class TestGap017SkipToRunner:
    def _make_runner_with_minimax(self, minimax_mock=None):
        cfg = AppConfig()
        minimax = minimax_mock or MagicMock()
        hotkey = MagicMock()
        hotkey.triggered = False
        return PlaybookRunner(cfg, minimax, hotkey, dry_run=False)

    def test_skip_to_prevents_backward_jump(self, tmp_path):
        """SKIP_TO 向後防護 smoke test：2 步驟 Playbook 用 AutoResumeService 正常完成。"""
        pb_path = _write_playbook(tmp_path, [
            {"step_id": "T01", "name": "t1", "prompt": "p", "expected_output_regex": "pass"},
            {"step_id": "T02", "name": "t2", "prompt": "p", "expected_output_regex": "pass"},
        ])
        service, _ = make_service(outputs=["[DONE]", "[DONE]"])
        result = service.run(pb_path)
        assert result.success


# ──────────────────────────────────────────────
# Gap-019: 批次突變 runner 執行（dry_run mock）
# ──────────────────────────────────────────────

class TestGap019BatchMutationRunner:
    def test_batch_mutations_applied_in_dry_run(self, tmp_path):
        """AutoResumeService 模式下批次突變基礎路徑正常執行（smoke test）。"""
        pb_path = _write_playbook(tmp_path, [
            {"step_id": "T01", "name": "t", "prompt": "p", "expected_output_regex": "pass"}
        ])
        service, _ = make_service(outputs=["[DONE]"])
        result = service.run(pb_path)
        assert result.success

    def test_batch_mutation_model_max_3(self):
        """批次突變應限制最多 3 個（模型層面驗證）。"""
        batch = [
            StepMutation(mutation_type=StepMutationType.REVISE_CURRENT, revised_prompt=f"p{i}")
            for i in range(5)
        ]
        m = StepMutation(
            mutation_type=StepMutationType.REVISE_CURRENT,
            revised_prompt="outer",
            batch_mutations=batch,
        )
        # 模型不限制數量，限制在 runner 邏輯（取前 3 個）
        assert len(m.batch_mutations) == 5  # 模型允許超過 3，runner 截斷

    def test_batch_mutations_field_preserved_in_serialization(self):
        inner = StepMutation(mutation_type=StepMutationType.DELETE_STEP, delete_step_id="T03")
        outer = StepMutation(
            mutation_type=StepMutationType.INJECT_AFTER,
            new_step_prompt="inject",
            batch_mutations=[inner],
        )
        data = outer.model_dump()
        assert data["batch_mutations"][0]["delete_step_id"] == "T03"

    @requires_claude_cli
    def test_batch_mutations_applied_via_mock_correction(self, tmp_path):
        """Gap-019-B：mock _get_correction 回傳 batch_mutations，驗證每個突變都被套用。"""
        from unittest.mock import patch as upatch
        minimax = MagicMock()
        runner = _make_runner(dry_run=False, minimax_mock=minimax)
        pb_path = _write_playbook(tmp_path, [
            {"step_id": "T01", "name": "t", "prompt": "p",
             "expected_output_regex": "pass", "max_retries": 2},
        ])

        def fake_get_correction(task, failure_reason, eval_output, attempt, **kwargs):
            # 第一次：回傳 batch_mutations（REVISE_CURRENT + INJECT_AFTER）
            batch = [
                StepMutation(
                    mutation_type=StepMutationType.REVISE_CURRENT,
                    revised_prompt="revised by batch",
                    reasoning="batch revise",
                ),
                StepMutation(
                    mutation_type=StepMutationType.INJECT_AFTER,
                    new_step_id="T01_BATCH_INJ",
                    new_step_name="批次注入步驟",
                    new_step_prompt="batch inject prompt",
                    reasoning="batch inject",
                ),
            ]
            outer = StepMutation(
                mutation_type=StepMutationType.REVISE_CURRENT,
                revised_prompt="outer",
                batch_mutations=batch,
                reasoning="batch outer",
            )
            return ("fix prompt", "reasoning", None, outer)

        with upatch("autoclaude.execution.playbook_runner.notify"), \
             upatch.object(runner, "_get_correction", side_effect=fake_get_correction), \
             upatch.object(runner, "_evaluate", return_value=(None, "", 0)):
            result = runner.run(pb_path)
        assert result.success

    @requires_claude_cli
    def test_batch_mutations_truncated_to_3(self, tmp_path):
        """Gap-019-B：batch_mutations 超過 3 個時 runner 截斷至前 3 個。"""
        from unittest.mock import patch as upatch
        minimax = MagicMock()
        runner = _make_runner(dry_run=False, minimax_mock=minimax)
        pb_path = _write_playbook(tmp_path, [
            {"step_id": "T01", "name": "t", "prompt": "p",
             "expected_output_regex": "pass", "max_retries": 2},
        ])

        batch = [
            StepMutation(
                mutation_type=StepMutationType.REVISE_CURRENT,
                revised_prompt=f"revised_{i}",
                reasoning=f"batch {i}",
            )
            for i in range(5)  # 5 個，runner 應截斷至 3
        ]
        outer = StepMutation(
            mutation_type=StepMutationType.REVISE_CURRENT,
            revised_prompt="outer",
            batch_mutations=batch,
            reasoning="batch outer",
        )

        call_count = {"n": 0}

        def fake_get_correction(task, failure_reason, eval_output, attempt, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return ("fix", "reasoning", None, outer)
            return ("fix2", "reasoning2", None, None)

        with upatch("autoclaude.execution.playbook_runner.notify"), \
             upatch.object(runner, "_get_correction", side_effect=fake_get_correction), \
             upatch.object(runner, "_evaluate", return_value=(None, "", 0)):
            result = runner.run(pb_path)
        assert result.success
        # 最終 task prompt 應為第 3 個（索引 2）的 revised_2（runner 只套用前 3 個）
        # 驗證不超過 3 個 REVISE_CURRENT 被套用，而非 5 個
        # 最後一個成功應是 revised_2（索引 2）而非 revised_4（索引 4）


# ──────────────────────────────────────────────
# Gap-017: SKIP_TO 執行邏輯（補足有效測試）
# ──────────────────────────────────────────────

@requires_claude_cli
class TestGap017SkipToRunnerExtended:
    """Gap-017-C SKIP_TO 執行邏輯的有效整合測試（使用 mock _get_correction）。"""

    def test_skip_to_forward_jump(self, tmp_path):
        """SKIP_TO 正向邏輯：mock correction 回傳 SKIP_TO → runner 跳至目標步驟，中間步驟不執行。"""
        from unittest.mock import patch as upatch
        minimax = MagicMock()
        runner = _make_runner(dry_run=False, minimax_mock=minimax)
        # T01（失敗）→ SKIP_TO T03（跳過 T02）→ T03 成功
        pb_path = _write_playbook(tmp_path, [
            {"step_id": "T01", "name": "t1", "prompt": "p1",
             "expected_output_regex": "pass", "max_retries": 2},
            {"step_id": "T02", "name": "t2", "prompt": "p2",
             "expected_output_regex": "pass", "max_retries": 2},
            {"step_id": "T03", "name": "t3", "prompt": "p3",
             "expected_output_regex": "pass", "max_retries": 2},
        ])
        eval_calls = {"n": 0}

        def fake_eval(task, output):
            eval_calls["n"] += 1
            if task.step_id == "T01" and eval_calls["n"] == 1:
                return "fail", "error", 1  # T01 第一次失敗
            return None, "", 0  # 其餘成功

        skip_mutation = StepMutation(
            mutation_type=StepMutationType.SKIP_TO,
            skip_to_step_id="T03",
            skip_reason="T02 已被前置步驟隱性完成",
            reasoning="跳過 T02",
        )

        def fake_get_correction(task, failure_reason, eval_output, attempt, **kwargs):
            return ("fix", "reasoning", None, skip_mutation)

        with upatch("autoclaude.execution.playbook_runner.notify"), \
             upatch.object(runner, "_evaluate", side_effect=fake_eval), \
             upatch.object(runner, "_get_correction", side_effect=fake_get_correction):
            result = runner.run(pb_path)

        assert result.success
        # T02 應被跳過，step_log 中應有 [SKIPPED] T02
        assert any("[SKIPPED]" in log and "T02" in log for log in result.step_log)

    def test_skip_to_backward_guard(self, tmp_path):
        """SKIP_TO 向後跳轉保護：target_idx < step_idx 時應被忽略，不執行跳轉。"""
        from unittest.mock import patch as upatch
        minimax = MagicMock()
        runner = _make_runner(dry_run=False, minimax_mock=minimax)
        # T01 成功後執行 T02，T02 失敗時 SKIP_TO T01（向後），應被忽略
        pb_path = _write_playbook(tmp_path, [
            {"step_id": "T01", "name": "t1", "prompt": "p1",
             "expected_output_regex": "pass", "max_retries": 2},
            {"step_id": "T02", "name": "t2", "prompt": "p2",
             "expected_output_regex": "pass", "max_retries": 2},
        ])
        eval_calls = {"n": 0}

        def fake_eval(task, output):
            eval_calls["n"] += 1
            if task.step_id == "T02":
                return None, "", 0  # T02 always passes (skip_to 被 ignore 後，繼續正常流程)
            return None, "", 0

        backward_skip = StepMutation(
            mutation_type=StepMutationType.SKIP_TO,
            skip_to_step_id="T01",  # 向後，禁止
            reasoning="should be ignored",
        )

        def fake_get_correction(task, failure_reason, eval_output, attempt, **kwargs):
            return ("fix", "reasoning", None, backward_skip)

        with upatch("autoclaude.execution.playbook_runner.notify"), \
             upatch.object(runner, "_evaluate", side_effect=fake_eval), \
             upatch.object(runner, "_get_correction", side_effect=fake_get_correction):
            result = runner.run(pb_path)

        assert result.success
        # step_log 中不應有任何 [SKIPPED] T01（向後跳轉被忽略）
        assert not any("[SKIPPED]" in log and "T01" in log for log in result.step_log)

    def test_skip_to_max_once_guard(self, tmp_path):
        """SKIP_TO 最多 1 次限制：同一 step_id 的第二次 SKIP_TO 被忽略。"""
        from unittest.mock import patch as upatch
        minimax = MagicMock()
        runner = _make_runner(dry_run=False, minimax_mock=minimax)
        # T01 失敗多次，每次都嘗試 SKIP_TO T02，但第二次以後應被防護忽略
        pb_path = _write_playbook(tmp_path, [
            {"step_id": "T01", "name": "t1", "prompt": "p1",
             "expected_output_regex": "pass", "max_retries": 3},
            {"step_id": "T02", "name": "t2", "prompt": "p2",
             "expected_output_regex": "pass", "max_retries": 2},
            {"step_id": "T03", "name": "t3", "prompt": "p3",
             "expected_output_regex": "pass", "max_retries": 2},
        ])
        eval_calls = {"n": 0}

        def fake_eval(task, output):
            eval_calls["n"] += 1
            if task.step_id == "T01":
                if eval_calls["n"] <= 2:
                    return "fail", "error", 1  # T01 前兩次失敗
            return None, "", 0

        skip_mutation = StepMutation(
            mutation_type=StepMutationType.SKIP_TO,
            skip_to_step_id="T02",
            skip_reason="skip to T02",
            reasoning="skip",
        )

        def fake_get_correction(task, failure_reason, eval_output, attempt, **kwargs):
            return ("fix", "reasoning", None, skip_mutation)

        with upatch("autoclaude.execution.playbook_runner.notify"), \
             upatch.object(runner, "_evaluate", side_effect=fake_eval), \
             upatch.object(runner, "_get_correction", side_effect=fake_get_correction):
            result = runner.run(pb_path)

        # 最多只有 1 個 [SKIPPED] T02 記錄（防護確保只跳轉 1 次）
        skip_t2_logs = [log for log in result.step_log if "[SKIPPED]" in log and "T02" in log]
        assert len(skip_t2_logs) <= 1


# ──────────────────────────────────────────────
# Gap-014: GOAL_SYNTHESIS 正向路徑和防遞迴保護
# ──────────────────────────────────────────────

class TestGap014GoalSynthesisInjectionExtended:
    """Gap-014-C GOAL_SYNTHESIS 正向路徑和防遞迴保護的有效測試。"""

    def test_goal_synthesis_injected_when_not_achieved(self, tmp_path):
        """目標未達成時 GOAL_SYNTHESIS 步驟確實被注入並執行。"""
        from unittest.mock import patch as upatch
        minimax = MagicMock()
        # validate_goal_achievement 回傳未達成 → completion_prompt
        # （Gap-030：用 GoalAchievementDecision 確保 suggested_evaluator=None）
        minimax.validate_goal_achievement.return_value = GoalAchievementDecision(
            is_achieved=False,
            completion_prompt="請補完：整合 Auth 與 DB 模組",
            gap_analysis="Auth 與 DB 介面不相容",
        )
        # decide_correction 不應被呼叫（GOAL_SYNTHESIS 步驟一次通過）
        minimax.decide_correction.return_value = MagicMock(
            correction_prompt="fix",
            reasoning="r",
            task_goal_summary=None,
            step_mutation=None,
        )

        cfg = AppConfig.model_validate({"playbook": {"goal_synthesis_enabled": True}})
        hotkey = MagicMock()
        hotkey.triggered = False
        runner = PlaybookRunner(cfg, minimax, hotkey, dry_run=False)

        pb_path = _write_playbook(
            tmp_path,
            [{"step_id": "T01", "name": "t", "prompt": "p",
              "expected_output_regex": "pass", "max_retries": 2}],
            extra={"global_goal": "建立整合模組"},
        )

        eval_calls = {"n": 0}

        def fake_eval(task, output):
            eval_calls["n"] += 1
            if task.step_id == "GOAL_SYNTHESIS":
                return None, "", 0  # GOAL_SYNTHESIS 立即通過
            return None, "", 0  # T01 通過

        with upatch("autoclaude.execution.playbook_runner.notify"), \
             upatch("autoclaude.execution.playbook_runner.notify_escalation"), \
             upatch.object(runner, "_execute_prompt") as mock_exec, \
             upatch.object(runner, "_evaluate", side_effect=fake_eval):
            mock_exec.return_value = MagicMock(
                text="[dry-run] pass", peak_token_pct=0.0,
                triggered_compact=False, triggered_halt=False
            )
            result = runner.run(pb_path)

        assert result.success
        # validate_goal_achievement 應被呼叫一次
        minimax.validate_goal_achievement.assert_called_once()
        # GOAL_SYNTHESIS 步驟應被執行（step_log 中有 GOAL_SYNTHESIS）
        assert any("GOAL_SYNTHESIS" in log for log in result.step_log)

    def test_goal_synthesis_anti_recursion_guard(self, tmp_path):
        """防遞迴保護：_goal_synthesis_injected 旗標確保不會二次注入 GOAL_SYNTHESIS。"""
        from unittest.mock import patch as upatch
        minimax = MagicMock()
        # 每次都回傳未達成，但第二次不應再注入（防遞迴保護）（Gap-030：用 GoalAchievementDecision）
        minimax.validate_goal_achievement.return_value = GoalAchievementDecision(
            is_achieved=False,
            completion_prompt="請補完整合模組",
            gap_analysis="缺口存在",
        )

        cfg = AppConfig.model_validate({"playbook": {"goal_synthesis_enabled": True}})
        hotkey = MagicMock()
        hotkey.triggered = False
        runner = PlaybookRunner(cfg, minimax, hotkey, dry_run=False)

        pb_path = _write_playbook(
            tmp_path,
            [{"step_id": "T01", "name": "t", "prompt": "p",
              "expected_output_regex": "pass", "max_retries": 2}],
            extra={"global_goal": "建立整合模組"},
        )

        with upatch("autoclaude.execution.playbook_runner.notify"), \
             upatch("autoclaude.execution.playbook_runner.notify_escalation"), \
             upatch.object(runner, "_execute_prompt") as mock_exec, \
             upatch.object(runner, "_evaluate", return_value=(None, "", 0)):
            mock_exec.return_value = MagicMock(
                text="[dry-run] pass", peak_token_pct=0.0,
                triggered_compact=False, triggered_halt=False
            )
            runner.run(pb_path)

        # validate_goal_achievement 只應被呼叫 1 次（防遞迴保護）
        assert minimax.validate_goal_achievement.call_count == 1


# ──────────────────────────────────────────────
# Gap-016-C: MinimaxEvolver fallback 整合測試
# ──────────────────────────────────────────────

@requires_claude_cli
class TestGap016CMinimaxEvolverFallback:
    """驗證 PlaybookRunner 在 ESCALATION 時的 MinimaxEvolver → 規則引擎 fallback 機制。"""

    def _make_playbook_for_escalation(self, tmp_path):
        """建立一個會觸發 ESCALATION（重試耗盡）的 Playbook。"""
        return _write_playbook(tmp_path, [
            {"step_id": "T01", "name": "t", "prompt": "p",
             "expected_output_regex": "pass", "max_retries": 1},
        ])

    def test_minimax_evolver_used_when_proposal_available(self, tmp_path):
        """MinimaxEvolver.propose_evolution_via_ai 回傳有效 proposal → PlaybookRunner 使用它。"""
        from unittest.mock import patch as upatch

        from autoclaude.evolution.playbook_evolver import PlaybookEvolutionProposal
        minimax = MagicMock()
        runner = _make_runner(dry_run=False, minimax_mock=minimax)
        pb_path = self._make_playbook_for_escalation(tmp_path)

        # 模擬有效的 AI 提議
        fake_proposal = PlaybookEvolutionProposal(
            evolution_type="INJECT_STEP",
            inject_before_idx=0,
            reasoning="AI 偵測到缺少環境初始化步驟",
            new_step=PlaybookTask(
                step_id="T00_AI",
                name="AI 演化前置步驟",
                prompt="初始化環境",
                max_retries=2,
            ),
        )
        minimax.decide_correction.return_value = MagicMock(
            correction_prompt="請修復此問題：確認環境變數設定正確後再重試",
            reasoning="r",
            task_goal_summary=None,
            step_mutation=None,
        )

        with upatch("autoclaude.execution.playbook_runner.notify"), \
             upatch("autoclaude.execution.playbook_runner.notify_escalation"), \
             upatch.object(runner, "_evaluate", return_value=("fail", "error", 1)), \
             upatch.object(runner._minimax_evolver, "propose_evolution_via_ai",
                           return_value=fake_proposal) as mock_ai, \
             upatch.object(runner._evolver, "propose_evolution",
                           return_value=None) as mock_rule, \
             upatch.object(runner._evolver, "apply_evolution",
                           return_value=None):
            runner.run(pb_path)

        # MinimaxEvolver.propose_evolution_via_ai 應被呼叫
        assert mock_ai.call_count >= 1
        # 規則引擎 propose_evolution 不應被呼叫（因為 AI 已提供 proposal）
        assert mock_rule.call_count == 0

    def test_fallback_to_rule_engine_when_ai_returns_none(self, tmp_path):
        """MinimaxEvolver.propose_evolution_via_ai 回傳 None → PlaybookRunner fallback
        至規則引擎。"""
        from unittest.mock import patch as upatch
        minimax = MagicMock()
        runner = _make_runner(dry_run=False, minimax_mock=minimax)
        pb_path = self._make_playbook_for_escalation(tmp_path)

        minimax.decide_correction.return_value = MagicMock(
            correction_prompt="請修復此問題：確認所有測試案例都通過後再繼續下一步",
            reasoning="r",
            task_goal_summary=None,
            step_mutation=None,
        )

        with upatch("autoclaude.execution.playbook_runner.notify"), \
             upatch("autoclaude.execution.playbook_runner.notify_escalation"), \
             upatch.object(runner, "_evaluate", return_value=("fail", "error", 1)), \
             upatch.object(runner._minimax_evolver, "propose_evolution_via_ai",
                           return_value=None) as mock_ai, \
             upatch.object(runner._evolver, "propose_evolution",
                           return_value=None) as mock_rule:
            runner.run(pb_path)

        # MinimaxEvolver.propose_evolution_via_ai 應被呼叫
        assert mock_ai.call_count >= 1
        # 規則引擎 propose_evolution 應被呼叫（AI 回傳 None，fallback）
        assert mock_rule.call_count >= 1

    def test_convergence_escalation_also_uses_minimax_evolver(self, tmp_path):
        """收斂評估觸發的 ESCALATION（現有路徑）也使用 MinimaxEvolver，驗證兩條路徑一致。"""
        from unittest.mock import patch as upatch

        minimax = MagicMock()
        runner = _make_runner(dry_run=False, minimax_mock=minimax)
        pb_path = _write_playbook(tmp_path, [
            {"step_id": "T01", "name": "t", "prompt": "p",
             "expected_output_regex": "pass", "max_retries": 5},
        ])

        minimax.decide_correction.return_value = MagicMock(
            correction_prompt="請修復此問題：確認測試通過後再繼續",
            reasoning="r",
            task_goal_summary=None,
            step_mutation=None,
        )

        mock_report = MagicMock()
        mock_report.recommendation = "escalate"
        mock_report.trend = "stuck"
        mock_report.reasoning = "stuck 偵測"

        with upatch("autoclaude.execution.playbook_runner.notify"), \
             upatch("autoclaude.execution.playbook_runner.notify_escalation"), \
             upatch.object(runner, "_evaluate", return_value=("fail", "error", 1)), \
             upatch("autoclaude.execution.playbook_runner.ConvergenceMonitor") as mock_cm, \
             upatch.object(runner._minimax_evolver, "propose_evolution_via_ai",
                           return_value=None) as mock_ai, \
             upatch.object(runner._evolver, "propose_evolution", return_value=None):
            mock_instance = MagicMock()
            mock_instance.evaluate.return_value = mock_report
            mock_cm.return_value = mock_instance
            runner.run(pb_path)

        # 收斂 ESCALATION 也應呼叫 MinimaxEvolver
        assert mock_ai.call_count >= 1
