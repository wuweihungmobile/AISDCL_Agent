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

## 第五輪（2026-09-11；四方複審後仍 partial ⇒ D11～D16）

### 觸發（掌舵者原話逐字）

第四輪 commit ea6113d push 後，掌舵者要求對「已修好」的宣稱做獨立複審：

1. 「我用終端 claude 都會出現以下問題，才開新視窗，就說他被擋不能寫檔案用工具了，然後也不去查真實的數據」
2. 「模型都不用真實的 /context 或 API 去查真實數據」

並要求：「派出 Architect / SA / SD / QA 四方專家獨立審查，與目前系統現況進行比對，請確認是否有以下問題，若有請徹底解決」；「請確認以上都已經修好！」

### 四方判決與收斂發現

Architect／SA／SD／QA 四方（皆 Sonnet 5、唯讀、各自在隔離副本獨立重現，不互相溝通）判決一致：
問題 1「新視窗一開就被擋」＝**partial**；問題 2「不用真實 /context 或 API 查數據」＝**partial**。
收斂發現如下（座標見前次任務書 §3 F1～F12；下方 (a)～(h) 為四方交叉重現後的收斂結論）：

- **(a) PENDING × 首擊 m=None ⇒ 首擊 Write/Task deny**（四方皆重現）。新 session 第一次 `PreToolUse` 量不到 usage
  （逐字稿尚未寫入帶 `usage` 的 assistant 訊息），`main()` 的 D4 出口要求 `m is not None` 才會嘗試釋放 PENDING；
  若專案 FSM-STATE 恰好停在 `AUTO_COMPACT_PENDING`，新視窗第一個非白名單工具呼叫（Write／Edit 非
  `build/reports/`、Task／Agent）會被 `_assert_allowed_under_auto_compact` deny——這正是掌舵者原話①的機制根源。
- **(b) per-stage cap ⇒ 專案級 ESCALATION，之後每個新視窗全擋、不自癒**（Architect／SD／QA 重現）。
  第四輪 D3 明文保留「per-stage cap 超限仍走既有結構性升級」，但 `record_escalation()` 把 `ESCALATION`
  寫進**跨 session 黏著**的專案級 FSM-STATE，R-9.5「不可自動退出」⇒ 任何全新視窗（含 `claude -r`、
  subagent／Workflow 子 session）開場即被 PreToolUse 全擋，SessionStart 只印「需人工介入」、無可執行指令。
- **(c) 指定值分母（967000）對 observed_model 零交叉，haiku 真實 125% 讀成 25.9%**
  （四方皆以 `resolve_window` 直呼重現）。分母鏈②③④階取到操作者釘值（如 `AUTOSDD_CONTEXT_WINDOW=967000`）後
  從未與 `observed_model` 查表值比較收斂；當實際跑的是 haiku-4-5（Models API 上限 200,000）而釘值仍是
  967000 時，真實 125% 的用量會被算成 25.9%——量測「不用真實 API 查數據」（原話②）在跨模型／子 agent
  情境下並未收斂。
- **(d) Stop hook 無「被擋／水位」宣稱佐證判準**（四方）。`check_claim_provenance.py` 既有四個判準未涵蓋
  「模型自稱『被擋了』／『水位過高』但本場零機器事件佐證」這一類無值宣稱，沒有機械物逼模型先查真實值
  才能做這類宣稱。
- **(e) SD-06（另案）**：並行 subagent 共用同一份專案級 FSM-STATE；`load_track_state`／`track_id` 已存在但
  hook 未使用，屬於 (a)(b) 的同根結構性問題的另一個面向。
- **(f) ARCH-06（另案）**：v0.30 `.claude/settings.json` 的 `PreToolUse` matcher 缺 `Agent|Workflow`，
  代表 Agent／Workflow 工具呼叫目前**繞過** SDD FSM 護欄（與 (a)(b) 相反方向的缺口：不是「多擋」而是「該擋沒擋」）。
- **(g) QA 親跑複驗上一場（第四輪）數字成立**：SDD 全套 `1845 passed, 8 skipped` rc=0；根層
  `Ran 4097 tests … OK` rc=0；DEF-200-278 的 18 支測試「`ea6113d^` 紅、現版綠」。[他包回報]
  （第四輪「已修復」宣稱在**已驗證的既有回歸範圍內**成立，partial 判決指向的是四方新發現的 (a)～(f)，
  不是推翻第四輪既有測試。）
- **(h) F8 定性更正**：主控前一份任務書把「近四天逐字稿中 2026-09-10T08:31:21Z 的一筆 attachment」
  誤判為 hook deny 事件；QA 複驗後更正：該筆 attachment type 為 `edited_text_file`（磁碟異動提醒），
  **不是** hook deny——本場近四天逐字稿內找不到真實 hook deny 事件樣本，(d) 的假紅普查因此以合成注入自證
  （見〈實測〉D15 假紅普查一節）。

### 裁決 D11～D16（總架構師定案；被否決意見括註）

> 逐字抄自本輪設計定案 `design_r5.md`；括號內為被否決的替代方案與否決理由。

- **D11 PENDING × 量不到 usage ⇒ 放行一次（C3 原則補齊）**。`context_ledger_pre.py`：FSM 為
  `AUTO_COMPACT_PENDING` 且 `m is None or m.used is None` 時，`assert_tool_allowed` 拋出的 PENDING deny
  改為放行＋notice：`[SDD-CTX][AUTO-COMPACT][UNMETERED] 本次呼叫量不到 usage（新 session 首擊／compact 後
  尚無新 usage）⇒ 依 C3 放行一次；下一次呼叫依真實 usage 判定（<85% 自動解除 PENDING）。PENDING 由
  session=<trigger sid> 於 <triggered_at> 觸發`。ESCALATION 類狀態不受本條影響。
  （否決「加 session 守衛只讓觸發 session 被擋」：那回到 ARCH-03 的乒乓與根因 C 形狀；否決「把 D4 出口
  放寬成 m=None 也出口」：量不到不能當「已回落」。）
- **D12 PENDING deny 訊息必帶真實數字＋來源 session**。量得到而仍 deny 時，reason 必含
  `used=… window=… 來源=…`、`PENDING 由 session=<sid> 於 <ts> 觸發`、解除規則一句（`真實 usage 回落 <85%
  後下一次工具呼叫自動恢復 resume_state`）。抽 helper `_pending_deny_reason(rt, m, window, source)`。
- **D13 per-stage cap 超限 ⇒ session 級，不再寫專案級 ESCALATION**（ARCH-02／SD-02／QA P0）。
  `FSMRuntime.trigger_auto_compact` cap 分支：不呼叫 `record_escalation`、不 transition；改在
  `auto_compact_state["cap_exceeded"]={"at","session_id","stage_key","count"}` 落一次性標記（已存在則不重寫）、
  `save_abort_report(category="auto-compact-rate-limit")` 只在首次落標記時寫一次、`save_state`；回
  `{"escalated": False, "cap_exceeded": True, "noop": True, "reason": "..."}`。hook（CRIT 與 AUTO_COMPACT
  兩分支）收到 `cap_exceeded` ⇒ 以 `_assert_allowed_under_auto_compact` 白名單做**session 級** deny：
  `[SDD-CTX][CRIT][CAP] 本 session 於 stage '<k>' 已 <n> 次觸發 auto-compact 未見有效壓縮 ⇒ 本 session
  拒絕非 compact 工具（不寫 ESCALATION、不影響其他視窗）。請 /compact 或 claude -r 重啟本 session；真實
  usage 回落 <90% 即解除。` D4 出口 `observed_effective=True` 時同步清掉 `cap_exceeded`。R-9.2 yaml
  `failure_mode` 文字改為 session 級語意（只改字、不改結構鍵）。既有
  `test_per_stage_cap_exceeded_*_denies_with_project_escalation` 改名重寫為 session 級斷言＋新增「另一個
  全新 session（零 usage）在 cap 後照常放行」。TLA：無狀態／邊增刪 ⇒ 不重跑 TLC，但要跑
  `test_tla_python_sync`／`test_md_python_sync`。
  （否決「ESCALATION 只放 Read」：仍是專案級鎖，違反 D3 的層級論證。）
- **D14 指定值分母（②③④階）以 observed_model 查表值收斂**（SA-04／ARCH-04／SD-03／QA-04 P1）。
  `context_window.resolve_window`：取到 ②`AUTOSDD_CONTEXT_WINDOW`／③CC env／④settings `autoCompactWindow`
  的釘值後，若 `observed_model`（只認逐字稿實跑 model，不認 hint）在 `known_models` 查得且**表值 < 釘值**
  ⇒ 回 `(表值, "已收斂" 來源字串)`。① `SDD_MAX_CONTEXT` 是 session 手動釘值，不收斂。`may_block` 對此來源
  ＝True。根層守衛的同型收斂**另案**登記（它沒有查表階）。
- **D15 Stop hook 新判準：「被擋／水位」無值宣稱須有本場佐證**（SA-03／ARCH-03／QA-05／SD-05）。
  `.claude/hooks/check_claim_provenance.py` 新增純函式 `unbacked_block_claim_hits(claim_text, evidence_text)`：
  句子含被擋類詞（引號夾住的不算）而本場佐證文字不含 `permissionDecision|deny|[SDD-FSM]|[SDD-CTX]|used=|--check`
  任一 ⇒ 出聲，**永不阻斷**。`AUTOSDD_UNATTENDED` 有設時沿用既有縮窄規則。必做假紅普查。
- **D16 recovery_hint 印目前真實水位**（SA-02 P2）。`recovery_hint(state, *, sdd_root, python=…,
  measurement=None, window=None, source=None)` 可選參數；pre hook 與 session_start 傳入量測；有值印
  「目前本 session 真實 used=… window=… 來源=…」，量不到印「目前本 session 尚無可用 usage」。既有簽名呼叫
  零改動。

### 修法逐檔

分兩包並行（鎖持有面已切開）：Dev-A 負責 D11／D12／D13／D16（SDD 治理面）；Dev-B 負責 D14／D15
（量測面＋根層 Stop hook）。下表合併兩包報告；標「範圍外」的檔案不在原始任務分派清單內，是因為它們是
被要求修改的函式（`trigger_auto_compact`）的直接消費者，不修會讓 `pytest tools/fsm_runtime/tests/ -m
"not chaos"` 見紅，判斷屬「開發-編譯-測試循環」義務範圍、非擅自擴權（已核實與 Dev-B 的檔無重疊）。

| 檔案 | 改動 | 包 |
|---|---|---|
| `AISDLC_SDD_v0.30/.claude/hooks/context_ledger_pre.py` | D11：新增 `_pending_unmetered_notice()`，`AUTO_COMPACT_PENDING` 且 `m is None or m.used is None` ⇒ 放行一次＋`[UNMETERED]` notice；D12：新增 `_pending_deny_reason(rt, m, window, source)` 組真實數字 reason；`_recovery_hint` 簽名擴充轉呼叫新版 `recovery_hint()`；D13：新增 `_cap_exceeded_deny_reason()`／`_cap_exceeded_pass_notice()`，CRIT／AUTO_COMPACT 兩分支在 `escalated` 檢查前插入 `cap_exceeded` 檢查（AUTO_COMPACT 分支需排在 `noop` 檢查之前），走白名單做 session 級 `[CAP]` deny／放行；`escalated` 分支保留為防禦性 fallback | Dev-A |
| `AISDLC_SDD_v0.30/.claude/hooks/context_ledger_post.py` | **範圍外**（`trigger_auto_compact` 直接消費者，不修會使全套測試見紅）：D13 的 `cap_exceeded` 分支需排在 `noop` 分支之前（否則 PostToolUse 通知被 `[NOOP]` 蓋掉，實測踩到）；新增對稱 `[CAP]` 通知文字；`escalated` 分支保留為防禦性 fallback | Dev-A |
| `AISDLC_SDD_v0.30/.claude/hooks/session_start.py` | D16：新增 `_recovery_measurement(payload)`，獨立重新量測一次（duck-typing、例外回 `(None,None,None)`）；ESCALATION／ESCALATION_FINAL 區塊呼叫 `recovery_hint()` 時傳入量測 | Dev-A |
| `AISDLC_SDD_v0.30/tools/fsm_runtime/fsm_runtime.py` | D13：`trigger_auto_compact()` per-stage cap 分支移除 `record_escalation` 與轉態，改落 `auto_compact_state.cap_exceeded` 一次性標記；`save_abort_report()`／`_record_escalation_catches(["R-9.2"])` 只在首次落標記時呼叫一次；回傳 `cap_exceeded=True`／`escalated=False` | Dev-A |
| `AISDLC_SDD_v0.30/tools/fsm_runtime/recovery_hint.py` | D16：`recovery_hint()` 新增 `measurement=None, window=None, source=None` 可選關鍵字參數（duck-typing 讀 `.used`）；輸出多一行真實水位或「尚無可用 usage」；既有呼叫簽名零改動 | Dev-A |
| `AISDLC_SDD_v0.30/governance/rules/R-9.2-context-budget.yaml` | 只改 `failure_mode:` 文字（Edit 逐段替換，非 yaml dump）為 session 級語意；`enforcement_mechanism`／`spec:` 皆未動 | Dev-A |
| `tools/fsm_runtime/tests/test_context_ledger_pre_hook.py` | 新增 `PendingUnmeteredTests`（D11，3 支）；`test_pending_deny_reason_has_real_numbers_and_trigger_session`（D12）；`RealUsageGatingTests` 兩個 cap 測試改名重寫為 session 級語意＋新增「全新低用量 session 照常放行」 | Dev-A |
| `tools/fsm_runtime/tests/test_context_ledger_post_hook.py` | **範圍外**：`..._reports_project_escalation` 改名重寫為 `..._reports_session_level_cap` | Dev-A |
| `tools/fsm_runtime/tests/test_recovery_hint.py` | 新增 `RecoveryHintMeasurementTests`（D16，4 支）；`test_trigger_auto_compact_stores_details_and_passes_them_on_cap` 改寫為 D13 語意 | Dev-A |
| `tools/fsm_runtime/tests/test_w20_catch_wiring.py`／`test_w37_catch_wiring.py` | R-9.2／R-9.7 catch 測試改寫斷言（D13 語意；catch_count 判定不變） | Dev-A |
| `tools/fsm_runtime/tests/test_auto_compact_rate_limit.py` | **範圍外**：`test_over_limit_escalates`→`test_over_limit_marks_cap_exceeded_not_escalated`；`test_over_limit_writes_abort_report` 斷言改 cap_exceeded；`test_trigger_in_escalation_is_noop` 改用 `record_escalation()` 直接造前提 | Dev-A |
| `AISDLC_SDD_v0.30/tools/fsm_runtime/context_window.py` | D14：新增 `_converge_pinned_window(pinned, observed_model, known_models)` 純函式；`resolve_window` 改寫，① `SDD_MAX_CONTEXT` 獨立不收斂，②③④ 迴圈內插入收斂呼叫 | Dev-B |
| `tools/fsm_runtime/tests/test_context_window.py` | 新增 `ConvergePinnedToKnownModelTests`（6 測試：autosdd 收斂／fable 保留釘值／sdd_raw 永不收斂／observed None 保留釘值／cc_env_raw 收斂／settings_window 收斂） | Dev-B |
| `.claude/hooks/check_claim_provenance.py`（根層） | D15：`_INTERESTING` 前篩加寬 `hook_blocking_error`／`hook_additional_context`；新增 `_block_evidence_text(records)`；新增 `BLOCK_CLAIM_RE`／`BLOCK_EVIDENCE_RE`（含假紅普查逼出的 `kind=|band=|cap=|requested permissions|haven't granted`）；新增 `unbacked_block_claim_hits(claim_text, evidence_text)`；`main()` 新增第五判準分支，逃生口 `AUTOSDD_BLOCK_CLAIM_GUARD_OFF`（獨立、不與既有四個共用） | Dev-B |
| `tools/tests/test_claim_provenance_r86.py`（根層） | 新增 `TestTheUnbackedBlockClaimJudgement`（6 測試）／`TestTheUnbackedBlockClaimHookWiring`（5 測試） | Dev-B |
| `tools/tests/test_adr_xplat001_c1c2_lock.py`（根層） | guard-line 棘輪重釘：`test_claim_provenance_r86.py` 806→936；本檔自身漂移 +17＋7；`_GUARD_LINES_REPIN_LOG` 新增 R144 三列，淨額 97056→97210（+154）；`_REPIN_LOG_HISTORY_SHA256` 重算；`_FROZEN_PREFIX_REWRITE_LEDGER` 新增 R144 接鏈列 | Dev-B |
| `tools/tests/test_context_window_parity.py`（根層） | **只讀未改**（設計範圍限制）；D14 收斂邏輯只影響②③④階，`known_models={}` 時行為逐字不變，parity 未受影響 | Dev-B（唯讀） |

