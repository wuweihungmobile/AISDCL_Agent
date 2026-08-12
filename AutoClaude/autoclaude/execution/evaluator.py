# 獨立評估器：在 Claude Code 子進程之外執行驗證指令。
# AI 說完成不算，由 Evaluator 親自執行並回傳結果。
#
# 🔴 R85：模組說明由 docstring 改為 `#` 註解（`#` 不計 LOC，內容一字未改）。動機不是
# 為了本檔——是為了不要把 total 餘裕吃到只剩 2 行就走人：下一個在 autoclaude/ 加三行
# 的人會撞上 [TOTAL] 阻塞，而那個紅與他自己改的東西毫無關係。
from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass

from ..utils.platform_caps import kill_process_tree, new_session_kwargs
from ..utils.trace_context import propagate_to_subprocess_env

logger = logging.getLogger("autoclaude.execution.evaluator")

# R69：行程樹回收（原 kill_process_tree）與平台守門一併收斂至
# utils/platform_caps.py —— 它與 perception/pty_wrapper.py `close()` 原本是同一套
# 邏輯的兩份複製（DEF-101-706）。此處僅 re-export 供既有呼叫端
# （mutation_applier/_conditional.py）沿用原 import 路徑。
# 常數在 import 期算一次，維持 `**_NEW_SESSION_KWARGS` 呼叫站點語意不變。
_NEW_SESSION_KWARGS: dict = new_session_kwargs()


# ──────────────────────────────────────────────────────────────────────────────
# 🔴 R85（AC-(a)）：無人看管回合的能力閘。
#
# 立案事實（不是假想）：續航路徑 `tools/session_resume_planner.py::_run_resume()` 以
# `claude -p -r <sid>` 把工作續跑起來，並在 spawn 那一刻注入 `AUTOSDD_UNATTENDED=1`。
# 那一跑沒有 TTY、沒有人在看，掌舵者對它的條件是「不准 commit／push」。該條件今天由
# monorepo 根層的 PreToolUse 守衛執行——而**那道守衛看不到 AutoClaude**：
#   · hook 的輸入是 Claude Code 的 `tool_input.command`。無人看管回合送出的是**一條**
#     `python -m autoclaude <playbook>`（本身完全無害、必然放行）；
#   · 其後 AutoClaude 自己以 `subprocess.Popen(shell=True)` 送出的每一條 evaluator／
#     condition 指令，都發生在**另一棵行程樹**裡，結構上不產生任何 tool 呼叫
#     ⇒ 六支 PreToolUse 守衛一次都不會被叫到。
# ⇒ 「把 AutoClaude 當舵手跑」（AC-(b) 正是這件事）會讓授權邊界整片失明，而失明是靜默的：
#    rc、log、畫面與「守衛有在守」完全相同。這一格只有 AutoClaude 自己補得起來。
#
# 為何不 import 根層那支 hook 的判準：`.importlinter` 第 9 條
# （`no-harness-import`：autoclaude must not import monorepo harness modules）明文禁止。
# ⇒ 這裡是**刻意的第二份實作**，而且刻意**更窄**：hook 那份守的是「毀掉工作樹的形態」
#   （stash／reset --hard／clean…），本函式守的是「授權邊界」（寫入遠端／歷史的動詞）。
#   兩者判準不同源、不該互相抄；把它們統一成一份的正確做法是改架構契約，不是偷偷 import。
#
# 零附帶面（同根層守衛的設計）：`AUTOSDD_UNATTENDED` 在互動 session 一律不存在
# ⇒ 本函式恆回 None，正常開發與 CI 一行行為都不變。
#
# 誠實劃界（本閘擋不到什麼）：
#   · 「改配置」那一半沒有判準——它沒有穩定的指令字面（可以是 Write、可以是 `sed`、
#     可以是 python 一行）。本閘只認寫入型 git／gh 動詞，別把它讀成完整的能力閘。
#   · 指令若把動詞藏進變數／別名／`python -c` 內字串，判準看不到。
#   · shell 函式與 `xargs`／`find -exec` 這類間接呼叫同樣看不到。
_UNATTENDED_ENV = "AUTOSDD_UNATTENDED"
# 動詞前要求一個空白 ⇒ `--grep=commit` 這種「動詞只是參數的值」不會命中；`[^;\n|]*?`
# 不跨管線／分號 ⇒ `git log | grep push` 不算在 push。路徑前綴須以分隔符結尾 ⇒
# `legit commit` 這種字尾巧合不會被誤判（與根層守衛同一組取捨，各自獨立維護）。
# 🔴 兩個載具前綴是本檔自己的測試在落地當回合抓出來的真實逃逸口，不是抄來的：
#   ① `VAR=x git commit`（POSIX 殼的環境賦值前綴）② `"C:\…\git.exe" push`（帶空白的
#   引號路徑——不加引號那一種在任何殼上本來就跑不起來，故刻意不判）。
_UNATTENDED_WRITE = re.compile(
    r"(?:^|[;&|]\s*)(?:(?:[A-Za-z_]\w*=\S*|env|sudo|nohup|command)\s+)*"
    r"(?:\"[^\"\n]*[\\/]|'[^'\n]*[\\/]|[^\s;|&\"']*[\\/])?(?:git|gh)(?:\.exe)?"
    r"(?![\w.-])[^;\n|]*?\s(?:commit|push|pr\s+create|pr\s+merge|release\s+create)"
    r"(?![\w-])", re.IGNORECASE)


