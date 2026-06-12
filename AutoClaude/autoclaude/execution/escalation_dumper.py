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


def dump_escalation_impl(
    runner: "PlaybookRunner",
    tracker: "FailureTracker",
    task: "PlaybookTask",
    playbook_path: str,
    final_eval_output: str,
    human_hint: str = "",
) -> "EscalationDump":
    """SD_06 W2-T2-12：_save_escalation_dump 全文下沉。

    含 cfg snapshot + _notify_cb closure；委派至 CheckpointPlugin.save_escalation_dump。
    SD_05 W3 Arch-M1：closure 只捕獲 notification 必要欄位 snapshot，避免 cfg 熱重載污染。
    """
    from .playbook_runner import _pr

    cfg = runner._cfg
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
    )