### 舊測試 → 新測試對照（Dev-A）

| 舊測試 | 新測試/新斷言 | 檔案 |
|--------|--------------|------|
| `test_per_stage_cap_exceeded_at_950000_denies_with_project_escalation` | `test_per_stage_cap_exceeded_at_950000_denies_session_level` | test_context_ledger_pre_hook.py |
| `test_per_stage_cap_exceeded_at_900000_denies_with_project_escalation` | `test_per_stage_cap_exceeded_at_900000_denies_session_level` | test_context_ledger_pre_hook.py |
| （無，新增）| `test_cap_exceeded_does_not_block_a_brand_new_low_usage_session` | test_context_ledger_pre_hook.py |
| （無，新增）| `PendingUnmeteredTests`（D11，3 支）／`test_pending_deny_reason_has_real_numbers_and_trigger_session`（D12） | test_context_ledger_pre_hook.py |
| `test_per_stage_cap_exceeded_at_900000_reports_project_escalation` | `test_per_stage_cap_exceeded_at_900000_reports_session_level_cap` | test_context_ledger_post_hook.py |
| `test_trigger_auto_compact_stores_details_and_passes_them_on_cap`（斷言 escalated=True） | 同名，斷言改 `cap_exceeded=True`／`escalation_history==[]` | test_recovery_hint.py |
| （無，新增）| `RecoveryHintMeasurementTests`（D16，4 支） | test_recovery_hint.py |
| `test_r92_catch_on_auto_compact_overflow_flag_on` / `test_r92_catch_flag_off_zero_regression` | 同名，斷言改 D13 語意 | test_w20_catch_wiring.py |
| `test_r97_not_attributed_on_auto_compact_overflow` | 同名，斷言改 D13 語意 | test_w37_catch_wiring.py |
| `test_over_limit_escalates` | `test_over_limit_marks_cap_exceeded_not_escalated` | test_auto_compact_rate_limit.py |
| `test_over_limit_writes_abort_report` | 同名，斷言改 cap_exceeded | test_auto_compact_rate_limit.py |
| `test_trigger_in_escalation_is_noop` | 同名，改用 `record_escalation()` 直接造前提（不再靠 cap 超限進 ESCALATION） | test_auto_compact_rate_limit.py |

### 實測

> Dev-A／Dev-B 為兩個獨立子 agent，於各自 session 內自行實測；本文件整合 agent 未重跑，以下 Dev-A／Dev-B
> 段落數字全數標記 [他包回報]。文件整合 agent 本場親跑驗證見文末〈驗證〉一節（不加標記）。

**Dev-A（D11/D12/D13/D16）**：[他包回報]
```
# 紅（實作前）
python -m pytest tools/fsm_runtime/tests/test_context_ledger_pre_hook.py -q -p no:cacheprovider
→ 7 failed, 36 passed in 6.68s
python -m pytest tools/fsm_runtime/tests/test_recovery_hint.py tools/fsm_runtime/tests/test_w20_catch_wiring.py tools/fsm_runtime/tests/test_w37_catch_wiring.py -q -p no:cacheprovider
→ 7 failed, 32 passed in 1.93s
# 綠（逐步修復後）
python -m pytest tools/fsm_runtime/tests/test_recovery_hint.py -q -p no:cacheprovider → 29 passed in 1.58s
python -m pytest tools/fsm_runtime/tests/test_context_ledger_pre_hook.py -q -p no:cacheprovider → 43 passed in 6.58s
# 組合驗證（8 檔）
python -m pytest tools/fsm_runtime/tests/test_context_ledger_pre_hook.py tools/fsm_runtime/tests/test_context_ledger_post_hook.py tools/fsm_runtime/tests/test_recovery_hint.py tools/fsm_runtime/tests/test_w20_catch_wiring.py tools/fsm_runtime/tests/test_w37_catch_wiring.py tools/fsm_runtime/tests/test_w39_coverage_denominator.py tools/fsm_runtime/tests/test_governance_coverage.py tools/fsm_runtime/tests/test_context_window.py -q -p no:cacheprovider
→ 153 passed in 20.23s（首跑 1 failed，`context_ledger_post.py` 也依賴舊 escalated 語意，修好後綠）
# rule loader／md-python sync／tla sync
python -m pytest tools/fsm_runtime/tests/test_md_python_sync.py tools/fsm_runtime/tests/test_rule_loader_eol.py tools/fsm_runtime/tests/test_tla_python_sync.py tools/fsm_runtime/tests/test_rule_938_translation_fidelity.py tools/fsm_runtime/tests/test_rule_catch_telemetry_wiring.py tools/fsm_runtime/tests/test_rule_fire_telemetry_wiring.py tools/fsm_runtime/tests/test_rules_index_sync.py -q -p no:cacheprovider
→ 41 passed, 1 skipped in 0.60s
# 全套（含 Dev-B 同時在改的檔）
python -m pytest tools/fsm_runtime/tests/ -m "not chaos" -q -p no:cacheprovider
→ 1860 passed, 8 skipped, 34 deselected, 14 subtests passed in 45.98s（首跑 3 failed，`test_auto_compact_rate_limit.py` 因 grep 大小寫漏抓 `MAX_AUTO_COMPACT_PER_STAGE` 常數用法，改寫後綠）
# ci-gate.sh（含 v0.01 凍結基線＋v0.30 LATEST 雙軌＋根層 scripts/tests 共享 infra）
✅ 本機 CI 閘門全數通過（版本：AISDLC_SDD_v0.01 AISDLC_SDD_v0.30）；逐軌計數：AISDLC_SDD_v0.01:1475 AISDLC_SDD_v0.30:1860 scripts/tests:351；CI_GATE_RC=0
```

**Dev-B（D14/D15）**：[他包回報]
```
# D14 紅：3 個新測試（autosdd/cc_env/settings 三階收斂案例）修法前 AssertionError: 967000 != 200000
# D14 綠
cd AISDLC_SDD/AISDLC_SDD_v0.30 && python -m pytest tools/fsm_runtime/tests/test_context_window.py -q → 39 passed in 0.10s（33 舊 + 6 新）
python -m pytest tools/fsm_runtime/tests/test_context_window.py tools/fsm_runtime/tests/test_context_ledger_pre_hook.py tools/fsm_runtime/tests/test_context_ledger_post_hook.py -q → 95 passed in 18.14s
cd tools/tests && python -m unittest test_context_window_parity -v → Ran 3 tests in 0.010s / OK（未受影響）
# D15 紅：暫時把 unbacked_block_claim_hits 改成 return []，python -m unittest tools.tests.test_claim_provenance_r86 -q → 2 個測試失敗
# D15 綠
python -m unittest tools.tests.test_claim_provenance_r86 -q → Ran 62 tests in 0.822s / OK（還原後）；加入 kind=/band=/cap=/權限牆兩個新測試後 → Ran 64 tests in 0.794s / OK
```

**D15 假紅普查（Dev-B，[他包回報]）**：母體 `~/.claude/projects/-Users-wuweihong-Antigravity-AISDCL-Agent/*.jsonl`
近 7 天（mtime，非 rglob 只掃頂層）40 支，逐支循序掃描每一則 assistant text 區塊（證據只累積「這一則之前」
的內容，模擬真實 Stop hook 因果順序）：
- 初版詞表（`deny|[SDD-FSM]|[SDD-CTX]|used=|--check`）：命中 4 筆，逐筆判讀 4 筆全部假紅（配速守衛 `kind=…band=`
  通知、Claude Code 內建權限牆訊息 3 筆）。
- 加入 `kind=|band=|cap=|requested permissions|haven't granted` 後重跑同一份母體：**命中 0 筆**。
- 本機母體上真陽性同樣是 0 筆（無「本場真的沒有任何機器事件佐證」的被擋宣稱）——召回率在本機母體上無從
  量測，紅綠自證靠合成注入（`TestTheUnbackedBlockClaimJudgement`／`TestTheUnbackedBlockClaimHookWiring`）。

### 把握程度

- **高把握（Dev-A）**：D11／D12／D13 的核心行為變更、D16 的 `recovery_hint` 擴充，皆先紅後綠、且全套
  fsm_runtime 測試（1860 passed）驗證過。
- **Dev-A 對 `_record_escalation_catches(["R-9.2"])` 保留的判斷**：讀了 `rule_loader.record_state_catches()`
  實作後發現它**不檢查 FSM 狀態**，只憑 rule_id + failure_mode 記 `catch_count`；而
  `test_w39_coverage_denominator.py`／`test_governance_coverage.py`（皆不在 Dev-A/Dev-B 範圍內、且靜態掃描
  `_record_escalation_catches([...])` 呼叫字面）鎖死「R-9.2 屬於 7 條 escalation-attributable 規則」這個
  不變式。若移除該呼叫，`_ESCALATION_ATTRIBUTABLE_RULE_IDS` 與 R-9.2 yaml 的
  `enforcement_mechanism: escalation` 會與這兩支範圍外測試打架，而 Dev-A 不能改它們（也不能改
  `enforcement_mechanism`，只准改 `failure_mode` 文字）。故 Dev-A 判斷：catch 語意收斂為「規則自描述的
  失敗模式真的被打到」，不再要求「必進 project-level ESCALATION」——已在呼叫點與 R-9.2 yaml 的
  `failure_mode` 裡寫清楚這個收斂。**若總架構師認為應該移除**，需要同時鬆動
  `_ESCALATION_ATTRIBUTABLE_RULE_IDS`／`test_w39_coverage_denominator.py`／`test_governance_coverage.py`／
  R-9.2 的 `enforcement_mechanism`，那是四方之外的另一個決策面，建議另案處理（本輪暫按 Dev-A 判斷收尾，
  未進一步裁決推翻）。
- **中高把握（Dev-B）**：D14 收斂邏輯只影響②③④階、且只在 `known_models` 非空且命中時觸發；parity 測試
  傳 `known_models={}`，結構上不可能受影響（已實測確認）。D15 判準本體與假紅收斂經過兩輪真實語料驗證
  （4→0），且有合成注入雙向自證。
- **Dev-B 的 `kind=`/`band=`/`cap=` 可滿足性代價（誠實劃界）**：這三個詞加入 `BLOCK_EVIDENCE_RE` 是假紅
  普查逼出的收斂，但覆蓋率不是免費的——本機 40 支語料中 16／14／16 支含這些字樣（40%），一旦本場任何地方
  出現過就會讓 D15 判準對「被擋」整場靜音，即使與該次宣稱無關。這是刻意的可滿足性選擇（精確度換召回率），
  代價已寫入 `check_claim_provenance.py` 檔頭「第五個判準」段落，未被總架構師推翻。
- D14／D15 皆未觸及 Windows 側真機驗證；D14 查表值仍是 `known_model_windows.json` 的 2026-06-24 種子值
  （本機無 `anthropic` SDK／key，`refresh_known_model_windows.py` 本輪仍未真跑）。

### 未做事項（另案）

- **SD-06**：並行 subagent 共用同一份專案級 FSM-STATE，`load_track_state`／`track_id` 存在但 hook 未用。
  已立 **DEF-200-279**（P1，open）。
- **ARCH-06**：v0.30 `.claude/settings.json` `PreToolUse` matcher 缺 `Agent|Workflow`（Agent/Workflow
  工具呼叫繞過 SDD FSM 護欄）。已立 **DEF-200-280**（P2，open）。
- 根層 `context_budget_guard.py` 無查表階 ⇒ D14 同型收斂仍是另案，本輪未做。
- `known_model_windows.json` 仍未真打 Models API（本機無 SDK／key）；`refreshed_at` 仍為 `null`。
- `session_start.py` 的 D16 改動沒有新增獨立測試（design 只把它列為「只為 D16 傳參」；既有
  `test_session_start_rules.py`／`test_timeout_checker.py` 跑過確認無回歸，但沒有一支直接斷言
  session_start 的 `recovery_hint` 輸出帶水位——建議由後續收尾窗口補一支整合測試）。
- Dev-B 完成根層 guard-line 棘輪重釘（`test_adr_xplat001_c1c2_lock.py` 97056→97210）後，該檔另有 5 個測試
  要求本輪（R144）在**兩個不同檔案**（`docs/04_planning/AutoSDD_improving_*.md`、
  `docs/06_quality/CrossPlatform_R*_Scan_Findings.md` 或 `docs/04_planning/R*_HANDOFF.md`，三選二）寫入
  `<!-- guard-total:R144 -->` 形態標記——本輪 `AutoSDD_improving_112.md` R144 段刻意只留佔位行（見該檔），
  數字待喚醒鏈（DEF-200-281）棘輪重釘完成才能一次定案，故這 5 支測試（
  `test_a_broken_arithmetic_in_the_real_docs_is_red`／`test_a_stale_total_in_the_real_docs_is_red`／
  `test_removing_the_marker_is_red_and_history_rounds_do_not_count`／
  `test_the_docs_cite_the_live_guard_total`／`test_the_extended_doc_surface_covers_the_handoff_without_false_reds`）
  本輪仍紅，留待收尾窗口補上真正的 `guard-total:R144` 數字後一次關掉。

### 喚醒鏈（DEF-200-281）

自願停機喚醒鏈斷裂為獨立缺陷，鑑識、修法、紅→綠逐字與真實 launchd 端到端演練全文見
`docs/06_quality/CrossPlatform_DEF200278_Halt_Handoff_Evidence.md`〈第二輪（2026-09-11；
DEF-200-281 自願停機喚醒鏈斷裂）〉節；缺陷帳本狀態見 `AutoSDD_Defect_Log.md` DEF-200-281。

### D11／D13 複審 REJECT→修復→APPROVE

第五輪 Dev-A 交棒後，複審者（唯讀）用合成重現腳本 `scratchpad/Review/d11_spec_check.py`／
`scratchpad/Review/d13_stage_change_gap.py` 抓到兩個真缺陷並判 REJECT：

- **R-D11**：D11「PENDING × 量不到 usage ⇒ 放行一次」的放行範圍未排除 Rule 9.6 絕對禁令 #3
  （規格檔寫入）——PENDING＋零 usage 時對 `docs/01_requirements/*.md` 之類規格前綴目標的
  Write/Edit 本應仍 deny，卻被 D11 的「量不到就放行一次」短路成放行。
