"""escalation_dumper.py — _save_escalation_dump 拆解收尾模組（SD_06 W2-T2-12）。

對應：
  - SD_Improving_06.md v1.2 §4 W2-5 / W2-12（escalation_dumper.py）
  - SD06_Execution_Guide.md W2 T2-12

設計原則：
  - 真正 ESCALATION dump 邏輯由 CheckpointPlugin.save_escalation_dump 承擔（SD_05 W3-1d）
  - notify_escalation 透過 callback 注入（plugin 不直接 import infra）
  - 對應 SD_06 W3 將整合 PII filter（W0 ENUM schema）
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.escalation import EscalationDump
    from ..models.playbook import PlaybookTask
    from .failure_tracker import FailureTracker
    from .playbook_runner import PlaybookRunner


def _resolve_topology_dashboard(runner: "PlaybookRunner") -> str:
    """AutoSDD_improving_14 A 軌（W-14-2）：從 runner 上可選的 SddGovernancePlugin 取已載入的
    meta⁸ 拓樸審批儀表板（kernel 路徑 PRE_RUN fail-closed 載入後寫入 plugin 狀態）。

    防禦性：facade 路徑無 sdd_governance / 非 SDD recursion signoff → 回 ""（零退化）。
    """
    gov = getattr(runner, "_sdd_governance_plugin", None)
    if gov is None:
        return ""
    try:
        return gov.pending_topology_dashboard() or ""
    except Exception:  # noqa: BLE001 — 儀表板為 advisory，絕不拖垮既有 escalation 鏈
        return ""


def dump_escalation_impl(
    runner: "PlaybookRunner",
    tracker: "FailureTracker",
    task: "PlaybookTask",
    playbook_path: str,
    final_eval_output: str,
    human_hint: str = "",
    topology_dashboard: str = "",
) -> "EscalationDump":
    """SD_06 W2-T2-12：_save_escalation_dump 全文下沉。

    含 cfg snapshot + _notify_cb closure；委派至 CheckpointPlugin.save_escalation_dump。
    SD_05 W3 Arch-M1：closure 只捕獲 notification 必要欄位 snapshot，避免 cfg 熱重載污染。

    AutoSDD_improving_14（W-14-2）：topology_dashboard 未顯式傳入時，自 runner 上 SDD 治理
    plugin 解析（fail-closed 已在 plugin/adapter 端完成；此處只取結果）。
    """
    from .playbook_runner import _pr

    cfg = runner._cfg
    if not topology_dashboard:
        topology_dashboard = _resolve_topology_dashboard(runner)
    cfg_snapshot = SimpleNamespace(
        checkpoint_dir=cfg.checkpoint_dir,
        notification=SimpleNamespace(
            enabled=cfg.notification.enabled,
            webhook_url=getattr(cfg.notification, "webhook_url", None),
        ),
    )

    def _notify_cb(*, title, message, dump_path):
        _pr().notify_escalation(
            title=title, message=message,
            dump_path=str(dump_path) if dump_path else "",
            cfg=cfg_snapshot,
        )

    return runner._checkpoint_plugin.save_escalation_dump(
        tracker=tracker,
        task=task,
        playbook_path=playbook_path,
        final_eval_output=final_eval_output,
        checkpoint_dir=cfg.checkpoint_dir,
        log_dir=cfg.log_dir,
        human_hint=human_hint,
        notify_callback=_notify_cb,
        topology_dashboard=topology_dashboard,
    )
