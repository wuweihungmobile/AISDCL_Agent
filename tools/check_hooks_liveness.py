#!/usr/bin/env python3
"""共用 git hooks liveness 偵測（advisory-only）— S11 抽出，S22 再收斂判定核心。

WHY（S11）：repo 搬移/改名或未安裝 dispatcher hooks 時 core.hooksPath 會靜默失效
（pre-commit/pre-push 閘門不執行也不報錯）。原偵測邏輯（比對 core.hooksPath
與 `<repo根>/tools/git-hooks` 是否一致）在四支腳本（AutoClaude/tools/
local_ci_gate.{ps1,sh} + tools/integration_gate.{ps1,sh}）逐行複製，抽出
為本檔單一真相源，四個呼叫點各改一行呼叫（DEF-101-068(c) / S11）。

WHY（S22）：四方複審再發現，`tools/dev_start.py` 的 step_hooks()（每日自動修復，
step 5/7）另外重寫了一份幾乎相同的判定邏輯（含 linked worktree 感知——core.hooksPath
永遠指向主 checkout 絕對路徑，比較基準須用主 checkout 推算，不能用當前 worktree 自己的
根目錄），與本檔的 advisory-only 版本行為分歧（本檔原本完全不處理 linked worktree，
在該情境下會誤判假警告）。本輪把「判定演算法」（預期 dispatcher 目錄在哪、
core.hooksPath 目前值是否等於該目錄、三支 hook 檔是否齊備）抽成 `evaluate()` /
`resolve_expected_hooks_dir()` / `is_hooks_effective()` 三個不含任何 git 子行程呼叫、
不印訊息的純函式，dev_start.step_hooks() 與本檔的 `check_hooks_liveness()` 皆呼叫
同一份 `evaluate()`；兩處唯一容許的差異在於「取得輸入的方式」（dev_start 用固定
`-C ROOT` 的既有 `_git()` helper；本檔用自己的 `_run()`，依賴呼叫時的 cwd）與
「拿到結果後的反應」（dev_start 自動重跑安裝腳本；本檔只印警告不阻擋）——
判定邏輯本身不再有第二份實作。

本檢查（`check_hooks_liveness()` / CLI 入口）僅警告、不阻擋呼叫端閘門（呼叫端應
忽略本腳本的 exit code）；CI 環境的略過邏輯由呼叫端負責（呼叫端於 `$CI`/`$env:CI`
有值時整段跳過）。

用法：
    python tools/check_hooks_liveness.py

Exit code：0 = hooks 已生效（或不在 git repo 內、無法判定）；
           1 = 偵測到未生效（已印出警告；advisory，呼叫端不應據此中止）。
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(中文/全形標點) 防崩潰保護

HOOK_FILENAMES = ("pre-commit", "pre-push", "post-commit")


def _run(cmd: list[str]) -> str:
    """跑一個 git 子指令，回傳 stripped stdout；任何失敗一律回傳空字串。

    encoding 必須顯式指定：`text=True` 無 encoding 在無 PYTHONUTF8 的 Windows 終端
    走 locale（zh-TW＝cp950），git 輸出的 UTF-8 非 ASCII repo 路徑會 UnicodeDecodeError
    → liveness 偵測靜默失效（無法判定＝不警告；R9 跨平台複審實證）。
    """
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=10, check=False
        )
        if result.returncode != 0:
            return ""
        return result.stdout.strip()
    except Exception:
        return ""


@dataclass(frozen=True)
class LivenessResult:
    """`evaluate()` 的結構化判定結果——呼叫端依此自行決定要自動修復還是只印警告。"""

    ok: bool
    hooks_dir: Path
    current_value: str
    is_linked_worktree: bool


def resolve_expected_hooks_dir(
    repo_root: Path, git_dir: str, git_common_dir: str
) -> tuple[Path, bool]:
    """算出「預期的 dispatcher 目錄」與「是否為 linked worktree」。

    linked worktree（git-dir 與 git-common-dir 不同）時，core.hooksPath 是所有
    worktree 共用的同一個值、且永遠指向主 checkout 的絕對路徑——預期目錄必須以
    git-common-dir 推回主 checkout 根目錄計算，不能用 `repo_root`（可能是本
    worktree 自己的根目錄，physical 位置與主 checkout 天生不同，用它比對會恆為
    False）。
    """
    hooks_dir = repo_root / "tools" / "git-hooks"
    try:
        hooks_dir = hooks_dir.resolve()
    except OSError:
        pass
    is_linked_worktree = False
    if git_dir and git_common_dir:
        try:
            gd_resolved = Path(git_dir).resolve()
            gcd_resolved = Path(git_common_dir).resolve()
            is_linked_worktree = gd_resolved != gcd_resolved
            if is_linked_worktree:
                hooks_dir = gcd_resolved.parent / "tools" / "git-hooks"
        except OSError:
            pass
    return hooks_dir, is_linked_worktree


def is_hooks_effective(
    repo_root: Path,
    hooks_dir: Path,
    current_value: str,
    *,
    is_file: Callable[[Path], bool] = lambda p: p.is_file(),
) -> bool:
    """core.hooksPath 目前值是否等於 `hooks_dir` 且三支 hook 檔齊備。

    `is_file` 可由呼叫端注入（例如 dev_start.py 傳入自家的 `_safe_is_file()`，
    吞掉外接碟/網路磁碟抖動造成的 OSError）；預設用裸 `Path.is_file()`，與本檔
    CLI 入口原本的行為一致。
    """
    if not current_value:
        return False
    try:
        resolved = (repo_root / current_value).resolve()
    except OSError:
        return False
    if resolved != hooks_dir:
        return False
    return all(is_file(hooks_dir / h) for h in HOOK_FILENAMES)


def evaluate(
    repo_root: Path,
    git_dir: str,
    git_common_dir: str,
    current_value: str,
    *,
    is_file: Callable[[Path], bool] = lambda p: p.is_file(),
) -> LivenessResult:
    """單一判定入口：純函式，不呼叫任何 git 子行程、不印訊息。

    呼叫端各自負責取得四個輸入字串（`git rev-parse --git-dir` /
    `--git-common-dir` / `config --get core.hooksPath` 的 stdout，以及要比對的
    repo 根目錄），本函式只做判定本身。
    """
    hooks_dir, is_linked_worktree = resolve_expected_hooks_dir(
        repo_root, git_dir, git_common_dir
    )
    ok = is_hooks_effective(repo_root, hooks_dir, current_value, is_file=is_file)
    return LivenessResult(
        ok=ok,
        hooks_dir=hooks_dir,
        current_value=current_value,
        is_linked_worktree=is_linked_worktree,
    )


def check_hooks_liveness() -> bool:
    """CLI advisory 入口：自行取得 git 輸入、交給 `evaluate()` 判定，僅印警告不阻擋。

    回傳 True＝hooks 已生效（或無法判定，視為不警告）；False＝已印出未生效警告。
    """
    top = _run(["git", "rev-parse", "--show-toplevel"])
    if not top:
        return True  # 不在 git repo 內：無法判定，交由呼叫端自身前置檢查負責

    top_path = Path(top).resolve()
    git_dir = _run(["git", "-C", str(top_path), "rev-parse", "--git-dir"])
    git_common_dir = _run(["git", "-C", str(top_path), "rev-parse", "--git-common-dir"])
    raw = _run(["git", "-C", str(top_path), "config", "--get", "core.hooksPath"])

    result = evaluate(top_path, git_dir, git_common_dir, raw)
    if result.ok:
        return True

    shown = result.current_value if result.current_value else "（未設定）"
    print("")
    print("[hooks liveness] dispatcher git hooks 未生效 — pre-commit/pre-push 閘門不會執行！")
    print(f"    core.hooksPath 目前值：{shown}")
    print(f"    預期值：{result.hooks_dir}")
    if result.is_linked_worktree:
        print("    偵測到 linked worktree：core.hooksPath 由所有 worktree 共用，"
              "請至主 checkout 執行安裝腳本：")
    else:
        print("    請執行安裝腳本（兩子專案閘門同時生效，裝一次即可）：")
    print("        powershell -ExecutionPolicy Bypass -File AutoClaude/tools/install_git_hooks.ps1")
    print("        bash AutoClaude/tools/install_git_hooks.sh")
    print("    （本檢查僅警告、不阻擋閘門執行；CI 環境自動跳過）")
    return False


if __name__ == "__main__":
    sys.exit(0 if check_hooks_liveness() else 1)
