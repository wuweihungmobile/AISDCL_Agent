#!/usr/bin/env python3
"""🔴 R82／Q4-02：治理活文件裡的**否定存在宣稱**必須能被證偽。

立案（R82 掃描，量測值不是引用）
-------------------------------
Q4 那一輪重跑歸因後最大的一桶是「**宣稱先於查證**」，而 repo 現有的三面 CLAIM-FIRST
判準（幽靈路徑／幽靈符號／機械物實質）**全部只判正向存在**——文件說某個檔／符號／機械物
在，就去驗它真的在。反向那一半（「尚未落地」「零交付」「沒有任何一行」）全庫零判準。

它放過的第一個真實案例就寫在同一輪的交棒書裡：`docs/04_planning/R81_HANDOFF.md` §3.2
斷言那道降級閂鎖還沒有被寫出來，而它在**同一個 commit**（`692753e`）裡就已經落地。
那句話同時逃過兩道既有的鎖——幽靈路徑鎖只判路徑存在，交棒宣稱鎖那一輪對整份 R81
交棒書收到 **0 筆**條目（散文體例不進它的分母，屬 Q4-01，另一包在修）。

🔴 **為什麼觀測者平面是靜態面**：CLAIM-FIRST 這一桶的多數形態（rc 讀數、inline 指令
字串、對話裡的口頭宣稱）**永遠不會變成 repo 裡的檔案**，任何靜態掃描器結構上都看不到
它們——那一半留給 `tools/probe/audit_session.py` 當事後量測器（依其自述不得接閘門）。
但「否定存在宣稱」被**寫進了交棒書 `.md`**，是這一桶裡少數靜態面看得到的一角，所以
第一個機械物挑它。

判準的形狀（兩件事各自獨立，缺一都會讓它變成裝飾）
--------------------------------------------------
① **必須帶一個機讀的證偽標的**：`<!-- absent-if: <pattern> -->`。
   🔴 「附了現查指令」**不算數**——§3.2 就是附了一條 `Select-String` 卻仍為假：它 grep
   的是 ADR，而 ADR 只證明「設計存在」，不證明「實作不存在」。錨與宣稱不同軸的指令
   永遠打不臉，而它在版面上與一條真的現查指令長得一模一樣。
② **真的去搜**：`absent-if:` 的 pattern 一旦在任何 tracked 檔裡搜得到，該宣稱即為假 ⇒ 紅，
   並印出打臉的「檔案:行」。搜的是 `tools/lib/git_paths.py`（帶 `-c core.quotepath=false`
   ／`-z` 的取數層 SSOT）列出來的 tracked 檔，不是自己再走一次 `os.walk`。

逃生口與它的天花板
------------------
有些事真的沒有機械管道（例：「四方複審有沒有跑過」不落磁碟）。那些沿用 repo 既有的
`<!-- handoff-claim-verified: WHY -->`（WHY 必填），**但它有 shrink-only 天花板**：
逃生口一旦沒有上限，它就會變成預設關法，而那與沒有判準等價。

活躍面／存量面
--------------
硬判準只作用在**最新一份**交棒書（＝下一輪真的會照著做的那一份）；更舊的幾份走
shrink-only 存量棘輪（未帶標記的宣稱數只准往下）。理由與根 CLAUDE.md 行尾那一列同構：
把整片存量一次判紅，得到的是幾十筆要逐一辯護的假紅，而那種鎖活不過一輪。

🔴 為何新增一支檔而不是併進 `test_doc_loc_baseline_freshness_r60.py`
-------------------------------------------------------------------
那支檔本輪由**另一包**在改（Q4-01 正是改它的 `_handoff_claim_blocks()`），兩包同時動
同一支檔會互踩成假紅。代價明說：`tools/tests/test_adr_xplat001_c1c2_lock.py` 的
`_FROZEN_GUARD_LINES` 逐檔行數棘輪會因此暫時紅，重釘由收尾包在所有包停工後做一次
——**不在本包射程內**，已列入交件回報。這是已知且已回報的狀態，不是漏看。
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))

from lib import git_paths  # noqa: E402  # 路徑列舉的取數層 SSOT（quotepath 安全）

#: 掃描面：交棒書家族。這是「下一輪照著做」的那一份文件，也是 L4-01 發生的地方。
_HANDOFF_GLOB = "docs/04_planning/R*_HANDOFF.md"

#: 否定存在詞表。刻意只收**斷言某物不存在**的說法；「未達成」「還在 warn 線」這類
#: 講程度／狀態的不在內——它們沒有一個可以被 grep 打臉的標的。
_NEGATIVE_VOCAB: tuple[str, ...] = (
    "尚未落地", "未落地", "尚未執行", "尚未建立", "零交付", "零實作",
    "零覆蓋", "零消費者", "零載體", "沒有任何一行", "一行都沒有", "一次都沒跑",
)

_ABSENT_RE = re.compile(r"<!--\s*absent-if:\s*(?P<pattern>[^>]+?)\s*-->")
_ESCAPE_MARK = "handoff-claim-verified:"

#: 存量棘輪：舊交棒書裡**未帶任何標記**的否定宣稱數，只准往下。
#: 取值＝納管當下的實測（`python tools/tests/test_negative_existence_claims_r82.py
#: --print-baseline`），零餘裕是刻意的——留餘裕就是日後無聲加回去的破口。
_LEGACY_UNMARKED_CEILING = 14

#: 逃生口天花板（同上，只准往下）。逃生口沒有上限就會變成預設關法。
#: 納管當下＝8（R74/R77/R79/R80 各既有一筆＋R81 §3.2／§3.4 本輪各補一筆，其餘在證據檔）。
_ESCAPE_CEILING = 8


def newest_handoff(names: object) -> str:
    """交棒書家族裡輪號最大的那一份（`""`＝一份都沒有）。純函式。

    🔴 刻意**不寫死 R81**：寫死的那一刻，下一輪新開一份交棒書就自動不受本判準管轄，
    而「最新那一份」正是唯一真的會被照著做的那一份。
    """
    best, best_round = "", -1
    for rel in names:
        match = re.search(r"R(\d+)_HANDOFF\.md$", str(rel).replace("\\", "/"))
        if match and int(match.group(1)) > best_round:
            best, best_round = str(rel).replace("\\", "/"), int(match.group(1))
    return best


def _blocks(text: str) -> list[tuple[int, list[str]]]:
    """把 markdown 切成「標題 → 到下一個標題為止」的區塊；回 `(起始行號, 行)`。

    宣稱寫在標題上、標記寫在下面兩行，是這類文件最常見的排版 ⇒ 判準必須以區塊為單位，
    否則「標記就在下一行」會被判成沒帶標記（那是假紅，而假紅會讓判準被關掉）。
    """
    out: list[tuple[int, list[str]]] = []
    current: list[str] = []
    start = 1
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.startswith("#"):
            if current:
                out.append((start, current))
            current, start = [line], lineno
        else:
            current.append(line)
    if current:
        out.append((start, current))
    return out


def negative_claims(rel: str, text: str) -> list[dict]:
    """該檔裡每一筆否定存在宣稱：`{rel, line, word, patterns, escaped}`。純函式。"""
    found: list[dict] = []
    for start, block in _blocks(text):
        body = "\n".join(block)
        patterns = [m.group("pattern") for m in _ABSENT_RE.finditer(body)]
        escaped = _ESCAPE_MARK in body
        for offset, line in enumerate(block):
            if _ABSENT_RE.search(line) or _ESCAPE_MARK in line:
                continue  # 標記自己不算宣稱，否則寫標記就會製造下一筆宣稱
            for word in _NEGATIVE_VOCAB:
                if word in line:
                    found.append({"rel": rel, "line": start + offset, "word": word,
                                  "patterns": patterns, "escaped": escaped})
                    break
    return found


def unmarked(claims: object) -> list[dict]:
    """既沒有 `absent-if:` 也沒有逃生口的那些（＝今天無從證偽的宣稱）。"""
    return [c for c in claims if not c["patterns"] and not c["escaped"]]


def falsified(claims: object, hits: object) -> list[str]:
    """`absent-if:` 的 pattern 真的被搜到了 ⇒ 該宣稱為假。`hits`＝`{pattern: [檔案:行]}`。

    🔴 **標記行自己不算命中**（落地當回合實測到的第一個假紅）：`<!-- absent-if: X -->`
    這一行本身就含有 `X`，於是每一筆帶標記的宣稱都會被自己打臉 ⇒ 判準恆紅。恆紅與恆綠
    同樣沒有鑑別力，而恆紅的下場是被整個關掉。過濾的是**宣告**，不是證據。
    """
    problems: list[str] = []
    for claim in claims:
        for pattern in claim["patterns"]:
            where = [w for w in (hits.get(pattern) or []) if "absent-if:" not in w]
            if where:
                problems.append(
                    f"[宣稱為假] {claim['rel']}:{claim['line']} 寫著「{claim['word']}」，"
                    f"但它自己登記的證偽標的 `{pattern}` 在磁碟上找得到："
                    + "、".join(where[:3]))
    return problems


def grep_tracked(pattern: str, repo_root: Path) -> list[str]:
    """在 tracked 檔裡找 `pattern`；回 `檔案:行` 清單（`git grep -n -F`）。

    走 `git grep` 而不是自己 walk：它天生只看 tracked 檔（未追蹤的暫存檔不該替一個
    宣稱背書，也不該打臉它），而 `git_paths.QUOTEPATH_OFF` 讓非 ASCII 路徑不被引號化。
    """
    proc = subprocess.run(
        git_paths.git_argv(repo_root, "grep", "-n", "-F", "--", pattern),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        check=False, timeout=180)
    if proc.returncode not in (0, 1):  # 0＝有命中、1＝沒命中，其餘＝取數管道壞了
        raise RuntimeError(f"git grep 失敗 rc={proc.returncode}：{proc.stderr[:200]}")
    return [line for line in proc.stdout.splitlines() if line.strip()]


class NegativeExistenceClaimsTest(unittest.TestCase):
    """最新一份交棒書的否定存在宣稱：每一筆都要能被證偽，且今天不得為假。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.files = {rel: (_REPO_ROOT / rel).read_text(encoding="utf-8-sig")
                     for rel in git_paths.ls_files(_REPO_ROOT, _HANDOFF_GLOB)}
        cls.newest = newest_handoff(cls.files)

    def test_the_scan_surface_is_not_empty(self) -> None:
        """分母自檢：掃描面空掉時本組會**恆綠**，那與沒有判準等價（本 repo 判例）。"""
        self.assertTrue(self.files, f"`{_HANDOFF_GLOB}` 一份都沒列到 ⇒ 取數管道壞了")
        self.assertTrue(self.newest, "認不出最新一份交棒書 ⇒ 硬判準沒有作用對象")

    def test_every_negative_claim_in_the_newest_handoff_is_falsifiable(self) -> None:
        claims = negative_claims(self.newest, self.files[self.newest])
        bad = unmarked(claims)
        self.assertEqual(
            [f"{c['rel']}:{c['line']}「{c['word']}」" for c in bad], [],
            "最新一份交棒書裡有『某物不存在』的宣稱，卻沒有任何機讀的證偽標的。"
            "附一條現查指令**不算數**——R81 §3.2 就是附了指令而錨與宣稱不同軸，"
            "於是永遠打不臉。加 `<!-- absent-if: <pattern> -->`，"
            f"真的沒有機械管道才用 `<!-- {_ESCAPE_MARK} WHY -->`。")

    def test_no_negative_claim_is_contradicted_by_the_disk(self) -> None:
        claims = negative_claims(self.newest, self.files[self.newest])
        patterns = {p for c in claims for p in c["patterns"]}
        hits = {p: grep_tracked(p, _REPO_ROOT) for p in patterns}
        self.assertEqual(falsified(claims, hits), [])

    def test_the_legacy_stock_only_shrinks(self) -> None:
        """舊交棒書走存量棘輪：未帶標記的宣稱數只准往下（雙邊帶）。"""
        total = sum(len(unmarked(negative_claims(rel, text)))
                    for rel, text in self.files.items() if rel != self.newest)
        self.assertLessEqual(
            total, _LEGACY_UNMARKED_CEILING,
            "舊交棒書新增了無從證偽的否定宣稱——存量棘輪只准往下")
        self.assertGreaterEqual(
            total, 0, "計數為負＝判準壞了")
        if total < _LEGACY_UNMARKED_CEILING:
            self.fail(f"存量已降到 {total}（棘輪還寫著 {_LEGACY_UNMARKED_CEILING}）⇒ "
                      "合法縮小後必須同步下修，否則那段餘裕就是日後無聲加回去的破口")

    def test_the_escape_hatch_has_a_ceiling(self) -> None:
        """逃生口沒有上限就會變成預設關法——那與沒有判準等價。"""
        used = sum(text.count(_ESCAPE_MARK) for text in self.files.values())
        self.assertLessEqual(used, _ESCAPE_CEILING,
                             f"`{_ESCAPE_MARK}` 用了 {used} 次，超過 shrink-only 天花板")


