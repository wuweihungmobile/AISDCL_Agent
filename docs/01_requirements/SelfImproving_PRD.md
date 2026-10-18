# PRD - SelfImproving（自我進化機制）模組
# Product Requirements Document - Universal Template

**文檔類型**: PRD (Product Requirements Document)
**模板版本**: v0.01 Universal（結構複製自 `AISDLC_SDD/AISDLC_SDD_v0.30/docs_template/core/prd/PRD_Universal_Template.md`；模板本體未改）
**適用情境**: Brownfield（必讀章節 1–8；可選 10、11；依任務書另填 12、13、14）
**適用平台**: 不適用（工作流與治理機制，無 UI 平台）。介面＝CLI 文字（§7）；跨平台＝Windows PowerShell 與 macOS（NFR-SI-06）
**上游需求**: 掌舵者 T1（2026-10-18）原文五點（§14）；研究方法論 SOP `docs/05_development/SelfImproving_Research_Methodology_SOP.md`
**FSM 位置**: 鍵 `monorepo-selfimproving`、SPEC_DRAFTING（Stage-1；依任務書，本稿作者未跑 FSM CLI 查證）。本檔是 Stage-1 上位規格，FRD／TCS／SRD 於實作輪再產

## 📋 文檔元數據
| 項目 | 內容 |
|-----|------|
| **專案名稱** | SelfImproving（自我進化機制）模組 |
| **專案類型** | Brownfield |
| **目標平台** | 不適用（無 UI 平台；介面＝CLI 文字，見 §7）；跨平台＝Windows（PowerShell）與 macOS |
| **目標日期** | 無日曆日期（刻意；階段出口一律為症狀型判準，見 §8） |
| **文檔狀態** | Draft |
| **Product Owner** | 掌舵者 |
| **Stakeholders** | 掌舵者（唯一核准者）；主控 agent（Fable）；子代理（Sonnet／haiku）；AutoClaude 引擎；AISDLC_SDD FSM runtime；Console 操作者 |
| **撰寫日期** | 2026-10-19（掌舵者 T1 立案日仍為 2026-10-18） |
| **最後更新** | 2026-10-19 |
| **AISDLC 版本** | v0.30（LATEST；現查 `python AISDLC_SDD/scripts/sdd_version.py`） |

### 專案類型專屬欄位（Brownfield）
| 項目 | 內容 |
|-----|------|
| **既有系統名稱** | AutoSDD（AutoClaude 指揮官＋AISDLC_SDD 框架＋AgentConsole＋根整合層；monorepo 根 `AISDCL_Agent/`） |
| **現行版本** | AISDLC_SDD v0.30；其餘子專案版本一律現查各自 `CLAUDE.md`／`AISDLC_SDD/FRAMEWORK_STATUS.md`（本稿不寫死） |
| **目標版本** | 不適用（新增模組，非版本升級；框架改動走 LATEST 原地改，見根 `CLAUDE.md`〈路徑陷阱〉） |
| **系統文檔位置** | 根 `CLAUDE.md`、`AutoClaude/CLAUDE.md`、`AISDLC_SDD/CLAUDE.md`、`AgentConsole/CLAUDE.md` |
| **技術棧**（既有，非本 PRD 選型） | Python 3.11+（AutoClaude 引擎、SDD FSM runtime）；Next.js＋Spring Boot＋FastAPI（AgentConsole）；Claude Code harness（hooks／skills／auto memory） |

## 🎯 1. 專案願景與目標 (Vision & Objectives)
### 1.1 專案願景
讓 AutoSDD 對「同一類流程缺陷反覆發生」這件事，不再靠掌舵者與主控的記憶，而是由帳本驅動一條**有界、人工逐項核准、可一個動作回滾、以真實症狀驗收**的改進迴圈（觀察→歸因→提案→人工閘→沙盒套用→驗證→量測→退役）；全程不更新模型權重、不自動修改治理面。

**可被反證**：迴圈採納若干改進後，若連續兩個量測窗的同根因缺陷復發率（M1）都沒有低於迴圈啟用前的同尺度基線，或採納後回滾比例（M5）隨採納數上升，本願景即被反證——不自動下線，改列為掌舵者 T1 決策項（縮減範圍或廢止）。樣本不足＝NOT-EVALUABLE，既不算支持也不算反證。

### 1.2 業務目標
**解決的問題**:
- **現況痛點**（座標皆寫稿時現查）:
  - 復發靠人記得：缺陷帳本以自由文字記「再開症狀」，復發連結沒有結構化欄（例：DEF-200-551 現象欄以文字寫「DEF-200-535 再開症狀於 116 命中」，`docs/06_quality/AutoSDD_Defect_Log.md` 寫稿時第 324 行）⇒ 復發率今天只能人工數。
  - 記憶面沒有結果標籤與退役：Claude Code 記憶索引 `MEMORY.md` 寫稿時為 22,755 bytes／113 行（記憶目錄共 125 個 .md 檔，含索引），逼近官方載入上限（S-08 稱「前 200 行或 25KB」；25KB 換算未查證），沒有退役或合併機制。
  - 引擎演化「只提案不套用」靠「舊 PlaybookRunner 沒有生產建構點」而非守衛（OBS-SI-010；`AutoClaude/CLAUDE.md:191`）。
  - 改進提案沒有獨立評估器：AutoClaude 演化提案與根整合層的改進迴圈皆無 held-out（SOP II-6 缺口欄）。
  - 提案沒有統一審閱介面與冷卻：被否決的同型提案可重複出現（SDD 規則面有 add↔retire 抖動防護 R-9.24，其他面無）。
- **目標用戶**: 掌舵者（主要）；主控與子代理（執行者）。
- **市場機會**: 不適用（Brownfield 內部模組；替代方案比較見 §4.2）。

**預期成果**（階段性、以症狀出口表達，無日曆；出口全文見 §8）:
- **短期＝P0＋P1**：任何視窗新增觀察時不需追問欄位；提案物件與提案卡可被掌舵者三句話判讀。
- **中期＝P2**：至少一筆真實提案走完「閘→沙盒→驗證→晉升或否決」，正式面零未經閘的變更。
- **長期＝P3**：M1～M5 可重跑量測；至少一個採納窗關閉並入帳；至少一筆退役走完人工閘。

### 1.3 成功指標 (Success Metrics)
只准症狀型結果指標。初值參數（W_N、W_MIN 等）皆標「初值（未校準）」，見 §5 開頭說明。基線未量測者一律寫 NOT-EVALUABLE，不得用估計值頂替。

| 指標類型 | 具體指標 | 目標值 | 衡量時間點（事件，非日曆） | 量法與資料來源 |
|---------|---------|--------|---------------------------|----------------|
| **結果指標** | **M1 同根因缺陷復發率** | 窗內 M1 低於迴圈啟用前的同尺度基線；連續兩窗未低於基線＝願景被反證（§1.1） | P2、P3 出口評估；每個採納量測窗關閉時 | M1＝窗內「已結列被確認再現」數 ÷ 窗內已結列數；窗＝最近 `W_N`（初值 20，無先例）筆首詞為 `fixed` 的 DEF／OBS 列；再現候選由量測腳本自帳本抓（`reopens:` 標記、現象欄「再開症狀…命中」字樣），確認由審查者（≠歸因者）；n < `W_MIN`（初值 5，先例 `params.json` 的 `q1b_min_n`）＝NOT-EVALUABLE。來源：`docs/06_quality/AutoSDD_Defect_Log.md`（含 `_archive_*`）、觀察帳本 |
| **結果指標** | **M2 DEF 列從立案到 fixed 的中位時間** | 不高於基線；不得以多開 `closed-by-decision` 取得改善（該類另列資訊欄） | 同上 | 中位數（`fixed@<sha>` 的 commit 時間 − 該列「發現日期」），單位日（日期欄無時分）；sha 取自狀態欄、commit 時間以 git 查；sha 無法解析者排除並計數。來源：缺陷帳本＋git |
| **結果指標** | **M3 再開症狀命中後到修復的時間** | 不高於基線 | 同上 | 中位數（修復 commit 時間 − 命中列發現日期）；命中清單同 M1 的確認結果。來源：缺陷帳本＋觀察帳本＋git |
| **結果指標** | **M4 提案被否決後同型提案再出現的次數** | 0（由冷卻結構保證；>0＝冷卻被繞過） | 每次人工閘決定時 | 計數（同型＝artifact_class＋target＋〔根因鍵相同或證據座標有交集〕）在冷卻期內且無再提資格事件而再生成者。來源：PROP／DEC 紀錄 |
| **結果指標** | **M5 採納後回滾比例** | 不隨採納數上升；無「未經人工閘而採納」者 | 每個採納量測窗關閉時 | M5＝窗內被回滾的 promoted PROP 數 ÷ 量測窗已關閉的 promoted PROP 數；`unverified_ack` 採納另列、不併入分母。來源：DEC 紀錄 |

#### 1.3.1 明文禁止當成功指標（Goodhart）
| 禁用指標 | 為什麼不行 | 座標 |
|---------|-----------|------|
| 提案數、採納率、駁回率 | 可被灌水（多提小案、挑好過的案）；只准當資訊欄 | DP-10；先例：五問協定家族計數降為資訊欄（`docs/06_quality/FiveQuestion_Audit_Protocol/README.md`:85–89） |
| 審查產出數（發現數）、OBS 筆數 | 對擴張中的面做對抗搜尋沒有不動點；多查漲、少查歸零 | C-13；根 `CLAUDE.md`〈守衛面准入〉 |
| 任何自評分數（LLM 信心、「這提案很好」） | 自評存入記憶會放大錯誤；自評不得充當成效 | DP-01、DP-05（S-11、S-20、S-21）；禁令 17 |
| 覆蓋度、測試數、行數等量化代理 | 對代理指標過度最佳化會損害真實表現 | DP-10；C-12（無覆蓋度門檻） |
| 「零發現」 | 零發現不是 PASS | C-13；`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md`:371–375 |

**🔴 人機協作確認點**：[ ] Stakeholders 確認願景與反證條件一致　[ ] 成功指標可衡量且合理（尤其 `W_N`、`W_MIN` 初值）　[ ] 短中長期成果有清晰路徑

## 👥 2. 目標用戶與使用場景 (Target Users & Use Cases)
### 2.1 用戶角色定義
| 用戶角色 | 描述 | 主要需求 | 使用頻率 | 技術熟練度 |
|---------|------|---------|---------|-----------|
| **掌舵者** | Product Owner、唯一核准者；以 T1 立案新需求 | 以最小閱讀量做 K=1 決定；看見症狀指標而非產出數 | 事件驅動（每張提案卡一次決定） | 高 |
| **主控 agent（Fable）** | 裁決與親驗：派工、路由、驗收交件、親跑重驗 | 讓子代理無法繞過閘；交件可被零信任重驗 | 每次運轉 | 高 |
| **子代理（Sonnet／haiku）** | 受任務書約束的執行者：擷取、歸因、提案、審查（角色分離） | 明確任務書、文字交卷、不碰正式面 | 隨派工 | 中（模型） |
| **AutoClaude 引擎** | 微核心＋Plugin；產生 ESCALATION／KB／演化提案事件 | 事件可被讀取；演化只提案 | 隨 playbook 執行 | 不適用 |
| **AISDLC_SDD FSM runtime** | 閉環治理狀態機；規則載入、SLV／SPEC-PATCH 提案、HUMAN_PENDING 閘 | 既有提案管線被重用而非重造 | 隨 FSM 狀態 | 不適用 |
| **Console 操作者** | 經 AgentConsole 檢視與簽核的人（目前即掌舵者） | 只讀顯示、既有簽核硬閘 | 隨使用 | 中 |

#### 2.1.1 迴圈權限矩陣（能做／不能做）
| 角色 | 能做 | 不能做 |
|------|------|--------|
| 掌舵者 | 立案 T1；對每張 PROP 下核准／否決／退回；下達晉升與回滾指令；明示解除冷卻；修改不可進化面（經 T1／PRD 修訂，不經本迴圈） | 沒有 digest 綁定的口頭「好」不構成核准；核准不能覆蓋憲法禁令（不提供「採納自我發明評估器」的核准路徑，須先修憲，禁令 22～25 末項） |
| 主控 agent | 派工與角色分派；讀全部帳本；親驗（親跑指令、先存 rc 再讀）；退回不合規交件；以單一窗口寫帳本處置欄 | 代為核准任何 PROP（MVP 不開放代決，附錄 C.2 #2）；改不可進化面；跳過驗證；以自評分數當成效；ESCALATION 後自動恢復 |
| 子代理 | 擔任擷取者、歸因者、提案者（產 `proposed` 物件）、審查者（唯讀、獨立 context）；在沙盒副本跑驗證 | 寫正式面；寫 DEC 紀錄；提案者看見 held-out 與評估指令；同一提案兼任提案者與審查者；再派子代理（遞迴）；寫報告檔（文字交卷，OBS-SI-004） |
| AutoClaude 引擎 | 產出 `MutationProposal`／escalation dump／KB 記錄（只提案）；執行 `evaluator_command` 取客觀訊號 | 未經人工閘把演化套用到正式 playbook；自改 `evaluator_command`（`REVISE_EVALUATOR` 型不受理）；ESCALATION 後自動恢復 |
| AISDLC_SDD FSM runtime | 驅動狀態、載入規則、產 `trust_level: proposed` 的 SLV／SPEC-PATCH 草案、`meta_halt_monitor` 把關、HUMAN_PENDING 閘 | 自動採納或退役 active 規則（禁令 11）；自動改 FRD／AC（禁令 12）；本迴圈不得繞過 `FSMRuntime` 讀寫狀態檔（禁令 1） |
| Console 操作者 | 只讀檢視 FSM 與（post-MVP）提案卡鏡像；在既有簽核硬閘內簽核 | Console 寫 FSM 狀態檔（一律經 `FSMRuntime` CLI 子行程，`AgentConsole/CLAUDE.md:15`）；以 Console 繞過 K=1 |

### 2.2 核心使用場景
| 場景 | 觸發條件 | 用戶目標 | 關鍵步驟 | 成功標準 |
|------|---------|---------|---------|---------|
| **SC-SI-1 同症狀復發→提案** | 新缺陷列的症狀與某已結列的再開症狀相符（例：DEF-200-535 的再開症狀於 116 命中而立 DEF-200-551） | 讓同根因不再第三次發生 | 觀察入帳（`reopens` 候選）→ 歸因（根因鍵）→ 產 PROP → 上卡 → K=1 決定 | 採納窗內無再現；M1、M3 可量 |
| **SC-SI-2 三句話決定** | 一張提案卡送達掌舵者 | 不讀長文即可決定 | 卡面三句（症狀／改動／風險與回滾）＋座標；回覆「核准／否決／退回 PROP-SI-NNN」 | 無歧義決定被記為 DEC，digest 綁定 |
| **SC-SI-3 否決後再提被擋** | 子代理對同一目標與根因再生成提案 | 不重複審同一件事 | 冷卻擋下；除非掌舵者解除或出現新證據 | M4＝0 |
| **SC-SI-4 記憶索引容量事件** | `MEMORY.md` 用量達上限的 `CAP_FRAC` | 條目不被默默截斷 | 產生退役／合併提案清單（M 類）→ 逐項 K=1 → 晉升前先做前置快照 | 索引回到上限內；回滾配方乾跑通過 |
| **SC-SI-5 迴圈自觀察（dogfood）** | 開發本模組時發現流程不當或 BUG（本輪 OBS-SI-001 起） | 迴圈自身的缺陷也能被消化 | 發現當下入帳；真缺陷升 DEF；對迴圈自身的改進走轉交 | 處置欄無「之後再看」且皆合枚舉 |

