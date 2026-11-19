# R217 Architect 報告：PRD v2.1 全面檢討——「任務沒結束、工作就停滯」

> 角色：Architect（Opus），全程唯讀；本檔邊做邊寫。座標格式＝`檔案:行號`；「推論」二字標明非實查。

## 0. 已讀
- 根 CLAUDE.md（system-reminder 注入）、任務書、共同全貌檔。
- PRD v2.1 L1–245（修訂表 v2.1.0～v2.1.22、§0、§1、§2、§3）。

- PRD L1000–1310（§4.3、§4.5.1～§4.5.7）、L2357–2656（§11～§15）、L2655–2690、L2766–2790（§16.1／§16.5／§16.6）。

## 1. PRD 讀後關鍵事實（座標）
- F1 §1.2 原則 1（PRD:128-130）：「Daemon 是指揮官（Governor）…本身不得呼叫任何 LLM」；§3.1 單一 Daemon 架構圖（PRD:181）已入 §16.7 退役。§15.2（PRD:2489-2491）Q3：常駐 Daemon 唯一正當理由＝帳號層級決策；§15.3（PRD:2504-2532）最小架構＝statusLine＋hook＋決策器，**沒有任何「任務推進者」元件**。
- F2 §4.5.7 偏離 2（PRD:1294-1304）：`autoclaude/utils/notifier.py` 未安裝於根層 `.venv`，續航路徑「跨子專案 import 會 ImportError」→ 刻意不用 AutoClaude。＝PRD 自己記錄了「續航路徑與 AutoClaude 引擎在套件層斷開」。
- F3 §11.3（PRD:2375-2379）：喚醒驗收只到「接續正確的 `interrupted_step`」「完成任務」，**「任務」從未定義**（§2 名詞表 PRD:157-167 無「任務／完成」詞條）。
- F4 §16.1 邊界（PRD:2684）：「Windows 真機親驗不入本表」——真機驗收在結構上被排除於結案判準之外。
- F5 §16.5（PRD:2772-2774）：「⏸ 沒有掃描器——它是症狀索引，不是待辦清單」「**沒有**逐輪遞延的待辦清單」。這是 v2.1.17 為拆「覆蓋度永動源」（PRD:2659）而刻意的設計。
- F6 §16.6 v2.1.22 列（PRD:2787）：結案格 ⏸，但⏸原因寫「E2E-SS-04／05、V-SS1～V-SS5 尚未全數入帳——全部入帳且 QA PASS 後轉 ✅」＝這是**待辦**，不是症狀；違反 §16.1 (c)（PRD:2676：⏸ 只准留給症狀在本 repo 製造不出來的列）。待辦被裝進「沒有掃描器」的格子 ⇒ 結構上無驅動器。**這是本次「宣告式完成」在 PRD 層的直接成因。**

## 2. 當回合實查證據（全部本棒親跑）

