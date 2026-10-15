# RTM 回填：W4-F1（前端第一棒——匯入頁、設定頁、通知徽章）

> 日期 2026-10-15｜依據：契約 v1.1（`docs/02_architecture/API_Contract_P3-6.md`）、任務書 `agent_briefs/W4F1_FRONTEND_IMPORT_SETTINGS.md`。
> 本檔**不改 RTM.md**，由主控彙整。路徑一律相對 `AgentConsole/`；測試以 `檔案::describe 區塊` 表示（區塊名即 vitest／Playwright 的標題）。
> 「E2E 驗證」欄由 QA 對真後端回填；本棒的 Playwright 是 route mock（契約形狀的假資料），**不算**真後端驗證。
> 狀態沿用 RTM §1.4 的圖例；FE 側完成但後端／QA 未驗者標 `✅ 實作+測試`（FE 欄位），不代表整列結案。

## 一、使用者故事（FE 側）

| ID | 實作檔 | 自動測試 | 狀態 |
|----|--------|----------|------|
| US-I-01 | frontend/components/domain/import/SourceCard.tsx、frontend/components/domain/import/sourceRules.ts、frontend/lib/api/endpoints.ts（`uploadImport`）、frontend/lib/api/client.ts（FormData 不設 Content-Type） | frontend/components/domain/import/SourceCard.test.tsx::步驟 1：來源 tab（US-I-01／02／06）、frontend/components/domain/import/sourceRules.test.ts::匯入檔案預檢（US-I-01：.md／.pdf／.docx、≤10MB）、frontend/lib/api/endpoints.test.ts::endpoints：檔案上傳（multipart）與下載（Blob）、frontend/tests/e2e/import.mock.spec.ts::上傳檔案：選檔（含拖放區說明）→ multipart 上傳 → 解析；副檔名不符當場擋下；後端 413 顯示 reason | ✅ 實作+測試 |
| US-I-02 | frontend/components/domain/import/SourceCard.tsx（貼上文字 tab：需求文字、來源名稱、格式）、frontend/lib/api/endpoints.ts（`importText`） | frontend/components/domain/import/SourceCard.test.tsx::步驟 1：解析選項與開始解析（US-I-05／07／08）、frontend/tests/e2e/import.mock.spec.ts::貼上文字 → 解析 → 三層樹 → 編輯任務名 → 422 三條 gate → 修正儲存 → signoff → 確認匯入 → 專案頁 | ✅ 實作+測試 |
| US-I-03 | frontend/components/domain/import/TreeEditor.tsx（folder／target／file-text 圖示、縮排、可展開說明與通過標準）、frontend/components/domain/import/StructureCard.tsx、frontend/components/domain/import/ImportView.tsx（`?id=` 還原） | frontend/components/domain/import/TreeEditor.test.tsx::三層樹預覽（US-I-03）、frontend/tests/e2e/import.mock.spec.ts::歷史記錄：列出時間／來源／狀態／專案連結／模型 Token；重開已解析的記錄，重新整理後仍還原；重開被擋下的記錄還原閘清單 | ✅ 實作+測試 |
| US-I-04 | frontend/components/domain/import/tree.ts（reducer 與序列化）、frontend/components/domain/import/NodeEditDialog.tsx、frontend/components/domain/import/nodeSchemas.ts、frontend/components/domain/import/TreeEditor.tsx（dnd-kit 拖曳排序）、frontend/lib/api/endpoints.ts（`editImportResult`） | frontend/components/domain/import/tree.test.ts::編輯操作（reducer）、frontend/components/domain/import/TreeEditor.test.tsx::編輯操作（US-I-04）：每個節點可編輯、刪除；目標可新增任務；樹尾可新增目標、frontend/components/domain/import/StructureCard.test.tsx::步驟 2：編輯（US-I-04）、frontend/components/domain/import/nodeSchemas.test.ts::節點編輯表單驗證 | ✅ 實作+測試（拖曳以 reducer 的 move 動作單元驗證；指標拖曳手勢未做 E2E） |
| US-I-05 | frontend/components/domain/import/SourceCard.tsx（執行路徑 input：等寬、絕對路徑驗證、本機／Docker 兩種寫法提示）、frontend/components/domain/import/sourceRules.ts（`EXECUTION_PATH_HINT`） | frontend/components/domain/import/SourceCard.test.tsx::步驟 1：解析選項與開始解析（US-I-05／07／08） | ✅ 實作+測試（「瀏覽按鈕」依主控裁決 ⛔ 範圍外，契約 §4.6 G-I2） |
| US-I-06 | frontend/components/domain/import/HistoryPanel.tsx、frontend/lib/domain/status.ts（`importStatus`）、frontend/lib/api/queries.ts（`useImports`） | frontend/components/domain/import/HistoryPanel.test.tsx::歷史記錄（US-I-06）、frontend/lib/domain/status.test.ts::匯入記錄狀態表（契約 §1.1；ImportStatus 六態，lib/domain/status.ts 是唯一出處）、frontend/tests/e2e/import.mock.spec.ts::歷史記錄：列出時間／來源／狀態／專案連結／模型 Token；重開已解析的記錄，重新整理後仍還原；重開被擋下的記錄還原閘清單 | ✅ 實作+測試 |
| US-I-07 | frontend/components/domain/import/SourceCard.tsx（自治等級 Level 1～10，預設取 `agent.defaultAutonomyLevel`）、frontend/components/domain/import/ImportView.tsx、frontend/lib/api/queries.ts（`useSettingsCategory`） | frontend/components/domain/import/SourceCard.test.tsx::步驟 1：解析選項與開始解析（US-I-05／07／08）、frontend/tests/e2e/import.mock.spec.ts::貼上文字 → 解析 → 三層樹 → 編輯任務名 → 422 三條 gate → 修正儲存 → signoff → 確認匯入 → 專案頁（預設自治等級取自設定） | ✅ 實作+測試 |
| US-I-08 | frontend/components/domain/import/SourceCard.tsx（補充說明 textarea，≤4,000 字元） | frontend/components/domain/import/SourceCard.test.tsx::步驟 1：解析選項與開始解析（US-I-05／07／08） | ✅ 實作+測試 |
| US-I-09 | frontend/components/domain/import/StructureCard.tsx（signoff 橫幅含 `signed_off=false` 字樣、已 signoff 綠勾、確認匯入須已 signoff 且無未儲存編輯）、frontend/components/domain/SignoffDialog.tsx（新增 `import` 種類）、frontend/lib/api/queries.ts（`useSignoffImport`、`useConfirmImport`、`useRejectImport`） | frontend/components/domain/import/StructureCard.test.tsx::步驟 2：signoff 硬閘（US-I-09）、frontend/tests/e2e/import.mock.spec.ts::貼上文字 → 解析 → 三層樹 → 編輯任務名 → 422 三條 gate → 修正儲存 → signoff → 確認匯入 → 專案頁、frontend/tests/e2e/import.mock.spec.ts::放棄：確認對話框 → REJECTED → 回到新的匯入 | ✅ 實作+測試 |
| US-I-10 | frontend/components/domain/import/gateErrors.ts、frontend/components/domain/import/parts.tsx（`ParseFailurePanel`：閘別、位置、完整原因，不截斷）、frontend/components/domain/import/TreeEditor.tsx（錯誤節點標紅）、frontend/components/domain/import/SourceCard.tsx（失敗後沿用記錄重試） | frontend/components/domain/import/parts.test.tsx::有界閘錯誤呈現（US-I-10：完整列出、不截斷）、frontend/components/domain/import/gateErrors.test.ts::有界閘錯誤正規化（US-I-10）、frontend/components/domain/import/StructureCard.test.tsx::步驟 2：編輯（US-I-04）（422 三條 gate 的儲存情境）、frontend/tests/e2e/import.mock.spec.ts::解析被有界閘擋下（422）：清單完整列出、保留已填的選項；改選項後直接重試（不重複建立記錄） | ✅ 實作+測試 |
| US-S-01 | frontend/components/domain/settings/SettingsView.tsx、frontend/components/domain/settings/labels.ts（六分類 tab 與 50 鍵中文名稱）、frontend/components/ui/pill-tabs.tsx、frontend/lib/api/queries.ts（`useSettings`） | frontend/components/domain/settings/SettingsView.test.tsx::版面與分類 tab（US-S-01）、frontend/components/domain/settings/labels.test.ts::設定頁字典與契約附錄 C 一致、frontend/tests/e2e/settings.mock.spec.ts::六個分類 tab 都能切換：標題、參數列數與契約附錄 C 一致；執行 tab 的 Token Guard 成對編輯 | ✅ 實作+測試 |
| US-S-02 | frontend/components/domain/settings/SettingsView.tsx（逐鍵儲存、停在失敗鍵、敏感鍵二次確認）、frontend/components/domain/settings/settingsModel.ts（草稿、驗證、儲存計畫）、frontend/components/domain/settings/settingsErrors.ts | frontend/components/domain/settings/SettingsView.test.tsx::修改與儲存（US-S-02）、frontend/components/domain/settings/SettingsView.test.tsx::敏感參數（US-S-02、US-S-04）、frontend/components/domain/settings/settingsModel.test.ts::儲存計畫、frontend/tests/e2e/settings.mock.spec.ts::改一個數值並儲存：只送有變動的鍵；成功 toast；修改歷史多一列、frontend/tests/e2e/settings.mock.spec.ts::敏感鍵（API Key）：儲存前二次確認，確認後以 confirm=true 送出；歷史只記遮罩 | ✅ 實作+測試 |
| US-S-03 | frontend/components/domain/settings/SettingRow.tsx（列尾「重置」IconButton）、frontend/components/domain/settings/ResetAllDialog.tsx（對六分類各一次分類級 reset）、frontend/lib/api/queries.ts（`useResetSetting`、`useResetCategory`） | frontend/components/domain/settings/SettingsView.test.tsx::重置（US-S-03）、frontend/tests/e2e/settings.mock.spec.ts::重置：單鍵（一般參數直接、敏感參數先確認並帶 confirm=true）；全部重置對六個分類各呼叫一次 | ✅ 實作+測試 |
| US-S-04 | frontend/components/domain/settings/SettingControl.tsx（ENCRYPTED：password 遮罩、顯示／隱藏）、frontend/components/domain/settings/SettingsView.tsx（顯示＝`?reveal=true`，僅 ADMIN） | frontend/components/domain/settings/SettingControl.test.tsx::設定控制項依 valueType 渲染（七種各一）、frontend/components/domain/settings/SettingsView.test.tsx::敏感參數（US-S-02、US-S-04）、frontend/tests/e2e/settings.mock.spec.ts::API Key「顯示」：ADMIN 以 reveal=true 取明文，隱藏後回遮罩 | ✅ 實作+測試 |
| US-S-05 | frontend/components/domain/settings/ConnectionTest.tsx、frontend/components/domain/settings/settingsErrors.ts（SSRF 違規類別與 host） | frontend/components/domain/settings/SettingsView.test.tsx::測試連線（US-S-05）、frontend/tests/e2e/settings.mock.spec.ts::測試連線：測試中 spinner → 綠勾「連線成功（延遲 230ms）」；失敗與 SSRF 拒絕顯示紅字原因；可帶尚未儲存的值 | ✅ 實作+測試 |
| US-S-06 | frontend/components/domain/settings/SettingsView.tsx（匯出＝Blob 下載）、frontend/components/domain/settings/ImportSettingsDialog.tsx、frontend/lib/api/client.ts（`apiDownload`、`saveBlob`） | frontend/components/domain/settings/SettingsView.test.tsx::匯出／匯入設定（US-S-06）、frontend/lib/api/client.test.ts::API client：檔案下載（apiDownload）、frontend/tests/e2e/settings.mock.spec.ts::匯出設定：POST export 下載 JSON（50 個鍵、加密參數為 <encrypted>）；匯入設定：上傳 JSON 顯示 applied／skipped／errors | ✅ 實作+測試 |
| US-S-07 | frontend/components/domain/settings/HistoryCard.tsx、frontend/components/domain/settings/settingsModel.ts（`formatHistoryLine`） | frontend/components/domain/settings/SettingsView.test.tsx::修改歷史（US-S-07）、frontend/components/domain/settings/settingsModel.test.ts::修改歷史格式（US-S-07） | ✅ 實作+測試 |
| US-S-08 | frontend/components/domain/settings/SettingRow.tsx（ⓘ 影響範圍提示行，Lucide `Info`）、frontend/components/domain/settings/SettingsView.tsx（敏感確認框列出影響提示） | frontend/components/domain/settings/SettingsView.test.tsx::版面與分類 tab（US-S-01）（影響提示、誠實標示）、frontend/components/domain/settings/SettingsView.test.tsx::敏感參數（US-S-02、US-S-04）（確認框的影響提示） | ✅ 實作+測試 |

