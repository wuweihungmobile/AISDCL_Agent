"""
自動偵測目標專案使用哪一種 AISDLC 工作流程。
偵測依據：目錄結構中的標記檔案/資料夾。
"""
from __future__ import annotations
from enum import Enum
from pathlib import Path
import logging

logger = logging.getLogger("autoclaude.execution.workflow_detector")


class WorkflowType(str, Enum):
    AISDLC = "aisdlc"
    AISDLC_SDD = "aisdlc_sdd"
    UNKNOWN = "unknown"


class WorkflowDetector:
    # AISDLC_SDD 特有標記（優先檢查）
    _SDD_MARKERS = [
        "docs_template/sdd",
        "cicd/SDD_GREENFIELD_CICD.md",
        "cicd/SDD_BROWNFIELD_CICD.md",
    ]
    # 標準 AISDLC 標記
    _AISDLC_MARKERS = [
        "agent/core",
        "workflow/core",
        "docs_template/core/prd",
    ]

    def detect(self, path: str) -> WorkflowType:
        root = Path(path)
        if not root.exists():
            logger.warning("工作流程路徑不存在: %s", path)
            return WorkflowType.UNKNOWN

        for marker in self._SDD_MARKERS:
            if (root / marker).exists():
                logger.info("偵測到 AISDLC_SDD 工作流程 (標記: %s)", marker)
                return WorkflowType.AISDLC_SDD

        for marker in self._AISDLC_MARKERS:
            if (root / marker).exists():
                logger.info("偵測到 AISDLC 工作流程 (標記: %s)", marker)
                return WorkflowType.AISDLC

        logger.warning("無法識別工作流程類型，路徑: %s", path)
        return WorkflowType.UNKNOWN
