# AgentConsole 實作計畫（Implementation Plan）

| 項目 | 內容 |
|------|------|
| 版本 | v1.0（W1 由 Architect 建立；進度帳由主控維護） |
| 建立日期 | 2026-10-14 |
| 依據 | PRD §10（六個 Phase）、[Architecture.md](../02_architecture/Architecture.md)、[ADR-001](../02_architecture/ADR-001-TechStack-Lock.md)、[RTM.md](../06_quality/RTM.md) |
| 用法 | 每波開工前核對「入口條件」；收工時逐條跑「出口閘門」並把**逐字輸出**貼進交卷；進度帳由主控填 |

> **指令規則**：每段指令皆為 bash＋PowerShell 雙區塊；工作目錄假設在 monorepo 根；PowerShell 不用裸 `cd`、不用 `VAR=value` 前綴、不接管線讀 rc（規則見 [CLAUDE.md](../../CLAUDE.md)〈跨平台鐵律〉）。預期輸出欄刻意不寫測試筆數（筆數是量測值，由執行者貼實測）。

---

## 1. PRD Phase ↔ 本輪波次對照

| PRD Phase | PRD §10.2 交付物 | 後端 | 前端 | Bridge | Infra | QA |
|-----------|------------------|------|------|--------|-------|----|
| P1 基礎建設 | 骨架、DB Schema、認證 | W2 | W3（骨架、四區塊版面） | W1（`/health`） | W2（服務、網路、映像） | W4 |
| P2 專案控管 | 專案／目標／任務 CRUD | W2 | W3 | — | — | W4 |
| P3 匯入解析 | 匯入、AI 解析、結構預覽 | W3 | W4 | W1（decompose、sdd） | — | W4 |
| P4 專案執行 | 啟動／暫停／取消、即時日誌、審核 | W3 | W4 | W1（runs 全系列） | — | W4 |
| P5 專案監控 | KPI、趨勢圖、告警 | W3 | W4 | — | W2（Grafana 面板） | W4 |
| P6 設定與整合 | 設定頁、整合測試、效能與安全 | W3 | W4 | — | W2（備援／備份／監控） | W4、W5 |

| 波次 | 並行角色 | 範圍 | 主要產物 |
|------|----------|------|----------|
| W1 | Architect（W1-A）∥ Bridge（W1-B） | 架構文件、RTM、計畫、CLAUDE／README；Engine Bridge 全部 | `docs/`、`engine-bridge/` |
| W2 | 後端（W2-A）∥ Infra（W2-B） | backend P1＋P2；compose／docker／備援備份監控全套 | `backend/`、`docker/`、`docker-compose*.yml`、`.env.example` |
| W3 | 前端（W3-A）∥ 後端 P3～6（W3-B） | frontend P1＋P2 ＋四區塊版面；backend 匯入／執行／監控／設定 | `frontend/`、`backend/` 增補 |
| W4 | 前端 P3～6 ∥ QA | 匯入／執行／監控／設定頁；全鏈 E2E；RTM 逐列核對 | `frontend/` 增補、`docs/06_quality/` 報告 |
| W5 | 修復 | W4 缺陷、RTM 缺口、Windows 接續缺陷 | 缺陷修復、RTM 全綠 |

---

## 2. 波次、入口條件與出口閘門

### W1　架構＋Bridge（本波）

**入口條件**

- 主控的共同背景與 W1-A／W1-B 任務書就緒；PRD 與設計稿可讀。
- `AutoClaude/`、`AISDLC_SDD/`、根層 `CLAUDE.md`、`.claude/`、`tools/`、`.github/` 未被動過。

**出口閘門（Architect 部分）**

```bash
find AgentConsole -type f -not -path '*/.venv/*' -not -path '*/.ruff_cache/*' -not -path '*/__pycache__/*' | sort
wc -l AgentConsole/CLAUDE.md AgentConsole/README.md
grep -c '^| US-\|^| API-\|^| BR-\|^| NFR-\|^| INF-\|^| UI-' AgentConsole/docs/06_quality/RTM.md
grep -c '^| US-' AgentConsole/docs/06_quality/RTM.md
grep -rniE 'pass[e]d|skip[p]ed' AgentConsole --include='*.md' | grep -E '[0-9]{4,}|[0-9]{1,3}(,[0-9]{3})+'
git status --porcelain
```

```powershell
Get-ChildItem AgentConsole -Recurse -File | Where-Object { $_.FullName -notmatch '\\(\.venv|\.ruff_cache|__pycache__)\\' } | Sort-Object FullName | ForEach-Object { $_.FullName }
(Get-Content AgentConsole\CLAUDE.md).Count; (Get-Content AgentConsole\README.md).Count
(Select-String -Path AgentConsole\docs\06_quality\RTM.md -Pattern '^\| (US|API|BR|NFR|INF|UI)-').Count
(Select-String -Path AgentConsole\docs\06_quality\RTM.md -Pattern '^\| US-').Count
Get-ChildItem AgentConsole -Recurse -Filter *.md | Select-String -Pattern 'pass[e]d|skip[p]ed' | Where-Object { $_.Line -match '\d{4,}|\d{1,3}(,\d{3})+' }
git status --porcelain
```

**出口閘門（Bridge 部分，取自 W1-B 任務書）**

