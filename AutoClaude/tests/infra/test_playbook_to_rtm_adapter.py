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

from autoclaude.core.ports.rtm_feedback import coverage_report_from_doc
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


# ── improving_115（ADR-XPLAT-016 §8.5，S6／D-115-16）：AC 歸屬改為「前兩段數字」──────────
# WHY：AT 文法放寬（首段三位、第二段數字、第三段起任意英數尾綴）後，若逆向仍只認恰好三段數字，
# 帶尾綴的 AT 會因「還原不出」被略過而從覆蓋率分母悄悄消失——覆蓋率被灌高。新規則：前兩段歸 AC；
# 不符文法的 AT 仍計入 AT 級指標、不進 AC 桶、列 unmapped、有它時不得宣稱 fully_covered。
def _ids(*pairs):
    """[(AT id, 是否完成)] → (tasks, completed)；step_id＝sdd-greenfield-<小寫 at_id>，同正向。"""
    tasks = [_task(f"sdd-greenfield-{at.lower()}", at) for at, _ in pairs]
    return tasks, [f"sdd-greenfield-{at.lower()}" for at, done in pairs if done]


class TestAcAttributionByFirstTwoSegments:
    def test_multi_segment_suffixes_belong_to_the_ac_of_their_first_two_segments(self):
        tasks, completed = _ids(
            ("AT-001-12-3-a", True), ("AT-001-12-3-b", True), ("AT-001-1-E-1", True),
            ("AT-001-1-1", False), ("AT-029-1-1-1-1", True))
        rep = PlaybookToRtmAdapter().compile_report(tasks, completed)
        assert dict((ac, (p, t)) for ac, p, t in rep.ac_coverage) == {
            "AC-001-12": (2, 2), "AC-001-1": (1, 2), "AC-029-1": (1, 1)}
        assert rep.total_at == 5 and rep.passed_at == 4
        assert rep.unmapped_at_ids == ()

    def test_reported_ids_are_upper_cased_but_attribution_is_not_affected(self):
        tasks, _ = _ids(("AT-001-1-1-a", False))
        rep = PlaybookToRtmAdapter().compile_report(tasks, [])
        assert rep.failed_at_ids == ("AT-001-1-1-A",)
        assert rep.ac_coverage == (("AC-001-1", 0, 1),)

    def test_non_grammar_ats_stay_in_at_level_metrics_but_in_no_ac_bucket(self):
        """AT 級指標不假裝它不存在（total_at／passed_at／failed_at_ids），AC 級指標不被它污染。"""
        tasks, completed = _ids(
            ("AT-001-1-1", True), ("AT-14-1-1", True), ("AT-001-E-2", False))
        rep = PlaybookToRtmAdapter().compile_report(tasks, completed)
        assert rep.total_at == 3 and rep.passed_at == 2
        assert rep.failed_at_ids == ("AT-001-E-2",)
        assert rep.ac_coverage == (("AC-001-1", 1, 1),)
        assert rep.unmapped_at_ids == ("AT-001-E-2", "AT-14-1-1")  # 排序

    def test_fully_covered_is_false_while_any_at_is_unmapped(self):
        """舊的三段形（對照組）全覆蓋為真；多一個無法歸屬的 AT，就算它通過、AC 也全覆蓋，仍為假。"""
        ad = PlaybookToRtmAdapter()
        tasks, completed = _ids(("AT-001-1-1", True), ("AT-001-2-1", True))
        assert ad.compile_report(tasks, completed).is_fully_covered is True
        tasks, completed = _ids(("AT-001-1-1", True), ("AT-001-2-1", True), ("AT-14-1-1", True))
        rep = ad.compile_report(tasks, completed)
        assert rep.ac_covered == rep.ac_total == 2 and rep.passed_at == rep.total_at == 3
        assert rep.is_fully_covered is False

    def test_the_legacy_three_segment_shape_is_attributed_exactly_as_before(self):
        rep = PlaybookToRtmAdapter().compile_report(
            _sdd_tasks(), ["sdd-greenfield-at-001-1-1", "sdd-greenfield-at-001-2-1"])
        assert (rep.total_at, rep.passed_at, rep.failed_at_ids) == (3, 2, ("AT-001-1-2",))
        assert rep.ac_coverage == (("AC-001-1", 1, 2), ("AC-001-2", 1, 1))
        assert rep.unmapped_at_ids == () and rep.weak_regex_at_ids == ()

    def test_a_name_that_is_not_an_at_falls_back_to_the_step_id_and_may_be_unmapped(self):
        events = []

        class _Obs:
            def emit_counter(self, *a, **k): pass
            def emit_histogram(self, *a, **k): pass
            def start_span(self, *a, **k): raise AssertionError("unused")
            def record_event(self, name, attributes=None):
                events.append(name)

        ad = PlaybookToRtmAdapter(observability=_Obs())
        rep = ad.compile_report(
            [_task("sdd-greenfield-at-001-e-1", name="登入頁"),   # 名稱被改過，step_id 還在
             _task("sdd-greenfield-at-001-1-1", name="登入頁")], ["sdd-greenfield-at-001-1-1"])
        assert rep.total_at == 2 and rep.unmapped_at_ids == ("AT-001-E-1",)
        assert rep.ac_coverage == (("AC-001-1", 1, 1),)
        assert events == []  # 有 `-at-` 界線的任務不算「還原不出」

    def test_render_yaml_carries_the_unmapped_fields_and_survives_the_round_trip(self):
        ad = PlaybookToRtmAdapter()
        tasks, completed = _ids(("AT-001-1-1", True), ("AT-14-1-1", False), ("AT-001-E-2", True))
        rep = ad.compile_report(tasks, completed, spec_digest="sha256:abc")
        doc = yaml.safe_load(ad.render_yaml(rep))
        assert doc["summary"]["unmapped_at"] == 2 and doc["summary"]["fully_covered"] is False
        assert doc["unmapped_at_ids"] == ["AT-001-E-2", "AT-14-1-1"]
        assert coverage_report_from_doc(doc) == rep  # 含新欄的全欄位等值

    def test_the_yaml_of_a_clean_report_says_zero_unmapped(self):
        ad = PlaybookToRtmAdapter()
        doc = yaml.safe_load(ad.render_yaml(ad.compile_report(_sdd_tasks(), [])))
        assert doc["summary"]["unmapped_at"] == 0 and doc["unmapped_at_ids"] == []

    def test_gap_markdown_names_the_unmapped_ats_and_never_claims_a_clean_pass(self):
        ad = PlaybookToRtmAdapter()
        tasks, completed = _ids(("AT-001-1-1", True), ("AT-14-1-1", True))
        md = ad.render_gap_markdown(ad.compile_report(tasks, completed))
        assert "無法歸屬 AC 的 AT 清單" in md and "- AT-14-1-1" in md
        assert "無 gap" not in md and "✅" not in md
        assert "不得宣稱全覆蓋" in md  # AC 都覆蓋了卻仍不是 100%：原因必須說出來


class TestRtmCoverageReportUnmappedField:
    def test_unmapped_defaults_empty_and_leaves_the_gate_untouched(self):
        rep = RtmCoverageReport(scenario="s", spec_digest="d", total_at=1, passed_at=1,
                                ac_coverage=(("AC-001-1", 1, 1),))
        assert rep.unmapped_at_ids == () and rep.is_fully_covered is True

    def test_unmapped_ids_veto_the_fully_covered_verdict(self):
        rep = RtmCoverageReport(scenario="s", spec_digest="d", total_at=2, passed_at=2,
                                ac_coverage=(("AC-001-1", 1, 1),), unmapped_at_ids=("AT-14-1-1",))
        assert rep.ac_covered == rep.ac_total and rep.is_fully_covered is False
