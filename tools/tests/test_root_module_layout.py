"""根層模組落點鎖（TCS-SelfImproving-P1 R62；PRD FR-SI-34；AT-134 系列）。

判準函式以 `repo_root` 為參數（真樹與合成樹用同一份碼自證）：登記表對磁碟、`tools/lib/` 同前綴
散落（shrink-only 名冊加天花板）、套件須登記、新模組 PRD 須引落點 SSOT。誠實劃界：只驗路徑存在與
登記，不驗路徑「該不該在那裡」；只看檔名前綴，同一模組換前綴命名的散落看不見；只判含「模組落點表」
字樣的 PRD。新增 `tools/tests/` 檔須付重釘稅（NFR-P1-9）。
"""

from __future__ import annotations

import re
import shutil
import tempfile
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SSOT_REL = "docs/02_architecture/Root_Layout_and_Module_Placement.md"
PATH_EXTS = (".py", ".md", ".json", ".jsonl", ".yml", ".yaml", ".ps1", ".sh")
# shrink-only 名冊：2026-10-20 對真樹現查（≥3 支同前綴、無套件目錄者）；成套件後必須自名冊移除。
PREFIX_ROSTER = {"ledger", "quota", "skip"}
ROSTER_CEILING = 3
TESTS_A = "tools/tests/" + "test_a.py"  # 合成樹內的虛構測試檔路徑；拆開寫，免被死信引用掃描當成真檔
_TMP: Path


def setUpModule() -> None:
    global _TMP
    _TMP = Path(tempfile.mkdtemp(prefix="si_ly_"))


def tearDownModule() -> None:
    shutil.rmtree(_TMP, ignore_errors=True)


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def registry_rows(repo_root: Path) -> list[list[str]]:
    """SSOT 標題含 `## 3.` 的節內、欄數為六的資料列（排除表頭與分隔列）；缺檔或缺節回空串列。"""
    path = repo_root / SSOT_REL
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    start = next((i for i, ln in enumerate(lines) if ln.startswith("## ") and "## 3." in ln), None)
    if start is None:
        return []
    out = []
    for ln in lines[start + 1 :]:
        if ln.startswith("## "):
            break
        if ln.startswith("|"):
            cells = _cells(ln)
            if len(cells) == 6 and not set("".join(cells)) <= set("-: "):
                out.append(cells)
    return out[1:] if out and out[0][0] == "模組" else out


def _is_candidate(frag: str) -> bool:
    if re.search(r"\s", frag) or frag.startswith(("~", "$")):
        return False
    return "/" in frag or frag.endswith(PATH_EXTS) or "*" in frag


def path_candidates(row: list[str]) -> list[tuple[str, str, str | None]]:
    """（欄名, 片段, 承繼的基底）；無目錄前綴的檔名片段承繼同欄前一個帶目錄的片段為基底。"""
    out = []
    for col in range(1, 5):
        base = None
        for frag in re.findall(r"`([^`]+)`", row[col]):
            if not _is_candidate(frag):
                continue
            if "/" in frag:
                out.append((str(col), frag, None))
                base = frag
            else:
                out.append((str(col), frag, base))
    return out


def _exists(repo_root: Path, frag: str, base: str | None) -> bool:
    if base is not None:
        dirs = {base.rstrip("/"), str(Path(base.rstrip("/")).parent).replace("\\", "/")}
        found = [d for d in dirs if (repo_root / d).is_dir()]
        if "*" in frag:
            return any(q.is_file() for d in found for q in (repo_root / d).glob(frag))
        return any((repo_root / d / frag).exists() for d in found)
    if "*" in frag:
        return any(p.is_file() for p in repo_root.glob(frag))
    target = repo_root / frag
    if frag.endswith("/"):
        return target.is_dir() and any(p.is_file() for p in target.rglob("*"))
    return target.exists()


def registry_problems(repo_root: Path) -> list[str]:
    rows = registry_rows(repo_root)
    if not rows:
        return [f"{SSOT_REL}：解析不到登記表（缺 ## 3. 節或沒有六欄資料列），不得以 0 列通過"]
    out = []
    for row in rows:
        for col, frag, base in path_candidates(row):
            if not _exists(repo_root, frag, base):
                out.append(f"登記列「{row[0]}」第 {int(col) + 1} 欄的路徑 {frag} 在磁碟找不到")
    return out


def prefix_problems(repo_root: Path, roster: set[str], ceiling: int) -> list[str]:
    lib = repo_root / "tools" / "lib"
    counts = Counter(p.stem.split("_")[0] for p in lib.glob("*.py") if p.name != "__init__.py")
    out = []
    for prefix in sorted(roster):
        if (lib / prefix).is_dir():
            out.append(f"名冊內前綴 {prefix} 已成套件，須自名冊移除")
    for prefix, n in sorted(counts.items()):
        if n >= 3 and not (lib / prefix).is_dir() and prefix not in roster:
            out.append(
                f"新前綴 {prefix} 散落：同前綴 {n} 支且無 tools/lib/{prefix}/ 套件（不在名冊）"
            )
    if len(roster) != ceiling:
        out.append(f"名冊 {len(roster)} 項與天花板 {ceiling} 不相等（只准縮、縮了要同步下修）")
    return out


