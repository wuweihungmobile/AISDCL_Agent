# CrossPlatform R89 — 結案／立案詳情面

> 本檔是 `AutoSDD_Defect_Log.md` 兩列的**詳情面**（帳本列只留一句話與指針，
> 體例同 `CrossPlatform_R88_Closure_Evidence.md`）。複審者要逐條重驗就得讀完它。
>
> 🔴 **本輪為單人輪，無第三方複審**：額度處於 `band=halt`（`binding=extra_usage`，
> 帳號月度支出上限 `used 610 / limit 500` 且 `org_level_disabled_until`）
> ⇒ PreToolUse 守衛結構上擋下所有扇出，四方複審**一次都沒跑**。
> 下方所有結論皆為自證，重啟後第一件事是重驗（同〈可重啟點四條件〉第 4 條）。

---

## DEF-200-112 — halt 的兩型在人機出口上分不出來（fixed@R89，①資訊面）

### R88 版描述的射程過寬（訂正，不逐字保留原文）

R88 立案時寫的是「halt 判準**不分**『有 reset 可以等』與『沒有 reset 只能等人』」，
並據此推出兩個後果：①續航哨兵結構上等不到 reset；②月度週期內派不出任何 agent。

**R89 當回合實查，①那一半是假的**：

| 既有機制 | 現查結果 |
|---|---|
| `quota_messages.reset_branch()` | **早已**分出 `arm`／`notify`／`escalate` 三支；`resets_at` 解不出來即回 `escalate` |
| `quota_gate.quota_halt_actions()` | `arm = waker(...) if branch == QUOTA_BRANCH_ARM else {}` ⇒ escalate **不呼叫 waker** |
| `quota_messages.quota_halt_message()` | escalate 分支逐字印「這一條**沒有 reset 可以等**（例：月度支出上限）；只有人去提額：<usage url> ⇒ 排程是錯的動作，只有人去提額才會回來。」 |

⇒ 「續航哨兵空等一個不會來的 reset」**結構上不會發生**。照 R88 描述動手的人，
會去補一個已經存在的機制（同 R80「低報分子」判例：低報與過報一樣貴）。

🔴 **查證過程本身有一個要記下來的教訓**：第一次渲染 halt 訊息時，我傳的 `act` dict 是
**自己捏的**（`posix=True, armed=False`），於是印出「本平台沒有排程載具（…本平台兩者
皆無）」，看起來像是 mac 上 launchd 偵測失效的重大缺陷。實查
`schedule_backend.select()` → `LaunchdBackend`，載具完好；escalate 分支的真實 `act`
是 `posix=False, armed=False`（waker 根本沒被呼叫）。**把自造輸入當成系統缺陷回報**
差一步就發生，攔下它的是「驗證載具本身要被驗證」那條紀律。

### 真缺口：只在兩個人機出口

| 出口 | R89 前 | 誰會看到 |
|---|---|---|
| `quota_halt_message()` | ✅ 已分兩型 | 撞線那一刻，**一個 reset 視窗只印一次**（早就捲出畫面） |
| `--pace`（`quota_gate.pace_report()`） | ❌ 只印 `reset 距離不明` | **舵手派工前查的那一個** |
| halt 閂鎖後的簡短訊息 | ❌ 同上 | 撞線期間**每一次** Read／Bash 都印＝人唯一持續看得到的那則 |

也就是「等 20 分鐘就好」與「只能等人去提額」在人真正會看的兩個地方逐字相同。

### 處置：接電，不新造

**刻意不新增 `halt_wait`／`halt_human` 兩個 band 值**（掌舵者原授權的形狀）：
那個語意 `reset_branch()` 的三分支已經承載，再造一份就是 R73 `Find-GitBash`
同型的「同一份知識住兩個家、只有一個家會被改」。改動只有兩處，各補一次
既有的 `throttle_horizon_line()`：

- `tools/lib/quota_gate.py` `pace_report()` 的 return
- 同檔 halt 閂鎖 `else` 分支的 stderr

🔴 **free 帶刻意不印**（`horizon = "" if decision.cap is None else …`）：
`throttle_horizon_line()` 逐字說「這道**節流**…」，而 free 帶沒有任何節流；
free 帶的 binding 常是 reset 不明的零消耗軸（實測 `nimbus_quill`）⇒ 無條件接
就會對一個根本不存在的節流宣告「它不會自己解除」。本 repo 判例：
**訊息裡混一句假話，比少一欄更難看見**。

### 當回合實測（非宣稱）

改動後 `python tools/session_resume_planner.py --pace` → **rc=0**，尾行新增：

```
⏳ 這一條**沒有 reset 可以等**（例：月度支出上限）；只有人去提額：
   https://claude.ai/settings/usage ⇒ 這道節流不會自己解除。
```

同一行也出現在 hook 的閂鎖後 stderr（見本輪任一 tool_result 的 PostToolUse 回饋）。

> 🔴 **R89 收尾訂正（QA 複審 B-4，本節不刪原文、只標註其效期）**：上面那段輸出是
> `fixed@R89` 的**唯一憑證**，而它在 HEAD **已不可重現**——同輪後續的憲法裁決把
> `extra_usage`／`spend` 移出 cap 聚合，於是在**當時那個姿態下**產生該尾行的那條路
> （binding 落在無 reset 的保險軸）結構上到不了了。**這不表示接電被拆掉**：接電
> （`throttle_horizon_line()` 掛進 `--pace`）仍在，判準仍由
> `QuotaPaceOutletIsReachableTest` 守著，只是**這一格的觸發者換成訂閱側的無期程軸**
> （live 快取實測 `weekly_scoped`／`nimbus_quill` 皆 `resets_at=null`）。
> 誠實劃界：憑證與被證的事在同一輪內被自己的另一個 commit 作廢，是本 repo 反覆踩的
> 「同一輪內文件比程式晚一步」形態；現行可重現的憑證改由該測試檔的 4 個 subTest 承擔
> （現查 `python -m pytest tools/tests/test_context_budget_guard.py -k pace_outlet -q`）。

### 鎖與**雙向**合成注入自證

`tools/tests/test_context_budget_guard.py::QuotaPaceOutletIsReachableTest` 新增 3 測。
兩個方向的注入各實跑一次：

> 🔴 **R89 收尾訂正（QA 複審 N-4）**：本節原句逐字寫「綠端：`9 passed`（含既有 6 測）」。
> 那個數字**在任何一次執行輸出裡都不存在**——該類是 `subTest` 參數化的，實跑印的是
> `1 passed, N subtests passed`。R89 收尾當回合實測（新增第 4 個 subTest 之後）：
> `1 passed, 357 deselected, 4 subtests passed`。⇒ 原句是把「我心裡算的測項數」寫成
> 「執行器印的數」，正是 `.claude/hooks/check_claim_provenance.py` 那道守衛在找的形態
> （值域對不上任何一次 `tool_result`）。

| 注入 | 改法 | 實測 |
|---|---|---|
| RED-INJECT-1（拆掉接電＝退回 R88 前） | `horizon = ""` | **2 failed**（兩條 halt 鎖）／free 帶那條仍綠（正確：沒接電就沒有假話） |
| RED-INJECT-2（無條件接電） | `horizon = throttle_horizon_line(...)` | **1 failed**（free 帶假話防線）／另兩條綠 |

⇒ 三條鎖各自有牙，且**兩個相反方向的錯誤都抓得到**。注入後已還原。

### ②cap 面：非缺陷，是裁決

「月度週期內派不出任何 agent，而訂閱窗只用 21%」**刻意不動**。掌舵者本輪裁決的
形狀逐字是「cap 兩者皆 0、只加分類資訊、**不放寬任何一軸**」。其解除條件不在程式裡
——只有人去 <https://claude.ai/settings/usage> 提額。放寬它就是 `DEF-200-107`
（R87：13 個 subagent 全滅、1,319,703 tokens 零產出）的重演。

> 🔴 **R89 收尾訂正（QA 複審 B-4，本節原文已為假，故不再是現行說法）**：上面整節寫於
> 本輪**前段**，而同輪稍後掌舵者下了**方向相反**的裁決（逐字：「付費額度是一個保險，
> 你把它當成主要，本末倒置！」「我有 100% 的訂閱額度不用，要我去開付費？」），落地
> commit `ca9985b` 正是把該姿態由 `cap=0／band=halt` **放寬到** `cap=1／band=notice`
> ——也就是本節逐字宣稱「不放寬任何一軸」「放寬它就是 `DEF-200-107` 重演」的那件事，
> 由**同一輪的下一個 commit** 做掉了。QA 以 `git log -L` 實證本節自 `18dee83` 起未被
> 動過 ⇒ 它不是「後來才過期」，是**寫下它的那一輪就自己推翻了它而沒有人回來改**。
> 現行說法（三段，彼此不衝突）：
> ① **保險軸不進 cap 聚合**＝憲法要求（PRD §6 4b `OVERAGE_POLICY=FREEZE`＋§15.5 紅線 2
>    ＋§0.6 新發現 1），不是放寬也不是 `DEF-200-107` 重演——後者是在**取數層**丟掉軸，
>    這裡兩軸照樣被量到、照樣進 `per_axis`／`--pace`／`describe()`，只是不進 cap 聚合。
> ② `ca9985b` 同時裝上的那道 `cap = min(cap, 1)` 地板，已於 R89 收尾**拆除**（見下方
>    〈R89 收尾：`cap=1` 地板拆除〉節的三條理由）。
> ③ 「只有人去提額」這句在本輪稍後也被實測推翻：`can_toggle:false`／
>    `can_purchase_credits:false`／`user_disabled:false` ⇒ 掌舵者**沒有**那個開關
>    （見 `R89_HANDOFF.md` §0 的解鎖條件訂正）。

---

## DEF-200-114 — `plan_fingerprint` 宣稱的用途一行都沒實作（open，承接 R90）

### 立案觸發

掌舵者本輪預告「這個帳號還是有限，用完我還會開下一個帳號給你用」
⇒ 查證「換帳號後額度快取會不會沿用舊帳號的讀數」。

### 現查

`quota_meter.account_posture()` 的 docstring 逐字宣稱：

> `plan_fingerprint` … 它的用途是**偵測方案變更**（組合變了 ⇒ 歷史標定／燃燒率作廢重學）

而那件事**一行都沒有實作**：

```
grep -rn "plan_fingerprint" tools AutoClaude .claude
  → 唯一的 production 消費端是 quota_gate.py:621 posture_line()（拿去印字串）
grep -rn "作廢|invalidate|重學" tools/lib/quota_pace.py tools/lib/quota_gate.py
  → 零命中
```

⇒ 宣稱的**用途**沒接電。同 `DEF-200-111` 散文假話族，只是這次假的是用途不是事實；
危害相同：下一個人讀到它會以為換方案時歷史會自己作廢，於是**不會去建那道機制**。

### 實際後果（與換帳號直接相關）

`quota_burn.jsonl` 的去重鍵只有 `measured_at`（`quota_gate.record_burn()`）
⇒ 換帳號／換方案後新舊樣本混在同一份落款，`burn_ratio()` 會拿 A 帳號的燃燒特性
去算 B 帳號的攤提配額。

**兩條時間軸不同，這是關鍵**：

| 面 | 自癒？ |
|---|---|
| 額度快取（`autosdd_quota.json`） | ✅ `QUOTA_CACHE_TTL_SECONDS = 180` ⇒ 最多 3 分鐘誤判 |
| 燃燒率落款（`quota_burn.jsonl`） | ❌ **持久**（`endurance_env.trace_dir()`）⇒ 不會自癒 |

### 本輪處置：只訂正假 docstring，刻意不修

修法要動 `record_burn`／`burn_ratio` ＝ **配速取數層**，而 `DEF-200-107` 的教訓
逐字是「不得以模型判斷改取數層」，需第三方複審——本輪額度 halt、結構上沒有第三方。
與 R88 對 `DEF-200-112` 下的判決同型，只是這次有本輪的具體證據支持。

### 誠實劃界（不要把這條讀成全集）

指紋只分得出**方案**變更。同方案的兩個帳號指紋**逐字相同**
（實測本帳號＝`extra_usage+five_hour+nimbus_quill+session+seven_day+spend+weekly_all`）
⇒ **Pro → Pro 換帳號這一型，靠指紋結構上抓不到**。要抓需要帳號識別
（token 雜湊之類），涉及憑證處理，屬 PRD §12 安全性射程，另案。

### 建議形狀（給 R90，非承諾）

落款列帶 fingerprint、`burn_ratio()` 只採同指紋樣本 ⇒ 治「方案變更」那一半；
「同方案換帳號」那一半誠實登記為已知邊界。判準本身要有雙向注入自證。

---

## statusLine 實測：PRD §0.6／§15.5 紅線 1 的前提在本專案不成立

### 為什麼要測

PRD 把「遙測引擎」整條的建議定成**採用 statusLine、刪除 T5（未公開 HTTP 端點）**
（§0.6 第一列＋§15.5 紅線 1 逐字：「statusLine 已提供你需要的一切」）。
而 `quota_meter.fetch_usage()` 打的正是 T5 ⇒ 照 PRD 字面讀，repo 現況是違規的。

**但 PRD 自己要求**（§前言逐字）：「核實來源是實作內部字串，不是官方文件承諾的公開介面
…凡標示內部者，實作時必須有降級路徑，不可硬依賴。」⇒ 先實測，不照抄。

### 方法（探針與對照組都不碰使用者環境）

`claude --version` = **2.1.226**。用 `--settings <file>` 掛臨時設定（scratchpad 內），
statusLine 指向一支「把 stdin 原封不動落地 + 印固定字串」的探針。
**對照組是關鍵**：同一份 settings 內同時掛一個 SessionStart hook（同樣落地 stdin）
——用來分辨「statusLine 沒被呼叫」與「`--settings` 根本沒生效」。

### 結果（當回合，rc 與檔案存在性皆為實測）

```
claude -p --settings <probe> --model haiku "reply ok"   → rc=0
hook_fired:       YES     ← --settings 確實生效
statusline_fired: NO      ← 同一份 settings 下 statusLine 一次都沒跑
```

SessionStart hook 的 payload 逐字只有五個鍵：
`session_id` / `transcript_path` / `cwd` / `hook_event_name` / `source`
⇒ **`rate_limits` 不在裡面**（`'rate_limits' in payload` → `False`）。

| 遙測管道 | headless（`claude -p`）會發生？ | payload 含 `rate_limits`？ |
|---|---|---|
| statusLine | ❌ 一次都沒被呼叫 | 無從得知（根本沒跑） |
| hook（SessionStart） | ✅ 會跑 | ❌ 不含 |
| `/api/oauth/usage`（PRD 的 T5） | ✅ | ✅ ← repo 現行在用 |

### 結論

**對 AutoClaude 的主要使用情境（headless Playbook 執行、續航哨兵 tick），
PRD §0.6 第一列與紅線 1 的前提不成立。** 非互動模式沒有狀態列可畫 ⇒ 不呼叫 statusLine；
而 hook 這條通得了的路，payload 裡沒有額度資料。**repo 走 T5 不是違規，是唯一可行的路。**

這同時解釋了 `autoclaude/core/ports/quota_meter.py` docstring 自陳的那個洞
（逐字：「額度軸會在無人看管那一跑上安靜地不存在」）**為什麼不能用 statusLine 補**。

🔴 **本節同時是一次自我訂正**：R89 稍早把這件事記成「repo 違反紅線 1，待架構師裁決」，
並寫進了交棒書。那個方向是**照 PRD 字面推論**得來的，實測後為假，已就地訂正。
判例同型於本輪 `DEF-200-112`：**照散文動手之前先問「這句話今天還是真的嗎」。**

### 給下一輪的真題目（原題目作廢）

headless 情境的刷新者只能是「自己去打 T5」，於是：
①**誰來打**？（`.importlinter` 的 `no-harness-import` 禁止 `autoclaude` import harness
⇒ 要嘛引擎自己有一份取數器，要嘛由外部排程器打完寫檔案契約 `autosdd_pace.json`）
②**T5 失效時的降級路徑是什麼**？（PRD 對內部介面的要求逐字是「必須有降級路徑」）

---

## 護欄層減法（R89 淨額 ≤ 0 的來源）

