# DEF-200-275 證據檔：SDD-FSM context/budget 計量表誤差與 ESCALATION 誤觸

> 本檔為 `docs/06_quality/AutoSDD_Defect_Log.md` 該列的體積守門接收端（`ROW_MAX_BYTES` 洩壓）；
> 列上只留一句話與本檔指針，逐字原文住這裡。

## 現象（2026-09-08 掌舵者直接發現）

SDD-FSM 的 context/budget 計量表長期量錯，與真實用量差 4 倍以上，且會誤觸 ESCALATION
硬鎖死全部工具呼叫：DEF-200-274 第四輪 Workflow（13 agent、125.6 萬 token）跑到一半，
FSM 自報 `INIT->AUTO_COMPACT_PENDING [auto_compact_trigger] ratio=91.11%`，隨後狀態被
推進 `ESCALATION`（R-9.5「不可自動退出」），連 `Read`/`Bash`/`Task` 等工具全數被
PreToolUse 擋下，之後又自報「context ratio 118%（cumulative=236279），下次 PreToolUse
將拒絕」；但使用者同時以內建 `/context` 指令實測**真實用量僅 29%（285.5k/1M
tokens）**，兩者差約 4 倍。

同型「hook 猜測值 vs `/context` 實測值」落差本專案已有 2 次前例（見 memory
`reference_context_window_check_via_slash_command.md` 記載 R105 967k vs 猜測 200k、
R106 猜測/實測差 4.8 倍），本次為第 3 次復發，屬結構性未修的計量錯誤，非單次偶發；且
這次額外造成**假警報升級成 ESCALATION 把整個 session／並行子 agent 全部鎖死**，代價遠
高於前兩次單純誤報。

## 建議或已採取的處置

找出 FSM 用來算 `cumulative`／`context ratio` 的計量邏輯（推測在
`AISDLC_SDD/<LATEST>/tools/fsm_runtime/` 或 `.claude/hooks/sdd_hook_router.py` 一帶），
釐清它跟真實 model context window（`/context` 可查的權威值）在分子／分母定義上的系統性
落差；修到量出來的百分比與 `/context` 同量級，而非只是拉高閾值治標；同時檢討「量錯就
自動 ESCALATION 鎖死全部工具且不可自動退出」這個懲罰是否與量測可信度不成比例。

## 狀態

> 🔴 **第一版修復已被四方獨立複審抓到區間性回歸，2026-09-10 同日訂正——見下方〈第二輪〉節。
> 本節（第一輪）逐字保留，不做靜默覆寫；「已修復」三字對第一輪修法而言不成立，讀者請以
> 〈第二輪〉狀態為準。**

**（第一輪，已訂正）已修復（2026-09-10）**：本項第 4 次復發（上一個 session 收尾 commit/push 時再次撞見，
`[SDD-CTX] TOKEN_BUDGET_CRITICAL cumulative=200994, ratio=1.00`，同一時刻使用者 `/context`
實測真實用量僅 378.8k/1,000,000＝38%）促成本輪查驗原始碼並修復。

**根因（已查驗，非猜測）**：`AISDLC_SDD/<LATEST>/.claude/hooks/context_ledger_pre.py` 與
`context_ledger_post.py` 的 `MAX_CONTEXT` 常數，在操作者未設 `SDD_MAX_CONTEXT` 環境變數
時預設寫死 `200000`——這是舊模型（Claude 3 世代）200K context window 年代的常數，現行
模型視窗常是 1,000,000。`ratio = cumulative / MAX_CONTEXT` 直接套用這個過時預設，
`cumulative` 一過 200000 就被誤判成「100% 滿」（200994/200000=1.0049，四捨五入即
`ratio=1.00`），與使用者猜測（「舊模型 20萬 token 視窗年代的常數沒跟著現在 100萬 token
視窗更新」）**核實相符**。此計量邏輯本身量的是 SDD Stage 的**估算式**預算
（`_estimate_tokens` 只看 tool_input，看不到工具輸出／subagent 回傳／對話本身），與
`.claude/hooks/context_budget_guard.py` 量的**實測**session 佔用是兩個不同分子，僅分母
的「舊模型常數不會隨模型換代更新」這一段落與本項現象吻合。

**修法**：不硬把 `MAX_CONTEXT` 改成另一個新的寫死數字（那樣換下一代模型視窗又會重演
同一個病），改比照姊妹守衛 `context_budget_guard.py` 的 `resolve_window()` 同一手法
（可證下界推論）：`context_ledger_pre.py`／`context_ledger_post.py` 新增
`_effective_max_context(cumulative)`——`MAX_CONTEXT` 未被操作者顯式釘住（`SDD_MAX_CONTEXT`
未設）且仍等於保守預設 `200_000`、而 `cumulative` 已實際觀測超過它時，改採已知的下一檔
變體 `WIDE_MAX_CONTEXT = 1_000_000`；操作者若顯式設定 `SDD_MAX_CONTEXT`（含顯式設回
`200000`），一律尊重原值、不做推論覆寫。兩個 hook 的 ratio 計算全面改走這個函式。

**回歸測試**：`tools/fsm_runtime/tests/test_context_ledger_pre_hook.py` 新增
`WideContextWindowInferenceTests`（2 個測試）：
(1) `test_real_incident_cumulative_does_not_falsely_escalate`——原樣重現本次事故數字
（`cumulative=200994`、`SDD_MAX_CONTEXT` 保證未設），驗證不再誤觸 deny／AUTO-COMPACT；
(2) `test_explicit_sdd_max_context_pin_still_denies_at_200k`——操作者顯式設
`SDD_MAX_CONTEXT=200000` 時，200994 仍正確觸發 `TOKEN_BUDGET_CRITICAL`（推論覆寫不吃掉
操作者的顯式選擇）。

**實測**（2026-09-10，`AISDLC_SDD_v0.30`，`python -m pytest`）：
- `tools/fsm_runtime/tests/test_context_ledger_pre_hook.py`：21 passed
- `tools/fsm_runtime/tests/test_context_ledger_post_hook.py`：7 passed
- `tools/fsm_runtime/tests/`（`-m "not chaos"`，全套回歸）：1746 passed, 8 skipped,
  34 deselected（chaos），無新增失敗

**判斷**：本次改動只調整 ratio 分母的計算方式，未觸及 FSM 狀態轉移本身
（`AUTO_COMPACT_PENDING`／`ESCALATION` 等狀態與觸發條件的形狀不變，只是餵給它的分母不再
是過時常數），故不需同步 `formal/SDD_FSM.tla`／重跑 TLC（R-9.18 僅在改動 `_HAPPY_PATH`
時強制）。

本項與 DEF-200-274（根層測試 runner 平行化）是兩個獨立的缺陷——DEF-200-275 只是在
DEF-200-274 第四輪的 Workflow 執行期間被撞見，兩者的修復範疇不重疊。

## 第二輪（2026-09-10 同日訂正）：四方獨立複審抓到區間性回歸

**觸發**：第一版修復送四方獨立審查（SA／SD-Architect／Developer／QA），2 位 REJECT、
2 位 APPROVE。兩位 REJECT（SA、QA）都**實際執行程式碼跑出具體數字**，而非僅憑意見分歧
判斷，證實第一版修復本身仍是同一類缺陷的區間性重演。

**破綻的機制（已自行核實，非照抄審查意見）**：第一版新增的
`_effective_max_context(cumulative)` 只有在 `cumulative` **嚴格大於** `200000` 時才把
分母切成 `WIDE_MAX_CONTEXT=1_000_000`；而 `CRIT_RATIO=0.95`，`0.95×200000=190000`——比
切換點 `200001` 早了整整一萬。`cumulative` 是單調遞增、逐步累加的，任何 session 必然先
經過 `190000~200000` 這個窗口才可能到達 `200001`。也就是說，一個真實視窗 1,000,000 的
session，在 `cumulative` 自然爬升到 190000（真實用量僅 19%）時就已經被 `ratio=0.95` 判
成 CRIT，觸發 `rt.state.record_escalation(...)`，把 FSM 狀態硬鎖進 `ESCALATION`（見
`fsm_runtime.py` 的 `_BLOCKING_STATES` 與 `AISDLC_SDD/CLAUDE.md` Rule 9 絕對禁令第 6 條
「ESCALATION 不可自動恢復」）——此時 `_effective_max_context` 的切換邏輯**還沒有機會執行
到**，因為它要 `cumulative > 200000` 才生效，而爬升到 200001 之前，session 早在 190000
就已經被鎖死。第一版修復並未真正解決原始缺陷（在某個 cumulative 值被誤判成滿版、鎖死
整個 session），只是把觸發門檻從「約 200000（100%）」往前移到「約 190000
（95%，對真實 1,000,000 視窗只是 19%）」，本質重演。

**重現**（第一版修復下的直接函式呼叫；`AISDLC_SDD_v0.30/.claude/hooks/context_ledger_pre.py`）：

```
cumulative   effective_max   ratio    (SDD_MAX_CONTEXT 未設)
170000       200000          0.85
180000       200000          0.90
190000       200000          0.95   ← 第一版在這裡就已誤觸 CRIT/ESCALATION
199999       200000          1.00
200000       200000          1.00
200001       1000000         0.20   ← 切換生效，但已經太晚
```