```bash
(cd AgentConsole/engine-bridge && . ../../.venv/bin/activate && uv pip install -e .)
(cd AgentConsole/engine-bridge && . ../../.venv/bin/activate && ruff check . && python -m pytest -q)
(cd AgentConsole/engine-bridge && . ../../.venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8081)
curl -s http://localhost:8081/health
(cd tools/tests && python -m unittest test_platform_neutral_paths.TestDirEntryPrimitivesAreAccountedFor -v)
ruff check AgentConsole/engine-bridge
docker build -f AgentConsole/engine-bridge/Dockerfile -t aisdlc-engine-bridge:dev .
```

```powershell
Push-Location AgentConsole\engine-bridge; ..\..\.venv\Scripts\Activate.ps1; uv pip install -e .; Pop-Location
Push-Location AgentConsole\engine-bridge; ..\..\.venv\Scripts\Activate.ps1; ruff check .; python -m pytest -q; Pop-Location
Push-Location AgentConsole\engine-bridge; ..\..\.venv\Scripts\Activate.ps1; uvicorn app.main:app --host 127.0.0.1 --port 8081; Pop-Location
Invoke-RestMethod http://localhost:8081/health
Push-Location tools\tests; python -m unittest test_platform_neutral_paths.TestDirEntryPrimitivesAreAccountedFor -v; Pop-Location
ruff check AgentConsole\engine-bridge
docker build -f AgentConsole\engine-bridge\Dockerfile -t aisdlc-engine-bridge:dev .
```

（`uvicorn` 與 `curl`／`Invoke-RestMethod` 分兩個終端執行；驗完關掉 uvicorn。）

| 閘門 | 預期輸出字樣／判準 |
|------|-------------------|
| 檔案清單 | 含 `docs/02_architecture/{Architecture,ADR-001-TechStack-Lock}.md`、`docs/04_planning/Implementation_Plan.md`、`docs/06_quality/RTM.md`、`CLAUDE.md`、`README.md`、四個服務目錄的 `README.md` |
| 行數 | `CLAUDE.md` ≤ 200；`README.md` ≤ 80 |
| RTM 列數 | 總列數與 RTM §3.2 合計一致（建表時為 361）；US 列數 58 |
| 基線字樣掃描（同一行同時有 pytest 結果摘要用字與 4 位以上數字；上列指令以字元類寫法避免命中自己；狀態列舉 `SKIPPED` 本身合法） | **無任何輸出**（根層 `check_pytest_baseline_sites.py` 對這種行計數，新增即使 push 被擋） |
| `git status` | 所有變更列都落在 `AgentConsole/` 之下 |
| ruff（兩處） | 無違規、rc=0 |
| pytest | rc=0；摘要列無 `failed`／`error`；W1-B 貼實際摘要 |
| `/health` | JSON 含 `"status":"ok"`、`engines.autoclaude.ok`、`engines.sdd.latest` |
| 根層 exec／目錄項鎖 | 輸出 `OK` |
| docker build | 建置成功（Docker daemon 須在線；逾 10 分鐘記「未完成」並附末 20 行） |

**出口動作**：W1-B 交卷的〈契約落地差異〉由主控回寫 Architecture §10 與 RTM `BR-*`；W1-B 對 V-1／V-2／V-3／V-9 的實證結論回寫 Architecture §12.2。

---

### W2　後端 P1＋P2 ∥ Infra

**入口條件**

- W1 出口閘門全數通過；`docker info` rc=0（Docker daemon 在線）；對外連線已放行（Spring Initializr、Maven Central、Docker Hub、npm；見 §3 D-5）。
- **Architect 追加項（W2 任務書未列，主控須轉達）**：

| # | 追加項 | 對象 | 來源 |
|---|--------|------|------|
| 1 | backend 依賴加 `io.micrometer:micrometer-registry-prometheus`（Prometheus 抓 `/actuator/prometheus`） | W2-A | `API-HLT-02`、`INF-DR-20` |
| 2 | backend 加 Checkstyle（最小規則集） | W2-A | `NFR-9.4-01` |
| 3 | `V2` 種子的 `autoclaude.dalBackend` 預設值寫 `FILE`（不是 PRD 的 `POSTGRESQL`） | W2-A | ADR-001 D13 |
| 4 | Create*Request 加選填 `draft`（true → `signedOff=false`），供草案與 E2E 使用 | W2-A（或 W3-B 補） | ADR-001 D12 |
| 5 | `gradlew.bat` 一併入庫；`gradlew` 索引模式待主控裁決（§3 D-2） | W2-A | ADR-001 D15 |
| 6 | nginx 同掛 backend-net；pgadmin 掛 backend-net；全棧 PG 預設不發布；刪除手動 Flyway 步驟；`NEXT_PUBLIC_API_URL` 留空；補齊各服務 healthcheck | W2-B | ADR-001 D14-9～12、G-01／G-02／G-05／G-07 |
| 7 | 主機側 `.sh`（restore、failover）改成容器內執行（`docker compose run --rm pgbackrest …`）或補 `.ps1`；`.sh` 只給容器內用 | W2-B | `NFR-XPL-03` |
| 8 | 對 Windows 路徑：compose 內一律相對路徑、不含任何磁碟絕對路徑；`.env.example` 不含磁碟路徑 | W2-B | `NFR-XPL-01` |

**出口閘門**

```bash
(cd AgentConsole/backend && ./gradlew clean build)
grep -o '<tfoot>.*</tfoot>' AgentConsole/backend/build/reports/jacoco/test/html/index.html
(cd AgentConsole && docker compose --env-file .env.ci config > /dev/null; echo "config_rc=$?")
(cd AgentConsole && docker compose --env-file .env.ci --profile db up -d --build)
(cd AgentConsole && docker compose --env-file .env.ci --profile db ps)
(cd AgentConsole && docker compose --env-file .env.ci exec postgres-primary psql -U aisdlc -d aisdlc -c "SELECT client_addr,state,sync_state FROM pg_stat_replication;")
(cd AgentConsole && docker compose --env-file .env.ci exec pgbackrest pgbackrest --stanza=aisdlc check)
(cd AgentConsole && docker compose --env-file .env.ci --profile db down -v)
```

