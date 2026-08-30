#!/usr/bin/env python3
"""Stop hook：量化判決數字**沒有出處**時出聲（治「宣稱先於查證」最大失誤桶的輸出面）。

WHY（本檔的立案量測）
--------------------
`tools/probe/misstep_attribution.py` 連兩輪把 `CLAIM-FIRST`（宣稱先於查證）量成最大的
非-OTHER 桶（本批當回合實測 n=1269／201 筆，`--control` lift 亦居首）。而該桶此前
**零攔截器**：它發生的平面是「宣稱本身」，永不變成 repo 裡的檔案 ⇒ 全庫靜態掃描器
結構上看不見它。既有的 `tools/probe/audit_session.py` 已經在事後量它（`CLAIM_RE` ×
`EVIDENCE_RE` × 往回看 3 個 tool_result），但依其檔頭自述**只能當每輪收尾的量測器**，
而且沒有任何地方會自動跑它 ⇒ 那個數字只在有人想起來時才存在。

本檔補的是**那個平面上的觀測者**：Stop 事件在「一則回覆剛落地」的那一刻觸發，payload
同時給得到宣稱（`last_assistant_message`）與證據面（`transcript_path`）——本批以拋棄式
dump hook 實測確認兩個欄位都在，且逐字稿當下**已經含**那一則的文字。

判準（為什麼是這個形狀，而不是「有沒有跑過工具」）
------------------------------------------------
逐字稿實測逼掉了兩個更直覺的判準，過程留在這裡以免有人再走一次：
  · **「這一輪沒叫過工具就出宣稱」** → 51 支逐字稿命中 28 筆，逐筆判讀後**多數是假紅**：
    收尾那一則本來就常是「把本場前幾輪真的跑過的結果收斂成一段話」，零工具是正常的。
  · **`EVIDENCE_RE` 近鄰佐證（audit_session 的既有判準）** → 同一批母體 `--latest 8`
    實測 78/275（28.4%）判無佐證。那個量級當量測器可以，當每輪都會響的警報不行——
    本 repo 已判過「一個永遠在響的警報等於沒有警報」。

現行判準因此收到**值域**上：一個「只可能來自某次執行」的數字（`N passed`／`N failed`／
`N OK`／`rc=N`），若它在**本場自己的工具輸出裡從來沒出現過**，那它只有兩個來源——
別人的回報，或者沒有來源。⇒ 判準不是「你有沒有驗」，是「**這個數字的出處在哪**」，
而它是**可滿足的**：自己跑過就必然對得上，轉述別人的就標一個出處標記（`[他包回報]`
是 `docs/04_planning/AutoSDD_improving_106.md` §0 已定義的既有慣例，此前零觀測者）。
可滿足性是設計約束不是客氣：擋到讓人無法工作的守衛會被整個關掉，而被關掉的守衛比
沒有守衛更糟。

落地當回合的真實面假紅普查（母體＝本機 51 支逐字稿，非 tracked 面）：
命中 **13 筆／470 筆量化判決宣稱**（2.8%），逐筆人工判讀 **12 筆真陽性**（全部是把別包
交件的數字當自己的話講）、**1 筆假陽性**（在描述某個機制的門檻值時寫出 `pmset rc=127`）。
收斂過程中修掉的兩類假紅**都是量出來的、不是猜的**：
  ① 千分位逗號——`3,566 passed` 的 `\\b(\\d+)` 只抓到 `566`（≠`3566`）。  # baseline-ok:語料
     正規化刻意只吃**數字之間**的半角逗號：先前版本連全角「，」一起吃，把
     `rc=0，44 skip` 併成 `rc=044` 而自製一筆假紅。
  ② 已帶出處標記的轉述——那正是本判準要的行為，命中它等於處罰正解。

🔴 **只出聲，永不阻斷**（exit 0；Stop hook 的 `decision:block` 一律不用）。三條理由各自
獨立成立：① 上述 7.7% 假紅率對阻斷型判準太高；② Stop 阻斷會把回合推回模型手上，而
本判準治的是「話講得太滿」，不是「工作沒做完」——推回去只會生出更多話；③ Stop 阻斷
迴圈的唯一煞車是 `stop_hook_active`，把煞車押在單一旗標上不值得。

第二個判準：錯誤訊息的字面被當成機制結論（R89 `DEF-200-123`，逃生口自己一個）
------------------------------------------------------------------------
立案事故（真實）：13 個 subagent 死於 `You've hit your monthly spend limit`，主控把**錯誤
訊息的字面**當成根因、宣稱保險池撞頂擋住了 agent，並把它寫進交棒書與多個 commit、還當
成前提餵給 Architect。掌舵者一句話戳破：那個池**本來就滿**——落款 `quota_burn.jsonl`
逐列實證它連續 15 列都是 100.0 ⇒ **它是常數，數學上不可能是變因**。

上面那個值域判準對這件事**結構上失明**：因果宣稱不帶可比對的值域。而「你有沒有做變因
查證」問不出可滿足的答案（普查實測見下），所以本判準同樣做了一次**收斂到可判定面**的
動作，只是收斂的目標不同：不問「你驗了嗎」，問「**這句話的主詞是不是機器剛剛吐給你的
那串字**」——句子做出機制結論（`MECHANISM_RE`）、主詞是一段反引號英文錯誤字面、而那串
字**逐字出現在本場的工具輸出裡** ⇒ 出聲。三個條件都是字串比對，沒有一項需要理解語意。

可滿足性同上一個判準：句子裡寫出你做過的對照（`常數`／`變因`／`對照組`／`反例`／
`成功組`／`失敗組`／`唯一差異`／`證偽`…＝`CONTRAST_RE`）即抑制。**這不是客氣**——真的做
過對照的句子本來就會寫出對照，而沒做過的寫不出來。

真實面假紅普查（母體＝本機**全部** 1,039 支逐字稿，非 tracked 面；重跑＝
`python tools/probe/causal_form_census.py`）：assistant 句 **40,703**、其中機制結論句
**1,474**、被 `CONTRAST_RE` 抑制 **54**、**最終命中 3 筆**（0.007%），逐筆人工判讀
**3 筆全部是真陽性**——都是本事故那條假前提鏈，分屬三場（上一輪的主 session、它派出的
一個 subagent、本輪主 session）。**假陽性 0 筆。**
🔴 **母體差一點就是假的**：`~/.claude/projects/<slug>/` 只住 60 支，另外 **978 支 subagent
逐字稿住在再深一層**的 `<session>/subagents/`。第一版普查用 `glob("*/*.jsonl")` 只掃到
6% 的母體、報回 4 筆命中／50% 精確率——**「假紅率看起來很低」最常見的成因就是母體被截斷**。
改 `rglob` 之後同一份判準命中 13 筆、精確率掉到 23%。
🔴 **精確率 23%→100% 是靠一條判準修的，不是靠調參**：那 10 筆假陽性有 8 筆的共同形態是
「引述的字面其實是**符號**」（`ModuleNotFoundError`／`DeadlineExceeded`／`WinError 216`／
`subprocess.TimeoutExpired`／某支測試的名字因為含 `…NeverExceed…` 而命中 `exceed`）。
符號與訊息的分別是語意上的，不是統計上的——見 `_is_prose_message()`。
🔴 抑制詞的鑑別力也是**量出來的**：拿掉它會多命中 1 筆，而那 1 筆**恰好是掌舵者訂正後
我自己寫下的正解**（「⇒ 它是常數，不可能是變因」）⇒ 它只擋正解、不減損鑑別力。
🔴 **誠實劃界：3 筆命中引述的是同一串字面**（`monthly spend limit`）⇒ 本判準在**這一型
缺陷的複發**上已證明有鑑別力且零假紅，但它對「別的錯誤訊息被當成根因」的召回率
**在本機母體上無從量測**（沒有第二個實例）。這是邊界，不是保證。

🔴 **兩個更直覺的形狀已被同一份普查逐一證偽，不要再走一次**（數字皆現跑
`--shape a`／`--shape b`）：
  · **「因果宣稱裡的具名量在本場觀測值全同」**（＝直接把「常數不可能是變因」寫成判準）
    → 命中 3 筆，逐筆判讀 **1 真 2 假**（33%）。假紅的成因是結構性的：判準只知道那個識別
    字**出現在句子裡**，不知道它是不是被當成原因（兩筆假紅分別是「`arm_reset` 全是 0 ⇒
    兩個痕跡不一致」與「跟 `five_hour`、`seven_day` 平起平坐 ⇒ 它 100% ⇒ 一票否決」，
    命中的識別字都只是**被順帶提到**）。這件事在散文平面上沒有解——要判斷誰是主詞就要
    理解語意，而那正是判準不該做的事。
  · **「因果宣稱裡的具名量在本場沒有兩個相異觀測值」**（含 0 次觀測）→ 命中 **153 筆**，
    隨機抽 12 筆逐筆判讀 **0 真 12 假**（0%）：命中的全部是 `condition_evaluator`／
    `last_log_path`／`enable_kernel_brain`／某支測試的名字這種**程式符號**，它們根本不是
    「量」，本來就不會有觀測值 ⇒ 這個形狀等於對「句子裡出現 snake_case」發警報。
⇒ **常數／變因這條軸在散文平面上做不出鑑別力**，它只在**落款平面**上是精確的（那裡欄位
與值都是結構化的，不必猜主詞）。所以那一半刻意**不做成警報**，改做成一支**正向工具**
`tools/probe/variate_contrast.py`：餵它一份 JSONL 落款，逐欄印出「觀測數／相異值數／
是不是常數」，並可 `--split-at` 切成兩組看哪些欄位真的區分得開兩組。本事故用它是一行的事
——`spend`／`extra_usage` 會直接印成 `CONSTANT`＝不可能是變因。本判準的訊息因此**指著它**，
讓查證比宣稱便宜（判準治形態、工具治內容，兩者刻意分工，不是同一份知識住兩個家）。

第三個判準：引述一個**已經過期**的額度讀數（本輪 M1~M8，逃生口自己一個）
--------------------------------------------------------------------
立案（使用者原話）：「我沒有每分每秒監督，也不一定會發現」。根 CLAUDE.md 對 `--pace`
的規定逐字是「值是 (水位%, 距 reset) 的函式——**每次派工前現查，不得記住上次的值**」，
而此前**零觀測者**：把四小時前的 pace 區塊整塊貼上，沒有任何東西會說一句話。

判準：句子裡出現「軸名 ＋ 百分比」（`PACE_AXES` × `PACE_VALUE_WINDOW` 字元窗），而那個
讀數的**量測時刻**距今超過該軸自己的 TTL ⇒ 出聲。量測時刻兩條路取得：作者自己貼的
`量測於=<ISO>`（優先），否則往本場 `tool_result` 回溯找同一個「軸＋值」的錨點、取那筆
落款時刻。

🔴 **逃生口是算術，不是「在場即抑制」**：貼了 `量測於` 不等於免罰——本判準把那個時刻
**解析出來算 age**，只有 `age <= TTL` 才靜音。立案是量出來的：先前設計版的抑制器（在場
即抑制）在本機全母體上**一次都沒有做對過** ⇒ 那不是逃生口，那是隨機靜音器。因此訊息
一律寫「**重跑** `--pace` 並貼上**新的** 量測於」，絕不寫「貼上量測於即抑制」——後者會把
讀者訓練成把舊區塊整塊貼上，而那正是本判準要治的行為本身。

🔴 **per-axis TTL 是導出來的，不是挑的**（M5）。落款 SSOT＝`~/.autosdd/traces/quota_burn.jsonl`，
本輪重跑（`rows=134`，跨 `2026-08-12T22:45:43+08:00` ~ `2026-08-23T20:49:42+08:00`，逐相鄰
樣本取 `Δpp/Δhr`、reset 造成的下降不計）實測**中位漂移**：
`five_hour` 27.1357／`session` 26.7305／`seven_day` 2.6315／`weekly_all` 2.5316 pp/hr，
而 `weekly_scoped`／`spend`／`nimbus_quill`／`extra_usage` 中位 **0.0000**。
TTL 取「期望漂移 1pp」⇒ `3600 / rate`（見 `PACE_TTL_S`）。
🔴 中位 0 的四軸**刻意不判**（M5 給的兩條路裡選「照實登記已量測的假紅類別」那條），而且
**不採信「那個讀數在物理上不會過期」**——同一份重跑實測 `weekly_scoped` 的 p90 是 9.375、
最大值 31.034 pp/hr（`spend` 最大 9.708），⇒ 它會動，只是中位是 0。把它判成「無上界」
會是一句在自己的母體上就能證偽的話；不判它是**登記的盲區**，不是「安全」。

🔴 **距離窗與單位都是量出來的**（M6；母體＝本機全部逐字稿的 assistant 文字塊 12,265 個，
軸出現 1,826 次，重跑腳本見 `docs/06_quality/` 本輪證據檔）：
  · 「軸 → 最近一個帶 `%` 的值」距離分佈 min=1／p50=2／p75=14／p90=38／max=76 ⇒ 窗寬
    覆蓋率實測 `<=8` **68.7%**、`<=20` 79.9%、`<=40` **91.6%**、`<=60` 97.8%。取 40：8
    是挑的（漏掉 31.3%），60 開始把隔句的數字吃進來。**殘餘 8.4% 是登記的漏抓**。
  · **全角 `％`**：assistant 文字面實測 **1** 次、含 tool_result 的原始語料 **83** 次。
    覆蓋成本是一個字元（`[%％]`）⇒ 收。**本輪不引用複審那一包的 37**（單機單作者母體，
    且我這輪量到的是 1／83，不是 37 — 母體定義不同的數字不可互換）。
  · **全角數字**（`０`~`９`）：assistant 文字面實測 **0** 次 ⇒ 不做正規化（沒有母體支持的
    覆蓋只是猜）。這是登記的漏抓。
  · **「軸 ＋ 裸數字」（無單位）刻意不判**：同一份普查裡「軸後最近值只有裸數字」的有 696
    次（vs 帶 `%` 的 418 次），而它的距離 p50=29（帶 `%` 的是 2）⇒ 那個數字**通常根本不是
    這個軸的值**（行號、筆數、別的百分比）。判它會讓觸發面 ×2.66 且多數是雜訊，而
    「一個永遠在響的警報等於沒有警報」本 repo 已有判例。代價是 `session 16`（不寫 `%`）
    可以規避 ⇒ **登記的規避口**，與下面那個同類。

🔴 **「錨不到＝放行」是登記的盲區，不是通過**（M7）。照實引述一個四小時前的真數字會被
唸；憑空捏一個讀數則錨不到、放行 ⇒ 反向誘因。判準無法在散文平面上分辨「捏的」與
「輸出被截斷」，所以本檔的處置是把它**單獨記一類**（`kind="unanchored"`）並讓它可數：
每次落一列 `claim_freshness.jsonl`，同一次執行讀回累計數塞進送給模型的那則訊息。
**這不是修好那個盲區，是讓它有數字。**

🔴 **送得進模型的通道只有一條，而它有迴圈**（M1）。stderr ＋ exit 0 **不進模型 context**
（`tools/lib/platform_utils.py` 的 `emit_to_model` 區塊註解逐字記著 `DEF-200-135`：實測
1h49m／45 turns 零訊號）；本機全母體 26 筆 Stop attachment 的 `content` 非空數 **0**、
`stderr` 非空 **26**，且有因果憑證（同一個值在相隔 38 分鐘各響一次 ⇒ 那則訊息不在行為
迴圈裡）。唯一送得進去的是 stdout 上的 `hookSpecificOutput`——但它會讓模型多跑一回合，
而那一回合結束又觸發 Stop ⇒ **不夾住就是自己燒額度**（實測一個 prompt 9 次 Stop、9 則零
內容 assistant 訊息）。⇒ 一律夾在 `stop_hook_active` 上：只有它為假時才發射，實測收斂成
2 次 Stop、1 次發射、恰好 1 個額外回合。**這個夾具不是優化，沒有它這支守衛會在額度吃緊
的那一刻製造它要防的傷害。**

誠實劃界（本檔抓不到什麼）
------------------------
· **只看數字**。「全綠」「已驗證」「零損失」這種**不帶值**的判決一律看不到——它們沒有
  可比對的值域，而那正是 `audit_session.py` 那支事後量測器的射程（兩者刻意分工，不是
  同一份知識住兩個家）。
· 第二個判準只認**反引號包起來的英文**錯誤字面。同一句話改寫成中文轉述（「死於月度支出
  上限」）或拿掉反引號就完全看不到 ⇒ 它守的是**這一型的複發**，不是整類因果謬誤。
· 第二個判準**不判斷因果是對是錯**，只判斷「你把機器的話當成了自己的結論」。上面兩筆
  假陽性正是這個邊界：推理其實成立，只是形態相同。**所以它只出聲、不阻斷**（同上）。
· **抓不到「有輸出但輸出被誤讀」**：數字對得上就放行，即使那個輸出講的是另一件事。
  R84 帳本裡「看著 rc=0 的下三行印著 Windows 欄失敗卻得出相反結論」那一型，本檔看不到。
· **出處標記無法防無人看管的模型自己寫**：句子裡塞一個「宣稱」就會被抑制。與
  `# git-guard-ok:` 同型，故 `AUTOSDD_UNATTENDED` 有設時**抑制詞表縮到只認方括號標記**
  （`[他包回報]`／`[本包實測]`），因為那兩個字面在 `docs/04_planning/` 有成文定義、
  亂標會在收輪對帳時被逐列核出來。這仍**不是**密封，只是把成本拉高。
· **證據面只認 `tool_result`**：背景 agent 的完成通知不是 tool_result ⇒ 它帶回來的數字
  一律判成無出處。這是**刻意的**——那正是「採信 agent 回報而未親查」本身。
· 第三個判準只在**寫出百分號**時看得見（見上方 M6 登記的兩個規避口：裸數字、全角數字）；
  它也**不判讀數對不對**，只判「你引的這個值是什麼時候量的」。
· 第三個判準的 TTL 由**本機**落款導出 ⇒ 換一台機器、換一種用法，漂移率就不是這幾個數字。
  重跑方式寫在 `PACE_DRIFT_MEDIAN_PP_PER_HOUR` 旁註；不重跑就沿用等於把量測值當常數。
· **執行期證據那一格只讀本場逐字稿**（`runtime_carrier_verdict`）：它看得到「本平台自己
  那條載具失敗」，看不到「載具跑起來了但目標腳本自己 fail-open 成了 no-op」——後者不留
  attachment（`hook_success` 只有在 hook 真的印字時才落盤，全母體實測）。
· 逐字稿讀不到／payload 退化／任何非預期例外 ⇒ **一律 fail-open 靜默放行**
  （`.claude/settings.json` description 記載過的 P0：hook 誤觸 deny 會把所有工具硬鎖死）。

判準本體 `unsourced_verdict_hits()` 是純函式，由 `tools/tests/test_claim_provenance_r86.py`
機械釘住（含合成注入紅綠雙向自證）。依賴方向與 `lint_powershell_command.py` 同：
**`tools/probe` 向本檔借，本檔不 import 任何 repo 模組**（本檔由 `runpy.run_path` 起、
`sys.path` 上沒有 `tools/`，import 期爆掉會破壞 fail-open 契約）。
"""
from __future__ import annotations

