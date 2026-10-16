# QA 報告：W5 修復波獨立零信任複驗（W5-QA）

| 項目 | 內容 |
|------|------|
| 版本 | v1.0（W5-QA 產出；供主控收斂使用） |
| 日期 | 2026-10-16 |
| 驗證者 | 獨立 QA（零信任：INFRA／BE／FE 三棒的交卷與三份 RTM 回填的「已驗證」一律不採信，每一列親跑才設 `✅ 已驗證`） |
| 被驗 commit | HEAD `76af7ccf`（契約 v1.2 `c91795eb`、INFRA `559da862`、BE `158bca46`、FE `9c5f556e`） |
| 依據 | 任務書 `docs/04_planning/agent_briefs/W5_QA_Reverify.md`、`W5_OVERVIEW.md`（裁決 C-1～C-22）、契約 `docs/02_architecture/API_Contract_P3-6.md` v1.2（§5 E2E-13、§6.5）、[RTM.md](RTM.md)、W4 報告 [QA_P3-6_E2E_Verification.md](QA_P3-6_E2E_Verification.md) |
| 相關文件 | [RTM.md](RTM.md)（E2E 驗證欄的節號都指向本檔）、`frontend/tests/e2e/README.md`〈W5 複驗〉 |

## 1. 摘要

**結論**：W5 修復波的 10 筆缺陷（DEF-AC-001～010）在真後端、真瀏覽器與 Docker 全棧（經 nginx）下**全部複驗結案**，包含 W4 的 P1（DEF-AC-003：Bridge 映像缺 git）——全棧路徑 A 批次現在不靠任何暫行手段就跑到 `COMPLETED`。契約 v1.2 §5 E2E-13 的 13 列、C-1～C-20 逐條有落點，**沒有發現 W5 新程式的功能缺陷**。新登 **1 筆缺陷（DEF-AC-011，P3）**：以程式控制開啟的對話框按 Esc 關閉後焦點落在 `<body>`，沒有歸還觸發鈕（WCAG 2.4.3；§4.5），已用 `test.fail` 釘住、未修。RTM 364 列（新增 `API-PRJ-06`、`API-MON-08`、`BR-26`）：`✅ 已驗證` **358**、`🟡 部分` 6、`❌ 缺陷` 0、`⬜ 未開始` 0（§8）。最需要主控決定的三件事：

1. **`NFR-9.1-05`（Markdown 預覽 < 100ms）20KB 文件仍是 131ms 中位數**（W4 112ms、C-19 的目標是 < 100ms）：1KB 10ms、5KB 23ms 達標；維持 `🟡`，請裁決驗收口徑（5KB 內達標，或另派一棒優化 20KB；§4.11）。
2. **DEF-AC-011（P3）** 要不要進下一波（修法很小：關閉時歸還焦點；§4.5）。
3. **`INF-VOL-07`（HTTPS）QA 沒有親驗**，維持 `🟡`（主控裁決不追）；RTM 引用的只是 INFRA 的自述。

**本回合實跑的數字**（逐條證據見 §3～§7）：

- 後端 `gradlew clean build`：`BUILD SUCCESSFUL in 1m 42s`，1,501 個測試全數成功（W4 為 1,337）、JaCoCo 指令 96％／分支 84％；前端 `lint`（ESLint＋Prettier）／`tsc`／`build` 皆 rc=0，`vitest` 48 個檔 697 個測試全數通過（Statements 95.58％）；Bridge `ruff` 乾淨（兩個視角）、pytest 326 個通過、4 個略過（Windows 無 symlink 權限）；Bridge 映像 `--no-cache` 重建 rc=0，映像內 `git version 2.47.3`；根層 `TestDirEntryPrimitivesAreAccountedFor` 7 個測試 OK。
- **本機整套 Playwright**（真後端＋假 Brain 版 Bridge＋mock claude，乾淨資料庫，共 150 支）：第 1 次 147 支通過、2 支失敗、1 支未執行（51.3 分鐘）——一支是 Windows 用戶端 `net::ERR_NO_BUFFER_SPACE` 讓單一 JS chunk 沒載入的環境暫態、一支是**我自己的 spec 命名撞到既有 spec 的子字串定位器**（§7.1）；兩者都已處置，**最終整套（乾淨庫、全棧已收）：150 支全數通過（52.2 分鐘）**（§7.2）。
- **Docker 全棧**（映像 `--build`，14 服務 healthy）：`docker.config.ts` **27 支全數通過**（10.7 分鐘；`p8` 11 支，DEF-AC-007／008 的 `test.fail` 已移除並正向通過）；唯讀探查 10 項；**RPO／RTO 演練在「整個 pgdata 目錄不存在」條件下重做：還原 1.7 秒、RTO 8.9 秒、各表列數一致、timeline 1→2**（W4 此條件下 `restore.sh` 失敗）；WAL 7 天清理以真實 crontab 指令對假檔實證（§6）。
- 親驗的新端點與行為：task-totals 與各專案 task-trend 加總逐欄相等（儀表板請求量由每分鐘約 31 次降到 5.0 次）；專案復原（200、三種 409／404／403）；PDF 報表真檔可抽出中文；升級告警跨批次不被吞；執行中刪除 409；手動重試；匯入記錄重開還原警告；批次列表 `bridgeStatus`；traceId 貫穿 Bridge（本機與全棧）；偽造 `X-Forwarded-For` 仍被限流（401×100、429×1）。
- 無障礙：axe 對 16 個頁面狀態**零違規**（W4 為 310 個違規節點）；鍵盤走查六情境通過，找到 DEF-AC-011。

**本輪新增或修改的驗證資產**（皆在 `frontend/tests/e2e/`）：新增 `p9-w5-api`／`p9-w5-bridge`／`p9-w5-ui`／`p9-w5-a11y`／`p9-w5-ui-evidence` 五支真後端 spec（33 支情境）、`pdfText.ts`（無套件 PDF 文字抽取）、`w5.ts`（psql／直連 Bridge／原始回應輔助）、12 張新截圖；修改 `p3`（移除 DEF-AC-001 的 `test.fail` 與手動繞法）、`p5`（告警 subject 帶 runId、PDF 改驗 200 真檔）、`p6`（移除 DEF-AC-002 的 `test.fail`）、`p8`（移除 DEF-AC-007／008 的 `test.fail`，新增 `/api/health`／Cache-Control、深度探針、traceId、偽造 XFF 四個全棧情境）、`task-retry`（新 toast 文案）、`realBackend.ts`、README〈W5 複驗〉；`frontend/.prettierignore` 移除真後端 spec 區塊後已 `npm run format`（純格式變動，`npm run lint` rc=0）。

**主控請知悉**：（a）整套第 1 次暴露的兩個非通過項不是產品缺陷（§7.1）；其中 spec 命名撞名是我方問題，已改名並於乾淨庫重跑；（b）Windows 的 260 字元路徑上限會讓 `E2E_ROOT` 太長的環境在審核「重試」時得 502（觀察 O-22，README 已註明）；（c）`AgentConsole/.env` 已刪、全棧已 `down -v`、本機服務已收（§2.5）；（d）`AutoClaude/.perf_baseline.toml` 在我開始前就是髒檔，不是我改的。

## 2. 環境與啟動

### 2.1 版本與主機

| 項目 | 值 |
|------|----|
| 作業系統 | Windows 11 專業版 10.0.26300（20 個邏輯核心、127.7GB 記憶體）；所有指令用 PowerShell 工具執行（Windows 上禁用 Bash 工具） |
| 被驗 commit | HEAD `76af7ccf`；本波四個 commit：契約 v1.2 `c91795eb`、INFRA `559da862`、BE `158bca46`、FE `9c5f556e` |
| 工具鏈 | Node v22.23.3／npm 10.9.9、OpenJDK 21.0.10、Python 3.11.9（根層 `.venv`）、Gradle 9.8.1、Next.js 16.4.0、Playwright 1.64.1（Chromium 156）、axe-core 4.14.0、Docker 29.5.3／Compose 5.1.4 |
| 資料庫 | PostgreSQL 18.4（`pgvector/pgvector:pg18`；本機 e2e 用單一容器，Docker 全棧用 primary＋replica）；Flyway 在乾淨庫套用 V1～V9 共 9 支遷移（`Successfully applied 9 migrations to schema "console", now at version v9`） |

### 2.2 零信任的做法：三棒的「已驗證」一律不採信

backend jar（`gradlew clean build` 重建，04:11 產出）、前端 standalone（以 `NEXT_PUBLIC_API_URL=http://localhost:18080` 重建並確認內嵌）、Bridge 映像（`docker build --no-cache` 重建）都在驗證前重建。全棧一律 `up --build`：BuildKit 依內容雜湊判斷快取，實測（`stack_up.log` 逐步統計）backend 與 frontend 重建了來源層（各 6 步與 8 步），engine-bridge、postgres-primary、pgbackrest 命中**同內容**的快取（engine-bridge 的快取層就是本輪 `--no-cache` 建出來的）。工作樹與 HEAD 的差別只有我改的測試與文件（`frontend/tests/e2e/**`、`frontend/.prettierignore`、`docs/06_quality/**`），外加不是我改的 `AutoClaude/.perf_baseline.toml`（量測基線檔，不是程式碼）；程式碼面等同 HEAD。三份 `rtm_backfill_W5*.md` 與三棒交卷的實跑數字只當「宣稱」，每一條都自己再跑一次（§3～§7）。

### 2.3 本機 e2e 環境（真後端＋假 Brain 版 Bridge＋mock claude）

埠：PostgreSQL 25433（容器 `qa-pg`；5432 的 `autoclaude_pg` 全程不動）、backend 18080（`e2e` profile）、假 Brain 版 Bridge 18081（`frontend/tests/e2e/support/fake_brain_bridge.py`）、前端 3000（`npm run build` 後 standalone，由 Playwright 的 webServer 起）。啟動順序仍是 **PG → backend → Bridge → 重啟 backend**（backend 先跑 Flyway 建 `console` schema，Bridge 的 DB 模式才有表可用；重啟 backend 是為了讓它的探測環看到 Bridge）。完整步驟與環境變數見 `frontend/tests/e2e/README.md`〈真 Bridge specs〉與本輪新增的〈W5 複驗〉節。本輪另外設了：

- `E2E_RESTART_BACKEND`（停止並重啟 backend 的腳本，「重啟 backend 看 SSE 重連」那支才不會略過）、`E2E_JWT_SECRET`（偽造過期 token）、`E2E_FAKE_BRAIN=1`（路徑 C 的情境才不會略過）。
- 新增的三個環境變數：`E2E_BRIDGE_URL`（直連 Bridge，預設 `http://127.0.0.1:18081`）、`E2E_BRIDGE_LOG`（Bridge 日誌檔，列 12 用）、`E2E_PG_CONTAINER`（資料庫容器名，列 2～3 用 `psql` 改 `deleted_at`）；沒設時對應情境會略過並說明原因。

> 🔴 **Windows 的 260 字元路徑上限（觀察 O-22，本輪新發現）**：`E2E_ROOT` 必須是**短路徑**。Bridge 在工作區內會寫 `workspace\<run uuid>\engine\checkpoints\playbook.checkpoint.<pid>.<uuid 32 碼>.tmp`，比 `ENGINE_WORKSPACE` 根多約 129 個字元；本機 `LongPathsEnabled=0`，根路徑 ≥ 約 131 個字元時，審核「重試」（restore）會讓 Bridge 回 500（`FileNotFoundError`）、console-api 轉成 502。本輪一開始把 `E2E_ROOT` 放在 session 暫存目錄底下（132 個字元），第 4 位數 pid 的那次剛好 260 個字元而踩到；改放磁碟根目錄下的短目錄（約 8 個字元）即消失。這是**環境條件，不是產品缺陷**（正式部署是 Linux 容器的 `/workspace`）；W4 的根路徑短 2 個字元所以沒踩到。已寫進 README〈W5 複驗〉。

### 2.4 Docker 全棧

`AgentConsole/.env` 由 `.env.example` 複製、填隨機測試值（`CONSOLE_ENCRYPTION_KEY` 以隨機 32 位元組的 base64；`MINIMAX_API_KEY` 在 compose 也是必填，用假值；`MINIO_ROOT_USER` 必須不同於 `AWS_ACCESS_KEY_ID`），驗完即刪。起停形態（映像一律加 `--build`，不沿用機器上別人留下的舊映像標籤；快取命中的情形見 §2.2）：

```bash
(cd AgentConsole && docker compose --profile db --profile app --profile full up -d --build --wait)
(cd AgentConsole && docker compose --profile db --profile app --profile full down -v --remove-orphans)
```

```powershell
Push-Location AgentConsole; docker compose --profile db --profile app --profile full up -d --build --wait; Pop-Location
Push-Location AgentConsole; docker compose --profile db --profile app --profile full down -v --remove-orphans; Pop-Location
```

### 2.5 收尾狀態

本輪起的所有東西在交卷前已收掉，證據是收尾後現查的輸出：

- **本機服務**：backend（18080）、假 Brain 版 Bridge（18081）、前端 standalone（3000）、PG 容器 `qa-pg`（25433）全部停止。收尾腳本輸出：`已停止 18080 上的行程樹`、`已停止 18081 上的行程樹`、`埠 3000 沒有監聽者`、`docker stop qa-pg rc=0`；埠 18080／18081／3000／25433（以及全棧的 80）的監聽數皆為 0。
- **行程**：`Get-Process java,node,python`——沒有任何 `java`；剩下的 `node`（Id 13140、14528、29176、29440）與 `python`（Id 28692、29016）全部啟動於 2026-10-15 上午 09:19，早於本輪驗證，不是本輪起的。
- **Docker**：全棧已 `down -v --remove-orphans`（rc=0，沒有任何 `aisdlc*` 卷）；`docker ps` 只剩 `autoclaude_pg`（`healthy`，5432，全程沒碰）；`AgentConsole/.env` 已刪（`Test-Path` 為 False）；我建的映像 `aisdlc-engine-bridge:w5qa` 已 `docker rmi` 刪除。
- **截圖**：被整套與 Docker 全棧改寫的**已追蹤**截圖共 102 張，已用 `git show HEAD:<path>` 的位元組寫回（沒有用 `restore`／`checkout`），寫回後仍有差異的已追蹤截圖 0 張；新的 `p9-*.png` 是未追蹤新檔，保留。
- **無法由我刪除的**：磁碟根目錄下的短 `E2E_ROOT` 目錄（四個子目錄 `projects`、`workspace`、`quota-cache`、`bridge-logs`，已清空內容但目錄本身還在）——環境對含該路徑字面量的 `Remove-Item` 有路徑保護；請主控手動刪除（§11）。

