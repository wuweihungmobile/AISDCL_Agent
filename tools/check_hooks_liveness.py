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

🔴 射程（QA-R81 N-3；照實寫在檔頭，因為誤用已經真的發生過）：本工具驗的是
**載具存在性**（git hooks 的 core.hooksPath ＋ Claude Code hook 的 exec form 載具），
**不驗 hook 的形態**。把一條 shell form 條目注回 `AutoClaude/.claude/settings.json`
（＝退掉 R81 P7 的一部分）後本工具仍回 rc=0，而同一棵樹上
`python -m unittest test_check_hooks_liveness`（於 tools/tests/）當場 FAILED 並指名
「shell form 條目實測 1、基準 0」。⇒ 拿本工具的 rc 當「exec form 轉換沒有被退回」
的憑證是**假綠**；形態那一面的唯一憑證是那支 unittest。
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

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


def check_claude_hook_carriers(repo_root: Path) -> bool:
    """**Claude Code** hook 載具的 liveness（R80 新增；git hooks 那半在下面）。

    WHY 這半非有不可：R80 把根 `.claude/settings.json` 的 hook 條目轉成 **exec form**
    （不經 `bash.exe` ⇒ 不再每觸發一次就閃一個 console 視窗），而 exec form 的
    `command` 是一個**執行檔路徑**：`${CLAUDE_PROJECT_DIR}/.venv/Scripts/pythonw.exe`。
    那個檔不在時（沒跑過 bootstrap／venv 被砍掉／被重建到別處），CC 只記一行 ERROR
    就放行——**六支守衛全部靜默失效，而螢幕上的表徵就是「終於不閃窗了」**。

    🔴 為何落在本檔而不是 CI 或 hook 自己：
      · 不能放在 hook 裡——載具沒了那支 hook 也跑不了（雞生蛋）。
      · 不能只靠 CI——**CI 從不跑 Claude Code hook**，在那裡這個檢查沒有意義（不是
        「會誤紅所以跳過」，是語意上不適用）；而本檔的四個呼叫端（local_ci_gate.{ps1,sh}
        ／integration_gate.{ps1,sh}）本來就在 `$CI` 有值時整段跳過，這個豁免是既有的、
        語意的，不是為了讓紅變綠新加的。
      · 判準本身（`tools/lib/hook_wiring.carrier_liveness_problems`）是**宣告 ↔ 實況
        雙向綁定**：settings.json 宣告了哪個載具，就要求那個載具存在 ⇒ 有人把載具
        換掉時同一條規則跟著移動，不會退化成守著一個過時的硬編路徑。

    🔴 R84：掃描面由「只有根層那一份」擴到 `discover_active_settings()` 現查出來的
    **每一份活躍 settings**（根層／AutoClaude／SDD LATEST）。立案理由是這半原本只問
    根層，而另外兩份各自宣告**不同的** venv 載具——`AutoClaude/.claude/settings.json` 的
    Windows 載具是 `AutoClaude/.venv/Scripts/pythonw.exe`（那是另一個 venv，由
    `AutoClaude/tools/bootstrap.*` 建），它不存在時該子專案 session 的六支守衛全部靜默
    失效，而本工具當時一個字都不會說。每一份用**它自己的專案根**展開佔位符（子專案
    session 的 `CLAUDE_PROJECT_DIR` 就是那個子目錄；拿 monorepo 根去展開帶 `../` 的載具
    會 normpath 到 repo 之外而假紅）。同一條載具被多份宣告時訊息去重。

    與本檔既有那半一樣是 **advisory**：印警告、回 False，不阻擋呼叫端閘門。
    """
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
        import hook_wiring  # noqa: PLC0415

        problems: list[str] = []
        for rel in hook_wiring.discover_active_settings(repo_root):
            settings_path = repo_root / rel
            if not settings_path.is_file():
                continue  # 沒有 settings＝沒有宣告，無從判定
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            project_dir = str(settings_path.parent.parent)
            for problem in hook_wiring.carrier_liveness_problems(settings, project_dir):
                entry = f"[{rel}] {problem}"
                if entry not in problems:
                    problems.append(entry)
    except Exception:
        return True  # 判不出來一律不出聲（同本檔既有的 advisory 語氣）
    if not problems:
        return True
    print("")
    print("[hooks liveness] Claude Code hook 載具不存在 — 這台機器上**全部 hook 都不會跑**！")
    for problem in problems:
        print(f"    {problem}")
    print("    （本檢查僅警告、不阻擋閘門執行；CI 環境由呼叫端整段跳過——"
          "CI 從不執行 Claude Code hook）")
    return False


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
    # 兩個 liveness 是**獨立**的失效面（git hooks 閘門 vs Claude Code hook 載具），
    # 兩邊都要出聲——只回報其中一個會讓另一個的失效變成靜默。
    carriers_ok = check_claude_hook_carriers(top_path)
    if result.ok:
        return carriers_ok

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


#: CLI 恆印的射程告示（檔頭 WHY 的一行版）。刻意印在 `__main__` 而不是函式裡：
#: 誤用發生在**讀 rc 的人**身上，而讀 rc 的人一定是走 CLI 這條路。
SCOPE_NOTICE = (
    "[hooks liveness] 射程＝git hooks 生效性 ＋ Claude Code hook 載具存在性。"
    "**形態判準（exec form / shell form 普查）不在本工具射程內**，"
    "本工具 rc=0 不代表沒有人把 hook 退回 shell form——"
    "那一面請跑：python -m unittest test_check_hooks_liveness（於 tools/tests/）"
)

if __name__ == "__main__":
    print(SCOPE_NOTICE)
    sys.exit(0 if check_hooks_liveness() else 1)
