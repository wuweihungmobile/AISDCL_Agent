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
  B BSD 工具紀律組（GNU-only 選項）：grep -P、readlink -f、sed -i
    （SA-R15-REV-4 揭露：ONBOARDING §8 靜態自查清單另列第 4 項「BRE 交替」
    屬語意級判準——grep 是否用 ERE `|` 交替需理解上下文，非行級 regex 能可靠
    判定，刻意不納入本守門、仍靠人工紀律；本組僅機械化前 3 項）
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
    # ── B BSD 工具紀律組（GNU-only 選項，macOS BSD 工具不支援）──────────────
    (re.compile(r"\bgrep\s+-[a-zA-Z]*P\b"), "grep -P（BSD grep 無 PCRE；請改 -E）"),
    (re.compile(r"\breadlink\s+-f\b"), "readlink -f（BSD readlink 不支援；請用 cd+pwd -P）"),
    (re.compile(r"\bsed\s+-i\b"), "sed -i（GNU/BSD 引數語意分歧；請改寫中間檔）"),
]


def _latest_root() -> Path:
    """LATEST 版根目錄（sdd_version.py SSOT；解析失敗即 AssertionError）。"""
    sdd_root = _REPO_ROOT / "AISDLC_SDD"
    resolver = sdd_root / "scripts" / "sdd_version.py"
    proc = subprocess.run(
        [sys.executable, str(resolver), "--sdd-root", str(sdd_root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    name = proc.stdout.strip()
    if proc.returncode != 0 or not name:
        raise AssertionError(
            f"LATEST 解析失敗（sdd_version.py rc={proc.returncode}；stderr="
            f"{proc.stderr.strip()!r}）——掃描邊界不得靜默縮小"
        )
    return sdd_root / name


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
        keys = {key for key, _files, _floor in _scan_trees()}
        self.assertEqual(
            keys,
            {
                "tools",
                "tools/git-hooks",
                "AutoClaude/tools",
                "AISDLC_SDD/scripts",
                "AISDLC_SDD/.githooks",
                "LATEST/tools",
            },
        )


if __name__ == "__main__":
    unittest.main()