### 為什麼本輪**必須**做減法

`_GUARD_LINES_REPIN_LOG` 現查：R86 −5、R87 +140、R88 +60
⇒ 已連續兩輪上升，而 `_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS = 2`
（款(11)`[只升不降]`：連續 3 輪為正即紅）⇒ **R89 的淨額必須 ≤ 0**。
這是 M1「總量連續三輪不上升」的機械面，合法出口逐字只有一個：
「讓某一輪的淨額 ≤ 0（刪行／合併鎖檔／把散文搬進帳本），連續計數當場歸零」。

🔴 掌舵者本輪的抱怨（「每輪都花時間在程式瘦身或文件瘦身，實在浪費精神與時間」）
在這裡有一個具體答案：**瘦身之所以每輪都來，是因為歷史敘事被寫進了程式碼**。
下面這 25 行就是標本——它記的不是「這個測試在守什麼」，而是「這段話在 R81/R82/R83
之間被誰訂正過幾次」。那屬於輪次證據檔，不屬於 `tools/tests/`。

### 搬遷標的：`MacCredentialSourceTest` 的 docstring 史料段（−25 行）

搬遷前先驗過兩件事：①全庫沒有任何判準讀本檔的 docstring 字面
（`grep -rn "get_docstring\|__doc__"` 的命中都是別的檔讀自己的）；
②`L4-03` 這個錨在別處只有註解引用，無機械消費者。

**逐字保全**（原文，不改一字）：

> R81 版是**單一硬編碼檔案路徑、零平台分支**，而代價是量出來的（本輪 Windows 模擬：
> 把 `CREDENTIALS` 指到不存在的檔＝等價於 mac 上該檔缺席 ⇒ `measure_detail` 回
> `no-credentials`、`quota_gate` rc=0、`fanout_cap(None) is None`）：切到 mac 之後
> 整條額度軸永久 `unmeasurable`，R81 落地的 80%／95% 兩道門**結構上一次都到不了**，
> 而外觀與「水位很低、很健康」完全相同。
>
> 🔴 **獨立複驗訂正本段的「誠實劃界」（原文今天起是假的，故不留著當現行說法）**：
> 原文寫「本組**沒有 mac 真機**」，並把「`security` 的 service 名與輸出形態在真 mac
> 上對不對」列為交棒項——而 **R83（mac 真機首輪）**已在真機上把那一半驗完。
> 🔴 這一行的輪號由獨立驗證者訂正過（原文署名 **R82**）：R82 收輪 commit 內這支檔逐字
> 寫著「我手上沒有 mac 真機…交由下一輪承接」⇒ 署名 R82 等於把交棒項講成上一輪已結清，
> 而那正是 `quota_meter.KEYCHAIN_SERVICE` 上方 R82 就寫下的那句預先警告在防的形態。
> 實測值的**唯一的家**
> 是 `quota_meter.KEYCHAIN_SERVICE` 的註解；本段刻意**不複寫**那幾個數字，複寫一份
> 就是再開一個會漂移的第二個家（R73 `Find-GitBash` 把一台機器的事實寫成常數，同型）。
> 這一段之所以會變假，正是「同一份知識住兩個家、只有一個家被改」：訂正落在 quota_meter
> 那一份，這一份留在原地說反話，而假在**會讓人以為這條路仍未驗**的方向。
>
> 🔴 順帶訂正這一行的輪號：原文把交棒輪號從承接輪改寫成**本批輪號**，而該行自己的
> 括號逐字寫著「交棒指名承接輪，非自稱本批輪號」⇒ 句子與它自己的判準相矛盾。而且那次
> 改寫**不必要**：該行同行本來就帶著 `round-label-ok` 具名豁免，輪號超前鎖
> （`test_check_defect_log_crossref.TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound`）
> 對它從來不成立（本回合實掃：違規清單裡沒有本檔）。交棒項既已結清，整個輪號標籤連同
> 那個豁免一併移除——留著一個沒有標的的豁免，下一個人只會再花一次力氣去讀它。

**判準零損失**：`MacCredentialSourceTest` 的測試方法一個都沒動，
留在 docstring 的是「今天守得住什麼／守不住什麼」那一段（現行有效的劃界）。

### 本輪淨額帳

當回合實測 `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`：

```
# 淨額 83670→83670 (+0)
# 逐檔漂移 0 支（淨額為 0 時本行仍會說話——那正是 R79 補它的理由）
```

⇒ 護欄層總量與 R88 基線**逐檔相同**，`_FROZEN_GUARD_LINES` 不需重釘、
`_GUARD_LINES_REPIN_LOG` 不需追加列（沒有漂移可記），款(11) 的連續上升計數歸零。

收斂過程（三次量測，全部實測而非估算）：

| 步驟 | 淨額 |
|---|---|
| 初版：3 個獨立測試，各帶完整 docstring | +38 |
| 壓成 1 個 `subTest` 參數化測試（鑑別力未損失） | +24 |
| ＋`MacCredentialSourceTest` docstring 史料搬遷 | +4 |
| ＋回收自己新寫的註解（WHY 已在本檔，指針仍在） | **+0** |

🔴 **本節就是掌舵者系統問題 3 的答案**：「每輪都在瘦身」不是宿命，也不是靠 Plugin
架構能解的——它的成因是**新增判準時沒有同步把等量史料搬出量測面**。這一輪新增了
一道完整的回歸鎖（含雙向注入自證），而護欄層總量**零成長**。做法可重複：
判準留在測試檔，史料進輪次證據檔，兩者以檔名指針相連。


---

## 護欄層減法（第二批）— 兩支鎖檔的史料段

🔴 **本節的存在理由本身是一個判例**：這兩段是由一個 subagent 搬走的，而它在
**寫進本檔之前**就死於 `monthly spend limit`（R87 的同一個錯誤訊息）⇒ 原檔的史料
已被刪除、docstring 裡卻留下指向本檔的**指針**，而本檔當時一個字都沒有。
**指針指向空處**比不搬更糟：它讓「資訊已保全」看起來是真的。原文由收尾者以
`git diff` 自工作樹取回並補齊於此。教訓：**搬遷是兩個動作，缺一即為刪除**；
派工時必須要求「先寫入目的地、再刪來源」，順序反了就沒有安全網。

### `tools/tests/test_sanitize_component_frozen_sdd_versions_lock.py`（−38 行）

>   對這 7 支檔案逐一用該既有 AST 掃描邏輯（掃描「風險識別字是否裸露出現在組
>   檔名的 f-string/字串串接/`%`/`.format()` 表達式中」）做對抗式驗證時，實測發現
>   兩個真實盲點，會讓搬過來的版本對兩支檔案完全失去鑑別力（bug-injection 用
>   `git show <固定基線 commit>:<path>` 取得修復前的真實歷史內容重放驗證，証實
>   下列兩者在修復前『0 offenders』——即該掃描法看不到真正的漏洞；此固定基線
>   commit 的選擇理由見下方 `_PRE_FIX_BASELINE_SHA` 常數註解與
>   `TestExpectedSanitizeCallDiscriminatesRealHistoricalRegression` docstring
>   ——R44 QA 一審發現原本用 `git show HEAD:<path>` 會在本輪修復 commit 之後
>   永久恆紅，已修正為錨定固定 SHA）：
>
>     (a) `production_to_fpl.py::generate_fpl_draft()`：修復前寫法
>         `fid = fpl_id or f"FPL-PROD-{ac_id}-{divergence_kind}"`——內層 f-string
>         本身不以 `.md`/`.yaml` 等副檔名結尾（副檔名是下一行
>         `f"{fid}.md"` 才組上去的兩段式間接組檔名），泛用掃描的
>         『f-string 字面結尾是否像檔名』判準因此不會命中這個 f-string，风险
>         識別字裸露完全被漏放。
>
>     (b) `counterfactual_replay.py::write_report()`：修復前寫法
>         `f"REPLAY-{patch.ac_id or 'unknown'}-{date}.md"`——`FormattedValue`
>         內是 `patch.ac_id or 'unknown'`（`ast.BoolOp`），泛用掃描的
>         `_raw_risky_reference()` 只認得裸 `Name`/`Attribute`/`Subscript`，
>         不會拆解 `BoolOp` 找出裡面包的 `Attribute`，同樣被漏放。
>
>   這兩個盲點目前也存在於 v0.30 端既有的 `test_sanitize_component_call_site_lock.py`
>   本身（R44 對該檔案做同款 bug-injection 交叉驗證證實，非本檔新引入的缺陷；
>   修復/回報該既有盲點超出本輪 P2 finding 的範圍，僅在此如實記載，供下一輪
>   評估是否值得投入修復那份泛用掃描器）。若要讓泛用 AST 掃描器同時涵蓋這兩種
>   形狀，需要遞迴拆解 `BoolOp`/追蹤『組檔名用到的中繼變數是否源自另一個本身不
>   以副檔名結尾的 f-string』——複雜度與投入不成比例（Rule 2 比例原則），對
>   **本質靜態、Copy-on-Evolve 之後不再變動**的 29 份凍結快照而言，改用下列
>   更簡單也更精準的手法：直接對每支檔案的『已知修復呼叫式』（如
>   `_sanitize_component(rule_id)`）做逐版正向存在性斷言——不管該呼叫式週邊的
>   程式碼結構多複雜、外層是否為 `BoolOp`/兩段式間接組檔名，只要修復呼叫式本身
>   被移除或還原，正向斷言必定測不到而失敗。本檔頂部 bug-injection 驗證
>   （見下方 `TestExpectedSanitizeCallDiscriminatesRealHistoricalRegression`）
>   逐一以 `git show <固定基線 commit>:<path>` 重放全部 7 支檔案修復前的真實
>   歷史內容，證實這個更簡單的正向斷言對全部 7 支檔案、包含上述兩個泛用掃描
>   盲點案例，均正確判定為「未通過」。

### `tools/tests/test_skip_discoverability_r83.py`（−21 行）

> ═══════════════════════════════════════════════════════════════════════════
> WHY（本檔為何存在——三筆當回合實測的缺陷，全部長在「指引」上）
> ═══════════════════════════════════════════════════════════════════════════
>
> 1. **DSN 守衛的修法只印 PowerShell 形態**（本輪主缺陷）。
>    `AutoClaude/tests/conftest.py::pg_dsn_problems` 修前逐字印
>    `$env:AUTOCLAUDE_TEST_PG_DSN = '…'`。`$env:` 是 PowerShell 專屬語法，bash/zsh 照抄
>    會把它展開成空字串、再把 `=` 當成指令名 ⇒ 得到一個與 DSN 毫無關係的錯誤。難看之處
>    在於**它長在一支專門用來「把人導向正解」的訊息上**：那則訊息存在的全部理由就是省下
>    使用者從 SQLAlchemy 錯誤反推回「我少打了四個字」那段路，而它自己在 mac 上又製造了
>    一段同型的反推。同檔另有 2 處、姊妹檔 `tests/perf/test_pgvector_recall_perf.py` 2 處、
>    `AutoClaude/tools/setup_pg_runtime_role.py` 1 處，全部同形態（本輪一併修）。
>
> 2. **`timeout <n>` 在 macOS 不存在**（GNU coreutils；BSD 沒有）。當回合實測：
>    `which timeout` → `timeout not found`、rc=1。repo 已有
>    `tools/tests/test_bash32_compat.py` 守 `.sh` 與 workflow inline `run:` 這兩個面，
>    但**文件與錯誤訊息裡的示範指令一個字都沒人看**。
>
> 3. 兩者的共同形態＝**單平台指引不外推**，而它發生的那個平面（活文件的散文與
>    Python 的訊息字串）此前零判準。

---

## 護欄層減法（第三批）— `MeterFailureShapesTest` 的 R83 訂正段

### 為什麼還要第三批

第一／二批把本輪新增判準的成長抵銷到淨額 0，但**款(12)`[到期未下修]` 同輪到期**
（稽核痕跡走到 R89＝`_REPIN_NET_CAP_DUE_ROUND`，而現行單輪淨額上限還停在上一段的值）。
它的唯一出口是**往 `_REPIN_NET_CAP_SCHEDULE` 追加一列更小的上限**，而那一列自己佔一行
⇒ 護欄層當回合實測回到 +5（`--print-guard-lines` 印 `83670→83675`）。
這就是這個機制的**固有遞迴**：兌現「重釘要付代價」的動作本身也要付代價。
⇒ 再搬一段等量以上的史料出量測面。

### 搬遷標的：`tools/tests/test_context_budget_guard.py::MeterFailureShapesTest`（−8 行）

搬遷前先驗過三件事（與前兩批同一組前置檢查）：
① 全庫沒有任何判準讀本檔的 docstring 字面——`grep -rn "get_docstring"` 的兩處命中
分別是 `test_check_defect_log_crossref.py`（讀**全樹**散文找超前輪號，不讀特定字面）與
`test_no_invalid_escape_sequences.py`（讀 raw-string 形態），皆非本段的消費者；
② 類名 `MeterFailureShapesTest` 在 `tools/lib/quota_meter.py` 與帳本有引用，
但引用的是**類名**、不是 docstring 內容，而類與其全部測試方法一個字都沒動；
③ **後段（R83／PD 複驗那一段）刻意不搬**——它含 `# stale-premise-ok:` 機械標記，
搬走就會把一個豁免與它的標的拆散。搬的只有中間那一段純輪次考古。

**逐字保全**（原文，不改一字）：

> 🔴 **R83 訂正本 docstring 原本的「誠實劃界」段（不逐字留著當現行說法）**：那段寫
> 「`CREDENTIALS` 仍然只有一個來源、零平台分支」，而 R82 同輪就把 darwin 分支落地了
> （`access_token()` 的平台分支，見 `git show HEAD:tools/lib/quota_meter.py`）
> ⇒ 這段自陳從落地當回合起就是假的，且它假在**會讓人以為這裡已經沒有平台問題**的方向。
> 真正的缺口是另一件事、而且沒有任何東西在守：`measure_detail()` 當時**沒有憑證來源的
> 注入點** ⇒ 本組只能靠改主機自己的憑證存放處來構造那兩條臂，於是每條臂只在一個平台
> 成立。mac 真機實測（**R83**＝mac 真機首輪）：把 `CREDENTIALS` 指到不存在的檔，
> darwin 完全不讀它 ⇒ 期望 `no-credentials`、實得 `http-401`，該臂在 mac 上結構性量不到。

**判準零損失**：`MeterFailureShapesTest` 的測試方法一個都沒動；留在 docstring 的是
「這個測試今天在守什麼」（SD-B4 的立案 WHY ＋ 現行雙欄矩陣的劃界）與那個帶機械標記的
輪號判例。原處留一行指針指回本節。

### 單輪淨額上限的到期兌現（款(12)）

| 項 | 舊 | 新 | 方向 |
|---|---|---|---|
| `_REPIN_NET_CAP_SCHEDULE` 末列 | `(87, 2600)` | 追加 `(89, 2000)` | 收緊（表 append-only、上限只准遞減） |
| `_REPIN_NET_CAP_DUE_TARGET` | 2000 | 1600 | 收緊 |
| `_REPIN_NET_CAP_DUE_ROUND` | 89 | 91 | **重新武裝**（見下） |

🔴 **為什麼到期輪一定要往後推，而這不是「放寬」**：款(12) 的紅燈條件是
`live_round >= due_round and cap > due_target`，而同一支測試另有一條
`assertLess(_REPIN_NET_CAP_DUE_TARGET, _REPIN_ROUND_NET_CAP)`（否則款(12) 是一句
永遠成立的話）。兩者在「到期輪＝當前輪」時互斥：前者要 `cap ≤ due_target`、
後者要 `due_target < cap`。⇒ 兌現的完整動作**必然**是「下修上限 ＋ 就地重新武裝下一段」，
這正是該常數區塊自己寫的「R85 兌現 5400→3200 之後必須就地重新武裝下一段，
否則這款從此恆綠＝機制靜默退役」。R85（→R87）與 R87（→R89）走的是同一條路。
本輪真正被收緊的是那把**尺**：上限 2600→2000、下一段目標 2000→1600。

步伐：−2200 →−600 →−600（本輪）→下一段 −400。刻意逐段變小，理由見該常數區塊：
再往下就逼近真實輪次大小，步伐不縮就會製造沒有出路的紅（ARCH-02）。