## 3. 閘門與重跑結果（Implementation_Plan §2 W4 出口閘門；本回合自跑，輸出逐字）

| 閘門 | 指令 | rc | 關鍵輸出 |
|------|------|----|---------|
| 後端建置與測試 | `Push-Location AgentConsole\backend; .\gradlew.bat clean build --console=plain; Pop-Location` | 0 | `BUILD SUCCESSFUL in 1m 42s`、`12 actionable tasks: 12 executed`；測試結果行 `Test result: SUCCESS`：1,501 個測試全數成功（0 失敗、0 略過；W4 為 1,337 個，本波新增 164 個）；`checkstyleMain`／`checkstyleTest`／`jacocoTestCoverageVerification` 皆通過 |
| 後端覆蓋率 | `jacocoTestReport` 的 `<tfoot>` | — | 指令覆蓋 96％（未涵蓋 1,674／49,483）、分支覆蓋 84％（未涵蓋 617／4,012）；門檻 80％ |
| 資料庫遷移 | 後端在乾淨庫啟動時 Flyway | — | V1～V9 全 `success`（V8 `import record warnings and options`、V9 `soft delete timestamps` 為本波新增）；JPA `ddl-auto=validate` 通過 |
| 前端 lint | `Push-Location AgentConsole\frontend; npm run lint; Pop-Location`（＝`eslint && npm run format:check`） | 0 | ESLint 無輸出；`Checking formatting...`／`All matched files use Prettier code style!`（NFR-9.4-01 的 Prettier 半邊，本波新增） |
| 前端型別 | `npx tsc --noEmit` | 0 | 無輸出 |
| 前端建置 | `npm run build`（`NEXT_PUBLIC_API_URL=http://localhost:18080`） | 0 | Next.js 16.4.0 編譯成功；20 條路由；standalone 產物內含 `localhost:18080`、不含 `localhost:8080` |
| 前端單元測試與覆蓋率 | `npx vitest run --coverage` | 0 | 48 個測試檔、697 個測試全數通過（W4 為 44 個檔、585 個測試）；Statements 95.58％（1,646／1,722）、Branches 89.63％（1,314／1,466）、Functions 97.4％（451／463）、Lines 97.11％（1,348／1,388）；門檻 70％ |
| 四區塊只在 `app/layout.tsx` 組裝 | 見下方指令 | 0 | **無任何輸出**（另有 vitest 的靜態守衛） |
| Bridge lint | `ruff check AgentConsole\engine-bridge`（本目錄與 monorepo 根視角各一次） | 0 | `All checks passed!`（兩次） |
| Bridge 測試 | `python -m pytest -q`（`BRIDGE_TEST_DSN` 指向本機 PG 容器，DB 整合測試實跑） | 0 | `326 passed, 4 skipped, 1 warning in 236.88s (0:03:56)`；4 個略過都是 Windows 無 symlink 權限（`test_api_validation.py:75`、`test_e2e_edge_cases.py:151`、`test_sdd.py:137`、`test_security.py:132`，與 W4 相同） |
| Bridge 映像（含 git） | `docker build --no-cache -f AgentConsole/engine-bridge/Dockerfile -t aisdlc-engine-bridge:w5qa .`（context 為 monorepo 根） | 0 | 41 秒；build 期 `RUN git --version` 冒煙通過；`naming to docker.io/library/aisdlc-engine-bridge:w5qa done` |
| 映像內 git | `docker run --rm aisdlc-engine-bridge:w5qa git --version` | 0 | `git version 2.47.3`（W4 的映像沒有 git，DEF-AC-003） |
| 根層檔案鎖 | `Push-Location tools\tests; python -m unittest test_platform_neutral_paths.TestDirEntryPrimitivesAreAccountedFor -v; Pop-Location` | 0 | `Ran 7 tests in 2.909s`／`OK` |
| compose 必填金鑰 | `docker compose config`（四種 profile 組合＋dev overlay；§4.6） | 1（缺值）／0（有值） | `required variable CONSOLE_ENCRYPTION_KEY is missing a value: CONSOLE_ENCRYPTION_KEY 必填，openssl rand -base64 32` |
| 本機整套 Playwright | `npx playwright test`（本機 e2e 環境、乾淨資料庫、假 Brain 版 Bridge；§7） | 0（最終）；第 1 次為 1 | 最終整套 **150 支全數通過**（52.2 分鐘；DEF-AC-011 的 `test.fail` 是預期失敗，計入通過）；第 1 次為 147 通過、2 失敗、1 未執行，原因與處置見 §7.1 |
| Docker 全棧 Playwright | `npx playwright test -c tests/e2e/docker.config.ts`（§6） | 0 | 27 支全數通過（10.7 分鐘）：`p8` 11 支（DEF-AC-007／008 的 `test.fail` 已移除，正向通過）＋既有真後端 specs 16 支；0 略過 |
| RTM 計數與文件鎖 | §8 的兩條現查指令與 `python tools\check_pytest_baseline_sites.py` | 0 | `RTM.md` 364 列、`⬜ 未開始` 0 列、`✅ 已驗證` 358 列（現查指令輸出見 §8.2）；`check_pytest_baseline_sites.py` rc=0；`AgentConsole/CLAUDE.md` 164 行（上限 200）、`README.md` 78 行（上限 80） |

四區塊掃描指令（結果：無輸出）：

```bash
grep -rEn 'TopRegion|ToolsRegion|BottomRegion' AgentConsole/frontend/app --include='*.tsx' | grep -v 'app/layout.tsx'
```

```powershell
Get-ChildItem AgentConsole\frontend\app -Recurse -Filter *.tsx | Where-Object { $_.FullName -notlike '*\app\layout.tsx' } | Select-String -Pattern 'TopRegion|ToolsRegion|BottomRegion'
```

## 4. 缺陷逐條結案（DEF-AC-001～011）

W4 登記的 10 筆缺陷（W4 報告 §11）與本輪新登的 DEF-AC-011（§4.5），逐條在**真後端／真瀏覽器**重驗；`test.fail` 預期失敗的釘子（p3 的 DEF-AC-001、p6 的 DEF-AC-002、p8 的 DEF-AC-007／008）在 W5-QA 全數移除，改為正向斷言。結案欄的「親跑」指本回合自己執行並取得輸出。

| 編號 | 級別 | 結案判定 | 證據節 |
|------|------|----------|--------|
| DEF-AC-001 | P2 | 已修，結案 | §4.1 |
| DEF-AC-002 | P3 | 已修，結案 | §4.2 |
| DEF-AC-003 | **P1** | 已修，結案（全棧實證） | §4.3、§6 |
| DEF-AC-004 | P3 | 已修，結案 | §4.4 |
| DEF-AC-005 | P3 | 已修，結案 | §4.5 |
| DEF-AC-006 | P3 | 已修，結案 | §4.6 |
| DEF-AC-007 | P2 | 已修，結案（全棧實證） | §4.7、§6 |
| DEF-AC-008 | P3 | 已修，結案（全棧實證） | §4.8、§6 |
| DEF-AC-009 | P2 | 已修，結案 | §4.9 |
| DEF-AC-010 | P3 | 已修，結案（全棧實證） | §4.10、§6 |
| DEF-AC-011 | P3（**新登**） | **未修**；以 `test.fail` 釘住 | §4.5 |

### 4.1 DEF-AC-001（P2）匯入頁節點編輯對話框：`maxRetries` 為 null

**W4 的缺陷**：AI 解析的任務回 `maxRetries: null`，節點編輯對話框把它顯示成字面「null」，zod 驗證（0～20 的整數）擋住「確定」，樹狀預覽也印「最大重試次數：null」。

**W5-QA 親跑**（`p3-import.spec.ts`，真後端＋假 OpenAI 相容伺服器，e2e profile）：

- 移除 `test.fail`，改為正向斷言：路徑 B 解析後開 `/import?id=…`，樹狀預覽**不含**字面 `null`；開「編輯任務：設定」，欄位「最大重試次數」的值為空字串（W4：`"null"`）；**不改任何欄位**按「確定」→ 對話框關閉、`dirty-notice`（未儲存的編輯）不出現。
- 主流程情境（貼文字→路徑 B→有界閘 422 三條→修正重試→編輯→signoff→confirm→專案全部 signedOff）原本要在編輯對話框先手動清空 `maxRetries` 才過得去（W4 的繞法）；本輪**拿掉繞法**，仍通過。
- p3 整檔 8 支（含本情境；另有路徑 A／B／C、上傳 .md／PDF／DOCX、歷史重開、唯讀、有界閘）與 p5、p6、`task-retry` 三檔改完後合跑，21 支全數通過（約 6 分鐘）；整套內的結果見 §7。
- 整套第 1 次該情境因 `net::ERR_NO_BUFFER_SPACE`（單一 JS chunk 沒載入）逾時，屬環境暫態（§7.1）；單檔重跑 8 支全數通過（4.4 分鐘）；**最終整套（乾淨庫）該情境 799ms 通過**。

**判定**：`US-I-04`、`UI-SCR-06` 由 `❌ 缺陷` 回 `✅ 已驗證`。

### 4.2 DEF-AC-002（P3）設定匯入對「值未變」的項目仍驗 allowlist

**W5-QA 親跑**（`p6-settings.spec.ts`，移除 `test.fail`；契約 §1.5.10、E2E-13 列 6）：

- admin `POST /settings/export`，把得到的檔**原樣** `POST /settings/import`（`model.apiUrl` 現值的主機不在 e2e allowlist）：HTTP 200、`errors=[]`、`applied=0`、`skipped=50`（2 筆 `<encrypted>` 佔位＋48 筆值未變）；W4 為 `errors=[model.apiUrl …]`、`skipped=49`。
- 把 `model.apiUrl` 改成 allowlist 外的主機再匯入：**只有該鍵**進 `errors`（原因含 allowlist／SSRF），其餘 49 筆 `skipped`，且沒有任何值被寫入（匯入後再 `GET` 現值不變）。
- p6 整檔 8 支含在上述 21 支合跑內，全數通過；整套內的結果見 §7。

**判定**：`US-S-06`、`API-SET-09` 由 `❌ 缺陷` 回 `✅ 已驗證`。

### 4.3 DEF-AC-003（P1）Bridge 映像缺 git（C-2、BR-26）

**W4 的缺陷**：`python:3.11-slim` 基底沒有 git，引擎內共 11 處 `subprocess` 呼叫 git；Docker 全棧下任何批次一律 FAILED（`引擎異常結束 exit=1`、`FileNotFoundError: 'git'`）。本機（有 git）、mock 測試、Bridge 的 pytest 全綠，只有全棧真跑才現形——所以這條缺陷的結案證據**必須來自全棧**。

**W5-QA 親跑**，三層證據：

1. **映像層**：`docker build --no-cache` rc=0（41 秒）、build 期 `RUN git --version` 冒煙通過；`docker run --rm aisdlc-engine-bridge:w5qa git --version` 印 `git version 2.47.3`（§3）。
2. **本機深度探針**（`p9-w5-bridge.spec.ts`，兩支）：e2e 環境的 Bridge `GET /health/deep` → **200**，`checks.git.version` 為 `git version …`、`autoclaude`／`workspace` 皆 ok、`db.ok=true`（DB 模式有 DSN 時真的 ping）、回應帶 `X-Trace-Id`，淺層 `/health` 不變；自起第二個 Bridge（埠 18082、純檔案模式）並讓 `PATH` 只剩一個空目錄 → **503**、`status=degraded`、`checks.git.ok=false` 且 `reason` 含 `git`、頂層 `reason` 帶出 `git:`、`autoclaude`／`workspace` 仍 ok、`db.ok=null`（無 DSN 不算失敗）、**淺層 `/health` 仍 200**；再把工作區整個刪掉 → `workspace` 也 503（`reason` 含「工作區不可寫」）且與 git 各自獨立失敗；補回工作區後只剩 git 一項失敗。
3. **全棧**（§6.1、§6.4）：14 服務 healthy、Bridge 的 healthcheck 打 `/health/deep`；路徑 A 全鏈批次沒有任何暫行手段就跑到 `COMPLETED`（`completedSteps=3`、`totalTokensUsed=3720`、`bridge.connected=true`）；容器內移走 git → `/health/deep` 503、淺層 `/health` 仍 200、容器轉 `unhealthy`，還原後回 `healthy`。

**判定**：缺陷結案。`INF-SVC-04`、`INF-DKR-04` 由 `❌ 缺陷` 回 `✅ 已驗證`；新列 `BR-26` 為 `✅ 已驗證`；`INF-HLT-01` 附註後維持 `✅ 已驗證`。

### 4.4 DEF-AC-004（P3）色彩對比不足（WCAG 2.1 AA）

**W4 的缺陷**：axe 對 11 頁報 `color-contrast` 257 個節點（`#edf3e9` 於主色底 `#498428`（12px）4.03:1；`#e4eddf` 於 `#498428`（11px）3.79:1；`#7a8775` 於白底 3.78:1）。

**W5-QA 親跑**（`p9-w5-a11y.spec.ts`，真瀏覽器對真後端；axe-core 4.14.0，規則集 `wcag2a`／`wcag2aa`／`wcag21a`／`wcag21aa`）：16 個頁面狀態，**每一個零違規**——不只 `color-contrast`，是整個 A／AA 規則集（W4 該輪共 310 個違規節點）。16 個狀態：登入頁、總覽（真資料）、專案列表、新建專案表單（Dialog＋Markdown 編輯器）、專案列表（已刪除檢視）、專案詳情、目標詳情、任務詳情（執行歷史與日誌）、執行頁（完成後的日誌與 DAG）、監控頁（圖表、告警、日誌）、執行頁（暫停中、待決審核卡）、設定頁（模型分頁、執行分頁；admin、50 鍵）、匯入頁（上傳檔案、貼上文字、歷史記錄三個分頁）。W4 的 11 頁全數涵蓋，另加已刪除檢視、暫停中審核卡、設定與匯入的分頁。

