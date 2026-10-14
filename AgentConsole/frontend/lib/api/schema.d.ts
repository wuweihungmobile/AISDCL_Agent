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
         * @description 含最近一次執行日誌與執行歷史（Phase 2 歷史為空清單）
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
         * @description RUNNING 狀態的任務回 409
         */
        delete: operations["delete"];
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
        put: operations["update_1"];
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
        put: operations["update_2"];
        post?: never;
        /**
         * 刪除目標（軟刪除）
         * @description 連帶軟刪其下任務；含 RUNNING 任務回 409
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
    "/api/v1/projects": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 查詢專案列表
         * @description 分頁、名稱模糊搜尋、狀態篩選、排序；排除已軟刪除
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
        post: operations["signoff_2"];
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
         * @description refresh token 無效或過期回 401；access token 不可當 refresh token 用
         */
        post: operations["refresh"];
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
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        UpdateTaskRequest: {
            name?: string;
            /** @description 給空白字串＝清除說明 */
            description?: string;
            passCriteria?: string;
            /** Format: int32 */
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
             * @description 預設 3
             */
            maxRetries?: number;
            /** @description true＝草案（signedOff=false）；預設 false＝手動建立（signedOff=true） */
            draft?: boolean;
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
            goals: components["schemas"]["GoalBrief"][];
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
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN） */
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
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN） */
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
        };
    };
    update_1: {
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
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN） */
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
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN） */
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
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN） */
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
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN） */
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
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN） */
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
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN） */
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
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN） */
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
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN） */
            403: {
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
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN） */
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
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN） */
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
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN） */
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
            /** @description 角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN） */
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
            /** @description 帳號密碼錯誤，或 refresh token 無效／過期 */
            401: {
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
            /** @description 帳號密碼錯誤，或 refresh token 無效／過期 */
            401: {
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
