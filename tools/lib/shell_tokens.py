"""引號感知的 shell token 切割（唯一的家）。

WHY 這一段從 `.claude/hooks/block_destructive_git.py` 搬出來（R84／C8）：它是一個
與「毀滅性 git 判準」完全無關的**通用原語**（判準②的 operand 取值用），而那支 hook
的護欄層 LOC 分級（`AutoClaude/tools/check_loc_budget.py` 的 `guardrail_cli<=750`）
逐字要求「先拆職責／抽共用模組」而不是把門檻調高。搬出來之後 hook 那支回到分級之內，
且下一個需要引號感知切割的消費者不必再抄第二份。

公開名 `shell_tokens`（hook 內沿用私有別名，呼叫端與既有回歸鎖一個字都不必改）。
"""
from __future__ import annotations

import re


def shell_tokens(text: str) -> list[str]:
    """引號感知的 token 切割（回**去引號後**的字面）。

    存在理由：判準②的 operand 必須從**原字串**取，而原字串裡它常常是被引號包住的
    （`pgrep -f 'run_root[_]unittests'`）——`str.split()` 會把引號帶進來、
    `mask_inert()` 會把它整段抹掉，兩者都拿不到那對方括號。
    遇到頂層的重導／管線／分隔符即停：那表示 pgrep 的參數列已經結束。
    """
    stop = " \t\r\n|;&(){}<>"
    toks: list[str] = []
    i, n = 0, len(text)
    while i < n:
        if text[i] in " \t\r\n":
            i += 1
            continue
        if text[i] in "|;&(){}<>":
            break
        buf: list[str] = []
        while i < n and text[i] not in stop:
            ch = text[i]
            if ch in "'\"":
                i += 1
                while i < n and text[i] != ch:
                    buf.append(text[i])
                    i += 1
                i += 1
            else:
                buf.append(ch)
                i += 1
        toks.append("".join(buf))
    return toks


#: 「整段就是一條路徑、且以目標執行檔收尾」的引號字面——根 CLAUDE.md 鐵律二**明訂**的
#: Windows 寫法（`& 'C:\\Program Files\\Git\\bin\\git.exe' push`）。起頭限碟符／`/`／`\\`／
#: `~`／`.`，且執行檔前必須有一個路徑分隔符 ⇒ 散文（`'run git.exe push'`）與純資料
#: （`'git push'`）都不會命中：前者不以執行檔收尾，後者沒有分隔符。
_QUOTED_EXE_RE = re.compile(
    r"""(['"])((?:[A-Za-z]:)?[\\/~.][^'"\n]*[\\/](?:git|gh)(?:\.exe)?)\1""", re.IGNORECASE)


def unquote_exe_paths(text: str) -> str:
    """把「被引號包起來的執行檔路徑」就地換成它的 basename，**長度逐字元不變**。

    WHY（R85／SD-B3，實測立案）：兩支守衛都先 `mask_*()` 把引號區段抹成空白才判——
    而鐵律二要求的正是把絕對路徑**用引號包起來**呼叫，於是那條路徑連同 `git.exe`
    整段消失。實測：`& '<Program Files 下的絕對路徑>\\git.exe' stash` 在
    `destructive_git_hits()` 與授權邊界兩條路上**都不擋**（同一條指令去掉引號則兩條都擋）
    ⇒ 這不是「比較寬鬆」，是本 repo 自己明訂的寫法恰好落在射程外。

    長度不變是**前提不是巧合**：`mask_inert()`／`mask_regions()` 的等長不變式讓遮蔽後
    可以跟原字串比位置，本函式若改變長度會把那個不變式一起弄壞。

    刻意**不判「指令位置」**：`git_invocations()` 本來就掃每一個 token 位置
    （`sudo git`／`xargs git` 都認），再加一層位置判準只會多一個與它不一致的家。

    誠實劃界：只認**帶路徑分隔符**的形態。裸的 `& 'git' push`（引號包住純指令名）
    不在射程內——它不是鐵律二要求的絕對路徑寫法，而放寬到那裡會讓 `-f 'git'` 這類
    把指令名當資料的參數一起被解讀成呼叫。
    """
    return _QUOTED_EXE_RE.sub(
        lambda m: re.split(r"[\\/]", m.group(2))[-1].ljust(len(m.group(0))), text)


