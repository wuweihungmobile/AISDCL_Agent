# QA 報告：W7 收尾波獨立零信任複驗（W7-QA）

| 項目 | 內容 |
|------|------|
| 版本 | v1.2（v1.0 為 W7-QA 第一輪產出；W8-QA 第二輪複驗於 2026-10-17 追加 §13，並更新 §10.1、§12.2 的缺陷狀態；整合輪 115 的 W5-QA 於同日追加 §14，只指路缺陷編號的去處；第一輪的其餘章節維持當時的描述，不回頭改寫） |
| 日期 | 2026-10-17 |
| 驗證者 | 獨立 QA（零信任：BE／FE／INFRA 三棒的交卷與三份 RTM 回填 `rtm_backfill_W7BE.md`／`W7FE.md`／`W7INFRA.md` 的「已驗證」一律不採信，每一列親跑才設 `✅ 已驗證`） |
| 被驗 commit | HEAD `06891089`（W7 六個 commit：`230d70af` 第一批、`10033d5d` INFRA、`a4e028ed` FE 第一＋二批、`3c95862b` 契約 v1.4 補丁、`a7993946` FE 第三批、`06891089` BE 第二批） |
| 依據 | 主控派工任務書（W7-QA）、`docs/04_planning/agent_briefs/W7_OVERVIEW.md`（§1 裁決表、§3.6、§4 環境、§5 交卷格式）、[Completeness_Audit_W7.md](Completeness_Audit_W7.md)（27 筆）、契約 `docs/02_architecture/API_Contract_P3-6.md` v1.4（E2E-14／15／16）、[RTM.md](RTM.md)、W5 報告 [QA_W5_Reverification.md](QA_W5_Reverification.md) |
| 相關文件 | [RTM.md](RTM.md)（E2E 驗證欄的節號都指向本檔）、`frontend/tests/e2e/README.md`〈W7 複驗〉 |

## 1. 摘要

> **W8 複驗更新（2026-10-17）**：第一輪登記的 DEF-AC-013（P2，資安）與 DEF-AC-014（P3）已由主控依 D-21 修於 `85ed0915`（前端）與 `520c2850`（後端），第二輪複驗全數通過（§13）；下文本節其餘段落、§8.4、§11 描述的是第一輪當時的狀態，保留不改；DEF-AC-012 維持 P4 保留（D-21）。

**結論**：**W7 收尾波通過 QA 複驗，可進主控收斂；但有一個資安缺陷需要你決定（DEF-AC-013，P2）。** 我在本機真後端（Windows）、真 Bridge、真瀏覽器與 Docker 全棧（Linux 容器）上親跑：本機 Playwright 整套 213 個全數通過（0 失敗、0 略過）；Docker 全棧 32 個測試都有通過的紀錄（第一次整套 28 個通過，唯一的失敗是我自己新寫那支測試的限流額度設計，修正後該檔重跑兩次各 5 個全數通過）；RTM 五列 `🟡` 全部升 `✅`、新增十列全 `✅`，合併後 **374 列全為 `✅ 已驗證`**；完整性審查 27 筆逐筆處置完畢；設計稿九畫面逐項對照完成（145 項 DOM 斷言加人眼逐張對照）；V-05 的 63 列 INF 重驗 56 列、部分 6 列、1 列未逐列重驗。**新登三筆缺陷**：DEF-AC-012（P4，Bridge 與 SSOT 對 SDD LATEST 的判定在未入庫目錄時分歧）、DEF-AC-013（P2，資安，編輯器預覽會執行內嵌 `<iframe srcdoc>` 的腳本）、DEF-AC-014（P3，SSE 客戶端斷線被記成 ERROR 日誌）；三筆都沒有讓任何 RTM 列掉成 `❌`。BE／FE／INFRA 三棒的交卷與三份回填檔的「建議狀態」我一律沒有採信，每個升級都附本輪親跑的輸出（§4～§8）。

**最需要主控決定的三件事**：

1. **DEF-AC-013（P2，資安）要不要進下一波**：Markdown 編輯器預覽會執行內嵌 `<iframe srcdoc>` 裡的腳本，且是儲存式——operator 把 payload 存進專案說明，管理者開「編輯專案」頁就中，腳本可讀 `sessionStorage` 裡的 session（實測讀到鍵名 `aisdlc.console.session`）。img onerror、script 標籤、javascript: 連結三種載體不會執行，唯讀的詳情頁也不受影響，所以範圍很窄、修法也小（`MarkdownEditorImpl.tsx` 第 29～32 行的 `PREVIEW_OPTIONS` 加 `skipHtml` 或 `rehype-sanitize`）。已用 `test.fail` 釘住，沒有任何 RTM 列要求「預覽不執行腳本」所以我沒動 RTM 狀態；是否補列由你定（§10.1）。
2. **文件訂正請主控或 SA 落字**（不在我的持有面）：ADR-001 第 54 行（虛擬執行緒預設值「未驗」→ 實測結論）、Architecture §12.2 V-11（I-04 實驗結論與 DEF-AC-012）、`AgentConsole/CLAUDE.md` 環境變數表補 L-12 警語（純檔案模式下 Console 的步驟時間軸與斷點清單是空的，§8.4 實測）、契約字面兩處與實作不同（§12）。
3. **CI 路徑過濾不含 `AISDLC_SDD/**`**（觀察 O-34）：SDD 側改 FSM 狀態檔格式或 `sdd_version.py` 不會觸發 Console 的 CI；`.github` 不在本專案可改範圍。

其餘決定項（DEF-AC-014 日誌衛生 P3、DEF-AC-012 分歧 P4、觀察 O-28～O-39）逐條列在 §12.2。

**本回合實跑的數字**（逐條證據見 §3～§8）：

| 項目 | 當回合實測 | 節 |
|------|------------|----|
| 後端 `gradlew clean build` | rc=0，`BUILD SUCCESSFUL in 1m 45s`；1701 項測試全數成功、0 失敗、0 略過；JaCoCo 指令 96%／分支 84% | §3.1 |
| 前端 lint／`tsc --noEmit`／build | 皆 rc=0（編輯 spec 後 lint 與 tsc 又各跑一次，皆 rc=0） | §3.2、§3.4 |
| 前端 vitest（閒置機） | rc=0：57 個檔、886 項全數通過；覆蓋率（`coverage.include` 口徑）Statements 95.61%／Branches 89.71%／Functions 97.44%／Lines 97.17%（第一次與 gradle 並行時有 1 項逾時，單檔 2.75 秒通過，觀察 O-28） | §3.2 |
| Bridge | `ruff check` 兩視角皆 rc=0；pytest rc=0（386 通過、5 略過、1 個警告，261.28 秒；DSN 指向 `qa-pg`）；根層 `TestDirEntryPrimitivesAreAccountedFor` 7 項 OK | §3.3 |
| 本機 Playwright 整套 | rc=0，**213 通過**、0 失敗、0 略過（67.5 分鐘，31 個檔；W5 為 150 個、52.2 分鐘） | §8.1 |
| `p9-w7-*` 七支最終版重跑 | 46 通過、1 失敗（舊版 `html` spec＝DEF-AC-013 的發現）；改寫後的 `html` 新版 4 通過（含 2 個以 `test.fail` 釘住的預期失敗） | §8.4 |
| Docker 全棧 Playwright | 第一次整套 28 通過、1 失敗（我的限流額度設計）、3 未執行；`p9-w7-docker.stack.ts` 重跑兩次（第二次、定稿版）各 5 通過 | §8.2 |
| 五列 `🟡` | `API-AUT-06`（八個情境）、`US-M-10`（本機＋Docker 兩端）、`NFR-9.1-05`（20KB 中位數 57／57／62／57ms，上限 100ms）、`NFR-9.3-01`（量測機制＋告警 pending→firing＋卷歷史撐過 `down`）、`INF-VOL-07`（README〈14〉全程重跑、憑證指紋與 notAfter 變了、復原乾淨）全部升 `✅` | §4 |
| 契約 v1.4 新增面 | E2E-15 十三個情境（本機）加 Docker 半邊；E2E-16 列 1～10；DAG 全螢幕（E-22）；US-P-04 編輯鎖定 | §5 |
| 設計稿九畫面（V-08） | 145 項 DOM 斷言加人眼逐張對照，差異皆已有登記 | §7 |
| INF 唯讀探查（V-05） | 63 列：56 列重驗、6 列部分重驗、1 列未逐列重驗，無一被證偽 | §8.3 |
| 完整性審查 27 筆 | 18 筆已修且核實、7 筆已登記且核實、V-09 部分關閉加裁決保留、I-04 實驗確認分歧 | §6 |
| RTM | 364 列（`✅` 359、`🟡` 5）→ 374 列（`✅` 374、其餘 0） | §9、§12.1 |
| 新缺陷 | DEF-AC-012（P4）、DEF-AC-013（P2，資安）、DEF-AC-014（P3） | §10.1 |

**本輪新增或修改的驗證資產**（皆在 `AgentConsole/frontend/tests/e2e/`）：新增 `w7.ts`（假模型伺服器、YAML 讀寫、變體 Bridge 啟停、目錄快照等共用輔助）與 `p9-w7-engine`／`resources`／`sdd`／`signoffs`／`ui`／`purefile`／`html` 七支真後端 spec 及 `p9-w7-docker.stack.ts`（Docker 全棧）；修改 `p9-w5-ui-evidence.spec.ts`（NFR-9.1-05 的 20KB 上限 400ms→100ms）與 `README.md`；16 張新截圖（`p9-w7-*.png`）。

**主控請知悉**：（a）整套的 213 個全過，不代表沒有缺陷——DEF-AC-013 是 `html` spec 在探測時發現的，那支 spec 以 `test.fail` 釘住；（b）整套開跑後我又改了幾處 spec（畫面 3／4／5 夾具、一個 log 字串、SDD 版本不再寫死、`html` spec 改寫成四情境、Docker spec 的限流等待），所以對 `p9-w7-*` 七支最終版另外重跑一次（§8.4），Docker 那支改後重跑兩次（§8.2）；（c）`AgentConsole/docs/04_planning/Implementation_Plan.md` 與 `AutoClaude/.perf_baseline.toml` 在我開始前就是髒檔，不是我改的；（d）環境殘留見 §12.4。

## 2. 環境與啟動

### 2.1 版本與主機

| 項目 | 值 |
|------|----|
| 作業系統 | Windows 11 專業版 10.0.26300（20 個邏輯核心、127.7GB 記憶體）；所有指令用 PowerShell 工具執行（Windows 上禁用 Bash 工具） |
| 被驗 commit | HEAD `06891089`（W7 的六個 commit：第一批 `230d70af`〔契約 v1.3／v1.4、後端等級物化、完整性審查〕、INFRA `10033d5d`、FE 第一＋二批 `a4e028ed`、契約 v1.4 補丁 `3c95862b`、FE 第三批 `a7993946`、BE 第二批 `06891089`）；工作樹與 HEAD 的差別只有我改的測試與文件，外加不是我改的 `AgentConsole/docs/04_planning/Implementation_Plan.md` 與 `AutoClaude/.perf_baseline.toml`（開始前就是髒檔） |
| 工具鏈 | Node v22.23.3／npm 10.9.9、OpenJDK 21.0.10、Python 3.11.9（根層 `.venv`）、Gradle（wrapper）、Next.js 16.4.0、Playwright 1.64.x（Chromium）、vitest 5.0.4、Docker 29.5.3／Compose 5.1.4 |
| 資料庫 | PostgreSQL 18（`pgvector/pgvector:pg18`）；本機 e2e 用單一容器 `qa-pg`（25433），Docker 全棧用 primary＋replica（沿用 W7-INFRA 殘留的 `aisdlc_*` 卷與其拋棄式 `--env-file`） |

### 2.2 零信任的做法

三份回填檔（`rtm_backfill_W7BE.md`／`W7FE.md`／`W7INFRA.md`）與三棒的交卷只當「宣稱」：後端 `gradlew clean build`、前端 lint／tsc／build／vitest 都在驗證前自己重跑；本機 e2e 的 backend jar 與前端 standalone 產物在驗證前重建（`NEXT_PUBLIC_API_URL=http://localhost:18080` 內嵌）；Docker 全棧一律 `up -d --build --wait`，Bridge 映像先於驗證重建（`:dev` 標籤是 W7-INFRA 第二批之前的舊映像，沒有 `resources`、`GET /sdd/fsm`、`checks.sdd`）。每個「已驗證」都附當回合真跑的輸出；每個 spec 的失敗先判斷是環境暫態、我方 spec 或產品缺陷，不憑印象。

### 2.3 本機 e2e 環境（真後端＋假 Brain 版 Bridge＋mock claude）

埠：PostgreSQL 25433（容器 `qa-pg`；5432 的 `autoclaude_pg` 全程不動）、backend 18080（`e2e` profile）、假 Brain 版 Bridge 18081（`frontend/tests/e2e/support/fake_brain_bridge.py`）、前端 3000（`npm run build` 後 standalone，由 Playwright 的 webServer 起）；本輪 spec 另起的變體 Bridge 18082～18086（純檔案模式、各自的工作區）與假模型伺服器（隨機埠）。啟動順序仍是 **PG → backend → Bridge → 重啟 backend**（backend 先跑 Flyway 建 `console` schema，Bridge 的 DB 模式才有表可用；重啟 backend 是為了讓探測環看到 Bridge）。`E2E_ROOT` 是短路徑 `%TEMP%\e2e`（PowerShell 寫成 `$env:TEMP\e2e`；含 `projects`、`workspace`、`quota-cache`、`bridge-logs`）。每次 Playwright 都帶 `--output=<自己的暫存目錄>`（不共用 `frontend/test-results`）。設定的環境變數：`E2E_RESTART_BACKEND`、`E2E_JWT_SECRET`、`E2E_FAKE_BRAIN=1`、`E2E_BRIDGE_URL`、`E2E_BRIDGE_LOG`、`E2E_PG_CONTAINER=qa-pg`，以及本輪新增的 `E2E_STOP_BRIDGE`、`E2E_START_BRIDGE`（結束／重啟共用 Bridge 的 PowerShell 腳本）與 `E2E_MOCK_DELAY`（契約形態的慢速批次）。完整步驟見 `frontend/tests/e2e/README.md`〈真 Bridge specs〉〈W5 複驗〉〈W7 複驗〉。

### 2.4 Docker 全棧

沿用 W7-INFRA 的拋棄式 `--env-file`（隨機測試值，不入庫；殘留卷內的 PostgreSQL 是用它初始化的，換一份會連不上），起停形態（`down` 一律**不帶 `-v`**，主控裁定保留殘留卷；映像一律加 `--build`）：

```bash
(cd AgentConsole && docker compose --env-file <STACK_ENV> --profile db --profile app --profile full up -d --build --wait)
(cd AgentConsole && docker compose --env-file <STACK_ENV> --profile db --profile app --profile full down)
```

```powershell
Push-Location AgentConsole; docker compose --env-file <STACK_ENV> --profile db --profile app --profile full up -d --build --wait; Pop-Location
Push-Location AgentConsole; docker compose --env-file <STACK_ENV> --profile db --profile app --profile full down; Pop-Location
```

**本輪實跑的起停與結果**（`<STACK_ENV>` 是 INFRA 留下的拋棄式 env 檔，我只列鍵名不列值；起停都經我寫的 `dc.ps1` 包裝，它會拒絕 `down -v`）：

- `up -d --build --wait` **rc=0，耗時 180 秒**（log `logs\stack_up.log`、`logs\stack_up.rc.txt`）。BuildKit 這次 32 個步驟命中快取、59 個步驟重新執行；五個自建映像都重新匯出，**映像 ID 與起跑前皆不同**（backend `e5d7da693e0a`→`1afdb9529ac3`、frontend `39510e0f25ca`→`303afb3c5c7a`、engine-bridge `8fca9b37b01a`→`aeeeae74dea8`、pgbackrest `7fe1d6dc7154`→`db04c923f95b`、postgres-primary `cf34f6a2d0af`→`7d30adf4edcc`；`logs\stack_snap_pre.log` 對 `logs\stack_snap_before.log`）。這也證實 `aisdlc-engine-bridge:dev` 是這次重建的新映像，不是 INFRA 第二批之前沒有 `resources`、`GET /sdd/fsm`、`checks.sdd` 的舊映像（舊的是 22 小時前建的那個）。
- 起來之後 `docker compose ps`：14 個長駐服務全部 `healthy`，`aisdlc-minio-certs` 與 `aisdlc-minio-init` 兩個一次性 job 為 `Exited (0)`（`logs\stack_ps_before.txt`）；共 16 個容器，與 compose 的 16 個 `container_name` 一致。
- 卷：起跑前殘留 11 個 `aisdlc_*`（沿用，PostgreSQL 資料就是用 INFRA 那份 env-file 初始化的），起來後新增 `aisdlc_prometheus_data`（INF-VOL-12）共 12 個。5432 的 `autoclaude_pg`（別的專案）全程 `Up … (healthy)`、沒有動。
- backend 啟動時 Flyway 對既有資料卷升級（`docker logs aisdlc-backend`）：`Current version of schema "console": 9` → 套用 V10「execution run engine capabilities」與 V11「health check path deep」→ `Successfully applied 2 migrations to schema "console", now at version v11`，也就是驗到「既有 PostgreSQL 資料卷上的升級」，沒有驗「完全乾淨的 Docker 環境從零 build」（§11）。
- Playwright 是經 nginx（`http://localhost`）打同源入口跑的，`docker.config.ts` 現查共 32 個測試（W5 時 27 個，多出的 5 個是 `p9-w7-docker.stack.ts`）。

## 3. 閘門（驗證前自己重跑；log 都在 `<SCRATCH>\w7_qa\logs\`，路徑以 §2 的暫存目錄為根）

### 3.1 後端

```bash
(cd AgentConsole/backend && sh gradlew clean build > "$LOG" 2>&1; echo "rc=$?")
```

```powershell
Push-Location AgentConsole\backend; .\gradlew.bat clean build *> $log; $rc = $LASTEXITCODE; Pop-Location
```

| 項目 | 實測（當回合） | 證據 |
|------|----------------|------|
| `gradlew clean build` | rc=0，`BUILD SUCCESSFUL in 1m 45s`（外層計時 106 秒） | `logs\gate_backend.log`、`logs\gate_backend.rc.txt` |
| 測試總數 | `Test result: SUCCESS`——1701 項測試、1701 項成功、0 失敗、0 略過（W5 為 1501 項，W7 淨增 200 項） | `logs\gate_backend.log` |
| JaCoCo | 指令覆蓋 96%（未涵蓋 1,698／51,735）、分支覆蓋 84%（638／4,231）；已重讀 `backend\build\reports\jacoco\test\html\index.html` 的 tfoot | 同上 |
| ArchUnit | `ArchitectureRulesTest`：tests=8、skipped=0、failures=0、errors=0（`backend\build\test-results\test\TEST-com.aisdlc.console.architecture.ArchitectureRulesTest.xml`） | 同上 |

### 3.2 前端

```bash
(cd AgentConsole/frontend && npm run lint > "$L1" 2>&1; echo "rc=$?"; npx tsc --noEmit > "$L2" 2>&1; echo "rc=$?"; npm run build > "$L3" 2>&1; echo "rc=$?")
```

```powershell
Push-Location AgentConsole\frontend; npm run lint *> $l1; $r1 = $LASTEXITCODE; npx tsc --noEmit *> $l2; $r2 = $LASTEXITCODE; npm run build *> $l3; $r3 = $LASTEXITCODE; Pop-Location
```

| 項目 | 實測（當回合） | 證據 |
|------|----------------|------|
| `npm run lint`（ESLint＋Prettier `format:check`） | rc=0；`All matched files use Prettier code style!`。編輯 spec 後**再跑一次**：rc=0（含 Prettier 檢查） | `logs\gate_fe_lint.log`、`logs\lint_final1.log` |
| `npx tsc --noEmit` | rc=0（輸出為空）；編輯 spec 後再跑一次：rc=0 | `logs\gate_fe_tsc.log`、`logs\tsc_final1.log` |
| `npm run build`（Next.js 16.4.0 Turbopack） | rc=0；`NEXT_PUBLIC_API_URL=http://localhost:18080`；20 條路由；`Compiled successfully in 626ms` | `logs\gate_fe_build.log` |
| `npx vitest run --coverage`（第 1 次，與 `gradlew clean build` 並行） | **rc=1**：57 個測試檔中 56 通過、1 失敗；886 個測試中 885 通過、1 失敗——失敗的是 `components/markdown/rehypePrismLinear.test.ts` 的「大文件」案例，`Test timed out in 5000ms`（實測 6143ms） | `logs\gate_fe_vitest.log` |
| 同一支測試單檔重跑 | 15 項全部通過（2.75 秒） | `logs\gate_fe_vitest_prism_alone.log` |
| `npx vitest run --coverage`（閒置機重跑） | **rc=0**：57 個測試檔、886 項測試全數通過（耗時 33.43 秒）；覆蓋率（`vitest.config.mts` 的 `coverage.include` 口徑，31 項）Statements 95.61%（1677／1754）、Branches 89.71%（1334／1487）、Functions 97.44%（458／470）、Lines 97.17%（1374／1414），門檻 70／60 皆過（W5 的 Statements 是 95.58%） | `logs\gate_fe_vitest_idle.log` |

第 1 次紅燈是**負載相依**（後端 gradle 與 vitest 並行、`jsdom` 建了 57 次），單檔 2.75 秒通過；判斷依據與 O-28 一併寫在 §10.2。我沒有把它當通過，而是在閒置機重跑一次整套再下結論（上一列）。

### 3.3 Engine Bridge 與根層護欄

```bash
(cd AgentConsole/engine-bridge && . ../../.venv/bin/activate && ruff check .)
. .venv/bin/activate && ruff check AgentConsole/engine-bridge          # 從 monorepo 根看
(cd AgentConsole/engine-bridge && . ../../.venv/bin/activate && BRIDGE_TEST_DSN="postgresql://<使用者>:<密碼>@127.0.0.1:25433/aisdlc" python -m pytest -q)   # DSN 指向本機 qa-pg
(cd tools/tests && python -m unittest test_platform_neutral_paths.TestDirEntryPrimitivesAreAccountedFor -v)
python tools/check_pytest_baseline_sites.py
```

```powershell
Push-Location AgentConsole\engine-bridge; ..\..\.venv\Scripts\ruff.exe check .; Pop-Location
.venv\Scripts\ruff.exe check AgentConsole\engine-bridge          # 從 monorepo 根看
Push-Location AgentConsole\engine-bridge; $env:BRIDGE_TEST_DSN = "postgresql://<使用者>:<密碼>@127.0.0.1:25433/aisdlc"; ..\..\.venv\Scripts\python.exe -m pytest -q; Pop-Location   # DSN 指向本機 qa-pg
Push-Location tools\tests; python -m unittest test_platform_neutral_paths.TestDirEntryPrimitivesAreAccountedFor -v; Pop-Location
python tools\check_pytest_baseline_sites.py
```

| 項目 | 實測（當回合；以下三項在機器閒置時跑） | 證據 |
|------|------------------------------------------|------|
| `ruff check`（`engine-bridge` 本目錄） | rc=0，`All checks passed!` | `logs\gate_ruff_local.log` |
| `ruff check AgentConsole/engine-bridge`（monorepo 根視角） | rc=0，`All checks passed!` | `logs\gate_ruff_root.log` |
| Bridge `pytest -q`（`BRIDGE_TEST_DSN` 指向 `qa-pg`，所以 `test_db_integration.py` 的真 PG 整合測試有跑） | rc=0：386 個通過、5 個略過、1 個警告，耗時 261.28 秒（W5 為 326 通過、4 略過）。5 個略過我沒有另跑 `-rs` 逐一列出，但 `tests/` 內「此環境無法建立 symlink」的 skip 恰有 5 處（W5 是 4 處，W7 在 `test_sdd_fsm.py` 多一個 symlink 測試），其他 skip 條件（沒有 git、沒設 DSN、沒有 FSM 狀態檔）在這台機器都不成立 | `logs\gate_bridge_pytest.log` |
| 根層 `TestDirEntryPrimitivesAreAccountedFor` | rc=0：`Ran 7 tests`、`OK` | `logs\gate_root_unittest.log` |
| `tools/check_pytest_baseline_sites.py` | rc=0：`pytest 基線站點守門通過：12 份掃描檔中僅 SSOT（ONBOARDING.md）載有基線數字` | `logs\gate_baseline_sites.log` |
| `AgentConsole/CLAUDE.md` 行數（≤ 200） | 164 | `logs\gates_idle.rc.txt` |
| `AgentConsole/README.md` 行數（≤ 80） | 78 | 同上 |
| 新文件不得有「測試摘要字樣＋4 位數字」同行 | 我用自寫的小程式（逐行套用該工具的兩個判準）掃本報告與 `RTM.md`：命中 0 行（§9.3） | §9.3 |

### 3.4 我自己改過的測試檔再跑一次

整套與各 spec 跑完之後我又改了 `p9-w7-html.spec.ts`、`p9-w7-signoffs.spec.ts`、`p9-w7-sdd.spec.ts`、`p9-w7-docker.stack.ts`、`w7.ts`，所以 lint 與型別檢查在**最後一次編輯之後**重跑（`logs\lint_final2.log`、`logs\tsc_final2.log`，加上最後一個編輯後單檔的 `prettier`／`eslint`）；Docker 那支與文件定稿之後我又在**所有檔案都定稿的最終狀態**整個重跑了一次（`logs\lint_final3.log`、`logs\tsc_final3.log`，兩個指令各 rc=0）：

| 項目 | 實測 |
|------|------|
| `npm run lint`（ESLint＋Prettier `format:check`） | 編輯後 rc=0（`lint_final2`）；最終狀態 rc=0（`lint_final3`）：`All matched files use Prettier code style!` |
| `npx tsc --noEmit` | 編輯後 rc=0（`tsc_final2`）；最終狀態 rc=0（`tsc_final3`，輸出為空，0 bytes） |
| 最後幾次編輯 `p9-w7-html.spec.ts` 與 `p9-w7-docker.stack.ts` 後的單檔 `prettier --write`／`eslint` | `prettier17.log`：`tests/e2e/p9-w7-html.spec.ts 64ms (unchanged)`；`prettier19.log`：`tests/e2e/p9-w7-docker.stack.ts 110ms`（這次被重排了一次格式，之後的整體 lint 就是上兩列）；`eslint17.log`、`eslint19.log` 皆 0 bytes（沒有任何訊息） |

## 4. 五列「部分」逐一親驗

W7 開工時 RTM 有五列 `🟡 部分`（`API-AUT-06`、`US-M-10`、`NFR-9.1-05`、`NFR-9.3-01`、`INF-VOL-07`）。以下每列：契約怎麼說、我怎麼造情境、當回合逐字輸出、判定。證據行以 `[w7-…]` 開頭者是 spec 自己用 `console.log` 印出的量測值，原檔在 `logs\pw_*.log`。

### 4.1 `API-AUT-06`（等級 6～10 傳遞引擎；契約 v1.3 E2E-14 列 1～7＋審查 V-12）

**契約怎麼說**：契約 v1.3 E2E-14 列 1～7 與審查 V-12。等級 6～10 的「自動突變」「自演化」兩個引擎能力旗標，不能只停在 console-api 的設定表：`engineCapabilities`（`autoMutation`、`selfEvolution` 各為 `ENABLED`／`OFF`／`UNAVAILABLE_NO_API_KEY`）要與**磁碟上引擎真正讀的設定檔**（`config.yaml`、`playbook.yaml`、`run.json`）以及**假模型伺服器實際收到的請求**一致；V-12 另要求附錄 C 標為 `ENGINE` 的十六把設定鍵，逐鍵設非預設值、起一個批次，磁碟上的引擎設定逐鍵吻合。

**我怎麼造情境**：`p9-w7-engine.spec.ts`（八個測試，本機真後端＋真 Bridge＋mock claude）。另起一個**假模型伺服器**（隨機埠，spec 內建；依請求內容把 Brain 請求分成 `goal`／`correction`／`evolution` 三類並計數，`minimax.base_url` 經 `model.apiUrl` 指到它）。檔案那一邊的斷言都由測試自己用 YAML／JSON 解析器讀（YAML 經根層 `.venv` 的 PyYAML），不經 console-api 或 Bridge 轉述。