- E1 宣告式完成原文（主逐字稿 `31ea79d4…jsonl`）：L1670 09:46:55Z「R216 全部完成…**仍未結的項目**：E2E-SS-04／E2E-SS-05／V-SS1～V-SS5…沒有需要你決定的事」；L1687 09:47:03Z「這輪**沒有剩下要做的事**…已經掛上主控保溫…最多 9 次」；L1703 10:32:15Z「保溫 ping，已重掛。」⇒ 未結項明列、卻零驅動器。
- E2 midwork 判準（`tools/lib/sessionctl/midwork.py:8-18, 72-80`）：只認「進行式詞表」∧「`background_tasks` 無 running」。「沒有剩下要做的事」不在詞表；且**保溫 shell 本身就是 running 背景任務** ⇒ `background_idle()` 回 False ⇒ 保溫把半路停工閘整個遮掉。結構上抓不到宣告式完成。
- E3 叫醒噪音（同逐字稿，task-notification 依 task-id 去重）：2026-11-18 20:06Z～11-19 10:32Z 共 **21 次**監督／保溫叫醒，rc 分佈 0×8、6×10、5×2、2×1。8 次 rc=0（all_done）全部在 harness 的「Agent finished」通知後 7～30 秒內（20:05:58→20:06:17、21:00:17→21:00:44、22:47:10→22:47:25、00:08:56→00:09:25、01:56:50→01:56:57、03:41:51→03:42:20、04:53:22→04:53:45、08:52:38→08:52:53）＝**純重複叫醒**。每次叫醒後主控前 3 筆 assistant 記錄 cache_read 合計 40 萬～99 萬（首筆 13.3 萬→33.0 萬隨上下文成長）。
- E4 殘局不收（`python tools/sessionctl.py status` 18:53 實跑）：ab573c773 仍「安靜」、另 3 支「殘局」。根因兩條：
  - (a) 已實證：被 TaskStop 的 killed 通知在 05d1b770 逐字稿 L769（`<status>killed</status>`），其後尚有 **284,096 bytes**；`roster._killed_ids` 只讀尾端 `_TAIL_BYTES=262144`（`roster.py:29,173-186`）⇒ 擠出尾端、認不到。
  - (b) 高信度推論：`roster.py:210` 的 `alive` 以 `procstop.sid_of(cmd)`（`procstop.py:113-116`，取命令列第一個 UUID）算；交棒開出的新視窗 pid 15660 命令列含舊 sid 05d1b770 ⇒ 擁有者被當成活著 ⇒ 永遠不降成殘局。DEF-200-611 D-2a 的 `_spawned_from` 修正（`roster.py:246-255`）只用在 `_windows()` 顯示，沒套到 `alive`。
  - (c) 殘局只「不列」（`RESIDUE_MAX_AGE_SECONDS=24h`，`roster.py:28,231-234`），沒有任何收斂動作；PRD 對代理生命週期唯一條文 §4.4.3 已退役（PRD:1029）。
- E5 AutoClaude 是否上場：根層 `tools/` 對 `autoclaude` 的引用只有 `tools/lib/engine_resume_job.py`（引擎拒絕長睡時的外部承接）與測試；`.claude/` 4 檔 13 處皆為守衛字面。`Get-ScheduledTask AutoSDD_EngineResume*`＝空；User 層 `AUTOCLAUDE_EXTERNAL_RESUME_CMD`＝空。`AutoClaude/checkpoints/` 今天 4 份 escalation 檔，抽查 `escalation_GOAL_SYNTHESIS_20261119_133555.md` 的 Playbook＝`…\pytest-of-wuwei\pytest-10911\…\pb.yaml`＝**單元測試寫進真 checkpoints 目錄**，不是真跑。⇒ 本輪 AutoClaude 引擎零次真實執行。
- E6 現存待驗標記：tracked `docs/**/*.md` 對「待真機|待掌舵者目視|待目視|仍待真機|待驗|計未結」共 143 處／61 檔（前三：R215_PendingVerification_Closure 19、RTM-SelfImproving-P4 11、ADR-XPLAT-004 10）。R215 已有一次性收斂設計（54 項）＋ `realverify` 載具，但**無任何排程或閘門會呼叫 `realverify`**（`tools/**/*.py` 引用全在 realverify 自身、cases 與測試）。
- E7 既有「有憑證的定時驅動器」先例：`AutoSDD_SI_Patrol`（`tools/si_patrol_tick.ps1`，LastTaskResult 0、NextRunTime 2026/11/19 19:00）——自我精進已有「巡邏→事件→才運轉」形態，待驗項沒有。

## 3. 停滯分類學（工作停住、沒人推進）

