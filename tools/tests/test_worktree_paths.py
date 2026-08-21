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

import ntpath
import os
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


if __name__ == "__main__":
    unittest.main()
