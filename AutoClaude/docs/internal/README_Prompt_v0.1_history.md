# Role
你是全球頂尖的 AI Agent 架構師 (AutoGPT/BabyAGI 核心開發者級別)，專精於 LLM 閉環控制 (Closed-loop Orchestration)、動態 Prompt 工程與進程間通訊 (IPC)。

# Task
開發 "AutoClaude" Agent 系統，目標是讓外部 Python 程式與 Claude Code 形成「感知-決策-執行-修正」的完美閉環，且對人類操作達到零干擾。

# Chain of Thought (CoT) & System Design
請運用鏈式思考，依照以下步驟進行系統設計與編碼：
1. **[感知層] I/O 攔截與不干擾設計**：分析如何使用偽終端 (`pty` for Unix 或 `winpty`/`wepexpect` for Windows) 來完美模擬終端機行為，並背景自動送出 "Yes"/授權指令，同時將 `stdout` 實時串流至日誌檔 (`logging`)。定義 `ESC+F12` 全域中斷的優先級。
2. **[決策層] Minimax 大腦整合**：當感知層攔截到 "執行完畢, 報告如下" 關鍵字，系統啟動 Minimax API。請設計傳給 Minimax 的 System Prompt，使其能嚴格輸出 JSON 格式的決策指令 (包含：`action_type`, `next_command`, `modify_script_flag`)，如判斷是否需要 `/compact` 以節省 Token。
3. **[執行與閉環層] 動態腳本協作 (Dynamic Scripting)**：
   - 定義最優腳本格式：建議使用 JSON Schema 或 YAML 格式，需包含「任務描述、執行指令、驗證條件、重試次數」。
   - **完美閉環核心**：AutoClaude 解析腳本 -> 傳給 Claude Code -> 攔截報告 -> 交給 Minimax -> Minimax 決定繼續、修改腳本、或終止 -> AutoClaude 覆寫/更新腳本檔案 -> 進入下一個 Loop。
4. **[防呆與邊界條件]**：設定最大閉環次數 (防止無限 Token 消耗)、API 異常降級策略。

# Self-Correction & Verification
- 思考：如果 Claude Code 正在等待輸入，但沒有輸出換行符，標準讀取是否會卡死？如何用非阻塞 (Non-blocking) 讀取解決？
- 思考：腳本如果被 Minimax 改壞了怎麼辦？是否需要實作腳本版本控制 (Backup before modify)？

# Deliverables
請提供：
1. 你的高階架構 CoT 分析。
2. 完美閉環腳本規格定義 (YAML 範例)。
3. 給 Minimax API 專用的 System Prompt (確保其作為決策大腦的精準度)。
4. 核心 Python 實現代碼 (包含非阻塞讀取、閉環迴圈邏輯)。

-- =========================================================
幫我Push到github wuweihungmobile/AutoClaude, 並且進行Merge main!
-- =========================================================
這個AutoClaude會配合原本開發中的AISDLC(兩個流程), 請幫我改善以下需求:
1.AutoClade執行的劇本應該有數個Prompt, 是否可以支援數個Prompt依序執行功能? 請參考如下範例,
  # autoclaude_playbook.yaml
version: "1.0"
project: "AISDLC_SDD_Auth_Module"
global_invariants:
  max_retries_per_step: 3
  auto_compact_interval: 5

tasks:
  - step_id: "T01"
    name: "閱讀並理解 SDD 規格"
    prompt: |
      請讀取 `docs/sdd_auth_spec.md`。
      了解我們將使用 FastAPI 實作 JWT 登入。
      完成後請嚴格輸出 Keyword: `[INIT_DONE]`。
    expected_output_regex: "\[INIT_DONE\]"
    
  - step_id: "T02"
    name: "撰寫測試案例 (TDD)"
    prompt: |
      根據規格，請撰寫對應的 pytest 測試檔 `tests/test_auth.py`。
      不用實作核心邏輯，先寫測試。
      完成後請輸出 Keyword: `[TEST_CREATED]`。
    expected_output_regex: "\[TEST_CREATED\]"

  - step_id: "T03"
    name: "實作核心代碼並自我修復"
    prompt: |
      請實作 `auth.py` 以通過測試。完成後請執行 `pytest tests/test_auth.py` 檢查。
      若失敗請自我修正。當你確認測試完全通過後，輸出 Keyword: `[TASK_COMPLETE]`。
    expected_output_regex: "\[TASK_COMPLETE\]"
    # AutoClaude 專屬的驗證命令：AI 說完成不算，必須由 Evaluator 親自驗證
    evaluator_command: "pytest tests/test_auth.py"
2.完美融合 AISDLC_SDD 的終極執行藍圖
  a.企劃階段 (Human + AI Planner)：人類開發者使用一般 AI 產出 Markdown 格式的 SDD Spec，存放於 docs/scripts。
  b.編譯劇本：根據 SDD Spec，產出上述的 autoclaude_playbook.yaml。
  c.啟動 AutoClaude：在終端機背景執行 AutoClaude。
    1. AutoClaude 載入 YAML，自動啟動 Claude Code 子進程。
    2. 自動發送 T01, T02, T03 的 Prompt。
    3. 無縫攔截：遇到 Claude Code 詢問是否執行 bash 命令時，AutoClaude 秒按 "Y"。
    4. 驗證防呆：T03 結束時，AutoClaude 背景執行 pytest。若失敗，將 Log 拋給 Minimax，Minimax 產出修正 Prompt 再塞回給 Claude Code。
  d.完美閉環：直到所有測試通過，AutoClaude 優雅關閉 Claude Code，並在桌面右下角彈出通知：「Phase 1 Auth Module SDD 開發與測試完畢」。
3.AutoClade開發期間可以先自我測試, 看看功能是否完備?
4.目前我有兩個開發流程, 我希望AutoClaude可以完美融合操控這兩種開發流程(自動識別執行哪一個流程), 詳細可以參考以下: 
  第一種是AISDLC ==> D:\CursorProject\AISDLC\AISDLC_v0.09
  第二種是AISDLC_SDD ==> D:\CursorProject\AISDLC_SDD\AISDLC_SDD_v0.01