掃描條件（寫在 `a11y.ts`，與 W4 同一把尺）：視窗拉高到整頁可見（內容區是固定高度內捲動，視窗外的節點 axe 只回 incomplete）、游標移到角落（避免量到 hover 色）、要求減少動態並等現有動畫跑完（避免量到漸變到一半的顏色）；掃描失敗時訊息列出規則與節點。每個情境結尾另斷言瀏覽器主控台沒有錯誤。

W5-FE 的作法（ADR-001 §4 偏離清單已登記）：`frontend/styles/tokens.console.css` 的〈無障礙覆寫〉把當文字用的色彩加深，並新增 `warning-text`／`secondary-text`／`terminal-*` 四個文字專用色；設計稿原值仍在 `tokens.css` 逐字保留，主色 `#498428` 與區塊底色不動。這是**設計決定**（主控裁決 C-18）；QA 只驗結果達標，不評設計。設計若再改色票，必須同時過 `a11y.ts` 這道閘。

**判定**：`UI-A11Y-03` 由 `❌ 缺陷` 回 `✅ 已驗證`。

### 4.5 DEF-AC-005（P3）無障礙結構；鍵盤走查；新登 DEF-AC-011（P3）

**DEF-AC-005**：W4 報 `label-content-name-mismatch` 31、`svg-img-alt` 18、`list` 1、`listitem` 3。上述 16 個頁面狀態同一輪 axe 掃描中這四條規則**全為 0 個節點**。**判定**：`UI-A11Y-01` 由 `🟡` 升 `✅ 已驗證`（W4 的缺口就是這四類結構問題）。

**鍵盤走查（UI-A11Y-02：Tab／Enter／Esc、拖曳的鍵盤替代）**——`p9-w5-a11y.spec.ts` 的六支情境，**全程不碰滑鼠**（只用 `page.keyboard`）：

| 情境 | 結果 |
|------|------|
| 登入 | Tab 依序到使用者名稱→密碼→登入鈕，Enter 送出，進入總覽 |
| 跳到主要內容 | 第一個 Tab 停在「跳到主要內容」連結；Enter 後下一個 Tab 落在內容區（不是又繞過整個頂列與側欄） |
| 對話框焦點陷阱 | 以鍵盤開「新建專案」對話框；連按 12 次 Tab，焦點每一次都還在對話框內；Esc 關閉 |
| 目標排序的鍵盤替代 | 拖曳把手 Space 拾起、↑ 移動、Space 放下 → `PUT reorder`、畫面與後端 `sortOrder` 一致（核心、基礎）；重新整理後保持；拾起後按 Esc 不改順序。dnd-kit 的鍵盤感測器在起始鍵之後的下一個 tick 才掛 keydown，按鍵之間要留約 250ms |
| 分頁籤 | 設定頁（6 個分頁）與匯入頁（3 個分頁）：→ 切換並移動焦點與 `aria-selected`，End／Home 到頭尾，Tab 離開 tablist 進入分頁內容 |
| 審核卡與通知鈴 | 執行頁暫停中的審核卡：Enter 開確認對話框、Esc 取消（後端 `pendingReviews` 仍是 1 筆，沒有送出任何決定）、再 Enter 確認後批次續跑到下一個審核點；通知鈴 Enter 開 Popover、Esc 關閉，**焦點回到鈴** |

**🔴 新登 DEF-AC-011（P3）：以程式控制開啟的對話框，Esc 關閉後焦點落在 `<body>`，沒有歸還觸發鈕**（WCAG 2.4.3 焦點順序；ARIA 對話框慣例是歸還）。實測四個對話框全部「未歸還」：「新建專案」（觸發鈕 button「新建專案」→ 焦點 body）、「新增目標」、「刪除專案確認」（觸發鈕 button「刪除專案」）、「審核確認」（觸發鈕 button「通過」）；對照組通知鈴的 Popover 有歸還（焦點回到鈴）。影響：鍵盤與螢幕閱讀器使用者每關一個對話框就要從頁首重新 Tab。已用 `test.fail(DEFECTS_OPEN, …)` 釘在 `p9-w5-a11y.spec.ts`：缺陷還在時整支「預期失敗」＝綠燈（Playwright 的 list 會顯示 ✘，但計入通過），修好後會「意外通過」而變紅，提醒移除該行；設 `E2E_DEFECTS_FIXED=1` 可看真實失敗訊息。QA 對成因的觀察（假設，未讀進 Radix 內部驗證）：`grep` 實查 `frontend/components` 底下，除了 `ui/dialog.tsx` 的匯出宣告，沒有任何地方使用 `DialogTrigger`，也沒有任何 `onCloseAutoFocus`——對話框都由頁面狀態（`open`）控制開關；Radix 的慣例是把焦點還給 Trigger，沒有 Trigger 時就無處可還。建議修法：關閉時由呼叫端記下觸發元素並在 `onCloseAutoFocus` 還焦點，或改用 `DialogTrigger` 包住觸發鈕。

**判定**：`UI-A11Y-02` **維持 `🟡 部分`**——鍵盤主線（登入、跳到主要內容、焦點陷阱、排序替代、分頁籤、審核卡、通知鈴）全數可用，剩 DEF-AC-011 一項。

### 4.6 DEF-AC-006（P3）`CONSOLE_ENCRYPTION_KEY` 預設空（C-16）

**W5-QA 親跑**（`docker compose config`，不起容器；工作目錄 `AgentConsole/`；`.env` 用三種形態各產一份——金鑰那一行不存在、`CONSOLE_ENCRYPTION_KEY=` 留空、有值——每份跑四個 profile 組合，另對 dev overlay 跑「金鑰那一行不存在」與「有值」兩種；跑完即刪 `.env`）：

| 組合 | 金鑰未設 | 金鑰留空 | 金鑰有值 |
|------|----------|----------|----------|
| 無 profile | rc=1 | rc=1 | rc=0（`services: {}`，沒有 profile 就沒有服務） |
| `db` | rc=1 | rc=1 | rc=0 |
| `db`＋`app` | rc=1 | rc=1 | rc=0 |
| `db`＋`app`＋`full` | rc=1 | rc=1 | rc=0 |
| `docker-compose.dev.yml`（extends 載入整份主檔） | rc=1 | — | rc=0 |

缺值時的訊息逐字（八個缺值組合完全相同）：`error while interpolating services.backend.environment.CONSOLE_ENCRYPTION_KEY: required variable CONSOLE_ENCRYPTION_KEY is missing a value: CONSOLE_ENCRYPTION_KEY 必填，openssl rand -base64 32`。W4 的狀況是 compose 放行空值、backend 無限重啟，要等 155 秒才看到「container is unhealthy」；現在在 `config` 階段就失敗，與 `POSTGRES_PASSWORD` 一致。另有兩個實測附帶發現（不是缺陷）：`MINIMAX_API_KEY` 在 compose 也是必填；`MINIO_ROOT_USER` 必須不同於 `AWS_ACCESS_KEY_ID`——產 `.env` 時兩者都要處理。全棧以有金鑰的 `.env` 起，`up -d --build --wait` rc=0（§6.1）。

**判定**：`INF-SVC-03`、`INF-HLT-01` 附註「DEF-AC-006 已修」，狀態維持 `✅ 已驗證`。

### 4.7 DEF-AC-007（P2）backend 暫時性 502 被當成登入失效（C-5）

**W4 的缺陷**：經 nginx 重啟 backend（約 15～40 秒）時，`POST /auth/refresh` 在 backend 尚未就緒時回 502，前端把任何換新失敗都當成登入失效，清掉 session 並導向 `/login`；mock 與本機直連（重啟只有約 10 秒、重連先成功）都看不到。

**W5-QA 親跑**：`p8` 的「重啟 backend」情境（W4 以 `test.fail` 釘住，本輪移除）在**全棧經 nginx**通過（1.6 分鐘）：串流離開 `open`（「重新連線中」）→ backend 容器 `healthy` → 自動重連（至少 1 次 `…/logs` 重連請求）→ 畫面仍是「已暫停」、審核卡仍在、日誌「開始：初始化」「完成：初始化」各恰好一行（事件不重複）→ **沒有被導向 `/login`、session 沒被清除** → 通過審核兩次，批次 **COMPLETED**（`totalTokensUsed=3720`）。細節見 §6.4。

**判定**：缺陷結案。`API-SSE-03`、`NFR-9.2-01` 附註「DEF-AC-007 已修」，維持 `✅ 已驗證`。

### 4.8 DEF-AC-008（P3）nginx `error_log` 洩漏 `access_token`（C-15）

**W4 的缺陷**：上游被切斷時 nginx 在 `[error]` 行印出完整請求行（含 `?access_token=<JWT>`）：81 行 `[error]` 中 16 行含 token 值；`log_format` 管不到 `error_log`。

**W5-QA 親跑**：`error_log … crit`（`grep` 設定行為 `15:error_log  /var/log/nginx/error.log crit;`）；`p8` 的「nginx error log」情境（W4 以 `test.fail` 釘住，本輪移除）通過：重啟 backend 切斷開著的 SSE 之後，本檔用過的每個 JWT 都不出現在 nginx 的 stderr。全部日誌現查：1,883 行，`[error]`、`[crit]`、`[warn]` 皆 0 行，含 `access_token=` 的行 0 行；SSE 存取行的 query 是 `?***`。`nginx -t` rc=0。順帶驗了同批的 O-08（經 nginx `GET /api/health` 回前端自己的 200 `{"status":"ok"}`，W4 回 401）與 O-09（`/_next/static` 的 `Cache-Control` 恰好一份，W4 兩份）。細節見 §6.2、§6.4。

**判定**：缺陷結案。`INF-NGX-04` 附註「DEF-AC-008／O-08 已修」、`INF-NGX-03` 附註「O-09 已修」，維持 `✅ 已驗證`。誠實劃界：`crit` 等級也意味著 nginx 的一般錯誤（例如上游暫時連不上的 `[error]`）不再進日誌；要除錯時須暫時調回 `error` 並清檔（nginx.conf 檔頭〈誠實劃界〉已改寫）。

### 4.9 DEF-AC-009（P2）總覽頁請求扇出（C-1）

**W4 的缺陷**：總覽頁每次載入 31 次請求（29 次 `task-trend`），閒置時每 60 秒再打一輪，穩態每分鐘約 31 次（佔每使用者每分鐘 100 次額度的三成）；專案數 ≥ 30 後快速導覽就出現「請求過於頻繁」。

**W5-QA 親跑**（`p9-w5-ui.spec.ts::C-1／DEF-AC-009`，本機真後端；做法同 W4 §8：以 `page.on("request")` 記錄瀏覽器對 `/api/v1/` 的每一個請求）：資料庫補到 31 個專案（W4 的扇出上限是前 30 個）、先跑完一個批次讓「本週完成」有值、把 viewer 的額度補到 95 再開始量；以 viewer 登入開總覽頁，閒置 130 秒。

| 量測 | W4 | W5（親跑） | 任務書目標 |
|------|----|------------|------------|
| 載入前 10 秒的請求數 | 31（含 29 次 `task-trend`） | **3**：`/projects` 1、`/notifications/summary` 1、`/monitor/task-totals` 1 | — |
| 穩態每分鐘請求數 | 約 31 | **5.0**（120 秒內 10 次：`notifications/summary` 4、`projects` 4、`task-totals` 2） | ≤ 10 |
| `task-trend` 請求 | 每輪 27～29 次 | **0**（整段量測期間任何時刻都沒有） | — |

另驗：畫面的「本週完成」＝同一個視窗的 `GET /monitor/task-totals` 的 `completed`（至少 3，因為剛跑完一個 3 任務的批次）；整段瀏覽器主控台沒有錯誤、畫面沒有「請求過於頻繁」。task-totals 與各專案 `task-trend` 的逐欄加總相等見 §5.1。

**判定**：缺陷結案；`UI-SCR-01` 由 `🟡` 升 `✅ 已驗證`。

### 4.10 DEF-AC-010（P3）`restore.sh` 對不存在的資料目錄失敗（C-17）

**W4 的缺陷**：整個 `pgdata` 目錄不存在（換新磁碟／`pg_data` 卷被刪掉重建＝全新空卷）時，`restore.sh` 於 Step 1 的 `find` 對不存在的目錄 rc=1 中止；更危險的是此時照 README 直接 start primary，PG 映像的入口程序會在空目錄 `initdb` 出全新的空叢集、約 10 秒後顯示 healthy，只看 healthy 的人會誤以為還原成功。

**W5-QA 親跑**（§6.5，Docker 全棧、32.2MB 資料庫）：全備後以 root 刪掉整個 `pgdata` 目錄（卷根 `root:root 0755`），`restore.sh --yes` **rc=0、1.7 秒**；primary 約 6.2 秒 healthy；`console` schema 逐表列數與災難前一致（`projects` 多 1＝全備後的標記專案經 WAL 重播回來、`audit_log` 多 2＝標記專案寫入與還原後登入，逐筆對過）、`timeline_id` 1→2、`pgbackrest check` rc=0；RTO 8.9 秒。安全檢查仍在：primary 在跑時 `restore.sh --yes` 拒絕（rc=1）。README〈4.3〉的「還原後核對資料列數」三項核對（逐表精確列數、`timeline_id`、`pgbackrest check`）都照做並貼了輸出。

**判定**：缺陷結案。`INF-DR-16`、`NFR-9.3-03` 附註後維持 `✅ 已驗證`。W5-INFRA 另寫的「整個 pgdata 刪掉直接 start」危險面（約 10 秒 healthy、0 表、timeline 1）QA 沒有重現——README 的核對判準以上述真實還原的結果（timeline 2、各表列數）為對照，已足夠區分。

### 4.11 NFR-9.1-05 Markdown 預覽更新時間（C-19：去抖；目標 20KB 文件 < 100ms）

**W5-QA 親跑**（`p9-w5-ui-evidence.spec.ts::NFR-9.1-05`，Chromium，新建專案對話框的 Markdown 編輯器）：以 `MutationObserver` 觀察預覽區，從「寫入編輯器值並送出 `input` 事件」到「預覽區最後一次 DOM 變動」（之後 150ms 內無變動即視為穩定）；內容是重複的區塊（標題、粗體／斜體／行內碼／連結、核取清單、GFM 表格、python 程式碼區塊）；每種大小量 7 次取中位數。

