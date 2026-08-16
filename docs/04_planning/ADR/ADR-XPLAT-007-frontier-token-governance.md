# ADR-XPLAT-007 — 前沿 AI Agent 額度治理對標，與訴求 6 全鏈設計複審

- **狀態**：Proposed（R85／P8 調研包產出；R85／P10 續寫 §2 前沿調研＋§3.7 對照＋§4.1-bis `.env` 實測）
- **P10 的改動面**：本檔（續寫）＋ **新建根 `.env`**（已確認在 `.gitignore` 內、未進版控）。其餘唯讀
- **日期**：2026-08-12
- **平台**：本輪全部量測在 **macOS**（Darwin 25.5.0）。凡涉及 Windows 的結論一律標「靜態推論、未在真機驗證」
- **上游**：[ADR-XPLAT-004](ADR-XPLAT-004-token-endurance-protocol.md)（續航協定／哨兵）、[ADR-XPLAT-005](ADR-XPLAT-005-quota-aware-throttling-and-fanout-resume.md)（額度節流與扇出）
- **驅動**：掌舵者訴求 6z／6a／6b／6C／6c／6d／6e／6f

---

## 0. 本檔的取證紀律（先講清楚，因為本檔通篇是宣稱）

本檔**每一個數字都是量測值，不是常數**。每一格都註明「哪一支載具現查得到」。
凡本回合沒有親自跑到的，一律寫「**未驗證**」或「**靜態推論**」，不以文件自陳頂替——
根 `CLAUDE.md` 與 `R84_HANDOFF.md` 的自陳在本檔一律只當**待驗假設**看待。

> 🔴 **本檔自己就踩到一次這條紀律的價值**：根 `CLAUDE.md` 兩處要求「reset 窗數字一律現查
> `python tools/probe/reset_window_distribution.py`」，而該指令**今天 rc=1**（見 §1.5）。
> 若照慣例引用文件自陳，本檔會直接複製一組**再也無法複驗**的數字。

---

## 1. 現況實測（訴求 6a~6f 逐款，本回合真跑）

### 1.1 逐條指令與輸出摘要

| # | 指令（cwd＝monorepo 根，python＝`.venv/bin/python`） | rc | 摘要 |
|---|---|---|---|
| C1 | `tools/lib/quota_policy.py --print-env-example` | **0** | 印出 **17 個鍵**（結構上＝14 政策鍵 ＋ 3 逃生口，見 §4.4）；自陳優先序 `env > AutoClaude/.env > 根 .env > 出廠預設` |
| C2 | `tools/session_resume_planner.py --pace` | **0** | `可派 4／cap=4／band=notice／binding=seven_day 61% 剩 5357 分鐘`；**7 軸**；`來源=cache` |
| C3 | `tools/session_resume_planner.py --check` | **0** | `used 215,216／window 1,000,000（推斷）／水位 21.5%`；`重啟指令 claude -r <sid>` |
| C4 | `tools/session_resume_planner.py --check-autocompact` | **0** | `harness autocompact 開啟`；`window=auto`；判定鏈兩段皆「未設 ⇒ 採預設」 |
| C5 | `tools/probe/reset_window_distribution.py` | **1** 🔴 | `AttributeError: module 'context_budget_guard' has no attribute '_RESET_RE'` |
| C6 | `pmset -g custom` | 0 | **只有 `AC Power` 一段**（無電池段 ⇒ 桌機）；`sleep 0`／`displaysleep 10`／`womp 1`／`standby 0` |
| C7 | `pmset -g sched` | 0 | **空**（本機沒有任何排定的喚醒事件） |
| C8 | `pmset -g assertions` | 0 | `PreventUserIdleSystemSleep 1`（powerd 持有，理由＝顯示器亮著）；`PreventSystemSleep 0` |
| C9 | `launchctl list \| grep AutoSDD` | 0 | `-  0  AutoSDD_Sentinel_c426c871-36ee-428f-a67b-e84864bea5a1` ⇒ **本 session 的哨兵確實已武裝** |
| C10 | `endurance_env.sleep_trouble(runner)` | — | 回**空字串**＝無異常；`posture_note()`＝「各電源段 `sleep` 皆為 0」 |
| C11 | `ls .env`（monorepo 根） | **1** | **根 `.env` 不存在** |
| C12 | `which caffeinate` | 0 | `/usr/bin/caffeinate`（**不需 sudo**） |

C2 的 7 軸逐字：`session 43%/17min`、`weekly_all 61%/5357min`、`weekly_scoped 0%/不明`、
`five_hour 43%/17min`、`seven_day 61%/5357min`、`nimbus_quill 0%/不明`、`spend 0%/不明`。

### 1.2 取數口徑（訴求 6a 的核心）

`tools/lib/quota_meter.py:72` — 取數端點是 **`https://api.anthropic.com/api/oauth/usage`**，
以 Claude Code 自己的 OAuth access token（Keychain）認證。檔頭明載「這個呼叫不是模型推論
⇒ 不吃額度、不進 5 小時視窗」。**伺服器直接回百分比**（依帳號方案算好），本機不自行推導分母。

⇒ **訴求 6a「水位是 % 不是固定量（因為啟動帳號不同）」在架構上已經達成**，而且達成方式是
最強的那一種：分母根本不在本機，所以「換帳號＝換分母」這件事結構上不可能出錯。

### 1.3 現況表 — 6a~6f 逐款

| 款 | 掌舵者要的 | 今天做到哪 | 憑證（本回合） | 缺口 |
|---|---|---|---|---|
| **6z** 前沿參考 | 查最新前沿 agent 設計 | **已完成**（R85／P10，§2 四個子題皆有帶 URL 的資料，含 3 筆已讀原文的官方文件） | §2.1~2.4；§3.7 逐項對照 | 3 格【查無】已明說；【摘要】級來源不得引用細節 |
| **6a** %-based 監控 | 隨時可查用量、水位用 % | **已達成**。伺服器端算好的 % ＋ 7 軸 ＋ 180s TTL 快取 ＋ `--pace` 零 token 出口 | C2（`來源=cache`）；`quota_meter.py:72` | 端點**未公開文件化**（見 §3.2 R-1） |
| **6b** 演算法 | %Usage × Reset 期程 ⇒ 可派數 | **已達成且已治本**。`cap=min(逐軸)` 煞車 ／ `rec=min(base×pace, cap)` 加速，`pace` 取最短期程軸 | C2 實測 `cap=4 rec=4`；`quota_policy.py:430 _pace_of` | 加速的**正當性**依賴「固定區塊」模型；係數是「挑的」（§3.4） |
| **6C/6c** 85 準備／95 停止 | 85% 準備、95% 停止、記錄狀態 | **已達成**。四道門檻 50/70/85/95 皆為 env 可調；`halt` 帶 `cap=0` 且不吃任何覆寫 | C1 印出四鍵；`quota_policy.py:331 _cap_for` halt 分支 | 門檻**現值從未被實務調校**（§4.2） |
| **6d** 同 session 續跑 | 撞線後 reset 時喚起、**同 session** | **半達成**。武裝端**今天真的在跑**（C9）；「同 session」語意正確——續跑 argv 實查為 `claude -p -r <session_id> <prompt>` | C9 launchd 實物；`session_resume_planner.py:1114`；`test_context_budget_guard.py:2748` | 🔴 **載具端到端零驗證**——測試把 `_register_and_record` **刻意 stub 掉**（§3.5） |
| **6e** 度過 0~5 小時 | 不休眠、每 50 分喚醒？ | **部分達成**。「每 50 分鐘」已被量測否決；mac 側只做到「**失效可偵測**」 | C6/C10 皆 OK；C7 空 | 🔴 **睡著的 Mac 仍不會被喚醒**（§3.6） |
| **6f** `.env` 實測調優 | copy 到根目錄 `.env`、調到最佳值 | **已執行**（R85／P10）。根 `.env` 已建立，且**已證明真的被讀到**（band 隨門檻翻動） | §4.1-bis 的 A／B／C 三快照，rc 皆 0 | 逐鍵複審見 §4.3／4.3-bis；`CAP_*` 仍缺實測語料 |

---

### 1.4 🔴 三點設計優勢（低報與過報一樣貴，照實記）

> 🔴 **措辭限定**：以下是**與本 repo 自身既有標準、以及常見單數字設計**的對照。
> 因 §2 未完成，**不得**讀成「勝過前沿框架」——那個宣稱需要 §2 的證據才成立。

1. **多軸同時判讀，且「binding 軸」被具名指出**。C2 一次印 7 軸，並回答「最緊的是哪一條、
   它距 reset 幾分鐘」。業界常見形態是單一 `remaining` 數字；單一數字結構上無法回答
   「我現在該不該派工」——因為煞車的軸與加速的軸可以是不同的兩條。
2. **「查一次不會讓被查的數字變大」是設計約束**。`--pace` 只讀 180s 快取，端點本身也不是
   模型呼叫 ⇒ **零 token**。相對地，任何「叫一次模型去問自己還剩多少」的設計都是自我消耗。
3. **憑證優於 rc 已上升為判準**。`relay_problems()` 明文禁止在憑證為空時把狀態寫成
   `armed`／`waiting`；且 mac 與 Windows **刻意不共用憑證鍵**（launchd 從不報「下次幾點跑」，
   把推算值塞進 `next_run_time` 就是把推算偽裝成排程器回報）。這一條比多數框架嚴格。

### 1.5 🔴 本回合發現的新缺陷：**現查入口自己壞了**（`DEF-200-P8-01`，建議編號由收尾窗口指派）

**症狀**：`tools/probe/reset_window_distribution.py` rc=1（C5）。

**根因**（實查，非推論）：該 probe 第 95 行取 `guard._RESET_RE`，而 R81 的收斂把撞線判讀原語
整組搬到 `tools/lib/quota_limits.py`；`context_budget_guard.py:270` 是一份**具名 import 清單**
（`from quota_limits import (...)`），只 re-export 公開名。實測：

```
LIMIT_SESSION True / classify_limit True / parse_reset_at True / _RESET_RE False
```

**為什麼這一筆特別貴**（三層，逐層都有先例）：

- 根 `CLAUDE.md` 有**兩處**明文要求「數字一律現查」並指名這支 probe ⇒ 那條紀律今天
  **結構上執行不了**。這與 R79 對 R77 下過的判決（「沒有留下任何可重跑的產物，所以
  『每輪重跑』結構上做不到」）**逐字同型**，只是這次產物存在、但跑不動。
- `session_resume_planner.py:309` 與 `test_context_budget_guard.py:1603` 都以
  「全庫 1,433 支逐字稿、14 個相異 episode」為註解依據——那組數字**今天無法複驗**。
- **沒有任何東西會轉紅**：probe 不接任何閘門的 rc。失效是靜默的，且已靜默了至少一輪。

