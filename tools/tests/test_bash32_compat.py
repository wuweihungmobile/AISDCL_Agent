#!/usr/bin/env python3
"""bash 3.2 相容性行級機械守門（R15 DEF-101-202；DEF-101-004 家族實證）。

WHY：macOS 內建 /bin/bash 凍結於 3.2.57（2007，GPLv2 授權凍結），bash 4+ 語法
（declare -A／mapfile／${var,,}／|&…）在 `bash -n` 語法檢查下**不會**被攔——
多數以「合法指令名／執行期展開」形式存在，直到執行期才炸（DEF-101-004 家族
真機重現：CI 的 ubuntu bash 5.x 全綠、mac 執行期才紅）。另 BSD 工具紀律組
（grep -P／readlink -f／sed -i）為 GNU/BSD 選項分歧，同樣執行期才炸。
本測試以行級 regex 掃描六樹 active bash 腳本，防未來複製舊 pattern 再踩
（骨架鏡射 test_subprocess_encoding_hygiene.py：豁免行內註記＋stale 自檢＋
per-tree 下限）。

判準（行級 regex；先剝註解再掃，heuristic 邊界如下，均為刻意取捨）：
  A 執行期必炸組（bash 4+ 語法）：declare -A、mapfile、readarray、
    ${var,,}/${var^^}/${var@Q…}、|&、&>>、coproc、local -n、wait -n
  B BSD 工具紀律組（GNU-only 選項）：grep -P、readlink -f、sed -i、stat -c、
    date -d、timeout、xargs -r、find -printf
    （SA-R15-REV-4 揭露：ONBOARDING §8 靜態自查清單另列「BRE 交替」屬語意級判準
    ——grep 是否用 ERE `|` 交替需理解上下文，非行級 regex 能可靠判定，刻意不納入
    本守門、仍靠人工紀律。🔴 R69：本段原寫「本組僅機械化前 3 項」，而
    `tools/macos_smoke_local.sh` 檔頭同時逐字宣告 8 項禁令 ⇒ 5 項只活在散文裡、
    注入後全套根層測試仍 rc=0。已補齊，並由 TestProseBanListIsFullyMechanised
    把兩側雙向綁定，防再長出「列了但沒守」的差集。A 組同輪補 local -A／
    typeset -A／shopt -s globstar／declare -g 四項）
  - 註解剝除：整行 `#` 與行內 `#`（僅剝「引號外、且位於字首或空白/;&|( 之後」
    的 #——單/雙引號逐字元追蹤，字串內的 # 不誤剝；$'…'/反引號等罕見形不追，
    屬 heuristic 邊界）；
  - 字串字面值**內**的 pattern 文字仍會命中（行級 regex 無語法樹；實掃六樹
    零此類誤報，未來真誤報以行尾標記豁免或改寫字串）。

豁免機制：違規行行尾加註 `# bash4-ok: <WHY>`（WHY 必填，留空視同無豁免力）。
stale 自檢：帶標記的行掃不到任何被壓下的違規（已改寫／標記放錯行）→ fail-loud
指名該行請移除標記，防豁免清單腐化（語意對齊 encoding-ok 慣例）。

掃描樹（六樹；一律以 `git ls-files` 列舉——排除未追蹤垃圾/暫存複製品）：
根 tools/（git-hooks 另列）、根 tools/git-hooks/、AutoClaude/tools/（含其
git-hooks/）、AISDLC_SDD/scripts/、AISDLC_SDD/.githooks/、LATEST 版 tools/
（LATEST 以 scripts/sdd_version.py SSOT subprocess 解析，解析失敗 fail-loud
不得縮面；凍結版 v0.01~v0.2X 依鐵律不掃、也不可修）。檔案認定＝`*.sh`/`*.bash`
＋無副檔名且檔頭 shebang 含 bash（git hooks 慣例）。per-tree 掃描檔數下限
釘選防單樹靜默縮面（＝2026-07-20 實掃數 6/3/8/5/1/5 打八折取整、最低 1，
慣例對齊 test_subprocess_encoding_hygiene）；樹清單本體另由
TestScanConfigPinning 釘選，防「刪清單一列」整樹靜默出界。
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parents[1]

sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
import sdd_latest  # noqa: E402

_OK_MARKER = "bash4-ok:"

# （regex, 說明）；掃描對象為剝註解後的 code 段
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # ── A 執行期必炸組（bash 4+ 語法，bash -n 攔不住）──────────────────────
    (re.compile(r"\bdeclare\s+-[a-zA-Z]*A"), "declare -A 關聯陣列（bash 4.0+）"),
    (re.compile(r"\bmapfile\b"), "mapfile（bash 4.0+）"),
    (re.compile(r"\breadarray\b"), "readarray（bash 4.0+）"),
    (
        re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*(?:\[[^]]*\])?(?:,,|\^\^|@[QEPAa])"),
        "${var,,}/${var^^}/${var@Q} 參數展開運算子（bash 4.0+/4.4+）",
    ),
    (re.compile(r"\|&(?!&)"), "|& 管線縮寫（bash 4.0+；請用 2>&1 |）"),
    (re.compile(r"&>>"), "&>> 重導縮寫（bash 4.0+；請用 >> f 2>&1）"),
    (re.compile(r"\bcoproc\b"), "coproc（bash 4.0+）"),
    (re.compile(r"\blocal\s+-n\b"), "local -n nameref（bash 4.3+）"),
    (re.compile(r"\bwait\s+-n\b"), "wait -n（bash 4.3+）"),
    # R69（DEF-101-702／R68-03）：A 組原漏 `local -A`／`typeset -A`（`declare -A` 的兩個
    # 等價寫法，bash 3.2 同樣必炸）、`shopt -s globstar`（4.0+，3.2 下 `**` 靜默退化成 `*`
    # ⇒ 掃描面無聲縮小，比報錯更危險）、`declare -g`（4.2+，3.2 直接 `invalid option`）。
    (re.compile(r"\b(?:local|typeset)\s+-[a-zA-Z]*A\b"),
     "local -A / typeset -A 關聯陣列（bash 4.0+；同 declare -A）"),
    (re.compile(r"\bshopt\s+-s\s+globstar\b"),
     "shopt -s globstar（bash 4.0+；3.2 下 ** 靜默退化為 *，掃描面無聲縮小）"),
    (re.compile(r"\bdeclare\s+-[a-zA-Z]*g\b"), "declare -g（bash 4.2+）"),
    # ── B BSD 工具紀律組（GNU-only 選項，macOS BSD 工具不支援）──────────────
    (re.compile(r"\bgrep\s+-[a-zA-Z]*P\b"), "grep -P（BSD grep 無 PCRE；請改 -E）"),
    (re.compile(r"\breadlink\s+-f\b"), "readlink -f（BSD readlink 不支援；請用 cd+pwd -P）"),
    (re.compile(r"\bsed\s+-i\b"), "sed -i（GNU/BSD 引數語意分歧；請改寫中間檔）"),
    # R69（DEF-101-702／R68-03）：B 組原只機械化 3 項，而本 repo 自己在
    # `tools/macos_smoke_local.sh` 檔頭「相容性」段逐字宣告了 8 項禁令——**宣告的比守的多**，
    # 剩下 5 項在沙箱注入後全套根層測試仍 rc=0。以下補齊，判準與該段散文由
    # `TestProseBanListIsFullyMechanised` 雙向綁定，避免再長出「列了但沒守」的差集。
    (re.compile(r"\bstat\s+(?:-[a-zA-Z]+\s+)*-c\b"), "stat -c（GNU；BSD stat 用 -f）"),
    (re.compile(r"\bdate\s+(?:-[a-zA-Z]+\s+)*-d\b"), "date -d（GNU；BSD date 用 -v/-j -f）"),
    (re.compile(r"(?<![\w./-])timeout\s+[0-9]"),
     "timeout（GNU coreutils；macOS 預設不存在，命令直接 not found）"),
    (re.compile(r"\bxargs\s+(?:-[a-zA-Z]+\s+)*-r\b"), "xargs -r（GNU；BSD xargs 無此旗標）"),
    (re.compile(r"\bfind\b[^\n|;]*\s-printf\b"), "find -printf（GNU；BSD find 無此述詞）"),
    # R82（MAC-01）：**裸 mktemp**（不帶模板）。GNU coreutils 省略模板時會用預設的
    # `tmp.XXXXXXXXXX`；BSD/macOS 沒有這個預設，裸 `mktemp` 直接是 usage error（rc=1、
    # 什麼都不建）。危害不是「少一個暫存檔」——本 repo 的三個站點全都住在 `set -uo
    # pipefail`（**無 -e**）的 git hook 裡，於是失敗只讓變數變空字串，接著的重導向失敗
    # 被上層讀成**別的**失敗，印出「無法讀取暫存區內容」「ruff check tools/ 失敗」這種
    # 與真因無關的診斷 ⇒ mac 開發者拿到的是確定為假的因果。
    # 判準形狀：`mktemp` 之後（可跨若干短旗標）第一個非旗標 token 必須以引號／`$`／`/`
    # 起頭＝有模板。**刻意不判「模板是否含 XXXXXX」**——那要理解變數展開，不是行級 regex
    # 能可靠判定的東西，寫進來只會製造要逐筆辯護的假紅。
    (re.compile(r"\bmktemp(?!\s+(?:-[a-zA-Z]+\s+)*[\"'$/])"),
     "裸 mktemp（BSD 無預設模板，必須帶 \"${TMPDIR:-/tmp}/x.XXXXXX\"）"),
]

# 散文側禁令 token ↔ 上表判準的綁定用樣本：每個 token 配一段**應被判違規**的最小 bash。
# 兩側由 `TestProseBanListIsFullyMechanised` 雙向比對：散文列了而這裡沒有 → 紅；
# 這裡有而樣本打不中對應 pattern → 紅（即「登記了卻是空殼」）。
_BAN_TOKEN_SAMPLES: dict[str, str] = {
    "declare -A": "declare -A map",
    "mapfile": "mapfile -t arr < f",
    "${var,,}": 'echo "${v,,}"',
    "local -A": "local -A m",
    "typeset -A": "typeset -A m",
    "shopt -s globstar": "shopt -s globstar",
    "declare -g": "declare -g X=1",
    "grep -P": "grep -P 'x' f",
    "readlink -f": "readlink -f x",
    "sed -i": "sed -i 's/a/b/' f",
    "stat -c": "stat -c %Y f",
    "date -d": "date -d @123",
    "timeout": "timeout 5 cmd",
    "xargs -r": "xargs -r rm",
    "find -printf": "find . -printf '%p'",
    "mktemp": "x=$(mktemp)",
}


def _latest_root() -> Path:
    """LATEST 版根目錄（sdd_version.py SSOT；解析失敗即 AssertionError）。委派
    tools/lib/sdd_latest.py 單一真相源（ADR-XPLAT-002 Phase 2-C，R66 收斂）。"""
    return sdd_latest.resolve_latest_root(_REPO_ROOT / "AISDLC_SDD")


def _git_tracked(rel_prefix: str) -> list[str]:
    """git tracked 檔案相對路徑清單（fail-loud：git 失敗即 AssertionError）。"""
    proc = subprocess.run(
        ["git", "-C", str(_REPO_ROOT), "-c", "core.quotePath=false",
         "ls-files", "--", rel_prefix],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"git ls-files 失敗（{rel_prefix}；rc={proc.returncode}；"
            f"stderr={proc.stderr.strip()!r}）——掃描邊界不得靜默縮小"
        )
    return [line for line in proc.stdout.splitlines() if line]


def _is_bash_script(rel: str) -> bool:
    """*.sh/*.bash 必收；無副檔名（git hooks 慣例）看檔頭 shebang 含 bash。"""
    name = rel.rsplit("/", 1)[-1]
    if name.endswith((".sh", ".bash")):
        return True
    if "." in name:
        return False
    p = _REPO_ROOT / rel
    try:
        with p.open("rb") as fh:
            head = fh.readline(256)
    except OSError as exc:  # tracked 但磁碟缺席等——fail-loud 不縮面
        raise AssertionError(f"無法讀取 tracked 檔 {rel}：{exc}") from exc
    return head.startswith(b"#!") and b"bash" in head


def _scan_trees() -> list[tuple[str, list[str], int]]:
    """（樹 key, bash 檔相對路徑清單, 檔數下限）；下限＝實掃數打八折（最低 1）。

    根 tools/ 排除 git-hooks/（該樹獨立列管，floor 各自釘選——單樹縮面必紅、
    不被同層他樹掩蓋）；AutoClaude/tools/ 含其 git-hooks/（同一納管語意，
    對齊任務裁決的樹清單）。LATEST key 以「LATEST/tools」正規化，升版不失效。
    """
    latest = _latest_root()
    latest_prefix = f"AISDLC_SDD/{latest.name}/tools"
    specs: list[tuple[str, str, tuple[str, ...], int]] = [
        ("tools", "tools", ("tools/git-hooks/",), 4),
        ("tools/git-hooks", "tools/git-hooks", (), 2),
        ("AutoClaude/tools", "AutoClaude/tools", (), 6),
        ("AISDLC_SDD/scripts", "AISDLC_SDD/scripts", (), 4),
        ("AISDLC_SDD/.githooks", "AISDLC_SDD/.githooks", (), 1),
        ("LATEST/tools", latest_prefix, (), 4),
    ]
    trees: list[tuple[str, list[str], int]] = []
    for key, prefix, excludes, floor in specs:
        files = [
            rel
            for rel in _git_tracked(prefix)
            if not rel.startswith(excludes) and _is_bash_script(rel)
        ]
        trees.append((key, sorted(files), floor))
    return trees


def _split_code_comment(line: str) -> tuple[str, str]:
    """單行拆（code 段, 註解段）——引號外且位於字首/空白/;&|( 之後的 # 才算註解。

    單/雙引號逐字元追蹤（雙引號內與引號外的反斜線跳脫下一字元；單引號內
    無跳脫），字串內的 # 不會誤判為註解起點（`$#`、`${#arr[@]}` 前導字元
    非分隔符，亦不誤判）。$'…'/backtick 等罕見形不追（docstring 明示邊界）。
    """
    in_sq = in_dq = False
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if in_sq:
            if ch == "'":
                in_sq = False
        elif in_dq:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_dq = False
        else:
            if ch == "\\":
                i += 2
                continue
            if ch == "'":
                in_sq = True
            elif ch == '"':
                in_dq = True
            elif ch == "#" and (i == 0 or line[i - 1] in " \t;&|("):
                return line[:i], line[i:]
        i += 1
    return line, ""


def scan_source(source: str, rel: str) -> tuple[list[str], list[str]]:
    """純函式核心：回傳 (offenders, stale_markers)，元素皆為 `rel:行號: 說明`。

    stale＝標記存在但該行沒有被壓下的違規（含 WHY 留空）→ 必須清掉或補 WHY。
    """
    offenders: list[str] = []
    stale: list[str] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        code, comment = _split_code_comment(line)
        why: str | None = None
        if _OK_MARKER in comment:
            why = comment.split(_OK_MARKER, 1)[1].strip()
        hits = [desc for pattern, desc in _PATTERNS if pattern.search(code)]
        if hits:
            if why:  # 有標記且 WHY 非空 → 豁免（壓下該行全部命中）
                continue
            offenders.extend(
                f"{rel}:{lineno}: {desc}（bash 3.2/BSD 不相容）" for desc in hits
            )
            if why is not None:  # 標記在但 WHY 留空 → 無豁免力，另列 stale
                stale.append(f"{rel}:{lineno}: bash4-ok 標記 stale（WHY 留空）")
        elif why is not None:
            stale.append(f"{rel}:{lineno}: bash4-ok 標記 stale（該行無被壓下的違規）")
    return offenders, stale


def scan_files(rels: list[str]) -> tuple[list[str], list[str], list[str]]:
    """回傳 (offenders, stale, read_failures)——讀檔失敗一律列報不靜默跳過。"""
    offenders: list[str] = []
    stale: list[str] = []
    read_failures: list[str] = []
    for rel in rels:
        try:
            source = (_REPO_ROOT / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            read_failures.append(f"{rel}: {type(exc).__name__}: {exc}")
            continue
        off, st = scan_source(source, rel)
        offenders.extend(off)
        stale.extend(st)
    return offenders, stale, read_failures


class TestBash32Compat(unittest.TestCase):
    def test_repo_trees_have_no_bash4_or_gnu_only_usage(self) -> None:
        offenders: list[str] = []
        stale: list[str] = []
        read_failures: list[str] = []
        for key, files, floor in _scan_trees():
            # per-tree 下限釘選：單樹縮面必紅
            self.assertGreaterEqual(
                len(files), floor,
                f"{key} 掃描檔數 {len(files)} < 下限 {floor}——該樹掃描面疑似縮小"
                f"（git ls-files 列舉異常／檔案大規模消失）",
            )
            off, st, rf = scan_files(files)
            offenders.extend(off)
            stale.extend(st)
            read_failures.extend(rf)
        self.assertEqual(
            read_failures, [],
            "以下 bash 腳本無法讀取——掃描面不得靜默縮小：\n" + "\n".join(read_failures),
        )
        self.assertEqual(
            offenders, [],
            "發現 bash 3.2/BSD 不相容站點（macOS /bin/bash 3.2.57 或 BSD 工具下"
            "執行期才炸，bash -n 攔不住）——請改寫為 3.2 相容寫法；確屬刻意"
            "（如宣告僅跑於 bash 4+ 環境）時，於該行行尾加 `# bash4-ok: <WHY>` "
            "豁免：\n" + "\n".join(offenders),
        )
        self.assertEqual(
            stale, [],
            "bash4-ok 豁免標記 stale（防清單腐化）：\n" + "\n".join(stale),
        )

    # ── 以下以注入 fixture 自證判準紅綠（fixture 僅存在於 tmp，不留違規樣本於 repo）──

    def _scan_fixture(self, source: str) -> tuple[list[str], list[str]]:
        """tempfile 寫假腳本後走檔案讀取路徑掃描（不落 repo 樹內）。"""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "fixture_case.sh"
            p.write_text(source, encoding="utf-8")
            return scan_source(p.read_text(encoding="utf-8"), "fixture_case.sh")

    def test_injected_bash4_violations_detected(self) -> None:
        """A 組假違規 fixture 必紅（declare -A／mapfile／${var,,}／|&／wait -n）。"""
        off, stale = self._scan_fixture(
            "#!/bin/bash\n"
            "declare -A map\n"
            "mapfile -t lines < f\n"
            'echo "${name,,}"\n'
            "cmd |& tee log\n"
            "wait -n\n"
        )
        self.assertEqual(len(off), 5, off)
        self.assertIn("fixture_case.sh:2: declare -A", off[0])
        self.assertIn("fixture_case.sh:3: mapfile", off[1])
        self.assertIn("${var,,}", off[2])
        self.assertIn("|&", off[3])
        self.assertIn("wait -n", off[4])
        self.assertEqual(stale, [])

    def test_injected_bsd_discipline_violations_detected(self) -> None:
        """B 組假違規 fixture 必紅（grep -P／readlink -f／sed -i）。"""
        off, stale = self._scan_fixture(
            "grep -oP 'x' f\n"
            "readlink -f /tmp/x\n"
            "sed -i 's/a/b/' f\n"
        )
        self.assertEqual(len(off), 3, off)
        self.assertIn("grep -P", off[0])
        self.assertIn("readlink -f", off[1])
        self.assertIn("sed -i", off[2])
        self.assertEqual(stale, [])

    def test_injected_bare_mktemp_is_detected_and_templates_are_not(self) -> None:
        """R82 MAC-01：注入三個站點**修前**的逐字形態必紅；repo 既有的帶模板寫法必綠。

        兩個方向都要——只驗紅的那一半會漏掉「判準太寬、把正解一起判違規」，而那種鎖
        的下場是被整個關掉（本檔 `timeout` 那條當初就差點如此）。
        """
        off, stale = self._scan_fixture(
            '_blob="$(mktemp)"\n'                       # pre-commit:330 修前
            "_ac_log=\"$(mktemp 2>/dev/null || echo '')\"\n"   # pre-push:255 修前
            '_ruff_err="$(mktemp)"\n'                   # pre-push:387 修前
        )
        self.assertEqual(len(off), 3, off)
        for i in (0, 1, 2):
            self.assertIn("裸 mktemp", off[i])
        self.assertEqual(stale, [])
        # 帶模板的三種既有正確體例（含 `-d`、含中間旗標）一律不得誤紅
        ok, ok_stale = self._scan_fixture(
            'WORK="$(mktemp -d "${TMPDIR:-/tmp}/x.XXXXXX")"\n'
            'LOG="$(mktemp "${TMPDIR:-/tmp}/y.XXXXXX")"\n'
            "T=\"$(mktemp '/tmp/z.XXXXXX')\"\n"
            'echo "無法建立暫存檔（mktemp \'${TMPDIR:-/tmp}/y.XXXXXX\' 失敗）"\n'
        )
        self.assertEqual((ok, ok_stale), ([], []))

    def test_comment_hits_are_ignored(self) -> None:
        """整行/行內註解中的 pattern 文字不判違規（六樹實況命中全在註解內）。"""
        off, stale = self._scan_fixture(
            "# 相容性：禁 declare -A / mapfile / ${var,,}\n"
            "echo ok  # 註：grep -P 與 sed -i 皆禁用\n"
        )
        self.assertEqual((off, stale), ([], []))

    def test_string_hash_does_not_hide_violation(self) -> None:
        """字串內的 # 不得被誤當註解起點——其後的真違規仍必須命中。"""
        off, stale = self._scan_fixture('echo "x # y"; mapfile -t z < f\n')
        self.assertEqual(len(off), 1, off)
        self.assertIn("fixture_case.sh:1: mapfile", off[0])
        self.assertEqual(stale, [])

    def test_marker_suppresses_violation(self) -> None:
        """行尾豁免標記（附 WHY）＝綠，且不判 stale。"""
        off, stale = self._scan_fixture(
            "declare -A map  # bash4-ok: 本腳本檔頭強制 bash>=4 才執行\n"
        )
        self.assertEqual((off, stale), ([], []))

    def test_stale_or_empty_why_marker_fails(self) -> None:
        """標記 stale（該行無被壓下的違規）或 WHY 留空 → fail-loud 防腐化。"""
        off, stale = self._scan_fixture(
            "echo ok  # bash4-ok: 已改寫後忘了拆標記\n"
            "declare -A map  # bash4-ok:\n"
        )
        # WHY 留空的標記不具豁免力：該違規仍列報
        self.assertEqual(len(off), 1, off)
        self.assertIn("fixture_case.sh:2: declare -A", off[0])
        self.assertEqual(len(stale), 2, stale)
        self.assertIn("fixture_case.sh:1", stale[0])
        self.assertIn("該行無被壓下的違規", stale[0])
        self.assertIn("fixture_case.sh:2", stale[1])
        self.assertIn("WHY 留空", stale[1])


class TestScanConfigPinning(unittest.TestCase):
    """守門自身樹清單釘選（QA-R13-2 同構；手法同 test_subprocess_encoding_hygiene）。

    WHY：per-tree 下限只防「樹內縮檔數」，不防「整樹自 _scan_trees 刪列」——
    刪一列即整樹靜默出界、零機械訊號。LATEST 已於 _scan_trees 以「LATEST/tools」
    正規化 key，升版不失效。樹清單有意變更時須連同本案改。
    """

    def test_scan_trees_pinned(self) -> None:
        """R56 round 5 修正（SA）：與 ps1 側 QA B-3 同步，維持兩平台守門密度對稱。

        原實作 `keys = {key for key, _files, _floor in _scan_trees()}` 之後只斷言
        keys、`_floor` 從未進入斷言——與 `test_ps51_compat.TestPs51ScanConfigPinning`
        修正前逐字同構。注入實證：把 `AutoClaude/tools` 的 floor 由 6 改成 1，本模組
        全部 8 支測試仍 failures=0 errors=0＝「下限值本身被無聲下修」零機械訊號。
        改為 keys 與 floors 逐值同釘（DEF-101-451：修一邊卻讓兩平台失衡，正是本輪
        主題所要防的問題）。

        既知邊界（與 ps1 側刻意不同，非疏漏）：本檔 floors ＝實掃數打八折（見
        `_scan_trees` docstring），故掃描面本來就可先無聲縮水約 20% 才紅；ps1 側
        floors 與實數零餘裕。本斷言只鎖住「下限值本身被改動／整樹被刪列」這兩條
        路徑，不收斂那 20% 鬆弛。
        """
        keys_floors = [(key, floor) for key, _files, floor in _scan_trees()]
        self.assertEqual(
            keys_floors,
            [
                ("tools", 4),
                ("tools/git-hooks", 2),
                ("AutoClaude/tools", 6),
                ("AISDLC_SDD/scripts", 4),
                ("AISDLC_SDD/.githooks", 1),
                ("LATEST/tools", 4),
            ],
            "bash 掃描樹清單或 per-tree 檔數下限被改動——刻意調整請同步改本釘選值",
        )


class TestProseBanListIsFullyMechanised(unittest.TestCase):
    """R69（DEF-101-702／R68-03）：**宣告的禁令不得多於守得住的判準**。

    WHY：本 repo 在三個地方各寫了一份「bash 3.2 / BSD 禁用清單」，長度分別是 8、4、3 項，
    而 `_PATTERNS` 修前只機械化其中 3 項 BSD 禁令 —— 沙箱把 5 項散文列了但沒守的形態注入
    腳本後，全套根層測試仍 rc=0。「文件宣告」與「機械判準」的差集就是**假合規面**：讀者
    照檔頭寫程式時以為有人在守，實際沒有。本鎖把差集本身變成紅燈。

    兩個方向都要（單向會留下另一種漂移）：
      ① 散文列的每一項都必須有能真的打中它的 pattern（否則是空頭宣告）；
      ② `_BAN_TOKEN_SAMPLES` 登記的每一項都必須真的被某條 pattern 命中（否則是空殼登記，
         看起來有守、其實 pattern 寫壞了也沒人知道）。
    """

    _PROSE_SH = _REPO_ROOT / "tools" / "macos_smoke_local.sh"

    def _prose_tokens(self) -> set[str]:
        """自 macos_smoke_local.sh 檔頭「相容性」段抽出禁令 token（該段即散文 SSOT）。"""
        text = self._PROSE_SH.read_text(encoding="utf-8")
        start = text.find("# 相容性：嚴格 bash 3.2")
        self.assertNotEqual(start, -1, "macos_smoke_local.sh 檔頭「相容性」段消失——抽取面崩塌")
        block = text[start:text.find("相容手法參照", start)]
        return {tok for tok in _BAN_TOKEN_SAMPLES if tok in block}

    def test_every_prose_ban_has_a_pattern_that_fires(self) -> None:
        tokens = self._prose_tokens()
        # 🔴 R82：下限由 8 重釘為 12（**收緊**，方向與棘輪紀律一致）。8 是 R69 落地當時
        # 的值，而該段散文早已列到 11 項；下限停在舊值＝保護逐輪稀釋（同 `_SCAN_FLOOR`
        # 在 R75 被抓到的病）。本輪新增「裸 mktemp」⇒ 實測 12。
        self.assertGreaterEqual(
            len(tokens), 12, f"檔頭禁令 token 只抽到 {sorted(tokens)}——抽取樣式或散文漂移"
        )
        uncovered = sorted(
            tok for tok in tokens
            if not any(pat.search(_BAN_TOKEN_SAMPLES[tok]) for pat, _desc in _PATTERNS)
        )
        self.assertEqual(
            uncovered, [],
            f"這些禁令只活在散文裡、`_PATTERNS` 打不中：{uncovered}——"
            f"補上判準，或（若刻意不守）把它從檔頭清單移除並寫明理由",
        )

    def test_every_registered_sample_is_actually_caught(self) -> None:
        """反空殼：登記表本身的每一筆都必須真的觸發某條 pattern。"""
        dead = sorted(
            tok for tok, sample in _BAN_TOKEN_SAMPLES.items()
            if not any(pat.search(sample) for pat, _desc in _PATTERNS)
        )
        self.assertEqual(dead, [], f"_BAN_TOKEN_SAMPLES 有登記卻打不中的空殼條目：{dead}")

    def test_the_real_trees_stay_green_after_widening(self) -> None:
        """反誤紅：新增判準後，六棵真實掃描樹不得冒出任何新違規。"""
        rels: list[str] = []
        for _key, files, _floor in _scan_trees():
            rels.extend(files)
        offenders, stale, read_failures = scan_files(rels)
        self.assertEqual(read_failures, [])
        self.assertEqual(offenders, [], "擴充判準後真實腳本樹出現違規（請逐筆修，勿縮判準）")
        self.assertEqual(stale, [])


# ---- R69（DEF-101-702／R68-43）：set -u ＋ 空陣列展開（bash 3.2 執行期必炸）----------
_SET_U_RE = re.compile(r"set\s+-[a-zA-Z]*u")
_EMPTY_ARRAY_DECL_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)=\(\s*\)", re.M)


def unset_safe_array_problems(code: str, rel: str) -> list[str]:
    """回傳「`set -u` 檔內、以 `"${NAME[@]}"` 裸展開可能為空之陣列」的違規清單。

    WHY（本判準為何存在）：`AISDLC_SDD_v0.30/tools/fsm_runtime/formal/run_tlc.sh` 同時有
    `set -euo pipefail` 與 `TLA_VERSION_ARGS=()`，於是在 macOS 系統 bash 3.2 下**每一條**
    執行路徑都死在 `"${TLA_VERSION_ARGS[@]}"`（3.2 對空陣列的 `[@]` 展開視為 unbound），
    而該檔自訂 rc=1＝「TLC 偵測到 invariant violation」⇒ **環境錯誤被偽裝成形式化驗證失敗**。
    `bash -n` 攔不到（語法合法），CI 的 bash 5.x 也攔不到（5.x 不視為 unbound）。

    安全形態＝`${NAME[@]+"${NAME[@]}"}`（3.2/5.x 皆正確）。

    啟發式邊界（刻意寫明，勿當成完備分析）：若檔內任何地方以 `${#NAME[@]}` 做過非空守衛
    （如 `if [ "${#a[@]}" -gt 0 ]`），視該陣列為已守；`${#…}` 對空陣列本來就安全，這是本
    repo 既有的正確寫法（`AutoClaude/tools/git-hooks/pre-commit`）。代價是「守衛在別的分支、
    展開不在其內」這種形態會漏抓——行級掃描器換不到控制流分析，如實揭露。
    """
    if not _SET_U_RE.search(code):
        return []
    problems: list[str] = []
    for name in sorted(set(_EMPTY_ARRAY_DECL_RE.findall(code))):
        if f"${{#{name}[@]}}" in code:
            continue
        for match in re.finditer(rf'"\$\{{{name}\[@\]\}}"', code):
            line_start = code.rfind("\n", 0, match.start()) + 1
            segment = code[line_start:match.end()]
            if f"${{{name}[@]+" in segment:
                continue
            lineno = code.count("\n", 0, match.start()) + 1
            problems.append(
                f"{rel}:{lineno}: `set -u` 檔內對可能為空的陣列 {name} 裸展開 "
                f'"${{{name}[@]}}" —— bash 3.2 判為 unbound、執行期必炸；'
                f'請改 ${{{name}[@]+"${{{name}[@]}}"}}'
            )
    return problems


#: `$NAME` 後**緊接非 ASCII 字元**（全形括號／中文標點等）。bash 3.2 會把該字元的位元組
#: 併進變數名，5.x 不會 —— 故這是 3.2 專屬陷阱，正是本檔的守備範圍。
_FULLWIDTH_GLUED_VAR_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)([^\x00-\x7f])")


def fullwidth_glued_var_problems(code: str, rel: str) -> list[str]:
    """回傳「`$VAR` 緊接非 ASCII 字元」的違規清單（純函式，可構造輸入測鑑別力）。

    WHY（R69 終審 P3，`DEF-101-742`）：`tools/git-hooks/pre-push` 的
    `echo "…找不到 $SDD_CI_YML（根層消費檔清單來源…"` 在 macOS 系統 bash 3.2.57
    （`/bin/bash`）＋ `set -u` 下，全形左括號的位元組被併進變數名 ⇒
    `SDD_CI_YML<亂碼>: unbound variable`，**整支 hook 當場中止**（實測：該行之後的所有
    leg 都不再執行、rc=1）。CI 的 bash 5.x 與 `bash -n` 皆攔不到（語法合法、5.x 名稱
    解析不同），`macos-compat-ci` 雖有「以 /bin/bash 3.2 直接執行 dispatcher」步驟，
    但走不到這個分支（要 `aisdlc-sdd-ci.yml` 缺席才觸發）⇒ 這條路徑上零機械訊號。

    安全形態＝`${VAR}（`。判準刻意**不限於 `set -u` 檔**：即使沒有 `set -u`，該寫法也會
    靜默展開成空字串、訊息內容當場失真——只是不會炸而已，一樣是缺陷。
    """
    problems: list[str] = []
    for match in _FULLWIDTH_GLUED_VAR_RE.finditer(code):
        lineno = code.count("\n", 0, match.start()) + 1
        name, glued = match.group(1), match.group(2)
        problems.append(
            f"{rel}:{lineno}: `${name}` 緊接非 ASCII 字元 {glued!r} —— macOS 系統 bash "
            f"3.2 會把它併進變數名，`set -u` 下即 unbound variable 並中止整支腳本"
            f"（bash 5.x 與 `bash -n` 都攔不到）。請改寫成 ${{{name}}}{glued}"
        )
    return problems


class TestFullwidthGluedVariableName(unittest.TestCase):
    """R69 `DEF-101-742`：`$VAR` 緊接全形標點 —— bash 3.2 專屬的整支中止陷阱。"""

    def test_real_trees_have_no_fullwidth_glued_variable(self) -> None:
        problems: list[str] = []
        for _key, files, _floor in _scan_trees():
            for rel in files:
                source = (_REPO_ROOT / rel).read_text(encoding="utf-8")
                code = "\n".join(_split_code_comment(line)[0] for line in source.splitlines())
                problems.extend(fullwidth_glued_var_problems(code, rel))
        self.assertEqual(problems, [], "\n".join(problems))

    def test_detector_catches_the_pre_push_pre_fix_shape(self) -> None:
        """注入 pre-push:152 修前的逐字形態，必須命中並指名變數。"""
        code = 'echo "找不到 $SDD_CI_YML（根層消費檔清單來源）" >&2\n'
        hits = fullwidth_glued_var_problems(code, "pre-push")
        self.assertTrue(hits, "修前形態未被命中 —— 本道無牙")
        self.assertIn("SDD_CI_YML", hits[0])

    def test_detector_accepts_the_braced_form_and_ascii_neighbours(self) -> None:
        """修後形態與一般 ASCII 相鄰字元不得誤紅（否則全 repo 每個 `$VAR` 都會紅）。"""
        self.assertEqual(
            fullwidth_glued_var_problems(
                'echo "找不到 ${SDD_CI_YML}（來源）"\n', "pre-push"), [])
        self.assertEqual(
            fullwidth_glued_var_problems('echo "$A/$B-$C.txt $D"\n', "x.sh"), [])


class TestUnsetSafeArrayExpansion(unittest.TestCase):
    """R69（DEF-101-702／R68-43）：`set -u` ＋ 空陣列展開的行級守門與其鑑別力。"""

    def test_real_trees_have_no_unguarded_empty_array_expansion(self) -> None:
        problems: list[str] = []
        for _key, files, _floor in _scan_trees():
            for rel in files:
                source = (_REPO_ROOT / rel).read_text(encoding="utf-8")
                code = "\n".join(_split_code_comment(line)[0] for line in source.splitlines())
                problems.extend(unset_safe_array_problems(code, rel))
        self.assertEqual(problems, [], "\n".join(problems))

    def test_detector_catches_the_run_tlc_pre_fix_shape(self) -> None:
        """注入 run_tlc.sh 修前的逐字形態，必須命中。"""
        code = 'set -euo pipefail\nARGS=()\nrun --module X "${ARGS[@]}"\n'
        self.assertTrue(unset_safe_array_problems(code, "x.sh"))

    def test_detector_accepts_the_fixed_form(self) -> None:
        code = 'set -euo pipefail\nARGS=()\nrun --module X ${ARGS[@]+"${ARGS[@]}"}\n'
        self.assertEqual(unset_safe_array_problems(code, "x.sh"), [])

    def test_detector_accepts_the_length_guarded_form(self) -> None:
        """本 repo 既有的正確寫法（pre-commit 的 `[ "${#a[@]}" -gt 0 ]`）不得誤紅。"""
        code = ('set -eu\nA=()\nA+=("x")\n'
                'if [ "${#A[@]}" -gt 0 ]; then ruff check "${A[@]}"; fi\n')
        self.assertEqual(unset_safe_array_problems(code, "x.sh"), [])

    def test_detector_is_inert_without_set_u(self) -> None:
        """沒有 `set -u` 就沒有這個缺陷類別——不得對一般腳本製造噪音。"""
        code = 'A=()\nrun "${A[@]}"\n'
        self.assertEqual(unset_safe_array_problems(code, "x.sh"), [])


# ── R82（MAC-05）：`date +…%N` 奈秒 —— BSD strftime 無此格式字元 ─────────────────
#: `date` 的格式字串裡出現 `%N`。判準刻意只認「`date` 之後、同一個 simple command 內、
#: 以 `+` 起頭的格式字串裡帶 `%N`」——只判 `%N` 三個字元會把註解外的一般文字也掃進來。
_GNU_DATE_NANOS_RE = re.compile(r"\bdate\s+[^|;&]*\+[^\s|;&)\"']*%N")

#: 存量債（shrink-only）：今天有幾行在用它。落地當回合實測＝
#: `AutoClaude/tools/sd06_w3_staging_dryrun.sh` 16 行（剝註解後）。
#:
#: 🔴 為何走**債表**而不是併進 `_PATTERNS`：`_PATTERNS` 是零容忍面（`TestProseBanList
#: IsFullyMechanised::test_the_real_trees_stay_green_after_widening` 要求擴充判準後六樹
#: 不得冒出任何違規），而這 16 個站點住在 `AutoClaude/**`——本包（R82 A3）在檔案所有權
#: 上不得動那棵樹。把它塞進零容忍面只會製造一個「必須立刻繞過」的紅，那種鎖活不過一輪。
#: 債表的張力方向與 `_WORKFLOW_GNU_DEBT` 逐字相同：多一筆＝有人新寫（紅）；少一筆＝債還
#: 了請把數字改小（也紅，否則下一筆新違規會被舊值遮住）；出現**不在表上的檔**＝紅。
_DATE_NANOS_DEBT: dict[str, int] = {
    "AutoClaude/tools/sd06_w3_staging_dryrun.sh": 16,
}


def gnu_date_nanos_problems(code: str, rel: str) -> list[str]:
    """回傳「`date` 格式字串帶 `%N`」的違規清單（純函式，可構造輸入測鑑別力）。

    WHY（R82 MAC-05）：`%N`（奈秒）是 **GNU coreutils 的擴充**，不在 BSD `strftime(3)`
    的格式字元表內；macOS 的 `date` 就是 BSD date。BSD 對不認得的轉換是**原樣輸出**，
    於是 `date +%s%N` 回的是 `1754…N` 這種尾巴帶字母 N 的字串，接著的
    `$(( END - START ))` 直接算術崩——而 `bash -n` 攔不到（語法完全合法）、ubuntu CI
    也攔不到（GNU date 支援）、Windows 的 Git Bash 同樣是 GNU userland ⇒ **三個平時
    在跑的環境全部給假綠，只有 mac 會炸**。

    跨平台寫法（兩者皆不需要 GNU）：
      · 只要秒級 → `date +%s`（POSIX，兩邊都對）；
      · 真的要次秒解析度 → `python3 -c 'import time; print(time.time_ns())'`
        （本 repo 的腳本本來就都要求 python3 在場）。

    🔴 本 repo 內那 16 個站點所在的檔案，其**檔頭自陳與自己下一句矛盾**（逐字同時斷言
    「現代 macOS BSD date 皆支援」與「嚴格 BSD 會輸出字面 N」），且那句「R11 真 Mac 實測」
    在 repo 內找不到可重跑的取證位置。本判準不去裁決那句話，只把「有幾個站點押在它上面」
    變成一個會說話的數字。
    """
    problems: list[str] = []
    for lineno, line in enumerate(code.splitlines(), start=1):
        if _GNU_DATE_NANOS_RE.search(line):
            problems.append(
                f"{rel}:{lineno}: `date` 格式字串帶 %N 奈秒（GNU 擴充）——BSD/macOS 的 "
                "strftime 無此格式字元、會原樣輸出字面 N，後續整數運算當場崩；"
                "請改 `date +%s`（秒級）或 "
                "`python3 -c 'import time; print(time.time_ns())'`"
            )
    return problems


class TestGnuDateNanoseconds(unittest.TestCase):
    """R82 MAC-05：`date +%N` 的存量債棘輪與判準鑑別力。"""

    def test_real_trees_match_the_debt_ratchet(self) -> None:
        counts: dict[str, int] = {}
        for _key, files, _floor in _scan_trees():
            for rel in files:
                source = (_REPO_ROOT / rel).read_text(encoding="utf-8")
                code = "\n".join(_split_code_comment(line)[0] for line in source.splitlines())
                hits = gnu_date_nanos_problems(code, rel)
                if hits:
                    counts[rel] = len(hits)
        self.assertEqual(
            counts, dict(_DATE_NANOS_DEBT),
            "`date +…%N` 存量與棘輪不符。多一筆／多一個檔＝新寫了 GNU-only 用法"
            "（**不得調高**債表）；少一筆＝債已還請把數字改小。"
            "跨平台寫法見 `gnu_date_nanos_problems` docstring",
        )

    def test_detector_catches_the_staging_dryrun_shape(self) -> None:
        """注入實際站點的逐字形態，必須命中並給出跨平台寫法。"""
        hits = gnu_date_nanos_problems("START=$(date +%s%N)\nEND=$(date +%s%N)\n", "x.sh")
        self.assertEqual(len(hits), 2, hits)
        self.assertIn("x.sh:1", hits[0])
        self.assertIn("time.time_ns()", hits[0])

    def test_detector_accepts_portable_forms(self) -> None:
        """POSIX 寫法與 python 取代方案不得誤紅（否則整批正解會被判違規）。"""
        for safe in (
            "START=$(date +%s)\n",
            'echo "$(date -u +%Y%m%d_%H%M%S)"\n',
            "START=$(python3 -c 'import time; print(time.time_ns())')\n",
            "date +%Y-%m-%dT%H:%M:%S%z\n",
        ):
            self.assertEqual(gnu_date_nanos_problems(safe, "x.sh"), [], safe)


# ══════════════════════════════════════════════════════════════════════════════
# R81 包 G（XPL-S1-02）— 同一套判準，第二個掃描面：workflow 的 inline `run:`
# ══════════════════════════════════════════════════════════════════════════════
# 缺陷本體：本檔的知識寫得很完整（連 `tools/macos_smoke_local.sh` 檔頭都逐字複述一遍），
# 但**同一份知識住兩個家、只有 `.sh` 那個家被鎖**——`_scan_trees()` 實測回傳 6 棵、
# 合計 29 支檔，副檔名集合是 `['.sh', '<none>']`，`.yml` **一支都不看**。
#
# 危害面是不對稱的：Windows 開發機的 Git Bash 帶 GNU userland、ubuntu CI 也是 GNU，
# 兩邊都會給出「這樣寫沒問題」的假訊號；只有 macos-latest 的 BSD userland 會炸，而
# `macos-compat-ci.yml` 的 inline `run:` 剛好就是唯一跑在那裡的東西，也剛好一個觀測者
# 都沒有。落地當回合實測：用**本檔自己的 `_PATTERNS`** 掃 12 支 workflow 的 inline
# `run:`，命中 3 筆 `date -d`（GNU-only），全在 `root-infra-ci.yml`。
#
# 判準把 `runs-on` 當**輸入**而不是寫死：
#   · 檔內任一 `runs-on:` 提到 macos ⇒ 該檔全部 `run:` 命中判**紅**（今天 0 筆，零成本）；
#   · 其餘（ubuntu／windows only）⇒ 進 shrink-only 存量棘輪，只登記不阻塞。
# 🔴 刻意做成**檔級**而非 job 級的過度涵蓋：同一支檔裡把一段 step 複製到 macos job，
#   是這條路徑上最可能發生的事，而 job 級判準對它結構上失明。代價是 macos 檔裡的
#   ubuntu-only job 也被判——實測 0 筆，且那本來就該收斂。
_WF_DIR = _REPO_ROOT / ".github" / "workflows"
_RUN_KEY_RE = re.compile(r"^(\s*)(?:-\s+)?run:\s*(\|[-+]?|>[-+]?)?\s*(.*)$")
_SHELL_KEY_RE = re.compile(r"^(\s*)shell:\s*(\S+)")
_RUNS_ON_RE = re.compile(r"^\s*runs-on:\s*(.*)$")
_LIST_ITEM_RE = re.compile(r"^(\s*)-\s")
#: 走 bash/sh 的 `shell:` 值（GitHub 預設在 Linux/macOS 上就是 bash）。其餘
#: （pwsh／powershell／cmd／python）**不是本判準的語言**，掃了只會製造假紅。
_BASH_SHELLS = ("bash", "sh")


def workflow_is_macos_capable(text: str) -> bool:
    """檔內任一 `runs-on:` 提到 macos ⇒ 這支 workflow 會踩到 BSD userland。"""
    return any("macos" in m.group(1).lower() for m in
               (_RUNS_ON_RE.match(line) for line in text.splitlines()) if m)


def _step_shell(lines: list[str], run_idx: int, indent: int) -> str | None:
    """該 `run:` 所屬 step 的 `shell:` 值（同縮排的兄弟鍵）；沒宣告回 None。

    啟發式邊界（刻意寫明）：以「同縮排或更淺的 `- ` 清單項」當 step 邊界。GitHub
    Actions 的 step 是 `- name:／uses:／run:／shell:` 這種平鋪結構，故同縮排的
    `shell:` 就是它的兄弟。job 級 `defaults.run.shell` 不追（本 repo 零使用）。
    """
    start = 0
    for idx in range(run_idx, -1, -1):
        item = _LIST_ITEM_RE.match(lines[idx])
        if item and len(item.group(1)) <= indent:
            start = idx
            break
    for idx in range(start, len(lines)):
        if idx != start:
            item = _LIST_ITEM_RE.match(lines[idx])
            if item and len(item.group(1)) <= indent:
                break
        found = _SHELL_KEY_RE.match(lines[idx])
        if found and len(found.group(1)) == indent:
            return found.group(2).strip("\"'")
    return None


def workflow_run_offenders(text: str, rel: str) -> tuple[list[str], list[str]]:
    """回傳 (offenders, stale)。判準與掃描機制**全部複用** `.sh` 那一側，不另立規則表。"""
    lines = text.splitlines()
    offenders: list[str] = []
    stale: list[str] = []
    idx = 0
    while idx < len(lines):
        found = _RUN_KEY_RE.match(lines[idx])
        if not found:
            idx += 1
            continue
        indent, block, inline = found.group(1), found.group(2), found.group(3)
        shell = _step_shell(lines, idx, len(indent))
        body: list[tuple[int, str]] = []
        if block:
            base = len(indent) + 2
            cursor = idx + 1
            while cursor < len(lines):
                line = lines[cursor]
                if line.strip() and (len(line) - len(line.lstrip())) < base:
                    break
                body.append((cursor + 1, line))
                cursor += 1
            idx = cursor
        else:
            body.append((idx + 1, inline))
            idx += 1
        if shell is not None and not shell.startswith(_BASH_SHELLS):
            continue                                   # pwsh／cmd 不是本判準的語言
        for lineno, line in body:
            code, comment = _split_code_comment(line)
            why: str | None = None
            if _OK_MARKER in comment:
                why = comment.split(_OK_MARKER, 1)[1].strip()
            hits = [desc for pattern, desc in _PATTERNS if pattern.search(code)]
            if hits:
                if why:
                    continue
                offenders.extend(f"{rel}:{lineno}: {desc}（inline run:）" for desc in hits)
                if why is not None:
                    stale.append(f"{rel}:{lineno}: {_OK_MARKER} 標記 stale（WHY 留空）")
            elif why is not None:
                stale.append(f"{rel}:{lineno}: {_OK_MARKER} 標記 stale（該行無被壓下的違規）")
    return offenders, stale


#: 🔴 shrink-only 存量棘輪：**只跑在 ubuntu／windows 的 workflow** 今天有幾筆 GNU-only
#: 用法。落地當回合實測 3 筆，全是 `root-infra-ci.yml` 的 `date -d`。
#: 兩個方向都會響：多一筆＝有人在非 macos job 新寫了 GNU-only 用法（那支檔與
#: `macos-compat-ci.yml` 是同一個目錄下的姊妹檔，複製一段 step 過去就會炸）；
#: 少一筆＝債還了請把數字改小，不改的話下一筆新違規會被舊值遮住。
#: **macos-capable 的 workflow 不進本表**——它們是零容忍。
_WORKFLOW_GNU_DEBT: dict[str, int] = {
    "root-infra-ci.yml": 3,
}


class TestWorkflowInlineRunIsBsdSafe(unittest.TestCase):
    """workflow 的 inline `run:` 與 `.sh` 受同一套判準（見上方區段 WHY）。"""

    @staticmethod
    def _scan() -> tuple[dict[str, int], dict[str, int], list[str], list[str], int]:
        macos_hits: dict[str, int] = {}
        other_hits: dict[str, int] = {}
        detail: list[str] = []
        stale: list[str] = []
        files = sorted(_WF_DIR.glob("*.yml")) + sorted(_WF_DIR.glob("*.yaml"))
        for path in files:
            text = path.read_text(encoding="utf-8")
            off, st = workflow_run_offenders(text, path.name)
            stale.extend(st)
            if not off:
                continue
            detail.extend(off)
            bucket = macos_hits if workflow_is_macos_capable(text) else other_hits
            bucket[path.name] = len(off)
        return macos_hits, other_hits, detail, stale, len(files)

    def test_macos_capable_workflows_have_no_gnu_only_usage(self) -> None:
        macos_hits, other_hits, detail, stale, scanned = self._scan()
        self.assertGreaterEqual(
            scanned, 10,
            f"workflow 掃描面只有 {scanned} 支 ⇒ 疑似縮面（落地當回合實測 12 支）")
        self.assertEqual(
            macos_hits, {},
            "跑在 macos-latest 上的 workflow 出現 bash 3.2／BSD 不相容用法——CI 的 ubuntu "
            "與 Windows 的 Git Bash 都是 GNU userland，兩邊都攔不到，只有 macOS runner "
            f"會炸。請改寫，或於該行行尾加 `# {_OK_MARKER} <WHY>`：\n" + "\n".join(detail))
        self.assertEqual(
            other_hits, dict(_WORKFLOW_GNU_DEBT),
            "非 macos workflow 的 GNU-only 存量與棘輪不符。多一筆＝新增（**不得調高**）；"
            "少一筆＝債已還請把數字改小：\n" + "\n".join(detail))
        self.assertEqual(
            stale, [],
            f"{_OK_MARKER} 豁免標記 stale（防清單腐化）：\n" + "\n".join(stale))

    # ── 紅綠自證：合成 workflow 片段（不落檔於 repo）────────────────────────────

    def test_injected_gnu_only_usage_in_a_run_block_is_detected(self) -> None:
        off, stale = workflow_run_offenders(
            "jobs:\n  x:\n    runs-on: macos-latest\n    steps:\n"
            "      - name: probe\n        run: |\n"
            "          readlink -f /tmp/x\n"
            "          declare -A m\n", "fixture.yml")
        self.assertEqual(len(off), 2, off)
        self.assertIn("readlink -f", off[0])
        self.assertIn("declare -A", off[1])
        self.assertEqual(stale, [])

    def test_a_single_line_run_is_also_scanned(self) -> None:
        off, _ = workflow_run_offenders(
            "      - run: sed -i 's/a/b/' f\n", "fixture.yml")
        self.assertEqual(len(off), 1, off)

    def test_powershell_steps_are_out_of_scope(self) -> None:
        """`shell: pwsh` 的 run: 不是 bash ⇒ 掃了只會製造假紅（windows-compat-ci 實況）。"""
        off, stale = workflow_run_offenders(
            "      - name: p\n        shell: pwsh\n        run: |\n"
            "          Get-Date -Format o   # timeout 5 cmd\n", "fixture.yml")
        self.assertEqual((off, stale), ([], []))

    def test_yaml_outside_run_blocks_is_not_scanned(self) -> None:
        """只有 `run:` 的內文是 shell；別的 YAML 鍵值不得被當程式碼掃。"""
        off, stale = workflow_run_offenders(
            "env:\n  NOTE: 'timeout 5 cmd 這串只是說明文字'\n"
            "      - uses: actions/checkout@v5\n", "fixture.yml")
        self.assertEqual((off, stale), ([], []))

    def test_runs_on_is_an_input_not_a_hardcoded_verdict(self) -> None:
        macos = "jobs:\n  a:\n    runs-on: macos-latest\n"
        ubuntu = "jobs:\n  a:\n    runs-on: ubuntu-latest\n"
        matrix = "jobs:\n  a:\n    runs-on: [ubuntu-latest, macos-latest]\n"
        self.assertTrue(workflow_is_macos_capable(macos))
        self.assertTrue(workflow_is_macos_capable(matrix))
        self.assertFalse(workflow_is_macos_capable(ubuntu))

    def test_the_marker_suppresses_and_rots_loudly(self) -> None:
        suppressed = ("      - run: date -d @1  # " + _OK_MARKER
                      + " 僅跑於 ubuntu job\n")
        self.assertEqual(workflow_run_offenders(suppressed, "fixture.yml"), ([], []))
        orphan = "      - run: echo ok  # " + _OK_MARKER + " 已改寫後忘了拆標記\n"
        self.assertTrue(workflow_run_offenders(orphan, "fixture.yml")[1])

    def test_the_pattern_table_is_shared_with_the_sh_side(self) -> None:
        """反漂移：本掃描面**不得**長出第二份規則表（那是本輪立案的病本身）。"""
        sample = "declare -A m"
        self.assertTrue(any(pat.search(sample) for pat, _d in _PATTERNS))
        off, _ = workflow_run_offenders(f"      - run: {sample}\n", "fixture.yml")
        self.assertTrue(off, "workflow 側沒有共用 `_PATTERNS` ⇒ 兩個家又要開始漂移")


if __name__ == "__main__":
    unittest.main()