### 2.3 User Stories
- **US-SI-01** 身為掌舵者，我要在一張卡上用三句話決定核准／否決／退回，審閱成本才不隨提案複雜度增加（FR-SI-12、14）。
- **US-SI-02** 身為掌舵者，我要被否決的同型提案在沒有新證據前不再出現，才不必重複審同一件事（FR-SI-13）。
- **US-SI-03** 身為掌舵者，我要任何已採納的改進都能一個動作回滾，出錯時損失才有界（FR-SI-16、23）。
- **US-SI-04** 身為主控，我要子代理交卷的「流程摩擦」成為帶座標的觀察，教訓才不靠記憶累積（FR-SI-01、02、29）。
- **US-SI-05** 身為審查者（子代理），我要有獨立於提案者的外部可重跑訊號，驗證才不是自說自話（FR-SI-18、19、20）。
- **US-SI-06** 身為掌舵者，我要看到症狀型指標（復發率、修復時間、回滾比例）而不是提案數，才能判斷模組值不值得保留（FR-SI-22、24）。
- **US-SI-07** 身為掌舵者，我要記憶索引逼近上限時被提示退役或合併，而不是被默默截斷（FR-SI-25、27）。
- **US-SI-08** 身為 AutoClaude 維護者，我要「演化只提案不套用」是可重跑的檢查而不是文件宣稱（FR-SI-28）。

**🔴 人機協作確認點**：[ ] 用戶角色定義準確　[ ] 使用場景符合實際需求　[ ] 使用流程合理可行

## 🏗️ 3. 功能範圍與 MVP 定義 (Scope & MVP Definition)
### 3.1 MVP / 本次範圍（Brownfield：本次新增範圍）
**MVP 迴圈**（事件驅動，無日曆）：觀察 → 歸因 → 提案 → 人工閘（K=1）→ 套用（僅沙盒；最後一步「晉升」為人工動作）→ 驗證（審查者≠提案者）→ 量測 → 退役。

**MVP 邊界**：四類可進化工件（M 記憶條目、P Playbook 片段、R SDD 規則草案、D 非治理文件 diff）；掌舵者本人 K=1；CLI 文字提案卡；零新增守衛碼；不可進化面一律轉交（FR-SI-07）。**管轄範圍（誠實劃界）**：本迴圈只管轄經它提出的改進；掌舵者與主控依既有治理做的日常編修、以及 harness 自寫的記憶不在其管轄內，只作為觀察來源（FR-SI-29；§10 記憶污染列）。優先級 M＝Must-have、S＝Should-have（刻意不用 P0／P1，避免與階段 P0～P3 同名）。

| 群組 | 功能名稱 | FR | 階段 | 優先級 | 複雜度 | FRD 連結 | 狀態 |
|------|---------|-----|------|--------|--------|----------|------|
| FG-A | 觀察擷取 | FR-SI-01～04 | P0 | M | 低 | 實作輪產出 | P0 已 dogfood |
| FG-B | 歸因 | FR-SI-05～07 | P1 | M | 中 | 實作輪產出 | Planning |
| FG-C | 提案生成 | FR-SI-08～11 | P1 | M | 中 | 實作輪產出 | Planning |
| FG-D | 人工閘 | FR-SI-12～14 | P2（14 為 P1） | M | 中 | 實作輪產出 | Planning |
| FG-E | 套用（沙盒／晉升） | FR-SI-15～17 | P2 | M | 高 | 實作輪產出 | Planning |
| FG-F | 驗證 | FR-SI-18～21 | P2 | M | 高 | 實作輪產出 | Planning |
| FG-G | 量測 | FR-SI-22～24 | P3 | S | 中 | 實作輪產出 | Planning |
| FG-H | 退役 | FR-SI-25～27 | P3 | S | 中 | 實作輪產出 | Planning |
| FG-I | 既有缺口收斂／元層 | FR-SI-28、29 | P1、P0 | S、M | 低 | 實作輪產出 | Planning |

### 3.2 範圍外 (Out of Scope)
- ❌ 更新模型權重（RL 微調、自博弈訓練；SOP S1 不在範圍）。
- ❌ 自動改根 `CLAUDE.md`／`AISDLC_SDD/CLAUDE.md`／`AutoClaude/CLAUDE.md`／`.claude/**`／守衛面——無暴露證據不得碰（根 `CLAUDE.md`〈守衛面准入〉）；本 PRD 亦不新增任何守衛碼、鎖或 hook。
- ❌ 自我發明評估器（meta-oracle 自演化；禁令 22～25 末項、C-07）。反例（候選 CD-01：label-free 自設計評估套件作次級把關；S-24 單一來源，且須先有對抗分離不可繞過性證明，只登記不採納）。
- ❌ 以自評當唯一判官；以無驗證資料的軌跡蒸餾結果直接當採納依據（候選 CD-04，DP-01）。
- ❌ 經自動評估通過即自動採納、無人工閘（候選 CD-02，S-18／S-19；違反禁令 11、12）。
- ❌ 對每次採納做 e-process 序貫統計把關（候選 CD-03：證據單一、本系統無實證，只登記）。
- ❌ 無界遞迴與任何層級的自我擴充（維度、詞彙、算子、字母、深度、互遞迴；禁令 19～25）；迴圈不改自己的預算、閘門、停機條件與指標定義（DP-12）。
- ❌ 日曆觸發、版本號觸發、覆蓋度門檻、「每 N 輪」型觸發（C-12）；常駐行程或排程驅動（本 repo 刻意不做 Daemon：`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` §16.1 ➖）。
- ❌ 運轉期使用 WebSearch／WebFetch 做文獻擴充（SOP 已完成；重跑僅依 SOP S7 觸發）；跨機器同步記憶（auto memory 本機不跨機器，S-08）。
- ❌ 開 `AutoSDD_improving_117`（附錄 C.1；本 PRD 本身是驅動器）。

### 3.3 未來規劃 (Post-MVP；皆為 ⏸，以再開症狀驅動、不排日曆)
| 功能編號 | 功能名稱 | 再開症狀（一句可觀測事件） |
|---------|---------|--------------------------|
| F-SI-101 | Console 提案卡（唯讀鏡像＋既有簽核硬閘） | 掌舵者要求在 Console 內審提案，或 CLI 卡的 digest 綁定在實際使用中被誤用（附 sid 與 PROP-ID） |
| F-SI-102 | 授權代決（主控在書面授權下代為核准 D 類） | 掌舵者書面明示授權，或掌舵者回報來不及審（附待決 PROP-ID 清單） |
| F-SI-103 | 機器可讀帳本（jsonl 等）取代 Markdown 表 | 量測腳本解析 Markdown 表連續出現誤判（附列座標），或同一運轉需處理的列數使人工核對不可行 |
| F-SI-104 | harness 整體 diff 提案（playbook 以外的 harness 元件） | 掌舵者要求以提案方式改 playbook 以外的 harness 元件，或同型 harness 缺陷第二次復發（DP-12 的凍結快照評估管線現無） |

**🔴 人機協作確認點**：[ ] MVP／範圍定義清晰　[ ] 優先級合理　[ ] 範圍外項目已確認

## 📊 4. 商業需求分析 (Business Requirements)
> Brownfield 內部模組：不金額化，成本以額度與人審表達。

### 4.1 投資報酬分析
**成本項目（上界）**：掌舵者審閱（每次運轉 ≤ `MAX_PROPOSALS_PER_RUN` 張卡；不審＝不變，FR-SI-10、12）；子代理額度（受 `--pace` 與額度門檻節制、扇出前現查、百分比不複寫，NFR-SI-07）；沙盒與驗證算力（每提案宣告預算、超界收 verdict，NFR-SI-01）；帳本維護（每列 ≤700 bytes、活躍帳本有上限與歸檔，NFR-SI-08）。

**預期收益**：以 §1.3 症狀指標表達，不換算金額。**ROI**：不適用——價值主張被反證時依 §1.1 退場。

### 4.2 競爭分析（替代方案）
| 替代方案 | 優勢 | 劣勢 | 我們的差異化 |
|---------|------|------|-------------|
| 現行人工流程（缺陷帳本＋記憶檔＋掌舵者記憶） | 零新增機制 | 復發靠人記得；記憶無退役；無冷卻 | 把「觀察→提案→閘」結構化，保留人工 K=1 |
| 引擎內建演化（EvolutionPlugin） | 已有提案管線與計數上限 | 只涵蓋 Playbook；無 held-out；有 `REVISE_EVALUATOR` 型 | 統一 PROP 物件；評估器隔離；評估器變更不受理 |
| 論文式全自動自我改進（S-17、S-18、S-19） | 在機器可驗證領域有進步 | 治理工件沒有機器可驗訊號；憲法禁止自動採納；有自評偏誤與目標玩弄風險（S-17 附錄 H） | 只取「文字工件＋外部訊號重跑」，採納一律人工 |

## 💡 5. 功能性需求 (Functional Requirements)
> 📋 **ID 命名規範**: `FR-SI-NN`＝Feature ID 的模組前綴形態（先例：`docs/01_requirements/Agent_ConsoleUI_PRD.md` 的 `FR-SEC-03`、PRD v2.1 的 `F-SBR-001`）；`AC-SI-NN-Y`、`US-SI-NN`、`NFR-SI-NN` 同；觀察／提案／決定 ID 見 §5.1。

**閱讀說明**
- 每條 FR 標〔階段｜接既有／新建／既有缺口收斂〕。工件類別碼：**M**＝記憶條目（Claude Code 記憶檔的新增／修改／刪除；AutoClaude KB／偏好條目僅退役或合併提案）、**P**＝Playbook 片段、**R**＝SDD 規則草案（`trust_level: proposed`）、**D**＝非治理文件 diff。不可進化面（NFR-SI-02-1）一律走轉交（FR-SI-07）。
- 座標縮寫：「禁令 N」＝`AISDLC_SDD/CLAUDE.md` Rule 9〈絕對禁令〉第 N 條（位於該檔第 314＋N 行）；「C-NN」＝SOP Part I S1 約束表；「守衛面准入」＝根 `CLAUDE.md`〈守衛面准入（R197 裁決：量、不挖）〉；「鐵律 N」＝根 `CLAUDE.md`〈Windows 側單一載具原則〉。
- 數值參數一律標「初值（未校準）」：有既有同類上限者附座標，無先例者明標「無先例」；調整屬不可進化面（掌舵者核准）；參數 SSOT 建立後以 SSOT 為準，本文不再複寫（根 `CLAUDE.md`「數字現查」紀律）。
- **運轉**＝由啟動事件起、到該次各提案皆落入終態止的一次迴圈執行；不是日曆週期。

### 5.1 資料模型定稿（FR-SI-01、08、12 共用）
存放形態由 SD 棒決定；P0 現行載體＝`docs/06_quality/SelfImproving_Observation_Ledger.md` 的 Markdown 表（8 欄）加第 9 欄「標記」，欄位語意不因載體改變。

#### 5.1.1 觀察記錄（`OBS-SI-NNN`）
| 欄位 | 口徑 | 必填 | 規則 |
|------|------|------|------|
| ID | `OBS-SI-NNN`（≥3 位流水號、遞增、不重用、不改號；歸檔不改 ID） | 必 | 帳本內唯一；跨檔引用須指向存在的列（AC-SI-04-1） |
| 時間 | 發現時點，本機時間且帶 UTC offset（例 `2026-10-19 02:30 +08:00`）；歷時型另記 `span=<起>～<迄>` | 必 | 不得為不帶 offset 的本地時間（鐵律三 naive 時間戳同型） |
| 情境 | 視窗・代理・FSM 階段 | 必 | 一句 |
| 症狀 | 一句可觀測事實（不含推論） | 必 | 一句 |
| 證據座標 | 檔案:行／指令＋rc／sid＋seq／帳本列 ID，≥1 個 | 必 | 無座標不入帳；只存座標，不存原始輸出全文 |
| 分類 | `process`／`bug`／`tooling`／`doc`／`decision` | 必 | 單選 |
| 嚴重度 | P1～P4（口徑見下） | 必 | 兩套口徑不得混用 |
| 處置 | 枚舉見下 | 必 | 不得空白或「之後再看」；唯一可原地改寫的欄位，且只能由 `open` 轉為終值一次 |
| 標記（第 9 欄；key=value，`;` 分隔） | `面`＝守衛／產品／文件／流程；`暴露`＝a／b／c／無（`面=守衛` 時必填）；`來源`＝人／代理／工具／逐字稿／帳本（`外部衍生=是` 見 FR-SI-02）；`回報者`＝角色標籤；`根因`＝根因鍵（FR-SI-06）；`rel`＝關聯列 ID；`reopens`＝被再現的已結列 ID；`orig`＝遷移前處置原文（逐字） | 條件 | 加此欄後仍 ≤ `ROW_MAX_BYTES`（700 bytes，先例 `tools/lib/defect_ledger_index.py:545`）；超長內容搬附註檔並留座標 |

**嚴重度口徑（兩套，依 `面` 擇一）**：
- `面≠守衛`（產品／文件／流程）：P1＝走不通、鎖死、資料分裂或已造成不實結案宣稱；P2＝須手動繞過、文件自相矛盾、結案不成立或終點設計有結構漏洞；P3＝文字／可用性；P4＝理論洞（構造性、無暴露證據）。座標：`docs/04_planning/AutoSDD_improving_116.md` §3 標題列；範本〈審查閉環的終止〉（`AutoSDD_Iteration_Prompt_Template.md`:371–375）。
- `面=守衛`：逐字引 `docs/06_quality/FiveQuestion_Audit_Protocol/severity.md`（P2 須有暴露證據 a／b／c 三取一；無暴露證據者一律 P4，入理論洞清單、不立輪、不同輪修）。

**處置枚舉**：`open`（唯一暫態）／`fixed@<sha>`／`DEF-<id>`（升級為缺陷列，該列須存在）／`deferred`（附一句可觀測再開症狀）／`retired`（附依據座標）／`decided`（附裁決者與一句裁決）／`merged@OBS-SI-NNN`／`proposed@PROP-SI-NNN`（已轉提案，終態看該 PROP）。三分類對映範本〈休眠判準〉#3：立案＝`DEF-`、延後＝`deferred`、退役＝`retired`（`AutoSDD_Iteration_Prompt_Template.md`:344–350）。

#### 5.1.2 提案（`PROP-SI-NNN`；先例：觀察帳本處置欄已出現 PROP-SI-001／002）
| 欄位 | 內容 |
|------|------|
| id／state | `PROP-SI-NNN`／見下方狀態機 |
| sources | 來源 OBS／DEF ID（≥1） |
| attribution | (種類, 座標) 清單；不含任何自評分數 |
| cls／action | M／P／R／D × add／modify／delete／retire；另有 `evaluator-change`、`loop-self` 兩類標記（不受理，只轉交） |
| target／diff／digest／touch | 目標座標；增量 delta；內容摘要（演算法由 SD 定，核准綁定此值）；新增／刪除行數與觸及比例 |
| budget／verify_plan | 回合・牆鐘・token（零扇出）；提案者建議的可重跑探針、基線症狀預期、突變規格（僅供審查者參考；判定用的評估指令與 held-out 由提案者以外角色凍結，FR-SI-20） |
| rollback／retire_when／reopen_symptom | 一個動作的回滾配方；各一句可觀測條件 |
| proposer／reviewer／route | 角色標籤（reviewer≠proposer）；`loop`／`handoff:<通道>` |

**狀態機（唯一合法轉移）**：`proposed → approved｜rejected｜returned｜handed-off`；`returned → proposed`（修訂 ≤ `MAX_REVISIONS`，超限＝rejected）；`approved → sandboxed → verified`（verdict＝PASS／FAIL／NE）；`verified[PASS] → promoted｜rejected`（人決定不晉升，入冷卻）；`verified[NE] → promoted｜rejected`（promoted 須 `unverified_ack`）；`verified[FAIL] → returned｜rejected`；`promoted → measuring → closed`（clean／recurred／rolled-back）；`closed → retired`（退役提案經閘）。

#### 5.1.3 決定（`DEC-SI-NNN`）
`prop`（PROP ID）；`kind`＝approve／reject／return／promote／decline-promote／rollback／unblock／resume／ack-handoff；`decider`（掌舵者；MVP 不開放代決）；`quote`（掌舵者原句與逐字稿座標 sid＋seq）；`time`（帶 offset）；`digest`（綁定的卡面摘要）；`reason_class`（證據不足／風險過高／工件類別錯／已被涵蓋／範圍外／卡面不清／未說明）＋一句 `reason`；`flags`（例 `unverified_ack`）。

