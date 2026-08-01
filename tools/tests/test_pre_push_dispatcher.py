#!/usr/bin/env python3
"""tools/git-hooks/pre-push dispatcher 的功能性回歸鎖（R10 QA-1 / DEF-101-126）。

WHY（Rule 9 — 測試鎖的是意圖，不只是行為）：
本 dispatcher 是 R9 P1 修復（root-infra leg：純根層變更 push 原本一個閘門都不跑，
CI 帳單停擺期間零防護）＋ R10 ARCH-1 擴充（根層消費檔 leg：aisdlc-sdd-ci.yml paths
承認的非 AISDLC_SDD/ 條目，其回歸鎖住在 AISDLC_SDD/scripts/tests，純根層 push 原本
永遠不執行它們）的核心防線，先前卻零自動化測試（tools/tests 只有 pre-commit 的
SIGPIPE 回歸鎖）。分流邏輯一旦被重構改壞——case 前綴比對寫錯、fail-safe 被
「優化」成靜默放行、消費檔 yml 解析退化成空集合、子 hook 缺失改成軟跳過——
症狀全都是「push 照樣全綠放行」，沒有任何紅燈，正是最危險的無聲復發。
本檔以 tmp fake repo「真跑」dispatcher（非 mock），逐情境鎖住：
  1. 純根層變更 → 只跑 root-infra leg（R9 P1 的存在理由）
  2. 僅 AutoClaude/ 變更 → 只分流 AutoClaude 子 hook（不多跑）
  3. 空 stdin → fail-safe 全部 leg 都跑（寧可多跑不可漏跑）
  4. 根層消費檔變更 → 補跑 AISDLC_SDD/scripts/tests 回歸鎖（R10 ARCH-1）
  5. 刪除遠端分支（local_sha 全零）→ 明確跳過、不觸發 fail-safe
  6. 子 hook 缺失 → fail-loud rc=1（hooks 體系損壞不得靜默放行）
  7. 整合層閘門本體變更 → 實跑 tools/integration_gate.sh --skip-full（R67-C18：該閘門
     在整個自動化層零呼叫端，唯二執行者是已停擺的兩支 compat-CI ⇒ 實質已死）
  8. 整合閘門實跑失敗 → rc=1 擋 push（接線不等於閘門：rc 沒接上就只是裝飾）
  9. 整合閘門檔缺失 → fail-loud rc=1（閘門蒸發不得以全綠偽裝正常）

執行：python -m unittest tools.tests.test_pre_push_dispatcher -v
（亦由 tools/run_root_unittests.py discover 納入 pre-push root-infra leg 與
root-infra-ci / windows-compat-ci / macos-compat-ci 對應 step）
"""
from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path, PureWindowsPath
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
DISPATCHER = REPO_ROOT / "tools" / "git-hooks" / "pre-push"
ZERO_SHA = "0000000000000000000000000000000000000000"

# R32 Architect 架構最佳化：驗活探測「參數」（指令/期望輸出/System32 排除段）
# 抽為共用資料規格（tools/lib/bash_probe_spec.py），三份獨立實作各自 import 取得
# 同一份規則資料；驗活的 subprocess 執行邏輯本檔仍獨立寫死，不共用函式（見下方
# `_usable_bash()` docstring）。
sys.path.insert(0, str(REPO_ROOT / "tools" / "lib"))
import bash_probe_spec as _spec  # noqa: E402

# fake 消費檔清單來源：格式鏡真實 aisdlc-sdd-ci.yml（`- "..."` 雙引號條目）。
# dispatcher 機械解析此檔（單一真相源），本測試據此鎖住「解析→比對→補跑」全鏈。
_FAKE_SDD_CI_YML = """\
name: fake-aisdlc-sdd-ci
on:
  push:
    paths:
      - "AISDLC_SDD/**"
      - "tools/check_ntfs_paths.py"
      - ".github/workflows/aisdlc-sdd-ci.yml"
"""


