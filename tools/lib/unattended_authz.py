"""無人看管回合的**授權邊界**判準 ＋ 訊息——唯一的家（R85／P12）。

WHY 這一段要有第二個消費者，而且**不能**各守衛各抄一份
------------------------------------------------------
R79 立的規則是：排程叫起來的那一跑（`claude -p -r <sid>`，spawn 時注入
`AUTOSDD_UNATTENDED=1`）**不准動 git 歷史**——那是掌舵者開 Auto Pilot 的**條件**，
不是建議。它當時只落在 `.claude/hooks/lint_powershell_command.py`，而那支的
matcher 是 `PowerShell`、且第一件事是 `os.name != 'nt' → exit 0`。

⇒ **在 macOS 上，那條規則今天一行都不會跑**（本輪 P3 實測）：mac 的 shell 載具是
`Bash`，連 matcher 都對不上。而續航的那一跑（訴求 6d：reset 後自動喚醒續跑）正是
headless 代理，R83 已裁定「該做的是把 headless 代理的能力面**寫清楚**」——今天在 mac
上那個能力面**沒有任何機械物**。該 hook 檔頭自己已經把這個缺口寫成〈誠實劃界〉，
所以這不是被忘記，是被登記了卻一直沒補。

補的方式**不是**把判準抄進第二支 hook：本 repo 反覆判過那個病（R73 的
`Find-GitBash`、R77 的 ruff 規則集、R84 的「同一份知識住三個家、三種內容」）。判準與
訊息一律住這裡，兩支 hook 都向這裡取用。

為什麼 git 那一半允許呼叫端傳解析結果進來
------------------------------------------
兩支 hook 手上的東西不一樣：`lint_powershell_command` 只有一段遮蔽過的字串；
`block_destructive_git` 另有 `git_invocations()`——一個會處理 `sudo git`／`FOO=1 git`／
`git -C <path>`／`xargs git`／殼 `-c` operand 的真解析器。要求後者退回正則等於丟掉精準度，
要求前者長出解析器等於把那支 hook 重寫一遍。⇒ `authz_hits()` 的 git 那一半吃
**呼叫端已解析出的子指令集**，沒有就退回本檔的正則。`gh` 那一半兩邊共用同一條正則
（沒有第二個解析器，也就沒有第二份真相）。
"""
from __future__ import annotations

import re
from collections.abc import Iterable

#: 訊號本身。由 `tools/session_resume_planner.py` 的 `_run_resume()` 在 spawn 那一刻注入
#: 子行程環境（hook 是那個 `claude` 行程的子行程 ⇒ 一路繼承得到，含子代理派工）。
#: **正常互動 session 一律沒有這個變數**，整段不參與判定＝零附帶面。
UNATTENDED_ENV = "AUTOSDD_UNATTENDED"

#: 會動到 git 歷史／把改動送出去的子指令。刻意**只有這兩個**：那一跑要做的事正是
#: 「把狀態寫下來然後停」，擋到它讀 git、寫任務書、留稽核痕跡等於逼它什麼都不留就死掉。
GIT_WRITE_SUBS = frozenset({"commit", "push"})

#: 指令位置的邊界（行首／`;`／換行／`&&`／`|`／子殼括號之後都算一個指令的起頭）。
_CMD_START = r"(?:^|[;\n|&{}()])\s*"
#: 允許帶路徑前綴（`<某處>/git.exe`），但前綴必須以路徑分隔符結尾——否則
#: `legit commit`／`weigh pr create` 這種字尾巧合會被誤判。
_EXE_HEAD = r"(?:[^\s;|&]*[\\/])?"
#: 動詞與子指令之間允許夾參數（`git -C <path> commit`），但**不得跨越管線或 `&`**
#: （`git log | Select-String push` 不是在 push；🔴 R85／SD-B3 實測 `git log && echo push`
#: 也被判成 push——`&` 是**下一個**指令的起頭，跨過去等於把別人的參數算到 git 頭上）。
#: 子指令前要求一個空白，於是 `--grep=push` 這種「push 只是參數的值」不會命中。
_ARGS = r"[^;\n|&]*?\s"