import json
import os
import re
import sys

# `timezone.utc` 不用 `datetime.UTC`（py311+）：hook 鏈須在 mac 預設直譯器載入。
from datetime import datetime, timezone

# payload 讀取與 UTF-8 stdio 都住共用層 `tools/lib/platform_utils.py`，形態逐字對齊姊妹檔
# `block_destructive_git.py`／`lint_powershell_command.py`（同一個 shim、同一個 except 語意）。
# 🔴 **本檔不得自己碰 `sys.stdin`、也不得自己 reconfigure**：兩者各有一條 shrink-only 棘輪
# 在守（`test_pre_commit_dispatcher_sigpipe.py::TestHookPayloadSingleHome`／
# `test_platform_utils_dedup.py::TestR75StdioUtf8HasOneImplementation`）。本檔第一版兩條都
# 犯了，被那兩道鎖當場判紅——立論逐字是「長出第二個家的唯一入口就是自己碰 stdin」，而
# 此前 7 支手抄本實測已漂移成 3 種行為。無 UTF-8 保護的代價同樣是實測過的（DEF-101-789，
# GitHub windows-latest 逐字重現）：本檔的輸出**就是使用者唯一看得到的指引**，en-US
# （cp1252）下整段變 `\uXXXX` 逃脫、zh-TW（cp950）下變亂碼 ⇒ 「出聲有了、教學沒了」。
# 與 fail-open 契約不衝突：共用層不可達時 payload 退化成 `{}`（走下面「缺欄位即 return 0」
# 分支）、`init_utf8_streams()` 契約是「取不到就靜默不動」，兩者都與 fail-open 同向。
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "tools", "lib"))
try:
    from platform_utils import read_hook_payload  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001 — 共用層不可達＝退化，不是崩潰（fail-open 是 P0）
    def read_hook_payload() -> dict:  # type: ignore[misc]
        return {}

