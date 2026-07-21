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

import os
import shutil
import subprocess
import sys
from pathlib import Path

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
        if shutil.which(parts[0]) is None:
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
        _err("❌ 既有 .venv 缺 Scripts\\python.exe（多半是 macOS/Linux 上建立的 .venv）— 本平台無法沿用。")
        _err("   請刪除後重建：Remove-Item -Recurse -Force .venv；再跑 powershell -ExecutionPolicy Bypass -File tools/bootstrap.ps1")
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
        _err(f"❌ .venv 建立指令回報成功（rc=0）但 Scripts\\python.exe 不存在（直譯器：{used_interp_label}）。")
        _err("   請刪除後重試：Remove-Item -Recurse -Force .venv；再跑 powershell -ExecutionPolicy Bypass -File tools/bootstrap.ps1")
    else:
        _err(f"❌ .venv 建立指令回報成功（rc=0）但 bin/python 不存在（直譯器：{used_interp_label}）。")
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
                _out(f"⚠️ 選定直譯器為 {actual_mm}，與 .python-version 目標 {py_target} 不一致（仍 >= 3.11 可用）")
            else:
                _out(f"⚠️  選定直譯器為 {actual_mm}，與 .python-version 目標 {py_target} 不一致（>=3.11 仍可用，僅提醒）")

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

    _out("[1/2] AutoClaude（editable, [dev,notifications,lint]）")
    autoclaude_target = f"{REPO_ROOT / 'AutoClaude'}{os.sep}.[dev,notifications,lint]"
    rc = pip_install(use_uv, venv_py, ["-e", autoclaude_target])
    if rc != 0:
        _err(f"❌ 依賴安裝失敗（rc={rc}）：pip install -e {autoclaude_target}")
        return rc

    sdd_req = REPO_ROOT / "AISDLC_SDD" / "AISDLC_SDD_v0.01" / "requirements-ci.txt"
    if sdd_req.is_file():
        _out("[2/2] AISDLC_SDD CI 依賴（requirements-ci.txt）")
        rc = pip_install(use_uv, venv_py, ["-r", str(sdd_req)])
        if rc != 0:
            _err(f"❌ 依賴安裝失敗（rc={rc}）：pip install -r {sdd_req}")
            return rc
    else:
        _out(f"[2/2] 略過：找不到 {sdd_req}")
    return 0


def print_completion_guide() -> None:
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
    cd AISDLC_SDD; bash scripts/ci-gate.sh   # 需 Git Bash

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


def main() -> int:
    # 自身 stdout/stderr best-effort 行緩衝：非 TTY（管線/log 擷取）下 Python 預設對
    # stdout 做 full buffering，會讓本檔狀態訊息與子行程（uv/pip）即時輸出交錯錯亂
    # （對齊 tools/local_ci_gate.py／AutoClaude/tools/run_act_core.py main() 同款收斂；
    # R16 一審 Architect 抓到本檔獨漏，此為補齊）。
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(line_buffering=True)
        except (AttributeError, OSError, ValueError):
            pass

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
