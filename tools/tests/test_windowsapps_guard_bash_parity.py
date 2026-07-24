#!/usr/bin/env python3
"""WindowsApps 空殼排除 guard — bash 側對稱實作收斂鎖（R43 Scan-B，DEF-101-353）。

背景：`tools/lib/WindowsAppsGuard.ps1::Test-IsRealPython`（R37 抽出）與
`bootstrap_core.py::_is_windows_apps_stub`（Python 側）皆只涵蓋各自語言的
呼叫端，repo 內另有 9 支 tracked bash 腳本（含 `tools/git-hooks/pre-push` 這個
每次 push 都會實際執行的 dispatcher 本體）各自用裸 `command -v python`／
`command -v python3` 判斷可用性，從未排除 Windows Store App Execution Alias
空殼——Git Bash on Windows 會繼承 Windows PATH，同樣會命中
`%LOCALAPPDATA%\\Microsoft\\WindowsApps` 底下系統自動註冊的空殼
`python.exe`/`python3.exe`（`command -v` 判定為「存在」，實際執行只會跳出
Microsoft Store 安裝提示，對 `pre-push` 這類阻斷式 hook 而言即為掛起）。

本檔比照既有 `test_windowsapps_guard_cross_consistency.py`（.ps1 側）的兩段式
結構鎖住 bash 側對稱實作：
  ① 共用函式本身的行為測試：以真實 subprocess 建構假 PATH 目錄（真直譯器 stub /
     WindowsApps 路徑 stub / 不存在），驗證 `is_real_python_candidate` 判斷邏輯。
  ② 存在性檢查：所有已知呼叫端須 dot-source 共用檔案並改用
     `is_real_python_candidate`，不得殘留繞過共用函式的裸 `command -v python`／
     `command -v python3` 判斷。

執行：python -m pytest tools/tests/test_windowsapps_guard_bash_parity.py -v
"""
from __future__ import annotations

import re
import shutil
import subprocess
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GUARD_SH = _REPO_ROOT / "tools" / "lib" / "windowsapps_guard.sh"

# 目前已知呼叫端（皆已改用 is_real_python_candidate；DEF-101-353 收斂範圍）。
_CALLER_FILES = [
    _REPO_ROOT / "tools" / "git-hooks" / "pre-push",
    _REPO_ROOT / "tools" / "lib" / "git_hooks_install_common.sh",
    _REPO_ROOT / "tools" / "dev_start.sh",
    _REPO_ROOT / "tools" / "bootstrap.sh",
    _REPO_ROOT / "tools" / "integration_gate.sh",
    _REPO_ROOT / "AutoClaude" / "tools" / "local_ci_gate.sh",
    _REPO_ROOT / "AutoClaude" / "tools" / "run_act.sh",
    _REPO_ROOT / "AutoClaude" / "tools" / "sd06_w3_staging_dryrun.sh",
    _REPO_ROOT / "AISDLC_SDD" / "scripts" / "ci-gate.sh",
]

# 裸 `command -v python`／`command -v python3` 可用性判斷殘留偵測——只認本 repo
# 既有慣例「重導向 /dev/null 作為條件判斷」的用法（`command -v python >/dev/null`），
# 不誤判註解文字或純資訊性 `$(command -v python)` 顯示用途（如 dev_start.sh 成功
# 訊息內嵌已解析路徑，非可用性判斷、不繞過 guard）。
_RAW_CHECK_RE = re.compile(r"command\s+-v\s+python3?\s*>\s*/dev/null")

# 較寬鬆的裸判斷偵測（供 repo-wide 前瞻掃描用，逐行比對、跳過註解行；涵蓋
# `command -v python || command -v python3 || true` 這類無 `>/dev/null` 的變體，
# 這是 install_post_commit.sh／run_local_nightly.sh 等實際存在的寫法，
# _RAW_CHECK_RE 的窄比對抓不到）。
_LOOSE_RAW_CHECK_RE = re.compile(r"command\s+-v\s+python3?\b")

