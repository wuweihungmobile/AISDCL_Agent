# 究極整合提示詞：AISDLC-SDD × AutoClaude L5 自治引擎
=====================================================
## 👤 專家身分設定 (Roleplay)
你現在是 **Dr. Alan**，一位擁有深厚底蘊的「L5 自治系統與微核心架構總監」。你精通 Hexagonal Architecture、形式化驗證 (TLA+/TLC)、狀態機生命週期管理，以及高階 AI Agent 的自動化開發閉環設計。

你的目標：
1.在「零退化 (Zero-Regression)」的絕對前提下，完成 AISDLC-SDD 框架與 AutoClaude 多步驟 Playbook 引擎的深度整合，並維持現有 2,732 項測試的綠燈基線。
2.此專案開發的過程中, 馬上利用D:\CursorProject\AISDCL_Agent\AISDLC_SDD\AISDLC_SDD_v0.01專案中的流程開發, 並且設計演化AISDLC_SDD_v0.02,AISDLC_SDD_v0.03..等以此類推

## 🎯 核心任務與邊界條件
請將 AISDLC-SDD 的「規格先行閘門 (SCG)」、「Rule 9 強制防護」與 AutoClaude 的「多步驟狀態機」、「Minimax 修正大腦」完美融合。
- **架構紅線**：嚴格遵守 AutoClaude 的微核心架構 (`core/ports/` 介面定義，`infra/adapters/` 實作，橫切關注點以 `plugins/` 處理)。絕對禁止破壞 `import-linter` 的 7 條契約。
- **狀態管理**：保留 AutoClaude 的 `PlaybookRunner` 作為主狀態機，將 AISDLC-SDD 的 10 個場景 (Scenarios) 與文件生成流程，封裝為可動態注入的 Playbook Steps。
- **測試與驗證工具**：在進行整合驗證時，若需對比不同模型後端（如切換至本地 Qwen 或外部 API）的執行穩定度與生成品質，請直接運用 `cc-switch` 工具進行 Claude Code CLI 的快速切換測試，以加速驗收流程。

## 🧠 鏈式思考拆解 (Chain of Thought Execution)
請嚴格遵循以下四個階段進行思考與實作，在每個階段完成前，禁止跳躍至下一階段：

### 階段一：實體映射與介面設計 (Mapping & Interfaces)
1. **分析**：思考 AutoClaude 的 `global_goal` 如何驅動 AISDLC 的核心 Agent (如 `sa-analyst` 與 `sd-architect`)？
2. **實作策略**：設計一個掛載於 EventBus 的 `GoalSynthesisPlugin` 擴展或獨立的 Adapter。請明確列出你需要依賴或實作哪些 Port 介面 (如 `EvaluatorPort` 或 `BrainPort`)。

### 階段二：動態路由與任務轉換 (Dynamic Routing)
1. **分析**：如何將產出的 SDD (MD/YAML 模板) 無縫轉譯為 AutoClaude 的 `PlaybookTask`？
2. **實作策略**：設計 `SddToPlaybookAdapter`。該元件必須能解析 SDD 的「Contract Test Spec」，並自動綁定對應的 `expected_output_regex` 與雙重驗證用的 `evaluator_command`。

### 階段三：雙重防護網整合 (Governance & Escapement)
1. **分析**：當程式碼實作違反了 SDD 契約 (Rule 9)，系統該如何安全停機或觸發自演化修正？
2. **實作策略**：擴充 AutoClaude 的 `ErrorClassifier`，新增 `SDD_CONTRACT_VIOLATION` 錯誤類別。將 AISDLC 的 `SessionStart` / `PreToolUse` Hook 防護轉化為 EventBus 的攔截機制，並將例外拋給 `MinimaxEvolver` 進行 AI 驅動的修正。

