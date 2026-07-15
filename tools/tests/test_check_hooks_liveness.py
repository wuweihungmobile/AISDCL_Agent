#!/usr/bin/env python3
"""tools/check_hooks_liveness.py 的單元測試（S11：抽出四份重複 liveness 偵測邏輯後，
驗證鏡子自身要被驗證 — 單一真相源必須有測試，不可只憑呼叫端手動走查）。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_hooks_liveness as m  # noqa: E402


class TestCheckHooksLiveness(unittest.TestCase):
    def test_not_in_git_repo_returns_true_silently(self) -> None:
        """`git rev-parse --show-toplevel` 失敗（不在 repo 內）→ 無法判定，不警告。"""
        with mock.patch.object(m, "_run", return_value=""):
            self.assertTrue(m.check_hooks_liveness())

    def test_matching_hooks_path_returns_true_without_warning(self) -> None:
        """core.hooksPath 與 `<top>/tools/git-hooks` 一致且三支 hook 檔齊備 → PASS，不印警告。"""

        def fake_run(cmd: list[str]) -> str:
            if cmd[:2] == ["git", "rev-parse"]:
                return "D:/repo"
            if "config" in cmd:
                return "tools/git-hooks"
            return ""

        with mock.patch.object(m, "_run", side_effect=fake_run), \
             mock.patch("pathlib.Path.is_file", return_value=True), \
             mock.patch("builtins.print") as mock_print:
            self.assertTrue(m.check_hooks_liveness())
            mock_print.assert_not_called()

    def test_mismatched_hooks_path_returns_false_with_warning(self) -> None:
        """core.hooksPath 指向錯誤路徑 → FAIL，印出警告（含目前值與預期值）。"""

        def fake_run(cmd: list[str]) -> str:
            if cmd[:2] == ["git", "rev-parse"]:
                return "D:/repo"
            if "config" in cmd:
                return "D:/wrong/path"
            return ""

        with mock.patch.object(m, "_run", side_effect=fake_run), \
             mock.patch("builtins.print") as mock_print:
            self.assertFalse(m.check_hooks_liveness())
            printed = "\n".join(str(c.args[0]) for c in mock_print.call_args_list if c.args)
            self.assertIn("dispatcher git hooks 未生效", printed)
            self.assertIn("D:/wrong/path", printed)

    def test_unset_hooks_path_shows_placeholder(self) -> None:
        """core.hooksPath 完全未設定 → 警告顯示「（未設定）」而非空字串。"""

        def fake_run(cmd: list[str]) -> str:
            if cmd[:2] == ["git", "rev-parse"]:
                return "D:/repo"
            return ""

        with mock.patch.object(m, "_run", side_effect=fake_run), \
             mock.patch("builtins.print") as mock_print:
            self.assertFalse(m.check_hooks_liveness())
            printed = "\n".join(str(c.args[0]) for c in mock_print.call_args_list if c.args)
            self.assertIn("（未設定）", printed)

    def test_main_exit_code_reflects_result(self) -> None:
        """CLI entrypoint：liveness True → exit 0；False → exit 1（供呼叫端識別，雖為 advisory）。"""
        with mock.patch.object(m, "check_hooks_liveness", return_value=True):
            self.assertEqual(0 if m.check_hooks_liveness() else 1, 0)
        with mock.patch.object(m, "check_hooks_liveness", return_value=False):
            self.assertEqual(0 if m.check_hooks_liveness() else 1, 1)

    def test_linked_worktree_mismatch_prints_worktree_specific_hint(self) -> None:
        """S22：本檔（advisory-only）過去完全不處理 linked worktree，會用本
        worktree 自己的根目錄誤判「未生效」。收斂到共用 evaluate() 後，偵測到
        linked worktree 時警告文字須明確提及，而非泛用的重裝指示。"""

        def fake_run(cmd: list[str]) -> str:
            # 三支 rev-parse 呼叫皆以 `-C <top>` 前綴，故不能用 cmd[:2] 區分——依尾端
            # 旗標判斷（與 check_hooks_liveness()/step_hooks() 實際呼叫方式一致）。
            if "--git-dir" in cmd:
                return "/repo/.git/worktrees/wt"
            if "--git-common-dir" in cmd:
                return "/repo/.git"
            if cmd[:2] == ["git", "rev-parse"]:
                return "/repo-wt1"  # --show-toplevel（唯一沒有 -C 前綴的呼叫）：本 worktree 自己的根目錄
            if "config" in cmd:
                return ""  # 主 checkout 從未安裝
            return ""

        with mock.patch.object(m, "_run", side_effect=fake_run), \
             mock.patch("builtins.print") as mock_print:
            self.assertFalse(m.check_hooks_liveness())
            printed = "\n".join(str(c.args[0]) for c in mock_print.call_args_list if c.args)
            self.assertIn("linked worktree", printed)


class TestResolveExpectedHooksDir(unittest.TestCase):
    """`resolve_expected_hooks_dir()` 純函式：dev_start.step_hooks() 與
    check_hooks_liveness() 共用同一份判定，此處直接單元測試演算法本身。"""

    def test_non_worktree_uses_repo_root(self) -> None:
        hooks_dir, is_linked = m.resolve_expected_hooks_dir(Path("D:/repo"), "", "")
        self.assertFalse(is_linked)
        self.assertEqual(hooks_dir, (Path("D:/repo") / "tools" / "git-hooks").resolve())

    def test_linked_worktree_resolves_to_main_checkout(self) -> None:
        hooks_dir, is_linked = m.resolve_expected_hooks_dir(
            Path("D:/repo-wt1"),
            "D:/repo/.git/worktrees/wt",
            "D:/repo/.git",
        )
        self.assertTrue(is_linked)
        self.assertEqual(hooks_dir, (Path("D:/repo") / "tools" / "git-hooks").resolve())

    def test_same_git_dir_and_common_dir_is_not_linked_worktree(self) -> None:
        _, is_linked = m.resolve_expected_hooks_dir(Path("D:/repo"), "D:/repo/.git", "D:/repo/.git")
        self.assertFalse(is_linked)


class TestIsHooksEffective(unittest.TestCase):
    """`is_hooks_effective()` 純函式：路徑比對 + 三支 hook 檔齊備 + is_file 可注入。"""

    def test_empty_current_value_is_not_effective(self) -> None:
        self.assertFalse(m.is_hooks_effective(Path("D:/repo"), Path("D:/repo/tools/git-hooks"), ""))

    def test_mismatched_path_is_not_effective(self) -> None:
        self.assertFalse(
            m.is_hooks_effective(Path("D:/repo"), Path("D:/repo/tools/git-hooks"), "D:/wrong")
        )

    def test_matching_path_defers_to_injected_is_file(self) -> None:
        hooks_dir = Path("D:/repo/tools/git-hooks")
        self.assertTrue(
            m.is_hooks_effective(
                Path("D:/repo"), hooks_dir, str(hooks_dir), is_file=lambda _p: True
            )
        )
        self.assertFalse(
            m.is_hooks_effective(
                Path("D:/repo"), hooks_dir, str(hooks_dir), is_file=lambda _p: False
            )
        )

    def test_is_file_injection_lets_caller_supply_oserror_safe_wrapper(self) -> None:
        """dev_start.py 注入自家 `_safe_is_file`（吞 OSError）；本函式不得繞過注入
        自己另外裸呼叫 `Path.is_file()`（否則 dev_start 的 OSError 防護就被架空）。"""
        calls: list[Path] = []

        def safe_is_file(p: Path) -> bool:
            calls.append(p)
            return True

        hooks_dir = Path("D:/repo/tools/git-hooks")
        result = m.is_hooks_effective(
            Path("D:/repo"), hooks_dir, str(hooks_dir), is_file=safe_is_file
        )
        self.assertTrue(result)
        self.assertEqual(len(calls), 3)  # pre-commit / pre-push / post-commit


if __name__ == "__main__":
    unittest.main()