---

## DEF-200-123 — 把錯誤訊息的字面當成根因（fixed@R89）

### 事故（真實，非假想）

多個 subagent 死於 API 錯誤 `You've hit your monthly spend limit`。主控把**錯誤訊息的
字面**當成根因，宣稱保險池（`extra_usage`／`spend`）撞頂會擋住 agent，並把它寫進
`docs/04_planning/R89_HANDOFF.md`、本檔、多個 commit message，還當成**前提**餵給
Architect ⇒ 他整段 B-2 分析建立在假前提上。

掌舵者一句話戳破：「我的 monthly spend limit **本來就滿**」。落款
`~/.autosdd/traces/quota_burn.jsonl` 逐列實證：`spend`／`extra_usage` 自
`2026-08-13T22:29` 起**連續 15 列都是 100.0、一次都沒變** ⇒ 常數，**數學上不可能是變因**。
真變因是訂閱窗（`five_hour` 0↔84 反覆、`seven_day` 單調 0→86）。

### 為何既有攔截器抓不到

`.claude/hooks/check_claim_provenance.py` 的既有判準**刻意收在值域上**，只認「只可能
來自某次執行」的數字（`N passed`／`rc=N`），問的是「這個數字的出處在哪」。而因果宣稱
**不帶可比對的值域** ⇒ 結構上看不見。該檔檔頭自己記載了這個設計取捨。

### 假紅普查（母體＝逐字稿，不是 tracked 檔；重跑指令見下）

```
python tools/probe/causal_form_census.py [--shape g|a|b] [--jsonl out.jsonl]
```

母體（當回合實測）：**1,039 支**逐字稿、assistant 句 **40,703**、機制結論句 **1,474**、
對照詞抑制 **54**。

| 形狀 | 命中 | 真陽性 | 假陽性 | 判決 |
|------|------|--------|--------|------|
| **G**（錯誤字面被當成機制結論）＋ 符號過濾 | **3** | **3** | **0** | ✅ **上線** |
| G 未加符號過濾 | 13 | 3 | 10 | ❌ 精確率 23% |
| **A**（因果句裡的具名量在本場觀測值全同） | 3 | 1 | 2 | ❌ 精確率 33% |
| **B**（具名量沒有兩個相異觀測值，含 0 次） | **153** | 0（抽 12 筆） | 12 | ❌ 精確率 0% |

🔴 **母體差一點就是假的**：`~/.claude/projects/<slug>/` 只住 60 支，另外 **978 支
subagent 逐字稿住在再深一層**的 `<session>/subagents/`。第一版普查用 `glob("*/*.jsonl")`
只掃到 6% 的母體、報回 4 筆命中／50% 精確率。改 `rglob` 後同一份判準命中 13 筆、精確率
掉到 23%。**「假紅率看起來很低」最常見的成因就是母體被截斷。**

#### G 的 3 筆命中（全部真陽性，分屬三場 session）

1. `012fcf6d`（**上一輪主 session**）：「13 個 agent 仍全數死於 `monthly spend limit`
   ⇒ **subagent 那條路不吃訂閱窗**」——本輪的假前提正是從這句長出來的。
2. `agent-a2…`（該輪派出的 subagent）：「在訂閱窗幾乎全空的情況下，13 個 subagent 仍然
   全數死於 `monthly spend limit`」。
3. `b2e798a7`（本輪主 session）：「主池被 13 個並發衝爆…⇒ 報 `monthly spend limit`」。

#### 精確率 23%→100% 是靠一條判準修的，不是靠調參

未加符號過濾時的 10 筆假陽性中有 8 筆共同形態是「引述的字面其實是**符號**」：
`ModuleNotFoundError`／`DeadlineExceeded`／`WinError 216`／`subprocess.TimeoutExpired`／
某支測試的名字（因含 `…NeverExceed…` 而命中 `exceed`）。寫「⇒ `ModuleNotFoundError`」
的人是在指認他**推理出來的**失效模式，不是在轉述機器的散文——這是語意上的分別，不是
統計上的。判準＝`_is_prose_message()`：≥2 個空白分隔的詞，且每個詞都不含詞內大寫／
`.`／`_`／`:`。

#### 抑制詞的鑑別力也是量出來的

拿掉 `CONTRAST_RE` 會多命中 1 筆，而那 1 筆**恰好是掌舵者訂正後主控自己寫下的正解**
（「`monthly spend limit` 全程都是滿的 ⇒ 它是常數，不可能是變因」）⇒ 它只擋正解、
不減損鑑別力。

#### 🔴 上表是**量測值不是常數**（R89 放行條件收斂／SA N-C・QA NEW-3 訂正）

上表那三個數字（命中 3／真陽 3／假陽 0）先前被當成平述事實引用，包括帳本 `DEF-200-123`
那一列。**它們會漂，而且會往上漂**——原因是本判準的母體是**逐字稿**，而每一輪自己寫下的
逐字稿都會進到下一次普查的母體裡（**自指母體**）。三次量測（同一支探針、同一條判準）：

| 量測時點 | 母體逐字稿 | shape=g 命中 | 真陽性 | 精確率 |
|---|---|---|---|---|
| 落地當回合 | 1,039 | 3 | 3 | 100% |
| SA／QA 複審 | 1,046 | 4 | 3 | 75% |
| 放行條件收斂（本節寫下時） | **1,047** | **6** | **3** | **50%** |

新增的三筆命中**是同一句話的三個副本**（`agent-a3` 兩次、`agent-ab` 一次）：
「`ruff check .`（AutoClaude）→ **`Found 732 errors`** ⇒ 存量債仍在」。逐筆判讀為
**假陽性**——它在**複述工具輸出**（`Found 732 errors` 是 ruff 自己印的），不是把錯誤字面
當成機制結論；而它連命中三次是因為交件轉述會把同一句原文再抄一遍，普查不去重。

⇒ **不得把「假紅 0」寫成本判準的性質**。現行正確表述：判準對「引述錯誤字面 ⇒ 下機制結論」
這個形狀有效，對「引述工具計數 ⇒ 下存量結論」會誤命中；**精確率一律現查**：

```
python tools/probe/causal_form_census.py --shape g
```

（本判準只出聲、永不阻斷，所以 50% 這個精確率不會擋住任何人——那正是當初選「只出聲」
的理由。真要收斂假陽性，方向是把「複述工具輸出」與「下機制結論」分開，而不是調參。）

### 為何 A／B 兩個形狀被否決（＝「常數不可能是變因」不能直接寫成警報）

A 的假紅成因是結構性的：判準只知道識別字**出現在句子裡**，不知道它是不是被當成原因
（兩筆假紅命中的識別字都只是被順帶提到）。B 更糟：命中的 153 筆幾乎全是
`condition_evaluator`／`last_log_path`／`enable_kernel_brain` 這種**程式符號**，它們
根本不是「量」⇒ 該形狀等於對「句子裡出現 snake_case」發警報。

⇒ **常數／變因這條軸在散文平面上做不出鑑別力，但在落款平面上它是精確的**（欄位與值
都是結構化的，不必猜主詞）。所以那一半**不做成警報，做成正向工具**：

```
python tools/probe/variate_contrast.py ~/.autosdd/traces/quota_burn.jsonl \
    --split-at 2026-08-13T22:29
```

當回合實跑，逐欄判定（節錄）：

```
pct.extra_usage    n=13  相異 1   CONSTANT   └ 值恆為 100.0 ⇒ **不可能是任何事情的變因**
pct.nimbus_quill   n=20  相異 1   CONSTANT
pct.five_hour      n=21  相異 19  DISCRIMINATES  └ 前 ['24.0','35.0','38.0'] ／ 後 ['0.0','1.0','10.0','11.0']
pct.seven_day      n=21  相異 20  DISCRIMINATES
pct.weekly_all     n=20  相異 19  DISCRIMINATES
```

⇒ 整件事的證據**當時就躺在磁碟上**，一行指令、10 秒。攔截器的訊息因此**指著這支工具**，
讓查證比宣稱便宜（判準治形態、工具治內容，刻意分工，不是同一份知識住兩個家）。

### 落地面與逃生口

| 項目 | 位置 |
|------|------|
| 判準本體 | `.claude/hooks/check_claim_provenance.py::error_literal_mechanism_hits()`（既有 Stop hook，**不新增 settings.json 條目** ⇒ 不動兩種載具的配對面） |
| 逃生口 | `AUTOSDD_CAUSAL_GUARD_OFF`（**與 `AUTOSDD_CLAIM_GUARD_OFF` 分開**；`main()` 在讀完 payload 後分別檢查，關掉一個不影響另一個，由 `test_turning_off_the_causal_guard_leaves_the_other_one_armed` 釘住） |
| 出聲方式 | **只出聲、永不阻斷**（一律 exit 0，沿用同檔既有的 fail-open 契約） |
| 回歸鎖 | `tools/tests/test_claim_provenance_r86.py::TestTheR89ErrorLiteralMechanismJudgement`／`::TestTheCausalEscapeHatchIsItsOwn`（雙向合成注入：復發即紅、正解不紅） |
| 普查器 | `tools/probe/causal_form_census.py`（三種形狀都留著，因為**被否決的那兩種也是交件的一部分**——`DEF-200-046` 判過「普查沒有留下可重跑的產物 ⇒ 無法複驗」） |
| 正向工具 | `tools/probe/variate_contrast.py` |

### 🔴 誠實劃界

- **3 筆命中引述的是同一串字面**（`monthly spend limit`）⇒ 本判準在**這一型缺陷的複發**
  上已證明有鑑別力且零假紅，但它對「別的錯誤訊息被當成根因」的召回率**在本機母體上
  無從量測**（沒有第二個實例）。這是邊界，不是保證。
- 只認**反引號包起來的英文**。改寫成中文轉述（「死於月度支出上限」）或拿掉反引號就
  完全看不到。
- **不判斷因果是對是錯**，只判斷「你把機器的話當成了自己的結論」。被否決版本的兩筆
  `DeadlineExceeded` 假陽性正是這個邊界：推理其實成立，只是形態相同——這也是它**只出聲
  不阻斷**的第三個理由。

---

## DEF-200-123 附錄 A — 護欄層史料遷入（R89，淨額到期義務）

> **為何在這裡**：`_FROZEN_GUARD_LINES` 棘輪本輪淨額必須 ≤ 0，而 `DEF-200-123` 的回歸鎖
> 需要 +101 行。棘輪自己指定的合法出口就是「把 WHY 與史料搬出護欄層」（先例＝
> `test_claim_provenance_r86.py` 檔頭 R86 那次）。下列兩段是**逐字**遷入，不是摘要；
> 來源檔各留一行指針指回本節。搬動順序是**先寫入本檔、再刪來源**（本輪已有 agent 中途
> 死亡把搬遷變成刪除的判例）。
>
> 🔴 兩段都是**史料與已知邊界的敘述**，不是判準本體——判準本體一行都沒有動，
> 兩支鎖的 `scan_source()`／正則／豁免機制與遷入前逐字相同。

### A-1 — `tools/tests/test_ps51_compat.py`：R56 round 5/6/7 三元判準的判讀史

原文逐字（來源：該檔檔頭 docstring，遷出前的第 59–102 行）：

```text
  - 三元判準的 `?` 別名區辨（SD P3-SD-1）：實際把別名寫法擋在門外的是「同一行
    後方必須另有 ` : `」這個條件——PowerShell **程式碼**層級的「空白 冒號 空白」
    幾乎只出現在三元（`$env:X`／`C:\\`／`:label`／`${function:f}` 的冒號兩側都無
    空白）。`(?<!\\|)` 是額外的前瞻性防護（擋 `| ? { … }` 同行寫法），但**現行
    21 支 active `.ps1` 的 code 段連一處「空白 `?` 空白」都沒有**（2026-07-27
    實掃），故它今天不被任何真實檔案行使，偽陽性回歸鎖也**驗不到它**——如實記載，免得
    後續審查員誤以為該 lookbehind 已受測試保護（同輪 QA B-3 名實不符的教訓）。
    已知殘餘缺口（**偽陽性**方向）：管線換行後另起一行只寫 `? { … }`（行首無 `|`）
    且該行另含 ` : ` 時仍會偽陽性。
    已知殘餘缺口（**假陰性**方向。R56 round 5 SA 補列，round 6 Architect／SD／SA
    三方各自獨立以 pwsh 7.6.3 `Parser::ParseInput` + `FindAll(TernaryExpressionAst)`
    複驗、主控再親跑一次後訂正——原列的四例中有一例其實不成立，見下）：
    本判準 `(?<!\\|)\\s\\?\\s.*?\\s:\\s` 要求「`?` 後有空白**且**冒號兩側皆有空白」，
    但 PS7 語法不要求冒號兩側有空白——故下列**六例**皆為合法 `TernaryExpressionAst`
    （在 PS 5.1 必 parse error＝正是本鎖守備目標）卻**不命中**（兩項都實測過：
    pwsh AST errs=0／ternary=1，且本檔 `scan_source()` hits=0）：
    `$c ? 1:2`／`$c ?1 : 2`／`$c ? 1 :2`／`$c ? $a :$b`／`$c ? 1:$b`／`$c ? ($a):($b)`。
    **R56 round 7 二次訂正**：round 6 原列的第七例 `$c ? 'a':'b'` 其實**會命中**
    （`scan_source()` hits=1，`$x = $c ? "a":"b"`／`Write-Host ($c ? 'yes':'no')`
    亦同）——`split_code_comment()` 把字串字面值抹成等長空白後，該行變成
    `$x = $c ?  : `，反而製造出判準所需的 ` ? … : `。故「**兩分支皆為引號字串
    字面值**」的形態是**已被涵蓋**、不是缺口。此例由 Architect 與 QA 於 round 7
    各自獨立實測揪出，主控複驗確認（並發現自己首次複驗時把 `scan_source(source, rel)`
    的參數傳反、掃到檔名字串而得出全 0 的假結論——**驗證手法本身無鑑別力**的同型
    錯誤，同輪已在 venv 污染檢查上犯過一次，見帳本 DEF-101-461）。
    教訓：驗證「合法三元」（AST 面）與驗證「本鎖是否真的漏抓」（掃描器面）是
    **兩件事**，round 6 只驗了前者就下結論，故連續兩輪都在同一清單上出錯。
    **不需涵蓋、非缺口的三種形態**（實測皆非 `TernaryExpressionAst`）：
      - `$true?1:2` —— 全無空白，PS7 根本不解析為三元（errs=0／ternary=0）。
      - `$c ? $a:$b`／`$c ? $a: $b` —— 真值分支以**變數**結尾且緊接 `:` 時，
        `$a:` 被當成 scope-qualified 變數（`$scope:name`），PS7 本身即 parse error
        （errs=3／ternary=0：「Variable reference is not valid. ':' was not
        followed by a valid variable name character.」）。**R56 round 6 訂正**：
        此例原被誤列為假陰性，三方 AST 複驗證偽。留著會反向製造假缺口，誘使
        後續維護者去放寬 regex——而放寬正是下一段明確裁定不做的事，且 `$a:$b`
        恰恰就是那段所警告的 `$var:NAME` 形狀（自我矛盾）。
    故真正的判準不是「冒號兩側有無空白」，而是**冒號左側是否為變數**
    （`$c ? 1:$b` 成立、`$c ? $a:1` 不成立）。
    刻意不放寬冒號空白條件：實測放寬為 `\\s\\?\\s*.*?\\s*:\\s*` 雖對現行 21 支 active
    `.ps1` 仍零命中，但會讓 `… | ? { $_ -ne $env:TEMP }` 這類「Where-Object 別名
    ＋ `$env:X`」的同行寫法變成偽陽性，收緊代價高於收益。
    **因此檔頭「A 語法/運算子組」所列的 `? :` 僅涵蓋全空白形態**，非該禁令的完整
    機械化；`tools/windows_smoke_local.ps1` 檔頭列的 4 項禁令中，三元這一項仍部分
    依賴人工複核。
```

#### A-1 補遷（R89 放行條件收斂／QA C1）— 同檔檔頭「R57 QA-R57-04 訂正」段

