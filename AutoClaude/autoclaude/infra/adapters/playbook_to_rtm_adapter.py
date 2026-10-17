"""PlaybookToRtmAdapter — 逆向橋接：Playbook 執行結果 → RTM 覆蓋度報告。

對應 AutoSDD_improving_24.md A 軌（W-24-1）。與 SddToPlaybookAdapter
（infra/adapters/sdd_to_playbook_adapter.py）對稱：

  正向：SddSpec --compile_tasks--> list[PlaybookTask]   （step_id=sdd-{scenario}-{at_id})
  逆向：(tasks, completed_step_ids) --compile_report--> RtmCoverageReport

核心職責（純函式、無 IO）：
  1. 自 playbook.tasks 篩出 SDD 編譯任務（step_id 前綴 "sdd-"）
  2. 還原每個 task 對應的 AT id（優先用 task.name，fallback 反解 step_id）
  3. 以 completed_step_ids 判定 AT pass/fail，聚合為 AC 覆蓋度
  4. 序列化為機器可讀 YAML（coverage）+ 人類可讀 gap Markdown（諮詢用）

AC 歸屬（improving_115／ADR-XPLAT-016 §8.5，D-115-16）：AT id 文法與「前兩段數字＝所屬 AC」
共用 core/ports/spec_source 的 AT_ID_PATTERN／ac_id_of_at（正向與逆向同一份判準）。
還原得到 `AT-` 開頭卻不合文法的 id（舊規格的 `AT-14-1-1`、E 類 `AT-001-E-1`）：**仍計入**
total_at 並依完成與否計入 passed_at／failed_at_ids（AT 級指標不假裝它不存在），但不進任何 AC 桶
（AC 級指標不被它污染），並列入 unmapped_at_ids；有 unmapped 時不得宣稱 fully_covered。
——否則放寬文法後帶尾綴的 AT 會從覆蓋率分母悄悄消失，把覆蓋率灌高。

安全/誠實紀律：
  - 不自動覆寫人工 RTM-{System}.md（SCG-5 人工所有）；只產諮詢報告
  - completed_step_ids 去重（GOTO 回跳會重複），防覆蓋率 >100%
"""
from __future__ import annotations

import re
from collections.abc import Iterable

import yaml

from ...core.ports.observability import IObservabilityPort, NullObservability
from ...core.ports.rtm_sink import RtmCoverageReport
from ...core.ports.spec_source import AT_ID_PATTERN, ac_id_of_at
from ...models.playbook import PlaybookTask

_SDD_STEP_PREFIX = "sdd-"
_AT_ID_RE = re.compile(AT_ID_PATTERN)