```powershell
Push-Location AgentConsole\backend; .\gradlew.bat clean build; Pop-Location
Select-String -Path AgentConsole\backend\build\reports\jacoco\test\html\index.html -Pattern '<tfoot>.*</tfoot>' | ForEach-Object { $_.Matches.Value }
Push-Location AgentConsole; docker compose --env-file .env.ci config *> $null; "config_rc=$LASTEXITCODE"; Pop-Location
Push-Location AgentConsole; docker compose --env-file .env.ci --profile db up -d --build; Pop-Location
Push-Location AgentConsole; docker compose --env-file .env.ci --profile db ps; Pop-Location
Push-Location AgentConsole; docker compose --env-file .env.ci exec postgres-primary psql -U aisdlc -d aisdlc -c "SELECT client_addr,state,sync_state FROM pg_stat_replication;"; Pop-Location
Push-Location AgentConsole; docker compose --env-file .env.ci exec pgbackrest pgbackrest --stanza=aisdlc check; Pop-Location
Push-Location AgentConsole; docker compose --env-file .env.ci --profile db down -v; Pop-Location
```

（`.env.ci` 由 `.env.example` 複製並填測試值，驗完必須刪除；`./gradlew` 出現 Permission denied 時改 `sh gradlew`。W2-A／W2-B 任務書列出的其餘閘門——bootRun 健康與登入、OpenAPI 路徑清單、`docker build`、備份全備／差備／離站／演練、Prometheus targets、Grafana 面板、shellcheck——照任務書執行並貼輸出。）

| 閘門 | 預期輸出字樣／判準 |
|------|-------------------|
| `gradlew clean build` | `BUILD SUCCESSFUL`；測試完成數與失敗數由 W2-A 貼實測（失敗須為 0） |
| JaCoCo | 總覆蓋率 ≥ 80%（NFR-9.4-02 後端門檻），貼 `<tfoot>` 內百分比 |
| Flyway＋JPA | 啟動無 `validate` 錯誤；`console` schema 內有 10 張表（V1）加種子（V2） |
| compose config | `config_rc=0` |
| compose ps | 各服務 healthy（`db` profile） |
| 串流複製 | 1 列 `state=streaming` |
| pgBackRest | `check` 無錯誤；全備／差備／離站／演練腳本成功（W2-B 貼輸出） |
| 清場 | 容器與 volume 全收；`.env.ci` 已刪；交卷列「開了→收了」 |

**出口動作**：回填 RTM（`INF-*`、`US-P／G／T`、`API-PRJ／GOL／TSK／SGN-02～04`、`API-AUTH／HLT／FMT`、`NFR-9.2-0x`）；把 `docker compose config` 的最終服務／埠／卷回填 Architecture §2；ADR-001 §6 的 E-1（Spring Boot 版本證據）、E-4、E-5 填入逐字輸出；V-5、V-6、V-10 結論回寫 Architecture §12.2。

---

### W3　前端 P1＋P2 ∥ 後端 P3～P6

**入口條件**

- W2 出口閘門通過；backend 在本機 8080 可啟動，`/v3/api-docs` 可取；`docker-compose.dev.yml` 可起 PG。
- W3-B（後端 P3～6）任務書由主控依本計畫與 Architecture §6、§7、§11 撰寫；範圍：匯入（二段拆解、signoff／confirm）、執行（`PlaybookBuilder`、`RunEventConsumer`、SSE 轉發、審核閘、自治等級、`GET /projects/{id}/executions`）、監控（指標、告警、報表、`GET /notifications/summary`）、設定（原子 token-guard、加密、歷史、匯出入、`ConfigMaterializer`）、Flyway V3／V4／V5。

**出口閘門（前端 W3-A，取自其任務書）**

```bash
(cd AgentConsole/frontend && npm run lint && npx tsc --noEmit && npm run build)
(cd AgentConsole/frontend && npx vitest run)
(cd AgentConsole/frontend && npx playwright test)
grep -rnE "TopRegion|ToolsRegion|BottomRegion" AgentConsole/frontend/app --include='*.tsx' | grep -v 'app/layout.tsx'
```

```powershell
Push-Location AgentConsole\frontend; npm run lint; npx tsc --noEmit; npm run build; Pop-Location
Push-Location AgentConsole\frontend; npx vitest run; Pop-Location
Push-Location AgentConsole\frontend; npx playwright test; Pop-Location
Get-ChildItem AgentConsole\frontend\app -Recurse -Filter *.tsx | Where-Object { $_.FullName -notlike '*\app\layout.tsx' } | Select-String -Pattern 'TopRegion|ToolsRegion|BottomRegion'
```

**出口閘門（後端 W3-B）**

```bash
(cd AgentConsole/backend && ./gradlew clean build)
(cd AgentConsole/backend && ./gradlew jacocoTestReport)
grep -o '<tfoot>.*</tfoot>' AgentConsole/backend/build/reports/jacoco/test/html/index.html
```