| 契約列 | 驗什麼 | 當回合實測（逐字節錄自 `logs\pw_final1.log`） |
|--------|--------|----------------------------------------------|
| 1 等級 7＋金鑰、三步全成功 | `engineCapabilities`＝{ENABLED, ENABLED}（201 與詳情同值）；磁碟 `minimax.enable_kernel_brain＝true`、`minimax.base_url＝model.apiUrl`、`playbook.yaml` 沒有 `max_evolutions`／`require_evolution_signoff`、minimax 區段沒有 `api_key`；`run.json` 的 `env_keys` 含名稱 `MINIMAX_API_KEY`、整個 run 目錄搜不到金鑰值；批次 `COMPLETED`；假伺服器只收到目標驗證請求（校正 0） | `[w7-engine] 列 1：caps={"autoMutation":"ENABLED","selfEvolution":"ENABLED"}、假伺服器請求 goal；run 目錄 15 個檔` |
| 2 等級 7＋金鑰＋失敗步驟（假伺服器全回 500） | Brain 真的被呼叫（校正請求 3 次）、T1 只有 1 個 attempt 就直接升級（`STARTED→FAILED`）、`totalTokensUsed`＝1240、`reason`＝「引擎升級（ESCALATION）：Minimax API 故障，安全停止」；沒有 `evolved_*.yaml`、T2／T3 未執行 | `[w7-engine] 列 2：reason＝引擎升級（ESCALATION）：Minimax API 故障，安全停止；steps＝G1-T1:STARTED、G1-T1:FAILED；tokens＝1240；假伺服器請求＝correction、correction、correction` |
| 3 對照：等級 3＋金鑰（Brain 關）、同一個失敗夾具 | {OFF, ENABLED}；`enable_kernel_brain＝false`；T1 有 2 個 attempt（`STARTED→RETRYING→FAILED`）、零校正、演化提案 3 次；沒有 `evolved_*.yaml` | `[w7-engine] 列 3：steps＝G1-T1:STARTED、G1-T1:RETRYING、G1-T1:FAILED；tokens＝2480；假伺服器請求＝evolution、evolution、evolution` |
| 4 沒有金鑰、等級 7 | {UNAVAILABLE_NO_API_KEY, UNAVAILABLE_NO_API_KEY}；磁碟 config 沒有 `minimax` 區段；批次 `COMPLETED`（沒有因 `enable_kernel_brain` 缺金鑰而離開碼 1）；假伺服器零請求 | 通過（無 `console.log` 證據行；斷言在 spec 內） |
| 5 等級 3、沒有金鑰、旗標全 false | {OFF, OFF}；磁碟沒有 `minimax` 區段；`COMPLETED`（目標邊界的審核一律通過） | 通過（同上） |
| 6 旗標單獨生效（等級 3） | ①金鑰＋`agent.enableAutoMutation` ②金鑰＋`model.enableKernelBrain` 皆 {ENABLED, ENABLED} 且磁碟 `true`；③無金鑰＋`agent.enableSelfEvolution` {OFF, UNAVAILABLE_NO_API_KEY}；④金鑰＋`agent.enableSelfEvolution` {OFF, ENABLED}（`enable_kernel_brain＝false`） | `[w7-engine] 列 6①：agent.enableAutoMutation＝true、金鑰有 → {"autoMutation":"ENABLED","selfEvolution":"ENABLED"}、磁碟 enable_kernel_brain＝true`；`列 6②…同上`；`列 6③：agent.enableSelfEvolution＝true、金鑰無 → {"autoMutation":"OFF","selfEvolution":"UNAVAILABLE_NO_API_KEY"}、磁碟 enable_kernel_brain＝（無 minimax 區段）`；`列 6④：…金鑰有 → {"autoMutation":"OFF","selfEvolution":"ENABLED"}、磁碟 enable_kernel_brain＝false` |
| 7 凍結與缺席 | 清掉金鑰後詳情仍是列 1 的值；批次列表項沒有此欄；以 SQL 把 DB 欄位設 NULL 後詳情缺席或 null | `[w7-engine] 列 7：DB 欄位原值 {"autoMutation": "ENABLED", "selfEvolution": "ENABLED"}；設為 NULL 後詳情的 engineCapabilities＝null` |
| V-12 十六把 ENGINE 鍵 | 十四把鍵逐鍵設非預設值、起批次、磁碟 `config.yaml`／`playbook.yaml` 逐鍵吻合（含 `agent.maxRetries`→`playbook.yaml` 的 `global_invariants.max_retries_per_step`＝2）；`model.apiKey` 只經環境變數、不落檔；第十六把 `agent.enableAutoMutation` 在列 6①；結束後全部還原 | `[w7-engine] V-12：14 把鍵（另 model.apiKey 走 env）逐鍵吻合；磁碟 claude＝{"command":"…\\aisdlc-mock-claude.exe","extra_args":["--e2e-extra=1","--e2e-flag"],"continue_flag":"--continue-e2e","encoding":"utf-8-sig"}、token_guard＝{"compact_threshold_pct":71,"halt_threshold_pct":93,"auto_resume":true,"max_auto_resumes":7}、minimax＝{"base_url":"http://127.0.0.1:49902/v1/chat/completions","model":"e2e-model-v12","timeout_seconds":45,"enable_kernel_brain":true}`（`command` 的路徑前綴略去） |
| L-02 補充：標籤目錄 | `GET /settings` 的 50 個設定鍵每一把都有生效標籤；`ENGINE` 恰 16 把、`UNVERIFIED` 恰 `sdd` 三把 | `[w7-engine] 設定鍵目錄（GET /settings 的 effect）：STORED_ONLY 16、ENGINE 16、CONSOLE 15、UNVERIFIED 3；STORED_ONLY＝model.provider、…、autoclaude.dualReadResolution`（逐鍵清單見 log） |

**判定**：八個情境全通過。`API-AUT-06` 升 `✅ 已驗證`——口徑是「契約 E2E-14 列 1～7＋V-12 在本機真後端、真 Bridge、假模型伺服器上全部成立」。誠實劃界：①本列沒有 Docker 版，因為 Docker 全棧不載入 `e2e` profile、假伺服器從容器內不可達（契約 §5.0.1）；②「自演化」只產生提案、不套用（Architecture L-10）：列 2、列 3 都斷言沒有 `evolved_*.yaml`，所以 `selfEvolution＝ENABLED` 的意思是「有金鑰、會提案」，不是「引擎真的改寫了 playbook」；③驗的是請求發沒發、發幾次、磁碟設定是什麼、金鑰有沒有洩漏，不是 Brain 回覆的語意品質。整套之前我另外獨立單檔跑過一次（8 個通過，2.0 分鐘；當時檔名還是 `p10-w7-engine`，後改名為 `p9-w7-engine`，log 為 `logs\pw_engine1.log`），證據行與上表相同，只有假伺服器的隨機埠不同。

### 4.2 `US-M-10`（Agent 即時狀態：資源使用情況；契約 v1.3 E2E-14 列 8～9）

**契約怎麼說**：契約 v1.3 E2E-14 列 8～9（D-12）：Agent 即時狀態卡的「資源使用情況」要由真行程的取樣而來——Bridge 每 5 秒取樣引擎行程樹（`cpuPercent` 整機正規化、`memoryBytes` 為 RSS 總和、`processCount`、`sampledAt`），console-api 轉發到 `GET /executions/{id}` 的 `bridge.resources`，前端卡片顯示「CPU x.x%・記憶體 N MB・M 行程」；沒有資料時（終態、PAUSED、Bridge 不可達）為 `null`，卡片顯示單一「—」。**不得出現 `pid`**。W5 時此列是 `🟡`（Bridge 沒有資料來源），W7 補上來源，QA 要用兩端——本機（Windows 行程樹）與 Docker（Linux 容器內行程樹）——各驗一次。

**本機**（`p9-w7-resources.spec.ts`，三個情境；逐字節錄自 `logs\pw_final1.log`）：

| 契約列 | 驗什麼 | 當回合實測 |
|--------|--------|------------|
| 8 執行中 | 40 個任務的長批次（mock claude 預設延遲）：`bridge.resources` 欄位型別與範圍（`cpuPercent` 0～100 且一位小數、`memoryBytes` 正整數、`processCount` ≥ 1、`sampledAt` 帶時區）、第二次輪詢的 `sampledAt` 前進、整個回應沒有 `pid`；卡片格式符合契約 M-19，卡片的 `title`（取樣時間）隨輪詢前進 | `[w7-resources] 列 8：首筆樣本在起跑後 10ms 出現＝{"cpuPercent":0,"memoryBytes":12644352,"processCount":2,"sampledAt":"2026-10-16T18:06:08.047960+00:00"}；6.5 秒後第二筆＝{"cpuPercent":0,"memoryBytes":116178944,"processCount":7,"sampledAt":"2026-10-16T18:06:11.285525+00:00"}；畫面「CPU 0.0%・記憶體 12 MB・2 行程」（取樣時間 02:06:08）→ 之後 title 前進；批次形態＝40 任務／預設延遲` |
| 9 沒有資料時 | 終態與 PAUSED 的批次 `resources` 為 `null`／缺席、卡片單一「—」且沒有舊說明句；Bridge 被結束後 `bridge.connected＝false`、卡片「—」、頂列「Engine Bridge 未連線」；Bridge 重啟後該批次判為 `FAILED` | `[w7-resources] 列 9：終態 resources＝null、卡片「—」；PAUSED resources＝null、卡片「—」`；`[w7-resources] 列 9：Bridge 結束後 bridge＝{"connected":false,"instance":"e2e-bridge","checkedAt":"2026-10-16T18:08:40.222085800Z"}；畫面連線燈「Engine Bridge 未連線」、資源使用「—」`；`[w7-resources] 列 9：Bridge 重啟後 status＝FAILED、bridge＝{"connected":true,"instance":"e2e-bridge","status":"FAILED","runKnown":true,"checkedAt":"2026-10-16T18:08:45.400903Z"}` |

另在整套之前，我用契約字面的慢速形態（`E2E_MOCK_DELAY=8`、5 個任務）單獨跑過一次（`logs\pw_resources1.log`）：首筆 `{cpuPercent 0, memoryBytes 12558336, processCount 2}`、6.5 秒後 `{memoryBytes 115630080, processCount 7}`，畫面「CPU 0.0%・記憶體 12 MB・2 行程」——兩種批次形態得到同樣的量級。

**Docker 全棧**（`p9-w7-docker.stack.ts` 第 2 個情境「E2E-14 列 8～9（全棧）」；Bridge 容器內是 Linux 行程樹。Docker 全棧不載入 `e2e` profile，mock claude 用預設延遲，批次要靠任務數撐長——單一目標 90 個任務約一分鐘；逐字節錄自定稿版重跑 `logs\pw_docker3.log`，第二次 `logs\pw_docker2.log` 同形）：

| 契約列 | 驗什麼 | 當回合實測 |
|--------|--------|------------|
| 8 執行中 | `bridge.resources` 欄位集合恰為 `cpuPercent`、`memoryBytes`、`processCount`、`sampledAt`；型別與範圍同本機；整個回應沒有 `pid`；第二次輪詢的 `sampledAt` 前進；畫面格式符合 M-19 且卡片 `title` 隨輪詢改變 | `[w7-docker] 列 8（全棧）：首筆＝{"cpuPercent":0,"memoryBytes":7839744,"processCount":1,"sampledAt":"2026-10-16T18:47:55.675439+00:00"}；第二筆（與首筆的 sampledAt 相隔 67 秒）＝{"cpuPercent":0,"memoryBytes":49537024,"processCount":2,"sampledAt":"2026-10-16T18:49:02.364109+00:00"}；畫面「CPU 0.0%・記憶體 47 MB・2 行程」` |
| 9 沒有資料時 | 取消批次、進入終態後 `resources` 為 `null`；重新整理後卡片單一「—」且沒有舊說明句 | `[w7-docker] 列 9（全棧）：終態 CANCELLED，resources＝null，卡片「—」` |

兩筆樣本相隔 67 秒不是取樣週期：首筆是建完夾具後由 API 輪詢到的，之後要等限流視窗重置（`ensureQuota`）才能載入監控頁，第二筆是頁面載入後再輪詢一次的值。

**判定**：本機與 Docker 兩端都通過，`US-M-10` 升 `✅ 已驗證`（RTM 的 E2E 欄附加兩端的證據）。契約字面在兩端都成立：欄位集合與型別、`sampledAt` 前進、整個回應沒有 `pid`、終態為 `null`、卡片格式與「—」。兩端的數字不同是平台與批次形態使然（本機 Windows：首筆 2 行程、之後 7 行程、記憶體 12→116 MB；Docker Linux：首筆 1 行程、之後 2 行程、記憶體 7.5→47 MB），不影響判定。誠實劃界：①兩端的 CPU 都是 0.0%——mock claude 只在等待、沒有真負載，所以「高負載時 CPU 百分比準不準」這個情境驗不到（Bridge 側有自己的 `tests/test_resources.py`，其中 25 處提到 `cpu_percent`，本輪整套 Bridge pytest 通過，但我沒有逐條重驗換算公式）；②我沒有量取樣週期，兩端的兩筆樣本都是「輪詢到的兩筆」，不是連續樣本；③第一次 Docker 整套在這個情境失敗，是我自己測試的限流額度設計（§8.2），不是產品缺陷。

### 4.3 `NFR-9.1-05`（Markdown 預覽更新 < 100ms；D-13）

**口徑與歷史**：PRD NFR-9.1-05 的門檻是 < 100ms。W4 實測 20KB 文件的中位數 112ms、W5 實測 131ms（所以 W5 維持 `🟡`），W7-FE 自報優化後約 58ms——自報不採信，我自己重量。

**量法**（與 W4／W5 同一把尺，不為了過關而改尺）：`p9-w5-ui-evidence.spec.ts` 的 `NFR-9.1-05` 情境——真瀏覽器（Chromium）、production standalone 建置、在「新建專案」的說明欄編輯器一次貼入 N KB 的 Markdown，量到預覽穩定為止，每種大小量 7 次取中位數。我在這支 spec 只動一處：20KB 的斷言上限由 400ms 收緊為 100ms（與 1KB、5KB 同一個門檻，也是 PRD 原文），標題與註解同步更新。

**四次量測**（毫秒；前三次是在機器閒置時單獨跑這一支 spec——開跑前確認 CPU 約 2～4%，沒有其他測試或建置在跑；第四次是整套 213 個依序跑到它的時候）：

| 次序 | 1KB 中位數（最大） | 5KB 中位數（最大） | 20KB 中位數（最大） | 20KB 的七個樣本 | log |
|------|-------------------|-------------------|--------------------|----------------|-----|
| 1 閒置 | 9（27） | 17（22） | **57**（64） | 62, 57, 64, 57, 56, 62, 55 | `logs\pw_nfr1.log` |
| 2 閒置 | 10（27） | 17（22） | **57**（66） | 58, 66, 54, 56, 62, 57, 53 | `logs\pw_nfr2.log` |
| 3 閒置 | 9（28） | 18（29） | **62**（66） | 66, 62, 63, 61, 55, 64, 54 | `logs\pw_nfr3.log` |
| 4 整套中 | 9（27） | 20（24） | **57**（67） | 60, 67, 56, 54, 63, 56, 57 | `logs\pw_full1.log` |

逐字節錄（第 1 次與整套中的那次）：

```
[ui-evidence] NFR-9.1-05 1KB：樣本(ms)=27, 10, 9, 8, 8, 6, 9；中位數 9ms、最大 27ms
[ui-evidence] NFR-9.1-05 5KB：樣本(ms)=21, 17, 22, 17, 16, 16, 19；中位數 17ms、最大 22ms
[ui-evidence] NFR-9.1-05 20KB：樣本(ms)=62, 57, 64, 57, 56, 62, 55；中位數 57ms、最大 64ms
```

```
[ui-evidence] NFR-9.1-05 20KB：樣本(ms)=60, 67, 56, 54, 63, 56, 57；中位數 57ms、最大 67ms
```

**判定**：四次的 20KB 中位數都是 57～62ms，連單一最慢的樣本（67ms）都低於 100ms；整支 spec 四次皆通過。W5 維持 `🟡` 的理由（20KB 的 131ms）已消失，`NFR-9.1-05` 升 `✅ 已驗證`。誠實註記：這個數字對機器負載敏感（W5 報告已指出），我在閒置機與整套中各量了幾次，都達標；若在 CI 的多 CPU 並行下量，結果可能不同——但那不是這條需求的驗收環境（NFR 量測型，本機真瀏覽器）。

### 4.4 `NFR-9.3-01`（可用性 99.5%；D-14）

**口徑（主控裁決 D-14，W7_OVERVIEW §1）**：PRD §9.3 的「可用性 99.5%」本質是 30 天的營運觀測值，單次驗證給不出數字。所以這一列驗的是**量測機制**——規則寫對了、載入了、查得出值、告警與面板接得上、歷史撐得過重啟——並由 Grafana 持續顯示實際值；**不宣稱任何 30 天可用率的數值**。

**① README〈7〉的三條 promtool 指令逐字執行**（映像 `prom/prometheus:v3.15.0`、`--entrypoint promtool`、掛載 `AgentConsole/docker/prometheus`；不需要先起容器；log `logs\promtool3.log`）：

| 指令 | 實測 |
|------|------|
| `promtool test rules /etc/prometheus/tests/slo_test.yml` | `SUCCESS`，rc=0 |
| `promtool check rules /etc/prometheus/slo.yml /etc/prometheus/alerts.yml` | `slo.yml`：`SUCCESS: 5 rules found`；`alerts.yml`：`SUCCESS: 12 rules found`；rc=0 |
| `promtool check config /etc/prometheus/prometheus.yml` | `SUCCESS: 2 rule files found`、`prometheus.yml is valid prometheus config file syntax`；rc=0 |

**② 全棧上的實況**（`up -d --build --wait` 之後約 2.3 分鐘；log `logs\nfr931.log`；Prometheus 的 `startTime` 是 02:28:38（本機時間，即 UTC 18:28:38），全部是對 `http://localhost:9090`、`http://localhost:3001` 的唯讀查詢）：

| 項目 | 實測（逐字節錄） |
|------|------------------|
| 規則載入 | `group aisdlc-console-availability interval=15s`：`ConsoleDown type=alerting health=ok`；`group aisdlc-console-slo interval=60s`：`ratio_1d`、`ratio_7d`、`ratio_30d`（recording）與 `ConsoleAvailabilityBelowTarget`（alerting）皆 `health=ok lastError=''`；`all groups: aisdlc-backup=4, aisdlc-postgres=8, aisdlc-console-availability=1, aisdlc-console-slo=4`（共 17 條＝alerts.yml 12 條＋slo.yml 5 條） |
| 保留期 | `storage.tsdb.retention.time=5w  storage.tsdb.path=/prometheus`（5 週＝35 天，大於 30 天窗口） |
| 可用率查詢 | `aisdlc:console_availability:ratio_1d -> instance=backend:8080 job=spring-boot value=1`；`ratio_7d` 與 `ratio_30d` 同為 1；`up{job=spring-boot} -> 1`（卷是剛建的，歷史只有這幾分鐘，所以是 1——「歷史不足 30 天時以已有期間計算」，README〈7〉已寫明） |
| 告警 | `active alerts:`（空）——`ConsoleDown`、`ConsoleAvailabilityBelowTarget` 都沒有觸發 |
| Grafana 面板 | `title=Application Overview provisioned=True panels=23`；`panel id=21 type=row title=可用性 SLO（NFR-9.3-01：目標 99.5%）— slo.yml 的 recording rules`、`panel id=22 type=stat title=30 天可用率（目標 99.5%）`、`panel id=23 type=timeseries title=1 天可用率（另附 7 天、30 天窗口）` |
| 面板查詢真的跑得出來 | 對 Grafana 的 `POST /api/ds/query` 原樣重放面板 22、23 的查詢：`panel 22…：queries=1 HTTP=200 errors=0`、`panel 23…：queries=3 HTTP=200 errors=0` |

**③ 歷史撐過重啟**（`prometheus_data` 卷；`down` 之後只起 prometheus，最早一筆樣本的時間戳不變）：`prom_persist.ps1`（log `logs\prom_persist.log`）：`down` 前記下三條序列在 `[3h]` 窗口內最早一筆樣本的時間戳與筆數；`docker compose down`（不帶 `-v`）；確認卷還在、容器已不存在；`up -d --no-deps prometheus` 起一個新容器；再查一次。

| 序列 | `down` 前 | 重起後 |
|------|-----------|--------|
| `up{job="prometheus"}`（Prometheus 自身） | 140 筆，最早 `1792175325.301`（2026-10-16T18:28:45Z） | 140 筆，最早 `1792175325.301` |
| `up{job="spring-boot"}`（backend） | 139 筆，最早 `1792175330.118` | 139 筆，最早 `1792175330.118` |
| `aisdlc:console_availability:ratio_30d`（recording rule） | 33 筆，最早 `1792175374.743`（18:29:34Z） | 33 筆，最早 `1792175374.743` |

其餘逐字：`volume before: aisdlc_prometheus_data`；`mount: volume:aisdlc_prometheus_data->/prometheus`；`compose down rc=0`；`volume after down (must still exist): aisdlc_prometheus_data`；`prometheus container after down: []`；`compose up -d --no-deps prometheus rc=0`；`new container (startTime differs) = True`（Prometheus 的 `startTime` 由 18:28:38Z 變成 19:03:35Z）；三條序列都印 `first sample timestamp unchanged = True; samples not fewer = True`。

**判定**：量測機制通過，`NFR-9.3-01` 升 `✅ 已驗證`——口徑是 D-14 的「量測機制已驗證」，**不宣稱任何 30 天可用率的數值**。證據鏈：規則寫對（promtool 三條 rc=0、17 條規則 `health=ok`）→ 載入且查得出值（`ratio_1d`／`ratio_7d`／`ratio_30d`）→ Grafana 面板的查詢重放 HTTP 200、errors 0 → 告警會動（④）→ 歷史撐過重啟（③）。

**④ 告警真的會動**（意外取得的活體證據，不是我另外造的情境）：第一次 Docker 整套裡「重啟 backend」的情境（`p8-docker-stack.stack.ts` 第 292 行的 `docker restart aisdlc-backend`，backend 容器因此在 18:32:18Z 重新啟動）讓 `up{job="spring-boot"}` 出現一個 0 的樣本，`aisdlc:console_availability:ratio_30d` 降到 `0.9859154929577465`（＝70／71，低於目標 0.995），`ConsoleAvailabilityBelowTarget`（`for: 15m`）於 2026-10-16T18:32:34Z 進入 `pending`。時間線（`/api/v1/alerts` 與 `/api/v1/rules`；主機與 Prometheus 的時鐘實測相差不到 0.1 秒）：

| 時刻（UTC） | 觀察 |
|-------------|------|
| 18:32:34Z | `state=pending`、`activeAt=2026-10-16T18:32:34.74Z`（`ratio_30d` 0.9859） |
| 18:48:19Z | 仍是 `pending`：規則群組 `aisdlc-console-slo` 每 60 秒才評估一次，最近一次評估在 18:47:34Z（由後來查到的 18:50:34Z 與 60 秒間隔回推），距 `activeAt` 14 分 59.9 秒，差 0.1 秒 |
| 18:50:56Z | `state=firing`（規則 `lastEvaluation=18:50:34Z`、`health=ok`） |
| 18:53:27Z | 仍 `firing`，`value=0.989010989010989`（＝90／91），`ALERTS{alertname="ConsoleAvailabilityBelowTarget",alertstate="firing"}＝1` |

所以「掉到目標以下 → 15 分鐘後轉 firing」的 `for` 與求值路徑是通的。數字註記：三個窗口（1d／7d／30d）的值相同，是因為卷只有幾十分鐘歷史，且只有 1 個失敗樣本（0.9859＝70／71、0.989＝90／91 的分子分母推得）；這不是產品的可用率，是我自己重啟 backend 的副作用。

誠實劃界：①compose 沒有 Alertmanager（README〈7〉與 `slo.yml` 檔頭都明寫：告警只在 Prometheus 的 Alerts 頁與 Grafana 面板可見，不對外通知），所以「通知送達」沒有驗也不在範圍；②30 天窗口的真實可用率要靠這個卷在營運環境累積 30 天，本輪沒有也不可能驗；③`ConsoleDown`（`up == 0`、`for: 60s`）只驗到規則載入與 `health=ok`，沒有看到它觸發——backend 那次重啟只讓一個 15 秒的樣本為 0，不夠 60 秒。

### 4.5 `INF-VOL-07`（nginx_certs 卷與 HTTPS；D-15）

**契約怎麼說**（D-15）：RTM 的 `INF-VOL-07` 原為 `🟡`——`nginx_certs` 卷與 nginx 的 443 區塊「憑證實際放入與 HTTPS 區塊」缺實跑證據。W7 INFRA 補了 `https.conf.example`、`https-redirect.inc` 與 README〈14〉的步驟；QA 要在**全棧**上把 README〈14〉從頭到尾獨立重跑一遍，並依「回到只有 HTTP」復原，證明工作樹沒有殘留。特別要求：步驟 1a 前後，卷內 `fullchain.pem` 的指紋與 `notAfter` 必須改變（證明憑證真的換了）。

**我怎麼做**：`https_verify.ps1`（log `logs\https_verify.log`；全棧在跑；`default.conf` 先備份位元組，`finally` 一律復原；指令與 README〈14〉相同，PowerShell 形態）。

| README 步驟 | 當回合實測（逐字節錄） |
|-------------|------------------------|
| 前置 | `default.conf sha256=32FFEC463963B3E2CB6D3591482D1F3C00CA345A63AB70E320E86E143C15D584 bytes=926`；`Test-Path https.conf = False`；`git status docker/nginx: []`；啟用前 `http://localhost/nginx-health: 200 (curl rc=0)`、`https://localhost/nginx-health（-k）: 000 (curl rc=35)`（握手失敗） |
| 1a 之前：卷內憑證（舊） | `fullchain.pem` sha256 `3241a106f7ee495fd313ce70d5e3d2443e34608f081a4c6a7ec132b551e839c4`；`serial=3D10422123726BAAB41D64519E81F760518AFA91`；`notAfter=Nov 15 11:37:35 2026 GMT`；指紋 `37:24:05:D1:C6:D4:D6:64:…:DC:D3:BE:02`（檔案時間 Oct 16 11:39；推測是 INFRA 當時驗證所留） |
| 1a 重新產生（README 原指令，借用 `pgvector/pgvector:pg18` 內的 openssl） | `rc=0`；新 `fullchain.pem` sha256 `45a5296433d31264d520bc28bdc10f6d159a091769d63e02fb93e89f746a84a4`；`serial=0FF4E8F986C52C9B6386FD2A3B0D02D40463EBBB`；`notAfter=Nov 15 18:52:10 2026 GMT`；指紋 `C4:B7:2B:E9:28:BE:A6:A0:…:EA:C2:5E`；`subject=CN = localhost`；SAN `DNS:localhost, IP Address:127.0.0.1`。**sha256、serial、notAfter、指紋四個都變了**，卷內確實換成新憑證 |
| 2 複製 `https.conf` | `Test-Path https.conf = True` |
| 3 include 換成 `https-redirect.inc` | `舊 include 行出現次數＝1（應為 1）` |
| 4 檢查並重啟 | `nginx -t`：`syntax is ok`、`test is successful`，`nginx -t rc=0`；`restart rc=0`；重啟後 `starting`→等待後 `healthy`；`RestartCount: 0` |
| 5 驗證 | `HTTPS 健康（-k）: 200`；`80 埠健康: 200`；`80→443 轉址 /x: 301 https://localhost/x`；`/api/v1/projects: 301 https://localhost/api/v1/projects`；`HTTPS /: 200`、`/api/health: 200`、`/api/v1/projects: 401`、`/actuator/health: 403`；經 HTTPS 登入 `HTTP=200 curl rc=0 data 欄位＝[accessToken,refreshToken,expiresIn,role]`（token 值不印）；`ps nginx`（帶 profile）`Up 5 seconds (healthy)`、`0.0.0.0:80->80/tcp … 0.0.0.0:443->443/tcp`；不靠 `-k`：`--cacert＋--ssl-no-revoke: 200 ssl_verify_result=0`，不給 `--cacert` 的對照 `000 (curl rc=60)` |
| 回到只有 HTTP | `Test-Path https.conf = False（應為 False）`；`default.conf sha256 還原後＝32FFEC463963B3E2CB6D3591482D1F3C00CA345A63AB70E320E86E143C15D584；與備份相同＝True`；`nginx -t rc=0`、`restart rc=0`、`health after revert: healthy`；`http://localhost/: 200`、`http://localhost/x: 404`（不再轉址）、`https://localhost/nginx-health（-k）: 000 (curl rc=35)`（握手失敗，與啟用前相同）；`git status docker/nginx: []`、`git diff --stat default.conf: []` |

**判定**：`INF-VOL-07` 升 `✅ 已驗證`。「憑證放入 `nginx_certs` 卷 → 範例改成 `https.conf` → 443 起來、80 轉址 → 還原到只有 HTTP」整條在全棧上獨立重跑通過，且復原後工作樹乾淨（`git status`、位元組雜湊、握手結果三重確認）。誠實劃界：①驗的是自簽憑證與 `--cacert` 驗證鏈；CA 簽發的正式憑證（含中繼憑證的 `fullchain.pem`）的格式與續期流程沒有驗（README〈14〉也寫明不在範圍）；②README 要求使用者把 `server_name` 改成自己的網域，我只用 `localhost`；③驗完後卷 `aisdlc_nginx_certs` 內留下的是我這輪產生的自簽憑證（30 天、2026-11-15 到期），不是原本那一張——兩張都是 `CN=localhost` 自簽，影響只有指紋不同（記在 §12.4）。

## 5. 契約 v1.4 新增面（E2E-15、E2E-16、DAG 全螢幕）

### 5.1 E2E-15　AISDLC_SDD 接入（D-16；`API-ENG-01`、`NFR-OBS-01`、`BR-13`、`BR-14`）

