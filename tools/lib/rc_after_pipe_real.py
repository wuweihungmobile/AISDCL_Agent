"""`rc-after-pipe-real` 的真機答案表與紅綠自證（R80／S7；DEF-200-481 起判準收歸 hook）。

判準本體住攔截端 `.claude/hooks/lint_powershell_command.py` 的 `_rc_after_pipe()`：攔截與量測
同吃一份，不再有「偏擋的攔截端」與「窄的量測端」兩套（`rc-after-pipe` 與本欄並印只為 `--parity`
對拍）。本檔只留兩樣東西：`_RC_SELFTEST`（pwsh 7.6／Windows PowerShell 5.1 逐形態真機答案表）
與 `selftest()`。依賴方向 `tools/probe → .claude/hooks` 不變：hook 由 `runpy.run_path` 起、
`sys.path` 上沒有 `tools/`，import 期爆掉會破壞它的 fail-open 契約，所以只能是被借的一方，
由呼叫端把已載入的 hook 模組傳進來。

真機結論（seed 一律先灌 7；「沒被寫入」在 pwsh 7 是保留前值 7、在 PS 5.1 是 -1，同為錯值）：
  ① 上游是外部執行檔（cmdlet 管線不碰 `$LASTEXITCODE`；`$v = git …` 之後 `$v | Select -First 1`
     不污染）。
  ② 管線提前結束（`Select-Object -First`／`-Index`，含縮寫 `-f`／`-ind`；`-Wait` 取消）⇒ 真 rc
     不被寫入；接另一支外部執行檔（findstr 等）⇒ 讀到消費者自己的 rc；其餘 cmdlet 消費者一律正確。
  ③ 之後才讀，且中間沒有一次真的外部呼叫——裸 `git status`／`python …`／`cmd /c …` 都會重設 rc；
     被函式／別名遮蔽的同名指令不會；curl／sc／more／wget 兩引擎分歧（5.1 是別名），不算重設。
  ④ 賦值／括號包住不改變 ②（DEF-200-483）：`$o = git … | Select -First 1`、`$(git … | …)`、
     `@(…)`、`(git … | …) | …`（截斷發生在括號內）真 rc 同樣沒被寫入；`(git …) | …`（括號先閉合）
     與 `$o = git status`（賦值右側的裸 git 重設 rc）則 rc 正確。
"""

from __future__ import annotations

from typing import Any


def rc_after_pipe_real(command: str, hook: Any) -> bool:
    """量測端入口＝攔截端判準本體 `hook._rc_after_pipe`（欄位名保留供報表與 `--parity` 對拍）。"""
    return bool(hook._rc_after_pipe(hook.mask_regions(command, keep_expandable=False),
                                    hook.mask_regions(command, keep_expandable=True)))