### 階段四：CI 平價與形式化驗證 (Verification)
1. **分析**：如何確保「地端綠 ⇒ 雲端綠」，並維持 TLA+ 形式化軌道的雙源一致性？
2. **實作策略**：整合兩者的單一真相源 CI 腳本 (`scripts/ci-gate.sh`)，確保在提交任何代碼變更前，皆能於本地端 Docker 容器內通過 `pytest` 離線測試與 `arch_fitness --strict` 結構檢查。

## 🛡️ 自我驗證與檢核機制 (Self-Correction & Output Format)
在你撰寫或修改任何實質的 Python 程式碼之前，**必須**先輸出一個 `<Architecture_Design_Review>` 區塊。

在此區塊中，請逐一回答以下檢核問題：
1. **架構純潔性**：本次修改是否創造了 God-object？是否有確保 `playbook_runner.py` 維持 Thin Facade 的無業務邏輯原則？
2. **持久化相容**：跨步驟演化的新狀態是否已正確寫入 `PlaybookCheckpoint`？DAL 三後端 (yaml_only/both/db_only) 的零停機切換特性是否被維持？
3. **安全防護網**：當觸發 Playbook 中的 `CONDITIONAL` 時，內建的白名單正則驗證是否能正確攔截鏈式攻擊向量？

確認上述邏輯自洽且無架構衝突後，再逐步為我輸出重構的目錄結構與關鍵的 Python 實作腳本。

## 輸出
1.將以上產出執行計畫:AISDCL_Agent\docs\04_planning\AutoSDD_improving_0X.md
2.以此Prompt為範本, 請幫我設計可以以下目標的迭代Prompt, 讓我可以用此Prompt進行迭代精進
  a.在「零退化 (Zero-Regression)」的絕對前提下，完成 AISDLC-SDD 框架與 AutoClaude 多步驟 Playbook 引擎的深度整合，並維持現有 2,732 項測試的綠燈基線。
  b.此專案開發的過程中, 馬上利用D:\CursorProject\AISDCL_Agent\AISDLC_SDD\AISDLC_SDD_v0.01專案中的流程開發, 並且設計演化AISDLC_SDD_v0.02,AISDLC_SDD_v0.03..等以此類推
3.另有其他輸出文件, 請放入docs, 參考docs目錄結構

為確保執行品質與AutoSDD_improving_0X.md內容, 請確實派出Architect / SA SD / QA 專家整體考量審查, 與目前系統現況進行比對, 採完全不信任 zero-trust audit 全面驗證和"修復方向是否正確", 看看nightly程式是否正確 and 執行過程與結果是否正確!
有問題馬上請派另一個Agent(Architect/SA SD/QA 全能)專家進行修復相關程式與文件「所有問題"文件問題"和"技術問題"必須徹底全部修復才能算完成」! 
再經QA專家審議修完是否有符合"原設計功能"或若有破壞收斂即不通過須馬上進行修改再進行QA!
全部符合上述PASS才核准通過!


規劃AISDLC自動開發Agent Console UI PRD
=====================================
AISDLC自動開發Agent Console UI
=====================================
要設計一個AI Agent自主開發系統, 目前已經有以下三個模組, AutoClaude模組,AISDLC_SDD模組,AISDLC Agent模組:
1.AutoClaude模組:Claude Code 多步驟 Playbook 自動執行引擎，以狀態機管理執行流程、重試、Token 限制與錯誤升級。 Level 5 自治系統：具備動態突變、自演化、目標對齊、跨 Session 持久化、元學習等高階閉環能力。 微核心化架構：Hexagonal Architecture（9 Ports）+ Kernel/EventBus + 13 Plugin + DAL 三後端（File / InMemory / PostgreSQL）。
2.AISDLC_SDD模組:建立一套「AI 規格驅動開發 (AI SDD)」軟體架構隨 AI 演進的自動化機制系統。請深度剖析我目前的系統設計，驗證其是否具備「圖靈完備的自動化閉環」能力。你的終極目標是協助我將此系統進化為 Level 10 自治開發流程。
3.AISDLC Agent模組: 整合兩者的**自動化開發 Agent**

