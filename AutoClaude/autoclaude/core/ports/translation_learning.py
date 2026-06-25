"""ITranslationLearningSink — A 軌轉譯策略元學習 Port（AutoSDD_improving_60，data tier ≤150）。

A 軸協作自治 L4→L5：在既有 IRtmFeedbackSource（improving_27 回流讀回邊）之上，補建
「轉譯失敗跨 session 元學習 → 自動提議改進候選」迴圈，達 Rubric L5「有界自演化、人在環上」。

與 rtm_feedback.py 同模式（純 Protocol + dataclass + 模組級純函數，零 IO、零外部依賴）：
  讀回（improving_27）：RTM-COVERAGE-HISTORY-*.jsonl --IRtmFeedbackSource--> RtmCoverageReport
  元學習（improving_60）：history --select_proposals()--> TranslationProposal（proposed）
                         --ITranslationLearningSink.record_proposal--> PROPOSALS-{project}.jsonl

🔴 紅線（沿用 rtm_sink/rtm_feedback「RTM/SPEC-PATCH 絕不自動套用」）：
  proposals 一律 status="proposed"，**僅供諮詢**——人工 review 後手動改 adapter 轉譯規則，
  絕不由本機制自動改變 SddToPlaybookAdapter 轉譯行為（apply=人工 signoff 守界）。

core 純度：本檔僅 import stdlib + 同層 rtm_sink 的 dataclass，不觸 execution/infra
（與 rtm_sink.py / rtm_feedback.py / spec_source.py 同模式），不破壞 core-purity contract。
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .rtm_sink import RtmCoverageReport


@dataclass(frozen=True)
class TranslationProposal:
    """轉譯策略改進提議（恆 proposed；apply 由人工，絕不自動升 verified）。"""

    at_id: str            # 反覆失敗的契約 AT id（轉譯改進候選錨點）
    failing_runs: int     # 跨 session 執行失敗 run 計數（信號①強度）
    total_runs: int       # 觀察窗口內總 run 數
    rationale: str        # 人類可讀提議理由（XAI：為何建議檢視此 AT 轉譯）
    status: str = "proposed"   # 恆 "proposed"；絕不由機制自動改 verified/applied
    weak_runs: int = 0    # improving_61：跨 session weak_regex run 計數（信號②強度，
    #                       轉譯保真度弱點；與 failing_runs 正交）。additive 預設 0。
    # improving_67 W-67-1：雙信號分類，供舵手 review 時一眼分流（XAI 可審批面）。
    # "both"=規格與實作雙弱（最該深查）／"execution_failure"=純執行失敗／
    # "translation_weak"=純轉譯保真度弱。additive 預設 ""；舊 jsonl 無此欄 fail-soft 讀回。
    signal_class: str = ""


@runtime_checkable
class ITranslationLearningSink(Protocol):
    """轉譯策略提議落地抽象（File-only，沿用 rtm_sink 先例，無 PG 後端）。"""

    def record_proposal(self, project: str, proposal: TranslationProposal) -> None:
        """append 一筆 proposed 提議（冪等不保證，dedup 由呼叫端經 list_proposals 處理）。"""

    def list_proposals(self, project: str) -> tuple[TranslationProposal, ...]:
        """讀回 project 既有提議（供 dedup / 人工 review）；fail-soft 回 ()。"""


def _build_rationale(at_id: str, total_runs: int, fail_runs: int, weak_runs: int,
                     min_failing_runs: int, min_weak_runs: int) -> str:
    """XAI 可審：依觸發信號（執行失敗①／weak_regex②／雙信號）產人類可讀理由。"""
    sig_fail = fail_runs >= min_failing_runs
    sig_weak = weak_runs >= min_weak_runs
    parts: list[str] = []
    if sig_fail:
        parts.append(f"執行未通過 {fail_runs} 個 run（達門檻 {min_failing_runs}）")
    if sig_weak:
        parts.append(
            f"轉譯為 weak_regex（Gherkin 無法編出強斷言）{weak_runs} 個 run"
            f"（達門檻 {min_weak_runs}）"
        )
    signals = "；又".join(parts)
    return (
        f"契約 {at_id} 於觀察窗口 {total_runs} 個 run 中{signals}；建議人工檢視其 "
        f"Gherkin→regex 轉譯保真度／契約可測性，必要時手動精修 SddToPlaybookAdapter "
        f"轉譯規則（不自動套用）。"
    )


def _classify_signal(fail_runs: int, weak_runs: int,
                     min_failing: int, min_weak: int) -> str:
    """improving_67 W-67-1：依雙信號達標情況分類（XAI 審批分流）。

    候選必至少一信號達門檻（select_proposals 過濾保證），故三類窮盡：
      - 雙達標 → "both"（規格與實作雙弱，最該深查）
      - 僅執行失敗達標 → "execution_failure"
      - 僅 weak_regex 達標 → "translation_weak"
    """
    sig_fail = fail_runs >= min_failing
    sig_weak = weak_runs >= min_weak
    if sig_fail and sig_weak:
        return "both"
    if sig_fail:
        return "execution_failure"
    return "translation_weak"


def select_proposals(
    history: tuple[RtmCoverageReport, ...],
    already_proposed_at_ids: frozenset[str],
    *,
    min_failing_runs: int = 2,
    max_new: int = 3,
    min_weak_runs: int = 2,
) -> tuple[TranslationProposal, ...]:
    """雙信號元學習（improving_61 加固）：at_id 達 (執行失敗頻次≥min_failing_runs)
    OR (weak_regex 頻次≥min_weak_runs) 且未提議過者 → 提議（有界 max_new）。

    L5 守界（§4.5）：
      - 信號①＝跨 session 執行**失敗頻次**（failed_at_ids）；信號②＝跨 session
        **weak_regex 頻次**（weak_regex_at_ids，轉譯保真度弱點，與①正交）。
      - 兩門檻獨立降噪：偶發單次失敗 / 單次弱轉譯不提議。
      - max_new 硬上限：合併雙信號候選後仍有界（不重試、超限截斷），杜絕洪泛。
      - dedup：已提議過的 at_id 不重複提議（跨 session 收斂）。
      - 確定性：依 (max(失敗頻次,weak頻次) desc, at_id asc) 穩定排序（可審、可重現）。

    Args:
        history: 既有 IRtmFeedbackSource.read_history(project)（最舊→最新）。
        already_proposed_at_ids: sink.list_proposals 既有提議的 at_id 集（dedup）。
        min_failing_runs: 信號①門檻（預設 2）。
        max_new: 本次最多新提議數（預設 3，有界硬閘）。
        min_weak_runs: 信號②門檻（預設 2）。
    """
    total_runs = len(history)
    if total_runs == 0 or max_new <= 0:
        return ()
    # 兩信號各自統計「出現於多少個 run」（同一 run 內去重 → 計 run 數）
    fail_counter: Counter[str] = Counter()
    weak_counter: Counter[str] = Counter()
    for report in history:
        for at_id in set(report.failed_at_ids):
            fail_counter[at_id] += 1
        for at_id in set(report.weak_regex_at_ids):
            weak_counter[at_id] += 1

    all_at_ids = set(fail_counter) | set(weak_counter)
    candidates = [
        (at_id, fail_counter.get(at_id, 0), weak_counter.get(at_id, 0))
        for at_id in all_at_ids
        if at_id not in already_proposed_at_ids
        and (fail_counter.get(at_id, 0) >= min_failing_runs
             or weak_counter.get(at_id, 0) >= min_weak_runs)
    ]
    # 確定性排序：較強信號（兩者取大）高者優先；同強以 at_id 字典序
    candidates.sort(key=lambda x: (-max(x[1], x[2]), x[0]))

    proposals: list[TranslationProposal] = []
    for at_id, fail_runs, weak_runs in candidates[:max_new]:
        proposals.append(TranslationProposal(
            at_id=at_id,
            failing_runs=fail_runs,
            total_runs=total_runs,
            weak_runs=weak_runs,
            rationale=_build_rationale(
                at_id, total_runs, fail_runs, weak_runs,
                min_failing_runs, min_weak_runs,
            ),
            signal_class=_classify_signal(
                fail_runs, weak_runs, min_failing_runs, min_weak_runs,
            ),
        ))
    return tuple(proposals)


__all__ = ["TranslationProposal", "ITranslationLearningSink", "select_proposals"]