**訂正方向（已核實姊妹守衛的實際邏輯，非照抄審查員說法）**：讀了
`.claude/hooks/context_budget_guard.py` 的 `resolve_window()`／`may_block()` 後確認：
`resolve_window()` 依優先序回傳 `(window, source)`，`source` 有六種
（`SOURCE_PINNED`／`SOURCE_PINNED_CC_ENV`／`SOURCE_PINNED_CC_SETTING`／
`SOURCE_MODEL_MARKER`／`SOURCE_INFERRED_WIDE`／`SOURCE_INFERRED_FLOOR`）；`may_block(source)`
的定義是 `source != SOURCE_INFERRED_FLOOR`——也就是說**只有「保守下界猜測」
（`SOURCE_INFERRED_FLOOR`，未顯式設定且尚未觀測到用量超過保守預設）不准拿去硬擋**，
其餘五種來源（含已推得「用量已超過保守預設、下界必然是寬視窗」的 `SOURCE_INFERRED_WIDE`）
都**准許**硬擋——因為那個方向的猜測只會讓阻斷「晚」發生（安全），不會在真實低用量時
誤擋。這與最初審查說法「只要分母來源還是『未確認的保守下界』就不准硬擋」一致，且核實後
確認精準。

依此語意移植到 `context_ledger_pre.py`／`context_ledger_post.py`：新增
`_max_context_confirmed(cumulative)`——`True`（可以硬擋）有兩種情形：①操作者已顯式設定
`SDD_MAX_CONTEXT`（即使值恰好等於保守預設 200000，仍尊重操作者的選擇）；②未顯式設定但
`_effective_max_context(cumulative)` 已經因為 `cumulative > 200000` 而切到
`WIDE_MAX_CONTEXT`（可證的下界推論，不再是純猜測，對應 `SOURCE_INFERRED_WIDE`）。`False`
只有一種情形（對應 `SOURCE_INFERRED_FLOOR`）：未顯式設定、且 `cumulative` 仍未超過
200000——此刻 200000 純粹是「還沒證據」的保守猜測，CRIT／AUTO_COMPACT 分支在此狀態下
**降級為 `additionalContext` 警告，不呼叫 `record_escalation`、不 deny、不
`trigger_auto_compact`**；FSM 狀態不變。這對應任務書方向 (a)。

**改了哪些檔案**：
- `AISDLC_SDD/AISDLC_SDD_v0.30/.claude/hooks/context_ledger_pre.py`——新增
  `_max_context_confirmed()`／`_unconfirmed_notice()`；zero-token 短路分支與正常
  append 分支的 CRIT／AUTO_COMPACT 判定前都加上 `confirmed` 閘。
- `AISDLC_SDD/AISDLC_SDD_v0.30/.claude/hooks/context_ledger_post.py`——同構新增；
  `AUTO_COMPACT`（`trigger_auto_compact` 呼叫點）與 `CRIT` 訊息分支都加上 `confirmed` 閘。
- 兩支對應的 `tools/fsm_runtime/tests/test_context_ledger_pre_hook.py`／
  `test_context_ledger_post_hook.py`——新增回歸測試（見下）。

**回歸測試（新增，覆蓋自然爬升路徑，非單點 seed）**：

- `MaxContextConfirmedUnitTests`（pre／post 各一份，共 6 個測試）：直接對
  `_max_context_confirmed()` 做邊界值單元測試——未顯式設定時 `{0,170000,180000,190000,
  199999,200000}` 皆 `False`，`{200001,250000,500000,999999}` 皆 `True`；顯式設定時
  任何 cumulative 皆 `True`（含恰好等於 200000）。
- `DEF200275NaturalClimbTests`（pre／post 各一份，共 4 個測試）：
  - `test_natural_climb_never_escalates_when_denominator_unconfirmed`（pre）／
    `test_natural_climb_never_locks_fsm_when_denominator_unconfirmed`（post）：
    模擬 cumulative **依序**爬過 `170000 → 180000 → 190000 → 199999 → 200000 →
    200001 → 250000`（`SDD_MAX_CONTEXT` 保證未設，非事後單點 seed 200994——本輪
    正是要抓「爬升路徑中途」而非「已經爬到很大」的破口），每一步都用同一個
    `FSMRuntime` 實例斷言 `state.current` 全程停在 `SPEC_DRAFTING`（從未被鎖進
    `ESCALATION`／`AUTO_COMPACT_PENDING`），且回應中從未出現 `permissionDecision:
    deny`。
  - `test_explicit_pin_still_escalates_at_190000`（pre）／
    `test_explicit_pin_still_triggers_auto_compact_at_180000`（post）：對照組——
    操作者顯式設定 `SDD_MAX_CONTEXT=200000` 時，190000/200000=95%（pre）／
    180000/200000=90%（post）仍必須正常觸發 `TOKEN_BUDGET_CRITICAL`／
    `ESCALATION`／`AUTO_COMPACT_PENDING`，證明訂正沒有連帶拆掉操作者顯式選擇小
    視窗時的正常防護。

**實測**（2026-09-10，`AISDLC_SDD_v0.30`，`source .venv/bin/activate` 後跑）：

```
$ python -m pytest tools/fsm_runtime/tests/test_context_ledger_pre_hook.py tools/fsm_runtime/tests/test_context_ledger_post_hook.py -q
38 passed in 0.30s

$ python -m pytest tools/fsm_runtime/tests/ -m "not chaos" -q
1756 passed, 8 skipped, 34 deselected, 14 subtests passed in 22.06s
```

（`--collect-only` 核對：pre 檔本輪 26 個測試＝第一輪既有 21 個 + 本輪新增 5 個
〔`MaxContextConfirmedUnitTests` 3 個 + `DEF200275NaturalClimbTests` 2 個〕；post 檔
本輪 12 個測試＝第一輪既有 7 個 + 本輪新增 5 個〔同構〕；26+12=38，與實測數字相符。
全套 `-m "not chaos"` 前一輪基線 1746 passed，本輪新增 10 個測試，1746+10=1756，
與實測數字相符，無新增失敗。）

**修復過程中的踩坑記錄（誠實留痕，非隱藏）**：本輪為 `context_ledger_post.py` 新增
的兩個 `DEF200275NaturalClimbTests` 測試最初撰寫時未顯式覆寫 `SDD_HOOKS_DISABLE`
環境變數，而本開發環境的 ambient shell 本身設有 `SDD_HOOKS_DISABLE=1`（見 repo
memory〈Bash工具shell state不持續+zshrc污染〉），導致 hook 在測試中整支被跳過、
測試斷言的其實是「沒做任何事」而非「訂正邏輯生效」——其中一個測試因為斷言內容較弱
（只查 FSM 狀態未變）而**表面碰巧通過**、另一個測試（斷言 `additionalContext` 含
`AUTO-COMPACT`）因為 hook 被跳過而正確地紅了，因此被抓到並訂正（兩處測試皆已顯式加入
`"SDD_HOOKS_DISABLE": ""` 覆寫）。記此教訓：涉及 hook 行為的測試務必顯式覆寫全部
「靜默停用」類環境變數，不能只信任 `clear=True`／`dict(os.environ)` 快照。

**重新驗證 190000~200000 這個具體區間**（比照使用者提供的重現腳本，跑一次確認新版
行為）：

```
$ source .venv/bin/activate
$ python3 -c "
import sys; sys.path.insert(0, 'AISDLC_SDD/AISDLC_SDD_v0.30/.claude/hooks')
import context_ledger_pre as m
for cum in (170000,180000,190000,195000,199999,200000,200001,200994,250000,500000,950000,999999):
    eff = m._effective_max_context(cum)
    conf = m._max_context_confirmed(cum)
    ratio = cum/eff
    print(cum, eff, round(ratio,4), 'confirmed=', conf, 'CRIT-would-fire=', ratio>=m.CRIT_RATIO and conf)
"
170000 200000 0.85   confirmed=False CRIT-would-fire=False
180000 200000 0.9    confirmed=False CRIT-would-fire=False
190000 200000 0.95   confirmed=False CRIT-would-fire=False   ← 第一版在此誤觸；新版不再誤觸
195000 200000 0.975  confirmed=False CRIT-would-fire=False
199999 200000 1.0    confirmed=False CRIT-would-fire=False
200000 200000 1.0    confirmed=False CRIT-would-fire=False
200001 1000000 0.2   confirmed=True  CRIT-would-fire=False
200994 1000000 0.201 confirmed=True  CRIT-would-fire=False
250000 1000000 0.25  confirmed=True  CRIT-would-fire=False
500000 1000000 0.5   confirmed=True  CRIT-would-fire=False
950000 1000000 0.95  confirmed=True  CRIT-would-fire=True   ← 真實 95% 用量，正常觸發
999999 1000000 1.0   confirmed=True  CRIT-would-fire=True
```

以及顯式 pin 對照組（`SDD_MAX_CONTEXT=200000`）：

```
170000 200000 0.85 confirmed=True CRIT-would-fire=False
180000 200000 0.9  confirmed=True CRIT-would-fire=False
190000 200000 0.95 confirmed=True CRIT-would-fire=True   ← 操作者顯式選小視窗，正常觸發
```

