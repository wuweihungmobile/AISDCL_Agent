#!/usr/bin/env python3
"""nightly 載具的直譯器必須「決定性 + 可取證」（DEF-101-506，紀律 #14 延伸）。

WHY（2026-07-27 真機事故）：`run_local_nightly.ps1` 把直譯器存成字面 token
`$script:PyExe = 'python'`，每個呼叫點都由 PATH **現場解析**。於是同一支 nightly：

  - schtasks 排程下 → pyenv-win 的 python（`python.bat` shim，且裝了 psycopg2）
  - 已啟用 monorepo .venv 的終端機／agent 下 → `.venv\\Scripts\\python.exe`
    （真 .exe，且**未**裝 `[postgres,pgvector]` 選配）

兩者跑出來的紅綠不可互相比較：實測一次以 .venv 跑出 `pg-e2e=1`（psycopg2 缺席）
與 `perf=1` 兩個假紅並寫進 `nightly_latest.log`；更隱蔽的是它讓 DEF-101-503
（`%` 被 batch shim 吃掉）的修復「綠得沒有鑑別力」——真 .exe 本來就不觸發該 bug，
沒修也會綠。而 log 當時只印字面 token「python」，事後完全無法指認是哪一顆。

🔴 **R59 補述（DEF-101-522 教訓）**：本檔原本 A/B/C 三項**全是行級靜態檢查**，
於是當 PATH 正規化區塊的比對「形狀齊備但語意永遠不成立」時（`Activate.ps1` 插入的是
`.venv/Scripts` 正斜線、`Join-Path` 產生 `.venv\Scripts` 反斜線 → 比對必不等），本檔
當時的斷言全綠（**R59 二審 QA 訂正**：本處原寫「20 支」、下方 A 項註解原寫「7 支斷言」，QA 副本注入實測為 **4 支測試／8 條斷言**全綠；數字改為不寫死以免再過期）。**形狀鎖對「比對永遠不成立」這類缺陷結構上零鑑別力**，故 R59 新增第
D 項＝**行為級鎖**（真的把該區塊的比對式抽出來在 PowerShell 子行程裡跑一次）。

本檔鎖四件事（A/B/C 為行級靜態檢查、D 為行為級實跑）：
  A. `.ps1` 必須有「已啟用 venv → 自本行程 PATH 移除其 Scripts」的正規化區塊，
     且必須有「移除後找不到 python 就還原」的降級分支（載具正規化不得讓整晚
     驗證開天窗）。
  B. 兩支載具都必須把**解析後的直譯器路徑**寫進 log（禁止只印字面 token）。
  C. mac 側必須維持「絕對路徑釘死」而非 PATH 現場解析。
  D.（R59 新增，行為級）自 `.ps1` 抽出 PATH 正規化的**比對式本體**，在 PowerShell
     子行程裡對一個含**正斜線**寫法的合成 PATH 執行，斷言該項真的被判為相符並移除。
     這是唯一能抓到 DEF-101-522 的形狀——A 項只看「有沒有 `-split ';'`／`Join-Path`／
     `$pathBefore`」，那些在缺陷存在時全部齊備。

刻意不鎖「兩平台必須用同一顆直譯器」：mac 釘 `.venv/bin/python`、Windows 走
pyenv，是各自既有且各自綠的政策；本缺陷要根治的是「**同一平台上因啟動方式不同
而漂移**」，不是強推跨平台統一（那會讓 Windows 排程失去 psycopg2）。
"""
from __future__ import annotations

import platform
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PS1 = _ROOT / "AutoClaude" / "tools" / "run_local_nightly.ps1"
_SH = _ROOT / "AutoClaude" / "tools" / "run_local_nightly.sh"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


class TestCarrierFilesExist(unittest.TestCase):
    def test_both_carriers_present(self):
        """檔案改名/搬家時本檔其餘斷言會全部靜默失效，先釘存在性。"""
        self.assertTrue(_PS1.is_file(), f"找不到 {_PS1}")
        self.assertTrue(_SH.is_file(), f"找不到 {_SH}")


