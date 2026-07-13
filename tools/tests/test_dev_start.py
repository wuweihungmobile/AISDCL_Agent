#!/usr/bin/env python3
"""tools/dev_start.py 的輕量單元測試（純 stdlib unittest，root-infra-ci 零依賴安裝原則）。

四方複審（Architect/SA/SD/QA，2026-07-13）共同指出核心邏輯複雜度已超過純語法檢查
（py_compile）能守住的範圍。本檔覆蓋純邏輯函式與本輪修復的迴歸點，範圍刻意限於
「給定輸入即可斷言輸出」的情境：不涉及真實建置 venv / 真實網路 fetch。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import ctypes
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dev_start  # noqa: E402


class DevStartTestCase(unittest.TestCase):
    """每個測試前重置模組層級可變狀態（WARNINGS/SUMMARY），避免測試互相污染。"""

    def setUp(self) -> None:
        dev_start.WARNINGS.clear()
        dev_start.SUMMARY.clear()


class TestFlavor(DevStartTestCase):
    def test_flavor_mapping(self):
        self.assertEqual(dev_start._flavor("windows"), "windows")
        self.assertEqual(dev_start._flavor("mac"), "posix")
        self.assertEqual(dev_start._flavor("linux"), "posix")

    def test_venv_python_at(self):
        base = Path("/tmp/x")
        self.assertEqual(dev_start._venv_python_at(base, "windows"), base / "Scripts/python.exe")
        self.assertEqual(dev_start._venv_python_at(base, "posix"), base / "bin/python")


class TestDepsRelevantLines(DevStartTestCase):
    def test_build_system_section_included(self):
        text = (
            "[build-system]\n"
            'requires = ["hatchling"]\n'
            "\n"
            "[project]\n"
            'name = "x"\n'
            'version = "1.0"\n'
            'dependencies = ["a==1"]\n'
            "\n"
            "[tool.ruff]\n"
            "line-length = 100\n"
        )
        lines = dev_start._deps_relevant_lines(text, scoped=True)
        self.assertIn('requires = ["hatchling"]', lines)
        self.assertIn('dependencies = ["a==1"]', lines)
        self.assertNotIn('name = "x"', lines)
        self.assertNotIn('version = "1.0"', lines)
        self.assertNotIn("line-length = 100", lines)

    def test_unscoped_keeps_everything_non_comment(self):
        text = "pytest==8.0.0\n# comment\n\nmypy==1.0\n"
        lines = dev_start._deps_relevant_lines(text, scoped=False)
        self.assertEqual(lines, ["pytest==8.0.0", "mypy==1.0"])


class TestDepsHashBuildSystemGap(DevStartTestCase):
    """QA/Architect/SD 四方複審共同確認並修復的殘留缺口：
    build-system 段落變動先前不會觸發依賴 hash 改變（假綠）。
    """

    def test_build_system_change_alters_hash(self):
        with tempfile.TemporaryDirectory() as td:
            pyproject = Path(td) / "pyproject.toml"
            pyproject.write_text(
                '[build-system]\nrequires = ["hatchling"]\n\n[project]\nname = "x"\n',
                encoding="utf-8",
            )
            with mock.patch.object(dev_start, "DEPS_FILES", (pyproject,)):
                before = dev_start._deps_hash()
                pyproject.write_text(
                    '[build-system]\nrequires = ["setuptools"]\n\n[project]\nname = "x"\n',
                    encoding="utf-8",
                )
                after = dev_start._deps_hash()
            self.assertNotEqual(before, after)


class _RaisingPath:
    """模擬 chmod 000 上層目錄：is_*()/exists() 皆拋 OSError（P1-3 兜底防護的測試替身）。"""

    def __init__(self, name: str = "<fake>") -> None:
        self._name = name

    def exists(self):
        raise OSError(13, "Permission denied")

    def is_dir(self):
        raise OSError(13, "Permission denied")

    def is_file(self):
        raise OSError(13, "Permission denied")

    def is_symlink(self):
        raise OSError(13, "Permission denied")

    def __str__(self):
        return self._name


class TestSafeWrappers(DevStartTestCase):
    def test_safe_exists_swallows_oserror(self):
        self.assertFalse(dev_start._safe_exists(_RaisingPath()))
        self.assertEqual(len(dev_start.WARNINGS), 1)

    def test_safe_is_dir_swallows_oserror(self):
        self.assertFalse(dev_start._safe_is_dir(_RaisingPath()))
        self.assertEqual(len(dev_start.WARNINGS), 1)

    def test_safe_is_file_swallows_oserror(self):
        self.assertFalse(dev_start._safe_is_file(_RaisingPath()))
        self.assertEqual(len(dev_start.WARNINGS), 1)

    def test_safe_is_symlink_swallows_oserror(self):
        self.assertFalse(dev_start._safe_is_symlink(_RaisingPath()))
        self.assertEqual(len(dev_start.WARNINGS), 1)


class TestReadOriginMarker(DevStartTestCase):
    def test_oserror_warns_and_returns_none(self):
        fake_dir = mock.MagicMock()
        fake_dir.__truediv__ = mock.Mock(return_value=_RaisingPath())
        result = dev_start._read_origin_marker(fake_dir)
        self.assertIsNone(result)
        self.assertEqual(len(dev_start.WARNINGS), 1)

    def test_missing_file_returns_none_without_warning(self):
        with tempfile.TemporaryDirectory() as td:
            result = dev_start._read_origin_marker(Path(td))
            self.assertIsNone(result)
            self.assertEqual(dev_start.WARNINGS, [])

    def test_reads_written_marker(self):
        with tempfile.TemporaryDirectory() as td:
            dev_start._write_origin_marker(Path(td), "mac")
            self.assertEqual(dev_start._read_origin_marker(Path(td)), "mac")


class TestLoadState(DevStartTestCase):
    def test_malformed_json_warns_and_returns_empty(self):
        with tempfile.TemporaryDirectory() as td:
            state_file = Path(td) / "state.json"
            state_file.write_text("{not valid json", encoding="utf-8")
            with mock.patch.object(dev_start, "STATE_FILE", state_file):
                result = dev_start._load_state()
            self.assertEqual(result, {})
            self.assertEqual(len(dev_start.WARNINGS), 1)

    def test_non_dict_json_returns_empty(self):
        with tempfile.TemporaryDirectory() as td:
            state_file = Path(td) / "state.json"
            state_file.write_text("[1, 2, 3]", encoding="utf-8")
            with mock.patch.object(dev_start, "STATE_FILE", state_file):
                result = dev_start._load_state()
            self.assertEqual(result, {})

    def test_bad_deps_hash_type_drops_only_that_key(self):
        with tempfile.TemporaryDirectory() as td:
            state_file = Path(td) / "state.json"
            state_file.write_text(
                json.dumps({"developing": "mac", "deps_hash": "not-a-dict"}), encoding="utf-8")
            with mock.patch.object(dev_start, "STATE_FILE", state_file):
                result = dev_start._load_state()
            self.assertEqual(result, {"developing": "mac"})

    def test_missing_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(dev_start, "STATE_FILE", Path(td) / "nope.json"):
                self.assertEqual(dev_start._load_state(), {})


class TestStepHooksLinkedWorktree(DevStartTestCase):
    """Architect 複審 P1 迴歸測試：linked worktree 分支過去在主 checkout 從未裝過 hooks 時，
    仍會印出「對本 worktree 仍生效」並直接 return，零警告——是假陽性。修復後必須真的
    檢查 core.hooksPath，未生效時要 _warn() 並在 SUMMARY 標示「未生效」。
    """

    def test_unset_hooks_path_in_linked_worktree_warns_not_silently_ok(self):
        def fake_git(*args, **_kwargs):
            cp = mock.Mock()
            cp.returncode = 0
            if args[:2] == ("rev-parse", "--git-dir"):
                cp.stdout = "/repo/.git/worktrees/wt\n"
            elif args[:2] == ("rev-parse", "--git-common-dir"):
                cp.stdout = "/repo/.git\n"
            elif args[:3] == ("config", "--get", "core.hooksPath"):
                cp.stdout = ""  # 主 checkout 從未設定
                cp.returncode = 1
            else:
                cp.stdout = ""
            return cp

        with mock.patch.object(dev_start, "_git", side_effect=fake_git):
            dev_start.step_hooks("mac", True)

        self.assertEqual(len(dev_start.WARNINGS), 1)
        self.assertIn("linked worktree", dev_start.WARNINGS[0])
        self.assertIn("未生效", dev_start.SUMMARY.get("hooks", ""))

    def test_linked_worktree_with_correctly_installed_hooks_reports_normal(self):
        """Architect 複審再次發現：上一輪修復比較基準誤用本 worktree 自己的
        ROOT 算出的 HOOKS_DIR，但 core.hooksPath 永遠指向主 checkout 的絕對路徑，
        兩者physical 目錄天生不同 → 恆為 False，導致主 checkout 完全正確設定時，
        任何 worktree 內執行都會 100% 誤判「未生效」。這裡驗證修正後（比較基準改用
        由 git-common-dir 推導的主 checkout 路徑）不會再有這個假陰性。
        """
        with tempfile.TemporaryDirectory() as td:
            main_root = Path(td) / "main"
            hooks_dir = main_root / "tools" / "git-hooks"
            hooks_dir.mkdir(parents=True)
            for h in ("pre-commit", "pre-push", "post-commit"):
                (hooks_dir / h).write_text("#!/bin/sh\n", encoding="utf-8")
            main_git_dir = main_root / ".git"
            main_git_dir.mkdir()

            def fake_git(*args, **_kwargs):
                cp = mock.Mock()
                cp.returncode = 0
                if args[:2] == ("rev-parse", "--git-dir"):
                    cp.stdout = str(main_git_dir / "worktrees" / "wt") + "\n"
                elif args[:2] == ("rev-parse", "--git-common-dir"):
                    cp.stdout = str(main_git_dir) + "\n"
                elif args[:3] == ("config", "--get", "core.hooksPath"):
                    cp.stdout = str(hooks_dir) + "\n"
                else:
                    cp.stdout = ""
                return cp

            with mock.patch.object(dev_start, "_git", side_effect=fake_git):
                dev_start.step_hooks("mac", True)

            self.assertEqual(dev_start.WARNINGS, [])
            self.assertEqual(dev_start.SUMMARY.get("hooks"), "正常")


class TestStepVenvForceCrossFlavor(DevStartTestCase):
    """SD 複審 P1 迴歸測試：--force-bootstrap 與跨 OS 同 flavor（mac⇄linux）切換併發時，
    過去會整段跳過清除跨 OS 二進位 .venv 的步驟，讓 force 這個救援旗標在最需要救援
    時反而失敗。修復後不論 force 為何，cross_same_flavor 的清理都必須先執行。
    """

    def test_cleanup_runs_before_bootstrap_even_when_forced(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            venv = root / ".venv"
            venv.mkdir()
            venv_python = venv / "bin" / "python"
            venv_existed_at_bootstrap_call: dict = {}

            def fake_run_bootstrap(_now, _reason, on_start=None):
                venv_existed_at_bootstrap_call["exists"] = venv.exists()
                venv_python.parent.mkdir(parents=True, exist_ok=True)
                venv_python.write_text("fresh-binary", encoding="utf-8")
                return True

            with mock.patch.object(dev_start, "ROOT", root), \
                 mock.patch.object(dev_start, "LOCK_FILE", root / ".dev_start.lock"), \
                 mock.patch.object(dev_start, "_ensure_venv_shape", return_value="ok"), \
                 mock.patch.object(dev_start, "_deps_hash", return_value="h"), \
                 mock.patch.object(dev_start, "_run_bootstrap", side_effect=fake_run_bootstrap), \
                 mock.patch.object(dev_start, "_write_origin_marker"), \
                 mock.patch.object(dev_start, "_venv_python", return_value=venv_python):
                ok = dev_start.step_venv("linux", {}, force=True, cross_same_flavor=True)

            self.assertTrue(ok)
            self.assertFalse(venv_existed_at_bootstrap_call["exists"],
                              "跨 OS .venv 應在呼叫 bootstrap 前已被清除，即使 force=True")


class TestHooksConstantsConsistency(DevStartTestCase):
    """Architect 複審 P2：dev_start.py 與 install_git_hooks.sh 各自硬編碼同一組
    「dispatcher 目錄名＋三支 hook 檔名」假設，過去無機械比對——本測試補上這道守門。
    """

    def test_hooks_dir_and_filenames_match_install_script(self):
        install_sh = dev_start.ROOT / "AutoClaude" / "tools" / "install_git_hooks.sh"
        text = install_sh.read_text(encoding="utf-8")
        m = re.search(r'HOOKS_DIR="\$TOPLEVEL/([^"]+)"', text)
        self.assertIsNotNone(m, "install_git_hooks.sh 的 HOOKS_DIR 宣告格式已變，需同步本測試")
        self.assertEqual(dev_start.HOOKS_DIR, dev_start.ROOT / m.group(1))

        m2 = re.search(r"for h in ([\w\- ]+); do", text)
        self.assertIsNotNone(m2, "install_git_hooks.sh 的 hook 檔名清單宣告格式已變，需同步本測試")
        self.assertEqual(tuple(m2.group(1).split()), ("pre-commit", "pre-push", "post-commit"))


class TestVenvCacheHandoffBackup(DevStartTestCase):
    """QA 複審 P2：換手快取碰撞時，先前「請先手動備份」警告後立即在同一次呼叫覆蓋，
    使用者讀到警告時已來不及。修復後應改名為時間戳記備份，而非直接覆蓋。
    """

    def test_collision_renames_to_backup_instead_of_overwriting(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            venv = root / ".venv"
            (venv / "bin").mkdir(parents=True)
            (venv / "bin" / "python").write_text("posix-binary-being-handed-off", encoding="utf-8")

            cache_other = root / ".venv-cache-posix"
            (cache_other / "bin").mkdir(parents=True)
            (cache_other / "bin" / "python").write_text("sentinel-must-survive", encoding="utf-8")

            with mock.patch.object(dev_start, "ROOT", root):
                shape = dev_start._ensure_venv_shape("windows")

            self.assertEqual(shape, "missing")
            backups = list(root.glob(".venv-cache-posix.bak-*"))
            self.assertEqual(len(backups), 1, "碰撞時應改名為備份，而非覆蓋原內容")
            self.assertEqual(
                (backups[0] / "bin" / "python").read_text(encoding="utf-8"),
                "sentinel-must-survive",
            )


class TestStepFinalizeResilience(DevStartTestCase):
    """SA 複審 P1 迴歸測試：狀態檔寫入失敗（如唯讀外接碟，本功能明文旗艦情境）過去會
    裸崩潰，且發生在 venv/hooks 皆已整備成功之後，把已可用的環境誤報為整體失敗。
    """

    def test_write_failure_does_not_raise(self):
        with tempfile.TemporaryDirectory() as td:
            fake_state_file = Path(td) / "nonexistent-parent" / "state.json"
            with mock.patch.object(dev_start, "STATE_FILE", fake_state_file), \
                 mock.patch.object(dev_start, "_deps_hash", return_value="h"):
                try:
                    dev_start.step_finalize("mac", {}, is_repo=False)
                except OSError:
                    self.fail("step_finalize 不應在狀態檔寫入失敗時裸崩潰")
            self.assertEqual(len(dev_start.WARNINGS), 1)

    def test_successful_write_is_atomic_temp_replace(self):
        with tempfile.TemporaryDirectory() as td:
            state_file = Path(td) / "state.json"
            with mock.patch.object(dev_start, "STATE_FILE", state_file), \
                 mock.patch.object(dev_start, "_deps_hash", return_value="h"):
                dev_start.step_finalize("mac", {}, is_repo=False)
            self.assertTrue(state_file.is_file())
            data = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertEqual(data["developing"], "mac")
            leftover_tmp = list(Path(td).glob("state.json.tmp-*"))
            self.assertEqual(leftover_tmp, [], "成功寫入後不應留下 temp 檔")


class TestLoadStateOSErrorSafety(DevStartTestCase):
    """P1-1 迴歸測試：_load_state() 原本裸呼叫 STATE_FILE.is_file()，任何非 ENOENT 的
    OSError（如外接碟 EIO）會讓整支工具在跑任何步驟之前就裸崩潰。修復後改用
    _safe_is_file()，比照現有 TestSafeWrappers 手法 monkeypatch 驗證不裸崩潰。
    """

    def test_is_file_oserror_does_not_crash(self):
        with mock.patch.object(dev_start, "STATE_FILE", _RaisingPath()):
            try:
                result = dev_start._load_state()
            except OSError:
                self.fail("_load_state 不應在 STATE_FILE.is_file() 拋 OSError 時裸崩潰")
        self.assertEqual(result, {})
        self.assertEqual(len(dev_start.WARNINGS), 1)


class TestStepHooksIsFileOSError(DevStartTestCase):
    """P1-2 迴歸測試：step_hooks() 內 hooks 檔案存在性檢查原本是
    `(hooks_dir / h).is_file()` 裸呼叫。本輪修復把 hooks_dir 改成可能指向「主
    checkout」（跨掛載點，例如主 checkout 在外接碟/網路磁碟），比修復前風險更高卻
    沒同步套用 _safe_* 防護。改用 _safe_is_file() 後，此處驗證檔案系統暫時不可讀
    （如外接碟/網路磁碟抖動）拋 OSError 時不會讓整支工具裸崩潰。
    """

    def test_is_file_oserror_does_not_crash(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            hooks_dir = root / "tools" / "git-hooks"
            hooks_dir.mkdir(parents=True)
            for h in ("pre-commit", "pre-push", "post-commit"):
                (hooks_dir / h).write_text("#!/bin/sh\n", encoding="utf-8")
            git_dir = root / ".git"
            git_dir.mkdir()

            def fake_git(*args, **_kwargs):
                cp = mock.Mock()
                cp.returncode = 0
                if args[:2] == ("rev-parse", "--git-dir"):
                    cp.stdout = str(git_dir) + "\n"
                elif args[:2] == ("rev-parse", "--git-common-dir"):
                    cp.stdout = str(git_dir) + "\n"
                elif args[:3] == ("config", "--get", "core.hooksPath"):
                    cp.stdout = str(hooks_dir) + "\n"
                else:
                    cp.stdout = ""
                return cp

            with mock.patch.object(dev_start, "_git", side_effect=fake_git), \
                 mock.patch.object(dev_start, "ROOT", root), \
                 mock.patch.object(dev_start, "HOOKS_DIR", hooks_dir), \
                 mock.patch.object(dev_start, "_stream", return_value=0), \
                 mock.patch.object(Path, "is_file", side_effect=OSError(5, "I/O error")):
                try:
                    dev_start.step_hooks("mac", True)
                except OSError:
                    self.fail("step_hooks 不應在 hooks 檔案存在性檢查拋 OSError 時裸崩潰")

            self.assertTrue(any("無法讀取" in w for w in dev_start.WARNINGS))


class TestBootstrapLock(DevStartTestCase):
    """P1-3 迴歸測試：SA 審查以真實並行執行 + kill 重跑實測證實，venv bootstrap
    完全沒有互斥鎖時，兩個並行/中斷重跑的 bootstrap 行程會競態寫入同一個 .venv，
    且雙方都回報「✅ 完成」——其中一方環境其實已被覆蓋。以下驗證 PID lock 機制。
    """

    def test_alive_pid_holder_blocks_acquisition(self):
        with tempfile.TemporaryDirectory() as td:
            lock_file = Path(td) / ".dev_start.lock"
            # 寫入本測試行程自己的 PID —— 保證在整個測試期間存活
            lock_file.write_text(str(os.getpid()), encoding="utf-8")
            with mock.patch.object(dev_start, "LOCK_FILE", lock_file):
                result = dev_start._acquire_bootstrap_lock()
            self.assertIsNone(result, "存活 PID 持有鎖時應拿不到鎖")
            self.assertTrue(lock_file.is_file(), "存活 PID 持有的鎖檔不應被清除")
            self.assertTrue(any("另一個 dev_start" in w for w in dev_start.WARNINGS))

    def test_stale_lock_is_cleared_and_acquired(self):
        with tempfile.TemporaryDirectory() as td:
            lock_file = Path(td) / ".dev_start.lock"
            # 找一個保證不存在的 PID：目前行程 PID + 大偏移量，並先確認該 PID 真的不存在
            stale_pid = os.getpid() + 100000
            while dev_start._pid_alive(stale_pid):
                stale_pid += 1
            lock_file.write_text(str(stale_pid), encoding="utf-8")
            fd = None
            try:
                with mock.patch.object(dev_start, "LOCK_FILE", lock_file):
                    fd = dev_start._acquire_bootstrap_lock()
                self.assertIsNotNone(fd, "陳舊鎖應被自動清除並成功取得鎖")
                self.assertTrue(lock_file.is_file())
                self.assertEqual(lock_file.read_text(encoding="utf-8").strip(), str(os.getpid()))
            finally:
                if fd is not None:
                    os.close(fd)

    def test_release_removes_lock_file(self):
        with tempfile.TemporaryDirectory() as td:
            lock_file = Path(td) / ".dev_start.lock"
            with mock.patch.object(dev_start, "LOCK_FILE", lock_file):
                fd = dev_start._acquire_bootstrap_lock()
                self.assertIsNotNone(fd)
                dev_start._release_bootstrap_lock(fd)
            self.assertFalse(lock_file.is_file(), "釋放鎖後鎖檔應被刪除")


class TestStepVenvLockedAborts(DevStartTestCase):
    """P1-3 迴歸測試：另一個存活 PID 持有鎖時，step_venv() 應中止且不進行 bootstrap
    （不要真的競態啟動兩個行程去測，改用「先手動建立一個假鎖檔、寫入本測試行程自己
    的 PID（保證存活）」的方式驗證 step_venv 完全不呼叫 _run_bootstrap，且回傳 False
    讓 main() 以非 0 結束碼收尾 —— fail loud，不可靜默略過）。
    """

    def test_step_venv_aborts_without_running_bootstrap_when_lock_held(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            lock_file = root / ".dev_start.lock"
            lock_file.write_text(str(os.getpid()), encoding="utf-8")
            bootstrap_calls = []

            with mock.patch.object(dev_start, "ROOT", root), \
                 mock.patch.object(dev_start, "LOCK_FILE", lock_file), \
                 mock.patch.object(dev_start, "_ensure_venv_shape", return_value="ok"), \
                 mock.patch.object(dev_start, "_deps_hash", return_value="h"), \
                 mock.patch.object(dev_start, "_run_bootstrap",
                                    side_effect=lambda *a: bootstrap_calls.append(a) or True):
                ok = dev_start.step_venv("mac", {}, force=True)

            self.assertFalse(ok, "鎖被佔用時 step_venv 應回傳 False（非 0 結束碼）")
            self.assertEqual(bootstrap_calls, [], "鎖被佔用時不應進行 bootstrap")


class TestVenvShapeOSErrorSafety(DevStartTestCase):
    """P2-2 迴歸測試：_ensure_venv_shape() 內 `cache_mine.is_symlink()`（同函式內其他
    呼叫點皆已套用 _safe_* 包裝，這是漏網之魚）原本裸呼叫，檔案系統探測拋 OSError
    時會讓整支工具裸崩潰。改用 _safe_is_symlink() 後驗證不再裸崩潰。
    """

    def test_ensure_venv_shape_survives_cache_mine_is_symlink_oserror(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cache_mine = root / ".venv-cache-posix"  # mac → flavor=posix
            cache_mine.mkdir()
            with mock.patch.object(dev_start, "ROOT", root), \
                 mock.patch.object(Path, "is_symlink", side_effect=OSError(5, "I/O error")):
                try:
                    shape = dev_start._ensure_venv_shape("mac")
                except OSError:
                    self.fail(
                        "_ensure_venv_shape 不應在 cache_mine.is_symlink() 拋 OSError 時裸崩潰")
            self.assertEqual(shape, "missing")
            self.assertTrue(any("無法讀取" in w for w in dev_start.WARNINGS))


class TestStepSyncRealGitRepo(DevStartTestCase):
    """QA 複審：step_sync() 零測試覆蓋，且 QA 實測示範把「髒工作樹不自動 pull」的
    判斷刻意改壞（`if dirty:` → `if False:`）後，py_compile 與既有 23 個 unittest
    全數通過、完全沒抓到——這是本工具核心安全承諾（絕不對髒工作樹硬做）的真實 CI
    盲區。以下用真實 temp git repo（非 mock，真正 git init/commit/fetch）驗證整合行為。
    """

    @staticmethod
    def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
        return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)

    def _make_pair(self, base: Path) -> tuple[Path, Path]:
        """建立 origin（本地倉）+ local（clone）一組配對，供 step_sync 整合測試使用。"""
        origin = base / "origin"
        local = base / "local"
        origin.mkdir()
        for args in (
            ["init", "--quiet"],
            ["config", "user.email", "test@example.com"],
            ["config", "user.name", "Test"],
            ["config", "commit.gpgsign", "false"],
        ):
            self._run_git(args, origin)
        (origin / "f.txt").write_text("v1\n", encoding="utf-8")
        self._run_git(["add", "."], origin)
        self._run_git(["commit", "--quiet", "-m", "init"], origin)
        self._run_git(["clone", "--quiet", str(origin), str(local)], base)
        for args in (
            ["config", "user.email", "test@example.com"],
            ["config", "user.name", "Test"],
            ["config", "commit.gpgsign", "false"],
        ):
            self._run_git(args, local)
        return origin, local

    def test_dirty_worktree_does_not_pull(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            origin, local = self._make_pair(base)
            (origin / "f.txt").write_text("v2-origin\n", encoding="utf-8")
            self._run_git(["commit", "--quiet", "-am", "advance"], origin)
            # local 弄髒：修改已追蹤檔但不 commit
            (local / "f.txt").write_text("v1-dirty-local-edit\n", encoding="utf-8")

            with mock.patch.object(dev_start, "ROOT", local):
                dev_start.step_sync(no_sync=False, is_repo=True)

            self.assertEqual(
                (local / "f.txt").read_text(encoding="utf-8"), "v1-dirty-local-edit\n",
                "髒工作樹時不應自動 pull，本地未提交變更應保留")
            self.assertTrue(any("未提交變更" in w for w in dev_start.WARNINGS))
            self.assertIn("未同步", dev_start.SUMMARY.get("sync", ""))

    def test_clean_fast_forward_pulls(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            origin, local = self._make_pair(base)
            (origin / "f.txt").write_text("v2-origin\n", encoding="utf-8")
            self._run_git(["commit", "--quiet", "-am", "advance"], origin)

            with mock.patch.object(dev_start, "ROOT", local):
                dev_start.step_sync(no_sync=False, is_repo=True)

            self.assertEqual((local / "f.txt").read_text(encoding="utf-8"), "v2-origin\n",
                              "乾淨且可 fast-forward 時應正確 pull")
            self.assertIn("已更新", dev_start.SUMMARY.get("sync", ""))

    def test_diverged_does_not_force_merge(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            origin, local = self._make_pair(base)
            (origin / "f.txt").write_text("v2-origin\n", encoding="utf-8")
            self._run_git(["commit", "--quiet", "-am", "origin-advance"], origin)
            (local / "f.txt").write_text("v2-local\n", encoding="utf-8")
            self._run_git(["commit", "--quiet", "-am", "local-advance"], local)

            with mock.patch.object(dev_start, "ROOT", local):
                dev_start.step_sync(no_sync=False, is_repo=True)

            self.assertEqual((local / "f.txt").read_text(encoding="utf-8"), "v2-local\n",
                              "分叉時不應自動 rebase/merge，本地內容應維持原狀")
            self.assertTrue(any("分叉" in w for w in dev_start.WARNINGS))
            self.assertIn("分叉", dev_start.SUMMARY.get("sync", ""))

    def test_fetch_failure_degrades_to_offline(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            origin, local = self._make_pair(base)
            shutil.rmtree(origin)  # 模擬離線：origin 路徑消失，fetch 必失敗

            with mock.patch.object(dev_start, "ROOT", local):
                dev_start.step_sync(no_sync=False, is_repo=True)

            self.assertTrue(any("離線" in w for w in dev_start.WARNINGS))
            self.assertIn("離線", dev_start.SUMMARY.get("sync", ""))


class TestCacheRestoreTrustRestoredBranch(DevStartTestCase):
    """QA 複審：_cache_restore_trust() / _venv_healthy() 的『restored』分支是 round 2
    （b2a9cf2）修復的核心防線、也是本工具『秒級換回』賣點的實作核心，先前只測到
    TestVenvCacheHandoffBackup 這個旁支（碰撞備份），本體完全沒有直接測試機械把關。
    透過 _ensure_venv_shape() 驗證端到端行為（含實際 rename 是否發生），而非只測
    _cache_restore_trust 的回傳值。
    """

    @staticmethod
    def _make_fake_interpreter(py: Path, healthy: bool) -> None:
        py.parent.mkdir(parents=True, exist_ok=True)
        if healthy:
            py.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        else:
            # 損毀的假二進位：非合法可執行格式（無 shebang、非 ELF/Mach-O）→ exec 失敗
            py.write_bytes(b"\x7fbroken-not-a-real-binary\x00\x01")
        py.chmod(0o755)

    def test_valid_same_platform_cache_is_restored(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cache_mine = root / ".venv-cache-posix"
            py = cache_mine / "bin" / "python"
            self._make_fake_interpreter(py, healthy=True)
            dev_start._write_origin_marker(cache_mine, "mac")

            with mock.patch.object(dev_start, "ROOT", root):
                shape = dev_start._ensure_venv_shape("mac")

            self.assertEqual(shape, "restored")
            self.assertFalse(cache_mine.exists(), "換回後快取目錄應已被 rename 走")
            restored_py = root / ".venv" / "bin" / "python"
            self.assertTrue(restored_py.is_file())
            self.assertEqual(restored_py.read_text(encoding="utf-8"), "#!/bin/sh\nexit 0\n",
                              "換回後內容須與原快取一致")

    def test_origin_marker_mismatch_rejects_restore(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cache_mine = root / ".venv-cache-posix"
            py = cache_mine / "bin" / "python"
            self._make_fake_interpreter(py, healthy=True)
            dev_start._write_origin_marker(cache_mine, "windows")  # 與 now="mac" 不符

            with mock.patch.object(dev_start, "ROOT", root):
                shape = dev_start._ensure_venv_shape("mac")

            self.assertEqual(shape, "missing")
            self.assertTrue(cache_mine.is_dir(), "標記不符時快取應原封不動，不可被清除")
            self.assertTrue((cache_mine / "bin" / "python").is_file())
            self.assertFalse((root / ".venv").exists())
            self.assertTrue(any("標記建於" in w for w in dev_start.WARNINGS))

    def test_corrupt_interpreter_health_check_rejects_restore(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cache_mine = root / ".venv-cache-posix"
            py = cache_mine / "bin" / "python"
            self._make_fake_interpreter(py, healthy=False)
            dev_start._write_origin_marker(cache_mine, "mac")  # 標記正確，但二進位損毀

            with mock.patch.object(dev_start, "ROOT", root):
                shape = dev_start._ensure_venv_shape("mac")

            self.assertEqual(shape, "missing")
            self.assertTrue(cache_mine.is_dir(), "健檢失敗時快取應原封不動，不可被清除")
            self.assertFalse((root / ".venv").exists())
            self.assertTrue(any("健檢失敗" in w for w in dev_start.WARNINGS))


class TestPidAliveWindowsBranch(DevStartTestCase):
    """P2（Architect/SA/QA 四方複審交叉印證，本輪複核再次確認）：_pid_alive() 的
    Windows 分支過去把任何 OpenProcess 失敗都當作「行程已死」，沒有比照 POSIX
    分支區分「行程不存在」vs「行程存在但無權限探測」（ERROR_ACCESS_DENIED=5）。
    """

    def test_open_process_succeeds_is_alive(self):
        fake_kernel32 = mock.Mock()
        fake_kernel32.OpenProcess.return_value = 12345  # 非 0 = 成功開啟 handle
        fake_windll = mock.Mock(kernel32=fake_kernel32)
        with mock.patch.object(ctypes, "windll", fake_windll, create=True), \
             mock.patch.object(dev_start.os, "name", "nt"):
            self.assertTrue(dev_start._pid_alive(4242))
        fake_kernel32.CloseHandle.assert_called_once_with(12345)

    def test_open_process_fails_with_access_denied_is_alive(self):
        fake_kernel32 = mock.Mock()
        fake_kernel32.OpenProcess.return_value = 0
        fake_kernel32.GetLastError.return_value = 5  # ERROR_ACCESS_DENIED
        fake_windll = mock.Mock(kernel32=fake_kernel32)
        with mock.patch.object(ctypes, "windll", fake_windll, create=True), \
             mock.patch.object(dev_start.os, "name", "nt"):
            self.assertTrue(dev_start._pid_alive(4242))

    def test_open_process_fails_with_other_error_is_dead(self):
        fake_kernel32 = mock.Mock()
        fake_kernel32.OpenProcess.return_value = 0
        fake_kernel32.GetLastError.return_value = 87  # ERROR_INVALID_PARAMETER
        fake_windll = mock.Mock(kernel32=fake_kernel32)
        with mock.patch.object(ctypes, "windll", fake_windll, create=True), \
             mock.patch.object(dev_start.os, "name", "nt"):
            self.assertFalse(dev_start._pid_alive(4242))


class TestAcquireBootstrapLockMalformedContent(DevStartTestCase):
    """QA 發現的測試缺口：鎖檔存在但內容無法解析為 PID（非數字）時，
    _acquire_bootstrap_lock() 應視為安全起見『仍被持有』，回傳 None 並警告，
    而不是裸拋例外或誤判可清除。
    """

    def test_unparseable_lock_content_aborts_with_warning(self):
        with tempfile.TemporaryDirectory() as td:
            lock_file = Path(td) / ".dev_start.lock"
            lock_file.write_text("not-a-pid", encoding="utf-8")
            with mock.patch.object(dev_start, "LOCK_FILE", lock_file):
                result = dev_start._acquire_bootstrap_lock()
            self.assertIsNone(result)
            self.assertTrue(lock_file.is_file(), "無法辨識的鎖檔內容不應被清除")
            self.assertTrue(any("無法辨識" in w for w in dev_start.WARNINGS))


class TestRecordLockPid(DevStartTestCase):
    """本輪核心修法之一：_record_lock_pid() 把鎖檔內容從 orchestrator PID
    改寫成真正執行 bootstrap 的子行程 PID，驗證覆寫行為正確（截斷舊內容、
    不是附加）。
    """

    def test_overwrites_lock_file_content_with_given_pid(self):
        with tempfile.TemporaryDirectory() as td:
            lock_file = Path(td) / ".dev_start.lock"
            fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, str(os.getpid()).encode("utf-8"))
                dev_start._record_lock_pid(fd, 999999)
            finally:
                os.close(fd)
            self.assertEqual(lock_file.read_text(encoding="utf-8").strip(), "999999")

    def test_overwrite_with_shorter_pid_leaves_no_trailing_garbage(self):
        """舊內容（如 "123456789"）比新內容（如 "42"）長時，若忘記 ftruncate，
        檔案會殘留舊內容尾巴（"42456789"）而非乾淨的 "42"。"""
        with tempfile.TemporaryDirectory() as td:
            lock_file = Path(td) / ".dev_start.lock"
            fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, b"123456789")
                dev_start._record_lock_pid(fd, 42)
            finally:
                os.close(fd)
            self.assertEqual(lock_file.read_text(encoding="utf-8").strip(), "42")


class TestPeekBootstrapLock(DevStartTestCase):
    """_peek_bootstrap_lock() 的純讀取語意單元測試：missing / 損毀內容 / 陳舊
    PID / 存活 PID 四種情況，且驗證『唯讀不清理』（存活時鎖檔不應被修改）。
    """

    def test_missing_lock_file_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(dev_start, "LOCK_FILE", Path(td) / "nope.lock"):
                self.assertIsNone(dev_start._peek_bootstrap_lock())

    def test_malformed_content_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            lock_file = Path(td) / ".dev_start.lock"
            lock_file.write_text("not-a-pid", encoding="utf-8")
            with mock.patch.object(dev_start, "LOCK_FILE", lock_file):
                self.assertIsNone(dev_start._peek_bootstrap_lock())

    def test_dead_pid_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            lock_file = Path(td) / ".dev_start.lock"
            stale_pid = os.getpid() + 100000
            while dev_start._pid_alive(stale_pid):
                stale_pid += 1
            lock_file.write_text(str(stale_pid), encoding="utf-8")
            with mock.patch.object(dev_start, "LOCK_FILE", lock_file):
                self.assertIsNone(dev_start._peek_bootstrap_lock())

    def test_alive_pid_returns_pid_without_mutating_lock_file(self):
        with tempfile.TemporaryDirectory() as td:
            lock_file = Path(td) / ".dev_start.lock"
            lock_file.write_text(str(os.getpid()), encoding="utf-8")
            with mock.patch.object(dev_start, "LOCK_FILE", lock_file):
                result = dev_start._peek_bootstrap_lock()
            self.assertEqual(result, os.getpid())
            self.assertTrue(lock_file.is_file(), "peek 不應清除/修改鎖檔（唯讀）")
            self.assertEqual(lock_file.read_text(encoding="utf-8").strip(), str(os.getpid()))


class TestStreamOnStartCallback(DevStartTestCase):
    """_stream() 改用 subprocess.Popen 後，on_start 必須在子行程建立當下就拿到
    真實子行程 PID（而非等到程序結束才知道），這樣呼叫端（_run_bootstrap）才能
    在 bootstrap 真正執行期間就把 PID 寫入鎖檔，不留時間差讓孤兒行程繞過鎖。
    用真實 subprocess（而非函式層級 mock）驗證，因為這正是本輪要修的『行程樹
    存活語意』問題本身。
    """

    def test_on_start_receives_real_child_pid(self):
        captured_pids = []
        rc = dev_start._stream(
            [sys.executable, "-c", "import time; time.sleep(0.3)"],
            on_start=lambda pid: captured_pids.append(pid),
        )
        self.assertEqual(rc, 0)
        self.assertEqual(len(captured_pids), 1)
        self.assertGreater(captured_pids[0], 0)

    def test_on_start_omitted_still_works(self):
        rc = dev_start._stream([sys.executable, "-c", "pass"])
        self.assertEqual(rc, 0)

    def test_file_not_found_returns_127(self):
        rc = dev_start._stream(["definitely-not-a-real-command-xyz"])
        self.assertEqual(rc, 127)


class TestOrphanChildLockRegression(DevStartTestCase):
    """收尾要求：本輪核心修法（子行程 PID 追蹤 + step_venv 頂部 busy-lock 檢查）
    的端到端迴歸測試。Architect 明確指出上一輪測試抓不到問題正是因為只用函式
    層級 mock（如 mock.patch.object(dev_start, "_run_bootstrap", ...)）——這類
    『行程樹存活語意』的 bug（orchestrator 死亡但子行程變孤兒仍存活）本質上
    無法被函式層級 mock 看見，必須用真實 subprocess.Popen 起一個真的會存活數秒
    的子行程才能驗證鎖真正追蹤的是誰。
    """

    def test_peek_reflects_real_child_process_lifetime(self):
        with tempfile.TemporaryDirectory() as td:
            lock_file = Path(td) / ".dev_start.lock"
            proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(2)"])
            try:
                lock_file.write_text(str(proc.pid), encoding="utf-8")
                with mock.patch.object(dev_start, "LOCK_FILE", lock_file):
                    self.assertEqual(dev_start._peek_bootstrap_lock(), proc.pid,
                                      "① 子行程存活期間 peek 應回傳其 PID")
                proc.wait(timeout=5)
                with mock.patch.object(dev_start, "LOCK_FILE", lock_file):
                    self.assertIsNone(dev_start._peek_bootstrap_lock(),
                                       "② 子行程結束後 peek 應回傳 None")
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()

    def test_step_venv_aborts_when_lock_holds_live_child_pid_even_without_reason(self):
        """③ 核心迴歸：模擬『orchestrator 死掉但子行程還活著』——鎖檔一旦被
        _record_lock_pid 寫入子行程 PID，只要該子行程仍存活，step_venv() 就必須
        在函式最開頭中止，即使會落入『prev is None』（過去版本完全不取鎖、也
        不檢查鎖的分支）也不例外。這正是上一輪鎖機制的真實漏洞：orchestrator
        被 kill 後孤兒子行程仍在寫 .venv，但下一輪重跑若走到 prev is None 分支，
        舊版鎖完全形同虛設。
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            lock_file = root / ".dev_start.lock"
            proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(2)"])
            shape_calls = []
            bootstrap_calls = []
            try:
                lock_file.write_text(str(proc.pid), encoding="utf-8")
                with mock.patch.object(dev_start, "ROOT", root), \
                     mock.patch.object(dev_start, "LOCK_FILE", lock_file), \
                     mock.patch.object(dev_start, "_ensure_venv_shape",
                                        side_effect=lambda *a: shape_calls.append(a) or "ok"), \
                     mock.patch.object(dev_start, "_deps_hash", return_value="h"), \
                     mock.patch.object(dev_start, "_run_bootstrap",
                                        side_effect=lambda *a, **k: bootstrap_calls.append(a)
                                        or True):
                    # state 裡沒有 deps_hash 紀錄 → 若無頂部 busy-lock 檢查，會落入
                    # `prev is None` 分支（過去版本完全不取鎖、也不檢查鎖）
                    ok = dev_start.step_venv("mac", {}, force=False)
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()

            self.assertFalse(ok, "鎖被存活子行程持有時，即使落入 prev-is-None 分支也應中止")
            self.assertEqual(shape_calls, [], "頂部 busy-lock 檢查應搶在 _ensure_venv_shape 之前中止")
            self.assertEqual(bootstrap_calls, [], "不應執行 bootstrap")


