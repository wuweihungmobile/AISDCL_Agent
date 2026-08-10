#!/usr/bin/env python
"""PreToolUse 守衛：擋下**會不可逆清掉工作樹內容**的 git 指令（R83）。

WHY（立案事實，不是假想）
------------------------
本輪一個 subagent 在**六包並行共用的同一個工作樹**上執行了

    git stash -q -u --keep-index

瞬間清空 16 個修改檔 ＋ 4 個未追蹤檔（含其他包當時正在寫的
`tools/lib/quota_meter.py`、`tools/tests/test_dev_start.py`、`tools/lib/schedule_backend.py`）。
它自己發現後 `git stash pop` 還原，前後 `git diff --stat` 逐字相同
（16 files / 1791 insertions / 215 deletions）⇒ **沒有偵測到資料遺失，但那是運氣不是設計**：
當時若有任何 agent 正在寫檔，pop 會衝突或直接覆蓋。

那一次的任務書上**已經寫著**「不要 git add / commit / push」。
⇒ **禁令沒涵蓋到的那個動詞，就是被踩的那個。** 這正是本 repo 判過兩次的形態
（`block_bash_on_windows.py` 的立案理由、`lint_powershell_command.py` 的立案理由）：
**純文件約束對「當下的模型」零攔阻力**——規則寫進 CLAUDE.md 的同一個回合仍會再犯，
因為 CLAUDE.md 由 session 開場載入，而「主動記得」正是決策負荷第一個擠掉的東西。
所以這一條必須是 hook，不是散文；而散文那一半（動詞清單會有缺口）本檔也不修，
本檔改成**列舉會毀掉工作樹的形態**，不是列舉「不准做的事」。

判準為何必須精準（另一半的設計約束）
------------------------------------
repo 原話：**擋到讓人無法工作的守衛會被整個關掉，而被關掉的守衛比沒有守衛更糟**——
它會讓人以為那一面有人在看。所以本檔對動詞**不做無差別封鎖**：

  · `git stash create` 是根 CLAUDE.md〈可重啟點四條件〉第 1 條**指定**的保全手法
    （「`git stash create` ＋ `git tag <輪次>-wip-preserved` 保全」）——擋掉它
    等於擋掉本 repo 自己的安全暫停 SOP，那會是這道鎖被拔掉的第一個理由。
  · `git reset`（mixed）與 `git reset --soft` 一個字節的工作樹內容都不動 ⇒ 放行。
  · 純切分支（`git checkout -b` / `git switch -c` / `git checkout <branch>`）⇒ 放行。
  · 所有唯讀查詢（`status`／`diff`／`log`／`show`／`stash list`／`stash show`…）⇒ 放行。

🔴 動詞的**危害射程**：為什麼不能「換一棵樹就整條放行」（R83 誤攔訂正）
----------------------------------------------------------------------
立案之後，兩名複審者各自在**自己 scratchpad 的拋棄式 worktree 內**跑
`git checkout -- <path>`（清掉零代價）而被本檔攔下。那是真誤擋，而誤擋正是這道鎖
被整個拔掉的路徑。但「偵測到不是共用工作樹就整條放行」是**錯的修法**——動詞的
危害射程不一樣，本回合在合成 repo（主樹 ＋ 一棵 linked worktree）逐條實測：

  · **只限當前工作樹**（`checkout -- <path>`／`restore`／`reset --hard`／`clean`／`switch -f`）：
    在 wt 內 `git checkout -- b.txt` 之後，wt 的未提交改動消失、**主樹的
    `MAIN_UNCOMMITTED` 原封不動倖存 1 筆**。⇒ 這一族換一棵樹確實就安全了。
  · **會溢出到共用 `.git`**（`stash` 全家）：在 wt 內跑事故那條
    `git stash -q -u --keep-index`，**主樹的 stash 深度 0→1、兩邊 `rev-parse refs/stash`
    是同一個 SHA**。⇒ `refs/stash` 是 repo 級不是工作樹級，**不論在哪一棵樹都必須擋**。
    這正是「只看樹就放行」會製造的新漏擋，而它漏掉的恰好是立案那一條指令。

所以判準是**動詞感知**的：先分類，再問樹。放寬只作用在「只限當前工作樹」那一族。

🔴 樹要從哪裡看出來？（一個會讓修法變成死分支的量測）
------------------------------------------------------
複審者建議的判準是 `realpath(git rev-parse --show-toplevel) != realpath($CLAUDE_PROJECT_DIR)`。
`--show-toplevel` 確有鑑別力（實測主樹／wt 回不同值；`--git-common-dir` 兩邊相同 ⇒ 不可用），
**但問題在「在哪裡跑它」**：本回合實測 PreToolUse payload 的欄位與 hook 自己的行程狀態——

    payload keys: agent_id / agent_type / cwd / effort / hook_event_name / permission_mode /
                  prompt_id / session_id / tool_input / tool_name / tool_use_id / transcript_path
    payload["cwd"] == os.getcwd() == $CLAUDE_PROJECT_DIR == <專案根>
    ——即使被檢查的那條指令自己是 `cd /private/tmp && pwd`，這三個值仍然全是專案根。

⇒ 拿 hook 自己的 cwd 去跑 `--show-toplevel`，答案**恆等於**專案根 ⇒ 判準恆假 ⇒
放寬永遠不觸發、誤擋一次都沒少，而程式碼看起來已經修好了。那正是本 repo 反覆判紅的
「鎖存在但沒有鑑別力」。**唯一真的帶著樹資訊的東西是指令字串自己**：段內的
`cd`／`pushd`／`Set-Location` 目標，與 `git -C <path>`。故本檔從字串推導「這次呼叫會落腳在
哪個目錄」，推導不出來就**不放寬**（fail-closed 到現行行為）。

放寬的四道前提（缺一即不放寬——每一條都對應一個實測到的漏擋）
--------------------------------------------------------------
1. 目錄**字面寫出來**且 `isdir()` 為真。理由是實測的：`cd /不存在; git clean -fdx`
   會因 `cd` 失敗而讓 `git` 落在**原來的 cwd（＝共用工作樹）**，用 `;` 串接時
   `&&` 的保護也不存在 ⇒ 目標不存在就必須當成「落在共用樹」。
2. 目標與專案根**互不包含**（雙向）。只判「不在專案根底下」會漏掉反向：
   `cd <專案根的上一層> && git clean -fdx` 會把整個專案目錄當未追蹤內容刪掉。
3. 指令內沒有 `--work-tree`／`--git-dir`／`--namespace`。實測：在 wt 內
   `git --git-dir=<主樹/.git> --work-tree=<主樹> checkout -- b.txt` rc=0，
   主樹的改動當場消失 ⇒ 這兩個選項能把危害導回任意樹，git 自己不會攔。
4. 指令內沒有子殼／群組／反引號／`popd`。`(cd /wt); git clean -fdx` 的 `cd` 作用域在
   `)` 就結束了，順序掃描會把後面那條誤判成落在 `/wt`——方向是**放行共用工作樹**。

`git -C` 是**反向**也要成立的那一半：`cd` 到別處不代表安全。實測 cwd=`/tmp`（完全在
lab 之外）時 `git -C <主樹> checkout -- b.txt` rc=0、主樹改動消失 ⇒ `-C` 必須被當成
這次呼叫的落腳目錄（於是它會判回「共用工作樹」而擋下），不是被忽略。

不需要另立判準的那一個（git 自己就守住了）
------------------------------------------
「在 wt 內用絕對路徑指主樹的檔」實測 rc=**128**、逐字
`fatal: <path>: '<path>' is outside repository at '<wt>'`，主樹的 `MAIN_AGAIN` 倖存 ⇒
pathspec 逃出當前工作樹這條路由 git 自己關掉。本檔因此**不**另加 pathspec 包含性判準
（多一條判準就多一族假紅），代價是這條事實由 git 的行為擔保、不由本檔擔保。

`--staged` 的取捨（刻意的、不是漏看）
------------------------------------
`git restore --staged <path>`（且未同時帶 `--worktree`／`-W`）**只動 index**，
工作樹的檔案內容原封不動 ⇒ **放行**。本檔守的危害類是「工作樹內容被不可逆清掉」，
而 unstage 掉的東西還完整躺在檔案裡。代價誠實寫在這裡：它確實會丟掉「哪些 hunk 已暫存」
這個狀態，`--keep-index` 那種精細操作會被打斷——但那不是本檔守的東西，把它一起擋
就是拿一筆會天天發生的誤擋，去換一個沒有資料遺失的情境。
`git restore --staged --worktree <path>` 兩者同時帶時工作樹會被覆寫 ⇒ **擋**。

行為契約
--------
· `tool_name` 不在 `OWN_TOOLS`（`Bash`／`PowerShell`）→ exit 0。
  射程不得擴大：matcher 若被改寬，守衛自己必須認得工具名（同 `block_bash_on_windows.py`
  的第二道限縮）。
· 命中任一形態 → exit 2 阻斷，stderr 一次列出**全部**命中項（不早退——早退會遮蔽
  後面檢查的訊號，而遮蔽的方向是「看起來變乾淨」）。
· payload 解析不出工具名／指令 → **exit 1（出聲但不阻斷）**，不是 exit 2。理由同
  `lint_powershell_command.py`：Bash（mac）／PowerShell（Windows）是這台機器上**唯一的
  shell 載具**，對一份根本讀不出內容的 payload 硬擋它，等於用一個讀不懂的輸入換掉整個
  工作面；而「送壞 payload 繞過守衛」在這裡不是真實威脅面——payload 由 Claude Code 產生，
  不由被守的一方撰寫。真正要防的是**守衛靜默失效**，exit 1 已經滿足（不阻斷但出聲）。
  這條「rc==2 才必須配窄 matcher」的對應關係由
  `tools/tests/test_check_hooks_liveness.py::degraded_payload_verdict` 機械釘住；
  本檔即使走 rc=1，matcher 仍取 `Bash|PowerShell`＝**恰好等於自己的射程**，零附帶面。
· 任何非預期例外 → exit 0（fail-open）。`.claude/settings.json` description 記載過的 P0：
  hook 誤觸 PreToolUse deny 會把**所有**工具硬鎖死，守衛自身絕不可成為那種故障源。

🔴 為何**不**加平台閘（鐵律三的自問：「這在另一個平台是什麼值？」）
------------------------------------------------------------------
姊妹檔 `block_bash_on_windows.py` 第一件事是 `os.name != 'nt' → exit 0`，因為它守的
規則本身只在 Windows 成立。本檔相反：**`git stash` 在 mac 上清掉的檔案，和在 Windows 上
清掉的一模一樣**，而立案的那起事故就發生在 macOS。無條件把姊妹檔的平台閘抄過來，
會讓這道鎖在事故現場那個平台上一行都不跑——那是 `DEF-101-766` 的鏡像版本
（單平台判準不可無條件外推，**兩個方向都不可以**）。故本檔不看平台。

兩個逃生口（刻意是兩個層級，且刻意**不與既有變數共用**）
--------------------------------------------------------
1. 環境變數 `AUTOSDD_GIT_GUARD_OFF` 有設 → 整支 no-op。
   🔴 **刻意不共用** `AUTOSDD_CONTEXT_GUARD_OFF`／`AUTOSDD_SENTINEL_OFF`：repo 明文
   「共用一個會讓『我只是想暫時別被擋』順手把別的保護一起關掉，而那件事沒有人會注意到」。
   🔴 這個出口**模型碰不到**，是刻意的不對稱：hook 是 `claude` 行程的子行程，讀的是
   **它自己的** `os.environ`；在 Bash 工具裡寫 `AUTOSDD_GIT_GUARD_OFF=1 git stash`
   只會影響那一條 `git` 的環境，對 hook 行程無效。要真的關掉，人必須在啟動 `claude`
   之前設好、或改 `.claude/settings.json` 的 `env`（那是一次看得見的檔案異動）。
2. 行內豁免 `# git-guard-ok: <WHY>`（住在**真註解**裡，理由必填）。體例對齊
   `lint_powershell_command.py` 的 `# ps-lint-ok:`，標記字樣刻意不同——共用一個標記
   會讓「為了避開 lint 而寫的豁免」順手把毀滅性 git 一起放行。
   正當用途：舵手要走 CLAUDE.md 的安全暫停 SOP 而需要一個本檔擋下的形態
   （例如事故後用 `git stash pop` 把東西**還原**回來）、或刻意重現缺陷／寫探針。
   🔴 已知弱點，誠實寫在這裡：**一個無人看管的模型回合可以自己寫出這行豁免。**
   出口仍然留著，因為沒有出口的窄守衛會被整個拔掉（repo 判例）；但補上一道邊界——
   `AUTOSDD_UNATTENDED` 有設（＝被排程叫起來、沒有人在看的那種回合）時，
   行內豁免**無效**，同 `lint_powershell_command.py` 對授權邊界的處置。

誠實劃界（本檔擋不到什麼——寫在這裡，因為讀到這支 hook 的人才是會誤以為它完整的人）
--------------------------------------------------------------------------------
· **不經 shell 的路徑**：Python `subprocess.run(["git", "stash"])`、MCP git 工具、
  用 `Write`／`Edit` 工具直接覆寫檔案或改 `.git/`。本檔只看 shell **指令字串**。
· **放寬只認「字面寫出來的目錄」**：`cd "$WT" && git checkout -- x` 裡的 `"$WT"` 會被
  `mask_inert()` 抹成空白（本檔看不到殼變數的值）⇒ 推導不出目錄 ⇒ **仍然擋**。
  同理，靠**上一次** Bash 呼叫留下的持久 cwd（主 agent 的殼會保留 `cd`）落在拋棄式
  worktree、然後只寫裸 `git checkout -- x` 的形態也仍然擋——payload 的 `cwd` 實測是專案根，
  本檔看不到那個持久狀態。兩者都是 fail-closed 方向；要放寬就把目錄寫出來
  （`cd <絕對路徑> && …` 或 `git -C <絕對路徑> …`），或用行內豁免。
· **`stash` 在真正無關的第三方 repo 內也會被擋**（例如自己在 scratchpad `git init` 出來的
  合成 repo）。技術上可鑑別——`git rev-parse --git-common-dir` 在共用 repo 的 linked
  worktree 內指回共用 `.git`、在無關 repo 內指自己（本回合實測），但那要在推導出的目錄裡
  起一支 `git` 子行程，而換到的只是一個罕見情境，行內豁免已經覆蓋它。取「不為罕見情境
  在阻斷路徑上加子行程」那一邊，代價誠實寫在這裡。
· **執行檔路徑被引號包住**時（`& '<含空白的安裝路徑>/git.exe' stash` 這種寫法）：
  引號區段會被 `mask_inert()` 抹掉 ⇒ 那個 `git` token 消失 ⇒ 漏擋。這是「遮蔽以避免
  誤擋」的必然代價，方向與姊妹檔 `_EXE_HEAD` 相同。
  （此處刻意寫成佔位符而不是某台機器上的真實磁碟機路徑：本檔會被 commit，寫死的
    路徑對其他 checkout 一律是錯的，且 `tools/tests/test_platform_neutral_paths.py`
    會逐行掃描並判紅——姊妹檔 `block_bash_on_windows.py` 因同一條規則已訂正過一次。）
· **別名／函式**：`alias gst='git stash'` 之後只寫 `gst`——判準看不到定義。
· **PowerShell 的反引號行接續**（`` git ` ``↵`` stash ``）：bash 的「反斜線＋換行」已折回
  （見 `_LINE_CONT_RE`），反引號那一種**刻意沒折**——理由與代價寫在該常數旁邊：
  一起折會把 bash 側 `` X=`git rev-parse HEAD` `` 的下一行併進同一段，而每段只取第一次
  git 呼叫 ⇒ 會把**已驗平台**原本擋得住的形態換成漏擋。Windows 側因此在這一點上有缺口。
· **heredoc 內容**：`bash <<'EOF' … EOF` 裡的 git 指令**會**執行，但本檔把 heredoc
  當資料遮掉（因為 `python - <<'PY' … PY` 這種寫探針的正當用法遠遠更常見，不遮就是
  一整類誤擋）。取的是「寧可漏擋、不要誤擋」那一邊。
· `git rm`／`git branch -D`／`git push --force`／`git filter-branch`：**不在射程內**。
  它們毀的不是「未提交的工作樹內容」，另案；把射程一次撐大是誤擋的來源。
"""

