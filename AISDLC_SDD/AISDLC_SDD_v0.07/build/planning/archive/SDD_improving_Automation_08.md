# SDD 自動化進化藍圖 08 — Phase H：生成–對抗–執行層（Generative-Adversarial Execution Layer）

> **✅ 執行狀態（2026-05-31）**：ACT-045~058 全數實作完成並驗收。pytest **440 passed**
> （+35 Phase H +1 稽核補洞）、chaos 100 輪 bounded_ratio=1.0、FSM/TLA/MD 三源同步測試全綠。
> 對應 CLAUDE.md **Rule 9.20**。
>
> **2026-05-31 稽核補洞（§G8 / ACT-056）**：抓漏發現結構性 ESCALATION_FINAL 雖算出 diagnostic
> 卻 (1) 不呼叫 save_abort_report，(2) 傳入的 dict 無法被僅吃 DiagnosticResult 的 render_steersman
> 渲染（舵手區塊被靜默吞掉）。已於 `fsm_runtime.enter_auto_recovery` 補 abort 報告寫入 +
> `steersman_renderer.render_steersman` dict 容錯，新增回歸測試，§6 wrong-spec 自我驗證鏈端到端成立。
>
> **執行接地後端狀態**：
> - ✅ **docker 後端已實作並真實驗證**（`DockerBackend`）— 容器實跑、exit code/stderr 捕捉、
>   測試摘要解析、硬 timeout 有界停機；3 個真實 docker e2e 測試 PASSED（pass / runtime_fail /
>   FSM 端到端路由），證明「按下執行鍵」鏈路：容器實跑→OQS→FSM 路由→logql 查根因。
> - 🟡 playwright(UI driver) 仍為 stub（node 不在本機）；TLC reachable 重算需 CI 的 java/TLC。
>   兩者屬環境限制，HTTP 層驗證已由 docker 後端覆蓋。


> **作者角色**：首席 AI 自動化架構師（Chief AI Automation Architect）
> **產出日期**：2026-05-31
> **對應 tag（規劃）**：`phase-h-gae`
> **前置基線**：Phase G Final（L5 Self-Driving，tag `phase-g-final`，pytest 401 passed / TLC 27/27 / chaos bounded_ratio=1.0）
> **驗證方法**：6 探針並行對 Anthropic「動態對抗框架」+ OpenAI「智慧體優先環境」前沿思維做缺口稽核（workflow `sdd-l5-gap-audit`，526K subagent tokens）
> **狀態**：規劃中（active）— 待人工 review 後進入 Phase H 實作

---

## 0. 終極結論（Executive Verdict）

| 維度 | 現況評級 | 說明 |
|------|---------|------|
| **有界停機（Bounded Halting）** | ✅ **業界頂尖** | FSM 27 狀態 + retry budget + TLA+/TLC 窮舉證明 + chaos 100 輪。此維度已超越多數商用 Agentic 系統。 |
| **圖靈完備的自動化閉環** | 🟡 **形式完備、語意未閉合** | 系統能「永遠停機」（halting 已證），但閉環的**回饋訊號是規格層的靜態投影**，而非執行層的客觀現實。閉環在數學上收斂，但收斂到的不一定是「能跑的軟體」。 |
| **L5 Self-Driving** | 🟠 **L4.9（規格自治），非 L5（現實自治）** | 框架達成的是「**規格驅動的自治**」（Spec-Driven Autonomy）。真正的 L5 需要「**現實驅動的自治**」（Reality-Grounded Autonomy）：Evaluator 必須能在隔離環境中**實際運行軟體**、觀測客觀錯誤，並反哺規格。 |

**一句話診斷**：
> 目前的系統是一台**證明過必然停機的規格校對機（Spec Proof-Checker）**，但它從未「按下執行鍵」。它能保證「文件之間自洽」，卻無法保證「軟體真的會動」。閉環缺的最後一環，是 Anthropic 反覆強調的 **execution-grounded Evaluator** — 讓評估器擁有 Playwright 級別的實體操作能力，在沙箱中親手運行 App、點擊 UI、捕捉 stderr 與 HTTP 真實回應。

---

## 1. `<thinking>` — 深度推理與漏洞挖掘