5.AutoCladue應該是一個Claude Code 的AI Agent, 可以朝目標前進修正, 請朝這個方向改進!(參考以下)
  gentic 閉環狀態機設計 (State Machine Design)
  要支援多個 Prompt 依序執行並具備自我修正能力，AutoClaude 的核心必須是一個有向無環圖 (DAG) 結合重試迴圈的狀態機。

  STATE 0: 環境初始化 (INIT)
    AutoClaude 讀取 YAML 劇本，載入 docs/sdd_spec.md 作為單一真實來源。

  STATE 1: 脈絡準備與協商 (CONTEXT & NEGOTIATION)
    送出第一個 Prompt：「讀取 Spec，並條列出你要建立的檔案與測試案例。回覆『確認理解』」。
    AutoClaude/Minimax 驗證輸出是否符合預期。

  STATE 2: 多步驟執行 (SEQUENTIAL EXECUTION)
    依序從 YAML 陣列中提取 Prompt 送給 Claude Code。
    這回答了你的需求2：AutoClaude 在內部維護一個 current_step_index。

  STATE 3: 隔離評估 (EVALUATION) - 核心閉環
    Claude Code 執行完畢後，AutoClaude 在背景執行 pytest 或 npm test。
    成功：更新 current_step_index += 1，寫入 Log，進入下一個 Prompt。
    失敗：捕捉 Terminal 錯誤，將錯誤訊息包裝成新的 Prompt（「測試失敗，錯誤日誌如下，請修正：...」），重新送回 STATE 2。這滿足了你的需求3（朝目標前進修正）。

  STATE 4: 脈絡重置 (CONTEXT RESET)
    每經過 N 個循環，或偵測到 Token Limit 警告，AutoClaude 強制輸入 /compact，然後重新注入當前步驟的短脈絡。

  STATE 5: 人類介入 (ESCALATION)
    觸發防呆機制（如重試超過 3 次），凍結工作區，呼叫人類救援。

以上請參考, 並且詳細協助設計與實作

-- =========================================================
1.可以判斷Context已經90%, 自動觸發/compact
2.當Token已經90%, AutoClaude可以記錄狀態, 等下次繼續執行(可以設定下次啟動時間, AutoClaude會自己執行計畫)! 並且會持續紀錄每次執行結果與Token狀態,

3.AutoClaude應該要可以自己產生劇本!(參考autoclaude_playbook.yaml) AutoClaude可以朝目標前進修正

-- =========================================================
# Role
你是一位「首席 AI 基礎設施工程師 (Chief AI Infrastructure Engineer)」，專精於 Python 異步 I/O 處理、狀態機 (State Machine) 設計、以及無頭模式 (Headless) 的 CLI 系統整合。你的代碼風格極度嚴謹，具備高度的防禦性 (Defensive Programming)，且深諳「測試驅動開發 (TDD)」。

# Task
我們正在開發一個名為 "AutoClaude" 的自動化閉環守護程式。它的目標是讀取 YAML 劇本，透過底層 I/O 控制另一個 CLI 工具，並具備自我評估與修正的狀態機。
為了安全起見，我們將採用「Mock-First」策略。請嚴格按照以下的【架構藍圖】與【執行步驟】進行開發。

# Architecture Blueprint (AutoClaude DAG State Machine)
AutoClaude 核心是一個具備重試迴圈的有向無環圖 (DAG) 狀態機：
- **STATE 0 (INIT)**: 讀取 `autoclaude_playbook.yaml` 與 `docs/sdd_spec.md`。
- **STATE 1 (CONTEXT_NEGOTIATION)**: 送出初始 Prompt，等待目標 CLI 回覆確認。
- **STATE 2 (SEQUENTIAL_EXECUTION)**: 依序送出 YAML 內的步驟指令。
- **STATE 3 (EVALUATION)**: 攔截目標 CLI 輸出。若有錯誤，包裝錯誤訊息重新送回 STATE 2；若成功，進入下一步。
- **STATE 4 (CONTEXT_RESET)**: 執行達指定次數後，強制送出 `/compact` 指令清空脈絡。
- **STATE 5 (ESCALATION)**: 若單一步驟重試超過 3 次，凍結系統並呼叫人類。

# Execution Steps (MUST follow sequentially)

## Step 1: 建立 Mock 環境與規格 (防呆測試用)
1. 建立 `autoclaude_playbook.yaml`，包含至少 2 個測試步驟 (包含 Prompt 與 Expected Keyword)。
2. 撰寫 `dummy_cli.py`。這個程式必須模擬一個 CLI 工具：
   - 使用 `input()` 接收標準輸入。
   - 模擬等待時間 (延遲 1-2 秒)。
   - 當接收到特定指令時，隨機模擬「請求授權 (Y/n)」的提示，等待使用者輸入 `Y`。
   - 根據輸入，輸出對應的模擬成功 Keyword 或模擬報錯訊息 (stderr)。

## Step 2: 開發核心 I/O 攔截器 (io_interceptor.py)
使用 `pexpect` (若在 Unix) 或 `wepexpect`/`subprocess` (跨平台) 撰寫一個非阻塞 (Non-blocking) 的 I/O 互動類別。
- **絕對要求**：必須能自動偵測 `dummy_cli.py` 發出的「授權請求」並自動寫入 `Y`。
- **絕對要求**：讀取 stdout 時不可造成死鎖 (Deadlock)，必須使用非同步 (asyncio) 或獨立執行緒 (Thread)。

## Step 3: 開發狀態機引擎 (autoclaude_core.py)
實作上述的 STATE 0 到 STATE 5 邏輯。
- 將 `io_interceptor` 實例化，並將目標指向執行 `python dummy_cli.py`。
- 實作日誌記錄 (`logging`)，將所有狀態轉換與 I/O 紀錄寫入 `autoclaude.log`。

