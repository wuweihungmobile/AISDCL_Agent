# SessionSwitch 成本模型設計（R216：快取不過期優先、算帳才換 session）

> 角色：Architect（R216 Architect＋SA 合一棒，2026-11-18）。驗收契約＝`docs/03_testing/contracts/TCS-SessionSwitch-CostModel-20261118.md`（下稱 TCS）。
> 上游需求＝`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md`（下稱 PRD；v2.1.17 起凍結，本設計對它的修憲草案見 §8，PRD 本身本棒唯讀）。
> 既有機制的權威設計＝`docs/04_planning/ADR/ADR-XPLAT-004-token-endurance-protocol.md` §2.13／§2.14／§2.17／§2.18（下稱 ADR）。本設計落地時由收尾窗口在 ADR 追加 §2.19 指向本檔（§12 連動面），本棒不改 ADR。
> 數字一律是 2026-11-18 當回合實跑的量測值（指令見 §7），不是常數；引用時重跑。

---

## 0. 結論先講（給掌舵者的一頁版）

1. **目標換了**：首要指標從「上下文多大」改成「快取有沒有過期」。14 天母體裡，上下文大小本身不是浪費的主因；**快取過期後整份重寫**才是：子代理 189 件／8,046 萬 token、主控 36 件／1,101 萬 token（`waste_census --since-days 14`）。
2. **新發現（本棒逐字稿實測）**：主控閒置約 55 分鐘時，harness 會**自動壓縮**大上下文——14 天 17 次自動壓縮中 **9 次**發生在閒置 54.6～56.5 分之後（壓縮前 25.6 萬～69.7 萬 token、壓縮後只剩 1.2 萬～2.2 萬）。也就是說「人離開一小時」的代價不只是重寫，**而是上下文被砍到剩 2%**。這正是掌舵者說的「自我閹割」，而且不是我們的 R1 造成的，是閒置造成的。保溫（每 45 分鐘輕觸一次）同時擋掉重寫與這種壓縮。
3. **補兩個保溫洞**：(a) 主控無背景工作、人離開 ⇒ 掛 `sessionctl keepwarm`，每 45 分鐘叫醒一次只讀快取（約 0.2×上下文的讀價），以 ski-rental 上限（約 9～10 次、7 小時左右）收手；重放：可保溫的 22 件閒置裡 20 件不再過期，成本省 52%。(b) 子代理跑超過 5 分鐘的指令 ⇒ 改「背景跑＋每 4 分鐘回來看一次」（`sessionctl runlong`／`waitfor`），重放省 85%（77 件、3,126 萬 token 重寫）。
4. **換 session 改成算帳**：上下文大小只剩兩條線——**邊界軟線**（只在沒有在飛代理、要結束回合時才問；由成本公式推出，出廠約 53 萬，掌舵者可用 `sessionctl hold` 宣告「這個任務需要上下文」暫緩）與**硬線**（autocompact 之前的最後防線，出廠 85 萬）。25 萬固定換手退役。
5. **誠實的反面**：只看 token，越早換越省（重放：在 25 萬換一次仍淨省 618 萬單位）。把軟線拉到 53 萬，靠的是「上下文本身有價值」這個治理係數 `q`（出廠 1＝上下文值一次接手成本）。`q` 與軟線出廠值是需要掌舵者確認的決定（§11 D-1）。🔴 **已裁決（2026-11-18）：不設軟線、只留硬線 85 萬，主軸＝快取不過期；hold 不實作。見 §11 開頭。**
6. `sessionctl watch` 在 prepare 帶一掛就 `rc=5` 的缺陷定案為**同 reset 窗同一帶只觸發一次的閂鎖**（不加 `--ack-quota`），§4.3。

---

## 1. 問題與證據

### 1.1 掌舵者原話（2026-11-18）

「請檢討context 25萬就切換Session的合理性, 是否應該專注在不要讓Cache過期(目標在此)! Context的容量本來就100M, 本來有些任務就需要Conext的內文, 現在變成25萬就切換, 是否變成自我閹割功能, 本末倒置!」；互動選項選定「改成算帳才換」。

### 1.2 現況機制（換 session 相關，2026-11-18 現查）

| 機制 | 判準座標 | 觸發 | 出廠值（`python tools/lib/quota_policy.py --print-env-example`） |
|---|---|---|---|
| R1 出聲＋產交接包 | `tools/lib/sessionctl/handoff.py::advise_once` → `switch.fresh_reasons` | 主控上下文 ≥ R1 | `AUTOSDD_SWITCH_R1_CTX_TOKENS=250000` |
| R2／R3 續跑選路 | `switch.fresh_reasons`（planner 無人續跑） | 壓縮 ≥2 次／上次續跑寫入 ≥ R3 | `R2=2`、`R3=100000` |
| 封存閘（Stop） | `seal.stop_verdict` | 無在飛代理 ∧ ctx ≥ R1 ∧ 未封存 | 同 R1 |
| 收斂閘（PreToolUse 派工擋） | `converge.converge_verdict` | 已出聲 ∧ ctx ≥ HARD | `AUTOSDD_SWITCH_HARD_CTX_TOKENS=290000` |
| 冷續棒閘 | `sessionctl_guard.py` SendMessage 分支＋`cachestate.py` | 目標代理快取冷 ∧ ctx ≥ | `AUTOSDD_RESUME_AGENT_TOKENS=150000` |
| 監督 watch | `watch.py` | 交卷／停滯／逾時／預算／額度／保溫（啟動後 50 分） | `WATCH_AGENT_CTX=700000` |
| 冷窗轉送 | `forward.py` | 已封存 ∧ 快取冷 | — |
| park | `park.py`／`park_cli.py` | 短窗原始讀數 ≥ prepare 而無續航憑證 | — |

### 1.3 14 天量測（`python tools/probe/waste_census.py --since-days 14`，2026-11-18 本棒實跑）

