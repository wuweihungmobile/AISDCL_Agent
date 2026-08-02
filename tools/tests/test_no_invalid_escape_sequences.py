#!/usr/bin/env python3
"""非法轉義序列（`W605` / `SyntaxWarning: invalid escape sequence`）機械鎖
（R60 QA-R60-05 的結構性那一半）。

WHY（為何非得有這道鎖）：
  R60 在 `AutoClaude/tools/local_ci_gate.py`（本機 CI 閘門**唯一核心**）的 docstring
  引述 Windows 路徑時引入 `\\l`，Python 3.11 只印 DeprecationWarning、**3.12 起升為
  SyntaxWarning、CPython 已宣告未來版本改為 SyntaxError**（屆時該檔無法 import）。
  當時三道閘門全綠：AutoClaude 的 ruff `select` 不含 `W`（已於同輪補上），而**根層
  `tools/` 與 AISDLC_SDD 樹完全沒有任何 ruff 閘門**，所以這一整類在本 repo 過去只能
  靠人眼。QA-R60-05 判為 blocking 的正是這個結構面：不是那一個 `\\l`，而是
  「這一類在閘門上看不見」。
  同輪 Pkg-4 自己就對 `tools/tests/test_extras_quoting_zsh_safety.py` 的同款缺陷寫過
  「建議由該檔擁有者改成 raw string」——建議在同一輪內沒有承接者，正是「沒有機械物
  就等於沒發生」的教科書例子。

判準：對 `_SCAN_ROOTS` 下每一支 `.py` 做 `compile()`，收集 `invalid escape sequence`
  警告。命中且不在 `_KNOWN_DEBT` 名冊內 → 紅。
  （本 docstring 刻意不寫出三引號字面——寫了會提前結束自己，本檔第一版即因此
  `SyntaxError: invalid character`，屬「示範壞形態的文件會反咬自己」的同族陷阱。）

🔴 修法（**首選＝把該處反斜線改寫成 `\\\\`**，次選才是整串改 raw）：
  R60 Pkg-P3 回收存量債時實測發現「一律改 raw 前綴」這個處置**不是**零語意變更，
  原名冊三筆的 WHY 都寫錯了方向：raw 化會讓同一 docstring 內**既有的合法轉義**
  一併改變 rendered 內容——`test_ps51_compat.py` 有 8 處 `\\\\`（本意是顯示單一反斜線
  的正則，raw 後會變成顯示兩個，**文件反而變錯**）、`test_nightly_interpreter_determinism.py`
  有 2 處、`test_extras_quoting_zsh_safety.py` 甚至有一個合法的 `\\t`（rendered 是真
  TAB）。三檔實測 `ast.get_docstring()` 皆 `differs_if_made_raw=True`。
  反之「把該處反斜線加倍」對**非法**轉義是恆等變換（Python 對非法轉義原樣保留
  反斜線），R60 實測三檔 rendered docstring 的 len 與 sha256 前後完全相同——這也正是
  `ruff --select W605` 自己給的 `help: Add backslash to escape sequence` 與 `--fix` 行為。
  只有在該字串內**沒有**任何合法轉義時，raw 化才等價。

🔴 判準邊界（誠實劃界）：
  - **掃描面刻意不含 `AISDLC_SDD/AISDLC_SDD_v0.01`~`v0.29`**（29 個凍結版）：依
    Copy-on-Evolve 政策那些樹不改，掃出來只能長出 29 份永久豁免。實測（R60）：全 repo
    5,451 支 `.py` 掃完為 6.8 秒、命中仍是同樣這 3 支；縮到現行掃描面是 832 支／0.7 秒
    且**命中集合完全相同**——即縮面沒有損失鑑別力，只省時間。若哪天凍結版真的長出這
    類問題，它也不在本鎖負責的範圍（該由凍結版豁免家族處理）。
  - 只驗「非法轉義」這一類，不是完整的 ruff `W`。AutoClaude 樹另有 ruff `W`
    （`AutoClaude/pyproject.toml`，R60 補入）作為更全面的第二層；本鎖是**跨樹**那一層。
  - `compile()` 只做語法層編譯、**不執行**任何模組，無 import 副作用。

名冊紀律（防「豁免變永久」）：`_KNOWN_DEBT` 為既有存量債（皆非本輪引入），每筆須帶
  WHY；並有 stale 自檢——某筆已修好卻留在名冊 ⇒ 紅，強制回收。這是刻意避開 R60
  `_PENDING_MIGRATION_SITES` 的坑（無 stale 自檢的 pending 名單永遠不會退場）。

  🔴 **名冊現為空**（R60 Pkg-P3 全數回收，見上）。原本登記的 3 筆是「**無承接輪次的
  backlog**」——只是把待辦從缺陷帳本搬進程式碼裡的名冊，正是本輪硬規則② 要治的形態，
  而三筆的修法都只是加倍反斜線（零 rendered 變更），沒有任何延後的理由。
  名冊機制**保留**（未來仍可能有真的需要凍結的存量債），但空名冊會讓 stale／WHY 兩支
  自檢變成恆真斷言，故另立 `test_stale_detector_reports_a_synthetic_stale_entry` 與
  `test_why_detector_reports_a_synthetic_empty_why` 兩支**合成自證**，讓名冊機制在
  零條目時仍有鑑別力（同本檔既有的 `test_detector_catches_a_synthetic_offender` 慣例）。

執行：python tools/run_root_unittests.py
      python -m unittest tools.tests.test_no_invalid_escape_sequences -v
"""
from __future__ import annotations

