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


# --- $MinPass/MIN_PASS 語意鎖（R19 修復包 B，DEF-101-243①）登記表 -----------------

_SH_PASS_RE = re.compile(r'pass\s+"([^"]*)"')

# macos_smoke_local.sh 裡「字面上兩個 pass 呼叫、實際執行只會命中其一」的互斥分支
# （case 分支 / if-else 分支）。每個 tuple 是該互斥組的完整訊息文字集合。
_SH_EXCLUSIVE_PASS_GROUPS = (
    (
        "dispatcher 直呼煙霧（pre-commit 放行/擋 NTFS 保留名、post-commit、pre-push 刪除跳過）",
        "dispatcher 直呼煙霧（pre-commit 放行、post-commit、pre-push 刪除跳過；NTFS 保留名子測試 SKIP——非 macOS 平台先擋）",
    ),
    (
        "install_mac_nightly.sh --render-only plist 產出＋plutil -lint＋log 落點斷言",
        "install_mac_nightly.sh --render-only（SKIP-計-PASS：非 macOS）",
    ),
)

_PS1_PASS_ITEM_RE = re.compile(r"Pass-Item\s+['\"]([^'\"]*)['\"]")

# windows_smoke_local.ps1 裡「函式定義內只有 1 個 Pass-Item 字面出現，但函式被
# 呼叫多次」的共用函式（每次呼叫最多貢獻 1 個實際 PASS）。
_PS1_MULTI_CALL_FUNCS = ("Test-InstallRoundtrip", "Test-WorktreeReject")


def _extract_ps1_function_body(text: str, func_name: str) -> str:
    """抽出 `function <func_name> {` 到下一個「行首恰為 `}`」之間的函式體全文
    （本檔兩支共用函式皆以此縮排慣例撰寫：函式自身收尾 `}` 在行首列 0，內部巢狀
    區塊的收尾皆有縮排，不會提前誤中）。"""
    m = re.search(rf"^function\s+{re.escape(func_name)}\b.*?\n(.*?)^\}}", text, re.MULTILINE | re.DOTALL)
    if m is None:
        raise AssertionError(f"windows_smoke_local.ps1 找不到 {func_name} 函式定義——結構已變動，需同步更新語意鎖登記表")
    return m.group(1)


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

    def test_min_pass_equals_actual_step_count(self) -> None:
        """DEF-101-243①：$MinPass/MIN_PASS 釘選值本身須等於腳本實際會執行到的
        PASS 步驟數，而非只交叉比對「文件宣稱＝腳本釘選」（上方
        test_onboarding_pass_claims_match_script_pins 只鎖這一半）。QA 二審
        bug-injection 證實：只改錯釘選值本身、步驟仍在，既有測試不會變紅。

        兩腳本「原始碼字面 pass/Pass-Item 呼叫次數」與「實際執行到的步驟數」不
        直接相等：
        - macos_smoke_local.sh 有互斥分支（case/if-else 兩條路徑各呼叫一次
          pass，實際執行恰命中其一），字面數比實際數多。
        - windows_smoke_local.ps1 有共用函式（Test-InstallRoundtrip /
          Test-WorktreeReject）被呼叫多次、函式定義內只有 1 個 Pass-Item 字面
          出現，字面數比實際數少。

        通用剖析器精確歸納這兩種語意風險高（易在未來改版時悄悄算錯、製造假的
        安全感），改用顯式登記表 + fail-loud 存在性檢查（同 R19 修復包 A
        test_known_consumers_detected() 精神）：登記已知的「字面數與實際執行數
        不一致」樣式，明確列出其原始碼錨點；錨點消失（訊息被改寫/函式改名）即
        讓本測試紅，逼人工重新核算並更新登記表。
        """
        sh_text = _read(_SH)
        all_sh_msgs = _SH_PASS_RE.findall(sh_text)
        collapsed = 0
        for group in _SH_EXCLUSIVE_PASS_GROUPS:
            for msg in group:
                self.assertIn(
                    msg, all_sh_msgs,
                    f"macos_smoke_local.sh 互斥 pass 訊息錨點消失：{msg!r}——"
                    "MIN_PASS 語意登記表已腐化，需人工重新核對 _SH_EXCLUSIVE_PASS_GROUPS",
                )
            collapsed += len(group) - 1  # N 條互斥路徑實際執行只命中其一，收斂為 1
        actual_sh_steps = len(all_sh_msgs) - collapsed
        sh_pin = _extract_pin(sh_text, r"^MIN_PASS=(\d+)")
        self.assertEqual(
            actual_sh_steps, sh_pin,
            f"macos_smoke_local.sh 實際步驟數（互斥分支收斂後）={actual_sh_steps}，"
            f"與 MIN_PASS 釘選值 {sh_pin} 不一致——釘選值本身寫錯或步驟增減未同步",
        )

        ps1_text = _read(_PS1)
        all_ps1_msgs = _PS1_PASS_ITEM_RE.findall(ps1_text)
        in_shared_func_count = 0
        expanded = 0
        for func_name in _PS1_MULTI_CALL_FUNCS:
            body = _extract_ps1_function_body(ps1_text, func_name)
            body_pass_count = len(_PS1_PASS_ITEM_RE.findall(body))
            self.assertEqual(
                body_pass_count, 1,
                f"windows_smoke_local.ps1 函式 {func_name} 函式體內 Pass-Item "
                f"字面出現次數={body_pass_count}（預期恰 1）——多次呼叫語意鎖假設"
                "已被打破，需重新核對 _PS1_MULTI_CALL_FUNCS 登記表",
            )
            in_shared_func_count += 1
            call_count = len(
                re.findall(rf"^\s*{re.escape(func_name)}\b", ps1_text, re.MULTILINE)
            )
            self.assertGreaterEqual(
                call_count, 1,
                f"windows_smoke_local.ps1 找不到 {func_name} 任何呼叫點——"
                "語意鎖登記表已腐化（函式改名/移除？）",
            )
            expanded += call_count
        actual_ps1_steps = (len(all_ps1_msgs) - in_shared_func_count) + expanded
        ps1_pin = _extract_pin(ps1_text, r"^\$MinPass\s*=\s*(\d+)")
        self.assertEqual(
            actual_ps1_steps, ps1_pin,
            f"windows_smoke_local.ps1 實際步驟數（共用函式呼叫次數展開後）="
            f"{actual_ps1_steps}，與 $MinPass 釘選值 {ps1_pin} 不一致——"
            "釘選值本身寫錯或步驟增減未同步",
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