**為何補**：該檔檔頭現存的指標逐字寫「該訂正史料逐字遷至……§A-1」，而 §A-1 本身
**沒有**這一段（`grep -F "R57 QA-R57-04"` 於本檔命中 0）＝指向不存在物的指標。原文逐字
（來源：`tools/tests/test_ps51_compat.py` 檔頭 docstring，遷出前的第 16–19 行）：

```text
（R57 QA-R57-04 訂正：本段原文「全部 step 一律 `shell: pwsh`（＝7），只有
windows-nightly-full 有**一支** `shell: powershell` 步驟」與 workflow 實況
不符——bash 例外未提、5.1 步驟已不只一支。此處刻意不寫死各引擎的步驟支數，
以免再次靜默過期；逐 job 的 shell 分佈以 workflow 檔本身為準。）
```

### A-2 — `tools/tests/test_extras_quoting_zsh_safety.py`：R57／R59 的缺陷本體與立案理由

原文逐字（來源：該檔檔頭 docstring，遷出前的第 3–43 行）：

```text
# 缺陷（R57 Scan-A2 = DEF-101-479；R59 擴面 = DEF-101-507／508）

macOS 自 Catalina 起預設登入 shell 為 **zsh**，且 `nomatch` 預設開啟。zsh 對未加引號的
`.[dev,notifications]` 執行 filename generation（glob）；repo 內沒有「`.` + 單一字元」的
匹配檔名，zsh 遂 **在執行指令之前就中止整條命令列**：

    $ zsh -c 'echo REACHED .[dev,notifications]'
    zsh:1: no matches found: .[dev,notifications]      rc=1     ← echo 從未執行
    $ zsh -c "echo REACHED '.[dev,notifications]'"
    REACHED .[dev,notifications]                        rc=0
    $ bash -c 'echo REACHED .[dev,notifications]'
    REACHED .[dev,notifications]                        ← bash 無此行為

實害：macOS 開發者照文件複製貼上 `uv pip install -e .[dev,notifications]`，看到的是  <!-- zsh-glob-ok: 本檔即此鎖的實作，docstring 必須原樣引述壞形態才能說明缺陷本身 -->
一個與套件完全無關的 `no matches found` —— uv/pip 根本沒被呼叫到。同一行在 bash 與
PowerShell 下都正常，故 **Windows 開發者永遠不會遇到**，是單邊平台缺陷。

R57 動工時全 repo 活文件共 16 處未加引號（`AutoClaude/README.md` 9、
`docs/AISDLC_Agent_UserGuide.md` 4、另三份各 1），全部已修。

**R59 擴面的兩個新形態**（DEF-101-507／508）：R57 只修了裸 `.[extras]`，但同一個 zsh
`nomatch` 語意對 **具名套件** 完全一樣——`autoclaude[postgres]` 是合法 glob（literal
`autoclaude` + 一個取自 `{p,o,s,t,g,r,e}` 的字元），無匹配檔名時同樣整條中止。R59 動工時
掃描面內這種形態有 40 行（另 1 行在 `README_Prompt_v0.1_history.md` 歷史快照，依逐字保全
政策不改），其中十幾處是 **執行期 raise/print 給使用者的唯一修復指引**
（`factory.py` 4 處、各 `Pg*` adapter/repository 的 ImportError、`alembic/env.py`、
`migrate_file_to_pg.py`）——使用者已經卡在缺依賴，照唯一提示做又拿到第二個看不懂的錯。
另一形態是 `tools/bootstrap_core.py` 安裝失敗訊息把 **f-string 插值的絕對路徑 target**
裸著印出（DEF-101-508）。

# 為何需要這道鎖

修完只是解決當下；本 repo 反覆的教訓是「人工修完的東西沒有機械鎖就會回流」。
extras 語法在文件裡是高頻複製貼上的樣板，未來任一次新增安裝說明都可能寫回未加引號
形態，而 `check_pytest_baseline_sites.py` 等既有守門完全不看這個面向。

**R59 的教訓更直接**：這道鎖 R57 版的 docstring 曾以「repo 內無此寫法」為理由明文排除
具名套件形態——該前提當下即為假（40 行），且 R57 自己在 `ONBOARDING.md` 寫的
`pip install -e 'AutoClaude[dev,notifications,lint]'` 已經加了引號，可見它認得這個風險，
卻在鎖裡宣稱不存在。**未實測的「repo 內沒有」不可以拿來當縮減掃描面的理由**，這正是
`docs/06_quality/CrossPlatform_Scan_Dimensions.md` 判準 (4) 要治的病。
```

#### A-1 續 — 同檔「剝除策略」的實測數字與 here-string 誤啟（QA B-2）判讀史

原文逐字（來源：同一份 docstring，遷出前的第 38–58 行）：

```text
剝除策略（比 bash32 版**多剝字串**，刻意，非疏漏）：本 repo 的 `.ps1` 大量以字串
與 here-string **產生 bash 腳本內容**（`install_post_commit.ps1` 的 here-string 內就
有 `|| true`），只剝註解會立刻假紅。實測（2026-07-27，四棵樹 21 支）此策略零命中；
未剝字串則 4 筆偽陽性（2 筆 here-string 內的 bash `|| true`、2 筆變數名
`$utf8NoBom` 撞 `utf8NoBOM` 關鍵字——後者另以「前一字元不得為 `$`/單字元」的
negative lookbehind 收斂）。
代價（如實揭露）：真的寫在字串裡、之後 `Invoke-Expression` 執行的 PS7-only 語法
掃不到；行級 regex 無語法樹，屬 heuristic 邊界。該邊界的兩個**具名子情形**
（R56 round 5 由 QA／SD 實測補列，避免下一輪重新「發現」後誤判為新缺陷）：
  - here-string 誤啟（QA B-2）：`_HERE_STRING_RE` 只認 `@"`／`@'` 這兩個字元組合、
    不分辨其是否位於行尾。**行內**出現的 `@"`（如 `Write-Host "user@"`）或 `@'`
    （如 `.Split('@')`）會被當成 here-string 起點，一路吃到下一個行首 `"@`／`'@`，
    **遮蔽其間的真違規**（純函式探針實證：緊接其後一行的 `$IsWindows` 掃不到）。
    刻意不改 regex：實害目前為零（R56 round 5 訂正、分列口徑實測——四棵樹 21 支共
    3550 行中，**here-string 規則單獨**只清空 18 個非空行（span 19 行），
    block-comment 規則另清空 311 個非空行（span 362 行），兩者合計 329；原文把合計
    值 329 掛在「本規則」名下，把 here-string 規則的覆蓋面誇大約 17 倍。且
    **四棵樹掃描面內**「非行尾的 `@"`／`@'`」只有 2 處（LATEST 版
    `install_post_commit.ps1:116/117`），兩處都已落在既開啟的 here-string 區內；
    凍結版 v0.01~v0.29 的同名檔另有 47 處同形，惟凍結版不在掃描面內），
    而收緊判準所引入的偽陽性風險高於這個零實害的漏判。
```

---

## R89 收尾：`cap=1` 地板拆除（掌舵者裁決／SA 複審條件 1／QA 複審 B-1・B-2）

### 動作

刪除 `tools/lib/quota_policy.py::decide()` 內的

```python
cap = binding.cap
if any(r.band == BAND_HALT and r.axis.kind in FALLBACK_KINDS for r in readings):
    cap = 1 if cap is None else min(cap, 1)
```

改為 `cap=binding.cap` 直接進 `Decision`。原地留**墓碑註解**（不留「暫時關掉」的版本
——本檔已判過「留一個沒人叫的版本等於把缺陷留在原地等下一個呼叫端」）。

### 為什麼是「拆」而不是「留著加註記」（三條理由各自獨立成立）

**① 立案事實已被落款證偽，而且引用方向整個反過來。**
舊註解逐字引 `docs/04_planning/R87_HANDOFF.md:20` 的「主力軸只有 1%」當立案事實。
實查該行：

```
| 錯誤的證據① | 「主力軸只有 1%」——訂閱窗與月度付費上限是**不同的池** |
```

它住在 R87 事故表的「**錯誤的證據①**」那一列——是 R87 自己標記為**錯誤判讀**的東西，
不是事實。落款側的獨立證據（`~/.autosdd/traces/quota_burn.jsonl` 第 5~8 列，當回合複驗）：

| # | ts | `five_hour` |
|---|---|---|
| 5 | 2026-08-13T22:29:22+08:00 | 1.0 |
| 6 | 2026-08-13T22:32:38+08:00 | 6.0 |
| 7 | 2026-08-13T22:37:55+08:00 | 11.0 |
| 8 | 2026-08-13T22:40:56+08:00 | **63.0** |

11 分鐘內 Δ=**62pp**，與 `R87_HANDOFF.md` §2 的「Δpct 62」逐字吻合 ⇒ 那 13 個 agent
**跑了 634 秒、真的燒掉 62pp 訂閱窗才死**，不是被擋在派工口。
⇒ 舊註解那兩句「（探針）沒有解釋 R87 為何 13/13 全滅」「本機結構上觀測不到」都不成立。
**現行說法：R87 的死因至今未知**；`You've hit your monthly spend limit` 是**後果的字面**，
不是變因（同一批 agent 已先在訂閱窗上燒掉 62pp）。

**② 判準鍵在一個常數上 ⇒ 零鑑別力。**
對池子撞頂的帳號，`any(r.band == BAND_HALT and kind in FALLBACK_KINDS)` **終生無條件
成立** ⇒ cap 被**永久**釘在 1。它不是「把殘餘風險收斂成 1 個 agent」的取證協定機制化，
而是把本輪剛拿掉的否決權（16→0）**從後門還回 15/16**（16→1）＝掌舵者裁定的「本末倒置」
原樣復發。

**③ 同一個 commit 自帶反證。** `ca9985b` 的 message 逐字：「派 1 個 subagent 成功
（63027 tokens / 4.6s）⇒ 推翻『subagent 用量走付費池』的推論」。探針**已經**推翻了
「保險池滿 ⇒ 一定派不出去」，地板卻仍以「未解釋」為由裝上。

### 憲法面：就算前提沒被證偽，這道地板仍是**明示偏離**

- PRD §4.2.3（`:289-298`）是一份**封閉**的 8 步閘門列舉，「決策順序固定，任一步命中即
  短路」，八步分別讀 `HALTED_MANUAL`／遙測狀態／`U7d`／`U5h`／`U7d_model`——
  **沒有任何一步讀 overage**。在其後追加第 9 條「保險軸 halt ⇒ cap 夾 1」是規格外的動作。
- 若掛 PRD §1.2 原則 5（fail-safe，`:113-114`）當理由：該原則列舉的觸發是
  「**遙測不可得、逾時、解析失敗、時鐘異常**」，**不含**「過去有一次無法解釋的事故」
  ⇒ 那是**外推**，必須寫成外推。
- 依 `R89_HANDOFF.md` §6a 的治理規則，PRD 是最高憲法基準，偏離要走修憲程序
  （四方全同意）。本輪沒有四方同意 ⇒ **不得靠登記到期輪次把偏離留著**，只能拆。

### 附帶效益（拆掉才回來的不變式）

`decision.cap == per_axis[decision.binding.kind].cap`。地板在時 binding **不再解釋** cap，
連帶兩個下游現為假：

| 站點 | 地板在時的行為 |
|---|---|
| `tools/lib/quota_messages.py::throttle_horizon_line()` | 取 binding 的 `resets_at` ⇒ 在本輪姿態下印「這道節流很快就會自己解除」＝假話（cap=1 來自 `extra_usage`／`spend`，等 `five_hour` reset 不會解除） |
| `tools/lib/quota_gate.py` free 帶早退（`cap is None`） | 地板產生 `cap == 1` ⇒ 從它底下漏過去 |
| `tools/lib/quota_gate.py` 註解「`cap is None` ⟺ binding 落在 free 帶」 | 現為假 |

拆除後三者同時回復；本輪**不必**再各自打補丁。

### 取證協定要保留的話（**另案，不是本輪**）

正確的鍵不是保險軸的 band，而是 `account_posture()["fallback_available"] is False`
**且**訂閱軸已進 prepare 帶。本輪沒有任何量測支持任何一個門檻值 ⇒ 不在這裡發明數字。

### 🔴 登記：`ca9985b` 的 commit message 第③點含一筆已證偽的引用

commit message 改不掉（append-only 的歷史），只能在此登記：
`ca9985b` 的 message 第③點以 `R87_HANDOFF.md:20` 為立案事實，而該行是「錯誤的證據①」。
**任何日後讀到那則 message 的人，以本節為準。**

### 🔴 明文劃界：本次前提訂正**不影響**主體改動

`ca9985b` 的主體改動＝`gate = [r for r in readings if r.axis.kind not in FALLBACK_KINDS]`
（保險軸不進 cap 聚合）。它的依據是**純 PRD 推導**，與上面被證偽的那個前提無關：

| 依據 | 逐字 |
|---|---|
| PRD `:109-110`（§1.2 原則 3） | 「任何派工決策必須同時通過 5 小時視窗閘門與週上限閘門」——**雙軸**，不含 overage |
| PRD `:289-298`（§4.2.3） | 封閉 8 步閘門列舉，無一步讀 overage |
| PRD `:876`（§6 4b） | `OVERAGE_POLICY=FREEZE`（預設，絕不動用超額） |
| PRD `:1367`（§15.5 紅線 2） | 「超額用量必須是顯式的 opt-in」 |
| PRD `:78`（§0.6 新發現 1） | 「達到訂閱限制**後**可能可以付費續跑」＝它是**之後**的東西 |

⇒ **整包不需要重做**；本輪拆掉的只有 `ca9985b` 之上那一小段第 9 條閘門。

---

## R89 收尾：`FALLBACK_KINDS` 補齊 ＋ 鏡射鎖由 `==` 改為子集（SA 複審條件 2／B-3）

### 病

`tools/tests/test_quota_policy.py` 的鏡射鎖寫成
`assertEqual(Q.FALLBACK_KINDS, frozenset(M.CREDIT_POOL_KEYS))`。兩者**命名空間不同**：

| 常數 | 語意 | 成員必須是 |
|---|---|---|
| `quota_meter.CREDIT_POOL_KEYS` | 美元計價池在 payload **頂層**的兩種表述 | payload 頂層鍵，且 `_credit_pool()` 認得它的欄位形狀 |
| `quota_policy.FALLBACK_KINDS` | 哪些 **bucket kind** 不進 cap 聚合 | `limits[].kind`／頂層 bucket 名 |

今天恰好同值，被 `==` **焊成契約** ⇒ 「補齊保險軸」這件事本身會轉紅（本輪實測到）。
正確關係是**包含**：美元池必為保險軸，保險軸可以更多。

### 動作

- 判準改為 `assertLessEqual(frozenset(M.CREDIT_POOL_KEYS), Q.FALLBACK_KINDS)`。
- `FALLBACK_KINDS` 補入 PRD `:78`（§0.6 新發現 1）明列的 overage 類：**`overage`**、
  **`seven_day_overage_included`**。理由是**取數層原樣帶出 kind**
  （`quota_meter.bucket_readings()`：`{"kind": str(item.get("kind") or "?"), ...}`）
  ⇒ 伺服器哪天吐這兩個 kind，它們會被當**訂閱軸**進 cap 聚合＝本輪剛治好的 bug 原樣復發，
  而失敗表徵與正常運作相同。今天 live payload 命中 0 ⇒ **純寫入面判準，零假紅**。
- `spend` **不在** PRD `:78` 的列舉裡（它是端點頂層鍵、不是 `rate_limits` 的 kind）
  ⇒ 三家的註解都逐字註明「PRD 未列、由 payload 實測補入」，不讓下一個人以為四個成員
  都有憲法出處。
- 三家鏡射鏈同步：`tools/lib/quota_policy.py`（root policy）／`tools/lib/quota_meter.py`
  （root meter，**維持 2 個成員**＋關係註解）／
  `AutoClaude/autoclaude/core/ports/quota_meter.py`（engine copy，4 個成員）。
  引擎側那道鎖（`AutoClaude/tests/test_r82_quota_axis_and_shipped_defaults.py::
  TestTheFallbackKindsMirrorTheRootDeclaration`）同輪由 `==` 改為子集。

