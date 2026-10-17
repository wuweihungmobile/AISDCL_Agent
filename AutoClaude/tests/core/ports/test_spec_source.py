"""W1（AutoSDD_improving_01 §2.2）：ISpecSource port 契約測試。

驗證：
  1. SpecContract / SddSpec 為 frozen dataclass（不可變快照）
  2. ISpecSource 為 Protocol，最小 stub 即滿足結構型別
  3. SpecNotFrozenError / SpecTaintedError 例外階層正確
"""
from __future__ import annotations

import dataclasses
import re

import pytest

from autoclaude.core.ports.spec_source import (
    AT_ID_PATTERN,
    ISpecSource,
    SddSpec,
    SpecContract,
    SpecDigestMismatchError,
    SpecNotFrozenError,
    SpecTaintedError,
    ac_id_of_at,
)
from autoclaude.models.playbook import PlaybookTask


def _contract(**overrides) -> SpecContract:
    base = dict(
        ac_id="AC-001-1",
        at_id="AT-001-1-1",
        gherkin="Given X When Y Then 回傳 201 Created",
        expected_regex="(?i)(201|created)",
        evaluator_cmd='python -m pytest tests/test_x.py -k "AT-001-1-1" -q',
        scg_gate="SCG-4",
    )
    base.update(overrides)
    return SpecContract(**base)


class TestSpecContractDataclass:
    def test_frozen_immutable(self):
        c = _contract()
        with pytest.raises(dataclasses.FrozenInstanceError):
            c.ac_id = "AC-999-9"  # type: ignore[misc]

    def test_weak_regex_defaults_false(self):
        assert _contract().weak_regex is False

    def test_weak_regex_flag_settable(self):
        assert _contract(weak_regex=True).weak_regex is True


class TestSddSpecDataclass:
    def test_frozen_immutable(self):
        spec = SddSpec("docs/", "sha256:abc", "brownfield")
        with pytest.raises(dataclasses.FrozenInstanceError):
            spec.digest = "sha256:def"  # type: ignore[misc]

    def test_contracts_default_empty_tuple(self):
        spec = SddSpec("docs/", "sha256:abc", "brownfield")
        assert spec.contracts == ()

    def test_contracts_tuple_of_spec_contract(self):
        spec = SddSpec("docs/", "sha256:abc", "testing", contracts=(_contract(),))
        assert spec.contracts[0].at_id == "AT-001-1-1"


class _StubSource:
    """最小 stub：結構滿足 ISpecSource Protocol。"""

    def load_spec(self, spec_dir: str) -> SddSpec:
        return SddSpec(spec_dir, "sha256:stub", "greenfield", (_contract(),))

    def compile_tasks(self, spec: SddSpec) -> list[PlaybookTask]:
        return [
            PlaybookTask(
                step_id=f"sdd-{spec.scenario}-{c.at_id.lower()}",
                name=c.at_id,
                prompt=c.gherkin,
                expected_output_regex=c.expected_regex,
                evaluator_command=c.evaluator_cmd,
            )
            for c in spec.contracts
        ]


class TestISpecSourceProtocol:
    def test_stub_satisfies_protocol_structurally(self):
        src: ISpecSource = _StubSource()
        spec = src.load_spec("docs/")
        tasks = src.compile_tasks(spec)
        assert len(tasks) == 1
        assert tasks[0].step_id == "sdd-greenfield-at-001-1-1"
        assert tasks[0].expected_output_regex == "(?i)(201|created)"

    def test_compiled_task_is_playbook_task(self):
        src = _StubSource()
        task = src.compile_tasks(src.load_spec("docs/"))[0]
        assert isinstance(task, PlaybookTask)
        assert task.evaluator_command.startswith("python -m pytest")