## 二、UI 項目

| ID | 實作檔 | 自動測試 | 狀態 |
|----|--------|----------|------|
| UI-SCR-06 | frontend/app/import/page.tsx、frontend/components/domain/import/ImportView.tsx、SourceCard.tsx、StructureCard.tsx、TreeEditor.tsx、HistoryPanel.tsx、NodeEditDialog.tsx、parts.tsx（皆在 frontend/components/domain/import/） | frontend/tests/e2e/import.mock.spec.ts（六支 route mock 情境）、frontend/components/domain/import/（九個 vitest 檔） | ✅ 實作+測試（取代原路由殼；真後端 E2E 待 QA） |
| UI-SCR-09 | frontend/app/settings/page.tsx、frontend/components/domain/settings/SettingsView.tsx、SettingRow.tsx、SettingControl.tsx、TokenGuardCard.tsx、ConnectionTest.tsx、HistoryCard.tsx、ImportSettingsDialog.tsx、ResetAllDialog.tsx、labels.ts、settingsModel.ts、settingsErrors.ts（皆在 frontend/components/domain/settings/） | frontend/tests/e2e/settings.mock.spec.ts（九支 route mock 情境）、frontend/components/domain/settings/（六個 vitest 檔） | ✅ 實作+測試（取代原路由殼；真後端 E2E 待 QA） |
| UI-OVL-01（新對話框） | frontend/components/domain/import/NodeEditDialog.tsx（編輯專案／新增與編輯目標／新增與編輯任務）、frontend/components/domain/SignoffDialog.tsx（匯入草案審批）、frontend/components/domain/settings/ImportSettingsDialog.tsx、frontend/components/domain/settings/ResetAllDialog.tsx、frontend/components/domain/ConfirmDialog.tsx（放棄匯入、敏感參數儲存與重置確認的新用法） | frontend/components/domain/import/StructureCard.test.tsx（編輯、signoff、放棄對話框）、frontend/components/domain/settings/SettingsView.test.tsx（確認儲存、確認重置、全部重置、匯入設定） | ✅ 實作+測試 |
| UI-OVL-03（載入狀態：解析中 spinner） | frontend/components/domain/import/ImportView.tsx（`import-parsing`：spinner＋「AI 解析中…（套用有界閘：步驟 ≤24 / Kahn 無環 / prompt 非空）」）、frontend/components/domain/settings/ConnectionTest.tsx（測試中 spinner） | frontend/tests/e2e/import.mock.spec.ts::貼上文字 → 解析 → 三層樹 → 編輯任務名 → 422 三條 gate → 修正儲存 → signoff → 確認匯入 → 專案頁（解析中畫面）、frontend/components/domain/settings/SettingsView.test.tsx::測試連線（US-S-05） | ✅ 實作+測試 |
| UI-SCR-01（Dashboard「待審批草案數」KPI 卡；UI-KPI 組的待審批卡） | frontend/components/domain/views/DashboardView.tsx（KPI 取 `summary.pendingSignoffs`；載入前「—」） | frontend/components/domain/views/DashboardView.test.tsx::Dashboard「待審批草案數」KPI（契約 §4.5 G-06）、frontend/tests/e2e/notifications.mock.spec.ts::全部為 0：沒有徽章；Dashboard「待審批草案數」KPI 取自摘要（跨專案、含目標與任務層級），不是專案列表算出的近似值 | 🟡 部分（其餘 KPI 與「進行中的執行」屬 W4-F2） |
| UI-LAY-01（頂列通知鈴與 signoff 佇列徽章） | frontend/components/layout/TopRegion.tsx、frontend/components/domain/notifications/NotificationBell.tsx、frontend/lib/api/queries.ts（`useNotificationSummary`：每 30 秒輪詢、地板 10 秒、頁面不可見時暫停） | frontend/components/domain/notifications/NotificationBell.test.tsx::通知鈴（契約 §4.5 G-01、G-G2）、frontend/lib/api/queries.polling.test.tsx::useNotificationSummary 的輪詢節奏、frontend/components/layout/layout.test.tsx::RootLayout 渲染：四區塊各一份、frontend/tests/e2e/notifications.mock.spec.ts::通知鈴徽章＝待審核＋未確認告警；signoff 佇列鈕徽章＝待簽核；點鈴鐺開小面板列三個數字與連結 | ✅ 實作+測試（Bridge 連線點屬 W4-F2） |
| UI-DS-07（ImportStatus 標籤與顏色） | frontend/lib/domain/status.ts（`IMPORT_STATUS`、`importStatus`、`isImportReopenable`） | frontend/lib/domain/status.test.ts::匯入記錄狀態表（契約 §1.1；ImportStatus 六態，lib/domain/status.ts 是唯一出處） | ✅ 實作+測試 |
| API 層（FE 側；非 RTM 獨立列，供 API-IMP／SET／NTF 的 FE 欄對照） | frontend/lib/api/schema-p3-6.d.ts（由 openapi-p3-6.yaml 產生，入庫；`npm run gen:api-p36` 可重產）、frontend/lib/api/types.ts、frontend/lib/api/endpoints.ts（新增 20 個端點函式）、frontend/lib/api/queries.ts、frontend/lib/api/reasons.ts（附錄 B 逐字常數） | frontend/lib/api/endpoints.test.ts::endpoints：每個後端端點一個函式、frontend/lib/api/reasons.test.ts::lib/api/reasons.ts 與契約附錄 B 逐字一致 | ✅ 實作+測試 |

