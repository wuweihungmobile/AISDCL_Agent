# R89 交棒書 — 單人輪（額度 halt，四方複審結構上派不出去）

> **Session ID**：`b2e798a7-52c9-4d95-9084-ab0858958641`
> 重啟：`claude -r b2e798a7-52c9-4d95-9084-ab0858958641`
>
> 🔴 **重啟後第一件事是重驗，不採信本書任何「已通過」宣稱**（〈可重啟點四條件〉第 4 條）。

## 0. 本輪為什麼是單人輪

`python tools/session_resume_planner.py --pace` 當回合實測：

```
現在可派 0 個 agent（硬上限 cap=0）｜band=halt｜最緊的一條＝extra_usage 100% reset 距離不明
派工前置：credits 已耗盡、已停用 ⇒ **無 fallback**，訂閱窗即硬牆
⏳ 這一條**沒有 reset 可以等**（例：月度支出上限）；只有人去提額 ⇒ 這道節流不會自己解除。
```

訂閱窗健康（session／five_hour 13%、seven_day 22%），卡住的是 `extra_usage`／`spend`
兩軸（皆 100%、`resets_at=null`）⇒ PreToolUse 守衛結構上擋下**所有**扇出。

🔴 **不得繞過**：R87 正是改取數層繞過 halt ⇒ 13 個 subagent 全滅、1,319,703 tokens
零產出（`DEF-200-107`）。守衛的訊息就是答案。

🔴 **解鎖條件訂正（R89 實打端點取得，推翻本輪稍早與 R88 交棒書的同一句指示）**：
R88 與 R89 第一版都寫著「需要掌舵者親自到 <https://claude.ai/settings/usage> 提額」。
**那是一件做不到的事**——當回合 `fetch_usage()` 的 `extra_usage` 區塊逐字：

```
monthly_limit: 500   used_credits: 610.0   currency: "USD"   utilization: 100.0
is_enabled: false    disabled_reason: "org_level_disabled_until"
user_disabled: false          ← 不是使用者自己關的
can_purchase_credits: false   ← 買不了
can_toggle: false             ← 設定頁那個開關對他是鎖住的
```

也就是**月上限 US$5.00、已用 US$6.10**，而池子由 org 層停用、使用者**沒有**開關權限。
⇒ 交棒書不得再把「請掌舵者去提額」寫成待辦：那會讓下一輪繼續等一件不會發生的事
（本 repo 反覆治的「散文假話」，只是這次假的是**一個指派給人的動作**）。

**真正可能的解除路徑**（皆非本 repo 能控制）：①`disabled_until` 字面暗示有期限，
但 payload **沒有給那個時間**，所以說不出是幾號；②官方支援管道（payload 自附連結
`https://support.claude.com/articles/12429409`）；③掌舵者換帳號（他已預告，
技術風險見 `DEF-200-114`）。

🔴 **原本寫在這裡的「一個未實測的關鍵推論」已於本輪末被實測推翻，故不留著當現行說法**
（QA 複審 B-4）。原文推論「subagent 用量計在付費池、不計在訂閱窗」，並據此推出
「在池子恢復前沒有任何辦法派 agent，與守衛怎麼寫無關」「`DEF-200-112` ② 面不是缺陷」。
**三句都是假的**，兩份獨立證據：

1. **探針**（`ca9985b` 的 message 逐字）：派 1 個 subagent **成功**（63027 tokens／4.6s）
   ⇒「保險池滿 ⇒ 一定派不出去」不恆真。
2. **落款**（`~/.autosdd/traces/quota_burn.jsonl` 第 5~8 列）：R87 那次事故中
   `five_hour` 在 11 分鐘內 **1.0 → 6.0 → 11.0 → 63.0**（Δ=62pp，與下方 §2 表的
   「Δpct 62」逐字吻合）⇒ 那 13 個 agent **真的燒掉 62pp 訂閱窗**才死，
   **subagent 用量確實計在訂閱窗**。

⇒ **R87 的死因至今未知**；`monthly spend limit` 是後果的字面，不是變因。
本輪據此拆掉了 `quota_policy.decide()` 裡那道以此推論為前提的 `cap=min(cap,1)` 地板
（三條理由與憲法面分析＝`docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`
〈R89 收尾：`cap=1` 地板拆除〉；帳本＝`DEF-200-119`）。

> 🔴 **帳號輪替不做進系統機制**：PRD §1.3 自己把「多帳號輪替或帳號池化以擴大額度」
> 列為非目標，§1.2 原則 7 是「合規優先」。掌舵者手動換帳號登入是他的帳號管理，
> 但本 repo 不建自動輪替。換帳號的**技術**風險已立案，見 `DEF-200-114`。

## 1. 本輪交付（皆附當回合實測）

