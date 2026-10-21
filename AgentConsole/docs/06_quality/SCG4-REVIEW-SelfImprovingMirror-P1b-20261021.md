# SCG-4 PR Review 報告 — SelfImproving 唯讀鏡像 P1b（PRD FR-SI-32；鍵 `agentconsole-si-mirror`）

**審查日期**: 2026-10-22　**審查者**: SCG-4 獨立 QA（Sonnet，唯讀；未參與規格撰寫與實作——規格作者＝SA 棒（三審 PASS 後凍結）、實作者＝互動 Sonnet Developer，三方不同）　**主控親驗**: 2026-10-21 `verify_p1b.ps1` 九閘（Fable 5.1）
**審查範圍**: `AgentConsole/**` 共 76 檔（修改 23、新增 53；Bridge `app/si_cli.py`、`app/routers/si.py`、`app/settings.py`；backend `SiController`、`SiMirrorQueryService`、`SiBridgeErrors`、`SiExportResponse`、`SiKeyNames`、`BridgeHttpAdapter.siExport`、`ErrorReasons`；frontend `app/self-improving/page.tsx`、`components/domain/si/*`、`lib/domain/si.ts`、`lib/nav/registry.ts`、`ToolsRegion.tsx`、`NodeEditDialog.tsx`、`schema.d.ts` 重產；`docker-compose.yml`）＋主控代改 `.github/workflows/agentconsole-ci.yml` paths 五行（D11）＋契約後繼檔 `docs/02_architecture/API_Contract_SelfImproving_P1b.md`
**基準規格**: `AgentConsole/docs/03_testing/contracts/TCS-SelfImprovingMirror-P1b-20261021.md`（Stage-2 凍結 `sha256:a95b783d…52e20`；AC 14／AT 73；R1～R29）　**上位**: 根層 `docs/01_requirements/SelfImproving_PRD.md` v0.10 FR-SI-32、Architecture §5.2／§5.4／§10／§11.1／§12
**判決檔（逐項證據）**: 主控 scratchpad `si_p2\qa_p1b_scg4_verdict.md`（本檔為其入庫摘要；數字皆為審查者或主控當回合親跑）

### A. FRD 功能規格一致性（AC 14／14）

| AC-ID | 驗收標準（摘要） | 實作座標 | 測試（AT 數） | 結論 |
|-------|------------------|----------|--------------|------|
| AC-932-1 | 頁面與回應逐欄等於同一時刻 `si export`；卡面逐位元組；不重算、純文字渲染 | `si_cli.py`／`routers/si.py`；`SiExportResponse`／`SiKeyNames`；`SiView` 四面板 | 16（Bridge 差分 4、backend 黃金檔 4、frontend 8） | Pass |
| AC-932-2 | 零寫入：無非 GET、argv 只有 `export`、AST 鎖、ArchUnit 鎖、前端無 Bridge 路徑字面 | `si_cli.py`（唯一子行程通道）、`SiController`（無寫入對映）、`SiReadOnlyArchTest` | 9 | Pass |
| AC-932-3 | 不可用時 503 `si_unavailable`（九種 cause、`detail` 帶 rc 與 stderr 尾段）、502／504 沿既有、前端只顯示錯誤不渲染空表或舊資料、量不到顯示 NE | `si_cli.py` 九種 cause、`SiBridgeErrors`、`siParts.tsx`／`lib/domain/si.ts` | 13 | Pass（P3-1：`touched` 為 null 顯示「無」，修復棒二已改為 NE 顯示並補測） |
| AC-932-4 | 需登入（401 不觸 Bridge）、Viewer 以上可讀、未登入導向登入、Bridge 無 `ports` | `SecurityConfig` 零改動、`docker-compose.yml`、`si-login-gate.test.tsx` | 5 | Pass |
| AC-932-6 | 導覽入口單一來源＝登記表；加一列即多一入口；`order`／`roles`／`mobile`／`match`；未知路徑不 fallback | `lib/nav/registry.ts`、`ToolsRegion.tsx`、`layout.test.tsx` 改登記表驅動 | 11 | Pass |
| AC-940-1 | `SI_ROOT` 解析、拒檔案系統根、不併入 `allowed_path_roots` | `settings.py` | 2 | Pass（⚖-B 字面改釘意圖，列 TCS 勘誤） |
| AC-940-2 | argv 固定不帶 `--repo`／`-I`／`-P`；環境白名單；機密不洩入 | `si_cli.py` | 2 | Pass |
| AC-940-3 | compose 設計 A 六條唯讀 bind、`SI_ROOT=/repo`、無 `ports` | `docker-compose.yml` | 2 | Pass（設計 B 空檔未建，⚖-D） |
| AC-940-4 | 差分測試的根層輸入皆在 `agentconsole-ci.yml` 兩處 `paths` | `.github/workflows/agentconsole-ci.yml`（D11 主控補） | 2 | Pass（AT-940-4-1 於 D11 後轉綠） |
| AC-940-5 | reason 常數落點：前端 `lib/domain/si.ts`、不進 `REASONS`；後端 `ErrorReasons` 兩常數 | `ErrorReasons.java`、`lib/domain/si.ts` | 2 | Pass |
| AC-940-6 | 匯入頁執行路徑欄重用 `EXECUTION_PATH_HINT`、`aria-describedby` | `NodeEditDialog.tsx` | 2 | Pass |
| AC-940-7 | 差分夾具以真 CLI 閉包建狀態 A／B、反空轉前提 | `tests/si_repo_support.py`、`tests/fixtures/si_repo/**` | 2 | Pass |
| AC-940-8 | `/v3/api-docs` 六路徑各只有 `get`、`schema.d.ts` 重產入庫、`siBase()` 同 `sddBase()` | `OpenApiIT`（61→67／70→76）、`schema.d.ts`、`BridgeEndpoints.siBase` | 3 | Pass（`schema.d.ts` 位元組級重產一致；非 live bootRun，⚖-I） |
| AC-940-9 | 只收 `since`／`limit`／合格 `{id}`，其餘 422；404 與 503 語意分離；不合規輸入不啟動子行程 | `routers/si.py` | 2 | Pass |

