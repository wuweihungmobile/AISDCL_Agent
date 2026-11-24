#!/usr/bin/env python
"""`tools/lib/worktree_paths.py` 的回歸鎖（P0-1）。

WHY：R96 版 `.claude/hooks/block_destructive_git.py` 對「這是不是拋棄式
worktree」做**純字串包含**判斷，不解析 `..`——`<root>/.claude/worktrees/../../X`
這種路徑，`realpath` 後其實落在拋棄式樹**之外**（甚至可以是專案根自己），卻因為
字面上仍帶著 `.claude/worktrees` 這段子字串而被誤判放行，讓 `git worktree remove
--force` 的保護臂可以被 `..` 包裝繞過。本檔鎖住抽出來的
`is_under_disposable_worktree()`：正確放行拋棄式樹本身與其底下的目標、正確擋下
`..` 穿越出去的目標，且混合分隔符／NTFS 大小寫不敏感兩格在**兩個平台**都真的
走得進去——以 `ntpath` 顯式注入 Windows 語意（`ntpath.realpath` 在沒有 `nt` 模組
時會退化成純字面 `normpath`／`abspath`，不摸磁碟，CPython `ntpath.py` 原始碼確認
過這條路徑，所以 mac／Linux CI 上也真的走進這兩格，不是只在 Windows 才觸發）。
"""
from __future__ import annotations

import contextlib
import ntpath
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
import worktree_paths as WT  # noqa: E402