from __future__ import annotations

import os
import re
import sys
from typing import NamedTuple

# payload 讀取住共用層 `tools/lib/platform_utils.py`（R81／SUB-S1-04 的既有紀律，本檔
# R83 收尾補上）。**長出第二個家的唯一入口就是自己碰 stdin**——本檔第一版正是那樣寫的，
# 被 `tools/tests/test_pre_commit_dispatcher_sigpipe.py::TestHookPayloadSingleHome` 判紅。
# 該紀律的實證：此前 7 支 hook 各帶一份手抄本，實測已漂移成 3 種行為，其中 3 支在頂層
# 非 object 的合法 JSON（`[1,2,3]`／`null`）上 rc=1 AttributeError ⇒ 阻斷級守衛的判定
# 根本沒產出。
# 🔴 與本檔 fail-open 契約不衝突：共用層不可達時退化成回 `{}`，正好走下面既有的
# 「讀不出 tool_name → rc=1 出聲不阻斷」分支；模組層不會爆掉，也不留第二份 JSON 解析。
# 形態逐字對齊姊妹檔 `lint_powershell_command.py`（同一個 shim、同一個 except 語意）。
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "tools", "lib"))
try:
    from platform_utils import read_hook_payload  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001 — 共用層不可達＝退化，不是崩潰（fail-open 是 P0）
    def read_hook_payload() -> dict:  # type: ignore[misc]
        return {}

