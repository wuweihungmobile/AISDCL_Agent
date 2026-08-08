"""`rc-after-pipe-real` 判準本體（R80／S7-01＋S7-09）——「真的會量到假 rc」的那一欄。

為何住在 `tools/lib/` 而不是 `tools/probe/audit_session.py` 裡（R80 收尾包移出）：
消費端受根層 `guardrail_cli<=750` 的 LOC 分級管，而該分級的合法出口逐字寫著
「先拆職責／抽共用模組（先例：tools/lib/ci_liveness.py），確認為不可壓縮的真實功能後
才具名調高」。本模組就是那個「拆職責」——它是一組**純函式＋一張實測語料表**，與逐字稿
掃描、報表、CLI 全無耦合，本來就該獨立。**不得**為了讓它留在原地而調高 LOC 上限。

依賴注入：兩支判準要用攔截端（`.claude/hooks/lint_powershell_command.py`）的純函式，
但那支 hook 只能是**被借的一方**（它由 `runpy.run_path` 起、`sys.path` 上沒有 `tools/`，
import 期爆掉會破壞它的 fail-open 契約）。故本模組**不自己載入 hook**——由呼叫端把已載入
的 hook 模組傳進來。這也避免了「同一份載入邏輯住兩個家」。

──────────────────────────────────────────────────────────────────────────
🔴 S7-01＋S7-09：把「攔截端會擋什麼」與「真的會量到假 rc 幾次」拆成兩欄
──────────────────────────────────────────────────────────────────────────
上一欄（`rc-after-pipe`）＝攔截端那支函式本身。R79 把它借過來，理由是「兩端不會
再漂移」——那件事達成了，但它同時把**攔截端刻意保守的偏擋**整批灌進了量測數字，
而那個數字正是拿來對根 CLAUDE.md 下結論用的。攔截端偏擋是對的（誤報有行內豁免
當出口，漏擋沒有）；量測器偏擋不是——它會讓「這條規則有多少真違規」整整高一個
數量級，而下結論的人看到的是量測器。

R80 pwsh 7.6.4 真機逐形態實測（腳本與逐字輸出見交件的證據檔），seed 一律先灌 7、
再看 `$LASTEXITCODE` 有沒有被寫成 git 的真 rc(0)：

  git log … | Select-Object -First 1   → after=7  ← STALE：真 rc 完全沒被寫入
  git log … | select      -First 1     → after=7  ← 同上（別名）
  git log … | Select-Object -Index 0   → after=7  ← 同上
  git log … | Select-String / Sort-Object / Measure-Object / ForEach-Object
            / Where-Object / Out-Null / Out-String / Format-Table / Tee-Object
            / % {…} / findstr           → after=0  ← 全部正確寫入，一個都不污染
  git log … | Select-Object -Last 1 / -Skip 1 / -First 1 -Wait / -First 999
                                       → after=0  ← 不提前結束管線就不污染
  $v = git log …; $v | Select-Object -First 1 → after=0 ← 左邊是變數不是原生指令

⇒ 真正會產生「真紅被讀成綠」的條件是三個**同時**成立，不是「看到管線就算」：
  ① 管線左段真的在跑一支**外部執行檔**（cmdlet 管線根本不碰 `$LASTEXITCODE`）；
  ② 管線接進的是**會提前結束**的元素（實測只有 `-First N`／`-Index N`，且 `-Wait`
     會取消提前結束、`-First N` 在 N 大於輸出筆數時也不會）；
  ③ 之後才讀 `$LASTEXITCODE`。

本 repo 逐字稿全母體實測（見報表的量測窗）：`rc-after-pipe` 152 命中裡有 139 筆
（91.4%）不滿足這三條 ⇒ 那一欄**不可**被引用成「違規次數」。誤報的大宗正好是根
CLAUDE.md 逐字教的正解形態（`& <exe> …; "rc=$LASTEXITCODE"` 之後另起一句用管線
篩輸出）——方向是「越遵守規則、違規率越高」，用它做的歸因符號相反。

🔴 兩欄都留、都印，不合併：`rc-after-pipe` 是**對拍錨**（`--parity` 與
`TestHookAndProbeShareOneCriterion` 靠它證明兩端沒漂移），`rc-after-pipe-real`
是**唯一可引用為「量到幾次真風險」的那一欄**。
"""

from __future__ import annotations

import re
from typing import Any

#: 實測會提前結束管線的元素。`-Wait` 明確排除（實測 after=0）。
#: 刻意**不**收 `head`：pwsh 沒有這個指令，它只在 Bash 工具面成立而那一面另有鐵律一。
_TRUNCATING_PIPE_RE = re.compile(
    r"\|\s*(?:Select-Object|select)(?![\w-])"
    r"(?![^|;\n]*-Wait(?![\w-]))"
    r"[^|;\n]*?(?:-First|-Index)(?![\w-])",
    re.IGNORECASE,
)

