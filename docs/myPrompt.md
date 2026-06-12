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




問題:
===========================================================
請驗證AutoSDD_Iteration_Prompt_Template.md與執行以下AISDLC_SDD_v0.01專案進行自我迭代開發為目標, 來修改驗證AutoSDD_Iteration_Prompt_Template.md
1.可否依照目前的D:\CursorProject\AISDCL_Agent\AISDLC_SDD\AISDLC_SDD_v0.01專案 進行自我迭代開發, 行進中並記錄缺點Bug進行改進
2.此專案開發的過程中, 馬上利用D:\CursorProject\AISDCL_Agent\AISDLC_SDD\AISDLC_SDD_v0.01專案中的流程開發, 並且設計演化AISDLC_SDD_v0.02,AISDLC_SDD_v0.03..等以此類推

為確保執行品質與AutoSDD_improving_0X.md內容, 請確實派出Architect / SA SD / QA 專家整體考量審查, 與目前系統現況進行比對, 採完全不信任 zero-trust audit 全面驗證和"修復方向是否正確", 看看nightly程式是否正確 and 執行過程與結果是否正確!
有問題馬上請派另一個Agent(Architect/SA SD/QA 全能)專家進行修復相關程式與文件「所有問題"文件問題"和"技術問題"必須徹底全部修復才能算完成」! 
再經QA專家審議修完是否有符合"原設計功能"或若有破壞收斂即不通過須馬上進行修改再進行QA!
全部符合上述PASS才核准通過!

2.AutoClaude的驗證測試Nightly是否有繼續?

下一步：依計畫 🔴 人工確認點，待您確認 AutoSDD_improving_01.md 凍結後即可啟動 W1（spec_source.py）實作；屆時直接用迭代範本以 {{N}}=02 開啟第二輪即可。

2.建立一個 dynamic workflow 來請詳細執行 AutoSDD_improving_01.md and 以及AutoSDD_improving_01相關資訊與文件
===========================================================
請協助解決以下問題，詳細規劃需要的執行項目，注意每個項目都不可以遺漏，完成後逐項打勾確認！
除非必要讓我參考的報告，否則不必產出報告(若有後續Next Action, 需要產出報告)。若有修改，更新相關必要文件即可。請將輸出部分簡潔清楚就好，節省Token！

問題： 
1.確認 AutoSDD_improving_01.md 凍結
2.請詳細規劃執行 AutoSDD_improving_01.md and 以及AutoSDD_improving_01相關資訊與文件
3.若有需要確認, 請評估選項, 以互動方式我會進行回覆!





為確保執行品質與AutoSDD_improving_01.md執行項目都有執行, 請確實派出Architect / SA SD / QA 專家整體考量審查, 與目前系統現況進行比對, 採完全不信任 zero-trust audit 全面驗證和"修復方向是否正確", 看看nightly程式是否正確 and 執行過程與結果是否正確!
有問題馬上請派另一個Agent(Architect/SA SD/QA 全能)專家進行修復相關程式與文件「所有問題"文件問題"和"技術問題"必須徹底全部修復才能算完成」! 
再經QA專家審議修完是否有符合"原設計功能"或若有破壞收斂即不通過須馬上進行修改再進行QA!
全部符合上述PASS才核准通過!

以上執行完後, 
1.以日期Timestamp為標籤(例:v2026.05.01-0x), 幫我Push到github wuweihungmobile/AISDCL_Agent, 並且進行Merge main!
2.開發改進中, 是否有發現AISDLC_SDD_v0.01開發流程有問題, 請立即記錄準備於下一輪進行改善


2.請依照4 軸並行新規劃告訴我下一步的執行檔案與執行大綱,並評估是否有收斂?目前此專案成熟度?!
3.請問SD09_Execution_Guide.md還有哪些還沒執行? 還有哪些可以繼續安排改進? 要如何快速執行完SD09_Execution_Guide.md往下階段前進! 







===========================================================
✅ 結案報告 — 第二輪全部 PASS，核准通過
您兩個問題的答案
1. 可否依 v0.01 進行自我迭代開發、行進中記錄缺點 Bug 改進？——可以，且框架已內建官方機制，無需另造。 逐層開檔驗證（證據在 AutoSDD_ZeroTrust_Audit_01.md §6.2）：

自舉：SessionStart hook 自動呼叫 FSMRuntime.bootstrap()（session_start.py:74），project 由 SDD_PROJECT 環境變數指定，FSM 狀態檔落 build/reports/fsm/，decision_trace 自動留痕全部狀態轉換。
場景：對框架自身迭代走 Brownfield（既有系統改進），轉場依 SCENARIO_TRANSITION_GUIDE.md。
缺陷記錄與回流：v0.01 已有五層回流鏈（production inbox / decision_trace / drift / FPL→SLV / meta_halt）+ Phase J SPEC-PATCH + RFC 慣例（build/planning/active/）+ 官方 DEFECT-CLASSIFICATION P0~P3 分級。
邊界釐清：build/、data/ 是可寫運行工作區（官方機制本就寫此處）；框架本體（agent/governance/workflow/tools/.claude）凍結，修改走 Copy-on-Evolve 落 v0.02。
2. 立即用 v0.01 流程開發 + 演化 v0.02/v0.03…？——已寫入範本：B 軌 SCG-05 載體映射 + Copy-on-Evolve 條款（v0.0(X+1) + EVOLUTION_LOG + 五軌 TLC 義務）+ improving_01 §6 的 v0.02 Phase Z（ACT-162171）規劃。

範本改版內容（已通過審查閉環）
AutoSDD_Iteration_Prompt_Template.md 升級為雙軌迭代：A 軌（整合 W 項）+ B 軌（🐶 自我迭代模式），新增可寫/凍結邊界表、啟動三步驟（附程式碼錨點）、缺陷記錄紀律（DEF-{{N}}-{seq} 格式、發現即記）、四路分流表（SPEC-PATCH / FPL→SLV / RFC / A 軌 W 項）、B 軌結案條件、階段一硬停機閘、內嵌零退化矩陣。

並當場實踐 dogfooding：新建缺陷帳本 AutoSDD_Defect_Log.md，把已發現的 5 筆缺陷 seed 入帳（RULES_INDEX 表頭過期、run_tlc.sh 僅 2 軌、tools/ 缺 __init__.py、ci.yml pg-e2e 每晚雙跑、原始 Prompt 假設偏差——最後一筆已標 fixed）。

審查閉環紀錄
關卡	結果
Architect 審查	CONDITIONAL PASS：2 WARN（hooks 描述精度、矩陣未內嵌）
SA-SD 審查	範本 12/12 機制宣稱逐項開檔屬實；4 缺口（帳本不存在為首）
QA 審查	agent 因 API 內容過濾中斷，檢核項併入最終複審補齊（已誠實記載於審計 §6.3）
全能修復	FIX-1~8 全數落地，每項先複驗再修文；含檔名對齊（Audit_001→Audit_01，消除與 {{N}} 編號制的首輪斷鏈）
QA 最終複審	PASS：A 區 8/8（所有錨點開檔比對無一失準、5 筆 seed 證據屬實）、B 區 5/5（一致性/路徑/繁中/nightly/目標覆蓋）、C 區零退化實測重跑 2732 passed / 122 skipped / 0 failed
Nightly 再抽查仍屬實（fsm-chaos cron 0 2 + -m chaos；AutoClaude 2 條 active cron），本輪零程式碼修改、零基線退化。下一輪可直接以範本 {{N}}=02 啟動：A 軌做 W1（spec_source.py），B 軌同步開 FSM 實例並處置帳本中 4 筆 routed 缺陷。