try:
    from platform_utils import init_utf8_streams  # type: ignore[import-not-found]

    init_utf8_streams()
except Exception:  # noqa: BLE001 — 模組層崩潰會繞過 main() 的 fail-open，故必須吞掉
    pass

# 🔴 三個「有就用、沒有就退化」的借用（每一個都各自 try：任一不可達不得拖垮其他兩個，
# 而三者全部不可達時本檔仍必須是一支會 exit 0 的合法 hook）。
#   · `emit_to_model`：唯一送得進模型 context 的通道（見檔頭 M1）。取不到就只剩 stderr，
#     那等於回到 `DEF-200-135` 的狀態——**會靜默失聲**，所以退化版回 False 讓呼叫端知道。
#   · `hook_wiring`：執行期證據判準（M9）住在佈線唯一真相源那一支，本檔不重寫第二份。
#   · `trace_dir`：痕跡目錄解析的 SSOT（`AUTOSDD_TRACE_DIR` 逃生口、唯讀時退回暫存）。
try:
    from platform_utils import emit_to_model  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001
    def emit_to_model(event: str, msg: str) -> bool:  # type: ignore[misc]
        return False

try:
    import hook_wiring  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001
    hook_wiring = None  # type: ignore[assignment]

try:
    from endurance_env import trace_dir  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001
    trace_dir = None  # type: ignore[assignment]