```powershell
Push-Location AgentConsole\backend; .\gradlew.bat clean build; Pop-Location
Push-Location AgentConsole\backend; .\gradlew.bat jacocoTestReport; Pop-Location
Select-String -Path AgentConsole\backend\build\reports\jacoco\test\html\index.html -Pattern '<tfoot>.*</tfoot>' | ForEach-Object { $_.Matches.Value }
```

| 閘門 | 預期輸出字樣／判準 |
|------|-------------------|
| 前端 lint／tsc／build | 皆 rc=0；貼 build 的 Route 表（含 §5.1 全部路由） |
| vitest | rc=0；含「四區塊各渲染一次且只在 `app/layout.tsx` 組裝」、`status.ts` 對照表完整（專案 6／目標 5／任務 11）、API client 的 401→refresh 流程 |
| Playwright | rc=0；每頁截圖入庫並列出與設計稿的差異 |
| 區塊組裝掃描 | **無任何輸出** |
| 圖表 spike | ADR-002 記載成／敗、採用方案與版本；回填 ADR-001 §6 E-3 |
| 後端 build | `BUILD SUCCESSFUL`；ArchUnit A1～A6 全綠；Flyway V3／V4／V5 套用且 JPA `validate` 通過 |
| 後端覆蓋率 | 總覆蓋率 ≥ 80% |
| Bridge 契約替身測試 | 以 MockWebServer／WireMock 驗：409／422 轉譯、SSE 位移與重連、補償刪除 run 列、審核閘提前 pause 的時序 |
| 真 Bridge 冒煙（一次） | 以 mock CLI 的真 Bridge 完成一次 `execute` → 終態 COMPLETED（貼 run 狀態與 3 個以上 step 事件） |
| 權限與安全 | RBAC（viewer 寫入 403、無 token 401）、SSRF（私網段／redirect／DNS rebinding 以假解析器驗）、token-guard 原子校驗 400 |

**出口動作**：回填 RTM（`US-P／G／T` 的 FE 側、`UI-SCR-02～05`、`UI-LAY-*`、`UI-DS-*`、`UI-MD-*`、`UI-OVL-*`、`API-IMP／EXE／MON／SET／ALR／AUT／DAG／SSE`）；V-4、V-7、V-8 結論回寫 Architecture §12.2。

---

### W4　前端 P3～P6 ∥ QA

**入口條件**：W3 出口閘門通過；後端 P3～6 與 Bridge 可同時在本機啟動（§9.2 步驟）；mock CLI 設定就緒（`console.execution.mock-cli=true`）；Plan 相依 D-1（decompose 的 FakeBrain 注入點）已落地或已記為 `🟡`。

**出口閘門**

```bash
(cd AgentConsole/frontend && npm run lint && npx tsc --noEmit && npm run build)
(cd AgentConsole/frontend && npx vitest run --coverage)
(cd AgentConsole/frontend && npx playwright test)
grep -c -E '^\| (US|API|BR|NFR|INF|UI)-.*⬜ 未開始 \|$' AgentConsole/docs/06_quality/RTM.md
grep -c -E '^\| (US|API|BR|NFR|INF|UI)-.*✅ 已驗證 \|$' AgentConsole/docs/06_quality/RTM.md
```

```powershell
Push-Location AgentConsole\frontend; npm run lint; npx tsc --noEmit; npm run build; Pop-Location
Push-Location AgentConsole\frontend; npx vitest run --coverage; Pop-Location
Push-Location AgentConsole\frontend; npx playwright test; Pop-Location
(Select-String -Path AgentConsole\docs\06_quality\RTM.md -Pattern '^\| (US|API|BR|NFR|INF|UI)-.*⬜ 未開始 \|$').Count
(Select-String -Path AgentConsole\docs\06_quality\RTM.md -Pattern '^\| (US|API|BR|NFR|INF|UI)-.*✅ 已驗證 \|$').Count
```

| 閘門 | 預期輸出字樣／判準 |
|------|-------------------|
| 前端靜態＋建置 | 皆 rc=0 |
| 前端覆蓋率 | ≥ 70%（NFR-9.4-02 前端門檻） |
| 全鏈 Playwright E2E | rc=0；涵蓋：登入 → 匯入（貼文字）→ 解析（FakeBrain）→ 觸發有界閘錯誤顯示 → signoff → confirm → 啟動執行（mock CLI）→ SSE 日誌 → pause／resume → restore → 審核閘 → 監控 KPI 與圖表 → 設定頁 token-guard 校驗 400 |
| Docker 全棧 E2E | 經 nginx 單一入口重跑上列主要流程；`/api/v1/projects` 未帶 token 回 401（證明 nginx→backend 通） |
| 消毒字元集 parity | 腳本比對 Bridge 常數（import 引擎 `BASE_DENY_CHARS`）與後端常數一致，貼輸出（Architecture §8.3） |
| RTM 核對 | `⬜ 未開始` 計數為 0；每列為 `✅ 已驗證`、`❌ 缺陷`或 `⛔ 範圍外`；`✅` 皆附輸出 |
| NFR 量測 | NFR-9.1-01～06 各附量測方法與數值（方法由 QA 於報告載明） |

**出口動作**：QA 報告落 `docs/06_quality/`；`❌` 列轉 W5；RTM §3 統計以現查指令重算。

---

### W5　修復

**入口條件**：W4 QA 報告與 RTM 中的 `❌ 缺陷`清單；Windows 接續階段回報的缺陷（§4）。

**出口閘門**

```bash
python tools/check_pytest_baseline_sites.py
python tools/lib/secret_scan.py --paths AgentConsole/.env.example AgentConsole/CLAUDE.md AgentConsole/README.md
ruff check AgentConsole/engine-bridge
python tools/run_root_unittests.py
```