| # | 型態 | 典型表徵 | PRD 涵蓋座標 | 機械物 | 本次失效？（證據） |
|---|---|---|---|---|---|
| S1 | 撞額度（5h／週） | API 層死、hook 零觸發 | §4.5.6 R-4.5.6-1/2（PRD:1196-1204）、§4.5.10 | 哨兵 schtasks＋`sentinel_decide` | 否（本輪無撞線；哨兵 `AutoSDD_Sentinel_31ea79d4…` 在） |
| S2 | 壓縮（auto／閒置壓縮） | 大上下文被壓、品質降 | §4.3（PRD:1000-1025）、v2.1.22 註記 | 硬線 HARD、keepwarm、precompact hook | 部分：R215 D-1 已記錄 `cachestate` 看不到 `compact_boundary`（R215 檔 §0-4） |
| S3 | session 死／換窗 | 視窗關、交接包未接 | §4.5.4（PRD:1128-1148）、v2.1.22 | handoff/seal/spawn/forward | 否；但 DEF-200-617 已修（共同全貌） |
| S4 | 第四類：散文交棒 | 決定留給人、結束回合 | **PRD 無**（grep 0；只在根 CLAUDE.md〈收尾常態規則〉） | `check_pending_handoff.py` | 否（「沒有需要你決定的事」為否定句，設計上放行） |
| S5 | 第五類：額度自願停 | 未撞線就停、叫人回舊窗 | **PRD 無**（park 只在 §4.5.4 v2.1.22 註記與 §16.6 出現） | `park`＋Stop park 閘 | 否（12:5x park 正常） |
| S6 | 第六類：半路停工 | 「接下來要做」卻無事件源 | **PRD 無**；ADR-XPLAT-004 §2.18 D5 | `midwork.py` | 不適用但**被遮蔽**：見 S7 |
| **S7** | **宣告式完成（新）** | 主控宣告完成，未結項無驅動器 | **PRD 無**；更糟：§16.1 邊界排除真機驗收（PRD:2684）、§16.5 明文禁待辦清單（PRD:2772-2774）、§16.6 v2.1.22 列把待驗收裝進⏸（PRD:2787） | **無** | **是**（E1、E2） |
| **S8** | **保溫遮蔽停工閘（新）** | 保溫 shell 讓「無背景工作」恆假 | 無 | 無（midwork 反被它關掉） | **是**（E2） |
| **S9** | **殘局代理不收（新）** | 名冊常駐、被當成「還在跑」 | §4.4.3 已退役 | roster 只標示、不收斂 | **是**（E4） |
| **S10** | **叫醒過多（新）** | 叫醒本身成為主要支出、每次 3 回合 | §1.2 原則 2 v2.1.22 註記只說「入帳」，無預算 | watch／keepwarm 無合併、無預算 | **是**（E3：21 次、8 次重複） |
| **S11** | **待驗項需要「閒置」卻被保溫消滅（新）** | E2E-SS-04 要閒置 45～100 分，主控保溫正好阻止它發生 | 無 | 無 | 是（推論：E1 列 E2E-SS-04 同時 E1 掛保溫） |
| **S12** | **人眼項無集合點（新）** | V-SS1～5 只寫在 TCS，下次人回來時無人提出 | 無 | SessionStart 簡報不讀待驗清單 | 是（E1、E6） |
| S13 | 引擎路徑長睡無承接 | AutoClaude 拒絕長睡 rc=1 | §16.2 §4.5.2 列（PRD:2720） | `engine_resume_job.py`（opt-in） | 未觸發（引擎零真跑，E5） |

**PRD 結構上沒有涵蓋的洞**：PRD 的量測軸只有「額度」與「上下文／快取成本」，**沒有「工作推進（liveness of work）」軸**——S4～S12 全部落在這個空軸上，它們的機械物散在根 CLAUDE.md 與 ADR-XPLAT-004 §2.18，PRD 不擁有、因此 §16 結案帳也不會把它們算進「做完」。

## 4. 洞的分級

**P1**
- **H1 沒有「完成」的定義，且結案帳主動排除驅動器**：§2 無「任務／完成」詞條（PRD:157-167）；§11.3「完成任務」未定義（PRD:2375-2379）；§16.1 排除真機驗收（PRD:2684）；§16.5 禁待辦清單（PRD:2772-2774）；§16.6 v2.1.22 列以⏸承載待驗收、違反 §16.1 (c)（PRD:2676 vs 2787）。⇒ 宣告式完成在規格層是**合法的**。
- **H2 停工閘在保溫下失明**：`midwork.background_idle` 把 keepwarm 算 running（midwork.py:72-80）；措辭判準不認完成宣告（midwork.py:30-39）。E2 實證。
- **H3 AutoClaude 不在續航路徑上，PRD 也沒把它放進去**：§1.2 原則 1 的 Governor 是「不呼叫 LLM 的 Daemon」（PRD:128-130），Daemon 已退役（§16.7）；§15.3 最小架構無「推進者」（PRD:2504-2532）；§4.5.7 明載 AutoClaude 套件不在根層 `.venv`、刻意不用（PRD:1294-1304）；引擎只以「一個會長睡的消費者」出現（PRD:2720、2803）。2026-08-08 掌舵者指令「無人看管時舵手是 AutoClaude（帶目標的 Playbook）」（repo 記憶 `unattended-helm-is-autoclaude.md`）**從未入憲**。

