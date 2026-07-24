"""Pydantic 資料模型單元測試（Playbook / PlaybookTask / ContextNegotiation / EscalationDump）。"""
from __future__ import annotations

import re

import yaml

from autoclaude.models import (
    ContextNegotiation,
    GlobalInvariants,
    Playbook,
    PlaybookTask,
)
from autoclaude.models.escalation import EscalationDump
from autoclaude.utils.logger import _WIN_FORBIDDEN_CHARS

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
# DEF-101（Mac/Windows 相容性）：EscalationDump.save() 對含 Windows 禁用字元的
# step_id 必須淨化檔名，而非直接組進去（否則 Windows 上 open() 會拋未捕捉的
# OSError，同類根因見 DEF-101-219＠R16／DEF-101-295＠R33）。
# ──────────────────────────────────────────────

def test_escalation_dump_save_sanitizes_step_id_with_colon_and_space(tmp_path):
    """playbook 作者手寫 YAML 常見自然字串（如 "Step 1: Setup"）不可讓 save()
    產生含冒號/其他 Windows 禁用字元的檔名。"""
    dump = _make_escalation_dump(step_id="Step 1: Setup")
    path = dump.save(str(tmp_path))
    assert path.exists()
    assert ":" not in path.name
    for ch in _WIN_FORBIDDEN_CHARS:
        assert ch not in path.name, f"禁用字元 {ch!r} 洩漏進檔名 {path.name!r}"


def test_escalation_dump_save_sanitizes_step_id_with_all_forbidden_chars(tmp_path):
    """step_id 含全部 Windows 禁用字元（< > : " | ? * \\）時，save() 產生的檔名
    不得含任一個禁用字元。"""
    step_id = "".join(sorted(_WIN_FORBIDDEN_CHARS)) + "weird"
    dump = _make_escalation_dump(step_id=step_id)
    path = dump.save(str(tmp_path))
    assert path.exists()
    for ch in _WIN_FORBIDDEN_CHARS:
        assert ch not in path.name, f"禁用字元 {ch!r} 洩漏進檔名 {path.name!r}"


def test_escalation_dump_save_returns_path_under_dump_dir(tmp_path):
    """回歸：淨化後 save() 仍回傳實際寫入路徑，且該路徑確實存在於指定 dump_dir 下。"""
    dump = _make_escalation_dump(step_id="normal_step")
    path = dump.save(str(tmp_path))
    assert path.parent == tmp_path
    assert path.exists()
    assert path.name.startswith("escalation_normal_step_")


def test_escalation_dump_save_step_id_with_control_char_is_stripped(tmp_path):
    """step_id 含控制字元（如 \\x01）時，save() 產生的檔名不得殘留該字元
    （對稱於 logger.py 既有 RawStreamLogger 的控制字元淨化行為）。"""
    dump = _make_escalation_dump(step_id="bad\x01step\x7f")
    path = dump.save(str(tmp_path))
    assert path.exists()
    assert "\x01" not in path.name
    assert "\x7f" not in path.name


def test_escalation_dump_save_step_id_with_slash_stays_flat_file_not_subdir(tmp_path):
    """step_id 含 `/`（如 `"setup/init"` 這種自然階層式命名，或更刻意的路徑穿越
    `"../../x"`）不得被 pathlib 解讀成額外路徑層級——save() 必須產生 tmp_path
    下的單一扁平檔案，而非意外建出子目錄或試圖穿越到 tmp_path 之外（R37 QA
    一審實測：未淨化前 `step_id="../../../../../../tmp/pwned"` 會讓
    `path.parent.mkdir()` 拋出未捕捉的 PermissionError）。"""
    dump = _make_escalation_dump(step_id="setup/init")
    path = dump.save(str(tmp_path))
    assert path.exists()
    assert path.parent == tmp_path, "不得因 step_id 含 / 而建出非預期子目錄"
    assert "/" not in path.name


def test_escalation_dump_save_step_id_with_path_traversal_stays_within_dump_dir(tmp_path):
    """對稱於上一測試，驗證更刻意的 `../` 穿越同樣被淨化，save() 仍落在
    tmp_path 之內、不拋出例外。"""
    dump = _make_escalation_dump(step_id="../../../../../../tmp/pwned")
    path = dump.save(str(tmp_path))
    assert path.exists()
    assert path.parent == tmp_path
    assert ".." not in path.parts


def test_escalation_dump_uses_shared_sanitizer_not_a_reimplementation():
    """DEF-101 反覆復發根因＝同一淨化規則被多處獨立實作。鎖住 escalation.py
    是直接 import utils/logger.py 的 `_sanitize_log_filename`（同一顆函式物件），
    而非另外複製一份相似邏輯——防止未來有人在 escalation.py 內嵌新的字元集合。"""
    from autoclaude.models import escalation as esc_mod
    from autoclaude.utils import logger as logger_mod

    assert esc_mod._sanitize_log_filename is logger_mod._sanitize_log_filename


def test_escalation_dump_save_falls_back_when_step_id_too_long_for_filesystem(tmp_path):
    """`_sanitize_log_filename()` 只淨化禁用字元，不截斷長度——step_id 為完全自由
    格式無驗證欄位，超長字串仍可能讓檔名超出檔案系統上限（觀察到的 OSError:
    File name too long）。save() 必須 fallback 寫入系統暫存目錄，而非讓 ESCALATION
    診斷快照（失敗復盤關鍵材料）完全遺失。"""
    dump = _make_escalation_dump(step_id="x" * 300)
    path = dump.save(str(tmp_path))
    assert path.exists()
    assert path.read_text(encoding="utf-8") == dump.to_markdown()
    assert path.parent != tmp_path, "應 fallback 至系統暫存目錄，而非留在（必然失敗的）原 dump_dir"


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