```powershell
python tools\check_pytest_baseline_sites.py
python tools\lib\secret_scan.py --paths AgentConsole\.env.example AgentConsole\CLAUDE.md AgentConsole\README.md
ruff check AgentConsole\engine-bridge
python tools\run_root_unittests.py
```

| 閘門 | 預期輸出字樣／判準 |
|------|-------------------|
| 全部 `❌` | 修復後重跑對應 E2E，RTM 轉 `✅ 已驗證`，附輸出 |
| 基線站點掃描 | rc=0 |
| 機密掃描 | rc=0（`.env.example` 只含 `<YOUR_...>` 佔位符） |
| ruff | 無違規、rc=0 |
| 根層全套 | rc=0（耗時長，須以有契約的背景方式或長 timeout 執行；`gradlew` 索引模式若為 100755，須先完成 §3 D-2 的 ONBOARDING 同步） |

---

## 3. 跨波次相依與風險

| 編號 | 相依／風險 | 負責 | 處置 |
|------|------------|------|------|
| D-1 | decompose 的真鏈 E2E 需要可決定性 Brain：`mock_brain_server.py` 不支援 decomposition（ADR-001 D9），Bridge 需提供 FakeBrain 注入點（建議 `BRIDGE_FAKE_BRAIN=1`） | W1-B 或 W5 | 未提供則 decompose 真鏈 E2E 標 `🟡`，僅以 Bridge 層單元測試覆蓋 |
| D-2 | `gradlew` 索引模式：掌舵者的跨平台補充要求 100755，根層 exec bit 鎖要求 100755 檔須列入 `ONBOARDING.md` §6「755 入庫」範圍（ADR-001 D15） | 主控 | 第一次 commit 前二擇一：補進 ONBOARDING §6，或改 644＋文件寫 `sh gradlew` |
| D-3 | compose 的 nginx／pgadmin 網路、PG 發布埠、`NEXT_PUBLIC_API_URL` 語意（ADR-001 D14-9～12） | W2-B | 實測後回寫 `docker/README.md` 與 Architecture §2 |
| D-4 | W2 任務書追加項（W2 入口條件表） | 主控 | 開工前轉達 W2-A、W2-B |
| D-5 | 對外連線（Initializr、npm、Maven Central、Docker Hub）可能被 auto mode 分類器擋下 | 主控 | 預先放行該類呼叫，或由主控代跑骨架生成與依賴下載 |
| D-6 | Docker Desktop 須在線（W1-A 撰寫初期曾連不上 socket，收尾時已在線；狀態會變動） | 主控 | 每次開工前 `docker info` rc=0 |
| D-7 | 根層 `CLAUDE.md` 仍稱「雙專案 monorepo」，且有多支內容鎖讀它 | 主控 | 第一次 commit 前跑根層全套；是否更新根 CLAUDE.md 由主控裁決（本輪不得動） |
| D-8 | PRD §12.3.4／§12.5.2 的 restore、failover 為主機側 `.sh` | W2-B | 改容器內執行或補 `.ps1`（`NFR-XPL-03`） |
| R-1 | Spring Boot 4 的 starter／springdoc／jjwt／Testcontainers 相容 | W2-A | 以編譯為準，逐模組 `compileJava compileTestJava` |
| R-2 | Tremor Raw 於 Tailwind 4 不通 | W3-A | 30 分鐘限時，改 shadcn chart（ADR-001 D3） |
| R-3 | 審核閘提前 pause 的精度受 SSE 延遲與步驟時長影響（Architecture L-7） | W3-B、W4 QA | mock CLI 製造不同步驟時長驗證；不成立則開 ADR-003 |
| R-4 | Windows 行程控制：`terminate()` 強制結束、claude 子行程樹殘留 | W1-B、Windows 接續 | 以 psutil 清理行程樹；Windows 全套實跑 |
| R-5 | PGDG apt 的 pgbackrest 是否支援 PG18 | W2-B | 不支援則改以官方原始碼或其他來源安裝，記入 `docker/README.md` |

---

## 4. Windows 接續檢查清單

本輪結束後在 **Windows 11 ＋ PowerShell** 接續（無 Bash 工具）。以下逐項在 Windows 上第一次實跑前核對；結果回寫本節與進度帳。

### 4.1 前置軟體

| 軟體 | 版本 | 備註 |
|------|------|------|
| Docker Desktop | 含 Compose v2；WSL2 後端 | 須在線（`docker info` rc=0）；Testcontainers 與 compose 皆依賴 |
| Java | 21（Temurin 等） | `JAVA_HOME` 指向 JDK 21 |
| Node.js | 22 LTS（npm 10） | |
| uv | 最新穩定版 | 由 uv 取得 Python 3.11（不要用系統 Python） |
| Git | 含 `core.autocrlf` 以 repo 的 `.gitattributes` 為準 | `.sh`／Dockerfile／yml 須維持 LF |
| PowerShell | 7（pwsh） | 本專案無 PS 5.1 專屬腳本 |

```bash
docker --version; docker info > /dev/null; echo "docker_rc=$?"
java -version
node -v; npm -v
uv --version
```

```powershell
docker --version; docker info *> $null; "docker_rc=$LASTEXITCODE"
java -version
node -v; npm -v
uv --version
```

### 4.2 各服務第一次啟動要驗的三條指令

**PostgreSQL（dev compose）**