**修法**（**持有面＝`tools/**`＝P2**，本包不動）：兩案，建議走案二。
- 案一：把 `_RESET_RE` 加進 `context_budget_guard.py:270` 的 import 清單。1 行，但等於認可
  「跨模組取用私有名」，下一次改名同樣會斷。
- 案二（建議）：`quota_limits.py` 開一個公開存取器（例：`reset_literal(text) -> str | None`），
  probe 改呼叫它。理由與該檔既有體例一致——判讀原語的唯一的家就是 `quota_limits`。
  實查 `dir(quota_limits)`：今天**沒有**任何公開的字面存取器（只有 `_RESET_RE` 這個私有名）。
- **配套（必要，否則同型必復發）**：加一支 smoke 測試，對三支 probe 各跑一次
  `--help` 或空語料，斷言 **rc=0**。實查 `tools/tests/` — **今天零 probe smoke 測試**
  （`ls tools/tests | grep -i probe` 只有 `test_bash_probe_spec_contract.py`，那是別的主題）。

**診斷已被證實（不是推測）**：本包在**記憶體內**注入 `guard._RESET_RE = quota_limits._RESET_RE`
（`runpy` 跑 probe，**未修改任何檔案**），probe 隨即 **rc=0** 並產出完整報表 ⇒ 根因確認為單點，
修法確認可行。輸出見 §1.6。

### 1.6 🔴 被搶救回來的量測（本回合，2026-08-12，**這台 mac**）

> 這組數字是 §1.5 修法的副產品，也是根 `CLAUDE.md` 要求「一律現查」但至少一輪拿不到的那組。
> **一律視為量測值。** 現查入口＝修好之後的 `python tools/probe/reset_window_distribution.py`。

| 量 | 本回合值 |
|---|---|
| 逐字稿母體 | **1,056 支**（`~/.claude/projects`） |
| 事件分類 | `quota_session 76`／`transient 37`／`unknown 19` |
| session-limit 事件 | 76 筆，**解得出 reset 的 76 筆**（parse 成功率 100%） |
| reset 相異字面 | **7 個**：`4am`(21)／`11pm`(21)／`6pm`(7)／`4:20pm`(8)／`1pm`(8)／`5:50pm`(6)／`3:20am`(5) |
| 相異撞線 episode | **15 個** |
| episode hit→reset | **min 3.4／median 170.8／max 286.9 分鐘** |
| ≤16 分／≤50 分 | **1／3**（分母 15） |
| **>300 分（>5 小時）** | **0** |
| 單一觀測者最短窗 | min 2.7／median 170.5／max 285.6 分鐘 |

**四個可直接使用的結論：**

1. **「五小時」這個前提仍然不成立，但安全邊際只剩 13.1 分鐘。** max=286.9 分（4.78h）。
   舊輪引用的 max 是 253.2 分 ⇒ **這個上界正在成長**。⇒ 「>5h 者 0 個」這句話**不得再被當成
   常數引用**，它是一個正在逼近失效的量測值。建議把它做成有方向的棘輪（max 上升就出聲）。
2. 🔴 **母體是機器本地的，跨機器不可比。** 本回合 1,056 支；舊輪（Windows 機）自陳 1,433 支、
   14 episode。**這不是語料減少，是不同機器的不同逐字稿目錄**。⇒ 任何跨輪的數字對照
   都必須先問「哪一台機器」。本檔的數字只對這台 mac 成立。
3. **7 個相異字面沒有一個落在 5 小時固定格點上**（`4:20pm`／`5:50pm`／`3:20am`）
   ⇒ 區塊錨定模型再次被證實。**這正是 §3.4(a) 加速正當性所依賴的那個前提**，本回合已量到。
4. **15 分鐘巡邏間隔在本語料下仍然正確**：只有 1／15 episode 短於 16 分（那一次走 `probe`
   ＝花一次探測，不是失效）；而若改成 50 分鐘，**3／15（20%）的 episode 會整個沒醒過**。
   ⇒ 「不採用每 50 分鐘」的決定在**本輪新語料**下重新成立，不是沿用舊結論。

---

## 2. 訴求 6z — 前沿做法調研（R85／P10 執行，檢索日期 **2026-08-12**）

### 2.0 本節的證據分級（先講，因為下面每一筆都靠它判讀）

本節每一筆標 **官方**／**第三方**，並額外標一層**我到底讀了多少**——兩者是不同的軸，
混在一起正是「宣稱先於查證」的溫床：

| 標記 | 意思 |
|---|---|
| 【**已讀原文**】 | 本回合以 `WebFetch` 真的抓下該頁並讀過內文。可以引用逐字 |
| 【**僅搜尋摘要**】 | 只從 `WebSearch` 的結果摘要／標題得知。**URL 為真，內文未讀** ⇒ 只可當「有這個東西存在」的線索，**不得引用其細節為事實** |

🔴 **第一道篩子（每一筆外部做法都要先過它）**：Claude Code 的 hook 體系在**額度耗盡**時
一次都不會被叫到——那是 **API 層**失敗，不是工具呼叫失敗 ⇒ PreToolUse／PostToolUse 皆無
觸發點。**任何「撞到才反應」的設計在本專案結構上都不適用**，一律必須改寫成「趁還能跑指令
時預先武裝 ＋ 由 OS 排程器輪詢」（＝現行 `--arm-sentinel`）。下面逐筆標「適用性」。

---

### 2.1 子題 a — 額度／用量的可觀測性

**a-1【官方・已讀原文】Messages API 的 rate-limit response headers（完整且有文件）**
`https://platform.claude.com/docs/en/api/rate-limits`（讀於 2026-08-12）
每個 response 都帶三族 header，逐字：`anthropic-ratelimit-requests-{limit,remaining,reset}`／
`anthropic-ratelimit-{input,output}-tokens-{limit,remaining,reset}`／
`anthropic-ratelimit-tokens-{limit,remaining,reset}`（後者「display the values for the most
restrictive limit currently in effect」），另有 `retry-after`（429 時）與 Priority Tier 的
`anthropic-priority-*`。`*-reset` 一律 **RFC 3339**。
- 🔴 **本專案適用性：不適用（結構上拿不到）。** 這些 header 掛在**呼叫端自己發出的 API
  response** 上；本專案是 Claude Code 的 **hook**，從不自己發 Messages 請求，那個 response
  不經過我們的行程。⇒ 這條路要成立必須由 harness 轉發，而那正是下面 a-2 的兩個 issue 在要的東西。
- 🔴 **但它給了一個可直接抄的設計判準**：`anthropic-ratelimit-tokens-*` 的「回報**最緊那一條**」
  正是本專案 `binding` 軸的同一個概念——**前沿與我們對「多軸要指名最緊那一條」是同一個結論**（§3.7）。

**a-2【第三方／官方 repo 的使用者議題・僅搜尋摘要】把 rate-limit header 轉發給 hook／statusline 的請求**
`https://github.com/anthropics/claude-code/issues/33820`（Expose API rate-limit response headers
to hooks and status line scripts）與 `https://github.com/anthropics/claude-code/issues/55333`
（Persist `anthropic-ratelimit-unified-5h-*` response headers for hooks/statuslines）。
- 🔴 **誠實劃界：這兩筆我只看到搜尋結果的標題與 URL，未讀內文**，因此**不知道**它們的狀態
  （open／closed／有無官方回覆）。可斷言的只有兩件事：①「hook 拿不到 rate-limit header」
  **不是只有我們有這個問題**，它已被登記為公開議題；② 標題逐字出現 `anthropic-ratelimit-unified-5h-*`
  這個**名字**，而該名字**不在** a-1 那份官方 header 表內 ⇒ 存在一族與「5 小時視窗」有關、
  但未文件化的 header。**本專案不得依賴它**（同 `api/oauth/usage` 的處境）。
- **適用性：待觀察。** 若哪天官方真的把它轉發給 hook，那會是 R-1 的正解（受支持的通道）。

**a-3【官方・已讀原文】Usage & Cost Admin API ＝ 有官方端點，但對本專案不適用**
`https://platform.claude.com/docs/en/manage-claude/usage-cost-api`（讀於 2026-08-12）
`GET /v1/organizations/usage_report/messages`（token 用量，bucket `1m`/`1h`/`1d`）與
`GET /v1/organizations/cost_report`（USD，僅 `1d`）。
- 🔴 **三個各自獨立、任一個就足以否決它作為本專案取數源的事實**（逐字引用）：
  1. **「The Admin API is unavailable for individual accounts.」** 本專案跑在個人訂閱帳號上 ⇒ **結構上不可用**。
  2. 它是**歷史消耗量**，不是**剩餘額度**：全篇只有 `starting_at`／`ending_at` 的區間查詢，
     **沒有任何「還剩多少 / 何時 reset」的欄位**。要算水位得自己知道分母——而分母正是
     訂閱制不公開的那個東西（對照 §1.2：`api/oauth/usage` 是**伺服器直接回百分比**）。
  3. 新鮮度：「Usage and cost data typically appears **within 5 minutes**」＋建議輪詢
     **每分鐘一次** ⇒ 對「派工前一秒問一次」這個用途，延遲量級不對。
- **適用性：不適用。** 它解的是 FinOps／事後歸帳，不是**派工前的節流決策**。

**a-4【官方・已讀原文（僅為 a-1 頁內的交叉引用）】另有兩支官方 API，皆非「當前用量」**
同頁逐字指向 `Rate Limits API`（`/docs/en/manage-claude/rate-limits-api`，用途逐字是
「read your **configured** rate limits」＝讀**設定值**不是讀用量）與
`Claude Code Analytics API`（`/docs/en/manage-claude/claude-code-analytics-api`，per-user
估計成本與生產力指標，組織級）。**兩者本回合皆未開啟原文**，僅由 a-1／a-3 頁內連結與說明得知。

> 🔴 **子題 a 的總結論（這是本節最重要的一句，直接決定 R-1 怎麼收）**：
> **「查詢個人訂閱帳號當前額度水位與 reset 時刻」這件事，2026-08-12 當下沒有任何官方文件化的端點。**
> 官方的三條路各自解別的問題：header 解「我這次請求的即時餘量」（但 hook 拿不到）、
> Usage/Cost API 解「組織的歷史帳」（個人帳號不可用）、Rate Limits API 解「我的設定值是多少」。
> ⇒ `api/oauth/usage` **不是一個「懶得找官方替代品」的選擇，它是唯一存在的通道**。
> R-1 的正確處置因此**不是「遷移到官方端點」（沒有這個東西），而是把降級路徑做成一等公民**
> ——這一點把 §3.2 的建議從「找替代」訂正為「驗降級」。

