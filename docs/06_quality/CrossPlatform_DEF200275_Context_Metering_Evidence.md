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

全文移至 CrossPlatform_DEF200275_Context_Metering_Lore.md 同名節。

## 〈行為契約〉〈PreToolUse 阻斷模式〉〈相依規則〉〈R82／Q2-02 職責邊界〉原文（D21 前）

全文移至 CrossPlatform_DEF200275_Context_Metering_Lore.md 同名節。

## `_NEXT_STEP` 上方註解、`spawn_sentinel`／`arm_sentinel`／`spawn_sentinel_gc` 原文（D21 前）

全文移至 CrossPlatform_DEF200275_Context_Metering_Lore.md 同名節。

## `main()` 內 R83 相關大段註解原文（D22 前）

全文移至 CrossPlatform_DEF200275_Context_Metering_Lore.md 同名節。

## `known_model_windows_path()` docstring 原文（搬出前，逐字保留）

全文移至 CrossPlatform_DEF200275_Context_Metering_Lore.md 同名節。

## tools/tests/test_wake_chain_halt_r278.py

全文移至 CrossPlatform_DEF200275_Context_Metering_Lore.md 同名節。

## tools/tests/test_context_budget_guard.py

全文移至 CrossPlatform_DEF200275_Context_Metering_Lore.md 同名節。

## tools/tests/test_claim_provenance_r86.py

全文移至 CrossPlatform_DEF200275_Context_Metering_Lore.md 同名節。

## tools/tests/test_check_hooks_liveness.py

全文移至 CrossPlatform_DEF200275_Context_Metering_Lore.md 同名節。

## tools/tests/test_root_guard_known_model_r145.py（新檔，全檔本輪）

全文移至 CrossPlatform_DEF200275_Context_Metering_Lore.md 同名節。

## tools/tests/test_sentinel_tick_e2e_r145.py（新檔，全檔本輪）

全文移至 CrossPlatform_DEF200275_Context_Metering_Lore.md 同名節。

## 第七輪（2026-09-12；四方獨立複審 3 APPROVE／1 REJECT ⇒ D27～D30）

### 觸發

commit e90ee11（第六輪「修後複審 APPROVE」）push 後，主控再派 Architect／SA／SD／QA 四方（皆 Sonnet 5、唯讀、各自隔離重現、互不溝通）對掌舵者原始三問重新獨立複審：①新視窗一開就被擋；②不用真實 /context 或 API 查數據；③印出的數字與 /context 明顯不符。四方之後另加一層**三鏡對抗驗證**（repro／code／intent 三個獨立 Sonnet 5 agent，對每一筆待裁決 finding 各自判定「是否已被駁回」），原始報告全文在
`~/.claude/projects/-Users-wuweihong-Antigravity-AISDCL-Agent/17e2da67-e140-43a8-9817-d1b6f61f3f7a/subagents/workflows/wf_9afa3db6-c24/journal.jsonl`（`type=started` 行有 `label`，`type=result` 行有 `result`），以下逐字引用皆取自該檔。

### 四方判決與收斂發現（Architect／SA／SD／QA 皆 Sonnet 5、唯讀、各自隔離重現，不互相溝通）

| | Architect | SA | SD | QA |
|---|---|---|---|---|
| P1 新視窗被擋 | partial | **fixed** | **fixed** | **fixed** |
| P2 不用真實數據 | partial | **fixed** | partial | **fixed** |
| P3 數字與 /context 不符 | partial | **fixed** | partial | **fixed** |
| overall | **REJECT** | APPROVE | APPROVE | APPROVE |

**ARCH-A4-01（Architect，P1，對應問題 3；`.claude/hooks/context_budget_guard.py:547`）**——四方本輪最重的發現，逐字：

```
根層與 SDD 層 context window 分母鏈不是同一套邏輯：根層缺『無釘值時查表』階，兩層數字在新視窗低用量時可相差 5 倍

resolve_window()／window_evidence() 只在至少一階已有釘值（AUTOSDD_CONTEXT_WINDOW／CC env／settings）時才會查
known_model_windows.json（僅用於『收斂』既有釘值，D21 註解明文『只在至少一階有指定值時才查表』）；SDD 層
context_window.py::resolve_window() 有獨立、無條件的『⑥ 以 model id 查表』階，沒有任何釘值也會命中。兩層因此
不是同一套演算法，只是共用同一份 JSON 資料檔——資料 SSOT 有了，演算法 SSOT 沒有。

repro：peak_used=50000（模擬新視窗低用量）、不設 AUTOSDD_CONTEXT_WINDOW／CC settings、model_hint=None、
observed_model='claude-fable-5-1'（表值 1,000,000），分別呼叫根層與 SDD 層 resolve_window()。
actual：根層回報 window=200,000（ratio=25.00%，來源『推斷值・保守下界』）；SDD 層回報 window=1,000,000
（ratio=5.00%，來源『查表值』）。現有 test_context_window_parity.py 對 SDD 側硬寫死 known_models={}，
結構上永遠測不到這條分歧（該測試目前 3/3 綠燈）。
```

三鏡對此 finding 的裁決：**repro 未駁回**（`refuted=false, confidence=high`，親手重跑得到與 finding 逐字相同的數字：200,000/25.00% vs 1,000,000/5.00%，並額外驗證「即使手動把查表結果硬塞進根層 `resolve_window()`，無釘值時仍完全不用它」，證明是判定邏輯本身缺這一階，不只是資料收集面被擋）；**code 未駁回**（`refuted=false, confidence=high`，逐行核對 HEAD e90ee11 兩層程式碼與 finding 描述精確無誤）；**intent 判「已裁決」**（`refuted=true, confidence=high`）：

```
ARCH-A4-01 描述的行為…皆為第六輪四方複審已裁決、附理由的刻意設計，非未書面化的缺陷。
裁決 D21（證據檔 L1034）：「根層 context_budget_guard.py 補查表收斂階，資料只有一個家…否決根層另存一份查表」。
效能取捨的明文理由（證據檔 L1631）：「D21 效能取捨：沒有任何 pin 時 window_evidence() 不該去解析 LATEST
（_converge_pinned_window 用不到它）——省一次 sdd_latest 的 subprocess 解析」。
因此 ARCH-A4-01 描述的「行為不一致」屬實（未推翻其技術觀察），但其定性為「未經裁決的架構缺陷」不成立——
這條路徑的存在、理由與測試邊界，第六輪 D21 裁決與程式模組 docstring 皆已書面化並附理由。
```

三鏡結論：**confirmed 且為書面裁決**（技術現象真實存在、且是 D21 白紙黑字的刻意取捨，不是遺漏）。**總架構師本輪推翻 D21**：理由——①本機 `AUTOSDD_CONTEXT_WINDOW=967000` 這個釘值只住 `~/.claude/settings.json`，不隨 clone 走，換一台乾淨機器就會退化成「無釘值」狀態；②無釘值機器在低用量（peak<200,000）時會用猜的分母（200,000）擋展開型工具，正是掌舵者問題 1（新視窗被擋）與問題 3（數字對不上）共同的形狀根源，不是各自獨立的兩個問題；③正確性不得用效能捷徑換——D21 當時的取捨是「省一次 subprocess」，但省下的代價是「無釘值時分母系統性失真 5 倍」，兩者不對等。

**SD-F1（SD，P2，對應問題 3；`.claude/hooks/context_budget_guard.py:338`）**：

```
known_model_windows 收斂只修正『分母高估』方向，未涵蓋『分母低估』方向

_converge_pinned_window() 只在 table_value < pinned 時才把 window 往下修正；當已指定的 window
（來自 AUTOSDD_CONTEXT_WINDOW 環境變數或 CC settings）小於查表真實值時，函式回 None，resolve_window()
沿用原本（偏小）的指定值，不做任何修正。這個方向性選擇 docstring 有交代理由（『猜小只是早喊，猜大會讓阻斷
遲到』），是從『會不會太晚擋下工具』這個安全角度做的合理取捨，但沒有解決『算出來的百分比是否貼近 /context
真實顯示值』這個不同判準——如果分母被低估，算出來的用量百分比會系統性地高於 /context 真實值。

actual：回傳 (200000, '指定值（環境變數 AUTOSDD_CONTEXT_WINDOW；查表 claude-fable-5-1=1,000,000 ≥
指定值，不收斂）')——雖然有老實在 source 字串裡標註查到的表值供人工核對，但百分比本身仍用偏小的分母算出，
不會自動修正。
```

