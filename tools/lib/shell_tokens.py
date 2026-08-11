"""引號感知的 shell token 切割（唯一的家）。

WHY 這一段從 `.claude/hooks/block_destructive_git.py` 搬出來（R84／C8）：它是一個
與「毀滅性 git 判準」完全無關的**通用原語**（判準②的 operand 取值用），而那支 hook
的護欄層 LOC 分級（`AutoClaude/tools/check_loc_budget.py` 的 `guardrail_cli<=750`）
逐字要求「先拆職責／抽共用模組」而不是把門檻調高。搬出來之後 hook 那支回到分級之內，
且下一個需要引號感知切割的消費者不必再抄第二份。

公開名 `shell_tokens`（hook 內沿用私有別名，呼叫端與既有回歸鎖一個字都不必改）。
"""
from __future__ import annotations


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