#: 「只可能來自某次執行」的量化判決形狀。刻意不含不帶值的判決詞（見檔頭誠實劃界）。
VERDICT_RE = re.compile(
    r"(?:\b(\d{1,7})\s+(?:passed|failed|OK)\b|\brc\s*=\s*(\d{1,3})\b)", re.IGNORECASE
)

#: 出處標記。命中即抑制——轉述別人的數字並標明出處，是本判準要的**正解**。
PROVENANCE_RE = re.compile(
    r"(\[他包回報\]|\[本包實測\]|宣稱|回報|回覆|轉述|聲稱|所述|交件|測得|據|"
    r"未親驗|未重跑)"
)

#: 無人看管時只認方括號標記（見檔頭：把「自己寫一個豁免」的成本拉高）。
UNATTENDED_PROVENANCE_RE = re.compile(r"(\[他包回報\]|\[本包實測\])")

#: 千分位正規化：**只**吃數字之間的半角逗號。連全角「，」一起吃會把
#: `rc=0，44 skip` 併成 `rc=044` ⇒ 自製假紅（本批實測）。
_THOUSANDS_RE = re.compile(r"(?<=\d),(?=\d)")

_SENTENCE_RE = re.compile(r"(?<=[。！？!?\n])")

#: 「這句話在做機制結論」的標記。`⇒` 收在裡面是量出來的：本 repo 的推論慣用它，而事故
#: 那兩句**都沒有**用 `造成`／`導致`，只用了 `⇒`——不收它就對本事故零召回。
MECHANISM_RE = re.compile(
    r"(根因|真因|成因|病因|真正的原因|造成|導致|肇因|引發|root cause|⇒)")

#: 反引號內的英文長字面（≥11 字元）＝ 錯誤訊息被引述時的典型形態。
_BACKTICK_LITERAL_RE = re.compile(r"`([A-Za-z][A-Za-z0-9'’,.\- ]{10,120})`")

#: 上面那個字面要**看起來像錯誤訊息**才算數（否則整片反引號英文都會進來）。
_ERROR_WORD_RE = re.compile(
    r"(?i)(error|limit|failed|failure|denied|refus|exceed|not found|timeout|"
    r"unauthor|forbidden|cannot|can't|unable|hit your)")

#: 🔴 **符號 ≠ 訊息**——這一條把精確率從 23% 拉到 100%（普查實測，見檔頭）。
#: 錯誤**訊息**是機器寫給人看的散文（小寫詞＋空白）；例外**類別名**是符號
#: （`ModuleNotFoundError`／`DeadlineExceeded`／`WinError 216`／`subprocess.TimeoutExpired`）。
#: 寫「⇒ `ModuleNotFoundError`」的人是在指認一個他推理出來的失效**模式**，不是在轉述機器
#: 的話——那正是本判準要放行的行為。判準：≥2 個空白分隔的詞，且每個詞都不含**詞內大寫**、
#: 也不含 `.`／`_`／`:`（三者都是符號的記號，不是散文的記號）。
_SYMBOL_TOKEN_RE = re.compile(r"[._:]|(?<=.)[A-Z]")