```
<thinking>

【第一性原理：什麼叫「圖靈完備的自動化閉環」？】
一個閉環要圖靈完備，需要三件事：
  (1) 狀態可無限演進（State）— ✅ 已有 FSM + decision_trace
  (2) 條件分支與停機（Branch + Halt）— ✅ 已有 retry budget + TLC 證明
  (3) 與「外部現實」的 I/O 通道（Tape R/W）— ❌ 這是缺口

第 (3) 點是致命的。圖靈機的紙帶是「外部世界」。目前 SDD 的「紙帶」
只有 docs/ 裡的規格文件——它讀規格、寫規格、比對規格。但它從來
沒有把「運行中的軟體」當作紙帶來讀寫。這就是為什麼我說它「形式
完備、語意未閉合」：它在一個封閉的符號系統裡自洽地循環，卻沒接
上現實的接地線（grounding）。

【套用 Anthropic 的對抗框架，挖第一個洞】
Anthropic 的 SDG（生成–評估分離）核心是：AI 不能改自己的考卷。
探針 G1/G2 證實：
  - dev-senior（Generator 生成器）寫程式
  - qa-tester / SCG gate（Evaluator 評估器）判程式
  - 但兩者都向「同一個 sdd-orchestrator」回報，由它一個 FSM
    控制迴圈同時決定「dev 改夠了沒」與「qa 測夠了沒」。
這是單點控制偏誤（single-point-of-control bias）：orchestrator
握有 retry budget（IMPLEMENTATION max_iterations=20）又握有
PR_REVIEW 的通過/失敗裁決樹。它有結構性動機去「讓測試通過」
而非「讓程式符合意圖」。這正是 GAN 訓練裡 mode collapse 的工程
對應物——生成器學會了騙過判別器，而不是生成真貨。

更深一層（G1）：就算分離了，Evaluator 的「判」也只是
drift_monitor.py 的 regex diff（行 98-133）+ 人工讀碼。它從不
「按執行鍵」。Anthropic 文中 [cite:100,137] 的關鍵洞見是——主觀/
複雜任務的評估，必須給 Evaluator 一個能「實際操作應用程式」的工
具（Playwright）。沒有執行，評估器就只是另一個會幻覺的讀者。一
個 P95<0ms 的荒謬 NFR，靜態 SLV 抓得到；但「並發下偶發 deadlock」
「記憶體在第 4 小時洩漏」「OAuth callback 在真實 redirect 下 400」
——這些只有「跑起來」才看得到。SCG-4 通過 = 紙上合規，不等於現實
可動。

【套用 Anthropic 的「主觀標準量化」+「動態演進」，挖第二、三個洞】
- 主觀量化：框架其實做對了一半——AmbiguityScorer（Rule 9.16）把
  「規格寫得模糊」量化成 0~1 分。這是漂亮的 subjective→quantified。
  但它只量化「輸入規格」的模糊度，沒量化「輸出產物」的品質。缺一個
  對稱物：Output Quality Scorer（執行結果的客觀評分）。
- 動態演進（G6，這洞最深）：Anthropic [cite:201,255] 說框架要能
  「隨模型變強，大膽移除不再需要的鷹架」。但 SDD 的 Rule 9 是
  純加法的：Phase D→E→F→G，9.1→9.19，只增不減。slv_generator
  甚至用 RuleOverwriteProtected 硬禁覆寫 verified 規則（行 350）。
  這會導致：
    (a) 規則幾何膨脹（SLV-001→∞）
    (b) FSM 狀態組合爆炸（已 27 狀態）
    (c) 最諷刺的——它會打爆自己的形式化證明：Rule 9.18 的 TLA+
        假設「固定狀態集」，每加一條規則就讓先前的 TLC 證明失效。
  一個只會長不會瘦的系統，最終會被自己的鷹架壓垮。這違反了
  Karpathy 式的審美：好的自動化是「持續刪除自己」的。

【套用 OpenAI 的環境防護思維，挖第四、五個洞】
- 漸進式揭露（G4）：OpenAI [cite:37,38,40] 說放棄龐大單一指令檔，
  用 docs/ 當地圖 + lazy load。SDD 的 docs/ 與 docs_template/ 確實
  做對了（專案產物知識結構化、按需）。但**治理規則本身**反其道而行：
  CLAUDE.md 的 Rule 9 有 605 行、INIT.md 825 行，宣稱「初始 ~200
  token」實則每 session 強制吃進 ~12,000 token 的規則。這是「規格
  優先」原則的自我背叛——它要求別人 spec-first，自己的 governance
  卻是 batch-load。而且規則是寫死在散文表格裡，連系統自己都無法
  「按狀態推理某條規則是否適用」，更別說 self-heal 重寫它。
- 運行時可觀測性（G5）：OpenAI [cite:36] 要求把日誌/指標/追蹤透過
  LogQL/PromQL 暴露給 AI 推理。SDD 的 Production Feedback（Rule
  9.10）卻是 File-based Pull——AI 只收到「NFR-PERF-001 在 24h 內
  違反 3 次」這種人類預先嚼碎的 HMAC 簽章檔案，無法 drill-down，
  無法問「為什麼請求 X 失敗」。OPEN-10.6 為了資安禁掉 HTTP endpoint
  是對的，但把嬰兒和洗澡水一起倒了——應該保留「AI 可查詢」能力，
  只是改用安全的本地唯讀查詢通道（見 §4）。

【上下文污染與衰減（用戶要求專查）】
這點 SDD 做得好，給它公道：stage-compaction（SPEC_FROZEN 強制
壓縮）、CONTEXT-SNAPSHOT、decision_trace（active 50 + FIFO flush）、
RESUME_VERIFICATION——結構化交接機制完整，脈絡重置有 hook 強制。
唯一隱憂（G7 衍生）：decision_trace 只 FIFO 不評估「哪些決策事後
證明是錯的」，flushed trace 永不回收。長期是隻會長不會修剪的記憶。

【停機問題與人類舵手（用戶要求專查，G8）】
停機本身：完美。wrong-spec 場景（自我驗證協議要求的極端案例）我
在腦中跑了一遍——
  dev attempt 1,2 fail（同 pattern H1）
  → TrajectoryPredictor S1+S2 觸發 → switch_to_audit
  → SPEC_AUDIT 跑 SLV → 抓到 AC↔INV 矛盾
  → ESCALATION → DiagnosticAgent 判 structural/spec_conflict
  → ESCALATION_FINAL（不自動修）→ 人工
  → TLC 已預證此路徑必達 terminal，零無限重試。
  ✅ Token 不會被燒乾，停機優雅。

但——致命的最後一哩（G8 三探針一致）：DiagnosticAgent 算出的
DiagnosticResult（sub_type=spec_conflict、rationale、哪條 AC 撞哪條
INV）**從未被傳進 save_abort_report()**（fsm_runtime.py:479-547 拿到
diagnostic 卻不傳；snapshot.py:202-234 的 save_abort_report 簽章根本
沒有 diagnostic 參數）。所以人類收到的 abort 報告只寫「retry
exhausted, escalation_count=N」，沒寫「AC-003-1 的 P95<0ms 與
INV-002 物理矛盾，請 sa-analyst 提供修正後的 AC-003-1」。

這就把人類從「環境設計舵手」降級成「考古學家」——他得自己重建矛盾
現場。OpenAI/Anthropic 的共同理念 [cite:34,35,44] 是：當 AI 撞牆，
系統要引導人類提供「AI 缺的工具或環境限制」，讓人類維持在設計環境
的高度。目前的 abort 是「我壞了，你修」（coder-demotion），而不是
「我缺 X 能力/這裡有結構矛盾，請你以舵手身份補上」（steersman）。
機器已經算出了答案，卻把答案吞了，只把痛苦丟給人。

【收斂：八個洞，一條主軸】
G1/G2/G3 = 缺「執行接地的對抗評估」（閉環的現實 I/O）
G4/G5    = 缺「AI 可推理的環境介面」（漸進揭露 + 可觀測查詢）
G6/G7    = 缺「鷹架的新陳代謝」（生成的對立面：刪除/垃圾回收）
G8       = 缺「機器→人類的舵手級交接」（停機後的尊嚴交棒）

主軸：系統精通「收斂與停機」，但欠缺「接地與代謝」。Phase H 要補的
不是更多護欄，恰恰相反——是讓系統第一次真正「接觸現實」，並學會
「丟棄自己」。

</thinking>
```

