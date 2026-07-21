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
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dev_start  # noqa: E402
from _platform_helpers import (  # noqa: E402
    copy_functional_interpreter as _copy_functional_interpreter,
)
from _platform_helpers import create_symlink_or_skip  # noqa: E402


def _rmtree_force(path: Path) -> None:
    """跨平台安全的 rmtree（R3 QA 發現：Windows 上刪 git repo 直接 shutil.rmtree()
    炸 PermissionError——git 物件檔（.git/objects/**）預設唯讀，POSIX 刪檔看的是
    父目錄寫入權限（唯讀位元不擋刪除），但 Windows 刪檔會檢查檔案本身唯讀屬性，
    需先清除才能刪除；POSIX 上呼叫此函式與裸 shutil.rmtree 行為等價，零副作用）。
    """
    def _on_error(func, p, exc_info):
        os.chmod(p, 0o700)
        func(p)
    shutil.rmtree(path, onerror=_on_error)


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


class TestTomlDepsSnapshot(DevStartTestCase):
    """MUST FIX #3：先前手寫正則掃描（_TOML_SECTION_RE 等）改用標準庫 tomllib
    正確解析。以下涵蓋 QA 用實際函式呼叫重現的三個正則邊角案例，以及既有
    build-system／metadata 排除行為的等價覆蓋。
    """

    def test_project_dependencies_included_metadata_and_tool_excluded(self):
        text = (
            "[build-system]\n"
            'requires = ["hatchling"]\n'
            'build-backend = "hatchling.build"\n'
            "\n"
            "[project]\n"
            'name = "x"\n'
            'version = "1.0"\n'
            'dependencies = ["a==1"]\n'
            "\n"
            "[tool.ruff]\n"
            "line-length = 100\n"
        )
        snapshot = dev_start._toml_deps_snapshot(text, Path("pyproject.toml"))
        self.assertIn("a==1", snapshot)
        self.assertIn("hatchling", snapshot)
        self.assertNotIn('"x"', snapshot, "name 中繼資料不應納入")
        self.assertNotIn("line-length", snapshot, "[tool.ruff] 與依賴無關，不應納入")

    def test_optional_dependencies_included(self):
        """SHOULD FIX #6c：project.optional-dependencies（本 repo 真實
        AutoClaude/pyproject.toml 的 dev/notifications/postgres/pgvector 四組
        extras 正是用這個段落）必須被納入依賴 hash。"""
        text = (
            "[project]\n"
            'dependencies = ["a==1"]\n'
            "\n"
            "[project.optional-dependencies]\n"
            'dev = ["pytest==8.0.0"]\n'
        )
        snapshot = dev_start._toml_deps_snapshot(text, Path("pyproject.toml"))
        self.assertIn("pytest==8.0.0", snapshot)

        changed = text.replace("pytest==8.0.0", "pytest==9.0.0")
        snapshot_changed = dev_start._toml_deps_snapshot(changed, Path("pyproject.toml"))
        self.assertNotEqual(snapshot, snapshot_changed,
                             "optional-dependencies 內容變動應反映在 snapshot 上")

    def test_case_a_inline_comment_after_section_header(self):
        """案例 a（P1，fail-silent 最嚴重）：正則方案下 `[project]  # comment`
        不匹配表頭正則，section 沿用前一個值，真正的依賴宣告被完全排除在
        hash 之外且零警告。tomllib 正確解析，不受行內註解影響。"""
        without_comment = '[project]\ndependencies = ["a==1"]\n'
        with_inline_comment = '[project]  # main package metadata\ndependencies = ["a==2"]\n'
        snap1 = dev_start._toml_deps_snapshot(without_comment, Path("pyproject.toml"))
        snap2 = dev_start._toml_deps_snapshot(with_inline_comment, Path("pyproject.toml"))
        self.assertIn("a==2", snap2)
        self.assertNotEqual(snap1, snap2, "表頭後接註解時仍應正確辨識依賴變動")

    def test_case_b_nested_array_table_not_misfiled(self):
        """案例 b：`[[table.array]]` 巢狀陣列表不匹配表頭正則，正則方案下會被
        誤判歸入前一個區段（過度觸發重裝，方向安全但邏輯錯）。"""
        text = (
            "[project]\n"
            'dependencies = ["a==1"]\n'
            "\n"
            "[[tool.custom.plugins]]\n"
            'name = "unrelated-plugin"\n'
        )
        snapshot = dev_start._toml_deps_snapshot(text, Path("pyproject.toml"))
        self.assertNotIn("unrelated-plugin", snapshot)

    def test_case_c_multiline_triple_quoted_string_not_hashed(self):
        """案例 c：多行三引號字串的續行內容，正則方案下會被誤納入 hash
        （純文案異動誤觸發重裝）。"""
        quote = '"""'
        base = (
            "[project]\n"
            'dependencies = ["a==1"]\n'
            f"description = {quote}line one\n"
            f'line two mentions dependencies = ["fake"]\n{quote}\n'
        )
        changed = base.replace("line two mentions", "line two now says")
        snap_base = dev_start._toml_deps_snapshot(base, Path("pyproject.toml"))
        snap_changed = dev_start._toml_deps_snapshot(changed, Path("pyproject.toml"))
        self.assertEqual(snap_base, snap_changed,
                          "description 內文字變動不應觸發依賴 hash 改變")

    def test_invalid_toml_falls_back_to_whole_text_and_warns(self):
        text = "[project\ndependencies = [1, 2\n"  # 語法錯誤：未閉合的表頭/陣列
        snapshot = dev_start._toml_deps_snapshot(text, Path("pyproject.toml"))
        self.assertIn(text, snapshot)
        self.assertTrue(any("非合法 TOML" in w for w in dev_start.WARNINGS))

    def test_case_1_bare_date_dependency_falls_back_instead_of_crashing(self):
        """MUST FIX #1（SD 複審發現的 P1 迴歸）：`dependencies = [2024-01-01]`
        語法合法（tomllib 解析成 datetime.date），但 json.dumps() 無法序列化
        會裸拋 TypeError。修復前只保護 tomllib.loads() 本身，這裡驗證裸崩潰
        已改為 fail-loud 的警告 + 退回整檔內容路徑。"""
        text = '[project]\nname = "x"\ndependencies = [2024-01-01]\n'
        snapshot = dev_start._toml_deps_snapshot(text, Path("pyproject.toml"))
        self.assertIn(text, snapshot)
        self.assertTrue(any("TOML" in w for w in dev_start.WARNINGS))

    def test_case_2_project_as_scalar_falls_back_instead_of_crashing(self):
        """MUST FIX #1：`project = "oops-not-a-table"` 語法合法，但
        data.get("project", {}) 拿到字串而非 dict，後續 project.get(...) 會
        裸拋 AttributeError。同上，驗證改為 fail-loud 警告路徑。"""
        text = 'project = "oops-not-a-table"\n'
        snapshot = dev_start._toml_deps_snapshot(text, Path("pyproject.toml"))
        self.assertIn(text, snapshot)
        self.assertTrue(any("TOML" in w for w in dev_start.WARNINGS))

    def test_deps_hash_does_not_crash_on_malformed_shape_toml(self):
        """驗證 _deps_hash() 這個上游呼叫端同樣不會被這兩個案例拖累裸崩潰
        （不只是 _toml_deps_snapshot() 單元本身）。"""
        with tempfile.TemporaryDirectory() as td:
            pyproject = Path(td) / "pyproject.toml"
            pyproject.write_text(
                '[project]\nname = "x"\ndependencies = [2024-01-01]\n', encoding="utf-8")
            with mock.patch.object(dev_start, "DEPS_FILES", (pyproject,)):
                try:
                    digest = dev_start._deps_hash()
                except (TypeError, AttributeError):
                    self.fail("_deps_hash 不應在依賴檔含合法但形狀不符的 TOML 時裸崩潰")
            self.assertIsInstance(digest, str)


class TestPlainRelevantLines(DevStartTestCase):
    def test_keeps_everything_non_comment(self):
        text = "pytest==8.0.0\n# comment\n\nmypy==1.0\n"
        lines = dev_start._plain_relevant_lines(text)
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
    """Architect 複審 P2：dev_start.py 與 git hooks 安裝腳本各自硬編碼同一組
    「dispatcher 目錄名＋三支 hook 檔名」假設，過去無機械比對——本測試補上這道守門。

    獨立複審 finding（GitHooksInstallCommon.ps1 雙軌重寫）修復後，判定邏輯的單一
    真相源改為 tools/git_hooks_install_common.py（tools/lib/GitHooksInstallCommon.ps1
    與 tools/lib/git_hooks_install_common.sh 皆改為呼叫它的薄殼層，各自不再宣告
    HOOKS_DIR／hook 檔名），本測試改比對該 Python 檔。
    """

    def test_hooks_dir_and_filenames_match_install_script(self):
        common_py = dev_start.ROOT / "tools" / "git_hooks_install_common.py"
        text = common_py.read_text(encoding="utf-8")
        m = re.search(r'Path\(top\) / "([^"]+)" / "([^"]+)"', text)
        self.assertIsNotNone(m, "git_hooks_install_common.py 的 HOOKS_DIR 宣告格式已變，需同步本測試")
        self.assertEqual(dev_start.HOOKS_DIR, dev_start.ROOT / m.group(1) / m.group(2))

        m2 = re.search(r"HOOK_FILENAMES = \(([^)]+)\)", text)
        self.assertIsNotNone(m2, "git_hooks_install_common.py 的 hook 檔名清單宣告格式已變，需同步本測試")
        filenames = tuple(re.findall(r'"([^"]+)"', m2.group(1)))
        self.assertEqual(filenames, ("pre-commit", "pre-push", "post-commit"))


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


class TestAcquireBootstrapLockPartialAliveMiddleState(DevStartTestCase):
    """MUST FIX C（QA 複審發現的測試覆蓋缺口）：現有測試只涵蓋
    `_acquire_bootstrap_lock()` 的『單一 PID 全存活』（見上方
    `test_alive_pid_holder_blocks_acquisition`）與『全部 PID 死透』（見上方
    `test_stale_lock_is_cleared_and_acquired`）兩端；`TestMultiGrandchildLockNotPrematurelyStale`
    (MUST FIX A 重寫前) 對『A 死 B 活』中間態只透過 `_peek_bootstrap_lock()`
    （讀取端）驗證，從未在同一中間態下直接呼叫 `_acquire_bootstrap_lock()`
    （取得端）。QA 把 `_acquire_bootstrap_lock()` 的邏輯改成『全部存活才忙碌』
    （不安全反轉：只要有一個死的就會誤判整把鎖陳舊）後，既有測試套件零失敗，
    證實這是真實的覆蓋盲區。

    本測試直接建構一個鎖檔內容含『一個已死 PID + 一個存活 PID』的情境，直接
    呼叫 `_acquire_bootstrap_lock()`（不透過 `_peek_bootstrap_lock()`），斷言
    回傳 None（拿不到鎖，因為還有存活成員）——且鎖檔不應被清除。

    MUST FIX A 之後鎖檔語意隨平台改變（POSIX 可能是 process group id、Windows
    是個別 PID），但 `_lock_target_alive()` 對『一般存活 PID』（非 pgid）一律
    先用 `_pid_alive()` 判斷即回真，不需要動用 killpg——故本測試無需區分平台、
    用一個單純的存活子行程即可等價驗證『部分存活即忙碌』這個核心語意，兩平台
    通用。
    """

    def test_partial_alive_pid_list_blocks_acquisition_via_acquire_not_just_peek(self):
        with tempfile.TemporaryDirectory() as td:
            lock_file = Path(td) / ".dev_start.lock"
            dead_pid = os.getpid() + 100000
            while dev_start._pid_alive(dead_pid):
                dead_pid += 1
            alive_proc = subprocess.Popen(
                [sys.executable, "-c", "import time; time.sleep(5)"])
            try:
                lock_file.write_text(json.dumps([dead_pid, alive_proc.pid]),
                                      encoding="utf-8")
                with mock.patch.object(dev_start, "LOCK_FILE", lock_file):
                    result = dev_start._acquire_bootstrap_lock()
                self.assertIsNone(
                    result,
                    "清單中一個 PID 已死、另一個仍存活時，_acquire_bootstrap_lock() "
                    "應拿不到鎖（不可誤判為『全部存活才忙碌』的不安全反轉）")
                self.assertTrue(lock_file.is_file(),
                                 "部分存活的鎖檔不應被 _acquire_bootstrap_lock() 清除")
            finally:
                alive_proc.kill()
                alive_proc.wait()

    def test_all_dead_in_list_is_cleared_and_acquired_for_contrast(self):
        """對照組：清單中全部 PID 皆死透時，才應被視為真正陳舊、可清除重新
        取得——確保上一個測試不是因為函式邏輯整個壞掉（如永遠回傳 None）而
        巧合通過。"""
        with tempfile.TemporaryDirectory() as td:
            lock_file = Path(td) / ".dev_start.lock"
            dead_pid_1 = os.getpid() + 100000
            while dev_start._pid_alive(dead_pid_1):
                dead_pid_1 += 1
            dead_pid_2 = dead_pid_1 + 1
            while dev_start._pid_alive(dead_pid_2):
                dead_pid_2 += 1
            lock_file.write_text(json.dumps([dead_pid_1, dead_pid_2]), encoding="utf-8")
            fd = None
            try:
                with mock.patch.object(dev_start, "LOCK_FILE", lock_file):
                    fd = dev_start._acquire_bootstrap_lock()
                self.assertIsNotNone(fd, "清單中全部 PID 皆死透時應能清除陳舊鎖並重新取得")
            finally:
                if fd is not None:
                    os.close(fd)


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
        return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True,
                              encoding="utf-8", errors="replace")

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
            _rmtree_force(origin)  # 模擬離線：origin 路徑消失，fetch 必失敗

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
            # R3 QA 發現：shebang 腳本（#!/bin/sh）只在 POSIX 上可執行，Windows
            # 上 _venv_healthy() 實際 subprocess.run([py, "--version"]) 會撞
            # WinError 193（非合法 PE 格式），使「健康」情境在 Windows 上永遠
            # 走到「不健康」分支——改複製當前真正在跑的直譯器本體（含 pyvenv.cfg，
            # 見 _copy_functional_interpreter），三平台皆為合法可執行檔，能真實
            # 驗證 _venv_healthy() 的 subprocess 呼叫成功。
            _copy_functional_interpreter(py)
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
            self.assertEqual(restored_py.read_bytes(), Path(sys.executable).read_bytes(),
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


class TestRecordLockPids(DevStartTestCase):
    """本輪核心修法之一：_record_lock_pids() 把鎖檔內容從 orchestrator PID
    改寫成真正執行 bootstrap 的子行程 PID 清單（JSON 陣列），驗證覆寫行為
    正確（截斷舊內容、不是附加）。MUST FIX #2 起改為接受 PID 清單而非單一 PID。
    """

    def test_overwrites_lock_file_content_with_given_pids(self):
        with tempfile.TemporaryDirectory() as td:
            lock_file = Path(td) / ".dev_start.lock"
            fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, str(os.getpid()).encode("utf-8"))
                dev_start._record_lock_pids(fd, [999999])
            finally:
                os.close(fd)
            self.assertEqual(
                json.loads(lock_file.read_text(encoding="utf-8")), [999999])

    def test_overwrite_with_shorter_content_leaves_no_trailing_garbage(self):
        """舊內容（如 "123456789"）比新內容（如 "[42]"）長時，若忘記
        ftruncate，檔案會殘留舊內容尾巴而非乾淨的 "[42]"。"""
        with tempfile.TemporaryDirectory() as td:
            lock_file = Path(td) / ".dev_start.lock"
            fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, b"123456789")
                dev_start._record_lock_pids(fd, [42])
            finally:
                os.close(fd)
            self.assertEqual(json.loads(lock_file.read_text(encoding="utf-8")), [42])

    def test_records_multiple_pids_sorted(self):
        with tempfile.TemporaryDirectory() as td:
            lock_file = Path(td) / ".dev_start.lock"
            fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                dev_start._record_lock_pids(fd, [999, 111, 555])
            finally:
                os.close(fd)
            self.assertEqual(
                json.loads(lock_file.read_text(encoding="utf-8")), [111, 555, 999])


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


