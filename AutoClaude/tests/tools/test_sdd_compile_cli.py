"""W4（AutoSDD_improving_01 §3.3）：sdd_compile CLI 測試。

覆蓋：
  1. 編譯產物 = 標準 playbook YAML（yaml.safe_load + Playbook.model_validate 可載入）
  2. 產物 evaluator_command 過 PreRunValidator 煙霧（截斷點 3）
  3. 凍結硬閘 / 汙染 / 缺檔的 exit code 分流
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from autoclaude.execution.pre_run_validator import PreRunValidator
from autoclaude.infra.adapters.sdd_to_playbook_adapter import SddToPlaybookAdapter
from autoclaude.models.playbook import Playbook
from autoclaude.tools.sdd_compile import SpecAtUnmappedError, compile_spec, main
from autoclaude.utils.config import load_config
from tests.infra.test_sdd_to_playbook_adapter import (
    _SPEC_MD,
    _WORDCOUNT_DIR,
    _WORDCOUNT_TCS,
    _frozen_stage,
    _spec_path,
    _spec_text,
    _write_fsm_state,
    _write_spec,
    _write_state,
)


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

    def test_unsupported_spec_version_exit_code_5(self, tmp_path, capsys):
        """W-85-2 / RTM-85-4：宣告未支援版本 → main() 乾淨退碼 5（非未捕捉 traceback）。

        修前 main() 不接 SpecFormatVersionError，版本漂移會噴 traceback + exit 1；本測試
        鎖定「防漂移閘觸發時 CLI 仍乾淨退場」這條協作橋接契約（Rule 9：能因行為改變而失敗）。
        """
        # 生產端 bold 行格式宣告未支援版本 2.0 → load_spec raise SpecFormatVersionError
        spec_dir = _write_spec(
            tmp_path, text=_SPEC_MD + "\n**spec-format-version**: 2.0\n")
        _write_fsm_state(tmp_path)
        out = tmp_path / "o.yaml"
        rc = main(["--spec-dir", str(spec_dir), "--out", str(out)])
        assert rc == 5 and not out.exists()
        assert "防漂移" in capsys.readouterr().err

    def test_fsm_state_outside_runtime_search_path_exit_code_2(self, tmp_path, capsys):
        """D-SBR-04：--fsm-state-path 只作用於編譯期；執行期 PRE_RUN 以 workflow_path 向上搜尋。

        狀態檔放在 spec-dir 祖先鏈之外時，編譯是綠的、執行卻在 PRE_RUN 被 SPEC_NOT_FROZEN 否決
        （0 步、0.0 秒）——把這個「編譯綠、執行紅」提前到編譯期：rc=2、不寫出 --out。
        """
        spec_dir = _write_spec(tmp_path / "project")
        _write_fsm_state(tmp_path / "elsewhere")  # 與 spec-dir 祖先鏈無交集
        state = tmp_path / "elsewhere" / "build" / "reports" / "fsm" / "FSM-STATE-demo.yaml"
        out = tmp_path / "o.yaml"
        rc = main(["--spec-dir", str(spec_dir), "--out", str(out),
                   "--fsm-state-path", str(state)])
        assert rc == 2 and not out.exists()
        assert "執行期" in capsys.readouterr().err

    def test_explicit_fsm_state_path_the_runtime_would_also_find_still_compiles(self, tmp_path):
        """上一例的對照組：狀態檔本來就在祖先鏈上時，顯式 --fsm-state-path 不得被誤擋。"""
        spec_dir = _write_spec(tmp_path)
        _write_fsm_state(tmp_path)
        state = tmp_path / "build" / "reports" / "fsm" / "FSM-STATE-demo.yaml"
        out = tmp_path / "o.yaml"
        rc = main(["--spec-dir", str(spec_dir), "--out", str(out),
                   "--fsm-state-path", str(state)])
        assert rc == 0 and out.is_file()


# F-SBR-001 AC-SBR-007：修法前探針對同一份規格編出的 task 序列，逐欄釘住（§2.3）。
# (step_id, expected_output_regex, evaluator_command, max_retries, maintain_context, weak_regex)
_WORDCOUNT_GOLDEN = [
    ("sdd-greenfield-at-001-1-1", r"(?s)(?=.*the)(?=.*cat)",
     'pytest tests -k "AT_001_1_1" -q', 5, False, False),
    ("sdd-greenfield-at-001-1-2", r"(?s)\A(?=.*hello)(?!.*hello,)",
     'pytest tests -k "AT_001_1_2" -q', 5, True, False),
    ("sdd-greenfield-at-002-1-1", r"\bPASS(ED)?\b",
     'pytest tests -k "AT_002_1_1" -q', 5, False, True),
]
_WORDCOUNT_DIGEST = "sha256:0de6845eee4e1d63532a76aebd5049651f8e5fa061599d0b84aeeb9fe110f742"


class TestBridgeWordcountFixture:
    """入庫的迷你專案（scripts/bridge_e2e/wordcount）：不用真 claude 即可重現橋接鏈前半。"""

    def test_fixture_compiles_to_the_golden_tasks(self, tmp_path):
        spec_dir = _write_spec(
            tmp_path, text=_WORDCOUNT_TCS.read_text(encoding="utf-8"), name=_WORDCOUNT_TCS.name)
        _write_fsm_state(tmp_path)
        out = tmp_path / "out" / "playbook.yaml"
        rc = main(["--spec-dir", str(spec_dir), "--out", str(out), "--project", "wordcount_sbr"])
        assert rc == 0
        # runner 載入端看到的樣子（YAML 來回之後）
        pb = Playbook.model_validate(yaml.safe_load(out.read_text(encoding="utf-8")))
        assert [(t.step_id, t.expected_output_regex, t.evaluator_command, t.max_retries,
                 t.maintain_context, t.weak_regex) for t in pb.tasks] == _WORDCOUNT_GOLDEN
        # spec_digest＝規格文字的 sha256：fixture 被改一個字就紅（不斷言含絕對路徑的欄位）
        assert {t.spec_digest for t in pb.tasks} == {_WORDCOUNT_DIGEST}
        # 引擎實際載入的是序列化之後的 prompt：評估指令與輸出契約必須原樣活過 YAML 來回
        for t in pb.tasks:
            assert t.evaluator_command in t.prompt, t.step_id
            assert t.expected_output_regex in t.prompt, t.step_id

    def test_real_run_config_template_keeps_brain_off_and_leaves_guard_thresholds_alone(
            self, tmp_path):
        """範本是真跑的起點：Brain 關閉（重試才不會被 Brain 改寫 prompt）、模型 haiku、不彈通知；
        而且**不得**覆寫任何額度／context 門檻——守衛的訊息就是答案，不為了跑而調門檻。"""
        text = (_WORDCOUNT_DIR / "config.template.yaml").read_text(encoding="utf-8")
        cfg_path = tmp_path / "config.yaml"
        cfg_path.write_text(text.replace("__RUN_DIR__", str(tmp_path)),
                            encoding="utf-8", newline="\n")
        cfg = load_config(str(cfg_path))  # 檔不存在時 load_config 會靜默回預設，故下面逐值斷言
        assert cfg.minimax.enable_kernel_brain is False
        assert cfg.claude.extra_args[-2:] == ["--model", "haiku"]
        assert cfg.token_guard.auto_resume is False
        assert cfg.playbook.goal_synthesis_enabled is False
        # Path 比較：範本寫正斜線、Windows 的 tmp_path 是反斜線，字串相等在那邊必假紅
        assert Path(cfg.log_dir) == tmp_path / "logs"
        assert Path(cfg.checkpoint_dir) == tmp_path / "checkpoints"
        thresholds = [k for k in yaml.safe_load(text)["token_guard"] if k.endswith("_pct")]
        assert thresholds == [], f"範本不得覆寫門檻：{thresholds}"


# ══════════════════════════════════════════════════════════════════════════════════════
# improving_115（ADR-XPLAT-016 §8.2-8.3／§6）：rc 6、--spec-file、--fsm-project、摘要不符 rc 2
# ══════════════════════════════════════════════════════════════════════════════════════

# 官方模板本體的形狀（§1 的列是佔位、§2 示例標頭卻是真 ID）：模板住 docs_template/，
# **不是**編譯輸入，硬拿去編譯是預期的大聲失敗（§8.2「模板本體」列），
# 實例化時示例區塊要刪或改成真實 AC 的 AT。
_TEMPLATE_BODY = """# Test Contract Specification — 範本本體