**把握程度**：整條 170000→250000 自然爬升路徑（新增回歸測試）與直接函式呼叫
（上方重新驗證區塊）雙重確認，190000~200000 這個第一版曾誤觸的窗口在新版下
`confirmed=False`，CRIT 分支降級為警告、不記 `ESCALATION`；顯式 pin 對照組確認
未連帶拆除操作者主動選擇小視窗時的正常防護。有信心此區間性回歸已解決，但誠實
補充：本輪驗證範圍限於 pre／post 兩支 hook 的 CRIT／AUTO_COMPACT 分支本身，未
覆蓋 `fsm_runtime.py::trigger_auto_compact` 內部 per-stage 上限超過時的 escalate
分支（那是既有邏輯，本輪未改動，也未在新增測試中特別驗證其與 `confirmed` 閘的交互——
但該分支只在已經進入 `AUTO_COMPACT_PENDING` 之後才可能觸發，而 `confirmed=False`
時本輪修法已阻止進入 `AUTO_COMPACT_PENDING`，故邏輯上不會被觸及）。

## 第三輪（2026-09-10 同日訂正）：`_SDD_MAX_CONTEXT_PINNED` 只問「有沒有設」不問「解析成不成功」

**觸發**：第二輪修復送四方獨立複審，結果 3 APPROVE、1 REJECT。但兩位投 APPROVE 的
審查員（QA、SA）**各自獨立**在程式碼中發現了同一個具體漏洞，只是判斷「不阻斷、可下輪
再修」；投 REJECT 的架構師審查員判定這個漏洞後果嚴重（與 DEF-200-275 原始 bug 同一種
「未經確認的分母被拿去硬擋」路徑重演），現在就該修掉，不宜留到下一輪。三位獨立審查員
（含判定不同嚴重度的兩派）分別在程式碼中撞見同一行，足以確認這不是誤判。

**破綻的機制（已自行核實，非照抄審查意見）**：`context_ledger_pre.py`／
`context_ledger_post.py` 兩支檔案裡：

```python
_SDD_MAX_CONTEXT_PINNED = os.environ.get("SDD_MAX_CONTEXT") is not None
```

這一行只檢查環境變數「有沒有被設定」，沒檢查「設定的值能不能被成功解析成一個有效的
正整數」。而緊接在它上面、解析 `_RAW_MAX_CONTEXT` 的 try/except 區塊，本身已經正確地把
`"abc"`／`"1.5"`／`"12k"`／空字串／`"0"`／`"-5"` 這組壞值 fallback 回保守預設
`200000`（`MaxContextGuardTests`／`MaxContextFloorTests` 兩個既有測試類別已驗證這一半
沒問題）。但 `_SDD_MAX_CONTEXT_PINNED` 卻只因為「環境變數有設（即使是打錯的壞值）」就被
判定為 `True`（已釘住／已確認），導致 `_max_context_confirmed()` 在這種情況下恆為
`True`——`cumulative` 在 190000（若真實視窗是 1,000,000，僅約 19% 用量）時，會被當成
「操作者刻意選的小視窗」正確地觸發真 CRIT/ESCALATION，但操作者其實只是打錯字，不是真
的選了小視窗。這正是 DEF-200-275 原始 bug（誤鎖進不可恢復的 ESCALATION）的第三種重演
路徑（第一輪：過時常數當滿版；第二輪：切換點早於 CRIT 門檻；第三輪：壞值被誤判成
「已釘住」）。

**重現（修復前）**：

```
$ source .venv/bin/activate
$ cd AISDLC_SDD/AISDLC_SDD_v0.30   # 任務書實際路徑為 monorepo 根，此處等價換算
$ SDD_MAX_CONTEXT=abc python3 -c "
import sys; sys.path.insert(0, '.claude/hooks')
import context_ledger_pre as m
print('MAX_CONTEXT=', m.MAX_CONTEXT)
print('_SDD_MAX_CONTEXT_PINNED=', m._SDD_MAX_CONTEXT_PINNED)
print('confirmed@190000=', m._max_context_confirmed(190000))
"
MAX_CONTEXT= 200000
_SDD_MAX_CONTEXT_PINNED= True     ← 錯誤：值根本沒解析成功
confirmed@190000= True            ← 連帶錯誤：190000（19% 真實用量）會被硬鎖
```

**核實姊妹守衛判準（已讀 `.claude/hooks/context_budget_guard.py` 原始碼，非照抄審查
說法）**：`_positive_int(raw)`（第 477~484 行）「能讀成正整數就回它，否則回 0」；
`resolve_window()`（第 525~559 行）判斷「這是不是一個有效的顯式指定值」時，對
`env_raw`／`cc_window_raw`／`settings_window` 三個候選來源一律先算
`pinned = _positive_int(raw)`，只有 `pinned > 0`（解析成功**且**為正整數）才回傳該來源
當作「指定值」（`SOURCE_PINNED` 等），否則不採用、繼續往下一階推論。核實與任務書描述一致：
姊妹守衛從未把「環境變數存在」本身當成「已指定」的判準，一律要求解析成功。

**修法**：把 `_SDD_MAX_CONTEXT_PINNED` 的判定跟 `_RAW_MAX_CONTEXT` 那段既有 try/except
的解析結果掛鉤，而不是重新用 `os.environ.get(...) is not None` 猜一次。具體做法（兩支
檔案 symmetric）：

```python
try:
    _RAW_MAX_CONTEXT = int(os.environ.get("SDD_MAX_CONTEXT", "200000"))
    _RAW_MAX_CONTEXT_PARSE_OK = True
except (TypeError, ValueError):
    _RAW_MAX_CONTEXT = 200000
    _RAW_MAX_CONTEXT_PARSE_OK = False
MAX_CONTEXT = _RAW_MAX_CONTEXT if _RAW_MAX_CONTEXT > 0 else 200000

_SDD_MAX_CONTEXT_PINNED = (
    os.environ.get("SDD_MAX_CONTEXT") is not None
    and _RAW_MAX_CONTEXT_PARSE_OK
    and _RAW_MAX_CONTEXT > 0
)
```

三個條件缺一不可：①環境變數必須真的有設（否則「未設」本來就該是 `False`，不能因為
`_RAW_MAX_CONTEXT_PARSE_OK` 在未設時也是 `True` 而誤判）；②解析過程沒有拋
`TypeError`/`ValueError`（排除 `"abc"`／`"1.5"`／`"12k"`／空字串這類非數字壞值）；
③解析出來的值是正整數（排除 `"0"`／`"-5"` 這類數字但非法的壞值——`int()` 對它們不會
拋例外，必須額外靠 `> 0` 排除）。這與姊妹守衛 `_positive_int(raw) > 0` 的語意等價，只是
複用了本檔既有的解析結果，不重新猜一次。

**改了哪些檔案**：
- `AISDLC_SDD/AISDLC_SDD_v0.30/.claude/hooks/context_ledger_pre.py`——`_RAW_MAX_CONTEXT`
  解析區塊新增 `_RAW_MAX_CONTEXT_PARSE_OK` 旗標；`_SDD_MAX_CONTEXT_PINNED` 判準改掛鉤該
  旗標＋正整數檢查；WHY 註解同步補上第三輪脈絡。
- `AISDLC_SDD/AISDLC_SDD_v0.30/.claude/hooks/context_ledger_post.py`——同構修改。
- `AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/tests/test_context_ledger_pre_hook.py`——
  `MaxContextConfirmedUnitTests` 新增 `test_malformed_pin_at_190000_is_unconfirmed`
  （壞值集合 `"abc"`／`"1.5"`／`"12k"`／`""`／`"0"`／`"-5"` 逐一斷言
  `_SDD_MAX_CONTEXT_PINNED is False` 且 `_max_context_confirmed(190000) is False`）與
  `test_valid_pin_at_190000_is_confirmed`（對照組：有效正整數 `"200000"` 仍正確回傳
  `True`）。
- `AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/tests/test_context_ledger_post_hook.py`——
  同構新增兩個測試。

**實測**（2026-09-10，`AISDLC_SDD_v0.30`，`source .venv/bin/activate` 後跑）：

```
$ python -m pytest tools/fsm_runtime/tests/test_context_ledger_pre_hook.py tools/fsm_runtime/tests/test_context_ledger_post_hook.py -q
42 passed in 0.25s

$ python -m pytest tools/fsm_runtime/tests/ -m "not chaos" -q
1760 passed, 8 skipped, 34 deselected, 14 subtests passed in 20.42s
```

（`--collect-only` 核對：pre 檔本輪 28 個測試＝第二輪既有 26 個 + 本輪新增 2 個；post
檔本輪 14 個測試＝第二輪既有 12 個 + 本輪新增 2 個；28+14=42，與實測數字相符。全套
`-m "not chaos"` 前一輪基線 1756 passed，本輪新增 4 個測試，1756+4=1760，與實測數字
相符，無新增失敗。8 skipped／34 deselected 與前一輪相同，皆與本缺陷無關的既有站點。）

**重現（修復後，任務書給定的重現腳本，逐值跑過整組壞值＋對照組）**：

```
$ source .venv/bin/activate
$ cd AISDCL_Agent
$ for v in abc 1.5 12k "" 0 -5 200000; do
SDD_MAX_CONTEXT="$v" python3 -c "
import sys; sys.path.insert(0, 'AISDLC_SDD/AISDLC_SDD_v0.30/.claude/hooks')
import context_ledger_pre as m
print('v=$v', 'MAX_CONTEXT=', m.MAX_CONTEXT, '_SDD_MAX_CONTEXT_PINNED=', m._SDD_MAX_CONTEXT_PINNED, 'confirmed@190000=', m._max_context_confirmed(190000))
"
done
v=abc     MAX_CONTEXT= 200000 _SDD_MAX_CONTEXT_PINNED= False confirmed@190000= False
v=1.5     MAX_CONTEXT= 200000 _SDD_MAX_CONTEXT_PINNED= False confirmed@190000= False
v=12k     MAX_CONTEXT= 200000 _SDD_MAX_CONTEXT_PINNED= False confirmed@190000= False
v=        MAX_CONTEXT= 200000 _SDD_MAX_CONTEXT_PINNED= False confirmed@190000= False
v=0       MAX_CONTEXT= 200000 _SDD_MAX_CONTEXT_PINNED= False confirmed@190000= False
v=-5      MAX_CONTEXT= 200000 _SDD_MAX_CONTEXT_PINNED= False confirmed@190000= False
v=200000  MAX_CONTEXT= 200000 _SDD_MAX_CONTEXT_PINNED= True  confirmed@190000= True   ← 對照組：有效顯式設定仍正常釘住
```