| 內容大小 | 7 次樣本（ms） | 中位數 | 最大 | W4 | W5-FE 自報 |
|----------|---------------|--------|------|----|-----------|
| 1KB | 28、10、9、9、10、9、10 | **10ms** | 28ms | 12ms | — |
| 5KB | 26、28、22、22、28、23、20 | **23ms** | 28ms | 29ms | — |
| 20KB | 131、127、144、137、123、138、122 | **131ms** | 144ms | 112ms | 149ms |

另兩次量測的 20KB 中位數：整套第 1 次 125ms（最大 133ms）、先前單獨跑 129ms（最大 142ms），同一量級；1KB、5KB 兩次也都是 10ms、23ms 上下。

**判定**：1KB 與 5KB 遠低於 100ms（說明欄與通過標準的常見大小都在 5KB 內）；**20KB 仍高於 100ms**（中位數 131ms，比 W4 的 112ms 還慢；原因 QA 沒有追——一個待驗假設是這個量法「從貼入到預覽穩定」把去抖的等待也算進去了）。需求原文「Markdown 渲染小於 100ms」沒寫大小，所以 `NFR-9.1-05` **維持 `🟡 部分`**，並列入〈給主控的提醒〉待裁決：接受「5KB 內達標」為驗收口徑，或另派一棒優化 20KB 路徑。不另登缺陷——這是 W4 已登記的〈與設計稿差異〉（W4 報告 §13），本輪只是重量並確認數字。

### 4.12 設計系統與覆蓋層：真瀏覽器逐項證據（`✅ 實作+測試` 5 列升級）

`p9-w5-ui-evidence.spec.ts` 對真後端逐項量測（computed style、`getAnimations()`、bounding box），不是單元測試的樣式字串比對：

| 需求 | 親跑的量測結果 |
|------|----------------|
| `UI-DS-04` 僅用 Lucide 線性圖示 | 11 個頁面狀態逐頁普查（svg 總數／Lucide／圖表或編輯器工具列）：總覽 23／22／1、專案列表 33／33／0、新建專案對話框 79／39／40、專案詳情 24／24／0、目標詳情 20／20／0、任務詳情 24／24／0、執行頁（完成）25／25／0、執行頁（暫停中審核卡）33／33／0、監控頁 24／22／2、設定頁 52／52／0、匯入頁 20／20／0；**全部 `fill: none`、`stroke-width: 1.5px`；0 個 emoji、0 個 `<img>`**。已知例外：新建專案對話框的 Markdown 編輯器工具列有 40 個 svg 是 `@uiw/react-md-editor` 套件自帶的圖示（不是 Lucide）；總覽與監控頁各 1～2 個是圖表 svg |
| `UI-DS-06` 動效規範 | hover：主色鈕（「新建專案」）底色 `rgb(73,132,40)`→`rgb(51,106,41)`（primary-strong）、名稱連結字色 `rgb(42,54,38)`→`rgb(73,132,40)`（主色字）、導覽項底色透明→`rgb(228,239,217)`（tertiary）；三者 `transform` 皆 `none`、`box-shadow` 皆 `none`、`getBoundingClientRect` 不變（版面不位移）；ghost 鈕 hover 不位移。過場組合只有 0.15 秒（`color`／`opacity`，Tailwind 預設曲線）、0.2 秒（`all`，ease-out）、0.4 秒（進度條與圖表柱的 `width`／`height`，`cubic-bezier(0.4, 0, 0.2, 1)`），沒有任何含 `transform` 的過場宣告；執行中專案的狀態點 `wg-blink` 1400ms 無限循環（`getAnimations()` 取得，`iterations=Infinity`）；進度條 `width` 0.4 秒。註：暫停中批次的專案狀態是 READY（契約 §3.5.2），要看到 EXECUTING 的呼吸點得用 26 個任務的長批次撐住（mock claude 沒有慢步驟旋鈕，O-21） |
| `UI-DS-07` 狀態中文標籤與顏色 | 專案：執行中＝`rgb(73,132,40)`（`--color-primary`，呼吸）、草稿＝`rgb(95,107,90)`（`--color-text-muted`）、就緒＝`rgb(128,177,85)`（`--color-secondary`）、完成＝`rgb(73,132,40)`（`--color-primary`）、失敗＝`rgb(184,67,63)`（`--color-error`，W5-FE 無障礙覆寫後的值）；目標頁的任務：待人工＝accent、待處理＝disabled、完成＝primary；執行頁批次：已完成／失敗／已暫停；標籤文字逐字比對 |
| `UI-OVL-02` Toast | 水平中心對視窗中線偏差 **0.0px**、底緣距視窗底 **28.0px**；連按匯出 CSV、匯出 PDF：取樣 22 次、訊息序列 2 種，任何一次取樣宿主內都只有一則（後來的取代先前的）；成功 toast 存續 2905ms（規格 2400）、錯誤 toast 6496ms（規格 6000）——量測含 Playwright 輪詢與離場過場，精度約 ±0.5 秒，斷言區間為規格值 ±1.2 秒，不是精準計時 |
| `UI-OVL-03` 載入 Skeleton／spinner | 以 route 把 `GET /projects` 與專案詳情的回應各延遲 1.8 秒模擬載入慢：列表 Skeleton 的 computed style 為 `animation-name: wg-pulse`、1.4s、`ease-in-out`、`infinite`、`aria-hidden="true"`；詳情的頁面骨架 `aria-busy="true"`、名稱「頁面載入中」；匯入解析（假 OpenAI 相容伺服器延遲 1.5 秒）時置中 spinner：`wg-spin`、0.8s、`linear`、`infinite`、角色 `status` 名稱「AI 解析中」，並有說明文字「AI 解析中」；載入完成後 Skeleton、頁面骨架與 spinner 都消失 |

**判定**：`UI-DS-04`、`UI-DS-06`、`UI-DS-07`、`UI-OVL-02`、`UI-OVL-03` 由 `✅ 實作+測試` 升 `✅ 已驗證`。

## 5. 契約 v1.2 §5 E2E-13 與 C-1～C-22 逐條

E2E-13 是 SA 寫進契約的 W5 最低驗證矩陣（13 列）。下表給每列的落點與結果；細節在 §5.1 以後。「本機」＝真後端（e2e profile）＋真 Bridge＋mock claude；「Docker」＝全棧經 nginx（§6）。

| 列 | 情境（裁決） | 驗證落點 | 結果 |
|----|--------------|----------|------|
| 1 | task-totals 與 task-trend 加總一致（C-1） | 本機 `p9-w5-api`；儀表板 `p9-w5-ui` | 通過（§5.1、§4.9） |
| 2 | 專案復原（C-3） | 本機 `p9-w5-api`、`p9-w5-ui` | 通過（§5.2） |
| 3 | restore 的錯誤路徑（C-3） | 本機 `p9-w5-api` | 通過（§5.2） |
| 4 | PDF 報表（C-4） | 本機 `p9-w5-api`；`p5-monitor` | 通過（§5.4） |
| 5 | refresh 暫時失敗不登出（C-5） | Docker `p8` | 通過（§4.7） |
| 6 | 設定原樣匯入（C-6） | 本機 `p6-settings` | 通過（§4.2） |
| 7 | escalation 跨批次不被吞（C-7） | 本機 `p9-w5-api`（兩支）；`p5-monitor` | 通過（§5.7） |
| 8 | 執行中刪除（C-8） | 本機 `p9-w5-api`、`p9-w5-ui` | 通過（§5.8） |
| 9 | 手動重試（C-9） | 本機 `p9-w5-api`、`p9-w5-ui`、`task-retry` | 通過（§5.9） |
| 10 | 匯入記錄重開（C-10） | 本機 `p9-w5-ui` | 通過（§5.10） |
| 11 | 批次列表 `bridgeStatus`（C-11） | 本機 `p9-w5-api`、`p9-w5-ui` | 通過（§5.11） |
| 12 | traceId 貫穿（C-12） | 本機 `p9-w5-api`；Docker `p8` | 通過（§5.12） |
| 13 | Bridge 深度探針（C-2） | 本機 `p9-w5-bridge`；Docker `p8` | 通過（§4.3） |

節號對應 E2E-13 的列號：§5.1＝列 1、§5.2＝列 2～3、§5.4＝列 4、§5.7～§5.12＝列 7～12；列 5、6、13 的細節在上表所指的 §4.7、§4.2、§4.3。

### 5.1 列 1｜task-totals（C-1、API-MON-08；本機）

`p9-w5-api.spec.ts`：建三個專案（A1、A2 各 3 個任務全成功；B 的 T2 帶 `[FAIL_ME]` 會失敗並重試），各以 Level 4 跑一批到終態；取視窗 `[from, to)` 後，`GET /monitor/task-totals` 的 `started`／`completed`／`failed`／`retried` **逐欄等於**三個專案 `GET …/task-trend?bucket=DAY` 各桶加總（斷言有鑑別力：`completed` 恰為 7＝3＋3＋B 的 T1；`failed`、`retried` 至少 1；`projectsCounted` 恰為 3；回應鍵集合為 `from`／`to`／`started`／`completed`／`failed`／`retried`／`projectsCounted`）。viewer／operator／admin 皆 200、未認證 401。**軟刪專案不計**：刪掉 A2 後同視窗 `completed` 少 3、`projectsCounted` 少 1。**400 三條**：缺 `from`（`errors[0].field=from`）；視窗超過 92 天（reason `時間範圍不合法`、`errors[0].field=to`、`details.maxDays=92`）；`from` 不早於 `to`；剛好 92 天則是 200。儀表板改打這一支的請求量見 §4.9。

### 5.2 列 2～3｜專案復原（C-3、API-PRJ-06、NFR-9.3-04；本機）

`p9-w5-api.spec.ts`（兩支）：先單獨刪 T2、再單獨刪 G2（連同 T3）、再刪專案 → 詳情 404；`GET /projects?deleted=true` 含該專案且 `deletedAt` 為剛才、一般清單不含；`POST /projects/{id}/restore` → **200**，`status` 與刪除前相同；連帶軟刪的目標 G1 與任務 T1 **回來**，專案刪除前就單獨刪掉的 T2、G2、T3 **不回來**；復原後一般清單又列得到、已刪除清單不再有；`console.audit_log` 恰有一筆 `POST …/restore`、200、操作者 operator。錯誤路徑：① 沒被刪的專案 restore → **409 `project_not_deleted`**；② 以 SQL 把 `deleted_at` 改到 31 天前再 restore → **409 `restore_window_expired`**（`details.retentionDays=30`），且該專案仍是 404（不會因為復原失敗而復活）；③ 隨機 uuid → **404**；④ viewer 呼叫 restore → **403 `ACCESS_DENIED`**；viewer 查已刪除清單 403。UI（`p9-w5-ui::C-3`）：列表的「已刪除」篩選、卡片顯示已刪除標籤與刪除時間、復原按鈕與 toast（帶目標與任務數）、復原後回一般清單看得到；VIEWER 沒有「已刪除」鈕。清除排程 `console.retention.purge-enabled` 預設關閉，屬單元測試範圍（BE 的單元測試，後端 1,501 個測試的一部分，§3）；QA 沒有在 e2e 開啟它。

### 5.4 列 4｜PDF 報表（C-4、US-M-07、API-MON-07；本機）

`p9-w5-api.spec.ts`：`GET …/report?format=pdf`（`Accept: application/pdf`）→ **200**、`Content-Type: application/pdf`、`Content-Disposition` 為 `attachment; filename="monitor-report-<專案 id 前 8 碼>-<yyyyMMdd>-<HHmm>.pdf"`；本文以 `%PDF-` 開頭、結尾含 `%%EOF`、大小超過 5KB（內嵌 CJK 字型子集）。QA 自寫的**無套件 PDF 文字抽取器**（`frontend/tests/e2e/pdfText.ts`：Flate 解壓、`ToUnicode` CMap 還原；PDFBox 的 2 位元組字形編號在整串位元組都是 ASCII 時會寫成含 NUL 的字面字串，否則十六進位）抽得出：標題「`<專案名> 監控報表`」、「時間範圍：」「範圍：全部批次」「產生時間（UTC）：」、四個區段標題 `summary`／`runs`／`tasks`／`alerts`、`totalTokens` 的值 3720、**中文目標與任務名**（基礎、核心、初始化、設定、實作）、alerts 區段的「（無資料）」。CSV 同四區段且 `totalTokens,3720`。`runId` 指定單一批次時範圍行以 runId 為值；`Accept: text/csv` 搭 `format=pdf` 仍回 PDF（以 `format` 為準）；`format=docx` → 400「不支援的報表格式」；不存在的專案 404；未認證 401。不再有 501。UI：監控頁「匯出 PDF」下載、檔名取自 `Content-Disposition`（`p5-monitor`、`monitor.mock`）。

### 5.7 列 7｜escalation 跨批次不被吞（C-7；本機）

`p9-w5-api.spec.ts`（兩支）：① 同一專案連續兩批都在 `G1-T1` 失敗、**不確認**第一批的 `ENGINE_ESCALATION` 告警：第二批照樣新增，`GET …/alerts` 共兩列，`subject` 為 `step:<runId1>:G1-T1`、`step:<runId2>:G1-T1`，兩列都未確認（W4：第二批被未確認的舊告警吞掉）。② 同批次內同一步驟再次升級仍被去重：第二步失敗 → 審核 RETRY（204，回應沒有 `X-Follow-Up-Run-Id`＝同批次還原重跑）→ 再失敗並建立第二個審核項，但 `ENGINE_ESCALATION` 告警仍只有 `step:<runId>:G1-T2` 一筆。`p5-monitor` 的告警情境同步改為 `step:<runId>:G1-T2`。附註：第一步失敗的 RETRY 會改開後續批次（沒有還原點，契約 §1.2.10），所以②用第二步失敗來驗同批次。

### 5.8 列 8｜執行中刪除（C-8；本機）

