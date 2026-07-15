#!/usr/bin/env python3
"""共用 git hooks 安裝流程 — 單一真相源（Python），供 .ps1/.sh 兩份 thin wrapper 呼叫。

WHY（獨立複審 finding，對應 DEF-101-068(c)/S11/E23 的後續修正）：本輪原本把
「雙軌維護降為共用模組」的解法選成「.ps1 一份＋.sh 一份」各自重寫共用邏輯
（tools/lib/GitHooksInstallCommon.ps1 + tools/lib/git_hooks_install_common.sh），
本身仍是兩份獨立實作，重新引入了它宣稱要消除的「雙軌漂移」風險類別。本檔改採
本 repo 已證明可行、同一輪內就有活範例的模式（tools/check_hooks_liveness.py
被 integration_gate.{sh,ps1}／local_ci_gate.{sh,ps1} 四個呼叫點共用一份判定邏輯；
tools/dev_start.py 呼叫同一份 evaluate()）：判定邏輯只在這裡實作一次，
tools/lib/GitHooksInstallCommon.ps1 與 tools/lib/git_hooks_install_common.sh
皆改為呼叫本檔 CLI 子指令的薄殼層（只保留該平台原生的呈現層 —— PowerShell 的
Write-Host 顏色、bash 的全域變數回傳慣例 —— 不再各自重寫判定邏輯本身）。

子指令（見 main() 的 argparse；exit code 為呼叫端唯一應依賴的判斷依據）：
  assert-not-linked-worktree [--prefix P]
      不在 git repo 內、或偵測到 linked worktree（git-dir ≠ git-common-dir）時，
      印錯誤到 stderr 並 exit 1；否則 exit 0。
  get-hooks-dir [--prefix P]
      印出 `<repo根>/tools/git-hooks` 絕對路徑（正規化）到 stdout；
      不在 git repo 內時印錯誤到 stderr 並 exit 1。
  assert-hooks-present <hooks_dir> [--prefix P]
      三支 dispatcher hook 檔（pre-commit/pre-push/post-commit）皆存在則
      best-effort chmod +x 後 exit 0；缺一即印錯誤到 stderr 並 exit 1（於第一個
      缺失處停止，與原兩版逐行複製的迴圈行為一致）。
  check-installed <hooks_dir>
      印兩行到 stdout：`CUR=<core.hooksPath 目前值或空字串>` 與 `OK=1|0`；
      恆 exit 0（成功/失敗由呼叫端讀 `OK=` 那行決定，不外顯於本子指令的 exit code，
      對齊原 PowerShell 版 `Test-GitHooksPathInstalled` 不 exit、只回傳結構化結果
      交由呼叫端決定成功/失敗訊息的既有設計）。

用法：
  python tools/git_hooks_install_common.py get-hooks-dir --prefix '[install_git_hooks] '
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(中文/❌/⚠) 防崩潰保護

HOOK_FILENAMES = ("pre-commit", "pre-push", "post-commit")


def _run(cmd: list[str]) -> tuple[int, str]:
    """跑一個子指令，回傳 (returncode, stripped stdout)；任何例外一律視為失敗。"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
        return result.returncode, result.stdout.strip()
    except Exception:
        return 1, ""


def is_linked_worktree(git_dir: str, git_common_dir: str) -> bool:
    """git-dir 與 git-common-dir 正規化（resolve）後不同即為 linked worktree。"""
    return Path(git_dir).resolve() != Path(git_common_dir).resolve()


def missing_hook_files(hooks_dir: Path) -> list[str]:
    """回傳 `hooks_dir` 下缺少的 dispatcher hook 檔名（依 HOOK_FILENAMES 順序）。"""
    return [h for h in HOOK_FILENAMES if not (hooks_dir / h).is_file()]


