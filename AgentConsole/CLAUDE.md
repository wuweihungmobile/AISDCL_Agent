# CLAUDE.md — AgentConsole 專案指引

**Last Updated**: 2026-10-14 | **PRD**: v1.1.0（`docs/01_requirements/Agent_ConsoleUI_PRD.md`，§0 權威）| **狀態**: W1（架構文件＋Engine Bridge）；後續波次見 [Implementation_Plan](docs/04_planning/Implementation_Plan.md)

> **🔴 Important Notice 🔴** 本檔指令 OVERRIDE 預設行為，必須嚴格遵守。monorepo 根層 `CLAUDE.md` 的鐵律（尤其 Windows 側「PowerShell 單一載具、禁裸 cd」）同樣適用；本檔只補本子專案的規定，不得違反根層鐵律。

---

## 🔴 溝通語言規範

所有回覆、文件、註解、commit 訊息一律**繁體中文**（專有名詞如 AISDLC、SDD、API、Docker、JWT、SSE 保持原文）。禁止英文、簡體、日韓文回覆；每次回覆前自我檢查語言。

## 📍 這是什麼

AISDLC Agent Console UI：掌舵者用網頁管理 AI Agent 的開發生命週期（專案→目標→任務、BRD/PRD 匯入、🔴 人工 signoff 硬閘、執行與監控、系統參數）。**最小侵入白名單**（2026-10-17 整合輪 115 取代原「零侵入」）：兩引擎只准改 `docs/04_planning/ADR/ADR-XPLAT-016-sdd-integration-loop-minimal-intrusion.md` §11 列出的檔，其餘仍由 Engine Bridge 旁車包它們；SDD FSM 的寫入一律經 `FSMRuntime` CLI 子行程，Bridge 不開寫狀態檔。

| 服務 | 技術 | 埠 | 路徑 |
|------|------|----|------|
| frontend | Next.js 16／TypeScript 5 strict／Tailwind 4／shadcn/ui | 3000 | `frontend/` |
| backend（console-api） | Spring Boot 4.1／Java 21／Gradle Kotlin DSL／Clean Architecture | 8080 | `backend/` |
| engine-bridge | Python 3.11／FastAPI／uvicorn／psycopg 3（裝進根層 `.venv`，單一 venv 規則） | 8081 | `engine-bridge/` |
| PostgreSQL 18 | `pgvector/pgvector:pg18`；Console 表在 `console` schema | 5432 | `docker/` |

## 🏗️ 目錄地圖

```
AgentConsole/
├── CLAUDE.md / README.md / docker-compose.yml / docker-compose.dev.yml / .env.example
├── docs/{02_architecture,03_testing,04_planning,06_quality}/   # 03＝SDD 的 TCS（contracts/）
├── frontend/   backend/   engine-bridge/   docker/{nginx,postgres/{primary,replica},pgbackrest,redis,prometheus,grafana}/
```

細節見 [Architecture.md](docs/02_architecture/Architecture.md) §3。核心業務規則：AI 草案 `signed_off=false` **禁止執行**，後端對 execute／resume／restore 二次校驗，違者 409（前端禁用按鈕只是體驗）。

## ⚙️ 開發指令

> 工作目錄一律假設在 **monorepo 根**；每段指令皆 bash＋PowerShell 並列；每個服務各開一個終端前景執行。

### engine-bridge（安裝／執行／測試／lint）

```bash
(cd AgentConsole/engine-bridge && . ../../.venv/bin/activate && uv pip install -e .)
(cd AgentConsole/engine-bridge && . ../../.venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8081)
(cd AgentConsole/engine-bridge && . ../../.venv/bin/activate && python -m pytest -q)
(cd AgentConsole/engine-bridge && . ../../.venv/bin/activate && ruff check .)
```