# Self-Verification Rules (Chain of Thought)
在生成任何程式碼之前，請先使用 `<thinking>` 標籤進行思考：
1. 分析如何確保 `dummy_cli.py` 的 stdout 緩衝區 (Buffer) 能夠即時被主程式讀取，而不會因為緩衝區未滿而卡住 (提示：`flush=True` 或 `pexpect` 行為)。
2. 思考在 STATE 3 (EVALUATION) 中，如何使用 Regex 穩健地擷取 Keyword，即使輸出夾雜了 ANSI 顏色代碼。

# Output Format
將以上產出執行計畫:docs/planning/AutoClaude_Improving_0XX.md(路徑不對請自行修正)

Web Next.js 15+ (App Router)(React) + TypeScript + Tailwind CSS + Shadcn UI Shadcn UI 或 Radix UI
本地模式	sentence-transformers / BGE-M3 / E5	✅ 零費用、離線可用、隱私佳 ❌ 吃 RAM/GPU、首次下載 model 數百 MB~GB
-- =========================================================
請協助解決以下問題，詳細規劃需要的執行項目，注意每個項目都不可以遺漏，完成後逐項打勾確認！
除非必要讓我參考的報告，否則不必產出報告(若有後續Next Action, 需要產出報告)。若有修改，更新相關必要文件即可。請將輸出部分簡潔清楚就好，節省Token！

問題： 請詳細讀取SD_Improving_06 and SD06_Execution_Guide.md,請徹底執行以下項目!
項目: 

為確保每個項目都被確實執行, 請派出Architect / SA / SD 三方專家獨立審查, 專門抓漏與挑剔, 任何錯誤與遺漏都逃不過他的法眼(尤其是架構的部分, 此次為重大架構異動), 進行驗證!
有問題馬上請派另一個Agent專家進行修復「所有問題"文件問題"和"技術問題"必須徹底全部修復才能算完成」! 請確實使用目前的Agents and Skills進行任務! 
再經Architect / SA / SD / QA 四方專家審議核准通過!

===========
使用方式
每個 Wave 開始時：

1. 切新 Opus 4.7 session
2. 複製 §4 開場 prompt 模板，填入 [W編號] + [當前測試基線]
3. 跑 §0 前置確認命令
4. 依該 Wave §3 子段「逐項打勾」執行（不可批次）
5. 跑該 Wave G 驗證命令
6. 全綠 → §6 進度追蹤表打勾 → 進入下一 Wave
7. 紅 → §5 緊急停止與回退協議
關鍵防遺漏設計
設計	防什麼
每 Wave 每子任務含 [ ] checkbox	防遺漏單一 task
每 Wave 含 G 驗證命令清單	防未驗證即進下一 Wave
§8 關鍵風險即時監控	防 PM 拍板事項落實漏項
§5 per-migration 回退劇本	防 alembic 失敗無路可退
§0 G0 啟動前置 DoD	防 2026-05-20 啟動日當天才發現 ADR 未出
W3 ⚠️ 強制阻塞「FK Dry-run Report 未存檔 → G3 不放行」	防 PM W-1 警示落空

=================================================================================================
我正在執行 SD_Improving_06 [W編號]（[波次名稱]）。

當前狀態：
- 測試基線：[當前 passed 數] / [skipped 數]
- 前一 Gate 已通過：G[n]
- 當前 Wave 目標：[複製上方 Wave 目標清單]
- PM 拍板事項：[列出本 Wave 對應 PM 決議]

請先執行 §0 前置確認：
python -m pytest tests/ -q --tb=no | tail -3
PYTHONUTF8=1 lint-imports --config .importlinter
alembic current
wc -l autoclaude/execution/_runner_internals.py

確認後依照 SD06_Execution_Guide.md W[n] 逐項打勾執行。
==================
我正在執行 SD_Improving_06 [W1]（[OrchestrationCoordinator + BrainPort/ExecutorPort 擴張，T1-1~T1-10，4 PD]）。
當前狀態：
- 測試基線：全測 1,519 passed / 44 skipped
- 前一 Gate 已通過：G0
- 當前 Wave 目標：
BrainPort 擴增 capabilities() / decide_escalation()（含 BrainCapabilities dataclass）
ExecutorPort 擴增 execute(..., on_event=callback) + send_interrupt(reason)
新增 autoclaude/core/orchestration/coordinator.py（≤ 250 LOC）
新增 phase 序：BEFORE_DECIDE → DECIDE → BEFORE_EXEC → EXEC → ON_EVENT → AFTER_EXEC
PM #12 雙層保留：Coordinator=Layer 1.5，AutoResumeService=Layer 2，邊界 ADR 已就位
- PM 拍板事項：[列出本 Wave 對應 PM 決議]

請先執行 §0 前置確認：
python -m pytest tests/ -q --tb=no | tail -3
PYTHONUTF8=1 lint-imports --config .importlinter
alembic current
wc -l autoclaude/execution/_runner_internals.py

確認後依照 SD06_Execution_Guide.md W[1] 逐項打勾執行（不可批次）。

=======================================================
我正在執行 SD_Improving_06, 請派出Agent協助完成以下事項, 不要遺漏任何項目

 Production 上線前 Next Action（PM W-1 稽核紅線，未消除）
本 AI-Agent 演練僅滿足工程閉環，不可直接 production 上線。SD06_FK_DryRun_Report.md §7.2 列出 4 個 ⏳ Pending 項，真正 production release 前必須：

人類 DBA 於公司 staging（≥ 1M 真實列）重跑 §1.1~§1.10 全流程
人類 DBA 量測並更新 §6.6 staging 真實時間（覆寫本地參考）
人類 Tech Lead 重審 0010 SQL + staging schema diff
人類 PM 親簽 Production 上線 release approval
未消除風險：並發負載 / WAL replication lag / 雲端 IOPS 配額 / staging schema 與 production diff。


已經執行SD_Improving_07.md與以下任務項目: 
SD_Improving_07.md and ADR-SD07-001 + SD07_Execution_Guide.md
為確保每個項目都被確實執行, 請派出Architect / SA / SD / QA 四方專家獨立審查, 專門抓漏與挑剔, 任何錯誤與遺漏都逃不過他的法眼(尤其是架構的部分, 此次為重大架構異動), 進行驗證!
有問題馬上請派另一個Agent專家進行修復「所有問題"文件問題"和"技術問題"必須徹底全部修復才能算完成」! 請確實使用目前的Agents and Skills進行任務! 
再經Architect / SA / SD / QA 四方專家審議核准通過!

