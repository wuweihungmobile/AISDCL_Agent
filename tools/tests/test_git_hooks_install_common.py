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
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path, PureWindowsPath
from unittest import mock

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


def _usable_bash() -> str | None:
    """回傳可跑 repo bash 腳本的 bash 路徑；只有 WSL 佔位 bash 或無 bash → None。

    邏輯鏡自 AISDLC_SDD/scripts/bash_probe.py（該檔是子專案 scripts/tests 的
    SSOT，tools/tests/test_pre_push_dispatcher.py 已有同款鏡）；根層 tools/tests
    刻意不跨子專案 import——子專案檔案搬移不應弄壞根層閘門。若該檔邏輯更新，
    請三處同步。裸 `shutil.which("bash")` 在本機常誤中 Windows CreateProcess
    搜尋順序優先於 PATH 的 `C:\\Windows\\System32\\bash.exe`（WSL 佔位，完全不同
    的檔案系統視角，會讓本檔案案 Windows 側路徑一律「找不到檔案」而非真失敗）。

    R31 Scan-B 修復：System32 排除改用 `PureWindowsPath` 逐段精確比對（對齊
    `tools/integration_gate_core.py::_has_system32_segment()`，DEF-101-236），
    不再用任意子字串命中即排除（會誤傷路徑含 "system32" 子字串但非該目錄段的
    合法候選）。
    """
    candidates: list[str] = []
    git = shutil.which("git")
    if git:
        gp = Path(git).resolve()
        for up in list(gp.parents)[:4]:
            for sub in ("usr/bin/bash.exe", "bin/bash.exe"):
                c = up / sub
                if c.exists():
                    candidates.append(str(c))
    bare = shutil.which("bash")
    if bare and not any(part.lower() == "system32" for part in PureWindowsPath(bare).parts):
        candidates.append(bare)
    for cand in candidates:
        try:
            r = subprocess.run(
                [cand, "-c", "echo ok"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=15,
            )
            if r.returncode == 0 and r.stdout.strip() == "ok":
                return cand
        except Exception:
            continue
    return None


class TestUsableBashSystem32Guard(unittest.TestCase):
    """R31 QA 一審必修條件 2：`_usable_bash()` 是本檔鏡射自 `bash_probe.py` 的獨立
    副本，先前只被當成 `skipif` 用的基礎設施函式呼叫，沒有任何 case 直接斷言其
    System32 排除邏輯本身——QA 親驗證實把 guard 改回舊版寬鬆判斷時，本檔既有
    20 個測試全數依然通過（因為它們都走 `skipif`，guard 壞掉只會讓更多測試被
    跳過而非變紅）。本類別補上直接呼叫點回歸鎖，比照
    `AISDLC_SDD/scripts/tests/test_bash_probe.py::TestUsableBashSystem32Guard`
    既有慣例。"""

    def test_skips_wsl_system32_placeholder(self) -> None:
        """`_usable_bash()` 呼叫點層級回歸鎖：PATH 上的 bash 是 WSL System32
        佔位（完整路徑段）時必須被排除、不得進入 subprocess.run 探測。"""
        with (
            mock.patch.object(shutil, "which") as mock_which,
            mock.patch.object(subprocess, "run") as mock_run,
        ):
            mock_which.side_effect = lambda name: (
                r"C:\Windows\System32\bash.exe" if name == "bash" else None  # platform-ok: mock 回傳值
            )
            result = _usable_bash()
        mock_run.assert_not_called()
        self.assertIsNone(result, "WSL System32 佔位 bash 應被排除、不應嘗試 subprocess.run")

    def test_does_not_reject_substring_false_positive_path(self) -> None:
        """R31 bug-injection 標的：路徑含 'system32' 子字串但非完整路徑段的合法
        候選（如 `C:\\MySystem32Tools\\bash.exe`）不應被誤排除——若退化回舊版
        `"system32" not in bare.lower()` 寬鬆判斷，本測試須變紅。"""
        legit_path = r"C:\MySystem32Tools\bash.exe"  # platform-ok: mock 回傳值，非真實檔案路徑
        with (
            mock.patch.object(shutil, "which") as mock_which,
            mock.patch.object(subprocess, "run") as mock_run,
        ):
            mock_which.side_effect = lambda name: legit_path if name == "bash" else None
            mock_run.return_value = mock.Mock(returncode=0, stdout="ok\n")
            result = _usable_bash()
        self.assertEqual(result, legit_path)


_USABLE_BASH = _usable_bash()


class TestDotSourceTrapSafety(unittest.TestCase):
    """DEF-101-261 回歸鎖：兩份共用庫的 .EXAMPLE/用法示範直接互動式 dot-source／
    source，內部驗證失敗分支歷史上直接裸 exit 1——若使用者真的照做並命中失敗
    分支，會把整個互動 shell 關掉。修復後須雙向驗證：

    1. 生產情境（子行程/獨立腳本方式呼叫，如 `bash caller.sh` / `powershell -File
       caller.ps1`）：失敗時仍必須 exit 1 終止整個行程——既有行為零改變的回歸鎖，
       防止「不誤殺互動 shell」的修復意外退化成「生產路徑靜默略過繼續執行」。
    2. 互動情境（無外層腳本檔，直接以 `bash -c` / `powershell -Command` source／
       dot-source 本檔後呼叫函式）：失敗時必須 return 而非 exit——同一 shell
       之後的指令仍須能繼續執行（不誤殺使用者 shell）。
    """

    @staticmethod
    def _run(cmd: list[str], cwd: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30,
        )

    @unittest.skipIf(_USABLE_BASH is None, "需要非 WSL 佔位的可用 bash")
    def test_sh_script_driven_failure_still_terminates_whole_process(self) -> None:
        # ignore_cleanup_errors：Windows 上 bash.exe 以此目錄為 cwd 結束後，OS 偶爾
        # 會延遲釋放目錄 handle（與本測試邏輯無關的環境雜訊），寬容跳過清理失敗。
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
            non_git_dir = Path(td) / "not_a_repo"
            non_git_dir.mkdir()
            caller = Path(td) / "caller.sh"
            caller.write_text(
                "#!/usr/bin/env bash\n"
                f'source "{_SH_WRAPPER.as_posix()}"\n'
                'assert_not_linked_worktree "[t] "\n'
                "echo SHOULD_NOT_PRINT\n",
                encoding="utf-8",
            )
            # Windows Git Bash 吃正斜線絕對路徑（C:/...），反斜線會被當跳脫（既有
            # contract 慣例，見 test_ntfs_length_gate.py 的 hook.replace 同款處理）。
            proc = self._run(
                [_USABLE_BASH, str(caller).replace("\\", "/")], cwd=str(non_git_dir)
            )
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertNotIn("SHOULD_NOT_PRINT", proc.stdout)

    @unittest.skipIf(_USABLE_BASH is None, "需要非 WSL 佔位的可用 bash")
    def test_sh_interactive_style_failure_does_not_kill_shell(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
            non_git_dir = Path(td) / "not_a_repo"
            non_git_dir.mkdir()
            script = (
                f'source "{_SH_WRAPPER.as_posix()}"; '
                'assert_not_linked_worktree "[t] "; '
                "echo STILL_ALIVE"
            )
            proc = self._run([_USABLE_BASH, "-c", script], cwd=str(non_git_dir))
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("STILL_ALIVE", proc.stdout)

    @unittest.skipIf(
        shutil.which("powershell") is None and shutil.which("pwsh") is None,
        "需要 powershell/pwsh",
    )
    def test_ps1_top_level_python_missing_script_driven_terminates_process(
        self,
    ) -> None:
        """R23 SA/QA 必修條件回歸鎖：模組**頂層**（不在任何函式內）「找不到
        python」檢查歷史上用裸 `exit 1`——PowerShell 對「被 dot-source 的巢狀
        腳本頂層本體」呼叫 exit 的作用域規則是只終止該巢狀腳本自身的載入，不
        終止外層真正呼叫它的腳本／行程（與本檔其餘 3 個失敗分支不同——那些都
        在函式內，exit 語意正確）。若退化為裸 `exit 1`，script-driven 情境下
        呼叫端（install_git_hooks.ps1 等）會不受阻擋繼續往下跑，之後才因不相關
        錯誤失敗甚至以 exit 0 收尾，違反 fail-loud。

        用清空 PATH（換成保證不含 python.exe 的空目錄）讓 `Get-Command python`
        真的找不到 python，以 `-File` 呼叫端（模擬生產 dot-source 鏈路）斷言
        整個呼叫行程 exit code 非 0，且 dot-source 之後的陳述式不會被執行到。
        """
        exe = shutil.which("powershell") or shutil.which("pwsh")
        with tempfile.TemporaryDirectory() as td:
            caller = Path(td) / "caller.ps1"
            caller.write_text(
                f'. "{_PS1_WRAPPER}"\n'
                "Write-Host 'SHOULD_NOT_PRINT'\n",
                encoding="utf-8",
            )
            empty_path_dir = Path(td) / "empty_path"
            empty_path_dir.mkdir()
            env = dict(os.environ)
            env["PATH"] = str(empty_path_dir)
            proc = subprocess.run(
                [exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(caller)],
                cwd=td, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=30, env=env,
            )
            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertNotIn("SHOULD_NOT_PRINT", proc.stdout)

    @unittest.skipIf(
        shutil.which("powershell") is None and shutil.which("pwsh") is None,
        "需要 powershell/pwsh",
    )
    def test_ps1_script_driven_failure_still_terminates_whole_process(self) -> None:
        exe = shutil.which("powershell") or shutil.which("pwsh")
        with tempfile.TemporaryDirectory() as td:
            non_git_dir = Path(td) / "not_a_repo"
            non_git_dir.mkdir()
            caller = Path(td) / "caller.ps1"
            caller.write_text(
                f'. "{_PS1_WRAPPER}"\n'
                "Assert-NotLinkedWorktree -Prefix '[t] '\n"
                "Write-Host 'SHOULD_NOT_PRINT'\n",
                encoding="utf-8",
            )
            proc = self._run(
                [exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(caller)],
                cwd=str(non_git_dir),
            )
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertNotIn("SHOULD_NOT_PRINT", proc.stdout)

    @unittest.skipIf(
        shutil.which("powershell") is None and shutil.which("pwsh") is None,
        "需要 powershell/pwsh",
    )
    def test_ps1_interactive_style_failure_does_not_kill_shell(self) -> None:
        exe = shutil.which("powershell") or shutil.which("pwsh")
        with tempfile.TemporaryDirectory() as td:
            non_git_dir = Path(td) / "not_a_repo"
            non_git_dir.mkdir()
            script = (
                f". '{_PS1_WRAPPER}'; "
                "Assert-NotLinkedWorktree -Prefix '[t] '; "
                "Write-Host 'STILL_ALIVE'"
            )
            proc = self._run([exe, "-NoProfile", "-Command", script], cwd=str(non_git_dir))
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("STILL_ALIVE", proc.stdout)


if __name__ == "__main__":
    unittest.main()
