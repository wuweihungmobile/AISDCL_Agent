"""
CrossStepStateValidator — 跨步驟狀態污染偵測（Gap-010-C）。

在每個 step EXECUTE 前，快速驗證工作目錄是否有前一步驟遺留的未確認修改，
防止 T(N) ESCALATION 的殘骸污染 T(N+1) 的執行環境。
"""
from __future__ import annotations

import os
import subprocess
from typing import Optional

from ..models.playbook import PlaybookTask
from ..utils.trace_context import propagate_to_subprocess_env


class CrossStepStateValidator:
    """
    在每個 step 開始前，執行快速 git status 污染偵測。
    若偵測到異常未確認修改，回傳注入 prompt 的警告文字。
    """

    def validate_before_step(
        self,
        current_step: PlaybookTask,
        prev_step: Optional[PlaybookTask],
        working_dir: str = ".",
        modified_threshold: int = 5,
    ) -> Optional[str]:
        """
        若偵測到跨步驟污染，回傳注入 prompt 的警告文字；否則回傳 None。

        Args:
            current_step: 即將執行的步驟
            prev_step: 上一個步驟（可為 None）
            working_dir: 工作目錄（git 根目錄）
            modified_threshold: 未確認修改檔案數量的警告門檻

        Returns:
            警告文字字串（若有污染）或 None
        """
        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True, cwd=working_dir, timeout=10,
                env=propagate_to_subprocess_env(dict(os.environ)),
            )
            if result.returncode != 0:
                return None  # 非 git 環境，安全略過
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return None

        lines = result.stdout.splitlines()
        modified_count = sum(1 for ln in lines if len(ln) >= 2 and ln[1] in ("M", "A", "D", "R"))
        untracked_count = sum(1 for ln in lines if ln.startswith("??"))

        if modified_count > modified_threshold:
            prev_id = prev_step.step_id if prev_step else "?"
            return (
                f"⚠️ 跨步驟污染警告：偵測到 {modified_count} 個已修改但未確認的檔案（git status）。"
                f"前一步驟 [{prev_id}] 可能未完成清理。"
                f"請先確認這些修改是預期的（或 git stash 後），再繼續當前步驟 [{current_step.step_id}]。"
            )

        if untracked_count > modified_threshold * 3:
            return (
                f"⚠️ 跨步驟注意：偵測到 {untracked_count} 個未追蹤的新檔案。"
                f"請確認這些檔案是否為步驟 [{current_step.step_id}] 的預期產出。"
            )

        return None