**查無**：Claude Code 是否輸出 **OpenTelemetry token 指標**——本回合**未檢索到**任何官方頁面
（a-3 頁列了 Honeycomb「through OpenTelemetry」的合作整合，但那是 **API 組織用量**的整合，
不是 Claude Code 本地 session 的 context 水位）。⇒ **這一格留白，不以印象補**。

---

### 2.2 子題 b — 水位 → 行為調節

**b-1【第三方・僅搜尋摘要】HiveMind: OS-Inspired Scheduling for Concurrent LLM Agent Workloads**
`https://arxiv.org/html/2604.17111v1`（另有 PDF `https://arxiv.org/pdf/2604.17111`）
搜尋摘要逐字給出它宣稱的**五個排程原語**：admission control via condition variables／
**provider-aware rate-limit tracking**／**AIMD backpressure with circuit breaking**／
**per-agent token budgets**／priority queuing with dependency DAGs。
- 🔴 **誠實劃界：未讀原文**，不知其實驗設計與結論強度。可用的只有「這五個名字」這個結構線索。
- **適用性：高，且它同時是對本專案的一份體檢表。** 逐項對照見 §3.7——本專案有第 2、4 項的對等物，
  **缺第 3 項（AIMD 的乘性減）與第 5 項（依賴 DAG 的優先佇列）**，第 1 項只有粗糙版（滾動視窗計數）。

**b-2【第三方・僅搜尋摘要】AIMD 驅動自適應併發，訊號取自正規化的 `ratelimit-remaining`**
`https://dev.to/supertrained/designing-agent-fleets-that-survive-rate-limits-a-production-architecture-guide-2ign`
與 `https://tianpan.co/blog/2026-04-12-backpressure-in-agent-pipelines-when-ai-generates-work-faster-than-it-can-execute`。
摘要逐字：「Adapt concurrency using AIMD, driven by the normalized ratelimit-remaining header」、
「Throttle with a **distributed token bucket** so all agent workers **share one quota view**」、
以及「Before the orchestrator spawns a new sub-agent…, it checks the remaining token budget,
the current rate limit headroom, and the depth of pending work」。
- **適用性：直接對得上，而且有一項我們已經做到了**——「所有 worker 共用一份額度視野」
  正是本專案 `tools/lib/quota_ledger.py` 的派發帳（**本回合實測它是跨 session 共用的**，見 §2.5）。
- 🔴 **但「AIMD」這個形狀我們只有一半**：本專案的加速是**乘性**（`pace_near=2.0`），
  減速也是**乘性**（`pace_far=0.5`）＝MIMD，而 AIMD 的整個要點是**不對稱**（加性增、乘性減），
  理由正是猜錯的代價不對稱。這強化了 §3.4(b) 的建議，且現在**有外部對照了**（此前只有我們自己的推理）。
- 🔴 **另一個我們沒有的東西：「pending work 的深度」**。前沿在派工前看三個量（餘量／
  rate-limit headroom／**待辦深度**），本專案只看前兩個。第三個量會改變結論：同樣 cap=4，
  待辦 3 件與待辦 300 件應該給不同的建議。**列為新缺口 R-9。**

**查無**：把「用量%」直接接到**模型選型**（水位高就自動降到小模型）的**官方或具名開源實作**。
搜尋摘要只提到 Bifrost 的 **API key 池**加權分流（`https://www.getmaxim.ai/articles/top-5-tools-to-tackle-rate-limiting-for-llm-apps/`），
那是**換一把鑰匙**不是**換一個模型**，兩件事不可混為一談。⇒ 這一格**查無**。
（本專案的節流訊息末句「或降扇出／**切小模型**」是**給人的建議**，不是機制——誠實記在 §3.7。）

---

### 2.3 子題 c — 長時任務跨額度視窗的續航

**c-1【第三方・僅搜尋摘要】durable execution 是 2026 的既成產業形態，而不是新鮮事**
`https://temporal.io/blog/temporal-langgraph-plugin-durable-execution`、
`https://www.diagrid.io/blog/checkpoints-are-not-durable-execution-why-langgraph-crewai-google-adk-and-others-fall-short-for-production-agent-workflows`、
`https://zylos.ai/research/2026-04-24-durable-execution-agent-runtimes/`。
摘要點名的引擎：Temporal／Restate／Inngest／Hatchet／DBOS／Cloudflare Workflows／
AWS Lambda Durable Functions／Azure Durable Task；agent 框架側：LangGraph（checkpointer ＋
`thread_id`）／OpenAI Agents SDK／AutoGen／CrewAI／Dapr Agents／Microsoft Agent Framework。
- 🔴 **關鍵區辨（這是本子題的核心，也是本專案最容易被誤判成「落後」的地方）**：
  上述全部解的是「**行程死掉之後從最後一個 checkpoint 續跑**」。
  本專案要解的是「**行程沒死，但伺服器在未來某個牆鐘時刻之前不會再服務我**」。
  **兩者不是同一個問題**：前者的觸發是*失敗事件*，後者的觸發是*時間*。
  ⇒ 前沿的 durable execution **不能直接搬過來**；能搬的是它的**耐久計時器**（見 c-2）。
- 「不依賴 session 存活」那一類的共同解法是**把耐久性放在外部服務**（Temporal server 重派、
  LangGraph 的 checkpointer 存 DB）。本專案的對等物是 **OS 排程器（launchd／schtasks）＋
  磁碟任務書**——**同構，只是把「外部服務」換成了「作業系統」**，因為本專案不可能要求
  掌舵者跑一台 Temporal server。**這是刻意的取捨，不是缺陷。**

**c-2【第三方・僅搜尋摘要】前沿真正對應「等 reset」的原語是 durable timer，不是 checkpoint**
同上 Temporal 來源，摘要逐字：「There are production agents on Temporal that run for months
right now.」——能跑數月的東西必然帶**耐久睡眠**（workflow 睡到某個時刻、期間不佔 worker）。
- **適用性：概念適用、實作不適用。** 本專案的 `--arm-sentinel` ＋ `StartCalendarInterval`
  就是這個原語的**單機版**。⇒ **不建議引入工作流引擎**（為了一個計時器背一台 server 是
  本 repo 判過的過度設計），但**建議承認我們做的就是 durable timer**，並照它的標準檢驗：
  耐久計時器的驗收就是「**它真的會在那個時刻醒**」，而那正是 §3.5 指出今天**零覆蓋**的那一格。
- 🔴 **一個前沿有、我們沒有的具體風險**：c-1 的 LangGraph 摘要逐字提到
  「if two processes try to resume the same `thread_id` simultaneously…LangGraph has no built-in
  coordination」。本專案的同型風險是**兩支哨兵同時判到同一次撞線**。**列為新缺口 R-10**
  （本回合**未驗證**現行 `claim_once` 是否已涵蓋，見 §6）。

---

### 2.4 子題 d — context 壓縮

**d-1【官方・已讀原文】伺服器端 Compaction 已是受支持的 API 功能**
`https://platform.claude.com/docs/en/build-with-claude/compaction`（讀於 2026-08-12）
`context_management.edits[].type = "compact_20260112"`。逐字要點：
- **觸發**：`trigger = {"type": "input_tokens", "value": 150000}`；`input_tokens` 是**唯一**支援
  的觸發型別，預設 **150,000**，**最小 50,000**（強制）。
- **保真度取捨（官方自己寫的）**：產生一個 `compaction` block（`<summary></summary>`），
  且「**all content blocks before it are ignored**」＝**先前內容整批丟棄**，不是分層保留。
- **旋鈕**：`instructions`（自訂摘要 prompt，**完全取代**預設）、`pause_after_compaction`
  （產生摘要後暫停，`stop_reason: "compaction"`，讓呼叫端自己挑要留哪幾則）。
- 🔴 **對本專案最關鍵的一句**：「**Compaction requires an additional sampling step, which
  contributes to rate limits and billing.**」⇒ **壓縮本身要花額度**。
  而且 `usage.iterations` 才是真帳，頂層 `input_tokens`／`output_tokens` **不含**壓縮那一次。
- **適用性：機制不適用、判準適用。** 本專案不是 API 呼叫端（壓縮由 Claude Code harness 自己做，
  本專案只能觀測 `--check-autocompact`）。但那句「壓縮要花額度」**直接證偽**了一個很容易犯的直覺：
  「水位高就多壓縮一點」——在額度緊的時候壓縮**會讓事情更糟**。
  ⇒ 本專案 90% 那道門「停止開新戰場、只做收斂」的方向是**對的**，而「到 90% 就自動 `/compact`」
  這種提案**不該採納**。**這是本輪唯一一筆用外部證據否決掉一個未來提案的發現。**

**d-2【第三方・僅搜尋摘要】Claude Code 的壓縮不是一招，是一條管線**
`https://decodeclaude.com/compaction-deep-dive/`、`https://www.x-cmd.com/blog/260617/`、
`https://arxiv.org/html/2604.14228v1`（Dive into Claude Code: The Design Space…）。
摘要點名**五段**：單一 tool output 的預算削減／`Snip`（時間深度）／**`Microcompact`**
（去重舊 tool result、清 thinking block，**無模型呼叫**）／context collapse（超長歷史）／
auto-compact（語意壓縮）。
- 🔴 **未讀原文，且這三筆都是第三方對閉源行為的逆向描述** ⇒ **不得當成契約**。
- **適用性（概念）：高。** 它給出一個本專案可以借用的排序原則：**先做不花模型的那幾種**
  （去重、丟棄舊 tool 結果），**最後才做要花一次 sampling 的語意摘要**。這與 d-1 的
  「壓縮要花額度」是同一個結論的兩面。

**查無**：壓縮**保真度**的量化評估（摘要後任務成功率掉多少）。搜尋結果只有一筆標題暗示
（x-cmd 那篇的標題逐字「AI Coding Agents Getting Worse Over Time?」），**未讀原文、不引用**。

---

### 2.5 🔴 本節在檢索過程中**意外量到**的一件本專案事實（不是外部資料）

執行本節的 WebSearch／WebFetch 時被本專案自己的額度守衛擋下 **4 次**（逐字：
`每 300s 最多 4 次扇出，本視窗已用 4 次 ⇒ WebFetch 本次不執行`）。追查派發帳
（`tools/lib/quota_gate.py:fanout_ledger_path()` → `$TMPDIR/autosdd_quota_dispatch.d`）發現：

| 實測 | 值 |
|---|---|
| 帳本位置 | 系統暫存目錄，**路徑不含 session id** |
| 本包送出的扇出 | 1（09:00:47 那一筆） |
| 同一視窗內的其他 3 筆 | **不是本包送的**——來自 R85 同輪的其他並行包 |

