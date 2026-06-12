"""W1（AutoSDD_improving_01 §2.2）：ISpecSource port 契約測試。

驗證：
  1. SpecContract / SddSpec 為 frozen dataclass（不可變快照）
  2. ISpecSource 為 Protocol，最小 stub 即滿足結構型別
  3. SpecNotFrozenError / SpecTaintedError 例外階層正確
"""
from __future__ import annotations

import dataclasses

import pytest

from autoclaude.core.ports.spec_source import (
    ISpecSource,
    SddSpec,
    SpecContract,
    SpecNotFrozenError,
    SpecTaintedError,
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