def unattended_refusal(command: str | None) -> str | None:
    # 回傳拒絕理由（字串）或 None＝放行。刻意回字串而非 bool：呼叫端要把理由原樣
    # 交給使用者，「為什麼被擋」若只留在這裡，失效時的表徵會退化成一次普通的步驟失敗。
    if not os.environ.get(_UNATTENDED_ENV) or not command:
        return None
    return (f"{_UNATTENDED_ENV}=1（無人看管回合）拒絕執行寫入型 git／gh 指令："
            f"{command}") if _UNATTENDED_WRITE.search(command) else None


# ──────────────────────────────────────────────────────────────────────────────
# 🔴 R85 P7：`shell=True` 的**可攜性**診斷。與上方能力閘**不同軸**——那道守「授權」
# （誰准跑），這道守「同一條指令在另一個平台是什麼語意」。別把兩者混為一談。
#
# 立案事實（本輪逐句真跑，不是引述）：repo 內唯一與可攜性沾邊的輸入面過濾器
# `_SHELL_TRUE_COND_WHITELIST`（mutation_applier/_conditional.py）與可攜性目標**反相關**：
#   · `python -c "print(1)"`（該檔註解逐字建議的**可攜正解**）→ False（**擋掉**）
#   · `test -f foo`／`grep -q x f`／`pgrep -f x`／`pmset -g custom`／`rm -rf /`
#     （該檔註解逐字點名要避免的 POSIX 專屬語法）→ True（**全部放行**）
# 成因不是寫錯：它是 Gap-046 的**資安字元白名單**，擋的是 shell metacharacter
# （`;`／`(`／`)`／`$`／`|`／`&`／`%`／`\`）。`python -c "print(1)"` 被擋是因為括號，
# `test -f foo` 被放行是因為它剛好只用白名單字元 ⇒ 兩者都與可攜性無關。
# ⇒ 可攜性這一軸在本檔與姊妹檔此前**零判準**，而該檔註解那句「`&&`/`||` 則已被
#   Gap-046 擋下」讀起來像是有人在守，這正是它難以被發現的原因。
#
# 為何**只出聲、不阻擋**（三條各自獨立成立，任一條都足以否決「擋」那一版）：
#   ① 單平台 playbook 是**合法**的——只在 POSIX 部署跑的專案寫 `grep` 沒有任何錯，
#      擋它是純假紅；repo 已判過「擋到讓人無法工作的守衛會被整個關掉，而被關掉的
#      守衛比沒有守衛更糟」。
#   ② 詞彙表在 Windows 側會**過度命中**：Git for Windows 把 `grep`／`test`／`sed`
#      放進 PATH 是常態 ⇒ 「另一平台上一定跑不了」這個推論本身就不可靠，只能當提示。
#   ③ 真實母體（見回歸鎖的假紅普查）今天命中 **0** ⇒ 擋不擋在今天沒有行為差別，
#      而「擋」那一版帶著上面兩個風險。零收益 × 有風險 ⇒ 不擋。
#
# 為何**不能**改走 `shell=False` ＋ argv 陣列（本輪實測**否決**的候選解，不是沒想到）：
#   CONDITIONAL 的慣用寫法是 shell **builtin**——本 repo 自己的測試就用 `exit 0`／
#   `exit 1`（tests/test_gap021_028.py 四處）。本輪實測：`shlex.split("exit 0")` 送
#   `shell=False` → **FileNotFoundError**；同一句 `shell=True` → **rc=0**。
#   ⇒ 殼在這條路上是**承重的**，拔掉它會讓 CONDITIONAL 整個功能停擺。
#   姊妹實作 `core/services/mutation/_conditional_evaluator.py` 能走 `shell=False`，
#   是因為它另有 `_DENY_CHARS` 深度黑名單且其呼叫慣例不吃 builtin ⇒ **兩者不可互抄**。
#
# 判準**只認 argv[0]**，刻意不碰語法差異（`%VAR%` vs `$VAR`、引號、路徑分隔符）：
# 那一族假紅率高且無法只靠字面判定；argv[0] 是可判定、可逐筆辯護的那一半。
# 詞彙表刻意**不收** `exit`／`echo`／`cd`／`set`（cmd.exe 與 /bin/sh **都有**的
# builtin＝本來就可攜，收了就是對 repo 自己的慣用寫法製造假紅）。
_SINGLE_PLATFORM_ARGV0 = frozenset(("test grep sed awk ls cat rm cp mv chmod which pgrep"
    " pkill pmset launchctl uname sudo dir where taskkill powershell reg schtasks wmic").split())