# 🔴 自己的 stdout／stderr 強制 UTF-8（DEF-101-789）。缺這段時：locale 表達不了 CJK
# （en-US ＝ cp1252）→ 整段指引變 `\uXXXX` 逃脫字面；locale 表達得了但非 UTF-8
# （zh-TW ＝ cp950）→ 讀者端拿到亂碼。兩種都讓「阻斷有了、教學沒了」，而一支只會擋、
# 不會教的守衛正是會被拔掉的那種。
#
# 🔴 **走共用層而不是自己就地 reconfigure 一次**（R83 收尾訂正）。本檔第一版抄了姊妹檔
# `block_bash_on_windows.py` 的就地形態，並在註解裡寫「不 import 的理由是 fail-open 契約
# 要求零外部相依，且 `tools/` 不在 hook 行程的 sys.path 上」——那個理由**在本檔已不成立**：
# 上面為了 `read_hook_payload` 已經把 `tools/lib` 掛上 sys.path，而 `init_utf8_streams()`
# 自己的契約就是「取不到 SSOT 時靜默不動」＝與 fail-open 同向。
# 而代價是真的：`tools/tests/test_platform_utils_dedup.py::TestR75StdioUtf8HasOneImplementation`
# 是一條 **shrink-only** 棘輪，本檔一加就讓 `.claude/hooks` 的複本數由凍結值往上跑並當場
# 判紅。那道棘輪守的正是本 repo 反覆判過的病——同一份知識住第 N 個家，而只有一個家會被改。
# ⇒ 正解是消費既有的公開名，不是把棘輪往上釘（往上釘＝放寬，本 repo 明文禁止）。
try:
    from platform_utils import init_utf8_streams  # type: ignore[import-not-found]

    init_utf8_streams()