`context_ledger_post.py` 以同一組值逐一覆核，結果與上表逐字相同（symmetric 修法，見上）。

**判斷**：本次改動只調整「pinned 判準」本身的計算方式（從「環境變數是否存在」改為
「環境變數存在且能被成功解析為有效正整數」），未新增 FSM 狀態、未觸及狀態轉移的形狀，
故不需同步 `formal/SDD_FSM.tla`／重跑 TLC（R-9.18 僅在改動 `_HAPPY_PATH` 時強制）。

**把握程度**：任務書指定的六個壞值（`"abc"`／`"1.5"`／`"12k"`／空字串／`"0"`／`"-5"`）
與有效值對照組（`"200000"`）皆有回歸測試逐一釘住，且用任務書原始重現腳本逐值實測驗證，
pre／post 兩支 hook 皆已核實。已知範圍限制（誠實揭露，非隱藏）：本輪未窮舉「解析成功
但為極端數值」的邊界（例如超大整數字串、含前後空白的數字字串如 `" 200000 "`——Python
`int()` 本身會 strip 空白成功解析，行為與姊妹守衛一致，屬設計內而非本輪修復範圍）；亦
未變動 `_effective_max_context()` 本身（第二輪已核實的下界推論邏輯不受本輪影響，因為
本輪只動了 `_SDD_MAX_CONTEXT_PINNED` 的計算來源，未動它被消費的位置）。


## 第四輪（2026-09-10 同日；第三輪宣稱 fixed 後第 5 次復發）：分子量錯東西、帳本自己灌水、懲罰錯層級

### 觸發（掌舵者原話逐字）

1. 「我用終端 claude 都會出現以下問題，才開新視窗，就說他被擋不能寫檔案用工具了，然後也不去查真實的數據」
2. 「模型都不用真實的 /context 或 API 去查真實數據」
3. 「請讓他使用正確的 API 去查 context」（本輪中途再次強調 ⇒ 硬性設計約束）
4. 「省去非必要文件，只留一定需要文件」

復發史：`archive/FSM-STATE-AISDLC_SDD-escalated-2026-09-10.yaml` 顯示 09-08、09-09 各誤觸一次；09-09 06:07 人工走
`ESCALATION→RESUME_VERIFICATION→SPEC_DRAFTING` 恢復後 09-09 16:19 又誤觸；09-10 01:52 UTC 第 5 次
（`escalation_history[-1].trigger_reason="TOKEN_BUDGET_CRITICAL: cumulative=993581 ratio=0.99"`，`auto_compact_state.resume_state="INIT"`）。

### 現場實測（第四輪開工時，本 session）

| 量 | 值 | 來源 |
|---|---|---|
| 真實 context 佔用（API usage） | 開工時 97,184；本輪收尾實測 **430,428** tokens（`input+cache_creation+cache_read`） | 逐字稿 `~/.claude/projects/-Users-wuweihong-Antigravity-AISDCL-Agent/8d8773f9-….jsonl` 最後一筆 `type=="assistant"` 的 `message.usage`；2.19MB 全掃 0.011s |
| 真實視窗 | 1,000,000（`claude-fable-5-1`）；使用者 settings 另釘 `AUTOSDD_CONTEXT_WINDOW=967000` | Models API `max_input_tokens`（claude-api skill 快取表 2026-06-24 核實）／`~/.claude/settings.json` |
| SDD hook 自報 | session 一開始 `[SDD-CTX][CRIT] context ratio 119% (cumulative=1190753)`；每叫一次 Bash **+3 萬**；40 分鐘後 `240% (cumulative=2396191)` | PostToolUse additionalContext |
| 今日帳本 | `cumulative_tokens=1,586,885`，215 entries；`phase=conv-overhead` 80 筆共 1,466,400（**92%**），單筆 30000, 30300, 30600…（每次 +300） | `build/reports/fsm/CONTEXT-LEDGER-2026-09-10.yaml`（已於 06:24:17Z 被新 hook 依設計 rotate 為 `.corrupt-20260910T062417370815Z.yaml`，見〈把握程度〉） |
| 第三輪遺留測試 | `ZeroTokenEscalationTests` 2 failed／58 passed（本場基線實跑：`2 failed, 58 passed in 0.38s`） | 根因＝本機 `~/.claude/settings.json` 的 `model=claude-fable-5-1[1m]` 與 `AUTOSDD_CONTEXT_WINDOW=967000` 污染測試（C12） |

### 根因 A（分子灌水）：帳本 read-modify-write 弄丟 `conversation_overhead` 書籤 — 本場在**未修改的舊 pre hook**上直接重現

```
merge#1 -> {'merged': True, 'added_tokens': 3300, 'cumulative': 5500, 'sidecar_merged': 0} | bookmark = 22
after OLD pre-hook _append_ledger -> top-level keys = ['cumulative_tokens', 'date', 'entries'] | bookmark = None
merge#2 -> {'merged': True, 'added_tokens': 3600, 'cumulative': 9101, 'sidecar_merged': 0}   <== 根因 A 重現：書籤遺失後立即再合併
```

機制：pre/post 兩支 hook 各自的 `_read_modify_write` 重寫整份 doc 時只保留 `{date, cumulative_tokens, entries}`，
`conversation_overhead.last_merge_entry_index` 消失 ⇒ `merge_conversation_overhead_into_ledger` 每次都從 0 起算、把全部
entries 再合併一次 ⇒ `+ (len/2)*300`、單調遞增（O(n²)）。**A-2（撕裂寫入）**：所有寫入者共用同名 `.tmp`，兩支並行 hook 的
`os.replace` 互相搬走對方半寫的檔 ⇒ 活帳本出現半截 `t: null` 行（L1606），hook 自 02:23:52 UTC 起 `yaml.safe_load` crash → fail-open。

### 根因 B（量錯東西）：`cumulative_tokens` 是「當天所有 session 的估算式 I/O 總和」

帳本按日期命名、跨 session 共用、單調遞增、compaction 後不下降。新開 session 真實 context ~5 萬卻繼承同日別的 session 的
119 萬 ⇒ 開場即 CRIT——這就是原話①。分母上輪已修對（1M）；**本輪錯的是分子**。

### 根因 C（懲罰錯層級）：session 級的 context 事件寫進專案級、跨 session 黏著的 `ESCALATION`

`record_escalation()` 把 `state.current="ESCALATION"` 寫進專案唯一的 FSM-STATE；R-9.5「ESCALATION 不可自動退出」⇒ 下一個
全新 session（視窗全空）開場就被 PreToolUse 全擋。SessionStart 只印「必須人工介入」，沒有可執行的指令。

### 裁決 D1~D10（總架構師定案；被否決意見括註）

- **D1 分子**＝逐字稿最後一筆 assistant `usage` 三欄和，跳過 `<synthetic>`；每次全檔掃描（子字串預篩、O(1) 記憶體）；最後一個
  `compact_boundary` 落在最後 usage 之後 ⇒ `used=None`。（否決 offset 快取：本場 2.19MB 實測 0.011s、5MB 合成夾具實測 <2s 上界，8s timeout 餘裕兩個數量級；記為「量到 >1s 才啟用的備案」。）
- **D2 分母鏈**：`SDD_MAX_CONTEXT` → `AUTOSDD_CONTEXT_WINDOW` → `CLAUDE_CODE_AUTO_COMPACT_WINDOW`／settings `autoCompactWindow`
  → model `[1m]`／`-1m` 標記（交叉否決）→ **Models API `max_input_tokens` 查表**（`data/known_model_windows.json`，刷新腳本
  `refresh_known_model_windows.py` 只用官方 SDK、hook 路徑永不打網路、SDK 缺席 rc=2 不寫檔）→ `peak>200K` 可證下界 → 保守值（只出聲）。
- **D3 ≥95%**：不再寫專案級 ESCALATION／TOKEN_BUDGET_CRITICAL；`trigger_auto_compact`＋以既有 `_assert_allowed_under_auto_compact`
  判當次工具（白名單放行附 CRIT 訊息、否則 deny）。（否決 SA／SD／Developer「保留進 ESCALATION、靠一行指令恢復」：context window 是
  session 的屬性、FSM-STATE 是專案的屬性；R-9.5 規範「進入之後」不規範「誰可以進」，語意零弱化。）per-stage cap 超限仍走既有結構性升級。
- **D4 PENDING 出口**：`used < 0.85×window`（遲滯帶）⇒ `complete_auto_compact(observed_effective=True)`；`resume_state` 非法（活狀態 `INIT`）
  ⇒ remap `SPEC_DRAFTING` 並註明；`observed_effective` ⇒ `count_per_stage` 歸 0（ACT-026 cap 語意收斂為「只對從未觀測到有效壓縮的連續觸發生效」）。
  （否決「boundary 出現即出口」：boundary 出現但 used 仍 ≥85% 代表壓縮沒解決問題。）
