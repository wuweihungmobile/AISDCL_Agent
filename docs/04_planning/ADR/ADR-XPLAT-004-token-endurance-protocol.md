# ADR-XPLAT-004：Token 額度續航協定（quota endurance）

- **狀態**：Accepted（R79）
- **日期**：2026-08-07
- **取代／被取代**：無。與 ADR-XPLAT-001/002/003 無重疊（那三支管跨平台面，本支管 harness 額度）
- **落地物**：`.claude/hooks/context_budget_guard.py`（純判讀）、`tools/session_resume_planner.py`（CLI／編排）、
  `tools/tests/test_context_budget_guard.py`（回歸鎖）。**本協定新增檔案數＝0**（本 ADR 除外）
  > 🔴 **「新增檔案數＝0」是本協定的自我約束，不是 repo 規則——不要把它讀成硬規則。**
  > repo 的硬規則只有 `DEF-101-561③`「禁新增**鎖檔**（`tools/tests/*`），只准合併／刪除」那一條；
  > 「不新增任何檔」是本 ADR 自己選的（理由見 §3 那一列：`tools/` 新增 `*.py` 會同時污染 ruff／
  > LOC 棘輪／`_script_scan_surface` 三個面）。**同輪其他包並未遵守它**（例如新建了
  > `tools/lib/skip_group_policy.py`、`tools/probe/misstep_attribution.py`、
  > `tools/probe/xplat_injection_matrix.py`），那不是違規。
  > **代價要照實記**：R79 四方複審實測，遵守它讓 `tools/session_resume_planner.py` 一度只剩
  > **1 行**餘裕（`guardrail_cli` 那一格）。複審後修復包用**壓縮表達**收回餘裕（長 WHY 由 docstring
  > 改成 `#` 註解——`count_loc` 計 docstring、不計註解行，這是 `AutoClaude/tools/check_loc_budget.py`
  > 自己的 TIER-WARN 指引，內容一字未刪），**沒有調高任何門檻**。
  > 但那只是止血：真正的修法是把續航編排抽成 `tools/session_endurance.py`、planner 退回
  > 「量水位＋產任務書＋CLI 分派」。已具名登記在 `R79_HANDOFF.md` §4.3。
  > 現查餘裕：`& $p "$r\AutoClaude\tools\check_loc_budget.py"`（看 `[ROOT-TOOLS-WARN]` 那一格）

---

## 1. 背景：一個今天真的發生過的事故

2026-08-07 約 09:30，七個 subagent 同時啟動，**16 秒內全數失敗**，逐字：

```
You've hit your session limit · resets 9am (Asia/Taipei)
```

主 session 仍活著（仍能跑工具、寫檔），但**沒有任何機制知道該等多久、也沒有任何機制會在額度回來時把工作接回去**。
SA 量到的等待分布說明浪費在哪：那次撞線在台北 08:44、訊息說 09:00 恢復（**只需等 16 分鐘**），
而下一則成功回覆是 **62 分鐘**後——**46 分鐘純粹在等人**。要自動化收回的就是這 46 分鐘。

既有機制全部不適用，逐項實查：

| 既有物 | 為何接不上 |
| --- | --- |
| AutoClaude Kernel 的 Token Guard（≥80% compact／≥90% checkpoint ＋ `scheduled_resume_at`） | 它守的是**被驅動的那個 CLI 的 PTY**，與 Claude Code session 自己零接線。它的 `time.sleep()` 睡在本 repo 自己的 Python 行程裡，而我們的等待必須發生在 harness 的行程裡 |
| `context_budget_guard.py` 的 75/90 線 | 那是 **context 水位**（分母＝window）。額度耗盡當下水位只有 ~18%，四道放行條件會全數放行 |
| `CronCreate` | `CronList` 標 `[session-only]`。R59 已踩過並寫進 CLAUDE.md |
| `ScheduleWakeup` | `delaySeconds` clamp 到 [60, 3600]；**且它不寫磁碟、沒有可查詢的登錄、沒有 `NextRunTime`** ⇒ 沒有任何憑證，事後無從得知它排到了沒有——與 R59 那次事故同形 |
| CLAUDE.md〈Token 將耗盡時的 SOP〉 | 純散文。本 repo 已反覆實證純文件約束對當下的模型零攔阻力 |

---

## 2. 決策