---

## 2. 缺口矩陣（Verified Gap Matrix）

| ID | 缺口 | 對應前沿思維 | 判定 | 嚴重度 | 核心證據 |
|----|------|------------|------|--------|---------|
| **G1** | 無執行接地的 Evaluator（從不運行 App） | Anthropic：賦予 Evaluator Playwright 實體操作能力 [100,137] | ✅ confirmed | 🔴 critical | `drift_monitor.py:98-133` 純 regex diff；SCG-4 全程「讀規格+看碼」無「跑起來」步驟；全樹無 playwright/e2e/sandbox/docker run |
| **G2** | Generator 與 Evaluator 共用同一 orchestrator 控制迴圈 | Anthropic：生成–評估分離，AI 不改自己考卷 [53,54,76] | ✅ confirmed | 🟠 high | `sdd-orchestrator-zh.yaml:17-24,87-91` 同一 context 既派 dev 又派 qa 又裁決；`subagent_contract.py` 只鎖 dispatch 生命週期非測試標準 |
| **G3** | IMPLEMENTATION 前無「測試標準合約談判」閘 | Anthropic：Planner 宏觀擴展→Gen/Eval 微觀合約談判 [127,140,142] | ✅ confirmed | 🔴 critical | SCG-3→stage-compaction→IMPLEMENTATION，中間無 `TEST_CONTRACT_NEGOTIATED` 態；QA 的 TEST-STRATEGY 單方產出，dev 不簽署 |
| **G4** | 治理規則（Rule 9）違反漸進式揭露，monolithic eager-load | OpenAI：放棄單一巨型指令檔，docs/ 當地圖 lazy load [37,38,40] | ✅ confirmed | 🟠 high | CLAUDE.md Rule 9 = 605 行 ~5,885 tok；INIT.md 825 行宣稱 200 tok 實則 ~6,371 tok；規則寫死散文表格，系統無法按狀態推理規則適用性 |
| **G5** | 無 LogQL/PromQL 級可查詢觀測介面，僅 file-based pull | OpenAI：日誌/指標/追蹤透過 LogQL/PromQL 暴露給 AI [36] | ✅ confirmed | 🔴 critical | `production_monitor.py:531-604` 只掃 inbox 移檔；AI 只收「NFR 違反 3 次」預嚼摘要，無法 drill-down 問「為何失敗」 |
| **G6** | 鷹架純加法，無規則退役/畢業/ROI 機制 | Anthropic：隨模型變強大膽移除鷹架 [201,255] | ✅ confirmed | 🔴 critical | Rule 9.1→9.19 只增不減；`slv_generator.py:350` RuleOverwriteProtected 硬禁退役；加規則即破 Rule 9.18 TLA+ 既有證明 |
| **G7** | 無常駐 GC Agent，清理全為被動 advisory | OpenAI：常駐 Agent 定期清理技術債與不一致 [42,45] | ✅ confirmed | 🟠 high | `post_commit_drift.py` 2s 預算只寫 warning 不啟背景工作；無 `deprecate_rule()`；decision_trace 只 FIFO 不評估決策對錯 |
| **G8** | 停機後 DiagnosticResult 未進 abort 報告，人類被降級 | Anthropic/OpenAI：引導人類補「缺的工具/環境」，維持舵手高度 [34,35,44] | ✅ confirmed（+1 partial +1 refuted 子項） | 🟠 high | `fsm_runtime.py:479-547` 拿到 diagnostic 卻不傳；`snapshot.py:202-234` save_abort_report 簽章無 diagnostic 參數；abort 只寫「retry exhausted」 |

