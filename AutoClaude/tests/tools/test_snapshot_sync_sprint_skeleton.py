"""tools/snapshot_sync.py — sprint H3 vs sprint_history.md §1.X 對齊驗證單元測試。

對應 ADR-SD08-001 v1.1 §9.2 五層抗膨脹保險 #4（雙向 link 一致性）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

import snapshot_sync  # noqa: E402


SAMPLE_CLAUDE_MD = """\
# Doc

## H2

### SD_Improving_08（test）

body

### SD_Improving_09（test）

body
"""

SAMPLE_HISTORY = """\
# History

## 1. 主目錄

### 1.6 SD_Improving_08（done）— ✅

body

### 1.7 SD_Improving_09（in progress）— 🟡

body
"""


class TestCheckSprintSkeletonAlignment:
    def test_no_issue_when_aligned(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cm = tmp_path / "CLAUDE.md"
        sh = tmp_path / "sprint_history.md"
        cm.write_text(SAMPLE_CLAUDE_MD, encoding="utf-8")
        sh.write_text(SAMPLE_HISTORY, encoding="utf-8")
        monkeypatch.setattr(snapshot_sync, "CLAUDE_MD", cm)
        monkeypatch.setattr(snapshot_sync, "SPRINT_HISTORY", sh)
        issues = snapshot_sync.check_sprint_skeleton_alignment()
        assert issues == []

    def test_detects_missing_history_skeleton(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # CLAUDE.md 有 SD_10 但 sprint_history.md 缺
        cm = tmp_path / "CLAUDE.md"
        sh = tmp_path / "sprint_history.md"
        cm.write_text(
            SAMPLE_CLAUDE_MD + "\n### SD_Improving_10（new）\n\nbody\n",
            encoding="utf-8",
        )
        sh.write_text(SAMPLE_HISTORY, encoding="utf-8")
        monkeypatch.setattr(snapshot_sync, "CLAUDE_MD", cm)
        monkeypatch.setattr(snapshot_sync, "SPRINT_HISTORY", sh)
        issues = snapshot_sync.check_sprint_skeleton_alignment()
        assert len(issues) == 1
        assert "SD_Improving_10" in issues[0]
        assert "scaffold_sprint_section.py" in issues[0]

    def test_detects_multiple_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cm = tmp_path / "CLAUDE.md"
        sh = tmp_path / "sprint_history.md"
        cm.write_text(
            SAMPLE_CLAUDE_MD
            + "\n### SD_Improving_10（a）\n\n### SD_Improving_11（b）\n\nbody\n",
            encoding="utf-8",
        )
        sh.write_text(SAMPLE_HISTORY, encoding="utf-8")
        monkeypatch.setattr(snapshot_sync, "CLAUDE_MD", cm)
        monkeypatch.setattr(snapshot_sync, "SPRINT_HISTORY", sh)
        issues = snapshot_sync.check_sprint_skeleton_alignment()
        assert len(issues) == 2

    def test_fail_open_when_files_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(snapshot_sync, "CLAUDE_MD", tmp_path / "missing.md")
        monkeypatch.setattr(snapshot_sync, "SPRINT_HISTORY", tmp_path / "missing2.md")
        issues = snapshot_sync.check_sprint_skeleton_alignment()
        assert issues == []  # fail-open，不阻斷

    def test_excess_history_not_flagged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # sprint_history.md 多 sprint（如已下沉的舊 sprint），CLAUDE.md 沒有 → 不告警
        # 因為 N=2 滾動窗口允許 history 比 CLAUDE.md 多
        cm = tmp_path / "CLAUDE.md"
        sh = tmp_path / "sprint_history.md"
        cm.write_text("### SD_Improving_09（only this）\n\nbody\n", encoding="utf-8")
        sh.write_text(SAMPLE_HISTORY, encoding="utf-8")
        monkeypatch.setattr(snapshot_sync, "CLAUDE_MD", cm)
        monkeypatch.setattr(snapshot_sync, "SPRINT_HISTORY", sh)
        issues = snapshot_sync.check_sprint_skeleton_alignment()
        assert issues == []

    def test_detects_duplicate_h3_in_claude_md(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """R23 audit P2-4：CLAUDE.md 有重複 ### SD_Improving_09 → 必須告警。"""
        cm = tmp_path / "CLAUDE.md"
        sh = tmp_path / "sprint_history.md"
        cm.write_text(
            "### SD_Improving_09（first）\n\nbody1\n\n### SD_Improving_09（dup）\n\nbody2\n",
            encoding="utf-8",
        )
        sh.write_text(SAMPLE_HISTORY, encoding="utf-8")
        monkeypatch.setattr(snapshot_sync, "CLAUDE_MD", cm)
        monkeypatch.setattr(snapshot_sync, "SPRINT_HISTORY", sh)
        issues = snapshot_sync.check_sprint_skeleton_alignment()
        assert any("重複" in i and "SD_Improving_09" in i for i in issues), (
            f"應偵測到 CLAUDE.md 重複 H3，但 issues={issues}"
        )

    def test_detects_duplicate_section_in_sprint_history(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """sprint_history.md 有重複 §1.X SD_NN → 必須告警。"""
        cm = tmp_path / "CLAUDE.md"
        sh = tmp_path / "sprint_history.md"
        cm.write_text(SAMPLE_CLAUDE_MD, encoding="utf-8")
        sh.write_text(
            SAMPLE_HISTORY + "\n### 1.8 SD_Improving_09（dup）— 重複\n\nbody\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(snapshot_sync, "CLAUDE_MD", cm)
        monkeypatch.setattr(snapshot_sync, "SPRINT_HISTORY", sh)
        issues = snapshot_sync.check_sprint_skeleton_alignment()
        assert any("重複" in i and "SD_Improving_09" in i for i in issues), (
            f"應偵測到 sprint_history 重複段，但 issues={issues}"
        )