```bash
(cd AgentConsole && docker compose -f docker-compose.dev.yml up -d)
(cd AgentConsole && docker compose -f docker-compose.dev.yml ps)
(cd AgentConsole && docker compose -f docker-compose.dev.yml exec postgres-primary pg_isready -U aisdlc -d aisdlc)
```

```powershell
Push-Location AgentConsole; docker compose -f docker-compose.dev.yml up -d; Pop-Location
Push-Location AgentConsole; docker compose -f docker-compose.dev.yml ps; Pop-Location
Push-Location AgentConsole; docker compose -f docker-compose.dev.yml exec postgres-primary pg_isready -U aisdlc -d aisdlc; Pop-Location
```

預期：`ps` 顯示 healthy；`pg_isready` 回 `accepting connections`。

**Engine Bridge**

```bash
(cd AgentConsole/engine-bridge && . ../../.venv/bin/activate && uv pip install -e .)
(cd AgentConsole/engine-bridge && . ../../.venv/bin/activate && python -m pytest -q)
(cd AgentConsole/engine-bridge && . ../../.venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8081)
```

```powershell
Push-Location AgentConsole\engine-bridge; ..\..\.venv\Scripts\Activate.ps1; uv pip install -e .; Pop-Location
Push-Location AgentConsole\engine-bridge; ..\..\.venv\Scripts\Activate.ps1; python -m pytest -q; Pop-Location
Push-Location AgentConsole\engine-bridge; ..\..\.venv\Scripts\Activate.ps1; uvicorn app.main:app --host 127.0.0.1 --port 8081; Pop-Location
```

預期：pytest 全套 rc=0（尤其 pause／stop／孤兒回收／restore 四組，它們碰到 Windows 行程控制）；另開終端 `Invoke-RestMethod http://localhost:8081/health` 回 `status = ok`。`Activate.ps1` 被執行原則擋下時：`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`（僅本行程）。

**backend**

```bash
(cd AgentConsole/backend && ./gradlew --version)
(cd AgentConsole/backend && ./gradlew clean build)
(cd AgentConsole/backend && JWT_SECRET='<YOUR_JWT_SECRET_MIN_32_CHARS>' SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/aisdlc SPRING_DATASOURCE_USERNAME=aisdlc SPRING_DATASOURCE_PASSWORD='<YOUR_POSTGRES_PASSWORD>' ENGINE_BRIDGE_URL=http://localhost:8081 ./gradlew bootRun)
```

```powershell
Push-Location AgentConsole\backend; .\gradlew.bat --version; Pop-Location
Push-Location AgentConsole\backend; .\gradlew.bat clean build; Pop-Location
Push-Location AgentConsole\backend; $env:JWT_SECRET="<YOUR_JWT_SECRET_MIN_32_CHARS>"; $env:SPRING_DATASOURCE_URL="jdbc:postgresql://localhost:5432/aisdlc"; $env:SPRING_DATASOURCE_USERNAME="aisdlc"; $env:SPRING_DATASOURCE_PASSWORD="<YOUR_POSTGRES_PASSWORD>"; $env:ENGINE_BRIDGE_URL="http://localhost:8081"; .\gradlew.bat bootRun; Pop-Location
```

預期：`--version` 印出 Gradle 與 JVM 21；`build` 為 `BUILD SUCCESSFUL`（Testcontainers 需 Docker Desktop 在線）；另開終端 `Invoke-RestMethod http://localhost:8080/actuator/health` 回 `status = UP`。

**frontend**

```bash
(cd AgentConsole/frontend && npm ci)
(cd AgentConsole/frontend && npm run build)
(cd AgentConsole/frontend && npm run dev)
```

```powershell
Push-Location AgentConsole\frontend; npm ci; Pop-Location
Push-Location AgentConsole\frontend; npm run build; Pop-Location
Push-Location AgentConsole\frontend; npm run dev; Pop-Location
```

預期：`build` 輸出 Route 表且 rc=0；另開終端 `Invoke-RestMethod http://localhost:3000/api/health` 回 `status = ok`。

**Docker 全棧**

```bash
(cd AgentConsole && docker compose --profile db --profile app --profile full config > /dev/null; echo "config_rc=$?")
(cd AgentConsole && docker compose --profile db --profile app --profile full up -d --build)
(cd AgentConsole && docker compose --profile db --profile app --profile full ps)
```

```powershell
Push-Location AgentConsole; docker compose --profile db --profile app --profile full config *> $null; "config_rc=$LASTEXITCODE"; Pop-Location
Push-Location AgentConsole; docker compose --profile db --profile app --profile full up -d --build; Pop-Location
Push-Location AgentConsole; docker compose --profile db --profile app --profile full ps; Pop-Location
```

預期：`config_rc=0`；`ps` 全部 healthy；`curl.exe -s -o NUL -w "%{http_code}\n" http://localhost/` 回 200，`.../api/v1/projects` 回 401。

### 4.3 Windows 專屬風險檢查

