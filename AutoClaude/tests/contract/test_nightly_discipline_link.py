"""SD_09 R18 後續 — Nightly Forensic Discipline 完整版外移後的連結 contract test。

對應：
  - ADR-SD08-001 §2.1 規範性內容可外移細節（方案 E 落地）
  - CLAUDE.md §Nightly / CI 取證紀律 (現為摘要 + 連結)
  - docs/06_quality/Nightly_Forensic_Discipline.md (完整版 SSOT)
"""
from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CLAUDE_MD = PROJECT_ROOT / "CLAUDE.md"
DISCIPLINE_DOC = PROJECT_ROOT / "docs" / "06_quality" / "Nightly_Forensic_Discipline.md"


@pytest.fixture(scope="module")
def claude_md_content() -> str:
    return CLAUDE_MD.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def discipline_doc_content() -> str:
    return DISCIPLINE_DOC.read_text(encoding="utf-8")


class TestNightlyDisciplineLink:
    """CLAUDE.md ↔ Nightly_Forensic_Discipline.md SSOT 連結驗證。"""

    def test_discipline_doc_exists(self) -> None:
        assert DISCIPLINE_DOC.exists(), (
            f"Nightly_Forensic_Discipline.md 不存在: {DISCIPLINE_DOC}"
            "（CLAUDE.md §Nightly 完整版 SSOT 必須就位）"
        )

    def test_claude_md_links_to_discipline_doc(self, claude_md_content: str) -> None:
        assert "docs/06_quality/Nightly_Forensic_Discipline.md" in claude_md_content, (
            "CLAUDE.md §Nightly 區段必須含至完整版的連結"
        )

    def test_discipline_doc_has_all_13_disciplines(self, discipline_doc_content: str) -> None:
        for n in range(1, 14):
            marker = f"### 紀律 #{n}"
            assert marker in discipline_doc_content, (
                f"完整版缺少 {marker}（13 條紀律必須完整）"
            )

    def test_discipline_doc_has_sampling_section(self, discipline_doc_content: str) -> None:
        assert "## 3. 採樣統計紀律" in discipline_doc_content, (
            "完整版必須含採樣統計紀律段（baseline lock samples ≥ 20 + rc 三態）"
        )

    def test_claude_md_summary_keeps_13_numbered_items(self, claude_md_content: str) -> None:
        """CLAUDE.md 摘要必須保留 13 條編號 — 雙向追蹤。"""
        nightly_start = claude_md_content.find("## 🔴 Nightly / CI 取證紀律")
        assert nightly_start >= 0, "CLAUDE.md 必須保留 §Nightly heading"
        next_h2 = claude_md_content.find("\n## ", nightly_start + 1)
        nightly_section = claude_md_content[nightly_start:next_h2]
        for n in range(1, 14):
            assert f"{n}. **" in nightly_section, (
                f"CLAUDE.md §Nightly 摘要缺編號 {n}（13 條必須完整）"
            )
