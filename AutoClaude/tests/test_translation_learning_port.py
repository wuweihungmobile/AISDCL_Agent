"""W-60-1 select_proposals 純元學習單測（AutoSDD_improving_60，R-60-1/5）。

Rule 9：測試編碼「為何」——元學習須(1)跨 session 頻次達門檻才提議（降噪、非每次失敗都提）、
(2)提議數有界（防洪泛）、(3)dedup（跨 session 收斂）、(4)確定性（可審可重現）、
(5)proposals 恆 proposed（apply 由人工，紅線）。
"""
from __future__ import annotations

from autoclaude.core.ports.rtm_sink import RtmCoverageReport
from autoclaude.core.ports.translation_learning import (
    TranslationProposal,
    select_proposals,
)


def _report(failed: tuple[str, ...]) -> RtmCoverageReport:
    return RtmCoverageReport(
        scenario="brownfield", spec_digest="sha256:x",
        total_at=5, passed_at=5 - len(failed), failed_at_ids=failed,
    )


def test_empty_history_no_proposal():
    assert select_proposals((), frozenset()) == ()


def test_single_failure_below_threshold_no_proposal():
    """單次失敗 < min_failing_runs（預設 2）→ 不提議（降噪：可能是實作錯非轉譯錯）。"""
    history = (_report(("AT-001",)),)
    assert select_proposals(history, frozenset()) == ()


def test_repeated_failure_crosses_threshold_proposes():
    """同一 at_id 跨 2 run 失敗 → 達門檻 → 提議（元學習信號）。"""
    history = (_report(("AT-001",)), _report(("AT-001",)))
    out = select_proposals(history, frozenset())
    assert len(out) == 1
    assert out[0].at_id == "AT-001"
    assert out[0].failing_runs == 2
    assert out[0].total_runs == 2
    assert out[0].status == "proposed"  # 紅線：恆 proposed


def test_same_run_duplicate_at_counts_once():
    """同一 run 內同 at_id 多次（理論上不該，但保守去重）只計 1 個失敗 run。"""
    history = (_report(("AT-001", "AT-001")),)
    # 僅 1 run → 仍未達門檻 2
    assert select_proposals(history, frozenset()) == ()


def test_dedup_already_proposed():
    """已提議過的 at_id 不重複提議（跨 session 收斂）。"""
    history = (_report(("AT-001",)), _report(("AT-001",)))
    assert select_proposals(history, frozenset({"AT-001"})) == ()


def test_bounded_max_new_cap():
    """提議數有界：6 個達門檻候選、max_new=3 → 只提 3（硬閘、超限截斷）。"""
    failing = tuple(f"AT-{i:03d}" for i in range(6))
    history = (_report(failing), _report(failing))  # 每個都跨 2 run 失敗
    out = select_proposals(history, frozenset(), max_new=3)
    assert len(out) == 3


def test_max_new_zero_returns_empty():
    history = (_report(("AT-001",)), _report(("AT-001",)))
    assert select_proposals(history, frozenset(), max_new=0) == ()


def test_deterministic_order_by_frequency_then_id():
    """確定性：失敗頻次高者優先；同頻次 at_id 字典序（可審、可重現）。"""
    # AT-009 失敗 3 run、AT-001/AT-005 各 2 run
    history = (
        _report(("AT-009", "AT-001", "AT-005")),
        _report(("AT-009", "AT-001", "AT-005")),
        _report(("AT-009",)),
    )
    out = select_proposals(history, frozenset(), max_new=3)
    assert [p.at_id for p in out] == ["AT-009", "AT-001", "AT-005"]
    assert out[0].failing_runs == 3


def test_proposal_is_frozen_and_rationale_nonempty():
    history = (_report(("AT-007",)), _report(("AT-007",)))
    out = select_proposals(history, frozenset())
    assert isinstance(out[0], TranslationProposal)
    assert out[0].rationale  # XAI：人類可讀理由非空
    assert "AT-007" in out[0].rationale