| 風險 | 驗證（PowerShell；括號內為 bash 對照） | 預期 |
|------|----------------------------------------|------|
| 行尾：`.sh`、Dockerfile、yml 須 LF；`.ps1` 須 CRLF；`gradlew` LF、`gradlew.bat` CRLF | `git ls-files --eol AgentConsole/backend/gradlew AgentConsole/backend/gradlew.bat`（同） | `gradlew` 的工作樹欄為 `w/lf`；`gradlew.bat` 為 `w/crlf` |
| `.env` 以 LF 儲存（CRLF 會讓 compose 變數尾帶 `\r`） | `(Get-Content AgentConsole\.env -Raw).Contains([string][char]13)`（`grep -c $'\r' AgentConsole/.env`） | `False`（bash 為 0） |
| 路徑比對（大小寫不分、磁碟機代號） | Bridge pytest 內的 `execution_path` allowlist 測試 | 全綠；`..` 與 symlink 逃逸仍被擋 |
| stop 後無殘留引擎行程 | 啟動一個 run → stop → `Get-CimInstance Win32_Process -Filter "Name like 'python%'" \| Select-Object ProcessId,CommandLine` | 無屬於該 run 的 `autoclaude`／mock CLI 行程 |
| 主機側不依賴 `.sh` | `Get-ChildItem AgentConsole -Recurse -Filter *.sh \| Select-Object FullName`，逐一確認僅被容器使用 | 無任何文件教人在 Windows 主機直接執行 `.sh` |
| `gradlew` 執行位元（Git 索引） | `git ls-files -s AgentConsole/backend/gradlew`（同） | 依 §3 D-2 的裁決（100755 或 100644） |

---

## 5. 進度帳（主控填）

### 5.1 波次進度

| 波次 | 狀態 | commit | 出口閘門結果（逐字貼關鍵行或附證據檔路徑） | 未結缺陷 | 備註 |
|------|------|--------|--------------------------------------------|----------|------|
| W1 | ✅ 完成（主控親驗） | 本 commit | W1-A：7 份文件、RTM 361 列（PRD 58 條使用者故事程式化對帳 0 缺）、PowerShell 區塊 lint 0 命中。W1-B：主控親跑 `ruff check .`＝All checks passed、`pytest -n 4`＝235 passed／9 skipped（9 支為需 BRIDGE_TEST_DSN 的 DB 整合測試，他包回報含 DB 244 全綠）、字面 `docker build` slim 映像 rc=0 且容器 `/health` 兩引擎 ok、根層 TestDirEntryPrimitivesAreAccountedFor OK | 無 | 兩個前提被真機推翻：引擎不寫步驟級 checkpoint；E2E 替身＝`aisdlc-mock-claude`（ADR-001 D8／補記 D17） |
| W2 | ✅ 完成（主控親驗） | 本 commit | W2-A：主控親跑 `sh gradlew clean build`＝Test result SUCCESS（448 支、0 失敗）、Checkstyle 通過、JaCoCo 驗證通過、BUILD SUCCESSFUL。W2-B：主控親跑 `docker compose config`（四 profile）rc=0；14 支 .sh shellcheck 0.11／bash -n／CR 皆 0 問題；`--profile db up --wait` rc=0 全部 healthy、`pg_stat_replication`＝streaming async、副本讀到主庫寫入、`pgbackrest check` WAL 同時歸檔 repo1 與 repo2（MinIO）、全備兩 repo 皆成功、`down -v` 清場 | 無 | 主控第一次驗證把 `.env` 12 個佔位符填同一值導致 minio-init 退出 1（root 帳號與備份帳號同名）——非缺陷，已在 `.env.example` 加註 |
| W2-B（Infra） | 完成，待主控驗證與 commit | 未 commit | 2026-10-15 macOS（Docker Desktop）實跑：config 四種模式 rc=0；ps 全部 healthy；pg_stat_replication 1 列 streaming／async；pgbackrest check 兩個 repo 皆成功歸檔；全備與差備皆 repo1＋repo2；pg_dump 離站物件在 MinIO logical/；verify-backup 兩個 repo 皆 OK；Prometheus targets 4 個 up（db profile 下 spring-boot down 屬預期）、規則 12 條健康；Grafana 2 個 dashboard；docker 下 14 支 .sh 的 shellcheck 與 bash -n 皆 rc=0；down -v 清場。另以 W3-A／W2-A 建好的真實 frontend／backend 映像實跑 db＋app＋full：14 個長駐服務全 healthy、經 nginx 登入並建立專案、Flyway 13 張表串流到 replica、spring-boot target up、含應用資料的全備與還原演練兩個 repo 皆 OK、failover 與切回（含真實 backend）資料不丟 | 無新增缺陷；已知限制見 docker/README.md〈10〉 | D-3／D-8／R-5 已結：G-01／G-02 實測（ADR-001 §6 E-4／E-5 已回填）、restore 與 failover 改為 docker compose 指令序列（含實跑的切回流程）、PGDG 的 pgbackrest 2.59.3 支援 PG18；偏離 PRD 27 項見 docker/README.md〈9〉；官方 minio 映像已下架（改 pgsty/minio）；Windows 未驗，清單見 docker/README.md〈11〉 |
| W2-A（後端 P1＋P2） | ✅ 實作＋測試完成，待主控驗證與 commit | 待主控 | `gradlew clean build`＝BUILD SUCCESSFUL（448 筆測試、0 失敗、0 略過；Checkstyle 通過；JaCoCo 指令覆蓋 97%、分支 88%，門檻 80%）；`docker build -t aisdlc-backend:dev AgentConsole/backend` rc=0，容器 healthy；bootRun 取證：`/actuator/health`＝`{"groups":["liveness","readiness"],"status":"UP"}`，登入、建專案、列表、signoff、軟刪除皆符合；`/v3/api-docs` 13 個路徑、22 個操作 | 無 | Spring Boot 4.1.1、springdoc 3.1.1、jjwt 0.12.7；偏離與行為備忘見 `backend/README.md`；Windows 尚未驗證項見 W2-A 交卷〈Windows 接續注意〉 |
| W3-A（前端 P1＋P2＋四區塊版面） | ✅ 實作＋測試完成，待主控驗證與 commit | 待主控 | `npm run lint` rc=0；`npx tsc --noEmit` rc=0；`npm run build` rc=0（路由表 20 項含 `_not-found`，PRD §4.2 巢狀路由齊全）；vitest 14 個檔、104 個案例全數通過，受測範圍覆蓋率 語句 88.16%／分支 80.32%／函式 89.06%／行 91.4%（門檻 70%）；Playwright 17 個案例全數通過（對 `docker build` 出的生產映像容器＋真後端 console-api＋PostgreSQL；含登入→CRUD→依賴成環→拖曳排序→signoff→刪除、響應式、設計系統守衛、圖表）；四區塊唯一性 grep 閘門輸出為空；`docker build -t aisdlc-frontend:dev` rc=0，容器 uid 1001、`GET /api/health` 回 `{"status":"ok"}`、Health.Status＝`healthy` | 無 | Next 16.4.0／React 19.3.0／Tailwind 4.3.3／shadcn CLI 4.21.5（radix-nova，已重寫為設計系統版）；圖表 spike **成功**（Tremor Raw AreaChart＋recharts 2.15.4，須 `overrides.react-is`＝19.3.0，詳見 ADR-002 §D6）；匯入／執行／監控／設定為路由殼（W4）；Windows 尚未驗證項見 W3-A 交卷〈Windows 接續注意〉 |
| W3 | 🟡 W3-A 完成（主控親驗）；W3-B 未派 | 本 commit | W3-A：主控親跑 lint rc=0、tsc rc=0、build 成功（20 路由）、vitest 14 檔 104 案例全過、Playwright 對真後端＋PG 17 passed（資料零殘留）、版面唯一性 grep 為空 | 無 | W3-B（後端 Phase 3～6）任務書已備（`agent_briefs/W3_BACKEND_P3-6.md`），Windows 輪第一棒 |
| W4 | ⬜ 未開始 | — | — | — | 前端 Phase 3～6 任務書待後端 Phase 3～6 的 OpenAPI 定案後撰寫；QA 全面 E2E 矩陣同輪 |
| W5 | ⬜ 未開始 | — | — | — | 修復波 |
| Windows 接續 | 🟡 首跑完成（主控親驗 2026-10-15）；Docker 全棧與 Playwright 留給 W4 QA 在 Windows 實跑 | 本 commit | Bridge：`uv pip install -e AgentConsole\engine-bridge --python .venv\Scripts\python.exe` rc=0；`python -m pytest -q` 第一次 1 failed／230 passed／13 skipped——`tests/test_procutil.py::test_terminate_takes_the_grandchild_too` 的等號斷言在 Windows 不成立（venv 的 `python.exe` 是啟動器，行程樹多出啟動器行程；主控以 psutil 探針實證），改為 win32 超集合斷言後該檔 7 passed、ruff 綠。backend：`.\gradlew.bat clean build`＝Test result SUCCESS（448 tests、0 failures）、BUILD SUCCESSFUL in 2m 12s（Java 21.0.10、Gradle 9.8.1、Testcontainers 走 Docker Desktop）。frontend：`npm ci` rc=0、`npm run build` rc=0（20 路由）；`npx vitest run` 在 Node 20.19.5 下 14 個測試檔全部起不來（jsdom 內的 undici 需要 Node 22 的 zlib zstd API），以 nvm-windows 切到 Node 22.23.3 後 14 檔 104 案例全過 | 無（兩個環境缺口當場修掉） | §4.1 的 Node 22 是硬性前置，不是建議；`nvm use` 在無人核准 UAC 時會刪掉舊 symlink 卻建不出新的（訊息仍印成功），主控以不需管理員的 junction 修復（`New-Item -ItemType Junction -Path C:\nvm4w\nodejs -Target <nvm>\v22.23.3`） |

