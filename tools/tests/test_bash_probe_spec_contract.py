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
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import bash_probe_spec as _spec  # noqa: E402

_BASH = shutil.which("bash")


def usable_bash_with_probe_spy(
    bash_probe_module, path_env: str
) -> tuple[str | None, list[tuple[int, str]], list[OSError]]:
    """真跑生產端 `usable_bash()`，同時記錄它對 `subprocess.run` 的每一次呼叫結果。

    WHY（R60 A-01／DEF-101-531）：生產端 `bash_probe.usable_bash()` 的 `except
    Exception: continue`（`AISDLC_SDD/scripts/bash_probe.py:79-80`）把兩種語意
    完全不同的情況壓成同一個 `None`——
      ① 子行程真的起來、跑完 `PROBE_CMD` 而**驗活失敗** → 候選被正確拒絕（我們要驗的）；
      ② 子行程**根本沒起來**（`OSError`）→ 載具壞掉，對生產端 wiring 零資訊。
    只用 `assertIsNone(result)` 的測試無法分辨兩者，於是可以在 ② 之下長年假綠。
    本 helper 把兩種來源分流回傳，讓斷言端**必須**表態。

    回傳 `(result, completed, spawn_errors)`：
      `completed`    = `[(returncode, stdout), ...]`（子行程起來並跑完）
      `spawn_errors` = `[OSError, ...]`（`CreateProcess`／`execve` 失敗，載具壞掉）
    """
    real_bash = _BASH
    completed: list[tuple[int, str]] = []
    spawn_errors: list[OSError] = []
    real_run = subprocess.run

    def spy(*args, **kwargs):
        try:
            result = real_run(*args, **kwargs)
        except OSError as exc:
            spawn_errors.append(exc)
            raise
        completed.append((result.returncode, result.stdout or ""))
        return result

    with mock.patch.object(
        bash_probe_module.shutil, "which",
        side_effect=lambda name: real_bash if name == "bash" else None,
    ), mock.patch.dict(
        # 刻意**不用** `clear=True`：Windows 上清空整個 Win32 環境區塊會讓
        # `CreateProcess` 直接回 `[WinError 87] 參數錯誤`（本機實測
        # `GetEnvironmentStringsW` entries=0），子行程根本沒起來 → 上述來源②。
        os.environ, {"PATH": path_env},
    ), mock.patch.object(bash_probe_module.subprocess, "run", spy):
        result = bash_probe_module.usable_bash()
    return result, completed, spawn_errors


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
        # R60 A-01 修正載具：舊版用 `{"PATH": ""}` + `clear=True`，在 Windows 上**兩段都壞**——
        #   ① Windows 的 `os.environ["PATH"] = ""` 是「**刪除**該變數」而非「設為空字串」
        #      （本機實測：設完 `GetEnvironmentVariableW("PATH")` 回 0／ERROR_ENVVAR_NOT_FOUND），
        #      而子 MSYS bash 在**完全沒有 PATH** 時會自行合成 `/usr/local/bin:/usr/bin:...`
        #      → `dirname` 照樣找得到、驗活成功 → 本測試該紅（pytest 載具下實測就是紅的）；
        #   ② 再加 `clear=True` 清空整個環境區塊 → `CreateProcess` 回 `[WinError 87]`，
        #      子行程根本沒起來、`except Exception` 吞掉 → `None` → 誤綠（官方 unittest 閘門）。
        # 改用「PATH 指向一個真實存在但空無一物的目錄」：兩平台皆讓 bash 用得到 PATH 這個
        # 變數、卻找不到 `dirname`（本機實測 rc=127 / `dirname: command not found`）。
        with tempfile.TemporaryDirectory(prefix="probe_no_coreutils_") as empty_dir:
            result, completed, spawn_errors = usable_bash_with_probe_spy(
                self.bash_probe, empty_dir
            )
        self.assertFalse(
            spawn_errors,
            "載具故障（非生產端結論）：usable_bash() 的探測子行程根本沒起來"
            f"（{[f'{type(e).__name__}: {e}' for e in spawn_errors]}）——此時的 None 只代表"
            "本測試無法驗證任何事，不得當成『候選被正確拒絕』通過（DEF-101-531／R60 A-01）",
        )
        self.assertTrue(
            completed,
            "生產端 usable_bash() 一次 subprocess 都沒呼叫——候選蒐集或 which 替身壞了，"
            "此時的 None 與 PROBE_CMD 驗活無關",
        )
        self.assertNotEqual(
            completed[-1][0], 0,
            f"PATH 只含空目錄時 PROBE_CMD 應以非 0 收場（實際 rc=0，stdout="
            f"{completed[-1][1]!r}）——`dirname` 仍被找到，本載具已失去鑑別力",
        )
        self.assertIsNone(
            result,
            "PATH 缺 dirname 時 usable_bash() 應拒絕該候選並回傳 None，"
            "實際卻回傳可用路徑——生產端 wiring 未真正依賴 PROBE_CMD 的 coreutils 驗證",
        )

    def test_usable_bash_accepts_candidate_with_real_path(self) -> None:
        real_path = os.environ.get("PATH", "/usr/bin:/bin")
        result, completed, spawn_errors = usable_bash_with_probe_spy(
            self.bash_probe, real_path
        )
        self.assertFalse(
            spawn_errors,
            f"載具故障：探測子行程沒起來（{[str(e) for e in spawn_errors]}）",
        )
        self.assertEqual(result, _BASH)
        self.assertEqual(completed[-1][0], 0)


