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
from pathlib import Path, PureWindowsPath
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import bash_probe_spec as _spec  # noqa: E402


def _probe_a_real_usable_bash_for_fixture() -> str | None:
    """獨立重寫版：探測本機一個「真正可用」的 bash 路徑，供本檔案的 `_BASH` fixture 使用。

    WHY（R64／DEF-101-617）：舊版 `_BASH = shutil.which("bash")` 在「PATH 上
    `bash` 解析到 WSL System32 佔位版、真正的 Git Bash 未直接掛在 PATH、只能
    透過 `git.exe` 相對路徑找到」這種真實可重現的 Windows 開發機設定下，會把
    該被排除的佔位版錯當成可用 bash——`_BASH` 本身就是錯的，且
    `usable_bash_with_probe_spy()` 對 `shutil.which` 的 mock 讓生產端
    `usable_bash()` 的 git.exe 相對路徑候選完全失效，本檔在這種機器上會有
    6/8 測試確定性失敗（與本輪 ADR-XPLAT-002 §8 item 12 UEP 棘輪化工作無關的
    既有缺陷）。

    比照生產端 `AISDLC_SDD/scripts/bash_probe.py::usable_bash()`（第 48~63 行）
    的候選蒐集邏輯**獨立重新實作**（不 import 生產程式碼），維持本檔案頭
    docstring 宣告的「三份消費者各自獨立重寫」架構慣例——若讓本檔直接呼叫
    生產端函式，測試會因為共用生產端邏輯而失去對生產端共同盲點的鑑別力。
    對每個候選實際跑一次 `PROBE_CMD` 驗活，第一個驗活成功的候選才接受為
    `_BASH`；全部候選都驗活失敗（或根本沒有候選）才回傳 `None`（維持既有
    `@unittest.skipUnless(_BASH, ...)` 語意：找不到就跳過，不是失敗）。
    """
    candidates: list[str] = []
    git = shutil.which("git")
    if git:
        git_path = Path(git).resolve()
        for up in list(git_path.parents)[:4]:
            for sub in ("usr/bin/bash.exe", "bin/bash.exe"):
                cand = up / sub
                if cand.exists():
                    candidates.append(str(cand))
    bare = shutil.which("bash")
    if bare and not any(
        part.lower() == _spec.SYSTEM32_SEGMENT for part in PureWindowsPath(bare).parts
    ):
        candidates.append(bare)
    for cand in candidates:
        try:
            result = subprocess.run(
                [cand, "-c", _spec.PROBE_CMD],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=15,
            )
        except Exception:
            continue
        lines = result.stdout.splitlines()
        if (
            result.returncode == 0
            and len(lines) >= 2
            and lines[0].strip() == _spec.PROBE_EXPECT_ECHO
            and lines[1].strip() == _spec.PROBE_EXPECT_DIRNAME
        ):
            return cand
    return None


_BASH = _probe_a_real_usable_bash_for_fixture()


def _find_real_git_bash_install_root() -> Path | None:
    """回傳本機真實 Git for Windows 安裝根目錄（同時含 `bin/bash.exe` 與
    `usr/bin/bash.exe` 兩支二進位的目錄），供下方手法 A／B 兩個新輔助函式共用
    （DEF-101-618(a)）。找不到（例如非 Windows 平台、或找不到 git）回傳 `None`。
    """
    git = shutil.which("git")
    if not git:
        return None
    git_path = Path(git).resolve()
    for up in list(git_path.parents)[:4]:
        if (up / "bin" / "bash.exe").exists() and (up / "usr" / "bin" / "bash.exe").exists():
            return up
    return None


_install_root_for_bin_bash = _find_real_git_bash_install_root()
_REAL_BIN_BASH: str | None = (
    str(_install_root_for_bin_bash / "bin" / "bash.exe") if _install_root_for_bin_bash else None
)