`p9-w5-api.spec.ts`：專案有 `RUNNING`／`PAUSED` 批次時（Level 1，5 個任務，第一步後暫停），`DELETE /goals/{尚未開始的目標}`、`DELETE /tasks/{尚未開始的任務}`、`DELETE /tasks/{已完成的任務}` 一律 **409 `project_executing`**，`details` 帶 `projectId` 與 `runId`；啟動執行被擋則是另一組中文 reason（「專案正在執行中」或「同專案同路徑已有執行中的批次」，契約 §0.3 第 5 點，兩者不可混用）；取消批次進入終態後同一請求 **204**。UI（`p9-w5-ui::C-8`）：PAUSED 批次時在目標頁刪除 → 確認對話框**內**顯示白話原因且**不關閉**；取消批次後同一操作成功。

### 5.9 列 9｜手動重試（C-9；本機）

`p9-w5-api.spec.ts`：`maxRetries=1` 的 ESCALATED 任務連續兩次 `POST /tasks/{id}/retry` 都 **200**、狀態回 QUEUED、`retryCount` 每次增加且**大於 `maxRetries`**，不回 409（第二次前讓它再失敗一次）。UI（`p9-w5-ui::C-9`、`task-retry.spec.ts`）：按「重試」→ toast「手動重試第 N 次（不計入自動重試上限 M）」。

### 5.10 列 10｜匯入記錄重開（C-10；本機，需假 Brain Bridge）

`p9-w5-ui.spec.ts`：路徑 C 解析出 2 個 `passcriteria_placeholder` 警告；`GET /import/{id}` 帶**相同**的 `warnings[]` 與等於請求的 `parseOptions`；UI 用網址 `/import?id=…` 重開，黃色提示與自治等級、執行路徑、補充說明都還原；被有界閘擋下的重新解析（補充說明帶 `GATE_MAX`）改寫 `parseOptions` 但**保留** `warnings`；`PUT result` 補齊通過標準後 `warnings` 以重算值覆寫（清空）、`parseOptions` 不動。發現：假 Brain 只看內容文字、不看 `additionalPrompt`，所以「被有界閘拒絕的重新解析」改用路徑 B＋FakeLlm 的 `GATE_MAX` 補充說明來造。

### 5.11 列 11｜批次列表 `bridgeStatus`（C-11；本機）

`p9-w5-api.spec.ts`：Level 4 的 5 任務批次執行中呼叫 `pause` → 回應 `status=RUNNING`、`bridgeStatus=PAUSING`，列表立即列出 `RUNNING/PAUSING`，步驟邊界後變 `PAUSED/PAUSED`；另一專案執行中 `cancel` → `RUNNING/CANCELLING`，終態後 `CANCELLED`；所有終態批次的 `bridgeStatus` 與 `status` 同名。UI（`p9-w5-ui::C-11`）：以 `MutationObserver` 捕捉到執行頁的「暫停中」晶片（`bridgeStatus=PAUSING`，`status` 仍 RUNNING），到步驟邊界後晶片消失、顯示已暫停。

### 5.12 列 12｜traceId 貫穿 Bridge（C-12、NFR-9.4-04；本機）

`p9-w5-api.spec.ts`（Bridge 以 `BRIDGE_LOG_DIR` 啟動並寫 `bridge.log`）：`POST /projects/{id}/execute` 的回應標頭 `X-Trace-Id` 與封包 `traceId` 同值；Bridge 日誌出現 `trace_id=<該值> ` 的 `POST /autoclaude/runs`（201）那一行，且同一個 trace id 還貫穿該批次的其他 Bridge 請求（至少 2 行）；Bridge 日誌**每一行**（含啟動行、uvicorn 存取行、引擎匯入警告）都有 `trace_id` 欄位；直連 Bridge `GET /health` 不帶標頭 → 回應帶自產的 uuid4 `X-Trace-Id`，帶合法標頭則原樣回帶並出現在 `GET /health` 那一行日誌。Docker 側（容器 stderr 與卷內 `bridge.log` 各一份、backend 卷內 `console.log` 為 JSON 行）見 §6。一個小發現（P4 觀察）：Bridge 記錄「未處理例外」的那一行 `trace_id` 是 `-`（tracing 中介層在 uvicorn 記例外之前已重設 contextvar）。

### 5.13 C-13｜KPI 環形（UI-KPI-01／02；主控裁決）

依 ADR-001 §4 偏離清單與 §5 G-20（D11 設計稿為準）：PRD §5.4.2 寫的「環形」以設計稿畫面 8 的數值卡為準；`p5-monitor.spec.ts::M1` 對真後端驗證數值卡與 delta（專案完成率 100.0％）。`UI-KPI-01`、`UI-KPI-02` 依裁決改 `✅ 已驗證`。

### 5.14 C-14｜追蹤鏈視圖（US-M-09；主控裁決）

設計稿與契約皆無獨立視圖，以批次下拉＋事件時間軸＋日誌查詢涵蓋（契約 §4.3 M-12）；`p5-monitor.spec.ts::M2` 對真後端驗證從啟動追到完成。`US-M-09` 依裁決改 `✅ 已驗證`。

### 5.15 其餘 C-x 與 O 項的落點

| 裁決 | 落點 |
|------|------|
| C-2 Bridge 深度探針 | §4.3、§6（BR-26） |
| C-5 換新失敗語意 | §4.7、§6 |
| C-6 設定原樣匯入 | §4.2 |
| C-15 nginx（error_log、`/api/health`、Cache-Control） | §4.8、§6 |
| C-16 compose（金鑰必填、`LOG_DIR`、`CONSOLE_INTERNAL_PROXIES`） | §4.6、§6 |
| C-17 還原腳本（空卷） | §4.10、§6 |
| C-18 無障礙 | §4.4、§4.5 |
| C-19 前端規範與效能（Prettier、預覽去抖） | §3（`npm run lint` 含 Prettier）、§4.11 |
| C-20 文件說明（O-06、O-16） | `docker/README.md` 有〈12 正式部署前必做（預設帳號、內部端點）〉〈13 反向代理與 X-Forwarded-For 信任〉〈14 啟用 HTTPS〉〈15 日誌與追蹤碼〉四節——QA 只確認章節存在，沒有逐字審閱內容；這是文件處置、無行為變更，不另驗 |
| C-21／C-22 契約回寫（SA） | 不在 QA 範圍（SA 契約 v1.2 §6.5） |

## 6. Docker 全棧（經 nginx；映像 `--build`、乾淨資料庫）

### 6.1 起動

```bash
(cd AgentConsole && docker compose --profile db --profile app --profile full up -d --build --wait)
```

```powershell
Push-Location AgentConsole; docker compose --profile db --profile app --profile full up -d --build --wait; Pop-Location
```

結果：`up -d --build --wait` **rc=0，耗時 118 秒**；14 個長駐服務全數 `healthy`（backend、engine-bridge、frontend、nginx、grafana、prometheus、redis、minio、pgadmin、pgbackrest、postgres-primary、postgres-replica、兩個 postgres-exporter）。W4 的同一動作要靠暫裝 git 才能讓批次跑起來；本輪沒有任何暫行手段。

### 6.2 唯讀探查（起動後、跑情境前；指令與逐字輸出）

| 項目 | 指令（容器名為 compose 的 `container_name`） | 輸出 |
|------|-----------------------------------------------|------|
| Bridge 映像內的 git（DEF-AC-003、INF-DKR-04） | `docker exec aisdlc-engine-bridge git --version` | `git version 2.47.3`（`/usr/bin/git`） |
| Bridge healthcheck 定義（INF-HLT-01） | `docker inspect -f '{{json .Config.Healthcheck.Test}}' aisdlc-engine-bridge` | `["CMD","python","-c","import sys,urllib.request as u; sys.exit(0 if u.urlopen('http://127.0.0.1:8081/health/deep', timeout=9).status == 200 else 1)"]`；狀態 `healthy` |
| `/health/deep`（容器內，DB 模式） | `docker exec aisdlc-engine-bridge python -c <GET 腳本> http://127.0.0.1:8081/health/deep` | `200 {"status":"ok","checks":{"git":{"ok":true,"version":"git version 2.47.3"},"autoclaude":{"ok":true,"version":"0.1.0"},"workspace":{"ok":true},"db":{"ok":true}}}`（有 DSN 時 `db.ok` 是真的 ping：`true`） |
| nginx 設定語法（INF-NGX-04） | `docker exec aisdlc-nginx nginx -t` | `syntax is ok`／`test is successful`，rc=0 |
| nginx `error_log` 等級（C-15、DEF-AC-008） | `docker exec aisdlc-nginx sh -c "grep -n '^error_log' /etc/nginx/nginx.conf"` | `15:error_log  /var/log/nginx/error.log crit;` |
| 經 nginx 的前端自身健康（O-08） | `GET http://localhost/api/health`、`GET http://localhost/nginx-health` | `HTTP 200 {"status":"ok"}`（W4：被反代到 backend 回 401）；`HTTP 200 ok` |
| `_next/static` 的 Cache-Control（O-09） | `GET http://localhost/_next/static/chunks/<首頁引用的 css>` | `HTTP 200`；`Cache-Control` 份數＝**1**，值 `public, max-age=31536000, immutable`（W4：兩份） |
| 檔案日誌設定（C-16、INF-VOL-06） | `docker exec aisdlc-backend printenv LOG_DIR`；`docker exec aisdlc-engine-bridge printenv BRIDGE_LOG_DIR` | 皆 `/app/logs`；`app_logs` 卷內有 `bridge.log`（`bridge` 使用者寫入）與 `console.log`（`spring` 使用者寫入），兩個容器各自看得到兩個檔 |
| 信任代理（C-16、O-20） | `docker exec aisdlc-backend printenv CONSOLE_INTERNAL_PROXIES` | `172\.31\.250\.(?:[2-9]\|[1-9]\d\|1\d\d\|2[0-4]\d\|25[0-4])`（只信 compose 子網的 .2～.254；閘道 .1＝主機端進來的請求位址，刻意排除） |
| 固定子網（O-20） | `docker network inspect aisdlc_backend-net` | `172.31.250.0/24`，gw=`172.31.250.1` |

自建映像的建立時間（`docker images`）：`aisdlc-frontend:dev`、`aisdlc-backend:dev` 約 18 分鐘前（來源層重建）；`aisdlc-engine-bridge:dev` 約 2 小時前（命中本輪 `--no-cache` 建出的同內容快取層）；`aisdlc-pgbackrest:pg18`、`aisdlc-postgres-primary:pg18` 命中先前同內容的快取。

### 6.3 Docker 整套 Playwright（`docker.config.ts`）

```bash
(cd AgentConsole/frontend && E2E_API_URL=http://localhost npx playwright test -c tests/e2e/docker.config.ts --reporter=list)
```

```powershell
Push-Location AgentConsole\frontend; $env:E2E_API_URL = "http://localhost"; npx playwright test -c tests/e2e/docker.config.ts --reporter=list; Pop-Location
```

**結果：27 支全數通過（10.7 分鐘，rc=0）**——`p8-docker-stack.stack.ts` 11 支（W4 為 7 支，其中兩支是 `test.fail`；本輪 DEF-AC-007／008 的 `test.fail` 已移除，改為正向斷言）加既有真後端 specs 16 支（`chart` 1、`crud-flow` 1、`design-system` 3、`shells-and-layout` 6、`signoff` 5；全棧是乾淨資料庫、經 nginx 同源）。W4 為 23 支。

| p8 情境 | 耗時 | 驗的是什麼（對應） |
|---------|------|--------------------|
| 入口 | 1.0 分 | 首頁 200、`/nginx-health` 200、`/actuator/health` 被封 403、無 token 的 `/api/v1/projects` 401；未登入導向 `/login?next=%2Fprojects`，UI 登入後導回 |
| **路徑 A 全鏈（UI）** | 20.4 秒 | 凍結規格（寫進 Bridge 容器的 `/workspace`）→ 規格驅動解析（`parse-path` 為「規格驅動（SDD）」、三個合約任務）→ signoff → confirm → 執行 Level 4 → 進度逐步前進（至少 3 個不同的進度值，不是一次從 0 跳到 3）→ **COMPLETED**：`completedSteps=3`、`totalSteps=3`、`totalTokensUsed=3720`、`bridge.connected=true`、整段無瀏覽器主控台錯誤。**這是 DEF-AC-003 的結案證據**（§6.4） |
| SSE 經 nginx | 11.3 秒 | 暫停中的串流先送重播框架：21 個框架，到達時間 19、19、20、20…（全部在 20ms 內），連線仍開著、不等到結束才一次吐出（`proxy_buffering off` 生效） |
| **重啟 backend** | 1.6 分 | DEF-AC-007／C-5／E2E-13 列 5：見 §6.4 |
| 上傳大小經 nginx | 0.8 秒 | 剛好 10MB → 201；超過 10MB 但封裝後仍小於 11MB → 後端 413「檔案超過 10MB 上限」；12MB → nginx 自己擋下的 413（HTML） |
| nginx access log | 49ms | `access_token` 的值不出現；SSE 請求只留路徑（`…/logs?*** HTTP`） |
| **nginx error log** | 1.0 分 | DEF-AC-008／C-15：見 §6.4 |
| `/api/health` 與 Cache-Control | 35ms | O-08／O-09：`/api/health` 200 `{"status":"ok"}`；`/_next/static` 資源的 `Cache-Control` 恰好一份 `public, max-age=31536000, immutable` |
| **Bridge 深度探針（全棧）** | 2.7 分 | BR-26／DEF-AC-003／C-2：見 §6.4 |
| **X-Trace-Id 貫穿** | 18.8 秒 | C-12／NFR-9.4-04／INF-VOL-06：見 §6.4 |
| **偽造 X-Forwarded-For** | 2.1 分 | O-20／C-16：見 §6.4 |

### 6.4 缺陷與裁決逐條（Docker 側證據）

**DEF-AC-003（P1）Bridge 映像缺 git → 結案。** 證據鏈：① 映像內 `git version 2.47.3`（§6.2）；② `docker build --no-cache` rc=0、build 期 `RUN git --version` 冒煙通過（§3）；③ 全棧 14 服務 healthy，且 Bridge 的 healthcheck 打的是 `/health/deep`（§6.2）；④ 路徑 A 全鏈批次**沒有任何暫行手段**就跑到 COMPLETED（W4 是 `引擎異常結束 exit=1`、traceback 止於 `FileNotFoundError: 'git'`，要暫裝 git 才跑得動）；⑤ 深度探針的前後對照（下段）。

