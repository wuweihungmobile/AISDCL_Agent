#!/usr/bin/env python3
"""tools/dev_start.py 的輕量單元測試（純 stdlib unittest，root-infra-ci 零依賴安裝原則）。

四方複審（Architect/SA/SD/QA，2026-07-13）共同指出核心邏輯複雜度已超過純語法檢查
（py_compile）能守住的範圍。本檔覆蓋純邏輯函式與本輪修復的迴歸點，範圍刻意限於
「給定輸入即可斷言輸出」的情境：不涉及真實建置 venv / 真實網路 fetch。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import json
import re
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

            def fake_run_bootstrap(_now, _reason):
                venv_existed_at_bootstrap_call["exists"] = venv.exists()
                venv_python.parent.mkdir(parents=True, exist_ok=True)
                venv_python.write_text("fresh-binary", encoding="utf-8")
                return True

            with mock.patch.object(dev_start, "ROOT", root), \
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


if __name__ == "__main__":
    unittest.main()
