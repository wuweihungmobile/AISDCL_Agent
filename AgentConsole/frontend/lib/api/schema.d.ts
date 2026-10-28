/**
 * 由 scripts/gen-api.mjs 依後端 /v3/api-docs 自動產生（openapi-typescript），請勿手改。
 * 重新產生：npm run gen:api（後端需在線；位址見 scripts/gen-api.mjs）。
 */

export interface paths {
    "/api/v1/tasks/{id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 查詢任務詳情
         * @description 含最近一次執行日誌與執行歷史：executionHistory 由 execution_steps 依 task_id 衍生（跨執行批次、依時間升冪、最多最近 200 筆；STARTED／RETRYING／COMPLETED／FAILED 各一列；tokensUsed 只在 COMPLETED／FAILED 列）；從未執行過為空清單
         */
        get: operations["get"];
        /**
         * 更新任務
         * @description 可改名稱、說明、通過標準、maxRetries、evaluatorCommand、expectedOutputRegex、passCriteriaSpec
         */
        put: operations["update"];
        post?: never;
        /**
         * 刪除任務（軟刪除）
         * @description 所屬專案有進行中批次（INITIALIZING／RUNNING／PAUSED）回 409 reason=project_executing（details＝{projectId, runId}；v1.2，C-8）；其次，RUNNING 狀態的任務回 409
         */
        delete: operations["delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/settings/{category}/{key}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * 更新單一參數
         * @description 驗證順序：404 鍵不存在 → 400 型別／validationRule／範圍／SEC-04 allowlist（model.apiUrl）→ 400 token_guard 單鍵跨鍵校驗（讀對端鍵現值）→ 409 敏感參數未帶 confirm=true
         */
        put: operations["update_1"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/settings/execution/token-guard": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * 原子更新 token_guard 群組（NFR-SEC-05）
         * @description compactThresholdPct 與 haltThresholdPct 一併提交，同一交易內跨鍵校驗 halt > compact；不滿足 → 400（reason 逐字：halt_threshold_pct 必須大於 compact_threshold_pct）；任何失敗都不改任何一個鍵
         */
        put: operations["updateTokenGuard"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 查詢專案詳情
         * @description 含目標摘要清單（每個目標的任務數與已完成數）
         */
        get: operations["get_1"];
        /**
         * 更新專案
         * @description EXECUTING 狀態只准改 name／description，其他欄位有變更回 409
         */
        put: operations["update_2"];
        post?: never;
        /**
         * 刪除專案（軟刪除）
         * @description is_deleted=true、status=ARCHIVED，連帶軟刪目標與任務；EXECUTING 回 409
         */
        delete: operations["delete_1"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{id}/sdd-binding": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * 編輯專案的 FSM 專案（改綁；v1.5，D-115-14）
         * @description 存入去前後空白後的值（非 null 時 1～100 字元、不含控制字元；null＝清除，回到「用預設」＝專案名；鍵缺席 → 400），不檢查狀態檔是否存在、不呼叫 Bridge；先檢查唯一性（同 executionPath 已有未刪除專案以同一個 sddProject 綁定 → 409 sdd_binding_conflict）；相同值再送＝冪等（200，不寫稽核）。改綁不搬移 FSM 狀態檔，也不影響進行中的批次。寫 audit（project.sdd.bind）。
         */
        put: operations["updateProjectSddBinding"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/issues/{id}/priority": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * 設定議題的優先順序（議題中心；僅 ADMIN）
         * @description 設定或更新該議題的順位與備註（Console 自有資料；不寫帳本，也不要求 console.si.deciders 名單）。驗證順序固定：角色（僅 ADMIN；否則 403 ACCESS_DENIED）→ 本文不是 JSON 物件（400 MALFORMED_REQUEST_BODY）→ 輸入閘（422 invalid_request；details.violations[{field,message}] 一次全列，Bridge 零呼叫）→ 取該議題（Bridge 失敗 503／502／504；查無 404 si_not_found）→ 議題狀態不可排（409 issue_not_rankable；details.id、details.status）→ UPSERT。任一前序失敗都零寫入。成功 200：寫入的那一列。後者生效（setBy、setAt 為後者）。
         */
        put: operations["putIssuePriority"];
        post?: never;
        /**
         * 清除議題的優先順序（議題中心；僅 ADMIN）
         * @description 刪除該議題的順位列。冪等：列不存在也是 204。不呼叫 Bridge，所以議題已結案或已不存在時仍清得掉遺留的列。驗證順序固定：角色（僅 ADMIN；否則 403 ACCESS_DENIED）→ id 格式（422 invalid_request）→ 刪除。沒有本文。
         */
        delete: operations["deleteIssuePriority"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/import/{id}/result": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * 編輯解析結果（重新過有界閘）
         * @description 以整棵樹覆寫 project 與 goals（陣列順序即排序）；成功後 status=REVIEWING，編輯會撤銷既有 signoff
         */
        put: operations["editResult"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/goals/{id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 查詢目標詳情
         * @description 含依賴目標 id 與任務標題清單
         */
        get: operations["get_2"];
        /**
         * 更新目標
         * @description dependsOn：null＝不變、空陣列＝清除、有值＝整組取代（Kahn 防環）
         */
        put: operations["update_3"];
        post?: never;
        /**
         * 刪除目標（軟刪除）
         * @description 連帶軟刪其下任務；所屬專案有進行中批次（INITIALIZING／RUNNING／PAUSED）回 409 reason=project_executing（details＝{projectId, runId}；v1.2，C-8）；其次，含 RUNNING 任務回 409
         */
        delete: operations["delete_2"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/goals/reorder": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * 調整目標順序
         * @description orderedGoalIds 須恰好是專案下全部（未刪除）目標，依新順序重寫 sortOrder
         */
        put: operations["reorder"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{id}/signoff": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 人工 signoff 任務草案
         * @description approver 必填、非空白；缺漏回 400；已 signoff 回 409
         */
        post: operations["signoff"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{id}/retry": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 手動重試任務
         * @description 只允許 FAILED／ESCALATED：retryCount+1、狀態轉 QUEUED；其他狀態回 409
         */
        post: operations["retry"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/sysadmin/backups/jobs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 備份工作紀錄（唯讀；Console 發起的手動工作）
         * @description requested_at 嚴格新到舊；排程工作不在此表（看總覽的狀態卡）。limit 預設 20、1～100；before 為 ISO-8601 時間（嚴格小於 requested_at）；參數非法 → 422 invalid_request（details.violations[{field,message}]）。回 {items, nextBefore}。requestedBy、detail 僅 ADMIN。控制面未設定或資料庫讀取失敗 → 503 backup_control_unavailable。VIEWER 以上可讀。
         */
        get: operations["getBackupJobs"];
        put?: never;
        /**
         * 手動觸發備份（全備、增備、驗證；僅 ADMIN）
         * @description body {type:"full|diff|verify", confirm:true}。驗證順序固定：角色（僅 ADMIN；否則 403 ACCESS_DENIED）→ 本文不是 JSON 物件（400 MALFORMED_REQUEST_BODY）→ type 缺、非字串或不合（422 invalid_request；details.violations）→ confirm 不是 JSON 布林 true（400 backup_confirm_required）→ 控制面不可用（503 backup_control_unavailable：目錄未設、心跳過期、匯出不可讀、資料庫讀取失敗）→ 已有 QUEUED 或 RUNNING（409 backup_job_in_progress）→ 頻率上限（409 backup_too_frequent；full 86400 秒、diff 3600 秒、verify 不設；details.type、details.nextAllowedAt）→ 建列並寫請求檔；寫檔失敗該列補償為 FAILED（control_write_failed）並回 503。任一前序失敗都零列、零檔。成功 202：工作已排入佇列（QUEUED），多餘的鍵忽略、id 由伺服器產生。
         */
        post: operations["postBackupJob"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/si/proposals/{id}/decide": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 對待決提案或暫停的運轉下決定（P2b；僅 ADMIN）
         * @description 九種動詞（approve、reject、return、promote、decline-promote、rollback、unblock、resume、ack-handoff；沒有批次核准）；路徑 id 為 PROP 號（resume 為 RUN 號）。各動詞必填與禁止的欄位見 SiDecideRequest；多帶或缺帶一律 422。驗證順序固定：角色（僅 ADMIN；否則 403 ACCESS_DENIED）→ 帳號須在 console.si.deciders（403 si_write_forbidden）→ 寫入面啟用（503 si_write_disabled；details.cause＝audit_key_unset｜bridge_token_unset）→ 輸入閘（422 invalid_request；details.violations[{field,message}] 一次全列）→ 簽章、寫 Console 稽核列、單次 Bridge 呼叫（連線 2 秒／讀取 20 秒、不重試）。Bridge 明確拒絕或確定未落檔時補償刪除稽核列；結果不明（504、送出後連線重設的 502、2xx 本文無法解析的 502）時保留該列並在 details.outcomeUnknown 標明。重送一律新 auditRef。201 的意思是稽核檔已落地、待入帳（由主機端根層 CLI 以 --carrier console 驗簽入帳），不是已入帳。
         */
        post: operations["postSiDecide"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/si/observations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * SelfImproving 觀察帳本（唯讀；P1b）
         * @description Bridge GET /si/observations 的原樣轉遞：帳本逐列（九欄、marksKv、line）；無法解析的壞列以 {line, raw, valid:false} 出現，problems 逐項說明。游標分頁：truncated 為 true 時以 nextSince 取下一頁。失敗沒有 data。VIEWER 以上可讀。
         */
        get: operations["getSiObservations"];
        put?: never;
        /**
         * 新增觀察列（P2b；僅 ADMIN）
         * @description 新增一列處置為 open 的觀察；corrects 帶被更正列的 OBS 號時產生 rel=corrects 標記。建議先呼叫 observations/validate 預檢。驗證順序固定：角色（僅 ADMIN；否則 403 ACCESS_DENIED）→ 帳號須在 console.si.deciders（403 si_write_forbidden）→ 寫入面啟用（503 si_write_disabled；details.cause＝audit_key_unset｜bridge_token_unset）→ 輸入閘（422 invalid_request；details.violations[{field,message}] 一次全列）→ 簽章、寫 Console 稽核列、單次 Bridge 呼叫（連線 2 秒／讀取 20 秒、不重試）。Bridge 明確拒絕或確定未落檔時補償刪除稽核列；結果不明（504、送出後連線重設的 502、2xx 本文無法解析的 502）時保留該列並在 details.outcomeUnknown 標明。重送一律新 auditRef。201 的意思是稽核檔已落地、待入帳（由主機端根層 CLI 以 --carrier console 驗簽入帳），不是已入帳。
         */
        post: operations["postSiObservation"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/si/observations/{id}/close": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 關閉處置為 open 的觀察列（P2b；僅 ADMIN）
         * @description 把處置為 open 的觀察列一次關成七個終值之一（沒有 open）；路徑 id 為 OBS 號。是否存在、是否仍為 open 由根層 CLI 入帳時判（不成立＝入帳被拒，稽核檔與 Console 稽核列原地不動，持續顯示待入帳）。驗證順序固定：角色（僅 ADMIN；否則 403 ACCESS_DENIED）→ 帳號須在 console.si.deciders（403 si_write_forbidden）→ 寫入面啟用（503 si_write_disabled；details.cause＝audit_key_unset｜bridge_token_unset）→ 輸入閘（422 invalid_request；details.violations[{field,message}] 一次全列）→ 簽章、寫 Console 稽核列、單次 Bridge 呼叫（連線 2 秒／讀取 20 秒、不重試）。Bridge 明確拒絕或確定未落檔時補償刪除稽核列；結果不明（504、送出後連線重設的 502、2xx 本文無法解析的 502）時保留該列並在 details.outcomeUnknown 標明。重送一律新 auditRef。201 的意思是稽核檔已落地、待入帳（由主機端根層 CLI 以 --carrier console 驗簽入帳），不是已入帳。
         */
        post: operations["postSiObservationClose"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/si/observations/validate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 新增觀察列的唯讀預檢（P2b；僅 ADMIN）
         * @description 根層 obs-add --dry-run：回預覽列、位元組數與根層的拒收原因（ok=false 仍是 200）。不取 auditRef、不簽章、不寫 Console 稽核列、不落檔、不寫帳本。與新增觀察同一關（授權、停用、輸入閘）；Bridge 回 503 si_unavailable 時原因逐字轉出。驗證順序固定：角色（僅 ADMIN；否則 403 ACCESS_DENIED）→ 帳號須在 console.si.deciders（403 si_write_forbidden）→ 寫入面啟用（503 si_write_disabled；details.cause＝audit_key_unset｜bridge_token_unset）→ 輸入閘（422 invalid_request；details.violations[{field,message}] 一次全列）→ 簽章、寫 Console 稽核列、單次 Bridge 呼叫（連線 2 秒／讀取 20 秒、不重試）。Bridge 明確拒絕或確定未落檔時補償刪除稽核列；結果不明（504、送出後連線重設的 502、2xx 本文無法解析的 502）時保留該列並在 details.outcomeUnknown 標明。重送一律新 auditRef。201 的意思是稽核檔已落地、待入帳（由主機端根層 CLI 以 --carrier console 驗簽入帳），不是已入帳。
         */
        post: operations["postSiObservationValidate"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/settings/{category}/{key}/reset": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 重置單一參數為預設值
         * @description 寫歷史。token_guard 單鍵重置後若違反 halt > compact → 400；加密鍵需 confirm=true，否則 409
         */
        post: operations["reset"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/settings/{category}/reset": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 重置整個分類為預設值（補充端點）
         * @description 同一交易內逐鍵重置並各寫歷史；加密鍵預設略過（要連同重置須 confirm=true）；token_guard 以重置後的最終值做跨鍵校驗，不滿足 → 400 且整批不套用
         */
        post: operations["resetCategory"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/settings/test-connection": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 測試模型連線（SEC-04）
         * @description 預設測試已儲存的 model.apiUrl／apiKey；body（選填）可帶尚未儲存的值。對完整端點原樣送一則 1-token 的 POST ping；連線釘死在已驗證的 IP、不跟 redirect。SSRF／allowlist 檢查未過 → 422；網路層結果 → 200＋success=false
         */
        post: operations["testConnection"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/settings/import": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 匯入設定（JSON 檔）
         * @description multipart 欄位 file（≤ 1MB、version=1）。逐筆驗證，通過者在同一交易套用並寫歷史；<encrypted> 佔位值略過；token_guard 兩鍵以合併後的最終值做 halt > compact 跨鍵校驗。經 nginx 時須有 client_max_body_size 2m（契約 §0.7）
         */
        post: operations["importSettings"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/settings/export": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 匯出設定（JSON 檔）
         * @description 不包 ApiResult 封包，直接回檔案；加密參數的 value 一律輸出佔位字串 <encrypted>（匯入時略過）
         */
        post: operations["export"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 查詢專案列表
         * @description 分頁、名稱模糊搜尋、狀態篩選、排序；預設排除已軟刪除。deleted=true 改為「只列軟刪除的專案」（OPERATOR 以上，VIEWER 回 403 ACCESS_DENIED；列表項帶 deletedAt；保留期已過的專案仍會列出，按復原才會得到 409 restore_window_expired；v1.2，C-3）
         */
        get: operations["list"];
        put?: never;
        /**
         * 建立專案
         * @description 狀態預設 DRAFT；手動建立 signedOff=true，draft=true 時為 false
         */
        post: operations["create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{projectId}/goals": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 查詢目標列表
         * @description 依 sortOrder 排序；含任務數、已完成數與完成比例（只算未軟刪）
         */
        get: operations["list_1"];
        put?: never;
        /**
         * 建立目標
         * @description dependsOn 以 Kahn 試算防環；成環／自依賴／跨專案回 400
         */
        post: operations["create_1"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{projectId}/execute": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 啟動專案執行
         * @description 後端二次硬校驗（前端按鈕禁用只是體驗）。驗證順序固定：404 專案 → 400 欄位驗證 → 409 專案正在執行中 → 409 專案狀態不允許執行 → 409 未經人工審批的草案不可執行 → 400 範圍 id 不屬於此專案 → 409 範圍問題 → 409 目標依賴成環 → 422 物化失敗 → Bridge（409 鎖／422／502／504，並補償刪除剛建的 run 列）。成功：建立 execution_runs（run_number 同專案遞增）→ Bridge POST /autoclaude/runs → 專案 EXECUTING、範圍內任務 QUEUED、啟動事件消費者。v1.3：依自治等級（≥ 6 要求自動突變、≥ 7 要求自演化）與旗標物化引擎設定，回應的 engineCapabilities 如實標示「實際送進引擎的」能力（沒有 model.apiKey 不報錯，回 UNAVAILABLE_NO_API_KEY）
         */
        post: operations["execute"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{id}/signoff": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 人工 signoff 專案草案
         * @description approver 必填、非空白；缺漏回 400；已 signoff 回 409
         */
        post: operations["signoff_1"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{id}/sdd/freeze": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 核准凍結 SDD 規格（人工閘；v1.5，D-115-03）
         * @description PRD §0.4 把 Console 的 signoff 對映 FSM 的 HUMAN_PENDING：本端點是 Console 對 FSM 唯一的寫入動詞，HUMAN_PENDING→SPEC_FROZEN，帶 approver（一律取 JWT subject，不可由 client 指定）、理由與文件摘要。驗證順序固定：專案存在（404）→ 請求驗證（400）→ backend 沒有設定寫入權杖（503 sdd_write_disabled）→ 唯讀取標準鍵（Bridge GET /sdd/fsm/{project}?root=）→ 綁定唯一性與寫回（409 sdd_binding_conflict；獨立短交易、先於 Bridge 寫入）→ Bridge POST /sdd/fsm/{project}:freeze（帶 X-Bridge-Token，讀取逾時 40 秒、不重試）。Bridge 失敗對映：fsm_state_conflict→409 sdd_fsm_state_conflict；fsm_not_found→409 sdd_fsm_not_found；spec_digest_changed→409 sdd_spec_digest_changed；422→引擎拒絕此請求；503 sdd_write_disabled→503；403 sdd_write_forbidden→502（設定缺陷）。非冪等：第二次呼叫（FSM 已不在 HUMAN_PENDING）→ 409 sdd_fsm_state_conflict。寫 audit（project.sdd.freeze）。成功 200：凍結後的 FSM 狀態（與 GET /engines/sdd 的 fsm 同形）。
         */
        post: operations["freezeProjectSddSpec"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{id}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 復原軟刪除的專案（v1.2 補充端點）
         * @description 復原專案與同一次刪除連帶軟刪的目標／任務（以相同的 deleted_at 辨識；單獨先刪除的目標／任務不回來）；專案 status 還原為刪除前的狀態（升級前就已軟刪者：未 signoff → DRAFT、已 signoff → READY）。前置：專案已軟刪除，且 deleted_at 在保留期內（console.retention.soft-delete-days，預設 30 天；與清除排程是否開啟無關）。找不到該 id（含已被清除）→ 404；未被刪除 → 409 project_not_deleted；已逾保留期 → 409 restore_window_expired。寫 audit（project.restore）
         */
        post: operations["restore"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/monitor/alerts/{alertId}/acknowledge": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 確認告警
         * @description 寫入 acknowledged／By／At。冪等：已確認的告警再次確認仍回 204，且不改寫第一次的確認人與時間。確認後同一規則＋對象可再產生新告警
         */
        post: operations["acknowledge"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/import/{id}/signoff": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 🔴 人工 signoff 匯入草案（只批准，不落庫）
         * @description approver 必填、非空白（不可匿名）；路徑 C 對每個 draftId 呼叫 Bridge :approve；已 signoff 回 409
         */
        post: operations["signoff_2"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/import/{id}/reject": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 放棄匯入（補充端點）
         * @description status 轉 REJECTED；已 IMPORTED／REJECTED 或解析中回 409
         */
        post: operations["reject"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/import/{id}/parse": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 觸發 AI 解析（三條路徑擇一）
         * @description 同步呼叫。路徑 A（SDD 規格）> C（高階目標，Bridge decompose）> B（OpenAI 相容 LLM）；三道有界閘與 prompt_too_long 任一不過 → 422（記錄退回 UPLOADED），不截斷不修剪
         */
        post: operations["parse"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/import/{id}/confirm": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 確認匯入（單一交易建立專案／目標／任務）
         * @description 要求 signedOff=true，否則 409；全部 signedOff=true、signedOffBy／At 承襲匯入記錄
         */
        post: operations["confirm"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/import/upload": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 上傳 BRD/PRD 檔案
         * @description 副檔名限 .md／.pdf／.docx（不分大小寫）、大小 ≤ 10MB；後端擷取純文字存入 sourceContent。經 nginx 時 /api/v1/import/ 須設 client_max_body_size 11m（契約 §0.7）
         */
        post: operations["upload"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/import/text": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 貼上純文字建立匯入記錄
         * @description sourceType 只接受 PLAIN_TEXT（預設）與 MARKDOWN；路徑判斷（高階目標 vs 結構化文件）在 parse 階段
         */
        post: operations["importText"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/goals/{id}/signoff": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 人工 signoff 目標草案
         * @description approver 必填、非空白；缺漏回 400；已 signoff 回 409
         */
        post: operations["signoff_3"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/goals/{goalId}/tasks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 查詢任務列表
         * @description 依 sortOrder 排序
         */
        get: operations["list_2"];
        put?: never;
        /**
         * 建立任務
         * @description NFR-SEC-03：evaluatorCommand 命中黑名單字元、expectedOutputRegex 不可編譯皆回 400
         */
        post: operations["create_2"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/executions/{runId}/review/{stepId}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 審核執行結果（通過／拒絕／重試／跳過）
         * @description 路徑的 {stepId} 是 review_requests.id（UUID），不是 playbook 的 step_id。審核人取自 JWT subject。可用的決定由審核項的 allowedDecisions 決定；不在其內 → 409「此審核項不允許該決定」。成功 204。SKIP（以及找不到還原點的 RETRY）會另開後續批次（follow-up run），其 id 放在回應標頭 X-Follow-Up-Run-Id
         */
        post: operations["review"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/executions/{runId}/resume": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 恢復執行（PAUSED 同進度接續）
         * @description Bridge :resume（只收 PAUSED）。後端先重驗範圍內 Goal／Task 皆 signedOff（否則 409「未經人工審批的草案不可執行」）。回應 bridgeStatus=RUNNING
         */
        post: operations["resume"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/executions/{runId}/restore/{checkpointId}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 從指定歷史 checkpoint 還原並續跑
         * @description Bridge POST /autoclaude/runs/{id}/restore（接受 PAUSED 與終態 COMPLETED／FAILED／CANCELLED；終態已放的鎖須重新取得，可能 409）。還原點之後的任務與目標由後端「系統重設」；專案回 EXECUTING。後端先重驗範圍內 signedOff。restore 沿用該 run 建立時的 playbook；只允許對專案最新的批次 restore（否則 409「只能還原專案最新的執行批次」）
         */
        post: operations["restore_1"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/executions/{runId}/pause": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 暫停執行（下一個步驟邊界生效）
         * @description Bridge :pause（只收 RUNNING；PAUSING 時冪等）。回應的 bridgeStatus 為 PAUSING，status 仍是 RUNNING，直到 SSE 送出 status-change（PAUSED）。已在最後一步時暫停來不及，run 照常 COMPLETED
         */
        post: operations["pause"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/executions/{runId}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 取消執行（stop）
         * @description Bridge :stop（RUNNING／PAUSING／PAUSED 可收）。回應 bridgeStatus=CANCELLING；終態 CANCELLED 由 SSE 通知。取消後範圍內 RUNNING／QUEUED 任務轉 CANCELLED（系統重設，US-E-06），專案回 READY
         */
        post: operations["cancel"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/refresh": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 以 refresh token 換新的 token
         * @description refresh token 無效、過期或已被撤銷回 401（reason INVALID_REFRESH_TOKEN）；access token 不可當 refresh token 用。換新時原子地撤銷舊的 refresh token：同一個 token 的兩個併發換新只有一個成功（v1.4，D-19）
         */
        post: operations["refresh"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 登出並撤銷 refresh token（v1.4 補充端點，D-19；免認證）
         * @description 登出時撤銷該 refresh token 的 jti（撤銷名單：Redis 優先，不在線降級為單實例記憶體並記 WARN；ADR-001 D16、D23）。免認證，與 login／refresh 同：登出時 access token 可能已過期，仍必須能撤銷 refresh token。請求格式合法就一律 204：refresh token 有效 → 撤銷；無效、過期、已被撤銷、或是 access token → 同樣 204、不撤銷任何東西（不讓這支端點變成探測 token 有效性的管道）。不撤銷 access token（無狀態，最長 30 分鐘後自然失效）。撤銷後再以該 refresh token 呼叫 POST /auth/refresh → 401 INVALID_REFRESH_TOKEN。
         */
        post: operations["logout"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/login": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 登入
         * @description 帳密正確回 accessToken（30 分鐘）與 refreshToken（7 天）；失敗一律 401
         */
        post: operations["login"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/sysadmin/backups": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 備份總覽（唯讀；系統管理／資料庫備份）
         * @description 備份清單、四張最近狀態卡（全備、增備、離站 pg_dump、驗證）、排程與保留、各 repo 狀態、WAL 歸檔健康與進行中的工作。每個請求讀 sidecar 匯出的 8 個控制面檔案（不快取）。🔴 fail-loud：控制面未設定（control.reason=not_configured）、匯出檔不可讀（export_unreadable）、格式版本不符（schema_mismatch）時仍回 200，但所有資料區塊為 null（不是空陣列或 0）；runner_offline（心跳逾 30 秒）時資料照回但 canTrigger=false。個別來源失敗（info／logical 的 ok:false、cron 解析不了、資料庫讀取失敗）只降級該區塊並加 control.warnings。時間一律 UTC 帶 Z；排程時區取自 schedule.json。輸出尾段與觸發者僅 ADMIN。VIEWER 以上可讀。
         */
        get: operations["getBackupOverview"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/sysadmin/backups/jobs/{id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 單筆備份工作（唯讀）
         * @description 查無或 id 不是 UUID → 404 backup_job_not_found（不是 500、不是 422）。detail（已遮罩、最後 ≤2000 字元）與 requestedBy 僅 ADMIN。控制面未設定或資料庫讀取失敗 → 503 backup_control_unavailable。VIEWER 以上可讀。
         */
        get: operations["getBackupJob"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/stream/executions/{runId}/metrics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 即時執行指標（SSE）
         * @description 事件：metric-update、token-update、progress-update。三者都是狀態快照（latest-wins）：重連時不重播歷史，伺服器先送各一則最新快照再接即時事件（收斂重播）。三則快照的 id 互異：<S>.1＝progress-update、<S>.2＝token-update、<S>.3＝metric-update（S＝目前最後處理的 Bridge seq）；之後的即時事件 id 嚴格大於 <S>.3。run 已終態時：Last-Event-ID 已 ≥ <S>.3 → 204，否則送終態快照後關閉。其餘認證／keep-alive／框架／終態規則同 /logs
         */
        get: operations["metrics"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/stream/executions/{runId}/logs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 即時執行日誌（SSE）
         * @description 事件：log、status-change、review-request、alert（data 形狀見 Markdown 契約 §2）。認證：Authorization: Bearer 與 ?access_token= 兩者皆收（EventSource 不能帶標頭）；後端任何存取日誌不得輸出含 access_token 的 query string，nginx 的 log_format 須遮罩（契約 §0.7；AR-05）。id: 沿用 Bridge seq；後端自產的事件用 <seq>.<n>。Last-Event-ID 重播未送達事件。每 15 秒無事件送 keep-alive 註解（內容為 keep-alive）。PAUSED 不結束串流；終態後送 status-change 並關閉；重連時若 run 已終態且無事件可重播 → 204（EventSource 收到 204 不再重連）
         */
        get: operations["logs"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/signoffs/pending": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 待簽核的草案清單（跨專案；v1.4 補充端點，D-18）
         * @description 列出待 signoff 的草案：專案、目標、任務與待審批的匯入記錄四種，判準與通知摘要的 pendingSignoffs 完全相同（PROJECT：signed_off=false 且未軟刪；GOAL／TASK：另要求所屬專案（與目標）未軟刪；IMPORT：PARSED／REVIEWING 且未 signoff），計數與清單的述詞由同一處產生，不變量：counts.total 恆等於 GET /notifications/summary 的 pendingSignoffs。排序 created_at 升冪（同值以 id 升冪）；limit 只截斷 items（預設 50、上限 200），不影響 counts。IMPORT 項的 projectId／projectName／parentId 為 null（匯入記錄在 confirm 之前還沒有專案）。供儀表板「待人工審批」卡；取代前端用專案與目標 API 另組的近似清單（完整性審查 I-05）。
         */
        get: operations["getPendingSignoffs"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/si/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * SelfImproving 狀態摘要（唯讀；P1b）
         * @description Bridge GET /si/status（根層 si export --kind status）的原樣轉遞：啟動事件偵測、開啟中的運轉、待決提案、冷卻、暫停、各項「量不到」（NOT-EVALUABLE）。不分頁、不收任何查詢參數。每個請求恰一次 Bridge 呼叫（連線 2 秒、讀取 20 秒、不重試），不快取；失敗沒有 data（503 si_unavailable 帶 details.cause 與 details.detail）。VIEWER 以上可讀。
         */
        get: operations["getSiStatus"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/si/runs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * SelfImproving 運轉（唯讀；P1b）
         * @description Bridge GET /si/runs 的原樣轉遞：運轉的開關事件序號、觸發、研究事件、提案結果（outcome）。游標分頁同 observations。失敗沒有 data。VIEWER 以上可讀。
         */
        get: operations["getSiRuns"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/si/proposals": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * SelfImproving 提案清單（唯讀；P1b）
         * @description Bridge GET /si/proposals 的原樣轉遞：每筆含狀態、route、digest、verdict、cooldown 與卡面 card 字串（逐位元組等於 si card 的輸出，量不到時為 null 並於 ne 說明）。游標分頁同 observations。失敗沒有 data。VIEWER 以上可讀。
         */
        get: operations["getSiProposals"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/si/proposals/{id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * SelfImproving 單筆提案（唯讀；P1b）
         * @description Bridge GET /si/proposals/{id} 的原樣轉遞（items 恰一筆）。id 原樣嚴格 percent-encode 成單一路徑段後交給 Bridge；格式（PROP-SI-<三位以上數字>）的單一真相在 Bridge：不合 → 422（details.bridgeReason=invalid_request）。格式合法而查無 → 404（reason si_not_found，details.id；「404 的 reason 省略」慣例的第二個例外）。不收任何查詢參數。VIEWER 以上可讀。
         */
        get: operations["getSiProposal"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/si/events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * SelfImproving 事件帳本（唯讀；P1b）
         * @description Bridge GET /si/events 的原樣轉遞：事件帳本逐行（多型事件，鍵依 kind 而異，原樣轉 camelCase）。游標分頁同 observations。失敗沒有 data。VIEWER 以上可讀。
         */
        get: operations["getSiEvents"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/si/console-writes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Console 稽核列與 SelfImproving 帳本的對帳（P2b；VIEWER 以上可讀）
         * @description 回 Console 自己的稽核列（時間新到舊；不含 body 與 mac）與每列是否已入帳（ingested）、帳本中 carrier 為 console 而本表沒有對應列的項（orphans，紅色警示來源）。對帳在 backend 一次全量做：以 Bridge 的 observations 與 events 各自 limit=500 迴圈取頁（上限各 20 頁）。讀路徑唯一的副作用是把 obs-add 列的 subjectId（NULL）依帳本新列號回填（冪等）；Bridge 永遠只被呼叫 GET。量不到（Bridge 失敗、逾時、頁數超限）＝reconcile.status 為 NOT-EVALUABLE（reason：si_unavailable、bridge_unreachable、bridge_timeout、scan_cap_exceeded），items 照回、ingested 與 orphans 為 null——不回空陣列、不冒充無待入帳。
         */
        get: operations["getSiConsoleWrites"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/settings": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 查詢所有參數（依分類）
         * @description 六個分類：model／agent／execution／monitor／autoclaude／sdd。加密值一律 ••••••••，並附 hasValue；reveal=true 僅 ADMIN（其他角色 403），每次揭露寫審計
         */
        get: operations["listAll"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/settings/{category}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 查詢特定分類參數
         * @description 同 GET /api/v1/settings 的遮罩與 reveal 規則；分類不存在 → 404
         */
        get: operations["listCategory"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/settings/history": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 查詢參數修改歷史（分頁）
         * @description 由新到舊。加密參數的 oldValue／newValue 一律遮罩；單獨給 key（沒有 category）回 400
         */
        get: operations["history"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{projectId}/executions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 列出專案執行批次（補充端點，ADR-001 G-16）
         * @description 分頁；預設 startedAt,desc。每列帶批次比較所需的 Token／時間／成功率（US-M-06），供執行頁挑選目前批次與監控頁「執行批次」下拉
         */
        get: operations["list_3"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/notifications/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 通知與待辦計數（補充端點，ADR-001 G-17）
         * @description 供頂列通知鈴與 signoff 佇列徽章。pendingSignoffs＝專案、目標、任務三表中未 signoff 且未軟刪的列數＋待審批的匯入記錄數；輪詢間隔不得小於 monitor.refreshIntervalMs（預設與最小 10 秒）
         */
        get: operations["summary"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/monitor/task-totals": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 全域任務總計（跨專案；v1.2 補充端點）
         * @description 跨全部未封存且未軟刪除的專案，execution_steps 在 [from, to) 內 STARTED／COMPLETED／FAILED／RETRYING 的列數（與 task-trend 同一張表、同一判準，只計所屬任務未軟刪的列；只是不分桶、不分專案）。取代前端對每個專案各打一次 task-trend 再加總的做法（DEF-AC-009）。from 必填；to 省略＝現在；from 必須早於 to 且視窗不可超過 92 天，違反 → 400（reason「時間範圍不合法」，errors[].field=to，details={from,to,maxDays:92}）。不變量：同一視窗下，各專案 task-trend 各桶加總逐欄等於本端點（契約 §1.3.8）
         */
        get: operations["taskTotals"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/monitor/projects/{projectId}/token-trend": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Token 使用趨勢（含預算線）
         * @description 依 bucket 分桶（預設：視窗 ≤ 48 小時用 HOUR，否則 DAY）；資料來源 console.run_token_samples（由 Bridge token 事件寫入）。沒有資料的桶不補零（前端自行補）。budget 為該桶所屬批次的 tokenBudget（多批次時取桶內最新批次；無預算為 null）
         */
        get: operations["tokenTrend"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/monitor/projects/{projectId}/task-trend": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 任務執行趨勢（依步驟事件分桶）
         * @description 資料來源 console.execution_steps（STARTED／COMPLETED／FAILED／RETRYING 各自計數）。成功／失敗比率由 completed 與 failed 推得。只回 List<TaskTrendPoint>（PRD §7.1.6），不含事件清單：事件時間軸改用 GET /api/v1/executions/{runId}/steps（主控裁決）
         */
        get: operations["taskTrend"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/monitor/projects/{projectId}/report": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 匯出監控報表（CSV／PDF）
         * @description 不包 ApiResult 封包，直接回檔案並帶 Content-Disposition: attachment；後端以 format 為準、不因 Accept 不符回 406（CSV 送 text/csv、PDF 送 application/pdf，皆可用 *\/*）。CSV：UTF-8 含 BOM、CRLF、RFC 4180 引號；多個區段以 #section,<名稱> 行分隔（summary／runs／tasks／alerts），格式見 Markdown 契約 §1.3.7。PDF（v1.2，C-4）：與 CSV 相同的四個區段，另加標題（專案名稱＋「監控報表」）、時間範圍、範圍與產生時間（UTC）；null 顯示「—」、純文字（不做 CSV 注入引號）；內嵌 CJK 字型，字型沒有的字元以 ? 取代
         */
        get: operations["report"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/monitor/projects/{projectId}/metrics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 查詢專案指標（PRD 八項 KPI＋設計稿所需欄位）
         * @description 百分比一律 0～100 並四捨五入到小數 1 位；平均值四捨五入到小數 2 位。previousValue／delta 是與「緊鄰前一個等長視窗」的比較，無法計算時為 null（UI 顯示「—」）。公式見 Markdown 契約 §3.8。預設視窗：to＝現在、from＝to−24h
         */
        get: operations["metrics_1"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/monitor/projects/{projectId}/logs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 查詢結構化日誌
         * @description 日誌由 execution_steps、批次生命週期（execution_runs）、alerts、review_requests 衍生，不含引擎原始 stdout（原始行只在 SSE log 事件，來源 ENGINE）。等級對映：FAILED／CRITICAL→ERROR；RETRYING／WARNING／CANCELLED→WARN；其餘 INFO。預設 order=desc（新到舊）
         */
        get: operations["logs_1"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/monitor/projects/{projectId}/alerts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 查詢告警
         * @description 由新到舊；PRD 回傳 List<AlertResponse>（不分頁），以 limit（預設 50，上限 200）截斷
         */
        get: operations["alerts"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/issues": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 議題清單（唯讀；議題中心）
         * @description Bridge GET /si/issues（根層 si export --kind issues）的原樣轉遞，每筆另有 Console 自有的 priority、priorityNote（僅 rankable 為真且有順位列才有值，其餘 null）。回應含 legend（狀態、結果、來源、嚴重度的中文與說明）與 summary（整本帳的計數，不受篩選、游標影響）。status、source 是中文篩選別名（逗號取聯集、兩者取交集），原樣轉給根層判（含空字串；不認得的值＝503 si_unavailable，不是 422）。每個請求恰一次 Bridge 呼叫與一次順位表讀取（連線 2 秒、讀取 20 秒、不重試），不快取。失敗一律沒有 data：Bridge 的 503 si_unavailable→503（details.cause、details.detail 逐字）、連線失敗或 Bridge 的其他 5xx→502、讀取逾時（20 秒、不重試）→504；順位表讀取失敗→5xx。VIEWER 以上可讀。
         */
        get: operations["getIssues"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/issues/{id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 單筆議題（唯讀；議題中心）
         * @description Bridge GET /si/issues/{id} 的原樣轉遞（items 恰一筆，含 raw、timeline、links 與 priority、priorityNote；沒有 legend、summary）。id 原樣嚴格 percent-encode 成單一路徑段後交給 Bridge；格式（OBS-SI-<三位以上數字>、PROP-SI-<三位以上數字>、DEF-<數字>-<數字>）的單一真相在 Bridge：不合 → 422（details.bridgeReason=invalid_request）。格式合法而查無 → 404（reason si_not_found，訊息「查無此議題」，details.id）。不收查詢參數。失敗一律沒有 data：Bridge 的 503 si_unavailable→503（details.cause、details.detail 逐字）、連線失敗或 Bridge 的其他 5xx→502、讀取逾時（20 秒、不重試）→504；順位表讀取失敗→5xx。VIEWER 以上可讀。
         */
        get: operations["getIssue"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/import": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 查詢匯入歷史（分頁）
         * @description 列表不含 sourceContent、parsedResult（用 GET /api/v1/import/{id} 取詳情）。預設依 createdAt 由新到舊
         */
        get: operations["list_4"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/import/{id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 查詢匯入記錄詳情（補充端點）
         * @description 含 sourceContent 與 parsedResult；parsedResult 在第一次成功解析前為 null
         */
        get: operations["get_3"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/executions/{runId}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 查詢執行狀態
         * @description 合併 DB 列與 Bridge GET /autoclaude/runs/{id}。Bridge 不可達時仍回 200，bridge.connected=false，進度欄位退回 DB 衍生值（currentStep 缺席），不回 5xx。pendingReviews 只含 PENDING。v1.3：engineCapabilities（讀自 DB，建立時凍結）與 bridge.resources（引擎行程樹的資源取樣，值原樣來自同一次 Bridge 快照；行程不存活、Bridge 不可達或不認得該批次時缺席）
         */
        get: operations["get_4"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/executions/{runId}/steps": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 分頁查詢執行步驟（亦為 SSE 斷線的 REST 回補）
         * @description 資料列由 Bridge 寫入 execution_steps（每個 step 事件一列）。stepNumber 等於該 step 事件的 Bridge seq（與 SSE id: 同一個序號空間），所以 afterSeq 直接對 SSE 的 Last-Event-ID 整數部分。依 stepNumber 升冪；afterSeq 為嚴格大於。預設 size=50、上限 200
         */
        get: operations["steps"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/executions/{runId}/rtm": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 執行追溯覆蓋（諮詢視圖；v1.5 補充端點，G-05）
         * @description Bridge GET /autoclaude/runs/{id}/rtm 的投影：引擎 RtmWritebackPlugin 在 SDD 批次正常走完時寫的 AT／AC 覆蓋報告。諮詢視圖：AT 通過只代表評估指令與驗收 regex 皆通過，不等於規格被滿足；SCG-4 的人工審查才是真閘，所以回應恆帶 advisory:true。有無法歸屬 AC 的 AT 時 unmappedAtIds 列出它們（已計入 at.total、at.passed／failedAtIds，但不計入任何 AC），fullyCovered 恆為 false。批次存在但沒有報告（沒有啟用 SDD 治理、批次尚未結束、批次不是正常走完、工作區已清除）→ 404 rtm_not_found（details.runId）；報告壞掉 → 422 引擎拒絕此請求（details.bridgeReason=rtm_unreadable）。不輪詢、不快取：前端在批次進入終態後取一次。Bridge 逾時 2 秒／3 秒、不重試。
         */
        get: operations["getExecutionRtm"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/executions/{runId}/dag": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 查詢 DAG 圖
         * @description 節點與邊在建立批次時凍結於 execution_runs.dag；每個節點的 status 於讀取時疊加目標／任務的現況（歷史批次也是現況，見 statusAsOf）
         */
        get: operations["dag"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/executions/{runId}/checkpoints": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 查詢可用斷點列表
         * @description 由 console.checkpoints 讀取（Bridge 於每個步驟完成時自行記錄歷史快照，append-only），依建立時間舊→新。不含 stateSnapshot 本體；stepIdx／stepId 取自快照內的 step_idx／step_id（＝還原後下一個要跑的步驟）
         */
        get: operations["checkpoints"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/engines/sdd": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * AISDLC_SDD 引擎狀態（只讀；v1.4 補充端點，D-16）
         * @description Console 對 FSM 狀態的唯一消費點（監控頁「AISDLC_SDD 引擎」卡；PRD §0.3：FSM-STATE 是 Console 對 SDD 的遙測來源）。依序呼叫 Bridge 的 GET /sdd/version、GET /sdd/fsm，帶了 project 時再呼叫 GET /sdd/fsm/{project}；三者全是唯讀，console-api 不寫 SDD 目錄、不寫任何 FSM-STATE 檔（ADR-001 D22）。每個呼叫 2 秒／3 秒逾時、不重試、失敗即短路。引擎不可用也回 200（沿用「Bridge 不可達回 200」的慣例）：available=false 並以 reason 說明（bridge_unreachable／sdd_unavailable／bridge_error）；帶了 project 而找不到或讀不動時 available 仍為 true、fsm=null、reason 為 fsm_not_found／fsm_state_unreadable。reason 是回應欄位，不是 ApiError.reason。project 省略 → fsm=null（不帶 reason），由前端依 projects 選一個再帶 project 重取。FSM 狀態檔只在 SDD runtime 執行時才變動，前端 30 秒輪詢一次，不走 SSE（ADR-001 D22）。build/reports/ 被 git 忽略，乾淨 clone 沒有 FSM 狀態檔：available=true、projects=[] 是正常狀態。Bridge 清單裡讀不動的檔名（errors[]）只記日誌，不轉發。v1.5（D-115-02、D-115-14）：新增選填 projectId——帶了就讀「該專案」的 FSM（root＝專案的 executionPath；專案不存在或已軟刪除 → 404，不是 UUID → 400）；project 省略時預設取該專案的有效 FSM 專案（sddProject 有值取它，否則專案名；Backend 不淨化，值原樣交給 Bridge）。fsm 新增 phase／escalationHistory／escalationProvenance／fsmProject／recovery（皆選填，舊版 Bridge 缺鍵時補預設）；reason 新增 sdd_root_rejected（projectId 的專案根被 Bridge 拒絕：仍回 200、available=true、projects=[]、fsm=null）。
         */
        get: operations["getSddEngineStatus"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        UpdateTaskRequest: {
            name?: string;
            /** @description 給空白字串＝清除說明 */
            description?: string;
            passCriteria?: string;
            /**
             * Format: int32
             * @description 上限 20（Bridge PlaybookIn 的上限，契約 §0.8／AR-14）
             */
            maxRetries?: number;
            /** @description NFR-SEC-03；給空白字串＝清除 */
            evaluatorCommand?: string;
            /** @description 須可 Pattern.compile；給空白字串＝清除 */
            expectedOutputRegex?: string;
            /** @description 結構化通過標準（JSON 物件）；給空物件 {} ＝清除 */
            passCriteriaSpec?: {
                [key: string]: unknown;
            };
            /** Format: int32 */
            sortOrder?: number;
            /** Format: int64 */
            estimatedTokens?: number;
        };
        ApiResultTaskResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["TaskResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        TaskResponse: {
            /** Format: uuid */
            id: string;
            /** Format: uuid */
            goalId: string;
            name: string;
            description?: string;
            passCriteria: string;
            evaluatorCommand?: string;
            expectedOutputRegex?: string;
            passCriteriaSpec?: {
                [key: string]: unknown;
            };
            /** Format: int32 */
            sortOrder: number;
            /** @enum {string} */
            status: "PENDING" | "QUEUED" | "BLOCKED" | "RUNNING" | "VALIDATING" | "COMPLETED" | "FAILED" | "ESCALATED" | "PAUSED" | "SKIPPED" | "CANCELLED";
            /** Format: int64 */
            estimatedTokens?: number;
            /** Format: int64 */
            actualTokens?: number;
            /** Format: int32 */
            retryCount: number;
            /** Format: int32 */
            maxRetries: number;
            assignedAgent?: string;
            signedOff: boolean;
            signedOffBy?: string;
            /** Format: date-time */
            signedOffAt?: string;
            /** Format: date-time */
            createdAt: string;
            /** Format: date-time */
            updatedAt: string;
            /** Format: date-time */
            startedAt?: string;
            /** Format: date-time */
            completedAt?: string;
        };
        UpdateConfigRequest: {
            /** @description 一律字串；加密參數給空字串表示清除 */
            value: string;
            /** @description 加密（敏感）參數須明確帶 true，否則 409 */
            confirm?: boolean;
        };
        ApiResultConfigResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["ConfigResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        ConfigResponse: {
            /** Format: uuid */
            id: string;
            /** @enum {string} */
            category: "model" | "agent" | "execution" | "monitor" | "autoclaude" | "sdd";
            key: string;
            value: string;
            /** @enum {string} */
            valueType: "STRING" | "INTEGER" | "LONG" | "FLOAT" | "BOOLEAN" | "ENUM" | "ENCRYPTED";
            defaultValue?: string;
            description?: string;
            isEncrypted: boolean;
            hasValue: boolean;
            validationRule?: string;
            options?: string[];
            min?: number;
            max?: number;
            impactNote?: string;
            /** @enum {string} */
            effect: "ENGINE" | "CONSOLE" | "STORED_ONLY" | "UNVERIFIED";
            /** Format: date-time */
            updatedAt?: string;
            updatedBy?: string;
        };
        TokenGuardRequest: {
            /**
             * Format: int32
             * @description 達此 context 百分比觸發 /compact
             */
            compactThresholdPct: number;
            /**
             * Format: int32
             * @description 達此 context 百分比 checkpoint 收斂；必須大於 compactThresholdPct
             */
            haltThresholdPct: number;
        };
        ApiResultListConfigResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["ConfigResponse"][];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        UpdateProjectRequest: {
            name?: string;
            executionPath?: string;
            passCriteria?: string;
            /** @description 給空白字串＝清除說明 */
            description?: string;
            /** Format: int32 */
            autonomyLevel?: number;
            /**
             * @description 手動狀態轉移的目標，本版只開放 DRAFT／READY；其餘狀態由執行引擎事件驅動，要求其他值回 409
             * @enum {string}
             */
            status?: "DRAFT" | "READY" | "EXECUTING" | "COMPLETED" | "FAILED" | "ARCHIVED";
        };
        ApiResultProjectResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["ProjectResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        ProjectResponse: {
            /** Format: uuid */
            id: string;
            name: string;
            executionPath: string;
            passCriteria: string;
            description?: string;
            /** @enum {string} */
            status: "DRAFT" | "READY" | "EXECUTING" | "COMPLETED" | "FAILED" | "ARCHIVED";
            /** Format: int32 */
            autonomyLevel: number;
            signedOff: boolean;
            signedOffBy?: string;
            /** Format: date-time */
            signedOffAt?: string;
            /** Format: int32 */
            goalsCount: number;
            /** Format: int32 */
            tasksCount: number;
            /** Format: int32 */
            tasksDone: number;
            /** Format: date-time */
            createdAt: string;
            /** Format: date-time */
            updatedAt: string;
            createdBy?: string;
            /** @description v1.5：FSM 專案鍵（≤ 100 字元）；null＝「用預設」（專案名）。第一次使用時寫回標準鍵，或由 PUT /projects/{id}/sdd-binding 編輯 */
            sddProject?: string | null;
            /** @description v1.5：規格檔所在目錄（絕對路徑）；尚未用路徑 A 匯入為 null */
            sddSpecDir?: string | null;
            /** @description v1.5：規格檔（絕對路徑）；尚未用路徑 A 匯入為 null */
            sddSpecFile?: string | null;
        };
        /** @description 編輯專案的 FSM 專案鍵（v1.5，D-115-14；ADR-XPLAT-016 §7.2）。sddProject 為 null＝清除，回到「用預設」（專案名）；非 null 時去前後空白後 1～100 字元、不含控制字元。不檢查狀態檔是否存在、不呼叫 Bridge */
        SddBindingRequest: {
            /** @description FSM 專案鍵（自由輸入，由 Bridge 淨化後生效）；null＝清除，回到「用預設」（專案名）；鍵缺席 → 400 */
            sddProject: string | null;
        };
        ApiResultProjectDetailResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["ProjectDetailResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        GoalBrief: {
            /** Format: uuid */
            id: string;
            name: string;
            /** @enum {string} */
            status: "PENDING" | "IN_PROGRESS" | "COMPLETED" | "FAILED" | "SKIPPED";
            /** Format: int32 */
            sortOrder: number;
            signedOff: boolean;
            /** Format: int32 */
            taskCount: number;
            /** Format: int32 */
            completedTaskCount: number;
        };
        ProjectDetailResponse: {
            /** Format: uuid */
            id: string;
            name: string;
            executionPath: string;
            passCriteria: string;
            description?: string;
            /** @enum {string} */
            status: "DRAFT" | "READY" | "EXECUTING" | "COMPLETED" | "FAILED" | "ARCHIVED";
            /** Format: int32 */
            autonomyLevel: number;
            signedOff: boolean;
            signedOffBy?: string;
            /** Format: date-time */
            signedOffAt?: string;
            /** Format: int32 */
            goalsCount: number;
            /** Format: int32 */
            tasksCount: number;
            /** Format: int32 */
            tasksDone: number;
            /** Format: date-time */
            createdAt: string;
            /** Format: date-time */
            updatedAt: string;
            createdBy?: string;
            /** @description v1.5：FSM 專案鍵（≤ 100 字元）；null＝「用預設」（專案名） */
            sddProject?: string | null;
            /** @description v1.5：規格檔所在目錄（絕對路徑）；尚未用路徑 A 匯入為 null */
            sddSpecDir?: string | null;
            /** @description v1.5：規格檔（絕對路徑）；尚未用路徑 A 匯入為 null */
            sddSpecFile?: string | null;
            goals: components["schemas"]["GoalBrief"][];
        };
        /** @description 設定議題的優先順序（僅 ADMIN）。rank 必填、整數 1～9999（null、缺鍵、0、負數、小數、字串、布林、陣列、物件、超過 9999 一律 422，不當清除）；note 選填（缺鍵＝空字串；null 與數字 422）、至多 200 個字元（code point）、不含控制字元。要清除順位請用 DELETE */
        IssuePriorityRequest: {
            /**
             * Format: int32
             * @description 順位（1 最先；可與其他議題重複）
             */
            rank: number;
            /** @description 備註（缺鍵＝空字串） */
            note?: string;
        };
        ApiResultIssuePriority: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["IssuePriority"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        /** @description 議題的優先順序（Console 自有；一個議題最多一列） */
        IssuePriority: {
            /** @description 議題編號 */
            id: string;
            /**
             * Format: int32
             * @description 順位（1 最先）
             */
            rank: number;
            /** @description 備註（可為空字串） */
            note: string;
            /** @description 設定者（JWT 帳號） */
            setBy: string;
            /**
             * Format: date-time
             * @description 設定時間（伺服器時間，ISO-8601 帶 offset）
             */
            setAt: string;
        };
        EditParsedResultRequest: {
            parsedResult: components["schemas"]["ParsedResult"];
        };
        ParsedGoal: {
            key: string;
            name: string;
            description?: string;
            passCriteria: string;
            /**
             * Format: int32
             * @description 伺服器依陣列順序重編（0 起連續）；請求帶了也忽略
             */
            sortOrder?: number;
            dependsOn?: string[];
            tasks: components["schemas"]["ParsedTask"][];
        };
        ParsedProject: {
            name: string;
            executionPath: string;
            passCriteria: string;
            description?: string;
            /** Format: int32 */
            autonomyLevel?: number;
        };
        /** @description 三層草案樹（專案→目標→任務）；後半的 path／aiModel／… 為伺服器擁有的欄位，請求帶了也忽略 */
        ParsedResult: {
            project: components["schemas"]["ParsedProject"];
            goals: components["schemas"]["ParsedGoal"][];
            /** @enum {string} */
            path?: "SDD" | "LLM" | "DECOMPOSE";
            aiModel?: string;
            /** Format: int64 */
            tokenUsed?: number;
            reasoning?: string;
            draftIds?: string[];
            specDigest?: string;
            /** @description v1.5：路徑 A 的規格格式版本（Bridge /sdd/compile 的 spec_format_version）；伺服器擁有，只供顯示與稽核 */
            specFormatVersion?: string;
            /** @description v1.5：路徑 A 通過凍結閘的 FSM 專案的標準鍵（Bridge 回應的 fsm_project）；伺服器擁有；confirm 據此回填專案的 sddProject */
            sddProject?: string;
            /** @description v1.5：規格檔所在目錄（絕對路徑）＝Bridge 回應 spec_path 的父目錄；伺服器擁有；confirm 據此回填專案的 sddSpecDir */
            sddSpecDir?: string;
            /** @description v1.5：路徑 A 實際採用的規格檔（絕對路徑）＝Bridge 回應的 spec_path；伺服器擁有；confirm 據此回填專案的 sddSpecFile */
            sddSpecFile?: string;
        };
        ParsedTask: {
            name: string;
            description: string;
            passCriteria: string;
            /**
             * Format: int32
             * @description 伺服器依陣列順序重編（0 起連續）；請求帶了也忽略
             */
            sortOrder?: number;
            /** Format: int64 */
            estimatedTokens?: number;
            /** @description NFR-SEC-03：含禁用字元 → 400 */
            evaluatorCommand?: string;
            /** @description 須可編譯，否則 400 */
            expectedOutputRegex?: string;
            /** @description 結構化通過標準（JSON 物件；路徑 C 會放 {source, stepId, draftId}） */
            passCriteriaSpec?: {
                [key: string]: unknown;
            };
            /** Format: int32 */
            maxRetries?: number;
        };
        ApiResultParseResultResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["ParseResultResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        GateError: {
            /** @enum {string} */
            gate: "empty_prompt" | "max_steps" | "cycle" | "prompt_too_long" | "brain_unsupported" | "brain_failed";
            detail: string;
            /** @description 例：goals[0].tasks[3].description；沒有位置的閘（brain_*）缺席 */
            location?: string;
        };
        ParseResultResponse: {
            /** Format: uuid */
            importId: string;
            /** @enum {string} */
            status: "UPLOADED" | "PARSING" | "PARSED" | "REVIEWING" | "IMPORTED" | "REJECTED";
            /** @enum {string} */
            path: "SDD" | "LLM" | "DECOMPOSE";
            parsedResult: components["schemas"]["ParsedResult"];
            /** @description parse 成功時恆為 false；editResult 後為 false（編輯撤銷 signoff） */
            signedOff: boolean;
            aiModel?: string;
            /** Format: int64 */
            tokenUsed?: number;
            reasoning?: string;
            errors: components["schemas"]["GateError"][];
            warnings: components["schemas"]["ParseWarning"][];
        };
        /** @description 非阻擋提示（例如不安全的 evaluatorCommand 被清空） */
        ParseWarning: {
            /** @description 例：evaluator_command_dropped、regex_dropped、passcriteria_placeholder；v1.5 新增 at_unmapped（規格宣告位置出現但未編成步驟的 AT；location=specDir）、frozen_digest_absent（規格凍結時沒有記錄內容摘要，無法偵測凍結後改檔；location=specDir）、state_dir_not_ignored（專案根的 build/reports/fsm/ 未被 git 忽略；Bridge 回報，location=executionPath）——皆為黃色提示、不阻擋 */
            code: string;
            detail: string;
            location?: string;
        };
        UpdateGoalRequest: {
            name?: string;
            /** @description 給空白字串＝清除說明 */
            description?: string;
            passCriteria?: string;
            /** Format: int32 */
            sortOrder?: number;
            /** @description null＝不變；空陣列＝清除全部依賴；有值＝整組取代（Kahn 防環：成環回 400，reason＝依賴成環） */
            dependsOn?: string[];
        };
        ApiResultGoalResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["GoalResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        GoalResponse: {
            /** Format: uuid */
            id: string;
            /** Format: uuid */
            projectId: string;
            name: string;
            description?: string;
            passCriteria: string;
            /** Format: int32 */
            sortOrder: number;
            /** @enum {string} */
            status: "PENDING" | "IN_PROGRESS" | "COMPLETED" | "FAILED" | "SKIPPED";
            signedOff: boolean;
            signedOffBy?: string;
            /** Format: date-time */
            signedOffAt?: string;
            /** Format: date-time */
            createdAt: string;
            /** Format: date-time */
            updatedAt: string;
        };
        ReorderRequest: {
            /** Format: uuid */
            projectId: string;
            /** @description 新的目標順序（第 0 個＝sortOrder 0） */
            orderedGoalIds: string[];
        };
        SignoffRequest: {
            approver: string;
        };
        ApiResultBackupJobAccepted: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["BackupJobAccepted"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        /** @description 手動觸發已受理：工作已排入佇列（QUEUED），由 sidecar 撿取後執行 */
        BackupJobAccepted: {
            /** @description 工作 id（UUID；伺服器產生） */
            id: string;
            /** @enum {string} */
            type: "full" | "diff" | "verify";
            /** @enum {string} */
            status: "QUEUED";
            /** @description 要求時間（UTC，ISO-8601 帶 Z） */
            requestedAt: string;
        };
        /** @description 對待決提案（或暫停的運轉）下決定。九種動詞：approve、reject、return、promote、decline-promote、rollback、unblock、resume、ack-handoff；各動詞必填與禁止的欄位見表 M-D（多帶或缺帶一律 422，一次全列）。沒有批次核准 */
        SiDecideRequest: {
            /**
             * @description 動詞
             * @enum {string}
             */
            dkind: "approve" | "reject" | "return" | "promote" | "decline-promote" | "rollback" | "unblock" | "resume" | "ack-handoff";
            /** @description 開啟決定當下看到的卡面 digest（綁定它，過期由根層 CLI 以 STALE-CARD 拒收）。approve、reject、return、promote、decline-promote、ack-handoff 必填；rollback、unblock、resume 不可帶 */
            digest?: string;
            /** @description 理由（1～500 個 code point 的單行字串，不含控制字元）。reject、decline-promote、return、rollback、resume 必填；其餘不可帶 */
            reason?: string;
            /**
             * @description 理由類別。reject、decline-promote、return 必填；其餘不可帶
             * @enum {string}
             */
            reasonClass?: "證據不足" | "風險過高" | "工件類別錯" | "已被涵蓋" | "範圍外" | "卡面不清" | "未說明";
            /** @description 晉升後式（verdict 為 NE 的晉升）的勾選；true 只准 promote，稽核 body 的 flags 因此帶 unverified_ack */
            unverifiedAck?: boolean;
        };
        ApiResultSiWriteReceipt: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["SiWriteReceipt"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        /** @description 稽核檔已落地的收據；待入帳，由主機端根層 CLI 驗簽入帳 */
        SiWriteReceipt: {
            /**
             * Format: uuid
             * @description 稽核編號（小寫正規 UUID；入帳指令的 --audit-ref）
             */
            auditRef: string;
            /** @enum {string} */
            kind: "decide" | "obs-add" | "obs-close";
            /** @description decide＝PROP 號（resume 為 RUN 號）、obs-close＝OBS 號、obs-add＝null（入帳後才知道新列號） */
            subject?: string | null;
            /** @description 稽核 body 的 time（秒精度、±HH:MM，UTC 為 +00:00） */
            time: string;
            /** @description 簽章金鑰的 sha256 前 8 碼 */
            keyId: string;
        };
        /** @description 新增觀察列（或預檢）。三個字串欄各 1～300 個 code point、UTF-8 位元組和不得超過 700（必要條件；權威是預檢與根層 CLI 的列位元組上限），且不得含豎線與控制字元（觀察列是 Markdown 九欄表） */
        SiObservationRequest: {
            /** @description 情境 */
            context: string;
            /** @description 症狀 */
            symptom: string;
            /** @description 證據座標（須含可定位座標，由根層 CLI 判） */
            evidence: string;
            /** @enum {string} */
            category: "process" | "bug" | "tooling" | "doc" | "decision";
            /** @enum {string} */
            severity: "P1" | "P2" | "P3" | "P4";
            /** @enum {string} */
            face: "守衛" | "產品" | "文件" | "流程";
            /**
             * @description face 為守衛時必填、否則不可帶
             * @enum {string}
             */
            exposure?: "a" | "b" | "c" | "無";
            /** @description 是否外部衍生（表單預設 false） */
            externalDerived: boolean;
            /** @description 被更正的觀察列（選填；是否存在由根層 CLI 判） */
            corrects?: string;
        };
        /** @description 關閉觀察列。七個終值（沒有 open）：fixed（ref＝7～40 碼小寫十六進位提交編號）、def（ref＝DEF-<n>-<n>）、merged（ref＝OBS 號）、proposed（ref＝PROP 號）、deferred／retired／decided（text＝1～120 個字元，不含豎線、控制字元與「之後再看」） */
        SiCloseRequest: {
            /**
             * @description 終值
             * @enum {string}
             */
            terminal: "fixed" | "def" | "deferred" | "retired" | "decided" | "merged" | "proposed";
            /** @description fixed、def、merged、proposed 必填（格式依終值）；其餘不可帶 */
            ref?: string;
            /** @description deferred、retired、decided 必填；其餘不可帶。與終值以全形冒號相接成處置終值 */
            text?: string;
        };
        ApiResultSiValidation: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["SiValidation"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        /** @description 觀察列預檢結果（obs-add --dry-run）：預覽列、位元組數與根層的拒收原因 */
        SiValidation: {
            ok: boolean;
            /** @description 預覽列全文（通過才有；否則空字串）；audit_ref 以等長的全零 UUID 佔位 */
            row: string;
            /**
             * Format: int64
             * @description 預覽列的 UTF-8 位元組數（等於入帳列的位元組數）
             */
            rowBytes: number;
            /**
             * Format: int64
             * @description 根層協定參數檔的列位元組上限；根層量不到時為 null
             */
            rowMaxBytes?: number | null;
            findings: components["schemas"]["SiValidationFinding"][];
        };
        SiValidationFinding: {
            code: string;
            detail: string;
        };
        TestConnectionRequest: {
            /** @description 完整的 chat-completions 端點 URL（與系統參數 model.apiUrl 同義；後端不補路徑） */
            apiUrl?: string;
            /** @description 不回顯、不寫日誌 */
            apiKey?: string;
            model?: string;
        };
        ApiResultConnectionTestResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["ConnectionTestResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        ConnectionTestResponse: {
            success: boolean;
            /** Format: int64 */
            latencyMs?: number;
            message: string;
            resolvedHost?: string;
            /** Format: int32 */
            httpStatus?: number;
        };
        ApiResultImportSettingsResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["ImportSettingsResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        ImportSettingsError: {
            category: string;
            key: string;
            reason: string;
        };
        ImportSettingsResponse: {
            /** Format: int32 */
            applied: number;
            /**
             * Format: int32
             * @description 值未變、或加密佔位值略過的筆數
             */
            skipped: number;
            errors: components["schemas"]["ImportSettingsError"][];
        };
        ExportedConfig: {
            category: string;
            key: string;
            /** @description 加密參數固定為 <encrypted> */
            value: string;
        };
        SettingsExportDocument: {
            /**
             * Format: int32
             * @description 固定為 1；匯入時 version≠1 回 400
             */
            version: number;
            /** Format: date-time */
            exportedAt: string;
            configs: components["schemas"]["ExportedConfig"][];
        };
        CreateProjectRequest: {
            name: string;
            /** @description 專案執行路徑，必須是絕對路徑（POSIX 或 Windows） */
            executionPath: string;
            passCriteria: string;
            description?: string;
            /**
             * Format: int32
             * @description 自治等級 1～10，預設 3
             */
            autonomyLevel?: number;
            /** @description true＝草案（signedOff=false，需另外 signoff）；預設 false＝手動建立（signedOff=true） */
            draft?: boolean;
        };
        CreateGoalRequest: {
            name: string;
            description?: string;
            passCriteria: string;
            /** @description 前置依賴目標 id；須為同一專案內、未刪除的目標；成環／自依賴／跨專案回 400 */
            dependsOn?: string[];
            /** @description true＝草案（signedOff=false）；預設 false＝手動建立（signedOff=true） */
            draft?: boolean;
        };
        /** @description US-E-10 的單一任務／單一目標 Token 上限（整體上限是 tokenBudget）；超過 → TOKEN_BUDGET_EXCEEDED 告警＋自動暫停 */
        ExecutionLimits: {
            /** Format: int64 */
            taskTokens?: number;
            /** Format: int64 */
            goalTokens?: number;
        };
        /** @description ALL＝全部可執行任務；SELECTED＝goalIds 的全部可執行任務 ∪ taskIds。followUpOfRunId 只出現在後續批次（follow-up run）的回應 */
        ExecutionScope: {
            /**
             * @description 請求可省略（預設 ALL）；回應一律帶
             * @enum {string}
             */
            mode?: "ALL" | "SELECTED";
            goalIds?: string[];
            taskIds?: string[];
            limits?: components["schemas"]["ExecutionLimits"];
            /** Format: uuid */
            followUpOfRunId?: string;
        };
        /** @description 全部欄位可省略（body 可為 {}）。Architecture §11.2 把三者標必填，這裡放寬並給預設（Markdown 契約 §6 D-10） */
        StartExecutionRequest: {
            /**
             * Format: int32
             * @description 預設取專案的 autonomyLevel
             */
            autonomyLevel?: number;
            /**
             * Format: int64
             * @description 預設取系統參數 execution.globalTokenBudget
             */
            tokenBudget?: number;
            scope?: components["schemas"]["ExecutionScope"];
        };
        ApiResultExecutionRunResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["ExecutionRunResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        /** @description v1.3（D-11）：該批次 spawn 時 Console 實際送進引擎的能力狀態（契約 §3.4.2 決策表）。autoMutation 對映引擎鍵 minimax.enable_kernel_brain（Brain 逐步校正：失敗步驟尚有重試次數時先由 Brain 改寫 prompt 再重試，Brain 呼叫失敗則該步驟直接升級；實務上只有 prompt 改寫，不含步驟變異）；selfEvolution：引擎沒有演化開關，有金鑰就是 ENABLED，與旗標和等級都無關（失敗型 ESCALATION 時由 Brain 產生演化「提案」，只寫引擎日誌，不套用、不重載）；沒有金鑰時，有人要求（agent.enableSelfEvolution 或等級 ≥ 7）為 UNAVAILABLE_NO_API_KEY，否則 OFF */
        EngineCapabilities: {
            /**
             * @description ENABLED＝已送進引擎且引擎會做；OFF＝沒有人要求（或有金鑰且明確送 enable_kernel_brain=false）；UNAVAILABLE_NO_API_KEY＝有人要求但 Console 沒有金鑰可送（不送 minimax.*，批次照常執行，只是沒有 Brain）
             * @enum {string}
             */
            autoMutation: "ENABLED" | "OFF" | "UNAVAILABLE_NO_API_KEY";
            /**
             * @description 同 autoMutation 的值域；有金鑰恆為 ENABLED（語意是「只產生演化提案、不套用」）
             * @enum {string}
             */
            selfEvolution: "ENABLED" | "OFF" | "UNAVAILABLE_NO_API_KEY";
        };
        ExecutionRunResponse: {
            /** Format: uuid */
            id: string;
            /** Format: uuid */
            projectId: string;
            /**
             * Format: int32
             * @description 同專案內遞增
             */
            runNumber: number;
            /** @enum {string} */
            status: "INITIALIZING" | "RUNNING" | "PAUSED" | "COMPLETED" | "FAILED" | "CANCELLED";
            /** @enum {string} */
            bridgeStatus?: "INITIALIZING" | "RUNNING" | "PAUSING" | "PAUSED" | "CANCELLING" | "COMPLETED" | "FAILED" | "CANCELLED";
            /** Format: int32 */
            autonomyLevel: number;
            scope: components["schemas"]["ExecutionScope"];
            /**
             * Format: int64
             * @description Bridge 寫入 execution_runs.total_tokens_used（console-api 只讀）
             */
            totalTokensUsed: number;
            /** Format: int64 */
            tokenBudget?: number;
            /** Format: date-time */
            startedAt: string;
            /** Format: date-time */
            completedAt?: string;
            /** @description v1.3（D-11）：該批次 spawn 時 Console 實際送進引擎的能力狀態（契約 §3.4.2 的決策表）。落庫於 execution_runs.engine_capabilities（V10），建立時凍結，resume／restore 不更新；V10 之前建立的批次缺席或為 null（不得猜測）。execute 的 201、GET /executions/{runId}、pause／resume／cancel／restore 的快照同值；批次列表不帶它 */
            engineCapabilities?: components["schemas"]["EngineCapabilities"];
            /** @description v1.5（D-115-06；契約 §1.10.6）：<b>只有 execute 的 201</b> 帶；沒有警告就缺席（維持 v1.4 的回應形狀）。sdd_governance_inactive＝範圍內有 SDD 來源任務、但本批次沒有啟用 SDD 治理（cause 見契約 §1.10.5）；sdd_frozen_digest_absent＝已啟用治理、但凍結時沒有記錄內容摘要（Bridge 回的 201 warnings 原樣轉入）。審核決定開的後續批次回 204，警告只寫日誌 */
            warnings?: components["schemas"]["ExecutionWarning"][];
        };
        /** @description execute 的 201 回應的警告項（v1.5，D-115-06）。sdd_governance_inactive：範圍內至少有一個 SDD 來源任務，但本批次沒有啟用 SDD 治理（沒有預檢、沒有 FSM 同步、step_id 維持 G<g>-T<t>、事後也不會有追溯報告）；sdd_frozen_digest_absent：已啟用 SDD 治理，但凍結時沒有記錄內容摘要，放行但無法偵測凍結後改檔（Bridge 回的 201 warnings 原樣轉入） */
        ExecutionWarning: {
            /** @description sdd_governance_inactive 或 sdd_frozen_digest_absent；日後新增的值前端要原樣顯示、不崩潰（所以文件上不是列舉） */
            code: string;
            /** @description 只有 sdd_governance_inactive 帶：不成立的資格（契約 §1.10.5 的順序）——not_bound、token_not_configured、mixed_scope、spec_mismatch、duplicate_step_id；日後新增的值前端要原樣顯示（所以文件上不是列舉） */
            cause?: string;
            /** @description 給人看的中文說明 */
            detail: string;
        };
        /** @description 核准凍結請求（v1.5，D-115-03、D-115-14）。approver 不在請求內（一律取 JWT subject）；沒有 binding 欄——Console 專案是錨，FSM 專案＝sddProject（NULL 時取專案名） */
        SddFreezeRequest: {
            /** @description 去前後空白後 1～500 字元，不含控制字元（含換行）；不靜默截斷、不替換；寫進 FSM decision_trace （console-freeze approver=<approver>; reason=<理由>）與 Console 稽核 */
            reason: string;
            /** @description 階段名；省略時 Bridge 用 Stage-<n>（n＝frozen_stages 中 kind 不是 refreeze 的條目數＋1，缺 kind 視為凍結）。階段名不要求唯一 */
            stage?: string;
            /** @description 要凍結並計摘要的規格文件，每項是相對專案 executionPath 的 POSIX 路徑（不得為絕對路徑、不得含 ..）；須含至少一份 TCS（TEST-CONTRACT-SPEC-* 或 TCS-*，由 Bridge 判定）。省略＝[sddSpecFile 換算成相對 executionPath 的路徑]（專案已有 sddSpecFile 時）；省略而專案沒有 sddSpecFile、或規格檔不在 executionPath 之下、或專案已有 sddSpecFile 而 docs 不含它 → 400（errors[0].field=docs） */
            docs?: string[];
            /** @description 選填：核准人當時看到的摘要 {<docs 內的相對路徑>: "sha256:<64 位小寫 hex>"}。有帶＝Bridge 逐一與現檔比對，不符 → 409 sdd_spec_digest_changed（details.pair=expected_vs_file）；鍵須都在 docs 內，否則 400（errors[0].field=expectedDigests）。v1.5 的畫面不送這欄，保留給 API 消費者 */
            expectedDigests?: {
                [key: string]: string;
            };
        };
        ApiResultSddFsmState: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["SddFsmState"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        /** @description FSM 階段資訊（v1.5，G-13）。name 主路徑值為 INTAKE、SPECIFICATION、HUMAN_GATE、FROZEN、IMPLEMENTATION、REVIEW、VERIFICATION、RELEASE（order 1～8）；非主路徑為 BLOCKED／TRANSIENT／OBSERVATION／UNKNOWN（order 一律 0）。前端的字典沒有的新 name 值要原樣顯示 */
        SddFsmPhase: {
            name: string;
            /** Format: int32 */
            order: number;
            /** @description 阻塞態（ESCALATION、ESCALATION_FINAL、TERMINATED、TOKEN_BUDGET_CRITICAL）為 true */
            blocking: boolean;
            /** @description 觀測態（SDD OBSERVATION_STATES）為 true */
            observation: boolean;
        };
        /** @description 單一 FSM 專案的狀態（Bridge GET /sdd/fsm/{project} 的投影；v1.4，D-16）。最外層鍵轉 camelCase，巢狀內容原樣（frozenStages[]、decisionTrace[]、humanPending.items[]、retryHistory.last、rtmCoverage 保留 FSM 檔的 snake_case 鍵），使「FSM 檔 ↔ API ↔ 畫面」可逐值比對（NFR-OBS-01）。唯讀：Console 不寫 FSM-STATE（ADR-001 D22） */
        SddFsmState: {
            project: string;
            /** @description current_state（例 INIT、HUMAN_PENDING、ESCALATION） */
            currentState?: string | null;
            /**
             * Format: int32
             * @description current_sprint
             */
            currentSprint?: number | null;
            /** @description session_id */
            sessionId?: string | null;
            /** @description updated_at（ISO-8601 字串，原樣、不轉型） */
            updatedAt?: string | null;
            /** @description frozen_stages（原樣；缺則空陣列） */
            frozenStages: {
                [key: string]: unknown;
            }[];
            /** @description decision_trace 的尾 5 筆（舊→新，原樣；每筆 {ts, from, to, reason, spec_refs, agents_consulted, trigger}） */
            decisionTrace: {
                [key: string]: unknown;
            }[];
            /** @description 檔名（FSM-STATE-<project>.yaml） */
            source: string;
            humanPending: components["schemas"]["SddHumanPending"];
            retryHistory: components["schemas"]["SddRetryHistory"];
            /** @description fsm_state.rtm_coverage：有就原樣帶出，沒有就 null。現行 FSM-STATE schema 沒有任何 RTM 覆蓋數值的鍵，所以現況恆為 null（保留位；Console 卡片不顯示它） */
            rtmCoverage?: null;
            /** @description v1.5（G-13）：由 current_state 純函式投影出的階段資訊（契約 §3.1.5）；Bridge 尚未接線或舊版缺鍵為 null；未知狀態是 UNKNOWN 物件而不是 null */
            phase?: components["schemas"]["SddFsmPhase"];
            /** @description v1.5（G-13）：escalation_history 的尾 5 筆（舊→新，原樣——保留 FSM 檔的 snake_case 鍵，例 triggered_at、trigger_reason、resolved_at、resolution、source）；缺則空陣列 */
            escalationHistory?: {
                [key: string]: unknown;
            }[];
            /** @description v1.5（D-115-16）：escalation_provenance 原樣；缺或不是映射為 null。人工恢復後不會被清除，不是現況旗標：有沒有未解的升級只能由 currentState 與 escalationHistory 末筆的 resolved_at 判斷 */
            escalationProvenance?: {
                [key: string]: unknown;
            } | null;
            /** @description v1.5：狀態檔名裡淨化後的標準鍵（FSM-STATE-<鍵>.yaml 的 <鍵>）；project 是檔內原名，兩者可能不同，不能拿 project 當鍵；舊版 Bridge 缺鍵為 null */
            fsmProject?: string | null;
            /** @description v1.5：僅 currentState 為 ESCALATION／ESCALATION_FINAL 時由 Bridge 回；其餘為 null */
            recovery?: components["schemas"]["SddRecovery"];
        };
        /** @description 待人工確認（v1.4，D-16）：entered_at 有值 → count=1、items=[該映射原樣]；否則 count=0、items=[]；若來源是 list，count＝筆數、items＝尾 5 筆原樣。count 實務上只會是 0 或 1。items 的內容原樣＝FSM 檔寫什麼就是什麼（保留 snake_case 鍵） */
        SddHumanPending: {
            /** Format: int32 */
            count: number;
            /** @description 原樣的項目（最多 5 筆） */
            items: {
                [key: string]: unknown;
            }[];
        };
        /** @description ESCALATION 的恢復指令（v1.5）：Bridge 組字的 resume-from-escalation 指令（含 <人工原因> 佔位）；Console 原樣顯示，不提供恢復動作。不含任何機密 */
        SddRecovery: {
            /** @description 建議的 resume-from-escalation --to（SPEC_DRAFTING／IMPLEMENTATION／PR_REVIEW；委派失敗＝IMPLEMENTATION） */
            target: string;
            /** @description PowerShell 形態的完整指令（含 <人工原因> 佔位） */
            powershell: string;
            /** @description bash／zsh 形態的完整指令（含 <人工原因> 佔位） */
            posix: string;
        };
        /** @description 重試歷史（v1.4，D-16）：count＝各閘 history 筆數的總和；last＝全部筆中 date 最晚者（原樣，另加 gate 欄＝所屬的重試閘名）；沒有任何一筆為 {count: 0, last: null} */
        SddRetryHistory: {
            /** Format: int32 */
            count: number;
            /** @description 最近一筆（原樣再加 gate 欄）；沒有為 null */
            last: {
                [key: string]: unknown;
            } | null;
        };
        ApiResultImportRecordResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["ImportRecordResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        ImportRecordResponse: {
            /** Format: uuid */
            id: string;
            /** @enum {string} */
            sourceType: "MARKDOWN" | "PDF" | "DOCX" | "PLAIN_TEXT";
            sourceFileName?: string;
            /** @enum {string} */
            status: "UPLOADED" | "PARSING" | "PARSED" | "REVIEWING" | "IMPORTED" | "REJECTED";
            signedOff: boolean;
            signedOffBy?: string;
            /** Format: date-time */
            signedOffAt?: string;
            /** Format: uuid */
            projectId?: string;
            /** Format: date-time */
            createdAt: string;
            aiModel?: string;
            /** Format: int64 */
            tokenUsed?: number;
            /** @enum {string} */
            parsePath?: "SDD" | "LLM" | "DECOMPOSE";
            lastParseErrors?: components["schemas"]["GateError"][];
        };
        ParseOptions: {
            /**
             * Format: int32
             * @description 預設 3；也成為落庫專案的 autonomyLevel
             * @default 3
             */
            autonomyLevel: number;
            /** @description 專案執行路徑（絕對路徑格式：POSIX、磁碟機代號或 UNC） */
            executionPath: string;
            additionalPrompt?: string;
            /** @description 明示的 SDD 規格目錄（絕對路徑）；省略則以 executionPath 探測 */
            specDir?: string;
            /** @description v1.5：要編譯的規格檔——相對 specDir 的 POSIX 路徑，或 specDir 之下的絕對路徑；須與明示的 specDir 並用，單獨帶 → 400 */
            specFile?: string;
            /** @description v1.5：FSM 專案名的有效值（可以是原名；Console 不淨化，由 Bridge 的淨化鏡像處理）；帶 targetProjectId 時取自目標專案，請求另帶不同值 → 409 sdd_binding_conflict */
            sddProject?: string;
            /**
             * Format: uuid
             * @description v1.5：併入既有專案（Console 專案是錨）；目標專案須存在且未軟刪除（否則 404）；省略＝建立新專案
             */
            targetProjectId?: string;
        };
        TextImportRequest: {
            /** @description 需求文字（支援 Markdown）；不可全為空白 */
            content: string;
            /** @description 選填的來源名稱（例：來自剪貼簿） */
            sourceFileName?: string;
            /**
             * @description PLAIN_TEXT（預設）或 MARKDOWN；PDF／DOCX 只能由 upload 產生（其他值 400）
             * @enum {string}
             */
            sourceType?: "PLAIN_TEXT" | "MARKDOWN";
        };
        CreateTaskRequest: {
            name: string;
            description?: string;
            passCriteria: string;
            /** @description NFR-SEC-03：不得含 ! ` > < ~ $ & ; 等字元或換行，命中回 400 並列出違規字元 */
            evaluatorCommand?: string;
            /** @description 須可被 Java Pattern.compile，否則回 400 */
            expectedOutputRegex?: string;
            /** @description 結構化通過標準（JSON 物件） */
            passCriteriaSpec?: {
                [key: string]: unknown;
            };
            /** Format: int64 */
            estimatedTokens?: number;
            /**
             * Format: int32
             * @description 預設 3；上限 20（Bridge PlaybookIn 的上限，契約 §0.8／AR-14）
             */
            maxRetries?: number;
            /** @description true＝草案（signedOff=false）；預設 false＝手動建立（signedOff=true） */
            draft?: boolean;
        };
        ReviewRequest: {
            /** @enum {string} */
            decision: "APPROVE" | "REJECT" | "RETRY" | "SKIP";
            comment?: string;
        };
        RefreshRequest: {
            refreshToken: string;
        };
        ApiResultTokenResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["TokenResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        TokenResponse: {
            accessToken: string;
            refreshToken: string;
            /** Format: int64 */
            expiresIn: number;
            role: string;
        };
        /** @description POST /api/v1/auth/logout 的請求本文（v1.4，D-19） */
        LogoutRequest: {
            /** @description 要撤銷的 refresh token（目前 session 的那一個） */
            refreshToken: string;
        };
        LoginRequest: {
            username: string;
            password: string;
        };
        ApiResultTaskDetailResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["TaskDetailResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        ExecutionStepBrief: {
            /** Format: uuid */
            id: string;
            /** Format: int32 */
            stepNumber: number;
            action: string;
            status: string;
            /** Format: int64 */
            tokensUsed?: number;
            errorMessage?: string;
            /** Format: date-time */
            timestamp?: string;
        };
        TaskDetailResponse: {
            /** Format: uuid */
            id: string;
            /** Format: uuid */
            goalId: string;
            name: string;
            description?: string;
            passCriteria: string;
            evaluatorCommand?: string;
            expectedOutputRegex?: string;
            passCriteriaSpec?: {
                [key: string]: unknown;
            };
            /** Format: int32 */
            sortOrder: number;
            /** @enum {string} */
            status: "PENDING" | "QUEUED" | "BLOCKED" | "RUNNING" | "VALIDATING" | "COMPLETED" | "FAILED" | "ESCALATED" | "PAUSED" | "SKIPPED" | "CANCELLED";
            /** Format: int64 */
            estimatedTokens?: number;
            /** Format: int64 */
            actualTokens?: number;
            /** Format: int32 */
            retryCount: number;
            /** Format: int32 */
            maxRetries: number;
            assignedAgent?: string;
            executionLog?: string;
            executionHistory: components["schemas"]["ExecutionStepBrief"][];
            signedOff: boolean;
            signedOffBy?: string;
            /** Format: date-time */
            signedOffAt?: string;
            /** Format: date-time */
            createdAt: string;
            /** Format: date-time */
            updatedAt: string;
            /** Format: date-time */
            startedAt?: string;
            /** Format: date-time */
            completedAt?: string;
        };
        ApiResultBackupOverviewResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: {
                [key: string]: unknown;
            };
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        ApiResultBackupJobPage: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["BackupJobPage"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        /** @description Console 發起的備份工作（手動觸發；排程工作不在此表） */
        BackupJob: {
            /** @description 工作 id（UUID） */
            id: string;
            /** @enum {string} */
            type: "full" | "diff" | "verify";
            /** @enum {string} */
            status: "QUEUED" | "RUNNING" | "SUCCEEDED" | "FAILED" | "REJECTED" | "EXPIRED";
            /** @description 要求時間（UTC，ISO-8601 帶 Z） */
            requestedAt: string;
            /** @description runner 撿起請求的時間；尚未開始為 null */
            startedAt?: string | null;
            /** @description 終態時間；進行中為 null */
            finishedAt?: string | null;
            /**
             * Format: int32
             * @description 耗時（秒）
             */
            durationSeconds?: number | null;
            /**
             * Format: int32
             * @description 工作腳本的結束碼；被拒、逾時、中斷者為 null
             */
            exitCode?: number | null;
            /** @description 封閉詞彙（契約〈backup 類 reason 表〉的工作理由）；成功為 null */
            reason?: string | null;
            /** @description 觸發者；僅 ADMIN */
            requestedBy?: string | null;
            /** @description 已遮罩的輸出尾段（≤2000 字元）；僅 ADMIN */
            detail?: string | null;
        };
        /** @description 工作紀錄的一頁（新到舊）；nextBefore 是續取游標（尚有更多時為本頁最後一筆的 requestedAt，否則 null） */
        BackupJobPage: {
            items: components["schemas"]["BackupJob"][];
            /** @description 續取游標：下一頁以 before=<nextBefore> 請求（嚴格小於） */
            nextBefore?: string | null;
        };
        ApiResultBackupJob: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["BackupJob"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        ApiResultPendingSignoffsResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["PendingSignoffsResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        /** @description 四種草案各自的待簽核數與總和（v1.4，D-18）。total 恆等於 GET /notifications/summary 的 pendingSignoffs（同一組述詞、同一判準；limit 不影響本物件） */
        PendingSignoffCounts: {
            /** Format: int32 */
            projects: number;
            /** Format: int32 */
            goals: number;
            /** Format: int32 */
            tasks: number;
            /** Format: int32 */
            imports: number;
            /**
             * Format: int32
             * @description 四者之和
             */
            total: number;
        };
        /** @description 待簽核草案清單的一筆（v1.4，D-18）。id 也是對應 signoff 端點的路徑參數（/projects｜goals｜tasks/{id}/signoff、/import/{id}/signoff）。IMPORT 項的 projectId／projectName／parentId 為 null（匯入記錄在 confirm 之前還沒有專案） */
        PendingSignoffItem: {
            /** @enum {string} */
            kind: "PROJECT" | "GOAL" | "TASK" | "IMPORT";
            /** Format: uuid */
            id: string;
            /**
             * Format: uuid
             * @description 所屬專案；PROJECT 項＝自己的 id；IMPORT 項為 null
             */
            projectId: string | null;
            /** @description 所屬專案名稱；IMPORT 項為 null */
            projectName: string | null;
            /**
             * Format: uuid
             * @description PROJECT＝null；GOAL＝專案 id；TASK＝目標 id；IMPORT＝null
             */
            parentId: string | null;
            /** @description PROJECT／GOAL／TASK＝name；IMPORT＝source_file_name，沒有檔名（貼上文字）時為「貼上文字」 */
            title: string;
            /**
             * Format: date-time
             * @description 該列的 created_at（UTC）；清單依它升冪排序（同值以 id）
             */
            createdAt: string;
        };
        /** @description GET /api/v1/signoffs/pending 的 data（v1.4，D-18；Markdown 契約 §1.8.1） */
        PendingSignoffsResponse: {
            counts: components["schemas"]["PendingSignoffCounts"];
            /** @description 依 createdAt 升冪；最多 limit 筆（預設 50、上限 200） */
            items: components["schemas"]["PendingSignoffItem"][];
        };
        ApiResultSiExportResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: {
                [key: string]: unknown;
            };
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        ApiResultSiConsoleWrites: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["SiConsoleWrites"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        SiConsoleWriteItem: {
            /** Format: uuid */
            auditRef: string;
            /** @enum {string} */
            kind: "decide" | "obs-add" | "obs-close";
            user: string;
            role: string;
            /**
             * Format: date-time
             * @description 稽核 body 的 time（同一瞬間；以 UTC 表示）
             */
            time: string;
            /** @description decide＝PROP 號（resume 為 RUN 號）、obs-close＝OBS 號、obs-add＝入帳後回填的新列號（入帳前為 null） */
            subjectId?: string | null;
            /** @description 卡面 digest（只有六種決定動詞才有） */
            digest?: string | null;
            /** @description 簽章金鑰的 sha256 前 8 碼 */
            keyId: string;
            /** @description 帳本是否已有同 auditRef 的 dec／obs.add／obs.close 事件或觀察列標記；量不到時為 null */
            ingested?: boolean | null;
        };
        SiConsoleWriteOrphan: {
            auditRef: string;
            /** @enum {string} */
            kind: "decide" | "obs-add" | "obs-close";
            /** @description dec 的 prop（resume 為 run）、觀察列的 id、obs.close 的 obs */
            subject?: string | null;
        };
        /** @description Console 稽核列與 SelfImproving 帳本的對帳結果 */
        SiConsoleWrites: {
            /** @description 稽核列（時間新到舊、同刻依 auditRef 升冪） */
            items: components["schemas"]["SiConsoleWriteItem"][];
            /** @description 表內還有更舊的列（以 limit 取回更多） */
            truncated: boolean;
            /** @description 帳本中 carrier 為 console、Console 表內卻沒有對應列的項（紅色警示來源）；量不到時為 null */
            orphans?: components["schemas"]["SiConsoleWriteOrphan"][] | null;
            reconcile: components["schemas"]["SiReconcile"];
        };
        SiReconcile: {
            /** @enum {string} */
            status: "ok" | "NOT-EVALUABLE";
            /**
             * @description 量不到的原因；ok 時為 null
             * @enum {string|null}
             */
            reason?: "si_unavailable" | "bridge_unreachable" | "bridge_timeout" | "scan_cap_exceeded" | null;
            /**
             * Format: int32
             * @description 本次回填 subject_id 的筆數（量不到時為 0）
             */
            backfilled: number;
        };
        ApiResultMapStringListConfigResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: {
                [key: string]: components["schemas"]["ConfigResponse"][];
            };
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        ApiResultPageDataConfigHistoryResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["PageDataConfigHistoryResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        ConfigHistoryResponse: {
            /** Format: uuid */
            id: string;
            /** Format: uuid */
            configId: string;
            category: string;
            key: string;
            oldValue?: string;
            newValue: string;
            /** Format: date-time */
            changedAt: string;
            changedBy?: string;
        };
        PageDataConfigHistoryResponse: {
            content: components["schemas"]["ConfigHistoryResponse"][];
            /** Format: int32 */
            page: number;
            /** Format: int32 */
            size: number;
            /** Format: int64 */
            totalElements: number;
            /** Format: int32 */
            totalPages: number;
        };
        ApiResultPageDataProjectSummaryResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["PageDataProjectSummaryResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        PageDataProjectSummaryResponse: {
            content: components["schemas"]["ProjectSummaryResponse"][];
            /** Format: int32 */
            page: number;
            /** Format: int32 */
            size: number;
            /** Format: int64 */
            totalElements: number;
            /** Format: int32 */
            totalPages: number;
        };
        ProjectSummaryResponse: {
            /** Format: uuid */
            id: string;
            name: string;
            executionPath: string;
            /** @enum {string} */
            status: "DRAFT" | "READY" | "EXECUTING" | "COMPLETED" | "FAILED" | "ARCHIVED";
            /** Format: int32 */
            autonomyLevel: number;
            signedOff: boolean;
            /** Format: int32 */
            goalsCount: number;
            /** Format: int32 */
            tasksCount: number;
            /** Format: int32 */
            tasksDone: number;
            /** Format: date-time */
            updatedAt: string;
            /**
             * Format: date-time
             * @description 軟刪除當下的時間；只有 GET /projects?deleted=true 的列表帶值（v1.2，C-3）
             */
            deletedAt?: string;
        };
        ApiResultListGoalSummaryResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["GoalSummaryResponse"][];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        GoalSummaryResponse: {
            /** Format: uuid */
            id: string;
            /** Format: uuid */
            projectId: string;
            name: string;
            /** Format: int32 */
            sortOrder: number;
            /** @enum {string} */
            status: "PENDING" | "IN_PROGRESS" | "COMPLETED" | "FAILED" | "SKIPPED";
            signedOff: boolean;
            /** Format: int32 */
            taskCount: number;
            /** Format: int32 */
            completedTaskCount: number;
            /** Format: double */
            completionRatio: number;
        };
        ApiResultPageDataExecutionRunSummaryResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["PageDataExecutionRunSummaryResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        /** @description 批次列表（含 US-M-06 批次比較所需欄位） */
        ExecutionRunSummaryResponse: {
            /** Format: uuid */
            id: string;
            /** Format: uuid */
            projectId: string;
            /** Format: int32 */
            runNumber: number;
            /** @enum {string} */
            status: "INITIALIZING" | "RUNNING" | "PAUSED" | "COMPLETED" | "FAILED" | "CANCELLED";
            /**
             * @description 與詳情的 bridgeStatus 同義（PAUSING／CANCELLING 在此可見），但列表不逐批呼叫 Bridge：取 console-api 記憶體內最近一則 status 事件的值，沒有就以 DB status 同名值補；status=RUNNING 又沒有記憶體值時缺席
             * @enum {string}
             */
            bridgeStatus?: "INITIALIZING" | "RUNNING" | "PAUSING" | "PAUSED" | "CANCELLING" | "COMPLETED" | "FAILED" | "CANCELLED";
            /** Format: int32 */
            autonomyLevel: number;
            /** @enum {string} */
            scopeMode: "ALL" | "SELECTED";
            /** Format: int64 */
            totalTokensUsed: number;
            /** Format: int64 */
            tokenBudget?: number;
            /** Format: date-time */
            startedAt: string;
            /** Format: date-time */
            completedAt?: string;
            /**
             * Format: int64
             * @description 已完成批次＝completedAt−startedAt；進行中＝現在−startedAt
             */
            durationSec?: number;
            /**
             * Format: int32
             * @description 範圍內任務數（取自凍結的 dag）
             */
            tasksTotal: number;
            /**
             * Format: int32
             * @description 該批次內有 COMPLETED 步驟列的相異任務數
             */
            tasksCompleted: number;
            /**
             * Format: int32
             * @description 該批次內有 FAILED 步驟列的相異任務數
             */
            tasksFailed: number;
            /**
             * Format: double
             * @description tasksCompleted÷(tasksCompleted＋tasksFailed)×100（小數 1 位）；兩者皆 0 為 null
             */
            successRate?: number | null;
        };
        PageDataExecutionRunSummaryResponse: {
            content: components["schemas"]["ExecutionRunSummaryResponse"][];
            /** Format: int32 */
            page: number;
            /** Format: int32 */
            size: number;
            /** Format: int64 */
            totalElements: number;
            /** Format: int32 */
            totalPages: number;
        };
        ApiResultNotificationSummaryResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["NotificationSummaryResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        NotificationSummaryResponse: {
            /** Format: int32 */
            pendingSignoffs: number;
            /** Format: int32 */
            pendingReviews: number;
            /** Format: int32 */
            unacknowledgedAlerts: number;
            /** @description 最近一次 Bridge 健康探測的結果；尚未探測過為 null */
            bridgeConnected?: boolean | null;
            /**
             * Format: date-time
             * @description 最近一次 Bridge 健康探測的時間；尚未探測過為 null
             */
            bridgeCheckedAt?: string | null;
        };
        ApiResultTaskTotalsResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["TaskTotalsResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        TaskTotalsResponse: {
            /** Format: date-time */
            from: string;
            /** Format: date-time */
            to: string;
            /** Format: int64 */
            started: number;
            /** Format: int64 */
            completed: number;
            /** Format: int64 */
            failed: number;
            /** Format: int64 */
            retried: number;
            /** Format: int32 */
            projectsCounted: number;
        };
        ApiResultListTokenTrendPoint: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["TokenTrendPoint"][];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        TokenTrendPoint: {
            /**
             * Format: date-time
             * @description 桶起點（UTC 整點或整日）
             */
            bucketStart: string;
            /**
             * Format: int64
             * @description 該桶內 Token 增量之和
             */
            tokens: number;
            /**
             * Format: int64
             * @description 視窗起點起累計
             */
            cumulativeTokens: number;
            /**
             * Format: int64
             * @description 預算線；無預算為 null
             */
            budget?: number | null;
        };
        ApiResultListTaskTrendPoint: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["TaskTrendPoint"][];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        TaskTrendPoint: {
            /** Format: date-time */
            bucketStart: string;
            /** Format: int32 */
            started: number;
            /** Format: int32 */
            completed: number;
            /** Format: int32 */
            failed: number;
            /** Format: int32 */
            retried: number;
        };
        ApiResultProjectMetricsResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["ProjectMetricsResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        /** @description 一個 KPI 的數值與「緊鄰前一個等長視窗」的比較；無法計算者為 null（UI 顯示「—」） */
        MetricValue: {
            /** @description 百分比 0～100（小數 1 位）；平均值小數 2 位；Token 為整數 */
            value: number | null;
            previousValue?: number | null;
            /** @description value−previousValue（百分比為百分點） */
            delta?: number | null;
        };
        /** @description PRD §5.4.2 八項 KPI 全數提供，另含設計稿使用的 taskCompletionRate（卡片「完成率」）與 retryRate（卡片「重試率」），以及任務狀態分佈、執行時間分佈、重試次數分佈（ADR-001 G-13） */
        ProjectMetricsResponse: {
            /** Format: uuid */
            projectId: string;
            /** Format: uuid */
            runId?: string;
            /** Format: date-time */
            from: string;
            /** Format: date-time */
            to: string;
            /** Format: date-time */
            generatedAt: string;
            projectCompletionRate: components["schemas"]["MetricValue"];
            goalAchievementRate: components["schemas"]["MetricValue"];
            taskCompletionRate: components["schemas"]["MetricValue"];
            taskSuccessRate: components["schemas"]["MetricValue"];
            averageRetryCount: components["schemas"]["MetricValue"];
            retryRate: components["schemas"]["MetricValue"];
            totalTokens: components["schemas"]["MetricValue"];
            tokenBudgetUsageRate: components["schemas"]["MetricValue"];
            averageTaskDurationSec: components["schemas"]["MetricValue"];
            agentAvailability: components["schemas"]["MetricValue"];
            /**
             * Format: int64
             * @description 視窗內各批次 tokenBudget 之和；無預算為 null
             */
            tokenBudget?: number | null;
            /** @description 任務十一態的現況計數（key＝TaskStatus，缺的狀態為 0 且一律出現） */
            taskStatusDistribution: {
                [key: string]: number;
            };
            /** @description 視窗內完成的任務，依耗時由長到短，最多 10 筆 */
            taskDurations: components["schemas"]["TaskDurationItem"][];
            retryDistribution: components["schemas"]["RetryBucket"][];
        };
        RetryBucket: {
            /**
             * Format: int32
             * @description 重試次數（0、1、2…；≥5 併入 5）
             */
            retries: number;
            /** Format: int32 */
            tasks: number;
        };
        TaskDurationItem: {
            /** Format: uuid */
            taskId: string;
            taskName: string;
            goalName?: string;
            /**
             * Format: double
             * @description completedAt−startedAt（秒，小數 1 位）
             */
            durationSec: number;
        };
        ApiResultPageDataLogEntryResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["PageDataLogEntryResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        LogEntryResponse: {
            /** @description 穩定的衍生 id（來源表 id 加前綴，例：step:<uuid>） */
            id: string;
            /** Format: date-time */
            timestamp: string;
            /** @enum {string} */
            level: "INFO" | "WARN" | "ERROR";
            /**
             * @description STEP＝步驟事件；RUN＝批次生命週期；ALERT＝告警；REVIEW＝審核項
             * @enum {string}
             */
            source: "STEP" | "RUN" | "ALERT" | "REVIEW";
            message: string;
            /** Format: uuid */
            runId?: string;
            /** Format: uuid */
            taskId?: string;
            stepId?: string;
        };
        PageDataLogEntryResponse: {
            content: components["schemas"]["LogEntryResponse"][];
            /** Format: int32 */
            page: number;
            /** Format: int32 */
            size: number;
            /** Format: int64 */
            totalElements: number;
            /** Format: int32 */
            totalPages: number;
        };
        AlertResponse: {
            /** Format: uuid */
            id: string;
            /** Format: uuid */
            projectId: string;
            /** Format: uuid */
            runId?: string;
            /**
             * @description 前六個是 PRD §5.4.4 的規則；後兩個是引擎原生告警（ESCALATION／TOKEN_HALT）的持久化規則名
             * @enum {string}
             */
            rule: "TOKEN_BUDGET_WARNING" | "TOKEN_BUDGET_EXCEEDED" | "CONSECUTIVE_FAILURES" | "AGENT_UNRESPONSIVE" | "TASK_DURATION_EXCEEDED" | "HIGH_RETRY_RATE" | "ENGINE_ESCALATION" | "ENGINE_TOKEN_HALT";
            /** @enum {string} */
            severity: "WARNING" | "CRITICAL";
            /** @description 去重對象：run:<uuid>／task:<uuid>／goal:<uuid>／step:<step_id> */
            subject?: string;
            message: string;
            /** Format: date-time */
            createdAt: string;
            acknowledged: boolean;
            acknowledgedBy?: string;
            /** Format: date-time */
            acknowledgedAt?: string;
        };
        ApiResultListAlertResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["AlertResponse"][];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        ApiResultIssueExportResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: {
                [key: string]: unknown;
            };
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        ApiResultPageDataImportRecordResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["PageDataImportRecordResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        PageDataImportRecordResponse: {
            content: components["schemas"]["ImportRecordResponse"][];
            /** Format: int32 */
            page: number;
            /** Format: int32 */
            size: number;
            /** Format: int64 */
            totalElements: number;
            /** Format: int32 */
            totalPages: number;
        };
        ApiResultImportRecordDetailResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["ImportRecordDetailResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        ImportRecordDetailResponse: {
            /** Format: uuid */
            id: string;
            /** @enum {string} */
            sourceType: "MARKDOWN" | "PDF" | "DOCX" | "PLAIN_TEXT";
            sourceFileName?: string;
            /** @enum {string} */
            status: "UPLOADED" | "PARSING" | "PARSED" | "REVIEWING" | "IMPORTED" | "REJECTED";
            signedOff: boolean;
            signedOffBy?: string;
            /** Format: date-time */
            signedOffAt?: string;
            /** Format: uuid */
            projectId?: string;
            /** Format: date-time */
            createdAt: string;
            aiModel?: string;
            /** Format: int64 */
            tokenUsed?: number;
            /** @enum {string} */
            parsePath?: "SDD" | "LLM" | "DECOMPOSE";
            lastParseErrors?: components["schemas"]["GateError"][];
            sourceContent: string;
            /** @description 第一次成功解析前為 null；失敗的 parse 不會寫入它 */
            parsedResult?: components["schemas"]["ParsedResult"];
            /** @description 最近一次成功的 parse 或 PUT result 的黃色解析提示（與 ParseResultResponse.warnings 同形）；沒有就是 []，永遠出現（v1.2，C-10） */
            warnings: components["schemas"]["ParseWarning"][];
            /** @description 最近一次 parse 請求的選項（進入 PARSING 時寫入，不論成敗）；從未 parse 過為 null（v1.2，C-10） */
            parseOptions?: components["schemas"]["ParseOptions"];
        };
        ApiResultGoalDetailResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["GoalDetailResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        GoalDetailResponse: {
            /** Format: uuid */
            id: string;
            /** Format: uuid */
            projectId: string;
            name: string;
            description?: string;
            passCriteria: string;
            /** Format: int32 */
            sortOrder: number;
            /** @enum {string} */
            status: "PENDING" | "IN_PROGRESS" | "COMPLETED" | "FAILED" | "SKIPPED";
            dependsOn: string[];
            signedOff: boolean;
            signedOffBy?: string;
            /** Format: date-time */
            signedOffAt?: string;
            /** Format: int32 */
            taskCount: number;
            /** Format: int32 */
            completedTaskCount: number;
            /** Format: double */
            completionRatio: number;
            tasks: components["schemas"]["TaskBrief"][];
            /** Format: date-time */
            createdAt: string;
            /** Format: date-time */
            updatedAt: string;
        };
        TaskBrief: {
            /** Format: uuid */
            id: string;
            name: string;
            /** @enum {string} */
            status: "PENDING" | "QUEUED" | "BLOCKED" | "RUNNING" | "VALIDATING" | "COMPLETED" | "FAILED" | "ESCALATED" | "PAUSED" | "SKIPPED" | "CANCELLED";
            /** Format: int32 */
            sortOrder: number;
            /** Format: int32 */
            retryCount: number;
            /** Format: int32 */
            maxRetries: number;
            signedOff: boolean;
        };
        ApiResultListTaskSummaryResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["TaskSummaryResponse"][];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        TaskSummaryResponse: {
            /** Format: uuid */
            id: string;
            /** Format: uuid */
            goalId: string;
            name: string;
            /** Format: int32 */
            sortOrder: number;
            /** @enum {string} */
            status: "PENDING" | "QUEUED" | "BLOCKED" | "RUNNING" | "VALIDATING" | "COMPLETED" | "FAILED" | "ESCALATED" | "PAUSED" | "SKIPPED" | "CANCELLED";
            /** Format: int64 */
            estimatedTokens?: number;
            /** Format: int64 */
            actualTokens?: number;
            /** Format: int32 */
            retryCount: number;
            /** Format: int32 */
            maxRetries: number;
            signedOff: boolean;
            /** Format: date-time */
            updatedAt: string;
        };
        ApiResultExecutionRunDetailResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["ExecutionRunDetailResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        BridgeInfo: {
            /** @description Bridge 是否可達（網路層）；false 時進度欄位為 DB 衍生值 */
            connected: boolean;
            /** @description Bridge 實例識別（bridge_instance）；不含 pid、lock key */
            instance?: string;
            /** @enum {string} */
            status?: "INITIALIZING" | "RUNNING" | "PAUSING" | "PAUSED" | "CANCELLING" | "COMPLETED" | "FAILED" | "CANCELLED";
            /** @description Bridge 可達但回 404 run_not_found 時為 false（workspace 已清除） */
            runKnown?: boolean;
            /** Format: date-time */
            checkedAt: string;
            /** @description v1.3（D-12；US-M-10）：引擎行程樹的資源取樣（Bridge GET /autoclaude/runs/{id} 回應的 resources，規格見契約 §3.1.2）。引擎行程不存活（尚未啟動、暫停中、終態）、還沒有第一筆樣本、最近一筆樣本已超過 15 秒、Bridge 不可達（connected=false）、runKnown=false，或 Bridge 的回應沒有這個鍵（舊版 Bridge）時為 null 或缺席。只有 GET /executions/{runId}（ExecutionRunDetailResponse.bridge）帶 bridge 物件；pause／resume／cancel／restore 的快照沒有 */
            resources?: components["schemas"]["ResourceUsage"];
        };
        CurrentStep: {
            /** @description playbook step_id（例：G1-T2） */
            stepId: string;
            /**
             * Format: int32
             * @description 該步驟在 playbook 內的位置（1 起算，Bridge 的 current_step_number）；與 ExecutionStepResponse.stepNumber（事件 seq）不同義，見 Markdown 契約 §0.6
             */
            stepNumber: number;
            /** Format: uuid */
            taskId?: string;
            taskName: string;
            /** Format: uuid */
            goalId?: string;
            /**
             * Format: int32
             * @description 第幾次嘗試（1＝首次；RETRYING 為 2 起）
             */
            attempt: number;
        };
        /** @description ExecutionRunResponse ＋ 進度、待審核項與 Bridge 連線資訊 */
        ExecutionRunDetailResponse: {
            /** Format: uuid */
            id: string;
            /** Format: uuid */
            projectId: string;
            /**
             * Format: int32
             * @description 同專案內遞增
             */
            runNumber: number;
            /** @enum {string} */
            status: "INITIALIZING" | "RUNNING" | "PAUSED" | "COMPLETED" | "FAILED" | "CANCELLED";
            /** @enum {string} */
            bridgeStatus?: "INITIALIZING" | "RUNNING" | "PAUSING" | "PAUSED" | "CANCELLING" | "COMPLETED" | "FAILED" | "CANCELLED";
            /** Format: int32 */
            autonomyLevel: number;
            scope: components["schemas"]["ExecutionScope"];
            /**
             * Format: int64
             * @description Bridge 寫入 execution_runs.total_tokens_used（console-api 只讀）
             */
            totalTokensUsed: number;
            /** Format: int64 */
            tokenBudget?: number;
            /** Format: date-time */
            startedAt: string;
            /** Format: date-time */
            completedAt?: string;
            /** @description v1.3（D-11）：該批次 spawn 時 Console 實際送進引擎的能力狀態；同 ExecutionRunResponse.engineCapabilities（讀自 DB，建立時凍結；V10 之前建立的批次缺席或為 null） */
            engineCapabilities?: components["schemas"]["EngineCapabilities"];
            currentStep?: components["schemas"]["CurrentStep"];
            /** Format: int32 */
            completedSteps: number;
            /** Format: int32 */
            totalSteps: number;
            /**
             * Format: int32
             * @description Bridge 最後一則事件 seq；Bridge 不可達時為 DB 內最大 step_number 或 null
             */
            lastEventSeq?: number;
            /** @description Bridge 的狀態原因（例：「引擎升級（ESCALATION）：…」） */
            reason?: string;
            /**
             * Format: int64
             * @description 進行中＝現在−startedAt；終態＝completedAt−startedAt
             */
            elapsedSec?: number;
            pendingReviews: components["schemas"]["ReviewRequestResponse"][];
            bridge: components["schemas"]["BridgeInfo"];
        };
        /** @description 引擎行程樹的資源取樣（v1.3，D-12；Bridge RunStateOut.resources 的投影，規格見契約 §3.1.2）：Bridge 背景每 5 秒以 psutil 取樣一次，請求路徑只回最近一筆；不含 pid、命令列與環境變數 */
        ResourceUsage: {
            /**
             * Format: double
             * @description 整機正規化的 CPU 百分比＝行程樹各行程 cpu_percent 總和 ÷ 邏輯核心數，小數 1 位；取樣器第一筆可為 0.0
             */
            cpuPercent: number;
            /**
             * Format: int64
             * @description 行程樹各行程 RSS 的總和（bytes）
             */
            memoryBytes: number;
            /**
             * Format: int32
             * @description 取樣當下仍存活的行程數（含引擎根行程）
             */
            processCount: number;
            /**
             * Format: date-time
             * @description 取樣時間（ISO-8601 含 offset；Bridge 一律 UTC，值原樣帶出）
             */
            sampledAt: string;
        };
        /** @description 待審核／已處理的審核項；allowedDecisions 決定 UI 哪些按鈕可按 */
        ReviewRequestResponse: {
            /** Format: uuid */
            id: string;
            /** Format: uuid */
            runId: string;
            /** @enum {string} */
            kind: "TASK_CONFIRM" | "GOAL_CONFIRM" | "GOAL_COMPLETED" | "ESCALATED";
            /** @enum {string} */
            status: "PENDING" | "APPROVED" | "REJECTED" | "RETRIED" | "SKIPPED";
            /**
             * Format: uuid
             * @description 佐證步驟列 execution_steps.id（UUID，不是 playbook 的 step_id；TASK_CONFIRM／GOAL_*＝剛完成的步驟；ESCALATED＝失敗步驟；Markdown 契約 §0.6）
             */
            stepId?: string;
            /** Format: uuid */
            taskId?: string;
            /** Format: uuid */
            goalId?: string;
            taskName?: string;
            goalName?: string;
            /** @description 給人看的原因（樣板見 Markdown 契約 §3.6.2） */
            reason: string;
            /** Format: date-time */
            requestedAt: string;
            decidedBy?: string;
            /** Format: date-time */
            decidedAt?: string;
            comment?: string;
            allowedDecisions: ("APPROVE" | "REJECT" | "RETRY" | "SKIP")[];
        };
        ApiResultPageDataExecutionStepResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["PageDataExecutionStepResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        ExecutionStepResponse: {
            /** Format: uuid */
            id: string;
            /** Format: uuid */
            runId: string;
            /** Format: uuid */
            taskId: string;
            taskName?: string;
            /** Format: uuid */
            goalId?: string;
            /**
             * Format: int32
             * @description ＝該 step 事件的 Bridge seq（與 SSE id 同序號空間）；不是步驟位置，位置請以 stepId 對 dag 的 sequence（Markdown 契約 §0.6）
             */
            stepNumber: number;
            /** @description playbook step_id（取自 input.step_id） */
            stepId?: string;
            /**
             * Format: int32
             * @description 取自 input.attempt
             */
            attempt?: number;
            /** @description Bridge 寫成「<step_id>: <任務名稱>」 */
            action: string;
            /**
             * @description Bridge 實際寫入的四種步驟狀態（沒有 IN_PROGRESS）
             * @enum {string}
             */
            status: "STARTED" | "COMPLETED" | "FAILED" | "RETRYING";
            /**
             * Format: int64
             * @description Bridge 不寫此欄；COMPLETED／FAILED 列由 Console 以 token 事件歸因後回傳，其餘為 null
             */
            tokensUsed?: number | null;
            errorMessage?: string;
            output?: string;
            /** Format: date-time */
            timestamp: string;
        };
        PageDataExecutionStepResponse: {
            content: components["schemas"]["ExecutionStepResponse"][];
            /** Format: int32 */
            page: number;
            /** Format: int32 */
            size: number;
            /** Format: int64 */
            totalElements: number;
            /** Format: int32 */
            totalPages: number;
        };
        ApiResultExecutionRtmResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["ExecutionRtmResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        /** @description 執行追溯覆蓋（v1.5，G-05）。Bridge 同名欄位的投影，鍵轉 camelCase、值原樣。諮詢視圖：AT 通過不等於規格被滿足；有無法歸屬 AC 的 AT（unmappedAtIds 非空）時，它們仍計入 at.total、at.passed／failedAtIds，但不計入任何 AC，且 fullyCovered 恆為 false */
        ExecutionRtmResponse: {
            /** @description 場景；缺則空字串 */
            scenario: string;
            /** @description 編譯規格的摘要（sha256:<hex>）；缺則空字串 */
            specDigest: string;
            at: components["schemas"]["RtmAtCoverage"];
            ac: components["schemas"]["RtmAcCoverage"];
            /** @description 未通過的 AT（Bridge 已排序；沒有為空陣列；含無法歸屬者） */
            failedAtIds: string[];
            /** @description 驗收 regex 偏弱（轉譯保真度警訊）的 AT；沒有為空陣列 */
            weakRegexAtIds: string[];
            /** @description 逆向還原後無法歸屬 AC 的 AT（已排序；舊報告缺欄為空陣列）。與 POST /sdd/compile 回應的同名 unmapped_at_ids（規格宣告位置出現卻沒編成步驟）是兩個不同層的欄位，不得混用 */
            unmappedAtIds: string[];
            /** @description ac.total>0 且 AC 全數覆蓋，且 unmappedAtIds 為空（SCG-5 的機器判斷，仍是諮詢） */
            fullyCovered: boolean;
            /** @description 恆為 true（契約：const true）；前端必須標示「諮詢視圖」 */
            advisory: boolean;
        };
        /** @description AC 層的覆蓋（v1.5）。無法歸屬的 AT 不進任何 AC 桶 */
        RtmAcCoverage: {
            /** Format: int32 */
            covered: number;
            /** Format: int32 */
            total: number;
            /**
             * Format: double
             * @description 百分比（0～100，1 位小數；Bridge 原值）
             */
            pct: number;
        };
        /** @description AT 層的覆蓋（v1.5）。total、passed 含無法歸屬 AC 的 AT */
        RtmAtCoverage: {
            /** Format: int32 */
            passed: number;
            /** Format: int32 */
            total: number;
            /**
             * Format: int32
             * @description 逆向還原後無法歸屬 AC 的 AT 個數（舊報告缺欄為 0）；已計入 total，不計入任何 AC
             */
            unmapped: number;
            /**
             * Format: double
             * @description 百分比（0～100，1 位小數；Bridge 原值）
             */
            pct: number;
        };
        ApiResultDagResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["DagResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        DagEdge: {
            /** Format: uuid */
            from: string;
            /** Format: uuid */
            to: string;
            /**
             * @description DEPENDENCY＝目標前置依賴（from＝前置 → to＝依賴者）；CONTAINS＝目標包含任務
             * @enum {string}
             */
            kind: "DEPENDENCY" | "CONTAINS";
        };
        DagNode: {
            /**
             * Format: uuid
             * @description 目標或任務的 UUID
             */
            id: string;
            /** @enum {string} */
            kind: "GOAL" | "TASK";
            label: string;
            /** @description GOAL＝PENDING／IN_PROGRESS／COMPLETED／FAILED／SKIPPED；TASK＝十一態（現況疊加） */
            status: string;
            /**
             * Format: uuid
             * @description TASK 節點的所屬目標
             */
            goalId?: string;
            /** @description TASK 節點在該批次 playbook 的 step_id */
            stepId?: string;
            /**
             * Format: int32
             * @description 執行順序（GOAL＝目標序；TASK＝展平後的位置，1 起算）
             */
            sequence?: number;
        };
        DagResponse: {
            /** Format: uuid */
            runId: string;
            nodes: components["schemas"]["DagNode"][];
            edges: components["schemas"]["DagEdge"][];
            /**
             * Format: date-time
             * @description 節點 status 的取值時間（現況，不是該批次當時）
             */
            statusAsOf: string;
        };
        ApiResultListCheckpointResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["CheckpointResponse"][];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        CheckpointResponse: {
            /** Format: uuid */
            id: string;
            /** Format: uuid */
            runId: string;
            /** @description Bridge 命名「after-<step_id>」 */
            name: string;
            /** Format: date-time */
            createdAt: string;
            isAutomatic: boolean;
            /**
             * Format: int32
             * @description 還原後下一個要跑的步驟位置（0 起算；＝快照的 step_idx）
             */
            stepIdx?: number;
            /** @description 還原後下一個要跑的步驟 step_id；已跑完時為空字串 */
            stepId?: string;
            /**
             * Format: int32
             * @description 快照內已完成步驟數
             */
            completedSteps?: number;
        };
        ApiResultSddEngineStatusResponse: {
            /** Format: int32 */
            code: number;
            message: string;
            data: components["schemas"]["SddEngineStatusResponse"];
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        /** @description GET /api/v1/engines/sdd 的 data（v1.4，D-16）。引擎不可用也回 200：回報的是「引擎現在的狀態」，不是「這次呼叫成不成功」。projects 的順序＝Bridge 清單順序（專案名不分大小寫升冪）；開發機上會含 SDD 測試套件留下的 test-<數字> 專案，照列 */
        SddEngineStatusResponse: {
            /** @description Bridge 的 GET /sdd/version 與 GET /sdd/fsm 都成功為 true；任一失敗為 false */
            available: boolean;
            /**
             * @description available=true 且沒有問題時為 null。bridge_unreachable／sdd_unavailable／bridge_error 時 available=false；fsm_not_found／fsm_state_unreadable／sdd_root_rejected（v1.5：帶了 projectId，而 Bridge 對該專案的 root 回 422 sanitization_failed；projects=[]，version 保留）時 available=true、fsm=null（回應欄位的值，不是 ApiError.reason）
             * @enum {string|null}
             */
            reason: "bridge_unreachable" | "sdd_unavailable" | "bridge_error" | "fsm_not_found" | "fsm_state_unreadable" | "sdd_root_rejected" | null;
            /** @description GET /sdd/version 失敗時為 null */
            version: components["schemas"]["SddVersion"];
            /** @description available=false 時為空陣列（第三個呼叫失敗時保留前兩個呼叫已取得的值）；available=true 而為空表示 SDD 目錄存在但還沒有任何 FSM 狀態檔（正常狀態） */
            projects: components["schemas"]["SddProjectEntry"][];
            /** @description 帶了 project 且取得時有值；未帶 project、專案不存在、讀不動或引擎不可用時為 null */
            fsm: components["schemas"]["SddFsmState"];
            /**
             * Format: date-time
             * @description console-api 處理這次請求的時間（UTC）
             */
            checkedAt: string;
        };
        /** @description FSM 專案清單的一筆（v1.4，D-16）。project 就是 GET /engines/sdd?project= 吃的鍵，每一筆都點得進去 */
        SddProjectEntry: {
            /** @description 檔名 FSM-STATE-<project>.yaml 中的專案名（淨化後的標準鍵；v1.5 起值域＝Bridge 淨化鏡像 fsm_component() 的輸出域：非空、NFC、≤ 80、不含禁用字元與控制字元、不以 . 結尾，可含 CJK、空白、括號） */
            project: string;
            /** @description 檔名（FSM-STATE-<project>.yaml） */
            source: string;
            /** @description 檔內 fsm_state.current_state；缺則 null */
            currentState: string | null;
            /** @description 檔內 fsm_state.updated_at（ISO-8601 字串，原樣、不轉型）；缺則 null */
            updatedAt: string | null;
        };
        /** @description Bridge GET /sdd/version 的投影（v1.4，D-16）。root 是 Bridge 看到的目錄路徑（Docker 下是容器內路徑；開發機上是主機絕對路徑），僅供顯示，前端預設只秀 latest */
        SddVersion: {
            /** @description SDD 版本目錄名（例 AISDLC_SDD_v0.30） */
            latest: string;
            /** @description Bridge 端的目錄路徑（僅供顯示） */
            root: string;
        };
        ApiError: {
            /** Format: int32 */
            code: number;
            message: string;
            reason?: string;
            errors: components["schemas"]["FieldError"][];
            details?: {
                [key: string]: unknown;
            };
            /** Format: date-time */
            timestamp: string;
            traceId: string;
        };
        FieldError: {
            field: string;
            message: string;
            gate?: string;
            detail?: string;
            location?: string;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultTaskDetailResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UpdateTaskRequest"];
            };
        };
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultTaskResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description No Content */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    update_1: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 設定分類 */
                category: "model" | "agent" | "execution" | "monitor" | "autoclaude" | "sdd";
                key: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UpdateConfigRequest"];
            };
        };
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultConfigResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    updateTokenGuard: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TokenGuardRequest"];
            };
        };
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultListConfigResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    get_1: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultProjectDetailResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    update_2: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UpdateProjectRequest"];
            };
        };
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultProjectResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    delete_1: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description No Content */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    updateProjectSddBinding: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SddBindingRequest"];
            };
        };
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultProjectDetailResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    putIssuePriority: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 議題編號（例：PROP-SI-004） */
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["IssuePriorityRequest"];
            };
        };
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultIssuePriority"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 查無此議題（reason si_not_found，訊息「查無此議題」，details.id；先取該議題才寫入，查無＝零寫入） */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 輸入閘未通過（reason invalid_request；details.violations[{field,message}] 一次全列，errors[] 同內容；欄位 id、rank、note）或 Bridge 拒絕此請求（reason 引擎拒絕此請求；details.bridgeReason） */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務無法連線／回了非預期的錯誤（含 Bridge 的其他 4xx 與 5xx、200 但本文不是 JSON 物件） */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description si_unavailable：Bridge 的 SelfImproving 資料面不可用（details.cause 為 si_root_unset、si_script_missing、spawn_failed、timeout、stdout_too_large、nonzero_rc、bad_json、schema_rev_mismatch、bad_shape 之一；details.detail 為 rc 與 stderr 末 1,000 字元，逐字取自 Bridge）。不回空表、不回舊資料 */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務逾時（讀取 20 秒、不重試） */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    deleteIssuePriority: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 議題編號（例：PROP-SI-004） */
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description No Content */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 輸入閘未通過（reason invalid_request；details.violations 的 id 欄：id 不符議題編號格式；不碰資料庫） */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    editResult: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EditParsedResultRequest"];
            };
        };
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultParseResultResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未通過有界閘（任務 name／description 為空白字串＝empty_prompt） */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    get_2: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultGoalDetailResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    update_3: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UpdateGoalRequest"];
            };
        };
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultGoalResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    delete_2: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description No Content */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    reorder: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReorderRequest"];
            };
        };
        responses: {
            /** @description No Content */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    signoff: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SignoffRequest"];
            };
        };
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultTaskResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    retry: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultTaskResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    getBackupJobs: {
        parameters: {
            query?: {
                /** @description 頁大小（選填；整數 1～100，預設 20）；不合 → 422 invalid_request */
                limit?: number;
                /** @description 游標（選填；ISO-8601 時間）：只回 requested_at 嚴格早於它的工作；取自上一頁的 nextBefore；不合 → 422 invalid_request */
                before?: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultBackupJobPage"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 參數未通過檢查（reason invalid_request；details.violations[{field,message}]：limit 須為 1～100 的整數、before 須為 ISO-8601 時間） */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description backup_control_unavailable：控制面未設定或資料庫讀取失敗 */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    postBackupJob: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": Record<string, never>;
            };
        };
        responses: {
            /** @description Accepted */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultBackupJobAccepted"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description type 缺、非字串或不在 full／diff／verify（reason invalid_request；details.violations[{field,message}]） */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description backup_control_unavailable：控制面未設定、心跳逾 30 秒、匯出檔不可讀、資料庫讀取失敗，或寫請求檔失敗（該列已補償為 FAILED） */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    postSiDecide: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 提案 ID（例：PROP-SI-004）；resume 為運轉 ID（例：RUN-SI-001） */
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SiDecideRequest"];
            };
        };
        responses: {
            /** @description Created */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultSiWriteReceipt"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 輸入閘未通過（reason invalid_request；details.violations[{field,message}] 一次全列，errors[] 同內容）或 Bridge 拒絕此請求（reason 引擎拒絕此請求；details.bridgeReason、violations） */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務無法連線／回了非預期的錯誤：連線階段失敗與 5xx 已補償刪除稽核列；送出後連線重設與 2xx 本文無法解析的結果不明，稽核列保留、details.outcomeUnknown＝true；含 Bridge 的 403 si_write_forbidden（兩端權杖設定不一致） */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description si_write_disabled（backend 的金鑰或權杖未設：details.cause＝audit_key_unset｜bridge_token_unset；或 Bridge 的寫入面停用，details.detail 逐字）或 si_unavailable（Bridge 的稽核目錄寫入失敗等；details.cause、details.detail 逐字）。稽核列已補償刪除 */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務逾時（讀取 20 秒、不重試）：請求已送出、結果不明，稽核列保留、details.outcomeUnknown＝true */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    getSiObservations: {
        parameters: {
            query?: {
                /** @description 游標（選填；整數 ≥0）：只回「ID 的數字部分」嚴格大於它的項目；取自上一頁回應的 nextSince。不合 → 400 */
                since?: number;
                /** @description 頁大小（選填；整數 ≥1）：不合 → 400；超過根層協定參數檔的上限時，CLI 失敗而回 503 si_unavailable（cause=nonzero_rc） */
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultSiExportResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務無法連線／回了非預期的錯誤（含 Bridge 的其他 4xx 與 5xx、200 但本文不是 JSON 物件） */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description si_unavailable：Bridge 的 SelfImproving 資料面不可用（details.cause 為 si_root_unset、si_script_missing、spawn_failed、timeout、stdout_too_large、nonzero_rc、bad_json、schema_rev_mismatch、bad_shape 之一；details.detail 為 rc 與 stderr 末 1,000 字元，逐字取自 Bridge）。不回空表、不回舊資料 */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務逾時（讀取 20 秒、不重試） */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    postSiObservation: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SiObservationRequest"];
            };
        };
        responses: {
            /** @description Created */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultSiWriteReceipt"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 輸入閘未通過（reason invalid_request；details.violations[{field,message}] 一次全列，errors[] 同內容）或 Bridge 拒絕此請求（reason 引擎拒絕此請求；details.bridgeReason、violations） */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務無法連線／回了非預期的錯誤：連線階段失敗與 5xx 已補償刪除稽核列；送出後連線重設與 2xx 本文無法解析的結果不明，稽核列保留、details.outcomeUnknown＝true；含 Bridge 的 403 si_write_forbidden（兩端權杖設定不一致） */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description si_write_disabled（backend 的金鑰或權杖未設：details.cause＝audit_key_unset｜bridge_token_unset；或 Bridge 的寫入面停用，details.detail 逐字）或 si_unavailable（Bridge 的稽核目錄寫入失敗等；details.cause、details.detail 逐字）。稽核列已補償刪除 */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務逾時（讀取 20 秒、不重試）：請求已送出、結果不明，稽核列保留、details.outcomeUnknown＝true */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    postSiObservationClose: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 觀察列 ID（例：OBS-SI-005） */
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SiCloseRequest"];
            };
        };
        responses: {
            /** @description Created */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultSiWriteReceipt"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 輸入閘未通過（reason invalid_request；details.violations[{field,message}] 一次全列，errors[] 同內容）或 Bridge 拒絕此請求（reason 引擎拒絕此請求；details.bridgeReason、violations） */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務無法連線／回了非預期的錯誤：連線階段失敗與 5xx 已補償刪除稽核列；送出後連線重設與 2xx 本文無法解析的結果不明，稽核列保留、details.outcomeUnknown＝true；含 Bridge 的 403 si_write_forbidden（兩端權杖設定不一致） */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description si_write_disabled（backend 的金鑰或權杖未設：details.cause＝audit_key_unset｜bridge_token_unset；或 Bridge 的寫入面停用，details.detail 逐字）或 si_unavailable（Bridge 的稽核目錄寫入失敗等；details.cause、details.detail 逐字）。稽核列已補償刪除 */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務逾時（讀取 20 秒、不重試）：請求已送出、結果不明，稽核列保留、details.outcomeUnknown＝true */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    postSiObservationValidate: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SiObservationRequest"];
            };
        };
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultSiValidation"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 輸入閘未通過（reason invalid_request；details.violations 一次全列）或 Bridge 拒絕此請求（reason 引擎拒絕此請求） */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務無法連線／回了非預期的錯誤 */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description si_write_disabled（backend 的金鑰或權杖未設，details.cause 說明）或 si_unavailable（根層 CLI 不可用；details.cause、details.detail 逐字） */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務逾時（讀取 20 秒、不重試） */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    reset: {
        parameters: {
            query?: {
                /** @description 涉及加密參數的重置須明確帶 true */
                confirm?: boolean;
            };
            header?: never;
            path: {
                /** @description 設定分類 */
                category: "model" | "agent" | "execution" | "monitor" | "autoclaude" | "sdd";
                key: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultConfigResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    resetCategory: {
        parameters: {
            query?: {
                /** @description 涉及加密參數的重置須明確帶 true */
                confirm?: boolean;
            };
            header?: never;
            path: {
                /** @description 設定分類 */
                category: "model" | "agent" | "execution" | "monitor" | "autoclaude" | "sdd";
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultListConfigResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    testConnection: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["TestConnectionRequest"];
            };
        };
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultConnectionTestResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 目標位址未通過 SSRF／allowlist 檢查（未發出任何連線） */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    importSettings: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": {
                    /** Format: binary */
                    file: string;
                };
            };
        };
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultImportSettingsResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 設定檔超過 1MB 上限 */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 只接受 JSON 設定檔 */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    export: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SettingsExportDocument"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    list: {
        parameters: {
            query?: {
                page?: number;
                size?: number;
                /** @description 名稱模糊搜尋（不分大小寫） */
                q?: string;
                status?: "DRAFT" | "READY" | "EXECUTING" | "COMPLETED" | "FAILED" | "ARCHIVED";
                /** @description 排序：欄位[,asc|desc]，欄位可為 name／status／createdAt／updatedAt；預設 updatedAt,desc */
                sort?: string;
                /** @description true＝只列軟刪除的專案（OPERATOR 以上）；false／省略＝只列未軟刪除者 */
                deleted?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultPageDataProjectSummaryResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateProjectRequest"];
            };
        };
        responses: {
            /** @description Created */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultProjectResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    list_1: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                projectId: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultListGoalSummaryResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    create_1: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                projectId: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateGoalRequest"];
            };
        };
        responses: {
            /** @description Created */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultGoalResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    execute: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                projectId: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["StartExecutionRequest"];
            };
        };
        responses: {
            /** @description Created */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultExecutionRunResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 物化失敗（步驟 prompt 超過 20000 字元、評估指令禁用字元／不在白名單、regex 無法編譯、範圍任務數超過 500、任務 maxRetries 超過 20）或 Bridge 拒絕（reason：引擎拒絕此請求） */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務無法連線／回了非預期的錯誤（剛建的 run 列已補償刪除） */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務逾時（剛建的 run 列已補償刪除） */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    signoff_1: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SignoffRequest"];
            };
        };
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultProjectResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    freezeProjectSddSpec: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SddFreezeRequest"];
            };
        };
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultSddFsmState"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎拒絕此請求（details.bridgeReason 為 sanitization_failed／sdd_invalid_argument／fsm_state_unreadable；docs 不合法、缺檔、跑出根目錄、不含 TCS，或 approver／reason 值域不合） */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務無法連線／回了非預期的錯誤（含 403 sdd_write_forbidden＝兩端權杖設定不一致；已寫回的綁定不回滾） */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description sdd_write_disabled：backend 或 Bridge 沒有設定寫入權杖（BRIDGE_SDD_WRITE_TOKEN），SDD 寫入面停用 */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務逾時 */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    restore: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultProjectDetailResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    acknowledge: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                alertId: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description No Content */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    signoff_2: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SignoffRequest"];
            };
        };
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultImportRecordResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description Bridge 無法連線／批准草案時回了非預期的錯誤（不改任何狀態） */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務逾時 */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    reject: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultImportRecordResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    parse: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ParseOptions"];
            };
        };
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultParseResultResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未通過有界閘（reason：解析結果未通過有界閘，errors[] 帶 gate／detail／location）或 SDD 規格被拒 */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務無法連線／回了非預期的錯誤 */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務逾時 */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    confirm: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Created */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultProjectResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    upload: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": {
                    /** Format: binary */
                    file: string;
                };
            };
        };
        responses: {
            /** @description Created */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultImportRecordResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 上傳超過 10MB 上限（reason：檔案超過 10MB 上限） */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 副檔名不在 .md／.pdf／.docx（reason：只支援 .md／.pdf／.docx 檔案） */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 檔案內容與副檔名不符、非 UTF-8、PDF 已加密、檔案已損毀、無法擷取文字 */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    importText: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TextImportRequest"];
            };
        };
        responses: {
            /** @description Created */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultImportRecordResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    signoff_3: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SignoffRequest"];
            };
        };
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultGoalResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    list_2: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                goalId: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultListTaskSummaryResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    create_2: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                goalId: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateTaskRequest"];
            };
        };
        responses: {
            /** @description Created */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultTaskResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    review: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                runId: string;
                stepId: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReviewRequest"];
            };
        };
        responses: {
            /** @description 已處理（無內容） */
            204: {
                headers: {
                    /** @description 後續批次 id（僅 SKIP／無還原點的 RETRY 會出現） */
                    "X-Follow-Up-Run-Id"?: string;
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description SKIP／RETRY 開後續批次或 restore 時 Bridge 拒絕（reason：引擎拒絕此請求） */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務無法連線／回了非預期的錯誤（審核項維持 PENDING） */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務逾時（審核項維持 PENDING） */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    resume: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                runId: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultExecutionRunResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務無法連線／回了非預期的錯誤（DB 狀態不變） */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務逾時（DB 狀態不變） */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    restore_1: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                runId: string;
                checkpointId: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultExecutionRunResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description Bridge 拒絕（execution_path 重驗失敗；reason：引擎拒絕此請求） */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務無法連線／回了非預期的錯誤（DB 狀態不變） */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務逾時（DB 狀態不變） */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    pause: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                runId: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultExecutionRunResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務無法連線／回了非預期的錯誤（DB 狀態不變） */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務逾時（DB 狀態不變） */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    cancel: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                runId: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultExecutionRunResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 與目前狀態衝突（reason 說明原因） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務無法連線／回了非預期的錯誤（DB 狀態不變） */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務逾時（DB 狀態不變） */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    refresh: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RefreshRequest"];
            };
        };
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultTokenResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 帳號密碼錯誤，或 refresh token 無效／過期／已被撤銷 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    logout: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LogoutRequest"];
            };
        };
        responses: {
            /** @description No Content */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    login: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LoginRequest"];
            };
        };
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultTokenResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 帳號密碼錯誤，或 refresh token 無效／過期／已被撤銷 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    getBackupOverview: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultBackupOverviewResponse"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    getBackupJob: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 工作 id（UUID） */
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultBackupJob"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 查無此備份工作（reason backup_job_not_found，訊息「查無此備份工作」；id 不是 UUID 亦同） */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description backup_control_unavailable：控制面未設定或資料庫讀取失敗 */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    metrics: {
        parameters: {
            query?: {
                /** @description access token（與 Authorization 標頭擇一） */
                access_token?: string;
            };
            header?: {
                /** @description 最後收到的事件 id（<seq> 或 <seq>.<n>）；伺服器從其後重播 */
                "Last-Event-ID"?: string;
            };
            path: {
                runId: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description text/event-stream */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "text/event-stream": string;
                };
            };
            /** @description run 已終態且沒有可送的事件（Last-Event-ID 已 ≥ <S>.3；結束重連）；沒有本文 */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    logs: {
        parameters: {
            query?: {
                /** @description 沒有 Last-Event-ID 時，先重播最後 N 則事件再接即時（預設 200；0＝只收之後的新事件） */
                tail?: number;
                /** @description access token（與 Authorization 標頭擇一） */
                access_token?: string;
            };
            header?: {
                /** @description 最後收到的事件 id（<seq> 或 <seq>.<n>）；伺服器從其後重播 */
                "Last-Event-ID"?: string;
            };
            path: {
                runId: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description text/event-stream */
            200: {
                headers: {
                    /** @description no-cache, no-store */
                    "Cache-Control"?: string;
                    /** @description no */
                    "X-Accel-Buffering"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/event-stream": string;
                };
            };
            /** @description run 已終態且沒有可重播的事件（結束重連）；沒有本文 */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    getPendingSignoffs: {
        parameters: {
            query?: {
                /** @description 清單最多回幾筆（預設 50，範圍 1～200）；不影響 counts */
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultPendingSignoffsResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    getSiStatus: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultSiExportResponse"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務無法連線／回了非預期的錯誤（含 Bridge 的其他 4xx 與 5xx、200 但本文不是 JSON 物件） */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description si_unavailable：Bridge 的 SelfImproving 資料面不可用（details.cause 為 si_root_unset、si_script_missing、spawn_failed、timeout、stdout_too_large、nonzero_rc、bad_json、schema_rev_mismatch、bad_shape 之一；details.detail 為 rc 與 stderr 末 1,000 字元，逐字取自 Bridge）。不回空表、不回舊資料 */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務逾時（讀取 20 秒、不重試） */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    getSiRuns: {
        parameters: {
            query?: {
                /** @description 游標（選填；整數 ≥0）：只回「ID 的數字部分」嚴格大於它的項目；取自上一頁回應的 nextSince。不合 → 400 */
                since?: number;
                /** @description 頁大小（選填；整數 ≥1）：不合 → 400；超過根層協定參數檔的上限時，CLI 失敗而回 503 si_unavailable（cause=nonzero_rc） */
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultSiExportResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務無法連線／回了非預期的錯誤（含 Bridge 的其他 4xx 與 5xx、200 但本文不是 JSON 物件） */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description si_unavailable：Bridge 的 SelfImproving 資料面不可用（details.cause 為 si_root_unset、si_script_missing、spawn_failed、timeout、stdout_too_large、nonzero_rc、bad_json、schema_rev_mismatch、bad_shape 之一；details.detail 為 rc 與 stderr 末 1,000 字元，逐字取自 Bridge）。不回空表、不回舊資料 */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務逾時（讀取 20 秒、不重試） */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    getSiProposals: {
        parameters: {
            query?: {
                /** @description 游標（選填；整數 ≥0）：只回「ID 的數字部分」嚴格大於它的項目；取自上一頁回應的 nextSince。不合 → 400 */
                since?: number;
                /** @description 頁大小（選填；整數 ≥1）：不合 → 400；超過根層協定參數檔的上限時，CLI 失敗而回 503 si_unavailable（cause=nonzero_rc） */
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultSiExportResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務無法連線／回了非預期的錯誤（含 Bridge 的其他 4xx 與 5xx、200 但本文不是 JSON 物件） */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description si_unavailable：Bridge 的 SelfImproving 資料面不可用（details.cause 為 si_root_unset、si_script_missing、spawn_failed、timeout、stdout_too_large、nonzero_rc、bad_json、schema_rev_mismatch、bad_shape 之一；details.detail 為 rc 與 stderr 末 1,000 字元，逐字取自 Bridge）。不回空表、不回舊資料 */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務逾時（讀取 20 秒、不重試） */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    getSiProposal: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 提案 ID（例：PROP-SI-004） */
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultSiExportResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 查無此提案（reason si_not_found，details.id 為請求的 id；「404 的 reason 省略」慣例的例外之一）。不是「資料面壞了」——那是 503 si_unavailable */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎拒絕此請求（details.bridgeReason=invalid_request；id 不符 PROP-SI-<三位以上數字>） */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務無法連線／回了非預期的錯誤（含 Bridge 的其他 4xx 與 5xx、200 但本文不是 JSON 物件） */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description si_unavailable：Bridge 的 SelfImproving 資料面不可用（details.cause 為 si_root_unset、si_script_missing、spawn_failed、timeout、stdout_too_large、nonzero_rc、bad_json、schema_rev_mismatch、bad_shape 之一；details.detail 為 rc 與 stderr 末 1,000 字元，逐字取自 Bridge）。不回空表、不回舊資料 */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務逾時（讀取 20 秒、不重試） */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    getSiEvents: {
        parameters: {
            query?: {
                /** @description 游標（選填；整數 ≥0）：只回「ID 的數字部分」嚴格大於它的項目；取自上一頁回應的 nextSince。不合 → 400 */
                since?: number;
                /** @description 頁大小（選填；整數 ≥1）：不合 → 400；超過根層協定參數檔的上限時，CLI 失敗而回 503 si_unavailable（cause=nonzero_rc） */
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultSiExportResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務無法連線／回了非預期的錯誤（含 Bridge 的其他 4xx 與 5xx、200 但本文不是 JSON 物件） */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description si_unavailable：Bridge 的 SelfImproving 資料面不可用（details.cause 為 si_root_unset、si_script_missing、spawn_failed、timeout、stdout_too_large、nonzero_rc、bad_json、schema_rev_mismatch、bad_shape 之一；details.detail 為 rc 與 stderr 末 1,000 字元，逐字取自 Bridge）。不回空表、不回舊資料 */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務逾時（讀取 20 秒、不重試） */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    getSiConsoleWrites: {
        parameters: {
            query?: {
                /** @description 回傳的稽核列數（選填；整數 1～500，預設 100）：不合 → 400 */
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultSiConsoleWrites"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    listAll: {
        parameters: {
            query?: {
                /** @description true＝揭露加密值明文（僅 ADMIN） */
                reveal?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultMapStringListConfigResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    listCategory: {
        parameters: {
            query?: {
                /** @description true＝揭露加密值明文（僅 ADMIN） */
                reveal?: boolean;
            };
            header?: never;
            path: {
                /** @description 設定分類 */
                category: "model" | "agent" | "execution" | "monitor" | "autoclaude" | "sdd";
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultListConfigResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；已刪除專案清單需 OPERATOR 以上） */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    history: {
        parameters: {
            query?: {
                category?: string;
                /** @description 需與 category 併用（單獨給 key 回 400） */
                key?: string;
                page?: number;
                size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultPageDataConfigHistoryResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    list_3: {
        parameters: {
            query?: {
                page?: number;
                size?: number;
                status?: "INITIALIZING" | "RUNNING" | "PAUSED" | "COMPLETED" | "FAILED" | "CANCELLED";
                /** @description 欄位[,asc|desc]；欄位限 startedAt／runNumber；預設 startedAt,desc */
                sort?: string;
            };
            header?: never;
            path: {
                projectId: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultPageDataExecutionRunSummaryResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    summary: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultNotificationSummaryResponse"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    taskTotals: {
        parameters: {
            query: {
                /** @description 視窗起點（含；ISO-8601 帶 offset）；必填 */
                from: string;
                /** @description 視窗終點（不含；ISO-8601 帶 offset）；預設現在。to − from 不可超過 92 天 */
                to?: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultTaskTotalsResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    tokenTrend: {
        parameters: {
            query?: {
                /** @description 只看此執行批次（必須屬於該專案，否則 404）；省略＝專案全部批次 */
                runId?: string;
                /** @description 視窗起點（ISO-8601 帶 offset）；預設 to 之前 24 小時 */
                from?: string;
                /** @description 視窗終點（ISO-8601 帶 offset）；預設現在。from 必須早於 to，否則 400 */
                to?: string;
                /** @description 分桶粒度；預設視窗 ≤ 48 小時用 HOUR，否則 DAY */
                bucket?: "HOUR" | "DAY";
            };
            header?: never;
            path: {
                projectId: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultListTokenTrendPoint"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    taskTrend: {
        parameters: {
            query?: {
                /** @description 只看此執行批次（必須屬於該專案，否則 404）；省略＝專案全部批次 */
                runId?: string;
                /** @description 視窗起點（ISO-8601 帶 offset）；預設 to 之前 24 小時 */
                from?: string;
                /** @description 視窗終點（ISO-8601 帶 offset）；預設現在。from 必須早於 to，否則 400 */
                to?: string;
                /** @description 分桶粒度；預設視窗 ≤ 48 小時用 HOUR，否則 DAY */
                bucket?: "HOUR" | "DAY";
            };
            header?: never;
            path: {
                projectId: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultListTaskTrendPoint"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    report: {
        parameters: {
            query?: {
                format?: "csv" | "pdf";
                /** @description 只看此執行批次（必須屬於該專案，否則 404）；省略＝專案全部批次 */
                runId?: string;
                /** @description 視窗起點（ISO-8601 帶 offset）；預設 to 之前 24 小時 */
                from?: string;
                /** @description 視窗終點（ISO-8601 帶 offset）；預設現在。from 必須早於 to，否則 400 */
                to?: string;
            };
            header?: never;
            path: {
                projectId: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 報表檔案 */
            200: {
                headers: {
                    /** @description attachment; filename="monitor-report-<projectId 前 8 碼>-<yyyyMMdd-HHmm>.csv|pdf" */
                    "Content-Disposition"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/csv": string;
                    "application/pdf": string;
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    metrics_1: {
        parameters: {
            query?: {
                /** @description 只看此執行批次（必須屬於該專案，否則 404）；省略＝專案全部批次 */
                runId?: string;
                /** @description 視窗起點（ISO-8601 帶 offset）；預設 to 之前 24 小時 */
                from?: string;
                /** @description 視窗終點（ISO-8601 帶 offset）；預設現在。from 必須早於 to，否則 400 */
                to?: string;
            };
            header?: never;
            path: {
                projectId: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultProjectMetricsResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    logs_1: {
        parameters: {
            query?: {
                /** @description 只看此執行批次（必須屬於該專案，否則 404）；省略＝專案全部批次 */
                runId?: string;
                /** @description 視窗起點（ISO-8601 帶 offset）；預設 to 之前 24 小時 */
                from?: string;
                /** @description 視窗終點（ISO-8601 帶 offset）；預設現在。from 必須早於 to，否則 400 */
                to?: string;
                level?: "ALL" | "INFO" | "WARN" | "ERROR";
                taskId?: string;
                /** @description 訊息關鍵字（不分大小寫；萬用字元視為字面） */
                q?: string;
                order?: "asc" | "desc";
                page?: number;
                size?: number;
            };
            header?: never;
            path: {
                projectId: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultPageDataLogEntryResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    alerts: {
        parameters: {
            query?: {
                /** @description 只看此執行批次（必須屬於該專案，否則 404）；省略＝專案全部批次 */
                runId?: string;
                /** @description true＝只看已確認；false＝只看未確認；省略＝全部 */
                acknowledged?: boolean;
                limit?: number;
            };
            header?: never;
            path: {
                projectId: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultListAlertResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    getIssues: {
        parameters: {
            query?: {
                /** @description 狀態篩選（選填；七個狀態名或分頁名「待處理」，逗號分隔）。值以 64 字元、不以 - 起頭、不含控制字元為限，不合 → 422（引擎拒絕此請求） */
                status?: string;
                /** @description 來源篩選（選填；四個來源名，逗號分隔）。規則同 status */
                source?: string;
                /** @description 游標（選填；整數 ≥0）：只回游標嚴格大於它的項目；取自上一頁回應的 nextSince。不合 → 400（不觸及 Bridge） */
                since?: number;
                /** @description 頁大小（選填；整數 ≥1）：不合 → 400；超過根層協定參數檔的上限時，CLI 失敗而回 503 si_unavailable（cause=nonzero_rc） */
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultIssueExportResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎拒絕此請求（details.bridgeReason=invalid_request；status、source 超過 64 字元、以 - 起頭或含控制字元）。篩選值本身不認得（含空字串）不是 422，而是 503 si_unavailable（cause=nonzero_rc） */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務無法連線／回了非預期的錯誤（含 Bridge 的其他 4xx 與 5xx、200 但本文不是 JSON 物件） */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description si_unavailable：Bridge 的 SelfImproving 資料面不可用（details.cause 為 si_root_unset、si_script_missing、spawn_failed、timeout、stdout_too_large、nonzero_rc、bad_json、schema_rev_mismatch、bad_shape 之一；details.detail 為 rc 與 stderr 末 1,000 字元，逐字取自 Bridge）。不回空表、不回舊資料 */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務逾時（讀取 20 秒、不重試） */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    getIssue: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 議題編號（例：PROP-SI-004） */
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultIssueExportResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 查無此議題（reason si_not_found，訊息「查無此議題」，details.id 為請求的 id；「404 的 reason 省略」慣例的例外之一）。不是「資料面壞了」——那是 503 si_unavailable */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎拒絕此請求（details.bridgeReason=invalid_request；id 不符 OBS-SI-<三位以上數字>、PROP-SI-<三位以上數字>、DEF-<數字>-<數字>） */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務無法連線／回了非預期的錯誤（含 Bridge 的其他 4xx 與 5xx、200 但本文不是 JSON 物件） */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description si_unavailable：Bridge 的 SelfImproving 資料面不可用（details.cause 為 si_root_unset、si_script_missing、spawn_failed、timeout、stdout_too_large、nonzero_rc、bad_json、schema_rev_mismatch、bad_shape 之一；details.detail 為 rc 與 stderr 末 1,000 字元，逐字取自 Bridge）。不回空表、不回舊資料 */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務逾時（讀取 20 秒、不重試） */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    list_4: {
        parameters: {
            query?: {
                page?: number;
                size?: number;
                status?: "UPLOADED" | "PARSING" | "PARSED" | "REVIEWING" | "IMPORTED" | "REJECTED";
                /** @description 來源檔名模糊搜尋（不分大小寫；萬用字元視為字面） */
                q?: string;
                /** @description 欄位[,asc|desc]；欄位限 createdAt／status；預設 createdAt,desc */
                sort?: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultPageDataImportRecordResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    get_3: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultImportRecordDetailResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    get_4: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                runId: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultExecutionRunDetailResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    steps: {
        parameters: {
            query?: {
                page?: number;
                /** @description 每頁筆數（1～200） */
                size?: number;
                /** @description 只回傳 stepNumber（＝事件 seq）大於此值的列（嚴格大於） */
                afterSeq?: number;
            };
            header?: never;
            path: {
                runId: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultPageDataExecutionStepResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    getExecutionRtm: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                runId: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultExecutionRtmResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 批次不存在（訊息「執行批次不存在或已刪除：<id>」，無 reason），或批次存在但沒有追溯報告（reason rtm_not_found；本端點是「404 的 reason 省略」慣例的例外之一） */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 報告檔存在但壞掉（引擎拒絕此請求；details.bridgeReason=rtm_unreadable） */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務無法連線／回了非預期的錯誤 */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 引擎橋接服務逾時 */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    dag: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                runId: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultDagResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    checkpoints: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                runId: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultListCheckpointResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 資源不存在或已軟刪除 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
    getSddEngineStatus: {
        parameters: {
            query?: {
                /** @description 選填（v1.5）。帶了＝以該 Console 專案的 executionPath 為 root 讀它的 FSM；專案不存在或已軟刪除 → 404，不是 UUID → 400。省略＝v1.4 行為（讀 Bridge 預設的狀態目錄） */
                projectId?: string;
                /** @description FSM 專案名的有效值（可以是原名；v1.5 起 Console 不淨化，只驗長度與控制字元，由 Bridge 的淨化鏡像處理）；1～200 字元、不含控制字元，不合 → 400。省略 → 沒有 projectId 時 fsm=null；帶了 projectId 時取該專案的有效 FSM 專案 */
                project?: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiResultSddEngineStatusResponse"];
                };
            };
            /** @description 請求格式或欄位驗證失敗（errors 列出每個欄位的問題） */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 未登入，或 access token 無效／過期 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description projectId 找不到（專案不存在或已軟刪除；訊息「專案不存在或已刪除：<id>」，無 reason） */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
            /** @description 超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After） */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiError"];
                };
            };
        };
    };
}