def _build_coreutils_less_bash_clone(tmp_root: Path) -> Path | None:
    """在 `tmp_root` 下建構一份「刻意缺 coreutils 的 `Git\\bin\\bash.exe` 複製品」
    （手法 B，DEF-101-618(a)）。

    WHY：`export PATH=` 限縮外部傳入 PATH 這招對真實 `Git\\bin\\bash.exe`
    完全無效——該啟動器啟動時會**無條件**把 `/mingw64/bin:/usr/bin`（相對自身
    安裝根目錄）注入到自己內部 PATH 最前面，不受外部傳入 PATH 內容影響（實測：
    `env={"PATH": <單一空目錄>}` 呼叫後，bash 內部 `echo $PATH` 仍印出
    `/mingw64/bin:/usr/bin:...`）。要讓這款啟動器對 `dirname` 確定性失敗，須讓
    它自我注入的目標目錄本身缺 coreutils，而非限縮外部 PATH（那是手法 A，只對
    `usr/bin/bash.exe` 這類不自我注入的解譯器有效，見 `TestProbeCmdRealSubprocessBehavior`）。

    複製品結構（皆複製自本機真實 Git 安裝，路徑相對 `tmp_root`）：
      bin/bash.exe          <- 啟動器本體（真實 `<install_root>/bin/bash.exe`）
      usr/bin/bash.exe      <- 真解譯器（真實 `<install_root>/usr/bin/bash.exe`）
      usr/bin/msys-2.0.dll  <- 解譯器執行期依賴（缺了會啟動失敗，非本測試要模擬
                                的「找不到 dirname」情境，兩者性質不同）
      etc/                  <- 空目錄（MSYS root 偵測標記）
      mingw64/bin/          <- 空目錄（自我注入目標之一，刻意不放 coreutils）

    找不到本機真實 Git 安裝（例如非 Windows 平台）回傳 `None`，呼叫端應
    `skipTest`。
    """
    install_root = _find_real_git_bash_install_root()
    if install_root is None:
        return None
    real_bin_bash = install_root / "bin" / "bash.exe"
    real_usr_bin_bash = install_root / "usr" / "bin" / "bash.exe"
    real_msys_dll = install_root / "usr" / "bin" / "msys-2.0.dll"
    if not real_msys_dll.exists():
        return None
    clone_bin = tmp_root / "bin"
    clone_usr_bin = tmp_root / "usr" / "bin"
    clone_etc = tmp_root / "etc"
    clone_mingw64_bin = tmp_root / "mingw64" / "bin"
    for d in (clone_bin, clone_usr_bin, clone_etc, clone_mingw64_bin):
        d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(real_bin_bash, clone_bin / "bash.exe")
    shutil.copy2(real_usr_bin_bash, clone_usr_bin / "bash.exe")
    shutil.copy2(real_msys_dll, clone_usr_bin / "msys-2.0.dll")
    return clone_bin / "bash.exe"