**額度耗盡時：從錯誤訊息觀測 reset 時刻 → 排一支一次性 `schtasks` → 到點由確定性的 Python 探測 →
通了就續跑／沒通就依新觀測的時刻重排／月度上限就硬停並叫人。等待期間零 token、終端可關、機器可睡。**

### 2.1 reset 時刻**只能觀測，不能算**（本 ADR 最關鍵的一條）

全庫 1,180 支逐字稿掃出的 reset 值共 **7 個相異**：`3:50am` `4am` `9am` `11pm` `12:20pm` `12:30pm` `6pm`。
**沒有一個落在 5 小時的固定格點上** ⇒ 它是滾動視窗、錨在該區塊第一次用量。

因此 `DEFAULT_AT_EXPR = "(Get-Date).AddHours(5)"` 是缺陷：它把一台機器的偶然事實寫成常數（R73 同型）。
更難看見的是它的失效**不會轉紅**——排程會成立、`NextRunTime` 也拿得到、取證規則照樣綠，
只是它**醒在錯的時間**。這是「憑證存在、但憑證不回答那個問題」。

⇒ `parse_reset_at()` 解不出時間時回 `None`，呼叫端一律**拒絕武裝**，
**不准**退回「假設 5 小時」（`relay_problems()` 對 `reset_source` 非觀測值一律判紅）。

### 2.2 S1（session 額度）與 S2（月度支出上限）必須分開

實測計數：`session limit` **151** 筆／`monthly spend limit` **71** 筆（＝32%）。
兩者的字面前綴同為 `You've hit your `，只比對前綴的分類器會把那 71 筆判成可等待
⇒ 排一支永遠不會成功的工作、每次觸發燒一次探測，而真正該做的事（叫人提額）一直沒發生。
這是本協定**最貴的一種誤判**，故 `classify_limit()` 的判讀順序把 spend 排在 session 之前，
且 `LIMIT_UNKNOWN` 一律 fail-closed（不重排）。

### 2.3 分層：只有一層是自動的

| 層 | 機制 | 憑證 | 終端可關？ |
| --- | --- | --- | --- |
| **L0 觸發**（R79 補洞包新增，見 §2.6） | SessionStart hook 自動 `--arm-sentinel` | `NextRunTime` ＋ JSONL 痕跡 | ✅ |
| **L1 武裝**（session 內，一個回合，零等待） | `--arm-endurance` | `NextRunTime` | — |
| **L2 自動**（唯一撐得住的） | `schtasks` ＋ `--resume-tick` | `NextRunTime` ＋ JSONL 痕跡 | ✅ |
| **L3 地板**（永遠成立） | `%TEMP%` 的任務書＋狀態塊，含 `claude -r <sid>` | 檔案本身 | ✅ |

**L3 是進入等待的前置條件**：寫不出任務書就直接放棄並大聲說做不到，不准假裝在等。

### 2.4 狀態只有一個家

續航狀態嵌進**既有的可重啟點任務書**（`%TEMP%\autosdd_resume_plan_<sid>.md`），
用兩行字面 sentinel 夾一段 JSON。一份檔、兩個面：人讀六節、機器讀那一塊。
解析走「找 sentinel → `json.loads`」的子字串掃描，**不解析 markdown**（有人調一個標題不該讓狀態讀不出來）。

「沒有武裝過」與「武裝過但狀態壞了」必須分得開（`has_relay()` vs `parse_relay()`）——
這是「量不到 ≠ 量到零」在狀態檔這一層的形態。

### 2.5 無人看管的那一跑：續跑**預設關閉**

`claude -p -r` 是全自動、沒有人在迴圈裡，而任務書的〈禁止事項〉是散文，對 print 模式的模型一樣零攔阻力。
故：**醒來那一跑預設只做「探測 ＋ 留痕 ＋ 通知」**，真的續跑要在武裝時顯式帶 `--allow-resume`
（該選擇記進狀態塊，事後查得到）。
昂貴的那部分（等 5 小時、知道額度什麼時候回來）兩種模式都完成；被關住的只有最後那個模型回合。

> 🔴 **未解**：`--allow-resume` 開啟時，要不要用 hook 機械擋掉 commit/push？

### 2.6 預防性哨兵：補上**觸發層**（R79 補洞包；本節是對 §2.3 那張分層表的修正）

§2.3 把 L1 武裝寫成「session 內，一個回合，零等待」，讀起來像是已經解決了。**它沒有**——
L1 是**手動**的，而本輪在協定落地的**同一天又撞了一次額度，協定一點作用都沒有**。三層根因：