- **R-D13**：D13「per-stage cap 超限 ⇒ session 級標記」的 `first_mark` 判準是全域一次性旗標
  （只認「有無 marker」，不認 stage 是否已換），導致 stage 換過後的新 cap 事件被舊 stage 的
  marker 擋住、拿不到自己的 `abort_report`。

由 Dev-A2（接 Dev-A 的棒）修復：`fsm_runtime.py` 新增 `_is_blocked_spec_write()`／
`FSMRuntime.is_blocked_spec_write()`（R-D11，沿用既有 `_SPEC_TARGET_PREFIXES`／
`_STATES_ALLOWING_SPEC_WRITE`、不複製第二份清單）；`context_ledger_pre.py` 的 D11 分支在放行前
先查 `is_blocked_spec_write()`，命中則 deny（新函式 `_pending_unmetered_spec_deny_reason()`）；
`trigger_auto_compact()` 的 `first_mark` 判準改為「無 marker，或 marker 的 `stage_key` 已不是
目前 stage」（R-D13），`complete_auto_compact()` 的 `observed_effective=True` 出口同步清掉
`cap_exceeded` 殘留標記。兩者皆先紅後綠（新增 4＋2 支測試），複審者重現腳本核實：
`d11_spec_check.py` 情境 A（PENDING＋零 usage＋Write 規格檔）從 `denied=False` 變
`denied=True`；`d13_stage_change_gap.py` 第二次（stage-B／sess-B）cap 事件從
`abort_report=None` 變成非 None 且 marker 正確更新為 stage-B。修復後複審轉 APPROVE。

全套驗證：`SDD_ENABLE_RULE_FIRE_TELEMETRY=0 SDD_ENABLE_RULE_CATCH_TELEMETRY=0 python -m pytest tools/fsm_runtime/tests/ -m "not chaos" -q -p no:cacheprovider` →
`1866 passed, 8 skipped, 34 deselected, 14 subtests passed in 48.42s`，rc=0（[他包回報]，Dev-A2）。

### 治理 yaml 污染事件與還原

本輪期間發生一次治理 yaml 污染：某探針（Dev-C 效能量測腳本）漏加
`SDD_ENABLE_RULE_FIRE_TELEMETRY=0 SDD_ENABLE_RULE_CATCH_TELEMETRY=0` 前綴，觸發
`transition()` 的 `rule_loader.record_state_fires` 以 `yaml.safe_dump` 回寫，導致
11 支 tracked `governance/rules/R-9.*.yaml` 被重新排版（形態改變＋`fire_count` 灌值，非本輪
刻意變更）。主控（收尾單人窗口）發現後以 `git show HEAD:<path> > <path>` 逐支還原：10 支完全
還原為 HEAD 版本；`R-9.2-context-budget.yaml` 因本輪 D13 確實需要修改其 `failure_mode:` 文字
（session 級語意），改為手動重寫為只含 D13 語意改動的版本（不含污染帶來的形態重排與
`fire_count` 灌值）。還原後 `git status --short -- AISDLC_SDD/AISDLC_SDD_v0.30/governance/`
只列 R-9.2（其 `failure_mode:` 文字改動屬本輪合法變更，非污染殘留）。還原後主控親跑 SDD 全套：

```
$ SDD_ENABLE_RULE_FIRE_TELEMETRY=0 SDD_ENABLE_RULE_CATCH_TELEMETRY=0 python -m pytest tools/fsm_runtime/tests/ -m "not chaos" -q -p no:cacheprovider
1872 passed, 8 skipped, 34 deselected, 14 subtests passed in 42.16s   rc=0
```

（1872 為 D11/D13 複審修復＋Dev-C 稽核帳本效能修復＋喚醒鏈第二修復包全數併入後的最終基線；
較 Dev-A 段落〈實測〉的 1866 多 6，來自 Dev-C 新增的 `LedgerPerformanceTests`／
`LedgerOrphanPartCleanupTests` 四案與另外兩案收斂。）

### 稽核帳本效能（DEF-200-282）

**觸發**：本場多次收到 `[SDD-ROUTER][WARN] context_ledger_post.py 逾 8.0s 未回應，已中止
child 並本次放行`——守門被靜默放行的實證。主控親跑 post hook 端到端修前 5.09s／5.83s。

**量測拆解**（Dev-C，1500 筆／364.6KB 夾具，貼近 `context_ledger_post.py` 真實 entry 形狀；
cProfile，`append_ledger_entry` 單次呼叫）：safe_load 佔 ~63%（0.4082s）、safe_dump 佔
~37%（0.2509s）；鎖等待與 merge 邏輯本身 <1ms（可忽略）。>95% 時間落在純 Python
`yaml/scanner.py`／`yaml/composer.py`（load）與 `yaml/serializer.py`（dump），隨帳本大小線性
增長，終究撞上 router 8s child timeout。附帶發現孤兒 `.part.<pid>`：router 砍 child 時
`_atomic_write_yaml` 寫到一半的 pid 專屬暫存檔沒有任何人清理，同目錄永久累積（現場實測 7 個、
0～530KB 不等）。

**修法**：`AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/conversation_ledger.py` 改用
libyaml C 綁定（`yaml.CSafeLoader`/`yaml.CSafeDumper`，`getattr` 保底回純 Python）——量測顯示
>95% 耗時落在純 Python YAML 編解碼本身，換一個 C 加速的相容實作即可線性換算成本（6-7 倍），
格式、鍵結構、`entries`/`conversation_overhead`/書籤/sidecar/corrupt-rotate 語意完全不變。
未採「entries 移出 YAML 到 JSONL sidecar」（`fsm_runtime.py::_reset_today_ledger()` 直接呼叫
`_load_ledger_doc`/`_atomic_write_yaml` 並自行操作 `entries` 列表，繞過公開介面，格式一變這個
既有呼叫端會在不知情下寫壞主檔）與「entries 上限滾動」（同樣的相容性風險，複雜度不亞於前者但
收益不明顯更好）兩個候選。另新增 `cleanup_orphan_part_files(ledger_dir)`：清掉 mtime > 600s 且
pid 已死（POSIX `os.kill(pid,0)`；Windows `psutil.pid_exists()` 若可用，否則保守回 True）的
`.part.*`；`append_ledger_entry` 開頭 best-effort 呼叫。

**前後耗時**（同一夾具）：
```
修法前：append_ledger_entry wall time: 0.6567s
修法後：append_ledger_entry wall time: 0.1192s   （_load_ledger_doc 0.0579s + _atomic_write_yaml 0.0520s）
```
真實活帳本端到端（802KB／2026-09-11 當日帳本）：
```
$ echo '{}' | /usr/bin/time python3 .claude/hooks/context_ledger_post.py
{"hookSpecificOutput": {"hookEventName": "PostToolUse"}}        0.42 real         0.40 user         0.02 sys
rc=0
```
較主控實測基線 5.09s/5.83s 快 ~12x；孤兒 `.part.*` 清理前 9 個、跑完本輪測試與一次真實 post
hook 呼叫後僅剩 2 個（皆 <10 分鐘齡，設計上刻意保留待下次呼叫再清）。

**複審結論**：APPROVE。**備註**：AISDLC_SDD 未宣告 `psutil` 依賴 ⇒ Windows 側孤兒 `.part.*`
清理的 `psutil.pid_exists()` 分支實質 no-op（`psutil` 不可 import 時保守回 `True`，即「當作活
著、本次不清」）——方向安全（fail-safe，不會誤刪還在寫入的檔案），但 Windows 上孤兒清理功能
本身目前不生效，僅本 macOS/Linux 分支（`os.kill(pid,0)`）已在本機驗證兩種分支。

新增回歸測試：`LedgerPerformanceTests`（1500 筆規模 append/merge 各 <0.3s 硬性驗收）／
`LedgerOrphanPartCleanupTests`（死 pid＋逾時清除／死 pid＋未逾時保留／活 pid＋逾時保留／
`append_ledger_entry` 整合面自動觸發清理，四案）。全套：
```
$ python -m pytest tools/fsm_runtime/tests/test_conversation_ledger.py -q
31 passed in 1.87s
```
未改動 `merge_conversation_overhead_into_ledger` 既有書籤/rebaseline/corrupt-rotate/sidecar
語意——27 支既有測試（本輪新增 4 支，共 31 支）全綠，未動任何既有斷言。詳見缺陷帳本
`AutoSDD_Defect_Log.md` DEF-200-282。


## 第六輪（2026-09-12；四方獨立複審再判 REJECT ⇒ D17～D26）

### 觸發（掌舵者原話逐字）

第五輪 commit fda2903 push 後，掌舵者要求再做一次獨立複審，並限定「派 Subagent 時使用 Sonnet 5！你當主控 Agent 還是使用 Fable 5.1」、「以 AISDLC 的程序……省去非必要文件，只留一定需要文件」：

1. 「我用終端 claude 都會出現以下問題，才開新視窗，就說他被擋不能寫檔案用工具了，然後也不去查真實的數據」
2. 「模型都不用真實的 /context 或 API 去查真實數據」
3. 「印出的 context 數字與 /context 明顯不符，直接告訴我，那就是新缺陷。==> 好像沒有，請確認！」

另附：「從 ~/.zshrc 移除 SDD_HOOKS_DRY_RUN=1 ==> 已經移除」（本輪現查 `~/.zshrc` L10 為註解行 `# SDD_HOOKS_DRY_RUN=1`，行程環境無該變數）；
「誠實劃界（已登記另案）：Windows 未真機驗證；並行 subagent 共用專案級狀態檔（DEF-200-279）；SDD hook 沒攔 Agent／Workflow 工具（DEF-200-280）；Models API 表仍是種子值 ==> 這個我要如何解決！」；
「派出 Architect / SA / SD / QA 四方專家獨立審查，請確認以上都已經修好！」

主控開場實測（同 session、派工前）：`python tools/session_resume_planner.py --check` ⇒ `used 99,017／window 967,000〔指定值（環境變數 AUTOSDD_CONTEXT_WINDOW）〕／model claude-fable-5-1／水位 10.2%`；
逐字稿最後一筆 assistant `usage`＝`input_tokens=2, cache_creation_input_tokens=12363, cache_read_input_tokens=86652` ⇒ 手算 99,017，與 --check 一致。
SessionStart hook 逐字：「[SDD-CTX] 量測＝逐字稿 API usage；transcript_path=有；尚無可用 usage（不 gating）」，`current_state: SPEC_DRAFTING`（本 session 開場**未被擋**）。

### 四方判決與收斂發現（Architect／SA／SD／QA 皆 Sonnet 5、唯讀、各自隔離重現，不互相溝通）

| | Architect | SA | SD | QA |
|---|---|---|---|---|
| P1 新視窗被擋 | PARTIAL | PARTIAL | PARTIAL | PARTIAL |
| P2 不用真實數據 | PARTIAL | PARTIAL | PARTIAL | **FIXED** |
| P3 數字與 /context 不符 | CANNOT_VERIFY | PARTIAL | PARTIAL | **FIXED** |
| overall | REJECT | REJECT | REJECT | REJECT |

四方對第五輪 D11～D16 的機制面**皆親跑核實成立**（Architect：hook 測試 65 passed rc=0；QA：D11／D13／D16 逐案重現與宣稱逐字相符）。REJECT 指向的是**修復範圍外**的殘餘路徑：

- **F-ARCH-01／QA-C1（新，P1）**：任何非 context 來源的專案級 ESCALATION（R-9.1 重試預算、R-9.23 human-pending 逾時…）對全新視窗第一擊仍無條件 deny，且訊息零溯源（不知是哪個舊視窗、何時、為何寫的）。Architect 以合成重現 `DENIED_ON_FIRST_TOOL_CALL_WITH_NO_USAGE_MEASURED = True`，並以 `claude -p --debug hooks` 即時讀到本 repo 2026-09-10T16:44:57 真實 decision_trace 的 `ESCALATION->RESUME_VERIFICATION [human_resume]` 一筆。[他包回報]
- **SD-01（P1）**：per-stage cap 計數器 `count_per_stage`／`cap_exceeded` 只以 stage_key 為鍵、跨 session 共用；SD 親跑：session-A 觸發 4 次超限後，**從未觸發過的** session-B 第一次 ≥95% 呼叫即 `cap_exceeded=True`，deny 訊息印「本 session 已 N 次觸發」——對 B 而言是假話。[他包回報]
- **SD-02／F-ARCH-03（DEF-200-279 本體）**：`FSMRuntime.bootstrap()` 零參數、三支 hook 從未用 `load_track_state`；`AUTO_COMPACT_PENDING` 是專案級，別的 session 觸發即牽連新 session（ARCH-03 乒乓）。Architect 警告：天真整份拆 track 會讓 R-9.1 重試預算／R-9.5 ESCALATION 斷路器失效（治理倒退），須先定範圍。
- **F-ARCH-02（新，P1）**：DEF-200-280 原修法只改 v0.30 settings.json；但 Claude Code 只載入啟動目錄的 `.claude/settings.json`——在 monorepo 根開 claude 時生效的是**根層** `sdd_hook_router` 那條 matcher，它同樣缺 `Agent|Workflow`，而同檔緊鄰的 `context_budget_guard` 條目 R80 已加（8,106 次真實 tool_use 量測）卻沒同步。Architect 以 `claude -p --debug hooks` 證實只有根層 settings 被載入。[他包回報]
- **SD-09（P2；＝P3 的根層另一半）**：根層 `context_budget_guard.py` 無 D14 同型查表收斂階；指定值≠實跑模型視窗時根層 ratio 仍會算錯。SD 判：**不是新缺陷**，是 DEF-200-275 證據檔自陳「本輪未做」的另一半；建議把 DEF-200-275 狀態改寫為「SDD 側已收斂；根層守衛見 D21」。
- **QA P3 實測**：手算逐字稿／SDD `context_window.measure()`／根層 `--check` 三路徑數字**完全一致**（與主控開場實測同型）⇒ SDD 側無「印出數字與 /context 不符」新缺陷。[他包回報]
- **SA-01～03（新，P2/P3，文件面）**：`SDD_CONTEXT_GOVERNOR.md` L189 恢復指令寫死凍結基線 `cd AISDLC_SDD_v0.01`；L23 `model_reference` 稱 sonnet-4-6 為 200K 而查表為 1,000,000（自我矛盾）；L158 仍用 `cumulative_ratio` 舊詞；QA 另指 step_3～step_5 仍是 cumulative_tokens 舊敘述。
- **SD-04～SD-08（既有殘留，非新）**：prepare 閂鎖鍵缺 sid；`announced_latches`／`remember_latch` 非原子；D15 佐證窗口全場不分時間（kind=/band=/cap= 一出現就整場靜音）；INV-H3 未做；`_sentinel_tick` 空 session_id 降級路徑無測試。
- **Models API 種子值**：SA 以 claude-api skill 查證 SDK 憑證鏈（`ANTHROPIC_API_KEY` → `ANTHROPIC_AUTH_TOKEN` → `ant auth login` profile → …）**不含** Claude Code 自身的 Keychain OAuth 憑證；本機 `.venv` 無 `anthropic`、環境無 key。[他包回報]
- 四方 `git status --short` 皆為空（探針零污染）。

### 裁決 D17～D26（總架構師定案；被否決意見括註）

> 全文＝主控 scratchpad `r6_decisions.md`（含派工矩陣與全包共同紀律）；此處為定案摘要。