`p9-w7-sdd.spec.ts`（十三個情境）。主體用**夾具**（`<E2E_ROOT>\sdd-fixture\AISDLC_SDD_v9.99`，spec 以 YAML 序列化器自己產生，不依賴被 git 忽略的真實檔）；另起三個純檔案模式的變體 Bridge：18082（夾具）、18083（`SDD_ROOT` 指向不存在的目錄）、18084（乾淨 clone 等價：只有入口文件）。檔案 ↔ API ↔ 畫面的比對，檔案那一邊由測試自己的 YAML 解析器（PyYAML）讀，不經 Bridge。

| 契約列 | 驗什麼 | 當回合實測（逐字節錄自 log） |
|--------|--------|------------------------------|
| 1 清單 | `projects` 恰兩筆且順序；壞檔、含空白檔名、`.yml` 不在其中；`fsm＝null`、沒有 `reason` | `[w7-sdd] 列 1：{"available":true,"version":"AISDLC_SDD_v9.99","projects":["e2e-alpha:IMPLEMENTATION","e2e-bravo:HUMAN_PENDING"]}` |
| 2 單一專案 | 欄位與檔案原樣：`decisionTrace` 是檔內七筆的最後五筆（snake_case 鍵保留）、`frozenStages`、`retryHistory`、`rtmCoverage＝null` | 通過（`humanPending.count`、`retryHistory.count` 與 `last`（加 `gate`）與夾具逐值相等） |
| 3 待人工 | `e2e-bravo`：`humanPending.count＝1` 且 `items[0].entered_at` 原樣 | 通過 |
| 4 找不到、壞檔、非法名 | `nope`→200＋`fsm_not_found`；壞檔→200＋`fsm_state_unreadable`；`a b`、`../x`→400（`errors[0].field＝project`） | 通過 |
| 5 檔案 ↔ API ↔ 畫面（NFR-OBS-01 補強） | 卡片的狀態、Sprint、更新時間（本機時區）、待人工、最近 5 筆決策（倒序）與夾具檔逐值一致，也與列 2 的 API 一致；改選 bravo 顯示等待人工確認 | `[w7-sdd] 列 5：alpha 畫面＝IMPLEMENTATION／Sprint 2／2026-10-16 09:02:03，5 筆決策倒序 r7→r6→r5→r4→r3；bravo＝等待人工確認` |
| 6 輪詢跟上 | 改寫檔案後下一輪輪詢更新（不整頁重載）；讀到寫一半的壞檔顯示「FSM 狀態檔無法讀取」，下一輪恢復 | `[w7-sdd] 列 6：改檔後卡片 30020ms 內更新為 PR_REVIEW／r8；壞檔顯示「FSM 狀態檔無法讀取」；恢復後下一輪回來；全程未重載` |
| 7 Bridge 不可達 | 200＋`bridge_unreachable`；卡片「Engine Bridge 無法連線」；重啟後下一輪復原 | `[w7-sdd] 列 7：Bridge 18082 結束 → 200／bridge_unreachable／卡片「Engine Bridge 無法連線」；重啟後下一輪復原為可用` |
| 8 SDD 目錄無效 | `/engines/sdd` 為 `sdd_unavailable`；該 Bridge 的 `/health/deep` 仍 200、`checks.sdd＝{ok:false,…}`、頂層沒有 `reason`；`/health` 200 | `[w7-sdd] 列 8：/engines/sdd＝{"available":false,"reason":"sdd_unavailable"}；18083 的 /health/deep＝200 checks.sdd＝{"ok":false,"latest":null,"reason":"SDD_ROOT 不是目錄：no-such-dir"}` |
| 9 乾淨 clone | `available＝true`、`projects＝[]`、`reason＝null`；`checks.sdd＝{ok:true, latest:AISDLC_SDD_v9.98}`；卡片「尚無 FSM 狀態檔」 | `[w7-sdd] 列 9：18084 的 /engines/sdd＝available true、projects 0；/health/deep checks.sdd＝{"ok":true,"latest":"AISDLC_SDD_v9.98"}；卡片「尚無 FSM 狀態檔」（Docker 全棧的另一半見 QA 報告）` |
| 10 權限 | 未認證 401；viewer／operator／admin 皆 200 | 通過 |
| 11 只讀 | 夾具目錄（遞迴）mtime 與大小快照在第 1～5、10 列前後、與第 6～9 列之後完全相同 | 通過（前半、後半兩個情境） |
| 12 真實檔（選跑） | `AISDLC_SDD/<LATEST>/build/reports/fsm/FSM-STATE-AISDLC_SDD.yaml` 存在才跑：`projects` 含 `AISDLC_SDD`、`fsm` 與該檔逐欄一致、畫面一致 | `[w7-sdd] 列 12：真實檔 FSM-STATE-AISDLC_SDD.yaml ↔ API ↔ 畫面一致：INIT／Sprint 1／2026-07-15T17:36:40+00:00／待人工 0／重試 0／清單含 AISDLC_SDD 與另 7 個專案`（該檔存在於本機，所以有跑；乾淨 clone 與 CI 沒有它） |

Docker 全棧的另一半（列 8～9 的 Linux 映像、`checks.sdd` 對掛載的真實 `AISDLC_SDD`、`/engines/sdd` 與主機上真實 FSM 檔逐值一致）：`p9-w7-docker.stack.ts` 的第 3、4 個情境，逐字節錄自定稿版重跑 `logs\pw_docker3.log`（第二次 `pw_docker2.log` 同形）：

| 項目 | 當回合實測 |
|------|------------|
| 全棧：Bridge 容器 `/health/deep` 的 `checks.sdd`（掛載真實 `AISDLC_SDD`）、`GET /engines/sdd` 與主機上真實 FSM 檔逐值一致、三個容器 healthy | `[w7-docker] 列 9／NFR-OBS-01（全棧）：checks.sdd＝{"ok":true,"latest":"AISDLC_SDD_v0.30"}；/engines/sdd＝AISDLC_SDD_v0.30（8 個專案）；AISDLC_SDD 的 INIT／Sprint 1／2026-07-16 01:36:40 與主機檔逐值一致` |
| 同一個 Bridge 映像（Linux，`aisdlc-engine-bridge:dev`）另起容器：乾淨 clone 等價（只有入口文件的唯讀掛載）與 `SDD_ROOT` 不存在 | `[w7-docker] 列 9（Linux 映像 aisdlc-engine-bridge:dev）：乾淨 clone 等價 checks.sdd＝{"ok":true,"latest":"AISDLC_SDD_v9.98"}、/sdd/fsm projects＝[]；SDD_ROOT 不存在 checks.sdd＝{"ok":false,"latest":null,"reason":"SDD_ROOT 不是目錄：dir"}、整體 200、/sdd/fsm＝503` |

兩邊的時間是同一個時刻：本機列 12 的 `2026-07-15T17:36:40+00:00`（UTC）＝畫面與 Docker 版顯示的本機時區 `2026-07-16 01:36:40`（UTC+8）。全棧上的 SDD 版本是 `AISDLC_SDD_v0.30`（當下的 LATEST，spec 以 SSOT 腳本現查、不寫死）；Linux 映像另起的容器用夾具版本 `v9.98`，與本機列 9 同形。兩個半邊合起來，E2E-15 列 8～9 在 Windows 本機與 Linux 容器兩個平台都成立。

### 5.2 E2E-16 列 1～2　探測預設改打深度探針（D-17；`US-M-10`、`UI-KPI-08`、`BR-26`）

`p9-w7-signoffs.spec.ts` 前兩個情境（乾淨資料庫的整套裡跑）：

| 契約列 | 驗什麼 | 當回合實測（逐字節錄自 `logs\pw_final1.log`） |
|--------|--------|----------------------------------------------|
| 1 探測預設值 | 全新資料庫：admin `GET /settings/autoclaude` 的 `healthCheckPath.value` 與 `defaultValue` 都是 `/health/deep`；`impactNote` 逐字等於附錄 C.5 | `[w7-signoffs] 列 1：healthCheckPath value＝/health/deep、defaultValue＝/health/deep、impactNote 與附錄 C.5 逐字相同` |
| 2 探測打深度探針 | ①另起 Bridge 18085（`PATH` 只剩空目錄、`git` 解析不到）：直連 `/health` 200、`/health/deep` 503（`checks.git.ok=false`、頂層 `reason` 以 `git:` 開頭）；`autoclaude.engineUrl` 指向它後 `bridgeConnected＝false`、`agentAvailability` 下降；②把 `healthCheckPath` 暫設 `/health`，同一個 Bridge 被判成功；③`engineUrl` 改指 18083（`SDD_ROOT` 無效）並還原成 `/health/deep`：`bridgeConnected＝true`、`agentAvailability` 不再下降、`/engines/sdd` 為 `available＝false`；結束還原設定並停掉 18083～18085 | `[w7-signoffs] 列 2：①18085（git 不在 PATH）bridgeConnected＝false、agentAvailability 99.5→99.1；②改 /health 後 bridgeConnected＝true；③18083（SDD_ROOT 無效）bridgeConnected＝true、agentAvailability＝99.1、/engines/sdd＝available false／sdd_unavailable` |

**判定**：兩列通過。`US-M-10`／`UI-KPI-08` 因此從「探測只打淺層 `/health`」變成「探測打深度探針、503 計為失敗、`sdd` 無效不算」（審查 I-03）。數字註記：`agentAvailability` 的絕對值是滾動視窗內成功樣本占比，與當時視窗裡有幾個樣本有關——同一個情境我跑了三次，乾淨資料庫整套裡是 100→99.4→99.4、最終版重跑是 99.5→99.1→99.1、早先的單檔跑是 100→96.3→96.6——所以判準是「下降」與「不再下降」，不是某個固定值。

### 5.3 E2E-16 列 3～6　待審批清單與計數同源、儀表板卡、通知鈴（D-18；`API-SGN-05`、`API-NTF-01`）

`p9-w7-signoffs.spec.ts` 的列 3～6（四個情境）：

| 契約列 | 驗什麼 | 當回合實測（逐字節錄自 `logs\pw_final1.log`） |
|--------|--------|----------------------------------------------|
| 3 清單與計數同源 | 四種待簽草案各造一筆（專案、目標、任務、停在 `PARSED` 的匯入記錄；匯入記錄造兩筆：檔名一筆、「貼上文字」一筆，所以 `imports` 增量是 2）加不該計入的干擾列六個（已簽專案、軟刪專案與其未軟刪的目標及任務、`UPLOADED` 與 `REJECTED` 的匯入記錄各一）；`counts` 各項相對基線恰 +1、`counts.total`＝`summary.pendingSignoffs`、`items` 的 `createdAt` 升冪、各 `kind` 欄位正確（`IMPORT` 的 `projectId`／`projectName`／`parentId` 為 null）、干擾列都不出現 | `[w7-signoffs] 列 3：基線 counts＝{"projects":1,"goals":2,"tasks":3,"imports":1,"total":7}；造出後 counts＝{"projects":2,"goals":3,"tasks":4,"imports":3,"total":12}（delta {"projects":1,"goals":1,"tasks":1,"imports":2,"total":5}）；summary.pendingSignoffs＝12；6 個干擾列（已簽專案、軟刪專案與其目標及任務、UPLOADED 與 REJECTED 的匯入記錄）皆未出現`（軟刪旗標是 `is_deleted`，`deleted_at` 只記時間，干擾列兩個欄位都設；基線不是 0 是因為這次重跑沒有重置資料庫，判準本來就是「相對基線」） |
| 4 `limit` 與權限 | `?limit=2` 回最早的兩筆且 `counts` 不變；`0`、`201`、`abc` → 400（`errors[0].field＝limit`）；未認證 401；viewer 200 | 通過（無 `console.log` 證據行；斷言在 spec 內） |
| 5 儀表板卡與簽核後同步 | 徽章＝KPI「待審批草案數」＝`counts.total`、項目數＝`min(total, 50)`；依序對 PROJECT、GOAL、TASK、IMPORT 各審批一筆，卡片、徽章、KPI 同步減 1（不整頁重載）；各 `kind` 連結符合 G-10 | `[w7-signoffs] 列 5：儀表板徽章＝KPI＝API total＝12；審批 PROJECT、GOAL、TASK、IMPORT 各一筆後 12→8，卡片項目數、徽章、KPI 同步；連結落點符合 G-10` |
| 6 通知鈴連結 | 「待簽核草案」恆為 `/#pending-signoff`；「待審核項目」「未確認告警」在專案頁導向該專案的 `/execute`、`/monitor`，在儀表板導向 `/projects`（已知限制 G-G4） | `[w7-signoffs] 列 6：儀表板 → signoffs＝/#pending-signoff、reviews／alerts＝/projects；專案頁 → reviews＝…/execute、alerts＝…/monitor` |

**判定**：四列通過，`API-SGN-05` 與 `API-NTF-01` 的同源不變量成立（`counts.total`＝通知摘要＝儀表板徽章＝KPI，審批後同步減少）。誠實註記：通知鈴在儀表板上的「待審核項目」「未確認告警」連結落到 `/projects`（契約已登記為已知限制 G-G4），不是 bug。我另在獨立單檔重跑（非乾淨庫，基線 17）也得到同樣的相對增量（delta 與 `total` 22→18），代表判準是「相對基線」而不是絕對值。

### 5.4 E2E-16 列 7～10　refresh 輪替、登出撤銷、Redis 降級（D-19；`API-AUTH-03`、`API-AUTH-02`、`INF-SVC-07`）

`p9-w7-signoffs.spec.ts` 的列 7～9（本機，三個情境）與 `p9-w7-docker.stack.ts` 的列 10（Docker 全棧）：

| 契約列 | 驗什麼 | 當回合實測（逐字節錄自 `logs\pw_final1.log`） |
|--------|--------|----------------------------------------------|
| 7 refresh 輪替撤銷 | `login` 得 RT1；`refresh(RT1)` 得 RT2；再 `refresh(RT1)` → 401 `INVALID_REFRESH_TOKEN`；`refresh(RT2)` 仍 200（換出 RT3）；RT1 當 Bearer 仍是 401 `TOKEN_INVALID` | `[w7-signoffs] 列 7：login→refresh(RT1)=200→refresh(RT1)=401 INVALID_REFRESH_TOKEN→refresh(RT2)=200；RT1 當 Bearer=401 TOKEN_INVALID` |
| 8 登出撤銷 | `logout` 204 之後 `refresh` 401；垃圾字串、已撤銷的 RT、access token 皆 204（不洩漏有效性）；缺或空白 `refreshToken` → 400（`errors[0].field＝refreshToken`）；全程不帶 Authorization | `[w7-signoffs] 列 8：logout=204→refresh=401 INVALID_REFRESH_TOKEN；垃圾／已撤銷／access token 皆 204；缺或空白 refreshToken=400（field=refreshToken）；皆未帶 Authorization` |
| 9 前端登出流程 | 瀏覽器按「登出」送出恰一個 `POST /api/v1/auth/logout`（body 只有 `refreshToken`）、導向 `/login`、session 清空；該 RT 之後換新 401；另把 logout 請求以網路攔截弄成失敗再登出一次，仍導向 `/login` 並清 session | `[w7-signoffs] 列 9：登出送出 1 個 POST /auth/logout（body 只有 refreshToken）→ /login、session 清空、舊 RT 換新 401；logout 被攔截失敗時仍導向 /login 並清 session（該 RT 因 logout 沒到後端，換新 200）` |
| 10 Redis 降級（Docker 全棧） | 全棧（Redis 啟用；`p9-w7-docker.stack.ts`）：①Redis 在線登出→撤銷名單寫進 Redis（鍵數＋1）；②停掉 `aisdlc-redis` 之後：換新仍可用（200）、輪替後舊 token 再換新 401 `INVALID_REFRESH_TOKEN`、登出 204 且之後換新 401（撤銷在降級的記憶體名單仍有效）、`/actuator/health` 維持 UP、backend 容器維持 healthy、日誌恰一筆 WARN（降級）；③Redis 回來後恰一筆 INFO（恢復）、WARN 不再增加、新的撤銷再寫進 Redis（鍵數＋1） | `[w7-docker] 列 10：Redis 在線登出→鍵 3→4；停掉後 換新=200、舊 token 再換新=401 INVALID_REFRESH_TOKEN、登出=204、之後換新=401；actuator UP、backend healthy；WARN 1 筆；啟動後 INFO 1 筆、WARN 仍 1 筆、新撤銷寫進 Redis（鍵 4→5）`（定稿版 `pw_docker3.log`；第二次 `pw_docker2.log` 是鍵 1→2、2→3，同形——鍵數是接續累積的） |

**判定**：列 7～10 通過（列 10 在 Docker 全棧：Redis 停掉時撤銷名單降級為記憶體、backend 容器維持 healthy、日誌恰一筆 WARN，Redis 回來後恰一筆 INFO 且新撤銷回寫 Redis；backend 自己的 WARN 字樣也寫明「降級期間的撤銷只對本實例有效，Redis 恢復後不回補」）。`API-AUTH-02`（換新）與 `API-AUTH-03`（登出與撤銷名單）的契約字面都成立。列 9 的最後半句是契約 §1.9.1（第 1220 行）明文接受的代價：前端登出是 fire-and-forget，logout 沒到後端時該 refresh token 在到期前仍可換新，所以撤銷是盡力而為，不是缺陷（觀察 O-29）。本機 e2e profile 使用記憶體撤銷名單（`store=memory`），Redis 路徑只在 Docker 全棧驗（列 10）。

### 5.5 DAG 全螢幕（E-22，D-01；`US-E-09`）與 US-P-04 編輯鎖定（審查 V-04）

`p9-w7-ui.spec.ts` 的前兩個情境（真後端、真瀏覽器 Chromium 1440x900）：

| 項目 | 驗什麼 | 當回合實測（逐字節錄自 `logs\pw_final1.log`） |
|------|--------|----------------------------------------------|
| DAG 全螢幕（契約 §4.2 E-22；審查 D-01） | 在執行頁（有跑完的批次）點「全螢幕」→ 覆蓋層尺寸等於視窗；展開／收合狀態進出都保留；`Esc` 與「結束全螢幕」都能關；關閉後焦點回到「全螢幕」鈕；全螢幕內 axe 零違規 | `[w7-ui] E-22：全螢幕尺寸 1440x900＝視窗 1440x900；Esc 與「結束全螢幕」都關閉並把焦點還給「全螢幕」鈕；收合／展開狀態進出保留；全螢幕內 axe 零違規` |
| US-P-04 編輯鎖定（審查 V-04） | 真的執行中的批次（單一目標 25 個任務的長批次，mock claude）讓專案處於 EXECUTING：先查 API 確認專案狀態是 `EXECUTING`，再開編輯頁看到橫幅「專案執行中：只能修改名稱與說明，其他欄位已鎖定。」、執行路徑與自治等級停用、專案名稱可編輯；批次取消、專案離開 EXECUTING 後重新整理，欄位解鎖、橫幅消失 | `[w7-ui] US-P-04：EXECUTING 專案的編輯頁顯示鎖定橫幅；執行路徑、自治等級停用；名稱可編輯`；`[w7-ui] US-P-04：批次取消、專案離開 EXECUTING 後重新整理，欄位解鎖、橫幅消失` |

**判定**：兩項通過。`US-E-09` 的「DAG 全螢幕」從契約 D-01 的「被默默拿掉」變成有真瀏覽器驗證的功能；`US-P-04` 以前只有請求轉換的單元測試與 API 層 409，RTM 自己註記「無法用真資料驗證 UI 行為」的理由（後端沒有把專案轉成 EXECUTING 的入口）在 Phase 4 之後已不成立，現在由真後端的長批次補上（V-04）。

## 6. 完整性審查 27 筆逐筆處置

做法：每筆都重讀審查原文的「證據」欄，再用本輪的指令或讀檔當面核對；結論分四類——**已修且核實**（本波已改，QA 實跑／實讀證明）、**已登記且核實**（以文件登記取代程式修改，登記內容與程式相符）、**裁決保留**（掌舵者或主控已裁，QA 只驗證登記存在）、**誤報**（寫明為何不是）；另有兩筆是組合結論（V-09「部分關閉＋裁決保留」、I-04「實驗確認分歧」）。27 筆實際分佈：18 筆已修且核實、7 筆已登記且核實、V-09 一筆、I-04 一筆；本輪沒有判為誤報的項目，單獨的「裁決保留」只出現在 V-09 的後半。27 筆之中沒有「審查指出缺、而本波沒修也沒登記」的項目；本輪新登的缺陷有三筆：I-04 實驗確認的分歧（DEF-AC-012，P4）；FE 回填〈九〉第 3 點留給「另案評估」的內嵌 HTML 疑慮經實測確認為資安缺陷（DEF-AC-013，P2）；以及從 Docker 容器日誌掃出的 SSE 客戶端斷線被當成「未預期的例外」記 ERROR（DEF-AC-014，P3）——後兩筆不在 27 筆之內，是 QA 另外探測出來的，見 §10。

