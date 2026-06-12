"""Pydantic 資料模型單元測試（Playbook / PlaybookTask / ContextNegotiation / EscalationDump）。"""
from __future__ import annotations
import re
from pathlib import Path

import yaml

from autoclaude.models import (
    Playbook,
    PlaybookTask,
    ContextNegotiation,
    GlobalInvariants,
)
from autoclaude.models.escalation import EscalationDump


# ──────────────────────────────────────────────
# 預設值與選填欄位
# ──────────────────────────────────────────────

def test_playbook_model_defaults():
    pb = Playbook(
        project="test",
        tasks=[PlaybookTask(step_id="T01", name="step1", prompt="do something")],
    )
    assert pb.version == "1.0"
    assert pb.workflow_type == "auto"
    assert pb.global_invariants.max_retries_per_step == 3
    assert pb.global_invariants.auto_compact_interval == 5
    assert pb.tasks[0].maintain_context is True
    assert pb.tasks[0].max_retries is None


def test_playbook_task_per_step_override():
    task = PlaybookTask(
        step_id="T01", name="s", prompt="p",
        max_retries=1, maintain_context=False,
        expected_output_regex=r"\[DONE\]",
    )
    assert task.max_retries == 1
    assert task.maintain_context is False
    assert re.search(task.expected_output_regex, "output [DONE] here")


def test_playbook_load_from_yaml(tmp_path):
    data = {
        "version": "1.0",
        "project": "demo",
        "global_invariants": {"max_retries_per_step": 2, "auto_compact_interval": 3},
        "tasks": [
            {"step_id": "T01", "name": "n", "prompt": "p",
             "expected_output_regex": r"\[OK\]"},
        ],
    }
    yaml_path = tmp_path / "pb.yaml"
    yaml_path.write_text(yaml.dump(data), encoding="utf-8")

    pb = Playbook.model_validate(yaml.safe_load(yaml_path.read_text(encoding="utf-8")))
    assert pb.project == "demo"
    assert pb.global_invariants.max_retries_per_step == 2
    assert pb.tasks[0].step_id == "T01"


# ──────────────────────────────────────────────
# command 欄位（mock CLI 模式使用）
# ──────────────────────────────────────────────

def test_task_command_field_optional():
    task = PlaybookTask(step_id="T01", name="n", prompt="p", command="dummy_cmd")
    assert task.command == "dummy_cmd"


def test_task_command_field_defaults_none():
    task = PlaybookTask(step_id="T01", name="n", prompt="p")
    assert task.command is None


def test_task_with_command_loaded_from_yaml(tmp_path):
    data = {
        "version": "1.0", "project": "x",
        "tasks": [{
            "step_id": "T01", "name": "n", "prompt": "p",
            "command": "mock_cmd", "expected_output_regex": "x",
        }],
    }
    p = tmp_path / "pb.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")
    pb = Playbook.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))
    assert pb.tasks[0].command == "mock_cmd"


# ──────────────────────────────────────────────
# ContextNegotiation 欄位
# ──────────────────────────────────────────────

def test_context_negotiation_model():
    cn = ContextNegotiation(prompt="start", expected_keyword="ready")
    assert cn.prompt == "start"
    assert cn.expected_keyword == "ready"


def test_playbook_context_negotiation_from_yaml(tmp_path):
    data = {
        "version": "1.0", "project": "x",
        "context_negotiation": {"prompt": "start", "expected_keyword": "ready"},
        "tasks": [{"step_id": "T01", "name": "n", "prompt": "p"}],
    }
    p = tmp_path / "pb.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")
    pb = Playbook.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))
    assert pb.context_negotiation is not None
    assert pb.context_negotiation.prompt == "start"
    assert pb.context_negotiation.expected_keyword == "ready"


def test_playbook_backward_compat_no_context_negotiation(tmp_path):
    data = {
        "version": "1.0", "project": "x",
        "tasks": [{"step_id": "T01", "name": "n", "prompt": "p"}],
    }
    p = tmp_path / "pb.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")
    pb = Playbook.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))
    assert pb.context_negotiation is None


def test_global_invariants_defaults():
    gi = GlobalInvariants()
    assert gi.max_retries_per_step == 3
    assert gi.auto_compact_interval == 5


# ──────────────────────────────────────────────
# EscalationDump 測試
# ──────────────────────────────────────────────

def _make_escalation_dump(**kwargs) -> EscalationDump:
    defaults = dict(
        playbook_path="test.yaml",
        step_id="T01",
        step_name="Test Step",
        total_attempts=4,
        failure_chain=[],
        final_eval_output="test output",
        is_stuck=False,
        is_diverging=False,
        suspect_test_file=False,
    )
    defaults.update(kwargs)
    return EscalationDump(**defaults)


def test_escalation_dump_is_oscillating_defaults_false():
    dump = _make_escalation_dump()
    assert dump.is_oscillating is False