class TestStreamOtherOSErrorDoesNotCrash(DevStartTestCase):
    """MUST FIX 3（SA 複審發現，P2）：`_stream()` 過去只 catch `FileNotFoundError`。
    若執行環境限制 `setsid()`（例如受限 seccomp/沙盒設定拒絕該系統呼叫），
    `Popen(..., start_new_session=True)` 會在子行程端呼叫失敗、經內部 pipe
    回報，父行程端拋出 `PermissionError`（`OSError` 子類別，但不是
    `FileNotFoundError`）——SA 用函式層級 mock 實測驗證這個例外先前完全沒被
    攔截，會直接向上傳播讓整支工具在 `_run_bootstrap()`/`step_venv()`/`main()`
    裸崩潰。

    本測試 mock `subprocess.Popen` 拋出 `PermissionError`，驗證 `_stream()` 不
    裸崩潰、回傳合理的非零 rc 並印出警告，而不是讓例外往上炸穿。
    """

    def test_permission_error_from_popen_returns_nonzero_without_crashing(self):
        with mock.patch.object(
                dev_start.subprocess, "Popen",
                side_effect=PermissionError("setsid() 遭沙盒拒絕")):
            rc = dev_start._stream(["irrelevant-cmd"])
        self.assertIsInstance(rc, int)
        self.assertNotEqual(rc, 0, "Popen 失敗不可被誤判為成功")

    def test_other_oserror_from_popen_also_does_not_crash(self):
        """對照組：不只 PermissionError，任意其他非 FileNotFoundError 的
        OSError 子類別（如 BlockingIOError）也必須走同一條安全網分支，證明
        修法接住的是『OSError 大類』而非只特化處理 PermissionError 這一種。"""
        with mock.patch.object(
                dev_start.subprocess, "Popen",
                side_effect=BlockingIOError("模擬其他 OSError 子類別")):
            rc = dev_start._stream(["irrelevant-cmd"])
        self.assertIsInstance(rc, int)
        self.assertNotEqual(rc, 0)

    def test_file_not_found_still_returns_127_not_swallowed_by_broader_oserror(self):
        """對照組：擴大 except 範圍後，FileNotFoundError 的既有語意（rc=127，
        訊息為『找不到指令』）不可被更廣的 OSError 分支蓋掉——必須確認
        except 子句宣告順序仍讓 FileNotFoundError 優先匹配。"""
        rc = dev_start._stream(["definitely-not-a-real-command-xyz"])
        self.assertEqual(rc, 127)

    def test_run_bootstrap_propagates_false_instead_of_crashing_on_oserror(self):
        """端到端：_run_bootstrap() 呼叫鏈上真正會踩到此例外的路徑
        （_stream() 內 Popen 失敗）不應讓 _run_bootstrap() 裸崩潰，而是要能
        繼續完成收尾（哨兵/鎖狀態）並回傳可預期的結果，供 step_venv()/main()
        正常往下走錯誤處理路徑，而非整支工具中止。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with mock.patch.object(dev_start, "ROOT", root), \
                 mock.patch.object(
                     dev_start.subprocess, "Popen",
                     side_effect=PermissionError("setsid() 遭沙盒拒絕")):
                try:
                    ok = dev_start._run_bootstrap("mac", "測試原因")
                except OSError:
                    self.fail("_run_bootstrap() 不應讓 Popen 的 OSError 裸崩穿透")
            self.assertFalse(ok, "_stream() 回傳非零 rc 時 _run_bootstrap() 應回傳 False")


class TestStreamNewProcessGroup(DevStartTestCase):
    """MUST FIX A：`_stream(new_process_group=True)` 的基本行為——POSIX 上應讓
    子行程自身 PID 等於其 pgid（`start_new_session=True` 語意）；Windows 上
    絕不可把 `start_new_session` 傳給 `subprocess.Popen`（Python 文件明載該
    參數為 POSIX-only，Windows 上傳入非假值會拋 `ValueError`）。
    """

    @unittest.skipIf(os.name == "nt", "pgid 語意僅適用 POSIX")
    def test_posix_child_pid_equals_its_own_pgid(self):
        captured: dict = {}

        def on_start(pid):
            captured["pid"] = pid
            captured["pgid"] = os.getpgid(pid)

        rc = dev_start._stream(
            [sys.executable, "-c", "import time; time.sleep(0.2)"],
            on_start=on_start,
            new_process_group=True,
        )
        self.assertEqual(rc, 0)
        self.assertEqual(captured["pgid"], captured["pid"],
                          "start_new_session=True 應使子行程自身 PID 等於其 pgid")

    def test_windows_never_receives_start_new_session_kwarg(self):
        captured_kwargs: dict = {}

        class FakeProc:
            pid = 4242

            def wait(self):
                return 0

        def fake_popen(_cmd, **kwargs):
            captured_kwargs.update(kwargs)
            return FakeProc()

        with mock.patch.object(dev_start.os, "name", "nt"), \
             mock.patch.object(dev_start.subprocess, "Popen", side_effect=fake_popen):
            rc = dev_start._stream(["irrelevant"], new_process_group=True)

        self.assertEqual(rc, 0)
        self.assertNotIn(
            "start_new_session", captured_kwargs,
            "Windows 上不可傳遞 start_new_session（POSIX-only kwarg，Windows 上"
            "subprocess.Popen 對非假值會拋 ValueError）")

    @unittest.skipIf(os.name == "nt", "pgid 語意僅適用 POSIX")
    def test_new_process_group_false_does_not_isolate(self):
        """對照組：new_process_group 預設 False（既有呼叫端，如 git pull／hooks
        安裝）不應被本輪修改影響——子行程仍與呼叫端同一 process group。"""
        captured: dict = {}

        def on_start(pid):
            captured["pid"] = pid
            captured["pgid"] = os.getpgid(pid)  # 須在子行程仍存活時查詢

        rc = dev_start._stream(
            [sys.executable, "-c", "import time; time.sleep(0.2)"],
            on_start=on_start,
        )
        self.assertEqual(rc, 0)
        self.assertEqual(
            captured["pgid"], os.getpgid(0),
            "未指定 new_process_group 時，子行程應沿用呼叫端的 process group"
            "（不應獨立成新 session），維持既有 Ctrl-C 行為不變")


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
            pid = proc.pid
            try:
                lock_file.write_text(str(pid), encoding="utf-8")
                with mock.patch.object(dev_start, "LOCK_FILE", lock_file):
                    self.assertEqual(dev_start._peek_bootstrap_lock(), pid,
                                      "① 子行程存活期間 peek 應回傳其 PID")
                proc.wait(timeout=5)
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
            # R3 QA 發現（Windows-only）：Popen 物件本身持有子行程 handle，即使
            # 子行程已真正結束，只要此 handle 未關閉，Windows 仍視該行程物件為
            # 存活（OpenProcess 可成功開啟），造成 _pid_alive() 誤判仍存活——這
            # 與正式場景（另一個全新 dev_start 行程檢查陌生 PID、從未持有其
            # handle）不同，顯式釋放本行程自己持有的 handle 才能正確模擬「已
            # 終止且無人持有」的情境。POSIX 上 del 對測試結果無影響。
            del proc
            with mock.patch.object(dev_start, "LOCK_FILE", lock_file):
                self.assertIsNone(dev_start._peek_bootstrap_lock(),
                                   "② 子行程結束後 peek 應回傳 None")

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


class TestStreamNewProcessGroupSurvivesDirectChildDeath(DevStartTestCase):
    """MUST FIX A 核心迴歸測試（Architect 第三輪複審用真實驗證證明「事後 ppid
    回溯」在因果上必然太晚：production 呼叫鏈是 `_stream()` 的 `proc.wait()`
    等到直接子行程確實死亡才返回 → `_run_bootstrap()` 返回 → `step_venv()` 才
    呼叫回溯邏輯，此時直接子行程的 ppid 早已被核心過繼給 subreaper，以其 PID
    為根的事後回溯注定撲空）。

    根本重做：`_stream(new_process_group=True)` 讓 bootstrap 直接子行程呼叫
    `start_new_session=True`（POSIX 對應 `setsid()`），使其成為新 session 的
    group leader——其自身 PID 同時即為 process group id。之後不論該子行程
    fork 出多少層、多少個孫行程，只要仍有任一成員存活，`os.killpg(pgid, 0)`
    就會成功；這不受「父行程死亡時子行程 ppid 被核心過繼」影響，因為過繼只
    改變 ppid，不改變 process group membership。本測試用真實 subprocess（非
    函式層級 mock）直接驗證這個核心因果宣稱本身。
    """

    @unittest.skipIf(os.name == "nt",
                      "process group / os.killpg 僅適用 POSIX；Windows 維持既有"
                      " _DescendantWatcher 設計，見 dev_start.py 對應 docstring")
    def test_killpg_survives_direct_child_kill_while_grandchild_alive(self):
        with tempfile.TemporaryDirectory() as td:
            pidfile = Path(td) / "grandchild.pid"
            script = (
                "import subprocess, sys\n"
                "gc = subprocess.Popen([sys.executable, '-c', "
                "'import time; time.sleep(5)'])\n"
                f"open({str(pidfile)!r}, 'w').write(str(gc.pid))\n"
                "gc.wait()\n"
            )
            result: dict = {}

            def runner():
                result["rc"] = dev_start._stream(
                    [sys.executable, "-c", script],
                    on_start=lambda pid: result.setdefault("pgid", pid),
                    new_process_group=True,
                )

            thread = threading.Thread(target=runner)
            thread.start()
            try:
                deadline = time.monotonic() + 5
                while "pgid" not in result and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertIn("pgid", result, "應已透過 on_start 取得直接子行程 PID（測試前提）")
                pgid = result["pgid"]
                self.assertEqual(os.getpgid(pgid), pgid,
                                  "new_process_group=True 應使直接子行程自身 PID 等於其 pgid"
                                  "（setsid 語意）")

                deadline = time.monotonic() + 5
                while not pidfile.is_file() and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertTrue(pidfile.is_file(), "孫行程應已 fork 出來（測試前提）")
                grandchild_pid = int(pidfile.read_text(encoding="utf-8").strip())

                # 模擬使用者/監控工具只精準 kill 掉直接子行程（不碰整個 group）
                os.kill(pgid, signal.SIGKILL)
                thread.join(timeout=10)
                self.assertFalse(thread.is_alive(), "背景執行緒應已隨直接子行程死亡而結束")
                self.assertLess(result["rc"], 0, "直接子行程應被訊號終止（負值 rc）")

                # 核心斷言：直接子行程已死，但孫行程仍存活——os.killpg 不受 ppid
                # 過繼影響，仍應成功（不像事後 ps 回溯注定撲空）。
                try:
                    os.killpg(pgid, 0)
                except ProcessLookupError:
                    self.fail("直接子行程死亡但孫行程仍存活時，os.killpg 不應回報"
                              "process group 已消失——這正是本輪要修的因果性 bug")

                deadline = time.monotonic() + 6
                while dev_start._pid_alive(grandchild_pid) and time.monotonic() < deadline:
                    time.sleep(0.1)
                self.assertFalse(dev_start._pid_alive(grandchild_pid), "孫行程應已結束（測試前提）")

                with self.assertRaises(ProcessLookupError):
                    os.killpg(pgid, 0)
            finally:
                if thread.is_alive():
                    thread.join(timeout=5)


class TestBootstrapProcessGroupSurvivesDirectChildKill(DevStartTestCase):
    """MUST FIX A 迴歸測試（取代舊版 TestGrandchildOrphanSurvivesDirectChildKill /
    TestMultiGrandchildLockNotPrematurelyStale 對『事後 ppid 回溯』的測試方式）：
    Architect 第三輪複審已用真實驗證證明那個修法在因果上必然無效（見上方
    TestStreamNewProcessGroupSurvivesDirectChildDeath 與 dev_start.py 內
    `_stream`/`_lock_target_alive`/`_DescendantWatcher` docstring 的完整推導），
    舊測試的 `root_pid` 用的是測試行程自己（全程沒有死亡），跟真正的 bug
    （直接子行程本身已經死亡、孫行程被過繼）完全是兩回事。

    新設計：`_run_bootstrap()` 對 POSIX 呼叫 `_stream(..., new_process_group=True)`，
    讓直接子行程以 `start_new_session=True` 成為新 session 的 group leader
    （pgid == 自身 PID）。`step_venv()` 不再需要背景輪詢採樣後代 PID——直接用
    `os.killpg(pgid, 0)` 判斷整個 group（含任意數量、任意深度的孫行程）是否
    仍有成員存活，鎖檔內容全程維持記錄這一個 pgid 不變，不需要『事後發現多個
    孫行程 PID 再改寫鎖檔』（舊設計 MUST FIX #2 修的『只記錄 min(live) 單一
    PID』整個 bug class，在 pgid + killpg 設計下結構性不可能發生）。

    本測試模擬兩個孫行程（壽命不同）一次驗證：①任一孫行程存活時鎖不釋放；
    ②鎖檔內容全程是最初的 pgid（不像舊設計需要改寫成觀察到的孫行程 PID）；
    ③下一輪 `_peek_bootstrap_lock()` 透過 `_lock_target_alive()` 的 killpg
    fallback 仍正確判斷忙碌；④兩個孫行程都結束後鎖能被正常清除重新取得，不
    會永久卡死。
    """

    @unittest.skipIf(os.name == "nt",
                      "process group / os.killpg 僅適用 POSIX；Windows 維持既有"
                      " _DescendantWatcher 設計，見 dev_start.py 對應分支")
    def test_lock_stays_busy_via_killpg_while_any_grandchild_alive_then_clears(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            lock_file = root / ".dev_start.lock"
            pidfile_a = root / "grandchild_a.pid"
            pidfile_b = root / "grandchild_b.pid"

            # 假 bootstrap 的直接子行程：前景 fork 出兩個壽命不同的孫行程並等待
            # 兩者結束——A 壽命短，B 壽命長（比照真實 uv 平行化下載時各任務
            # 耗時不同）。
            direct_child_script = (
                "import subprocess, sys\n"
                "gc_a = subprocess.Popen([sys.executable, '-c', "
                "'import time; time.sleep(2)'])\n"
                "gc_b = subprocess.Popen([sys.executable, '-c', "
                "'import time; time.sleep(6)'])\n"
                f"open({str(pidfile_a)!r}, 'w').write(str(gc_a.pid))\n"
                f"open({str(pidfile_b)!r}, 'w').write(str(gc_b.pid))\n"
                "gc_a.wait()\n"
                "gc_b.wait()\n"
            )
            direct_child_holder: dict = {}

            def fake_stream(_cmd, on_start=None, **_kwargs):
                # 模擬 _stream(new_process_group=True) 的真實行為：只 mock
                # 「跑哪個指令」這一層（不用真的 bootstrap.sh），行程樹本身
                # 的 OS 語意（start_new_session=True）如實重現。
                direct_child = subprocess.Popen(
                    [sys.executable, "-c", direct_child_script],
                    start_new_session=True,
                )
                direct_child_holder["proc"] = direct_child
                if on_start is not None:
                    on_start(direct_child.pid)
                for _ in range(100):  # 最多等 5s 讓兩個孫行程真的 fork 出來
                    if pidfile_a.is_file() and pidfile_b.is_file():
                        break
                    time.sleep(0.05)
                time.sleep(0.3)
                # 模擬使用者/監控工具只 kill 掉直接子行程本身（不碰整個 group）
                os.kill(direct_child.pid, signal.SIGKILL)
                return direct_child.wait()  # 被 SIGKILL：負值 rc

            try:
                with mock.patch.object(dev_start, "ROOT", root), \
                     mock.patch.object(dev_start, "LOCK_FILE", lock_file), \
                     mock.patch.object(dev_start, "_ensure_venv_shape", return_value="ok"), \
                     mock.patch.object(dev_start, "_deps_hash", return_value="h"), \
                     mock.patch.object(dev_start, "_stream", side_effect=fake_stream):
                    ok = dev_start.step_venv("mac", {}, force=True)

                self.assertTrue(pidfile_a.is_file() and pidfile_b.is_file(),
                                 "兩個孫行程應已 fork 出來（測試前提）")
                pid_a = int(pidfile_a.read_text(encoding="utf-8").strip())
                pid_b = int(pidfile_b.read_text(encoding="utf-8").strip())
                pgid = direct_child_holder["proc"].pid

                self.assertFalse(ok, "任一孫行程仍存活時 step_venv 應回報失敗")
                self.assertTrue(lock_file.is_file(), "孫行程仍存活時鎖檔不應被移除")
                self.assertTrue(
                    any("process group" in w and "仍有行程存活" in w for w in dev_start.WARNINGS),
                    "應有明確警告告知 bootstrap process group 仍有行程存活、鎖未釋放")

                recorded = json.loads(lock_file.read_text(encoding="utf-8"))
                self.assertEqual(recorded, [pgid],
                                  "鎖檔內容應全程是最初記錄的 pgid（直接子行程自身 PID），"
                                  "不需要像舊設計那樣事後改寫成觀察到的孫行程 PID")

                # 等 A（短命）先結束，此時 B（長壽命）應仍存活
                deadline = time.monotonic() + 5
                while dev_start._pid_alive(pid_a) and time.monotonic() < deadline:
                    time.sleep(0.1)
                self.assertFalse(dev_start._pid_alive(pid_a), "A 應已結束（測試前提）")
                self.assertTrue(dev_start._pid_alive(pid_b), "B 應仍存活（測試前提）")

                with mock.patch.object(dev_start, "LOCK_FILE", lock_file):
                    still_busy = dev_start._peek_bootstrap_lock()
                self.assertIsNotNone(
                    still_busy,
                    "直接子行程已死、A 已死，但 B（孫行程）仍存活時，鎖不應被誤判陳舊"
                    "——os.killpg(pgid, 0) 只要 group 內任一成員存活就會成功，不像"
                    "事後 ppid 回溯需要逐一追蹤個別 PID")

                # 等 B 也結束，鎖才應能被正常清除重新取得
                deadline = time.monotonic() + 8
                while dev_start._pid_alive(pid_b) and time.monotonic() < deadline:
                    time.sleep(0.1)
                self.assertFalse(dev_start._pid_alive(pid_b), "B 應已結束（測試前提）")

                with mock.patch.object(dev_start, "LOCK_FILE", lock_file):
                    fd = dev_start._acquire_bootstrap_lock()
                self.assertIsNotNone(fd, "A、B 皆已結束後，鎖應能被正常清除並重新取得")
                if fd is not None:
                    os.close(fd)
                    lock_file.unlink(missing_ok=True)
            finally:
                proc = direct_child_holder.get("proc")
                if proc is not None and proc.poll() is None:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except OSError:
                        pass
                    proc.wait()


class TestSigintForwardsToBootstrapProcessGroup(DevStartTestCase):
    """MUST FIX A 必要配套的迴歸測試（POSIX only）：`_stream(new_process_group=True)`
    讓 bootstrap 直接子行程脫離終端機 foreground process group 後，使用者按
    Ctrl-C（SIGINT 只送到 foreground process group）將不再自然傳到 bootstrap
    樹，可能讓它在背景孤兒繼續跑而使用者誤以為已中止。

    本測試用『真實訊號』（而非函式層級 mock）驗證：dev_start.py 安裝
    `_forward_signal_to_bootstrap_group` 為 SIGINT handler 後，模擬使用者在
    bootstrap 執行期間按 Ctrl-C（對自己送出真實 SIGINT），驗證整個 bootstrap
    process group（含直接子行程與孫行程）確實收到訊號終止，不會變成背景孤兒
    繼續執行。
    """

    def setUp(self) -> None:
        super().setUp()
        dev_start._set_active_bootstrap_pgid(None)

    def tearDown(self) -> None:
        dev_start._set_active_bootstrap_pgid(None)
        super().tearDown()

    @unittest.skipIf(os.name == "nt", "SIGINT/os.killpg 訊號轉發僅適用 POSIX；"
                      "Windows 未使用 start_new_session，既有 Ctrl-C 行為不變（見"
                      " main() 內對應安裝條件）")
    def test_real_sigint_terminates_direct_child_and_grandchild(self):
        with tempfile.TemporaryDirectory() as td:
            pidfile = Path(td) / "grandchild.pid"
            script = (
                "import subprocess, sys\n"
                "gc = subprocess.Popen([sys.executable, '-c', "
                "'import time; time.sleep(30)'])\n"
                f"open({str(pidfile)!r}, 'w').write(str(gc.pid))\n"
                "gc.wait()\n"
            )
            result: dict = {}

            def runner():
                def on_start(pid):
                    dev_start._set_active_bootstrap_pgid(pid)
                    result["pgid"] = pid
                result["rc"] = dev_start._stream(
                    [sys.executable, "-c", script],
                    on_start=on_start,
                    new_process_group=True,
                )

            thread = threading.Thread(target=runner)
            old_handler = signal.signal(signal.SIGINT,
                                         dev_start._forward_signal_to_bootstrap_group)
            try:
                thread.start()
                deadline = time.monotonic() + 5
                while "pgid" not in result and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertIn("pgid", result, "應已取得直接子行程 pgid（測試前提）")

                deadline = time.monotonic() + 5
                while not pidfile.is_file() and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertTrue(pidfile.is_file(), "孫行程應已 fork 出來（測試前提）")
                grandchild_pid = int(pidfile.read_text(encoding="utf-8").strip())

                # 模擬使用者在 bootstrap 執行期間按下 Ctrl-C：對自己送出真實 SIGINT
                time.sleep(0.1)
                os.kill(os.getpid(), signal.SIGINT)

                thread.join(timeout=10)
                self.assertFalse(thread.is_alive(),
                                  "handler 轉發訊號後，直接子行程應已終止、背景執行緒應已結束")
                self.assertLess(result["rc"], 0, "直接子行程應被訊號終止（負值 rc）")

                deadline = time.monotonic() + 3
                while dev_start._pid_alive(grandchild_pid) and time.monotonic() < deadline:
                    time.sleep(0.1)
                self.assertFalse(
                    dev_start._pid_alive(grandchild_pid),
                    "孫行程應已隨 process group 一併終止，而非變成背景孤兒繼續執行")
            finally:
                signal.signal(signal.SIGINT, old_handler)
                if thread.is_alive():
                    thread.join(timeout=5)

    def test_no_active_bootstrap_falls_back_to_keyboard_interrupt(self):
        """對照組：沒有進行中的 bootstrap 時（如 step_sync/step_hooks 期間），
        handler 應退回 Python 預設行為（拋出 KeyboardInterrupt），不改變既有
        Ctrl-C 語意——這是 handler 的『安全網』分支，須直接單元測試（不涉及
        真實子行程）。"""
        self.assertIsNone(dev_start._ACTIVE_BOOTSTRAP_PGID)
        with self.assertRaises(KeyboardInterrupt):
            dev_start._forward_signal_to_bootstrap_group(signal.SIGINT, None)


class TestNormalBootstrapFlowUnaffectedByProcessGroupChange(DevStartTestCase):
    """交付要求 2(i)：MUST FIX A 是一個牽涉「子行程怎麼被產生」的結構性改動
    （`_stream()` 新增 `new_process_group=True` 分支、`step_venv()` 改走 pgid/
    killpg 路徑），必須用真實 subprocess 端到端驗證『正常成功的 bootstrap 流程
    完全不受影響』——不能只驗證新機制本身，還要證明沒有把好路徑弄壞：rc 仍
    正確傳遞（0）、真實孫行程仍能正常結束、鎖仍會在成功後正常釋放（不會被
    誤判為『process group 仍有人存活』而卡住）、`_ACTIVE_BOOTSTRAP_PGID` 仍會
    在流程結束後正確清除。
    """

    @unittest.skipIf(os.name == "nt", "pgid 語意僅適用 POSIX；Windows 分支未變動")
    def test_successful_bootstrap_with_short_lived_grandchild_releases_lock_cleanly(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            lock_file = root / ".dev_start.lock"
            venv_python = root / ".venv" / "bin" / "python"

            # 模擬真實 bootstrap.sh 正常成功：前景 fork 一個短命孫行程（如
            # pip install 的子步驟）並等它結束，接著建好 venv 直譯器、rc=0。
            direct_child_script = (
                "import subprocess, sys\n"
                "gc = subprocess.Popen([sys.executable, '-c', 'pass'])\n"
                "gc.wait()\n"
            )

            def fake_stream(_cmd, on_start=None, **_kwargs):
                direct_child = subprocess.Popen(
                    [sys.executable, "-c", direct_child_script],
                    start_new_session=True,
                )
                if on_start is not None:
                    on_start(direct_child.pid)
                rc = direct_child.wait()
                if rc == 0:
                    venv_python.parent.mkdir(parents=True, exist_ok=True)
                    venv_python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                    venv_python.chmod(0o755)
                return rc

            with mock.patch.object(dev_start, "ROOT", root), \
                 mock.patch.object(dev_start, "LOCK_FILE", lock_file), \
                 mock.patch.object(dev_start, "_ensure_venv_shape", return_value="missing"), \
                 mock.patch.object(dev_start, "_deps_hash", return_value="h"), \
                 mock.patch.object(dev_start, "_venv_python", return_value=venv_python), \
                 mock.patch.object(dev_start, "_stream", side_effect=fake_stream):
                ok = dev_start.step_venv("mac", {}, force=True)

            self.assertTrue(ok, "正常成功的 bootstrap 流程應回報成功，不受 pgid 改動影響")
            self.assertIn("bootstrap 完成", dev_start.SUMMARY.get("venv", ""))
            self.assertFalse(lock_file.is_file(), "成功且行程樹已全數結束時，鎖應正常釋放")
            self.assertIsNone(
                dev_start._ACTIVE_BOOTSTRAP_PGID,
                "_run_bootstrap() 返回後，無論成功與否都應清除 _ACTIVE_BOOTSTRAP_PGID"
                "（避免遺留給下一次無關的 Ctrl-C 誤轉發）")

    @unittest.skipIf(os.name == "nt", "pgid 語意僅適用 POSIX；Windows 分支未變動")
    def test_stream_rc_and_stdout_passthrough_unaffected_by_new_process_group(self):
        """對照組：`_stream(new_process_group=True)` 對一個會印出 stdout 且
        正常結束的指令，rc 仍正確傳遞、且 Popen 未攔截 stdout（維持即時可見，
        不因新增 process group 隔離而被緩衝/吞掉）。"""
        marker = "DEV_START_STREAM_PASSTHROUGH_CHECK"
        inner_cmd = [sys.executable, "-c", f"print({marker!r})"]
        outer_script = (
            "import sys, dev_start\n"
            f"rc = dev_start._stream({inner_cmd!r}, new_process_group=True)\n"
            "sys.exit(rc)\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", outer_script],
            cwd=str(Path(dev_start.__file__).resolve().parent),
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
        )
        self.assertEqual(proc.returncode, 0, f"stderr={proc.stderr}")
        self.assertIn(marker, proc.stdout,
                      "new_process_group=True 不應攔截/吞掉子行程 stdout —— "
                      "Popen 未設定 stdout=PIPE，應照常繼承並即時可見")


class TestDescendantWatcherFinalSyncSampleWindows(DevStartTestCase):
    """MUST FIX #3 迴歸測試（Windows 版）：`_DescendantWatcher` 自 MUST FIX A
    起僅供 Windows 使用（POSIX 已改用 pgid + os.killpg，見上方兩個新測試類別）；
    舊版 `TestDescendantWatcherFinalSyncSample` 是在這台 macOS 開發機上直接
    呼叫 `_DescendantWatcher`，實際命中的是已被移除的 POSIX 分支
    （`_list_pid_ppid_pairs_posix`）——該分支代表的機制在生產環境已不再被任何
    平台呼叫（POSIX 不用，且該分支本身已刪除），繼續測它沒有意義。

    本測試改用 `mock ctypes.windll` 的既有慣例（比照 `TestPidAliveWindowsBranch`）
    模擬 Windows Toolhelp32 API，在 Windows 分支上重新驗證 MUST FIX #3 這個
    「stop_and_collect() 必須自己補一次同步採樣、不能只靠背景執行緒排程」的
    修復——這個機制對 Windows 而言仍然成立且仍在生產程式碼路徑上（見
    `_DescendantWatcher` docstring：Windows 的 th32ParentProcessID 是靜態
    快照，事後回溯本身沒有 POSIX 那個因果性缺陷，但『背景輪詢的取樣空窗』
    這個獨立問題兩平台通用，仍需要 stop_and_collect() 的同步補採樣）。
    """

    def test_child_born_in_polling_gap_is_still_captured_on_windows(self):
        root_pid = 42
        grandchild_pid = 4242
        state = {"grandchild_born": False}

        class FakeEntry:
            th32ProcessID = 0
            th32ParentProcessID = 0

        class FakeKernel32:
            def CreateToolhelp32Snapshot(self, _flags, _pid):
                return 1  # 非 0/-1 的假 handle

            def Process32First(self, _snapshot, entry_ptr):
                pairs = self._current_pairs()
                self._pairs = pairs
                self._idx = 0
                return self._fill(entry_ptr)

            def Process32Next(self, _snapshot, entry_ptr):
                self._idx += 1
                return self._fill(entry_ptr)

            def _current_pairs(self):
                base = [(root_pid, 1)]
                if state["grandchild_born"]:
                    base.append((grandchild_pid, root_pid))
                return base

            def _fill(self, entry_ptr):
                if self._idx >= len(self._pairs):
                    return 0
                pid, ppid = self._pairs[self._idx]
                entry_ptr.contents.th32ProcessID = pid
                entry_ptr.contents.th32ParentProcessID = ppid
                return 1

            def CloseHandle(self, _snapshot):
                return 1

        fake_windll = mock.Mock(kernel32=FakeKernel32())
        with mock.patch.object(ctypes, "windll", fake_windll, create=True), \
             mock.patch.object(dev_start.os, "name", "nt"):
            # 放大 poll_interval（3 秒）讓背景執行緒排定的下一次採樣遠晚於孫
            # 行程誕生與 stop_and_collect() 被呼叫的時間點，決定性重現空窗。
            watcher = dev_start._DescendantWatcher(root_pid, poll_interval=3.0)
            watcher.start()
            time.sleep(0.1)  # 讓背景執行緒完成「第一次」採樣（此時孫行程尚未誕生）

            state["grandchild_born"] = True
            time.sleep(0.05)
            observed = watcher.stop_and_collect()

        self.assertIn(
            grandchild_pid, observed,
            "stop_and_collect() 應透過同步補採樣抓到剛誕生的孫行程，"
            "即使背景執行緒尚未排到下一次採樣（poll_interval 空窗）——"
            "Windows 上此機制仍在生產程式碼路徑上，須維持通過")


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
            # R3 QA 發現：shebang 腳本在 Windows 上非合法 PE、_venv_healthy() 會撞
            # WinError 193，改複製當前真正在跑的直譯器本體（含 pyvenv.cfg，見
            # _copy_functional_interpreter），三平台皆可真實執行。
            _copy_functional_interpreter(venv_python)
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


class TestBootstrapIncompleteMarker(DevStartTestCase):
    """MUST FIX #2 迴歸測試：Architect 發現 venv 建立成功但 pip install 失敗時
    （tools/bootstrap.sh 用 set -euo pipefail，兩步驟獨立），bootstrap 回傳非 0
    → main() 跳過 step_finalize()，狀態檔不寫入。使用者重跑時 state={}（prev=None）
    但 .venv/bin/python 已存在 → 過去只做 _venv_healthy()（只驗證 python --version
    能跑，不驗證套件是否裝好）就沿用，把「其實半殘」的 venv 靜默漂白成功。
    修復後：bootstrap 失敗且 .venv 已建立時寫入哨兵；下次即使健檢通過，哨兵
    存在也要視同壞損、改走正常 bootstrap 路徑。
    """

    def test_partial_failure_leaves_marker_and_forces_rebootstrap_next_run(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            venv_python = root / ".venv" / "bin" / "python"

            def fake_stream_partial_failure(_cmd, on_start=None, **_kwargs):
                # 模擬 tools/bootstrap.sh 的真實行為：venv 建立成功（bin/python
                # 出現）但後段 pip install 失敗，整體 bootstrap 回傳非 0。哨兵
                # 邏輯寫在 _run_bootstrap() 內部，故這裡改 mock 更底層的
                # _stream()，讓真正的 _run_bootstrap() 執行（含哨兵讀寫）。
                venv_python.parent.mkdir(parents=True, exist_ok=True)
                # R3 QA 發現：shebang 腳本在 Windows 上非合法 PE、_venv_healthy()
                # 會撞 WinError 193，改複製當前真正在跑的直譯器本體（含 pyvenv.cfg，
                # 見 _copy_functional_interpreter）。
                _copy_functional_interpreter(venv_python)
                venv_python.chmod(0o755)
                return 1

            with mock.patch.object(dev_start, "ROOT", root), \
                 mock.patch.object(dev_start, "LOCK_FILE", root / ".dev_start.lock"), \
                 mock.patch.object(dev_start, "_ensure_venv_shape", return_value="missing"), \
                 mock.patch.object(dev_start, "_deps_hash", return_value="h"), \
                 mock.patch.object(dev_start, "_stream",
                                    side_effect=fake_stream_partial_failure):
                first_ok = dev_start.step_venv("mac", {}, force=False)

            self.assertFalse(first_ok, "bootstrap 失敗時 step_venv 應回傳 False")
            marker = root / ".venv" / dev_start._BOOTSTRAP_INCOMPLETE_MARKER
            self.assertTrue(marker.is_file(), "bootstrap 部分失敗後哨兵應保留在 .venv 內")

            # main() 會在 ok=False 時跳過 step_finalize()，狀態檔不寫入
            # → 下次重跑時 state 仍是 {}（prev=None），但 .venv/bin/python 已存在
            # → _ensure_venv_shape() 會回傳 "ok"（本平台直譯器存在）。
            dev_start.WARNINGS.clear()
            dev_start.SUMMARY.clear()
            second_bootstrap_calls = []

            def fake_run_bootstrap_second(_now, reason, on_start=None):
                second_bootstrap_calls.append(reason)
                dev_start._clear_bootstrap_incomplete(root / ".venv")
                return True

            with mock.patch.object(dev_start, "ROOT", root), \
                 mock.patch.object(dev_start, "LOCK_FILE", root / ".dev_start.lock"), \
                 mock.patch.object(dev_start, "_ensure_venv_shape", return_value="ok"), \
                 mock.patch.object(dev_start, "_deps_hash", return_value="h"), \
                 mock.patch.object(dev_start, "_venv_python", return_value=venv_python), \
                 mock.patch.object(dev_start, "_write_origin_marker"), \
                 mock.patch.object(dev_start, "_run_bootstrap",
                                    side_effect=fake_run_bootstrap_second):
                second_ok = dev_start.step_venv("mac", {}, force=False)

            self.assertTrue(second_ok)
            self.assertEqual(len(second_bootstrap_calls), 1,
                              "哨兵殘留時，第二次呼叫應觸發重新 bootstrap，"
                              "而非誤判『既有 .venv 沿用』靜默漂白成功")
            self.assertIn("哨兵", second_bootstrap_calls[0])
            self.assertNotIn("沿用既有", dev_start.SUMMARY.get("venv", ""))

    def test_healthy_and_no_marker_still_reuses_without_bootstrap(self):
        """對照組：健檢通過且無哨兵殘留時，仍應維持原行為（沿用既有 .venv，
        不因本輪新增的哨兵檢查而誤觸發不必要的重裝）。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            venv_python = root / ".venv" / "bin" / "python"
            venv_python.parent.mkdir(parents=True)
            # R3 QA 發現：shebang 腳本在 Windows 上非合法 PE、_venv_healthy() 會撞
            # WinError 193，改複製當前真正在跑的直譯器本體（含 pyvenv.cfg，見
            # _copy_functional_interpreter），三平台皆可真實執行。
            _copy_functional_interpreter(venv_python)
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
            self.assertEqual(bootstrap_calls, [], "無哨兵殘留時不應觸發 bootstrap")
            self.assertIn("沿用既有", dev_start.SUMMARY.get("venv", ""))


