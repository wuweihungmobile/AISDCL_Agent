"""TranslationLearnerPlugin 測試（AutoSDD_improving_60，R-60-2~6）。

Rule 9：測試編碼「為何」——A→L5 活體化必須同時滿足
  (活體) 預設 ON 自跨 session history 元學習提議；
  (零退化) opt-out（config/env）、非 SDD playbook、無注入、fail-soft 一律 no-op；
  (紅線) proposals 恆 proposed、絕不自動套用（plugin 無 adapter ref，只寫 sink）；
  (守界) 提議數有界、dedup 跨 session 收斂。
"""
from __future__ import annotations

from unittest.mock import MagicMock

from autoclaude.core.hookspec import HookContext, KernelPhase
from autoclaude.core.ports.rtm_sink import RtmCoverageReport
from autoclaude.infra.adapters.translation_learning_sink import (
    FileTranslationLearningSink,
)
from autoclaude.models.playbook import Playbook, PlaybookTask
from autoclaude.plugins.translation_learner_plugin import TranslationLearnerPlugin


def _report(failed):
    return RtmCoverageReport(
        scenario="brownfield", spec_digest="sha256:x",
        total_at=5, passed_at=5 - len(failed), failed_at_ids=tuple(failed),
    )


def _pb(workflow_type="aisdlc_sdd") -> Playbook:
    return Playbook(
        version="1.0", project="SddProj", workflow_type=workflow_type,
        tasks=[PlaybookTask(step_id="sdd-x", name="t", prompt="p")],
    )


def _ctx(workflow_type="aisdlc_sdd") -> HookContext:
    return HookContext(phase=KernelPhase.POST_RUN, playbook=_pb(workflow_type))


def _feedback(history):
    fb = MagicMock()
    fb.read_history.return_value = tuple(history)
    return fb


def _plugin(tmp_path, **kw):
    sink = FileTranslationLearningSink(str(tmp_path))
    fb = kw.pop("rtm_feedback", _feedback([_report(["AT-001"]), _report(["AT-001"])]))
    return TranslationLearnerPlugin(sink=sink, rtm_feedback=fb, **kw), sink


class TestBasics:
    def test_name_priority_phase(self):
        p, _ = _plugin_default()
        assert p.name() == "translation_learner"
        assert p.priority() == 55
        assert p.subscribed_phases() == [KernelPhase.POST_RUN]


def _plugin_default():
    sink = MagicMock()
    sink.list_proposals.return_value = ()
    fb = _feedback([_report(["AT-001"]), _report(["AT-001"])])
    return TranslationLearnerPlugin(sink=sink, rtm_feedback=fb), sink


class TestLiveActivation:
    def test_default_on_proposes_from_history(self, tmp_path, monkeypatch):
        """活體：env 未設 + config 預設 ON → 跨 session 重複失敗 → 提議。"""
        monkeypatch.delenv("AUTOCLAUDE_ENABLE_TRANSLATION_AUTO_PROPOSE", raising=False)
        p, sink = _plugin(tmp_path)  # enabled 預設 True
        p.on_event(_ctx())
        out = sink.list_proposals("SddProj")
        assert [x.at_id for x in out] == ["AT-001"]
        assert out[0].status == "proposed"

    def test_recorded_proposals_all_proposed_status(self, tmp_path, monkeypatch):
        """紅線：所有提議恆 proposed（絕不自動 verified/applied）。"""
        monkeypatch.delenv("AUTOCLAUDE_ENABLE_TRANSLATION_AUTO_PROPOSE", raising=False)
        fb = _feedback([_report(["AT-001", "AT-002"]), _report(["AT-001", "AT-002"])])
        p, sink = _plugin(tmp_path, rtm_feedback=fb)
        p.on_event(_ctx())
        assert all(x.status == "proposed" for x in sink.list_proposals("SddProj"))


