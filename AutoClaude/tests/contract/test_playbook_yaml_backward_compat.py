"""SD_Improving_05 W2 — Playbook YAML backward-compat + per-step token_guard 契約測試。

驗證：
  1. 既有 Playbook YAML（scripts/example_playbook.yaml / tests/fixtures/mock_playbook.yaml）
     在 PlaybookTask 加入 `token_guard: Optional[dict]` 欄位後仍可正常載入
  2. per-step token_guard override 優先序（M-7）：task.token_guard > global cfg
  3. 各種 override 場景（部分欄位 / 全欄位 / 空 dict / None）
  4. resolve_per_step_cfg 驗證錯誤 cfg 拒絕（如 halt < compact）

對應 SD_05 §6.1 namespace 規範 + §8.2 G2 阻塞條件
（test_playbook_yaml_backward_compat.py 60+ YAML 載入 + per-step override 優先序 AC）。
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from autoclaude.models.playbook import Playbook, PlaybookTask
from autoclaude.plugins.token_guard_plugin import TokenGuardPlugin
from autoclaude.utils.config import TokenGuardConfig


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ─────────────────────────────────────────────────────────────
# 1. YAML schema backward compat（新 token_guard 欄位不破壞舊 YAML）
# ─────────────────────────────────────────────────────────────
class TestPlaybookTaskSchemaBackwardCompat:
    def test_task_without_token_guard_field_loads(self):
        """既有 PlaybookTask（無 token_guard 欄位）必須仍可建構。"""
        task = PlaybookTask(
            step_id="T01", name="legacy", prompt="do something",
        )
        assert task.token_guard is None

    def test_task_with_full_fields_loads(self):
        """完整既有 PlaybookTask 欄位仍正常。"""
        task = PlaybookTask(
            step_id="T01", name="full", prompt="p",
            command=None,
            expected_output_regex="\\[DONE\\]",
            evaluator_command="pytest",
            max_retries=3,
            maintain_context=True,
            evaluator_timeout_seconds=60,
        )
        assert task.token_guard is None
        assert task.max_retries == 3

    def test_task_with_token_guard_override(self):
        """新功能：可設定 token_guard override。"""
        task = PlaybookTask(
            step_id="T01", name="t", prompt="p",
            token_guard={"compact_threshold_pct": 70.0, "halt_threshold_pct": 85.0},
        )
        assert task.token_guard == {"compact_threshold_pct": 70.0, "halt_threshold_pct": 85.0}

    @pytest.mark.parametrize("yaml_path", [
        "scripts/example_playbook.yaml",
        "tests/fixtures/mock_playbook.yaml",
    ])
    def test_existing_playbook_yaml_loads(self, yaml_path):
        """既有生產 / fixture Playbook YAML 必須在 schema 變更後仍正常載入。"""
        path = PROJECT_ROOT / yaml_path
        if not path.exists():
            pytest.skip(f"{yaml_path} 不存在")
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        pb = Playbook(**data)
        assert pb.project
        assert len(pb.tasks) > 0
        # 所有現有 task 的 token_guard 必為 None（未設定）
        for task in pb.tasks:
            assert task.token_guard is None, (
                f"既有 YAML {yaml_path} step {task.step_id} 不應有 token_guard 欄位"
            )

    def test_yaml_with_token_guard_override_loads(self, tmp_path):
        """新版 YAML（含 token_guard override）載入無誤。"""
        yaml_content = """
version: "1.0"
project: "TEST"
global_invariants:
  max_retries_per_step: 3
tasks:
  - step_id: T01
    name: "setup（高門檻）"
    prompt: "install deps"
    token_guard:
      compact_threshold_pct: 85.0
      halt_threshold_pct: 95.0
  - step_id: T02
    name: "codegen（低門檻）"
    prompt: "generate code"
    token_guard:
      compact_threshold_pct: 70.0
      halt_threshold_pct: 85.0
  - step_id: T03
    name: "test（無 override）"
    prompt: "pytest"