- **D5 帳本**降為稽核／校準：entry 加 `session_id／observed_used／window／window_source`；`append_ledger_entry` 合併兩支 hook 的複本並保留
  其餘鍵；書籤缺失且已有 conv-overhead 列 ⇒ rebaseline 不合併（全新帳本照舊從 0）；tmp 一律 `.part.<pid>`；merge 進同一把鎖；損毀
  ⇒ rotate `.corrupt-<UTC ts>.yaml`；帳本 I/O 例外永不到 `main()`；刪 pre 的 `_read_cumulative` 與 tokens==0 分支。
- **D6 人工恢復**：`FSMRuntime.resume_from_escalation(to, reason)` ＋ CLI `resume-from-escalation --to <STATE> --reason`（兩跳皆 `trigger=human_resume`，
  回填 `escalation_history[-1].resolved_at／resolution`）；`recovery_hint.py` 印來源 session／類別／原因／時間＋一行指令（`;` 三殼通用；PowerShell 加 `& `）。
  （否決 `&&` 串接：PS 5.1 無 `&&`。）
- **D6b** `record_escalation(reason, *, details=None)`／`trigger_auto_compact(..., details=None)`：None 時鍵集合逐字不變。
- **D7 文件**嚴格 C13；**D8 整合閘門** if/elif 三候選鏈；**D9 根層 parity 測試**（不 skip、含 bug-injection 自證）；**D10** 撤回 settings.json 的 `SDD_MAX_CONTEXT=1000000` 裸常數、刪 `detect_model_wide_hint` 家族。

### 修法逐檔

| 檔 | 改動 |
|---|---|
| `SDD/tools/fsm_runtime/context_window.py`（重寫，納入版控） | 量測＋分母鏈＋門檻常數唯一的家；八個來源字串；`measure()`／`window_evidence()` I/O 收口 |
| `SDD/tools/fsm_runtime/data/known_model_windows.json`（新）＋ `refresh_known_model_windows.py`（新） | Models API 查表與離線刷新 |
| `SDD/tools/fsm_runtime/conversation_ledger.py` | `append_ledger_entry`／`ledger_lock`／`_load_ledger_doc`（rotate）／`_atomic_write_yaml`（pid tmp）；merge 進鎖＋rebaseline |
| `SDD/tools/fsm_runtime/fsm_runtime.py` | `trigger_auto_compact(details)`；`complete_auto_compact(observed_effective, remap)`；`resume_from_escalation`；CLI 子命令；`_reset_today_ledger` pid tmp |
| `SDD/tools/fsm_runtime/state_loader.py` | `record_escalation(details=None)` |
| `SDD/tools/fsm_runtime/recovery_hint.py`（新） | 一行恢復指令 |
| `SDD/.claude/hooks/context_ledger_pre.py`／`context_ledger_post.py`（重寫） | 分子＝真實 usage；D3／D4；稽核帳本零決策權；零 `200000` 字面值 |
| `SDD/.claude/hooks/session_start.py` | 讀 payload；`[SDD-CTX] 量測＝…` 一行；BLOCK 訊息接 `recovery_hint` |
| `SDD/.claude/settings.json` | 撤回 `SDD_MAX_CONTEXT` |
| `SDD/workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md`／`governance/rules/R-9.2-context-budget.yaml` | 規格同步（見下） |
| `ROOT/tools/integration_gate.sh`＋`tools/check_wrapper_thinness.py` | 候選鏈＋重釘 hash `d5a8c9ca…f44f69b` |
| `ROOT/tools/tests/test_context_window_parity.py`（新）＋`tools/lib/skip_tag_policy.py` | parity 鎖＋`_TREE_FILE_FLOORS` 重釘（55→56、60→62，依判準訊息） |
| `SDD/tools/fsm_runtime/tests/test_session_start_rules.py` | BLOCK 訊息含恢復指令／量測來源行的回歸鎖（隔離 runtime＋patch scan_inbox） |
| `ROOT/tools/tests/test_adr_xplat001_c1c2_lock.py` | guard-line 棘輪重釘 R143 列（96506→96671→96744）＋`_REGRESSION_LANE_LOG` 同輪列＋`_FROZEN_PREFIX_REWRITE_LEDGER` 鏈列＋`_REPIN_NET_CAP_SCHEDULE` 到期兌現 |
| `ROOT/tools/tests/test_platform_neutral_paths.py` | `_DIRENT_UNGUARDED_DEBT` 42→40 下修（三個 `os.replace` 站點收斂為 `_atomic_write_yaml`） |
| `ROOT/docs/04_planning/AutoSDD_improving_112.md` | 寄居列：本輪 doc-total 站點登記（依 `run_root_unittests.py` 判準訊息） |
| `ROOT/docs/06_quality/CrossPlatform_R143_Scan_Findings.md`（新）＋`tools/lib/governance_docs.py` | R143 護欄層對帳逐檔清單；F1 補登記進 `_GOVERNANCE_DOCS`（漏登記時 `check_defect_log_crossref.py` rc=1 早退） |
| **第 1 輪審查修復**：`SDD/tools/fsm_runtime/conversation_ledger.py`／`.claude/hooks/context_ledger_post.py` | F2：抽出 `_write_sidecar`／`write_sidecar`（零取鎖）；post hook 逾時降級不再進 `append_ledger_entry` 二次取鎖（實測 10.07s→<8s）；SD-05 負整數書籤視同缺失 |
| **第 1 輪審查修復**：`SDD/tools/fsm_runtime/fsm_runtime.py` | F2：`_reset_today_ledger` 走 `ledger_lock`＋`_load_ledger_doc`（rotate）＋`_atomic_write_yaml`；`complete_auto_compact` 包 try/except 回 `ledger={"reset": False, "error": …}`、新增 `released_by`（ARCH-03）；`RESUME_TARGETS` 搬回核心（ARCH-04）；decision_trace 印 `used=／source=`（ARCH-05）；CLI 成功後 stderr 全 ASCII 提醒移除 `SDD_HOOKS_DRY_RUN=1`（SA-R4-08） |
| **第 1 輪審查修復**：`SDD/tools/fsm_runtime/recovery_hint.py`／`context_window.py`／兩支 hook | F3：`pythonw.exe`→同目錄 `python.exe`（存在才換，`exists` 可注入）＋兩殼各一行（PowerShell `Set-Location …; & "<py>" …`）；ARCH-07 `repo_root()` 退路 `parents[4]`→`parents[2]`；ARCH-06 `[NOOP]` 訊息與 CRIT deny 依狀態分句；DONE 訊息帶 `released_by_session／triggered_by_session` |
| **第 1 輪審查修復**：`ROOT/tools/tests/test_find_git_bash_parity.py`＋`SDD_FSM_ENGINE.md` | SA-R4-03 候選鏈三案（`WindowsApps/` 目錄遮蔽法，+60；bug-injection 自證 2 紅）；SA-R4-07 狀態圖 `95% HARD-STOP`→`95% SESS-DENY`（同寬，parser 只掃〈狀態轉換表〉節） |
| **第 2 輪審查修復**：`SDD/tools/fsm_runtime/fsm_runtime.py` | G1（QA-R2-01／ARCH-R2-01／SD-R2-02 三方實測 ≈10s）：`_reset_today_ledger(*, lock_timeout=1.0)`，逾時回 `lock_timeout=True`（帳本零決策權；PENDING 出口單支 hook 最壞 5+1=6s < router 8s）；G4：`_load_ledger_doc` 拋 OSError ⇒ 回 `reset=False`＋`error`，不覆寫 |
| **第 2 輪審查修復**：`SDD/tools/fsm_runtime/conversation_ledger.py` | G3（SD-R2-01，HEAD 既有）：`_merge_locked` 早退前 `if sidecar_merged: _atomic_write_yaml`（折回真的持久化，回傳帶 `sidecar_merged`）；G4（SD-R2-03，本輪 delta 引入）：`_load_ledger_doc` 讀檔 OSError **re-raise**（讀不到 ≠ 空帳本），`append_ledger_entry` 接住回 0、`merge_*` 回 `io_error`；`_write_sidecar`／`append_ledger_entry` docstring「折回」宣稱改為實際行為 |
| **第 2 輪審查修復**：`SDD/tools/fsm_runtime/recovery_hint.py` | SA-R4-09＝SD-R2-04：`safe_reason = re.sub(r'["$`\\]', "'", reason)`（兩殼雙引號都會對 `$`／反引號插值） |
| **第 2 輪審查修復**：`SDD/tools/fsm_runtime/tests/test_e2e_smoke.py` | G2（ARCH-R2-02，既有非本輪）：S10 改 patch `state_loader.REPO_ROOT`／`snapshot.SNAPSHOT_DIR` 到 tmp，刪 backup／覆蓋回寫（不再碰活帳本；意圖與斷言不動） |
| **第 2 輪審查修復**：`SDD/tools/fsm_runtime/tests/test_context_ledger_{pre,post}_hook.py`／`test_conversation_ledger.py`／`test_recovery_hint.py` | 回歸鎖 +7：pre／post PENDING 出口鎖競爭計時各 1（QA 探針收編，LEDGER_DIR＝REPO_ROOT/build/reports/fsm 同目錄）；post `LockTimeoutDegradationTests` 加「降級 entry 下次 merge 後真的在磁碟上」斷言；sidecar 未達門檻仍持久化；不可讀帳本不覆寫（append／merge／reset 三面，`Path.open` 注入而非 chmod 000——root 與 Windows 都會假綠）；reset 等鎖 1s 上界；reason 中和 `$`／反引號／反斜線 |

