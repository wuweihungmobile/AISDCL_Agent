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

## 已經執行完 AutoSDD_improving_11.md 和 AutoSDD_ZeroTrust_Audit_11.md 等相關項目

參考資訊:
階段四（CI 平價，全項綠）

AutoClaude 改動後複測 3075 / 0 failed（零改動持平）
雙軌 ci-gate exit 0：v0.01:1478 / v0.05:1499，FF-17 報告 ff17-ok 自證最新版 v0.05 自動入閘
v0.05 not-chaos 1499 passed、arch_fitness 87 passed、-k ff17 5 passed
五軌 TLC N/A（零 _HAPPY_PATH/*.tla 變更，Rule 9.18.1 不啟動）
多專家 Zero-Trust 三鏡審查 — 初審技術 PASS → 複審 FAIL（文件誠實性 + Copy-on-Evolve 潔淨度）→ 即修後複驗 PASS
獨立 agent 親跑重驗，親手反向實驗證實 FF-17 真鑑別力（monkeypatch 指向寫死單版 → 確實 structural fail）；確認 v0.01~v0.04 源碼零改動。**複審揭露缺口**：鏡三 QA 潔淨度查證僅涵蓋 .pyc，未涵蓋 build/reports（173 runtime 取證檔）+ arch-fitness.json，而此二類將隨 v0.05 commit 入庫。即修＝AISDLC_SDD/.gitignore 新增 v0.05 區塊排除（would-add 1013→839），ci-gate 雙軌 1478/1499 不變複驗。

缺陷帳本
DEF-10-002 → fixed@improving_11（兩子項齊備）
新記 DEF-11-001（P3）→ fixed@improving_11（即清理子項）/ routed v0.0Y（通用 helper+SOP 子項）：Copy-on-Evolve cp -r 缺排除 runtime 產物之 helper；複審發現 v0.05 build/reports + arch-fitness.json 未被 .gitignore 涵蓋將入 commit，本輪即以 .gitignore 排除（1013→839），通用 copy_on_evolve.sh helper 留 v0.0Y
四件套產出
AutoSDD_improving_11.md
AutoSDD_ZeroTrust_Audit_11.md
AutoSDD_Defect_Log.md（DEF-10-002→fixed、新增 DEF-11-001）
AISDLC_SDD_v0.05/（FF-17 + 測試 + EVOLUTION_LOG + CHANGELOG）+ 範本 (f)


為確保執行品質與AutoSDD_improving_11.md執行項目都有執行, 請確實派出Architect / SA SD / QA 專家整體考量審查, 與目前系統現況進行比對, 採完全不信任 zero-trust audit 全面驗證和"修復方向是否正確", 看看nightly程式是否正確 and 執行過程與結果是否正確!
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