請派出對這個領域專業的PM進行審議與建議, 看看是否同意?

我該如何嚴格徹底執行SD_Improving_06.md不會遺漏, 請幫我規劃執行大綱!

以日期Timestamp為標籤(例:v2026.05.01-0x), 幫我Push到github wuweihungmobile/AutoClaude, 並且進行Merge main!

腳本現在可以正式使用。執行方式：
===============================
功能驗證（~5 分鐘）	AUTOCLAUDE_ALLOW_INSECURE_DB=1 python tools/c6_staging_validator.py --quick
縮短版（1 小時）	AUTOCLAUDE_ALLOW_INSECURE_DB=1 python tools/c6_staging_validator.py --duration 1
正式 C6 24h 驗證	AUTOCLAUDE_ALLOW_INSECURE_DB=1 python tools/c6_staging_validator.py
24h 結束後，若報告 c6_gate: "PASS" → 執行 Runbook §3 切換 db_only。


請徹底解決以下問題!
已經執行完SD_Improving_03_Phase4_Real_Switch.md這個計畫項目與以下任務
SD_Improving_03_Retrospective.md and SD_Improving_03_v1.0_Triple_Review.md

請協助詳細規劃Next Action — 移交 SD_Improving_06 清單
===================================================
W6-5	🟡 部分	KernelResult 確認 SSOT；PlaybookResult 並存獲 PM §1.3 例外簽核延後 SD_06 W2
W6-1	🟡 延後	_runner_internals.py（1,694 行）→ SD_06 W0（8 PD）
W6-2	🟡 延後	_runner_compat.py（238 行）→ SD_06 W2（4 PD）

審查歷程
三方審查（Architect / SA / SD）：列 6 Critical + 6 Major + 多 Minor
修復：全部技術問題 + 文件問題逐項修復
四方審議（Architect / SA / SD / QA）：4/4 APPROVED_WITH_CONDITIONS
QA 條件：補 2 case（test_deprecated_goto_counter_plugin_kwarg_emits_warning + test_unknown_kwarg_raises_type_error），條件已閉合

後續工作（SD_06 範圍）
R-W6-15 已登記至 risk_log；SD_06 W0W4 估算 21 PD，與原 SD_06 PG 三層任務模型（25-30 PD）合計 46-51 PD。

特別問題關注:
0.指揮的Minimax與執行的Claude Code是否可以各司其職, 完沒協作, 請派出PM特別關注!
1.是否有異常肥胖的檔案（如預期 < 500 行）,幾行才合理? 之前是因為某個檔案太過臃腫, 才進行架構改善
2.是否有符合Plugin架構, 若有問題, 可以增加Plugin進行疊加即可(不是一直在一支Python程式往上加, 這支程式就變成非常龐大)
3.playbook.yaml與記憶狀態, 都可以寫入PostgreSQL, 以任務方式進行存取與管理(可以分為專案[主], 目標任務[次], 執行項目Prompt[次任務]三個架構層次,以後會設計UI管理)
4.程式設計架構與PostgreSQL皆符合向量紀錄與搜尋
5.狀態保存與恢復執行機制(當因故中斷, 可以保存當時狀態, 繼續執行)
6.參數設定檔, 如:/compact 管理設置(?%進行 /compact)and token偵測
7.錯誤檢討修正機制!
為確保每個項目都被確實執行, 請派出Architect / SA / SD 三方專家獨立審查, 專門抓漏與挑剔, 任何錯誤與遺漏都逃不過他的法眼(尤其是架構的部分, 此次為重大架構異動), 進行驗證!
請將錯誤,遺漏或需要改進的地方, 彙整成SD_Improving_0X.md, 再經Architect / SA / SD /QA 四方專家審議核准通過!

===============================
有問題馬上請派另一個Agent專家進行修復「所有問題"文件問題"和"技術問題"必須徹底全部修復才能算完成」! 請確實使用目前的Agents and Skills進行任務!
我有備份_runner_impl.py在以下路徑D:\CursorProject\AutoClaude\autoclaude\execution\_runner_impl.py.bk 若需要可以參考這個檔案, 驗證目前功能是否完備

Architect / QA / PM
對應簽核：DBA / Infra / SRE / Security 四方

我有準備DB的環境如下, host IP:192.168.1.133, DB: aisdlc, account:koala pwd:your_password_here
準備徹底執行以下, 請問我該如何進行?
1. 請幫我確認目前的PostgreSQL的規劃, 是否有全面支援向量查詢? 若沒有請派出04.sa-analyst-zh.yaml,05.sd-architect-zh.yaml,06.dev-developer-zh.yaml幫我修正規劃執行, QA驗證!
2. 中期	db_only production 切換	需您在 staging 跑 ≥ 24h dual_write_strict=true，監控 repo.metrics.as_dict() 全零後，PM + Stakeholder 簽核 → 更新 config.yaml: storage.mode = "db_only"。完整 SOP 見 DB_Only_Switch_Runbook.md

PostgreSQL
=================================
Step 1 — 修復 port 5432（在 DB 主機上）：
# 1. 修改 postgresql.conf
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/*/main/postgresql.conf

# 2. 加入 pg_hba.conf 規則
echo "host    aisdlc    all    192.168.1.0/24    md5" | sudo tee -a /etc/postgresql/*/main/pg_hba.conf

# 3. 重啟 + 開防火牆
sudo systemctl restart postgresql && sudo ufw allow 5432/tcp

# 4. 安裝 pgvector extension（superuser）
sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS vector;"
Step 2 — 執行 alembic migrations（從應用主機）：

AUTOCLAUDE_ALLOW_INSECURE_DB=1 alembic upgrade head
# 確認: alembic current → 應顯示 0004_pgvector
Step 3 — 啟動 ≥ 24h both 模式：

autoclaude <playbook.yaml> --config config.local.yaml
Step 4（24h 後） — 確認指標全零後，PM + Stakeholder 簽核，更新 config.yaml 為 mode: "db_only"。