def package_problems(repo_root: Path) -> list[str]:
    lib = repo_root / "tools" / "lib"
    registered = " ".join(row[1] for row in registry_rows(repo_root))
    return [
        f"套件 tools/lib/{p.name}/ 未登記在任何登記列的程式碼欄"
        for p in sorted(lib.iterdir())
        if p.is_dir() and (p / "__init__.py").exists() and f"tools/lib/{p.name}/" not in registered
    ]


def prd_problems(repo_root: Path) -> list[str]:
    out = []
    for prd in sorted((repo_root / "docs" / "01_requirements").glob("*_PRD.md")):
        text = prd.read_text(encoding="utf-8")
        if "模組落點表" in text and SSOT_REL not in text:
            out.append(f"{prd.name} 含「模組落點表」字樣而未引用 {SSOT_REL}")
    return out


def synth(name: str) -> Path:
    root = _TMP / name
    root.mkdir(parents=True)
    return root


def write(root: Path, rel: str, text: str = "x\n") -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


HEAD = "| 模組 | 程式碼 | 入口／探針 | 測試 | 資料／文件 | 形態 |\n|---|---|---|---|---|---|\n"


def make_ssot(root: Path, rows: list[str], section: str = "## 3. 既有模組登記表\n\n") -> None:
    write(root, SSOT_REL, "# SSOT\n\n" + section + HEAD + "\n".join(rows) + "\n\n## 4. 其他\n")


def row(name="M", code="", entry="", tests="", data="") -> str:
    return f"| {name} | {code} | {entry} | {tests} | {data} | 形態 |"


class TestRegistryMatchesDisk(unittest.TestCase):
    def test_AT_134_1_1_real_registry_is_green(self):
        self.assertEqual(registry_problems(ROOT), [])
        rows = registry_rows(ROOT)
        self.assertGreaterEqual(len(rows), 1)
        self.assertGreaterEqual(sum(len(path_candidates(r)) for r in rows), 1)
        root = synth("g1")
        for rel in (
            "tools/lib/pkg/a.py",
            "tools/lib/pkg/b.py",
            "tools/x.py",
            "tools/probe/p.py",
            TESTS_A,
            "docs/06_quality/Z_Protocol/params.json",
            "tools/lib/solo/s.py",
        ):
            write(root, rel)
        make_ssot(
            root,
            [
                row(
                    "承繼",
                    code="`tools/lib/pkg/`（`a.py`、`b.py`）",
                    entry="`tools/x.py`",
                    tests=f"`{TESTS_A}`",
                    data="`docs/06_quality/Z_Protocol/params.json`",
                ),
                row(
                    "並列",
                    code="`tools/lib/solo/`、`s.py`",
                    entry="`python tools/x.py check`、`~/x/y.py`、"
                    "`$HOME/z.py`、`ledger`、`_hook_launcher`",
                    tests="`tools/tests/test_*.py`",
                    data="`tools/lib/pkg/*.py`",
                ),
            ],
        )
        self.assertEqual(registry_problems(root), [])

    def test_AT_134_1_E_1_missing_paths_are_red(self):
        def build(name, mutate=None, rows=None):
            root = synth(name)
            for rel in ("tools/lib/pkg/a.py", "tools/x.py", "docs/data/d.json"):
                write(root, rel)
            rows = rows or [
                row(
                    "對照",
                    code="`tools/lib/pkg/a.py`",
                    entry="`tools/x.py`",
                    tests="`docs/data/*.json`",
                    data="`docs/data/`",
                )
            ]
            make_ssot(root, rows)
            if mutate:
                mutate(root)
            return root

        self.assertEqual(registry_problems(build("e0")), [])
        root = build("e1", lambda r: (r / "tools/x.py").unlink())
        probs = registry_problems(root)
        self.assertEqual(len(probs), 1)
        self.assertTrue("對照" in probs[0] and "tools/x.py" in probs[0])
        root = build("e2", lambda r: (r / "docs/data/d.json").unlink())
        self.assertTrue(registry_problems(root))
        root = build(
            "e3",
            lambda r: (
                (r / "docs/data/d.json").unlink(),
                (r / "docs/data/e").mkdir(),
                (r / "docs/data").mkdir(exist_ok=True),
            ),
            rows=[row("目錄", data="`docs/data/`")],
        )
        probs = registry_problems(root)
        self.assertEqual(len(probs), 1)
        self.assertIn("docs/data/", probs[0])
        root = synth("e4")
        write(root, SSOT_REL, "# SSOT\n\n## 2. 只有別的節\n\n" + HEAD + row() + "\n")
        self.assertTrue(registry_problems(root))
        root = synth("e5")
        write(root, SSOT_REL, "# SSOT\n\n## 3. 空節\n\n只有文字，沒有六欄資料列\n")
        self.assertTrue(registry_problems(root))