### 5.2 核心功能詳述
#### FG-A 觀察擷取（P0）
##### FR-SI-01 觀察記錄資料模型（欄位定稿）〔P0｜接既有＋定稿〕
**追溯**：DP-08；既有：`docs/06_quality/SelfImproving_Observation_Ledger.md`（欄位暫定版）、`AutoSDD_Defect_Log.md` 列體例。｜**憲法對照**：守衛面准入（`暴露` 欄）；鐵律三（時間欄帶 offset）。
- **AC-SI-01-1** Given 一筆新觀察 When 寫入帳本 Then 必填欄（ID／時間／情境／症狀／證據座標／分類／嚴重度／處置）皆有值、證據座標 ≥1 個可定位、時間帶 UTC offset；缺任一欄者被檢查器判不合規並拒收。
- **AC-SI-01-2** Given `面=守衛` 的列 When 嚴重度標 P1／P2 Then `暴露` 必為 a／b／c 之一且附座標，否則降為 P4 並入理論洞清單；`面≠守衛` 者依非守衛口徑判級。
- **AC-SI-01-3** Given 既有各列（寫稿時 OBS-SI-001～014，帳本現查）When 遷移到定稿欄位 Then ID 不變、處置原文逐字留 `orig=`、處置值落入枚舉、遷移後無「之後再看」類字樣（訂正協議：禁止靜默覆寫）。
##### FR-SI-02 觀察來源標記與外部衍生內容隔離〔P0｜新建〕
**追溯**：DP-09、DP-08；既有：無（記憶「依寫入來源過濾」本輪未見，SOP II-6）。｜**憲法對照**：禁令 26（外聯須 OPEN-X.x）；守衛面准入。
- **AC-SI-02-1** Given 觀察內容源自網頁、第三方檔案或工具輸出中的內嵌指示 When 入帳 Then `外部衍生=是`，且該列不得單獨充當 M 類或 R 類提案的證據；須另有 ≥1 個內部來源（本 repo 檔案、指令 rc、掌舵者回報）佐證。
- **AC-SI-02-2** Given 任一觀察 When 入帳 Then `來源` 與 `回報者` 皆有值；觀察本身不自動啟動任何行為（觀察≠記憶，不得直接寫入記憶或規則）。
##### FR-SI-03 迴圈只由事件啟動〔P0｜接既有〕
**追溯**：既有 C-12（範本〈🏁〉T1～T4：`AutoSDD_Iteration_Prompt_Template.md`:352–358；五問協定 S1～S6：`FiveQuestion_Audit_Protocol/README.md`:67–76）；DP-06。｜**憲法對照**：C-12、C-13。
- **AC-SI-03-1** Given 迴圈任一階段 When 檢視啟動條件 Then 僅有：(a) 掌舵者指令；(b) 同一症狀第二次被記入觀察（經審查者確認相同）；(c) 缺陷帳本新立 P≤2 未結列；(d) 已採納工件的再開症狀命中；(e) 容量事件（FR-SI-27）。不存在日曆、版本號、覆蓋度門檻、「每 N 輪」型觸發。
- **AC-SI-03-2** Given 某次運轉觀察零筆或零提案 When 判定狀態 Then 記為「無事件」而非「通過」；任何成效宣稱仍須指向症狀指標（§1.3）。
- **AC-SI-03-3** Given 本迴圈產出數量 When 評估是否再開 `AutoSDD_improving_NN` Then 產出數量不構成理由（再開僅依範本〈🏁〉T1～T4）。
##### FR-SI-04 觀察與缺陷帳本分工、引用完整性與原地改寫偵測〔P0｜接既有＋新建（檢查）〕
**追溯**：DP-08；既有：`AutoSDD_Defect_Log.md` 治理、`tools/check_defect_log_crossref.py`、`tools/tests/test_defect_id_reference_integrity.py`（`_REF_RE` 現含 DEF-101／200 兩族）。｜**憲法對照**：鐵律四。
- **AC-SI-04-1** Given 處置為 `DEF-<id>` 或任何 `OBS-SI-`／`PROP-SI-`／`DEC-SI-` 跨檔引用 When 檢查 Then 被引列存在（含 archive）；引用不存在的 ID＝不合規。
- **AC-SI-04-2** Given 符合缺陷帳本收錄定義的真缺陷 When 觀察入帳 Then 處置須為 `DEF-<id>`（OBS 只留觀察與座標，不取代 DEF 帳本）。
- **AC-SI-04-3** Given 已存在的列 When 量測腳本比對版本歷史 Then 除「處置欄 open→終值一次」外的原地改寫被標 `ROW-MUTATED` 並要求掌舵者過目；更正一律追加「更正列」（`rel=corrects:OBS-SI-NNN`）。

#### FG-B 歸因（P1）
##### FR-SI-05 歸因映射〔P1｜接既有（唯讀量測器）＋新建（映射格式）〕
**追溯**：DP-08；既有：`tools/probe/misstep_attribution.py`（關鍵詞分群、只量不閘）、SDD `test-failure-analyzer` skill（失敗 TC→AC／US／F 映射）、`spec_localizer.py`。｜**憲法對照**：禁令 13（localizer 不得自動改 spec）。
- **AC-SI-05-1** Given 一個觀察或觀察群 When 歸因 Then 產出 `attribution` 清單，每項為（種類∈DEF／OBS／RULE／PLAYBOOK_STEP／DOC／MEMORY_ENTRY／NONE，座標）；NONE 必須寫明「無法歸因」，不得以猜測補位。
- **AC-SI-05-2** Given 歸因輸出 When 檢視欄位 Then 不含自評分數或信心數值；歸因不修改被指向的任何檔案。
##### FR-SI-06 根因鍵與復發連結（人審確認）〔P1｜新建〕
**追溯**：DP-10；既有：缺陷帳本「再開症狀」文字（寫在分流去向／狀態欄，非獨立欄）。｜**憲法對照**：C-13；守衛面准入。
- **AC-SI-06-1** Given 歸因完成 When 指派根因鍵（`<面>/<機制>`，小寫連字號） Then 鍵由歸因者提出、審查者（≠歸因者）確認；鍵被事後更改的次數記入資訊欄。
- **AC-SI-06-2** Given 新列疑似為已結列所防症狀的再現 When 量測腳本列候選（依 `reopens:`、同證據座標檔案路徑∩同分類、現象欄「再開症狀…命中」字樣） Then 候選須經審查者確認才計入 M1；未確認者標「候選」而不計數。
##### FR-SI-07 不可進化面的歸因出口（轉交，不套用）〔P1｜新建（流程）；零新增守衛碼〕
**追溯**：DP-11、DP-12；既有：守衛面准入；治理檔唯讀守衛（`.claude/hooks/block_destructive_git.py`:1423–1472，僅 `AUTOSDD_UNATTENDED` 下阻斷）。｜**憲法對照**：守衛面准入；禁令 22～25 末項；PRD v2.1 §15.5 紅線 10。
- **AC-SI-07-1** Given 歸因目標落在不可進化面（NFR-SI-02-1 清單） When 產生提案 Then `route=handoff:<既有通道>`（DEF／R 系列／T1／PRD 修訂擇一），卡面標「僅轉交，本迴圈不套用」，迴圈對該目標零寫入（例：OBS-SI-005 的候選 PROP-SI-001 屬守衛面、OBS-SI-012 的候選 PROP-SI-002 屬根 `CLAUDE.md`，皆走轉交）。
- **AC-SI-07-2** Given 轉交目標屬守衛面且無暴露證據（`severity.md`〈暴露度〉三取一） When 轉交 Then 一律登記為理論洞（P4）、不立案修復；本 PRD 不新增任何守衛碼、鎖或 hook。

#### FG-C 提案生成（P1）
##### FR-SI-08 提案物件（只產 proposed）與狀態機〔P1｜接既有＋新建（統一物件）〕
**追溯**：DP-04、DP-02、DP-07；既有：`EvolutionPlugin` 回傳 `MutationProposal`（`AutoClaude/autoclaude/plugins/evolution_plugin.py`:113–132）、`translation_learner_plugin.py`（只產 proposed）、SDD `slv_generator.py`（`trust_level: proposed`、`reviewed_by: null`）、`spec_patch_proposer.py`。｜**憲法對照**：禁令 10、11、12。
- **AC-SI-08-1** Given 任一來源（歸因者、既有 EvolutionPlugin、SLV／SPEC-PATCH 管線） When 產生改進 Then 一律登記為 `PROP-SI-NNN`（§5.1.2 欄位齊備）、初始狀態 `proposed`；R 類 PROP 的 target＝既有管線產出的草案座標（不複製、不改管線）；產生者對正式面無寫入權。
- **AC-SI-08-2** Given PROP When 狀態轉移 Then 僅允許 §5.1.2 狀態機所列轉移；任何跳級（例：`proposed`→`promoted`）被拒並記 OBS。
- **AC-SI-08-3** Given R 類提案 When 入庫 Then `trust_level: proposed` 且不得阻塞 SCG（禁令 10）。
##### FR-SI-09 提案輸入限定、抽象化與增量 delta〔P1｜新建〕
**追溯**：DP-03、DP-08、DP-09；既有：preference 10 鍵上限（`preference_memory_plugin.py`:19）、KB 結果標籤（`knowledge_base_plugin.py`:7–10）、SDD `NoBigBangValueRewrite`（`AISDLC_SDD/CLAUDE.md`:332）。｜**憲法對照**：禁令 18。
- **AC-SI-09-1** Given 提案生成 When 取輸入 Then 輸入只能是帳本列、歸因證據座標與真實失敗軌跡的**抽象化摘要**（帶結果標籤＝失敗／成功／升級，與適用範圍），不得以原始軌跡全文充當條目。
- **AC-SI-09-2** Given 提案 diff When 受理檢查 Then 為增量 delta：觸及既有內容比例 ≤ `MAX_TOUCH_RATIO`（初值 0.2，無先例）、新增條目 ≤ `MAX_NEW_ENTRIES`（初值 3，無先例）；超界者退回拆分，整份重寫一律不受理。
- **AC-SI-09-3** Given M 類條目 When 入提案 Then 必含結果標籤、適用範圍、來源 OBS、退役條件（FR-SI-25）四欄，缺欄不受理。
##### FR-SI-10 提案數量、預算與不遞迴〔P1｜接既有＋新建〕
**追溯**：DP-06；既有：`translation_max_proposals_per_run=3`（`AutoClaude/autoclaude/utils/config.py`:226）、`max_evolutions=3`（:192）、Gap-042／048 計數器（`AutoClaude/CLAUDE.md`:200–201）、`select_proposals` 的 dedup（`core/ports/translation_learning.py`:94）。｜**憲法對照**：禁令 4、16。
- **AC-SI-10-1** Given 一次運轉 When 產生提案 Then 提案數 ≤ `MAX_PROPOSALS_PER_RUN`（初值 3，先例同上）；與待決或已核准提案同型者（artifact_class＋target＋根因鍵）不重複產生。
- **AC-SI-10-2** Given 提案者或審查者 When 執行 Then 不得再派提案者／審查者（零遞迴）；每提案宣告預算（回合、牆鐘、token），超界即停並升級人工（禁令 4）。
##### FR-SI-11 提案類別白名單與評估器變更提案不受理〔P1｜新建；接既有型別標記〕
**追溯**：DP-05、DP-12、DP-11；既有：`playbook_evolver.py`:14–16、:37（含 `REVISE_EVALUATOR`）、`evolution_plugin.py`:284–289。｜**憲法對照**：禁令 22～25 末項（meta-oracle 自演化紅線）；C-07。
- **AC-SI-11-1** Given 提案類別 When 受理 Then 僅 M／P／R／D 四類（及其退役）受理；任何改變評估器、held-out、評分權重、本迴圈預算／閘門／停機條件者標 `evaluator-change` 或 `loop-self`，走 FR-SI-07 轉交，不進採納流程。
- **AC-SI-11-2** Given 既有引擎產出 `REVISE_EVALUATOR` 型演化提案 When 迴圈接到 Then 標 `evaluator-change` 並記一筆 OBS；不得轉送沙盒或晉升。

#### FG-D 人工閘（P2；FR-SI-14 為 P1）
##### FR-SI-12 K=1 人工閘〔P2｜接既有（SDD HUMAN_PENDING／Console）＋新建（通用閘）〕
**追溯**：DP-04；既有：SDD HUMAN_PENDING 與 `rule_loader.set_maturity(reviewed_by=)`（`rule_loader.py`:309）、`PlaybookRunner._evolution_signoff_granted`（`AutoClaude/autoclaude/execution/playbook_runner.py`:299–322）、AgentConsole 簽核硬閘（`AgentConsole/CLAUDE.md`:15）。｜**憲法對照**：禁令 11、12、13；C-15。
- **AC-SI-12-1** Given 一張 PROP 卡 When 掌舵者回覆 Then 僅「核准／否決／退回＋PROP ID」構成決定，且綁定該 PROP 最近一次送達之卡面 digest（卡面與 digest 一併留存）；DEC 須附掌舵者原句與其逐字稿座標（sid＋seq），使「主控偽造核准」可被事後稽核；無決定或無法解析的回覆＝預設拒絕、狀態不變。
- **AC-SI-12-2** Given 核准後 PROP 內容改變（digest 不同），或決定對應的卡面 digest ≠ 現行 digest（過期卡） When 嘗試進入沙盒 Then 核准失效、決定被拒並重新上卡。
- **AC-SI-12-3** Given 多張 PROP When 呈現 Then 逐張決定（K=1），不提供「全部核准」；核准者必須是掌舵者本人（MVP 不開放代決，附錄 C.2 #2），DEC 記 `decider`。
##### FR-SI-13 拒絕紀錄與同型冷卻〔P2｜新建；接既有（dedup、抖動防護）〕
**追溯**：DP-04、DP-10；既有：SDD 抖動防護 R-9.24.1／9.24.2（`AISDLC_SDD/AISDLC_SDD_v0.30/governance/rules/R-9.24-meta-halting-offline-experiment-phase-l.yaml`）、`select_proposals` 的 dedup。｜**憲法對照**：禁令 14。
- **AC-SI-13-1** Given 否決或退回 When 記 DEC Then 必含 `reason_class` 與一句理由；「未說明」亦可，但採最嚴冷卻。
- **AC-SI-13-2** Given 某型（artifact_class＋target＋〔根因鍵相同或證據座標集合有交集〕）剛被否決 When 同型提案再生成 Then 被擋（冷卻中），直到再提資格事件：(a) 掌舵者明示解除（DEC kind=unblock）；(b) 否決後新立、同根因鍵、且證據座標與原提案證據集不相交的觀察或缺陷列 ≥1 筆；再提案須附「逐項回應否決理由」。
- **AC-SI-13-3** Given 冷卻被繞過 When 量測 M4 Then 計數 >0 並記 OBS（分類 `bug`）。
##### FR-SI-14 提案卡由確定性轉換產出〔P1｜新建；類比既有 R-9.37〕
**追溯**：DP-04、DP-10；既有類比：`recursion_topology_view` 的 `verify_topology_consistency`（`AISDLC_SDD/CLAUDE.md`:341 禁令 27，渲染須與來源物件同構）。｜**憲法對照**：禁令 27（可審批性不得靠簡化呈現繞過）。
- **AC-SI-14-1** Given PROP When 產卡 Then 卡面核心三句（症狀／改動／風險與回滾）、diff、digest、證據座標與預算皆由 PROP 欄位確定性轉換而來；提案者自由撰寫的摘要不得取代 diff 本文。
- **AC-SI-14-2** Given 一張卡 When 反解析卡面欄位 Then 與 PROP 物件逐欄一致（digest、diff 行數、驗證狀態）；不一致的卡不得送達掌舵者。
- **AC-SI-14-3** Given 一張卡 When 檢視版面 Then 核心區 ≤ 12 行、每項 ≤ 1 句；完整 diff 與證據以座標附於卡尾（§7.3）。