#: 🔴 `rc-after-pipe-real` 的紅綠自證語料（`audit_session.py --selftest` 與單元閘，可重跑）。
#:
#: 每列的 `measured` 是兩個引擎真機量出來的：先 `& cmd /c exit 7` 灌種子，跑該形態，再讀
#: `$LASTEXITCODE`，記成 `after=<pwsh 7>/<PS 5.1>`。讀到 7／-1＝真 rc 根本沒被寫入（真紅被讀成
#: 綠）；讀到別的值＝rc 被寫入（或被消費者換掉）。改判準時請連 `measured` 一起用兩個引擎重測，
#: 不要只改 `expect`（2026-10-04 以 pwsh 7.6.6／PS 5.1.26100.9444 逐列重測：既有 18 列原值全數
#: 重現、DEF-200-483 新增 11 列為同日實測；`python` 形態須先有輸出，靜默退出的 -First 1 不截斷）。
_RC_SELFTEST: tuple[tuple[str, bool, str, str], ...] = (
    # ── 已知違規（真 rc 被吃掉或換了主人） ──────────────────────────────
    ('git log --oneline -n 40 | Select-Object -First 1\n"rc=$LASTEXITCODE"',
     True, "after=7/-1", "截斷型 -First：git 的真 rc 完全沒被寫入"),
    ('git log --oneline -n 40 | select -First 1\n"rc=$LASTEXITCODE"',
     True, "after=7/-1", "同上的別名寫法（`select` 是最常見的寫法）"),
    ('git log --oneline -n 40 | Select-Object -Index 0\n"rc=$LASTEXITCODE"',
     True, "after=7/-1", "-Index 同樣提前結束管線"),
    ('git log --oneline -n 40 | Select-Object -First 1 | Out-Null\n'
     '$x = 1\n"rc=$LASTEXITCODE"',
     True, "after=7/-1", "跨語句污染：`$x = 1` 不重設 rc，污染延續到下一句的讀取"),
    ('git log --oneline -n 40 | Select-Object -First 1 | Out-Null\n'
     "function git { 'x' }\ngit status\n\"rc=$LASTEXITCODE\"",
     True, "after=7/-1", "函式遮蔽 git：呼叫的不是外部執行檔，污染不被清掉"),
    ('git log --oneline -n 40 | Select-Object -First 1 | Out-Null\n'
     'Set-Alias git Write-Output\ngit status\n"rc=$LASTEXITCODE"',
     True, "after=7/-1", "別名遮蔽 git：同上"),
    ('git log --oneline -n 40 | Select-Object -First 1 | Out-Null\n'
     'curl --version\n"rc=$LASTEXITCODE"',
     True, "after=0/-1", "curl 兩引擎分歧（7 是 curl.exe、5.1 是別名）：不入詞彙表"),
    ('git log --oneline -n 40 | findstr zzzqqq\n"rc=$LASTEXITCODE"',
     True, "after=1/1", "原生消費者：讀到的是 findstr 的 rc（1）而不是 git 的（0）"),
    # ── DEF-200-483：賦值／括號／子運算式包住的原生上游（判準曾一律放行） ──────
    ('$o = git log --oneline -n 40 | Select-Object -First 1\n"rc=$LASTEXITCODE"',
     True, "after=7/-1", "賦值包住的原生上游：管線頭是右側的 git，真 rc 沒被寫入"),
    ('$o = python -c "print(\'x\'); import sys; sys.exit(3)" 2>&1 | Select-Object -First 1\n'
     '"rc=$LASTEXITCODE"',
     True, "after=7/-1", "同上帶 2>&1：真 rc=3 被吃（python 有輸出，-First 1 才會提前結束）"),
    ('$o = $(git log --oneline -n 40 | Select-Object -First 1)\n"rc=$LASTEXITCODE"',
     True, "after=7/-1", "子運算式內的管線：git 在 $( ) 內就被截斷"),
    ('(git log --oneline -n 40 | Select-Object -First 1) | Out-Null\n"rc=$LASTEXITCODE"',
     True, "after=7/-1", "括號內被截斷、括號外再接管線"),
    ('Write-Output (git log --oneline -n 40 | Select-Object -First 1) | Out-Null\n'
     '"rc=$LASTEXITCODE"',
     True, "after=7/-1", "cmdlet 引數內的括號管線，同上"),
    ('$o = @(git log --oneline -n 40 | Select-Object -First 1)\n"rc=$LASTEXITCODE"',
     True, "after=7/-1", "陣列子運算式 @( ) 同 $( )"),
    ('$o = @()\n$o += git log --oneline -n 40 | Select-Object -First 1\n"rc=$LASTEXITCODE"',
     True, "after=7/-1", "複合賦值 += 的右側同樣是管線頭"),
    # ── 已知正解（rc 被正確寫入，或根本沒有外部指令在管線裡） ──────────────
    ('git log --oneline -n 40 | Select-String \'commit\'\n"rc=$LASTEXITCODE"',
     False, "after=0/0", "Select-String 不提前結束管線 ⇒ rc 正確"),
    ('git log --oneline -n 40 | Measure-Object\n"rc=$LASTEXITCODE"',
     False, "after=0/0", "Measure-Object 必須讀完全部輸入 ⇒ rc 正確"),
    ('& cmd /c "exit 3" | Out-File -Encoding utf8 x.txt\n"rc=$LASTEXITCODE"',
     False, "after=3/3", "Out-File 不截斷 ⇒ 真 rc=3 被正確讀到"),
    ('$v = git log --oneline -n 40\n$v | Select-Object -First 1\n'
     '"rc=$LASTEXITCODE"',
     False, "after=0/0", "管線左邊是變數不是原生指令 ⇒ 根 CLAUDE.md 教的正解形態"),
    ('git log --oneline -n 40 | Select-Object -First 1 | Out-Null\n'
     'git status --porcelain\n"rc=$LASTEXITCODE"',
     False, "after=0/0", "裸原生指令**會**重設 rc，污染在它之後被清乾淨（S7-09）"),
    ('git log --oneline -n 40 | Select-Object -Last 1\n"rc=$LASTEXITCODE"',
     False, "after=0/0", "-Last 必須讀完全部輸入 ⇒ rc 正確"),
    ('git log --oneline -n 40 | Select-Object -First 1 | Out-Null\n'
     'python -c "pass"\n"rc=$LASTEXITCODE"',
     False, "after=0/0", "裸 python（詞彙表）重設：污染在它之後被清乾淨"),
    ('git log --oneline -n 40 | Select-Object -First 1 | Out-Null\n'
     'cmd /c exit 3\n"rc=$LASTEXITCODE"',
     False, "after=3/3", "裸 cmd /c exit 3 重設：讀到的是它自己的 3"),
    ('Get-ChildItem . | Select-Object -First 1 | Out-Null\n"rc=$LASTEXITCODE"',
     False, "after=7/7", "無原生上游：-First 不碰 rc（前一個外部指令的真 rc 原樣保留）"),
    ('git log --oneline -n 40 | Out-File x.txt\n"rc=$LASTEXITCODE"',
     False, "after=0/0", "Out-File 不截斷 ⇒ git 的真 rc 被正確寫入"),
    ('(git log --oneline -n 40) | Select-Object -First 1\n"rc=$LASTEXITCODE"',
     False, "after=0/0", "已閉合的分組：git 先完整跑完才進管線 ⇒ rc 正確（對照 DEF-200-483）"),
    ('git log --oneline -n 40 | Select-Object -First 1 | Out-Null\n'
     '$o = git status --porcelain\n"rc=$LASTEXITCODE"',
     False, "after=0/0", "賦值右側的裸 git 也重設 rc：污染在它之後被清乾淨"),
    ('$o = git log --oneline -n 40 | Select-String \'commit\'\n"rc=$LASTEXITCODE"',
     False, "after=0/0", "賦值包住但 Select-String 不提前結束 ⇒ rc 正確"),
    ('git log --oneline -n (1 | Select-Object -First 1)\n"rc=$LASTEXITCODE"',
     False, "after=0/0", "括號內只是 cmdlet 上游：外面的 git 在引數算完後才跑 ⇒ rc 正確"),
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
