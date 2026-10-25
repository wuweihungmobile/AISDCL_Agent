# SCG-4 PR Review 報告 — SelfImproving 寫入載體 P2b（PRD FR-SI-33／35 的 Console 半；鍵 `agentconsole-si-decide`）

**審查日期**: 2026-10-25　**審查者**: SCG-4 獨立 QA（Sonnet，唯讀；未參與規格撰寫與實作——規格作者＝SA 棒（二審 PASS 後凍結）、實作者＝互動 Sonnet Developer，三方不同）　**主控親驗**: 2026-10-25 06:2x～06:4x（Fable 5.1；Bridge ruff／pytest 全套、backend `clean build`、frontend lint／tsc／vitest／build、根層 `TestDirEntryPrimitivesAreAccountedFor`、`si check`）
**審查範圍**: `AgentConsole/**` 共 117 檔（新增 63、修改 54；QA 以 `git ls-files -m -o --exclude-standard` 計）＋黃金檔三處副本 10 檔（主控依根層 P3 重產）＋主控代改 `.github/workflows/agentconsole-ci.yml` paths 兩處各兩行（D10）＋契約後繼檔 `docs/02_architecture/API_Contract_SelfImproving_P2b.md`。Bridge `app/si_audit.py`（新）、`app/routers/si.py`、`app/security.py`、`app/settings.py`、`app/si_cli.py`；backend `SiController`、`SiConsoleWriteService`、`SiWriteGates`、`SiAuditSigner`、`SiAuditJson`、`SiReconcileService`、`SiConsoleWriteAdapter`、`SiWriteProperties`、`BridgeHttpAdapter`、`UpstreamException`、`SiBridgeErrors`、`ErrorReasons`、`SecurityConfig`、Flyway `V13__si_console_writes.sql`、DTO 與 `domain/model/si` 記錄；frontend `SiDecideDialog`、`SiObsForm`、`SiObsCloseDialog`、`SiWritesPanel`、`SiView`、`lib/domain/si.ts`、`lib/api/*`、`schema.d.ts` 重產；`docker-compose.yml`、`.env.example`。
**基準規格**: `AgentConsole/docs/03_testing/contracts/TCS-SelfImprovingDecide-P2b-20261024.md`（Stage-2 凍結 `sha256:8f591aed…239d`；AC 18／AT 98＝正 49＋負 49；W1～W25；D1～D11）　**上位**: 根層 `docs/01_requirements/SelfImproving_PRD.md` v0.10 FR-SI-33、FR-SI-35、§9.1 C18／C21、§9.3；根層 `tools/lib/selfimproving/consoleaudit.py`（位元組契約權威）；Architecture §10.2／§10.3、§11.1、§12.1 L-14
**判決檔（逐字）**: 審查者交卷全文在本 session 子代理逐字稿（主控 scratchpad `tasks\a14c743f20bc49b1a.output`；分析工具在 `scratchpad\si_p3\qa_p2b_scg4\`）；本檔為其入庫摘要，數字皆為審查者或主控當回合親跑。

### A. FRD 功能規格一致性（AC 18／18；AT 98／98）

審查者自寫腳本重跑映射：TCS §1 解出 98 列、18 個 AC；分層 Bridge 32（正 16／負 16）、backend 41（19／22）、frontend 25（14／11）；98 個 AT 在對應層的執行結果檔（Bridge junitxml、Gradle XML、vitest json）都找到至少一個已執行且通過的案例，零命中 0、跨層命中 0、無 skipped。

| AC-ID | 驗收標準（摘要） | 實作座標 | 測試（AT 正／負） | 結論 |
|-------|------------------|----------|------------------|------|
| AC-933-1 | 九動詞、綁卡面 digest、預設拒絕、簽章落檔、真 CLI 收 | `si_audit.py`、`routers/si.py`；`SiConsoleWriteService`、`SiAuditSigner`、`SiAuditJson`、`SiWriteGates.decide`；`SiDecideDialog`、`lib/domain/si.ts`（`decideVerbOptions`、`validateDecideForm`） | 6／4 | Pass |
| AC-933-2 | 同型稽核列、列先於 Bridge、對帳 | `SiConsoleWriteService.write`、V13 表、`SiReconcileService` | 1／1 | Pass |
| AC-935-1 | 新增觀察：表單、先預檢、位元組估計 | `SiObsForm`、`estimateRowBytes`、`SiWriteGates.observation`、Bridge `run_validate` | 4／4 | Pass |
| AC-935-2 | 更正與七個終值關閉 | `SiObsCloseDialog`、`validateCloseForm`、`SiWriteGates.close` | 4／3 | Pass |
| AC-935-3 | 無刪除能力 | `SiController` 無 PUT／PATCH／DELETE、`SiReadOnlyArchTest`、前端無刪除控件、Bridge 405 | 2／2 | Pass |
| AC-935-4 | ADMIN 且在名單內才能寫 | `SecurityConfig`（`POST /api/v1/si/**` 要 ADMIN，置於通用規則前）、`authorize`、`SiWriteProperties`、`SiView` 的 `isAdmin` | 2／3 | Pass |
| AC-935-5 | 對帳、待入帳、紅色警示、回填 | `SiReconcileService`、`SiConsoleWriteAdapter`、`SiWritesPanel`、`pendingWrites` | 3／4 | Pass（P4-4、P4-6 為 UX） |
| AC-950-1 | Bridge 設定與落檔 | `settings.py`、`si_audit.py`、README | 3／3 | Pass（P3-1：`os.fsync` 無 AT 守，修復棒補 spy） |
| AC-950-2 | 三個寫入端點 | `routers/si.py`、`security.require_si_write_token` | 3／4 | Pass |
| AC-950-3 | 唯讀預檢 | `si_cli.run_validate`、`build_validate_argv`、`_parse_validate` | 3／2 | Pass |
| AC-950-4 | 稽核 JSON 契約與向量 | `SiAuditSigner`、`SiAuditJson`、黃金檔雙副本 | 3／3 | Pass |
| AC-950-5 | backend 設定與金鑰 | `SiWriteProperties`、`BridgeProperties`、`SiAuditKeyRing` | 1／2 | Pass |
| AC-950-6 | 寫入用例與補償 | `BridgeHttpAdapter`（`siWrite*`、`handle`、`translate`）、`UpstreamException`、`SiBridgeErrors.mapWrite`、`SiConsoleWriteService`（`settle`、`outcomeUnknown`、`compensate`） | 3／3 | Pass |
| AC-950-7 | 輸入閘 | `SiWriteGates` | 2／3 | Pass |
| AC-950-8 | V13 與列不可改 | `V13__si_console_writes.sql`、`SiConsoleWriteAdapter`、`SiReadOnlyArchTest` | 2／2 | Pass |
| AC-950-9 | frontend API 與純函式 | `endpoints.ts`、`queries.ts`、`types.ts`、`lib/domain/si.ts`、`si.static.test.ts` | 3／3 | Pass |
| AC-950-10 | 契約面與釘選同步 | `OpenApiIT`（71／81）、`schema.d.ts`、`registry.test.ts` | 2／1 | Pass（P4-2：一條標題含第二個 AT id，修復棒改） |
| AC-950-11 | 部署與 CI | `docker-compose.yml`、`.env.example`、`agentconsole-ci.yml`、`WRITE_CLOSURE` | 2／2 | Pass（AT-950-11-2 於 D10 後轉綠） |

重點條文逐項核對（程式與測試皆讀過）：W3／W4 Bridge 閘門序（停用 503→權杖 403→本文 ≤65536 單一 UTF-8 JSON 物件→外層七鍵→落檔→201；`_read_limited_body` 恰 65536 為 201、65537 為 422；validate 不需權杖、不落檔）；W5 AST 鎖負控樣本齊、stdin 例外收斂條件窄；W7／W8 Java 鍵序與時間格式（`xxx`，UTC 為 `+00:00`，毫秒截斷不進位）對上根層 `consoleaudit.py` 讀法；W10／W11 補償矩陣（一審 FAIL 的 P2 根因）：`BridgeRejectedException`（任何 4xx、503 `si_write_disabled`、503 `si_unavailable`）、`Failure` 且 bridgeStatus≠200、連線階段失敗 ⇒ 刪列；`TimedOut`、`deliveryUncertain` 的 `Unavailable`、`Failure` 且 bridgeStatus 200 ⇒ 保留並標 `outcomeUnknown`；三個突變從不同分支攻擊皆被殺；閘門序 authorize→輸入閘→取 ref→簽章→INSERT→Bridge；W12 數值邊界皆有對照（reason 500／501、單欄 300／301、三欄 700／701、close text 120／121），控制字元含 DEL 與孤立代理字元、code point 計長、一次回報全部違規、九個 dkind 矩陣逐列對上 M-D；W13 V13 的 regex CHECK、觸發器唯一例外、DELETE 允許；W14 全量掃描、事件側在前、依 auditRef 去重、回填冪等、NOT-EVALUABLE 時 `ingested` 與 `orphans` 為 null，根層 `export_limit_max` 500 相容；W16～W22 寫入控件只對 ADMIN、連點以 ref 同步擋、digest 綁開啟當下、NE 不給「退回」、NE 時不顯示「無待入帳」；D10 兩處 paths 已補。

### B. Contract 一致性（`API_Contract_SelfImproving_P2b.md`；後繼 P1b 契約）
審查者以標準庫獨立重算 V1～V4、負控一與二、黃金檔 G1～G5：body 位元組數 281／355／380／227、外層位元組數、sha256、mac、key_id（`f076edf0`）全部等於 TCS，不符 0 項；G1～G5 位元組數 527／609／630／658／454、sha256 與 mac 全等於 §5.3；外層鍵序、無 BOM、無結尾換行、無 `\r`、無 `\u` 跳脫；Bridge fixtures 與 backend resources 逐位元組相同。M-D／M-O／M-C 的 20 個期望 body 全部通過根層 `consoleaudit.body_guard`，與 `SiAuditSignerTest` 重組的期望逐字相等（雙向差集 0）。OpenAPI：`schema.d.ts` 71 條路徑、81 個操作、五個新 operationId 皆在、SI 路徑方法恰為 get／post；以 repo 的 openapi-typescript 7.13.0 對傾印檔重產與入庫檔逐位元組相同（無手改）；`OpenApiIT`（活的 `/v3/api-docs`，71／81）親跑通過；傾印檔的產出（Spring 測試 context）為 [他包回報]。契約後繼檔輕量核對（五個新路徑、三個 reason、`outcomeUnknown`、兩個 cause、NE 原因、G1～G5 與向量 sha256、Bridge 兩種端點形態）與實作一致；未逐段審。

### C. Business Invariants（無刪除、金鑰邊界、機密、部署）
`SiReadOnlyArchTest` 鎖恰七個 `@GetMapping`、四個 `@PostMapping`、無 Put／Patch／Delete；AT-935-3-E-1 共 54 次呼叫 Viewer 403、Operator 與 Admin 405；Bridge 九路徑乘三方法 27 次全 405、零檔零子行程；前端無刪除類控件。Bridge `app/` 全樹無 `AUDIT_KEY`、`AUTOSDD_SI`、`hmac.new`，`body="not json"` 加全零 mac 仍 201（不解 body、不驗簽）。`SiWriteProperties`／`BridgeProperties`／`SiAuditKeyRing` 的 `toString` 只標有沒有設；AT-950-5-E-2 掃回應、日誌、`si_console_writes`、`audit_log` 無 8 字元以上子字串；`sk-`、PEM、`AKIA`、`ghp_`、`xox` 形態 0 命中。`SecurityConfig.java:85` 對 `POST /api/v1/si/**` 要 ADMIN；`docker compose config` 靜態 rc 0：engine-bridge 無 ports、恰一條可寫 bind（`~/.autosdd/selfimproving/console_audit`→`/si-audit`、`create_host_path` False）、其餘 SI bind 與 `/sdd` 皆唯讀、與根層 CLI 預設目錄一致；`.env.example` 只有佔位。文件規則：128 個變更或新增檔 0 個含 CR；「測試摘要字樣＋4 位數字」0 命中（13 行 `test:8081` 誤報）；測試檔無 skip／xfail／`@Disabled`；`si check` rc 0（`PASS ref.obs`、`PASS ref.def`）。

### D. RTM 覆蓋率確認
AC 18／18、AT 98／98 皆可定位且真跑（RTM §2.3 子表 126 列）；單跑抽三層各一（Bridge `-k AT_950_2_1` 1 passed／38 deselected；backend `SiConsoleWriteApiIT.AT_933_1_4*` 1 test 通過；frontend `-t AT_933_1_2` 3 passed），子集互不誤收（唯一例外 P4-2）；51 個 AT 恰一個宣告、47 個為參數化或多個 it（每個宣告都帶底線形，符合 TCS「子情境以參數化保留底線形」，P4-3 資訊性）。被 P2b 取代的七條 P1b AT 在 RTM §2.2 以「→ AT-9xx-y（P2b）」標示（P1b TCS 勘誤二第 21 列）。

### E. 審查證據（當回合親跑；rc 先存變數）
| 項目 | 結果 |
|------|------|
| Bridge 七檔 `pytest -q -rs`（write_routes、console_ingest、audit_filename_safety、readonly_lock、si_cli、deploy_config、si_routes） | rc 0；216 passed、0 skipped；突變還原後再跑同數。主控親驗 Bridge 全套 rc 0、0 失敗（計數見 `helm_gates2.log`） |
| `ruff check .`（engine-bridge）與根視角 | rc 0／0 |
| backend `gradlew test` 加 `*Si*`、`*OpenApiIT`、`*SchemaMigrationIT`、`*V5UpgradeMigrationIT`、`*BridgePropertiesTest` | rc 0；235 tests、0 failures、0 skipped；還原後再跑同數。主控親驗 `clean build` BUILD SUCCESSFUL、0 failures、JaCoCo 驗證過（計數見同 log） |
| frontend vitest SI 子集（9 檔）／全套／`tsc --noEmit`／`npm run lint` | rc 0；SI 子集 287 passed；全套 80 檔全綠；tsc 無輸出；Prettier 全檔符合 |
| `python tools/selfimproving.py check`；根層 `TestDirEntryPrimitivesAreAccountedFor`；`test_ci_paths_cover_root_consumers.py` | rc 0（`PASS ref.obs`、`PASS ref.def`）；7 tests OK；49 passed |
| 標準庫重算 V1～V4、G1～G5；`schema.d.ts` 重產比對；`docker compose config` 靜態 | 不符 0 項；71／81 逐位元組相同；rc 0 |
| 突變複核（審查者自選 14 個，每層至少 1，皆已 Edit 還原、還原後檔案位元組與基線相同） | 12 殺／2 存活：B-M1 `compare_digest` 改 `==`→AT-950-2-2 殺；**B-M2 拿掉 `os.fsync`→存活（P3-1）**；B-M3 obs-add 的 subject 須為 null 規則停掉→AT-950-2-E-4 殺；K-M1 `xxx` 改 `XXX`→AT-950-4-E-1／E-3 殺；K-M2a `Unavailable` 一律當確定未送達→AT-950-6-E-2 殺；K-M2b `Failure` bridgeStatus 200 改 0→AT-950-6-E-2 殺；K-M3 deciders 不分大小寫→AT-935-4-1 殺；**K-M4 `PAGE_CAP` 20 改 40→存活（P4-1）**；K-M5 長度改 `String.length()`→AT-950-7-1 殺；K-M6 V13 觸發器不擋 body→AT-950-8-E-1 殺；F-M1 `codePointLength` 改 `.length`→AT-950-9-2 殺；F-M2 NE 多給「退回」→AT-933-1-1 殺；F-M3 NE 時也顯示 `si-writes-empty`→AT-935-5-E-4 殺；F-M4 豎線檢查關掉→AT-950-9-2、AT-935-2-E-1、AT-935-1-E-1、AT-950-9-E-3 殺。Developer 自報的突變未重放 |
| 主控同步站點（不計等級） | 黃金檔重產後 P1b `AT_932_1_E_6` 轉紅，主控改為去掉 `buckets` 欄的狀態 A 複本（P1b TCS 勘誤二第 22 列）；RTM 六處 `SchemaMigrationIT` 舊方法名已改 |

### 審查結論

| 項目 | 狀態 |
|------|------|
| FRD 功能規格 | Pass（0 項不符；P3 一項、P4 七項不阻擋） |
| Contract 一致性 | Pass |
| Invariants 保護 | Pass |
| RTM 覆蓋率 | 100%（AC 18／18、AT 98／98） |
| 測試強度（突變） | Pass（審查者 14 個：12 殺；2 存活各對應 P3-1、P4-1，修復棒補鎖） |

**SCG-4 建議**: [通過]（範圍＝Windows 單機；V1～V12 見〈未驗〉）

### 必修項目
無（P≤2 為零）。**P3（修復棒）**：P3-1 W2 的 `os.fsync` 沒有 AT 鎖住（`si_audit.py:74`；AT-950-1-2 只驗 `O_CREAT`／`O_EXCL`）——修復棒在 AT-950-1-2 加 `os.fsync` spy（對稽核檔 fd 恰一次、於寫入後關閉前）；TCS 勘誤一第 12 列。**P4（修復棒）**：P4-1 對帳頁數上限 20 沒被釘住（`SiReconcileService.java:37`）——AT-935-5-E-2 補 MiniBridge 計頁斷言（勘誤一第 13 列）；P4-2 `registry.test.ts:363` 標題含第二個 AT id——改文字描述（勘誤一第 14 列）。**P4（登記）**：P4-3「各恰一個測試」字面（勘誤一第 15 列）；P4-4 `truncated` 時「無待入帳（僅涵蓋最新 100 筆）」較舊待入帳不可見（UX；勘誤一第 16 列、OBS 候選）；P4-5 compose 可寫 bind 用 `create_host_path: false`、主機目錄須預先存在（README 與 `.env.example` 已載明；CI 不跑 compose）；P4-6 寫入失敗（含 `outcomeUnknown`）時前端不重取（勘誤一第 5 列）；P4-7 D5／§5.7 漏列檔與黃金檔副本歸屬（勘誤一第 7 列）。

### 未驗（如實標記；構造情境不得充當）
V1 全棧寫入通路（真 PG／真 backend／真 Bridge／真 CLI／可寫 bind）；V2 真瀏覽器；V3 真容器（只做 compose 靜態檢查；Windows Docker Desktop 可寫 bind 權限、主機目錄缺席時 compose 明確失敗皆未驗）；V4 掌舵者真機各一次 decide、obs-add、obs-close；V5 專用金鑰通道（缺金鑰時 promote 拒絕 Console 載體的 fail-closed 未驗）；V6 對帳實況；V9 雲端 CI；V10 macOS 與 Linux；V11 `docker compose logs` 機密掃描；V12 入帳後的 `check` 與歷史。另：`npm run build` 與 Playwright mock.spec 由主控／CI 承擔；Bridge `GET /health` 未測；`gradlew clean build` 與 JaCoCo 80% 為主控親驗；真 CLI 入帳只涵蓋 G1～G5（return、promote、decline-promote、rollback、unblock、resume、ack-handoff 七個 dkind 的 Java 簽出檔未餵真 CLI，只靠 `body_guard` 形態通過與 AT-950-4-2 的 body 逐字比對）。

### 流程摩擦（NFR-P2b-9 (10)；由主控於收尾入帳為 OBS 候選）
審查窗口內主控動過工作樹（06:42 `SiView.test.tsx` 同步站點、09:04 RTM 與 P1b TCS 勘誤）——與並行派工防互踩檢查表第 3 條有出入，如實登記；黃金檔重產的連鎖（根層 P3 動了 export 輸出 ⇒ 三處副本重產 ⇒ 一個 P1b 前端測試前提失效；三處副本的擁有者在 TCS §5.7 沒有位置）；PowerShell 重導向中文輸出 cp950 亂碼（改 Python `open(encoding="utf-8")` 寫檔）；檔案計數口徑（未追蹤目錄是否展開）；Gradle 熱 daemon 後單類別 7～25 秒、Bridge 與 frontend 突變一次不到 20 秒。審查者用量約 0.7M tokens。