| # | 項 | 憑證 |
|---|---|---|
| 1 | `DEF-200-112` 治本（①資訊面） | `--pace` rc=0，尾行新增期程句；hook 閂鎖後 stderr 同步 |
| 2 | 訂正 `DEF-200-112` 的**射程**（R88 散文比實際寬） | 見下 §2 |
| 3 | 立案 `DEF-200-114`（`plan_fingerprint` 宣稱的用途零實作<!-- absent-if: invalidate -->） | `grep` 實證：唯一消費端只印字串 |
| 4 | 護欄層**淨減法**（收尾窗口再減一次） | `--print-guard-lines` → `83670→83578 (-92)`、逐檔漂移 0 支 |
| 5 | ADR-XPLAT-002 §6 邊界 1 補 R89 列（SC-10） | `test_adr_xplat001_c1c2_lock.py` 138 passed |
| 6 | 立案 `DEF-200-115`（守衛可被受守衛者關閉：模型寫 `.claude/settings.json` 的 `env` 即可設 `AUTOSDD_QUOTA_GUARD_OFF=1`） | 讀 PRD §15.5 紅線 10 後實查，全 repo 無禁寫保護 |
| 7 | 3 處 pgvector `[DEBT]` 承接輪次 R89→R90（走測試指定的出口②，附推遲理由） | `test_conftest_windows_native_skip_report.py` 8 passed；ruff rc=0 |

🔴 **推進帳本時鐘到 R89 會連帶弄紅四類鎖，下一輪要有心理準備**（本輪逐一實測並修畢）：
①輪號超前鎖（程式碼註解寫 R89 > 帳本當前輪）②ADR §6 SC-10 缺當前輪覆蓋列
③AutoClaude `[DEBT]` 承接輪次被追平 ④交棒書「還沒做」宣稱必須附現查指令
（`TestR78HandoffClaimsCarryLiveCommands`）。①②④在根層、③在 AutoClaude 側。

<!-- guard-total:R89 --> **本輪護欄層累積淨額＝ 83670 → 83578（-92）** —— 前段包的新增
（`DEF-200-112` 回歸鎖、`FALLBACK_KINDS` 專屬鎖、款(12) 到期義務的新上限列）已由四段史料
搬遷等量抵銷（該段淨額 0）；收尾單人窗口再做一次史料搬遷（動因＝**分桶棘輪**，見 §6c）
把總量往下推到 `-92` `[收尾單人窗口當回合實測；憑證＝--print-guard-lines 印 (-92) 且逐檔漂移 0 支]`。

詳情面（複審者要逐條重驗就讀它）＝`docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`。

## 2. 最重要的一筆：R88 對 `DEF-200-112` 的描述過寬

R88 寫「halt 判準**不分**兩型」，並推出「續航哨兵結構上等不到 reset」。
**R89 實查，那一半是假的**：`reset_branch()` 早已分 `arm`／`notify`／`escalate`，
`quota_halt_actions()` 只在 `arm` 才呼叫 waker，`quota_halt_message()` 也早已印出
「沒有 reset 可以等…排程是錯的動作」。

真缺口只在**人機出口**：`--pace`（派工前查的那個）與 halt 閂鎖後每次工具都印的那則。
修法是**接電**既有的 `throttle_horizon_line()`，**不新增 band 值**
（`halt_wait`／`halt_human` 會是同一份知識的第二個家＝R73 判例）。

🔴 **教訓（差一步就犯）**：查證時我曾用**自己捏的** `act` dict 渲染 halt 訊息，
印出「本平台沒有排程載具」，看起來像 mac 上 launchd 失效的重大缺陷。
實查 `schedule_backend.select()` → `LaunchdBackend`，載具完好。
攔下這次誤報的是「驗證載具本身要被驗證」那條紀律。

## 3. 還沒做什麼（誠實劃界）

全部因 `band=halt` 而未執行，現查 `python tools/session_resume_planner.py --pace`：

- **四方複審（Architect／SA／SD／QA）** — 一次都沒跑，本輪所有結論皆為自證。
  <!-- absent-if: CrossPlatform_R89_Review --> 證偽標的就是上一行標記裡那個 pattern：
  四方複審一旦真的跑過，本 repo 既有體例會在 `docs/06_quality/` 產出對應的複審證據檔，
  屆時本行當場被打臉。🔴 **說明句刻意不逐字重複那個字面**——R89 第一版重複了它，
  於是鎖 grep 到的是我自己的說明文字，判定「宣稱為假」（自己命中自己）。
  現查「現在派不派得出去」：`python tools/session_resume_planner.py --pace`
  （`band=halt` 即結構上派不出任何 agent）
- PRD `AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` 只讀完 §1–§4.4（1574 行讀了 628 行），
  §15 執行方法論（動工前必讀）**未讀**
- 訴求 1／3（跨平台全掃、M5 雙向不落差實跑）
- 系統問題 1（skipped 殲滅）：R88 已分類（母體 73，`[WINDOWS-NATIVE-ONLY]` 36／
  `[ENV-DISABLED]` 13／`[DEBT]` 5／`[TOOL-ABSENCE]` 2），本輪**零殲滅**
- 系統問題 2（帳本降到 warn 線下）：未結 **88 → 89**（結 1〔`112`〕立 2〔`114`／`115`〕，
  淨 **+1**；warn 86、fail 98，距 fail 線 9 筆）。🔴 誠實說：這一輪帳本是**變差**的。
  兩筆新案都是真的（挖深挖出來的），但「降到 warn 線下」本輪**沒有進展**。
  現查：`python tools/check_defect_log_crossref.py --unresolved-count`
- 系統問題 3（Plugin 架構裁決）：本輪只給了**部分**答案（見 §4），未做架構裁決
- `DEF-200-114` 的修法（要動配速取數層，需第三方複審）
- Archive／Docker housekeeping／SDD Agents 精進