class TestExceptions:
    def test_spec_not_frozen_is_runtime_error(self):
        assert issubclass(SpecNotFrozenError, RuntimeError)
        with pytest.raises(SpecNotFrozenError):
            raise SpecNotFrozenError("docs/")

    def test_spec_tainted_is_runtime_error(self):
        assert issubclass(SpecTaintedError, RuntimeError)
        with pytest.raises(SpecTaintedError):
            raise SpecTaintedError("`rm -rf /`")

    def test_digest_mismatch_is_a_not_frozen_error_so_existing_handlers_fail_closed(self):
        """ADR-XPLAT-016 §6.2：既有 `except SpecNotFrozenError`（plugin PRE_RUN veto、
        sdd_compile rc 2）自動 fail-closed；要區分的呼叫端（Bridge 409 vs 422）先接子類。"""
        assert issubclass(SpecDigestMismatchError, SpecNotFrozenError)
        with pytest.raises(SpecNotFrozenError):
            raise SpecDigestMismatchError("摘要不符")
        # 反向：父類不是子類——「根本沒凍結」不得被當成「內容變了」
        assert not issubclass(SpecNotFrozenError, SpecDigestMismatchError)


# ── improving_115（ADR-XPLAT-016 §8.1，D-115-16）：AT ID 文法的唯一定義 ─────────────────────
_ACCEPTED = [
    "AT-001-1-1", "AT-001-1", "AT-001-12-3-a", "AT-001-1-E1", "AT-001-1-E-1", "AT-029-1-1-1-1",
]
_REJECTED = [
    "AT-14-1-1",        # 首段非三位
    "AT-123", "AT-001",  # 缺第二段數字
    "AT-001-E-1",       # 第二段非數字（模板 §4 的編號：不可編譯）
    "AT-0001-1-1",      # 首段四位
    "AT-001-1-",        # 尾端孤立連字號
    "AT-001--1",        # 連續連字號
    "at-001-1-1",       # 小寫 at
    "AT-001-1-1_a",     # `_` 不在尾綴字元集
    "AT-001-1-1 x",     # 尾隨文字
    "AT-{NNN}-1-1",     # 模板佔位，根本不算 AT 字樣
]


class TestAtIdGrammar:
    def test_the_pattern_is_the_decided_literal(self):
        """D-115-16 定案的字面；正向與逆向 adapter 都由它組 regex，不得各寫一份。"""
        assert AT_ID_PATTERN == r"AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*"

    def test_seventeen_samples(self):
        assert len(_ACCEPTED) + len(_REJECTED) == 17

    @pytest.mark.parametrize("at_id", _ACCEPTED)
    def test_accepted_ids_fullmatch(self, at_id):
        assert re.fullmatch(AT_ID_PATTERN, at_id)

    @pytest.mark.parametrize("at_id", _REJECTED)
    def test_rejected_ids_do_not_fullmatch(self, at_id):
        assert not re.fullmatch(AT_ID_PATTERN, at_id)

    @pytest.mark.parametrize(("at_id", "ac_id"), [
        ("AT-001-1-1", "AC-001-1"),
        ("AT-001-1", "AC-001-1"),
        ("AT-001-12-3-a", "AC-001-12"),     # 多段尾綴不影響歸屬
        ("AT-001-1-E-1", "AC-001-1"),
        ("AT-029-1-1-1-1", "AC-029-1"),
    ])
    def test_the_first_two_numeric_segments_name_the_ac(self, at_id, ac_id):
        assert ac_id_of_at(at_id) == ac_id

    @pytest.mark.parametrize("at_id", _REJECTED)
    def test_ids_outside_the_grammar_belong_to_no_ac(self, at_id):
        assert ac_id_of_at(at_id) is None


class TestSddSpecNewFields:
    def test_the_three_new_fields_have_safe_defaults_so_old_constructions_still_work(self):
        spec = SddSpec("docs/", "sha256:abc", "brownfield", (_contract(),), "1.0")  # 舊的位置建構
        assert spec.fsm_project == ""
        assert spec.frozen_digest_status == "absent"  # 沒有任何東西被驗證的誠實值
        assert spec.unmapped_at_ids == ()

    def test_the_new_fields_are_settable_and_the_spec_stays_frozen(self):
        spec = SddSpec("docs/", "sha256:abc", "testing", fsm_project="alpha",
                       frozen_digest_status="verified", unmapped_at_ids=("AT-001-E-1",))
        assert (spec.fsm_project, spec.frozen_digest_status) == ("alpha", "verified")
        assert spec.unmapped_at_ids == ("AT-001-E-1",)
        with pytest.raises(dataclasses.FrozenInstanceError):
            spec.frozen_digest_status = "absent"  # type: ignore[misc]