### 規格改句 before／after

- `SDD_FSM_ENGINE.md` AUTO_COMPACT_PENDING `exit_on`：「stage-compaction Skill 完成」→「stage-compaction Skill 完成，或 hook 於下一次工具呼叫觀測到本 session 逐字稿 API usage 已回落 < 85% window（Claude Code 自動 compaction 亦視為完成；DEF-200-275 第四輪）」
- `TOKEN_BUDGET_CRITICAL.description`：「…AUTO_COMPACT 失敗後的最後防線」→「…hook 自第四輪起不再自動進入本狀態（改為 session 級拒絕非 compact 工具＋Snapshot）；保留供人工／結構性升級」
- 轉換表兩列 `≥ 95%`：目標「TOKEN_BUDGET_CRITICAL → ESCALATION」→「AUTO_COMPACT_PENDING（拒絕非 compact 工具＋Context Snapshot；session 級，不寫 ESCALATION；分子＝逐字稿實測 usage 且分母已確認）」；表後新增 `>` 註腳（不以 `|` 起頭；dst 欄刻意不寫 `API` 三個大寫字母——`fsm_md_parser.STATE_TOKEN` 會把它抓成狀態 token，實測 `test_md_happy_path_subset_of_python` 轉紅一次後訂正）
- 狀態圖 `95% → TOKEN_BUDGET_CRITICAL → ESCALATION` → `95% → deny 非 compact 工具 + Snapshot（session 級，不寫 ESCALATION）`
- `R-9.2 spec`：「≥95% 立即停止、產出 Context Snapshot 進 ESCALATION…」→「≥95% 立即拒絕非 compact 工具並產出 Context Snapshot（session 級；不寫 ESCALATION）。使用率分子＝本 session 逐字稿 API usage（context_window.scan_transcript），分母＝context_window.resolve_window 鏈（未確認分母只示警）；AUTO_COMPACT_PENDING 於觀測到 usage 回落 <85% 時自動完成。…conversation_ledger.py 估算值僅稽核／校準。」（`enforcement_mechanism`／`failure_mode`／`test_ref` 不動；R-9.5 零改動）

### 舊測試 → 新測試 1:1 對照

| 第二～三輪測試 | 意圖 | 第四輪落點 |
|---|---|---|
| pre `MaxContextGuardTests`（0／負／非數字 fallback） | 壞值不得 crash、不得算釘住 | `test_context_window.py::PositiveIntTests`＋pre `PinnedWindowTests::test_malformed_pin_is_not_pinned` |
| pre `WideContextWindowInferenceTests`（200994 不誤擋／顯式釘 200000 仍擋） | 下界推論＋顯式釘住優先 | `ResolveWindowTests::test_unknown_model_goes_to_inference`／`test_each_tier_wins_when_earlier_tiers_are_absent`＋pre `PinnedWindowTests` |
| pre/post `MaxContextConfirmedUnitTests` | 未確認分母不硬擋 | `ResolveWindowTests`（`may_block` 只在 floor 為 False）＋pre `UnmeteredAndUnconfirmedTests::test_floor_window_only_warns` |
| pre/post `DEF200275NaturalClimbTests`（170000→250000 不鎖；900000／950000 真動作） | 自然爬升不誤鎖；已確認分母仍防護 | post `RealRatioTierTests::test_unconfirmed_floor_only_warns_at_180000`／`test_explicit_pin_180000_of_200000_still_triggers`；pre `RealUsageGatingTests::test_real_900000_…`／`test_real_950000_…` |
| pre `ZeroTokenEscalationTests`（Bash 空 command 仍受 gating） | 零估算工具仍受 gating | pre `PinnedWindowTests::test_pinned_window_1000_with_used_960_denies`／`_920_auto_compact`／`_300_passes`（真實 used 自然滿足，不再讀帳本） |
| post `MaxContextFloorTests` | SDD_MAX_CONTEXT=0／負／非數字不 ZeroDivision | `PositiveIntTests`（壞值歸 0 ⇒ 不被採用為 window） |
| 既有 P1-04／P1-05／DEF-CLDREV-020／025／029 各類 | 原樣保留（新增 FSM 隔離以免吃到活 ESCALATION） | 同名類別 |

### 實測（2026-09-10，`source .venv/bin/activate` 後；每個數字附指令）

```
# 先紅（Step A：舊 _append_ledger 逐字搬入 conversation_ledger 後跑新測試）
$ python -m pytest tools/fsm_runtime/tests/test_conversation_ledger.py -q -k LedgerBookmarkAndTearingTests
E   AssertionError: True is not false : 書籤遺失後立即再合併：{'merged': True, 'added_tokens': 3600, 'cumulative': 9101, 'sidecar_merged': 0}
5 failed, 2 passed, 14 deselected in 0.53s
# 再綠（Step B 修法後）
$ python -m pytest tools/fsm_runtime/tests/test_conversation_ledger.py -q
22 passed in 5.51s
# §5-1 隔離環境 hook 相關測試（AISDLC_SDD_v0.30 下）
$ env -u SDD_HOOKS_DISABLE SDD_HOOKS_DRY_RUN= SDD_MAX_CONTEXT= AUTOSDD_CONTEXT_WINDOW= python -m pytest tools/fsm_runtime/tests/test_context_ledger_pre_hook.py tools/fsm_runtime/tests/test_context_ledger_post_hook.py tools/fsm_runtime/tests/test_conversation_ledger.py tools/fsm_runtime/tests/test_context_window.py tools/fsm_runtime/tests/test_recovery_hint.py -q
132 passed in 11.76s      （第 1 輪審查修復後；審查時 117 passed，新增 15 案：F2 計時＋損毀帳本×3＋F3×3＋QA-02×3＋ARCH-03×2＋ARCH-06×2＋SD-05）
# 全套
$ python -m pytest tools/fsm_runtime/tests/ -m "not chaos" -q
1838 passed, 8 skipped, 34 deselected, 14 subtests passed in 32.58s      （rc=0；審查時 1823；上輪 [他包回報] 1760）
$ python -m tools.arch_fitness.arch_fitness --strict                       → rc=1（fail=0、warn=3：FF-5／FF-16×2 皆既有 advisory；--strict 只對 structural fail 回 2）
$ cd AISDLC_SDD && python -m pytest scripts/tests -q                        → 351 passed, 2 skipped, 31 subtests passed in 48.54s（rc=0）
# 根層
$ python -m pytest tools/tests/test_context_window_parity.py tools/tests/test_pre_push_dispatcher.py tools/tests/test_find_git_bash_parity.py tools/tests/test_check_wrapper_thinness.py -q
108 passed, 55 subtests passed in 11.73s      （第 1 輪審查修復後；審查時 105）
$ python tools/check_defect_log_crossref.py → rc=0（F1 前 rc=1：CrossPlatform_R143_Scan_Findings.md 未登記進 _GOVERNANCE_DOCS，12 道檢查早退）
$ python tools/check_wrapper_thinness.py   → ✅ wrapper 薄殼守門通過（16 支殼 hash 釘選 + 行數上限皆正常） rc=0
$ python tools/check_script_parity.py      → ✅ 雙平台腳本對等檢查通過
$ bash tools/integration_gate.sh --skip-full → ✅ 整合閘門通過（2 PASS / 1 SKIP） rc=0
$ python tools/run_root_unittests.py       → rc=0；發現 4079 個測試（下限 4054）；0 failures / 0 errors（第 1 輪審查修復後終值）
  （審查時 rc=1／15 failures 全部同一根因＝F1 漏登記 R143；修復途中另 6 紅逐項處置：guard-line 棘輪 +73（SA-R4-03 測試 +60 ＋鎖檔自身漂移 +13，同輪追加列 96671→96744、回歸鎖軌全額申報、前綴鏈 7bd3af08e2e2→3d5c464c7535）、
   test_recovery_hint.py 的 `C:/…` 假路徑與 POSIX 絕對路徑字面值改為常數＋`platform-ok`／期望值由 `Path.with_name` 渲染（Windows 會渲染成反斜線——掃描器抓到的是真假紅）、
   fsm_runtime.py CLI stderr 提醒改全 ASCII（入口點無 UTF-8 stdio 保護鎖）。
   第四輪首跑歷史：首兩跑於靜態標籤掃描階段早退 rc=1：_TREE_FILE_FLOORS 兩棵樹下限過期，依訊息重釘 55→56／60→62；
   其後 7 紅逐項依判準訊息處置：guard-line 棘輪重釘 R143 列 96506→96671（+165，全額回歸鎖軌；
   _FROZEN_PREFIX_REWRITE_LEDGER 補 R143 鏈列、_REPIN_NET_CAP_SCHEDULE 兌現 (143, 544) 並重新武裝 145／543；
   doc-total 兩站點＝新檔 CrossPlatform_R143_Scan_Findings.md ＋ AutoSDD_improving_112.md 寄居列）、
   E501 存量棘輪（parity 測試全部折行 ≤100 欄，含 EAW 寬度）、subprocess text=True 補 encoding、
   _DIRENT_UNGUARDED_DEBT 42→40（下修：三個 os.replace 站點收斂為 _atomic_write_yaml）、
   refresh 腳本 console 輸出改全 ASCII（島內 stdio-UTF-8 複本 shrink-only 棘輪不得再長一處；其測試併入 test_context_window.py 以免再動 _TREE_FILE_FLOORS））
# 端到端（本 session 真實逐字稿餵新 pre hook；FSM state／ledger／snapshot 全在 tmp）
# 🔴 QA-03：凡 pytest 之外驅動 hook／FSM（探針、手動驗證、CLI），指令一律前綴
#   SDD_ENABLE_RULE_FIRE_TELEMETRY=0 SDD_ENABLE_RULE_CATCH_TELEMETRY=0 python …
#   否則 transition() 的 rule_loader.record_state_fires 會以 yaml.safe_dump 回寫 tracked governance/rules/*.yaml
#   （形態重排＋fire_count 灌值；審查期間並行探針重演一次＝QA-01）。做完以
#   `git status --short -- AISDLC_SDD/AISDLC_SDD_v0.30/governance/` 確認只剩 R-9.2。
measure: used=430428 peak=430428 model=claude-fable-5-1 boundaries=0 stale=False
window=967000 source=指定值（環境變數 AUTOSDD_CONTEXT_WINDOW） ratio=0.445
pre hook tool=Read/Write/Bash rc=0 out={"hookSpecificOutput": {"hookEventName": "PreToolUse"}}   ← 無 CRIT／無 deny／無 additionalContext
state after: SPEC_DRAFTING | escalation_history: 0
audit entry: {'phase': 'pre', 'tool': 'Bash', 'session_id': '8d8773f9-…', 'observed_used': 430428, 'window': 967000}
```