def _is_prose_message(literal: str) -> bool:
    """這串字看起來是「機器寫給人看的一句話」，而不是一個符號名。"""
    tokens = literal.split()
    return len(tokens) >= 2 and not any(_SYMBOL_TOKEN_RE.search(t) for t in tokens)

#: 抑制詞＝「我已經做過變因對照」的證據。普查實測它只擋掉正解那一句（見檔頭）。
CONTRAST_RE = re.compile(
    r"(常數|變因|對照組|對照|反例|控制|兩組|證偽|唯一差異|成功組|失敗組|同一個值|沒有變)")


#: 額度／pace 軸名。SSOT＝`tools/lib/quota_policy.KNOWN_KINDS`；本檔刻意重寫一份字面而
#: 不 import 那支檔（本檔的 import 面只准是「有就用、沒有就退化」的三個借用，多一個硬
#: 相依就多一條 fail-open 路徑），對帳由 `tools/tests/test_claim_provenance_r86.py` 的具名
#: 斷言做——同一份知識允許住兩個家的唯一條件就是有東西在對帳。
PACE_AXES = ("session", "five_hour", "seven_day", "weekly_all", "weekly_scoped",
             "nimbus_quill", "spend", "extra_usage")

#: 本輪重跑實測的**中位**漂移率（pp/hr）。母體＝`~/.autosdd/traces/quota_burn.jsonl`
#: （rows=134，跨 2026-08-12 ~ 2026-08-23），逐相鄰樣本取 `Δpp / Δhr`、reset 造成的下降不計。
#: 🔴 **這是量測值不是常數**：換機器／換用法就不是這幾個數字，重跑方式見檔頭 M5 段。
#: 值為 0 的軸＝中位不動 ⇒ 依檔頭登記**刻意不判**（不是「無上界」，同段有反例）。
PACE_DRIFT_MEDIAN_PP_PER_HOUR = {
    "session": 26.7305, "five_hour": 27.1357, "seven_day": 2.6315, "weekly_all": 2.5316,
    "weekly_scoped": 0.0, "spend": 0.0, "nimbus_quill": 0.0, "extra_usage": 0.0,
}

#: per-axis TTL（秒）＝「期望漂移 1pp 需要多久」。**導出來的，不是挑的**——這一行就是
#: 導出式本身，改門檻只能改上面那張量測表（或重新量），不能直接改秒數。
PACE_TTL_S = {axis: round(3600.0 / rate)
              for axis, rate in PACE_DRIFT_MEDIAN_PP_PER_HOUR.items() if rate > 0}

#: 軸名到它的百分比值之間允許幾個字元。40＝實測 p90（覆蓋 91.6%）；見檔頭 M6 的覆蓋率表。
PACE_VALUE_WINDOW = 40

#: 🔴 讀數還必須與 **pace 輸出自己的欄位記號**同行。這不是額外的抑制器，是把觸發面收回
#: 到本判準自己的立案（「把舊的 pace **區塊**整塊貼上」）上——沒有這一條，判準等於對
#: 「散文裡提到某個軸名附近有個百分比」發警報，而那個母體裡多數根本不是讀數。
#:
#: 🔴 **精確率是逐筆判讀出來的，而且它比本檔另兩個判準弱——照實寫在這裡，不藏**。
#: 母體＝本機 1,061 支逐字稿／12,279 個 assistant 文字塊／330 個軸綁定百分比讀數
#: （重跑方式見檔頭 M6 段；逐場重放，以「該則之前」的 tool_result 當證據面、該則自己的
#: 落款時刻當 now ⇒ 量的是**當時真正的處境**，不是事後視角）：
#:   · 不收斂（只有「軸 ＋ %」）：stale **71**，抽 12 筆逐筆判讀 **5 真 7 假（41.7%）**
#:   · ＋ 本行的 pace 欄位記號：stale **34**
#:   · ＋ 下面的 `_STALE_AWARE_RE`：stale **30**（占讀數 9.1%、占訊息 **0.24%**、≈2.7 筆/天），
#:     抽 14 筆逐筆判讀 **8 真 6 假（57.1%）**；`unanchored` **4**（1.2%）；
#:     被「時間戳／錨點自己是新的」**正確靜音 296（89.7%）**。
#: 🔴 **對照本檔第一個判準的 12/13**：57.1% 明顯較弱。它仍然出貨的三個理由都是既有判例：
#: ① 只出聲、永不阻斷；② 有自己的逃生口；③ 送模型那條被 `stop_hook_active` 夾成恰好一個
#: 額外回合。但**這個數字必須留在檔頭讓下一個人重新裁決**，不是被寫成「已驗證」。
#: 🔴 **殘餘假紅三類照實登記，本輪刻意不再加第四、第五條 regex**（≤14 筆判讀上調參就是
#: overfitting，而本檔立案的那個「隨機靜音器」正是這樣長出來的）：
#:   (a) 把讀數當成**分析裡的證據**引述（缺陷敘事、甚至表格裡的**合成測試 fixture 值**）
#:   (b) **討論 pace 輸出本身**的名詞／格式對照表（同一則訊息會貢獻多筆）
#:   (c) 作者用**本詞表沒收的說法**敘明它是舊讀數（實例：「那是 06:45 量到的值…中間過了
#:       約 4 小時」）——這一筆與 `_STALE_AWARE_RE` 同類，只是詞沒收到。
#: 已實測否決的修法：擋「反引號內／表格列」會同時打掉**主要立案形態**（整塊貼上的
#: `kind=… band=…` 區塊本來就住在 code fence 裡，抽樣裡多筆真陽性正是它）⇒ 那不是收斂，
#: 是把召回率換掉。
_PACE_OUTPUT_TOKEN_RE = re.compile(
    r"(kind=|band=|binding=|recommended=|pace_index=|cap=|horizon=|量測於|"
    r"剩\s*\d+\s*分鐘)")