| 編號 | 結論 | 核實證據 |
|------|------|----------|
| L-01 缺列（compose 的 minio-certs 與四個卷） | 已修且核實 | RTM 補 `INF-SVC-16`（minio-certs）、`INF-VOL-09`（pg_socket）、`INF-VOL-10`（minio_data）、`INF-VOL-11`（minio_certs）、`INF-VOL-12`（prometheus_data）；Docker 全棧實查見 §8.3：`docker ps -a` 的 16 個容器（14 個長駐 healthy，加 `aisdlc-minio-certs`、`aisdlc-minio-init` 兩個一次性 job 的 `Exited (0)`）與 `INF-SVC-01`～`16` 逐一對應；`docker volume ls` 的 12 個 `aisdlc_*` 卷與 `INF-VOL-01`～`12` 逐一對應（原有 8 個加本輪補的 4 個）。四個新卷與 minio-certs 的實況：minio-certs `Exited (0)`、minio 以 `service_completed_successfully` 相依、憑證 `CN=minio`；`pg_socket` 內 pgbackrest 容器看得到 primary 的 `.s.PGSQL.5432`；`minio_data` 內有 bucket `aisdlc-db-backup`；`minio_certs` 內有 `private.key`（600）與 `public.crt`；`prometheus_data` 的持久性見 §4.4 |
| L-02 缺列（只儲存／未驗設定鍵沒有追溯） | 已修且核實 | RTM 補 `API-SET-11`（設定鍵生效標籤目錄）；`p9-w7-engine.spec.ts` 的 V-12 情境斷言 `GET /settings` 的標籤目錄：實測 `GET /settings` 的 50 個設定鍵每一把都有生效標籤：`ENGINE` 16、`CONSOLE` 15、`STORED_ONLY` 16、`UNVERIFIED` 3（恰為 `sdd` 三把）（§4.1 末列，spec 另印出 16 把 `STORED_ONLY` 的鍵名） |
| L-03 Virtual Threads 範圍沒登記 | 已登記且核實 | ADR-001 D1 第 54 行寫明只有 `StreamConnection.java:64`、`RunConsumers.java:90` 兩處明確用虛擬執行緒，並自陳「4.1 的預設值**未驗**」。QA 補驗這個未驗：對執行中的 backend 以 `jcmd <pid> Thread.print` 取傾印（`logs\thread_dump_backend.txt`），Tomcat 請求執行緒名稱是 `http-nio-18080-exec-1`…`exec-6`（共十三個，皆為平台執行緒；虛擬執行緒的 Tomcat 處理器會叫 `tomcat-handler-N` 且不在傾印中），所以 Spring Boot 4.1 在本專案設定下**預設不啟用**虛擬執行緒（本專案 yml 沒有設 `spring.threads.virtual.enabled`）。建議 ADR-001 第 54 行把「未驗」改成這個實測結論 |
| L-04 缺 Clean Architecture 分層鎖的列與目錄樹差異說明 | 已修且核實 | Architecture §4.1.1（第 264 行起）寫明與 PRD §4.1 目錄樹的差異（沒有 `adapter/in/sse`、`adapter/out/messaging`、`domain/event`）；RTM 補 `NFR-9.4-06`；`gradlew clean build` 的 `ArchitectureRulesTest` 八條規則 0 失敗（`backend\build\test-results\test\TEST-com.aisdlc.console.architecture.ArchitectureRulesTest.xml`：tests=8、skipped=0、failures=0、errors=0） |
| V-01 `ImportRecordMapperTest` 測試名過期；UI-SCR-07 的情境數 | 已修且核實 | 我把 `check_test_refs.py` 強化成「Java 引用必須對得到 `\bname\s*\(` 方法宣告」，基線掃出 12 處失配（涉及 US-T-06、API-TSK-06、US-I-06、US-I-10、API-IMP-03、API-TSK-04、NFR-SEC-03、API-AUT-04、NFR-9.4-03、INF-DB-12／14／15 共 12 列）；合併後 0 處（§9）。`ImportRecordMapperTest` 新名 `…NorTheParseResultNorTheWarningsAndOptions` 在 `ImportRecordMapperTest.java:107`。`execute.mock.spec.ts` 現有二十一個情境（`npx playwright test --list` 現查），UI-SCR-07 的「十五個情境」已改 |
| V-02 十三列實作欄「待填」、十四列測試欄「待填」 | 已修且核實 | 依列填實：備份類指向 `docker/pgbackrest/**`、`INF-DB-17` 指向 `V5__seed_engine_configs.sql` 與 `SchemaMigrationIT` 的四個方法、量測型寫「量測型，無專屬實作檔」；合併後 `待填` 只剩 0 列（Grep 現查，§9） |
| V-03 八列「已驗證」的實作欄殘留過期待辦字樣 | 已修且核實 | US-P-04、NFR-9.2-01、NFR-9.3-04、NFR-9.4-01、NFR-9.4-02、NFR-9.4-04、NFR-XPL-04、UI-A11Y-01 逐列改成現況；每句都先查證事實再改（例：NFR-XPL-04 的 `gradlew` 索引模式已由主控 2026-10-15 裁決 D-2，Implementation_Plan 決策表；NFR-9.3-04 的 restore 已於 W5 完成＝`API-PRJ-06`） |
| V-04 US-P-04 的 UI 鎖定沒有任何元件或 E2E 驗證 | 已修且核實 | `p9-w7-ui.spec.ts`「US-P-04」：真後端、真的執行中批次，專案編輯頁顯示橫幅「專案執行中：只能修改名稱與說明，其他欄位已鎖定。」、執行路徑與自治等級停用、「專案名稱」可編；批次取消後解鎖（§5.5 同表） |
| V-05 六十三列 INF 的「已驗證」只有開發者自述 | 已修且核實 | Docker 全棧唯讀探查 `inf_probe.ps1`（`logs\inf_probe.log`），逐組留證並補進各列 E2E 欄；探不到的如實寫「未逐列重驗」（§8.3）：63 列中 56 列完整重驗、6 列部分重驗（`INF-VOL-01`～`04`、`INF-VOL-08` 的重起後資料仍在，加 `INF-DR-06` 的重建）、1 列未逐列重驗（`INF-DR-17` 手動 failover，破壞性）；沒有任何一列被證偽，逐組結果與備份起點的發現見 §8.3 |
| V-06 NFR-OBS-01 驗的不是 PRD 的四源 | 已修且核實 | Console 後端新增 `GET /engines/sdd`（API-ENG-01），E2E-15 列 5 與列 12 把「FSM 檔 ↔ API ↔ 畫面」逐值比對補進 NFR-OBS-01（`p9-w7-sdd.spec.ts`；列 12 用真實 `AISDLC_SDD/AISDLC_SDD_v0.30/build/reports/fsm/FSM-STATE-AISDLC_SDD.yaml`：INIT／Sprint 1／updated_at `2026-07-15T17:36:40+00:00` 三方一致）；原有的 Bridge／PG／SSE 一組維持。「引擎執行邏輯」那一源仍是 Bridge 對引擎行程的觀測，沒有另一份獨立真相可比（§11） |
| V-07 前端覆蓋率只量子集，口徑沒登記 | 已登記且核實 | ADR-001 第 225 行（§4 偏離表）與 G-21（第 253 行）登記：只量 `vitest.config.mts` 的 `coverage.include`（三十一項，其中兩個 glob）、branches 門檻 60；`vitest.config.mts` 實數 31 項與 ADR 相符。RTM `NFR-9.4-02` 的 E2E 欄已寫明口徑，並附本輪一次全量範圍的資訊值：閒置機上重跑（§3.2）：config 口徑 Statements 95.61%、Branches 89.71%、Functions 97.44%、Lines 97.17%；**全量範圍的資訊值**（把 `coverage.include` 換成 `app`、`components`、`lib`、`hooks` 底下全部 ts／tsx、排除測試與 d.ts、門檻設為 0，只當資訊）Statements 81.51%（3709／4550）、Branches 75.94%（3107／4091）、Functions 79.47%（1150／1447）、Lines 82.28%（3190／3877）——也都高於 70／60 的門檻。所以「只量子集」的口徑雖然寬鬆，全量也沒有掉到門檻以下（`logs\gate_fe_vitest_wide.log`） |
| V-08 UI 沒有與設計稿逐畫面比對 | 已修且核實 | §7：九畫面＋全域版面的 DOM 結構斷言（`p9-w7-ui.spec.ts`）與人眼逐張對照，寫進 `UI-SCR-01～09` 的 E2E 欄 |
| V-09 Playwright E2E 沒有持續重跑 | 部分關閉＋裁決保留 | `agentconsole-ci.yml` 已有 Playwright mock spec 的 job（`npx playwright test mock.spec --output=test-results-mock`，第 124～135 行，路徑過濾含 `AgentConsole/**`），所以 `*.mock.spec.ts` 每次 push 都機械重跑；真後端 E2E 仍是人工輪跑（D-20：需要真 Bridge＋PG＋mock claude，CI 沒有這套環境）。`.github` 不在本專案可改範圍，不登缺陷 |
| V-10 RTM 檔頭與 §3.2 數字不一致 | 已修且核實 | §3.2、§3.3 以腳本依各列的 ID 前綴、層與 Phase 欄重算，**方法先自證**：對 HEAD 的 RTM 扣掉 W5 新增的三列後重算，與檔內舊表逐行相同；檔頭與 §1.2 的列數同步更新（§9） |
| V-11 Architecture／契約／程式註解四處與實作不符 | 已修且核實 | ①`Architecture.md:1082` 的 `autoclaude.dalBackend` 改為「無有效對映」、標 ⛔；②`Architecture.md:457` 與 `:659` 改成位移存 DB、限流記憶體，且已註明訂正來源；③契約 §4.2 的 E-22、§4.6 的 G-E1／G-E4 已更正（DAG 全螢幕實作、任務層級範圍）；④`AgentBridge.listCheckpoints` 已從 `backend/src/main` 刪除（Grep：現在只剩 `MiniRun.java:95` 的一句註解說明它已刪除） |
| V-12 十五把引擎生效鍵只有三把有行為證據 | 已修且核實 | `p9-w7-engine.spec.ts` V-12：附錄 C 標 ENGINE 的鍵逐鍵設非預設值、起一個批次、讀磁碟上的 `config.yaml`／`playbook.yaml` 逐鍵吻合，結束後還原；實測（§4.1）：標籤目錄 `ENGINE` 恰 16 把；其中十五把各設一個非預設值並起批次——十四把逐鍵吻合（含 `agent.maxRetries`→`global_invariants.max_retries_per_step`＝2）、`model.apiKey` 只經環境變數；第十六把 `agent.enableAutoMutation` 在列 6①；結束後全部還原 |
| D-01 DAG「全螢幕」被默默拿掉 | 已修且核實 | `DagCard.tsx` 加全螢幕（契約 §4.2 E-22；ADR-001／契約登記）；`p9-w7-ui.spec.ts` 真瀏覽器：覆蓋層尺寸等於視窗、Esc 與「結束全螢幕」都能關、焦點歸還「全螢幕」鈕、展開／收合狀態進出保留、全螢幕內 axe 零違規（§5.5） |
| D-02 專案詳情的「匯出」沒做且沒登記 | 已登記且核實 | ADR-002 §4 第 10 項（第 132 行，主控 2026-10-16 裁決保留）；`p9-w7-ui.spec.ts` 畫面 3 斷言「不提供匯出」 |
| D-03 任務詳情第三張卡與暫停／取消 | 已登記且核實 | ADR-002 §4 第 4 項更正理由、第 11 項補登（第 126、133 行）；`p9-w7-ui.spec.ts` 畫面 5 斷言沒有暫停／取消、沒有「執行時長」卡 |
| D-04 公告列五個靜態字樣 | 已登記且核實 | 契約 §4.6 G-G5（第 2182 行）登記為靜態標示（`TopRegion` 以 `<span>` 呈現）；`p9-w7-ui.spec.ts` 全域版面逐字斷言公告列各項存在 |
| I-01 AISDLC_SDD 只接上一個點 | 已修且核實 | API-ENG-01（`GET /api/v1/engines/sdd`）、監控頁「AISDLC_SDD 引擎」卡；E2E-15 十三個情境（§5.1）；Docker 全棧半邊 `checks.sdd＝{"ok":true,"latest":"AISDLC_SDD_v0.30"}`、`/engines/sdd` 回 8 個專案且 INIT／Sprint 1／更新時間與主機上的真實 FSM 檔逐值一致，Linux 映像另起容器的乾淨 clone 與 `SDD_ROOT` 不存在兩種情境也成立（§5.1） |
| I-02 PRD 寫的 SSE 推 FSM、decompose 呼叫 SDD skill、signoff 對應 HUMAN_PENDING | 已登記且核實 | ADR-001 D22 與 §4 第 222～224 行登記三項偏離（FSM 不走 SSE 改 30 秒輪詢；`/decompose` 只用 `GoalDecomposer`、SDD 規格走路徑 A；signoff 與 HUMAN_PENDING 只做語意對映、Console 唯讀不回寫 FSM-STATE）。登記與程式相符的證據：E2E-15 列 6 在檔案改寫後 30 秒內（實測 30070ms）卡片更新、全程未重載；`humanPending` 顯示為唯讀（列 3） |
| I-03 探測環打淺層 /health | 已修且核實 | D-17：探測預設改 `/health/deep`；E2E-16 列 1（`healthCheckPath` 的 value＝defaultValue＝`/health/deep`，`impactNote` 與附錄 C.5 逐字相同）、列 2（`git` 不在 PATH 的 Bridge：直連 `/health` 200、`/health/deep` 503，`bridgeConnected` 為 false、`agentAvailability` 下降（最終版重跑 99.5→99.1；單檔 100→96.3，絕對值隨視窗樣本數而異，§5.2）；改設 `/health` 後回 true；`SDD_ROOT` 無效的 Bridge 不拖累探測：`bridgeConnected` 為 true、`/engines/sdd` 為 `sdd_unavailable`）（§5.2） |
| I-04 Bridge 與 SSOT 對 SDD LATEST 的判定可能分歧 | **實驗確認分歧**（登 DEF-AC-012，P4） | Architecture §12.2 的 V-11 要求 W7-QA 以只存在於工作樹的 `AISDLC_SDD_v9.99` 比對。我在 scratchpad 建拋棄式 git repo（不碰真實的 `AISDLC_SDD/`）：v0.29、v0.30 已 commit，v9.99、`v0.31.bak`、`v0.30 - Copy` 只在工作樹。SSOT（`tools/lib/sdd_latest.py` 載入的 `AISDLC_SDD/scripts/sdd_version.py`，以 `git ls-files` 判定）回 `AISDLC_SDD_v0.30`（stderr 警告 v9.99 未 tracked）；Bridge `discover_sdd_root` 與 `load_settings(SDD_ROOT=<父目錄>)` 都回 `AISDLC_SDD_v9.99`。兩者都正確排除 `.bak` 與「- Copy」；v9.99 `git add` 後 SSOT 也回 v9.99；非 git 目錄兩者一致。log：`logs\i04_probe.log`。CI 路徑過濾也核實：`agentconsole-ci.yml` 第 21～26、29～34 行的 `paths` 不含 `AISDLC_SDD/**`，SDD 側改 FSM 格式不會觸發 Console 的 CI。處置建議在 §10 |
| I-05 待審批清單與徽章不是同一個集合 | 已修且核實 | API-SGN-05（`GET /api/v1/signoffs/pending`）與同源述詞 `PendingSignoffSql`；E2E-16 列 3～6（§5.3）：四種草案各造一筆加五個干擾列，`counts.total`＝通知摘要的 `pendingSignoffs`＝儀表板徽章＝KPI，依序審批後同步減少 |
| I-06 後端沒有使用 Redis、登出沒有撤銷名單 | 已修且核實 | API-AUTH-03（`POST /api/v1/auth/logout`）與 refresh token 撤銷名單（Redis 優先、不在線降級記憶體）；E2E-16 列 7～9（本機）、列 10（Docker 全棧停掉 Redis）（§5.4）：Redis 在線登出使撤銷鍵 3→4；停掉 Redis 後換新 200、舊 token 再換新 401 `INVALID_REFRESH_TOKEN`、登出 204、之後換新 401，`/actuator/health` 維持 UP、backend 容器 healthy、日誌恰一筆 WARN；Redis 回來後恰一筆 INFO、新撤銷寫進 Redis（鍵 4→5）。降級期間的撤銷只對本實例有效、Redis 恢復後不回補，是契約與 WARN 字樣都明寫的取捨 |
| I-07 Console 的斷點清單與步驟時間軸依賴 Bridge 的 DB 模式 | 已登記且核實（並補驗純檔案模式的實際表現：空的） | Architecture §12.1 的 L-12 與 `Architecture.md:815` 已登記；死碼 `AgentBridge.listCheckpoints` 已刪（V-11④）。**本輪補驗**（`p9-w7-purefile.spec.ts`，§8.4）：同一份夾具各跑一次——DB 模式 Bridge：批次 `COMPLETED` 3／3、步驟時間軸 6 筆、斷點 3 個；純檔案模式 Bridge（沒有 `BRIDGE_DB_DSN`）：批次一樣 `COMPLETED` 3／3，但**步驟時間軸 0 筆、斷點清單 0 個**。也就是 L-12 的警語屬實且可量化：純檔案模式只適用於單獨驗 Bridge，不適用於 Console 的完整功能。`AgentConsole/CLAUDE.md` 的環境變數表仍只寫「無 DSN＝純檔案模式」，沒有加註（觀察 O-33，§12） |

## 7. 審查 V-08：設計稿九畫面逐張對照

**做法**（兩層，缺一不可）：

1. **DOM 結構斷言**：`p9-w7-ui.spec.ts` 的 `V-08` 區塊（十個情境：全域版面一個、畫面 1～9 各一個）。每個設計稿元素都是一條 `expect.soft(…toBeVisible)`，失敗時一次列完而不是遇到第一個就停；已登記的差異另用「登記的差異」斷言（例如 KPI 四張改了標籤、底部多「刪除專案」、不提供「匯出」），不計為缺口。共 **145** 項逐項斷言（全域 21、畫面 1 13、畫面 2 21、畫面 3 16、畫面 4 9、畫面 5 12、畫面 6 15、畫面 7 11、畫面 8 15、畫面 9 12；數字是 QA 用小程式掃描 spec 檔得來：各情境內以 `["` 開頭的錨點列數，加上 `expect.soft` 另列斷言與 KPI 四張的硬斷言）。
2. **截圖人眼對照**：每個畫面存一張真實畫面截圖（`AgentConsole/frontend/tests/e2e/__screenshots__/p9-w7-screen-0N-*.png`），與設計稿 `docs/01_requirements/01.UI_Design/Design_ConsoleUI/screenshots/0N-*.png`（monorepo 根下）以圖片檢視逐張並排比對版面、元素位置、元素有無。誠實劃界：**沒有做像素差異比對**——設計稿是低解析度示意圖（單張 15～24KB），字型、尺寸與資料都不同，像素比對沒有意義；人眼對照是主觀判斷，所以每張都把「看到的差異」逐條列出並對上登記處。

| 畫面 | 設計稿 | 我的截圖 | DOM 斷言（逐項，全部通過） | 與設計稿的差異（皆已登記） |
|------|--------|----------|----------------------------|----------------------------|
| 全域版面 | 各畫面共通的四區塊 | （各畫面截圖皆含） | 21 項：公告列七項＋使用者徽章、Logo 兩行、搜尋列、通知鈴、待審批佇列鈕、側欄標題與六個導航項、我的專案 | 公告列的「說明文件／下載 CLI／GitHub／通知總覽／幫助中心」是靜態標示（契約 §4.6 G-G5，D-04）；Engine Bridge 為真實連線燈（契約 G-03） |
| 1 總覽儀表板 | `01-dashboard.png` | `p9-w7-screen-01-dashboard.png` | 13 項：副標、匯入主色按鈕、KPI 容器恰四張、進行中的執行與「查看全部專案 →」、待人工審批與 signoff 硬閘說明與計數徽章 | KPI 四張的標籤與數值改為活躍專案數／待審批草案數／本週完成任務數／執行中 run 數（ADR-002 §4 第 2 項）；待人工審批清單含四種草案（契約 G-10）；底部多狀態列與登出（ADR-002 §4 第 1 項） |
| 2 專案管理 | `02-projects.png` | `p9-w7-screen-02-projects.png` | 21 項：副標（共 N 筆）、匯入、新建專案、篩選標籤、六個狀態 tab、排序下拉、專案卡（名稱、未審批標籤、四段 meta、查看／編輯／執行／監控） | 多一個「已刪除」篩選（W5 契約 C-3）；排序第三項由「任務數」改「最近建立」（ADR-002 §4 第 3 項） |
| 3 專案詳情 | `03-project-detail.png` | `p9-w7-screen-03-project-detail.png` | 16 項：返回連結、meta、signoff 警示橫幅與審批鈕、基本資訊與專案說明兩欄、目標清單與新增目標、底部三個動作；通過標準渲染成三項清單 | 目標列多拖曳把手（ADR-002 §4 第 1 項）、底部多「刪除專案」（第 4 項）、不提供「匯出」（第 10 項，審查 D-02） |
| 4 目標詳情 | `04-goal-detail.png` | `p9-w7-screen-04-goal-detail.png` | 9 項：返回專案、草案警示橫幅、目標說明與通過標準、任務清單與新增任務、編輯目標；通過標準渲染成兩項核取清單（皆未勾） | 多「刪除目標」（ADR-002 §4 第 4 項） |
| 5 任務詳情 | `05-task-detail.png` | `p9-w7-screen-05-task-detail.png` | 12 項：返回目標、三張指標卡（開始時間／Token 消耗／重試次數）、任務說明與通過標準、深色執行日誌卡、編輯；通過標準兩項核取清單（一項已勾）；沒有暫停／取消、沒有「執行時長」卡 | 通過標準卡多「期望輸出 Regex」（ADR-002 §4 第 5 項）；日誌多搜尋框（第 1 項）；第三張卡取設計稿的「重試次數」（第 11 項，審查 D-03）；沒有暫停／取消（第 4 項） |
| 6 匯入 | `06-import.png`（只有步驟 1；步驟 2 對的是設計稿 `README.md` 的文字描述） | `p9-w7-screen-06-import-step1.png`、`p9-w7-screen-06-import-step2.png` | 15 項：步驟 1（輸入來源、上傳檔案與貼上文字兩個 tab、拖放區、10MB 說明、自治等級、執行路徑、補充說明、開始解析）；步驟 2（結構預覽與編輯、樹狀預覽、signoff 警示與審批鈕、放棄、確認匯入） | 執行路徑欄下多一段 Docker 與本機路徑寫法的說明（Architecture §12.1 L-8）；來源 tab：設計稿 README 寫「檔案上傳／貼上文字／URL 之類」，設計稿 PNG 與實作都是「上傳檔案／貼上文字／歷史記錄」三個（以 PNG 為準，README 與 PNG 在這裡本來就不一致）；自治等級預設值取 PRD 的 Level 3（PNG 示範值是 Level 1，屬示範資料） |
| 7 專案執行 | `07-execute.png` | `p9-w7-screen-07-execute.png` | 11 項：副標、執行控制（自治等級、Token 預算、執行範圍、啟動執行）、執行進度、DAG 依賴視覺化、即時日誌與 SSE 串流標頭、待審核項目 | 多執行批次下拉（契約 §4.2 E-20）、自動突變與自演化晶片（E-21，D-11）、DAG 的「收合任務」與「全螢幕」（E-13、E-22）、日誌的「顯示引擎原始輸出」開關（E-14）與搜尋框 |
| 8 專案監控 | `08-monitor.png` | `p9-w7-screen-08-monitor.png` | 15 項：返回專案、時間範圍、四張指標卡（完成率／任務成功率／重試率／Token 消耗）、Token 使用趨勢與圖、任務狀態分佈、執行時間分佈、執行日誌查詢與等級下拉、告警、Agent 即時狀態卡、AISDLC_SDD 引擎卡 | 多批次下拉（契約 G-M1）、第二列六張小 KPI（ADR-001 G-13）、另三張圖與事件時間軸（契約 G-M2）、Agent 卡與 AISDLC_SDD 引擎卡（M-19、M-20） |
| 9 系統參數設定 | `09-settings.png` | `p9-w7-screen-09-settings.png` | 12 項：匯出／匯入設定、六個分類 tab、測試連線、每列重置、修改歷史、全部重置為預設值 | 分頁名取設計稿 README（模型／Agent／執行／監控／AutoClaude／SDD）；每列多生效標籤與影響說明（契約 §4.4） |

**畫面 3／4／5 的「通過標準」要怎麼讀**（一個我自己先犯、後來更正的判斷）：三個詳情頁的通過標準都是 `MarkdownView variant="criteria"`，本來就以 Markdown 渲染（`- ` 清單、`- [ ]`／`- [x]` 核取清單，核取方塊是 `role=checkbox` 加 `aria-checked`）。我第一次截圖時夾具的通過標準只寫了一句「全部完成」，所以畫面是單段文字——那是夾具資料，不是產品缺口（我一度想登成缺陷，檢查原始碼後撤回）。後來把這三筆夾具改成設計稿同款內容，重跑的截圖就與設計稿一致：

- 畫面 3 的基本資訊卡：三項項目符號清單「所有單元測試通過率 ≥ 95%」「整合測試全數通過」「程式碼覆蓋率 ≥ 80%」（斷言 `.md-criteria li` 恰 3 個）。
- 畫面 4 的通過標準卡：兩項**都未勾**的核取清單「所有核心模組通過單元測試」「API 架構層通過整合測試」（斷言 `.md-criteria [role=checkbox]` 恰 2 個、`aria-checked=false` 恰 2 個）。
- 畫面 5 的通過標準卡：兩項核取清單、第一項已勾（斷言 checkbox 恰 2 個、`aria-checked=true` 恰 1 個），與設計稿的勾選狀態一致；另外多一個「期望輸出 Regex」區塊（已登記差異 ADR-002 §4 第 5 項）。

人眼對照時我逐張並排看了設計稿與最終版截圖（畫面 1、2、6、7、8、9 在整套與重跑兩次的截圖之間只有資料不同：專案名稱、時間戳、卡片數量；版面、元素有無與位置沒有變）。設計稿是低解析度示意圖，目標說明等欄位的內容（例如畫面 4 的目標說明文字、畫面 3 的專案說明兩段文字）是示範資料，我的夾具沒有填，所以那幾格是「尚未填寫」或單句——這是資料差異，不是版面差異。

**觀察 O-31（設計稿本身的措辭不一致）**：設計稿 `09-settings.png` 圖內的六個分類 tab 寫的是「AI 模型／Agent 行為／執行引擎／監控告警／AutoClaude／AISDLC_SDD」，與同目錄 `README.md` 的「模型／Agent／執行／監控／AutoClaude／SDD」措辭不同（個數、意義一致）；產品依 README 實作，且 PRD §0 以 README 與 ADR 為準。建議設計稿 PNG 與 README 擇一訂正，不是產品缺陷。

## 8. 本機整套與 Docker 回歸

### 8.1 本機整套 Playwright（真後端＋假 Brain 版 Bridge＋mock claude；乾淨資料庫）

**組成**：`npx playwright test --list` 現查共 **213** 個測試、31 個檔（W5 為 150）；多出的 63 個＝本輪新增的五支 `p9-w7-*` spec 共 45 個（`p9-w7-engine` 8、`p9-w7-resources` 3、`p9-w7-sdd` 13、`p9-w7-signoffs` 9、`p9-w7-ui` 12）＋ W7 前端三批新增的 route mock 情境 18 個（mock 檔合計 W5 時 53 個、現 71 個；`execute.mock` 16→21、`monitor.mock` 9→15、`dashboard.mock` 3→8 等）。

**起跑前重置**（`reset_local.ps1 -Fake`，輸出 `logs\reset2.log`）：停掉 backend 與 Bridge、重建 `qa-pg`（清空 `E2E_ROOT` 內容）→ backend（Flyway 建 `console` schema）→ 假 Brain 版 Bridge → 重啟 backend → 等探測環；實測 `Bridge health: ok`、`notifications/summary: bridgeConnected=True`、`projects total: 0`（乾淨資料庫）。

**指令與結果**（`run_pw.ps1 -Tag full1`；`--reporter=list --output=<自己的暫存目錄>`，log＝`logs\pw_full1.log`）：

```bash
(cd AgentConsole/frontend && npx playwright test --reporter=list --output=<暫存目錄> > "$LOG" 2>&1; echo "rc=$?")
```

```powershell
Push-Location AgentConsole\frontend; npx playwright test --reporter=list --output=<暫存目錄> *> $log; $rc = $LASTEXITCODE; Pop-Location
```

```
rc=0 elapsed_sec=4047 start=2026-10-17T00:53:29.5997691+08:00 end=2026-10-17T02:00:57.0200479+08:00
213 passed (1.1h)
```

整套 **213 個全數通過、0 失敗、0 略過**（前一行是 `run_pw.ps1` 寫的 rc 檔，後一行是 Playwright 尾端摘要；實際經過 67.5 分鐘，W5 為 52.2 分鐘，多出的時間來自 63 個新測試）。逐檔統計（`pw_summary.py` 由 log 的 `✓` 行重算，與尾端摘要相符；粗體是本輪新增的 `p9-w7-*`；耗時是各測試本體耗時加總）：

| 檔案 | 測試數 | 通過 | 失敗 | 略過 | 耗時（分） |
|------|-------:|-----:|-----:|-----:|-----------:|
| `a11y.mock.spec.ts` | 3 | 3 | 0 | 0 | 0.1 |
| `chart.spec.ts` | 1 | 1 | 0 | 0 | 0.0 |
| `crud-flow.spec.ts` | 1 | 1 | 0 | 0 | 0.1 |
| `dashboard.mock.spec.ts` | 8 | 8 | 0 | 0 | 0.1 |
| `design-system.spec.ts` | 3 | 3 | 0 | 0 | 0.0 |
| `execute.mock.spec.ts` | 21 | 21 | 0 | 0 | 0.7 |
| `import.mock.spec.ts` | 8 | 8 | 0 | 0 | 0.2 |
| `markdown-editor.spec.ts` | 5 | 5 | 0 | 0 | 0.1 |
| `monitor.mock.spec.ts` | 15 | 15 | 0 | 0 | 0.3 |
| `notifications.mock.spec.ts` | 3 | 3 | 0 | 0 | 0.0 |
| `p3-import.spec.ts` | 8 | 8 | 0 | 0 | 3.3 |
| `p4-execute.spec.ts` | 12 | 12 | 0 | 0 | 12.8 |
| `p4b-execute-more.spec.ts` | 9 | 9 | 0 | 0 | 8.5 |
| `p5-monitor.spec.ts` | 4 | 4 | 0 | 0 | 1.2 |
| `p6-settings.spec.ts` | 8 | 8 | 0 | 0 | 1.2 |
| `p7-cors-ratelimit.spec.ts` | 1 | 1 | 0 | 0 | 2.1 |
| `p9-w5-a11y.spec.ts` | 9 | 9 | 0 | 0 | 2.3 |
| `p9-w5-api.spec.ts` | 10 | 10 | 0 | 0 | 5.0 |
| `p9-w5-bridge.spec.ts` | 2 | 2 | 0 | 0 | 0.0 |
| `p9-w5-ui-evidence.spec.ts` | 6 | 6 | 0 | 0 | 6.0 |
| `p9-w5-ui.spec.ts` | 6 | 6 | 0 | 0 | 5.5 |
| **`p9-w7-engine.spec.ts`** | 8 | 8 | 0 | 0 | 1.8 |
| **`p9-w7-resources.spec.ts`** | 3 | 3 | 0 | 0 | 3.7 |
| **`p9-w7-sdd.spec.ts`** | 13 | 13 | 0 | 0 | 3.7 |
| **`p9-w7-signoffs.spec.ts`** | 9 | 9 | 0 | 0 | 2.3 |
| **`p9-w7-ui.spec.ts`** | 12 | 12 | 0 | 0 | 3.2 |
| `projects.mock.spec.ts` | 3 | 3 | 0 | 0 | 0.0 |
| `settings.mock.spec.ts` | 10 | 10 | 0 | 0 | 0.2 |
| `shells-and-layout.spec.ts` | 6 | 6 | 0 | 0 | 0.1 |
| `signoff.spec.ts` | 5 | 5 | 0 | 0 | 0.1 |
| `task-retry.spec.ts` | 1 | 1 | 0 | 0 | 0.0 |
| **合計（31 個檔）** | **213** | **213** | **0** | **0** | **64.6**（測試本體耗時加總，不含 hooks） |

**這次整套與先前單檔跑的差別**：W7 的五支 spec 我都先在開發途中單檔跑過；整套是在乾淨資料庫上依序跑完全部 31 個檔，所以多驗了一件事——新 spec 之間、以及與 W3～W5 舊 spec 之間沒有互踩（共用限流額度、共用 Bridge、設定鍵還原）。整套尾端的 `signoff.spec.ts` 與 `task-retry.spec.ts` 測試本體合計不到 0.2 分鐘，但從 `shells-and-layout.spec.ts` 結束到整套結束隔了約一分鐘，與 `signoff.spec.ts` 檔頭自述的設計相符（每個情境前 `waitForQuota`，額度不夠就等限流視窗過去；這只是時間線觀察，我沒有逐項量測等待時間）。整套開跑之後我又改了三處（`p9-w7-ui.spec.ts` 把畫面 3／4／5 的夾具改成設計稿同款的清單與核取清單、`p9-w7-signoffs.spec.ts` 修一個 log 字串的計數、SDD 的 LATEST 不再寫死在 spec 與 `w7.ts` 裡），所以整套中那幾支跑的不一定是最後入庫的版本（`p9-w7-html.spec.ts` 與 `p9-w7-purefile.spec.ts` 是整套之後才首次執行，Docker 那支的修正見 §8.2）；為了讓證據對應「最後入庫的版本」，§8.4 對 `p9-w7-*` 七支最終版重跑了一次，畫面 3／4／5 的截圖與判斷、以及各支 spec 的證據行以重跑為準。

### 8.2 Docker 全棧（經 nginx）

起停與環境見 §2.4～§2.5。`docker.config.ts` 現查共 **32 個測試**（W5 時 27 個；本輪多出的 5 個是 `p9-w7-docker.stack.ts`）。我在全棧起來後依序做：promtool 與 Prometheus／Grafana 查詢（§4.4）→ 這一節的 Playwright（第一次整套、第二次重跑）→ INF 唯讀探查與備份（§8.3）→ 定稿版重跑（第三次）→ 自簽 HTTPS（§4.5）→ 收尾前的容器日誌掃描與 SSE 斷線重現（§10.1 的 DEF-AC-014）→ Prometheus 卷持久性（§4.4）→ `down`（不帶 `-v`）。

**第一次整套（`logs\pw_docker1.log`）：28 通過、1 失敗、3 未執行**。失敗的是我自己新寫的那支 `p9-w7-docker.stack.ts` 的資源卡情境（E2E-14 列 8～9 全棧），它是 `serial` 模式，所以同檔後面三個情境（SDD 全棧半邊、Linux 映像另起容器、Redis 降級）沒有執行。**原因是測試的限流額度設計，不是產品**：建夾具要 92 次呼叫（1 個專案、1 個目標、90 個任務），用掉 operator 這一分鐘的大半額度；緊接著以 operator 開監控頁，頁面一載入就是 30 次上下的呼叫，撞 429。證據——nginx 近十分鐘的狀態碼分佈在 18:37 分鐘是 201×93、429×8，18:38 分鐘是 429×21；失敗測試的 trace 時間線（`pw_out\docker1\…\trace.zip` 內的網路紀錄）：18:37:52～53 建夾具 92 筆 201，之後頁面每 15 秒一輪全是 429（18:38:09、:24、:39），**18:38:54 限流視窗重置後 10 筆全部 200**——而我的 `toHaveText` 等待上限 60 秒剛好在 18:38:55 到期。產品的行為（429 後照 15 秒輪詢、視窗重置後立刻恢復）是正常的；同時 Bridge 端直接查，該 90 任務批次的 `resources` 一直有值（`{"cpu_percent":0.0,"rss_bytes":49713152,"process_count":2,…}`）。修法只動測試：載入頁面前 `ensureQuota(request, "operator", 60)` 等限流視窗重置。

**重跑 `p9-w7-docker.stack.ts`（第二次與第三次）**：只重跑 `p9-w7-docker.stack.ts`，**5 個全部通過**（rc=0，2.0 分鐘）。修法只動測試（`ensureQuota`，見上）。這個重跑我做了兩次：第二次（docker2）在修法剛落地時；整理文件時發現 spec 的 log 文字寫「6.5 秒後」，實際兩筆樣本相隔的是「等限流視窗重置再載入頁面」的時間（67 秒），所以把 log 文字改成「第二筆（與首筆的 sampledAt 相隔 N 秒）」，並在**定稿版再跑一次（第三次，docker3）**。兩次的數字同形（首筆 `processCount` 1、第二筆 2、記憶體 47 MB、CPU 0.0%）。

**第二次（`logs\pw_docker2.log`）**：

```
rc=0 elapsed_sec=119 start=2026-10-17T02:41:27.9606469+08:00 end=2026-10-17T02:43:26.8836827+08:00
5 passed (2.0m)
```

證據行（逐字節錄自 `logs\pw_docker2.log`）：