def portability_note(command: str | None) -> str | None:
    # 回傳命中的 argv[0]（並出聲一次）或 None＝未命中。**永不阻擋、永不改變控制流**：
    # 兩個呼叫端都刻意忽略回傳值，回傳只是為了讓回歸鎖驗得到「它真的判了」——
    # 只驗 log 的鎖會在訊息措辭改動時假綠。
    argv0 = (command or "").strip().split(" ", 1)[0].rsplit("/", 1)[-1].strip("\"'")
    if argv0 not in _SINGLE_PLATFORM_ARGV0:
        return None
    logger.warning("可攜性：argv[0] `%s` 單平台專屬，另一平台原生殼上找不到：%s", argv0, command)
    return argv0


@dataclass
class EvalResult:
    success: bool
    output: str
    exit_code: int


class Evaluator:
    def __init__(self, timeout: int = 120):
        self._timeout = timeout

    def run(self, command: str, timeout: int | None = None) -> EvalResult:
        # 執行 playbook 作者提供的 evaluator_command。
        #
        # 跨平台注意：以 subprocess.run(shell=True) 執行，實際呼叫的是「作業系統原生殼」——
        # Windows 為 cmd.exe，POSIX 為 /bin/sh，而非固定的 bash。因此 evaluator_command
        # 必須寫成可攜指令（如 `pytest ...`、`python -c "..."`），避免 POSIX 專屬語法
        # （test -f、單引號字串、&&/||、grep 等 shell builtin/GNU 工具），否則在 Windows
        # 上會被 cmd.exe 解讀出非預期結果，而非清楚的「找不到指令」失敗。
        #
        # 🔴 R85（AC-(a)）：說明由 docstring 改為 `#` 註解——LOC 預算的合法出口之一
        # （`#` 不計 LOC），內容一字未改。理由見本檔上方能力閘那一段：那一段要花預算。
        denied = unattended_refusal(command)
        if denied:
            logger.error(denied)
            return EvalResult(success=False, output=denied, exit_code=-1)
        # R85 P7：可攜性診斷。刻意忽略回傳值——這道是**診斷**不是閘，不改控制流。
        portability_note(command)
        effective_timeout = timeout if timeout is not None else self._timeout
        logger.info("執行評估指令: %s (timeout=%ds)", command, effective_timeout)
        try:
            # 改 Popen + communicate（而非 subprocess.run）純為了逾時分支能拿到
            # Popen 物件呼叫 kill_process_tree()——run() 內部逾時時已自行 kill
            # 直接子行程並吞掉 handle，呼叫端無從回收孫行程。
            proc = subprocess.Popen(
                command, shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace",
                env=propagate_to_subprocess_env(dict(os.environ)),
                **_NEW_SESSION_KWARGS,
            )
            try:
                out, err = proc.communicate(timeout=effective_timeout)
            except subprocess.TimeoutExpired:
                kill_process_tree(proc)
                try:
                    proc.communicate(timeout=5)
                except Exception:
                    pass
                msg = f"評估指令逾時 ({effective_timeout}s): {command}"
                logger.error(msg)
                return EvalResult(success=False, output=msg, exit_code=-1)
            output = ((out or "") + (err or "")).strip()
            success = proc.returncode == 0
            if success:
                logger.info("評估通過 [exit=%d]", proc.returncode)
            else:
                logger.warning("評估失敗 [exit=%d]\n%s", proc.returncode, output[:800])
            return EvalResult(success=success, output=output, exit_code=proc.returncode)
        except Exception as exc:
            msg = f"評估指令異常: {exc}"
            logger.error(msg)
            return EvalResult(success=False, output=msg, exit_code=-1)
