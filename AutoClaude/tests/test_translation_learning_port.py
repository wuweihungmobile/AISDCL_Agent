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


# ── improving_61 W-61-2：雙信號元學習（weak_regex 第二信號）─────────────────

def _wreport(failed: tuple[str, ...] = (), weak: tuple[str, ...] = ()) -> RtmCoverageReport:
    return RtmCoverageReport(
        scenario="brownfield", spec_digest="sha256:x",
        total_at=5, passed_at=5 - len(failed), failed_at_ids=failed,
        weak_regex_at_ids=weak,
    )


def test_weak_only_signal_proposes():
    """R-61-4：純 weak_regex 跨 2 run（全通過、零失敗）→ 仍達信號②門檻 → 提議。"""
    history = (_wreport(weak=("AT-009",)), _wreport(weak=("AT-009",)))
    out = select_proposals(history, frozenset())
    assert len(out) == 1
    assert out[0].at_id == "AT-009"
    assert out[0].failing_runs == 0   # 正交：零執行失敗
    assert out[0].weak_runs == 2
    assert "weak_regex" in out[0].rationale


def test_weak_below_threshold_no_propose():
    """R-61-6：weak 僅 1 run < min_weak_runs（預設 2）且無失敗 → 不提議（降噪）。"""
    history = (_wreport(weak=("AT-009",)),)
    assert select_proposals(history, frozenset()) == ()


def test_fail_only_still_proposes():
    """R-61-5：純執行失敗信號（零 weak）仍提議（向後相容 improving_60 行為）。"""
    history = (_wreport(failed=("AT-001",)), _wreport(failed=("AT-001",)))
    out = select_proposals(history, frozenset())
    assert len(out) == 1 and out[0].at_id == "AT-001"
    assert out[0].weak_runs == 0
    assert "執行未通過" in out[0].rationale and "weak_regex" not in out[0].rationale


def test_dual_signal_rationale_distinguishes():
    """R-61-5：同 at_id 兩信號齊發 → rationale 同時陳述兩信號與計數。"""
    history = (_wreport(failed=("AT-007",), weak=("AT-007",)),
               _wreport(failed=("AT-007",), weak=("AT-007",)))
    out = select_proposals(history, frozenset())
    assert len(out) == 1
    p = out[0]
    assert p.failing_runs == 2 and p.weak_runs == 2
    assert "執行未通過" in p.rationale and "weak_regex" in p.rationale


def test_dual_signal_bounded_and_deterministic():
    """R-61-7：合併雙信號候選後仍受 max_new 截斷；確定性排序（較強信號優先）。

    QA 突變鎖：4 個達門檻候選（混失敗/weak），max_new=2 → 恰 2 筆，且取信號最強的
    前 2（AT-D weak=3 最強、AT-A fail=2）。若排序鍵或 max 邏輯被改 → 此斷言轉紅。
    """
    history = (
        _wreport(failed=("AT-A", "AT-B"), weak=("AT-C", "AT-D")),
        _wreport(failed=("AT-A", "AT-B"), weak=("AT-C", "AT-D")),
        _wreport(weak=("AT-D",)),  # AT-D weak=3（最強信號）
    )
    out = select_proposals(history, frozenset(), max_new=2)
    assert len(out) == 2  # 有界
    assert out[0].at_id == "AT-D" and out[0].weak_runs == 3  # 最強信號排首
    assert {p.at_id for p in out} == {"AT-D", "AT-A"}  # 取信號最強前 2


def test_dual_signal_dedup_skips_already_proposed():
    """R-61-7：已提議過的 at_id（不論信號）不重複提議（跨 session 收斂）。"""
    history = (_wreport(weak=("AT-009",)), _wreport(weak=("AT-009",)))
    assert select_proposals(history, frozenset({"AT-009"})) == ()


def test_proposals_always_proposed_status_dual_signal():
    """R-61-4/紅線：weak 信號提議仍恆 status='proposed'（apply 由人工）。"""
    history = (_wreport(weak=("AT-009",)), _wreport(weak=("AT-009",)))
    out = select_proposals(history, frozenset())
    assert all(p.status == "proposed" for p in out)


# ── improving_67 W-67-1：提議信號分類（XAI 可審批分流）─────────────────────
# Rule 9：signal_class 編碼「為何分類」——舵手 review PROPOSALS 時需一眼分辨缺陷源頭
# （規格弱 vs 實作弱 vs 雙弱），分類錯誤會誤導人工 review 方向。三類窮盡且互斥。

def test_signal_class_execution_failure_only():
    """R-67-1：純執行失敗達門檻（零 weak）→ signal_class='execution_failure'。"""
    history = (_wreport(failed=("AT-001",)), _wreport(failed=("AT-001",)))
    out = select_proposals(history, frozenset())
    assert out[0].signal_class == "execution_failure"


def test_signal_class_translation_weak_only():
    """R-67-1：純 weak_regex 達門檻（零失敗）→ signal_class='translation_weak'。"""
    history = (_wreport(weak=("AT-009",)), _wreport(weak=("AT-009",)))
    out = select_proposals(history, frozenset())
    assert out[0].signal_class == "translation_weak"


def test_signal_class_both_is_deepest_concern():
    """R-67-1：雙信號齊達門檻 → signal_class='both'（規格與實作雙弱，最該深查）。"""
    history = (_wreport(failed=("AT-007",), weak=("AT-007",)),
               _wreport(failed=("AT-007",), weak=("AT-007",)))
    out = select_proposals(history, frozenset())
    assert out[0].signal_class == "both"
    # 與既有雙信號 rationale 正交並存（分類欄不取代理由）
    assert "執行未通過" in out[0].rationale and "weak_regex" in out[0].rationale


def test_signal_class_default_empty_backward_compat():
    """R-67-2：直接構造（如舊 jsonl 讀回無此欄）→ signal_class 預設 ''（fail-soft 向後相容）。"""
    p = TranslationProposal(at_id="AT-001", failing_runs=2, total_runs=2, rationale="x")
    assert p.signal_class == ""


def test_proposals_fully_deterministic_across_calls():
    """R-67-3（折入 Explore W-67-4）：同輸入往復呼叫 select_proposals → 逐欄完全一致
    （含 signal_class）。meta-learning dedup/收斂依賴此確定性，非確定會使提議跨 run 漂移。"""
    history = (
        _wreport(failed=("AT-A", "AT-B"), weak=("AT-C", "AT-D")),
        _wreport(failed=("AT-A", "AT-B"), weak=("AT-C", "AT-D")),
        _wreport(weak=("AT-D",)),
    )
    first = select_proposals(history, frozenset(), max_new=3)
    second = select_proposals(history, frozenset(), max_new=3)
    assert first == second  # frozen dataclass 逐欄相等
    assert [p.signal_class for p in first] == [p.signal_class for p in second]