## 4. 對系統問題 3 的部分答案（「為何每輪都在瘦身」）

不是 Plugin 架構能解的。成因是**新增判準時沒有同步把等量史料搬出量測面**。

本輪示範：新增一道完整回歸鎖（含雙向注入自證），護欄層總量**零成長**。
收斂過程（三次實測）：3 個獨立測試 +38 → `subTest` 參數化 +24 →
搬走 `MacCredentialSourceTest` 的 25 行史料 +4 → 回收自己的註解 **+0**。

做法可重複：**判準留在測試檔，史料進輪次證據檔，兩者以檔名指針相連。**
`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS = 2` 就是逼這件事的機械物
（R87 +140、R88 +60 已連兩輪上升 ⇒ R89 必須 ≤0）。

## 4b. 本輪收官閘門實測（當回合，非引述）

```
python tools/run_root_unittests.py    → rc=0  Ran 3327 tests  OK (skipped=44)  0 FAIL
cd AutoClaude && python -m pytest tests/ -q
                                      → rc=0  4586 passed, 73 skipped in 104.49s
python tools/check_defect_log_crossref.py → rc=0（未結 89）
ruff check <本輪觸碰的 AutoClaude 檔>  → All checks passed!
```

🔴 **取證紀律附記（本輪自己踩到一次）**：第二次雙閘門的 AutoClaude 那半回 `rc=4`、
`no tests ran in 0.06s`——原因不是紅，是**我把 cwd 留在 repo 根**去跑 `pytest tests/`
（掃到的是根層 `tests/` 不是 AutoClaude 的）。`rc≠0` 這次剛好會叫，但**若根層恰好有
可收集的 `tests/`，它會靜默跑錯一批測試然後回 rc=0**＝假綠。上表的數字是用正確 cwd
重跑後取得的。同 `useMacWin.md` 記載的 cwd 跨呼叫持續問題（鐵律二的 POSIX 對應面）。

## 5. 下一輪第一件事

```bash
python tools/session_resume_planner.py --pace          # band 仍 halt 就還是單人輪
python tools/run_root_unittests.py                     # 根層全綠才動工
cd AutoClaude && python -m pytest tests/ -q            # 見 §6 的本輪基線
python tools/check_defect_log_crossref.py              # rc=0（R89 收輪實測）
python tools/check_defect_log_crossref.py --unresolved-count   # R89 收輪實測 91／warn 86／fail 98
```

額度解除後**第一件該做的事**：補跑本輪缺的四方複審（Architect／SA／SD／QA），
標的＝本輪 5 項交付 ＋ `CrossPlatform_R89_Closure_Evidence.md` 的每一條宣稱。

### 5a. 🔴 R90 開場定時炸彈：**先批次改派，再寫任何新列**

**動作順序是硬的**：R90 的第一個動作**不是**開新缺陷列，是把承接輪次寫 `R89` 的那批**批次改派**。

**為什麼**：帳本時鐘由「發現情境」欄**現查**推得。R89 收輪當下時鐘 `= R89`，那批列的
「承接輪次 R89」恰等於當前輪 ⇒ 硬規則② 判它合法，只發 **fail-open warning**。
**時鐘一推進到 R90（＝有人寫下第一列「發現情境 R90」的那一秒），這批列同時變成孤兒**，
`check_defect_log_crossref.py` 直接 **rc=1**，而觸發它的人是「只是想開一列新缺陷」的那個人。
同型事故已發生過一次並記在 `DEF-200-113`（R88 那次，當時 24 列）。

**當回合實測**（把 `current_round()` 釘成 90 後跑真判準 `orphan_backlog_problems()`）：

| 量 | 值 |
|---|---|
| 現行時鐘（`current_round()` 現查） | **R89**；`orphan_backlog_problems()` → **0** |
| 時鐘推到 R90 後的孤兒列 | **17 筆** ⇒ rc=1 |
| 孤兒 ID 逐筆 | `DEF-200-010`／`015`／`023`／`042`／`043`／`063`／`065`／`067`／`075`／`084`／`086`／`090`／`096`／`097`／`101`／`106`／`111` |

🔴 **另有 4 筆同樣寫 R89、卻不會轉紅（別漏了它們）**：`DEF-200-012`／`053`／`059`／`070`。
硬規則② 的出口是「承接輪次 ≥ 當前輪 **或**已載明改派」，而這 4 列的狀態欄都含「改派」二字
——其中 `053`／`059`／`070` 的「改派」講的是**別列**的承接輪次，不是自己的。⇒ 它們在 R90
一樣過期，只是**靜默**。批次改派時要把這 4 筆一併處理，不能只修會轉紅的那 17 筆。
（這條關鍵字出口本身是否該收緊，另案，本輪不處置。）

**現查指令**（改派前後各跑一次，貼 rc 與筆數）：

```bash
python tools/check_defect_log_crossref.py --unresolved-count   # 未結列數與逐筆 ID
python tools/check_defect_log_crossref.py                      # rc=0 才算改派完成
```

### 5b. 🔴 R90 首要單人窗口＝**帳本瘦身包**（持有面一次給齊，不得拆給並行包）

**這件事為什麼只能單人做**：它要動的常數／史料／消費端住在不同檔（鐵律七的原樣實例），
拆開後任何單包都只能回報 `not_done`——`DEF-200-049` 已經實證過一次。