def _usable_bash() -> str | None:
    """回傳可跑 repo bash 腳本的 bash 路徑；只有 WSL 佔位 bash、缺 coreutils 的
    殘缺 bash、或無 bash → None。

    邏輯鏡自 AISDLC_SDD/scripts/bash_probe.py（該檔是子專案 scripts/tests 的
    SSOT）；根層 tools/tests 刻意不跨子專案 import 該檔的執行邏輯——子專案檔案
    搬移不應弄壞根層閘門。驗活探測「參數」（指令/期望輸出/System32 排除段）
    改為共用 `tools/lib/bash_probe_spec.py`（R32 Architect 架構最佳化），三處
    讀同一份規則資料，但本檔的 subprocess 執行邏輯仍獨立寫死；若執行邏輯本身
    更新，請三處同步。

    R31 Scan-B 修復：System32 排除改用 `PureWindowsPath` 逐段精確比對（對齊
    `tools/integration_gate_core.py::_has_system32_segment()`，DEF-101-236），
    不再用任意子字串命中即排除。

    R32 修復 DEF-101-275（R27 開出、連續 5 輪未收斂）：原本只用 `echo ok` 驗活，
    未驗 coreutils（如 `dirname`），精簡版 Git Bash 會誤判為可用。改用
    `_spec.PROBE_CMD`（echo + dirname 兩段串接）驗活。
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
    if bare and not any(
        part.lower() == _spec.SYSTEM32_SEGMENT for part in PureWindowsPath(bare).parts
    ):
        candidates.append(bare)
    for cand in candidates:
        try:
            r = subprocess.run(
                [cand, "-c", _spec.PROBE_CMD],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=15,
            )
            lines = r.stdout.splitlines()
            if (
                r.returncode == 0
                and len(lines) >= 2
                and lines[0].strip() == _spec.PROBE_EXPECT_ECHO
                and lines[1].strip() == _spec.PROBE_EXPECT_DIRNAME
            ):
                return cand
        except Exception:
            continue
    return None


class TestUsableBashSystem32Guard(unittest.TestCase):
    """R31 QA 一審必修條件 2：`_usable_bash()` 是本檔鏡射自 `bash_probe.py` 的獨立
    副本，先前只被當成模組層級 `_BASH = _usable_bash()`（供 `skipif` 判斷）呼叫，
    沒有任何 case 直接斷言其 System32 排除邏輯本身。本類別補上直接呼叫點回歸鎖，
    比照 `AISDLC_SDD/scripts/tests/test_bash_probe.py::TestUsableBashSystem32Guard`
    既有慣例。"""

    def test_skips_wsl_system32_placeholder(self) -> None:
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
            mock_run.return_value = mock.Mock(returncode=0, stdout="probe_ok\n/tmp/probe_dir\n")
            result = _usable_bash()
        self.assertEqual(result, legit_path)

    def test_rejects_bash_missing_coreutils_dirname(self) -> None:
        """R32 bug-injection 標的（DEF-101-275，R27 開出、連續 5 輪未收斂）：
        精簡版 Git Bash 只有 `echo` 可用、缺 `dirname` 這類 coreutils 時，
        `&&` 串接的第二段會以非 0 回傳碼失敗——必須被拒絕，不能只驗 echo 就
        誤判為可用。若退化回舊版只驗 `echo ok`，本測試須變紅。"""
        legit_path = r"C:\Program Files\Git\usr\bin\bash.exe"  # platform-ok: mock 回傳值
        with (
            mock.patch.object(shutil, "which") as mock_which,
            mock.patch.object(subprocess, "run") as mock_run,
        ):
            mock_which.side_effect = lambda name: legit_path if name == "bash" else None
            # bash: dirname: command not found → echo 段已輸出，但整串 && 鏈
            # 因第二段找不到指令而以 rc=127 失敗。
            mock_run.return_value = mock.Mock(returncode=127, stdout="probe_ok\n")
            result = _usable_bash()
        self.assertIsNone(result, "缺 coreutils（dirname）的殘缺 bash 應被拒絕")

    def test_accepts_bash_with_working_coreutils(self) -> None:
        """正向案例：echo 與 dirname 皆正確輸出、rc=0 時應被接受。"""
        legit_path = r"C:\Program Files\Git\usr\bin\bash.exe"  # platform-ok: mock 回傳值
        with (
            mock.patch.object(shutil, "which") as mock_which,
            mock.patch.object(subprocess, "run") as mock_run,
        ):
            mock_which.side_effect = lambda name: legit_path if name == "bash" else None
            mock_run.return_value = mock.Mock(returncode=0, stdout="probe_ok\n/tmp/probe_dir\n")
            result = _usable_bash()
        self.assertEqual(result, legit_path)


_BASH = _usable_bash()


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )


def _bash_marker_stub(marker: Path) -> str:
    """子 hook stub：留下 marker 檔證明真的被執行到（比照 SIGPIPE 測試手法）。"""
    return f'#!/usr/bin/env bash\n: > "{marker.as_posix()}"\nexit 0\n'


def _py_marker_stub(marker: Path) -> str:
    """python stub：寫 marker 後 exit 0（供 run_root_unittests 替身用）。"""
    return (
        "from pathlib import Path\n"
        f'Path("{marker.as_posix()}").write_text("ran", encoding="utf-8")\n'
        "raise SystemExit(0)\n"
    )


@unittest.skipIf(_BASH is None, "pre-push dispatcher 為 bash 腳本，需可用 bash（非 WSL 佔位）")
class TestPrePushDispatcher(unittest.TestCase):
    """在 tmp fake repo 內真跑本 repo 的 pre-push dispatcher，鎖住分流語意。"""

    def setUp(self) -> None:
        self.assertTrue(DISPATCHER.is_file(), f"dispatcher 不存在：{DISPATCHER}")

        self.tmp = Path(tempfile.mkdtemp(prefix="pp_dispatcher_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        init = _git("init", "-q", cwd=self.repo)
        self.assertEqual(init.returncode, 0, init.stderr)

        # 隔離本機組態：中和全域 hooks（fixture commit 不得誤觸本機真 hook）與
        # gpg 簽章（無 key 的環境 commit 會炸）。
        no_hooks = self.tmp / "no-hooks"
        no_hooks.mkdir()
        for key, value in (
            ("user.email", "test@example.com"),
            ("user.name", "Test"),
            ("commit.gpgsign", "false"),
            ("core.hooksPath", str(no_hooks)),
        ):
            cfg = _git("config", key, value, cwd=self.repo)
            self.assertEqual(cfg.returncode, 0, cfg.stderr)

        # 受測物：本 repo 的「真」dispatcher copy 進 fake repo 對應位置。
        # dispatcher 以 `git rev-parse --show-toplevel` 定位樹根 → 必須於
        # fake repo cwd 執行，才會對 fake 樹分流，而非真 repo 的樹。
        hooks_dir = self.repo / "tools" / "git-hooks"
        hooks_dir.mkdir(parents=True)
        shutil.copy(DISPATCHER, hooks_dir / "pre-push")
        os.chmod(hooks_dir / "pre-push", 0o755)

        # R43 Scan-B（DEF-101-353）：dispatcher 現以 `. "$TOPLEVEL/tools/lib/
        # windowsapps_guard.sh"` 載入共用 guard，fake repo 樹需同步備有此檔，
        # 否則 source 失敗、guard 函式未定義，兩處 leg 判斷會誤判「找不到 python」。
        guard_lib_dir = self.repo / "tools" / "lib"
        guard_lib_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(
            REPO_ROOT / "tools" / "lib" / "windowsapps_guard.sh",
            guard_lib_dir / "windowsapps_guard.sh",
        )

        # marker 檔（tmp 層、repo 外）：各 leg 真的執行到的鐵證。
        self.marker_autoclaude = self.tmp / "MARKER_AUTOCLAUDE_SUBHOOK"
        self.marker_sdd = self.tmp / "MARKER_SDD_SUBHOOK"
        self.marker_rootinfra = self.tmp / "MARKER_ROOTINFRA_UNITTESTS"
        self.marker_consumer = self.tmp / "MARKER_SDD_SCRIPTS_TESTS_PYTEST"
        self.marker_integration_gate = self.tmp / "MARKER_INTEGRATION_GATE"

        # 兩個子 hook stub。
        self._write(
            "AutoClaude/tools/git-hooks/pre-push", _bash_marker_stub(self.marker_autoclaude)
        )
        os.chmod(self.repo / "AutoClaude" / "tools" / "git-hooks" / "pre-push", 0o755)
        self._write("AISDLC_SDD/.githooks/pre-push", _bash_marker_stub(self.marker_sdd))
        os.chmod(self.repo / "AISDLC_SDD" / ".githooks" / "pre-push", 0o755)

        # 最小 root-infra 面：py_compile 目標（tools/ + .claude/hooks/，驗 R10
        # 範圍擴充不炸）、run_root_unittests 替身（寫 marker）、七支守門 stub
        # （R13 增 check_pytest_baseline_sites；R55 增 check_gha_action_versions；
        # R60 增 archive_defect_log --check，隨 pre-push leg ③ 清單同步）。
        self._write("tools/ok.py", "OK = True\n")
        self._write("tools/run_root_unittests.py", _py_marker_stub(self.marker_rootinfra))
        for guard in (
            "check_script_parity",
            "check_ntfs_paths",
            "check_defect_log_crossref",
            "check_wrapper_thinness",
            "check_pytest_baseline_sites",
            "check_gha_action_versions",
        ):
            self._write(f"tools/{guard}.py", "raise SystemExit(0)\n")
        # R60：leg ③ 的守門迴圈項自此可帶子指令（`archive_defect_log.py --check`），
        # 實作靠「`python $guard` 不加引號以分詞」。本 stub 刻意**檢查 argv**：少了
        # `--check` 就回非零 → 這支 fake-repo 測試同時成為那個分詞機制的端到端驗證，
        # 而不只是讓迴圈有檔可跑（不檢查 argv 的 stub 會讓「參數被吃掉」靜默通過）。
        self._write(
            "tools/archive_defect_log.py",
            "import sys\n"
            'raise SystemExit(0 if "--check" in sys.argv else 3)\n',
        )
        # R60 round 3：leg ③ 第 8 支＝`sync_onboarding_baselines.py --check-snapshot`
        # （ONBOARDING §7 表② 的測試樹指紋觸發器，DEF-101-563）。同上以 argv 檢查
        # 當 stub，讓「子指令被吃掉」不可能靜默通過——這一支的子指令與前一支不同字樣，
        # 故兩支併看即證明分詞機制對「多個各帶不同子指令的項目」都成立。
        self._write(
            "tools/sync_onboarding_baselines.py",
            "import sys\n"
            'raise SystemExit(0 if "--check-snapshot" in sys.argv else 4)\n',
        )
        self._write(".claude/hooks/trivial_hook.py", "OK = True\n")

        # R67-C18：整合閘門 leg 的受測面。真薄殼→核心委派由
        # tools/tests/test_find_git_bash_parity.py 的 TestIntegrationGateShellDelegation
        # 實跑覆蓋（R67 round 2 QA-R67-03 訂正：原指名一支名為
        # test_integration_gate_local_carrier.py 的鎖檔，該檔從未存在）；本檔只驗
        # 「dispatcher 有沒有在對的 push 範圍下把它叫起來」，故用 marker stub。
        # `--skip-full` 的透傳一併以 argv 檢查（不檢查 argv 的 stub 會讓「參數被吃掉」
        # 靜默通過，同 leg ③ 兩支帶子指令守門 stub 的手法）。
        self._write(
            "tools/integration_gate.sh",
            "#!/usr/bin/env bash\n"
            'case " $* " in *" --skip-full "*) ;; *) exit 9 ;; esac\n'
            f': > "{self.marker_integration_gate.as_posix()}"\n'
            "exit 0\n",
        )
        os.chmod(self.repo / "tools" / "integration_gate.sh", 0o755)
        self._write("tools/integration_gate_core.py", "OK = True\n")

        # 消費檔清單來源 + 消費檔 leg 的 pytest 目標（conftest 寫 marker＝執行鐵證）。
        self._write(".github/workflows/aisdlc-sdd-ci.yml", _FAKE_SDD_CI_YML)
        self._write(
            "AISDLC_SDD/scripts/tests/conftest.py",
            "from pathlib import Path\n"
            f'Path("{self.marker_consumer.as_posix()}").write_text("ran", encoding="utf-8")\n',
        )
        self._write(
            "AISDLC_SDD/scripts/tests/test_ok.py", "def test_ok():\n    assert True\n"
        )

        self._write("docs/x.md", "# base\n")

        self.base_sha = self._commit_all("base")

    # ------------------------------------------------------------------ helpers

    def _write(self, relpath: str, content: str) -> Path:
        """寫 UTF-8 + LF（bash stub 若被翻成 CRLF，\\r 會混進 marker 檔名）。"""
        p = self.repo / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8", newline="\n")
        return p

    def _commit_all(self, msg: str) -> str:
        add = _git("add", "-A", cwd=self.repo)
        self.assertEqual(add.returncode, 0, add.stderr)
        commit = _git("commit", "-q", "-m", msg, cwd=self.repo)
        self.assertEqual(commit.returncode, 0, commit.stderr)
        head = _git("rev-parse", "HEAD", cwd=self.repo)
        self.assertEqual(head.returncode, 0, head.stderr)
        return head.stdout.strip()

    def _python_dir(self) -> str:
        """回傳含 `python` 可執行檔的目錄（dispatcher 以 `command -v python` 探測）。

        venv 內天然有 python(.exe)；系統直譯器只有 python3 別名時（ubuntu CI
        常見）以 symlink shim 補上，symlink 建不了再退回複製。
        """
        exe_dir = Path(sys.executable).parent
        name = "python.exe" if os.name == "nt" else "python"
        if (exe_dir / name).exists():
            return str(exe_dir)
        shim = self.tmp / "pyshim"
        shim.mkdir(exist_ok=True)
        link = shim / "python"
        if not link.exists():
            try:
                link.symlink_to(Path(sys.executable))
            except OSError:
                shutil.copy2(sys.executable, link)
        return str(shim)

    def _run_dispatcher(self, stdin_text: str) -> tuple[int, str, str]:
        """於 fake repo cwd 以探測到的 bash 真跑 dispatcher，回傳 (rc, stdout, stderr)。"""
        env = dict(os.environ)
        # 外層若帶跳過旗標（如開發者 shell 殘留），dispatcher 會直接 exit 0，全部斷言失真。
        env.pop("AUTOCLAUDE_SKIP_HOOKS", None)
        # production 下 git 會幫 hook 把自家 usr/bin（GNU find/sed/sort/grep）prepend
        # 進 PATH；直接 spawn bash.exe 時 Windows 會把 find/sort 解析到 System32 版、
        # sed/grep 直接缺席（本機實測）→ 比照 git 行為 prepend bash 所在目錄。
        # 另 prepend 當前直譯器目錄：dispatcher 內 `command -v python` 必須解析到
        # 「正在跑本測試的直譯器」（消費檔 leg 的 pytest 住在它的環境裡）。
        env["PATH"] = os.pathsep.join(
            [self._python_dir(), str(Path(_BASH).parent), env.get("PATH", "")]
        )
        proc = subprocess.run(
            [_BASH, "tools/git-hooks/pre-push"],
            cwd=str(self.repo),
            # bytes 餵 stdin：text 模式會把 \n 翻成 os.linesep（Windows=\r\n），
            # \r 黏進 sha 欄位 → git diff 失敗 → 誤觸 fail-safe，測試全面失真。
            input=stdin_text.encode("utf-8"),
            capture_output=True,
            env=env,
            timeout=300,
        )
        return (
            proc.returncode,
            proc.stdout.decode("utf-8", errors="replace"),
            proc.stderr.decode("utf-8", errors="replace"),
        )

    @staticmethod
    def _push_line(local_sha: str, remote_sha: str) -> str:
        """組一行 git 餵給 pre-push 的 stdin：<local_ref> <local_sha> <remote_ref> <remote_sha>。"""
        return f"refs/heads/main {local_sha} refs/heads/main {remote_sha}\n"

    # ------------------------------------------------------------------- tests

    def test_root_only_change_triggers_rootinfra_leg_only(self) -> None:
        """情境 1：純根層變更（docs/）→ root-infra leg 必跑、兩子 hook 必不跑。

        WHY：R9 P1 的核心承諾——純根層 push 不再零閘門。此分支被改壞的症狀
        是 push 照樣全綠放行、無任何紅燈，唯一防線就是本測試。
        """
        self._write("docs/x.md", "# changed\n")
        sha = self._commit_all("root only change")
        rc, out, err = self._run_dispatcher(self._push_line(sha, self.base_sha))
        self.assertEqual(rc, 0, f"stdout={out}\nstderr={err}")
        self.assertIn("push 範圍含根層檔", out)
        self.assertTrue(
            self.marker_rootinfra.exists(),
            "root-infra leg 未執行（run_root_unittests 替身 marker 不存在）——"
            "純根層 push 再次零閘門（R9 P1 回歸）",
        )
        self.assertFalse(self.marker_autoclaude.exists(), "純根層變更不應觸發 AutoClaude 子 hook")
        self.assertFalse(self.marker_sdd.exists(), "純根層變更不應觸發 AISDLC_SDD 子 hook")
        self.assertFalse(self.marker_consumer.exists(), "docs/ 非消費檔，不應觸發消費檔 leg")
        self.assertNotIn("根層消費檔", out)
        self.assertFalse(
            self.marker_integration_gate.exists(),
            "docs/ 未動到整合閘門本體，不應付整合閘門的執行成本（R67-C18 路徑範圍觸發）",
        )

    def test_autoclaude_only_change_routes_to_autoclaude_only(self) -> None:
        """情境 2：僅 AutoClaude/ 變更 → 只分流 AutoClaude 子 hook，root-infra 不多跑。

        WHY：分流的「不多跑」面向——root-infra leg 誤觸發會讓每次子專案 push
        都付整套根層閘門成本，開發者遲早用 --no-verify 繞過，防線形同虛設。
        """
        self._write("AutoClaude/x.txt", "x\n")
        sha = self._commit_all("autoclaude only change")
        rc, out, err = self._run_dispatcher(self._push_line(sha, self.base_sha))
        self.assertEqual(rc, 0, f"stdout={out}\nstderr={err}")
        self.assertIn("push 範圍含 AutoClaude/", out)
        self.assertTrue(
            self.marker_autoclaude.exists(),
            "AutoClaude 子 hook 未被執行——分流靜默漏跑",
        )
        self.assertFalse(self.marker_sdd.exists(), "未涉 AISDLC_SDD/ 不應觸發 SDD 子 hook")
        self.assertFalse(self.marker_rootinfra.exists(), "未涉根層檔不應觸發 root-infra leg")
        self.assertFalse(self.marker_consumer.exists(), "未涉消費檔不應觸發消費檔 leg")
        self.assertFalse(
            self.marker_integration_gate.exists(),
            "僅 AutoClaude/ 變更不應觸發整合閘門 leg——那正是「pre-push 變慢到沒人用」的路",
        )
        self.assertNotIn("root-infra", out)

    def test_empty_stdin_failsafe_runs_all_legs(self) -> None:
        """情境 3：空 stdin → fail-safe 全部 leg 都跑（寧可多跑不可漏跑）。

        R67-C18 起「全部」＝四 leg（兩子專案 + root-infra + 整合閘門）；測試名刻意不寫
        死數字，避免下一次增減 leg 時名稱與內容漂移（本 repo 已多次踩到計數敘述漂移）。

        WHY：pre-commit 框架等外層工具可能吃掉 hook 的 stdin；無法判定 push
        範圍時唯一安全語意是全跑。fail-safe 若被「優化」成靜默放行（rc=0、
        零 leg），就是整個 dispatcher 最危險的回歸模式。
        """
        rc, out, err = self._run_dispatcher("")
        self.assertEqual(rc, 0, f"stdout={out}\nstderr={err}")
        self.assertIn("fail-safe", out)
        self.assertTrue(self.marker_autoclaude.exists(), "fail-safe 應執行 AutoClaude 子 hook")
        self.assertTrue(self.marker_sdd.exists(), "fail-safe 應執行 AISDLC_SDD 子 hook")
        self.assertTrue(self.marker_rootinfra.exists(), "fail-safe 應執行 root-infra leg")
        # SDD leg 已含 scripts/tests（ci-gate.sh 內），消費檔 leg 依設計免重複跑。
        self.assertFalse(self.marker_consumer.exists(), "SDD leg 已觸發時消費檔 leg 不應重複跑")
        self.assertTrue(
            self.marker_integration_gate.exists(),
            "fail-safe 應執行整合閘門 leg——無法判定範圍時該 push 可能正好動到閘門本體，"
            "「寧可多跑不可漏跑」對這一 leg 同樣適用（R67-C18）",
        )

    def test_consumer_file_change_runs_sdd_regression_and_rootinfra(self) -> None:
        """情境 4：根層消費檔變更（tools/check_ntfs_paths.py、不碰 AISDLC_SDD/）
        → 補跑 AISDLC_SDD/scripts/tests 回歸鎖，且 root-infra leg 同時觸發。

        WHY：R10 ARCH-1 / DEF-101-125——消費檔的回歸鎖住在 SDD suite，而 SDD
        leg 只在 push 涉 AISDLC_SDD/ 時觸發；沒有本 leg，改壞消費檔可零機械
        訊號直推 main。消費檔清單是機械解析 yml 而來，解析被改壞的症狀是
        「空集合＝leg 永不觸發」，同樣全綠無聲，只有本測試能抓。
        """
        if importlib.util.find_spec("pytest") is None:
            # 消費檔 leg 以 `python -m pytest` 真跑（非 mock）；root-infra CI 的
            # 純 stdlib 環境無 pytest → 誠實 skip（本機 venv / 開發環境必真跑）。
            self.skipTest("消費檔 leg 需 pytest；當前直譯器無 pytest（純 stdlib CI 環境）")
        self._write("tools/check_ntfs_paths.py", "# changed by test\nraise SystemExit(0)\n")
        sha = self._commit_all("consumer file change")
        rc, out, err = self._run_dispatcher(self._push_line(sha, self.base_sha))
        self.assertEqual(rc, 0, f"stdout={out}\nstderr={err}")
        self.assertIn("根層消費檔", out)
        self.assertTrue(
            self.marker_consumer.exists(),
            "AISDLC_SDD/scripts/tests 未被 pytest 真跑（conftest marker 不存在）——"
            "消費檔回歸鎖靜默漏跑（R10 ARCH-1 回歸）",
        )
        self.assertTrue(
            self.marker_rootinfra.exists(),
            "消費檔同時是根層檔，root-infra leg 也必須觸發",
        )
        self.assertFalse(self.marker_autoclaude.exists(), "未涉 AutoClaude/ 不應觸發其子 hook")
        self.assertFalse(self.marker_sdd.exists(), "未涉 AISDLC_SDD/ 不應觸發 SDD 子 hook 本體")

    def test_branch_deletion_runs_no_legs(self) -> None:
        """情境 5：刪除遠端分支（local_sha 全零）→ 所有 leg 不跑、且不落入 fail-safe。

        WHY：刪分支無東西可驗證，是「已判定的明確跳過」而非「無法判定」。
        此語意邊界被改壞的兩種方向都危險：歸成 fail-safe＝刪分支付全套閘門
        成本；parsed 判定壞掉＝正常 push 反而可能被當 0 行處理而漏跑。
        """
        rc, out, err = self._run_dispatcher(self._push_line(ZERO_SHA, self.base_sha))
        self.assertEqual(rc, 0, f"stdout={out}\nstderr={err}")
        self.assertNotIn("fail-safe", out)
        self.assertNotIn("→ 執行", out)
        self.assertFalse(self.marker_autoclaude.exists(), "刪分支不應觸發 AutoClaude 子 hook")
        self.assertFalse(self.marker_sdd.exists(), "刪分支不應觸發 AISDLC_SDD 子 hook")
        self.assertFalse(self.marker_rootinfra.exists(), "刪分支不應觸發 root-infra leg")
        self.assertFalse(self.marker_consumer.exists(), "刪分支不應觸發消費檔 leg")
        self.assertFalse(
            self.marker_integration_gate.exists(), "刪分支不應觸發整合閘門 leg"
        )

    def test_missing_subhook_fails_loud(self) -> None:
        """情境 6：分流命中 AutoClaude 但子 hook 檔缺失 → rc=1 fail-loud。

        WHY：子 hook 應存在卻缺失＝hooks 體系損壞（安裝腳本壞掉／檔案被搬移）；
        若被改成「檔案不在就跳過」的軟處理，壞掉的體系會以全綠偽裝正常，
        永遠沒人發現閘門早已蒸發。
        """
        self._write("AutoClaude/y.txt", "y\n")
        sha = self._commit_all("autoclaude change with missing subhook")
        (self.repo / "AutoClaude" / "tools" / "git-hooks" / "pre-push").unlink()
        rc, out, err = self._run_dispatcher(self._push_line(sha, self.base_sha))
        self.assertEqual(rc, 1, f"子 hook 缺失必須 rc=1 拒絕放行：\nstdout={out}\nstderr={err}")
        self.assertIn("子 hook 缺失", out + err)
        self.assertFalse(self.marker_autoclaude.exists(), "子 hook 已缺失不可能留下 marker")

    def test_integration_gate_change_runs_the_gate(self) -> None:
        """情境 7：變更整合閘門本體（tools/integration_gate_core.py）→ 實跑該閘門。

        WHY（R67-C18）：tools/integration_gate.{sh,ps1,_core.py} 是 monorepo 整合層
        閘門，但它在整個自動化層零呼叫端——唯二執行者是兩支已隨 CI 帳務停擺
        （DEF-101-081）而多輪未跑的 compat-CI。「雲端是唯一執行者的東西＝實質已死」：
        改壞閘門本體後，本機沒有任何流程會發現。本 leg 是它在本機的第一個活體執行者。
        刻意用 `_core.py`（而非 `.sh`）當觸發檔，鎖住 dispatcher 的 glob 前綴比對
        `tools/integration_gate*` 真的涵蓋三支，而不只認到薄殼那一支。
        """
        self._write("tools/integration_gate_core.py", "OK = True  # changed by test\n")
        sha = self._commit_all("integration gate core change")
        rc, out, err = self._run_dispatcher(self._push_line(sha, self.base_sha))
        self.assertEqual(rc, 0, f"stdout={out}\nstderr={err}")
        self.assertIn("push 涉整合層閘門本體", out)
        self.assertTrue(
            self.marker_integration_gate.exists(),
            "整合閘門未被實跑（marker 不存在）——閘門本體被改動時仍零活體驗證"
            "（R67-C18 回歸）",
        )
        self.assertFalse(self.marker_autoclaude.exists(), "未涉 AutoClaude/ 不應觸發其子 hook")

    def test_integration_gate_failure_blocks_push(self) -> None:
        """情境 8：整合閘門實跑失敗 → rc=1 擋 push。

        WHY：這一條才是「leg 是閘門」而非「leg 是裝飾」的定義。接線只保證它「被叫到」，
        rc 沒接上的症狀是閘門紅字照印、push 照樣放行——本 repo 已在 R60 對帳本保全
        稽核踩過同一形狀（「可重跑但沒有任何閘門看它的 rc」）。
        """
        self._write("tools/integration_gate.sh", "#!/usr/bin/env bash\nexit 1\n")
        os.chmod(self.repo / "tools" / "integration_gate.sh", 0o755)
        sha = self._commit_all("integration gate turns red")
        rc, out, err = self._run_dispatcher(self._push_line(sha, self.base_sha))
        self.assertEqual(
            rc, 1, f"整合閘門失敗必須擋 push：\nstdout={out}\nstderr={err}"
        )
        self.assertIn("整合閘門未通過", out + err)

    def test_missing_integration_gate_fails_loud(self) -> None:
        """情境 9：閘門檔應存在卻缺失 → rc=1 fail-loud（同子 hook 缺失語意）。

        WHY：閘門被刪掉／搬走時若軟跳過，「閘門蒸發」會以全綠偽裝正常——正是本輪
        在治的病（整合閘門已經因為載具死亡而實質蒸發多輪沒人發現）。
        """
        self._write("tools/integration_gate_core.py", "OK = True  # changed by test\n")
        sha = self._commit_all("integration gate core change with gate removed")
        (self.repo / "tools" / "integration_gate.sh").unlink()
        rc, out, err = self._run_dispatcher(self._push_line(sha, self.base_sha))
        self.assertEqual(rc, 1, f"閘門缺失必須 rc=1：\nstdout={out}\nstderr={err}")
        self.assertIn("整合閘門缺失", out + err)


# ── 指名鎖檔必須存在（R67 round 2，QA-R67-03）──────────────────────────────────
# WHY：本檔 setUp 與 `tools/git-hooks/pre-push` 的註解同時把
# `test_integration_gate_local_carrier.py` 指名為「路徑觸發抓不到的另兩種腐爛」的
# 守門者，而那支檔案**從未存在**（`ls` rc=1、全庫 `find` 零命中；真正的守門依
# `DEF-101-561③` 併進了 `test_find_git_bash_parity.py` 的既有姊妹鎖）。
# 實害是治理面：那段註解正是 DEF-101-639 修法正當性的核心論證，指向不存在的容器＝讀者
# 現查時無法驗證；更糟的是下一輪若有人執行「檔案不存在 ⇒ 這層守門沒落地」的推論，會誤判
# 本輪修復不完整並重做一次。本 repo 對「指名不存在的容器」已有明文硬規則
# （`docs/06_quality/CrossPlatform_Scan_Dimensions.md` 硬規則③ 第一點：禁止寫「記入某某
# 帳本」而該帳本不是真實檔案路徑），本筆是同一形態發生在程式碼註解上。
#
# 掃描面（為何不只掃本檔與 pre-push）：同一形態在 `tools/tests/` 其他鎖檔一樣會發生，
# 而成本只是一次 rglob；掃描面取兩者聯集。
_CARRIER_REF_RE = re.compile(r"tools/tests/(test_[A-Za-z0-9_]+\.py)")

# 具名登記：**刻意指向不存在檔名**的引用（＝反事實敘述，不是死信）。
# 兩筆的共同形狀：作者明說「本應為它新增一支專屬鎖檔，但 DEF-101-561③ 棘輪禁止新增鎖檔，
# 故改擴充進既有檔」——那個檔名是**被否決的方案名**，不是承諾存在的容器，讀者不會照著去
# 找（也因此它們寫成路徑形態並不算錯，只是需要在此表態）。登記本身帶 stale 自檢：
# 一旦這些檔案真的被建出來，本表就過期 ⇒
# 下面的相等斷言會紅並要求刪掉該筆登記（豁免不能因為「沒人記得回收」而永久存在）。
_COUNTERFACTUAL_CARRIER_REFS: dict[str, str] = {
    "test_sdd_latest.py":
        "tools/lib/sdd_latest.py 的專屬鎖檔——被 DEF-101-561③ 檔數棘輪否決，判準改擴充進 "
        "test_component_sanitizer_shared_layer_lock.py／"
        "test_sanitize_component_frozen_sdd_versions_lock.py，兩處引用皆明說『本應…但…』",
    "test_windowsapps_verdict_parity.py":
        "WindowsApps guard 行為表 parity 的專屬鎖檔——同被 DEF-101-561③ 否決，判準併入 "
        "test_windowsapps_guard_cross_consistency.py，該處引用亦明說『原本寫成獨立檔…被擋下』",
}


class TestNamedCarrierFilesActuallyExist(unittest.TestCase):
    """`tools/git-hooks/*` 與 `tools/tests/*.py` 內形如 `tools/tests/test_*.py` 的引用
    必須指向真實存在的檔案，否則就是死信。

    Rule 9（測意圖）：本鎖要的不是「檔名拼對」，而是「被當成守門依據引用的容器真的在」
    ——論證的可驗證性。刻意的反事實引用（明說『本應新增但被棘輪擋下』）走具名登記，
    且登記本身有 stale 自檢。
    """

    @staticmethod
    def _scan() -> dict[str, list[str]]:
        surface = sorted(
            p for p in list((REPO_ROOT / "tools" / "git-hooks").glob("*"))
            + list((REPO_ROOT / "tools" / "tests").glob("*.py"))
            if p.is_file()
        )
        dangling: dict[str, list[str]] = {}
        for path in surface:
            text = path.read_text(encoding="utf-8", errors="replace")
            for lineno, line in enumerate(text.splitlines(), 1):
                for name in _CARRIER_REF_RE.findall(line):
                    if not (REPO_ROOT / "tools" / "tests" / name).exists():
                        dangling.setdefault(name, []).append(
                            f"{path.relative_to(REPO_ROOT).as_posix()}:{lineno}"
                        )
        return dangling

    def test_no_unregistered_dangling_carrier_reference(self) -> None:
        """雙向斷言：掃到的死信集合必須**逐字等於**具名登記。

        · 多出來（新的死信、或本輪修好的那兩處退化回去）⇒ 紅。
        · 少了（某筆登記的檔案真的被建出來）⇒ 也紅，並要求刪掉該筆登記——豁免只能因為
          「條件還沒補」存在，不能因為「沒人記得回收」存在（`_PENDING_MIGRATION_SITES`
          的同型教訓）。
        """
        dangling = self._scan()
        unregistered = {
            k: v for k, v in dangling.items() if k not in _COUNTERFACTUAL_CARRIER_REFS
        }
        self.assertEqual(
            unregistered, {},
            "有引用指向不存在的鎖檔（死信）：\n  "
            + "\n  ".join(f"{k} ← {v}" for k, v in sorted(unregistered.items()))
            + "\n改法：指向真正的守門檔（必要時附類別名）；若是刻意的反事實敘述，"
              "請登記進 _COUNTERFACTUAL_CARRIER_REFS 並寫明理由。",
        )
        stale = sorted(k for k in _COUNTERFACTUAL_CARRIER_REFS if k not in dangling)
        self.assertEqual(
            stale, [],
            f"下列登記已過期（檔案已存在，或引用已被刪除）：{stale}——請刪掉該筆登記",
        )

    def test_the_scanner_is_not_vacuous(self) -> None:
        """正控：掃描面必須真的掃到東西，且對合成死信會說話。

        列舉器一旦寫壞（回空集合／正則失效），上面那支會恆真通過＝靜默失效。這裡以
        「本檔自己被引用到」與「合成不存在檔名必被判為 dangling」雙向釘住。
        """
        text = DISPATCHER.read_text(encoding="utf-8")
        self.assertIn(
            "tools/tests/test_find_git_bash_parity.py", text,
            "pre-push 註解不再指名整合閘門的守門鎖檔——QA-R67-03 訂正被回退？",
        )
        self.assertTrue(
            _CARRIER_REF_RE.findall(text), "正則對 pre-push 抽不到任何鎖檔引用"
        )
        # 合成檔名以字串拼接寫出：整支路徑形態不得以字面值出現在本檔源碼裡，否則本檔
        # 自己就成了掃描面上的一筆死信（實測：初版直接寫字面值，上面那支當場紅——
        # 這也順帶證明了掃描器對「新出現的死信」是會說話的）。
        ghost_name = "test_this_file_never_existed.py"
        ghost = "tools/tests/" + ghost_name
        self.assertEqual(_CARRIER_REF_RE.findall(ghost), [ghost_name])
        self.assertFalse((REPO_ROOT / "tools" / "tests" / ghost_name).exists())


if __name__ == "__main__":
    unittest.main()