```powershell
Push-Location AgentConsole\engine-bridge; ..\..\.venv\Scripts\Activate.ps1; uv pip install -e .; Pop-Location
Push-Location AgentConsole\engine-bridge; ..\..\.venv\Scripts\Activate.ps1; uvicorn app.main:app --host 127.0.0.1 --port 8081; Pop-Location
Push-Location AgentConsole\engine-bridge; ..\..\.venv\Scripts\Activate.ps1; python -m pytest -q; Pop-Location
Push-Location AgentConsole\engine-bridge; ..\..\.venv\Scripts\Activate.ps1; ruff check .; Pop-Location
```

### backend（建置＋測試／執行）

```bash
(cd AgentConsole/backend && ./gradlew clean build)
(cd AgentConsole/backend && JWT_SECRET='<YOUR_JWT_SECRET_MIN_32_CHARS>' ./gradlew bootRun)
```

```powershell
Push-Location AgentConsole\backend; .\gradlew.bat clean build; Pop-Location
Push-Location AgentConsole\backend; $env:JWT_SECRET="<YOUR_JWT_SECRET_MIN_32_CHARS>"; .\gradlew.bat bootRun; Pop-Location
```

`./gradlew` 出現 Permission denied 時改 `sh gradlew`；`bootRun` 另需 `SPRING_DATASOURCE_*` 與 `ENGINE_BRIDGE_URL`（見下表）。

### frontend（安裝／執行／測試／lint＋型別＋建置）

```bash
(cd AgentConsole/frontend && npm ci)
(cd AgentConsole/frontend && npm run dev)
(cd AgentConsole/frontend && npx vitest run)
(cd AgentConsole/frontend && npm run lint && npx tsc --noEmit && npm run build)
```

```powershell
Push-Location AgentConsole\frontend; npm ci; Pop-Location
Push-Location AgentConsole\frontend; npm run dev; Pop-Location
Push-Location AgentConsole\frontend; npx vitest run; Pop-Location
Push-Location AgentConsole\frontend; npm run lint; npx tsc --noEmit; npm run build; Pop-Location
```

### Docker（本機開發只起 PG／全棧一鍵／收尾）

```bash
(cd AgentConsole && docker compose -f docker-compose.dev.yml up -d)
(cd AgentConsole && docker compose --profile db --profile app --profile full up -d --build)
(cd AgentConsole && docker compose --profile db --profile app --profile full down)
```

```powershell
Push-Location AgentConsole; docker compose -f docker-compose.dev.yml up -d; Pop-Location
Push-Location AgentConsole; docker compose --profile db --profile app --profile full up -d --build; Pop-Location
Push-Location AgentConsole; docker compose --profile db --profile app --profile full down; Pop-Location
```

`down -v` 會刪除全部資料卷，僅限清場；profile 名稱以 `docker/README.md` 為準。

### 環境變數（完整表見 Architecture §9.4；`.env.example` 只放 `<YOUR_...>` 佔位符）

| 變數 | 服務 | 說明 |
|------|------|------|
| `JWT_SECRET` | backend | 必填，≥32 字元 |
| `SPRING_DATASOURCE_URL`／`_USERNAME`／`_PASSWORD` | backend | 本機 `jdbc:postgresql://localhost:5432/aisdlc` |
| `ENGINE_BRIDGE_URL`、`CONSOLE_ENCRYPTION_KEY` | backend | Bridge 位址；敏感參數 AES-256 金鑰 |
| `BRIDGE_DB_DSN`、`BRIDGE_DB_SCHEMA` | Bridge | 無 DSN＝純檔案模式（🔴 Console 的步驟時間軸與斷點清單會是空的——那兩張表只由 Bridge 的 DB 模式寫入，W7-QA 實測；正式部署一律設 DSN）；schema 預設 `console` |
| `BRIDGE_ALLOWED_PATH_ROOTS`、`BRIDGE_OUTBOUND_ALLOWLIST` | Bridge | 路徑與外呼 allowlist（NFR-SEC-03／04） |
| `NEXT_PUBLIC_API_URL` | frontend | 後端 origin（不含 `/api/v1`）；全棧同源為空 |