### 未知 kind 的預設分類（本節同時回答 SA 條件 2 末項）

live 快取當回合實測 7 軸：`session`／`weekly_all`／`weekly_scoped`／`five_hour`／
`seven_day`／`nimbus_quill`／`spend`。其中 **`nimbus_quill` 不在 PRD 任何列舉裡**，
而它**今天已經在參與 cap 聚合**（deny-list 的結構性後果：不在 `FALLBACK_KINDS` 就進
gate），沒有任何地方說過這件事。

**定調＝維持訂閱軸／保守側，但必須出聲。** 落地：`quota_policy.KNOWN_KINDS` ＋
`NOTE_UNKNOWN_KIND`，未知 kind 在 `note` 與 `reason` 兩個出口各出現一次。
當回合 `--pace` 實測逐字：`kind=nimbus_quill 0% reset 距離不明 band=free horizon=none
cap=None note=missing+unknown-kind`。

🔴 **為什麼這不違反 `quota_policy.py` 檔頭「禁止寫死桶名清單」那條紀律**：那條禁的是拿
名單去**選桶／分類**（名單一過期就整片失明，而且會**靜默答錯**）。`KNOWN_KINDS` 一行都
不參與分類，只決定「要不要多說一句」；它過期的後果是**多說**幾句 false unknown，
結構上不可能改變任何一個 `cap`／`band`／`rec` ⇒ 方向是 fail-safe。這條性質不是散文，
由 `TestR89UnknownKindsAreLoudButNeverReclassified::test_red_a_stale_vocabulary_only_adds_noise`
釘住（把一個**已知**軸從詞彙表拿掉 ⇒ 三個決策欄逐字不變、只多一句話）。

### 判準（皆含雙向合成注入自證）

| 判準 | 位置 | 紅端 |
|---|---|---|
| 保險集只能收白名單內的 kind（QA N-1：由「黑名單四個」翻成「白名單以外一律紅」） | `TestR89TheFallbackSetMayNotSwallowASubscriptionAxis::test_no_subscription_axis_is_ever_a_fallback_axis` | `..._test_red_the_old_blacklist_was_blind_to_the_axes_it_did_not_name`：注入 `weekly_scoped` ⇒ 舊黑名單全綠、新白名單必紅 |
| 兩家關係是包含不是相等 | 同上（`assertLessEqual`） | 把 `CREDIT_POOL_KEYS` 拿掉一個成員即紅 |
| PRD `:78` 的 overage 類必須在 | 同上 | 移除任一即紅 |
| 未知 kind 兩個出口都出聲 | `TestR89UnknownKindsAreLoudButNeverReclassified::test_an_unknown_kind_says_so_in_both_outlets` | 已知軸被誤標即紅 |
| 詞彙表成員資格不得改變決策 | 同類 `::test_membership_changes_nothing_but_the_note` | 同一組讀數換已知軸名，三欄必須逐字相同 |

### QA B-3 第二筆：`test_context_budget_guard.py` 的換軸

`:6362-6364` 把「只能等人」那格的 `spend` 換成 `nimbus_quill` 是**對的**（`nimbus_quill`
不在 `FALLBACK_KINDS` ⇒ halt 時 binding 就是它自己 ⇒ 訊息正確），但它同時把「保險軸撞頂」
這個**真實姿態**從本表移走，於是那一格一個觀測者都沒有。

🔴 **加回來的那一格，期望值與 QA 給的形狀相反，理由在此說明（不是漏做）**：QA 寫的是
「`spend` 100% ＋ 訂閱軸健康 ⇒ 斷言出現 escalate 字樣」，那個期望值成立的前提是**地板還在**
（cap 被夾成 1、binding 卻是健康的訂閱軸 ⇒ 印「很快就會自己解除」＝B2 那句假話）。
地板既已於同一批指令中拆除，`spend` 根本不進 cap 聚合 ⇒ 誠實的答案是
**一句節流都不宣稱**——宣告一個不存在的節流，正是同表第三格（free 帶）在防的事。
故該格寫成 `deny="這道節流"`。實測：`1 passed, 4 subtests passed`。

---

## 護欄層史料搬遷（R89 收尾批）

**規則**：`tools/tests/**` 本輪淨額已重釘為 **+0**，在那裡加行必須等量把史料搬出量測面。
下列原文逐字遷入本檔，來源處只留一行指標（`docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`）。

### 來源：`tools/tests/test_quota_policy.py::TestR87TheMeterMayNotDropAThrottlingAxis`（class docstring）

```text
R87 事故鎖：**取數層不得把「已撞頂但自報 `enabled:false`」的軸丟掉。**

🔴 立案（本輪真實事故，非假想）：13 個 subagent 全數撞
`You've hit your monthly spend limit`，燒 **1,319,703 tokens**／331 tool_uses／634 秒、
**零產出**。根因**不在判讀層**——`decide()` 的「halt 一票否決」不變式當時完好無損；
舵手是從**取數層**把 `spend`／`extra_usage` 兩軸整個排除掉（誤讀
`enabled:false` ＝「池子關著、不算節流軸」，真意是 `used 610 > limit 500` 已撞月度
支出上限、購買功能因此被 org 層停用）。於是判讀層**拿不到輸入**，整道保護在
**零判準觸發**的情況下失效，且失敗表徵與「一切正常」完全相同。

⇒ 這揭露的架構缺口是：判讀層的不變式只保證「**給定的軸**不會被放寬」，
它**不保證「軸不會消失」**。本鎖補的就是那一格——把事故當下的真實 payload 釘成
fixture，任何讓它**不再 halt** 的改動當場轉紅。

🔴 本鎖的存在理由是「**由程式否決模型，不是由模型自律**」：掌舵者對本事故的裁決
逐字為「不是要寫在程式架構控制嗎？怎麼變成你在控制？」。散文約束對當下的模型
零攔阻力（repo 已多次實證），所以下一次有人再判定「這是假紅」時，必須有東西轉紅。
```

🔴 **R89 收尾對上段第 2 段的訂正**：「任何讓它**不再 halt** 的改動當場轉紅」這句
已於 R89 憲法裁決後不成立（保險軸不進 cap 聚合 ⇒ 該 fixture 現在本來就不 halt）。
現行判準守的是**軸還在不在、水位有沒有被改寫、逐軸帶別與逐軸 cap 有沒有被放寬**。

### 來源：同檔 `::test_the_incident_payload_still_carries_both_axes_end_to_end`（docstring）

```text
端到端：兩軸的**逐軸讀數必須原封不動**，只有 cap 聚合不吃它們。

🔴 R89 重新表述（Architect 複審 4-1）。舊判準是「結論必須是 halt／cap=0」，
而 R89 的憲法裁決（PRD §6 4b `OVERAGE_POLICY=FREEZE`＝絕不動用超額 ⇒ 保險軸
不進 cap 聚合）讓它必然為假。**但期望值不可以改成 `free`**：Architect 實測
把事故 payload 同時餵給正確實作與 R87 錯誤實作，`band`／`cap`／`rec`／`binding`
四欄**逐字相同** ⇒ 改成 free 會得到一支對 R87 錯誤實作照樣通過的假鎖。
⇒ 判準改到**仍有鑑別力**的觀測面：R87 是「軸整個消失」，所以就守軸還在不在、
水位有沒有被改寫、逐軸帶別與逐軸 cap 有沒有被放寬。R87 錯誤實作**結構上**
滿足不了第一條（軸不在 `per_axis` 裡）。
```

### 來源：同檔 `::TestR89TheFallbackSetMayNotSwallowASubscriptionAxis`（class docstring）

```text
🔴 R89／Architect 複審②：`FALLBACK_KINDS` 是新開的繞過面，本鎖是它唯一的觀測者。

立案實測（Architect 對該常數逐條合成注入，跑全套 136 測）：注入 `five_hour`
——**最主要的訂閱節流軸**——只有 **1** 支測試會紅，而那支正是同輪被改寫的
`test_the_incident_payload_still_halts`；注入**全部**訂閱軸則轉紅 **0** 支
（被 `decide()` 裡的 `or readings` fail-safe 遮住）。⇒ `DEF-200-107` 的形狀
（一個軸可以靜默停止 gating，而失敗表徵與正常運作相同）沒有被消滅，只是從**取數層**
搬到了**判讀層**，新住址一個不變式都沒有。本鎖補的就是那一格。
```

🔴 **R89 放行條件收斂（QA C1）訂正本區塊的「逐字」二字**：上段先前把原文裡的
`test_the_incident_payload_still_halts` 就地換成了它今天的名字（`..._carries_both_axes_end_to_end`），
於是一個標著「逐字」的區塊裡混進了一個**當時並不存在的字面**——那正是本 repo 反覆判紅的
「憑證裡混一句假話」。現已還原為原文逐字；改名這件事寫在區塊**外**：該測試已於同輪更名為
`test_the_incident_payload_still_carries_both_axes_end_to_end`（見上一節），
`test_the_incident_payload_still_halts` 今日在 repo 內不存在，引用它時請視為史料而非活體符號。

### 來源：同檔 `::test_a_toothless_null_axis_no_longer_vetoes_acceleration` 與
`::test_an_axis_with_no_horizon_but_a_real_cap_blocks_acceleration`（docstring 史料段）

```text
🔴 R84／SA-01 訂正本測試此前的形狀（原版拿 `spend 0%`＝free 帶當否決者，斷言
`rec == 8`）。那個斷言把「一個 cap=None、零煞車力的軸有完整否決權」釘成了契約，
於是掌舵者錨點①（低水位＋近 reset ⇒ 多派）在 production **任何**水位下都拿不到
×2：live 快取 7 軸有 3 軸 `resets_at=null` 且全是 0% ⇒ 否決永遠成立。
現在的不變式是「**不參與 cap 的軸不得參與 pace**」，兩個方向各自被下面兩支釘住。

數字是 live 快取的形狀（3 軸 `resets_at=null` 且 0%）：修前 8、修後 16。

🔴 R89 收尾／QA 複審 B-3：fixture 由 `spend` 換成 `nimbus_quill`，理由與上面那支
逐字相同——`spend` 自 R89 起被 `decide()` 的 `gate` 排除 ⇒ **它根本到不了
`_pace_of()`**，這條 assert 對它宣稱要守的缺陷零鑑別力（QA 注入實證：把 `_pace_of`
退回舊 `any(horizon == AXIS_NONE)` 判準，行為鎖本身全綠）。同輪一併把紅端
自證的軸換成同一個：綠端走 `decide()`（gate）、紅端走 `axes_of()`（全部軸），
**軸集合必須相同兩端才配對得起來**，而 `nimbus_quill` 不在 `FALLBACK_KINDS`
⇒ 兩個面對它逐字等長。
```

### 來源：同檔 `::TestR87AccountPostureIsKnownBeforeDispatch`（class docstring 史料段）

```text
立案逐字：「配置 Agents 前，要先知道 Account Type and Account 是否有 Usage
credits 再進行配置！」。事故機制＝訂閱窗尚有 37% 餘裕、credits 池已爆且停用
⇒ 扇出全滅而主 session 照常 ⇒ **credits 是「還有沒有救」的布林，不是節流軸**。
```

🔴 **R89 收尾訂正**：上段「訂閱窗尚有 37% 餘裕」與 `quota_burn.jsonl` 第 5~8 列
（`five_hour` 1.0→63.0）指的是事故的**不同時刻**，兩者都不是「13 個 agent 被擋在派工口」
的證據——**R87 的死因至今未知**，見上方〈`cap=1` 地板拆除〉①。

---

## R89 收尾：兩筆過程事實（照實記，不是宣稱）

### ① 帳本併發寫入把一列 P1 未結案**整列刪掉**，靠 `git show HEAD` 才救回來

本包寫帳本的同時，另一個包也在寫同一支 `AutoSDD_Defect_Log.md`（兩邊都是「讀整檔 →
以列索引改寫 → 整檔寫回」）。競態的結果不是衝突而是**靜默覆蓋**，磁碟上的表徵是：

- `DEF-200-114` 出現**兩列**（一列舊版、一列本包訂正版）；
- `DEF-200-115`（P1、open、承接 R90，「守衛可被受守衛者關閉」）**整列消失**。

抓到它的不是任何人的注意力，是 `tools/tests/test_archive_defect_log.py` 的
同檔 ID 唯一性判準（21 支測試一起紅，訊息逐字點名 `DEF-200-114：在 … 內出現 2 列`）。
`tools/check_defect_log_crossref.py` 對這兩件事**都是 rc=0**（重複列與缺列都不在它的
判準內）⇒ 只跑 crossref 的人會拿到假綠。處置：刪掉舊版重複列、由
`git show HEAD:docs/06_quality/AutoSDD_Defect_Log.md` 取回 `DEF-200-115` 原文並插回。

⇒ **給收尾窗口的行動項**：帳本這種「整檔讀改寫」的共享檔，**不得由並行包各自寫**
（同根 `CLAUDE.md` 鐵律七「鎖的持有面」那條的另一個面向：這裡切開的不是鎖的常數／史料／
消費端，而是**同一支檔的寫入權**）。本輪沒有改判準，只把事實記在這裡。

### ② 本包對護欄層行數棘輪的足跡是 **0**

`tools/tests/` 只動了兩支，兩支收斂後**逐字回到 `_FROZEN_GUARD_LINES` 的凍結值**
（`test_quota_policy.py` 1805、`test_context_budget_guard.py` 6380）⇒ 不需要重釘、
不需要新增 `_GUARD_LINES_REPIN_LOG` 列。做法就是本輪示範的那條：
**判準留在測試檔，史料進本檔，兩者以檔名指針相連**（見上方〈護欄層史料搬遷（R89 收尾批）〉）。

收尾當回合 `--print-guard-lines` 仍印 `逐檔漂移 4 支`，四支**全部不是本包的檔**
（`test_claim_provenance_r86.py` +93／`test_extras_quoting_zsh_safety.py` −37／
`test_ps51_compat.py` −56／`test_subprocess_encoding_hygiene.py` +1，皆為同輪另一包
未收斂的工作樹改動）。那四支的重釘屬**收尾單人窗口**，本包刻意不碰。

🔴 **R89 收尾窗口訂正上面這一節的標題與結論（「足跡是 0」在分桶棘輪那把尺上為假）**：
見下方〈分桶棘輪：+157 全部來自**重新歸類**，不是散文成長〉。

---

## 分桶棘輪：+157 全部來自**重新歸類**，不是散文成長（R89 收尾窗口實測）

### 現象

收尾窗口接手時 `TestGuardBucketRatchet::test_shrink_only_buckets_did_not_grow` 紅：

```
[分桶成長] shrink-only 桶 `prose`：4119 → 4276（+157）
```

### 逐檔歸因（可重跑）

以 `tools/lib/guard_bucket_policy.py` 的量測入口對 `HEAD` 與工作樹各跑一次、逐檔相減：

```
HEAD prose: 4119   NOW prose: 4276
  +157  tools/tests/test_quota_policy.py  (0 -> 157)