def is_hooks_path_installed(repo_root: Path, hooks_dir: Path, current_value: str) -> bool:
    """core.hooksPath 目前值是否等於 `hooks_dir`（正規化後）且三支 hook 檔齊備。

    `current_value` 依 git 官方支援可存相對路徑，且規範應相對於工作樹根目錄
    （`repo_root`）解讀，而非呼叫當下的 cwd（獨立複審發現：舊版直接
    `Path(current_value).resolve()`，同一組輸入依 cwd 不同會給出不同答案，
    與姊妹判定邏輯 tools/check_hooks_liveness.py 的 `is_hooks_effective()` 行為
    不一致——該函式已正確先與 repo_root 組合再 resolve，本函式比照修正）。
    `Path.__truediv__` 對絕對路徑的第二運算元會直接取代整個路徑，故
    `current_value` 為絕對路徑時本行為不變。
    """
    if not current_value:
        return False
    try:
        cur = (repo_root / current_value).resolve()
    except OSError:
        return False
    if cur != hooks_dir.resolve():
        return False
    return not missing_hook_files(hooks_dir)


def cmd_assert_not_linked_worktree(prefix: str) -> int:
    rc, git_dir = _run(["git", "rev-parse", "--git-dir"])
    if rc != 0 or not git_dir:
        print(f"{prefix}❌ 不在 git repo 內（git rev-parse --git-dir 失敗）", file=sys.stderr)
        return 1
    rc2, git_common_dir = _run(["git", "rev-parse", "--git-common-dir"])
    if rc2 != 0 or not git_common_dir:
        print(f"{prefix}❌ 不在 git repo 內（git rev-parse --git-common-dir 失敗）", file=sys.stderr)
        return 1
    if is_linked_worktree(git_dir, git_common_dir):
        print(f"{prefix}❌ 偵測到 linked worktree（git-dir ≠ git-common-dir）", file=sys.stderr)
        print("   core.hooksPath 寫入共享 .git/config，在 worktree 內安裝/卸載會毒化主 checkout",
              file=sys.stderr)
        print("   （worktree 刪除後閘門靜默全滅）。請在主 checkout 執行安裝。", file=sys.stderr)
        return 1
    return 0


def cmd_get_hooks_dir(prefix: str) -> int:
    rc, top = _run(["git", "rev-parse", "--show-toplevel"])
    if rc != 0 or not top:
        print(f"{prefix}❌ 不在 git repo 內（git rev-parse --show-toplevel 失敗）", file=sys.stderr)
        return 1
    hooks_dir = (Path(top) / "tools" / "git-hooks").resolve()
    print(str(hooks_dir))
    return 0


def cmd_assert_hooks_present(hooks_dir_raw: str, prefix: str) -> int:
    hooks_dir = Path(hooks_dir_raw)
    missing = missing_hook_files(hooks_dir)
    if missing:
        print(f"{prefix}缺少 dispatcher hook 檔：{hooks_dir / missing[0]}", file=sys.stderr)
        return 1
    for h in HOOK_FILENAMES:
        try:
            (hooks_dir / h).chmod(0o755)
        except OSError:
            pass
    return 0


def cmd_check_installed(hooks_dir_raw: str) -> int:
    hooks_dir = Path(hooks_dir_raw)
    rc_top, top = _run(["git", "rev-parse", "--show-toplevel"])
    repo_root = Path(top) if rc_top == 0 and top else Path.cwd()
    rc, cur = _run(["git", "config", "--get", "core.hooksPath"])
    current_value = cur if rc == 0 else ""
    ok = is_hooks_path_installed(repo_root, hooks_dir, current_value)
    print(f"CUR={current_value}")
    print(f"OK={'1' if ok else '0'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p1 = sub.add_parser("assert-not-linked-worktree")
    p1.add_argument("--prefix", default="")

    p2 = sub.add_parser("get-hooks-dir")
    p2.add_argument("--prefix", default="")

    p3 = sub.add_parser("assert-hooks-present")
    p3.add_argument("hooks_dir")
    p3.add_argument("--prefix", default="")

    p4 = sub.add_parser("check-installed")
    p4.add_argument("hooks_dir")

    args = parser.parse_args()
    if args.command == "assert-not-linked-worktree":
        return cmd_assert_not_linked_worktree(args.prefix)
    if args.command == "get-hooks-dir":
        return cmd_get_hooks_dir(args.prefix)
    if args.command == "assert-hooks-present":
        return cmd_assert_hooks_present(args.hooks_dir, args.prefix)
    if args.command == "check-installed":
        return cmd_check_installed(args.hooks_dir)
    return 1  # pragma: no cover — argparse required=True 已排除未知子指令


if __name__ == "__main__":
    sys.exit(main())