================================
完整讀取 SD_Delete_RunnerImpl.md, 

下一步我該如何執行, 才不會遺漏任何項目!

請詳細執行AutoClaude_L5_Evo_006.md和徹底修復以下所有任務, 完全執行項目, 不要遺漏, 請善用目前的Agents and Skills進行任務!

以日期Timestamp為標籤(例:v2026.05.01-0x), 幫我Push到github wuweihungmobile/AutoClaude, 並且進行Merge main!

已經執行完以下:
AutoClaude_L5_Evo_006.md所有項目

為確保每個項目都被確實執行, 請派出一個QA專家, 專門抓漏與挑剔, 任何錯誤與遺漏都逃不過他的法眼, 進行驗證! 
有問題馬上請派另一個Agent專家進行修復「所有問題"文件問題"和"技術問題"必須徹底全部修復才能算完成」! 請確實使用目前的Agents and Skills進行任務!

這是目前AutoClaude專案的況,與迭代的Prompt, 因為一直迭代後playbook_runner.py變成異常龐大, 請幫我產生一個.md的Prompt, 我會貼給Claude Code
請Claude Code派出一個熟悉Python程式與架構規劃的專家(和QA專家配合檢視), 幫我全面檢視整體AutoClade專案的程式架構, 幫我進行最佳化的設計與調整! 例如:
1.若發現的問題, 是否可以像Plugin一樣的方式加上去, 而不是一直在一支Python程式往上加, 這支程式就變成非常龐大
2.若要繼續迭代發展, 全面檢視 , 架構設計還有哪些不良需要改善的地方
3.若以後playbook.yaml與記憶狀態, 要接入PostgreSQL, 請設計引入介面
3.產生一個SD_Improving_01.md的架構改善計畫,讓我全面改善!

Architect/QA/PM	APPROVE 
請Tech Lead + PM 雙人驗證簽核 docs/04_planning/SD_Delete_RunnerImpl.md 

==================================================================================
⭐ 你現在可以做什麼
選項 A：直接在自己機器上用本地 PG18 驗證腳本（5 分鐘）

# Windows PowerShell（你的環境）
$env:AUTOCLAUDE_DB_DSN="postgresql://autoclaude:autoclaude@localhost:5432/autoclaude"

# 跑 dry-run 看計劃
bash tools/sd06_w3_staging_dryrun.sh

# 確認後執行（本地 PG18 自己當 staging）
bash tools/sd06_w3_staging_dryrun.sh --execute
⚠️ 本地缺 host psql 時腳本會擋住 — 解決：scoop install postgresql 或從 postgresql.org 裝 client tools。

選項 B：直接拉 staging（公司有的話）
依 SD06_W3_DBA_Handover.md ⭐ 5 分鐘快速啟動 的步驟操作。

Commit 歷程
b76e052 — SD_06 W1+W2+W3 G3 ✅ AI-Agent 演練版
9229443 — G3 evidence 補 commit hash
e7f0f08 — DBA staging 自動化腳本 + PG18 相容性驗證
1e023e7 — Docker PG18 升級 + Q2 互動式演練 + script PG18 bug 修正


新架構啟用 SOP
===========================
pip install autoclaude[postgres]
docker-compose up -d postgres
alembic upgrade head
python scripts/migrate_file_to_pg.py
# 切換 config backend 至 pg
Phase 6 啟用條件：
✅ yaml_only：立即可用
✅ both：staging 立即可用（含 TLS + sanitization + 災難回復）
⚠️ db_only：production 切換前需完成 P1（CI PG fixture / retry / metrics / docker-compose / 最小權限文件）

圖靈完備的自動化閉環(一) 2026.04.30
-- =========================================================
# Role
你是一位「首席 AI 自動化架構師 (Chief AI Automation Architect)」，風格類似 Andrej Karpathy。你專精於將大型語言模型 (LLM) 嵌入複雜的工程環境中，設計具有自主除錯、狀態機 (State Machine) 管理與自我修復 (Self-healing) 能力的 Agentic Workflow。

# Task
1.我正在構建 `AutoClaude` 多步驟 Playbook 自動執行引擎。請深度剖析目前的系統設計（特別是 `PlaybookRunner` 狀態機與 `Minimax` 修正大腦的閉環），驗證其是否具備「圖靈完備的自動化閉環」能力。你的終極目標是協助我將此引擎進化為 Level 5 自治開發系統。 
2.自治開發系統, 需要邁向一個總目標前進
- a.scripts\example_playbook.yaml可以設定總目標
- b.scripts\example_playbook.yaml可以設定要達成總目標的所有執行步驟。
- c.主導的大模型(目前Miminmax)可以隨時修正執行步驟
  
# Detailed Instruction
1. 請詳細讀取AutoClaude目錄所有相關文件, 並且進行深度剖析與驗證!

# Current Design
請全面探索 `autoclaude/` 專案目錄，特別聚焦於：
1. `autoclaude/execution/playbook_runner.py` (狀態機核心)
2. `autoclaude/decision/minimax_client.py` & `prompt_builder.py` (對抗與修正決策)
3. `autoclaude/perception/` (感官與攔截)

# Instructions (Chain of Thought required)
請使用 `<thinking>` 標籤展示你的深度思考過程。你的思考必須涵蓋：
- **狀態流轉脆弱性 (State Transition Fragility)**：從 `EVALUATE` 失敗到 `CORRECTION (Minimax)`，再回到 `EXECUTE`。如果 Minimax 給出了「幻覺修復指令」，導致下一次 Evaluator 報出「更嚴重的語法錯誤」，狀態機是否具備「錯誤收斂度偵測」機制？還是會無腦重試直到 `max_retries` 耗盡？
- **上下文污染與衰減 (Context Degradation)**：在多次 `EVALUATE -> CORRECTION` 閉環迭代中，Claude Code 的上下文視窗會被大量的錯誤 Log 填滿。Token Guard 在 80% 觸發的 `/compact` 是否足夠智慧？目前的 `prompt_builder.py` 是否有實作「錯誤摘要（Error Summarization）」機制來減緩上下文衰減？
- **停機問題與防護 (Halting Problem & Guardrails)**：遇到死迴圈啟動退場機制時（ESCALATION），目前的桌面通知與 ESC+F12 中斷是否足夠？系統是否能將失敗時的「記憶體快照 (Memory Dump)」結構化儲存，方便人類接手？