**BR-26 深度探針（全棧）。** `p8` 該情境在 Bridge 容器內做：容器的 healthcheck 定義含 `/health/deep`、狀態 `healthy`；`git --version` 可執行；`/health/deep` 回 200，`checks.git`／`autoclaude`／`workspace`／`db` 皆 `ok`（DB 模式：`db.ok=true`）；**把容器內的 git 移走**（`mv /usr/bin/git /usr/bin/git.qa-off`，以 root）→ `/health/deep` 回 **503**、`status=degraded`、`checks.git.ok=false`、`reason` 含 `git`，**淺層 `/health` 仍 200**（這正是 DEF-AC-003 當時看不見問題的原因）；容器的 healthcheck 隨之轉 **`unhealthy`**（W4：永遠 healthy）；把 git 還原後 healthcheck 回到 **`healthy`**，`/health/deep` 回 200。整段 2.7 分鐘（含等待 healthcheck 的重試週期），`finally` 區塊保證 git 一定被還原。

**DEF-AC-007（P2）暫時性 502 被當成登入失效 → 結案。** `p8` 的「重啟 backend」情境（W4 以 `test.fail` 釘住，本輪移除）：Level 1 專案暫停在審核卡 → `docker restart aisdlc-backend` → 前端串流狀態點離開 `open`（「重新連線中」）→ 等 backend 容器 `healthy`（容器重啟約 15～40 秒；W4 就是在這段空窗 `/auth/refresh` 回 502 而被登出）→ 串流**自動重連**（至少 1 次 `…/logs` 重連請求）→ 畫面仍是「已暫停」、審核卡仍在、日誌「開始：初始化」「完成：初始化」各**恰好一行**（事件不重複）→ **沒有被導向 `/login`、session 沒被清除** → 通過審核兩次（approve）跑到 **COMPLETED**，`totalTokensUsed=3720`。W4 的結果是 refresh 回 502 後前端清掉 session、導向 `/login`。對應 FE 的 C-5（換新失敗分 `renewed`／`invalid`／`unavailable`，只有 `invalid` 才登出；SSE 以 1→2→4→…→30 秒退避重連）。

**DEF-AC-008（P3）nginx error_log 洩漏 access_token → 結案。** 設定：`error_log … crit`（§6.2）。情境（W4 以 `test.fail` 釘住，本輪移除）：重啟 backend 切斷開著的 SSE（URL 帶 `?access_token=<JWT>`）後，把本檔用過的每個 JWT 拿去比對 `docker logs aisdlc-nginx` 的 stderr，**一個都沒有出現**。全部日誌現查：1,883 行，`[error]`、`[crit]`、`[warn]` 各 0 行，含 `access_token=` 的行 0 行；SSE 存取行的 query 一律是 `?***`。W4 對照：同一情境 81 行 `[error]`、其中 16 行含完整 JWT。

**C-12／NFR-9.4-04／INF-VOL-06（全棧）。** 經 nginx `POST …/execute` 啟動 Level 4 批次，回應的 `X-Trace-Id`（本次為 `74dc4bac-…`）出現在 Bridge 容器日誌的 `POST /autoclaude/runs`（201）那一行，同一個 trace id 在 Bridge 命中 3 行；Bridge 容器 stderr **每一行**都有 `trace_id`；卷內 `/app/logs/bridge.log` 322 行，**每一行**都有 `trace_id`，且含該 traceId；backend 卷內 `console.log` 是 JSON 行（鍵含 `@timestamp`、`@version`、`message`、`logger_name`、`thread_name`、`level`、`level_value`）。這是 W4 的 O-11（Bridge 日誌沒有 traceId）與 INF-VOL-06（卷內沒有日誌檔）的結案證據；§6.2 另見 `app_logs` 卷的兩個檔案與擁有者（`bridge`、`spring` 各自可寫，`:nocopy` 讓 compose 的 create 順序不影響權限）。

**O-20／C-16 偽造 `X-Forwarded-For`。** 先等 62 秒讓主機來源（172.31.250.1）的未認證桶回到整個視窗，然後對 `GET /api/v1/projects` 連打 101 次、**每次偽造不同的 `X-Forwarded-For`**：結果 **401×100、429×1**（W4：101 次全是 401、沒有 429——偽造標頭即換新桶，限流可被繞過）。原因（INFRA 的處置，QA 親驗效果）：compose 把 `backend-net` 固定為 `172.31.250.0/24`，`CONSOLE_INTERNAL_PROXIES` 預設只信該子網的 .2～.254、刻意排除閘道 .1（主機端進來的請求位址）；§6.2 已逐字貼出環境變數與子網。INFRA 的回填說 HEAD 的 backend 當時尚未把 `CONSOLE_INTERNAL_PROXIES` 對應到 Tomcat 的 `remoteip.internal-proxies`，用 Spring 寬鬆繫結的替身驗證；本輪 HEAD 的 backend 已含這個對應（W5-BE；QA 以全棧的效果驗證、沒有讀碼），所以上面的結果是**直接用 `CONSOLE_INTERNAL_PROXIES` 的全棧實測**。`NFR-9.2-06` 狀態維持 `✅ 已驗證`，E2E 欄附註 O-20 已處置。

### 6.5 RPO／RTO 演練：用新的 `restore.sh` 在「整個 pgdata 目錄不存在（全新空卷）」重做（DEF-AC-010、C-17）

演練腳本逐步計時（W4 的演練與 README〈4.3〉同一套程序；本輪的差別是災難條件改成 W4 失敗的那一種）：

```bash
(cd AgentConsole && docker compose exec pgbackrest bash /usr/local/bin/backup-full.sh)
(cd AgentConsole && docker compose stop postgres-primary)
# 以 root 把整個 pgdata 目錄（含目錄本身）刪掉：卷根屬 root:root 0755，postgres 無權重建它＝W4 失敗的條件
(cd AgentConsole && docker run --rm --entrypoint sh -v <pg_data 卷名>:/d aisdlc-postgres-primary:pg18 -c 'rm -rf /d/pgdata; ls -ld /d')
(cd AgentConsole && docker compose run --rm --no-deps pgbackrest bash /usr/local/bin/restore.sh --yes)
(cd AgentConsole && docker compose start postgres-primary)
```

```powershell
Push-Location AgentConsole; docker compose exec pgbackrest bash /usr/local/bin/backup-full.sh; Pop-Location
Push-Location AgentConsole; docker compose stop postgres-primary; Pop-Location
Push-Location AgentConsole; docker run --rm --entrypoint sh -v "<pg_data 卷名>:/d" aisdlc-postgres-primary:pg18 -c 'rm -rf /d/pgdata; ls -ld /d'; Pop-Location
Push-Location AgentConsole; docker compose run --rm --no-deps pgbackrest bash /usr/local/bin/restore.sh --yes; Pop-Location
Push-Location AgentConsole; docker compose start postgres-primary; Pop-Location
```

| 步驟 | 結果 |
|------|------|
| 灌資料 | 經 nginx 的 REST 建 30 個專案（各 1 目標 1 任務）；演練前專案總數 34；`console` schema 逐表列數：`alerts` 0、`audit_log` 181、`checkpoints` 10、`execution_runs` 4、`execution_steps` 20、`flyway_schema_history` 9、`goal_dependencies` 4、`goals` 40、`import_records` 2、`projects` 39、`review_requests` 3、`run_token_samples` 10、`system_config_history` 5、`system_configs` 50、`tasks` 43；timeline 1 |
| 全備 | `backup-full.sh` rc=0、**5.3 秒**（repo1＋repo2 各一份；資料庫 32.2MB，repo2 的備份 3.5MB） |
| RPO | 全備後寫入標記專案 `W5QA-RPO-marker-…`（HTTP 201）：**replica 約 0.3 秒內重播到該 LSN**（`0/180075C8`）；該筆交易所在 WAL 段（`…18`）**約 61.7 秒後歸檔到 repo1**（`archive_timeout=60`，量測含約 2 秒的輪詢誤差）。RPO 目標 1 分鐘：複製面達標；歸檔面受 `archive_timeout` 支配，貼著 60 秒 |
| 宣告災難 | `stop postgres-primary` 0.4 秒；整個 `pgdata` 目錄刪除（`GONE`；卷根 `drwxr-xr-x root root`）0.3 秒 |
| 還原 | `restore.sh --yes`（還原到最新）**rc=0、1.7 秒**：`restore size = 32.2MB, file total = 1357 … restore command end: completed successfully`（W4：Step 1 的 `find` 對不存在的目錄 rc=1 中止） |
| 啟動 | `start postgres-primary` 0.2 秒；**約 6.2 秒 healthy** |
| 服務恢復 | 經 nginx 登入並讀專案列表成功，距 healthy 再 0.1 秒 |
| **RTO** | **宣告災難 → API 讀回還原後資料 ＝ 8.9 秒**（目標 15 分鐘；W4 為 9 秒） |

**資料核對**（README〈4.3〉的必做步驟，不用 healthy 代替）：

| 表 | 演練前 | 還原後 | 判定 |
|----|--------|--------|------|
| `projects` | 39 | 40 | ＋1＝全備**之後**寫入的標記專案，**經 WAL 重播回來**（專案總數 34→35；標記專案在庫內 1 筆） |
| `audit_log` | 181 | 183 | ＋2＝標記專案的 `POST /projects`（201）與還原後登入的 `POST /auth/login`（200），皆在演練前快照之後；查 `occurred_at` 最新兩列已對過 |
| 其餘 13 張表（`alerts`、`checkpoints`、`execution_runs`、`execution_steps`、`flyway_schema_history`、`goal_dependencies`、`goals`、`import_records`、`review_requests`、`run_token_samples`、`system_config_history`、`system_configs`、`tasks`） | — | — | **逐表列數與演練前完全一致** |

另：`timeline_id` **1 → 2**（成功還原會升格新時間軸；全新的空叢集恆為 1）；`pgbackrest --stanza=aisdlc check` rc=0。演練腳本自帶的「逐表列數相同」判斷印出 `False`，原因就是上表 `projects` 與 `audit_log` 兩列的已知差異（腳本只排除了 `projects`）；這兩列各自的差異已逐筆解釋，不是資料遺失。**還原後 `restore.sh` 的安全檢查**：primary 在跑時再跑 `restore.sh --yes` → **rc=1**，`ERROR: primary 仍在接受連線。請先在主機執行：docker compose stop postgres-primary`，primary 不受影響（仍可讀、timeline 仍為 2）。

**判定**：DEF-AC-010 結案；`INF-DR-16`、`NFR-9.3-03` 附註後維持 `✅ 已驗證`。侷限：資料量只有 32.2MB，RTO 不外推到大庫；還原自 repo1（預設），沒有做 `--repo 2` 的還原。

### 6.6 INF-DR-13：WAL 7 天本地複本清理（手動觸發，對假的舊檔驗行為）

做法：取**容器內 crontab 的真實那一行**（不是自擬指令）：`30 3 * * *  find /var/lib/postgresql/wal_archive -type f -mtime +7 -delete >> /var/log/pgbackrest/cron.log 2>&1`（每日 03:30，容器時區 `Asia/Taipei`）；在 `wal_archive` 目錄以 `postgres` 身分（cron 的執行身分）製造 5 個 0 位元組假檔（名稱 `FAKE_…`，`touch -t` 設定年齡），再執行那一行：

| 假檔 | 年齡 | 執行後 |
|------|------|--------|
| `FAKE_00_10d.gz` | 10 天 | **被刪** |
| `FAKE_01_8d2h.gz` | 8 天 2 小時 | **被刪** |
| `FAKE_02_7d12h.gz` | 7 天 12 小時 | 保留 |
| `FAKE_03_3d.gz` | 3 天 | 保留 |
| `FAKE_04_now.gz` | 剛建立 | 保留 |

25 個真實歸檔檔（都不到 7 天）執行前後都是 25 個，**沒有被誤刪**；假檔事後清掉。語意要點：`-mtime +7` 是「超過 7 個整天」，所以 7 天 12 小時的檔案還不會刪、滿 8 天才刪——保留期**不會短於 7 天**（README〈4.1〉寫「7 天前」，實際是「至少 7 天」）。誠實劃界：排程觸發機制（busybox crond 讀 crontab、以 `postgres` 身分執行）沿用 README〈4.1〉的探針工作實測，QA 沒有等到 03:30 的真實觸發。

**判定**：`INF-DR-13` 的缺口（清理行為從未驗證）已補，由 `🟡` 升 `✅ 已驗證`，E2E 欄註明上述劃界。

### 6.7 其他全棧事實

- **還原後的 replica**（README〈4.3〉的警告成立）：演練後 primary 的 `pg_stat_replication` 為 0 行；replica 的日誌印出 `new timeline 2 forked off current database system timeline 1 before current recovery point 0/190000A0` 與 `waiting for WAL to become available`，重播位置停在 `0/190000A0`，primary 已到 `0/1A005520`。但 replica 容器仍是 **`healthy`**——它的 healthcheck 只有 `pg_isready -h 127.0.0.1 -U aisdlc`（見觀察 O-26）。QA 沒有照 README〈5〉重建 replica（驗證完即整套收掉）。
- **`INF-VOL-07` HTTPS**：QA 沒有親驗（主控裁決不追）；只看到 nginx 容器發布 80 與 443 兩個埠、本輪全棧情境皆經 `http://localhost`。維持 `🟡`，E2E 欄註明「INFRA 自述，QA 未親驗」。

## 7. 本機整套 Playwright（真後端＋假 Brain 版 Bridge＋mock claude；乾淨資料庫）

```bash
(cd AgentConsole/frontend && E2E_ROOT=<短目錄> E2E_API_URL=http://localhost:18080 E2E_MODE=standalone E2E_FAKE_BRAIN=1 E2E_JWT_SECRET=<同 backend> E2E_RESTART_BACKEND=<重啟腳本> E2E_BRIDGE_URL=http://127.0.0.1:18081 E2E_BRIDGE_LOG=<bridge.log> E2E_PG_CONTAINER=qa-pg npx playwright test --reporter=list)
```