- 母體：主控逐字稿 40 支／子代理 260 支；主控 4,518 回合、子代理 17,416 回合。
- 快取重寫：**主控 36 件／11,010,245 token（主控加權 8.3%）**，36 件全是 1h 層；**子代理 189 件／80,456,572 token（子代理加權 12.0%）**，全是 5m 層。
- 壽命邊界：主控間隔 ≤60 分 4,441 回合只失效 1（0.02%）、>60 分 33 件失效 15（加上 55～65 分桶的 50%）；子代理間隔 ≤5 分 16,980 回合失效 4、>5 分 188 件失效 168。⇒ **TTL 是確定性的邊界：在邊界內回來幾乎必中，越界幾乎必失效。** 保溫的物理前提成立。
- 浪費排序（占全軸加權）：子代理「交卷後被續棒且已冷」5.4%（107 件）＞ 子代理「執行中長等待 >5 分」3.7%（82 件）＞ 主控通知喚醒首回合讀取 3.4%（下界、多屬必要）＞ **主控閒置過期重寫 2.0%（36 件）** ＞ … ＞ **R1 出聲後仍留在同 session 多付的讀取費：8 支合計約 193 萬單位（0.2%）**。
- ⇒ 25 萬換手想省的東西（大上下文的讀取溢價）在帳上只占 0.2%；真正大的是快取過期。這支持掌舵者的判斷「目標在不要讓 cache 過期」。

### 1.4 三個本棒新量到的事實

1. **閒置自動壓縮**（`r216\compact_idle.py`，見 §7）：17 次 auto 壓縮中，8 次是正常流程內（閒置 2.0～3.0 分、壓縮前 881,938～889,737 token＝autocompact 點）；**9 次在閒置 54.6～56.5 分之後**（壓縮前 255,860～696,607 token，壓縮後 11,727～21,724）。機制未查到官方文件（§11 Q-1），但時間點穩定落在 1h TTL 前約 5 分鐘。設計含意：保溫截止必須早於 54 分 ⇒ 取 **45 分**。
2. **接手成本 F**（`r216\replay216.py` §F）：23 支以交接包／handoff 開場的主控 session，前 15 回合加權單位中位 **480,734**（p25 406,110／p75 508,253），第 15 回合上下文中位 **B=147,780**。F 含部分真實工作，是上界（偏向不換）。
3. **喚醒實測**（PRD §11.3 的 `autosdd_resume_cost.jsonl`，`~/.autosdd/traces/`）：5 筆 measured 的續跑首回合 cache_creation＝86,838／863,852／13,713／773,611／138,811，cache_read 分別 16,875／32,045／143,329／0／32,666 ⇒ 過期後 `SESSION_RESUME` 幾乎整份重寫（4/5 筆寫入占比 ≥81%），與 PRD §4.5.4 的成本盲點描述一致；唯一便宜的是接力窗 relay_seq=1（快取仍熱）。

---

## 2. 目標與指標

| 指標 | 定義（量測器＝`waste_census`，WP-G 新增欄） | 基線（14 天） | 目標 |
|---|---|---|---|
| M-K1 | 主控「可保溫」閒置後重寫（起因 human／task_notification／peer_handback／other_user，間隔 ≥55 分） | 21 件／7,362,729 token | ≤2 件 |
| M-K2 | 主控閒置自動壓縮（auto 壓縮前閒置 50～60 分） | 9 次 | 0 |
| M-K3 | 子代理執行中長等待 >5 分後重寫 | 77 件／31,263,469 token | ≤ 基線 15% |
| M-K4 | 子代理冷續棒重寫（交卷後 >5 分被續） | 146 件／70,155,830 token | 不升（既有閘已擋） |
| M-K5 | 保溫自身成本（keepwarm＋waitfor 回合的加權單位） | 0 | ≤ 所避免重寫加權的 0.5 倍（ski-rental 保證 ≤1 倍） |
| M-K6 | 換手次數與 F 實付 | 現行 R1 | 只在 §5 決策表允許的邊界發生 |

成功判準＝M-K1、M-K2、M-K3 達標且 M-K5 不超標（保溫成本入帳，不准用「快取命中」掩蓋保溫花掉的錢）。

---

## 3. 成本模型

### 3.1 單位

加權單位與 `tools/lib/wastecensus/reader.py` 同一組：input 1.0／output 5.0／cache_read 0.1／cache_write(5m) 1.25／cache_write(1h) 2.0。記號：`W_CR=0.1`、`W_CC1=2.0`（主控）、`W_CC5=1.25`（子代理）。一個上下文 `c` token 的 session：讀一次＝`0.1c`；過期後重寫＝`W_CC×c`。

### 3.2 參數表（全部有量測來源；出廠值寫進 `ENV_SPEC`，`waste_census --calibrate-switch` 重算建議值）

| 參數 | 意義 | 出廠 | 來源 |
|---|---|---|---|
| `F` | 新 session 接手成本（單位） | 480,000 | §1.4-2：n=23 中位 480,734 |
| `B` | 接手後穩定上下文（token） | 150,000 | §1.4-2：中位 147,780 |
| `F_a` | 新子代理接手成本 | 不設參數（沿用既有 150k 閘，§4.5） | 重放 n=228 中位 297,953 |
| `q` | 上下文價值係數：失去上下文的品質損失＝`q×F` | 1.0 | 治理決定（§11 D-1） |
| `N_lo` | 跨過軟線後「保守估計」的剩餘回合數（低分位） | 25 | §7 P4b：11-14 前 9 支跨 45 萬者剩餘回合 19～230，取低分位避免替快收尾的 session 付 F |
| `P_fix` | 每次保溫的固定單位 | 4,500 | 叫醒＋重掛兩回合的輸出約 300 token×5＋新增上下文約 1,500 token×2；對照實測「純確認型通知鏈」48 鏈平均 57,913 單位（`waste_census` §4，含讀取） |
| `T_kw` | 主控保溫截止（距主控最後一筆帶 usage 的 assistant 記錄） | 45 分 | §1.4-1：閒置自動壓縮最早 54.6 分；留 9 分給請求延遲與巡檢週期 |
| `T_sub` | 子代理分段等待上限 | 240 秒 | 5m TTL 300 秒 − 60 秒；實測 ≤5 分命中率 99.98% |
| `HARD` | autocompact 前的最後防線 | 850,000 | §1.4-1：流程內 autocompact 最小 881,938；留約 3 萬（數回合） |