class TestWindowsInterpreterNormalization(unittest.TestCase):
    """A：Windows 側必須主動把「已啟用 venv」正規化掉，使解析與 schtasks 等價。"""

    def test_has_virtual_env_detection(self):
        self.assertRegex(
            _read(_PS1), r"if\s*\(\s*\$env:VIRTUAL_ENV\s*\)",
            "run_local_nightly.ps1 必須偵測 $env:VIRTUAL_ENV——否則已啟用 venv 的終端機/"
            "agent 跑出來的紅綠與 schtasks 排程不可比較（DEF-101-506）")

    def test_removes_active_venv_scripts_from_path(self):
        text = _read(_PS1)
        # R59 DEF-101-522：原斷言寫死 `$env:PATH -split ';'`。修復後兩次比對（算命中數、
        # 算保留集）一律對 `$pathBefore` 這份**同一快照**做，避免中途被改動造成兩次比對
        # 依據不同；故本斷言放寬為「對某個 PATH 字串做 `-split ';'`」，語意不變（仍要求
        # 真的重組 PATH、不能只印警告了事），但不再把實作細節寫死。
        self.assertRegex(
            text, r"\$(?:env:PATH|pathBefore)\s+-split\s+';'",
            "必須實際重組 PATH 以移除 venv Scripts，不能只印警告了事")
        self.assertRegex(text, r"Join-Path\s+\$env:VIRTUAL_ENV\s+'Scripts'",
                         "必須以 VIRTUAL_ENV 推導出要移除的 Scripts 目錄")
        # DEF-101-522 形狀面補鎖（行為面見 TestPathNormalisationBehaviour）：
        # 比對前必須把斜線正規化，否則 Activate.ps1 的正斜線寫法永遠不相符。
        self.assertIn(
            ".Replace('/', '\\')", text,
            "PATH 比對前必須把 `/` 正規化為 `\\`——Activate.ps1 插入的是 "
            "`$env:VIRTUAL_ENV/Scripts`（正斜線），不正規化則比對永遠不成立（DEF-101-522）")

    def test_normalisation_block_precedes_pyexe_resolution(self):
        """QA-R59-03：位置鎖。A 項其餘斷言都是**全檔** assertIn/assertRegex，只要區塊
        存在就綠——把整塊搬到 `$script:PyExe` 解析之後（例如某次「把 PATH 設定集中管理」
        的重構），同類其餘斷言仍全綠（二審 QA 副本注入實測：4 支測試／8 條斷言），但從已啟用 venv 啟動時解析到的仍是 `.venv` 的 python，
        DEF-101-506 完全復發、log 還會誠實印出錯的那一顆。**存在但無效**是另一個成因類別。
        技法同本類別既有的 guard dot-source 順序斷言。"""
        text = _read(_PS1)
        norm_at = text.index("if ($env:VIRTUAL_ENV)")
        pyexe_at = text.index("$script:PyExe = $null")
        self.assertLess(
            norm_at, pyexe_at,
            "PATH 正規化區塊必須在 $script:PyExe 解析**之前**——否則正規化對本輪實際"
            "使用的直譯器毫無影響（DEF-101-506／QA-R59-03）",
        )

    def test_post_strip_check_uses_real_python_guard(self):
        """移除 venv 後的『還有沒有 python』判斷必須用 Test-IsRealPython：若用裸
        Get-Command，PATH 上只剩 WindowsApps 空殼時會誤判為可用而不還原。"""
        text = _read(_PS1)
        strip_block = text.split("if ($env:VIRTUAL_ENV)", 1)[-1].split("try {", 1)[0]
        self.assertIn("Test-IsRealPython -CandidateName 'python'", strip_block,
                      "正規化區塊必須以 Test-IsRealPython 判斷，不可用裸 Get-Command")
        # guard SSOT 必須在正規化區塊之前 dot-source，否則上面那行是未定義函式
        self.assertLess(
            text.index("tools/lib/WindowsAppsGuard.ps1"), text.index("if ($env:VIRTUAL_ENV)"),
            "WindowsAppsGuard.ps1 必須在 venv 正規化區塊之前載入")

    def test_has_restore_fallback_when_no_other_python(self):
        """降級分支：移除後若沒有其他 python，必須還原，不可讓整晚驗證開天窗。"""
        text = _read(_PS1)
        self.assertIn("$pathBefore", text, "必須保留還原用的 PATH 快照")
        self.assertRegex(
            text, r"\$env:PATH\s*=\s*\$pathBefore",
            "必須有『找不到其他 python 就還原 PATH』的降級路徑（DEF-101-506）")


