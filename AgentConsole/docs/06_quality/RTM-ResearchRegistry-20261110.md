# 2.15 研究來源單一化 Console 半（追蹤來源表 V24／V25、Bridge 追蹤來源端點與登記快照、console-api 追蹤來源與同步端點、稽核 kind `src-registry`、研究來源設定對話框追蹤來源區）的 TCS 本地 ID 追溯（對映 FR-R2P-24；不計入 §2 總列數）

**檔頭說明**：本檔依 DEF-200-576 體例自始獨立成檔（`RTM.md` §2.15 只留存根）。鍵 `agentconsole-research-registry`；規格 `AgentConsole/docs/03_testing/contracts/TCS-ResearchRegistry-20261110.md`（AC-965-1～10、AT 72 個，含勘誤 E-1～E-10）；根層接縫見 `docs/03_testing/contracts/TCS-SelfImproving-P6-20261110.md`（共享附錄 A～D 的唯一本文）。實作 commit `9e07a54e`，SCG-4 修正 `d0a750bd`（QA4C-01）；SCG-4 獨立審查報告 `AgentConsole/docs/06_quality/SCG4-REVIEW-ResearchRegistry-20261110.md`：PASS（P1 0／P2 0／P3 2）。ID 為 TCS 本地編號（AC-965-x／AT-965-x），一律加反引號、不計入 RTM.md §3 總列數。

**自動測試證據（本輪實跑）**：backend `gradlew clean build` 為 `BUILD SUCCESSFUL`，共 2572 條、0 失敗；Bridge 全套僅一條紅，為與本鍵無關的 `test_AT_961_22_E_2…[archive]` 負載逾時，單跑為綠（QA4C-02）；前端 vitest 共 2840 條全綠；mock E2E AT-965-10-2、AT-965-10-E-1 綠。**AT-965-10-1（真棧 E2E）待主控以拋棄式棧執行，不得視為已驗。**（原文保留）**更新（2026-11-10 夜，拋棄式棧 `e2ereg`）**：`-g AT_965_10_1` 單跑 1 passed——前置要一次性 chmod 稽核具名卷（卷為 root 擁有、Bridge uid 10001 寫入 EACCES ⇒ 同步 503；產品缺口 DEF-AC-036：映像未預建 `/si-audit`）；同 spec 整檔跑兩次本案皆紅（未見「有變更尚未同步」中間態，疑限流時序，DEF-AC-037，待以 trace 查證）；同檔 AT_960_22_5／22_E_1／22_3／22_4 通過、22_2 依設計略過；長駐棧 before／after 零變動。

**表格約定**：測試欄寫 `檔（AT 底線形前綴）`；backend 類別位於 `AgentConsole/backend/src/test/java/com/aisdlc/console/` 之下，Bridge 測試位於 `AgentConsole/engine-bridge/tests/`，前端測試位於 `AgentConsole/frontend/` 之下。實作檔摘要：D1＝Flyway V24／V25；D2／D3＝backend 追蹤來源與同步端點；D4＝Bridge `app/research/registry.py` 等；D5／D6＝前端純函式與元件；D7＝E2E。

