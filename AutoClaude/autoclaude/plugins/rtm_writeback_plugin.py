"""RtmWritebackPlugin — A 軌逆向回寫閉環（AutoSDD_improving_24 W-24-2）。

訂閱 phase：
  - POST_RUN → 自 ctx.playbook.tasks 篩出 SDD 編譯任務（step_id 前綴 "sdd-"），
    以 payload.completed_step_ids 判定 AC/AT 覆蓋度，產出 coverage(YAML) +
    gap(Markdown) 報告經注入的 IRtmSink 寫出。

語意註記（對齊 GoalProgressPlugin 慣例）：
  - POST_RUN 僅於 run 正常走完時發布（halt / escalate 提前 return 不發），
    故報告反映「完成的 run」之覆蓋度快照。
  - **非 SDD playbook 全程 no-op**：無 sdd-* task → 直接 return（零退化）。
  - adapter / sink 由 wiring 注入（plugin 不直接 import infra）；任一為 None 即 no-op。
  - 寫出失敗以 warning 吞掉，絕不阻斷主流程（回寫為輔助功能）。
  - 不自動覆寫人工 RTM-{System}.md；只產諮詢用報告（SCG-5 人工所有）。
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from ..core.hookspec import HookContext, KernelPhase
from ..core.ports.rtm_feedback import coverage_report_to_doc

logger = logging.getLogger("autoclaude.plugins.rtm_writeback")

_SDD_STEP_PREFIX = "sdd-"
_DIGEST_RE = re.compile(r"digest\s+([0-9a-f]{6,64})")


class RtmWritebackPlugin:
    """A 軌逆向回寫 Plugin（SDD→Playbook 的反向：Playbook→RTM coverage 報告）。"""

    PRIORITY = 52  # goal_progress(50) 之後、convergence(65) 之前

    def __init__(self, adapter: Any | None = None, sink: Any | None = None):
        self._adapter = adapter
        self._sink = sink

    def name(self) -> str:
        return "rtm_writeback"

    def priority(self) -> int:
        return self.PRIORITY

    def subscribed_phases(self) -> list[KernelPhase]:
        return [KernelPhase.POST_RUN]

    def on_event(self, ctx: HookContext) -> Any | None:
        if ctx.phase != KernelPhase.POST_RUN:
            return None
        if self._adapter is None or self._sink is None:
            return None
        tasks = list(getattr(ctx.playbook, "tasks", []) or [])
        sdd_tasks = [t for t in tasks if (getattr(t, "step_id", "") or "").startswith(_SDD_STEP_PREFIX)]
        if not sdd_tasks:
            return None  # 非 SDD playbook → no-op（零退化）
        payload = ctx.payload or {}
        completed = payload.get("completed_step_ids") or []
        digest = self._extract_digest(sdd_tasks)
        try:
            report = self._adapter.compile_report(tasks, completed, spec_digest=digest)
            project = ctx.playbook.project
            self._sink.write_report(
                f"RTM-COVERAGE-{project}",
                self._adapter.render_yaml(report),
                fmt="yaml",
            )
            self._sink.write_report(
                f"RTM-GAP-{project}",
                self._adapter.render_gap_markdown(report),
                fmt="md",
            )
            # AutoSDD_improving_27 W3：append 本次覆蓋快照至跨輪趨勢 history（jsonl），
            # 供 IRtmFeedbackSource.read_history 讀回「上次 X% → 本次 Y%」。覆寫語意
            # （write_report）保留最新快照，append 累積趨勢；行序即時序。
            self._sink.append_report_line(
                f"RTM-COVERAGE-HISTORY-{project}",
                json.dumps(coverage_report_to_doc(report), ensure_ascii=False),
            )
        except Exception as exc:  # 回寫為輔助功能，絕不阻斷主流程
            logger.warning("RtmWritebackPlugin writeback failed: %s", exc)
        return None

    @staticmethod
    def _extract_digest(sdd_tasks: list[Any]) -> str:
        """取回 spec digest 作覆蓋報告溯源指紋。

        improving_56 W-56-2（DEF-56-001）：優先讀 PlaybookTask.spec_digest 結構化欄
        （forward adapter 填入之權威全 "sha256:..." 值），消除「prompt 正則反解 + 8 字元
        截斷」的脆弱漂移。僅當結構化欄缺漏（外部手寫 / 舊版編譯之 playbook）時，才回退
        prompt 反解維持向後相容（零退化）。
        """
        for task in sdd_tasks:
            structured = (getattr(task, "spec_digest", "") or "").strip()
            if structured:
                return structured
        for task in sdd_tasks:
            prompt = getattr(task, "prompt", "") or ""
            m = _DIGEST_RE.search(prompt)
            if m:
                return m.group(1)
        return ""


__all__ = ["RtmWritebackPlugin"]