⇒ **派發帳是「機器全域」的，跨 session 共用。** 這與 §2.2 的 b-2「all agent workers share
one quota view」**正好是同一個設計**，所以它**是對的**（額度本來就是帳號級的，不是 session 級的）。
🔴 **但它有一個沒被寫下來的後果**：`FANOUT_WINDOW_SECONDS=300` × `cap` 是**全機共用**的預算，
於是 **N 個並行包的人均扇出預算是 `cap/N`**。本輪 N=6、cap=4 ⇒ 人均 0.67。
**調研型的包（大量 WebSearch／WebFetch）在並行波中會被結構性餓死**，而它的表徵是
「一直被擋」，看起來像額度很緊，實際上是**同輪兄弟把視窗吃滿了**。
- 本包的處置（可複製）：不硬闖、不碰 `AUTOSDD_QUOTA_GUARD_OFF`，改成**先零成本讀帳本、
  有空位才送**（`until` 迴圈阻塞在派發帳計數上）。這條路**零 token**且不製造幽靈計數。
- **列為新缺口 R-11**：節流訊息今天說「本視窗已用 4 次」，但**不說那 4 次是誰用的**。
  一句「其中 N 次來自其他 session」就能讓人不去誤調門檻。**這是 §3.4(a-2) 同型的可見性問題。**

---

## 3. Gap 分析與可實作提案

### 3.1 提案總表

| # | 缺口 | 嚴重度 | 持有面（常數／史料／消費端） |
|---|---|---|---|
| R-1 | 取數端點未公開文件化，且**無降級路徑測試** | **高** | `tools/lib/quota_meter.py`（P2） |
| R-2 | 現查 probe rc=1（§1.5） | **高** | `tools/probe/`＋`tools/lib/quota_limits.py`（P2） |
| R-3 | 6d 端到端零驗證（§3.5） | **高** | `tools/tests/`＋`tools/lib/schedule_backend.py`（P2） |
| R-4 | 6e 睡著的 Mac（§3.6） | 中 | `tools/lib/endurance_env.py`（P2） |
| R-5 | 6b 加速前提未被機械釘住（§3.4a） | 中 | `tools/lib/quota_policy.py`（P2） |
| R-8 | 🔴 **週軸 ≥50% 時加速結構上到不了，且畫面上看不出來**（§3.4a-2，本包實測兩個時刻） | **中高** | `tools/lib/quota_policy.py::describe`（P2） |
| R-6 | 根 `.env` 不存在 ⇒ 6f 從未執行（§4） | **已關閉**（R85／P10 建立並實證生效，§4.1） | **人為動作**，非程式 |
| R-7 | 快取過期＝不節流 | **已關閉**（讀碼複驗，§3.3） | `tools/lib/quota_gate.py`（P2） |
| R-9 | 🔴 派工決策**不看「待辦深度」**——前沿看三個量，我們只看兩個（§2.2 b-2） | 中 | `tools/lib/quota_policy.py`（P2）＋ 待辦來源（今天不存在） |
| R-10 | 兩支哨兵可能同時判到同一次撞線（LangGraph 同型風險，§2.3 c-2）；**本輪未驗證** `claim_once` 是否已涵蓋 | 中 | `tools/lib/quota_ledger.py`（P2） |
| R-11 | 🔴 節流訊息說「本視窗已用 4 次」但**不說那幾次是誰用的**——並行波中人均預算＝`cap/N`，被擋的人會誤以為是自己的水位問題（§2.5） | **中高** | `tools/lib/quota_gate.py::quota_throttle_message`（P2） |

### 3.2 R-1 — 取數端點的脆弱性

`api/oauth/usage` 不在 Anthropic 任何公開 API 文件內（**§2.1 已完成查證**）。它是 Claude Code
自用端點，**可以在任何一次 CLI 更新後改變 schema 或消失**，而失效表徵是 `pct=None`＝「量不到」。

🔴 **R85／P10 訂正本節的處置方向（原文隱含「應該找官方替代品」，而查證結果是沒有這個東西）**：
§2.1 逐條查完官方三條通道——rate-limit header（hook 拿不到）、Usage & Cost Admin API
（逐字「unavailable for individual accounts」，且只有歷史消耗、無剩餘額度）、Rate Limits API
（讀**設定值**不是讀用量）——**沒有任何一條能回答「我這個個人訂閱帳號的當前水位與 reset 時刻」**。
⇒ `api/oauth/usage` **是唯一存在的通道，不是偷懶的選擇**。
**這把 R-1 的正解從「遷移」改成「把降級路徑做成一等公民並真的驗它」**，也就是下面那段驗收憑證
——它從「順便做」升級為**本項唯一的處置**。

repo 自陳已處理「量不到」（`degraded_cap`），但本包**未複驗**該路徑。建議驗收憑證：
注入 `USAGE_URL` 指向一個回 404／回 schema 不符的本機 stub，斷言
① `--pace` 仍 rc=0；② 印出的 cap **等於 `degraded_cap`** 而不是 `None`／不設限；
③ stderr 明說「量不到」。**假紅代價低**（純注入，不碰網路、不碰真帳號）。

### 3.3 R-7 — 「快取過期就等於全數放行」是否真的關掉了：**靜態複驗通過**

不採信檔頭自陳，逐點讀碼複驗（`tools/lib/quota_gate.py`），四段接得起來：

| 段 | 座標 | 實查所見 |
|---|---|---|
| TTL | `:101` | `QUOTA_CACHE_TTL_SECONDS = 180` |
| 過期 ⇒ 量不到 | `:290-295` | 超過 TTL 回 `_blank("stale-cache")`，**不是**回舊值、也不是回不設限 |
| 量不到 ⇒ 有 cap | `quota_policy.py:464-468` | `axes == ()` ⇒ `cap = rec = max(1, degraded_cap)`（C1 印出 `=4`），且**永不 halt** |
| 補量 ＋ 出聲 | `:434-450`、`:381-408` | 只在扇出型工具、每 TTL 至多一次（`claim_refresh_slot`）同步 `measure()`；失敗走 `note_degraded()`，且出聲帶 per-source TTL 閂鎖（避免每次呼叫都吵而被整個關掉） |

⇒ **R81 的修法確實在磁碟上**，「過期＝全數放行」這個病已關閉。
🔴 **誠實劃界：這是讀碼複驗，不是動態注入。** 本包**沒有**把快取 mtime 推老再觸發 `Agent`
去觀察它真的走了那條路。要升級成端到端憑證，驗收長這樣：推老 mtime → 觸發一次扇出型工具 →
斷言 `autosdd_quota_degraded.jsonl` 真的長大，且該次派發的 cap **等於 `degraded_cap`**。

### 3.4 🔴 6b 演算法本身是否最優（掌舵者「以最佳化進行設定調整」）

**現行形狀**（`quota_policy.py`，實查）：

```
cap  = min(逐軸 _cap_for(band_i, horizon_i))          ← 煞車，取最緊
pace = max(逐軸 _mult(horizon_i))                      ← 加速，取最短期程
       ↳ 但若有任一軸「期程不明 **且** cap 非 None」⇒ pace 夾在 1.0（fail-closed）
rec  = min( clamp(min(逐軸 _base_rec(band_i)) × pace), cap )
```

**評價：這個形狀是對的，而且它已經解掉了一個非顯而易見的病。** 把 `rec` 也寫成
`min(逐軸 rec)` 會讓長期程軸（weekly 的 horizon 幾乎恆為 far ⇒ ×0.5）永遠 binding，
短期程軸的 ×2 一次都出不來——也就是掌舵者的錨點①「剩 30 分鐘還有 100% 沒用 ⇒ 多派」
在**任何**水位下都到不了。把「稀缺度」與「節奏」拆成兩個各自聚合的量是正解。

**但有三個可改進點，逐條給修法與代價：**

**(a) 🔴 加速的正當性依賴一個未被釘住的前提。**
「reset 快到了 ⇒ 用力派」只有在額度視窗是**固定區塊**（block 到期即整批歸還，use-it-or-lose-it）
時才成立。若計費改成**真正的滑動視窗**（sliding window，過去 N 小時的積分），那麼此刻多派
會等比例延後恢復 ⇒ **`pace_near` 的正負號要反過來**。repo 已量測到「錨在該區塊第一次用量」
（＝區塊模型），所以今天成立；但這個前提**只活在散文裡**，沒有任何機械物釘住它。
- 🔴 **本輪已把這個前提量出來了**（§1.6 結論 3）：7 個相異 reset 字面含 `4:20pm`／`5:50pm`／
  `3:20am`，**沒有一個落在 5 小時固定格點上** ⇒ 區塊錨定成立、`pace_near` 的正負號今天是對的。
  缺的不是證據，是**把這個證據接成一個會轉紅的東西**。
- 🔴 **R85／P10 補一筆外部證據，而它讓這個前提比原本更危險，不是更安全**（§2.1 a-1，已讀原文）：
  官方 rate-limit 文件逐字寫 **「The API uses the token bucket algorithm… your capacity is
  continuously replenished up to your maximum limit, rather than being reset at fixed intervals.」**
  ⇒ **Anthropic 明文說它那一側是連續補充（滑動），不是固定區塊。**
  這**不直接推翻**本專案的前提，因為那句話講的是 **API tier 的 RPM/ITPM/OTPM**，
  而本專案量的是**訂閱方案的 session／5h／7d 額度桶**（`api/oauth/usage`），兩者是不同的系統
  ——§1.6 量到的 7 個非格點 reset 字面仍然支持訂閱側是**區塊錨定**的。
  🔴 **但它把風險講清楚了**：同一家供應商**同時存在兩種計費形狀**，而 `pace_near>1`
  **只對其中一種成立**。⇒ 「加速」這條規則**必須綁定在「訂閱桶」這個射程上**，
  一旦有人把同一套 `Policy` 套到 API-key 計費的軸上（例如未來多一條 `spend` 之外的 API 軸），
  **`pace_near` 的正負號就是錯的，而且不會有任何東西轉紅**。
- 修法：在 `quota_policy.py` 的 `_mult` 上方立一段具名前提（**逐字寫上「本乘數只對區塊錨定的
  訂閱桶成立；token-bucket 型的軸必須 `pace=1.0`」**），並加一支**證偽探針**——
  以歷史 episode 語料檢查「reset 字面是否落在固定格點上」，若哪天全部對齊到整點格點
  （＝計費改成滑動視窗的訊號），即出聲要求人重新裁決 `pace_near` 的方向。
- 持有面：常數＝`quota_policy.py`；史料＝逐字稿（經 §1.5 修好的 probe）；消費端＝`--pace`。
  🔴 **三者不在同一持有面 ⇒ 依鐵律七，這一項不得派給並行包。**
- 假紅代價：中。語料稀疏時群聚判準會抖 ⇒ 建議做成 **warn-only 探針**，不接閘門 rc。

**(a-2) 🔴 加速今天在實務上幾乎不會發生——本包在 16 分鐘內量到同一台機器的兩個時刻，證據如下。**