**持有面（缺一即做不完，任務書必須一次列全）**：

| 檔 | 這一包要動它的什麼 |
|---|---|
| `docs/06_quality/AutoSDD_Defect_Log.md` | 被瘦身的列本身 |
| `docs/06_quality/CrossPlatform_R89_Closure_Evidence.md` | 原文逐字的落點（受 `_GOVERNANCE_DOCS` 體積守門） |
| `tools/lib/defect_ledger_index.py` | `OVERSIZE_ROW_GRANDFATHERED`／`OVERSIZE_ROW_CEILING`／`OVERSIZE_ROW_EXCESS_CEILING` |
| `tools/lib/ledger_rotation.py` | 上面兩條天花板的 `*_HISTORY`（末元素必須等於現值，否則方向鎖說「史料是裝飾品」） |
| `tools/check_defect_log_crossref.py` | `_UNPINNED_HANDOVER_GRANDFATHERED` 名單 |

**走既有判例、不要自創**：R82（13 列）與 R85（17 列）都跑完過整條出口＝**結案 ＋ 瘦身成索引，
原文逐字進具名證據檔**。`oversize_row_problems()` 的②向訊息會**當回合現算並印出**三個新值
（清單刪哪幾筆／兩條天花板各改成多少），照著貼即可，不要自己重算。

**一次解掉兩件事**：`DEF-200-053`（P1，open，**正是這個阻塞的既有立案**——天花板是相等斷言
⇒ 餘裕結構上恆為 0）＋ 存量。

**R89 收輪現況**：未結 **91** 列（warn 86／fail 98，**距 fail 線 7 筆**）——當回合實測，
量測入口＝`check_defect_log_crossref.py --unresolved-count`；另「已結列殘留待辦」**13 筆**
（**不帶旗標的完整執行**才會印那筆 warning 並逐筆列出 ID 與行號；`--unresolved-count` 只印
未結列，**不印**那 13 筆——SA N-E 訂正，本段先前寫「同一次輸出」不精確）。這 13 列因分類為
已結而結構上進不了承接稽核；「13 列全部驗過仍未修」一句為 **[收尾窗口回報]**，本包未獨立複驗。

🔴 **R89 放行條件收斂訂正（SA N-D）：本段先前寫「是本輪唯一的可寫面」＝高估阻塞。**
當回合實測（含本輪新增的 `DEF-200-125`）：未結 **92** 列中 **47 列已超標**、其餘 **45 列**
合計仍有 **2,203 B** 餘裕，其中 **7 列各 ≥100 B**（中位數 **22 B**）。放大到整張表更寬：
**202** 列中 **66** 列超標、其餘 **136** 列合計 **9,366 B** 餘裕、**35 列**各 ≥100 B（中位數 52.5 B）。
⇒「沒有地方可以寫字」是假的阻塞；真正緊的是**未結列數**（92／fail 98，距 **6** 筆）。
重跑（判準與量測入口都不要自己重寫）：

```bash
python tools/check_defect_log_crossref.py --unresolved-count   # 未結列數的唯一入口
python tools/check_defect_log_crossref.py                      # 13 筆殘留待辦只在這裡印
```

## 6. PRD §15 對照現況：一個**架構級**發現（交下一輪四方複審裁決）

本輪讀完 PRD §15（動工前必讀那一章）。**好消息**：§15.3「最小可行架構」與本 repo
現況高度重合，四項「真正必須自建」的模組本 repo 已有其三：

🔴 **R89 收尾訂正（SA 複審 N-2）：本表原寫「四項已有其三」＝過報。** 每個「部分」格
必須註明**缺哪一條 PRD 條文**，否則「已有」會被下一輪讀成「不必做」。

🔴 **R89 放行條件收斂二次訂正（SA 條件 4／QA B3）**：上一版此處寫「應為 1 已達／2 部分／
1 未有」，而相隔五行的表格四列實為 **0 已達／3 部分／1 未有**——**自我矛盾且零機械觀測者**。
本輪逐列拿 PRD 條文複核（不是為了對齊而改數字），結論是**表格對、散文錯**：
① 治理決策器——`grep -cE "hysteresis|遲滯|dwell|停留|slew|變化率|死區|EWMA" tools/lib/quota_policy.py`
當回合回 **0**，`DRAINING`／`LONG_HIBERNATE` 於整個 `tools/lib/*.py` 亦 **0** ⇒ §4.2.4／§3.2 全缺，
不是已達；② 長等待交棒——同上那次 `grep` 對 `LONG_HIBERNATE` 在 `tools/lib/*.py` 逐檔皆回
**0**（PRD `:188` 定義了它，實作面搜不到同名符號）⇒ 只覆蓋 5h 級；
③ 狀態持久化——`write_cache()` 實測是裸 `write_text`（非 tmp→fsync→rename）⇒ 不合 `:950`；
④ 帳號層級仲裁——未見。⇒ 計數改為 **0 已達／3 部分／1 未有**。
**此計數由下方表格現查，兩者不一致時以表格為準**（散文是量測值的複本，複本必過期）。

