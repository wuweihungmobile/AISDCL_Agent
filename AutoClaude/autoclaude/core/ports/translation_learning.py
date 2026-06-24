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
    failing_runs: int     # 跨 session 失敗 run 計數（元學習信號強度）
    total_runs: int       # 觀察窗口內總 run 數
    rationale: str        # 人類可讀提議理由（XAI：為何建議檢視此 AT 轉譯）
    status: str = "proposed"   # 恆 "proposed"；絕不由機制自動改 verified/applied


@runtime_checkable
class ITranslationLearningSink(Protocol):
    """轉譯策略提議落地抽象（File-only，沿用 rtm_sink 先例，無 PG 後端）。"""

    def record_proposal(self, project: str, proposal: TranslationProposal) -> None:
        """append 一筆 proposed 提議（冪等不保證，dedup 由呼叫端經 list_proposals 處理）。"""

    def list_proposals(self, project: str) -> tuple[TranslationProposal, ...]:
        """讀回 project 既有提議（供 dedup / 人工 review）；fail-soft 回 ()。"""


def select_proposals(
    history: tuple[RtmCoverageReport, ...],
    already_proposed_at_ids: frozenset[str],
    *,
    min_failing_runs: int = 2,
    max_new: int = 3,
) -> tuple[TranslationProposal, ...]:
    """純元學習：統計各 at_id 跨 run 失敗頻次，達門檻且未提議過者 → 提議（有界 max_new）。

    L5 守界（§4.5）：
      - 元學習信號＝跨 session 失敗**頻次**（同一 at_id 在多個 run 的 failed_at_ids 出現）。
      - min_failing_runs 門檻：偶發單次失敗（可能是實作錯非轉譯錯）不提議，降噪。
      - max_new 硬上限：每次提議數有界（不重試、超限截斷），杜絕提議洪泛。
      - dedup：已提議過的 at_id 不重複提議（跨 session 收斂）。
      - 確定性：依 (失敗頻次 desc, at_id asc) 穩定排序，取前 max_new（可審、可重現）。

    Args:
        history: 既有 IRtmFeedbackSource.read_history(project)（最舊→最新）。
        already_proposed_at_ids: sink.list_proposals 既有提議的 at_id 集（dedup）。
        min_failing_runs: 達此跨 run 失敗次數才提議（預設 2）。
        max_new: 本次最多新提議數（預設 3，有界硬閘）。
    """
    total_runs = len(history)
    if total_runs == 0 or max_new <= 0:
        return ()
    # 統計各 at_id 在多少個 run 的 failed_at_ids 中出現（跨 session 失敗頻次）
    fail_counter: Counter[str] = Counter()
    for report in history:
        for at_id in set(report.failed_at_ids):  # 同一 run 內去重，計「失敗 run 數」
            fail_counter[at_id] += 1

    candidates = [
        (at_id, runs)
        for at_id, runs in fail_counter.items()
        if runs >= min_failing_runs and at_id not in already_proposed_at_ids
    ]
    # 確定性排序：失敗頻次高者優先；同頻次以 at_id 字典序（穩定、可重現）
    candidates.sort(key=lambda x: (-x[1], x[0]))

    proposals: list[TranslationProposal] = []
    for at_id, runs in candidates[:max_new]:
        proposals.append(TranslationProposal(
            at_id=at_id,
            failing_runs=runs,
            total_runs=total_runs,
            rationale=(
                f"契約 {at_id} 於觀察窗口 {total_runs} 個 run 中有 {runs} 個 run 執行未通過"
                f"（達門檻 {min_failing_runs}）；建議人工檢視其 Gherkin→regex 轉譯保真度／"
                f"契約可測性，必要時手動精修 SddToPlaybookAdapter 轉譯規則（不自動套用）。"
            ),
        ))
    return tuple(proposals)


__all__ = ["TranslationProposal", "ITranslationLearningSink", "select_proposals"]
