#!/usr/bin/env python3
"""tools/lib/clean_venv_carrier.py 的單元測試（DEF-200-306；驗證鏡子自身要被驗證）。

全程 `subprocess.run`／`shutil.rmtree` 皆 patch，不真的建 venv、不裝套件、不碰
磁碟上的真實目錄（`cleanup()` 對不存在的路徑直接視為成功，見其實作）。

執行：python -m pytest tools/tests/test_clean_venv_carrier.py -q
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_REPO_ROOT = Path(__file__).resolve().parents[2]

# 合成路徑一律**相對**、不寫 POSIX 絕對字面：test_platform_neutral_paths.py 的
# TestNoPosixAbsPathLiteralInAsserts 對斷言區塊內的 `/tmp`／`/fake` 字面判紅（鐵律三——
# 那種字面在 Windows 上不是同一個路徑）。這些替身只餵給被 patch 掉的 subprocess，
# 從不落盤，相對與絕對對測試語意零差別。
_FAKE_ROOT = Path("fake-root")
_FAKE_VENV_DIR = _FAKE_ROOT / "autoclaude_cleanvenv_20260101T000000Z"
_FAKE_PY = Path("fake") / "venv" / "python"
_FAKE_REPO = Path("fake") / "repo"
_FAKE_PY_SHORT = Path("fake") / "py"


def _carrier():
    """延後 import 唯一真相源（同鄰檔 test_single_venv_identity.py 的既有慣例：
    不進 import 期路徑，且每次呼叫都重新解析，避免測試間 sys.path 順序互相干擾）。
    """
    sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
    import clean_venv_carrier  # noqa: PLC0415

    return clean_venv_carrier


def _ok_run(*_a, **_k):
    """萬用替身：模擬 subprocess.run 成功（rc=0，stdout 空）。"""
    result = MagicMock()
    result.returncode = 0
    result.stdout = ""
    return result


class CreateCleanVenvTest(unittest.TestCase):
    """(a) 建 venv 的 argv 形態；(g) 目錄名含 cleanvenv。"""

    def test_venv_creation_argv_and_naming(self):
        cvc = _carrier()
        with patch.object(cvc.subprocess, "run", side_effect=_ok_run) as mock_run:
            target = cvc.create_clean_venv(base_temp_dir=_FAKE_ROOT)

        assert "cleanvenv" in target.name
        venv_calls = [
            c for c in mock_run.call_args_list if "venv" in c.args[0] and "-m" in c.args[0]
        ]
        assert len(venv_calls) == 1
        argv = venv_calls[0].args[0]
        assert argv[1:3] == ["-m", "venv"]
        assert argv[3] == str(target)

    def test_low_version_base_interpreter_fails_loud(self):
        """基底直譯器版本探針回非零 rc（< 3.11）→ 立即 raise，不建 venv。"""
        cvc = _carrier()

        def _low_version_run(argv, **kwargs):
            result = MagicMock()
            result.returncode = 1 if "-c" in argv else 0
            result.stdout = ""
            return result

        with patch.object(cvc.subprocess, "run", side_effect=_low_version_run) as mock_run:
            with self.assertRaises(RuntimeError):
                cvc.create_clean_venv(base_temp_dir=_FAKE_ROOT)
        # 版本探針之後不應再有第二次呼叫（venv 建立），因為已經 raise。
        assert mock_run.call_count == 1


class ProbePgExtrasTest(unittest.TestCase):
    """(b) 探針輸出含 PRESENT → raise；全 ABSENT → 不 raise。"""

    def test_present_raises(self):
        cvc = _carrier()
        result = MagicMock()
        result.stdout = "psycopg2 PRESENT\nsqlalchemy ABSENT\n"
        with patch.object(cvc.subprocess, "run", return_value=result):
            with self.assertRaises(cvc.CleanVenvContaminatedError):
                cvc.assert_pg_extras_absent(_FAKE_PY)

    def test_all_absent_does_not_raise(self):
        cvc = _carrier()
        result = MagicMock()
        result.stdout = "psycopg2 ABSENT\nsqlalchemy ABSENT\n"
        with patch.object(cvc.subprocess, "run", return_value=result):
            cvc.assert_pg_extras_absent(_FAKE_PY)  # 不應拋例外


class RunOnboardingSyncTest(unittest.TestCase):
    """(c) 回填 argv 不含 --allow-pg-extras 且含 --write --with-slow。"""

    def test_argv_shape(self):
        cvc = _carrier()
        with patch.object(cvc.subprocess, "run", side_effect=_ok_run) as mock_run:
            rc = cvc.run_onboarding_sync(_FAKE_PY, _FAKE_REPO)
        assert rc == 0
        argv = mock_run.call_args.args[0]
        assert "--allow-pg-extras" not in argv
        assert "--write" in argv
        assert "--with-slow" in argv


class MainDryRunTest(unittest.TestCase):
    """(d) main(["--dry-run"]) 不呼叫 subprocess.run 且 rc=0。"""

    def test_dry_run_never_touches_subprocess(self):
        cvc = _carrier()
        with patch.object(cvc.subprocess, "run") as mock_run:
            rc = cvc.main(["--dry-run"])
        assert rc == 0
        mock_run.assert_not_called()


class MainCleanupInvariantTest(unittest.TestCase):
    """(e) 中途 raise 時 cleanup 仍被呼叫一次（finally）；--keep 時不呼叫。"""

    def test_cleanup_called_once_when_probe_raises(self):
        cvc = _carrier()
        fake_venv_dir = _FAKE_VENV_DIR
        with (
            patch.object(cvc, "create_clean_venv", return_value=fake_venv_dir),
            patch.object(cvc.platform_utils, "venv_python_path", return_value=_FAKE_PY_SHORT),
            patch.object(
                cvc,
                "install_deps",
                return_value=MagicMock(returncode=0),
            ),
            patch.object(
                cvc, "assert_pg_extras_absent", side_effect=cvc.CleanVenvContaminatedError("x")
            ),
            patch.object(cvc, "cleanup", return_value=True) as mock_cleanup,
        ):
            rc = cvc.main([])
        assert rc == 1
        mock_cleanup.assert_called_once_with(
            fake_venv_dir, is_windows=cvc.platform_utils.is_windows()
        )

    def test_keep_flag_skips_cleanup(self):
        cvc = _carrier()
        fake_venv_dir = _FAKE_VENV_DIR
        with (
            patch.object(cvc, "create_clean_venv", return_value=fake_venv_dir),
            patch.object(cvc.platform_utils, "venv_python_path", return_value=_FAKE_PY_SHORT),
            patch.object(cvc, "install_deps", return_value=MagicMock(returncode=0)),
            patch.object(cvc, "assert_pg_extras_absent", return_value=None),
            patch.object(cvc, "run_onboarding_sync", return_value=0),
            patch.object(cvc, "cleanup") as mock_cleanup,
        ):
            rc = cvc.main(["--keep"])
        assert rc == 0
        mock_cleanup.assert_not_called()


class CleanupFailureTest(unittest.TestCase):
    """(f) 刪除失敗時印出含目錄路徑的刪除指令且 rc 非零。"""

    def test_rmtree_failure_prints_copyable_command_and_returns_false(self):
        cvc = _carrier()
        venv_dir = _FAKE_VENV_DIR
        with (
            patch.object(cvc.Path, "exists", return_value=True),
            patch("shutil.rmtree", side_effect=OSError("locked")),
        ):
            with patch("builtins.print") as mock_print:
                ok = cvc.cleanup(venv_dir, is_windows=True)
        assert ok is False
        printed = "\n".join(str(c.args[0]) for c in mock_print.call_args_list if c.args)
        assert str(venv_dir) in printed
        assert "Remove-Item" in printed

    def test_main_returns_nonzero_when_cleanup_fails(self):
        cvc = _carrier()
        fake_venv_dir = _FAKE_VENV_DIR
        with (
            patch.object(cvc, "create_clean_venv", return_value=fake_venv_dir),
            patch.object(cvc.platform_utils, "venv_python_path", return_value=_FAKE_PY_SHORT),
            patch.object(cvc, "install_deps", return_value=MagicMock(returncode=0)),
            patch.object(cvc, "assert_pg_extras_absent", return_value=None),
            patch.object(cvc, "run_onboarding_sync", return_value=0),
            patch.object(cvc, "cleanup", return_value=False),
        ):
            rc = cvc.main([])
        assert rc == 1


if __name__ == "__main__":
    unittest.main()