## 🚦 閘門清單（各波出口指令與預期輸出：[Implementation_Plan](docs/04_planning/Implementation_Plan.md) §2）

> **閘門對映**（整合輪 116 D-116-05）：SCG-0～3＝規格閘（FSM 可驗）、SCG-4～5＝品質閘；W 波次是交付里程碑簽核，不改名、不取代。對映表見〈文件索引〉開發方法論列（Bridge §8）。

| 服務 | 閘門 |
|------|------|
| engine-bridge | `ruff check`（本目錄與 monorepo 根視角各一次）、pytest、`GET /health`、根層 `TestDirEntryPrimitivesAreAccountedFor`、`docker build` |
| backend | `gradlew clean build` 為 `BUILD SUCCESSFUL`；JaCoCo ≥80%；ArchUnit（domain 不依賴 Spring／JPA）；Flyway＋`ddl-auto=validate` |
| frontend | lint、`tsc --noEmit`、build、vitest（≥70%）、四區塊只在 `app/layout.tsx` 組裝（掃描無輸出） |
| docs | RTM 列數與 PRD 對帳（US 58）；`CLAUDE.md` ≤200 行、`README.md` ≤80 行；新文件不得有「測試摘要字樣＋4 位數字」同行 |

```bash
(cd tools/tests && python -m unittest test_platform_neutral_paths.TestDirEntryPrimitivesAreAccountedFor -v)
ruff check AgentConsole/engine-bridge
```

```powershell
Push-Location tools\tests; python -m unittest test_platform_neutral_paths.TestDirEntryPrimitivesAreAccountedFor -v; Pop-Location
ruff check AgentConsole\engine-bridge
```

## 🔴 本 repo 鐵律（違反＝push 被擋或 CI 紅）

1. 文件、註解、commit 訊息一律繁體中文；文件寫進 `docs/0[1-8]_*/` 對應子目錄（本專案用 02／03／04／06；03 給 SDD 的 TCS：`docs/03_testing/contracts/`）。
2. 所有文字檔 **LF 行尾**（`.ps1` 例外為 CRLF）；`.sh` 含 CR 會被 hook 擋。
3. 開發 agent **不准 commit／push**；主控驗證後 commit。
4. **不准寫真實機密**；`.env.example` 只放 `<YOUR_...>`；pre-commit 有機密掃描。
5. 新 `.sh` 須 shellcheck 乾淨且 `bash -n` 過，且**只給容器內（Linux）用**。
6. 新 Python：`open()`／`read_text()`／`write_text()` 一律帶 `encoding="utf-8"`；`os.replace`／`os.rename`／`shutil.move`／`Path.rename`／`Path.replace` 呼叫點須包 `try/except OSError`；平台專屬 API 罩 `sys.platform`；時間戳一律帶 tz（`datetime.now(timezone.utc)`）；`ruff check` 必須 0 錯。
7. 不准動根層 `CLAUDE.md`、`.claude/`、`tools/`、`.github/`；`AutoClaude/` 與 `AISDLC_SDD/` 只准改 ADR-XPLAT-016 §11 白名單列出的檔（AISDLC_SDD 只准 LATEST 原地改，凍結版一律不碰），白名單外仍禁止、以 `git diff --name-only` 機械核對。
8. 暫存檔放 session 提供的暫存目錄，不放 repo；不自架背景等待後交卷；不再派子 agent。
9. Write 被擋（例如檔名含 report）就改用 Bash heredoc 落檔。
10. 「根因是 X」只是待驗假設，實證後才寫成結論；宣稱「已驗證／通過」必附當回合真跑的輸出。
11. 每完成一支程式立即編譯並跑單元測試，**絕不累積開發**；失敗立即停下修復，禁止跳過或註解掉失敗測試。
12. 完成一項需求就回填 [RTM](docs/06_quality/RTM.md) 該列四格（實作檔／自動測試／E2E 驗證／狀態）；不得刪列、改號、合併列。