class TestRootLevelBootstrapIncompleteMarker(DevStartTestCase):
    """MUST FIX #4 迴歸測試（Architect 複審發現，門檻遠低於原本描述的 P1）：
    首次建置期間，最普通的 Ctrl-C 會讓 SIGINT 同時打中 dev_start.py 本體與
    bootstrap 子行程（前景 process group），dev_start.py 立即死亡，
    `_run_bootstrap()` 內 `rc = _stream(...)` 之後的「rc!=0 補寫哨兵」程式碼
    永遠執行不到——過去 `.venv` 內部哨兵只在 `.venv` 目錄「已存在」時才會於
    呼叫 bootstrap 前先寫入，對「首次建置、.venv 完全不存在」這個情境完全沒有
    防護。修復後 ROOT 層級哨兵無條件於呼叫 `_stream()` 之前落地，不受 `.venv`
    是否存在限制、也不依賴任何「`_stream()` 之後」才執行到的程式碼。
    """

    def test_root_marker_survives_process_death_before_stream_returns(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # 模擬「dev_start.py 本體在 bootstrap 呼叫後、還沒執行到任何後續
            # 程式碼前就被中止」：直接呼叫 _mark_root_bootstrap_incomplete()
            # （對應 _run_bootstrap() 呼叫 _stream() 之前的無條件寫入點），
            # 之後不再執行任何 _run_bootstrap() 內剩餘程式碼——代表 dev_start.py
            # 在此處已死亡（.venv 尚未建立、rc 補寫哨兵永遠執行不到）。
            with mock.patch.object(dev_start, "ROOT", root):
                dev_start._mark_root_bootstrap_incomplete()
                # 模擬 bootstrap.sh 死前來得及建好 venv 目錄與可執行直譯器，
                # 但本體已死，不會再執行到任何後續程式碼。
                venv_python = root / ".venv" / "bin" / "python"
                venv_python.parent.mkdir(parents=True)
                # R3 QA 發現：shebang 腳本在 Windows 上非合法 PE、_venv_healthy()
                # 會撞 WinError 193，改複製當前真正在跑的直譯器本體（含 pyvenv.cfg，
                # 見 _copy_functional_interpreter）。
                _copy_functional_interpreter(venv_python)
                venv_python.chmod(0o755)

            marker_path = root / dev_start._BOOTSTRAP_INCOMPLETE_MARKER
            self.assertTrue(marker_path.is_file(),
                             "ROOT 層級哨兵應在呼叫 _stream() 之前就已落地，"
                             "即使後續程式碼完全沒有機會執行")

            # 使用者原地重跑：state={}（本體死亡時 step_finalize 從未執行到）、
            # .venv/bin/python 已存在 → 驗證 step_venv() 不會誤判「沿用既有
            # .venv」（過去只看 .venv 內部哨兵，該哨兵在此情境下從未被寫入）。
            bootstrap_calls = []

            def fake_run_bootstrap(_now, reason, **_kwargs):
                bootstrap_calls.append(reason)
                dev_start._clear_bootstrap_incomplete(root / ".venv")
                dev_start._clear_root_bootstrap_incomplete()
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
            self.assertEqual(len(bootstrap_calls), 1,
                              "ROOT 層級哨兵殘留時，應觸發重新 bootstrap，"
                              "而非誤判『沿用既有 .venv』回報虛假成功")
            self.assertIn("哨兵", bootstrap_calls[0])
            self.assertNotIn("沿用既有", dev_start.SUMMARY.get("venv", ""))

    def test_healthy_and_no_root_marker_still_reuses_without_bootstrap(self):
        """對照組：健檢通過且 ROOT 層級哨兵不存在時，仍應維持原行為（沿用既有
        .venv，不因本輪新增的檢查而誤觸發不必要的重裝）。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            venv_python = root / ".venv" / "bin" / "python"
            venv_python.parent.mkdir(parents=True)
            # R3 QA 發現：shebang 腳本在 Windows 上非合法 PE、_venv_healthy() 會撞
            # WinError 193，改複製當前真正在跑的直譯器本體（含 pyvenv.cfg，見
            # _copy_functional_interpreter），三平台皆可真實執行。
            _copy_functional_interpreter(venv_python)
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
            self.assertEqual(bootstrap_calls, [], "無 ROOT 層級哨兵殘留時不應觸發 bootstrap")
            self.assertIn("沿用既有", dev_start.SUMMARY.get("venv", ""))


class TestRunBootstrapWiresRootMarkerBeforeStream(DevStartTestCase):
    """MUST FIX B（QA 複審發現的測試覆蓋缺口）：既有
    `TestRootLevelBootstrapIncompleteMarker` 都是直接呼叫
    `_mark_root_bootstrap_incomplete()` 手動模擬「哨兵已經落地」的終態，從未
    驗證 `_run_bootstrap()` 本身真的有在呼叫 `_stream()` 之前無條件呼叫這個
    函式——QA 把 `_run_bootstrap()` 裡那行呼叫拿掉後，全套既有測試零失敗，
    證實這是真實的覆蓋盲區（只驗證了消費端/讀取端行為，沒驗證生產端接線）。

    本測試 mock 掉 `_stream()`，讓它在被呼叫的當下記錄「此刻 ROOT 層級哨兵
    是否已落地」，直接呼叫真正的 `_run_bootstrap()`（不是 fake），證明生產端
    接線順序正確：哨兵先落地、才開始跑 bootstrap（而不是事後才補寫）。
    """

    def test_root_marker_present_at_the_moment_stream_is_invoked(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            marker_present_at_call_time = []

            def fake_stream(_cmd, on_start=None, **_kwargs):
                marker_present_at_call_time.append(
                    dev_start._root_bootstrap_incomplete_marker_present())
                return 0

            with mock.patch.object(dev_start, "ROOT", root), \
                 mock.patch.object(dev_start, "_stream", side_effect=fake_stream):
                ok = dev_start._run_bootstrap("mac", "測試原因")

            self.assertTrue(ok)
            self.assertEqual(len(marker_present_at_call_time), 1,
                              "_stream() 應被 _run_bootstrap() 呼叫恰好一次")
            self.assertTrue(
                marker_present_at_call_time[0],
                "_run_bootstrap() 必須在呼叫 _stream() 之前就無條件寫入 ROOT 層級"
                "哨兵——這是唯一能涵蓋『dev_start.py 本體被 Ctrl-C 打死、_stream()"
                "永遠不會返回』情境的落地點，不能只驗證讀取端（哨兵存在時的後續"
                "行為）而不驗證寫入時機本身")

    def test_root_marker_absent_before_run_bootstrap_called_at_all(self):
        """對照組：_run_bootstrap() 被呼叫之前，哨兵不應無中生有地存在——確保
        上一個測試的「哨兵存在」斷言真的是 _run_bootstrap() 造成的，而非測試
        環境殘留或其他副作用。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with mock.patch.object(dev_start, "ROOT", root):
                self.assertFalse(dev_start._root_bootstrap_incomplete_marker_present())


class TestRunBootstrapPassesNewProcessGroupToStream(DevStartTestCase):
    """MUST FIX 1（QA 第四輪複審發現的測試覆蓋缺口）：既有涉及 process group
    語意的測試（`TestBootstrapProcessGroupSurvivesDirectChildKill`、
    `TestNormalBootstrapFlowUnaffectedByProcessGroupChange` 等）都是 mock 掉
    `_stream()` 並在假實作裡『自己』手動設定 `start_new_session=True`，從未
    驗證 production `_run_bootstrap()` 本身是否真的把 `new_process_group=True`
    傳給 `_stream()`——QA 把 `_run_bootstrap()` 裡那個實參改成 `False` 後，
    92 個既有測試零失敗，證實這是真實的覆蓋盲區（只驗證了消費端/假實作行為，
    沒驗證生產端接線本身）。

    本測試直接 mock `_stream()`（單純記錄呼叫參數、不用假實作模擬效果），
    呼叫真正的 `_run_bootstrap()`，斷言傳給 `_stream()` 的呼叫確實包含
    `new_process_group=True`。
    """

    def test_run_bootstrap_passes_new_process_group_true(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with mock.patch.object(dev_start, "ROOT", root), \
                 mock.patch.object(dev_start, "_stream", return_value=0) as mock_stream:
                ok = dev_start._run_bootstrap("mac", "測試原因")

            self.assertTrue(ok)
            mock_stream.assert_called_once()
            _, call_kwargs = mock_stream.call_args
            self.assertIn(
                "new_process_group", call_kwargs,
                "_run_bootstrap() 呼叫 _stream() 時必須明確傳遞 new_process_group")
            self.assertTrue(
                call_kwargs["new_process_group"],
                "_run_bootstrap() 必須把 new_process_group=True 傳給 _stream()，"
                "否則 bootstrap 子行程不會獨立成新 process group，Ctrl-C 訊號轉發"
                "（_forward_signal_to_bootstrap_group）與 step_venv() 的 killpg "
                "存活判斷都會完全失效卻無法被任何既有測試發現")


class TestNowLabelPlatformMapping(DevStartTestCase):
    """MUST FIX #4c：QA 用 bug-injection 重現——把 win32→"windows"／darwin→"mac"
    兩支互換後現有 54 個測試全過。_now_label() 是「跨平台自動偵測」整支工具
    最根本的函式（決定走 mac/windows/linux 哪個分支），過去完全沒有直接測試。
    """

    def test_win32_maps_to_windows(self):
        with mock.patch.object(sys, "platform", "win32"):
            self.assertEqual(dev_start._now_label(), "windows")

    def test_darwin_maps_to_mac(self):
        with mock.patch.object(sys, "platform", "darwin"):
            self.assertEqual(dev_start._now_label(), "mac")

    def test_other_platform_maps_to_linux(self):
        with mock.patch.object(sys, "platform", "linux"):
            self.assertEqual(dev_start._now_label(), "linux")


class TestStepSwitchCacheCleanup(DevStartTestCase):
    """MUST FIX #4a：QA 用 bug-injection 重現——把 `if not env_changed:` 反轉成
    `if env_changed:` 後現有 54 個測試全過。用真實 tmp 目錄建立假的
    .pytest_cache/.ruff_cache（含 symlink 與一般目錄兩種情況），驗證
    env_changed=True 時確實被清除、env_changed=False 時確實不動——絕不觸碰
    這個 repo 真正的快取目錄，全程沙盒化。
    """

    def test_env_changed_removes_cache_dir_and_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            real_target = base / "real-target"
            real_target.mkdir()
            (real_target / "keep.txt").write_text("keep", encoding="utf-8")

            pytest_cache = base / ".pytest_cache"
            pytest_cache.mkdir()
            (pytest_cache / "marker.txt").write_text("x", encoding="utf-8")

            ruff_cache_link = base / ".ruff_cache"
            create_symlink_or_skip(self, ruff_cache_link, real_target, target_is_directory=True)

            with mock.patch.object(dev_start, "ROOT", base), \
                 mock.patch.object(dev_start, "_CACHE_BASES", (base,)):
                dev_start.step_switch(env_changed=True)

            self.assertFalse(pytest_cache.exists(), "跨平台切換時應清除 .pytest_cache 目錄")
            self.assertFalse(
                ruff_cache_link.exists() or ruff_cache_link.is_symlink(),
                "跨平台切換時應清除 .ruff_cache symlink 本身")
            self.assertTrue(real_target.is_dir(), "symlink 清除不應波及其指向的真實目錄內容")
            self.assertTrue((real_target / "keep.txt").is_file())

    def test_env_unchanged_does_not_touch_cache_dirs(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            pytest_cache = base / ".pytest_cache"
            pytest_cache.mkdir()
            marker = pytest_cache / "marker.txt"
            marker.write_text("keep-me", encoding="utf-8")

            with mock.patch.object(dev_start, "ROOT", base), \
                 mock.patch.object(dev_start, "_CACHE_BASES", (base,)):
                dev_start.step_switch(env_changed=False)

            self.assertTrue(pytest_cache.is_dir(), "無跨平台切換時不應清除快取")
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep-me")


class TestStepPlatformLongpaths(DevStartTestCase):
    """MUST FIX #4b：QA 用 bug-injection 重現——把 `if lp != "true":` 反轉成
    `if lp == "true":` 後現有 54 個測試全過。用真實 git tmp repo 驗證：
    core.longpaths 尚未設為 true 時會被設定、已經是 true 時不會重複觸發設定。
    """

    @staticmethod
    def _make_repo(base: Path) -> Path:
        repo = base / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "--quiet"], cwd=str(repo), check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"],
                        cwd=str(repo), check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=str(repo), check=True)
        return repo

    def test_sets_longpaths_when_not_true(self):
        with tempfile.TemporaryDirectory() as td:
            repo = self._make_repo(Path(td))
            # R15 起 step_platform 尾端接 CI 活性哨兵——本測試意圖只鎖 longpaths，
            # mock 掉避免測試中打真實 gh 網路呼叫（SUMMARY["sync"] 未設時三閘不攔）。
            with mock.patch.object(dev_start, "ROOT", repo), \
                 mock.patch.object(dev_start, "_check_ci_liveness",
                                   return_value=None):
                dev_start.step_platform("windows", is_repo=True)
            r = subprocess.run(
                ["git", "-C", str(repo), "config", "--get", "core.longpaths"],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(r.stdout.strip().lower(), "true")
            self.assertIn("已設", dev_start.SUMMARY.get("platform", ""))

    def test_does_not_reset_when_already_true(self):
        with tempfile.TemporaryDirectory() as td:
            repo = self._make_repo(Path(td))
            subprocess.run(["git", "-C", str(repo), "config", "core.longpaths", "true"],
                            check=True)
            # 同上：mock 掉 CI 活性哨兵避免真實 gh 網路呼叫
            with mock.patch.object(dev_start, "ROOT", repo), \
                 mock.patch.object(dev_start, "_check_ci_liveness",
                                   return_value=None):
                dev_start.step_platform("windows", is_repo=True)
            # R12 起 summary 尾端附 nightly 心跳註記——本測試意圖只鎖「已是 true
            # 時不重複觸發設定」，改斷言前綴（若誤觸發會以「已設」開頭）
            self.assertTrue(
                dev_start.SUMMARY.get("platform", "").startswith("無需調整"),
                "已是 true 時不應重複觸發設定",
            )


class TestMainIntegrationGate(DevStartTestCase):
    """MUST FIX #4d：QA 用 bug-injection 重現——把 main() 的 `if ok:` 改成
    `if True:` 後現有 54 個測試全過，代表 bootstrap 失敗時 step_finalize()/
    step_hooks()/step_platform() 仍會被執行這件事完全沒有整合層級測試防護。
    """

    def test_step_venv_failure_skips_finalize_and_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state_file = root / ".dev_env_state.json"
            hooks_calls = []
            platform_calls = []
            finalize_calls = []

            with mock.patch.object(dev_start, "ROOT", root), \
                 mock.patch.object(dev_start, "STATE_FILE", state_file), \
                 mock.patch.object(dev_start, "_git",
                                    return_value=subprocess.CompletedProcess(
                                        args=[], returncode=1, stdout="", stderr="")), \
                 mock.patch.object(dev_start, "step_sync"), \
                 mock.patch.object(dev_start, "step_switch"), \
                 mock.patch.object(dev_start, "step_venv", return_value=False), \
                 mock.patch.object(dev_start, "step_hooks",
                                    side_effect=lambda *a: hooks_calls.append(a)), \
                 mock.patch.object(dev_start, "step_platform",
                                    side_effect=lambda *a: platform_calls.append(a)), \
                 mock.patch.object(dev_start, "step_finalize",
                                    side_effect=lambda *a: finalize_calls.append(a)):
                rc = dev_start.main([])

            self.assertNotEqual(rc, 0, "step_venv 失敗時 main() 應回傳非 0")
            self.assertEqual(finalize_calls, [], "step_venv 失敗時不應呼叫 step_finalize")
            self.assertEqual(hooks_calls, [], "step_venv 失敗時不應呼叫 step_hooks")
            self.assertEqual(platform_calls, [], "step_venv 失敗時不應呼叫 step_platform")
            self.assertFalse(state_file.exists(), "step_venv 失敗時狀態檔不應被寫入")

    def test_step_venv_success_runs_remaining_steps(self):
        """對照組：step_venv 成功時，後續三步驟仍應正常執行（避免只驗證失敗
        路徑，讓『恆為 False』這類反向 mutant 也被抓到）。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state_file = root / ".dev_env_state.json"
            hooks_calls = []
            platform_calls = []
            finalize_calls = []

            with mock.patch.object(dev_start, "ROOT", root), \
                 mock.patch.object(dev_start, "STATE_FILE", state_file), \
                 mock.patch.object(dev_start, "_git",
                                    return_value=subprocess.CompletedProcess(
                                        args=[], returncode=1, stdout="", stderr="")), \
                 mock.patch.object(dev_start, "step_sync"), \
                 mock.patch.object(dev_start, "step_switch"), \
                 mock.patch.object(dev_start, "step_venv", return_value=True), \
                 mock.patch.object(dev_start, "step_hooks",
                                    side_effect=lambda *a: hooks_calls.append(a)), \
                 mock.patch.object(dev_start, "step_platform",
                                    side_effect=lambda *a: platform_calls.append(a)), \
                 mock.patch.object(dev_start, "step_finalize",
                                    side_effect=lambda *a: finalize_calls.append(a)):
                rc = dev_start.main([])

            self.assertEqual(rc, 0, "step_venv 成功時 main() 應回傳 0")
            self.assertEqual(len(finalize_calls), 1)
            self.assertEqual(len(hooks_calls), 1)
            self.assertEqual(len(platform_calls), 1)


class TestMainInstallsSignalHandlerReference(DevStartTestCase):
    """MUST FIX 2（QA 第四輪複審發現的測試覆蓋缺口）：既有
    `TestSigintForwardsToBootstrapProcessGroup` 底下兩個測試都是自己手動呼叫
    `signal.signal(signal.SIGINT, dev_start._forward_signal_to_bootstrap_group)`
    模擬「已安裝好 handler」的狀態，從未透過 `main()` 走完整安裝路徑——QA 把
    `main()`（約 1462-1463 行）安裝 handler 那兩行改裝成 `signal.SIG_DFL`（保留
    正確的還原邏輯，不觸發任何裸崩潰）後，92 個既有測試零失敗，證實這是真實
    的覆蓋盲區：沒有任何測試驗證 production `main()` 本身真的有做這件事。

    本測試呼叫真正的 `main()`，mock 掉 `step_venv()` 讓它在被呼叫的當下（此刻
    handler 理應已安裝、且尚未被 `finally` 還原）記錄
    `signal.getsignal(SIGINT/SIGTERM)`，斷言兩者確實『引用等於』
    `dev_start._forward_signal_to_bootstrap_group`——不是只驗證「裝了某個非
    預設 handler」，而是驗證裝的正是這個函式本身。
    """

    @unittest.skipIf(os.name == "nt", "本 handler 僅在 POSIX 安裝（見 main() 內"
                      "對應條件判斷與其 docstring）")
    def test_main_installs_forward_signal_handler_during_step_venv(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state_file = root / ".dev_env_state.json"
            captured: dict = {}

            def fake_step_venv(now, state, force, cross_same_flavor=False):
                captured["sigint"] = signal.getsignal(signal.SIGINT)
                captured["sigterm"] = signal.getsignal(signal.SIGTERM)
                return False

            old_sigint = signal.getsignal(signal.SIGINT)
            old_sigterm = signal.getsignal(signal.SIGTERM)
            try:
                with mock.patch.object(dev_start, "ROOT", root), \
                     mock.patch.object(dev_start, "STATE_FILE", state_file), \
                     mock.patch.object(dev_start, "_git",
                                        return_value=subprocess.CompletedProcess(
                                            args=[], returncode=1, stdout="", stderr="")), \
                     mock.patch.object(dev_start, "step_sync"), \
                     mock.patch.object(dev_start, "step_switch"), \
                     mock.patch.object(dev_start, "step_venv", side_effect=fake_step_venv), \
                     mock.patch.object(dev_start, "step_hooks"), \
                     mock.patch.object(dev_start, "step_platform"), \
                     mock.patch.object(dev_start, "step_finalize"):
                    dev_start.main([])
            finally:
                # main() 自身的 try/finally 理應已還原；這裡是測試層級的保險絲，
                # 避免萬一斷言失敗中途拋出時，汙染後續其他測試的訊號狀態。
                signal.signal(signal.SIGINT, old_sigint)
                signal.signal(signal.SIGTERM, old_sigterm)

            self.assertIn("sigint", captured, "step_venv() 應已被 main() 呼叫（測試前提）")
            self.assertIs(
                captured["sigint"], dev_start._forward_signal_to_bootstrap_group,
                "main() 必須在呼叫 step_venv() 之前，把 SIGINT handler 安裝為"
                "『真正的』_forward_signal_to_bootstrap_group 函式引用，而不只是"
                "『裝了某個非預設 handler』")
            self.assertIs(
                captured["sigterm"], dev_start._forward_signal_to_bootstrap_group,
                "main() 必須在呼叫 step_venv() 之前，把 SIGTERM handler 安裝為"
                "『真正的』_forward_signal_to_bootstrap_group 函式引用")

            self.assertEqual(
                signal.getsignal(signal.SIGINT), old_sigint,
                "main() 結束後必須把 SIGINT handler 還原成呼叫前的狀態")
            self.assertEqual(
                signal.getsignal(signal.SIGTERM), old_sigterm,
                "main() 結束後必須把 SIGTERM handler 還原成呼叫前的狀態")


class TestEnsureVenvShapeBothMissingActuallyRemoves(DevStartTestCase):
    """SHOULD FIX #6a：_ensure_venv_shape() 「兩平台直譯器皆缺 → 移除重建」
    分支（壞損 .venv，如 symlink 斷裂）過去只驗證回傳值是 "missing"，沒有
    斷言磁碟上的壞損目錄真的被刪除。
    """

    def test_broken_venv_directory_is_actually_removed_from_disk(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            venv = root / ".venv"
            # 兩平台直譯器皆缺：既非 posix(bin/python) 也非 windows(Scripts/python.exe)
            (venv / "lib").mkdir(parents=True)
            (venv / "lib" / "leftover.txt").write_text("junk", encoding="utf-8")

            with mock.patch.object(dev_start, "ROOT", root):
                shape = dev_start._ensure_venv_shape("mac")

            self.assertEqual(shape, "missing")
            self.assertFalse(venv.exists(), "壞損 .venv 應已從磁碟實際移除，而非只回傳狀態字串")


class TestNightlyHeartbeat(DevStartTestCase):
    """R12 ARCH-R12-2：nightly 心跳哨兵三態（缺席／新鮮／過期）。

    WHY：launchd/schtasks 是否真的在跑過去零機械查核（DEF-101-164 ARCH-8），
    CI 停擺期間本地 nightly 是唯一每日兜底層。三態語意：缺席→提示不入
    WARNINGS（排程未啟用可接受但須可見）；過期（>8 天）→ _warn advisory；
    新鮮→OK。路徑一律以 tempfile + pathlib 構造（平台中立，守
    test_platform_neutral_paths）。"""

    def _run(self, root: Path, now: str = "mac") -> str:
        # R15 起缺席分支會呼叫 _launchd_nightly_loaded()（DEF-101-203②）——本類
        # 測試鎖的是「三態 mtime 比對」既有語意，固定 None（查不到）維持原文案，
        # 也避免在真 mac 上打到真實 launchctl 造成結果隨本機排程狀態漂移。
        with mock.patch.object(dev_start, "ROOT", root), \
             mock.patch.object(dev_start, "_launchd_nightly_loaded",
                               return_value=None), \
             mock.patch("builtins.print"):
            return dev_start._check_nightly_heartbeat(now)

    def test_absent_heartbeat_is_hint_not_warning(self):
        """缺席：記入 summary 片段但不入 WARNINGS（不可誤傷未啟用排程者）。

        R14 OPT-3：缺席文案必須含「尚未首跑」消歧——launchd/schtasks 剛安裝、首輪
        02:00 未到前心跳檔必然缺席，只說「未啟用」會誤導剛裝完的人（本機 R14 實證
        處於此誤導窗；語意對齊 install_mac_nightly.sh --status 文案）。"""
        with tempfile.TemporaryDirectory() as td:
            note = self._run(Path(td))
        self.assertIn("未偵測", note)
        self.assertIn("尚未首跑", note,
                      "缺席文案缺「尚未首跑」消歧——剛安裝未首跑者會被誤導為未啟用")
        self.assertIn("ONBOARDING", note)
        self.assertEqual(dev_start.WARNINGS, [],
                         "心跳缺席是提示不是警告——不得進 WARNINGS")

    def test_absent_heartbeat_print_gives_flavor_specific_verify_cmd(self):
        """R14 一審 QA-R14-REV-5＋SD-R14-REV-4：print 側消歧句須含依 flavor 的查證
        指令（mac→install_mac_nightly.sh --status；windows→schtasks），print 是
        獨立站點，僅斷言 return 值鎖不住它。"""
        for flavor, expect in (
            ("mac", "install_mac_nightly.sh --status"),
            ("windows", "schtasks /query /tn AutoClaude_Nightly"),
        ):
            with tempfile.TemporaryDirectory() as td, \
                 mock.patch.object(dev_start, "ROOT", Path(td)), \
                 mock.patch.object(dev_start, "_launchd_nightly_loaded",
                                   return_value=None), \
                 mock.patch("builtins.print") as fake_print:
                dev_start._check_nightly_heartbeat(flavor)
            printed = " ".join(str(c) for c in fake_print.call_args_list)
            self.assertIn("尚未跑過第一輪", printed,
                          f"{flavor}：print 消歧句消失（QA-R14-REV-5）")
            self.assertIn(expect, printed,
                          f"{flavor}：缺 flavor 對等查證指令（SD-R14-REV-4）")

    def test_fresh_heartbeat_is_ok(self):
        """新鮮（剛寫入）：OK、零警告。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            logs = root / "AutoClaude" / "logs"
            logs.mkdir(parents=True)
            (logs / "nightly_mac_latest.log").write_text("heartbeat\n", encoding="utf-8")
            note = self._run(root)
        self.assertIn("新鮮", note)
        self.assertEqual(dev_start.WARNINGS, [])

    def test_stale_heartbeat_warns_but_stays_advisory(self):
        """過期（mtime 9 天前 > 門檻 8 天）：_warn 進 WARNINGS，但不拋例外、
        不改流程（advisory——step_platform 不因此失敗）。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            logs = root / "AutoClaude" / "logs"
            logs.mkdir(parents=True)
            hb = logs / "nightly_mac_latest.log"
            hb.write_text("heartbeat\n", encoding="utf-8")
            nine_days_ago = time.time() - 9 * 86400
            os.utime(hb, (nine_days_ago, nine_days_ago))
            note = self._run(root)
        self.assertIn("過期", note)
        self.assertTrue(any("nightly 心跳過期" in w for w in dev_start.WARNINGS),
                        f"過期須 _warn，實際 WARNINGS={dev_start.WARNINGS}")

    def test_windows_flavor_reads_ps1_heartbeat_filename(self):
        """flavor 選檔：windows → nightly_latest.log（.ps1 既有心跳），
        posix → nightly_mac_latest.log（run_local_nightly.sh R12 起寫入）。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            logs = root / "AutoClaude" / "logs"
            logs.mkdir(parents=True)
            (logs / "nightly_latest.log").write_text("heartbeat\n", encoding="utf-8")
            note_win = self._run(root, now="windows")
            note_mac = self._run(root, now="mac")
        self.assertIn("新鮮", note_win)
        self.assertIn("未偵測", note_mac, "posix 不得誤讀 windows 心跳檔")

    def test_stat_oserror_never_fails_dev_start(self):
        """任何 OSError（外接碟抖動等）都不得讓 dev_start 失敗——降級為缺席提示。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with mock.patch.object(dev_start, "ROOT", root), \
                 mock.patch.object(dev_start.Path, "stat",
                                   side_effect=OSError("I/O error")), \
                 mock.patch.object(dev_start, "_launchd_nightly_loaded",
                                   return_value=None), \
                 mock.patch("builtins.print"):
                note = dev_start._check_nightly_heartbeat("mac")
        self.assertIn("未偵測", note)
        self.assertEqual(dev_start.WARNINGS, [])

    def test_step_platform_summary_includes_heartbeat_note(self):
        """step_platform 整合：summary『平台健檢』欄必含心跳片段，且七步驟
        標頭（[6/7] 平台專屬健檢）不變。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # _launchd_nightly_loaded 固定 None：鎖既有缺席文案不隨本機 launchd
            # 狀態漂移；_check_ci_liveness 走 is_repo=False 閘自然回 None。
            with mock.patch.object(dev_start, "ROOT", root), \
                 mock.patch.object(dev_start, "_launchd_nightly_loaded",
                                   return_value=None), \
                 mock.patch("builtins.print") as fake_print:
                dev_start.step_platform("mac", is_repo=False)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("平台專屬健檢", printed)
        self.assertIn("nightly 心跳", dev_start.SUMMARY["platform"])
        self.assertIn("無需調整", dev_start.SUMMARY["platform"],
                      "既有『無需調整』語意必須保留（心跳為附加片段）")


class TestGitTimeoutExpired(DevStartTestCase):
    """SHOULD FIX #6b：_git() 的 TimeoutExpired 例外處理分支零測試覆蓋。
    驗證逾時時回傳 rc=124（不是被誤判成功的 rc=0），避免上游呼叫端誤判
    git 指令成功。
    """

    def test_timeout_expired_returns_rc_124(self):
        with mock.patch.object(
                dev_start.subprocess, "run",
                side_effect=subprocess.TimeoutExpired(cmd="git", timeout=60)):
            result = dev_start._git("fetch", "origin")
        self.assertEqual(result.returncode, 124)
        self.assertNotEqual(result.returncode, 0, "逾時不可被誤判為成功")


class TestNightlyHeartbeatFilenameContract(unittest.TestCase):
    """心跳檔名契約寫讀兩端機械繫結（R12 QA 一審 QA-5／SD 一審 SD-4）。

    WHY：`nightly_mac_latest.log` 硬編於 writer（run_local_nightly.sh）與 reader
    （dev_start.py）兩處字面值——單側改名後 dev_start 永遠報「未偵測」且該態刻意
    不入 WARNINGS，靜默退化零訊號。本測試以靜態錨點鎖住：兩端檔名一致＋writer
    呼叫位置在最終彙總之後、exit 判定之前（成功/失敗皆寫的語意錨點）。Windows 側
    （nightly_latest.log ↔ run_local_nightly.ps1）同構加鎖。"""

    _REPO = Path(dev_start.__file__).resolve().parents[1]

    def test_mac_writer_reader_filename_and_call_position(self) -> None:
        sh = (self._REPO / "AutoClaude" / "tools" / "run_local_nightly.sh").read_text(
            encoding="utf-8")
        src = Path(dev_start.__file__).read_text(encoding="utf-8")
        self.assertIn("nightly_mac_latest.log", sh, "writer 檔名錨點消失")
        self.assertIn("nightly_mac_latest.log", src, "reader 檔名錨點消失")
        pos_summary = sh.rfind("nightly 彙總：PASS=")  # 最終彙總（def 內另有一處故 rfind）
        pos_call = sh.find("\nwrite_heartbeat\n")      # 裸呼叫行（def 行為 `write_heartbeat() {`）
        pos_exit = sh.find('if [ "$FAIL" -gt 0 ]')
        self.assertGreater(pos_summary, 0, "最終彙總 printf 錨點消失")
        self.assertGreater(pos_call, pos_summary, "write_heartbeat 呼叫須在最終彙總之後")
        self.assertGreater(pos_exit, pos_call, "write_heartbeat 呼叫須在 exit 判定之前（失敗路徑也要寫）")

    def test_windows_reader_filename_matches_ps1_writer(self) -> None:
        ps1 = (self._REPO / "AutoClaude" / "tools" / "run_local_nightly.ps1").read_text(
            encoding="utf-8-sig")
        src = Path(dev_start.__file__).read_text(encoding="utf-8")
        self.assertIn("nightly_latest.log", ps1, "Windows writer 檔名錨點消失")
        self.assertIn('"nightly_latest.log"', src, "Windows reader 檔名錨點消失")

    def test_installer_third_site_filename_and_threshold(self) -> None:
        """R13 第三站點（install_mac_nightly.sh --status）納入契約鎖（ARCH-R13-REV-2）。

        WHY：安裝器 --status 自帶心跳三態、硬編檔名與 8 天門檻各一份——僅靠註解
        宣稱「與 dev_start 同值同語意」。任一端漂移＝--status 說謊零機械訊號，
        正是 R13 ARCH-R13-1 在消滅的「多站點註解同步」同構病灶。"""
        installer = (self._REPO / "tools" / "install_mac_nightly.sh").read_text(
            encoding="utf-8")
        self.assertIn("nightly_mac_latest.log", installer, "安裝器心跳檔名錨點消失")
        self.assertIn(
            f"HEARTBEAT_MAX_AGE_DAYS={dev_start._HEARTBEAT_MAX_AGE_DAYS}",
            installer,
            "安裝器過期門檻須與 dev_start._HEARTBEAT_MAX_AGE_DAYS 同值（8 天）",
        )
        # SD-R13-1 迴歸鎖：過期判定必須以秒比較（整數天除法在 (8,9) 天窗口誤判新鮮）
        self.assertIn("* 86400", installer, "安裝器過期判定須以秒比較（防整數天截斷回歸）")


class TestVenvPythonVersionSentinel(DevStartTestCase):
    """R15 DEF-101-207：venv Python 版本比對哨兵。

    WHY：.python-version 升版後 bootstrap 對「既有 .venv 沿用」路徑不換直譯器，
    pin 檔不在 DEPS_FILES 內、hash 觸發是無效藥——唯一可見點是整備成功收尾塊
    對 venv 直譯器實測版本。驅動真實 step_venv()（hash 未變的沿用路徑），
    monkeypatch 兩支新純函式鎖三態：不一致→警告；一致→零警告；pin 缺席→
    零警告且不得 spawn 直譯器（短路）。
    """

    def _run_step_venv(self, target, minor_mock) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fake_py = root / ".venv" / "bin" / "python"
            fake_py.parent.mkdir(parents=True)
            fake_py.write_text("", encoding="utf-8")  # 只需存在（過 _safe_exists 守門）
            state = {"deps_hash": {"posix": "h"}}  # prev == cur → 走「hash 未變」沿用路徑
            with mock.patch.object(dev_start, "ROOT", root), \
                 mock.patch.object(dev_start, "LOCK_FILE", root / ".dev_start.lock"), \
                 mock.patch.object(dev_start, "_ensure_venv_shape", return_value="ok"), \
                 mock.patch.object(dev_start, "_deps_hash", return_value="h"), \
                 mock.patch.object(dev_start, "_venv_python", return_value=fake_py), \
                 mock.patch.object(dev_start, "_write_origin_marker"), \
                 mock.patch.object(dev_start, "_python_version_target",
                                   return_value=target), \
                 mock.patch.object(dev_start, "_venv_python_minor", minor_mock), \
                 mock.patch("builtins.print"):
                ok = dev_start.step_venv("mac", state, force=False)
            self.assertTrue(ok, "版本哨兵是 advisory——不得改變 step_venv 成敗")

    def test_mismatch_warns(self):
        self._run_step_venv("3.12", mock.Mock(return_value="3.11"))
        self.assertTrue(
            any("venv Python 3.11" in w and ".python-version 目標 3.12" in w
                and "DEF-101-207" in w for w in dev_start.WARNINGS),
            f"目標/實際不一致須 _warn，實際 WARNINGS={dev_start.WARNINGS}")

    def test_match_no_warning(self):
        self._run_step_venv("3.11", mock.Mock(return_value="3.11"))
        self.assertEqual(dev_start.WARNINGS, [], "版本一致不得出現任何警告")

    def test_pin_absent_silent_and_short_circuits(self):
        # pin 缺席（target=None）→ 零警告，且不得呼叫 _venv_python_minor
        # （短路：不 spawn 直譯器子行程）
        minor = mock.Mock(side_effect=AssertionError("pin 缺席時不得實測直譯器版本"))
        self._run_step_venv(None, minor)
        self.assertEqual(dev_start.WARNINGS, [], "pin 缺席是合法狀態——靜默")
        minor.assert_not_called()


class TestVenvPythonVersionRealBody(DevStartTestCase):
    """QA-R15-REV-3：_python_version_target()／_venv_python_minor() 真身驅動。

    WHY：TestVenvPythonVersionSentinel 只驗證 step_venv 依兩支函式回傳值決定
    要不要 _warn，兩支函式本身（讀 .python-version 截斷邏輯、subprocess 呼叫
    子行程取版本）全程被 mock 掉、零真身覆蓋（R15 四方一審 QA-R15-REV-3 揭露）。
    本測試以 tempfile 真檔案＋sys.executable 真直譯器直接驅動函式本體。
    """

    def test_target_two_segment_version(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".python-version").write_text("3.11\n", encoding="utf-8")
            with mock.patch.object(dev_start, "ROOT", root):
                self.assertEqual(dev_start._python_version_target(), "3.11")

    def test_target_three_segment_truncated_to_major_minor(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".python-version").write_text("3.11.9", encoding="utf-8")
            with mock.patch.object(dev_start, "ROOT", root):
                self.assertEqual(dev_start._python_version_target(), "3.11")

    def test_target_strips_surrounding_whitespace(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".python-version").write_text("  3.12  \n", encoding="utf-8")
            with mock.patch.object(dev_start, "ROOT", root):
                self.assertEqual(dev_start._python_version_target(), "3.12")

    def test_target_missing_file_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)  # 不建立 .python-version
            with mock.patch.object(dev_start, "ROOT", root):
                self.assertIsNone(dev_start._python_version_target())

    def test_target_blank_content_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".python-version").write_text("   \n", encoding="utf-8")
            with mock.patch.object(dev_start, "ROOT", root):
                self.assertIsNone(dev_start._python_version_target())

    def test_minor_real_subprocess_call_against_current_interpreter(self):
        # 用當前測試執行的直譯器本身（sys.executable）真實 spawn 子行程，
        # 驗證輸出解析為 "major.minor" 字串（非 mock 掉 subprocess.run）。
        result = dev_start._venv_python_minor(Path(sys.executable))
        expected = f"{sys.version_info.major}.{sys.version_info.minor}"
        self.assertEqual(result, expected)

    def test_minor_nonexistent_interpreter_returns_none(self):
        result = dev_start._venv_python_minor(Path("/nonexistent/path/to/python"))
        self.assertIsNone(result)

    def test_minor_nonzero_exit_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            fake_py = Path(td) / "fail_py.sh"
            fake_py.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            fake_py.chmod(0o755)
            result = dev_start._venv_python_minor(fake_py)
            self.assertIsNone(result)