class TestZeroRegression:
    def test_config_opt_out_noop(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AUTOCLAUDE_ENABLE_TRANSLATION_AUTO_PROPOSE", raising=False)
        p, sink = _plugin(tmp_path, enabled=False)
        p.on_event(_ctx())
        assert sink.list_proposals("SddProj") == ()

    def test_env_opt_out_noop(self, tmp_path, monkeypatch):
        """env 顯式 opt-out → no-op，即使 config 預設 ON。"""
        monkeypatch.setenv("AUTOCLAUDE_ENABLE_TRANSLATION_AUTO_PROPOSE", "0")
        p, sink = _plugin(tmp_path)  # enabled=True
        p.on_event(_ctx())
        assert sink.list_proposals("SddProj") == ()

    def test_non_sdd_playbook_noop(self, tmp_path, monkeypatch):
        """非 aisdlc_sdd workflow → no-op，即使有失敗 history。"""
        monkeypatch.delenv("AUTOCLAUDE_ENABLE_TRANSLATION_AUTO_PROPOSE", raising=False)
        p, sink = _plugin(tmp_path)
        p.on_event(_ctx(workflow_type="auto"))
        assert sink.list_proposals("SddProj") == ()

    def test_no_injection_noop(self):
        p = TranslationLearnerPlugin(sink=None, rtm_feedback=None)
        assert p.on_event(_ctx()) is None

    def test_wrong_phase_noop(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AUTOCLAUDE_ENABLE_TRANSLATION_AUTO_PROPOSE", raising=False)
        p, sink = _plugin(tmp_path)
        ctx = HookContext(phase=KernelPhase.PRE_RUN, playbook=_pb())
        p.on_event(ctx)
        assert sink.list_proposals("SddProj") == ()

    def test_fail_soft_on_feedback_error(self, tmp_path, monkeypatch):
        """rtm_feedback 讀回拋例外 → fail-soft，不 raise、不崩潰。"""
        monkeypatch.delenv("AUTOCLAUDE_ENABLE_TRANSLATION_AUTO_PROPOSE", raising=False)
        fb = MagicMock()
        fb.read_history.side_effect = RuntimeError("boom")
        p, sink = _plugin(tmp_path, rtm_feedback=fb)
        assert p.on_event(_ctx()) is None  # 不拋例外


class TestBoundedAndDedup:
    def test_bounded_cap(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AUTOCLAUDE_ENABLE_TRANSLATION_AUTO_PROPOSE", raising=False)
        failing = [f"AT-{i:03d}" for i in range(6)]
        fb = _feedback([_report(failing), _report(failing)])
        p, sink = _plugin(tmp_path, rtm_feedback=fb, max_proposals_per_run=2)
        p.on_event(_ctx())
        assert len(sink.list_proposals("SddProj")) == 2

    def test_dedup_across_sessions(self, tmp_path, monkeypatch):
        """第二次 run 不重複提議已提議過的 at_id（跨 session 收斂）。"""
        monkeypatch.delenv("AUTOCLAUDE_ENABLE_TRANSLATION_AUTO_PROPOSE", raising=False)
        p, sink = _plugin(tmp_path)
        p.on_event(_ctx())
        first = len(sink.list_proposals("SddProj"))
        p.on_event(_ctx())  # 再跑一次，AT-001 已提議過
        assert len(sink.list_proposals("SddProj")) == first  # 無新增

    def test_observability_emitted(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AUTOCLAUDE_ENABLE_TRANSLATION_AUTO_PROPOSE", raising=False)
        obs = MagicMock()
        p, sink = _plugin(tmp_path, observability=obs)
        p.on_event(_ctx())
        assert obs.record_event.called
        evt, payload = obs.record_event.call_args[0]
        assert evt == "sdd.translation_proposal"
        assert payload["status"] == "proposed"


def _wreport(failed=(), weak=()):
    return RtmCoverageReport(
        scenario="brownfield", spec_digest="sha256:x",
        total_at=5, passed_at=5 - len(failed), failed_at_ids=tuple(failed),
        weak_regex_at_ids=tuple(weak),
    )


class TestWeakRegexSecondSignal:
    """improving_61 W-61-3 / R-61-9：plugin 將 min_weak_runs 接到 select_proposals，
    使 weak_regex 第二信號（即使零執行失敗）也能驅動提議，並寫出 weak_runs。"""

    def test_weak_signal_drives_proposal(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AUTOCLAUDE_ENABLE_TRANSLATION_AUTO_PROPOSE", raising=False)
        fb = _feedback([_wreport(weak=["AT-009"]), _wreport(weak=["AT-009"])])
        p, sink = _plugin(tmp_path, rtm_feedback=fb)  # 預設 min_weak_runs=2
        p.on_event(_ctx())
        out = sink.list_proposals("SddProj")
        assert [x.at_id for x in out] == ["AT-009"]
        assert out[0].failing_runs == 0 and out[0].weak_runs == 2

    def test_min_weak_runs_threaded(self, tmp_path, monkeypatch):
        """提高 min_weak_runs=3 → weak=2 不達門檻 → no-op（門檻確實接到純函數）。"""
        monkeypatch.delenv("AUTOCLAUDE_ENABLE_TRANSLATION_AUTO_PROPOSE", raising=False)
        fb = _feedback([_wreport(weak=["AT-009"]), _wreport(weak=["AT-009"])])
        p, sink = _plugin(tmp_path, rtm_feedback=fb, min_weak_runs=3)
        p.on_event(_ctx())
        assert sink.list_proposals("SddProj") == ()

    def test_observability_emits_weak_runs(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AUTOCLAUDE_ENABLE_TRANSLATION_AUTO_PROPOSE", raising=False)
        obs = MagicMock()
        fb = _feedback([_wreport(weak=["AT-009"]), _wreport(weak=["AT-009"])])
        p, sink = _plugin(tmp_path, rtm_feedback=fb, observability=obs)
        p.on_event(_ctx())
        _evt, payload = obs.record_event.call_args[0]
        assert payload["weak_runs"] == 2