| ID | 來源 | 摘要 | 層 | Phase | 實作檔 | 自動測試 | E2E 驗證 | 狀態 |
|----|------|------|----|-------|--------|----------|----------|------|
| `AT-965-1-1` | `AC-965-1` | 追蹤來源表欄位、型別與全部 CHECK 逐項 | backend | R2P | D1：`V24__research_watch_sources.sql` | `infrastructure/persistence/ResearchWatchSourceSchemaIT`（`AT_965_1_1`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-1-2` | `AC-965-1` | 受控更新守衛只放行三欄，DELETE 被擋，重新啟用清空停用欄 | backend | R2P | D1 | `ResearchWatchSourceSchemaIT`（`AT_965_1_2`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-1-3` | `AC-965-1` | 種子 17 列，15 列與 SI 舊表逐字相等，啟用 10、停用 7 | backend | R2P | D1 | `ResearchWatchSourceSchemaIT`（`AT_965_1_3`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-1-4` | `AC-965-1` | 網域種子四列 FETCH、WEB 零新增 | backend | R2P | D1 | `ResearchWatchSourceSchemaIT`（`AT_965_1_4`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-1-5` | `AC-965-1` | 種子 INSERT 重跑冪等 | backend | R2P | D1 | `ResearchWatchSourceSchemaIT`（`AT_965_1_5`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-1-6` | `AC-965-1` | 通用守衛函式重定義後九條既有允許清單不退步 | backend | R2P | D1 | `ResearchWatchSourceSchemaIT`（`AT_965_1_6`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-1-7` | `AC-965-1` | `url` CHECK 逐列等於附錄 D 的 CON 欄 | backend | R2P | D1 | `ResearchWatchSourceSchemaIT`（`AT_965_1_7`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-1-E-1` | `AC-965-1` | 既有表升級零變動與 research 表守衛不退步 | backend | R2P | D1 | `ResearchWatchSourceSchemaIT`（`AT_965_1_E_1`）、`BackupJobMigrationIT` | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-2-1` | `AC-965-2` | kind CHECK 恰六值、約束名與欄寬不變 | backend | R2P | D1：`V25__si_console_writes_kind_src_registry.sql` | `infrastructure/persistence/SiConsoleWritesMigrationIT`（`AT_965_2_1`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-2-2` | `AC-965-2` | `src-registry` 列可寫入，列不可改的觸發器不變 | backend | R2P | D1 | `SiConsoleWritesMigrationIT`（`AT_965_2_2`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-2-3` | `AC-965-2` | 自 V23 升級既有列逐列不變 | backend | R2P | D1 | `SiConsoleWritesMigrationIT`（`AT_965_2_3`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-3-1` | `AC-965-3` | Bridge POST 正控與副作用面 | Bridge | R2P | D4：`app/research/registry.py`、`routers/research.py`、`research/db.py` | `test_research_watch_sources.py`（`AT_965_3_1`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-3-2` | `AC-965-3` | 六條輸入閘規則一次全列 | Bridge | R2P | D4 | `test_research_watch_sources.py`（`AT_965_3_2`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-3-3` | `AC-965-3` | URL 原樣判定等於附錄 D CON 欄逐列 | Bridge | R2P | D4 | `test_research_watch_sources.py`（`AT_965_3_3`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-3-4` | `AC-965-3` | 單一閘 `host_not_allowed` | Bridge | R2P | D4 | `test_research_watch_sources.py`（`AT_965_3_4`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-3-5` | `AC-965-3` | 重複 slug 與 slug 永不重用 | Bridge | R2P | D4 | `test_research_watch_sources.py`（`AT_965_3_5`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-3-6` | `AC-965-3` | PATCH 規則與重新啟用 | Bridge | R2P | D4 | `test_research_watch_sources.py`（`AT_965_3_6`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-3-7` | `AC-965-3` | 停用網域後的追蹤來源狀態 | Bridge | R2P | D4 | `test_research_watch_sources.py`（`AT_965_3_7`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-3-8` | `AC-965-3` | 大小閘邊界 | Bridge | R2P | D4 | `test_research_watch_sources.py`（`AT_965_3_8`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-3-9` | `AC-965-3` | 讀端、排序、無 DSN 與權杖 | Bridge | R2P | D4 | `test_research_watch_sources.py`（`AT_965_3_9`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-3-E-1` | `AC-965-3` | R2P allowlist 端點零變動 | Bridge | R2P | D4 | `test_research_watch_sources.py`（`AT_965_3_E_1`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-4-1` | `AC-965-4` | 黃金檔 G-R1 位元組與 sha | Bridge | R2P | D4：`app/research/registry.py` | `test_research_registry_snapshot.py`（`AT_965_4_1`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-4-2` | `AC-965-4` | 確定性與插入順序無關 | Bridge | R2P | D4 | `test_research_registry_snapshot.py`（`AT_965_4_2`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-4-3` | `AC-965-4` | `hosts` 規則與位元組序 | Bridge | R2P | D4 | `test_research_registry_snapshot.py`（`AT_965_4_3`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-4-4` | `AC-965-4` | `min_interval_seconds` 算式 | Bridge | R2P | D4 | `test_research_registry_snapshot.py`（`AT_965_4_4`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-4-5` | `AC-965-4` | `watch` 全列、時間與 `expand` 形狀 | Bridge | R2P | D4 | `test_research_registry_snapshot.py`（`AT_965_4_5`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-4-6` | `AC-965-4` | 停用／重新啟用網域與 digest 往返 | Bridge | R2P | D4 | `test_research_registry_snapshot.py`（`AT_965_4_6`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-4-7` | `AC-965-4` | sha 公式與位元組衛生 | Bridge | R2P | D4 | `test_research_registry_snapshot.py`（`AT_965_4_7`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-4-8` | `AC-965-4` | 超界與無 DSN | Bridge | R2P | D4 | `test_research_registry_snapshot.py`（`AT_965_4_8`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-4-9` | `AC-965-4` | 快照路徑不讀時鐘（靜態） | Bridge | R2P | D4 | `test_research_registry_snapshot.py`（`AT_965_4_9`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-4-E-1` | `AC-965-4` | `is_public_ip` 對附錄 A 逐列 | Bridge | R2P | D4 | `test_research_registry_snapshot.py`（`AT_965_4_E_1`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-4-E-2` | `AC-965-4` | 附錄 B 列內容為 DB 夾具，快照逐位元組等於附錄 B | Bridge | R2P | D4 | `test_research_registry_snapshot.py`（`AT_965_4_E_2`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-5-1` | `AC-965-5` | 角色矩陣與零 Bridge 請求 | backend | R2P | D2：`ResearchController`、`ResearchRegistryService`、`SecurityConfig` | `adapter/in/web/ResearchWatchSourceApiIT`（`AT_965_5_1`）、`infrastructure/security/RbacIT` | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-5-2` | `AC-965-5` | ADMIN 寫入的審計與事件帳不變 | backend | R2P | D2 | `ResearchWatchSourceApiIT`（`AT_965_5_2`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-5-3` | `AC-965-5` | 輸入閘 400 先於 Bridge | backend | R2P | D2 | `ResearchWatchSourceApiIT`（`AT_965_5_3`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-5-4` | `AC-965-5` | Bridge 錯誤逐字透傳 | backend | R2P | D2 | `ResearchWatchSourceApiIT`（`AT_965_5_4`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-5-5` | `AC-965-5` | R2P allowlist 端點回應與請求數不變 | backend | R2P | D2 | `adapter/in/web/ResearchApiIT`（`AT_965_5_5`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-5-6` | `AC-965-5` | OpenAPI 操作與 DTO | backend | R2P | D2 | `ResearchWatchSourceApiIT`（`AT_965_5_6`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-5-E-1` | `AC-965-5` | ArchUnit：呼叫面與零寫入掃描 | backend | R2P | D2 | `architecture/ResearchArchTest`（`AT_965_5_E_1`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-6-1` | `AC-965-6` | 同步正控：簽章、原樣嵌入、落檔位元組 | backend | R2P | D3：`SiController`、`SiConsoleWriteService`、`SiAuditSigner.registrySyncBody`、`SiWriteKind.SRC_REGISTRY` | `adapter/in/web/SiRegistrySyncApiIT`（`AT_965_6_1`）、`application/service/SiAuditSignerTest` | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-6-2` | `AC-965-6` | 閘門序表驅動與零副作用 | backend | R2P | D3 | `SiRegistrySyncApiIT`（`AT_965_6_2`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-6-3` | `AC-965-6` | 冪等判定表 | backend | R2P | D3 | `SiRegistrySyncApiIT`（`AT_965_6_3`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-6-4` | `AC-965-6` | 補償與結果不明 | backend | R2P | D3 | `SiRegistrySyncApiIT`（`AT_965_6_4`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-6-5` | `AC-965-6` | 外層檔超界 | backend | R2P | D3 | `SiRegistrySyncApiIT`（`AT_965_6_5`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-6-6` | `AC-965-6` | Bridge `/si/registry:sync` 落檔 | Bridge | R2P | D4：`routers/si.py` | `test_si_registry_route.py`（`AT_965_6_6`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-6-7` | `AC-965-6` | G-S1：Console 副本等於根層檔，Java 重新產生位元組相等 | backend+Bridge | R2P | D3、D4 | `application/service/SiAuditSignerTest`（`AT_965_6_7`）、`test_si_console_ingest.py`（`AT_965_6_7`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-6-9` | `AC-965-6` | 冪等：D 到 E（待入帳）再到 D 照常送出 | backend | R2P | D3 | `SiRegistrySyncApiIT`（`AT_965_6_9`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-6-8` | `AC-965-6` | 機密不外洩 | backend | R2P | D3 | `SiRegistrySyncApiIT`（`AT_965_6_8`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-6-E-1` | `AC-965-6` | ArchUnit：唯一呼叫面與唯讀鎖不退步 | backend | R2P | D3 | `architecture/SiReadOnlyArchTest`（`AT_965_6_E_1`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-7-1` | `AC-965-7` | 同步狀態四態判定表 | backend | R2P | D3：狀態 DTO、`SiController` | `adapter/in/web/SiRegistryStatusApiIT`（`AT_965_7_1`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-7-2` | `AC-965-7` | `unknown` 原因與主資料失敗 | backend | R2P | D3 | `SiRegistryStatusApiIT`（`AT_965_7_2`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-7-3` | `AC-965-7` | 回應鍵集合與角色 | backend | R2P | D3 | `SiRegistryStatusApiIT`（`AT_965_7_3`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-7-4` | `AC-965-7` | `researchFetchMax` 只轉鏡像值 | backend | R2P | D3 | `SiRegistryStatusApiIT`（`AT_965_7_4`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-7-5` | `AC-965-7` | 對帳讀面新 kind | backend | R2P | D3：`SiReconcileService` | `adapter/in/web/SiConsoleWritesReadApiIT`（`AT_965_7_5`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-8-1` | `AC-965-8` | 純函式：表單驗證與請求本文 | frontend | R2P | D5：`lib/domain/researchRegistry.ts` | `lib/domain/researchRegistry.test.ts`（`AT_965_8_1`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-8-2` | `AC-965-8` | 清單渲染與警示 | frontend | R2P | D6：`components/domain/research/WatchSourcesSection.tsx` | `components/domain/research/WatchSourcesSection.test.tsx`（`AT_965_8_2`）、`researchRegistry.test.ts` | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-8-3` | `AC-965-8` | 新增流程與自動同步 | frontend | R2P | D6 | `WatchSourcesSection.test.tsx`（`AT_965_8_3`）、`researchRegistry.test.ts` | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-8-4` | `AC-965-8` | 停用與重新啟用 | frontend | R2P | D6 | `WatchSourcesSection.test.tsx`（`AT_965_8_4`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-8-5` | `AC-965-8` | 同步狀態列文案 | frontend | R2P | D5、D6 | `WatchSourcesSection.test.tsx`、`researchRegistry.test.ts`（`AT_965_8_5`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-8-6` | `AC-965-8` | 同步錯誤文案與重試 | frontend | R2P | D5、D6 | `WatchSourcesSection.test.tsx`、`researchRegistry.test.ts`（`AT_965_8_6`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-8-7` | `AC-965-8` | 手動同步鈕與併發去重 | frontend | R2P | D6 | `WatchSourcesSection.test.tsx`（`AT_965_8_7`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-8-8` | `AC-965-8` | 角色與既有 AT-960-19-8 不退步 | frontend | R2P | D6：`AllowlistDialog.tsx` | `components/domain/research/AllowlistDialog.test.tsx`（`AT_965_8_8`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-8-E-1` | `AC-965-8` | 靜態掃描 | frontend | R2P | D5 | `lib/domain/researchRegistry.static.test.ts`（`AT_965_8_E_1`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-8-E-2` | `AC-965-8` | 鍵盤、焦點與 aria | frontend | R2P | D6 | `WatchSourcesSection.test.tsx`（`AT_965_8_E_2`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-9-1` | `AC-965-9` | `SiView` 一行說明 | frontend | R2P | D6：`components/domain/si/SiView.tsx` | `components/domain/si/SiView.test.tsx`（`AT_965_9_1`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-9-2` | `AC-965-9` | 對帳面板新 kind 標籤與入帳指令 | frontend | R2P | D5、D6 | `SiView.test.tsx`、`lib/domain/si.test.ts`（`AT_965_9_2`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-9-3` | `AC-965-9` | 每頁說明與既有說明鎖 | frontend | R2P | D6：`lib/help/research-workspace.ts`、`self-improving.ts` | `lib/help/research-workspace.test.ts`（`AT_965_9_3`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-9-4` | `AC-965-9` | `schema.d.ts` 與端點函式 | frontend | R2P | D5：`lib/api/{endpoints,queries,types}.ts`、`schema.d.ts` | `lib/api/research.endpoints.test.ts`、`lib/domain/researchRegistry.test.ts`（`AT_965_9_4`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-9-5` | `AC-965-9` | 橫幅三鍵具名呈現（研究來源、同步、反事實回測） | frontend | R2P | D6 | `components/domain/si/SiStatusBanner.test.tsx`（`AT_965_9_5`） | — | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-10-1` | `AC-965-10` | Docker 全棧：種子、新增、同步、稽核檔 | E2E | R2P | D7：`tests/e2e/research-docker.stack.spec.ts` | `frontend/tests/e2e/research-docker.stack.spec.ts`（`AT_965_10_1`；SCG-4 修正 `d0a750bd`：docker 缺席直接失敗，不再 `test.skip`） | 拋棄式棧單跑 1 passed（2026-11-10；稽核卷需 chmod，DEF-AC-036）；整檔跑本案紅（DEF-AC-037） | 🟡 單跑通過；DEF-AC-036／037 待修 |
| `AT-965-10-2` | `AC-965-10` | 三寬度 axe 與溢出 | E2E | R2P | D7：`tests/e2e/a11y.mock.spec.ts` | `frontend/tests/e2e/a11y.mock.spec.ts`（`AT_965_10_2`；mock） | mock E2E 綠（2026-11-10） | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |
| `AT-965-10-E-1` | `AC-965-10` | 非名單 ADMIN 的同步被拒（mock） | E2E | R2P | D7：`tests/e2e/research-registry.mock.spec.ts` | `frontend/tests/e2e/research-registry.mock.spec.ts`（`AT_965_10_E_1`；mock） | mock E2E 綠（2026-11-10） | ✅ 實作+測試（SCG-4 PASS 2026-11-10） |

## 真機與出口實查項（TCS §6.2 V 系列；不是 AT）

| 編號 | 內容 | 目前狀態 |
|------|------|----------|
| `V1` | 主控真機：Windows 本機真全棧，ADMIN 開研究來源設定，目視 17 列種子、10 啟用；新增一筆呈「待入帳」；等根層巡邏入帳後轉「已同步」（需根層半真機） | 部分已驗：API 讀回 17 列／啟用 10；同步 201 → 待入帳 → 手動 `registry-ingest`（根層 seq 88）→ 已同步（根層 V-P6-1）；巡邏自動入帳與介面目視未做 |
| `V2` | 入帳後主機 SI 鏡像檔位元組等於 Console 當下 `registry_text`（sha256 比對） | ✅ 已驗：鏡像 sha＝Console digest（根層 V-P6-1，seq 88） |
| `V3` | 根層 SI 實抓 `anthropic-research` 的 sitemap 取得三篇文章純文字（屬根層 V-P6-1） | ✅ 已驗：網站地圖展開 3 篇文章含 `.plain.txt`（RUN-SI-008，seq 89～91） |
| `V4`～`V6` | 既有研究 AT 預期值改動恰等於 §4.1；全套建置；Linux 與 Windows 各一次（macOS 未驗） | 本輪全套已跑（見檔頭）；雲端 agentconsole-ci 綠（`89766d18`）；macOS 本機未驗 |
| `V7` | 掌舵者目視研究來源設定對話框版面與文案 | 待驗 |
| `V8` | 以種子加十個新增逼近大小上限，確認 422 `registry_too_large` 出現在預期處 | 待驗 |