class TestLaunchdNightlyLoaded(DevStartTestCase):
    """R15 DEF-101-203②：launchctl 精確查核三態（含干擾列防前綴誤中）。

    以 fake launchctl 輸出驅動 _check_nightly_heartbeat 缺席分支端到端，
    鎖三態對應文案；非 darwin 直接回 None（不 spawn launchctl）。
    """

    _DECOY = "123\t0\tcom.autoclaude.nightly2"  # 前綴干擾列：精確等值不得誤中

    def _heartbeat_with_launchctl(self, stdout: str, rc: int = 0):
        """在空 ROOT（心跳必缺席）+ 假 darwin + 假 launchctl 下跑心跳哨兵。"""
        fake = subprocess.CompletedProcess(args=["launchctl", "list"],
                                           returncode=rc, stdout=stdout, stderr="")
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(dev_start, "ROOT", Path(td)), \
             mock.patch.object(sys, "platform", "darwin"), \
             mock.patch.object(dev_start.subprocess, "run", return_value=fake), \
             mock.patch("builtins.print") as fake_print:
            note = dev_start._check_nightly_heartbeat("mac")
        printed = " ".join(str(c) for c in fake_print.call_args_list)
        return note, printed

    def test_loaded_true_despite_decoy_gives_normal_wording(self):
        # 干擾列在前、真 label 在後（PID 欄為 `-`＝未在跑，launchctl 真實輸出形態）
        out = f"{self._DECOY}\n-\t0\tcom.autoclaude.nightly\n"
        note, printed = self._heartbeat_with_launchctl(out)
        self.assertIn("launchd 已載入、尚未跑過第一輪", printed,
                      "True 態須明示「已載入、尚未首跑＝正常」消歧")
        self.assertIn("install_mac_nightly.sh --status", printed,
                      "長解釋須指向 --status，不得再造第三份完整三態措辭")
        self.assertIn("launchd 已載入", note)
        self.assertEqual(dev_start.WARNINGS, [], "True 態是正常狀態——不得 _warn")

    def test_decoy_only_is_false_gives_install_wording(self):
        note, printed = self._heartbeat_with_launchctl(f"{self._DECOY}\n")
        self.assertIn("launchd 未載入", printed,
                      "只有前綴干擾列時必須判 False——精確等值不得誤中 nightly2")
        self.assertIn("bash tools/install_mac_nightly.sh", printed)
        self.assertIn("launchd 未載入", note)
        self.assertEqual(dev_start.WARNINGS, [], "False 態是提示不是警告")

    def test_launchctl_failure_is_none_keeps_dual_wording(self):
        note, printed = self._heartbeat_with_launchctl("", rc=1)
        self.assertIn("排程可能未啟用", printed,
                      "None 態必須維持現行雙可能文案不變")
        self.assertIn("尚未跑過第一輪", printed)
        self.assertIn("排程未啟用？或尚未首跑？", note)

    def test_non_darwin_returns_none_without_spawning(self):
        with mock.patch.object(sys, "platform", "linux"), \
             mock.patch.object(dev_start.subprocess, "run") as fake_run:
            self.assertIsNone(dev_start._launchd_nightly_loaded())
        fake_run.assert_not_called()