#: 🔴 **作者自己已經說出「這個讀數是舊的」時抑制** —— 與第二個判準的 `CONTRAST_RE` 同一個
#: 設計模式（本檔已驗證過兩次）：真的做對的人本來就會寫出來，沒做的寫不出來。
#: 立案是逐筆判讀出來的，不是預防性設計：12 筆抽樣裡有 **3 筆假紅是「正解被處罰」**
#: —— 作者明文寫「`cap=8` 這個數字現在是過期的」「我 22:32 量到 6%，現在量到 47%」
#: 「`five_hour` 在我取樣期間由 5% 升到 28%」，也就是**他做的正是本判準要求的事**。
#: 處罰正解是本檔檔頭已判過的失格條件（「命中它等於處罰正解」），比假紅率本身嚴重。
_STALE_AWARE_RE = re.compile(
    r"(過期|重跑|重新量|再量|現在量到|升到|降到|舊值|前值|兩個時刻|相隔|照實記)")

#: 「軸 ＋ 百分比」。`[%％]` 收全角（覆蓋成本一個字元）；裸數字刻意不收（見檔頭 M6）。
_PACE_READING_RE = re.compile(
    "(" + "|".join(PACE_AXES)
    + rf")[^\n]{{0,{PACE_VALUE_WINDOW}}}?(\d{{1,3}}(?:\.\d+)?)\s*[%％]")

#: 作者自己貼出來的量測時刻。**要求帶 offset**：不帶 offset 的字串算 age 要猜時區，而
#: naive 本地時間戳在本 repo 是明文禁止持久化的形態（鐵律三的機械物之一）。解析不到就
#: 當作沒貼 ⇒ 走錨點那條路，方向是「不因為一個壞時間戳而免罰」。
_MEASURED_AT_RE = re.compile(
    r"量測於\s*[=＝]\s*(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?"
    r"(?:Z|[+-]\d{2}:?\d{2}))")


def _parse_aware(text: str):
    """ISO 字串 → **帶 tzinfo** 的 datetime；解析不出或是 naive 一律回 `None`。"""
    try:
        when = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return when if when.tzinfo is not None else None


def _anchor_time(axis: str, value: str, stamped: list):
    """本場工具輸出裡「這個軸綁這個值」最後一次出現的落款時刻（`None`＝全場無錨點）。"""
    needle = re.compile(re.escape(axis) + rf"[^\n]{{0,{PACE_VALUE_WINDOW}}}"
                        + re.escape(value))
    for when, text in reversed(stamped):
        if when is not None and needle.search(text):
            return when
    return None


def stale_pace_hits(claim_text: str, stamped: list, now) -> list[dict]:
    """`claim_text` 裡引述的**過期**額度讀數，以及錨不到的那一類（`[]`＝沒有）。

    純函式。`stamped`＝本場 `tool_result` 的 `[(落款時刻|None, 文字)]`（時序）；`now` 必須
    帶 tzinfo。回傳每筆帶 `kind`：`"stale"`＝真的過期（會出聲）／`"unanchored"`＝軸綁定
    讀數但全場找不到錨點（**登記的盲區，不出聲、只計數**，見檔頭 M7）。
    """
    own = None
    match = _MEASURED_AT_RE.search(claim_text)
    if match:
        own = _parse_aware(match.group(1))
    seen: set = set()
    out: list[dict] = []
    for m in _PACE_READING_RE.finditer(claim_text):
        axis, value = m.group(1), m.group(2)
        ttl = PACE_TTL_S.get(axis)
        if ttl is None:
            continue  # 中位漂移 0 的軸刻意不判（檔頭 M5 登記）
        start = claim_text.rfind("\n", 0, m.start()) + 1
        stop = claim_text.find("\n", m.end())
        line = claim_text[start: stop if stop >= 0 else len(claim_text)]
        if not _PACE_OUTPUT_TOKEN_RE.search(line):
            continue  # 同行沒有 pace 輸出的欄位記號 ⇒ 這不是在引述讀數（見上方實測）
        if _STALE_AWARE_RE.search(line):
            continue  # 作者自己已經說出這是舊讀數 ⇒ 那是正解，不是違規
        when = own if own is not None else _anchor_time(axis, value, stamped)
        if when is None:
            kind, age = "unanchored", None
        else:
            age = int((now - when).total_seconds())
            if age <= ttl:
                continue  # 🔴 逃生口是**算術**：時間戳自己是新的才靜音
            kind = "stale"
        key = (kind, axis, value)
        if key in seen:
            continue
        seen.add(key)
        out.append({"kind": kind, "axis": axis, "value": value, "age_s": age,
                    "ttl_s": ttl, "source": "self-quoted" if own is not None else "transcript"})
    return out


#: 痕跡檔名。與 `quota_burn.jsonl` 同目錄、同「沒觸發＝檔不長大」語意。
FRESHNESS_TRACE = "claim_freshness.jsonl"


def freshness_trace(hits: list[dict], *, cap: int = 4 * 1024 * 1024) -> tuple[int, int]:
    """落一列痕跡並**同一次讀回**累計數 → `(累計 stale, 累計 unanchored)`。

    🔴 這個「讀回」就是本通道的自動讀者（檔頭 M8）：本輪否決權複審現查全庫的 trace 消費端只有
    一支要人記得跑的手動 probe ⇒ 那不是機制。這裡把累計數塞進同一則送給模型的訊息，
    讓盲區的數字在**沒有人監督**時也會出現在讀者眼前。誠實劃界：它只讀自己寫的那一份、
    只出聲，**repo 側沒有任何閘門會因為這個數字轉紅**（那需要一個穩定的分母，本機母體不是）。
    任何 I/O 失敗一律回 `(0, 0)`——痕跡寫不進去絕不可反過來變成守衛的故障源。
    """
    stale = sum(1 for h in hits if h.get("kind") == "stale")
    unanchored = len(hits) - stale
    if not hits or trace_dir is None:
        return (stale, unanchored)  # 沒觸發＝檔不長大（本 repo 對痕跡的既有語意）
    try:
        path = os.path.join(str(trace_dir()), FRESHNESS_TRACE)
        row = {"ts": datetime.now(timezone.utc).isoformat(), "stale": stale,
               "unanchored": unanchored,
               "axes": sorted({str(h.get("axis")) for h in hits})}
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
        if os.path.getsize(path) > cap:
            return (stale, unanchored)
        with open(path, encoding="utf-8", errors="replace") as handle:
            rows = [json.loads(x) for x in handle if x.strip().startswith("{")]
        return (sum(int(r.get("stale") or 0) for r in rows),
                sum(int(r.get("unanchored") or 0) for r in rows))
    except Exception:  # noqa: BLE001 — 見 docstring 最後一句
        return (stale, unanchored)