## 三、契約 §4 頁面↔端點矩陣的 FE 項（逐項）

### §4.1 匯入頁 `/import`

| 項 | FE 實作 | 測試 | 備註 |
|----|---------|------|------|
| I-01 來源 tab | SourceCard.tsx（`PillTabs`：上傳檔案／貼上文字／歷史記錄） | SourceCard.test.tsx::步驟 1：來源 tab（US-I-01／02／06） | 只做截圖上的三個 tab（G-I1：無 URL 匯入） |
| I-02 拖放區 | SourceCard.tsx、sourceRules.ts | SourceCard.test.tsx、sourceRules.test.ts、import.mock.spec.ts（上傳情境） | 413／415／422 的 reason 顯示在拖放區下方 |
| I-03 貼上文字 | SourceCard.tsx | SourceCard.test.tsx | |
| I-04 自治等級預設 | ImportView.tsx（`useSettingsCategory("agent")`） | import.mock.spec.ts（預設值取自設定） | 讀不到設定時預設 3 |
| I-05 執行路徑 | SourceCard.tsx | SourceCard.test.tsx | 後端 400 欄位錯誤對應回該欄位 |
| I-06 補充說明 | SourceCard.tsx | SourceCard.test.tsx | |
| I-07 開始解析與解析中 | ImportView.tsx | import.mock.spec.ts | 解析期間步驟 1 卡只隱藏不卸載，失敗後輸入還在 |
| I-08 有界閘違規 | gateErrors.ts、parts.tsx | parts.test.tsx、gateErrors.test.ts、import.mock.spec.ts | 重新整理後以 `lastParseErrors` 還原同一份清單 |
| I-09 規格被拒顯示 | gateErrors.ts（`details.bridgeReason`／`detail`） | gateErrors.test.ts、parts.test.tsx | |
| I-10 樹狀預覽 | TreeEditor.tsx、StructureCard.tsx | TreeEditor.test.tsx、import.mock.spec.ts（重新整理還原） | |
| I-11 節點編輯與排序 | tree.ts、NodeEditDialog.tsx、TreeEditor.tsx | tree.test.ts、TreeEditor.test.tsx、StructureCard.test.tsx | 新增目標自行產生 `g-<8 碼>` key；編輯會撤銷 signoff 並明示 |
| I-12 解析提示 | parts.tsx（`ParseWarnings`） | parts.test.tsx、import.mock.spec.ts | 見交卷〈契約缺口〉第 1 項：重新整理後無法還原 |
| I-13 signoff 橫幅與審批 | StructureCard.tsx、SignoffDialog.tsx | StructureCard.test.tsx、import.mock.spec.ts | approver 預設帶目前使用者 |
| I-14 已 signoff 綠勾 | StructureCard.tsx | StructureCard.test.tsx | |
| I-15 放棄 | StructureCard.tsx（ConfirmDialog） | StructureCard.test.tsx、import.mock.spec.ts | |
| I-16 確認匯入 | StructureCard.tsx | StructureCard.test.tsx、import.mock.spec.ts（導向專案頁） | 未 signoff 或有未儲存編輯時禁用 |
| I-17 歷史列表 | HistoryPanel.tsx | HistoryPanel.test.tsx、import.mock.spec.ts | 只有仍有下一步的記錄可開啟 |