#: 語句開頭若是這些字，那**不是**外部執行檔（PowerShell 內建別名／關鍵字）。
#: 這張表是「裸原生指令偵測」的偽陰性面：漏收一個別名就會把它誤判成原生呼叫、
#: 進而誤以為污染被清掉（＝漏報方向）。刻意只收**真的會出現在語句開頭**的那些。
_PS_ALIAS_HEADS = frozenset("""
echo ls dir cat type cd chdir sl rm del ren cp copy move mv pwd md mkdir rmdir
select sort where foreach measure sls gc sc gi gci gcm gm iwr irm man help cls
clear history kill ps sleep tee write ft fl oh popd pushd gal sal gp sp gv sv
rv ni ri mi ci gl gu nal compare diff group set get new test out format
""".split())
_PS_KEYWORD_HEADS = frozenset("""
if else elseif for foreach while do switch try catch finally function param
return throw break continue begin process end filter class enum using exit
trap data dynamicparam hidden static
""".split())
_STATEMENT_HEAD_RE = re.compile(r"^\s*(?:&\s*)?['\"]?([A-Za-z][\w.\\/:-]*)")


def head_is_native_invocation(statement: str) -> bool:
    """語句開頭是不是一支**外部執行檔**（⇒ 它會重寫 `$LASTEXITCODE`）。

    🔴 S7-09：攔截端的 `_statement_resets_rc()` 明文把「裸原生指令（`git status`
    這種不帶 `&`、不帶副檔名者）」判成**不算**重設，並自陳那是刻意偏擋。pwsh 7.6.4
    實測那句話是假的——`& cmd /c exit 7` 之後跑 `git status`，`$LASTEXITCODE` 由 7
    變成 0；`git nosuchsubcmd` 變成 1；`cmd /c exit 3` 變成 3。跨語句實測同樣成立：
    `git … | Select-Object -First 1` 造成的污染，被下一句裸 `git status` 清乾淨
    （after=0），被 `$x = 1` 清不掉（after=7）。
    ⇒ 攔截端偏擋的**代價方向**與它自陳的相反：它不是「多擋一點」，是把污染的存續
    區間算得比實際長，於是同一條指令後面所有的 rc 讀取都被判成違規。這個代價此前
    從未從量測數字裡扣掉，本函式就是扣掉它的地方。

    判準（誠實劃界）：帶 `.exe`／`.cmd`／`.bat` 副檔名 → 是；含 `-` 的 token 視為
    Verb-Noun cmdlet → 否；其餘裸字若不在內建別名／關鍵字表裡 → 視為外部執行檔。
    這是**啟發式**：使用者自訂函式（`function gp { … }` 之後寫 `gp`）會被誤判成原生
    呼叫（偽陽性、方向是漏報）。表本身是偽陰性面，見 `_PS_ALIAS_HEADS`。
    """
    match = _STATEMENT_HEAD_RE.match(statement)
    if not match:
        return False
    token = match.group(1)
    if re.search(r"\.(?:exe|cmd|bat|com)$", token, re.IGNORECASE):
        return True
    base = token.rsplit("\\", 1)[-1].rsplit("/", 1)[-1].lower()
    if "-" in base:  # Verb-Noun ＝ cmdlet，不是外部執行檔
        return False
    return base not in _PS_ALIAS_HEADS and base not in _PS_KEYWORD_HEADS


def statement_invokes_native(statement: str, hook: Any) -> bool:
    """這一句有沒有真的發起一次外部呼叫（＝`$LASTEXITCODE` 被重寫）。

    攔截端那兩個條件（呼叫運算子 `&`、`.exe` 開頭）**原樣沿用**，另補上實測證明
    會重設的第三種：裸原生指令。三者取聯集，不是另起一套。
    """
    return bool(
        hook._RC_RESET_RE.search(statement)
        or hook._NATIVE_HEAD_RE.search(statement)
        or head_is_native_invocation(statement)
    )


