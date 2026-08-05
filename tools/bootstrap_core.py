#!/usr/bin/env python3
"""bootstrap_core.py — monorepo 一鍵開發環境整備單一核心（macOS / Linux / Windows 共用）。

第 16 輪架構最佳化 Architect 建議 B：原 tools/bootstrap.{sh,ps1} 為雙原生實作
（bash / PowerShell 各長一份幾乎對稱的業務邏輯），本檔將全部語意收斂為單一
Python 核心，兩支同名 .sh / .ps1 降為「確認直譯器 → 轉呼叫本檔 → 傳遞 exit
code」的薄殼——模式對齊本 repo 已驗證過的 AutoClaude/tools/local_ci_gate.py
（R12 收斂案）。

與 local_ci_gate 的關鍵差異：local_ci_gate 假設 .venv 已啟用（PATH 上已有
`python`），本檔則反過來——**在 .venv 尚未存在時**就要負責找一個堪用的基底
直譯器來建立它，因此「挑直譯器」的判斷邏輯（含 Windows CI 特化順序）本身
即是本檔要收斂的業務邏輯之一，不能像 local_ci_gate 一樣交給薄殼簡化掉。

做什麼（與收斂前 .sh/.ps1 完全對等）：
  1. 若 .venv 已存在 → 直接沿用（形狀不符本平台則 fail-fast）
  2. 否則挑一個 >= 3.11 的直譯器（讀 .python-version 為目標版，偵測到 uv
     則跳過此步，改用 `uv venv --python`）並建立 .venv
  3. 安裝 AutoClaude（editable, [dev,notifications,lint]）+ AISDLC_SDD CI 依賴
  4. 印出啟用指引與 git-hooks 安裝選項（不自動改 core.hooksPath）

輸出文字為 CI（macos-compat-ci.yml / windows-compat-ci.yml）機械比對的凍結
介面之一（例如「偵測到既有 .venv → 沿用」子字串），改動前務必確認未破壞
既有 workflow 斷言。
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path, PureWindowsPath

REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = REPO_ROOT / ".venv"

# platform_utils 位於 tools/lib/ 子目錄（非本檔同層），需顯式插入 sys.path 才能
# import——手法對齊本輪其他核心檔案既有慣例（R17 DEF-101-231 觀察點 1+2：收斂
# is_windows/os_label/venv_python_path 平台判斷邏輯的第二次重複）。
sys.path.insert(0, str(REPO_ROOT / "tools" / "lib"))
import platform_utils  # noqa: E402

IS_WINDOWS = platform_utils.is_windows()

_VERSION_CHECK_CODE = "import sys; sys.exit(0 if sys.version_info[:2] >= (3,11) else 1)"
_VERSION_PRINT_CODE = "import sys; print('%d.%d' % sys.version_info[:2])"


def _out(msg: str = "") -> None:
    print(msg)


def _err(msg: str = "") -> None:
    # posix：對齊收斂前 .sh 的 `>&2`（真正寫入 stderr）。
    # windows：對齊收斂前 .ps1 的 Write-Host（走 Information stream，非 stderr）。
    if IS_WINDOWS:
        print(msg)
    else:
        print(msg, file=sys.stderr)


def read_py_target(root: Path) -> str:
    """讀 .python-version 首行，截為 major.minor（缺檔/空白回退 3.11）。"""
    raw = ""
    try:
        with (root / ".python-version").open("r", encoding="utf-8", errors="replace") as fh:
            raw = fh.readline().strip()
    except OSError:
        raw = ""
    if not raw:
        raw = "3.11"
    parts = raw.split(".")
    return ".".join(parts[:2]) if len(parts) > 2 else raw


def _probe_ok(argv_prefix: list[str]) -> bool:
    try:
        proc = subprocess.run(
            [*argv_prefix, "-c", _VERSION_CHECK_CODE],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except OSError:
        return False
    return proc.returncode == 0


def _probe_version_mm(argv_prefix: list[str]) -> str:
    try:
        proc = subprocess.run(
            [*argv_prefix, "-c", _VERSION_PRINT_CODE],
            capture_output=True, encoding="utf-8", errors="replace",
        )
    except OSError:
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _probe_version_display(exe: str) -> str:
    """對齊 .sh 的 `"$BASE_PY" --version 2>&1`（顯示用；windows 側不需要）。"""
    try:
        proc = subprocess.run(
            [exe, "--version"], capture_output=True, encoding="utf-8", errors="replace",
        )
    except OSError:
        return ""
    return (proc.stdout + proc.stderr).strip()


def _is_windows_apps_stub(resolved_path: str) -> bool:
    """WHY: WindowsApps 底下的 python.exe/python3.exe 常是系統自動註冊的 App
    Execution Alias 空殼——`shutil.which()` 找得到、但實際執行只會跳出
    Microsoft Store 安裝提示，不會執行任何 Python 碼。`tools/bootstrap.ps1`
    （DEF-101-273/279）已對 `python`/`python3` 裸名候選加了同款靜態路徑排除
    guard（`_probe_ok()` 用執行結果判斷在此情境不可靠，正是 `.ps1` 改用靜態
    路徑比對而非執行探測的原因）；本函式對稱補齊 Python 核心 `pick_python()`
    （R31 Scan-B 掃描實證：兩邊此前不對稱，只有 `.ps1` 有 guard）。
    """
    return any(part.lower() == "windowsapps" for part in PureWindowsPath(resolved_path).parts)


def pick_python(py_target: str) -> str | None:
    """挑一個 >= 3.11 的直譯器；回傳可直接 .split() 餵給 subprocess 的字串。"""
    if IS_WINDOWS:
        is_ci = os.environ.get("GITHUB_ACTIONS") == "true" or os.environ.get("CI") == "true"
        candidates = (
            ["python", "python3", f"py -{py_target}", "py -3.12", "py -3.11"]
            if is_ci
            else [f"py -{py_target}", "py -3.12", "py -3.11", "python", "python3"]
        )
    else:
        candidates = [f"python{py_target}", "python3.12", "python3.11", "python3", "python"]

    for candidate in candidates:
        parts = candidate.split()
        resolved = shutil.which(parts[0])
        if resolved is None:
            continue
        # `py` launcher 候選（含空格，parts[0] == "py"）不需要此 guard——它本身
        # 就是官方解析真直譯器的入口，不會是 WindowsApps 空殼（同 bootstrap.ps1
        # 註解）；只有裸名 "python"/"python3" 候選會命中空殼別名。
        if IS_WINDOWS and parts[0] in ("python", "python3") and _is_windows_apps_stub(resolved):
            continue
        if _probe_ok(parts):
            return candidate
    return None


def _venv_python_usable(venv_dir: Path) -> bool:
    vpy = platform_utils.venv_python_path(venv_dir, is_windows=IS_WINDOWS)
    if IS_WINDOWS:
        return vpy.is_file()
    return vpy.is_file() and os.access(vpy, os.X_OK)


def _run_stream(cmd: list[str]) -> int:
    try:
        return subprocess.run(cmd).returncode
    except OSError as exc:
        _err(f"❌ 執行失敗：{' '.join(cmd)}（{exc}）")
        return 1


def _run_quiet_stdout(cmd: list[str]) -> int:
    try:
        return subprocess.run(cmd, stdout=subprocess.DEVNULL).returncode
    except OSError as exc:
        _err(f"❌ 執行失敗：{' '.join(cmd)}（{exc}）")
        return 1


def _reused_venv_error() -> None:
    _err("")
    if IS_WINDOWS:
        _err("❌ 既有 .venv 缺 Scripts\\python.exe（多半是 macOS/Linux 上建立的 .venv）"
             "— 本平台無法沿用。")
        _err("   請刪除後重建：Remove-Item -Recurse -Force .venv；再跑 "
             "powershell -ExecutionPolicy Bypass -File tools/bootstrap.ps1")
    else:
        _err("❌ 既有 .venv 缺 bin/python（多半是 Windows 上建立的 .venv）— 本平台無法沿用。")
        _err("   請刪除後重建：rm -rf .venv && bash tools/bootstrap.sh")


def _reused_venv_ok_message() -> None:
    if IS_WINDOWS:
        _out("偵測到既有 .venv → 沿用（如需重建請先 Remove-Item -Recurse -Force .venv）")
    else:
        _out("偵測到既有 .venv → 沿用（如需重建請先 rm -rf .venv）")


def _no_interpreter_error(py_target: str) -> None:
    _err("")
    _err(f"❌ 找不到 Python >= {py_target}。")
    if IS_WINDOWS:
        _err("   Windows 安裝建議：winget install Python.Python.3.11（或用 pyenv-win）")
        _err("   或安裝 uv：winget install astral-sh.uv")
    else:
        _err("   macOS 安裝建議：brew install python@3.11")
        _err("   或安裝 uv（自動管理版本）：curl -LsSf https://astral.sh/uv/install.sh | sh")


def _venv_shape_mismatch_error(used_interp_label: str) -> None:
    _err("")
    if IS_WINDOWS:
        _err(f"❌ .venv 建立指令回報成功（rc=0）但 Scripts\\python.exe 不存在"
             f"（直譯器：{used_interp_label}）。")
        _err("   請刪除後重試：Remove-Item -Recurse -Force .venv；再跑 "
             "powershell -ExecutionPolicy Bypass -File tools/bootstrap.ps1")
    else:
        _err("❌ .venv 建立指令回報成功（rc=0）但 bin/python 不存在"
             f"（直譯器：{used_interp_label}）。")
        _err("   請刪除後重試：rm -rf .venv && bash tools/bootstrap.sh")


def ensure_venv(py_target: str, use_uv: bool) -> int:
    """確保 .venv 存在且形狀符合本平台；回傳 0 成功、非 0 為失敗（呼叫端應直接 return）。"""
    if VENV_DIR.exists():
        if not _venv_python_usable(VENV_DIR):
            _reused_venv_error()
            return 1
        _reused_venv_ok_message()
        return 0

    base_py: str | None = None
    if not use_uv:
        base_py = pick_python(py_target)
        if base_py is None:
            _no_interpreter_error(py_target)
            return 1
        if IS_WINDOWS:
            _out(f"使用直譯器：{base_py}")
        else:
            _out(f"使用直譯器：{base_py}（{_probe_version_display(base_py)}）")
        actual_mm = _probe_version_mm(base_py.split())
        if actual_mm and actual_mm != py_target:
            if IS_WINDOWS:
                _out(f"⚠️ 選定直譯器為 {actual_mm}，與 .python-version 目標 {py_target} "
                     "不一致（仍 >= 3.11 可用）")
            else:
                _out(f"⚠️  選定直譯器為 {actual_mm}，與 .python-version 目標 {py_target} "
                     "不一致（>=3.11 仍可用，僅提醒）")

    _out("建立虛擬環境：.venv")
    if use_uv:
        used_interp_label = f"uv --python {py_target}"
        rc = _run_stream(["uv", "venv", "--python", py_target, str(VENV_DIR)])
    else:
        used_interp_label = base_py or ""
        rc = _run_stream([*used_interp_label.split(), "-m", "venv", str(VENV_DIR)])

    if rc != 0:
        _err(f"❌ 建立 .venv 失敗（rc={rc}）")
        return rc

    if not _venv_python_usable(VENV_DIR):
        _venv_shape_mismatch_error(used_interp_label)
        return 1
    return 0


def pip_install(use_uv: bool, venv_py: Path, args: list[str]) -> int:
    if use_uv:
        return _run_stream(["uv", "pip", "install", "--python", str(venv_py), *args])
    return _run_stream([str(venv_py), "-m", "pip", "install", *args])


def install_dependencies(use_uv: bool, venv_py: Path) -> int:
    _out("")
    _out("----- 安裝依賴 -----")
    if not use_uv:
        rc = _run_quiet_stdout([str(venv_py), "-m", "pip", "install", "--upgrade", "pip"])
        if rc != 0:
            _err(f"❌ pip 升級失敗（rc={rc}）")
            return rc

    # 🔴 R76：extras 刻意**不含** `hotkey`（＝ESC+F12 的 `keyboard` 後端）。理由不是遺漏：
    # `keyboard` 的 metadata 逐字 `Requires-Dist: pyobjc ; sys_platform == "darwin"`，加進來
    # 等於讓每一個 mac 的 bootstrap 都拖進整個 pyobjc 傘包；而它在非 root 的 mac 上
    # （`_darwinkeyboard.listen()` 首行 `os.geteuid() != 0`）根本不會生效 ⇒ 付了安裝面拿不到
    # 功能。代價已誠實記在 ONBOARDING.md 雷區表與 docs/AISDLC_Agent_UserGuide.md §4.2：
    # 出廠環境按 ESC+F12 無反應（程式面優雅降級只印 warning），要用請 `.[hotkey]` 顯式裝。
    _out("[1/2] AutoClaude（editable, [dev,notifications,lint]）")
    autoclaude_target = f"{REPO_ROOT / 'AutoClaude'}{os.sep}.[dev,notifications,lint]"
    rc = pip_install(use_uv, venv_py, ["-e", autoclaude_target])
    if rc != 0:
        # WHY 單引號包住 target（DEF-101-508）：這行是安裝失敗當下印給使用者複製貼上的唯一
        # 修復指引。macOS 預設 shell 是 zsh 且 nomatch 預設開啟，`…/.[dev,notifications,lint]`
        # 會被當成 glob；無匹配檔名時 zsh 在呼叫 pip 之前就中止整條命令列（no matches found），
        # 使用者等於拿到一個與套件無關的第二個錯誤。單引號在 bash/zsh/PowerShell 皆為引號字元。
        _err(f"❌ 依賴安裝失敗（rc={rc}）：pip install -e '{autoclaude_target}'")
        return rc

    sdd_req = REPO_ROOT / "AISDLC_SDD" / "AISDLC_SDD_v0.01" / "requirements-ci.txt"
    if sdd_req.is_file():
        _out("[2/2] AISDLC_SDD CI 依賴（requirements-ci.txt）")
        rc = pip_install(use_uv, venv_py, ["-r", str(sdd_req)])
        if rc != 0:
            # 同 DEF-101-508：印給使用者複製貼上的插值路徑一律加單引號。此處雖無 extras
            # 方括號，但 repo 被 checkout 到含空白或 glob 元字元的路徑（macOS 家目錄如
            # `/Users/John Doe/`）時，裸路徑同樣會讓這行指令貼上去就壞。
            _err(f"❌ 依賴安裝失敗（rc={rc}）：pip install -r '{sdd_req}'")
            return rc
    else:
        _out(f"[2/2] 略過：找不到 {sdd_req}")
    return 0


def print_completion_guide() -> None:
    """印出啟用指引。

    🔴 Windows 分支的閘門入口必須是 `.ps1`，不可寫成 `bash scripts/ci-gate.sh`：
    Windows 上 `bash` 由 `PATH` 解析到 `C:\\WINDOWS\\system32\\bash.exe`（WSL 佔位
    或真 WSL），落進的是一個沒有本 repo Windows venv／依賴的 Linux 環境；且反斜線
    路徑會被吃掉。本檔是新機器 bootstrap 後使用者唯一會照著敲的那幾行，教錯等於
    每台新 Windows 機器第一次跑閘門就撞牆——與 `DEF-101-778`（治理文件自己教壞掉的
    載具）同一個病，只是站點不同。
    `AISDLC_SDD/scripts/ci-gate.ps1` 已內建 `tools/lib/Find-GitBash.ps1`（SSOT，含
    system32/WSL 逐段排除）→ 偵測到 Git Bash 即薄委派完整雙軌閘門、偵測不到才走
    自陳降級的 fallback。指向它＝零硬寫磁碟路徑（寫死路徑會被 commit，對 Git 裝在
    別處的 checkout 一律是錯的），且與 ONBOARDING.md §6 對照表的 Windows 欄一致。
    """
    if IS_WINDOWS:
        _out(r"""
