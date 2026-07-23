"""`tools/lib/bash_probe_spec.py::PROBE_CMD` 真實行為契約鎖（R32 一審 SA/QA 交叉發現）。

WHY：三份 `usable_bash()`/`_usable_bash()` 消費者（`AISDLC_SDD/scripts/bash_probe.py`、
`tools/tests/test_pre_push_dispatcher.py`、`tools/tests/test_git_hooks_install_common.py`）
的既有測試全部用 `mock.patch.object(subprocess, "run")` 手填回傳值，只驗證了
「拿到給定 stdout 後如何比對」的分支邏輯，完全沒有驗證「`PROBE_CMD` 本身是否
真的依賴 coreutils（`dirname`）」這件事——R32 一審時 SA 與 QA 各自獨立用
bug-injection 把 `PROBE_CMD` 改回退化版（拿掉 `dirname`、只留 `echo`），三份
消費者共 43 個既有 case **全數維持綠燈**，證實這是裝飾性斷言缺口（DEF-101-275
的整個修復可被悄悄撤回而無測試發現）。本檔補上不經 mock 的真實行為鎖。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import bash_probe_spec as _spec  # noqa: E402

_BASH = shutil.which("bash")


class TestProbeCmdContentDependsOnCoreutils(unittest.TestCase):
    """資料層防線：PROBE_CMD 字面必須含 coreutils 呼叫，不能只剩 echo。"""

    def test_probe_cmd_literally_invokes_dirname(self) -> None:
        self.assertIn(
            "dirname",
            _spec.PROBE_CMD,
            "PROBE_CMD 已不含 dirname 呼叫——DEF-101-275 修復被悄悄撤回，"
            "退化為只驗 echo 存活（無法偵測缺 coreutils 的殘缺 bash）",
        )


@unittest.skipUnless(_BASH, "需要本機可用的 bash 執行真實行為驗證")
class TestProbeCmdRealSubprocessBehavior(unittest.TestCase):
    """行為層防線：不 mock subprocess，直接用真實 bash 執行 PROBE_CMD，
    以「PATH 缺 dirname」模擬 DEF-101-275 描述的殘缺 Git Bash 情境。
    """

    def _run_probe(self, path_env: str) -> subprocess.CompletedProcess:
        env = {"PATH": path_env}
        return subprocess.run(
            [_BASH, "-c", _spec.PROBE_CMD],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=15, env=env,
        )

    def test_fails_when_path_lacks_dirname(self) -> None:
        # 空 PATH：shell 內建 echo 仍可跑，但外部指令 dirname 解析不到 → 非 0。
        result = self._run_probe(path_env="")
        self.assertNotEqual(
            result.returncode, 0,
            f"PATH 缺 dirname 時 PROBE_CMD 應失敗，實際 rc=0，stdout={result.stdout!r}",
        )

    def test_succeeds_with_real_path(self) -> None:
        result = self._run_probe(path_env=os.environ.get("PATH", "/usr/bin:/bin"))
        lines = result.stdout.splitlines()
        self.assertEqual(result.returncode, 0)
        self.assertGreaterEqual(len(lines), 2)
        self.assertEqual(lines[0].strip(), _spec.PROBE_EXPECT_ECHO)
        self.assertEqual(lines[1].strip(), _spec.PROBE_EXPECT_DIRNAME)


@unittest.skipUnless(_BASH, "需要本機可用的 bash 驗證生產端到端 wiring")
class TestUsableBashEndToEndWithRestrictedPath(unittest.TestCase):
    """Wiring 層防線：不 mock subprocess.run，讓 `bash_probe.usable_bash()` 真的
    透過受限 PATH 的子行程呼叫 PROBE_CMD，證明生產程式碼真的把 PROBE_CMD 傳給
    subprocess 執行（而非測試替身各自獨立宣稱的行為）。
    """

    def setUp(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(repo_root / "AISDLC_SDD" / "scripts"))
        import bash_probe  # noqa: PLC0415
        self.bash_probe = bash_probe

    def test_usable_bash_rejects_candidate_when_path_lacks_dirname(self) -> None:
        real_bash = _BASH
        with mock.patch.object(
            self.bash_probe.shutil, "which",
            side_effect=lambda name: real_bash if name == "bash" else None,
        ), mock.patch.dict(os.environ, {"PATH": ""}, clear=True):
            result = self.bash_probe.usable_bash()
        self.assertIsNone(
            result,
            "PATH 缺 dirname 時 usable_bash() 應拒絕該候選並回傳 None，"
            "實際卻回傳可用路徑——生產端 wiring 未真正依賴 PROBE_CMD 的 coreutils 驗證",
        )

    def test_usable_bash_accepts_candidate_with_real_path(self) -> None:
        real_bash = _BASH
        real_path = os.environ.get("PATH", "/usr/bin:/bin")
        with mock.patch.object(
            self.bash_probe.shutil, "which",
            side_effect=lambda name: real_bash if name == "bash" else None,
        ), mock.patch.dict(os.environ, {"PATH": real_path}, clear=True):
            result = self.bash_probe.usable_bash()
        self.assertEqual(result, real_bash)


if __name__ == "__main__":
    unittest.main()