### 3.3 核心公式

**(F1) 保溫 vs 放冷（主控閒置，ski-rental）**
每次保溫成本 `p(c) = 2·W_CR·c + P_fix`（叫醒回合＋重掛的 tool_result 回合各讀一次）；放冷的代價 `R(c) = W_CC1·c`（回來時整份重寫，且可能被閒置壓縮砍掉上下文）。
最多保溫次數 `n*(c) = floor( R(c) / p(c) ) = floor( 2c / (0.2c + 4500) )`（c=40 萬 ⇒ 9；c=15 萬 ⇒ 8）。
確定性 ski-rental：先保溫至多 `n*` 次再放手，任何返回時間下總成本 ≤ 事後最優的 2 倍；實測分布（22 件中 20 件 ≤7.5 小時回來）下遠優於 2 倍。

**(F2) 子代理長等待（分段等待）**
每段成本 `p_s(c) = W_CR·c + 1500`；放冷代價 `W_CC5·c`；`n_s* = floor(1.25c / (0.1c+1500)) ≈ 12`（約 48 分）。超過 `n_s*` 段仍未完成 ⇒ 不再分段、一次等到底（照付重寫）。

**(F3) 換窗（邊界軟線）**
留在本 session 的讀取溢價（對比換到新 session）每回合 ≈ `W_CR·(c − B)`；保守剩餘 `N_lo` 回合；換窗代價 `F·(1+q)`。
換窗 ⇔ `N_lo · W_CR · (c − B) > F·(1+q)` ⇔ `c > T_soft ≡ B + F(1+q) / (W_CR · N_lo)`。
出廠：`150,000 + 480,000×2 / (0.1×25) = 534,000`。`AUTOSDD_SWITCH_R1_CTX_TOKENS` 若有設，作為 `T_soft` 的**只准下修**上限覆寫（相容既有鍵語意）。

**(F4) 冷回來／額度續跑選路（取代 PRD §4.5.4 AUTO「依對話規模」）**
同 session 續跑（`SESSION_RESUME`）成本 `W_CC1·c`（過期必重寫；§1.4-3 實證）；`FRESH_SESSION_WITH_STATE` 成本 `F·(1+q)`。
FRESH ⇔ `W_CC1·c > F·(1+q)` ⇔ `c > F(1+q)/2 = 480,000`（出廠）。快取仍熱（距最後寫入 < TTL−30 秒）⇒ 一律續跑（讀價 `0.1c` 必小於 F）。

### 3.4 本模型不算的東西（劃界）

- 輸出品質：只能用 `q` 這個治理係數代表，模型不量它。
- 週額度與短窗額度的「使用期限」：短窗殘量在 reset 時歸零，理論上 reset 前保溫幾乎免費；本版不利用此點（§10 X-7）。
- 子代理之間的上下文重疊、主控派工策略本身。

---

## 4. 機制設計

### 4.1 主控保溫 `sessionctl keepwarm`（新；補「無背景工作、人離開」的洞）

- **事件源**：`python tools/sessionctl.py keepwarm --sid <sid>`，主控以 `run_in_background`、輸出導檔掛上（鐵律六的合法事件源：阻塞到截止才結束，結束即叫醒主控）。
- **截止錨點**：主控逐字稿**最後一筆帶 usage 的 assistant 記錄**時間 ＋ `T_kw`（45 分）；每 60 秒重讀尾端，有新記錄就往後延（人回來工作時不會提早叫醒）。不錨 `started_at`。
- **保溫帳**：`trace_dir()/keepwarm/<sid>.json` 記 `pings`、`n_star`、`ctx`；**本 session 出現真人提示（`transcript_activity.is_forwardable_prompt` 為真者）即歸零**。
- **結束輸出**：末行 `KEEPWARM_VERDICT=ping k=<k> n=<n*> rc=6`（沿用 watch 的 keepwarm rc 6）或 `KEEPWARM_VERDICT=cap k=<n*> rc=7`（已達上限）。處置表（印在判決行前）：`ping`＝什麼都不判、重掛 keepwarm、本回合輸出 ≤50 token；`cap`＝不重掛；若 `c ≥ T_soft` 先封存（§4.4），否則直接結束回合（讓它冷，ski-rental 已到損益點）。
- **不掛的情形**：無人窗口（`AUTOSDD_UNATTENDED`；print 模式背景上限會殺掉它）、模式非 auto、已交棒（spawned／acked）、park 標記 armed 且仍有效（park 接手）、`c < 30,000`（重寫便宜，不值得叫醒）。
- **與既有守衛的互動**（SD 必須同包處理，不留後遺症）：
  - **保溫閘（Stop，新）**：無任何 running 背景任務 ∧ 上述「不掛的情形」皆不成立 ∧ 保溫帳 `pings < n*` ⇒ 推回一次：「掛 keepwarm」。與封存閘、park 閘的合成次序見 §5。
  - **冷叫醒閘**（`converge._finalized_wake`）：目前 `.sealed` 即要求 TaskStop 所有背景任務。改為：**已交棒**（spawn／ack）⇒ 照舊全停；**只封存、在等掌舵者** ⇒ `sessionctl.py keepwarm` shell 豁免（它就是要叫醒這個 session 保溫，醒來讀的是熱快取）。
  - 半路停工判準（`midwork.py`）：keepwarm 在跑＝有事件源，不判半路停工（現行判準已滿足，只需回歸測試）。
  - 轉送（`forward.py`）：保溫中快取恆熱 ⇒ 條件 5 放行（現行行為正確）。
  - watch 與 keepwarm 不並存：有在飛代理時用 watch（其保溫分支見 §4.2）；全部交卷後 watch 判 all_done，主控收卷後若要閒置改掛 keepwarm。

