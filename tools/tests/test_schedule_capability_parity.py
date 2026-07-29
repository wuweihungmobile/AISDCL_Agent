"""tools/tests/test_schedule_capability_parity.py — 排程能力對照契約（R22 DEF-101-233 殘留修復）。

背景：DEF-101-233（R16 Architect 架構檢視）建議補「排程能力對照契約」機械測試，
斷言 mac 支援子命令集合 ⊆ Windows 支援子命令集合；`tools/install_windows_nightly.ps1`
自 R19 建立後，五輪掃描/複審（R19~R22）皆確認此測試從未真正落地——
`tools/check_script_parity.py` 把這對腳本登記為 `_EXEMPT_PAIRS`（放棄字面比對），
註解暗示「行為對等由 test_install_windows_nightly.py 守門」，但該檔實際只驗證
Windows 腳本自身結構，從未跨檔比對 mac 側能力集合，形成「兩邊都以為對方在管」
的治理縫隙（R22 Architect 一審發現）。

設計原則（R22 SD 一審技術指引）：**禁止字面旗標字串集合比對**——mac `--render-only`
與 Windows `-WhatIf` 語意對等但字面完全不同（前者是自訂旗標產出 plist 供 lint，
後者是 PowerShell 原生 `SupportsShouldProcess` 機制），若用字面集合比對會產生假紅。
改用「語意能力 → 各平台實際承載物」的對照表，各自以靜態 regex 從原始碼抽取實際
存在的承載物，逐一比對映射表宣稱的能力是否兩邊都有對應物。

🔴 R60 DEF-101-539（Scan-C C-01）：本檔原以 **pytest 模組層函式風格**撰寫，而四道
執行 `tools/tests` 的閘門（`tools/git-hooks/pre-push` root-infra leg、
`.github/workflows/root-infra-ci.yml`、`windows-compat-ci.yml`、`macos-compat-ci.yml`）
全部走 `tools/run_root_unittests.py` 的 `unittest discover`——它只收 `TestCase` 子類，
模組層 `def test_*` **一支都不收**。實測 `python -m unittest tools.tests.
test_schedule_capability_parity` → `Ran 0 tests ... OK`，同一檔 pytest → 6 passed。
落地於 R22（0053f2a，2026-07-22），至 R59 之間帶「相容性 R」的收輪 commit 有 **34 支**，
這道鎖從未在任何閘門裡跑過一次。改寫為 `TestCase` 類別風格即真正被收集。
根因不只本檔一支寫錯——**「單檔貢獻 0 支測試」在現行守門下零訊號**（`MIN_TESTS`
下限只抓大規模消失；R60 實測下限值 661 與實況 661 相等＝缺席已被固化進下限），
故同時補 `TestUnittestDiscoverConformance` 這道 repo-wide 前瞻鎖，見該類別 docstring。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import ast
import re
import unittest
import warnings
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAC_SCRIPT = _REPO_ROOT / "tools" / "install_mac_nightly.sh"
_WIN_SCRIPT = _REPO_ROOT / "tools" / "install_windows_nightly.ps1"
_TESTS_DIR = Path(__file__).resolve().parent


def _mac_source() -> str:
    assert _MAC_SCRIPT.exists(), f"mac 安裝器缺失：{_MAC_SCRIPT}"
    return _MAC_SCRIPT.read_text(encoding="utf-8")


def _win_source() -> str:
    assert _WIN_SCRIPT.exists(), f"windows 安裝器缺失：{_WIN_SCRIPT}"
    return _WIN_SCRIPT.read_text(encoding="utf-8-sig")


def _mac_case_labels(src: str) -> set[str]:
    """從 `case "${MODE}" in ... esac` 區塊抽出所有字面 case label。"""
    m = re.search(r'case\s+"\$\{MODE\}"\s+in(.*?)\nesac', src, re.DOTALL)
    assert m is not None, "mac 腳本找不到 case \"${MODE}\" in ... esac 區塊——結構已變動"
    block = m.group(1)
    labels: set[str] = set()
    for raw_label in re.findall(r'^\s*([^)#\n]+)\)\s*$', block, re.MULTILINE):
        for part in raw_label.split("|"):
            labels.add(part.strip())
    return labels


def _win_switch_names(src: str) -> set[str]:
    """從 `param( ... )` 區塊抽出所有 `[switch]$Name` 宣告。"""
    m = re.search(r"param\s*\((.*?)\n\)", src, re.DOTALL)
    assert m is not None, "windows 腳本找不到 param( ... ) 區塊——結構已變動"
    return set(re.findall(r"\[switch\]\$(\w+)", m.group(1)))


class TestScheduleCapabilityParity(unittest.TestCase):
    """mac ↔ Windows 排程安裝器的「語意能力對照表」契約。

    R60：由 pytest 模組層函式改寫為 `TestCase` 方法（見檔頭 DEF-101-539）。斷言主體
    與訊息刻意逐字保留 R22 原文，只換載具形態——形態才是缺陷，內容不是。
    """

    def test_mac_case_labels_extracted_sane(self) -> None:
        """靜態抽取本身要抽到已知的四個核心標籤，證明 regex 未失準（鏡子自證）。"""
        labels = _mac_case_labels(_mac_source())
        for expected in ("install", "--uninstall", "--status", "--render-only"):
            self.assertIn(
                expected, labels,
                f"mac case label 抽取遺漏 {expected!r}——regex 可能已與腳本結構脫節，"
                f"抽到的集合：{labels}",
            )

    def test_win_switch_names_extracted_sane(self) -> None:
        """靜態抽取本身要抽到已知的 switch 集合，證明 regex 未失準（鏡子自證）。"""
        switches = _win_switch_names(_win_source())
        self.assertEqual(
            switches, {"Uninstall", "Status"},
            f"windows switch 抽取結果與預期不符（可能新增/刪除了 switch，"
            f"需同步更新本測試的能力對照表）：{switches}",
        )

    def test_capability_uninstall_present_on_both_platforms(self) -> None:
        """能力：uninstall。mac=`--uninstall`；windows=`-Uninstall` switch。"""
        self.assertIn("--uninstall", _mac_case_labels(_mac_source()))
        self.assertIn("Uninstall", _win_switch_names(_win_source()))

    def test_capability_status_present_on_both_platforms(self) -> None:
        """能力：status query。mac=`--status`；windows=`-Status` switch。"""
        self.assertIn("--status", _mac_case_labels(_mac_source()))
        self.assertIn("Status", _win_switch_names(_win_source()))

    def test_capability_install_default_action_present_on_both_platforms(self) -> None:
        """能力：install（預設動作，無參數時觸發）。

        mac：`MODE="${1:-install}"` 明確以 install 為預設值；windows：docstring
        明文記載「install（預設）」且無 `$Install` switch（無旗標即走 install 分支，
        非另立旗標），並實際呼叫 `Register-ScheduledTask`（ensure 語意落地，非空殼宣稱）。
        """
        mac_src = _mac_source()
        self.assertRegex(
            mac_src, r'MODE="\$\{1:-install\}"',
            "mac 腳本必須以 install 為 MODE 預設值（無參數呼叫＝安裝）",
        )
        win_src = _win_source()
        self.assertRegex(
            win_src, r"install（預設）",
            "windows 腳本 docstring 必須明文記載「install（預設）」語意",
        )
        self.assertNotIn(
            "Install", _win_switch_names(win_src),
            "windows install 能力應為「無旗標時的預設分支」，不應另立 $Install switch"
            "（與 mac 側「無參數＝install」的預設語意對齊）",
        )
        self.assertIn(
            "Register-ScheduledTask", win_src,
            "windows install 分支必須實際呼叫 Register-ScheduledTask（ensure 語意，"
            "非僅文件宣稱）",
        )

    def test_capability_render_preview_present_on_both_platforms(self) -> None:
        """能力：render/preview only（不落地執行，僅預覽/產出供檢視）。

        mac=`--render-only <path>`（自訂旗標，產出 plist 供 lint）；
        windows=`-WhatIf`（PowerShell 原生 `SupportsShouldProcess` 機制）。
        **刻意不比較字面旗標字串**——兩者語意對等但字面不同，字面比對會產生假紅
        （R22 SD 一審明確指出的陷阱）。
        """
        self.assertIn("--render-only", _mac_case_labels(_mac_source()))
        win_src = _win_source()
        self.assertRegex(
            win_src, r"SupportsShouldProcess",
            "windows 腳本必須以 SupportsShouldProcess 提供 render/preview-only 能力"
            "（PowerShell 原生 -WhatIf 機制，語意對等 mac 側 --render-only）",
        )
        self.assertRegex(
            win_src, r"\$PSCmdlet\.ShouldProcess\(",
            "windows 腳本的實際落地動作（Register-ScheduledTask）必須包在 "
            "$PSCmdlet.ShouldProcess(...) 判斷內，-WhatIf 才能真的攔下執行",
        )


class TestUnittestDiscoverConformance(unittest.TestCase):
    """repo-wide 前瞻鎖：`tools/tests/` 每支 `test_*.py` 都必須真的被 `unittest
    discover` 收到測試（DEF-101-539 治本層）。

    WHY 這道鎖才是 C-01 的真價值：把本檔包成 `TestCase` 只治好這一支。現行守門
    `tools/run_root_unittests.py` 的 `MIN_TESTS` 是**下限**語意，只能抓「大規模靜默
    消失」，對「新增/改寫一支檔案而它貢獻 0 支」完全無訊號——R60 實測下限值 661 與
    discover 實況 661 完全相等，證實這 6 支的缺席早已被固化進下限，且
    `RATCHET_STALE_RATIO=1.25`（826 才紅）保證永遠不會有訊號。

    為何放在本檔而不新開掃描器檔案：沿用 DEF-101-519（R59）已裁定的折中慣例
    ——「不新建掃描器檔案，在既有 parity 測試內加一段 repo-wide 枚舉斷言」。本檔正是
    這個缺陷的唯一受害者，WHY 與現象同處一檔，讀者不需跨檔追。

    鎖的兩個形狀（三種靜默丟棄形態中，第一種由 discover 實測抓、後兩種由 AST 抓）：
      ① `discover` 對該檔實收 0 支 → 整支檔案在四道閘門裡不存在（本缺陷的形態）。
      ② 模組層 `def test_*` 函式 → pytest 收、unittest 丟。**② 不能被 ① 取代**：
         一支檔案若同時有 `TestCase` 類別與額外的模組層 `def test_*`，① 會通過
         （實收 > 0）而那幾支模組層測試仍被靜默丟棄。
      ③ 帶 `test_*` 方法但**未繼承** `TestCase` 的類別（pytest 的 `class Test*` 慣例）
         → 同樣 pytest 收、unittest 丟，且 ① 同樣看不到。
    R60 落地時實測：① 命中 1 支（本檔，改寫後歸零）、② 命中 6 支（本檔，改寫後歸零）、
    ③ 全庫 0 支（前瞻性，非現存缺陷）。
    """

    @staticmethod
    def _test_modules() -> list[Path]:
        # 判準與 run_root_unittests.discover_suite 的 pattern="test_*.py" 逐字對齊；
        # 掃描面靜默縮小（目錄改名/清空）本身即失敗，故 0 份時 fail-loud。
        return sorted(_TESTS_DIR.glob("test_*.py"))

    def test_scan_surface_is_not_silently_empty(self) -> None:
        """掃描面自檢：本鎖若因目錄結構變動而掃到 0 份檔案，必須紅而非靜默通過。"""
        modules = self._test_modules()
        self.assertGreaterEqual(
            len(modules), 40,
            f"tools/tests/ 只掃到 {len(modules)} 份 test_*.py——掃描面疑似靜默縮小"
            f"（目錄改名/pattern 不符）；R60 實測 43 份",
        )

    def test_every_test_module_contributes_at_least_one_discovered_test(self) -> None:
        """每支 `test_*.py` 至少貢獻 1 支被 `unittest discover` 收集的測試。

        用 discover 本身當量測面（不是 AST 推測），與四道閘門的收集機制**完全同一顆**。
        note：import 失敗會被 unittest 轉成 `_FailedTest`（計數 1 且執行必紅），故本鎖
        不會把「壞檔」誤判為合規——那條路由 runner 自己的紅燈負責。
        """
        zero: list[str] = []
        for path in self._test_modules():
            # 每次新建 TestLoader：defaultTestLoader 有 `_top_level_dir` 殘留狀態
            # （run_root_unittests.discover_suite 同註解）。
            suite = unittest.TestLoader().discover(str(_TESTS_DIR), pattern=path.name)
            if suite.countTestCases() == 0:
                zero.append(path.name)
        self.assertEqual(
            zero, [],
            "下列 tools/tests/*.py 被 unittest discover 收到 0 支測試——四道閘門"
            "（pre-push root-infra leg／root-infra-ci／windows-compat-ci／macos-compat-ci）"
            f"全部跑不到它，等於這些鎖不存在（DEF-101-539）：{zero}。"
            "修法：把測試包進 unittest.TestCase 子類，勿用 pytest 模組層函式風格",
        )

    def test_no_pytest_only_test_shapes_that_unittest_silently_drops(self) -> None:
        """AST 層補 discover 抓不到的兩種形狀（見類別 docstring ②③）。"""
        module_level: list[str] = []
        plain_classes: list[str] = []
        for path in self._test_modules():
            with warnings.catch_warnings():
                # 掃描面內既有檔案的 docstring 帶非法轉義序列（實測
                # `test_extras_quoting_zsh_safety.py` 第 1~2 行的 `\`` / `\S` / `\s`），
                # `ast.parse` 會對**被掃描的**原始碼發 Deprecation/SyntaxWarning，混進
                # runner 終端輸出成噪音——那不是本鎖要抓的東西（該類別屬 ruff W605 領域），
                # 且會混淆複審者對「本次是否真有失敗」的判讀（同 run_root_unittests.py
                # `_write_failure_log` 的既有理由）。只在解析期間靜音，不改判任何斷言。
                warnings.simplefilter("ignore")
                tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and \
                        node.name.startswith("test"):
                    module_level.append(f"{path.name}::{node.name}")
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                has_testcase_base = any(
                    "TestCase" in ast.unparse(base) for base in node.bases
                )
                has_test_methods = any(
                    isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and m.name.startswith("test")
                    for m in node.body
                )
                if has_test_methods and not has_testcase_base:
                    plain_classes.append(f"{path.name}::{node.name}")
        self.assertEqual(
            module_level, [],
            "下列 test_ 函式寫在模組層（pytest 風格）——unittest discover 一支都不收，"
            f"pytest 卻會收，形成「本機 pytest 綠、四道閘門完全跑不到」（DEF-101-539）：{module_level}",
        )
        self.assertEqual(
            plain_classes, [],
            "下列類別帶 test_ 方法但未繼承 unittest.TestCase——unittest discover 不收，"
            f"pytest 會收（同 DEF-101-539 家族的第三種形狀）：{plain_classes}",
        )


if __name__ == "__main__":
    unittest.main()
