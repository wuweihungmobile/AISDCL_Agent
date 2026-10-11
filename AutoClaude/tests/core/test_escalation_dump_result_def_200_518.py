"""DEF-200-518：EscalationDumpedResult.dump 合併成 MergedResult.escalation_dump。

驗證意圖（Rule 9）：這條通道是「dump 物件由 CheckpointPlugin 回給發布者、
再由發布者轉交 ON_ESCALATION 下游」的唯一載具；預設 None 必須維持
（既有 EscalationDumpedResult(contributor, dump_path) 建構點不變）。
"""
from __future__ import annotations

from autoclaude.core.hookspec import EscalationDumpedResult, KernelPhase, PersistenceResult
from autoclaude.core.resolution_policy import DefaultResolutionPolicy


def _merge(results):
    return DefaultResolutionPolicy().merge(KernelPhase.ON_ESCALATION_DUMP_REQUEST, results)


def test_dump_object_is_carried_next_to_its_path():
    sentinel = object()
    merged = _merge([EscalationDumpedResult(contributor="c", dump_path="/d.md", dump=sentinel)])
    assert merged.escalation_dump_path == "/d.md" and merged.escalation_dump is sentinel


def test_default_dump_is_none_for_existing_two_argument_call_sites():
    merged = _merge([EscalationDumpedResult(contributor="c", dump_path="/d.md")])
    assert merged.escalation_dump_path == "/d.md" and merged.escalation_dump is None


def test_persistence_result_kind_escalation_dump_sets_path_only():
    merged = _merge([PersistenceResult(contributor="c", path="/p.md", succeeded=True,
                                       kind="escalation_dump")])
    assert merged.escalation_dump_path == "/p.md" and merged.escalation_dump is None


def test_first_contributor_wins_for_both_fields():
    merged = _merge([
        EscalationDumpedResult(contributor="a", dump_path="/a.md", dump="A"),
        EscalationDumpedResult(contributor="b", dump_path="/b.md", dump="B"),
    ])
    assert (merged.escalation_dump_path, merged.escalation_dump) == ("/a.md", "A")