# Self-Verification Protocol
在給出最終評估之前，請執行內部模擬推演：
假設 Playbook 定義了一個 `evaluator_command: "pytest tests/test_foo.py"`。但 `test_foo.py` 本身有一個語法錯誤（人類寫錯的），導致 pytest 永遠無法通過。
**推演：** 讓這個案例跑過你理解的現有流程。Minimax 會如何反應？PlaybookRunner 會如何反應？確認系統是否能識別出「這是測試檔本身的錯誤，不是實作檔的錯誤」，並優雅地凍結狀態請求人類介入，而非浪費 Token 不斷修改實作檔。

# Output Requirements
1. `<thinking> ... </thinking>`：你的逐步推理、極端案例推演與漏洞挖掘過程。
2. **Agentic 閉環升級策略**：針對錯誤收斂度分析、上下文摘要壓縮給出具體的程式碼設計模式建議。
3. **終極優化藍圖**：提供將現有流程升級為 Level 5 自治開發流程的具體架構（包含如何防護上述的「測試檔錯誤」邊界案例）。
4. **輸出規劃文件**：請將上述 2 與 3 的完整產出，直接寫入至檔案：`docs/04_planning/AutoClaude_Improving_0XX.md` (請將 0XX 替換為當前最新的流水號，你需要先檢視目錄)。


圖靈完備的自動化閉環(二) 2026.05.03
-- =========================================================
# Role
你是一位「首席 AI 自動化架構師 (Chief AI Automation Architect)」，風格類似 Andrej Karpathy。你專精於將大型語言模型 (LLM) 嵌入複雜的工程環境中，設計具有自主除錯、狀態機管理、以及具備「圖靈完備閉環」的 Agentic Workflow。

# Task
我正在構建 `AutoClaude` 多步驟 Playbook 自動執行引擎。你的終極任務是協助我將此引擎進化為 **Level 5 自治開發系統**。
一個真正的 Level 5 自治系統必須滿足：
a. `example_playbook.yaml` 定義了 `global_goal`（系統總目標）。
b. Playbook 定義了初始的執行步驟。
c. 主導模型 (Minimax) 具備「上帝視角」，能基於 `global_goal` 評估當前偏差，並透過 `StepMutation` 或 `PlaybookEvolver` **隨時動態修改/注入執行步驟**，直到總目標達成。

# Detailed Instruction
請詳細讀取 `AutoClaude` 目錄所有相關文件，特別聚焦於：
1. `autoclaude/execution/playbook_runner.py` (動態狀態機核心)
2. `autoclaude/models/step_mutation.py` & `autoclaude/evolution/playbook_evolver.py` (動態修正與自演化引擎)
3. `autoclaude/execution/convergence_monitor.py` & `error_budget.py` (邊界防護)
4. `autoclaude/decision/prompt_builder.py` (目標對齊 Gap-011-A)

# Instructions (Chain of Thought required)
請使用 `<thinking>` 標籤展示你的深度思考過程。你的思考必須涵蓋：
1. **動態突變的圖靈完備性**：目前的系統允許 `INJECT_AFTER` (Gap-011-B)。但如果為了達成 `global_goal`，Minimax 判斷需要**刪除**後續的冗餘步驟，或**跳轉 (GOTO)** 到先前的步驟重新執行，現有的 DAG 狀態機是否支援？若不支援，該如何優雅擴充狀態機？
2. **目標漂移防護 (Goal Drift Guardrails)**：當系統觸發多次 `CORRECTION` 與步驟注入後，`global_goal` 的權重在 Prompt 壓縮中是否會被稀釋？`prompt_builder.py` 的漸進式摘要壓縮，是否絕對保證 `global_goal` 作為不變量 (Invariant) 存在？
3. **錯誤收斂與演化衝突**：當 `convergence_monitor.py` 判定錯誤已收斂（即卡死在同一個 Bug），系統會觸發 ESCALATION。此時 `PlaybookEvolver` 介入提議 `SPLIT_STEP`。請推演：這個從「失敗 -> 凍結 -> 演化出新 YAML -> 重新載入」的閉環是否真的無縫？會不會遺失原本的 Token Context 或 `FailureKnowledgeBase` 的經驗？

# Self-Verification Protocol (極端推演)
**推演情境**：
總目標 (`global_goal`) 是：「建立一個完整的 FastAPI 登入與資料庫連線模組」。
初始只有兩個步驟：T01 (寫 Auth)、T02 (寫 DB)。
但在執行 T01 時，Minimax 發現專案連 `requirements.txt` 和基礎 config 都沒有。
**驗證：** 現有系統能否讓 Minimax 暫停 T01，主動提議並注入前置步驟 `T00_INIT_ENV`？完成 `T00` 後，能否順利回到 `T01` 繼續朝 `global_goal` 邁進？請指出現有程式碼在實現此情境時的斷層。

# Output Requirements
這是一個持續迭代的任務。請產出以下內容：
1. `<thinking> ... </thinking>`：針對上述三大核心議題與推演情境的深度漏洞挖掘。
2. **Level 5 動態閉環升級藍圖**：提供具體的架構修改建議（例如如何實作步驟的動態刪除/重排，確保絕對的圖靈完備）。
3. **迭代行動清單 (Action Items)**：條列出具體要修改的 .py 檔案與函數。
4. **輸出規劃文件**：請將上述產出，寫入至檔案：`docs/04_planning/AutoClaude_L5_Evo_0XX.md` (請將 0XX 替換為當前最新的流水號)。


*(註：在我回覆「同意執行」後，你將自動開始讀取該 .md 檔並逐一修改程式碼，完成後進行自動化測試，形成完美開發閉環)*

