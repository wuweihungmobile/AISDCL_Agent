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
from typing import NamedTuple

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


# ── `(expected …)` 能力列的**兩側靜態**抽取（R72，原 darwin-only 鎖搬家至此）──────
#
# 搬家理由：原鎖 `test_dev_start.py::TestMacNightlyPlistCapabilityTable::
# test_capability_row_count_reaches_windows_side_parity` 是「mac 列數 ≥ Windows 列數」
# 的**跨平台對稱**斷言，卻繼承了類別層的 `@skipUnless(sys.platform == "darwin")`
# ⇒ Windows／Linux 上一律 SKIPPED，三道非 mac 閘門全部看不到它。而兩側取值方式本來
# 就不對稱：Windows 側是純讀檔 regex（不需平台），mac 側走 `--status` 真跑 bash
# （需 Darwin）。可是 mac 那幾列在 `.sh` 裡**全是字面 echo**，靜態可列舉——也就是
# 這道對稱鎖從來不需要 Darwin，只是搭錯了車。
#
# 本檔是搬家的落點而非新開檔：本檔本來就是「mac ↔ Windows 安裝器語意能力對照」的
# 靜態鎖、零平台條件、且自帶鏡子自證慣例；`DEF-101-561③` 亦禁止新增鎖檔。
#
# 行為驗證那一半**留在原處**（darwin-only）：`--status` 真的印得出能力表、每列皆 ✅、
# 且執行期列數與本檔靜態抽取的預測相等——那一條才是本抽取器的現實對帳單。
class CapabilityRow(NamedTuple):
    """一列「執行期會印出 `(expected …)`」的能力列（靜態預測，未執行任何腳本）。"""

    kind: str      # "_cap_line"（helper 呼叫）／"echo"（直接輸出）／"case-group"
    lineno: int    # 1-based
    label: str     # 該列的原始碼片段（供鏡子自證與失敗訊息定位）
    branches: int  # 互斥分支數；非 case 群恆為 1


_EXPECTED_TOKEN = "(expected "
# mac 側 helper：`_cap_line "名稱" "實際" "期望"` 每呼叫一次印一列。
_MAC_HELPER_NAME = "_cap_line"
_MAC_HELPER_DEF_RE = re.compile(rf"^{_MAC_HELPER_NAME}\(\)\s*\{{")
_MAC_HELPER_CALL_RE = re.compile(rf"^\s*{_MAC_HELPER_NAME}\s")
# `case … in` / `esac`：同一個 case 區塊內的分支**執行期只會走一條**，故整群算一列。
_SH_CASE_OPEN_RE = re.compile(r"^\s*case\s+.*\sin\s*$")
_SH_CASE_CLOSE_RE = re.compile(r"^\s*esac\b")


def mac_capability_rows(src: str) -> list[CapabilityRow]:
    """靜態列舉 `install_mac_nightly.sh --status` 執行期會印出的 `(expected …)` 列。

    三個非做不可的排除／歸併（漏任何一個，數字都會假）：
      ① **排除 helper 定義本體**：`_cap_line()` 內有兩行模板 echo（✅／⚠️ 各一），
         它們是**印出來的樣板**不是能力列；照數會憑空 +2。
      ② **排除註解行**：本檔頭與 `report_plist_capabilities` 的說明文字都逐字寫著
         `(expected 期望值)`／`(expected X)`；照數會憑空 +3。
      ③ **`case` 互斥分支歸併**：`case "${_last_exit}" in` 的三個分支各有一行
         `(expected 0)`，執行期只會印**其中一行**；照數會憑空 +2。
    """
    emitters: list[tuple[str, int, str]] = []   # (kind, lineno, 原始碼片段)
    case_of: dict[int, int] = {}                # emitter 行號 -> 所屬 case 區塊起始行號
    in_helper_def = False
    helper_def_seen = False
    case_stack: list[int] = []
    for lineno, line in enumerate(src.splitlines(), start=1):
        stripped = line.strip()
        if _MAC_HELPER_DEF_RE.match(line):
            in_helper_def, helper_def_seen = True, True
            continue
        if in_helper_def:
            if line.rstrip() == "}":      # ① helper 本體結束（收在第 0 欄）
                in_helper_def = False
            continue
        if stripped.startswith("#"):      # ②
            continue
        if _SH_CASE_OPEN_RE.match(line):
            case_stack.append(lineno)
            continue
        if _SH_CASE_CLOSE_RE.match(line) and case_stack:
            case_stack.pop()
            continue
        is_helper_call = bool(_MAC_HELPER_CALL_RE.match(line))
        if not is_helper_call and _EXPECTED_TOKEN not in line:
            continue
        emitters.append(("_cap_line" if is_helper_call else "echo", lineno, stripped))
        if case_stack:
            case_of[lineno] = case_stack[-1]
    assert helper_def_seen, (
        f"install_mac_nightly.sh 找不到 `{_MAC_HELPER_NAME}() {{` 定義——腳本結構已變動，"
        "本抽取器的排除①失效（模板 echo 會被誤計成能力列），須同步更新"
    )
    rows: list[CapabilityRow] = []
    seen_groups: set[int] = set()
    for kind, lineno, snippet in emitters:
        group = case_of.get(lineno)
        if group is None:
            rows.append(CapabilityRow(kind, lineno, snippet, 1))
            continue
        if group in seen_groups:          # ③ 同一 case 群的其餘分支併入首列
            continue
        seen_groups.add(group)
        rows.append(CapabilityRow(
            "case-group", group, snippet,
            sum(1 for g in case_of.values() if g == group),
        ))
    assert rows, "install_mac_nightly.sh 一列 (expected …) 能力列都抽不到——結構已變動"
    return rows


