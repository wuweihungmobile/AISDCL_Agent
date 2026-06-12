"""W4（AutoSDD_improving_01 §3.3）：sdd_compile CLI 測試。

覆蓋：
  1. 編譯產物 = 標準 playbook YAML（yaml.safe_load + Playbook.model_validate 可載入）
  2. 產物 evaluator_command 過 PreRunValidator 煙霧（截斷點 3）
  3. 凍結硬閘 / 汙染 / 缺檔的 exit code 分流
"""
from __future__ import annotations

import yaml

from autoclaude.execution.pre_run_validator import PreRunValidator
from autoclaude.models.playbook import Playbook
from autoclaude.tools.sdd_compile import compile_spec, main
from tests.infra.test_sdd_to_playbook_adapter import _write_fsm_state, _write_spec


class TestCompileSpec:
    def test_returns_validated_playbook(self, tmp_path):
        spec_dir = _write_spec(tmp_path)
        _write_fsm_state(tmp_path)
        pb = compile_spec(str(spec_dir), project="demo")
        assert isinstance(pb, Playbook)
        assert pb.workflow_type == "aisdlc_sdd"
        assert pb.project == "demo"
        assert len(pb.tasks) == 3
        assert pb.global_goal and "brownfield" in pb.global_goal

    def test_empty_contracts_raises(self, tmp_path):
        spec_dir = _write_spec(tmp_path, text="# TCS 空殼\n無表格")
        _write_fsm_state(tmp_path)
        try:
            compile_spec(str(spec_dir))
            raise AssertionError("應拋 ValueError")
        except ValueError as exc:
            assert "無可編譯步驟" in str(exc)


class TestCliMain:
    def _compile(self, tmp_path, *extra):
        spec_dir = _write_spec(tmp_path)
        _write_fsm_state(tmp_path)
        out = tmp_path / "out" / "sdd_playbook.yaml"
        rc = main(["--spec-dir", str(spec_dir), "--out", str(out), *extra])
        return rc, out

    def test_output_is_standard_playbook_yaml(self, tmp_path):
        rc, out = self._compile(tmp_path)
        assert rc == 0 and out.is_file()
        doc = yaml.safe_load(out.read_text(encoding="utf-8"))
        pb = Playbook.model_validate(doc)  # 與 runner 載入端等價的 schema 驗證
        assert [t.step_id for t in pb.tasks] == [
            "sdd-brownfield-at-001-1-1",
            "sdd-brownfield-at-001-1-2",
            "sdd-brownfield-at-002-1-1",
        ]

    def test_output_passes_pre_run_validator_smoke(self, tmp_path):
        """截斷點 3 煙霧：產物 evaluator_command 經 PreRunValidator 無 block。"""
        rc, out = self._compile(tmp_path)
        assert rc == 0
        pb = Playbook.model_validate(yaml.safe_load(out.read_text(encoding="utf-8")))
        validator = PreRunValidator()
        for task in pb.tasks:
            issues = validator.validate_step(task.evaluator_command, task.prompt)
            blocks = [i for i in issues if i.severity == "block"]
            assert blocks == [], f"{task.step_id}: {blocks}"

    def test_not_frozen_exit_code_2(self, tmp_path, capsys):
        spec_dir = _write_spec(tmp_path)  # 不寫 FSM 狀態檔
        out = tmp_path / "o.yaml"
        rc = main(["--spec-dir", str(spec_dir), "--out", str(out)])
        assert rc == 2 and not out.exists()
        assert "規格未凍結" in capsys.readouterr().err

    def test_tainted_test_path_exit_code_3(self, tmp_path, capsys):
        spec_dir = _write_spec(tmp_path)
        _write_fsm_state(tmp_path)
        rc = main(["--spec-dir", str(spec_dir), "--out", str(tmp_path / "o.yaml"),
                   "--test-path", "tests;rm"])
        assert rc == 3
        assert "SPEC_TAINTED" in capsys.readouterr().err

    def test_missing_spec_exit_code_4(self, tmp_path):
        (tmp_path / "docs").mkdir()
        rc = main(["--spec-dir", str(tmp_path / "docs"),
                   "--out", str(tmp_path / "o.yaml")])
        assert rc == 4
