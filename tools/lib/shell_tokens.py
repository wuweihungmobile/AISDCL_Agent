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