三鏡：repro 駁回（判為刻意設計、非可歸咎的未書面化缺陷）、code 未駁回（技術現象屬實）、intent 判「D21 已裁決」（單向收斂是設計取捨，非遺漏）。裁決：**不改碼**，寫入誠實劃界（見下）。

**SA-R7-01（SA，P2，對應問題 0；`AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/rule_loader.py:158`）**：

```
複審視窗內治理規則 YAML 被非隔離 FSM 驅動寫回（fire_count 遙測），唯讀複審協定無機械守衛

本輪複審期間（git status 顯示，非 e90ee11 commit 內容本身）發現 9 支 governance/rules/*.yaml
（R-9.13／16／18／2／3／6／7／8／9，皆 trigger_states=["*"]）被同一秒（mtime 2026-09-12 11:27:23）
改動，diff 為真實遙測寫回（fire_count: 0→1），非純格式重排。根因鎖定：rule_loader.py::_write_rule()
（由 fsm_runtime.py:287 在 _rule_fire_telemetry_enabled() 為真時、經 record_state_fires() 呼叫）在未帶
SDD_ENABLE_RULE_FIRE_TELEMETRY=0 前綴、對真實 governance/rules/ 目錄跑一次真實 FSM transition 時會寫回本體。
已核實不是本 SA 造成：本 SA 三次 SDD pytest 呼叫皆已加上正確前綴，相關測試皆用隔離 tmp_path；11:27:23 在
本 SA 所有指令視窗之外，高度疑似同機另一位複審方跑了『pytest 外』手動 FSM 重現腳本卻漏帶前綴（與既有記憶
缺陷『SDD 探針會回寫治理 yaml』同型）。
```

三鏡（repro／code／intent）皆未駁回（`refuted=false, confidence=high` ×3）。根因補充（主控自查，非三鏡發現）：主控派審任務書把 opt-out 旗標名寫成縮寫展開錯名（`SDD_ENABLE_RULE_FIRE=0`／`SDD_ENABLE_CATCH_TELEMETRY=0`），正確全名為 `SDD_ENABLE_RULE_FIRE_TELEMETRY`／`SDD_ENABLE_RULE_CATCH_TELEMETRY`；主控已於審查結束後以 `git show HEAD:<path> > <path>` 逐支還原 9 支（`git status` 核為 0 列）。

**SA-R7-02（SA，P2，對應問題 0；`docs/06_quality/CrossPlatform_DEF200275_Context_Metering_Evidence.md:1334`）**：

```
commit e90ee11「修後複審 APPROVE」壓縮了真實過程——第一次修後複審其實 3 REJECT／1 APPROVE，之後只有
『護欄層記帳』被重新四方複審，D17/SA-F2/SA-F1/QA-R6-01 的實質修復僅由主控親跑自證，未經第二次四方獨立重現

證據檔記載：修後複審（第一次）結果為 Architect REJECT／SA REJECT／SD APPROVE／QA REJECT，抓到
ARCH-R6-01／SA-F2／QA-R6-01 三筆阻斷發現；Dev-A2／Dev-D2 修復後，證據檔只再記錄了『護欄層記帳複審』
（針對 LOC 棘輪分軌申報），並未見對 D17（含 ARCH-R6-01 訂正）／SA-F1／SA-F2 本身的第二輪四方獨立重現
紀錄，這部分只有『主控親跑』自證。commit message 用『修後複審 APPROVE』一詞，容易讓人誤讀成四方對全部
修復內容都重新獨立確認過。本 SA 本輪已針對 ARCH-R6-01／D18／D19／D20 的程式碼與測試做了獨立重現，結果與
Dev-A2/Dev-D2 的自陳一致，未發現實質錯誤，因此本項定性為文件精確度問題而非阻斷級發現。
```

三鏡皆未駁回。裁決：文件精確度訂正（見 D29(b)），不影響本輪 fixed 判定。

**ARCH-A2-01（Architect，P3，對應問題 1；`AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/fsm_runtime.py:562`）**（未走三鏡，直接登記）：`_BLOCKING_STATES`（ESCALATION／ESCALATION_FINAL／TERMINATED／TOKEN_BUDGET_CRITICAL）對所有工具無例外阻擋（含 Read／Bash），D17 恢復指令依賴 Bash——但 Bash 正是被擋工具之一，須人類開真終端執行。Architect 讀碼確認為 R-9.5「禁止自動恢復」刻意設計、D17 已提供人工可讀溯源與恢復指令，判「非缺陷，記錄供掌舵者確認是否仍可接受」。留掌舵者裁決是否對非觸發者 session 放行 Read（若要開放，Architect 建議仿照 `AUTO_COMPACT_PENDING` 白名單模式另開窄例外，但明言「此舉超出本輪審查範圍」）。

**SD-F2（SD，P3，對應問題 0；`.claude/hooks/context_budget_guard.py:426`）**（未走三鏡，直接登記）：`remember_latch()` 用 `os.open(..., O_CREAT|O_EXCL)` 先建立檔案、再 `os.write()` 寫入內容，兩步非原子；行程若在兩步之間中斷會留下空內容的 marker 檔，之後同一 key 永遠無法被成功記錄，導致該門檻反覆出聲。SD 未能在測試環境重現（中斷視窗極短），僅讀碼推導；失效方向本身安全（「多喊一次」符合本檔「寧可多喊，不要靜默失聲」既定紀律），SD 建議「不需要在本輪處理，僅供記錄」。

四方 `git status --short` 除 SA-R7-01 指出的 9 支治理 yaml（非四方自己造成、已還原）外，皆與開工時逐字相同。

四方各自跑的測試（[他包回報]，除主控開場實測外）：SA 親跑 `python tools/run_root_unittests.py` → `Ran 4157 tests in 801.467s; OK (skipped=46)` rc=0；SA／QA 皆 `1907 passed, 8 skipped, 34 deselected, 14 subtests passed`、chaos `34 passed`；SD 針對性跑與 D17～D25 直接相關測試檔合計 933 支 rc=0（自陳未跑全套 4157，誠實劃界見下）；QA 與 SA 同時刻三條算法（手算逐字稿／根層 `scan_transcript`／SDD `measure()`）對主控逐字稿皆 `used=119,598／peak=119,598／window=967,000／ratio≈12.4%`，逐位元組一致。

### 裁決 D27～D30（總架構師定案；被否決意見括註）

- **D27（ARCH-A4-01）**：根層 `context_budget_guard.py` 補⑥查表收斂階（`known_model_window()` 與 SDD `context_window.py` 逐字同構）、`window_evidence()` 改為無條件查表（不再有「只在有釘值時才查表」的提前跳過）。效能疑慮（每次工具呼叫都多開一個 `sdd_latest` subprocess）以 `tools/lib/sdd_latest.py` 新增 `resolve_latest_name_fast()`／`resolve_latest_root_fast()`（`importlib` 就地載入 `sdd_version.py`，不起第二個 python 行程）＋ per-session 快取檔（`_known_table_cache_path()`，住 `_latch_marker_dir()`）解決。（否決 SD-F1 提議的「雙向收斂」——維持 D21 原有的單向安全取捨，只改「有沒有查表」，不改「查到了怎麼收斂」。）
- **D28（SA-R7-01）**：**不翻 v0.24 既有預設**，走加法式守衛：settings env `SDD_TELEMETRY_WRITEBACK_REQUIRES_HOOK=1`（根層與 v0.30 兩份 `.claude/settings.json` 皆加）＋ hook 入口標記 `SDD_FSM_HOOK_ENTRY=1`（`context_ledger_pre.py`／`context_ledger_post.py`／`session_start.py` 的 `main()` 第一行設定）＋ `fsm_runtime.py` 新增 `_telemetry_writeback_allowed()` 共用判定（顯式 0/1 優先 → `REQUIRES` 且非 hook 入口 → `False` 並 stderr 出聲一次 → 否則 `True`）；`conftest.py` 隔離兩個新 env（避免既有測試套件被牽連轉紅）。
- **D29（誠實劃界訂正，三點）**：(a) SD-F1 的單向收斂（只修分母高估方向）寫進〈把握程度〉誠實劃界；(b) 第六輪「修後複審 APPROVE」的範圍訂正（SA-R7-02）：commit 訊息應區分「護欄層記帳複審 APPROVE」與「阻斷發現本身是否經第二次四方複審」；(c) 問題 2 的機制邊界重申：hook 已保證分子數字是真的（逐字稿 API usage）、Stop hook 對無佐證的「被擋」宣稱出聲，但**結構上無法機械強制模型去對照 /context 或打 API**（Architect／SA 兩方各自獨立劃界，逐字一致）；D26 Models API 種子值仍未做（需 `ANTHROPIC_API_KEY`，另案）。
- **D30（登記不修）**：ARCH-A2-01（ESCALATION 全擋含 Read/Bash）留掌舵者裁決；SD-F2（latch marker 非原子）P3 登記；新立哨兵缺陷 DEF-200-286（見〈喚醒鏈哨兵新缺陷〉節）。