import re
import unittest
import warnings
from collections.abc import Iterable, Mapping
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parents[1]

_SCAN_ROOTS = (
    "tools",
    "AISDLC_SDD/AISDLC_SDD_v0.30",
    "AISDLC_SDD/scripts",
    "AutoClaude/autoclaude",
    "AutoClaude/tools",
    "AutoClaude/tests",
    "AutoClaude/alembic",
)

# 既有存量債名冊（檔案級，鍵＝repo 相對 posix 路徑，值＝WHY／處置方向）。
#
# 🔴 R60 Pkg-P3：原 3 筆（test_extras_quoting_zsh_safety / test_nightly_interpreter_determinism
# / test_ps51_compat，共 7 個 W605）**已全數修畢並回收**，名冊回到空集合。
# 修法一律為「該處反斜線加倍」——三檔 rendered docstring 的 len 與 sha256 前後完全相同
# （實測；原 WHY 所寫的 `r` 前綴反而會改動 rendered 內容，見檔頭「修法」段）。
# 新增條目前先讀檔頭「名冊紀律」：名冊是**既有存量債**的凍結清單，不是新債的收容所。
_KNOWN_DEBT: dict[str, str] = {}


def scan(repo_root: Path = _REPO_ROOT) -> dict[str, list[str]]:
    """回傳 {repo 相對 posix 路徑: [警告訊息…]}（純掃描，無副作用）。"""
    found: dict[str, list[str]] = {}
    for root in _SCAN_ROOTS:
        base = repo_root / root
        if not base.is_dir():
            raise AssertionError(
                f"掃描面目錄不存在：{root}——目錄改名/搬移必須同步 _SCAN_ROOTS，"
                f"否則本鎖會靜默縮面（fail-loud）"
            )
        for path in sorted(base.rglob("*.py")):
            rel = path.relative_to(repo_root).as_posix()
            if "/.venv/" in f"/{rel}" or "/__pycache__/" in f"/{rel}":
                continue
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                try:
                    compile(
                        path.read_text(encoding="utf-8", errors="replace"),
                        rel,
                        "exec",
                    )
                except SyntaxError:
                    # 真正的語法錯誤不是本鎖的職責（其他閘門會擋），略過不誤報。
                    continue
                msgs = [
                    str(w.message)
                    for w in caught
                    if "invalid escape sequence" in str(w.message)
                ]
            if msgs:
                found[rel] = msgs
    return found