# ── 判準⑤（迴圈內輪詢 `gh run`）──────────────────────────────────────────────────
# WHY 住在這裡而不是 hook：hook 屬 `guardrail_cli<=750` 分級（只算斷言行），判準⑤是與毀滅性
# git 無關的「迴圈區間辨識」原語，依 R84 先例抽成共用模組；hook 只剩三行薄接線。
# 立案＝掌舵者真機回報 sid 680d8411-58ac-4adb-9e23-521f6a7bb557（2026-11-14）：手寫輪詢以短 SHA
# 查 `gh run list --commit` 回 `[]` 且 rc=0，結束條件永不成立，CI 全綠後主控閒置 78 分鐘。
CI_POLL_TAG = "迴圈內輪詢 `gh run`"
CI_POLL_MESSAGE = (
    CI_POLL_TAG + "：手寫迴圈沒有自己的截止時間，也分不出「還沒跑完」與「查不到」（`gh run list "
    "--commit <短 SHA>` 回 `[]` 且 rc=0 ⇒ 結束條件永不成立；2026-11-14 事故：CI 約 20 分鐘全綠、"
    "主控閒置 78 分鐘）。改用 `python tools/ci_wait.py --commit <rev>`（`run_in_background: "
    "true`、輸出導檔；自帶硬截止時間、先解完整 SHA、查無 run 大聲失敗）。🔴 本條不吃 "
    "`# waitform-ok:`，人的逃生口只有 `AUTOSDD_GIT_GUARD_OFF`")
_GH_RUN_RE = re.compile(
    r"(?<![\w./-])gh(?:\.exe)?\s+(?:[^\s;|&(){}]+\s+){0,2}?run\s+(?:list|view|watch)(?![\w.-])")
#: 迴圈頭：bash／PowerShell 的 `while`／`until`、PowerShell 的 `do {`、無限 `for(;;)`。
_LOOP_HEAD_RE = re.compile(
    r"(?<![\w.-])(?:while|until|do(?=\s*\{)|for(?=\s*\(\(?\s*;\s*;\s*\)?\)?))(?![\w.-])")
_OPENER_OR_DONE_RE = re.compile(r"(?<![\w.-])(?:while|until|for|select|done)(?![\w.-])")
_DONE_RE = re.compile(r"(?<![\w.-])done(?![\w.-])")
_DO_TAIL_RE = re.compile(r"\s*(?:while|until)\s*\(")
_BLOCK_RE = re.compile(r"\s*\{")


def ci_poll_is(reason: str) -> bool:
    """這條命中理由是不是判準⑤的（`main()` 用它讓行內 `# waitform-ok:` 對⑤無效）。"""
    return reason.startswith(CI_POLL_TAG)


def _balanced_end(view: str, i: int, op: str, cl: str) -> int:
    """`view[i]` 是 `op` ⇒ 回配對 `cl` 之後的位置；配不起來回 -1。"""
    depth = 0
    for j in range(i, len(view)):
        if view[j] == op:
            depth += 1
        elif view[j] == cl:
            depth -= 1
            if depth == 0:
                return j + 1
    return -1


def _loop_regions(view: str) -> list[tuple[int, int]]:
    """遮蔽面（字串／註解已是空白）上所有迴圈構造的 (起, 迄)。

    PowerShell：`while|until|for (cond) { … }`、`do { … } while|until (cond)`（尾巴併入區間，
    尾巴的 `while` 不另算一個迴圈）；bash：`while|until cond; do … done`（`done` 依巢狀深度
    配對，配不到就到字串尾）。只有條件、沒有區塊也沒有 `done` 的單獨 `while (cond)` 只算
    條件本身，不把它之後的獨立指令吞進區間（否則「迴圈後的單次查詢」會被誤判）。
    """
    regions: list[tuple[int, int]] = []
    tails: list[tuple[int, int]] = []
    for head in _LOOP_HEAD_RE.finditer(view):
        if any(a <= head.start() < b for a, b in tails):
            continue
        k = head.end()
        while k < len(view) and view[k] in " \t\r\n":
            k += 1
        end = -1
        if head.group(0) == "do":
            end = _balanced_end(view, k, "{", "}")
            tail = _DO_TAIL_RE.match(view, end) if end > 0 else None
            if tail and (cond_end := _balanced_end(view, tail.end() - 1, "(", ")")) > 0:
                tails.append((end, cond_end))
                end = cond_end
        elif view.startswith("(", k) and (cond_end := _balanced_end(view, k, "(", ")")) > 0:
            block = _BLOCK_RE.match(view, cond_end)
            if block:
                end = _balanced_end(view, block.end() - 1, "{", "}")
            elif not _DONE_RE.search(view, cond_end):
                end = cond_end
        if end < 0:
            depth, end = 1, len(view)
            for m in _OPENER_OR_DONE_RE.finditer(view, head.end()):
                depth += -1 if m.group(0) == "done" else 1
                if depth == 0:
                    end = m.end()
                    break
        regions.append((head.start(), end))
    return regions


def ci_poll_hit(view: str) -> str | None:
    """判準⑤：`view`（hook 的遮蔽面）裡有迴圈構造的條件或迴圈體含 `gh run list|view|watch`
    ⇒ 回命中理由 `CI_POLL_MESSAGE`，否則 None。單次查詢與迴圈後的單次查詢不判。"""
    if any(_GH_RUN_RE.search(view, a, b) for a, b in _loop_regions(view)):
        return CI_POLL_MESSAGE
    return None