```
[w7-docker] 列 1：healthCheckPath value＝/health/deep／default＝/health/deep；bridgeConnected＝true；Bridge 容器 healthy、backend healthy
[w7-docker] 列 8（全棧）：首筆＝{"cpuPercent":0,"memoryBytes":7839744,"processCount":1,"sampledAt":"2026-10-16T18:41:30.603786+00:00"}；6.5 秒後＝{"cpuPercent":0,"memoryBytes":49651712,"processCount":2,"sampledAt":"2026-10-16T18:42:37.356957+00:00"}；畫面「CPU 0.0%・記憶體 47 MB・2 行程」
[w7-docker] 列 9（全棧）：終態 CANCELLED，resources＝null，卡片「—」
[w7-docker] 列 9／NFR-OBS-01（全棧）：checks.sdd＝{"ok":true,"latest":"AISDLC_SDD_v0.30"}；/engines/sdd＝AISDLC_SDD_v0.30（8 個專案）；AISDLC_SDD 的 INIT／Sprint 1／2026-07-16 01:36:40 與主機檔逐值一致
[w7-docker] 列 9（Linux 映像 aisdlc-engine-bridge:dev）：乾淨 clone 等價 checks.sdd＝{"ok":true,"latest":"AISDLC_SDD_v9.98"}、/sdd/fsm projects＝[]；SDD_ROOT 不存在 checks.sdd＝{"ok":false,"latest":null,"reason":"SDD_ROOT 不是目錄：dir"}、整體 200、/sdd/fsm＝503
[w7-docker] 列 10：Redis 在線登出→鍵 1→2；停掉後 換新=200、舊 token 再換新=401 INVALID_REFRESH_TOKEN、登出=204、之後換新=401；actuator UP、backend healthy；WARN 1 筆；啟動後 INFO 1 筆、WARN 仍 1 筆、新撤銷寫進 Redis（鍵 2→3）
```

**第三次＝定稿版（`logs\pw_docker3.log`）**——列 10 的撤銷名單鍵數是接續 docker2 往上累積的，所以是 3→4、4→5：

```
rc=0 elapsed_sec=119 start=2026-10-17T02:47:53.1402908+08:00 end=2026-10-17T02:49:51.8846791+08:00
5 passed (2.0m)
```

證據行（逐字節錄自 `logs\pw_docker3.log`）：

```
[w7-docker] 列 1：healthCheckPath value＝/health/deep／default＝/health/deep；bridgeConnected＝true；Bridge 容器 healthy、backend healthy
[w7-docker] 列 8（全棧）：首筆＝{"cpuPercent":0,"memoryBytes":7839744,"processCount":1,"sampledAt":"2026-10-16T18:47:55.675439+00:00"}；第二筆（與首筆的 sampledAt 相隔 67 秒）＝{"cpuPercent":0,"memoryBytes":49537024,"processCount":2,"sampledAt":"2026-10-16T18:49:02.364109+00:00"}；畫面「CPU 0.0%・記憶體 47 MB・2 行程」
[w7-docker] 列 9（全棧）：終態 CANCELLED，resources＝null，卡片「—」
[w7-docker] 列 9／NFR-OBS-01（全棧）：checks.sdd＝{"ok":true,"latest":"AISDLC_SDD_v0.30"}；/engines/sdd＝AISDLC_SDD_v0.30（8 個專案）；AISDLC_SDD 的 INIT／Sprint 1／2026-07-16 01:36:40 與主機檔逐值一致
[w7-docker] 列 9（Linux 映像 aisdlc-engine-bridge:dev）：乾淨 clone 等價 checks.sdd＝{"ok":true,"latest":"AISDLC_SDD_v9.98"}、/sdd/fsm projects＝[]；SDD_ROOT 不存在 checks.sdd＝{"ok":false,"latest":null,"reason":"SDD_ROOT 不是目錄：dir"}、整體 200、/sdd/fsm＝503
[w7-docker] 列 10：Redis 在線登出→鍵 3→4；停掉後 換新=200、舊 token 再換新=401 INVALID_REFRESH_TOKEN、登出=204、之後換新=401；actuator UP、backend healthy；WARN 1 筆；啟動後 INFO 1 筆、WARN 仍 1 筆、新撤銷寫進 Redis（鍵 4→5）
```

合起來看：Docker 全棧共 32 個測試；第一次整套 28 個通過（其中含 W7 檔的第 1 個）、第二次與第三次各把 W7 檔的 5 個全部跑過；`docker.config.ts` 的 `retries` 是 0，沒有任何測試是靠重試才過的。

**第一次整套的逐檔統計**（`pw_summary.py` 由 log 的 `✓` 行重算；失敗的那個測試在表內算 1 失敗，未執行的 3 個不在表內）：

| 檔案 | 測試數 | 通過 | 失敗 | 略過 | 耗時（分） |
|------|-------:|-----:|-----:|-----:|-----------:|
| `chart.spec.ts` | 1 | 1 | 0 | 0 | 0.0 |
| `crud-flow.spec.ts` | 1 | 1 | 0 | 0 | 0.1 |
| `design-system.spec.ts` | 3 | 3 | 0 | 0 | 0.0 |
| `p8-docker-stack.stack.ts` | 11 | 11 | 0 | 0 | 8.2 |
| `p9-w7-docker.stack.ts` | 2 | 1 | 1 | 0 | 1.0 |
| `shells-and-layout.spec.ts` | 6 | 6 | 0 | 0 | 0.1 |
| `signoff.spec.ts` | 5 | 5 | 0 | 0 | 0.1 |
| **合計（7 個檔）** | **29** | **28** | **1** | **0** | **9.6** |

**指令**（`run_pw_docker.ps1`；`docker.config.ts`、`E2E_API_URL=http://localhost`、`--reporter=list --output=<自己的暫存目錄>`）：

```bash
(cd AgentConsole/frontend && E2E_API_URL=http://localhost npx playwright test -c tests/e2e/docker.config.ts --reporter=list --output=<暫存目錄> > "$LOG" 2>&1; echo "rc=$?")
```

```powershell
Push-Location AgentConsole\frontend; $env:E2E_API_URL = 'http://localhost'; npx playwright test -c tests/e2e/docker.config.ts --reporter=list --output=<暫存目錄> *> $log; $rc = $LASTEXITCODE; Pop-Location
```

第一次整套的 rc 檔與 Playwright 尾端（`logs\pw_docker1.rc.txt`、`logs\pw_docker1.log`）：

```
rc=1 elapsed_sec=642 start=2026-10-17T02:29:25.1593370+08:00 end=2026-10-17T02:40:06.8992507+08:00
1 failed
3 did not run
28 passed (10.7m)
```

### 8.3 INF 唯讀探查（審查 V-05）

**審查 V-05 的問題**：RTM 有 63 列 INF 的 `✅ 已驗證` 只有開發者（INFRA）自述，QA 在 W5 沒有逐列重驗。我在 Docker 全棧上做**唯讀探查**：逐列對照 RTM 的說法與 README 的指令，所有指令都是查詢或 README 本來就要你跑的日常檢查；會改動狀態的只有四件：README〈8〉本來就要求的備份（見下）、`INF-SVC-07`／`INF-VOL-05` 對 redis 的重啟與一個測試鍵（SET 後 DEL）、`INF-DR-19` 讓 redis 容器自己結束一次、以及 §4.5 的 HTTPS 演練。完整輸出在 `logs\inf_probe.log`、`logs\inf_backup_probe.log`、`logs\inf_probe2.log`；備份後 Grafana 面板重放在 `logs\backup_panels_replay.log`；收尾前的快照在 `logs\final_docker_state.log`。

**新部署沒有備份——這個起點本身就是一項發現**：全棧剛起來時 `pgbackrest info` 回 `status: error (no valid backups)`、`pgbackrest_stanza_status＝2`、`pgbackrest_backup_since_last_full_seconds` 與 `pgbackrest_backup_last_status` 沒有序列，Grafana「Backup Status」列 9 個面板只有 5 個有資料。這與 README〈9〉與 `alerts.yml` 註解的「新部署視為正常現象」一致（INFRA 已知，不是缺陷），但它代表 INF-DR-09～15、28、29、33 這幾列**不能只看「有沒有東西」**，必須先製造備份。所以我執行了 cron 排程會跑的**同一支腳本**（`backup-full.sh`、`backup-incr.sh`、`pg_dump-offsite.sh`、`pgbackrest expire`、`pgbackrest verify`、`verify-backup.sh`；不是等 cron 觸發），再查指標與面板：

```
backup-full.sh      rc=0 elapsed_sec=6    full backup: 20261017-024528F（repo1）、20261017-024530F（repo2）；database size 32.9MB → backup set size 3.7MB
backup-incr.sh      rc=0 elapsed_sec=3    diff backup: 20261017-024528F_20261017-024533D（repo1）、20261017-024530F_20261017-024535D（repo2）
pg_dump-offsite.sh  rc=0 elapsed_sec=0    pg_dump offsite backup pushed: aisdlc-20261016-184536.dump（135.43 KiB）
pgbackrest info     rc=0                  status: ok、cipher: aes-256-cbc
pgbackrest expire   rc=0；pgbackrest verify rc=0
verify-backup.sh    rc=0 elapsed_sec=11   repo2 輪：15 張表列數 restored＝live；pg_restore 讀得到 TOC 90 筆；OK: Backup verification + restore drill completed
備份後的指標         pgbackrest_stanza_status＝0；since_last_full repo1＝55／repo2＝52 秒；backup_last_status{type=diff}＝0
```

**逐組結果**（RTM 列 → 當回合實測；「程度」＝重驗／部分重驗／未逐列重驗）：

| RTM 列 | 當回合實測 | 程度 |
|--------|------------|------|
| `INF-SVC-07`、`INF-VOL-05`（redis） | `PONG`；`appendonly yes`；SET→`docker restart aisdlc-redis`→GET 值仍在（`SET→OK；restart 後 healthy=True；GET→persist-ok；DEL→1`）；healthy、`unless-stopped`、256 MiB、無主機埠；`aisdlc_redis_data`→`/data`（rw）；另是 refresh 撤銷名單的後端（§5.4 列 10） | 重驗 |
| `INF-SVC-08`（pgadmin） | `http://localhost:5050/misc/ping -> 200`；啟動日誌 `Added 1 Server Group(s) and 2 Server(s).`；uid 5050；healthy | 重驗 |
| `INF-SVC-09`（pgbackrest） | healthy；crontab 六條排程（週日 02:00 全備、週一至週六 02:00 差備、每日 02:30 pg_dump、週三 04:00 驗證、每日 03:00 expire、每日 03:30 清 WAL）；`pgbackrest check` rc=0；`pgBackRest 2.59.3`；`:9854` 是 Prometheus 目標且 up | 重驗（cron 的實際觸發沒有等，改跑同一支腳本） |
| `INF-SVC-10`（prometheus） | 5 個目標全 up；4 個規則群組共 17 條 `health=ok`；`/-/healthy` 200；`aisdlc_prometheus_data`→`/prometheus` | 重驗 |
| `INF-SVC-11`（grafana） | `/api/health` 200；兩個 dashboard 皆 provisioned（Application Overview 23 個面板、PostgreSQL Overview 44 個）；資料源 Prometheus；3001→3000；uid 472 | 重驗 |
| `INF-SVC-12`、`INF-SVC-13`（minio、minio-init） | minio healthy；minio-certs job `Exited (0)`，憑證 `CN=minio`、SAN `DNS:minio, DNS:localhost, IP Address:127.0.0.1`、`notAfter=Oct 13 11:35:11 2036 GMT`；minio-init `Exited (0)`、restart `no`；bucket `aisdlc-db-backup` 在 `minio_data` 內，之後收到 pg_dump 與 repo2 備份 | 重驗 |
| `INF-SVC-14`、`INF-SVC-15`（兩個 exporter） | 皆 healthy、nobody、128 MiB；目標 up；`min(pg_up)`＝1；`pg_replication_lag_seconds{job=postgres-replica}`＝0 | 重驗 |
| `INF-NET-01`～`INF-NET-03` | frontend-net `172.21.0.0/16`（成員 frontend、nginx）；backend-net 固定 `172.31.250.0/24`（成員 engine-bridge、backend、frontend、grafana、prometheus、nginx、pgadmin）；db-net `internal=true`（`172.22.0.0/16`，11 個成員）；pg-primary、pg-replica、redis、minio、pgbackrest 的 `docker port` 全空，對主機發布的只有 nginx 80／443、pgadmin 5050、prometheus 9090、grafana 3001。**「主機連 5433 被拒」不能當證據**：主機的 5433 有行程在聽，是本機原生的 `postgresql-x64-18` Windows 服務（PID 6848，由 `pg_ctl` 啟動，與本專案無關） | 重驗 |
| `INF-VOL-01`～`04`、`INF-VOL-08` | 掛載與用量逐一對得上（pg_data→primary 與 pgbackrest；pg_replica_data→replica；pg_wal_archive→primary／pgbackrest 讀寫、replica 唯讀，`du` 2.8M→備份後 3.6M；pg_backup→`/var/lib/pgbackrest`，備份後 11M；engine_workspace→bridge 的 `/workspace`，uid 10001、`touch` 可寫）；`down`（不帶 `-v`）後 12 個 `aisdlc_*` 卷都還在 | 部分（「重起後資料仍在」沒有驗，只有 `redis_data` 與 `prometheus_data` 實測過） |
| `INF-DKR-01`、`02`、`03`、`05` | frontend 351MB、uid 1001（nextjs）；backend 497MB、`spring`、`-XX:+UseZGC -XX:MaxRAMPercentage=75.0`、`/actuator/health` UP；pgbackrest 映像 693MB、Debian 12、`pgBackRest 2.59.3`；primary 映像 634MB、`pgBackRest 2.59.3`（與 sidecar 同版） | 重驗 |
| `INF-CMD-01`、`02`、`INF-DEV-01` | `up -d --build --wait` rc=0（180 秒；以 INFRA 的拋棄式 env 檔取代 `.env`）；`ps nginx`（帶 profile）、`logs --tail 2 nginx`、`restart nginx` 皆 rc=0；本機開發 compose 帶 env 檔 `config --services` rc=0＝`postgres-primary,redis`，發布 5432／6379 且綁 `127.0.0.1`，不帶必要變數 rc=1（`required variable … is missing a value`） | 重驗 |
| `INF-DR-01`～`05`、`07` | `pg_stat_replication`：`172.22.0.6/32 streaming async replay_lag=00:00:00.000569`；replica `pg_is_in_recovery＝t`；`wal_level=replica archive_mode=on archive_timeout=60 hot_standby=on max_replication_slots=5 max_wal_senders=5`；`archive_command`＝`/usr/local/bin/pgbackrest-archive-wal.sh %p %f`；hba 有效行（local trust、127.0.0.1／::1／172.16/12／192.168/16 scram-sha-256、replication 兩個私網段 scram-sha-256、`0.0.0.0/0 reject`）；`primary_slot_name＝replica_slot_1`；`replicator` 帶 replication、slot active；`pg_stat_archiver archived=22 failed=0` | 重驗 |
| `INF-DR-06`（replica 建立與重建） | replica 運作中且 streaming；刪卷重建屬破壞性（`down -v` 被禁止），沒有演練 | 部分 |
| `INF-DR-09`、`10`、`12`、`15` | 見上方備份腳本輸出：`backup-incr.sh` rc=0、`pg_dump-offsite.sh` rc=0（TOC 90 筆可由 `pg_restore` 讀）、`verify-backup.sh` rc=0（15 張表 restored＝live）、`pgbackrest verify` rc=0、`expire` rc=0（`repo1-retention-full=4 repo1-retention-diff=7 repo2-retention-full=4`） | 重驗（同一支腳本，非 cron 觸發） |
| `INF-DR-17`（手動 failover） | 要停掉 primary，屬破壞性，沒有演練；只確認前提（replica 在 recovery、slot active、延遲 0） | 未逐列重驗 |
| `INF-DR-19`（崩潰自動重啟） | 以 `redis-cli shutdown nosave` 讓容器內行程自己結束（`docker kill` 會被 Docker 視為手動停止而不重啟，所以不用）：`RestartCount 0→1`、`StartedAt` 前進、回到 healthy；policy `unless-stopped` | 重驗 |
| `INF-DR-20`～`27` | 5 目標 up；`min(pg_up)`＝1；`pg_replication_lag_seconds`＝0；`sum(pg_stat_activity_count)`＝14；`pg_database_size_bytes{datname="aisdlc"}` primary 10909375／replica 10933951；`aisdlc_storage_used_ratio`＝0.0316；bgwriter 配置率約 0.049／0.042；`sum(pg_locks_count)`＝3；平均查詢時間約 0.0068 秒；對應的告警規則皆 `health=ok` | 重驗 |
| `INF-DR-28`、`29` | 備份前序列缺席、`stanza_status＝2`；備份後 since_last_full 55／52 秒、`backup_last_status{type=diff}＝0`、`stanza_status＝0` | 重驗（先製造備份） |
| `INF-DR-30`～`35`（六列面板） | PostgreSQL Overview 六個列各面板逐一重放 `/api/ds/query`（`now-6h`）HTTP 200、errors 0：PG 總覽 8／8、複製狀態 9／9、查詢效能 3／3、備份狀態 5／9→備份後 9／9（面板 32、33 各 2 個序列 8 點）、鎖與等待 4／4、儲存空間 5／5（有資料面板數／面板數） | 重驗 |
| `INF-OPS-01`～`09`（README〈8〉九條） | 01／02 `accepting connections`；03 `172.22.0.6`、streaming、四個 LSN 皆 `0/17023D18`；04 備份前 `status: error (no valid backups)`、備份後 `status: ok`；05 `docker system df` 有輸出（Images 36、Containers 17、Local Volumes 41、Build Cache 197）；06 `pgbackrest verify` rc=0；07 慢查詢 Top3（`CREATE DATABASE "aisdlc"` mean=30.82 calls=1 等）；08 表膨脹 0 列；09 `wal_archive` 2.8M→備份後 3.6M | 重驗 |

**判定**：63 列中 **56 列完整重驗、6 列部分重驗、1 列未逐列重驗**，沒有任何一列被證偽，狀態都維持 `✅ 已驗證`，各列 E2E 欄附加了上面對應的證據與程度。六列部分重驗＝`INF-VOL-01`～`04`、`INF-VOL-08`（只驗掛載與用量，「重起後資料仍在」沒驗）加 `INF-DR-06`（沒演練重建）；一列未驗＝`INF-DR-17`（failover）。沿用 INFRA 證據、本輪沒有演練的事項另列在 §11。我在探查中順帶看到的產品面觀察（不改任何 RTM 狀態）：backend 記憶體貼著容器上限（O-35）、pgadmin 閒置時用掉 86% 的記憶體上限（O-36）、`up`／`down` 循環累積孤兒匿名卷（O-37）、Grafana 啟動時兩筆 error 日誌（O-38）、SpringDoc 端點在正式 profile 預設啟用（O-39）；另有一個真缺陷 DEF-AC-014（SSE 斷線的 ERROR 日誌，§10.1）是從容器日誌掃出來的。

### 8.4 整套之後單獨跑的三項補充（I-07 純檔案模式、Markdown 內嵌 HTML、版本中性補丁後的 SDD spec）

整套（§8.1）開跑之後，我又做了三件事，為的是讓證據對應**最後要入庫的版本**：

1. **SDD 的 LATEST 不再寫死**：`w7.ts` 新增 `realSddLatest()`（掃 `AISDLC_SDD/` 底下目錄名「數字」最大的版本目錄，語意與 Bridge 的探索相同）與 `REAL_FSM`，`p9-w7-sdd.spec.ts` 與 `p9-w7-docker.stack.ts` 改用它們，不再出現版本字串；同時把 `p9-w7-signoffs.spec.ts` 列 3 的 log 字串「5 個干擾列」更正為實際斷言的 6 個。改後 `prettier`／`eslint`／`tsc` 皆 rc=0。
2. **`p9-w7-html.spec.ts`**：第一次跑（整套之後的七支重跑裡，檔內只有一個斷言「四種腳本載體都不執行」的舊版）**失敗**，這就是 DEF-AC-013 的發現；我把它改寫成四個情境（①三種載體不執行〔通過〕、②③DEF-AC-013 以 `test.fail(DEFECTS_OPEN)` 釘住、④唯讀詳情頁對照〔通過〕）後單獨重跑，結果見下。
3. **對 `p9-w7-*` 七支最終版重跑一次**（`run_pw.ps1 -Tag final1`，log `logs\pw_final1.log`；環境沿用整套的本機環境、資料庫沒有重置，所以數字與整套的乾淨庫不同但判準是相對的）：

| 檔案 | 測試數 | 通過 | 失敗 | 略過 | 耗時（分） |
|------|-------:|-----:|-----:|-----:|-----------:|
| `p9-w7-engine.spec.ts` | 8 | 8 | 0 | 0 | 1.8 |
| `p9-w7-html.spec.ts` | 1 | 0 | 1 | 0 | 0.0 |
| `p9-w7-purefile.spec.ts` | 1 | 1 | 0 | 0 | 1.2 |
| `p9-w7-resources.spec.ts` | 3 | 3 | 0 | 0 | 2.7 |
| `p9-w7-sdd.spec.ts` | 13 | 13 | 0 | 0 | 3.7 |
| `p9-w7-signoffs.spec.ts` | 9 | 9 | 0 | 0 | 2.2 |
| `p9-w7-ui.spec.ts` | 12 | 12 | 0 | 0 | 3.2 |
| **合計（7 個檔）** | **47** | **46** | **1** | **0** | **14.8** |

（`p9-w7-html.spec.ts` 那一列是**舊版**那一個情境的失敗；改寫後的新版見下。）rc 檔與 Playwright 尾端：

```
rc=1 elapsed_sec=911 start=2026-10-17T02:02:54.9182791+08:00 end=2026-10-17T02:18:05.5346373+08:00
```

```
  1 failed
    [chromium] › tests\e2e\p9-w7-html.spec.ts:27:5 › 預覽端內嵌 HTML：四種腳本載體都不執行（img onerror、script、javascript: 連結、iframe srcdoc）
  46 passed (15.1m)
```

除了舊版 html 之外的六支共 46 個**全數通過**，包括畫面 3／4／5 夾具改成設計稿同款清單後的斷言（`.md-criteria li`＝3、核取清單 2 個、已勾 1 個）。

**`p9-w7-html.spec.ts` 新版單獨重跑**（最終版：`run_pw.ps1 -Tag html3`，log `logs\pw_html3.log`；先前的 `html2` 是只差一行 log——少印主控台錯誤的內容——的同一版，結果相同；`✘` 是 `test.fail` 預期中的失敗，Playwright 把它們算成通過）：

```
[w7-html] ①預覽端建出的元素＝{"img":1,"imgHasOnerror":false,"script":1,"anchorHref":"javascript:throw new Error('React has blocked a javascript: URL as a security precaution.')","details":1}；window.__w7xss＝null；點連結後開出的視窗數＝0、其 __w7xss＝[]；主控台錯誤數＝2（pageerror: Minified React error #231; visit https://react.dev/errors/231?args[]=onError&args[]=string for the full message or use the non-minified dev environme ／ pageerror: React has blocked a javascript: URL as a security precaution.）
  ✓  1 [chromium] › tests\e2e\p9-w7-html.spec.ts:65:5 › ① 編輯器預覽：img onerror、script 標籤、javascript: 連結都不執行 (2.9s)
[w7-html] ②DEF-AC-013 預覽端：window.__w7xss＝"iframe-srcdoc"；srcdoc 內腳本讀到的 sessionStorage 鍵名＝"aisdlc.console.session"（只讀鍵名，不讀值）
  ✘  2 [chromium] › tests\e2e\p9-w7-html.spec.ts:98:5 › ② DEF-AC-013（P2）：編輯器預覽裡 <iframe srcdoc> 內的腳本不應執行（目前會執行，釘住） (2.5s)
[w7-html] ③DEF-AC-013 儲存式（admin 開編輯頁）：window.__w7xss＝"iframe-srcdoc"；srcdoc 內腳本讀到的 sessionStorage 鍵名＝"aisdlc.console.lastProject,aisdlc.console.session"（只讀鍵名，不讀值）
  ✘  3 [chromium] › tests\e2e\p9-w7-html.spec.ts:124:7 › 已儲存的專案說明含 iframe srcdoc › ③ DEF-AC-013（P2，儲存式）：管理者開「編輯專案」頁，儲存的 iframe srcdoc 不應在編輯器預覽執行（目前會執行，釘住） (2.3s)
[w7-html] ④唯讀詳情頁：window.__w7xss＝null；頁面內 iframe 元素數＝0
  ✓  4 [chromium] › tests\e2e\p9-w7-html.spec.ts:135:7 › 已儲存的專案說明含 iframe srcdoc › ④ 對照：同一份內容在唯讀的專案詳情頁不執行（react-markdown 不渲染原始 HTML） (1.9s)
  4 passed (10.7s)
```

這支 spec 的判讀：①的三種載體各有不同的擋法，而且擋法靠的是 React 在執行期的行為、不是明確的消毒——`<img onerror="…">` 的字串事件處理器被 React 拒絕（主控台 pageerror＝React error #231：`onError` 必須是函式，所以 DOM 上沒有 `onerror`，`imgHasOnerror＝false`）、`<script>` 元素雖然被建出（`script＝1`）但經 DOM 插入後不執行、`javascript:` 連結的 `href` 被 React 換成一段只會丟錯的字串（點擊後 pageerror＝React has blocked a javascript: URL，沒有開出任何視窗）；只有 `<iframe srcdoc>` 內的腳本真的執行了——②在新建專案的預覽、③在管理者開已儲存內容的編輯頁，兩處都讀得到 `sessionStorage` 的鍵名（③ 多一個 `aisdlc.console.lastProject`，是管理者那個 session 本來就有的鍵）。④證明只有編輯器預覽有這個問題。缺陷登記見 §10.1 的 DEF-AC-013。

**`p9-w7-purefile.spec.ts`（審查 I-07／Architecture L-12 的「待驗」）**：同一份夾具（單一專案、兩個目標、三個任務）各跑一次到終態，一次走共用的 DB 模式 Bridge、一次走另起（18086）的純檔案模式 Bridge（沒有 `BRIDGE_DB_DSN`；`autoclaude.engineUrl` 暫時指過去，結束還原），比對 Console 的批次詳情、步驟時間軸與斷點清單（逐字節錄自 `logs\pw_final1.log`）：

```
[w7-purefile] DB 模式：{"status":"COMPLETED","instance":"e2e-bridge","completedSteps":3,"totalSteps":3,"stepsTotal":6,"stepStatuses":"STARTED,COMPLETED,STARTED,COMPLETED,STARTED,COMPLETED","checkpoints":3}
[w7-purefile] 純檔案模式：{"status":"COMPLETED","instance":"w7-purefile","completedSteps":3,"totalSteps":3,"stepsTotal":0,"stepStatuses":"","checkpoints":0}
```

**判定**：批次本身在純檔案模式下照樣跑完（`COMPLETED` 3／3、由變體 Bridge 跑的），但 Console 的**步驟時間軸 0 筆、斷點清單 0 個**；DB 模式是 6 筆與 3 個。這證實 Architecture §12.1 L-12 的警語屬實而且可量化：純檔案模式只適用於單獨驗 Bridge，Console 的這兩個畫面依賴 Bridge 的 DB 模式（`BR-24`「步驟與斷點由 Bridge 寫」的另一面）。這是已登記的限制、不是新缺陷；我只量了這兩個端點，沒有逐項驗純檔案模式下 Console 其餘功能（§11）。

## 9. RTM 合併與統計

### 9.1 怎麼合併（單線；W7 三棒不碰 `RTM.md`）

以 `HEAD` 的 `RTM.md` 為底（冪等：每次都從 `git show HEAD:` 重做，重跑不會累積附加），只改每列的「實作檔、自動測試、E2E 驗證、狀態」四格；新列另補來源、摘要（≤ 20 字）、層、Phase：

