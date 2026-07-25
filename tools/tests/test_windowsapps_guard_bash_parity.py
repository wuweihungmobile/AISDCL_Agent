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
import sys
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
    # R44 Architect 深度架構評估新增：本檔docstring 第 2 行明文「由
    # tools/run_local_nightly.ps1 透過 `docker run python:3.11-slim bash
    # /workspace/tools/run_mutmut_in_docker.sh` 呼叫」——結構性只在 Linux
    # container 內執行（官方 python:3.11-slim image 為 base，python3 保證存在於
    # 該映像檔），Windows Store App Execution Alias 空殼是 Windows 原生 PATH
    # 專屬機制，Linux container 內不可能出現，guard 在此無意義（同
    # macos_smoke_local.sh／run_local_nightly.sh 的「非 Windows 執行環境」豁免
    # 精神，只是換成 Linux container 而非 macOS）。
    "AutoClaude/tools/run_mutmut_in_docker.sh",
}


def _has_unmigrated_raw_check(text: str) -> bool:
    """純函式（供直接單元測試）：判斷一段 `.sh` 內文是否仍殘留未收斂的裸
    `command -v python`/`python3` 判斷。「已收斂」定義為同時含
    `windowsapps_guard.sh`（source）與 `is_real_python_candidate`（實際呼叫）；
    只有 source 行、沒有任何呼叫（如被局部退化改回裸判斷）不算已收斂
    （R43 三審 QA bug-injection 揪出，訂正二審初版「只要有 source 行就整檔
    豁免」的鑑別力缺口）。"""
    if "windowsapps_guard.sh" in text and "is_real_python_candidate" in text:
        return False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if _LOOSE_RAW_CHECK_RE.search(line):
            return True
    return False


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


_FROZEN_SDD_VERSION_RE = re.compile(r"^AISDLC_SDD/(AISDLC_SDD_v\d+\.\d+)/")


