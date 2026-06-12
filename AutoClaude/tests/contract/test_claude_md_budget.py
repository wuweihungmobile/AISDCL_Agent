"""ADR-SD08-001：CLAUDE.md 文件治理契約測試（≤ 400 行 + Snapshot SSOT + 必留章節）。

對應：
  - SD_08 W0 T0-E6
  - ADR-SD08-001 §2.1 (CLAUDE.md ≤ 400) + §2.2 (Snapshot SSOT) + §2.3 (滾動窗口 N=2)
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CLAUDE_MD = PROJECT_ROOT / "CLAUDE.md"
SNAPSHOT_BEGIN = "<!-- ARCH_SNAPSHOT_BEGIN -->"
SNAPSHOT_END = "<!-- ARCH_SNAPSHOT_END -->"


@pytest.fixture(scope="module")
def claude_md_content() -> str:
    assert CLAUDE_MD.exists(), f"CLAUDE.md 不存在: {CLAUDE_MD}"
    return CLAUDE_MD.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def claude_md_lines() -> list[str]:
    return CLAUDE_MD.read_text(encoding="utf-8").splitlines()


class TestClaudeMdLineBudget:
    """ADR-SD08-001 §2.1：CLAUDE.md ≤ 400 行（wc -l 等價）。"""

    def test_claude_md_at_most_400_lines(self, claude_md_lines: list[str]) -> None:
        n = len(claude_md_lines)
        assert n <= 400, (
            f"CLAUDE.md={n} lines > 400 (ADR-SD08-001 §2.1)；"
            f"請執行下沉至 docs/05_development/sprint_history.md"
        )

    def test_claude_md_not_empty(self, claude_md_content: str) -> None:
        assert claude_md_content.strip(), "CLAUDE.md 不可為空"


class TestArchitectureSnapshotSection:
    """ADR-SD08-001 §2.2：[Architecture Snapshot] SSOT 區段格式驗證。"""

    def test_snapshot_begin_marker_present(self, claude_md_content: str) -> None:
        assert SNAPSHOT_BEGIN in claude_md_content, (
            f"CLAUDE.md 缺少 {SNAPSHOT_BEGIN}（執行 python tools/snapshot_sync.py 重生）"
        )

    def test_snapshot_end_marker_present(self, claude_md_content: str) -> None:
        assert SNAPSHOT_END in claude_md_content, (
            f"CLAUDE.md 缺少 {SNAPSHOT_END}"
        )

    def test_snapshot_block_is_well_formed(self, claude_md_content: str) -> None:
        pattern = re.compile(
            re.escape(SNAPSHOT_BEGIN) + r"(.*?)" + re.escape(SNAPSHOT_END),
            re.DOTALL,
        )
        match = pattern.search(claude_md_content)
        assert match is not None, "Snapshot 區段格式錯誤（BEGIN/END 標記順序錯誤）"
        body = match.group(1)
        # 必須包含 5 個子段落（ADR-SD08-001 §2.2）
        required = [
            "[Architecture Snapshot]",
            "LOC Tiers",
            "importlinter Rules",
            "Plugin 列表",
            "Port 列表",
            "DAL 三後端",
        ]
        for label in required:
            assert label in body, f"Snapshot 區段缺少子段：{label}"


class TestRequiredSections:
    """ADR-SD08-001 §2.1：CLAUDE.md 必留三大區段（任一不可下沉）。"""

    @pytest.mark.parametrize(
        "heading",
        [
            "溝通語言規範",
            "開發-編譯-測試循環",
            "專案文檔目錄規範",
            "Agent 自動載入",
            "AutoClaude 專案架構",
            "DAL 三後端 storage.mode",
            "PlaybookRunner 關鍵行為",
            "Phase 0~6 微核心化重構歷程",
            "快速導覽",
        ],
    )
    def test_must_keep_heading(self, claude_md_content: str, heading: str) -> None:
        assert heading in claude_md_content, (
            f"CLAUDE.md 缺少必留章節：{heading}（ADR-SD08-001 §2.1）"
        )

    def test_sprint_history_link_present(self, claude_md_content: str) -> None:
        """SD_03~SD_06 詳細紀錄已下沉至 sprint_history.md（滾動窗口 N=2）。"""
        assert "sprint_history.md" in claude_md_content, (
            "CLAUDE.md 必須引用 sprint_history.md（SD_03~SD_06 下沉指引）"
        )

    def test_n2_window_keeps_sd07_sd08(self, claude_md_content: str) -> None:
        """滾動窗口 N=2：SD_08 W6 收尾後當前保留 SD_07 + SD_08 完整摘要。"""
        assert "SD_Improving_07" in claude_md_content, "SD_07 應保留於 N=2 窗口內"
        assert "SD_Improving_08" in claude_md_content, "SD_08 應保留於 N=2 窗口內"