**P2**
- **H4 殘局生命週期無規格**：E4 (a)(b)(c)。
- **H5 叫醒無預算、重複叫醒**：E3；`watch.ORDER` 含 `all_done`（watch.py:31-33）與 harness 的 Agent finished 通知重複。
- **H6 驗收觀察期與「禁日曆觸發」衝突**：E2E-SS-05 要「上線滿 14 天」（PRD:2787），§16.5 禁日曆觸發（PRD:2774）⇒ 合規路徑上**不可能**被驅動。
- **H7 人眼項無集合點**：S12。

**P3**
- **H8 停工型態 4～6 不在 PRD**：PRD 對「半路停工／散文交棒／收尾常態」grep 0（`park` 僅 L1148、L2787）。
- **H9 AutoClaude 單元測試寫入真 `checkpoints/`**：E5（今天 4 份 escalation 檔來自 pytest 暫存 playbook），污染引擎真實告警面。
- **H10 退出碼兼作事件碼被顯示為失敗**：另一棒 SD 正修（r216_ux_brief），本棒不重複。

## 5. 「AutoClaude 沒有作用」的結論

**判定：兩者都是，但主因是「PRD 本身沒把 AutoClaude 放進這條路」。**
- PRD 視角：標題叫「AutoClaude 核心排程」，但 v2.1 核實後（§0.6、§15.2～§15.3）把治理塌成「Claude Code 原生能力＋hook＋根層 `tools/` 薄治理層」；Daemon（§1.2 原則 1 的 Governor）退役；AutoClaude 引擎在 PRD 裡只剩「一個會被額度擋住、需要外部重啟的消費者」（PRD:2720、2803）。PRD 從未規定「誰負責把一件任務推到完成」——治理層管的是**能不能跑**，不管**有沒有跑完**。
- 願景視角：2026-08-08 掌舵者分工（無人＝AutoClaude Playbook 當舵手，有 `global_goal`／`evaluator_command`／GOAL_SYNTHESIS／PG checkpoint）只存在於 repo 記憶與 improving_104 §4.5，未進 PRD、未進根 CLAUDE.md 的續航 SOP ⇒ 沒有任何元件會啟動它（E5：零真跑、零 EngineResume 排程、外部續跑變數空）。
- 為什麼這很要命：本次缺的「完成判準」**AutoClaude 已經有**——GOAL_SYNTHESIS 目標驗證＋`evaluator_command`（「AI 說完成不算，Evaluator 親自跑」）＋失敗鏈 escalation（`AutoClaude/autoclaude/plugins/goal_synthesis_plugin.py` 35 處、`_goal_synthesis.py` 10 處命中）。互動路徑則只有措辭詞表（midwork）。兩邊各有一半。
- 結構障礙（實查）：①根層 `.venv` 不含 `autoclaude` 套件（PRD:1297-1299 自述）；②引擎決策層走 MiniMax（`decision/minimax_client.py`），需另一把金鑰；③舵手狀態要 PG 後端才有續航意義（記憶檔）；④引擎以 subprocess 跑 `claude`，與互動 session 不共用上下文——適合「有明確驗收指令的批次項」，不適合需要對話脈絡的設計判斷。

## 6. 完成判準（終結條件）設計

**現況判準**：只有措辭（`check_pending_handoff` 詞表、`midwork` 進行式詞表）＋「有無背景任務」。兩者都是**代理指標**，主控一句「沒有剩下要做的事」＋一支保溫 shell 即通過（E1、E2）。