class TestStepVenvPrevNoneHealthCheck(DevStartTestCase):
    """Architect 建議（非阻塞但一併修）：既有 .venv 沿用、只記首次依賴基準的
    `prev is None` 分支過去完全不做健檢就信任現狀。修復後健檢失敗應視同壞損，
    改走正常 bootstrap 路徑（並仍受頂部 busy-lock 檢查與鎖機制保護）。
    """

    def test_healthy_interpreter_still_reuses_without_bootstrap(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            venv_python = root / ".venv" / "bin" / "python"
            venv_python.parent.mkdir(parents=True)
            venv_python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            venv_python.chmod(0o755)
            bootstrap_calls = []

            with mock.patch.object(dev_start, "ROOT", root), \
                 mock.patch.object(dev_start, "LOCK_FILE", root / ".dev_start.lock"), \
                 mock.patch.object(dev_start, "_ensure_venv_shape", return_value="ok"), \
                 mock.patch.object(dev_start, "_deps_hash", return_value="h"), \
                 mock.patch.object(dev_start, "_venv_python", return_value=venv_python), \
                 mock.patch.object(dev_start, "_run_bootstrap",
                                    side_effect=lambda *a, **k: bootstrap_calls.append(a) or True):
                ok = dev_start.step_venv("mac", {}, force=False)

            self.assertTrue(ok)
            self.assertEqual(bootstrap_calls, [], "健檢通過時不應觸發 bootstrap")
            self.assertIn("沿用既有", dev_start.SUMMARY.get("venv", ""))

    def test_unhealthy_interpreter_triggers_bootstrap_instead_of_silent_reuse(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            venv_python = root / ".venv" / "bin" / "python"
            venv_python.parent.mkdir(parents=True)
            venv_python.write_bytes(b"\x7fbroken-not-a-real-binary\x00\x01")
            venv_python.chmod(0o755)
            bootstrap_calls = []

            def fake_run_bootstrap(_now, reason, **_kwargs):
                bootstrap_calls.append(reason)
                return True

            with mock.patch.object(dev_start, "ROOT", root), \
                 mock.patch.object(dev_start, "LOCK_FILE", root / ".dev_start.lock"), \
                 mock.patch.object(dev_start, "_ensure_venv_shape", return_value="ok"), \
                 mock.patch.object(dev_start, "_deps_hash", return_value="h"), \
                 mock.patch.object(dev_start, "_venv_python", return_value=venv_python), \
                 mock.patch.object(dev_start, "_write_origin_marker"), \
                 mock.patch.object(dev_start, "_run_bootstrap", side_effect=fake_run_bootstrap):
                ok = dev_start.step_venv("mac", {}, force=False)

            self.assertTrue(ok)
            self.assertEqual(len(bootstrap_calls), 1)
            self.assertIn("健檢失敗", bootstrap_calls[0])


if __name__ == "__main__":
    unittest.main()