class TestHeartbeatFailSentinel(DevStartTestCase):
    """R15 ARCH-R15-1：心跳 FAIL 內容哨兵（mac 側）。

    WHY：mtime 只證明「在跑」不證明「在綠」——CI 停擺期間 nightly 是唯一每日
    活體，連續全紅晨間 dev_start 仍 ✅ 是盲區。心跳前 3 行是
    run_local_nightly.sh write_heartbeat() 的固定契約。
    """

    @staticmethod
    def _write_heartbeat(root: Path, fail: int) -> None:
        logs = root / "AutoClaude" / "logs"
        logs.mkdir(parents=True)
        (logs / "nightly_mac_latest.log").write_text(
            "nightly_mac heartbeat（UTC）：2026-07-20T02:00:00Z\n"
            f"===== nightly 彙總：PASS=5 FAIL={fail} =====\n"
            "失敗 stage：mutation pg-e2e\n",
            encoding="utf-8")

    def _run(self, root: Path) -> str:
        with mock.patch.object(dev_start, "ROOT", root), \
             mock.patch("builtins.print"):
            return dev_start._check_nightly_heartbeat("mac")

    def test_fail_gt_zero_warns_with_count_and_defect_id(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_heartbeat(root, fail=2)
            note = self._run(root)
        self.assertTrue(
            any("FAIL=2" in w and "ARCH-R15-1" in w and "未全綠" in w
                for w in dev_start.WARNINGS),
            f"FAIL>0 須 _warn（含計數與缺陷編號），實際 WARNINGS={dev_start.WARNINGS}")
        self.assertIn("FAIL=2", note, "summary 片段須附註 FAIL 計數")

    def test_fail_zero_no_warning(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_heartbeat(root, fail=0)
            note = self._run(root)
        self.assertEqual(dev_start.WARNINGS, [], "FAIL=0（全綠）不得出現任何警告")
        self.assertEqual(note, "nightly 心跳新鮮")


class TestCiLiveness(DevStartTestCase):
    """R15 DEF-101-208：CI 活性哨兵——gh read-only API 查最新 run 結論。

    三道靜默跳過閘（無 gh／sync 離線或跳過／非 repo）＋四態輸出。全部
    advisory：None＝不入 summary；「未知」不入 WARNINGS；僅非 success _warn。
    """

    @staticmethod
    def _gh_result(payload: str, rc: int = 0) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(args=["gh"], returncode=rc,
                                           stdout=payload, stderr="")

    def test_no_gh_returns_none_silently(self):
        with mock.patch.object(dev_start.shutil, "which", return_value=None), \
             mock.patch("builtins.print") as fake_print:
            self.assertIsNone(dev_start._check_ci_liveness(is_repo=True))
        self.assertEqual(dev_start.WARNINGS, [])
        fake_print.assert_not_called()

    def test_offline_sync_returns_none_without_network_probe(self):
        # 重用 step_sync 判定：離線時不做第二次網路探測。不能用 side_effect 拋錯
        # 驗證（兜底 except 會吞掉假失敗），改記錄呼叫並雙重斷言。
        dev_start.SUMMARY["sync"] = "離線（fetch 失敗）"
        with mock.patch.object(dev_start.shutil, "which", return_value="/usr/bin/gh"), \
             mock.patch.object(dev_start.subprocess, "run") as fake_run, \
             mock.patch("builtins.print"):
            self.assertIsNone(dev_start._check_ci_liveness(is_repo=True))
        fake_run.assert_not_called()

    def test_failure_conclusion_warns_with_local_fallback_hint(self):
        dev_start.SUMMARY["sync"] = "已是最新（origin/main）"
        payload = json.dumps([{"status": "completed", "conclusion": "failure",
                               "updatedAt": "2026-07-19T18:00:00Z",
                               "workflowName": "autoclaude-ci"}])
        with mock.patch.object(dev_start.shutil, "which", return_value="/usr/bin/gh"), \
             mock.patch.object(dev_start.subprocess, "run",
                               return_value=self._gh_result(payload)), \
             mock.patch("builtins.print"):
            note = dev_start._check_ci_liveness(is_repo=True)
        self.assertIn("CI 活性異常", note)
        self.assertTrue(
            any("autoclaude-ci=failure" in w and "DEF-101-081/208" in w
                and "pre-push＋nightly" in w for w in dev_start.WARNINGS),
            f"非 success 須 _warn（含 workflow/結論/本地兜底提示），"
            f"實際 WARNINGS={dev_start.WARNINGS}")

    def test_success_returns_normal_fragment_without_warning(self):
        dev_start.SUMMARY["sync"] = "已是最新（origin/main）"
        payload = json.dumps([{"status": "completed", "conclusion": "success",
                               "updatedAt": "2026-07-20T01:00:00Z",
                               "workflowName": "autoclaude-ci"}])
        with mock.patch.object(dev_start.shutil, "which", return_value="/usr/bin/gh"), \
             mock.patch.object(dev_start.subprocess, "run",
                               return_value=self._gh_result(payload)), \
             mock.patch("builtins.print"):
            note = dev_start._check_ci_liveness(is_repo=True)
        self.assertEqual(note, "CI 活性正常")
        self.assertEqual(dev_start.WARNINGS, [])

    def test_in_progress_status_is_normal_not_warning(self):
        """SD-R15-REV-1：run 尚未跑完時 conclusion 恆為 null——不得誤判為帳務停擺/失敗。"""
        dev_start.SUMMARY["sync"] = "已是最新（origin/main）"
        payload = json.dumps([{"status": "in_progress", "conclusion": None,
                               "updatedAt": "2026-07-20T01:00:00Z",
                               "workflowName": "autoclaude-ci"}])
        with mock.patch.object(dev_start.shutil, "which", return_value="/usr/bin/gh"), \
             mock.patch.object(dev_start.subprocess, "run",
                               return_value=self._gh_result(payload)), \
             mock.patch("builtins.print"):
            note = dev_start._check_ci_liveness(is_repo=True)
        self.assertEqual(note, "CI 活性正常（執行中）")
        self.assertEqual(dev_start.WARNINGS, [],
                          "run 尚未跑完不得誤判為異常並 _warn")

    def test_queued_status_is_normal_not_warning(self):
        dev_start.SUMMARY["sync"] = "已是最新（origin/main）"
        payload = json.dumps([{"status": "queued", "conclusion": None,
                               "updatedAt": "2026-07-20T01:00:00Z",
                               "workflowName": "autoclaude-ci"}])
        with mock.patch.object(dev_start.shutil, "which", return_value="/usr/bin/gh"), \
             mock.patch.object(dev_start.subprocess, "run",
                               return_value=self._gh_result(payload)), \
             mock.patch("builtins.print"):
            note = dev_start._check_ci_liveness(is_repo=True)
        self.assertEqual(note, "CI 活性正常（執行中）")
        self.assertEqual(dev_start.WARNINGS, [])


class TestCrossSiteLiteralLocks(unittest.TestCase):
    """R15 雙站點字面互鎖（機械鎖漂移；同 TestNightlyHeartbeatFilenameContract 病灶）。

    dev_start.py 與 install_mac_nightly.sh 各硬編一份 launchd label 與心跳門檻，
    單側改動另一側零訊號——regex 自兩側原始碼抽字面值斷言相等。
    install_mac_nightly.sh 本測試只讀不寫。
    """

    _REPO = Path(dev_start.__file__).resolve().parents[1]

    def _installer_text(self) -> str:
        return (self._REPO / "tools" / "install_mac_nightly.sh").read_text(
            encoding="utf-8")

    def test_launchd_label_matches_installer(self) -> None:
        """ARCH-R15-3：label 兩站點相等（launchctl 查核比對的就是這個字串）。"""
        src = Path(dev_start.__file__).read_text(encoding="utf-8")
        m_dev = re.search(r'_NIGHTLY_LAUNCHD_LABEL = "([^"]+)"', src)
        m_ins = re.search(r'^LABEL="([^"]+)"', self._installer_text(), re.MULTILINE)
        self.assertIsNotNone(m_dev, "dev_start.py 的 launchd label 錨點消失")
        self.assertIsNotNone(m_ins, "install_mac_nightly.sh 的 LABEL= 錨點消失")
        self.assertEqual(m_dev.group(1), "com.autoclaude.nightly")
        self.assertEqual(m_dev.group(1), m_ins.group(1),
                         "兩站點 label 漂移——launchctl 查核將永遠 False")

    def test_heartbeat_threshold_matches_installer(self) -> None:
        """ARCH-R15-2：心跳過期門檻兩站點相等（--status 與 dev_start 同語意）。"""
        src = Path(dev_start.__file__).read_text(encoding="utf-8")
        m_dev = re.search(r"_HEARTBEAT_MAX_AGE_DAYS = (\d+)", src)
        m_ins = re.search(r"^HEARTBEAT_MAX_AGE_DAYS=(\d+)",
                          self._installer_text(), re.MULTILINE)
        self.assertIsNotNone(m_dev, "dev_start.py 的門檻常數錨點消失")
        self.assertIsNotNone(m_ins, "install_mac_nightly.sh 的門檻常數錨點消失")
        self.assertEqual(m_dev.group(1), m_ins.group(1),
                         "兩站點心跳門檻漂移——--status 與 dev_start 判定分歧")


if __name__ == "__main__":
    unittest.main()
