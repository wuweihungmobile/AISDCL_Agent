# 2.10 研究議題轉規格書 P2 內環可視與交付（ResearchToPRD；`/research?step=build|deliver`）的 TCS 本地 ID 追溯（ResearchToPRD_PRD.md；不計入 §2 總列數）

**檔頭說明（2026-11-07 立骨架）**：本檔依 DEF-200-576 每功能一檔體例自始立為獨立檔；[RTM.md](RTM.md) 的 §2.10 存根於 P2 補一行引言。**本檔只增列不改號；回填規則照 RTM.md §1**；四格（實作檔、自動測試、E2E 驗證、狀態）一律由 `⬜` 起，完成一項回填一列，不得刪列、改號、合併列（`AgentConsole/CLAUDE.md` 鐵律 12）。

> 本子表的 ID 是 `AgentConsole/docs/03_testing/contracts/TCS-ResearchToPRD-P2-20261107.md`（下稱 TCS）的本地編號（F／US／AC／AT），ID 欄一律加反引號、不計入總列數。對應 PRD `docs/01_requirements/ResearchToPRD_PRD.md`（P2：FR-R2P-15、16、17、18 類型 (b)～(d)、20，及 FR-R2P-01、02、19、21、23 的 P2 增量）；本子表 343 列＝F 1、US 3、AC 30、AT 309（負控與邊界 107、正控 202；Bridge、backend、frontend、E2E 與指令核對）。FSM 功能鍵 `agentconsole-research-to-prd-p2`；開工基準 commit、規格摘要與 RELEASE 落款於 Stage-1 與 RELEASE 時由主控補。

