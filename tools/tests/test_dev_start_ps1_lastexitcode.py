#!/usr/bin/env python3
"""tools/dev_start 兩支殼（.ps1 / .sh）的「被 source 時 rc 語意」回歸鎖。

# 第一部分（原始職責）：tools/dev_start.ps1 dot-source 失敗分支 $LASTEXITCODE（DEF-101-304）

`tools/dev_start.ps1` 的 `.NOTES` 明載「dot-source 呼叫端判斷成功/失敗請讀
$LASTEXITCODE，不要用 $?」，但早期失敗分支（找不到 repo 根／找不到 Python
直譯器）在 dot-source 情境下只執行裸 `return`，未對 `$LASTEXITCODE` 賦值——
呼叫前的殘值（可能是 0）會被誤判為成功。對等的 `tools/dev_start.sh` 用
`return 1` 正確傳遞失敗，兩邊在 exit code 語意上不對稱（R35 Scan-A 發現）。

本測試只驗證「找不到 Python 直譯器」這條分支（PATH 清空即可穩定觸發，
不依賴 Windows PATHEXT／`.cmd` 解析語意，pwsh 在 macOS/Linux/Windows 上
dot-source 與 `$LASTEXITCODE` 的語言層行為一致，故不比照
`test_bootstrap_ps1.py` 的 `_windows_pwsh_available()` 額外限定真 Windows）。

# 第二部分（R67-C17 併入）：tools/dev_start.sh 的 zsh／bash 實跑載具

**為何併進本檔而不新開一支**：`DEF-101-561③`（由
`test_adr_xplat001_c1c2_lock.py::TestGuardFileCountShrinkOnlyRatchet` 機械強制）明文
禁止在 `tools/tests/` 新增鎖檔、只准「把新判準擴充進既有鎖檔」。而本檔正是 dev_start
兩支殼「被 source／dot-source 時如何傳 rc」的既有鎖檔——上面第一部分的緣起，逐字就是
「對等的 `tools/dev_start.sh` 用 `return 1` 正確傳遞失敗」這句**從未被機械驗證過**的
對照宣稱。第二部分把那句話變成真跑出來的事實，是同一條軸上的補完，不是雜物。

**缺口本體（R67-C17）**：`source tools/dev_start.sh` 是 ONBOARDING §2.1 教使用者每天
開工敲的第一道指令，而 macOS 自 Catalina 起預設 shell 就是 **zsh**。該檔有真正的 zsh
專屬程式碼路徑：`ZSH_EVAL_CONTEXT` 判定是否被 source、`${(%):-%x}` 取當前檔案路徑
（`zsh -c` 下 `$0` 是 "zsh"，不可靠）。R67 全庫普查實測：這條分支在整個自動化層的唯一
執行者是 `.github/workflows/macos-compat-ci.yml` 的一個 step，而該 workflow 因 CI 帳務
停擺（DEF-101-081）多輪未真正執行 ⇒ **使用者最常走的開工入口，全 repo 零活體驗證**。
`bash -n` / `zsh -n` 只做語法解析，執行不到這條分支（本機實測兩者皆 rc=0）。

🔴 **第二部分的斷言「結構」是重點，不只是斷言內容**（R67-C17 附帶發現的直接修復）：
macOS compat-CI 那個 step 的形狀是「`zsh -c 'source dev_start.sh; <斷言>'`」——把斷言
寫在同一個 shell 的 source 之後。R67 注入實測證明該形狀對它**本來要抓的主要故障模式
結構性失明**：一旦 sourced 偵測壞掉（`_ds_sourced=0`），dev_start.sh 會落到檔尾
`exit "$_ds_rc"`，**直接殺掉整個 `zsh -c`**，後面所有斷言一行都不執行、rc 仍為 0 全綠
（實測：注入後 CI 形狀 rc=0、`ASSERTION_LINE_REACHED` 從未印出）。故本檔改用**行程外側
通道**：把證物寫進 source 之後的一個重導向檔，再於 Python 端檢查。「斷言被跳過」因此
變成「證物檔不存在」＝當場紅，而不是靜默通過。

第二部分覆蓋（每項在 zsh 與 bash 各跑一次，鎖住兩殼行為對等）：
  1. 被 source 時**不得**殺掉呼叫端 shell（證物檔必須存在）
  2. `${(%):-%x}` / `${BASH_SOURCE[0]}` 路徑解析：核心必須以**腳本自身所在的 repo 根**
     被叫到（刻意在別的 cwd 執行，讓靠 cwd 猜路徑的實作當場失敗）
  3. 位置參數透傳給核心
  4. 成功時自動啟用 .venv（`VIRTUAL_ENV` 有值）
  5. 核心失敗時原樣回傳 rc、且**不得**誤啟用 venv（＝第一部分那句對照宣稱的實證）
  6. 呼叫端 shell 零 `_ds_*` 殘留（檔尾 `eval "unset _ds_rc; return $_ds_rc"` 的語意）
  7. 以「執行」而非 source 時：不動呼叫端 shell、印出提示、rc 照傳
刻意不做：真的建 .venv／真的 pip install／連網（那是 bootstrap 的職責，破壞性且分鐘級）。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ps_engine import any_engine_available, production_engine  # noqa: E402  # R60 E-A-03

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEV_START_PS1 = _REPO_ROOT / "tools" / "dev_start.ps1"
_DEV_START_SH = _REPO_ROOT / "tools" / "dev_start.sh"
_GUARD_LIB_SH = _REPO_ROOT / "tools" / "lib" / "windowsapps_guard.sh"


@unittest.skipIf(
    not any_engine_available(),  # R60 E-A-03：語意② SSOT 述詞
    "需要 powershell/pwsh",
)
class TestDevStartPs1DotSourceLastExitCode(unittest.TestCase):
    def _run(self) -> subprocess.CompletedProcess:
        exe = production_engine()  # R60 E-A-03：5.1 優先（DEF-101-509 判準）
        # R42 修復（DEF-101-350）：本機真實 Windows 11 開發機已有真實 `.venv`，
        # dev_start.ps1 的 `$VenvPy = Join-Path $Root '.venv\Scripts\python.exe'`
        # 用 Test-Path 短路判斷排在 PATH 查詢之前——原本只清空 PATH 的手法在「本
        # repo 目前開發中、已有真實 .venv」的機器上完全觸發不到「找不到 Python」
        # 分支（`Test-Path $VenvPy` 恆真，PATH 清空與否已不相關）。改把
        # dev_start.ps1 複製到隔離的臨時 `tools/` 目錄下執行（`$PSScriptRoot` 因而
        # 解析到臨時 $Root，`$VenvPy` 保證不存在），比照本 repo 既有 WindowsApps
        # guard 測試的臨時目錄隔離慣例，不依賴真實開發機器上是否已有 `.venv`。
        with tempfile.TemporaryDirectory() as td:
            tmp_tools = Path(td) / "tools"
            tmp_tools.mkdir()
            tmp_ps1 = tmp_tools / "dev_start.ps1"
            tmp_ps1.write_text(_DEV_START_PS1.read_text(encoding="utf-8"), encoding="utf-8")
            # dev_start.ps1 用相對路徑 dot-source `lib/WindowsAppsGuard.ps1`，
            # 隔離目錄需一併複製，否則 dot-source 找不到檔案會在抵達
            # 「找不到 Python」分支之前就先拋出無關的腳本錯誤。
            tmp_lib = tmp_tools / "lib"
            tmp_lib.mkdir()
            guard_src = _REPO_ROOT / "tools" / "lib" / "WindowsAppsGuard.ps1"
            (tmp_lib / "WindowsAppsGuard.ps1").write_text(
                guard_src.read_text(encoding="utf-8"), encoding="utf-8"
            )
            # PATH 只留最基本目錄，排除任何 py/python 候選，穩定觸發
            # 「找不到 Python 直譯器」這條 dot-source 失敗分支。
            # [Console]::OutputEncoding 設 UTF-8（R42 修復，DEF-101-350）：本機
            # 為繁體中文 Windows（Big5/950 codepage），dev_start.ps1 的中文錯誤
            # 訊息若不明確指定輸出編碼會被以錯誤 codepage 解讀成亂碼，斷言
            # 因而誤判失敗——同一根因/同一修法比照本輪稍早
            # test_install_post_commit_windowsapps_guard.py::_run_with_shadowed_python()
            # 的既有修復。
            cmd = (
                '[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; '
                '$env:PATH = "/usr/bin:/bin"; '
                f". '{tmp_ps1}'; "
                'Write-Output "RC_AFTER=$LASTEXITCODE"'
            )
            return subprocess.run(
                [exe, "-NoProfile", "-Command", cmd],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=30,
            )

    def test_python_not_found_sets_lastexitcode_nonzero_after_dot_source(self) -> None:
        """dot-source 情境下「找不到 Python」必須讓 $LASTEXITCODE 為非零值，
        修復前該分支只 `return`、$LASTEXITCODE 停留在呼叫前殘值（本測試以
        乾淨 pwsh 子行程執行，殘值恆為空字串，等同「看似成功」的誤判）。
        """
        proc = self._run()
        output = proc.stdout + proc.stderr
        self.assertIn("找不到", output, output)
        self.assertIn("RC_AFTER=1", output, output)
        self.assertNotIn("RC_AFTER=\n", output, output)


class TestDevStartPs1BothFailureBranchesSetLastExitCode(unittest.TestCase):
    """靜態一致性鎖，補齊上面行為測試的覆蓋盲區（R35 四方一審 Architect/QA/SD
    交叉獨立發現）：「找不到 Python」分支可用清空 PATH 穩定觸發並實際執行驗證，
    但同構的「找不到 repo 根」分支只在腳本被複製到磁碟根時才會觸發（見腳本
    第 26 行註解），無法在不需要磁碟根寫入權限的前提下安全地實際執行觸發。
    改用靜態文字比對鎖住兩個分支同時擁有修復，防止「只修一個分支」的回歸
    （SD 一審 bug-injection 證實：只還原其中一支修復，行為測試仍全綠）。
    """

    def test_both_dotsourced_failure_branches_set_lastexitcode_before_return(self) -> None:
        text = _DEV_START_PS1.read_text(encoding="utf-8")
        fixed = text.count("if ($DotSourced) { $global:LASTEXITCODE = 1; return }")
        bare = text.count("if ($DotSourced) { return }")
        self.assertEqual(
            fixed, 2,
            f"預期兩處 dot-source 失敗分支（找不到 repo 根／找不到 Python）皆設 "
            f"$LASTEXITCODE，實際命中 {fixed} 處",
        )
        self.assertEqual(
            bare, 0,
            "偵測到未設 $LASTEXITCODE 的裸 `if ($DotSourced) { return }`，"
            "回歸至修復前的失敗語意",
        )


# ===========================================================================
# 第二部分（R67-C17）：tools/dev_start.sh 的 zsh／bash 實跑載具
# 設計理由與收納契約見檔頭 docstring「第二部分」。
# ===========================================================================

# stub 核心：把「殼到底把什麼交給核心、從哪裡叫到它」寫成 JSON 證物。
# `__file__` 解析後的絕對路徑就是 `${(%):-%x}` / `${BASH_SOURCE[0]}` 路徑解析是否正確
# 的鐵證——解析錯了根本叫不到這支檔案。
_DS_STUB_CORE = """\
import json, os, sys
from pathlib import Path
Path(os.environ["DS_STUB_MARKER"]).write_text(
    json.dumps({"argv": sys.argv[1:], "self": str(Path(__file__).resolve())}),
    encoding="utf-8",
)
raise SystemExit(int(os.environ.get("DS_STUB_RC", "0")))
"""

# stub activate：只做真 activate 對本殼而言唯一可觀測的契約（設 VIRTUAL_ENV + 改 PATH）。
_DS_STUB_ACTIVATE = """\
VIRTUAL_ENV="{root}/.venv"
export VIRTUAL_ENV
PATH="$VIRTUAL_ENV/bin:$PATH"
export PATH
"""

_DS_UNSET = "__UNSET__"


def _ds_shell_path(name: str) -> str | None:
    """回傳可用的 shell 路徑（`shutil.which` 找不到時退回 /bin/<name>，macOS 系統 zsh）。"""
    found = shutil.which(name)
    if found:
        return found
    fallback = Path("/bin") / name
    return str(fallback) if fallback.exists() else None


_ZSH = _ds_shell_path("zsh")
_SH_BASH = _ds_shell_path("bash")


@unittest.skipIf(
    os.name == "nt",
    "tools/dev_start.sh 檔頭自陳為 macOS/Linux 專用（Windows 對等＝tools/dev_start.ps1，"
    "由本檔第一部分覆蓋）——不在 Windows 上驗證非目標平台的殼",
)
class TestDevStartShShellCarrier(unittest.TestCase):
    """在 tmp fake repo 內以真 shell 實跑真 dev_start.sh（stub 核心／stub activate）。"""

    def setUp(self) -> None:
        self.assertTrue(_DEV_START_SH.is_file(), f"受測物不存在：{_DEV_START_SH}")
        # `.resolve()`：macOS 的 /var 是指向 /private/var 的 symlink，stub 核心回報的
        # `Path(__file__).resolve()` 會是 /private/var/…；不先正規化會拿兩種寫法比對而假紅。
        self.tmp = Path(tempfile.mkdtemp(prefix="ds_shell_")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

        self.root = self.tmp / "repo"
        (self.root / "tools" / "lib").mkdir(parents=True)
        (self.root / ".venv" / "bin").mkdir(parents=True)

        shutil.copy(_DEV_START_SH, self.root / "tools" / "dev_start.sh")
        shutil.copy(_GUARD_LIB_SH, self.root / "tools" / "lib" / "windowsapps_guard.sh")
        (self.root / "tools" / "dev_start.py").write_text(
            _DS_STUB_CORE, encoding="utf-8", newline="\n"
        )
        (self.root / ".venv" / "bin" / "activate").write_text(
            _DS_STUB_ACTIVATE.format(root=self.root.as_posix()), encoding="utf-8", newline="\n"
        )
        # 殼優先選 `$root/.venv/bin/python`（`[ -x ]`）——以 sh wrapper 轉呼叫目前直譯器，
        # 免建真 venv。
        venv_py = self.root / ".venv" / "bin" / "python"
        venv_py.write_text(
            f'#!/bin/sh\nexec {shlex.quote(sys.executable)} "$@"\n',
            encoding="utf-8", newline="\n",
        )
        venv_py.chmod(0o755)

        self.core_marker = self.tmp / "core_marker.json"
        self.post_marker = self.tmp / "post_source.txt"

    # ------------------------------------------------------------------ helpers

    def _env(self, stub_rc: int) -> dict[str, str]:
        env = dict(os.environ)
        env["DS_STUB_MARKER"] = str(self.core_marker)
        env["DS_STUB_RC"] = str(stub_rc)
        # 外層若已在 venv 內，VIRTUAL_ENV 會被繼承 → 「有沒有啟用 venv」的斷言全部假綠。
        env.pop("VIRTUAL_ENV", None)
        return env

    def _source_script(self, args: str) -> str:
        """組出「source 之後把證物寫進外部檔」的 shell 片段。

        證物寫在**重導向的複合命令**裡：dev_start.sh 若誤走 `exit` 路徑殺掉本 shell，
        這段就永遠不會執行、檔案不存在——正是 macOS compat-CI 那個 step 抓不到的形狀。
        """
        sh = shlex.quote(str(self.root / "tools" / "dev_start.sh"))
        post = shlex.quote(str(self.post_marker))
        return (
            f"source {sh} {args}\n"
            "rc=$?\n"
            "{\n"
            '  printf "RC=%s\\n" "$rc"\n'
            f'  printf "VENV=%s\\n" "${{VIRTUAL_ENV-{_DS_UNSET}}}"\n'
            f'  printf "DSSOURCED=%s\\n" "${{_ds_sourced-{_DS_UNSET}}}"\n'
            f'  printf "DSRC=%s\\n" "${{_ds_rc-{_DS_UNSET}}}"\n'
            f"}} > {post}\n"
        )

    def _run_sourced(self, shell: str, args: str = "--no-sync --probe", stub_rc: int = 0):
        """在**非 repo 根**的 cwd 以 `shell -c` source 受測殼，回傳 (rc, stdout, stderr)。"""
        proc = subprocess.run(
            [shell, "-c", self._source_script(args)],
            cwd=str(self.tmp),  # 刻意不是 repo 根：靠 cwd 猜路徑的實作會當場失敗
            capture_output=True, env=self._env(stub_rc), timeout=120,
        )
        return (
            proc.returncode,
            proc.stdout.decode("utf-8", errors="replace"),
            proc.stderr.decode("utf-8", errors="replace"),
        )

    def _post(self) -> dict[str, str]:
        self.assertTrue(
            self.post_marker.exists(),
            "source 之後的證物檔不存在 ⇒ dev_start.sh 把呼叫端 shell 整個殺掉了"
            "（sourced 偵測回歸）。這正是使用者每天 `source tools/dev_start.sh` 時"
            "終端會直接關閉／整段 rc 被吞的形狀",
        )
        out: dict[str, str] = {}
        for line in self.post_marker.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                out[key] = value
        return out

    def _core(self) -> dict:
        self.assertTrue(
            self.core_marker.exists(),
            "核心 stub 未被執行 ⇒ 殼沒能把 tools/dev_start.py 的路徑解析出來"
            "（zsh 端即 `${(%):-%x}` 回歸；bash 端即 `${BASH_SOURCE[0]}` 回歸）",
        )
        return json.loads(self.core_marker.read_text(encoding="utf-8"))

    # ------------------------------------------------------------- 共用情境主體

    def _assert_sourced_happy_path(self, shell: str) -> None:
        rc, out, err = self._run_sourced(shell)
        self.assertEqual(rc, 0, f"stdout={out}\nstderr={err}")
        post = self._post()
        self.assertEqual(post["RC"], "0", f"source 的 rc 非 0：{post}")
        self.assertEqual(
            post["VENV"], str(self.root / ".venv"),
            f"被 source 時必須自動啟用 .venv（VIRTUAL_ENV），實得 {post['VENV']!r}——"
            f"這是 ONBOARDING §2.1 對使用者承諾的唯一可觀測效果",
        )
        self.assertEqual(
            (post["DSSOURCED"], post["DSRC"]), (_DS_UNSET, _DS_UNSET),
            f"呼叫端 shell 殘留 _ds_* 變數：{post}——檔尾 "
            f'`eval "unset _ds_rc; return $_ds_rc"` 的語意已回歸',
        )
        core = self._core()
        self.assertEqual(
            core["self"], str(self.root / "tools" / "dev_start.py"),
            "核心不是從腳本自身所在的 repo 根被叫到——路徑解析退化為靠 cwd 猜",
        )
        self.assertEqual(
            core["argv"], ["--no-sync", "--probe"], "位置參數未原樣透傳給核心",
        )

    def _assert_core_failure_propagates(self, shell: str) -> None:
        rc, out, err = self._run_sourced(shell, stub_rc=3)
        post = self._post()
        self.assertEqual(
            post["RC"], "3",
            f"核心 rc=3 卻沒有原樣傳回呼叫端：{post}（stdout={out} stderr={err}）——"
            f"開工失敗被吞成 0，使用者會在壞掉的環境上開始一整天的工作。"
            f"這也正是本檔第一部分（DEF-101-304）拿來當對照組的那句 .sh 側宣稱",
        )
        self.assertEqual(
            post["VENV"], _DS_UNSET, f"核心失敗時不得啟用 .venv，實得 {post['VENV']!r}",
        )
        self.assertEqual(rc, 0, f"外層 shell 不應被殺（rc={rc}）：{err}")

    def _assert_executed_not_sourced(self, shell: str) -> None:
        """以「執行」而非 source：不動呼叫端 shell、rc 照傳。"""
        proc = subprocess.run(
            [shell, str(self.root / "tools" / "dev_start.sh"), "--no-sync", "--probe"],
            cwd=str(self.tmp), capture_output=True, env=self._env(5), timeout=120,
        )
        out = proc.stdout.decode("utf-8", errors="replace")
        self.assertEqual(
            proc.returncode, 5,
            f"執行（非 source）時核心 rc 必須原樣成為腳本 rc：rc={proc.returncode}\n{out}",
        )
        self.assertEqual(
            self._core()["argv"], ["--no-sync", "--probe"], "執行模式下位置參數未透傳",
        )
        self.assertFalse(
            self.post_marker.exists(), "執行模式不該產生 source 證物檔（測試自身健全性）"
        )

    # -------------------------------------------------------------------- zsh

    @unittest.skipIf(_ZSH is None, "本機無 zsh（macOS 預設 shell）——zsh 分支無法實跑")
    def test_zsh_sourced_happy_path(self) -> None:
        """zsh source：不殺 shell、路徑解析正確、參數透傳、自動啟用 venv、零殘留。

        WHY：macOS 使用者敲的就是這一條；先前唯一驗證者是已停擺的 macos-compat-ci。
        """
        self._assert_sourced_happy_path(_ZSH)

    @unittest.skipIf(_ZSH is None, "本機無 zsh（macOS 預設 shell）——zsh 分支無法實跑")
    def test_zsh_core_failure_propagates_and_does_not_activate(self) -> None:
        self._assert_core_failure_propagates(_ZSH)

    @unittest.skipIf(_ZSH is None, "本機無 zsh（macOS 預設 shell）——zsh 分支無法實跑")
    def test_zsh_executed_not_sourced(self) -> None:
        self._assert_executed_not_sourced(_ZSH)

    # ------------------------------------------------------------------- bash

    @unittest.skipIf(_SH_BASH is None, "本機無 bash")
    def test_bash_sourced_happy_path(self) -> None:
        """bash 端同一組斷言：兩殼行為必須對等（殼內是**兩條不同的**程式碼路徑）。"""
        self._assert_sourced_happy_path(_SH_BASH)

    @unittest.skipIf(_SH_BASH is None, "本機無 bash")
    def test_bash_core_failure_propagates_and_does_not_activate(self) -> None:
        self._assert_core_failure_propagates(_SH_BASH)

    @unittest.skipIf(_SH_BASH is None, "本機無 bash")
    def test_bash_executed_not_sourced(self) -> None:
        self._assert_executed_not_sourced(_SH_BASH)


class TestDevStartShProbeStructure(unittest.TestCase):
    """本節**自身**的鑑別力鎖：證物必須寫在 source 之後的外部重導向檔。

    WHY（這條鎖為何值得存在）：R67 實測證明「斷言寫在同一個 shell 的 source 之後」
    這個直覺寫法，對 sourced 偵測回歸結構性失明（腳本 `exit` 會把斷言連同 shell 一起
    帶走，rc=0 全綠）。macOS compat-CI 的 step 就是這個形狀。若日後有人把本節「簡化」
    回同款形狀，失明會靜默回來、而且沒有任何訊號——故把結構本身釘住。
    """

    def test_evidence_is_written_to_an_out_of_process_file(self) -> None:
        src = Path(__file__).read_text(encoding="utf-8")
        self.assertIn(
            "post_marker", src,
            "證物檔機制（post_marker）消失——斷言若改回 in-process，"
            "sourced 偵測回歸將再次靜默通過",
        )
        self.assertIn(
            "self.assertTrue(\n            self.post_marker.exists(),", src,
            "缺少「證物檔必須存在」的斷言——那正是把 in-process 失明轉成紅燈的那一行",
        )


if __name__ == "__main__":
    unittest.main()