- **D17（F-ARCH-01／F-ARCH-04 ⇒ 新立 DEF-200-283）ESCALATION 溯源＋首擊訊息完整化**：**不**放行 ESCALATION（R-9.5 人工介入不動；否決「量不到就放行一次」擴大到 ESCALATION）。每一處寫入 ESCALATION／ESCALATION_FINAL 的站點落 `escalation_provenance{session_id, at, reason, rule_id, source}`；deny reason 與 SessionStart 皆印「由 session X 於 T（N 小時前）因 R 寫入；本 session 是／不是觸發者」＋一行可複製的恢復指令；首擊 m=None 亦然；`_ESCALATION_STATES` 擴到 TOKEN_BUDGET_CRITICAL／TERMINATED。
- **D18（SD-01；DEF-200-279 第一刀）**：cap 計數器與標記改 (stage_key, session_id) 鍵，保留專案級彙總供 R-9.2 catch 記帳；deny 訊息只對真正觸發者說「本 session 已 N 次」。
- **D19（SD-02；DEF-200-279 第二刀）PENDING 改「持有者範圍」gating，不動 FSM 狀態集／邊／TLA**：進 PENDING 時記 `pending_owner{session_id, at, transcript_path}`；只有 owner 受「只准 compact」限制；非 owner 量得到 ratio<0.90 ⇒ 放行且**不釋放**；非 owner m=None ⇒ D11 放行一次；釋放只准 owner 自己或 owner 已陳舊（transcript 不存在或 mtime 距今 > `SDD_PENDING_OWNER_STALE_SECONDS`，預設 1800）。（否決「維持任何 session 皆可釋放」——那是 ARCH-03 乒乓的根源。）
- **D20（F-ARCH-02／SD-03；DEF-200-280）**：根層與 v0.30 兩份 settings.json 的 SDD PreToolUse matcher 皆加 `|Agent|Workflow`；根 CLAUDE.md 機械守衛總表同列同步；根層 `test_check_hooks_liveness.py` 加正面斷言＋v0.30 新測試檔 `test_settings_matcher_r145.py`。
- **D21（SD-09）**：根層 `context_budget_guard.py` 補查表收斂階，資料**只有一個家**（`AISDLC_SDD/<LATEST>/tools/fsm_runtime/data/known_model_windows.json`，經 `tools/lib/sdd_latest.py` 解析；缺檔 fail-open）；`--check` 印收斂證據。（否決根層另存一份查表——DEF-101-778 判例。）
- **D22（SD-04／SD-05）**：prepare 閂鎖鍵加 sid；`announced_latches`／`remember_latch` 原子化（O_EXCL 或平台分支檔鎖）。
- **D23（SD-07／SD-08；INV-H3 收斂版）**：halt 標記未過期時 --pace／--check 印「halted，reset 於 T」而非 unmeasured，**不打 API**（否決 halt 期間真打 usage 端點）；`relay_problems` 空 session_id 體檢；`_sentinel_tick` 消費 halt 標記的端到端測試（monkeypatch `_register_and_record`）。
- **D24（SD-06）**：D15 佐證窗口從「全場」收斂為「本回合＋前一回合」（倒數第二則 user 訊息之後）；4 筆假紅普查案例須仍不誤報＋新增「兩回合前舊證據不得免罰」合成案。
- **D25（SA-01～03／QA 文件項）**：`SDD_CONTEXT_GOVERNOR.md` L23／L158／L189／step_3～step_5 改新語意；`AISDLC_SDD_INIT.md` session_resume 段只在有舊語意字樣時改。
- **D26（Models API 種子值）需憑證、不可自動化**，交掌舵者執行（指令見〈未做事項〉）。
- **SA-04**：只做加法——snapshot／abort_report 加 `"numerator": "transcript_api_usage"` 鍵，不改既有欄位名。

派工：Dev-A（D17／D18／D19／SA-04：v0.30 hooks＋fsm_runtime）／Dev-B（D20：兩份 settings.json＋根 CLAUDE.md 一列＋佈線測試）／Dev-C（D21／D22／D23：根層 guard／quota／planner＋測試）／Dev-D（D24／D25：兩份 SDD 文件＋check_claim_provenance.py）四包 Sonnet 5 並行，鎖持有面互斥（矩陣見 `r6_decisions.md`）；棘輪表／ONBOARDING／帳本／證據檔由收尾單人窗口統一處理。

### 修法逐檔（四包並行，皆 Sonnet 5；細節與紅→綠逐字見各包回報，標 [他包回報]）

**Dev-A（SDD 治理面；D17／D18／D19／SA-04）** [他包回報]
- D17：`state_loader.py`／`fsm_runtime.py` 的 `record_escalation()`（fsm_runtime.py 全部 8 個 ESCALATION 生產落點的唯一寫入函式：R-9.7／R-9.1／R-9.3／implementation-budget／R-SELF-STRIDE／R-9.21／R-9.22／spec_patch-no-draft）落 `escalation_provenance{session_id, at, reason, rule_id, source}`，缺值寫 `"unknown"`；ESCALATION_FINAL 只從 ESCALATION 經 `transition()` 轉出，天然繼承同一份 provenance。`recovery_hint.py` 新增 `caller_session_id` 與溯源行（「由 session X 於 T（N 小時前）因 R 寫入；本 session 是／不是觸發者」，provenance 缺席時印「無法確認」）；`context_ledger_pre.py` 的 `_ESCALATION_STATES` 擴到 TOKEN_BUDGET_CRITICAL／TERMINATED（F-ARCH-04）；`session_start.py` 同步。新測試 10 支（`EscalationProvenanceTests`／`RecoveryHintProvenanceTests`／`EscalationRecoveryHintTests` 三案），紅（8 failed, 4 passed）→ 綠（86 passed）。
- D18：`fsm_runtime.py` 新增 `count_per_stage_by_session`／`cap_exceeded_by_session` 逐 session 分桶，`cap_exceeded` 判定改讀分桶；舊 `count_per_stage`／`cap_exceeded` 保留為專案級彙總（R-9.2 catch 記帳零改動）。hook `_cap_exceeded_deny_reason()` 新增 `other_session_id` 兩分支措辭，並修正既有「把 `max_per_stage` 當次數印出」的小 bug；`context_ledger_post.py` 同步。4 支既有測試因手動預置舊格式 state 補分桶種子值。紅→綠 127 passed。
- D19：`trigger_auto_compact()` 進 PENDING 落 `auto_compact_state.pending_owner{session_id, at, transcript_path}`；`assert_tool_allowed()` 新增 optional `session_id`（17 處既有呼叫端零改動）——非 owner 不受「只准 compact」限制、Rule 9.6 規格檔仍以同一份 `_is_blocked_spec_write` 擋；session_id 缺席或無 owner 記錄 ⇒ fail-closed 維持舊語意。hook 新增 `_owner_is_stale()`／`_pending_owner_stale_seconds()`（env `SDD_PENDING_OWNER_STALE_SECONDS`，預設 1800），D4/C5 釋放分支改為「owner 自己釋放，或非 owner 但 owner 已陳舊」。`complete_auto_compact()` 刻意不改（ARCH-03 底層 API 定位不變）。`PendingOwnerScopeTests` 7 案先紅後綠；`test_release_and_trigger_sessions_are_recorded` docstring 明改為 D19 語意。TLA／`transition_rules.py` 狀態集零改動。
- SA-04：cap_exceeded 分支的 abort_report `extra_context` 加 `"numerator": "transcript_api_usage"`（不改 `cumulative_tokens` 鍵名）；`save_auto_snapshot()` markdown 加「分子來源」一行。泛用 `save_abort_report()` 其它 category 刻意不加（其 extra_context 不含 token 欄位，加了是假話）。
- Dev-A 收工全套：`1896 passed, 8 skipped, 34 deselected, 14 subtests passed in 45.54s` rc=0；`test_tla_python_sync`／`test_md_python_sync` `10 passed, 1 skipped` rc=0；`governance/` 零 diff。

**Dev-B（佈線；D20）** [他包回報]
- 讀碳確認兩點後才動工：`sdd_hook_router.py` 對 argv[1] 分派、對 tool_name 零過濾；`FSMRuntime.assert_tool_allowed()` 對 `_BLOCKING_STATES` 的 deny 只看 `state.current`、與 tool 名稱無關，`_is_blocked_spec_write()` 只在 Write／Edit 生效 ⇒ `context_ledger_pre.py` **不需**為 Agent／Workflow 改碼（`AgentWorkflowGatingTests` 三案改 matcher 前已綠——驗證的是「不需改碼」本身）。
- 改：根層 `.claude/settings.json` 與 v0.30 `.claude/settings.json` 的 SDD PreToolUse matcher 皆加 `|Agent|Workflow`（各加 `_comment`）；根 CLAUDE.md 機械守衛總表 sdd_hook_router 列 PreToolUse 格加「Agent／Workflow」；`tools/tests/test_check_hooks_liveness.py` 加正面斷言 `test_root_sdd_hook_router_pretooluse_matcher_includes_agent_and_workflow`（未動 `_REGISTRATION_BASELINE` floor 表，同 R80 慣例）；新檔 `tools/fsm_runtime/tests/test_settings_matcher_r145.py`（4 案）。
- 收工：`test_doc_loc_baseline_freshness_r60 test_check_hooks_liveness` `Ran 449 tests … OK (skipped=5)` rc=0；新檔 `4 passed`；`hook_wiring.SHELL_FORM_CENSUS` 不受影響（判準只看 exec form）。

**Dev-C（根層守衛／額度；D21／D22／D23）** [他包回報]
- D21：`context_budget_guard.py` 新增 `known_model_windows_path()`（經 `tools/lib/sdd_latest.resolve_latest_root()` 解析 LATEST，四種失效皆 fail-open 回 None，**不另存副本**）＋查表收斂階（語意逐項對齊 SDD `_converge_pinned_window`：只在查表值＜指定值時收斂、同族交叉否決）；`window_evidence()` 只在至少一階有指定值時才查表；`--check` window 行印收斂證據。新檔 `tools/tests/test_root_guard_known_model_r145.py`（16 passed, 2 subtests）。
- D22：`quota_prepare_actions()` 閂鎖鍵改 `prepare@{sid}@{kind}@{reset[:16]}`（sid 經 `resolve_halt_transcript`，淨零行）；`announced_latches`／`remember_latch` 從「單一 JSON 整讀→union→整寫」改為「每 key 一個 `O_CREAT|O_EXCL` 標記檔」（同 `quota_ledger.py` 既有慣例；同 key 競爭輸方安靜跳過，冪等）。`PrepareLatchIsSessionScopedTest`／`AtomicLatchStorageTest` 新增；既有 `QuotaPrepareBandActuallyPreparesTest` 重置手法改 `rmtree(_latch_marker_dir)`。
- D23：`quota_messages.halted_band_line()` 純函式；`quota_gate.pace_report()` 加 sid、halt 未過期時最前面短路印「halted，reset 於 T」、**不進 `pace_state()`**；`relay_problems()` 加空 session_id 體檢；`--check` 同款顯示。收工前發現 `endurance_env.trace_dir()` 在唯讀探測時也會 mkdir、弄紅既有「--check 不寫檔」契約 ⇒ 加 `_halt_marker_probe_path()`（只讀路徑存在性、不建目錄）並補 `HaltMarkerProbePathDoesNotCreateDirectoriesTest`。新檔 `tools/tests/test_sentinel_tick_e2e_r145.py`（2 案：`arm_reset` 真走到 `_register_and_record`／`probe` 真交棒 `_resume_tick`，monkeypatch 排程副作用、不 mock 判定層；**誠實**：兩案對修前碼亦綠，屬覆蓋補強非修復證據）。
- LOC（Dev-C 逐次量）：`context_budget_guard.py` 1088→1083（special tier budget 1089；靠搬 21 處歷史敘述到史料檔抵銷，見下節）；`quota_gate.py` 495→499/500（headroom 1）；`session_resume_planner.py` 750/750（headroom 0，靠把 `main()` 內 4 支 `if X: return Y` 併單行換出等量）；`quota_messages.py` 186/400。`check_loc_budget.py --json`：`total_violation=False special=[] root_tools=[]`。
- 收工：`test_context_budget_guard test_wake_chain_halt_r278 test_quota_policy test_root_guard_known_model_r145 test_sentinel_tick_e2e_r145` `Ran 943 tests in 32.159s OK (skipped=10)` rc=0；ruff `All checks passed!`；`~/.autosdd/traces` 零 `halt_*` 洩漏。

**Dev-D（文件＋D15 窗口；D24／D25）** [他包回報]
- D24：`check_claim_provenance.py` `_INTERESTING` 前篩加 `"role":"user"` 兩種字面；新增 `_is_genuine_user_turn()`（content 純 tool_result block ⇒ 中繼、非真人發言；本機 47 筆 role=user 逐筆核對）；`_read_transcript()` 回 3-tuple（新增 `user_turns` 落款清單）；新增 `_block_claim_evidence()`：真人 user 訊息 <2 則退回全場（既有 4 筆假紅普查案例與 hook-wiring 測試語料零 role=user，行為不變），否則邊界＝倒數第二則真人訊息落款（`>=` 算數、解析不到當「之後」收進，fail-open 方向）。純函式 `unbacked_block_claim_hits()` 簽名不變。檔頭「第五個判準」段新增「證據面窄化」小節。新測試 3 支，`Ran 67 tests OK`。
- D25：`SDD_CONTEXT_GOVERNOR.md` L189 `cd AISDLC_SDD_v0.01` → `<LATEST>`（加註現查 `python scripts/sdd_version.py`）；L23 `model_reference` 改「分母依 `context_window.resolve_window()` 分母鏈現查」；L160（原報 L158）`cumulative_ratio` → 真實 usage ratio；step_3～step_5 改寫為真實 usage gating＋D19 PENDING 持有者／陳舊語意（Dev-D 自陳依裁決文字寫、未親讀 Dev-A 程式碼——修後複審 SA 主責核對）。D17／D18 在該檔無可掛載段落，未杜撰。`AISDLC_SDD_INIT.md` session_resume 段 grep 零舊語意字樣 ⇒ 依規則不動。全套 `1885 passed`（Dev-A 同時在改）rc=0。

**單點補修（chaos 舊債）** [他包回報]：`test_chaos.py::test_auto_compact_rate_limit_triggers_escalation`（在乾淨 HEAD fda2903 副本主控親測 `1 failed in 0.15s`——D13 起 cap 超限不再進 ESCALATION，此測試自第五輪起即紅、只在 nightly `-m chaos` 才會跑到）改名 `test_auto_compact_rate_limit_halts_at_cap_exceeded`：連續 `MAX_AUTO_COMPACT_PER_STAGE` 次皆允許，第 N+1 次 `cap_exceeded=True`／`escalated=False`／`current` 非 ESCALATION／cap 標記帶觸發 session_id；docstring 引 D13／D18。`-m chaos`：`34 passed, 1904 deselected in 14.10s` rc=0。

**收尾窗口（主控）**：`tools/lib/skip_tag_policy.py` `_TREE_FILE_FLOORS` 重釘 `tools/tests` 56→58、LATEST fsm tests 62→63（`run_root_unittests.py` 前置掃描第三向逐字指示；四包停工後所量）；三處程式碼註解移除超前帳本的 R 號；`tools/tests/test_sentinel_tick_e2e_r145.py:156`／`test_wake_chain_halt_r278.py:312` 兩行 EAW 寬度 >100 的新行折行（Dev-C 用 `# noqa: E501` 想略過，但 `_overlong_line_count` 量的是實際顯示寬度、不看 noqa）；缺陷帳本補立 DEF-200-283。