def normalize_digits(text: str) -> str:
    """把千分位逗號拿掉，讓 `3,566 passed` 與輸出裡的 `3566` 對得上。"""  # baseline-ok:語料
    return _THOUSANDS_RE.sub("", text)


def unsourced_verdict_hits(claim_text: str, tool_output: str,
                           unattended: bool = False) -> list[dict]:
    """`claim_text` 裡「值在 `tool_output` 中找不到」的量化判決（`[]`＝沒有）。

    純函式，供攔截端（本檔 Stop 分支）與事後量測端（`tools/probe/`）共用同一份判準。
    """
    corpus = normalize_digits(tool_output)
    seen = set(re.findall(r"\d{1,7}", corpus))
    marker = UNATTENDED_PROVENANCE_RE if unattended else PROVENANCE_RE
    hits: list[dict] = []
    for sentence in _SENTENCE_RE.split(claim_text):
        if not sentence.strip() or marker.search(sentence):
            continue
        for match in VERDICT_RE.finditer(normalize_digits(sentence)):
            value = match.group(1) or match.group(2)
            if value in seen:
                continue
            hits.append({"value": value, "sentence": sentence.strip()[:200]})
    return hits


def error_literal_mechanism_hits(claim_text: str, tool_output: str) -> list[dict]:
    """`claim_text` 裡「把機器吐出來的錯誤字面當成機制結論」的句子（`[]`＝沒有）。

    純函式，供攔截端（本檔 Stop 分支）與普查端（`tools/probe/causal_form_census.py`）
    共用同一份判準。三個條件全部是字串比對：① 句子在做機制結論；② 句子引述了一段
    看起來像錯誤訊息的反引號英文字面；③ 那串字**逐字出現在本場工具輸出裡**（＝它確實
    是機器說的，不是我自己造的詞）。句子自帶對照詞時抑制——見檔頭的抑制詞鑑別力量測。
    """
    hits: list[dict] = []
    for sentence in _SENTENCE_RE.split(claim_text):
        sentence = sentence.strip()
        if not sentence or not MECHANISM_RE.search(sentence):
            continue
        if CONTRAST_RE.search(sentence):
            continue
        for literal in _BACKTICK_LITERAL_RE.findall(sentence):
            if not _ERROR_WORD_RE.search(literal) or not _is_prose_message(literal):
                continue
            if literal not in tool_output:
                continue
            hits.append({"literal": literal, "sentence": sentence[:200]})
            break  # 一句只報一次：同一句裡的第二個字面不是另一筆缺陷
    return hits


#: 逐字稿裡「這一列值得 json 解析」的字面前篩。第三項起是 hook 執行結果 attachment 的
#: `type` 值（M9 的執行期證據面）——刻意用字面前篩而不是全列解析：本機最大逐字稿 6.0 MB，
#: 每一列都解析會把單次成本從 61ms 推到秒級，而 Stop 是**每一則回覆都會經過**的路徑。
_INTERESTING = ('"tool_result"', '"hook_success"', '"hook_non_blocking_error"')


