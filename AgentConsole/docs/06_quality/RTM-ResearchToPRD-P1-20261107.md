# 2.10 研究議題轉規格書 P1 分流與內環交棒（ResearchToPRD；`/research?step=route|build`）的 TCS 本地 ID 追溯（ResearchToPRD_PRD.md；不計入 §2 總列數）

**檔頭說明（2026-11-07 立骨架）**：本檔依 DEF-200-576 每功能一檔體例自始立為獨立檔；[RTM.md](RTM.md) 的 §2.10 存根於 P1 補一行引言。**本檔只增列不改號；回填規則照 RTM.md §1**；四格（實作檔、自動測試、E2E 驗證、狀態）一律由 `⬜` 起，完成一項回填一列，不得刪列、改號、合併列（`AgentConsole/CLAUDE.md` 鐵律 12）。

> 本子表的 ID 是 `AgentConsole/docs/03_testing/contracts/TCS-ResearchToPRD-P1-20261107.md`（下稱 TCS）的本地編號（F／US／AC／AT），ID 欄一律加反引號、不計入總列數。對應 PRD `docs/01_requirements/ResearchToPRD_PRD.md`（P1：FR-R2P-11～14、19 後端與 FSM 序列，及 FR-R2P-02、04、21、23 的 P1 增量）；本子表 238 列＝F 1、US 3、AC 25、AT 209（負控與邊界 43、正控 166；Bridge、backend、frontend、E2E 與指令核對）。FSM 功能鍵 `agentconsole-research-to-prd-p1`；開工基準 commit、規格摘要與 RELEASE 落款於 Stage-2 凍結與 RELEASE 時由主控回填。