def stale_entries(registry: Mapping[str, str], current: Iterable[str]) -> list[str]:
    """名冊中已無違規的條目（＝該回收的豁免）。抽成純函式供合成自證共用。"""
    return sorted(set(registry) - set(current))


def entries_missing_why(registry: Mapping[str, str]) -> list[str]:
    """未填 WHY（或只有空白）的條目。抽成純函式供合成自證共用。"""
    return sorted(key for key, why in registry.items() if not why.strip())


def scanned_file_count(repo_root: Path = _REPO_ROOT) -> int:
    """掃描面的 `.py` 支數（供反空轉下限）。"""
    total = 0
    for root in _SCAN_ROOTS:
        for path in (repo_root / root).rglob("*.py"):
            rel = f"/{path.relative_to(repo_root).as_posix()}"
            if "/.venv/" in rel or "/__pycache__/" in rel:
                continue
            total += 1
    return total


class TestNoInvalidEscapeSequences(unittest.TestCase):
    def test_no_new_invalid_escape_sequences(self) -> None:
        """掃描面內不得有未登記的非法轉義序列。"""
        offenders = {k: v for k, v in scan().items() if k not in _KNOWN_DEBT}
        self.assertEqual(
            offenders,
            {},
            "發現未登記的非法轉義序列（Python 3.12 起為 SyntaxWarning、未來版本為 "
            "SyntaxError；屆時該檔直接無法 import）：\n"
            + "\n".join(f"  {k}: {v}" for k, v in offenders.items())
            + "\n修法（首選）：該處反斜線加倍（例 `\\\\S`）——對非法轉義是恆等變換，"
            "rendered 內容前後不變，等同 `ruff --select W605 --fix`。次選才是整串改 raw"
            "（`r` 前綴），但**只有該字串內沒有任何合法轉義時才等價**（詳見檔頭「修法」段）。"
            "\nWHY 不接受「加進 _KNOWN_DEBT」當修法：名冊是**既有存量債**的凍結清單，"
            "不是新債的收容所（R60 QA-R60-05 就是新造一筆同款缺陷）。",
        )

    def test_known_debt_entries_are_not_stale(self) -> None:
        """名冊 stale 自檢：已修好的檔必須從 `_KNOWN_DEBT` 移除（強制回收豁免）。

        WHY：R60 的 `_PENDING_MIGRATION_SITES` 就是因為沒有這一支，遷移完成後條目
        留著，讓那支檔案對它自己的鎖永久免疫。
        """
        stale = stale_entries(_KNOWN_DEBT, scan())
        self.assertEqual(
            stale,
            [],
            f"以下檔已無非法轉義序列，卻仍留在 _KNOWN_DEBT（請逕行刪除該筆）：{stale}",
        )

    def test_known_debt_entries_all_have_why(self) -> None:
        """每筆豁免必須帶 WHY（空 WHY 不具豁免力，比照 encoding-ok / baseline-ok 紀律）。"""
        empty = entries_missing_why(_KNOWN_DEBT)
        self.assertEqual(empty, [], f"以下豁免未填 WHY：{empty}")

    def test_stale_detector_reports_a_synthetic_stale_entry(self) -> None:
        """名冊機制自證（stale）：`_KNOWN_DEBT` 現為空 ⇒ 上面兩支對真名冊的斷言恆真，
        零鑑別力。故此處餵一個「名冊有、掃描面沒有」的合成條目，證明回收機制真會說話。
        """
        current = scan()
        synthetic = "tools/tests/__never_existed_synthetic__.py"
        self.assertNotIn(synthetic, current, "合成路徑不得真的存在，否則本自證無意義")
        self.assertEqual(
            stale_entries({synthetic: "合成 WHY"}, current),
            [synthetic],
            "stale 判定器對「已修好卻留在名冊」的條目必須指名，否則豁免會永久化",
        )

    def test_why_detector_reports_a_synthetic_empty_why(self) -> None:
        """名冊機制自證（WHY）：空／全空白 WHY 必須被指名，帶 WHY 的不得誤報。"""
        self.assertEqual(
            entries_missing_why({"b.py": "有理由", "a.py": "", "c.py": "   \t "}),
            ["a.py", "c.py"],
            "WHY 判定器必須擋下空白 WHY（空 WHY 不具豁免力），且不得誤報有 WHY 的條目",
        )

    def test_scan_surface_is_not_silently_empty(self) -> None:
        """反空轉：掃描面支數必須在下限之上（目錄改組時不得靜默掃 0 支）。"""
        count = scanned_file_count()
        self.assertGreaterEqual(
            count,
            600,
            f"掃描面只找到 {count} 支 .py（下限 600；R60 實測 832）——"
            f"掃描面崩塌時「零違規」是假綠，故 fail-loud",
        )

    def test_detector_catches_a_synthetic_offender(self) -> None:
        """判定器自證：合成的非法轉義來源必須被偵測到（不是恆綠）。"""
        source = 'x = "C:' + chr(92) + 'local_ci_gate.ps1"\n'
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            compile(source, "<synthetic>", "exec")
        self.assertTrue(
            any("invalid escape sequence" in str(w.message) for w in caught),
            "偵測手法（compile + warnings 捕捉）對已知壞形態必須說話，否則本鎖零鑑別力",
        )

    def test_detector_accepts_raw_string_form(self) -> None:
        """判定器自證：raw 形態（＝本輪的修法）不得被誤報。"""
        source = 'x = r"C:' + chr(92) + 'local_ci_gate.ps1"\n'
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            compile(source, "<synthetic>", "exec")
        self.assertEqual(
            [str(w.message) for w in caught if "invalid escape" in str(w.message)], []
        )