> **公道話**：G8 子探針確認「停機偵測本身」是 partial-OK（wrong-spec 場景能正確 SPEC_AUDIT→ESCALATION_FINAL，token 不被燒乾）。問題純粹在「交接訊息的品質」，非「停機能力」。上下文管理（compaction/snapshot/decision_trace）則完全合格，不在缺口內。

---

## 3. Agentic 閉環狀態機設計（含生成、評估與合約談判）

### 3.1 核心架構轉變：從「規格校對閉環」到「生成–對抗–執行閉環」

```
                    ┌─────────────────────────────────────────────┐
                    │           PLANNER 層（宏觀規格擴展）           │
                    │   sa-analyst / sd-architect → FRD/SRD/OpenAPI │
                    └───────────────────────┬─────────────────────┘
                                            │ macro spec frozen (SCG-0~3)
                                            ▼
                    ┌─────────────────────────────────────────────┐
                    │   🆕 TEST_CONTRACT_NEGOTIATED（微觀合約談判）   │  ← 補 G3
                    │   Evaluator 草擬 Test-Contract（每 AC 明確     │
                    │   pass/fail + oracle）→ Generator 形式簽署     │
                    │   → git commit「測試標準凍結」→ 才准進實作      │
                    └───────────────────────┬─────────────────────┘
                                            │ test oracle frozen
          ┌─────────────────────────────────┼─────────────────────────────────┐
          ▼ (生成器，封閉)                                    ▼ (評估器，獨立)
┌───────────────────────┐                       ┌─────────────────────────────────┐
│  GENERATOR CONTEXT     │   產出 artifact        │   🆕 EVALUATOR CONTEXT（隔離）    │ ← 補 G1/G2
│  dev-senior / dev-dev  │ ───────────────────►   │   1. 在 sandbox 啟動 App         │
│  只能寫碼，看不到       │                       │   2. Playwright/HTTP 實際操作     │
│  Evaluator 的私有測試  │   ◄───────────────────  │   3. 捕捉 stderr/HTTP/exit code   │
│  oracle 細節           │   客觀 verdict + 日誌   │   4. 查詢 sandbox 可觀測層        │ ← 補 G5
└───────────────────────┘                       │   5. 對輸出產物量化評分（OQS）    │
          ▲                                       └────────────────┬────────────────┘
          │ FIX（僅當 verdict=FAIL 且非 spec 缺陷）                  │ verdict
          │                                                        ▼
          │                              ┌──────────────────────────────────────┐
          └──────────────────────────────│  NEUTRAL DISPATCHER（中立調度，非裁判） │
                                         │  sdd-orchestrator 降級：只路由不裁決    │
                                         │  裁決權交給獨立 Evaluator 的客觀 verdict│
                                         └──────────────────────────────────────┘
```

### 3.2 新增 / 修改的 FSM 狀態

| 狀態 | 類型 | 入口 | 出口 | 補的洞 |
|------|------|------|------|--------|
| **`TEST_CONTRACT_NEGOTIATED`** | gatekeep（阻塞） | `SPEC_FROZEN`（SCG-3 後、IMPLEMENTATION 前） | success→`IMPLEMENTATION`；無共識→`SPEC_DRAFTING`（規格不夠明確） | G3 |
| **`EXECUTION_EVALUATION`** | gatekeep（阻塞） | `IMPLEMENTATION`（取代部分 PR_REVIEW 的靜態判定） | pass→`PR_REVIEW`（靜態合規確認）；runtime fail→`IMPLEMENTATION`；spec defect→`SPEC_AUDIT` | G1/G2 |
| **`SCAFFOLD_GC`** | observation（非阻塞） | `enter_scaffold_gc()`（排程 / `RELEASE` 後 / 人工，結構同 PRODUCTION_SIGNAL） | continue→`RELEASE`；`respec`→`SPEC_DRAFTING`（退役提案另寫 SCAFFOLD-ROI 報告，交既有 `LEARNING_COMMIT` 人工 review 非同步消化，避免污染 LC 入口契約） | G6/G7 |

### 3.3 關鍵轉換規則（接續 `transition_rules._HAPPY_PATH`，須同步 SDD_FSM.tla — Rule 9.18.1）