class TheRuleHasTeethTest(unittest.TestCase):
    """合成注入：三個方向各自驗一次紅。少了這一組，上面全綠只證明「今天沒有」。"""

    _CLAIM = "### 3.9 那個閂鎖\n\n本輪 `note_degraded` **尚未落地**。\n"

    def test_an_unmarked_claim_is_caught(self) -> None:
        bad = unmarked(negative_claims("X_HANDOFF.md", self._CLAIM))
        self.assertEqual(len(bad), 1, "沒帶任何標記的否定宣稱竟然放行 ⇒ 判準沒有牙齒")
        self.assertEqual(bad[0]["word"], "尚未落地")

    #: 合成注入的證據字面。刻意是一個**不存在於任何 production 程式碼**的 token——
    #: 它只會出現在本檔與本測當場建出來的臨時 repo 裡。
    _SYNTHETIC = "ZZZ_SYNTHETIC_EVIDENCE_R82"

    @staticmethod
    def _git(root: Path, *args: str) -> None:
        """臨時 repo 的 git 動作；`-c` 關掉會讓 init 依賴使用者全域設定的東西。"""
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            check=False, timeout=120)
        if proc.returncode != 0:  # 取數管道壞掉要 fail-loud，不可默默跳過
            raise RuntimeError(f"git {args} rc={proc.returncode}：{proc.stderr[:200]}")

    def test_a_marked_claim_that_the_disk_contradicts_is_caught(self) -> None:
        """🔴 這一顆牙就是當場擋下 R81 §3.2 的那一顆。

        🔴 **自證的語料不得取自 production 符號**（R82 收尾實測到的第二個真實案例）：
        本測原本拿 `def note_degraded` 當「磁碟上一定找得到」的錨，而同一輪另一包把該符號
        整段搬進 `tools/lib/quota_gate.py`（新檔、當時 untracked）⇒ `git grep` 對它回空。
        它當時之所以還綠，靠的是 R81 交棒書自己那兩行 `Select-String` **指令文字**碰巧含有
        同一個字面——自證量到的是文件的迴音，不是實作。錨一搬家，這一顆牙就會因為與它所判
        的主題**毫無關係**的理由翻紅，而下一個人最省力的修法是把語料改回去（＝把判準調成
        配合現況，本 repo 判過那等於關掉它）。

        ⇒ 改成在**臨時 git repo 內就地構造**證據：零 production 符號、零 tracked 狀態依賴，
        repo 內任何搬家都動不到它。體例沿用根 CLAUDE.md 記載的
        `TestGitPathEnumerationIsQuotepathSafe`（同樣在臨時 repo 內明文構造對照組）。
        """
        text = self._CLAIM + f"\n<!-- absent-if: {self._SYNTHETIC} -->\n"
        claims = negative_claims("X_HANDOFF.md", text)
        self.assertEqual(unmarked(claims), [], "帶了標記卻仍被判成無從證偽")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._git(root, "init", "-q")
            (root / "evidence.py").write_text(
                f"{self._SYNTHETIC} = 1\n", encoding="utf-8", newline="\n")
            self._git(root, "add", "evidence.py")
            real = grep_tracked(self._SYNTHETIC, root)
        self.assertTrue(
            real, "取數管道自檢：剛 `git add` 進去的 tracked 檔竟然搜不到 ⇒ "
                  "`grep_tracked()` 壞了（這一條與被判的主題無關，是管道自身的體檢）")
        problems = falsified(claims, {self._SYNTHETIC: real})
        self.assertTrue(problems, "宣稱與磁碟相反竟然放行 ⇒ 本判準是裝飾")
        self.assertIn("宣稱為假", problems[0])

    def test_the_declaration_line_never_falsifies_itself(self) -> None:
        """🔴 `<!-- absent-if: X -->` 這一行自己就含有 `X` ⇒ 不過濾的話判準恆紅。

        恆紅與恆綠一樣沒有鑑別力，而恆紅的下場是被整個關掉——所以這一格要單獨釘住。
        反向：真正的證據（非標記行）仍必須打得臉，那由上一條守。
        """
        text = self._CLAIM + "\n<!-- absent-if: ZZZ_ONLY_HERE -->\n"
        claims = negative_claims("X_HANDOFF.md", text)
        self_hit = ["docs/x.md:9:<!-- absent-if: ZZZ_ONLY_HERE -->"]
        self.assertEqual(falsified(claims, {"ZZZ_ONLY_HERE": self_hit}), [])
        real = ["tools/x.py:3:ZZZ_ONLY_HERE = 1"]
        self.assertTrue(falsified(claims, {"ZZZ_ONLY_HERE": self_hit + real}),
                        "混了一筆宣告進去就把真證據一起吃掉 ⇒ 過濾過頭＝判準失明")

    #: 對照組的證偽標的：一個**刻意不會被寫進臨時 repo** 的字面（見下方 docstring）。
    _ABSENT = "ZZZ_ABSENT_CONTROL_R82"

    def test_a_true_claim_stays_green(self) -> None:
        """對照組：真的不存在時必須放行，否則本判準只是「一律判紅」（同樣沒有鑑別力）。

        🔴 **對照組不能拿本 repo 當「不存在」的舞台**（R82 收尾實測，本測第一版就踩到）：
        原版把 `def note_degraded_NOT_REAL` 當成連續字面寫進斷言，而本檔自己是 tracked
        檔 ⇒ `git grep` 在**本檔原始碼內**命中 3 筆（全部來自這一條測試自己的三行），
        於是「這個字面真的不存在」這個前提在本 repo 內**結構上永遠成立不了**，對照組恆紅。
        自我指涉的失效方向特別難看見：紅的理由與它所判的主題毫無關係，而最省力的修法
        （把斷言刪掉）會順手拿掉這一組唯一的**綠側**自證——只剩紅側的判準無法區分
        「有鑑別力」與「一律判紅」。
        ⇒ 改成在臨時 repo 內就地構造「不存在」，形狀照抄同檔
        `test_a_marked_claim_that_the_disk_contradicts_is_caught`：標的存不存在由本測
        自己決定，repo 裡有沒有人寫過那個字面一律影響不到它。
        """
        text = self._CLAIM + f"\n<!-- absent-if: {self._ABSENT} -->\n"
        claims = negative_claims("X_HANDOFF.md", text)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._git(root, "init", "-q")
            (root / "evidence.py").write_text(
                f"{self._SYNTHETIC} = 1\n", encoding="utf-8", newline="\n")
            self._git(root, "add", "evidence.py")
            # 🔴 管道自檢必須與對照組**同一次**呼叫同一個 repo：空集合是「真的不存在」
            # 還是「grep 壞了／掃描面塌了」，兩者的回傳值與 rc 完全相同。先證明它搜得到
            # 東西，那個空集合才有意義。
            self.assertTrue(
                grep_tracked(self._SYNTHETIC, root),
                "臨時 repo 內剛 `git add` 進去的字面竟然搜不到 ⇒ 取數管道壞了")
            absent = grep_tracked(self._ABSENT, root)
        self.assertEqual(absent, [], "臨時 repo 內從未寫入的字面竟然搜得到")
        self.assertEqual(falsified(claims, {self._ABSENT: absent}), [],
                         "證偽標的真的不存在時竟然判紅 ⇒ 本判準只是「一律判紅」")

    def test_the_escape_hatch_really_exempts_and_the_marker_is_not_a_claim(self) -> None:
        text = "### 3.9 複審\n\n本輪四方複審**零交付**。\n<!-- handoff-claim-verified: 派工不落 rc -->\n"
        claims = negative_claims("X_HANDOFF.md", text)
        self.assertEqual(unmarked(claims), [])
        self.assertEqual(len(claims), 1,
                         "標記自己被算成一筆新宣稱 ⇒ 寫標記會製造下一筆待辦，判準無法收斂")

    def test_a_marker_two_lines_below_the_heading_still_counts(self) -> None:
        """區塊語意：宣稱在標題、標記在下面兩行，是這類文件最常見的排版。"""
        text = "### 3.9 那個載體本輪**零交付**\n\n說明文字。\n<!-- absent-if: ZZZ_NOT_REAL -->\n"
        self.assertEqual(unmarked(negative_claims("X_HANDOFF.md", text)), [])

    def test_the_newest_handoff_is_picked_by_round_number_not_sort_order(self) -> None:
        """`R9` vs `R81` 的字典序會選錯——而選錯的方向是「硬判準去管一份沒人看的舊檔」。"""
        self.assertEqual(newest_handoff([
            "docs/04_planning/R9_HANDOFF.md",
            "docs/04_planning/R81_HANDOFF.md",
            "docs/04_planning/R80_HANDOFF.md"]), "docs/04_planning/R81_HANDOFF.md")
        self.assertEqual(newest_handoff(["docs/04_planning/NOT_A_HANDOFF.md"]), "")