✅ bootstrap 完成。

下一步（每個新終端機都要做，或設進 profile / VSCode 直譯器）：
    .venv\Scripts\Activate.ps1
    （若報「因為這個系統上已停用指令碼執行」：先跑
      Set-ExecutionPolicy RemoteSigned -Scope CurrentUser 一次性放行，再重新啟用）

啟用後驗證：
    Get-Command python      # 應指向 .venv\Scripts\python.exe
    cd AutoClaude; python -m pytest tests/ -q
    powershell -ExecutionPolicy Bypass -File AISDLC_SDD\scripts\ci-gate.ps1

git hooks（選用）：安裝根層 dispatcher hooks — 兩子專案閘門同時生效
（AutoClaude pre-commit/pre-push ＋ AISDLC_SDD pre-push，依 commit/push
涉及路徑自動分流），不再互斥；任一支安裝腳本皆指向同一 dispatcher，跑一次即可：
    powershell -ExecutionPolicy Bypass -File AutoClaude/tools/install_git_hooks.ps1
    （或 AISDLC_SDD/scripts/install-hooks.ps1，效果相同）""")
    else:
        _out("""
✅ bootstrap 完成。

下一步（每個新終端機都要做，或設進 shell profile / VSCode 直譯器）：
    source .venv/bin/activate