```

**全部 157 落在同一支檔，而那支檔在 HEAD 的 prose 計數是 0。** 再往下切到 chunk 粒度：

| chunk | HEAD 行數 → 現行行數 | HEAD 歸屬 → 現行歸屬 | 對 prose 桶的貢獻 |
|---|---|---|---|
| `TestR87TheMeterMayNotDropAThrottlingAxis` | 104 → **78**（−26） | `selfcontained` → `prose` | +78 |
| `TestR87AccountPostureIsKnownBeforeDispatch` | 47 → **44**（−3） | `selfcontained` → `prose` | +44 |
| `TestR89UnknownKindsAreLoudButNeverReclassified` | （新增）→ 35 | — → `prose` | +35 |

三塊的**行數合計** 151 → 157（**+6**），而**桶的讀數** 0 → 157（**+157**）。

### 機制（為什麼會這樣）

`_FROZEN_SHRINK_ONLY_BUCKET_LINES` 的歸屬基準是 **chunk 粒度的 `exclusive`**：一塊裡只要
出現**唯一一棵樹**的路徑 token，整塊的行數就全額計入那一桶。上面三塊在 HEAD 時**一個路徑
token 都沒有**（`selfcontained`＝未歸屬殘差、刻意不受 shrink-only 判準）；R89 前段包做
「搬史料」時，依規在原處留下一行指標——而那行指標寫的是
`docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`，於是三塊各獲得**恰好一個** `prose`
token，整塊 78／44／35 行一次全額灌進 `prose` 桶。

⇒ **棘輪指定的正解（把史料搬出散文、原處留一行指標），在「原本零路徑 token 的塊」上會
讓 shrink-only 桶當場上升，且上升幅度與搬走多少行無關、只與那一塊有多大有關。**
本例的比例是 6 行的實質變動換來 157 的讀數變動。

### 本窗口的處置（不改判準、不重釘、照棘輪自己指定的出口走）

沒有動 `_FROZEN_SHRINK_ONLY_BUCKET_LINES`（那是重釘，棘輪明文說要帶四方複審），也沒有動
分桶判準或 `BUCKET_TREES`（那會是「為了讓紅變綠而改判準」）。走的是棘輪自己列的第三條
出口：**把 `tools/tests/` 內已歸在 `prose` 桶的塊裡、屬於「哪一輪發生過什麼／實測數字多少」
的史料，逐段遷入本檔，原處只留判準與判準的理由。**逐段清單見下一節。

### 🔴 留給下一輪的判斷題（本窗口不處置，只登記）

分桶棘輪今天無法區分這兩件事，而它們的治理意義相反：

1. **真的多了守散文的鎖**（該紅）；
2. **既有的鎖引用了一份文件**（本例；被引用的還正是「史料搬遷的目的地」本身）。

②的代價不是理論值。本窗口的實帳（皆為當回合實測）：

| 量 | 值 |
|---|---|
| 三塊的實質行數變動 | **+6** |
| 分桶棘輪因此報出的成長 | **+157** |
| 為壓回綠而真的刪掉的史料行（只計「刪除前後都仍歸在 `prose`」的塊，排除任何歸類跳動） | **−110** |
| 被動到的鎖檔支數（史料搬遷） | 14 支，全部與那三塊無關 |
| 護欄層總行數 | `83670 → 83578`（**−92**） |

那些刪除本身是有價值的（史料本來就該住證據檔），但**觸發它的訊號是假的**，而
「下一次同樣的事再發生時，最省力的滿足方式是不要在測試檔裡寫出證據檔的路徑」——那與
搬遷體例直接抵觸。

🔴 **本窗口實際踩到的兩次反向artefact，一併記下來當證據**（都不是刻意的）：
① 把 `TestTheFalsePositiveCensusIsRerunnable` 的「根 CLAUDE.md 鐵律五自陳…」壓縮掉之後，
該塊失去唯一的 prose token ⇒ 整塊 74 行一次退出 `prose` 桶（**−74 的假減法**，2 行的實質
變動）。已把該句還原（它是判準的理由，本來就不該搬）。
② 同型的第二次發生在 `TestScanTarget`（`ONBOARDING.md` 那個字面），同樣已還原。
⇒ 這個桶在**兩個方向**都由「一個 token 決定一整塊」主導，量到的東西不是行數變化。

可考慮的形狀（**未實作，需四方複審**）：把「指標行單獨形成的 prose 歸屬」比照
`reference_counts()` 對 `self_name` 的既有處置（該處已有先例：每支檔都寫得出自己的名字，
若計入會讓 `guard_self` 桶恆真而失去鑑別力）。

### 本窗口做了什麼、刻意沒做什麼

**做了**：①上述 14 支鎖檔的史料搬遷（判準、判準的理由、反例說明**一行都沒搬**）；
②`test_quota_policy.py` 的完整路徑指標收斂成**檔頭唯一一處**，其餘三處改用**同一支檔內
既有的短指稱**（該檔在本輪之前就同時存在四種寫法，其中 `TestM5EveryScanSurfaceIsGatedHard`
與 `test_the_incident_payload_...` 用的正是短指稱）⇒ 那三塊回到 HEAD 時的歸屬。
完整路徑仍在檔內、且在最容易找到的位置，可發現性未降。

**刻意沒做**：未調高 `prose` 桶上限或任何門檻；未重釘 `_FROZEN_SHRINK_ONLY_BUCKET_LINES`；
未改 `BUCKET_TREES`／`GUARD_BUCKET_RATCHET_BASIS`／任何分桶判準；未刪任何判準或其理由。

---

## 護欄層史料搬遷（R89 收尾窗口批）

**規則同上一批**：原文逐字遷入本節，來源處只留「判準 ＋ 判準的理由 ＋ 一行指標」。
下列每一段的來源都是**當時已歸在 `prose` 桶**的塊，因此每刪一行就是桶讀數減一。

### 來源：`tools/tests/_platform_helpers.py::copy_functional_interpreter`（docstring）

```text
真實 Windows 機器踩到的落差（tools/tests 首次真跑於本機 venv-launcher
佈局才顯形，Mock/CI 環境不重現）：Windows 上（尤其 uv/`python -m venv`
建立的 `.venv/Scripts/python.exe`）sys.executable 常是依賴同層
`pyvenv.cfg`（記錄 `home=` 指回真正安裝目錄）才能運作的轉導 stub，並非
完整直譯器本體；只複製這個 exe、不帶走 pyvenv.cfg，會得到一個檔案存在
但 subprocess 執行 rc=106（"No pyvenv.cfg file"）的壞掉直譯器，讓本應
測「健康」情境的測試誤判為「不健康」。一併複製 pyvenv.cfg（若源頭存在）
並維持同層相對位置（dest 上一層），讓複製後的直譯器仍可正確解析 home=。

R21 四方一審（Architect/SA/SD/QA）追加（DEF-101-256）：當 sys.executable
本身**不是**透過 venv 執行時（任何未啟用 venv 的官方支援直譯器安裝
路徑皆會命中同一情境——pyenv-win、winget／python.org 安裝器版型，見
ONBOARDING.md §1；uv 管理的直譯器因走上面 pyvenv.cfg 分支已被涵蓋），
複製出的直譯器旁邊沒有同層相依 DLL（`python3*.dll`／`vcruntime140*.dll`），
在 Windows 上啟動會因 STATUS_DLL_NOT_FOUND（0xC0000135）失敗
（rc=3221225781）。修法無條件（不做任何 `if is_windows()` 平台分支）
從 exe 本身同層 glob 具名 DLL pattern 並複製到 dest 同層——macOS/Linux
上 sys.executable 同層通常沒有 `.dll` 副檔名檔案，glob 自然空手，本身
即是安全的 no-op，三平台行為天生一致，不需要平台條件判斷（避開
R19/R20 QA 抓到過的「條件分支寫反/從未真正執行卻沒人發現」風險形態）。
刻意使用具名 glob pattern（非裸 `*.dll` 全複製）避免誤複製到
sqlite3/libssl/tcl-tk 等不必要的 DLL（增加 I/O 與被鎖檔風險）。
```

### 來源：`tools/tests/test_dev_start.py::TestMacNightlyPlistCapabilityTable`（兩支 docstring）

`::test_healthy_plist_passes_every_capability_row`：

```text
🔴 R82：「健康」在本測試裡是**兩個自變數**，不是一個。能力表混了兩種輸入——
大多數列讀 plist **檔案內容**（`install_healthy_plist()` 全權控制），
WakeToRun／NextRunTime 兩列讀 `pmset -g sched` ＝ **這台機器的電源排程狀態**
（需 sudo 才排得起來，安裝器刻意不代跑）。修前只設了前者就斷言「每列皆 ✅」，
等於偷偷把「跑測試這台 Mac 剛好排過 pmset repeat」寫成前提；那是多數 Mac 的
**非**常態 ⇒ 本測試在真 mac 上結構性必紅，而在 Windows 上被 class 的
@skipUnless(darwin) 跳過所以沒有人看見。夾具的 pmset stub 把第二個自變數也
收進測試手裡，兩列因此**留在**斷言內（沒有被拿掉、沒有被放寬成允許 ⚠️）。
```

`::test_status_prints_exactly_the_rows_static_extraction_predicts`：

```text
R72：跨平台對稱斷言（mac 列數 ≥ Windows 列數）已搬到
`test_schedule_capability_parity.py::TestScheduleCapabilityParity::
test_capability_row_count_reaches_windows_side_parity`——那是一道兩側都只讀
原始碼的靜態鎖，不需要 Darwin，卻因為住在本 darwin-only 類別裡而在
Windows／Linux 三道閘門上一律 SKIPPED。

🔴 R82：②「每一列都是 ✅」同樣吃兩個自變數（plist 檔案內容 ＋ 機器的 pmset
排程狀態），理由與 `test_healthy_plist_passes_every_capability_row` 逐字相同，
夾具的 pmset stub 已把後者收進測試手裡。③ 不受影響——它比的是列**數**，
兩列的值是 ✅ 還是 ⚠️ 都算一列。
```

### 來源：`tools/tests/test_smoke_ci_sync.py::TestSmokeCiSync`（三支 docstring）

`::test_min_pass_equals_actual_step_count`：

```text
DEF-101-243①：$MinPass/MIN_PASS 釘選值本身須等於腳本實際會執行到的
PASS 步驟數，而非只交叉比對「文件宣稱＝腳本釘選」（上方
test_onboarding_pass_claims_match_script_pins 只鎖這一半）。QA 二審
bug-injection 證實：只改錯釘選值本身、步驟仍在，既有測試不會變紅。

兩腳本「原始碼字面 pass/Pass-Item 呼叫次數」與「實際執行到的步驟數」不
直接相等：
- macos_smoke_local.sh 有互斥分支（case/if-else 兩條路徑各呼叫一次
  pass，實際執行恰命中其一），字面數比實際數多。
- windows_smoke_local.ps1 有共用函式（Test-InstallRoundtrip /
  Test-WorktreeReject）被呼叫多次、函式定義內只有 1 個 Pass-Item 字面
  出現，字面數比實際數少。

通用剖析器精確歸納這兩種語意風險高（易在未來改版時悄悄算錯、製造假的
安全感），改用顯式登記表 + fail-loud 存在性檢查（同 R19 修復包 A
test_known_consumers_detected() 精神）：登記已知的「字面數與實際執行數
不一致」樣式，明確列出其原始碼錨點；錨點消失（訊息被改寫/函式改名）即
讓本測試紅，逼人工重新核算並更新登記表。
```

`::test_exclusive_pass_groups_are_genuinely_branch_separated`：

```text
DEF-101-246⑤／DEF-101-247④（R19 QA 二審提案，R20 落地）：
`_SH_EXCLUSIVE_PASS_GROUPS` 顯式登記表本身完全信任人工登記——R19 QA
bug-injection 證實：在 macos_smoke_local.sh 插入兩個實際非互斥、但謊報
登記進登記表的假互斥 `pass` 呼叫（連同同步竄改 MIN_PASS 與 ONBOARDING
排除交叉訊號），test_min_pass_equals_actual_step_count 仍全綠。
```

`::test_bash_n_scan_surface_matches_root_infra_ci`：

```text
R56 新增（Architect round 3 建議的治本鎖）：`root-infra-ci.yml` 第 1 道
（bash -n）與 `macos_smoke_local.sh` [1/7] 是兩份手寫實作，兩者自述「同一份
git ls-files 清單、同一套判準」，但此前零機械互鎖——R56 一輪之內就連續發生
三種漂移：CI 擴面而本地沒跟上、下限釘選值訂在被凍結版稀釋的總數上、本地
少了 CI 有的引號防護。
```

### 來源：`tools/tests/test_check_defect_log_crossref.py::TestMain::test_a_legal_first_word_can_no_longer_land_in_the_vague_soft_exit`

```text
🔴 B5 / SA-R60R3-07：`partial` 這條軟出口已關閉（本測試是舊測試的**繼承者**）。

舊測試 `test_main_separates_vague_rows_from_valid_count_and_does_not_fail` 拿
`partial@R60（降級出口）` 當「含糊但首詞合法」的 fixture —— 而**那個 fixture 本身
就是缺陷**：`partial` 是《格式定義》宣告的合法首詞，卻沒有任何分類器對應，於是
`_classify` 回 None、該列落進 `main()` 的「狀態含糊」桶，而含糊**只印 warning、
永不 fail**。DEF-101-556 要消滅的「只修一半被當成已修」並沒有消失，只是從
「靜默算 fixed」搬到「靜默算含糊」。
```

### 來源：`tools/tests/test_doc_loc_baseline_freshness_r60.py`（六處 docstring）

`::TestLockedLineProseIsAlsoManaged`：

```text
四方複審 round 2 **全部四位獨立命中同一根因**（ARCH-R60R2-03／SA-R60R2-02／
SD-R60-R2-03／QA2-R60-02）：round 1 落地產生器後，受鎖行的 token 已回填為當輪
實測值，而**同一行的散文仍留著同輪的較舊宣稱**。⇒ 產生器 ＋ `--check` 只保證
「被抽取的那個 token」新鮮，不保證同一行的散文新鮮。

🔴 **正樣本刻意用「真實缺陷的逐字形態」**（比照本 repo 既有慣例：以真實語料當守門
樣本）——`R60=756` 這串就是 round 2 四方在 ONBOARDING.md:216 抓到的原字樣。
```

`::TestR67CliFailsLoud`：

```text
WHY：原版 `"--flag" in argv` 手搓解析，未知旗標一律靜默掉進 default 分支並 rc=0。
實測後果（Scan-D 於乾淨 clone 注入真實過期後）：正確拼法 rc=1，少打一個字母 rc=0
**假綠**——同一棵工作樹、同一時刻，該紅的守門回綠燈。而 `--check` 這個被 ONBOARDING
§7、`CrossPlatform_Scan_Dimensions.md`、`ADR-XPLAT-002` 三份文件引用的旗標，在 R67
之前**根本不存在**，只是恰好掉進 default 分支才「看起來對」。

修法選「把 `--check` 實作為真旗標」而非「改三份文件」：那三份文件有兩份不在本包授權
範圍內，且「產生器 ＋ `--check`」本就是本 repo 既有慣例（`snapshot_sync.py`）——讓字面
成真比讓三份文件改口更小、也更對。
```

`::test_documented_flags_all_exist_in_the_parser`：

```text
未覆蓋面（如實揭露）：散落在**不提工具名**之行上的旗標，例如
`CrossPlatform_Scan_Dimensions.md`／`ADR-XPLAT-002` 的引用——那兩份不在本包授權
範圍內，本輪改以「把 `--check` 實作成真旗標」讓它們的字面成真，而非改它們的字。
```

`::_slow_window_sandbox`：

```text
為何要沙箱：這條路徑會**寫 ONBOARDING.md** 並實跑分鐘級量測。以 tmp 目錄替換
`_REPO_ROOT`／`_ONBOARDING`、以確定性 stub 替換兩支慢量測器之後，同一條生產程式碼
可以在毫秒內被完整驅動，且真實 repo 的檔案全程唯讀。

平台亦是沙箱的一部分（R67 round 3）：`current_platform_key()` 被釘成
`_SANDBOX_PLATFORM`，理由見該常數上方。帶參數呼叫仍走真實實作，才不會連帶蓋掉
`current_platform_key("linux")` 這種顯式查詢的語意。
```

`::TestR67SlowMeasurementWindowIsFingerprintBracketed`：

```text
WHY 這道鎖必須存在（Rule 9：測 intent 不只測 behavior）：
  表② 之所以敢在沒有 live 鎖的情況下被信任，**全部理由**就是
  `snapshot-fingerprints-<平台>` 錨那一句「這一欄的數字是在**哪一棵測試樹**上量的」。
  而回填路徑原本是「先跑分鐘級慢量測、**跑完之後**才取指紋」⇒ 樹若在窗口內被改動，
  錨記下的是一棵**從未被量測過**的樹，四格計數卻留在改動前的樹上。
  事後 `--check-snapshot` 量到的 live 指紋與錨相符 ⇒ ✅ rc=0，而計數已 stale。