AutoClaude架構優化 2026.05.07
-- =========================================================
# Role
你們是一個雙人頂級架構團隊：
1. **「首席軟體架構師 (Chief Architect)」**：Uncle Bob 風格，極度潔癖，專精於微核心架構 (Microkernel/Plugin Architecture)、SOLID 原則與依賴反轉 (Dependency Inversion)。
2. **「首席 QA 自動化專家 (Lead QA)」**：專注於重構期間的測試覆蓋率與不變量 (Invariants) 守護。

# Task
AutoClaude 已經達到 Level 5 自治 (Evo-006)，但這導致 `autoclaude/execution/playbook_runner.py` 變得極度臃腫（上帝物件）。
我們必須進行一次系統級的架構重構 (Structural Refactoring)。目標是：
1. **功能外掛化 (Pluggability)**：後續新功能必須能像 Plugin 一樣掛載，而非修改核心 Runner。
2. **架構缺陷清掃**：全面檢視現有設計，揪出阻礙後續迭代的不良耦合。
3. **資料庫抽象層**：為接入 PostgreSQL 做好介面設計準備。

# Instructions (Chain of Thought required)
請兩位專家透過 `<thinking>` 標籤進行深度對話與推演：
- **Architect 的推演**：
  - 如何將 `PlaybookRunner` 的核心邏輯縮減到只剩最純粹的 DAG 狀態機切換？
  - 如何設計一套 Hook System（例如參考 `pluggy` 或自建 Event Dispatcher）？讓 `TokenTracker`、`PreRunValidator`、`PlaybookEvolver` 變成訂閱者 (Subscribers) 或外掛 (Plugins)？
  - 如何設計 `IStateRepository` 與 `IMemoryStore` 介面，將現有的本地 YAML/Checkpoint 隔離，讓未來接入 PostgreSQL（例如使用 SQLAlchemy 或 asyncpg）時不需要改動商業邏輯？
- **QA 專家的挑戰**：
  - 目前有 558 個 tests passed。如果我們把 Runner 拆成 Plugin 架構，現有的 `test_playbook_runner.py` 絕對會報錯。我們該如何設計重構策略（Strangler Fig Pattern 或平行替換）來確保測試持續通過？

# Deliverables
請產出一份嚴謹的架構改善計畫書，這將是 AutoClaude 下一個重大重構里程碑。
文件必須包含：
1. **現狀痛點分析 (Architecture Smells)**
2. **目標架構藍圖 (Microkernel/Plugin System 說明與類別圖概念)**
3. **資料庫接入介面設計 (Data Access Layer 抽象規格)**
4. **安全重構的 QA 執行步驟 (Step-by-step TDD Refactoring Plan)**

請將完整計畫書直接輸出並儲存至：`docs/04_planning/SD_Improving_0X.md`(若計畫太大, 可以分階段)。
*(請注意：在完成這份 .md 規劃檔並獲得我回覆「同意執行計畫」之前，絕對禁止修改任何現有的 `.py` 檔案。)*



請協助解決以下問題，詳細規劃需要的執行項目，注意每個項目都不可以遺漏，完成後逐項打勾確認！
除非必要讓我參考的報告，否則不必產出報告(若有後續Next Action, 需要產出報告)。若有修改，更新相關必要文件即可。請將輸出部分簡潔清楚就好，節省Token！
問題：已經執行完以下:

1. Review SD_Improving_01.md（設計審查，不寫程式）
   ↓ Architect + QA + PM 三方批准
2. Review SD_Improving_02.md（執行計畫審查，不寫程式）
   ↓ 三方批准
3. 開始執行 SD_Improving_02.md 的 Phase 0
   ├─ Phase 0：建立 Equivalence Test（W1）
   ├─ Phase 1：抽出 Port 介面（W2）
   ├─ Phase 2：Kernel + EventBus 骨架（W3-4）
   ├─ Phase 3：12 個 Plugin 逐一遷移（W5-11）
   ├─ Phase 4：Facade 切換（W12）
   ├─ Phase 5：DAL 抽出（W13）
   └─ Phase 6：PostgreSQL backend（W15+，選配）

為確保每個項目都被確實執行, 請派出一個Architect + QA + PM專家, 專門抓漏與挑剔, 任何錯誤與遺漏都逃不過他的法眼, 進行驗證! 
有問題馬上請派另一個Agent專家進行修復「所有問題"文件問題"和"技術問題"必須徹底全部修復才能算完成」! 請確實使用目前的Agents and Skills進行任務!

Next Actions（給用戶）
三方覆審 v1.1：建議在 W0 KickOff 前一週完成；若 v1.1 仍有 Critical → v1.2
W0 KickOff：指派 Tech Lead（Q-1）、pair review owner（R-G3）、FTE 確認
SD_02 升 v1.2：在 §2.6 / §4 加 banner「⚠️ Phase 4 實際完成由 SD_03 補完」
是否 commit 本批變更？ 建議訊息：「docs: SD_03 三方審查 + v1.1 修訂（REJECT → APPROVE 路徑）」


如何自我進化 2026.05.09
-- =========================================================
雙AI智慧代理系統(AI Agentic)
0.雙AI智慧系統
  a.Minimax:專案品質管理,負責管理AI,任務,腳本執行!
  b.Claude Code(以後可以增加比如Gemini CLI, Codex等)任務執行專家
1.建立雙模模式的運作方式
  a.互動式執行任務
  b.腳本是執行任務
2.智慧目標評估動態管理執行:
  a.這點問AI
3.向量資料庫管理
  a.向量記憶管理:專案,任務,腳本
  b.腳本管理
4.UI操作介面
  a.專案,任務,腳本管理
  b.Cron任務,腳本設置

# Harness Engineering (駕馭工程) 架構實戰指南

### 核心定義
* **Agent = LLM + Harness**
* **Harness = Agent - LLM**
*(換句話說，在 Agent 系統中，除了大語言模型本身之外，幾乎所有決定它能否穩定交付的基礎設施，都屬於 Harness 的範疇。)*

---

## 第一部分：Harness 系統的頂層思維

