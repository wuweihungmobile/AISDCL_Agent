r"""install_post_commit.ps1 的 WindowsApps 空殼 python.exe 排除 guard 回歸鎖
（R38 Mac/Windows 相容性審查系列，DEF-101-273/279/300/303 同類缺陷第 4~5 個
獨立位置）。

WHY（測意圖非僅行為，Rule 9）：
全新 Windows 11 機器未裝真 Python 時，`Get-Command python` 仍會命中 WindowsApps
底下系統自動註冊的空殼 `python.exe`（Store App Execution Alias）——`Get-Command`
找得到、但實際執行只會跳出 Microsoft Store 安裝提示，不是可判讀例外。修復前
`install_post_commit.ps1` 的前置檢查只判斷「找不找得到 python」（`-not
(Get-Command python ...)`），命中空殼會誤判為「有 python」，讓後續 `& python ...`
靜默失敗或掛起，而非本檔自己設計的乾淨 `Write-Error` + `exit 1`。

R38 早期修復曾以「本框架有 `releases/` 獨立打包發布機制，硬相依 monorepo 根
路徑的共用檔會找不到檔案」為由，獨立內嵌一份判斷邏輯（不 dot-source 根層
`tools/lib/WindowsAppsGuard.ps1`）。同輪 Architect 一審 REJECT 並查證推翻：
實際 `releases/` 打包產物內根本沒有 `tools/install_hooks/` 目錄，本檔從未被
獨立打包過；且本檔本就用 `$MainCheckoutRoot` 組出 `$HookSrcDrift`/
`$HookSrcClosure` 等強相依 monorepo 根路徑的路徑，早已 100% 綁死在「必須跑在
monorepo checkout 裡」的前提上。故改為 dot-source 共用函式
`Test-IsRealPython`（`tools/lib/WindowsAppsGuard.ps1`），消滅第 4~5 個獨立
副本。本檔驗證的是**本檔呼叫共用函式後的整體腳本行為**，不重複驗證共用函式
本身的判斷邏輯（該函式已有
`tools/tests/test_windowsapps_guard_cross_consistency.py` 自己的回歸鎖）。

兩層測試手法：
1. **可攜式（任何平台皆具鑑別力）**：用 shadow `Get-Command` 函式技巧
   （比照根層 `tools/tests/test_windowsapps_guard_cross_consistency.py` 既有
   先例）——在呼叫 `install_post_commit.ps1` 之前，於同一 pwsh 呼叫端 session
   定義一個同名 `Get-Command` 函式（PowerShell 函式解析優先於原生 cmdlet），
   讓腳本內部呼叫到的 `Get-Command python` 回傳指定的假 `.Source`。這不受
   各平台 `Get-Command` 對裸名候選的路徑解析語意差異影響（真實 Windows 用
   反斜線路徑，macOS/Linux 上找到的可執行檔路徑用斜線），故在本機 macOS pwsh
   上就能直接對 bug-injection（退回舊版 `-not (Get-Command python ...)` 裸判斷）
   具鑑別力：退回舊版時，shadow 回傳的假物件仍為 truthy，舊邏輯的 guard 會
   放行，腳本會繼續執行到 `& python ...`（此時呼叫的是真實 PATH 解析出的
   系統 python，可能實際执行成功），導致本測試斷言的「找不到」訊息與非零
   exit code 不會出現，測試轉紅——證明測試對修復意圖有真實鑑別力。
2. **Windows 專屬端到端（依賴 PATHEXT 解析語意，僅 skip 於真 Windows 平台）**：
   比照既有 `tools/tests/test_bootstrap_ps1.py` 手法，用假 `.exe`/`.cmd` 檔案
   佈署於 PATH 上，驗證 Windows PATHEXT 語意下 `Get-Command python` 命中
   WindowsApps 路徑下的 `python.exe` 空殼時腳本正確排除；空殼與真直譯器
   （`.cmd` 假腳本，執行時印出可斷言的標記字串）同時在 PATH 時，正確選中
   真直譯器而非空殼。

執行：cd AISDLC_SDD && python -m pytest scripts/tests/test_install_post_commit_windowsapps_guard.py -v
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# 本檔 → scripts/tests → scripts → AISDLC_SDD（REPO_ROOT）
REPO_ROOT = Path(__file__).resolve().parents[2]
# AISDLC_SDD 的父目錄 = monorepo 根（R38 改 dot-source 後，安裝器需要
# monorepo 根層 tools/lib/WindowsAppsGuard.ps1 存在，假 monorepo 需一併備妥）。
MONOREPO_ROOT = REPO_ROOT.parent


def _pwsh_exe() -> str | None:
    return shutil.which("pwsh") or shutil.which("powershell")


_PWSH = _pwsh_exe()

pytestmark = pytest.mark.skipif(_PWSH is None, reason="需要 powershell/pwsh")


def _latest_installer() -> Path:
    """解析 LATEST（`scripts/sdd_version.py` SSOT）取得目前生效的 .ps1 安裝器路徑。"""
    proc = subprocess.run(
        ["python3", str(REPO_ROOT / "scripts" / "sdd_version.py")],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
    )
    assert proc.returncode == 0 and proc.stdout.strip(), (
        f"LATEST 解析失敗：rc={proc.returncode} stderr={proc.stderr!r}"
    )
    return (
        REPO_ROOT / proc.stdout.strip() / "tools" / "install_hooks"
        / "install_post_commit.ps1"
    )


def _make_fake_monorepo(base: Path) -> Path:
    """建立最小化假 monorepo：`AISDLC_SDD/scripts/sdd_version.py`（真 resolver，
    需隨 tracked 檔存在）＋一份 dummy 版本目錄的 hook 來源檔＋根層
    `tools/lib/WindowsAppsGuard.ps1`（R38 改 dot-source 共用函式後，安裝器
    前置檢查會要求此檔存在，缺席即 Write-Error + exit 1），並 commit 使其
    tracked（`sdd_version.py` 的 LATEST 解析要求 git tracked）。安裝器只在
    存在性檢查與 LATEST 解析階段依賴這些檔案，不觸發真實 commit hook 執行。
    """
    repo = base / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-q", str(repo)], check=True, capture_output=True, timeout=30
    )
    scripts_dir = repo / "AISDLC_SDD" / "scripts"
    scripts_dir.mkdir(parents=True)
    shutil.copy2(
        REPO_ROOT / "scripts" / "sdd_version.py", scripts_dir / "sdd_version.py"
    )
    guard_dir = repo / "tools" / "lib"
    guard_dir.mkdir(parents=True)
    shutil.copy2(
        MONOREPO_ROOT / "tools" / "lib" / "WindowsAppsGuard.ps1",
        guard_dir / "WindowsAppsGuard.ps1",
    )
    hooks_dir = repo / "AISDLC_SDD" / "AISDLC_SDD_v0.01" / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True)
    for stub in ("post_commit_drift.py", "closure_evidence_verify.py"):
        (hooks_dir / stub).write_text("# stub\n", encoding="utf-8")
    git_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    }
    subprocess.run(
        ["git", "-C", str(repo), "add", "-A"],
        check=True, capture_output=True, timeout=30,
    )
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", "init"],
        check=True, capture_output=True, timeout=30, env=git_env,
    )
    return repo


def _run_with_shadowed_python(
    installer: Path, cwd: Path, source: str | None
) -> subprocess.CompletedProcess:
    """在 shadow `Get-Command` 函式生效下執行 `installer`。

    `source=None` 模擬「完全找不到 python」；否則模擬「找到 python，`.Source`
    為指定字串」。非 'python' 候選名稱一律轉呼真正的原生 `Get-Command`（本檔
    未用到，但保留對稱性避免意外攔截其他候選）。
    """
    if source is None:
        get_command_body = "return $null"
    else:
        escaped = source.replace('"', '`"')
        get_command_body = f'return [PSCustomObject]@{{ Source = "{escaped}" }}'
    script = (
        "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;\n"
        "function Get-Command {\n"
        "  param(\n"
        "    [Parameter(Position=0)][string]$Name,\n"
        "    [Parameter(ValueFromRemainingArguments=$true)] $Rest\n"
        "  )\n"
        "  if ($Name -ne 'python') {\n"
        "    return Microsoft.PowerShell.Core\\Get-Command -Name $Name "
        "-ErrorAction SilentlyContinue\n"
        "  }\n"
        f"  {get_command_body}\n"
        "}\n"
        f'& "{installer}"\n'
    )
    return subprocess.run(
        [_PWSH, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        cwd=str(cwd),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=60,
    )


# ---------------------------------------------------------------------------
# ① 可攜式：shadow Get-Command 直接驗證本檔獨立實作的判斷邏輯
# ---------------------------------------------------------------------------
def test_windowsapps_stub_python_is_rejected_with_clean_error(tmp_path) -> None:
    """`Get-Command python` 命中位於 WindowsApps 路徑下的候選時，必須視同
    「找不到 python」，回報乾淨的 `Write-Error` 並 `exit 1`，不得讓後續
    `& python ...` 真的被觸發。

    Bug-injection 鑑別力：若退回舊版 `-not (Get-Command python ...)` 裸判斷，
    shadow 回傳的假物件仍為 truthy，guard 會放行，腳本會繼續執行到
    `& python ...` 並實際呼叫本機真實 PATH 上的 python（測試環境需要真 python
    才能執行 `ci-gate.sh` 等既有工具，通常存在），導致 exit code 為 0 且輸出
    不含「找不到」——本測試斷言即會轉紅。
    """
    installer = _latest_installer()
    assert installer.is_file(), f"安裝器缺席：{installer}"
    repo = _make_fake_monorepo(tmp_path)

    proc = _run_with_shadowed_python(
        installer, repo,
        source=r"C:\Users\me\AppData\Local\Microsoft\WindowsApps\python.exe",  # platform-ok: 純字面值餵給 PowerShell 腳本文字，非 Python Path join
    )
    output = proc.stdout + proc.stderr
    assert proc.returncode != 0, (
        f"WindowsApps 空殼應被排除、腳本應以非零 exit 結束：\n{output}"
    )
    assert "找不到" in output, f"應回報「找不到 python」乾淨錯誤，實際輸出：\n{output}"


def test_windowsapps_segment_match_is_case_insensitive(tmp_path) -> None:
    """`-like` 預設不分大小寫；即使路徑中 WindowsApps 區段大小寫不同（如系統
    本地化或大小寫不敏感檔案系統回傳的不同大小寫），仍須被排除。防未來有人
    改成 `-clike`（大小寫敏感版本）而悄悄弱化 guard。
    """
    installer = _latest_installer()
    repo = _make_fake_monorepo(tmp_path)

    proc = _run_with_shadowed_python(
        installer, repo,
        source=r"C:\Users\me\AppData\Local\Microsoft\windowsapps\python.exe",  # platform-ok: 純字面值餵給 PowerShell 腳本文字，非 Python Path join
    )
    output = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"大小寫不同的 WindowsApps 區段仍應被排除：\n{output}"
    assert "找不到" in output, output


def test_missing_python_still_reports_clean_error(tmp_path) -> None:
    """既有行為不可回歸：完全找不到 python（`Get-Command` 回傳 `$null`）時，
    仍必須乾淨回報「找不到」並 `exit 1`，不得因新增的 `.Source` 存取而對
    `$null` 拋例外。
    """
    installer = _latest_installer()
    repo = _make_fake_monorepo(tmp_path)

    proc = _run_with_shadowed_python(installer, repo, source=None)
    output = proc.stdout + proc.stderr
    assert proc.returncode != 0, output
    assert "找不到" in output, output


def test_real_python_outside_windowsapps_is_accepted_and_hook_installs(tmp_path) -> None:
    """真實（非 WindowsApps）python 不應被誤排除——guard 修復後腳本仍應放行
    正常情境並完成安裝（hook 寫入 `.git/hooks/post-commit`），證明修復是
    「排除空殼」而非「連真 python 一併擋下」的過度收斂。

    shadow 只攔截 `Get-Command python` 的**存在性判斷**那一行；之後腳本真正
    執行 `& python ...` 時呼叫的是本機 PATH 上實際的 python 直譯器（測試環境
    需要真 python 才能跑 `ci-gate.sh` 等既有工具，通常存在），故此測試同時
    驗證了 guard 放行後全流程仍可正常完成。
    """
    installer = _latest_installer()
    repo = _make_fake_monorepo(tmp_path)

    proc = _run_with_shadowed_python(
        installer, repo, source=r"C:\Python311\python.exe",  # platform-ok: 純字面值餵給 PowerShell 腳本文字，非 Python Path join
    )
    output = proc.stdout + proc.stderr
    assert proc.returncode == 0, f"真實 python 不應被 guard 誤擋：\n{output}"
    hook = repo / ".git" / "hooks" / "post-commit"
    assert hook.is_file(), f"guard 放行後應完成安裝、hook 未寫入：\n{output}"


# ---------------------------------------------------------------------------
# ② Windows 專屬端到端：依賴 PATHEXT 解析語意，僅在真 Windows 平台具鑑別力
# ---------------------------------------------------------------------------
def _windows_pwsh_available() -> bool:
    """僅供依賴 Windows PATHEXT／`.cmd`／`.exe` 解析語意的測試使用——這類測試
    用假直譯器讓 `Get-Command python`／`& python` 命中它，但這類檔案需要
    Windows 的 PATHEXT／App Execution Alias 語意解讀，在裝有 pwsh 的
    macOS/Linux 開發機上會失去鑑別力（`Get-Command python` 不會透過 PATHEXT
    把裸名解析到 `python.exe`），故額外檢查平台本身（比照
    `tools/tests/test_bootstrap_ps1.py` 既有先例）。
    """
    return sys.platform.startswith("win") and _PWSH is not None


def _git_dir() -> str | None:
    """git.exe 所在目錄——`install_post_commit.ps1` 第一步就呼叫
    `git rev-parse --git-common-dir`，若 `_run_with_path` 建構的 PATH 完全
    排除 git，腳本會在尚未執行到 WindowsApps guard 邏輯前就先因「'git' 詞彙
    無法辨識」中止，導致測試斷言的 guard 行為（「找不到」/ 標記字串）根本沒
    機會出現（R42 修正：測試 fixture 缺陷，非 install_post_commit.ps1 本身
    的 bug）。"""
    git_path = shutil.which("git")
    if not git_path:
        return None
    return str(Path(git_path).resolve().parent)


def _run_with_path(installer: Path, cwd: Path, path_dirs: list[Path]) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    all_dirs = [str(p) for p in path_dirs]
    git_dir = _git_dir()
    if git_dir:
        all_dirs.append(git_dir)
    env["PATH"] = os.pathsep.join(all_dirs)
    cmd = (
        "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
        f"& '{installer}'"
    )
    return subprocess.run(
        [_PWSH, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
        cwd=str(cwd),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=30, env=env,
    )


_WINDOWS_PATHEXT_SKIP = pytest.mark.skipif(
    not _windows_pwsh_available(),
    reason=(
        "[WINDOWS-NATIVE-ONLY] 此測試依賴 Windows PATHEXT／App Execution Alias 解析語意，僅能在真 "
        "Windows 平台上跑（見 _windows_pwsh_available 說明；R44 DEF-101-348 標籤，"
        "比照 tools/tests/ 既有用法，供未來彙整可見度）"
    ),
)


@_WINDOWS_PATHEXT_SKIP
def test_windowsapps_only_python_stub_is_skipped_and_reports_not_found_real_pathext(
    tmp_path,
) -> None:
    installer = _latest_installer()
    repo = _make_fake_monorepo(tmp_path)
    stub_dir = tmp_path / "WindowsApps"
    stub_dir.mkdir()
    (stub_dir / "python.exe").write_bytes(b"")
    proc = _run_with_path(installer, repo, [stub_dir])
    output = proc.stdout + proc.stderr
    assert proc.returncode != 0, output
    assert "找不到" in output, output


@_WINDOWS_PATHEXT_SKIP
def test_windowsapps_stub_present_first_is_rejected_not_silently_bypassed_real_pathext(
    tmp_path,
) -> None:
    """R42 四方複審修正（前身
    `test_real_python_outside_windowsapps_is_used_even_when_windowsapps_stub_present_first_real_pathext`
    的期待本身是錯的）：

    `install_post_commit.ps1` 只有 **單一** `python` 候選名稱（第 61 行
    `Test-IsRealPython -CandidateName 'python'`，沒有 `python3`／`py` 等第二
    候選可退而求其次——與根層 `tools/dev_start.ps1` 同構）。共用函式
    `Test-IsRealPython`（`tools/lib/WindowsAppsGuard.ps1`）目前實作是
    `Get-Command $CandidateName`（單一結果，依 PATH 目錄順序取第一個），
    呼叫端拿到 `$true`/`$false` 後一律用**候選名稱字面值** `'python'` 去實際
    呼叫。PATH 上「WindowsApps 空殼排前面、真直譯器排後面」時，`Get-Command
    python` 與後續 `& python` 兩者都會解析到 PATH 最前面的 WindowsApps 空殼
    ——guard 正確判斷第一候選是空殼並回傳 `$false`，腳本回報「找不到」並停
    下，這是正確且更安全的行為（見根層
    `tools/tests/test_windowsapps_guard_cross_consistency.py` 同款修正的完整
    推導與本機實測證據，該處的分析對本檔同樣成立）。前身測試期待「跳過空殼
    採用後面真直譯器」在目前架構下不可能發生、也不應該發生：若要讓 guard
    真的跳過空殼，`Test-IsRealPython` 必須改回傳完整路徑且三個呼叫端都要
    改用該路徑呼叫，屬於超出本輪比例原則的高風險大改動。
    """
    installer = _latest_installer()
    repo = _make_fake_monorepo(tmp_path)
    stub_dir = tmp_path / "WindowsApps"
    stub_dir.mkdir()
    (stub_dir / "python.exe").write_bytes(b"")
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    fake = real_dir / "python.cmd"
    fake.write_text(
        "@echo off\r\necho FAKE_PYTHON_INVOKED\r\nexit /b 42\r\n",
        encoding="ascii",
    )
    proc = _run_with_path(installer, repo, [stub_dir, real_dir])
    output = proc.stdout + proc.stderr
    assert "FAKE_PYTHON_INVOKED" not in output, output
    assert proc.returncode != 0, output
    assert "找不到" in output, output