啟用後驗證：
    which python            # 應指向 .venv/bin/python
    cd AutoClaude && python -m pytest tests/ -q
    cd AISDLC_SDD && bash scripts/ci-gate.sh

🔴 重要：請在「已啟用 .venv 的終端機」中啟動 Claude Code，否則 hooks 用的
   裸 `python` 會在 macOS 找不到直譯器。VSCode 則於右下角選 .venv 為直譯器。

git hooks（選用）：安裝根層 dispatcher hooks — 兩子專案閘門同時生效
（AutoClaude pre-commit/pre-push ＋ AISDLC_SDD pre-push，依 commit/push
涉及路徑自動分流），不再互斥；任一支安裝腳本皆指向同一 dispatcher，跑一次即可：
    bash AutoClaude/tools/install_git_hooks.sh
    （或 bash AISDLC_SDD/scripts/install-hooks.sh，效果相同）""")


_WRAPPER_NAME = "tools/bootstrap.ps1" if IS_WINDOWS else "tools/bootstrap.sh"

_USAGE_EPILOG = f"""\
本腳本**不接受任何旗標**（`--help` 除外）。指定未知旗標一律 fail-loud（rc=2），
不會退回預設行為——R67-F9：兩支薄殼原樣透傳 `$@`／`@args` 到一個完全不讀 argv
的核心，導致 `{_WRAPPER_NAME} --help` 靜默跑完整套 bootstrap（無 .venv 的新機器
上等於憑空建 venv ＋下載整套依賴），而任何 typo（例如把 `--force-bootstrap`
打成 `--forse-bootstrap`）同樣 rc=0 走預設路徑，使用者誤以為已強制重建、實際
只是沿用舊 .venv。