except Exception:  # noqa: BLE001 — 共用層不可達＝退化，不是崩潰（模組層崩潰繞得過 main()）
    pass

#: 本守衛自己的射程。matcher 與這個集合**刻意相等**：mac 上實際送出 shell 指令的工具是
#: `Bash`（本機 60 份逐字稿 7,189 次 tool_use 實測：Bash 4,083 次），Windows 上鐵律一
#: 禁用 Bash ⇒ 指令一律走 `PowerShell`。圈一組這個 harness 不會發出的名字，會讓阻斷臂
#: 蓋好了卻永遠不觸發（R80 對 `Task` 的實測：8,106 次 tool_use 裡出現 0 次）。
OWN_TOOLS = frozenset({"Bash", "PowerShell"})

GUARD_OFF_ENV = "AUTOSDD_GIT_GUARD_OFF"
#: 與 `lint_powershell_command.py` 共用的「這一跑沒有人在看」訊號（由 planner 在
#: spawn `claude -p -r <sid>` 時注入）。共用是刻意的：它描述的是**回合的性質**，
#: 不是某一支守衛的開關；兩支守衛對同一個性質做出同方向的處置才是一致的。
UNATTENDED_ENV = "AUTOSDD_UNATTENDED"

#: 行內豁免：`# git-guard-ok: <WHY>`，WHY 必填（空白理由不算豁免，讓「刻意這樣寫」
#: 與「沒注意」分得開）。
_EXEMPT_RE = re.compile(r"#\s*git-guard-ok:\s*\S")

#: git 執行檔 token：允許路徑前綴（`/usr/bin/git`、`…\\git.exe`），但前綴必須以路徑
#: 分隔符結尾——否則 `legit`／`gitk` 這種字尾／字首巧合會被誤判。
_GIT_EXE_RE = re.compile(r"^(?:[^\s]*[\\/])?git(?:\.exe)?$", re.IGNORECASE)

#: git **全域**選項裡會吃掉下一個 token 的那幾個（`git -C <path> stash` 的 `<path>`
#: 不是子指令）。漏列的後果是把參數當成子指令 ⇒ 命中不了 ⇒ 漏擋，不是誤擋。
_GIT_GLOBAL_VALUE_OPTS = frozenset({
    "-C", "-c", "--git-dir", "--work-tree", "--namespace",
    "--exec-path", "--config-env", "--super-prefix",
})

#: 指令分隔符（在**遮蔽後**的結構面上切）。`(`／`)`／`` ` ``／`{`／`}` 一併切，
#: 讓 `$(git stash)`、`` `git stash` ``、`if …; then git stash; fi` 都各自成段。
_SEP_RE = re.compile(r"[;&|()\n{}`]+")

#: bash 的行接續（`\` ＋ 換行）是**行內空白**，不是語句邊界。不先折回去的話，
#: `git \`↵`  stash -q -u --keep-index` 會被 `_SEP_RE` 的 `\n` 切成「git」與「stash …」
#: 兩段而**整條漏擋**——立案的那條指令換個換行位置就繞過去了。這不是假想形態：
#: 本機 60 份逐字稿、4,087 條 shell 指令實測有 30 條用了行接續，其中 17 條是 git 指令。
#: 替換成**等長**空白，維持 `mask_inert()` 那條「遮蔽後位置一一對應」的契約。
#: 🔴 PowerShell 的接續符是**反引號＋換行**，本檔刻意不折：反引號在 bash 是命令替換的
#: 邊界（`` X=`git rev-parse HEAD` `` 的收尾正好落在行末），一起折會把下一行併進同一段，
#: 而每段只取第一次 git 呼叫 ⇒ 反而把 bash 側原本擋得住的形態變成漏擋。取「漏擋不誤擋、
#: 且不拿已驗平台的守備去換未驗平台」那一邊，代價列在模組 docstring 的誠實劃界。
_LINE_CONT_RE = re.compile(r"\\\r?\n")

#: `git stash` 的**允許清單**（其餘一律擋，含裸 `git stash`＝push）。用允許清單而不是
#: 禁止清單，是因為 stash 的子指令會增加，而「新增的那個是不是安全」的預設答案必須是否。
_STASH_SAFE = frozenset({"create", "list", "show"})

#: 危害**只限指令實際落腳的那一棵工作樹**的子指令 ⇒ 落在非共用工作樹時可以放寬。
#: 實測依據見模組 docstring：wt 內 `git checkout -- b.txt` 後主樹改動倖存。
_WORKTREE_SCOPED = frozenset({"checkout", "restore", "reset", "clean", "switch"})