| | 08:39 快照（C2） | 08:55 快照（同一 session，本包第二次跑） |
|---|---|---|
| `session` | 43%／剩 17 分／band=free／horizon=near／**cap=None** | 56%／**剩 3 分**／band=notice／horizon=near／**cap=16** |
| `seven_day` | 61%／剩 5357 分／band=notice／horizon=far／cap=4 | 62%／剩 5343 分／band=notice／horizon=far／**cap=4** |
| 結果 | `cap=4 rec=4 binding=seven_day` | `cap=4 rec=4 binding=seven_day` |

第二個快照是**加速條件的極大值**：5 小時軸只剩 **3 分鐘**就 reset、water 56%＝還有 44% 會被丟掉
（教科書級的 use-it-or-lose-it）。演算法**也確實算出了加速**——該軸 `cap=16`（＝`8 × pace_near 2.0`，
撞到 `max_fanout`）。但最終 `rec` 仍是 **4**，因為 `seven_day` 的 `far × 0.5 = 4` 是 binding。

⇒ **不變式：只要任何一條週級軸 ≥ `notice_pct`(50%)，5 小時軸的加速就完全表現不出來。**
（週軸 horizon 恆 far ⇒ cap = `_base_cap(band) × 0.5`；notice 帶 ⇒ 4，而 free 帶的 5 小時軸
加速後最多也只是被夾到 4。）掌舵者的錨點①「還有 100% 沒用就應該可以加速」在
**週軸過半之後結構上到不了**。

**(a-3) 🔴 R85／P10 把 (a-2) 從「兩個時刻的快照」升級成「掃描出來的不變式」，並訂正它的措辭。**

(a-2) 是兩個實測快照，說服力受限於「那兩個時刻恰好如此」。本包直接對 `decide()` 掃描
（純函式、零 I/O、零額度；載具＝`.venv/bin/python`＋`tools/lib/quota_policy.py`，本回合 rc=0）：

| 週軸 `seven_day` % | 該軸 band | 該軸 cap | **最終 rec** |
|---|---|---|---|
| 0 / 30 / 49 / **49.9** | free | None | **16** |
| **50.0** / 51 / 63 / 69 | notice | 4 | **4** |
| 70 | converge | 2 | 2 |
| 85 | prepare | 1 | 1 |
| 95 | halt | 0 | 0 |

（5 小時軸固定在**加速條件的極大值**：`0%`、剩 3 分鐘。）

**兩個比 (a-2) 更強的結論：**
1. **懸崖恰好落在 `notice_pct`（50.0），而且是 4 倍。** 週軸 49.9% ⇒ `rec=16`；50.0% ⇒ `rec=4`。
   **0.1 個百分點的移動讓可派數掉成四分之一。** 這不是漸進收斂，是階梯的第一階就砍 4 倍。
2. **越過之後，5 小時軸的期程完全隱形。** 固定週軸 63%（＝本回合真實水位），把 session 軸的
   reset 由 **1 分鐘掃到 297 分鐘**，`cap=4 rec=4 binding=seven_day` **逐格相同**——
   也就是掌舵者錨點①「剩 30 分鐘就 reset、還有 100% 沒用 ⇒ 加速」在**整個過半的那一週內
   一次都不會發生**。本回合實測週軸 63%、距 reset **5,336 分鐘（約 3.7 天）** ⇒ 本專案**此刻**
   就在這個死區裡，而且會待上數天。

**這是不是 bug？本包獨立複核後同意 P8 的判讀：不是 bug——而且理由比 P8 給的更強。**
P8 的理由是「週額度是更稀缺的資源」。**那個理由不足**（稀缺不等於該否決加速）。
真正的理由是**加速的前提在這裡根本不成立**：`pace_near>1` 的正當性是 **use-it-or-lose-it**
——5 小時區塊到期未用就蒸發。但**當週軸是 binding 時，沒有東西會蒸發**：
省下來的用量留在週視窗裡，下一個 5 小時區塊照樣可以花。
⇒ **「不用會浪費」這個前提只有在「近 reset 的那一軸同時也是最緊的那一軸」時才為真。**
現行 `rec = min(base × pace, cap)` 的 `min` 恰好就是在表達這件事，**所以它是對的，不是妥協**。

🔴 **本輪把上面這句話定為明文政策（此前它只活在程式的形狀裡，沒有任何一份文件寫過）：**
> **政策 P-1（加速的射程）**：`pace` 的加速只在「最短期程的軸同時是 binding 軸」時才有實效。
> 當較長視窗的軸 binding 時，加速被 `min` 吃掉是**正確行為**——因為此時未使用的短視窗額度
> 並不會蒸發，它留在長視窗裡。⇒ **不得**為了「讓加速看得見」而把 `rec` 改成不受 `cap` 拘束。

但 R84 才剛修過**同型**的病（`_pace_of` 的 null 軸否決權讓加速「結構上到不了」），
而這一次的「到不了」**不在任何文件裡**——`--pace` 印得出 `cap=16`，人會以為加速生效了。
**⇒ 缺的不是修演算法（P-1 說它是對的），是修可見性。**
- 建議修法（**低成本、不動演算法**）：`describe()` 在「某軸算出的 cap 明顯高於最終 cap」時
  多印一句，例：`（session 軸本可派 16，被 seven_day 夾到 4）`。把「為什麼沒有加速」
  變成畫面上看得見的一句話，而不是要人自己回去讀 `_binding_key`。
- 🔴 **R85／P10 訂正這個判準的形狀（照原文寫會在今天的水位下完全不觸發）**：原文的條件是
  「某軸算出的 **cap** 明顯高於最終 cap」，而**本回合實測 session 軸是 `0%` ⇒ free 帶 ⇒ `cap=None`**
  ——`None` 不「高於」4，條件不成立，這句話一次都不會印。**而這正是最需要印的那個情境**
  （水位 0%、額度整塊要蒸發、卻只能派 4 個）。
  ⇒ 判準應改為**反事實的 `rec`**：`rec_without_binding = decide(移除 binding 軸)`，
  當它 `> rec` 時印 `（若不計 seven_day 本可派 16，實得 4）`。
  本回合已實測這個反事實值算得出來且穩定（移除週軸後 `rec=16`，載具同 (a-3)）。
- 持有面：`tools/lib/quota_policy.py` 的 `describe()`（P2）。單一持有面，可派工。
- 假紅代價：零（純輸出，不改判定）。

**(b) 係數是「挑的」，而掌舵者要的是「依實務調到最佳」。**
`pace_near=2.0`／`pace_far=0.5` 今天由方向與單調性守著（`policy_monotonicity_problems`），
**數值本身零依據**。前沿的對應物是壅塞控制（見 §2.3）：AIMD 的不對稱性——
**乘性減、加性增**（急煞、緩加）——正是為了「猜錯時的代價不對稱」。
本專案的代價同樣不對稱：**少派只是慢，多派會撞線並打死整批扇出**（R80 實測一次撞線
16 秒內全部 subagent 掛掉）。
- ⇒ **建議把 `pace_near` 由「乘 2」改成「加性」**（例：`rec = base + k`，`k` 小且可調），
  而 `pace_far` 維持乘性（0.5）。這樣就從「對稱的乘性雙向」變成教科書 AIMD 形狀。
- 代價誠實講：這會**改變掌舵者原話「就可以多派」的手感**（加性比乘性保守）。
  ⇒ 建議**先量再改**：加一支影子紀錄，記下每次 `--pace` 的 `(pct, minutes, rec)` 與
  「該輪最後有沒有撞線」，累積數輪後再決定係數。**沒有這份語料之前不要動數值**——
  否則只是把一組挑的數字換成另一組挑的數字。

**(c) `_base_rec` 只吃 band，不吃「還剩多少絕對餘量」。**
`band` 是 5 段階梯，同一段內 51% 與 69% 給出完全相同的建議。前沿（見 §2.3）的作法是連續函式。
- 誠實評估：**這一點建議不改**。階梯的可解釋性正是它在本 repo 存活的理由（掌舵者的原話
  本身就是階梯：50 注意／70 收斂／85 準備／95 停止），改成連續函式會讓「為什麼是 4 個」
  變成不可口頭解釋的東西。**列為已評估並否決，不列為缺口。**

### 3.5 🔴 6d 端到端驗證的具體設計（本包的主要交付之一）

**今天的邊界在哪（實查）**：`tools/tests/test_context_budget_guard.py:2721` 逐字寫

> 「排程註冊必須被攔下來：這一組測試若真的去建 schtasks，它就成了一支會在開發者機器上
> 留下垃圾工作、且在 CI（Linux）上必紅的測試。」

於是 `_register_and_record` 被 `_swap` 成 `_register()`，回 `(0, "FAKE-NEXT-RUN")`。
**這個決定是對的**，但它的淨效果是：**「撞線 → 判 arm_reset → 呼叫註冊」有覆蓋，
「排程器真的收下了一個會在 reset_at 觸發的工作」零覆蓋**。C9 證明武裝路徑在真機能跑，
但那是**巡邏**哨兵，不是**由撞線觸發轉成續航**的那一支。

**提案：一支 opt-in 的載具級 e2e（`AUTOSDD_E2E_CARRIER=1` 才跑，預設 skip、CI 永遠 skip）**

注入點**今天就已經存在，不需要改 production 程式**——這是本提案最重要的一句：

| 注入軸 | 既有出口 | 注入什麼 |
|---|---|---|
| 逐字稿 | 狀態塊的 `transcript` 欄（`_sentinel_tick` 第 1257 行讀它） | 合成一支 `.jsonl`，內含一筆**真形狀**的 session-limit 事件（帶 `resets <未來時刻>`）且**其後無復原證據** |
| 任務書 | `--plan <絕對路徑>` | 滿足 `relay_problems()` 全部必填鍵；`reset_source` 必須是 `transcript-verbatim` |
| 痕跡落點 | `AUTOSDD_TRACE_DIR` | 指到沙箱 ⇒ 不碰 `~/.autosdd/traces` |
| 排程名 | `--task-name` | `AutoSDD_E2E_<pid>_<rand>`，**與 `AutoSDD_Sentinel_*` 前綴不同** |

**斷言鏈**（缺一則這支測試沒有守住它宣稱要守的東西）：
1. 痕跡出現 `sentinel_decided action=arm_reset`（判定對）；
2. 痕跡的 `credential` 欄**非空**（憑證優於 rc，同 `relay_problems` 判準）；
3. **mac**：`launchctl print` 該 label 的 plist 真的帶 `StartCalendarInterval`，且時刻
   ＝`reset_at + RESET_SKEW_SECONDS`（±1 分鐘）。🔴 這一條是核心——R83-B 的判例正是
   「四個相異 `at` 值產出同一份 plist」，而只斷言 rc 或只斷言痕跡**看不到**那個 bug；