### §4.4 設定頁 `/settings`

| 項 | FE 實作 | 測試 | 備註 |
|----|---------|------|------|
| S-01 分類 tab | SettingsView.tsx、labels.ts | SettingsView.test.tsx、labels.test.ts、settings.mock.spec.ts | |
| S-02 label 與說明 | labels.ts（50 鍵字典）、SettingRow.tsx | labels.test.ts（與附錄 C 逐鍵對帳） | `model.apiUrl` 提示「完整的 chat-completions 端點 URL」；`monitor.refreshIntervalMs` 提示最小 10000 |
| S-03 控制項型別 | SettingControl.tsx | SettingControl.test.tsx（七種各一） | 數值用 inputMode，不用 type=number |
| S-04 值、預設與重置 | SettingRow.tsx、SettingsView.tsx | SettingsView.test.tsx::重置（US-S-03） | 已是預設值時重置停用 |
| S-05 遮罩與顯示切換 | SettingControl.tsx、SettingsView.tsx | SettingsView.test.tsx::敏感參數（US-S-02、US-S-04） | 非 ADMIN 按鈕停用並提示 |
| S-06 驗證紅字 | settingsModel.ts（`validateValue`）、settingsErrors.ts | settingsModel.test.ts、SettingsView.test.tsx::修改與儲存（US-S-02） | 後端 400 的 reason 與 errors[0] 對應到該列 |
| S-07 測試連線 | ConnectionTest.tsx | SettingsView.test.tsx::測試連線（US-S-05） | 只帶改過、尚未儲存的欄位 |
| S-08 修改歷史 | HistoryCard.tsx | SettingsView.test.tsx::修改歷史（US-S-07） | 目前分類 tab 的歷史 |
| S-09 儲存變更 | SettingsView.tsx、settingsModel.ts（`buildSavePlan`） | settingsModel.test.ts::儲存計畫、SettingsView.test.tsx | token_guard 任一鍵有改就走群組端點 |
| S-10 全部重置 | ResetAllDialog.tsx | SettingsView.test.tsx::重置（US-S-03） | 六分類各一次；加密參數須勾選才帶 `confirm=true` |
| S-11 匯出／匯入 | SettingsView.tsx、ImportSettingsDialog.tsx | SettingsView.test.tsx::匯出／匯入設定（US-S-06） | |
| S-12 影響範圍提示 | SettingRow.tsx（ⓘ 行）、SettingsView.tsx（敏感確認框） | SettingsView.test.tsx | |
| S-13 僅儲存標示 | SettingRow.tsx（`effect-tag`） | SettingsView.test.tsx::版面與分類 tab（US-S-01） | `STORED_ONLY`／`UNVERIFIED` 兩種 |
| S-14 敏感參數二次確認 | SettingsView.tsx（先彈窗、再以 `confirm=true` 送出） | SettingsView.test.tsx::敏感參數（US-S-02、US-S-04） | |

### §4.5 全域元素

| 項 | FE 實作 | 測試 |
|----|---------|------|
| G-01 通知鈴 | NotificationBell.tsx、TopRegion.tsx | NotificationBell.test.tsx、notifications.mock.spec.ts |
| G-02 signoff 佇列徽章 | TopRegion.tsx | layout.test.tsx::RootLayout 渲染：四區塊各一份、import.mock.spec.ts |
| G-06 Dashboard 待審批草案數 | DashboardView.tsx | DashboardView.test.tsx、notifications.mock.spec.ts |
