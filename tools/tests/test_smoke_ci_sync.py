#!/usr/bin/env python3
"""smoke 腳本 ↔ compat-CI ↔ ONBOARDING 的數字/注記機械互鎖（R11 Architect B2）。

WHY：macos_smoke_local.sh / windows_smoke_local.ps1 / macos-compat-ci.yml /
windows-compat-ci.yml 是四份手寫實作，互相宣稱「同步維護」，但 R11 前純靠註解
自律、零機械互鎖——smoke 腳本改 PASS 下限釘選或增刪情境分組時，ONBOARDING.md
的宣稱數字（PASS=10 / PASS=8）與 CI 對應 step 不會有任何訊號。本測試機械抽取
兩腳本的釘選值與 `--- [n/m]` 情境分組標籤，交叉斷言文件宣稱一致、同步注記仍在；
抽取數量另設下限釘選，防宣告 pattern 漂移後靜默 0 命中假綠（比照
check_script_parity._MIN_EXTRACT_COUNTS 慣例）。
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SH = _REPO_ROOT / "tools" / "macos_smoke_local.sh"
_PS1 = _REPO_ROOT / "tools" / "windows_smoke_local.ps1"
_MAC_CI = _REPO_ROOT / ".github" / "workflows" / "macos-compat-ci.yml"
_WIN_CI = _REPO_ROOT / ".github" / "workflows" / "windows-compat-ci.yml"
_ONBOARDING = _REPO_ROOT / "ONBOARDING.md"

# 情境分組標籤（echo/Write-Host 的字面 `--- [n/m]`；檔內框線註解用 U+2500「──」
# 不會誤中）。抽取數量下限釘選＝2026-07-17 現況分組數，刻意刪減分組時同步下修。
_GROUP_RE = re.compile(r"---\s*\[(\d+)/(\d+)\]")
_MIN_GROUPS = {"sh": 5, "ps1": 6}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _extract_pin(text: str, pattern: str) -> int:
    m = re.search(pattern, text, re.MULTILINE)
    if m is None:  # 不用裸 assert：python -O 會剝除 assert，守門靜默失效（R11 P4）
        raise AssertionError(f"抽取不到 PASS 下限釘選——pattern 未命中：{pattern!r}（宣告樣式已漂移）")
    return int(m.group(1))


class TestSmokeCiSync(unittest.TestCase):
    def test_onboarding_pass_claims_match_script_pins(self) -> None:
        """ONBOARDING.md 的 PASS=N 宣稱集合必須恰等於兩腳本釘選值集合。"""
        sh_pin = _extract_pin(_read(_SH), r"^MIN_PASS=(\d+)")
        ps1_pin = _extract_pin(_read(_PS1), r"^\$MinPass\s*=\s*(\d+)")
        claims = {int(v) for v in re.findall(r"(?<![A-Z_])PASS=(\d+)", _read(_ONBOARDING))}
        self.assertEqual(
            claims,
            {sh_pin, ps1_pin},
            f"ONBOARDING.md 宣稱的 smoke PASS 數字 {sorted(claims)} 與腳本釘選 "
            f"{{sh={sh_pin}, ps1={ps1_pin}}} 不一致——改釘選須同步改文件（反之亦然）",
        )

    def test_scenario_groups_consistent_and_floored(self) -> None:
        """分組標籤 [n/m]：n 連續 1..m、組數==m、組數不低於下限釘選（防 0 命中假綠）。"""
        for label, path in (("sh", _SH), ("ps1", _PS1)):
            groups = _GROUP_RE.findall(_read(path))
            floor = _MIN_GROUPS[label]
            self.assertGreaterEqual(
                len(groups), floor,
                f"{path.name} 抽取到 {len(groups)} 個分組標籤 < 下限 {floor}——"
                f"宣告 pattern 疑似漂移（靜默縮面）；刻意刪減請同步下修 _MIN_GROUPS",
            )
            declared_totals = {int(m) for _n, m in groups}
            self.assertEqual(
                declared_totals, {len(groups)},
                f"{path.name} 分組標籤宣告總數 {declared_totals} 與實際組數 "
                f"{len(groups)} 不一致（增刪分組漏改 [n/m] 分母）",
            )
            self.assertEqual(
                [int(n) for n, _m in groups], list(range(1, len(groups) + 1)),
                f"{path.name} 分組編號不連續：{[n for n, _m in groups]}",
            )

    def test_sync_maintenance_comments_present(self) -> None:
        """四向同步注記仍在（防有人刪注記後兩邊靜默分道揚鑣）。"""
        checks = [
            (_SH, "macos-compat-ci.yml"), (_SH, "同步維護"),
            (_PS1, "windows-compat-ci.yml"), (_PS1, "同步維護"),
            (_MAC_CI, "macos_smoke_local.sh"), (_MAC_CI, "同步維護"),
            (_WIN_CI, "windows_smoke_local.ps1"), (_WIN_CI, "同步維護"),
        ]
        for path, needle in checks:
            self.assertIn(
                needle, _read(path),
                f"{path.name} 缺同步注記關鍵字「{needle}」——同步維護約定被刪除？",
            )


if __name__ == "__main__":
    unittest.main()
