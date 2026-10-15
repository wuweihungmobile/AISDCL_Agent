# W5 修復波總覽（主控 2026-10-15；所有 W5 棒次必讀，與各棒任務書衝突時以本檔為準）

> 位置：`AgentConsole/docs/04_planning/agent_briefs/`。本檔是 W5 五棒（SA 契約 v1.2、BE、FE、INFRA、QA）共同的全貌；各棒只做自己持有面內的事，但要知道別棒在做什麼、介面在哪裡定。

## 1. 背景

- W4 獨立 QA（`docs/06_quality/QA_P3-6_E2E_Verification.md`，813 行）在「真後端＋真 Bridge＋mock claude」與「Docker 全棧經 nginx」兩種環境實跑：本機整套 Playwright 108 支全過、全棧 23 支全過；登記 10 筆缺陷（P1×1、P2×3、P3×6）與 21 筆觀察（O-01～O-21）；RTM 361 列＝`✅ 已驗證` 331、`🟡 部分` 17、`❌ 缺陷` 7、`✅ 實作+測試` 5、`⬜ 未開始` 1。
- 被驗 commit `c3250dd7`；QA 產物（報告、RTM 回填、`frontend/tests/e2e/` 的 p3～p8 真後端 specs、`support/fake_brain_bridge.py`、44 張截圖）由主控親驗後另 commit（W5 各棒開工時已在 HEAD）。
- W5 目標：10 筆缺陷全部修復；`🟡` 列中可做的做掉（主控裁決維持者除外）；契約 v1.2 一次回寫所有漂移與新端點；RTM 由 W5-QA 單線合併後只剩主控裁決列。

## 2. 棒次、持有面與順序

| 棒 | 模型 | 持有面（只准寫這些路徑） | 順序 |
|----|------|------------------------|------|
| W5-SA | Sonnet | `docs/02_architecture/API_Contract_P3-6.md`、`docs/02_architecture/openapi-p3-6.yaml`、`docs/02_architecture/ADR-001-TechStack-Lock.md`、`docs/02_architecture/Architecture.md` | 先跑（契約 v1.2 定稿後 FE 才能重產型別） |
| W5-BE | Sonnet | `backend/**`、`docs/06_quality/rtm_backfill_W5BE.md` | SA 交卷後，與 FE、INFRA 並行 |
| W5-FE | Sonnet | `frontend/**`（含 `tests/e2e/*.mock.spec.ts` 與單元測試；**不改** p3～p8／signoff／crud-flow 等真後端 spec）、`docs/06_quality/rtm_backfill_W5FE.md` | 同上 |
| W5-INFRA | Sonnet | `engine-bridge/**`、`docker/**`、`docker-compose.yml`、`docker-compose.dev.yml`、`.env.example`、`docs/06_quality/rtm_backfill_W5INFRA.md` | 同上 |
| W5-QA | Sonnet | `frontend/tests/e2e/**`（真後端 spec、移除 `test.fail`）、`docs/06_quality/**`（RTM.md 單線合併、QA 報告第二版） | 三棒皆由主控 commit 後 |

並行鐵律（根層 CLAUDE.md 鐵律七）：不寫他棒路徑；不改 `RTM.md`（走各自的 `rtm_backfill_*.md`）；不 commit／push；不派子 agent；不自架背景等待後交卷；暫存檔一律放 session 暫存目錄。同一棵工作樹有人同時在改別的目錄是正常的，`git status` 看到他棒的檔不要碰、也不要「順手還原」。

## 3. 主控裁決（契約 v1.2 條目；SA 寫入契約，BE／FE／INFRA 依此實作，QA 依此驗）

> **契約 v1.2 已定稿**（SA 交卷、主控親驗 openapi-typescript rc=0）：`API_Contract_P3-6.md` §6.5 是變更一覽（6.5.1 裁決對照、6.5.2 漂移回寫、6.5.3 SA 的判斷），本表與契約有出入時**以契約為準**。主控已接受 §6.5.3 全部判斷，特別注意：新 reason 四個（`project_executing`／`project_not_deleted`／`restore_window_expired`／`upstream_unavailable`）是英文識別字（§0.3 第 5 點）；V9 加 `projects.deleted_at`／`status_before_delete`、`goals`／`tasks.deleted_at`（既有的 `is_deleted` 不動）；PDF 四區段同 CSV；B1-1 的 `ConfigCatalog.java` `max` 要對齊 12 位規則；`ENGINE_TOKEN_HALT` 去重鍵同型缺口列為後續候選、W5 不動；E2E-13 是 QA 最低驗證矩陣。