#### 第 1 輪審查修復實測（2026-09-10；Architect／SA／SD／QA 四方審查後，單一 Developer）

```
# F0 核實：R-9.2 只剩 spec 內文改句（folded `spec: >`、`- "*"`、scaffold_roi 三數 0 皆為 HEAD 形態）
$ git diff --stat -- AISDLC_SDD/AISDLC_SDD_v0.30/governance   → 1 file changed, 5 insertions(+), 2 deletions(-)
# F2 先紅（未修碼；他人持 fresh sentinel）
$ pytest tools/fsm_runtime/tests/test_context_ledger_post_hook.py -q -k LockTimeoutDegradation
E   AssertionError: 10.068358707998414 not less than 8.0 : 降級路徑耗時 10.07s ≥ router child timeout 8s
1 failed, 13 deselected in 10.20s
# F2 再綠（post hook 逾時直接 write_sidecar，零取鎖）：同案含在上方 132 passed in 11.76s（單案 ≈5s）
# SA-R4-03 bug-injection 自證：把 integration_gate.sh 候選鏈拔回只認 python
$ pytest tools/tests/test_find_git_bash_parity.py -q -k TestIntegrationGateShellDelegation
2 failed, 5 passed, 40 deselected in 0.33s   （紅的正是 python3 退路與 .venv 退路兩案；還原後 7 passed、check_wrapper_thinness rc=0）
# 50MB 合成逐字稿（88,264 行）全掃
50MB fixture: size=50.0MB records=88264 measure()=0.192s scan_transcript()=0.191s used=403012 peak=403012
$ python -m tools.arch_fitness.arch_fitness --strict → rc=1（fail=0、warn=3；--strict 只對 structural fail 回 2——QA-04：rc=1 不是回歸）
$ python tools/check_wrapper_thinness.py → rc=0   $ python tools/check_script_parity.py → rc=0   $ bash tools/integration_gate.sh --skip-full → rc=0（2 PASS / 1 SKIP）
$ git status --short -- AISDLC_SDD/AISDLC_SDD_v0.30/governance/ → 只列 R-9.2
```
#### 第 2 輪審查修復實測（2026-09-10；四方複審全 APPROVE 後 8 筆新發現，單一 Developer；先紅再綠）

```
# 先紅（未修碼；8 案一次跑）
$ env -u SDD_HOOKS_DISABLE SDD_HOOKS_DRY_RUN= SDD_MAX_CONTEXT= AUTOSDD_CONTEXT_WINDOW= python -m pytest -q <8 個新案 node id>
E   AssertionError: 10.02267070801463 not less than 8.0 : PENDING 出口路徑耗時 10.02s ≥ router child timeout 8s        ← G1 pre
E   AssertionError: 10.082782957993913 not less than 8.0 : PENDING 出口路徑耗時 10.08s ≥ router child timeout 8s        ← G1 post
E   AssertionError: 5.043424665986095 not less than 3.0 : reset 等鎖 5.04s（上界應為 1s 量級，不是 5s）                 ← G1 runtime
E   AssertionError: 1 != 2 : 降級 entry 必須在下一次 merge 後真的在磁碟上：{'date': '2026-09-10', 'cumulative_tokens': 1000, 'entries': [{… 'phase': 'post' …}]}   ← G3 post（sidecar 被 unlink、內容消失）
E   AssertionError: None != 3 : {'merged': False, 'added_tokens': 0, 'cumulative': 166}                                 ← G3 unit（回傳 166 但磁碟只有 100）
E   AssertionError: 7 != 0                                                                                              ← G4 append 以空 doc 覆寫並回 7
E   AssertionError: True is not false : {'resumed_to': 'IMPLEMENTATION', 'ledger': {'reset': True, … 'previous_cumulative': 0}, …}   ← G4 reset 假成功
E   AssertionError: '$' unexpectedly found in '"cost $x `id` back\\slash \'q\'"' : cd "/x" ; "/p" -m … --reason "cost $x `id` back\slash 'q'"   ← SA-R4-09
8 failed in 30.52s
# 再綠（修後同 8 案；--durations 取上界）
6.08s call  test_context_ledger_post_hook.py::LockTimeoutDegradationTests::test_pending_exit_under_foreign_lock_stays_within_router_budget
6.05s call  test_context_ledger_pre_hook.py::PendingExitLockContentionTests::test_pending_exit_under_foreign_lock_stays_within_router_budget
5.04s call  test_context_ledger_post_hook.py::LockTimeoutDegradationTests::test_lock_timeout_degrades_within_router_budget
1.06s call  test_recovery_hint.py::CompleteAutoCompactD4Tests::test_foreign_lock_reports_lock_timeout_within_one_second_budget
8 passed in 18.39s
# G2：S10 單案連跑 5 次（此前本 session 5 跑 2 紅）
1 passed in 0.10s / 1 passed in 0.09s / 1 passed in 0.09s / 1 passed in 0.09s / 1 passed in 0.09s
# 六檔 hook 測試（隔離 env；第 2 輪審查時 137，+7 新案）
$ env -u SDD_HOOKS_DISABLE SDD_HOOKS_DRY_RUN= SDD_MAX_CONTEXT= AUTOSDD_CONTEXT_WINDOW= python -m pytest tools/fsm_runtime/tests/test_context_ledger_pre_hook.py tools/fsm_runtime/tests/test_context_ledger_post_hook.py tools/fsm_runtime/tests/test_conversation_ledger.py tools/fsm_runtime/tests/test_context_window.py tools/fsm_runtime/tests/test_recovery_hint.py tools/fsm_runtime/tests/test_session_start_rules.py -q
144 passed in 25.52s
# 全套／scripts／根層四支
$ env -u SDD_HOOKS_DISABLE SDD_HOOKS_DRY_RUN= python -m pytest tools/fsm_runtime/tests/ -m "not chaos" -q → 1845 passed, 8 skipped, 34 deselected, 14 subtests passed in 48.52s（rc=0；第 2 輪審查時 1838）
$ cd AISDLC_SDD && python -m pytest scripts/tests -q → 351 passed, 2 skipped, 31 subtests passed in 51.06s（rc=0）
$ python -m pytest tools/tests/test_context_window_parity.py tools/tests/test_pre_push_dispatcher.py tools/tests/test_find_git_bash_parity.py tools/tests/test_check_wrapper_thinness.py -q → 108 passed, 55 subtests passed in 11.53s（rc=0）
$ git status --short -- AISDLC_SDD/AISDLC_SDD_v0.30/governance/ → 只列 R-9.2
$ python tools/run_root_unittests.py > /tmp/x.log 2>&1; echo rc=$? → rc=1；Ran 4079 tests in 796.814s；FAILED (failures=1, skipped=46)
  唯一真紅＝test_subprocess_encoding_hygiene.TestRootToolsLintPolicy.test_e501_debt_only_shrinks：
  「AssertionError: 140 not less than or equal to 139 : tools/tests/ 的過長行由 139 增至 140 —— 本棘輪只准往下改」
  🔴 歸因：本單（FIX_R2）未動任何根層 tools/ 檔；+1 來自**另一包**於 23:39:54 落地的未追蹤新檔
  tools/tests/test_wake_chain_halt_r278.py L105（EAW 寬度 126 > 100；同批另一包還改了 tools/lib/quota_messages.py／quota_gate.py／
  tools/session_resume_planner.py）。依 FIX_R2「本單不動 tools/tests」，該紅交另一包折行或收尾窗口重釘，本單不碰（避免兩包同時重釘同一張棘輪表）。
  單案重跑同紅（rerun_rc=1）；其餘 4078 案綠、skip 46 全為 [WINDOWS-NATIVE-ONLY] 平台標籤（欠債型 0）。
  同尺重現（EAW 顯示寬度 >100，非 ruff 的字元數——ruff E501 含不含該檔皆 136，量不到這 +1）：tools/tests 全量 140／排除
  test_wake_chain_halt_r278.py 後 139＝棘輪天花板。
```

### 把握程度（誠實劃界）