# R43 二審 Architect 一審複查揪出：TestBashCallersEnrollment 原本只驗證固定
# 白名單（_CALLER_FILES），不是真正的 repo-wide 前瞻鎖——同一類「防增生鎖只
# 蓋到已知案例」缺陷（R41 對 _sanitize_component 呼叫點也犯過一次）。改為對
# git-tracked 全部 `*.sh` 做前瞻掃描；下列為明確判斷「WindowsApps 空殼排除
# guard 不適用」而豁免的檔案，皆附理由，供未來覆核：
_EXEMPT_SH_FILES = {
    # macOS 專屬本地驗證聚合腳本（docstring 明文「嚴格 bash 3.2（macOS /bin/bash）」
    # + 只由 macos-compat-ci.yml 呼叫）；WindowsApps 是 Windows Store 專屬機制，
    # 該資料夾不可能出現在 macOS PATH 上，guard 在此為無意義的防禦性死碼。
    "tools/macos_smoke_local.sh",
    # macOS 專屬 nightly 薄聚合器（docstring 明文「bash 3.2（macOS /bin/bash）」+
    # Windows 對等品是完全獨立的 run_local_nightly.ps1），同上理由豁免。
    "AutoClaude/tools/run_local_nightly.sh",
}


def _tracked_sh_files() -> list[str]:
    """git tracked 的全部 `*.sh` repo-relative 路徑（含子專案），比照既有
    `test_windowsapps_guard_cross_consistency.py::_tracked_files` 慣例，用
    `git ls-files` 而非 `Path.rglob`（天然排除 `.git`/`.venv`/`__pycache__`）。"""
    proc = subprocess.run(
        ["git", "-C", str(_REPO_ROOT), "-c", "core.quotePath=false",
         "ls-files", "--", "*.sh"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"git ls-files 失敗（rc={proc.returncode}；stderr={proc.stderr.strip()!r}）"
            "——掃描邊界不得靜默縮小"
        )
    return [line for line in proc.stdout.splitlines() if line]


def _bash_exe() -> str | None:
    return shutil.which("bash")


@unittest.skipUnless(_bash_exe(), "本機找不到 bash，略過 shell 行為驗證")
class TestSharedGuardShellFunctionBehavior(unittest.TestCase):
    """實際以 subprocess 執行共用函式，驗證三種情境判斷正確。

    fixture 的暫存目錄與候選可執行檔全部由 **bash 自身**的 `mktemp -d` 建立，
    不透過 Python `tempfile` 產生 Windows 樣式路徑（`C:\\Users\\...`）字面塞進
    `$PATH`——R43 實測發現 `C:/...` 這類含磁碟機代號冒號的路徑塞進以 `:` 分隔的
    `$PATH` 字串會被冒號本身腰斬（`C` 與 `/Users/...` 誤判為兩個獨立、皆不存在
    的路徑片段），導致 fixture 目錄從未真正被搜尋到、`command -v python` 悄悄
    改為命中繼承自呼叫端行程環境的其他 `python`（如已啟用的 `.venv`），使本測試
    看似「跑過」卻完全沒驗證到目標邏輯——與本輪（R43 baseline agent）在真實
    `test_bash_probe_spec_contract.py` 上踩到的路徑格式陷阱同一根因類別。"""

    def _run(self, subdir_name: str, candidate: str = "python") -> bool:
        script = (
            'set -e\n'
            'tmp="$(mktemp -d)"\n'
            'trap \'rm -rf "$tmp"\' EXIT\n'
            f'mkdir -p "$tmp/{subdir_name}"\n'
            f'cat > "$tmp/{subdir_name}/python" <<\'EOS\'\n'
            '#!/usr/bin/env bash\n'
            'echo real\n'
            'EOS\n'
            f'chmod +x "$tmp/{subdir_name}/python"\n'
            f'PATH="$tmp/{subdir_name}:$PATH"\n'
            f'. "{_GUARD_SH.as_posix()}"\n'
            f'is_real_python_candidate {candidate}\n'
        )
        r = subprocess.run(
            [_bash_exe(), "-c", script],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
        )
        return r.returncode == 0

    def test_real_candidate_accepted(self) -> None:
        self.assertTrue(self._run("real"))

    def test_windowsapps_stub_rejected(self) -> None:
        self.assertFalse(self._run("WindowsApps"))

    def test_missing_candidate_rejected(self) -> None:
        self.assertFalse(self._run("real", candidate="totally_nonexistent_xyz"))

    def test_mixed_case_windowsapps_stub_rejected(self) -> None:
        """R43 二審 Architect/SD 各自獨立揪出：一審初版 `case *WindowsApps*)` 對
        bash 而言預設大小寫敏感，`WINDOWSAPPS`（或其他大小寫變體）會漏放——與
        `WindowsAppsGuard.ps1`（`-notlike` 本身大小寫不敏感）／`bootstrap_core.py`
        （逐片段 `.lower()`）兩份姊妹 SSOT 不對稱。"""
        self.assertFalse(self._run("WINDOWSAPPS"))

    def test_legit_dir_merely_containing_substring_is_accepted(self) -> None:
        """R43 二審 Architect/SD 各自獨立揪出：一審初版裸子字串比對會誤傷路徑僅
        「含有」WindowsApps 字面值、但並非該路徑片段本身的合法目錄（如
        `MyWindowsAppsBackup/python`），對 pre-push 這類阻斷式 hook 而言等同誤報
        「找不到 python」。"""
        self.assertTrue(self._run("MyWindowsAppsBackup"))


class TestBashCallersEnrollment(unittest.TestCase):
    """所有已知呼叫端須改用共用函式，且不得殘留繞過它的裸 command -v 判斷。"""

    def test_shared_guard_file_exists_and_defines_the_function(self) -> None:
        self.assertTrue(_GUARD_SH.is_file(), f"{_GUARD_SH} 不存在")
        text = _GUARD_SH.read_text(encoding="utf-8")
        self.assertIn(
            "is_real_python_candidate()", text,
            "tools/lib/windowsapps_guard.sh 未定義 is_real_python_candidate 共用函式",
        )
        self.assertIn("WindowsApps", text)

    def test_all_known_callers_source_shared_guard(self) -> None:
        for f in _CALLER_FILES:
            with self.subTest(file=str(f.relative_to(_REPO_ROOT))):
                self.assertTrue(f.is_file(), f"{f} 不存在")
                text = f.read_text(encoding="utf-8")
                self.assertIn(
                    "windowsapps_guard.sh", text,
                    f"{f} 未 dot-source 共用 guard 檔案",
                )
                self.assertIn(
                    "is_real_python_candidate", text,
                    f"{f} 未改用 is_real_python_candidate 判斷 python 可用性",
                )

    def test_no_raw_unguarded_python_check_remains(self) -> None:
        for f in _CALLER_FILES:
            with self.subTest(file=str(f.relative_to(_REPO_ROOT))):
                text = f.read_text(encoding="utf-8")
                hits = _RAW_CHECK_RE.findall(text)
                self.assertEqual(
                    hits, [],
                    f"{f} 殘留繞過共用 guard 的裸 `command -v python`/`python3` 判斷：{hits}",
                )

    def test_repo_wide_scan_finds_no_unmigrated_sh_scripts(self) -> None:
        """R43 二審 Architect 一審複查揪出的真實系統性缺口：本類別原本只驗證固定
        白名單 `_CALLER_FILES`，本身就是「防增生鎖只蓋到已知案例」——Architect 用
        全 repo grep 實測找到 3 支未列入清單、仍是裸判斷的既有 tracked 腳本
        （`tools/macos_smoke_local.sh`／`AutoClaude/tools/run_local_nightly.sh`／
        `AISDLC_SDD/AISDLC_SDD_v0.30/tools/install_hooks/install_post_commit.sh`）。
        本測試改為對 git-tracked 全部 `*.sh` 做前瞻掃描：逐行跳過註解，命中裸
        `command -v python`/`python3` 判斷、且該檔案既不在 `_CALLER_FILES`（已收斂）
        也不在 `_EXEMPT_SH_FILES`（明確記載豁免理由）者視為未收斂新缺口。"""
        known_relpaths = {str(f.relative_to(_REPO_ROOT)).replace("\\", "/") for f in _CALLER_FILES}
        unmigrated: list[str] = []
        for rel in _tracked_sh_files():
            if rel in known_relpaths or rel in _EXEMPT_SH_FILES:
                continue
            path = _REPO_ROOT / rel
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if "windowsapps_guard.sh" in text:
                continue  # 已 source 共用 guard，即使仍含 fallback 分支的裸判斷也不算未收斂
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if _LOOSE_RAW_CHECK_RE.search(line):
                    unmigrated.append(rel)
                    break
        self.assertEqual(
            unmigrated, [],
            f"發現未收斂的裸 python 可用性判斷（未 source windowsapps_guard.sh 且未登記"
            f"豁免）：{unmigrated}——請改用 is_real_python_candidate 或於 "
            f"_EXEMPT_SH_FILES 附理由登記豁免",
        )


if __name__ == "__main__":
    unittest.main()