### 5.2 RTM 快照（以 RTM §3.4 現查指令填）

| 日期 | 總列數 | `⬜ 未開始` | `🟡 部分` | `✅ 實作+測試` | `✅ 已驗證` | `❌ 缺陷` | `⛔ 範圍外` |
|------|--------|-------------|-----------|----------------|-------------|-----------|-------------|
| 2026-10-15 | 361 | 157 | 23 | 99 | 82 | 0 | 0 |

### 5.3 待裁決事項

| 編號 | 事項 | 狀態 | 裁決與日期 |
|------|------|------|-----------|
| D-2 | `gradlew` 索引模式與 ONBOARDING §6 | ✅ 已裁決 | 2026-10-15 主控：入庫 644、文件一律 `sh gradlew`（Windows `.\gradlew.bat`）、Dockerfile 內 `chmod +x`；不動 ONBOARDING §6 |
| D-1 | decompose 真鏈 E2E 的 FakeBrain 注入點 | ✅ 已裁決（部分作廢） | 2026-10-15 主控：dummy_cli 授權提示議題作廢（替身改 `aisdlc-mock-claude`）；Bridge 的 decompose 測試以行程內 FakeBrain 覆蓋；後端 Phase 3 若需跨行程注入點，由 W3-B 評估後提案（見 `agent_briefs/W3_BACKEND_P3-6.md`） |
| D-7 | 根層 `CLAUDE.md` 是否更新為三子專案 | ✅ 已裁決 | 2026-10-15 主控：已加 AgentConsole 列與文件快查列，鎖測試 test_doc_loc_baseline_freshness_r60 rc=0；windows-compat-ci.yml 補 `AgentConsole/**/*.sh`（compat-CI 觸發對稱鎖） |
