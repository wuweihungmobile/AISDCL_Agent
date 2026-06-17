"""IRtmSink + RtmCoverageReport — A 軌逆向回寫契約（data tier ≤150 LOC）。

對應 AutoSDD_improving_24.md A 軌（W-24-1）：Playbook 執行結果 → SDD RTM
coverage/gap 報告的逆向橋接。與 ISpecSource（core/ports/spec_source.py）對稱：
正向 SDD→Playbook 由 ISpecSource 編譯 PlaybookTask；逆向 Playbook→SDD 由本
契約把執行結果還原為 AC/AT 覆蓋度報告。

設計原則（仿 IObservabilityPort，contract/data tier）：
  - 純 Protocol + frozen dataclass，零實作、零外部依賴
  - core 僅依賴本介面；檔案寫出實作封裝於 infra adapter（FileRtmSink）
  - 不自動覆寫人工 RTM-{System}.md（SCG-5 人工所有）；本契約只產**諮詢用**
    coverage/gap 報告，對齊「RTM/SPEC-PATCH 絕不自動套用」紅線

core 純度：本檔僅 import stdlib（dataclasses / typing），不觸 execution/infra，
故不破壞 core-purity contract（與 spec_source.py 同模式）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol


@dataclass(frozen=True)
class RtmCoverageReport:
    """Playbook 執行結果還原的 AC/AT 覆蓋度快照（純資料、可序列化）。

    覆蓋語意（對齊 SCG-5 RTM 100% AC 覆蓋）：
      - AT 級：passed_at / total_at（單一驗收測試是否通過）
      - AC 級：一個 AC 之全部 AT 皆 passed 才算「已覆蓋」（保守判定）

    欄位以 tuple 表示集合（frozen 友善 + 確定性排序，杜絕 dict 順序漂移）。
    """

    scenario: str
    spec_digest: str  # 對應 SddSpec.digest（drift 防護指紋）
    total_at: int
    passed_at: int
    failed_at_ids: tuple[str, ...] = field(default=())  # 未通過（含未達 / 失敗）的 AT id
    # (ac_id, passed_count, total_count)；依 ac_id 排序確定性輸出
    ac_coverage: tuple[tuple[str, int, int], ...] = field(default=())

    @property
    def coverage_pct(self) -> float:
        """AT 級覆蓋率（passed / total × 100）。total=0 時回 0.0（空 SDD playbook）。"""
        if self.total_at <= 0:
            return 0.0
        return round(100.0 * self.passed_at / self.total_at, 2)

    @property
    def ac_total(self) -> int:
        return len(self.ac_coverage)

    @property
    def ac_covered(self) -> int:
        """全部 AT 通過的 AC 數（保守判定：partial 不計入覆蓋）。"""
        return sum(1 for _ac, passed, total in self.ac_coverage if total > 0 and passed == total)

    @property
    def ac_coverage_pct(self) -> float:
        """AC 級覆蓋率（已覆蓋 AC / 總 AC × 100）。對接 SCG-5 100% 判準。"""
        if self.ac_total <= 0:
            return 0.0
        return round(100.0 * self.ac_covered / self.ac_total, 2)

    @property
    def is_fully_covered(self) -> bool:
        """SCG-5 RTM 閘門判準：全部 AC 皆已覆蓋（且非空）。"""
        return self.ac_total > 0 and self.ac_covered == self.ac_total


class IRtmSink(Protocol):
    """RTM coverage/gap 報告寫出契約。

    實作（W-24-1c）：autoclaude.infra.adapters.rtm_file_sink.FileRtmSink

    使用模式（plugin / service，建構式注入）：
        def __init__(self, sink: Optional[IRtmSink] = None):
            self._sink = sink or NullRtmSink()  # 未注入時 no-op
    """

    def write_report(self, report_name: str, content: str, *, fmt: str = "yaml") -> str:
        """寫出一份 RTM 報告，回傳寫入檔案的絕對路徑（no-op 實作回空字串）。

        Args:
            report_name: 報告基名（如 "RTM-COVERAGE-MyProject"），不含副檔名
            content: 已序列化的報告內容（YAML / Markdown 文字）
            fmt: 副檔名決定（"yaml" | "md"）
        """
        ...

    def append_report_line(self, report_name: str, line: str) -> str:
        """append 單行至 {report_name}.jsonl（improving_27 W3 跨輪趨勢持久化）。

        覆寫語意（write_report）保留「最新快照」；append 語意累積「跨輪趨勢」，
        供 IRtmFeedbackSource.read_history 讀回。回傳檔案絕對路徑（no-op 回空字串）。
        """
        ...


class NullRtmSink:
    """No-op IRtmSink 實作；未注入 sink 時 fallback（符合 Protocol，duck typing）。"""

    def write_report(self, report_name: str, content: str, *, fmt: str = "yaml") -> str:
        return ""

    def append_report_line(self, report_name: str, line: str) -> str:
        return ""


__all__ = ["RtmCoverageReport", "IRtmSink", "NullRtmSink"]
