#!/usr/bin/env python3
"""run_act_core.py — 在本機 Docker 內以 act 重現 GitHub Actions 單一核心
（macOS/Linux/Windows 共用）。

架構收斂案（仿 R12 DEF-101-070 ② local_ci_gate 模式）：原 tools/run_act.{sh,ps1} 為雙實作
（bash / PowerShell 各長一份業務邏輯，靠人工「對齊 run_act.sh」註解手動同步），本檔將全部
業務邏輯收斂為單一 Python 核心，兩支同名 .sh / .ps1 降為「確認直譯器 → 參數映射 → 轉呼叫
本檔 → 傳遞 exit code」的薄殼。

monorepo 根層接線（2026-07-10）：workflow 已遷至 monorepo 根層
.github/workflows/autoclaude-ci.yml → act 一律於 monorepo 根執行（讀根層 .actrc）。

對應 GitHub push/PR 觸發的 gating jobs（autoclaude-ci.yml）：
  test               pytest + LOC budget + import-linter（主閘門）
  claude-md-budget   CLAUDE.md <= 400 行 + snapshot freshness
  equivalence        equivalence snapshot（needs: test）
  pg-contract        PG 契約測（含 postgres service；CI 標 continue-on-error）

nightly/排程 job（mutation / pg-e2e / perf）以 `if: schedule` 排除，push 事件不會觸發，
本地請改用 tools/run_local_nightly.{sh,ps1}。

依序（6 步；步驟編號與訊息沿用收斂前 .sh/.ps1）：
  1. 定位 act（含 gh-act 退回；Windows 另探測 winget 安裝路徑）
  2. 確認 Docker daemon
  3. List 模式（--list / -List，列出所有 job 後結束）
  4. 預先 pull 所需鏡像（繞過 act forcePull 對公開鏡像送無效認證的 401 bug）
  5. 空 .env 覆蓋（安全 + 忠實：GitHub runner 無 .env，避免注入個人憑證/偽 fail）
  6. 組裝並執行 act

用法（一般經薄殼呼叫；直接呼叫亦可）：
  python tools/run_act_core.py --job test     # 最快：只跑主測試閘門
  python tools/run_act_core.py                 # 完整：跑 push 全部 job（含 PG 契約）
  python tools/run_act_core.py --list          # 列出所有 job
  python tools/run_act_core.py --dry-run       # 只解析不執行
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent          # AutoClaude/tools
MONOREPO_ROOT = SCRIPT_DIR.parent.parent               # 本腳本上兩層 = monorepo 根
WORKFLOW = ".github/workflows/autoclaude-ci.yml"
RUNNER_IMAGE = "catthehacker/ubuntu:act-latest"
PG_IMAGE = "pgvector/pgvector:pg17"

# platform_utils 位於 monorepo 根 tools/lib/ 子目錄，本檔在 AutoClaude/tools/ 下，
# 需顯式插入 sys.path 才能 import——手法對齊本輪其他核心檔案既有慣例（R17
# DEF-101-231 觀察點 1+2：收斂 is_windows/os_label/venv_python_path 平台判斷邏輯
# 的第二次重複）。
sys.path.insert(0, str(MONOREPO_ROOT / "tools" / "lib"))
import platform_utils  # noqa: E402


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--job", default="", help="只跑單一 job（例：test）")
    parser.add_argument("--list", action="store_true", help="列出所有 job 後結束")
    parser.add_argument("--dry-run", action="store_true", help="只解析不執行（傳 -n 給 act）")
    return parser.parse_args(argv)


def _gh_act_extension_installed() -> bool:
    """gh extension list 是否含 gh-act（'gh-act' 子字串同時涵蓋 'nektos/gh-act'）。

    gh 未安裝時 subprocess 擲 FileNotFoundError（POSIX）或 OSError（Windows），
    對齊收斂前 .sh 的 `gh extension list 2>/dev/null || true` 容錯語意。
    """
    try:
        proc = subprocess.run(
            ["gh", "extension", "list"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        ext_list = proc.stdout or ""
    except OSError:
        ext_list = ""
    return "gh-act" in ext_list


def resolve_act() -> list[str] | None:
    """定位 act（含 gh-act 退回；Windows 另探測 winget 安裝路徑，對齊收斂前 .ps1）。

    回傳指令前綴（['act'] 或 ['gh', 'act'] 等），未尋獲回傳 None。
    """
    exe = shutil.which("act")
    if exe:
        return [exe]
    if platform_utils.is_windows():
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        if local_appdata:
            glob_pattern = "Microsoft/WinGet/Packages/nektos.act_*/act.exe"
            found = sorted(Path(local_appdata).glob(glob_pattern))
            if found:
                return [str(found[0])]
    if _gh_act_extension_installed():
        return ["gh", "act"]
    return None


def _print_install_hint() -> None:
    print("[run_act] act 未安裝。請擇一安裝：", file=sys.stderr)
    if platform_utils.is_windows():
        print("  winget install --id nektos.act -e", file=sys.stderr)
        print("  scoop install act", file=sys.stderr)
    else:
        print("  brew install act", file=sys.stderr)
    print(
        "  gh extension install https://github.com/nektos/gh-act   # 再以 gh act 呼叫",
        file=sys.stderr,
    )


def _run_quiet(cmd: list[str]) -> int:
    """靜音執行（探測用途）；命令不存在時視為失敗，對齊 shell 端「找不到指令即非 0」語意。"""
    try:
        return subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode
    except OSError:
        return 1


def check_docker() -> bool:
    """確認 Docker daemon 是否可連線（`docker info`）。"""
    return _run_quiet(["docker", "info"]) == 0


def image_ready(image: str) -> bool:
    return _run_quiet(["docker", "image", "inspect", image]) == 0


def pull_image(image: str) -> int:
    print(f"[run_act] 本地缺鏡像 {image} → docker pull（首次約 1~1.5GB）…")
    rc = subprocess.run(["docker", "pull", image]).returncode
    if rc != 0:
        print(f"[run_act] docker pull {image} 失敗。", file=sys.stderr)
    return rc


def ensure_images(job: str) -> int:
    """4. 預先 pull 所需鏡像（繞過 act forcePull 對公開鏡像送無效認證的 401 bug）。"""
    needed = [RUNNER_IMAGE]
    if not job:
        needed.append(PG_IMAGE)
    for image in needed:
        if image_ready(image):
            print(f"[run_act] 鏡像已就緒：{image}")
        else:
            rc = pull_image(image)
            if rc != 0:
                return 1
    return 0


def run_act(act_prefix: list[str], job: str, dry_run: bool, empty_env_path: str) -> int:
    """6. 組裝並執行 act。"""
    act_args = ["push", "-W", WORKFLOW, "--pull=false", "--env-file", empty_env_path]
    if job:
        act_args += ["-j", job]
    if dry_run:
        act_args += ["-n"]
    print(f"[run_act] 執行: {' '.join(act_prefix + act_args)}")
    return subprocess.run(act_prefix + act_args).returncode


def main(argv: list[str] | None = None) -> int:
    # 自身 stdout/stderr best-effort UTF-8 + 行緩衝：非 TTY（管線/log 擷取）下 Python 預設
    # 對 stdout 做 full buffering，會讓 stdout 進度訊息與 stderr 錯誤訊息交錯錯亂
    # （對齊 tools/local_ci_gate.py main() 同款收斂）。
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        except (AttributeError, OSError, ValueError):
            pass

    args = parse_args(sys.argv[1:] if argv is None else argv)
    os.chdir(MONOREPO_ROOT)

    print("[1/6] 定位 act（含 gh-act 退回）")
    act_prefix = resolve_act()
    if act_prefix is None:
        _print_install_hint()
        return 127
    print(f"[run_act] act = {' '.join(act_prefix)}")

    print("[2/6] 確認 Docker daemon")
    if not check_docker():
        print("[run_act] Docker daemon 未啟動，請先開啟 Docker Desktop。", file=sys.stderr)
        return 1

    print("[3/6] List 模式")
    if args.list:
        return subprocess.run(act_prefix + ["-l", "-W", WORKFLOW]).returncode

    print("[4/6] 預先 pull 鏡像")
    rc = ensure_images(args.job)
    if rc != 0:
        return 1

    print("[5/6] 空 .env 覆蓋")
    # act 預設會把 cwd 的 .env 注入容器。本 repo .env 含真實 MINIMAX_API_KEY / DB 憑證：
    #   (1) 安全：不應把個人憑證注入容器；
    #   (2) 忠實度：GitHub runner 無 .env，注入後會讓「預期 env 未設」的測試偽 fail。
    # 解法：傳一個空的 --env-file 覆蓋預設 .env 載入；tempfile + finally 確保清理不留垃圾。
    fd, empty_env_path = tempfile.mkstemp(prefix="autoclaude_act_empty_")
    try:
        os.close(fd)
        print("[6/6] 組裝並執行")
        rc = run_act(act_prefix, args.job, args.dry_run, empty_env_path)
    finally:
        try:
            os.remove(empty_env_path)
        except OSError:
            pass

    if rc == 0:
        print("[run_act] ✅ 本地 CI 通過（act 退出碼 0）— 可安全 push。")
    else:
        print(f"[run_act] ❌ 本地 CI 失敗（act 退出碼 {rc}）— 請於本機修復後再 push。")
    return rc


if __name__ == "__main__":
    sys.exit(main())
