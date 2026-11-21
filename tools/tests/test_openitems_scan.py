"""tools/lib/openitems/scan.py（A1；TCS-WorkProgress REQ-WP-04、AT-WP-05、E2E-WP-01 的入口面）。

WHY：掃描器決定「哪些待驗標記沒有 OI 認領」，A8 以它對帳 143 處標記、REQ-WP-23 的 CI 鎖以它擋新
漏網。所以測的是會讓對帳說謊的方向：定義文件被當使用處、glob 漏掉／多掉目錄、一行多標記重複計、
帶 id 與不帶 id 對調。縫：真檔案系統暫存根、真 CLI 子行程；git 母體另以真 `git init` 夾具驗。
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "tools"))
sys.path.insert(0, str(_REPO / "tools" / "lib"))

from lib.openitems import params, scan  # noqa: E402

CLI = _REPO / "tools" / "openitems.py"
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _rmtree(path: Path) -> None:
    """含 `git init` 產物的暫存根：.git 內的物件檔唯讀，Windows 上 `ignore_errors` 會留下殘骸。"""
    def _force(func, target, _exc):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    shutil.rmtree(path, onerror=_force)


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class ScanTest(unittest.TestCase):
    """受測：`tools/lib/openitems/scan.py`。"""
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="oi_scan_"))
        self.addCleanup(_rmtree, self.root)
        dest = self.root / params.PARAMS_REL
        dest.parent.mkdir(parents=True)
        shutil.copyfile(_REPO / params.PARAMS_REL, dest)
        self.params = params.load(self.root)
        self.definer = self.params["vocabulary_definers"][0]

    def test_mapped_unmapped_and_definers_are_classified(self):
        # AT-WP-05：帶 id＝mapped、不帶＝unmapped、definers 內的檔不計
        write(self.root, "docs/a.md", "待真機 OI-20261119-001\n乾淨行\n仍待真機 沒有 id\n")
        write(self.root, self.definer, "待真機 這裡是詞彙定義\n")
        hits = scan.scan(self.root, self.params)
        self.assertEqual([(h.path, h.line, h.mapped) for h in hits],
                         [("docs/a.md", 1, True), ("docs/a.md", 3, False)])
        self.assertEqual(scan.summary_line(hits), "OPENITEMS_SCAN=mapped=1 unmapped=1")

    def test_glob_covers_nested_docs_and_root_claude_md_but_not_other_trees(self):
        # 反向變體：tools/ 底下與非 .md 檔不掃；docs/ 任意深度、根 CLAUDE.md 要掃
        write(self.root, "docs/x/y/z.md", "待驗\n")
        write(self.root, "CLAUDE.md", "待目視\n")
        write(self.root, "tools/note.md", "待驗\n")
        write(self.root, "docs/data.json", "待驗\n")
        got = sorted(h.path for h in scan.scan(self.root, self.params))
        self.assertEqual(got, ["CLAUDE.md", "docs/x/y/z.md"])

    def test_one_line_with_several_markers_counts_once(self):
        write(self.root, "docs/a.md", "待真機且待掌舵者目視，另外待驗\n")
        self.assertEqual(len(scan.scan(self.root, self.params)), 1)

    def test_glob_regex_semantics(self):
        rx = scan.glob_to_regex("docs/**/*.md")
        self.assertTrue(rx.match("docs/a.md"))
        self.assertTrue(rx.match("docs/a/b/c.md"))
        self.assertFalse(rx.match("docs/a/b/c.txt"))
        self.assertFalse(rx.match("other/docs/a.md"))
        self.assertFalse(scan.glob_to_regex("*.md").match("docs/a.md"))  # `*` 不跨 /

    def test_git_tracked_population_excludes_untracked_files(self):
        # 母體＝git 追蹤檔：未追蹤的檔不掃（反向：不在 git 工作樹時才退回檔案系統，上面各測已涵蓋）
        git = ["git", "-C", str(self.root)]
        subprocess.run([*git, "init", "-q"], check=True, creationflags=NOWIN)
        write(self.root, "docs/tracked.md", "待驗\n")
        write(self.root, "docs/untracked.md", "待驗\n")
        subprocess.run([*git, "add", "docs/tracked.md"], check=True, creationflags=NOWIN)
        self.assertEqual([h.path for h in scan.scan(self.root, self.params)], ["docs/tracked.md"])


class ScanCliTest(unittest.TestCase):
    """受測：`tools/openitems.py` 的 `scan` 動詞（`tools/lib/openitems/scan.py`）。"""
    def test_cli_scan_last_line_format_and_rc0_on_real_repo(self):
        # E2E-WP-01 的入口面（真 repo、真子行程）：rc 0、末行格式固定；unmapped 只是資訊不是錯誤。
        # 與 ARC E6 的 143 處／61 檔逐條對帳由 A8 種子階段做（本棒不寫帳本）。
        proc = subprocess.run([sys.executable, str(CLI), "scan"], text=True, capture_output=True,
                              encoding="utf-8", timeout=240, creationflags=NOWIN, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertRegex(proc.stdout.splitlines()[-1],
                         r"^OPENITEMS_SCAN=mapped=\d+ unmapped=\d+$")

    def test_cli_scan_on_sandbox_reports_expected_counts(self):
        root = Path(tempfile.mkdtemp(prefix="oi_scancli_"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        dest = root / params.PARAMS_REL
        dest.parent.mkdir(parents=True)
        shutil.copyfile(_REPO / params.PARAMS_REL, dest)
        write(root, "docs/a.md", "待驗 OI-20261119-002\n待驗\n待驗\n")
        proc = subprocess.run([sys.executable, str(CLI), "--root", str(root), "scan"], text=True,
                              capture_output=True, encoding="utf-8", timeout=120,
                              creationflags=NOWIN, check=False)
        self.assertEqual(proc.stdout.splitlines()[-1], "OPENITEMS_SCAN=mapped=1 unmapped=2")


if __name__ == "__main__":
    unittest.main()