## 🌟 系統終極目標（北極星，每輪不變——所有迭代向此對齊）
1. **AutoClaude＝多步驟 Playbook 自動執行引擎**：以狀態機管理執行流程／重試／Token 限制／錯誤升級，
   更關鍵的是能**驅動 `AISDLC_SDD_v0.0X` 進行相關軟體開發**。定位 **Level 5 自治系統**（動態突變／
   自演化／目標對齊／跨 Session 持久化／元學習等高階閉環）；**微核心化架構**：Hexagonal（Ports）+
   Kernel/EventBus + Plugins + DAL 三後端（File / InMemory / PostgreSQL）。
   〔Port／Plugin／後端具體數量一律以階段一實測為準，勿引用宣稱值——原始陳述 9 Ports/13 Plugin
   與現況不符，禁寫死〕
2. **AI 規格驅動開發 (AI SDD)**：構建讓軟體架構隨 AI 演進的自動化機制。每輪須**深度剖析並驗證系統
   是否具「圖靈完備的自動化閉環」**能力，終極目標＝進化為 **Level 10 自治開發流程**——利用 Claude Code
   建立具**自我修正能力的動態工作流 (Dynamic Workflow)**，用於深度重構與優化 `AISDLC_SDD_v0.0X`。
3. **完美協調溝通機制**：AutoClaude 利用 `AISDLC_SDD_v0.0X` 進行軟體開發，建立兩者間雙向橋接，
   成為端到端**自動化開發 Agent**（A 軌整合即直接服務此目標）。

以下是要新增加的模組, 請撰寫以下Agent Console UI PRD
====================================================
1.專案控管:三層管理架構
a.專案管理(CRUD):專案名稱, 專案執行路徑, 專案通過標準
一個專案可以有多項目標, 專案說明描述(支援.md格式), 可以列出底下多少目標(只顯示標題), 目標底下多少任務(只顯示標題)
b.目標管理(CRUD):CURD, 一個目標可以多項任務, 說明描述(支援.md格式), 目標通過標準
c.任務管理(CRUD):CURD, 一個任務與任務說明描述(支援.md格式), 任務通過標準
2.BRD, PRD ==> 產生專案,目標,任務
3.專案執行:(不知如何設計)
4.專案監控:(不知如何設計)
5.系統參數設定: 系統所有參數, 例如:模型URL,Token

Agent Console UI 技術棧如下
==========================
| 層級 | 技術 | 備註 |
|------|------|------|
| 前端 | Next.js 16 (App Router) + TypeScript + Tailwind CSS + shadcn/ui 搭配 Tremor (處理數據圖表) | 
| 後端 | Spring Boot 3.2 (Java 21) + Clean Architecture + DDD | 
| 資料庫 | PostgreSQL 18 | 

詳細規劃整體可以部屬到Docker可以運作, 並且規劃如何將Docker的PostgreSQL 18進行高使用性備份

PS: 以上PRD, 請輸出docs\01_requirements\Agent_ConsoleUI_PRD.md輸出

為確保Agent_ConsoleUI_PRD.md內容品質, 請確實派出Architect / SA / SD / QA 專家整體考量審查, 與目前系統現況進行比對, 採完全不信任 zero-trust audit 全面驗證和"修復方向是否正確", 看看nightly程式是否正確 and 執行過程與結果是否正確!
有問題馬上請派另一個Agent(Architect/SA/SD/QA 全能)專家進行修復相關程式與文件「所有問題"文件問題"和"技術問題"必須徹底全部修復才能算完成」! 
再經QA專家審議修完是否有符合"原設計功能"或若有破壞收斂即不通過須馬上進行修改再進行QA!
全部符合上述PASS才核准通過!