4. **Windows**：`Get-ScheduledTask | Get-ScheduledTaskInfo` 的 `NextRunTime` 非空且相符
   （**靜態推論、未在真機驗證**）；
5. `addCleanup` 移除該工作，**並斷言移除後查不到**（洩漏偵測）。

**會不會污染真實痕跡——逐項回答（這是任務書明問的）：**

| 污染面 | 會嗎 | 為什麼 |
|---|---|---|
| 逐字稿母體（`reset_window_distribution` / `audit_session` 的分母） | **不會，但有一條硬紅線** | 那兩支掃的是 `project_transcript_dir()`＝`~/.claude/projects/<slug>/`。合成逐字稿只要**寫在系統暫存**就完全不在分母內。🔴 **必須把「fixture 路徑不得位於真實 project dir 之下」寫成測試自己的第一條斷言**——否則哪天有人為了「更真實」把它搬進去，就會把合成撞線注入所有歷史分析，而那是**不可逆**的語料污染 |
| `~/.autosdd/traces` | 不會 | `AUTOSDD_TRACE_DIR` 逃生口既有 |
| 系統暫存的任務書殘骸 | 不會 | 沙箱 + `escalation.gc_plans` 已有導向沙箱的既有作法（第 2712 行） |
| **真實排程器** | 🔴 **會，這是唯一的真風險** | 這支測試**必須**真的建一個 job（不建就等於沒測到）。三道防護：專屬名稱前綴、`addCleanup` 移除、洩漏斷言。並**明文禁止**該測試呼叫 `--remove-schtasks` 的預設 task 名（那會拆掉活著的哨兵） |
| 桌面通知 | 不會 | `arm_reset` 分支不叫人（只有 `escalate` 才 `alert`） |

**持有面**：`tools/tests/`（新檔）＋ 可能需要 `schedule_backend.py` 開一個唯讀的
「回讀這個 label 的觸發時刻」查詢函式（若今天沒有）。**兩者都在 P2**，故本項**可以**派給單一包。

### 3.6 🔴 6e 的 mac 側 — 不改機器設定的前提下還有什麼形狀

**先把邊界講準**（本回合實測）：本機 `pmset -g custom` **只有 `AC Power` 一段**（C6）
⇒ 這是**桌機**，且 `sleep 0`＝插著電就不會系統睡眠。`sleep_trouble()` 回空字串（C10）。
⇒ **在這台機器上，6e 的睡眠風險今天實質為零**。但這是**這台機器的現況，不是本專案的保證**
（`posture_note()` 自己就是這樣講的，措辭正確）——換一台筆電就成立。

**三個候選形狀，逐個評估：**

**形狀 A：`caffeinate` 有界斷言（建議採用）**
`/usr/bin/caffeinate` **不需 sudo**（C12），且它**不改任何持久設定**——assertion 隨行程結束即消失。
⇒ 它完全不在「掌舵者已否決的改動電源設定」射程內：那條否決針對的是 `pmset repeat`（需 sudo、
**持久**、會改變掌舵者機器的行為）；`caffeinate -t` 是**行程生命期內、且自帶逾時**的暫時斷言。

- 用法：判定 `arm_reset` 時，若 `reset_at - now` 在合理範圍內，detached spawn
  `caffeinate -s -t <秒數 + margin>`；把它的 pid 記進續航痕跡。
- 🔴 **`-s` 的兩個硬限制必須寫進 docstring，不得靜默**（man page 逐字，C12 實讀）：
  ① `-s` **只在 AC 電源下有效**——而「在電池上」正是最需要它的情境 ⇒ 它**治不了筆電拔線**；
  ② caffeinate **不能喚醒已經睡著的機器**，它只能「阻止即將發生的睡眠」。
- ⇒ 誠實定位：**這是把「闔蓋前就已進入等待」那一段的失效關掉**，不是「睡著也會醒」。
  它把 6e 從「失效可偵測」推進到「**一部分失效被真的關掉**」，但**不宣稱**完成 6e。
- 逾時上界建議綁到**量測到的最長 episode**：§1.6 實測 max=**286.9 分** ⇒ 建議
  `-t` 取 `min(reset_at - now + margin, 300 分)`。無界的 caffeinate 會把機器永久卡醒，
  那是新的傷害；而 300 分這個硬頂**必須隨 §1.6 的 max 棘輪一起調**，不得寫死後遺忘。
- 持有面：`tools/lib/endurance_env.py`（判準與 spawn）＋ 痕跡欄位。單一持有面，可派工。
- 假紅代價：低。非 darwin 一律不 spawn（同 `sleep_trouble` 既有的平台前置判準）。

**形狀 B：接受延遲，但讓「延遲了多久」變成可稽核的值（建議一併採用，成本近乎零）**
launchd 對錯過的 `StartCalendarInterval` **會在醒來後補跑一次**（repo 已載明）。
⇒ 真正的缺口不是「不會跑」，是「**不知道晚了多久**」。修法：tick 一開始就把
`now - 排定觸發時刻` 算出來寫進痕跡。這讓「Mac 睡了 3 小時」變成一個**可查的數字**，
而不是一段事後推測。**這一項嚴格優於任何猜測性補償**，且不碰電源。

**形狀 C：`pmset -g sched` 讀取（已實測，建議只當觀測不當機制）**
C7 回空 ⇒ 本機零排定喚醒。它可以當 `posture_note()` 的第二個證據來源
（「就算 sleep≠0，只要有 scheduled wake 落在 reset 附近，也還有救」），
但**寫入** `pmset schedule` 需要 root ⇒ **不採用寫入側**。

**明確不建議**：任何形式的「每 50 分鐘醒來看看」。R81/R84 已量測否決（把最壞死等由
15 分放大到 50 分而換不到任何東西），本包沒有任何新證據推翻它。

---

### 3.7 🔴 前沿有 vs 我們有 — 逐項對照（訴求 6z 的驗收面）

> 🔴 **本表的證據強度不均勻，逐列標**：只有標【已讀原文】的那幾列可以引用細節；
> 標【摘要】的列只能斷言「那個東西存在」。**低報與過報一樣貴**，兩個方向都照實記。

#### (甲) 前沿有、我們沒有

| # | 前沿的東西 | 來源／強度 | 我們的現況 | 判讀 |
|---|---|---|---|---|
| G1 | **AIMD 的不對稱**（加性增／乘性減） | b-2【摘要】＋ HiveMind 五原語之一【摘要】 | `pace_near=2.0`／`pace_far=0.5` ＝**乘性雙向（MIMD）** | 🔴 **真缺口。** 代價不對稱（少派只是慢，多派打死整批扇出）⇒ 形狀該是 AIMD。**但先量再改**（§3.4b） |
| G2 | **待辦深度（pending work depth）進入派工決策** | b-2 逐字「remaining token budget, rate limit headroom, **and the depth of pending work**」【摘要】 | 只看前兩個 | 🔴 **真缺口（R-9）**。同樣 cap=4，待辦 3 件與 300 件應給不同建議 |
| G3 | **依賴 DAG 的優先佇列** | HiveMind 原語⑤【摘要】 | 無。派工順序由人決定 | 缺口，但**優先度低**：本專案的並行度上限是個位數，DAG 排程的收益要在高併發才顯著 |
| G4 | **壓縮管線分層**（先做零成本的去重／丟棄，最後才做要花 sampling 的語意摘要） | d-2【摘要，第三方逆向】 | 只有單一門檻（75%／90%；R92 起 84/94，見 ADR-XPLAT-008）＋ 交給 harness 的 auto-compact | 概念缺口。**但本專案不是 API 呼叫端**，能做的只有「建議人怎麼做」，不是機制 |
| G5 | **絕對 token 觸發**（`input_tokens ≥ 150000`），不需要知道視窗多大 | d-1【已讀原文】 | 用**百分比**，而分母要靠推斷（`--check` 實測印 `window 1,000,000（**推斷**）`） | 🔴 **值得重視的設計對照**：絕對值**不需要分母**⇒ 結構上不會因為換模型／換視窗而失準。我們的百分比在分母推斷錯時會靜默失準 |
| G6 | **耐久計時器**是工作流引擎的一等原語 | c-2【摘要】 | 有對等物（launchd／schtasks），但**端到端零驗證**（§3.5） | 缺的不是機制，是**驗收**。前沿對耐久計時器的驗收標準就是「它真的在那個時刻醒」 |
| G7 | 同一 checkpoint 被兩個行程同時 resume 的協調 | c-1 逐字（LangGraph「no built-in coordination」）【摘要】 | 兩支哨兵同時判到同一次撞線？**本輪未驗證** | R-10，**先查再說**，不假設有病也不假設沒病 |

#### (乙) 我們有、前沿（在本輪檢索範圍內）沒有對等物

| # | 我們的東西 | 為什麼算領先 | 誠實限定 |
|---|---|---|---|
| A1 | **多軸同時判讀 ＋ binding 軸具名 ＋ 每軸都帶「距 reset 幾分鐘」** | 官方 header 只做到「回報最緊那一條的**數值**」（a-1 逐字），**不告訴你那是哪一條**；`--pace` 直接印 `binding=seven_day` 並附該軸期程 | 官方 header 與我們解的不是同一層問題（它是單次請求，我們是派工決策），**不是同題較量** |
| A2 | **零 token 的水位查詢**（`--pace` 只讀 180s 快取；端點本身非模型呼叫） | 前沿的 header 方案要**先發一個請求**才拿得到餘量 ⇒ 「查一次就消耗一次」；Usage API 則有 5 分鐘延遲＋每分鐘輪詢上限（a-3 逐字） | 我們的零成本建立在一個**未文件化**的端點上（R-1）。**便宜但脆弱**，兩者要一起講 |
| A3 | **「量不到 ≠ 不設限」**（`degraded_cap`，且**永不 halt**） | 本輪檢索**未見**任何來源討論「取數失敗時該怎麼辦」——這正是最容易靜默放行的一格 | 【查無】不等於【前沿沒有】。只能說**本輪沒檢索到對照** |
| A4 | **憑證優於 rc**（`next_run_time` 非空才准寫 `armed`；mac／Windows 刻意不共用憑證鍵） | 同上，未見外部對照 | 同 A3 的限定 |
| A5 | **跨 session 共用一份派發帳** | 與 b-2「all agent workers share one quota view」**同一設計** ⇒ **這一格我們與前沿平手，不是落後** | 🔴 但缺 R-11 的可見性（不說那幾次是誰用的） |

#### (丙) 用外部證據**否決掉**的提案（本輪唯一一筆）

| 提案 | 否決依據 |
|---|---|
| 「水位高 ⇒ 自動多做 `/compact`」 | d-1 官方逐字：**「Compaction requires an additional sampling step, which contributes to rate limits and billing.」** ⇒ 壓縮**要花額度**。額度緊的時候壓縮**讓事情更糟**。現行 90% 那道門「只做收斂、不開新戰場」的方向是對的，**不要**在額度軸上加自動壓縮 |