def _latest_sdd_version_name() -> str:
    """LATEST 版本名（sdd_version.py SSOT；解析失敗即 AssertionError）。比照
    test_windowsapps_guard_cross_consistency.py::_latest_sdd_root 同款手法：
    subprocess 呼叫 CLI（非 process 內 import），避免 sys.path 汙染。"""
    sdd_root = _REPO_ROOT / "AISDLC_SDD"
    resolver = sdd_root / "scripts" / "sdd_version.py"
    proc = subprocess.run(
        [sys.executable, str(resolver), "--sdd-root", str(sdd_root)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    name = proc.stdout.strip()
    if proc.returncode != 0 or not name:
        raise AssertionError(
            f"LATEST 解析失敗（sdd_version.py rc={proc.returncode}；stderr="
            f"{proc.stderr.strip()!r}）——掃描邊界不得靜默縮小"
        )
    return name


def _exclude_frozen_sdd_versions(paths: list[str], latest_name: str) -> list[str]:
    """排除 AISDLC_SDD 凍結版本（v0.01 ~ 除 LATEST 以外者）——凍結版依鐵律
    (CLAUDE.md「Copy-on-Evolve」慣例) 不應被新規則追殺歷史快照。R44 新增：
    `run_self_evolution.sh` 等模板檔案透過 Copy-on-Evolve 逐字複製進每個凍結
    版本，若不排除，新掃描會把 29 份歷史快照全部誤判為新缺口。"""
    kept = []
    for rel in paths:
        m = _FROZEN_SDD_VERSION_RE.match(rel)
        if m and m.group(1) != latest_name:
            continue
        kept.append(rel)
    return kept


def _has_ssot_guard(text: str) -> bool:
    """R44 抽出：與 `_has_unmigrated_raw_check` 開頭判斷同義，供
    `_has_zero_guard_python_call` 共用。"""
    return "windowsapps_guard.sh" in text and "is_real_python_candidate" in text


def _has_any_raw_availability_check(text: str) -> bool:
    """檔案是否**存在**（非「已收斂」）裸 `command -v python`/`python3` 判斷
    ——不管有沒有搭配 SSOT。逐行跳過註解，比對 `_LOOSE_RAW_CHECK_RE`。"""
    for line in text.splitlines():
        if line.strip().startswith("#"):
            continue
        if _LOOSE_RAW_CHECK_RE.search(line):
            return True
    return False


_BARE_PYTHON_WORD_RE = re.compile(r"\bpython3?\b")


def _invokes_python_bare(text: str) -> bool:
    """檔案是否有呼叫 python/python3 的痕跡（逐行掃描、跳過整行註解）。刻意
    採寬鬆的全字匹配（不要求特定呼叫語法）——R44 目標形狀本身就包含
    `copy_on_evolve.sh` 這種透過變數預設值間接呼叫（`_PY="${PYTHON:-python}"`）
    的寫法，比對呼叫語法反而會漏放此類間接呼叫。"""
    for line in text.splitlines():
        if line.strip().startswith("#"):
            continue
        if _BARE_PYTHON_WORD_RE.search(line):
            return True
    return False


def _has_zero_guard_python_call(text: str) -> bool:
    """R44 Architect 深度架構評估找到的系統性缺口：既有
    `_has_unmigrated_raw_check` 只認得『有做可用性判斷（command -v）但沒有
    SSOT guard』這一種繞過形狀（如殘留 `command -v python >/dev/null` 卻沒
    source guard 檔），完全抓不到『整支檔案從頭到尾根本沒有任何 python 可用性
    判斷、直接裸呼叫 python』這種更原始也更危險的形狀（如
    `run_self_evolution.sh` 只檢查 `command -v claude`、`copy_on_evolve.sh`
    完全不檢查就呼叫 `"${_PY}"`）——WindowsApps 空殼會被直接呼叫執行，連
    『找不到就報錯』這道最基本防線都沒有。

    判準：非 SSOT 已收斂（`_has_ssot_guard`）、且非既有『有裸判斷但無 SSOT』
    形狀（`_has_any_raw_availability_check`，那是 `_has_unmigrated_raw_check`
    既有測試涵蓋的範圍，不重複計）、且確實呼叫 python/python3
    （`_invokes_python_bare`）者，才視為本形狀的新缺口。"""
    if _has_ssot_guard(text):
        return False
    if _has_any_raw_availability_check(text):
        return False
    return _invokes_python_bare(text)


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


class TestHasUnmigratedRawCheck(unittest.TestCase):
    """R43 三審 QA bug-injection 揪出的鑑別力缺口回歸鎖：直接對 `_has_unmigrated_raw_check`
    純函式單元測試「已 migrate 但被局部退化」情境（source 行還在、呼叫被整段
    改回裸判斷），確認不再被誤判為已收斂。"""

    def test_fully_unmigrated_file_is_flagged(self) -> None:
        text = 'command -v python >/dev/null 2>&1 || echo missing\n'
        self.assertTrue(_has_unmigrated_raw_check(text))

    def test_properly_migrated_file_is_not_flagged(self) -> None:
        text = (
            '. "$root/tools/lib/windowsapps_guard.sh"\n'
            'if is_real_python_candidate python; then PY=python; fi\n'
        )
        self.assertFalse(_has_unmigrated_raw_check(text))

    def test_migrated_with_fallback_branch_is_not_flagged(self) -> None:
        """install_post_commit.sh 這類「guard 檔缺席時降級回退裸判斷」的合法設計
        不應被誤判為未收斂（fallback 分支本身就是刻意保留的裸 command -v）。"""
        text = (
            'GUARD_SRC="$MAIN_CHECKOUT_ROOT/tools/lib/windowsapps_guard.sh"\n'
            'if [ -f "$GUARD_SRC" ]; then\n'
            '  . "$GUARD_SRC"\n'
            '  is_real_python_candidate python && PY=python\n'
            'else\n'
            '  PY="$(command -v python || command -v python3 || true)"\n'
            'fi\n'
        )
        self.assertFalse(_has_unmigrated_raw_check(text))

    def test_sourced_but_never_called_is_flagged(self) -> None:
        """R43 三審 QA 揪出的真實鑑別力缺口：source 行還在，但呼叫端已被整段改回
        裸判斷（如遭局部退化/regression）——舊版「只要含 windowsapps_guard.sh 字串
        就整檔豁免」會誤放行，本測試鎖住訂正後的行為。"""
        text = (
            '. "$root/tools/lib/windowsapps_guard.sh"\n'
            'if command -v python >/dev/null 2>&1; then PY=python; fi\n'
        )
        self.assertTrue(_has_unmigrated_raw_check(text))

    def test_comment_only_mention_is_not_flagged(self) -> None:
        text = '# 比照 tools/integration_gate.sh 的 command -v python 判斷慣例\n'
        self.assertFalse(_has_unmigrated_raw_check(text))


class TestHasZeroGuardPythonCall(unittest.TestCase):
    """R44 Architect 深度架構評估新增的鑑別力回歸鎖：直接對
    `_has_zero_guard_python_call` 純函式單元測試各種情境，確認它只認『完全
    沒有任何可用性判斷卻直接呼叫 python』這一種形狀，不與既有
    `_has_unmigrated_raw_check` 涵蓋的『有裸判斷但無 SSOT』形狀重疊誤判。"""

    def test_fully_unguarded_bare_call_is_flagged(self) -> None:
        text = 'python -c "import json,sys;print(1)"\n'
        self.assertTrue(_has_zero_guard_python_call(text))

    def test_variable_default_indirection_is_flagged(self) -> None:
        """`copy_on_evolve.sh` 的真實形狀：透過 `${PYTHON:-python}` 預設值間接
        呼叫，全程沒有任何 command -v／SSOT 判斷。"""
        text = (
            '_PY="${PYTHON:-python}"\n'
            '"${_PY}" "$SCRIPT_DIR/foo.py" --write\n'
        )
        self.assertTrue(_has_zero_guard_python_call(text))

    def test_file_with_raw_check_but_no_ssot_is_not_flagged_by_this_helper(self) -> None:
        """有裸 `command -v python` 判斷（即使沒有 SSOT）屬於既有
        `_has_unmigrated_raw_check` 測試涵蓋的形狀，本 helper 不應重複計。"""
        text = 'command -v python >/dev/null 2>&1 || echo missing\n'
        self.assertFalse(_has_zero_guard_python_call(text))

    def test_ssot_guarded_file_is_not_flagged(self) -> None:
        text = (
            '. "$root/tools/lib/windowsapps_guard.sh"\n'
            'if is_real_python_candidate python; then PY=python; fi\n'
        )
        self.assertFalse(_has_zero_guard_python_call(text))

    def test_no_python_mention_at_all_is_not_flagged(self) -> None:
        self.assertFalse(_has_zero_guard_python_call('echo hello\ncommand -v git\n'))

    def test_comment_only_mention_is_not_flagged(self) -> None:
        text = '# 見 tools/dev_start.py，此處無需直接呼叫 python\n'
        self.assertFalse(_has_zero_guard_python_call(text))


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
        也不在 `_EXEMPT_SH_FILES`（明確記載豁免理由）者視為未收斂新缺口。

        R43 三審 QA 用 bug-injection 揪出的鑑別力缺口（訂正二審初版）：原本只要
        檔案內文字含有 `"windowsapps_guard.sh"` 字串（即有 source 這一行）就整檔
        跳過，不管該檔是否仍殘留裸判斷——「已 migrate 但被局部退化」（source 行
        還在、但呼叫端改回裸判斷）的情境會被誤放行。改為要求同時含
        `is_real_python_candidate`（實際呼叫共用函式）才視為已收斂，只 source
        不呼叫（或呼叫被整段刪掉、只留 source 行）不再豁免。"""
        known_relpaths = {str(f.relative_to(_REPO_ROOT)).replace("\\", "/") for f in _CALLER_FILES}
        unmigrated: list[str] = []
        for rel in _tracked_sh_files():
            if rel in known_relpaths or rel in _EXEMPT_SH_FILES:
                continue
            path = _REPO_ROOT / rel
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if _has_unmigrated_raw_check(text):
                unmigrated.append(rel)
        self.assertEqual(
            unmigrated, [],
            f"發現未收斂的裸 python 可用性判斷（未 source windowsapps_guard.sh 且未登記"
            f"豁免）：{unmigrated}——請改用 is_real_python_candidate 或於 "
            f"_EXEMPT_SH_FILES 附理由登記豁免",
        )

    def test_repo_wide_scan_finds_no_zero_guard_python_calls(self) -> None:
        """R44 Architect 深度架構評估找到的系統性缺口：上一測試
        （`test_repo_wide_scan_finds_no_unmigrated_sh_scripts`）與 .ps1 側對應
        測試都只認得『有做可用性判斷（command -v / Get-Command）但沒有
        dot-source SSOT guard』這一種繞過形狀，完全抓不到『整支檔案從頭到尾
        根本沒有任何 python 可用性判斷、直接裸呼叫 python』這種更原始也更
        危險的形狀。本測試 repo-wide 掃描全部 git-tracked `*.sh`（排除
        AISDLC_SDD 凍結版本目錄 AISDLC_SDD_v0.01~v0.29，只掃 LATEST 演化版與
        其餘 monorepo 檔案——凍結版依 Copy-on-Evolve 鐵律不回改），找出符合
        此形狀的檔案。

        已知真實命中（本輪稍後步驟修復，本測試只建立/驗證掃描鎖本身）：
        `AISDLC_SDD/AISDLC_SDD_v0.30/tools/arch_fitness/run_self_evolution.sh`
        （只檢查 `command -v claude`，從未檢查 python 本身）與
        `AISDLC_SDD/scripts/copy_on_evolve.sh`（透過 `${PYTHON:-python}` 預設值
        間接呼叫，全程零檢查）。
        """
        latest_name = _latest_sdd_version_name()
        known_relpaths = {str(f.relative_to(_REPO_ROOT)).replace("\\", "/") for f in _CALLER_FILES}
        scoped = _exclude_frozen_sdd_versions(_tracked_sh_files(), latest_name)

        unmigrated: list[str] = []
        for rel in scoped:
            if rel in known_relpaths or rel in _EXEMPT_SH_FILES:
                continue
            path = _REPO_ROOT / rel
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if _has_zero_guard_python_call(text):
                unmigrated.append(rel)

        self.assertEqual(
            unmigrated, [],
            f"發現完全沒有任何 python 可用性判斷（既無 SSOT guard 也無裸 "
            f"command -v 判斷）卻直接呼叫 python/python3 的檔案：{unmigrated}"
            f"——請改用 is_real_python_candidate（source tools/lib/"
            f"windowsapps_guard.sh），或於 _EXEMPT_SH_FILES 附理由登記豁免",
        )


if __name__ == "__main__":
    unittest.main()
