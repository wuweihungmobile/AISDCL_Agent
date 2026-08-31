#!/usr/bin/env python3
"""tools/dev_start.py 的輕量單元測試（純 stdlib unittest，root-infra-ci 零依賴安裝原則）。

四方複審（Architect/SA/SD/QA，2026-07-13）共同指出核心邏輯複雜度已超過純語法檢查
（py_compile）能守住的範圍。本檔覆蓋純邏輯函式與本輪修復的迴歸點，範圍刻意限於
「給定輸入即可斷言輸出」的情境：不涉及真實建置 venv / 真實網路 fetch。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import ast
import ctypes
import datetime
import inspect
import io
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
import tokenize
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dev_start  # noqa: E402

# R68：`tools/lib/` 由 dev_start 自己 insert 進 sys.path，故此處經它取得同一個模組
# 物件（不重新 import，避免測試 patch 到與生產路徑不同的副本）。
ci_liveness = dev_start.ci_liveness
from _platform_helpers import (  # noqa: E402
    PS_UTF8_PRELUDE,
    create_symlink_or_skip,
    ps_utf8_command,
    usable_bash_for_fixture,
)
from _platform_helpers import (  # noqa: E402
    copy_functional_interpreter as _copy_functional_interpreter,
)


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


class TestDepsHashEntryPointGap(DevStartTestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestDepsHashEntryPointGap WHY〉節。"""

    _BASE = '[project]\nname = "x"\ndependencies = ["pyyaml"]\n'

    def _hash_of(self, td: str, body: str) -> str:
        pyproject = Path(td) / "pyproject.toml"
        pyproject.write_text(body, encoding="utf-8")
        with mock.patch.object(dev_start, "DEPS_FILES", (pyproject,)):
            return dev_start._deps_hash()

    def test_adding_console_script_alters_hash(self):
        with tempfile.TemporaryDirectory() as td:
            before = self._hash_of(td, self._BASE)
            after = self._hash_of(
                td, self._BASE + '\n[project.scripts]\nfoo-check = "pkg.mod:main"\n')
            self.assertNotEqual(before, after)

    def test_adding_gui_script_alters_hash(self):
        with tempfile.TemporaryDirectory() as td:
            before = self._hash_of(td, self._BASE)
            after = self._hash_of(
                td, self._BASE + '\n[project.gui-scripts]\nfoo-gui = "pkg.mod:gui"\n')
            self.assertNotEqual(before, after)

    def test_adding_entry_point_group_alters_hash(self):
        with tempfile.TemporaryDirectory() as td:
            before = self._hash_of(td, self._BASE)
            after = self._hash_of(
                td, self._BASE + '\n[project.entry-points."my.plugins"]\np = "pkg.mod:P"\n')
            self.assertNotEqual(before, after)

    def test_metadata_only_change_still_does_not_alter_hash(self):
        """反向鎖：白名單擴大後仍不可把純中繼資料變動誤判為依賴變動（否則
        每次改 description/version 都無謂重裝，等於退回黑名單排除法）。"""
        with tempfile.TemporaryDirectory() as td:
            before = self._hash_of(td, self._BASE)
            after = self._hash_of(td, self._BASE + 'description = "改了文案"\n')
            self.assertEqual(before, after)


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
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestHooksConstantsConsistency WHY〉節。"""

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
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestStepHooksIsFileOSError WHY〉節。"""

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
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestAcquireBootstrapLockPartialAliveMiddleState WHY〉節。"""

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

            with mock.patch.object(dev_start, "ROOT", local), \
                    mock.patch.object(dev_start, "_nightly_running", return_value=False):
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

            with mock.patch.object(dev_start, "ROOT", local), \
                    mock.patch.object(dev_start, "_nightly_running", return_value=False):
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

            with mock.patch.object(dev_start, "ROOT", local), \
                    mock.patch.object(dev_start, "_nightly_running", return_value=False):
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

            with mock.patch.object(dev_start, "ROOT", local), \
                    mock.patch.object(dev_start, "_nightly_running", return_value=False):
                dev_start.step_sync(no_sync=False, is_repo=True)

            self.assertTrue(any("離線" in w for w in dev_start.WARNINGS))
            self.assertIn("離線", dev_start.SUMMARY.get("sync", ""))

    def test_nightly_running_blocks_pull(self):
        """2026-07-27 Windows 實機事故的回歸鎖：nightly 在跑時 pull 會把 113 個檔案
        抽換到它的 pytest 腳下（當天實測 5 支假紅），故不自動 pull。"""
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            origin, local = self._make_pair(base)
            (origin / "f.txt").write_text("v2-origin\n", encoding="utf-8")
            self._run_git(["commit", "--quiet", "-am", "advance"], origin)

            with mock.patch.object(dev_start, "ROOT", local), \
                    mock.patch.object(dev_start, "_nightly_running", return_value=True):
                dev_start.step_sync(no_sync=False, is_repo=True)

            self.assertEqual(
                (local / "f.txt").read_text(encoding="utf-8"), "v1\n",
                "nightly 執行中時不應 pull，工作樹內容應維持原狀")
            self.assertTrue(any("nightly 正在執行" in w for w in dev_start.WARNINGS))
            self.assertIn("nightly 執行中", dev_start.SUMMARY.get("sync", ""))

    def test_nightly_running_still_warns_when_already_up_to_date(self):
        """已是最新時沒有 pull 可擋，但「別跑全套測試」的提醒仍必須發出——這才是
        開工當下最常見的情境（心跳補跑與開工同時發生），漏掉等於防呆失效。"""
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            origin, local = self._make_pair(base)

            with mock.patch.object(dev_start, "ROOT", local), \
                    mock.patch.object(dev_start, "_nightly_running", return_value=True):
                dev_start.step_sync(no_sync=False, is_repo=True)

            self.assertTrue(any("nightly 正在執行" in w for w in dev_start.WARNINGS))
            self.assertIn("已是最新", dev_start.SUMMARY.get("sync", ""))

    def test_undetermined_nightly_state_does_not_block_pull(self):
        """None＝無法判定（如 Global 具名物件權限不足）不可冒充「在跑」而擋住同步：
        防呆機制自己失敗時，必須降級為不作為，不是把 dev_start 弄壞。"""
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            origin, local = self._make_pair(base)
            (origin / "f.txt").write_text("v2-origin\n", encoding="utf-8")
            self._run_git(["commit", "--quiet", "-am", "advance"], origin)

            with mock.patch.object(dev_start, "ROOT", local), \
                    mock.patch.object(dev_start, "_nightly_running", return_value=None):
                dev_start.step_sync(no_sync=False, is_repo=True)

            self.assertEqual((local / "f.txt").read_text(encoding="utf-8"), "v2-origin\n")
            self.assertIn("已更新", dev_start.SUMMARY.get("sync", ""))


class TestPyprojectTopLevelTableRoster(DevStartTestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestPyprojectTopLevelTableRoster WHY〉節。"""

    _KNOWN_TOP_LEVEL = {"build-system", "project", "tool"}

    def test_top_level_tables_match_known_roster(self):
        import tomllib

        pyproject = dev_start.ROOT / "AutoClaude" / "pyproject.toml"
        self.assertTrue(pyproject.is_file(), f"找不到 {pyproject}")
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        self.assertEqual(
            set(data), self._KNOWN_TOP_LEVEL,
            "AutoClaude/pyproject.toml 的頂層表集合變了。請判斷新增的表**是否屬於"
            "「安裝當下才生效」的內容**（如 dependency-groups／tool.uv 的 override/constraint／"
            "tool.setuptools.packages）——若是，必須同步加進 "
            "`tools/dev_start.py::_toml_deps_snapshot` 的白名單，否則 dev_start 會判「依賴新鮮」"
            "跳過重裝，形成 DEF-101-502 同款假綠；若只是中繼資料，把它加進本 roster 即可。",
        )