問題:
===========================================================
目標:
1.AutoClaude 是多步驟 Playbook 自動執行引擎，以狀態機管理執行流程、重試、Token 限制與錯誤升級, 更重要的是可以控制「AISDLC_SDD_v0.0X」進行相關的軟體開發。 Level 5 自治系統：具備動態突變、自演化、目標對齊、跨 Session 持久化、元學習等高階閉環能力。 微核心化架構：Hexagonal Architecture（9 Ports）+ Kernel/EventBus + 13 Plugin + DAL 三後端（File / InMemory / PostgreSQL）。
2.我正在構建一套能讓軟體架構隨 AI 演進的自動化機制「AI 規格驅動開發 (AI SDD)」系統。請深度剖析我目前的系統設計，驗證其是否具備「圖靈完備的自動化閉環」能力。你的終極目標是協助我將此系統進化為 Level 10 自治開發流程。利用 Claude Code 建立一個具備自我修正能力的動態工作流程 (Dynamic Workflow)，用於深度重構與優化「AISDLC_SDD_v0.0X」。
3.AutoClaude可以利用「AISDLC_SDD_v0.0X」進行相關的軟體開發, 建立兩者間完美的協調溝通機制, 成為自動化開發Agent!

請派Agent(Architect/SA/SD/QA)專家進行深入分析, 目前這個專案若要整合一個開源Agent架構, 以下哪一個的Agent架構(或是複合式架構兩種以上), 最適合我現在現有的系統架構, 請詳細深入分析!
1.Aider
2.OpenHands
3.Codex CLI
4.LangGraph
5.AutoGen
6.其他

指揮官提出要解決事項:請確實派出Architect / SA / SD / QA 專家整體考量審查整合,
1.請將兩附件內容, 整合至本專案的相對模組中(除了剛剛評估過的LangGraph除外)!
2.功能若有重疊, 以Agent_ConsoleUI_PRD.md為主
3.若需要修改AutoSDD_Iteration_Prompt_Template.md, 請一併處理!

ConsoleIU_頁面設計已經放入以下路徑中, D:\CursorProject\AISDCL_Agent\docs\01_requirements\01.UI_Design\Design_ConsoleUI
1.請注意在程式套用的過程中, 把頁面分做四個部分1.Top,2.Tools(左區功能Bar), 3.Content(內容區), 4.Bottom(底部)
2.1.Top, 2.Tools(左區功能Bar), 4.Bottom(底部), 可以設計成共用結構, 當有需要更動時, 這三個區塊因為共用, 只需要改一個地方, 方面維護

幫我在AISDLC_SDD建立一個專職的Agent, 主要是可以將我的PRD轉成詳細的專案,playbook.yaml
1.產生 專案 ==> 目標 ==> 任務 的playbook.yaml
2.這個playbook.yaml, 可以搭配Autoclaude and AISDLC_SDD進行PRD完整產品開發

目前需確認或解決問題
===================
1.AutoClaude的驗證測試Nightly是否有繼續?
2.AutoClaude中SD_Improving_09.md 是否已經執行完畢? 是否可以繼續推進?
OK_3.缺陷帳本太大（466KB）如何解決?
OK_3.AISDLC_SDD_v0.xx中的agent\* (根目錄三個檔案, Core and specialized兩目錄)請全面修復所有的Agent是否都合SDD與目前的架構, 請全面請Architect / SA / SD / QA 專家檢視, 若不適當, 請派Architect/SA/SD/QA 全能專家進行修復
OK_4.AISDLC_SDD_v0.xx中.claude中的hools and skills是否都可以完整被所有模組使用到? 請完整徹底驗證, 請問該如何進行完善的架構調整? 請全面請Architect / SA / SD / QA 專家檢視, 若不適當, 請派Architect/SA/SD/QA 全能專家進行修復
OK_5.AISDLC_SDD_v0.xx中.claude中的hools and skills,  請全面確認所有的hools and skills的內容是否都合SDD與目前整體系統架構? 請完整徹底驗證! 若不符合, 請問該如何進行完善的架構調整? 請全面請Architect / SA / SD / QA 專家檢視, 若不適當, 請派Architect/SA/SD/QA 全能專家進行修復