| 層 | 缺口 | 為什麼 §2.3 那張表看不出來 |
| --- | --- | --- |
| **觸發** | 沒有任何東西會去按 `--arm-endurance` | 那張表只描述「按下去之後會發生什麼」，沒有一欄在問「誰按」 |
| **偵測** | 額度耗盡**不是工具呼叫失敗**，是 API 層失敗 ⇒ PreToolUse／PostToolUse 一次都不會被叫到 | 全 repo 唯一的事中觀測面是 hook，而這件事在 hook 體系裡**沒有觸發點** |
| **形態** | 這是「機制蓋好沒接電」的第三次復發（R77 PKG-GUARD 有前例） | 覆盤只看「功能對不對」，不看「有沒有東西會自動去用它」 |

實測逐字（撞線後補跑 L1）：`rc=1`／「觀測到的 reset 時刻 … 已經過去 … 沒有東西需要等」。
判斷是**對的**——但它暴露了設計缺口：`--arm-endurance` 只在「已撞線且 reset 尚未到」那個很窄的
時間窗裡有用，**而那個窗恰好是沒有人會去用它的時候**。

#### 關鍵洞察（整個哨兵成立的原因）

> **探測是為了知道「額度回來了沒」——那件事只能問伺服器；
> 但要知道「額度撞了沒」根本不用探測——讀逐字稿就行，成本是零。**

這個不對稱讓「還沒撞線就先掛著」變得可行：平時每次醒來只讀檔（零 token），
只有真的撞線那一次才花一次探測（~32K tokens）。對照被否決的 `ScheduleWakeup` 接力
（§3 第一列）：那個方案**每次**醒來都要花一個模型回合（實測 ~20.7 萬 tokens），
所以它才被迫把間隔拉到 50 分鐘——成本結構不同，取值就不同。

#### 哨兵四分支（`sentinel_decide()`，純函式）

| 分支 | 條件 | 動作 | 成本 |
| --- | --- | --- | --- |
| `arm_reset` | 有未處理撞線、reset 尚未到 | 重排到 reset＋skew（`--sentinel-tick`） | 零 token |
| `probe` | 有未處理撞線、reset 已過 | 花一次探測，之後交棒 `--resume-tick` 既有機器 | 一次探測 |
| `patrol` | 無未處理撞線、逐字稿仍在更新 | 重排下一次巡邏 | 零 token |
| `disarm` | 無未處理撞線、逐字稿已靜止 | 自我解除並驗證真的移除 | 零 token |

外加兩個 fail-loud 出口：月度支出上限 ⇒ `escalate`（等待無效）；解不出 reset 時刻 ⇒
`escalate`（**拒絕用猜的重排**，同 §2.1）；狀態塊指的逐字稿不存在 ⇒ `escalate`
（哨兵瞎了與哨兵正常下班必須留下不同的痕跡）。

#### 「未處理」的判準，以及它為什麼可證

事件時間戳**嚴格大於**狀態塊裡的 `handled_through`。武裝當下把逐字稿裡最後一筆事件記成
已處理，理由是可證的：**我們此刻跑得動武裝指令，就證明額度是通的** ⇒ 已經在逐字稿裡的
那些撞線必然都已解決。少了這一格，哨兵會每 15 分鐘對同一筆早就結案的撞線探測一次。

#### 兩個閾值都是**量出來的**，不是挑的

- `SENTINEL_INTERVAL_SECONDS = 900`：實測那次真實撞線是 08:44 撞、訊息逐字 `resets 9am`
  ⇒ hit→reset 只有 **16 分鐘**。間隔必須小於它，否則「精確重排到 reset」那一支在
  **已觀測到的最短窗**下結構上不可達，整個機制退化成只會事後補救。
- `SENTINEL_IDLE_SECONDS = 21600`（6h）：必須**大於一個完整額度視窗**（5h）。等額度那段
  逐字稿本來就不會更新，門檻若短於視窗，哨兵會在最需要它的時候把自己拆掉。
  兩者的方向都由 `tools/tests/test_context_budget_guard.py::SentinelDecisionTest` 釘住。

#### 接電：SessionStart hook（本節的重點，不是那個工具）