**提案：Open-Items Register（OIR，未結項登記簿）＋完成閘**
1. **單一資料面**：`docs/06_quality/OpenItems_Protocol/open_items.jsonl`（落點依根層 SSOT：協定資料 `docs/06_quality/<Module>_Protocol/`；函式庫 `tools/lib/openitems/`、入口 `tools/openitems.py`）。每項欄位：`id`、`source`（TCS／帳本／ADR 座標）、`kind ∈ {auto, observe, human, k1}`、`driver`、`credential`、`attempts`、`max_attempts`、`state ∈ {open, driven, closed, escalated}`、`evidence`。
   - 掃描器（零 token）把既有散落標記（E6 的 143 處）收斂成 OIR 列；新標記寫入文件時必須同時有 OIR 列（CI 鎖：文件出現「待真機／待目視…」字樣卻無對應 OIR id ⇒ 紅）。
2. **「完成」的機械定義**：任務（一輪／一個功能鍵）完成 ⇔ 其名下每個 OIR 列滿足下列其一：
   - `closed`：附證據（RealVerify 帳列、CI run、逐字稿座標）；
   - `driven`：有**驅動器＋排程器自報憑證**（Windows `NextRunTime` 值／mac rc），且 `attempts < max_attempts`；
   - `human`／`k1`：已進「掌舵者目視清單」並由 SessionStart 簡報呈現（事件驅動、零成本），清單上限 N 項，超過 ⇒ 必須先嘗試轉機驗（R215 的 B→機驗換算）。
   - 其餘＝**未驅動項（undriven）**，任務不得宣告完成。
3. **驅動器四型**：
   - `auto`：`realverify` 案例，以一次性 schtasks（沿用 `schedule_backend`／`engine_resume_job` 原語與四項設定）在**沙盒 session** 跑，不佔主控上下文；E2E-SS-04 這類「需要閒置」的項目必須走沙盒，**不得**拿主控 session 自己閒置（S11）。
   - `observe`：驗收觀察期（E2E-SS-05 的 14 天）＝**一次性**到期檢查排程＋讀量測（`waste_census --switch-metrics`），不是週期觸發；需 §16.5 修憲豁免（H6）。
   - `human`：SessionStart 簡報＋同回合 AskUserQuestion（掌舵者在場時）。
   - `k1`：只列、不推（DEC 只認真人）。
4. **完成閘（Stop，狀態為主、措辭不參與）**：Stop 時若「本 session 新增或觸及的 OIR 列中有 undriven」⇒ 推回一次，句內給出口：`python tools/openitems.py drive <id>`（掛驅動器）／轉 human 清單／AskUserQuestion。修正 S8：`background_idle` 判定時**排除 keepwarm／watch 這類純保溫 shell**（它們不推進工作）。
5. **防永動（回應 §16.5 的本意）**：`max_attempts` 出廠 2；用盡 ⇒ `escalated`，轉 human 清單一次、不再自動重排。OIR 只收「已立案功能的驗收項」，不收「覆蓋度缺口」——母體仍凍結，不復活 v2.1.17 拆掉的永動源。
6. **Token 帳（推論，依 E3 數字）**：主控上下文 C≈30 萬時，一次冷重寫≈C×1.25≈37.5 萬加權；一次保溫叫醒若只 1 回合≈C×0.1≈3 萬，若如實測 3 回合≈9～10 萬。`auto` 驅動器在沙盒跑，主控成本≈0；`realverify` 單案以 haiku／sonnet `claude -p` 計，本機 RV 案上下文 2 萬級（名冊 rv-t1-worker 上下文 22,336、累計 131,366）⇒ 每項自驗約 10 萬級 token，遠小於一次主控冷重寫。結論：把待驗項從「主控閒置等人」搬到「沙盒排程自驗」是**淨省**。

## 7. 事件源噪音與叫醒預算