def _read_transcript(transcript_path: str, byte_cap: int = 32 * 1024 * 1024
                     ) -> tuple[list, list]:
    """一次掃完 → `([(落款時刻|None, 工具輸出文字)], [帶 hook attachment 的記錄])`。

    `byte_cap` 是防呆而非效能手段：本機最大逐字稿 6.0 MB／全場 51 支掃完 10.3 s
    ⇒ 單場遠在預算內。超過上限時**回空字串會讓每個數字都變成命中**（截斷偏向假紅），
    故超限一律讓呼叫端 fail-open 放行，見 `main()`。

    🔴 讀不到／超上限一律 **raise**，讓 `main()` 走 fail-open 靜默放行。
    絕不可 `return`空的：空證據面會讓**每一個**數字都變成命中，而那是假紅方向。
    本檔第一版就是回空字串，被 `tools/tests/test_claim_provenance_r86.py::
    TestTruncationBiasesTowardsSilenceNotFalseRed` 當場抓出來（逐字稿路徑不存在時
    噴出一整段違規訊息）——「證據面拿不到」與「證據面裡沒有這個數字」必須分開。
    """
    size = os.path.getsize(transcript_path)  # OSError ⇒ 交給 main() fail-open
    if size > byte_cap:
        raise ValueError("transcript exceeds byte cap")
    stamped: list = []
    records: list = []
    with open(transcript_path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not any(token in line for token in _INTERESTING):
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue  # 逐字稿邊寫邊讀，尾列半截是常態
            if not isinstance(record, dict):
                continue
            if isinstance(record.get("attachment"), dict):
                records.append(record)
            when = _parse_aware(record.get("timestamp"))
            message = record.get("message")
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                inner = block.get("content")
                if isinstance(inner, str):
                    stamped.append((when, inner))
                elif isinstance(inner, list):
                    stamped.extend((when, str(b.get("text") or "")) for b in inner
                                   if isinstance(b, dict))
    return stamped, records


def _tool_output_digits(transcript_path: str, byte_cap: int = 32 * 1024 * 1024) -> str:
    """本場**自己跑出來的**工具輸出（只認 `tool_result`；見檔頭誠實劃界）。"""
    return "\n".join(text for _when, text in
                     _read_transcript(transcript_path, byte_cap)[0])


def _say(messages: list[str], event: str, quiet: bool) -> None:
    """兩條通道各說一次：stderr（人看的 log）＋ 模型 context（唯一進得去的那條）。

    🔴 `quiet` 就是 M1 的夾具：`stop_hook_active` 為真時**只寫 stderr、不發射**。發射會讓
    模型多跑一回合，而那一回合結束又觸發 Stop ⇒ 不夾就是自己燒額度（實測一個 prompt
    9 次 Stop、9 則零內容 assistant 訊息）。夾住之後收斂成 2 次 Stop、1 次發射、恰好 1 個
    額外回合。stderr 那條**保留但不能當憑證**：exit 0 的 stderr 依官方契約不進模型
    context（`DEF-200-135`，本機 26 筆 Stop attachment 的 content 非空數為 0）。
    """
    for msg in messages:
        print(msg, file=sys.stderr)
    if quiet:
        return
    for msg in messages:
        emit_to_model(event, msg)


def _pace_messages(hits: list[dict]) -> list[str]:
    """第三個判準的兩則訊息（過期讀數／登記的盲區），無事回 `[]`。"""
    if not hits:
        return []  # 無事不碰痕跡檔：`trace_dir()` 會 mkdir、讀回會掃全檔，而 Stop 是每一則
                   # 回覆都會經過的路徑（「沒觸發＝檔不長大」是本 repo 對痕跡的既有語意）
    stale = [h for h in hits if h.get("kind") == "stale"]
    totals = freshness_trace(hits)
    out: list[str] = []
    if stale:
        listed = "／".join(
            f"{h['axis']}={h['value']}%（量測於 {max(1, (h['age_s'] or 0) // 60)} 分鐘前，"
            f"TTL {h['ttl_s']} 秒）" for h in stale[:3])
        out.append(
            f"🔴 這一則引述了 {len(stale)} 個**已經過期**的額度讀數：{listed}。"
            f"額度是 (水位%, 距 reset) 的函式，不是可以記住的常數 —— 請**重跑** "
            f"`python tools/session_resume_planner.py --pace`（零 token）並貼上**新的** "
            f"「量測於=<時刻>」。⚠️ 把舊的 pace 區塊整塊貼上**不會**讓它變新：本守衛對你貼的"
            f"那個時刻**算 age**，過期照樣出聲。TTL 由實測漂移導出（1pp／該軸中位 pp/hr，"
            f"見 PACE_DRIFT_MEDIAN_PP_PER_HOUR）。"
            f"（判準：.claude/hooks/check_claim_provenance.py；關閉：AUTOSDD_PACE_GUARD_OFF=1）")
    blind = [h for h in hits if h.get("kind") == "unanchored"]
    if blind:
        out.append(
            f"ℹ️ 另有 {len(blind)} 個軸綁定讀數在本場工具輸出裡**找不到任何錨點**"
            f"（可能是輸出被截斷，也可能是憑空寫的——判準在散文平面上分不出來）。"
            f"本守衛對這一類**放行**：這是**登記的盲區，不是通過**。"
            f"累計（{FRESHNESS_TRACE}）：過期 {totals[0]} 筆／錨不到 {totals[1]} 筆。")
    return out


def main() -> int:
    # 🔴 每個判準各自一個逃生口，且**都在讀 payload 之後才分別檢查**：共用一個開關會讓
    # 「我只是想暫時別被唸這一件事」順手把另一件也關掉，而那件事沒有人會注意到。
    try:
        payload = read_hook_payload()
        claim = str(payload.get("last_assistant_message") or "")
        transcript = str(payload.get("transcript_path") or "")
        if not claim or not transcript:
            return 0
        event = str(payload.get("hook_event_name") or "Stop")
        # 🔴 M1 的夾具值。缺欄位時**當成 False**（＝會發射）：CC 只在「這一回合是 Stop hook
        # 造成的續跑」時才給 True，缺席等同第一次 ⇒ 把缺席當 True 會讓通道永遠不開。
        quiet = bool(payload.get("stop_hook_active"))
        stamped, records = _read_transcript(transcript)
        output = "\n".join(text for _when, text in stamped)
        messages: list[str] = []
        if not os.environ.get("AUTOSDD_CLAIM_GUARD_OFF"):
            hits = unsourced_verdict_hits(
                claim, output,
                unattended=bool(os.environ.get("AUTOSDD_UNATTENDED")),
            )
            if hits:
                listed = "／".join(f"{h['value']}" for h in hits[:4])
                messages.append(
                    f"🔴 這一則有 {len(hits)} 個量化判決數字（{listed}）在本場自己的工具輸出裡"
                    f"找不到出處。若是轉述別包交件，請標 `[他包回報]`；若是自己跑的，請把那次"
                    f"執行的指令與 rc 一起貼出來。（判準：.claude/hooks/check_claim_provenance.py"
                    f"；關閉：AUTOSDD_CLAIM_GUARD_OFF=1）")
        if not os.environ.get("AUTOSDD_CAUSAL_GUARD_OFF"):
            causal = error_literal_mechanism_hits(claim, output)
            if causal:
                listed = "／".join(f"`{h['literal']}`" for h in causal[:3])
                messages.append(
                    f"🔴 這一則有 {len(causal)} 句把**錯誤訊息的字面**（{listed}）當成機制"
                    f"結論。那串字是機器吐給你的**症狀**，不是你查出來的**變因**——變因必須"
                    f"有兩個不同的觀測值（R89 事故：那個量連續 15 列都是 100.0＝常數，數學上"
                    f"不可能是變因）。查證只要一行："
                    f"`python tools/probe/variate_contrast.py <落款.jsonl> --split-at <時刻>`"
                    f"（逐欄印相異值數與 CONSTANT 標記）；已經對照過就在句子裡寫出來"
                    f"（常數／變因／對照組／反例／成功組／失敗組…）即抑制。"
                    f"（判準：.claude/hooks/check_claim_provenance.py"
                    f"；關閉：AUTOSDD_CAUSAL_GUARD_OFF=1）")
        if not os.environ.get("AUTOSDD_PACE_GUARD_OFF"):
            messages += _pace_messages(
                stale_pace_hits(claim, stamped, datetime.now(timezone.utc)))
        # 🔴 執行期證據（M9）：本檔是全 repo 唯一每一則回覆都會跑、且**手上已經有逐字稿**
        # 的地方 ⇒ 「hook 載具到底有沒有解析到」這件事的自動讀者只能是它。靜態那三道結構上
        # 看不到這件事（判準面是 settings.json ＋ 檔案系統，不是執行結果），而執行期證據
        # 此前**零讀者** —— 本機全母體 217 筆 hook 失敗跨九天沒有任何東西說過一句話。
        if hook_wiring is not None and not os.environ.get("AUTOSDD_CARRIER_GUARD_OFF"):
            problems, counts = hook_wiring.runtime_carrier_verdict(
                hook_wiring.hook_result_attachments(records))
            if problems:
                messages.append(
                    "🔴 本場逐字稿的執行期證據顯示 hook **本平台自己那條載具**失敗了"
                    f"（{len(problems)} 筆；另有 {counts['by_design_fail']} 筆是跨平台配對"
                    "刻意的 fail-open、不計）。CC 對載具失敗只記一行 ERROR 就放行 ⇒ 表徵與"
                    "「修好了」完全相同。逐筆：\n    " + "\n    ".join(problems))
        _say(messages, event, quiet)
    except Exception:  # noqa: BLE001 — fail-open，見檔頭 P0
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
