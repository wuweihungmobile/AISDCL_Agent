"""tools/scaffold_sprint_section.py — Sprint W0 骨架自動生成 CLI 單元測試。

對應 ADR-SD08-001 v1.1 §9.2 五層抗膨脹保險 #5（W0 骨架自動產生）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

import scaffold_sprint_section as scaffold  # noqa: E402


SAMPLE_HISTORY = """\
# Sprint 歷史

## 1. 主目錄

### 1.1 SD_Improving_03（Phase 4）— ✅ 完成

內容…

### 1.2 SD_Improving_04（God-object）— ✅ 完成

內容…

---

## 2. 議題索引表

| 議題 | 對應 |
|------|------|
"""


class TestFindExisting:
    def test_returns_none_when_sprint_not_found(self) -> None:
        existing, max_x = scaffold.find_existing(SAMPLE_HISTORY, "10")
        assert existing is None
        assert max_x == 2

    def test_returns_x_when_sprint_exists(self) -> None:
        existing, max_x = scaffold.find_existing(SAMPLE_HISTORY, "04")
        assert existing == 2
        assert max_x == 2

    def test_max_x_picks_highest_when_multiple(self) -> None:
        content = SAMPLE_HISTORY + "\n### 1.5 SD_Improving_07（測試）— ✅\n"
        existing, max_x = scaffold.find_existing(content, "10")
        assert existing is None
        assert max_x == 5


class TestBuildSkeleton:
    def test_skeleton_contains_required_fields(self) -> None:
        sk = scaffold.build_skeleton("10", 8, "示例主軸", "2026-06-01")
        assert "### 1.8 SD_Improving_10" in sk
        assert "示例主軸" in sk
        assert "2026-06-01" in sk
        assert "#### 1.8.1 W0" in sk
        assert "#### 1.8.3 W3 zero-trust audit" in sk
        assert "ADR-SD08-001 v1.1 §9" in sk

    def test_skeleton_warns_against_writing_claude_md(self) -> None:
        sk = scaffold.build_skeleton("10", 8, "test", "2026-06-01")
        assert "不寫入 CLAUDE.md" in sk

    def test_skeleton_references_next_sprint_in_w6(self) -> None:
        sk = scaffold.build_skeleton("10", 8, "test", "2026-06-01")
        # SD_10 -> next is SD_11
        assert "SD_11" in sk


class TestInsertSkeleton:
    def test_inserts_before_issues_index(self) -> None:
        skeleton = "### 1.3 SD_Improving_10（test）\n\nbody\n\n---\n"
        result = scaffold.insert_skeleton(SAMPLE_HISTORY, skeleton)
        idx_skel = result.find("### 1.3 SD_Improving_10")
        idx_issues = result.find("## 2. 議題索引表")
        assert idx_skel < idx_issues
        assert idx_skel > 0

    def test_falls_back_to_append_when_issues_index_missing(self) -> None:
        content = "# Doc\n\n### 1.1 SD_Improving_03\n\nbody\n"
        skeleton = "### 1.2 SD_Improving_04\n"
        result = scaffold.insert_skeleton(content, skeleton)
        assert result.endswith(skeleton)


class TestCli:
    def test_dry_run_does_not_modify_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_history = tmp_path / "sprint_history.md"
        fake_history.write_text(SAMPLE_HISTORY, encoding="utf-8")
        monkeypatch.setattr(scaffold, "SPRINT_HISTORY", fake_history)
        monkeypatch.setattr(sys, "argv", [
            "scaffold_sprint_section.py", "--sprint", "10", "--title", "test",
            "--dry-run", "--date", "2026-06-01",
        ])
        rc = scaffold.main()
        assert rc == 0
        assert fake_history.read_text(encoding="utf-8") == SAMPLE_HISTORY

    def test_actual_write_inserts_skeleton(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_history = tmp_path / "sprint_history.md"
        fake_history.write_text(SAMPLE_HISTORY, encoding="utf-8")
        monkeypatch.setattr(scaffold, "SPRINT_HISTORY", fake_history)
        monkeypatch.setattr(sys, "argv", [
            "scaffold_sprint_section.py", "--sprint", "10", "--title", "新主軸",
            "--date", "2026-06-01",
        ])
        rc = scaffold.main()
        assert rc == 0
        content = fake_history.read_text(encoding="utf-8")
        assert "### 1.3 SD_Improving_10（新主軸）" in content
        assert "## 2. 議題索引表" in content  # not removed
        # 順序：§1.3 應在 §1.2 之後、§2 之前
        idx_12 = content.find("### 1.2 SD_Improving_04")
        idx_13 = content.find("### 1.3 SD_Improving_10")
        idx_2 = content.find("## 2. 議題索引表")
        assert idx_12 < idx_13 < idx_2

    def test_existing_sprint_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_history = tmp_path / "sprint_history.md"
        fake_history.write_text(SAMPLE_HISTORY, encoding="utf-8")
        monkeypatch.setattr(scaffold, "SPRINT_HISTORY", fake_history)
        monkeypatch.setattr(sys, "argv", [
            "scaffold_sprint_section.py", "--sprint", "04", "--title", "dup",
            "--date", "2026-06-01",
        ])
        rc = scaffold.main()
        assert rc == 1
        assert fake_history.read_text(encoding="utf-8") == SAMPLE_HISTORY

    def test_missing_history_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        missing = tmp_path / "nonexistent.md"
        monkeypatch.setattr(scaffold, "SPRINT_HISTORY", missing)
        monkeypatch.setattr(sys, "argv", [
            "scaffold_sprint_section.py", "--sprint", "99", "--title", "x",
            "--date", "2026-06-01",
        ])
        rc = scaffold.main()
        assert rc == 1
