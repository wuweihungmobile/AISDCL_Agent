#!/usr/bin/env python3
"""靜態掃描器的「掃描面」單一真相源：**git 已追蹤 ∪ 未追蹤但非 ignored**。

## 為什麼需要這支模組（R58 round 2 ARCH-R58R2-01）

R58 新增了多支 repo-wide 靜態掃描器（能力門檻／用法示範／行為層鎖／編碼 hygiene…），
初版一律用 `git ls-files`（**只列 tracked**）。round 1 Architect 實測指出：本輪自己新增的測試檔
當時全是 untracked，於是「全套測試 ＋ 守門工具全綠」的基線**在定義上排除了本輪自己寫的
程式碼**——正是本輪立案要消滅的形態（宣稱涵蓋面 ≠ 實際涵蓋面）在守門器自身復發。

round 1 只改了其中一支（`test_platform_guard_availability._scanned`），round 2 Architect 抓到
**旗艦行為層鎖仍是 tracked-only**，兩支同輪、同需求的掃描器因此有兩套政策且無記載理由。
依本 repo 判例（`docs/06_quality/CrossPlatform_Scan_Dimensions.md`〈靜態掃描錨為何從三份複本
收斂為 SSOT〉）的第二層分診問句——**這 N 份複本是否觀測同一個對象？** 兩支觀測的都是
「本 repo 的檔案集合」⇒ 複本數不產生鑑別力，**應收斂為 SSOT**。故有本模組。

## 契約

`scanned(pattern)` ＝ `git ls-files <pattern>` **∪** `git ls-files --others --exclude-standard <pattern>`
（去重後排序）。

**適用範圍（R58 round 3 ARCH-R58R3-01 訂正：原文寫「一律用它」，而同一個 commit 內就有兩支
本輪新寫的掃描器沒用它、且沒有記載理由——無條件命令＋未記載的例外＝下一輪必生爭議）**：

> 凡以「**新程式碼在 `git add` 之前也必須被守，否則新程式碼享有豁免**」為論證的靜態掃描器，
> 一律用 `scanned()`。

**刻意不適用的一類：共用已提交產物的掃描面。** golden fixture 家族
（`tools/gen_ps_comment_golden.tracked_ps1`／`tools/tests/test_ps_comment_golden._tracked_ps1`）
必須維持 **tracked-only**，理由不是疏漏而是正確性：`ps_comment_golden.json` 是**被提交、由所有人
共用**的產物。若它的掃描面含本機未追蹤檔，那些條目會被烤進共用產物，別人 checkout 後新鮮度
檢查會報「golden 仍登記已不存在／已不 tracked 的檔案」而**集體翻紅**——把機器本地狀態污染進
共用工件。同理，產生器與驗證器兩側必須用**同一個**掃描面，否則 `--check` 恆不一致。

**呼叫端鎖**：`tools/tests/test_platform_guard_availability.py::RepoScanSsotCallsiteLock`
——凡在 `*test_*.py` ∪ `tools/*.py` 內自寫 `git ls-files` 字面而未走本模組者，必須列入該鎖的
附理由例外登記表（golden 家族兩支即登記於此）。

**已實測涵蓋**：`--exclude-standard` 已套用 `.gitignore`／`.git/info/exclude`／global excludes，
故 `.venv/`、`__pycache__/`、產物與 log 皆不入面。

**已實測不涵蓋**（誠實劃界）：
  * 被刻意 ignore 的目錄仍在面外——這與 git 自身的可見性定義一致，不另行擴張。
  * **git index 面**：本模組看的是**工作樹**。「已 `git add` 之後又改工作樹」造成的
    index/worktree 分歧不在本模組職責內（R58 round 2 SA-R58R2-01 實測踩到過一次：
    staged 版壞掉而 worktree 是好的，本機零訊號、要等 CI 才紅）。需要驗 index 面者，
    請在 pre-commit 以 `git show :<path>` 取待提交內容後另行檢查。
  * shallow／detached HEAD 環境：`git ls-files` 讀 index 不需要歷史，故不受影響（已實測
    本機正常路徑；**未在真 shallow clone 上驗過**，故列此劃界）。

**未窮舉**：不宣稱「除此之外無盲區」。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def scanned(pattern: str) -> list[str]:
    """回傳符合 pattern 的 repo 相對路徑：tracked ∪ untracked-but-not-ignored（排序去重）。"""

    def _ls(extra: list[str]) -> list[str]:
        return subprocess.run(
            ["git", "ls-files", *extra, pattern],
            cwd=_REPO_ROOT, capture_output=True, text=True, encoding="utf-8", check=True,
        ).stdout.splitlines()

    both = _ls([]) + _ls(["--others", "--exclude-standard"])
    return sorted({ln.strip() for ln in both if ln.strip()})