| PRD §15.2 必建模組 | 本 repo 現況 | 缺的 PRD 條文 |
|---|---|---|
| 治理決策器（配速 + 狀態機） | ⚠️ **部分** — `decide()` 是**無狀態的水位帶映射**；`grep hysteresis\|遲滯\|dwell\|停留\|slew\|變化率\|死區\|EWMA` 於 `quota_policy.py` **零命中** | §4.2.4（`:311-330`）五項平穩性機制（遲滯帶／死區／slew rate／最小停留／控制週期）全缺；§4.2.1（`:265`）`V_actual` 的 EWMA α=0.25 未實作；§3.2（`:179-193`）8 態狀態機未實作（無 `DRAINING` 單向鎖存、無 `LONG_HIBERNATE`）；§4.2.3（`:300-307`）四個致動器只有「併發 Agent 數」一個；🔴 **R89 放行條件收斂新增（SA N-B ＝ `DEF-200-125`）**：`:79`（§0.6 新發現 2）／`:1372`（第 7 條）／`:1529`（B-13）三處皆指定 **`status` 枚舉為權威狀態訊號、百分比僅作配速輸入**，而取數層**零讀取**（`grep -rhoE "allowed_warning\|rejected"` 於 `quota_meter.py`＋`quota_policy.py` **0 命中**；`bucket_readings()` 只取 kind／percent／resets_at／group）⇒ 本 repo 現行整條決策鏈建在 PRD 明說「可靠得多」的那個訊號**之外**。誠實劃界與 R90 的實測動作見該 DEF 列 |
| 跨 5h 視窗長等待與交棒 | ⚠️ **部分** — `session_resume_planner --arm-sentinel`（launchd／schtasks）只覆蓋 5h 級 | §3.2（`:188`）`LONG_HIBERNATE`（`U7d ≥ WEEKLY_HALT` ⇒ 週額度最長 7 天的交棒）未實作；mac 休眠邊界未覆蓋（見根 `CLAUDE.md`／SA-05：闔蓋期間 launchd 不會被喚醒，本專案刻意不碰 `pmset repeat`） |
| 治理層狀態持久化 | ⚠️ **部分** — 有額度快取 ＋ `quota_burn.jsonl` ＋ 任務書，但寫入方式不合規：實測 `quota_meter.write_cache()`（收尾當回合 `:596-607`，行號會漂移，現查 `grep -n "def write_cache" tools/lib/quota_meter.py`）是直接 `write_text` | `:950` `STATE_WRITE_MODE=ATOMIC`（tmp → fsync → rename）未實作 ⇒ **非原子**；`:951` `STATE_RETAIN_VERSIONS=5` 未實作 ⇒ 無版本保留；§7 要求的 checksum 未實作 |
| 帳號層級配額仲裁 | ❌ 未見（`fanout_ledger` 是本機 session 面，非跨專案帳號面） | §15.4 P4（`:1357`）「帳號層級仲裁鎖」 |

§15.3 的「PreToolUse 在 `Agent` 工具層攔截」正是 `context_budget_guard.py` 在做的事
⇒ PRD 稱之為「本次核實帶來最大的簡化」，本 repo 已經走在這條路上。

🔴 **PRD 有一條紅線在本專案不成立——已實測，不是推論**：

> §15.5 紅線 1 逐字：「**不要碰未公開的 HTTP 端點。** statusLine 已提供你需要的一切，
> 而且是官方支援的路徑。原 PRD 的 T5 方案現在既無必要也有風險。」
> §0.6 第一列同義：遙測引擎「**採用** statusLine，原 T5 整條刪除」。

`quota_meter.fetch_usage()` 打的正是 `/api/oauth/usage`＝PRD 的 **T5**。
本輪原本把它記成「repo 違反紅線 1，待架構師裁決」——**那個方向錯了**，實測見下。

**當回合實測**（`claude --version` 2.1.226；探針與對照組都在 scratchpad，
逐字與方法見 `CrossPlatform_R89_Closure_Evidence.md` §statusLine 實測）：

| 遙測管道 | headless（`claude -p`）會發生？ | payload 含 `rate_limits`？ |
|---|---|---|
| statusLine | ❌ **一次都沒被呼叫** | 無從得知（根本沒跑） |
| hook（SessionStart） | ✅ 會跑 | ❌ **不含**（只有 `session_id`／`transcript_path`／`cwd`／`hook_event_name`／`source`） |
| `/api/oauth/usage`（T5） | ✅ | ✅ ← repo 現行在用 |

**載具因素已排除**：同一份 `--settings` 檔同時掛 statusLine 與 SessionStart hook，
一次 `claude -p` 之後 `hook_fired=YES`／`statusline_fired=NO` ⇒ 不是 `--settings` 沒生效，
是**非互動模式沒有狀態列可畫，所以不呼叫 statusLine**。

⇒ **結論：對 AutoClaude 的主要使用情境（headless Playbook 執行、續航哨兵 tick），
PRD §0.6 第一列與紅線 1 的前提不成立；repo 走 T5 不是違規，是唯一可行的路。**
這同時解釋了 `core/ports/quota_meter.py` docstring 自陳的那個洞
（「額度軸會在無人看管那一跑上安靜地不存在」）為什麼**不能**用 statusLine 補。

**給下一輪的真題目**（原題目作廢）：headless 情境的刷新者只能是「自己去打 T5」，
那麼 ①誰來打（AutoClaude 不得 import harness ⇒ 要嘛引擎自己有一份取數器、要嘛
由外部排程器打完寫檔案契約）？②T5 失效時的降級路徑是什麼（PRD 對「內部介面」
的要求逐字是「必須有降級路徑，不可硬依賴」）？