#### FG-E 套用（P2；僅沙盒，最後一步晉升為人工動作）
##### FR-SI-15 沙盒套用（正式面零變更）〔P2｜接既有＋新建〕
**追溯**：DP-04、DP-07、DP-11；既有：`PlaybookEvolver.apply_evolution` 寫 `evolved_<原檔名>.yaml` 而非原地改（`AutoClaude/autoclaude/evolution/playbook_evolver.py`:302）、SDD `sandbox_runner.py`／R-9.20.1。｜**憲法對照**：鐵律五；根 `CLAUDE.md`〈權限姿態〉。
- **AC-SI-15-1** Given 已核准 PROP When 套用 Then 只作用於隔離副本（沙盒；例：git worktree 或等價隔離）；沙盒位置不得改變正式面的掃描與棘輪量測結果；套用前後正式面 `git status --porcelain` 與 HEAD 逐字相同。
- **AC-SI-15-2** Given 沙盒建立與清理 When 執行 Then 不使用鐵律五擋下的毀滅性 git 形態（`stash`、`reset --hard`、`checkout --`、`clean` 等）；清理＝丟棄副本即回原狀。
- **AC-SI-15-3** Given 遇 R-9.6 擋寫（路徑子字串含 `docs/01～03` 且視窗綁定 IMPLEMENTATION 中功能鍵）或 harness 分類器拒絕（`.claude/**`） When 套用 Then 不得以改派子代理或換路徑繞過；改由符合條件的視窗處理，或走轉交（FR-SI-07）。
##### FR-SI-16 晉升為人工動作與回滾配方〔P2｜新建；接既有（git、set_maturity）〕
**追溯**：DP-04、DP-07、DP-02；既有：git、`rule_loader.set_maturity(reviewed_by=)`、`EvolutionMetadata`（`playbook_evolver.py`:274–298 的 generation／mutation_log）。｜**憲法對照**：禁令 11、12。
- **AC-SI-16-1** Given 驗證 verdict＝PASS 且 digest 與核准時相同 When 掌舵者下達晉升指令（DEC 附其原句與 sid＋seq） Then 才合入正式面；verdict 為 FAIL、或 NE 而無 `unverified_ack`（FR-SI-19）、或 digest 不同者，晉升被拒。
- **AC-SI-16-2** Given 每筆 PROP When 受理 Then 必附一個動作的回滾配方（git revert、刪條目＋還原前置快照、`set_maturity` 退回之一）；回滾配方在驗證階段乾跑通過才可晉升（M 類的記憶目錄不在版本控制內，必須以前置快照作回滾，不得假設 git revert 可用）。
- **AC-SI-16-3** Given 晉升完成 When 記 DEC Then 含晉升者、時間（帶 offset）、合入 sha 或快照座標。
##### FR-SI-17 套用預算、停機與不自動恢復〔P2｜接既有〕
**追溯**：DP-06；既有：R-9.5／R-9.14（ESCALATION 後不自動恢復）、`step_timeout_seconds`（`AutoClaude/autoclaude/utils/config.py`:188）。｜**憲法對照**：禁令 4、6、7、26。
- **AC-SI-17-1** Given 沙盒套用或驗證超出宣告預算 When 超界 Then 立即停止並收一個 verdict（FAIL 或 NE），不等沙箱（禁令 26：沙箱 hang 收 verdict），並升級人工。
- **AC-SI-17-2** Given 進入 ESCALATION When 恢復 Then 僅能由人工恢復，迴圈不得自動恢復（禁令 6、7）。

#### FG-F 驗證（P2）
##### FR-SI-18 審查者≠提案者；外部訊號為主依據〔P2｜接既有＋新建〕
**追溯**：DP-01、DP-05；既有：R-9.20.3（Generator／Evaluator 獨立 context；`governance/rules/R-9.20-phase-h-gae.yaml`）、`evaluator_command` 二次驗證（`AutoClaude/CLAUDE.md`:175、239）、鐵律七檢查表第 3 點（複審唯讀）。｜**憲法對照**：禁令 17；鐵律七。
- **AC-SI-18-1** Given 一張 PROP When 驗證 Then 審查者與提案者為不同代理實例與不同 context，審查者全程唯讀、不得自起背景長任務。
- **AC-SI-18-2** Given 判定 When 記 PASS Then 主依據必為外部可重跑訊號（指令 rc、測試、重放結果）；LLM 審查意見只作次級，且不得單獨把 FAIL 改成 PASS（同家族模型的審查獨立性有限，見 §10 自評偏誤列）。
##### FR-SI-19 對照／突變與三態判定〔P2｜新建〕
**追溯**：DP-01、DP-10；既有：五問協定三態 PASS／FAIL／NOT-EVALUABLE（`FiveQuestion_Audit_Protocol/README.md`:48–62）、SDD `counterfactual_replay.py`（命中率僅為證據）、整合輪 116 QA 以 `git archive` 匯出 commit 量突變（`docs/04_planning/AutoSDD_improving_116.md` §9.1）。｜**憲法對照**：禁令 14、26；C-13。
- **AC-SI-19-1** Given 驗證計畫 When 執行 Then 先對照：基線（未套用）須重現症狀（RED），套用後症狀消失（GREEN），再突變（弱化或移除提案內容）後症狀須回來（RED）；三者缺一＝驗證無鑑別力＝NE。
- **AC-SI-19-2** Given 結果 When 判定 Then 僅三態 PASS／FAIL／NE（NOT-EVALUABLE）；NE 不得視為 PASS，晉升須掌舵者 `unverified_ack`，且該 PROP 在指標中另列「未驗採納」；M／D 類無可執行症狀探針者預設 NE。
- **AC-SI-19-3** Given R 類重放 When 命中率高 Then 僅為證據，不得據此自動核准（禁令 14）。
##### FR-SI-20 評估器隔離與 held-out 分割〔P2｜新建（通用化既有 SDD 機制）〕
**追溯**：DP-05；既有：R-9.20.3、R-9.27～R-9.29 held-out 對抗分離（`AISDLC_SDD/CLAUDE.md`:331～333）、`AISDLC_SDD/AISDLC_SDD_v0.30/knowledge/held-out-corpus/`。｜**憲法對照**：禁令 17、18、19；C-05、C-07。
- **AC-SI-20-1** Given 一個驗證計畫 When 於歸因完成、提案生成之前 Then 評估集（held-out 觀察／缺陷列分割與評估指令）由提案者以外的角色先行凍結；提案者 context 不含其內容，亦無寫入權。
- **AC-SI-20-2** Given 評估集 When 規模 < `MIN_HELDOUT`（初值 5；先例：`SDD_REPLAY_MAX_CASES` clamp 下限 5、`params.json` 的 `q1b_min_n`＝5） Then 判 NE，不得以小樣本宣稱有效。
- **AC-SI-20-3** Given 任一角色 When 嘗試修改評估指令、評分權重、held-out 或量測腳本 Then 視為 `evaluator-change`（FR-SI-11）；僅掌舵者經 T1 可改。
##### FR-SI-21 驗證證據逐字入帳〔P2｜接既有（鐵律四）〕
**追溯**：DP-10；既有：`.claude/hooks/check_claim_provenance.py`（Stop 事件，只出聲不阻斷）。｜**憲法對照**：鐵律四；C-14。
- **AC-SI-21-1** Given 驗證記錄 When 入帳 Then 含執行者、時間（帶 offset）、指令、rc（先存變數再讀）、輸出摘錄座標、母體／樣本數；轉述他包者標 `[他包回報]`，主控親跑後才升格為「已驗證」。
- **AC-SI-21-2** Given 「已驗證／已達標」宣稱 When 檢視 Then 附當回合真跑輸出；貼不出者改寫為「未驗證」。

#### FG-G 量測（P3）
##### FR-SI-22 症狀型指標量測（確定性）〔P3｜新建；類比既有量測器〕
**追溯**：DP-10；既有：`tools/probe/audit_session.py`（只量不閘，檔頭:8–14；印判準指紋，檔頭:31–32）、`tools/probe/misstep_attribution.py`。｜**憲法對照**：C-13；根 `CLAUDE.md` 12-Rule Rule 5（確定性轉換不用模型）。
- **AC-SI-22-1** Given 帳本與 git 歷史 When 跑量測腳本 Then 輸出 M1～M5 的值、樣本數、窗定義與「判準指紋」；n < `W_MIN`（初值 5，先例 `q1b_min_n`／`q2_min_n`＝5）者印 NOT-EVALUABLE；腳本不呼叫模型。
- **AC-SI-22-2** Given 輸出 When 呈現 Then 資訊欄（提案數、決定分佈、OBS 筆數、`closed-by-decision` 數、未驗採納數）與成功指標分區；指標定義變更必改指紋，不同指紋的數字不得並列；量測腳本不接任何閘門。
- **AC-SI-22-3** Given 提案者 When 運作 Then 看不到指標目標值與計算細節（迴圈層指標只對掌舵者與量測者呈現）。
##### FR-SI-23 採納後量測窗與回滾偵測〔P3｜新建〕
**追溯**：DP-04、DP-10；既有：缺陷帳本「再開症狀」體例。｜**憲法對照**：C-12。
- **AC-SI-23-1** Given 一筆 promoted PROP When 開量測窗 Then 窗以事件界定：自晉升起，到「同面新立列累計 `W_OPP`（初值 5，無先例）筆」或「出現再現／回滾」先到者關閉；窗關閉結果記 `clean`／`recurred`／`rolled-back`。
- **AC-SI-23-2** Given 窗內偵測到再現 When 出聲 Then 產生回滾提案卡（不自動回滾）；回滾動作由掌舵者執行，記 DEC。
##### FR-SI-24 劣化暫停（邊際報酬遞減）〔P3｜新建〕
**追溯**：DP-06；既有：SDD `SDD_META_CHURN_MAX`（R-9.24.1）、ESCALATION 不自動恢復（R-9.5）。｜**憲法對照**：禁令 6、7、14。
- **AC-SI-24-1** Given 連續 `STOP_AFTER_BAD`（初值 2，無先例）筆採納於其量測窗內 recurred 或 rolled-back When 判定 Then 迴圈進入 SUSPENDED：不再受理新提案，僅掌舵者可恢復（DEC kind=resume）。
- **AC-SI-24-2** Given SUSPENDED When 觀察 Then 觀察擷取（FR-SI-01）照常，僅提案以後各階段暫停。

#### FG-H 退役（P3）
##### FR-SI-25 退役條件與退役提案（人工）〔P3｜接既有（scaffold_gc、set_maturity）＋新建（通用）〕
**追溯**：DP-02、DP-03；既有：`scaffold_gc.py`（GC 只提議、永不自動退役，檔頭:10–11）、`scaffold_ceiling_detector.py`（advisory）、`rule_loader.set_maturity(reviewed_by=)`。｜**憲法對照**：禁令 11。
- **AC-SI-25-1** Given 任一已採納工件 When 受理 Then 帶 `retire_when`（一句可觀測條件）與 `reopen_symptom`（一句可觀測再開症狀，不得含輪號、日期、「待排程」字樣）。
- **AC-SI-25-2** Given 退役 When 執行 Then 退役本身是 `action=retire` 的 PROP、走同一 K=1 閘；SDD 規則退役必經 `set_maturity(reviewed_by=)`；系統只提議、不自動退役。
##### FR-SI-26 抖動防護（add↔retire）〔P3｜接既有（SDD）＋新建（其他面）〕
**追溯**：DP-04；既有：`tools/fsm_runtime/meta_halt/meta_halt_monitor.py`、R-9.24.1／9.24.2（`CHURN_MAX` 預設 2；退役棘輪）。｜**憲法對照**：禁令 14。
- **AC-SI-26-1** Given 同一（target, 根因鍵）的 add→retire→re-add 循環 When 次數 > `CHURN_MAX`（初值 2，先例 `SDD_META_CHURN_MAX`） Then 不再受理並升級人工。
- **AC-SI-26-2** Given 已退役工件被再提 When 受理 Then 須附 capability-delta 證據＝退役後新出現、與原證據集不相交的症狀證據；SDD 規則面沿用 `meta_halt_monitor` 把關，其他面由本迴圈檢查。
##### FR-SI-27 容量事件觸發退役／合併提案〔P3｜新建；接既有上限〕
**追溯**：DP-03、DP-09；既有：S-08（`MEMORY.md` 前 200 行或 25KB）、`_MAX_ENTRIES=1000`（`AutoClaude/autoclaude/utils/knowledge_base.py`:31）、preference 10 鍵（`preference_memory_plugin.py`:19）。｜**憲法對照**：C-12（事件驅動、無日曆）。
- **AC-SI-27-1** Given 有上限的儲存或載入面（記憶索引、KB、偏好注入） When 用量達其上限的 `CAP_FRAC`（初值 0.9，無先例；`MEMORY.md` 寫稿時約為上限的 89%～91%，25KB 換算未查證） Then 產生退役／合併提案清單（只提議、不自動刪除）。
- **AC-SI-27-2** Given 索引檔實際大小超過載入上限（位元組或行數）而仍有條目排在上限之後 When 檢查 Then 視為「截斷風險」缺陷入帳（面＝流程），因為「被截斷」與「已退役」的表徵不同。

#### FG-I 既有缺口收斂／元層
##### FR-SI-28 「演化只提案不套用」由宣稱升為可重跑檢查〔P1｜既有缺口收斂；零新增守衛碼〕
**追溯**：DP-04、DP-12；既有：`AutoClaude/CLAUDE.md`:191、`evolution_plugin.py`:9–19（`ON_EVOLUTION_APPLY` 為 NO-OP）、DEF-13-004 `evolution_approver`（`playbook_runner.py`:299–322）。｜**憲法對照**：禁令 12；守衛面准入（無暴露證據⇒取最小形態）。
- **AC-SI-28-1** Given AutoClaude 原始碼 When 靜態可達性檢查 Then 可證 Kernel 正式路徑不呼叫 `apply_evolution`、且 `PlaybookRunner` 無生產建構點（把 `AutoClaude/CLAUDE.md`:191 的文字宣稱變成可重跑檢查，取代僅靠「沒有建構點」）；現有呼叫點（`execution/steps_orchestrator/_escalation_handler.py`:111／208／263、`execution/mutation_applier/_complex_mutations.py`:114）列為受檢清單。
- **AC-SI-28-2** Given `require_evolution_signoff` 預設 False（`utils/config.py`:194，演化版自動重載放行）而文件宣稱「只提案不套用」 When 對照 Then 二者須一致：或改預設為 fail-closed，或文件改述為「預設放行但無生產建構點」；方向由掌舵者裁決（附錄 C.2 #4），兩個方向都須保持既有測試零退化。
- **AC-SI-28-3** Given 任何路徑出現生產建構 `PlaybookRunner`（OBS-SI-010 再開症狀） When 發生 Then 立即升為缺陷列，並走 FR-SI-12 的人工閘（此時暴露證據成立）。
##### FR-SI-29 迴圈自我觀察（dogfood；T1 原文第 3、4 點）〔P0｜新建（流程）〕
**追溯**：DP-08、DP-12；既有：T1 原文第 3、4 點、`SelfImproving_Observation_Ledger.md`。｜**憲法對照**：C-12。
- **AC-SI-29-1** Given 開發或運轉本迴圈時發現流程不當或 BUG When 發現當下 Then 一律入觀察帳本（一句症狀＋一個座標），真缺陷升 DEF；子代理以文字交卷的「流程摩擦」節為入口（OBS-SI-004）。
- **AC-SI-29-2** Given 對迴圈本身預算／閘門／停機條件／指標定義的改進 When 提出 Then 一律標 `loop-self` 並轉交（FR-SI-07），僅經掌舵者 T1／PRD 修訂；本迴圈不得提案修改自己（DP-12；禁令 20～25）。

**🔴 人機協作確認點**（§5 整體）：[ ] FR／AC 與 T1 原文五點一致（§14）　[ ] 每條 FR 皆有 DP 或既有機制追溯（附錄 A）　[ ] 每條 FR 皆有憲法對照且無違反（附錄 B）

## 🔧 6. 非功能性需求 (Non-Functional Requirements)
> 📋 **ID 命名規範**: `NFR-SI-NN`，子項 `NFR-SI-NN-M`。數值皆為「初值（未校準）」，先例座標附於欄內，調整屬不可進化面。