#: 子指令後的邊界。🔴 R85／SD-B3：`.` 必須在裡面——`git config push.default`（唯讀設定
#: 查詢）實測被判成 push，而 git 的設定鍵**天生**以子指令名開頭（`push.*`／`commit.*`），
#: 這一族假紅在無人看管回合會擋掉「把狀態寫下來然後停」本身。
_SUB_END = r"(?![\w.-])"

GIT_WRITE_RE = re.compile(
    _CMD_START + _EXE_HEAD + r"git(?:\.exe)?(?![\w.-])" + _ARGS
    + rf"(?:{'|'.join(sorted(GIT_WRITE_SUBS))}){_SUB_END}", re.IGNORECASE)
GH_WRITE_RE = re.compile(
    _CMD_START + _EXE_HEAD + r"gh(?:\.exe)?(?![\w.-])" + _ARGS
    + rf"(?:pr|release)\s+(?:create|merge){_SUB_END}", re.IGNORECASE)

_GIT_HIT = ("  · git commit／git push（含 `git -C <path> …`、`git.exe`、"
            "`;`／換行／`&&`／`|` 之後的第二段指令）")
_GH_HIT = "  · gh pr create／pr merge／release create（把改動送出去的另一條路）"


def authz_hits(masked: str, git_subs: Iterable[str] | None = None) -> list[str]:
    """無人看管回合的命中清單（空＝放行）。純函式，紅綠由注入自證。

    `masked` 必須是**已遮蔽引號／註解**的結構面：訊息文字裡提到「git commit」不是在
    commit，硬擋它會讓那一跑連留下狀態都做不到——而「把狀態寫下來然後停」正是本條
    要它做的事。`git_subs`＝呼叫端解析器抽出的 git 子指令；`None` 表示沒有解析器，
    退回本檔的正則（見模組 docstring 最後一段）。
    """
    seen = (GIT_WRITE_SUBS & {str(s).lower() for s in git_subs} if git_subs is not None
            else (GIT_WRITE_SUBS if GIT_WRITE_RE.search(masked) else frozenset()))
    return ([_GIT_HIT] if seen else []) + ([_GH_HIT] if GH_WRITE_RE.search(masked) else [])


def authz_header(marker: str) -> str:
    """阻斷訊息的抬頭。`marker`＝該守衛自己的行內豁免標記名（各守衛不同，故是參數）。

    🔴 訊息必須指名**訊號**（讀者才知道怎麼關）與**替代動作**（那一跑才知道該做什麼），
    而不是只說「被擋了」——`tools/tests/test_check_hooks_liveness.py` 兩向釘住這兩件事。
    """
    return (
        f"🔴 這一跑是**被排程叫起來的無人看管回合**（環境變數 {UNATTENDED_ENV} 有設），"
        f"禁止動 git 歷史。這是掌舵者開啟 Auto Pilot 時的**條件**，不是可以商量的建議，"
        f"行內豁免 `# {marker}:` 對本條**無效**（豁免是給窄判準的出口，"
        "不是給授權邊界的）。\n"
        "  該做的事：把改動留在工作樹、把狀態寫進任務書／稽核痕跡，然後停下來讓人回來收。\n"
        "  本次命中：\n"
    )


def waiver_void_note(marker: str, why: str) -> str:
    """「行內豁免在本回合無效」的補述（接在別族判準的命中清單之後）。

    住這裡而不是住各 hook：這句話講的是**授權邊界**（誰有權開出口），不是那一族判準
    自己的內容；R85 之前它在 `block_destructive_git.py` 內有兩份逐字近似的複本。
    """
    return (f"\n  🔴 這一跑是**被排程叫起來的無人看管回合**（環境變數 {UNATTENDED_ENV} "
            f"有設），\n     行內豁免 `# {marker}:` 對本回合**無效**——{why}\n")