| ID | 來源 | 摘要 | 層 | Phase | 實作檔 | 自動測試 | E2E 驗證 | 狀態 |
|----|------|------|----|-------|--------|----------|----------|------|
| `F-908` | ResearchToPRD_PRD.md·TCS-ResearchToPRD-P2 | ResearchToPRD P2：內環看板、自癒監視器、終端窗格、決策彈窗、SCR 前端、SCG 登錄、追溯表與 Release Tag 與 PR、ResearchBackLink；Flyway V21；步驟 4 其餘與步驟 5 | frontend／backend／engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `US-926` | ResearchToPRD_PRD.md·TCS-ResearchToPRD-P2 | US-R2P-15、16、17：作為 OPERATOR，我要在步驟 4 一頁看到從拆解到回歸驗收五階段各卡在哪、自癒嘗試與規格漂移、背景命令的即時輸出，並能一鍵進入既有執行中心；Bridge 不可達時我要看到有時間標示的快照而不是空畫面（AC-962-6、AC-962-7、AC-962-8、AC-962-9、AC-962-10、AC-962-11、AC-962-12、AC-962-13） | — | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `US-927` | ResearchToPRD_PRD.md·TCS-ResearchToPRD-P2 | US-R2P-18（類型 b、c、d）、15-6、19 的 UI 半、01-5：作為掌舵者，我要在系統需要我決定時被明確告知、能登錄 SCG-4 與 SCG-5 的審查結果（含審查者獨立聲明）、能從看板發起 SCR 並看到橫幅與停用，且能從執行中心回到研發工作流（AC-962-3、AC-962-4、AC-962-14、AC-962-15、AC-962-16） | — | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `US-928` | ResearchToPRD_PRD.md·TCS-ResearchToPRD-P2 | US-R2P-20、21、22、23 的 P2 增量：作為掌舵者，我要在交付前看見每條驗收準則是否都有通過的測試，並一鍵建立 Release Tag 與（可選）PR；作為維運，我要資料表、閘、對帳、稽核與契約鎖在 P2 一併到位且守衛不鬆動（AC-962-1、AC-962-2、AC-962-5、AC-962-17、AC-962-18、AC-962-19、AC-962-20、AC-962-21、AC-962-22、AC-962-23、AC-962-24、AC-962-25、AC-962-26、AC-962-27、AC-962-28、AC-962-29、AC-962-30） | — | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-1` | TCS-ResearchToPRD-P2 | 資料庫 V21：gate 加 SCG6、決定列 details、交付列 snapshot_sha256、SCR 列 evidence_url | backend／engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-2` | TCS-ResearchToPRD-P2 | gitops 白名單 P2 形態：tag、push origin tag、ls-remote、remote get-url、pr create、pr list | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-3` | TCS-ResearchToPRD-P2 | Bridge :gates：內環 SCG-4／SCG-5／RELEASE_READY FAIL 登錄的 FSM 序列與決定入庫 | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-4` | TCS-ResearchToPRD-P2 | console-api POST …/gates：角色、服務層前置、獨立性聲明與稽核 | backend／frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-5` | TCS-ResearchToPRD-P2 | 鎖：AST、能力登記、動詞表與 P2_OPS | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-6` | TCS-ResearchToPRD-P2 | 自癒同步 :healing-sync：視圖列對日誌行、冪等、尾 300 字元、2 MiB 上限 | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-7` | TCS-ResearchToPRD-P2 | 自癒遮蔽：Bridge 與 console-api 兩端共用夾具對拍 | engine-bridge／backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-8` | TCS-ResearchToPRD-P2 | SPEC_CHANGE_FORBIDDEN：凍結規格漂移的偵測、標記與告警（不還原） | engine-bridge／backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-9` | TCS-ResearchToPRD-P2 | console-api 自癒讀端與通知：GET healing、maxRetries、導出欄、RunConsumers post-commit 通知 | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-10` | TCS-ResearchToPRD-P2 | 看板聚合端點 GET …/kanban：五欄差分、待審、gates、Bridge 不可達快照、無第二套執行控制 | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-11` | TCS-ResearchToPRD-P2 | 看板前端：五欄、SSE 500ms、斷線回補、不可達態、深連結 | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-12` | TCS-ResearchToPRD-P2 | 自癒監視器前端：嘗試次數對上限、純文字、耗盡升級、規格漂移引導 SCR | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-13` | TCS-ResearchToPRD-P2 | 終端窗格：共用日誌元件與串流客戶端、純文字、REST 回補、開合不影響串流 | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-14` | TCS-ResearchToPRD-P2 | 人機協同決策彈窗 (b)～(d)：單一殼、去重、稍後處理、決定走既有端點 | frontend／backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-15` | TCS-ResearchToPRD-P2 | SCR 前端與 evidence_url：發起入口、表單、橫幅、停用規則、證據連結入庫 | frontend／backend／engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-16` | TCS-ResearchToPRD-P2 | ResearchBackLink：深連結 ?researchId=、兩頁掛點、反向釘改寫 | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-17` | TCS-ResearchToPRD-P2 | 追溯表：build_traceability、unitStatus 導出、totals、GET traceability 與表格呈現 | engine-bridge／backend／frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-18` | TCS-ResearchToPRD-P2 | Bridge :tag：冪等序列、快照檔、單交易入庫、FSM RELEASE 與失敗續跑 | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-19` | TCS-ResearchToPRD-P2 | console-api Tag 端點：服務層前置、semver 與長度邊界、錯誤透傳與稽核 | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-20` | TCS-ResearchToPRD-P2 | PR：標題與內文確定性模板、預覽確認、冪等、前置缺項、token 零外洩、失敗不補償 | engine-bridge／backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-21` | TCS-ResearchToPRD-P2 | 步驟 5 前端：DeliverPanel、追溯表、發布動作列、Tag 與 PR 確認框、開啟本地專案 | frontend／backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-22` | TCS-ResearchToPRD-P2 | 交付稽核與完整率：records/audit、audit_log 與事件 trace_id、append-only | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-23` | TCS-ResearchToPRD-P2 | 對帳第七項 delivery：快照 sha256 對 snapshot_sha256、交付時點自動對帳 | engine-bridge／backend／frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-24` | TCS-ResearchToPRD-P2 | 契約鎖：reason 37、OpenAPI 114／131、RBAC、端點函式 125 | backend／frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-25` | TCS-ResearchToPRD-P2 | 說明登記表、五步接線與兩處漂移橫幅整併、導覽不動 | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-26` | TCS-ResearchToPRD-P2 | 寫入擁有權與 db op：Bridge 唯一寫入者、delivery.record、outbox、檢查序 | engine-bridge／backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-27` | TCS-ResearchToPRD-P2 | FE-W3 型別層：schema.d.ts 重產、生成型替換手寫型、夾具補必填欄 | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-28` | TCS-ResearchToPRD-P2 | 整合 P2：內環走完到交付、真失敗步驟、Docker mock-only 負控與清理 | engine-bridge／frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-29` | TCS-ResearchToPRD-P2 | 邊界、跨平台與衛生閘：允許集合、禁區、無新守衛、無新目錄項原語 | gate／engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AC-962-30` | TCS-ResearchToPRD-P2 | 文件連動與 V 系列：K.6、十四處勘誤、RTM 回填、出口逐項 | docs／gate | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-1-1` | TCS-ResearchToPRD-P2 AC-962-1（AC-R2P-02-7、AC-R2P-02-8） | Flyway 歷史 1～21 全成功；V21 檔名與描述固定；V1～V20 的 checksum 不變；ddl-auto validate 不報錯。（預定載具：ResearchSchemaMigrationIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-1-2` | TCS-ResearchToPRD-P2 AC-962-1（AC-R2P-02-7） | research_gate_decisions.gate 的 CHECK 加 SCG6：列舉恰八值，SCG7 與小寫被拒，VARCHAR(11) 容得下全部值。（預定載具：ResearchSchemaMigrationIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-1-3` | TCS-ResearchToPRD-P2 AC-962-1（AC-R2P-02-7） | research_gate_decisions.details：JSONB NOT NULL 預設空物件，CHECK 限物件型別；三個約定鍵可寫入。（預定載具：ResearchSchemaMigrationIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-1-4` | TCS-ResearchToPRD-P2 AC-962-1（AC-R2P-02-7） | research_deliveries.snapshot_sha256：CHAR(64) 可空，64 位小寫十六進位才合法。（預定載具：ResearchSchemaMigrationIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-1-5` | TCS-ResearchToPRD-P2 AC-962-1（AC-R2P-02-7、AC-R2P-19-1） | research_scr.evidence_url：可空，限 https 開頭且長度不超過 500；不在受控更新清單內。（預定載具：ResearchSchemaMigrationIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-1-6` | TCS-ResearchToPRD-P2 AC-962-1（AC-R2P-02-7） | P0／P1 的守衛不退步：十八張 research_ 表逐表 DELETE 仍被擋、受控表清單與 append-only 清單不變。（預定載具：ResearchSchemaMigrationIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-1-7` | TCS-ResearchToPRD-P2 AC-962-1（AC-R2P-02-7） | 六處 Flyway 版本清單加 21，且既有表零變動快照不受 V21 影響。（預定載具：BackupJobMigrationIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-1-8` | TCS-ResearchToPRD-P2 AC-962-1（AC-R2P-02-7） | Bridge 的拋棄式資料庫夾具套到 V21，且 Bridge 兩個 INSERT 帶新欄位。（預定載具：test_research_deliver_router.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-1-E-1` | TCS-ResearchToPRD-P2 AC-962-1（AC-R2P-02-7） | 升級不改既有資料：在已有 V20 資料（含各 gate 值的決定列、SCR 列、交付列）的庫上套 V21，既有列逐欄不變。（預定載具：ResearchSchemaMigrationIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-1-E-2` | TCS-ResearchToPRD-P2 AC-962-1（AC-R2P-02-8） | V21 的時間欄與欄位型別：新增欄型別固定，既有時間欄仍皆為帶時區型別。（預定載具：ResearchSchemaMigrationIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-1-E-3` | TCS-ResearchToPRD-P2 AC-962-1（AC-R2P-02-7） | V21 約束名可預期且可被 pg_constraint 逐條查到（不是匿名約束）。（預定載具：ResearchSchemaMigrationIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-2-1` | TCS-ResearchToPRD-P2 AC-962-2（AC-R2P-20-3） | gitops 白名單新增 git 形態：tag --list、tag -a、push origin <tag>、ls-remote --tags origin、remote get-url origin、rev-parse --verify refs/tags。（預定載具：test_research_gitops.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-2-2` | TCS-ResearchToPRD-P2 AC-962-2（AC-R2P-20-4） | gitops 白名單新增 gh 形態：pr create 與 pr list；其餘 gh 子命令仍拒。（預定載具：test_research_gitops.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-2-3` | TCS-ResearchToPRD-P2 AC-962-2（AC-R2P-20-3） | tag 訊息模板正規式：`release: <semver>（RP-NNNN，追溯快照 sha256 <12 碼小寫十六進位>）`；既有 commit 模板不退步。（預定載具：test_research_gitops.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-2-4` | TCS-ResearchToPRD-P2 AC-962-2（AC-R2P-20-3） | valid_semver 常數邊界：官方 semver 2.0 的保守子集，長度上限 64。（預定載具：test_research_gitops.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-2-5` | TCS-ResearchToPRD-P2 AC-962-2（AC-R2P-20-3） | push origin <tag> 與既有 push -u origin <ref> 分開比對，不放寬 -u 形態。（預定載具：test_research_gitops.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-2-6` | TCS-ResearchToPRD-P2 AC-962-2（AC-R2P-20-3、AC-R2P-20-4） | gh 與 git 呼叫的環境與 token 隔離沿 P1 不變：GH_TOKEN 只進 gh，不進 argv 與 git。（預定載具：test_research_gitops.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-2-E-1` | TCS-ResearchToPRD-P2 AC-962-2（AC-R2P-20-3、AC-R2P-20-4） | 仍禁形態負控：--force、push --tags、tag -d、tag -f、gh release create、gh pr merge、任何刪除形態，在 spawn 之前拒絕。（預定載具：test_research_gitops.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-2-E-2` | TCS-ResearchToPRD-P2 AC-962-2（AC-R2P-20-3） | 選項注入負控：tag 名與 branch 名以 `-` 起頭、含空白、含控制字元一律在 spawn 前被拒。（預定載具：test_research_gitops.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-2-E-3` | TCS-ResearchToPRD-P2 AC-962-2（AC-R2P-20-3） | EXEC_MODULES 不變：git 與 gh 的 argv 字面只住 gitops.py；新模組不含 git／gh 字面。（預定載具：test_research_gitops.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-3-1` | TCS-ResearchToPRD-P2 AC-962-3（AC-R2P-15-6） | SCG-4 登錄：現態 IMPLEMENTATION 先 transition 再 gate PASS，序列與 decision_trace 和人工等價序列相同。（預定載具：test_research_inner_gates.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-3-2` | TCS-ResearchToPRD-P2 AC-962-3（AC-R2P-15-6） | PR_REVIEW 現態矩陣：EXECUTION_EVALUATION、ADVERSARIAL_EVALUATION 先 transition；現態已是 PR_REVIEW 略過 transition。（預定載具：test_research_inner_gates.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-3-3` | TCS-ResearchToPRD-P2 AC-962-3（AC-R2P-15-6） | PR_REVIEW FAIL 回 IMPLEMENTATION 並耗預算；連續 FAIL 到限額時 next_state 以引擎回傳為準（含 ESCALATION），Bridge 不自算。（預定載具：test_research_inner_gates.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-3-4` | TCS-ResearchToPRD-P2 AC-962-3（AC-R2P-15-6） | SCG-5 登錄：RTM_VERIFY PASS 到 RELEASE_READY、FAIL 回 IMPLEMENTATION（預算 2）；現態必須是 RTM_VERIFY。（預定載具：test_research_inner_gates.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-3-5` | TCS-ResearchToPRD-P2 AC-962-3（AC-R2P-15-6） | RELEASE_READY FAIL（雲端 CI 紅）：理由必填，回 IMPLEMENTATION，登錄為 gate 值 SCG6 並記 details.ci_red。（預定載具：test_research_inner_gates.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-3-6` | TCS-ResearchToPRD-P2 AC-962-3（AC-R2P-15-6、AC-R2P-02-5） | 決定入庫映射：PR_REVIEW→SCG4、RTM_VERIFY→SCG5、RELEASE_READY→SCG6；PASS→APPROVED、FAIL→REJECTED；details 承載獨立性聲明與報告參照。（預定載具：test_research_inner_gates.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-3-7` | TCS-ResearchToPRD-P2 AC-962-3（AC-R2P-15-6） | 零信任 RTM 重驗：PR_REVIEW 要求報告 fully_covered、RTM_VERIFY 要求 ac.pct 為 100，不信 console-api 傳入的判斷。（預定載具：test_research_inner_gates.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-3-8` | TCS-ResearchToPRD-P2 AC-962-3（AC-R2P-15-6） | 冪等：同一 decision_id 重送不重複 FSM 寫入與 DB 列。（預定載具：test_research_inner_gates.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-3-9` | TCS-ResearchToPRD-P2 AC-962-3（AC-R2P-15-6） | 與 SCR 共存：SCR MINOR 序列內部的 gate PR_REVIEW FAIL 不寫 SCG4 列；OPEN SCR 期間 `:gates` 回 scr_open。（預定載具：test_research_inner_gates.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-3-E-1` | TCS-ResearchToPRD-P2 AC-962-3（AC-R2P-15-6） | 現態不合負控：矩陣外的每個 FSM 狀態一律 409 且零 FSM 寫入、零 DB 列。（預定載具：test_research_inner_gates.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-3-E-2` | TCS-ResearchToPRD-P2 AC-962-3（AC-R2P-15-6） | 無 SUCCEEDED 分流時一律 409，details.cause 為 route_not_succeeded。（預定載具：test_research_inner_gates.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-3-E-3` | TCS-ResearchToPRD-P2 AC-962-3（AC-R2P-15-6） | 組合與欄位邊界：(RELEASE_READY, PASS) 一律 422；FAIL 理由必填；reason 500／501；review_report_ref 300／301。（預定載具：test_research_inner_gates.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-3-E-4` | TCS-ResearchToPRD-P2 AC-962-3（AC-R2P-15-6） | approver 不合（空、含控制字元、超長）時 422，且不呼叫任何 FSM 動詞。（預定載具：test_research_inner_gates.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-3-E-5` | TCS-ResearchToPRD-P2 AC-962-3（AC-R2P-15-6） | FSM 在前、DB 在後：DB 阻塞時 `:gates` 回 503 db_blocked，決定列留在 outbox，恢復後重放補寫且游標重衍生。（預定載具：test_research_inner_gates.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-3-E-6` | TCS-ResearchToPRD-P2 AC-962-3（AC-R2P-15-6、AC-R2P-16-5） | `:gates` 前置漂移負控：三種 gate 遇凍結 digest 不符一律 422 digest_mismatch，零寫入、零 FSM 呼叫。（預定載具：test_research_inner_gates.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-4-1` | TCS-ResearchToPRD-P2 AC-962-4（AC-R2P-15-6） | ADMIN 登錄 SCG-4：console-api 產 decisionId、帶最新 runId、approver 取 JWT subject，回應形狀固定。（預定載具：ResearchGateApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-4-2` | TCS-ResearchToPRD-P2 AC-962-4（AC-R2P-15-6） | PR_REVIEW 服務層前置：任務未完成或 RTM 未全覆蓋或無 RTM 時 409，details.unmet 逐項列出，Bridge 請求數為 0。（預定載具：ResearchGateApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-4-3` | TCS-ResearchToPRD-P2 AC-962-4（AC-R2P-15-6） | RTM_VERIFY 前置：acPct 為 100 才轉送；99.99 拒。（預定載具：ResearchGateApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-4-4` | TCS-ResearchToPRD-P2 AC-962-4（AC-R2P-15-6） | 審查者獨立性：PR_REVIEW 必須 reviewerIndependent 為 true；其餘 gate 不要求；Console 不判斷獨立性。（預定載具：ResearchGateApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-4-5` | TCS-ResearchToPRD-P2 AC-962-4（AC-R2P-15-6） | 欄位邊界：FAIL 必填 reason（1～500）、reviewReportRef 不超過 300、組合限制。（預定載具：ResearchGateApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-4-6` | TCS-ResearchToPRD-P2 AC-962-4（AC-R2P-15-6） | OPEN SCR 期間 409 scr_open；escalated 由 nextState 前綴 ESCALATION 判定並如實回傳。（預定載具：ResearchGateApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-4-7` | TCS-ResearchToPRD-P2 AC-962-4（AC-R2P-15-6） | GateRegisterDialog 正控：三個 gate 選項、PR_REVIEW 顯示審查者獨立聲明與報告參照、勾選後送出的請求本文、成功與升級呈現。（預定載具：components/domain/research/GateRegisterDialog.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-4-8` | TCS-ResearchToPRD-P2 AC-962-4（AC-R2P-15-6） | GateRegisterDialog：RELEASE_READY 只有 FAIL 選項、FAIL 必填理由計數器、SCR_OPEN 時停用。（預定載具：components/domain/research/GateRegisterDialog.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-4-E-1` | TCS-ResearchToPRD-P2 AC-962-4（AC-R2P-15-6） | OPERATOR 呼叫 gates 回 403，Bridge 請求數為 0，無任何研究表變化。（預定載具：RbacIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-4-E-2` | TCS-ResearchToPRD-P2 AC-962-4（AC-R2P-15-6） | VIEWER 呼叫 gates 回 403，且與 OPERATOR 同為授權鏈拒絕。（預定載具：RbacIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-4-E-3` | TCS-ResearchToPRD-P2 AC-962-4（AC-R2P-15-6） | 專案狀態負控：研究專案不存在回 404；尚未綁 console 專案回 409。（預定載具：ResearchGateApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-4-E-4` | TCS-ResearchToPRD-P2 AC-962-4（AC-R2P-15-6） | Bridge 不可達或逾時：502 或 504，且 console-api 不留部分狀態。（預定載具：ResearchGateApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-4-E-5` | TCS-ResearchToPRD-P2 AC-962-4（AC-R2P-15-6、AC-R2P-16-5） | console-api 透傳 gates 的 422 digest_mismatch：reason、狀態碼與 details.drift 原樣，不重寫。（預定載具：ResearchGateApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-4-E-6` | TCS-ResearchToPRD-P2 AC-962-4（AC-R2P-15-6） | 未勾審查者獨立聲明不可送：PR_REVIEW 送出鈕停用、請求數為 0；其餘 gate 不要求。（預定載具：components/domain/research/GateRegisterDialog.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-4-E-7` | TCS-ResearchToPRD-P2 AC-962-4（AC-R2P-15-6） | FAIL 無理由不可送；理由 500／501 與報告參照 300／301 邊界。（預定載具：components/domain/research/GateRegisterDialog.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-4-E-8` | TCS-ResearchToPRD-P2 AC-962-4（AC-R2P-15-6） | 非 ADMIN（OPERATOR、VIEWER）：登錄鈕停用且 title 為權限不足，請求數為 0。（預定載具：components/domain/research/GateRegisterDialog.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-4-E-9` | TCS-ResearchToPRD-P2 AC-962-4（AC-R2P-15-6） | 錯誤文案：409 fsm_state_conflict（unmet 逐項中文）、409 scr_open、422 digest_mismatch（列出漂移路徑並引導發起 SCR）、502 取 RESEARCH_REASON_TEXT；403 `ACCESS_DENIED` 取通用權限不足文案（非研究 reason）。（預定載具：components/domain/research/GateRegisterDialog.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-5-1` | TCS-ResearchToPRD-P2 AC-962-5（AC-R2P-15-6） | inner_gates.py 的三個 gate 呼叫皆為字面常數，各在一個 if 分支；gate_needs_guard 對它們為假。（預定載具：test_research_ast_locks.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-5-2` | TCS-ResearchToPRD-P2 AC-962-5（AC-R2P-15-6） | inner_gates 專屬規則：只呼叫 fsm_ops.gate 與 fsm_ops.transition，不呼叫 spec_frozen、approve_baseline、spec_refreeze、create_key。（預定載具：test_research_ast_locks.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-5-3` | TCS-ResearchToPRD-P2 AC-962-5（AC-R2P-20-3） | delivery.py 與 healing.py 列入 _NO_FSM_WRITE_MODULES：兩檔零 FSM 寫入；RELEASE 的 transition 住 inner_gates。（預定載具：test_research_ast_locks.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-5-4` | TCS-ResearchToPRD-P2 AC-962-5（AC-R2P-20-3） | EXEC_MODULES 不變且新模組不自起子行程：spawners 為 EXEC_MODULES 的子集。（預定載具：test_research_ast_locks.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-5-5` | TCS-ResearchToPRD-P2 AC-962-5（AC-R2P-20-3） | 能力登記：四個新模組先登記再掃描，實樹與登記表一對一。（預定載具：test_research_capability.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-5-6` | TCS-ResearchToPRD-P2 AC-962-5（AC-R2P-15-6） | 動詞表不變：RESEARCH_VERBS 五個、resume-from-escalation 不入；transition 目標含 PR_REVIEW 與 RELEASE。（預定載具：test_sdd_cli.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-5-7` | TCS-ResearchToPRD-P2 AC-962-5（AC-R2P-20-3） | P2_OPS 登記 delivery.record；OPS、METHOD_KINDS、WRITE_METHODS 不動，一一對應鎖仍綠。（預定載具：test_research_db.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-5-E-1` | TCS-ResearchToPRD-P2 AC-962-5（AC-R2P-15-6） | 紅綠自證負控：變數 gate、delivery 內 spec_frozen、healing 內 subprocess 的夾具原始碼各被判違規。（預定載具：test_research_ast_locks.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-5-E-2` | TCS-ResearchToPRD-P2 AC-962-5（AC-R2P-15-6） | 游標更新函式同時 append_event：delivery.record 與 gate.decision 內的游標 UPDATE 同函式含 append_event。（預定載具：test_research_ast_locks.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-6-1` | TCS-ResearchToPRD-P2 AC-962-6（AC-R2P-16-1） | 視圖列與日誌行逐筆一致：key 為 (run_id, step_number)，欄位集合固定，view_rows 的 key 集合等於 log 的 key 集合。（預定載具：test_research_healing.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-6-2` | TCS-ResearchToPRD-P2 AC-962-6（AC-R2P-16-1） | 冪等：重送不重複，只追加缺的行。（預定載具：test_research_healing.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-6-3` | TCS-ResearchToPRD-P2 AC-962-6（AC-R2P-16-1） | attempt 導出：同 (run_id, task_id) 內依 step_number 升冪的第 n 筆。（預定載具：test_research_healing.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-6-4` | TCS-ResearchToPRD-P2 AC-962-6（AC-R2P-16-1、AC-R2P-16-4） | excerpt 取遮蔽後的尾端 300 字元；以字元計不以位元組計；邊界 299、300、301。（預定載具：test_research_healing.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-6-5` | TCS-ResearchToPRD-P2 AC-962-6（AC-R2P-16-1） | 日誌上限 HEALING_LOG_MAX_BYTES＝2097152：到達上限前正常追加，超過後不再追加、寫一次 truncated 行並發 HEALING_LOG_TRUNCATED。（預定載具：test_research_healing.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-6-6` | TCS-ResearchToPRD-P2 AC-962-6（AC-R2P-16-1） | 寫檔經 fsutil.write_text_atomic，LF、UTF-8、ensure_ascii 為假，且不新增目錄項原語站點。（預定載具：test_research_healing.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-6-7` | TCS-ResearchToPRD-P2 AC-962-6（AC-R2P-16-1） | ResearchDb 唯一新增的方法是唯讀的 list_healing_attempts；沒有新寫入面。（預定載具：test_research_healing.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-6-8` | TCS-ResearchToPRD-P2 AC-962-6（AC-R2P-16-1） | `:healing-sync` 為內部端點：檢查序、回應形狀與角色。（預定載具：test_research_deliver_router.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-6-E-1` | TCS-ResearchToPRD-P2 AC-962-6（AC-R2P-16-1） | 無視圖列或專案未綁 console 專案：200 無操作，不建空檔。（預定載具：test_research_healing.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-6-E-2` | TCS-ResearchToPRD-P2 AC-962-6（AC-R2P-16-1） | 並行 sync 持專案鎖序列化，不產生重複行。（預定載具：test_research_healing.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-6-E-3` | TCS-ResearchToPRD-P2 AC-962-6（AC-R2P-16-1） | 資料庫阻塞時 503 db_blocked，且不寫檔。（預定載具：test_research_healing.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-7-1` | TCS-ResearchToPRD-P2 AC-962-7（AC-R2P-16-4） | Bridge 遮蔽對拍夾具逐筆：疊用 redact_secrets 與 gitops.redact。（預定載具：test_research_healing.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-7-2` | TCS-ResearchToPRD-P2 AC-962-7（AC-R2P-16-4） | 研究面恆遮：不讀 REDACT_SECRETS_IN_LOGS，環境關掉開關仍遮。（預定載具：test_research_healing.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-7-3` | TCS-ResearchToPRD-P2 AC-962-7（AC-R2P-16-4） | Java 遮蔽器與 Python 同夾具逐筆相同（兩端對拍）。（預定載具：HealingExcerptMaskerTest） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-7-4` | TCS-ResearchToPRD-P2 AC-962-7（AC-R2P-16-4） | log 檔逐字掃描：假 token 零明文。（預定載具：test_research_healing.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-7-5` | TCS-ResearchToPRD-P2 AC-962-7（AC-R2P-16-4） | API 回應逐字掃描：GET healing 的 excerpt 已遮蔽。（預定載具：ResearchHealingApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-7-E-1` | TCS-ResearchToPRD-P2 AC-962-7（AC-R2P-16-4） | 先遮蔽再截尾：token 跨 300 字元邊界時不留半截 token。（預定載具：test_research_healing.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-7-E-2` | TCS-ResearchToPRD-P2 AC-962-7（AC-R2P-16-4） | 誤殺負控：非機密長字串與雜湊不被遮蔽。（預定載具：test_research_healing.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-7-E-3` | TCS-ResearchToPRD-P2 AC-962-7（AC-R2P-16-4） | 夾具鎖：兩端測試各自讀同一份 JSON，不各抄一份。（預定載具：HealingExcerptMaskerTest） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-8-1` | TCS-ResearchToPRD-P2 AC-962-8（AC-R2P-16-5） | 偵測：改動一個已凍結檔，healing.detect_spec_change 回出漂移，且 Bridge 不改該檔。（預定載具：test_research_healing.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-8-2` | TCS-ResearchToPRD-P2 AC-962-8（AC-R2P-16-5） | 未改動不誤報；凍結階段取聯集；digest 逐檔重算。（預定載具：test_research_healing.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-8-3` | TCS-ResearchToPRD-P2 AC-962-8（AC-R2P-16-5） | 告警：追加 log 一行 spec_change、發 research.alert kind SPEC_CHANGE_FORBIDDEN，同一漂移不重複告警。（預定載具：test_research_healing.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-8-4` | TCS-ResearchToPRD-P2 AC-962-8（AC-R2P-16-5） | 偵測點三處：`:healing-sync` 只記錄與告警；`:gates` 與 `:tag` 前置比對不符即 422 digest_mismatch（阻擋，D-142）。（預定載具：test_research_healing.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-8-5` | TCS-ResearchToPRD-P2 AC-962-8（AC-R2P-16-5） | API 於漂移列補 specChangeForbidden。（預定載具：ResearchHealingApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-8-E-1` | TCS-ResearchToPRD-P2 AC-962-8（AC-R2P-16-5） | 不還原負控：偵測後 Bridge 不呼叫任何破壞性 git 形態。（預定載具：test_research_healing.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-8-E-2` | TCS-ResearchToPRD-P2 AC-962-8（AC-R2P-16-5） | 凍結檔被刪除亦為漂移，且不拋例外。（預定載具：test_research_healing.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-8-E-3` | TCS-ResearchToPRD-P2 AC-962-8（AC-R2P-16-5） | 劃界負控：回應與事件不聲稱『已拒絕補丁』。「被拒」屬框架 hooks，由 V-S1 承擔。（預定載具：test_research_healing.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-9-1` | TCS-ResearchToPRD-P2 AC-962-9（AC-R2P-16-1、AC-R2P-16-2） | GET healing 逐值對 DB：列數、run、task、attempt、status、excerpt、occurredAt；VIEWER 可讀。（預定載具：ResearchHealingApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-9-2` | TCS-ResearchToPRD-P2 AC-962-9（AC-R2P-16-2） | maxRetries 取系統參數 agent.maxRetries：預設 3，改 5 後回 5。（預定載具：ResearchHealingApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-9-3` | TCS-ResearchToPRD-P2 AC-962-9（AC-R2P-16-2、AC-R2P-16-3） | resolved 與 escalated 導出：任務其後 COMPLETED 補 resolved；任務 ESCALATED 的最後一列補 escalated。（預定載具：ResearchHealingApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-9-4` | TCS-ResearchToPRD-P2 AC-962-9（AC-R2P-16-2） | attribution 與 patchResult 恆為 null，不假造（PRD R10 與資料現況不一致，D-140 #5）。（預定載具：ResearchHealingApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-9-5` | TCS-ResearchToPRD-P2 AC-962-9（AC-R2P-16-1） | 日誌落後筆數：logSyncedThrough 與差額推得。（預定載具：ResearchHealingApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-9-6` | TCS-ResearchToPRD-P2 AC-962-9（AC-R2P-16-1） | 通知時點與條件：RunConsumers.handle 在 tx 提交之後、hub.publish 之前，僅當事件使任務進入 RETRYING／FAILED／ESCALATED 時呼叫 notify。（預定載具：ResearchHealingNotifierTest） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-9-7` | TCS-ResearchToPRD-P2 AC-962-9（AC-R2P-16-2） | retryingSteps 計算：最新 run 內 RETRYING 且其後無同 task 非 RETRYING 列者。（預定載具：ResearchHealingApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-9-E-1` | TCS-ResearchToPRD-P2 AC-962-9（AC-R2P-16-1） | 通知 best-effort：Bridge 不可達或逾時只記 log，事件處理與 SSE 發佈不受影響。（預定載具：ResearchHealingNotifierTest） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-9-E-2` | TCS-ResearchToPRD-P2 AC-962-9（AC-R2P-16-1） | 非研究專案的 run：notify 為無操作，Bridge 請求數為 0。（預定載具：ResearchHealingNotifierTest） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-9-E-3` | TCS-ResearchToPRD-P2 AC-962-9（AC-R2P-16-2） | 不存在的研究專案 404；專案無 console 專案時回空列 200。（預定載具：ResearchHealingApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-10-1` | TCS-ResearchToPRD-P2 AC-962-10（AC-R2P-15-1） | 差分：Task 拆解欄與 GET decomposition 逐值相等（完成判定＝已簽核且非 stale）。（預定載具：ResearchKanbanApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-10-2` | TCS-ResearchToPRD-P2 AC-962-10（AC-R2P-15-1） | 差分：測試規格產生欄與 GET fsm 的 frozenStages、negotiated 逐值相等。（預定載具：ResearchKanbanApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-10-3` | TCS-ResearchToPRD-P2 AC-962-10（AC-R2P-15-1） | 差分：程式碼實作欄與專案任務計數、FSM 現態逐值相等；完成判定在邊界上精確。（預定載具：ResearchKanbanApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-10-4` | TCS-ResearchToPRD-P2 AC-962-10（AC-R2P-15-1） | 差分：自癒修復欄與 GET healing 的 retryingSteps、escalatedTasks、maxRetries 逐值相等。（預定載具：ResearchKanbanApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-10-5` | TCS-ResearchToPRD-P2 AC-962-10（AC-R2P-15-1） | 差分：回歸驗收欄與 executions/{runId}/rtm、FSM 現態逐值相等；完成判定邊界。（預定載具：ResearchKanbanApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-10-6` | TCS-ResearchToPRD-P2 AC-962-10（AC-R2P-18-3、AC-R2P-15-1） | pendingReviews：review_requests 的 PENDING 與該專案所有 run 相連；kind 區分 ESCALATED；已決定者不列。（預定載具：ResearchKanbanApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-10-7` | TCS-ResearchToPRD-P2 AC-962-10（AC-R2P-15-6） | gates 清單：SCG4、SCG5、SCG6 各取最近 5 筆；6 筆時只回 5。（預定載具：ResearchKanbanApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-10-8` | TCS-ResearchToPRD-P2 AC-962-10（AC-R2P-15-4） | Bridge 不可達：200、bridgeReachable 為 false、stale 為 true、FSM 衍生欄 null 加 unknown、DB 欄取即時值、snapshotAt 取三個來源時間的最大值。（預定載具：ResearchKanbanApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-10-9` | TCS-ResearchToPRD-P2 AC-962-10（AC-R2P-15-1） | latestRunId 取專案最新 execution_run；無 run 時為 null 且 rtmAvailable 為 false。（預定載具：ResearchKanbanApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-10-E-1` | TCS-ResearchToPRD-P2 AC-962-10（AC-R2P-15-2） | 路由清單比對：/api/v1/research/** 無執行控制動詞路徑；P2 新增路徑集合恰七條；負控夾具被判違規。（預定載具：ResearchKanbanRouteInventoryTest） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-10-E-2` | TCS-ResearchToPRD-P2 AC-962-10（AC-R2P-15-2） | 看板 GET 無副作用：前後研究表列數與 Bridge 寫入請求數不變，Bridge 只收讀請求。（預定載具：ResearchKanbanApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-10-E-3` | TCS-ResearchToPRD-P2 AC-962-10（AC-R2P-15-2） | 未簽核與 SCR 開啟時既有 execute 仍回 409（看板不重造守衛）。（預定載具：ResearchKanbanApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-10-E-4` | TCS-ResearchToPRD-P2 AC-962-10（AC-R2P-15-1） | 存取與不存在：VIEWER 200、未登入 401、不存在專案 404。（預定載具：ResearchKanbanApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-10-E-5` | TCS-ResearchToPRD-P2 AC-962-10（AC-R2P-15-1） | 完成判定不被假資料抬高：RTM 諮詢性質不被當成獨立通過證據。（預定載具：ResearchKanbanApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-11-1` | TCS-ResearchToPRD-P2 AC-962-11（AC-R2P-15-1） | kanbanColumns 純函式窮舉表：五欄完成判定的每個邊界。（預定載具：lib/domain/research.test.ts） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-11-2` | TCS-ResearchToPRD-P2 AC-962-11（AC-R2P-15-1） | 渲染五欄、順序固定、計數等於資料。（預定載具：components/domain/research/KanbanBoard.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-11-3` | TCS-ResearchToPRD-P2 AC-962-11（AC-R2P-15-3） | SSE 到客戶端至 DOM 更新不超過 500ms（假計時器、假 EventSource，不用牆鐘）。（預定載具：components/domain/research/KanbanBoard.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-11-4` | TCS-ResearchToPRD-P2 AC-962-11（AC-R2P-15-3） | 三條串流任一幀都觸發 kanban 失效重抓；同一去抖窗內多幀合併為一次。（預定載具：components/domain/research/KanbanBoard.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-11-5` | TCS-ResearchToPRD-P2 AC-962-11（AC-R2P-15-3） | 斷線回補：replay_gap 幀或重連後以 REST 全量重抓，並帶 Last-Event-ID。（預定載具：components/domain/research/KanbanBoard.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-11-6` | TCS-ResearchToPRD-P2 AC-962-11（AC-R2P-15-5、AC-R2P-01-5） | 每欄深連結：開啟執行中心與監控中心，帶 researchId；停用規則與文案取登記處。（預定載具：components/domain/research/KanbanBoard.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-11-7` | TCS-ResearchToPRD-P2 AC-962-11（AC-R2P-15-4） | Bridge 不可達態：橫幅加快照時間加未知徽章，不渲染空看板，不把快照當即時。（預定載具：components/domain/research/KanbanBoard.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-11-8` | TCS-ResearchToPRD-P2 AC-962-11（AC-R2P-15-2） | 靜態判準：KanbanBoard 只用 Link 或既有 endpoints 函式，不 import 新的執行控制端點函式，不直呼 fetch。（預定載具：components/domain/research/KanbanBoard.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-11-9` | TCS-ResearchToPRD-P2 AC-962-11（AC-R2P-15-3、AC-R2P-15-4） | Playwright mock：頁面內 performance.mark 再驗 500ms、斷線回補、Bridge 不可達態。（預定載具：tests/e2e/research-kanban.mock.spec.ts） | frontend（E2E） | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-11-E-1` | TCS-ResearchToPRD-P2 AC-962-11（AC-R2P-15-1） | VIEWER：看板可讀，寫入類動作停用，title 為權限不足。（預定載具：components/domain/research/KanbanBoard.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-11-E-2` | TCS-ResearchToPRD-P2 AC-962-11（AC-R2P-15-4） | 缺值不猜：FSM 欄為 null 時顯示未知，不顯示 0 或完成。（預定載具：components/domain/research/KanbanBoard.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-11-E-3` | TCS-ResearchToPRD-P2 AC-962-11（AC-R2P-15-3） | 去抖邊界：99ms 內合併、101ms 後各自觸發。（預定載具：components/domain/research/KanbanBoard.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-11-E-4` | TCS-ResearchToPRD-P2 AC-962-11（AC-R2P-15-1） | a11y 與版面：看板在大、中、小三種寬度（寬度值沿 P1 的 a11y 規格）無水平溢出，axe 無 serious 與 critical。（預定載具：tests/e2e/a11y.mock.spec.ts） | frontend（E2E） | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-12-1` | TCS-ResearchToPRD-P2 AC-962-12（AC-R2P-16-2） | 每任務顯示嘗試次數對上限、最近失敗摘錄、歸因與補丁結果；數值等於資料。（預定載具：components/domain/research/HealingMonitor.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-12-2` | TCS-ResearchToPRD-P2 AC-962-12（AC-R2P-16-2） | 純文字：摘錄含 HTML 與 on* 屬性時 DOM 無元素節點。（預定載具：components/domain/research/HealingMonitor.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-12-3` | TCS-ResearchToPRD-P2 AC-962-12（AC-R2P-16-3） | 耗盡升級：escalated 列顯示已升級徽章並連到決策彈窗，不再提供自動重試。（預定載具：components/domain/research/HealingMonitor.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-12-4` | TCS-ResearchToPRD-P2 AC-962-12（AC-R2P-16-5、AC-R2P-19-1） | 規格漂移列：顯示引導並預填 SCR 發起。（預定載具：components/domain/research/HealingMonitor.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-12-5` | TCS-ResearchToPRD-P2 AC-962-12（AC-R2P-16-1） | 日誌落後提示。（預定載具：components/domain/research/HealingMonitor.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-12-E-1` | TCS-ResearchToPRD-P2 AC-962-12（AC-R2P-16-2） | 空狀態不顯示假進度。（預定載具：components/domain/research/HealingMonitor.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-12-E-2` | TCS-ResearchToPRD-P2 AC-962-12（AC-R2P-16-5） | VIEWER：發起 SCR 鈕停用。（預定載具：components/domain/research/HealingMonitor.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-12-E-3` | TCS-ResearchToPRD-P2 AC-962-12（AC-R2P-16-2） | 摘錄長度與版面：300 字元摘錄不撐破容器。（預定載具：components/domain/research/HealingMonitor.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-13-1` | TCS-ResearchToPRD-P2 AC-962-13（AC-R2P-17-1） | 展開時以 useRunStream 餵 LiveLogCard；收合時仍訂閱，開合不重連。（預定載具：components/domain/research/TerminalPane.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-13-2` | TCS-ResearchToPRD-P2 AC-962-13（AC-R2P-17-2） | 靜態判準：與執行中心共用同一日誌元件與串流客戶端，無第二份實作。（預定載具：components/domain/research/TerminalPane.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-13-3` | TCS-ResearchToPRD-P2 AC-962-13（AC-R2P-17-3） | 純文字哨兵：script、img、on* 屬性與哨兵呼叫皆為 0，ANSI 序列不殘留。（預定載具：components/domain/research/TerminalPane.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-13-4` | TCS-ResearchToPRD-P2 AC-962-13（AC-R2P-17-4） | run 結束後以 REST 回補：steps?afterSeq 分頁補齊，與結束前一致。（預定載具：components/domain/research/TerminalPane.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-13-5` | TCS-ResearchToPRD-P2 AC-962-13（AC-R2P-17-1） | 開合狀態僅存瀏覽器：鍵 research.terminal.open，預設收合，localStorage 例外時仍可用。（預定載具：components/domain/research/TerminalPane.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-13-6` | TCS-ResearchToPRD-P2 AC-962-13（AC-R2P-17-1） | log 幀到達至顯示不超過 500ms（假計時器）。（預定載具：components/domain/research/TerminalPane.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-13-7` | TCS-ResearchToPRD-P2 AC-962-13（AC-R2P-17-1） | 斷線以 Last-Event-ID 回補。（預定載具：components/domain/research/TerminalPane.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-13-E-1` | TCS-ResearchToPRD-P2 AC-962-13（AC-R2P-17-2） | 靜態掃描負控：夾具原始碼含 WebSocket、new EventSource、dangerouslySetInnerHTML 皆被判違規。（預定載具：components/domain/research/TerminalPane.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-13-E-2` | TCS-ResearchToPRD-P2 AC-962-13（AC-R2P-17-1） | runId 為 null：顯示尚無執行批次，不訂閱。（預定載具：components/domain/research/TerminalPane.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-13-E-3` | TCS-ResearchToPRD-P2 AC-962-13（AC-R2P-17-3） | 重用元件零改動：LiveLogCard.tsx、useRunStream.ts、LogPanel.tsx 零 diff。（預定載具：指令核對） | gate | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-14-1` | TCS-ResearchToPRD-P2 AC-962-14（AC-R2P-18-2） | 類型 (b) 自癒耗盡：ESCALATED 待審開彈窗，四個決定按鈕由 allowedDecisions 驅動。（預定載具：components/domain/research/DecisionModal.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-14-2` | TCS-ResearchToPRD-P2 AC-962-14（AC-R2P-18-2） | 類型 (c) Agent 請求審核：kind 非 ESCALATED 的待審與 review-request 幀同殼處理。（預定載具：components/domain/research/DecisionModal.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-14-3` | TCS-ResearchToPRD-P2 AC-962-14（AC-R2P-18-2） | 類型 (d) 重大架構選擇：alert ESCALATION 幀與 review-request 皆可觸發；去重鍵 reviewId，無則用 alert 幀 seq；Console 不判斷何謂重大。（預定載具：components/domain/research/DecisionModal.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-14-4` | TCS-ResearchToPRD-P2 AC-962-14（AC-R2P-18-2） | 決定送出走既有端點，不寫 research gates。（預定載具：components/domain/research/DecisionModal.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-14-5` | TCS-ResearchToPRD-P2 AC-962-14（AC-R2P-18-3） | 稍後處理：只關窗並以 sessionStorage 記 key，待辦仍在列表與頂列徽章，重新整理後仍在。（預定載具：components/domain/research/DecisionModal.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-14-6` | TCS-ResearchToPRD-P2 AC-962-14（AC-R2P-18-3） | 去重：SSE 重播的重複幀同 key 只出現一個彈窗；重新整理後由 pendingReviews 重建。（預定載具：components/domain/research/DecisionModal.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-14-7` | TCS-ResearchToPRD-P2 AC-962-14（AC-R2P-18-2） | 單一彈窗殼：research 目錄不得出現第二個彈窗殼，並重用 SddEscalationBlock。（預定載具：components/domain/research/DecisionModal.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-14-8` | TCS-ResearchToPRD-P2 AC-962-14（AC-R2P-18-2） | 決定入庫：review_requests 的 decided_by、decided_at、comment 與 audit_log 一列；不寫 research_gate_decisions。（預定載具：ResearchKanbanApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-14-E-1` | TCS-ResearchToPRD-P2 AC-962-14（AC-R2P-18-2） | VIEWER：可讀內容，決定鈕全停用，title 為權限不足。（預定載具：components/domain/research/DecisionModal.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-14-E-2` | TCS-ResearchToPRD-P2 AC-962-14（AC-R2P-18-2） | allowedDecisions 以外的按鈕不渲染。（預定載具：components/domain/research/DecisionModal.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-14-E-3` | TCS-ResearchToPRD-P2 AC-962-14（AC-R2P-18-2） | 他人已決定：決定端點回 409 或 404 時顯示錯誤並重抓 pendingReviews，不重複送出。（預定載具：components/domain/research/DecisionModal.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-14-E-4` | TCS-ResearchToPRD-P2 AC-962-14（AC-R2P-18-2） | 無逾時自動處理：時間前進 72 小時仍無自動決定請求。（預定載具：components/domain/research/DecisionModal.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-15-1` | TCS-ResearchToPRD-P2 AC-962-15（AC-R2P-19-1） | 發起入口：看板與步驟 4 頁頂的『發起規格變更（SCR）』，OPERATOR 以上可用。（預定載具：components/domain/research/ScrRequestDialog.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-15-2` | TCS-ResearchToPRD-P2 AC-962-15（AC-R2P-19-1、AC-R2P-19-5） | 表單欄位齊備與預填：kind、sourceKind、reason 計數器、reasonClass 中文五值、affectedSections 多選、證據連結。（預定載具：components/domain/research/ScrRequestDialog.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-15-3` | TCS-ResearchToPRD-P2 AC-962-15（AC-R2P-19-1、AC-R2P-19-4、AC-R2P-19-7） | 送出與結果：202 顯示已發起；MAJOR 導向後繼專案；HEALING_FAILED 只顯示可複製指令。（預定載具：components/domain/research/ScrRequestDialog.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-15-4` | TCS-ResearchToPRD-P2 AC-962-15（AC-R2P-19-5、AC-R2P-19-6） | 錯誤回顯：422 violations 逐筆回到欄位；scr_open、scr_limit、fsm_state_conflict 顯示登記文案。（預定載具：components/domain/research/ScrRequestDialog.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-15-5` | TCS-ResearchToPRD-P2 AC-962-15（AC-R2P-19-4、AC-R2P-19-1） | SCR_OPEN 時橫幅與停用規則：看板、InnerLoopLinks、GateRegisterDialog、ReleaseActions 的啟動類動作一律停用並顯示同一文案。（預定載具：components/domain/research/ScrBanner.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-15-6` | TCS-ResearchToPRD-P2 AC-962-15（AC-R2P-19-1、AC-R2P-19-5） | console-api 的 evidenceUrl：ScrOpenRequest 選填，轉送 Bridge 的 evidence_url，ScrDto 回傳。（預定載具：ResearchScrApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-15-7` | TCS-ResearchToPRD-P2 AC-962-15（AC-R2P-19-1、AC-R2P-19-5） | Bridge `:scr` 接受 evidence_url 並寫入 research_scr.evidence_url。（預定載具：test_research_scr.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-15-8` | TCS-ResearchToPRD-P2 AC-962-15（AC-R2P-19-1） | scr.open op 的 INSERT 帶 evidence_url，欄位順序與參數一一對應。（預定載具：test_research_scr.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-15-E-1` | TCS-ResearchToPRD-P2 AC-962-15（AC-R2P-19-5） | 常數邊界：reason 500／501、affectedSections 20／21、單項 200／201、證據連結 500／501。（預定載具：components/domain/research/ScrRequestDialog.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-15-E-2` | TCS-ResearchToPRD-P2 AC-962-15（AC-R2P-19-1） | 無權不送請求：VIEWER 的對話框不能開啟、送出請求數為 0。（預定載具：components/domain/research/ScrRequestDialog.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-15-E-3` | TCS-ResearchToPRD-P2 AC-962-15（AC-R2P-19-5） | reasonClass 兩種拼法：前端送中文，後端兩種拼法皆收。（預定載具：components/domain/research/ScrRequestDialog.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-15-E-4` | TCS-ResearchToPRD-P2 AC-962-15（AC-R2P-19-5） | 證據連結以外部連結安全規則顯示：只接受 https，顯示為純文字。（預定載具：components/domain/research/ScrRequestDialog.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-16-1` | TCS-ResearchToPRD-P2 AC-962-16（AC-R2P-01-5） | ResearchBackLink：UUID 顯示回到研發工作流，href 固定；null 不渲染。（預定載具：components/domain/research/ResearchBackLink.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-16-2` | TCS-ResearchToPRD-P2 AC-962-16（AC-R2P-01-5、AC-R2P-15-5） | ExecuteView 在 ?researchId=<uuid> 時頁頂顯示 BackLink。（預定載具：components/domain/execute/ExecuteView.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-16-3` | TCS-ResearchToPRD-P2 AC-962-16（AC-R2P-01-5、AC-R2P-15-5） | MonitorView 在 ?researchId=<uuid> 時頁頂顯示 BackLink。（預定載具：components/domain/monitor/MonitorView.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-16-4` | TCS-ResearchToPRD-P2 AC-962-16（AC-R2P-15-5） | 看板與 InnerLoopLinks 的連結帶 researchId 查詢參數。（預定載具：components/domain/research/InnerLoopLinks.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-16-5` | TCS-ResearchToPRD-P2 AC-962-16（AC-R2P-01-5） | P1 反向釘改寫：工作區只在已有 consoleProjectId 的步驟 4 面板出現連結字樣，其他步驟仍沒有。（預定載具：components/domain/research/ResearchWorkspaceView.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-16-E-1` | TCS-ResearchToPRD-P2 AC-962-16（AC-R2P-01-5） | 無參數（深連結直接開執行中心）不顯示返回連結，不猜。（預定載具：components/domain/execute/ExecuteView.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-16-E-2` | TCS-ResearchToPRD-P2 AC-962-16（AC-R2P-01-5） | 非 UUID 一律忽略：路徑穿越、腳本、長度不符、非十六進位。（預定載具：components/domain/research/ResearchBackLink.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-16-E-3` | TCS-ResearchToPRD-P2 AC-962-16（AC-R2P-01-5） | 零後端、零儲存：不呼叫 API、不讀寫 storage；頁面殼零差異。（預定載具：components/domain/research/ResearchBackLink.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-17-1` | TCS-ResearchToPRD-P2 AC-962-17（AC-R2P-20-1） | build_traceability：列數等於凍結 PRD 的 AC 總數，一個 AC 一列，集合相等、無遺漏無多餘。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-17-2` | TCS-ResearchToPRD-P2 AC-962-17（AC-R2P-20-1） | gherkinSummary 每段不超過 120 字；邊界 120／121。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-17-3` | TCS-ResearchToPRD-P2 AC-962-17（AC-R2P-20-1、AC-R2P-20-2） | unitStatus 導出：覆蓋任務全 COMPLETED 為 PASS；任一 FAILED 或 ESCALATED 為 FAIL；其餘 NOT_RUN；無覆蓋任務為 NONE。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-17-4` | TCS-ResearchToPRD-P2 AC-962-17（AC-R2P-20-1） | e2eStatus：僅當存在 SCG5 的 APPROVED 決定且其後無 REJECTED 時為 PASS，否則 NOT_RUN（無逐 AC 的 E2E 機器來源，如實標示）。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-17-5` | TCS-ResearchToPRD-P2 AC-962-17（AC-R2P-20-2） | totals：未覆蓋＝unitStatus 不為 PASS 的列數；e2e 欄不計入；零測試不是通過。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-17-6` | TCS-ResearchToPRD-P2 AC-962-17（AC-R2P-20-1） | `:traceability-preview` 零副作用：DB 與檔案前後相同。（預定載具：test_research_deliver_router.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-17-7` | TCS-ResearchToPRD-P2 AC-962-17（AC-R2P-20-1、AC-R2P-20-2） | GET delivery/traceability 逐值對 Bridge 回放；VIEWER 可讀；rtm 欄形狀固定。（預定載具：ResearchDeliveryApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-17-8` | TCS-ResearchToPRD-P2 AC-962-17（AC-R2P-20-1、AC-R2P-20-2） | 表格呈現：一 AC 一列、紅標、未覆蓋計數、摘要純文字。（預定載具：components/domain/research/TraceabilityTable.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-17-E-1` | TCS-ResearchToPRD-P2 AC-962-17（AC-R2P-20-1） | 凍結 PRD 讀不到：409 fsm_state_conflict，unmet 含 prd_not_frozen，零寫入。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-17-E-2` | TCS-ResearchToPRD-P2 AC-962-17（AC-R2P-20-2） | 拆解缺席或 stale：全部 AC 的 unitStatus 為 NONE，不假設通過。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-17-E-3` | TCS-ResearchToPRD-P2 AC-962-17（AC-R2P-20-1） | AC 數邊界：N 為 1 與 250 時列數仍等於 N。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-17-E-4` | TCS-ResearchToPRD-P2 AC-962-17（AC-R2P-20-3） | 零信任：`:tag` 內重算追溯表，不信任請求帶入的列。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-18-1` | TCS-ResearchToPRD-P2 AC-962-18（AC-R2P-20-3） | Tag 正控序列：驗證、冪等探測、取 commit、tag -a、（push:true 且有 origin）push、寫快照檔、單交易入庫、transition RELEASE、對帳。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-18-2` | TCS-ResearchToPRD-P2 AC-962-18（AC-R2P-20-3） | tag 訊息只取模板：release: <tag>（RP-NNNN，追溯快照 sha256 <前 12 碼>），使用者 message 不進 argv，只入 detail 並先遮蔽。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-18-3` | TCS-ResearchToPRD-P2 AC-962-18（AC-R2P-20-3、AC-R2P-02-5） | 快照檔與 R11：traceability_matrix.json 鍵序固定、LF、不跳脫中文；其 sha256 等於 snapshot_sha256 欄；rtm_report_ref 為檔案相對路徑。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-18-4` | TCS-ResearchToPRD-P2 AC-962-18（AC-R2P-20-3） | 單一 DB 交易：RELEASE_TAG 列與 research.delivery 事件同交易，欄位值固定。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-18-5` | TCS-ResearchToPRD-P2 AC-962-18（AC-R2P-20-3） | FSM 與游標：transition --to RELEASE 序列與游標落點。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-18-6` | TCS-ResearchToPRD-P2 AC-962-18（AC-R2P-20-3） | 冪等續跑：同 tag 已有 CREATED 列時跳過 tag、push、入庫，只補 transition。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-18-7` | TCS-ResearchToPRD-P2 AC-962-18（AC-R2P-20-3） | push 失敗：502 delivery_step_failed、failure_step 為 push，本地 tag 保留，可重送續跑，絕不強推。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-18-8` | TCS-ResearchToPRD-P2 AC-962-18（AC-R2P-20-3） | FSM 步驟失敗：502 failure_step 為 fsm_release，DB 列已存，重送只重做 transition。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-18-9` | TCS-ResearchToPRD-P2 AC-962-18（AC-R2P-20-3） | push 確認規則：push 為假或無 origin 不推送；遠端已有同 sha 視為成功；不同 sha 拒。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-18-E-1` | TCS-ResearchToPRD-P2 AC-962-18（AC-R2P-20-3） | tag 已存在且非本專案 CREATED 列：409 tag_exists，零 DB、零 FSM。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-18-E-2` | TCS-ResearchToPRD-P2 AC-962-18（AC-R2P-20-2、AC-R2P-20-3） | 前置不成立：現態非 RELEASE_READY、追溯未全覆蓋、SCR 開啟，各 409 且零 git 副作用。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-18-E-3` | TCS-ResearchToPRD-P2 AC-962-18（AC-R2P-20-3） | createGithubRelease 為 true：422 release_not_supported，零副作用。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-18-E-4` | TCS-ResearchToPRD-P2 AC-962-18（AC-R2P-20-3） | argv 注入：message 含 --exec、換行、$(...) 時 argv 仍恰為模板。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-18-E-5` | TCS-ResearchToPRD-P2 AC-962-18（AC-R2P-20-3、AC-R2P-16-5） | 規格漂移與 Tag：前置比對凍結 digest 不符即 422 digest_mismatch，零副作用（D-142 ⚖P2-9）。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-18-E-6` | TCS-ResearchToPRD-P2 AC-962-18（AC-R2P-20-3） | 容器模式前置：目標專案不可寫（repo_writable 缺）時 `:tag` 回 422 route_unsupported_in_deployment，零副作用。（預定載具：test_research_deliver_router.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-19-1` | TCS-ResearchToPRD-P2 AC-962-19（AC-R2P-20-3） | ADMIN 建立 tag：轉送 Bridge 一次，請求欄位固定。（預定載具：ResearchDeliveryApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-19-2` | TCS-ResearchToPRD-P2 AC-962-19（AC-R2P-20-2、AC-R2P-20-3） | 服務層前置先於 Bridge：FSM 現態、RTM 閘、無 OPEN SCR，不合 409 且 Bridge 請求 0。（預定載具：ResearchDeliveryApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-19-3` | TCS-ResearchToPRD-P2 AC-962-19（AC-R2P-20-3） | tagName 正規式與長度邊界：與 Bridge 同一份常數字面。（預定載具：ResearchDeliveryApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-19-4` | TCS-ResearchToPRD-P2 AC-962-19（AC-R2P-20-3） | message 長度：200 通過、201 為 422。（預定載具：ResearchDeliveryApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-19-5` | TCS-ResearchToPRD-P2 AC-962-19（AC-R2P-20-3） | Bridge 錯誤透傳：tag_exists、delivery_step_failed 保持 reason、HTTP 狀態與 details。（預定載具：ResearchDeliveryApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-19-6` | TCS-ResearchToPRD-P2 AC-962-19（AC-R2P-02-5） | 稽核：每個 tag 寫入請求入 audit_log，且與 Bridge 事件同 trace_id。（預定載具：ResearchDeliveryApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-19-E-1` | TCS-ResearchToPRD-P2 AC-962-19（AC-R2P-20-3） | OPERATOR 呼叫 tag 回 403，Bridge 請求 0，無研究表變化。（預定載具：RbacIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-19-E-2` | TCS-ResearchToPRD-P2 AC-962-19（AC-R2P-20-3） | VIEWER 呼叫 tag 回 403。（預定載具：RbacIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-19-E-3` | TCS-ResearchToPRD-P2 AC-962-19（AC-R2P-20-3） | createGithubRelease 為 true：422 release_not_supported，Bridge 請求 0；push 缺省為 false。（預定載具：ResearchDeliveryApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-19-E-4` | TCS-ResearchToPRD-P2 AC-962-19（AC-R2P-20-3） | Bridge 不可達：502，無部分狀態。（預定載具：ResearchDeliveryApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-19-E-5` | TCS-ResearchToPRD-P2 AC-962-19（AC-R2P-20-3、AC-R2P-16-5） | console-api 透傳 tag 的 422 digest_mismatch。（預定載具：ResearchDeliveryApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-19-E-6` | TCS-ResearchToPRD-P2 AC-962-19（AC-R2P-20-3） | console-api 直呼 `:tag` 於容器模式：透傳 422 route_unsupported_in_deployment（沿 P1 AT-961-22-5 體例），不自行猜測部署能力。（預定載具：ResearchDeliveryApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-20-1` | TCS-ResearchToPRD-P2 AC-962-20（AC-R2P-20-4） | PR 正控序列：push -u origin、gh pr create（argv 陣列、token 只進環境）、入庫、事件。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-20-2` | TCS-ResearchToPRD-P2 AC-962-20（AC-R2P-20-4） | 標題與內文模板：標題截斷 60 字、內文四段固定序、不超過 4000 字、不帶使用者自由文字。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-20-3` | TCS-ResearchToPRD-P2 AC-962-20（AC-R2P-20-4） | title 欄只作預覽：不等於模板輸出時 422 title_not_template；bodyPreviewAck 必須為 true。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-20-4` | TCS-ResearchToPRD-P2 AC-962-20（AC-R2P-20-4） | 已有 PR 冪等：回既有、created 為 false，不再 gh pr create。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-20-5` | TCS-ResearchToPRD-P2 AC-962-20（AC-R2P-20-4） | 前置缺項：gh、gh_auth、origin、repo_writable 缺任一，422 route_unsupported_in_deployment，零副作用。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-20-6` | TCS-ResearchToPRD-P2 AC-962-20（AC-R2P-20-4） | token 零外洩：只進 gh 子行程環境，不入 argv、log、DB、回應。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-20-7` | TCS-ResearchToPRD-P2 AC-962-20（AC-R2P-20-4） | 失敗不補償：502 delivery_step_failed、failure_step 為 push 或 pr_create，不寫 FAILED 列，只發 FAILED 事件。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-20-8` | TCS-ResearchToPRD-P2 AC-962-20（AC-R2P-20-4） | console-api：ADMIN 建 PR，只在此端點讀 research.github_token 放進本文 github_token。（預定載具：ResearchDeliveryApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-20-E-1` | TCS-ResearchToPRD-P2 AC-962-20（AC-R2P-20-4） | OPERATOR 與 VIEWER 呼叫 pr 回 403，Bridge 請求 0。（預定載具：RbacIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-20-E-2` | TCS-ResearchToPRD-P2 AC-962-20（AC-R2P-20-4） | bodyPreviewAck 為 false 或缺：422，Bridge 請求 0。（預定載具：ResearchDeliveryApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-20-E-3` | TCS-ResearchToPRD-P2 AC-962-20（AC-R2P-20-4） | branch 驗證：預設取 route_decisions.git_branch；不合 ref 規則 422。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-20-E-4` | TCS-ResearchToPRD-P2 AC-962-20（AC-R2P-20-4） | PR 內文不含 GH_TOKEN：leak 模式下以 token 值掃描 PR 標題與內文。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-21-1` | TCS-ResearchToPRD-P2 AC-962-21（AC-R2P-21-5、AC-R2P-20-1） | 步驟 5 取代占位：deliver 為 DeliverPanel，研究面占位面板為零個。（預定載具：components/domain/research/ResearchWorkspaceView.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-21-2` | TCS-ResearchToPRD-P2 AC-962-21（AC-R2P-20-1） | DeliverPanel 整體呈現：追溯表、發布動作列、交付紀錄、對帳狀態。（預定載具：components/domain/research/DeliverPanel.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-21-3` | TCS-ResearchToPRD-P2 AC-962-21（AC-R2P-20-2） | 建立 Tag 鈕停用規則：未覆蓋大於 0、非 RELEASE_READY、SCR_OPEN、非 ADMIN 任一成立即停用並顯示原因與未覆蓋清單。（預定載具：components/domain/research/ReleaseActions.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-21-4` | TCS-ResearchToPRD-P2 AC-962-21（AC-R2P-20-3） | Tag 確認框：semver 即時驗證、push 勾選預設未勾並附說明、成功顯示交付與快照 sha256、錯誤 reason 文案。（預定載具：components/domain/research/TagConfirmDialog.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-21-5` | TCS-ResearchToPRD-P2 AC-962-21（AC-R2P-20-4） | PR：已記錄顯示 URL（新分頁、noopener noreferrer）；無 PR 時 ADMIN 見建立 PR 並預覽標題、內文與推送目標；其餘顯示尚未建立與原因。（預定載具：components/domain/research/PrConfirmDialog.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-21-6` | TCS-ResearchToPRD-P2 AC-962-21（AC-R2P-20-5） | 開啟本地專案：顯示專案根路徑與複製鈕；容器模式標示容器內路徑；不假裝可開啟。（預定載具：components/domain/research/ReleaseActions.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-21-7` | TCS-ResearchToPRD-P2 AC-962-21（AC-R2P-20-5、AC-R2P-20-4） | GET delivery 概覽逐欄：deliveries、snapshot、projectRoot、containerMode、preconditions。（預定載具：ResearchDeliveryApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-21-8` | TCS-ResearchToPRD-P2 AC-962-21（AC-R2P-20-1、AC-R2P-20-2） | 步驟 5 的 mock E2E：版面無溢出、axe 無 serious 與 critical、兩個確認框焦點陷阱與歸還。（預定載具：tests/e2e/research-deliver.mock.spec.ts） | frontend（E2E） | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-21-E-1` | TCS-ResearchToPRD-P2 AC-962-21（AC-R2P-20-2） | RTM 100% 但非 RELEASE_READY：仍停用。（預定載具：components/domain/research/ReleaseActions.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-21-E-2` | TCS-ResearchToPRD-P2 AC-962-21（AC-R2P-20-1） | 純文字渲染：摘要含 HTML 不執行。（預定載具：components/domain/research/TraceabilityTable.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-21-E-3` | TCS-ResearchToPRD-P2 AC-962-21（AC-R2P-20-4） | 外部連結安全：所有外部連結帶 noopener noreferrer。（預定載具：components/domain/research/PrConfirmDialog.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-21-E-4` | TCS-ResearchToPRD-P2 AC-962-21（AC-R2P-20-3） | 已交付（FSM 為 RELEASE）：Tag 鈕顯示已建立並停用，不可重複送出。（預定載具：components/domain/research/ReleaseActions.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-22-1` | TCS-ResearchToPRD-P2 AC-962-22（AC-R2P-02-4、AC-R2P-20-6） | 已交付專案 records/audit：missing 為空（R11 筆數至少 1；R10 與 R12 允許 0）。（預定載具：ResearchApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-22-2` | TCS-ResearchToPRD-P2 AC-962-22（AC-R2P-02-4） | 未交付專案口徑不變：missing 仍含 R11。（預定載具：ResearchApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-22-3` | TCS-ResearchToPRD-P2 AC-962-22（AC-R2P-02-5） | Release Tag 稽核：audit_log 一列與 research.delivery 事件同 trace_id，事件含 digest 與理由。（預定載具：ResearchDeliveryApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-22-4` | TCS-ResearchToPRD-P2 AC-962-22（AC-R2P-02-5） | SCG 登錄稽核：gates 請求入 audit_log，決定列的 audit_trace_id 與之對應。（預定載具：ResearchDeliveryApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-22-5` | TCS-ResearchToPRD-P2 AC-962-22（AC-R2P-02-5、AC-R2P-20-3） | 交付列不可變與唯一：append-only 守衛、UNIQUE(research_id, kind, ref)。（預定載具：ResearchSchemaMigrationIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-22-E-1` | TCS-ResearchToPRD-P2 AC-962-22（AC-R2P-02-5） | 失敗的 tag（502）不產生 research_deliveries 列，但 audit_log 仍有一列。（預定載具：ResearchDeliveryApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-22-E-2` | TCS-ResearchToPRD-P2 AC-962-22（AC-R2P-02-5） | 重送冪等：同 (kind, ref) 不增列。（預定載具：ResearchDeliveryApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-22-E-3` | TCS-ResearchToPRD-P2 AC-962-22（AC-R2P-02-4） | R10 為 0 筆的已交付專案仍通過完整率。（預定載具：ResearchApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-23-1` | TCS-ResearchToPRD-P2 AC-962-23（AC-R2P-23-1） | CHECK_IDS 加第七項 delivery，順序固定；以原始碼為準，不寫死數字。（預定載具：test_research_reconcile.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-23-2` | TCS-ResearchToPRD-P2 AC-962-23（AC-R2P-23-4） | delivery 檢查：重算 traceability_matrix.json 的 sha256 對 snapshot_sha256；一致 ok，不符 drift。（預定載具：test_research_reconcile.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-23-3` | TCS-ResearchToPRD-P2 AC-962-23（AC-R2P-23-4） | 無交付列：absent_check，ok 且 present 為假；有列但檔缺失為 drift。（預定載具：test_research_reconcile.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-23-4` | TCS-ResearchToPRD-P2 AC-962-23（AC-R2P-23-4） | 交付時點自動對帳：reconcile_at_delivery 在 :tag 成功後恰一次，結果 consistent 為 true（出口 g）。（預定載具：test_research_reconcile.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-23-5` | TCS-ResearchToPRD-P2 AC-962-23（AC-R2P-16-1） | `:reconcile` 尾端順帶 healing.sync，失敗不影響對帳結果。（預定載具：test_research_reconcile.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-23-6` | TCS-ResearchToPRD-P2 AC-962-23（AC-R2P-23-1） | console-api 轉送七項：名稱取自 Bridge 的 CHECK_IDS，迷你 Bridge 回 7 項。（預定載具：ResearchBridgeShapeTest） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-23-7` | TCS-ResearchToPRD-P2 AC-962-23（AC-R2P-23-4） | 前端 `RECONCILE_CHECK_LABEL` 新增 delivery＝『交付』，`reconcileDriftView` 對 delivery drift 回檔案漂移列，單一橫幅顯示 delivery 漂移。（預定載具：components/domain/research/ResearchWorkspaceView.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-23-E-1` | TCS-ResearchToPRD-P2 AC-962-23（AC-R2P-23-1） | P1 的 pending_correction 第三態不受影響。（預定載具：test_research_reconcile.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-23-E-2` | TCS-ResearchToPRD-P2 AC-962-23（AC-R2P-23-4） | 只報告不修復：對帳後快照檔與 DB 列位元組不變。（預定載具：test_research_reconcile.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-24-1` | TCS-ResearchToPRD-P2 AC-962-24（AC-R2P-20-3） | reason 由 35 增為 37：新增 tag_exists（409）、delivery_step_failed（502），四方集合相等。（預定載具：ResearchReasonsTest） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-24-2` | TCS-ResearchToPRD-P2 AC-962-24（AC-R2P-15-1、AC-R2P-20-3） | OpenApiIT 計數：路徑 107 變 114、操作 124 變 131；研究路徑 30 變 37、操作 35 變 42、operationId 34 變 41、狀態碼表 35 變 42。（預定載具：OpenApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-24-3` | TCS-ResearchToPRD-P2 AC-962-24（AC-R2P-20-3） | 七個新操作的狀態碼表逐一登記：gates、tag、pr 含 403、404、409、422、502，讀端含 401、403、404。（預定載具：OpenApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-24-4` | TCS-ResearchToPRD-P2 AC-962-24（AC-R2P-15-6、AC-R2P-20-3、AC-R2P-20-4） | RBAC 矩陣：gates、tag、pr 為 ADMIN 專屬（OPERATOR 與 VIEWER 皆 403）；kanban、healing、delivery、traceability 的 GET 為 VIEWER 以上。（預定載具：RbacIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-24-5` | TCS-ResearchToPRD-P2 AC-962-24（AC-R2P-15-1） | 端點函式總數與 operationId 一一對應：118 增為 125。（預定載具：lib/api/endpoints.test.ts） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-24-6` | TCS-ResearchToPRD-P2 AC-962-24（AC-R2P-20-3） | 前端兩個新 reason 有中文文案且 research.ts 常數與後端逐字一致。（預定載具：lib/domain/research.test.ts） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-24-E-1` | TCS-ResearchToPRD-P2 AC-962-24（AC-R2P-20-3） | RESEARCH_ 前綴：新常數不污染 REASONS 集合鎖。（預定載具：ResearchReasonsTest） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-24-E-2` | TCS-ResearchToPRD-P2 AC-962-24（AC-R2P-20-3） | 未登記四方鎖的字面不得流出：Bridge 新模組的 reason 字面皆屬 37 個。（預定載具：ResearchReasonsTest） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-24-E-3` | TCS-ResearchToPRD-P2 AC-962-24（AC-R2P-20-3） | 契約與 Architecture 的 reason 表缺列由具名名單鎖住，勘誤批次後清空。（預定載具：指令核對） | gate | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-25-1` | TCS-ResearchToPRD-P2 AC-962-25（AC-R2P-21-2） | 說明登記表：步驟 4 其餘與步驟 5 的欄位釋義一次寫完，過三道鎖與 lint，HELP_PAGES 計數不變。（預定載具：lib/help/research-workspace.test.ts） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-25-2` | TCS-ResearchToPRD-P2 AC-962-25（AC-R2P-21-5） | P2 版步驟接入：五步皆真面板；Gate 0 未完成時超前導回規則不變。（預定載具：components/domain/research/ResearchWorkspaceView.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-25-3` | TCS-ResearchToPRD-P2 AC-962-25（AC-R2P-23-4） | 兩處漂移橫幅整併為工作區單一橫幅（D-131(6)）。（預定載具：components/domain/research/BuildFrontPanel.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-25-4` | TCS-ResearchToPRD-P2 AC-962-25（AC-R2P-21-5） | P0 殘留 R-3：反向斷言正則改字串拼接，AT_960_20_4 的字面掃描不再自我命中。（預定載具：components/domain/research/ResearchFlowHeader.test.tsx） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-25-5` | TCS-ResearchToPRD-P2 AC-962-25（AC-R2P-21-2） | 導覽與詞彙不動：registry.ts 零 diff，mobile 不超過 6，詞彙與衍生標籤計數與 P1 相同。（預定載具：lib/nav/research-nav.test.ts） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-25-E-1` | TCS-ResearchToPRD-P2 AC-962-25（AC-R2P-21-2） | 四區塊零差異：layout.tsx 與 components/layout/** 零 diff。（預定載具：指令核對） | gate | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-25-E-2` | TCS-ResearchToPRD-P2 AC-962-25（AC-R2P-21-2） | 狀態表不增：StateTableId 成員數不變。（預定載具：lib/help/research-workspace.test.ts） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-26-1` | TCS-ResearchToPRD-P2 AC-962-26（AC-R2P-02-10） | 字串掃描：console-api 新類對 research_* 零 INSERT、UPDATE、DELETE。（預定載具：ResearchArchTest） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-26-2` | TCS-ResearchToPRD-P2 AC-962-26（AC-R2P-20-3、AC-R2P-02-10） | delivery.record op：研究表唯一寫入者為 Bridge，DB 列與事件同一交易，fail-loud。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-26-3` | TCS-ResearchToPRD-P2 AC-962-26（AC-R2P-20-3） | outbox：DB 阻塞時 delivery.record 與 gate.decision 入 outbox，恢復後補寫，游標重衍生。（預定載具：test_research_delivery.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-26-4` | TCS-ResearchToPRD-P2 AC-962-26（AC-R2P-02-10） | 新 Java 類符合 ArchUnit 層次與命名；masker 在 persistence 層。（預定載具：ResearchArchTest） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-26-5` | TCS-ResearchToPRD-P2 AC-962-26（AC-R2P-02-5、AC-R2P-20-4） | research.delivery 事件登記：成功與失敗兩種 payload 的鍵集合定案並進 EVENT_PAYLOAD_KEYS，append_event 對登記外鍵 fail-loud。（預定載具：test_research_events.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-26-E-1` | TCS-ResearchToPRD-P2 AC-962-26（AC-R2P-20-3） | Bridge 五個新端點的檢查序：權杖、資料庫、專案存在、本文、前置。（預定載具：test_research_deliver_router.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-26-E-2` | TCS-ResearchToPRD-P2 AC-962-26（AC-R2P-02-10） | healing-sync 為內部端點：不在 console-api 路由與 OpenAPI。（預定載具：OpenApiIT） | backend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-27-1` | TCS-ResearchToPRD-P2 AC-962-27（AC-R2P-21-2） | schema.d.ts 由 backend OpenAPI 重產：七條新路徑與新 DTO 存在，重產後 diff 為空。（預定載具：指令核對） | gate | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-27-2` | TCS-ResearchToPRD-P2 AC-962-27（AC-R2P-21-2） | 手寫型別改引生成型：P2 型別皆為生成型別名的別名或引用。（預定載具：lib/api/types.test.ts） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-27-3` | TCS-ResearchToPRD-P2 AC-962-27（AC-R2P-21-2） | 夾具補必填欄、不放寬為選填（D-135）：生成型必填欄在夾具皆有值。（預定載具：lib/api/types.test.ts） | frontend | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-27-E-1` | TCS-ResearchToPRD-P2 AC-962-27（AC-R2P-21-2） | tsc、lint、build 皆 rc 0。（預定載具：指令核對） | gate | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-27-E-2` | TCS-ResearchToPRD-P2 AC-962-27（AC-R2P-21-2） | 單一歸屬：schema.d.ts 只由 FE-W3 修改。（預定載具：指令核對） | gate | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-28-1` | TCS-ResearchToPRD-P2 AC-962-28（AC-R2P-20-3、AC-R2P-15-6） | 出口 (a)：內環走完到交付。gates（PR_REVIEW PASS、RTM_VERIFY PASS）→ FSM RELEASE_READY → tag（file:// bare origin）→ FSM RELEASE，逐字證據。（預定載具：test_research_int_p2.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-28-2` | TCS-ResearchToPRD-P2 AC-962-28（AC-R2P-20-4） | 出口 (a) 的 PR URL：假 gh 走 pr create 與 pr list。（預定載具：test_research_int_p2.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-28-3` | TCS-ResearchToPRD-P2 AC-962-28（AC-R2P-16-3、AC-R2P-16-1） | 出口 (b)(f)：引擎重試耗盡自然觸發 ESCALATED（claude 為 mock 可執行檔，須標明），視圖對真失敗步驟有列。（預定載具：test_research_int_p2.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-28-4` | TCS-ResearchToPRD-P2 AC-962-28（AC-R2P-18-2、AC-R2P-16-3） | 出口 (b)：ESCALATED 後彈窗出現（mock 一次、真棧一次），決定走既有 review 端點。（預定載具：tests/e2e/research-deliver.stack.spec.ts） | frontend（E2E） | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-28-5` | TCS-ResearchToPRD-P2 AC-962-28（AC-R2P-19-1、AC-R2P-19-4） | 出口 (c)：本機模式從看板 UI 發起 MINOR SCR，Gate 0 經 approveViaApi 代驗，舊凍結版保留、新 digest 入庫。（預定載具：tests/e2e/research-deliver.stack.spec.ts） | frontend（E2E） | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-28-6` | TCS-ResearchToPRD-P2 AC-962-28（AC-R2P-23-4） | 出口 (g)：`:tag` 後對帳 consistent 為 true。（預定載具：test_research_int_p2.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-28-7` | TCS-ResearchToPRD-P2 AC-962-28（AC-R2P-15-1、AC-R2P-17-1、AC-R2P-20-1） | Docker mock-only：看板、自癒視圖、終端窗格、追溯表可驗；`:gates` 用暫存 FSM 鍵。（預定載具：tests/e2e/research-deliver.stack.spec.ts） | frontend（E2E） | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-28-8` | TCS-ResearchToPRD-P2 AC-962-28（AC-R2P-20-3） | Docker 容器模式負控：API 直呼 :tag 回 422 route_unsupported_in_deployment，DB 零變化。（預定載具：tests/e2e/research-deliver.stack.spec.ts） | frontend（E2E） | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-28-E-1` | TCS-ResearchToPRD-P2 AC-962-28（AC-R2P-16-5） | SPEC_CHANGE_FORBIDDEN 取證：暫存專案手改凍結檔，偵測加告警，sha 不被 Bridge 改動；『被拒』列 V-S1。（預定載具：test_research_int_p2.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-28-E-2` | TCS-ResearchToPRD-P2 AC-962-28（AC-R2P-20-3） | 清理義務：subst、worktree、bare repo、拋棄式 DB、假 gh 目錄、Docker 測試標籤與懸空卷無殘留。（預定載具：指令核對） | gate | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-28-E-3` | TCS-ResearchToPRD-P2 AC-962-28（AC-R2P-20-3） | hermetic：任何 P2 pytest AT 不連外網，真 GitHub 不被連線（沿 AT-961-23-E-1 的替身體例）。（預定載具：test_research_int_p2.py） | engine-bridge | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-29-1` | TCS-ResearchToPRD-P2 AC-962-29（AC-R2P-02-10） | 允許變更檔案集合：只動各包 §5.7 的集合，其餘零差異。（預定載具：指令核對） | gate | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-29-2` | TCS-ResearchToPRD-P2 AC-962-29（AC-R2P-02-10） | 禁區零差異：根 CLAUDE.md、.claude、tools、.github、AutoClaude、AISDLC_SDD、Flyway V1～V20、package.json、sdd_cli.py、rtm.py、SecurityConfig、ExecutionController、ResearchFlowPolicy.java、nav registry。（預定載具：指令核對） | gate | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-29-3` | TCS-ResearchToPRD-P2 AC-962-29（AC-R2P-02-10） | 不新增 os.replace、rename、move 站點，根層 dirent 鎖綠。（預定載具：指令核對） | gate | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-29-4` | TCS-ResearchToPRD-P2 AC-962-29（AC-R2P-02-10） | 根層 tools/tests 相關鎖自跑（D-141）：windowsapps guard 平價、E501 棘輪、_TREE_FILE_FLOORS、名冊。（預定載具：指令核對） | gate | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-29-5` | TCS-ResearchToPRD-P2 AC-962-29（AC-R2P-02-10） | Python 衛生：ruff 0 錯，新檔 open 與 read_text 與 write_text 帶 encoding，時間戳帶 tz。（預定載具：指令核對） | gate | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-29-E-1` | TCS-ResearchToPRD-P2 AC-962-29（AC-R2P-02-10） | 子行程使用者不增：除 gitops、sdd_cli 既有六檔外無新增。（預定載具：指令核對） | gate | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-29-E-2` | TCS-ResearchToPRD-P2 AC-962-29（AC-R2P-02-10） | 新增夾具目錄不含 shell 腳本，名冊不變。（預定載具：指令核對） | gate | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-29-E-3` | TCS-ResearchToPRD-P2 AC-962-29（AC-R2P-02-10） | 入庫文件守門：無測試摘要字樣加四位數字同行。（預定載具：指令核對） | gate | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-30-1` | TCS-ResearchToPRD-P2 AC-962-30（AC-R2P-20-3） | V21 DDL 與 Architecture K.6 逐字一致，且與 `V21_DDL.md` 草案對拍。（預定載具：指令核對） | gate | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-30-2` | TCS-ResearchToPRD-P2 AC-962-30（AC-R2P-20-3） | RELEASE_READY 勘誤批次：D-140 十四處與 D-139 連動寫入契約、ADR-003 D16、Architecture、PRD，並一併 refreeze。（預定載具：指令核對） | gate | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-30-3` | TCS-ResearchToPRD-P2 AC-962-30（AC-R2P-02-4） | RTM-P2 子表回填：列數等於 F 1 加 US 3 加 AC 30 加 AT 總數，四格回填，不刪列不改號。（預定載具：指令核對） | gate | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-30-4` | TCS-ResearchToPRD-P2 AC-962-30（AC-R2P-02-4） | V 系列（§6）皆有文字證據或如實標未驗。（預定載具：指令核對） | gate | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-30-5` | TCS-ResearchToPRD-P2 AC-962-30（AC-R2P-20-3） | PRD §8.1 P2 出口 (a)～(i) 逐項有證據。（預定載具：指令核對） | gate | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-30-E-1` | TCS-ResearchToPRD-P2 AC-962-30（AC-R2P-02-4） | 計數宣告一致：TCS 檔頭 AT 數、RTM 列數、§1.5 列數相等。（預定載具：指令核對） | gate | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
| `AT-962-30-E-2` | TCS-ResearchToPRD-P2 AC-962-30（AC-R2P-02-4） | 專案文件上限：AgentConsole/CLAUDE.md 不超過 200 行、README.md 不超過 80 行。（預定載具：指令核對） | gate | P2 | ⬜ | ⬜ | ⬜ | ⬜ |