### NFR-SI-01: 有界停機（每階段預算與停機條件）
| 階段 | 上界（初值） | 停機條件 | 超界動作 |
|------|-------------|---------|---------|
| 觀察擷取 | 純文字寫入、零扇出；單列 ≤ `ROW_MAX_BYTES`（先例 700） | 單列超長 | 拒收並要求縮寫，長內容搬附註檔留座標 |
| 歸因 | 單一歸因者；讀取面限帳本＋證據座標；不上網 | 超出任務書宣告預算 | 記 `NONE`（無法歸因），不猜 |
| 提案生成 | ≤ `MAX_PROPOSALS_PER_RUN`（3）；每提案修訂 ≤ `MAX_REVISIONS`（2；先例 `MAX_PATCH_PER_AC=2`、範本「至多二審」）；零遞迴 | 任一超界 | 停止並升級人工；修訂超限＝否決並入冷卻 |
| 人工閘 | 無逾時自動核准（預設拒絕）；待決不計時 | — | 待決提案不阻塞觀察擷取 |
| 沙盒套用 | 牆鐘與回合依提案宣告（先例 `step_timeout_seconds` 600）；零扇出 | 超界或沙箱 hang | 收 verdict（FAIL／NE），不等待（禁令 26） |
| 驗證 | 一審＋一次複驗（至多二審）；每次重跑 ≤ 2 | 超界 | 判 NE 並升級人工 |
| 量測／退役 | 量測腳本零 token；窗以事件關閉（FR-SI-23）；退役與提案共用 `MAX_PROPOSALS_PER_RUN` | — | — |
| 整體 | 劣化暫停 `STOP_AFTER_BAD`（2）；抖動 `CHURN_MAX`（2） | 觸發 | SUSPENDED／升級；僅掌舵者恢復 |

context 三段水位與額度四道門檻一律現查（`python tools/session_resume_planner.py --check`、`python tools/lib/quota_policy.py --print-env-example`），本文不複寫百分比。

### NFR-SI-02: 安全（守衛面與受保護路徑）
- **NFR-SI-02-1 不可進化面（唯一真相源）**：(i) agent 指令與憲法檔：根／`AISDLC_SDD`／`AutoClaude`／`AgentConsole` 的 `CLAUDE.md`、`maturity: active` 的 `governance/rules/R-*.yaml` 規則本體；(ii) 守衛面：`.claude/hooks/**`、`.claude/settings*.json`（含 permissions.allow）、根 `CLAUDE.md`〈守衛面准入〉所列 `tools/lib/` 檔與 `tools/session_resume_planner.py`；(iii) 評估與協定：`evaluator_command`、`knowledge/held-out-corpus/`、評分權重常數、`docs/06_quality/FiveQuestion_Audit_Protocol/`、範本〈🏁〉、量測腳本與指標定義；(iv) 迴圈自身：本 PRD、預算／閘門／停機參數、狀態機。
- **NFR-SI-02-2 受保護路徑**：`.claude/**` 屬 harness 受保護路徑（auto 模式一律交分類器，根 `CLAUDE.md`〈權限姿態〉）；子代理成品一律 staged 到 scratchpad 交主控；被拒一次走人工核准重試，不改派子代理或換路徑繞過。
- **NFR-SI-02-3 無人值守**：`AUTOSDD_UNATTENDED` 下治理檔唯讀；迴圈在無人值守下僅可執行到「提案」止；人工閘、套用、晉升必須有人；人的逃生口（`AUTOSDD_GOVWRITE_GUARD_OFF`、`AUTOSDD_GIT_GUARD_OFF`）模型碰不到，迴圈不得要求關閉任何守衛。
- **NFR-SI-02-4 無外聯與最小留存**：運轉期不開網路外聯（禁令 26：外聯須 OPEN-X.x）；證據只存座標、不存原始輸出全文（降低密鑰／PII 外洩面；日誌遮蔽先例 `AutoClaude/autoclaude/utils/redaction.py`）。
- **NFR-SI-02-5 守衛面准入的誠實劃界**：現有 `_GOV_EXACT` 僅在 `AUTOSDD_UNATTENDED` 下阻斷、僅涵蓋 Write／Edit／NotebookEdit，且不含三份 `CLAUDE.md`、`governance/rules/*.yaml`（`.claude/hooks/block_destructive_git.py`:1423–1472）；本 PRD 不為此新增守衛碼（無暴露證據⇒理論洞 P4），MVP 以流程性邊界達成：提案產物只落沙盒、晉升為人工動作、不可進化面轉交。

### NFR-SI-03: 可稽核
- **NFR-SI-03-1** 每個 PROP 可追到 OBS→歸因→PROP→DEC→套用→驗證→量測→退役；斷鏈者不得晉升。
- **NFR-SI-03-2** ID 不重用、不改號；更正以追加列；已存在列的原地改寫被標 `ROW-MUTATED`（AC-SI-04-3）。
- **NFR-SI-03-3** 每筆紀錄含執行者角色與帶 offset 的時間；驗證證據含指令、rc、母體數（FR-SI-21）；追溯完整性由確定性檢查產出（不用模型）。

### NFR-SI-04: 可逆
- **NFR-SI-04-1** M：前置快照＋刪條目；P：撤銷採納 commit 或刪 evolved 副本；R：`set_maturity` 退回或撤銷 commit；D：git revert。
- **NFR-SI-04-2** 每筆 PROP 的回滾為一個動作並於驗證階段乾跑（AC-SI-16-2）；回滾本身是人工動作（掌舵者），系統只提示（AC-SI-23-2）。

### NFR-SI-05: 反 Goodhart
- **NFR-SI-05-1** 評估器對生成器不可見：held-out 與評估指令由提案者以外角色凍結（FR-SI-20）。
- **NFR-SI-05-2** 迴圈層指標由確定性腳本產出、只對掌舵者與量測者呈現；提案者看不到目標值（AC-SI-22-3）。
- **NFR-SI-05-3** 資訊欄與成功指標分區，不用提案數、採納率、自評分數（§1.3.1）；指標定義帶判準指紋、定義變更屬不可進化面（FR-SI-22）；重放命中率只作證據、不得自動核准（禁令 14）。

### NFR-SI-06: 跨平台（Windows PowerShell／macOS）
- **NFR-SI-06-1** Windows 只用 PowerShell 工具（禁 Bash 工具）；一律絕對路徑、不裸 `cd`；讀 rc 先存變數（鐵律一、二）。
- **NFR-SI-06-2** 凡新增腳本或欄位先自問「這在另一個平台是什麼值？」（鐵律三觸發清單：時間戳 offset、路徑分隔符、console 編碼、行尾、大小寫）。
- **NFR-SI-06-3** 帳本與腳本的檔案 I/O 一律明示 UTF-8 編碼；`.md` 帳本不依賴特定行尾。
- **NFR-SI-06-4** 沙盒與背景任務不使用被擋的毀滅性 git 形態與壞等待形態（鐵律五、六）。
- **NFR-SI-06-5** macOS 未實跑的項目在驗收報告標「未驗」，不得以 Windows 結果代表。

### NFR-SI-07: Token／額度預算
- **NFR-SI-07-1** 主控 Fable 只做裁決與親驗（派工、驗收、親跑重驗）；擷取、歸因、提案、審查用子代理 Sonnet；機械性轉換與格式檢查用 haiku 或確定性腳本；子代理以文字交卷、不寫報告檔（OBS-SI-004）。
- **NFR-SI-07-2** 每次扇出前現查 `python tools/session_resume_planner.py --pace`，不得記住上次值（根 `CLAUDE.md`〈工具選型〉）。
- **NFR-SI-07-3** 預算語意＝「任務書宣告、超出必揭露」；它與根 `CLAUDE.md` 12-Rule Rule 6 字面（每任務 4,000／每 session 30,000 tokens）的關係見 OBS-SI-012（候選 PROP-SI-002，待人工閘）；裁決前本迴圈不得默默超支。
### NFR-SI-08: 容量與可讀性
- **NFR-SI-08-1** 單列 ≤ `ROW_MAX_BYTES`；活躍帳本有列數／位元組上限，超限依「歸檔不改 ID」搬遷（先例：`docs/06_quality/AutoSDD_Defect_Log_archive_*.md`）；PROP 卡核心區 ≤ 12 行（AC-SI-14-3）。

### NFR-SI-09: 失效可偵測（fail loud）
- **NFR-SI-09-1** 量不到＝NOT-EVALUABLE，不得 false-green（禁令 26；根 `CLAUDE.md` 12-Rule Rule 12）。
- **NFR-SI-09-2** 擷取通路失效可偵測：子代理交卷的「流程摩擦」項目數與入帳 OBS 數對帳（只量、不接閘門；先例 `tools/probe/audit_session.py`）。
- **NFR-SI-09-3** 迴圈任一階段失敗都留一筆 OBS（分類 `bug`），不得靜默吞掉。

**追蹤鏈**：`NFR-SI-01 → AC-SI-10-2／17-1／24-1`；`NFR-SI-02 → AC-SI-07-1／15-3`；`NFR-SI-05 → AC-SI-20-1／22-3`；`NFR-SI-09 → AC-SI-19-2／20-2`。

**🔴 人機協作確認點**：[ ] 所有 NFR 已定義 ID　[ ] 預算初值與先例座標可接受　[ ] 安全要求符合守衛面准入與受保護路徑姿態

## 🎨 7. 使用者體驗需求 (UX Requirements)
### 7.1 設計原則
- **易用性**：一卡一決定；三句話可決定核准／否決／退回；預設拒絕（不回覆＝不變）。
- **一致性**：卡面欄位順序固定；用語沿用 §13.1 詞彙表。
- **回饋機制**：每個決定回一行確認（PROP ID、決定、digest 前 8 碼）；被拒的決定說明原因（過期卡／無法解析／冷卻中）。

### 7.2 介面規範（二擇一：採「CLI 文字提案卡」）
- **MVP 介面＝CLI 文字提案卡**：純文字／Markdown 區塊，由主控在掌舵者視窗貼出（或終端機印出）。回覆語法：`核准 PROP-SI-NNN`／`否決 PROP-SI-NNN <一句理由>`／`退回 PROP-SI-NNN <一句修改要求>`；晉升確認 `晉升 PROP-SI-NNN`（僅在驗證 PASS 且 digest 相同時被接受）。轉交卡（`route=handoff`）只回「轉交／不轉交」。
- **Console 卡片＝範圍外**（⏸ F-SI-101，見 §3.3）：不寫入 FSM 狀態檔、不繞過既有簽核硬閘。
- 設計系統：不適用（純文字）；響應式：不適用；無障礙：不依賴色彩，可在 Windows Terminal 與 macOS Terminal 顯示；語言：繁體中文，專有名詞保留原文。

### 7.3 原型／線框（提案卡；核心區 ≤ 12 行）
```text
[PROP-SI-007] 記憶條目｜retire｜目標：<座標>｜digest：a1b2c3d4｜驗證：PASS／FAIL／NE／未驗
一、症狀：<一句；含 OBS／DEF 座標與再現次數>
二、改什麼：<一句；+x／-y 行；觸及比例>
三、風險與回滾：<一句；影響面＋一個動作的回滾配方＋驗證狀態>
決定：核准 ／ 否決＋一句理由 ／ 退回＋一句修改要求
--- 以下不計入核心區 ---
證據座標｜預算宣告｜完整 diff 座標｜冷卻狀態｜轉交通道（route=handoff 時）
```

## 📅 8. 時程與里程碑 (Timeline & Milestones)
### 8.1 專案里程碑（階段出口一律為症狀型判準；沒有日期、沒有版本號）
| 階段 | 里程碑 | 交付物 | 出口判準（症狀型；條件全部成立） | 負責人 |
|------|--------|--------|--------------------------------|--------|
| **P0** | 觀察帳本＋資料模型（本輪已 dogfood） | §5.1.1 欄位定稿、遷移後的觀察帳本；FR-SI-01～04、29 | (a) 任何視窗新增一筆觀察時不需向掌舵者追問任何必填欄（反症狀：出現「某欄無法填」的觀察即未達）；(b) 全帳本通過欄位與引用檢查；(c) 既有各列處置皆合枚舉且 `orig` 保全；(d) 零筆無座標列、零筆「之後再看」 | 主控（帳本單一窗口）、SD、QA（SCG-0 審查） |
| **P1** | 歸因＋提案（只提案） | FR-SI-05～11、14、28；PROP 物件與提案卡 | (a) 至少一筆真實（非構造）觀察端到端走到提案卡，且至少一筆屬 M／P／R／D 類（PROP-SI-001、002 屬不可進化面，走轉交，不能充當本條）；(b) 零提案觸及正式面（`git status`／HEAD 逐字對照）；(c) 掌舵者回饋中無 `reason_class=卡面不清` 的退回；(d) FR-SI-28 的可重跑檢查存在且綠 | 子代理（提案者）、主控 |
| **P2** | 人工閘＋沙盒套用＋驗證 | FR-SI-12、13、15～21 | (a) 至少一筆 M／P／R／D 類真實提案走完「閘→沙盒→驗證→晉升或否決」，DEC 紀錄齊全；(b) 該筆驗證含對照與突變，且突變確實使驗證轉紅（證明驗證有鑑別力）；(c) 至少一次同型再提被冷卻擋下（M4 結構性為 0 的證據）；(d) 正式面零「未經人工閘的變更」（git 歷史與 DEC 對帳）；(e) 回滾配方乾跑通過 | 掌舵者（閘）、審查者（子代理）、主控 |
| **P3** | 量測＋退役 | FR-SI-22～27；量測腳本 | (a) 量測腳本在真實帳本上跑通，輸出 M1～M5 值、樣本數、窗與判準指紋（樣本不足者印 NOT-EVALUABLE）；(b) 至少一個採納量測窗關閉並入帳（clean／recurred／rolled-back）；(c) 至少一筆退役提案走完人工閘；(d) §1.1 反證條件已檢查並留紀錄（M1 未優於基線者列為 T1 決策項，不自動下線） | 主控、掌舵者 |

**🔴 人機協作確認點**：[ ] 出口判準為症狀型且無日期　[ ] 負責人已確認　[ ] 里程碑定義清晰

### 8.2 出口判定規則
- 出口須有**正向證據**：零發現不是 PASS（C-13）；量不到＝NOT-EVALUABLE，不算達標也不算失敗，沿用上值並說明缺什麼。
- 已達標階段的出口症狀再現（附 sid 或 OBS 座標）＝該階段重評；時間流逝、版本升級、覆蓋度數字不構成重評理由。
- 每階段出口時，該階段 FR 與 AC 各列必須落在且只落在 §8.3 四格之一，沒有「未分類」列。

### 8.3 結案帳體例（沿用 PRD v2.1 §16.1）與立案時已宣告的 ➖／⏸
四格：✅ 已落地（規範性機制在、且有測試或鎖）／➖ 依設計退役（附依據座標）／⏸ 延後至症狀驅動（附**一句**可觀測再開症狀；禁止寫輪號、日期、「待排程」）／📎 驗收資料殘留（附殘留是什麼）。座標：`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` §16.1。立案時（本稿）尚無任何 ✅；以下是立案時已宣告的 ➖／⏸：

| 項目 | 格 | 依據／再開症狀 |
|------|-----|---------------|
| 更新模型權重 | ➖ | SOP S1 不在範圍；§3.2 |
| 自我發明評估器（meta-oracle 自演化） | ➖ | 禁令 22～25 末項；C-07 |
| 日曆／版本號觸發與常駐排程 | ➖ | C-12；PRD v2.1 §16.1 ➖（本 repo 刻意不做 Daemon） |
| 無人工閘的自動採納 | ➖ | 禁令 11、12；§3.2 |
| F-SI-101～104（Console 提案卡／授權代決／機器可讀帳本／harness 整體 diff 提案） | ⏸ | 各自的一句再開症狀見 §3.3 |