**這一次不做成「要人記得去按」的東西**。`.claude/settings.json` 的 `SessionStart` 新增一個
條目，掛同一支 `context_budget_guard.py`（第三個模式，由 `hook_event_name` 分派）。
契約：只在 Windows 動作；`AUTOSDD_SENTINEL_OFF` 一律 no-op；**恆 exit 0、不出聲、不量水位**；
註冊走 **detached 子行程**故不阻塞 session 開場（同步外呼 `powershell.exe` 註冊實測數秒，
每次開 session 都卡是不可接受的代價）。取證沒有因為非同步而消失——`--arm-sentinel` 自己
有 `NextRunTime` 憑證閘，成敗都進稽核 jsonl。

> 🔴 **`.claude/settings.json` 從此不再是「本協定不動」**（§4 最後一列原本這樣寫，那是對的——
> 在寫下它的時候）。本節是一個**新決策**：額度確實不是 context，但**接電點**只能長在 hook
> 註冊面上，因為那是全 repo 唯一「session 一開就會自動跑」的地方。共用腳本、不共用門檻。

#### 已知限制（照實寫）

1. **首次武裝有一個巡邏間隔的空窗**：SessionStart 之後 15 分鐘內撞線，要等下一次巡邏才
   被看見。代價是延遲、不是漏掉（`handled_through` 不會前進）。
2. **detached 子行程的成敗，SessionStart 那一刻看不到**——只能事後查 jsonl／`Get-ScheduledTask`。
   這是為了不阻塞開場付的價。
3. **每個 session 一支排程工作**；靠 `disarm` 分支回收。若機器在哨兵下班前就關掉，工作會
   留到下次開機補跑（`StartWhenAvailable`）才自我解除。
4. **mac/Linux 完全沒有**：`run_powershell()` 在非 Windows fail-loud，哨兵整條路同樣只在
   Windows 成立（鐵律三：單平台判準不外推）。
5. **`--allow-resume` 的風險未變**（§2.5、§7-5）。哨兵只是讓「等到額度回來」這件事會自己
   發生，最後那個模型回合的授權面一個字都沒放寬。
> `claude --disallowed-tools` 存在（實查 `--help`），但它只能擋整支工具，擋掉 PowerShell 會讓續跑失去意義。
> 本輪**沒有**做這道，故預設關閉是它的替代品。這是已知缺口，不是漏看。

---

## 3. 被否決的方案（各記為何否決）

| 方案 | 出處 | 否決理由 |
| --- | --- | --- |
| **`ScheduleWakeup` 鏈式接力 6 棒** | 原始需求的預設想法 | ① 主 session 醒一次約 20.7 萬 token（成本正比於自己的 context，且會隨 session 長大），6 棒 ≈ 124 萬；外部探針是**常數 31,847**（本輪實測）。② 醒來那一棒本身就是一次模型請求，額度斷電期間它自己也會被擋，而 runtime 的 keepalive 補救常數實查為 **1** ⇒ **結構上撐不過一次完整的 5 小時斷電**。③ **它沒有任何憑證**，事後無從得知排到了沒有。④ schtasks 沒有 1 小時上限 ⇒ 「接力」整個是 `delaySeconds` 上限外溢出來的**假需求** |
| **session 內 `run_in_background` 守望行程** | Architect | 仍然要求終端開著（與接力同一個死穴）；`run_in_background` 是否受 600000ms 上限砍掉**未驗**，而被砍時很可能是靜默的＝看起來像「排了但沒觸發」，正是 R59 那個事故的形狀；且行程 exit 後的回訪仍需要一個模型回合，那個回合可能自己被額度擋下 |
| **新增 `tools/endurance/` 三支檔** | SA | 本 repo 最大缺陷來源是護欄層自我增殖；`test_check_wrapper_thinness.py` 明載往 `tools/` 新增 `*.py` 會同時污染 ruff／LOC 棘輪／`_script_scan_surface`。全部功能塞得進既有兩支檔，且塞的位置有結構理由（見 §4） |
| **`.claude/loop.md` 接力棒** | SD | 接力已否決 ⇒ 它沒有消費者。且它是掌舵者日常 `/loop` 讀的**同一個檔**，寫進去會污染日常行為；25,000 bytes 上限還是**靜默截斷** |
| **長壽 canary session 壓低探針成本** | SA | 美元便宜（$0.0176 → $0.0036，本輪兩支探針實測）但多一個長期存活的移動零件。token 成本兩者相同（~32K），而預算上界是用 token 算的 ⇒ 收益不值那個複雜度。**記為已知可選優化** |
| **任務書改落 `%LOCALAPPDATA%`** | Architect／SD 皆提 | `%TEMP%` 被清掉確實是靜默的單點失效，但搬家會動到 `guard.PLAN_PREFIX`／`write_resume_plan()`／既有測試。**真正的修法不是搬家而是讓失效變大聲**：註冊時把「任務書不存在就中止」寫進 Action 自己（任務書不存在時，沒有人讀得到寫在它裡面的規則）。搬家列為候選 |

