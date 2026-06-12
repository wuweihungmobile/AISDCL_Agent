"""W6（AutoSDD_improving_01 §4）：SddGovernancePlugin 測試（coverage ≥90%）。

覆蓋：啟用判定 / 凍結 veto / SCG 越閘 deny / 違反記帳與清除 / 升級諮詢 /
checkpoint 掛載還原 / digest drift advisory / 攻防（越閘存取）。
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from autoclaude.core.hookspec import (
    CounterSnapshotResult,
    HookContext,
    KernelPhase,
    VetoResult,
)
from autoclaude.core.ports.observability import NullObservability
from autoclaude.core.ports.spec_source import (
    SddSpec,
    SpecContract,
    SpecNotFrozenError,
)
from autoclaude.models.playbook import Playbook, PlaybookTask
from autoclaude.plugins.sdd_governance_plugin import SddGovernancePlugin
from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint


class _SpyObs(NullObservability):
    def __init__(self):
        self.counters: list[tuple[str, dict]] = []
        self.events: list[tuple[str, dict]] = []

    def emit_counter(self, name, value=1, tags=None):
        self.counters.append((name, dict(tags or {})))

    def record_event(self, name, attributes=None):
        self.events.append((name, dict(attributes or {})))


def _spec(tmp_path: Path) -> SddSpec:
    spec_file = tmp_path / "TCS-Demo.md"
    spec_file.write_text("spec body", encoding="utf-8")
    digest = "sha256:" + hashlib.sha256(b"spec body").hexdigest()
    return SddSpec(
        spec_path=str(spec_file), digest=digest, scenario="testing",
        contracts=(
            SpecContract("AC-001-1", "AT-001-1-1", "g1", "ok", "python -m pytest t -q",
                         "SCG-4"),
            SpecContract("AC-002-1", "AT-002-1-1", "g2", "ok", "python -m pytest t -q",
                         "SCG-5"),
        ),
    )


class _StubSource:
    def __init__(self, spec=None, frozen=True):
        self._spec, self._frozen = spec, frozen

    def load_spec(self, spec_dir):
        if not self._frozen:
            raise SpecNotFrozenError(spec_dir)
        return self._spec

    def compile_tasks(self, spec):
        return []


def _playbook(workflow_type="aisdlc_sdd", workflow_path="docs/"):
    return Playbook(
        project="p", workflow_type=workflow_type, workflow_path=workflow_path,
        tasks=[
            PlaybookTask(step_id="sdd-testing-at-001-1-1", name="a", prompt="x"),
            PlaybookTask(step_id="sdd-testing-at-002-1-1", name="b", prompt="y"),
        ],
    )


def _ctx(phase, playbook, task=None, payload=None, **kw):
    return HookContext(phase=phase, playbook=playbook, task=task,
                       payload=payload or {}, **kw)


def _activated_plugin(tmp_path, brain=None, obs=None):
    spec = _spec(tmp_path)
    plugin = SddGovernancePlugin(
        brain=brain, observability=obs, spec_source=_StubSource(spec))
    pb = _playbook()
    assert plugin.on_event(_ctx(KernelPhase.PRE_RUN, pb)) is None
    return plugin, pb, spec


class TestActivation:
    def test_non_sdd_workflow_inactive(self, tmp_path):
        plugin = SddGovernancePlugin(spec_source=_StubSource(_spec(tmp_path)))
        pb = _playbook(workflow_type="auto")
        assert plugin.on_event(_ctx(KernelPhase.PRE_RUN, pb)) is None
        # inactive：後續 phase 全 no-op
        assert plugin.on_event(
            _ctx(KernelPhase.PRE_ATTEMPT, pb, task=pb.tasks[0])) is None
        assert plugin.snapshot()["spec_digest"] is None

    def test_not_frozen_spec_vetoes_pre_run(self, tmp_path):
        obs = _SpyObs()
        plugin = SddGovernancePlugin(
            observability=obs, spec_source=_StubSource(frozen=False))
        result = plugin.on_event(_ctx(KernelPhase.PRE_RUN, _playbook()))
        assert isinstance(result, VetoResult)
        assert "SDD-VIOLATION[SPEC_NOT_FROZEN]" in result.reason
        assert ("sdd.scg_gate_fail", {"gate": "SPEC_FROZEN"}) in obs.counters

    def test_missing_workflow_path_degrades_to_passive(self, tmp_path):
        obs = _SpyObs()
        plugin = SddGovernancePlugin(
            observability=obs, spec_source=_StubSource(_spec(tmp_path)))
        pb = _playbook(workflow_path=None)
        assert plugin.on_event(_ctx(KernelPhase.PRE_RUN, pb)) is None
        assert obs.events[0][0] == "sdd.spec_dir_missing"

    def test_activation_loads_digest_and_gate_map(self, tmp_path):
        plugin, _, spec = _activated_plugin(tmp_path)
        snap = plugin.snapshot()
        assert snap["spec_digest"] == spec.digest
        assert snap["fsm_state"] == "IMPLEMENTATION"


class TestGateEnforcement:
    def test_clean_state_allows_attempt_and_tracks_gate(self, tmp_path):
        plugin, pb, _ = _activated_plugin(tmp_path)
        assert plugin.on_event(
            _ctx(KernelPhase.PRE_ATTEMPT, pb, task=pb.tasks[0])) is None
        assert plugin.snapshot()["scg_gate"] == "SCG-4"

    def test_cross_gate_violation_denied(self, tmp_path):
        """攻防：SCG-4 仍有未解違反時，SCG-5 步驟越閘 → VetoResult。"""
        obs = _SpyObs()
        plugin, pb, _ = _activated_plugin(tmp_path, obs=obs)
        plugin.on_event(_ctx(
            KernelPhase.POST_ATTEMPT, pb, task=pb.tasks[0],
            payload={"failure_reason": "regex miss"}))
        veto = plugin.on_event(_ctx(KernelPhase.PRE_ATTEMPT, pb, task=pb.tasks[1]))
        assert isinstance(veto, VetoResult)
        assert "SDD-VIOLATION[AT-002-1-1]" in veto.reason
        assert ("sdd.scg_gate_fail", {"gate": "SCG-5"}) in obs.counters

    def test_same_gate_violation_not_blocking(self, tmp_path):
        plugin, pb, _ = _activated_plugin(tmp_path)
        plugin.on_event(_ctx(
            KernelPhase.POST_ATTEMPT, pb, task=pb.tasks[0],
            payload={"failure_reason": "fail"}))
        # 同 SCG-4 步驟重試不被閘（retry 屬既有 max_retries 管轄）
        assert plugin.on_event(
            _ctx(KernelPhase.PRE_ATTEMPT, pb, task=pb.tasks[0])) is None

    def test_success_clears_violations_and_unblocks(self, tmp_path):
        plugin, pb, _ = _activated_plugin(tmp_path)
        plugin.on_event(_ctx(
            KernelPhase.POST_ATTEMPT, pb, task=pb.tasks[0],
            payload={"failure_reason": "fail"}))
        plugin.on_event(_ctx(KernelPhase.ON_SUCCESS, pb, task=pb.tasks[0]))
        assert plugin.snapshot()["contract_violations"] == []
        assert plugin.on_event(
            _ctx(KernelPhase.PRE_ATTEMPT, pb, task=pb.tasks[1])) is None

    def test_non_sdd_step_not_gated(self, tmp_path):
        plugin, pb, _ = _activated_plugin(tmp_path)
        other = PlaybookTask(step_id="T99", name="n", prompt="p")
        assert plugin.on_event(_ctx(KernelPhase.PRE_ATTEMPT, pb, task=other)) is None


class TestViolationLedger:
    def test_violation_recorded_with_at_id_and_event(self, tmp_path):
        obs = _SpyObs()
        plugin, pb, _ = _activated_plugin(tmp_path, obs=obs)
        plugin.on_event(_ctx(
            KernelPhase.POST_ATTEMPT, pb, task=pb.tasks[0],
            payload={"failure_reason": "assertion failed"}))
        v = plugin.snapshot()["contract_violations"][0]
        assert v["at_id"] == "AT-001-1-1" and v["reason"] == "assertion failed"
        assert any(n == "sdd.contract_violation" for n, _ in obs.events)

    def test_success_payload_not_recorded(self, tmp_path):
        plugin, pb, _ = _activated_plugin(tmp_path)
        plugin.on_event(_ctx(KernelPhase.POST_ATTEMPT, pb, task=pb.tasks[0],
                             payload={}))  # 無 failure_reason
        assert plugin.snapshot()["contract_violations"] == []


class TestEscalationConsult:
    class _SpyBrain:
        def __init__(self, fail=False):
            self.calls, self._fail = [], fail

        def decide_escalation(self, **kw):
            if self._fail:
                raise RuntimeError("minimax down")
            self.calls.append(kw)
            return None

    def _saturate(self, plugin, pb, n=3):
        for _ in range(n):
            plugin.on_event(_ctx(
                KernelPhase.POST_ATTEMPT, pb, task=pb.tasks[0],
                payload={"failure_reason": "same pattern"}))

    def test_threshold_triggers_brain_consult(self, tmp_path):
        brain = self._SpyBrain()
        obs = _SpyObs()
        plugin, pb, _ = _activated_plugin(tmp_path, brain=brain, obs=obs)
        self._saturate(plugin, pb)
        plugin.on_event(_ctx(KernelPhase.ON_FAILURE, pb, task=pb.tasks[0]))
        assert len(brain.calls) == 1
        assert brain.calls[0]["convergence_trend"] == "sdd_contract_violation"
        assert len(brain.calls[0]["failure_history"]) == 3
        assert any(n == "sdd.escalation_consult" for n, _ in obs.events)

    def test_below_threshold_no_consult(self, tmp_path):
        brain = self._SpyBrain()
        plugin, pb, _ = _activated_plugin(tmp_path, brain=brain)
        self._saturate(plugin, pb, n=2)
        plugin.on_event(_ctx(KernelPhase.ON_FAILURE, pb, task=pb.tasks[0]))
        assert brain.calls == []

    def test_brain_failure_does_not_propagate(self, tmp_path):
        brain = self._SpyBrain(fail=True)
        plugin, pb, _ = _activated_plugin(tmp_path, brain=brain)
        self._saturate(plugin, pb)
        plugin.on_event(_ctx(KernelPhase.ON_FAILURE, pb, task=pb.tasks[0]))  # 不拋例外


class TestCheckpointMount:
    def test_save_request_returns_counter_snapshot_result(self, tmp_path):
        plugin, pb, spec = _activated_plugin(tmp_path)
        result = plugin.on_event(_ctx(KernelPhase.ON_CHECKPOINT_SAVE_REQUEST, pb))
        assert isinstance(result, CounterSnapshotResult)
        assert result.snapshot["sdd_governance"]["spec_digest"] == spec.digest

    def test_restore_from_checkpoint_payload(self, tmp_path):
        plugin, pb, _ = _activated_plugin(tmp_path)
        cp = PlaybookCheckpoint(
            playbook_path="x.yaml", step_idx=0, step_id="s", total_steps=2,
            sdd_governance={"scg_gate": "SCG-5", "fsm_state": "PR_REVIEW",
                            "contract_violations": [{"step_id": "s", "at_id": "A"}],
                            "spec_digest": plugin.snapshot()["spec_digest"]})
        plugin.on_event(_ctx(KernelPhase.ON_CHECKPOINT_RESTORE, pb,
                             payload={"checkpoint": cp}))
        snap = plugin.snapshot()
        assert snap["scg_gate"] == "SCG-5"
        assert snap["contract_violations"] == [{"step_id": "s", "at_id": "A"}]

    def test_restore_digest_mismatch_is_advisory(self, tmp_path):
        obs = _SpyObs()
        plugin, pb, _ = _activated_plugin(tmp_path, obs=obs)
        cp = PlaybookCheckpoint(
            playbook_path="x.yaml", step_idx=0, step_id="s", total_steps=2,
            sdd_governance={"spec_digest": "sha256:other"})
        plugin.on_event(_ctx(KernelPhase.ON_CHECKPOINT_RESTORE, pb,
                             payload={"checkpoint": cp}))
        assert any(n == "sdd.spec_digest_mismatch" for n, _ in obs.events)
        # 凍結中的 digest 不被舊值覆寫
        assert plugin.snapshot()["spec_digest"] != "sha256:other"


class TestDriftAdvisory:
    def test_spec_file_mutation_emits_drift_event(self, tmp_path):
        obs = _SpyObs()
        plugin, pb, spec = _activated_plugin(tmp_path, obs=obs)
        Path(spec.spec_path).write_text("tampered", encoding="utf-8")
        plugin.on_event(_ctx(KernelPhase.ON_SUCCESS, pb, task=pb.tasks[0]))
        drift = [a for n, a in obs.events if n == "sdd.spec_drift"]
        assert drift and drift[0]["frozen_digest"] == spec.digest

    def test_unchanged_spec_no_drift_event(self, tmp_path):
        obs = _SpyObs()
        plugin, pb, _ = _activated_plugin(tmp_path, obs=obs)
        plugin.on_event(_ctx(KernelPhase.ON_SUCCESS, pb, task=pb.tasks[0]))
        assert not any(n == "sdd.spec_drift" for n, _ in obs.events)


class TestPluginContract:
    def test_priority_45_between_persistence_and_tiebreakers(self):
        assert SddGovernancePlugin.PRIORITY == 45

    def test_name(self):
        assert SddGovernancePlugin().name() == "sdd_governance"

    def test_subscribed_phases_cover_plan_and_dispatched(self):
        phases = set(SddGovernancePlugin().subscribed_phases())
        assert {KernelPhase.PRE_RUN, KernelPhase.PRE_ATTEMPT,
                KernelPhase.POST_ATTEMPT, KernelPhase.ON_SUCCESS,
                KernelPhase.ON_FAILURE, KernelPhase.POST_EVALUATE,
                KernelPhase.ON_ESCALATION,
                KernelPhase.ON_CHECKPOINT_SAVE_REQUEST,
                KernelPhase.ON_CHECKPOINT_RESTORE} <= phases