活體證據（R67 收尾 Scan-H）：BASELINE 包寫入的 macOS `scripts/tests` 格是 253、
收尾包在同一棵樹量到 259，而 `snapshot-fingerprints-darwin` 的 `scripts=` 前後
**完全相同** ⇒ 那條錨當時正在為一組對不上的計數背書。
```

`::TestR78HandoffClaimsCarryLiveCommands`：

```text
🔴 為何是體例而不是兩個個案：R78 收到的兩筆 finding 是**同一個形態**——
  · 「30 支 tag 尚未推送」：R78 開場實查，遠端 30 支都在（`git ls-remote --tags`）。
  · 「Windows nightly 缺 root_unittests」：R77 自己在同一輪已把它併進 STAGE-L，
    照原文再加一次的代價是每晚多跑一次 260〜313 秒的全套。

🔴 R82 Q4-01 修的兩個縫（兩個都讓本鎖在**看起來全綠**的狀態下失去射程）：
  ① 取材面只收 list item ⇒ R81 交棒書（§3 全是散文＋fenced code）整份 **0 命中**；
  ② 反崩塌斷言跨文件加總 ⇒ R79 那 7 筆把總量永久撐 ≥1，最新一份掉到 0 打不出來。
```

### 來源：`tools/tests/test_block_destructive_git_r83.py`（三處 docstring）

`::TestTheRelaxationOpensNoNewHoles::test_the_filesystem_root_contains_the_project_too`：

```text
WHY 它躲得過上一支測試：包含判準原本寫 `p + os.sep`，而檔案系統根的
`"/" + "/"` ＝ `"//"`，**沒有任何路徑以 `"//"` 開頭** ⇒ 反向包含在
`target == "/"` 這一格恆假，`cd / && git clean -fdx` 實測被放行（rc=0）。
`cd /Users …` 那一級擋得住，所以整條前提 ②「與專案根互不包含（雙向）」
讀起來完全成立——這正是本 repo 反覆判紅的「鎖在、但某一格沒有鑑別力」，
而它只有把根這一格真的送進去才看得見。
```

`::TestR84StashRefSentinel`（class docstring）：

```text
本守衛只讀指令字串 ⇒ 這四條路它結構上碰不到：MCP git 工具（不是 Bash 呼叫）、
別的 session、**寫在 `.py` 檔裡**的 `subprocess`（工具面只看得到 `python foo.py`）、
別名與殼函式。加判準對它們一行都沒用 ⇒ 只能改成「事後一定看得見」。

（第一版一起看 `logs/HEAD`，已否決——每次 `git commit` 都會變 ⇒ 常駐亮燈，
  而常駐全亮的燈等於沒有燈。）
```

`::test_a_stash_the_guard_already_saw_is_not_reported`：

```text
🔴 R84／SD-04 訂正本 docstring 的兩處假事實：ack **不是**「指令字串裡出現 stash」
（子字串判定會被 `grep -rn stash docs/` 點亮 ⇒ 下一次真 drift 靜默、而且 head 已被
改寫成新 SHA ⇒ **永久吞掉**），也**不含**「被擋」與 `stash create` 這兩種——被擋的
指令根本不會跑、`stash create` 一個字節都不動那個 ref，兩者都解釋不了任何變動。
```

### 來源：`tools/tests/test_archive_defect_log.py::TestCriterion2VerbatimQuoteTailMask`

```text
立案實測（R76 動工時對主檔現查）：20 筆列**只**被判準② 一項擋著、合計 69,113 bytes
＝主檔的 29.3%，其中 15 筆命中的字樣全部落在這一族慣用語之後的引文裡——那段文字的
用途正是**宣告該狀態已不成立**，判準② 卻把它讀成「還成立」，語意剛好相反。這是
`DEF-101-676`（R68 收窄反引號／角引號）的同型復發，第三種逸出面。
```

### 來源：`tools/tests/test_context_budget_guard.py::SentinelReapVerdictTest::test_reaping_a_sentinel_leaves_an_audit_trace`

```text
`_sweep_artifacts` 把任務書／閂鎖／boot log／水位 state 四件全刪、`_remove_task`
又把排程本體拆掉 ⇒ 少了這一行痕跡，`--apply` 跑完之後的磁碟狀態與「哨兵自己靜默
消失」（判過四次 `arm_reset`、log 某刻起空白、`launchctl` 零命中）**完全同形**，
事後連「是被收掉還是自己死了」都分不出來。根 CLAUDE.md〈反事後諸葛取證規則〉要的
是「沒觸發＝可偵測」，而回收是排程生命週期的另一半——武裝那半一直有痕跡，這半沒有。
```

### 來源：`tools/tests/test_onboarding_parity_interlock.py::TestOnboardingSelfSectionRefsResolve`

```text
WHY：R69 實測 §6.1 的 `root-infra-ci.yml` 列寫著「逐輪覆蓋沿革見 **§9.1 逐輪平台覆蓋表**」
——而本文件從來沒有 §9.1。那句話是在同一輪把別處改寫成「指向 live 來源」時寫下的，
指路句本身卻指向不存在的地方；讀者按圖索驥找不到東西，只會退回猜測，比不指路更糟。
同型判準 `ADR-XPLAT-002` §8 item 14 (d)（內部交叉引用必須解析得到）早已寫成規格，
但射程只到那兩份 ADR，本文件不在內——本鎖補上這一半。
```

### 來源：`tools/tests/test_skip_discoverability_r83.py::TestPgSkipRemedyStaysDiscoverable`

```text
R83 實測（macOS，同一棵工作樹、同一支直譯器）：
  · `AUTOCLAUDE_NO_PG_AUTODETECT=1 pytest tests/ -q` → 172 skipped
  · 容器 healthy、零程式改動零環境變數 → 76 skipped
⇒ 96 支 skip 的全部成因就是「容器沒起來」，而這件事在 R83 之前於
`ONBOARDING.md`／`useMacWin.md` 兩份 onboarding 文件裡**一個字都找不到**
（只寫在 `AutoClaude/docker-compose.ci.yml` 檔頭——那是已經知道要找它的人才會開的檔）。
```

### 第二批來源（同一批搬遷，逐段原文）

`tools/tests/test_block_destructive_git_r83.py::TestR84TheArgvPlaneDoesNotOverBlock`：

```text
普查（可重跑）：母體＝`~/.claude/projects/**/*.jsonl` 的 `tool_use` 指令字串
**42,387 筆、去重 39,739 種**；新判準把命中由 252 → 257（新增 5），逐筆判讀
**1 筆真陽性（原凶本身）＋ 4 筆是本次鑑識自己寫的探針**（把危險形態當資料寫出來），
且**舊擋新放 0 筆**（沒有任何既有守備被這次改動換掉）。
```

同檔 `::TestQuotingAndHeredocAreInert`／`::TestTheRelaxationOpensNoNewHoles`（class docstring）／
`::TestTheCriterionItselfCanFail::test_the_old_prefix_writing_is_pinned_as_a_tombstone`／
`::TestTheFalsePositiveCensusIsRerunnable::test_the_census_surface_is_the_transcripts_not_tracked_files`：

```text
上一代姊妹守衛在這裡誤擋過（SD-02 實測三條規則全中），修法是「先把不是可執行
結構的區段拿掉再比對」——本類是那個修法在本檔的回歸鎖。

複審者的警告逐字：「只看『cwd 不在專案根』就整條放行，會不會製造新的漏擋？」
本類就是那個問題的答案，逐條列舉並釘死。

這一支的存在理由與上面三支不同：它守的不是「判準會不會恆真」，而是
「**已知會漏的那個寫法不准回來**」。獨立驗證輪實測 `cd / && git clean -fdx`
在舊寫法下 rc=0。

實測（本輪）：tracked 面上 `waitform` 的命中**全部落在描述這兩種形態的 `.md`
散文與本判準自己的 docstring**，而 hook 結構上讀不到 `.md` ⇒ 照 tracked 面判會
得到「全是假紅」的錯誤結論並否決一個好判準。
```

`tools/tests/test_check_defect_log_crossref.py`（`::TestScanTarget`／`::TestMain`／
`::TestCurrentRoundIsReadofFromTheLedgerNotHardcoded`／`::TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound`）：

```text
回歸鎖：曾因 _CLAIM_RE 括號內容量詞硬性上限 {0,150} 導致超長度的真實宣稱被靜默跳過
比對，複審實測 ONBOARDING.md DEF-101-057 的括號內容達 186 字元，工具因此完全沒抓到
該筆宣稱，帳本狀態即使被刻意改成與文件矛盾也不會被回報。

R10 QA-9 回歸鎖：archive 檔 ≥ 256KB 必須 fail——R9 補的 archive glob 迴圈先前零測試
覆蓋（fixture 目錄天然無 archive，迴圈從未被驗證會紅），glob pattern / parent 路徑被
改壞時主檔測試仍綠、DEF-99-001 政策的一半守門無聲失效。

兩套編號**不是同一個東西**：整合迭代輪（`AutoSDD_improving_NN`）與跨平台複審輪
（`R\d+`）各自獨立累積。若拿前者當「當前輪」，帳本裡每一列的承接輪號都會遠小於
它 ⇒ 整本帳本瞬間全紅。

`DEF-101-765` 實測：當前輪被推成 72 時 `DEF-101-752` 立刻被誤判為孤兒 backlog、rc=1。
```

`tools/tests/test_ntfs_trailing_space_device_name.py::TestRootDocsPathRefsAreCaseExact::test_the_three_r67_a15_citation_sites_resolve_exactly`：

```text
🔴 R72 訂正：清單裡的**站點路徑**原本寫死在上層（`docs/04_planning/
AutoSDD_improving_54.md`），而該檔本輪依歸檔慣例搬進了 `Archive/`
⇒ `read_text()` 當場 FileNotFoundError。這正是本 repo 反覆在治的
「會過期的站點」：鎖以為自己在守引用，其實還多守了一個檔案位置。
改為經 `resolve_doc_ref()` 解析——清單指名的是**文件**，不是它今天住哪。
```

`tools/tests/test_doc_loc_baseline_freshness_r60.py`（四處）：

```text
WHY 這支要單獨存在（R67 round 3）：同輪把沙箱的平台**釘死**在受管欄上，才能讓
窗口鎖在三個 host 上跑同一件事；那個釘死同時把「無欄平台會怎樣」擋在射程外。
而那條分支正是 R67-D1 的最後一道。

落地首版的正則寫成 `…true\s*$`（行尾不得有東西），而 YAML 最普通的寫法就是
`continue-on-error: true  # 理由`——磁碟上當時就有一個（`autoclaude-pg-e2e-on-label.yml`）。

🔴 這一條就是 R82 Q4-01 的驗收：R81 交棒書當時整份 0 命中，而跨文件加總被
R79 的 7 筆永久撐綠。

🔴 WHY fail-loud 而不是沿用「取最後一個」（R75 落地當回合被自己咬到，實測取證）：
原版是 `dict(_CLOUD_FIELD_RE.findall(...))`，而錨是**單獨一行**、機器欄位與人讀散文
同住那一行。我為了說明 pending 的用法，在同一行散文裡寫了一個 `pending=<sha>…` 字樣，
它就**靜默覆蓋**掉真正的欄位值，判準於是拿一個帶省略號的字串去比 sha ⇒ 假紅，而錯誤
訊息還印著一個看起來正確的值（`pending=a371068…` vs `origin/main=a371068448a5…`
——兩者其實是同一個 commit）。
```

`tools/tests/test_doc_env_prefix_platform_parity_r60.py`／`test_check_hooks_liveness.py`／
`test_pre_commit_dispatcher_sigpipe.py`／`test_check_pytest_baseline_sites.py`：

```text
🔴 R83：`useMacWin.md` 加入本清單——該檔新增 ONBOARDING §7.1 的最短路徑
（`AUTOCLAUDE_DB_DSN=… alembic upgrade head`），同檔已附 PowerShell 對照，
故 `test_live_docs_have_powershell_counterpart` 仍綠；本清單只是庫存盤點。

這一維是上一版鎖缺的那個：字面同步、行為在 gap 0 也一致，但兩邊的**視窗**
長度不同 ⇒ gap≥1 的多行指令在量測端整類看不見。低報的方向看起來像「變乾淨」，
而那個數字是拿來寫進根 CLAUDE.md 下結論的。

WHY：舊實作是裸 `str.startswith(prefix)`，於是與白名單目錄**同前綴的另一個目錄**
會被整片收下。本輪實測改前逐字：`is_allowed_md('docs/06_qualityEXTRA/a.md')` → True。

R13 README 漂移實證的原始形狀：badge 內數字與 SSOT 並立且無空格分隔，
判準（passed 子字串＋≥4 位整數）須對此天然有效。

WHY：與同輪 encoding-ok（空 WHY 無豁免力）及 parity「豁免必附 WHY」紀律
一致；否則「防豁免濫用」宣稱在零 WHY 情境失效。
```

---

## 護欄層史料搬遷（R89 放行條件收斂批）— QA 複審 C1 的補遷

**為何有這一節**：R89 收尾自 `tools/tests/` 刪了 537 行（20 支檔），前面三批只遷入了其中
一部分。QA 複審 C1 以「去空白／去引言符」的寬鬆比對量出約三成的實質史料在本檔中找不到，
且其中數段**來源處已留下指標**（「史料＝R89 收尾證據檔」）⇒ 那些指標指向不存在的節。
本節按 QA 給的選項 (a) 處置：**把缺的史料真的補進來**，讓既有指標變成有效指標。

**體積前提（動筆前現查，不是宣稱）**：具名治理文件的體積上限與帳本共用同一條物理界線
（`check_defect_log_crossref.py` 的 `_LEDGER_WARN_BYTES = 240 * 1024`／
`_LEDGER_FAIL_BYTES = 256 * 1024`，出處＝Read 工具單次讀取上限）。本檔補遷前 94,460 bytes
⇒ 餘裕約 167KB，**本節全數走選項 (a)，沒有任何一段因體積改走選項 (b)**。

🔴 **本節的判讀邊界（誠實劃界）**：QA 的 32.5%／本輪複量的 37.6% 都是**寬鬆比對的上界**，
不是真實遺失率——分母含大量「被改寫而非被刪除」的行（同一句話換了措辭仍住在原處）、
純程式碼行（fixture 換軸、斷言換面）、以及每輪都會動的基線常數重釘。逐行判讀後，
真正「史料不見了且沒有第二個家」的是下列各段。**判讀腳本可重跑**：
`/private/tmp/.../audit_lore.py`（一次性探針，刻意不進 repo——它比對的是工作樹 vs HEAD
的暫態差異，進了 repo 下一輪就恆綠＝又一個假鎖）。

**補遷前後的複量（同一支探針、同一套判準）**：`37.6%`（186／495）→ **`16.4%`（81／495）**。
殘餘 81 行**逐行判讀後全部是寬鬆比對的假陽性**，分三類、無一是史料損失：
① `test_adr_xplat001_c1c2_lock.py` 那 24 行是逐檔行數基線與 `_REPIN_*` 常數；
② `test_doc_loc_baseline_freshness_r60.py` 那 24 行絕大多數**仍住在來源檔內**（改寫時縮排／
措辭變了，比對器對不上，但知識沒有離開）；③ 其餘是被引號／逗號包住的符號名與 `assert` 程式碼行。
⇒ 這個殘值**不應該再往下追**：把它壓到 0 的唯一辦法是連程式碼與常數一起抄進本檔，
那會製造一批「同一份知識住兩個家」的複本，正是本 repo 反覆判紅的病。

### 來源：`tools/tests/test_quota_policy.py` 檔頭 ＋ `TestM5EveryScanSurfaceIsGatedHard` 上方註解

**這一段是 QA 點名的第一筆具體損失**：M5 那五組沙箱注入的**逐項結果**——它是「舊鎖恆綠」
這個判決的唯一證據，摘要成「五組注入全綠」五個字之後，讀者無從知道是哪五組、注到哪裡去。

檔頭原文逐字（遷出前）：

```text
  · ✅ **M5 靜態半的三個掃描面已於 R82／C4 全數轉成硬 gate**（見
    `TestM5EveryScanSurfaceIsGatedHard`）。此處原本記載「本包只 gate 得動第一個、
    其餘兩面留待下一階段」——那段劃界在當時是誠實的，但它被留在原地整整一輪，
    期間複審鏡以沙箱注入實測**五組全綠**（worst() 放回 gate／meter、fanout_cap(pct)
    放回 gate 與 AutoClaude adapter、quota_tier_of(pct) 放回 hook）。
    現在四個面逐檔硬判，並附「注入真檔內容後必須翻紅」的端到端自證。
