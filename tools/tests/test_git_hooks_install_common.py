#!/usr/bin/env python3
"""tools/git_hooks_install_common.py 的單元測試（獨立複審 finding 落地）。

WHY：獨立複審發現這支「單一真相源」新模組完全沒有函式級單元測試，也沒有被既有
的雙軌漂移防護（check_script_parity.py / check_wrapper_thinness.py）涵蓋——本檔
直接補上函式級單元測試（含 is_hooks_path_installed 的 cwd 獨立性回歸鎖）+ CLI
子指令 smoke test，並對兩份呼叫端薄殼（tools/lib/GitHooksInstallCommon.ps1、
tools/lib/git_hooks_install_common.sh）做一道自成一體的輕量薄殼守門（不與
check_wrapper_thinness.py 共用資料結構，避免為了收納這對檔案而改動已穩定的
dev_start 對子行數上限，降低變更風險）。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import git_hooks_install_common as m  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LIB_DIR = _REPO_ROOT / "tools" / "lib"
_PS1_WRAPPER = _LIB_DIR / "GitHooksInstallCommon.ps1"
_SH_WRAPPER = _LIB_DIR / "git_hooks_install_common.sh"


def _make_hooks_dir(tmp: Path, *, complete: bool = True) -> Path:
    hooks_dir = tmp / "git-hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    names = m.HOOK_FILENAMES if complete else m.HOOK_FILENAMES[:2]
    for name in names:
        (hooks_dir / name).write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    return hooks_dir


class TestIsLinkedWorktree(unittest.TestCase):
    def test_same_dir_not_linked(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self.assertFalse(m.is_linked_worktree(td, td))

    def test_different_dir_is_linked(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            other = Path(td) / "sub"
            other.mkdir()
            self.assertTrue(m.is_linked_worktree(td, str(other)))


class TestMissingHookFiles(unittest.TestCase):
    def test_complete_hooks_dir_reports_none_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            hooks_dir = _make_hooks_dir(Path(td), complete=True)
            self.assertEqual(m.missing_hook_files(hooks_dir), [])

    def test_incomplete_hooks_dir_reports_missing_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            hooks_dir = _make_hooks_dir(Path(td), complete=False)
            self.assertEqual(m.missing_hook_files(hooks_dir), ["post-commit"])


class TestIsHooksPathInstalled(unittest.TestCase):
    def test_empty_current_value_not_installed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            hooks_dir = _make_hooks_dir(Path(td))
            self.assertFalse(m.is_hooks_path_installed(Path(td), hooks_dir, ""))

    def test_absolute_current_value_matching_hooks_dir_installed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            hooks_dir = _make_hooks_dir(Path(td))
            self.assertTrue(
                m.is_hooks_path_installed(Path(td), hooks_dir, str(hooks_dir))
            )

    def test_missing_hook_file_not_installed_even_if_path_matches(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            hooks_dir = _make_hooks_dir(Path(td), complete=False)
            self.assertFalse(
                m.is_hooks_path_installed(Path(td), hooks_dir, str(hooks_dir))
            )

    def test_relative_current_value_resolved_against_repo_root_not_cwd(self) -> None:
        """獨立複審回歸鎖：core.hooksPath 存相對路徑時，判定結果不可依呼叫時的
        cwd 而異——必須固定相對 repo_root 解讀（比照 check_hooks_liveness.py 的
        is_hooks_effective() 已有的正確行為）。

        真的切換 cwd 呼叫兩次（R9 跨平台複審修正：舊版同輸入同 cwd 連呼兩次
        assertEqual 恆真，鎖不住任何退化）：若實作退化為依 cwd 解析相對路徑
        （如 `Path(current_value).resolve()`），第一次呼叫（cwd＝repo 根）仍 True、
        第二次（cwd＝無關目錄）轉 False → assertEqual 轉紅。"""
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td) / "repo"
            repo_root.mkdir()
            hooks_dir = _make_hooks_dir(repo_root / "tools")  # -> repo_root/tools/git-hooks
            relative_value = "tools/git-hooks"
            unrelated_cwd = Path(td) / "unrelated"
            unrelated_cwd.mkdir()

            original_cwd = os.getcwd()
            try:
                os.chdir(repo_root)
                result_a = m.is_hooks_path_installed(repo_root, hooks_dir, relative_value)
                os.chdir(unrelated_cwd)
                result_b = m.is_hooks_path_installed(repo_root, hooks_dir, relative_value)
            finally:
                os.chdir(original_cwd)
            self.assertTrue(result_a)
            self.assertEqual(result_a, result_b)

    def test_relative_current_value_wrong_repo_root_not_installed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            hooks_dir = _make_hooks_dir(repo_root / "tools")  # -> repo_root/tools/git-hooks
            wrong_root = repo_root / "not-the-repo-root"
            wrong_root.mkdir()
            self.assertFalse(
                m.is_hooks_path_installed(wrong_root, hooks_dir, "tools/git-hooks")
            )


class TestCliSmoke(unittest.TestCase):
    """對真實 repo（本檔所在 repo）跑 CLI 子指令，確認基本行為正常（唯讀操作）。"""

    def test_get_hooks_dir_prints_absolute_path_under_real_repo(self) -> None:
        result = subprocess.run(
            [sys.executable, str(_REPO_ROOT / "tools" / "git_hooks_install_common.py"),
             "get-hooks-dir"],
            cwd=str(_REPO_ROOT), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        printed = Path(result.stdout.strip())
        self.assertTrue(printed.is_absolute())
        self.assertTrue(str(printed).replace("\\", "/").endswith("tools/git-hooks"))

    def test_check_installed_prints_cur_and_ok_lines(self) -> None:
        hooks_dir = str((_REPO_ROOT / "tools" / "git-hooks").resolve())
        result = subprocess.run(
            [sys.executable, str(_REPO_ROOT / "tools" / "git_hooks_install_common.py"),
             "check-installed", hooks_dir],
            cwd=str(_REPO_ROOT), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.strip().splitlines()
        self.assertTrue(any(line.startswith("CUR=") for line in lines))
        self.assertTrue(any(line.startswith("OK=") for line in lines))


class TestCliNonAsciiRepoPathEncoding(unittest.TestCase):
    """R9 跨平台複審回歸鎖：`_run()` 的 subprocess 必須顯式 `encoding="utf-8"`。

    未顯式指定時 `text=True` 走 locale（zh-TW Windows 無 PYTHONUTF8 ＝ cp950），
    git 輸出的 UTF-8 非 ASCII repo 路徑會 UnicodeDecodeError → get-hooks-dir 假報
    「不在 git repo 內」、check-installed 靜默退回 cwd 推算。以剝除 PYTHONUTF8／
    PYTHONIOENCODING 的子行程環境重現；POSIX 下 locale 天然 UTF-8 不會炸，
    但 rc=0 + 路徑正確的斷言仍有效。"""

    def _make_non_ascii_fake_repo(self, td: str) -> tuple[Path, Path]:
        repo = Path(td) / "中文測試repo"
        hooks_dir = repo / "tools" / "git-hooks"
        hooks_dir.mkdir(parents=True)
        for name in m.HOOK_FILENAMES:
            (hooks_dir / name).write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(repo)], check=True, timeout=30)
        subprocess.run(
            ["git", "-C", str(repo), "config", "core.hooksPath", "tools/git-hooks"],
            check=True, timeout=10,
        )
        return repo, hooks_dir

    @staticmethod
    def _env_without_utf8_overrides() -> dict[str, str]:
        return {k: v for k, v in os.environ.items()
                if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}

    def test_get_hooks_dir_on_non_ascii_repo_without_pythonutf8(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo, hooks_dir = self._make_non_ascii_fake_repo(td)
            result = subprocess.run(
                [sys.executable, str(_REPO_ROOT / "tools" / "git_hooks_install_common.py"),
                 "get-hooks-dir"],
                cwd=str(repo), env=self._env_without_utf8_overrides(),
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(Path(result.stdout.strip()), hooks_dir.resolve())

    def test_check_installed_from_subdir_on_non_ascii_repo_without_pythonutf8(self) -> None:
        # cwd 刻意設在 repo 子目錄：修復前 --show-toplevel 解碼崩潰會退回
        # Path.cwd()（＝子目錄）推算 repo 根 → OK=0 假陰性；修復後 OK=1。
        with tempfile.TemporaryDirectory() as td:
            repo, hooks_dir = self._make_non_ascii_fake_repo(td)
            result = subprocess.run(
                [sys.executable, str(_REPO_ROOT / "tools" / "git_hooks_install_common.py"),
                 "check-installed", str(hooks_dir.resolve())],
                cwd=str(repo / "tools"), env=self._env_without_utf8_overrides(),
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            lines = result.stdout.strip().splitlines()
            self.assertIn("OK=1", lines)


class TestWrapperThinnessGuard(unittest.TestCase):
    """輕量薄殼守門：兩份呼叫端（.ps1/.sh）只該是「轉呼叫本檔 CLI 子指令」的薄殼。

    刻意只守「行數上限」、不比照 check_wrapper_thinness.py 用關鍵字黑名單：這對
    wrapper 本質是「呼叫 subprocess → 解析其結構化 stdout（CUR=/OK= 兩行）」，
    解析 stdout 天生需要迴圈（如 `foreach ($line in $lines)`），這是合理的呈現層
    工作、不是業務邏輯外溢——若對這裡也套用迴圈關鍵字黑名單，會誤中本來就合法的
    現有內容（實測重現：直接沿用 dev_start 的黑名單會誤判 `foreach (` 這行）。
    真正該守的是「兩支腳本是否重新長出 git 偵測/路徑判定邏輯本身」，但這類語意
    無法用簡單子字串黑名單可靠窮舉（同一輪 SD 複審對 check_wrapper_thinness.py
    黑名單式做法的批評同樣適用於此），改用行數上限作為早期示警訊號已足夠：
    真正重新實作判定邏輯必然大幅增加行數。"""

    _PS1_MAX_LINES = 150
    _SH_MAX_LINES = 100

    def test_ps1_wrapper_within_line_budget(self) -> None:
        text = _PS1_WRAPPER.read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), self._PS1_MAX_LINES)

    def test_sh_wrapper_within_line_budget(self) -> None:
        text = _SH_WRAPPER.read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), self._SH_MAX_LINES)


if __name__ == "__main__":
    unittest.main()