1. **開發者回填**：`rtm_backfill_W7BE.md`、`rtm_backfill_W7FE.md`、`rtm_backfill_W7INFRA.md` 的「實作檔」「自動測試」以頂層頓號切項、去重、保序併入（同一個檔案或測試出現兩次時保留第一個，把後一個的括號註記併進去）；三份的「建議狀態」一律**不採用**，狀態由 QA 逐列依本報告的親跑證據判定。INFRA 回填把同一個測試檔的第二個以後的測試寫成 `::test_x`（省略檔案路徑），合併時補成完整相對路徑；FE 回填的「突變驗證見〈七〉」之類指向回填檔章節的字樣，改成帶檔名的 `見 rtm_backfill_W7FE.md〈七〉`。回填檔裡的敘述性儲存格（例：`API-SET-10` 的「沿用：…」、`INF-VOL-07` 的「沿用（W5）：…；W7 修訂：…」、`BR-13、BR-14` 的「同 API-ENG-01 列的…案例」）不整格併入，改成具名的項目逐一補進。
2. **QA 判定**：每個有判定的列，在「E2E 驗證」欄**附加**一句 `QA 2026-10-17（W7 複驗）：…（QA_W7_Closure.md §n）`（既有文字不動，且是新文字的前綴），並設定狀態。
3. **新列十個**（接在各前綴家族最大號之後，不改既有列號）：`API-ENG-01`（AISDLC_SDD 引擎狀態，接在 `API-IMP-10` 後）、`API-SGN-05`、`API-AUTH-03`、`API-SET-11`（設定鍵生效標籤目錄）、`NFR-9.4-06`（後端分層以 ArchUnit 鎖住）、`INF-SVC-16`（minio-certs）、`INF-VOL-09`（pg_socket）、`INF-VOL-10`（minio_data）、`INF-VOL-11`（minio_certs）、`INF-VOL-12`（prometheus_data）。
4. **V-01～V-03、V-10 的清理**（§6）：十二處過期的測試引用改成現名（涉及 12 列）、`UI-SCR-07` 的情境數、十三列實作欄與十四列測試欄的「待填」、八列過期待辦字樣、檔頭總列數與 §1.2 前綴列數、§3.2／§3.3 以腳本重算（**方法先自證**：對 `HEAD` 的 RTM 扣掉 W5 新增的 `API-PRJ-06`、`API-MON-08`、`BR-26` 後重算，與檔內舊表逐行相同，再套用到含新列的表）。
5. **基線站點鎖的保護**：RTM 一列就是一行，測試名裡剛好含 `skipped` 字樣、行內又有四位以上數字就會命中 `tools/check_pytest_baseline_sites.py` 的判準；合併腳本對這種新項不併入並列出——本輪只有一項：`engine-bridge/tests/test_resources.py::test_processes_that_vanish_or_cannot_be_read_are_skipped_not_fatal`（它仍在回填檔與測試檔裡，只是不放進 RTM 的 `US-M-10` 列）。
6. **驗證合併本身**（`verify_rtm_w7`）：見 §9.3。

### 9.2 統計表（前綴 × 狀態；套用後現查）

依合併後的 `RTM.md` 逐列統計（前綴與狀態都取每列自己的格子；`_rtm_numbers.py` 的輸出，並與 §12.1 的 Grep 現查數字交叉相符）：

| 前綴 | 列數 | ✅ 已驗證 | 🟡 部分 | ❌ 缺陷 | ⬜ 未做 |
|------|-----:|----------:|--------:|--------:|--------:|
| US | 58 | 58 | 0 | 0 | 0 |
| API | 97 | 97 | 0 | 0 | 0 |
| BR | 26 | 26 | 0 | 0 | 0 |
| NFR | 33 | 33 | 0 | 0 | 0 |
| INF | 108 | 108 | 0 | 0 | 0 |
| UI | 52 | 52 | 0 | 0 | 0 |
| **合計** | **374** | **374** | **0** | **0** | **0** |

**W7 前後**：`HEAD` 的 RTM 是 364 列（`✅` 359、`🟡` 5）；合併後 374 列（多 10 個新列，皆 `✅`），原本五列 `🟡`（`API-AUT-06`、`US-M-10`、`NFR-9.1-05`、`NFR-9.3-01`、`INF-VOL-07`）都升 `✅`，沒有任何一列降級。RTM 內的 §3.2（類別×Phase）合計欄＝374，§3.3（層×Phase；複合層計入每個涉及的層，所以加總大於列數）已由腳本依各列重算。誠實註記：全表 `✅` 不等於「沒有缺陷」——DEF-AC-013（P2，資安）與 DEF-AC-014（P3）都是**沒有任何 RTM 列要求**的行為（預覽不執行內嵌腳本、斷線不記 ERROR），所以沒有列因它們掉成 `❌`；它們已在 `UI-MD-01`、`API-SSE-01`、`API-SSE-02` 的 E2E 欄加註，缺陷表在 §10.1。

### 9.3 合併驗證與文件鎖

合併腳本只是工具，所以合併完我又用四支獨立的檢查腳本與根層守門各驗一次（都在 `RTM.md` 寫入之後當回合執行；腳本在暫存目錄，不入庫）：

| 檢查 | 當回合結果 |
|------|------------|
| `verify_rtm_w7.py`（對 `HEAD` 的 RTM 做差異比對） | rc=0：列數 `HEAD` 364 → 工作樹 374；新列 10 個（`API-SGN-05`、`API-SET-11`、`API-AUTH-03`、`API-ENG-01`、`NFR-9.4-06`、`INF-SVC-16`、`INF-VOL-09`～`12`）；非表格行的差異只有 8 個區塊（檔頭列數與 §1.2 前綴列數、§3.2、§3.3 的標題與表）；各欄有變動的既有列數：實作檔 36、自動測試 41、E2E 驗證 93、狀態 5；前綴計數 US 58／API 97／BR 26／NFR 33／INF 108／UI 52；`問題 無` |
| `check_paths.py`（實作檔欄與測試檔路徑存在） | rc=0：檢查 1794 個路徑，不存在 0 個 |
| `check_test_refs.py`（自動測試欄的 `檔案::測試名` 對得到宣告） | rc=0：檢查 1619 個測試引用，找不到 0 個（我把 Java 的判準強化成「必須對得到 `\bname\s*\(` 方法宣告」，所以基線上 12 處過期名稱被掃出來，併入時已更正，見 §6 V-01） |
| `scan_baseline_pattern.py`（逐行套用 `tools/check_pytest_baseline_sites.py` 的兩個判準：同一行有 `passed`／`skipped`（不分大小寫）又有四位以上數字或千分位數，或 `\d{3,5}/\d{1,3}` 配 pytest 脈絡） | `RTM.md`：527 行，命中 0 行 |
| `python tools/check_pytest_baseline_sites.py`（monorepo 根；RTM 寫入後跑） | rc=0：`pytest 基線站點守門通過：12 份掃描檔中僅 SSOT（ONBOARDING.md）載有基線數字（另 34 筆豁免行，見 warning）` |
| 檔案形態 | `RTM.md` 496386 bytes、無 BOM、無 CR（LF 行尾） |
| 表格列內的「待填」 | 0 處（檔頭三行欄位說明仍寫「初值 `待填`」，那是說明文字，不是儲存格） |
| 文件鐵律掃描（本報告、`RTM.md`、本輪改的 e2e `README.md` 與新 spec） | 磁碟絕對路徑（磁碟機代號開頭的路徑、使用者家目錄字樣）與使用者名稱：本報告與 `RTM.md` 都沒有命中（掃描時發現本報告 §2.3 曾寫出 `E2E_ROOT` 的完整路徑，已改成 `%TEMP%\e2e`）；金鑰樣式與密碼字面：無（只有 `task-detail`、`API-TSK-06` 這類恰含 `sk-` 子字串的字面，屬假命中）；新 spec 內的開發預設密碼沿用 W5 的拆開寫法（`["Operator", …].join("#")`），不以整串字面出現 |
| 本報告 `QA_W7_Closure.md` 自身（組裝成最終檔之後） | `scan_baseline_pattern.py` 命中 0 行；再跑一次 `python tools/check_pytest_baseline_sites.py`（monorepo 根）rc=0；檔案 LF 行尾、無 BOM、無 CR（結果見交卷訊息的驗證證據） |

## 10. 缺陷與觀察

### 10.1 新登缺陷

| 編號 | 級別 | 摘要 | 影響的 RTM 列 | 重現與證據 |
|------|------|------|---------------|------------|
| DEF-AC-012 | P4 | Bridge 與 SSOT 對「SDD LATEST」的判定在「工作樹有合法名稱但未入庫的版本目錄」時分歧：Bridge 的 `discover_sdd_root` 掃磁碟、取數字最大者（回 `AISDLC_SDD_v9.99`），SSOT `AISDLC_SDD/scripts/sdd_version.py` 以 `git ls-files` 判定、只認已 tracked 的（回 `AISDLC_SDD_v0.30` 並在 stderr 警告）。本機開發模式（Bridge 預設探索 `REPO_ROOT/AISDLC_SDD`）下，Copy-on-Evolve 剛複製出、尚未 `git add` 的新版目錄會讓 Console 的 SDD 卡顯示新版號，而 ci-gate 仍測舊版；Docker 全棧唯讀掛載的是 git checkout，通常沒有這種目錄，所以不分歧 | `BR-13`（SDD LATEST 版）、`API-ENG-01`（`version.latest`） | `logs\i04_probe.log`（§6 的 I-04 列有逐字輸出）。指令：在拋棄式 git repo 內放 v0.29、v0.30（commit）與未 `git add` 的 v9.99，對同一個 `AISDLC_SDD/` 目錄分別執行 `python AISDLC_SDD/scripts/sdd_version.py --sdd-root <dir>`（印 `AISDLC_SDD_v0.30`）與 `python -c "from app.settings import discover_sdd_root; …"`（在 `engine-bridge/` 內，印 `AISDLC_SDD_v9.99`）。`v0.31.bak`、`v0.30 - Copy` 兩者都正確排除；`git add` 之後與非 git 目錄兩者一致。**處置建議**（QA 不改程式）：二擇一——Bridge 對照 SSOT 的 tracked 過濾；或在 `settings.py` 註明「磁碟語意、刻意與 SSOT 不同」的理由，並把 Architecture §12.2 V-11 的結論改成「已驗：未入庫的合法版本目錄會分歧（DEF-AC-012，P4）」 |
| DEF-AC-013 | **P2（資安）**；**已修（W8，`85ed0915`），W8 複驗通過（§13）** | **【已修，W8 複驗通過】** **Markdown 編輯器預覽會執行內嵌 `<iframe srcdoc>` 裡的腳本（儲存式 XSS 向量）**：編輯器預覽走 `@uiw/react-md-editor` 預設鏈的 rehype-raw，原始 HTML 被建成真元素；`<iframe srcdoc="<script>…">` 的內層腳本與父頁同源，可存取 `parent.sessionStorage`（鍵 `aisdlc.console.session`，值含 access／refresh token）。同一組實驗中 `<img onerror>` 的字串事件處理器被 React 拒絕（pageerror＝React error #231）、`<script>` 元素經 DOM 插入後不執行、`javascript:` 連結的 `href` 被 React 換成只會丟錯的字串（三種載體都不執行，但靠的是 React 的執行期行為，不是明確的消毒）——只有 iframe `srcdoc` 通過。唯讀的專案詳情頁（`MarkdownView`，react-markdown 不渲染原始 HTML）對照組不受影響。**儲存式**：operator 把 payload 寫進專案說明（匯入的 BRD／PRD `.md` 同理），管理者開「編輯專案」頁時，預覽渲染儲存的內容而執行——權限提升（operator→admin）的向量 | `UI-MD-01`（即時預覽）。RTM／PRD §9.2 沒有任何一列要求「預覽不執行內嵌腳本」，所以不改狀態；是否補列與是否升級，請主控決定 | `p9-w7-html.spec.ts` ①～④（②③以 `test.fail(DEFECTS_OPEN)` 釘住，設 `E2E_DEFECTS_FIXED=1` 可看真實失敗訊息）。逐字證據行在 §8.4（`logs\pw_html3.log`）：②預覽端 `window.__w7xss＝"iframe-srcdoc"`、srcdoc 內腳本讀到 sessionStorage 的鍵名 `aisdlc.console.session`；③管理者開已儲存內容的編輯頁同樣執行，鍵名 `aisdlc.console.lastProject,aisdlc.console.session`（只讀鍵名，不讀值、不外送）；④唯讀詳情頁 `window.__w7xss＝null`、頁面內 iframe 數 0。重現：在「新建專案」的說明描述欄貼 `<iframe srcdoc="<script>parent.__w7xss='x'</script>"></iframe>`，預覽端 `window.__w7xss` 變成 `x`（`E2E_DEFECTS_FIXED=1` 可看 spec 的真實失敗訊息）。**根因是待驗假設**（鐵律 10）：`components/markdown/MarkdownEditorImpl.tsx` 第 29～32 行的 `PREVIEW_OPTIONS` 只有 `remarkGfm`、`rehypeHighlight`、`rehypeTaskLabels`，沒有 `skipHtml`、也沒有 `rehype-sanitize`。**候選修法**（QA 未驗證，由 FE 評估）：`PREVIEW_OPTIONS` 加 `skipHtml: true`，或加 `rehype-sanitize`（把 iframe／script／事件屬性剔除）；修好後 ②③會「意外通過」，請移除 spec 內的 `test.fail` 一行 **W8 複驗證據座標**：§13.4（`p9-w7-html.spec.ts` 八個情境全數通過、對修復前建置同一支 spec 為 2 個通過 6 個失敗）、§13.5（Markdown 相關七個檔回歸）、§13.7（本機整套 225 個全數通過）。 |
| DEF-AC-014 | P3；**已修（W8，`520c2850`），W8 複驗通過（§13）** | **【已修，W8 複驗通過】** **SSE 客戶端斷線被記成 ERROR「未預期的例外」，緊接著還有一筆寫不出回應的 WARN**：`StreamController` 的兩條 SSE 端點（`/api/v1/stream/executions/{runId}/logs` 與 `/metrics`）在客戶端斷線（關掉頁面、`EventSource.close()`、curl 被結束）後，Tomcat 以 `AsyncRequestNotUsableException: Servlet container error notification for disconnected client`（cause＝`IOException: Broken pipe`）通知，落到 `GlobalExceptionHandler#handleOther(Exception)`，記一筆 `ERROR 未預期的例外（traceId=null）`；`handleOther` 隨後要把 `ApiError` 寫進已被 `produces=text/event-stream` 定了 Content-Type 的回應，找不到轉換器，再記一筆 `WARN Failure in @ExceptionHandler …（HttpMessageNotWritableException: No converter for [class …ApiError] with preset Content-Type 'text/event-stream;charset=UTF-8'）`。對使用者沒有影響（客戶端已經離開）、串流功能與重連語意不受影響；影響是 ERROR 級日誌被正常行為灌水（以日誌級別計數或告警會被污染，真正的錯誤更難看出來），而且 `traceId` 是 null（非同步分派丟了 MDC） | `API-SSE-01`、`API-SSE-02`（串流端點；功能成立，狀態不改，E2E 欄已加註） | 重現（`logs\sse_repro.log`；Docker 全棧，經 nginx）：①以 admin 登入取 access token；②挑一個 PAUSED 的批次（PAUSED 不結束串流）；③`curl.exe -N -H @<標頭檔> http://localhost/api/v1/stream/executions/<runId>/logs`，4 秒後已收到 87052 bytes，結束 curl；④`docker logs --since <時刻> aisdlc-backend`——30 秒內出現 1 筆 `"level":"ERROR"`（logger `com.aisdlc.console.adapter.in.web.GlobalExceptionHandler`、thread `http-nio-8080-exec-1`、stack 首行 `AsyncRequestNotUsableException`）與 1 筆 `Failure in @ExceptionHandler` WARN；`/metrics` 同樣（4 秒後 684 bytes，結束後 1 ERROR＋1 WARN）。自然發生的次數：本機整套 Playwright 的 backend 日誌（`logs\backend_r010652.log`）13 組，常是同一毫秒兩組（logs 與 metrics 兩條串流一起斷）；Docker 第一次整套 1 組（18:31:11Z，`/executions/{id}/cancel` 的同一秒）。**根因是待驗假設**（鐵律 10）：`GlobalExceptionHandler.handleOther` 是 `Exception.class` 的總接，沒有針對 `AsyncRequestNotUsableException`（或回應已 committed、Content-Type 是 event-stream）略過或降級。**候選修法**（QA 未驗證，由 BE 評估）：加一個 `@ExceptionHandler(AsyncRequestNotUsableException.class)`（不回 body、以 DEBUG 記一行），或在 `handleOther` 內先判斷回應是否已 committed／是否為 event-stream，是的話不寫 body 並降級日誌 **W8 複驗證據座標**：§13.6（本機受控重現與整套日誌統計：ERROR 0、Failure 0；Docker 全棧經 nginx 三輪 ERROR 0）、§13.8（Docker 32 個情境全數通過）。 |

> 本輪新登三筆：DEF-AC-012（P4，文件與取捨層級）、DEF-AC-013（P2，資安，**需要主控決定是否進下一波**）與 DEF-AC-014（P3，日誌衛生）。W7 沒有發現會讓任何 RTM 列掉回 `❌ 缺陷` 的**功能**缺陷：契約 v1.3／v1.4 的新增面（E2E-14～E2E-16）在真後端、真 Bridge、真瀏覽器與 Docker 全棧下都與契約字面一致，唯一的契約字面與實作不同處已由 BE 在回填檔登記（匿名請求的審計主體實作為 `NULL` 而契約寫 `-`；第三個呼叫失敗時 `projects` 保留前兩個呼叫的值，契約 yaml 與 §1.7.1 互相矛盾，實作採 §1.7.1，由 `EnginesApiIT` 釘住）。
>
> W8 複驗（§13）：DEF-AC-013、DEF-AC-014 已修並複驗通過；DEF-AC-012 維持 P4 保留（D-21）；本輪沒有新增缺陷。

### 10.2 觀察（P4，不立缺陷；W5 的 O-22～O-27 之後續號）

| 編號 | 觀察 | 建議 |
|------|------|------|
| O-28 | 前端 vitest 全套在「與 `gradlew clean build` 並行」的負載下，`components/markdown/rehypePrismLinear.test.ts` 的「大文件」案例以 6143ms 逾時（預設 5000ms）；單獨重跑十五個案例 2.75 秒全數通過，閒置機上整套重跑也通過（§3）。負載相依，不是邏輯缺陷 | 該案例若要在 CI 的多 CPU 並行下穩定，把逾時調大或標為效能測試；不阻擋任何閘門 |
| O-29 | `E2E-16` 列 9：前端登出送出的 `POST /auth/logout` 被攔截失敗時，前端仍然導向 `/login` 並清 session，但後端沒有收到撤銷——該 refresh token 在到期前仍可換新（實測：logout 被弄成失敗後，該 RT 換新回 200）。這是契約 §1.9.1（第 1220 行：fire-and-forget，「不等結果，網路失敗或非 2xx 也不阻擋本機登出」）明文接受的代價（登出對使用者永遠要成功），不是缺陷；撤銷是盡力而為 | 若要更強的保證，需要登出重送或短效 refresh token，另案 |
| O-30 | 第一次整套前的單檔執行都在 Windows 本機完成；六支新 spec 起額外的行程與埠（變體 Bridge 18082～18086、假模型伺服器隨機埠），測試中途被強制中止時可能殘留這些行程（`p9-w7-*` 的 `afterAll` 會收，但 Playwright 被 `taskkill` 時不會） | 手動收尾查 `Get-NetTCPConnection -State Listen` 的 18082～18086；§12 有收尾證據 |
| O-31 | 設計稿 `09-settings.png` 的六個分頁名（AI 模型／Agent 行為／執行引擎／監控告警／AutoClaude／AISDLC_SDD）與同目錄 `README.md` 的分頁名（模型／Agent／執行／監控／AutoClaude／SDD）措辭不同——個數與意義一致，只是 PNG 的名稱較長。設計稿內部的兩份權威措辭互不相同；實作取 README | 設計稿的 PNG 與 README 擇一訂正；不影響實作 |
| O-32 | `ADR-001` D1 第 54 行寫「Spring Boot 4.1 的 `spring.threads.virtual.enabled` 預設值未驗」；本輪以 `jcmd Thread.print` 實測：Tomcat 請求執行緒是平台執行緒（`http-nio-18080-exec-N`），即預設未啟用 | 把「未驗」改成實測結論（§6 的 L-03 列） |
| O-33 | `AgentConsole/CLAUDE.md` 的環境變數表仍只寫「`BRIDGE_DB_DSN`：無 DSN＝純檔案模式」，沒有 Architecture §12.1 L-12 的警語（Console 的斷點清單與步驟時間軸依賴 Bridge 的 DB 模式；純檔案模式只適用於單獨驗 Bridge） | 在該列補一句指向 L-12（`AgentConsole/CLAUDE.md` 不在 QA 持有面） |
| O-34 | `agentconsole-ci.yml` 的 `paths` 過濾不含 `AISDLC_SDD/**`（`AgentConsole/**`、`AutoClaude/autoclaude/**`、`AutoClaude/pyproject.toml`、`tools/lib/cpu_budget.py`、workflow 本身），SDD 側改 FSM 狀態檔格式或 `sdd_version.py` 不會觸發 Console 的 CI（審查 I-04 的後半，Architecture §12.2 V-11 要求評估） | 評估加 `AISDLC_SDD/scripts/**` 與 FSM 範本路徑；`.github` 不在本專案可改範圍，交主控 |
| O-35 | Docker 全棧的 backend 容器記憶體貼著上限：起來約 5 分鐘、幾乎閒置時，容器內 cgroup 讀到 `memory.current＝1073618944`、`memory.max＝1073741824`（1GiB 上限，用了約 99.99%）；其中 `anon`＝264314880、`file`＝794705920；JVM 參數 `-XX:+UseZGC -XX:MaxRAMPercentage=75.0`（堆上限約 768MiB）。`OOMKilled＝false`、`RestartCount＝0`，整輪 Docker 測試（含一次重啟 backend 的情境與 90 任務的長批次）都沒有被殺。整輪結束前的最後一次快照（`logs\final_docker_state.log`）：`memory.current＝774692864`（約 739 MiB、上限的 72%；`anon＝329936896`、`file＝431398912`，其中 `shmem＝423624704`），所以用量會隨使用起伏，不是恆貼上限。**根因是待驗假設**：ZGC 的堆積以 memfd 映射、算進 cgroup 的 file／shmem，768MiB 的堆加非堆就可能把 1GiB 填滿；這不是缺陷（沒有 OOM），但餘裕可能是 0 | 高負載（長批次、大匯入）時是否被 cgroup OOM-kill 未驗；若要保守，把 backend 上限提到 1.5GiB 或降 `MaxRAMPercentage`，再用 `docker stats` 與 `memory.stat` 重量一次（`docker-compose.yml` 不在 QA 持有面） |
| O-36 | `aisdlc-pgadmin` 閒置時 `docker stats` 顯示 `219.9MiB / 256MiB`（85.91%），上限是 compose 設的 256MiB（`INF-RES-01`）；`OOMKilled＝false`、`RestartCount＝0`。正式使用（多開查詢視窗）時餘裕很小。pgadmin 日誌另有第三方套件的 `SyntaxWarning`（sshtunnel）與 alembic `UserWarning`，無害 | 評估把上限提到 384～512MiB 再用 `docker stats` 重量（`docker-compose.yml` 不在 QA 持有面） |
| O-37 | `up`／`down`（不帶 `-v`）循環每次留下 5 個匿名孤兒卷：`pgvector/pgvector:pg18`、`aisdlc-postgres-primary:pg18`、`aisdlc-pgbackrest:pg18` 三個映像都宣告 `VOLUME /var/lib/postgresql`（`docker image inspect` 現查），compose 只把具名卷掛在子路徑（`/var/lib/postgresql/data` 等），所以 primary、replica、pgbackrest、minio-certs 各多一個匿名卷，pgadmin 的 `/var/lib/pgadmin` 也是匿名卷。本機現有 26 個 64 字元的匿名孤兒卷（含我這輪留下的 5 個：`a3fd4199b0c5…`、`7df67c3a4325…`、`e8d688ff225e…`、`c31dbc553ad3…`、`432adf1657c8…`）；無功能影響，沒有逐個量大小。我沒有執行任何刪卷指令 | compose 對這幾個服務加上 `/var/lib/postgresql` 的對應宣告，或在 README 清場一節說明這些孤兒卷與清理指令（會刪卷的指令不在 QA 範圍） |
| O-38 | Grafana 啟動日誌有 2 筆 `level=error`：`/etc/grafana/provisioning/plugins` 與 `/etc/grafana/provisioning/alerting` 目錄不存在（compose 只掛了 `provisioning` 的 datasources 與 dashboards 子目錄）；另有 `storage.unified.migrations` 的 warn（`no such table`）。這是 Grafana 容忍的情形、不影響面板（兩個 dashboard 皆 provisioned、查詢重放全 200），但每次啟動都印 error 級日誌，會被日誌告警誤判 | 在 provisioning 目錄放空的 `plugins/`、`alerting/` 子目錄即可消除 |
| O-39 | backend 啟動日誌兩筆 WARN：`SpringDoc /swagger-ui.html endpoint is enabled by default. To disable it in production…` 與 `/v3/api-docs` 同形——Docker 全棧（正式形態）沒有關掉它們。對外面：經 nginx 的 `/swagger-ui.html`、`/v3/api-docs` 是 404（落到 Next.js）、`/api/v3/api-docs` 是 401（`/api/` 一律要 JWT），所以目前不外露；容器內直連 `http://127.0.0.1:8080/v3/api-docs` 回 200、`/swagger-ui.html` 回 302。不外露靠的是 nginx 沒有轉發這兩個路徑這個事實 | 正式 profile 依 WARN 內文建議關掉 SpringDoc 兩個端點，或登記為刻意保留 |

## 11. 未覆蓋與保留的口徑

**RTM 上五列「部分」在本輪都升到 `✅ 已驗證`**（§4）；各列的口徑界線如下，請不要把它讀得比證據大：

1. **`NFR-9.3-01`（可用性 99.5%）驗的是量測機制，不是 30 天可用率的數值**：Prometheus 規則與告警（promtool 單元測試三條指令 rc 全 0）、全棧上規則載入、`ratio_*` 有值、Grafana 面板查詢 200 無錯誤、`prometheus_data` 卷讓歷史跨 `down` 存活；實際的 30 天數值只能由持續運轉的環境在 Grafana 看。依 W7 掌舵者口徑（D-14）升 `✅`，E2E 欄逐字寫明。
2. **`US-M-10`（資源使用情況）**：本機（Windows 行程樹）與 Docker（Linux 容器內行程樹）兩端各驗一次；`cpuPercent` 的**數值正確性**（滿載時是否貼近 100）沒有在容器內做 CPU 滿載實驗，由 Bridge 的 pytest（真行程測試與正規化單元測試）負責。
3. **`INF-VOL-07`（HTTPS）**驗的是自簽憑證路徑；CA 簽發的真憑證申請與續期不在專案範圍（README〈14〉已寫明）。
4. **`NFR-9.1-05`**：口徑是 W5 同一把尺（真瀏覽器、production standalone、每種大小七次取中位數；中位數 < 100ms）；它對機器負載敏感，QA 在閒置機（CPU 約 2～4%）上量測三次，與整套中的第四次一起列在 §4.3。

**本輪沒有做、或只做一部分的事**（不宣稱已驗證）：

1. **前端全量覆蓋率只是資訊值**（§3）：ADR-001 G-21 的口徑仍是 `coverage.include` 子集，本輪沒有改門檻也沒有把全量當閘門。
2. **Bridge 純檔案模式下 Console 的斷點清單與步驟時間軸**（審查 I-07／Architecture L-12 的「待驗」）：已在本輪補驗（§8.4）——批次本身正常，但兩個畫面的資料是空的。沒做的是「純檔案模式下 Console 其餘功能（匯入、監控圖表、SSE 日誌…）逐項是否可用」，只量了 Console 唯二被 L-12 點名的兩個端點。
3. **V-05 的 63 列 INF**（§8.3）：56 列完整重驗、6 列部分重驗、1 列未逐列重驗。**沒有演練**的破壞性或需要等時間的事項（各列 E2E 欄與 §8.3 都寫明，沿用 W2-B／W5 的證據）：cron 排程的**實際觸發**（我跑的是同一支腳本，不是等 cron）、`restore.sh`／PITR 還原（`INF-DR-16`）、手動 failover（`INF-DR-17`）、RPO／RTO 目標（`INF-DR-18`）、備份保留份數的實際滾動（`INF-DR-13`）、replica 刪卷重建（`INF-DR-06`）、pg_dump 離站備份的真實還原（只驗到 `pg_restore` 讀得到 TOC 90 筆，沒有還原進資料庫）、各資料卷「`down` 後重起、資料仍在」（只有 `redis_data` 與 `prometheus_data` 實測）；`INF-DR-19`（崩潰自動重啟）只對 redis 一個容器以 `redis-cli shutdown nosave` 模擬崩潰，沒有對 backend、Bridge、PostgreSQL 逐個驗。
4. **真 LLM 與真 Claude CLI**：E2E-14 的 Brain 請求打的是本檔自起的假模型伺服器（分類計數用），引擎與 Bridge 是真的；Docker 與本機的執行批次都用 `aisdlc-mock-claude`。所以「Brain 校正真的改寫了 prompt」的**語意品質**沒有驗，驗的是「請求有沒有發、發幾次、磁碟上的設定檔是什麼、金鑰有沒有洩漏」。
5. **引擎的「自演化」只提案、不套用**（Architecture L-10）：`engineCapabilities.selfEvolution=ENABLED` 的意思只是「有金鑰、會產生提案」；E2E-14 列 2、列 3 都斷言沒有 `evolved_*.yaml`，但「日後引擎真的套用演化」的行為不在本輪範圍。
6. **瀏覽器與平台**：全部在 Chromium、Windows 11 主機、Docker Desktop；沒有 Firefox／WebKit、沒有 Linux／macOS 主機。Docker 內 Linux 容器的行為（資源取樣、Bridge 映像的 `git`、SDD 唯讀掛載）有驗，但主機側的 bash 形態指令（README 並列的 bash 區塊）沒有在 macOS／Linux 實跑。
7. **全棧的冷啟動**：Docker 全棧是在有映像快取與既有資料卷（W7-INFRA 殘留）的機器上 `up -d --build --wait`；有驗到「既有 PostgreSQL 資料卷上 Flyway V10／V11 升級」，沒有驗「完全乾淨的 Docker 環境從零 build」。
8. **持續重跑機制（V-09）**：真後端 E2E 仍是人工輪跑（D-20）；本輪證明它們**現在**全綠，不證明之後仍綠。
9. **契約字面與實作的兩處已登記的差異**（BE 回填檔〈八〉）：匿名請求的審計主體；第三個呼叫失敗時 `projects` 的保留。QA 依實作行為驗證，契約字面請 SA 訂正。
10. **SSE 斷線日誌的探測範圍**（DEF-AC-014）：重現只用了 curl 在 PAUSED 的批次上對 `/logs` 與 `/metrics` 兩條端點各斷線一次，加上整套與 Docker 整套日誌裡自然出現的次數（本機 13 組、Docker 1 組）；沒有量瀏覽器 `EventSource` 的各種斷線形態（網路中斷、電腦睡眠、nginx 逾時切斷），也沒有量「執行中批次」與「終態後」兩種狀態下斷線的日誌是否不同，更沒有驗證候選修法。
11. **內嵌 HTML 的探測範圍**（DEF-AC-013）：我只測了四種載體（`<iframe srcdoc>`、`<img onerror>`、`<script>`、`javascript:` 連結）與兩個編輯面（「新建專案」的對話框、已儲存專案的「編輯專案」頁）。`<object>`／`<embed>`、`<svg onload>`、`<form action=javascript:>`、`<meta http-equiv=refresh>`、`data:` 位址的 iframe，以及目標、任務、匯入節點的編輯器，都沒有逐一驗；修好時請以消毒白名單為準整組重驗，不要只重跑我釘住的兩個情境。