def rc_after_pipe_real(command: str, hook: Any) -> bool:
    """實測會產生**錯的 rc 讀數**的形態（上游原生 × 截斷型管線 × 之後讀 rc）。

    與 `rc-after-pipe`（＝攔截端那支函式）的差別只有兩處，兩處都由真機實測支撐
    （見本檔檔頭）：
      · 管線元素收窄到**實測會提前結束**的那兩個參數，其餘 14 種一律不算；
      · 管線左段必須真的在跑外部執行檔，且污染的解除認得裸原生指令。
    """
    structural = hook.mask_regions(command, keep_expandable=False)
    expandable = hook.mask_regions(command, keep_expandable=True)
    contaminated = False
    for start, end in hook.statement_spans(structural):
        segment = structural[start:end]
        truncating = _TRUNCATING_PIPE_RE.search(segment)
        pipe_pos = -1
        if truncating and statement_invokes_native(segment[:truncating.start()], hook):
            pipe_pos = start + truncating.start()
        for read in hook._RC_READ_RE.finditer(expandable[start:end]):
            if contaminated or (pipe_pos >= 0 and start + read.start() > pipe_pos):
                return True
        if pipe_pos >= 0:
            contaminated = True
        elif statement_invokes_native(segment, hook):
            contaminated = False
    return False


#: 🔴 `rc-after-pipe-real` 的紅綠自證語料（`--selftest`，可重跑）。
#:
#: 每一列的 `expect` **不是我認為它應該是什麼**，而是 pwsh 7.6.4 真機量出來的：先
#: `& cmd /c exit 7` 把 `$LASTEXITCODE` 灌成 7，跑該形態，再讀一次——讀到 7 表示
#: 真 rc 根本沒被寫入（＝STALE＝這條規則要防的「真紅被讀成綠」），讀到 0/3 表示
#: rc 被正確寫入（＝安全）。`after` 欄記的就是那個實測值，改判準時請連它一起重測，
#: 不要只改 `expect`。本 repo 的紀律 #4：驗證載具本身要被驗證——這張表就是這道判準的
#: 那一層，而它此前不存在（判準整支向 hook 借，沒有任何一組已知答案在守它）。
_RC_SELFTEST: tuple[tuple[str, bool, str, str], ...] = (
    # ── 已知違規（實測 after=7＝真 rc 被吃掉） ──────────────────────────
    ('git log --oneline -n 40 | Select-Object -First 1\n"rc=$LASTEXITCODE"',
     True, "after=7", "截斷型 -First：git 的真 rc 完全沒被寫入"),
    ('git log --oneline -n 40 | select -First 1\n"rc=$LASTEXITCODE"',
     True, "after=7", "同上的別名寫法（`select` 是最常見的寫法）"),
    ('git log --oneline -n 40 | Select-Object -Index 0\n"rc=$LASTEXITCODE"',
     True, "after=7", "-Index 同樣提前結束管線"),
    ('git log --oneline -n 40 | Select-Object -First 1 | Out-Null\n'
     '$x = 1\n"rc=$LASTEXITCODE"',
     True, "after=7", "跨語句污染：`$x = 1` 不重設 rc，污染延續到下一句的讀取"),
    # ── 已知正解（實測 rc 被正確寫入） ──────────────────────────────────
    ('git log --oneline -n 40 | Select-String \'commit\'\n"rc=$LASTEXITCODE"',
     False, "after=0", "Select-String 不提前結束管線 ⇒ rc 正確"),
    ('git log --oneline -n 40 | Measure-Object\n"rc=$LASTEXITCODE"',
     False, "after=0", "Measure-Object 必須讀完全部輸入 ⇒ rc 正確"),
    ('& cmd /c "exit 3" | Out-File -Encoding utf8 x.txt\n"rc=$LASTEXITCODE"',
     False, "after=3", "Out-File 不截斷 ⇒ 真 rc=3 被正確讀到"),
    ('$v = git log --oneline -n 40\n$v | Select-Object -First 1\n'
     '"rc=$LASTEXITCODE"',
     False, "after=0", "管線左邊是變數不是原生指令 ⇒ 根 CLAUDE.md 教的正解形態"),
    ('git log --oneline -n 40 | Select-Object -First 1 | Out-Null\n'
     'git status --porcelain\n"rc=$LASTEXITCODE"',
     False, "after=0", "裸原生指令**會**重設 rc，污染在它之後被清乾淨（S7-09）"),
    ('git log --oneline -n 40 | Select-Object -Last 1\n"rc=$LASTEXITCODE"',
     False, "after=0", "-Last 必須讀完全部輸入 ⇒ rc 正確"),
)


def selftest(hook: Any) -> list[str]:
    """跑 `_RC_SELFTEST`，回傳失敗訊息清單（空＝全綠）。純函式，供 `--selftest`。"""
    failures: list[str] = []
    for command, expected, measured, why in _RC_SELFTEST:
        got = rc_after_pipe_real(command, hook)
        if got is not expected:
            failures.append(
                f"判準說 {got}、實測是 {measured}（{'違規' if expected else '正解'}）"
                f"：{why}\n      {' '.join(command.split())[:150]}")
    return failures