- 實測（E3）：14.5 小時 21 次；其中 8 次 all_done 與 harness 的 Agent finished 通知重複（≤30 秒）；保溫型 rc=6 10 次（子代理還在跑、主控 45 分無記錄）；每次主控回 ~3 回合。
- 評估：
  1. **砍掉 watch 的 `all_done` 事件**（harness 已保證送達子代理完成通知；watch 只保留 harness 不會送的：quota／budget／stall／overrun／keepwarm）。預估去掉 8/21＝38% 叫醒。
  2. **單一保溫源**：同一 session 同時只允許一個持有保溫錨的行程（watch 在時由 watch 帶、無背景代理時才 keepwarm）——現況 watch 已內含 keepwarm 事件（`watch.py:33,161-162`），缺的是「互斥」與憑證檢查。
  3. **一叫一回合**：保溫叫醒的處置必須 1 個 assistant 回合內完成（重掛＋結束），把 3 回合壓成 1 回合，每次省 ~2×C×0.1。可機械量：waste_census 新指標「每次保溫叫醒的主控回合數」。
  4. **叫醒預算**：每個閒置段的保溫叫醒數 ≤ ski-rental 上限（現 `keepwarm` cap，約 9～10）；**含子代理在跑期間**也計入同一預算（現況 watch 的 keepwarm 不受 keepwarm cap 約束——推論，待 SD 核）。
- 與 §1.2 的關係：原則 2「零 Token 遙測」管的是**量測**；叫醒是**控制動作**，有真成本。v2.1.22 只說「入帳」（PRD:134），應補一條「叫醒是預算化的致動器」原則：每次叫醒須能指出它避免的成本（避免冷重寫或推進工作），否則不准存在。

## 8. 改進架構草案（只設計、不實作）

### 8.1 元件變更
| 類 | 元件 | 變更 |
|---|---|---|
| 新增 | `tools/lib/openitems/`（register、scan、drive、gate）＋入口 `tools/openitems.py`＋`docs/06_quality/OpenItems_Protocol/` | OIR 資料面、掃描器、驅動器掛載（憑證必回讀）、完成閘判準 |
| 新增 | 一次性 `AutoSDD_OpenItem_<id>` 排程 | `auto`／`observe` 驅動器；沿用 `schedule_backend`、`engine_resume_job` 原語與 `realverify` 沙盒 |
| 改 | `.claude/hooks/check_pending_handoff.py`／`midwork.py` | 加 OIR 完成閘；`background_idle` 排除純保溫 shell（守衛面：暴露證據＝E1/E2 sid 31ea79d4 L1670/L1687） |
| 改 | `tools/lib/sessionctl/watch.py` | 移除 `all_done` 叫醒（或降為不退出的心跳）；保溫錨互斥 |
| 改 | `tools/lib/sessionctl/roster.py` | `alive` 套 `_spawned_from` 排除；killed 通知改讀「全檔 queue-operation 索引」或以 harness `<status>killed` 的 output-file 存在性判；殘局加「收斂」：TaskStop 不到者標 `retired` 寫痕跡，不再列 |
| 改 | `tools/lib/session_brief.py` | SessionStart 簡報加「掌舵者目視清單」（OIR human 列，上限 N） |
| 改 | AutoClaude 測試夾具 | checkpoints 目錄改 tmp（H9） |
| 第二期 | AutoClaude 當無人舵手 | `AutoClaude/scripts/openitems_playbook.yaml`：`global_goal`＝「OIR 中 auto 列全部 closed」、`evaluator_command`＝`python tools/openitems.py check --kind auto`（rc 0 才算達成）、tasks 由 OIR 生成；由 `AutoSDD_SI_Patrol` 同型巡邏在「有 auto 列 ∧ 額度帶允許 ∧ 無互動 session 活動」時啟動；前置：根層 `.venv` 安裝 `autoclaude`、PG 後端、MiniMax 金鑰檢查 |

