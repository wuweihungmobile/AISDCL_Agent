"""ADR-SD08-001 v1.1 §9 — CLAUDE.md ↔ sprint_history.md 雙向一致性 contract test。

對應：
  - ADR-SD08-001 v1.1 §9.2 五層抗膨脹保險 #4（雙向 link 一致性）
  - SD_09 W3 R22 結構性收尾：W 期間骨架先行 SOP 強制驗證
  - 防止 SD_10+ 啟動時忘記在 sprint_history.md 建立 §1.N 骨架（snapshot_sync --check 亦會擋）

驗證三條件：
  1. CLAUDE.md 每個 ### SD_Improving_NN H3 段 body 必含 `sprint_history.md` link
  2. CLAUDE.md 出現的每個 NN，sprint_history.md 必有對應 ### 1.X SD_Improving_NN
  3. sprint_history.md §1.X 編號連續無 gap（防遺漏 sprint 紀錄）

**R23 adversarial 補強（紀律 #4 驗證鏡子自身要被驗證）**：
  4. 餵入缺 sprint_history.md link 的 CLAUDE.md fixture → 驗 test fail（assert fail mechanism 真實有效）
  5. 餵入 NN 缺對應 history 段的 fixture → 驗 test fail
  6. CLAUDE.md 不可有重複 `### SD_Improving_NN` H3（R23 補：dedup 漏洞防護）
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CLAUDE_MD = PROJECT_ROOT / "CLAUDE.md"
SPRINT_HISTORY = PROJECT_ROOT / "docs" / "05_development" / "sprint_history.md"

CLAUDE_MD_SPRINT_H3 = re.compile(r"^### SD_Improving_(\d+)")
SPRINT_HISTORY_H3 = re.compile(r"^### 1\.(\d+) SD_Improving_(\d+)")


def _h3_body(content: str, heading_line: str, h_level: str = "### ") -> str:
    """從 heading 行起，回傳到下個同 / 更高層 heading 之前的 body（含 heading）。"""
    lines = content.splitlines()
    start = None
    for i, l in enumerate(lines):
        if l == heading_line or l.startswith(heading_line.split(" — ")[0]):
            start = i
            break
    if start is None:
        return ""
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith(h_level) or lines[j].startswith("## ") or lines[j].startswith("# "):
            end = j
            break
    return "\n".join(lines[start:end])


@pytest.fixture(scope="module")
def claude_md_content() -> str:
    return CLAUDE_MD.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def sprint_history_content() -> str:
    return SPRINT_HISTORY.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def claude_md_sprint_nns(claude_md_content: str) -> list[str]:
    """CLAUDE.md 內所有 ### SD_Improving_NN H3 的 NN（保持出現順序）。"""
    nns: list[str] = []
    for line in claude_md_content.splitlines():
        m = CLAUDE_MD_SPRINT_H3.match(line)
        if m:
            nns.append(m.group(1))
    return nns


@pytest.fixture(scope="module")
def sprint_history_sections(sprint_history_content: str) -> list[tuple[str, str]]:
    """sprint_history.md 內所有 ### 1.X SD_Improving_NN 的 (X, NN)。"""
    pairs: list[tuple[str, str]] = []
    for line in sprint_history_content.splitlines():
        m = SPRINT_HISTORY_H3.match(line)
        if m:
            pairs.append((m.group(1), m.group(2)))
    return pairs