### 4.2 watch 的保溫錨點

`watch.decide` 的 keepwarm 條件由「watch 啟動後 50 分」改為「主控最後一筆帶 usage 的 assistant 記錄 ＋ `T_kw`」（與 §4.1 共用同一個函式，住 `keepwarm.py`）。WHY：主控在 watch 執行期間被其他通知叫醒過，舊錨點會提早或延後叫醒；50 分也晚於閒置壓縮的安全邊際。

### 4.3 watch 額度事件閂鎖（真機缺陷定案）

- **缺陷**：短窗原始讀數在 prepare 帶時，`quota_hit_now()` 每次輪詢都成立 ⇒ `sessionctl watch` 一掛即 `WATCH_VERDICT=quota rc=5`，處置表要求「代理快完成 ⇒ 重掛」但重掛必再觸發，prepare 帶內監督形同失效（主控 2026-11-18 21:26 watch1.log 與重掛 bd116c583 兩次實證）。
- **定案＝閂鎖**：quota 事件以 `(sid, reset 時刻（分鐘）, 帶級)` 為鍵寫 `trace_dir()/watch/<sid>.quota.json`；同鍵已觸發 ⇒ 該次輪詢視為 `quota_hit=False`；**帶升級**（prepare→halt）或 **reset 時刻改變**（新窗）⇒ 重新觸發。閂鎖讀不到或壞檔 ⇒ 照觸發並在 stderr 出聲（PRD 原則 5：失效往保守＝提醒主控收斂）；寫不進去 ⇒ 照觸發並出聲（寧可再吵一次，也不靜默吞掉額度事件）。
- 處置表 `quota` 列改為：「估剩餘：代理快完成 ⇒ 重掛 watch（同一 reset 窗同一帶不會再觸發）…」。
- **否決 `--ack-quota`**：(1) 要人每次重掛都記得帶旗標，忘了就回到缺陷；(2) 旗標帶上後連「帶升級到 halt」也一起被吞，逃生口變成盲區；(3) 閂鎖的作用域（一個 reset 窗）天然到期，旗標沒有到期。

### 4.4 換窗決策：軟線、hold、硬線

- **軟線 `T_soft`（F3）**：只在**邊界**評估——Stop 時無在飛代理（封存閘既有前提）。ctx ≥ `T_soft` ∧ 未交棒 ∧ 封存無效 ∧ **無有效 hold 戳記** ⇒ 封存閘推回（文案同現行，門檻字改 `T_soft`）。`handoff.advise_once` 出聲門檻同步改 `T_soft`。運行中（有在飛代理）不推回、不擋派工。
- **hold 戳記（新，仿 `quota_rush`）**：`python tools/sessionctl.py hold --hours <H> --why "<≥8 字>"`／`--off`／`--status`。語意＝「本任務依賴目前上下文」，期間軟線不推回、不出聲；**不影響硬線**；上限 12 小時、自帶到期、無人窗口無效、讀不到當無戳記。判準住 `tools/lib/sessionctl/hold.py`。
- **硬線 `HARD`（F 外的最後防線）**：出廠 850,000。語意由「出聲後再長大就擋派工」改為「autocompact 之前主動交棒」（PRD §4.3 line 1022 的替代路線）：ctx ≥ HARD ⇒ (a) PreToolUse 擋 Agent／Task／Workflow（現行收斂閘，**移除「須先出聲」前提**），(b) Stop 封存閘推回（hold 無效）。不變式：`T_soft < HARD < 觀測到的流程內 autocompact 點`（啟動自檢＋測試釘住）。
- **R2**（壓縮 ≥2 次 ⇒ 續跑走 FRESH）保留：它是品質訊號（多次壓縮後摘要疊摘要），與成本無關。
- **R3**（上次續跑寫入 ≥10 萬 ⇒ FRESH）**退役**：被 F4 取代（F4 直接用現在的 c 算續跑成本；R3 在 c=17 萬時判 FRESH，但按帳續跑 34 萬單位 < FRESH 96 萬單位，R3 是錯方向）。鍵保留讀取、出廠值移除、出聲「已退役，見 F4」（遷移見 §9）。

### 4.5 子代理

- **長等待（新，補 5m TTL 洞）**：
  - `python tools/sessionctl.py runlong --out <檔> -- <argv…>`：子代理以 `run_in_background` 執行；結束時原子寫 `<檔>.done`（內容＝rc 與結束時刻）。
  - `python tools/sessionctl.py waitfor --done <檔>.done --max-sec 240`：前景阻塞至多 `--max-sec` 秒（預設 240、**上限 255**；WHY 不是 270：waitfor 自己是前景呼叫，等 270 秒需要 timeout > 270000，會被下一條長前景閘自己擋住）；完成 rc 0 並印尾端 40 行，未完成 rc 3（`WAITFOR_VERDICT=pending`），參數錯 rc 2。子代理迴圈呼叫直到 rc 0 或達 `n_s*` 段（之後改一次前景等到底，照付重寫）。
  - **長前景閘（PreToolUse，新）**：呼叫帶 `agent_id`（子代理）∧ 工具＝PowerShell／Bash ∧ 非 `run_in_background` ∧ `timeout > 270000` ⇒ rc 2，訊息指路 runlong／waitfor。依據：工具預設 timeout 120 秒，要跑超過 5 分鐘**必須**顯式設大 timeout ⇒ 這個判準精確、零猜測。行內豁免 `# keepwarm-ok: <WHY>`（無人窗口無效，同其他守衛）。主控不判（1h TTL）。
  - 暴露證據（守衛面准入）：77 件真實逐字稿長等待重寫（非構造），`waste_census` §1 子代理前一工具 PowerShell 52 件。
