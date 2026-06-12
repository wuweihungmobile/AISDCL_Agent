"""SD_09 R18 後續 — CLAUDE.md per-section 行數預算 contract test。

對應：
  - ADR-SD08-001 §2.1 CLAUDE.md ≤ 400 行
  - 整合專家方案 E 抗膨脹保險 #1：單區段失控可被擋（即使整檔 < 400）
  - 防止「單一 sprint 段落或紀律段落膨脹」反模式（如 line 198 SD_09 R11-18 累積敘事 2,397 字元案例）
  - **R18 audit P1-2 修復**：SD_Improving_NN 段落改自動偵測（regex），避免新 sprint 啟動時保險失效
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CLAUDE_MD = PROJECT_ROOT / "CLAUDE.md"

# Per-section 行數上限（不含區段標題本身，含內文 + blank lines）
# 設定原則：以 R18 後重構為基線 + 20% buffer，留給未來自然增長
SECTION_BUDGETS: dict[str, int] = {
    "## 🔴 Nightly / CI 取證紀律": 30,
    "## 📜 Phase 0~6 微核心化重構歷程": 60,
    "## 🪝 Hook 治理": 30,
    "## 🏗️ AutoClaude 專案架構": 65,
}

# R22 SD_09 W3 結構性收尾：H2 default budget 反向驗證
# 任何新增 H2（未顯式列入 SECTION_BUDGETS）也受預設上限保護，
# 避免 SD_10+ 新增 H2 段落（如「新功能規範」）逃逸監控直到撞 ≤ 400 紅線。
DEFAULT_H2_BUDGET = 70

# H2 反向驗證白名單（自動生成 / 結構性例外，不受 DEFAULT_H2_BUDGET 約束）
H2_BUDGET_WHITELIST: set[str] = {
    # Architecture Snapshot 由 tools/snapshot_sync.py 從程式碼自動生成
    "## [Architecture Snapshot]",
}

# Sprint H3 段統一上限（自動偵測 ### SD_Improving_NN，N=2 滾動窗口）
# R18 audit P1-2 修復：取代原本靜態 SPRINT_SUBSECTION_BUDGETS={'07','08','09'} dict，
# 避免 SD_10 啟動時保險完全失效。
SPRINT_H3_MAX_LINES = 15
SPRINT_H3_PATTERN = re.compile(r"^### SD_Improving_\d+")
H2_HEADING_PATTERN = re.compile(r"^## .+")


def _section_line_count(content: str, heading: str, h_level: str = "## ") -> int | None:
    """從 heading 行起算到下個同 / 更高層 heading 之前的行數（含 heading 本身）。"""
    lines = content.splitlines()
    start = None
    for i, l in enumerate(lines):
        if l.startswith(heading):
            start = i
            break
    if start is None:
        return None
    # 找下一個同層或更高層 heading
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith(h_level) or lines[j].startswith("# "):
            end = j
            break
    return end - start


@pytest.fixture(scope="module")
def claude_md_content() -> str:
    return CLAUDE_MD.read_text(encoding="utf-8")


class TestClaudeMdSectionBudget:
    """每個 H2 區段個別行數上限 — 抗膨脹保險 #1。"""

    @pytest.mark.parametrize(
        ("heading", "max_lines"), list(SECTION_BUDGETS.items())
    )
    def test_h2_section_within_budget(
        self, claude_md_content: str, heading: str, max_lines: int
    ) -> None:
        n = _section_line_count(claude_md_content, heading, h_level="## ")
        assert n is not None, f"CLAUDE.md 找不到 H2 區段：{heading}"
        assert n <= max_lines, (
            f"CLAUDE.md '{heading}' 區段 {n} 行 > 上限 {max_lines}（per-section budget）；"
            f"請下沉細節至 sprint_history.md 或對應 docs/0X_quality/"
        )

    def test_all_sprint_h3_sections_within_budget(self, claude_md_content: str) -> None:
        """所有 ### SD_Improving_NN H3 段（自動偵測）≤ 15 行。

        R18 audit P1-2 修復：以 regex 自動偵測取代靜態 dict，覆蓋未來所有
        SD_Improving_NN（如 SD_10、SD_11）；未來 sprint 啟動時保險不會失效。
        """
        lines = claude_md_content.splitlines()
        violations: list[tuple[str, int]] = []
        for i, line in enumerate(lines):
            if SPRINT_H3_PATTERN.match(line):
                heading = line.split(" — ")[0].strip()
                n = _section_line_count(claude_md_content, heading, h_level="### ")
                if n is not None and n > SPRINT_H3_MAX_LINES:
                    violations.append((heading, n))
        assert not violations, (
            f"CLAUDE.md 有 {len(violations)} 個 SD_Improving_NN H3 段超過 {SPRINT_H3_MAX_LINES} 行上限：\n"
            + "\n".join(f"  {h}: {n} lines" for h, n in violations)
            + "\n單 sprint H3 累積敘事請下沉至 sprint_history.md §1.x（W 期間骨架先行 SOP）。"
        )

    def test_at_least_one_sprint_h3_present(self, claude_md_content: str) -> None:
        """N=2 滾動窗口：CLAUDE.md 至少保留 2 個 SD_Improving_NN H3 段。

        R18 audit P2-3 修復：原 None 靜默 return 改為 explicit assertion，
        確保「該 key 不存在」資訊被攤在 pytest report 中。
        """
        lines = claude_md_content.splitlines()
        sprint_h3s = [line for line in lines if SPRINT_H3_PATTERN.match(line)]
        assert len(sprint_h3s) >= 2, (
            f"CLAUDE.md 只找到 {len(sprint_h3s)} 個 SD_Improving_NN H3 段；"
            f"ADR-SD08-001 §2.3 滾動窗口 N=2 規定至少保留 2 個（最近 2 sprint）"
        )

    def test_h2_budget_whitelist_entries_exist(self, claude_md_content: str) -> None:
        """R23 audit P2-6：H2_BUDGET_WHITELIST 每個前綴必須在 CLAUDE.md 至少匹配一個 H2。

        防止白名單寫錯（如多空格 `## [Architecture Snapshot ]`）靜默失效。
        """
        lines = claude_md_content.splitlines()
        h2_lines = [l for l in lines if H2_HEADING_PATTERN.match(l)]
        missing: list[str] = []
        for w in H2_BUDGET_WHITELIST:
            if not any(line.startswith(w) for line in h2_lines):
                missing.append(w)
        assert not missing, (
            f"H2_BUDGET_WHITELIST 有 {len(missing)} 個前綴在 CLAUDE.md 找不到對應 H2：{missing}。"
            f"請檢查拼字 / 空格 / 是否該 H2 已被改名或刪除。"
        )

    def test_all_h2_sections_within_default_budget(self, claude_md_content: str) -> None:
        """ADR-SD08-001 v1.1 §9.2 — H2 default budget 反向驗證。

        R22 結構性收尾：任何未列入 SECTION_BUDGETS 明示 budget 的 H2 段，
        都受 DEFAULT_H2_BUDGET 預設上限保護（白名單除外）。
        確保 SD_10+ 新增 H2 段落不會無聲膨脹直到撞 ≤ 400 紅線。
        """
        lines = claude_md_content.splitlines()
        violations: list[tuple[str, int, int]] = []
        for i, line in enumerate(lines):
            if not H2_HEADING_PATTERN.match(line):
                continue
            heading_key = line  # 完整 heading line
            # 白名單比對（前綴 match，因 Snapshot heading 含長後綴）
            if any(heading_key.startswith(w) for w in H2_BUDGET_WHITELIST):
                continue
            # 已在 SECTION_BUDGETS 顯式 override 的，由 test_h2_section_within_budget 覆蓋
            if any(line.startswith(k) for k in SECTION_BUDGETS):
                continue
            n = _section_line_count(claude_md_content, heading_key.split(" — ")[0], h_level="## ")
            if n is not None and n > DEFAULT_H2_BUDGET:
                violations.append((heading_key, n, DEFAULT_H2_BUDGET))
        assert not violations, (
            f"CLAUDE.md 有 {len(violations)} 個未顯式設定 budget 的 H2 段超過 default {DEFAULT_H2_BUDGET} 行：\n"
            + "\n".join(f"  '{h}': {n} 行 > {b}" for h, n, b in violations)
            + "\n請在 SECTION_BUDGETS 顯式加 budget 或下沉細節至 docs/05_development/sprint_history.md。"
        )