### B. Contract 一致性（`API_Contract_SelfImproving_P1b.md`；後繼 P3-6 契約）
六路徑、兩個 reason 字串（Java `ErrorReasons`、TS `SI_REASONS`、契約 §0.4、Architecture §11.1 逐字相同）、§2.3 九種 cause 與 `si_cli.py` 一致、§3 對映表與 `BridgeHttpAdapter.handle`／`SiBridgeErrors` 一致、`SiKeyNames.camel` 規則與契約 §0.2 一致；`si_not_found` 為「404 reason 省略」慣例的第二個例外（P3-6 凍結檔字樣不改，OBS-SI-260 登記）。`schema.d.ts` 由審查者在 scratchpad 複本傾印 `/v3/api-docs`（67 路徑、76 操作）並以 repo 的 openapi-typescript 重產，與 repo 檔 sha256 完全相同——無手改；diff 大是 HEAD 版只有 13 個路徑鍵。

### C. Business Invariants（零寫入與安全不變量）
`si_cli.py` argv 只有 `export`、無 `--repo`；環境白名單加固定鍵；stdin `DEVNULL`；stdout 8 MiB 上限；逾時以 psutil 殺整棵行程樹；`SecurityConfig` 零改動；前端無 Bridge 路徑字面、無 `dangerouslySetInnerHTML`（`si.static.test.ts` 掃描器有負控）；engine-bridge 無 `ports`、SI 六條 bind 唯讀。

### D. RTM 覆蓋率確認
AC 14／14、AT 73／73 皆可定位且全部真跑（`RTM.md` §2.2 子表 95 列）；US→AC 對映與 TCS FRD-lite 表逐列一致。

### E. 審查證據（當回合親跑；rc 先存變數）
| 項目 | 結果 |
|------|------|
| Bridge SI 五檔（cwd `engine-bridge`） | rc 0，0 略過（27 個 AT）；主控九閘的 Bridge 全套 rc 0（唯一預期紅 AT-940-4-1 已於補 D11 後轉綠） |
| backend（`gradlew test --tests "*Si*"`；主控 `clean build`） | Si 測試 0 failures（13 個 AT）；主控 `BUILD SUCCESSFUL in 2m 31s`；JaCoCo／ArchUnit 在 build 內 |
| frontend（12 檔 vitest；主控 lint／tsc／build／全套） | 261 通過（33 個 AT）；主控四閘 rc 0 |
| ruff 兩視角；CI paths 鎖 `test_ci_paths_cover_root_consumers` | All checks passed；49 通過 |
| 突變檢驗（scratchpad 複本，repo 零改動） | Bridge M1（argv 加 `--repo`）、backend B4（加 `PostMapping`）、frontend M8（錯誤時渲染舊資料）、backend retry（`siExport` 加重試）皆轉紅；Developer 自報 Bridge 4／backend 4／frontend 11 一致 |
| 文件規則 | 77 檔 0 個 CR；無「測試摘要字樣＋4 位數字」命中；無機密；OBS-SI 編號全在真帳本；NTFS 大小寫碰撞 0 |
| 根層對照 | `TestDirEntryPrimitivesAreAccountedFor` 紅 43≠37：AgentConsole 貢獻 0 筆，超額在 P2 棒 `tools/lib/selfimproving/**`（另案收尾） |

### 審查結論

| 項目 | 狀態 |
|------|------|
| FRD 功能規格 | Pass（0 項不符；P3 三筆不阻擋） |
| Contract 一致性 | Pass |
| Invariants 保護 | Pass |
| RTM 覆蓋率 | 100%（AC 14／14、AT 73／73） |
| 測試強度（突變） | Pass（審查者複核 4／4 被殺；Developer 19 個自報皆先紅後還原） |

**SCG-4 建議**: [通過]（範圍＝Windows 單機；V1～V10 與 Playwright mock 閘見〈未驗〉）

### 必修項目
無（P≤2 為零）。**P3（已處置）**：P3-1 `touched`／`touchedCount` 為 null 時前端顯示「無」（R16 精神）——修復棒二改為 NE 顯示並補 vitest；根層 `export` 側缺 `ne` 項另登 OBS。**P3（待驗）**：P3-2 Playwright route-mock 閘（CI `agentconsole-ci.yml` 的 `npx playwright test mock.spec`）由主控以 repo 外 `--output` 跑一次；P3-3 差分測試吃工作樹上的活 CLI，P2 棒落地後須重跑 `test_si_export_differential.py`。**P4**（文字／資訊，見判決檔）：Java 註解補「§1.7」字樣（修復棒二）；契約 §1.5 `StrictHttpFirewall` 400 無 AT；`schema.d.ts` 無路徑集合對拍鎖（OBS）；Bridge 無並行子行程上限；凍結檔「唯一例外」殘留三處（OBS-SI-260）；⚖-H `PageTitle` h2 債（OBS-SI-259）。

### 未驗（如實列）
V1～V10（真後端全棧差分、真瀏覽器 DOM、真容器掛載設計 A／B、冷啟動量測、掌舵者真機）、真 bootRun 版 `/v3/api-docs`、Linux／macOS 與 POSIX 行程樹終止、`safe.directory` 環境變數式放行與單檔 bind inode（V3／V9／雲端 CI）。
