#!/usr/bin/env python3
"""`tools/install_statusline.py`（含其復用的 `statusline_context_feed.build_command()`／
`resolve_windows_interpreter()`／`_quote_token()`）的回歸鎖（R158 P5）。 round-label-ok
WHY：安裝器只 touch `statusLine` 鍵，每條控制組都配「其餘鍵是否原樣保留」的注入組；
`test_statusline_context_feed.py` 屬另一包界外檔案（不可改動），故新純函式改在本檔測。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TOOLS_DIR = _REPO_ROOT / "tools"
_MOD_PATH = _TOOLS_DIR / "install_statusline.py"

sys.path.insert(0, str(_TOOLS_DIR))
import install_statusline as installer  # noqa: E402
import statusline_context_feed as feed  # noqa: E402


def _run_cli(argv: list[str], home: Path) -> tuple[int, str, str]:
    """子行程等級呼叫 CLI；`HOME` 覆寫成 tempdir，絕不動真實使用者設定檔。"""
    env = {**os.environ, "HOME": str(home)}
    proc = subprocess.run([sys.executable, str(_MOD_PATH), *argv], capture_output=True,
                           text=True, encoding="utf-8", env=env, timeout=15, check=False)
    return proc.returncode, proc.stdout, proc.stderr


def _leading_json(text: str) -> object:
    """只解析輸出開頭那一段 JSON（安裝成功時後面還接著親驗清單純文字）。"""
    return json.JSONDecoder().raw_decode(text)[0]


class QuoteTokenTest(unittest.TestCase):
    def test_no_space_passthrough(self) -> None:
        got = feed._quote_token("/a/b/c")
        self.assertEqual(got, "/a/b/c")  # posix-abs-ok: 純字串操作，不經 Path 轉換

    def test_space_gets_wrapped_in_double_quotes(self) -> None:
        got = feed._quote_token("/a/b c/d")
        self.assertEqual(got, '"/a/b c/d"')


class ResolveWindowsInterpreterTest(unittest.TestCase):
    """純函式：呼叫端決定何時觸發，本身不看 `os.name`。"""

    def test_returns_pythonw_when_present_alongside_interpreter(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            python_exe = d / "python.exe"
            python_exe.write_text("", encoding="utf-8")
            pythonw_exe = d / "pythonw.exe"
            pythonw_exe.write_text("", encoding="utf-8")
            self.assertEqual(feed.resolve_windows_interpreter(python_exe), pythonw_exe)

    def test_falls_back_to_original_when_pythonw_absent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            python_exe = d / "python.exe"
            python_exe.write_text("", encoding="utf-8")
            self.assertEqual(feed.resolve_windows_interpreter(python_exe), python_exe)


class BuildCommandTest(unittest.TestCase):
    def test_no_quotes_when_no_space_matches_existing_unquoted_shape(self) -> None:
        """姊妹檔 `test_statusline_context_feed.py::SettingsSnippetTest`（R158 P5 round-label-ok
        不可改動）用 `command.split(" ", 1)` 假設純空白分隔、無引號——本 checkout
        路徑無空白，`build_command()` 對這種輸入必須維持該舊形態。"""
        cmd = feed.build_command(Path("/a/b/python3"), Path("/a/b/script.py"))
        want = "/a/b/python3 /a/b/script.py"
        self.assertEqual(cmd, want)

    def test_quotes_tokens_that_contain_a_space(self) -> None:
        """含空白路徑（如 Windows OneDrive）才需要保護：正斜線＋雙引號，兩殼皆安全。"""
        python_path = Path("/Users/x/One Drive/venv/bin/python3")
        script_path = Path("/Users/x/One Drive/repo/tools/statusline_context_feed.py")
        cmd = feed.build_command(python_path, script_path)
        self.assertEqual(
            cmd,
            '"/Users/x/One Drive/venv/bin/python3" '
            '"/Users/x/One Drive/repo/tools/statusline_context_feed.py"',
        )
        self.assertNotIn("\\", cmd, "要求 POSIX 正斜線")

    def test_swaps_to_pythonw_when_os_name_is_nt(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            python_exe = d / "python.exe"
            python_exe.write_text("", encoding="utf-8")
            pythonw_exe = d / "pythonw.exe"
            pythonw_exe.write_text("", encoding="utf-8")
            script = d / "statusline_context_feed.py"
            script.write_text("", encoding="utf-8")
            with mock.patch("statusline_context_feed.os.name", "nt"):
                cmd = feed.build_command(python_exe, script)
        self.assertIn(pythonw_exe.as_posix(), cmd)
        self.assertNotIn(python_exe.as_posix(), cmd)

    def test_keeps_python_on_posix_even_if_pythonw_exists(self) -> None:
        """`os.name` 不是 `"nt"` 時（本測試環境即是）不觸發替換——即使同目錄剛好
        有一支叫 `pythonw.exe` 的檔案，也不該被誤用。"""
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            python_exe = d / "python3"
            python_exe.write_text("", encoding="utf-8")
            pythonw_exe = d / "pythonw.exe"
            pythonw_exe.write_text("", encoding="utf-8")
            script = d / "statusline_context_feed.py"
            script.write_text("", encoding="utf-8")
            cmd = feed.build_command(python_exe, script)
        self.assertIn(python_exe.as_posix(), cmd)
        self.assertNotIn("pythonw.exe", cmd)


class SettingsPathTest(unittest.TestCase):
    def test_uses_dot_claude_settings_json_under_home(self) -> None:
        home = Path("/tmp/fake-home-r158")
        self.assertEqual(installer.settings_path(home), home / ".claude" / "settings.json")


class LoadSettingsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)

    def test_missing_file_returns_empty_dict(self) -> None:
        self.assertEqual(installer.load_settings(installer.settings_path(self.home)), {})

    def test_blank_file_returns_empty_dict(self) -> None:
        path = installer.settings_path(self.home)
        path.parent.mkdir(parents=True)
        path.write_text("   \n", encoding="utf-8")
        self.assertEqual(installer.load_settings(path), {})

    def test_non_object_top_level_raises(self) -> None:
        path = installer.settings_path(self.home)
        path.parent.mkdir(parents=True)
        path.write_text("[1, 2, 3]", encoding="utf-8")
        with self.assertRaises(ValueError):
            installer.load_settings(path)


class InstallUninstallStatusTest(unittest.TestCase):
    """核心行為：全程以 tempdir 當 `home`，絕不動真實 `~/.claude/settings.json`。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)
        self.path = installer.settings_path(self.home)

    def _seed(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def test_install_onto_empty_home_creates_file_with_status_line(self) -> None:
        report = installer.install(home=self.home)
        self.assertEqual(report["action"], "installed")
        self.assertIsNone(report["backup"], "全新檔案不該有備份")
        written = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(written["statusLine"], installer.desired_status_line())

    def test_install_preserves_other_keys_and_backs_up(self) -> None:
        self._seed({"otherKey": {"a": 1}, "model": "x"})
        report = installer.install(home=self.home)
        self.assertEqual(report["action"], "installed")
        backup = Path(report["backup"])
        self.assertTrue(backup.is_file())
        self.assertEqual(
            json.loads(backup.read_text(encoding="utf-8")),
            {"otherKey": {"a": 1}, "model": "x"},
        )
        written = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(written["otherKey"], {"a": 1})
        self.assertEqual(written["model"], "x")
        self.assertIn("statusLine", written)

    def test_second_install_is_idempotent_no_second_backup(self) -> None:
        self._seed({"otherKey": 1})
        installer.install(home=self.home)
        backups_after_first = sorted(self.path.parent.glob("settings.json.bak-*"))
        self.assertEqual(len(backups_after_first), 1)
        report2 = installer.install(home=self.home)
        self.assertEqual(report2["action"], "noop")
        backups_after_second = sorted(self.path.parent.glob("settings.json.bak-*"))
        self.assertEqual(backups_after_first, backups_after_second, "冪等安裝不得新增備份")

    def test_dry_run_does_not_write_or_backup(self) -> None:
        self._seed({"otherKey": 1})
        report = installer.install(home=self.home, dry_run=True)
        self.assertEqual(report["action"], "would-install")
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), {"otherKey": 1})
        self.assertEqual(list(self.path.parent.glob("*.bak-*")), [])

    def test_uninstall_removes_key_preserves_others(self) -> None:
        installer.install(home=self.home)
        data = json.loads(self.path.read_text(encoding="utf-8"))
        data["otherKey"] = "keep-me"
        self.path.write_text(json.dumps(data), encoding="utf-8")
        report = installer.uninstall(home=self.home)
        self.assertEqual(report["action"], "uninstalled")
        written = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertNotIn("statusLine", written)
        self.assertEqual(written["otherKey"], "keep-me")
        self.assertTrue(Path(report["backup"]).is_file())

    def test_uninstall_when_not_installed_is_noop(self) -> None:
        self._seed({"otherKey": 1})
        report = installer.uninstall(home=self.home)
        self.assertEqual(report["action"], "noop")
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), {"otherKey": 1})

    def test_uninstall_dry_run_does_not_write(self) -> None:
        installer.install(home=self.home)
        report = installer.uninstall(home=self.home, dry_run=True)
        self.assertEqual(report["action"], "would-uninstall")
        written = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertIn("statusLine", written, "dry-run 不該真的移除")

    def test_status_reports_installed_and_matches(self) -> None:
        installer.install(home=self.home)
        report = installer.status(home=self.home)
        self.assertTrue(report["installed"])
        self.assertTrue(report["matches_current_checkout"])
        self.assertTrue(report["settings_file_exists"])

    def test_status_reports_not_installed_on_fresh_home(self) -> None:
        report = installer.status(home=self.home)
        self.assertFalse(report["installed"])
        self.assertFalse(report["matches_current_checkout"])
        self.assertFalse(report["settings_file_exists"])

    def test_write_settings_has_no_tmp_leftover(self) -> None:
        payload = {"otherKey": 1, "statusLine": installer.desired_status_line()}
        installer.write_settings(self.path, payload)
        self.assertEqual([p for p in self.path.parent.iterdir() if p != self.path], [])
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), payload)