派工：Dev-A7（D27：根層 context_budget_guard.py／sdd_latest.py／相關測試）／Dev-B7（D28：SDD telemetry writeback 守衛，三支 hook＋fsm_runtime.py＋conftest＋新測試）／Dev-Trim7（護欄層行數棘輪抵銷：Dev-A7／B7 的合法新增使棘輪轉紅，搬運既有測試檔 docstring 敘事）三包 Sonnet 5 並行，鎖持有面互斥；棘輪逐檔重釘、缺陷帳本、證據檔收尾由本節〈收尾窗口〉（Dev-C7，收尾單人窗口）統一處理。

### 修法逐檔（三包並行，皆 Sonnet 5；細節與紅→綠逐字見各包回報，標 [他包回報]）

**Dev-A7（D27；根層查表收斂＋效能）** [他包回報]
- 改 `.claude/hooks/context_budget_guard.py`（最終 1089 行＝`SPECIAL_FILES` 上限，餘裕 0）、`tools/lib/sdd_latest.py`（新增 `resolve_latest_name_fast`／`resolve_latest_root_fast`）、`tools/tests/test_root_guard_known_model_r145.py`（`test_no_pin_at_all_yields_empty_known_models` 翻案為 `WindowEvidenceAlwaysQueriesTheRealTableTests::test_no_pin_at_all_still_queries_the_real_table`，語意由「無 pin 不查表」反轉為「無 pin 也一定查表」）、`tools/tests/test_context_window_parity.py`（新增 `KnownModelLookupStageParityTest`）、`tools/tests/test_context_budget_guard.py`（fixture 預設 model 改合成值 `claude-test-double-3`，修復 7 支因查表攔截而假紅的既有測試）、SDD `context_window.py` 只改 docstring（不動判定邏輯，parity 語意不變）、證據檔檔尾〈第七輪 史料搬遷（Dev-A7）〉保全原文。
- 紅→綠：`AssertionError: None != 1000000`（r145 翻案紅）；parity 注入紅 `'lookup[claude-fable-5-1] window: 200000 vs 1000000'`。
- 效能中位數（10 次跑）：OLD（D21，僅取無 pin 分支）76.40ms → 僅套 `resolve_latest_root_fast()`（無快取）111.58ms（+35.18ms，超過 30ms 門檻，`git ls-files` 本身即耗 ~24-32ms）→ 加 per-session 快取 77.92ms（+1.28ms，10 次裡只有第 1 次冷啟動吃到 ~35ms，第 2～10 次快取命中）。
- 端到端：無釘值兩側皆 `window=1,000,000／ratio=0.050000`、source 逐字相等（ARCH-A4-01 描述的分歧已消除）；有釘值 967000 兩側 window／ratio 相等，source 差一段根層稽核註記（D21／SD-09 既有行為，非本輪改動）。

**Dev-B7（D28；SDD telemetry writeback 守衛）** [他包回報]
- 改 `fsm_runtime.py`（新增 `_telemetry_writeback_allowed()`）、三支 hook（`context_ledger_pre.py`／`context_ledger_post.py`／`session_start.py` 的 `main()` 首行設 `SDD_FSM_HOOK_ENTRY=1`）、`conftest.py`（隔離兩個新 env）、新檔 `tools/fsm_runtime/tests/test_rule_telemetry_requires_hook_r7.py`（13 案）、兩份 `.claude/settings.json`（`SDD_TELEMETRY_WRITEBACK_REQUIRES_HOOK=1`）、`tools/tests/test_context_budget_guard.py` 新增 `SettingsChainTest` 一案。
- 紅→綠：`4 failed, 9 passed`（helper 回舊行為）→ `13 passed`。
- 端到端：`REQUIRES=1` 且無 `ENTRY` 標記 → 治理 yaml 摘要 digest `8b2692a9…`→`8b2692a9…`（`unchanged=True`）＋ stderr 出聲一次；`ENTRY=1`（真 hook 路徑）→ digest 變為 `7b3bbeb0…`（`unchanged=False`，遙測正常寫回）。
- `ci-gate.sh`：v0.30 `1920 passed`／`arch_fitness` `fail=0 warn=3`（既有）／`scripts` `351 passed` rc=0。

**Dev-Trim7（護欄層行數棘輪抵銷）** [他包回報]
- Dev-A7／B7 對 `test_context_window_parity.py`／`test_context_budget_guard.py`／`test_root_guard_known_model_r145.py` 的合法新增使護欄層行數棘輪（`_FROZEN_GUARD_LINES` 總量 98236）與分桶棘輪（`prose` 桶 4512）雙雙轉紅（98373／4528）。12 支既有 `tools/tests/` 測試檔模組頂端 docstring／歷史敘事搬到本證據檔〈第七輪 史料搬遷（Dev-Trim7）〉，判準與斷言本身一行未砍，淨減 177 行（289 刪／112 增）。
- `GLC_LINES` 98373→98196（`_FROZEN_GUARD_LINES` 舊基準 98236，Dev-Trim7 收工時餘裕 40 行）；`prose` 分桶 4528→4493（`_FROZEN` 基準 4512）；`guard_self` 3431 持平。
- 12 支模組各自 `unittest` OK、`ruff` `All checks passed`。**未做**逐檔重釘（`_FROZEN_GUARD_LINES` 逐檔基準與磁碟不符，`[逐檔漂移]` 共 15 支檔轉紅），依任務書明文「不准重釘任何棘輪常數／不准動 `_GUARD_LINES_REPIN_LOG`」留待收尾單人窗口——即本節〈收尾窗口〉。

### 實測（主控親跑）

```
$ cd tools/tests && python -m unittest test_context_window_parity test_root_guard_known_model_r145 \
  test_context_budget_guard test_check_hooks_liveness -q
Ran 818 tests in 39.537s
OK (skipped=15)
$ cd AISDLC_SDD/AISDLC_SDD_v0.30 && python -m pytest tools/fsm_runtime/tests/ -m "not chaos" -q
1920 passed, 8 skipped, 34 deselected, 14 subtests passed in 50.98s   rc=0
$ ... -m chaos ...
34 passed, 1928 deselected in 15.96s   rc=0
$ git status --short -- AISDLC_SDD/AISDLC_SDD_v0.30/governance/
（空）
$ python tools/session_resume_planner.py --check   # 於 12:5x
used 264,124／window 967,000／27.3%
```

棘輪現況（Dev-Trim7 收工後、Dev-C7 收尾前）：`GLC_LINES=98196`。主控在派下一輪工作前，`python tools/session_resume_planner.py --pace` 首行回報哨兵活性異常（見下〈喚醒鏈哨兵新缺陷〉），已當場 `--arm-sentinel` 重武裝止血。全套 `run_root_unittests.py` 未跑（主控收工後親跑）。

### 喚醒鏈哨兵新缺陷（DEF-200-286；本欄刻意零輪號）

主控派工前 `python tools/session_resume_planner.py --pace` 首行逐字：

```
🔴 哨兵活性：armed stamp 說 AutoSDD_Sentinel_17e2da67-e140-43a8-9817-d1b6f61f3f7a 已武裝，
排程器現查卻沒有這支工作 ⇒ 哨兵已死、喚醒鏈斷線（2026-08-16 事故形狀）
```