---

## 4. 為何住在這兩支檔（職責歸屬）

- **不放 `AutoClaude/autoclaude/`**：那是會出貨的套件，受 8 條 import-linter contract 與 LOC 分級管。
  續航要摸的是 harness 內臟（`~/.claude/projects/**/*.jsonl`、`claude -p -r`、schtasks），
  放進去等於「被驅動的引擎反過來依賴驅動它的 harness」，方向倒轉。
- **純判讀放 `context_budget_guard.py`**：逐字稿掃描的實作已經在那裡（`scan_transcript`），
  而 planner 已經 import 它。反過來寫會讓「怎麼掃逐字稿」有兩個家。
  該 hook 由 `runpy.run_path` 起、`sys.path` 不含 `tools/` ⇒ 它**只能被 import，不能 import**，
  既有依賴方向 `tools/ → .claude/hooks/` 只能維持。
- **CLI／編排放 `session_resume_planner.py`**：`run_powershell()`（顯式外呼 5.1）、
  `schtasks_script()`、`next_run_time()` 取證閘都已在那裡。續航是「這個 session 快不能工作了怎麼辦」
  的**另一半**（context 爆掉 vs 額度用完），拆新檔就是製造第二個家。
- **`.claude/` 只提供事件，不承載邏輯**（這一條沒變，SessionStart 條目也只是叫回 planner）。
  🔴 **下一句已被 §2.6 取代，別照它推論**：本列原本斷言本協定完全不動 `.claude/settings.json`。
  R79 補洞包新增了一個 SessionStart 條目——理由不是「額度變成 context 了」（兩者仍是兩件事、
  門檻仍各自獨立），而是**接電點只能長在 hook 註冊面上**：那是全 repo 唯一「session 一開就會
  自動跑」的地方，而沒有接電的協定本輪已實證等於沒有。原句與其論證保留在下方以存脈絡：
  **本協定**（R79 補洞包之前）不新增任何 `.claude/settings.json` 條目——
  額度不是 context，把額度掛上那支守衛會讓它變成「一個東西假裝能做兩件事」。
  > 🔴 **R79 四方複審訂正射程**：本列原本寫「**本輪**不動 `.claude/settings.json`」，而同一個工作樹裡
  > 該檔實測 **+11／−0 行**——那是**同輪 context 水位包**新增的 PreToolUse 條目
  > （matcher `Task|WebFetch|WebSearch`，掛同一支 `context_budget_guard.py` 的阻斷模式），
  > 屬**另一個決策**（context 水位 ≥90% 擋展開型工具），不是本協定的一部分。
  > 兩者共用腳本、由 payload 的 `hook_event_name` 分派，但立案理由與門檻各自獨立。
  > 「本輪」與「本協定」在多包並行的一輪裡不是同一個範圍，**ADR 只能替自己說話**。
  > 現查：`git -C "$r" diff --numstat -- .claude/settings.json`

### 與 AutoClaude Token Guard 的關係：另立一套

判準是「**改一個值，是不是兩邊都得改？**」——不是「看起來像不像」。
門檻階梯（80/90 vs 75/90）歷來各自設定、從沒有人需要同時改；
`seconds_until_resume()` 吃 ISO 字串、睡在本 repo 的 Python 行程裡，而本協定的輸入是**人類可讀的錯誤字串**、
等待發生在 harness 的行程裡。共用要嘛讓套件依賴 harness 內臟、要嘛讓根治理層被子專案的 LOC/import 契約綁住。
Copy-on-Evolve 管的是**知識（事實）**不是**形狀（模式）**：事實只能有一個家，
「從目標時刻算等待 → 睡 → 從持久化的點續跑」是模式，在兩個 runtime 基質上各自出現不是缺陷。

---

## 5. 實測證據（全部為 R79 當回合真跑）