def test_escalation_dump_is_oscillating_true_in_markdown():
    dump = _make_escalation_dump(is_oscillating=True)
    md = dump.to_markdown()
    assert "振盪錯誤（ABAB 交替）: ✅ 是" in md


def test_escalation_dump_is_oscillating_false_in_markdown():
    dump = _make_escalation_dump(is_oscillating=False)
    md = dump.to_markdown()
    assert "振盪錯誤（ABAB 交替）: ❌ 否" in md


def test_escalation_dump_to_markdown_contains_all_four_diagnostic_flags():
    dump = _make_escalation_dump()
    md = dump.to_markdown()
    assert "錯誤卡死" in md
    assert "錯誤發散" in md
    assert "振盪錯誤" in md
    assert "疑似測試檔" in md


def test_escalation_dump_is_stuck_true_in_markdown():
    dump = _make_escalation_dump(is_stuck=True)
    md = dump.to_markdown()
    assert "錯誤卡死（特徵相同）: ✅ 是" in md


# ──────────────────────────────────────────────
# Gap-036：StepMutation 注入步驟評估欄位
# ──────────────────────────────────────────────

def test_step_mutation_gap036_new_fields_defaults_none():
    """Gap-036：StepMutation 新增的三個評估欄位預設為 None。"""
    from autoclaude.models.step_mutation import StepMutation, StepMutationType
    m = StepMutation(mutation_type=StepMutationType.INJECT_BEFORE, new_step_prompt="do something")
    assert m.new_step_evaluator_command is None
    assert m.new_step_expected_regex is None
    assert m.new_step_max_retries is None


def test_step_mutation_gap036_inject_before_with_evaluator():
    """Gap-036：INJECT_BEFORE 可攜帶 evaluator_command 和 expected_regex。"""
    from autoclaude.models.step_mutation import StepMutation, StepMutationType
    m = StepMutation(
        mutation_type=StepMutationType.INJECT_BEFORE,
        new_step_id="T01_PRE",
        new_step_name="環境初始化",
        new_step_prompt="pip install fastapi",
        new_step_evaluator_command="pip show fastapi && echo OK",
        new_step_expected_regex=r"OK",
        new_step_max_retries=2,
    )
    assert m.new_step_evaluator_command == "pip show fastapi && echo OK"
    assert m.new_step_expected_regex == r"OK"
    assert m.new_step_max_retries == 2


def test_step_mutation_gap036_inject_after_with_evaluator():
    """Gap-036：INJECT_AFTER 可攜帶 evaluator_command。"""
    from autoclaude.models.step_mutation import StepMutation, StepMutationType
    m = StepMutation(
        mutation_type=StepMutationType.INJECT_AFTER,
        new_step_id="T01_VERIFY",
        new_step_prompt="run tests",
        new_step_evaluator_command="pytest tests/ -v",
    )
    assert m.new_step_evaluator_command == "pytest tests/ -v"
    assert m.new_step_expected_regex is None


def test_step_mutation_gap036_serialization_round_trip():
    """Gap-036：StepMutation 含評估欄位可正確序列化/反序列化。"""
    from autoclaude.models.step_mutation import StepMutation, StepMutationType
    m = StepMutation(
        mutation_type=StepMutationType.INJECT_BEFORE,
        new_step_prompt="install deps",
        new_step_evaluator_command="pip show requests",
        new_step_max_retries=3,
    )
    dumped = m.model_dump()
    assert dumped["new_step_evaluator_command"] == "pip show requests"
    assert dumped["new_step_max_retries"] == 3
    restored = StepMutation.model_validate(dumped)
    assert restored.new_step_evaluator_command == "pip show requests"
    assert restored.new_step_max_retries == 3


# ──────────────────────────────────────────────
# Gap-038：PlaybookConfig conditional_evaluator_timeout_seconds
# ──────────────────────────────────────────────

def test_config_gap038_conditional_timeout_default():
    """Gap-038：PlaybookConfig.conditional_evaluator_timeout_seconds 預設值為 5。"""
    from autoclaude.utils.config import PlaybookConfig
    cfg = PlaybookConfig()
    assert cfg.conditional_evaluator_timeout_seconds == 5


def test_config_gap038_conditional_timeout_override():
    """Gap-038：PlaybookConfig 可覆寫 conditional_evaluator_timeout_seconds。"""
    from autoclaude.utils.config import PlaybookConfig
    cfg = PlaybookConfig(conditional_evaluator_timeout_seconds=15)
    assert cfg.conditional_evaluator_timeout_seconds == 15


def test_config_gap038_app_config_includes_timeout():
    """Gap-038：AppConfig 透過 PlaybookConfig 包含 conditional_evaluator_timeout_seconds。"""
    from autoclaude.utils.config import AppConfig
    cfg = AppConfig()
    assert hasattr(cfg.playbook, "conditional_evaluator_timeout_seconds")
    assert cfg.playbook.conditional_evaluator_timeout_seconds == 5