---

## 4. 訴求 6f — `.env.example` 參數複審

### 4.1 🔴 「根目錄 `.env` 有沒有消費者」——實查答案：**有，而且不只一個**

| 消費者 | 讀哪一支 `.env` | 實查座標 |
|---|---|---|
| harness／hook 側（額度節流、扇出 cap） | **只讀 monorepo 根 `.env`** | `tools/lib/quota_gate.py:182 policy_env()` → `parents[2]/.env` |
| 逃生口三開關 | 同上（R82 起經 `apply_env_defaults` 前置填充） | `quota_gate.py:208` |
| AutoClaude 引擎（`quota_throttle_pct`／`quota_halt_pct`） | **只讀 `AutoClaude/.env`** | `autoclaude/utils/config.py:31 _quota_env` |

⇒ **掌舵者的直覺是對的，但缺口不是「沒有消費者」，是「檔案不存在」**：C11 實測根 `.env` 不存在
⇒ 今天**全部 14 個政策鍵都走出廠預設**，`.env.example` 印出來的那份東西從未被實際生效過一次。
訴求 6f 逐字要求「copy to `.env` 在根目錄，開始進行測試」——**這一步從未執行**。

### 4.1-bis 🔴 R85／P10：**已執行，且已證明它真的被讀到**（R-6 關閉）

P8 刻意未執行（非其持有面）。本包執行，逐步留證。

**步驟 0 — 先確認 `.gitignore` 涵蓋根 `.env`（不涵蓋就不建）**
```
$ git check-ignore -v .env
.gitignore:35:.env	.env          ← rc=0，第 35 行命中
```
⇒ 涵蓋。`.env` 不會進版控，**本包也未對它做任何 git 操作**。

**步驟 1 — 由 SSOT 生成（不手寫）**
`.venv/bin/python tools/lib/quota_policy.py --print-env-example > .env` ⇒ rc=0，50 行、
17 個鍵（13 政策鍵帶值 ＋ 1 政策鍵留空 ＋ 3 逃生口留空；分類口徑見 §4.4）。

**步驟 2 — 🔴 生效驗證（本節的核心；預設值相同時「讀到了」與「沒讀到」外觀完全一樣）**
只改**一個**門檻（**收緊方向**：`CONVERGE_PCT` 70 → 60），觀察 `band` 與 `cap` 是否真的動：

| 快照 | `.env` 的 `CONVERGE_PCT` | `--pace` 首行（逐字） | rc |
|---|---|---|---|
| **A** 生成後 | `70`（出廠預設） | `現在可派 4 個 agent（硬上限 cap=4）｜band=notice｜最緊的一條＝seven_day 63% 剩 5337 分鐘` | 0 |
| **B** 暫時改值 | **`60`** | `現在可派 2 個 agent（硬上限 cap=2）｜band=**converge**｜最緊的一條＝seven_day 63% 剩 5336 分鐘` | 0 |
| **C** 還原 | `70` | `現在可派 4 個 agent（硬上限 cap=4）｜band=notice｜最緊的一條＝seven_day 63% 剩 5336 分鐘` | 0 |

⇒ **`band` 由 `notice` 翻成 `converge`、`cap` 由 4 掉到 2、還原後完全回復。**
這就是「根 `.env` 真的被 `policy_env()` 讀到」的憑證——**不是**「檔案存在」，也**不是** rc=0。
（水位 63% 三次相同 ⇒ 變的只有政策，排除了「剛好水位變了」這個混淆因子。）

**磁碟現況**：根 `.env` 已存在、內容＝`render_env_example()` 的逐字產物（即全部走出廠預設），
`CONVERGE_PCT` 已還原為 `70`。**沒有任何一個值被本包改成非預設。**

> 🔴 **為何選「收緊」方向做這個實驗**：實驗期間若有並行包正在派工，放寬會讓它們多派 agent
> （真實副作用）；收緊最多讓它們少派，**不會造成不可逆的傷害**。任何在共用工作樹上驗證
> 額度政策的人都該照這個方向做。

---

**（以下為 P8 原文的建議，已由上方 4.1-bis 執行完畢，保留供對照）**
建議指令（**不要 `git add`**，`.env` 已被 pre-commit 三層守衛擋，那是正確的）：

```bash
cd /Users/wuweihong/Antigravity/AISDCL_Agent
.venv/bin/python tools/lib/quota_policy.py --print-env-example > .env
.venv/bin/python tools/session_resume_planner.py --pace     # 應與 C2 相同（因為值＝預設）
```
生效驗證的**憑證**：把某一個門檻暫時改成一個明顯不同的值，再跑 `--pace`，**`band` 必須改變**。
band 沒變＝檔案沒被讀到，而「讀到了」與「沒讀到」在預設值相同時**外觀完全一樣**
——這正是本 repo 反覆判過的假綠形態。

### 4.2 兩份 `.env.example` 的參數集一致嗎？

**不一致，而且這個不一致是刻意且正確的**（本包複審後**同意現況，不建議改**）。

- 根層 SSOT（`quota_policy.py::ENV_SPEC`）：**17 個鍵**（14 政策 ＋ 3 逃生口，見 §4.4）。
- `AutoClaude/.env.example`：只有 **2 個**額度鍵（`CONVERGE_PCT=70`／`HALT_PCT=95`）。

理由（該檔第 150~155 行自陳，本包複驗其邏輯成立）：**引擎不派 agent**
⇒ `NOTICE_PCT`／`CAP_*`／`MAX_FANOUT`／`PACE_*` 在引擎側沒有消費者，抄過去就是**幽靈鍵**。
而該檔**還有一道鎖**在守這件事：`tests/test_r82_quota_axis_and_shipped_defaults.py
::test_every_autosdd_key_in_the_env_example_has_a_real_reader`
——要求該檔每個 `AUTOSDD_` 鍵都必須在 `autoclaude/**` 找得到讀者。
⇒ 「同一份知識住兩個家」這個病在這裡**已經被治過了**，治法是「兩個家各自只放自己有讀者的鍵，
並用鎖釘住」。**這是正確的形狀，本包不建議動它。**

🔴 但有一個**真的**缺口：`AutoClaude/.env.example` 第 120~125 行的優先序說明與根層
`--print-env-example` 印出的那一段**措辭不同**（根層印「env > AutoClaude/.env > 根 .env」；
AutoClaude 側說「hook 側**完全不讀** `AutoClaude/.env`」）。兩句話講的是**不同軸**
（前者是引擎側的合併序，後者是 hook 側的射程），但併排讀會互相矛盾。
- 建議：根層那句加上射程限定詞（「引擎側」）。**1 行文字，持有面＝`tools/lib/quota_policy.py`（P2）。**

### 4.3 門檻現值合理嗎？依據是什麼？

**誠實結論：四道門檻（50/70/85/95）的依據是掌舵者的原話，不是量測。** 這**不是缺點**——
它們是**政策**不是最佳化目標，由人指定是正確的。但兩個**係數**不同：

| 參數 | 現值 | 依據 | 本包評價 |
|---|---|---|---|
| `NOTICE/CONVERGE/PREPARE/HALT_PCT` | 50/70/85/95 | 掌舵者原話逐字 | ✅ 保持。政策由人定 |
| `ACCEL_WINDOW_MINUTES` | 30 | 掌舵者原話「30min Reset」 | ✅ 保持 |
| `FAR_HORIZON_MINUTES` | 360 | 原自陳無依據 → **本輪量到依據了** | ✅ 保持，見下 |
| `PACE_NEAR / PACE_FAR` | 2.0 / 0.5 | **無依據**（檔內自陳「這三個數字是挑的」） | ⚠️ §3.4(b)；G1 補了外部對照 |
| `CAP_NOTICE/CONVERGE/PREPARE` | 8/4/2 | **無依據**（挑的） | ⚠️ 見下 |
| `MAX_FANOUT` | 16 | **無依據** | 🔴 **見 §4.3-bis：P8 對本鍵的評價是錯的** |
| `DEGRADED_CAP` | 4 | **無依據**，但方向正確（保守） | ✅ 保持 |

### 4.3-bis 🔴 訂正 P8 對 `MAX_FANOUT` 的評價（「低風險，因 cap 恆更緊」＝**實測為假**）

P8 的理由是「`cap` 恆比 `MAX_FANOUT` 更緊，所以這個鍵幾乎不起作用」。**本包實測推翻它。**

`free` 帶的 `cap` 是 **`None`（不設限）**——這時 `MAX_FANOUT` 是**唯一**的約束：

```
axes = (session 0% 剩 10 分, seven_day 30% 剩 5000 分)   ← 兩軸皆 free ⇒ cap=None
MAX_FANOUT= 4 ⇒ cap=None rec=4      MAX_FANOUT=12 ⇒ cap=None rec=12
MAX_FANOUT= 8 ⇒ cap=None rec=8      MAX_FANOUT=16 ⇒ cap=None rec=16
MAX_FANOUT=32 ⇒ cap=None rec=16     ← 上方飽和：rec_max = cap_notice × pace_near = 8×2 = 16
```
（載具＝`.venv/bin/python` 直呼 `quota_policy.decide()`，本回合 rc=0。）

⇒ **精確陳述**：`free` 帶時 `rec = min(cap_notice × pace_near, max_fanout) = min(16, max_fanout)`。
本鍵在 **≤16 的任何值上都是實際 binding 的**；只有 >16 才失效（被 8×2 飽和）。
**它不是一個沒作用的旋鈕，它是「水位還很寬鬆時到底一次派幾個」的唯一控制點。**
- **建議值：維持 16，但理由要改。** 不是「反正 cap 更緊」，而是：本鍵**只在最寬鬆的情境生效**，
  而那正是最容易一口氣派太多、把水位從 free 直接推進 notice 的時候。
- 🔴 **附一條沒人在守的性質**：`MAX_FANOUT > cap_notice × pace_near` 時本鍵**靜默失效**
  （設 32 與設 16 完全同義）。建議在 `policy_monotonicity_problems()` 旁加一句 warn
  ——「你設的值超過可達上界 N，實際不會生效」。**持有面＝`tools/lib/quota_policy.py`（P2）。**

🔴 **`FAR_HORIZON_MINUTES=360` 的評價，因 §1.6 的量測而反轉——它其實是對的，而且現在有依據了。**
本輪實測全部 15 個 episode 落在 3.4~286.9 分，**全部 ≤ 360** ⇒ 5 小時級的軸
（`session`／`five_hour`）**結構上永遠到不了 `far` 檔**，只會落在 near 或 mid；
而 C2 實測 `weekly_all`／`seven_day` 是 5,357 分 ⇒ 穩穩落在 `far`。
- ⇒ **`far_horizon=360` 的真正語意是「把 5 小時級的軸與週級的軸分開」**，而 286.9（觀測 max）
  與 5,357（週軸實測）之間有近 19 倍的間距 ⇒ 這個界**極度穩健**，落在哪裡都對。
