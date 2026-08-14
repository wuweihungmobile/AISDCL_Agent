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

### 鎖與**雙向**合成注入自證

`tools/tests/test_context_budget_guard.py::QuotaPaceOutletIsReachableTest` 新增 3 測。
綠端：`9 passed`（含既有 6 測）。兩個方向的注入各實跑一次：

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