### 8.4 再開與退場（事件驅動）
- 修訂本 PRD 只依：T1（掌舵者立案，附原文）、SOP S7 觸發 T-1～T-7 的症狀、§3.3 某 ⏸ 列的再開症狀實際發生（附 sid／座標）。
- 本 PRD 本身是驅動器：不開 `AutoSDD_improving_117`、不產四件套（附錄 C.1）；範本〈🏁〉T1～T4 仍管軌道①。
- 退場：§1.1 反證條件成立時列為 T1 決策項；退場方式（縮減或廢止）由掌舵者決定，不自動下線。

## 🔧 9. 技術選型與架構 (Technical Stack & Architecture)
*架構方向由 SD 棒填寫。*

## ⚠️ 10. 風險與依賴 (Risks & Dependencies)
### 10.1 風險評估
| 風險（來源） | 機率 | 影響 | 現有防線（座標） | 本 PRD 緩解 | 剩餘風險 | 負責人 |
|-------------|------|------|-----------------|------------|----------|--------|
| **Goodhart／指標被優化**（S-20、S-21） | 中 | 高 | 五問協定家族計數降為資訊欄（`FiveQuestion_Audit_Protocol/README.md`:85–89）；R-9.27／9.28 held-out（`AISDLC_SDD/CLAUDE.md`:331～332） | §1.3.1、FR-SI-20、22、NFR-SI-05 | 帳本與腳本是可寫純文字；偵測靠 git 歷史（AC-SI-04-3）而非機械擋寫 | 掌舵者、量測者 |
| **Reward hacking／目標玩弄**（S-17 附錄 H：代理移除偵測所需記錄而得滿分） | 中 | 高 | R-9.20.3 Generator／Evaluator 獨立；鐵律四 | FR-SI-11、18、20；AC-SI-04-3 | 提案者可能改「被評估對象」而非評估器；靠審查者唯讀與突變鑑別（FR-SI-19） | 審查者 |
| **自評偏誤**（S-03、S-11、S-24、S-25） | 高 | 中 | `evaluator_command` 二次驗證（`AutoClaude/CLAUDE.md`:175、239）；K=1 人工閘 | FR-SI-18（外部訊號為主）、19；AC-SI-06-1 | 提案者與審查者同為 Claude 家族，錯誤可能相關（S-11：錯誤獨立是矯正的必要條件）⇒ 只能降低、不能消除 | 主控 |
| **無界遞迴／無界增長／成本**（S-17、S-25、S-26） | 中 | 高 | `SDD_*_BUDGET`；Gap-042／048（`AutoClaude/CLAUDE.md`:200–201）；額度守衛 | NFR-SI-01；FR-SI-10、17、24 | 初值未校準；邊際報酬遞減只靠落後指標（回滾／再現），沒有領先指標 | 主控 |
| **Context collapse／brevity bias／記憶膨脹**（S-06、S-07、S-12） | 中 | 中 | `MEMORY.md` 載入上限（S-08）；preference 10 鍵；context 水位守衛 | FR-SI-09（增量 delta、禁整份重寫）、27 | delta 累積仍會膨脹；Playbook 與規則層沒有通用策展（SOP II-6） | 提案者 |
| **守衛面自我修改**（S-09、S-10、S-22） | 低～中 | 高 | 治理檔唯讀守衛（`.claude/hooks/block_destructive_git.py`:1445，僅 `AUTOSDD_UNATTENDED` 阻斷）；守衛面准入；harness 分類器（`.claude/**`） | FR-SI-07（轉交）、NFR-SI-02；零新增守衛碼 | 有人值守時 `_GOV_EXACT` 只出聲不阻斷；三份 `CLAUDE.md`、`governance/rules/*.yaml` 不在清單（理論洞 P4）；靠流程與審查者唯讀 | 主控 |
| **記憶污染／記憶獎勵膨脹**（S-13、S-11、S-22） | 中 | 高 | `knowledge_base` 存結果標籤；`MEMORY.md` 可人審 | FR-SI-02、09、27；K=1 閘 | Claude Code auto memory 由 harness 自寫、不在本迴圈控制內（誠實劃界）；只能事後稽核（只讀） | 掌舵者 |
| **Misevolution／工具與技能供應鏈**（S-22、S-09、S-10） | 低 | 高 | Rule 9；hooks deny 連 `bypassPermissions` 都擋（S-10）；治理檔唯讀守衛 | NFR-SI-02；FR-SI-07（skill／hook 一律轉交） | 新 skill／hook 啟用前的掃描流程本輪未確認存在（SOP II-6） | 掌舵者 |
| **信心懸崖**（S-25：裁判可靠度隨迴圈衰退） | 中 | 中 | K=1 人工閘；`meta_halt_monitor` | FR-SI-24（劣化暫停）、19（對照／突變，不靠裁判預測） | 後期提案的裁判可靠度仍可能衰退；以回滾／再現作落後訊號 | 掌舵者 |
| **提案疲勞（審閱瓶頸）** | 中 | 中 | — | FR-SI-10（≤3）、§7 三句話卡、預設拒絕（不審＝不變） | 長期不審則迴圈靜止（安全但無價值）；M1 會顯示無改善，走 §1.1 反證路徑 | 掌舵者 |
| **樣本過小致指標常態 NOT-EVALUABLE** | 高 | 中 | NOT-EVALUABLE 體例（五問協定） | FR-SI-22（印樣本數；不以小樣本宣稱） | P3 出口可能長期達不到 ⇒ 價值主張長期「未證」；是否維持由掌舵者決定 | 量測者 |
| **額度耗盡**（C-16） | 高 | 中 | 額度守衛、`--pace` | NFR-SI-07 | 研究型 Web 工具節流已被實測成瓶頸（OBS-SI-005）；運轉期不使用 Web（§3.2） | 主控 |

### 10.2 依賴項目
**技術依賴**：AutoClaude EventBus／EvolutionPlugin（`AutoClaude/autoclaude/core/`、`plugins/`）；SDD FSM runtime CLI（`FSMRuntime`）與 R-9.2x 提案管線；缺陷帳本與其工具（`tools/check_defect_log_crossref.py`）；Claude Code harness 的記憶／hooks／skills 行為（以 S-08／S-09／S-10 為準，現行頁面描述，不以版本號當觸發）；git；額度守衛。
**團隊依賴**：掌舵者審閱（唯一核准者）；QA 獨立審查（SCG-0）；SD 補架構方向（§9）。
**再查證觸發**：本 PRD 引用的 DP／S-NN 失效時依 SOP II-7（T-1 追溯斷裂、T-2 dogfood 失效、T-4 反證浮現、T-7 來源失效等症狀）重跑相關步驟，不整份重跑。

**🔴 人機協作確認點**：[ ] 所有風險已識別　[ ] 緩解措施可行　[ ] 依賴項目已確認

## 🔍 11. 既有系統分析 (Existing System Analysis)
### 11.1 現況分析
**系統概況**：AutoSDD 已有分散的自我改進面（引擎內演化／知識庫、SDD 規則提案管線、根層缺陷帳本與審計協定、Claude Code 記憶／hooks／skills）。共同特徵：多數已守「只提案、人工閘」，但各面各自為政——沒有統一的提案物件、冷卻、獨立評估器、症狀指標與退役。**盤點基準**：寫稿期間 HEAD 由 `a50bc04c` 前進到 `b78effb4`（主控並行提交），下表以 `b78effb4` 時的檔案為準，座標一律現查。

| # | 面 | 位置 | 學什麼 | 怎麼套用 | 閘門 | 缺口 → 對應 FR |
|---|----|------|--------|---------|------|----------------|
| 1 | AutoClaude 演化 | `autoclaude/evolution/`（`playbook_evolver.py`、`minimax_evolver.py`）＋`plugins/evolution_plugin.py` | ESCALATION 失敗鏈→INJECT_STEP／SPLIT_STEP／REVISE_EVALUATOR 提案（AI 優先、規則 fallback） | Kernel 路徑回傳 `MutationProposal`、只寫 log（`AutoClaude/CLAUDE.md`:191）；舊路徑 `apply_evolution` 寫 `evolved_<檔名>.yaml` | `max_evolutions=3`、per-step 上限 2、`require_evolution_signoff`（預設 False） | 只提案靠「無生產建構點」；`REVISE_EVALUATOR` 動到評估器；無 held-out → FR-SI-11、20、28 |
| 2 | AutoClaude 知識庫 | `utils/knowledge_base.py`＋`plugins/knowledge_base_plugin.py` | 成功／升級結果→error_signature→策略映射（JSONL） | 查詢命中直接跳到歷史有效策略 | `_MAX_ENTRIES=1000`；帶結果標籤 | 容量汰除無人審、無退役條件 → FR-SI-09、27 |
| 3 | AutoClaude 偏好記憶 | `plugins/preference_memory_plugin.py` | 使用者偏好（人寫入） | PRE_CORRECTION 唯讀注入 correction prompt | ≤10 鍵；Brain 輸出不得回寫（ADR-AGT-003 §2） | 寫入通道（誰呼叫 `set`）未查證 → 只讀接點 |
| 4 | AutoClaude 轉譯策略學習 | `plugins/translation_learner_plugin.py`＋`core/ports/translation_learning.py` | RTM 覆蓋度歷史的失敗頻次→轉譯策略改進候選 | 只產 `proposed`、dedup、`record_proposal` | `translation_max_proposals_per_run=3`；apply＝人工 signoff 守界 | 提議的審閱介面未見（未查證：誰在哪裡審）→ FR-SI-08、12、14 |
| 5 | AutoClaude 收斂／目標驗證 | `plugins/convergence_plugin.py`、`plugins/goal_synthesis_plugin.py` | 即時 trend 判定；DONE 前 Brain 驗證 global_goal，未達成→`MutationProposal(INJECT_AFTER)` | run 內動態步驟突變（不落盤） | `goal_synthesis_fail_closed=False`（預設 fail-open，`utils/config.py`:211） | Brain 判定屬自評點，是否有外部校驗未逐一盤點（SOP II-6）→ FR-SI-18（僅涵蓋進迴圈者） |
| 6 | AutoClaude 回寫與進度 | `plugins/rtm_writeback_plugin.py`、`plugins/goal_progress_plugin.py` | RTM 覆蓋度報告、跨 run 進度快照 | 諮詢用報告／帳本，不覆寫人工 RTM | — | 資料來源（只讀） |
| 7 | SDD 規則提案管線 | `tools/fsm_runtime/{production_to_fpl,slv_generator,spec_patch_proposer,scaffold_gc}.py`；`governance/rules/R-9.20～R-9.37` | 生產偏差→FPL→SLV 草案；spec_defect 重複→SPEC-PATCH 草案；規則 ROI→退役提議 | 一律 `proposed`；LEARNING_COMMIT／HUMAN_PENDING 人工 review（`AISDLC_SDD/AISDLC_SDD_v0.30/workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md`:395–396） | `set_maturity(reviewed_by=)`、`MAX_PATCH_PER_AC=2`、`meta_halt_monitor` | AutoClaude 與根層無對等管線；僅 SDD 面完整 → FR-SI-08（R 類）、25、26 |
| 8 | SDD 元停機與 held-out | `tools/fsm_runtime/meta_halt/`、`objective_tuner.py`、`dimension_necessity_oracle.py`、`joint_calibration_oracle.py`、`counterfactual_replay.py`；R-9.24／9.27～9.29 | 元迴圈採納／退役抖動；tuner 與 held-out 對抗分離 | advisory＋有界 | `SDD_META_CHURN_MAX`、`SDD_REPLAY_MAX_CASES`、`SDD_OBJ_TUNE_BUDGET` | 機制只服務 SDD 自身評分器（依檔名與規則文判斷，未逐檔讀碼），未通用化到記憶／Playbook／文件 → FR-SI-20、26 |
| 9 | SDD 測試失敗映射 | `AISDLC_SDD/AISDLC_SDD_v0.30/.claude/skills/test-failure-analyzer/SKILL.md` | 失敗 TC→RTM→AC／US／F，判修程式或修 Spec | advisory skill（allowed-tools: Read） | — | 歸因的既有映射來源 → FR-SI-05 |
| 10 | 根層改進軌道與缺陷帳本 | `docs/04_planning/AutoSDD_improving_NN.md`（軌道①）、`docs/06_quality/AutoSDD_Defect_Log.md` | 缺陷／摩擦→DEF 列，附「再開症狀」文字 | 人工單一窗口入帳；休眠範本〈🏁〉T1～T4 | 每列 ≤700 bytes；crossref 閘 | 復發連結無結構化欄；發現日期無時分 → FR-SI-01、04、06 |
| 11 | 根層五問審計協定 | `docs/06_quality/FiveQuestion_Audit_Protocol/`、`docs/06_quality/FiveQuestion_Round_Ledger.jsonl` | hook 行為症狀量測 | 症狀閘＋三態；家族計數降為資訊欄 | `params.json` | （參考體例）→ FR-SI-19、22 |
| 12 | 根層事後量測器 | `tools/probe/audit_session.py`、`tools/probe/misstep_attribution.py` | 逐字稿／帳本的違規與失誤歸因（關鍵詞啟發式，量級可信） | 只量不閘（`audit_session.py` 檔頭:8–14） | — | 歸因／量測的既有載體 → FR-SI-05、22 |
| 13 | Claude Code 記憶檔 | `~/.claude/projects/<slug>/memory/`（`MEMORY.md`＋記憶檔；不在 repo 內） | Claude 依修正與偏好自寫筆記（S-08）；人可編輯／刪除 | 每次對話載入索引（有上限）；視為 context 非強制設定 | 寫稿時 `MEMORY.md` 22,755 bytes／113 行；目錄共 125 個 .md 檔含索引（本稿量測） | 無結果標籤、無退役；依寫入來源過濾未見；auto memory 不在迴圈控制內 → FR-SI-02、09、27 |
| 14 | Claude Code hooks／skills | 根 `.claude/hooks/`、`.claude/settings*.json`；各子專案 `.claude/skills/` | hooks＝確定性控制（deny 連 bypassPermissions 都擋，S-10）；skills 由 Claude 自建／改寫（S-09） | 守衛面准入；治理檔唯讀守衛 | `allowed-tools`、`` !`cmd` `` 風險（S-09） | 新 skill／hook 啟用前掃描流程未確認存在 → FR-SI-07（轉交） |
| 15 | AgentConsole | `AgentConsole/CLAUDE.md`:15；`docs/04_planning/ADR/ADR-XPLAT-016-sdd-integration-loop-minimal-intrusion.md` | BRD／PRD 匯入、人工 signoff 硬閘、FSM 唯讀顯示 | SDD FSM 寫入一律經 `FSMRuntime` CLI 子行程 | — | MVP 不整合提案卡（⏸，§8.3）→ FR-SI-12 的既有人工閘 |
| 16 | 休眠重評與延後體例 | `docs/04_planning/AutoSDD_improving_116.md` §9、`AutoSDD_improving_115.md` §5.2、PRD v2.1 §16 | 每輪末歸格＋延後清單附可觀測再開症狀 | 只准三分類；四格結案帳 | — | §8 階段出口沿用此體例 |