class CliSubprocessTest(unittest.TestCase):
    """全程走真的子行程＋真的 argv 解析（`main()` 那一層），`HOME` 覆寫成 tempdir。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)

    def test_install_status_uninstall_status_round_trip(self) -> None:
        rc, out, err = _run_cli([], self.home)
        self.assertEqual(rc, 0, err)
        doc = _leading_json(out)
        self.assertEqual(doc["action"], "installed")
        self.assertIn("親眼確認", out, "安裝成功後應印出親驗清單")

        rc, out, err = _run_cli(["--status"], self.home)
        self.assertEqual(rc, 0, err)
        doc = _leading_json(out)
        self.assertTrue(doc["installed"])
        self.assertTrue(doc["matches_current_checkout"])

        rc, out, err = _run_cli(["--uninstall"], self.home)
        self.assertEqual(rc, 0, err)
        doc = _leading_json(out)
        self.assertEqual(doc["action"], "uninstalled")

        rc, out, err = _run_cli(["--status"], self.home)
        self.assertEqual(rc, 1, "解除安裝後 --status 應回 rc=1（尚未安裝）")
        doc = _leading_json(out)
        self.assertFalse(doc["installed"])

    def test_dry_run_leaves_no_settings_file_on_fresh_home(self) -> None:
        rc, out, err = _run_cli(["--dry-run"], self.home)
        self.assertEqual(rc, 0, err)
        doc = _leading_json(out)
        self.assertEqual(doc["action"], "would-install")
        self.assertFalse((self.home / ".claude" / "settings.json").exists())

    def test_print_command_outputs_two_forward_slash_tokens(self) -> None:
        rc, out, err = _run_cli(["--print-command"], self.home)
        self.assertEqual(rc, 0, err)
        line = out.strip()
        self.assertNotIn("\\", line, "要求 POSIX 正斜線")
        self.assertEqual(len(line.split(" ")), 2, "本 checkout 路徑無空白，應恰為兩個 token")

    def test_unknown_flag_is_rejected_not_silently_ignored(self) -> None:
        rc, _out, _err = _run_cli(["--bogus-flag-xyz-not-a-real-flag"], self.home)
        self.assertNotEqual(rc, 0, "未知旗標必須拒收，不得靜默改跑預設路徑")


if __name__ == "__main__":
    unittest.main()