```python
# Phase H 新增（規劃）— 寫入 transition_rules._HAPPY_PATH 時須同步 .tla
_HAPPY_PATH["SPEC_FROZEN"] = {"TEST_CONTRACT_NEGOTIATED", "SPEC_DRAFTING"}  # 改：插入談判閘
_HAPPY_PATH["TEST_CONTRACT_NEGOTIATED"] = {"IMPLEMENTATION", "SPEC_DRAFTING"}
_HAPPY_PATH["IMPLEMENTATION"] = {"EXECUTION_EVALUATION", "SPEC_AUDIT"}      # 改：先過執行評估
_HAPPY_PATH["EXECUTION_EVALUATION"] = {"PR_REVIEW", "IMPLEMENTATION", "SPEC_AUDIT"}
# SCAFFOLD_GC 為 observation，加入 OBSERVATION_STATES + .tla ObservationStates
OBSERVATION_STATES |= {"SCAFFOLD_GC"}
_HAPPY_PATH["SCAFFOLD_GC"] = {"RELEASE", "SPEC_DRAFTING"}  # 實作：退役提案另走報告，不直連 LEARNING_COMMIT
```

> **有界性保證（必須）**：`EXECUTION_EVALUATION` 沿用 retry budget（建議 `EXEC_EVAL_LIMIT=3`），同 pattern 連續失敗 → 沿用 TrajectoryPredictor S1/S2 提早 `SPEC_AUDIT`。`SCAFFOLD_GC` 為 observation 不阻塞、不可進 Terminals（Rule 9.18.4）。所有新狀態加入後**必重跑 TLC**，reachable coverage 須維持 100%（27→30 states），4 invariant 全 PASS——否則 Phase H 不得宣稱完成。

### 3.4 生成–評估分離的硬約束（補 G2）

1. **獨立 context**：Evaluator 在**獨立的 subagent context / 獨立 git worktree** 執行，其 test oracle 對 Generator **不可見**（防止 Generator 針對性過擬合，即 GAN mode collapse 的工程防護）。
2. **Orchestrator 去裁判化**：`sdd-orchestrator` 從「裁決者」降為「中立路由器」——它只負責「把 verdict 路由到下一狀態」，**不得**自行判定「測試夠不夠」。通過/失敗的唯一真實來源是 Evaluator 的客觀 verdict（exit code / HTTP status / OQS 分數），寫入 `build/reports/eval/EVAL-{stage}-{date}.yaml`。
3. **對抗驗證沿用既有機制**：Evaluator 的 verdict 若聲稱「PASS」，由第二個獨立 skeptic 子代理（沿用 Rule 9.8 pattern + 對抗驗證模式）嘗試 refute，多數 refute 則 verdict 翻為 FAIL。

---

## 4. 環境建構與記憶體管理策略

### 4.1 漸進式揭露重構（補 G4）— 規則即程式，非散文

**問題**：Rule 9 是 ~12K token 的散文表格，eager-load，系統無法按狀態推理。

**方案：Rule Registry — 把治理規則從 CLAUDE.md 抽成可查詢的結構化規則庫**

```
AISDLC_SDD_v0.01/governance/
├── RULES_INDEX.md                    ← 唯一 eager-load（地圖，~300 tokens）
│                                        每條僅一行：id / 標題 / 觸發狀態 / 嚴重度 / 指標檔
├── rules/
│   ├── R-9.1-fsm-retry-budget.yaml   ← lazy-load：trigger_states, spec, test_ref,
│   ├── R-9.14-self-healing.yaml          maturity（active/audit-only/deprecated）, scaffold_roi
│   └── ...                               ← 一檔一規則（呼應 memory 設計哲學）
└── rule_loader.py                    ← 按 FSM 當前 state 只載入 trigger_states 命中的規則
```

- **CLAUDE.md 瘦身**：Rule 9 巨表 → 替換為「Rule Registry 指標 + 載入協議」（保留 §9 的不可違反禁令摘要 ≤ 1 頁，細節移 governance/rules/）。
- **狀態感知載入**：`rule_loader.load_for_state("IMPLEMENTATION")` 只回傳該狀態相關規則（如 Brownfield 永不進 PR_REVIEW 就不載 9.18 TLA+ 規則）。
- **單一真實來源**：規則的 `maturity` 與 `scaffold_roi` 欄位成為 §4.3 GC 與 §5 退役的機讀依據——規則第一次變成「系統能對自己推理」的物件，而非散文。

### 4.2 Prompt 與記憶體管理（強化既有，補 G7 的記憶面）

- **保留**並肯定既有：stage-compaction / CONTEXT-SNAPSHOT / decision_trace（active 50 + FIFO）/ RESUME_VERIFICATION——此為框架強項，不動。
- **新增 decision_trace 品質回收**：flushed trace 不再永久堆積。`SCAFFOLD_GC` 週期性對 flushed trace 做「事後正確性標註」（該決策是否導致後續 escalation/drift），產出 `build/reports/gc/TRACE-AUDIT-{date}.yaml`，餵回 TrajectoryPredictor 校準信號權重——把記憶從「只記不評」升級為「記且評」。

### 4.3 運行時可觀測性（補 G5）— 安全的本地唯讀查詢通道

**設計原則**：保留 OPEN-10.6「禁 HTTP endpoint」的資安決策，但**恢復 AI 的查詢能力**——關鍵是「查詢」不等於「開 server」。

```
data/observability/
├── logs.ndjson          ← sandbox 執行產生的結構化日誌（唯讀）
├── metrics.ndjson       ← 時序指標
└── traces.ndjson        ← span/trace
tools/fsm_runtime/observability_query.py
   ├── logql_lite(query)   ← LogQL 子集，本地檔案查詢（無網路、無 endpoint）
   └── promql_lite(query)  ← PromQL 子集，聚合時序
```