#: 危害**溢出到共用 `.git`** 的子指令 ⇒ 不論在哪一棵樹都擋，放寬對它無效。
#: 實測依據：wt 內 `git stash` 讓主樹 stash 深度 0→1、兩邊 `refs/stash` 同一個 SHA。
#: 這一格就是「只看樹就放行」會漏掉的東西，而漏掉的正是立案那條指令。
_SHARED_SCOPED = frozenset({"stash"})

#: 會改變後續指令落腳目錄的動詞（bash 與 PowerShell 的聯集，大小寫不敏感）。
#: `popd`／`pop-location` 刻意**不在**這裡——它們是「放寬殺手」（見 `_RELAX_KILLER_RE`）：
#: 還原到哪一棵樹要看堆疊，猜錯的方向是放行共用工作樹。
_CD_VERBS = frozenset({"cd", "chdir", "pushd", "push-location", "set-location", "sl"})

#: 讓「換樹放行」整條失效的形態。四類各自對應一個實測到的漏擋（見模組 docstring 前提 3、4）：
#: 兩個能把危害導到任意樹的 git 全域選項、命名空間重導、以及子殼／群組／反引號／`popd`
#: 這些會讓「順序掃描 `cd`」推導出錯誤落腳目錄的結構。
_RELAX_KILLER_RE = re.compile(
    r"--work-tree|--git-dir|--namespace|\bpopd\b|\bpop-location\b|[(){}`]", re.IGNORECASE)


def mask_inert(text: str, *, keep_comments: bool = False) -> str:
    """把「不是可執行結構」的區段換成**等長**空白：引號字串、here-string／heredoc、註解。

    等長是關鍵：遮蔽後與原字串位置一一對應，切段與比對才不會位移（體例同
    `lint_powershell_command.mask_regions()`）。換行刻意保留，語句切割才不會被遮蔽改變。

    🔴 **刻意是一支「兩種殼的聯集」而不是兩支 dialect 專屬實作**：本檔同時服務 Bash
    （mac）與 PowerShell（Windows），而兩者的惰性區段大部分重疊（`'…'`／`"…"`／`#`）。
    寫成兩份會讓同一份知識住兩個家、只有一個家會被改；寫成聯集則多認幾種對方沒有的
    形態（bash 沒有 `@'…'@`、PowerShell 沒有 heredoc），代價是**極罕見的過度遮蔽**，
    方向是漏擋而非誤擋——與本檔在 heredoc 上的取捨同向。

    `keep_comments=True`：註解**原樣保留**、字串照樣遮。只有行內豁免偵測在用——它要的
    正是「這個標記住在真註解裡，不是住在一段被引號包起來的資料裡」。
    """
    out = list(text)
    n = len(text)
    i = 0

    def blank(start: int, end: int) -> None:
        for k in range(start, min(end, n)):
            if out[k] != "\n":
                out[k] = " "

    while i < n:
        ch = text[i]
        # PowerShell here-string：@'…'@ / @"…"@
        if ch == "@" and i + 1 < n and text[i + 1] in "'\"":
            quote = text[i + 1]
            end = text.find(quote + "@", i + 2)
            end = n if end < 0 else end + 2
            blank(i, end)
            i = end
            continue
        if ch in "'\"":
            j = i + 1
            while j < n:
                if text[j] == "\\" and ch == '"':
                    j += 2  # bash 的 "…" 內 \" 是逃脫；'…' 內沒有逃脫
                    continue
                if text[j] == ch:
                    break
                j += 1
            blank(i, min(j + 1, n))
            i = min(j + 1, n)
            continue
        # PowerShell 區塊註解 <# … #>
        if ch == "<" and text.startswith("<#", i):
            end = text.find("#>", i + 2)
            end = n if end < 0 else end + 2
            if not keep_comments:
                blank(i, end)
            i = end
            continue
        # bash heredoc：<<[-] [引號]WORD  → 遮到獨立一行的 WORD 為止
        if ch == "<" and text.startswith("<<", i) and not text.startswith("<<<", i):
            m = re.match(r"<<-?\s*(['\"]?)([A-Za-z_][\w.-]*)\1", text[i:])
            if m:
                word = m.group(2)
                body = text.find("\n", i)
                if body < 0:
                    blank(i, n)
                    i = n
                    continue
                end = n
                for line_m in re.finditer(r"^[ \t]*" + re.escape(word) + r"[ \t]*$",
                                          text[body:], re.MULTILINE):
                    end = body + line_m.end()
                    break
                blank(i, end)
                i = end
                continue
        # 註解：# 只在行首或前面是空白／分隔符時才是註解（`foo#bar` 不是）
        if ch == "#" and (i == 0 or text[i - 1] in " \t\n;&|(){}`"):
            end = text.find("\n", i)
            end = n if end < 0 else end
            if not keep_comments:
                blank(i, end)
            i = end
            continue
        i += 1
    return "".join(out)


def has_exemption(command: str) -> bool:
    """行內豁免是否存在（只認**住在真註解裡**的標記：註解留、字串遮）。"""
    return bool(_EXEMPT_RE.search(mask_inert(command, keep_comments=True)))


def _short_flags(token: str) -> set[str]:
    """`-fdx` → {'f','d','x'}；長選項與非旗標回空集合（大小寫敏感，`-B` ≠ `-b`）。"""
    return set(token[1:]) if re.fullmatch(r"-[A-Za-z]+", token) else set()


class GitCall(NamedTuple):
    """一次 git 呼叫：子指令、子指令之後的參數、以及**它會落腳在哪個目錄**。

    `target` 為 `None`＝從指令字串推導不出來 ⇒ 呼叫端一律不放寬（fail-closed）。
    """

    sub: str
    args: list[str]
    target: str | None