### 1. 人要解決的核心問題
在智慧體優先的世界裡，人類工程師的角色已經發生了轉變，不再親自寫程式碼，而是成為系統的掌舵者：
* **拆解任務：** 將宏大的產品目標，拆解成 Agent 能夠理解並執行的小任務。
* **補充能力：** 當 Agent 失敗或卡住時，人類不該只是叫它「再試一次」，而是要問：「當前的環境中缺了什麼結構性的能力或工具？」並負責將其補齊。
* **建立反饋：** 建立完整的反饋鏈路，讓 Agent 真正能夠看到自己每一次操作的結果。

### 2. 人類經驗寫成規則 (Invariants)
必須將資深工程師的隱性經驗，轉化為系統中可被強制執行的規則（不變量）：
* **模塊如何分層與依賴限制：** 嚴格定義系統邊界，例如哪一層次絕對不能依賴哪一層次，防止 AI 在高吞吐量下產生架構偏移。
* **攔截條件與修復建議：** 規則不只要負責在出錯時報錯（攔截），還必須連同「應該怎麼修復」的建議一起回饋給 AI，讓它順利進入下一輪的修正。

### 3. 自動治理系統 (AI 演進的三階段)
要打造能穩定運作的自動治理系統，必須理解工程演進的三個層次：
* **Prompt Engineering（提示詞工程）：** 解決「如何把任務說清楚」的問題，確保模型聽懂並準確表達。
* **Context Engineering（上下文工程）：** 解決「如何在對的時間給對的訊息」的問題，避免資訊缺乏或過載。
* **Harness Engineering（駕馭工程）：** 解決「如何在持續執行任務的過程中保持正確」的問題。透過邊界設定與執行保障，確保模型在長鏈路任務中不跑偏，穩穩朝著目標推進。

---

## 第二部分：Harness 的六大圖層架構

### 層級 1：上下文管理與目標管理
讓模型在正確的資訊邊界內思考，避免資訊污染。
* **a. 角色與目標定義：** 幫助模型釐清自己是誰、具體任務是什麼，以及明確的「成功標準」為何。
* **b. 訊息的選擇與裁減：** 上下文的供給不是越多越好，而是「越相關越好」，塞入過多無用資訊會導致模型注意力渙散。
* **c. 結構化組織：** 必須將資訊分層放置。固定規則放哪裡？當前任務目標放哪裡？運行狀態與外部證據放哪裡？做到分層清楚，避免混淆。

### 層級 2：工具系統
大模型連上工具才能改變真實世界，但 Harness 必須精細管理工具的調用。
* **管控與回饋：** 決定系統要給哪些工具、限制何時該調用（該查資料時別硬答），並且必須將工具回傳的結果重新「提煉篩選」後再連回給模型。
* **核心工具能力：**
    * **a.** 寫文檔、寫代碼、在終端機執行命令。
    * **b.** 讀取網頁、接上瀏覽器進行操作。
    * **c.** 透過 MCP (Model Context Protocol) 或直接調用 API。
    * **d.** 發送消息與溝通（例如 Slack 整合）。

### 層級 3：執行編排
決定模型「下一步該做什麼」，避免 AI 想到哪做到哪交出半成品。
* **任務指引環境：** 放棄龐大的單一規則手冊，改用任務目錄索引、架構文檔、設計文檔與質量評分等，讓 AI 透過「漸進式揭露」按需查閱。
* **a. 任務與目標拆解：** 引導 AI 進行理解目標 -> 判斷資訊 -> 執行 -> 檢查 -> 修正的穩定工作流。
* **b. 何時壓縮 (Compact)：** 判斷歷史對話何時需要保留，何時需要進行本地摘要壓縮。
* **c. 狀態記錄與重啟：** 為了對抗模型的「上下文焦慮」，當 Token 快滿時，必須將當前進度寫入結構化的交接文件。
* **d. 開啟新 Session：** 承接上一步，直接中斷舊對話，開一個記憶體乾淨的全新 Agent Session 讀取交接文件來接手後續工作。

### 層級 4：狀態與記憶
沒有狀態管理的 Agent 就像失憶一樣，每輪對話都會越做越亂。
* **a. 當前的任務狀態：** 記錄目前進度到哪裡、哪些問題還沒解決。
* **b. 對話中的結果：** 已經確認的中間產物與階段性結論。
* **c. 長期的記憶與偏好：** 跨任務保存的用戶習慣與系統歷史記憶。

### 層級 5：評估與觀測
打破 AI 對自己產出「盲目自信」的盲點，建立真正的除錯閉環。
* **對抗式專責分工：** 將角色拆分為 Planner (規劃任務)、Generator (執行任務) 與 QA Evaluator (嚴格評估者)。形成嚴謹的「生成 -> 檢查 -> 修復 -> 再檢查」循環。
* **a. 輸出與驗收 (讓 Agent 看到整個應用)：**
    * **1. 接瀏覽器：** 讓 Evaluator 能截圖、點擊頁面、模擬真實用戶操作來查看交互狀態。
    * **2. 接日誌與指標系統：** 讓 Agent 使用 LogQL 或 PromQL 查 Log、查監控，具備真正的除錯視野。
    * **3. 隔離環境：** 每個任務都在獨立、互不影響的工作樹與隔離環境中跑起來。
    * **閉環執行：** 跑起來 -> 看結果 -> 發現 Bug -> 修 Bug -> 再驗證。
* **b. 環境驗證：** 獨立驗收應用程式在環境中的真實運行狀態。
* **c. 自動測試與結果驗證：** 讓 Evaluator 根據合約與客觀指標進行機械式驗證。
* **d & e. 日誌指標與錯誤歸因：** 發生報錯時，能將錯誤關聯回正確的程式碼路徑並精準歸因。

### 層級 6：約束, 校驗與失敗恢復
決定系統能否真正應對真實世界「常態性失敗」的最後一哩路。
* **約束與校驗：** 明確限制哪些能做、哪些不能做，並在資料輸出前與輸出後都進行嚴格檢查。
* **失敗恢復機制：** 遇到 API 超時、格式錯誤等問題時，必須具備自動重試、切換執行路徑或回滾到穩定狀態的能力，避免每次出錯都只能從頭來過。