if __name__ == "__main__":
    # 🔴 `--print-baseline` 印中文（`# 最新交棒書 = …`／`未帶標記 …`），而非 UTF-8 locale
    # 下 stdout 直接 UnicodeEncodeError（DEF-101-789 同型；本檔正是被
    # `test_subprocess_encoding_hygiene.py::TestEntryPointStdioProtection` 抓到）。
    # 保護只掛在 `__main__`：本檔由 unittest／pytest 以模組 import，import 期換串流會
    # 污染載具。走 SSOT 而非就地 reconfigure（理由見 `tools/lib/platform_utils.py`
    # 檔頭），並沿用本檔既有的 `from lib import …` namespace-package 形態。
    from lib.platform_utils import init_utf8_streams

    init_utf8_streams()
    if "--print-baseline" in sys.argv:
        files = {rel: (_REPO_ROOT / rel).read_text(encoding="utf-8-sig")
                 for rel in git_paths.ls_files(_REPO_ROOT, _HANDOFF_GLOB)}
        latest = newest_handoff(files)
        legacy = sum(len(unmarked(negative_claims(rel, text)))
                     for rel, text in files.items() if rel != latest)
        print(f"# 最新交棒書 = {latest}")
        for rel, text in sorted(files.items()):
            marks = len(unmarked(negative_claims(rel, text)))
            print(f"#   {rel}: 未帶標記 {marks}")
        print(f"_LEGACY_UNMARKED_CEILING = {legacy}")
        print("_ESCAPE_CEILING = "
              + str(sum(t.count(_ESCAPE_MARK) for t in files.values())))
        sys.exit(0)
    unittest.main()
