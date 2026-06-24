"""PlaybookToRtmAdapter + RtmCoverageReport 單元測試（AutoSDD_improving_24 A 軌 W-24-1）。

RTM AT 對應：
  - AT-24-1-1：SDD task 還原 AC/AT 覆蓋度（pass/fail 判定）
  - AT-24-1-2：非 SDD task 一律忽略（零退化）
  - AT-24-1-3：completed 去重防覆蓋率 >100%（GOTO 回跳）
  - AT-24-1-4：AC 級保守判定（全部 AT 通過才算覆蓋）
  - AT-24-1-5：step_id 反解（task.name 缺失時 fallback）
  - AT-24-1-6：render YAML / gap Markdown 確定性與正確性
"""
from __future__ import annotations

import yaml

from autoclaude.core.ports.rtm_sink import NullRtmSink, RtmCoverageReport
from autoclaude.infra.adapters.playbook_to_rtm_adapter import PlaybookToRtmAdapter
from autoclaude.models.playbook import PlaybookTask


def _task(step_id: str, name: str = "", prompt: str = "x") -> PlaybookTask:
    return PlaybookTask(step_id=step_id, name=name, prompt=prompt)


def _sdd_tasks() -> list[PlaybookTask]:
    return [
        _task("sdd-greenfield-at-001-1-1", "AT-001-1-1", "impl x（digest abcdef12）"),
        _task("sdd-greenfield-at-001-1-2", "AT-001-1-2"),
        _task("sdd-greenfield-at-001-2-1", "AT-001-2-1"),
        _task("T99", "non-sdd"),  # AT-24-1-2：非 SDD 應被忽略
    ]


class TestCompileReport:
    def test_basic_pass_fail(self):
        """AT-24-1-1：通過/未通過正確分類，覆蓋率正確。"""
        ad = PlaybookToRtmAdapter()
        completed = ["sdd-greenfield-at-001-1-1", "sdd-greenfield-at-001-2-1"]
        rep = ad.compile_report(_sdd_tasks(), completed, spec_digest="abcdef12")
        assert rep.total_at == 3  # 非 SDD task 不計入
        assert rep.passed_at == 2
        assert rep.coverage_pct == round(100.0 * 2 / 3, 2)
        assert rep.failed_at_ids == ("AT-001-1-2",)
        assert rep.scenario == "greenfield"
        assert rep.spec_digest == "abcdef12"

    def test_non_sdd_tasks_ignored(self):
        """AT-24-1-2：純非 SDD playbook → 空報告（零退化路徑）。"""
        ad = PlaybookToRtmAdapter()
        rep = ad.compile_report([_task("T01", "step")], ["T01"])
        assert rep.total_at == 0
        assert rep.passed_at == 0
        assert rep.coverage_pct == 0.0
        assert rep.ac_total == 0
        assert rep.is_fully_covered is False

    def test_completed_dedup(self):
        """AT-24-1-3：completed 含重複（GOTO 回跳）不致覆蓋率 >100%。"""
        ad = PlaybookToRtmAdapter()
        completed = ["sdd-greenfield-at-001-1-1"] * 5
        rep = ad.compile_report(_sdd_tasks(), completed)
        assert rep.passed_at == 1
        assert rep.coverage_pct <= 100.0

    def test_ac_conservative_coverage(self):
        """AT-24-1-4：AC-001-1 有兩 AT，僅一通過 → 不算覆蓋；AC-001-2 全過 → 覆蓋。"""
        ad = PlaybookToRtmAdapter()
        completed = ["sdd-greenfield-at-001-1-1", "sdd-greenfield-at-001-2-1"]
        rep = ad.compile_report(_sdd_tasks(), completed)
        cov = dict((ac, (p, t)) for ac, p, t in rep.ac_coverage)
        assert cov["AC-001-1"] == (1, 2)  # partial
        assert cov["AC-001-2"] == (1, 1)  # full
        assert rep.ac_total == 2
        assert rep.ac_covered == 1
        assert rep.is_fully_covered is False

    def test_fully_covered(self):
        """全部 AT 通過 → is_fully_covered 為 True（SCG-5 判準）。"""
        ad = PlaybookToRtmAdapter()
        all_ids = [t.step_id for t in _sdd_tasks() if t.step_id.startswith("sdd-")]
        rep = ad.compile_report(_sdd_tasks(), all_ids)
        assert rep.passed_at == 3
        assert rep.coverage_pct == 100.0
        assert rep.is_fully_covered is True

    def test_step_id_reverse_when_name_missing(self):
        """AT-24-1-5：task.name 非 AT 格式時，自 step_id 反解 at_id。"""
        ad = PlaybookToRtmAdapter()
        tasks = [_task("sdd-brownfield-at-007-3-2", name="")]  # name 缺
        rep = ad.compile_report(tasks, ["sdd-brownfield-at-007-3-2"])
        assert rep.total_at == 1
        assert rep.passed_at == 1
        assert rep.scenario == "brownfield"
        assert dict((ac, (p, t)) for ac, p, t in rep.ac_coverage) == {"AC-007-3": (1, 1)}

    def test_empty_inputs(self):
        ad = PlaybookToRtmAdapter()
        rep = ad.compile_report([], [])
        assert rep.total_at == 0 and rep.scenario == ""

    def test_unresolvable_sdd_step_recorded_and_skipped(self):
        """sdd- 前綴但無法還原 at_id（畸形 step_id）→ 記事件並跳過，不計入。"""
        events = []

        class _Obs:
            def emit_counter(self, *a, **k): pass
            def emit_histogram(self, *a, **k): pass
            def start_span(self, *a, **k): raise AssertionError("unused")
            def record_event(self, name, attributes=None):
                events.append(name)

        ad = PlaybookToRtmAdapter(observability=_Obs())
        tasks = [_task("sdd-greenfield-malformed", name="")]  # 無 -at- 段、name 非 AT
        rep = ad.compile_report(tasks, [])
        assert rep.total_at == 0  # 畸形任務不計入
        assert "rtm_writeback_unresolved_step" in events


