#!/usr/bin/env python
"""PreToolUse 守衛：擋下**會不可逆清掉工作樹內容**的 git 指令（R83）。

WHY（立案事實，不是假想；敘事全文已搬
`docs/06_quality/CrossPlatform_R95_GovWrite_Evidence.md` §史料搬遷）
------------------------
R83：一個 subagent 在**六包並行共用的工作樹**上跑 `git stash -q -u --keep-index`，
16 個修改檔＋4 個未追蹤檔瞬間消失；當時任務書**已寫著**「不要 git add / commit / push」
⇒ **禁令沒涵蓋到的那個動詞，就是被踩的那個**，而純文件約束對「當下的模型」零攔阻力
（本 repo 已判過兩次）。所以這一條必須是 hook 不是散文，且本檔**列舉會毀掉工作樹的
形態**，不是列舉「不准做的事」。

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

🔴 動詞的**危害射程**（R83 誤攔訂正；合成 repo 逐條實測全文見證據檔 §史料搬遷）
----------------------------------------------------------------------
誤擋是這道鎖被整個拔掉的路徑，但「不是共用樹就整條放行」是**錯的修法**——
`checkout -- <path>`／`restore`／`reset --hard`／`clean`／`switch -f` 危害**只限落腳的
那棵樹**（wt 內跑、主樹改動倖存），`stash` 全家**溢出到共用 `.git`**（`refs/stash`
是 repo 級，兩邊同一個 SHA ⇒ 不論在哪一棵樹都必須擋）。所以判準是**動詞感知**的：
先分類，再問樹；放寬只作用在前一族。

🔴 樹要從哪裡看出來？payload 的 `cwd`、hook 的 `os.getcwd()`、`$CLAUDE_PROJECT_DIR`
實測**三者恆等於專案根**（量測全文見證據檔 §史料搬遷）⇒ 在 hook 行程裡問 git 恆得
專案根、判準恆假。**唯一真的帶著樹資訊的是指令字串自己**：段內的 `cd`／`pushd`／
`Set-Location` 目標，與 `git -C <path>`；推導不出來就**不放寬**（fail-closed）。

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

`git -C` 是**反向**也要成立的那一半（`cd` 到別處不代表安全）：實測 `-C <主樹>` 會把
危害導回主樹 ⇒ 它必須被當成落腳目錄。pathspec 逃出當前工作樹則由 git 自己擋
（rc=128 fatal），本檔刻意不另加判準——兩者實測逐字見證據檔 §史料搬遷。

`--staged` 的取捨（刻意的、不是漏看；代價全文見證據檔 §史料搬遷）：
`git restore --staged <path>` 未同時帶 `--worktree`／`-W` 時**只動 index**，工作樹
內容原封不動 ⇒ 放行；兩者同時帶時工作樹會被覆寫 ⇒ 擋。

行為契約
--------
· `tool_name` 不在 `OWN_TOOLS ∪ GOV_TOOLS` → exit 0。射程不得擴大：matcher 若被
  改寬，守衛自己必須認得工具名（同 `block_bash_on_windows.py` 的第二道限縮）。
· 命中任一形態 → exit 2 阻斷，stderr 一次列出**全部**命中項（不早退——早退會遮蔽
  後面檢查的訊號，而遮蔽的方向是「看起來變乾淨」）。
· payload 解析不出工具名／指令 → **exit 1（出聲但不阻斷）**，不是 exit 2：shell
  載具是唯一工作面，硬擋一份讀不出內容的 payload 等於換掉整個工作面；真正要防的是
  **守衛靜默失效**，exit 1 已滿足（理由全文見證據檔 §史料搬遷）。「rc==2 才必須配窄
  matcher」由 `tools/tests/test_check_hooks_liveness.py::degraded_payload_verdict`
  機械釘住；本檔 matcher＝`OWN_TOOLS ∪ GOV_TOOLS`（R95 起）＝**恰好等於自己的射程**。
· 任何非預期例外 → exit 0（fail-open）。`.claude/settings.json` description 記載過的 P0：
  hook 誤觸 PreToolUse deny 會把**所有**工具硬鎖死，守衛自身絕不可成為那種故障源。

🔴 為何**不**加平台閘（鐵律三自問；論證全文見證據檔 §史料搬遷）：`git stash` 在
mac 清掉的檔案與 Windows 一模一樣，而事故就發生在 macOS——照抄姊妹檔的平台閘等於
在事故現場關掉它（`DEF-101-766` 的鏡像：單平台判準兩個方向都不可無條件外推）。

兩個逃生口（刻意是兩個層級，且刻意**不與既有變數共用**）
--------------------------------------------------------
1. 環境變數 `AUTOSDD_GIT_GUARD_OFF` 有設 → git／等待兩族 no-op（R95 起治理面唯讀
   另有自己的開關 `AUTOSDD_GOVWRITE_GUARD_OFF`，本開關刻意管不到它——見 R95 節）。
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
· **不經 shell 的路徑**：MCP git 工具、`Write`／`Edit` 直接覆寫檔案、以及**寫在 `.py`
  檔裡**的 `subprocess.run(["git","stash"])`（工具面只看得到 `python foo.py`）。指令字串裡
  **直接寫出來**的那一種已在射程內（見下方 R84 記錄）；攔不到的改由 `stash_ref_sentinel()` 偵測。
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
  誤擋」的必然代價，方向與姊妹檔 `_EXE_HEAD` 相同（為何寫佔位符：原文＝證據檔 §4.8）。
· **別名／函式**：`alias gst='git stash'` 之後只寫 `gst`——判準看不到定義。
· **PowerShell 的反引號行接續**（`` git ` ``↵`` stash ``）：bash 的「反斜線＋換行」已折回
  （見 `_LINE_CONT_RE`），反引號那一種**刻意沒折**——理由與代價寫在該常數旁邊：
  一起折會把 bash 側 `` X=`git rev-parse HEAD` `` 的下一行併進同一段，而每段只取第一次
  git 呼叫 ⇒ 會把**已驗平台**原本擋得住的形態換成漏擋。Windows 側因此在這一點上有缺口。
· **heredoc 內容**：R84 起依**擁有者**分流——擁有者＝`<<` 左側**最近的那個非旗標 token**
  （由右往左找；`ssh host bash <<'EOF'` 的擁有者是 bash）。餵給殼的 body 是可執行結構、
  照常判；餵給別的直譯器的（`python - <<'PY'`）仍當資料遮掉（那是寫探針的標準寫法，
  不遮就是一整類誤擋），其中的 Python 層 git 呼叫由 `argv_git_fragments()` 接住。
  🔴 擁有者**不可用「整行有沒有出現殼的名字」判**：`cd /tmp/sh && python - <<'PY'` 實測
  會被那種寫法誤擋（SD-06）。
· **`-c` 載具**（`sh|bash|zsh|ksh|dash|pwsh|powershell -c`／`-Command`／`eval`）的**引號
  operand** R84 起是獨立平面（SD-01，先前整族漏擋）。仍漏：operand 沒加引號、operand 是
  變數（`sh -c "$CMD"`），且該平面**一律不套用換樹放寬**（看不到落在哪棵樹 ⇒ fail-closed）。
· **argv 的執行檔不是字面**：`[GIT,"stash"]`／`["git","-C",wt,"stash"]`／`$(which git) stash`
  **結構上擋不住**；`sudo`／`env`／`VAR=val` 這類**字面**前綴 R84 起會跳過（SD-08）。
· `git rm`／`branch -D`／`push --force`／`filter-branch`／**`git apply -R`**：**不在射程內**
  （前四者毀的不是未提交的工作樹內容；`apply -R` 是把剛套上的 patch 退回去的正當手法而且
  可逆 ⇒ 擋它是製造誤擋）。R84 起**在**射程內的新成員：`git worktree remove --force`
  （不帶 `--force` 時 git 自己會因樹是髒的而拒絕）與 `git checkout-index -f`。
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
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

# 「這一跑沒有人在看」訊號 ＋ 授權邊界判準 ＋ 兩族的訊息，唯一的家＝
# `tools/lib/unattended_authz.py`。R85／P12 前它們散在兩支 hook 內（訊號名兩份、
# 「豁免在本回合無效」的補述兩份、判準只有 Windows 那一份有）——而 mac 上那一份
# 結構上跑不到（matcher `PowerShell` ＋ `os.name != 'nt'` 兩道都對不上），
# 於是無人看管代理在 mac 可自由 commit／push（本輪 P3 實測）。
# 🔴 **刻意不包 try/except**：理由與 `context_budget_guard.py` 對 `quota_limits` 的
# 處置逐字同構——授權邊界不是能力提供者，給它 fallback stub 等於在共用層不可達時
# 靜默放行。硬 import 失敗＝traceback ＋ 非 0/2 的 rc＝出聲但不阻斷（看得見的失效）。
from unattended_authz import (  # type: ignore[import-not-found] # noqa: E402
    UNATTENDED_ENV, authz_header, authz_hits, waiver_void_note)

# 🔴 P0-1：拋棄式 worktree 根目錄的正規化與包含判斷搬到 `tools/lib/
# worktree_paths.py`（理由同上——`guardrail_cli<=750` 零餘裕，且它與 `is_foreign_tree()`
# 同族，抽出去才不會第二次長出自己的正規化邏輯）。同 `unattended_authz` 刻意不包
# try/except：這是安全判準，import 失敗要 traceback 而不是靜默退化成放行。
from worktree_paths import is_under_disposable_worktree  # type: ignore[import-not-found] # noqa: E402

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

# ══════════════════════════════════════════════════════════════════════════════
# 🔴 R84：上面〈誠實劃界〉那兩條缺口的**第一個真實命中**（不是假想，是本輪的事故）
# ══════════════════════════════════════════════════════════════════════════════
# 2026-08-12 00:21:13，一個 agent 送出的 Bash 指令裡有一行沒刪掉的草稿殘留：
#
#     cd <repo>; .venv/bin/python - <<'PY'
#     import sys, pathlib, subprocess, tempfile, os
#     ...
#     head = subprocess.run(["git","stash"],capture_output=True)  # NO
#     PY
#
# 它清空了 R84 全輪工作樹（**91 檔、+4658/-508**），已用 `git stash apply` 全額還原
# （`stash@{0}` ＝ `7b7ce22` 留作備份）。`capture_output=True` 把 `Saved working
# directory…` 吃掉、前面的 print 照常回傳 ⇒ **rc=0、無 stderr、看起來完全正常**；
# 送出它的 agent 事後誠實自陳「我全程只跑唯讀指令」——**它自己看不見**。
#
# 差分實測（對本檔餵真 payload，exit 2＝擋、0＝放行）：原凶逐字 **0**、裸 `git stash` 2、
# heredoc 內以 `os` 模組的 `system()` 起 `git stash` **0**、無 heredoc 的
# `subprocess.run(["git","stash"])` **0**、
# 純 shell `git stash push -u` 2 ⇒ 兩條缺口（heredoc body 被當資料遮掉 ＋ 不經殼的
# Python 呼叫）**各自單獨就足以放行**，所以只補一條沒有用。
#
# 修法刻意**不開第二個家**：不新寫一套子指令判準，而是把「Python 層的 git 呼叫」
# **正規化成一段 shell 文字**（`argv_git_fragments()`），再餵回既有的 `git_invocations()`
# ⇒ `_DISPATCH`／`_STASH_SAFE`／`-C` 落腳推導全部原封不動共用。同一份語意只有一個家。
#
# 🔴 為什麼要求「引號字面 ＋ 逗號」而不是看到 `git` 就抓：判準的精準度就是這道鎖的命。
#   · 序列面（`["git","stash"]`）要求**至少一組逗號分隔的引號字面**——殼陣列 `("a" "b")`
#     沒有逗號、`print("git stash")` 沒有第二個字面，兩者都不會命中。
#   · 單字串面（`os` 模組的 `system('git stash')`）**必須有具名的呼叫者**（`os` 的
#     `system`／`popen`、`subprocess.*`／`Popen`）。🔴 這兩個名字在本註解裡刻意
#     **不寫成帶點的完整形態**：`test_the_hook_spawns_no_subprocess` 對本檔的**程式區**
#     做子字串掃描（禁用清單見該測試，含 subprocess 的 import 形態、那兩個 os 呼叫、
#     以及問 git 根目錄的那個旗標），它分不出
#     「真的呼叫」與「註解裡提到」——寫回帶點形態會當場讓那道鎖轉紅。少了這個錨，
#     `python -c "print('git clean -fd')"`
#     會當場變成假紅——那條**本檔既有的放行測試就在守它**（`test_quoted_text_is_not_a_command`）。
#: Python 層 git 呼叫的兩種形態（掃**未經 `mask_inert()` 的原始字串**——heredoc body 正是
#: 被遮掉的那一段，遮完再掃就永遠是空的）。
#: 🔴 R84／SD-02：序列的**最後一個元素可有可無**（`(?:…)?` 那一格）。少了它，**一個尾逗號
#: 就足以整條漏擋**，而 `black` 的多行格式**預設就會產生尾逗號** ⇒ 原凶只要被格式化成多行
#: 就自動逃掉。實測逐字：`x=([ "git","stash" ])` → `'git stash'`；多一個逗號 → `''`（exit 0）。
_ARGV_SEQ_RE = re.compile(
    r"""[\[(]\s*(?:(['"])[^'"]*\1\s*,\s*)+(?:(['"])[^'"]*\2\s*)?[\])]"""
    r"""|(?:os\.(?:system|popen)|subprocess\.\w+|Popen)\s*\(\s*(['"])\s*(?:[^\s'"\\/]*[\\/])?git(?:\.exe)?\s[^'"]*\3""")
_ARGV_LIT_RE = re.compile(r"""(['"])([^'"]*)\1""")

#: 殼的名字只有**一個家**：heredoc 擁有者判定與 `-c` 載具判定都從這裡長出來（R73
#: `Find-GitBash` 的判例：同一份知識住兩個家、只有一個家會被改）。
_SHELLS = r"sh|bash|zsh|ksh|dash|pwsh|powershell"
#: 一個 **token** 是不是殼執行檔（允許路徑前綴與 `.exe`，但整個 token 必須就是它）。
#: 🔴 R84／SD-06：這裡是 `match` 對**單一 token**，不是 `search` 對整行——後者正是實測到的
#: 誤擋：`cd /tmp/sh && python - <<'PY' … PY` → BLOCK，同一條去掉 `/tmp/sh` → allow，
#: 路徑裡一個 `/sh` 就把 python 的 heredoc 判成殼結構。而**誤擋是這道鎖被整個關掉的路徑**。
_SHELL_EXE_RE = re.compile(rf"^(?:[^\s]*[\\/])?(?:{_SHELLS})(?:\.exe)?$", re.IGNORECASE)
#: 🔴 R84／SD-01：`-c` 載具＝**另一個獨立的指令平面**。`sh -c '<毀滅性 git>'` 的 operand
#: 被 `mask_inert()` 當引號資料遮掉 ⇒ 實測 exit 0，而**同一件事**寫成 `bash <<'EOF'` 是
#: exit 2——一擋一放，只因換了載具。成因與 heredoc 完全同構，故修法也同構：把 operand
#: 當獨立平面遞迴餵回 `git_invocations()`，**不新開第二套子指令判準**。
#: `eval "…"` 同族（裸 `eval git stash` 本來就擋得住——`git_invocations()` 掃每個 token 位置）。
_CARRIER_RE = re.compile(
    rf"""(?:(?<![-\w.])(?:[^\s'"]*[\\/])?(?:{_SHELLS})(?:\.exe)?(?:\s+-[\w-]+)*\s+-(?:[a-z]*c|command)(?![\w-])"""
    rf"""|(?<![-\w./])eval)\s+(?P<q>['"])(?P<op>.*?)(?P=q)""", re.IGNORECASE | re.DOTALL)
#: 🔴 R84／SD-08：argv 序列的**執行檔不一定在第 0 格**（`["sudo","git","stash"]`／
#: `["env","GIT_DIR=x","git",…]`）⇒ 往後找第一個非前綴 token。誠實劃界：元素是變數
#: （`[GIT,"stash"]`／`["git","-C",wt,"stash"]`）或 `$(which git) stash` **結構上擋不住**
#: ——本檔只看得到字面，那一族改由 `stash_ref_sentinel()` 事後偵測。
_EXEC_PREFIX = frozenset({"sudo", "env", "nice", "time", "timeout", "nohup", "exec", "command"})
#: 真的會改動 `refs/stash` 的 stash 子指令（`""`＝裸 stash＝push）。`create`／`apply`／
#: `list`／`show` 一個字節都不動那個 ref ⇒ 不該點亮哨兵的 ack 位元（R84／SD-04）。
_STASH_REF_WRITERS = frozenset({"", "push", "save", "pop", "drop", "clear"})


# 回傳值餵給既有的 `git_invocations()`＝零重寫共用同一份子指令語意。刻意**不**把結果
# substitute 回原字串：那樣它會落在 heredoc body 內，接著被 `mask_inert()` 整段遮掉
# （本輪實測過的順序陷阱），而分離成獨立平面就不受遮蔽影響。落腳目錄一律 `None`
# （看不見 `cwd=` kwarg）⇒ 換樹放寬對這一面不生效，方向是 fail-closed。
def argv_git_fragments(command: str) -> str:
    """把指令字串裡**不經殼直接看得到的 git 呼叫**正規化成一段 shell 文字（`;` 分隔）。"""
    out: list[str] = []
    for m in _ARGV_SEQ_RE.finditer(command):
        lits = [t for _q, t in _ARGV_LIT_RE.findall(m.group(0))]
        # 🔴 SD-08：執行檔不一定在第 0 格（`sudo`／`env`／`VAR=val`／`timeout 30` 前綴），
        # 往後找。純數字那一格是 `timeout`／`nice` 的**值**，不跳過就會停在它身上。
        while len(lits) > 1 and (lits[0].lower() in _EXEC_PREFIX or "=" in lits[0]
                                 or lits[0].isdigit()):
            lits = lits[1:]
        # 🔴 序列面必須是**真的 argv**：第一個字面就是 git 執行檔。缺這一條時，
        # 「一串命令字串的 tuple」（`("git checkout -p", "git restore -p")` 這種探針表）
        # 會被整串攤平成一段假的指令 ⇒ 全語料實測 3 筆假紅，全部由本條收掉。
        # 單字面面（`os` 模組的 `system('git stash')`）不受此限——它的錨是呼叫者名稱。
        if len(lits) > 1 and not _GIT_EXE_RE.match(lits[0]):
            continue
        out.append(" ".join(lits))
    # 🔴 SD-01：殼 `-c`／`eval` 的 operand 也是這種「殼文字看不到、但真的會執行」的平面。
    # operand 自己可能再包一層 ⇒ 遞迴；它是原字串的**真子字串**，所以一定會停。
    out += [s for m in _CARRIER_RE.finditer(command)
            for s in (m.group("op"), argv_git_fragments(m.group("op"))) if s]
    return ";".join(out)


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
                # 🔴 R84：body 是不是可執行結構，由 heredoc 的**擁有者**決定（見檔頭 R84
                # 記錄）。餵給殼 ⇒ 只遮 `<<WORD` 本身、停在 `body` 讓主迴圈照常往下遮
                # body 內的引號與註解；餵給別的直譯器 ⇒ 整段當資料遮掉（維持既有行為）。
                # 🔴 SD-06：擁有者＝`<<` 左側**最近的那個非旗標 token**（由右往左找），
                # 不是「整行有沒有出現殼的名字」——後者實測會被 `cd /tmp/sh`、
                # `grep -rn bash docs/` 這種與 heredoc 無關的字面騙到而**誤擋**。
                # 由右往左也順帶正確處理 `ssh host bash <<EOF`（擁有者是 bash 不是 ssh）
                # 與 `sudo bash <<EOF`／`env FOO=1 bash <<EOF`（前綴自動被跳過）。
                exe = next((t for t in reversed(text[:i].rsplit("\n", 1)[-1].split())
                            if not t.startswith("-")), "")
                stop = body if _SHELL_EXE_RE.match(exe) else end
                blank(i, stop)
                i = stop
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


# 🔴 抽出來的理由是 **LOC 預算**，不是整潔：本檔住在 `guardrail_cli` tier，R84 收窄
# 前餘裕只剩兩位數，而下面四個 handler 各自抄了一份逐字相同的三行迴圈。純提取、
# 零行為變更（`_short_flags` 的語意原封不動），既有的 handler 測試就是它的回歸鎖。
def _all_shorts(args: list[str]) -> set[str]:
    return {c for a in args for c in _short_flags(a)}


# `target` 為 `None`＝從指令字串推導不出來 ⇒ 呼叫端一律不放寬（fail-closed）。
# （docstring 改註解的理由同 `_all_shorts`：本檔的 LOC 預算把 docstring 也算成程式行。）
class GitCall(NamedTuple):
    """一次 git 呼叫：子指令、子指令之後的參數、以及**它會落腳在哪個目錄**。"""

    sub: str
    args: list[str]
    target: str | None


# `None` 的語意是「不知道」而不是「安全」——呼叫端對 `None` 一律不放寬。`cd -`（回上一個
# 目錄）與被 `mask_inert()` 抹成空白的殼變數都落在這一格。（docstring 改註解的理由同上。）
def _resolve_dir(base: str | None, token: str) -> str | None:
    """把 `cd <token>`／`git -C <token>` 的 token 解析成絕對目錄；解析不出回 `None`。"""
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
    # 🔴 R85／SD-B3：`unquote_exe_paths()` 必須在 `mask_inert()` **之前**跑——鐵律二明訂的
    # `& '<絕對路徑>\git.exe' <sub>` 寫法整段會被遮蔽抹掉（實測：帶引號的絕對路徑寫法
    # 回空 list，同一條去掉引號則正常命中）。它長度逐字元不變，下面的
    # 等長不變式與位置比對照舊成立。（docstring 改註解的理由同 `_all_shorts`：本檔的
    # `guardrail_cli` LOC 預算把 docstring 也算成程式行。）
    masked = _LINE_CONT_RE.sub(lambda m: " " * len(m.group(0)),
                               mask_inert(unquote_exe_paths(command)))
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


# 存在理由是一個實測到的漏擋，不是整潔：直接寫 `path + os.sep` 在 `path` 已是檔案系統根
# （`"/"`）時得到 `"//"`，而**沒有任何路徑以 `"//"` 開頭** ⇒ 包含判準在那一格恆假。
# `rstrip` 先去掉既有的末端分隔符再補一個，根與非根走同一條路。（docstring 改註解同上。）
def _dir_prefix(path: str) -> str:
    """回「用來判包含關係」的目錄前綴（末端恰好一個分隔符）。"""
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


# 這是**加在規格之外的一層**：`git checkout <path>`（不帶 `--`）與 `git checkout <branch>`
# 在字面上分不開，而前者是最常見的毀滅形態之一（`git checkout .` 尤其）。用「工作樹裡
# 存在同名檔案」當判準，是因為分支名與現存路徑同名在實務上罕見（真同名時 git 自己也會
# 喊 ambiguous）。解析不出／任何 OSError 一律回 False（＝放行），誤擋成本高於漏擋。
# （本段由 docstring 改成註解的理由與 `_all_shorts` 同一個：本檔的 `guardrail_cli` LOC
#  預算把 docstring 也算成程式行，而 R84 這批治本要在**不調高預算**的前提下塞進來。）
def _looks_like_worktree_path(token: str, base: str | None = None) -> bool:
    """`git checkout <token>` 的 token 是不是工作樹裡真的存在的檔案／目錄。"""
    if not token or token.startswith("-"):
        return False
    try:
        root = base or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        return os.path.exists(os.path.join(root, token)) or os.path.exists(token)
    except Exception:  # noqa: BLE001 — 見 docstring：解析不出就放行
        return False


def _checkout_hit(args: list[str], target: str | None = None) -> str | None:
    flags = {a for a in args if a.startswith("-")}
    shorts = _all_shorts(args)
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
    shorts = _all_shorts(args)
    if ("--staged" in args or "S" in shorts) and not ("--worktree" in args or "W" in shorts):
        return None  # 只動 index，工作樹內容原封不動——取捨理由見模組 docstring
    return "git restore（預設 --worktree：把工作樹的檔案還原，未提交的改動直接消失）"


def _stash_hit(args: list[str], target: str | None = None) -> str | None:
    sub = next((a for a in args if not a.startswith("-")), "")
    if {"-h", "--help"} & set(args) or sub.lower() in _STASH_SAFE:
        return None
    return (f"git stash {sub or '(裸 stash＝push)'}（把整個工作樹的改動搬走／搬回；在**多包"
            "並行共用工作樹**上這一下會清掉別人正在寫的檔案——R83 實測 16 個修改檔 + 4 個"
            "未追蹤檔瞬間消失）")


def _clean_hit(args: list[str], target: str | None = None) -> str | None:
    if "--dry-run" in args or "n" in _all_shorts(args):
        return None  # -n／--dry-run 只印不刪
    return "git clean（直接刪除未追蹤檔案，且不進 stash、不進 reflog ⇒ 沒有還原路徑）"


def _switch_hit(args: list[str], target: str | None = None) -> str | None:
    if not ({"--force", "--discard-changes"} & set(args) or "f" in _all_shorts(args)):
        return None
    return "git switch -f／--force／--discard-changes（強制切換會丟掉未提交的修改）"


# 🔴 R84／SD-07：`git worktree remove --force` 毀的正是「未提交的工作樹內容」（不帶
# `--force` 時 git 自己會因為樹是髒的而拒絕 ⇒ 那一半安全，本檔不擋）。它既不屬
# `_WORKTREE_SCOPED`（危害在**參數**指的那棵樹，不是指令落腳的那棵）也不屬
# `_SHARED_SCOPED`（不動 `refs/stash`）⇒ 兩個集合都不進，放寬寫在這個 handler 自己身上。
#
# 🔴 **放寬是量出來的，不是設計出來的**：本輪對逐字稿全語料（4,017 筆／去重 3,740 種）
# 新舊判準各跑一次，新增命中 6 種**全部**是這個動詞，而逐筆判讀 6/6 都是「拆掉自己的
# 拋棄式樹」（`.claude/worktrees/agent-*` 收工清理、scratchpad 沙盒 teardown、
# `/private/tmp/...` 測試樹）——**一筆事故形態都沒有**。無差別擋它就是拿一個從未發生的
# 危害，去換一個天天發生的誤擋，而 repo 已判過「誤擋是這道鎖被整個關掉的路徑」。
# ⇒ 判準改成問**被拆的是誰**：目標樹落在共用專案樹之外（`is_foreign_tree`，含「路徑不存在
# ⇒ 判不出來 ⇒ 不放寬」的 fail-closed）才放行；落在專案樹內（典型是**另一個 agent 還活著的**
# `.claude/worktrees/agent-*`）照擋。順帶一提 `git worktree remove` 結構上碰不到主工作樹
# （git 自己回 `fatal: … is a main working tree`）⇒ R83 立案那個形態它做不出來。
#: harness 自己的 agent 沙盒樹（`isolation: "worktree"` 建在這裡、收工就拆）。它住在專案
#: 根底下 ⇒ `is_foreign_tree()` 判它「不是外樹」而擋下，但那是**routine teardown**：全語料
#: 6 筆新增命中裡有 3 筆就是它。放行的代價誠實寫在這裡——拆掉一棵**還有 agent 活著**的沙盒
#: 樹會被放行；那個危害與 `rm -rf <該目錄>` 同級，而本檔本來就不守 `rm`。
#
# 🔴 P0-1：識別「這是不是拋棄式 worktree」的正規化與包含判斷已搬到
# `tools/lib/worktree_paths.py::is_under_disposable_worktree()`（理由與零 LOC 代價見
# 該模組檔頭）。R96 版在這裡自己寫的是**純字串包含**（`_DISPOSABLE_WT in normcase(victim)`），
# 不解析 `..`——`<repo>/.claude/worktrees/../../AutoClaude` 這種路徑 `realpath` 後其實落在
# 拋棄式樹**之外**（等於 `<repo>/AutoClaude`），卻因為字面上仍帶著 `.claude\worktrees\` 這段
# 子字串而被判定放行；同一招甚至能繞出 `<repo>/.claude/worktrees/../..`＝repo 根自己。
# 兩例當回合實測見 `tools/tests/test_worktree_paths.py` 與
# `test_block_destructive_git_r83.py::TestR84WorktreeRemoveForce
# .test_dotdot_traversal_disguised_as_disposable_worktree_is_blocked`。新函式比對前把
# `victim` 也 `realpath()`＋`normcase()`，改成**前綴**（不是子字串）比對，對齊
# `is_foreign_tree()` 的既有手法，`..` 穿越與大小寫／分隔符混用同時收斂。
# 混合分隔符／NTFS 大小寫不敏感的回歸鎖（**平台中性**，以 `ntpath` 顯式注入 Windows 語意，
# 所以 mac／Linux 上也真的走進這一格）＝`TestR84WorktreeRemoveForce
# .test_the_mixed_separator_shape_is_judged_on_every_platform` 與
# `…_the_windows_case_insensitive_shape_is_judged`。


def _worktree_hit(args: list[str], target: str | None = None) -> str | None:
    pos = [a for a in args if not a.startswith("-")]
    victim = _resolve_dir(target, pos[1] if len(pos) > 1 else "") or ""
    if pos[:1] != ["remove"] or not ("--force" in args or "f" in _all_shorts(args)) or \
            is_foreign_tree(victim) or is_under_disposable_worktree(victim):
        return None
    return ("git worktree remove --force（把整棵 linked worktree 連同裡面未提交的改動與"
            "未追蹤檔一起刪掉；不進 stash、不進 reflog ⇒ 沒有還原路徑）")


# 🔴 R84／SD-07 同族：`git checkout-index -f -a` 用 index 的內容強制覆寫工作樹。它是
# plumbing、實務上幾乎沒有人手寫（全語料實測 0 筆）⇒ 假紅面為零，故收；但也別把它
# 當成這一格的主力。**刻意不收的是 `git apply -R`**：那是「把剛套上的 patch 退回去」的
# 正當手法、而且可逆（再套一次就回來），擋它是在製造誤擋，方向與本檔的設計約束相反。
def _checkout_index_hit(args: list[str], target: str | None = None) -> str | None:
    if not ("--force" in args or "f" in _all_shorts(args)):
        return None
    return "git checkout-index -f（用 index 的內容強制覆寫工作樹檔案，未提交的改動直接消失）"


def _reset_hit(args: list[str], target: str | None = None) -> str | None:
    hit = {"--hard", "--merge", "--keep"} & set(args)   # 預設 mixed 與 --soft 不動工作樹
    return (f"git reset {sorted(hit)[0]}（重寫工作樹內容；"
            "`git reset` 預設的 mixed 與 --soft 不會，所以本檔只擋這三個）") if hit else None


_DISPATCH = {
    "stash": _stash_hit,
    "checkout": _checkout_hit,
    "restore": _restore_hit,
    "reset": _reset_hit,
    "clean": _clean_hit,
    "switch": _switch_hit,
    "worktree": _worktree_hit,
    "checkout-index": _checkout_index_hit,
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
    # 🔴 R84：兩個平面。① 殼文字本身；② Python 層 argv ＋ 殼 `-c`／`eval` 的 operand（見
    # `argv_git_fragments()`）。②**必須**是獨立平面而不是就地 substitute：原凶那條的
    # argv 住在 heredoc body 裡，就地取代之後會連同 body 一起被遮掉（實測 exit 仍為 0）。
    hidden = argv_git_fragments(command)
    # 🔴 放寬殺手也**必須**在 ② 上跑一次（SD-01 落地時自測抓到的洞）：`sh -c '(cd /wt);
    # git clean -fdx'` 的子殼括號住在引號裡，在 ① 的遮蔽面上是空白 ⇒ 只看 ① 會判成
    # 「這條落在 /wt」而放行，實際上 `)` 已經結束了 cd 的作用域、git 落在共用工作樹。
    blockers = relaxation_blockers(command) or relaxation_blockers(hidden)
    calls = git_invocations(command, start_dir=start_dir)
    calls += [c for c in git_invocations(hidden) if c not in calls]
    for call in calls:
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


# ══════════════════════════════════════════════════════════════════════════════
# 🔴 R84 偵測層：攔截器**結構上**接不到的那一半（本 repo「失效必須可偵測」紀律）
# ══════════════════════════════════════════════════════════════════════════════
# 上面每一道判準都只看得到**指令字串**。真正動了 `refs/stash` 卻不經過這裡的路至少四條：
# MCP git 工具（不是 Bash 呼叫）／別的 session（本行程看不到）／**寫在 `.py` 檔裡**的
# `subprocess.run(["git","stash"])`（工具面只看得到 `python foo.py`，argv 在檔案裡）／
# 別名與殼函式。這四條**不可能**靠加判準關掉 ⇒ 只能改成「事後一定看得見」。
#
# 判準刻意只看 `refs/stash` 這一個 ref：它**只會**因 stash push／pop／drop／clear 而變，
# 而那正好是本檔守的那一族。（一起看 `logs/HEAD` 是第一版的寫法，已否決——它每次
# `git commit` 都會變，那是天天發生的合法動作 ⇒ 常駐亮燈，而常駐全亮的燈等於沒有燈。）
#
# 🔴 假紅面為零的關鍵是那個 ack 位元：凡「上一次工具呼叫的指令字串裡出現過 stash」
# （不論被擋、被豁免、還是 `stash create` 這種放行形態），本次就不出聲——那一次變動
# **本守衛看見了**，不是隱形的路。只有「ref 變了、而上一次沒有任何 stash 經過」才報。
#
# 成本近零且平台中立：兩次讀檔＋一次寫檔，**不起子行程**（本檔的
# `test_the_hook_spawns_no_subprocess` 明文禁止；PreToolUse 每次工具呼叫都會跑）。
# 狀態檔住 `.git/`（不是 tempdir）⇒ 天生逐 repo 隔離、不會被別的 checkout 汙染，
# 而且 git 自己不追蹤它。誠實劃界：`.git` 是**檔案**的 linked worktree 內寫入會失敗 ⇒
# 該情境下哨兵靜默不作用（回 `None`），這是刻意的 fail-open，同本檔的 P0 契約。


# 🔴 R84／SD-04：ack 位元**不可以用子字串判**。修訂前 `main()` 傳的是 `"stash" in command`
# ⇒ 上一條指令只要「提到」stash（`grep -rn stash docs/`、`ls .git/autosdd_stash_sentinel`、
# 甚至本檔自己的檔名出現在指令裡）就把 ack 點亮，下一次**真的** drift 便靜默；而它同一次
# 已把 state 改寫成新 SHA ⇒ 之後再也不會報＝**永久吞掉**，不是延後。修法是重用
# `git_invocations()`（含 argv／`-c` 兩個隱藏平面）而不是字串比對，並且只認真的會改動
# `refs/stash` 的那幾個子指令。
def stash_writer_seen(command: str) -> bool:
    """這條指令裡真的有一次**會改動 `refs/stash`** 的 git 呼叫嗎？"""
    calls = git_invocations(command) + git_invocations(argv_git_fragments(command))
    return any(c.sub == "stash" and next((a for a in c.args if not a.startswith("-")), "").lower()
               in _STASH_REF_WRITERS for c in calls)


def stash_ref_sentinel(root: str | None = None, ack: bool = False) -> str | None:
    """`refs/stash` 相對**上一次工具呼叫**有沒有在本守衛看不見的地方被動過。"""
    git = Path(root or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()) / ".git"
    ref, state = git / "refs" / "stash", git / "autosdd_stash_sentinel"
    now = ref.read_text(encoding="utf-8").strip() if ref.is_file() else ""
    head, _, seen = (state.read_text(encoding="utf-8") if state.is_file() else "").partition(" ")
    try:
        state.write_text(f"{now} {int(ack)}", encoding="utf-8")
    except OSError:
        return None
    if not head or now == head or seen.strip() == "1":
        return None
    return (f"[block_destructive_git] 🔴 refs/stash {head[:12]} → {now[:12] or '(空)'}，而上一次"
            "工具呼叫裡沒有任何 stash 經過本守衛 ⇒ 有一條它攔不到的路動了 stash（MCP git 工具／"
            "別的 session／`.py` 檔內的 subprocess／別名）。"
            "立刻查 `git stash list` 與 `git status`。\n")


# ══════════════════════════════════════════════════════════════════════════════
# 鐵律六（R84／`DEF-200-044`）：**等待／確認的機制自己靜默壞掉 ⇒ 無做工空轉**
# ══════════════════════════════════════════════════════════════════════════════
# WHY 這一族住在**這一支** hook 而不是新開一支
# --------------------------------------------
# 本檔已經是「PreToolUse × 讀 Bash／PowerShell 指令字串 × 平台中立」那個觀測面上
# 唯一的住戶（見 `OWN_TOOLS` 與模組 docstring）。鐵律六要判的兩種形態**只住在指令
# 字串裡**，需要的輸入與本檔逐字相同 ⇒ 另開一支等於把同一個 payload 解析、同一份
# `mask_inert()`、同一套逃生口語意各再抄一份，而那正是本 repo 反覆判紅的
# 「同一份知識住兩個家、只有一個家會被改」（R73 `Find-GitBash` 的形態）。
# 代價誠實寫在這裡：本檔的檔名說的是 git，而它現在也守一族與 git 無關的東西。
# 取「共用觀測面、不長第二個家」那一邊，並以本節標題把射程寫明。
#
# 立案事實（R83 收輪實帳，不是假想）
# ----------------------------------
# `nohup <cmd> > log 2>&1 &` 讓工作**脫離 harness 的完成追蹤**：實測外層 rc=0、0 秒
# 就返回，而那個工作同一刻還活著 ⇒ harness 的完成通知講的是外層那個殼。實帳
# **00:39 → 01:27 共 48 分鐘零工作**，靠掌舵者來問才發現。
# 另一半：`until ! pgrep -f 'X'` 兩支並行時**兄弟互匹**（各自命中對方的 `sh` 與
# `pgrep`）⇒ `until ! …` 永不退出。`man pgrep` 只排除**自己與祖先**，所以它在單支
# 試跑下永遠是綠的——這正是「失敗表徵與正常進行完全相同」。
#
# 🔴 判準② **不得**建在 `mask_inert()` 之上（獨立驗證輪的實測，SD-01）
# --------------------------------------------------------------------
# 判準②要判的東西——自我否定字元類 `run_root[_]unittests`——**正好住在被遮掉的那個
# 引號字串裡**。直觀實作（把 operand 也從遮蔽字串上取）會讓「壞形態」與「已修好的
# 形態」在遮蔽面上完全同形 ⇒ 兩種都放行。實測逐字：
#     FAIL "until ! pgrep -f 'run_root_unittests'; do sleep 5; done" -> []
# ⇒ 本檔採**兩軌**：迴圈頭／`;`／`do`／`pgrep` 這些**結構**在遮蔽字串上定位（避免
# 命中引號內的假結構），operand 則以**同一 offset 從原字串取**（`mask_inert()` 明文
# 保證等長 ⇒ offset 一一對應）。
#
# 🔴 假紅普查的**量測面**（SD-02；R83 鐵律五那套「對全庫 tracked 檔普查」對本族是錯的）
# ------------------------------------------------------------------------------------
# 這兩種形態**不住在 repo 裡**——它們是模型當回合現寫、送進 Bash 工具的字串。實測：
# tracked 檔上的命中**全部落在描述它們的 `.md` 散文**（根 CLAUDE.md、Defect_Log），
# 而 hook 結構上讀不到 `.md` ⇒ 照 tracked-檔普查法會得到「全是假紅」的錯誤結論並
# 否決一個好判準。正確母體＝逐字稿裡真的送出過的 `tool_input.command`，
# 可重跑產物＝`tools/probe/shell_command_corpus.py`（同時也補上鐵律五缺的那一份）。

#: 判準①的 `wait` 豁免（**指令全域**，不只同一段）。SD-02 逐筆判讀出的唯一假陽性是
#: `nohup true; python … & BGPID=$!; wait $BGPID`——`wait` 與 `nohup` 段不同段，
#: 而它是**正確**形態（外層殼真的阻塞到工作做完）⇒ 豁免必須跨段成立。
_WAIT_RE = re.compile(r"(?<![\w./-])wait(?![\w.-])")
#: 判準①的標的動詞。`disown`／`setsid` 與 `nohup` 同族：都把子行程從「外層殼結束時
#: 會被追蹤到」的關係裡拆開。
_NOHUP_RE = re.compile(r"(?<![\w./-])nohup(?![\w.-])")
_DETACH_RE = re.compile(r"(?<![\w./-])(?:disown|setsid)(?![\w.-])")
#: statement 邊界：**只切 `;` 與換行，刻意不切 `&`**——`&` 正是判準①要找的東西。
#: 不切段的後果是假陽性（`nohup foo; bar &` 被判成同一件事）；切 `&` 的後果是漏擋
#: （`nohup foo &` 自己被切成兩半）。
_STMT_SEP_RE = re.compile(r"[;\n]+")
#: 迴圈頭與 `pgrep`（判準②，在**遮蔽面**上定位）。
_LOOP_HEAD_RE = re.compile(r"(?<![\w.-])(?:until|while)(?![\w.-])")
_PGREP_RE = re.compile(r"(?<![\w./-])pgrep(?![\w.-])")
#: 條件的結束邊界：第一個 `;`／換行／`do`／`then`。`docker` 這種含 `do` 的字元不會命中
#: （右側 `\w` 邊界），引號內的 `do` 也不會（在遮蔽面上已是空白）。
_COND_END_RE = re.compile(r"[;\n]|(?<![\w.-])(?:do|then)(?![\w.-])")
#: `pgrep` 會**吃掉下一個 token** 的旗標（漏列 ⇒ 把旗標的值當 pattern ⇒ 誤判方向）。
_PGREP_VALUE_SHORT = frozenset("uUGPsgtd")
_PGREP_VALUE_LONG = frozenset({
    "--uid", "--euid", "--group", "--parent", "--session", "--pgroup",
    "--terminal", "--delimiter", "--ns", "--nslist", "--runstates",
})
#: 判準②的行內豁免。**刻意與 `# git-guard-ok:` 不同字樣**：共用一個標記會讓「為了
#: 放行一個等待形態而寫的豁免」順手把毀滅性 git 一起放行（同本檔既有的兩層逃生口論述）。
_WAITFORM_EXEMPT_RE = re.compile(r"#\s*waitform-ok:\s*\S")


def _fold(command: str) -> str:
    """遮蔽 ＋ 折回 bash 行接續，回**與原字串等長**的結構面（判準①②共用）。"""
    return _LINE_CONT_RE.sub(lambda m: " " * len(m.group(0)), mask_inert(command))


def _background_amps(segment: str) -> bool:
    """這一段裡有沒有**真的背景化**的 `&`（排除 `&&`／`2>&1`／`&>`／`|&`）。

    每一種排除都對應一個會製造假紅的真實寫法：`a && b`（邏輯與）、`cmd 2>&1`（重導，
    與背景毫無語意關係）、`cmd &> log`（bash 的合併重導）、`cmd |& next`（管線含 stderr）。
    """
    for i, ch in enumerate(segment):
        if ch != "&":
            continue
        if i + 1 < len(segment) and segment[i + 1] in "&>":
            continue                                   # `&&` / `&>`
        if i and segment[i - 1] in "&><|":
            continue                                   # `&&` 的後半 / `2>&1` / `|&`
        return True
    return False


# `tools/lib/shell_tokens.py` 的兩個原語，唯一的家在那裡（R84／C8 的減法：兩者都與
# 「毀滅性 git 判準」零交集）。形態與上面 `read_hook_payload` 那一格逐字相同（同一條
# sys.path、同一種 fail-open），退化方向都是**少擋**而不是憑殘缺資料誤擋：
#   · `shell_tokens`（判準②取 operand）不可達 ⇒ 切不出 token ⇒ 判準②不出手。
#   · `unquote_exe_paths`（R85／SD-B3，把引號包住的執行檔絕對路徑還原成 basename；
#     必須跑在 `mask_inert()` **之前**，否則遮蔽會把整段連 `git.exe` 一起抹掉）
#     不可達 ⇒ 恆等 ⇒ 退回 R85 之前的行為。這裡不必再蓋硬 import：`unattended_authz`
#     與它同目錄共用同一條 sys.path，真的不可達時那一行會先炸 ⇒ 姿態已是 fail-loud。
try:
    import shell_tokens as _st  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001 — 共用層不可達＝退化，不是崩潰（fail-open 是 P0）
    _st = None  # type: ignore[assignment]
_shell_tokens = getattr(_st, "shell_tokens", lambda text: [])
unquote_exe_paths = getattr(_st, "unquote_exe_paths", lambda text: text)


def _pgrep_full_operand(rest: str) -> str | None:
    """`pgrep` 之後的參數列 → 「`-f` 有帶時的那個 pattern」；否則 `None`。

    `None` 有兩種來源，兩者都刻意**不擋**：① 沒有 `-f`（那樣 pgrep 只比對**行程名**，
    兄弟的 `sh -c` 包裝與 `pgrep` 自己都不會命中 ⇒ 不是本判準的危害形態）；
    ② 有 `-f` 但 pattern 缺漏（那是 usage error，擋它換不到任何東西）。
    """
    toks = _shell_tokens(rest)
    full = False
    i = 0
    while i < len(toks):
        tok = toks[i]
        if tok.startswith("--"):
            if tok in ("--full",):
                full = True
            if tok in _PGREP_VALUE_LONG:
                i += 2
                continue
            i += 1
            continue
        if len(tok) > 1 and tok.startswith("-"):
            if "f" in tok[1:]:
                full = True
            if tok[-1] in _PGREP_VALUE_SHORT:
                i += 2
                continue
            i += 1
            continue
        return tok if full else None
    return None


def _self_negating(pattern: str) -> bool:
    """pattern 是否用了**字元類自我否定**（`run_root[_]unittests`／`[p]ython.*X`）。

    這是 CLAUDE.md 鐵律六 ✅ 那一格逐字指定的形態，也是本判準的**放行面**：
    只要 pattern 裡有一段非空的 `[…]`，這條指令的字面就不再匹配它自己（兄弟的
    `sh -c` 與 `pgrep` 自身都帶著原始字面）⇒ 鑑別力保住、死鎖消失。
    實測（本輪，同一 pattern 兩支並行）：自我否定版兩支皆 rc=1（零命中），
    對真標的仍 rc=0（命中 2 支）。
    """
    return bool(re.search(r"\[[^\]]+\]", pattern))


def waitform_hits(command: str, *, run_in_background: bool = False) -> list[str]:
    """鐵律六的命中理由（空 list＝通過）。**三條**判準，共用同一個遮蔽面。

    · ① `nohup`／`disown`／`setsid` 與背景 `&` 同一 statement
    · ② `until`／`while` 的**條件內**出現裸 `pgrep -f <非自我否定 pattern>`
    · ③ `run_in_background=True` 搭一個**自己就會立刻返回**的指令（背景 `&`／`disown`）
      — 本輪實測 payload 真的帶得到這個旗標（`tool_input.run_in_background: true`，
        前景呼叫則整個 key 不存在）⇒ 這一條不是靜態推論。

    🔴 `wait` 豁免（全指令任一處出現即成立）**只罩 ①③、不罩 ②**——`until ! pgrep …` 的
    死鎖與有沒有 `wait` 無關。這個不對稱是實作逐字的形狀（①③ 住在 `if not waited:` 內、
    ② 在它外面）。🔴 **本 docstring 是這一族「有幾條判準」的 SSOT**：實作住在這裡，而
    CLAUDE.md 鐵律六與缺陷帳本各自另有一份不同版本（QA-03：同一份知識三個家、三種內容）。
    """
    masked = _fold(command)
    hits: dict[str, None] = {}

    waited = bool(_WAIT_RE.search(masked))
    if not waited:
        for segment in _STMT_SEP_RE.split(masked):
            if not _background_amps(segment):
                continue
            if _NOHUP_RE.search(segment) or _DETACH_RE.search(segment):
                hits["nohup／disown／setsid ＋ 背景 `&`：這個工作**脫離 harness 的完成追蹤**"
                     "（實測外層 rc=0、0 秒返回，而工作同一刻還活著 ⇒ 完成通知講的是外層"
                     "那個殼）。R83 收輪實帳：00:39 → 01:27 共 48 分鐘零工作"] = None
            elif run_in_background:
                hits["`run_in_background: true` 搭一個自己就會立刻返回的指令（段內有背景 "
                     "`&`）：叫醒你的是**外層殼結束**的那一刻，而它 0 秒就結束 ⇒ 通知到達時"
                     "工作還在跑"] = None
        if run_in_background and _DETACH_RE.search(masked):
            hits["`run_in_background: true` 搭 `disown`／`setsid`：同上，外層殼與真正的"
                 "工作已經沒有父子關係 ⇒ harness 追蹤不到它結束"] = None

    for head in _LOOP_HEAD_RE.finditer(masked):
        start = head.end()
        stop = _COND_END_RE.search(masked, start)
        end = stop.start() if stop else len(masked)
        for pg in _PGREP_RE.finditer(masked, start, end):
            # 🔴 operand 從**原字串**同 offset 取（SD-01：遮蔽面上它是空白 ⇒ 好壞同形）
            operand = _pgrep_full_operand(command[pg.end():end])
            if operand is None or _self_negating(operand):
                continue
            hits[f"`{head.group(0)}` 的條件內用裸 `pgrep -f {operand}`：兩支並行時**兄弟"
                 f"互匹**（各自命中對方的 `sh` 與 `pgrep`）⇒ `until ! …` 永不退出。"
                 f"`man pgrep` 只排除**自己與祖先**，所以單支試跑永遠是綠的。"
                 f"改成字元類自我否定：`{operand[:1]}[{operand[1:2] or '_'}]{operand[2:]}` "
                 f"這種形態（只否定自己、不減損鑑別力）"] = None
    return list(hits)


def has_waitform_exemption(command: str) -> bool:
    """判準①②③的行內豁免（只認住在**真註解**裡的 `# waitform-ok: <理由>`）。"""
    return bool(_WAITFORM_EXEMPT_RE.search(mask_inert(command, keep_comments=True)))


_WAITFORM_HEADER = (
    "🔴 這條指令的**等待／確認機制自己會靜默壞掉**，已擋下（鐵律六／`DEF-200-044`）。\n"
    "  一句話的本體：**我用來等待／確認的那個機制自己壞掉，而失敗的表徵與「還在正常"
    "進行」完全相同。**\n"
    "  本次命中：\n"
)
_WAITFORM_FOOTER = (
    "\n"
    "  改用**有契約的**事件源（照鐵律六的 ✅ 那兩格）：\n"
    "   · `run_in_background: true` ＋ 一個**會阻塞到真的做完**的前景指令\n"
    "     （Bash 工具說明逐字：`it keeps running across turns and re-invokes you when it"
    " exits`\n"
    "       ⇒ 叫醒你的是那個行程結束的那一刻，所以它必須一直活到工作真的做完）\n"
    "   · 真的要自己輪詢 → 條件的比對面**不含自己**（字元類自我否定）：\n"
    "        until ! pgrep -f 'run_root[_]unittests'; do sleep 20; done\n"
    "   · 已經背景化、而你要等它 → 同段補 `wait`（本守衛對帶 `wait` 的指令整條放行）\n"
    "\n"
    "  🔴 只有「等額度 reset」與「等人介入」是合法的無事件源停等。其餘任何停等都必須有"
    "一個\n"
    "     會**主動叫醒你**的事件源；掛不掛得上，是派工前就要決定的事，不是事後補救。\n"
    "\n"
    "  真的確定要這樣寫？在指令內加行內豁免 `# waitform-ok: <理由>`（理由必填）。\n"
)
_WAITFORM_UNATTENDED_NOTE = waiver_void_note(
    "waitform-ok",
    "而這一族的代價在無人看管時最大：\n     沒有人會來問「它是不是空轉了 48 分鐘」。")


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
_UNATTENDED_NOTE = waiver_void_note(
    "git-guard-ok",
    "出口是給人的，不是給\n     一個沒有人在看的模型回合自己寫給自己的。請把改動留在"
    "工作樹、把狀態寫進\n     任務書，然後停下來讓人回來收。")


# ══════════════════════════════════════════════════════════════════════════════
# 🔴 R95／Pkg-B：PRD §15.5 紅線 10「治理檔在無人值守下唯讀」的機械物
# ══════════════════════════════════════════════════════════════════════════════
# 立案（R87 實帳，不是假想）：一個 agent 為繞過 halt 改了取數層 ⇒ 13 agent 全滅、
# 1.3M tokens 零產出——「不得以模型判斷推翻機械守衛」此前只有散文，零機械物。
# WHY 住本檔而不是新開一支 hook：本檔已是「PreToolUse × 平台中立」觀測面上唯一的
# 住戶（同上方鐵律六那一族的入住理由——另開一支等於把 payload 解析、UTF-8 stdio、
# fail-open 契約與逃生口語意各再抄一份，且 hook 檔數與 hook_wiring 普查面都要多付
# 一格）。設計取捨與實測 rc 逐字＝docs/06_quality/CrossPlatform_R95_GovWrite_Evidence.md。
# 判準刻意窄（誤擋是守衛被整個關掉的路徑，repo 判例）：
#   · 只在 AUTOSDD_UNATTENDED 有設（無人值守／並行包）時**阻斷**；有人值守只出聲
#     不阻斷——主 session 每輪都要改這些檔，擋了守衛就會被關掉。
#   · 保護面＝下表字面清單（SSOT 只有這一份，測試與文件都引用這裡）；寫入目標落在
#     專案根之外一律放行（scratchpad／合成樹裡的同名檔不是治理檔）。
#   · 刻意**沒有行內豁免**：無人值守的回合自己寫得出豁免（同 authz 的處置）。
#     人的出口＝啟動 claude 前設 AUTOSDD_GOVWRITE_GUARD_OFF——刻意不與
#     AUTOSDD_GIT_GUARD_OFF 共用（共用會讓「關掉 git 守衛」順手把治理面唯讀一起
#     關掉，而那件事沒有人會注意到；repo 對此已有明文與具名測試）。
# 誠實劃界（擋不到什麼）：經 shell 的寫檔（`sed -i`／`tee`／`cp` 蓋治理檔）走的是
# Bash/PowerShell 指令字串面，本包刻意不加該判準（寫檔動詞的假紅面大，會把守衛
# 變成天天誤擋的東西）；MCP 檔案工具與其他 session 同樣不經此觀測面。
GOVWRITE_OFF_ENV = "AUTOSDD_GOVWRITE_GUARD_OFF"
#: 治理面的射程（寫檔工具）。與 OWN_TOOLS 刻意分開：兩族判準輸入不同（路徑 vs 指令字串）。
GOV_TOOLS = frozenset({"Write", "Edit", "NotebookEdit"})
#: 保護面清單（相對專案根、正斜線）。`.claude/hooks/` 底下只保護 `.py`（README 等不擋）。
#: 收錄邊界判準＝「改它可直接改變 cap/band/武裝裁決/守衛自身行為」（R95 修復包 m4，
#: 論證全文＝GovWrite 證據檔 §2.2）。`.env` 是 QA 探針實證的繞行面（settings.json 的
#: `env` 同義載體，M3）；`.autoclaude/` 是 PRD 紅線 10 字面的目錄前綴（目錄今日不存在，
#: 先釘判準）。
_GOV_HOOK_PREFIX = ".claude/hooks/"
_GOV_DIR_PREFIX = ".autoclaude/"
_GOV_EXACT = frozenset({
    ".env", ".claude/settings.json", ".claude/settings.local.json",
    "tools/lib/quota_meter.py", "tools/lib/quota_gate.py", "tools/lib/quota_policy.py",
    "tools/lib/quota_pace.py", "tools/lib/quota_limits.py", "tools/lib/pace_contract.py",
    "tools/lib/sentinel_lifecycle.py", "tools/lib/schedule_backend.py",
    "tools/lib/quota_messages.py", "tools/lib/quota_escalation.py",
    "tools/lib/platform_utils.py", "tools/session_resume_planner.py",
})

_GOVWRITE_BLOCK_MSG = (
    "🔴 治理檔在無人值守下唯讀（PRD §15.5 紅線 10），已擋下：{rel}\n"
    "  需要改它請回報主控，由收尾單人窗口處理（立案＝R87：agent 為繞過 halt 改了"
    "取數層 ⇒ 13 agent 全滅、1.3M tokens 零產出——守衛的訊息就是答案）。\n"
    "  本條刻意沒有行內豁免；人的出口＝啟動 claude 前設 " + GOVWRITE_OFF_ENV + "。\n")
_GOVWRITE_NOTE_MSG = (
    "[block_destructive_git] 提醒：{rel} 是治理檔（PRD §15.5 紅線 10 保護面）。"
    "有人值守 ⇒ 只出聲不阻斷；無人值守回合對它是唯讀的，改完請跑對應守衛測試。\n")


def govwrite_hit(tool_input: object) -> str | None:
    # 寫入目標落在治理面時回「相對專案根的正斜線路徑」，否則 None。realpath 對根與
    # 目標**兩邊都做**：symlink（mac 的 /tmp）與 `..` 繞行收在同一格；相對路徑以專案根
    # 為基準（production 的 file_path 實測是絕對路徑，這格是防禦縱深）。任何解析失敗
    # ＝不在保護面——fail-open 是 P0（hook 誤觸 deny 會把所有工具硬鎖死）。
    try:
        raw = (tool_input.get("file_path") or tool_input.get("notebook_path")) \
            if isinstance(tool_input, dict) else None
        if not isinstance(raw, str) or not raw.strip():
            return None
        root = os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
        target = os.path.realpath(raw if os.path.isabs(raw)
                                  else os.path.join(root, raw))
        if not target.startswith(_dir_prefix(root)):
            return None  # 專案根之外的同名檔不是治理檔（沙盒樹照常可寫）
        rel = target[len(_dir_prefix(root)):].replace(os.sep, "/")
        if rel in _GOV_EXACT or rel.startswith(_GOV_DIR_PREFIX) or (
                rel.startswith(_GOV_HOOK_PREFIX) and rel.endswith(".py")):
            return rel
        return None
    except Exception:  # noqa: BLE001 — 判不出＝不在保護面，見上方 P0 理由
        return None


def main() -> int:
    try:
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
        # 🔴 R95 治理面唯讀（GOV_TOOLS 一族）。刻意判在 GUARD_OFF_ENV **之前**：那個
        # 開關是 git／等待兩族的逃生口，不得順手把治理面唯讀一起關掉（兩族各自有開關，
        # 同本檔「不與既有變數共用」的既有論述；具名測試釘住兩個方向）。
        if tool in GOV_TOOLS:
            rel = None if os.environ.get(GOVWRITE_OFF_ENV) \
                else govwrite_hit(payload.get("tool_input"))
            if rel is None:
                # 逃生口有設（人啟動前設的，模型改不到 hook 行程的環境）、目標不在
                # 保護面、或判不出目標（fail-open）——三者同一格，一律放行。
                return 0
            if os.environ.get(UNATTENDED_ENV):
                sys.stderr.write(_GOVWRITE_BLOCK_MSG.format(rel=rel))
                return 2
            sys.stderr.write(_GOVWRITE_NOTE_MSG.format(rel=rel))
            return 1
        if os.environ.get(GUARD_OFF_ENV) or tool not in OWN_TOOLS:
            # 前者＝git／等待兩族「人的逃生口」（模型改不到 hook 行程的環境，見模組
            # docstring）；後者＝matcher 被改寬時的第二道限縮。
            return 0

        tool_input = payload.get("tool_input")
        command = tool_input.get("command") if isinstance(tool_input, dict) else None
        if not isinstance(command, str) or not command.strip():
            sys.stderr.write(
                f"[block_destructive_git] {tool} payload 沒有 command 字串 ⇒ 本次不檢查。\n")
            return 1

        # payload 的 `cwd` 只是**起點**：實測它恆為專案根（即使指令自己 `cd` 去別處），
        # 所以真正的落腳目錄一律由指令字串推導（見模組 docstring）。傳它進去是為了讓
        # 相對路徑的 `cd` 有基準——而那個基準指向共用工作樹，方向正是 fail-closed。
        raw_cwd = payload.get("cwd")
        start_dir = raw_cwd if isinstance(raw_cwd, str) else None
        hits = destructive_git_hits(command, start_dir=start_dir)
        # 🔴 鐵律六那一族的旗標來源是 payload 自己（本輪實測：前景呼叫**沒有**這個 key、
        # `run_in_background: true` 的呼叫有 ⇒ `bool(...)` 兩向都正確，不需要預設值特判）。
        wait_hits = waitform_hits(
            command, run_in_background=bool(tool_input.get("run_in_background")))

        unattended = bool(os.environ.get(UNATTENDED_ENV))
        # 🔴 R85／P12：授權邊界（無人看管 ⇒ 禁動 git 歷史）。此前只有 Windows 那支
        # 姊妹 hook 有，而它 matcher 是 `PowerShell`、且 `os.name != 'nt'` 就 exit 0
        # ⇒ mac 上一行都不跑。git 那一半餵**本檔解析器**的結果（`sudo git`／`git -C`／
        # argv 序列／殼 `-c` operand 四個平面都認得，體例同 `destructive_git_hits()`），
        # 比正則精準；`gh` 那一半沒有第二個解析器，兩支 hook 共用同一條正則。
        authz = authz_hits(mask_inert(unquote_exe_paths(command)), [
            c.sub for text in (command, argv_git_fragments(command))
            for c in git_invocations(text)]) if unattended else []
        # 🔴 順序本身就是判準的一部分：無人看管時**先於**行內豁免判定，因為那個回合
        # 可以自己寫出豁免註解（同 lint_powershell_command.py 對授權邊界的處置）。
        # 🔴 兩族的豁免**各自獨立判**：一個 `# git-guard-ok:` 不得順手放行一個壞掉的
        # 等待形態，反之亦然（同兩個標記字樣刻意不同的理由）。
        if hits and has_exemption(command) and not unattended:
            hits = []
        if wait_hits and has_waitform_exemption(command) and not unattended:
            wait_hits = []

        # 偵測層（見上方 R84 偵測層說明）：出聲但**絕不阻斷**。rc=1 是 Claude Code 對
        # 「stderr 給人看、工具照跑」的那一格，與本檔既有的退化 payload 分支同一格。
        # 🔴 R84／SD-04：ack 的語意是「**接下來真的會有**一次 stash 經過本守衛」⇒ 它必須
        # ①用 `git_invocations()` 判而不是子字串（否則 `grep … stash` 就能把哨兵消音）、
        # ②在本次要阻斷時為 False（被擋下的指令根本不會跑，它解釋不了任何 ref 變動）。
        # 兩者缺一，下一輪真正隱形的那條路就會被靜默吞掉——而吞掉是**永久**的。
        note = stash_ref_sentinel(
            start_dir, stash_writer_seen(command) and not (hits or wait_hits))
        sys.stderr.write(note or "")
        if not hits and not wait_hits and not authz:
            return 1 if note else 0

        message = ""
        # 授權邊界排在最前面：它回答的是「你這一跑有沒有權限做這件事」，而其餘兩族
        # 回答的是「這個寫法對不對」。權限不足時先講權限，讀者才不會去修寫法。
        if authz:
            message += authz_header("git-guard-ok") + "".join(f"{h}\n" for h in authz)
        if hits:
            message += (_HEADER + "".join(f"   · {h}\n" for h in hits)
                        + (_UNATTENDED_NOTE if unattended else _FOOTER))
        if wait_hits:
            message += (_WAITFORM_HEADER + "".join(f"   · {h}\n" for h in wait_hits)
                        + (_WAITFORM_UNATTENDED_NOTE if unattended else _WAITFORM_FOOTER))
        sys.stderr.write(message)
        return 2
    except Exception:  # noqa: BLE001 — fail-open 是刻意的，見模組 docstring 的 P0
        return 0


if __name__ == "__main__":
    sys.exit(main())