```

`TestM5EveryScanSurfaceIsGatedHard` 上方註解原文逐字（遷出前）：

```text
# 🔴 R82／C4：把「三個掃描面」從**列舉**升成**硬 gate**。
#
# 病（複審鏡以沙箱注入實測，每次跑全套）：`QC.worst_mentions`／`QC.scalar_decision_defs` 兩個
# 判準只對 `_MODULE_SRC`（＝`quota_policy.py` 自己）斷言，於是
#   worst() 放回 quota_gate.py → rc=0 GREEN；放回 quota_meter.py → rc=0 GREEN；
#   fanout_cap(pct) 放回 quota_gate.py → GREEN；quota_tier_of(pct) 放回 hook → GREEN；
#   fanout_cap(pct) 放進 AutoClaude adapter → GREEN。
# 五組注入全綠。`_M5_SCAN_SURFACES` 當時**列了**三個面，但那一條只 `assertIsInstance(...,
# list)`＝「解析得動」，不是「乾淨」；而那支「確認掃描器擋得住活標的」的測試（同輪一併
# 刪除，名字刻意不用反引號寫出來——它已不存在，寫成反引號就是新的幽靈引用）
# 用的是 `if 定義還在: assertIn(...)` ⇒ 定義不在就整條沉默，**結構上不可能失敗**。
# 「掃描面列出來了」與「掃描面被判了」是兩件事，前者讀起來很像後者。
#
# 現在的判準：三個面（＋ AutoClaude adapter 那一面）**每一支檔**都必須同時
# `QC.scalar_decision_defs == []` 且 `QC.worst_mentions == []`。今天全部為空（落地當回合實測），
# 所以這不是「登記存量」而是「不准有人放回去」。
```

判準本體搬家（`tools/lib/quota_criteria.py`）的兩條理由，原文逐字：

```text
# 🔴 判準本體（M2／M5／M7／M10 ＋ R86 三缺陷）住 `tools/lib/quota_criteria.py`，本檔只留
# 「呼叫判準 ＋ 斷言」。理由兩條同時成立，見該檔檔頭：① 它們不依賴 unittest，是對源碼／
# 讀數的純判定；② `tools/tests/*.py` 受護欄層行數棘輪管，判準留在這裡會逼別包去砍別的
# 東西來抵。**鑑別力不得下降**：搬家後全部合成注入自證已重跑，結果與搬家前逐字相同。
```

### 來源：同檔 `TestR87TheMeterMayNotDropAThrottlingAxis` 的三支測試（`cap=1` 地板拆除的連帶）

`::test_the_incident_payload_still_carries_both_axes_end_to_end` 內被拆掉的那條斷言
與它的理由，原文逐字：

```text
        # 🔴 保險軸撞頂 ⇒ cap 夾到 1（不是 0、也不是 C_max）。理由見 `decide()` 內
        # 那段 B-2：n=1 的成功探針不足以解釋 R87 的 13/13 全滅，殘餘風險收斂成 1 個。
        self.assertEqual(d.cap, 1)
```

`::test_the_lock_discriminates` 的 docstring 與反向斷言，原文逐字：

```text
"""合成注入自證：**重演** R87 那個錯誤實作，必須被抓到。

🔴 R89：判準隨上一支一起換面。舊版斷言「重演組必須不再 halt」，而正確實作
現在**也**不 halt ⇒ 該斷言已恆真（Architect 實測四欄逐字相同）＝假鎖。
新判準指向 R87 真正的差異：**軸在不在**。
"""
        # 正確實作與錯誤實作在**這個**觀測面上必須不同（上一支守正向，這裡守反向）。
        self.assertNotEqual(d_broken.cap, 1, "掉軸之後 cap 若仍是 1，本鎖無鑑別力")
```

`::test_disabled_is_not_a_reason_to_drop_an_axis` docstring 原文逐字：

```text
"""`enabled:false` 這個欄位本身**不得**成為排除依據。

判準刻意寫成「同一份 payload、只把布林翻成 True」的對照：兩者收到的軸集合
必須**逐字相同**。若哪天有人再以 `enabled`／`is_enabled` 當過濾條件，
這一條會當場紅——而它是這次事故裡唯一被動過的那一行。
"""
```

`::test_the_fingerprint_is_the_axis_set_not_a_plan_name` docstring 原文逐字（**含實測值
「17 個頂層鍵」——那是「payload 沒有方案名」這個宣稱的唯一憑證**）：

```text
"""指紋＝軸組合。payload 沒有方案名（實測 17 個頂層鍵無一為方案名），
且它的用途是**偵測方案變更**，不是查一組寫死的參數。"""
```

### 來源：同檔 `TestR89TheFallbackSetMayNotSwallowASubscriptionAxis` 的舊黑名單判準

判準由黑名單翻成白名單時被換掉的舊常數與舊斷言，原文逐字（舊常數本身以
`OLD_BLACKLIST` 之名留在檔內當對照組，但**兩條斷言與那則「兩個家」註解已不在**）：

```text
    #: 訂閱窗那一族——它們**永遠**不是保險池，被吞掉即等於關閉主節流。
    SUBSCRIPTION = frozenset({"session", "five_hour", "seven_day", "weekly_all"})

    def test_no_subscription_axis_is_ever_a_fallback_axis(self) -> None:
        """三條一起：不得吞訂閱軸／保險集只有一個家／訂閱軸撞線仍然 halt。"""
        self.assertEqual(Q.FALLBACK_KINDS & self.SUBSCRIPTION, frozenset(),
                         "訂閱軸被列為保險池＝主節流被關掉，而這是唯一會叫的地方")
        # 🔴 同一份知識住兩個家（`FALLBACK_KINDS` 與 `quota_meter.CREDIT_POOL_KEYS`）
        # 且不准互相 import ⇒ 那個縫只能由判準縫（體例同 pace contract 那對）。
        self.assertEqual(Q.FALLBACK_KINDS, frozenset(M.CREDIT_POOL_KEYS),
                         "保險池清單在 policy 與 meter 兩邊漂移了")
```

🔴 該 `==` 已於 R89 收尾改為子集（SA 複審 B-3），理由見上方〈`FALLBACK_KINDS` 補齊 ＋
鏡射鎖由 `==` 改為子集〉節——此處只保全**舊形態的原文**，不是現行判準。

### 來源：`tools/tests/test_subprocess_encoding_hygiene.py`：`_CHILD_SITE_FLOOR` 的取值依據

🔴 **這一筆是本批唯一「連指標都沒留」的損失**（QA C1 點名）：來源處的註解被改寫成
「值改為當回合實測 × 0.95」——實測值本身被刪掉，於是那句話**不再指向任何數字**，
`45` 這個現值的推導從此無法複驗。原文逐字（遷出前）：

```text
#: 🔴 R75：值改為當回合實測 27 × 0.95（`suggested_floor`），並**套同一條腐化上界**
#: （`tree_count_verdict`）。原值 20 是落地當下 26 筆打八折——那個算法就是 per-tree
#: 下限腐化成 18 vs 81 的同一個算法，差別只在它還沒漂夠久。上界讓它不必靠人記得。
_CHILD_SITE_FLOOR = 35
```

⇒ 完整推導鏈（三個世代）：`20` ＝ R75 之前 26 筆打八折；`35` ＝ R75 當回合實測 **27** × 0.95
（`suggested_floor`）；`45` ＝ R89 當回合實測 **47** × 0.95。三代都是「當回合實測 × 係數」，
**係數在 R75 由 0.8 收緊為 0.95 之後未再變動**。

🔴 **本段今天沒有回指的指標**（來源處是 `tools/tests/`，本輪禁止改動）⇒ 反向索引就是本節
標題裡的檔名。R90 若要動那支檔，順手把「取值依據＝本節」一行補回去。

### 來源：`tools/tests/test_doc_loc_baseline_freshness_r60.py`（三處，各有指標但無對應節）

`::TestR67SlowMeasurementWindowIsFingerprintBracketed` 的量測次數段——來源處指標逐字為
「原版各路徑量幾次＝R89 收尾證據檔」。原文逐字：

```text
        原版 `--check-snapshot` 判決後又重量一次才印 ✅ 那一行、`--json` 更量了 3 次 ⇒
        「印出來的證據」與「判決所依據的」可能是不同時點的樹。這與主缺陷同型（同一個量
        在不同時點被量兩次），且違反 Nightly 取證紀律「取證載具必須就是判決依據」。
```

`ci_liveness` 複本鎖的實測——來源處指標逐字為「當時的實測＝R89 收尾證據檔」。原文逐字：

```text
        R76 之前是兩份逐字相同的複本，於是同一個瞎點有兩個家、修一個不會修到另一個
        （實測：對 windows-compat-ci 那一行加註解，`ci_liveness` 的 run 層 fail-open
        自白會一起啞掉）。`assertIs` 讓「又抄了一份」在下一次就當場紅。
```

巢狀小標題繼承父節射程那一支——來源處指標逐字為「史料＝R89 收尾證據檔」。原文逐字：

```text
        """巢狀小標題繼承父節射程——這是 R79 複審點名、上一版**靜默放行**的那個縫。

        上一版對任何 `##` 以上標題一律重設 `in_section`，於是「待辦」大節底下一個
        普通 `###` 小標題就會把其下所有條目整區踢出射程；本輪 §4 的四個小標題正是
        靠「把觸發字寫進每一個小標題」繞過的。這支測試把繞過換成判準：小標題**不含**
        任何觸發字時，父節的裸宣稱仍必須被抓到。
```

### 來源：`tools/tests/test_context_budget_guard.py`（四處，各有指標但無對應節）

`ContextOnlyRulerTest` 的種快取註解——來源處指標逐字為「實測讀數＝R89 收尾證據檔」。
**這一段是「為什麼那三條靜默斷言在 mac 上會無故轉紅」的唯一診斷紀錄**，原文逐字：

```text
        # 🔴 R83：本類量的是 **context** 那把尺，而接電讓額度那把尺也跑在 PostToolUse 上 ⇒
        # 不種快取時額度軸會在這裡回報「量不到」並出聲，三條「必須完全靜默」當場紅，而**紅的
        # 原因與被測性質無關**：`_isolated_env` 把 `HOME` 指到沙箱、Keychain 讀不到憑證
        # （source=no-credentials-darwin）＝fixture 產物，不是 production 狀態（本機真跑
        # `quota_meter.py --json` 為 session 42%／rc=0）。種一份 free 帶健康快取把被測世界
        # 收斂回「額度正常時，低 context 必須靜默」；斷言一個字都沒放寬（`err == ""` 仍逐字
        # 成立，額度軸若誤出聲照樣紅）。
```

憑證來源雙欄矩陣的輪次考古——來源處指標逐字為「輪次考古（原文逐字）＝……」。原文逐字：

```text
🔴 **R83 訂正本 docstring 原本的「誠實劃界」段（不逐字留著當現行說法）**：那段寫
「`CREDENTIALS` 仍然只有一個來源、零平台分支」，而 R82 同輪就把 darwin 分支落地了
（`access_token()` 的平台分支，見 `git show HEAD:tools/lib/quota_meter.py`）
⇒ 這段自陳從落地當回合起就是假的，且它假在**會讓人以為這裡已經沒有平台問題**的方向。
真正的缺口是另一件事、而且沒有任何東西在守：`measure_detail()` 當時**沒有憑證來源的
注入點** ⇒ 本組只能靠改主機自己的憑證存放處來構造那兩條臂，於是每條臂只在一個平台
成立。mac 真機實測（**R83**＝mac 真機首輪）：把 `CREDENTIALS` 指到不存在的檔，
darwin 完全不讀它 ⇒ 期望 `no-credentials`、實得 `http-401`，該臂在 mac 上結構性量不到。
現在改成**雙欄矩陣**（見 `_CRED_COLUMNS`）：兩個平台的憑證來源在任何一台機器上都跑。
```

哨兵回收的 dry-run 自產缺陷（兩段，來源處指標分別為「史料＝R89 收尾證據檔」與
「實跑數字＝R89 收尾證據檔」）。原文逐字：

```text
        `armed` 一定要在裡面：本輪實跑 dry-run 才發現第一版只認終態，而現實中**每一支
        巡邏中的哨兵狀態都是 `armed`** ⇒ 那個版本對真正要收的東西一支都收不到，
        而它的外觀是「很保守、很安全」。

        """🔴 本輪 dry-run 當場抓到的自產缺陷，釘成回歸鎖。

        第一版把「逐字稿目錄定位不到」（planner import 失敗 ⇒ `_transcript_dir()` 回
        `None`）與「這個 session 的檔真的被刪了」擠進同一個 `False` ⇒ **實跑時三支哨兵
        全被判為可收，包含當下正在跑的那一支**。

        注入的是真實形態而不是合成例外：`planner.append_log` 對寫不進去是**刻意吞掉**的
        （留不下痕跡不得升級成回收失敗），所以「靜默沒寫成」是這條路上真的會發生的事。
        少了這條斷言，`_record_reap` 可以無條件回傳路徑字串而全綠——那就變成「回報說留了
        痕跡，磁碟上沒有」，比完全不留痕跡更難看見（本 repo 對「憑證裡混一句假話」的判例）。
```

`--pace` 人機出口的紅端、以及 R86 那一列的立案畫面。原文逐字：

```text
    """🔴 紅端：`python tools/lib/quota_policy.py` → rc=2 只印用法；
    `quota_meter.py --from-cache --json` → rc=0 但全文無 band／cap／pace／recommended；
    `describe()` 的唯一呼叫端是被擋下時的三個 stderr 寫入點 ⇒ 舵手要拿到那個數字，
    今天唯一的途徑是**先被守衛擋下**。訴求 6a「隨時監控」在人機介面這一側等於不存在。
    """

        """🔴 R86：掌舵者看到「短窗還很空、卻只能派 2 個」時，畫面必須自己回答為什麼。

        他當時看到的只有 `binding=seven_day` ⇒ 讀起來像程式抓錯。同一次呼叫也必須落款
        一列（換算比只能從歷時差分推估）。判準本體＝`quota_criteria.pace_line_problems`。
        """
```

### 來源：`tools/tests/test_block_destructive_git_r83.py`（兩處尾巴）

`TestTheFalsePositiveCensusIsRerunnable` 立案事實的末句、以及 LOC 註解的誠實劃界段，
原文逐字：

```text
    CLAUDE.md 自己已對 R77 的失誤分群下過同一個判決並以 probe 修好；這是同一個修法。

        # 因為 `count_loc` 排除純 `#` 行而計入 docstring ⇒ 同一份 WHY 寫成註解是 0 行成本，
        # 而本包同輪把被守的那支 hook 推到 718/750（`guardrail_cli` tier）。
        # 🔴 誠實劃界（本註解第一版寫錯過一次，故留在這裡）：根層 `tools/` 是**獨立帳**，
        # `check_loc_budget.py` 逐字寫「不進 total／baseline cap」⇒ 那個「全庫 total 只剩
        # 個位數餘裕」的預警**與本檔無關**，不可拿它當本檔的理由。真正咬人的是 tier。
```

### 判讀為「非史料損失」而刻意不搬的三類（誠實劃界，免得下一輪重新「發現」）

1. **基線常數重釘**：`test_adr_xplat001_c1c2_lock.py` 那 24 行全部是逐檔行數基線、
   `_REPIN_NET_CAP_DUE_ROUND`／`_REPIN_NET_CAP_DUE_TARGET`／`_REPIN_LOG_FROZEN_PREFIX_LEN`
   與一個凍結雜湊——它們是**量測值與棘輪常數**，舊值住在該檔自己的重釘紀錄裡，
   搬進本檔等於再開一個會漂移的家。
2. **fixture 換軸的程式碼行**：`spend` → `nimbus_quill` 那一族 `Q.axes_of(...)`／
   `Q.decide(...)`——換軸的理由已逐字在上方〈護欄層史料搬遷（R89 收尾批）〉節。
3. **只換措辭、沒換內容**：多數被寬鬆比對判成「找不到」的行，其實是同一句話在原處
   被改寫（例如「本次 main 三支全紅」→「CI 上三支全紅」）。判定方式是回去讀來源檔的
   **現行**內容，不是只看 diff 的 `-` 側。