- Evaluator 在 `EXECUTION_EVALUATION` 中可呼叫 `logql_lite('{level="error"} |= "deadlock"')` 直接對沙箱日誌**主動推理「為何失敗」**，而非被動收摘要。
- 仍經 anonymizer（沿用 Phase F PII 雙掃）後才能進跨實例 Hub。
- 與 file-based pull 並存：pull 給「生產 SLO 告警」，query 給「沙箱失敗根因分析」——兩者互補。

### 4.4 不變量防護欄（Invariants as Linter，肯定既有 + 一處強化）

- 既有 SLV-001~011 + AmbiguityScorer 已是良好的「自訂 Linter 不變量」，保留。
- **新增對稱物 — Output Quality Scorer（OQS）**：AmbiguityScorer 量化「輸入規格模糊度」，OQS 量化「輸出執行品質」（測試通過率 / 客觀錯誤數 / 效能 vs PBS / UI 斷言通過率），0~1 分，由 Evaluator 在沙箱執行後產出。讓「主觀產物品質」也被量化（呼應 Anthropic [82,84]）。

---

## 5. 終極優化藍圖 — 升級至 Level 5 自治（含垃圾回收與人類協作介面）

### 5.1 鷹架新陳代謝機制（補 G6/G7）— 系統學會「丟棄自己」

**核心思想（Karpathy 式）**：最好的自動化框架是會「持續刪除自己鷹架」的框架。引入 **Scaffold ROI** 與 **Rule Graduation**。

| 機制 | 定義 | 落地 |
|------|------|------|
| **Scaffold ROI** | 每條規則記錄 `fire_count`（觸發次數）/ `catch_count`（真攔到問題次數）/ `false_positive_count`。ROI = catch / fire。 | `rule_loader` 每次評估規則時記帳到 `governance/rules/R-*.yaml` 的 `scaffold_roi` 欄位 |
| **Rule Graduation（畢業/降級）** | 規則經 N 次（建議 1000 commits）`fire_count > 0 且 catch_count == 0` → `SCAFFOLD_GC` 提議降級 `active → audit-only`；再 N 次仍無攔截 → 提議 `deprecated` | 提議寫入 `LEARNING_COMMIT`，**人工 review 後**才生效（沿用 trust_level 人工 gate，絕不自動退役 verified 安全規則） |
| **常駐 GC Agent** | `sdd-gc-zh.yaml`（新 specialized agent）：排程觸發（建議每週 / RELEASE 後），執行 `SCAFFOLD_GC` 狀態：①算 Scaffold ROI ②稽核 decision_trace 正確性 ③掃技術債/不一致碼 ④提議退役清單 | 非阻塞 observation；產出 `build/reports/gc/SCAFFOLD-ROI-{date}.md` |

> **與形式化驗證的協同（關鍵）**：規則退役後 FSM 狀態集**縮小**，反而讓 TLC 驗證更易維持 reachable=100%。退役流程必須同步移除 `SDD_FSM.tla` 對應 transition 並重跑 TLC——把「刪除」也納入 Rule 9.18.1 雙源一致性。這讓「鷹架代謝」與「形式化證明」相互強化，而非衝突。

### 5.2 人類舵手協作介面（補 G8）— 停機後的尊嚴交棒

**修正**：`save_abort_report()` 簽章**必須**接收 `DiagnosticResult`，並透過新的 **Steersman Renderer** 把機讀分類轉成「環境設計請求」。

```
tools/fsm_runtime/steersman_renderer.py
   render(diagnostic, slv_verdict) → 結構化人類交接訊息：
     ┌──────────────────────────────────────────────────────┐
     │ 🛑 系統已優雅停機（已證明非無限重試，token 已保全）      │
     │                                                        │
     │ 【根因分類】spec_conflict（structural，不可自動修復）    │
     │ 【具體矛盾】AC-003-1「P95 < 0ms」與 INV-002「延遲 > 0」  │
     │            物理矛盾（SLV-004 verdict 附行號）            │
     │                                                        │
     │ 【你是舵手，不是修碼員】系統缺的不是「再試一次」，而是：  │
     │   👉 sa-analyst 角色：請提供修正後的 AC-003-1（建議      │
     │      P95 < 200ms），或說明此 NFR 的真實意圖              │
     │   👉 若這是「缺工具」：系統偵測到無法在沙箱啟動 X 服務，  │
     │      請提供 docker-compose 或環境變數 Y                  │
     │                                                        │
     │ 【恢復路徑】修正後輸入「確認恢復」→ RESUME_VERIFICATION  │
     └──────────────────────────────────────────────────────┘
```

- **sub_type → 能力缺口 → 環境請求** 三段映射表內建於 renderer：
  - `spec_conflict` → 「AI 缺正確規格」→ 「請角色 R 提供修正 AC/INV」
  - `data_corruption` → 「AI 缺完整狀態」→ 「請確認 .bak 或提供 snapshot」
  - `retry_exhausted`（含 G6 budget_exhausted）→ 「AI 缺能力/預算」→ 「請提供更強模型/工具/拆解任務」
  - 沙箱啟動失敗 → 「AI 缺環境」→ 「請提供 compose/憑證/mock」