請驗證AutoSDD_Iteration_Prompt_Template.md與執行以下AISDLC_SDD_v0.01專案進行自我迭代開發為目標, 來修改驗證AutoSDD_Iteration_Prompt_Template.md
1.可否依照目前的D:\CursorProject\AISDCL_Agent\AISDLC_SDD\AISDLC_SDD_v0.01專案 進行自我迭代開發, 行進中並記錄缺點Bug進行改進
2.此專案開發的過程中, 馬上利用D:\CursorProject\AISDCL_Agent\AISDLC_SDD\AISDLC_SDD_v0.01專案中的流程開發, 並且設計演化AISDLC_SDD_v0.02,AISDLC_SDD_v0.03..等以此類推

為確保執行品質與AutoSDD_improving_0X.md內容, 請確實派出Architect / SA / SD / QA 專家整體考量審查, 與目前系統現況進行比對, 採完全不信任 zero-trust audit 全面驗證和"修復方向是否正確", 看看nightly程式是否正確 and 執行過程與結果是否正確!
有問題馬上請派另一個Agent(Architect/SA/SD/QA 全能)專家進行修復相關程式與文件「所有問題"文件問題"和"技術問題"必須徹底全部修復才能算完成」! 
再經QA專家審議修完是否有符合"原設計功能"或若有破壞收斂即不通過須馬上進行修改再進行QA!
全部符合上述PASS才核准通過!



===========================================================
請協助解決以下問題，詳細規劃需要的執行項目，注意每個項目都不可以遺漏，完成後逐項打勾確認！
除非必要讓我參考的報告，否則不必產出報告(若有後續Next Action, 需要產出報告)。若有修改，更新相關必要文件即可。請將輸出部分簡潔清楚就好，節省Token！

問題： 

## 已經執行完 AutoSDD_improving_23.md 和 AutoSDD_ZeroTrust_Audit_23.md 等相關項目


參考資訊:
✅ AutoSDD improving_23 結案 — B 軌 XAI 深化：Folding 降維
Dr. Alan 結案判定：准予結案（tag v2026.06.17-20，直推 main）