### 史料搬遷（D21／D22 LOC 抵銷：Dev-C 自 `.claude/hooks/context_budget_guard.py` 搬出的原文，逐字保全）

> 依〈護欄層成長用搬史料抵銷〉紀律：判準不砍、歷史敘述搬到證據檔。以下為 Dev-C 暫存檔 `scratchpad/dev-c/moved_lore.md` 全文。


## 模組頂端 docstring（原文，D21 前）

```
"""PostToolUse 守衛：Claude Code session 的 context 水位觀測者（本 repo 首見）。

WHY
---
掌舵者連續多輪指名要兩件事：「注意上下文是否超出 90%，進行 /compact，不要爆」與
「注意 Token 限制，適當進行排程再喚醒繼續處理」。四處實查（哪四處、當時各量到什麼，
逐字保全於 `docs/06_quality/CrossPlatform_R91_Scan_Findings.md` §A-1；R91 搬出，理由是
其中的 `claude --version` 讀數已隨版本過期，而過期的量測值住在契約文件裡會被當成常數）
的結論只剩兩句仍在約束今天的行為：**沒有任何既有 hook 在看 context 水位**，以及
**harness 自己的 autocompact 預設開啟**（姿態現查 `--check-autocompact`，見下一節）。

🔴 因此本檔的角色被明確收斂（別讓一個東西假裝能做兩件事）
--------------------------------------------------------
「不要爆」這件事**主要由 harness 的 autocompact 做**，本檔做不到——hook 不能執行
`/compact`，模型也不能自己打 slash 指令。本檔是那條線的**第二道**：
  ① 把「現在幾 %」變成看得見的數字（harness 的 autocompact 不告訴你水位）；
  ② 在 ≥94% 時**真的擋下展開型工具**（見下方〈PreToolUse 阻斷模式〉）——因為
     autocompact 觸發時會丟掉舊訊息，而「丟掉什麼」不由使用者決定；在那之前把
     戰場收斂掉，才是掌舵者要的「不要爆」。
  ③ 產出「可重啟點任務書」骨架，供 token 用完後 `claude -r` 續跑。
harness 那一半的姿態是**可現查的**：`python tools/session_resume_planner.py
--check-autocompact`（autocompact 被關掉時 rc=1）。

🔴 與 SDD `context_ledger` 的分工邊界（**先查過再寫，本檔不是重複造輪子**）
------------------------------------------------------------------------
repo 內確實已有一套帶 90% 門檻的 context 機制（SDD 各版目錄的 `context_ledger_pre/post`，
經 `sdd_hook_router.py` 橋接在根註冊面上）。**它不該被廢、也不該被改**（數十個版目錄、
Copy-on-Evolve 凍結、FSM 有依賴）。本檔與它**量的不是同一個東西**，三點逐項實查過——
估算 vs 實測（ledger 的分子只看 `tool_input`，看不到工具輸出／subagent 回傳／對話本身）／
生效條件不相交（ledger 以 `SDD_ACTIVE_VERSION` 為守衛，純根 session 一行都不跑）／
分母不同（Stage 預算 vs context window）。逐條實查數字與 ledger 的常數表逐字保全於
`docs/06_quality/CrossPlatform_R91_Scan_Findings.md` §A-4（R91 搬出：那是另一支檔的實作
細節，抄在這裡就是同一份知識的第二個家，而只有這一份會過期）。

🔴 這個分工論證的**洞**，照實寫（不粉飾）
------------------------------------------
`SDD_ACTIVE_VERSION` 有設時兩者同時活著，而**兩邊都有一條 90% 線**、分子分母都不同 ⇒
同一時刻兩個百分比會不一樣。處置是**標示而非收編**：每一則訊息都印 `MEASURE_LABEL`；
不讀也不寫 ledger 的檔案（耦合會讓凍結版被拖下水）；不因它存在而讓路。
**未解的那一半**：兩者同時觸發時使用者會連拿兩則語氣相近的告警。本檔不試圖去重
（去重需要跨全部凍結版的協議），僅以標籤讓它們可分辨——已知且已接受的限制，不是漏看。

而「純文件約束對當下的模型零攔阻力」在本 repo 已被實證兩次（`block_bash_on_windows.py`
與 `lint_powershell_command.py` 的立案量測，逐字見 `CrossPlatform_R91_Scan_Findings.md`
§A-2）。水位這件事同型且更嚴重——CLAUDE.md 由 session **開場**載入，而「現在幾 % 了」
是每回合都在變的量，靠模型主動想起來去算它，正是決策負荷第一個擠掉的東西。
```
（其餘〈量測面〉〈context window 判定〉〈行為契約〉〈PreToolUse 阻斷模式〉〈相依規則〉
〈R82／Q2-02 職責邊界〉〈回歸鎖〉段落 D21 後仍原文保留在檔內，未搬出，此處不重複。）

## 〈行為契約〉〈PreToolUse 阻斷模式〉〈相依規則〉〈R82／Q2-02 職責邊界〉原文（D21 前）