class TestNightlyRunningDetection(DevStartTestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestNightlyRunningDetection WHY〉節。"""

    def _force_posix(self):
        return mock.patch.object(dev_start.platform_utils, "is_windows", return_value=False)

    def test_no_lock_dir_means_not_running(self):
        with tempfile.TemporaryDirectory() as td, self._force_posix(), \
                mock.patch.object(dev_start, "ROOT", Path(td)):
            self.assertIs(dev_start._nightly_running(), False)

    def test_lock_dir_with_live_pid_means_running(self):
        with tempfile.TemporaryDirectory() as td, self._force_posix(), \
                mock.patch.object(dev_start, "ROOT", Path(td)), \
                mock.patch.object(dev_start, "_pid_alive", return_value=True):
            lock = Path(td) / dev_start._NIGHTLY_POSIX_LOCK
            lock.mkdir(parents=True)
            (lock / "pid").write_text("12345\n", encoding="utf-8")
            self.assertIs(dev_start._nightly_running(), True)

    def test_stale_lock_dir_with_dead_pid_means_not_running(self):
        """前次 nightly crash 留下的陳舊鎖不可讓提醒永久常亮（常亮＝背景噪音）。"""
        with tempfile.TemporaryDirectory() as td, self._force_posix(), \
                mock.patch.object(dev_start, "ROOT", Path(td)), \
                mock.patch.object(dev_start, "_pid_alive", return_value=False):
            lock = Path(td) / dev_start._NIGHTLY_POSIX_LOCK
            lock.mkdir(parents=True)
            (lock / "pid").write_text("12345\n", encoding="utf-8")
            self.assertIs(dev_start._nightly_running(), False)

    def test_lock_dir_without_pid_file_is_undetermined(self):
        """.sh 先 mkdir 再寫 pid，兩者之間有競態窗口；讀不到 pid 一律回 None，
        不可冒充 False（假「沒在跑」比不知道更危險）。"""
        with tempfile.TemporaryDirectory() as td, self._force_posix(), \
                mock.patch.object(dev_start, "ROOT", Path(td)):
            (Path(td) / dev_start._NIGHTLY_POSIX_LOCK).mkdir(parents=True)
            self.assertIsNone(dev_start._nightly_running())

    def test_lock_path_matches_the_shell_script_ssot(self):
        """字面量漂移鎖：本檔的鎖路徑／Mutex 名一旦與 nightly 腳本不一致，偵測會
        靜默失效（永遠回「沒在跑」），沒有任何其他訊號會提醒。"""
        sh = (Path(dev_start.ROOT) / "AutoClaude" / "tools" / "run_local_nightly.sh")
        ps1 = (Path(dev_start.ROOT) / "AutoClaude" / "tools" / "run_local_nightly.ps1")
        # R59 ARCH-R59-04：原寫 `.split("/")[-1]`＝只鎖檔名 `.nightly_mac.lock`，
        # 不鎖目錄。把 `.sh` 的鎖目錄從 AutoClaude/logs/ 搬到別處而檔名不變 → 本鎖照樣
        # 綠，而 `_nightly_running()` 會永遠在錯的路徑找不到鎖、回 False＝假「沒在跑」，
        # DEF-101-504 原樣復發且零訊號。這是「鎖自己留了一個它宣稱要守的洞」，且與同一
        # 測試 Windows 側鎖完整 Mutex 字面值的做法不對稱。改鎖完整相對路徑。
        self.assertIn(dev_start._NIGHTLY_POSIX_LOCK,
                      sh.read_text(encoding="utf-8", errors="replace"))
        # R59 QA-R59-05：原為全檔 assertIn，而該 Mutex 名在 .ps1 內出現兩次
        # （功能碼的 New-Object 與一行 Write-Output 訊息）。只改功能碼那一處、保留訊息
        # 字面，本鎖與 AutoClaude 側同款全檔鎖都會照綠，而 `_nightly_running()` 對真的
        # 在跑的 nightly 靜默回 False＝假「沒在跑」，DEF-101-504 的保護整體歸零。
        # 改為鎖住**實際建立 Mutex 的那一句**。
        ps1_text = ps1.read_text(encoding="utf-8", errors="replace")
        self.assertIn(
            f"System.Threading.Mutex($false, '{dev_start._NIGHTLY_MUTEX_NAME}')",
            ps1_text,
            "必須鎖住實際建立 Mutex 的那一句，而非全檔任意提及（QA-R59-05）")


class TestCheckNightlyFlag(DevStartTestCase):
    """`--check-nightly`：useMacWin.md 提示詞在「手動 git merge 之前」呼叫的撞車防呆
    查詢。此處刻意連「不得順便跑整備七步」一起鎖——它若不小心走完 main() 全程，
    等於在使用者只想查狀態時偷偷同步/裝依賴，比沒有這支旗標更糟。
    """

    def _run(self, nightly_state):
        with mock.patch.object(dev_start, "_nightly_running", return_value=nightly_state), \
                mock.patch.object(dev_start, "step_sync") as sync, \
                mock.patch.object(dev_start, "step_venv") as venv, \
                mock.patch("builtins.print") as printed:
            rc = dev_start.main(["--check-nightly"])
        out = " ".join(str(c.args[0]) for c in printed.call_args_list if c.args)
        return rc, out, sync, venv

    def test_running_returns_rc1_and_names_the_state(self):
        rc, out, sync, venv = self._run(True)
        self.assertEqual(rc, 1)
        self.assertIn("NIGHTLY-RUNNING", out)
        sync.assert_not_called()
        venv.assert_not_called()

    def test_idle_returns_rc0(self):
        rc, out, sync, venv = self._run(False)
        self.assertEqual(rc, 0)
        self.assertIn("idle", out)
        sync.assert_not_called()
        venv.assert_not_called()

    def test_undetermined_is_not_reported_as_running(self):
        """無法判定時不可回 rc=1——防呆機制自己失敗就擋住開工，比不防呆更擾民。"""
        rc, out, sync, venv = self._run(None)
        self.assertEqual(rc, 0)
        self.assertIn("UNDETERMINED", out)
        sync.assert_not_called()


class TestCacheRestoreTrustRestoredBranch(DevStartTestCase):
    """QA 複審覆蓋缺口立案（round 2／b2a9cf2 核心防線，原文＝Guard_Repin 證據檔 §D-4）。
    透過 _ensure_venv_shape() 驗證端到端行為（含實際 rename 是否發生），而非只測
    _cache_restore_trust 的回傳值。
    """

    @staticmethod
    def _make_fake_interpreter(py: Path, healthy: bool) -> None:
        py.parent.mkdir(parents=True, exist_ok=True)
        if healthy:
            # R3 QA 發現：shebang 腳本在 Windows 上不可執行會誤判「不健康」
            # （原文＝Guard_Repin 證據檔 §D-5）；改複製真正在跑的直譯器本體。
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
        # R17 DEF-101-231：_pid_alive() 的 Windows 判斷改呼叫 platform_utils.is_windows()
        # （不再讀 os.name），故 mock 目標同步改為該函式，而非 dev_start.os.name。
        with mock.patch.object(ctypes, "windll", fake_windll, create=True), \
             mock.patch.object(dev_start.platform_utils, "is_windows", return_value=True):
            self.assertTrue(dev_start._pid_alive(4242))
        fake_kernel32.CloseHandle.assert_called_once_with(12345)

    def test_open_process_fails_with_access_denied_is_alive(self):
        fake_kernel32 = mock.Mock()
        fake_kernel32.OpenProcess.return_value = 0
        fake_kernel32.GetLastError.return_value = 5  # ERROR_ACCESS_DENIED
        fake_windll = mock.Mock(kernel32=fake_kernel32)
        with mock.patch.object(ctypes, "windll", fake_windll, create=True), \
             mock.patch.object(dev_start.platform_utils, "is_windows", return_value=True):
            self.assertTrue(dev_start._pid_alive(4242))

    def test_open_process_fails_with_other_error_is_dead(self):
        fake_kernel32 = mock.Mock()
        fake_kernel32.OpenProcess.return_value = 0
        fake_kernel32.GetLastError.return_value = 87  # ERROR_INVALID_PARAMETER
        fake_windll = mock.Mock(kernel32=fake_kernel32)
        with mock.patch.object(ctypes, "windll", fake_windll, create=True), \
             mock.patch.object(dev_start.platform_utils, "is_windows", return_value=True):
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
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestStreamOnStartCallback WHY〉節。"""

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
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestStreamOtherOSErrorDoesNotCrash WHY〉節。"""

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

    @unittest.skipIf(os.name == "nt", "[POSIX-NATIVE-ONLY] pgid 語意僅適用 POSIX")
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

        # R17 DEF-101-231：_stream() 的 new_process_group Windows 判斷改呼叫
        # platform_utils.is_windows()（不再讀 os.name），mock 目標同步改為該函式。
        with mock.patch.object(dev_start.platform_utils, "is_windows", return_value=True), \
             mock.patch.object(dev_start.subprocess, "Popen", side_effect=fake_popen):
            rc = dev_start._stream(["irrelevant"], new_process_group=True)

        self.assertEqual(rc, 0)
        self.assertNotIn(
            "start_new_session", captured_kwargs,
            "Windows 上不可傳遞 start_new_session（POSIX-only kwarg，Windows 上"
            "subprocess.Popen 對非假值會拋 ValueError）")

    @unittest.skipIf(os.name == "nt", "[POSIX-NATIVE-ONLY] pgid 語意僅適用 POSIX")
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
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestOrphanChildLockRegression WHY〉節。"""

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
            # R3 QA 發現（Windows-only）：Popen 物件持有子行程 handle 未關閉會讓
            # _pid_alive() 誤判仍存活，故顯式 del 釋放（原文＝Guard_Repin 證據檔 §D-6）。
            del proc
            # R59 DEF-101-523：del 後 Windows 核心釋放行程物件仍有極短延遲，改為
            # 有界等待（≤2s、20 次輪詢）後才斷言（本輪實測與處置原文同上 §D-6）。
            with mock.patch.object(dev_start, "LOCK_FILE", lock_file):
                peeked = dev_start._peek_bootstrap_lock()
                for _ in range(20):
                    if peeked is None:
                        break
                    time.sleep(0.1)
                    peeked = dev_start._peek_bootstrap_lock()
                self.assertIsNone(peeked,
                                  "② 子行程結束後 peek 應回傳 None（已給 ≤2s 有界等待，"
                                  "仍非 None 即為真缺陷而非核心釋放延遲）")

    @unittest.skipUnless(
        os.name == "nt",
        "[WINDOWS-NATIVE-ONLY] 具名 Mutex 是 Windows 核心物件語意，只在原生 Windows 上"
        "測得到 True 分支（R43 DEF-101-348 標籤，供 run_root_unittests.py 彙整可見度）",
    )
    def test_nightly_running_true_branch_on_windows_mutex(self):
        """QA-R59-08：`_nightly_running()` 的 **Windows True 分支**正控測試。

        WHY：既有 `TestNightlyRunningDetection` 自陳只走 posix 分支（Windows 分支需要真的
        有 nightly 在跑才測得到 True），於是 DEF-101-504 真正提供保護的那條路徑在本輪之前
        從未被任何常駐測試觸及——帳本原本的「獨立驗證」跑的是 idle 分支，而 idle 正是
        **什麼都不做**的那一個。本測試自持一個**測試專用名稱**的具名 Mutex（不碰真排程用的
        正式鎖，比照 `test_run_local_nightly_static.py` 既有 `_TestOnly` 命名慣例）並斷言
        偵測回 True；釋放後回 False。
        """
        import ctypes

        # R59 二審 SD-R59-P3-2：原寫 `"Global\AutoClaude_..."`（非 raw 字串），`\A` 是**無效
        # 轉義序列** → DeprecationWarning（3.12+ 升 SyntaxWarning、未來版本為錯）。值剛好正確，
        # 但 production SSOT `tools/dev_start.py` 寫的是 `"Global\\AutoClaude_Nightly_Run"`，
        # 這裡對齊它的寫法。ruff 抓不到（W605 不在本 repo 選用規則集內）。
        test_name = "Global\\AutoClaude_Nightly_Run_R59TestOnly"
        handle = ctypes.windll.kernel32.CreateMutexW(None, False, test_name)
        self.assertTrue(handle, "CreateMutexW 失敗，無法建立測試用具名 Mutex")
        try:
            with mock.patch.object(dev_start, "_NIGHTLY_MUTEX_NAME", test_name):
                self.assertIs(
                    dev_start._nightly_running(), True,
                    "持有具名 Mutex 時必須偵測為 True——否則真的有 nightly 在跑也偵測不到"
                    "（DEF-101-504 的保護整體歸零）",
                )
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
        with mock.patch.object(dev_start, "_NIGHTLY_MUTEX_NAME", test_name):
            self.assertIs(
                dev_start._nightly_running(), False,
                "釋放 Mutex 後必須回 False（OS 自動回收具名物件）",
            )

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
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestStreamNewProcessGroupSurvivesDirectChildDeath WHY〉節。"""

    @unittest.skipIf(os.name == "nt",
                      "[POSIX-NATIVE-ONLY] process group / os.killpg 僅適用 POSIX；Windows 維持既有"
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
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestBootstrapProcessGroupSurvivesDirectChildKill WHY〉節。"""

    @unittest.skipIf(os.name == "nt",
                      "[POSIX-NATIVE-ONLY] process group / os.killpg 僅適用 POSIX；Windows 維持既有"
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
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestSigintForwardsToBootstrapProcessGroup WHY〉節。"""

    def setUp(self) -> None:
        super().setUp()
        dev_start._set_active_bootstrap_pgid(None)

    def tearDown(self) -> None:
        dev_start._set_active_bootstrap_pgid(None)
        super().tearDown()

    @unittest.skipIf(os.name == "nt", "[POSIX-NATIVE-ONLY] SIGINT/os.killpg 訊號轉發僅適用 POSIX；"
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
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestNormalBootstrapFlowUnaffectedByProcessGroupChange WHY〉節。"""

    @unittest.skipIf(os.name == "nt", "[POSIX-NATIVE-ONLY] pgid 語意僅適用 POSIX；Windows 分支未變動")
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

    @unittest.skipIf(os.name == "nt", "[POSIX-NATIVE-ONLY] pgid 語意僅適用 POSIX；Windows 分支未變動")
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
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestDescendantWatcherFinalSyncSampleWindows WHY〉節。"""

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
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestBootstrapIncompleteMarker WHY〉節。"""

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
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestRootLevelBootstrapIncompleteMarker WHY〉節。"""

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
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestRunBootstrapWiresRootMarkerBeforeStream WHY〉節。"""

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
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestRunBootstrapPassesNewProcessGroupToStream WHY〉節。"""

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
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestStepSwitchCacheCleanup WHY〉節。"""

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
            # mock 掉避免測試中打真實 gh 網路呼叫（SUMMARY["sync"] 未設時三閘不攔）；
            # 表② 指紋哨兵同理 mock 掉，隔離真 subprocess（Gap C）。
            with mock.patch.object(dev_start, "ROOT", repo), \
                 mock.patch.object(dev_start, "_check_ci_liveness",
                                   return_value=None), \
                 mock.patch.object(dev_start, "_check_onboarding_snapshot",
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
            # 同上：mock 掉 CI 活性哨兵避免真實 gh 網路呼叫；表② 指紋哨兵同理
            with mock.patch.object(dev_start, "ROOT", repo), \
                 mock.patch.object(dev_start, "_check_ci_liveness",
                                   return_value=None), \
                 mock.patch.object(dev_start, "_check_onboarding_snapshot",
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
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestMainInstallsSignalHandlerReference WHY〉節。"""

    @unittest.skipIf(os.name == "nt", "[POSIX-NATIVE-ONLY] 本 handler 僅在 POSIX 安裝（見 main() 內"
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
            # R69（windows-compat-ci 假紅姊妹站點）：join 的必須是 print 的**實際引數**，
            # 不是 `mock.call` 物件的 repr——repr 會把 Windows 路徑分隔符轉義（`\a` → `\\a`）
            # 並把換行變 `\n` 字面，使任何對路徑／多行文案的 assertIn 在 Windows 必假紅。
            printed = " ".join(str(a) for c in fake_print.call_args_list for a in c.args)
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
            # 狀態漂移；_check_ci_liveness 走 is_repo=False 閘自然回 None；
            # 表② 指紋哨兵 mock 掉隔離真 subprocess（Gap C）。
            with mock.patch.object(dev_start, "ROOT", root), \
                 mock.patch.object(dev_start, "_launchd_nightly_loaded",
                                   return_value=None), \
                 mock.patch.object(dev_start, "_check_onboarding_snapshot",
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


class TestOnboardingSnapshotProbe(DevStartTestCase):
    """判準本體住 `tools/lib/onboarding_snapshot_note.py`（本檔為 thin adapter）。
    WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestOnboardingSnapshotProbe WHY〉節。
    """

    @staticmethod
    def _completed(rc: int, stderr: str = "") -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=[], returncode=rc, stdout="ℹ️ 別平台欄恆亮段\n", stderr=stderr)

    def _probe(self, **run_kwargs):
        with mock.patch.object(dev_start.onboarding_snapshot_note.subprocess,
                               "run", **run_kwargs), \
             mock.patch("builtins.print") as fake_print:
            note = dev_start._check_onboarding_snapshot()
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args)
        return note, printed

    def test_stale_rc1_warns_with_routing_and_note(self):
        """(a) rc=1：note 非 None、指路句入 WARNINGS、stderr ❌ 條列有轉印。"""
        note, printed = self._probe(return_value=self._completed(
            1, stderr="❌ ONBOARDING.md §7 表② presumed stale：\n  - autoclaude 格指紋漂移\n"))
        self.assertIsNotNone(note)
        self.assertIn("stale", note)
        joined = "\n".join(dev_start.WARNINGS)
        self.assertIn("useMacWin.md 第 7 步", joined, "指路句必須入 WARNINGS")
        self.assertIn("回填要排在 commit/push 之前", joined)
        self.assertIn("autoclaude 格指紋漂移", printed, "stderr ❌ 條列須轉印")
        self.assertNotIn("恆亮段", printed, "stdout ℹ️ 恆亮段不得轉印（背景噪音紀律）")

    def test_fresh_rc0_is_quiet_and_note_says_match(self):
        """(b) rc=0：零 warn、note 含「相符」。"""
        note, _printed = self._probe(return_value=self._completed(0))
        self.assertIn("相符", note)
        self.assertEqual(dev_start.WARNINGS, [])

    def test_oserror_and_timeout_degrade_silently(self):
        """(c) OSError/TimeoutExpired：不拋例外、回 None、不入 WARNINGS。"""
        for effect in (OSError("I/O error"),
                       subprocess.TimeoutExpired(cmd="x", timeout=60)):
            with self.subTest(effect=type(effect).__name__):
                dev_start.WARNINGS.clear()
                note, _printed = self._probe(side_effect=effect)
                self.assertIsNone(note)
                self.assertEqual(dev_start.WARNINGS, [])

    def test_rc2_tool_refusal_is_not_a_verdict(self):
        """(c') rc=2 是工具自身模式錯誤／平台拒絕，不是指紋判決 → None、零 warn。"""
        note, _printed = self._probe(return_value=self._completed(
            2, stderr="❌ 模式旗標互斥\n"))
        self.assertIsNone(note)
        self.assertEqual(dev_start.WARNINGS, [])

    def test_step_platform_summary_includes_snapshot_note(self):
        """(d) 整合：SUMMARY["platform"] 含新片段（mock lib 函式、真 adapter＋真接線）。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with mock.patch.object(dev_start, "ROOT", root), \
                 mock.patch.object(dev_start, "_launchd_nightly_loaded",
                                   return_value=None), \
                 mock.patch.object(dev_start.onboarding_snapshot_note,
                                   "check_onboarding_snapshot",
                                   return_value="表② 指紋相符"), \
                 mock.patch("builtins.print"):
                dev_start.step_platform("mac", is_repo=False)
        self.assertIn("表② 指紋相符", dev_start.SUMMARY["platform"])

    def test_step_platform_calls_probe_exactly_once(self):
        """(e) 佈線存在鎖：step_platform 恰呼叫一次；None 時不入 summary。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with mock.patch.object(dev_start, "ROOT", root), \
                 mock.patch.object(dev_start, "_launchd_nightly_loaded",
                                   return_value=None), \
                 mock.patch.object(dev_start, "_check_onboarding_snapshot",
                                   return_value=None) as probe, \
                 mock.patch("builtins.print"):
                dev_start.step_platform("mac", is_repo=False)
        probe.assert_called_once()
        self.assertNotIn("表②", dev_start.SUMMARY["platform"],
                         "None＝無法判定，不得入 summary（靜默降級語意）")


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
        self.assertGreater(
            pos_exit, pos_call,
            "write_heartbeat 呼叫須在 exit 判定之前（失敗路徑也要寫）",
        )

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
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestVenvPythonVersionSentinel WHY〉節。"""

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
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestVenvPythonVersionRealBody WHY〉節。"""

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

    def _heartbeat_with_launchctl(self, stdout: str, rc: int = 0,
                                  plist_target: str | None = "__mine__"):
        """在空 ROOT（心跳必缺席）+ 假 darwin + 假 launchctl 下跑心跳哨兵。

        🔴 R68：`_launchd_nightly_loaded()` 命中 label 後還會讀
        `~/Library/LaunchAgents/<label>.plist` 來鑑別「指向的是不是本 checkout」。
        那是**真機檔案**，不 mock 就會讓本類別的結果取決於跑測試的機器裝了什麼排程
        （R68 實測：本機真有該 plist，於是 True 態被判成「指向另一份 checkout」而假紅）。
        `plist_target`：`"__mine__"`＝指向被 mock 的 ROOT（True 態）／字串＝別份
        checkout（str 態）／None＝讀不到（None 態，無鑑別力）。
        """
        fake = subprocess.CompletedProcess(args=["launchctl", "list"],
                                           returncode=rc, stdout=stdout, stderr="")
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(dev_start, "ROOT", Path(td)), \
             mock.patch.object(sys, "platform", "darwin"), \
             mock.patch.object(dev_start.subprocess, "run", return_value=fake), \
             mock.patch("builtins.print") as fake_print:
            target = (Path(td) / "AutoClaude" / "tools" / "run_local_nightly.sh"
                      if plist_target == "__mine__" else
                      (Path(plist_target) if plist_target else None))
            with mock.patch.object(dev_start, "_launchd_plist_target",
                                   return_value=target):
                note = dev_start._check_nightly_heartbeat("mac")
        # R69（windows-compat-ci 假紅）：join 的是 print 的**實際引數**，不是 call 物件的 repr。
        # repr 會把路徑分隔符轉義（Windows 上 `\elsewhere` → repr 成 `\\elsewhere`），
        # 於是任何對路徑的 assertIn 都會在 Windows 假紅。行 2728 已是此寫法，此處對齊。
        printed = " ".join(str(a) for c in fake_print.call_args_list for a in c.args)
        return note, printed

    # 別份 checkout 的 nightly 腳本路徑（字串字面值；由被測路徑經 Path 正規化後才比對）
    _ELSEWHERE = "/elsewhere/AutoClaude/tools/run_local_nightly.sh"

    def test_loaded_but_pointing_at_another_checkout_is_not_reported_as_normal(self):
        """R68 新四態的 str 態：label 全機唯一，第二個 clone／搬過家的 repo 會「命中
        label 但排程其實指向別份 checkout」。此時**不得**沿用 True 態的「已載入、
        尚未跑過第一輪」正常措辭——那會讓使用者以為本 repo 有 nightly 兜底，實際沒有。

        🔴 R69（windows-compat-ci 假紅）：斷言不得寫死 POSIX 字面值 `"/elsewhere"`——生產碼印的是
        `Path` 物件，其 `str()` 在 Windows 是 `\\elsewhere\\AutoClaude\\…`，字面值必然
        落空（windows-compat-ci 實紅）。改比對 `str(Path(self._ELSEWHERE))`：兩平台各自
        正規化後仍要求**整條目標路徑**出現在訊息裡——比原本只找 `/elsewhere` 更嚴，
        不是把斷言改弱。
        """
        out = f"{self._DECOY}\n-\t0\tcom.autoclaude.nightly\n"
        note, printed = self._heartbeat_with_launchctl(out, plist_target=self._ELSEWHERE)
        self.assertNotIn("launchd 已載入、尚未跑過第一輪", printed,
                         "指向別份 checkout 卻用 True 態措辭 ⇒ 誤報本 repo 有兜底")
        self.assertIn(str(Path(self._ELSEWHERE)), printed,
                      "須指出實際指向的路徑，否則無從排查")

    def test_unreadable_plist_falls_back_to_none_not_a_false_normal(self):
        """plist 讀不到 ⇒ 無鑑別力，必須退回 None 態的雙可能文案，不得謊報正常。"""
        out = f"{self._DECOY}\n-\t0\tcom.autoclaude.nightly\n"
        note, printed = self._heartbeat_with_launchctl(out, plist_target=None)
        self.assertNotIn("launchd 已載入、尚未跑過第一輪", printed)
        self.assertIn("排程可能未啟用", printed)

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

    def test_win32_returns_none_without_spawning(self):
        """DEF-101-243③／R19／DEF-101-247③ 立案：win32 專屬案例與三重 mock 視野缺口
        （原文＝Guard_Repin 證據檔 §D-3）。三重 mock 涵蓋 `subprocess.run`／`Popen`／
        `os.system`／`os.posix_spawn`，確保「提早 return、不 spawn 任何子行程」的
        意圖被完整鎖住。"""
        with mock.patch.object(sys, "platform", "win32"), \
             mock.patch.object(dev_start.subprocess, "run") as fake_run, \
             mock.patch.object(dev_start.subprocess, "Popen") as fake_popen, \
             mock.patch.object(dev_start.os, "system") as fake_system, \
             mock.patch.object(dev_start.os, "spawnv") as fake_spawnv, \
             mock.patch.object(dev_start.os, "posix_spawn", create=True) as fake_posix_spawn:
            self.assertIsNone(dev_start._launchd_nightly_loaded())
        fake_run.assert_not_called()
        fake_popen.assert_not_called()
        fake_system.assert_not_called()
        fake_spawnv.assert_not_called()
        fake_posix_spawn.assert_not_called()


class TestHeartbeatFailSentinel(DevStartTestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestHeartbeatFailSentinel WHY〉節。"""

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


class TestWindowsHeartbeatFailSentinel(DevStartTestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestWindowsHeartbeatFailSentinel WHY〉節。"""

    @staticmethod
    def _write_windows_log(root: Path, body: str) -> Path:
        logs = root / "AutoClaude" / "logs"
        logs.mkdir(parents=True)
        p = logs / "nightly_latest.log"
        p.write_text(body, encoding="utf-8")
        return p

    def _run(self, root: Path) -> str:
        with mock.patch.object(dev_start, "ROOT", root), \
             mock.patch("builtins.print"):
            return dev_start._check_nightly_heartbeat("windows")

    def test_exit_1_with_failed_stages_warns_with_note(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_windows_log(
                root,
                "[2026-07-22 02:00:00][INFO] BEGIN nightly run\n"
                "[2026-07-22 02:30:00][INFO] END nightly summary: mutation=1 "
                "pg-e2e=0 perf=0 drift=0 obs=0 local_ci_gate=0 sdd_chaos=0\n"
                "[2026-07-22 02:30:00][ERROR] END exit decision: exit=1 "
                "(failed stages: mutation=1)\n"
                "[2026-07-22 02:30:01][INFO] Latest log pointer 已更新: x\n",
            )
            note = self._run(root)
        self.assertTrue(
            any("exit=1" in w and "mutation=1" in w and "ARCH-R15-1" in w
                for w in dev_start.WARNINGS),
            f"exit=1 須 _warn（含 exit code 與 failed stages），"
            f"實際 WARNINGS={dev_start.WARNINGS}")
        self.assertIn("exit=1", note, "summary 片段須附註 exit code")
        self.assertIn("mutation=1", note, "summary 片段須附註 failed stages")

    def test_exit_0_no_warning(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_windows_log(
                root,
                "[2026-07-22 02:00:00][INFO] BEGIN nightly run\n"
                "[2026-07-22 02:30:00][INFO] END nightly summary: mutation=0 "
                "pg-e2e=0 perf=0 drift=0 obs=0 local_ci_gate=0 sdd_chaos=0\n"
                "[2026-07-22 02:30:00][INFO] END exit decision: exit=0 "
                "(no failed stages; SKIP/WARN 不計失敗)\n",
            )
            note = self._run(root)
        self.assertEqual(dev_start.WARNINGS, [], "exit=0（全綠）不得出現任何警告")
        self.assertEqual(note, "nightly 心跳新鮮")

    def test_large_log_tail_scan_still_finds_marker(self):
        """全量 log 可能數 MB（完整 pytest/mutmut 輸出）——驗證 tail 視窗機制在
        錨點前有大量雜訊時仍能命中，不需整檔載入。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            noise = "[2026-07-22 01:00:00][INFO] " + ("x" * 200) + "\n"
            body = noise * 500 + (
                "[2026-07-22 03:00:00][ERROR] END exit decision: exit=1 "
                "(failed stages: perf=1, drift=2)\n"
            )
            self._write_windows_log(root, body)
            note = self._run(root)
        self.assertIn("exit=1", note)
        self.assertIn("perf=1", note)

    def test_no_marker_found_returns_none_safely(self):
        """讀不到/無錨點（如安裝早期版本或檔案截斷）→ 安全回 None，不入警告、
        不崩潰（advisory 契約）。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_windows_log(root, "[2026-07-22 02:00:00][INFO] BEGIN nightly run\n")
            note = self._run(root)
        self.assertEqual(dev_start.WARNINGS, [])
        self.assertEqual(note, "nightly 心跳新鮮")

    #: R23 SD 點名的三種假陰性寫法（每列＝案例名／注入的收尾錨點行／期望出現在
    #: summary 片段裡的 failed stage）。R85／訴求 2：三支測試的判準與鷹架逐字相同，
    #: 只有注入字串不同 ⇒ 收斂成一張表；注入樣本與期望值一個不少，案例名改由 subTest
    #: 逐案報出。修復前 `_WINDOWS_EXIT_DECISION_RE` 對這三種偏離零容忍 → findall 零命中
    #: → 靜默回 None（即使 nightly 其實記錄失敗也不發警告，違反 fail-loud）。
    _FALSE_NEGATIVE_CASES = (
        ("decision: 後多一個空白",
         "[2026-07-22 02:30:00][ERROR] END exit decision:  exit=1 "
         "(failed stages: mutation=1)\n", "mutation=1"),
        ("END 寫成小寫 end",
         "[2026-07-22 02:30:00][ERROR] end exit decision: exit=1 "
         "(failed stages: perf=1)\n", "perf=1"),
        ("END 後多一個空白",
         "[2026-07-22 02:30:00][ERROR] END  exit decision: exit=1 "
         "(failed stages: drift=2)\n", "drift=2"),
    )

    def test_r23_false_negative_variants_are_still_detected(self):
        """R23 SD 點名的三種假陰性寫法今天都必須偵測得到（逐案，不聚合）。

        WHY 逐案而不是「任一命中即算過」：這三種偏離是**各自獨立**補進正則的，
        聚合斷言下任一種被改掉都不會轉紅，而那正是本族在防的事。

        🔴 R85／SD：樣本數鎖。表驅動化把三支測試方法收成一支 ⇒ unittest 的方法數少了 2，
        而**「表裡剩幾列」不再有任何東西在看**：刪掉一列的表徵是「少跑一個 subTest」，
        與正確地全部通過**逐字相同**。姊妹族 `test_check_wrapper_thinness` 的
        `_FORBIDDEN_CASES` 早有這道鎖，本族與下一族在 P2 收斂時漏補（SD 實測指出）。
        """
        self.assertEqual(
            len(self._FALSE_NEGATIVE_CASES), 3,
            "注入樣本數變了——本族是史料回歸鎖（R23 SD 點名的三種假陰性寫法），"
            "樣本只准增不准減；真的要退役某一列，請連同 `_WINDOWS_EXIT_DECISION_RE` "
            "對應的那一段容忍一起談")
        for label, line, stage in self._FALSE_NEGATIVE_CASES:
            with self.subTest(case=label):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td)
                    self._write_windows_log(root, line)
                    note = self._run(root)
                self.assertIn("exit=1", note, f"{label} 仍須偵測到 FAIL，不可假陰性")
                self.assertIn(stage, note, f"{label}：summary 片段須附註 failed stages")

    #: R25 DEF-101-263⑤ 的兩種**假陽性**語料（案例名／雜訊行）。R23 為容忍大小寫與空白偏離
    #: 把字面 `END` 改成 `re.IGNORECASE`，副作用是移除了隱性單字邊界：任何以 end 結尾的單字
    #: 緊接 `exit decision: exit=N` 就會被誤判成收尾錨點（修復前會發假警告）。單字邊界斷言
    #: 仍留一個縫（連字號結尾），故改用負向後顧一併收斂。R85／訴求 2：兩支測試判準與鷹架
    #: 逐字相同、只有雜訊行不同 ⇒ 收斂成一張表。
    _FALSE_POSITIVE_CASES = (
        ("backend（純字尾）", "daemon backend exit decision: "),
        ("high-end（連字號字尾）", "high-end exit decision: "),
    )

    def test_r25_end_suffixed_words_do_not_false_trigger(self):
        """兩種 end 結尾單字都不得誤觸發 END 收尾錨點警告（逐案，不聚合）。

        WHY 逐案：單字邊界斷言與「排除單字字元／連字號」的負向後顧是**兩次**分開的收斂
        （後者是一審 SA 二審複核追加），
        聚合斷言下把後者改回 `\b` 不會轉紅，而那正是這一族在防的事。

        🔴 R85／SD：樣本數鎖，立案理由同上一族（表驅動化之後「表裡剩幾列」無人在看，
        刪一列與全數通過的表徵逐字相同）。本族只有兩列，少一列就是**半個判準**——
        純字尾與連字號字尾分屬兩次收斂，砍掉任一列都會讓另一次收斂變成無人守。
        """
        self.assertEqual(
            len(self._FALSE_POSITIVE_CASES), 2,
            "注入樣本數變了——本族是 DEF-101-263⑤ 的史料回歸鎖，樣本只准增不准減")
        for label, noise in self._FALSE_POSITIVE_CASES:
            with self.subTest(case=label):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td)
                    self._write_windows_log(
                        root,
                        "[2026-07-23 02:00:00][INFO] BEGIN nightly run\n"
                        f"[2026-07-23 02:15:00][DEBUG] {noise}"
                        "exit=1 (failed stages: ghost=1)\n",
                    )
                    note = self._run(root)
                self.assertEqual(
                    dev_start.WARNINGS, [],
                    f"「{label}」不得誤觸發 END 收尾錨點警告")
                self.assertEqual(note, "nightly 心跳新鮮")

    def test_ps1_literal_end_exit_decision_lines_present_and_matched(self):
        """R25 DEF-101-263②：`_WINDOWS_EXIT_DECISION_RE` 與
        `run_local_nightly.ps1` 的 `Log(...)` 字面量目前靠人工核對一致、無機械
        鎖——任一方未來格式漂移會讓本正則靜默零比對（假陰性）。本測試跨檔讀取
        `.ps1` 實際字面量並斷言正則能命中，仿 `test_schedule_capability_parity.py`
        的「鏡子自證」模式：先斷言字面量真的存在於檔案中（避免抽取本身失準造成
        測試裝飾性通過），再驗證正則對其確實有鑑別力。"""
        ps1_path = (
            Path(__file__).resolve().parents[2]
            / "AutoClaude" / "tools" / "run_local_nightly.ps1"
        )
        ps1_text = ps1_path.read_text(encoding="utf-8-sig")
        fail_literal = (
            'Log ("END exit decision: exit=1 (failed stages: {0})" -f '
            "($finalFailures -join ', ')) 'ERROR'"
        )
        ok_literal = (
            "Log 'END exit decision: exit=0 (no failed stages; "
            "SKIP/WARN 不計失敗)'"
        )
        self.assertIn(
            fail_literal, ps1_text,
            "鏡子自證：.ps1 側失敗分支字面量若已改版，本斷言先炸，"
            "避免下方正則比對在錯誤前提下裝飾性通過",
        )
        self.assertIn(
            ok_literal, ps1_text,
            "鏡子自證：.ps1 側成功分支字面量若已改版，本斷言先炸",
        )
        rendered_fail = fail_literal.replace("{0}", "mutation=1, perf=2").split(
            '" -f', 1)[0].split('Log ("', 1)[1]
        match = dev_start._WINDOWS_EXIT_DECISION_RE.search(rendered_fail)
        self.assertIsNotNone(match, "正則須能命中 .ps1 實際失敗分支字面量渲染後結果")
        self.assertEqual(match.group(1), "1")
        rendered_ok = ok_literal.split("Log '", 1)[1].rstrip("'")
        match_ok = dev_start._WINDOWS_EXIT_DECISION_RE.search(rendered_ok)
        self.assertIsNotNone(match_ok, "正則須能命中 .ps1 實際成功分支字面量")
        self.assertEqual(match_ok.group(1), "0")


class TestCiLiveness(DevStartTestCase):
    """R15 DEF-101-208：CI 活性哨兵——gh read-only API 查最新 run 結論。

    三道靜默跳過閘（無 gh／sync 離線或跳過／非 repo）＋四態輸出。全部
    advisory：None＝不入 summary；「未知」不入 WARNINGS；僅非 success _warn。
    """

    def setUp(self):
        super().setUp()
        # 🔴 R68：`_check_ci_liveness()` 現在還會先做**逐軌陳舊度**查詢
        # （`ci_liveness.stale_schedule_tracks`），那是與本類別要驗的「最新一筆 run
        # 的四態輸出」正交的另一種粒度。不隔離掉它，本類別的單一 gh mock payload 會
        # 被它一起讀走——payload 裡的 `updatedAt` 只要距今超過該軌 cron 週期就被判陳舊
        # 並多出一筆 WARNING，紅因與被驗行為完全無關（R68 實測即如此假紅）。
        # 逐軌邏輯自身的鑑別力由 `TestStaleScheduleTracks` 專門驗，不是就此無覆蓋。
        p = mock.patch.object(dev_start.ci_liveness, "stale_schedule_tracks",
                              return_value=[])
        p.start()
        self.addCleanup(p.stop)

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
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestCrossSiteLiteralLocks WHY〉節。"""

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


class _NightlyHeartbeatDimensionMixin:
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start _NightlyHeartbeatDimensionMixin WHY〉節。"""

    _REPO = Path(dev_start.__file__).resolve().parents[1]
    _INSTALLER = _REPO / "tools" / "install_mac_nightly.sh"

    # 安裝器檔頭「與 dev_start 對齊的維度」機讀清單錨點（R67-E21）。
    _DIMENSIONS_RE = re.compile(r"DIMENSIONS:\s*([^)）]+)[)）]")

    def _installer_claimed_dimensions(self) -> list[str]:
        m = self._DIMENSIONS_RE.search(self._INSTALLER.read_text(encoding="utf-8"))
        self.assertIsNotNone(
            m,
            "install_mac_nightly.sh 檔頭的 `DIMENSIONS: ...` 機讀清單錨點消失——"
            "該清單是「--status 心跳語意與 dev_start 對齊」這句散文契約的唯一機械"
            "出口，移除它等於讓契約回到 R67-E21 之前的零訊號狀態",
        )
        return [d.strip() for d in m.group(1).split(",") if d.strip()]

    def _classify(self, text: str) -> dict[str, object]:
        """把一側的輸出化約成「逐維度判定」。

        dict 的鍵集合＝本鎖實際比對面，並由 `_installer_claimed_dimensions()`
        機械繫結到安裝器檔頭宣告，新增維度時漏改任一邊都會紅。
        """
        if "過期" in text:
            state = "過期"
        elif "新鮮" in text:
            state = "新鮮"
        elif "未偵測" in text:
            state = "未偵測"
        else:
            self.fail(f"無法從輸出判斷心跳三態分類：{text!r}")
        # FAIL 維度：兩側都只在 N>0 時才吐 `FAIL=N`，故「無命中」本身即為對稱語意。
        m = re.search(r"FAIL=(\d+)", text)
        # 年齡顯示維度（R68-M32）：判定早已對齊到秒（R67-M40），但「距今 N.N 天」
        # 這個**顯示值**兩側是各自合成的——bash 走整數十分位截斷、python 走
        # `{age_days:.1f}`，在 age_s=74304 分別印 0.8／0.9。上一輪的 8.5 天取樣點
        # 恰好落在兩側一致處，於是這個確定性分歧在既有鎖下完全靜默：宣告面與比對
        # 面雖已互鎖，兩者同時漏掉同一個維度時互鎖仍舊全綠。
        m_age = re.search(r"距今 ([\d.]+) 天", text)
        return {
            "三態": state,
            "FAIL 計數": int(m.group(1)) if m else None,
            "年齡顯示": m_age.group(1) if m_age else None,
        }


class TestNightlyHeartbeatDimensionContract(_NightlyHeartbeatDimensionMixin, unittest.TestCase):
    """R67-E21 的維度互鎖契約——**無平台條件**（R72 由下方 darwin-only 類別搬出）。"""

    def test_lock_covers_every_dimension_claimed_by_installer(self) -> None:
        """R67-E21：安裝器檔頭宣告的對齊維度，必須恰好等於本鎖實際比對的維度。

        兩個方向都要紅：安裝器新宣告一個維度而本鎖沒比對（宣稱大於實作）→ 紅；
        本鎖比對了一個安裝器沒宣告的維度（散文沒跟上）→ 也紅。這正是 R67-E21
        的根因形狀——契約寫在散文、鎖只驗子集，兩者之間沒有互鎖。
        """
        claimed = self._installer_claimed_dimensions()
        sample = self._classify("  ✅ 心跳：新鮮（距今 0.0 天）")
        self.assertEqual(
            sorted(claimed), sorted(sample.keys()),
            f"install_mac_nightly.sh 檔頭宣告對齊維度 {claimed}，但本鎖實際比對的是 "
            f"{sorted(sample.keys())}——兩者必須逐字相等。新增維度時三處要同時改："
            "① dev_start._check_nightly_heartbeat()／② install_mac_nightly.sh "
            "report_heartbeat()／③ 本檔 _classify() 與安裝器檔頭 DIMENSIONS 清單",
        )

    def test_installer_dimension_list_is_extracted_sane(self) -> None:
        """鏡子自證①：`_DIMENSIONS_RE` 確實從安裝器檔頭抽到**逐項**清單。

        沒有這一支，regex 若退化成「抓到一整團文字當單一維度」，上面那支的
        `sorted(claimed) == sorted(sample.keys())` 會直接紅——但讀者會被導向
        「生產碼漏了維度」這個錯誤結論。先證明抽取器本身沒壞，失敗訊息才可信
        （同 `test_schedule_capability_parity.py` 兩支 `_extracted_sane` 的理由）。
        """
        claimed = self._installer_claimed_dimensions()
        self.assertGreaterEqual(
            len(claimed), 3,
            f"DIMENSIONS 清單只抽到 {claimed}——regex 疑似把整段散文吞成一項",
        )
        for expected in ("三態", "FAIL 計數", "年齡顯示"):
            self.assertIn(expected, claimed, f"DIMENSIONS 抽取遺漏 {expected!r}：{claimed}")

    def test_classifier_reads_real_values_not_just_placeholders(self) -> None:
        """鏡子自證②：`_classify()` 對一份**三維度俱全**的真實形狀輸出要讀出真值。

        上面那支只餵「新鮮 0.0 天」——FAIL 維度在那份輸入上恆為 None，於是「分類器
        其實讀不到 FAIL」與「這次剛好沒有 FAIL」在它眼中完全一樣（R68-M32 逐字記過
        同型陷阱：兩側同時是 None 等於白守）。本支把三個維度各釘一個非平凡值。
        """
        got = self._classify(
            "⚠️ 心跳：過期（距今 8.5 天）\n"
            "===== nightly 彙總：PASS=4 FAIL=3 ====="
        )
        self.assertEqual(
            got, {"三態": "過期", "FAIL 計數": 3, "年齡顯示": "8.5"},
            f"分類器未能從真實形狀的輸出讀出三個維度的真值：{got}",
        )


@unittest.skipUnless(
    sys.platform == "darwin",
    "[MAC-NATIVE-ONLY] install_mac_nightly.sh 的 report_heartbeat() 依賴 BSD `stat -f %m`（見該檔"
    "頭『非 macOS fail-loud』guard，非 Darwin 上執行本身即為無意義假訊號，GNU "
    "stat 的 -f 語意也完全不同）——本鎖只在 macOS runner（macos-compat-ci.yml）"
    "上有意義，非 Darwin 平台跳過而非假綠",
)
class TestNightlyHeartbeatCrossSiteBehavioralEquivalence(
    _NightlyHeartbeatDimensionMixin, unittest.TestCase
):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestNightlyHeartbeatCrossSiteBehavioralEquivalence WHY〉節。"""

    # 維度契約面（`_REPO`／`_INSTALLER`／`_DIMENSIONS_RE`／`_installer_claimed_
    # dimensions()`／`_classify()`）已於 R72 移入 `_NightlyHeartbeatDimensionMixin`
    # ——那一段不需要 Darwin，留在這裡等於讓它跟著整組被 skip。

    # 兩側觀測「同一瞬間」時的精度差（R67-M40）：bash 的 `date +%s` 把該瞬間截斷成
    # 整數秒 N，python 的 `time.time()` 看到的是 N + 次秒。測試給 bash `IMN_NOW=N`、
    # 給 python `N + _SUBSECOND_SKEW`，模擬的就是這件事——若改成兩側都拿整數 N，
    # 恰好 8.0 天的邊界會因為次秒被抹掉而永遠一致，等於把要驗的東西驗掉了。
    _SUBSECOND_SKEW = 0.5

    def _bash_report_heartbeat_stdout(self, heartbeat_path: Path, now: int) -> str:
        """動態擷取 report_heartbeat() 函式本體，於獨立 bash 子行程執行（只餵它
        依賴的三個變數 HEARTBEAT／HEARTBEAT_MAX_AGE_DAYS／IMN_NOW，不觸碰真實
        launchd/plist 副作用、不 source 整支腳本以免誤觸其 case 分派或 Darwin
        guard 之外的其他邏輯），回傳其 stdout。

        R67-M38：門檻取自 `dev_start._HEARTBEAT_MAX_AGE_DAYS`，不得硬編（舊版
        寫死值曾讓本鎖假紅，原文＝Guard_Repin 證據檔 §D-9）。
        """
        extract = subprocess.run(
            ["sed", "-n", "/^report_heartbeat() {/,/^}/p", str(self._INSTALLER)],
            capture_output=True, text=True, check=True,
            encoding="utf-8", errors="replace",
        )
        func_src = extract.stdout
        self.assertTrue(
            func_src.strip(),
            "report_heartbeat() 函式擷取失敗（sed 找不到 report_heartbeat() { ... } "
            "區塊）——install_mac_nightly.sh 結構是否已變動？本測試的擷取正則須同步更新",
        )
        wrapper = (
            f'HEARTBEAT="{heartbeat_path}"\n'
            f'HEARTBEAT_MAX_AGE_DAYS={dev_start._HEARTBEAT_MAX_AGE_DAYS}\n'
            f'IMN_NOW={now}\n'
            f'{func_src}\n'
            'report_heartbeat\n'
        )
        proc = subprocess.run(
            # bash-ok: 本組 class 掛 @skipUnless(sys.platform == "darwin")，Windows 上
            # 恆不執行 ⇒ 無 WSL 佔位版劫持面（DEF-101-753）。
            ["bash", "-c", wrapper], capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        self.assertEqual(
            proc.returncode, 0,
            f"report_heartbeat() 於獨立 bash 子行程執行失敗（rc={proc.returncode}）："
            f"{proc.stderr}",
        )
        return proc.stdout

    def _python_classify(self, root: Path, now: int) -> dict[str, object]:
        printed: list[str] = []
        with mock.patch.object(dev_start, "ROOT", root), \
             mock.patch.object(dev_start, "WARNINGS", []), \
             mock.patch.object(dev_start, "_launchd_nightly_loaded",
                               return_value=None), \
             mock.patch("time.time",
                        return_value=float(now) + self._SUBSECOND_SKEW), \
             mock.patch("builtins.print",
                        side_effect=lambda *a, **k: printed.append(
                            " ".join(str(x) for x in a))):
            note = dev_start._check_nightly_heartbeat("mac")
        # R68-M32：年齡顯示只存在於「印出來的那一行」（新鮮走 print、過期走 _warn，
        # 後者內部亦是 print），回傳的 summary note 不含它。若仍只把 note 餵進
        # `_classify()`，新增的維度在 python 側恆為 None——鎖看起來多守了一維，
        # 實際上兩側同時是 None，等於白守（本輪修鎖時差點踩進去的坑）。
        return self._classify(note + "\n" + "\n".join(printed))

    def _make_heartbeat(self, root: Path, age_s: int, now: int,
                        fail_n: int = 0) -> Path:
        """寫出**真實的心跳檔契約**（AutoClaude/tools/run_local_nightly.sh
        write_heartbeat 的前 3 行格式），非佔位字串。

        R67-E21：舊版寫的是 `"heartbeat\\n"`——永遠沒有 `FAIL=` 行，於是不論兩側
        對 FAIL 維度的處置差多遠，這道鎖結構上都不可能看見。fixture 不長成生產
        形狀，鎖住的就只是 fixture 自己。
        """
        logs = root / "AutoClaude" / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        hb = logs / "nightly_mac_latest.log"
        lines = [
            "nightly_mac heartbeat（UTC）：2026-08-01T02:00:00Z",
            f"===== nightly 彙總：PASS={7 - fail_n} FAIL={fail_n} =====",
        ]
        if fail_n > 0:
            lines.append("失敗 stage： macos_smoke root_unittests")
        lines.append(f"log={logs / 'nightly_mac_20260801_020001.log'}")
        hb.write_text("\n".join(lines) + "\n", encoding="utf-8")
        # 整數秒 mtime：BSD `stat -f %m` 只給整數秒，讓 fixture 也落在整數秒上，
        # 兩側才是在比較「同一個年齡」而不是在比較各自的取整誤差（R67-M40）。
        os.utime(hb, (now - age_s, now - age_s))
        return hb

    def _assert_sides_agree(self, label: str, age_s: int, fail_n: int) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            now = int(time.time())
            hb = self._make_heartbeat(root, age_s, now, fail_n=fail_n)
            py_result = self._python_classify(root, now)
            bash_stdout = self._bash_report_heartbeat_stdout(hb, now)
            bash_result = self._classify(bash_stdout)
            self.assertEqual(
                py_result, bash_result,
                f"{label}：dev_start.py 逐維度判定={py_result!r}，但 "
                f"install_mac_nightly.sh report_heartbeat() 判定={bash_result!r}"
                f"（bash stdout={bash_stdout!r}）——兩份獨立實作分歧"
                "（DEF-101-042 同類『字面值鎖住、行為未鎖住』盲區）。"
                "若兩側門檻常數剛變更，先確認本測試 wrapper 注入的是 "
                "dev_start._HEARTBEAT_MAX_AGE_DAYS 而非硬編值（R67-M38）",
            )

    def test_fresh_boundary_and_far_stale_ages_classify_identically(self) -> None:
        """跨代表性年齡（極新鮮／剛好未過期／**恰好 8.0 天整**／逾期 1 秒／遠期），
        兩側判定須完全一致。

        R67-M40：`恰好 8.0 天整` 是舊版刻意避開的那一點——BSD `stat -f %m` 與
        `date +%s` 都只給整數秒，`os.stat().st_mtime` 卻保留次秒，於是 bash 算
        691200（`-gt` 為偽→新鮮）、python 算 691200.0x（`> 8` 為真→過期），實測
        10/10 必然分歧。修法是讓 python 側也先截成整數秒（dev_start.py
        `int(time.time()) - int(mtime)`），分歧被結構性消除而不是被測試繞開。
        `-gt` 為嚴格大於，故 8 天整＝新鮮、8 天又 1 秒＝過期。
        """
        day = 86400
        cases = {
            "極新鮮（0.01 天）": 864,
            "剛好未過期（7.9 天 < 8 天門檻）": 682560,
            "恰好 8.0 天整（R67-M40 邊界；嚴格大於故仍為新鮮）":
                dev_start._HEARTBEAT_MAX_AGE_DAYS * day,
            "逾期 1 秒（8 天 + 1 秒）":
                dev_start._HEARTBEAT_MAX_AGE_DAYS * day + 1,
            "剛好過期（8.1 天）": 699840,
            "遠期過期（30 天）": 30 * day,
        }
        for label, age_s in cases.items():
            with self.subTest(label=label):
                self._assert_sides_agree(label, age_s, fail_n=0)

    def test_fail_count_is_reported_identically(self) -> None:
        """R67-E21：FAIL 維度兩側須一致——mtime 只證明「排程在跑」，不證明「跑成綠」。

        真實情境：CI 因帳務停擺（DEF-101-081）時本地 nightly 是唯一每日兜底層，
        nightly 連續全紅時 mac 使用者照 ONBOARDING §8 跑 `--status` 會拿到 rc=0 ＋
        「✅ 心跳：新鮮」的全綠報告，而同一顆心跳檔在 dev_start 會出 ⚠️ 警告。
        新鮮／過期兩態都要驗：FAIL 偵測若被塞進「新鮮」分支內，過期路徑就會漏報。
        """
        day = 86400
        cases = {
            "全綠且新鮮（FAIL=0）": (day, 0),
            "全紅但新鮮（FAIL=3）——本缺陷的原始情境": (day, 3),
            "全紅且過期（FAIL=2）": (30 * day, 2),
        }
        for label, (age_s, fail_n) in cases.items():
            with self.subTest(label=label):
                self._assert_sides_agree(label, age_s, fail_n)

    def test_age_display_matches_dev_start_at_rounding_divergence_points(self) -> None:
        """R68-M32：「距今 N.N 天」的顯示值兩側須逐字相同。

        取樣點刻意選**修前確定分歧**的秒數，而不是再取一個好看的整點：
          74304 秒 → 修前 bash 印 0.8、dev_start 印 0.9（十分位截斷 vs 正確捨入）
          4320 秒  → 修前 bash 印 0.0、dev_start 印 0.1
          12960 秒 → 反向對照：把 bash 改成 round-half-up 的那種「假修」會在此點
                     新造分歧（0.2 vs 0.1），本點通過才能證明分歧是被消除、不是
                     被平移。R67-M39 的既有斷言取 8.5 天，那恰是兩側一致處，且只
                     驗 bash 單側——同一個顯示值上有鎖，卻鎖不到跨站分歧。
        """
        for label, age_s in {
            "74304 秒（修前 bash 0.8 ／ dev_start 0.9）": 74304,
            "4320 秒（修前 bash 0.0 ／ dev_start 0.1）": 4320,
            "12960 秒（round-half-up 假修會在此點新造分歧）": 12960,
        }.items():
            with self.subTest(label=label):
                self._assert_sides_agree(label, age_s, fail_n=0)

    def test_bash_wrapper_threshold_follows_dev_start_constant(self) -> None:
        """R67-M38：wrapper 注入的門檻必須跟著 `dev_start._HEARTBEAT_MAX_AGE_DAYS`。

        以 sentinel 門檻 10 天 ＋ 9 天心跳驗證：門檻為 10 時 bash 側必須判「新鮮」。
        若 wrapper 退回硬編 8，同一顆心跳會被判「過期」而紅——即「兩生產站點合法
        同步演進 8→10 會讓本 class 假紅」的最小可執行複現。
        """
        sentinel = 10
        with mock.patch.object(dev_start, "_HEARTBEAT_MAX_AGE_DAYS", sentinel), \
                tempfile.TemporaryDirectory() as td:
            now = int(time.time())
            hb = self._make_heartbeat(Path(td), 9 * 86400, now)
            stdout = self._bash_report_heartbeat_stdout(hb, now)
        self.assertEqual(
            self._classify(stdout)["三態"], "新鮮",
            f"門檻為 {sentinel} 天時 9 天心跳應判「新鮮」，實得 {stdout!r}——"
            "wrapper 疑似硬編門檻字面值而未取自 dev_start._HEARTBEAT_MAX_AGE_DAYS",
        )

    def test_stale_message_carries_no_false_inequality(self) -> None:
        """R67-M39：過期文案不得內嵌「N 天 > M 天」不等式。

        顯示精度（一位小數）與判定精度（秒）不同，(8,9) 天窗口內舊 bash 文案會印
        「距今 8 天 > 8 天」——數學上為偽，讀者會合理推斷工具算錯而忽略真實告警。
        取窗口正中央 8.5 天為代表：顯示須為 `8.5`，且整句不得出現不等式。
        """
        with tempfile.TemporaryDirectory() as td:
            now = int(time.time())
            hb = self._make_heartbeat(Path(td), 8 * 86400 + 43200, now)
            stdout = self._bash_report_heartbeat_stdout(hb, now)
        self.assertIn("距今 8.5 天", stdout,
                      f"過期文案的天數顯示須與秒級判定同精度（一位小數）：{stdout!r}")
        self.assertNotRegex(
            stdout, r"距今\s*[\d.]+\s*天\s*>",
            f"過期文案內嵌不等式，(8,9) 天窗口會印出數學上為偽的句子：{stdout!r}",
        )


# ── install_mac_nightly.sh `--status` 報表契約（R67-M37 ／ R67-F29）──────────────
#
# R72：跨平台對稱鎖的靜態抽取器住在姊妹鎖檔（那裡本來就是「mac ↔ Windows 安裝器
# 語意能力對照」的家、且零平台條件）。此處 import 它是為了讓下方 darwin-only 的行為
# 驗證能拿「執行期實況」對帳「靜態預測」——量測面本身必須被驗證。跨測試模組 import
# 是本目錄既有慣例（見 test_ntfs_trailing_space_device_name.py 的
# `import test_windows_forbidden_filename_parity as _parity`）。
import test_schedule_capability_parity as _cap_parity  # noqa: E402

# 為何長在 test_dev_start.py 而不是自成一支 test_install_mac_nightly.py：
# `DEF-101-561③`／`DEF-101-565` 已裁定「R61 開輪起 tools/tests 禁止新增鎖檔、只准
# 合併／刪除」，並由 test_adr_xplat001_c1c2_lock.TestGuardLayerRatchet 機械強制
# （當時的實測：新開一支檔案即翻紅）。
# 🔴 R78 ARCH-03 訂正：那道棘輪 R77 起改量逐檔行數的**淨額**、也不再比 HEAD——
# 新增檔案本身不違規，淨行數上升才違規。本節併入本檔的理由與量測面無關，仍然成立。
# 本檔本來就是 install_mac_nightly.sh 三道跨站鎖的所在地（`test_installer_third_
# site_filename_and_threshold`／`TestCrossSiteLiteralLocks`／上方的行為等價鎖），
# 新判準擴充進來與既有同源鎖相鄰，正是該裁定指定的「合法作法」。
#
# 退化 plist：逐字重現「R15 之前安裝、且 repo 已搬過家」的機器實況——無 RunAtLoad、
# ProgramArguments 指向不存在的舊 checkout、StandardOutPath 導 /tmp（R14 ARCH-GAP-3
# 遷出前的落點，會被 macOS 週期清理）。三個缺陷都真實發生過，非杜撰。
_MACNIGHTLY_DEGENERATE_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" \
"http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.autoclaude.nightly</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>/nonexistent/OLD_PATH/run_local_nightly.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>2</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>/tmp/nightly_mac_launchd.log</string>
  <key>StandardErrorPath</key><string>/tmp/nightly_mac_launchd.err</string>
</dict>
</plist>
"""


@unittest.skipUnless(
    sys.platform == "darwin",
    "[MAC-NATIVE-ONLY] install_mac_nightly.sh 對非 Darwin 直接 fail-loud（該檔 `uname != Darwin` "
    "guard），且本組依賴 plutil／BSD `date -v`／launchd plist 語意——非 macOS 上"
    "執行本身即為無意義假訊號，跳過而非假綠",
)
class MacNightlyStatusTestCase(unittest.TestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start MacNightlyStatusTestCase WHY〉節。"""

    _REPO = Path(dev_start.__file__).resolve().parents[1]
    _INSTALLER = _REPO / "tools" / "install_mac_nightly.sh"
    # R72：`_WIN_INSTALLER` 隨跨平台對稱鎖一併移出（唯一消費者是那支測試，現落在
    # test_schedule_capability_parity.py 的 `_WIN_SCRIPT`）——留一個沒有消費者的路徑
    # 常數，下一位讀者會以為本類別仍在跨平台比對。
    _LABEL = "com.autoclaude.nightly"

    def installer_source(self) -> str:
        return self._INSTALLER.read_text(encoding="utf-8")

    def coverage_lookback_days(self) -> int:
        """回看天數取自安裝器本體，不在測試裡另立第 2 份字面值（R67-M38 同型教訓：
        測試自帶的「第 N 份常數副本」是最容易在合法演進時假紅的那一份）。"""
        m = re.search(r"^NIGHTLY_COVERAGE_DAYS=(\d+)", self.installer_source(),
                      re.MULTILINE)
        self.assertIsNotNone(
            m, "install_mac_nightly.sh 的 NIGHTLY_COVERAGE_DAYS 錨點消失")
        return int(m.group(1))

    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)
        self.addCleanup(self._td.cleanup)

        # 最小 repo 樹：安裝器 + nightly 載體 + logs 目錄
        (self.root / "tools").mkdir(parents=True)
        shutil.copy2(self._INSTALLER, self.root / "tools" / "install_mac_nightly.sh")
        (self.root / "AutoClaude" / "tools").mkdir(parents=True)
        self.nightly_sh = self.root / "AutoClaude" / "tools" / "run_local_nightly.sh"
        self.nightly_sh.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
        self.logs = self.root / "AutoClaude" / "logs"
        self.logs.mkdir(parents=True)

        # fake HOME（安裝器的 PLIST_DIR="${HOME}/Library/LaunchAgents"）
        self.home = self.root / "fakehome"
        self.plist_dir = self.home / "Library" / "LaunchAgents"
        self.plist_dir.mkdir(parents=True)
        self.plist_path = self.plist_dir / f"{self._LABEL}.plist"

        # stub launchctl：預設回報「已載入」，讓 exit code 維持 0，好讓 advisory
        # 維度的訊號不被「launchd 未載入」這件事掩蓋。
        self.launchctl = self.root / "stub_launchctl.sh"
        self.launchctl.write_text(
            "#!/bin/bash\n"
            f'if [ "$1" = "list" ]; then printf -- "-\\t0\\t{self._LABEL}\\n"; fi\n'
            "exit 0\n",
            encoding="utf-8",
        )
        os.chmod(self.launchctl, 0o755)

        # stub pmset：與 launchctl stub 同理由、同預設姿態（預設回報「健康」，讓
        # 其餘維度的訊號不被機器狀態掩蓋）。
        #
        # 🔴 R82 這道縫為何非有不可：WakeToRun／NextRunTime 兩列的輸入是**這台機器的
        # 電源排程狀態**（`pmset -g sched`），不是 plist 檔案內容。沒有這道縫，
        # `install_healthy_plist()` 就只定義了「健康」的一半，而
        # `test_healthy_plist_passes_every_capability_row` 那句「每列皆 ✅」實際上
        # 隱含要求「跑測試這台 Mac 剛好排過 pmset repeat」——那需要 sudo、安裝器
        # 刻意不代跑，是多數 Mac 的**非**常態 ⇒ 該鎖在真 mac 上結構性必紅。
        # 實證：本輪之前這兩支測試從未在真 mac 上跑綠過（R82 及更早都在 Windows
        # 完成，整組被 class 上的 @skipUnless(darwin) 跳掉），紅是第一次真的跑才浮出來的。
        # 縫換掉的是**量測面的來源**，不是覆蓋：兩列仍在「每列皆 ✅」的斷言裡，
        # 而且下面另有一組把它們打成 ⚠️ 的紅控制組，證明這裡不是橡皮圖章。
        self.pmset = self.root / "stub_pmset.sh"
        self.set_pmset(self.PMSET_HEALTHY)

    #: stub pmset 對「已排定每日喚醒」的輸出。**逐字取自真 pmset 的行為**，不是猜的：
    #: `strings /usr/bin/pmset` 內的輸出樣板是 `  %s at %s %s`、區段標題是
    #: `Repeating power events:`，而 %s 是 com.apple.AutoWake.plist 的 `eventtype`
    #: 原值（本機 `plutil -p` 實查該 plist 確認）；`pmset repeat wakeorpoweron` 的
    #: eventtype 即 `wakepoweron`。R82 曾把判準字面值寫成 `wake or poweron`，而
    #: `strings /usr/bin/pmset | grep -c "wake or poweron"` ＝ 0 ⇒ 那個判準恆不命中。
    #: 本常數釘住的正是這件事：若安裝器再退回押那句散文，本 stub 的輸出會判不出來、
    #: 健康控制組立刻轉紅。
    PMSET_HEALTHY = (
        'printf "Repeating power events:\\n'
        '  wakepoweron at 1:55AM every day\\n"\n'
        "exit 0\n"
    )
    #: pmset 存在、但一件排程都沒有——**本機實測的真實常態**（`pmset -g sched`
    #: rc=0、stdout 0 bytes）。這正是修前讓兩支測試轉紅的那個狀態。
    PMSET_NO_SCHEDULE = "exit 0\n"
    #: 只有一次性事件（macOS 自己常年掛著 calaccessd／osanalytics 的 user-invisible
    #: wake，本機 `plutil -p /Library/Preferences/SystemConfiguration/com.apple.AutoWake.plist`
    #: 實查到兩則）。它撐不起「每天 02:00 前叫醒」的語意，不得被算成已排定。
    PMSET_ONESHOT_ONLY = (
        'printf "Scheduled power events:\\n'
        ' [0]  wake at 08/11/2026 01:52:44 by \'com.apple.alarm.user-invisible\'\\n"\n'
        "exit 0\n"
    )
    #: 一次性的 **wakeorpoweron**——這才是「全文子字串比對」那個舊形態真正會吃下去的
    #: 假綠，而 `PMSET_ONESHOT_ONLY`（eventtype＝`wake`）**吃不到**：`wake` 不是詞彙表
    #: `wakepoweron|wakeorpoweron|poweron` 的子字串，所以那一支即使拿全文比對去跑也照樣綠
    #: （本輪實測：忠實還原全文比對 → 24 tests OK，rc=0）。⇒ 沒有這一支，
    #: 「一次性事件不得算數」這件事在**歷史上真的出過錯的那個形態**上是零覆蓋的。
    #:
    #: 🔴 這不是虛構的 OS 行為，是反組譯實證：一次性段的顯示路徑（` [%ld]  %s at %s`）
    #: 在印出前先把 eventtype 原值與 `wakepoweron` 逐位元組比對
    #: （`x9=0x65776f70656b6177`＝"wakepowe" ＋ `w10=0x006e6f72`＝"ron"），**相等就把顯示
    #: 字串換成字面值 `wakeorpoweron`**（`csel x24, x9, x8, ne`，x8 指向 0x15d53）。
    #: 重複段則不做這個代換、直印原值 ⇒ 同一個 eventtype 在兩段的渲染**不同**。
    #: 使用者把 `pmset repeat` 打成 `pmset schedule` 就會落在這一格：事件跑一次就沒了，
    #: 撐不起「每天 02:00 前叫醒」，但全文比對會回報「已排定」。
    PMSET_ONESHOT_WAKEORPOWERON = (
        'printf "Scheduled power events:\\n'
        " [0]  wakeorpoweron at 08/11/2026 01:55:00 by 'me'\\n\"\n"
        "exit 0\n"
    )

    def set_pmset(self, body: str) -> None:
        """換掉 stub pmset 的行為（body 為 shebang 之後的腳本本體）。"""
        self.pmset.write_text("#!/bin/bash\n" + body, encoding="utf-8")
        os.chmod(self.pmset, 0o755)

    def remove_pmset(self) -> None:
        """讓 `IMN_PMSET` 指向一個不存在的路徑＝模擬「這台機器沒有 pmset」。

        與 `PMSET_NO_SCHEDULE` 是**兩個不同的狀態**，安裝器必須分辨得出來
        （前者要人去裝／換機器，後者要人去跑那句 sudo 指令）。
        """
        self.pmset.unlink()

    def run_installer(self, *args: str) -> subprocess.CompletedProcess:
        """跑沙箱裡那份**真實的**安裝器（任意模式）。

        R68-M64：以前只有 `run_status()`，於是 install／--uninstall 兩條會真的
        改動機器狀態的路徑在測試側零行為覆蓋——「load 失敗仍宣稱成功」這種缺陷
        結構上不可能被任何既有鎖看到。fake HOME ＋ `IMN_LAUNCHCTL` stub 讓這兩條
        路徑可以在不觸碰真實 `~/Library/LaunchAgents`／真實 launchd 的前提下驗行為。
        R82 補上 `IMN_PMSET`：兩個 stub 一起，本夾具才真的與「跑測試那台機器的
        系統狀態」無關——否則報表裡仍有兩列的值是機器給的，測試對它零控制權。
        """
        return subprocess.run(
            # bash-ok: MacNightlyStatusTestCase 掛 @skipUnless(sys.platform == "darwin")
            # （受測物 install_mac_nightly.sh 對非 Darwin 自己就 fail-loud）⇒ Windows
            # 上恆不執行，無 WSL 佔位版劫持面（DEF-101-753）。
            ["bash", str(self.root / "tools" / "install_mac_nightly.sh"), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env={**os.environ, "HOME": str(self.home),
                 "IMN_LAUNCHCTL": str(self.launchctl),
                 "IMN_PMSET": str(self.pmset)},
        )

    def run_status(self) -> subprocess.CompletedProcess:
        return self.run_installer("--status")

    def set_launchctl(self, body: str) -> None:
        """換掉 stub launchctl 的行為（body 為 shebang 之後的腳本本體）。"""
        self.launchctl.write_text("#!/bin/bash\n" + body, encoding="utf-8")
        os.chmod(self.launchctl, 0o755)

    def stub_list_reports(self, last_exit: str) -> str:
        """stub 本體：`list` 回報本 label 已載入、第 2 欄（last exit status）為指定值。

        `launchctl list` 的三欄是 PID／Status／Label，PID 對非執行中的 job 為 `-`。
        """
        return (f'if [ "$1" = "list" ]; then '
                f'printf -- "-\\t{last_exit}\\t{self._LABEL}\\n"; fi\n'
                "exit 0\n")

    def install_healthy_plist(self) -> None:
        """用安裝器自己的 `--render-only` 產出 plist 再放進 fake HOME——手抄一份
        期望 plist 會製造第 2 個真相源，renderer 一改測試就假紅。"""
        rendered = self.root / "rendered.plist"
        proc = subprocess.run(
            # bash-ok: 同上，MacNightlyStatusTestCase 為 darwin-only（DEF-101-753）。
            ["bash", str(self.root / "tools" / "install_mac_nightly.sh"),
             "--render-only", str(rendered)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env={**os.environ, "HOME": str(self.home)},
        )
        self.assertEqual(proc.returncode, 0,
                         f"--render-only 產出失敗：{proc.stdout}{proc.stderr}")
        shutil.copy2(rendered, self.plist_path)

    def install_degenerate_plist(self) -> None:
        self.plist_path.write_text(_MACNIGHTLY_DEGENERATE_PLIST, encoding="utf-8")

    def write_heartbeat(self, fail_n: int = 0) -> None:
        (self.logs / "nightly_mac_latest.log").write_text(
            "nightly_mac heartbeat（UTC）：2026-08-01T02:00:00Z\n"
            f"===== nightly 彙總：PASS={7 - fail_n} FAIL={fail_n} =====\n",
            encoding="utf-8",
        )

    def write_runid_logs(self, days_ago: list[int]) -> None:
        """為指定的「幾天前」各造一份 RunId log（run_local_nightly.sh 每輪產一份）。"""
        today = datetime.date.today()
        for n in days_ago:
            stamp = (today - datetime.timedelta(days=n)).strftime("%Y%m%d")
            (self.logs / f"nightly_mac_{stamp}_020001.log").write_text(
                "run\n", encoding="utf-8")


class TestMacNightlyPlistCapabilityTable(MacNightlyStatusTestCase):
    """R67-M37：`--status` 必須檢查**已安裝 plist 的內容**，不只檢查它存在。"""

    def test_healthy_plist_passes_every_capability_row(self) -> None:
        """控制組：健康 plist ＋ 健康機器狀態 ⇒ 每列皆 ✅、且無「與期望不符」彙總行。

        沒有這一組，「退化 plist 會噴 ⚠️」只證明載具會叫，不證明它會分辨。

        🔴「健康」在本測試裡是**兩個自變數**：能力表大多數列讀 plist 檔案內容
        （`install_healthy_plist()` 全權控制），WakeToRun／NextRunTime 兩列讀
        `pmset -g sched` ＝**這台機器的電源排程狀態**。夾具的 pmset stub 把第二個
        自變數也收進測試手裡，兩列因此**留在**斷言內（沒被拿掉、沒被放寬成允許 ⚠️）。
        只設前者時本測試在真 mac 上為何結構性必紅、又為何在 Windows 上沒人看見，
        史料＝`docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`。
        """
        self.install_healthy_plist()
        self.write_heartbeat()
        proc = self.run_status()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("補跑保護能力", proc.stdout, "能力表整段缺席")
        self.assertIn("✅ RunAtLoad = true   (expected true)", proc.stdout)
        self.assertIn("✅ plist 內容與現行安裝器產出逐位元組一致（無漂移）", proc.stdout)
        self.assertIn("✅ WakeToRun 對等（pmset repeat 排程喚醒） = 已排定", proc.stdout,
                      f"已排定的 repeat wakeorpoweron 沒被判讀出來：{proc.stdout!r}")
        # 憑證是那個**值**，不是某個指令的 rc（根 CLAUDE.md 反「事後諸葛」取證規則）。
        # 只斷言「有」不斷言值，等於允許安裝器印一句「有」而不印時刻——那正是該規則在防的。
        self.assertIn("憑證值＝wakepoweron at 1:55AM every day", proc.stdout,
                      f"NextRunTime 對等列沒把前瞻憑證的**值**印出來：{proc.stdout!r}")
        self.assertNotIn("項與期望不符", proc.stdout,
                         f"健康 plist 不該有任何能力列告警：{proc.stdout!r}")

    def test_degenerate_plist_flags_every_broken_capability(self) -> None:
        """缺陷本體：R15 之前安裝、且 repo 搬過家的 plist——三個能力列都要 ⚠️。

        逐列斷言而非只看「有沒有出現 ⚠️」：三個缺陷各自獨立（缺鍵／載體不存在／
        log 落點錯），只驗總數會讓其中兩項悄悄失去守護。
        """
        self.install_degenerate_plist()
        self.write_heartbeat()
        out = self.run_status().stdout
        self.assertIn("⚠️ RunAtLoad = (缺席)   (expected true)", out,
                      f"缺 RunAtLoad（開機/載入補跑窗口）未被標記：{out!r}")
        self.assertIn("⚠️ ProgramArguments 載體可讀 = 否", out,
                      f"載體路徑指向不存在的檔案未被標記：{out!r}")
        self.assertIn("⚠️ StandardOutPath 位於 AutoClaude/logs = 否", out,
                      f"log 落點導 /tmp（會被 macOS 週期清理）未被標記：{out!r}")
        self.assertIn("⚠️ plist 內容已與現行安裝器產出漂移", out,
                      f"整檔漂移未被標記：{out!r}")
        self.assertRegex(
            out, r"⚠️ 上列 \d+ 項與期望不符",
            f"缺少「共 N 項不符」彙總行——逐列 ⚠️ 容易被大量輸出淹沒：{out!r}",
        )

    def test_missing_plist_skips_capability_table_without_crashing(self) -> None:
        """plist 不存在時不得對空檔跑 plutil（`set -euo pipefail` 下會炸掉整支
        --status，把 advisory 缺口升級成工具本身不可用）。"""
        self.write_heartbeat()
        proc = self.run_status()
        self.assertIn("plist：不存在", proc.stdout)
        self.assertNotIn("補跑保護能力", proc.stdout,
                         "plist 缺席時不該印能力表（無產物可查）")
        self.assertEqual(proc.stderr, "", f"不得有 stderr 噪音：{proc.stderr!r}")

    def test_status_prints_exactly_the_rows_static_extraction_predicts(self) -> None:
        """行為驗證（darwin-only）＋ 靜態抽取器的**現實對帳單**。

        跨平台對稱斷言（mac 列數 ≥ Windows 列數）住
        `test_schedule_capability_parity.py`（兩側只讀原始碼、不需要 Darwin）。
        留在這裡的是**只有 macOS 才做得到的那一半**，且刻意做成對帳而非重複斷言：
        真跑一次 `--status`，驗 ① 能力表整段印得出來、② 每一列 `(expected …)` 都是
        ✅（健康 plist 不該有任何告警）、③ **執行期列數逐一等於**靜態抽取器對同一支
        安裝器的預測。③ 才是關鍵——靜態抽取器是那道跨平台鎖的量測面，而量測面本身
        必須被驗證（若它多算/少算，跨平台鎖會在 mac 以外的所有平台默默失準，
        而沒有任何人有辦法發現）。② 同樣吃 plist 內容與 pmset 排程兩個自變數，
        夾具的 stub 已把後者收進測試手裡；③ 不受影響（它比的是列**數**）。
        搬遷前的原文＝`docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`。
        """
        static_rows = _cap_parity.mac_capability_rows(self.installer_source())
        self.install_healthy_plist()
        self.write_heartbeat()
        out = self.run_status().stdout
        self.assertIn("補跑保護能力", out, "能力表整段缺席")
        runtime_rows = re.findall(r".*\(expected .+?\).*", out)
        self.assertEqual(
            len(runtime_rows), len(static_rows),
            f"--status 執行期印出 {len(runtime_rows)} 個 (expected …) 能力列，但靜態抽取器"
            f"（test_schedule_capability_parity.mac_capability_rows，跨平台對稱鎖的量測面）"
            f"預測 {len(static_rows)} 個——量測面已與現實脫節，那道鎖在 mac 以外的平台"
            f"正在用一個錯的數字比對。執行期抓到：{runtime_rows}；"
            f"靜態抓到：{[r.label[:40] for r in static_rows]}",
        )
        self.assertTrue(
            all("⚠️" not in row for row in runtime_rows),
            f"健康 plist 的每一列能力都應為 ✅，實得：{runtime_rows}",
        )


class TestMacNightlyMachineStateCapabilities(MacNightlyStatusTestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestMacNightlyMachineStateCapabilities WHY〉節。"""

    def _cap_lines(self, out: str) -> str:
        """只取那兩列，避免斷言被其他列的文字誤命中。"""
        return "\n".join(
            line for line in out.splitlines()
            if "WakeToRun 對等" in line or "NextRunTime 對等" in line
        )

    def test_a_mac_with_no_power_schedule_at_all_flags_both_rows(self) -> None:
        """缺陷本體（也是修前那兩支紅的真正成因）：pmset 在、但一件排程都沒有。

        這是絕大多數 Mac 的**出廠常態**（本機實測 `pmset -g sched` rc=0、stdout 空），
        而 `pmset repeat` 需要 sudo、安裝器刻意不代跑 ⇒ 使用者裝完 launchd 之後
        本來就處於這個狀態。報表必須明白說出「未排定」並給出那句 sudo 指令，
        因為那正是他還沒做、而且只有他做得到的那一件事。
        """
        self.set_pmset(self.PMSET_NO_SCHEDULE)
        self.install_healthy_plist()
        self.write_heartbeat()
        proc = self.run_status()
        rows = self._cap_lines(proc.stdout)
        self.assertIn("⚠️ WakeToRun 對等（pmset repeat 排程喚醒） = 未排定", rows,
                      f"沒有任何電源排程卻沒被標記：{rows!r}")
        self.assertIn("⚠️ NextRunTime 對等（pmset -g sched 前瞻憑證） = 無", rows,
                      f"拿不到前瞻憑證卻沒被標記：{rows!r}")
        self.assertIn("sudo pmset repeat wakeorpoweron MTWRFSU", proc.stdout,
                      "只說「未排定」不給逐字可執行的指令＝等於沒給（該項需提權，"
                      f"腳本刻意不代跑）：{proc.stdout!r}")
        self.assertNotIn(
            "無 pmset", rows,
            "「沒有排程」被講成「沒有 pmset」——後者是假話（本機 command -v pmset ＝ "
            "/usr/bin/pmset），而且它指向一個假的成因：讀者會以為要去裝 pmset，"
            f"實際要做的是跑那句 sudo 指令。實得：{rows!r}",
        )
        self.assertEqual(proc.returncode, 0,
                         "本段是 advisory，不得改動 exit code")

    def test_a_machine_without_pmset_is_reported_distinctly(self) -> None:
        """「沒有 pmset」與「有 pmset 但沒排程」必須是兩句不同的話。

        兩者的下一步動作完全不同（換機器／裝工具 vs. 跑一句 sudo），把兩者摺成同一句
        就是把讀者導向錯誤的處置——修前的 `_pmset_sched` 正是把兩者都回成空字串。
        """
        self.remove_pmset()
        self.install_healthy_plist()
        self.write_heartbeat()
        proc = self.run_status()
        rows = self._cap_lines(proc.stdout)
        self.assertIn("⚠️ WakeToRun 對等（pmset repeat 排程喚醒） = 無 pmset", rows,
                      f"pmset 不存在時應如實說「無 pmset」：{rows!r}")
        self.assertIn("憑證值＝(無 pmset)", rows,
                      f"NextRunTime 對等列的憑證值欄應區分「查不了」與「查到沒有」：{rows!r}")
        self.assertEqual(proc.returncode, 0,
                         "本段是 advisory，不得改動 exit code")

    def test_a_one_shot_wake_event_does_not_count_as_the_daily_repeat(self) -> None:
        """假綠防線：一次性 wake 事件不得被算成「已排定」。

        macOS 自己就常年掛著 user-invisible 的一次性 wake（本機
        `plutil -p /Library/Preferences/SystemConfiguration/com.apple.AutoWake.plist`
        實查到 calaccessd／osanalytics 兩則）。修前的判準對 `pmset -g sched` **全文**
        做子字串比對 ⇒ 只要輸出裡出現那個字樣就算數，不分區段。一次性事件跑完就沒了，
        撐不起「每天 02:00 前把機器叫醒」這個語意；把它算成已排定，等於在唯一的每日
        回饋通道上宣告一個不存在的保護。

        🔴 本鎖的鑑別力射程（**複審實測訂正**，不是推論）：本測試此前自陳的鑑別力宣稱
        經複審實測證偽，本支保留的價值是情境覆蓋而非形態鑑別力（原文＝Guard_Repin
        證據檔 §D-17）；真正吃得下全文比對假綠的輸入已補成獨立一支
        （`test_a_one_shot_wakeorpoweron_is_not_mistaken_for_the_daily_repeat`）。

        🔴 仍然沒有測試在守的那一半（不變）：合成注入「只拿掉安裝器的區段錨定、保留
        tolower($1) 欄位判準」→ 全綠。因為一次性段的 $1 結構上恆為 `[N]`
        （樣板 ` [%ld]  %s at %s`），欄位判準單獨就排除了它。區段錨定是縱深防禦、
        目前無鎖——寫在這裡是因為「以為有鎖在守」比「知道沒有」更貴。
        """
        self.set_pmset(self.PMSET_ONESHOT_ONLY)
        self.install_healthy_plist()
        self.write_heartbeat()
        rows = self._cap_lines(self.run_status().stdout)
        self.assertIn("⚠️ WakeToRun 對等（pmset repeat 排程喚醒） = 未排定", rows,
                      f"一次性 wake 事件被誤判成每日重複喚醒（假綠）：{rows!r}")
        self.assertIn("⚠️ NextRunTime 對等（pmset -g sched 前瞻憑證） = 無", rows,
                      f"一次性事件被當成前瞻憑證（假綠）：{rows!r}")

    def test_a_one_shot_wakeorpoweron_is_not_mistaken_for_the_daily_repeat(self) -> None:
        """真正的假綠防線：一次性的 **wakeorpoweron** 不得被算成每日重複喚醒。

        為何非要獨立一支（上一支不是已經測過一次性事件了嗎）：上一支的 eventtype 是
        `wake`，**不是**詞彙表任何一項的子字串 ⇒ 連最爛的全文比對都不會在它身上出錯，
        它證不了任何形態上的鑑別力（複審實測：忠實還原全文比對 → 24 tests OK）。
        本支的輸入才會讓全文比對回報「已排定」，也就是修前那個判準真正的破口。

        情境是真的會發生的：`pmset schedule`（一次性）與 `pmset repeat`（重複）只差一個
        動詞，打錯就落在這一格。一次性事件跑完就沒了，撐不起「每天 02:00 前把機器叫醒」；
        把它算成已排定，等於在唯一的每日回饋通道上宣告一個不存在的保護——而使用者會
        因為看到 ✅ 而**停止**去做那件他其實還沒做的事。

        輸入不是編的（見 `PMSET_ONESHOT_WAKEORPOWERON` 上方的反組譯證據鏈）：一次性段
        會把 eventtype `wakepoweron` 代換成字面值 `wakeorpoweron` 再印，重複段則直印原值。
        """
        self.set_pmset(self.PMSET_ONESHOT_WAKEORPOWERON)
        self.install_healthy_plist()
        self.write_heartbeat()
        rows = self._cap_lines(self.run_status().stdout)
        self.assertIn(
            "⚠️ WakeToRun 對等（pmset repeat 排程喚醒） = 未排定", rows,
            "一次性的 wakeorpoweron 被誤判成每日重複喚醒（假綠）——這正是「對 -g sched "
            f"全文做子字串比對」那個舊形態會吃下去的輸入：{rows!r}",
        )
        self.assertIn("⚠️ NextRunTime 對等（pmset -g sched 前瞻憑證） = 無", rows,
                      f"一次性的 wakeorpoweron 被當成前瞻憑證（假綠）：{rows!r}")


class TestMacNightlyPmsetMarkerIsNotProse(unittest.TestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestMacNightlyPmsetMarkerIsNotProse WHY〉節。"""

    _INSTALLER = Path(dev_start.__file__).resolve().parents[1] / "tools" / "install_mac_nightly.sh"

    def test_the_installer_does_not_pin_a_prose_marker_that_pmset_never_prints(self) -> None:
        """R82 那個判準字面值不得回來：`pmset` 從不印「wake or poweron」
        （真 mac 實測數字，原文＝Guard_Repin 證據檔 §D-18）。

        本斷言與那幾支行為測試不是重複——行為測試用的是 stub 的輸出，
        stub 可以被改成配合任何字面值；這一支直接讀原始碼，釘的是
        「判準不得押一個 OS 不會產出的字串」這件事本身。

        🔴 判斷面刻意**剝掉註解行**（同 test_mac_readiness_r82.pmset_capability_rows
        的既有慣例）：訂正紀錄本來就得逐字寫出被撤回的那個字面值，否則下一位讀者
        無從知道當初錯在哪、也就會再錯一次。本判準要禁的是「拿它當判準／印給使用者
        去找」，不是「提到它」。第一版沒剝，於是它把本檔自己的訂正註解判成違規——
        那種鎖的下場是被人把註解刪掉來滿足它，等於用刪除歷史換綠燈。
        """
        code = "\n".join(
            line for line in self._INSTALLER.read_text(encoding="utf-8").splitlines()
            if not line.strip().startswith("#")
        )
        self.assertNotIn(
            "wake or poweron", code,
            "判準（或印給使用者的文案）又押回 `wake or poweron`——該字串在 pmset "
            "二進位裡不存在，比對恆不命中 ⇒ 排好了也永遠印 ⚠️（假紅）",
        )
        self.assertIn(
            "wakepoweron", code,
            "判準必須認得 `pmset repeat wakeorpoweron` 實際寫進 AutoWake.plist 的 "
            "eventtype 值 `wakepoweron`（那才是 `pmset -g sched` 會印出來的 token）",
        )

    def test_the_pmset_seam_exists_so_the_rows_are_not_read_off_the_host(self) -> None:
        """兩列的量測面必須可注入——否則「健康 ⇒ 每列皆 ✅」又會偷偷要求機器狀態。

        這一條同樣是平台中立的：它守的是安裝器**有沒有留那道縫**，而縫在不在
        是原始碼事實。修前它不在，代價是 `test_healthy_plist_passes_every_
        capability_row` 在真 mac 上結構性必紅（本輪合成注入實證：把
        `PMSET="${IMN_PMSET:-pmset}"` 改回寫死 `pmset`，該測試立刻轉紅）。
        """
        src = self._INSTALLER.read_text(encoding="utf-8")
        self.assertIn(
            'PMSET="${IMN_PMSET:-pmset}"', src,
            "IMN_PMSET 測試縫消失 ⇒ WakeToRun／NextRunTime 兩列的值又回去讀跑測試那台"
            "機器的真實電源排程；`pmset repeat` 需 sudo、安裝器刻意不代跑 ⇒ "
            "「健康 plist ⇒ 每列皆 ✅」在多數 Mac 上結構性必紅",
        )


class TestMacNightlyCoverageContinuity(MacNightlyStatusTestCase):
    """R67-F29：`--status` 必須看得見「中間漏跑」，不只看得見「最後一次多久前」。"""

    def test_gap_days_are_listed_by_date(self) -> None:
        """缺陷本體：心跳今天剛更新（補跑）＋前幾天整段空窗 → 必須逐日列出缺口。

        這就是本機 07-28/29/30 的實況：`✅ 心跳：新鮮（距今 0 天）` 與「三天沒跑」
        同時為真，而修前只看得到前者。
        """
        lookback = self.coverage_lookback_days()
        present = [1, lookback]                      # 只有最新與最舊兩天有跑
        missing = [n for n in range(1, lookback + 1) if n not in present]
        self.write_runid_logs(present)
        self.write_heartbeat()
        self.install_healthy_plist()
        out = self.run_status().stdout
        self.assertIn(
            f"⚠️ 覆蓋連續性：近 {lookback} 天有 {len(missing)} 天無 nightly 紀錄",
            out, f"連續性缺口未被偵測：{out!r}")
        self.assertIn("✅ 心跳：新鮮", out,
                      "本鎖的前提是「心跳新鮮」與「有缺口」同時成立——前提沒成立"
                      f"就不是在驗這個缺陷：{out!r}")
        today = datetime.date.today()
        for n in missing:
            stamp = (today - datetime.timedelta(days=n)).strftime("%Y%m%d")
            self.assertIn(stamp, out,
                          f"缺口日期 {stamp} 未列出（只給數量無法排查）：{out!r}")

    def test_continuous_coverage_reports_green(self) -> None:
        """控制組：近 N 天每日皆有 log → 綠，且不得誤報任何日期。

        含「今天不算缺口」這條語意：02:00 排程在當日凌晨前尚未觸發，把今天算進去
        會讓每天 00:00~02:00 之間必然多報一天假缺口。
        """
        lookback = self.coverage_lookback_days()
        self.write_runid_logs(list(range(1, lookback + 1)))
        self.write_heartbeat()
        self.install_healthy_plist()
        out = self.run_status().stdout
        self.assertIn(f"✅ 覆蓋連續性：近 {lookback} 天每日皆有 nightly 紀錄", out,
                      f"無缺口卻報告缺口（假陽性會讓整段報表被忽略）：{out!r}")
        self.assertNotIn("無 nightly 紀錄", out)

    def test_no_runid_logs_at_all_is_reported_distinctly(self) -> None:
        """一份 RunId log 都沒有時，語意是「排程尚未跑過第一輪」而非「近 N 天全缺」
        ——剛裝完的人不該收到一則像是排程壞掉的告警。"""
        self.write_heartbeat()
        self.install_healthy_plist()
        out = self.run_status().stdout
        self.assertIn("覆蓋連續性：無任何 RunId log", out, f"{out!r}")
        self.assertNotIn("天無 nightly 紀錄", out)


class TestMacNightlyStatusWiring(MacNightlyStatusTestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestMacNightlyStatusWiring WHY〉節。"""

    def test_cmd_status_invokes_both_reports(self) -> None:
        m = re.search(r"^cmd_status\(\) \{(.*?)^\}", self.installer_source(),
                      re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(m, "install_mac_nightly.sh 的 cmd_status() 錨點消失")
        body = m.group(1)
        for fn in ("report_heartbeat", "report_plist_capabilities", "report_coverage"):
            self.assertIn(
                fn, body,
                f"cmd_status() 沒有呼叫 {fn}()——該函式定義得再完整，--status 也不會"
                f"執行到它（R67 上一輪半套修改的實際失敗形態）。cmd_status body="
                f"{body!r}",
            )

    def test_advisory_findings_never_change_exit_code(self) -> None:
        """退化 plist ＋ 覆蓋缺口 ＋ FAIL>0 三者齊發，rc 仍須為 0。

        `--status` 的機械判準是「launchd 有沒有載入」（該檔檔頭明文），三段報表
        皆屬 advisory。把它們升級成硬閘會讓既有呼叫端（ONBOARDING §8 SOP、任何
        `&&` 串接）行為回歸——要改語意得先改檔頭契約與呼叫端，不能從報表偷渡。
        """
        self.install_degenerate_plist()
        self.write_heartbeat(fail_n=3)
        proc = self.run_status()
        self.assertIn("⚠️", proc.stdout, "前提不成立：本案應同時觸發多個 advisory 告警")
        self.assertEqual(
            proc.returncode, 0,
            f"advisory 報表不得改變 --status exit code（實得 rc={proc.returncode}）："
            f"{proc.stdout}",
        )

    def test_exit_code_still_tracks_launchd_loaded_state(self) -> None:
        """反向：launchd 未載入時仍須 rc=1——新增報表不得把唯一的硬判準沖淡。

        R68-M31 註記：硬判準自本輪起是「已載入 **且** plist 仍在磁碟上」兩項合取
        （見安裝器檔頭 Exit codes，該句自 R13 就這樣寫、實作到 R68 才兌現）。本測試
        鎖的是其中「已載入」那一項，plist 那一項由
        `TestMacNightlyStatusPersistenceGate` 鎖——兩者是同一條合取式的兩個 conjunct，
        不是重複。
        """
        self.launchctl.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
        os.chmod(self.launchctl, 0o755)
        self.install_healthy_plist()
        self.write_heartbeat()
        proc = self.run_status()
        self.assertIn("❌ launchd 未載入", proc.stdout)
        self.assertEqual(proc.returncode, 1,
                         f"launchd 未載入時 --status 必須 rc=1：{proc.stdout!r}")


class TestMacNightlyStatusPersistenceGate(MacNightlyStatusTestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestMacNightlyStatusPersistenceGate WHY〉節。"""

    def test_loaded_but_plist_absent_from_disk_is_a_hard_failure(self) -> None:
        # 預設 stub 已回報「已載入」；刻意不安裝 plist＝重現孤兒狀態。
        self.write_heartbeat()
        proc = self.run_status()
        self.assertIn("✅ launchd 已載入", proc.stdout,
                      f"前提不成立：本案必須是「已載入」才在驗孤兒狀態：{proc.stdout!r}")
        self.assertIn("plist：不存在", proc.stdout)
        self.assertEqual(
            proc.returncode, 1,
            "已載入但磁碟無 plist＝下次登入即失效的死排程，rc 必須為 1"
            f"（安裝器檔頭 Exit codes 逐字承諾「或 plist 缺席」）：{proc.stdout!r}",
        )
        self.assertIn(
            "下次登入/重開機不會再載入", proc.stdout,
            "只印一行「plist：不存在」會讓讀者以為只是少了份備份檔——必須說明"
            f"這個載入狀態不會存活：{proc.stdout!r}",
        )

    def test_header_contract_still_promises_plist_absence_is_failure(self) -> None:
        """散文契約 ↔ 實作互鎖：上一條 rc 判準的來源就是檔頭那句話。

        沒有這道鎖，日後若有人為了讓某個情境變綠而把檔頭那半句刪掉，實作跟著放寬
        也不會有任何訊號——契約與實作會再一次悄悄脫鉤（這正是本缺陷存活到 R68 的
        機制：散文寫了 5 輪，沒有任何機械出口在讀它）。
        """
        # 錨在 Exit codes 那一句本身，而不是裸 `assertIn("或 plist 缺席")`——後者
        # 會被檔頭別處**解釋這條契約的註解**餵飽（本輪雙向注入實測：把契約句改掉、
        # 註解裡的引述還在，裸 assertIn 照綠 rc=0），那就是一道無牙的鎖。
        self.assertRegex(
            self.installer_source(),
            r"Exit codes：[^\n]*1＝失敗（--status 時＝未載入\n#\s*或 plist 缺席）",
            "安裝器檔頭 Exit codes 契約不得移除「未載入或 plist 缺席」——"
            "它是 --status 硬判準第 2 個 conjunct 的唯一散文來源",
        )


class TestMacNightlyLastExitStatusColumn(MacNightlyStatusTestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestMacNightlyLastExitStatusColumn WHY〉節。"""

    def test_nonzero_last_exit_replaces_the_false_first_run_claim(self) -> None:
        self.set_launchctl(self.stub_list_reports("3"))
        self.install_healthy_plist()
        # 刻意不寫心跳、不寫 RunId log——那正是「每晚跑、每晚在寫心跳前就掛」的形狀。
        out = self.run_status().stdout
        self.assertIn(
            "⚠️ 上次退出碼 = 3   (expected 0)", out,
            "last exit status 必須逐項印出並標記（對齊 Windows Show-TaskDetail 的 "
            f"LastTaskResult 列，體例沿用 `(expected X)`）：{out!r}",
        )
        self.assertNotIn(
            "尚未跑過第一輪", out,
            "第 2 欄為非零＝排程已經跑過而且失敗了，「尚未跑過第一輪」是確定為假的"
            f"因果，必須整段被取代而不是加註後保留：{out!r}",
        )
        self.assertIn(
            "exit 3", out,
            f"缺席文案須指出真正的成因（載體以 exit 3 結束）：{out!r}")

    def test_zero_last_exit_keeps_the_first_run_wording(self) -> None:
        """控制組：第 2 欄為 0 時原本的「尚未跑過第一輪」是正確的，不得被誤殺。

        沒有這一組，「非零時不准說尚未首跑」可以靠把那句話整個刪掉來作弊。
        """
        self.set_launchctl(self.stub_list_reports("0"))
        self.install_healthy_plist()
        out = self.run_status().stdout
        self.assertIn("✅ 上次退出碼 = 0   (expected 0)", out, f"{out!r}")
        self.assertIn(
            "尚未跑過第一輪", out,
            f"剛裝完、尚未到 02:00 的機器不該被告知載體失敗過：{out!r}")


class TestMacNightlyLoadSelfVerification(MacNightlyStatusTestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestMacNightlyLoadSelfVerification WHY〉節。"""

    _LOAD_FAILS_SILENTLY = (
        'if [ "$1" = "load" ]; then echo "Load failed: 5: Input/output error" >&2; fi\n'
        "exit 0\n"
    )

    def test_install_fails_loud_when_load_silently_fails(self) -> None:
        self.set_launchctl(self._LOAD_FAILS_SILENTLY)
        proc = self.run_installer()
        self.assertNotEqual(
            proc.returncode, 0,
            "launchctl load 未生效時 install 必須非零退出——把 rc 當判準的自動化"
            f"會據此認定排程已就緒：{proc.stdout}{proc.stderr}",
        )
        self.assertNotIn(
            "已安裝並載入", proc.stdout,
            f"排程根本沒載入卻宣稱「已安裝並載入」：{proc.stdout!r}")
        self.assertIn("不在 launchctl list", proc.stderr,
                      f"失敗訊息須說明是「list 自證未通過」：{proc.stderr!r}")

    def test_install_declares_success_only_after_list_confirms(self) -> None:
        """控制組：list 自證通過時仍須正常成功——修法不得把 install 一律變成失敗。"""
        self.set_launchctl(self.stub_list_reports("0"))
        proc = self.run_installer()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("✅ 已安裝並載入", proc.stdout)
        self.assertTrue(self.plist_path.exists(), "plist 應已寫入 fake HOME")

    def test_install_points_at_launchctl_enable_when_label_is_disabled(self) -> None:
        """最易觸發的成因要給到復原指令：`launchctl unload -w` 是網路教學常見的
        「暫時停用」寫法，之後任何 load 都會靜默失敗直到 `launchctl enable`。"""
        self.set_launchctl(
            f"""if [ "$1" = "print-disabled" ]; then echo '"{self._LABEL}" => disabled'; fi
exit 0
""")
        proc = self.run_installer()
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn(
            f"launchctl enable gui/{os.getuid()}/{self._LABEL}", proc.stderr,
            f"命中 disabled 時須直接給出解除指令：{proc.stderr!r}")

    def test_uninstall_keeps_plist_when_unload_did_not_take_effect(self) -> None:
        """unload 亦恆 exit 0；若不自證就 `rm -f` plist，本工具會親手製造 R68-M31
        的孤兒狀態（仍載入、磁碟已無 plist ⇒ 之後連本工具都卸不掉它）。"""
        self.install_healthy_plist()
        self.set_launchctl(self.stub_list_reports("0"))
        proc = self.run_installer("--uninstall")
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue(
            self.plist_path.exists(),
            "unload 未生效時不得刪除 plist——刪了就是孤兒排程（R68-M31）")
        self.assertNotIn("已解除安裝", proc.stdout,
                         f"仍在 launchctl list 卻宣稱已解除安裝：{proc.stdout!r}")

    def test_uninstall_removes_plist_once_list_confirms_gone(self) -> None:
        """控制組：確實卸載後才刪 plist 並宣告成功。"""
        self.install_healthy_plist()
        self.set_launchctl("exit 0\n")
        proc = self.run_installer("--uninstall")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("✅ 已解除安裝", proc.stdout)
        self.assertFalse(self.plist_path.exists())


class TestCopyFunctionalInterpreterDllCopy(unittest.TestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestCopyFunctionalInterpreterDllCopy WHY〉節。"""

    def test_copies_named_dll_patterns_beside_dest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fake_src_dir = root / "fake_interpreter_dir"
            fake_src_dir.mkdir(parents=True)
            fake_exe = fake_src_dir / "python.exe"
            fake_exe.write_bytes(b"fake-interpreter-body")
            # 兩個應被複製的具名 pattern，加一個刻意排除的無關 DLL（驗證
            # 「具名 glob pattern，非裸 *.dll 全複製」——Architect 的必修要求）。
            (fake_src_dir / "python311.dll").write_bytes(b"dll-a")
            (fake_src_dir / "vcruntime140_1.dll").write_bytes(b"dll-b")
            (fake_src_dir / "sqlite3.dll").write_bytes(b"dll-should-not-copy")

            dest_dir = root / "dest_venv" / "Scripts"
            dest_dir.mkdir(parents=True)
            dest = dest_dir / "python.exe"

            with mock.patch.object(sys, "executable", str(fake_exe)):
                _copy_functional_interpreter(dest)

            self.assertTrue(dest.is_file(), "直譯器本體未被複製")
            self.assertEqual(dest.read_bytes(), b"fake-interpreter-body")
            self.assertTrue(
                (dest_dir / "python311.dll").is_file(),
                "python3*.dll 具名 pattern 應被複製到 dest 同層",
            )
            self.assertTrue(
                (dest_dir / "vcruntime140_1.dll").is_file(),
                "vcruntime140*.dll 具名 pattern 應被複製到 dest 同層",
            )
            self.assertFalse(
                (dest_dir / "sqlite3.dll").exists(),
                "不在具名 pattern 內的 DLL 不應被複製（避免誤複製 sqlite3/"
                "libssl/tcl-tk 等不必要的 DLL，增加 I/O 與被鎖檔風險）",
            )

    def test_no_dlls_present_is_a_safe_noop(self) -> None:
        """來源目錄沒有任何 .dll（macOS/Linux 上 sys.executable 同層的常態）
        時，函式不應丟例外、也不應多複製任何檔案——無條件 glob-and-copy 對
        此類環境天生就是 no-op，不需要任何 `if is_windows()` 平台分支（QA
        要求優先選擇的寫法：三平台行為天生一致）。
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fake_src_dir = root / "fake_interpreter_dir"
            fake_src_dir.mkdir(parents=True)
            fake_exe = fake_src_dir / "python"
            fake_exe.write_bytes(b"fake-interpreter-body")

            dest_dir = root / "dest_venv" / "bin"
            dest_dir.mkdir(parents=True)
            dest = dest_dir / "python"

            with mock.patch.object(sys, "executable", str(fake_exe)):
                _copy_functional_interpreter(dest)

            self.assertTrue(dest.is_file())
            self.assertEqual(
                sorted(p.name for p in dest_dir.iterdir()), ["python"],
                "無 DLL 來源時不應多出任何檔案",
            )


class TestRmtreeWindowsSafe(DevStartTestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestRmtreeWindowsSafe WHY〉節。"""

    def _make_readonly_fixture(self, root: Path) -> tuple[Path, Path]:
        venv = root / ".venv"
        (venv / "bin").mkdir(parents=True)
        f = venv / "bin" / "python"
        f.write_text("fake-binary", encoding="utf-8")
        os.chmod(f, stat.S_IREAD)
        return venv, f

    def test_removes_directory_with_readonly_file(self):
        """對照組（green）：修復後的 helper 能吃掉含唯讀檔的目錄並整個移除。

        Discriminating on Windows only —— POSIX 的 unlink 不看唯讀位元，該
        平台裸呼叫本就不失敗（誠實對齊 hub_sync.py 對應測試的用詞：POSIX 上
        green either way，鑑別力來自下面的 Windows-only 對照測試）。
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            venv, f = self._make_readonly_fixture(root)
            try:
                dev_start._rmtree_windows_safe(venv)
            finally:
                # 保底：斷言失敗時也別讓 TemporaryDirectory 清理被唯讀位元卡死。
                if f.exists():
                    os.chmod(f, stat.S_IWRITE)
            self.assertFalse(
                venv.exists(), "含唯讀檔的 .venv 應已被完整移除，而非留下半殘目錄")

    def test_bare_rmtree_would_have_raised_permission_error(self):
        """對照組（red）：證明本測試用的 fixture 真的會踩到雷——沒有這個對照，
        上面那個 green 測試無法排除「只是 fixture 沒踩到問題」的可能。
        Windows-only：POSIX 上裸呼叫本就不失敗（見上），略過此對照。
        """
        if os.name != "nt":
            self.skipTest(
                "[WINDOWS-NATIVE-ONLY] 裸 rmtree 遇唯讀檔的 PermissionError 只在 Windows "
                "重現（R67-F11 補標籤，供 run_root_unittests.py 彙整可見度）"
            )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            venv, f = self._make_readonly_fixture(root)
            try:
                with self.assertRaises(PermissionError):
                    shutil.rmtree(venv)
                self.assertTrue(venv.exists(), "PermissionError 後應留下半殘目錄（未整個刪除）")
            finally:
                os.chmod(f, stat.S_IWRITE)
                if venv.exists():
                    shutil.rmtree(venv)


class TestVenvSelfHealCallSitesUseSafeRmtree(DevStartTestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestVenvSelfHealCallSitesUseSafeRmtree WHY〉節。"""

    def test_ensure_venv_shape_routes_through_safe_rmtree(self):
        src = inspect.getsource(dev_start._ensure_venv_shape)
        self.assertIn(
            "_rmtree_windows_safe(", src,
            "_ensure_venv_shape() 不再透過 _rmtree_windows_safe() 刪除 — R66 P2 硬化被還原")
        self.assertNotIn(
            "shutil.rmtree(", src,
            "_ensure_venv_shape() 又直接呼叫 shutil.rmtree — Windows 唯讀檔會 "
            "PermissionError 且留下半殘目錄（R66 P2 迴歸）")

    def test_step_venv_routes_through_safe_rmtree(self):
        src = inspect.getsource(dev_start.step_venv)
        self.assertIn(
            "_rmtree_windows_safe(", src,
            "step_venv() 的跨 OS 清理不再透過 _rmtree_windows_safe() — R66 P2 硬化被還原")
        self.assertNotIn(
            "shutil.rmtree(", src,
            "step_venv() 又直接呼叫 shutil.rmtree — Windows 唯讀檔會 "
            "PermissionError 且留下半殘目錄（R66 P2 迴歸）")


class TestStaleScheduleTracks(unittest.TestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestStaleScheduleTracks WHY〉節。"""

    # 🔴 R71：本類別 4 支既有鎖新增 `_latest_attempt` 的 mock（`return_value=None`
    # ＝「該軸無訊號」）。這**不是**放寬既有斷言——每一條原斷言逐字保留，加 mock 的
    # 唯一理由是 `stale_schedule_tracks` 現在多問一個軸（D-2 最近一次嘗試），不 mock
    # 的話這些純邏輯單元測試會真的去打 `gh`（慢、要網路、離線即漂移）。`None` 是刻意
    # 選的值：它讓新軸完全不發言 ⇒ 原本的訊息文字與回傳形狀維持不變，原斷言的鑑別力
    # 一分未減。新軸自己的鑑別力由本類別下方新增的雙向鎖負責。
    #: `_latest_attempt` 的「該軸無訊號」mock 參數（`return_value=None`）。
    #: ⚠️ 不可寫成 `dict(new=None)`——那會把函式本身換成 `None`，呼叫時 TypeError。
    _NO_ATTEMPT = dict(return_value=None)

    def _root_with_cron(self, cron_lines: str) -> Path:
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        wf = root / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "demo.yml").write_text(
            "on:\n  schedule:\n" + cron_lines, encoding="utf-8")
        return root

    def test_daily_track_with_no_success_for_weeks_is_reported(self) -> None:
        """正向注入：日頻軌最近成功在 13 天前（> 1 天 × factor 2）⇒ 必須報陳舊。"""
        root = self._root_with_cron('    - cron: "12 6 * * *"\n')
        now = datetime.datetime(2026, 8, 2, tzinfo=datetime.UTC)
        with mock.patch.object(ci_liveness, "_latest_success_run",
                               return_value="2026-07-20T01:00:00Z"), \
             mock.patch.object(ci_liveness, "_latest_attempt", **self._NO_ATTEMPT):
            stale = ci_liveness.stale_schedule_tracks(root, time.monotonic() + 25, now=now)
        self.assertEqual(len(stale), 1, f"日頻軌 13 天沒成功卻零訊號：{stale}")
        self.assertIn("demo.yml", stale[0])

    def test_fresh_track_is_not_reported(self) -> None:
        """還原：同一軌昨天才成功 ⇒ 不得報（否則哨兵會天天狼來了而被忽略）。"""
        root = self._root_with_cron('    - cron: "12 6 * * *"\n')
        now = datetime.datetime(2026, 8, 2, tzinfo=datetime.UTC)
        with mock.patch.object(ci_liveness, "_latest_success_run",
                               return_value="2026-08-01T01:00:00Z"), \
             mock.patch.object(ci_liveness, "_latest_attempt", **self._NO_ATTEMPT):
            self.assertEqual(
                ci_liveness.stale_schedule_tracks(root, time.monotonic() + 25, now=now), [])

    def test_weekly_track_tolerates_one_skip(self) -> None:
        """週頻軌 13 天前成功仍在容忍內（7 × 2 = 14）——STALE_PERIOD_FACTOR 的存在理由。

        🔴 R71 保留本鎖的理由（D-5 的處置說明）：診斷把 `STALE_PERIOD_FACTOR=2.0`
        列為缺陷（週頻門檻 14 天 ⇒ 結構上不可能「當場發現」）。本輪**刻意不動這個
        常數**——它擋的是「單次 runner 排隊／額度抖動」造成的假紅，拿掉就回到天天
        狼來了、然後被忽略（那正是 DEF-101-703 的死法）。改以**新增判準**取得當場
        訊號：`_schedule_axis_note` 讓「cron 觸發後 run 轉紅」立刻出聲，不進容忍窗
        （見 `test_failed_scheduled_attempt_inside_tolerance_window_still_speaks`）。
        """
        root = self._root_with_cron('    - cron: "12 6 * * 1"\n')
        now = datetime.datetime(2026, 8, 2, tzinfo=datetime.UTC)
        with mock.patch.object(ci_liveness, "_latest_success_run",
                               return_value="2026-07-20T01:00:00Z"), \
             mock.patch.object(ci_liveness, "_latest_attempt", **self._NO_ATTEMPT):
            self.assertEqual(
                ci_liveness.stale_schedule_tracks(root, time.monotonic() + 25, now=now), [])

    def test_no_signal_is_not_reported_as_stale(self) -> None:
        """查不到（gh 失敗／逾時）一律跳過：無訊號 ≠ 壞訊號，否則離線就整排假紅。"""
        root = self._root_with_cron('    - cron: "12 6 * * *"\n')
        with mock.patch.object(ci_liveness, "_latest_success_run", return_value=None):
            self.assertEqual(
                ci_liveness.stale_schedule_tracks(root, time.monotonic() + 25), [])

    def test_never_succeeded_is_reported(self) -> None:
        """查得到但一次都沒成功過（空字串）⇒ 必須報——這正是 nightly-full 的實況。"""
        root = self._root_with_cron('    - cron: "12 6 * * *"\n')
        with mock.patch.object(ci_liveness, "_latest_success_run", return_value=""), \
             mock.patch.object(ci_liveness, "_latest_attempt", **self._NO_ATTEMPT):
            stale = ci_liveness.stale_schedule_tracks(root, time.monotonic() + 25)
        self.assertEqual(len(stale), 1)
        self.assertIn("查無任何成功", stale[0])

    def test_commented_out_cron_is_not_an_expected_track(self) -> None:
        """dormant 軌（整行被註解）不得被列為期望軌——否則刻意停用會變成永久假紅。"""
        root = self._root_with_cron('    # - cron: "12 6 * * *"\n')
        self.assertEqual(ci_liveness.scheduled_workflow_periods(root), {})

    def test_deadline_stops_the_scan(self) -> None:
        """預算耗盡即中止：advisory 哨兵寧可少報，不可拖住開工流程。

        🔴 R71 訂正（本鎖唯一被改動的既有斷言，理由寫在這裡）：原本第二條是
        `assertEqual(stale_schedule_tracks(...), [])`——也就是**把「沒查」與「查過、
        很健康」編碼成同一個回傳值**。那正是 E-2 的病：`_scan_order` 前身是固定
        字典序 ⇒ 預算截斷永遠砍掉排最後的 `windows-compat-ci.yml`（實測本 repo 7 軌
        排序後它就是最後一名），而呼叫端收到 `[]`、印「排程軌正常」。
        本鎖的**意圖**（不得對 probe 發動查詢、不得拖住開工）以 `assert_not_called()`
        逐字保留並仍是主判準；改掉的只是「截斷必須靜默」這個附帶結果——靜默本身是
        缺陷，不是要保護的行為。
        """
        root = self._root_with_cron('    - cron: "12 6 * * *"\n')
        with mock.patch.object(ci_liveness, "_latest_success_run",
                               return_value="") as probe:
            out = ci_liveness.stale_schedule_tracks(root, time.monotonic() - 1)
        probe.assert_not_called()
        self.assertEqual(len(out), 1, f"截斷必須留下自白，實得：{out}")
        self.assertIn("掃描未完成", out[0])
        self.assertIn("demo.yml", out[0],
                      "截斷自白未指名被丟掉的是哪一軌——不指名等於沒說")

    def test_multiple_crons_take_the_strictest(self) -> None:
        """同檔多條 cron 取最短週期（最嚴），否則週頻那條會稀釋掉日頻的判準。"""
        root = self._root_with_cron(
            '    - cron: "12 6 * * 1"\n    - cron: "12 7 * * *"\n')
        self.assertEqual(ci_liveness.scheduled_workflow_periods(root), {"demo.yml": 1.0})

    # ── R71 D-2：三種狀態必須可分辨（(a) 沒觸發／(b) 觸發但紅／(c) 還沒輪到）──

    def test_stale_message_says_cron_never_fired(self) -> None:
        """(a) 排程軌零 run ⇒ 訊息必須說「沒觸發」，不能只說「最近成功於 N 天前」。

        Rule 9：兩者的處置完全不同——「沒觸發」要去看帳務／workflow state，
        「觸發但紅」要去看那次 run。壓成同一句話的哨兵沒有診斷價值。
        """
        root = self._root_with_cron('    - cron: "12 6 * * *"\n')
        now = datetime.datetime(2026, 8, 2, tzinfo=datetime.UTC)
        with mock.patch.object(ci_liveness, "_latest_success_run",
                               return_value="2026-07-20T01:00:00Z"), \
             mock.patch.object(ci_liveness, "_latest_attempt", return_value={}):
            stale = ci_liveness.stale_schedule_tracks(root, time.monotonic() + 25, now=now)
        self.assertEqual(len(stale), 1)
        self.assertIn("從未產生過任何 run", stale[0], f"實得：{stale[0]!r}")

    def test_stale_message_carries_the_failing_attempt(self) -> None:
        """(b) 排程軌有觸發但紅 ⇒ 訊息必須帶結論與 url，人才點得進去看。"""
        root = self._root_with_cron('    - cron: "12 6 * * *"\n')
        now = datetime.datetime(2026, 8, 2, tzinfo=datetime.UTC)
        att = {"conclusion": "failure", "createdAt": "2026-07-27T10:06:01Z",
               "updatedAt": "2026-07-27T10:06:08Z",
               "url": "https://example.invalid/runs/30256689776"}
        with mock.patch.object(ci_liveness, "_latest_success_run",
                               return_value="2026-07-14T08:20:59Z"), \
             mock.patch.object(ci_liveness, "_latest_attempt", return_value=att):
            stale = ci_liveness.stale_schedule_tracks(root, time.monotonic() + 25, now=now)
        self.assertEqual(len(stale), 1)
        self.assertIn("failure", stale[0])
        self.assertIn("2026-07-27T10:06:01Z", stale[0])
        self.assertIn("30256689776", stale[0],
                      "訊息沒有 run url——「去看那次 run」是唯一處置，卻要人自己去翻")

    # ── R71 D-3：一次手動補跑不得買到整個容忍窗的靜默 ──────────────────────

    def test_dispatch_only_freshness_is_reported_even_though_verdict_is_fresh(self) -> None:
        """正向注入（今天正在真實發生的形態）：dispatch 成功「治好」了警告，
        但 schedule 軌本身最近一次觸發是紅的、且晚於那次成功 ⇒ 必須出聲。

        實證來源（2026-08-03 唯讀 gh 實查）：`aisdlc-sdd-arch-fitness.yml` 的
        schedule 軌最後成功 2026-07-14、最近一次 schedule run 2026-07-27 failure，
        而 08-02 14:24 有一次 workflow_dispatch 成功 ⇒ 主判準看起來新鮮。

        🔴 為何不是把 `workflow_dispatch` 移出 `_LIVENESS_EVENTS`：那樣做會讓
        DEF-101-703 的死鎖復發（哨兵印的處置指令產生的正是 dispatch run，不算數
        就永遠解不開）。dispatch 繼續計入主判準，遮蔽事實另立一句話。
        """
        root = self._root_with_cron('    - cron: "37 2 * * 1"\n')
        now = datetime.datetime(2026, 8, 3, tzinfo=datetime.UTC)
        att = {"conclusion": "failure", "createdAt": "2026-07-27T06:05:35Z",
               "updatedAt": "2026-07-27T06:05:44Z",
               "url": "https://example.invalid/runs/30241622957"}
        with mock.patch.object(ci_liveness, "_latest_success_run",
                               return_value="2026-08-02T14:24:23Z"), \
             mock.patch.object(ci_liveness, "_latest_attempt", return_value=att):
            out = ci_liveness.stale_schedule_tracks(root, time.monotonic() + 25, now=now)
        self.assertEqual(len(out), 1, f"dispatch 遮蔽未被偵測：{out}")
        self.assertIn("不是排程軌掙來的", out[0])
        self.assertIn("workflow_dispatch", out[0])

    def test_healthy_schedule_attempt_stays_silent(self) -> None:
        """還原（負控）：排程軌自己最近一次就是綠的 ⇒ 一個字都不准說。

        缺這支，上一支可以靠「永遠報遮蔽」通過＝零鑑別力。
        """
        root = self._root_with_cron('    - cron: "37 2 * * 1"\n')
        now = datetime.datetime(2026, 8, 3, tzinfo=datetime.UTC)
        att = {"conclusion": "success", "createdAt": "2026-08-03T02:37:00Z",
               "updatedAt": "2026-08-03T02:44:00Z", "url": "https://example.invalid/r/1"}
        with mock.patch.object(ci_liveness, "_latest_success_run",
                               return_value="2026-08-03T02:44:00Z"), \
             mock.patch.object(ci_liveness, "_latest_attempt", return_value=att):
            self.assertEqual(
                ci_liveness.stale_schedule_tracks(root, time.monotonic() + 25, now=now), [])

    def test_failed_scheduled_attempt_inside_tolerance_window_still_speaks(self) -> None:
        """D-5 的處置：週頻軌只過了 2 天（遠在 14 天容忍窗內），但最近一次排程觸發
        已經紅了 ⇒ **當場**出聲，不等 14 天。這就是「不動 STALE_PERIOD_FACTOR 也能
        當場發現」的機制；動常數會讓容忍一次跳過的設計失效，兩者不可混為一談。
        """
        root = self._root_with_cron('    - cron: "12 6 * * 1"\n')
        now = datetime.datetime(2026, 8, 3, tzinfo=datetime.UTC)
        att = {"conclusion": "failure", "createdAt": "2026-08-03T06:12:00Z",
               "updatedAt": "2026-08-03T06:12:09Z", "url": ""}
        with mock.patch.object(ci_liveness, "_latest_success_run",
                               return_value="2026-08-01T06:20:00Z"), \
             mock.patch.object(ci_liveness, "_latest_attempt", return_value=att):
            out = ci_liveness.stale_schedule_tracks(root, time.monotonic() + 25, now=now)
        self.assertEqual(len(out), 1, f"容忍窗內的排程紅燈被吃掉了：{out}")
        self.assertIn("failure", out[0])

    # ── R71 E-1：同檔多條 cron 驅動不相交 job 集合 ⇒ run 層結論不構成證據 ──

    def _root_with_workflow(self, body: str) -> Path:
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        wf = root / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "demo.yml").write_text(body, encoding="utf-8")
        return root

    _DISJOINT_WF = (
        "on:\n  schedule:\n"
        '    - cron: "7 2 * * 1"\n'
        '    - cron: "7 3 * * 1"\n'
        "jobs:\n"
        "  pg-e2e-nightly:\n"
        "    name: PG E2E - nightly\n"
        "    if: (github.event_name == 'schedule' && github.event.schedule == '7 2 * * 1')\n"
        "  mutation-tg:\n"
        "    name: Mutation Test - TokenGuardPlugin\n"
        "    if: (github.event_name == 'schedule' && github.event.schedule == '7 3 * * 1')\n"
    )

    def test_disjoint_cron_job_sets_are_reported_as_a_blind_spot(self) -> None:
        """正向注入：兩條 cron 各驅動不同 job ⇒ 必須自白 run 層判定不構成證據。

        WHY（Rule 9）：這不是風格問題。實證＝`autoclaude-ci.yml` 被採計為「最後
        一次成功」的 run 29308467958 裡 PG E2E／Perf Baseline 是 `skipped`、
        `steps=0`，而同日 `7 2` 那次（29306905483）Perf Baseline 是 `failure`、
        `steps=11`＝真實測試紅。run 層綠遮蔽了另一條軌的死亡。
        """
        root = self._root_with_workflow(self._DISJOINT_WF)
        blind = ci_liveness.multi_cron_blind_spot(root, "demo.yml")
        self.assertIsNotNone(blind, "不相交 job 集合未被判為盲區")
        self.assertIn("7 2 * * 1", blind)
        self.assertIn("PG E2E - nightly", blind)
        self.assertIn("Mutation Test - TokenGuardPlugin", blind)

    def test_same_job_set_across_crons_is_not_a_blind_spot(self) -> None:
        """還原（負控）：兩條 cron 驅動**同一組** job ⇒ run 層結論仍代表得了它們，
        不得誤報。缺這支，上一支可以靠「凡多 cron 必報」通過＝零鑑別力。

        🔴 本 fixture 的形狀是被鑑別力驗證逼出來的：第一版把 `7 3` 那個 job 的 `if:`
        改成 `7 2`，結果 `cron_job_map` 只剩**一個**鍵 ⇒ 走的是 `len(mapping) < 2`
        的早退，**根本沒碰到**要守的「同一組 job」判準。實測：把 `all(s == sets[0])`
        整條刪掉，那一版仍然全綠＝死鎖。現在兩個 job 的 `if:` 都同時列出兩條 cron，
        因此 map 有兩個鍵、兩鍵的 job 集合相同——這才真的走到那條判準上。
        """
        both = ("    if: (github.event_name == 'schedule' && "
                "(github.event.schedule == '7 2 * * 1' || "
                "github.event.schedule == '7 3 * * 1'))\n")
        body = re.sub(r"^    if: .*\n", both, self._DISJOINT_WF, flags=re.MULTILINE)
        root = self._root_with_workflow(body)
        mapping = ci_liveness.cron_job_map(root / ".github" / "workflows" / "demo.yml")
        self.assertEqual(
            len(mapping), 2,
            f"正控：fixture 必須產生兩個 cron 鍵，否則本鎖會走早退路徑而空轉：{mapping}")
        self.assertEqual(len(set(map(frozenset, mapping.values()))), 1,
                         f"正控：兩鍵的 job 集合必須相同：{mapping}")
        self.assertIsNone(ci_liveness.multi_cron_blind_spot(root, "demo.yml"))

    def test_single_cron_workflow_is_never_a_blind_spot(self) -> None:
        """還原：單條 cron 的檔 run 粒度＝軌粒度，永遠不該報（零噪音下限）。

        刻意用「有 job、且 job 真的綁在那條 cron 上」的檔，不是空殼——空殼的
        `cron_job_map` 回 `{}`，那樣把靜態抽取式打壞本鎖仍會綠（實測），零鑑別力。

        誠實劃界：本鎖擋得住的是「同一組 job 判準被拿掉」（拿掉後單鍵也會被報成
        盲區 ⇒ 本鎖轉紅，實測 rc=1）。它**擋不住**把 `len(mapping) < 2` 那道早退
        改寬——因為 `len==1` 時下面的同集合判準本來就會回 None，兩者是有意的冗餘，
        不是兩道獨立防線。不在此宣稱守得住它。
        """
        root = self._root_with_workflow(
            "on:\n  schedule:\n"
            '    - cron: "12 6 * * 1"\n'
            "jobs:\n"
            "  only-track:\n"
            "    name: Windows Nightly Full\n"
            "    if: (github.event_name == 'schedule' && "
            "github.event.schedule == '12 6 * * 1')\n")
        self.assertEqual(
            list(ci_liveness.cron_job_map(
                root / ".github" / "workflows" / "demo.yml")),
            ["12 6 * * 1"], "正控：靜態解析必須真的抓到那條 cron，否則下一句恆真")
        self.assertIsNone(ci_liveness.multi_cron_blind_spot(root, "demo.yml"))

    def test_real_repo_autoclaude_ci_is_the_live_specimen(self) -> None:
        """活體覆蓋：本 repo 現況必須真的命中一支（否則上面三支全是實驗室綠燈）。

        釘的是「偵測器對真實 repo 有輸出」，不是「恰好是這一支」——若哪天
        autoclaude-ci.yml 被拆成兩支 workflow（就是本盲區的治本解），本鎖會紅並
        提醒把這個活體標的改成當時真正存在的多 cron 檔，或刪掉本鎖。
        """
        repo = Path(__file__).resolve().parents[2]
        blind = ci_liveness.multi_cron_blind_spot(repo, "autoclaude-ci.yml")
        self.assertIsNotNone(
            blind,
            "autoclaude-ci.yml 不再是多 cron／不相交 job 形態——盲區可能已被治本"
            "（拆檔），請改指到當時真正存在的多 cron 檔或刪掉本鎖")
        self.assertIn("7 2 * * 1", blind)

    # ── R71 E-2：掃描預算截斷不得有固定順序偏差 ────────────────────────────

    def test_scan_order_rotates_so_the_last_track_is_not_always_the_same(self) -> None:
        """正向：連續日期的起掃點必須不同 ⇒ 沒有哪一軌永遠排最後、被永遠丟掉。

        修前形狀＝`sorted()` 直接迭代；實測本 repo 7 支含 cron workflow 排序後
        最後一名正是 `windows-compat-ci.yml`（DEF-101-703 的主角），也就是哨兵的
        系統性盲區恰好落在它最該看的那一支。
        """
        periods = {f"{c}.yml": 1.0 for c in "abcde"}
        firsts = {
            ci_liveness._scan_order(
                periods, datetime.datetime(2026, 8, d, tzinfo=datetime.UTC))[0][0]
            for d in range(1, 6)
        }
        self.assertEqual(
            len(firsts), 5,
            f"5 天內起掃點只出現 {len(firsts)} 種 ⇒ 輪轉沒生效，截斷仍有固定偏差：{firsts}")

    def test_scan_order_is_a_permutation_not_a_filter(self) -> None:
        """還原：輪轉不得吃掉任何一軌（否則「修好偏差」變成「直接漏軌」）。"""
        periods = {f"{c}.yml": 1.0 for c in "abcde"}
        for d in range(1, 8):
            order = ci_liveness._scan_order(
                periods, datetime.datetime(2026, 8, d, tzinfo=datetime.UTC))
            self.assertEqual(sorted(order), sorted(periods.items()),
                             f"第 {d} 天的掃描順序不是原集合的排列：{order}")


class TestLivenessEventFilter(unittest.TestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestLivenessEventFilter WHY〉節。"""

    @staticmethod
    def _run(stdout: str, rc: int = 0) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(args=["gh"], returncode=rc,
                                           stdout=stdout, stderr="")

    def test_workflow_dispatch_success_counts_as_liveness(self) -> None:
        """schedule 從未成功、但有人手動補跑成功 ⇒ 必須採計該 dispatch 時戳。"""
        by_event = {"schedule": self._run("[]"),
                    "workflow_dispatch": self._run(
                        json.dumps([{"updatedAt": "2026-08-01T20:00:00Z"}]))}
        with mock.patch.object(ci_liveness.subprocess, "run",
                               side_effect=lambda a, **k: by_event[a[a.index("--event") + 1]]):
            self.assertEqual(ci_liveness._latest_success_run("demo.yml"),
                             "2026-08-01T20:00:00Z",
                             "手動補跑（workflow_dispatch）的成功未被採計——"
                             "本哨兵印給人的處置指令產生的正是這種 run，"
                             "不採計＝處置指令與判準實證互斥、閘門永遠解不開")

    def test_newest_across_events_wins(self) -> None:
        """兩事件都有成功 ⇒ 取較新者（否則舊的那筆會把新的蓋掉、假報陳舊）。"""
        by_event = {
            "schedule": self._run(json.dumps([{"updatedAt": "2026-07-14T08:20:59Z"}])),
            "workflow_dispatch": self._run(json.dumps([{"updatedAt": "2026-08-01T20:00:00Z"}])),
        }
        with mock.patch.object(ci_liveness.subprocess, "run",
                               side_effect=lambda a, **k: by_event[a[a.index("--event") + 1]]):
            self.assertEqual(ci_liveness._latest_success_run("demo.yml"),
                             "2026-08-01T20:00:00Z")

    def test_all_events_query_failure_is_no_signal_not_stale(self) -> None:
        """每個事件都查失敗 ⇒ None（無訊號），不得回空字串被上層當成「從未成功」。"""
        with mock.patch.object(ci_liveness.subprocess, "run",
                               side_effect=OSError("gh 不存在")):
            self.assertIsNone(ci_liveness._latest_success_run("demo.yml"))

    def test_queried_ok_but_zero_runs_is_never_succeeded(self) -> None:
        """查得到但兩事件皆零筆 ⇒ 空字串（＝真的從未成功），與無訊號必須可區分。"""
        with mock.patch.object(ci_liveness.subprocess, "run",
                               return_value=self._run("[]")):
            self.assertEqual(ci_liveness._latest_success_run("demo.yml"), "")

    def test_every_liveness_event_is_actually_queried(self) -> None:
        """鑑別力鎖：把 `_LIVENESS_EVENTS` 縮回單一事件會讓上面兩支鎖失去意義，
        故直接釘住「宣告的每個事件都真的被送進 gh」——防止未來有人只改常數不改迴圈。
        """
        seen: list[str] = []

        def _spy(argv, **_kw):
            seen.append(argv[argv.index("--event") + 1])
            return self._run("[]")

        with mock.patch.object(ci_liveness.subprocess, "run", side_effect=_spy):
            ci_liveness._latest_success_run("demo.yml")
        self.assertEqual(seen, list(ci_liveness._LIVENESS_EVENTS))
        self.assertIn("workflow_dispatch", ci_liveness._LIVENESS_EVENTS,
                      "手動補跑事件被移出 _LIVENESS_EVENTS＝死鎖復發")


from _ps_engine import any_engine_available as _ps_any_engine  # noqa: E402
from _ps_engine import available_engines as _ps_available_engines  # noqa: E402
from _ps_engine import native_ps51 as _ps_native_51  # noqa: E402
from _ps_engine import production_engine as _ps_production_engine  # noqa: E402
from _ps_engine import windows_with_engine as _ps_windows_with_engine  # noqa: E402
from _ps_engine import windows_with_native_ps51 as _ps_windows_native_51  # noqa: E402

# R71 併檔：`sdd_latest` 供下方 DEF-101-762 那組鎖動態解析 LATEST 版 SDD 根。
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import sdd_latest  # noqa: E402

_GUARD_SH_PATH = Path(__file__).resolve().parents[1] / "lib" / "windowsapps_guard.sh"
_GUARD_PS1_PATH = Path(__file__).resolve().parents[1] / "lib" / "WindowsAppsGuard.ps1"
_DEV_START_SH_PATH = Path(__file__).resolve().parents[1] / "dev_start.sh"
_DEV_START_PS1_PATH = Path(__file__).resolve().parents[1] / "dev_start.ps1"

# R71（DEF-101-760）：PowerShell 寫進 pipe 的是 console output code page 不是 UTF-8，
# 修法＝每次呼叫自帶 UTF-8 前置（`_platform_helpers.PS_UTF8_PRELUDE`）。缺陷形狀與
# 訂正沿革原文＝Guard_Repin 證據檔 §D-1。

# 掃描面：三棵測試樹（比照 test_bash_probe_spec_contract._TEST_TREES——只守自己那棵
# 等於留著下一次分歧）。AISDLC_SDD 側也有兩處行內複本，故不可只掃 tools/tests。
_PS_UTF8_TEST_TREES = ("tools/tests", "AISDLC_SDD/scripts/tests", "AutoClaude/tests")
_PS_UTF8_SCAN_ROOT = Path(__file__).resolve().parents[2]
# 「這串字在講主控台輸出編碼」的辨識鍵，與「唯一合法寫法」的完整賦值式。兩者都從
# SSOT 常數**推導**、不另寫字面值——寫成字面值會讓本檔自己被下面的掃描器命中。
_PS_UTF8_MARKER = PS_UTF8_PRELUDE.split("=", 1)[0]
_PS_UTF8_STATEMENT = PS_UTF8_PRELUDE.strip().rstrip(";")
# 「這串字在指涉 UTF-8」的辨識鍵；`65001` 是以碼頁號指涉的形態，漏掉它會讓
# `…OutputEncoding = [Text.Encoding]::GetEncoding(65001)` 這種分歧寫法從判準下溜走。
# WHY 判準要多這一關見 `_names_utf8()`。
_PS_UTF8_ALIASES = ("utf8", "utf-8", "65001")
# 豁免標記（拼法與語意比照 `test_ps51_compat` 的 `# ps7-ok: <WHY>`）：WHY 必填、留空
# 無豁免力；標記所在行若沒壓下任何命中即 stale ⇒ fail-loud，防豁免清單腐化。
# 只認**真正的註解 token**（走 `tokenize`），字串裡出現同形字樣不算——否則本行自己
# 就會被當成一個到處亂罩的豁免。
_PS_UTF8_OK_MARKER = "ps-utf8-quote-ok:"
# 0 命中假綠防線（同 test_bash_probe_spec_contract._MIN_SCANNED_FILES 慣例）。
# R71 實測命中 5 處（1 個 SSOT 常數 + 4 個尚未收斂的行內複本）。刻意設 3 而非 5：
# 本數字的用途只是「掃描面塌成 0 ⇒ 斷言恆真」的防線，不是站點數快照——之後把行內
# 複本收斂掉會讓命中數合法下降，不該因此翻紅。
_MIN_PS_UTF8_SITES = 3

# unittest 斷言／skip 述詞的「訊息參數」位置；其餘形態一律靠 `msg=`／`reason=` 具名。
# 表只列本 repo 實際用到的斷言，**漏列往嚴格方向倒**——沒列到的斷言，其訊息會被當成
# 一份複本而翻紅（吵、當場看得見），不會讓真複本靜默溜過去（漏抓、看不見）。
_ASSERT_MSG_POS = {
    "assertTrue": 1, "assertFalse": 1, "assertIsNone": 1, "assertIsNotNone": 1,
    "fail": 0,
    "assertEqual": 2, "assertNotEqual": 2, "assertIn": 2, "assertNotIn": 2,
    "assertIs": 2, "assertIsNot": 2, "assertIsInstance": 2, "assertCountEqual": 2,
    "assertGreater": 2, "assertGreaterEqual": 2, "assertLess": 2, "assertLessEqual": 2,
    "assertRegex": 2, "assertNotRegex": 2, "assertAlmostEqual": 2,
}
_SKIP_MSG_POS = {"skipUnless": 1, "skipIf": 1, "skip": 0, "skipTest": 0}
_MSG_KEYWORDS = ("msg", "reason")


def _names_utf8(text: str) -> bool:
    """這串字是否在指涉 UTF-8（含以碼頁號 65001 指涉）。

    WHY 判準要多這一關（R71／DEF-101-762 併檔）：`_PS_UTF8_MARKER` 只認得「有人在動
    主控台輸出編碼」，但本鎖守的是 **UTF-8 前置的拼法**。把編碼**刻意設成別的東西**
    （例如為了重現只在 CP950 才顯形的缺陷而 `GetEncoding(950)`）、或把先前存下的值
    **還原**回去（`= $prevEnc`），都不是 UTF-8 前置的第 N 種拼法——它們是重現危害與
    收拾現場的必要動作，判成分歧只會逼作者刪掉那段程式碼，與 docstring 自噬同型。
    鑑別力不因此下降：任何真的「把輸出編碼設成 UTF-8」的寫法都必須指名 UTF-8
    （`[System.Text.Encoding]::UTF8`／`New-Object System.Text.UTF8Encoding`／
    `GetEncoding(65001)`／`GetEncoding('utf-8')`），三個別名把這些形態全涵蓋。
    """
    low = text.lower()
    return any(alias in low for alias in _PS_UTF8_ALIASES)


def _call_name(node: ast.Call) -> str:
    """取呼叫的尾端名字（`self.assertIn` → `assertIn`；`unittest.skipUnless` → 同理）。"""
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def _narrative_node_ids(tree: ast.AST) -> set[int]:
    """回傳「敘述用字串」的 Constant 節點 id：docstring、斷言訊息、skip reason。

    三者的共同性質是**不會被當成 PowerShell 送出去執行**——它們在講解與指路。

    🔴 R71 為何要把 docstring 這一層擴出去（不是為了消紅，是兩道鎖真的互斥）：
    `DEF-101-762` 的鎖必須**逐字引述**生產碼的拼法才斷言得了它，而本鎖規定測試樹內
    唯一合法拼法是 SSOT 那一串。該組鎖併進本檔時，它「解釋 CP950 下會發生什麼事」的
    斷言訊息與 skip reason 全被判成分歧拼法（實測 8 筆命中、其他檔 0 筆）。把講解算成
    複本，作者唯一的消紅路徑是刪掉講解——鎖因此反過來消滅自己存在的理由，與本檔
    `TestPsUtf8PreludeIsSingleSpelling` docstring 記載的自噬是同一形狀，只是換了位置。
    真正需要「引述可執行拼法」的那一處另走具名豁免（`_PS_UTF8_OK_MARKER`），不走本層。
    """
    ids: set[int] = set()

    def _absorb(expr: ast.AST) -> None:
        for sub in ast.walk(expr):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                ids.add(id(sub))

    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            body = getattr(node, "body", None)
            first = body[0] if body else None
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                if isinstance(first.value.value, str):
                    ids.add(id(first.value))
        elif isinstance(node, ast.Call):
            name = _call_name(node)
            if name not in _ASSERT_MSG_POS and name not in _SKIP_MSG_POS:
                continue
            pos = _ASSERT_MSG_POS.get(name, _SKIP_MSG_POS.get(name))
            if pos is not None and len(node.args) > pos:
                _absorb(node.args[pos])
            for kw in node.keywords:
                if kw.arg in _MSG_KEYWORDS:
                    _absorb(kw.value)
    return ids


def _waiver_comment_lines(source: str) -> dict[int, str]:
    """行號 → 該行註解裡的豁免 WHY（WHY 留空即空字串）。

    走 `tokenize` 只認 COMMENT token：字串字面值裡出現同形字樣不算豁免，否則
    `_PS_UTF8_OK_MARKER` 的宣告行自己就會變成一個罩住該行的豁免。
    """
    out: dict[int, str] = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.COMMENT and _PS_UTF8_OK_MARKER in tok.string:
                out[tok.start[0]] = tok.string.split(_PS_UTF8_OK_MARKER, 1)[1].strip()
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # 走到這裡代表檔案 tokenize 不了，而 `ast.parse()` 在同一支檔上卻成功——
        # 不吞掉：回空表 ⇒ 既有豁免全部失效 ⇒ 命中照樣紅（往嚴格方向倒）。
        return {}
    return out


def scan_ps_utf8_source(source: str, rel: str) -> tuple[int, list[tuple[int, str]], list[str]]:
    """純函式核心（供直接單元測試）：回傳 `(站點數, 分歧命中, stale 豁免)`。

    · 站點＝該檔設定主控台輸出編碼的**可執行**字串字面值（含合法寫法，供下限釘選用）。
    · 分歧命中＝站點中「指涉 UTF-8、卻沒有逐字使用 SSOT 寫法、也沒有具名豁免」的那些。
    · stale＝豁免標記在、卻沒壓下任何命中（含 WHY 留空）——豁免清單腐化的 fail-loud。
    三者同一次 AST parse 取得（分成多支公開函式會讓每支檔案被 parse 多遍，掃描面
    500+ 檔時是白花數倍時間）；`tokenize` 只在檔內真的出現標記字樣時才跑。
    """
    tree = ast.parse(source)
    waivers = _waiver_comment_lines(source) if _PS_UTF8_OK_MARKER in source else {}
    used: set[int] = set()
    skip = _narrative_node_ids(tree)
    sites = 0
    bad: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if id(node) in skip or _PS_UTF8_MARKER not in node.value:
            continue
        sites += 1
        if _PS_UTF8_STATEMENT in node.value or not _names_utf8(node.value):
            continue
        # 豁免標記須落在**這個字串字面值自己的行段內**（單行字串＝同一行，嚴格；三引號
        # 字串沒有「行尾」可掛註解，收尾那行的 `"""` 之後就是它唯一的掛點）。放寬成
        # 「附近幾行」會讓一個標記無聲地罩住上下文，那正是豁免腐化的起點。
        span = range(node.lineno, (node.end_lineno or node.lineno) + 1)
        hit = next((n for n in span if waivers.get(n)), None)
        if hit is not None:
            used.add(hit)
            continue
        head = node.value[: node.value.find(_PS_UTF8_MARKER) + 90].replace("\n", "\\n")
        bad.append((node.lineno, head))
    stale = [
        f"{rel}:{n}：豁免標記 stale（WHY 留空，或該行沒有被壓下的分歧命中）"
        for n in sorted(set(waivers) - used)
    ]
    return sites, bad, stale


def scan_ps_utf8_prelude(path: Path) -> tuple[int, list[tuple[int, str]], list[str]]:
    """`scan_ps_utf8_source` 的讀檔外殼（掃描面走磁碟，純函式核心供注入測試）。"""
    return scan_ps_utf8_source(path.read_text(encoding="utf-8"), path.name)


class TestPsUtf8PreludeIsSingleSpelling(unittest.TestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestPsUtf8PreludeIsSingleSpelling WHY〉節。"""

    def _scan(self) -> tuple[int, int, dict[str, list[tuple[int, str]]], list[str]]:
        scanned = sites = 0
        found: dict[str, list[tuple[int, str]]] = {}
        stale: list[str] = []
        for tree_rel in _PS_UTF8_TEST_TREES:
            root = _PS_UTF8_SCAN_ROOT / tree_rel
            self.assertTrue(root.is_dir(), f"掃描面 {tree_rel} 不存在——目錄已搬移，請同步本鎖")
            for path in sorted(root.rglob("*.py")):
                if "__pycache__" in path.parts:
                    continue
                scanned += 1
                # `.as_posix()`：鍵會被印進失敗訊息，`str()` 在 Windows 上是
                # 反斜線形態，與其他鎖的正斜線比對慣例不一致。
                rel = path.relative_to(_PS_UTF8_SCAN_ROOT).as_posix()
                found_here, bad, stale_here = scan_ps_utf8_prelude(path)
                sites += found_here
                stale.extend(s.replace(f"{path.name}:", f"{rel}:", 1) for s in stale_here)
                if bad:
                    found[rel] = bad
        return scanned, sites, found, stale

    def test_scan_surface_is_not_silently_empty(self) -> None:
        """下限釘選：一個站點都掃不到時，本體斷言會假綠。"""
        scanned, sites, _, _ = self._scan()
        self.assertGreater(scanned, 100, f"只掃到 {scanned} 支 .py——掃描面已塌，本鎖失效")
        self.assertGreaterEqual(
            sites, _MIN_PS_UTF8_SITES,
            f"只找到 {sites} 個輸出編碼前置站點（下限 {_MIN_PS_UTF8_SITES}）——"
            "辨識鍵已對不上任何真實程式碼，本鎖形同虛設",
        )

    def test_no_divergent_spelling(self) -> None:
        _, _, found, _ = self._scan()
        detail = "\n".join(
            f"  {rel}:{ln}  {frag}" for rel, hits in found.items() for ln, frag in hits
        )
        self.assertEqual(
            found, {},
            "出現與 SSOT 不同的主控台輸出編碼前置寫法（R71 C-2 的復發形態）。\n"
            f"唯一合法寫法＝`_platform_helpers.PS_UTF8_PRELUDE`：{PS_UTF8_PRELUDE!r}\n"
            "呼叫端請改用 `_platform_helpers.ps_utf8_command(snippet)`；真有理由行內寫，"
            "也必須逐字使用同一串（不同寫法＝多一份會獨立漂移的修復）。\n"
            "若那一串是**對生產碼的逐字引述**（改寫即失去斷言對象），於該行加註"
            "具名豁免（WHY 必填）。\n"
            f"命中：\n{detail}",
        )

    def test_no_stale_waivers(self) -> None:
        """豁免清單不得腐化：標記還在、卻沒壓下任何分歧命中（含 WHY 留空）即紅。

        Rule 9：沒有這一支，具名豁免就是單向閥——加得進、退不出場。R60 已實證過
        `_PENDING_MIGRATION_SITES` 那種「自陳遷移完成後刪除」卻永遠留著的豁免。
        """
        _, _, _, stale = self._scan()
        self.assertEqual(
            stale, [],
            "主控台輸出編碼前置的豁免標記已 stale——請移除標記或補 WHY：\n  "
            + "\n  ".join(stale),
        )

    def test_scanner_classifies_each_category_by_construction(self) -> None:
        """鑑別力自檢（同 `test_ps51_compat::test_scan_source_detects_each_pattern` 慣例）。

        Rule 9：上面兩支在乾淨的樹上恆綠，本身證明不了新加的三層過濾（敘述字串／
        非 UTF-8 的編碼操作／具名豁免）沒有把判準放寬到失去鑑別力。本支以構造輸入
        逐類斷言分類結果——把任一層改成無條件放行，這裡當場紅。
        """
        # 🔴 樣本一律由 `_PS_UTF8_MARKER` **拼出來**、不寫字面值：本檔自己也在掃描面內，
        # 寫成字面值會讓這些樣本被上面兩支鎖當成真命中（同本檔 `_PS_UTF8_MARKER` 宣告
        # 上方那條理由，只是這次踩點在測試資料上）。
        def _ps(rhs: str) -> str:
            return f'"{_PS_UTF8_MARKER} = {rhs}"'

        div = _ps("New-Object System.Text.UTF8Encoding($false)")
        cases = {
            # ① 真分歧：可執行位置、指涉 UTF-8、非 SSOT 寫法 ⇒ 必抓
            "divergent": (f"run({div})\n", 1, 0),
            # ② SSOT 逐字寫法 ⇒ 算站點但不算分歧
            "ssot": (f"run({PS_UTF8_PRELUDE!r})\n", 0, 0),
            # ③ 敘述：斷言訊息／skip reason ⇒ 不是複本
            "assert_msg": (f"self.assertIn(x, y, {div})\n", 0, 0),
            "skip_reason": (f"unittest.skipUnless(c, {div})\n", 0, 0),
            # ④ 刻意設成**非** UTF-8／還原先前值 ⇒ 不是 UTF-8 前置的第 N 種拼法
            "other_codepage": (
                f'run({_ps("[System.Text.Encoding]::GetEncoding(950)")})\n', 0, 0),
            "restore": (f'run({_ps("$prev")})\n', 0, 0),
            # ⑤ 以碼頁號指涉 UTF-8 的分歧寫法（別名表漏掉 65001 就會從這裡溜走）
            "by_codepage": (
                f'run({_ps("[System.Text.Encoding]::GetEncoding(65001)")})\n', 1, 0),
            # ⑥ 具名豁免：帶 WHY 壓下命中；WHY 留空無豁免力且回報 stale
            "waived": (f"run({div})  # {_PS_UTF8_OK_MARKER} 引述生產碼\n", 0, 0),
            "waiver_empty_why": (f"run({div})  # {_PS_UTF8_OK_MARKER}\n", 1, 1),
            # ⑦ 標記在、該行卻沒有被壓下的命中 ⇒ stale
            "waiver_stale": (f"run('noop')  # {_PS_UTF8_OK_MARKER} 已無命中\n", 0, 1),
        }
        got = {
            label: scan_ps_utf8_source(src, f"{label}.py")[1:]
            for label, (src, _, _) in cases.items()
        }
        want = {label: (n_bad, n_stale) for label, (_, n_bad, n_stale) in cases.items()}
        self.assertEqual(
            {label: (len(bad), len(stale)) for label, (bad, stale) in got.items()}, want,
            f"掃描器的分類與構造預期不符（實際：{got}）",
        )


# 兩側「>= _MIN_PY 版本探測碼」的字面值抽取式（單引號宣告＝兩側現行形態；單引號
# 是刻意的：bash 與 PowerShell 的單引號都不做內插，探測碼可原封不動送給 python）。
# 抽取式本身失配時由 `test_probe_extraction_regexes_still_match` 出聲。
_SH_PROBE_RE = re.compile(r"^PYTHON_GE_MIN_PROBE='(?P<probe>[^']*)'[ \t]*$", re.MULTILINE)
_PS1_PROBE_RE = re.compile(
    r"^\$script:PythonGeMinProbe = '(?P<probe>[^']*)'[ \t]*$", re.MULTILINE
)


# 假「系統 3.9」直譯器：轉呼叫**真**直譯器，但先把 `sys.version_info` 改寫成
# 3.9.6，其餘行為（`-c` 探測／跑 script）逐字照舊。
# WHY 不直接用 `/usr/bin/python3`：那是 macOS 專屬路徑，Linux/Windows runner 上
# 不一定存在「一支剛好 < 3.11 的直譯器」，測試會因環境而非因缺陷變色；本 shim
# 讓「PATH 第一順位是 3.9」這個情境在三平台皆可構造。
_FAKE_39_SHIM = """#!/bin/sh
exec "{real}" -c '
import os, sys, runpy
sys.version_info = (3, 9, 6, "final", 0)
args = sys.argv[1:]
if args and args[0] == "-c":
    code = args[1]
    sys.argv = ["-c"] + args[2:]
    exec(code)
elif args:
    sys.argv = args
    # 對齊 CPython 跑 script 時 sys.path[0]＝script 所在目錄（runpy 不會自己補），
    # 否則 dev_start.py 的 `import _stdio_utf8` 會因 shim 而非因缺陷失敗
    sys.path.insert(0, os.path.dirname(os.path.abspath(args[0])))
    runpy.run_path(args[0], run_name="__main__")
' "$@"
"""


@unittest.skipIf(usable_bash_for_fixture() is None, "需要可用的 bash")
class TestPickPythonGeMin(unittest.TestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestPickPythonGeMin WHY〉節。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(_rmtree_force, self.tmp)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()

    def _write_fake_39(self, name: str) -> Path:
        path = self.bin / name
        path.write_text(_FAKE_39_SHIM.format(real=sys.executable), encoding="utf-8")
        path.chmod(0o755)
        return path

    def _write_real_311(self, name: str) -> Path:
        """把跑測試的直譯器（依模組頂端版本閘，必 >= 3.11）以指定名字曝露到 PATH。"""
        path = self.bin / name
        path.write_text(
            f'#!/bin/sh\nexec "{sys.executable}" "$@"\n', encoding="utf-8"
        )
        path.chmod(0o755)
        return path

    def _bash(self, snippet: str, path_env: str, extra_env: dict | None = None):
        env = {
            "PATH": path_env,
            "HOME": str(self.tmp / "nohome"),
            "LC_ALL": "C.UTF-8",
            "PYTHONIOENCODING": "utf-8",
        }
        env.update(extra_env or {})
        # bash 用絕對路徑呼叫：`path_env` 刻意可以只有 fixture 目錄（構造「機器上
        # 一支 >= 3.11 都沒有」），此時用裸名 'bash' 會連 shell 都找不到。
        # R69 後續（DEF-101-753）：解析改走 `usable_bash_for_fixture()`——原本的
        # `shutil.which("bash")` 只看 PATH 順序、無 System32 段排除，在「WSL 佔位版
        # 排在 Git Bash 之前」的 Windows 開發機（DEF-101-617 已記載該機型）會回 WSL
        # 啟動器，本組於是拿到與受測邏輯無關的 rc。
        return subprocess.run(
            [usable_bash_for_fixture(), "-c", snippet], capture_output=True, encoding="utf-8",
            errors="replace", env=env, timeout=120,
        )

    def test_picks_311_when_path_python3_is_39(self) -> None:
        """PATH 上 `python3` 是 3.9、另有 `python3.11` ⇒ 必須選中 3.11。

        候選順序刻意反著餵（`python3` 排第一），確保通過的理由是「版本判斷」
        而非「剛好順序在前」——修復前的實作正是「命中即用、不看版本」。
        """
        self._write_fake_39("python3")
        self._write_real_311("python3.11")
        r = self._bash(
            f'. "{_GUARD_SH_PATH}"\n'
            "PYTHON_GE_MIN_CANDIDATES=(python3 python3.11)\n"

            "pick_python_ge_min\n",
            path_env=f"{self.bin}:/usr/bin:/bin",
        )
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr}")
        picked = r.stdout.strip()
        self.assertTrue(picked, "pick_python_ge_min 什麼都沒印")
        mm = subprocess.run(
            [picked, "-c", "import sys;print('%d.%d' % sys.version_info[:2])"],
            capture_output=True, encoding="utf-8", errors="replace", timeout=60,
        ).stdout.strip()
        self.assertGreaterEqual(
            tuple(int(x) for x in mm.split(".")), (3, 11),
            f"選中的直譯器是 {mm}（{picked}）——候選鏈仍在撿 < 3.11 的直譯器",
        )

    def test_fails_loud_with_actionable_commands_when_no_311(self) -> None:
        """完全沒有 >= 3.11 ⇒ rc=1 且訊息含**逐字可執行**的補救指令。

        「請安裝 Python 3.11」這種要使用者自己翻文件的句子不算補救——本鎖要求
        訊息裡真的有可以複製貼上就跑的指令（mac 的 brew / Linux 的套件管理器）。
        """
        self._write_fake_39("python3")
        r = self._bash(
            f'. "{_GUARD_SH_PATH}"\n'
            "PYTHON_GE_MIN_CANDIDATES=(python3)\n"

            "pick_python_ge_min && echo PICKED\n"
            'echo "rc=$?"\n'
            "python_ge_min_remediation\n",
            path_env=f"{self.bin}",
        )
        self.assertNotIn("PICKED", r.stdout)
        self.assertIn("rc=1", r.stdout)
        combined = r.stdout + r.stderr
        self.assertIn("❌", combined)
        for cmd in ("brew install python@3.11", "apt-get install -y python3.11"):
            self.assertIn(cmd, combined, f"補救訊息缺少可執行指令：{cmd}")

    def test_dev_start_sh_end_to_end_picks_311_over_path_python3(self) -> None:
        """端到端（真的跑 tools/dev_start.sh）：PATH 第一順位是 3.9 仍須 rc=0。

        修復前這裡必然 rc=2（`tools/dev_start.py` 版本前置閘）——這正是複審在
        macOS 真機上重現的入門路徑斷點。`--help` 讓核心在 argparse 就結束，不
        觸發 git/venv 等副作用，但版本閘在 import 期就會擋，鑑別力不受影響。
        """
        self._write_fake_39("python3")
        self._write_fake_39("python")
        self._write_real_311("python3.11")
        r = self._bash(
            f'bash "{_DEV_START_SH_PATH}" --help\n',
            path_env=f"{self.bin}:/usr/bin:/bin",
        )
        self.assertEqual(
            r.returncode, 0,
            f"dev_start.sh rc={r.returncode}（修復前為 2）\nstdout={r.stdout}\nstderr={r.stderr}",
        )
        self.assertIn("usage: dev_start.py", r.stdout)

    @unittest.skipIf(
        shutil.which("zsh") is None,
        "[MAC-NATIVE-ONLY] 需要 zsh——本鎖驗的是 **macOS 預設 shell** 的字詞切分語意"
        "（SH_WORD_SPLIT off），且本 case 自帶 POSIX 形態的 PATH（/usr/bin:/bin）"
        "⇒ 在 Windows 上把 zsh 裝起來也跑不出有意義的結果，這不是「缺件」。"
        "互補剖面＝macOS runner（🔴 誠實劃界：本 repo 今天沒有任何 macOS 剖面被 census 過，"
        "`tools/tests@win32` 的互補剖面只指向 linux ⇒ 這一支目前仍無覆蓋證據）",
    )
    def test_candidate_chain_word_splits_under_zsh(self) -> None:
        """🔴 zsh 迴歸鎖（R69 P2 自身修復過程中真的踩到）：候選鏈初版寫成空白
        分隔字串 + `for c in $LIST`，在 bash 下正確、在 **zsh** 下整條清單被當成
        單一候選 ⇒ 一支都命中不了。zsh 對未加引號的參數展開預設不做字詞切分
        （SH_WORD_SPLIT off），而 `source tools/dev_start.sh` 的主場正是 macOS
        預設 shell zsh——bash 全綠、真實入門路徑仍斷，與本輪要修的缺陷同型。
        """
        self._write_fake_39("python3")
        self._write_real_311("python3.11")
        r = subprocess.run(
            [shutil.which("zsh"), "-c",
             f'. "{_GUARD_SH_PATH}"\npick_python_ge_min\n'],
            capture_output=True, encoding="utf-8", errors="replace", timeout=120,
            env={"PATH": f"{self.bin}:/usr/bin:/bin", "HOME": str(self.tmp / "nohome")},
        )
        self.assertEqual(r.returncode, 0, f"zsh 下候選鏈全數落空：stderr={r.stderr}")
        self.assertTrue(r.stdout.strip())

    def test_production_candidate_chain_covers_documented_install_paths(self) -> None:
        """生產候選鏈必須真的涵蓋 ONBOARDING §1 那條安裝路徑的落點。

        上面的行為測試會覆寫候選清單（為了控制順序），故清單內容本身另立本鎖：
        少了 Homebrew 的落點，`brew install python@3.11` 之後但 PATH 尚未含
        `/opt/homebrew/bin` 的新機器就會回到修復前的斷點。
        """
        text = _GUARD_SH_PATH.read_text(encoding="utf-8")
        m = re.search(r"PYTHON_GE_MIN_CANDIDATES=\((.*?)\)", text, re.DOTALL)
        self.assertIsNotNone(m, "找不到 PYTHON_GE_MIN_CANDIDATES 宣告")
        chain = " ".join(m.group(1).split())
        for expected in (
            "python3.11", "python3.12", "python3.13", "python3", "python",
            "/opt/homebrew/opt/python@3.11/bin/python3.11",
            "/usr/local/opt/python@3.11/bin/python3.11",
            ".pyenv/shims/python3.11",
        ):
            self.assertIn(expected, chain, f"候選鏈缺少 {expected}")
        self.assertLess(
            chain.index("python3.11"), chain.index(" python3 "),
            "版本化名稱必須排在裸 python3 之前（.python-version 目標版優先）",
        )

    def test_wrapper_delegates_and_wires_fail_loud(self) -> None:
        """薄殼必須委派 SSOT 候選鏈，且失敗分支真的接上補救訊息 + 非零 rc。"""
        text = _DEV_START_SH_PATH.read_text(encoding="utf-8")
        code = "\n".join(
            ln for ln in text.splitlines() if not ln.lstrip().startswith("#")
        )
        self.assertIn('py="$(pick_python_ge_min)"', code)
        self.assertIn("python_ge_min_remediation", code)
        self.assertNotIn(
            'py="python3"', code,
            "又出現「命中 python3 即用、不看版本」的舊分支＝R69 P2 缺陷復發",
        )


class TestMinPythonVersionSsotSync(unittest.TestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestMinPythonVersionSsotSync WHY〉節。"""

    def test_min_python_version_is_consistent_across_dev_start_ssots(self) -> None:
        core_mm = "{}.{}".format(*dev_start._MIN_PY)
        sh_text = _GUARD_SH_PATH.read_text(encoding="utf-8")
        ps_text = _GUARD_PS1_PATH.read_text(encoding="utf-8-sig")

        self.assertIn(f'PYTHON_GE_MIN_MM="{core_mm}"', sh_text)
        self.assertIn(f"PythonGeMinMM = '{core_mm}'", ps_text)
        probe_tuple = "({}, {})".format(*dev_start._MIN_PY)
        for label, text in (("bash", sh_text), ("powershell", ps_text)):
            self.assertIn(
                f"sys.version_info[:2] >= {probe_tuple}", text,
                f"{label} 側版本探測碼與核心 _MIN_PY={core_mm} 不同步",
            )

    # 🔴 R71（DEF-101-760）：上面那支鎖**只看版本數字**，看不到探測碼本體。兩份
    # `.sh`／`.ps1` 的檔頭都白紙黑字寫「用**同一段**探測碼（同構，非各自發明）」，
    # 但那是散文——實測（本輪動工前）單邊把探測碼改掉，本檔與 CI 全部照樣綠燈。
    # DEF-101-760 正是踩在這個縫上：`else ""` 在 bash 沒事、在 PowerShell 5.1 會被
    # 吃掉一個雙引號而整條失效，於是「兩側寫法必須逐字相同」這個假設一旦破裂，
    # 就只剩其中一個平台的使用者會炸，而且沒有任何機械物會出聲。
    def test_version_probe_literal_is_byte_identical_across_both_shells(self) -> None:
        sh_probe, ps_probe = self._extract_probes()
        self.assertEqual(
            sh_probe, ps_probe,
            "兩側探測碼字面值不再逐字相同——兩份檔頭都自述『同一段探測碼』，"
            "散文對不上實況時必須是這裡先紅，而不是等某一個平台的使用者踩到：\n"
            f"  bash       : {sh_probe!r}\n"
            f"  powershell : {ps_probe!r}",
        )

    def test_version_probe_has_no_embedded_double_quote(self) -> None:
        """探測碼不得含雙引號——Windows PowerShell 5.1 傳給原生 exe 時會吃掉它。

        這條與上一條是**兩件事**，不可合併：上一條只保證「兩邊一樣」，兩邊一起改成
        含雙引號的寫法仍然全綠，而那正好是 DEF-101-760 修復前的狀態（兩側當時確實
        逐字相同，同時也確實兩側都寫著 `""`）。本條鎖的是「那個寫法本身不能用」。
        行為面的證據由 tools/tests/test_ps51_compat.py::TestPs51NativeArgvRoundTrip
        真的起一支 powershell.exe 提供；本條是不需要任何引擎、恆會執行的靜態備援。
        """
        sh_probe, ps_probe = self._extract_probes()
        for label, probe in (("bash", sh_probe), ("powershell", ps_probe)):
            self.assertNotIn(
                '"', probe,
                f"{label} 側探測碼含雙引號 → PS 5.1 會吃掉一個 ⇒ python 收到"
                f"`unterminated string literal` ⇒ 每個候選都被判不合格 ⇒ "
                f"Get-PythonGeMin 恆回 $null（DEF-101-760 復發）。"
                f"空字串請寫 `str()`：{probe!r}",
            )

    def test_probe_extraction_regexes_still_match(self) -> None:
        """載具自檢：抽取式失配時上面兩支鎖會因為抽不到而**無從比較**。

        沒有這一支，把 `$script:PythonGeMinProbe` 改名或改成雙引號宣告，
        `_extract_probes()` 的 assertIsNotNone 才是唯一防線；把它獨立成一支具名
        測試，是為了讓「鎖失效」與「探測碼不同步」在報表上是兩個可區分的紅燈。
        """
        sh_probe, ps_probe = self._extract_probes()
        for label, probe in (("bash", sh_probe), ("powershell", ps_probe)):
            self.assertIn(
                "sys.version_info[:2]", probe,
                f"{label} 側抽到的內容不像版本探測碼（抽取式疑似錯位）：{probe!r}",
            )

    def _extract_probes(self) -> tuple[str, str]:
        """(bash 側探測碼, powershell 側探測碼)；任一側抽不到即 fail-loud。"""
        sh_text = _GUARD_SH_PATH.read_text(encoding="utf-8")
        ps_text = _GUARD_PS1_PATH.read_text(encoding="utf-8-sig")
        m_sh = _SH_PROBE_RE.search(sh_text)
        m_ps = _PS1_PROBE_RE.search(ps_text)
        self.assertIsNotNone(
            m_sh, f"{_GUARD_SH_PATH.name} 找不到 PYTHON_GE_MIN_PROBE 單引號宣告"
            "——宣告形態被改動，本鎖已無法比對（不得靜默略過）",
        )
        self.assertIsNotNone(
            m_ps, f"{_GUARD_PS1_PATH.name} 找不到 $script:PythonGeMinProbe 單引號宣告"
            "——宣告形態被改動，本鎖已無法比對（不得靜默略過）",
        )
        return m_sh.group("probe"), m_ps.group("probe")


# ── R71（DEF-101-755 解鎖）：PowerShell 行為鎖用的假直譯器，依 `os.name` 分派 ──
#
# 為何 `os.name` 而不是 `sys.platform`：要分的是**行程建立語意**——POSIX 的 `execve`
# 認 shebang，Windows 的 `CreateProcess` 只認 PE 映像＋PATHEXT 副檔名。判例＝
# `tools/tests/test_bash_probe_spec_contract.py::_STUB_FORMS`（DEF-101-754）。
#
# 為何 Windows 的 3.9 冒充者拆成「`.cmd` ＋ 旁邊一支 `.py`」而不是把 spoof 程式塞進
# `.cmd` 一行：`.cmd` 內若再寫一層 `-c "<python 程式碼>"`，cmd.exe 的跳脫規則會疊在
# PowerShell 重組命令列的規則上——而本類要驗的正是「引數原封不動送到直譯器」
# （DEF-101-760），載具自己絕不能引入第二層引號變因。`%*` 只是把 PowerShell 交來的
# 參數原樣轉手，不新增任何一層。
#
# 內文全 ASCII（WHY 一律寫在本 Python 檔）：`.cmd` 由 cmd.exe 以 OEM code page 解讀，
# 本機為 CP950，寫中文註解等於自找亂碼。換行 CRLF：cmd.exe 對純 LF 批次檔的行為在
# 部分構造下未定義。兩項皆同 DEF-101-754 判例。
_FAKE_39_SPOOF_PY = '''\
import os
import runpy
import sys

sys.version_info = (3, 9, 6, "final", 0)
args = sys.argv[1:]
if args and args[0] == "-c":
    code = args[1]
    sys.argv = ["-c"] + args[2:]
    exec(code)
elif args:
    sys.argv = args
    sys.path.insert(0, os.path.dirname(os.path.abspath(args[0])))
    runpy.run_path(args[0], run_name="__main__")
'''

_FAKE_39_CMD = '@echo off\r\n"{real}" "{spoof}" %*\r\n'
_PASSTHROUGH_CMD = '@echo off\r\n"{real}" %*\r\n'


@unittest.skipUnless(_ps_any_engine(), "需要 PowerShell 引擎（pwsh/powershell）")
class TestGetPythonGeMinPowerShell(unittest.TestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestGetPythonGeMinPowerShell WHY〉節。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(_rmtree_force, self.tmp)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.ps = _ps_production_engine()

    def _run_ps(self, snippet: str, path_env: str | None = None):
        env = dict(os.environ)
        if path_env:
            env["PATH"] = path_env
        return subprocess.run(
            [self.ps, "-NoProfile", "-Command", ps_utf8_command(snippet)],
            capture_output=True, encoding="utf-8", errors="replace",
            env=env, timeout=180,
        )

    def _write_fake_39(self, stem: str) -> None:
        """造一支「自稱 3.9.6」的候選，命名為 `stem`（Windows 上為 `stem.cmd`）。"""
        if os.name == "nt":
            spoof = self.bin / f"_spoof39_{stem.replace('.', '_')}.py"
            spoof.write_text(_FAKE_39_SPOOF_PY, encoding="utf-8")
            (self.bin / f"{stem}.cmd").write_text(
                _FAKE_39_CMD.format(real=sys.executable, spoof=spoof),
                encoding="ascii", newline="",
            )
            return
        path = self.bin / stem
        path.write_text(_FAKE_39_SHIM.format(real=sys.executable), encoding="utf-8")
        path.chmod(0o755)

    def _write_real_311(self, stem: str) -> None:
        """把跑測試的直譯器（模組頂端版本閘保證 >= 3.11）以 `stem` 曝露到 PATH。"""
        if os.name == "nt":
            (self.bin / f"{stem}.cmd").write_text(
                _PASSTHROUGH_CMD.format(real=sys.executable),
                encoding="ascii", newline="",
            )
            return
        path = self.bin / stem
        path.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n', encoding="utf-8")
        path.chmod(0o755)

    def _fixture_path(self) -> str:
        """PATH＝fixture 目錄優先 ＋ 該平台跑得動 shim 所需的最小系統目錄。

        Windows 上 System32 不可省：`.cmd` 由 `CreateProcess` 轉交 cmd.exe 執行。
        目錄取自 `ComSpec`（`os.path.dirname`）而非寫死磁碟機路徑——後者會被
        `tools/tests/test_platform_neutral_paths.py` 的假路徑鎖攔下，且在非預設
        `SystemRoot` 的機器上是錯的。
        """
        if os.name == "nt":
            comspec = os.environ.get("ComSpec", "")
            extra = [os.path.dirname(comspec)] if comspec else []
            return os.pathsep.join([str(self.bin), *extra])
        return os.pathsep.join([str(self.bin), "/usr/bin", "/bin"])

    def test_fake_39_shim_is_live_so_the_version_check_is_what_rejects_it(self) -> None:
        """正控（鏡子自證）：假 3.9 候選必須**真的跑得起來**且自稱 3.9.6。

        沒有這一支，下一支的 `only39=[]` 會在「shim 根本啟動失敗」時同樣成立
        ⇒ 主判準（版本比較）一次都沒被執行卻顯示綠燈。DEF-101-755 之所以出現，
        根子就是「Windows 上 shim 起不來」這件事沒有任何機械物在看。

        🔴 本測試的探測片段刻意**不含任何雙引號**（第一版寫 `print("MM=%d.%d" % …)`
        當場被 PS 5.1 吃掉一個引號、實測拿到 `SyntaxError: invalid syntax`）——
        載具本身踩進 DEF-101-760 就會量到假紅，看起來像 shim 壞了。
        改印 `sys.version_info[:2]` 這個 tuple 的預設 repr，零引號需求。
        """
        self._write_fake_39("python3")
        r = self._run_ps(
            "& python3 -c 'import sys;print(sys.version_info[:2])'; "
            "'rc=' + $LASTEXITCODE",
            path_env=self._fixture_path(),
        )
        self.assertIn(
            "(3, 9)", r.stdout,
            f"假 3.9 候選沒能冒充成功 ⇒ 下一支測試會失去鑑別力\n"
            f"stdout={r.stdout!r}\nstderr={r.stderr!r}",
        )
        self.assertIn("rc=0", r.stdout, f"shim 非零退出：stdout={r.stdout!r}")

    def test_skips_sub_311_candidate(self) -> None:
        self._write_fake_39("python3")
        self._write_real_311("python3.11")

        r = self._run_ps(
            f'. "{_GUARD_PS1_PATH}"; '
            "$script:PythonGeMinCandidates = @('python3'); "
            '"only39=[" + (Get-PythonGeMin) + "]"; '
            "$script:PythonGeMinCandidates = @('python3', 'python3.11'); "
            '"both=[" + (Get-PythonGeMin) + "]"',
            path_env=self._fixture_path(),
        )
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr}")
        self.assertIn("only39=[]", r.stdout, "3.9 候選竟被 Get-PythonGeMin 接受")
        self.assertNotIn(
            "both=[]", r.stdout,
            "有 3.11 可用卻回 $null——這正是 DEF-101-760 在 Windows 上的病徵"
            f"（探測碼被 PS 5.1 吃掉引號 ⇒ 每個候選 rc=1）\nstdout={r.stdout!r}",
        )

    def test_remediation_lists_actionable_commands(self) -> None:
        r = self._run_ps(f'. "{_GUARD_PS1_PATH}"; Write-PythonGeMinRemediation')
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr}")
        self.assertIn("❌", r.stdout)
        self.assertIn("winget install -e --id Python.Python.3.11", r.stdout)

    def test_ps1_wrapper_delegates_and_wires_fail_loud(self) -> None:
        code = "\n".join(
            ln for ln in _DEV_START_PS1_PATH.read_text(encoding="utf-8-sig").splitlines()
            if not ln.lstrip().startswith("#")
        )
        self.assertIn("$Py = Get-PythonGeMin", code)
        self.assertIn("Write-PythonGeMinRemediation", code)
        self.assertNotIn(
            "Get-Command py -ErrorAction SilentlyContinue", code,
            "又出現「py launcher 命中即用、不看版本」的舊分支＝R69 P2 缺陷復發",
        )


# R69 P1：版本閘之前的 prelude 必須在 _MIN_PY 下限以下的直譯器可載入；缺陷本體與
# 舊測試（`_FAKE_39_SHIM`）為何結構上驗不到，原文＝Guard_Repin 證據檔 §D-2。
# 本節改用真的次版直譯器 subprocess 實跑＋不依賴外部直譯器的靜態掃描，兩道互為備援。

_TOOLS_DIR = Path(__file__).resolve().parents[1]
_DEV_START_PY = _TOOLS_DIR / "dev_start.py"

# 掃描起點（各自的「必須在下限版可載入」射程）：
#   dev_start.py  → 只到版本閘為止（閘之後本來就允許 3.11+ API）
#   bootstrap_core.py → **整支**。它是 dev_start 版本閘訊息裡指名的補救路徑
#       （「先跑 bash tools/bootstrap.sh，其核心 3.9 可載入、會自動挑 3.11 建
#       .venv」），而 tools/bootstrap.sh 在 .venv 尚未存在時就是拿系統 python3
#       跑它。它若也炸 traceback，那句補救指引就是假的，使用者無路可走。
_PY39_ENTRYPOINTS = (
    (_DEV_START_PY, "prelude"),
    (_TOOLS_DIR / "bootstrap_core.py", "whole"),
)

# 3.9 之後才出現的 stdlib 名字（只列「寫程式時真的會順手用上、且一用就炸」的）。
# 這不是完整表，也不需要是——第一道真跑鎖才是完整判定，本表是它缺席時的近似。
_POST_39_MODULES = frozenset({"tomllib"})
_POST_39_FROM_NAMES = {
    "datetime": frozenset({"UTC"}),                                   # 3.11
    "enum": frozenset({"StrEnum", "ReprEnum", "EnumCheck", "verify"}),  # 3.11
    "asyncio": frozenset({"TaskGroup", "Runner", "Barrier", "timeout"}),  # 3.11
    "contextlib": frozenset({"chdir"}),                               # 3.11
    "hashlib": frozenset({"file_digest"}),                            # 3.11
    "typing": frozenset({                                             # 3.10 / 3.11
        "Self", "Never", "LiteralString", "assert_never", "assert_type",
        "reveal_type", "dataclass_transform", "TypeVarTuple", "Unpack",
        "ParamSpec", "Concatenate", "TypeAlias", "TypeGuard",
    }),
    "types": frozenset({"UnionType", "NoneType", "EllipsisType"}),     # 3.10
}


def _sub_min_interpreter_candidates() -> list[list[str]]:
    """候選直譯器的 argv（順序＝先便宜後昂貴）。

    🔴 R81 包 F（S3-06）：原本只有一串 PATH 名稱，而那串在 Windows 上結構上找不到
    任何可用的東西（pyenv-win shim 本機實測細節，原文＝Guard_Repin 證據檔 §D-13）。

    三種發現路徑並存，缺一都會在某類機器上失明：
      · `/usr/bin/python3`：macOS 主場（3.9.x），POSIX 上第一順位就命中。
      · pyenv：win 佈局 `<root>/versions/<ver>/python.exe` 與 posix 佈局
        `<root>/versions/<ver>/bin/python3` 兩種都掃，不存在的那一種自然掃不到東西
        （鐵律三：判準不得只在一個平台成立）。
      · Windows Python Launcher `py -3.X`：本機今天 `Get-Command py` 為空，所以它
        **不能**是唯一依靠，但別的 Windows 機器上常常只有它。
      · PATH 上的 `python3.X` 名稱：保留原行為（它在 CI 的 Linux 映像上就是主場）。
    """
    out: list[list[str]] = [["/usr/bin/python3"]]

    roots: list[Path] = []
    env_root = os.environ.get("PYENV_ROOT") or os.environ.get("PYENV")
    if env_root:
        roots.append(Path(env_root))
    roots.append(Path.home() / ".pyenv" / "pyenv-win")   # pyenv-win 佈局
    roots.append(Path.home() / ".pyenv")                 # pyenv（POSIX）佈局
    seen: set[str] = set()
    for root in roots:
        versions = root / "versions"
        if not versions.is_dir():
            continue
        for ver_dir in sorted(versions.iterdir()):
            for rel in ("python.exe", "bin/python3", "bin/python"):
                exe = ver_dir / rel
                if exe.is_file() and str(exe) not in seen:
                    seen.add(str(exe))
                    out.append([str(exe)])

    launcher = shutil.which("py")
    if launcher:
        out.extend([launcher, f"-3.{minor}"] for minor in (10, 9, 8, 7))

    out.extend([name] for name in ("python3.9", "python3.10", "python3.8", "python3.7"))
    return out


def _find_sub_min_interpreter() -> tuple[list[str] | None, tuple[int, ...] | None,
                                         list[str]]:
    """找一支版本**低於** `dev_start._MIN_PY` 的真直譯器（macOS 主場：/usr/bin/python3）。

    回傳 `(argv, (major, minor), broken)`。第三個值是**本輪的重點**：那些「找到了、
    跑了、但它自己壞掉」的候選，逐支帶 rc 與 stderr 首行。

    🔴 為何不能像原本那樣 `if probe.returncode != 0: continue`（S3-06）：那樣一來
    「根本沒找到」與「找到了但載具壞掉」會塌成同一個結果，而 skip reason 只說得出
    前者——於是帳面上是「這台機器缺件」（一個永遠不會有人去修的理由），實況是一支
    壞掉的 shim。本 repo 紀律〔斷言環境缺件前必先實查〕防的正是這個形態。
    """
    broken: list[str] = []
    for argv in _sub_min_interpreter_candidates():
        head = argv[0]
        exe = head if os.path.isabs(head) else shutil.which(head)
        if not exe or not Path(exe).exists():
            continue
        resolved = [exe, *argv[1:]]
        try:
            probe = subprocess.run(
                [*resolved, "-c", "import sys;print('%d.%d' % sys.version_info[:2])"],
                capture_output=True, encoding="utf-8", errors="replace", timeout=60,
            )
        except OSError as e:                       # 載具存在但起不來（權限／格式）
            broken.append(f"{' '.join(resolved)} → OSError {e}")
            continue
        if probe.returncode != 0:
            first = (probe.stderr or probe.stdout or "").strip().splitlines()
            broken.append(
                f"{' '.join(resolved)} → rc={probe.returncode} "
                f"stderr={first[0] if first else '(空)'}")
            continue
        try:
            mm = tuple(int(x) for x in probe.stdout.strip().split("."))
        except ValueError:
            broken.append(f"{' '.join(resolved)} → 版本輸出無法解析：{probe.stdout!r}")
            continue
        if mm < dev_start._MIN_PY:
            return resolved, mm, broken
    return None, None, broken


class TestRealSubMinInterpreterPrelude(unittest.TestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestRealSubMinInterpreterPrelude WHY〉節。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.py, cls.mm, cls.broken = _find_sub_min_interpreter()

    def setUp(self) -> None:
        if self.py is None:
            # 🔴 fail loud，不靜默綠：這支鎖的價值全在「真的用舊直譯器跑一次」，
            # 環境湊不出舊直譯器時必須讓 skip 訊息自己喊出來（`[TOOL-ABSENCE]`），
            # 讓 CI log 上「這道鎖沒跑」是可被搜尋的事實，而不是一片綠裡的沉默。
            #
            # 🔴 R81 包 F（S3-06）：兩種失效必須分得開，本機實況原文＝
            # Guard_Repin 證據檔 §D-14。
            if self.broken:
                self.skipTest(
                    f"[TOOL-ABSENCE] 找得到候選直譯器，但**每一支都跑不起來**"
                    f"（不是缺件，是載具壞掉）：{'；'.join(self.broken)}"
                    "⇒ 修好其中任一支即可讓本鎖真跑；不要把這句讀成「這台機器沒有舊直譯器」"
                )
            self.skipTest(
                f"[TOOL-ABSENCE] 找不到版本 < {dev_start._MIN_PY} 的真直譯器"
                "（掃過 /usr/bin/python3、pyenv 的 versions/ 目錄（win 與 posix 兩種佈局）、"
                "Windows Python Launcher `py -3.X`、PATH 上的 python3.7~3.10）"
                "⇒ 本機無法真跑 prelude 相容性鎖；macOS 真機必有 /usr/bin/python3（3.9.x）"
            )

    def _run(self, argv: list[str]):
        return subprocess.run(
            [*self.py, *argv], cwd=str(_TOOLS_DIR.parent), capture_output=True,
            encoding="utf-8", errors="replace", timeout=120,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )

    def test_dev_start_prelude_loads_and_gate_fires_friendly(self) -> None:
        r = self._run([str(_DEV_START_PY), "--help"])
        combined = r.stdout + r.stderr
        self.assertNotIn(
            "Traceback", combined,
            f"版本閘**之前**的 prelude 在 Python {'.'.join(map(str, self.mm))} 上炸了"
            f"（{' '.join(self.py)}）——DEF-101-628 的友善訊息又被 traceback 取代。"
            f"修法：把 3.11+ 專屬 import 移到版本閘之後或函式內。\n{combined}",
        )
        self.assertEqual(
            r.returncode, 2,
            f"rc={r.returncode}（版本閘定義為 2）\n{combined}",
        )
        self.assertIn("dev_start 需要 Python >=", r.stderr)
        self.assertIn("brew install python@3.11", r.stderr,
                      "友善訊息必須含逐字可執行的補救指令，不能只叫人去翻文件")

    def test_documented_bootstrap_remediation_actually_loads(self) -> None:
        """版本閘訊息把 `bash tools/bootstrap.sh` 當補救路徑 ⇒ 它的核心也得真的載得動。"""
        core = _TOOLS_DIR / "bootstrap_core.py"
        r = self._run(["-c", f"import sys;sys.path.insert(0,{str(_TOOLS_DIR)!r});"
                             "import bootstrap_core"])
        self.assertEqual(
            r.returncode, 0,
            f"{core.name} 在 Python {'.'.join(map(str, self.mm))} 上載入失敗 ⇒ 版本閘訊息"
            f"指的補救路徑是死路（使用者無路可走）\n{r.stdout}{r.stderr}",
        )


class TestPy39PreludeStaticScan(unittest.TestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestPy39PreludeStaticScan WHY〉節。"""

    def _prelude_source(self, path: Path) -> tuple[str, ast.Module]:
        """回傳 dev_start.py「版本閘（含）以前」的原始碼切片。"""
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        gate = next(
            (n for n in tree.body
             if isinstance(n, ast.If) and "version_info" in ast.dump(n.test)),
            None,
        )
        # fail-open 自檢：閘不見了（被改寫/搬走）⇒ 本鎖的射程會靜默縮成 0，
        # 那比缺陷本身更糟，故直接判失敗。
        self.assertIsNotNone(gate, f"{path.name} 找不到 sys.version_info 版本閘 ⇒ 掃描射程失效")
        lines = src.splitlines(keepends=True)
        return "".join(lines[: gate.end_lineno]), tree

    def _scoped_sources(self) -> dict[str, str]:
        """推導完整射程：入口 + 其（遞迴）import 到的本地 tools 模組整支檔。"""
        search = (_TOOLS_DIR, _TOOLS_DIR / "lib")
        out: dict[str, str] = {}
        pending: list[tuple[Path, str]] = list(_PY39_ENTRYPOINTS)
        seen: set[Path] = set()
        while pending:
            path, mode = pending.pop()
            if path in seen:
                continue
            seen.add(path)
            src = (self._prelude_source(path)[0] if mode == "prelude"
                   else path.read_text(encoding="utf-8"))
            # 🔴 key 必須用 as_posix()：str(PurePath) 在 Windows 渲染成 `tools\dev_start.py`，
            # 下方以 `"tools/dev_start.py"` 正斜線字面值斷言就會 Windows 假紅；更糟的是
            # assertNotIn 那條（ci_liveness 不得入射程）在 Windows 上會恆真通過＝假鎖。
            out[path.relative_to(_TOOLS_DIR.parent).as_posix()] = src
            for node in ast.walk(ast.parse(src)):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module.split(".")[0]]
                for name in names:
                    for base in search:
                        cand = base / f"{name}.py"
                        if cand.exists() and cand not in seen:
                            pending.append((cand, "whole"))
        return out

    def test_scope_covers_the_known_prelude_dependencies(self) -> None:
        """鑑別力自檢：射程推導若壞掉（只剩入口自己），下面兩支鎖就全是空轉。"""
        scoped = self._scoped_sources()
        self.assertIn("tools/dev_start.py", scoped)
        self.assertIn("tools/_stdio_utf8.py", scoped,
                      "dev_start prelude 的本地相依 _stdio_utf8 未被納入射程 ⇒ 推導壞了")
        self.assertNotIn(
            "tools/lib/ci_liveness.py", scoped,
            "ci_liveness 帶有 3.11 專屬的 datetime.UTC，卻進了「下限版可載入」射程"
            "⇒ 代表有人把它的 import 移到版本閘之前（＝R69 P1 缺陷復發）",
        )

    def test_no_post_39_stdlib_names_before_the_version_gate(self) -> None:
        offenders: list[str] = []
        for label, src in self._scoped_sources().items():
            for node in ast.walk(ast.parse(src)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".")[0] in _POST_39_MODULES:
                            offenders.append(f"{label}:{node.lineno} import {alias.name}")
                elif isinstance(node, ast.ImportFrom) and node.module:
                    banned = _POST_39_FROM_NAMES.get(node.module.split(".")[0], frozenset())
                    for alias in node.names:
                        if alias.name in banned:
                            offenders.append(
                                f"{label}:{node.lineno} from {node.module} import {alias.name}"
                            )
        self.assertEqual(
            offenders, [],
            "以下 import 只有 Python >= 3.10/3.11 才有，卻位在版本閘之前（或被它相依）"
            "⇒ 舊直譯器上會變 ImportError traceback，友善訊息失效：\n  "
            + "\n  ".join(offenders)
            + "\n修法：移到版本閘之後（見 dev_start.py `from datetime import UTC` 那行的註解），"
              "或延後到函式內 import。",
        )

    def test_scope_parses_under_the_oldest_supported_grammar(self) -> None:
        """語法面的零策展鎖：整個射程必須能被 3.9 文法解析。

        `ast.parse(..., feature_version=(3, 9))` 會對 `match` 陳述式等 3.10+ 文法
        直接丟 SyntaxError——這類東西不需要維護黑名單就抓得到，與上面的名字黑名單
        互補（黑名單管 API、本鎖管文法）。
        """
        for label, src in self._scoped_sources().items():
            with self.subTest(file=label):
                try:
                    ast.parse(src, feature_version=(3, 9))
                except SyntaxError as exc:
                    self.fail(f"{label} 用到 3.9 文法不支援的語法：{exc.msg}（line {exc.lineno}）")

    def test_blocklist_still_contains_the_two_that_actually_bit_us(self) -> None:
        """棘輪：黑名單被清空/縮水，上面那支鎖就退化成永遠綠。"""
        self.assertIn("UTC", _POST_39_FROM_NAMES["datetime"], "R69 P1 的兇手")
        self.assertIn("tomllib", _POST_39_MODULES, "R68 DEF-101-628 的兇手")


# ======================================================= 原生 stdout 解碼（DEF-101-762）
# 為何這組鎖住在本檔而非自己一支檔（R71／DEF-101-561③ 架構裁決）、以及這條缺陷為何
# 能活著出貨兩天以上（cp950 mojibake 真機實測、顯形條件與驗證條件互斥），
# 原文＝Guard_Repin 證據檔 §D-12。
#
# 三道鎖分工刻意不同，缺一都會退回原狀：①行為鎖（原生 5.1 才有鑑別力）②同類別內的
# 負控（證明危害此刻仍存在，否則①在「載具沒走到危害條件」時一樣綠）③靜態備援（任何
# 平台都跑）。③的誠實劃界（ADR-XPLAT-002 §3.2）：字面比對**不等於**行為證明，它只擋
# 「有人把包裝拆掉退回裸呼叫」這條最可能的回歸路；真正的行為證據是①②。

_PS1_SHIM = _TOOLS_DIR / "lib" / "GitHooksInstallCommon.ps1"
_PY_SSOT = _TOOLS_DIR / "git_hooks_install_common.py"

# 生產 `.ps1` 裡那道 UTF-8 釘選的**逐字引述**（DEF-101-762 的修復本體）。兩個安裝器都
# 必須逐字帶這一串，故引述只留一份。它是被斷言的**對象**，不是本測試樹拿去執行的前置
# ——改寫成 SSOT 寫法會讓斷言不再指向生產碼實際長的樣子＝鎖失效，故走具名豁免。
_PROD_UTF8_PIN = (
    "[Console]::OutputEncoding = New-Object "
    "System.Text.UTF8Encoding($false)"  # ps-utf8-quote-ok: 逐字引述生產碼，非本樹前置
)

# 煙霧測試 —— 與 tools/windows_smoke_local.ps1 [6/9] 用的是同一個目錄名。刻意以碼位而非
# 字面值書寫：本檔一旦被以非 UTF-8 讀取，字面值自己就先壞了，鎖會變成在驗自己（同
# test_ps51_compat 對「載具不可踩進待測缺陷」的要求）。
_CJK_CODEPOINTS = (0x7159, 0x9727, 0x6E2C, 0x8A66)
_CJK = "".join(chr(cp) for cp in _CJK_CODEPOINTS)

# 共用 Python CLI 的四個子指令——全部都必須經過 Invoke-CommonPy。
_SUBCOMMANDS = (
    "assert-not-linked-worktree",
    "get-hooks-dir",
    "assert-hooks-present",
    "check-installed",
)
_RAW_PY_CALL = "& python $script:GitHooksInstallCommonPy"

# DEF-101-762 在 LATEST 版 SDD 樹上的**兩個**同形態站點：都以 `git rev-parse` 的輸出反推
# 路徑，cp950 下損毀即整條路不可用。R71 落地時只鎖了 install_post_commit.ps1，run_tlc.ps1
# 雖已同法修好，卻只有 `check_script_parity._LATEST_PINNED_SHA256` 的 hash 釘選——那只證明
# 「內容沒被動過」，證明不了「釘選在讀取之前」，而後者正是本缺陷的形狀。「同棵樹、同形態、
# 只鎖一支」就是 DEF-101-757 入規要防的鎖射程缺口，故 R71 參數化到第二支（成本＝一個 case）。
_LATEST_REV_PARSE_SITES = (
    ("tools/install_hooks/install_post_commit.ps1",
     "它用 `git rev-parse --git-common-dir` 的輸出反推 repo 根，cp950 下中文路徑損毀會讓它"
     "以「找不到共用函式 …\\tools\\lib\\WindowsAppsGuard.ps1」中止（真機實測重現）"),
    ("tools/fsm_runtime/formal/run_tlc.ps1",
     "它同樣以 `--git-common-dir` 反推 `$MainCheckoutRoot` 再組出 WindowsAppsGuard.ps1 路徑，"
     "損毀即以 exit 2 中止 ⇒ 中文路徑的 repo 上形式化驗證（TLA+/TLC）整條路不可用"),
)


def _ps_cjk_literal() -> str:
    """在 PowerShell 端以碼位重建中文字串的運算式（保持本 snippet 純 ASCII）。

    snippet 走 `-Command` 傳入，中文字面值本身雖能經 CreateProcessW 完好抵達，但純
    ASCII 讓「傳輸層有沒有偷改東西」不再是本鎖需要先排除的變因。
    """
    chars = ", ".join(f"[char]0x{cp:04X}" for cp in _CJK_CODEPOINTS)
    return f"(-join ({chars}))"


def _parse_kv(stdout: str) -> dict[str, str]:
    """收 `KEY=VALUE` 行（子行程刻意只吐 ASCII，避免回程再被編碼問題污染）。"""
    out: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            out[key.strip()] = value.strip()
    return out


@unittest.skipUnless(
    _ps_windows_native_51(),
    "[WINDOWS-NATIVE-ONLY] 需要 Windows 真機上的原生 powershell.exe（5.1）："
    "本鎖量的是 5.1 依 [Console]::OutputEncoding 解碼原生指令 stdout 的行為，"
    "刻意不 fallback 到 pwsh（理由同 _ps_engine 語意④）。跨平台備援＝"
    "TestNativeStdoutDecodingRoutingLock（不需任何引擎）",
)
class TestGetDispatcherHooksDirUnderCp950(unittest.TestCase):
    """cp950 主控台 + 中文 repo 路徑下，共用 shim 回傳的路徑不得損毀。"""

    def _probe(self, repo: Path) -> dict[str, str]:
        """在強制 cp950 的子行程內，同時量「修復後」與「修復前寫法」兩個值。"""
        snippet = f"""
$env:PATH = '{Path(sys.executable).parent}' + ';' + $env:PATH
[Console]::OutputEncoding = [System.Text.Encoding]::GetEncoding(950)
$cn = {_ps_cjk_literal()}
Set-Location -LiteralPath '{repo}'
. '{_PS1_SHIM}'
$fixed = Get-DispatcherHooksDir
$raw = & python '{_PY_SSOT}' get-hooks-dir
'CP=' + [Console]::OutputEncoding.CodePage
'FIXED_INTACT=' + ([string]$fixed).Contains($cn)
'RAW_INTACT=' + ([string]$raw).Contains($cn)
'FIXED_EMPTY=' + [string]::IsNullOrEmpty([string]$fixed)
"""
        proc = subprocess.run(
            [_ps_native_51(), "-NoProfile", "-Command", snippet],
            capture_output=True, encoding="utf-8", errors="replace", timeout=180,
        )
        kv = _parse_kv(proc.stdout)
        for key in ("CP", "FIXED_INTACT", "RAW_INTACT", "FIXED_EMPTY"):
            self.assertIn(
                key, kv,
                f"載具故障：子行程未回報 {key}（不得當成通過）\n"
                f"rc={proc.returncode}\nstdout={proc.stdout!r}\nstderr={proc.stderr!r}",
            )
        self.assertEqual(
            kv["CP"], "950",
            "載具故障：子行程的 [Console]::OutputEncoding 沒有停在 cp950——"
            "危害條件根本沒被建立起來，本鎖此刻零鑑別力",
        )
        self.assertEqual(
            kv["FIXED_EMPTY"], "False",
            f"載具故障：Get-DispatcherHooksDir 回傳空值（shim 疑似在 dot-source 階段"
            f"就 return，例如子行程解析不到 python）\nstderr={proc.stderr!r}",
        )
        return kv

    def _cjk_repo(self, tmp: str) -> Path:
        repo = Path(tmp) / _CJK / "repo"
        repo.mkdir(parents=True)
        init = subprocess.run(
            ["git", "init", "--quiet", str(repo)],
            capture_output=True, encoding="utf-8", errors="replace", timeout=60,
        )
        self.assertEqual(init.returncode, 0, f"載具故障：git init 失敗 {init.stderr!r}")
        return repo

    def test_hooks_dir_survives_cp950_console(self) -> None:
        """本體：cp950 下 `Get-DispatcherHooksDir` 必須回傳未損毀的中文路徑。

        壞掉的後果（真機實測，非推測）：路徑變 mojibake → 下游 `assert-hooks-present`
        找不到 hook 檔 → `install_git_hooks.ps1` exit 1 ⇒ **路徑含中文的 repo 根本裝
        不了 git hooks**，且只在非 UTF-8 主控台重現。
        """
        with tempfile.TemporaryDirectory() as tmp:
            kv = self._probe(self._cjk_repo(tmp))
        self.assertEqual(
            kv["FIXED_INTACT"], "True",
            "cp950 主控台下 Get-DispatcherHooksDir 回傳的路徑遺失了非 ASCII 片段"
            "（DEF-101-762 回歸）。根因：PowerShell 依 [Console]::OutputEncoding 解碼"
            "原生指令 stdout，而 git_hooks_install_common.py 固定吐 UTF-8。"
            "修法：呼叫期間把 [Console]::OutputEncoding 釘成 UTF-8 再還原"
            "（見 tools/lib/GitHooksInstallCommon.ps1 的 Invoke-CommonPy）",
        )

    def test_carrier_has_teeth_raw_call_really_is_corrupted(self) -> None:
        """負控（鏡子自證）：修復前的裸呼叫寫法必須**真的**被改壞。

        沒有這一支，上一支在「cp950 其實沒生效／危害已不存在」時同樣是綠的——本 repo
        已兩度為此付出代價（DEF-101-760 唯一有行為鑑別力的鎖被 skip 在門外、
        DEF-101-761 紅燈無 log 落點）。本測試把「這個危害在本機此刻仍然存在」變成可
        觀測的事實，而不是註解裡的宣稱。
        """
        with tempfile.TemporaryDirectory() as tmp:
            kv = self._probe(self._cjk_repo(tmp))
        self.assertEqual(
            kv["RAW_INTACT"], "False",
            "裸 `& python …` 在 cp950 下竟原封不動傳回了中文路徑——本鎖假設的危害"
            "不存在了（PowerShell 換版？Windows 改了 GetConsoleOutputCP 語意？）。"
            "請重新量測並改寫本段註解，**不要留一支恆綠的鎖**；若危害真的消失，"
            "Invoke-CommonPy 的 UTF-8 釘選也應一併重新評估是否還需要",
        )


class TestNativeStdoutDecodingRoutingLock(unittest.TestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestNativeStdoutDecodingRoutingLock WHY〉節。"""

    def test_shim_routes_every_python_call_through_invoke_commonpy(self) -> None:
        """四個子指令全部經 `Invoke-CommonPy`；裸呼叫只准存在於該函式內部那一處。"""
        text = _PS1_SHIM.read_text(encoding="utf-8-sig")
        self.assertIn(
            "function Invoke-CommonPy", text,
            "tools/lib/GitHooksInstallCommon.ps1 找不到 Invoke-CommonPy——"
            "UTF-8 釘選入口疑似被移除（DEF-101-762 回歸）",
        )
        self.assertEqual(
            text.count(_RAW_PY_CALL), 1,
            f"`{_RAW_PY_CALL}` 出現 {text.count(_RAW_PY_CALL)} 次，應恰為 1 次"
            f"（只有 Invoke-CommonPy 內部那一處）。多出來的裸呼叫在非 UTF-8 主控台下"
            f"會把非 ASCII 路徑解成 mojibake（DEF-101-762）",
        )
        for sub in _SUBCOMMANDS:
            self.assertIn(
                f"Invoke-CommonPy -PyArgs @('{sub}'", text,
                f"子指令 {sub!r} 未經 Invoke-CommonPy 呼叫——該路徑缺 UTF-8 釘選",
            )

    def test_shim_invoke_commonpy_pins_utf8(self) -> None:
        """釘選本體還在（防「留著函式殼、把釘選拿掉」——import 級/存在級鎖看不到）。"""
        text = _PS1_SHIM.read_text(encoding="utf-8-sig")
        self.assertIn(
            _PROD_UTF8_PIN, text,
            "Invoke-CommonPy 內的 UTF-8 釘選不見了——函式殼還在但已無作用",
        )
        self.assertIn(
            "[Console]::OutputEncoding = $prevEnc", text,
            "UTF-8 釘選沒有還原路徑——會把主控台編碼洩漏給呼叫端；對 "
            "windows_smoke_local.ps1 而言更嚴重：受測腳本是同行程 `& $installer` "
            "呼叫，繼承 UTF-8 主控台後 [6] 那個專測 cp950 的缺陷就再也重現不出來",
        )

    def test_latest_git_rev_parse_sites_pin_utf8_before_reading_output(self) -> None:
        """LATEST 版**每一個** `git rev-parse → 路徑` 同型站點都必須先釘 UTF-8。

        LATEST 動態解析，Copy-on-Evolve 升版後本鎖不失效；凍結版 v0.01~v0.(N-1) 依鐵律
        不掃也不修。R71 本鎖只有 install_post_commit.ps1 一支（原名
        `test_latest_install_post_commit_pins_utf8_before_reading_git_common_dir`），
        R71 參數化到 `_LATEST_REV_PARSE_SITES`（WHY 見該表上方）。
        """
        latest = sdd_latest.resolve_latest_root(_TOOLS_DIR.parent / "AISDLC_SDD")
        # 錨在**執行敘述**上，不是 `--git-common-dir` 這個字串本身——該字串在兩支檔的檔頭
        # 註解都出現過，拿它比序會量到註解、不是程式碼。
        read_stmt = "$GitCommonDir = (git rev-parse"
        for rel, harm in _LATEST_REV_PARSE_SITES:
            with self.subTest(site=rel):
                target = latest / rel
                self.assertTrue(target.is_file(), f"找不到 LATEST 版 {rel}：{target}")
                text = target.read_text(encoding="utf-8-sig")
                self.assertIn(
                    _PROD_UTF8_PIN, text,
                    f"{rel} 缺 UTF-8 釘選（DEF-101-762 同型站點）：{harm}",
                )
                self.assertIn(
                    read_stmt, text,
                    f"{rel} 找不到 `{read_stmt}` 敘述——檔案結構已變動，本鎖需重新錨定",
                )
                self.assertLess(
                    text.index(_PROD_UTF8_PIN), text.index(read_stmt),
                    f"{rel}：UTF-8 釘選必須在 `{read_stmt} …` **之前**——順序反了等於沒釘",
                )


# ================================================ 非 Windows 平台短路（DEF-101-766）
# 缺陷本體：PATHEXT 過濾在非 Windows 上讓 Get-PythonGeMin 恆回 $null（與 DEF-101-759
# 同病換平台發作），原文＝Guard_Repin 證據檔 §D-11。
#
# 🔴 為何用「參數化 harness」而不是真的起一支 PS Core：缺陷只在
# 「`$PSVersionTable.PSVersion.Major >= 6` 且 `$IsWindows` 為假」時顯形，而在 Windows
# 上**任何**引擎都讓 `$IsWindows` 為真（它是唯讀常數），故那個組合在此平台結構性
# 不可達——引擎裝了什麼一律現查 `tools/tests/_ps_engine.py::available_engines()`，
# 不寫進本檔（R74：原句把量測當時的機器屬性寫成了常數，DEF-101-777 同型）。
# 替身變數這條路本包**實測走不通**：`$PSVersionTable` 在
# PS 5.1 是 read-only，`$PSVersionTable = …`／`$local:PSVersionTable = …`／
# `New-Variable -Force` 三種寫法皆回 `Cannot overwrite variable PSVersionTable because
# it is read-only or constant.`，連子作用域都蓋不掉（函式內看到的仍是 Major=5）。
# 故改為把**生產函式原始碼原封搬進 harness**，只把那一個蓋不掉的運算式換成可設定的
# `$FakePsMajor`（替換恰 1 處，數目不對即 fail-loud）。`$IsWindows` 不必替換——它在
# PS 5.1 本來就是未定義變數，harness 直接賦值即可，模擬 5.1 時則刻意**不定義**它。
#
# 🔴 被否決的第三種做法（誠實記錄，免下一個人再走一遍；本包實測結果原文＝
# Guard_Repin 證據檔 §D-11）：「在 PS 5.1 下清空 `$env:PATHEXT` 跑生產函式、斷言
# 它不回 $null」**零鑑別力**。
#
# 兩道鎖分工（缺一即有缺口，且此處**不是**「行為＋字面」的例行搭配）：①行為鎖真的執行
# 函式本體，抓「短路不存在／不生效」；②順序鎖抓「短路存在但落在 PATHEXT 過濾之後」。
# ②不是①的字面備援：本包實測把短路整段**搬到 PATHEXT 迴圈之後**，①仍回
# `RESULT_NULL=False`（迴圈在 POSIX 上濾光後落空、短路照樣接住）＝①對這種改法全綠，
# 只有②看得見。反之刪掉整段短路時①當場紅（實測 `RESULT_NULL=True`）。

_RESOLVE_FN = "Resolve-NativeExecutable"
_PS_MAJOR_EXPR = "$PSVersionTable.PSVersion.Major"
_PS_MAJOR_FAKE = "$FakePsMajor"
_PATHEXT_EXPR = "$env:PATHEXT"
_NON_WIN_GUARD = "if (-not $isWindowsHost)"
# 主機判定式的**逐字**形態：版本比較必須排在 `$IsWindows` 前面。`$IsWindows` 在 PS 5.1
# 未定義，對調後在 `Set-StrictMode -Version Latest` 的呼叫端會直接丟例外（生產碼在地
# 註解逐字載明「判定式順序不可調換」，本常數就是那句話的機械化）。
_ORDERED_HOST_TEST = "($PSVersionTable.PSVersion.Major -lt 6) -or $IsWindows"


def slice_ps_function(source: str, name: str) -> str:
    """切出 `function <name> { … }`（到收在第 0 欄的 `}` 為止——本 repo .ps1 的體例）。"""
    start = source.index(f"function {name} {{")
    return source[start : source.index("\n}\n", start) + len("\n}\n")]


def ps_code_only(body: str) -> str:
    """剝掉註解（整行 ＋ 行尾）：順序與計數判準量的是**程式碼**，不是講解。

    整行註解：在地 WHY 就寫在短路上方、且逐字提到 PATHEXT，含註解比序會量到註解
    （判例＝同檔 `test_latest_git_rev_parse_sites_pin_utf8_before_reading_output`
    對 `--git-common-dir` 出現在檔頭註解而必須改錨的教訓）。

    行尾註解：主機判定式那一行**可預期**會被掛上 `# ps7-ok: <WHY>` 豁免——
    `tools/tests/test_ps51_compat.py` 把 `$IsWindows` 判為 PS 6.0+ 專屬自動變數，而本處
    正是「確有必要」那一類（版本比較先短路，5.1 上根本不會讀到它）。豁免的 WHY 幾乎一定
    會逐字提到 `$IsWindows`，不剝行尾註解的話那一掛就會把本檔的計數判準推翻——鎖因為
    別人補了正確的豁免而翻紅，是最沒有說服力的一種紅。
    引號平衡檢查是為了不誤剝字串裡的 `#`（本函式射程內的程式碼一個 `#` 都沒有，此判斷
    是給未來的；踩到不平衡就整行保留，往「少剝」＝嚴格方向倒）。
    """
    kept: list[str] = []
    for line in body.splitlines():
        if line.lstrip().startswith("#"):
            continue
        cut = line.find(" #")
        if cut != -1 and line.count("'", 0, cut) % 2 == 0 and line.count('"', 0, cut) % 2 == 0:
            line = line[:cut].rstrip()
        if line.strip():
            kept.append(line)
    return "\n".join(kept)


def non_windows_short_circuit_problems(body: str) -> list[str]:
    """純函式核心（供構造輸入自檢）：回傳結構／順序問題碼清單，空清單＝合格。"""
    code = ps_code_only(body)
    problems: list[str] = []
    n_major = code.count(_PS_MAJOR_EXPR)
    n_pathext = code.count(_PATHEXT_EXPR)
    if n_major != 1:
        problems.append(
            f"version-probe-count：程式碼裡 `{_PS_MAJOR_EXPR}` 出現 {n_major} 次，應恰 1 次"
            "（0 次＝非 Windows 短路被移除，DEF-101-766 回歸）"
        )
    if n_pathext != 1:
        problems.append(
            f"pathext-count：程式碼裡 `{_PATHEXT_EXPR}` 出現 {n_pathext} 次，應恰 1 次"
            "（本鎖以它為 Windows-only 過濾的錨點，數目變了即需重新錨定）"
        )
    if _ORDERED_HOST_TEST not in code:
        problems.append(
            f"host-test-order：主機判定式必須逐字為 `{_ORDERED_HOST_TEST}`——"
            "`$IsWindows` 在 PS 5.1 未定義，必須先由版本比較短路擋掉"
        )
    if _NON_WIN_GUARD not in code:
        problems.append(f"guard-missing：找不到非 Windows 短路 `{_NON_WIN_GUARD}`")
    elif n_pathext >= 1:
        guard_at, pathext_at = code.index(_NON_WIN_GUARD), code.index(_PATHEXT_EXPR)
        if guard_at > pathext_at:
            problems.append(
                "guard-after-pathext：非 Windows 短路落在 PATHEXT 過濾**之後**＝等於沒修"
                "（POSIX 上 PATHEXT 不存在，過濾會先把所有候選濾光）"
            )
        elif "return" not in code[guard_at:pathext_at]:
            problems.append(
                "guard-does-not-return：短路區段內沒有 return，控制流仍會落進 PATHEXT 過濾"
            )
    return problems


def _resolve_harness(body: str, major: int, is_windows: bool | None,
                     cand: str, expected: Path) -> str:
    """生產函式原封搬進 harness，只把蓋不掉的版本運算式換成可設定的 `$FakePsMajor`。

    `is_windows=None`＝模擬 PS 5.1（該變數在 5.1 根本不存在，刻意不定義它才忠實）。
    子行程只吐 ASCII 的 `KEY=VALUE`：路徑比對在 PowerShell 端做完，回程不帶非 ASCII，
    本鎖因此不必先排除「回程編碼」這個與待驗缺陷無關的變因。
    """
    prelude = [f"{_PS_MAJOR_FAKE} = {major}"]
    if is_windows is not None:
        prelude.append("$IsWindows = $" + ("true" if is_windows else "false"))
    return (
        "\n".join(prelude) + "\n"
        + body.replace(_PS_MAJOR_EXPR, _PS_MAJOR_FAKE) + "\n"
        + f"$r = {_RESOLVE_FN} -CandidateName '{cand}'\n"
        + "'PATHEXT_LEN=' + $env:PATHEXT.Length\n"
        + "'RESULT_NULL=' + ($null -eq $r)\n"
        + f"'IS_FIXTURE=' + ($r -eq '{expected}')\n"
    )


def _production_resolve_body() -> str:
    return slice_ps_function(_GUARD_PS1_PATH.read_text(encoding="utf-8-sig"), _RESOLVE_FN)


@unittest.skipUnless(
    _ps_windows_with_engine(),
    "[WINDOWS-NATIVE-ONLY] 需要 Windows 平台 ＋ PowerShell 引擎（語意③）：本鎖的負控靠**真實**"
    "PATHEXT 語意——在沒有 PATHEXT 的平台上，負控會因為變數缺席而綠，而不是因為過濾"
    "生效才綠，等於量不到東西。跨平台備援＝TestResolveNativeExecutableShortCircuitOrder",
)
class TestResolveNativeExecutableNonWindowsBranch(unittest.TestCase):
    """行為鎖：同一支生產函式，只換平台判定的兩個輸入，四種平台各自的裁決都要對。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(_rmtree_force, self.tmp)
        self.assertNotIn(
            "'", str(self.tmp),
            "載具故障：暫存路徑含單引號，會剖壞 harness 內的 PowerShell 單引號字串",
        )
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        # 無副檔名候選＝POSIX 執行檔的形狀（也正是 DEF-101-759 那支 pyenv-win shim 的
        # 形狀）：Windows 分支必須淘汰它，非 Windows 分支必須接受它。同一個候選在兩種
        # 平台下裁決相反，正是本組鎖唯一需要的變因。
        (self.bin / "fakepy").write_text("#!/bin/sh\nexit 0\n", encoding="ascii")
        # `.cmd` 候選＝正控用：證明 Windows 分支本身沒壞、PATHEXT 確實有值。
        (self.bin / "fakecmd.cmd").write_text(
            "@echo off\r\nexit /b 0\r\n", encoding="ascii", newline="")
        self.ps = _ps_production_engine()
        # System32 不可省（`.cmd` 需 cmd.exe 解譯）；取自 `ComSpec` 而非寫死磁碟機路徑
        # ——後者會被 test_platform_neutral_paths.py 的假路徑鎖攔下。
        comspec = os.environ.get("ComSpec", "")
        extra = [os.path.dirname(comspec)] if comspec else []
        self.env = dict(os.environ)
        self.env["PATH"] = os.pathsep.join([str(self.bin), *extra])
        self.body = _production_resolve_body()

    def _probe(self, major: int, is_windows: bool | None,
               cand: str, expected_name: str) -> dict[str, str]:
        script = self.tmp / f"harness_{major}_{is_windows}_{cand}.ps1"
        # BOM 是刻意的：函式本體帶中文 WHY 註解，PS 5.1 讀無 BOM 的 UTF-8 會當成 ANSI
        # （本機 CP950），註解位元組被重解讀，最壞情況吐出引號把腳本剖壞
        # （同 tools/tests/test_ps1_bom.py 守的那件事）。
        script.write_text(
            _resolve_harness(self.body, major, is_windows, cand, self.bin / expected_name),
            encoding="utf-8-sig",
        )
        proc = subprocess.run(
            [self.ps, "-NoProfile", "-File", str(script)], env=self.env,
            capture_output=True, encoding="utf-8", errors="replace", timeout=180,
        )
        kv = _parse_kv(proc.stdout)
        for key in ("PATHEXT_LEN", "RESULT_NULL", "IS_FIXTURE"):
            self.assertIn(
                key, kv,
                f"載具故障：子行程未回報 {key}（不得當成通過）\n"
                f"rc={proc.returncode}\nstdout={proc.stdout!r}\nstderr={proc.stderr!r}",
            )
        self.assertNotEqual(
            kv["PATHEXT_LEN"], "0",
            "載具故障：子行程的 $env:PATHEXT 是空的——Windows 分支此刻會濾光所有候選，"
            "負控會因為載具壞掉而綠",
        )
        return kv

    def test_harness_is_a_faithful_copy_of_production(self) -> None:
        """載具自證：harness 與生產函式只差那一個替身，其餘逐字相同。

        沒有這一支，下面四支量的可能是一份被改寫過的副本——那就退化成「測試在測自己
        寫的 PowerShell」，與 ADR-XPLAT-002 §3.2 拒斥的字面比對型 parity 同一個病。
        """
        code = ps_code_only(self.body)
        self.assertEqual(
            code.count(_PS_MAJOR_EXPR), 1,
            f"生產函式裡 `{_PS_MAJOR_EXPR}` 不是恰 1 次——替身替換會失準，本組鎖需重新錨定",
        )
        self.assertEqual(
            code.count("$IsWindows"), 1,
            "生產函式裡 `$IsWindows` 不是恰 1 次——harness 的賦值可能罩不住全部讀取點",
        )
        harness = _resolve_harness(self.body, 7, False, "fakepy", self.bin / "fakepy")
        self.assertIn(_RESOLVE_FN, harness)
        self.assertNotIn(
            _PS_MAJOR_EXPR, harness,
            "harness 內仍留著讀不到的 `$PSVersionTable`——替身沒生效，四支行為斷言會全部"
            "只量到 PS 5.1 那一種平台",
        )
        self.assertEqual(
            ps_code_only(harness).count(_PS_MAJOR_FAKE), 2,
            "替身在程式碼裡應恰出現 2 次（harness 前置賦值 1 ＋ 函式本體被替換的 1）",
        )

    def test_windows_branch_still_rejects_extensionless_candidate(self) -> None:
        """DEF-101-759 不得因本次修復而回歸：PS 5.1 下無副檔名候選仍必須被淘汰。"""
        kv = self._probe(5, None, "fakepy", "fakepy")
        self.assertEqual(
            kv["RESULT_NULL"], "True",
            "PS 5.1 下無副檔名候選竟被接受——DEF-101-759 回歸（`&` 會對它回退 "
            "ShellExecute 並彈出「你要如何開啟這個檔案？」對話框，無人值守環境直接掛住）",
        )

    def test_windows_branch_positive_control_accepts_pathext_candidate(self) -> None:
        """正控（鏡子自證）：Windows 分支本身是活的，上一支的 $null 才歸因得了過濾。"""
        kv = self._probe(5, None, "fakecmd", "fakecmd.cmd")
        self.assertEqual(
            kv["IS_FIXTURE"], "True",
            "PS 5.1 下連 `.cmd` 候選都解析不到——Windows 分支或 fixture PATH 壞了，"
            f"此刻整組鎖零鑑別力（kv={kv}）",
        )

    def test_ps_core_on_non_windows_falls_back_to_first_application(self) -> None:
        """本體（DEF-101-766 的修復）：PS Core 非 Windows 必須跳過 PATHEXT 過濾。"""
        kv = self._probe(7, False, "fakepy", "fakepy")
        self.assertEqual(
            kv["IS_FIXTURE"], "True",
            "PS Core 在非 Windows 平台上仍照 PATHEXT 過濾 ⇒ POSIX 執行檔（無副檔名）"
            "全被淘汰 ⇒ Get-PythonGeMin 恆回 $null ⇒ macos-compat-ci 與 "
            f"root-infra-ci(ubuntu) 必紅（DEF-101-766 回歸；kv={kv}）",
        )

    def test_ps_core_on_windows_keeps_windows_semantics(self) -> None:
        """修復不得過度：PS Core 跑在 Windows 上仍要走 PATHEXT 過濾。

        少了這一支，把短路寫成「只要 Major >= 6 就跳過過濾」也會全綠——那會讓裝了
        pwsh 7 的 Windows 開發機重新踩回 DEF-101-759 的 ShellExecute 對話框。
        """
        kv = self._probe(7, True, "fakepy", "fakepy")
        self.assertEqual(
            kv["RESULT_NULL"], "True",
            "PS Core 跑在 Windows 上竟跳過了 PATHEXT 過濾——短路的條件寫成只看版本、"
            f"沒看 `$IsWindows`（kv={kv}）",
        )


def _real_pwsh7() -> str | None:
    """真 pwsh 7 的路徑（缺席即 None）。走 `_ps_engine` SSOT 的 `available_engines()`，
    **不**在此行內 `shutil.which("pwsh")`——那正是 `test_ps_engine_ssot.py` 的反增生鎖
    在擋的形態（DEF-101-509／E-A-03 家族）。"""
    return _ps_available_engines().get("pwsh")


@unittest.skipUnless(
    os.name == "nt" and _real_pwsh7() is not None,
    "[WINDOWS-NATIVE-ONLY] 需要 Windows 平台 ＋ **真** pwsh 7 行程：本組的全部價值就是"
    "「不用 harness 替身」，缺 pwsh 7 時沒有替代載具（harness 版＝"
    "TestResolveNativeExecutableNonWindowsBranch）",
)
class TestResolveNativeExecutableOnRealPwsh7(unittest.TestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestResolveNativeExecutableOnRealPwsh7 WHY〉節。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(_rmtree_force, self.tmp)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        (self.bin / "fakepy").write_text("#!/bin/sh\nexit 0\n", encoding="ascii")
        (self.bin / "fakecmd.cmd").write_text(
            "@echo off\r\nexit /b 0\r\n", encoding="ascii", newline="")
        comspec = os.environ.get("ComSpec", "")
        extra = [os.path.dirname(comspec)] if comspec else []
        self.env = dict(os.environ)
        self.env["PATH"] = os.pathsep.join([str(self.bin), *extra])
        self.ps = _real_pwsh7()

    def _probe(self, cand: str, expected_name: str) -> dict[str, str]:
        """把**未經任何替換**的生產函式交給真 pwsh 7 執行。"""
        body = _production_resolve_body()
        self.assertNotIn(
            _PS_MAJOR_FAKE, body,
            "生產碼裡出現了 harness 的替身變數——本組的前提是「不做任何替換」",
        )
        script = self.tmp / f"real_pwsh7_{cand}.ps1"
        script.write_text(
            body + "\n"
            + f"$r = {_RESOLVE_FN} -CandidateName '{cand}'\n"
            + "'PS_MAJOR=' + $PSVersionTable.PSVersion.Major\n"
            + "'IS_WINDOWS=' + $IsWindows\n"  # ps7-ok: 本組刻意只在 pwsh 7 上跑（skipUnless 已守）
            + "'RESULT_NULL=' + ($null -eq $r)\n"
            + f"'IS_FIXTURE=' + ($r -eq '{self.bin / expected_name}')\n",
            encoding="utf-8-sig",
        )
        proc = subprocess.run(
            [self.ps, "-NoProfile", "-File", str(script)], env=self.env,
            capture_output=True, encoding="utf-8", errors="replace", timeout=180,
        )
        kv = _parse_kv(proc.stdout)
        for key in ("PS_MAJOR", "IS_WINDOWS", "RESULT_NULL", "IS_FIXTURE"):
            self.assertIn(
                key, kv,
                f"載具故障：真 pwsh 7 子行程未回報 {key}（不得當成通過）\n"
                f"rc={proc.returncode}\nstdout={proc.stdout!r}\nstderr={proc.stderr!r}",
            )
        return kv

    def test_real_pwsh7_actually_enters_the_major_ge_6_branch(self) -> None:
        """載具自證：真的是 PS 7 在跑（否則下面兩支量的還是 5.1 那一格）。"""
        kv = self._probe("fakecmd", "fakecmd.cmd")
        self.assertGreaterEqual(
            int(kv["PS_MAJOR"]), 6,
            f"用來跑本組的引擎不是 PS 6+（kv={kv}）——`Major >= 6` 分支根本沒被觸及，"
            "整組退化成第二份 5.1 測試",
        )
        self.assertEqual(
            kv["IS_WINDOWS"], "True",
            f"真 pwsh 7 在 Windows 上回報 $IsWindows 非 True（kv={kv}）——"
            "本組的劃界前提（那一格結構性不可達）已不成立，請重讀類別 docstring",
        )

    def test_real_pwsh7_on_windows_keeps_pathext_filtering(self) -> None:
        """本體：PS 7 跑在 Windows 上**仍**必須照 PATHEXT 過濾（不得因版本短路而放行）。

        這是 harness 鎖唯一無法真正證明的那一半：harness 把版本運算式換成替身，
        它證明的是「副本在 major=7 時的行為」；本支證明真引擎在真 `$PSVersionTable`
        下走同一條路。若有人把短路條件寫成「只要 Major >= 6 就跳過過濾」，
        裝了 pwsh 7 的 Windows 開發機會重新踩回 `DEF-101-759` 的 ShellExecute 對話框，
        而本支會在那一刻紅。
        """
        kv = self._probe("fakepy", "fakepy")
        self.assertEqual(
            kv["RESULT_NULL"], "True",
            f"真 pwsh 7 在 Windows 上接受了無副檔名候選（kv={kv}）——版本短路把 Windows "
            "語意一起跳過了（DEF-101-759 回歸路徑）",
        )

    def test_real_pwsh7_positive_control_accepts_pathext_candidate(self) -> None:
        """正控（鏡子自證）：真 pwsh 7 下 Windows 分支本身是活的，上一支的 $null 才歸因得了過濾。"""
        kv = self._probe("fakecmd", "fakecmd.cmd")
        self.assertEqual(
            kv["IS_FIXTURE"], "True",
            f"真 pwsh 7 下連 `.cmd` 候選都解析不到（kv={kv}）——引擎或 fixture PATH 壞了，"
            "此刻整組鎖零鑑別力",
        )


class TestResolveNativeExecutableShortCircuitOrder(unittest.TestCase):
    """WHY 全文搬至 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok
    dev_start TestResolveNativeExecutableShortCircuitOrder WHY〉節。"""

    def test_production_short_circuit_is_present_and_ordered(self) -> None:
        problems = non_windows_short_circuit_problems(_production_resolve_body())
        self.assertEqual(
            problems, [],
            f"{_GUARD_PS1_PATH.name}::{_RESOLVE_FN} 的非 Windows 短路不合格：\n  "
            + "\n  ".join(problems),
        )

    def test_scanner_flags_each_degradation_by_construction(self) -> None:
        """鑑別力自檢：三種退化各自被判出對應問題碼，否則上面那支是恆綠的。

        退化樣本**由生產原始碼實地推導**（不是手寫的假 .ps1）——手寫樣本只證明掃描器
        看得懂自己造的形狀，證明不了它看得懂生產碼那個形狀。
        """
        body = _production_resolve_body()
        head, pathext_line, tail = "  $isWindowsHost =", "  $exts = @(", "  return $null\n}"
        for anchor in (head, pathext_line):
            self.assertIn(anchor, body, f"退化樣本錨點 `{anchor}` 已不在生產碼中，請重新錨定")
        self.assertTrue(body.rstrip().endswith(tail), f"函式結尾不再是 `{tail}`，請重新錨定")
        block = body[body.index(head) : body.index(pathext_line)]
        removed = body[: body.index(head)] + body[body.index(pathext_line) :]
        moved = removed.rstrip()[: -len(tail)] + block + tail + "\n"
        swapped = body.replace(
            _ORDERED_HOST_TEST, "$IsWindows -or ($PSVersionTable.PSVersion.Major -lt 6)")
        cases = {
            "clean": (body, []),
            # ① 整段短路被刪掉＝退回修復前的生產碼形狀
            "removed": (removed, ["version-probe-count", "host-test-order", "guard-missing"]),
            # ② 短路還在、但被搬到 PATHEXT 過濾之後（行為鎖對這種改法全綠）
            "moved_after_pathext": (moved, ["guard-after-pathext"]),
            # ③ `-or` 兩側對調＝PS 5.1 上先讀未定義變數
            "swapped_host_test": (swapped, ["host-test-order"]),
        }
        got = {
            label: [p.split("：", 1)[0] for p in non_windows_short_circuit_problems(src)]
            for label, (src, _) in cases.items()
        }
        self.assertEqual(
            got, {label: want for label, (_, want) in cases.items()},
            "順序掃描器的分類與構造預期不符——判準已被放寬到看不見對應退化",
        )


if __name__ == "__main__":
    unittest.main()