- 分子依賴 Claude Code 逐字稿的 `message.usage` 契約（非公開 API 保證）；欄位一旦改名，`measure()` 回 `used=None` ⇒ 退化為零 gating（fail-open 方向，不誤擋）。
- 查表 `refreshed_at=null`、`seeded_from=claude-api skill cached table 2026-06-24`（值與 skill 快取表逐項核實一致）；本機無 `anthropic` SDK，刷新腳本未實跑（`apply_models` 純函式有測試）。
- 50MB 合成逐字稿全掃實測 `measure()=0.192s`（88,264 行；2.19MB 真實逐字稿 0.011s）——距 router 8s child timeout 仍有 40 倍餘裕，offset 快取備案不啟用。
- `.ps1` 對等檔（`tools/integration_gate.ps1`）不動——不對稱：`.sh` 多一層 `.venv/bin/python` 候選。SA-R4-03 三案在 Windows 靠 MSYS bash 對 `command -v` 的 `.exe` 透明解析（shim 以 `python.exe` 命名）；本機為 macOS，**Windows 側未實跑**，交 windows-compat-ci 驗證。
- 恢復指令的 `python` 取 hook 行程的 `sys.executable`（本機實測為 `/Library/Developer/CommandLineTools/usr/bin/python3`，非 venv；該直譯器能載入 PyYAML 才跑得到這裡）。F3：Windows 根層 hook 載具是 GUI 子系統 `pythonw.exe`（exec form 免閃窗），`console_python()` 在同目錄 `python.exe` 存在時換成它、不存在則照印原值（誠實）；訊息改為 bash/zsh 與 PowerShell 各一行（`&` 緊貼直譯器路徑，不是整行最前）。
- 🔴 QA-03：pytest 之外任何 hook／FSM 探針必須前綴 `SDD_ENABLE_RULE_FIRE_TELEMETRY=0 SDD_ENABLE_RULE_CATCH_TELEMETRY=0`（conftest 已替 pytest 設好；探針沒有 conftest）。
- ARCH-03：D4 出口**不看 session**——PENDING 是專案級狀態，觸發它的 session A 與觀測到 usage 回落的 session B 可以不同；B（視窗本來就小）開場即釋放並把 `count_per_stage` 歸零，A 下一次工具呼叫再觸發 ⇒ 乒乓（每次都留 Snapshot＋decision_trace，不會鎖死）。現行取捨：不加 session 守衛（加了就回到「別的 session 把專案卡在 PENDING」的根因 C 形狀）；DONE 訊息與 decision_trace reason 已印 `released_by_session／triggered_by_session`，雙 session 測試釘住現行行為；是否改守衛另案。
- SD-03：交叉否決只擋**跨族**（settings `opus-4-6[1m]` vs 逐字稿 `sonnet`）；同族不同代（settings `opus-4-6[1m]`、實跑 `opus-4-1` 200K）會猜大——順序改動（查表先於標記）另案。
- SD-04：`settings_value` 取鏈上第一個非 None（settings.local 蓋 settings 蓋 ~/.claude），與 Claude Code 合併語意一致；低優先，登記。
- SD-05：負整數書籤視同缺失 rebaseline；「全新帳本（無 conv-overhead 列）從 0 起算」是**有意偏離**（那不是遺失，是從未合併），見 D5。
- QA-07：Bash 在 AUTO_COMPACT 白名單內（跑 compaction 需要它）⇒ 95% 時 Bash 只附 CRIT 訊息不擋；Write/Edit 非 `build/reports/` 目標才 deny。
- G1：**PENDING 出口路徑鎖等待上界 6s**（稽核鎖 5s＋reset 鎖 1s）< router 8s；其餘路徑仍 5s。`_reset_today_ledger` 等不到鎖就回 `lock_timeout=True`、帳本不歸零——帳本零決策權，cumulative 沒歸零只影響稽核讀數，不影響任何 gating。兩支 hook 的兩段等待是**串行**的，8s 上界只在單一 fresh sentinel 下成立；若同一 hook 行程還有第三個取鎖站點被加進來，上界就再破——新增取鎖站點時須重量 `PendingExitLockContentionTests`。
- G3：sidecar 折回現在**真的持久化**（未達 conv-overhead 門檻也寫檔一次）；代價＝有 sidecar 的那一 tick 多一次 `_atomic_write_yaml`（無 sidecar 時零額外寫入）。
- G4：`_load_ledger_doc` 讀檔 OSError 現在拋出、三個寫入者各自接住「該次不寫」；hook 端因 `_record_audit`／`_record_audit_and_merge` 既有 try/except 與 `complete_auto_compact` 的 ledger 欄包裝，例外仍永不到 main()。損毀（YAMLError／非 dict）路徑維持 rotate 重開——「讀不到」與「讀到壞的」刻意分流。回歸鎖以 `Path.open` 注入 PermissionError 而非 `chmod 000`：root（CI 容器）讀得到 000 檔、Windows 的 chmod 對讀取權零作用（鐵律三），兩個平台都會把 chmod 版變成假綠。
- G2：S10 hermetic 化（既有非本輪缺陷，順手修）——本 session 第 2 輪審查實測 5 跑 2 紅的來源是活 hook 在測試視窗內 append；改 patch `REPO_ROOT`／`SNAPSHOT_DIR` 後 5 跑皆綠。全套「N passed」此前在有活 hook 的 session 內不是 hermetic 的，現在是。
- SA-R4-09＝SD-R2-04：reason 中和 `$`／反引號／反斜線（換成 `'`）；SD 建議的另一解（PowerShell 分支改單引號包）未採——同一個 reason 兩殼各一種引號規則，比一次中和多一條要記的規則。測試只斷言 `--reason` 之後那段（Windows 的 `sdd_root` 本來就含反斜線）。
- QA-05：`test_second_merge_after_append_does_not_remerge` 是兩層同時失守才紅的端到端鎖（單注入各被另一層接住），docstring 已註明；單點鑑別由前後兩案負責。
- 🔴 活帳本 `CONTEXT-LEDGER-2026-09-10.yaml`（含半截行）在新 hook 上線那一刻（06:24:17Z）被 **hook 的正常路徑**自動 rotate 為 `.corrupt-20260910T062417370815Z.yaml` 並重開新檔——非手動操作，但等同「rotate 已由 hook 代做」，主控收尾不必再做。活狀態檔 `FSM-STATE-AISDLC_SDD.yaml` 未動（仍 ESCALATION，恢復指令已由 SessionStart／deny 訊息印出）。
- 本輪一次教訓：`test_cli_subcommand_contract` 初版用最小 env 跑 CLI 子行程，缺 conftest 的 `SDD_ENABLE_RULE_FIRE_TELEMETRY=0` ⇒ `transition()` 的 fire 遙測把 9 支凍結 `governance/rules/*.yaml` 以 `yaml.safe_dump` 重寫（形態＋`fire_count`）。已從 HEAD 逐檔還原（`git show`＋寫回，非 checkout）並讓子行程繼承隔離旗標；`git diff --stat governance` 只剩 R-9.2 的 spec 改句。

### 未做事項（另案）

- `SDD_CONTEXT_GOVERNOR.md` L183-197、`AISDLC_SDD_INIT.md` session_resume yaml 的文字仍為舊語意（C13 文件最小集刻意不碰）。
- `TOKEN_BUDGET_CRITICAL` 狀態去留（hook 已不進入；狀態、`_BLOCKING_STATES`、transition_rules、TLA 全不動）。
- `AUTO_COMPACT_PENDING` 目標集缺 `INIT` 補邊需碰 TLA（本輪以 remap 迴避）。
- post hook ≥70% 每呼叫出聲，與根層守衛（84／94）雙告警的去重。
- 刷新腳本真打 Models API 的實跑（需 `uv pip install anthropic`＋`ant auth login`）；表 `refreshed_at=null` 是否由主控收尾窗口裝 SDK 真打一次（ARCH-09），Developer 不動。
- ARCH-05 後半：Snapshot／abort report 仍以 `cumulative_tokens` 命名欄位（`save_auto_snapshot` 簽名要加 `numerator="transcript_api_usage"`，非一行修）；decision_trace reason 已改印 `used=／source=`。
- ARCH-03 的 session 守衛（是否只允許觸發 session 釋放 PENDING）——現行刻意不加，見〈把握程度〉。
- SD-03 分母鏈順序（查表先於 `[1m]` 標記以堵同族交叉否決盲區）。
- QA-08：`HooksDisableSubagentContractTests`／`LegacyReadFallbackTests` 未套 `_isolated_env`（既有測試、行為與環境無關，可選統一）。
- 第 2 輪審查 8 筆新發現（QA-R2-01／ARCH-R2-01／SD-R2-02 同件、ARCH-R2-02、SD-R2-01、SD-R2-03、SA-R4-09＝SD-R2-04）全數已修，無遺留；`test_e2e_smoke.py` 其餘各案（S2 escalation 等）是否也把 Snapshot 落 tmp 未逐案盤點（S10 以外的活目錄寫入面另案）。

### TLA 判斷

未改 `_HAPPY_PATH`、未增刪狀態與邊（`resume_from_escalation` 走既有 `ESCALATION→RESUME_VERIFICATION→{SPEC_DRAFTING,IMPLEMENTATION,PR_REVIEW}`；
D4 remap 走既有 `AUTO_COMPACT_PENDING→SPEC_DRAFTING`），不重跑 TLC（R-9.18 僅在改動 `_HAPPY_PATH` 時強制）。`test_tla_python_sync`／`test_md_python_sync` 全綠。