def _resolve_dir(base: str | None, token: str) -> str | None:
    """把 `cd <token>`／`git -C <token>` 的 token 解析成絕對目錄；解析不出回 `None`。

    `None` 的語意是「不知道」而不是「安全」——呼叫端對 `None` 一律不放寬。
    `cd -`（回上一個目錄）與被 `mask_inert()` 抹成空白的殼變數都落在這一格。
    """
    if not token or token.startswith("-"):
        return None
    token = os.path.expanduser(token)
    if os.path.isabs(token):
        return token
    return None if base is None else os.path.join(base, token)


def git_invocations(command: str, *, start_dir: str | None = None) -> list[GitCall]:
    """從指令字串抽出每一次 git 呼叫，回 `GitCall`。

    刻意**掃描每一個 token 位置**去找 git 執行檔，而不是只看每段的第一個 token：
    `sudo git stash`／`FOO=1 git stash`／`time git stash`／`xargs git stash` 都是真實
    寫法，只認段首會全部漏掉。代價是 `man git stash` 這種把 git 當**資料**的裸寫法會
    被誤判——實測 repo 存量為 0 筆（引號／管線兩種常見寫法都不會命中），故取這一邊。

    落腳目錄由**順序掃描**得出：段是照字面順序走的，段首是切目錄動詞就更新當前目錄，
    之後的 git 呼叫繼承它；該次呼叫自己的 `git -C <path>` 再覆蓋一次（實測 `-C` 會把
    危害導回它指的樹，cwd 在別處也一樣 ⇒ 它必須贏過 `cd`）。子殼會讓這個順序假設失效，
    那一族由 `_RELAX_KILLER_RE` 整條關掉放寬，不在這裡處理。
    """
    found: list[GitCall] = []
    masked = _LINE_CONT_RE.sub(lambda m: " " * len(m.group(0)), mask_inert(command))
    cur = start_dir
    for segment in _SEP_RE.split(masked):
        tokens = segment.split()
        if not tokens:
            continue
        if tokens[0].lower() in _CD_VERBS:
            cur = _resolve_dir(cur, tokens[1] if len(tokens) > 1 else "")
            continue  # 切目錄段不會同時是 git 段——分隔符已把它們切開
        for idx, token in enumerate(tokens):
            if not _GIT_EXE_RE.match(token):
                continue
            args = tokens[idx + 1:]
            j = 0
            target = cur
            while j < len(args) and args[j].startswith("-"):
                if args[j] in _GIT_GLOBAL_VALUE_OPTS:
                    if args[j] == "-C" and j + 1 < len(args):
                        target = _resolve_dir(target, args[j + 1])
                    j += 2
                else:
                    j += 1
            if j >= len(args):
                break  # 裸 `git`／只有全域選項——沒有子指令，不是本檔的射程
            found.append(GitCall(args[j].lower(), args[j + 1:], target))
            break  # 一段裡取第一次 git 呼叫即可（分隔符已把多次呼叫切開）
    return found


def relaxation_blockers(command: str) -> list[str]:
    """回**讓「換樹放行」失效**的形態（空 list＝沒有阻礙）。每一類都對應一個實測漏擋。"""
    masked = _LINE_CONT_RE.sub(lambda m: " " * len(m.group(0)), mask_inert(command))
    return sorted({m.group(0).lower() for m in _RELAX_KILLER_RE.finditer(masked)})


def _dir_prefix(path: str) -> str:
    """回「用來判包含關係」的目錄前綴（末端恰好一個分隔符）。

    存在理由是一個實測到的漏擋，不是整潔：直接寫 `path + os.sep` 在 `path` 已是
    檔案系統根（`"/"`）時得到 `"//"`，而**沒有任何路徑以 `"//"` 開頭** ⇒ 包含判準
    在那一格恆假。`rstrip` 先去掉既有的末端分隔符再補一個，根與非根走同一條路。
    """
    return path.rstrip(os.sep) + os.sep


def is_foreign_tree(path: str | None) -> bool:
    """`path` 是不是一棵「不是共用工作樹、也不含共用工作樹」的既存目錄。

    四道前提的實作（理由與實測見模組 docstring）：字面推導得出、`isdir` 為真、
    與專案根**互不包含**（雙向）。任何解析失敗一律回 `False`＝不放寬。
    """
    if not path:
        return False
    try:
        root = os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
        target = os.path.realpath(path)
        if not os.path.isdir(target):
            # `cd /不存在; git clean -fdx` ⇒ cd 失敗、git 落在原本的 cwd（共用工作樹）。
            return False
        # 🔴 前綴一律用 `_dir_prefix()` 造，不可寫 `p + os.sep`（獨立驗證輪實測的漏擋）：
        # 檔案系統根的 `"/" + "/"` ＝ `"//"`，沒有任何路徑以它開頭 ⇒ 反向包含判準對
        # `target == "/"` **恆假** ⇒ `cd / && git clean -fdx` 被放行（實測 rc=0，
        # 而前提 ② 明文說「與專案根互不包含（雙向）」⇒ 那是判準自陳與實作不符，
        # 屬本 repo 反覆判紅的「鎖存在但那一格沒有鑑別力」）。`cd /Users …` 那一級
        # 原本就擋得住，所以只有根這一格漏，也只有實測才看得見。
        if target == root or target.startswith(_dir_prefix(root)):
            return False  # 專案根本身，或開在 repo 內的 linked worktree ⇒ 保守擋
        return not root.startswith(_dir_prefix(target))  # 反向包含：clean 會把專案整包刪掉
    except Exception:  # noqa: BLE001 — 判不出就不放寬，同 `_looks_like_worktree_path`
        return False


def _looks_like_worktree_path(token: str, base: str | None = None) -> bool:
    """`git checkout <token>` 的 token 是不是工作樹裡真的存在的檔案／目錄。

    這是**加在規格之外的一層**：`git checkout <path>`（不帶 `--`）與 `git checkout <branch>`
    在字面上分不開，而前者是最常見的毀滅形態之一（`git checkout .` 尤其）。用「工作樹裡
    存在同名檔案」當判準，是因為分支名與現存路徑同名在實務上罕見（真同名時 git 自己也會
    喊 ambiguous）。解析不出／任何 OSError 一律回 False（＝放行），誤擋成本高於漏擋。
    """
    if not token or token.startswith("-"):
        return False
    try:
        root = base or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        return os.path.exists(os.path.join(root, token)) or os.path.exists(token)
    except Exception:  # noqa: BLE001 — 見 docstring：解析不出就放行
        return False