@unittest.skipUnless(_BASH, "需要本機可用的 bash 驗證生產端到端 wiring")
class TestNoneSourceIsDistinguishable(unittest.TestCase):
    """釘住「`usable_bash()` 回 None 的兩種來源必須可分辨」（R60 A-01／DEF-101-531）。

    WHY：生產端的 `except Exception: continue` 讓「候選被 PROBE_CMD 正確拒絕」與
    「子行程根本沒起來」回同一個 `None`。R60 實測本機 Windows 上官方閘門
    （`tools/run_root_unittests.py`，pre-push ＋ root-infra-ci ＋ macos/windows-compat-ci
    共四處呼叫）對 `test_usable_bash_rejects_candidate_when_path_lacks_dirname`
    **長年誤綠**：`None` 來自 `[WinError 87] 參數錯誤`（`CreateProcess` 沒起來），
    而非候選被拒絕。誤綠的代價是 DEF-101-275 的 wiring 層防線在 Windows 上等於不存在。
    本類鎖住兩件事：① helper 真的把兩種來源分流；② wiring 測試在「子行程起不來」時
    會**紅**而不是誤綠。
    """

    def setUp(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(repo_root / "AISDLC_SDD" / "scripts"))
        import bash_probe  # noqa: PLC0415
        self.bash_probe = bash_probe

    @staticmethod
    def _spawn_failure(*_args, **_kwargs):
        raise OSError(87, "參數錯誤（R60 注入：模擬 CreateProcess 沒起來）")

    def test_spawn_failure_is_reported_apart_from_rejection(self) -> None:
        with mock.patch.object(subprocess, "run", self._spawn_failure):
            result, completed, spawn_errors = usable_bash_with_probe_spy(
                self.bash_probe, "/definitely/not/a/real/dir"
            )
        self.assertIsNone(result, "生產端現況：spawn 失敗被 except Exception 吞成 None")
        self.assertEqual(completed, [], "子行程沒起來時不該有任何 completed 記錄")
        self.assertEqual(len(spawn_errors), 1, "spawn 失敗必須被單獨記錄，不可靜默")
        self.assertIsInstance(spawn_errors[0], OSError)

    def test_probe_rejection_is_reported_apart_from_spawn_failure(self) -> None:
        rejected = subprocess.CompletedProcess(
            args=[], returncode=127, stdout=f"{_spec.PROBE_EXPECT_ECHO}\n", stderr=""
        )
        with mock.patch.object(subprocess, "run", lambda *a, **kw: rejected):
            result, completed, spawn_errors = usable_bash_with_probe_spy(
                self.bash_probe, "/definitely/not/a/real/dir"
            )
        self.assertIsNone(result)
        self.assertEqual(spawn_errors, [], "驗活失敗不是 spawn 失敗，不可混記")
        self.assertEqual(completed, [(127, f"{_spec.PROBE_EXPECT_ECHO}\n")])

    def test_wiring_test_goes_red_instead_of_green_when_spawn_breaks(self) -> None:
        """把「子行程起不來」注入回 wiring 測試本體，斷言它 FAIL——這正是 A-01 的核心：
        修復前同一注入下該測試印 `ok`（假綠），修復後必須紅並指名載具故障。"""
        case = TestUsableBashEndToEndWithRestrictedPath(
            "test_usable_bash_rejects_candidate_when_path_lacks_dirname"
        )
        result = unittest.TestResult()
        with mock.patch.object(subprocess, "run", self._spawn_failure):
            case.run(result)
        problems = list(result.failures) + list(result.errors)
        self.assertEqual(
            len(problems), 1,
            "wiring 測試在『探測子行程根本沒起來』時仍然通過＝A-01 誤綠復發"
            f"（testsRun={result.testsRun}, skipped={result.skipped}）",
        )
        self.assertIn("載具故障", problems[0][1])


if __name__ == "__main__":
    unittest.main()