| ID | 來源 | 摘要 | 層 | Phase | 實作檔 | 自動測試 | E2E 驗證 | 狀態 |
|----|------|------|----|-------|--------|----------|----------|------|
| `F-907` | ResearchToPRD_PRD.md·TCS-ResearchToPRD-P1 | ResearchToPRD P1：分流精靈、軌道 A 與 B、內環鍵 Stage-1 採納、TCS 草擬、任務拆解與簽核、SCR 後端與 FSM 序列；Flyway V19；步驟 3 真面板與步驟 4 前半 | frontend／backend／engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `US-923` | ResearchToPRD_PRD.md·TCS-ResearchToPRD-P1 | 分流與軌道（US-R2P-11、12、13）：作為掌舵者，我要在 Gate 0 核准後用預演確認再由 ADMIN 確認分流；軌道 A 在獨立 worktree 併入既有模組、軌道 B 一次完成新專案與 GitHub 且不洩漏機密（AC-961-2、AC-961-3、AC-961-4、AC-961-5、AC-961-6、AC-961-8、AC-961-14、AC-961-16、AC-961-17） | — | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `US-924` | ResearchToPRD_PRD.md·TCS-ResearchToPRD-P1 | SDD 綁定、拆解交棒與 TCS 草擬（US-R2P-14）：作為掌舵者，我要把核准的 PRD 以內環鍵採納為基線、草擬測試規格、拆成帶覆蓋對映的任務草稿並在簽核前不准執行（AC-961-7、AC-961-9、AC-961-10、AC-961-11、AC-961-18、AC-961-19、AC-961-25） | — | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `US-925` | ResearchToPRD_PRD.md·TCS-ResearchToPRD-P1 | SCR 後端與橫切增量（US-R2P-19 後端、21、22、23 的 P1 增量）：作為 OPERATOR，我要走正式的規格變更請求；作為掌舵者，我要資料表、對帳、稽核與說明在 P1 到位（AC-961-1、AC-961-12、AC-961-13、AC-961-15、AC-961-20、AC-961-21、AC-961-22、AC-961-23、AC-961-24） | — | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-1` | TCS-ResearchToPRD-P1 | 資料庫 V19：分流、SCR、拆解、交付表與自癒視圖的不可變與 CHECK（Flyway V19） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-2` | TCS-ResearchToPRD-P1 | 分流輸入閘與消毒（Bridge route 驗證層） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-3` | TCS-ResearchToPRD-P1 | 分流預演：動作清單與零副作用、部署不支援 | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-4` | TCS-ResearchToPRD-P1 | 分流執行：逐步入庫、失敗停點、重試、衝突與事件 | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-5` | TCS-ResearchToPRD-P1 | 軌道 A：獨立 worktree、發佈、落點 stub 與主工作樹零擾動 | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-6` | TCS-ResearchToPRD-P1 | 軌道 B：範本展開、工作區複製、git 與 gh、token 零外洩 | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-7` | TCS-ResearchToPRD-P1 | 內環鍵建立與 Stage-1 基線採納（FSM 序列） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-8` | TCS-ResearchToPRD-P1 | gitops 白名單、能力登記與 FSM 單一寫入面（AST 與表驅動鎖） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-9` | TCS-ResearchToPRD-P1 | TCS 草擬 stage（tcs-draft） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-10` | TCS-ResearchToPRD-P1 | 任務拆解：草稿、有界閘、覆蓋對映與 stale | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-11` | TCS-ResearchToPRD-P1 | 拆解簽核與執行閘（console-api 二次校驗） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-12` | TCS-ResearchToPRD-P1 | SCR 後端：發起、輸入閘、上限、MAJOR 與自癒耗盡路徑 | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-13` | TCS-ResearchToPRD-P1 | SCR MINOR 的 FSM 指令序列與內環現態矩陣 | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-14` | TCS-ResearchToPRD-P1 | console-api 分流端點：預演、確認、先建專案列與補償 | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-15` | TCS-ResearchToPRD-P1 | console-api SCR、拆解端點、角色矩陣、OpenAPI 與 reason 契約 | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-16` | TCS-ResearchToPRD-P1 | capabilities 能力探針與 UI 停用 | backend／engine-bridge／frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-17` | TCS-ResearchToPRD-P1 | 前端 RouteDrawer 與步驟 3 面板 | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-18` | TCS-ResearchToPRD-P1 | 前端步驟 4 前半面板：拆解、覆蓋、簽核與 TCS 草擬 | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-19` | TCS-ResearchToPRD-P1 | 步驟接入、說明三道鎖、端點函式與前端靜態鎖 | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-20` | TCS-ResearchToPRD-P1 | 對帳：route_decision、task_decomposition 與 SCR 相態 | backend／engine-bridge／frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-21` | TCS-ResearchToPRD-P1 | 入庫完整率與稽核列（V19 口徑） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-22` | TCS-ResearchToPRD-P1 | 整合 P1：拋棄式 clone、假 gh、Docker mock 與 Playwright 真棧 | engine-bridge／frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-23` | TCS-ResearchToPRD-P1 | 邊界、跨平台與衛生閘（允許變更集合、禁區、無新守衛、無新目錄項原語） | docs／gate／engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-24` | TCS-ResearchToPRD-P1 | 文件連動、追溯與 V 系列 | docs／gate | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-961-25` | TCS-ResearchToPRD-P1 | TCS 凍結後的游標校正（D-125）：讀端衍生、Bridge 對帳校正、凍結後觸發與重新對帳 | backend／engine-bridge／frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-1-1` | TCS-ResearchToPRD-P1 AC-961-1（AC-R2P-02-7、AC-R2P-02-8） | Flyway 歷史 1～19 全成功；V19 的五張表與一個視圖齊備且只在 console schema；ddl-auto validate 不報錯。（預定載具：ResearchSchemaMigrationIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-1-2` | TCS-ResearchToPRD-P1 AC-961-1（AC-R2P-02-7） | research_route_decisions 的 CHECK：軌道與目標種類與模組三者一致、列舉值、PUBLIC 只准軌道 B、狀態列舉。（預定載具：ResearchSchemaMigrationIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-1-3` | TCS-ResearchToPRD-P1 AC-961-1（AC-R2P-02-7） | ux_research_route_active 部分唯一索引：同一研究專案至多一筆 PENDING、RUNNING 或 SUCCEEDED。（預定載具：ResearchSchemaMigrationIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-1-4` | TCS-ResearchToPRD-P1 AC-961-1（AC-R2P-02-7） | research_route_steps 的 CHECK 與主鍵：十一個步驟名、五個狀態、步序下界、(route_id, step_no) 唯一。（預定載具：ResearchSchemaMigrationIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-1-5` | TCS-ResearchToPRD-P1 AC-961-1（AC-R2P-02-7） | research_scr 的 CHECK 與唯一鍵：型別、來源類別、理由分類、狀態列舉與 (research_id, scr_no) 唯一。（預定載具：ResearchSchemaMigrationIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-1-6` | TCS-ResearchToPRD-P1 AC-961-1（AC-R2P-02-7） | research_decompositions 的 CHECK：路徑、雜湊格式、任務數下界、七個狀態。（預定載具：ResearchSchemaMigrationIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-1-7` | TCS-ResearchToPRD-P1 AC-961-1（AC-R2P-02-7） | research_deliveries：列舉、雜湊格式、(research_id, kind, ref) 唯一、append-only（P2 寫入，表於 P1 建立）。（預定載具：ResearchSchemaMigrationIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-1-8` | TCS-ResearchToPRD-P1 AC-961-1（AC-R2P-02-7） | 四張 V19 受控可更新表的通用守衛：清單內欄可更新、清單外欄位與任何 DELETE 被拒；含複合主鍵表的列定位（與 V16 函式內的允許清單逐表對拍；不併入 P0 的受控表迴圈）。（預定載具：ResearchSchemaMigrationIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-1-9` | TCS-ResearchToPRD-P1 AC-961-1（AC-R2P-02-7） | 視圖 v_research_healing_attempts：只含 RETRYING 與 FAILED 步驟、經 console_project_id 連結、不提供任何寫入路徑。（預定載具：ResearchSchemaMigrationIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-1-E-1` | TCS-ResearchToPRD-P1 AC-961-1（AC-R2P-02-7） | 所有十八張 research_ 表（P0 十三張加 V19 五張）逐表 DELETE 一律被擋，守衛錯誤的 SQLSTATE 一律為類別 23。（預定載具：ResearchSchemaMigrationIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-1-E-2` | TCS-ResearchToPRD-P1 AC-961-1（AC-R2P-02-7） | 既有五個 Flyway IT 的版本清單改為 1 至 19，且 BackupJobMigrationIT 的「既有表零變動」快照把視圖排除。（預定載具：BackupJobMigrationIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-1-E-3` | TCS-ResearchToPRD-P1 AC-961-1（AC-R2P-02-7） | V19 的預設值與 JSONB 欄位型別：published_docs 預設 {}、impl_fsm_actions 預設 []、型別皆為 jsonb。（預定載具：ResearchSchemaMigrationIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-2-1` | TCS-ResearchToPRD-P1 AC-961-2（AC-R2P-11-5、AC-R2P-13-3） | 分流請求本文的欄位驗證表：軌道、分支名、庫名、可見性、確認名、範本、理由長度的界內與界外，違規逐欄列出。（預定載具：test_research_route_gate.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-2-2` | TCS-ResearchToPRD-P1 AC-961-2（AC-R2P-11-5） | 消毒鏈：黑名單字元、`..`、逃出 allowlist 根的導出路徑、符號連結逃逸、不合 git ref 規則的分支名，一律 422 逐欄列出且零副作用（路徑由 Bridge 導出，使用者不輸入絕對路徑，D-106）。（預定載具：test_research_route_gate.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-2-3` | TCS-ResearchToPRD-P1 AC-961-2（AC-R2P-12-3） | 落點目標清單為 Bridge 常數 PLACEMENT_TARGETS（四值，每值附一句出處）：目標模組只能從清單選、預設值取自 PRD 落點表解析結果、覆寫被記錄；不提供 ADMIN 維護（D-100）。（預定載具：test_research_route_gate.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-2-4` | TCS-ResearchToPRD-P1 AC-961-2（AC-R2P-11-4） | 分流軌道與 PRD target_scope 不同時必填一句理由（1 至 200 字）並回差異警示；相同時不需要；PRD 凍結檔位元組不變。（預定載具：test_research_route_gate.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-2-5` | TCS-ResearchToPRD-P1 AC-961-2（AC-R2P-13-7） | 範本登記制：scaffold_templates 取自目錄清單，選不存在的範本回 422，node 與 java 不在清單。（預定載具：test_research_route_gate.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-2-6` | TCS-ResearchToPRD-P1 AC-961-2（AC-R2P-13-3） | Public 需名稱確認：預設 PRIVATE；PUBLIC 缺確認名或不符一律 422 且零副作用；軌道 A 不接受 PUBLIC。（預定載具：test_research_route_gate.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-2-7` | TCS-ResearchToPRD-P1 AC-961-2（AC-R2P-11-1） | Gate 0 未完成不得分流：外環 FSM 非 SPEC_FROZEN 或游標不在 route 時，預演與確認一律 409。（預定載具：test_research_route_gate.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-2-E-1` | TCS-ResearchToPRD-P1 AC-961-2（AC-R2P-13-3、AC-R2P-11-4） | 常數邊界一次釘齊：分支名、庫名、理由、確認名、範本變數的界內與界外各一對。（預定載具：test_research_route_gate.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-3-1` | TCS-ResearchToPRD-P1 AC-961-3（AC-R2P-11-2、AC-R2P-12-1） | 軌道 A 預演動作清單：步驟序固定、每項含動作、目標、是否觸及外部系統，且與執行共用同一份清單。（預定載具：test_research_route_gate.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-3-2` | TCS-ResearchToPRD-P1 AC-961-3（AC-R2P-13-1） | 軌道 B 預演動作清單：含建立目錄、複製並驗證、git init、設 remote、範本檔、初始 commit 與（選 GitHub 時）建遠端與推送，外部系統標示正確。（預定載具：test_research_route_gate.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-3-3` | TCS-ResearchToPRD-P1 AC-961-3（AC-R2P-11-2、AC-R2P-12-1） | 軌道 A 預演零副作用：主工作樹、worktree 清單、分支清單、目標目錄與資料庫在預演前後逐項相同。（預定載具：test_research_route_gate.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-3-4` | TCS-ResearchToPRD-P1 AC-961-3（AC-R2P-11-2、AC-R2P-13-1） | 軌道 B 預演零副作用：目標根下不產生任何檔案或目錄，假 gh 只可能收到唯讀探測。（預定載具：test_research_route_gate.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-3-5` | TCS-ResearchToPRD-P1 AC-961-3（AC-R2P-11-6、AC-R2P-13-1） | 部署不支援：缺 gh、缺可寫 repo 或未設 BRIDGE_SCAFFOLD_ROOT 時預演回 route_unsupported_in_deployment 並指出缺項，零副作用。（預定載具：test_research_route_gate.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-3-6` | TCS-ResearchToPRD-P1 AC-961-3（AC-R2P-13-6） | 目標目錄已存在且非空：預演與確認都回 422 target_not_empty，不覆寫、不合併；存在但為空允許。（預定載具：test_research_route_gate.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-3-7` | TCS-ResearchToPRD-P1 AC-961-3（AC-R2P-12-1） | 分支已存在：預演即回 409 branch_exists，零變更（含 worktree 清單）。（預定載具：test_research_route_gate.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-3-E-1` | TCS-ResearchToPRD-P1 AC-961-3（AC-R2P-11-2） | 預演與執行共用同一份計畫函式：動作清單的步驟名序列恆等於執行的步驟序列，且兩條路徑呼叫同一個驗證函式。（預定載具：test_research_route_gate.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-4-1` | TCS-ResearchToPRD-P1 AC-961-4（AC-R2P-11-3） | 執行成功路徑（同步）：步驟逐步入庫、成功才寫 route_decision.json 並推進游標到 build／ROUTED，並發出 research.route 事件。（預定載具：test_research_route_exec.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-4-2` | TCS-ResearchToPRD-P1 AC-961-4（AC-R2P-11-3、AC-R2P-12-5） | 部分失敗：第 k 步失敗即停，後續步驟不執行，已入庫列保留，游標停在 route 並帶失敗原因。（預定載具：test_research_route_exec.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-4-3` | TCS-ResearchToPRD-P1 AC-961-4（AC-R2P-11-3、AC-R2P-12-5、AC-R2P-13-4） | 重試失敗步驟：已成功的步驟不重做且其列位元組不變，只從失敗步驟起續做。（預定載具：test_research_route_exec.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-4-4` | TCS-ResearchToPRD-P1 AC-961-4（AC-R2P-11-3） | 失敗不補償到破壞態：Bridge 在失敗後不執行 git clean、stash、刪目錄或刪分支，已建立的 worktree 與分支原地保留。（預定載具：test_research_route_exec.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-4-5` | TCS-ResearchToPRD-P1 AC-961-4（AC-R2P-11-3） | 同專案不得有第二個進行中的分流：已有 PENDING、RUNNING 或 SUCCEEDED 時 POST route 回 409 route_conflict，零副作用。（預定載具：test_research_route_exec.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-4-6` | TCS-ResearchToPRD-P1 AC-961-4（AC-R2P-11-3） | 兩個 ADMIN 並發確認同一專案：一個 200、一個 409，只有一筆路由列，副作用只發生一次。（預定載具：test_research_route_exec.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-4-7` | TCS-ResearchToPRD-P1 AC-961-4（AC-R2P-11-3） | 步驟列先於副作用寫入（DB 先於檔案與子行程）：行程在副作用之後被中斷，重啟時孤兒回收把卡在 RUNNING 的分流列標 FAILED 並可重試。（預定載具：test_research_route_exec.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-4-8` | TCS-ResearchToPRD-P1 AC-961-4（AC-R2P-11-3） | 權杖與角色：確認需 Bridge 寫入權杖；approver 取自 console-api 轉入的 JWT subject，保留字與格式不合一律 422。（預定載具：test_research_route_exec.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-4-9` | TCS-ResearchToPRD-P1 AC-961-4（AC-R2P-11-8） | 補償通知：console-api 補償完 Console 專案列後呼叫 :route-compensated，Bridge 驗該列為 FAILED 才改 COMPENSATED（Bridge 為研究表唯一寫入者，D-112）。（預定載具：test_research_route_exec.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-4-E-1` | TCS-ResearchToPRD-P1 AC-961-4（AC-R2P-11-3） | DB 阻塞時的游標校正（D-128，oracle 取 P0 原文）：阻塞期間游標不重新衍生，復原後 outbox 重放完成的同一交易重新衍生游標。（預定載具：test_research_route_exec.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-4-E-2` | TCS-ResearchToPRD-P1 AC-961-4（AC-R2P-11-3） | 牆鐘上限邊界（BRIDGE_ROUTE_TIMEOUT_SECONDS＝300；D-105）：299 秒仍執行、300 秒觸發逾時、301 秒不再接受後續步驟。（預定載具：test_research_route_exec.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-4-E-3` | TCS-ResearchToPRD-P1 AC-961-4（AC-R2P-11-3） | 牆鐘逾時的負控：未逾時的長流程不誤殺，逾時後已成功步驟與其副作用原地保留。（預定載具：test_research_route_exec.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-5-1` | TCS-ResearchToPRD-P1 AC-961-5（AC-R2P-12-1） | 於獨立 worktree 建立 feature/issue-<NNNN>：基底 ref 預設 main，主工作樹 HEAD、狀態與 index 前後相同。（預定載具：test_research_route_a.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-5-2` | TCS-ResearchToPRD-P1 AC-961-5（AC-R2P-12-1、AC-R2P-12-5） | 分支已存在回 409 且零變更；基底 ref 不存在使 GIT_SWITCH 失敗，後續發佈與綁定不執行，可重試。（預定載具：test_research_route_a.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-5-3` | TCS-ResearchToPRD-P1 AC-961-5（AC-R2P-12-2） | 發佈 PRD：位元組相同的複本到目標落點，其 sha256 等於 Gate 0 凍結摘要對應項，feature 分支上有一筆繁體中文 commit。（預定載具：test_research_route_a.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-5-4` | TCS-ResearchToPRD-P1 AC-961-5（AC-R2P-12-6） | 分支變更只含 PRD 發佈檔與落點 stub：根 CLAUDE.md、.claude、落點 SSOT 與 tools 零變更（D-101）。（預定載具：test_research_route_a.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-5-5` | TCS-ResearchToPRD-P1 AC-961-5（AC-R2P-12-4） | Console 專案綁定回填：Bridge 收到 console_project_id 後寫入路由列與研究專案列，並於游標與事件反映。（預定載具：test_research_route_a.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-5-6` | TCS-ResearchToPRD-P1 AC-961-5（AC-R2P-12-1） | 主工作樹零擾動壓力：主工作樹上有進行中的修改（含衝突標記檔與已暫存刪除）時，分流仍成功且這些修改不被觸碰。（預定載具：test_research_route_a.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-5-E-1` | TCS-ResearchToPRD-P1 AC-961-5（AC-R2P-12-5） | 軌道 A 的檔案發佈在 worktree 內原子完成：發佈中途故障不留半寫檔。（預定載具：test_research_route_a.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-6-1` | TCS-ResearchToPRD-P1 AC-961-6（AC-R2P-13-8） | python-fastapi 範本展開的檔案集合與確定性：兩次展開逐檔 sha256 相同，無網路、無 LLM。（預定載具：test_research_scaffold.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-6-2` | TCS-ResearchToPRD-P1 AC-961-6（AC-R2P-13-8） | 範本變數字元集 [A-Za-z0-9_-] 與輸出路徑必須在新根之下：非法變數與路徑逃逸一律拒絕。（預定載具：test_research_scaffold.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-6-3` | TCS-ResearchToPRD-P1 AC-961-6（AC-R2P-13-8） | .env.example 只含 <YOUR_…> 佔位符：掃描展開樹不得出現真值樣式。（預定載具：test_research_scaffold.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-6-4` | TCS-ResearchToPRD-P1 AC-961-6（AC-R2P-13-2） | 複製研究工作區：新專案根含 00_research 至 03_execution 完整副本逐檔 sha256 相同，原工作區原地保留。（預定載具：test_research_route_b.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-6-5` | TCS-ResearchToPRD-P1 AC-961-6（AC-R2P-13-5、AC-R2P-13-2） | 初始 commit：git ls-files 不含 00_research/raw 與 .env，且等於預演的 will_commit 清單，全域 git config 不被改動。（預定載具：test_research_route_b.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-6-6` | TCS-ResearchToPRD-P1 AC-961-6（AC-R2P-13-4、AC-R2P-13-2） | gh 建遠端：argv 精確、可見性旗標正確、GH_TOKEN 只進 gh 子行程環境。（預定載具：test_research_route_b.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-6-7` | TCS-ResearchToPRD-P1 AC-961-6（AC-R2P-13-4） | token 零外洩：含假 token 的夾具下，日誌、資料庫、HTTP 回應、argv 紀錄、稽核與步驟尾端文字皆零命中。（預定載具：test_research_route_b.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-6-8` | TCS-ResearchToPRD-P1 AC-961-6（AC-R2P-13-4） | gh 失敗路徑：token 缺失、權限不足、gh 不存在時該步失敗並顯示原因，本地步驟結果保留，重試只重做遠端步驟。（預定載具：test_research_route_b.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-6-9` | TCS-ResearchToPRD-P1 AC-961-6（AC-R2P-13-8） | 範本的最小 pytest 在展開後的新專案內可跑並通過（供既有 evaluator 綁定）。（預定載具：test_research_scaffold.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-6-E-1` | TCS-ResearchToPRD-P1 AC-961-6（AC-R2P-13-2） | scaffold 根約束：目標不在 BRIDGE_SCAFFOLD_ROOT 之下或根未設，一律拒絕。（預定載具：test_research_route_b.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-6-E-2` | TCS-ResearchToPRD-P1 AC-961-6（AC-R2P-13-4） | token 脫敏函式的邊界：遮罩涵蓋 gh 常見 token 前綴、多行輸出、尾端截斷後仍不洩漏。（預定載具：test_research_route_b.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-7-1` | TCS-ResearchToPRD-P1 AC-961-7（AC-R2P-11-7） | 採納序列：show 建檔、五次 transition、spec-frozen --stage Stage-1，真 CLI 於暫存狀態目錄實跑，終態 SPEC_FROZEN。（預定載具：test_research_adopt.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-7-2` | TCS-ResearchToPRD-P1 AC-961-7（AC-R2P-11-7） | 逐字證據：內環 Stage-1 的 PRD 摘要等於外環 Gate 0 凍結摘要對應項，root 為目標根。（預定載具：test_research_adopt.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-7-3` | TCS-ResearchToPRD-P1 AC-961-7（AC-R2P-11-7） | impl_fsm_project 與 impl_state_dir 入庫：鍵名文法、狀態目錄在 allowed roots 且為 build/reports/fsm。（預定載具：test_research_adopt.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-7-4` | TCS-ResearchToPRD-P1 AC-961-7（AC-R2P-11-7、AC-R2P-11-3） | 內環鍵已存在或採納中斷：續做以 show 現態為憑，不重做已完成的 transition；建檔前鍵檔已存在且現態不合法回 409。（預定載具：test_research_adopt.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-7-5` | TCS-ResearchToPRD-P1 AC-961-7（AC-R2P-11-7） | HUMAN_PENDING 採納值只在內環鍵、現態 SCG_VALIDATION 且 reason 以 baseline adoption 起頭時被放行（既有檢查函式不被繞過）。（預定載具：test_research_adopt.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-7-6` | TCS-ResearchToPRD-P1 AC-961-7（AC-R2P-11-7） | FSM 子行程環境：白名單重建、內環鍵沿既有行為不強制關閉自動恢復，外環鍵仍固定關閉。（預定載具：test_research_adopt.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-7-7` | TCS-ResearchToPRD-P1 AC-961-7（AC-R2P-14-7） | 第二個理由前綴 tcs gate（D-97）：只在內環鍵、現態 SCG_VALIDATION 且該鍵已有 Stage-1 凍結時放行 transition --to HUMAN_PENDING，動詞集合不變。（預定載具：test_research_fsm_ops.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-7-E-1` | TCS-ResearchToPRD-P1 AC-961-7（AC-R2P-11-7） | 外環鍵於分流後不被改動：停在 SPEC_FROZEN，狀態檔位元組不變，FSM 呼叫紀錄對外環鍵只有唯讀的 show。（預定載具：test_research_adopt.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-7-E-2` | TCS-ResearchToPRD-P1 AC-961-7（AC-R2P-11-7） | 採納序列的計數釘住：恰 1 次 show、5 次 transition、1 次 spec-frozen，且沒有 gate、resume 類動詞。（預定載具：test_research_adopt.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-8-1` | TCS-ResearchToPRD-P1 AC-961-8（AC-R2P-13-4） | gitops 允許集合表驅動：每個 P1 允許形態通過驗證，組出的 argv 為陣列且不經 shell。（預定載具：test_research_gitops.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-8-2` | TCS-ResearchToPRD-P1 AC-961-8（AC-R2P-13-4） | 禁止形態逐一被拒：強推、硬重設、clean、stash、檢出路徑、restore 路徑、switch -f、全域與系統層 config。（預定載具：test_research_gitops.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-8-3` | TCS-ResearchToPRD-P1 AC-961-8（AC-R2P-13-4、AC-R2P-11-5） | 使用者可影響的 argv 片段先過列舉或正規式：選項注入與 shell 元字元一律拒絕。（預定載具：test_research_gitops.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-8-4` | TCS-ResearchToPRD-P1 AC-961-8（AC-R2P-13-4） | 子行程形態：argv 陣列、shell 為假、環境白名單重建、經 popen_platform_kwargs，且不寫入使用者家目錄設定。（預定載具：test_research_gitops.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-8-5` | TCS-ResearchToPRD-P1 AC-961-8（AC-R2P-13-4） | 能力登記：git 與 gh 子行程只住 gitops；新模組先登記 CAPABILITY 與 EXEC_MODULES，未登記即紅。（預定載具：test_research_ast_locks.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-8-6` | TCS-ResearchToPRD-P1 AC-961-8（AC-R2P-13-4、AC-R2P-11-7） | FSM 單一寫入面不被破壞：新模組不含 tools.fsm_runtime、字面值 spec-frozen 與 spec-refreeze；create_key 呼叫者集合含 :route 路徑。（預定載具：test_research_ast_locks.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-8-7` | TCS-ResearchToPRD-P1 AC-961-8（AC-R2P-13-4） | 白名單範圍不變：RESEARCH_VERBS 集合與既有 ALLOWED_VERBS 不變，resume-from-escalation 仍不入。（預定載具：test_research_gitops.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-8-E-1` | TCS-ResearchToPRD-P1 AC-961-8（AC-R2P-13-4） | git 與 gh 的 stderr、stdout 回傳給呼叫端前先脫敏並截尾，且 gitops 不對外洩漏絕對路徑以外的環境資訊。（預定載具：test_research_gitops.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-8-E-2` | TCS-ResearchToPRD-P1 AC-961-8（AC-R2P-13-4） | push 目的限定：只准 origin 與已驗證的分支，refspec 不得帶強推前綴。（預定載具：test_research_gitops.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-9-1` | TCS-ResearchToPRD-P1 AC-961-9（AC-R2P-14-7） | tcs-draft 前置：分流 SUCCEEDED、內環鍵 SPEC_FROZEN 且恰有 Stage-1 凍結、已有拆解列（D-110）、無進行中 stage、無 open SCR；任一不成立回 409 並逐條列 unmet。（預定載具：test_research_tcs_draft.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-9-2` | TCS-ResearchToPRD-P1 AC-961-9（AC-R2P-14-7） | tcs-draft 的 stage run：DB 記 TCS_DRAFT、編譯為最小授權的 spec-engineer run、prompt-by-reference。（預定載具：test_research_tcs_draft.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-9-3` | TCS-ResearchToPRD-P1 AC-961-9（AC-R2P-14-7） | TCS 確定性驗證（即 SCG 預檢，D-109）：AT 與凍結 AC 一一對映、AC 全涵蓋、判定指令非空、無機密、檔名合 _freeze 規則，任一不過 stage 失敗且內環鍵留在 SPEC_DRAFTING。（預定載具：test_research_tcs_draft.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-9-4` | TCS-ResearchToPRD-P1 AC-961-9（AC-R2P-14-7） | TCS 發佈與登記：通過後發佈到目標 docs/03_testing/contracts，內環鍵依序 transition 到 SCG_VALIDATION 與 HUMAN_PENDING（理由前綴 tcs gate），游標 TCS_PENDING。（預定載具：test_research_tcs_draft.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-9-5` | TCS-ResearchToPRD-P1 AC-961-9（AC-R2P-14-7） | TCS 凍結仍走既有 :freeze：帶 TCS 時成功並使內環鍵含 Stage-2，不帶 TCS 時仍 422 missing_tcs；Bridge 不自動凍結。（預定載具：test_research_tcs_draft.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-9-6` | TCS-ResearchToPRD-P1 AC-961-9（AC-R2P-14-7） | Stage-2 未凍結時 Bridge 內環鍵現態可被 console-api 讀到且不被 Bridge 自己放行執行（執行閘在 console-api，D-102）。（預定載具：test_research_tcs_draft.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-9-7` | TCS-ResearchToPRD-P1 AC-961-9（AC-R2P-14-7） | mock-only 下 tcs-draft 可跑：劇本含 (tcs-draft, 0)，Docker 全棧以 mock claude 走完草擬。（預定載具：test_research_tcs_draft.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-9-E-1` | TCS-ResearchToPRD-P1 AC-961-9（AC-R2P-14-7） | TCS 草擬不碰已凍結的規格：已發佈 PRD 與 Gate 0 凍結檔位元組不變。（預定載具：test_research_tcs_draft.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-9-E-2` | TCS-ResearchToPRD-P1 AC-961-9（AC-R2P-14-7） | tcs-draft 重試與重拆承接：驗證失敗後再啟動走完成功路徑；重拆產生新拆解列時承接前一列的 tcs_rel_path 與 tcs_sha256（D-110）。（預定載具：test_research_tcs_draft.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-10-1` | TCS-ResearchToPRD-P1 AC-961-10（AC-R2P-14-1） | 觸發拆解（Bridge :decompose，同步 HTTP、非 stage run）：逐 US 呼叫既有拆解服務，covers_ac 由該次呼叫綁定的 AC 清單確定性賦值，產生草稿與 R8 列。（預定載具：test_research_decompose.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-10-2` | TCS-ResearchToPRD-P1 AC-961-10（AC-R2P-14-1） | 三道有界閘：超過 24 步、有環、空 prompt 任一不過回 422 結構化錯誤，不截斷、不自動修剪。（預定載具：test_research_decompose.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-10-3` | TCS-ResearchToPRD-P1 AC-961-10（AC-R2P-14-2） | 覆蓋對映：凍結 PRD 的每個 AC 至少被一個 task 的 covers_ac 涵蓋，未覆蓋者逐一列出，未知 AC 編號被拒。（預定載具：test_research_decompose.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-10-4` | TCS-ResearchToPRD-P1 AC-961-10（AC-R2P-14-2） | 簽核前置：未覆蓋者清零或各有人工豁免才可寫入 SIGNED_OFF；豁免理由 1 至 500 字、各自成筆（D-113 單一寫入時點）。（預定載具：test_research_decompose.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-10-5` | TCS-ResearchToPRD-P1 AC-961-10（AC-R2P-14-5） | stale：PRD 凍結摘要與拆解的 prd_sha256 不符時，拆解標 STALE。（預定載具：test_research_decompose.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-10-6` | TCS-ResearchToPRD-P1 AC-961-10（AC-R2P-14-6） | DB 與檔案逐欄相等：task_decomposition.json 的 sha256 與 R8 列相符，簽核版本的正式 goals 與 tasks 數量相等。（預定載具：test_research_decompose.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-10-7` | TCS-ResearchToPRD-P1 AC-961-10（AC-R2P-14-1） | 重拆＝新版本：已簽核草稿不可變，只有已簽核的最新版為有效。（預定載具：test_research_decompose.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-10-8` | TCS-ResearchToPRD-P1 AC-961-10（AC-R2P-14-1） | 按 Goal 分批拆解：大型 PRD 單次逾 24 步被拒，改按 Goal 分批後每批不超過 24 步、總數可超過 24。（預定載具：test_research_decompose.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-10-E-1` | TCS-ResearchToPRD-P1 AC-961-10（AC-R2P-14-1） | planner 不得繞過人工 signoff：任何拆解路徑都不會產生 signed_off 為真的草稿，也不呼叫 FSM gate 類動詞。（預定載具：test_research_decompose.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-11-1` | TCS-ResearchToPRD-P1 AC-961-11（AC-R2P-14-3、AC-R2P-14-2） | 簽核：OPERATOR 以上對 POST decomposition/signoff 送出，經既有 import／signoff 服務（不走 HTTP 迴圈）落為正式專案、目標、任務並關聯研究專案。（預定載具：ResearchDecompositionApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-11-2` | TCS-ResearchToPRD-P1 AC-961-11（AC-R2P-14-3） | 簽核的角色與輸入：approver 取 JWT subject；憑證無 subject 回 400、VIEWER 403、匿名 401、ADMIN 同 OPERATOR；本文帶 approver 不被採用。（預定載具：ResearchDecompositionApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-11-3` | TCS-ResearchToPRD-P1 AC-961-11（AC-R2P-14-4） | 未簽核草稿啟動執行回 409，execute、resume、restore 三個入口皆二次校驗，前端停用只是體驗。（預定載具：ResearchDecompositionApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-11-4` | TCS-ResearchToPRD-P1 AC-961-11（AC-R2P-14-5） | 拆解 stale 時啟動執行回 409 decomposition_stale（console-api 側只驗 409 與透傳形狀；STALE 的寫入歸 Bridge 側 AT-961-10-5）。（預定載具：ResearchDecompositionApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-11-5` | TCS-ResearchToPRD-P1 AC-961-11（AC-R2P-14-4） | SCR 開啟期間啟動執行回 409 scr_open，內環唯讀。（預定載具：ResearchDecompositionApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-11-6` | TCS-ResearchToPRD-P1 AC-961-11（AC-R2P-14-7） | TCS 未凍結時內環 run 啟動回 409 fsm_state_conflict（D-102：既有啟動服務的單一前置守衛），凍結後放行。（預定載具：ResearchDecompositionApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-11-7` | TCS-ResearchToPRD-P1 AC-961-11（AC-R2P-14-1） | POST decomposition（觸發）：OPERATOR 以上、Bridge 同步呼叫讀逾時 330 秒、422 結構化錯誤逐字透傳，VIEWER 403。（預定載具：ResearchDecompositionApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-11-E-1` | TCS-ResearchToPRD-P1 AC-961-11（AC-R2P-14-3） | 軌道 B 的 Console 專案 execution_path 為新專案根，須在 allowlist 根之下，否則建專案被拒。（預定載具：ResearchDecompositionApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-11-E-2` | TCS-ResearchToPRD-P1 AC-961-11（AC-R2P-14-4） | 回歸：非研究專案的 Console 專案啟動執行完全不受 D-102 前置守衛影響。（預定載具：ResearchDecompositionApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-12-1` | TCS-ResearchToPRD-P1 AC-961-12（AC-R2P-19-1） | 發起 MINOR SCR：寫 research_scr 列、停止進行中 run、新的執行回 409 scr_open、凍結 PRD 位元組不變、游標進 SCR_OPEN。（預定載具：test_research_scr.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-12-2` | TCS-ResearchToPRD-P1 AC-961-12（AC-R2P-19-5） | SCR 輸入閘：理由、分類、受影響章節三類違規各自成筆，零 research_scr 列、零 FSM 呼叫、游標不變。（預定載具：test_research_scr.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-12-3` | TCS-ResearchToPRD-P1 AC-961-12（AC-R2P-19-3） | SCR 開啟而新 Gate 0 尚未完成時，恢復舊 run 回 409 scr_open，內環唯讀。（預定載具：test_research_scr.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-12-4` | TCS-ResearchToPRD-P1 AC-961-12（AC-R2P-19-6） | MINOR 上限（D-104 保守計）：同一研究專案內 kind 為 MINOR 且 status 為 OPEN、APPROVED 或 APPLIED 的列已有 2 筆，第 3 次回 409 scr_limit 並要求改 MAJOR。（預定載具：test_research_scr.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-12-5` | TCS-ResearchToPRD-P1 AC-961-12（AC-R2P-19-4） | MAJOR SCR：建立新研究專案（parent、slug、新外環鍵），舊專案游標不變，舊內環鍵不動。（預定載具：test_research_scr.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-12-6` | TCS-ResearchToPRD-P1 AC-961-12（AC-R2P-19-7） | 來源類別 HEALING_FAILED：只產生 resume-from-escalation 指令與 research_scr 記錄，不呼叫任何 FSM 寫入動詞。（預定載具：test_research_scr.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-12-7` | TCS-ResearchToPRD-P1 AC-961-12（AC-R2P-19-1、AC-R2P-19-3） | 同一專案同時只有一筆 OPEN 的 SCR：已有 OPEN 時再發起回 409 scr_open。（預定載具：test_research_scr.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-12-E-1` | TCS-ResearchToPRD-P1 AC-961-12（AC-R2P-19-1） | 發起 SCR 時沒有進行中 run 不是錯誤：:stop 為冪等，SCR 仍成立。（預定載具：test_research_scr.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-13-1` | TCS-ResearchToPRD-P1 AC-961-13（AC-R2P-19-8、AC-R2P-19-2） | MINOR 收尾序列於暫存狀態目錄實跑：外環重走、Gate-0-SCR 核准、內環五步，decision_trace 等於人工等價序列。（預定載具：test_research_scr_fsm.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-13-2` | TCS-ResearchToPRD-P1 AC-961-13（AC-R2P-19-8） | 內環現態矩陣：IMPLEMENTATION、EXECUTION_EVALUATION、ADVERSARIAL_EVALUATION、PR_REVIEW 直接起跑，SPEC_AUDIT 現態略過第一個 transition。（預定載具：test_research_scr_fsm.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-13-3` | TCS-ResearchToPRD-P1 AC-961-13（AC-R2P-19-8） | RTM_VERIFY 與 RELEASE_READY 現態：先 gate FAIL 退回 IMPLEMENTATION 再起跑，回傳不是 IMPLEMENTATION 即回報 BLOCKED 不重試。（預定載具：test_research_scr_fsm.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-13-4` | TCS-ResearchToPRD-P1 AC-961-13（AC-R2P-19-8） | 現態不在矩陣內（含任何 ESCALATION*）回 409 fsm_state_conflict，零 FSM 寫入、不起跑。（預定載具：test_research_scr_fsm.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-13-5` | TCS-ResearchToPRD-P1 AC-961-13（AC-R2P-19-8） | gate PR_REVIEW FAIL 被判同模式而改走 SPEC_AUDIT 時回報 BLOCKED，不重試。（預定載具：test_research_scr_fsm.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-13-6` | TCS-ResearchToPRD-P1 AC-961-13（AC-R2P-19-2） | 新版本與舊凍結版：Gate-0-SCR 核准後版本遞增、新增 R6 列，舊凍結版保留可比對，SCR 轉 APPLIED，既有拆解標 STALE。（預定載具：test_research_scr_fsm.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-13-7` | TCS-ResearchToPRD-P1 AC-961-13（AC-R2P-19-4） | 游標：SCR(MINOR) 發起後在 studio／SCR_OPEN，新 Gate 0 完成並發佈後回 build（Target Scope 變更才回 route）。（預定載具：test_research_scr_fsm.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-13-8` | TCS-ResearchToPRD-P1 AC-961-13（AC-R2P-19-8） | 發佈順序與失敗：SPEC_AUDIT 之後才發佈；發佈失敗中止序列並記錄到失敗處。（預定載具：test_research_scr_fsm.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-13-9` | TCS-ResearchToPRD-P1 AC-961-13（AC-R2P-19-8） | spec-refreeze 的參數與子行程環境：--doc 為目標 docs 相對路徑、--root 為目標根、--approver 為 JWT subject。（預定載具：test_research_scr_fsm.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-13-E-1` | TCS-ResearchToPRD-P1 AC-961-13（AC-R2P-19-2） | 預算重新計：SCR 重走起草後，Gate-0-SCR 核准時四個閘的計數一併歸零。（預定載具：test_research_scr_fsm.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-13-E-2` | TCS-ResearchToPRD-P1 AC-961-13（AC-R2P-19-8） | 序列中任一步 FSM 非 0 結束即停止：後續不執行，impl_fsm_actions 含失敗步驟。（預定載具：test_research_scr_fsm.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-13-E-3` | TCS-ResearchToPRD-P1 AC-961-13（AC-R2P-19-8） | 核准即套用失敗不留空窗：apply_minor 失敗時 SCR 停在 APPROVED，回應帶 scr_apply 狀態，ADMIN 以 :scr-apply 重試，重試冪等。（預定載具：test_research_scr_fsm.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-14-1` | TCS-ResearchToPRD-P1 AC-961-14（AC-R2P-11-2、AC-R2P-11-6） | route/preview：OPERATOR 以上、輸入閘先於 Bridge、Bridge 的缺項 422 逐字透傳。（預定載具：ResearchRouteApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-14-2` | TCS-ResearchToPRD-P1 AC-961-14（AC-R2P-11-8） | route 確認僅 ADMIN：OPERATOR 與 VIEWER 皆 403，Bridge 請求數 0、projects 列 0。（預定載具：ResearchRouteApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-14-3` | TCS-ResearchToPRD-P1 AC-961-14（AC-R2P-11-8、AC-R2P-12-4） | 先建 projects 列再呼 Bridge：順序可觀察，execution_path 取自預演回應，同 (execution_path, sdd_project) 只能綁一個專案。（預定載具：ResearchRouteApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-14-4` | TCS-ResearchToPRD-P1 AC-961-14（AC-R2P-11-8） | 失敗補償到安全態：projects 列標 ARCHIVED 並留稽核，不自動清理，且 Bridge 請求紀錄不含清理類呼叫。（預定載具：ResearchRouteApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-14-5` | TCS-ResearchToPRD-P1 AC-961-14（AC-R2P-11-8） | route_conflict 先於建專案列：已有 PENDING、RUNNING、SUCCEEDED 的分流回 409，零 projects 寫入。（預定載具：ResearchRouteApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-14-6` | TCS-ResearchToPRD-P1 AC-961-14（AC-R2P-13-4） | GitHub token：取自 system_configs 加密欄，單次請求傳給 Bridge，不入 DTO、回應、日誌、audit_log 與 toString。（預定載具：ResearchRouteApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-14-7` | TCS-ResearchToPRD-P1 AC-961-14（AC-R2P-11-3、AC-R2P-12-4） | GET route：回 RouteDecisionDto 與 steps，V+ 可讀，無分流時回空而非 404。（預定載具：ResearchRouteApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-14-8` | TCS-ResearchToPRD-P1 AC-961-14（AC-R2P-11-3） | route 與 decomposition 的 Bridge 呼叫讀逾時為 330 秒（Bridge 牆鐘上限 300 秒＋緩衝，D-105），其餘寫入呼叫維持 30 秒；Bridge 牆鐘逾時回 502 route_step_failed 而非 504 的語意。（預定載具：ResearchRouteApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-14-E-1` | TCS-ResearchToPRD-P1 AC-961-14（AC-R2P-11-4） | scopeDiffersReason 在 console-api 先判：軌道與 PRD target_scope 不同而缺理由回 422，相同時不要求。（預定載具：ResearchRouteApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-14-E-2` | TCS-ResearchToPRD-P1 AC-961-14（AC-R2P-11-3） | approver 只取 JWT subject：請求本文帶 approver 不被採信；欄位轉換 camelCase 與 snake_case 完整。（預定載具：ResearchRouteApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-15-1` | TCS-ResearchToPRD-P1 AC-961-15（AC-R2P-19-1、AC-R2P-19-5） | POST scr 與 GET scr：角色、輸入閘、MINOR 與 MAJOR 回應、HEALING_FAILED 的指令回應。（預定載具：ResearchScrApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-15-2` | TCS-ResearchToPRD-P1 AC-961-15（AC-R2P-14-1、AC-R2P-14-5） | GET decomposition：回 DecompositionDto（IFACE §3.1）：有效拆解、覆蓋、豁免與 stale 旗標，無拆解回 200 null，V+ 可讀。（預定載具：ResearchDecompositionApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-15-3` | TCS-ResearchToPRD-P1 AC-961-15（AC-R2P-14-1、AC-R2P-19-1） | OpenAPI：P1 新增 6 條路徑與 9 個操作（總數 107 條路徑、124 個操作），operationId 與契約一致，回應碼表補列；數字由實際新增路徑與操作自算。（預定載具：OpenApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-15-4` | TCS-ResearchToPRD-P1 AC-961-15（AC-R2P-19-1、AC-R2P-19-6、AC-R2P-14-5） | reason 四處集合相等：P0 的 22 個、P0 未結 R-2 的 4 個、P1 的 9 個（共 35 個），後端常數、前端 RESEARCH_REASONS、契約、Architecture 研究 reason 表、OpenAPI 說明一致。（預定載具：ResearchReasonsTest） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-15-5` | TCS-ResearchToPRD-P1 AC-961-15（AC-R2P-14-1、AC-R2P-14-5） | ArchUnit 字串掃描：console-api 對 research_ 與 V19 表零寫入，新讀配接器只用 JdbcClient 查詢。（預定載具：ResearchArchTest） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-15-6` | TCS-ResearchToPRD-P1 AC-961-15（AC-R2P-19-1、AC-R2P-14-1） | 角色矩陣：route 與 scr/apply 僅 ADMIN；route/preview、scr、decomposition、decomposition/signoff 為 OPERATOR 以上；三個 GET 為 VIEWER 以上。（預定載具：RbacIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-15-7` | TCS-ResearchToPRD-P1 AC-961-15（AC-R2P-14-1） | ResearchFlowPolicy 的 P1 衍生規則表驅動：route、TCS 相態直接取游標，build 相態依 Console 專案與 FSM 衍生，SCR_OPEN 原樣取用。（預定載具：ResearchFlowPolicyTest） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-15-8` | TCS-ResearchToPRD-P1 AC-961-15（AC-R2P-19-1、AC-R2P-14-1） | 源頭鎖：P1 的 Bridge 常數（路由步驟名、路由與 SCR 狀態、reason、事件型別）被 console-api 的契約形狀認得。（預定載具：ResearchBridgeShapeTest） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-15-9` | TCS-ResearchToPRD-P1 AC-961-15（AC-R2P-11-1、AC-R2P-11-4） | ResearchProjectDetail 帶唯讀 targetScope（取自 research_projects.target_scope），供預選卡與差異判斷（D-107）。（預定載具：ResearchApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-15-E-1` | TCS-ResearchToPRD-P1 AC-961-15（AC-R2P-19-1） | console-api 透傳 Bridge 的結構化錯誤：狀態碼與 reason 與 details 逐字不變，且 POST 不重試。（預定載具：ResearchRouteApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-15-E-2` | TCS-ResearchToPRD-P1 AC-961-15（AC-R2P-21-2） | P0 未結 R-1（D-123 歸 API-P1）：404 文案依 details 或路徑區分，allowlist 條目不存在不再寫成研究專案不存在（reason 仍為 research_not_found）。（預定載具：ResearchApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-16-1` | TCS-ResearchToPRD-P1 AC-961-16（AC-R2P-04-11、AC-R2P-13-7） | capabilities 十三鍵不變、值取真：scaffold_root、scaffold_templates、repo_writable 在 P1 取實值；gh_cli.authenticated 維持 NOT-EVALUABLE（D-98）。（預定載具：test_research_capabilities_p1.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-16-2` | TCS-ResearchToPRD-P1 AC-961-16（AC-R2P-04-11） | /health/deep 的 research 物件鍵集合維持八個，mode 判定不變，P1 值語意更新。（預定載具：test_research_capabilities_p1.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-16-3` | TCS-ResearchToPRD-P1 AC-961-16（AC-R2P-11-6、AC-R2P-04-11） | 容器模式：無 gh、repo 唯讀、未設 scaffold 根時 capabilities 如實回報，預演回缺項。（預定載具：test_research_capabilities_p1.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-16-4` | TCS-ResearchToPRD-P1 AC-961-16（AC-R2P-04-11、AC-R2P-13-7） | console-api 的 CapabilitiesDto：P1 欄位 camelCase 轉出、快取 30 秒、不透出內部路徑以外的環境資訊。（預定載具：ResearchRouteApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-16-5` | TCS-ResearchToPRD-P1 AC-961-16（AC-R2P-11-6、AC-R2P-04-11、AC-R2P-13-7） | 前端依 capabilities 缺項停用控件並說明（D-114、IFACE §8.3）：git 缺→預演與確認兩軌皆停用；repoWritable 假→軌道 A 卡；ghCli.ok 假→僅 GitHub 勾選；scaffoldRoot 為 null 或範本空→軌道 B 卡；mock-only→兩軌皆停用。（預定載具：components/domain/research/RouteDrawer.test.tsx） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-16-E-1` | TCS-ResearchToPRD-P1 AC-961-16（AC-R2P-13-7） | scaffold_templates 的目錄掃描規則：只認合法名稱、含必要檔的目錄；非法或空目錄不列。（預定載具：test_research_capabilities_p1.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-16-E-2` | TCS-ResearchToPRD-P1 AC-961-16（AC-R2P-04-11） | capabilities 載入失敗時步驟 3 顯示錯誤態，不假裝可用。（預定載具：components/domain/research/RouteDrawer.test.tsx） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-17-1` | TCS-ResearchToPRD-P1 AC-961-17（AC-R2P-11-1） | Gate 0 核准後進入第 3 步：抽屜顯示卡 A、卡 B 與評估維度表，依 PRD target_scope 預選其一，再進入可重開。（預定載具：components/domain/research/RouteDrawer.test.tsx） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-17-2` | TCS-ResearchToPRD-P1 AC-961-17（AC-R2P-11-1） | Gate 0 未完成：步驟 3 顯示阻擋頁並連回步驟 2，無任何寫入控件。（預定載具：components/domain/research/RoutePanel.test.tsx） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-17-3` | TCS-ResearchToPRD-P1 AC-961-17（AC-R2P-11-4、AC-R2P-12-3） | 卡 A 欄位：分支名預設 feature/issue-<NNNN>、基底 ref 預設 main、掛載目標下拉取自落點目標清單並附出處。（預定載具：components/domain/research/RouteDrawer.test.tsx） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-17-4` | TCS-ResearchToPRD-P1 AC-961-17（AC-R2P-13-3、AC-R2P-13-7） | 卡 B 欄位：專案名稱、owner、庫名、範本下拉取自 capabilities、GitHub 設定預設 Private、Public 需輸入庫名確認並顯示公開警告、CI 與 compose 勾選。（預定載具：components/domain/research/RouteDrawer.test.tsx） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-17-5` | TCS-ResearchToPRD-P1 AC-961-17（AC-R2P-11-2） | 預演面板：OPERATOR 可預演，動作清單以純文字渲染並標示外部系統，預演不改任何狀態。（預定載具：components/domain/research/RouteDrawer.test.tsx） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-17-6` | TCS-ResearchToPRD-P1 AC-961-17（AC-R2P-11-5、AC-R2P-11-6、AC-R2P-11-4） | 確認僅 ADMIN；差異警示與一句理由必填；VIEWER 全面停用且 title 為權限不足。（預定載具：components/domain/research/RouteDrawer.test.tsx） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-17-7` | TCS-ResearchToPRD-P1 AC-961-17（AC-R2P-11-3） | 逐步進度與失敗重試：執行中顯示進度清單，部分失敗顯示失敗步驟與原因並提供重試，完成後唯讀摘要與前往下一步。（預定載具：components/domain/research/RoutePanel.test.tsx） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-17-8` | TCS-ResearchToPRD-P1 AC-961-17（AC-R2P-11-6） | 部署不支援的錯誤態：預演 422 route_unsupported_in_deployment 時指出缺項，續做時還原已選卡與參數。（預定載具：components/domain/research/RoutePanel.test.tsx） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-17-E-1` | TCS-ResearchToPRD-P1 AC-961-17（AC-R2P-13-3） | Public 確認的邊界：差一個字元、大小寫不同、尾端空白、貼上不可見字元皆視為不符。（預定載具：components/domain/research/RouteDrawer.test.tsx） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-17-E-2` | TCS-ResearchToPRD-P1 AC-961-17（AC-R2P-11-5、AC-R2P-13-3、AC-R2P-11-4） | 前端分流常數與後端單一來源對拍：分支名與庫名正規式、理由上限、SCR 上限皆與契約字面相等。（預定載具：lib/domain/research.test.ts） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-18-1` | TCS-ResearchToPRD-P1 AC-961-18（AC-R2P-14-1、AC-R2P-14-2） | 拆解面板：空狀態與觸發拆解、草稿樹、覆蓋矩陣與未覆蓋清單。（預定載具：components/domain/research/BuildFrontPanel.test.tsx） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-18-2` | TCS-ResearchToPRD-P1 AC-961-18（AC-R2P-14-2、AC-R2P-14-3） | 簽核鈕：未覆蓋者清零或各有一句豁免理由前停用，簽核者為目前使用者，理由 500 字界。（預定載具：components/domain/research/BuildFrontPanel.test.tsx） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-18-3` | TCS-ResearchToPRD-P1 AC-961-18（AC-R2P-14-5） | stale 狀態：PRD 更新後拆解標過期，顯示說明與重新拆解入口，已簽核後唯讀。（預定載具：components/domain/research/BuildFrontPanel.test.tsx） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-18-4` | TCS-ResearchToPRD-P1 AC-961-18（AC-R2P-14-7） | TCS 草擬面板：內環鍵已採納才可草擬，顯示草擬中、待凍結、已凍結三態與路徑雜湊，凍結連到既有介面。（預定載具：components/domain/research/BuildFrontPanel.test.tsx） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-18-5` | TCS-ResearchToPRD-P1 AC-961-18（AC-R2P-14-3、AC-R2P-14-5） | 到既有 freeze、import、execute 的連結與執行閘說明：未簽核或未凍結時執行連結停用並說明原因。（預定載具：components/domain/research/BuildFrontPanel.test.tsx） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-18-6` | TCS-ResearchToPRD-P1 AC-961-18（AC-R2P-14-1） | SCR 開啟時本面板的操作停用並說明（與後端 409 scr_open 一致）。（預定載具：components/domain/research/BuildFrontPanel.test.tsx） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-18-7` | TCS-ResearchToPRD-P1 AC-961-18（AC-R2P-14-1） | Bridge 或 API 不可用時顯示錯誤態與快取，不顯示空白。（預定載具：components/domain/research/BuildFrontPanel.test.tsx） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-18-E-1` | TCS-ResearchToPRD-P1 AC-961-18（AC-R2P-14-2） | 覆蓋矩陣在大型 PRD 下仍可渲染：200 個 AC 乘 24 個 task 不阻塞互動。（預定載具：components/domain/research/BuildFrontPanel.test.tsx） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-19-1` | TCS-ResearchToPRD-P1 AC-961-19（AC-R2P-21-5） | ?step=route 與 ?step=build 不再是占位，?step=deliver 仍為占位；Gate 0 未完成時超前導回。（預定載具：components/domain/research/ResearchWorkspaceView.test.tsx） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-19-2` | TCS-ResearchToPRD-P1 AC-961-19（AC-R2P-21-2） | 說明三道鎖與寫實內容：research-workspace 的第 3、4 步說明寫實，三道鎖綠，計數不變。（預定載具：lib/help/research-workspace.test.ts） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-19-3` | TCS-ResearchToPRD-P1 AC-961-19（AC-R2P-21-2） | researchFlow 狀態表詞彙涵蓋 P1 相態並與 FLOW_PHASE_LABEL 的鍵一致。（預定載具：components/domain/help/stateKeys.test.ts） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-19-4` | TCS-ResearchToPRD-P1 AC-961-19（AC-R2P-21-5） | FlowStepper 的 route 與 build 步驟狀態：進行中、失敗阻擋、SCR 進行中標示。（預定載具：components/domain/research/FlowStepper.test.tsx） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-19-5` | TCS-ResearchToPRD-P1 AC-961-19（AC-R2P-21-5） | 端點函式與型別：新增 9 個函式（總數 118），operationId 與契約一一對應，schema.d.ts 重產含之，型別與契約 DTO 逐欄相符。（預定載具：lib/api/endpoints.test.ts） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-19-6` | TCS-ResearchToPRD-P1 AC-961-19（AC-R2P-21-5） | 前端靜態鎖遵守：新元件無陰影與漸層、只用設計 token、無手寫 svg、無 emoji、無 outline-none、無 dark:，四區塊名不出現在 app/research。（預定載具：tests/design-rules.test.ts） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-19-E-1` | TCS-ResearchToPRD-P1 AC-961-19（AC-R2P-21-2） | P1 reason 的前端文案表：每個 P1 reason 有中文說明，且不直出伺服器訊息。（預定載具：lib/domain/research.test.ts） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-20-1` | TCS-ResearchToPRD-P1 AC-961-20（AC-R2P-23-1） | route_decision 項：DB 路由決定列與 route_decision.json 的 sha256 對帳，漂移與缺席各判 drift，兩側皆缺席維持 ok 且 present 為假。（預定載具：test_research_reconcile.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-20-2` | TCS-ResearchToPRD-P1 AC-961-20（AC-R2P-23-1） | task_decomposition 項：DB R8 與 task_decomposition.json 對帳，改檔與缺席判 drift。（預定載具：test_research_reconcile.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-20-3` | TCS-ResearchToPRD-P1 AC-961-20（AC-R2P-23-1） | fsm_flow_mapping 對映表增列 P1 DB 游標組合（D-121）：只用 DB 游標值，衍生相態不入對映，TCS_PENDING 加 Stage-2 已凍結列為待校正而非 drift。（預定載具：test_research_reconcile.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-20-4` | TCS-ResearchToPRD-P1 AC-961-20（AC-R2P-23-4） | 分流時點自動對帳：route 成功路徑內恰一筆對帳事件、consistent 為真，失敗路徑不產生。（預定載具：test_research_reconcile.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-20-E-1` | TCS-ResearchToPRD-P1 AC-961-20（AC-R2P-23-1） | 對帳不修任何一邊：兩個新檢查項在漂移時，呼叫前後檔案與 DB 列（事件除外）逐項相同。（預定載具：test_research_reconcile.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-20-E-2` | TCS-ResearchToPRD-P1 AC-961-20（AC-R2P-23-1） | 前端對 pending_correction 的判讀（純函式）：第三態不算漂移，仍可被辨識為待校正。（預定載具：lib/domain/research.test.ts） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-20-E-3` | TCS-ResearchToPRD-P1 AC-961-20（AC-R2P-23-1） | console-api 對帳 DTO 與 OpenAPI 說明涵蓋第三態：ReconcileResultDto 的 status 說明含 pending_correction，並原樣透傳。（預定載具：ResearchApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-20-E-4` | TCS-ResearchToPRD-P1 AC-961-20（AC-R2P-23-1） | 步驟 4 面板渲染對帳結果：pending_correction 顯示「待校正」說明、不顯示漂移警示橫幅，並提供「重新對帳」入口（元件載具，承接 AT-961-20-E-2 的判讀）。（預定載具：components/domain/research/BuildFrontPanel.test.tsx） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-21-1` | TCS-ResearchToPRD-P1 AC-961-21（AC-R2P-02-4） | records/audit 的 V19 口徑：R7、R8 取自路由與拆解表，missing 恰為尚未交付者。（預定載具：ResearchApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-21-2` | TCS-ResearchToPRD-P1 AC-961-21（AC-R2P-02-5） | audit_log：ADMIN 確認分流、OPERATOR 簽核拆解各有一列 2xx 寫入審計，並與 R7、R8 同 trace_id 含 digest 與理由。（預定載具：ResearchApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-21-E-1` | TCS-ResearchToPRD-P1 AC-961-21（AC-R2P-02-5） | 被拒的分流相關寫入請求亦各有一列審計（V6 過濾器對每個 /api 寫入請求恆一列）。（預定載具：ResearchApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-22-1` | TCS-ResearchToPRD-P1 AC-961-22（AC-R2P-12-1、AC-R2P-11-2、AC-R2P-11-7） | 整合鏈（軌道 A）：拋棄式 clone 上預演、確認、發佈、內環鍵採納、對帳，主工作樹零擾動，逐字證據。（預定載具：test_research_int_p1.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-22-2` | TCS-ResearchToPRD-P1 AC-961-22（AC-R2P-13-4、AC-R2P-11-2） | 整合鏈（軌道 B）：暫存 scaffold 根與假 gh 上走完新專案、複製、初始 commit 與遠端，token 零外洩。（預定載具：test_research_int_p1.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-22-3` | TCS-ResearchToPRD-P1 AC-961-22（AC-R2P-14-7、AC-R2P-11-7） | 整合鏈（拆解後 TCS 草擬）：接 22-1，先 :decompose（夾具引擎）再 tcs-draft 以 mock 劇本走完，內環 Stage-2 的 show 逐字證據。（預定載具：test_research_int_p1.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-22-4` | TCS-ResearchToPRD-P1 AC-961-22（AC-R2P-19-8） | 整合鏈（SCR MINOR）：接 22-3 之後（內環已進入 IMPLEMENTATION 的夾具態），SCR 序列端到端，證據與人工等價序列一致。（預定載具：test_research_int_p1.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-22-5` | TCS-ResearchToPRD-P1 AC-961-22（AC-R2P-21-5、AC-R2P-11-6） | Docker 全棧（mock-only）：API 直呼預演回缺項，capabilities 如實，UI 停用兩卡並說明。（預定載具：tests/e2e/research-p1-docker.stack.spec.ts） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-22-6` | TCS-ResearchToPRD-P1 AC-961-22（AC-R2P-21-5） | Docker 全棧：步驟 4 前半與步驟 5 的呈現——build 顯示拆解面板空狀態與停用的草擬，deliver 仍為占位。（預定載具：tests/e2e/research-p1-docker.stack.spec.ts） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-22-7` | TCS-ResearchToPRD-P1 AC-961-22（AC-R2P-21-5） | a11y 與版面：RouteDrawer 與 BuildFrontPanel 在 1440、1000、600 寬度無水平溢出且 axe 無 serious 與 critical，抽屜焦點陷阱與歸還正確。（預定載具：tests/e2e/a11y.mock.spec.ts） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-22-8` | TCS-ResearchToPRD-P1 AC-961-22（AC-R2P-21-5） | P0 既有 E2E 不退步：兩條 Docker 路徑仍綠，唯一改動為占位斷言的預期值。（預定載具：tests/e2e/research-p1-docker.stack.spec.ts） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-22-E-1` | TCS-ResearchToPRD-P1 AC-961-22（AC-R2P-13-4） | 假 gh 夾具兩形態可行：本平台的假 gh 可被 gitops 以 PATH 解析並執行，記錄 argv 與環境鍵名。（預定載具：test_research_int_p1.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-22-E-2` | TCS-ResearchToPRD-P1 AC-961-22（AC-R2P-12-1） | 拋棄式 clone 的兩種來源都可：git clone --no-hardlinks 與 git archive 匯出再 git init，分流最小路徑皆通過。（預定載具：test_research_int_p1.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-23-1` | TCS-ResearchToPRD-P1 AC-961-23（AC-R2P-02-7） | 允許變更檔案集合與禁區：只動各包 §5.7 的集合，禁區零差異。（預定載具：指令核對） | docs／gate | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-23-2` | TCS-ResearchToPRD-P1 AC-961-23（AC-R2P-02-7） | 不新增 os.replace、rename、move 站點：研究套件的目錄項原語站點數不增，根層 dirent 鎖綠。（預定載具：指令核對） | docs／gate | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-23-3` | TCS-ResearchToPRD-P1 AC-961-23（AC-R2P-02-7） | 不新增 hook、守衛碼與根層 tools 模組。（預定載具：指令核對） | docs／gate | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-23-4` | TCS-ResearchToPRD-P1 AC-961-23（AC-R2P-02-7） | 新 Python 衛生：encoding 宣告、時間戳帶時區、平台專屬 API 罩 sys.platform、ruff 兩視角 0 錯、LF。（預定載具：指令核對） | docs／gate | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-23-5` | TCS-ResearchToPRD-P1 AC-961-23（AC-R2P-02-7） | Bridge 全套與跨平台守衛：含新模組後全套綠且 0 skipped（DSN 與 SDD_ROOT 在場）。（預定載具：test_cross_platform_guard.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-23-E-1` | TCS-ResearchToPRD-P1 AC-961-23（AC-R2P-02-7） | hermetic：AT 全程不連外部網路，假 gh 與假連線層取代真端點。（預定載具：test_research_int_p1.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-24-1` | TCS-ResearchToPRD-P1 AC-961-24（AC-R2P-21-6） | 文件閘與追溯：新文件無測試摘要字樣加四位數字同行、RTM 每列回填、編號不撞號、Architecture 5.4 檢查表逐項有交付。（預定載具：指令核對） | docs／gate | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-25-1` | TCS-ResearchToPRD-P1 AC-961-25（AC-R2P-14-7） | 讀端衍生（D-125 之一）：flowPhase 為 TCS_PENDING 且內環 FSM 視圖有 Stage-2 凍結時 effective 回 build／BUILD_READY／IDLE，其餘不變。（預定載具：ResearchFlowPolicyTest） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-25-2` | TCS-ResearchToPRD-P1 AC-961-25（AC-R2P-14-7、AC-R2P-23-1） | Bridge :reconcile 校正（D-125 之二）：TCS_PENDING 且內環已凍結 Stage-2 時，同交易把游標寫為 build／ROUTED／IDLE 並記 research.step 事件。（預定載具：test_research_reconcile.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-25-3` | TCS-ResearchToPRD-P1 AC-961-25（AC-R2P-14-7） | 凍結後觸發（D-125 之三）：既有 SDD freeze 服務成功後，若專案綁研究專案則呼叫 Bridge :reconcile 恰一次，其他情況不呼叫。（預定載具：ResearchApiIT） | backend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-25-4` | TCS-ResearchToPRD-P1 AC-961-25（AC-R2P-14-7） | 步驟 4 面板的「重新對帳」：OPERATOR 以上可按、送出一次 reconcile，成功後面板依回應刷新（BUILD_READY）。（預定載具：components/domain/research/BuildFrontPanel.test.tsx） | frontend | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-961-25-E-1` | TCS-ResearchToPRD-P1 AC-961-25（AC-R2P-14-7、AC-R2P-23-1） | 負控：Stage-2 未凍結時不校正、不發事件、不衍生為 BUILD_READY。（預定載具：test_research_reconcile.py） | engine-bridge | P1 | ⬜ | ⬜ | ⬜ | ⬜ |