def _checkout_hit(args: list[str], target: str | None = None) -> str | None:
    flags = {a for a in args if a.startswith("-")}
    shorts: set[str] = set()
    for a in args:
        shorts |= _short_flags(a)
    if flags & {"--force", "--discard-changes"} or "f" in shorts:
        return "git checkout -f／--force／--discard-changes（強制切換會丟掉未提交的修改）"
    if "--" in args and args.index("--") + 1 < len(args):
        return "git checkout … -- <path>（把工作樹的檔案還原成 treeish 的內容，改動直接消失）"
    # 🔴 建分支旗標一出現，後面那個位置參數就是**分支名**不是路徑 ⇒ 路徑啟發式必須關掉。
    # 實測的誤擋：`git checkout -b docs`（repo 內真的有 `docs/` 目錄）會被判成路徑還原。
    # 這是普查抽樣時抓到的，不是想像——語料裡 `git checkout -b <name>` 是常見寫法。
    if flags & {"--orphan", "--detach", "--track"} or shorts & {"b", "B", "t"}:
        return None
    positional = [a for a in args if not a.startswith("-")]
    if positional and _looks_like_worktree_path(positional[0], target):
        return (f"git checkout {positional[0]}（工作樹中存在同名檔案／目錄 ⇒ 這是**路徑**"
                "還原不是切分支，改動直接消失）")
    return None


def _restore_hit(args: list[str], target: str | None = None) -> str | None:
    shorts: set[str] = set()
    for a in args:
        shorts |= _short_flags(a)
    staged = "--staged" in args or "S" in shorts
    worktree = "--worktree" in args or "W" in shorts
    if staged and not worktree:
        return None  # 只動 index，工作樹內容原封不動——取捨理由見模組 docstring
    return "git restore（預設 --worktree：把工作樹的檔案還原，未提交的改動直接消失）"


def _stash_hit(args: list[str], target: str | None = None) -> str | None:
    if {"-h", "--help"} & set(args):
        return None
    sub = next((a for a in args if not a.startswith("-")), "")
    if sub.lower() in _STASH_SAFE:
        return None
    verb = sub or "(裸 stash＝push)"
    return (f"git stash {verb}（把整個工作樹的改動搬走／搬回；在**多包並行共用工作樹**上"
            "這一下會清掉別人正在寫的檔案——R83 實測 16 個修改檔 + 4 個未追蹤檔瞬間消失）")


def _clean_hit(args: list[str], target: str | None = None) -> str | None:
    shorts: set[str] = set()
    for a in args:
        shorts |= _short_flags(a)
    if "--dry-run" in args or "n" in shorts:
        return None  # -n／--dry-run 只印不刪
    return "git clean（直接刪除未追蹤檔案，且不進 stash、不進 reflog ⇒ 沒有還原路徑）"


def _switch_hit(args: list[str], target: str | None = None) -> str | None:
    flags = {a for a in args if a.startswith("-")}
    shorts: set[str] = set()
    for a in args:
        shorts |= _short_flags(a)
    if flags & {"--force", "--discard-changes"} or "f" in shorts:
        return "git switch -f／--force／--discard-changes（強制切換會丟掉未提交的修改）"
    return None


def _reset_hit(args: list[str], target: str | None = None) -> str | None:
    hit = {"--hard", "--merge", "--keep"} & set(args)
    if not hit:
        return None  # 預設 mixed 與 --soft 都不動工作樹內容
    return (f"git reset {sorted(hit)[0]}（重寫工作樹內容；"
            "`git reset` 預設的 mixed 與 --soft 不會，所以本檔只擋這三個）")


_DISPATCH = {
    "stash": _stash_hit,
    "checkout": _checkout_hit,
    "restore": _restore_hit,
    "reset": _reset_hit,
    "clean": _clean_hit,
    "switch": _switch_hit,
}


_SPILL_NOTE = (
    "\n     ↳ **換一棵工作樹不會讓它變安全**：`refs/stash` 是 repo 級的。實測——在 linked "
    "worktree 內 stash，主樹的 stash 深度 0→1、兩邊 `rev-parse refs/stash` 是同一個 SHA。")
_BLOCKER_NOTE = (
    "\n     ↳ 這條指令**看起來**落在共用工作樹之外，但同時出現了 {} ⇒ 落腳目錄推導不可信，"
    "本檔不放寬（理由與實測見 hook 模組 docstring〈放寬的四道前提〉）。")


def destructive_git_hits(command: str, *, start_dir: str | None = None) -> list[str]:
    """回**全部**命中理由（不早退：早退會遮蔽後面的訊號，方向是「看起來變乾淨」）。

    `start_dir`＝這條指令開跑時的 cwd（production 由 payload 的 `cwd` 提供）。給 `None`
    時完全不放寬，那是直接呼叫本函式的 fail-closed 預設。

    放寬只作用在 `_WORKTREE_SCOPED` 那一族，且四道前提全過才放；`_SHARED_SCOPED`
    （stash 全家）不論在哪一棵樹都擋——實測依據見模組 docstring。
    """
    hits: list[str] = []
    blockers = relaxation_blockers(command)
    for call in git_invocations(command, start_dir=start_dir):
        handler = _DISPATCH.get(call.sub)
        if handler is None:
            continue
        hit = handler(call.args, call.target)
        if not hit:
            continue
        if call.sub in _SHARED_SCOPED:
            hits.append(hit + _SPILL_NOTE)
            continue
        if call.sub in _WORKTREE_SCOPED and is_foreign_tree(call.target):
            if not blockers:
                continue  # 危害只限那一棵樹，而那棵樹既不是、也不含共用工作樹 ⇒ 放行
            hit += _BLOCKER_NOTE.format("／".join(f"`{b}`" for b in blockers))
        hits.append(hit)
    return hits