**spec-format-version**: 1.0
**scenario**: greenfield

## 1. AC → AT 映射表

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-{NNN}-{Y} | {描述} | AT-{NNN}-{Y}-{Z} | {描述} | ✅ | Unit | □ |

## 2. AT 格式（示例）

```gherkin
# AT-001-1-1
Scenario: 示例
  Given g
  When w
  Then 回傳 201 Created
```

```gherkin
# AT-001-1-2
Scenario: 示例二
  Given g
  When w
  Then 回傳 200 OK
```
"""


class TestUnmappedAtsExitCode6:
    """S-03／D-115-09：AT 出現卻未編成 ⇒ CLI 回 rc 6、印清單、不寫輸出檔（無覆寫旗標）。"""

    def _run(self, tmp_path, text, *extra):
        spec_dir = _write_spec(tmp_path, text=text)
        _write_fsm_state(tmp_path)
        out = tmp_path / "out.yaml"
        return main(["--spec-dir", str(spec_dir), "--out", str(out), *extra]), out

    def test_an_appearing_but_uncompiled_at_exits_6_lists_it_and_writes_nothing(
            self, tmp_path, capsys):
        text = _spec_text(rows=[("AC-001-1", "AT-001-1-1"), ("AC-001-1", "AT-001-E-1")],
                          gherkin_ids=["AT-001-1-1"])
        rc, out = self._run(tmp_path, text)
        assert rc == 6 and not out.exists()
        err = capsys.readouterr().err
        assert "AT-001-E-1" in err
        assert "AT-001-1-1" not in err  # 已編成的 AT 不在清單裡

    def test_the_uninstantiated_template_body_fails_loudly_with_rc_6(self, tmp_path, capsys):
        rc, out = self._run(tmp_path, _TEMPLATE_BODY)
        assert rc == 6 and not out.exists()  # 不是 rc 4「無可編譯步驟」：未編成的 AT 先被點名
        err = capsys.readouterr().err
        assert "AT-001-1-1" in err and "AT-001-1-2" in err

    def test_a_clean_spec_still_exits_0(self, tmp_path):
        text = _spec_text(rows=[("AC-001-1", "AT-001-1-1")], gherkin_ids=["AT-001-1-1"])
        rc, out = self._run(tmp_path, text)
        assert rc == 0 and out.is_file()

    def test_compile_spec_raises_a_value_error_subclass_that_carries_the_ids(self, tmp_path):
        spec_dir = _write_spec(tmp_path, text=_spec_text(
            rows=[("AC-002-1", "AT-001-1-1")]))  # AC 與 AT 前兩段不一致
        _write_fsm_state(tmp_path)
        with pytest.raises(SpecAtUnmappedError) as info:
            compile_spec(str(spec_dir))
        assert isinstance(info.value, ValueError) and info.value.at_ids == ("AT-001-1-1",)

    def test_rc_6_does_not_collide_with_the_format_version_code(self, tmp_path):
        """5 是規格格式版本不受支援（既有）、6 是未編成的 AT（新）：兩種原因不得共用退碼。"""
        rc6, _ = self._run(tmp_path / "unmapped", _spec_text(rows=[("AC-001-1", "AT-001-E-1")]))
        spec_dir = _write_spec(tmp_path / "ver", text=_SPEC_MD + "\n**spec-format-version**: 2.0\n")
        _write_fsm_state(tmp_path / "ver")
        rc5 = main(["--spec-dir", str(spec_dir), "--out", str(tmp_path / "ver.yaml")])
        assert (rc5, rc6) == (5, 6)


class TestDigestMismatchExitCode2:
    """G-06：凍結後改檔 ⇒ rc 2（SpecNotFrozenError 子類走同一個退碼），訊息說「內容已變更」。"""

    def test_editing_the_spec_after_the_freeze_exits_2_with_its_own_message(
            self, tmp_path, capsys):
        spec_dir = _write_spec(tmp_path)
        spec_file = _spec_path(tmp_path)
        _write_state(tmp_path, "demo", current="SPEC_FROZEN",
                     frozen_stages=[_frozen_stage(tmp_path, spec_file)])
        out = tmp_path / "o.yaml"
        assert main(["--spec-dir", str(spec_dir), "--out", str(out)]) == 0  # 未改：放行
        out.unlink()
        spec_file.write_text(_SPEC_MD + "\n凍結後偷加的一行\n", encoding="utf-8")
        rc = main(["--spec-dir", str(spec_dir), "--out", str(out)])
        assert rc == 2 and not out.exists()
        err = capsys.readouterr().err
        assert "內容已變更" in err and "摘要" in err and "未凍結（Spec-First" not in err


class TestSpecFileAndFsmProjectFlags:
    """S-04／G-02：--spec-file 讓同目錄兩份 TCS 可編；--fsm-project 讓多專案狀態目錄可指定。"""

    @pytest.fixture()
    def two_specs(self, tmp_path):
        alpha = _spec_text(rows=[("AC-001-1", "AT-001-1-1")], gherkin_ids=["AT-001-1-1"])
        beta = _spec_text(rows=[("AC-002-1", "AT-002-1-1")], gherkin_ids=["AT-002-1-1"])
        spec_dir = _write_spec(tmp_path, text=alpha, name="TCS-Alpha.md")
        _write_spec(tmp_path, text=beta, name="TCS-Beta.md")
        _write_fsm_state(tmp_path)
        return tmp_path, spec_dir

    def test_two_tcs_in_one_directory_are_ambiguous_without_the_flag(self, two_specs, capsys):
        root, spec_dir = two_specs
        out = root / "o.yaml"
        assert main(["--spec-dir", str(spec_dir), "--out", str(out)]) == 4
        assert "spec_file" in capsys.readouterr().err and not out.exists()

    def test_spec_file_compiles_the_named_one_and_anchors_workflow_path_to_the_file(
            self, two_specs):
        root, spec_dir = two_specs
        out = root / "o.yaml"
        rc = main(["--spec-dir", str(spec_dir), "--spec-file", "03_testing/contracts/TCS-Beta.md",
                   "--out", str(out)])
        assert rc == 0
        pb = Playbook.model_validate(yaml.safe_load(out.read_text(encoding="utf-8")))
        assert [t.step_id for t in pb.tasks] == ["sdd-greenfield-at-002-1-1"]
        assert Path(pb.workflow_path) == _spec_path(root, "TCS-Beta.md").resolve()
        # 引擎 PRE_RUN 以 workflow_path 呼叫 load_spec：檔案路徑被視為 spec_file，載到同一份規格
        runtime = SddToPlaybookAdapter().load_spec(pb.workflow_path)
        assert [c.at_id for c in runtime.contracts] == ["AT-002-1-1"]

    def test_without_spec_file_workflow_path_stays_the_directory(self, tmp_path):
        spec_dir = _write_spec(tmp_path)
        _write_fsm_state(tmp_path)
        assert compile_spec(str(spec_dir)).workflow_path == str(spec_dir)

    def test_the_runtime_equivalent_precheck_follows_the_spec_file(self, two_specs):
        """--fsm-state-path 的預檢（D-SBR-04）以 playbook 所帶的 workflow_path 呼叫；
        若仍用目錄，兩份 TCS 的目錄會在預檢丟 ValueError 未捕捉 traceback。"""
        root, spec_dir = two_specs
        state = root / "build" / "reports" / "fsm" / "FSM-STATE-demo.yaml"
        out = root / "o.yaml"
        rc = main(["--spec-dir", str(spec_dir), "--spec-file", "03_testing/contracts/TCS-Alpha.md",
                   "--fsm-state-path", str(state), "--out", str(out)])
        assert rc == 0 and out.is_file()

    @pytest.fixture()
    def shared_state_dir(self, tmp_path):
        spec_dir = _write_spec(tmp_path)
        _write_state(tmp_path, "alpha", current="SPEC_FROZEN")
        _write_state(tmp_path, "zeta", current="INIT")
        return tmp_path, spec_dir

    def test_fsm_project_selects_the_state_file_of_that_project_only(self, shared_state_dir):
        """舊版取字母序第一份（alpha）⇒ zeta 的規格也過；現在只認被指定者。"""
        root, spec_dir = shared_state_dir
        out = root / "o.yaml"
        assert main(["--spec-dir", str(spec_dir), "--fsm-project", "alpha",
                     "--out", str(out)]) == 0
        out.unlink()
        assert main(["--spec-dir", str(spec_dir), "--fsm-project", "zeta",
                     "--out", str(out)]) == 2
        assert not out.exists()

    def test_several_state_files_and_no_project_exit_2(self, shared_state_dir, capsys):
        root, spec_dir = shared_state_dir
        rc = main(["--spec-dir", str(spec_dir), "--out", str(root / "o.yaml")])
        assert rc == 2 and "不唯一" in capsys.readouterr().err

    def test_the_environment_variable_is_the_default_project_and_empty_string_opts_out(
            self, shared_state_dir, monkeypatch):
        root, spec_dir = shared_state_dir
        monkeypatch.setenv("SDD_PROJECT", "alpha")
        assert main(["--spec-dir", str(spec_dir), "--out", str(root / "env.yaml")]) == 0
        assert main(["--spec-dir", str(spec_dir), "--fsm-project", "",
                     "--out", str(root / "none.yaml")]) == 2