| # | 命題 | 實測 |
| --- | --- | --- |
| E1 | `DEF-101-089`「`CLAUDECODE=1` 巢狀 spawn 必死結」 | **對 `claude -p` 這條 subprocess 路證偽**。繼承 `CLAUDECODE=1` 外呼 `claude -p` → **rc=0、3.36s**（第三次獨立複驗）。<br>🔴 **R79 收輪收窄射程**（原文只寫「證偽」，是全稱的）：同輪另跑了樹上真正在用的**另一條** spawn 路（`wexpect` pty，11 支測試的 skip 判準所依賴的那一條），結論**相反**——`PtyWrapper.start()` 三次都沒回返（180／180／45s）、`claude.exe` 從未被啟動，且**剝除 `CLAUDECODE` 的對照組行為完全相同**。⇒ 證偽**不遞移**：`CLAUDECODE` 是巢狀環境的可靠標記、不是成因；本協定只依賴 subprocess 這一路，故 E1 對本協定成立。逐次量測見 `docs/06_quality/CrossPlatform_R79_Debt_Audit.md` 的 `## DEF-101-913` 節 |
| E2 | `claude -p -r <sid>` 真的接回同一支 session 並帶 context | **成立**。回傳 `session_id` 與傳入**完全相同**；續問「上一則你回了哪個字」答對 `PONG`（rc=0、3.01s） |
| E3 | 探測成本 | 冷探針 **31,847** tokens／$0.0176；`-p -r` 暖續跑 31,922 tokens／**$0.0036**（cache read） |
| E4 | reset 只能觀測 | 全庫 7 個相異值，無一落在 5 小時格點 |
| E5 | S1/S2 比例 | 151 : 71 |
| E6 | 水位計在撞線當刻讀 0% | **重現並修復**。135 筆合成記錄 usage 三欄全 0；修復後同一支逐字稿 used＝178,616（17.9%） |
| E7 | schtasks 端到端 | 見 §6 |
| E8 | 註冊當前使用者的工作不需提權 | 成立（本輪四次註冊全部在非提權 session 完成） |

---

## 6. 取證規則（本 ADR 對 CLAUDE.md〈反事後諸葛〉的補充）

**憑證是 `NextRunTime` 這個「值」，不是指令的 rc**——`Get-ScheduledTask` 對不存在的工作回 **rc=0**（非終止錯誤），
只讀 rc 會是假綠。`next_run_time()` 靠空字串把它判紅，`relay_problems()` 則禁止在 `next_run_time` 為空時
把狀態寫成 `armed`／`waiting`。

第二道是**痕跡**：每一次醒來 append 一行 JSONL，且**第一行必須在讀任何東西之前就寫**
（讓「觸發了但早期失敗」與「根本沒觸發」分得開）。
🔴 這一條在本輪端到端實測中自己出過錯：痕跡的鍵原本用 session id，而開場那一行寫得出來時
session id 還躺在沒讀的狀態塊裡 ⇒ 痕跡分裂成兩個檔，早期失敗那一行剛好落在沒人看的那一個。
鍵已改為**任務書路徑**，並由 `test_the_audit_trail_has_exactly_one_home` 釘住。

---

## 7. 已知限制（照實寫，不粉飾）

1. **醒來那一跑的 hook 攔截面未驗**：headless `claude -p` 是否跑本 repo 的 PreToolUse／PostToolUse hook，
   本輪沒有驗。若不跑，最無人看管的那一跑會是全 repo 唯一沒有護欄的地方。
   ——這正是 `--allow-resume` 預設關閉的第二個理由。
2. **`retry-is-probe` 未量測**：「有真工作待跑就直接重試它、失敗成本趨近零」是推論；
   無法構造一次真的額度耗盡來量它，故**沒有**實作，探測一律走 `--probe-quota`。
3. **`%TEMP%` 是地板的單點失效**，且失效是靜默的。已用「Action 自帶存在性檢查」把它變成大聲，
   但沒有搬家。
4. **mac/Linux 無對等物**：`run_powershell()` 在非 Windows 明文 fail-loud。
   L2 要 launchd／cron 才有對等物，本輪**明說做不到**而不是靜默缺席（鐵律三）。
5. **`--allow-resume` 開啟時沒有機械護欄**（見 §2.5）。
6. **探測預算上界 5 × 31,847 ≈ 16 萬 tokens**。`MAX_PROBE_ATTEMPTS = 5` 是挑的、不是量出來的。
7. **醒來後可能二次撞線**：reset 是滾動視窗，醒來只要一動就重新起算。
   故任務書第 3 節的第一條恆為「重驗＋收斂」，不是「繼續展開」。