class TestIsUnderDisposableWorktree(unittest.TestCase):
    """真實磁碟情境：用 tempdir 當專案根，走**未 mock** 的原生 realpath／normcase。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wtp-root-")
        self.addCleanup(self._tmp.cleanup)
        self.root = os.path.realpath(self._tmp.name)
        self.wt_dir = os.path.join(self.root, ".claude", "worktrees")
        os.makedirs(self.wt_dir, exist_ok=True)
        env = mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": self.root})
        env.start()
        self.addCleanup(env.stop)

    def test_a_leaf_under_the_disposable_root_is_recognized(self) -> None:
        self.assertTrue(WT.is_under_disposable_worktree(
            os.path.join(self.wt_dir, "agent-x")))

    def test_the_disposable_root_itself_is_recognized(self) -> None:
        self.assertTrue(WT.is_under_disposable_worktree(self.wt_dir))

    def test_a_sibling_that_merely_shares_the_prefix_is_not_recognized(self) -> None:
        """`…/.claude/worktrees_extra` 不是 `…/.claude/worktrees` 的子目錄——子字串
        包含判準（R96 版）會誤判為真，前綴（+ 分隔符）判準必須判假。"""
        self.assertFalse(WT.is_under_disposable_worktree(self.wt_dir + "_extra"))

    def test_dotdot_traversal_out_of_the_disposable_root_is_rejected(self) -> None:
        """P0-1 案例①：字面上帶著拋棄式樹前綴，`..` 解開後其實落在樹外。"""
        outside = os.path.join(self.wt_dir, "..", "..", "AutoClaude")
        direct = os.path.join(self.root, "AutoClaude")
        self.assertEqual(os.path.realpath(outside), os.path.realpath(direct),
                          "前提不成立：兩者 realpath 後應相同，測的才是同一個繞行")
        self.assertFalse(WT.is_under_disposable_worktree(outside))

    def test_dotdot_traversal_onto_the_project_root_is_rejected(self) -> None:
        """P0-1 案例②：`..` 穿越回專案根自己（對它跑 `remove --force` 等於刪 repo 根）。"""
        outside = os.path.join(self.wt_dir, "..", "..")
        self.assertEqual(os.path.realpath(outside), self.root)
        self.assertFalse(WT.is_under_disposable_worktree(outside))

    def test_empty_input_fails_closed(self) -> None:
        self.assertFalse(WT.is_under_disposable_worktree(""))


class TestCrossPlatformSeparatorAndCaseHandling(unittest.TestCase):
    """不摸磁碟：全程注入 `ntpath` 語意，讓 mac／Linux CI 也真的走進這幾格。"""

    _FAKE_ROOT = r"C:\Fake\WtpRepo123"  # platform-ok: 全程注入 ntpath 語意，不摸原生
    # os.path（見 setUp），需要真 Windows 磁碟機字面值才測得到，POSIX 上同樣安全

    def setUp(self) -> None:
        env = mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": self._FAKE_ROOT})
        env.start()
        self.addCleanup(env.stop)
        # 🔴 整包換掉 `os.path`（不是逐個函式換）：逐個換會漏掉分隔符那一格而造出
        # 「路徑是 \ 、分隔符是 /」的混血平台 ⇒ 判準對不上、mac 上假紅。整包換之後
        # 「只換一半」在結構上不可能發生，這才是把錯誤類別消掉而非只修實例。
        ntpath_patch = mock.patch.object(WT.os, "path", ntpath)
        ntpath_patch.start()
        self.addCleanup(ntpath_patch.stop)

    def test_mixed_separators_are_recognized(self) -> None:
        mixed = self._FAKE_ROOT + "/.claude/worktrees/agent-x"
        self.assertTrue(WT.is_under_disposable_worktree(mixed))

    def test_ntfs_case_insensitivity_is_recognized(self) -> None:
        upper = self._FAKE_ROOT + "\\.CLAUDE\\WORKTREES\\agent-x"
        self.assertTrue(WT.is_under_disposable_worktree(upper))

    def test_the_dotdot_traversal_fix_still_holds_under_ntpath_semantics(self) -> None:
        outside = self._FAKE_ROOT + r"\.claude\worktrees\..\..\AutoClaude"
        self.assertFalse(WT.is_under_disposable_worktree(outside))


class TestRglobLiveSkipsAgentWorktreeCopies(unittest.TestCase):
    """DEF-200-647：Agent 工具 `isolation: worktree` 把整份 repo 副本建在
    `<repo>/.claude/worktrees/<name>/`；全 repo 檔案系統掃描器把它當本體掃（2026-11-24 nightly
    6 紅、主樹 `{'live': 1205} != {'live': 37}`）。受測：`tools/lib/worktree_paths.py` 的
    `rglob_live`（唯一排除入口）與四支真實掃描器在「有／無假副本」時結果相同。"""

    _LIVE = ("tools/real.py", ".claude/hooks/h.py", "tools/s.ps1", "top.ps1", "tools/lib/q.sh")

    @staticmethod
    def _rels(root: Path, paths) -> set[str]:
        return {p.relative_to(root).as_posix() for p in paths}

    def _make_repo(self, with_copy: bool) -> Path:
        tmp = tempfile.TemporaryDirectory(prefix="wtp-scan-")
        self.addCleanup(tmp.cleanup)
        root = Path(os.path.realpath(tmp.name))
        for rel in self._LIVE:
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text("x = 1\n", encoding="utf-8")
        if with_copy:
            copy = root / ".claude" / "worktrees" / "agent-x"
            for rel in self._LIVE:
                (copy / rel).parent.mkdir(parents=True, exist_ok=True)
                (copy / rel).write_text("x = 1\n", encoding="utf-8")
            (copy / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
        return root

    def test_the_fixture_really_reproduces_the_bug_with_a_plain_rglob(self) -> None:
        """對照組：裸 `rglob` 在這份夾具上**確實**把副本掃進來（否則下面的鎖是空轉）。"""
        root = self._make_repo(with_copy=True)
        self.assertTrue(any("worktrees" in p.parts for p in root.rglob("*.py")))

    def test_rglob_live_equals_the_scan_of_a_repo_without_the_copy(self) -> None:
        with_copy, without = self._make_repo(True), self._make_repo(False)
        for pattern in ("*.py", "*.ps1", "*"):
            with self.subTest(pattern=pattern):
                got = self._rels(with_copy, WT.rglob_live(with_copy, pattern))
                want = self._rels(without, without.rglob(pattern))
                self.assertEqual(got, want)
                self.assertTrue(got, "空集合比對恆綠")

    def test_base_narrowing_to_dot_claude_also_skips_the_copy(self) -> None:
        root = self._make_repo(True)
        got = self._rels(root, WT.rglob_live(root, "*.py", root / ".claude"))
        self.assertEqual(got, {".claude/hooks/h.py"})

    def test_exclusion_is_anchored_at_the_repo_root_and_case_insensitive(self) -> None:
        self.assertTrue(WT.is_disposable_worktree_rel((".claude", "worktrees", "a", "b.py")))
        self.assertTrue(WT.is_disposable_worktree_rel((".Claude", "WorkTrees")))
        self.assertFalse(WT.is_disposable_worktree_rel(("docs", ".claude", "worktrees", "b.py")),
                         "只排除 repo 根的那一個；別處同名路徑照常掃")
        self.assertFalse(WT.is_disposable_worktree_rel((".claude", "hooks", "h.py")))
        self.assertFalse(WT.is_disposable_worktree_rel(()))

    def test_the_real_scanners_ignore_a_worktree_copy(self) -> None:
        """真實掃描器（不是本函式的替身）：把各模組的 `_REPO_ROOT` 指到夾具 repo，有副本與無副本
        的結果必須一致、且不含任何 `worktrees` 路徑。涵蓋 2026-11-24 nightly 的六處斷言與
        同型的全 repo 掃描面。"""
        import test_check_hooks_liveness as hl  # noqa: PLC0415
        import test_mac_endurance_r83 as mac  # noqa: PLC0415
        import test_platform_neutral_paths as pn  # noqa: PLC0415
        import test_python_c_percent_shim as shim  # noqa: PLC0415

        def rel(root: Path, items) -> list[str]:
            return sorted(str(i).replace("\\", "/") if isinstance(i, str)
                          else Path(i).relative_to(root).as_posix() for i in items)

        results: dict[bool, dict[str, list[str]]] = {}
        for with_copy in (True, False):
            root = self._make_repo(with_copy)
            with contextlib.ExitStack() as stack:
                for mod, attr in ((pn, "_REPO_ROOT"), (hl, "_REPO_ROOT"),
                                  (mac, "_REPO_ROOT"), (shim, "_ROOT")):
                    stack.enter_context(mock.patch.object(mod, attr, root))
                results[with_copy] = {
                    "pathext": rel(root, pn._pathext_scan_files()),
                    "action": rel(root, hl._action_scan_sources()),
                    "carrier": rel(root, mac._carrier_scan_surface()),
                    "consumers": rel(root, mac._outside_consumers("nothing")),
                    "ps1": rel(root, shim._iter_ps1_files()),
                }
        for name, got in results[True].items():
            with self.subTest(scanner=name):
                self.assertEqual(got, results[False][name], f"{name}：副本改變了掃描結果")
                self.assertFalse([p for p in got if "worktrees" in p], f"{name}：掃進了副本")
        self.assertTrue(results[False]["pathext"] and results[False]["ps1"],
                        "夾具沒有東西可掃＝上面的相等是空轉")

    def test_no_test_walks_the_repo_root_with_a_bare_rglob(self) -> None:
        """結構鎖：`tools/tests` 與 `tools/lib` 不得再出現「repo 根名稱直接 `.rglob(`」——全 repo
        掃描一律走 `worktree_paths.rglob_live`（新掃描器照抄舊寫法就是這個缺陷的復發路徑）。
        子樹（`tools/`、`tools/lib/`…）的 `rglob` 不在此限：副本不在其下。"""
        bare = re.compile(r"\b(?:_REPO_ROOT|_ROOT|REPO_ROOT|_REPO|repo_root)\.rglob\(")
        offenders = []
        for tree in (_REPO_ROOT / "tools" / "tests", _REPO_ROOT / "tools" / "lib"):
            for py in sorted(tree.rglob("*.py")):
                if "__pycache__" in py.parts:
                    continue
                text = py.read_text(encoding="utf-8")
                for n, line in enumerate(text.splitlines(), start=1):
                    if bare.search(line) and not line.lstrip().startswith("#"):
                        offenders.append(f"{py.relative_to(_REPO_ROOT).as_posix()}:{n}")
        offenders = [o for o in offenders if not o.startswith("tools/tests/test_worktree_paths.py")]
        self.assertEqual(offenders, [], "全 repo 掃描請改用 rglob_live（DEF-200-647）")


if __name__ == "__main__":
    unittest.main()