- **冷續棒閘**：**不改**。重放：現行「冷 ∧ ctx≥150k 擋」淨省 44,939,955；成本式（ctx > F_a/1.25 = 238,363）淨省 45,873,225，差 2%、在量測雜訊內（Rule 2：不為 2% 換判準）。
- **WATCH_AGENT_CTX（70 萬）**：不改（它是預算超支、不是換窗）。

### 4.6 park 的選路（F4 套到自願停工）

park job（`park --fire`）目前一律開新 session 帶交接包。改為依 F4：`c ≤ F(1+q)/2` ⇒ `claude -r <sid>` 續跑（重寫比接手便宜、保留上下文）；否則照舊 FRESH。重放（P3，14 件額度續跑）：κ=2（即 q=1）時 4 件走 FRESH、淨省 2,949,659 單位；現行 R1 判法 7 件。優先序 P2（§9 階段 3）。

---

## 5. 決策表

| # | 時點 | 條件（前者優先） | 動作 | 判準住 |
|---|---|---|---|---|
| D1 | Stop、有在飛代理 | 已交棒且有背景任務 | 冷叫醒閘：TaskStop | `converge._finalized_wake` |
| D1b | 同上 | 無有效監督憑證 | 監督閘：掛 watch | `supervise.stop_verdict` |
| D2 | Stop、無在飛代理 | 已交棒且有背景任務 | 冷叫醒閘（keepwarm 也停） | `converge` |
| D3 | 同上 | ctx ≥ HARD ∧ 未有效封存 | 封存閘（hold 無效） | `seal.stop_verdict` |
| D4 | 同上 | ctx ≥ T_soft ∧ 無 hold ∧ 未有效封存 | 封存閘 | `seal.stop_verdict` |
| D5 | 同上 | 短窗原始讀數 ≥ prepare ∧ 無續航憑證 | park 閘（與 D3／D4 合併一則，先封存後 park） | `park.stop_verdict` |
| D6 | 同上 | 無任何背景任務 ∧ 可保溫（§4.1）∧ pings < n* | 保溫閘：掛 keepwarm（與 D3／D4 合併時次序：封存→keepwarm；封存後仍等掌舵者就保溫） | `keepwarm.stop_verdict`（新） |
| D7 | keepwarm 結束 | `ping` | 重掛、≤50 token | 處置表 |
| D8 | keepwarm 結束 | `cap` | 不重掛；ctx ≥ T_soft 先封存 | 處置表 |
| D9 | UserPromptSubmit | 已封存 ∧ 快取冷 ∧ `W_CC1·c > F(1+q)` | 轉送新 session | `forward._forward_verdict`（加 F4 條件） |
| D10 | 無人續跑選路 | 快取熱 ⇒ RESUME；R2 ⇒ FRESH；F4 ⇒ FRESH；否則 RESUME | — | `switch.fresh_reasons` |
| D11 | park 到點 | F4 | RESUME 或 FRESH | `park_cli`（階段 3） |
| D12 | PreToolUse 派工 | ctx ≥ HARD | 擋 Agent／Task／Workflow | `converge.converge_verdict` |
| D13 | PreToolUse 子代理長前景 | §4.5 | 擋、指路 runlong／waitfor | `longwait.pretool_verdict`（新） |
| D14 | watch 輪詢 | quota 命中 ∧ 閂鎖同鍵 | 不觸發 | `keepwarm.quota_latch`（新） |

所有新判準 fail-open 方向與既有 sessionctl 一致（量不到 ⇒ 不推回、不擋），唯一例外是 D14 閂鎖失效 ⇒ 觸發（§4.3）。

---

## 6. 與現有機制的關係與取捨

| 既有 | 處置 | WHY |
|---|---|---|
| R1＝25 萬 | 退為 `T_soft` 的只准下修覆寫鍵；出廠空值＝用 F3 推導值 534,000 | 固定 25 萬沒有成本依據；F3 讓門檻隨 F、B、q、N_lo 校準 |
| R2 | 保留 | 品質訊號 |
| R3 | 退役（F4 取代） | §4.4 反例 |
| HARD 29 萬 | 改 85 萬、移除「先出聲」前提 | 變成 autocompact 前防線；PRD §4.3 line 1022 |
| 封存閘 | 門檻 R1→T_soft／HARD；加 hold | 只在邊界問 |
| 轉送 | 加 F4 成本條件 | 冷回來未必該換 |
| 冷叫醒閘 | 對「只封存」豁免 keepwarm | 封存後等人＝最該保溫的時候 |
| watch | 保溫錨點、quota 閂鎖 | §4.2／§4.3 |
| park | 加 F4 選路（階段 3） | 小上下文續跑比接手便宜 |
| 冷續棒閘 150k | 不改 | 重放差 2% |
| 哨兵／planner 喚醒 | 只換 `fresh_reasons` 內部 | 介面不動 |

---

## 7. 重放驗證（真實逐字稿；零 token）