其餘值得下一輪查的紅線：**紅線 10**（`.autoclaude/`、`.claude/settings*.json` 應列為
Agent 禁寫，否則「幫我把併發調高」就能拆掉整套治理）——本輪未查本 repo 有無此保護。

## 6a. 🔴 治理規則（掌舵者 2026-08-14 立，優先於本檔其餘一切）

1. **PRD `AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` 是最高憲法基準**，以後全部以它為準。
2. **修憲程序**（原話逐字）：「若有 PRD 憲法有爭議，提出討論，經過 Architect／SA／SD／QA
   **都同意**，則改規格書」——**不是**任何人（含我）單方判定某條作廢。
   四方**全部**同意才動 PRD；未達成前，PRD 原文有效。

🔴 **必須分清楚的兩種情形，處置完全不同**：

| 情形 | 處置 | 本輪實例 |
|---|---|---|
| **實作沒照 PRD 做** | 修**實作**，PRD 一個字都不動 | `extra_usage` 被當節流軸（見 §6b） |
| **PRD 本身與實測不符** | 走**修憲程序**：提案 → 四方全同意 → 才改 PRD | statusLine 紅線 1（見 §6，**現降級為待審提案**） |

⚠️ 本輪 §6 與 `CrossPlatform_R89_Closure_Evidence.md` 對 statusLine 的措辭寫成
「前提不成立」，語氣像已定案——依本規則那是**越權**。實測數據有效，但**結論待四方裁決**；
在四方同意之前，PRD §0.6 第一列與 §15.5 紅線 1 **仍然有效**。

## 6b. 🔴 實作違憲：`extra_usage`／`spend` 不得作為獨立節流軸（R89 末，掌舵者指令）

**掌舵者 2026-08-14 指令逐字**：「請去熟讀 `AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md`
規格書的設計，**以後全部以這個文件做最高憲法基準**！」
以及對本輪守衛行為的判決逐字：「**付費額度是一個保險，你把它當成主要，本末倒置！**」
「我有 100% 的訂閱額度不用，要我去開付費？」

### 憲法條文（PRD 原文，四條同向）

| 出處 | 逐字 |
|---|---|
| §0.6 新發現 1 | 「這代表達到訂閱限制**後**可能可以付費續跑」 |
| §6 第 4b 節 | `OVERAGE_POLICY=FREEZE`（預設，**絕不動用超額**）｜`ALLOW_WITH_CAP` |
| §15.5 紅線 2 | 「超額用量必須是顯式的 opt-in。預設 `OVERAGE_POLICY=FREEZE`」 |
| §15.1 前置檢查 3 | 風險是「**不會停止而會開始計費**…默默產生帳單。**這是本專案最危險的單一失敗模式**」 |

### 判決

PRD 的預設政策是**絕不動用** `extra_usage`。既然系統本來就不打算用它，
**它的水位對「訂閱窗還有餘裕時能不能派工」完全無關**。

現行 `quota_policy.decide()` 對所有軸一視同仁取 `min(cap)`
⇒ 把「保險」與「主力」放在同一平面比大小 ⇒ 保險用完即一票否決主力。
這**同時**違反兩件事：
① 把「絕不動用的東西」當成「決定能不能動的東西」（掌舵者原話：本末倒置）；
② **風險方向做反了**——PRD 怕的是它被偷偷用掉而產生帳單，守衛做成它沒得用所以停工。

🔴 **這不是「模型判斷推翻機械守衛」（`DEF-200-107` 禁止的那件事）**：那次是舵手憑判讀
改取數層；這次是**規格文件判定實作有誤**，規格 > 實作。但仍**不得**在無第三方複審時動手。

### 建議修法（依 PRD 設計，非我自創）

1. 引入 `OVERAGE_POLICY`（`FREEZE` 預設／`ALLOW_WITH_CAP`＋`OVERAGE_HARD_CAP_USD` 必填，
   見 PRD §6 4b 與 §6.1 啟動不變式 7b）。
2. `FREEZE` 時：`extra_usage`／`spend` **不進 cap 聚合**（系統不打算用它）。
3. 但**必須告警**：PRD §6 `OVERAGE_ALERT_ON_FIRST_USE=true`「一旦偵測到 overage 類額度
   被動用即告警」——那才是 PRD 要防的方向（靜默計費）。
   🔴 **R89 收尾實況：這一條至今零實作**，已立案 `DEF-200-118`（P1，承接 R90）。
   <!-- absent-if: overage_alert -->（證偽標的＝實作面一旦長出這個符號，本句當場為假）
   誠實措辭：改動前的行為**不是**靜默計費的保護（它在 100%＝錢已花完之後才反應）；
   本輪做的是「移除保險軸在 halt 帶的唯一反應」，而 PRD 指定的替代（首次動用告警）
   **從未存在**。
4. 訂閱窗（`five_hour`／`seven_day`／`session`／`weekly_all`）維持現行判準不放寬。
5. 🔴 **R89 收尾補**：`FALLBACK_KINDS` 同時補齊 PRD `:78` 明列的 `overage`／
   `seven_day_overage_included`（取數層原樣帶出 kind ⇒ 漏列即本病復發），
   三家鏡射鎖由 `==` 改子集判準。見 `DEF-200-120` 與 R89 收尾證據檔。