主控立即 `--arm-sentinel`：成功（`launchctl print` rc=0、interval 900s、plist 持久化；`launchctl list | grep AutoSDD_Sentinel_` 列出本 session 與前一 session `c65e030b` 各一）。取證缺口：重武裝覆寫了原 armed stamp（`/var/folders/…/autosdd_sentinel_armed_<sid>.json` 現為 11:57:49 的新值），SessionStart 那次武裝到底是 launchctl 失敗 fail-open 還是事後被卸載已無法分辨；`~/.autosdd/traces` 內查無本 session 事件。定 P1 open（喚醒鏈；根因未定；已登記 `docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-286；建議 armed stamp 改 append-only 或武裝時同步落 `launchctl print` 回讀證據）。

### 把握程度（誠實劃界）

- **高把握**：D27（ARCH-A4-01 分母鏈已補齊、效能以快取解決，端到端無釘值兩層數字與 source 逐字相等）、D28（SA-R7-01 加法式守衛，不翻既有預設，端到端 digest 測試證實 unchanged 語意）皆先紅後綠，且分別由 SD／SA／QA／Architect 四方或其三鏡至少一路徑獨立確認技術現象屬實。
- **中把握**：D29(a) SD-F1 的單向收斂殘留——分母被低估時百分比仍會系統性高於 `/context` 真實值，本輪判斷「這是既有安全取捨、不是本輪新缺陷」但**沒有解決**，日後若掌舵者實測到「數字比 /context 更高」的方向性落差，第一個該查的就是這個殘留。
- **P1 的殘餘邊界不變**：ARCH-A2-01（結構性 ESCALATION 全擋含 Read／Bash）本輪**未修**，是 R-9.5 刻意設計，D17 已提供溯源與恢復指令；是否要開窄例外放行 Read 留掌舵者裁決。
- **P2 的機制邊界（D29(c)）**：hook 對分子（真實 usage）與對「被擋」宣稱的雙重出聲機制已到位；**模型是否真的據以行動、是否真的去對照 /context** 結構上無法被 hook 保證，這是本輪與前六輪一致的誠實劃界，不會因為再修一輪而消失。
- **未驗證**：本 session 的三路徑數字一致性（119,598／967,000／12.4%）由 QA／SA 各自獨立算過，但**掌舵者本人尚未親自對照一次互動式 `/context` 面板**——同前幾輪劃界，subagent 結構上做不到。
- **Windows 未真機驗證**（同前幾輪）；D26 Models API 種子值仍未做（需憑證）；DEF-200-286（哨兵喚醒鏈）open，根因未定。

### 收尾窗口（Dev-C7，本節）

四方複審與修復波完工、工作樹無人再動之後，本窗口單人完成：

1. **證據檔**：本節（〈第七輪〉）撰寫；引用四方複審與三鏡驗證的逐字內容取自 `journal.jsonl`（見〈觸發〉節路徑）。
2. **缺陷帳本**：新增 `DEF-200-284`（ARCH-A4-01，P1，fixed 第七輪 D27）／`DEF-200-285`（SA-R7-01，P2，fixed 第七輪 D28）／`DEF-200-286`（哨兵 armed stamp 與 launchd 實況不一致，P1，open）三列；`DEF-200-275` 列補「第七輪 2026-09-12 D27 補根層⑥階查表收斂」一句，仍 <700 bytes。
3. **護欄層逐檔重釘**：`_FROZEN_GUARD_LINES` 依 `--print-guard-lines` 實測值重釘 15 支檔（`test_block_destructive_git_r83.py` 2288→2285／`test_context_budget_guard.py` 11909→11950／`test_context_window_parity.py` 145→229／`test_dev_start_ps1_lastexitcode.py` 548→521／`test_doc_env_prefix_platform_parity_r60.py` 340→331／`test_doc_loc_baseline_freshness_r60.py` 7155→7145／`test_gha_action_versions.py` 703→681／`test_no_invalid_escape_sequences.py` 339→315／`test_ntfs_trailing_space_device_name.py` 760→759／`test_platform_utils_dedup.py` 1112→1078／`test_root_guard_known_model_r145.py` 215→227／`test_sanitize_component_frozen_sdd_versions_lock.py` 340→317／`test_skip_discoverability_r83.py` 744→742／`test_smoke_ci_sync.py` 1399→1397／`test_windowsapps_guard_bash_parity.py` 973→953）；`_GUARD_LINES_REPIN_LOG` 新增兩列（R146 主表 −40／R146 本檔自身自含式漂移 +15，總淨額 −25，98236→98211，**淨減法輪**）；`_REPIN_LOG_FROZEN_PREFIX_LEN` 172→174、`_REPIN_LOG_HISTORY_SHA256` 重釘；`_FROZEN_PREFIX_REWRITE_LEDGER` 接鏈一列（`67af3c96e763`→`a4aa9940f730`，`DEF-200-275`）。doc-total 對帳（≥2 站點）：`docs/04_planning/AutoSDD_improving_112.md` 與 `docs/06_quality/CrossPlatform_R145_Scan_Findings.md`〈第七輪附記〉皆補 `<!-- guard-total:R146 -->` 標記行（同 R129～R145 寄居體例，不另建新檔）。逐檔清單全文見 `CrossPlatform_R145_Scan_Findings.md`〈第七輪附記〉節。
4. **零新檔**：本窗口未新增任何檔案（`tools/lib/governance_docs.py` 無需登記）。
5. **收工驗證**：`test_adr_xplat001_c1c2_lock`／`test_check_defect_log_crossref`／`test_doc_loc_baseline_freshness_r60`／`test_check_hooks_liveness` 四支根層 unittest 皆 `OK`；`test_check_defect_log_crossref` 單獨執行時因與 git HEAD 相比多出 1 筆淨新增未結列（`DEF-200-286`）觸發淨額棘輪 `❌`——此為既有記憶備忘所述「commit 前全套恰幾紅是預期，commit 後 pre-push 全綠」的已知模式（比較基準是尚未 commit 的 git HEAD），非新缺陷；帳本承接指派、輪號標籤、逐列位元組上限三項判準皆已修復為綠。

### 修後複審（Architect／SA／SD／QA 四方唯讀、皆 Sonnet 5；2026-09-12，全數 APPROVE ⇒ 進入收尾）

| 角色 | 判決 | 問題 1／2／3 | 發現 |
|------|------|-------------|------|
| Architect | APPROVE | partial／partial／fixed（1＝ARCH-A2-01 留裁決；2＝D29(c) 結構性邊界） | ARCH-F1 P3 |
| SA | APPROVE | fixed／fixed／fixed | 無 |
| SD | APPROVE | fixed／partial／fixed | SD-P3-01 P3（與 ARCH-F1 同一件事） |
| QA | APPROVE | fixed／fixed／fixed | 無 |

- 各自親跑（[他包回報]）：SDD `1920 passed, 8 skipped` rc=0、chaos `34 passed` rc=0（Architect／SA／QA 三方皆與主控親跑逐字相同）；根層針對性 `Ran 818 tests` `OK (skipped=15)`（QA／SD）；`test_adr_xplat001_c1c2_lock` `Ran 192 tests` `OK`、`GLC_LINES=98211`（四方皆核）；SD 以 `wc -l` 逐支核對 15 支重釘檔行數與 `_FROZEN_GUARD_LINES` 新值精確相符，並逐 hunk 讀完 12 支 Dev-Trim7 檔確認零 assert／零判準改動；SA 核 `test_check_defect_log_crossref` 恰 2 支已知 pre-commit 紅、帳本三列 591／632／677 bytes、DEF-200-275 補句後 661 bytes；SA 同時刻三條算法對主控逐字稿 `used=315,258／window=967,000／32.6%` 三路徑相等。
- QA 黑箱（[他包回報]）：對 `used=188,000、無釘值、model=claude-fable-5-1` 的假逐字稿，HEAD 舊 hook `rc=2` 硬擋並印 `94.0%`（分母仍是猜的 200,000）；改後 hook 同一輸入 `rc=0` 靜默（18.8%）——問題 1＋3 形狀的直接消失證據。有釘值／無釘值 × Read／Write／Bash 六組首擊皆 `rc=0` 無誤報；快取檔改成不存在路徑或亂碼 bytes 時 hook 仍 `rc=0` 且自我修復（fail-open）；D28 三象限（REQUIRES=1 無 ENTRY→digest 不變＋stderr 恰一次／ENTRY=1→fire_count+1／顯式 FIRE=0 覆蓋 ENTRY=1→不寫）全符合，全程 governance/rules 零列；Stop hook 對無佐證「被擋」宣稱出聲。
- **D30 追加登記（P3，不修）**：ARCH-F1／SD-P3-01——`known_model_windows_path(session_id=…)` 的 per-session 表路徑快取只以 `is_file()` 判有效，同一 session 內若發生 Copy-on-Evolve 換 LATEST 且舊版目錄仍在，快取不失效、會續用舊版表；且快取讀寫／三條 fail-open 分支無回歸測試。影響窄（單 session 內切版）、方向不定；候選修法＝快取內容加記 LATEST 目錄名或 `AISDLC_SDD/` 目錄 mtime、讀取時比對。Architect 另記一項前瞻性殘餘：D28 對「未來新增的 FSM 生產呼叫端忘記設 `SDD_FSM_HOOK_ENTRY`」無機械鎖（現況靜態搜尋零違反，生產呼叫端僅三支具名 hook）。
- 總架構師裁決：四方全 APPROVE、無 P0～P2 ⇒ 進入收尾單人窗口（全套根層閘門 → ONBOARDING §7 表② 回填 → commit → push）。

### 收尾窗口補修（主控親跑；修後複審 APPROVE 之後、push 之前發現的兩處）

- 根層全套 `python tools/run_root_unittests.py` → `Ran 4160 tests` `FAILED (failures=3, skipped=46)`：2 支＝commit 前已知淨額棘輪紅（`test_check_defect_log_crossref` 兩案），第 3 支 `test_subprocess_encoding_hygiene.TestEntryPointStdioProtection.test_entry_points_printing_non_ascii_are_protected` 指 `fsm_runtime.py` D28 的中文 stderr 警告「入口點印非 ASCII 但無 UTF-8 stdio 保護」。第一次修法（就地 `sys.stderr.reconfigure(encoding="utf-8", errors="replace")`）通過 hygiene 卻在 pre-push 被 `test_platform_utils_dedup` 的 stdio-SSOT 複本棘輪擋下（`行內 stdio-UTF-8 複本 1 處 > 凍結值 0 處`；SSOT＝`tools/_stdio_utf8.py`，但 AISDLC_SDD 不得跨專案 import）。最終修法＝沿用同檔 `_cli()` 既有慣例把警告改全 ASCII（`[SDD-FSM] rule telemetry write-back skipped: not a hook process (...)`），測試斷言同步。複驗：`test_subprocess_encoding_hygiene test_platform_utils_dedup` → `Ran 72 tests` `OK`；D28 `13 passed`；SDD `1920 passed, 8 skipped` rc=0。
- pre-push 快層 `ruff check tools/ .claude/hooks/` 抓到 Dev-A7 的 `known_model_windows_path()` 簽名 E501（101 > 100）：拆成兩行並把同函式 docstring 壓縮一行，檔案維持 1089 行（SPECIAL_FILES 上限）；`ruff` → `All checks passed!`；`test_adr_xplat001_c1c2_lock` 等 `Ran 839 tests` `OK (skipped=10)`。
- 教訓（主控）：`ruff … | tail -1` 接管線吃掉 rc，讓第一次 commit 在 lint 紅的情況下通過——鐵律六「讀 rc 不接管線」在 zsh 側零攔截器（DEF-200-086）再一次現形；第二次改為 `&&` 串接無管線。

### 掌舵者裁決（2026-09-12，push a264e72 之後）＋ /context 親對

- **ARCH-A2-01 裁決＝A（維持現狀）**：結構性（規則寫入的）ESCALATION 對所有 session 全擋、含 Read／Bash，D17 溯源＋一行恢復指令由人在 Claude Code 外的真終端執行；**不**對非觸發者 session 放行 Read。理由（主控建議、掌舵者採納）：context 來源的 ESCALATION 自第四輪起已不再由 hook 寫入，剩下的都是真的要人介入的情況，訊息已交代怎麼解。本項自此為已裁決事項，不再另案。
- **/context 親對（掌舵者於本 session 執行，逐字）**：`393.9k/1m tokens (39%)`；`Autocompact buffer: 33k tokens (3.3%)`；`Auto-compact window: 1m tokens`。主控 `python tools/session_resume_planner.py --check` 前後兩次逐字：/context 前兩則訊息 `used 391,289 … window 967,000 … 水位 40.5%`；/context 後一則 `used 400,305 … 水位 41.4%`。結論：**分子同源且一致**（393.9k 落在兩次量測之間，差值＝中間訊息本身）；**分母差＝定義差**：1,000,000 − 33,000（autocompact buffer）＝ 967,000，即 `~/.claude/settings.json` 的 `AUTOSDD_CONTEXT_WINDOW=967000` 釘值，故百分比 39% vs 40.5% 不是缺陷。問題 3 至此由掌舵者親對關閉。
- **「現在是否已真實查詢 /context 容量」誠實答**：分子＝逐字稿裡 API 回報的真實 usage（與 /context 同源）；分母＝釘值或快取表（`known_model_windows.json`：seeded_from＝claude-api skill cached table 2026-06-24、refreshed_at＝null），**未**打 Models API（D26 仍需 `ANTHROPIC_API_KEY`）；本次 /context 證實 claude-fable-5-1 為 1m，與表值一致。要讓工具百分比與 /context 完全相同，只需把釘值改為 1000000（或移除釘值改走查表），但 967,000 是「autocompact 前可用視窗」的保守定義，主控建議維持。


### 第七輪追加 A（2026-09-12）：windows-compat-ci #220／#221 ⇒ D31／D31b／D31c（DEF-200-287）

#### 觸發

windows-compat-ci #220／#221 紅：
```
test_conversation_ledger.py:401 199 != 200
test_conversation_ledger.py:463 0.3084s ≥ 0.3s
```
（mac 上不會踩到的 Windows 檔案鎖競態：多行程並行 append + merge 時，`os.replace()`／`Path.unlink()` 對「開著 handle」的目的檔在 Windows 上會拋 `PermissionError`(WinError 5/32)，導致合併漏筆〔199≠200〕與效能斷言在 CI runner 波動下臨界值超標。上列兩行為主控整理轉述的 CI 失敗摘要，非本檔逐字保存的原始 pytest traceback。）

#### 根因

稽核帳本（`AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/conversation_ledger.py`）的多行程 append/merge 路徑，隱含「不管有沒有人開著 fd，rename/unlink 一律成功」的 POSIX 假設在 Windows 上不成立；`file_lock.py` 的 `_try_unlink` 同樣假設單次嘗試即成功。

#### D31（第一棒）

- `_replace_with_retry`：`os.replace` 遇 `PermissionError` 重試 10×20ms 才拋出具名例外 `LedgerReplaceDenied`（不是泛用 `OSError`）。
- `append_ledger_entry` 先捕捉 `(TimeoutError, LedgerReplaceDenied)`（早於泛用 `except OSError`），降級寫 sidecar，而不是靜默回 0；G4（讀不到主檔 → 回 0、不寫 sidecar）語意不變。
- `_merge_sidecar_if_present` 讀取前先 `os.replace(sidecar, claimed)` 認領改名，避免讀取期間另一支 append 交錯造成遺失。
- `file_lock.py::_try_unlink` 對 transient `PermissionError`/`OSError` 重試 10×20ms 才回 `False`。
- 新增 `LedgerReplaceRetryTests`（7 測試）、`test_try_unlink_retries_transient_permission_denied`；`LedgerPerformanceTests.LIMIT_SEC` 在 Windows/CI 放寬到 1.0s（mac 本機維持 0.3s）。

mac 親跑：`test_conversation_ledger.py`+`test_file_lock.py` 44 passed 1 skipped；`pytest tools/fsm_runtime/tests/ -m "not chaos"` 1928 passed, 8 skipped；`bash scripts/ci-gate.sh` 全綠（v0.01:1475、v0.30:1928、scripts/tests:351）。

#### 第一棒複審：W／C 皆 REJECT

- **W-1（P1）**：`_merge_sidecar_if_present` 認領式改名把「失敗就整份保留、下次重來、零遺失」的語意換成「認領先發生、讀取/合併/持久化後發生」——若持鎖行程在 `os.replace` 成功後、`_atomic_write_yaml` 完成前被中止（正是本輪要防的 `sdd_hook_router.py` 8s child timeout 砍法），`claimed`（`<sidecar>.merging.<pid>`）永久孤兒，`cleanup_orphan_part_files()` 只 glob `.part.*`，不掃 `.append.merging.*`，零清理機制。
- **C3（P2）**：即使認領改名縮小了交錯窗口，仍未「消除」——若 process B 的 `open(sidecar,'a')` 拿到 fd 發生在 A 的 `os.replace` 之前、寫入發生在 A 完成 claim→read→merge→unlink 之後，B 寫入的 bytes 進了一個已無目錄項指向的 inode，close 後立即被 OS 回收，且連可事後稽核的殘檔都沒有。已用真實檔案系統操作（非 mock）重現，rc=0（腳本正常結束，是資料遺失的證明）。
- **W-2（P2）**：各重試預算各自論證「不逼近 8s」，但未見跨站點組合式最壞情境預算分析。
- **C5（P2）**：`LIMIT_SEC` 放寬到 1.0s 後，1500 筆規模下若 libyaml 退化回純 Python `safe_load`/`safe_dump`（DEF-200-275 第五輪要防的退化）耗時僅 0.67s，仍在放寬後門檻之內，測試會綠燈放過；且 macOS GitHub Actions runner 也會設 `CI=true`，「mac 本機仍保留 0.3s 緊門檻」的宣稱對 macos-compat-ci.yml 這條腿不成立。

#### D31b（第二棒；解 W-1／C3）

- sidecar 由「共用檔＋認領改名」全面改成「每筆一檔、寫成即不可變」：`_write_sidecar` 用 pid+時間戳+序號專屬檔名（`_sidecar_unique_suffix`）+ `_replace_with_retry`。
- `_merge_sidecar_if_present` 改回傳 `(merged, safe_to_delete)`，不再自己刪檔；刪除延後到 `_merge_locked` 在 `_atomic_write_yaml` 成功之後才呼叫 `_delete_sidecar_sources`；`folded_sidecar_ids` 書籤（依檔案是否存在自我裁剪）擋「持久化成功、刪除前被砍」的重複折算。
- 新增 `_iter_sidecar_sources`/`_read_sidecar_entries` 相容折回舊格式 `.append` 單檔與第一棒孤兒 `.append.merging.<pid>`。
- 預算下修：`_REPLACE_RETRY_ATTEMPTS` 25→10（0.5s→0.2s）、`file_lock._UNLINK_RETRY_ATTEMPTS` 10→5（0.2s→0.1s）；新增 `HOOK_CHILD_TIMEOUT_SEC=8.0`（鏡射 router）與 `worst_case_ledger_budget_sec()`。
- 新增 `LedgerSidecarFoldingTests`（W-1/C3 正式回歸鎖）、`LedgerLockBudgetTests`；`LedgerPerformanceTests` 加 `CSafeLoader`/`CSafeDumper` 身分斷言、`LIMIT_SEC` 改依平台不再依賴 `CI` 環境變數。

mac 親跑：125 passed 1 skipped（四支 ledger/hook 測試）；`not chaos` 1934 passed 8 skipped；ci-gate 全綠；並行測試 10/10；`worst_case_ledger_budget_sec()=5.5 ≤ HOOK_CHILD_TIMEOUT_SEC=8.0`。

#### 第二棒複審：C APPROVE／W REJECT（W-4 P0）

- **C（並行正確性，唯讀）APPROVE**：C1~C6 六項機械物皆重現確認——`open("a")` 共用檔站點已結構性消除、C3/W-1 回歸鎖通過、10/10 並行穩定、舊格式與第一棒孤兒皆能相容折回、G4 語意不變、C5 降級後身分斷言可靠變紅（1.4189s≥0.3s，與 D31b-4 docstring 對 mac 緊門檻的宣稱一致）。
- **W（Windows 檔案語意，唯讀）REJECT——W-4（P0）**：`_write_sidecar` 自身的 `os.replace(tmp,final)` 若永久被拒絕存取，`finally` 區塊會**刪掉唯一副本的 tmp 檔**——sidecar 這條「最後防線」本身無聲遺失資料，且觸發條件不需要行程被砍，一般 AV/索引器對「剛寫完準備 rename 的檔案」短暫持鎖即可（正是 windows-compat-ci #220/#221 的同型現象）。唯讀重現腳本 monkeypatch `os.replace` 對 sidecar final rename 永遠拋 `PermissionError(5)`：`files after _write_sidecar under permanent AV-hold on final rename: []`，`VERDICT: DATA LOST — entry vanished with no trace (finding CONFIRMED)`。
- 附帶 **W-2b（P2）**：D31b 下修的重試預算（25→10、10→5）縮小了「可容忍的瞬時持鎖窗口」，放大 W-4 的觸發機率；Dev-W7b 自己在 not_done 已誠實揭露「無法在真實 Windows CI 驗證縮短後的重試預算是否仍覆蓋現場實測窗口」。

#### D31c（第三棒；解 W-4／W-2b／W-3／W-5）

- `_write_sidecar` 不再對 `LedgerReplaceDenied` 無條件 `finally`-unlink tmp（那是這筆 entry 的唯一合法副本）——只在 dump 本身失敗或 replace 成功時才清 tmp。
- `_iter_sidecar_sources` 新增對 `.append.part.*` 的折回判準（來源 pid 已死或 mtime > `_SIDECAR_PART_FOLD_AGE_SEC=30s` 才折，避免讀到半成品）；`cleanup_orphan_part_files` 不再掃描 `.append.part.*`（那是 sidecar 唯一副本，交由折回路徑處理，不得直接刪）。
- `_merge_sidecar_if_present` 對解析失敗的 sidecar 印一行 ASCII stderr 警告（不刪、不崩）。
- 新增 `TestConversationLedgerChildTimeoutParity`（`tools/tests/test_check_hooks_liveness.py`）：純 ast 讀原始碼字面比對 `sdd_hook_router.py` 的 `_CHILD_TIMEOUT["PostToolUse"]` 與 SDD LATEST `conversation_ledger.py` 的 `HOOK_CHILD_TIMEOUT_SEC` 相等，含注入紅自證（解 W-3）。
- `tools/tests/test_platform_neutral_paths.py` 的 `_DIRENT_UNGUARDED_DEBT` 註解追記訂正（解 W-5；數字仍 39，未變動）。
- 新增 `LedgerSidecarPartRetentionTests`（6 測試）：replace 被拒後 tmp 保留且為合法 YAML；夠舊的 part 檔被折回並刪除、新鮮且來源行程存活的 part 檔不折不刪；`cleanup_orphan_part_files` 對 `.append.part.*` 不刪、對 `.yaml.part.<dead pid>` 仍刪（回歸鎖）；損毀的 `.append.part.*` 印警告不刪。紅綠自證：暫時還原成 D31b 的無條件 `finally: tmp.unlink()` 時 `test_replace_denied_keeps_a_valid_yaml_tmp_not_an_empty_husk` 真的紅（`0 != 1`），修復版全綠（50 passed in 1.99s）。

mac 親跑：131 passed 1 skipped；`not chaos` **1940 passed, 8 skipped**；ci-gate 全綠；並行測試 10/10；`ruff check` 僅既有 1 個 F401 舊帳（`import json` unused，非本輪 diff 內）。

#### 第三棒複審：W／C 皆 APPROVE

- **C（並行正確性）APPROVE，登記 C-1（P3，不修）**：永久損毀的 `.append.part.*` sidecar 檔（因寫入時被 SIGKILL 而永久損毀，非暫時性半成品）無終局清理路徑——`_read_sidecar_entries` 解析永遠失敗 ⇒ 每次 merge tick（預設每 10 個工具呼叫）都重跑一次、永遠失敗、永遠印一次 stderr 警告，殘檔永遠留在磁碟，無路徑把它移進「已確認損毀、不再重試」的終局狀態。既有設計即承認的取捨（docstring 明寫「供事後查驗」），非本輪引入的資料遺失，屬長跑部署下未加蓋的資源／日誌噪音成長點，登記不修。
- **W（Windows 檔案語意）APPROVE**：用兩支真實子行程（非 mock）驗證核心爭點——(1) 子行程存活+新鮮時 part 檔被排除在 `_iter_sidecar_sources` 之外；(2) 子行程被砍在半寫階段（pid 已死但 mtime 新鮮）時，`_merge_sidecar_if_present` 對無法解析的 YAML 一律不刪、印警告，不誤判成合法內容或靜默丟資料。fnmatch 獨立重算確認 `cleanup_orphan_part_files` 的 glob 與 sidecar 命名空間互斥。W-4/W-2b/W-3/W-5 四項視為已關閉。

#### 誠實劃界

- 本三棒全程在 macOS 上進行；`PermissionError`/WinError 5/32 一律靠 `monkeypatch` `_replace_with_retry`/`os.replace` 模擬，**無法驗證真實 NTFS/AV/索引器鎖行為本身**——這是連續三輪複審共同承認的邊界。真正的驗收只能等**下一次 windows-compat-ci** 跑 #220/#221 對應的測試轉綠。
- C-1（`.append.part.*` 永久損毀無終局清理）登記不修，理由見上；長跑部署下若噪音／磁碟殘留成為實際困擾，需另立缺陷。

#### 掌舵者裁決

Windows 修復（DEF-200-287）與 D32（DEF-200-288，見下）**合併一次 push**，不分兩次——節省 CI 額度；push 後以 windows-compat-ci 下一次跑動驗證 #220/#221 轉綠。

---

### 第七輪追加 B（2026-09-12）：status line 餵數 ⇒ D32／D32b（DEF-200-288）

#### 觸發

掌舵者追問（本欄刻意零輪號）：兩層守衛（根層 `.claude/hooks/context_budget_guard.py`、SDD `context_window.py`）量的都是「context 水位」，但分母始終只能靠**釘值**（`AUTOSDD_CONTEXT_WINDOW=967000`）、**查表**（`known_model_windows.json`，`refreshed_at=null`，未打 Models API）或**推論**，而 Claude Code **status line** 是唯一同時給「容量」（`context_window.context_window_size`）與「用量」（`current_usage` 三欄）的官方介面；hooks 的 stdin payload 完全沒有容量欄位。這條分母鏈本輪之前從未接上它。

#### D32（第一棒）

- 新檔 `tools/statusline_context_feed.py`：讀 status line 的 stdin JSON，原子寫入 `~/.autosdd/context_feed/<session_id>.json`；印 ASCII 一行給 UI（`used_percentage` 為 `null` 印 `n/a`，≥84% 前綴 `!`）；任何例外一律吞掉印 `ctx ? (feed error)` 並 `exit 0`（不可讓 status line 本身崩潰使用者終端）；`--print-settings-snippet` 印可貼進 `settings.json` 的 `statusLine` 區塊（本 checkout 絕對 python/腳本路徑、POSIX 正斜線）。
- `.claude/hooks/context_budget_guard.py`：新增 `SOURCE_HARNESS`、`context_feed_path()`、`read_context_feed()`；`resolve_window()` 加 ⓪ harness 回報階，優先於既有 `AUTOSDD_CONTEXT_WINDOW` 釘值；`main()` 在 WARN/HARD 訊息後附加分子交叉比對（差 >5% 才出聲，不新增阻斷門檻）。
- `tools/session_resume_planner.py::measure()`：呼叫 `guard.read_context_feed()` 取得 `harness_window`/`harness_note`/`harness_used`，覆寫進 `window_evidence()` 的證據字典；`--check` 新增一行 `harness used=… 逐字稿 used=… 差=…`。
- SDD 側 `context_window.py` 鏡像：`resolve_window()` 在 ①`SDD_MAX_CONTEXT` 之後、②`AUTOSDD_CONTEXT_WINDOW` 之前插入 ⓪′ harness 回報階；`Measurement` 加 `harness_used`。
- 新檔 `tools/tests/test_statusline_context_feed.py`；`tools/tests/test_context_budget_guard.py` 新增 `HarnessFeedStageTest`（20 案例）；`tools/tests/test_context_window_parity.py` 新增 `HarnessStageParityTest`。

mac 親跑（合併跑法前）：`test_statusline_context_feed`／`test_context_budget_guard`／`test_context_window_parity` 各自全綠；`not chaos` 1940 passed（與改動前基線相同）；`test_adr_xplat001_c1c2_lock` 3 個既有失敗（新檔未進 `_FROZEN_GUARD_LINES`、淨行數 +519，屬結構性、非本包職權修）。

#### 第一棒複審（A／Q 兩鏡）：皆 REJECT

| 鏡 | finding | 嚴重度 | 摘要 |
|---|---|---|---|
| Q | Q-1 | P1 | `tools/session_resume_planner.py` 觸犯 `check_loc_budget.py` guardrail_cli 分級（760>750），Dev-S8 回報未揭露（只提了 hook 那一筆） |
| Q | Q-2 | P2 | `read_context_feed()` 四種拒絕情境的 `reason` 欄位有寫入、無人消費——`--check`／hook 訊息對四種不同拒絕原因輸出完全相同，違反掌舵者「不成立需印一行原因」的明確要求 |
| A | A5-LOC-BUDGET | P1 | `.claude/hooks/context_budget_guard.py` 1147 行 > SPECIAL_FILES 上限 1089（+58），任務書 D32-6 明文要求的「搬史料抵銷」未做到 |
| A | A5-CIGATE-PATHS | P1 | 新檔 `tools/statusline_context_feed.py` 未列入 macos/windows-compat-ci.yml 的 `paths`，只改它時兩份 compat CI 不會跑回歸鎖（`bash scripts/ci-gate.sh` 現場重跑 2 failed） |
| A | A-TOOLSTESTS-RATCHET | P2 | `tools/tests` 淨額棘輪三支測試紅（既有模式，任務書禁止本包重釘，登記交收尾窗口） |
| A | A4-UILINE-NUMERATOR | P3 | `ui_line()` 分子取 `total_input_tokens`，判定邏輯（`cross_check_note()`）卻正確地用 `current_usage` 三欄和——顯示層與判定邏輯用了不同分子來源，測試附的樣本恰好讓兩者相等，並不保證官方 schema 恆等 |

#### D32b（第二棒；S8b／Trim8 全修，解上列六項）

- `.claude/hooks/context_budget_guard.py`：`main()` 改為只呼叫一次 `read_context_feed()`；`window_evidence()`/`cross_check_note()` 改接受呼叫端傳入的 feed 字典（解 Q-2 重複讀的前置）；`read_context_feed()` 把「無 feed 檔」與「壞 JSON」拆成不同 reason 字串，`cross_check_note()` 未採用時印「harness feed 未採用：<reason>」（解 Q-2）；模組 docstring 與 8 個函式 docstring 的展開版沿革搬到證據檔，raw line **1147→1087**（棘輪上限 1089，餘裕 2 行，解 A5-LOC-BUDGET）。
- 新檔 `tools/lib/harness_feed.py`：`measure()`（從 planner.py 搬來，guard 依賴注入，stdlib only）與 `check_lines()`；`tools/session_resume_planner.py::measure()` 改轉呼叫，guardrail_cli 計價 **760→740**（解 Q-1）。
- `tools/statusline_context_feed.py`：新增 `_current_usage_sum()`，`ui_line()` 分子改用 `current_usage` 三欄和，不再用 `total_input_tokens`（解 A4-UILINE-NUMERATOR）；新增回歸測試灌兩個不同值證明分子來源。
- `.github/workflows/macos-compat-ci.yml`／`windows-compat-ci.yml`：`paths` 清單（push/PR 對稱）新增 `tools/statusline_context_feed.py`、`tools/tests/test_statusline_context_feed.py`、`tools/lib/harness_feed.py`（第三筆是 `test_ci_paths_cover_root_consumers.py` 掃描器實測要求的，任務書原文只列前兩筆）（解 A5-CIGATE-PATHS）。
- SDD 側 `context_window.py`/`session_start.py` 鏡像同步：`Measurement` 新增 `harness_reason`，`[SDD-CTX]` 行在有值時附加「；harness feed 未採用：<reason>」。
- Dev-Trim8（同輪並行）：15 支 `tools/tests/*.py` 搬約 80 段歷史敘事，`GLC_LINES` 98730→98157（frozen 98211，淨 −54），供 A-TOOLSTESTS-RATCHET 的收尾重釘鋪路（見步驟 4）。

mac 親跑（D32b-6 指定合併跑法）：`test_statusline_context_feed`＋`test_context_budget_guard`＋`test_context_window_parity`＋`test_root_guard_known_model_r145`＋`test_subprocess_encoding_hygiene`＋`test_platform_utils_dedup`＋`test_check_hooks_liveness` 共 **935 tests OK (skipped=15)**；SDD `context_window.py` 40 passed；`not chaos` 1941 passed；`bash AISDLC_SDD/scripts/ci-gate.sh` 全綠；`scripts/tests/test_ci_paths_cover_root_consumers.py` 49 passed（兩份 compat workflow 皆轉綠）；`ruff check tools/ .claude/hooks/` 與 SDD 三檔皆 `All checks passed!`；`cd AutoClaude && python tools/check_loc_budget.py` violations=0。

`python tools/session_resume_planner.py --check`（隔離 feed 目錄）逐字：
```
window    1,000,000〔harness 回報（status line context_window.context_window_size；model=claude-fable-5-1；釘值 967,000 未採用）〕
harness used=576,752 逐字稿 used=576,752 差=0
```

#### 第二棒最終複審（final:architect／final:qa，兩鏡並行唯讀，聚焦 D32b）：皆 APPROVE

- **final:architect APPROVE，登記 A2-SDD-DOUBLE-READ（P2，不修）**：根層 `main()` 已改成 feed 只讀一次並下傳給 `window_evidence()`/`cross_check_note()`（`harness_feed.py` docstring 明講「feed 只讀一次」），但 **SDD 側 `context_window.py::window_evidence()` 沒有對應的 `feed=` 參數**——四個生產呼叫點（`session_start.py:65/86`、`context_ledger_pre.py:265`、`context_ledger_post.py:90`）都是先呼叫 `measure()`（內部已讀一次 feed）、再呼叫 `window_evidence()`（內部又讀一次同一份 feed 檔），同一次 hook 觸發對同一 session 的 feed 檔讀了兩次。純屬效能／一致性瑕疵（fail-open 讀檔失敗兩次都吞掉，結果值一致，不影響判定正確性），未同步到 SDD 側，登記不修。
- **final:qa APPROVE，登記 Q3-GAP-01（P2，不修）**：`block_verdict()`/`block_message()`（PreToolUse 真正擋下展開型工具那條路徑）沒有接上 `cross_check_note()`，只有 PostToolUse 的 `warn_message()`／`hard_message()`（≥84%／≥94%）接了——結果是「使用者的工具呼叫真的被擋下」的那一刻，stderr 反而不含 harness reason，三條訊息路徑分母證據不對稱。親跑覆核：PreToolUse 阻斷時 stderr 全文 grep `harness|reason|未採用` 零命中；同一份逐字稿改 PostToolUse 觸發 hard_message 則會印「harness feed 未採用：無 feed（statusLine 未設定或本 session 尚無 assistant 訊息）」。既有回歸測試全數只打 PostToolUse，從未對 PreToolUse block 路徑斷言過這行；不影響既有回歸（三套測試全綠、rc 全 0），性質類似 D31c 的 C-1「登記不修」判例，登記不修。

（原任務書預告的 P3 登記名目「ARCH-F1／SD-P3-01」經查 `journal.jsonl` 與實際不符——兩鏡最終複審實際各登記一筆 **P2**〔A2-SDD-DOUBLE-READ、Q3-GAP-01〕，非 P3；本節以 `subagents/workflows/wf_33ff7599-e2d/journal.jsonl` 實測結果逐字為準，訂正預告命名。）

#### 誠實劃界

- 掌舵者 mac 個人 `~/.claude/settings.json` 已加 `statusLine` 設定（讀 `--print-settings-snippet` 產出）；**repo 層 `settings.json` 刻意不加**——Windows 上 status line 走 shell 呼叫會閃 console 視窗，違反〈Windows 側單一載具原則〉鐵律一的 exec-form 精神，且並非所有機器都想要這個功能。其他機器（未手動設定 statusLine 者）status line feed 檔不存在，`read_context_feed()` 的「無 feed」reason 分支接手，分母鏈退回既有的釘值／查表/推論五階鏈，行為與本輪之前完全相同（向後相容、零迴歸）。
- **D26（真的打 Models API 現查容量）仍未做**：`known_model_windows.json` 的 `refreshed_at=null`、`seeded_from` 仍是快取表（2026-06-24），需要 `ANTHROPIC_API_KEY`。本輪只是多接上 status line 這個「不需要 API key 的官方分母來源」，兩者互補不互斥。
- 兩鏡最終複審登記的 A2-SDD-DOUBLE-READ、Q3-GAP-01 皆判定不影響正確性／既有回歸，予以登記不修；若未來 PreToolUse 阻斷訊息也要帶 harness reason，或 SDD 側要接住已讀 feed 省一次 I/O，需另案排入。

#### 掌舵者裁決

DEF-200-287（Windows 修復）與 DEF-200-288（D32 status line 餵數）**合併一次 push**，不分兩次——節省 GitHub CI 額度；push 後以下一次 windows-compat-ci／macos-compat-ci 跑動驗證兩者的回歸鎖與新 paths 涵蓋皆轉綠。


#### 收尾窗口最終登記（主控，2026-09-12）

- **最終複審 P2 登記（不修，總架構師裁決）**：(a) A2-SDD-DOUBLE-READ——SDD 側 `context_window.window_evidence()` 未接住 `measure()` 已讀的 feed，四個生產呼叫點各多讀一次 feed 檔（純效能，本機小檔；根層已於 D32b-1a 修為只讀一次）；(b) Q3-GAP-01——根層 PreToolUse `block_message()` 未併入 `cross_check_note()`，真正擋下展開型工具那一刻看不到「harness feed 是否採用／原因」（PostToolUse warn／hard 兩處已有）。不在本輪修的理由：hook 檔 1087／1089 只剩 2 行餘裕，再搬史料的邊際風險（Dev-S8 兩次誤傷既有測試）高於收益；兩項皆已列為下一輪 D33 候選。
- **搬史料副作用訂正**：`test_doc_loc_baseline_freshness_r60` 三支紅——`tools/tests/test_context_budget_guard.py` 一處反引號提到已改名的舊測試名（幽靈符號）改為敘述文字；`_MY_PIPE_RE`／`test_ac_matches_sum_of_seven_registries`／`test_is_windows_apps_stub_defined_exactly_once` 三筆豁免登記因引用面（被 Dev-Trim8 搬走的敘事）已無人提及而過期，依該判準「幽靈已清乾淨請刪登記」移除，原位置以註解行保留行數（避免再一次 `_FROZEN_GUARD_LINES` 逐檔重釘鏈）。
- **shrink-only 分桶 frozen 未下修**（prose 4512→現值 4496、guard_self 3431→現值 3313，住 `tools/lib/guard_bucket_policy.py`）：方向合法（現值低於 frozen），留下一收尾窗口下修。

## 第七輪 史料搬遷（Dev-A7；context_budget_guard.py 原文逐字保全）

全文移至 CrossPlatform_DEF200275_Context_Metering_Lore.md 同名節。

## 第七輪 史料搬遷（Dev-Trim7；護欄層原文逐字保全）

全文移至 CrossPlatform_DEF200275_Context_Metering_Lore.md 同名節。

## 第七輪 史料搬遷（Dev-S8b；context_budget_guard.py 原文逐字保全）

全文移至 CrossPlatform_DEF200275_Context_Metering_Lore.md 同名節。

## 第七輪 史料搬遷（Dev-Trim8；護欄層行數搬史料抵銷）

全文移至 CrossPlatform_DEF200275_Context_Metering_Lore.md 同名節。