# ---- R69（DEF-101-702／R68-39）：noqa 指令本體的形態 ---------------------------------
# WHY 住在本檔：本檔守的是「ruff 看得見、但本 repo 的閘門看不見」那一類靜默自傷，noqa
# 寫壞正是同一類——規則碼後面緊接**全形**括號（`PLC0415（避免循環 import）`）時 ruff 判
# 整條指令非法（印 Invalid directive warning）⇒ 該行**完全沒有被豁免**，而 pre-commit 的
# ruff leg 只看 rc、warning 全落地無人消費，於是「以為有豁免」與「其實沒有」外觀相同。
# 這是 DEF-101-525 已記載過的同型自傷第二次復發，當輪未落任何機械鎖。
#
# 樣式的負向前瞻 `(?![0-9])` 不可省：少了它，`noqa: E501` 這種正常寫法會因為規則碼
# 本身的數字而被逐字元回溯命中，製造大量假陽性（原缺陷報告給的樣式就是那個壞版本）。
#
# 🔴 R69 終審 P1（本節第一版自己犯了它要治的病，兩層）：
#   ① 上面這幾行原本把「井號＋noqa」的組合逐字寫在**註解**裡當說明，而 ruff 解析註解時
#      不管它是不是說明——冷 cache 實測本檔逐次吐三條 `warning: Invalid ... directive`
#      （235／237／242 行）。示範壞形態的**註解**會被工具當真，這正是本檔檔頭
#      警告過的「示範壞形態的文件會反咬自己」，只是換了一個工具。
#      （本段連引述那句 warning 都不敢寫全，正是因為引述本身就會再製造一條 warning。）
#      修法：散文一律不寫出該組合（改稱「noqa 指令」），要示範就用下面的 `_HASH` 拼。
#   ② 樣本字串（`test_detector_*` 的輸入）也讓**本檔自己**被自己的掃描器命中，於是第一版
#      加了一條「整檔自我豁免」——本鎖對最該被守的那支檔（它自己）射程為零，且該豁免還
#      掩護了 ① 那個真的壞掉的指令。修法：樣本改用 `_HASH` 動態拼接，源碼任何一行都不再
#      出現可被解析的指令，整檔豁免隨之刪除（同本檔既有 `chr(92)` 合成壞形態的慣例）。
_HASH = chr(35)
_NOQA_MALFORMED_RE = re.compile(r"#\s*noqa:\s*[A-Z]+[0-9]+(?![0-9])[^\s,]")