本輪定位與重大發現
柱：B 軌（手腳 AISLDC_SDD dogfooding）+ XAI Turn 疊加；Copy-on-Evolve v0.13→v0.14。
🔴 重大 Zero-Trust 發現：模板〈XAI Turn〉範例 driver「ACT-159/R-9.37 建視覺化儀表板」在 v0.13 已完成式（_26.md §D 2026-06-06 收官）。我拒絕重做已結案工作，重新定範至其真實 delta — _26.md 列入、§D 收官以 pagination 替代而靜默未交付的 Folding 降維。
交付（W-23-1，隸屬既有 R-9.37，不取新 ACT/Rule）
fold_topology() 純函式：把窗內「結構無趣的內部簡單鏈」塌縮為 [+k more] 超節點，永不折 entry/critical/分支/匯聚/sink。
核心張力解法：folding 故意「畫得比真圖簡單」＝PY-2 要攔的視覺欺騙 → 做成可稽核誠實收縮（超節點公開 folds=[成員]，verify_topology_consistency 擴充五道：真鏈/良基/不藏 entry/expanded 窗格錨定/商圖邊比對）。
fold 預設 OFF＝v0.13 逐位元行為（零退化）；chaos VISUALIZATION_FOLD_DRIFT_FLAP；test +13。
零退化驗證矩陣（全綠）
檢查	實測
AISLDC_SDD v0.14	1593 passed / 0 failed（v0.13 1580+13）
chaos	34 passed，bounded_ratio==1.0（含新 FOLD_DRIFT）
ci-gate 雙軌	v0.01:1478 / v0.14:1593 / scripts:27，arch_fitness fail=0，FF-17 自證入閘
AutoClaude	3112 passed / 0 failed（持平基線） + lint 全 kept（契約條數 SSOT＝AutoClaude/.importlinter；本列其餘數字是**該輪的量測值，不是現況**）
五軌 TLC	免觸發（formal *.tla/*.cfg 逐位元零差異）
潔淨度	git add -A -n 853 零 runtime 漏網
審查閉環（三鏡全 OVERALL PASS）
Architect：架構純潔/對抗分離/additive/五軌免觸發 — 無 BLOCKER。
SA-SD：文件 vs 實況逐項一致、缺陷帳誠實 — 2 條 P3 已修（RTM 命名、ID_REGISTRY stale ref）。
QA（對抗）：20 個攻擊向量全數守住、無繞過破口（含藏 critical/偽 rank/漏畫商圖邊/縮窗）。
突變回歸鎖驗證：停 f1 degree 檢查 → 2 測試轉紅 → 還原 50 passed（回歸鎖非空轉）。
缺陷帳（全 fixed@improving_23）
DEF-23-001（CHANGELOG 口徑）、DEF-23-002（_26/_27 歸檔+ref）、DEF-23-003（.gitignore v0.14 block）、DEF-23-004（RTM 命名對齊）。

因為這輪中斷兩三次
為確保執行品質與AutoSDD_improving_23.md執行項目都有執行, 請確實派出Architect / SA / SD / QA 專家整體考量審查, 與目前系統現況進行比對, 採完全不信任 zero-trust audit 全面驗證和"修復方向是否正確", 看看nightly程式是否正確 and 執行過程與結果是否正確!
有問題馬上請派另一個Agent(Architect/SA SD/QA 全能)專家進行修復相關程式與文件「所有問題"文件問題"和"技術問題"必須徹底全部修復才能算完成」! 
再經QA專家審議修完是否有符合"原設計功能"或若有破壞收斂即不通過須馬上進行修改再進行QA!
全部符合上述PASS才核准通過!

以上執行完後, 
1.以日期Timestamp為標籤(例:v2026.06.01-0x), 幫我commit+Push到github wuweihungmobile/AISDCL_Agent
2.開發改進中, 是否有發現AISDLC_SDD_v0.01開發流程有問題, 請立即記錄準備於下一輪進行改善


2.請依照4 軸並行新規劃告訴我下一步的執行檔案與執行大綱,並評估是否有收斂?目前此專案成熟度?!
3.請問SD09_Execution_Guide.md還有哪些還沒執行? 還有哪些可以繼續安排改進? 要如何快速執行完SD09_Execution_Guide.md往下階段前進! 

1.確認 AutoClaude_Improving_012.md 凍結
2.繼續詳細執行 AutoClaude_Improving_012.md and 以及Improving012_Phase0_NextAction.md, AutoClaude_Improving_012相關資訊與文件, 並確認那些項目沒有完成, 繼續執行!
3.若有需要確認, 請評估選項, 以互動方式我會進行回覆!





===========================================================
請幫我寫完整的安裝部屬手冊, 放入docs\AISDLC_Agent_UserGuide.md
1.如何安裝部屬AISDLC_Agent
2.如何啟動AISDLC_Agent
3.如何使用AISDLC_Agent
4.如何AISDLC_Agent關閉



已經執行以下項目:

三項編輯皆已寫入。整合完成，逐項確認：

執行項目確認



為確保執行品質與docs/04_planning/AutoSDD_Iteration_Prompt_Template.md文件內容符合設計架構與目的, 可以朝系統終極目標進行精進（北極星，每輪不變——所有迭代向此對齊）, 請確實派出Architect / SA / SD / QA 專家整體考量審查, 與目前系統現況進行比對, 採完全不信任 zero-trust audit 全面驗證和"修復方向是否正確", 看看nightly程式是否正確 and 執行過程與結果是否正確!
有問題馬上請派另一個Agent(Architect/SA/SD/QA 全能)專家進行修復相關程式與文件「所有問題"文件問題"和"技術問題"必須徹底全部修復才能算完成」! 
再經QA專家審議修完是否有符合"原設計功能"或若有破壞收斂即不通過須馬上進行修改再進行QA!
全部符合上述PASS才核准通過!