def usable_bash_with_probe_spy(
    bash_probe_module, path_env: str, candidate_bash: str | None = None
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

    `candidate_bash`（DEF-101-618(a) 新增，選用）：指定要驗的候選 bash 路徑；
    省略時沿用既有預設值 `_BASH`，對既有呼叫端零行為變化。用於讓
    `TestUsableBashRejectsCoreutilsLessBinBashClone` 可以指定手法 B 建構出的
    「缺 coreutils 複製品」作為候選，而非本檔 fixture 探測到的真實可用 bash。
    """
    real_bash = candidate_bash if candidate_bash is not None else _BASH
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


@unittest.skipUnless(
    _REAL_BIN_BASH,
    "[WINDOWS-NATIVE-ONLY] 需要本機真實 Git\\bin\\bash.exe 驗證自我注入 PATH 現象"
    "（Git for Windows 只存在於 Windows；R67-F11 補標籤，供 run_root_unittests.py 彙整可見度）",
)
class TestBinBashLauncherSelfInjectsPathContract(unittest.TestCase):
    """行為層防線（DEF-101-618(a)）：直接鎖住「限縮外部 PATH（手法 A 的原始形態）
    對 `bin/bash.exe` 這類會自我注入 PATH 的啟動器無效，但讓 bash **自己**在
    啟動器完成自我注入之後、於自身行程內部執行 `export PATH=` 則可讓它確定性
    失敗」這個現象本身，證明 R64 殘留發現（`TestProbeCmdRealSubprocessBehavior`
    的兩支「拒絕」測試在 pwsh 下選到 `bin/bash.exe` 時失去鑑別力）的前提是真的，
    也證明手法 A 的解法（"export PATH= ; " 前綴）對它真的有效。

    此類與 `TestProbeCmdRealSubprocessBehavior`（驗證 `usr/bin/bash.exe` 這類
    不自我注入的解譯器）互補、不重複：兩者驗證的是兩款不同二進位對同一種模擬
    手法的不同反應，各自對不同候選類型維持鑑別力。
    """

    def test_restricted_external_path_alone_is_ineffective(self) -> None:
        # 純限縮外部 PATH（單一空目錄）：對 bin/bash.exe 這類自我注入啟動器
        # 無效——它仍會找到 dirname（因為 /mingw64/bin:/usr/bin 已被注入內部
        # PATH 最前面），rc 仍是 0。這正是既有兩支「拒絕」測試在 pwsh 下選到
        # 這款啟動器時失去鑑別力的根因（DEF-101-618(a)）。
        with tempfile.TemporaryDirectory(prefix="probe_no_coreutils_") as empty_dir:
            result = subprocess.run(
                [_REAL_BIN_BASH, "-c", _spec.PROBE_CMD],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=15, env={"PATH": empty_dir},
            )
        self.assertEqual(
            result.returncode, 0,
            "現象前提不成立：外部限縮 PATH 竟讓 bin/bash.exe 也找不到 dirname"
            f"（rc={result.returncode}, stdout={result.stdout!r}）——若本斷言失敗，"
            "代表 DEF-101-618(a) 描述的自我注入現象在本機已不成立，需重新調查",
        )

    def test_export_path_empty_makes_probe_fail(self) -> None:
        # 手法 A：讓 bash 自己在內部執行 `export PATH=`，覆寫掉啟動器已完成的
        # 自我注入，此時 dirname 才真的找不到（確定性 rc != 0）。
        with tempfile.TemporaryDirectory(prefix="probe_no_coreutils_") as empty_dir:
            result = subprocess.run(
                [_REAL_BIN_BASH, "-c", "export PATH= ; " + _spec.PROBE_CMD],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=15, env={"PATH": empty_dir},
            )
        self.assertNotEqual(
            result.returncode, 0,
            "手法 A（bash 內部 export PATH= 清空自我注入後的 PATH）應讓 dirname "
            f"確定性失敗，實際 rc=0，stdout={result.stdout!r}",
        )


class TestUsableBashRejectsCoreutilsLessBinBashClone(unittest.TestCase):
    """Wiring 層防線（DEF-101-618(a)）：手法 B——複製一份「刻意缺 coreutils 的
    `bin/bash.exe` 複製品」，驗證 (i) 直接呼叫該複製品跑 PROBE_CMD 確定性失敗、
    (ii) 透過生產端 `usable_bash()` 完整 wiring 對這個候選正確拒絕（回傳 None）。

    此手法對 `bin/bash.exe` 這類自我注入啟動器仍有鑑別力——手法 A（限縮外部
    PATH）對它無效（見 `TestBinBashLauncherSelfInjectsPathContract`），因為
    生產端把候選當外部黑盒子呼叫（`[cand, "-c", _spec.PROBE_CMD]` 寫死），測試
    側無法從外部插入 `export PATH= ; ` 前綴；手法 B 改讓候選**本身**自我注入的
    目標目錄缺 coreutils，不依賴外部如何呼叫它，故仍可驗證生產端 wiring。
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="broken_git_bash_clone_")
        self.addCleanup(self._tmp.cleanup)
        clone = _build_coreutils_less_bash_clone(Path(self._tmp.name))
        if clone is None:
            self.skipTest(
                "[WINDOWS-NATIVE-ONLY] 找不到本機真實 Git for Windows 安裝（含 bin/bash.exe、"
                "usr/bin/bash.exe、usr/bin/msys-2.0.dll），無法建構手法 B 的"
                "複製品——本測試僅在該類機器設定下有意義（DEF-101-618(a)；"
                "R67-F11 補標籤，供 run_root_unittests.py 彙整可見度）"
            )
        self.broken_bash = str(clone)
        repo_root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(repo_root / "AISDLC_SDD" / "scripts"))
        import bash_probe  # noqa: PLC0415
        self.bash_probe = bash_probe

    def test_direct_subprocess_call_fails(self) -> None:
        # 必須明確限縮外部 PATH（單一空目錄）：若不傳 `env=`、讓子行程原樣繼承
        # 呼叫端目前這個真實系統 PATH（其中仍含本機真正的 coreutils 目錄），
        # 自我注入的空目錄找不到 dirname 後，解析仍會落到繼承 PATH 尾端的真實
        # coreutils 目錄而意外成功（本機實測 rc=0）——那驗的是「繼承 PATH 有無
        # coreutils」，不是本測試要驗的「複製品自我注入的目標目錄本身缺
        # coreutils」。限縮成單一空目錄後，整條 PATH 都沒有真實 coreutils 可
        # 落回，才能確定性重現 rc=127。
        with tempfile.TemporaryDirectory(prefix="probe_no_coreutils_") as empty_dir:
            result = subprocess.run(
                [self.broken_bash, "-c", _spec.PROBE_CMD],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=15, env={"PATH": empty_dir},
            )
        self.assertNotEqual(
            result.returncode, 0,
            "缺 coreutils 的 bin/bash.exe 複製品應無法執行 dirname，實際 rc=0，"
            f"stdout={result.stdout!r}——複製品未如預期缺 coreutils",
        )

    def test_usable_bash_rejects_this_candidate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="probe_no_coreutils_") as empty_dir:
            result, completed, spawn_errors = usable_bash_with_probe_spy(
                self.bash_probe, empty_dir, candidate_bash=self.broken_bash
            )
        self.assertFalse(
            spawn_errors,
            "載具故障（非生產端結論）：usable_bash() 的探測子行程根本沒起來"
            f"（{[f'{type(e).__name__}: {e}' for e in spawn_errors]}）",
        )
        self.assertTrue(
            completed,
            "生產端 usable_bash() 一次 subprocess 都沒呼叫——候選蒐集或 which 替身壞了",
        )
        self.assertNotEqual(
            completed[-1][0], 0,
            f"缺 coreutils 的複製品應以非 0 收場（實際 rc=0，stdout="
            f"{completed[-1][1]!r}）——複製品已失去鑑別力",
        )
        self.assertIsNone(
            result,
            "usable_bash() 應拒絕缺 coreutils 的 bin/bash.exe 複製品並回傳 None，"
            "實際卻回傳可用路徑",
        )


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