class PlaybookToRtmAdapter:
    """逆向：PlaybookTask 序列 × 執行結果 → RtmCoverageReport（純函式 + 序列化）。"""

    def __init__(self, observability: IObservabilityPort | None = None) -> None:
        self._obs = observability or NullObservability()

    # ──────────────────────────────────────────────────────────
    # compile：執行結果 → RtmCoverageReport（純函式、無 IO）
    # ──────────────────────────────────────────────────────────
    def compile_report(
        self,
        tasks: Iterable[PlaybookTask],
        completed_step_ids: Iterable[str],
        *,
        spec_digest: str = "",
    ) -> RtmCoverageReport:
        """還原 SDD 任務的 AC/AT 覆蓋度。非 SDD task 一律忽略。

        Args:
            tasks: playbook.tasks（含或不含 SDD 任務皆可）
            completed_step_ids: 本次 run 成功完成的 step_id（POST_RUN payload）
            spec_digest: 對應 SddSpec.digest（drift 指紋；可選）
        """
        completed = set(completed_step_ids or [])
        scenario = ""
        # at_id -> passed(bool)；保序（首見順序）以利確定性輸出
        at_status: dict[str, bool] = {}
        # improving_61 W-61-1：轉譯為 weak_regex 的 AT id（第二元學習信號）。任一搭載
        # task 標記 weak 即視該 AT 弱（OR；同 at_id 多 task 保守取真）。
        weak_at_ids: set[str] = set()
        # ADR §8.5：還原得到 `AT-` 開頭卻不合文法者（仍計入 total_at，但無法歸屬任何 AC）
        unmapped_at_ids: set[str] = set()
        for task in tasks:
            step_id = getattr(task, "step_id", "") or ""
            if not step_id.startswith(_SDD_STEP_PREFIX):
                continue
            if not scenario:
                scenario = self._scenario_of(step_id)
            at_id = self._at_id_of(task, step_id)
            if at_id is None:
                self._obs.record_event(
                    "rtm_writeback_unresolved_step",
                    {"step_id": step_id},
                )
                continue
            # 同一 AT 多次出現（理論上不應發生）採 OR：任一通過即視為通過
            at_status[at_id] = at_status.get(at_id, False) or (step_id in completed)
            if ac_id_of_at(at_id) is None:  # 不合 AT_ID_PATTERN：計入 AT 級、不進 AC 桶（§8.5）
                unmapped_at_ids.add(at_id)
            if getattr(task, "weak_regex", False):
                weak_at_ids.add(at_id)

        total_at = len(at_status)
        passed_at = sum(1 for ok in at_status.values() if ok)
        failed_at_ids = tuple(sorted(at for at, ok in at_status.items() if not ok))
        ac_coverage = self._aggregate_ac(at_status)
        return RtmCoverageReport(
            scenario=scenario,
            spec_digest=spec_digest,
            total_at=total_at,
            passed_at=passed_at,
            failed_at_ids=failed_at_ids,
            ac_coverage=ac_coverage,
            weak_regex_at_ids=tuple(sorted(weak_at_ids)),
            unmapped_at_ids=tuple(sorted(unmapped_at_ids)),
        )

    # ──────────────────────────────────────────────────────────
    # render：RtmCoverageReport → 序列化文字
    # ──────────────────────────────────────────────────────────
    def render_yaml(
        self, report: RtmCoverageReport, *, generated_at: str | None = None
    ) -> str:
        """機器可讀 coverage 報告（YAML）。供 CI / SCG-5 自動化消費。"""
        doc: dict[str, object] = {
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
                "unmapped_at": len(report.unmapped_at_ids),  # improving_115 §8.5
            },
            "ac_coverage": [
                {"ac_id": ac, "passed_at": passed, "total_at": total}
                for ac, passed, total in report.ac_coverage
            ],
            "failed_at_ids": list(report.failed_at_ids),
            "weak_regex_at_ids": list(report.weak_regex_at_ids),  # improving_61 W-61-1
            "unmapped_at_ids": list(report.unmapped_at_ids),  # improving_115 §8.5
        }
        if generated_at:
            doc["generated_at"] = generated_at
        return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)

    def render_gap_markdown(self, report: RtmCoverageReport) -> str:
        """人類可讀 gap 報告（Markdown），格式對齊 rtm-generate 的未覆蓋 AC 清單。"""
        if report.is_fully_covered:
            gate = "✅ 通過（100% AC 覆蓋）"
        elif report.ac_total > 0 and report.ac_covered == report.ac_total:
            # AC 都覆蓋了、is_fully_covered 卻為假：唯一原因是有無法歸屬 AC 的 AT（§8.5）
            gate = "❌ 有無法歸屬 AC 的 AT，不得宣稱全覆蓋"
        else:
            gate = "❌ 未達 100% AC 覆蓋"
        lines = [
            f"# RTM Gap Analysis — {report.scenario or '(unknown)'}",
            "",
            f"- AT 覆蓋率：{report.passed_at}/{report.total_at}（{report.coverage_pct}%）",
            f"- AC 覆蓋率：{report.ac_covered}/{report.ac_total}（{report.ac_coverage_pct}%）",
            f"- SCG-5 RTM 閘門：{gate}",
            "",
        ]
        uncovered_acs = [
            (ac, passed, total)
            for ac, passed, total in report.ac_coverage
            if not (total > 0 and passed == total)
        ]
        if uncovered_acs:
            lines.append("## 未完全覆蓋 AC 清單（需補測試 / 修復實作）")
            for ac, passed, total in uncovered_acs:
                lines.append(f"- {ac}: {passed}/{total} AT 通過")
            lines.append("")
        if report.failed_at_ids:
            lines.append("## 未通過 AT 清單")
            for at in report.failed_at_ids:
                lines.append(f"- {at}")
            lines.append("")
        if report.unmapped_at_ids:
            lines.append("## 無法歸屬 AC 的 AT 清單（AT ID 不合 AT_ID_PATTERN，前兩段＝所屬 AC）")
            for at in report.unmapped_at_ids:
                lines.append(f"- {at}")
            lines.append("")
        if (not uncovered_acs and not report.failed_at_ids and not report.unmapped_at_ids
                and report.total_at > 0):
            lines.append("> 全部 AC/AT 已覆蓋，無 gap。")
            lines.append("")
        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────
    # 內部：step_id / at_id 反解
    # ──────────────────────────────────────────────────────────
    @staticmethod
    def _scenario_of(step_id: str) -> str:
        """sdd-{scenario}-at-... → scenario。以 "-at-" 為界（at_id 必以 AT- 開頭）。"""
        body = step_id[len(_SDD_STEP_PREFIX):]
        marker = body.lower().find("-at-")
        if marker < 0:
            return ""
        return body[:marker]

    @staticmethod
    def _at_id_of(task: PlaybookTask, step_id: str) -> str | None:
        """優先用 task.name（forward adapter 設為 c.at_id，須合文法）；否則反解 step_id。

        反解得到的字串以 `AT-` 開頭卻不合文法者照樣回傳（由呼叫端標 unmapped 並計入 total_at，
        §8.5）；完全沒有 `-at-` 界線的 `sdd-` 任務回 None（呼叫端略過並出聲）。
        回傳一律大寫（既有行為）：尾綴含小寫字母的 ID 可編譯，回報時被大寫化，AC 歸屬不受影響。
        """
        name = (getattr(task, "name", "") or "").strip().upper()
        if _AT_ID_RE.fullmatch(name):
            return name
        # fallback：自 step_id 反解（sdd-{scenario}-{at_id.lower()}）
        body = step_id[len(_SDD_STEP_PREFIX):]
        marker = body.lower().find("-at-")
        if marker < 0:
            return None
        return body[marker + 1:].upper()  # 去掉界線 "-"，保留 AT-...

    @staticmethod
    def _aggregate_ac(at_status: dict[str, bool]) -> tuple[tuple[str, int, int], ...]:
        """AT 級狀態聚合為 AC 級。AT-{NNN}-{Y}-… → AC-{NNN}-{Y}（前兩段歸屬，尾綴不影響）。
        不合文法（無法歸屬）的 AT 不進任何 AC 桶。"""
        buckets: dict[str, list[int]] = {}  # ac_id -> [passed, total]
        for at_id, ok in at_status.items():
            ac_id = ac_id_of_at(at_id)
            if ac_id is None:
                continue
            slot = buckets.setdefault(ac_id, [0, 0])
            slot[1] += 1
            if ok:
                slot[0] += 1
        return tuple(
            (ac_id, passed, total)
            for ac_id, (passed, total) in sorted(buckets.items())
        )


__all__ = ["PlaybookToRtmAdapter"]