- **實跑佐證**（`horizon_band()` 直接餵值，本回合）：`10→near`／`100→mid`／**`300→mid`**／
  **`5357→far`** ⇒ 觀測 max（286.9）確實落在 `mid`，週軸確實落在 `far`，上述推論是量出來的。
- **建議：保持 360，但把上面這句話寫進 `quota_policy.py` 當作它的立案理由**——今天該值
  只被「必須小於 `far_horizon`」這種形式判準守著，**零語意依據**，於是下一個人看到
  「無依據」就會去動它，而動它會讓 5 小時軸開始被誤判成 far（＝在還有 4 小時時就減速）。
- 🔴 **附帶的方向鎖**：若哪天觀測 max 逼近 360（今天 286.9，餘裕 73 分），該界就必須上調。
  建議與 §1.6 結論 1 的棘輪合成同一支：**觀測 max 上升就出聲**。

### 4.4 🔴 順手抓到的一筆小型「兩個家」：`AUTOSDD_QUOTA_FANOUT_CAP` 的歸類自相矛盾

本包在複核自己引用的鍵數時發現（**這一筆不是任務書要求查的，是取證紀律逼出來的**）：

```
ENV_SPEC 結構分類：政策鍵 14（含 AUTOSDD_QUOTA_FANOUT_CAP，attr=fanout_cap_override）
                   逃生口 3（GUARD_OFF／SENTINEL_OFF／CONTEXT_GUARD_OFF）
--print-env-example 的渲染分區：逃生口那一區印了 4 個（把 FANOUT_CAP 也算進去）
```

⇒ **同一個鍵，結構上是「有 attr 的政策參數」，渲染上被歸進「逃生口」。**
兩者都不算錯（它確實是個覆寫旋鈕），但**這正是本 repo 反覆判過的形態**：
同一份分類住兩個家、只有一個家會被改。今天的實害很小（純顯示），但它會讓任何
「數一數有幾個政策鍵」的下游（含本 ADR 的第一版草稿，**當場就數錯了**）得到不一致的答案。

- 建議：渲染分區改為由 `spec.attr is None` 導出，而不是另寫一份分組。
  **持有面＝`tools/lib/quota_policy.py`（P2），1 處。** 併入 X-5 一起做。
- 🔴 這一筆的價值不在它本身，在它**證明了本檔的取證紀律真的會抓到東西**：
  我第一版憑閱讀寫下「14 ＋ 4」，程式一問就發現分母的定義有兩套。

**對「調到最佳值」的總體建議**：`CAP_*`（8/4/2）今天沒有任何實測依據，而它們是**最該量的**
——因為它們直接決定「一次派幾個 agent」，而那是撞線與否的主因。建議做法同 §3.4(b)：
先加影子紀錄（`(pct, horizon, rec, 該輪是否撞線)`），累積數輪語料後再調。
**在有語料之前，任何調整都只是把一組挑的數字換成另一組挑的數字。**

---

## 5. 跨包需求（本包唯讀，以下皆需別的持有面執行）

| # | 對象包 | 需求 | 優先 |
|---|---|---|---|
| X-1 | **P2**（`tools/**`） | 修 `reset_window_distribution.py` rc=1（§1.5，建議案二＋probe smoke 測試） | **P0**——它擋住 R-4／R-5／§4.3 三項 |
| X-2 | **P2** | 6d 載具級 e2e（§3.5，opt-in、含 5 條斷言與洩漏偵測） | **P1** |
| X-3 | **P2** | `caffeinate` 有界斷言 ＋ tick 遲到量（§3.6 形狀 A/B） | P1（A 需排在 X-1 後） |
| X-4 | **P2** | `quota_policy.py` 加速前提具名化 ＋ 影子語料紀錄（§3.4a／b） | P2 |
| X-8 | **P2** | `describe()` 印出「本可派 N、被 <軸> 夾到 M」（§3.4a-2）——今天「加速到不了」在畫面上不可見 | **P1**（純輸出，零風險） |
| X-5 | **P2** | 根層 `--print-env-example` ①優先序句補射程限定詞（§4.2）②逃生口分區改由 `attr is None` 導出（§4.4） | P3（2 處） |
| ~~X-6~~ | ~~收尾窗口／掌舵者~~ | ~~產生根 `.env` 並驗證生效~~ **⇒ R85／P10 已完成，見 §4.1-bis** | **已關閉** |
| X-7 | 收尾窗口 | §1.5 缺陷入 `docs/06_quality/AutoSDD_Defect_Log.md` 並指派正式 DEF 編號（**P10 另有 R-9／R-10／R-11 三筆待編號**） | P1 |
| X-9 | **P2** | `describe()` 的反事實 rec（§3.4a-2 訂正版：判 `rec`，**不是**判 `cap`——判 cap 在 free 帶恆不觸發） | **P1** |
| X-10 | **P2** | 節流訊息加一句「本視窗 N 次中有 M 次來自其他 session」（R-11／§2.5） | **P1**（純輸出，零風險） |
| X-11 | **P2** | `_mult` 上方立明文前提：**本乘數只對區塊錨定的訂閱桶成立**；token-bucket 型的軸必須 `pace=1.0`（§3.4a，官方 token bucket 逐字） | P2 |
| X-12 | **P2** | `MAX_FANOUT > cap_notice × pace_near` 時出 warn（設 32＝設 16，今天靜默失效；§4.3-bis） | P3 |
| X-13 | 收尾窗口 | 把 §3.4(a-3) 的**政策 P-1**（加速的射程）寫進 `quota_policy.py` 檔頭——它今天只活在程式的形狀裡 | P2 |

🔴 **鐵律七提醒**：§3.4(a) 那一項的常數（`quota_policy.py`）、史料（逐字稿 probe）、
消費端（`--pace`）**不在同一持有面** ⇒ **不得派給並行包**，須由收尾單人窗口做。

---

## 6. 誠實劃界 — 本包沒能做到的

1. **R-7 只做到讀碼複驗，未動態注入**（§3.3 末段已寫明驗收該長什麼樣）。
2. **未跑任何測試套件**（本包唯讀且不佔用工作樹；`tools/tests/` 全套未執行）。
3. **Windows 側全部是靜態推論**：§3.5 斷言鏈第 4 條、`schtasks` 相關結論皆未在真機驗證。
4. **§1.6 那組數字是以「記憶體內注入」取得的**（`guard._RESET_RE = quota_limits._RESET_RE`），
   **不是**乾淨執行 `python tools/probe/reset_window_distribution.py` 的產物——後者今天 rc=1。
   數值本身可信（judgment 邏輯一行都沒被改），但**在 X-1 修好之前它不可被第三人複跑**。
   ⇒ X-1 修好後應由收尾窗口**重跑一次乾淨的**，以該次輸出為準。
5. **未驗證 6d 的「同 session」語意**：C9 證明哨兵已武裝，但「reset 後真的以
   `claude -r <sid>` 回到同一個 session 並續跑」本包**未端到端跑過**（那需要真的撞線）。
6. ~~**`.env` 未建立、未測試**~~ ⇒ **R85／P10 已補**（§4.1-bis）。
7. ~~🔴 **訴求 6z 未完成**~~ ⇒ **R85／P10 已補**（§2、§3.7）。
   §1.4 的三點現在**可以**與外部對照了，對照結果見 §3.7(乙)：A1／A2 成立但**不是同題較量**，
   A3／A4 只能說「本輪未檢索到對照」，A5 **與前沿平手而非領先**。
   ⇒ 措辭仍**不得**升級成「業界最佳」，理由由「沒查」變成「查了，而它們不是同一題」。

---

## 6-bis. 誠實劃界 — R85／P10 沒能做到的

1. 🔴 **§2 的證據強度不均勻，而這是本節最重要的一句。** 只有 **3 筆**是【已讀原文】
   （官方 rate-limits／usage-cost-api／compaction 三頁）。其餘**全部**是【僅搜尋摘要】
   ——URL 為真、內文未讀。**HiveMind 的五原語、Temporal 能跑數月、Claude Code 的五段壓縮
   管線、兩個 GitHub issue 的狀態，本包一個字的原文都沒讀過。**
   ⇒ 下一輪若要引用這些細節，**必須先自己去讀原文**；本檔的標記就是為了讓那件事不會被跳過。
2. **兩個 GitHub issue（33820／55333）的狀態完全未知**（open？closed？官方有無回覆？）。
   ⇒ 「官方正在考慮把 header 轉發給 hook」這種話**本檔沒有講，也不得從本檔推導**。
3. **`anthropic-ratelimit-unified-5h-*` 只出現在 issue 標題裡**，我沒有在任何官方文件見到它，
   也沒有實際觀測到這個 header。**不得當成已存在的通道。**
4. **【查無】三格是「本輪沒檢索到」，不是「世界上沒有」**：① Claude Code 的 OTel token 指標；
   ② 把用量% 接到**模型選型**的具名實作；③ 壓縮保真度的量化評估。
5. **R-9／R-10／R-11 三筆新缺口只做了「登記」，一筆都沒有修，也沒有做假紅普查。**
   R-10（雙哨兵競態）**連現況都沒查**——本檔只說「未驗證」，沒有說「有病」。
6. **§4 的逐鍵複審沒有新增任何實測語料。** `CAP_*`（8/4/2）與 `PACE_*`（2.0/0.5）今天仍然
   **零實測依據**；本包**刻意不動它們**——§3.4(b) 的判決（「沒有語料之前，任何調整只是把一組
   挑的數字換成另一組」）本包完全同意，並據此**拒絕**了「順手調成看起來更合理的值」。
7. **本包未跑任何測試套件**（`tools/tests/` 全套未執行）。§3.4(a-3)／§4.3-bis 的掃描是
   **直呼純函式**，不是跑閘門。
8. **Windows 側零驗證**：本輪全程在 macOS（Darwin 25.5.0）。§2.5 的派發帳觀測、
   §4.1-bis 的三快照，皆**未在 Windows 真機重跑**。
9. 🔴 **§2.5 的「其他 3 筆來自並行包」是推論，不是直接觀測**：我看到的是 4 個目錄項
   而本包只送出 1 次扇出，**目錄項本身不帶 session id** ⇒ 我無法證明那 3 筆是誰的，
   只能證明**不是我的**。R-11 的修法若要落地，得先讓帳本記得下「誰」——**那本身就是一項設計決定**，
   而且它與「`.env` 是放機密的地方、不得把身分資訊亂寫進暫存」有張力。**本檔不預判該怎麼做。**