class TestRender:
    def test_render_yaml_roundtrip(self):
        """AT-24-1-6：YAML 可被 safe_load 還原，欄位正確。"""
        ad = PlaybookToRtmAdapter()
        rep = ad.compile_report(_sdd_tasks(), ["sdd-greenfield-at-001-2-1"])
        out = ad.render_yaml(rep, generated_at="2026-06-17T00:00:00Z")
        doc = yaml.safe_load(out)
        assert doc["kind"] == "rtm-coverage"
        assert doc["scenario"] == "greenfield"
        assert doc["summary"]["total_at"] == 3
        assert doc["summary"]["passed_at"] == 1
        assert doc["generated_at"] == "2026-06-17T00:00:00Z"
        assert {e["ac_id"] for e in doc["ac_coverage"]} == {"AC-001-1", "AC-001-2"}

    def test_render_yaml_omits_timestamp_when_none(self):
        ad = PlaybookToRtmAdapter()
        rep = ad.compile_report(_sdd_tasks(), [])
        doc = yaml.safe_load(ad.render_yaml(rep))
        assert "generated_at" not in doc

    def test_gap_markdown_lists_uncovered(self):
        ad = PlaybookToRtmAdapter()
        rep = ad.compile_report(_sdd_tasks(), ["sdd-greenfield-at-001-2-1"])
        md = ad.render_gap_markdown(rep)
        assert "RTM Gap Analysis" in md
        assert "AC-001-1" in md  # partial → 列入未覆蓋
        assert "AT-001-1-1" in md  # 未通過 AT
        assert "❌" in md

    def test_gap_markdown_clean_when_full(self):
        ad = PlaybookToRtmAdapter()
        all_ids = [t.step_id for t in _sdd_tasks() if t.step_id.startswith("sdd-")]
        md = ad.render_gap_markdown(ad.compile_report(_sdd_tasks(), all_ids))
        assert "無 gap" in md
        assert "✅" in md


class TestRtmCoverageReportProps:
    def test_zero_total_safe(self):
        rep = RtmCoverageReport(scenario="", spec_digest="", total_at=0, passed_at=0)
        assert rep.coverage_pct == 0.0
        assert rep.ac_coverage_pct == 0.0
        assert rep.is_fully_covered is False

    def test_null_sink_noop(self):
        assert NullRtmSink().write_report("a", "b") == ""


class TestWeakRegexCollection:
    """improving_61 W-61-1 / R-61-2：compile_report 收集 weak_regex task 的 at_id
    為 weak_regex_at_ids（第二元學習信號），與 failed_at_ids 正交。"""

    @staticmethod
    def _tasks_with_weak() -> list[PlaybookTask]:
        return [
            PlaybookTask(step_id="sdd-greenfield-at-001-1-1", name="AT-001-1-1",
                         prompt="x", weak_regex=True),
            PlaybookTask(step_id="sdd-greenfield-at-001-1-2", name="AT-001-1-2",
                         prompt="x", weak_regex=False),
            PlaybookTask(step_id="T99", name="non-sdd", prompt="x", weak_regex=True),
        ]

    def test_compile_report_collects_weak_regex_at_ids(self):
        ad = PlaybookToRtmAdapter()
        # 全通過：weak 與 pass/fail 正交——即使通過，weak AT 仍入 weak_regex_at_ids
        completed = ["sdd-greenfield-at-001-1-1", "sdd-greenfield-at-001-1-2"]
        rep = ad.compile_report(self._tasks_with_weak(), completed)
        assert rep.weak_regex_at_ids == ("AT-001-1-1",)  # 非 SDD task 不計入
        assert rep.failed_at_ids == ()  # 正交：全通過

    def test_no_weak_defaults_empty(self):
        ad = PlaybookToRtmAdapter()
        tasks = [PlaybookTask(step_id="sdd-greenfield-at-001-1-1", name="AT-001-1-1",
                              prompt="x")]
        rep = ad.compile_report(tasks, [])
        assert rep.weak_regex_at_ids == ()

    def test_render_yaml_includes_weak_regex_at_ids(self):
        ad = PlaybookToRtmAdapter()
        rep = ad.compile_report(self._tasks_with_weak(), [])
        doc = yaml.safe_load(ad.render_yaml(rep))
        assert doc["weak_regex_at_ids"] == ["AT-001-1-1"]
