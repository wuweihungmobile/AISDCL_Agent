"""RtmWritebackPlugin 單元測試（AutoSDD_improving_24 A 軌 W-24-2）。

RTM AT 對應：
  - AT-24-2-1：POST_RUN 對 SDD playbook 寫出 coverage + gap 兩份報告
  - AT-24-2-2：非 SDD playbook 全程 no-op（零退化）
  - AT-24-2-3：adapter/sink 未注入 → no-op
  - AT-24-2-4：非 POST_RUN phase → no-op
  - AT-24-2-5：寫出失敗以 warning 吞掉，不阻斷（回傳 None）
  - AT-24-2-6：EventBus 整合 + digest 萃取
  - AT-24-2-7：閉環 round-trip（SddToPlaybookAdapter → 執行 → PlaybookToRtmAdapter）
"""
from __future__ import annotations

import json

import yaml

from autoclaude.core.event_bus import EventBus
from autoclaude.core.hookspec import HookContext, KernelPhase
from autoclaude.core.ports.spec_source import SddSpec, SpecContract
from autoclaude.infra.adapters.playbook_to_rtm_adapter import PlaybookToRtmAdapter
from autoclaude.infra.adapters.rtm_file_sink import FileRtmSink
from autoclaude.infra.adapters.sdd_to_playbook_adapter import SddToPlaybookAdapter
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.plugins import RtmWritebackPlugin


def _pb(tasks: list[PlaybookTask], project: str = "Demo") -> Playbook:
    return Playbook(
        version="1.0", project=project,
        global_invariants=GlobalInvariants(), tasks=tasks,
    )


def _sdd_pb() -> Playbook:
    return _pb([
        PlaybookTask(step_id="sdd-greenfield-at-001-1-1", name="AT-001-1-1", prompt="x（digest abcdef12）"),
        PlaybookTask(step_id="sdd-greenfield-at-001-2-1", name="AT-001-2-1", prompt="x"),
    ])


class _RecordingSink:
    def __init__(self):
        self.calls = []
        self.history = []  # improving_27 W3：append_report_line 記錄

    def write_report(self, report_name, content, *, fmt="yaml"):
        self.calls.append((report_name, content, fmt))
        return f"/fake/{report_name}.{fmt}"

    def append_report_line(self, report_name, line):
        self.history.append((report_name, line))
        return f"/fake/{report_name}.jsonl"


def _post_run_ctx(pb: Playbook, completed: list[str]) -> HookContext:
    return HookContext(
        phase=KernelPhase.POST_RUN, playbook=pb, task=None,
        payload={"completed_step_ids": completed, "total_steps": len(pb.tasks)},
    )