```
行為契約（PostToolUse＝觀測模式）
--------------------------------
· payload 讀不出來（壞 JSON／空 stdin）→ stderr 一行 ＋ **exit 1**（出聲但不阻斷）。
  🔴 為何不是靜默 exit 0：`tools/tests/test_check_hooks_liveness.py` 的
  `degraded_payload_verdict` 判過——讀不懂輸入時放行，等於讓「送壞 payload」成為
  讓守衛整支消失的免費手段，而且失效時沒有人看得見。同一支判準也說「rc==1＝出聲
  但不阻斷，爆炸半徑為零，合法」，所以這裡取 1 而不是 2。
· 沒有 `transcript_path`／檔案不存在／掃不到任何 usage → exit 0 靜默。這與上一條
  是**不同**的事：那是「輸入壞掉」，這是「量測暫時不可得」（session 剛開場一定會
  走到這裡）。把兩者混同就會變成每次呼叫都出聲的守衛，然後整支被關掉。
· `< 84%` → exit 0 且**完全靜默**（每次工具呼叫都出聲的守衛會被關掉）。
  🔴 R92 掌舵者裁決：閾值 75／90 → **84／94**，理由見 `WARN_RATIO` 旁的 WHY
  （與額度尺 85／95 刻意錯開；84 在機械 autocompact 點之前、94 是它的失效警報）。
· `>= 84%` → stderr 一行 ＋ **同一段文字送進模型 context**（stdout 的
  `hookSpecificOutput`，發射口＝`platform_utils.emit_to_model`），exit 0。
  🔴 R91 立案：exit 0 下 stderr **不進模型 context**（官方契約：PostToolUse 只有 exit 2
  才回饋 stderr）⇒ 這一整帶（75~90%）模型結構上收不到任何訊號，本輪實測 1h49m／45 turns
  零訊號。stderr 保留不動（人與 log 的可見面），新增的是模型那一半——形態與
  `quota_gate.note_degraded()` 逐字同構（那是本通道在 production 的第一個消費者）。
  逃生口 `AUTOSDD_CONTEXT_SIGNAL_OFF` 只關這半條（退回舊的純 stderr），刻意不與
  `AUTOSDD_CONTEXT_GUARD_OFF`／`AUTOSDD_SENTINEL_OFF` 共用。
  🔴 **這一格說什麼，取決於額度那把尺**（`quota_gate.draining()`，零網路、只讀快取）：
  PRD `docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` §4.3 的壓縮觸發
  是**三個 AND**，本 hook 原本只實作了第一條（`K_ctx ≥ 75`）。PRD §0 第 1 條把「額度高時
  觸發 `/compact`」列為**阻斷級**（§2：壓縮要模型讀完整段對話再產摘要 ⇒ 顯著推升 U5h）。
  這個缺陷在 R91 之前是**良性的，正因為它壞著**——沒有人聽那則訊息；換上模型通道會讓它
  真的被執行 ⇒ 分流與換通道必須是**同一個** commit，見 `warn_message` 的 WHY。
· `>= 94%` → stderr 強制指引（含 %、used/window 實數、下一步）＋ 呼叫
  `tools/session_resume_planner.py` 寫出「可重啟點任務書」骨架 ＋ **exit 2**。
  PostToolUse 的 exit 2 會把 stderr 回饋給模型，這正是要的效果；它**不**阻斷已經
  完成的那次工具呼叫（與 PreToolUse 的 exit 2 語意不同，別混淆）。
· **同一門檻＋同一 window 只喊一次**（state 檔在系統暫存，檔名帶 session id）。
  🔴 閂鎖鍵含 window 是 R79 修的那半個缺陷：R78 版只以 tier 為鍵，於是「用 200K
  當分母誤喊一次 90%」之後，等分母修正成 1M、真的到 90% 時**閂鎖還鎖著** ⇒ 該喊
  的那一次被前面那次誤報吃掉。分母一變就重新武裝，對 200K session 零行為改變。
  代價仍明說：模型若無視同一組（門檻, window）的那一喊，本檔不會再喊第二次。

🔴 PreToolUse 阻斷模式（R79 新增——把「不要爆」從散文變成真的擋得下來的東西）
----------------------------------------------------------------------------
R78 版的鏈條是「印一段話 → 模型自己記得去 compact」，而「純文件約束對當下的模型零
攔阻力」在本 repo 已被實證兩次（`block_bash_on_windows.py` 的立案就是這樣來的）。
故同一支腳本另有一個由 payload 的 `hook_event_name` 分派的模式：

  · 只在 `>= 94%` 且 **window 不是保守下界猜測**時擋（`may_block()`）。分母是猜的
    就只出聲不擋——否則今天這個缺陷（1M session 被當成 200K）會直接變成「真實 18%
    就把工具鎖死」，比原缺陷更糟。
  · 只擋**展開型**工具（`BLOCKING_TOOLS`；R80 起含本 harness 真正在用的 `Agent`／
    `Workflow`，見該常數旁的 WHY），註冊面的 matcher 與它逐名對齊。
    Read／Edit／PowerShell 一律放行——根 CLAUDE.md 那句是
    「此後只做收斂，不做展開」，而收斂本身需要讀檔、寫任務書、跑 git。**擋到讓人
    無法收斂的守衛會被整個關掉**，那是本 repo 反覆判過的形態。
  · **不進閂鎖**：擋一次就放行的東西不是阻斷。它會一直擋到水位掉下來為止，而
    `/compact` 之後 used 會真的掉 ⇒ 自動解除，不需要任何人來關掉它。
  · 人為逃生口：環境變數 `AUTOSDD_CONTEXT_GUARD_OFF=1` 一律放行（供人在守衛誤判時
    自救；模型改不到 hook 行程的環境）。這是對 P0 的第二道保險，不是給模型的後門。
· **任何非預期例外 → exit 0（fail-open）**。`.claude/settings.json` 的 description
  記載過 P0：hook 誤觸會把所有工具硬鎖死。守衛自身絕不可成為故障源。

相依規則（R82／Q2-01 訂正：此前寫「本檔只用 stdlib」，而下面幾行就 import 了四支 tools/lib）
------------------------------------------------------------------------------------
①能力提供者（quota_gate／platform_utils）一律 try/except，不可達時該軸退化成「量不到」；
②判讀原語（quota_limits）hard import，給 stub 等於讓同一份字面有第二個家；
③`tools/lib/*` **只准裸名 import**——`from lib import X` 會讓同一份原始碼在同一行程裡
有兩個模組物件（`ModuleIdentityIsSingleTest` 在守）。反向依賴仍允許：planner import 本檔。

🔴 R82／Q2-02：本檔的**職責邊界**（額度軸已經不在這裡了）
--------------------------------------------------------
本檔只剩一把尺——**context 水位**：量它、判 window、越線時出聲／擋展開型工具／寫任務書，
外加哨兵武裝的**觸發面**（R82／HELM-02 起：SessionStart 只清閂鎖，真正註冊延後到
PostToolUse 且要通過 `tools/lib/sentinel_lifecycle` 的雙門檻——立案是掌舵者當場截圖的
「排程器裡三支哨兵，兩支屬於活 5 秒／12 秒的 session」）。額度尺整條住 `quota_gate.py`，本檔對
它只有兩件事：①`main()` 在五道 context 早退**之前**呼叫它一次（撞額度那刻 context 水位
可能只有 ~18%，掛在早退之後的分支一次都不會被執行——那是 SA-B1 判過的死碼）；
②把它需要的四個 hook 端能力注入進去（阻斷名單／閂鎖讀寫／任務書／喚醒武裝）。
兩把尺不共用早退條件、也不共用模組，就是那個設計。既有架構鎖
`test_quota_is_not_wired_into_the_context_blocking_path` 的射程零改變且更容易成立。
```

## `_NEXT_STEP` 上方註解、`spawn_sentinel`／`arm_sentinel`／`spawn_sentinel_gc` 原文（D21 前）

```
#: 84% 那一格的**下一步**，依額度相對 PRD `DRAIN_PERCENT` 的位置三分（`quota_gate.draining()`）。
#:
#: 🔴 立案（R91，PRD 前置條件）：PRD §4.3 的壓縮觸發是**三個 AND**——
#: `K_ctx ≥ CONTEXT_COMPACT_PERCENT`（R92＝84） ∧ `U5h + COMPACT_COST_BUDGET_PP ≤ DRAIN_PERCENT` ∧
#: `距上次壓縮 ≥ COMPACT_MIN_INTERVAL_SECONDS`——而本 hook 原本只實作了第一條，於是它在額度高位照樣
#: 喊 `/compact`。PRD §0 第 1 條把那件事列為 **🔴 阻斷級**，理由在 §2「關鍵釐清」：壓縮
#: 本身要模型讀完整段對話並產生摘要 ⇒ **會顯著推升 U5h**，高位壓縮是反向操作。
#: 本輪之前這個缺陷是**良性的，正因為它壞著**（訊息走沒有讀者的 stderr）；一旦換上模型
#: 通道，它就會**真的被執行** ⇒ 補這一條與換通道必須同一個 commit，否則等於啟動一個
#: 休眠的阻斷級違反。第三條 AND（距上次壓縮的間隔）本 hook 量不到，由「同一門檻本
#: session 只喊一次」的閂鎖近似——**誠實劃界：那是 per (tier, window)，不是 per 時間間隔**。
#: 🔴 第二條 AND 的 3pp 邊際（PRD §6 `COMPACT_COST_BUDGET_PP`）已由 `quota_gate.draining()`
#: 實作（DEF-200-137）：五小時軸 `pct + 邊際 > DRAIN` 亦回 `"yes"`，`(82, 85]` 帶不再勸壓縮。
#: `"unknown"` 不折進 `"no"`：PRD §0 第 6 條明定遙測失效方向為 fail-safe，而「證不出
#: 第二個 AND 成立」與「已證明它成立」是兩件事（同本檔通篇「量不到 ≠ 量到零」的紀律）。

# ───────────────────────── 預防性哨兵的**觸發層**（R79 補洞包；R82／HELM-02 改觸發時機）
# 🔴 SessionStart 只**清閂鎖**（見 `arm_sentinel`），真正註冊延後到 PostToolUse 且要通過
# `tools/lib/sentinel_lifecycle.should_arm()`（回合數＋存活跨度雙門檻）——判準不能寫在
# SessionStart 那一刻，逐字稿那時往往還不存在。為何非預防性不可、三個刻意取捨（detached
# 子行程／逐字稿不存在也照樣武裝／一切例外吞掉）逐字保全於
# `CrossPlatform_R91_Scan_Findings.md` §I-12；立案量測見同檔 §A-6。
def spawn_sentinel(transcript_raw: str, out: str, log: object = None) -> bool:
    """Detached 起 planner 的 `--arm-sentinel`；回「有沒有真的 spawn 出去」。

    🔴 R82／Q2-02 的減法：SessionStart 武裝與額度 95% 喚醒武裝此前是**兩份逐字相同的
    `Popen`**（同一支 planner、同一組旗標、同一個 `creationflags`），差別只有「要不要寫
    boot log」。兩份各自演化的代價已經看得到：R80 修「`DETACHED_PROCESS` 讓視窗回來」
    那一次只改了其中一份。收成一份之後那個漂移在結構上不存在。
    """
    ...
        subprocess.Popen(  # noqa: S603 — 參數全是本檔算出來的路徑，無 shell
            [quiet_python(), str(planner), "--transcript", transcript_raw,
             "--out", out, "--arm-sentinel"],
            stdout=log if log is not None else subprocess.DEVNULL,
            stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            # 🔴 R80：舊寫法帶了 `DETACHED_PROCESS`，而它在**本 venv 的 trampoline 載具**
            # 上會讓視窗回來（矩陣見 NO_WINDOW 第二列：`DET` 與 `DET|CNW` 兩格皆「可見」）
            # ——上面取捨①宣稱的「不彈視窗」在寫下的當回合就不成立，且失效是靜默的
            # （旗標有設、視窗照彈）。**不要把這句讀成「DETACHED 會抵銷 CNW」**：那是本檔
            # 第一版的過度一般化，真直譯器那一列 `DET|CNW` 是 0，翻面的是載具不是旗標語意。
            # 取捨①要的「不同步等它跑完」由「不呼叫 wait()」提供，與旗標無關；子行程活過
            # 父行程退場這件事也已實測不需要 DETACHED_PROCESS（父死 8 秒後子仍寫出痕跡）。
            creationflags=NO_WINDOW)


def arm_sentinel(payload: dict) -> None:
    """SessionStart：**不再直接武裝**，只把上一輪的武裝閂鎖清掉並留一行痕跡。

    🔴 為什麼還要清閂鎖（不是「什麼都不做就好」）：`claude -r` 續接一個已經下班（6 小時
    閒置自我解除）的 session 時，閂鎖若留著就再也不會重新武裝＝續航被靜默弄丟。清掉之後
    下一次工具呼叫會重新評估，而那時逐字稿早就過門檻 ⇒ 立刻補上。
    boot log 保留：它是「SessionStart 有沒有被叫到」唯一的痕跡，而本輪正是靠它才發現
    有四支短命 session 根本沒觸發過這支 hook（沒有 boot log）。
    """

# 🔴 R84／C3-P4b：`sentinel_lifecycle.gc()` 此前**零自動呼叫端**，殘骸哨兵每 15 分鐘
# 照樣醒來（立案實測全文搬至 docs/06_quality/CrossPlatform_Guard_Line_History.md
# 〈context_budget_guard 立案史彙整〉節）；呼叫點選在 SessionStart＝「後來的人開工」
# 那一刻，也是本函式已經在清閂鎖的地方（同一族的清理，不另開第二個時機）。
#
# 三個刻意的取捨，與 `spawn_sentinel` 逐條同構（同一族的風險，同一組處置）：
#  ① **detached 子行程**（`gc()` 要外呼排程器列舉，同步做＝每次開 session 先卡幾秒）；
#  ② **`keep=(當前 sid,)`**（自己的哨兵不能被自己收掉；`gc()` 內另有一層保護，兩層獨立）；
#  ③ **一切例外吞掉**（P0：hook 誤觸鎖死所有工具；回收失敗最多殘骸多留一輪，不可變故障源）。
def spawn_sentinel_gc(keep_sid: str) -> bool:
    ...
```

## `main()` 內 R83 相關大段註解原文（D22 前）

```
        # 🔴 R83：額度軸只在**我們真的推理過的那兩個事件**上動作。少了這一格，接電會順手
        # 把「事件名讀不出來」（壞 payload、未來新增的事件）也當成觀測點——本輪注入實測：
        # 一份沒有 `hook_event_name` 的 payload 會走完整條額度判讀並出聲，而那類 payload
        # 依本檔既有契約應該是「量測暫時不可得 ⇒ 靜默 rc=0」。射程要靠白名單而不是靠
        # 「不是 PreToolUse 就當 PostToolUse」，後者是預設開啟、方向錯的。
        measuring = event in ("PreToolUse", "PostToolUse")
        # 🔴 額度那把尺**必須在這裡**求值，不能往下擺（SA-B1 判過的死碼）。下面五道早退
        # 全是 context 語意，而 `tier_of()` 在低於 WARN_RATIO 時一律回 `None` ⇒ 撞額度那一刻
        # （實測水位只有 ~18~20%）任何掛在 `block_verdict()` 裡的 quota 分支都到不了。
        # 兩把尺不共用早退條件，這一行的位置就是那個設計。
        # 🔴 R83／接電：`blocking and` 這個前綴拿掉了，`event` 改為傳進去。立案是量出來的
        # ——舊條件讓額度那把尺**只在「我要扇出」那一刻**被問一次，而 R83 實測配額 5%→90%
        # 的整段，主 session 派完最後一波之後再也沒呼叫任何扇出型工具（後續全是全樹跑、
        # agent 回傳、大量讀檔）⇒ 本閘從頭到尾一次都沒被叫到。燒額度的是「我自己在做事」
        # 那條路，而 PostToolUse 的 matcher（`Read|Task|Grep|Glob|…|Bash|PowerShell`）
        # **本來就覆蓋**那條路 ⇒ `settings.json` 一個字都不用改，缺的只有這裡的條件與參數。
        # 射程的第二半在 `quota_gate()` 內（PostToolUse 不記派發帳、不擋節流帶），兩邊要一起讀。

            # 🔴 R83／Δ13：**接電引入的新缺陷，必須在同一個 commit 處理。** halt 帶在
            # PostToolUse 會**每一次**回 2 ⇒ 本 hook 在這裡提早 return ⇒ 下面那個
            # `arm_when_earned()` 在整個 halt 期間（一直到 reset）一次都不會執行，
            # context 續航哨兵靜默失去所有武裝機會。而額度那層的喚醒武裝只在 halt 閂鎖
            # **第一次**觸發時試一次、失敗不重試（見 `quota_gate` 的 D2 重排）⇒ 兩層都沒了。
            # 兩層續航是不同的東西（一次性 reset 喚醒 vs 900s 巡邏），不得因為額度那層
            # 說了話就把 context 那層吃掉。`arm_when_earned` 自身有閂鎖與 fail-open。
```

### 未做事項（另案；含掌舵者「誠實劃界 ==> 這個我要如何解決」四項的解法）

1. **Models API 種子值（D26）——需憑證，本輪不可自動化。** `known_model_windows.json` 仍 `refreshed_at=null`（seeded 2026-06-24）。SA 以 claude-api skill 查證：SDK `Anthropic()` 零參數建構子的憑證鏈＝`ANTHROPIC_API_KEY` → `ANTHROPIC_AUTH_TOKEN` → `ant auth login` profile → …，**不含** Claude Code 自身存在 macOS Keychain 的 OAuth 憑證（兩套憑證體系）[他包回報]。掌舵者照做即可（在 monorepo 根）：
   ```bash
   source .venv/bin/activate && uv pip install anthropic
   export ANTHROPIC_API_KEY=sk-ant-...        # console.anthropic.com → API Keys；要持久化再寫 ~/.zshrc
   cd AISDLC_SDD/AISDLC_SDD_v0.30 && python -m tools.fsm_runtime.refresh_known_model_windows
   git diff -- tools/fsm_runtime/data/known_model_windows.json   # rc 0=已刷新寫檔；2=SDK 未裝；3=API 失敗（無憑證／離線）；4=SDK 太舊；非 0 一律不寫檔
   ```
   刷新後若 `claude-fable-5-1` 等值有變，D14／D21 兩層收斂會自動吃到新值（hook 路徑只讀表、永不打網路）。
2. **Windows 真機驗證——需一台 Windows 機器，mac 上結構性做不到。** 本輪與前幾輪所有修法皆為純函式／跨平台碼，理論一致；但 exec form 載具（`pythonw.exe`）、schtasks 憑證、D22 的 O_EXCL 標記檔在 NTFS、孤兒 `.part.*` 清理的 `psutil` 分支（AISDLC_SDD 未宣告該依賴 ⇒ 實質 no-op）都只在 Windows 上看得到。解法：push 後看 `windows-compat-ci` 結論（`gh run list --workflow=windows-compat-ci.yml --limit 3`），並在有 Windows 機器時跑 `powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows_smoke_local.ps1` 與根 CLAUDE.md〈hook 載具〉的正面現查兩條。
3. **DEF-200-279——本輪以 D18＋D19 收斂（session 分桶＋PENDING 持有者範圔），不是原列「hook 串接 `load_track_state`／`track_id`」那條路。** Architect 判：天真整份拆 track 會讓 R-9.1 重試預算／R-9.5 ESCALATION 斷路器失效（治理倒退）；真正要「刻意並行多條 feature track」的情境，才走 `FSMRuntime.bootstrap(track_id=...)` 接線既有 `state_loader.load_track_state`（`fleet_orchestrator.TrackRegistry` 語意對齊）——**另案**，需先寫範圍界定 mini-ADR（哪些狀態留專案級：`current_state`／`retry_history`／ESCALATION／DONE；哪些下放：整個 `auto_compact_state`）。
4. **DEF-200-280——本輪 D20 兩層皆修**（根層 + v0.30）。殘留：`test_check_hooks_liveness.py` 的 `_REGISTRATION_BASELINE` floor 表未回填 Agent／Workflow（floor-only 棘輪本就允許落後，同 R80 context_budget_guard 列慣例）。
5. `endurance_env.trace_dir()` 在「宣稱唯讀」的路徑仍會 mkdir（Dev-C 只在 `session_resume_planner.py` 內用 `_halt_marker_probe_path()` 繞開）；其它呼叫 `read_halt_marker()`／`trace_dir()` 的唯讀路徑同型風險仍在——建議在 `endurance_env.py` 補「peek，不建目錄」介面。
6. LOC 餘裕：`tools/lib/quota_gate.py` 499/500、`tools/session_resume_planner.py` 750/750——下一輪要動這兩檔先量，不得假設有餘裕。
7. SA-04 只在 cap_exceeded 分支加 `numerator` 鍵；泛用 `save_abort_report()` 其它 category 是否加註需逐一核實欄位語意（Dev-A 刻意不做，避免對不含 token 欄位的 category 講假話）。
8. `SDD_CONTEXT_GOVERNOR.md` 無 ESCALATION 溯源／per-stage cap 可掛載段落（D17／D18 語意未進該檔）；是否補一段跨引用 `SDD_ESCALATION_PROTOCOL.md`／R-9.2 yaml 另案。
9. `TOKEN_BUDGET_CRITICAL` 狀態去留（hook 已不進入、無轉入邊；本輪只把它納入 recovery_hint 訊息一致性）、`AUTO_COMPACT_PENDING` 目標集缺 `INIT` 補邊需碰 TLA——沿第五輪未做事項。
10. P2 的「模型行為層」：hook 已把真實數字寫進 additionalContext／deny reason、Stop hook D15＋D24 對無佐證的「被擋」宣稱出聲（永不阻斷）；「模型是否真的據以行動」結構上無法被 hook 保證（Architect 誠實劃界），只能靠根 CLAUDE.md〈現查指令速查表〉＋事後量測器 `tools/probe/audit_session.py`。

### 修後複審（第一次；Architect／SA／SD／QA 皆 Sonnet 5、唯讀）

| | Architect | SA | SD | QA |
|---|---|---|---|---|
| 主責裁決 | D17 **DEVIATES**／D19 ✓／D20 ✓ | D21 DEVIATES（非阻斷）／D25 **DEVIATES**／SA-04 ✓ | D18 ✓／D19 ✓／D22 ✓／D23 ✓／D24 ✓ | D17～D25 全 ✓（實跑面） |
| P1／P2／P3 | PARTIAL／—／— | —／—／**FIXED** | PARTIAL／—／— | PARTIAL／PARTIAL／PARTIAL |
| overall | REJECT | REJECT | **APPROVE** | REJECT |

阻斷發現三筆（全數在同一輪修掉，見下〈複審修復波〉）：
- **ARCH-R6-01（P1）**：D17 的 provenance 只覆蓋 `record_escalation()`；fsm_runtime.py 另有 4 個函式直呼 `self.transition("ESCALATION")`（`exit_learning_commit` 兩分支／`exit_trajectory_predicted` abort_early／`record_dispatch_rejection`／`exit_autoclaude_delegated` failed），既不寫 provenance 也不 append history ⇒ 新 ESCALATION 會**自信地印出上一次已解除事件的舊溯源**（Architect 合成重現：舊 session 的 TOKEN_BUDGET_CRITICAL 原因被套到 dispatch 拒絕觸發的新 ESCALATION 上，連 `--reason` 都帶錯）。比 D17 前「模糊但不誤導」更糟。[他包回報]
- **SA-F2（P2）**：D25 新寫的 step_4 else 分支門檻寫 ≥0.90 比照 owner 限制；SA 親跑探針：非 owner 92% **完全放行**（只 WARN）、96% 才限制 ⇒ 程式門檻是 CRIT 0.95。Dev-D 自陳依裁決文字寫、未親讀程式碼——複審任務書點名的風險正中。[他包回報]
- **QA-R6-01（P1）**：主控補立的 DEF-200-283 帳本列 1481 bytes > `ROW_MAX_BYTES=700`，讓 `test_check_defect_log_crossref` 多 4 紅（超標列 37>36、超標總量 20808>20027）。主控收尾縮至 677 bytes 後 `Ran 278 tests OK`；超標列 36/36、總量 20027/20027 恰回基線。

非阻斷發現（登記，見〈未做事項〉補列）：SA-F1（D21 六種 fail-open 路徑零 stderr，裁決文字要求一行）；SA-F3（hard_stop 回落敘述「<90%」與程式兩種真實門檻 <85%（PENDING 內，`WARN_RATIO`）／<95%（trigger 被壓抑）皆不符——**第四／五輪既有殘留**，第五輪 SA 曾誤判已同步）；SD-RR-01（`state_loader.save_state()` 併發 `.bak` 輪替可拋 FileNotFoundError，既有 try/except 已吞）；SD-RR-02（Dev-A 回報稱 chaos 舊債「仍紅」，但主控已在其收工後另派單點補修轉綠——回報時序差，非矛盾）；QA-R6-02（PENDING／CRIT 下 Bash 一律放行，與「只准 compact 相關操作」措辭字面不完全對應——第四輪 QA-07 既有設計）。

四方 `git status --short` 皆與開工時逐字相同（零污染）。QA P3 判 PARTIAL 的唯一理由＝subagent 結構上不能呼叫互動式 `/context`（三路徑數字仍逐位元組一致：本 session 當時 `used=343,214／window=967,000／35.5%`）——由掌舵者在收尾回覆後親自對照一次 `/context` 即可關閉。

### 複審修復波（Dev-A2／Dev-D2，皆 Sonnet 5；根層 context_budget_guard 擋下 Workflow 後改逐個派 Agent）

**Dev-A2（ARCH-R6-01）** [他包回報]
- 座標訂正：「唯一寫入函式」宣稱住 `state_loader.py` 的 `FSMState.record_escalation()` 註解（約 L261-266），非 Architect 所寫的 `fsm_runtime.py`；已在正確檔案改為真話（列出現在全部 12 個生產落點，並註明 `transition()` 事後重寫 `decision_trace.from` 的既有副作用）。
- 寫入面：4 個繞過站點改為先 `self.state.record_escalation(reason, rule_id=…, source=…)` 再既有 `self.transition(...)`（保留原轉態行為）：`record_dispatch_rejection`（R-9.19.3／`cost_gate_escalation`）、`exit_trajectory_predicted` abort_early（R-9.15.2／`trajectory_predicted_abort_early`）、`exit_learning_commit` meta_halt（R-9.24.1／R-9.24.2 依 ChurnBounded／GraduationRatchet 動態選／`learning_commit_meta_halt`）、`exit_learning_commit` 人工 rejected（`unknown`／`learning_review_rejected`）、`exit_autoclaude_delegated` failed（`unknown`／`autoclaude_delegated_failed`）。`grep -n 'transition("ESCALATION' fsm_runtime.py` 程式碼零殘留（僅 1 筆說明性註解，主控親查亦為 0）。
- 讀取面：`recovery_hint.py` 新增 `_parse_iso()`／`_entered_escalation_at()`（decision_trace 最後一筆 `to=="ESCALATION"` 時間戳，量不到退回 state 檔 mtime）與 `_STALE_PROVENANCE_GRACE_SECONDS=5`（吸收 record_escalation→transition 同呼叫跨秒）；provenance 早於本次轉入超過容錯窗 ⇒ 印「溯源不可信：現有溯源屬於較早、已解除的事件…」，恢復指令 `--reason` 改通用措辭不帶舊原因。
- 新測試檔 `tools/fsm_runtime/tests/test_escalation_provenance_r6.py`（321 行、11 案：Architect 重現改寫／兩形態靜態鎖／4 函式 provenance 斷言／陳舊防呆正反案）。紅（暫時 revert）`9 failed, 2 passed in 0.29s` → 綠 `11 passed in 0.26s`。
- 收工：`1907 passed, 8 skipped, 34 deselected, 14 subtests passed in 44.91s` rc=0；chaos `34 passed, 1915 deselected in 14.58s` rc=0；TLA／MD sync `10 passed, 1 skipped` rc=0；`transition_rules.py`／`formal/` diff 為空；`governance/` 零 diff。

**Dev-D2（SA-F2／SA-F3／SA-F1）** [他包回報]
- 改前**親跑** SA 探針核實門檻：非 owner 92% 只 WARN 完全放行、96% 才 deny（`CRIT_RATIO=0.95`）；96%→PENDING 後降到 88% 仍 deny、82%（<85% `WARN_RATIO`）才釋放。
- SA-F2：`SDD_CONTEXT_GOVERNOR.md` step_4 else 分支拆成 allow（<0.95 僅 WARN 通知，不受 owner 限制）／deny（≥0.95 比照 owner「只准 compact 工具」），加註探針依據。SA-F3：L70 改成兩種真實門檻並寫入常數名（`context_window.WARN_RATIO`／`CRIT_RATIO`）；L80 摘要表同句由主控訂正。全檔 grep `v0.01`／`cumulative_ratio`／「≥0.90 時比照 owner」／「回落 < 90%」零操作性殘留。
- SA-F1：`context_budget_guard.py` 六種查表 fail-open 路徑各一行 `sys.stderr.write`（含失效種類與路徑；「有子專案無版本目錄」與「LATEST 解析失敗」以 `"找不到任何版本目錄" in str(exc)` 分流）；LOC 淨增 11 行撞 `SPECIAL_FILES` 1089 上限 ⇒ 壓縮 `known_model_windows_path()` docstring 8→2 行、原文搬 `scratchpad/dev-d2/moved_lore.md`（見下方史料搬遷補記），改後 1089 行恰在上限、`special_violations=[]`。測試：四支 fail-open 案加「stderr 非空且含關鍵字」斷言，紅（剝除 stderr）`FAILED (failures=4)` → 綠 `Ran 16 tests OK`；其中 `test_aisdlc_sdd_present_but_no_version_directories_is_fail_open` 原夾具只建空殼目錄、實際命中的是「LATEST 解析失敗」，已補真 `sdd_version.py` 使其如實重現該失效種類。
- 收工：`test_root_guard_known_model_r145 test_context_budget_guard` `Ran 641 tests in 29.359s OK (skipped=10)` rc=0；md／tla sync `10 passed, 1 skipped` rc=0；ruff `All checks passed!`；`check_loc_budget.py --json` 三欄皆空。

**主控親跑（兩包收工後）**：SDD `1907 passed, 8 skipped, 34 deselected, 14 subtests passed in 44.98s` rc=0；chaos `34 passed, 1915 deselected in 14.80s` rc=0；`governance/` 零 diff；`transition("ESCALATION` 程式碼命中 0；ruff 12 檔 `All checks passed!` rc=0；`check_loc_budget.py --json` `total_violation=False special=[] root_tools=[]`；根層八支相關測試模組 `OK (skipped=15)`。

#### 史料搬遷補記（SA-F1 LOC 抵銷：Dev-D2 自 `known_model_windows_path()` docstring 搬出的原文）

`known_model_windows_path()` / `load_known_model_windows()` 六種查表 fail-open 失效路徑
（無 AISDLC_SDD 子專案／有子專案無版本目錄／LATEST 解析失敗／表檔不存在／JSON 損毀／
JSON 形狀不對）此前全靜默、零 stderr 輸出。修復＝各補一行 `sys.stderr.write(...)`。

任務書要求：只准在查表 fail-open 分支加 stderr 輸出，其它一行不動；若加了 stderr 讓
`AutoClaude/tools/check_loc_budget.py` 的 `SPECIAL_FILES["../.claude/hooks/
context_budget_guard.py"] = 1089` 棘輪超標（納管當下 headroom 僅 6 行），把等量 docstring
史料搬到本檔，判準（stderr 邏輯）不砍。

實測：六行 stderr 加上必要的 `if`/`except as exc`/`kind =` 輔助邏輯，讓
`known_model_windows_path()` 淨增 9 行、`load_known_model_windows()` 淨增 2 行，共 +11 行
（1083→1094），超過棘輪（1089）5 行。已把 `known_model_windows_path()` 自己的 docstring
（8 行）壓縮為 2 行（原文逐字保留於下），淨省 6 行，最終 1089 行，剛好持平棘輪、不超標。
除這一段 docstring 之外，本檔其餘既有內容（含另一包 Dev-C 在本輪已對本檔做的其他改動）
一律未觸碰。

## `known_model_windows_path()` docstring 原文（搬出前，逐字保留）

```
    """LATEST 版 `known_model_windows.json` 的路徑；解析不到／檔不存在一律 `None`（D21 fail-open）。

    唯一真相源＝`tools/lib/sdd_latest.py`（`resolve_latest_root`，內部再呼叫 `sdd_version.py`
    判定 LATEST）。四種失效都 fail-open、不拋例外：`sdd_latest` 不可達／本機沒有
    `AISDLC_SDD/` 子專案（多數純 AutoClaude 部署的常態，不是錯誤）／LATEST 解析失敗
    （`AssertionError`，`sdd_latest.resolve_latest_root` 的既有契約）／檔案本身不存在。
    """
```

原地保留的精簡版（語意不變，指向本檔）：

```
    """LATEST 版 `known_model_windows.json` 的路徑；解析不到／檔不存在一律 `None`（D21 fail-open；
    四種失效各印一行 stderr，SA-F1 訂正——唯一真相源與失效分類全文見 moved_lore.md）。"""
```

（附註：SA-F1 finding 原文說「四種失效」是 `known_model_windows_path()` 這一層的既有分類
〔`sdd_latest` 不可達／無 AISDLC_SDD 子專案／LATEST 解析失敗／表檔不存在〕；SA 複審黑箱
測試觀察到的「六種失效路徑」把 `load_known_model_windows()` 的 JSON 損毀／JSON 形狀不對
兩種另計。本次實作對六種皆已補 stderr，其中「有子專案無版本目錄」在 `except Exception as
exc` 分支內以訊息內容 `"找不到任何版本目錄" in str(exc)` 與其餘 LATEST 解析失敗區分。）

### 史料搬遷（Dev-Trim；護欄層行數棘輪抵銷：六支測試檔 docstring 敘述原文逐字保全，−87 行）

> 每則被縮短的 docstring 現為「一句 WHY＋裁決編號＋指針本節」；原文如下（來源檔名＋函式名標於各段）。[他包回報]

不做任何改寫。搬遷理由：行數棘輪（連續三輪淨額為正）觸發，測試碼與判準本身
一行未砍，只搬「背景故事／事故經過／審查往來／重複複述的裁決全文」。

---

## tools/tests/test_wake_chain_halt_r278.py

### class HaltMarkerProbePathDoesNotCreateDirectoriesTest（原 docstring）

```
D23 收尾修復：`planner._halt_marker_probe_path()` 是 `--check`（唯讀契約，見
`test_context_budget_guard.py::PlannerCliTest::test_check_prints_usage_and_writes_
nothing`）用來探測 halt 標記存不存在的入口——它本身**不得**觸發
`endurance_env.trace_dir()` 的 `mkdir(parents=True, exist_ok=True)` 副作用，否則
光是「檢查有沒有標記」就會在從沒人寫過標記的機器上憑空長出 `.autosdd/traces` 目錄。
```

### class HaltedBandLineTest（原 docstring）

```
D23（SD-07；DEF-200-275 第六輪）：`quota_messages.halted_band_line()` 純函式——
本 sid 的 halt 標記未過期時印「halted，reset 於 T」，已過期或沒有標記一律 `None`
（呼叫端落回既有判定）。純函式：不讀任何檔，`halt_marker` 由呼叫端已經
`read_halt_marker(sid)` 取得，本測試不碰磁碟。
```

### class PaceReportShortCircuitsDuringHaltTest（原 docstring）

```
D23（SD-07）：`--pace`（`quota_gate.pace_report()`）在本 sid 的 halt 標記未過期時
必須直接短路回「halted」那一行，**不**進 `pace_state()`——後者在快取不可用時可能
補打一次 `/api/oauth/usage`，而 halt 期間不該再花任何一次 API（INV-H3 的殘餘）。
```

### class RelayProblemsCatchesEmptySessionIdTest（原 docstring）

```
D23（SD-08；DEF-200-275 第六輪）：`relay_problems()` 此前只檢查 `session_id`
這個鍵**存在**，不檢查**非空**——一個值為空字串的狀態塊會通過體檢，而
`_sentinel_tick` 拿它餵 `quota_gate.read_halt_marker(sid)`，該函式對假值 sid
直接靜默回 `None`（退化成 idle-based patrol，不會走到 halt 判定那一支）。
```

### class PrepareLatchIsSessionScopedTest（原 docstring）

```
D22（DEF-200-275 第六輪，SD-04）：`quota_prepare_actions()` 的閂鎖鍵此前不含 sid
（`f"prepare@{kind}@{reset[:16]}"`），與 halt 分支修復前同一種缺陷——`quota_latch_path()`
是 machine-wide 單一檔案，同一 reset 視窗內第二個進 prepare 帶（85~95%）的 session
會被第一個 session 的閂鎖誤擋，拿不到自己的 `write_resume_plan()` 任務書骨架
（不是訊息去重問題，是實質少一份任務書）。比照 `HaltLatchIsSessionScopedTest` 同型重現。
```

### test_two_sessions_in_the_same_prepare_window_both_get_their_own_plan（原 docstring）

```
紅端＝修前第二個 sid 撞進「已閂鎖」分支：`plan_writer` 只被叫一次——第二個
session 的任務書骨架永遠不會被寫出來（DEF-200-278 第二輪 §8 item 1）。
```

---

## tools/tests/test_context_budget_guard.py

### class AtomicLatchStorageTest（原 docstring）

```
D22（DEF-200-275 第六輪，SD-05）：`announced_latches`／`remember_latch` 此前是單一
JSON 檔的「整讀→union→整寫」——兩個行程幾乎同時各自 union 後寫回，後寫的會覆蓋先寫的、
遺失先寫入的那個 key（方向安全：多喊一次，不是漏喊；但不精確）。改成每個 key 一個
`O_CREAT|O_EXCL` 建出來的標記檔後，新增一個 key **結構上不可能**碰到既有 key 的儲存
（各自獨立的檔案）——本組用「後寫入的 key 不改動先寫入那個 key 的檔案」直接證明這一點
（這正是舊版「整寫」會違反、新版天生滿足的性質，比重現時序競態更穩定可重跑）。
```

### test_writing_a_second_key_never_touches_the_first_keys_file（原 docstring）

```
紅端＝舊版「整讀→union→整寫」每次 `remember_latch` 都重寫**同一份**檔案，
於是第一個 key 的儲存（整份 state 檔）必然被第二次呼叫改動；新版兩個 key 各自
獨立檔案，寫第二個絕不會碰到第一個的位元組（mtime／內容皆不變）。
```

### QuotaPrepareBandActuallyPreparesTest 迴圈內新增註解（原文）

```
# D22（SD-05）：閂鎖真正的落點已改成 `guard._latch_marker_dir()` 算出來的
# 目錄（每個 key 一個原子標記檔），不再是 `latch.json` 這個檔本身——只清
# 舊檔名會讓上一輪 subTest 的閂鎖繼續生效，第二個事件被誤判成「已喊過」。
```

---

## tools/tests/test_claim_provenance_r86.py

### class TestTheBlockClaimEvidenceWindowIsRecentTurnsOnly（原 docstring）

```
D24（DEF-200-275 第六輪；SD-06 收斂版）：第五個判準的佐證窗口從『全場不分時間』
收斂為『倒數第二則 role=user 訊息之後』（本回合＋前一回合）。立案見 SD-06：舊窗口讓
本場任何時候出現過一次 `kind=`/`band=`/`cap=` 通知，就對**之後所有**『被擋』宣稱整場
靜音——即使那次通知早已跟這次宣稱無關。這裡驗證『兩回合前』的通知不再能替『這一回合』
的赤裸宣稱背書，同時保留『上一回合／這一回合才提一句』的原始合法情境（不能矯枉過正）。
```

### _user_line 靜態方法（原 docstring）

```
一則**真人打字**的 role=user 訊息（非 tool_result 中繼）——D24 拿它當回合邊界。
```

### _notice_line 靜態方法（原 docstring）

```
`context_budget_guard.py` 額度守衛的 `hook_additional_context` 通知形狀
（SD-06 假紅普查逼出來的真實佐證形態之一，見本檔上方 `BLOCK_EVIDENCE_RE` 旁註）。
```

### test_a_notice_inside_the_previous_round_still_silences_it（原 docstring）

```
對照組：通知落在邊界（倒數第二則）之後時，仍要維持原判準的設計動機——
『先被擋、下一回合才提一句』仍要放行，不能因為收斂窗口而矯枉過正。
```

### test_fewer_than_two_user_turns_falls_back_to_whole_transcript（原 docstring）

```
少於兩則真人訊息（含 0／1 則）時沒有『倒數第二則』可切，退回全場——覆蓋既有
4 筆假紅普查案例的形狀（那些合成語料本來就不含任何 role=user 訊息）。
```

---

## tools/tests/test_check_hooks_liveness.py

### test_root_sdd_hook_router_pretooluse_matcher_includes_agent_and_workflow（原 docstring）

```
D20（DEF-200-280／F-ARCH-02）正面斷言：Agent／Workflow 呼叫必須觸發 SDD FSM guardrail。

`_REGISTRATION_BASELINE` 只是下限（floor-only 棘輪）——widening 測試只保證加寬
matcher『不會轉紅』，不保證『真的加了』：`registration_shrink_problems()` 對
`("PreToolUse", ".claude/hooks/sdd_hook_router.py")` 這一列釘的下限本身就沒有
Agent／Workflow（見 `context_budget_guard.py` 那列同樣只釘了加寬前的子集，R80 之後
matcher 本體已加寬但基準表從未回填——這是既有、刻意的慣例，不是本測試要修的東西）。
F-ARCH-02 實測指出：在 monorepo 根開 `claude` 是本任務背景描述的實際工作流，此時只有
根層 `.claude/settings.json` 生效；若那一條轉發 sdd_hook_router→context_ledger_pre 的
PreToolUse matcher 缺 Agent|Workflow，子代理（Agent）／批次編排（Workflow）呼叫會完全
繞過 SDD FSM guardrail（ESCALATION／AUTO_COMPACT_PENDING 等狀態形同虛設）——這是『該擋
沒擋』的鏡像問題（DEF-200-279／SD-01 是『不該擋卻擋』，本項相反）。本測試直接讀取現實
settings.json 內容做正面斷言，不透過棘輪下限迂迴，避免『floor 沒動、matcher 也沒動』
兩者同時發生時仍被誤判為合格。
```

---

## tools/tests/test_root_guard_known_model_r145.py（新檔，全檔本輪）

### 模組 docstring（原文）

```
D21（DEF-200-275 第六輪，SD-09）：根層 `context_budget_guard.py` 補查表收斂階。

WHY（引用 D21，見 scratchpad/dev-c/../r6_decisions.md）
---------------------------------------------------------
第五輪複審 SD-09／QA P2／Architect P2 三方一致指出：SDD 子專案的 `context_window.py`
已有 `_converge_pinned_window()`（D14）把「指定值」與「觀測到的 model 查表值」收斂，
但**根層**的姊妹守衛 `context_budget_guard.py` 完全沒有這一階——遇到指定值與實跑
模型的真實視窗不符時，算出來的 ratio 依然可能與 `/context` 差好幾倍。這支測試釘住
D21 的修法：資料只有一個家（`$V/tools/fsm_runtime/data/known_model_windows.json`，
經 `tools/lib/sdd_latest.py` 解析 LATEST 路徑讀取），根層自己不存第二份查表
（否決「根層另存一份」——DEF-101-778 判例：兩個家只會改一個）；收斂語意與 SDD
`_converge_pinned_window` 逐項相同（只在查表值嚴格小於指定值時收斂）；`--check`
的 window 行必須印得出「有沒有真的查過表」的證據，不論收不收斂（根層此前連查過表
這件事本身都看不見，是 SD-09 殘餘的核心）。

測試鏡射 SDD `test_context_window.py::ConvergePinnedToKnownModelTests` 的三階案例
（haiku 收斂／fable 不收斂但保留釘值／`SDD_MAX_CONTEXT` 無此概念，改測「無 known_models
表」的 fail-open 案）＋「表缺檔 fail-open」案（`known_model_windows_path()` 解析不到）。
```

### test_no_aisdlc_sdd_directory_is_fail_open 內註解（原文）

```
# SA-F1（第六輪複審）訂正：此前六種查表 fail-open 失效路徑全靜默、零 stderr——
# 「根層此前連查過表這件事本身都看不見」的 SD-09 殘餘。fail-open 方向不變，但
# 不可再靜默。
```

### test_aisdlc_sdd_present_but_no_version_directories_is_fail_open 內註解（原文）

```
# SA-F1：一個只有空殼、沒有 `scripts/sdd_version.py` 的 AISDLC_SDD 目錄會讓
# subprocess 連腳本都找不到（那是另一種「LATEST 解析失敗」，不是本測試要的
# 「有子專案無版本目錄」）——要真的重現後者，必須放進真的 sdd_version.py，
# 讓它實際跑起來、自己正確回報「找不到任何版本目錄」。
```

以及：

```
# SA-F1：同上——「有子專案無版本目錄」與「無子專案」是不同的失效種類，各自
# 印出的 stderr 訊息必須能分辨是哪一種（不能共用同一句籠統訊息）。
```

### test_corrupt_json_is_fail_open_not_a_crash 內註解（原文）

```
# SA-F1：JSON 損毀與「JSON 形狀不對」是 load_known_model_windows() 自己的兩種
# fail-open（`known_model_windows_path()` 那四種以外的另外兩種）。
```

### class WindowEvidenceOnlyQueriesTableWhenPinnedTests（原 docstring）

```
D21 效能取捨：沒有任何 pin 時 `window_evidence()` 不該去解析 LATEST（`_converge_
pinned_window` 用不到它）——省一次 `sdd_latest` 的 subprocess 解析。用一個一定會失敗的
`root` 探針間接證明：有 pin 時才會嘗試查表（回傳的 known_models 不含表徵值），沒 pin
時完全不觸碰查表路徑（`known_models=={}` 且不影響其餘證據欄位）。
```

### test_no_pin_at_all_yields_empty_known_models 內註解（原文）

```
# 隔離：本場開發環境本身可能已設 AUTOSDD_CONTEXT_WINDOW（供人互動時用）——
# 測試若不清乾淨會讀到真實行程環境，「沒有 pin」這個前提就不成立
# （DEF-200-281 同型教訓：夾具沒隔離會讓斷言測到別的東西）。
```

### test_keeps_pinned_when_table_value_is_larger_for_fable（原 docstring）

```
D21 例句：`967,000〔指定值…；查表 claude-fable-5-1=1,000,000 ≥ 指定值，不收斂〕`
——window 不變，但來源說明必須留下「有查過表」的證據（不是靜默沿用舊來源）。
```

### test_no_known_models_table_is_fail_open_and_silent（原 docstring）

```
表缺檔／解析失敗 fail-open：不收斂，且來源說明不留下「查過表」的字樣
（沒有表可查，不能假裝查過）。
```

---

## tools/tests/test_sentinel_tick_e2e_r145.py（新檔，全檔本輪）

### 模組 docstring（原文）

```
D23（DEF-200-275 第六輪，SD-08／OTHER PARTIAL _sentinel_tick 端到端）：構造合法 relay
狀態塊＋halt marker fixture，monkeypatch `_register_and_record` 為零副作用記錄函式，
直接呼叫 `_sentinel_tick(args)`，斷言 halt 標記真的被消費、decision 正確（`arm_reset`／
`probe`）。

WHY
---
既有測試（`test_context_budget_guard.py` 裡一大批 `_sentinel_tick` 呼叫）覆蓋面其實不小，
但都是「純函式邊界」層級（`sentinel_decide()`／`halt_verdict()` 各自獨立驗證）；沒有一支
是「構造一份磁碟上的 halt 標記 → 直接呼叫 `_sentinel_tick(args)` → 斷言它真的讀到、
真的據以決策」的端到端串接（DEF200278 證據檔第二輪 §8 自陳此為未做事項）。本檔補這一段
缺口：不 mock `quota_gate.read_halt_marker`／`halt_verdict`，只 mock 排程／告警的**副作用**
（`_register_and_record`／`_resume_tick`），讓 halt 標記到 decision 這一段是真的跑過的
程式碼，而不是分別驗證兩段純函式後靠推論黏起來。

隔離：`AUTOSDD_TRACE_DIR`（halt 標記落點）＋`tempfile.gettempdir`（`endurance_log_path`
落點）皆指向本測試專屬暫存目錄；`SDD_ENABLE_RULE_FIRE_TELEMETRY`／
`SDD_ENABLE_RULE_CATCH_TELEMETRY` 未涉及（`_sentinel_tick` 不碰 SDD FSM 治理面）。
```

### _transcript 方法（原 docstring）

```
`mtime`＝None 時用「現在」（session 還活著）；給定值時模擬「最後一次活動
落在那個時刻」——`halt_verdict()` 用它判斷 session 是否已在標記之後自行續跑過
（見 `test_expired_halt_marker_drives_probe_and_delegates_to_resume_tick` 的 WHY）。
```

### _write_plan 方法（原 docstring）

```
合法 relay 狀態塊（`relay_problems()` 必須回空清單，否則走自癒分支，
測的就不是「真的消費了 halt 標記」這件事）。
```

### test_unexpired_halt_marker_drives_arm_reset_and_reaches_register（原 docstring）

```
halt 標記的 reset_at 尚未到 ⇒ decision=arm_reset ⇒ `_sentinel_tick` 必須真的
走到 `_register_and_record()`（不是提早在別的分支短路掉）。
```

### test_expired_halt_marker_drives_probe_and_delegates_to_resume_tick（原 docstring）

```
halt 標記的 reset_at 已過 ⇒ decision=probe ⇒ `_sentinel_tick` 必須交棒給
`_resume_tick()`（既有的探測/重排/終態機器），不是自己另開一條路。
```

### test_expired_halt_marker_drives_probe_and_delegates_to_resume_tick 內註解（原文）

```
# 逐字稿最後活動落在 marker_at **之前**（模擬「halt 之後 session 沒有續跑過」，
# 見 `halt_verdict()` 的「活動晚於標記＝標記過期」防呆）——否則會被判成
# 已自行續跑而落回 idle-based patrol，不是本測試要驗的 probe 分支。
```

### 實測（主控親跑；他包數字皆已標 [他包回報]）

```
# SDD 全套（複審修復波後）
$ cd AISDLC_SDD/AISDLC_SDD_v0.30 && SDD_ENABLE_RULE_FIRE_TELEMETRY=0 SDD_ENABLE_RULE_CATCH_TELEMETRY=0 python -m pytest tools/fsm_runtime/tests/ -m "not chaos" -q -p no:cacheprovider
1907 passed, 8 skipped, 34 deselected, 14 subtests passed in 44.98s   rc=0
$ ... -m chaos ...
34 passed, 1915 deselected in 14.80s   rc=0
# 治理 yaml 零污染：git status --short -- AISDLC_SDD/AISDLC_SDD_v0.30/governance/ → （空）
# 直呼 transition("ESCALATION 程式碼命中：0（僅 1 筆註解）
# chaos 舊債在乾淨 HEAD fda2903 副本（git worktree add --detach）：1 failed in 0.15s ⇒ 確為既有
# ruff（根層 12 檔＋skip_tag_policy＋governance_docs＋guard_bucket_policy）：All checks passed!
# LOC：python AutoClaude/tools/check_loc_budget.py --json → total_violation=False special=[] root_tools=[]
# 帳本鎖：test_check_defect_log_crossref test_defect_id_reference_integrity → Ran 278 tests OK
#   DEF-200-283 列 677 bytes（≤700）；超標列 36/36、超標總量 20027/20027 恰回基線
# 護欄層行數棘輪：python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines
#   淨額 97488→98221 (+0 漂移)；python -m unittest test_adr_xplat001_c1c2_lock → Ran 192 tests OK
# 根層全套（首跑，四包收工後）：前置掃描早退 ⇒ 重釘 _TREE_FILE_FLOORS 56→58／62→63（→64）
# 根層全套（第二跑）：Ran 4157 tests in 778.409s FAILED (failures=6)——6 紅皆收尾項：3 支護欄棘輪、
#   round-label R145 超前帳本、DEF-200-283 未立列、E501 存量債 139→141（Dev-C 用 noqa 想略過的兩行）
#   ⇒ 全數由收尾窗口處理（見〈修法逐檔〉收尾窗口段與 R145 Scan_Findings §3）
```

P3 主控開場實測：`used 99,017／window 967,000／10.2%`＝逐字稿最後一筆 usage 手算；QA 修後複審 `343,214／967,000／35.5%`、SA 迷你複審 `425,134／967,000／44.0%`（window 行帶「查表 claude-fable-5-1=1,000,000 ≥ 指定值，不收斂」證據）——三路徑三個時間點皆逐位元組一致。[他包回報]

### 把握程度（誠實劃界）

- **高把握**：D17（含 ARCH-R6-01 補齊 4 落點＋陳舊溯源防呆）、D18、D19、D20 兩層、D22、D23、D24、D25（含 SA-F2／F3 訂正）皆先紅後綠＋修後複審／迷你複審獨立重現核實；FSM 狀態集／邊／TLA 零改動（`transition_rules.py`／`formal/` diff 為空，TLA／MD sync 綠）。
- **中高把握**：D21 根層查表收斂——語意逐項對齊 SDD `_converge_pinned_window`、六種 fail-open 各一行 stderr（SA 迷你複審逐一貼出）；但查表本身仍是 2026-06-24 種子值（D26），收斂到的「真實值」尚未被 Models API 驗證。
- **P1 的殘餘邊界**：ESCALATION **刻意仍擋**新視窗（R-9.5）；本輪解決的是「擋得有沒有溯源、擋得對不對人、非 owner 會不會被牽連、cap 計數會不會張冠李戴」。掌舵者若日後開新視窗仍被擋，訊息會直接印出「由哪個 session 於何時因何規則寫入、本 session 是否觸發者、一行恢復指令」——照做即可。
- **P2 的結構邊界**：hook 已把真實數字寫進 deny reason／SessionStart／Stop hook 出聲；「模型是否真的據以行動」結構上無法被 hook 保證（Architect 誠實劃界）。
- **P3**：subagent 結構上不能呼叫互動式 `/context`；三路徑數字一致，剩最後一步由掌舵者親自對照 `/context` 一次。
- **護欄層記帳**：本輪 +748 分軌申報——回歸鎖軌 392（結案回歸鎖＋本檔記帳，走 `_REGRESSION_LANE_APPROVED_OVERAGE` 唯一一格）、功能軌 356（兩支新判準能力鎖檔，熄滅款(11)[只升不降] 走 `_REPIN_APPROVED_ROUND_OVERAGE` 第三格、MAX_ENTRIES 2→3 可見上修）；prose 分桶 4182→4512。四方記帳複審 SA／SD／QA APPROVE，Architect 以分類寬度 REJECT 後改為現行分法再複核（R145 Scan_Findings §3.1／§3.2）。往後任何一輪的超額照原判準阻擋；下一次淨減法輪應下修 MAX_ENTRIES 並移除失效列。
- **Windows 未真機驗證**（同前幾輪）。

#### 收尾最終親跑（四方記帳複審全 APPROVE、所有編修定案後）

```
$ python tools/run_root_unittests.py
Ran 4157 tests in 790.649s
OK (skipped=46)                                   rc=0
$ cd AISDLC_SDD/AISDLC_SDD_v0.30 && SDD_ENABLE_RULE_FIRE_TELEMETRY=0 SDD_ENABLE_RULE_CATCH_TELEMETRY=0 python -m pytest tools/fsm_runtime/tests/ -m "not chaos" -q -p no:cacheprovider
1907 passed, 8 skipped, 34 deselected, 14 subtests passed in 46.97s   rc=0
$ ... -m chaos ...
34 passed, 1915 deselected in 15.33s              rc=0
$ python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines | head -1
# 淨額 98236→98236 (+0)
$ git status --short -- AISDLC_SDD/AISDLC_SDD_v0.30/governance/   → （空）
```
護欄層淨額定案 97488→98236（+748＝回歸鎖軌 392＋功能軌 356），四方記帳複審 SA／SD／QA APPROVE、Architect REJECT→修正 392／356 分法→APPROVE（R145 Scan_Findings §3.1／§3.2）。ONBOARDING §7 表② 指紋以樹外乾淨 venv（`onboarding_clean_venv`，Python 3.11.15，`psycopg2` absent）回填。
