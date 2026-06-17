"""IRtmFeedbackSource — A 軌反饋讀回契約（AutoSDD_improving_27 W1，data tier ≤150）。

與 IRtmSink（core/ports/rtm_sink.py）對稱、互為逆向：

  寫出（improving_24）：執行結果 --PlaybookToRtmAdapter--> RtmCoverageReport
                        --IRtmSink.write_report--> RTM-COVERAGE-{project}.yaml
  讀回（improving_27）：RTM-COVERAGE-{project}.yaml / HISTORY.jsonl
                        --IRtmFeedbackSource--> RtmCoverageReport

improving_24 補上「執行結果 → 覆蓋度報告」寫出側，使閉環有出口；本契約補
「報告 → 讀回」讀回側，使「執行結果 → 覆蓋度回流 → 諮詢下一動作」的閉環邊
存在（A 軸協作自治 L3→L4：執行結果可機械回饋，非僅人工讀 log）。

紅線（沿用 rtm_sink，對齊「RTM/SPEC-PATCH 絕不自動套用」）：
  讀回僅供**諮詢**（EvolutionPlugin rationale 增補 / observability 趨勢暴露），
  絕不自動覆寫人工 RTM-{System}.md、絕不自動套用為 SPEC-PATCH。消費端
  （EvolutionPlugin）flag 預設 OFF，且演化仍走 require_evolution_signoff +
  max_evolutions 硬閘。

core 純度：本檔僅 import stdlib + 同層 rtm_sink 的 dataclass，不觸 execution/infra，
故不破壞 core-purity contract（與 rtm_sink.py / spec_source.py 同模式）。
"""
from __future__ import annotations

from typing import Any, Optional, Protocol

from .rtm_sink import RtmCoverageReport


def coverage_report_to_doc(
    report: RtmCoverageReport, *, saved_at: str = ""
) -> dict[str, Any]:
    """RtmCoverageReport → 可序列化 doc（與 PlaybookToRtmAdapter.render_yaml 同結構）。

    供 W3 history 持久化（json.dumps 單行）使用；衍生 property（coverage_pct 等）
    一併寫出供消費端免重算，但讀回時以原始欄位重建（property 仍由 dataclass 計算）。
    """
    doc: dict[str, Any] = {
        "kind": "rtm-coverage",
        "scenario": report.scenario,
        "spec_digest": report.spec_digest,
        "summary": {
            "total_at": report.total_at,
            "passed_at": report.passed_at,
            "at_coverage_pct": report.coverage_pct,
            "total_ac": report.ac_total,
            "covered_ac": report.ac_covered,
            "ac_coverage_pct": report.ac_coverage_pct,
            "fully_covered": report.is_fully_covered,
        },
        "ac_coverage": [
            {"ac_id": ac, "passed_at": passed, "total_at": total}
            for ac, passed, total in report.ac_coverage
        ],
        "failed_at_ids": list(report.failed_at_ids),
    }
    if saved_at:
        doc["saved_at"] = saved_at
    return doc


def coverage_report_from_doc(doc: dict[str, Any]) -> RtmCoverageReport:
    """render_yaml / history doc → RtmCoverageReport（read_report/read_history 共用）。

    僅重建原始欄位（衍生 property 由 dataclass 計算）；缺欄位以保守預設補齊
    （fail-soft：畸形 doc 不 raise，回最小可用 report）。
    """
    summary = doc.get("summary") or {}
    ac_coverage = tuple(
        (str(d.get("ac_id", "")), int(d.get("passed_at", 0)), int(d.get("total_at", 0)))
        for d in (doc.get("ac_coverage") or [])
    )
    return RtmCoverageReport(
        scenario=str(doc.get("scenario", "") or ""),
        spec_digest=str(doc.get("spec_digest", "") or ""),
        total_at=int(summary.get("total_at", 0)),
        passed_at=int(summary.get("passed_at", 0)),
        failed_at_ids=tuple(str(x) for x in (doc.get("failed_at_ids") or [])),
        ac_coverage=ac_coverage,
    )


class IRtmFeedbackSource(Protocol):
    """RTM coverage 報告讀回契約（IRtmSink 的逆向）。

    實作（W1b）：autoclaude.infra.adapters.rtm_file_feedback_source.FileRtmFeedbackSource

    使用模式（plugin / service，建構式注入）：
        def __init__(self, feedback: Optional[IRtmFeedbackSource] = None):
            self._feedback = feedback or NullRtmFeedbackSource()  # 未注入時 no-op
    """

    def read_report(self, project: str) -> Optional[RtmCoverageReport]:
        """讀回 project 最近一次的 coverage 報告；不存在 / 解析失敗回 None（fail-soft）。"""
        ...

    def read_history(
        self, project: str, *, limit: int = 0
    ) -> tuple[RtmCoverageReport, ...]:
        """讀回 project 的跨輪覆蓋趨勢（時間序，最舊→最新）。

        limit>0 時只回最近 limit 筆；不存在 / 解析失敗回空 tuple（fail-soft）。
        """
        ...


class NullRtmFeedbackSource:
    """No-op IRtmFeedbackSource 實作；未注入 source 時 fallback（符合 Protocol）。"""

    def read_report(self, project: str) -> Optional[RtmCoverageReport]:
        return None

    def read_history(
        self, project: str, *, limit: int = 0
    ) -> tuple[RtmCoverageReport, ...]:
        return ()


__all__ = [
    "IRtmFeedbackSource",
    "NullRtmFeedbackSource",
    "coverage_report_to_doc",
    "coverage_report_from_doc",
]
