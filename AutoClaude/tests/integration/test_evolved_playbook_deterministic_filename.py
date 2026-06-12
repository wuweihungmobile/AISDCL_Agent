"""演化後 Playbook 確定性檔名測試（SD_Improving_03 §5.2 DoD #9）。

驗證 PlaybookEvolver.apply_evolution() 產生的檔名格式：
  - 格式為 evolved_{原檔名}.yaml（確定性前綴，非純時間戳）
  - 不同原始 playbook 產生不同演化檔名
  - 多次演化時，覆寫同一演化路徑（apply_evolution 的設計決策）
  - 演化後 YAML 內容可被 Playbook 重新解析（格式完整性）
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from autoclaude.evolution.playbook_evolver import PlaybookEvolver, PlaybookEvolutionProposal
from autoclaude.models.escalation import EscalationDump
from autoclaude.models.playbook import Playbook, PlaybookTask, GlobalInvariants


# ──────────────────────────────────────────────────────────
# 工廠函式
# ──────────────────────────────────────────────────────────

def _make_simple_playbook() -> Playbook:
    return Playbook(
        version="1.0",
        project="TestProject",
        global_goal="通過所有單元測試",
        global_invariants=GlobalInvariants(max_retries_per_step=3),
        tasks=[
            PlaybookTask(
                step_id="T01",
                name="建立模組",
                prompt="建立 my_module.py 並輸出 [T01_DONE]",
                expected_output_regex=r"\[T01_DONE\]",
            ),
            PlaybookTask(
                step_id="T02",
                name="執行測試",
                prompt="執行 pytest tests/ 並確認通過",
                expected_output_regex=r"\[T02_DONE\]",
                evaluator_command="pytest tests/ -q",
            ),
        ],
    )


def _make_dump(step_id="T02", suspect_test_file=True) -> EscalationDump:
    return EscalationDump(
        playbook_path="test.yaml",
        step_id=step_id,
        step_name=f"步驟 {step_id}",
        total_attempts=4,
        is_stuck=True,
        is_diverging=False,
        suspect_test_file=suspect_test_file,
        suspect_assertion_mismatch=False,
        final_eval_output="",
        human_hint="測試檔有 ImportError",
        failure_chain=[
            {"attempt": 1, "error_class": "import", "error_signature": "ImportError", "minimax_reasoning": "retry", "exit_code": 1},
            {"attempt": 2, "error_class": "import", "error_signature": "ImportError", "minimax_reasoning": "env_setup", "exit_code": 1},
            {"attempt": 3, "error_class": "import", "error_signature": "ImportError", "minimax_reasoning": "reinstall", "exit_code": 1},
        ],
    )


def _write_playbook_yaml(tmp_path: Path, name: str = "my_playbook.yaml") -> Path:
    """將簡單 playbook 寫入 tmp_path，並返回路徑。"""
    pb = _make_simple_playbook()
    pb_path = tmp_path / name
    with pb_path.open("w", encoding="utf-8") as f:
        yaml.dump(
            pb.model_dump(exclude_none=True),
            f,
            allow_unicode=True,
            default_flow_style=False,
        )
    return pb_path


# ──────────────────────────────────────────────────────────
class TestEvolvedPlaybookFilenameFormat:
    def test_evolved_playbook_filename_format(self, tmp_path):
        """演化後 playbook 檔名符合 evolved_{原檔名}.yaml 格式。"""
        pb_path = _write_playbook_yaml(tmp_path, "my_playbook.yaml")
        evolver = PlaybookEvolver()
        pb = _make_simple_playbook()
        dump = _make_dump(step_id="T02", suspect_test_file=True)

        proposal = evolver.propose_evolution(pb, failed_step_idx=1, escalation_dump=dump)
        assert proposal is not None, "應產生演化提議"

        evolved_path = evolver.apply_evolution(pb, proposal, str(pb_path))
        evolved_name = Path(evolved_path).name

        assert evolved_name == "evolved_my_playbook.yaml", (
            f"預期 evolved_my_playbook.yaml，實際 {evolved_name}"
        )

    def test_evolved_playbook_filename_not_pure_timestamp(self, tmp_path):
        """演化後 playbook 檔名不能是純 ISO timestamp（避免 non-deterministic 命名）。"""
        pb_path = _write_playbook_yaml(tmp_path, "sprint_task.yaml")
        evolver = PlaybookEvolver()
        pb = _make_simple_playbook()
        dump = _make_dump(step_id="T02")

        proposal = evolver.propose_evolution(pb, failed_step_idx=1, escalation_dump=dump)
        assert proposal is not None

        evolved_path = evolver.apply_evolution(pb, proposal, str(pb_path))
        evolved_name = Path(evolved_path).name

        # 純時間戳格式（如 2026-05-14T21_25_51.yaml）不應出現
        pure_timestamp_pattern = re.compile(
            r"^\d{4}-\d{2}-\d{2}[T_]\d{2}[_:]\d{2}[_:]\d{2}.*\.yaml$"
        )
        assert not pure_timestamp_pattern.match(evolved_name), (
            f"演化檔名不應是純時間戳格式，實際 {evolved_name}"
        )
        # 應以 evolved_ 為前綴
        assert evolved_name.startswith("evolved_"), (
            f"演化檔名應以 evolved_ 開頭，實際 {evolved_name}"
        )

    def test_evolved_playbook_different_source_different_filename(self, tmp_path):
        """不同原始 playbook 名稱產生不同演化檔名（確定性對應）。"""
        pb_path_a = _write_playbook_yaml(tmp_path, "plan_a.yaml")
        pb_path_b = _write_playbook_yaml(tmp_path, "plan_b.yaml")

        evolver = PlaybookEvolver()
        pb = _make_simple_playbook()
        dump = _make_dump(step_id="T02")

        proposal = evolver.propose_evolution(pb, failed_step_idx=1, escalation_dump=dump)
        assert proposal is not None

        evolved_a = Path(evolver.apply_evolution(pb, proposal, str(pb_path_a))).name
        evolved_b = Path(evolver.apply_evolution(pb, proposal, str(pb_path_b))).name

        assert evolved_a != evolved_b, "不同原始檔名應產生不同演化檔名"
        assert evolved_a == "evolved_plan_a.yaml"
        assert evolved_b == "evolved_plan_b.yaml"

    def test_evolved_playbook_yaml_is_valid_and_parseable(self, tmp_path):
        """演化後 YAML 可被 Playbook 重新解析（格式完整性）。"""
        pb_path = _write_playbook_yaml(tmp_path, "check_yaml.yaml")
        evolver = PlaybookEvolver()
        pb = _make_simple_playbook()
        dump = _make_dump(step_id="T02")

        proposal = evolver.propose_evolution(pb, failed_step_idx=1, escalation_dump=dump)
        assert proposal is not None

        evolved_path = evolver.apply_evolution(pb, proposal, str(pb_path))
        assert Path(evolved_path).exists(), "演化檔案應存在"

        # 確認 YAML 可解析
        with open(evolved_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        assert "tasks" in raw, "演化後 YAML 應含 tasks 欄位"
        assert len(raw["tasks"]) >= len(pb.tasks), "演化後步驟數應 >= 原始步驟數"

        # 確認可被 Playbook model 解析
        evolved_pb = Playbook(**raw)
        assert "[EVOLVED]" in evolved_pb.project

    def test_evolved_playbook_contains_injected_step(self, tmp_path):
        """INJECT_STEP 演化後，注入的新步驟確實存在於演化版 YAML 中。"""
        pb_path = _write_playbook_yaml(tmp_path, "inject_check.yaml")
        evolver = PlaybookEvolver()
        pb = _make_simple_playbook()
        # suspect_test_file=True → INJECT_STEP 在 T02 前注入 T02_PRE
        dump = _make_dump(step_id="T02", suspect_test_file=True)

        proposal = evolver.propose_evolution(pb, failed_step_idx=1, escalation_dump=dump)
        assert proposal is not None
        assert proposal.evolution_type == "INJECT_STEP"

        evolved_path = evolver.apply_evolution(pb, proposal, str(pb_path))
        with open(evolved_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        step_ids = [t["step_id"] for t in raw["tasks"]]
        assert "T02_PRE" in step_ids, f"注入的 T02_PRE 應存在，實際 step_ids={step_ids}"