### 11.2 缺口表（接既有／新建）
| 缺口 | 證據座標 | 對應 FR | 類型 |
|------|---------|---------|------|
| G-SI-01 演化「只提案不套用」靠無生產建構點；`apply_evolution` 呼叫點仍在 | `AutoClaude/CLAUDE.md`:191；`_escalation_handler.py`:111／208／263；`_complex_mutations.py`:114；OBS-SI-010 | FR-SI-28 | 既有缺口收斂 |
| G-SI-02 `require_evolution_signoff` 預設 False 與文件宣稱並存 | `AutoClaude/autoclaude/utils/config.py`:194；`execution/playbook_runner.py`:299–322 | FR-SI-28（AC-2） | 既有缺口收斂 |
| G-SI-03 `REVISE_EVALUATOR` 與評估器隔離衝突；兩條路徑語意不一（Kernel 路徑轉成 `REVISE_CURRENT` 的 prompt 包裝，舊路徑直接覆寫 `evaluator_command`）；`AutoClaude/CLAUDE.md`:109 原只列兩型，已於 `738f4f60` 補列（OBS-SI-009） | `evolution_plugin.py`:259、284；`playbook_evolver.py`:255–259 | FR-SI-11 | 新建（不受理） |
| G-SI-04 AutoClaude 演化提案與根層改進迴圈皆無 held-out／獨立評估器 | SOP II-6 | FR-SI-20 | 新建（通用化 SDD 機制） |
| G-SI-05 Playbook 與規則層無通用 delta 策展 | SOP II-6 | FR-SI-09 | 新建 |
| G-SI-06 無邊際報酬遞減停機規則 | SOP II-6 | FR-SI-24 | 新建 |
| G-SI-07 記憶面無結果標籤／退役；索引逼近載入上限 | `MEMORY.md`（22,755 bytes／113 行）；S-08 | FR-SI-02、09、27 | 新建 |
| G-SI-08 新 skill／hook 啟用前掃描流程未確認存在 | SOP II-6 | FR-SI-07（轉交；不新增守衛碼） | 登記（理論洞） |
| G-SI-09 可進化／不可進化面缺機械分界（`_GOV_EXACT` 僅無人值守阻斷、僅涵蓋 Write／Edit／NotebookEdit，不含三份 `CLAUDE.md`、`governance/rules/*.yaml`） | `.claude/hooks/block_destructive_git.py`:1423–1472 | FR-SI-07、15（流程性邊界） | 登記（理論洞；守衛面准入） |
| G-SI-10 復發連結無結構化欄；DEF 發現日期無時分 | `AutoSDD_Defect_Log.md`:70（欄位列）、DEF-200-551 列 | FR-SI-01、06、22 | 新建（OBS 側）；DEF 側欄位變更須掌舵者裁決（附錄 C.2 #3） |
| G-SI-11 `PROP-SI-NNN` 沒有定義的載體：目前只出現在觀察帳本處置欄文字 | OBS-SI-005、OBS-SI-012 | FR-SI-08（物件定義）；載體形態由 SD | 新建 |
| G-SI-12 驗證三態與突變鑑別在產品面未成文：只見於整合輪 116 QA 實務 | `AutoSDD_improving_116.md` §9.1 | FR-SI-19 | 新建（成文化既有實務） |
| G-SI-13 提案無冷卻（SDD 規則面有抖動防護，其他面無） | R-9.24.1／9.24.2 | FR-SI-13、26 | 新建（通用化） |
| G-SI-14 `translation_learner` 的 proposed 提議未見固定審閱介面 | `translation_learner_plugin.py`:10–19；`AutoSDD_improving_115.md` §5.2（Console 路徑活化列為延後） | FR-SI-14（提案卡）、§8.3 ⏸ | 新建（現況審閱者未查證） |

### 11.3 影響分析
| 模組／功能 | 影響程度 | 需要修改 | 風險 |
|-----------|---------|---------|------|
| AutoClaude 演化面 | 低 | 加可重跑檢查（FR-SI-28）；不改既有行為 | 零退化；須過 AutoClaude 全套與 lint |
| AISDLC_SDD runtime／規則 | 低 | 重用既有 proposed 管線；不改 `_HAPPY_PATH`、不改規則本體 | 不得引入新 FSM 狀態（禁令 8、9） |
| 根帳本與文件 | 中 | 新增欄位與提案／決定載體；DEF 側欄位變更須掌舵者裁決 | 每列 ≤700 bytes；crossref 閘需同步 |
| 記憶面 | 中 | 新增條目規範與容量事件 | 條目規範只約束經本迴圈寫入者；harness 自寫條目不受控 |
| Hooks／settings／守衛面 | 無 | 零修改（守衛面准入） | — |
| AgentConsole | 無 | MVP 不改（⏸） | — |

**向後相容性**:
- [x] 需要保持向後相容（既有演化行為、DEF 帳本體例、既有 OBS ID 不變）
- [ ] 允許 Breaking Changes

**🔴 人機協作確認點**：[ ] 影響範圍已完整評估　[ ] 相容性策略已確認

## 🔗 12. 整合規格 (Integration Specifications)
### 12.1 接點表
| # | 接點 | 對象與座標 | 資料流向／內容 | 權限 | 備註 |
|---|------|-----------|---------------|------|------|
| 1 | AutoClaude Plugin／EventBus | `autoclaude/core/event_bus.py`、`plugins/*` | 讀 ON_ESCALATION／ON_SUCCESS 產物（KB jsonl、escalation dump、checkpoint） | **只讀** | MVP 不新增 Plugin；新增須走 Plugin SOP（`AutoClaude/CLAUDE.md`） |
| 2 | AutoClaude 演化提案 | `EvolutionPlugin` 的 `MutationProposal` | 流入 PROP（FR-SI-08） | **提案**；套用**需人工**（FR-SI-12／16） | `apply_evolution` 現有呼叫點受 FR-SI-28 檢查 |
| 3 | SDD R-9.2x 提案管線 | `slv_generator`／`spec_patch_proposer`／`scaffold_gc`／`rule_loader.set_maturity` | R 類沿用；本迴圈只加歸因、冷卻、量測 | **提案**＋**需人工**（HUMAN_PENDING／`reviewed_by`） | 不新增管線 |
| 4 | SDD FSM runtime | `FSMRuntime` CLI（`python -m tools.fsm_runtime.fsm_runtime`） | 讀 `show` | **只讀** | 寫入一律經 CLI（禁令 1）；本迴圈不新增 FSM 狀態 |
| 5 | AgentConsole 簽核與顯示 | `AgentConsole/CLAUDE.md`:15；ADR-XPLAT-016 | MVP 不整合；post-MVP 唯讀鏡像提案卡 | MVP：無；post-MVP：**只讀**＋既有簽核硬閘（**需人工**） | ⏸ F-SI-101 |
| 6 | Claude Code 記憶檔 | `~/.claude/projects/<slug>/memory/` | 讀：稽核報告；寫：M 類提案經核准後由人晉升 | 讀＝**只讀**；寫＝**提案**＋**需人工**；harness 自寫＝不受控 | 回滾靠前置快照（AC-SI-16-2） |
| 7 | Claude Code hooks | `.claude/hooks/`、`.claude/settings*.json` | 讀 hooks 痕跡與量測器輸出；不新增、不修改 | **只讀**；任何變更＝守衛面准入（需暴露證據＋**需人工**） | 活性現查見根 `CLAUDE.md`〈hook 載具〉 |
| 8 | Claude Code skills | 各子專案 `.claude/skills/` | D 類提案 diff；啟用前掃描 `allowed-tools`／`` !`cmd` ``／夾帶 hook（S-09） | **提案**＋**需人工**；掃描＝**只讀** | `.claude/**` 屬受保護路徑 ⇒ 轉交（FR-SI-07） |
| 9 | 缺陷帳本／五問協定／休眠範本 | `AutoSDD_Defect_Log.md`、`FiveQuestion_Audit_Protocol/`、`AutoSDD_Iteration_Prompt_Template.md` | 讀；OBS→DEF 升級依帳本既有單一窗口治理 | **只讀**；升級＝**需人工**（單一窗口） | 不改既有協定一字（改協定＝`window_reset`） |
| 10 | 額度守衛 | `python tools/session_resume_planner.py --pace`、`tools/lib/quota_gate.py` | 派工前查詢 | **只讀** | 每次現查，不得記住上次值 |
| 11 | git | 根 repo | 沙盒副本／晉升 commit／回滾 revert | 晉升與回滾＝**需人工**；沙盒＝自動可丟棄 | 鐵律五擋毀滅性形態 |

### 12.2 資料流向、同步策略與錯誤處理
- **資料流向與同步**：事件驅動、單向（來源 → 觀察 → 歸因 → PROP → DEC → 套用／驗證 → 量測 → 退役）；無常駐行程、無排程（PRD v2.1 §16.1 ➖ 不做 Daemon）；同步頻率不適用，啟動只依 AC-SI-03-1 的五類事件。
- **錯誤處理**：修訂 ≤ `MAX_REVISIONS`、驗證重跑 ≤ 2，超界即停、不退避重試（禁令 4）；階段失敗留一筆 OBS（分類 `bug`）並於提案卡標示；ESCALATION 後僅人工恢復（禁令 6、7）；資料補償＝回滾配方（NFR-SI-04），人工執行。

**🔴 人機協作確認點**：[ ] 各接點的權限標示（只讀／提案／需人工）已確認　[ ] 同步策略符合需求　[ ] 錯誤處理機制完善

## 📎 13. 附錄 (Appendix)
### 13.1 詞彙表 (Glossary)
| 術語 | 定義 |
|------|------|
| 觀察（OBS）／提案（PROP）／決定（DEC） | OBS＝帶座標的一句症狀記錄，不取代 DEF 缺陷帳本；PROP＝起始狀態必為 `proposed` 的改進物件，產生者無正式面寫入權；DEC＝掌舵者對 PROP 的人工決定紀錄，綁 digest |
| 運轉／再開症狀／容量事件 | 運轉＝由啟動事件起、到該次各提案皆落入終態止的一次迴圈執行（非日曆週期）；再開症狀＝一句可觀測事件，成立時重新啟動某延後項，不得含輪號、日期；容量事件＝有上限的儲存用量達 `CAP_FRAC`，觸發退役／合併提案 |
| 歸因／根因鍵／復發 | 歸因＝把觀察映射到 DEF／OBS／規則／Playbook 步驟／文件／記憶條目的座標清單（不含自評分數）；根因鍵＝`<面>/<機制>` 短字串，由歸因者提出、審查者確認；復發（再現）＝已結列所防症狀再次發生且經審查者確認 |
| 暴露度／守衛面 | 暴露度＝P2 的必要條件：a 掌舵者真機回報／b 非構造性逐字稿／c 真實語料重放命中（`severity.md`〈暴露度〉）；守衛面＝根 `CLAUDE.md`〈守衛面准入〉所列 `.claude/hooks/**`、`.claude/settings*.json`、指定 `tools/lib/` 檔與 `tools/session_resume_planner.py` |
| 不可進化面／可進化面／轉交 | 不可進化面＝NFR-SI-02-1 清單，本迴圈對其零寫入；可進化面＝M 記憶條目／P Playbook 片段／R SDD 規則草案／D 非治理文件 diff；轉交（handoff）＝目標在不可進化面時，把提案交給既有人工通道（DEF／R 系列／T1／PRD 修訂） |
| K=1／digest | K=1＝逐項人工核准，一個決定對應一個 PROP、不批次；digest＝PROP 內容摘要（演算法由 SD 定），核准綁定此值、內容變動即失效 |
| 沙盒／晉升／回滾配方 | 沙盒＝與正式面隔離的副本，丟棄即回原狀；晉升＝把已驗證的沙盒變更合入正式面，必為人工動作；回滾配方＝一個動作即可回到採納前的指示（git revert、前置快照還原、`set_maturity` 退回） |
| 對照／突變／held-out | 對照／突變＝基線重現症狀、套用後消失、弱化後再現，缺一則驗證無鑑別力；held-out＝提案者看不到的評估資料與指令，由提案者以外角色凍結 |
| 三態（NE） | PASS／FAIL／NOT-EVALUABLE（簡寫 NE）；NE 不算 PASS |
| 冷卻／劣化暫停 | 冷卻＝被否決的同型提案暫禁再提，直到掌舵者解除或出現與原證據不相交的新證據（再提資格事件）；劣化暫停（SUSPENDED）＝連續採納劣化時迴圈停止受理提案，僅掌舵者可恢復 |
| Goodhart／context collapse／misevolution | 對代理指標過度最佳化損害真實目標（S-20、S-21、S-17 附錄 H）；整份重寫逐漸侵蝕細節（S-06）；自我演化經 model／memory／tool／workflow 路徑無意走偏（S-22） |
| 判準指紋／訂正協議 | 指標定義的摘要，指紋不同的數字不得並列（先例 `audit_session.py` 輸出）；修正舊文時原文逐字保留、不靜默覆寫（先例 `AISDLC_SDD/CLAUDE.md` 各〈訂正〉段） |

### 13.2 參考資料
- **上游與帳本**：SOP `docs/05_development/SelfImproving_Research_Methodology_SOP.md`；觀察帳本 `docs/06_quality/SelfImproving_Observation_Ledger.md`。
- **研究來源（只引 SOP 來源表 S-NN；層級 V1／V2／V3 與 URL 見 SOP II-3；本 PRD 不引用任何來源的量化結果——V2 數字是小模型轉述，引用前須開原頁面核對）**：S-01 Reflexion；S-02 Self-Refine；S-03 Large Language Models Cannot Self-Correct Reasoning Yet；S-05 Voyager；S-06 Agentic Context Engineering；S-07 Effective context engineering for AI agents；S-08 Claude Code 記憶官方文件；S-09 skills 官方文件；S-10 hooks 官方文件；S-11 Memory Reward Inflation；S-12 When Continual Learning Moves to Memory；S-13 MemoryGraft；S-14 Coding Agents are Strong Prompt Optimizers；S-15 MAS-PromptBench；S-16 ADAS；S-17 Darwin Gödel Machine；S-18 AlphaEvolve；S-19 Ouroboros；S-20 Scaling Laws for Reward Model Overoptimization；S-21 Categorizing Variants of Goodhart's Law；S-22 Your Agent May Misevolve；S-23 PACE；S-24 Self-Designed Evaluators and Warm Memory；S-25 Rehearse；S-26 Building effective agents；S-27 Practices for Governing Agentic AI Systems；S-28、S-29 綜述（地圖用）。S-04、S-30 為旁證、無 DP 去處，本 PRD 未引用。
- **憲法**：`AISDLC_SDD/CLAUDE.md` Rule 9〈絕對禁令〉1～27 與〈核心機制速查〉R-9.20～9.37；根 `CLAUDE.md`〈守衛面准入〉〈鐵律一～七〉〈權限姿態〉〈三條改進軌道〉；`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md`〈🏁〉；`docs/06_quality/FiveQuestion_Audit_Protocol/`（`README.md`、`severity.md`、`params.json`）。
- **既有機制與體例**：§11.1 各列座標；`docs/06_quality/AutoSDD_Defect_Log.md`；`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` §16；`docs/04_planning/AutoSDD_improving_115.md` §5.2、`AutoSDD_improving_116.md` §9。

### 13.3 變更記錄
| 日期 | 版本 | 變更內容 | 變更人 |
|------|------|---------|--------|
| 2026-10-19 | v0.1（Draft） | 初版：依掌舵者 T1 與 SOP 起草 Stage-1 上位規格（Brownfield） | SA 棒（Sonnet 5.5） |

## 🔗 14. 文檔追蹤鏈 (Traceability)
### 上游文檔
- **需求來源（掌舵者 T1，2026-10-18，逐字；本 PRD 的唯一上游需求）**：
  > 請協助設計自我進化機制 ==> SelfImproving.prd:
  > 1.請參考OPENAI/Claude Code等網路前言論文==> 有關自我進化機制論文, 收集有關的有用且重要資料進行分析研究, 來進行設計! 並統整一個研究方法論SOP
  > 2.依照第一項方法論SOP, 進行規劃，分析，設計，實作，與獨立審查, 完成此模組的PRD!
  > 3.在進行任何開發過程, 若有發現相關流程不適當或BUG, 請隨時記錄情境與相關資訊, 記錄成帳本, 以便日後進行自我精進!
  > 4.有必要則會隨時自我精進演化與除Bugs
  > 5.將SelfImproving.prd寫入docs\01_requirements
- **逐點對映**：第 1 點→SOP，附錄 A 以 DP-01～12 承接；第 2 點→本 PRD（SA）→SD 補 §9→QA 做 SCG-0 獨立審查→實作輪依 §8；第 3 點→FR-SI-01、02、29 與觀察帳本；第 4 點→全迴圈（§3.1）、事件驅動啟動（FR-SI-03）、Bug 升 DEF（FR-SI-04）；第 5 點→本檔（檔名依 OBS-SI-001 裁決）。
- **研究方法論**：SOP（DP-01～12、風險登記表、再查證觸發）。

