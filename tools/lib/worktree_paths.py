"""拋棄式 worktree 根目錄的正規化與包含判斷（唯一的家）。

WHY 這一段從 `.claude/hooks/block_destructive_git.py` 搬出來（P0-1）：
舊版判準對 `victim` 做**純字串包含**（`_DISPOSABLE_WT in normcase(victim)`），
不解析 `..`——`<repo>/.claude/worktrees/../../AutoClaude` 這種路徑 `realpath` 後
其實落在拋棄式樹**之外**（等於 `<repo>/AutoClaude`），卻因為字面上仍帶著
`.claude\\worktrees\\` 這段子字串而被判定放行，讓 `git worktree remove --force`
的保護臂可以被 `..` 包裝繞過（含拿它刪 repo 根自己：
`<repo>/.claude/worktrees/../..` realpath 後等於 repo 根，同樣曾被誤判放行）。

修法對齊同檔既有的 `is_foreign_tree()`：比對前先把兩邊都 `os.path.realpath()`
（結構化解掉 `..`，不需要目錄真的存在即可正確收斂——即使 `.claude/worktrees`
從未被建立過也一樣，純字面解析），再疊一層 `os.path.normcase()`（覆蓋
NTFS 大小寫不敏感／正反斜線混用，且不依賴磁碟查詢，所以「大小寫正確」這件事
不必等 `realpath` 去問磁碟），再做**前綴**（不是子字串）比對。

🔴 分隔符取 `os.path.sep`（**不是** `os.sep`），雖然兩者在任一真實平台上恆為
同值。理由是可模擬性：本函式的平台行為必須**完全**由 `os.path` 決定，測試才能
用一個 `mock.patch.object(os, "path", ntpath)` 把 Windows 語意整包注入。舊寫法
把分隔符留在 `os.sep`（`os.path` 之外的全域），於是只換 `os.path` 的模擬會造出
一個不存在的混血平台——路徑是 `\\` 而分隔符是 `/`——判準當場對不上。這個形態
已經咬過兩次（R96 那兩支回歸鎖的 docstring 自己寫了同一件事），所以修的是**類別**
而不是實例：`os.path` 之外的平台全域，本函式一律不碰。

搬出來的理由同 `tools/lib/shell_tokens.py`（同檔第一段 WHY 逐字同構）：
這支護欄的 `guardrail_cli<=750`（`AutoClaude/tools/check_loc_budget.py`）已
零餘裕，任何新程式碼行都必須先抽共用模組，不是把門檻調高。
"""
from __future__ import annotations

import os
from collections.abc import Iterable, Iterator
from pathlib import Path

#: 拋棄式 worktree 根（相對 repo 根）的路徑段。Agent 工具 `isolation: worktree` 把整份 repo 副本
#: 建在 `<repo>/.claude/worktrees/<name>/`（gitignored）；副本含本體的全部 `.py`／`.ps1`。
DISPOSABLE_WORKTREE_PARTS: tuple[str, str] = (".claude", "worktrees")


def is_disposable_worktree_rel(rel_parts: Iterable[str]) -> bool:
    """相對 repo 根的路徑段是否落在拋棄式 worktree 內（DEF-200-647；純字面、不碰磁碟）。

    WHY 與下面兩支並存：`is_under_disposable_worktree` 問「這條**絕對路徑**在不在」（hook 的
    刪除保護臂用，要 realpath）；本函式問「掃描迭代到的這一筆算不算本體」——掃描器的檔案
    迭代已經是 repo 相對路徑，不該為每一筆再 realpath 一次。大小寫不敏感（NTFS）。
    """
    head = tuple(s.lower() for s in list(rel_parts)[:2])
    return head == DISPOSABLE_WORKTREE_PARTS


def rglob_live(repo_root: Path, pattern: str, base: Path | None = None) -> Iterator[Path]:
    """`(base or repo_root).rglob(pattern)`，但略過 `<repo_root>/.claude/worktrees/` 底下的副本。

    DEF-200-647（2026-11-24 nightly 6 紅、主樹 `{'live': 1205} != {'live': 37}`）：全 repo 檔案系統
    掃描器（`rglob`／`os.walk`）把代理 worktree 副本當本體掃，代理在飛期間必假紅。唯一的排除入口
    在這裡——掃描根是 repo 根或 `.claude/` 的掃描器一律走本函式，不各寫一份排除；掃描根是
    `tools/`、`tools/lib/` 等子樹者不需要（副本不在其下）。排除錨定在 repo 根（不是任意位置的
    同名目錄）：凍結版或夾具裡剛好有叫 `.claude/worktrees` 的路徑，仍照舊被掃。
    """
    for path in (base or repo_root).rglob(pattern):
        if not is_disposable_worktree_rel(path.relative_to(repo_root).parts):
            yield path


def disposable_worktree_root() -> str:
    """本次呼叫當下、這個專案拋棄式 worktree 根目錄的正規化路徑（不含結尾分隔符）。

    呼叫期現算（讀 `CLAUDE_PROJECT_DIR`），不是模組載入時的常數字面——不同 session／
    測試之間這個環境變數會變，凍成常數會讓比對永遠對著錯的根。
    """
    root = os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    return os.path.normcase(os.path.realpath(os.path.join(root, ".claude", "worktrees")))


def is_under_disposable_worktree(path: str) -> bool:
    """`path` 解析後是否落在 `disposable_worktree_root()` 之內（含它本身）。

    解析失敗一律回 `False`（fail-closed，不放寬）——與 `is_foreign_tree()` 同一取捨。
    """
    if not path:
        return False
    try:
        target = os.path.normcase(os.path.realpath(path))
    except OSError:
        return False
    wt_root = disposable_worktree_root()
    return target == wt_root or target.startswith(wt_root + os.path.sep)