預設行為（無參數）：
  1. `.venv` 已存在 → 沿用（形狀不符本平台則 fail-fast，不自動刪除）
  2. 否則挑一個 >= 3.11 的直譯器（偵測到 uv 則用 `uv venv --python`）建立 `.venv`
  3. 安裝 AutoClaude（editable, [dev,notifications,lint]）＋ AISDLC_SDD CI 依賴
  4. 印出啟用指引與 git-hooks 安裝選項（不自動改 core.hooksPath）

.venv 位置：{VENV_DIR}
重建 .venv：{"Remove-Item -Recurse -Force .venv" if IS_WINDOWS else "rm -rf .venv"} 後再跑本腳本一次
相關旗標的正確歸屬：`--force-bootstrap`／`--no-sync`／`--check-nightly` 屬
`tools/dev_start.py`（`{"powershell -ExecutionPolicy Bypass -File tools/dev_start.ps1"
  if IS_WINDOWS else "bash tools/dev_start.sh"} --help`），不是本腳本。
"""


def build_parser() -> argparse.ArgumentParser:
    """本核心的 CLI 契約：零旗標 ＋ `-h/--help`；未知參數由 argparse 以 rc=2 拒絕。

    刻意用 `argparse` 而非手寫 argv 比對：同目錄 `tools/dev_start.py`／
    `integration_gate_core.py`／`run_act_core.py` 皆走 argparse，未知旗標 fail-loud
    與 usage 文字格式一併沿用同一套語意（Rule 11 conformance）。`prog` 依平台指向
    使用者實際會敲的薄殼名，而非核心檔名——使用者從沒直接呼叫過 bootstrap_core.py。
    """
    return argparse.ArgumentParser(
        prog=_WRAPPER_NAME,
        description="AISDCL_Agent monorepo 一鍵開發環境整備（建立 .venv ＋安裝兩子專案依賴）。",
        epilog=_USAGE_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )


def main(argv: list[str] | None = None) -> int:
    # 自身 stdout/stderr best-effort 行緩衝 + UTF-8 編碼：非 TTY（管線/log 擷取）下
    # Python 預設對 stdout 做 full buffering，會讓本檔狀態訊息與子行程（uv/pip）
    # 即時輸出交錯錯亂（對齊 tools/local_ci_gate.py／AutoClaude/tools/run_act_core.py
    # main() 同款收斂；R16 一審 Architect 抓到本檔獨漏，此為補齊）。R44 複審發現本檔
    # 獨漏 encoding="utf-8", errors="replace"：本檔大量輸出 ✅/❌/⚠️/🔴 等符號，被導向
    # （如 CI 用 `*>&1 | Out-String` 擷取）的 Windows 非 UTF-8 codepage（cp950/cp1252）
    # 終端下會 UnicodeEncodeError 崩潰，補齊對齊 AutoClaude/tools/run_act_core.py 同款
    # reconfigure() 呼叫（DEF-101-362）。
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        except (AttributeError, OSError, ValueError):
            pass

    # 🔴 參數解析必須在**任何副作用之前**（R67-F9）：`--help` 要真的什麼都不做，
    # 未知旗標要在 chdir／建 venv／裝依賴之前就擋下。argparse 於 `--help` 與
    # 參數錯誤時皆以 `SystemExit` 收場，此處收攏成 return code，讓 main() 維持
    # 「回傳 int」的既有契約（呼叫端 `sys.exit(main())` 與單元測試皆不需改）。
    try:
        build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit as exc:
        return 0 if exc.code is None else int(exc.code)

    os.chdir(REPO_ROOT)

    py_target = read_py_target(REPO_ROOT)
    header_platform = "（Windows）" if IS_WINDOWS else "（macOS/Linux）"
    _out(f"===== AISDCL_Agent bootstrap{header_platform}=====")
    _out(f"repo 根：{REPO_ROOT}")
    _out(f"目標 Python：>= {py_target}（.python-version）")

    use_uv = shutil.which("uv") is not None
    if use_uv:
        _out("偵測到 uv → 使用 uv 建立/安裝（加速）")

    rc = ensure_venv(py_target, use_uv)
    if rc != 0:
        return rc

    venv_py = platform_utils.venv_python_path(VENV_DIR, is_windows=IS_WINDOWS)
    rc = install_dependencies(use_uv, venv_py)
    if rc != 0:
        return rc

    print_completion_guide()
    return 0


if __name__ == "__main__":
    sys.exit(main())