```powershell
Push-Location AgentConsole\frontend; $env:E2E_ROOT = "<短目錄>"; $env:E2E_API_URL = "http://localhost:18080"; $env:E2E_MODE = "standalone"; $env:E2E_FAKE_BRAIN = "1"; $env:E2E_JWT_SECRET = "<同 backend>"; $env:E2E_RESTART_BACKEND = "<重啟腳本>"; $env:E2E_BRIDGE_URL = "http://127.0.0.1:18081"; $env:E2E_BRIDGE_LOG = "<bridge.log>"; $env:E2E_PG_CONTAINER = "qa-pg"; npx playwright test --reporter=list; Pop-Location
```

整套共 **150 支**（W4 為 108 支）：p9 五檔 33 支（a11y 9、api 10、bridge 2、ui-evidence 6、ui 6）加上其餘既有檔 117 支（比 W4 多 9 支；QA 沒有逐支追溯來源）；單一 worker，從乾淨的資料庫（PG 容器重建、backend 重新跑 Flyway、Bridge 重啟）起跑。

### 7.1 第 1 次整套（HEAD 的 spec 加上我的修改與 p9 五檔；全棧同時在線上）

**結果：147 支通過、2 支失敗、1 支未執行（51.3 分鐘）。** 其中 DEF-AC-011 那支 `test.fail` 是「預期失敗」，Playwright 的 list 顯示 ✘，但計入通過。最慢的檔案：`p4-execute` 11.5 分、`p4b-execute-more` 8.5 分、`p9-w5-ui-evidence` 6.0 分、`p9-w5-ui` 5.6 分、`p9-w5-api` 5.0 分。

三個非通過項逐一診斷（沒有一個是產品缺陷）：

| 項目 | 現象 | 診斷（證據） | 處置 |
|------|------|--------------|------|
| `p3-import` 的 DEF-AC-001 情境（失敗） | 開 `/import?id=…` 後 60 秒逾時，頁面停在「載入中」，頂列與頁尾的連線點都是「檢查中」 | trace 的 network 記錄顯示：頁面 27 個資源只有一個失敗——`GET /_next/static/chunks/0ec7uikna39ld.js` 回 `-1`，`_failureText=net::ERR_NO_BUFFER_SPACE`（Windows 用戶端 socket 緩衝耗盡）；那個 chunk 沒載入，頁面就沒有水合。時間點是全棧剛起完約 2 分鐘。環境暫態，不是產品也不是 spec 邏輯（同一支情境在單獨跑時 774ms 通過） | 單檔重跑 `p3-import.spec.ts`：**8 支全數通過**（4.4 分鐘，DEF-AC-001 情境通過） |
| `p3-import` 的唯讀情境（未執行） | `serial` 描述區塊裡前一支失敗，其後的不執行 | 上一列的連帶 | 同上，重跑通過 |
| `shells-and-layout` 的「手機 390px：側欄變成底部 Tab 導航」（失敗） | `getByRole('link', { name: '儀表板' })` 出現 strict mode violation：解析到 3 個元素 | 其中兩個是**我的** `p9-w5-ui` 建的專案「QA W5 儀表板完成 …」（最近專案導覽與專案列表各一個連結）——`name` 是子字串比對，專案名稱含「儀表板」就撞上側欄的「儀表板」連結。**我方 spec 的命名缺陷**（共用資料庫的狀態汙染），不是產品問題 | 把我建的專案改名（「QA W5 DASH 完成」、「QA W5 DASH 種子 i」），名稱不再含導覽字樣；改完於**乾淨庫**重跑整套（§7.2） |

### 7.2 最終整套（改名後；乾淨庫；Docker 全棧已先收掉，不再有同機網路流量）

做法：先收掉全棧（`down -v`），再把本機環境整個重置——PG 容器重建、E2E 根目錄的四個子目錄清空、backend（跑 Flyway）→ Bridge → 重啟 backend，專案總數 0 起跑——然後跑同一條 `npx playwright test`。

**結果：150 支全數通過（52.2 分鐘，rc=0）**；0 失敗、0 略過、0 未執行。其中 DEF-AC-011 那支是 `test.fail` 的預期失敗（list 顯示 ✘、計入通過），其餘 149 支正向通過。第 1 次失敗的兩支這次：`p3-import` 的 DEF-AC-001 情境 799ms 通過、`shells-and-layout` 的手機 390px 436ms 通過。最慢的檔案：`p4-execute` 12.5 分、`p4b-execute-more` 8.5 分、`p9-w5-ui-evidence` 6.0 分、`p9-w5-ui` 5.6 分、`p9-w5-api` 5.0 分。

各檔支數（合計 150）：`a11y.mock` 3、`chart` 1、`crud-flow` 1、`dashboard.mock` 3、`design-system` 3、`execute.mock` 16、`import.mock` 8、`markdown-editor` 5、`monitor.mock` 9、`notifications.mock` 2、`p3-import` 8、`p4-execute` 12、`p4b-execute-more` 9、`p5-monitor` 4、`p6-settings` 8、`p7-cors-ratelimit` 1、`p9-w5-a11y` 9、`p9-w5-api` 10、`p9-w5-bridge` 2、`p9-w5-ui-evidence` 6、`p9-w5-ui` 6、`projects.mock` 3、`settings.mock` 9、`shells-and-layout` 6、`signoff` 5、`task-retry` 1。

整套輸出裡的證據行（逐字摘錄；§4 各節與 RTM 引用的就是這一次的數字）：

- `[a11y]` 四個對話框 Esc 關閉後焦點都落在 body、未歸還（DEF-AC-011，§4.5）。
- `[dashboard]` 載入（前 10 秒）3 次：`/projects` 1、`/notifications/summary` 1、`/monitor/task-totals` 1；穩態 10 次／120 秒＝每分鐘 5.0 次（§4.9）。
- `[ui-evidence]` UI-OVL-02：水平中心偏差 0.0px、底緣距視窗底 28.0px、取樣 22 次訊息序列 2 種、成功 2905ms、錯誤 6496ms；NFR-9.1-05：1KB 中位數 10ms、5KB 23ms、20KB 131ms（最大 144ms）；UI-DS-04／06／07、UI-OVL-03 的量測見 §4.12。

整套首次與最終兩次的差別只有：命名修正、環境重置、全棧已收；兩次的 p9 證據數字在同一量級內——UI-OVL-02 成功／錯誤 toast：最終 2905／6496ms、第 1 次 2905／6494ms；NFR-9.1-05 的 20KB 中位數：最終 131ms、第 1 次 125ms、先前單獨跑 129ms，三次都高於 100ms。

## 8. RTM 合併與統計

### 8.1 怎麼合併（單線；W5 三棒不碰 `RTM.md`）

以 `HEAD` 的 `RTM.md` 為底（冪等，重跑不會累積附加），只改每列的「實作檔、自動測試、E2E 驗證、狀態」四格：

1. **開發者回填**：`rtm_backfill_W5BE.md`、`rtm_backfill_W5FE.md`、`rtm_backfill_W5INFRA.md` 的「實作檔」「自動測試」併入（去重、保序）；三份的「狀態」欄只是建議值，**一律不採用**，狀態由 QA 逐列依本報告的親跑證據判定。INFRA 回填把同一個測試檔的第二個以後的測試寫成 `test_x.py::name`（省略 `engine-bridge/tests/`），合併時補成完整相對路徑。
2. **QA 判定**：每個有判定的列，在「E2E 驗證」欄**追加**一句 `QA 2026-10-16（W5 複驗）：…（QA_W5_Reverification.md §n）`（W4 的既有文字不動），並設定狀態。
3. **主控裁決改列**：`UI-KPI-01`／`UI-KPI-02` → `✅ 已驗證`（C-13，ADR-001 §4 與 §5 G-20）；`US-M-09` → `✅ 已驗證`（C-14，契約 §4.3 M-12）；`NFR-9.3-01` → `🟡 部分`，E2E 欄依主控給定句：「可用性量測機制已就緒（Prometheus `up`＋Grafana 面板，W2-B）；99.5% 需 30 天觀測，由營運持續量測」。
4. **新列三個**（接在各前綴最大號之後，不改既有列號）：`API-PRJ-06`（復原軟刪除專案）、`API-MON-08`（全域任務總計）、`BR-26`（Bridge 深度探針）。
5. **過期的測試引用清理**：合併後以兩支腳本核對（路徑是否存在、測試名是否真的出現在測試檔）。核對腳本對第一版合併預覽回報 17 筆「找不到」（去重後 15 筆）：其中 **12 筆**是 `HEAD` 的 RTM 本來就有、因 W5 改名或移除測試而過期的引用（`pdfIs501WithTheW5Reason…`、`flywayAppliedVersionsOneToSevenSuccessfully`、`task-retry.spec.ts` 的舊標題、`monitor.mock.spec.ts` 的「CSV 下載」舊標題、`dashboard.mock.spec.ts` 的 task-trend 失敗情境、`globalTokenBudgetFollowsTheValidationRuleTwelveDigitsMax`），另 3 筆是 INFRA 回填省略路徑造成的誤報（合併時補全）。QA 逐一對回現行測試檔，改成現名或移除，影響 11 列（`US-T-02`／`05`／`06`、`UI-SCR-05`、`US-M-07`、`API-MON-07`、`API-SET-03`、`INF-DB-12`／`14`／`15`、`UI-SCR-01`）。修正後兩支腳本：路徑 1,558 個全數存在、測試引用 1,320 個全數找到（核對的是「測試名真的出現在測試檔」，不是「測試有跑」；有跑與否以 §3、§6、§7 的實跑為準）。
6. **驗證合併本身**（`verify_rtm_diff` 的 W5 版）：非表格行逐字不變；每列的 ID、來源、摘要、層、Phase 五格不變；只有四格有變動；儲存格內沒有管線字元；狀態都在詞彙內；已驗證列的 E2E 欄沒有「待填」。結果見 §8.3。

### 8.2 統計表（前綴 × 狀態；套用後現查）

| 前綴 | 列數 | `✅ 已驗證` | `✅ 實作+測試` | `🟡 部分` | `❌ 缺陷` | `⬜ 未開始` |
|------|------|------|------|------|------|------|
| `US-` | 58 | 57 | 0 | 1 | 0 | 0 |
| `API-` | 93 | 92 | 0 | 1 | 0 | 0 |
| `BR-` | 26 | 26 | 0 | 0 | 0 | 0 |
| `NFR-` | 32 | 30 | 0 | 2 | 0 | 0 |
| `INF-` | 103 | 102 | 0 | 1 | 0 | 0 |
| `UI-` | 52 | 51 | 0 | 1 | 0 | 0 |
| 合計 | **364** | **358** | 0 | **6** | **0** | **0** |

對照 W4（361 列）：`✅ 已驗證` 331、`🟡 部分` 17、`❌ 缺陷` 7、`✅ 實作+測試` 5、`⬜ 未開始` 1。W4 的 7 筆 `❌ 缺陷`（`US-I-04`、`UI-SCR-06`、`US-S-06`、`API-SET-09`、`INF-SVC-04`、`INF-DKR-04`、`UI-A11Y-03`）全數回 `✅ 已驗證`；`⛔ 範圍外` 0 列。

現查指令（Implementation_Plan W4 閘門的兩條，加總列數一條）：

```bash
grep -c -E '^\| (US|API|BR|NFR|INF|UI)-' AgentConsole/docs/06_quality/RTM.md
grep -c -E '^\| (US|API|BR|NFR|INF|UI)-.*⬜ 未開始 \|$' AgentConsole/docs/06_quality/RTM.md
grep -c -E '^\| (US|API|BR|NFR|INF|UI)-.*✅ 已驗證 \|$' AgentConsole/docs/06_quality/RTM.md
```

```powershell
(Select-String -Path AgentConsole\docs\06_quality\RTM.md -Pattern '^\| (US|API|BR|NFR|INF|UI)-').Count
(Select-String -Path AgentConsole\docs\06_quality\RTM.md -Pattern '^\| (US|API|BR|NFR|INF|UI)-.*⬜ 未開始 \|$').Count
(Select-String -Path AgentConsole\docs\06_quality\RTM.md -Pattern '^\| (US|API|BR|NFR|INF|UI)-.*✅ 已驗證 \|$').Count
```

本回合現查輸出（依序是總列數、`⬜ 未開始`、`✅ 已驗證`）：

```text
364
0
358
```

另現查：`❌ 缺陷` 0、`🟡 部分` 6、`✅ 實作+測試` 0。

### 8.3 合併驗證與文件鎖

- **合併驗證**（W5 版 `verify_rtm_w5`，對 `HEAD` 逐列）：**問題 無**。非表格行 153 行中只有 3 行有差異（標頭的「總列數」與 §1.2 前綴表 `API-`、`BR-` 的列數，都是新列帶來的預期更新）；列數 361→364（新列恰為 `API-PRJ-06`、`API-MON-08`、`BR-26`，各接在該家族最大號之後）；既有列的 ID／來源／摘要／層／Phase 五格零改動；各欄有變動的既有列數：實作檔 41、自動測試 43（其中 12 筆是過期引用的改名或移除）、E2E 驗證 50、狀態 25；E2E 驗證欄一律是**附加**（W4 的文字是新文字的前綴）；沒有管線字元、沒有殘留 `待填`（已驗證列）、沒有殘留佔位符、狀態都在詞彙內。
- **基線站點鎖**：`python tools\check_pytest_baseline_sites.py` **rc=0**——`✅ pytest 基線站點守門通過：12 份掃描檔中僅 SSOT（ONBOARDING.md）載有基線數字（另 34 筆豁免行，見 warning）；發現面另有 114 支未納管存量檔`（114 與 W4 相同，本輪沒有新增未納管檔）。該鎖只掃已追蹤檔，本報告是新檔，所以另以同一判準（同一行出現 `passed`／`skipped` 字樣又有 4 位以上數字，或帶千分位的數字）自掃：**命中 0 行**（657 行含全部表格列；另含 `check_pytest_baseline_sites.py` 的「數字配對＋pytest／venv 語境」判準，亦為 0 行）。
- **引用核對**：RTM 實作檔欄 1,558 個路徑全數存在；自動測試欄 1,320 個測試引用全數找到（§8.1 第 5 點）。
- **文件上限**：`AgentConsole/CLAUDE.md` 164 行（上限 200）、`AgentConsole/README.md` 78 行（上限 80）。