"""
        p = tmp_path / "x.yaml"
        p.write_text(yaml_content, encoding="utf-8")
        with p.open(encoding="utf-8") as f:
            pb = Playbook(**yaml.safe_load(f))
        assert pb.tasks[0].token_guard["compact_threshold_pct"] == 85.0
        assert pb.tasks[1].token_guard["halt_threshold_pct"] == 85.0
        assert pb.tasks[2].token_guard is None


# ─────────────────────────────────────────────────────────────
# 2. per-step token_guard override 優先序（M-7）
# ─────────────────────────────────────────────────────────────
class TestPerStepTokenGuardPriority:
    def test_no_task_returns_global_cfg(self):
        global_cfg = TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        plugin = TokenGuardPlugin(token_guard_cfg=global_cfg)
        assert plugin.resolve_per_step_cfg(task=None) is global_cfg

    def test_task_without_override_returns_global(self):
        global_cfg = TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        plugin = TokenGuardPlugin(token_guard_cfg=global_cfg)
        task = PlaybookTask(step_id="T01", name="n", prompt="p")
        assert plugin.resolve_per_step_cfg(task) is global_cfg

    def test_task_full_override(self):
        global_cfg = TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        plugin = TokenGuardPlugin(token_guard_cfg=global_cfg)
        task = PlaybookTask(
            step_id="T01", name="n", prompt="p",
            token_guard={"compact_threshold_pct": 70.0, "halt_threshold_pct": 85.0},
        )
        resolved = plugin.resolve_per_step_cfg(task)
        assert resolved.compact_threshold_pct == 70.0
        assert resolved.halt_threshold_pct == 85.0
        # global 未變
        assert global_cfg.compact_threshold_pct == 80.0

    def test_task_partial_override(self):
        """只覆寫一個欄位，其餘繼承 global。"""
        global_cfg = TokenGuardConfig(
            compact_threshold_pct=80.0, halt_threshold_pct=90.0, enabled=True,
        )
        plugin = TokenGuardPlugin(token_guard_cfg=global_cfg)
        task = PlaybookTask(
            step_id="T01", name="n", prompt="p",
            token_guard={"compact_threshold_pct": 75.0},
        )
        resolved = plugin.resolve_per_step_cfg(task)
        assert resolved.compact_threshold_pct == 75.0
        assert resolved.halt_threshold_pct == 90.0  # 繼承 global
        assert resolved.enabled is True

    def test_task_empty_override_returns_global(self):
        """空 dict override 視為無 override。"""
        global_cfg = TokenGuardConfig(compact_threshold_pct=80.0)
        plugin = TokenGuardPlugin(token_guard_cfg=global_cfg)
        task = PlaybookTask(
            step_id="T01", name="n", prompt="p",
            token_guard={},
        )
        assert plugin.resolve_per_step_cfg(task) is global_cfg

    def test_invalid_override_raises(self):
        """halt < compact override 必須被 TokenGuardConfig validator 攔下。"""
        global_cfg = TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        plugin = TokenGuardPlugin(token_guard_cfg=global_cfg)
        task = PlaybookTask(
            step_id="T01", name="n", prompt="p",
            token_guard={"halt_threshold_pct": 70.0},  # 低於 compact 80
        )
        with pytest.raises(Exception):
            plugin.resolve_per_step_cfg(task)


# ─────────────────────────────────────────────────────────────
# 3. W1 setup 高門檻 / W3 codegen 低門檻 情境 (SD_05 §3 W2-4)
# ─────────────────────────────────────────────────────────────
class TestRealisticPerStepProfiles:
    def test_w1_setup_high_threshold(self):
        """W1 setup 步驟可設較高 compact_threshold（容忍長輸出）。"""
        global_cfg = TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        plugin = TokenGuardPlugin(token_guard_cfg=global_cfg)
        setup_task = PlaybookTask(
            step_id="W1_SETUP", name="install deps", prompt="...",
            token_guard={"compact_threshold_pct": 85.0, "halt_threshold_pct": 95.0},
        )
        cfg = plugin.resolve_per_step_cfg(setup_task)
        assert cfg.compact_threshold_pct == 85.0
        assert cfg.halt_threshold_pct == 95.0

    def test_w3_codegen_low_threshold(self):
        """W3 codegen 步驟可設較低 compact_threshold（高重試壓力下提前清）。"""
        global_cfg = TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        plugin = TokenGuardPlugin(token_guard_cfg=global_cfg)
        codegen_task = PlaybookTask(
            step_id="W3_CODEGEN", name="generate", prompt="...",
            token_guard={"compact_threshold_pct": 70.0, "halt_threshold_pct": 85.0},
        )
        cfg = plugin.resolve_per_step_cfg(codegen_task)
        assert cfg.compact_threshold_pct == 70.0
        assert cfg.halt_threshold_pct == 85.0


# ─────────────────────────────────────────────────────────────
# 4. M-2 雙寫拔除合約測試
# ─────────────────────────────────────────────────────────────
class TestM2DualWriteEliminated:
    """SD_05 §2 M-2：_consecutive_compact_failures vs _compact_failure_count 雙寫拔除。

    SD_07 W4-T4-4：原 PlaybookRunner._consecutive_compact_failures property + setter
    已物理拔除；compact_failure 計數器 SSOT 唯一為 TokenGuardPlugin._compact_failure_count。
    本 class 保留純 plugin SSOT 行為驗證；原 `test_runner_property_delegates_to_plugin`
    backward compat 保護網 test 隨 property 一併移除（SD_07 W4 紅線 ❌15）。
    """

    def test_plugin_is_compact_failure_ssot(self):
        plugin = TokenGuardPlugin()
        assert plugin._compact_failure_count == 0
        plugin.record_compact_failure()
        plugin.record_compact_failure()
        assert plugin._compact_failure_count == 2
        plugin.reset_compact_failure()
        assert plugin._compact_failure_count == 0

    def test_process_compact_result_increment_on_failure(self):
        plugin = TokenGuardPlugin()
        ok = plugin.process_compact_result(triggered_compact=True, peak_token_pct=85.0)
        assert plugin._compact_failure_count == 1
        assert ok is True  # 第 1 次失敗仍允許
        ok = plugin.process_compact_result(triggered_compact=True, peak_token_pct=85.0)
        assert plugin._compact_failure_count == 2
        assert ok is False  # 第 2 次失敗達 critical

    def test_process_compact_result_reset_on_success(self):
        plugin = TokenGuardPlugin()
        plugin.record_compact_failure()
        assert plugin._compact_failure_count == 1
        # compact 成功 → triggered_compact=False
        ok = plugin.process_compact_result(triggered_compact=False, peak_token_pct=40.0)
        assert plugin._compact_failure_count == 0
        assert ok is True

# ─────────────────────────────────────────────────────────────
# 5. W2 三方審查 SA-C1：3 個新 plugin 方法補測試
# ─────────────────────────────────────────────────────────────
class TestBuildCompactPrompt:
    """SD_05 W2-1d：build_compact_prompt 純函式（W2 SA-C1 補測）。"""

    def test_basic_compact_prompt(self):
        plugin = TokenGuardPlugin()
        prompt = plugin.build_compact_prompt(task=None, attempt=0)
        assert "/compact" in prompt
        assert "MEMORY ANCHOR" not in prompt  # task=None 不附 anchor

    def test_compact_prompt_with_task_anchor(self):
        plugin = TokenGuardPlugin()
        task = PlaybookTask(
            step_id="T01", name="step one", prompt="p",
            expected_output_regex=r"\[DONE\]",
        )
        prompt = plugin.build_compact_prompt(task=task, attempt=2)
        assert "MEMORY ANCHOR" in prompt
        assert "[ACTIVE_TASK] T01: step one" in prompt
        assert "[ATTEMPT] 3" in prompt
        assert "[SUCCESS_CONDITION]" in prompt

    def test_compact_prompt_with_global_goal_truncation(self):
        plugin = TokenGuardPlugin()
        task = PlaybookTask(step_id="T01", name="n", prompt="p")
        long_goal = "X" * 500
        prompt = plugin.build_compact_prompt(
            task=task, attempt=0, global_goal=long_goal,
            global_goal_anchor_chars=100,
        )
        assert "[GLOBAL_GOAL]" in prompt
        # 截斷 + ellipsis
        assert "X" * 100 + "…" in prompt
        assert "X" * 101 not in prompt  # 不應超過 100 個 X

    def test_compact_prompt_with_failure_summary(self):
        plugin = TokenGuardPlugin()
        task = PlaybookTask(step_id="T01", name="n", prompt="p")
        prompt = plugin.build_compact_prompt(
            task=task, attempt=1, failure_summary="line1\nFinal error: assertion",
        )
        assert "[LAST_FAILURE] Final error: assertion" in prompt
        # failure_summary 整體也附在 prompt 末
        assert "壓縮後必須記住" in prompt


class TestObserveTokenLine:
    """SD_05 W2-1e：observe_token_line 純函式（W2 SA-C1 + SD-Minor 邊界）。"""

    def test_pct_none_no_update(self):
        plugin = TokenGuardPlugin()
        peak, c, h = plugin.observe_token_line(
            pct=None, peak_pct=50.0, triggered_compact=False, triggered_halt=False,
        )
        assert peak == 50.0
        assert c is False
        assert h is False

    def test_pct_equal_peak_no_update(self):
        """SD-Minor 邊界：pct == peak_pct 不應觸發更新。"""
        plugin = TokenGuardPlugin()
        peak, c, h = plugin.observe_token_line(
            pct=50.0, peak_pct=50.0, triggered_compact=False, triggered_halt=False,
        )
        assert peak == 50.0

    def test_pct_below_peak_no_update(self):
        plugin = TokenGuardPlugin()
        peak, c, h = plugin.observe_token_line(
            pct=40.0, peak_pct=50.0, triggered_compact=False, triggered_halt=False,
        )
        assert peak == 50.0

    def test_pct_above_halt_triggers_halt(self):
        plugin = TokenGuardPlugin(TokenGuardConfig(
            compact_threshold_pct=80.0, halt_threshold_pct=90.0,
        ))
        peak, c, h = plugin.observe_token_line(
            pct=95.0, peak_pct=80.0, triggered_compact=False, triggered_halt=False,
        )
        assert peak == 95.0
        assert h is True
        assert c is False  # halt 優先，未觸發 compact

    def test_pct_between_compact_and_halt_triggers_compact(self):
        plugin = TokenGuardPlugin(TokenGuardConfig(
            compact_threshold_pct=80.0, halt_threshold_pct=90.0,
        ))
        peak, c, h = plugin.observe_token_line(
            pct=85.0, peak_pct=70.0, triggered_compact=False, triggered_halt=False,
        )
        assert peak == 85.0
        assert c is True
        assert h is False

    def test_existing_triggered_preserved(self):
        """若已 triggered，後續 pct 增長保留 triggered 旗標。"""
        plugin = TokenGuardPlugin()
        peak, c, h = plugin.observe_token_line(
            pct=85.0, peak_pct=82.0, triggered_compact=True, triggered_halt=False,
        )
        assert c is True  # 保留前次 triggered


class TestVerifyCorrectionApplied:
    """SD_05 W2-1c：verify_correction_applied (W2 SA-C1 補測)。"""

    def test_attempt_zero_returns_none(self):
        plugin = TokenGuardPlugin()
        assert plugin.verify_correction_applied(attempt=0) is None

    def test_subprocess_error_returns_none(self, monkeypatch):
        """git 不存在或 subprocess 例外 → 回傳 None（容錯）。

        SD_06 W2-T2-13：subprocess 已搬至 token_guard.git_verifier；patch path 同步遷移。
        """
        plugin = TokenGuardPlugin()

        def fake_run(*args, **kwargs):
            raise FileNotFoundError("git 不存在")
        monkeypatch.setattr(
            "autoclaude.plugins.token_guard.git_verifier.subprocess.run", fake_run
        )
        assert plugin.verify_correction_applied(attempt=1) is None

    def test_no_diff_returns_warning(self, monkeypatch):
        """git diff stdout 空 → 回傳警告字串。"""
        plugin = TokenGuardPlugin()
        class _R:
            returncode = 0
            stdout = ""
        monkeypatch.setattr(
            "autoclaude.plugins.token_guard.git_verifier.subprocess.run",
            lambda *a, **kw: _R(),
        )
        result = plugin.verify_correction_applied(attempt=2)
        assert result is not None
        assert "attempt 2" in result
        assert "git diff HEAD 為空" in result

    def test_has_diff_returns_none(self, monkeypatch):
        """git diff 有變更 → 回傳 None（無警告）。"""
        plugin = TokenGuardPlugin()
        class _R:
            returncode = 0
            stdout = " file.py | 5 +++++"
        monkeypatch.setattr(
            "autoclaude.plugins.token_guard.git_verifier.subprocess.run",
            lambda *a, **kw: _R(),
        )
        assert plugin.verify_correction_applied(attempt=1) is None


# ─────────────────────────────────────────────────────────────
# 6. W2 三方審查 SD-M2 / Arch-M2：PlaybookTask.token_guard typo 防呆
# ─────────────────────────────────────────────────────────────
class TestTokenGuardTypoRejection:
    def test_unknown_key_raises(self):
        """拼錯 compact_threshold（漏 _pct）必須在 PlaybookTask 載入時就 raise。"""
        with pytest.raises(Exception, match="未知欄位|unknown|compact_threshold"):
            PlaybookTask(
                step_id="T01", name="n", prompt="p",
                token_guard={"compact_threshold": 70.0},  # 漏 _pct
            )

    def test_multiple_unknown_keys_listed(self):
        with pytest.raises(Exception, match="未知欄位"):
            PlaybookTask(
                step_id="T01", name="n", prompt="p",
                token_guard={"halt_pct": 90, "foo": 1},
            )

    def test_known_keys_accepted(self):
        """所有 TokenGuardConfig 合法欄位都應通過。"""
        task = PlaybookTask(
            step_id="T01", name="n", prompt="p",
            token_guard={
                "enabled": True,
                "compact_threshold_pct": 75.0,
                "halt_threshold_pct": 85.0,
                "resume_delay_minutes": 10,
                "auto_resume": False,
                "max_auto_resumes": 5,
            },
        )
        assert task.token_guard["compact_threshold_pct"] == 75.0

    def test_empty_dict_accepted(self):
        task = PlaybookTask(
            step_id="T01", name="n", prompt="p",
            token_guard={},
        )
        assert task.token_guard == {}

    def test_none_accepted(self):
        task = PlaybookTask(
            step_id="T01", name="n", prompt="p",
            token_guard=None,
        )
        assert task.token_guard is None