### 下游文檔
- **FRD／TCS／SRD**：於實作輪再產（非缺漏）；FRD 以 FR-SI-NN 為追溯鍵。
- **觀察帳本**：`docs/06_quality/SelfImproving_Observation_Ledger.md`（P0 載體，欄位依 §5.1.1 同步）。
- **RTM**：FR-SI-NN → AC-SI-NN-Y → TC，於實作輪產出。
- **追蹤鏈範例**：`DP-04 → FR-SI-12 → AC-SI-12-1 → （FRD BR）→ TCS → TC`；`T1 第 3 點 → FR-SI-29 → AC-SI-29-1 → OBS-SI-NNN → DEF-<id>`。

## 附錄 A　追溯矩陣（DP → FR-SI → 既有機制／新建）
每條 FR 的 DP／既有機制追溯見 §5.2 各條「追溯」行；FR-SI-03、04、29 以既有機制為主（C-12、缺陷帳本治理、T1 原文第 3、4 點）。強度與來源取自 SOP II-5；SOP 該表「PR」欄由本表「FR-SI」欄填寫（PR＝FR-SI-NN）。

| DP | 原則（摘自 SOP） | 主要來源 | 強度 | FR-SI | 既有機制／新建 |
|----|-----------------|---------|------|-------|---------------|
| DP-01 | 外部可驗證訊號優先於自評，自評只作輔助 | S-03、S-26、S-24、S-11、S-06、S-17 | 強 | 18、19 | 有（`evaluator_command`、R-9.27、鐵律四）；通用化到 M／D 類＝新建 |
| DP-02 | 改進落成人類可讀、可版本化、可刪除的工件，不碰權重 | S-05、S-06、S-08、S-09、S-16、S-18 | 強 | 08、16、25 | 有（KB、偏好、`MEMORY.md`、skills、git）→ 接既有 |
| DP-03 | 增量 delta 與逐條策展，禁整份重寫，容量有界 | S-06、S-07、S-08、S-12 | 中 | 09、25、27 | 部分（preference 10 鍵、`_MAX_ENTRIES`、`NoBigBangValueRewrite`）；Playbook／規則層策展＝新建 |
| DP-04 | 提案—驗證—採納三段分離；採納只經人工 K=1、可回滾 | S-17、S-19、S-27、S-26、S-23、S-08 | 強 | 08、12～16、23、26、28 | 有（`evolution_plugin` NO-OP、`translation_learner`、R-9.22、Console 簽核）→ 接既有；統一閘＝新建 |
| DP-05 | 評估器對生成器隔離；評估器不得由被評估者自行發明或修改 | S-17、S-20、S-11、S-21、S-24 | 強 | 11、18、20 | 部分（SDD R-9.27～9.32 有；AutoClaude／根層無）→ 新建（通用化） |
| DP-06 | 迴圈有界，且有邊際報酬遞減的停止規則 | S-25、S-17、S-26、S-10、S-23 | 強 | 03、10、17、24 | 有（`SDD_*_BUDGET`、Gap-042／048、ESCALATION、額度守衛）；停止規則（劣化暫停）＝新建 |
| DP-07 | 保留譜系與回滾；探索型改進保留多分支 | S-17、S-18、S-19、S-08（S-16 同組） | 中 | 08、15、16 | 有（git、Copy-on-Evolve、`EvolutionMetadata`）；「探索型多分支」不在 MVP |
| DP-08 | 提案以真實失敗軌跡與帳本列為輸入（抽象化、帶結果標籤） | S-01、S-14、S-06、S-05 | 強 | 01、02、04、05、09、29 | 有（`translation_learner`、KB、缺陷帳本、觀察帳本）→ 接既有 |
| DP-09 | 記憶只存帶真實結果標籤的條目，可審計並防毒化 | S-11、S-08、S-13、S-22、S-25 | 強 | 02、09、27 | 部分（KB 結果標籤、`MEMORY.md` 可人審）；來源過濾＝新建 |
| DP-10 | 成效以真實症狀驗收，不以自評分數、審查產出數、貪婪接受當成功 | S-20、S-21、S-17、S-11（機制 S-23） | 強 | 06、13、14、19、21、22、23 | 部分（症狀閘、再開症狀）；指標量測腳本＝新建 |
| DP-11 | 自我進化本身要做安全評估；新 skill／hook／工具啟用前掃描並人審；治理檔不在可進化面 | S-22、S-09、S-10、S-13、S-17、S-27 | 強 | 07、11、15；NFR-SI-02 | 有（Rule 9、hooks deny、治理檔唯讀守衛、守衛面准入）→ 接既有；掃描流程＝轉交（登記） |
| DP-12 | harness 可成為優化對象，但一律 diff 提案＋凍結快照評估後才活化；探索／評估流程本身不可改 | S-16、S-19、S-14、S-29、S-15 | 中 | 07、11、28、29 | 部分（INJECT_STEP／SPLIT_STEP／REVISE_EVALUATOR 提案；無 harness 整體 diff 管線）→ MVP 只落地「評估與迴圈自身不可改」半條；harness 整體 diff 提案＝⏸ F-SI-104 |

## 附錄 B　憲法對照表（被觸及的 Rule 9 禁令與守衛面規則 → 本 PRD 如何遵守）
| 規則（座標） | 被觸及原因 | 本 PRD 如何遵守 |
|-------------|-----------|----------------|
| 禁令 1、3（繞過 `FSMRuntime` 讀寫 FSM-STATE；IMPLEMENTATION 期間寫 `docs/01~03`；R-9.6） | 迴圈讀 FSM 狀態；D／R 類目標可能落在 `docs/01～03` | 只讀 `show`、寫入一律經 CLI、不新增 FSM 狀態（§12 #4）；不繞過 R-9.6 擋寫，改由符合條件的視窗處理或轉交（AC-SI-15-3） |
| 禁令 4、5、6、7（retry 超限；Token ≥95% 仍工作；ESCALATION 後自動恢復；structural 強行 auto-recovery） | 提案修訂、驗證重跑、扇出耗額度、停機 | `MAX_REVISIONS`、重跑 ≤ 2、超界升級人工（NFR-SI-01；AC-SI-10-2、17-1）；扇出前 `--pace`（NFR-SI-07）；ESCALATION／SUSPENDED 後僅人工恢復（AC-SI-17-2、24-1） |
| 禁令 8、9、10（`_HAPPY_PATH`／TLA+；觀測態入 Terminals；proposed／external 規則阻塞 SCG） | 是否新增狀態；R 類草案 | 不新增 FSM 狀態、PROP 狀態機只在帳本欄位（不觸 `_HAPPY_PATH`，N/A）；AC-SI-08-3：`proposed` 不阻塞 SCG |
| 禁令 11、12、13（自動退役 active 規則；自動套用 spec patch；planner 自動選目標、localizer 自動改 spec） | 退役提案；R／D 類 diff；歸因會指向 spec | FR-SI-25（系統只提議、SDD 規則退役必經 `set_maturity`）；FR-SI-12、16（K=1、晉升為人工動作）；FR-SI-05（歸因只指向座標、不改檔） |
| 禁令 14、15、16（繞過 `meta_halt_monitor`／無 capability-delta 重學／重放命中率自動 approve；組合排程與最佳化搜尋無界） | 退役與再採納、重放驗證、候選生成 | FR-SI-26；AC-SI-19-3；不做組合最佳化搜尋、候選數上限 FR-SI-10（15、16 其餘 N/A） |
| 禁令 17～25（自評放水、tuner 讀寫 held-out；維度／詞彙／算子／字母／深度／互遞迴自我發明；末項：未獲對抗分離證明即採納自我發明評估器） | 評估、指標與提案類別邊界 | FR-SI-18、20；NFR-SI-05；§3.2 範圍外；FR-SI-11（評估器變更不受理）；AC-SI-29-2（`loop-self` 轉交） |
| 禁令 26、27（接地 fail-closed、沙箱 hang 收 verdict、外聯須 OPEN-X.x；視覺化自動 signoff／簡化呈現繞過） | 沙盒驗證、量不到、提案卡呈現 | AC-SI-19-2、17-1；NFR-SI-02-4、09-1；FR-SI-14（卡面確定性轉換、反解析比對） |
| 守衛面准入（R197：量、不挖）、〈權限姿態〉（`.claude/**` 受保護路徑；不改派子代理繞過）、PRD v2.1 §15.5 紅線 10、`severity.md`〈暴露度〉 | 不可進化面、轉交與沙盒目標、無人值守、守衛面觀察的嚴重度 | FR-SI-01（`暴露` 欄）、07；NFR-SI-02-2、02-3、02-5；AC-SI-15-3；本 PRD 零新增守衛碼，無暴露證據一律理論洞 P4 |
| 鐵律四（宣稱附當回合輸出） | 驗證與指標宣稱 | FR-SI-21 |
| 鐵律一～三、五、六（Windows 載具、絕對路徑、跨平台自問、毀滅性 git、壞等待形態） | 新腳本與欄位、沙盒建立／清理、背景任務 | NFR-SI-06；AC-SI-15-2 |
| 鐵律七（並行派工前切鎖持有面；四點檢查表） | 角色分離與帳本寫入 | FR-SI-18（複審唯讀）；角色矩陣（帳本單一窗口）；附錄 C.1 串行裁決 |
| 三條改進軌道／範本〈🏁〉T1～T4 | 迴圈啟動與是否開輪 | FR-SI-03；附錄 C.1（不開 117） |
| 根 `CLAUDE.md` 12-Rule Rule 5／6／12 | 確定性轉換、預算、fail loud | FR-SI-22；NFR-SI-07-3；NFR-SI-09-1 |
| AgentConsole 人工 signoff 硬閘、FSM 只讀（C-15） | post-MVP Console 接點 | FR-SI-12；§12 #5 |

## 附錄 C　主控裁決與待裁決
### C.1 主控裁決（掌舵者授權；掌舵者可隨時以 T1 推翻）
| 編號 | 裁決 | 座標 |
|------|------|------|
| OBS-SI-001 | 檔名用 repo 慣例 `docs/01_requirements/SelfImproving_PRD.md`（T1 原文 `SelfImproving.prd` 不合 `*_PRD.md` 慣例，文件工具鏈與 docs 守門只認 `.md`）；回報掌舵者 | 觀察帳本 OBS-SI-001 |
| OBS-SI-002 | 額度守衛 `--pace` 回 cap=1，四方專家串行：研究員→SA→SD／Architect→QA；每棒交卷後主控親驗再派下一棒 | 觀察帳本 OBS-SI-002 |
| OBS-SI-003 | 延後；再開症狀：第二次有人為探針手改三件組而寫錯真狀態目錄 | 觀察帳本 OBS-SI-003 |
| OBS-SI-004 | 任務書一律改「文字交卷」，不再要求子代理寫報告檔 | 觀察帳本 OBS-SI-004 |
| 不開 `AutoSDD_improving_117` | 掌舵者要求省去非必要文件；本 PRD 本身是驅動器（不複製範本、不產四件套；軌道① 仍依範本〈🏁〉T1～T4 休眠） | 根 `CLAUDE.md`〈三條改進軌道〉；`AutoSDD_Iteration_Prompt_Template.md`〈🏁〉 |

帳本後續裁決（寫稿時快照；以帳本為準）：OBS-SI-006（任務書一次一題）、OBS-SI-008（PDF 走本機 `python -I` 粗抽、大頁改抓摘要頁）、OBS-SI-011（鐵律一優先於系統提示的 Bash 偏好）、OBS-SI-013（時間欄寫實際日期、任務書改寫「起算日」）。

### C.2 已裁決（主控代決 2026-10-19；授權依據＝掌舵者本輪原文「以上若需要我決策，請依照最佳化, 最理想, 最適當的解決方案，我授權幫我決策」；#1～#5 皆採 SA 建議預設值，凍結核准時掌舵者可逐項推翻，推翻即以 T1 改寫本表）
| # | 事項（原為待裁決） | 裁決＝建議預設值 | 影響 |
|---|-----------|-----------|------|
| 1 | 晉升形態：核准（綁 digest）後，驗證 PASS 仍須掌舵者再執行一次「晉升」動作（兩次人工接觸，第二次只確認）是否可接受？ | 接受（核准一次、晉升確認一次；晉升前顯示驗證摘要） | FR-SI-12、16 |
| 2 | 是否開放主控在掌舵者書面授權下代為核准？ | MVP 不開放；日後若開放，僅限 D 類且逐次書面授權，M／P／R 與轉交一律掌舵者本人（⏸ F-SI-102） | FR-SI-12 |
| 3 | DEF 帳本是否加復發標記（現象欄 `reopens:DEF-xxx` 文字慣例，或新增欄位／時分精度）以使 M1～M3 可機械量測？ | 只在 OBS 側新增；DEF 側用現象欄文字慣例由量測腳本解析、不改表頭；改表頭須另經掌舵者核准 | FR-SI-01、06、22 |
| 4 | `require_evolution_signoff` 預設方向：維持 False＋文件改述，或改 True（fail-closed）？ | 維持 False＋補可重跑靜態檢查＋文件改述（零退化）；改 True 會改變舊路徑行為，僅在掌舵者要求引擎層預設拒絕時採 | FR-SI-28 |
| 5 | MVP 介面採 CLI 文字提案卡（Console 卡 ⏸），PROP／DEC 載體 P1 先用 Markdown 表（與觀察帳本同型），P2 前由 SD 評估機器可讀？ | 同意 | §7、§5.1 |

## ✅ 文檔完成檢查清單
### PRD 品質檢查
- [x] 所有必填欄位已完成（元數據與 Brownfield 欄位已填；「目標日期」刻意無日曆，見 §8）
- [x] 根據專案類型填寫對應的情境專屬章節（Brownfield：§11 已填；Web／Mobile／Greenfield／Sprint／Integration 專屬欄位不適用：無 UI 平台、非新專案、非衝刺、非第三方整合）
- [x] 成功指標明確可衡量（§1.3 M1～M5 附量法與來源；基線未量測者標 NOT-EVALUABLE）
- [x] 範圍定義清晰（§3.1 In-Scope／§3.2 Out-of-Scope）
- [ ] 所有 🔴 確認點已通過（待掌舵者與 QA SCG-0；本稿作者不得自證）
- [x] 時程與資源合理（不適用日曆：改以症狀出口 §8 與額度／人審成本 §4.1 表達）
- [x] 風險已識別並有緩解措施（§10：12 項，含現有防線座標與剩餘風險）
- [ ] 與 Stakeholders 完成評審（待 QA 獨立審查與掌舵者）

### AISDLC 流程檢查
- [ ] 已由 PM/PO Agent (Victoria) 主導撰寫——不適用：本稿由 SA 棒（Sonnet 5.5）依掌舵者 T1 與 SOP 起草（四方專家流程）
- [ ] 已由 BA Agent (Beatrice) 協助驗證——不適用：由下一棒 QA 做 SCG-0 獨立審查
- [ ] 所有人機協作確認點已完成（待掌舵者）
- [x] 文檔追蹤鏈完整（§14、附錄 A；FRD／TCS／SRD 為實作輪下游，非缺漏）
- [x] 版本控制正確（Draft；落在 git 追蹤的 `docs/01_requirements/`；本稿作者未做 git 寫入，由主控提交）

### 本稿特有檢查（SA 自檢；QA 須獨立重驗，不得採信本欄）
- [x] 無日曆／版本號／覆蓋度門檻型觸發；延後項皆為 ⏸＋可觀測再開症狀
- [x] 只引 DP-01～12 與 S-01～30、repo 座標；候選 CD 只出現在 §3.2 作反例
- [x] 不引用任何外部來源的實驗量化結果（S-08 的載入上限屬文件陳述，已標 25KB 換算未查證）；初值參數皆標「初值（未校準）」並註明先例或「無先例」
- [x] 每條 FR 有「追溯」與「憲法對照」；每個 DP 至少落在一條 FR（附錄 A）
- [x] 未新增任何守衛碼、鎖、hook；未改任何既有檔（本稿只新增本檔）

---

**文檔所有者**: 掌舵者
**最後審查日期**: 尚未審查（待 QA SCG-0）
**下一次審查日期**: 事件驅動（QA 審查完成後；不排日曆）