### 8.4 仍非 `✅ 已驗證` 的列（逐列理由）

| ID | 摘要 | 理由 |
|----|------|------|
| `API-AUT-06` | Level 6-10 等級傳遞引擎 | 主控裁決維持：契約標 `UNVERIFIED`，等級 6～10 不送引擎設定；等級 1～5 已驗，11 回 400 |
| `US-M-10` | Agent 即時狀態 | 主控裁決維持：「資源使用情況」Bridge 沒有資料來源；Agent 連線狀態、可用率、目前任務已驗 |
| `INF-VOL-07` | 卷 nginx_certs（HTTPS） | 主控裁決「不追」：QA 沒有親驗 INFRA 的自簽憑證實驗，只引 INFRA 自述（§6.7、§10） |
| `NFR-9.3-01` | 可用性目標 99.5％ | 主控給定句：量測機制已就緒，99.5％需 30 天觀測，由營運持續量測 |
| `UI-A11Y-02` | 鍵盤導航 Tab／Enter／Esc | **QA 判定**：鍵盤主線六情境通過，剩 DEF-AC-011（P3，對話框關閉後焦點沒歸還，`test.fail` 釘住）未修（§4.5） |
| `NFR-9.1-05` | Markdown 渲染小於 100ms | **QA 判定**：1KB 10ms、5KB 23ms 達標，20KB 131ms 未達 C-19 的 < 100ms 目標；需求原文沒寫大小，W4 已列〈與設計稿差異〉；交主控裁決驗收口徑（§4.11）。**不在任務書預期的 🟡 清單內，也沒有登缺陷** |

## 9. 新登缺陷與觀察

### 9.1 新登缺陷

| 編號 | 級別 | 摘要 | 影響的 RTM 列 | 釘住方式 |
|------|------|------|---------------|----------|
| DEF-AC-011 | P3 | 以程式控制開啟的對話框（新建專案、新增目標、刪除專案確認、審核確認）按 Esc 關閉後，焦點落在 `<body>`，沒有歸還觸發鈕（WCAG 2.4.3 焦點順序）；通知鈴的 Popover 有歸還。鍵盤與螢幕閱讀器使用者每關一個對話框就要從頁首重新 Tab | `UI-A11Y-02`（維持 🟡） | `p9-w5-a11y.spec.ts` 的 `test.fail(DEFECTS_OPEN, …)`；修好後會「意外通過」而變紅，提醒移除；`E2E_DEFECTS_FIXED=1` 看真實失敗訊息 |

W4 的 10 筆缺陷（DEF-AC-001～010）編號不變；本輪沒有改動任何既有編號。DEF-AC-011 之外，W5 新增的程式（task-totals、restore、PDF、`/health/deep`、traceId、bridgeStatus、匯入記錄警告）在對應情境中**沒有**發現新缺陷。

### 9.2 新增觀察（P4，不立缺陷；W4 的 O-01～O-21 之後續號）

| 編號 | 觀察 | 建議 |
|------|------|------|
| O-22 | Windows 的 260 字元路徑上限：`E2E_ROOT` 太長時 Bridge 的 checkpoint 暫存檔路徑超限，審核「重試」得 502（§2.3）。環境條件，不是產品缺陷（正式部署是 Linux 容器） | README 註明 Windows 本機模式的 `ENGINE_WORKSPACE`／`E2E_ROOT` 要短（已寫進 `frontend/tests/e2e/README.md` 〈W5 複驗〉） |
| O-23 | Bridge 記錄「未處理例外」的那一行，`trace_id` 是 `-`（tracing 中介層在 uvicorn 記例外之前已重設 contextvar）；其餘每一行都有 trace id | 例外行也帶 trace id 會更利於追查；不阻擋 NFR-9.4-04 |
| O-24 | 報表 PDF 的外觀小瑕疵（只做文字抽取，沒有目視版面）：runId 欄位被換行切成兩段、時間範圍字串帶 9 位小數的奈秒（例：`2026-10-14T20:22:55.515323900Z`） | 欄寬與時間格式化；不影響內容正確 |
| O-25 | 新建專案對話框的 Markdown 編輯器工具列有 40 個 svg 是 `@uiw/react-md-editor` 套件自帶圖示，不是 Lucide | 已登記為 `UI-DS-04` 的已知例外 |
| O-26 | 還原後 replica 與 primary 的複製已斷（primary 的 `pg_stat_replication` 為 0 行；replica 日誌 `new timeline 2 forked off current database system timeline 1`、`waiting for WAL to become available`，重播位置停住），replica 容器卻仍是 `healthy`——它的 healthcheck 只有 `pg_isready -h 127.0.0.1 -U aisdlc`（README〈4.3〉已要求還原後重建 replica，這是文件化的行為，不是缺陷） | 監控面若沒有「複製延遲／`pg_stat_replication` 為 0」告警，這個狀態只靠人記得讀 README〈4.3〉；QA 沒有查 Prometheus 規則是否已涵蓋，建議確認 |
| O-27 | 整套第 1 次出現一次 `net::ERR_NO_BUFFER_SPACE`（Windows 用戶端 socket 緩衝耗盡），讓單一頁面少載一個 JS chunk 而卡在「載入中」（§7.1）。時間點是 Docker 全棧剛起完約 2 分鐘；同一支情境單獨跑 774ms 通過，整套第 2 次（無全棧在線上）150 支全數通過、沒有再出現 | 環境暫態；本機整套與 Docker 全棧不要同時跑；若要在 CI 吸收這類暫態，可評估 Playwright 的 `retries`（QA 不改設定檔） |

沿用且仍成立的 W4 觀察：O-21（mock claude 沒有慢步驟旋鈕，要看 EXECUTING 的呼吸點得用 26 個任務的長批次撐住）、O-20（`CONSOLE_INTERNAL_PROXIES` 的處置，§6 以真實全棧重驗）。

### 9.3 本輪發現的我方（測試）問題

寫新 spec 的過程中修掉的自家錯誤（皆在合併前修畢，不是產品缺陷，列出供日後寫測試者參考）：① 列 8 的「啟動執行被擋」reason 有兩種中文字串（專案正在執行中／同專案同路徑已有執行中的批次），PAUSED 持有鎖時是後者，斷言改為兩者之一；② dnd-kit 鍵盤感測器在起始鍵之後要約 250ms 才收方向鍵，按鍵之間要留間隔；③ UI-OVL-03 的 `animation-timing-function` 要取 computed style，`getAnimations()` 的 `effect.getTiming().easing` 只反映 effect 層、與 CSS 屬性不同；④ 假 Brain 只看內容文字、不看 `additionalPrompt`，C-10 被有界閘拒絕的重新解析改用路徑 B＋FakeLlm 造；⑤ 暫停中批次的專案狀態是 READY，要看到 EXECUTING 的呼吸點得用長批次；⑥ **專案名稱不可含導覽列的字樣**：整套第 1 次，`shells-and-layout` 的「手機 390px」用 `getByRole('link', { name: '儀表板' })` 做子字串比對，撞上我建的專案「QA W5 儀表板完成 …」而 strict mode violation——共用同一個資料庫的 specs 之間，名稱就是隱性的共用狀態；改名（`DASH`）後於乾淨庫重跑（§7.2）。

## 10. 未覆蓋與維持 🟡 的項目

**RTM 上仍是 `🟡 部分` 的列**（理由逐列見 §8.4）：`API-AUT-06`（等級 6～10 未驗證，主控裁決維持）、`US-M-10`（資源使用情況，主控裁決維持）、`INF-VOL-07`（HTTPS，主控裁決「不追」）、`NFR-9.3-01`（99.5％可用性需 30 天觀測，主控給定句）；另有兩列是本輪 QA 的判定：`UI-A11Y-02`（DEF-AC-011 未修）、`NFR-9.1-05`（20KB 預覽 131ms 高於 100ms）。

**〈未覆蓋〉**——本輪沒有做、或只做了一部分的事（不宣稱已驗證）：

1. **`INF-VOL-07` HTTPS**：QA 沒有親跑 INFRA 的自簽憑證實驗；RTM 引用的是 INFRA 回填的自述（自簽憑證實跑，真憑證申請與續期不在範圍），因此維持 🟡 並標明「INFRA 自述，QA 未親驗」。
2. **`NFR-9.3-01`**：可用性 99.5％要 30 天觀測，一輪驗證結構上做不到；只能確認量測機制（Prometheus `up`＋Grafana 面板）在全棧起得來（§6.1 的 prometheus、grafana 皆 healthy）。
3. **軟刪除清除排程**（`console.retention.purge-enabled=true`）：預設關閉，QA 沒有在 e2e 或 Docker 開啟；只有後端單元測試覆蓋（§3 的 1,501 個後端測試的一部分）。
4. **報表 PDF 的版面外觀**：只做文字抽取（標題、四區段、數字、中文任務名），沒有目視版面；O-24 是從抽取結果看到的瑕疵，不是視覺檢查。
5. **瀏覽器與平台**：全部在 Chromium（Playwright 的 Chromium 156）、Windows 11、Docker Desktop；沒有 Firefox／WebKit、沒有 Linux／macOS 主機上的 Docker。
6. **真 LLM**：匯入的路徑 B 用假 OpenAI 相容伺服器、路徑 C 用假 Brain；沒有對真的模型服務發請求（外呼 allowlist 本來就擋）；執行用 `aisdlc-mock-claude`，引擎與 Bridge 是真的。
7. **還原後的 replica**：RPO／RTO 演練驗的是 primary 的空卷還原；README〈4.3〉說還原後 replica 時間軸會分岔、必須重建（〈5〉）——QA 驗證完即整套收掉，沒有重建 replica；演練後 replica 的狀態見 §6.7（時間軸分岔、複製已斷、容器仍顯示 healthy）。
8. **離站 repo2 還原**：演練還原自 repo1（預設）；沒有做 `--repo 2` 的還原。
9. **全新主機的冷啟動**：全棧是在有快取映像的機器上 `up --build`（§2.2 的快取統計）；沒有在乾淨的 Docker 環境（無任何快取層）重做一次。
10. **不在 W5 範圍而 QA 沒追的**：`API-AUT-06`、`US-M-10`、`US-I-05` 瀏覽按鈕、O-07（日誌主機路徑遮罩，涉及 Architecture §8.3 三處消毒 parity）、O-21（mock claude 旋鈕）、C-21／C-22（SA 的契約回寫）。

## 11. 給主控的提醒

1. **兩件待主控裁決的事**：① `NFR-9.1-05` 的驗收口徑（現況 20KB 預覽更新中位數 131ms，C-19 的目標是 < 100ms；1KB、5KB 達標；§4.11）；② DEF-AC-011（P3）進不進下一波，修好後 `p9-w5-a11y.spec.ts` 那支 `test.fail` 會「意外通過」而變紅，把 `test.fail(DEFECTS_OPEN, …)` 那一行移除即可，`UI-A11Y-02` 隨即可升 `✅`。
2. **RTM 的 `🟡` 剩 6 列**：任務書預期的四列（`API-AUT-06`、`US-M-10`、`INF-VOL-07`、`NFR-9.3-01`）＋ QA 判定的兩列（`UI-A11Y-02`＝DEF-AC-011 未修；`NFR-9.1-05`＝20KB 未達標，**這一列不在任務書的預期清單內，也沒有登缺陷**：W4 已把它列為〈與設計稿差異〉，需求原文沒寫大小，所以我維持 `🟡` 交主控裁決，沒有擅自改 `✅` 或降 `❌`）。
3. **RTM 合併順手清了 11 列過期的測試引用**（W5 改名或移除測試後，`HEAD` 的 RTM 仍指向舊名；§8.1）。往後開發者改名或移除測試時，應同步改 RTM 的「自動測試」欄；兩支核對腳本可以收進 CI（只讀）。
4. **要 commit 的東西**：新增檔 `frontend/tests/e2e/` 的五支 `p9-w5-*.spec.ts`、`pdfText.ts`、`w5.ts` 與 `__screenshots__/` 底下 12 張新截圖（11 張 `p9-*.png`，加 `p8-docker-sse-reconnected.png`——後者是 W4 被 `test.fail` 擋住、本輪才走到的畫面）；修改檔 `p3`／`p4`／`p4b`／`p5`／`p6`／`p7`／`p8`／`markdown-editor`／`task-retry`／`realBackend.ts`／`README.md`、`frontend/.prettierignore`、`docs/06_quality/RTM.md`、本檔。其中 `p4`／`p4b`／`p7`／`markdown-editor` 等只是 Prettier 重排（真後端 spec 移出 `.prettierignore` 後 `npm run format` 的結果），diff 會有格式噪音。被整套改寫的**已追蹤**截圖已用 `git show HEAD:<path>` 的位元組寫回（沒有用 `restore`／`checkout`）。
5. **跑法與環境**：本機整套約 51 分鐘、Docker 全棧約 11 分鐘，**兩者不要同時跑**（共用 Docker 引擎與主機的 socket；O-27）；Windows 的 `E2E_ROOT` 要短（O-22）；限流是每使用者每分鐘 100 次，新 spec 一律先 `ensureQuota`；`p9-w5-ui` 建的專案名稱不可含導覽字樣（§9.3 第 ⑥ 點）。
6. **我沒有動的東西**：`AutoClaude/.perf_baseline.toml`（我開始前就是髒檔）；5432 的 `autoclaude_pg` 全程沒碰；機器上別人留下的映像（例如 `aisdlc-backend:w5`、`aisdlc-frontend:w5`）沒碰；不是我起的 `aisdlc_sdd_default` docker 網路沒碰。
7. **收尾遺留需要人處理**：磁碟根目錄下我用的短 `E2E_ROOT` 目錄（四個已清空的子目錄）**無法由我刪除**——環境對含該路徑字面量的 `Remove-Item` 有路徑保護；請在確認不再需要後手動刪除。我建的映像 `aisdlc-engine-bridge:w5qa` 已 `docker rmi` 刪除。
8. **Implementation_Plan 進度帳**可直接引用的數字：RTM 364 列＝`✅ 已驗證` 358＋`🟡 部分` 6；本機整套 150 支、Docker 全棧 27 支；閘門數字見 §3。