class TestClaudeMdSprintAnchor:
    """ADR-SD08-001 v1.1 §9.2 抗膨脹保險 #4 — 雙向 link 一致性。"""

    def test_each_claude_md_h3_body_has_sprint_history_link(
        self, claude_md_content: str, claude_md_sprint_nns: list[str]
    ) -> None:
        """CLAUDE.md 每個 ### SD_Improving_NN body 必含 sprint_history.md 連結。"""
        violations: list[str] = []
        lines = claude_md_content.splitlines()
        for i, line in enumerate(lines):
            m = CLAUDE_MD_SPRINT_H3.match(line)
            if not m:
                continue
            nn = m.group(1)
            body = _h3_body(claude_md_content, line, h_level="### ")
            if "sprint_history.md" not in body:
                violations.append(f"SD_Improving_{nn} (CLAUDE.md line {i+1})")
        assert not violations, (
            f"CLAUDE.md 有 {len(violations)} 個 sprint H3 缺 sprint_history.md link：\n"
            + "\n".join(f"  {v}" for v in violations)
            + "\n依 ADR-SD08-001 v1.1 §9.1 雙模式設計，H3 body 應含 sprint_history.md 連結"
            "（W 期間骨架先行：詳細紀錄寫於 sprint_history.md §1.N）。"
        )

    def test_each_claude_md_nn_has_history_section(
        self,
        claude_md_sprint_nns: list[str],
        sprint_history_sections: list[tuple[str, str]],
    ) -> None:
        """CLAUDE.md 每個 NN，sprint_history.md 必有對應 ### 1.X SD_Improving_NN 骨架。"""
        history_nns = {nn for _, nn in sprint_history_sections}
        missing: list[str] = []
        for nn in claude_md_sprint_nns:
            if nn not in history_nns:
                missing.append(nn)
        assert not missing, (
            f"CLAUDE.md 出現 {missing} 但 sprint_history.md 缺對應 ### 1.X SD_Improving_NN 骨架。\n"
            f"新 Sprint 啟動時應先跑 `python tools/scaffold_sprint_section.py --sprint NN`，"
            f"再於 CLAUDE.md 加 H3。\n（ADR-SD08-001 v1.1 §9.1 W 期間骨架先行 SOP）"
        )

    def test_sprint_history_numbering_continuous(
        self, sprint_history_sections: list[tuple[str, str]]
    ) -> None:
        """sprint_history.md §1.X 編號必須連續無 gap（防遺漏 sprint）。"""
        if not sprint_history_sections:
            pytest.skip("sprint_history.md 尚未建立任何 § 1.X 段")
        xs = sorted(int(x) for x, _ in sprint_history_sections)
        gaps = [(xs[i - 1], xs[i]) for i in range(1, len(xs)) if xs[i] - xs[i - 1] > 1]
        assert not gaps, (
            f"sprint_history.md §1.X 編號不連續：{gaps}（前→後）。"
            f"請補上中間缺漏的 sprint 骨架。"
        )

    def test_at_least_two_history_sections(
        self, sprint_history_sections: list[tuple[str, str]]
    ) -> None:
        """sprint_history.md 至少需有 2 個 §1.X 段（對應 N=2 滾動窗口）。"""
        assert len(sprint_history_sections) >= 2, (
            f"sprint_history.md 只有 {len(sprint_history_sections)} 個 §1.X 段；"
            f"ADR-SD08-001 §2.3 N=2 滾動窗口至少需 2 個。"
        )

    def test_no_duplicate_sprint_h3_in_claude_md(
        self, claude_md_sprint_nns: list[str]
    ) -> None:
        """R23 audit P2-4：CLAUDE.md 不可有重複 `### SD_Improving_NN` H3。

        snapshot_sync.check_sprint_skeleton_alignment() 用 set 去重，無法偵測重複 H3；
        本 case 用 list 計次直接擋。
        """
        from collections import Counter
        counts = Counter(claude_md_sprint_nns)
        duplicates = {nn: c for nn, c in counts.items() if c > 1}
        assert not duplicates, (
            f"CLAUDE.md 含重複 ### SD_Improving_NN H3：{duplicates}。"
            f"請刪除重複段或合併內容。"
        )


class TestSprintAnchorAdversarial:
    """R23 紀律 #4 — 驗證鏡子自身要被驗證（assertion 機制真實有效）。"""

    def _run_link_test(self, content: str) -> tuple[bool, str]:
        """模擬 test_each_claude_md_h3_body_has_sprint_history_link 邏輯。"""
        violations: list[str] = []
        lines = content.splitlines()
        for i, line in enumerate(lines):
            m = CLAUDE_MD_SPRINT_H3.match(line)
            if not m:
                continue
            nn = m.group(1)
            body = _h3_body(content, line, h_level="### ")
            if "sprint_history.md" not in body:
                violations.append(f"SD_Improving_{nn} line {i+1}")
        return (not violations), "; ".join(violations)

    def test_adversarial_h3_missing_link_is_detected(self) -> None:
        """餵入缺 sprint_history.md link 的 fixture → 必須被偵測。"""
        bad = "# x\n\n### SD_Improving_10（test）\n\nbody without link\n"
        passed, msg = self._run_link_test(bad)
        assert not passed, "adversarial fixture 應被偵測為缺 link，但通過了"
        assert "SD_Improving_10" in msg

    def test_adversarial_h3_with_link_passes(self) -> None:
        """合法 fixture（含 sprint_history.md link）必須通過。"""
        good = (
            "# x\n\n### SD_Improving_10（test）\n\n"
            "body 詳見 [sprint_history.md §1.8](docs/05_development/sprint_history.md)\n"
        )
        passed, _ = self._run_link_test(good)
        assert passed, "合法 fixture 應通過但被誤判 fail"

    def test_adversarial_nn_missing_history_section_is_detected(self) -> None:
        """餵入 NN 在 CLAUDE.md 但 sprint_history.md 缺對應段 → 必須被偵測。"""
        claude_nns = ["10"]
        history_pairs: list[tuple[str, str]] = [("7", "09")]
        history_nns = {nn for _, nn in history_pairs}
        missing = [nn for nn in claude_nns if nn not in history_nns]
        assert missing == ["10"], "adversarial fixture 應被偵測為缺對應段，但通過了"

    def test_h3_body_extracts_first_when_duplicates_present(self) -> None:
        """`_h3_body` helper 在重複 H3 時抓第一個（已知限制；duplicates 由 test_no_duplicate_h3 擋）。"""
        content = (
            "# x\n\n### SD_Improving_10（first）\n\nfirst body without link\n\n"
            "### SD_Improving_10（dup）\n\nsecond body [sprint_history.md](x)\n"
        )
        body = _h3_body(content, "### SD_Improving_10（first）", h_level="### ")
        assert "first body" in body
        assert "second body" not in body