_HEADER = (
    "🔴 這條指令會**不可逆地清掉工作樹內容**，已擋下（R83 立案：一個 subagent 在六包並行"
    "共用的工作樹上跑 `git stash`，16 個修改檔 + 4 個未追蹤檔瞬間消失；當時任務書寫的是"
    "「不要 git add / commit / push」——**禁令沒涵蓋到的那個動詞，就是被踩的那個**）。\n"
    "  本次命中：\n"
)
_FOOTER = (
    "\n"
    "  改用不會毀掉別人工作的做法：\n"
    "   · 要保全現況 → `git stash create` ＋ `git tag <輪次>-wip-preserved`\n"
    "     （根 CLAUDE.md〈可重啟點四條件〉第 1 條指定的手法，本守衛**不擋**它——\n"
    "       它只產一個 commit 物件，工作樹一個字節都不動）\n"
    "   · 要試改／要歸因 → 把**你自己的**檔案複製到 scratchpad 再改，別動共用工作樹\n"
    "   · 要看差異 → `git diff` / `git status` / `git stash list` / `git stash show`（全部放行）\n"
    "   · 真的必須做 → 停下來問舵手。共用工作樹上的破壞性動作不是可以自己決定的事。\n"
    "\n"
    "  🔴 如果你操作的是**自己在 scratchpad 建的臨時樹**（不是共用工作樹），那是正當用途，\n"
    "     而且對「危害只限當前工作樹」那一族（`checkout -- <path>`／`restore`／`reset --hard`／\n"
    "     `clean`／`switch -f`）本守衛**會放行**——但你必須把目錄**字面寫出來**，本守衛只看\n"
    "     指令字串（payload 的 `cwd` 實測恆為專案根，猜不出你 `cd` 去了哪）：\n"
    "        cd <臨時樹絕對路徑> && git checkout -- <path>\n"
    "        git -C <臨時樹絕對路徑> restore <path>\n"
    "     殼變數（`cd \"$WT\"`）看不到值、目錄不存在、或指令裡有 `--work-tree`／`--git-dir`／\n"
    "     子殼括號時一律不放寬（`cd /不存在; git clean -fdx` 會落在共用工作樹上）。\n"
    "  🔴 `git stash` 是例外，**任何一棵樹都擋**：`refs/stash` 跨 worktree 共用（實測同一個\n"
    "     SHA、主樹堆疊 0→1）⇒ 換樹不會讓它變安全。那一族請用行內豁免並寫明理由。\n"
    "\n"
    "  真的確定要這樣寫？在指令內加行內豁免 `# git-guard-ok: <理由>`（理由必填）。\n"
)
_UNATTENDED_NOTE = (
    "\n"
    f"  🔴 這一跑是**被排程叫起來的無人看管回合**（環境變數 {UNATTENDED_ENV} 有設），\n"
    "     行內豁免 `# git-guard-ok:` 對本回合**無效**——出口是給人的，不是給\n"
    "     一個沒有人在看的模型回合自己寫給自己的。請把改動留在工作樹、把狀態寫進\n"
    "     任務書，然後停下來讓人回來收。\n"
)


def main() -> int:
    try:
        if os.environ.get(GUARD_OFF_ENV):
            return 0  # 人的逃生口；模型改不到 hook 行程的環境（見模組 docstring）

        # 🔴 payload 讀取的**唯一家**是 `tools/lib/platform_utils.read_hook_payload()`。
        # 本檔第一版自己碰 `sys.stdin`，被
        # `tools/tests/test_pre_commit_dispatcher_sigpipe.py::TestHookPayloadSingleHome`
        # 當場判紅——那道鎖的立論逐字是「長出第二個家的**唯一入口**就是自己碰 stdin」，
        # 而它擋的正是本 repo 反覆判過的病（同一份知識住兩個家、只有一個家被改）。
        # `read_hook_payload()` 的契約與本檔需要的退化語意逐字相同：壞 JSON／空 stdin／
        # 非 dict 一律回 `{}`，於是下面「讀不出 tool_name ⇒ rc=1 出聲不阻斷」那一支
        # 完全不變。
        payload = read_hook_payload()

        tool = str(payload.get("tool_name") or "")
        if not tool:
            sys.stderr.write(
                "[block_destructive_git] payload 讀不出 tool_name（壞 JSON／空 stdin）⇒ "
                "本次不檢查。刻意不阻斷：硬擋唯一的 shell 載具，代價遠大於漏掉一次檢查；"
                "但也不靜默——守衛失效必須看得見。\n")
            return 1
        if tool not in OWN_TOOLS:
            return 0  # 射程不得擴大（matcher 被改寬時的第二道限縮）

        tool_input = payload.get("tool_input")
        command = tool_input.get("command") if isinstance(tool_input, dict) else None
        if not isinstance(command, str) or not command.strip():
            sys.stderr.write(
                f"[block_destructive_git] {tool} payload 沒有 command 字串 ⇒ 本次不檢查。\n")
            return 1

        # payload 的 `cwd` 只是**起點**：實測它恆為專案根（即使指令自己 `cd` 去別處），
        # 所以真正的落腳目錄一律由指令字串推導（見模組 docstring）。傳它進去是為了讓
        # 相對路徑的 `cd` 有基準——而那個基準指向共用工作樹，方向正是 fail-closed。
        start_dir = payload.get("cwd")
        hits = destructive_git_hits(
            command, start_dir=start_dir if isinstance(start_dir, str) else None)
        if not hits:
            return 0

        unattended = bool(os.environ.get(UNATTENDED_ENV))
        # 🔴 順序本身就是判準的一部分：無人看管時**先於**行內豁免判定，因為那個回合
        # 可以自己寫出豁免註解（同 lint_powershell_command.py 對授權邊界的處置）。
        if has_exemption(command) and not unattended:
            return 0

        sys.stderr.write(_HEADER + "".join(f"   · {h}\n" for h in hits)
                         + (_UNATTENDED_NOTE if unattended else _FOOTER))
        return 2
    except Exception:  # noqa: BLE001 — fail-open 是刻意的，見模組 docstring 的 P0
        return 0


if __name__ == "__main__":
    sys.exit(main())