## 12. 給主控的提醒

### 12.1 RTM 最終數字（本報告完成後以 Grep 現查，不是腳本自報）

以下是合併後對 `AgentConsole/docs/06_quality/RTM.md` 現查的數字（表格列的判準是行首 `| US-`／`| API-`／`| BR-`／`| NFR-`／`| INF-`／`| UI-`，檔頭欄位說明不計；下面兩種寫法並列，實際執行的是 PowerShell 形態與 Grep 工具，見表後註）：

```bash
grep -cE '^\| (US|API|BR|NFR|INF|UI)-' AgentConsole/docs/06_quality/RTM.md
grep -cE '^\| (US|API|BR|NFR|INF|UI)-.*\| ✅ 已驗證 \|$' AgentConsole/docs/06_quality/RTM.md
grep -cE '^\| (US|API|BR|NFR|INF|UI)-.*\| (🟡|❌|⬜)' AgentConsole/docs/06_quality/RTM.md
```

```powershell
(Select-String -Path AgentConsole\docs\06_quality\RTM.md -Encoding utf8 -Pattern '^\| (US|API|BR|NFR|INF|UI)-').Count
(Select-String -Path AgentConsole\docs\06_quality\RTM.md -Encoding utf8 -Pattern '^\| (US|API|BR|NFR|INF|UI)-.*\| ✅ 已驗證 \|$').Count
(Select-String -Path AgentConsole\docs\06_quality\RTM.md -Encoding utf8 -Pattern '^\| (US|API|BR|NFR|INF|UI)-.*\| (🟡|❌|⬜)').Count
```

| 項目 | 現查值 |
|------|-------:|
| 總列數 | 374（US 58／API 97／BR 26／NFR 33／INF 108／UI 52） |
| `✅ 已驗證` | 374 |
| `🟡 部分` | 0 |
| `❌ 缺陷` | 0 |
| `⬜ 未做` | 0 |

（Grep 工具與 `Select-String` 兩種寫法在本輪都實跑過：總列數 374、`✅` 374、`🟡`／`❌`／`⬜` 各 0；bash 形態是同一個正規式的 POSIX 寫法，我在這台 Windows 機器上沒有跑。）

### 12.2 需要你決定或動手的事

1. **【已結案（W8）】DEF-AC-013（P2，資安）**：主控裁決 D-21 進 W8，已修於 `85ed0915`，W8 複驗全數通過（§13.4，spec 的 `test.fail` 已移除）。以下是第一輪當時的決定項原文，保留作歷史——**要不要進下一波**：編輯器預覽會執行內嵌 `<iframe srcdoc>` 裡的腳本，而且是儲存式（operator 存、管理者開編輯頁就中，§10.1）。候選修法在 `components/markdown/MarkdownEditorImpl.tsx` 第 29～32 行的 `PREVIEW_OPTIONS` 加 `skipHtml: true` 或 `rehype-sanitize`（QA 沒驗證）。已用 `p9-w7-html.spec.ts` 的 `test.fail` 釘住；**修好後那兩個情境會「意外通過」而變紅，要同一個 commit 移除 spec 內的 `test.fail` 一行**。沒有 RTM 列要求「預覽不執行內嵌腳本」，所以我沒動狀態、只在 `UI-MD-01` 加註；要不要補列由你定。
2. **【已結案（W8）】DEF-AC-014（P3）**：已修於 `520c2850`，W8 複驗全數通過（§13.6）。以下是第一輪當時的決定項原文，保留作歷史：SSE 客戶端斷線被 `GlobalExceptionHandler.handleOther` 記成 ERROR「未預期的例外」，並多一筆寫不出回應的 WARN（§10.1，重現指令與候選修法都在那裡）。功能不受影響，是日誌衛生；`API-SSE-01`、`API-SSE-02` 的 E2E 欄已加註、狀態不改。
3. **DEF-AC-012（P4）**：Bridge 與 SSOT 對 SDD LATEST 的判定在「未入庫的合法版本目錄」時分歧（§10.1）。二擇一：Bridge 對照 SSOT 的 tracked 過濾，或在 `engine-bridge/app/settings.py` 註明「磁碟語意、刻意不同」並把 Architecture §12.2 V-11 的結論改成實驗結果。
4. **文件訂正（不在 QA 持有面，請主控或 SA 落字）**：
   - `ADR-001` D1 第 54 行：把「虛擬執行緒預設值未驗」改成實測結論（Tomcat 請求執行緒是平台執行緒，§6 L-03；觀察 O-32）。
   - `Architecture.md` §12.2 V-11：把 I-04 的「待驗」改成實驗結論與 DEF-AC-012（§6 I-04）。
   - `AgentConsole/CLAUDE.md` 環境變數表 `BRIDGE_DB_DSN` 列補一句指向 Architecture §12.1 L-12（觀察 O-33）；§6 I-07 的純檔案模式實測結果（§8.4）可作為那句警語的依據。
   - `.github/workflows/agentconsole-ci.yml` 的 `paths` 過濾加 `AISDLC_SDD/scripts/**` 與 FSM 範本路徑（觀察 O-34；`.github` 不在本專案可改範圍）。
   - 契約 §1.9／§1.7.1 字面兩處與實作不同（BE 回填檔〈八〉已登記）：匿名請求的審計主體實作為 `NULL`（契約寫 `-`）；第三個呼叫失敗時 `projects` 保留前兩個呼叫的值（契約 yaml 與 §1.7.1 互相矛盾，實作採 §1.7.1，`EnginesApiIT` 釘住）。請 SA 訂正契約字面。
5. **觀察 O-28～O-39**（§10.2）都是 P4，不阻擋；O-28（vitest 在並行負載下逾時）若 CI 的多 CPU 並行下偶發紅，把該案例逾時調大；O-35（backend 記憶體貼著 1GiB 上限）與 O-36（pgadmin 閒置就用掉 86% 上限）是 compose 資源上限的餘裕問題，高負載下的行為未驗；O-39（SpringDoc 端點在正式形態沒關）目前靠 nginx 沒轉發才不外露。
6. **Playwright 真後端 E2E 的持續重跑（V-09、D-20）**仍是人工輪跑；`*.mock.spec.ts` 共 71 個情境每次 push 在 CI 的 mock job 重跑，本輪都已隨整套通過。

### 12.3 要 commit 的檔案（皆在我的持有面）

路徑一律相對 monorepo 根；`git --no-optional-locks status --porcelain` 的完整輸出在交卷報告末尾。

| 類別 | 檔案 |
|------|------|
| 新增 e2e 檔（9 支，`AgentConsole/frontend/tests/e2e/`） | `w7.ts`、`p9-w7-engine.spec.ts`、`p9-w7-resources.spec.ts`、`p9-w7-sdd.spec.ts`、`p9-w7-signoffs.spec.ts`、`p9-w7-ui.spec.ts`、`p9-w7-purefile.spec.ts`、`p9-w7-html.spec.ts`、`p9-w7-docker.stack.ts` |
| 修改 e2e 檔（2 支） | `p9-w5-ui-evidence.spec.ts`（NFR-9.1-05 的 20KB 上限 400ms 收緊為 100ms）、`README.md`（新增〈W7 複驗〉節與檔案表、環境變數） |
| 新截圖（16 張，`__screenshots__/`） | `p9-w7-agent-bridge-down.png`、`p9-w7-agent-resources.png`、`p9-w7-dag-fullscreen.png`、`p9-w7-pending-card.png`、`p9-w7-project-edit-locked.png`、`p9-w7-screen-01-dashboard.png`、`-02-projects`、`-03-project-detail`、`-04-goal-detail`、`-05-task-detail`、`-06-import-step1`、`-06-import-step2`、`-07-execute`、`-08-monitor`、`-09-settings`、`p9-w7-sdd-card.png`。**已追蹤的舊截圖我都已依 `HEAD` 還原（位元組一致），不要 commit 它們的任何變動**；整套與各 spec 每跑一次都會改寫它們 |
| 文件（`AgentConsole/docs/06_quality/`） | 新增 `QA_W7_Closure.md`；修改 `RTM.md`（單線合併三份回填檔，§9）、`rtm_backfill_W3B1.md`（三處）、`rtm_backfill_W3B2.md`（一處）、`rtm_backfill_W5BE.md`（一處）——後三者只把過期的測試名換成現名（§6 V-01） |
| **不是我改的**（開始前就是髒檔，請主控自行處置） | `AgentConsole/docs/04_planning/Implementation_Plan.md`、`AutoClaude/.perf_baseline.toml` |

### 12.4 環境殘留與收尾證據

收尾於 2026-10-17 03:05 前後；以下每一項都是收尾時當回合現查的輸出（log 在暫存目錄的 `w7_qa\logs\`）：

| 項目 | 狀態與證據 |
|------|------------|
| Docker 全棧 | 收尾只做 `down`（**不帶 `-v`**；`dc.ps1` 會拒絕 `down -v`）：`compose down rc=0`，14 個長駐容器與兩個一次性 job 都已移除，`aisdlc_backend-net`／`aisdlc_db-net`／`aisdlc_frontend-net` 三個網路移除。`docker ps -a` 現在只剩 `autoclaude_pg`（別的專案，`Up 42 hours (healthy)`，全程沒動；5432 仍由它發布） |
| 具名卷 | 12 個 `aisdlc_*` 全數保留（`logs\stack_snap_after.log`）：起跑前殘留 11 個，本輪新增 `aisdlc_prometheus_data`。**`aisdlc_nginx_certs` 內現在是我在 §4.5 產生的自簽憑證**（30 天，`notAfter=Nov 15 18:52:10 2026 GMT`），不是原本那一張；兩張都是 `CN=localhost`，不影響任何功能。資料卷內另有我跑的備份（pgBackRest repo1／repo2 各一份 full 與一份 diff、MinIO 的 `offsite/aisdlc-db-backup/logical/` 一份 pg_dump）與 Redis 的撤銷鍵、PostgreSQL 內 E2E 造出的專案與批次（資料庫沒有重置） |
| 匿名孤兒卷 | 本機共 26 個 64 字元的匿名孤兒卷，其中 5 個是我這輪的容器留下的（`a3fd4199b0c5…`、`7df67c3a4325…`、`e8d688ff225e…`、`c31dbc553ad3…`、`432adf1657c8…`），來源見觀察 O-37。我沒有執行任何刪卷指令 |
| 映像 | 本輪 `up -d --build` 重建了五個自建映像（`aisdlc-backend:dev` `1afdb9529ac3`、`aisdlc-frontend:dev` `303afb3c5c7a`、`aisdlc-engine-bridge:dev` `aeeeae74dea8`、`aisdlc-pgbackrest:pg18` `db04c923f95b`、`aisdlc-postgres-primary:pg18` `7d30adf4edcc`）；舊的 `:w5`、`:master` 標籤與 `aisdlc-sdd-ci:local` 原樣留著 |
| 本機服務 | backend 18080、Bridge 18081 與 18082～18086、前端 3000、`qa-pg`（25433）都已停止並移除：`docker ps -a` 沒有 `qa-pg`；對 80、443、3000、3001、3100、5050、8080、8081、9090、18080～18086、25433 查 `Get-NetTCPConnection -State Listen` 為空；沒有任何帶 `w7_qa`、`console-0.0.1`、`fake_brain`、`playwright` 字樣的 java／node／python 行程 |
| 主機 5433 | 不是本專案：本機原生 `postgresql-x64-18` Windows 服務（PID 6848）在聽，我沒有動它 |
| 暫存資料 | `E2E_ROOT`（`%TEMP%\e2e`）仍在，1222 個檔、3.8 MB（`projects`、`workspace`、`quota-cache`、`bridge-logs`、夾具），可直接刪；Playwright 的輸出目錄在暫存區、各 spec 的 trace 與影片在其中；所有腳本、log、報告草稿在 session 暫存目錄（不在 repo） |
| 建置產物 | `AgentConsole/backend/build/` 與 `AgentConsole/frontend/.next/` 都被 `.gitignore` 忽略（`git status` 沒列）。**前端 `.next` 是用 `NEXT_PUBLIC_API_URL=http://localhost:18080` 建的**（e2e 用），要回到一般本機開發請重建 |
| 工作樹 | `docker/nginx/conf.d/https.conf` 不存在、`default.conf` 位元組與 `HEAD` 相同（§4.5）；已追蹤的 `__screenshots__` 依 `HEAD` 位元組還原後 `git diff` 為 0 張（`restore_screens.py`：`被改寫的已追蹤截圖：0 張`）；16 張新截圖與 `HEAD` 之外的差異只有新檔 |
| 沒動的東西 | `autoclaude_pg` 與 5432、`AutoClaude/`、`AISDLC_SDD/`、`.claude/`、`tools/`、`.github/`、後端與前端與 Bridge 的程式碼；沒有 commit、沒有 push、沒有派子 agent |

## 13. 第二輪複驗（W8，DEF-AC-013／014）

> 本節是 W8-QA（第二輪、獨立零信任）的補充：第一輪（§1～§12）的結論與數字維持當時的描述不改；本節只回答「主控依 D-21 修掉的兩筆缺陷，修好了沒有、有沒有帶來回歸」。`<SCRATCH>` 是本輪 session 的暫存目錄（絕對路徑寫在交卷訊息裡，文件不寫磁碟絕對路徑，與第一輪同做法）；本輪的腳本與 log 在 `<SCRATCH>\w8_qa\`，log 在其下的 `logs\`。測試計數一律寫中文或不與日期同行。

### 13.1 結論與數字

**結論**：DEF-AC-013（P2，資安）與 DEF-AC-014（P3）都已修好並通過複驗，沒有發現回歸、沒有新缺陷。RTM 現查（`Grep`）：總列 374、`✅ 已驗證` 374、`🟡`／`❌`／`⬜` 各 0；`UI-MD-01`、`API-SSE-01`、`API-SSE-02` 三列的 E2E 欄已把「未修」改成「已修＋W8 證據」，狀態維持 `✅`。DEF-AC-012 維持 P4 保留（D-21），本輪不修、也沒有重驗。

| 項目 | 當回合實測 | 節 |
|------|------------|----|
| 被驗版本 | HEAD `38e46582`；修復 commit：前端 `85ed0915`、後端 `520c2850`（兩者 `git show --stat` 現查，改動檔與任務書相符）；工作樹起點只有一個髒檔＝上一位 QA 半改的 `p9-w7-html.spec.ts` | 13.2 |
| 後端產物來源 | 本機 backend jar 與 Docker 映像內建出的 jar 位元組完全相同（SHA-256 皆 `5F88DC22…15EB`、109718408 bytes）；jar 內 `GlobalExceptionHandler.class` 含 `handleClientGone` | 13.2 |
| 前端閘門 | `npm run lint` rc=0（第一次 rc=1，原因與處置見 13.3）、`tsc --noEmit` rc=0、`npm run build` rc=0（內嵌 `http://localhost:18080`）、vitest rc=0：57 個檔、909 個案例全數通過 | 13.3 |
| `p9-w7-html.spec.ts` | 八個情境對真後端、真瀏覽器（production 建置）**全數通過**（20.8 秒、0 失敗，已沒有任何 `test.fail`）；同一支 spec 對**修復前**的前端建置跑：2 個通過（①④）、6 個失敗（②③⑤⑤b⑥⑥b）——證明新增情境鑑別得出缺陷 | 13.4 |
| Markdown 相關回歸 | 七個檔共 41 個情境全數通過（13.5 分）；NFR-9.1-05 的 20KB 預覽更新中位數 55ms（整套中 58ms），上限 100ms | 13.5 |
| DEF-AC-014 受控重現（本機） | 3 輪 × 2 條串流（`/logs`、`/metrics`），每輪都先確認兩條串流開著且收到資料、再同時結束 curl：30 秒內 `level=ERROR` 0 筆、`Failure in @ExceptionHandler` 0 筆；DEBUG 開時每條串流斷線恰一行 DEBUG（共 6 行），預設等級完全不記 | 13.6 |
| 本機整套 Playwright | **225 個全數通過**（0 失敗、0 略過；68.2 分，34 個檔；第一輪是 213 個、67.5 分）；跑完 backend 日誌 `ERROR` 0 筆、`Failure in @ExceptionHandler` 0 筆（第一輪同型整套留下 13 筆 ERROR 與 13 筆 WARN；這次同樣 13 次自然斷線全變成 DEBUG 行） | 13.7 |
| Docker 全棧（加分項） | `up -d --build --wait` rc=0（67 秒）；經 nginx 三輪斷線 `ERROR` 0、`WARN` 0；Docker 32 個情境全數通過（13.0 分）；跑完容器日誌 313 行：INFO 307、WARN 6（SpringDoc 4＋Redis 降級情境的預期 WARN 2）、ERROR 0 | 13.6、13.8 |
| 其他 | 上一位 QA 第二輪留下的「4 通過、4 失敗」不是 FE 修法的缺陷，是前端建置沒有內嵌 API 位址（13.9） | 13.9 |

### 13.2 被驗版本、產物來源與環境

| 項目 | 值 |
|------|----|
| 主機與工具 | Windows 11 專業版 10.0.26300（20 個邏輯核心）；Node v22.23.3／npm 10.9.9、OpenJDK 21.0.10、Python 3.11.9（根層 `.venv`）、Playwright 1.64.1（Chromium）、Docker 29.5.3／Compose 5.1.4；所有指令都用 PowerShell 工具執行（Windows 上禁用 Bash 工具） |
| 被驗 commit | 前端修法 `85ed0915`：`MarkdownEditorImpl.tsx`（`pluginsFilter` 的 `omitRawHtml` 拿掉預設鏈的 rehype-raw、`urlTransform` 走 `safeUrl.ts`）、`MarkdownView.tsx`（同一支白名單）、`safeUrl.ts`（新）、`markdown.test.tsx` 加測、`markdown-preview.mock.spec.ts`（新，3 個情境）；後端修法 `520c2850`：`GlobalExceptionHandler.handleClientGone`（`AsyncRequestNotUsableException` 專屬處理器，回 void、只記一行 DEBUG，traceId 取回應標頭 `X-Trace-Id`、日誌只記路徑不記 query string）、`StreamDisconnectApiIT`（新）、`GlobalExceptionHandlerTest` 加測。我讀了這幾支改動檔的現況（不採信 commit 訊息） |
| 靜態檢查（Grep，全 `frontend/` 原始碼） | Markdown 渲染只有兩條路徑：`MarkdownEditorImpl.tsx`（唯一的 `MDEditor` 匯入、`MDEditor.Markdown` 只用在預覽窗並帶 `PREVIEW_OPTIONS`）與 `MarkdownView.tsx`（`ReactMarkdown`）；沒有任何 `dangerouslySetInnerHTML`；`rehype-raw` 只在 `MarkdownEditorImpl.tsx`（拿來做函式身分比對）與測試檔出現。目標、任務、匯入節點的編輯器（`EntityForms.tsx`、`NodeEditDialog.tsx`、`TreeEditor.tsx`）都是同一個 `MarkdownEditor` 元件，專案、目標、任務的詳情頁（`ProjectDetailView.tsx`、`GoalDetailView.tsx`、`TaskDetailView.tsx`）都是同一個 `MarkdownView`，所以共用同一個修法 |
| 本機 backend jar | `AgentConsole/backend/build/libs/console-0.0.1-SNAPSHOT.jar`：109718408 bytes、mtime 2026-10-17T04:22:35+08:00、SHA-256 `5F88DC2271A24A99B4D383F4A6E865AE1E52A3158F46E24F40287076241A15EB`；以 Python `zipfile` 讀 `BOOT-INF/classes/com/aisdlc/console/adapter/in/web/GlobalExceptionHandler.class`（18140 bytes）含 `handleClientGone`（`logs\jar_probe_local.txt`）。我沒有重跑 `gradlew`（任務書：不需要），改以下一列的獨立來源交叉驗證 |
| Docker 映像內的 jar | `docker cp aisdlc-backend:/app/app.jar` 取出：109718408 bytes、SHA-256 `5F88DC2271A24A99B4D383F4A6E865AE1E52A3158F46E24F40287076241A15EB`——**與本機 jar 位元組完全相同**（`logs\jar_probe_docker.txt`）。映像是 `Dockerfile` 的 builder 階段在容器內用 `./gradlew bootJar --no-daemon -x test` 從 `backend/src` 建出的；本輪 `up -d --build` 時 `COPY src src`、`RUN ./gradlew bootJar`、`COPY --from=builder … app.jar` 三層都標 `CACHED`（`logs\stack_up2.log` 的 #50、#44、#48；BuildKit 以內容雜湊比對，命中代表現在工作樹的 `backend/src` 與建出那顆 jar 時的內容一致）。三者（工作樹原始碼、Docker 內建出的 jar、本機 jar）互相印證，不是只信主控的 `gradlew clean build` |
| 前端 `.next`（e2e 用） | 我以 `NEXT_PUBLIC_API_URL=http://localhost:18080 npm run build` 重建（rc=0，16 秒）；掃 `.next` 的 JS：`localhost:18080` 出現在 2 個檔、`localhost:8080` 為 0 個——確認內嵌的是 e2e 的後端位址 |
| 本機環境形態 | 同 §2.3：PG 25433（容器 `qa-pg`）→ backend 18080（`e2e` profile）→ 假 Brain 版 Bridge 18081 → 重啟 backend；前端 3000（standalone，Playwright 的 webServer 起）；`E2E_ROOT` 是 `%TEMP%\e2e`；每次 Playwright 都帶自己的 `--output`。本輪另在 backend 啟動參數加 `--logging.file.name=<SCRATCH>\w8_qa\logs\backend_r<時分秒>.log.spring.log`（Spring 自己寫 UTF-8 日誌；PowerShell 5.1 的 `*>` 擷取檔是 UTF-16 且被主機碼頁弄成亂碼，只能比對 ASCII 片段），整套與 DEBUG 受控重現時再加 `--logging.level.com.aisdlc.console.adapter.in.web.GlobalExceptionHandler=DEBUG` |
| 我接手時的殘留 | 上一位 QA 第二輪留下整套仍在運轉：Docker 全棧 14 個長駐服務（`Up 5 hours`，04:41 啟動）、`qa-pg`、本機 backend（PID 37440，04:41 起）與假 Brain Bridge（PID 28572）。我先對全棧 `docker compose … down`（**不帶 `-v`**，12 個 `aisdlc_*` 卷前後都是 12 個；`logs\leftover_stack_down.log`），本機行程與 PG 由 `reset_local.ps1` 換成我自己起的（`logs\reset1.log`） |

### 13.3 前端閘門（`<SCRATCH>\w8_qa\logs\`）

```powershell
Push-Location AgentConsole\frontend; npm run lint; npx tsc --noEmit; Pop-Location
Push-Location AgentConsole\frontend; $env:NEXT_PUBLIC_API_URL="http://localhost:18080"; npm run build; Pop-Location
Push-Location AgentConsole\frontend; npx vitest run; Pop-Location
```

```bash
(cd AgentConsole/frontend && npm run lint && npx tsc --noEmit)
(cd AgentConsole/frontend && NEXT_PUBLIC_API_URL=http://localhost:18080 npm run build)
(cd AgentConsole/frontend && npx vitest run)
```

（實際用 PowerShell 形態、每行指令各自 `*> log` 後讀 `$LASTEXITCODE`，不接管線；bash 形態在這台 Windows 機器上沒有跑。）

| 指令 | rc | 關鍵輸出（逐字） | log |
|------|----|------------------|-----|
| `npm run lint`（第一次，改完 spec 後） | **1** | `[warn] tests/e2e/p9-w7-html.spec.ts`／`[warn] Code style issues found in the above file. Run Prettier with --write to fix.` | `lint1.log` |
| `npx prettier --write tests/e2e/p9-w7-html.spec.ts` | 0 | 只重排上一位 QA 半改時寫的兩行 `console.log`（⑤、⑥ 各一行，6 行新增、2 行刪除，`prettier_diff.txt`）；內容不變 | `prettier_write.log` |
| `npm run lint`（重跑） | 0 | `All matched files use Prettier code style!` | `lint2.log` |
| `npx tsc --noEmit` | 0 | （無輸出，log 0 bytes） | `tsc2.log` |
| `NEXT_PUBLIC_API_URL=http://localhost:18080 npm run build` | 0 | 16 秒；路由表末列 `└ ○ /settings` | `build1.log` |
| `npx vitest run` | 0 | `Test Files  57 passed (57)`／`Tests  909 passed (909)`／`Duration  30.37s` | `vitest1.log` |

### 13.4 `p9-w7-html.spec.ts` 最終版

**改了什麼**（`AgentConsole/frontend/tests/e2e/p9-w7-html.spec.ts`，接上一位 QA 半改的檔）：移除 ②、③ 兩行 `test.fail(DEFECTS_OPEN, …)` 與已無人使用的 `DEFECTS_OPEN` 匯入；②③ 的標題與檔頭註解改成正向敘述（「不執行」，註明 W8 修於 `85ed0915`）；保留 ①④⑤⑤b⑥⑥b；Prettier 重排兩行 `console.log`。`tests/e2e/` 全樹 Grep：沒有任何 spec 再用 `test.fail(DEFECTS_OPEN`；`realBackend.ts` 的 `DEFECTS_OPEN` 與環境變數 `E2E_DEFECTS_FIXED` 保留為機制（下次登記未修缺陷時照用），`README.md` 第 115、156 行已同步（本輪起沒有 spec 用它釘住缺陷）。

**最終情境清單（八個）**：

| 情境 | 驗什麼 |
|------|--------|
| ① 編輯器預覽 | img onerror、script 標籤、javascript: 連結三種載體都不執行（新建專案對話框；含點連結後開出的視窗） |
| ② DEF-AC-013（P2） | 同一個預覽裡 `<iframe srcdoc>` 內的腳本不執行（修前會執行、可讀 sessionStorage） |
| ③ DEF-AC-013 儲存式 | 專案說明已存著 iframe srcdoc，管理者開「編輯專案」頁，預覽不執行 |
| ④ 對照 | 同一份已儲存內容在唯讀的專案詳情頁不執行、頁面內 iframe 為 0 |
| ⑤ meta／base | 新建專案預覽貼入 `<meta http-equiv=refresh>` 與 `<base href>`：文件內兩者皆 0、原文以文字顯示 |
| ⑤b meta／base（儲存式） | 管理者開編輯頁與詳情頁，文件內兩者皆 0、編輯頁預覽以文字顯示原文 |
| ⑥ 連結白名單 | https、mailto 保有 href；javascript:、tel: 整個拿掉 href；點了不導頁、預覽仍在、不執行 |
| ⑥b 連結白名單（儲存式） | 編輯頁預覽與詳情頁的連結規則一致 |

**修後（HEAD）的執行結果**（`run_pw.ps1 -Tag html`，輸出目錄 `<SCRATCH>\w8_qa\pw_out\html`，log `logs\pw_html.log`、rc 檔 `logs\pw_html.rc.txt`＝`rc=0 elapsed_sec=23`；`[w7-html]` 行與摘要行逐字）：