def scan_malformed_noqa(repo_root: Path = _REPO_ROOT) -> list[str]:
    """回傳 `rel:lineno: 原行` 清單——規則碼後緊接非空白、非逗號的字元即判違規。

    🔴 **無任何豁免**（R69 終審）：本檔自己也在掃描面內。
    """
    problems: list[str] = []
    for root in _SCAN_ROOTS:
        base = repo_root / root
        for path in sorted(base.rglob("*.py")):
            rel = path.relative_to(repo_root).as_posix()
            if "/.venv/" in f"/{rel}" or "/__pycache__/" in f"/{rel}":
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for lineno, line in enumerate(text.splitlines(), 1):
                if _NOQA_MALFORMED_RE.search(line):
                    problems.append(f"{rel}:{lineno}: {line.strip()}")
    return problems


class TestNoqaDirectivesAreWellFormed(unittest.TestCase):
    """noqa 指令必須是 ruff 認得的形態，否則豁免是假的。"""

    def test_no_malformed_noqa_in_scan_surface(self) -> None:
        problems = scan_malformed_noqa()
        self.assertEqual(
            problems, [],
            "以下 noqa 指令 ruff 判為非法（規則碼後緊接非空白字元，最常見是**全形**"
            "括號）——該行實際上完全沒有被豁免：\n" + "\n".join(problems) +
            "\n修法：規則碼與理由之間留空白，理由用半形括號或移到上一行。",
        )

    def test_detector_catches_the_pre_fix_form(self) -> None:
        """鑑別力：R69 修掉的那個逐字形態必須被命中。"""
        self.assertIsNotNone(_NOQA_MALFORMED_RE.search(
            f"        from ..utils.config import X  {_HASH} noqa: PLC0415（避免循環 import）"
        ))

    def test_this_file_is_inside_its_own_scan_surface(self) -> None:
        """反自我豁免（R69 終審）：本檔必須真的被自己掃到，且掃出來是乾淨的。

        第一版有一條 `if rel == _SELF_REL: continue` 的整檔豁免，於是本檔留著一個
        **真的壞掉**的 noqa 指令（ruff 每次冷 cache 都印 warning）而本鎖全綠。
        豁免掩護的正是本鎖存在的理由，故整條拆除；本測試釘住「不得再長回來」。
        """
        self_rel = Path(__file__).resolve().relative_to(_REPO_ROOT).as_posix()
        scanned = {
            p.relative_to(_REPO_ROOT).as_posix()
            for root in _SCAN_ROOTS
            for p in (_REPO_ROOT / root).rglob("*.py")
        }
        self.assertIn(self_rel, scanned, "本檔不在自己的掃描面內——掃描面或本檔位置已改變")
        self.assertEqual(
            [p for p in scan_malformed_noqa() if p.startswith(self_rel + ":")], [],
            "本檔自己含壞形態 noqa 指令——樣本一律以 `_HASH` 動態拼接，不得逐字寫在源碼行上",
        )

    def test_detector_does_not_flag_normal_forms(self) -> None:
        """對照組：本 repo 大量使用的正常寫法不得誤報（負向前瞻若被拿掉即紅）。"""
        for sample in (
            f"import sdd_latest  {_HASH} noqa: E402",
            f"x = 1  {_HASH} noqa: E501, F401",
            f"y = 2  {_HASH} noqa: PLC0415  (避免循環 import)",
            f"z = 3  {_HASH} noqa: E402  {_HASH} 另一段註解",
        ):
            with self.subTest(sample=sample):
                self.assertIsNone(_NOQA_MALFORMED_RE.search(sample))


if __name__ == "__main__":
    unittest.main()