class TestPrefixScatter(unittest.TestCase):
    def test_AT_134_2_1_compliant_shapes(self):
        self.assertEqual(prefix_problems(ROOT, PREFIX_ROSTER, ROSTER_CEILING), [])
        root = synth("p1")
        for rel in (
            "tools/lib/aa_x.py",
            "tools/lib/aa_y.py",
            "tools/lib/pkg_a.py",
            "tools/lib/pkg_b.py",
            "tools/lib/pkg_c.py",
            "tools/lib/cc_1.py",
            "tools/lib/cc_2.py",
            "tools/lib/cc_3.py",
            "tools/lib/one_x.py",
            "tools/lib/two_y.py",
            "tools/lib/pkg/__init__.py",
        ):
            write(root, rel)
        self.assertEqual(prefix_problems(root, {"cc"}, 1), [])

    def test_AT_134_2_E_1_red_shapes(self):
        def tree(name, files, dirs=()):
            root = synth(name)
            for rel in files:
                write(root, rel)
            for d in dirs:
                (root / d).mkdir(parents=True, exist_ok=True)
            return root

        aa = [f"tools/lib/aa_{c}.py" for c in "xyz"]
        probs = prefix_problems(tree("a", aa), set(), 0)
        self.assertTrue(any("aa" in p and "散落" in p for p in probs), probs)
        probs = prefix_problems(tree("b", [], ["tools/lib/bb"]), {"bb"}, 1)
        self.assertTrue(any("bb" in p and "已成套件" in p for p in probs), probs)
        cc = [f"tools/lib/cc_{c}.py" for c in "xyz"]
        dd = [f"tools/lib/dd_{c}.py" for c in "xyz"]
        probs = prefix_problems(tree("c", cc + dd), {"cc"}, 1)
        self.assertTrue(any("dd" in p and "新前綴" in p for p in probs), probs)
        self.assertFalse(any("cc" in p for p in probs))
        for name, roster in (("d", {"cc", "ee"}), ("e", set())):
            probs = prefix_problems(tree(name, cc), roster, 1)
            self.assertTrue(any("不相等" in p for p in probs), (name, probs))


class TestPackagesAndPrds(unittest.TestCase):
    def test_AT_134_3_1_real_packages_registered(self):
        self.assertEqual(package_problems(ROOT), [])
        self.assertTrue((ROOT / "tools/lib/selfimproving/__init__.py").is_file())
        root = synth("k1")
        write(root, "tools/lib/pkg1/__init__.py")
        make_ssot(root, [row(code="`tools/lib/pkg1/`")])
        self.assertEqual(package_problems(root), [])

    def test_AT_134_3_E_1_unregistered_package_red(self):
        root = synth("k2")
        write(root, "tools/lib/pkg1/__init__.py")
        write(root, "tools/lib/pkg2/__init__.py")
        make_ssot(root, [row(code="`tools/lib/pkg1/`")])
        probs = package_problems(root)
        self.assertTrue(len(probs) == 1 and "pkg2" in probs[0] and "pkg1" not in probs[0], probs)
        make_ssot(root, [row(code="`tools/lib/pkg1/`", tests="`tools/lib/pkg2/`")])
        probs = package_problems(root)
        self.assertTrue(len(probs) == 1 and "pkg2" in probs[0], probs)

    def test_AT_134_4_1_prd_must_cite_ssot(self):
        self.assertEqual(prd_problems(ROOT), [])
        root = synth("d1")
        write(root, "docs/01_requirements/X_PRD.md", f"模組落點表\n見 {SSOT_REL}\n")
        write(root, "docs/01_requirements/Y_PRD.md", "沒有那個字樣\n")
        write(root, "docs/01_requirements/notes.md", "模組落點表（不以 _PRD.md 結尾）\n")
        self.assertEqual(prd_problems(root), [])

    def test_AT_134_4_E_1_missing_citation_red(self):
        root = synth("d2")
        write(root, "docs/01_requirements/Z_PRD.md", "## 模組落點表\n\n| 內容 | 落點 |\n")
        probs = prd_problems(root)
        self.assertTrue(len(probs) == 1 and "Z_PRD.md" in probs[0], probs)
        write(root, "docs/01_requirements/Z_PRD.md", f"## 模組落點表\n\n依 {SSOT_REL}\n")
        self.assertEqual(prd_problems(root), [])


if __name__ == "__main__":
    unittest.main()