class TestRtmWritebackPlugin:
    def test_meta(self):
        p = RtmWritebackPlugin()
        assert p.name() == "rtm_writeback"
        assert p.priority() == 52
        assert p.subscribed_phases() == [KernelPhase.POST_RUN]

    def test_writes_two_reports_for_sdd_playbook(self):
        """AT-24-2-1：SDD playbook → coverage + gap 兩份報告。"""
        sink = _RecordingSink()
        plugin = RtmWritebackPlugin(adapter=PlaybookToRtmAdapter(), sink=sink)
        ctx = _post_run_ctx(_sdd_pb(), ["sdd-greenfield-at-001-1-1"])
        assert plugin.on_event(ctx) is None
        names = [c[0] for c in sink.calls]
        assert names == ["RTM-COVERAGE-Demo", "RTM-GAP-Demo"]
        # coverage 報告含 digest 萃取結果
        cov_doc = yaml.safe_load(sink.calls[0][1])
        assert cov_doc["spec_digest"] == "abcdef12"
        assert cov_doc["summary"]["passed_at"] == 1
        assert cov_doc["summary"]["total_at"] == 2

    def test_appends_history_snapshot_for_sdd_playbook(self):
        """AT-27-3-4（W3b）：SDD playbook POST_RUN 額外 append 一筆 history 快照。"""
        sink = _RecordingSink()
        plugin = RtmWritebackPlugin(adapter=PlaybookToRtmAdapter(), sink=sink)
        ctx = _post_run_ctx(_sdd_pb(), ["sdd-greenfield-at-001-1-1"])
        plugin.on_event(ctx)
        assert len(sink.history) == 1
        name, line = sink.history[0]
        assert name == "RTM-COVERAGE-HISTORY-Demo"
        # line 為單行 JSON，可還原為 coverage doc（與 read_history 對稱）
        doc = json.loads(line)
        assert doc["kind"] == "rtm-coverage"
        assert doc["summary"]["passed_at"] == 1
        assert doc["summary"]["total_at"] == 2

    def test_no_history_for_non_sdd_playbook(self):
        """W3b 零退化：非 SDD playbook → 不寫報告也不 append history。"""
        sink = _RecordingSink()
        plugin = RtmWritebackPlugin(adapter=PlaybookToRtmAdapter(), sink=sink)
        ctx = _post_run_ctx(_pb([PlaybookTask(step_id="T01", name="x", prompt="x")]), ["T01"])
        plugin.on_event(ctx)
        assert sink.calls == []
        assert sink.history == []

    def test_noop_for_non_sdd_playbook(self):
        """AT-24-2-2：非 SDD playbook → 不觸碰 sink（零退化）。"""
        sink = _RecordingSink()
        plugin = RtmWritebackPlugin(adapter=PlaybookToRtmAdapter(), sink=sink)
        ctx = _post_run_ctx(_pb([PlaybookTask(step_id="T01", name="s", prompt="p")]), ["T01"])
        assert plugin.on_event(ctx) is None
        assert sink.calls == []

    def test_noop_when_deps_missing(self):
        """AT-24-2-3：adapter/sink 未注入 → no-op。"""
        plugin = RtmWritebackPlugin()  # 皆 None
        assert plugin.on_event(_post_run_ctx(_sdd_pb(), [])) is None

    def test_noop_for_other_phase(self):
        """AT-24-2-4：非 POST_RUN → no-op。"""
        sink = _RecordingSink()
        plugin = RtmWritebackPlugin(adapter=PlaybookToRtmAdapter(), sink=sink)
        ctx = HookContext(phase=KernelPhase.PRE_RUN, playbook=_sdd_pb(), task=None, payload={})
        assert plugin.on_event(ctx) is None
        assert sink.calls == []

    def test_writeback_failure_swallowed(self):
        """AT-24-2-5：sink 拋例外 → warning 吞掉、回傳 None、不傳播。"""
        class _BoomSink:
            def write_report(self, *a, **k):
                raise RuntimeError("disk full")

        plugin = RtmWritebackPlugin(adapter=PlaybookToRtmAdapter(), sink=_BoomSink())
        assert plugin.on_event(_post_run_ctx(_sdd_pb(), [])) is None

    def test_no_digest_in_prompt_yields_empty_digest(self):
        """prompt 無 digest 字樣 → spec_digest 留空（不報錯）。"""
        sink = _RecordingSink()
        plugin = RtmWritebackPlugin(adapter=PlaybookToRtmAdapter(), sink=sink)
        pb = _pb([PlaybookTask(step_id="sdd-greenfield-at-002-1-1", name="AT-002-1-1", prompt="no fingerprint here")])
        plugin.on_event(_post_run_ctx(pb, []))
        cov_doc = yaml.safe_load(sink.calls[0][1])
        assert cov_doc["spec_digest"] == ""

    def test_missing_completed_payload_treated_empty(self):
        """payload 無 completed_step_ids → 視為全未通過（仍寫報告）。"""
        sink = _RecordingSink()
        plugin = RtmWritebackPlugin(adapter=PlaybookToRtmAdapter(), sink=sink)
        ctx = HookContext(
            phase=KernelPhase.POST_RUN, playbook=_sdd_pb(), task=None, payload={},
        )
        plugin.on_event(ctx)
        cov_doc = yaml.safe_load(sink.calls[0][1])
        assert cov_doc["summary"]["passed_at"] == 0


class TestEventBusIntegration:
    def test_via_bus_writes_files(self, tmp_path):
        """AT-24-2-6：經 EventBus emit POST_RUN，真實寫出兩檔到磁碟。"""
        bus = EventBus()
        sink = FileRtmSink(str(tmp_path / "rtm"))
        bus.register(RtmWritebackPlugin(adapter=PlaybookToRtmAdapter(), sink=sink))
        bus.emit(_post_run_ctx(_sdd_pb(), ["sdd-greenfield-at-001-1-1"]))
        files = sorted(p.name for p in (tmp_path / "rtm").iterdir())
        # improving_27 W3b：除既有 coverage/gap 兩檔，另 append 跨輪趨勢 history jsonl
        assert files == [
            "RTM-COVERAGE-Demo.yaml",
            "RTM-COVERAGE-HISTORY-Demo.jsonl",
            "RTM-GAP-Demo.md",
        ]


class TestClosureRoundTrip:
    def test_spec_to_playbook_to_rtm(self):
        """AT-24-2-7：閉環——SDD 規格編譯為 Playbook，模擬執行後還原 RTM 覆蓋度。

        驗證雙向橋接對稱性：forward step_id 與 reverse 解析一致。
        """
        spec = SddSpec(
            spec_path="docs/03_testing/TEST-CONTRACT-SPEC-Demo.md",
            digest="sha256:abcdef1234567890",
            scenario="greenfield",
            contracts=(
                SpecContract(
                    ac_id="AC-001-1", at_id="AT-001-1-1", gherkin="Given ... Then PASS",
                    expected_regex=r"\bPASS\b", evaluator_cmd='pytest tests -k "AT-001-1-1"',
                    scg_gate="SCG-4",
                ),
                SpecContract(
                    ac_id="AC-001-2", at_id="AT-001-2-1", gherkin="Given ... Then PASS",
                    expected_regex=r"\bPASS\b", evaluator_cmd='pytest tests -k "AT-001-2-1"',
                    scg_gate="SCG-4",
                ),
            ),
        )
        tasks = SddToPlaybookAdapter().compile_tasks(spec)
        assert len(tasks) == 2
        # 模擬：第一個 AT 通過、第二個失敗
        completed = [tasks[0].step_id]
        rep = PlaybookToRtmAdapter().compile_report(tasks, completed, spec_digest="abcdef12")
        assert rep.total_at == 2
        assert rep.passed_at == 1
        assert rep.scenario == "greenfield"
        assert rep.failed_at_ids == ("AT-001-2-1",)
        assert rep.ac_covered == 1 and rep.ac_total == 2