| 編號 | 裁決 | 落點 |
|------|------|------|
| C-1 | **全域任務總計**（DEF-AC-009、契約 §4.6 G-G3、§6.3 第 9 項）：新增 `GET /api/v1/monitor/task-totals?from=<ISO-8601 含 offset，必填>&to=<選填，預設現在>`，角色 VIEWER 以上；`to-from` 超過 92 天 → 400，reason 沿用既有 `時間範圍不合法`（`errors[].field=to`、`details={from,to,maxDays:92}`；契約 v1.2 §1.3.8 定稿）。回 `data`＝`{ "from", "to", "started", "completed", "failed", "retried", "projectsCounted" }`：四個計數＝`execution_steps` 在 `[from, to)` 內 `STARTED`／`COMPLETED`／`FAILED`／`RETRYING` 列數（與 §1.3.3 `task-trend` 同一張表、同一判準，只是不分桶、跨全部**未封存且未軟刪除**的專案），`projectsCounted`＝有貢獻列的專案數。不變量：同窗口下等於各專案 `task-trend` 各桶加總（BE 以 IT 釘住）。FE 的「本週完成」改打這一支（每 60 秒 1 次），拿掉 30 個專案的扇出。RTM 新列 `API-MON-08`（QA 追加）。 | SA／BE／FE／QA |
| C-2 | **Bridge 深度探針**（DEF-AC-003）：`engine-bridge/Dockerfile` 安裝 `git`（`apt-get install -y --no-install-recommends git ca-certificates`，build 後 `RUN git --version` 冒煙）；新增 `GET /health/deep`（免認證，與 `/health` 同）：檢查 `git --version`（subprocess，逾時 5 秒）、`import autoclaude`、workspace 可寫（建立並刪除暫存檔）、DB ping（有設 DSN 時）。全部通過回 200 `{"status":"ok","checks":{"git":{"ok":true,"version":"…"},"autoclaude":{…},"workspace":{"ok":true},"db":{"ok":true|null}}}`，任一失敗回 503 `status=degraded` 並附 `reason`。compose 的 bridge healthcheck 改打 `/health/deep`；backend 探測環維持打 `/health`。RTM 新列 `BR-26`（QA 追加）。 | SA／INFRA／QA |
| C-3 | **軟刪除復原**（NFR-9.3-04）：新增 `POST /api/v1/projects/{id}/restore`（OPERATOR 以上）：復原專案與**同一次刪除連帶軟刪**的目標／任務，回 200 專案詳情；不存在或已清除 → 404；未被刪除 → 409 `project_not_deleted`；`deletedAt` 早於保留期 → 409 `restore_window_expired`。保留期屬性 `console.retention.soft-delete-days`（預設 30）。`GET /api/v1/projects?deleted=true` 只列軟刪除專案（OPERATOR 以上；VIEWER 403）。清除排程 `console.retention.purge-enabled`（預設 **false**；開啟時每日清除逾期軟刪資料），有單元測試。audit_log 記 `project.restore`。RTM 新列 `API-PRJ-06`（QA 追加）。FE：專案列表加「已刪除」篩選與「復原」按鈕（OPERATOR 以上）。 | SA／BE／FE／QA |
| C-4 | **PDF 報表**（US-M-07／API-MON-07）：`GET …/report?format=pdf` 回 200 `application/pdf`，`Content-Disposition` 與 CSV 同型（副檔名 .pdf）；內容＝與 CSV 相同的四個區段（`summary`／`runs`／`tasks`／`alerts`）加標題與產生時間（契約 v1.2 §1.3.7 定稿）。以既有相依 PDFBox 3 產生；中文需內嵌 OFL 授權的 CJK 字型（建議 Noto Sans TC 靜態 Regular，放 `backend/src/main/resources/fonts/` 並附 OFL 授權檔；下載不到時改用英文標籤並在交卷〈沒做〉寫明）。拿掉 `NotImplementedYetException` 的 501 路徑與 `PDF_NOT_AVAILABLE`。FE：報表匯出的 PDF 選項啟用。 | SA／BE／FE／QA |
| C-5 | **換新失敗語意**（DEF-AC-007、契約 §2.8）：`POST /auth/refresh` 的失敗分三類——`renewed`／`invalid`（HTTP 400／401／403）／`unavailable`（網路錯誤、5xx、429）。只有 `invalid` 清 session 並導向登入；`unavailable` 保留 session：REST 路徑丟 `ApiError{status:503, reason:"upstream_unavailable", message:"伺服器暫時無法連線，請稍後再試"}`；SSE 取 token（`getFreshAccessToken({force})`）在 `unavailable` 時若現有 token 未過期就沿用、否則回 null 且**不登出**，串流層以 1→2→4→…→30 秒退避重連並維持「重新連線中」狀態。 | SA／FE／QA |
| C-6 | **設定匯入**（DEF-AC-002、契約 §1.5.10）：項目值與現值相同者一律計 `skipped`、**不做**值規則與 allowlist 驗證（順序：`<encrypted>` 佔位 → 加密鍵給明文 errors → 值未變 skipped → 驗證 → 候選）。 | SA／BE／QA |
| C-7 | **ENGINE_ESCALATION 去重鍵**（O-14、契約 §3.7）：由 `step:<stepId>` 改為 `step:<runId>:<stepId>`，不同批次的升級不再被未確認的舊告警吞掉。 | SA／BE／QA |
| C-8 | **執行中刪除**（O-05）：專案有進行中批次（`EXECUTING`／`PAUSING`／`PAUSED`／`CANCELLING`）時，刪除其目標或任務回 409 `project_executing`；FE 顯示原因。 | SA／BE／FE／QA |
| C-9 | **手動重試**（O-04）：維持不受 `maxRetries` 限制；契約明文，FE toast 文案改「手動重試第 N 次（不計入自動重試上限 M）」。 | SA／FE |
| C-10 | **匯入記錄補欄**（F1-1／F1-2、契約 §1.1.9）：Flyway V8 在 `import_records` 加 `warnings jsonb not null default '[]'`、`parse_options jsonb null`；parse 時存入；`GET /import/{id}` 回 `warnings[]` 與 `parseOptions`；FE 重開記錄時還原黃色提示與選項。 | SA／BE／FE／QA |
| C-11 | **批次列表 bridgeStatus**（F2-4、契約 §1.2.2）：列表項加 `bridgeStatus`（與詳情同義、可 null）；FE 列表顯示 PAUSING／CANCELLING 晶片。 | SA／BE／FE／QA |
| C-12 | **traceId 貫穿 Bridge**（NFR-9.4-04、O-11）：backend 對 Bridge 的每個請求帶 `X-Trace-Id`（取當前請求的 traceId，背景消費者用 run 的 traceId 或新產）；Bridge 中介層讀取（缺則自產 uuid4）、回應回帶同名標頭、**每一行**應用日誌含 `trace_id`。 | SA／BE／INFRA／QA |
| C-13 | **KPI 環形**（UI-KPI-01／02）：PRD §5.4.2「環形」以設計稿畫面 8 的數值卡為準（ADR-001 D11 已定視覺以設計稿為準）；SA 在 ADR-001 §4 偏離清單與 §5 加 G-20 一列；QA 據此把兩列改 `✅ 已驗證`。 | SA／QA |
| C-14 | **追蹤鏈視圖**（US-M-09）：設計稿與契約皆無獨立視圖，以批次下拉＋事件時間軸＋日誌查詢涵蓋；SA 在契約 §4.3 M-12 補一句、QA 改 `✅ 已驗證` 並在 E2E 欄註明裁決。 | SA／QA |
| C-15 | **nginx**（DEF-AC-008、O-08、O-09）：`error_log` 等級降為 `crit`（檔頭誠實劃界改寫：要除錯時暫時調回 `error` 並清檔）；`location = /api/health` 導向 frontend（放在 `/api/` 之前）；靜態資源的 `Cache-Control` 只留一份。 | INFRA／QA |
| C-16 | **compose**（DEF-AC-006、INF-VOL-06、O-20）：`CONSOLE_ENCRYPTION_KEY: ${CONSOLE_ENCRYPTION_KEY:?CONSOLE_ENCRYPTION_KEY 必填，openssl rand -base64 32}`；backend 加 `LOG_DIR=/app/logs`、Bridge 加 `BRIDGE_LOG_DIR=/app/logs`（各自寫滾動檔案日誌到 app_logs 卷：BE 由 logback 在 `LOG_DIR` 有值時啟用 JSON 行 RollingFileAppender、每日切檔保留 7 天；Bridge 同義）；backend 加 `CONSOLE_INTERNAL_PROXIES`（對應 `server.tomcat.remoteip.internal-proxies`，預設只信 compose 子網）。 | INFRA／BE／QA |
| C-17 | **還原腳本**（DEF-AC-010）：`docker/pgbackrest/scripts/restore.sh` Step 1 之前 `mkdir -p "$PGDATA_DIR"` 並設擁有者與 0700；`docker/README.md` §4.3 補「全新空卷」註記與「還原後核對資料列數」必做步驟。 | INFRA／QA |
| C-18 | **無障礙**（DEF-AC-004／005）：主色 `#498428` 底上的小字改 `#ffffff`；`wg-muted` 文字色加深到白底 ≥4.5:1（QA 建議 `#6b7766`）；頂列 logo 的 aria-label 須含可見文字；Markdown 工具列 svg 加 `aria-hidden="true"`；監控頁 Agent 狀態晶片的 list 結構改正。設計系統 spec／截圖受影響者一併更新。 | FE／QA |
| C-19 | **前端規範與效能**（NFR-9.4-01、NFR-9.1-05）：加 Prettier（設定須與現行程式風格一致，`npm run format:check` 加進 `lint` 流程；只准動 `frontend/**`、不動 `tests/e2e/` 的真後端 spec）；Markdown 預覽更新去抖（`useDeferredValue`／`startTransition`），目標 20KB 文件 <100ms。 | FE／QA |
| C-20 | **文件說明**（O-06、O-16）：`docker/README.md` 寫明預設帳密必須更換、`/actuator/prometheus` 免 token 只靠網路隔離。 | INFRA |
| C-21 | **契約漂移回寫**：`W4_QA_E2E.md`〈契約漂移裁決〉的 B1-1～B1-9、F1-1～F1-6、F2-1～F2-6，加上 B2 交卷〈契約漂移〉六條（scratchpad `b2_handoff.md`）——除 F1-1／F1-2（C-10）、F2-3（C-1）、F2-4（C-11）改為「v1.2 已補」外，其餘以實作為準寫進契約正文與 §6.3。 | SA |
| C-22 | **觀察 O-15**（CONSECUTIVE_FAILURES 幾乎不可達）：契約 §3.7 補一段「觸發路徑說明」，不改規則。 | SA |