```
[w7-html] ①預覽端建出的元素＝{"img":0,"imgHasOnerror":false,"script":0,"anchorHref":null,"details":0}；window.__w7xss＝null；點連結後開出的視窗數＝0、其 __w7xss＝[]；主控台錯誤數＝0
[w7-html] ②DEF-AC-013 預覽端：window.__w7xss＝null；srcdoc 內腳本讀到的 sessionStorage 鍵名＝null（只讀鍵名，不讀值）
[w7-html] ⑤新建專案預覽：貼入前文件＝{"metaRefresh":0,"base":0}；貼入後文件＝{"metaRefresh":0,"base":0}；預覽文字含 http-equiv＝true
[w7-html] ⑥新建專案預覽的連結＝{"官網":{"hasHref":true,"href":"https://example.com/w7"},"寄信":{"hasHref":true,"href":"mailto:qa@example.com"},"撥號":{"hasHref":false,"href":null},"腳本":{"hasHref":false,"href":null}}；點撥號與腳本之後網址不變＝true、預覽仍在＝true、window.__w7xss＝null
[w7-html] ③DEF-AC-013 儲存式（admin 開編輯頁）：window.__w7xss＝null；srcdoc 內腳本讀到的 sessionStorage 鍵名＝null（只讀鍵名，不讀值）
[w7-html] ④唯讀詳情頁：window.__w7xss＝null；頁面內 iframe 元素數＝0
[w7-html] ⑤b儲存式：編輯頁文件＝{"metaRefresh":0,"base":0}（預覽文字含 http-equiv＝true）；詳情頁文件＝{"metaRefresh":0,"base":0}
[w7-html] ⑥b儲存式：編輯頁預覽的連結＝{"官網":{"hasHref":true,"href":"https://example.com/w7"},"寄信":{"hasHref":true,"href":"mailto:qa@example.com"},"撥號":{"hasHref":false,"href":null},"腳本":{"hasHref":false,"href":null}}；詳情頁的連結＝{"官網":{"hasHref":true,"href":"https://example.com/w7"},"寄信":{"hasHref":true,"href":"mailto:qa@example.com"},"撥號":{"hasHref":false,"href":null},"腳本":{"hasHref":false,"href":null}}；window.__w7xss＝null
  8 passed (20.8s)
```

八個情境全部是 `✓`（不是 `test.fail` 的預期失敗）；`tel:` 兩處都是無 href 的文字，與主控裁決（D-21）一致。

**負向對照（修復前的前端建置，證明新情境鑑別得出缺陷）**：用 `git archive 520c2850 AgentConsole/frontend` 取出修復前的前端原始碼到暫存目錄（確認 `MarkdownEditorImpl.tsx` 沒有 `omitRawHtml`、沒有 `safeUrl.ts`），`node_modules` 從工作樹複製，以同樣的 `NEXT_PUBLIC_API_URL=http://localhost:18080 npm run build`（rc=0，31 秒，`logs\prefix_build.log`）建出 standalone，用 `node scripts/start-standalone.mjs` 在 3100 埠服務（後端 CORS 本來就放行 3100），**同一個 backend、同一個 Bridge、同一支 spec** 以 `run_pw.ps1 -Tag prefix -WebPort 3100` 跑（`logs\pw_prefix.log`，rc=1）：

| 情境 | 修復前的前端建置 | 修後（HEAD） |
|------|------------------|--------------|
| ① | 通過；但預覽建出真元素 `{"img":1,"script":1,"details":1}`，`anchorHref` 是 React 換上的 `javascript:throw new Error('React has blocked…')`，主控台錯誤 2 | 通過；建出元素全 0、`anchorHref＝null`、主控台錯誤 0 |
| ② | **失敗**：`window.__w7xss＝"iframe-srcdoc"`，srcdoc 內腳本讀到鍵名 `aisdlc.console.session` | 通過：`null` |
| ③ | **失敗**：`"iframe-srcdoc"`，鍵名 `aisdlc.console.lastProject,aisdlc.console.session` | 通過：`null` |
| ④ | 通過（詳情頁本來就不受影響） | 通過 |
| ⑤ | **失敗**：貼入後文件 `{"metaRefresh":1,"base":1}`、預覽文字不含 `http-equiv` | 通過：`{"metaRefresh":0,"base":0}`、文字含 `http-equiv` |
| ⑤b | **失敗**：編輯頁文件 `{"metaRefresh":1,"base":1}`（詳情頁 0） | 通過 |
| ⑥ | **失敗**：`撥號` 的 href 是 `tel:+886123456789`、`腳本` 的 href 是 React 換上的 `javascript:throw new Error(…)` | 通過：兩者皆無 href |
| ⑥b | **失敗**：編輯頁預覽同上；詳情頁的 `撥號`、`腳本` 是空字串 href（`href=""`，點下去會重新載入本頁） | 通過：兩處皆無 href |
| 摘要行 | `6 failed`／`2 passed (24.2s)` | `8 passed (20.8s)` |

同一個瀏覽器、同一個後端，只有前端建置不同：缺陷在修前真的存在、六個情境（②③⑤⑤b⑥⑥b）都抓得到、修後全部消失。暫存目錄的修復前建置在本節完成後已刪除（log 保留）。

### 13.5 Markdown 相關 spec 回歸

挑出所有會碰 Markdown 預覽或 `MarkdownView` 的既有 spec（Grep `w-md-editor-preview`、`markdown-view`、`MarkdownView`、`md-preview-region`、`md-criteria` 等：八個檔，扣掉 `p9-w7-html` 剩七個）各跑一次（`run_pw.ps1 -Tag md`，`logs\pw_md.log`、`logs\pw_md.rc.txt`＝`rc=0 elapsed_sec=810`；逐檔統計 `logs\pw_md.summary.txt`）：

| 檔案 | 情境數 | 通過 | 失敗 | 略過 |
|------|-------:|-----:|-----:|-----:|
| `markdown-editor.spec.ts`（編輯器八項功能） | 5 | 5 | 0 | 0 |
| `markdown-preview.mock.spec.ts`（FE 新增，production 建置） | 3 | 3 | 0 | 0 |
| `design-system.spec.ts` | 3 | 3 | 0 | 0 |
| `a11y.mock.spec.ts` | 3 | 3 | 0 | 0 |
| `p9-w5-a11y.spec.ts`（axe 掃 16 個頁面狀態） | 9 | 9 | 0 | 0 |
| `p9-w5-ui-evidence.spec.ts`（含 NFR-9.1-05） | 6 | 6 | 0 | 0 |
| `p9-w7-ui.spec.ts`（九畫面對設計稿） | 12 | 12 | 0 | 0 |
| **合計** | **41** | **41** | **0** | **0** |

尾端摘要行：`41 passed (13.5m)`。NFR-9.1-05 的 20KB 預覽更新（同 W5 量法，七次取中位數；上限 100ms），逐字：

```
[ui-evidence] NFR-9.1-05 1KB：樣本(ms)=27, 9, 9, 7, 6, 6, 8；中位數 8ms、最大 27ms
[ui-evidence] NFR-9.1-05 5KB：樣本(ms)=22, 23, 17, 17, 21, 17, 14；中位數 17ms、最大 23ms
[ui-evidence] NFR-9.1-05 20KB：樣本(ms)=58, 63, 54, 57, 54, 55, 53；中位數 55ms、最大 63ms
```

（整套裡同一支再量一次：20KB 中位數 58ms、最大 62ms；兩次都在閒置機上〔開跑前 CPU 讀數：逐檔批次 7%、整套 5%〕、都遠低於 100ms；FE 自己量的 61ms 與第一輪的 57～62ms 同一量級，`omitRawHtml` 沒有拖慢預覽。）

### 13.6 DEF-AC-014 複驗

**受控重現（本機真後端）**——沿用第一輪的作法（登入取 token → 找或造一個 PAUSED 批次 → `curl.exe -N` 接 `/logs` 與 `/metrics` → 收到資料後結束 curl → 看 backend 日誌 30 秒），腳本 `<SCRATCH>\w8_qa\repro_local.ps1`：登入 admin 取 token 寫進 curl 的標頭檔（不印出）；用等級 1 夾具建專案、`POST /api/v1/projects/{id}/execute`、等到 `PAUSED` 且審核項出現（PAUSED 不結束串流）；每輪同時開兩條串流、4 秒後確認兩個 curl 都還活著且 bytes>0，再同時 `Stop-Process -Force`；30 秒後讀「該輪開始之後」新寫入的 backend 日誌，統計 `ERROR` 層級行、`Failure in @ExceptionHandler`、`AsyncRequestNotUsableException` 提及次數、`WARN` 與 `GlobalExceptionHandler` 的 DEBUG 行。結束時再登入一次，確認那一行 `audit` 在 3 秒內出現在被監看的日誌裡（日誌監看是活的，「0 行」才有意義）。

```powershell
# 等價的最小形態（完整流程在腳本裡）：
$p1 = Start-Process curl.exe -ArgumentList '-N','-s','-H',"@$hdr","http://127.0.0.1:18080/api/v1/stream/executions/$run/logs" -RedirectStandardOutput $out1 -PassThru -WindowStyle Hidden
$p2 = Start-Process curl.exe -ArgumentList '-N','-s','-H',"@$hdr","http://127.0.0.1:18080/api/v1/stream/executions/$run/metrics" -RedirectStandardOutput $out2 -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 4; Stop-Process -Id $p1.Id,$p2.Id -Force
```

```bash
curl -N -s -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:18080/api/v1/stream/executions/$RUN/logs" > logs.out & P1=$!
curl -N -s -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:18080/api/v1/stream/executions/$RUN/metrics" > metrics.out & P2=$!
sleep 4; kill $P1 $P2   # bash 形態在這台 Windows 機器上沒有跑
```

| 回合 | backend 日誌等級 | 結果（逐字摘自 log） |
|------|------------------|----------------------|
| DEBUG 開（`logs\repro_debug.log`，PAUSED 批次 `4fd9d77e-c422-4082-9fab-6126666c790c`） | `GlobalExceptionHandler` 設為 DEBUG | 三輪皆 `streams were open and delivering = True`（`/logs` 7965 bytes、`/metrics` 約 676 bytes，首行 `retry:3000`）；每輪斷線後 30 秒：`level=ERROR lines=0; 'Failure in @ExceptionHandler' lines=0; AsyncRequestNotUsableException mentions=0; level=WARN lines=0; DEBUG GlobalExceptionHandler lines=2`；合計 `ERROR=0; Failure-in-ExceptionHandler=0; WARN=0; DEBUG GlobalExceptionHandler=6`；`log liveness probe … audit lines seen … = 1`；`run state after: PAUSED` |
| 預設（INFO，`logs\repro_info.log`，重啟 backend 後再用同一個 PAUSED 批次） | 預設 | 三輪皆兩條串流開著且收到資料；每輪斷線後 30 秒新寫入的日誌行數 0：`ERROR=0; Failure-in-ExceptionHandler=0; AsyncRequestNotUsableException mentions=0; WARN=0; DEBUG GlobalExceptionHandler=0`；`log liveness probe … = 1`；`run state after: PAUSED`；整份日誌 `ERROR` 0 行 |

DEBUG 開時的處理器日誌（`logs\repro_debug.log` 的第一輪，逐字；`traceId` 取自回應標頭、路徑不含 `access_token`）：

```
2026-10-17T11:18:31.180+08:00 DEBUG [traceId=] 40384 --- [console] [http-nio-18080-exec-9] c.a.c.a.in.web.GlobalExceptionHandler    : 客戶端已斷線，串流視為正常結束（run=4fd9d77e-c422-4082-9fab-6126666c790c，traceId=9e3c3fef-1c9b-415c-8ab1-6b174a2eadaa，path=/api/v1/stream/executions/4fd9d77e-c422-4082-9fab-6126666c790c/logs）：IOException: Connection reset by peer
2026-10-17T11:18:33.176+08:00 DEBUG [traceId=] 40384 --- [console] [http-nio-18080-exec-7] c.a.c.a.in.web.GlobalExceptionHandler    : 客戶端已斷線，串流視為正常結束（run=4fd9d77e-c422-4082-9fab-6126666c790c，traceId=e6f2abda-04b5-4686-864d-bb766b8e4a79，path=/api/v1/stream/executions/4fd9d77e-c422-4082-9fab-6126666c790c/metrics）：IOException: Connection reset by peer
```

**整套 Playwright 跑完後的 backend 日誌統計**（本機整套用 DEBUG 開著跑，才數得出自然斷線的次數；統計腳本 `<SCRATCH>\w8_qa\log_stats.py`，輸出 `logs\suite_log_stats.txt`；**同一支解析器先對第一輪修前的整套日誌重算作校準**，算出 13／13／13，確認這個判準看得到缺陷）：

| 日誌 | `ERROR` 層級行 | `Failure in @ExceptionHandler` | `AsyncRequestNotUsableException` 提及 | `GlobalExceptionHandler` 的 DEBUG 行 |
|------|---------------:|-------------------------------:|--------------------------------------:|-------------------------------------:|
| 第一輪整套（修前、213 個情境，`backend_r010652.log` 重算） | 13 | 13 | 13 | 0 |
| W8 整套（修後、225 個情境，兩個 backend 行程的 Spring UTF-8 日誌） | **0** | **0** | **0** | 13 |
| 同兩個行程的 stdout 擷取（交叉比對） | 0 | 0 | 0 | 13 |

W8 整套的 WARN 共 35 筆，全部與 SSE 無關（SDD 狀態檔讀不動／引擎不可用的情境 26 筆、PDF 字型 `Format 14 cmap` 4 筆、SpringDoc 預設啟用 4 筆、Bridge 暫時無法連線 1 筆）。兩次整套的情境數不同（213／225），自然斷線次數同為 13 次只是同一批開串流的情境造成，不作驗收判準；判準是 ERROR 與 `Failure in @ExceptionHandler` 為 0，以及斷線確實發生過（13 行 DEBUG）。

**Docker 全棧經 nginx（加分項）**：`up -d --build --wait` rc=0、67 秒（`logs\stack_up2.log`／`stack_up2.rc.txt`），14 個長駐服務皆 `healthy`、兩個一次性 job `Exited (0)`；後端映像 `aisdlc-backend:dev` 的 `COPY src src`、`RUN ./gradlew bootJar`、`COPY --from=builder … app.jar` 三層都命中快取（映像 `Created` 為 2026-10-16T20:40:55Z、ID `989de5b18bc0`；容器內 jar 的 SHA-256 見 13.2）。`<SCRATCH>\w8_qa\sse_disconnect_repro2.ps1 -Rounds 3 -WaitSec 40`（沿用第一輪 Docker 重現的做法，目標是資料庫裡殘留的 PAUSED 批次 `1a28bd6f-14ca-4afb-955e-e66ce2981725`），`logs\sse_repro2.log` 逐字：

```
round 1 [logs] after 4s: bytes=87052 curl alive=True
round 1 [metrics] after 4s: bytes=685 curl alive=True
round 1: 40s after the disconnect: level=ERROR lines=0; 'Failure in @ExceptionHandler' lines=0; AsyncRequestNotUsableException lines=0; level=WARN lines (any)=0; total backend log lines since t0=0
（第 2、3 輪同形：兩條串流都開著、收到 87052／685 bytes，斷線後 40 秒 ERROR 0、Failure 0、Async 0、WARN 0）
TOTAL over 3 rounds x 2 streams: ERROR=0; Failure-in-ExceptionHandler=0; AsyncRequestNotUsableException=0; WARN(any)=0
backend health: healthy; cumulative ERROR lines in the whole container log: 0
```

對照第一輪修前同一個做法（`/logs` 4 秒後 87052 bytes、`/metrics` 684 bytes，結束 curl 後 30 秒內各 1 筆 `"level":"ERROR"` 與 1 筆 `Failure in @ExceptionHandler`）：同一個批次、同樣的資料量，ERROR 與 WARN 都從 1 變 0。日誌監看是活的：另外經 nginx 登入一次，`docker logs --since` 在 3 秒內看到 1 行 `audit` 的 `/api/v1/auth/login`。Docker 容器的日誌等級是預設 INFO，所以處理器一行都不記（「total backend log lines since t0=0」）。

### 13.7 本機整套回歸（225 個）

`run_pw.ps1 -Tag full`（環境：重置後的乾淨資料庫、DEBUG 開、`--list` 現查 225 個情境、34 個檔）：`logs\pw_full.rc.txt`＝`rc=0 elapsed_sec=4089 start=2026-10-17T10:08:07+08:00 end=2026-10-17T11:16:17+08:00`；Playwright 尾端摘要行（逐字）與逐檔統計（`logs\pw_full.summary.txt`，測試本體耗時加總 65.2 分，不含 hooks）如下：

```
  225 passed (1.1h)
```

| 檔案 | 情境 | 通過 | 失敗 | 略過 | 分 |
|------|-----:|-----:|-----:|-----:|---:|
| `a11y.mock.spec.ts` | 3 | 3 | 0 | 0 | 0.1 |
| `chart.spec.ts` | 1 | 1 | 0 | 0 | 0.0 |
| `crud-flow.spec.ts` | 1 | 1 | 0 | 0 | 0.1 |
| `dashboard.mock.spec.ts` | 8 | 8 | 0 | 0 | 0.1 |
| `design-system.spec.ts` | 3 | 3 | 0 | 0 | 0.0 |
| `execute.mock.spec.ts` | 21 | 21 | 0 | 0 | 0.7 |
| `import.mock.spec.ts` | 8 | 8 | 0 | 0 | 0.2 |
| `markdown-editor.spec.ts` | 5 | 5 | 0 | 0 | 0.1 |
| `markdown-preview.mock.spec.ts` | 3 | 3 | 0 | 0 | 0.1 |
| `monitor.mock.spec.ts` | 15 | 15 | 0 | 0 | 0.3 |
| `notifications.mock.spec.ts` | 3 | 3 | 0 | 0 | 0.0 |
| `p3-import.spec.ts` | 8 | 8 | 0 | 0 | 3.3 |
| `p4-execute.spec.ts` | 12 | 12 | 0 | 0 | 11.6 |
| `p4b-execute-more.spec.ts` | 9 | 9 | 0 | 0 | 8.5 |
| `p5-monitor.spec.ts` | 4 | 4 | 0 | 0 | 1.2 |
| `p6-settings.spec.ts` | 8 | 8 | 0 | 0 | 1.2 |
| `p7-cors-ratelimit.spec.ts` | 1 | 1 | 0 | 0 | 2.1 |
| `p9-w5-a11y.spec.ts` | 9 | 9 | 0 | 0 | 2.3 |
| `p9-w5-api.spec.ts` | 10 | 10 | 0 | 0 | 5.0 |
| `p9-w5-bridge.spec.ts` | 2 | 2 | 0 | 0 | 0.0 |
| `p9-w5-ui-evidence.spec.ts` | 6 | 6 | 0 | 0 | 6.0 |
| `p9-w5-ui.spec.ts` | 6 | 6 | 0 | 0 | 5.5 |
| `p9-w7-engine.spec.ts` | 8 | 8 | 0 | 0 | 1.8 |
| `p9-w7-html.spec.ts` | 8 | 8 | 0 | 0 | 1.4 |
| `p9-w7-purefile.spec.ts` | 1 | 1 | 0 | 0 | 0.2 |
| `p9-w7-resources.spec.ts` | 3 | 3 | 0 | 0 | 3.7 |
| `p9-w7-sdd.spec.ts` | 13 | 13 | 0 | 0 | 3.7 |
| `p9-w7-signoffs.spec.ts` | 9 | 9 | 0 | 0 | 2.4 |
| `p9-w7-ui.spec.ts` | 12 | 12 | 0 | 0 | 3.2 |
| `projects.mock.spec.ts` | 3 | 3 | 0 | 0 | 0.0 |
| `settings.mock.spec.ts` | 10 | 10 | 0 | 0 | 0.2 |
| `shells-and-layout.spec.ts` | 6 | 6 | 0 | 0 | 0.1 |
| `signoff.spec.ts` | 5 | 5 | 0 | 0 | 0.1 |
| `task-retry.spec.ts` | 1 | 1 | 0 | 0 | 0.0 |
| **合計（34 個檔）** | **225** | **225** | **0** | **0** | **65.2** |

與第一輪（213 個、31 個檔）的差別：多出的 12 個＝`markdown-preview.mock.spec.ts` 3 個、`p9-w7-purefile.spec.ts` 1 個、`p9-w7-html.spec.ts` 由 4 個變 8 個（第一輪這兩支在整套之後才單獨跑，本輪放進整套）。整套與逐檔跑法都用同一個最終版 `p9-w7-html.spec.ts`（檔案 SHA-256 `B130B1DC…D600`，mtime 在所有跑次之前，跑完沒有再改）。

### 13.8 Docker 全棧情境（32 個）

`run_pw_docker.ps1 -Tag docker2`（`docker.config.ts`，經 nginx 同源）：`logs\pw_docker2.rc.txt`＝`rc=0 elapsed_sec=782`；尾端摘要行 `32 passed (13.0m)`；逐檔：`chart.spec.ts` 1、`crud-flow.spec.ts` 1、`design-system.spec.ts` 3、`p8-docker-stack.stack.ts` 11、`p9-w7-docker.stack.ts` 5、`shells-and-layout.spec.ts` 6、`signoff.spec.ts` 5，全數通過（含「SSE 經 nginx（`proxy_buffering off`）」與「重啟 backend → 前端串流重連、session 不得被清除」）。跑完對 backend 容器（`docker logs aisdlc-backend`，`logs\docker_backend_full.log`）統計：313 行，`INFO` 307、`WARN` 6、`ERROR` 0；`Failure in @ExceptionHandler` 0、`AsyncRequestNotUsableException` 0；6 筆 WARN 是 SpringDoc 預設啟用 4 筆（兩次啟動各 2 筆）與 E2E-16 列 10 的 Redis 降級情境依設計產生的 2 筆。容器 `RestartCount＝0`、`OOMKilled＝false`（容器 `StartedAt` 晚於 `up` 七分鐘，是 `p8-docker-stack` 的「重啟 backend」情境主動重啟，不是自動重啟）。第一輪 Docker 整套曾自然留下 1 組 ERROR＋WARN（`/executions/{id}/cancel` 同一秒），這次 0 組。

### 13.9 上一位 QA 第二輪的殘留與失敗診斷

我接手時，工作樹的 `p9-w7-html.spec.ts` 是半改狀態（加了 ⑤⑥⑤b⑥b，兩行 `test.fail` 還在、兩行 `console.log` 沒過 Prettier），上一位 QA 的暫存目錄裡有它最後一次跑的 log（`pw_html_old.log`）：**4 通過、4 失敗**——失敗的四個都是需要「已儲存專案」的情境（③④⑤b⑥b），畫面顯示「無法載入專案：Not Found」。我沒有採信那份結果，也沒有把它當缺陷：

1. 該次跑的 Playwright trace（`pw_out\html_old\…\trace.zip` 的 `*.network`）顯示頁面對 API 的請求打到 `http://localhost:3000/api/v1/projects` 與 `…/notifications/summary`，三次都是 **404**（同源的 Next.js），而 e2e 後端在 18080；只有 spec 的 `request` fixture（直接打 18080）成功。也就是說那次的前端 `.next` 建置**沒有內嵌** `NEXT_PUBLIC_API_URL=http://localhost:18080`。
2. 需要後端資料的情境（③④⑤b⑥b）因此全部 404；只靠「新建專案對話框」的情境（①②⑤⑥）不需要 API 資料，所以照常通過（②「預期失敗卻通過」正是修法已在那份建置裡）。
3. 我以 `NEXT_PUBLIC_API_URL=http://localhost:18080 npm run build` 重建（13.3、13.2 的 JS 掃描確認內嵌）後，同樣八個情境全部通過（13.4）。
4. **根因屬待驗假設**（鐵律 10）：我沒有看到是誰、在什麼時候用不帶 API 位址的指令重建了 `.next`（時序上吻合主控自己跑 `npm run build` 閘門）；我能確認的是 trace 的 404 證據與重建後的結果。**給主控的提醒**：任何不帶 `NEXT_PUBLIC_API_URL` 的 `npm run build` 都會覆蓋 `frontend/.next`；之後再跑真後端 Playwright（`E2E_MODE=standalone`）前一定要用 18080 重建一次（`tests/e2e/README.md`〈真 Bridge specs〉第 5 點已寫，但這個失敗形態容易被誤讀成產品缺陷）。我留下的 `.next` 是內嵌 18080 的版本，要回到一般本機開發請重建。

### 13.10 未覆蓋與保留的口徑

1. **瀏覽器 `EventSource` 的各種斷線形態沒有逐一驗**（網路中斷、電腦睡眠、nginx 逾時切斷）：本輪驗的是 curl 被結束（用戶端主動結束）與整套 Playwright 自然發生的 13 次斷線（關頁面、`EventSource.close()`）；另沒有量「執行中批次」與「終態後」兩種狀態下斷線的差異（受控重現只用 PAUSED 批次，整套的自然斷線涵蓋各種狀態）。
2. **其他 Markdown 編輯器沒有逐一在瀏覽器驗**：目標、任務、匯入節點的編輯頁沒有各自貼 payload；依據是 13.2 的靜態檢查（全站只有一個編輯器元件、一個唯讀檢視元件、沒有 `dangerouslySetInnerHTML`），加上 FE 的單元測試與 mock spec 的 12 種以上載體。瀏覽器端我只驗了新建專案對話框與已儲存專案的編輯頁／詳情頁；沒有新增第七個「更多載體」情境，因為 `markdown-preview.mock.spec.ts` 已在 production 建置下涵蓋 `iframe srcdoc`、`script`、`img onerror`、`javascript:`、`meta`、`base`、`object`、`svg onload`、`details ontoggle`，再加只會重複。
3. **預設等級（INFO）下處理器完全不記，DEBUG 下每次斷線一行**：前者在 13.6 受控重現與 Docker 驗過，後者在 DEBUG 受控重現與整套驗過；DEBUG 的開關是 `logging.level.com.aisdlc.console.adapter.in.web.GlobalExceptionHandler`（我用啟動參數開）。
4. **Docker 全棧沒有跑 `p9-w7-html.spec.ts`**：它需要 `e2e` profile（allow-loopback）與可寫入的專案路徑，Docker 全棧沒有；Docker 裡的前端映像已含 FE 修法，被 `design-system.spec.ts`（Markdown 編輯器 box-shadow 掃描）與 `crud-flow.spec.ts` 觸及編輯器，但沒有逐項驗 XSS 載體。
5. **後端 `gradlew clean build` 沒有重跑**（任務書：不需要）；後端單元與整合測試的結果以主控的回報為準（他包回報，不當我的證據），我的證據是行為（受控重現、整套日誌）與 jar 位元組來源（13.2）。
6. **`tel:` 取捨**：依主控裁決（D-21）驗證成「無 href 的文字」；若日後 PRD 要 `tel:` 可點，要同步改 `safeUrl.ts` 與 ⑥／⑥b。
7. 沒有在 macOS／Linux 主機跑；本節 bash 形態的指令沒有在這台 Windows 機器上實跑。

### 13.11 DEF-AC-012 與缺陷表結論

DEF-AC-012（P4，Bridge 與 SSOT 對 SDD LATEST 的判定在未入庫目錄時分歧）依 D-21 **維持 P4 保留**：本輪不修、也沒有重驗。DEF-AC-013、DEF-AC-014 狀態改為已修並複驗通過（§10.1 兩列已更新、§12.2 第 1～2 項標結案）。本輪沒有新增缺陷。

### 13.12 收尾與要 commit 的檔案

- **環境收尾**（逐項現查，結果見交卷訊息）：Docker 全棧只做 `down`（不帶 `-v`；12 個 `aisdlc_*` 卷保留，`autoclaude_pg` 全程沒動）；本機 backend、Bridge、前端與 `qa-pg` 都已停止並移除；修復前建置的暫存目錄已刪除；Playwright 改寫的已追蹤截圖（本輪四次還原：17、123、21、0 張，共 161 張）都用 `git show HEAD:<path>` 的位元組寫回（`restore_screens.py`，不用 `git restore`／`checkout`），最後一次還原後 `git diff` 的截圖差異為 0 張。
- **要 commit 的檔案**（皆在我的持有面）：`AgentConsole/frontend/tests/e2e/p9-w7-html.spec.ts`、`AgentConsole/frontend/tests/e2e/README.md`（第 115、156 行）、`AgentConsole/docs/06_quality/RTM.md`（只有 3 列的 E2E 欄，`git diff --stat` 3 行新增 3 行刪除）、`AgentConsole/docs/06_quality/QA_W7_Closure.md`（版本列、§1 的 W8 提示、§10.1 兩列、§12.2 第 1～2 項、本節）。

## 14. 整合輪 115 的缺陷編號去處（指路）

整合輪 115（SDD 迴圈）的 W4 dogfood 與 W5 獨立稽核另立證據檔，缺陷編號沿用本檔的 DEF-AC 序列、不重起：

- DEF-AC-015～DEF-AC-027（共 13 筆：P3 五筆、P4 八筆，沒有 P2 以上）由 W4 dogfood 登記，內容在根層 [AutoSDD_ZeroTrust_Audit_115.md](../../../docs/06_quality/AutoSDD_ZeroTrust_Audit_115.md) §1.9。
- W5 獨立稽核的缺陷自 DEF-AC-028 起，內容在同一檔 §4（歸屬根層帳本者，由該檔標明請主控入帳）。
- 本檔 §10.1、§12.2 的缺陷表停在 DEF-AC-014，不回頭改寫；DEF-AC-012 維持 P4 保留，與整合輪 115 無關。