# 🔴 R72 主控裁決：判準由 R67-M37 原鎖的 `\(expected \w+\)` **改寬**為 `[^)]+`。
#
# WHY：`\w+` 數的是**格式**不是**概念**——它只因為 `(expected S4U — Interactive 在使用者
# 未登入時整輪不跑)` 帶了破折號長句就漏掉那一列，於是 Windows 真實 7 項能力被算成 6。
# 後果是雙向的：① mac 側少一列 LogonType 對等物卻仍「對稱」通過；② 哪天有人把該列
# 改寫成 `(expected S4U)`，win 會無聲從 6 跳到 7 而語意根本沒變、mac 當場破閘。
# 這正是本 repo 反覆在治的「鎖住格式而非語意」形態。
#
# 改寬的安全性已實測（`probe_wide_regex.py`）：`install_windows_nightly.ps1` 全檔 7 處
# 命中**全部是 `Write-Output` 輸出行**（:124/:125/:126/:127/:132/:133/:135），零註解、
# 零散文誤收。配套 mac 側已補 LogonType 對等列（帶 `(expected 無對應鍵)`）⇒ 兩側皆 7。
_WIN_EXPECTED_ROW_RE = re.compile(r"\(expected [^)]+\)")


def win_capability_rows(src: str) -> list[CapabilityRow]:
    """靜態列舉 `install_windows_nightly.ps1 -Status` 的 `(expected X)` 能力列。

    Windows 側全是無分支的 `Write-Output` 直列，故只需排除註解行（`#` 開頭）——
    與 mac 側同一條排除紀律，不因為「目前剛好沒有註解命中」就省略：省略等於把
    正確性寄託在一個隨時會變的巧合上。
    """
    rows = [
        CapabilityRow("echo", lineno, line.strip(), 1)
        for lineno, line in enumerate(src.splitlines(), start=1)
        if not line.strip().startswith("#") and _WIN_EXPECTED_ROW_RE.search(line)
    ]
    assert rows, "install_windows_nightly.ps1 一列 (expected X) 都抽不到——結構已變動"
    return rows


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

    # ── `(expected …)` 能力列對稱（R72 由 test_dev_start.py 搬入，見上方區塊註解）──

    def test_mac_capability_rows_extracted_sane(self) -> None:
        """鏡子自證：靜態抽取器看得懂 `install_mac_nightly.sh` 現行的形狀。

        沒有這一支，抽取器抽錯時只會**默默少算**（例如 helper 改名 ⇒ 一列都抽不到、
        或 case 歸併失效 ⇒ 憑空多兩列），而對稱斷言 `mac ≥ win` 在多算的方向上照樣
        全綠——鎖住的就只是抽取器自己的誤差（同本檔既有兩支 `_extracted_sane` 的理由）。
        """
        rows = mac_capability_rows(_mac_source())
        labels = " | ".join(r.label for r in rows)
        for expected in ("RunAtLoad", "StartCalendarInterval", "ProgramArguments 載體可讀",
                         "StandardOutPath", "StandardErrorPath"):
            self.assertIn(
                expected, labels,
                f"mac 能力列抽取遺漏 {expected!r}——抽取器可能已與腳本結構脫節；抽到的是：{labels}",
            )
        groups = [r for r in rows if r.kind == "case-group"]
        self.assertEqual(
            len(groups), 1,
            f"預期恰有 1 個 case 互斥群（`case \"${{_last_exit}}\" in` 的上次退出碼列），"
            f"實得 {len(groups)}：{groups}。若安裝器新增/移除了 case 分支能力列，"
            "請同步更新本鏡子測試",
        )
        self.assertEqual(
            groups[0].branches, 3,
            f"上次退出碼 case 群應有 3 個互斥分支（0／空或 -／其他），實得 "
            f"{groups[0].branches}——歸併失效會讓 mac 側列數憑空膨脹",
        )
        # 排除①②的反向證明：模板 echo 與註解一列都不得混進來。
        for row in rows:
            self.assertNotIn(
                "$1 = $2", row.label,
                f"`_cap_line()` 定義內的模板 echo 被誤計成能力列（排除①失效）：{row}",
            )
            self.assertFalse(
                row.label.startswith("#"),
                f"註解行被誤計成能力列（排除②失效）：{row}",
            )

    def test_mac_extractor_excludes_template_comment_and_case_noise(self) -> None:
        """鏡子自證（合成對照）：對一份**刻意塞滿三種雜訊**的最小 shell 原始碼，
        抽取器必須只回報真正的 2 列（1 個 helper 呼叫 ＋ 1 個 case 群）。

        WHY 要合成而不只驗真檔：真檔目前恰好只有一種雜訊組合，若哪天雜訊消失，
        上一支測試的三條排除斷言就全部退化成恆真（沒有反例可證偽）。本支把三種
        排除各自的鑑別力**永久釘住**，與真檔內容無關。
        """
        synthetic = (
            "#!/usr/bin/env bash\n"
            '# 說明文字：逐項印 "實際值 (expected 期望值)"    <- 註解，不得計入\n'
            "_cap_line() {\n"
            '  echo "  ✅ $1 = $2   (expected $3)"           # <- 模板，不得計入\n'
            '  echo "  ⚠️ $1 = $2   (expected $3)"           # <- 模板，不得計入\n'
            "}\n"
            "report() {\n"
            '  _cap_line "RealRow" "$(x)" "true"\n'
            '  case "${v}" in\n'
            '    0) echo "  ✅ a = 0   (expected 0)" ;;\n'
            '    1) echo "  ⚠️ a = 1   (expected 0)" ;;\n'
            "  esac\n"
            "}\n"
        )
        rows = mac_capability_rows(synthetic)
        self.assertEqual(
            [(r.kind, r.branches) for r in rows], [("_cap_line", 1), ("case-group", 2)],
            f"三種雜訊（註解／helper 模板／case 互斥分支）未被正確處理，抽到：{rows}",
        )

    def test_win_capability_rows_extracted_sane(self) -> None:
        """鏡子自證：Windows 側抽取器看得懂 `Show-TaskDetail` 現行的形狀。"""
        labels = " | ".join(r.label for r in win_capability_rows(_win_source()))
        for expected in ("StartWhenAvailable", "WakeToRun", "DisallowStartIfOnBatteries",
                         "StopIfGoingOnBatteries", "ExecutionTimeLimit",
                         "MultipleInstancesPolicy"):
            self.assertIn(
                expected, labels,
                f"windows 能力列抽取遺漏 {expected!r}——抽取器可能已與腳本結構脫節；"
                f"抽到的是：{labels}",
            )

    def test_capability_row_count_reaches_windows_side_parity(self) -> None:
        """跨平台對稱鎖：mac 能力表的 `(expected …)` 列數 ≥ Windows 側的列數。

        R72：由 `test_dev_start.py::TestMacNightlyPlistCapabilityTable` 搬入，並把
        mac 側由「真跑 `--status` 數輸出行」換成「靜態列舉原始碼」——原鎖繼承了
        `@skipUnless(sys.platform == "darwin")`，這道**跨平台**斷言於是只在 mac
        閘門上跑得到；而它從來不需要 Darwin，mac 那幾列在 `.sh` 裡全是字面 echo。
        斷言主體與訊息刻意沿用原文（形態才是缺陷，內容不是）。

        缺陷的量化形態就是這個比值——修前 `grep -c expected` mac=1（且那 1 筆在
        註解裡）／windows=4。用「≥ Windows 實際列數」而非硬編數字，Windows 側日後
        新增保護設定時本鎖會自動要求 mac 跟上，不會靜默停在舊基準。
        """
        win_rows = win_capability_rows(_win_source())
        self.assertGreaterEqual(len(win_rows), 4, "Windows 側 (expected X) 列數抽取失準")
        mac_rows = mac_capability_rows(_mac_source())
        self.assertGreaterEqual(
            len(mac_rows), len(win_rows),
            f"mac --status 只印 {len(mac_rows)} 個 (expected …) 能力列，Windows -Status 有 "
            f"{len(win_rows)} 個——兩側 status 深度不對稱（R67-M37）。若某項 launchd 結構上"
            f"無對應鍵，仍須以「－ …對等：…無對應鍵可查」列出，讓讀者能逐列對照。"
            f"mac 側抽到：{[r.label[:40] for r in mac_rows]}",
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
