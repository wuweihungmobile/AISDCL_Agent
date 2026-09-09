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