指令（2026-11-18 本棒實跑；腳本暫存於 session scratchpad `r216\`，WP-G 正式化為 `waste_census --replay-switch`）：

```
python tools/probe/waste_census.py --since-days 14
python <scratchpad>\r216\replay216.py 14                 # 保溫間隔 50 分
$env:R216_PING_MIN='45'; python <scratchpad>\r216\replay216.py 14
python <scratchpad>\r216\compact_idle.py                  # 壓縮前閒置
```

| 重放 | 新判準改變的決定 | 加權單位（14 天） |
|---|---|---|
| P1 主控保溫（45 分、動態 n*） | 22 件可保溫閒置中 20 件由「放冷重寫」改為「保溫命中」，86 次保溫 | 實際重寫基線 14,725,458 → 7,069,932（**省 7,655,526，52%**）；對照同模型「不保溫」17,466,078 省 60%。固定 cap 掃描：480 分 7,268,883、720 分 7,566,350 |
| P1 附：閒置壓縮 | 9 次閒置自動壓縮皆發生在閒置 54.6～56.5 分；45 分保溫截止在其前（是否全數可擋待真機 E2E-K3 驗證） | 不入 token 帳（品質面） |
| P3 額度續跑選路（F4） | 14 件中，q=1 判 FRESH 4 件（ctx>480,734）；q=0 判 7 件（同現行 R1） | q=1 淨省 2,949,659；q=0 淨省 3,645,641 |
| P4b 邊界軟線（11-14 前 13 支，未受 R1 截斷；單次換窗） | 25 萬：9 支換、q=1 淨 6,175,983；35 萬 16,219,418；45 萬 25,360,406；**50 萬 27,455,536**；60 萬 25,527,379；70 萬 17,749,558 | 單支：45 萬時 04b38d83 剩 19 回合 ⇒ 淨 −377,986（用 N_lo 低分位的理由） |
| S1 冷續棒 | 現行 150k 擋 141 件；成本式擋 127 件 | 44,939,955 vs 45,873,225（不改） |
| S2 子代理分段等待 | 77 件全部由重寫改為命中（0 件仍過期），145 段 | 39,079,336 → 6,017,201（**省 33,062,135，85%**）；等待中位 8.6 分、p90 16.9 分 |

誠實劃界：(1) P4b 是「每 session 只換一次」的下界模型；允許重複換窗時，只看 token 會偏好更低門檻——軟線拉高的理由是 `q`，不是 token。(2) 11-14 後的 session 已被 R1 截斷，P4 全期數字（25 萬淨 7,050,801）有倖存者偏差，故以 P4b 為準。(3) 保溫成本 `P_fix` 是推估，WP-G 上線後以 M-K5 實測回寫。

---

## 8. PRD v2.1 追溯與修憲草案（收尾窗口套用；本棒不改 PRD）

> 🔴 **2026-11-19 收尾窗口已套用於 PRD**（修訂表 v2.1.22 列、§16.6 列、四處就地註記）。**實際落地全文以 PRD 為準**：依 §11 掌舵者裁決，PRD 版本不含軟線 `T_soft`／hold，`waitfor` 上限寫 255；下列 8.2～8.4 草案保留作史料。

### 8.1 受影響條文座標（行號＝2026-11-18 現查）

| PRD 座標 | 原文要點 | 與本設計的關係 |
|---|---|---|
| §1.2 原則 2（line 130～132） | 零 Token 遙測、嚴禁用 Prompt 探測額度 | 保溫回合會花 token，但**不是遙測、不探額度**；成本入 M-K5 帳。所有判準只讀逐字稿與本機痕跡（零 token）。不衝突，需就地註記劃界 |
| §1.2 原則 5（line 137～138） | 失效即保守 | D14 閂鎖失效 ⇒ 觸發；保溫量不到 ⇒ 不叫醒（少花）。sessionctl 守衛的 fail-open 是既有劃界（不改） |
| §1.2 原則 6（line 139～140）、§2 `K_ctx`（line 162）、§2 關鍵釐清（line 169～171） | 額度≠上下文；`K_ctx` 是觸發**壓縮**的唯一依據 | 本設計新增第三軸「快取成本軸」（session 層、單位＝加權 token），**不觸發壓縮**、只觸發換窗與保溫；上下文 token 是成本公式的輸入不是百分比門檻。PRD 原文沒有「上下文到 X 就換 session」——R1／HARD 在 PRD 無條文依據，這是本次修憲要補的 |
| §4.3（line 998～1022） | 壓縮 84%／硬線 94%（autocompact 90）；line 1022「若外部觸發壓縮不可行，改為在 `K_ctx` 超標時主動結束該 Step 並以新 session 交棒」 | `HARD` 即 line 1022 的落地：在 autocompact 前交棒。84／94 兩條百分比（context 守衛）不動，HARD 以 token 表示、須小於 autocompact 點 |
| §4.5.4（line 1125～1144） | 成本盲點；三策略；AUTO＝對話 ≤60000 token ⇒ RESUME；U7d 高 ⇒ FRESH（C6：實作比位元組、weekly 規則未實作） | F4 把 AUTO 從「依對話規模」改為「依成本」：熱 ⇒ RESUME；冷 ⇒ `W_CC1·c` 對 `F(1+q)`。對應：60000 token 門檻 ≈ 本模型 q=−0.75 的特例（不採）；位元組上限（32MiB）保留為 R4 兜底；weekly→FRESH 仍不做（本設計不引入週軸判準，維持 C6 處置） |
| §4.5.7（line 1231～1300） | 主控閒置盲區（等待期間零工具呼叫） | keepwarm 補同一盲區的**快取面**（§4.5.7 補的是水位提醒面）；兩者互不取代 |
| §9 指標 `autoclaude_resume_cost_pp`（line 2325）、§11.3（line 2371～2382） | 記錄喚醒實際額度成本；v2.1.16 `resume_cost.py` 落 jsonl | F4 的 F 與 RESUME 成本以 `autosdd_resume_cost.jsonl` 校準（§1.4-3），`--calibrate-switch` 讀它 |
| §15.6（line 2593）、§15.7 第 5 點（line 2611～2612） | 喚醒比工作貴就切 FRESH；以實測喚醒成本推 RESUME 門檻 | F4 正是 §15.7-5 的成本化版本 |
| §16.5（line 2761～2771）、§16.6（line 2773～2781）、修訂表（line 3～26） | 修憲程序 | 見 8.2～8.4 |

其他 PRD：`docs/01_requirements/` 內 grep「換 session／保溫／keepwarm／快取過期」只命中本 PRD 與設計系統打包檔中的商品字樣，無其他實質條文（SelfImproving_PRD 依主控摘要僅順帶一處，未構成需求）。

### 8.2 修訂表擬新增列（接在 line 26 之後；狀態格由收尾窗口依審查結果填）

```
| **v2.1.22（§16.5 (i)：換 session 改依快取成本；主控／子代理保溫）** | 2026-11-18 | **掌舵者 2026-11-18 直接立案（原文：「請檢討context 25萬就切換Session的合理性, 是否應該專注在不要讓Cache過期(目標在此)! Context的容量本來就100M, 本來有些任務就需要Conext的內文, 現在變成25萬就切換, 是否變成自我閹割功能, 本末倒置!」；互動選項選定「改成算帳才換」）；R216 四方（Architect／SA／SD／QA）〔審查紀錄座標待填〕** | 不改既有條文一字。新增「快取成本軸」（session 層、加權 token）：主控閒置保溫（`sessionctl keepwarm`，45 分截止、ski-rental 上限）、子代理長等待分段（`runlong`／`waitfor`）；換 session 由固定 25 萬改為邊界軟線 T_soft＝B＋F(1+q)/(0.1·N_lo) 與 autocompact 前硬線（§4.3 line 1022 路線）；§4.5.4 AUTO 判準讀作「依成本」（熱⇒RESUME；冷⇒W_CC1·c 對 F(1+q)）。設計＝`docs/02_architecture/SessionSwitch_CostModel_Design.md`；驗收＝`docs/03_testing/contracts/TCS-SessionSwitch-CostModel-20261118.md`；就地註記於 §1.2 原則 2、§4.3、§4.5.4、§11.3；結案格見 §16.6 |
```

### 8.3 §16.6 擬追加列（接在 line 2781 之後）

```
| 2026-11-18 | 換 session 改依快取成本、補主控與子代理保溫（掌舵者原文：「請檢討context 25萬就切換Session的合理性, 是否應該專注在不要讓Cache過期(目標在此)! … 本末倒置!」；互動選項「改成算帳才換」；對應 §4.5.4 成本盲點、§4.3 line 1022 交棒路線、§11.3 喚醒成本） | ⏸（落地且 TCS 全 AT＋E2E 通過後轉 ✅） | 依據＝設計 `docs/02_architecture/SessionSwitch_CostModel_Design.md`、TCS `docs/03_testing/contracts/TCS-SessionSwitch-CostModel-20261118.md`；量測＝`python tools/probe/waste_census.py --since-days 14` 的 M-K1～M-K6；再開症狀＝連續 14 天 M-K1（主控可保溫閒置後重寫）> 2 件，或 M-K2（閒置 50～60 分後的 auto 壓縮）≥ 1 次，或 M-K5 保溫成本 > 所避免重寫的 1 倍 |
```

### 8.4 就地註記全文（各接在指定行之後）

- §1.2 原則 2 之後（line 132 後）：`> 🔴 【v2.1.22 註記】快取保溫（主控 keepwarm、子代理 waitfor）的回合會消耗 token，但它不是遙測、也不探測額度；其成本另立「快取成本軸」入帳（waste_census M-K5）。本原則的「零 Token」範圍不變：所有保溫與換窗判準只讀本機逐字稿與痕跡。設計見修訂表 v2.1.22。`
- §4.3 line 1022 之後：`> 🔴 【v2.1.22 註記】本行「在 K_ctx 超標時主動結束該 Step 並以新 session 交棒」自 v2.1.22 起有落地：硬線 HARD（token 數，須小於流程內 autocompact 點），到線即封存交接包並擋展開型派工。CONTEXT_COMPACT_PERCENT 84／硬線 94 兩條百分比尺不變；換 session 不屬 K_ctx 的壓縮動作，屬快取成本軸（見 §4.5.4 同版註記）。`
- §4.5.4 C6 註記之後（line 1144 後）：`> 🔴 【v2.1.22 註記】AUTO 判準自本版讀作「依成本」：快取仍熱 ⇒ SESSION_RESUME；已冷 ⇒ 2×對話 token 與 F×(1+q) 比較（F＝新 session 接手成本、q＝上下文價值係數；出廠值與量測來源見設計文件 §3.2），前者大 ⇒ FRESH_SESSION_WITH_STATE。逐字稿位元組上限保留為兜底；週額度→FRESH 規則維持 C6 處置（未實作）。`
- §11.3 v2.1.16 落款之後（line 2382 後）：`> 🔴 【v2.1.22 註記】autosdd_resume_cost.jsonl 自本版起同時是 §4.5.4 成本判準 F 與 SESSION_RESUME 成本的校準來源（`waste_census --calibrate-switch`）。`

---

## 9. 遷移與相容

- **階段 1（WP-A、WP-C、WP-G）**：成本模型模組與參數、watch 閂鎖與錨點、量測與重放。行為改變只有 watch 不再重複 rc 5。
- **階段 2（WP-B、WP-D、WP-E）**：keepwarm＋保溫閘＋冷叫醒閘豁免；子代理 runlong／waitfor＋長前景閘；軟線／hold／硬線、R3 退役、轉送加 F4。
- **階段 3（WP-F）**：park 選路。
- 鍵：新增 `AUTOSDD_SWITCH_FRESH_COST_UNITS`(480000)、`AUTOSDD_SWITCH_FRESH_CTX_TOKENS`(150000)、`AUTOSDD_SWITCH_CONTEXT_VALUE_Q`(1.0)、`AUTOSDD_SWITCH_MIN_REMAINING_TURNS`(25)、`AUTOSDD_KEEPWARM_MINUTES`(45，只准下修，下限 15)、`AUTOSDD_KEEPWARM_MIN_CTX_TOKENS`(30000)。既有 `R1` 出廠改空（＝推導值），有設時只准下修推導值；`HARD` 出廠 290000→850000；`R3` 出廠移除、有設時出聲「已退役」不生效。`env.shared` 現無這些鍵（2026-11-18 grep 零命中），無遷移衝突。
- 回滾：`AUTOSDD_SESSION_SWITCH_MODE=notify／off` 照舊；keepwarm 另有 `AUTOSDD_KEEPWARM_OFF`（只關保溫閘與指令）。
- 相容：`fresh_reasons` 回傳格式不變（命中理由字串改為 F4 文字）；`handoff`／`seal` 檔案格式不變；痕跡新增事件 `keepwarm_verdict`、`keepwarm_stop_block`、`watch_quota_latched`、`longwait_block`。

---

## 10. 被否決方案與 WHY

| # | 方案 | 否決理由 |
|---|---|---|
| X-1 | 只把 R1 調高到 50 萬、其他不動 | 不碰真正的浪費（快取過期 2.0%＋5.4%＋3.7%）；閒置壓縮照樣砍上下文 |
| X-2 | 完全取消上下文觸發 | autocompact 在 88 萬一次把上下文砍到 1～2 萬，比交接包更失真；PRD §4.3 line 1022 也要求 |
| X-3 | 用 `/loop`／`ScheduleWakeup` 保溫 | 無憑證、單次上限 1 小時、靜默失效（根 CLAUDE.md 工具選型表）；PRD §15.5 紅線 3 |
| X-4 | 保溫無上限（一直叫醒到人回來） | 22 件中有 1 件 4,863 分後才回來；無上限＝最壞成本無界，ski-rental 給 2 倍保證 |
| X-5 | watch `--ack-quota` | §4.3 |
| X-6 | 子代理改用 1h TTL | 本機無可證實的設定面（§11 Q-2）；先做不依賴 harness 的分段等待，查證後若可行再評估 |
| X-7 | reset 前用即將歸零的短窗殘量保溫跨 reset | 撞 100% 後請求失敗、保溫鏈斷；且週額度不歸零。量不到真實收益，列 §11 |
| X-8 | 冷續棒閘改成本式 | 重放差 2%（§4.5） |
| X-9 | 純 token 最優的低門檻重複換窗 | 違背掌舵者「任務需要上下文」；以 q 明示代價而不隱藏 |

---

## 11. 未決問題

**🔴 掌舵者裁決（2026-11-18，sid 05d1b770 互動選項；同場再指令原文「專注在不要讓Cache過期!專注在不要讓Cache過期!專注在不要讓Cache過期!」）——以本段為準，優先於本文其他處**

- **D-1 ＝ ③ 不設軟線**：只留硬線 `HARD`＝850,000。⇒ §4.4 軟線 `T_soft`、§5 D4、§4.1 `cap` 處置裡的「c ≥ T_soft 先封存」、`handoff.advise_once` 改 `T_soft` 一律**不實作**；R1 的「建議換 session」出聲與封存閘門檻改為 HARD（不再在 25 萬推回）。F4（快取已冷時算續跑 vs 換新）照做——那是「快取已經冷了」之後的選路，不是主動換窗。
- **D-2 ＝ 不設上限**：因 D-1 取消軟線，hold 戳記沒有作用對象（hold 本來就不影響硬線）⇒ **hold 整個不實作**（Rule 2：不為沒有作用對象的開關寫碼）。若日後重新設軟線，hold 隨之再議、屆時不設上限。
- **實作優先序改為保溫先行**：WP-C（watch 閂鎖＋保溫錨點，建 keepwarm.py）→ WP-B（keepwarm 指令＋保溫閘）→ WP-D（子代理 runlong／waitfor＋長前景閘）→ WP-E（只剩硬線＋F4＋R3 退役）→ WP-F → WP-G／WP-H。WP-0、WP-A 只做保溫包需要的部分。

**原待決選項（史料，已由上段裁決）**

- **D-1 上下文價值係數 q 與軟線**：① q=1（軟線約 53 萬；重放單次換窗淨省約 2,700 萬單位／14 天；建議）② q=0（純 token，軟線約 34 萬，換得更勤）③ 只留硬線 85 萬、不設軟線（上下文最大化；放棄 P4b 所示的讀取節省，量級約 1,800～2,700 萬單位／14 天）。
- **D-2 hold 戳記上限**：① 12 小時（建議）② 不設上限（到硬線為止）。

**可代決（SD／QA 依此執行，WHY 已附）**

- Q-1 閒置約 55 分自動壓縮的 harness 機制：WP-0 查官方 changelog／settings 是否有開關；不論結果，keepwarm 45 分截止都先擋在它前面。若官方有開關，**不關**（保溫失效時它仍是兜底），只寫進 ADR。
- Q-2 子代理 1h TTL 是否可設：WP-0 一併查證，結果只寫證據檔，不改本設計。
- Q-3 `P_fix` 推估值：WP-G 上線後一週以 M-K5 實測重算。

---

## 12. 連動面清單（收尾單人窗口同一個 commit 收齊）

- ADR-XPLAT-004 追加 §2.19（指向本檔、決策表摘要）；§2.13 R3 與 §2.14 HARD 段落就地註記「v2.1.22 起見 §2.19」。
- 根 CLAUDE.md：〈換 session 的 SOP〉改寫（軟線／hold／硬線、keepwarm、runlong／waitfor）、〈機械守衛總表〉`sessionctl_guard.py` 列補 Stop 保溫閘、PreToolUse PowerShell／Bash 長前景閘（`.claude/settings.json` matcher 同批；`TestR74…`／`TestR79…` 雙向鎖）、現查速查表加 `sessionctl keepwarm`／`hold`。
- PRD：§8.2～8.4 全文。
- `docs/06_quality/AutoSDD_Defect_Log.md`：watch quota 重複觸發立 DEF 列（本設計 §4.3 為修法）。
- `docs/02_architecture/Root_Layout_and_Module_Placement.md`：sessionctl 套件既有登記列補新檔名（`keepwarm.py`、`hold.py`、`longwait.py`、`costmodel.py`）；wastecensus 列補 `sections_keep.py`。
- `.env.example` 生成物、`tools/tests` 棘輪重釘（新測試檔）。