## 🔴 跨平台鐵律（下一輪在 Windows 11 ＋ PowerShell 接續；那邊禁用 Bash 工具）

1. **文件指令雙形態**：每段指令皆 bash 區塊＋PowerShell 區塊並列。PowerShell：不准裸 `cd`／`Set-Location`（用 `Push-Location <路徑>; …; Pop-Location` 同行成對）；venv 啟動 `.\.venv\Scripts\Activate.ps1`；Gradle 用 `.\gradlew.bat`；不准 `VAR=value cmd` 前綴（改 `$env:VAR="value"; cmd`）；讀 rc 不接管線。
2. **Python（Bridge）須能在 Windows 跑**：結束子程序用 `proc.terminate()`／`proc.kill()`，不直接 `os.kill(pid, signal.SIGTERM)`；`signal.SIGTERM` 等名稱包 `if sys.platform != "win32"`；Windows spawn 帶 `creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)`；pid 是否存活與行程樹清理用 `psutil`（不用 `os.kill(pid, 0)`）；路徑比對 `Path(...).resolve()` 後再 `os.path.normcase()`；寫檔「寫新檔→（`try/except OSError`）replace」；不用 `fcntl`、`os.fork`、`pty`、unix socket；平台相依處留註解「Windows 行為＝…」。
3. **Shell 腳本只給容器內（Linux）用**；主機側操作用 `docker compose …`，或提供 `.ps1` 對等版（`.ps1` 必須 CRLF；含非 ASCII 加 UTF-8 BOM）。
4. **Git 層**：`gradlew`（LF）與 `gradlew.bat`（CRLF）都入庫；`.sh` 一律 LF；`gradlew` 的索引模式與根層 exec bit 鎖的衝突待主控裁決（ADR-001 D15）。
5. **路徑字面**：文件與程式碼不寫死任何磁碟絕對路徑（例如 macOS 使用者家目錄下的路徑）；一律走環境變數或相對 `AgentConsole/` 的路徑。
6. 交卷時附〈Windows 接續注意〉：列出本塊在 Windows 上尚未驗證的點與驗證指令（PowerShell 形態）；Windows 第一次啟動的檢查清單見 Implementation_Plan §4。

## 📚 文件索引

| 主題 | 文件 |
|------|------|
| 需求與 UI | PRD `docs/01_requirements/Agent_ConsoleUI_PRD.md`（§0 權威）；設計稿 `docs/01_requirements/01.UI_Design/Design_ConsoleUI/README.md` |
| 架構（地圖、契約、資料所有權） | [Architecture.md](docs/02_architecture/Architecture.md)；Bridge 契約在 §10，資料所有權在 §7 |
| 決策與偏離 PRD 清單 | [ADR-001-TechStack-Lock.md](docs/02_architecture/ADR-001-TechStack-Lock.md) |
| 需求追溯（回填義務） | [RTM.md](docs/06_quality/RTM.md) |
| 波次、閘門、Windows 接續、進度帳 | [Implementation_Plan.md](docs/04_planning/Implementation_Plan.md) |
| 兩個被包裝的引擎 | `AutoClaude/CLAUDE.md`、`AISDLC_SDD/CLAUDE.md`；monorepo 根 `CLAUDE.md` |
| 開發方法論（SDD 流程開發本專案自身） | `AISDLC_SDD/AISDLC_SDD_v<LATEST>/workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md` §8（LATEST 現查 `python AISDLC_SDD/scripts/sdd_version.py`）；三件組 `SDD_ACTIVE_VERSION`／`SDD_STATE_DIR`＝`AgentConsole/build/reports/fsm`／`SDD_PROJECT`＝`agentconsole-<slug>`，一功能一鍵、一律從 monorepo 根啟動 session；engine-bridge 可走委派迴圈，backend／frontend 走 SDD session-only 路徑（AT 由 `gradlew test --tests`／`vitest run -t` 自跑並逐字貼證據） |
