# AgentConsole

AISDLC Agent Console UI：掌舵者用網頁管理 AI Agent 的開發生命週期（專案→目標→任務、BRD/PRD 匯入、人工 signoff 硬閘、執行與監控、系統參數）。三個服務：`frontend`（Next.js 16）、`backend`（Spring Boot 4.1）、`engine-bridge`（FastAPI 旁車，包 AutoClaude 與 AISDLC_SDD），共用 PostgreSQL 18。

## 前置需求

Docker（Desktop 或 Engine，含 Compose v2）、Java 21、Node.js 22、uv（取得 Python 3.11）；Windows 另需 PowerShell 7（逐項檢查指令見 `docs/04_planning/Implementation_Plan.md` §4.1）。以下指令工作目錄假設在 monorepo 根，bash／PowerShell 並列。

## 本機開發（三步；埠 3000／8080／8081）

**1. 準備環境檔並起 PostgreSQL**（把 `.env` 內的 `<YOUR_...>` 換成本機測試值）
```bash
cp AgentConsole/.env.example AgentConsole/.env && (cd AgentConsole && docker compose -f docker-compose.dev.yml up -d)
```

```powershell
Copy-Item AgentConsole\.env.example AgentConsole\.env; Push-Location AgentConsole; docker compose -f docker-compose.dev.yml up -d; Pop-Location
```

**2. 起三個服務**（各開一個終端，前景執行）
```bash
(cd AgentConsole/engine-bridge && . ../../.venv/bin/activate && uv pip install -e . && uvicorn app.main:app --host 127.0.0.1 --port 8081)
(cd AgentConsole/backend && JWT_SECRET='<YOUR_JWT_SECRET_MIN_32_CHARS>' SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/aisdlc SPRING_DATASOURCE_USERNAME=aisdlc SPRING_DATASOURCE_PASSWORD='<YOUR_POSTGRES_PASSWORD>' ENGINE_BRIDGE_URL=http://localhost:8081 ./gradlew bootRun)
(cd AgentConsole/frontend && npm ci && npm run dev)
```

```powershell
Push-Location AgentConsole\engine-bridge; ..\..\.venv\Scripts\Activate.ps1; uv pip install -e .; uvicorn app.main:app --host 127.0.0.1 --port 8081; Pop-Location
Push-Location AgentConsole\backend; $env:JWT_SECRET="<YOUR_JWT_SECRET_MIN_32_CHARS>"; $env:SPRING_DATASOURCE_URL="jdbc:postgresql://localhost:5432/aisdlc"; $env:SPRING_DATASOURCE_USERNAME="aisdlc"; $env:SPRING_DATASOURCE_PASSWORD="<YOUR_POSTGRES_PASSWORD>"; $env:ENGINE_BRIDGE_URL="http://localhost:8081"; .\gradlew.bat bootRun; Pop-Location
Push-Location AgentConsole\frontend; npm ci; npm run dev; Pop-Location
```

`./gradlew` 出現 Permission denied 時改 `sh gradlew bootRun`。要讓執行資料寫進 PostgreSQL，Bridge 另設 `BRIDGE_DB_DSN`（見 `CLAUDE.md` 環境變數表）。

**3. 驗證**（另開終端）
```bash
curl -s http://localhost:8081/health
curl -s http://localhost:8080/actuator/health
```

```powershell
Invoke-RestMethod http://localhost:8081/health
Invoke-RestMethod http://localhost:8080/actuator/health
```

## Docker 全棧（三步；經 nginx 單一入口）

**1. 準備環境檔**（全棧的 `NEXT_PUBLIC_API_URL` 留空＝同源）

```bash
cp AgentConsole/.env.example AgentConsole/.env
```

```powershell
Copy-Item AgentConsole\.env.example AgentConsole\.env
```

**2. 建置並啟動；3. 檢查狀態**

```bash
(cd AgentConsole && docker compose --profile db --profile app --profile full up -d --build)
(cd AgentConsole && docker compose --profile db --profile app --profile full ps)
```

```powershell
Push-Location AgentConsole; docker compose --profile db --profile app --profile full up -d --build; Pop-Location
Push-Location AgentConsole; docker compose --profile db --profile app --profile full ps; Pop-Location
```

收尾：把 `up -d --build` 換成 `down`（`down -v` 會刪全部資料卷，僅限清場）。profile 名稱以 `docker/README.md` 為準。

## 看到什麼算成功

- Bridge `/health` 回 `"status":"ok"`；backend `/actuator/health` 回 `"status":"UP"`。
- 瀏覽器開 `http://localhost:3000`（Docker 全棧為 `http://localhost`）見登入頁，登入後見總覽儀表板。
- 全棧 `ps` 各服務皆 healthy；Grafana `http://localhost:3001`、pgAdmin `http://localhost:5050`、Prometheus `http://localhost:9090` 可開。

**文件**：規範與鐵律：[CLAUDE.md](CLAUDE.md)；地圖與契約：[Architecture](docs/02_architecture/Architecture.md)；決策：[ADR-001](docs/02_architecture/ADR-001-TechStack-Lock.md)；需求追溯：[RTM](docs/06_quality/RTM.md)；波次與閘門：[Implementation_Plan](docs/04_planning/Implementation_Plan.md)。