- 這讓人類**永遠停留在「設計環境」的高度**：每次停機都是一次「請舵手補環境」的對話，而非「請工人改 bug」的指派。

### 5.3 L5 達成判準（Level 5 = Reality-Grounded Autonomy）

| 判準 | 現況（L4.9） | L5 目標 |
|------|------------|---------|
| 評估接地 | 規格/碼靜態比對 | ✅ 沙箱實際執行 + Playwright UI 操作 + 客觀錯誤捕捉 |
| 生成評估分離 | 共用 orchestrator | ✅ 獨立 context + oracle 不可見 + 對抗 refute |
| 合約談判 | 僅 OpenAPI freeze | ✅ Test-Contract 雙方簽署後才實作 |
| 可觀測推理 | file pull 摘要 | ✅ logql/promql lite 主動查詢根因 |
| 鷹架代謝 | 純加法 | ✅ Scaffold ROI + Rule Graduation + GC Agent |
| 人類角色 | 被降級為修碼員 | ✅ Steersman Renderer 維持環境舵手高度 |
| 形式化保證 | TLC 27/27 | ✅ 含新狀態與退役流程，維持 reachable=100% |

---

## 6. 自我驗證協議重演（Spec 寫錯 → 測試永不通過）

**經 Phase H 優化後，跑一遍極端案例：**

```
1. SCG-0：AmbiguityScorer 對 AC-003-1「P95 < 0ms」評分 → 若措辭模糊先擋；
   若數值明確但荒謬，放行至下游（量化器不負責物理檢查）。
2. TEST_CONTRACT_NEGOTIATED（🆕 G3）：Evaluator 草擬 oracle「斷言 P95 < 0」，
   Generator 簽署前即可能標註「物理不可能」→ 退回 SPEC_DRAFTING（最早攔截點）。
3. 若漏過：IMPLEMENTATION → EXECUTION_EVALUATION（🆕 G1）：
   沙箱實跑，OQS 測得 P95 = 47ms，斷言 P95<0 必 FAIL，且 logql_lite 查得
   「assertion never satisfiable」客觀證據。
4. 連續 fail 同 pattern → TrajectoryPredictor S1+S2 → switch_to_audit → SPEC_AUDIT。
5. SPEC_AUDIT 跑 SLV-004 → 確認 AC-003-1 ↔ INV-002 矛盾 → ESCALATION。
6. DiagnosticAgent → spec_conflict / structural / 不可自動修 → ESCALATION_FINAL。
7. 🆕 Steersman Renderer（G8）：abort 報告明確寫出
   「AC-003-1 與 INV-002 物理矛盾，請 sa-analyst 提供修正後 AC，建議 P95<200ms」。
8. TLC 已預證此路徑必達 terminal → token 全程有界、零無限重試。
```

✅ **結論**：優化後系統能在**三個遞進關卡**（合約談判 / 執行評估 / SPEC_AUDIT）攔截 wrong-spec，最早在「按下執行鍵之前」就擋下；停機優雅且 token 有界；最關鍵——**人類收到的是可直接行動的舵手級請求，而非待考古的狀態 dump**。原始 Phase G 已能停機但訊息劣化；Phase H 補上「接地偵測」與「尊嚴交棒」兩環，閉環語意才真正閉合。

---

## 7. 執行計畫（Phase H：Generative-Adversarial Execution Layer）

> 接續既有 ACT 編號（現至 ACT-044），Phase H 為 ACT-045 起。每個 milestone 完成須過對應 gate 並重跑 TLC + chaos。

### M1 — Execution-Grounded Evaluator（補 G1/G2，最高優先）

| ACT | 任務 | 產出 | Gate |
|-----|------|------|------|
| ACT-045 | `EXECUTION_EVALUATION` 狀態 + Evaluator 隔離 context（git worktree） | `transition_rules` + `SDD_FSM.tla` 同步 + `agent/specialized/sdd-evaluator-zh.yaml` | TLC reachable 28/28 |
| ACT-046 | Sandbox Runner（docker-compose 啟動 App）+ Playwright/HTTP driver 抽象層 | `tools/fsm_runtime/sandbox_runner.py` + `evaluator/driver/` | 能對 sample app 跑出客觀 verdict |
| ACT-047 | Output Quality Scorer（OQS）+ 對抗 refute（沿用 Rule 9.8） | `tools/fsm_runtime/output_quality_scorer.py` | OQS fixture 準確率 ≥ 80% |
| ACT-048 | orchestrator 去裁判化（降為中立路由） | `sdd-orchestrator-zh.yaml` 改 step_4/step_6 | verdict 唯一來源為 Evaluator |

### M2 — Test-Contract Negotiation（補 G3）

| ACT | 任務 | 產出 | Gate |
|-----|------|------|------|
| ACT-049 | `TEST_CONTRACT_NEGOTIATED` 閘 + Test-Contract 模板 | FSM + `docs_template/sdd/testing/TEST-CONTRACT-NEGOTIATION-TEMPLATE.md` | 每 AC 有明確 oracle |
| ACT-050 | Generator 簽署協議（git commit 記錄雙方共識） | `subagent_contract.py` 擴充 `test_standard_agreement` | dev 未簽署不得進 IMPLEMENTATION |