class TestInterpreterIsForensicallyLogged(unittest.TestCase):
    """B：兩支載具都要把解析後的直譯器寫進 log；只印字面 token 等於沒印。"""

    def test_ps1_logs_resolved_path_not_bare_token(self):
        text = _read(_PS1)
        # 必須解析出絕對路徑，且必須用**兩步式**取 .Source——鏈式
        # `(Get-Command ... -ErrorAction SilentlyContinue).Source` 在 StrictMode 3.0
        # 下 $null.Source 會拋例外（紀律 #14 後半，另有 test_run_local_nightly_static
        # 的機械鎖；本修復初稿即因寫成鏈式被它攔下）。
        # 用 $script:PyExe 而非裸 `python` 字面值：test_windowsapps_guard_cross_consistency
        # 的呼叫點層級判準要求檔內不得有裸字面值 python 呼叫（本修復初稿寫成
        # `Get-Command python` 而被它攔下）。
        self.assertRegex(
            text, r"\$pyCmd\s*=\s*Get-Command\s+\$script:PyExe",
            "run_local_nightly.ps1 必須解析出 python 絕對路徑供取證（DEF-101-506）")
        self.assertRegex(
            text, r"\$pyResolved\s*=\s*if\s*\(\s*\$pyCmd\s*\)",
            "取 .Source 必須兩步式（先存變數再判 $null），不可鏈式存取（紀律 #14）")
        self.assertRegex(
            text, r"可用性驗證通過[^\n]*\$pyResolved",
            "驗證通過的 log 行必須帶上解析後路徑 $pyResolved")
        # 反向鎖：不可退回舊寫法「python 可用性驗證通過…：$script:PyExe」
        self.assertNotRegex(
            text, r"可用性驗證通過[^\n]*：\$script:PyExe\"",
            "log 不可只印字面 token $script:PyExe（值恆為 'python'，無取證價值）")

    def test_sh_logs_resolved_path(self):
        self.assertRegex(
            _read(_SH), r"python 直譯器：",
            "run_local_nightly.sh 必須印出解析後的直譯器路徑，與 .ps1 側取證對稱")


class TestMacInterpreterStaysPinned(unittest.TestCase):
    """C：mac 側的「絕對路徑釘死」是它不受本缺陷影響的原因，不可被改回現場解析。"""

    def test_pins_venv_absolute_path(self):
        self.assertRegex(
            _read(_SH), r'PY="\$ROOT/\.venv/bin/python"',
            "run_local_nightly.sh 必須維持絕對路徑釘死；改回裸 `python` 會把 Windows "
            "側的啟動方式漂移問題複製到 mac（DEF-101-506）")


class TestDetectorItself(unittest.TestCase):
    """紀律「驗證鏡子自身要被驗證」：確認上面的反向鎖真的抓得到舊寫法。"""

    def test_old_bare_token_pattern_would_be_caught(self):
        legacy = 'Log "python 可用性驗證通過（非 WindowsApps 空殼）：$script:PyExe"'
        self.assertTrue(
            re.search(r"可用性驗證通過[^\n]*：\$script:PyExe\"", legacy),
            "反向鎖的 regex 必須能命中修復前的舊寫法，否則該斷言是空殼")


# ── D 項：行為級鎖（R59 DEF-101-522）──────────────────────────────────────────
_NORM_HIT_RE = re.compile(
    r"\$removed\s*=\s*@\(\s*\$pathBefore\s+-split\s+';'\s*\|\s*Where-Object\s*\{(?P<hit>.+?)\}\s*\)\.Count",
    re.DOTALL,
)
_NORM_KEEP_RE = re.compile(
    r"\$kept\s*=\s*@\(\s*\$pathBefore\s+-split\s+';'\s*\|\s*Where-Object\s*\{(?P<keep>.+?)\}\s*\)",
    re.DOTALL,
)