### ~~未決的實然問題~~ → **已實測，本節作廢**（R89 收尾／QA 複審 B-4）

原文計畫一次「派一個最小 agent」的探針，以驗證「subagent 用量是否計在付費池」。
**那次探針已經跑過**（`ca9985b` 的 message 逐字：派 1 個 subagent 成功，
63027 tokens／4.6s）**且結果是推翻該推論**；同輪的落款證據（`five_hour` 11 分鐘內
1.0→63.0）更直接證明 subagent 用量**計在訂閱窗**。⇒ 本節不再是待辦，
下一輪**不要**再排這個探針。R87 的死因仍未知，見上方 §0 的訂正段與 `DEF-200-119`。

## 6c. 護欄層現值（重釘後）

<!-- guard-total:R89 --> **83670 → 83578（-92）** —— 護欄層累積總量現值。
款(12) 的到期義務同輪兌現：單輪淨額上限追加更小的一段、下一段目標與到期輪一併重新武裝
（推導與逐輪步伐＝`docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`）。

🔴 **收尾窗口那 `-92` 是被一個假訊號逼出來的，下一輪要知道**：分桶棘輪的 `prose` 桶報
`4119 → 4276（+157）`，逐檔歸因後 **+157 全部來自 chunk 粒度的重新歸類**，不是散文成長
——三塊在 HEAD 為 `selfcontained`，因搬遷體例留下的一行 `docs/` 指標而整塊改記入 `prose`，
三塊的**行數合計只 +6**。處置未動任何門檻、未重釘桶基準（照棘輪自己列的第三條出口做）。
量測、逐筆歸因、以及「下一輪的判斷題」逐字＝
`docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`〈分桶棘輪：+157 全部來自重新歸類〉。

🔴 **本現象已於 R89 收輪立案＝`DEF-200-124`（P2，open，承接輪次 R90）**，含反向的
**−74**／**−69** 假減法與「為壓回綠刪 110 行史料」的代價。候選處置（**未實作，需四方複審**）＝
把「指標行單獨形成的 prose 歸屬」比照 `reference_counts()` 對 `self_name` 的既有先例。

## 6d. 🔴 舵手裁決存查：三列凍結歷史版缺陷轉 `closed-by-decision`（R89 已裁，R90 執行）

**為什麼裁決文住在這裡而不是帳本**：三列都寫不下——但**兩列是兩種不同的擋法，別當成同一件事**
（當回合逐列實測 `row_bytes()`，`ROW_MAX_BYTES=700`）：

| 列 | 現行 bytes | 擋法 |
|---|---|---|
| `DEF-101-388` | **2967**（在 `OVERSIZE_ROW_GRANDFATHERED` 內） | `OVERSIZE_ROW_EXCESS_CEILING` 是**相等**斷言、餘裕結構上恆 **0** ⇒ 追加任何一個位元組即紅（`DEF-200-053`／`DEF-200-049` 的原樣重演） |
| `DEF-101-936` | **691**（未超標、不在豁免清單） | 餘裕只剩 **9 bytes** ⇒ 補理由句即越過 700，且它**不在**豁免清單 ⇒ 變成一筆**新**超標列（比追加在既有豁免列更嚴重：那是 ①向違規） |
| `DEF-101-917` | **680**（同上） | 餘裕 **20 bytes**，同 936 |

⇒ 936／917 的改寫必須**淨額不增**（狀態首詞 `open（承接輪次：**R81**）` 換成
`closed-by-decision` 本身會縮，但補上理由與指針就吃光那 9／20 bytes）。
**裁決先落在本節存查，待 §5b 的帳本瘦身包騰出 byte 預算後再執行到帳本上。**

**裁決**：`DEF-101-388`／`DEF-101-917`／`DEF-101-936` 三列——**凍結歷史版不予 Copy-on-Evolve
例外，轉 `closed-by-decision`**。

**理由（逐字，不要改寫成別的意思）**：根 `CLAUDE.md` 明文「**ci-gate 只測凍結基線 + LATEST
兩軌，改中間版無人看得到**」⇒ 對**中間歷史版**（凍結基線與 LATEST 之間各版；逐列的確切版本
區間見各列本文，本節刻意不複寫版號——LATEST 一律現查 `python AISDLC_SDD/scripts/sdd_version.py`）
**改了也沒有任何機械物會驗證**，只是製造「已修」的假象。
而這幾列的缺陷已從「未修的洞」轉為「**受監視的欠債**」。

**監視憑證（當回合逐筆實查，不是引述）**：

| 列 | 監視它的常數 | 座標 | 判準形態 |
|---|---|---|---|
| `DEF-101-936` | `_SELF_HELP_DEBT_FROZEN = 116` | `tools/lib/self_help_exec_parity.py:49`（比對在 `:130`） | 雙向精確比對（多一筆＝新增同型缺陷，少一筆＝有人動了凍結版） |
| `DEF-101-917` | `_BARE_SH_DOC_DEBT_FROZEN = 87` | `tools/tests/test_platform_neutral_paths.py:4086` | 同上 |
| `DEF-101-388` | **無常數**（誠實劃界，見下） | — | — |

