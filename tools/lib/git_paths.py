"""git 路徑列舉的唯一取數層（R81 包 G／XPL-S1-01）。

🔴 立案理由（實測，非假設）：`git ls-files`／`git diff --name-only` 預設會把**非 ASCII
路徑**以 C-quoted 形態輸出（`"a/\346\211\213\346\251\237.md"`）。本機今天不會炸，唯一
的原因是 `.git/config` 裡有一行 `core.quotepath=false`——那個檔由 `git clone` 就地新建、
**不是 tracked**，不隨 repo 走。也就是說這條路上真正的守門員是「這台機器的偶然事實」，
和 R73 判過的 `Find-GitBash` 寫死安裝路徑同型，只是這次那個事實連 grep 都掃不到。

當回合實測（R81）：全庫 27,566 條 tracked 路徑中 **630 條非 ASCII**；同一支列舉在
`quotepath=false` 與 `quotepath=true` 兩種設定下 key 集合**差 630 筆**，而 C-quoted key
拿去 `Path(...).is_file()` 回 **False** ⇒ 那 630 個檔會**靜默掉出掃描面**。失效方向是
「本機恆綠、mac 開發機／CI runner／任何 fresh clone 恆紅（或更糟：靜默縮面）」，且縮面
的表徵是「看起來更乾淨」（同 R76 Scan-H⑦）。

修法形狀＝**把旗標從「每個站點各自記得」升成取數層**。散在 repo 裡的十幾個站點原本各自
寫一次 `-c core.quotepath=false`，記得的人多、漏的人少，但漏掉的那一個不會有任何東西轉紅。
配套的門住在 `tools/tests/test_platform_neutral_paths.py::TestGitPathEnumerationIsQuotepathSafe`
（新站點漏帶旗標即紅；今天漏帶的存量逐筆登記，只准變少）。

🔴 刻意用 `-c core.quotepath=false` 而不是 `-z`：`-z` 改的是**分隔符**（NUL 取代換行），
所有消費端的 `splitlines()` 都要跟著改；`quotepath` 只改**引號化**，對既有解析零影響。
兩者都能解，選對消費端衝擊最小的那個。判準兩種都接受（見該測試）。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

#: 關掉 C-quoted 路徑輸出的 git 全域旗標。**唯一的家**——其餘站點一律走本模組。
QUOTEPATH_OFF: tuple[str, ...] = ("-c", "core.quotepath=false")


def git_argv(repo_root: Path | str, *args: str) -> list[str]:
    """組出帶 quotepath 旗標的 git argv（純函式，供測試直接比對，不碰磁碟）。"""
    return ["git", "-C", str(repo_root), *QUOTEPATH_OFF, *args]


def run(
    repo_root: Path | str, *args: str, timeout: int = 180
) -> subprocess.CompletedProcess[str]:
    """跑一次路徑列舉型 git 指令。rc 由呼叫端判——本層不代為決定 fail-loud 與否。

    `encoding="utf-8"` ＋ `errors="replace"` 是刻意的：關掉 quotepath 之後 git 直接吐
    原始位元組，Windows 的 CP950 主控台編碼會把中文路徑讀壞（同 `DEF-101-798` 那一族）。
    """
    return subprocess.run(
        git_argv(repo_root, *args),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def ls_files(repo_root: Path | str, *args: str, timeout: int = 180) -> list[str]:
    """`git ls-files <args>` 的非空輸出行。rc≠0 一律回空 list ＝取數管道壞掉。

    刻意**不**在這裡 raise：本 repo 既有的消費端對「取數失敗」有兩種正確處置（fail-loud
    的 AssertionError、與回空 dict 讓呼叫端報「管道壞掉」），把其中一種硬寫進共用層等於
    替另一半做決定。回空 list 是可被兩者辨識的訊號。
    """
    proc = run(repo_root, "ls-files", *args, timeout=timeout)
    if proc.returncode != 0:
        return []
    return [line for line in proc.stdout.splitlines() if line]