class TestPathNormalisationBehaviour(unittest.TestCase):
    """D 項：PATH 正規化的比對式必須真的能命中 `Activate.ps1` 實際寫入的形態。

    WHY 必須是行為級（DEF-101-522）：`.venv\\Scripts\\Activate.ps1` 插入 PATH 的字串是
    `"$env:VIRTUAL_ENV/Scripts"`（**正斜線**），而 `Join-Path` 產生反斜線。初版直接以
    `-ne` 比字串，在原生 PowerShell 下**永遠不相符** → venv 的 python 留在 PATH 上、
    腳本卻走進成功分支印出「已移除…已與 schtasks 排程等價」。從 Git Bash 啟動時 msys
    會把該項轉成反斜線、比對剛好成立，這就是本輪與上一輪都沒測出來的原因（載具剛好會過）。
    """

    @unittest.skipUnless(
        platform.system() == "Windows" and shutil.which("powershell"),
        "[WINDOWS-NATIVE-ONLY] 本鎖要在真 PowerShell 上執行抽出的比對式；"
        "PATH 分隔符與斜線語意僅 Windows 成立（R43 DEF-101-348 標籤，"
        "供 run_root_unittests.py 彙整可見度）",
    )
    def test_forward_slash_path_entry_is_matched_and_removed(self) -> None:
        src = _read(_PS1)
        hit = _NORM_HIT_RE.search(src)
        keep = _NORM_KEEP_RE.search(src)
        self.assertIsNotNone(hit, "找不到 $removed 的比對式——PATH 正規化區塊結構已變動，請同步本鎖")
        self.assertIsNotNone(keep, "找不到 $kept 的比對式——PATH 正規化區塊結構已變動，請同步本鎖")

        # 合成情境：VIRTUAL_ENV 為反斜線絕對路徑，PATH 內該項寫成**正斜線**
        # （＝Activate.ps1 的真實寫法），另含一個無關項確認不被誤刪。
        # 路徑以 tempfile 動態取得而非寫死磁碟機字母——`test_platform_neutral_paths.py`
        # 有一道禁止 .py 內出現寫死 Windows 假路徑的鎖（R59 落地本測試時當場被它攔下），
        # 且用真實臨時目錄比假路徑更忠實。
        with tempfile.TemporaryDirectory() as td:
            venv_dir = str(Path(td) / "venv")
            other_dir = str(Path(td) / "other")
            fwd = venv_dir.replace("\\", "/") + "/Scripts"
            script = "\n".join([
                f"$env:VIRTUAL_ENV = '{venv_dir}'",
                f"$pathBefore = '{other_dir};{fwd};'",
                "$venvScripts = Join-Path $env:VIRTUAL_ENV 'Scripts'",
                "$venvNorm = $venvScripts.Replace('/', '\\').TrimEnd('\\')",
                f"$removed = @($pathBefore -split ';' | Where-Object {{{hit.group('hit')}}}).Count",
                f"$kept = @($pathBefore -split ';' | Where-Object {{{keep.group('keep')}}})",
                "Write-Output \"REMOVED=$removed\"",
                "Write-Output \"KEPT=$($kept -join ',')\"",
            ])
            expected_kept = other_dir
            proc = subprocess.run(
                [shutil.which("powershell"), "-NoProfile", "-Command", script],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
            )
        out = proc.stdout
        self.assertEqual(proc.returncode, 0, f"抽出的比對式執行失敗：\n{proc.stdout}\n{proc.stderr}")
        self.assertIn(
            "REMOVED=1", out,
            "正斜線寫法的 venv Scripts 未被判為相符（REMOVED != 1）——DEF-101-522 迴歸："
            f"比對式對 `Activate.ps1` 的真實寫法無效，正規化區塊是死碼。實得：\n{out}",
        )
        self.assertIn(
            f"KEPT={expected_kept}", out,
            f"無關的 PATH 項被誤刪或保留集算錯。實得：\n{out}",
        )

    def test_zero_hit_must_not_claim_equivalence(self) -> None:
        """後置條件鎖：命中 0 項時不得宣告「已等價」。

        刻意不用「總項數變化」做自檢——實測 `$_ -and` 會濾掉 PATH 尾端的空字串項，
        造成 31→30 的假象，用總數自檢會被騙（DEF-101-522 實測記錄）。
        """
        src = _read(_PS1)
        self.assertRegex(
            src, r"if\s*\(\s*\$removed\s+-eq\s+0\s*\)",
            "缺少「命中 0 項」的後置條件分支——零命中時仍會印出等價宣稱（DEF-101-522）",
        )
        zero_branch = re.search(r"if\s*\(\s*\$removed\s+-eq\s+0\s*\)\s*\{(.+?)\}\s*else", src, re.DOTALL)
        self.assertIsNotNone(zero_branch, "零命中分支結構已變動，請同步本鎖")
        body = zero_branch.group(1)
        self.assertIn("WARN", body, "零命中分支必須是 WARN 而非成功訊息")
        self.assertNotIn("使直譯器解析與 schtasks 排程等價", body,
                         "零命中分支不得出現等價宣稱")


# 🔴 本區塊必須留在檔尾。R59 二審 QA-R59-P3-1：初稿把它誤放在 D 項類別**之前**
# （原第 178 行），直接 `python test_nightly_interpreter_determinism.py` 時
# unittest.main() 在 D 項類別尚未定義時就開跑 → 只收 10 支、靜默漏掉
# TestPathNormalisationBehaviour（本檔唯一的行為級鎖，守 P1 DEF-101-522）。
# 「載具自己少跑兩支卻回報 OK」正是本輪 Scan-F 要抓的形狀，故留註警示。
if __name__ == "__main__":
    unittest.main()