### 8.2 PRD 修憲列草案（§16.5 (i) 程序；不改既有條文，只加修訂表列、就地註記、§16.6 列）— **共 8 列**
1. **修訂表 v2.1.23 列**：「§16.5 (i)：工作推進軸（Work Liveness）入憲——未結項登記簿、完成閘、叫醒預算、殘局收斂；AutoClaude 無人舵手第二期」。掌舵者原文＝2026-11-19「所以又是任務沒有結束, 工作就停滯了! AutoClaude又沒有作用了!」。
2. **§2 名詞表就地註記**：新增「未結項（Open Item）」「驅動器（Driver）」「憑證（Credential）」「完成（Done）＝名下無 undriven 列」四詞；與 `K_ctx`／`U5h` 同表、獨立軸。
3. **§1.2 原則 1／2 就地註記**：①執行面舵手分工——有人＝互動 Claude Code；無人且有明確驗收指令＝AutoClaude Playbook（第二期）；②叫醒是預算化致動器，每次叫醒須對應「避免的成本」或「推進的未結項」。
4. **§16.1 就地註記**：⏸ 不得承載待驗收項（v2.1.22 列⏸原因 ③ 依本註記改由 OIR 承接）；「Windows 真機親驗不入本表」改讀為「不入 §16.2 母體，但入 OIR，帶驅動器」。
5. **§16.5 就地註記**：「驗收觀察期一次性到期檢查」不屬日曆觸發（條件：一次性、綁單一 OIR 列、到期即結或 escalate、不得續期）。
6. **新增 §4.5.11 完成閘**（R-4.5.11-1 OIR 單一資料面；-2 完成定義；-3 Stop 推回一次、狀態判準不靠措辭；-4 純保溫 shell 不算背景工作；-5 `max_attempts` 防永動）。
7. **新增 §4.5.12 叫醒預算與事件源合一**（R-4.5.12-1 不得重複 harness 已送達的事件；-2 保溫錨互斥；-3 保溫叫醒 1 回合；-4 預算＝ski-rental 上限、含子代理在跑期間）。
8. **§16.6 新列**：本修憲自帶結案格；✅ 條件＝OIR 上線且 E6 標記全數映射、完成閘真機推回一次入 RealVerify 帳、M-叫醒指標 14 天內每次保溫 ≤1 回合、殘局名冊對 05d1b770 類案例歸零；再開症狀＝任一 session 宣告完成而 OIR 有 undriven 列。（殘局收斂另以 R-4.5.13 併入本列，不另立節。）

### 8.3 遷移步驟
1. M0（唯讀）：OIR 掃描器先產「現況清單」，與 R215 54 項對帳；不接任何閘。
2. M1：OIR 資料面＋`drive`／`check` 指令＋憑證回讀；把 v2.1.22 的 E2E-SS-04（沙盒）、E2E-SS-05（observe）、V-SS1～5（human）三類各掛一個先例。
3. M2：roster 兩修（alive、killed 索引）＋殘局 retire；watch 拿掉 all_done；保溫錨互斥。（不碰守衛面，可先行。）
4. M3：完成閘接進 Stop hook（守衛面，附暴露證據 E1/E2）＋`background_idle` 排除保溫 shell；SessionStart 目視清單。
5. M4：CI 鎖「文件待驗標記必有 OIR id」；waste_census 加叫醒指標。
6. M5（第二期）：AutoClaude openitems playbook，先 DRY_RUN 一週再放行。

### 8.4 被否決的方案
| 方案 | 否決理由 |
|---|---|
| 擴充 midwork 詞表收「完成／沒有剩下」 | 打地鼠（ADR-XPLAT-004 X31 同型）；措辭不是狀態，「沒有需要你決定的事」也可為真 |
| 讓保溫叫醒順便「推進待驗項」 | 叫醒在主控大上下文裡做工＝最貴的地方；且 E2E-SS-04 正需要不保溫 |
| 把待驗項全塞回 §16.2 母體 | 復活 v2.1.17 拆掉的覆蓋度永動源（PRD:2659） |
| 週期性 cron 掃所有待驗並重跑 | 違反 §16.5 無日曆觸發本意、無上限燒額度；改「一次性＋max_attempts」 |
| 立刻讓 AutoClaude 接管互動續航 | 重造 harness 已有能力，違反 §15.2「先採用」；引擎缺根層 `.venv`／MiniMax／PG 前置，第二期處理 |
| 子代理收卷後主控自動 SendMessage 續推 | 冷代理續棒被 sessionctl 成本閘擋（根 CLAUDE.md〈換 session〉不能做），且不解決無驅動器 |
| 只把殘局從名冊隱藏（現況 24h 不列） | 隱藏不是收斂；ab573c773 仍誤列「安靜」且誤導監督閘 |

## 9. 實耗
- 本棒 Opus，全程唯讀；工具呼叫約 30 次；名冊 18:53 顯示本代理上下文 172,861、累計 1,922,267（含讀 PRD 大段）。

