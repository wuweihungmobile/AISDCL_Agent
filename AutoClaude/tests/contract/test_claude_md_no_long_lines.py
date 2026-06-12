"""SD_09 R18 後續 — CLAUDE.md 單行字元上限 contract test。

對應：
  - ADR-SD08-001 §2.1 + 整合專家方案 E 抗膨脹保險 #2
  - 防「單行繞過 ≤ 400 行紅線」反模式（如 SD_09 W3 line 198 R11-18 累積敘事 2,397 字元怪物段）
"""
from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CLAUDE_MD = PROJECT_ROOT / "CLAUDE.md"

# 單行字元上限。設定基於：
#   - 一般 markdown 段落自然長度 ~200-400 字元
#   - 表格行 / 長 list 上限 ~600 字元
#   - 800 = 寬鬆容忍 + 強制下沉「累積敘事」型怪物段
#
# R23 audit 釐清（紀律 #4 驗證鏡子）：MAX_LINE_CHARS 以 **Python codepoint**（即 len(str)）
# 計，**非 UTF-8 byte 數**。CJK 字元 1 codepoint ≈ 3 bytes，故 800 chars ≈ 2,400 bytes（純 CJK）。
# 設計選擇：codepoint 反映視覺字元數，符合 markdown 可讀性語義；byte 計會對 CJK 過嚴。
# 若需以 byte 計，請新建 test_claude_md_no_long_bytes.py 而非改本檔。
MAX_LINE_CHARS = 800


@pytest.fixture(scope="module")
def claude_md_lines() -> list[str]:
    return CLAUDE_MD.read_text(encoding="utf-8").splitlines()


class TestClaudeMdNoLongLines:
    """單行字元上限 — 抗膨脹保險 #2，防 line 198 怪物段重現。"""

    def test_no_line_exceeds_max_chars(self, claude_md_lines: list[str]) -> None:
        violations: list[tuple[int, int, str]] = []
        for i, line in enumerate(claude_md_lines, start=1):
            n = len(line)
            if n > MAX_LINE_CHARS:
                preview = line[:80].replace("\n", "")
                violations.append((i, n, preview))
        assert not violations, (
            f"CLAUDE.md 有 {len(violations)} 行超過 {MAX_LINE_CHARS} 字元上限：\n"
            + "\n".join(
                f"  line {ln} ({n} chars): {preview}..." for ln, n, preview in violations
            )
            + "\n提示：累積型敘事（多輪 audit 接續寫一行）請下沉至 sprint_history.md §1.x。"
        )


class TestAdversarialMaxChars:
    """R23 紀律 #4 — 驗證鏡子自身要被驗證（assertion 機制真實有效）。"""

    def test_adversarial_long_line_is_detected(self) -> None:
        """餵入含 > 800 字元的 fixture → 必須被偵測。"""
        bad_lines = ["short", "a" * 801, "ok"]
        violations = [(i, len(l)) for i, l in enumerate(bad_lines, 1) if len(l) > MAX_LINE_CHARS]
        assert violations == [(2, 801)], "adversarial 801-char fixture 應被偵測，但漏判"

    def test_adversarial_short_line_passes(self) -> None:
        """合法 fixture（含 800 字元行）必須通過。"""
        ok_lines = ["a" * 800, "b" * 799]
        violations = [(i, len(l)) for i, l in enumerate(ok_lines, 1) if len(l) > MAX_LINE_CHARS]
        assert violations == [], "800-char 邊界 fixture 應通過但被誤判"

    def test_chinese_chars_count_as_codepoints_not_bytes(self) -> None:
        """CJK 800 字元（codepoint）應通過，因設計以 codepoint 計而非 byte。"""
        # 800 中文字 = 2400 bytes，但 800 codepoints
        cjk_line = "中" * 800
        assert len(cjk_line) == 800
        assert len(cjk_line.encode("utf-8")) == 2400
        violations = [1] if len(cjk_line) > MAX_LINE_CHARS else []
        assert violations == [], "800 CJK codepoints 應通過（codepoint 計，非 byte）"