🔴 **`DEF-101-388` 不適用「已有雙向常數在守」這句話——它的正當性走的是另一條路**：該列的
分流欄本來就是「**不修復程式碼**（凍結版依既有紀律不回改，比照 `DEF-101-359`／`DEF-101-382`
判例）」，射程只有 `SDD_FW_VERSION=<v0.05~v0.29>` 這個 debug／二分定位用的手動路徑，
**預設雙軌閘門（凍結基線 v0.01 ＋ 動態解析 LATEST）完全不受影響**（P3）。⇒ 轉
`closed-by-decision` 是把一個 R47 就已定案的 known-gap 從「永遠掛著的 open」改成如實分類，
不是新開授權。**但它沒有數字在守**，所以「三列都有常數」那個說法為假，不要沿用。

### 不適用同一裁決、**維持 open** 的兩列（不可一句話掃掉）

| 列 | 為什麼形狀不同 |
|---|---|
| `DEF-101-336` | 它要的是「**為凍結版新增禁止 commit 的機械鎖**」＝**新工作**，不是例外授權。上面那條「改了沒人看得到」的理由對它不成立——鎖是要防止有人去改，不是去改 |
| `DEF-101-338` | 測試污染物（四支假 SHA 檔）被**誤 commit** ⇒ 正解是**刪檔**，不是原地改框架資產；Copy-on-Evolve 管的是「改」，刪除誤入的污染物不在它射程內 |

**R90 執行清單**：① 先做 §5b 的帳本瘦身包騰出 byte 預算；② 三列狀態欄改
`closed-by-decision`，理由欄以一句話 ＋ 指針指回本節；③ 三列離開未結集合後，
`--unresolved-count` 應降 3（改完現查，不要推算）。

### 6c. R89 放行條件收斂窗口交下來的四筆（皆**非阻塞**，只登記不處置）

| # | 內容 | 現查／複驗指令 |
|---|---|---|
| 1 | **`DEF-200-125`（新立案，P2，承接 R90）**：PRD `:79`／`:1372`／`:1529` 指定 `status` 枚舉為權威狀態訊號，取數層零讀取。R90 的動作是**取樣一次原始 payload**判定 `limits[]` 逐項有無該欄位——本機快取答不出來（`schema_keys` 只留 17 個**頂層**鍵、且取數層丟棄未知欄位） | `grep -rhoE "allowed_warning\|rejected" tools/lib/quota_meter.py tools/lib/quota_policy.py`（今日 0 命中） |
| 2 | **`DEF-200-123` 的假紅普查數字是量測值，不是常數**（SA N-C／QA NEW-3，已在證據檔就地訂正）：母體是**自指的**（每輪自己的逐字稿會進下一次普查），本窗口複量為母體 1,047 支／命中 6／真陽 3 ⇒ 精確率 50%；新增的假陽性全是「複述工具計數」形態 | `python tools/probe/causal_form_census.py --shape g` |
| 3 | **`DEF-200-124` 的 `−74`／`−69` 需重新評級**（SA N-F／QA NEW-4）：兩數今日複現為別的值、且 `−69` 在證據檔中**無出處**；QA 另實測該棘輪「只咬得住誠實者」（同 chunk 多打一個 token 讓它變 `mixed` ⇒ 真實 +183 行守備讀數反而是負值且全綠）⇒ **P2 可能低估**。🔴 本窗口**未獨立複驗**這三個數字，屬 **[他包回報]** | 見該 DEF 列與證據檔〈分桶棘輪〉節 |
| 4 | **HEAD 的逐檔守備基線本來就有 4 支漂移**（QA NEW-5，`+35`／`+20`／`−53`／`−2`，總和恰為 0）⇒ 淨額誠實、**逐檔面曾失準而無人發現**。本窗口實測現況為 **淨額 83578→83578 (+0)、逐檔漂移 0 支**（漂移已在 R89 收尾重釘時消掉）；留給 R90 的題目是**為什麼逐檔面可以漂而總量不動**，不是再修一次數字 | `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines \| head -2` |

## 7. 禁止事項

- 不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`
- 不准設 `AUTOSDD_QUOTA_GUARD_OFF`／改 `quota_meter.bucket_readings()` 之類的手法繞過 halt
  （`DEF-200-107` 的原樣重演）。🔴 **R89 放行條件收斂訂正（QA C2）**：本條與上表第 6 列、
  以及帳本 `DEF-200-115` 那一列，原先寫的都是把 `GUARD_` 那一段漏掉的變數名——repo 內
  **不存在**那個名字（唯一逃生口就是本行寫的這一個，現查：
  `grep -rn AUTOSDD_QUOTA_GUARD_OFF tools/ .claude/`）。**錯名不逐字寫回這裡**，
  寫回去就是新的幽靈符號。兩個後果各自成立：① R90 照舊配方去設那個不存在的變數、
  看守衛照樣攔，會把 `DEF-200-115` 誤判成「不可重現」而錯結一列 P1；② 這條禁令的
  **字面**沒有涵蓋真正的逃生口——那正是鐵律五「禁令沒涵蓋到的那個動詞就是被踩的那個」原樣
- 不准把 `DEF-200-112`／`114` 的 ID 補進 `OVERSIZE_ROW_GRANDFATHERED` 讓帳本體積道轉綠
- 不准在無第三方複審的輪次改配速**取數層**（`record_burn`／`burn_ratio`／`bucket_readings`）