### M3 — Progressive Disclosure 重構（補 G4）

| ACT | 任務 | 產出 | Gate |
|-----|------|------|------|
| ACT-051 | Rule Registry：Rule 9 抽成 `governance/rules/*.yaml` 一檔一規則 | `governance/RULES_INDEX.md` + `rule_loader.py` | CLAUDE.md Rule 9 瘦身至 ≤ 1 頁指標 |
| ACT-052 | 狀態感知載入 + 規則 maturity/scaffold_roi 欄位 | `rule_loader.load_for_state()` | 初始 governance load < 1K tokens（實測） |

### M4 — Runtime Observability Query（補 G5）

| ACT | 任務 | 產出 | Gate |
|-----|------|------|------|
| ACT-053 | 本地唯讀 logql_lite / promql_lite 查詢層 | `tools/fsm_runtime/observability_query.py` + `data/observability/` | Evaluator 可查沙箱日誌根因；無 HTTP endpoint（守 OPEN-10.6） |

### M5 — Scaffold Metabolism（補 G6/G7）

| ACT | 任務 | 產出 | Gate |
|-----|------|------|------|
| ACT-054 | Scaffold ROI 記帳 + Rule Graduation（active→audit-only→deprecated） | `rule_loader` ROI 欄位 + graduation 邏輯 | 退役須人工 review（trust gate） |
| ACT-055 | 常駐 GC Agent + `SCAFFOLD_GC` observation 態 + decision_trace 正確性稽核 | `agent/specialized/sdd-gc-zh.yaml` + FSM + `.tla` | TLC：含退役流程仍 reachable=100% |

### M6 — Steersman Handoff（補 G8）

| ACT | 任務 | 產出 | Gate |
|-----|------|------|------|
| ACT-056 | `save_abort_report()` 簽章加 `DiagnosticResult` + SLV verdict | `snapshot.py` / `fsm_runtime.py` | abort 報告含 sub_type + 具體 AC/INV |
| ACT-057 | Steersman Renderer（sub_type→能力缺口→環境請求 三段映射） | `tools/fsm_runtime/steersman_renderer.py` + abort 模板改版 | wrong-spec 場景輸出舵手級請求 |

### M7 — Phase H 驗收

| ACT | 任務 | 判準 |
|-----|------|------|
| ACT-058 | 全量回歸 + chaos 100 輪（含新狀態）+ TLC（30 states）+ §6 自我驗證腳本自動化 | bounded_ratio=1.0；TLC reachable=100%；4 invariant PASS；pytest 全綠；wrong-spec e2e 在「執行前」即攔截並輸出舵手請求 |

---

## 8. 風險與防護

| 風險 | 防護 |
|------|------|
| 沙箱執行引入無界等待（違反有界停機） | `EXECUTION_EVALUATION` 套用 `EXEC_EVAL_LIMIT=3` + 沙箱硬 timeout；FSM 本身不做 wall-clock wait（保 chaos-testable，沿用 Rule 9.14 架構約束） |
| GC 誤退役安全關鍵規則 | 退役走 `LEARNING_COMMIT` 人工 gate；`verified` 安全規則永不自動退役；退役同步 TLC 證明 |
| Rule Registry 拆檔造成同步債 | `rule_loader` 加雙源一致性測試（仿 Rule 9.18.1 _HAPPY_PATH↔.tla 模式）；CI 偵測 RULES_INDEX 與 rules/*.yaml 不一致即 fail |
| 新狀態破壞既有 TLC 證明 | 每個 ACT 完成即重跑 TLC，coverage 未達 100% 不得 merge（守 Rule 9.18.3） |
| 可觀測查詢層洩漏 PII | 查詢結果進 Hub 前經 anonymizer 雙掃（沿用 Phase F M2） |

---

## 9. 一頁總結

> **目前的 SDD 是一座證明過必然停機的「規格大教堂」——結構嚴謹、形式完備、自我證明。但它的祭壇上從未放過一件「真的會動的軟體」。**
>
> Phase H 做三件事，讓它從 **L4.9 規格自治** 跨入 **L5 現實自治**：
> 1. **接地（G1/G2/G3/G5）**：讓 Evaluator 第一次按下執行鍵——在沙箱實跑、用 Playwright 操作、查 logql 根因、與 Generator 先談妥測試合約再開工。
> 2. **代謝（G4/G6/G7）**：讓系統第一次學會「丟棄自己」——Rule Registry 漸進揭露、Scaffold ROI 量化鷹架價值、GC Agent 提議退役過時護欄。
> 3. **交棒（G8）**：讓停機第一次有尊嚴——把機器已算出的診斷，轉成「請舵手補環境」的具體請求，而非丟給人類一堆狀態殘骸。
>
> 框架最強的「收斂與停機」維持不動；補上最缺的「接地與代謝」。閉環的最後一環—**現實**—終於接上。

---

*本藍圖由 6 探針並行缺口稽核（workflow `sdd-l5-gap-audit`）驗證，所有缺口判定附 file:line 證據。待人工 review 後進入 Phase H 實作。*