不在 W5 範圍（維持 🟡 或 ⛔，QA 不追）：`API-AUT-06`、`US-M-10`「資源使用情況」、`US-I-05` 瀏覽按鈕、`NFR-9.3-01`（長期監測）、`INF-VOL-07` HTTPS（INFRA 只提供 `https.conf.example` 與 README 段落）、`INF-DR-13` WAL 7 天本地複本清理的時間驗證、O-07 日誌主機路徑遮罩（涉及 Architecture §8.3 三處消毒 parity，另案）、O-21 mock claude 旋鈕。

## 4. 環境事實（Windows 11，主控已實證；違反會白跑）

- 只用 PowerShell 工具；不裸 `cd`（`Push-Location <絕對路徑>; …; Pop-Location` 同一呼叫）；讀 rc 不接管線（先 `*> log` 再讀 `$LASTEXITCODE`）；跑 Bash 工具會被 hook 擋。
- Node v22.23.3（硬性）、OpenJDK 21、Gradle 9.8.1、Python 3.11（根層 `.venv`，Bridge 已以 `uv pip install -e` 裝入）、Docker Desktop 29.x。
- 埠：5432 `autoclaude_pg` **不准動**；5433 被原生 postgres 佔用；自己起 PG 用 25433 或 15433（`docker run -d --rm --name <你的名字> …`，收尾 `docker stop`；`docker rm -f` 會被守衛擋）。backend 用 18080、Bridge 18081；**Bridge 先於 backend 啟動**（否則 `agentAvailability` 變 75），backend 先跑 Flyway 建 `console` schema；輪詢 ≥1 秒（e2e profile 限流每使用者每分鐘 100 次）。
- backend 跑著時 `gradlew clean build` 會失敗（jar 被鎖）；Playwright dev 模式起跑前先刪 `frontend\.next\dev`。
- 機密掃描：commit 會擋 `user:pw@host` 形態的 DSN 與 `sk-` 開頭的假 key——夾具一律用 `your_password_here`／不帶 `sk-` 前綴的佔位。
- 文件：繁體中文；測試計數寫中文（「230 支通過」），不與日期同行（基線站點鎖）；所有文字檔 LF；新 Python 一律 `encoding="utf-8"`、時間戳帶 tz、平台 API 罩 `sys.platform`。
- 鐵律 11：每做一條就編譯＋跑對應測試，不累積；失敗立即修，不跳過、不註解掉。

## 5. 交卷格式（每棒相同）

`STATUS: DONE|PARTIAL`；〈做了什麼〉（絕對路徑、每條對應 C-x／DEF-AC-x）；〈驗證證據〉（每道閘門的指令與 rc、關鍵輸出逐字，log 絕對路徑）；〈沒做／偏離〉（含原因）；〈給 QA 的提醒〉（怎麼驗、哪些 `test.fail` 可移除、RTM 哪幾列該改）；〈git --no-optional-locks status --porcelain 全文〉（標出哪些不是你的）。宣稱「已驗證／通過」必附當回合真跑的輸出。
