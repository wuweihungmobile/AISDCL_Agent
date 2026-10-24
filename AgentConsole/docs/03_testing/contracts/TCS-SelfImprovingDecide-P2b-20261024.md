# Test Contract Specification — SelfImproving Decide P2b（Console 決定載體與帳本寫入載體：Bridge 稽核檔落地、backend 簽章與對帳、frontend 決定／新增觀察／關閉對話框）
# 測試契約規格文件（增量變更；FRD-lite 併入檔頭）

**文件類型**: Test Contract Specification (TCS)
**SDD Gate**: SCG-4 PR Review Gate（RG-TEST 為補充閘）
**使用時機**: 已凍結系統（AgentConsole；上位文件已於 Stage-1 採納凍結）的單一 Feature（SelfImproving P2b 階段）；FRD-lite 與 TCS 同檔
**存放位置**: `AgentConsole/docs/03_testing/contracts/TCS-SelfImprovingDecide-P2b-20261024.md`（相對 monorepo 根；`spec-frozen --root` 取 monorepo 根，因 Stage-1 含根層 PRD）
**spec-format-version**: 1.0
**scenario**: brownfield

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **Feature ID** | F-902 |
| **Feature 名稱** | SelfImproving P2b：Console 決定載體（FR-SI-33）與帳本寫入載體（FR-SI-35）——Bridge 三個 POST 落稽核檔加唯讀預檢、backend 四個 POST 加對帳讀面與 Flyway V13、frontend 三個對話框與對帳面板 |
| **User Story** | US-908～US-916 |
| **建立日期** | 2026-10-24 |
| **輸入快照** | HEAD＝`23b1afb1b6d1afe63fdd1687462f106db44544af`；Stage-1 七份凍結檔 digest 見〈增量追溯表〉，SA 已以 `Get-FileHash -Algorithm SHA256` 逐檔重算（換行正規化前後相同），與任務書所列全部相同 |
| **QA 負責人** | SelfImproving P2b 的 SCG-4 QA 棒（獨立審查者；規格作者＝本 TCS 的 SA 棒，實作者＝鍵 `agentconsole-si-decide` 的 hooks-ON 開發 agent，三方不同） |
| **FSM 功能鍵** | `agentconsole-si-decide`（一律從 monorepo 根啟動；`python AISDLC_SDD/scripts/sdd_env.py --sub agentconsole --slug si-decide`） |
| **SCG Gate** | SCG-4 □ 待審 |

---

## 增量變更專用：FRD-lite 與〈增量追溯表〉

> 適用 `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`〈增量（delta）條款〉：變更限於已凍結系統的單一 Feature（上位文件＝`docs/01_requirements/SelfImproving_PRD.md` v0.10 與 AgentConsole 的 Architecture、ADR-001、ADR-002、`API_Contract_P3-6.md`、`openapi-p3-6.yaml`、`API_Contract_SelfImproving_P1b.md`，均已於 Stage-1 凍結）。**凍結檔不得再改**：發現需修訂處一律寫在 §7 的 ⚖ 清單，走掌舵者 T1／SPEC_REGRESSION_CHECK；凡上位文件未定、本檔為使其可測而補定義者，標「本檔類推」並列入 §7.1。**根層 P2 已 RELEASE（鍵 `monorepo-si-p2-gate-apply`）：根層程式碼是事實上的介面契約**——PRD 散文與碼不一致處以碼為準，逐條登記於 §7.2（根層碼不改）。

### FRD-lite

**現況與變更（Before／After；brownfield）**

- Before：(1) Bridge 只有六個 `GET /si/*`；`si_cli.py` 只組 `export` argv；`settings.py` 無寫入設定；沒有 `si_audit.py`；`tests/test_si_readonly_lock.py` 的判準 1 要求 SI 相關模組零寫入形態呼叫。(2) backend 的 `SiController` 只有六個 GET，`AgentBridge` 的 `si*` 方法只有 `siExport`，`SecurityConfig` 對 `POST /api/v1/**` 只要求 OPERATOR 以上，沒有 `console.si.*` 設定與 `si_console_writes`（Flyway 最大 V12），`BridgeHttpAdapter.handle` 只把 503 `si_unavailable` 當明確拒絕，`SiReadOnlyArchTest` 鎖「零寫入映射」。(3) frontend `/self-improving` 零寫入：`si.static.test.ts` 禁表單、mutation hook、非 GET 字樣，`lib/api` 恰六個 `getSi*`。(4) compose 的 SI bind 全為唯讀。(5) 根層 P2 的 `decide --carrier console`、`obs-add`、`obs-close`、`check`、`status`、`export buckets[]` 已在 HEAD。
- After：Bridge 新增 `app/si_audit.py`、三個寫入 POST 與 `POST /si/observations:validate`、`si_cli.run_validate`；backend 新增 `SiController` 的四個 POST 與 `GET /api/v1/si/console-writes`、`SiConsoleWriteService`、`SiAuditSigner`、Flyway V13 `si_console_writes`、`console.si.*` 設定；frontend 新增 `SiDecideDialog`、`SiObsForm`、`SiObsCloseDialog` 與對帳面板；compose 加唯一一條可寫稽核 bind；各鎖與釘選測試同步（§4）。**「零寫入」的前提改寫為「SelfImproving 帳本只有根層 CLI 能寫；Console 只產生並落地經簽章的稽核 JSON」**；導覽登記表不改（C20：新元件只進 `components/domain/si/`）。

**AC 編號規則**

1. **編譯文法**：AC 為 `AC-[\d\-]+`、AT 為 `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*` 且 AT 前兩段數字＝所屬 AC（ADR-XPLAT-016 §8.1）。PRD 的 `AC-SI-NN-Y` 含字母，**本檔採雙名**：機器可讀處用數字 id，人讀處同時寫出 PRD 全名。
2. **對映**：`AC-SI-33-Y`＝`AC-933-Y`、`AC-SI-35-Y`＝`AC-935-Y`（P2b 範圍：33-1、33-2、35-1～35-5，共 7 個）；本檔自增 AC 自 `AC-950-1` 起（P1b 已用 `AC-932-*`、`AC-940-*`，不撞號），共 11 個：950-1 Bridge 設定與落檔、950-2 Bridge 寫入端點、950-3 唯讀預檢、950-4 稽核 JSON 契約、950-5 backend 設定與金鑰、950-6 backend 寫入用例、950-7 backend 輸入閘、950-8 Flyway V13、950-9 frontend API 與純函式、950-10 契約面與釘選同步、950-11 部署與 CI。
3. **AT 命名**：`AT-<AC 數字 id>-<序>`；負控與邊界 `AT-<AC 數字 id>-E-<序>`；測試名含其底線形（`AT-933-1-4`→`AT_933_1_4`；Java 方法名以底線形開頭加駝峰敘述）。每個 AC 內數字序與 E 序各不超過 9。
4. **計數**：AC 18 個、AT 98 個（正控 49、負控 49；分佈見 §1 末）。

**P2b 交付物**（D1～D11；路徑相對 monorepo 根）

| 編號 | 交付物 | 路徑 | 製作者 | 主要驗證 |
|------|--------|------|--------|----------|
| D1 | Bridge 設定與落檔：`si_write_token`、`si_audit_dir`、`store_audit` | `AgentConsole/engine-bridge/app/settings.py`（改）、`app/si_audit.py`（新） | 開發 agent | AC-950-1 |
| D2 | Bridge 路由：三個寫入 POST 加 validate；`si_cli.run_validate` | `app/routers/si.py`（改）、`app/si_cli.py`（改）、`app/security.py`（加 `require_si_write_token`）、`engine-bridge/README.md`（改） | 開發 agent | AC-950-2、950-3 |
| D3 | Bridge 鎖與測試 | `tests/test_si_readonly_lock.py`（改）、`test_si_write_routes.py`、`test_si_audit_filename_safety.py`、`test_si_console_ingest.py`（新）、`fake_si.py`、`si_repo_support.py`（補）、`tests/fixtures/si_audit/G1～G5.json`（新） | 開發 agent | AC-933-1、950-4 |
| D4 | backend 安全與設定 | `SecurityConfig`（改）、`application.yml`（改）、`BridgeProperties`（擴充，形態不鎖）、`SiWriteProperties`（新） | 開發 agent | AC-935-4、950-5 |
| D5 | backend 寫入用例 | `SiWriteUseCase`、`SiConsoleWriteService`、`SiAuditSigner`、`SiAuditRefSource`、`SiWriteGates`、請求／回應 DTO、`AgentBridge`（加四個方法）、`BridgeHttpAdapter`（加實作並讓 `handle` 認 503 `si_write_disabled`）、`UpstreamException.Unavailable`（區分連線階段與送出後通訊失敗：加 `deliveryUncertain` 旗標或新增子類，形態不鎖、行為由 AT-950-6-2 與 AT-950-6-E-2 鎖）、`SiBridgeErrors`、`ErrorReasons`（加三碼）、`SiController`（加四個 POST） | 開發 agent | AC-933-1、950-4、950-6、950-7 |
| D6 | Flyway V13 | `backend/src/main/resources/db/migration/V13__si_console_writes.sql`；`SiConsoleWriteRepository`／Adapter | 開發 agent | AC-950-8 |
| D7 | backend 對帳讀面 | `GET /api/v1/si/console-writes`（`SiController`）、`SiReconcileService`（本檔類推）、DTO | 開發 agent | AC-933-2、935-5 |
| D8 | frontend | `components/domain/si/{SiDecideDialog,SiObsForm,SiObsCloseDialog,SiWritesPanel}.tsx`、`SiView.tsx`／`SiStatusBanner.tsx`／兩個清單面板／`siParts.tsx`（接入與共用元件；`SiEventsPanel.tsx` 不動）、`lib/api/{endpoints,queries,types}.ts`、`schema.d.ts`（重產）、`lib/domain/si.ts` | 開發 agent | AC-933-1、935-1～935-5、950-9 |
| D9 | 既有釘選測試同步（只增不減；前後數字見 §4） | `OpenApiIT`、`SchemaMigrationIT`、`V5UpgradeMigrationIT`、`SiReadOnlyArchTest`、`SiMirrorApiIT`、`BridgePropertiesTest`、`endpoints.test.ts`、`si.endpoints.test.ts`、`si.static.test.ts`、`si.test.ts`、`test_si_readonly_lock.py`、`test_si_routes.py`、`test_si_deploy_config.py`（逐項見 §4） | 開發 agent | AC-950-10 |
| D10 | 文件與 CI 連動 | `docker-compose.yml`、`.env.example`（開發 agent）；`.github/workflows/agentconsole-ci.yml` 的 `paths`、`API_Contract_SelfImproving_P2b.md`、RTM 本地子表、Architecture 去註（**主控**） | 開發 agent、主控 | AC-950-11；V8、V9 |
| D11 | 出口實查（V 系列，非 AT） | §6.2 的 V1～V12 | QA、主控、掌舵者 | PRD §8.1 P2b (a)～(e) |

**提交順序與責任**

- 依賴序 Bridge（D1～D3）→ backend（D4→D6→D5→D7）→ frontend（D8）→ D9、D10；測試與受測碼同步完成。**D8 的 `schema.d.ts` 重產需要後端在線**（`npm run gen:api` 取 `http://localhost:8080/v3/api-docs`），須在 D5～D7 完成且 backend 啟動後執行，結果入庫。每支程式完成即編譯並跑該區 AT，不累積（`AgentConsole/CLAUDE.md` 鐵律 11）。
- 開發 agent **不 commit／push**、不動根層 `tools/`、`.github/`、`.claude/`、凍結檔與既有 TCS（鐵律 7）。與實作**同一個 commit** 收齊者：D10 的 `.github` 與 `API_Contract_SelfImproving_P2b.md`（主控落檔；開發 agent 於交卷以純文字附全文草稿，內容清單見 W25）；Architecture §10.3、§11.1、§12.1 L-14 去〔P2b 規劃〕於 RELEASE 之後另以純文件 commit。
- **AC-950-11 的 CI paths AT 依賴主控的 D10**：之前為預期紅（偵測連動面未收齊，不得改弱）。開發 agent 交卷時逐行列出需新增的 `paths` 項（`WRITE_CLOSURE` 的每一項，兩個觸發器）。
- 真帳本、真事件帳本、真 `~/.autosdd/` 一律唯讀：AT 只用 `tests/fixtures/si_repo/` 的複本與 tmp 目錄；出口 (c)（掌舵者真機各一次 decide、obs-add、obs-close）屬 V 系列，由掌舵者做、不由 AT 充當。
- 依賴：本鍵依賴根層 P2（已 RELEASE；`decide --carrier console`、`obs-add`、`obs-close`、`obs-add --dry-run`、`export` 的 `marks_kv`／`audit_ref` 於 HEAD 可實跑）與 P1b 的顯示面。

**〈P2b 行為規則〉**（W1～W25；各 AT 以 W 編號引用。實查依據：根層 `tools/lib/selfimproving/{consoleaudit,obsrows,obswrite,decwrite,decheck,decgrammar,events,rows,status}.py` 與 `tools/selfimproving.py`；Bridge 的 `app/{si_cli,settings,security,errors}.py`、`routers/si.py`；backend 的 `BridgeHttpAdapter`、`SiBridgeErrors`、`SecurityConfig`、`AuditLoggingFilter`、`MiniBridge`；frontend 的 `components/domain/si/*`、`lib/domain/si.ts`、`lib/api/*`；以及 SA 棒對真 CLI 的唯讀探針——scratchpad 內約 90 個稽核檔變形案例，寫入只發生在 tmp 倉）

*A. Bridge（`AgentConsole/engine-bridge/app/`）*

- **W1 設定**：`Settings` 新增 `si_write_token: str | None`（`BRIDGE_SI_WRITE_TOKEN`，`repr=False`）與 `si_audit_dir: Path | None`（`BRIDGE_SI_AUDIT_DIR`）。權杖規則＝既有 `_parse_sdd_write_token` 同款（去空白後空＝None；整串為 `<…>` 或含 `<YOUR_`〔不分大小寫〕或短於 32 字元＝`SettingsError`，訊息不含值）。稽核目錄：去空白後空＝None；非空＝`Path(raw).resolve()` 過 `_anchor_guard`；不檢查存在性、不併入 `allowed_path_roots`。**寫入面啟用＝兩者皆非 None**；`settings.py` 檔頭與 README 環境變數表各補兩列。
- **W2 `si_audit.store_audit(audit_dir, audit_ref, raw) -> None`**（整個 `app/` 唯一以寫入形態開啟 SI 路徑者）：`audit_ref` 須整串為**小寫正規 UUID**（否則 `ValueError`，路由層先擋成 422）；目標＝`audit_dir/<audit_ref>.json`，檔名只源自已驗過的 ref；`os.open(O_WRONLY|O_CREAT|O_EXCL`，Windows 加 `O_BINARY`）→寫入 raw 全部位元組→`os.fsync`→關閉；同名已存在＝`ApiError(409, "si_audit_exists")`（不覆寫）；其他 `OSError`（含目錄不存在或不可寫、磁碟滿）＝`ApiError(503, "si_unavailable", cause="audit_write_failed", detail="errno=<n>; <例外類名>")`，且寫入中途失敗須刪除半成品（`os.unlink` 包 `try/except OSError`；`O_BINARY` 以 `getattr(os, "O_BINARY", 0)` 取；不使用 `os.replace`、`rename`、`move`，使根層站點普查不增站點）；detail 不含任何絕對路徑；不建立 `audit_dir`。
- **W3 三個寫入路由**：`POST /si/proposals/{id}:decide`、`POST /si/observations`、`POST /si/observations/{id}:close`。依序（先中者定案）：(1) 寫入面停用＝503 `si_write_disabled`（先於權杖與本文）；(2) `X-Bridge-Token` 缺或錯＝403 `si_write_forbidden`（缺與錯同一回應；`hmac.compare_digest` 比 bytes；拒絕也記稽核，不含任何權杖值；比照 `require_sdd_write_token`，新增 `require_si_write_token`）；(3) 本文須為單一 UTF-8 JSON 物件且 ≤ `SI_WRITE_BODY_MAX_BYTES`＝65536（超過即 422，不讀完）；(4) 外層鍵集合**恰七個**（`schema_rev`、`kind`、`audit_ref`、`subject`、`body`、`key_id`、`mac`）、`schema_rev` 為整數 1（非 bool）、`kind` 等於端點的 kind（decide、obs-add、obs-close）、`audit_ref` 為小寫正規 UUID、`subject` 為字串或 null（decide 與 close 須為字串且等於路徑 `{id}`；obs-add 須為 null）、`body`／`key_id`／`mac` 皆為字串；路徑 `{id}`：decide 為 `^(PROP|RUN)-SI-[0-9]{3,}$`、close 為 `^OBS-SI-[0-9]{3,}$`；任一不符＝422 `invalid_request`（`violations[{field,rule,message}]`）；**不解內層 `body`、不驗簽、不驗 key_id／mac 的形態**；(5) `store_audit`；(6) 201 `{"audit_ref": <ref>, "stored": true}`（鍵序固定、不回路徑）。其餘方法（含 DELETE、PUT、PATCH）一律 405。
- **W4 validate**：`POST /si/observations:validate`，**不需權杖、不看寫入設定、不落檔**。本文須為單一 JSON 物件且 ≤65536（否則 422，不啟動子行程）；`si_cli.run_validate(si_root, raw: bytes)` 以 `build_validate_argv`＝`[sys.executable, <si_root>/tools/selfimproving.py, "obs-add", "--dry-run", "--body-file", "-", "--json"]` 起子行程（cwd＝si_root；stdin 餵 raw 位元組；環境與逾時同 `export`；不帶 `--repo`、`-I`、`-P`）。判定（先中者）：`si_root_unset`、`si_script_missing`、`spawn_failed`、`timeout`、`stdout_too_large`、rc 為 0 或 1 → stdout 須為單一 JSON 物件（否則 `bad_json`）且含 `ok`（布林）、`row`（字串）、`row_bytes`（整數）、`row_max_bytes`（整數或 null）、`findings`（陣列）（否則 `bad_shape`）→ 200 逐值透傳；rc 為其他值（含 3）＝`nonzero_rc`；失敗一律 503 `si_unavailable`（cause 如前，detail 為 `rc=<n|none>; stderr=<尾段>`）。`ok=false`（rc 1）仍 200。
- **W5 AST 鎖（`tests/test_si_readonly_lock.py`，改寫判準）**：判準 1′——「SI 相關」模組（`si_cli.py`、`routers/si.py`、`si_audit.py`，及原始碼含 `selfimproving` 字樣者）的寫入形態呼叫（沿 `write_shaped_calls`）只准出現在 `si_audit.py`；且該檔每個寫入形態呼叫的路徑引數須源自函式參數 `audit_dir`（不得含字串或 `Path` 字面路徑、`Path.home()`、`os.environ`、`os.getenv`、`expanduser`）；`routers/si.py` 呼叫 `store_audit` 時第一引數須是以 `.si_audit_dir` 結尾的屬性存取。判準 2、3 不變。判準 4′——組 argv 的函式（含「首元素 `sys.executable` 的列表字面值」者）恰兩個：`build_argv`（動詞 `export`）與 `build_validate_argv`（動詞 `obs-add` 接 `--dry-run`），各恰一個 `return`（列表字面值）；`Popen` 呼叫恰一處且其 argv 來自這兩函式之一；白名單＝{`export`、`obs-add --dry-run`}。判準 5′——對兩函式動態呼叫，動詞位置恆在白名單、不含 `--repo`。**邊界**：形態判準，`getattr`、動態拼接、`importlib` 看不到。
- **W6 夾具與閉包**：`fake_si.py` 新增旋鈕 `dry_run`（要輸出的物件；預設最小合法物件）並記錄 stdin（`stdin_b64`）；P1b 行為不變。`si_repo_support.py` 新增 `WRITE_CLOSURE = CLI_CLOSURE + ("tools/lib/apply_lock.py", "tools/lib/sdd_latest.py")`（SA 實測：缺任一個，寫入動詞即 `ImportError`——`evwrite` 要 `apply_lock`、`writeverbs` 頂層要 `sdd_latest`）與 `ingest_run(root, home, key, *args)`（環境＝`cli_env` 加 `AUTOSDD_SI_DIR`、`AUTOSDD_SI_AUDIT_KEY`）；`make_si_repo(..., closure=)` 缺檔大聲失敗。

*B. 稽核 JSON（Java 與 Python 之間的位元組契約；以根層 `consoleaudit.py` 為準）*

- **W7 格式**：外層恰七鍵、序固定 `schema_rev`、`kind`、`audit_ref`、`subject`、`body`（字串）、`key_id`、`mac`；緊湊 JSON、UTF-8 無 BOM、非 ASCII 原樣（不 `\u` 跳脫）、無結尾換行；**檔位元組＝backend 送出的請求本文＝Bridge 落檔位元組＝`audit_sha256` 的對象**。`body`＝緊湊 JSON 文字，鍵序與鍵集合依 §5.2 表 M-D、M-O、M-C；共通鍵 `schema_rev`（1）、`audit_ref`、`kind`、`user`、`role`（恆 `ADMIN`）、`time`。`audit_ref`＝小寫正規 UUID；`user`＝JWT subject；`time`＝`Clock` 現在、截到秒、樣式 `yyyy-MM-dd'T'HH:mm:ss` 接 `xxx`（UTC 為 `+00:00`，**絕不輸出 `Z`**）。`subject`：decide＝PROP 號（resume 為 RUN 號）、obs-close＝OBS 號、obs-add＝null，且須等於 body 的 `prop`／`run`／`obs_id`。簽章：金鑰＝環中**第一把**的 UTF-8 位元組；`key_id`＝sha256(金鑰) 前 8 碼小寫 hex；`mac`＝HMAC-SHA256(金鑰, `body` 的 UTF-8 位元組) 小寫 hex；**簽 `body` 字串本身、不重新序列化**。字串逸出為標準 JSON（`"`、`\`、控制字元；`/` 不逸出）。
- **W8 向量與黃金檔**：跨語言向量 V1～V4 與負控逐字取自根層 P2 TCS §5.5（SA 以標準庫重算全部相同，§5.1）；黃金檔 G1～G5 是**固定輸入下 Java 正式碼的輸出**（`Clock.fixed`＝2026-10-24T22:30:15+08:00、`SiAuditRefSource` 固定、金鑰＝向量金鑰），住 `backend/src/test/resources/si/audit/`，Bridge 副本住 `tests/fixtures/si_audit/`（逐位元組相同，AT 鎖住）；SA 已把這五個檔以標準庫造出並餵真 CLI 實跑（全數 rc 0，§5.3）。

*C. backend（`AgentConsole/backend`）*

- **W9 設定與金鑰**：`console.si.deciders`（`CONSOLE_SI_DECIDERS`，逗號清單；去空白、去空項、去重、保序；預設空＝無人可寫；比對＝與 JWT subject 逐字相等、區分大小寫）；`console.si.audit-key`（`CONSOLE_SI_AUDIT_KEY`；金鑰環，格式同根層 `AUTOSDD_SI_AUDIT_KEY`：逗號分隔、各自去空白、空項略過；**第一把簽章**、其餘保留供輪替——主機環須含全部舊金鑰；空或未設＝寫入面停用；有設而任一把短於 32 字元或為 `<…>` 佔位＝啟動失敗，訊息只講長度與序號）；`console.bridge.si-write-token`（`${BRIDGE_SI_WRITE_TOKEN:}`，規則同 `sdd-write-token`；未設＝停用）。`toString`、日誌、錯誤封包、`details` 一律不含金鑰與權杖值。**寫入面啟用＝金鑰環與權杖皆有設**（deciders 可空）。Bridge 不持有金鑰。`SiAuditSigner`、`SiWriteGates`、`SiConsoleWriteService` 住 application 層，經建構子純值或 application 層的 port 取得名單、金鑰環與權杖（既有 ArchUnit A2、A5：application 不得依賴 adapter 或 infrastructure；`SiWriteProperties` 只住 `infrastructure.config`）。
- **W10 閘門序（四個 POST 同一關，含 validate）**：401（無有效 JWT）→403 `ACCESS_DENIED`（角色非 ADMIN；`SecurityConfig` 對 `POST /api/v1/si/**` 要求 ADMIN，置於通用 POST 規則之前）→403 `si_write_forbidden`（帳號名不在 deciders；於用例入口以 `ForbiddenException` 擲出）→503 `si_write_disabled`（backend 端停用；`details.cause`＝`audit_key_unset` 或 `bridge_token_unset`，先中者）→422（W12 輸入閘，含帳號名值域 `^[A-Za-z0-9_.-]{1,64}$`）→執行。DELETE、PUT、PATCH：Viewer 403、Operator 與 Admin 405。
- **W11 寫入用例（`SiWriteUseCase`／`SiConsoleWriteService`）**：對 decide、obs-add、obs-close 依序：授權（W10）→停用檢查→輸入閘（W12）→取 `auditRef`（`SiAuditRefSource`，預設 `UUID.randomUUID()` 小寫）與 `time`（`Clock`）→`SiAuditSigner` 組 body 與外層字串並簽章→**INSERT `si_console_writes` 一列**→呼叫 `AgentBridge.siWrite…`（外層字串原樣送出，不經 Jackson 重新序列化）→結果：2xx 且本文解得出 `audit_ref` 與 `stored`＝回收據。**補償刪除該列（確定未落檔）**：`BridgeRejectedException`（任何 4xx、503 `si_write_disabled`、503 `si_unavailable`）；`UpstreamException.Failure` 且 `bridgeStatus`≥500；`UpstreamException.Unavailable` 且原因為連線階段（`ConnectException`、`HttpConnectTimeoutException`、`UnknownHostException`）。**保留該列（結果不明）**：`UpstreamException.TimedOut`；其他 `Unavailable`（`translate` 的「通訊失敗」，含送出後連線重設、提前 EOF）；`Failure` 且 `bridgeStatus`＝200（2xx 的本文無法解析）。其餘 `Failure`（`bridgeStatus` 小於 500 且不等於 200，含 1xx／3xx）＝請求未被處理，補償刪列。兩類由 `Unavailable` 的區分機制判定（D5），保留者對外的 `details.outcomeUnknown` 為 true（W15）。每請求至多一次 Bridge 呼叫、不重試；重送一律新 `auditRef`。順序為簽章→INSERT→Bridge：INSERT 仍先於 Bridge（寧可有列無檔、不要有檔無列；PRD §9.3 的 WHY，見 ⚖7）。`validate`：不取 ref、不簽、不寫 DB，組未簽 body（`schema_rev`、`kind` 為 obs-add、`user`、`role`、`time` 加觀察欄位；無 `audit_ref`、`mac`、`key_id`）→`siValidateObservation`。成功收據 `data`＝`{auditRef, kind, subject, time, keyId}`（不含 body、mac）。
- **W12 請求 DTO 與輸入閘**：decide＝`{dkind, digest?, reason?, reasonClass?, unverifiedAck?}`（路徑 `{id}`）；觀察（obs-add 與 validate）＝`{context, symptom, evidence, category, severity, face, exposure?, externalDerived, corrects?}`；關閉＝`{terminal, ref?, text?}`（路徑 `{id}`）。觀察 DTO **刻意不含** `marks_extra`（根層 body 的選用鍵）：Console 只產生 `corrects` 對應的 `rel=corrects:<ID>` 標記，其餘標記由主控手寫入帳。欄位與值域＝§5.2 表 M-D、M-O、M-C。違規一律 **422、頂層 `reason`＝`invalid_request`、`details.violations[{field,message}]`**（camelCase 欄名、一次全列）；字串先 trim 再判；所有字串欄不得含 C0 控制字元（U+0000～U+001F）與 DEL（U+007F）；長度以 code point 計；閘先於一切副作用（取 ref、簽章、DB、Bridge）。**閘的目的是不送出「根層入帳時不拒、事後 `check` 才轉紅」的 body**（SA 實測：approve 多帶 reason 或 flags、reject 的 reason 為空或含換行、obs-add 或 obs-close 欄位含換行，真 CLI 皆 rc 0 入帳而 `check` 轉紅，§7.2 發現 1）；列規則與前提的權威仍是 CLI（`retired` 座標、`corrects` 是否存在、PROP 狀態前提、卡面 digest 新鮮度），Console 不複製。
- **W13 Flyway V13**（`console.si_console_writes`）：`audit_ref UUID PRIMARY KEY`、`kind VARCHAR(12) NOT NULL CHECK (kind IN ('decide','obs-add','obs-close'))`、`"user" VARCHAR(64) NOT NULL`、`role VARCHAR(20) NOT NULL`、`"time" TIMESTAMP WITH TIME ZONE NOT NULL`、`subject_id VARCHAR(64)`、`digest VARCHAR(71)`、`body TEXT NOT NULL`、`key_id CHAR(8) NOT NULL`、`mac CHAR(64) NOT NULL`；`time` 上建索引。**列不可改**：`BEFORE UPDATE` 觸發器拒絕任何欄位變動，唯一例外是 `subject_id` 由 NULL 變為非 NULL（本檔類推，PRD 只要求不可改）；DELETE 允許（補償）。程式面：port 只有 insert、deleteByAuditRef、fillSubjectId 與唯讀查詢；原始碼對該表的 UPDATE 恰一條。
- **W14 對帳讀面**：`GET /api/v1/si/console-writes?limit=<1..500，預設 100>`（Viewer 以上；非整數或越界＝400）。回應 `data`＝`{items, truncated, orphans, reconcile}`：`items[]`（時間新到舊、`auditRef` 升冪破同刻）鍵集合恰 `auditRef`、`kind`、`user`、`role`、`time`、`subjectId`、`digest`、`keyId`、`ingested`（**不含 `body`、`mac`**）；`reconcile`＝`{status: "ok"|"NOT-EVALUABLE", reason, backfilled}`。**對帳在 backend 一次全量做**（前端分頁只載入部分帳本，逐頁判會誤報待入帳）：以 `siExport` 的 `observations` 與 `events` 各自 `limit=500` 迴圈取頁（`truncated` 且 `next_since` 為數字即續取，上限各 20 頁）；「已入帳」＝帳本中有同 `audit_ref` 的 `dec`／`obs.add`／`obs.close` 事件，或 `marks_kv.audit_ref` 相同的觀察列；`ingested`＝表內該列是否已入帳（NE 時為 null）；`orphans[]`（NE 時為 null）＝帳本中 `carrier` 為 console 而表內無對應 `audit_ref` 的項，元素 `{auditRef, kind, subject}`（kind 為 decide／obs-add／obs-close，subject 為 dec 的 prop 或 run、觀察列的 id、obs.close 的 obs）；orphans 的順序與去重：先列事件帳本的項（依 seq 升冪）、後列觀察列的項（依帳本行序），一律以 `auditRef` 去重，同一個 obs-add 同時有 `obs.add` 事件與觀察列只計一項（取事件側）；**回填**：kind 為 obs-add 且 `subject_id` 為 NULL 的列，若某觀察列的 `marks_kv.audit_ref` 相同，則 `UPDATE … SET subject_id = <OBS id> WHERE audit_ref=? AND subject_id IS NULL`（冪等；`backfilled` 為本次筆數）。**讀路徑唯一的副作用是這個回填**；Bridge 失敗、逾時、頁數超限＝`status` 為 `NOT-EVALUABLE`（`reason` 為 si_unavailable、bridge_unreachable、bridge_timeout 或 scan_cap_exceeded）、`items` 仍回、不回填、不得以空陣列冒充；Bridge 永遠只被呼叫 GET。
- **W15 錯誤對映（寫入端點）**：Bridge 503 `si_write_disabled`→503 同 reason（`details.detail` 逐字）；403 `si_write_forbidden`→403 同 reason；409 `si_audit_exists`→409 同 reason；422→422、頂層 reason＝既有 `引擎拒絕此請求`（`ErrorReasons.BRIDGE_REJECTED`），`details.bridgeReason` 與 `violations` 逐項；503 `si_unavailable`→503 同 reason（`details.cause`、`details.detail` 逐字）；其他 5xx→502；連線階段失敗（拒絕、DNS、連線逾時）→502（已補償刪列）；讀取逾時→504、送出後通訊失敗→502、2xx 本文無法解析→502（這三種結果不明者保留列，`details.outcomeUnknown` 為 true，見 W11）。`BridgeHttpAdapter.handle` 須把 503 `si_write_disabled` 視為明確拒絕（沿 `sdd_write_disabled`）。`ErrorReasons` 新增 `SI_WRITE_DISABLED`、`SI_WRITE_FORBIDDEN`、`SI_AUDIT_EXISTS` 三常數（與 Architecture §11.1 逐字一致；不新增其他 reason）。

*D. frontend（`AgentConsole/frontend`）*

- **W16 API 層**：`lib/api/endpoints.ts` 新增 `postSiDecide(id, body)`→`POST /api/v1/si/proposals/{seg}/decide`、`postSiObservation(body)`→`POST /api/v1/si/observations`、`postSiObservationClose(id, body)`→`POST /api/v1/si/observations/{seg}/close`、`postSiObservationValidate(body)`→`POST /api/v1/si/observations/validate`、`getSiConsoleWrites({limit})`→`GET /api/v1/si/console-writes`；`types.ts` 新增 `SiDecideRequest`、`SiObservationRequest`、`SiCloseRequest`、`SiWriteReceipt`、`SiValidation`、`SiConsoleWrite`、`SiConsoleWrites`；`queries.ts` 新增 `useSiConsoleWrites`（沿 `SI_QUERY_OPTIONS`；只有 ADMIN 啟用）、`useSiDecide`、`useSiAddObservation`、`useSiCloseObservation`、`useSiValidateObservation`（mutation 成功後使 SI 查詢與 `console-writes` 失效重取，不碰 `["notifications"]` 家族）。
- **W17 純函式（`lib/domain/si.ts`，名稱釘死）**：`decideVerbOptions(card)`（表 M-V）；`validateDecideForm`、`validateObservationForm`、`validateCloseForm`（回 `{field→message}`；與 W12 同表，前端先擋、backend 仍為權威）；`estimateRowBytes(form, ctx)`（與 CLI 同一九欄組列規則的位元組估計：`| OBS-SI-` 接 3 位數、時間格 `YYYY-MM-DD HH:MM ±HH:MM`、標記欄 `面=…`〔守衛加 `暴露=`、外部衍生加 `外部衍生=是`、更正加 `rel=corrects:<ID>`〕接 `來源=人;回報者=<user>;carrier=console;audit_ref=<UUID>`；含 `|` 或控制字元者回拒收而不給估計值；**僅供提示**，權威是 validate 與 CLI，⚖26）；`ingestCommands(kind, subject, auditRef)`→`{powershell, posix}`（對應 `CopyCommand` 的 `shell` 屬性值，沿 SDD 恢復指令先例），兩者字串**相同**：decide 為 `python tools/selfimproving.py decide <subject> --carrier console --audit-ref <auditRef>`、obs-add 為 `python tools/selfimproving.py obs-add --carrier console --audit-ref <auditRef>`、obs-close 為 `python tools/selfimproving.py obs-close --carrier console --audit-ref <auditRef>`（於 monorepo 根、已設主機端 `AUTOSDD_SI_AUDIT_KEY` 的 shell 執行；金鑰不出現在指令）；`pendingWrites(items)`；`siWriteErrorText(error)`（含 reason 逐字；422 另列各 violation 的 message；503 `si_unavailable` 另列 cause 與 detail）；`SI_REASONS` 增 `WRITE_DISABLED`、`WRITE_FORBIDDEN`、`AUDIT_EXISTS`。前端**不重算**任何判準：不判卡面 digest 新鮮度、不判 PROP 前提的細節（見 ⚖15）。
- **W18 `SiDecideDialog`**（`data-testid`：`si-decide-dialog`、`si-decide-verb`、`si-decide-digest`、`si-decide-reason`、`si-decide-class`、`si-decide-ack`、`si-decide-submit`、`si-decide-result`）：動詞下拉＝`decideVerbOptions` 的結果，**預設不選**、無批次或全部核准；顯示卡面 digest（前 8 碼可見、全文在 `title`）且送出時綁定開啟當下的值；必填依表 M-D（缺則送出鈕停用並顯示原因）；晉升後式（verdict 為 NE）須勾 `si-decide-ack`；恢復由狀態橫幅的 `si-resume-open` 開啟、綁 `suspended.run`。送出＝單次 `postSiDecide`（請求中停用，防連點）；成功＝顯示 `auditRef`、待入帳字樣與兩個 `CopyCommand`（W17 指令），對話框不自動關閉；失敗＝toast（`siWriteErrorText`）、對話框不關。
- **W19 `SiObsForm`**（模式 `new`／`correct`；testid：`si-obs-form`、`si-obs-context`、`si-obs-symptom`、`si-obs-evidence`、`si-obs-category`、`si-obs-severity`、`si-obs-face`、`si-obs-exposure`、`si-obs-external`、`si-obs-corrects`、`si-obs-estimate`、`si-obs-preview`、`si-obs-findings`、`si-obs-submit`、`si-obs-result`）：欄位與列舉＝表 M-O；字串欄即時拒收豎線與控制字元；face 為守衛時才出現且必填 exposure；`correct` 模式 corrects 預填且唯讀。表單邊打邊以 `estimateRowBytes` 在 `si-obs-estimate` 顯示估計位元組與 `row_max_bytes`（首次 validate 前用 700；估計值大於上限只警示、不阻擋，PRD AC-SI-35-1 的即時顯示，⚖26）。**送出＝先 `postSiObservationValidate`**：回 `ok=false`＝顯示 findings（code 與 detail 逐字、純文字）並**不**送 POST；`ok=true`＝顯示 `row`、`rowBytes` 與 `rowMaxBytes` 後才 `postSiObservation`；validate 回 422 或 503 一律顯示原因、不送。
- **W20 `SiObsCloseDialog`**（testid：`si-obs-close-dialog`、`si-close-terminal`、`si-close-ref`、`si-close-text`、`si-close-submit`、`si-close-result`）：終值下拉恰七項（表 M-C；**無 open**）；ref 與 text 的必填與格式依表 M-C；只對處置**恰為 open** 的列提供入口。送出與成功態同 W18。
- **W21 `SiView` 接入與對帳面板**：寫入控件**只對 ADMIN 渲染**（testid 前綴 `si-decide-open-`＜PROP 號＞、`si-resume-open`、`si-obs-new`、`si-obs-correct-`＜OBS 號＞、`si-close-open-`＜OBS 號＞）；是否在 deciders 由 backend 判，403 原因逐字 toast（前端不新增「我是否在名單」端點）；無任何刪除、移除、清除控件。ADMIN 才發 `console-writes` 查詢並渲染 `si-writes-panel`：`si-pending-<auditRef>` 列（kind、subject、time，展開見指令）；`si-write-alerts`（`role="alert"`，逐項 auditRef、kind、subject）；NE 時顯示 `si-reconcile-ne`（reason 逐字）而**不得**顯示無待入帳；僅在 ok 且無待入帳與無 orphans 時顯示 `si-writes-empty`。非 ADMIN：零控件、零 POST、零 `console-writes`、無待入帳或警示字樣（P1b 預設角色 OPERATOR 即此情境）。導覽登記表不改。
- **W22 靜態鎖（`si.static.test.ts` 改寫）**：`<form`、mutation hook 與非 GET 字樣只准出現在三個寫入元件；全樹禁 `dangerouslySetInnerHTML`、HTML／Markdown 渲染器、直接 `fetch(`、以 `/si/` 起頭的字串字面、8081 與 BRIDGE 字樣、delete／PUT／PATCH 方法字樣。

*E. 契約與連動*

- **W23 既有釘選測試同步**：數字與形態逐項見 §4〈需同步的既有測試〉；一律只增不減（`OpenApiIT` 67→71 路徑、76→81 操作；`endpoints.test.ts` 74→79；`SchemaMigrationIT` 與 `V5UpgradeMigrationIT` 的版本表加 13；`SiReadOnlyArchTest`、`SiMirrorApiIT`、`test_si_readonly_lock.py`、`test_si_routes.py`、`test_si_deploy_config.py` 改寫為 P2b 形態）。
- **W24 部署與 CI**：compose 的 engine-bridge 新增 `BRIDGE_SI_AUDIT_DIR`（容器內路徑）與**恰一條**可寫長語法 bind（source 為主機 `<AUTOSDD_SI_DIR>/console_audit`，經 compose 變數提供，不寫死磁碟路徑；`AUTOSDD_SI_DIR` 未設時預設來源為 `~/.autosdd/selfimproving`，與根層 CLI 的預設同處，Windows 以 `%USERPROFILE%`、macOS 與 Linux 以 `$HOME` 展開，寫法不鎖，AT-950-11-1 只驗 source 以 `console_audit` 結尾且不含寫死的磁碟路徑），其餘 SI bind 全部維持唯讀；engine-bridge 與 backend 各新增 `BRIDGE_SI_WRITE_TOKEN`（預設空），backend 另加 `CONSOLE_SI_DECIDERS`、`CONSOLE_SI_AUDIT_KEY`（預設空）；`.env.example` 三個新變數只放 `<YOUR_…>`；`agentconsole-ci.yml` 的 `paths` 補 `WRITE_CLOSURE` 新增的兩個根層檔（`tools/lib/apply_lock.py`、`tools/lib/sdd_latest.py`，兩個觸發器；主控同 commit）；README 補環境變數、四個 POST 路徑與三個 reason。
- **W25 文件連動（不留尾巴）**：`API_Contract_SelfImproving_P2b.md`（新檔；開發 agent 附全文草稿，主控落檔）必含：四個 backend POST 與 `GET /console-writes` 的路徑、請求欄位表（M-D、M-O、M-C）、回應形態、狀態碼與 `reason` 對映（W10、W15）、稽核 JSON 契約（W7；§5.1 向量與 G1～G5 的 sha256）、`console-writes` 回應形態（W14）、Bridge 四個端點與 W3、W4 的驗證順序；RTM 本地編號子表（先例 §2.2）；Architecture §10.3、§11.1、§12.1 L-14 去〔P2b 規劃〕於 RELEASE 之後另以純文件 commit；根層 RTM 的 FR-SI-33、35 列由主控依 Root_Layout SSOT 填。

**主控先行裁決（已裁，不再開 ⚖；掌舵者可推翻）**：(1) 稽核 JSON 形狀以根層碼為準；(2) 決定對話框動詞集合＝根層 `decide --carrier console` 實際受理的 dkind，不多不少（九個），晉升後式以必填勾選表達，恢復綁 RUN 號；(3) 前端不新增「我是否在 deciders」端點，寫入控件只對 Admin 顯示；(4) 對帳讀面＝唯讀 `GET /api/v1/si/console-writes`，`subject_id` 回填於該查詢時做；(5) Flyway 版本＝V13；(6) `time`＝伺服器送出時刻、秒精度、`±HH:MM`；(7) 帳號名值域兩端拒收；(8) 金鑰與權杖只走環境變數，測試向量金鑰字面不得 `sk-` 形態；(9) 文件最小化（本檔 ≤1,800 行、≤300KB，每條 AT ≤8 行）；(10) 本檔不寫測試摘要字樣與數字同行。

**User Story 與 AC 對映**

| US ID | User Story | AC ID | 摘要（PRD 座標；規則） |
|-------|------------|-------|-------------------------|
| US-908 | 作為掌舵者，我要在 Console 對待決 PROP 與暫停的運轉下決定（九種動詞、綁卡面 digest、預設拒絕、無批次核准），以便不必把決定貼回對話視窗 | AC-933-1 | PRD AC-SI-33-1；W7～W12、W17、W18：資格、簽章、落檔、真 CLI 收、argv 白名單 |
| US-909 | 作為稽核者，我要每次 Console 決定與帳本寫入都有伺服器端稽核列並可與帳本對帳，以便偵測遺漏與偽造 | AC-933-2、AC-935-5 | PRD AC-SI-33-2、35-5；W11、W13、W14、W21：同型列、待入帳、紅色警示、回填 |
| US-910 | 作為掌舵者，我要在 Console 新增觀察與更正列，並在送出前預檢列規則與位元組數 | AC-935-1、AC-950-3 | PRD AC-SI-35-1；W4、W12、W19 |
| US-911 | 作為掌舵者，我要把處置為 open 的觀察一次關成終值 | AC-935-2 | PRD AC-SI-35-2；W12、W20 |
| US-912 | 作為維護者，我要帳本沒有任何刪除能力 | AC-935-3 | PRD AC-SI-35-3；W3、W10、W21、W23 |
| US-913 | 作為安全審查者，我要只有名單內的 Admin 能寫，金鑰與權杖只走環境變數且不外洩 | AC-935-4、AC-950-5 | PRD AC-SI-35-4；W9、W10 |
| US-914 | 作為維護者，我要 Bridge 的寫入面只落稽核檔，且唯一以寫入形態開檔的模組受鎖 | AC-950-1、950-2、950-4 | W1～W8：設定、落檔、權杖、AST 鎖、跨語言契約 |
| US-915 | 作為維護者，我要 backend 的寫入順序與補償可證、對帳表不可改 | AC-950-6、950-7、950-8 | W11～W15 |
| US-916 | 作為前端維護者與部署者，我要新元件只進 `components/domain/si/`、既有釘選測試同步、部署與 CI 同 commit 收齊 | AC-950-9、950-10、950-11 | W16、W22～W25 |

> 編譯相容提醒：本表第一欄用 US ID，不把 AC ID 放第一欄（`sdd_compile` 會把第一欄形如 AC 的表格列當成 AC→AT 映射列掃描）；除 §1 外沒有任何第一欄以 AC 起頭的表格；AT ID 於 §1 與 §2 的宣告位置之外只出現在說明文字與表格的非第一欄。**§1 表格列的描述格不含豎線字元**（編譯器以豎線切欄）。

**INVEST 自檢**：獨立（只依賴 HEAD 上已存在的根層寫入動詞與 P1b 顯示面）、可協商（⚖ 清單列出可裁決的預設）、有價值（出口 (b) 由 AT 判定；(c) 真機操作由掌舵者做、不由 AT 充當）、可估計（Bridge 1 新模組加 3 新測試檔與 5 個黃金檔；backend 約 12 個新類別加 7 個測試類別；frontend 4 個新元件加 3 個新測試檔（面板的 AT 在既有 `SiView.test.tsx`））、小（零根層碼改動、不新增 NAV 列）、可測（真 CLI 入帳 AT 只用 tmp 倉與本機子行程，不連外網）。

**非功能需求（量化）**

| NFR ID | 內容 | 驗證方式 |
|--------|------|----------|
| NFR-P2b-1 | **逐位元被收**：Console 簽出的稽核 JSON 被真 CLI 收下（黃金檔 G1～G5 入帳 rc 0）；跨語言向量逐字相等 | AC-950-4、AC-933-1／935-1／935-2 的真 CLI AT |
| NFR-P2b-2 | **不留 accept-then-red**：Console 不送出會使根層 `check` 事後轉紅的 body（W12） | AC-950-7 |
| NFR-P2b-3 | 寫入面隔離：Bridge 以寫入形態開 SI 路徑只在 `si_audit.py`；backend 對帳本零直接寫入；Bridge 永不呼叫寫入型 CLI 動詞 | AC-933-1（AST 鎖）、AC-935-3 |
| NFR-P2b-4 | 機密：金鑰與權杖只走環境變數；任何輸出不含其 8 字元以上子字串；`.env.example` 只有佔位 | AC-950-5、AC-950-11；V11 |
| NFR-P2b-5 | 失效可偵測（NFR-SI-09 對稱）：對帳量不到＝NOT-EVALUABLE，絕不顯示無待入帳或空陣列 | AC-935-5 |
| NFR-P2b-6 | 逾時層級：Bridge 子行程 15 秒小於 backend 讀取 20 秒（沿 P1b）；寫入呼叫不重試 | AC-950-3、950-6 |
| NFR-P2b-7 | 跨平台（根鐵律三；`AgentConsole/CLAUDE.md`）：新 Python 的 `open`／`os.open` 帶二進位旗標與 `encoding`、時間帶 tz、平台旗標走 `procutil`；Windows 與 Linux（CI）皆須全綠；macOS 未驗 | 既有 `test_cross_platform_guard.py`；V10 |
| NFR-P2b-8 | 零退化與範圍：既有 AT 在其角色下仍綠，釘選數字只增不減（§4）；只動 §5.7 允許集合 | V8（`git diff --name-only`） |
| NFR-P2b-9 | **開發 agent 交卷前閘門**（輸出逐字貼入）：(1) 本檔各 AT 逐一單跑；(2) Bridge 全套與 `ruff check`（兩視角）；(3) `gradlew clean build`；(4) 前端 lint、tsc、build、vitest；(5) 讀 rc 先存變數；(6) 不 commit、不碰根層與凍結檔；(7) 夾具與測試中的 DEF、OBS、PROP、RUN 編號只准用真帳本已存在者；(8) 不得有 `sk-` 形態字串；(9) 交卷附契約後繼檔全文草稿與 `paths` 逐行清單；(10) 交卷含流程摩擦節 | SCG-4 實跑檢核 V7、V8 |

**追溯矩陣**：F-902 ← PRD FR-SI-33（AC-SI-33-1、33-2）、FR-SI-35（AC-SI-35-1～35-5）、§7.2 動詞表與 Console 段、§9.1〈C18 檔名表〉P2b 列、〈C21〉、§9.2〈Console 稽核 JSON〉、§9.3〈P2b 寫入端點〉、§9.4〈Console 面〉、§9.5 ADR-SI-03′、§8.1 P2b 列、§9.6 P2b 列、附錄 C.2 #12、#16、#18、#20；Architecture §5.4、§8.2、§10.2、§10.3、§11.1、§12.1 L-14；根層 P2 TCS §5.5 與 R94～R97；US-908～US-916 → AC（本檔 FRD-lite）→ AT（本檔 §1）。

**〈增量追溯表〉**（SCG-0～3；「已凍結上位文件」相對 `spec-frozen --root`＝monorepo 根）

| 清單項（閘門／項目） | 追溯 ID | 已凍結上位文件（路徑） | 凍結摘要 |
|---------------------|---------|----------------------|---------|
| SCG-0／PRD 版本已鎖定、FRD 覆蓋、利害關係人已簽核 | PRD v0.10 全文；F-902；FR-SI-33、35；T1 2026-10-24 sid `af29fe90-d902-4763-9d33-eb4d4b98214b` line 13 與 line 94；凍結常態規則（根 `CLAUDE.md`） | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-0／NFR 已量化、User Story INVEST、RTM 初版 | NFR-P2b-1～9；US-908～US-916；本檔 §1 與 §6（RTM 本地子表於 SCG-5 回填） | （本檔；隨 Stage-2 凍結，非上位文件） | n/a（自引） |
| SCG-1／SRD、整合架構、NFR 對應 | Architecture §5.4、§8.2、§10.2、§10.3、§12.1 L-14；子行程與權杖體例沿 ADR-001 D22 | AgentConsole/docs/02_architecture/Architecture.md | sha256:3592e2897ab3d2003f1a8c80263e90fe6cb0b3087deaf9c28b38269290bf055b |
| SCG-1／技術選型與偏離清單 | ADR-001（Spring Boot 4.1、Flyway、Testcontainers PG18、JDBC adapter 體例） | AgentConsole/docs/02_architecture/ADR-001-TechStack-Lock.md | sha256:ff0bcd0038b77e80885240d287cfc68fb55c02200dc59f62f7e59c7691094e38 |
| SCG-2／C4、前端設計系統 | Architecture §1～§3；ADR-002（新對話框與面板沿既有 token 與 `Dialog`、`Field`、`Toast`、`CopyCommand`） | AgentConsole/docs/02_architecture/ADR-002-Frontend-Design-System.md | sha256:d67e450b48f9ace170ec5873c81bca74d915ac1bd15ab496cbbfdea8efffbf36 |
| SCG-2／ADR、Trust Boundary | PRD §9.5 ADR-SI-03′（稽核 JSON＋HMAC＋主機端 CLI 入帳）；Bridge 無認證、只准 backend-net（L-6）；金鑰只在 console-api 與主機 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-3／API Spec 草稿、OpenAPI、錯誤碼、Consumer Contract | Architecture §10.3 簡表與 §11.1 reason 表；本檔 W3～W4、W10、W14～W15（後繼契約 `API_Contract_SelfImproving_P2b.md` 由主控落檔，W25）；凍結的 `API_Contract_P3-6.md` 與 `openapi-p3-6.yaml` 不動 | AgentConsole/docs/02_architecture/API_Contract_P3-6.md | sha256:14097a21263dbfd8fbe72e9630aa58c0cddf8cfc31bd88fac6927a756e02c6af |
| SCG-3／OpenAPI 3.1 完整性 | 機器可讀形狀由 springdoc 的 `/v3/api-docs` 與入庫的 `schema.d.ts` 承擔（AT-950-10-1、AT-950-10-2）；凍結的 openapi 不含 SI 端點 | AgentConsole/docs/02_architecture/openapi-p3-6.yaml | sha256:956539977c70fe6527c7d41162cc49a6d6138c5a49d35d7a43c4852a6bf87823 |
| SCG-3／契約先例與 SI 讀面契約 | P1b 後繼契約（SI 讀面、`SiKeyNames`、`si_not_found` 例外慣例）；P2b 的寫入契約為其後繼 | AgentConsole/docs/02_architecture/API_Contract_SelfImproving_P1b.md | sha256:832ee908acc641da32ef760992240a467f308bed056759a784704f46dbe06f9f |

> 凍結摘要＝該文件在 `frozen_stages[*].spec_doc_digests` 的值，取自 2026-10-24 Stage-1 `spec-frozen` 的真實輸出（任務書逐字列出）；SA 以 `Get-FileHash -Algorithm SHA256` 對工作樹逐檔重算、七檔全部相同（原始位元組與換行正規化後相同）。與該鍵 `show` 的輸出不符時以 `show` 為準並更正本表。

---

## 1. AC → AT 映射表

> **AT ID 文法**：`AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`，前兩段數字＝所屬 AC（見〈AC 編號規則〉）；邊界、錯誤與負控 AT 以 `AT-<NNN>-<Y>-E-<n>` 命名並列於本表。測試類型為 Unit／Integration／Contract；本 Feature 沒有 E2E 類 AT（真全棧、真瀏覽器與掌舵者真機屬 §6.2 的 V 系列）。各 AT 的判定指令與測試檔見 §2 各 AT 標頭。

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-933-1 | 決定載體：九種動詞、綁卡面 digest、預設拒絕、簽章落檔、真 CLI 入帳（PRD AC-SI-33-1） | AT-933-1-1 | （frontend）`decideVerbOptions` 對卡片情境表 M-V 回傳的動詞集合與 dkind 逐列相符，預設不選動詞 | ✅ | Unit | □ |
| AC-933-1 | 決定載體：九種動詞、綁卡面 digest、預設拒絕、簽章落檔、真 CLI 入帳（PRD AC-SI-33-1） | AT-933-1-2 | （frontend）各動詞送出的請求：方法、網址、JSON 本文逐欄，且綁定開啟時的卡面 digest | ✅ | Integration | □ |
| AC-933-1 | 決定載體：九種動詞、綁卡面 digest、預設拒絕、簽章落檔、真 CLI 入帳（PRD AC-SI-33-1） | AT-933-1-3 | （frontend）送出成功後顯示 auditRef 與待入帳指令（兩個 CopyCommand），對話框不自動關閉 | ✅ | Integration | □ |
| AC-933-1 | 決定載體：九種動詞、綁卡面 digest、預設拒絕、簽章落檔、真 CLI 入帳（PRD AC-SI-33-1） | AT-933-1-4 | （backend）decide 端對端：九個 dkind 的有效請求各得 201，Bridge 本文位元組等於黃金檔 | ✅ | Integration | □ |
| AC-933-1 | 決定載體：九種動詞、綁卡面 digest、預設拒絕、簽章落檔、真 CLI 入帳（PRD AC-SI-33-1） | AT-933-1-5 | （Bridge／真 CLI）黃金檔 G1、G2 被真 `decide --carrier console` 收下，事件鍵值逐項如 §5.3 | ✅ | Integration | □ |
| AC-933-1 | 決定載體：九種動詞、綁卡面 digest、預設拒絕、簽章落檔、真 CLI 入帳（PRD AC-SI-33-1） | AT-933-1-6 | （Bridge）AST 鎖對真原始碼通過 W5 的判準 1′～5′ | ✅ | Contract | □ |
| AC-933-1 | 決定載體：九種動詞、綁卡面 digest、預設拒絕、簽章落檔、真 CLI 入帳（PRD AC-SI-33-1） | AT-933-1-E-1 | （frontend）預設拒絕：未選動詞或缺必填欄時送出鈕停用且零請求，沒有批次核准 | ✅ | Integration | □ |
| AC-933-1 | 決定載體：九種動詞、綁卡面 digest、預設拒絕、簽章落檔、真 CLI 入帳（PRD AC-SI-33-1） | AT-933-1-E-2 | （frontend）失敗不關窗、原因逐字：403、409、503、422 各一次，連點只送一次 | ✅ | Integration | □ |
| AC-933-1 | 決定載體：九種動詞、綁卡面 digest、預設拒絕、簽章落檔、真 CLI 入帳（PRD AC-SI-33-1） | AT-933-1-E-3 | （Bridge）AST 鎖負控：違規樣本各自回非空並指出判準，良性樣本回空 | ✅ | Contract | □ |
| AC-933-1 | 決定載體：九種動詞、綁卡面 digest、預設拒絕、簽章落檔、真 CLI 入帳（PRD AC-SI-33-1） | AT-933-1-E-4 | （Bridge／真 CLI）篡改負控：八種變形逐項被真 CLI 拒收，帳本與事件位元組不變 | ✅ | Integration | □ |
| AC-933-2 | 決定稽核列與對帳（PRD AC-SI-33-2） | AT-933-2-1 | （backend）decide 於 DB 寫同型列：欄位逐項正確，body 等於稽核 body，列在 Bridge 呼叫前已存在 | ✅ | Integration | □ |
| AC-933-2 | 決定稽核列與對帳（PRD AC-SI-33-2） | AT-933-2-E-1 | （backend）decide 對帳：有 dec 而無列為紅色警示來源，有列而無 dec 為待入帳 | ✅ | Integration | □ |
| AC-935-1 | 新增觀察：表單、預檢、簽章落檔（PRD AC-SI-35-1） | AT-935-1-1 | （frontend）新增觀察表單：欄位與列舉、守衛面暴露，送出前先 validate 並顯示預估位元組 | ✅ | Integration | □ |
| AC-935-1 | 新增觀察：表單、預檢、簽章落檔（PRD AC-SI-35-1） | AT-935-1-2 | （frontend）送出成功顯示待入帳與入帳指令，並重取對帳資料 | ✅ | Integration | □ |
| AC-935-1 | 新增觀察：表單、預檢、簽章落檔（PRD AC-SI-35-1） | AT-935-1-3 | （backend）obs-add 端對端：有效請求 201，列、Bridge 本文與黃金檔 G3、G4 位元組相同；validate 零副作用 | ✅ | Integration | □ |
| AC-935-1 | 新增觀察：表單、預檢、簽章落檔（PRD AC-SI-35-1） | AT-935-1-4 | （Bridge／真 CLI）G3、G4 被真 obs-add 收下，列與事件逐位元組如 §5.3 | ✅ | Integration | □ |
| AC-935-1 | 新增觀察：表單、預檢、簽章落檔（PRD AC-SI-35-1） | AT-935-1-E-1 | （frontend）即時拒收：豎線與控制字元、空白必填欄、列舉外值 | ✅ | Integration | □ |
| AC-935-1 | 新增觀察：表單、預檢、簽章落檔（PRD AC-SI-35-1） | AT-935-1-E-2 | （frontend）validate 回 ok=false 時不送出：findings 逐字、純文字渲染 | ✅ | Integration | □ |
| AC-935-1 | 新增觀察：表單、預檢、簽章落檔（PRD AC-SI-35-1） | AT-935-1-E-3 | （backend）obs-add 違規一律 422，零副作用（代表樣本） | ✅ | Integration | □ |
| AC-935-1 | 新增觀察：表單、預檢、簽章落檔（PRD AC-SI-35-1） | AT-935-1-E-4 | （Bridge／真 CLI）CLI 拒收碼與 validate 一致：豎線、座標缺、列超長、corrects 不存在、守衛暴露 | ✅ | Integration | □ |
| AC-935-2 | 更新：更正列與處置終值（PRD AC-SI-35-2） | AT-935-2-1 | （frontend）更正列：從觀察列開啟，corrects 預填且唯讀，本文帶 corrects | ✅ | Integration | □ |
| AC-935-2 | 更新：更正列與處置終值（PRD AC-SI-35-2） | AT-935-2-2 | （frontend）關閉對話框：七個終值、各自欄位與送出本文 | ✅ | Integration | □ |
| AC-935-2 | 更新：更正列與處置終值（PRD AC-SI-35-2） | AT-935-2-3 | （backend）close 端對端：終值組成 disposition，Bridge 本文等於黃金檔 G5 | ✅ | Integration | □ |
| AC-935-2 | 更新：更正列與處置終值（PRD AC-SI-35-2） | AT-935-2-4 | （Bridge／真 CLI）G5 被真 obs-close 收下，只動處置欄，其餘位元組逐字不變 | ✅ | Integration | □ |
| AC-935-2 | 更新：更正列與處置終值（PRD AC-SI-35-2） | AT-935-2-E-1 | （frontend）關閉驗證：open 不可選、必填文字、ref 格式、豎線與之後再看 | ✅ | Integration | □ |
| AC-935-2 | 更新：更正列與處置終值（PRD AC-SI-35-2） | AT-935-2-E-2 | （backend）close 違規一律 422，零副作用（代表樣本） | ✅ | Integration | □ |
| AC-935-2 | 更新：更正列與處置終值（PRD AC-SI-35-2） | AT-935-2-E-3 | （Bridge／真 CLI）CLI 拒收關閉：非 open 列、列不存在、處置文法不合，帳本位元組不變 | ✅ | Integration | □ |
| AC-935-3 | 刪除不存在（PRD AC-SI-35-3） | AT-935-3-1 | （backend）ArchUnit：SI 寫入映射只有四個 POST，寫入只經 SiConsoleWriteService，AgentBridge 的 si 方法恰五個 | ✅ | Unit | □ |
| AC-935-3 | 刪除不存在（PRD AC-SI-35-3） | AT-935-3-2 | （frontend）沒有刪除 UI：ADMIN 畫面無刪除、移除、清除類控件，操作只有決定、新增、更正、關閉 | ✅ | Integration | □ |
| AC-935-3 | 刪除不存在（PRD AC-SI-35-3） | AT-935-3-E-1 | （backend）DELETE、PUT、PATCH 矩陣：Admin 與 Operator 得 405，Viewer 得 403，Bridge 零請求 | ✅ | Integration | □ |
| AC-935-3 | 刪除不存在（PRD AC-SI-35-3） | AT-935-3-E-2 | （Bridge）DELETE、PUT、PATCH 對全部 `/si/` 路徑得 405，無檔案、無子行程 | ✅ | Integration | □ |
| AC-935-4 | 寫入資格：Admin 且帳號名在名單內（PRD AC-SI-35-4） | AT-935-4-1 | （backend）資格通過矩陣：Admin 且在名單內，四個 POST 皆放行到用例 | ✅ | Integration | □ |
| AC-935-4 | 寫入資格：Admin 且帳號名在名單內（PRD AC-SI-35-4） | AT-935-4-2 | （frontend）ADMIN 看得到全部寫入控件並發出 console-writes 查詢 | ✅ | Integration | □ |
| AC-935-4 | 寫入資格：Admin 且帳號名在名單內（PRD AC-SI-35-4） | AT-935-4-E-1 | （backend）資格拒收矩陣：401、角色不足、不在名單、名單為空 | ✅ | Integration | □ |
| AC-935-4 | 寫入資格：Admin 且帳號名在名單內（PRD AC-SI-35-4） | AT-935-4-E-2 | （backend）閘門序：先授權、再停用、再輸入；帳號名值域另判，設定齊全時本文違規得 422 且零副作用 | ✅ | Integration | □ |
| AC-935-4 | 寫入資格：Admin 且帳號名在名單內（PRD AC-SI-35-4） | AT-935-4-E-3 | （frontend）非 ADMIN 沒有寫入面：VIEWER 與 OPERATOR 零控件、零 POST、零 console-writes 請求 | ✅ | Integration | □ |
| AC-935-5 | 對帳：待入帳與紅色警示（PRD AC-SI-35-5） | AT-935-5-1 | （backend）console-writes：三種 kind 的 ingested 旗標與欄位集合 | ✅ | Integration | □ |
| AC-935-5 | 對帳：待入帳與紅色警示（PRD AC-SI-35-5） | AT-935-5-2 | （backend）obs-add 的 subject_id 回填：只填 NULL，冪等，只動 Console 自有表 | ✅ | Integration | □ |
| AC-935-5 | 對帳：待入帳與紅色警示（PRD AC-SI-35-5） | AT-935-5-3 | （frontend）待入帳面板：項目、三種 kind 的入帳指令、入帳後消失 | ✅ | Integration | □ |
| AC-935-5 | 對帳：待入帳與紅色警示（PRD AC-SI-35-5） | AT-935-5-E-1 | （backend）orphans：帳本有 carrier=console 項而表無列（dec、obs.close、obs-add 事件與觀察列；排序與去重） | ✅ | Integration | □ |
| AC-935-5 | 對帳：待入帳與紅色警示（PRD AC-SI-35-5） | AT-935-5-E-2 | （backend）對帳量不到：Bridge 503、502、504 與頁數上限皆回 200 加 NOT-EVALUABLE | ✅ | Integration | □ |
| AC-935-5 | 對帳：待入帳與紅色警示（PRD AC-SI-35-5） | AT-935-5-E-3 | （backend）讀面邊界：401、Viewer 可讀、limit 範圍與排序、body 與 mac 不外露、零 Bridge POST | ✅ | Integration | □ |
| AC-935-5 | 對帳：待入帳與紅色警示（PRD AC-SI-35-5） | AT-935-5-E-4 | （frontend）紅色警示與量不到：orphans 顯示警示，NOT-EVALUABLE 時不顯示 無待入帳 | ✅ | Integration | □ |
| AC-950-1 | Bridge 設定與稽核檔落地（本檔自增） | AT-950-1-1 | （Bridge）`load_settings` 對寫入權杖與稽核目錄的解析表，以及寫入面啟用條件 | ✅ | Unit | □ |
| AC-950-1 | Bridge 設定與稽核檔落地（本檔自增） | AT-950-1-2 | （Bridge）`store_audit` 原樣寫入：位元組逐位元相同，檔名為 `<ref>.json`，目錄內恰一檔 | ✅ | Integration | □ |
| AC-950-1 | Bridge 設定與稽核檔落地（本檔自增） | AT-950-1-3 | （Bridge／文件）README 與設定檔頭載明兩個新環境變數、四個 POST 路徑與三個新 reason | ✅ | Contract | □ |
| AC-950-1 | Bridge 設定與稽核檔落地（本檔自增） | AT-950-1-E-1 | （Bridge）同名不覆寫：再寫得 409 且檔案不變；八執行緒搶同名恰一成功 | ✅ | Integration | □ |
| AC-950-1 | Bridge 設定與稽核檔落地（本檔自增） | AT-950-1-E-2 | （Bridge）I/O 失敗：503 si_unavailable 帶 errno，不洩漏路徑，半成品被清除 | ✅ | Integration | □ |
| AC-950-1 | Bridge 設定與稽核檔落地（本檔自增） | AT-950-1-E-3 | （Bridge）檔名安全：非小寫正規 UUID 的 audit_ref 一律拒收，目錄與其上層都不留檔 | ✅ | Unit | □ |
| AC-950-2 | Bridge 三個寫入端點（本檔自增） | AT-950-2-1 | （Bridge）三個寫入端點成功路徑：201 本文鍵集合固定，落檔位元組等於請求位元組 | ✅ | Integration | □ |
| AC-950-2 | Bridge 三個寫入端點（本檔自增） | AT-950-2-2 | （Bridge）不解 body、不驗簽；稽核記錄只含決策且不含權杖值 | ✅ | Integration | □ |
| AC-950-2 | Bridge 三個寫入端點（本檔自增） | AT-950-2-3 | （Bridge）{id} 與外層 subject 相符的合格形態皆放行 | ✅ | Integration | □ |
| AC-950-2 | Bridge 三個寫入端點（本檔自增） | AT-950-2-E-1 | （Bridge）寫入面停用矩陣：權杖或稽核目錄任一未設，三個寫入端點皆 503 si_write_disabled | ✅ | Integration | □ |
| AC-950-2 | Bridge 三個寫入端點（本檔自增） | AT-950-2-E-2 | （Bridge）權杖矩陣：缺、錯、空、近似值皆 403 si_write_forbidden，缺與錯回應相同 | ✅ | Integration | □ |
| AC-950-2 | Bridge 三個寫入端點（本檔自增） | AT-950-2-E-3 | （Bridge）形態違規一律 422 invalid_request 且不落檔 | ✅ | Integration | □ |
| AC-950-2 | Bridge 三個寫入端點（本檔自增） | AT-950-2-E-4 | （Bridge）{id} 與 subject 不符或格式不合得 422；同名 audit_ref 再送得 409 | ✅ | Integration | □ |
| AC-950-3 | 唯讀預檢 validate（本檔自增） | AT-950-3-1 | （Bridge）`run_validate` 的子行程契約：argv、stdin、cwd、環境 | ✅ | Integration | □ |
| AC-950-3 | 唯讀預檢 validate（本檔自增） | AT-950-3-2 | （Bridge）validate 路由：不需權杖，rc 0 與 1 皆 200 並逐值透傳，零檔案 | ✅ | Integration | □ |
| AC-950-3 | 唯讀預檢 validate（本檔自增） | AT-950-3-3 | （Bridge／真 CLI）validate 與真 CLI dry-run 逐值相等，預覽的 row_bytes 等於入帳列位元組數 | ✅ | Integration | □ |
| AC-950-3 | 唯讀預檢 validate（本檔自增） | AT-950-3-E-1 | （Bridge）validate 失敗形態：rc 3、非 JSON、缺鍵、逾時、超量皆 503 si_unavailable 且 cause 固定 | ✅ | Integration | □ |
| AC-950-3 | 唯讀預檢 validate（本檔自增） | AT-950-3-E-2 | （Bridge）validate 請求違規：422 且不啟動子行程 | ✅ | Integration | □ |
| AC-950-4 | 稽核 JSON 契約與跨語言向量（本檔自增） | AT-950-4-1 | （backend）跨語言向量：V1～V4 的 body、mac、key_id、位元組數與外層檔位元組逐字相等 | ✅ | Unit | □ |
| AC-950-4 | 稽核 JSON 契約與跨語言向量（本檔自增） | AT-950-4-2 | （backend）body 鍵序與鍵集合：表 M-D、M-O、M-C 的期望字串逐字相等 | ✅ | Unit | □ |
| AC-950-4 | 稽核 JSON 契約與跨語言向量（本檔自增） | AT-950-4-3 | （Bridge）黃金檔鏈：backend 資源與 Bridge 副本逐位元組相同，且以標準庫可重算 | ✅ | Contract | □ |
| AC-950-4 | 稽核 JSON 契約與跨語言向量（本檔自增） | AT-950-4-E-1 | （backend）負控：改 body 一字、金鑰接 x、Z 時間各自得到 §5.1 的對照值 | ✅ | Unit | □ |
| AC-950-4 | 稽核 JSON 契約與跨語言向量（本檔自增） | AT-950-4-E-2 | （backend）金鑰環語意：第一把簽章，逗號與空白被剝除，key_id 依實際金鑰 | ✅ | Unit | □ |
| AC-950-4 | 稽核 JSON 契約與跨語言向量（本檔自增） | AT-950-4-E-3 | （backend）time 格式邊界：秒精度、±HH:MM、UTC 為 +00:00、毫秒被截 | ✅ | Unit | □ |
| AC-950-5 | backend 設定與金鑰（本檔自增） | AT-950-5-1 | （backend）設定解析：deciders 清單、金鑰環、Bridge 寫入權杖與 toString 遮蔽 | ✅ | Unit | □ |
| AC-950-5 | backend 設定與金鑰（本檔自增） | AT-950-5-E-1 | （backend）啟動失敗：金鑰環任一把過短或為佔位，權杖過短或為佔位，訊息只講長度 | ✅ | Unit | □ |
| AC-950-5 | backend 設定與金鑰（本檔自增） | AT-950-5-E-2 | （backend）機密不外洩：金鑰與權杖不出現在回應、日誌、DB、例外與 details | ✅ | Integration | □ |
| AC-950-6 | backend 寫入用例與介面卡（本檔自增） | AT-950-6-1 | （backend）介面卡請求形態：網址、標頭、本文位元組原樣、逾時 2 與 20 秒、不重試 | ✅ | Unit | □ |
| AC-950-6 | backend 寫入用例與介面卡（本檔自增） | AT-950-6-2 | （backend）Bridge 回應到例外的對映：寫入端點的十二種回應，並區分確定未送達與結果不明 | ✅ | Unit | □ |
| AC-950-6 | backend 寫入用例與介面卡（本檔自增） | AT-950-6-3 | （backend）成功回應與 validate 回應形態：camelCase，鍵集合固定 | ✅ | Integration | □ |
| AC-950-6 | backend 寫入用例與介面卡（本檔自增） | AT-950-6-E-1 | （backend）補償矩陣：Bridge 明確拒絕與 5xx 故障一律刪列並逐字轉出 reason | ✅ | Integration | □ |
| AC-950-6 | backend 寫入用例與介面卡（本檔自增） | AT-950-6-E-2 | （backend）結果不明保留列、確定未送達刪列：讀取逾時、送出後連線重設、201 垃圾本文皆保留並帶 outcomeUnknown；連線被拒刪列 | ✅ | Integration | □ |
| AC-950-6 | backend 寫入用例與介面卡（本檔自增） | AT-950-6-E-3 | （backend）不重試且每次新 audit_ref：同一 payload 連送兩次得兩個不同 ref | ✅ | Integration | □ |
| AC-950-7 | backend 輸入閘（本檔自增） | AT-950-7-1 | （backend）decide 閘：表 M-D 九列的有效組合各通過並產生期望命令 | ✅ | Unit | □ |
| AC-950-7 | backend 輸入閘（本檔自增） | AT-950-7-2 | （backend）觀察與關閉閘：表 M-O、M-C 的有效組合通過，七個終值組成 disposition 逐項相等 | ✅ | Unit | □ |
| AC-950-7 | backend 輸入閘（本檔自增） | AT-950-7-E-1 | （backend）decide 違規：禁止欄、缺必填欄、格式與值域，一次回報全部違規 | ✅ | Unit | □ |
| AC-950-7 | backend 輸入閘（本檔自增） | AT-950-7-E-2 | （backend）觀察違規：欄位、列舉、守衛暴露、字元與長度 | ✅ | Unit | □ |
| AC-950-7 | backend 輸入閘（本檔自增） | AT-950-7-E-3 | （backend）關閉違規：終值、ref、text 與路徑 id；validate 與 obs-add 共用觀察閘 | ✅ | Unit | □ |
| AC-950-8 | Flyway V13 與列不可改（本檔自增） | AT-950-8-1 | （backend）V13 表結構：欄位、型別、可空性、主鍵、檢查約束與升級路徑 | ✅ | Integration | □ |
| AC-950-8 | Flyway V13 與列不可改（本檔自增） | AT-950-8-2 | （backend）表的寫入面只有三條：insert、補償 delete、subject_id 回填 | ✅ | Unit | □ |
| AC-950-8 | Flyway V13 與列不可改（本檔自增） | AT-950-8-E-1 | （backend）列不可改：除 subject_id 由空填值外任何 UPDATE 皆被資料庫拒絕，DELETE 可行 | ✅ | Integration | □ |
| AC-950-8 | Flyway V13 與列不可改（本檔自增） | AT-950-8-E-2 | （backend）約束：重複 audit_ref、kind 非法、key_id 或 mac 長度不符、body 為空皆被拒 | ✅ | Integration | □ |
| AC-950-9 | frontend API 層與純函式（本檔自增） | AT-950-9-1 | （frontend）五個新端點函式：方法、網址、本文與 id 編碼 | ✅ | Unit | □ |
| AC-950-9 | frontend API 層與純函式（本檔自增） | AT-950-9-2 | （frontend）純函式：三個驗證函式、ingestCommands、pendingWrites、siWriteErrorText 與 SI_REASONS | ✅ | Unit | □ |
| AC-950-9 | frontend API 層與純函式（本檔自增） | AT-950-9-3 | （frontend）estimateRowBytes：受控輸入的估計值等於真 CLI 預覽的 row_bytes，表單邊打邊顯示估計值與 row_max_bytes | ✅ | Integration | □ |
| AC-950-9 | frontend API 層與純函式（本檔自增） | AT-950-9-E-1 | （frontend）匯出名稱受限：get 加 Si 恰七個、post 加 Si 恰四個，無 put、patch、delete，總數受同步 | ✅ | Unit | □ |
| AC-950-9 | frontend API 層與純函式（本檔自增） | AT-950-9-E-2 | （frontend）靜態鎖：寫入字樣與表單只准在三個寫入元件，全樹無 HTML 渲染、直接 fetch、Bridge 路徑字面 | ✅ | Unit | □ |
| AC-950-9 | frontend API 層與純函式（本檔自增） | AT-950-9-E-3 | （frontend）估計與即時拒收：含豎線或控制字元不給估計值也不送出，三欄位元組和超過 700 時停用送出 | ✅ | Integration | □ |
| AC-950-10 | 契約面與既有釘選測試同步（本檔自增） | AT-950-10-1 | （backend）OpenAPI：SI 路徑與操作的精確集合與 operationId | ✅ | Contract | □ |
| AC-950-10 | 契約面與既有釘選測試同步（本檔自增） | AT-950-10-2 | （frontend）`schema.d.ts` 含五個新 operationId 與四個新路徑，`gen:api` 指令存在 | ✅ | Contract | □ |
| AC-950-10 | 契約面與既有釘選測試同步（本檔自增） | AT-950-10-E-1 | （frontend）導覽登記表未改：仍七列，ToolsRegion 無入口常數，新元件沒有新增 NAV 列 | ✅ | Unit | □ |
| AC-950-11 | 部署與 CI 連動（本檔自增） | AT-950-11-1 | （Bridge／compose）engine-bridge 恰一個可寫 SI bind（稽核目錄）與新環境變數；backend 三個新環境變數 | ✅ | Contract | □ |
| AC-950-11 | 部署與 CI 連動（本檔自增） | AT-950-11-2 | （Bridge／CI）agentconsole-ci.yml 的 paths 涵蓋寫入閉包的每個根層輸入（兩個觸發器） | ✅ | Contract | □ |
| AC-950-11 | 部署與 CI 連動（本檔自增） | AT-950-11-E-1 | （Bridge／compose）反例：其餘 SI bind 不得可寫，不得掛 repo 根與家目錄，不得發布 ports，.env.example 只有佔位 | ✅ | Contract | □ |
| AC-950-11 | 部署與 CI 連動（本檔自增） | AT-950-11-E-2 | （Bridge／夾具）寫入閉包缺檔時大聲失敗，不退回假 CLI | ✅ | Integration | □ |

**覆蓋率統計**:
- 總 AC 數: 18（PRD 的 7 個加本檔自增 11 個）
- 已映射 AT 數: 98（正控 49、負控與邊界 E 類 49；負控不少於正控）
- 層別分佈: Bridge 32（正控 16、負控 16）；backend 41（正控 19、負控 22）；frontend 25（正控 14、負控 11）
- 映射覆蓋率: 100% （目標: 100%）

---
## 2. 可自動化 AT 格式規範

> **驗收字樣與判定指令**：每個 AT 的最後一個 `And` 行帶一個以雙引號包住的驗收字樣（形態：方括號內為 `AT_OK_` 接 AT 底線形去掉 `AT_` 前綴的部分；E 類的 `E` 保留）；Then、And 行**只有驗收字樣一組引號**，其餘程式碼字面值一律用反引號，引號、撇號與全形引號 `「」` 一律不得出現在 Then、And 行（編譯器的引號字面抽取〔`sdd_to_playbook_adapter.py` 的 `_QUOTED_LITERAL`〕會把被框住的字誤收為期望輸出片段）。本 Feature 走 SDD session-only 路徑（backend 與 frontend；Bridge 可走委派迴圈）：實作者在 session 內自跑判定指令，**把輸出逐字貼進證據**（沒貼＝未驗證），並在最終回覆逐 AT 列出驗收字樣。
>
> **AT 底線形**＝把 AT ID 的連字號換成底線（`AT-935-1-E-4` 的底線形是 `AT_935_1_E_4`）；每個 AT 的測試函式（Java 為方法）名稱須含其底線形；每個 AC 內數字序與 E 序各不超過 9，使 `-k`、`-t`、`--tests` 的子字串比對不會誤收其他 AT。**同一 AT 的子情境**（Given 列舉者）一律以參數化或 `subTest` 實作並保留底線形，任一子情境失敗時，失敗訊息須指出是哪一個。**AT 內不引用其他 AT 的 ID**。**不得新增 skip、xfail 或 `it.skip`／`describe.skip`**：git 或 loopback 埠缺席視為環境壞、直接失敗。
>
> **每個 AT 區塊 8 行**：三行 `#` 標頭（AT ID；對應 AC、PRD 座標與規則；測試類型、自動化工具、判定指令）、`Scenario:`（＝§1 的 AT 描述）、`Given`、`When`、`Then`、帶驗收字樣的 `And`。
>
> **判定指令的三種形態**（標頭只列引數部分；PowerShell 不用裸 `cd`、讀 rc 先存變數再讀）：Bridge（pytest；已啟用根 `.venv`）`python -m pytest tests/<檔> -k <AT 底線形> -q`；backend（Gradle；整合測試需 Docker）`gradlew test --tests "<類別全名>.<AT 底線形>*"`；frontend（vitest）`npx vitest run <檔> -t <AT 底線形>`。

```powershell
Push-Location AgentConsole\engine-bridge; python -m pytest tests/test_si_write_routes.py -k AT_950_2_1 -q; Pop-Location
Push-Location AgentConsole\backend; .\gradlew.bat test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_933_1_4*"; Pop-Location
Push-Location AgentConsole\frontend; npx vitest run components/domain/si/SiDecideDialog.test.tsx -t AT_933_1_2; Pop-Location
```

```bash
(cd AgentConsole/engine-bridge && . ../../.venv/bin/activate && python -m pytest tests/test_si_write_routes.py -k AT_950_2_1 -q)
(cd AgentConsole/backend && ./gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_933_1_4*")
(cd AgentConsole/frontend && npx vitest run components/domain/si/SiDecideDialog.test.tsx -t AT_933_1_2)
```

> **斷言簡寫**（本節各 AT 共用；資料與設施細節見 §5）：
>
> - **Bridge 側**：`STA`＝`make_si_repo(tmp_path, "A", closure=WRITE_CLOSURE)` 的狀態 A 倉；`HOME`＝tmp 內的家目錄（`AUTOSDD_SI_DIR`；真家目錄不得被碰）；`K0`＝§5.1 向量金鑰（`AUTOSDD_SI_AUDIT_KEY`）；`ingest_run` 見 W6；`FK`＝`make_fake_si` 的假 CLI 樹；`BR-LIVE`＝`make_bridge(replace(settings, si_root=…, si_write_token=T0, si_audit_dir=AD))` 起的真 uvicorn（httpx 真 HTTP）；`T0`＝32 字元以上的測試權杖；`AD`＝tmp 內的稽核目錄；`G1`～`G5`＝§5.3 黃金檔。
> - **backend 側**：`SEAM`、`MiniBridge`、`ADMIN` 見 §5.4；HTTP 呼叫沿既有 `AbstractExecutionIT`／`ApiClient`。
> - **frontend 側**：`renderSi(opts)` 與 fetch 替身見 §5.5；表 M-V、M-D、M-O、M-C＝§5.2；`data-testid` 取元素。

```gherkin
# AT-933-1-1
# 對應 AC: AC-933-1（PRD AC-SI-33-1；W17）
# 測試類型: Unit；自動化工具: vitest（jsdom；hermetic）；判定指令: npx vitest run lib/domain/si.test.ts -t AT_933_1_1（cwd＝AgentConsole/frontend）
Scenario: （frontend）`decideVerbOptions` 對卡片情境表 M-V 回傳的動詞集合與 dkind 逐列相符，預設不選動詞
  Given §5.2 表 M-V 的十列卡片情境（state、route、verdict、cooldown，加橫幅 suspended 一列），每列附期望動詞序列
  When 對每列呼叫 `decideVerbOptions`；另取全部 PROP 情境所得 dkind 的聯集
  Then 每列回傳的 `{label,dkind,needsAck}` 序列與期望逐項相同；PROP 情境聯集恰為八個 dkind，加 `resume` 共九個，不多不少；任何列都沒有預設選取項
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_933_1_1]"
```
```gherkin
# AT-933-1-2
# 對應 AC: AC-933-1（PRD AC-SI-33-1；W16、W18）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiDecideDialog.test.tsx -t AT_933_1_2（cwd＝AgentConsole/frontend）
Scenario: （frontend）各動詞送出的請求：方法、網址、JSON 本文逐欄，且綁定開啟時的卡面 digest
  Given `renderSi` 以 ADMIN 開啟決定對話框；`overrides` 依表 M-V 把 `PROP-SI-004` 改寫成各動詞所需的情境（digest 取自狀態 A），fetch 替身記錄請求
  When 依表 M-D 對九個 dkind 各填必填欄後送出（恢復由狀態橫幅開啟、綁 `suspended.run`）
  Then 每次恰一個 POST，網址為 `/api/v1/si/proposals/<id>/decide`，本文鍵集合與值逐項等於表 M-D 該列；`digest` 等於開啟當下卡面 digest；`unverifiedAck` 只在晉升後式出現且為 true；resume 的 id 為 RUN 號且無 `digest`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_933_1_2]"
```
```gherkin
# AT-933-1-3
# 對應 AC: AC-933-1（PRD AC-SI-33-1；W17、W18）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiDecideDialog.test.tsx -t AT_933_1_3（cwd＝AgentConsole/frontend）
Scenario: （frontend）送出成功後顯示 auditRef 與待入帳指令（兩個 CopyCommand），對話框不自動關閉
  Given 替身對 POST 回 201 `{auditRef,kind,subject,time,keyId}`
  When 送出一次核准
  Then `si-decide-result` 含該 `auditRef` 與字樣 待入帳；`si-decide-result` 內 `sdd-recovery-command-powershell` 與 `sdd-recovery-command-posix` 的文字逐字等於 `ingestCommands(decide, PROP-SI-004, auditRef)`；對話框仍開啟；關閉後重開同一張卡不沿用上次結果
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_933_1_3]"
```
```gherkin
# AT-933-1-4
# 對應 AC: AC-933-1（PRD AC-SI-33-1；W7、W10、W11）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_933_1_4*"（cwd＝AgentConsole/backend）
Scenario: （backend）decide 端對端：九個 dkind 的有效請求各得 201，Bridge 本文位元組等於黃金檔
  Given ADMIN 在名單內、金鑰與權杖已設，`SEAM` 固定時鐘、audit_ref 與金鑰（§5.4）
  When 對 `PROP-SI-004` 送 approve 與 reject（表 M-D 的有效本文）；其餘七個 dkind 各送一個有效請求
  Then 九個皆 201；MiniBridge 對 `/si/proposals/<id>:decide` 各收到恰一個 POST；approve 與 reject 的原始本文位元組等於黃金檔 G1、G2；其餘七個的外層 `kind` 為 decide、`subject` 等於路徑 id（resume 為 RUN 號）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_933_1_4]"
```
```gherkin
# AT-933-1-5
# 對應 AC: AC-933-1（PRD AC-SI-33-1；W7、W8）
# 測試類型: Integration；自動化工具: pytest + 真 CLI 子行程 + tmp 倉 + 活 Bridge（hermetic）；判定指令: python -m pytest tests/test_si_console_ingest.py -k AT_933_1_5 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge／真 CLI）黃金檔 G1、G2 被真 `decide --carrier console` 收下，事件鍵值逐項如 §5.3
  Given G1 與 G2 各用一份新的 `STA` 倉（各有自己的 `HOME`、`K0`；同倉先入 G1 後 G2 會因前提態不符被拒），把該檔放進各自的 `HOME/console_audit/`
  When 各自以 `ingest_run` 跑 `decide PROP-SI-004 --carrier console --audit-ref <ref> --json`；入帳前後各跑一次 `check --json`
  Then rc 為 0；`export --kind events` 多一筆 `dec`，鍵集合與值逐項等於 §5.3 表 G1／G2 的事件欄（`carrier` 為 console、`audit_sha256` 等於檔位元組 sha256、`decided_at` 等於 body.time、無 quote、sid、line）；`export --kind proposals` 的 state 依序為 approved 與 rejected；`check --json` 的 fail 集合（扣夾具既有）前後無新增
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_933_1_5]"
```
```gherkin
# AT-933-1-6
# 對應 AC: AC-933-1（PRD AC-SI-33-1；W5）
# 測試類型: Contract；自動化工具: pytest + AST 掃描（hermetic）；判定指令: python -m pytest tests/test_si_readonly_lock.py -k AT_933_1_6 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge）AST 鎖對真原始碼通過 W5 的判準 1′～5′
  Given `app/` 全樹原始碼
  When 跑 `crit1_writes`、`crit2_imports`、`crit3_literal`、`crit4_argv`、`crit5_dynamic`（皆為 W5 的新版判準）
  Then 違規清單為空；掃描範圍含 `si_audit.py`、`si_cli.py`、`routers/si.py`；`si_cli.py` 恰兩個組 argv 函式，動詞集合恰為 export 與 obs-add 加 dry-run
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_933_1_6]"
```
```gherkin
# AT-933-1-E-1
# 對應 AC: AC-933-1（PRD AC-SI-33-1；W18）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiDecideDialog.test.tsx -t AT_933_1_E_1（cwd＝AgentConsole/frontend）
Scenario: （frontend）預設拒絕：未選動詞或缺必填欄時送出鈕停用且零請求，沒有批次核准
  Given ADMIN 開啟待決卡（PASS 與 NE 兩種 verdict 各一張）的決定對話框
  When 不選動詞按送出；逐一選動詞但各缺理由、理由類別或未驗採納勾選；掃描整個 `si-view`
  Then 送出鈕停用、fetch 替身零個 POST，且停用原因文字存在；沒有全部核准、批次核准或不帶 ID 的控件；verdict 為 PASS 的晉升沒有勾選框，NE 的晉升後式在未勾選時停用
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_933_1_E_1]"
```
```gherkin
# AT-933-1-E-2
# 對應 AC: AC-933-1（PRD AC-SI-33-1；W18、W17）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiDecideDialog.test.tsx -t AT_933_1_E_2（cwd＝AgentConsole/frontend）
Scenario: （frontend）失敗不關窗、原因逐字：403、409、503、422 各一次，連點只送一次
  Given 替身對 POST 依序回 403 `si_write_forbidden`、409 `si_audit_exists`、503 `si_write_disabled`、422（violations 兩筆）
  When 每種各送一次（每次連點送出鈕兩下）
  Then toast 文字含該 reason 逐字（422 另含每筆 violation 的 message）；對話框不關閉；送出鈕請求中停用、結束後恢復；每次點擊序列恰一個 POST
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_933_1_E_2]"
```
```gherkin
# AT-933-1-E-3
# 對應 AC: AC-933-1（PRD AC-SI-33-1；W5）
# 測試類型: Contract；自動化工具: pytest + AST 掃描（hermetic）；判定指令: python -m pytest tests/test_si_readonly_lock.py -k AT_933_1_E_3 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge）AST 鎖負控：違規樣本各自回非空並指出判準，良性樣本回空
  Given W5 的違規樣本集（寫入形態在 routers/si.py；si_audit.py 開字面路徑、`Path.home()` 或讀環境；第三個 argv 函式；動詞為 decide、obs-close 或缺 dry-run 的 obs-add；含 `--repo`；第二個模組含腳本字面；`sys.path` 變更）與良性樣本（合規的 si_audit.py 形態）
  When 對每個樣本跑對應判準函式
  Then 違規樣本各自回非空且訊息含判準編號；良性樣本回空
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_933_1_E_3]"
```
```gherkin
# AT-933-1-E-4
# 對應 AC: AC-933-1（PRD AC-SI-33-1；W7）
# 測試類型: Integration；自動化工具: pytest + 真 CLI 子行程 + tmp 倉 + 活 Bridge（hermetic）；判定指令: python -m pytest tests/test_si_console_ingest.py -k AT_933_1_E_4 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge／真 CLI）篡改負控：八種變形逐項被真 CLI 拒收，帳本與事件位元組不變
  Given G1 的八種變形：(1) 改 body 一字；(2) digest 末碼改 0 並重簽；(3) time 換 Z 並重簽；(4) 外層多一鍵；(5) 金鑰環未設；(6) 同一 audit_ref 第二次入帳；(7) 以 `K0` 接 x 簽出的 mac 而 `key_id` 仍為 `K0`；(8) `key_id` 不在環內；變形 1～5、7、8 各用新的 `STA` 倉，變形 6 在同一倉先入 G1 一次再入
  When 各自餵真 CLI（`decide … --json`）
  Then rc 皆為 1 且碼依序為 AUDIT-MAC-MISMATCH、STALE-CARD、AUDIT-TIME-FORMAT、AUDIT-SCHEMA、AUDIT-KEY-MISSING、AUDIT-REF-REUSED、AUDIT-MAC-MISMATCH、AUDIT-KEY-UNKNOWN；每次拒收前後（變形 6 為第二次入帳前後）事件帳本與 OBS 帳本位元組相同
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_933_1_E_4]"
```
```gherkin
# AT-933-2-1
# 對應 AC: AC-933-2（PRD AC-SI-33-2；W11、W13）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_933_2_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）decide 於 DB 寫同型列：欄位逐項正確，body 等於稽核 body，列在 Bridge 呼叫前已存在
  Given 同 933-1-4 的 `SEAM`；MiniBridge 在收到請求的當下以 JDBC 讀 `si_console_writes`
  When 送出 approve
  Then 收到請求當下表內已有該 `audit_ref` 一列；列的 kind 為 decide、user 為 admin、role 為 ADMIN、time 與 body.time 同刻、subject_id 為 PROP-SI-004、digest 為卡面 digest、body 等於外層 body 字串、key_id 與 mac 等於外層；成功後列仍在且表內恰一列
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_933_2_1]"
```
```gherkin
# AT-933-2-E-1
# 對應 AC: AC-933-2（PRD AC-SI-33-2；W14）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWritesReadApiIT.AT_933_2_E_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）decide 對帳：有 dec 而無列為紅色警示來源，有列而無 dec 為待入帳
  Given 表內 decide 列 R1、R3；MiniBridge events 含 R1 的 `dec`（carrier 為 console）與表內沒有的 R2 的 `dec`
  When `GET /api/v1/si/console-writes`
  Then R1 的 `ingested` 為 true、R3 的 `ingested` 為 false；`orphans` 恰含 R2（kind 為 decide、subject 為該 dec 的 prop）；`reconcile.status` 為 ok
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_933_2_E_1]"
```
```gherkin
# AT-935-1-1
# 對應 AC: AC-935-1（PRD AC-SI-35-1；W16、W19）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiObsForm.test.tsx -t AT_935_1_1（cwd＝AgentConsole/frontend）
Scenario: （frontend）新增觀察表單：欄位與列舉、守衛面暴露，送出前先 validate 並顯示預估位元組
  Given ADMIN 開啟新增觀察；替身 validate 回 `{ok:true,row,rowBytes:287,rowMaxBytes:700,findings:[]}`
  When 填六欄與列舉（face 為 產品）後送出；另把 face 改為 守衛
  Then 依序一個 validate POST 然後一個 `/api/v1/si/observations` POST；`si-obs-preview` 顯示 row、287 與 700；兩個本文的欄位逐項等於輸入（`externalDerived` 預設 false、無 exposure）；face 為守衛時 exposure 下拉出現且必填、本文帶 exposure
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_1_1]"
```
```gherkin
# AT-935-1-2
# 對應 AC: AC-935-1（PRD AC-SI-35-1；W17、W19、W21）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiObsForm.test.tsx -t AT_935_1_2（cwd＝AgentConsole/frontend）
Scenario: （frontend）送出成功顯示待入帳與入帳指令，並重取對帳資料
  Given 替身 POST 回 201 `{auditRef,kind:obs-add,subject:null,time,keyId}`
  When 填寫後送出
  Then `si-obs-result` 含 auditRef 與兩個 CopyCommand，指令逐字等於 `ingestCommands(obs-add, null, auditRef)`；表單送出鈕在請求中停用；成功後多一個 `console-writes` GET
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_1_2]"
```
```gherkin
# AT-935-1-3
# 對應 AC: AC-935-1（PRD AC-SI-35-1；W11、W12）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_935_1_3*"（cwd＝AgentConsole/backend）
Scenario: （backend）obs-add 端對端：有效請求 201，列、Bridge 本文與黃金檔 G3、G4 位元組相同；validate 零副作用
  Given 同 `SEAM`；請求本文依 §5.2 表 M-O 的有效範例
  When 送 G3 輸入與 G4 輸入（含 corrects）各一次；另送一次 validate
  Then 兩個 201；Bridge 收到的原始本文位元組等於 G3、G4；DB 列 kind 為 obs-add 且 subject_id 為 null；validate 為 200，不寫 DB、不取 audit_ref，Bridge 收到的是未簽 body（無 mac、key_id、audit_ref）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_1_3]"
```
```gherkin
# AT-935-1-4
# 對應 AC: AC-935-1（PRD AC-SI-35-1；W7、W8）
# 測試類型: Integration；自動化工具: pytest + 真 CLI 子行程 + tmp 倉 + 活 Bridge（hermetic）；判定指令: python -m pytest tests/test_si_console_ingest.py -k AT_935_1_4 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge／真 CLI）G3、G4 被真 obs-add 收下，列與事件逐位元組如 §5.3
  Given G3 與 G4 各用一份新的 `STA` 倉（同倉先入 G3 則 G4 的新列號為 OBS-SI-014），各自入帳
  When 各自跑 `obs-add --carrier console --audit-ref <ref> --json`；入帳前後各跑一次 `check --json`
  Then rc 0；帳本新增一列 OBS-SI-013，文字逐字等於 §5.3 表 G3／G4 的列欄（時間格 2026-10-24 22:30 +08:00；標記依序 面、（rel=corrects）、來源=人、回報者=admin、carrier=console、audit_ref）；事件 obs.add 鍵值如 §5.3；原有各列位元組不變；`check --json` 的 fail 集合（扣夾具既有）前後無新增
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_1_4]"
```
```gherkin
# AT-935-1-E-1
# 對應 AC: AC-935-1（PRD AC-SI-35-1；W19）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiObsForm.test.tsx -t AT_935_1_E_1（cwd＝AgentConsole/frontend）
Scenario: （frontend）即時拒收：豎線與控制字元、空白必填欄、列舉外值
  Given 開啟新增觀察表單
  When 在字串欄輸入豎線、貼上換行與 TAB；context 留空白；檢視 category、severity、face 的選項
  Then 欄位下立即顯示錯誤字樣（豎線與控制字元各一種）、送出鈕停用、零請求；空白必填欄各有錯誤；三個下拉只有表 M-O 的選項
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_1_E_1]"
```
```gherkin
# AT-935-1-E-2
# 對應 AC: AC-935-1（PRD AC-SI-35-1；W19）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiObsForm.test.tsx -t AT_935_1_E_2（cwd＝AgentConsole/frontend）
Scenario: （frontend）validate 回 ok=false 時不送出：findings 逐字、純文字渲染
  Given 替身 validate 回 `ok:false` 與兩筆 findings（detail 之一含 script 標籤字樣）
  When 按送出；改正後再送出
  Then 第一次零個 `/api/v1/si/observations` POST；`si-obs-findings` 逐筆顯示 code 與 detail 的字面文字（不執行、不轉格式）；`si-obs-preview` 仍顯示 row 與位元組；改正且替身回 ok 後再送出得一個 POST
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_1_E_2]"
```
```gherkin
# AT-935-1-E-3
# 對應 AC: AC-935-1（PRD AC-SI-35-1；W12）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_935_1_E_3*"（cwd＝AgentConsole/backend）
Scenario: （backend）obs-add 違規一律 422，零副作用（代表樣本）
  Given 表 M-O 的違規代表樣本：豎線、換行、守衛缺 exposure、三欄位元組和 701
  When 各送 obs-add 與 validate 一次；另送位元組和恰 700 與單欄恰 300 字元的對照
  Then 違規皆 422 `invalid_request` 且 `violations[].field` 含該欄；DB 零列、Bridge 零請求、audit_ref 來源零次取用；對照兩例為 201
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_1_E_3]"
```
```gherkin
# AT-935-1-E-4
# 對應 AC: AC-935-1（PRD AC-SI-35-1；W4、W7）
# 測試類型: Integration；自動化工具: pytest + 真 CLI 子行程 + tmp 倉 + 活 Bridge（hermetic）；判定指令: python -m pytest tests/test_si_console_ingest.py -k AT_935_1_E_4 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge／真 CLI）CLI 拒收碼與 validate 一致：豎線、座標缺、列超長、corrects 不存在、守衛暴露
  Given `STA` 倉、`BR-LIVE`；表 M-O 的 CLI 拒收列
  When 各做成稽核檔入帳，並以同一 body 打 `/si/observations:validate`
  Then 入帳 rc 為 1 且碼依序為 PIPE-IN-FIELD、COORD-NONE、ROW-BYTES-OVER、CORRECTS-NOT-FOUND、EXPOSURE-REQUIRED、EXPOSURE-UNEXPECTED；帳本位元組不變；validate 的 `ok` 為 false 且 findings 的 code 集合逐列等於該 CLI 碼
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_1_E_4]"
```
```gherkin
# AT-935-2-1
# 對應 AC: AC-935-2（PRD AC-SI-35-2；W19、W21）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiObsForm.test.tsx -t AT_935_2_1（cwd＝AgentConsole/frontend）
Scenario: （frontend）更正列：從觀察列開啟，corrects 預填且唯讀，本文帶 corrects
  Given ADMIN 檢視觀察分頁（含一列壞列），按 `si-obs-correct-OBS-SI-001`
  When 填寫後送出
  Then `si-obs-corrects` 預填 `OBS-SI-001` 且唯讀；POST 本文含 `corrects`；壞列（無 id）沒有更正鈕；其餘欄位與新增模式相同
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_2_1]"
```
```gherkin
# AT-935-2-2
# 對應 AC: AC-935-2（PRD AC-SI-35-2；W16、W20）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiObsCloseDialog.test.tsx -t AT_935_2_2（cwd＝AgentConsole/frontend）
Scenario: （frontend）關閉對話框：七個終值、各自欄位與送出本文
  Given ADMIN 對處置恰為 open 的 `OBS-SI-005` 列開啟關閉對話框
  When 對表 M-C 的七個終值各填欄後送出
  Then 終值下拉恰七項且無 open；POST 網址為 `/api/v1/si/observations/OBS-SI-005/close`，本文為 `{terminal,ref?,text?}` 且欄位依表 M-C；deferred、retired、decided 缺 text 時與 ref 類缺 ref 時送出鈕停用；處置不是 open 的列沒有關閉鈕
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_2_2]"
```
```gherkin
# AT-935-2-3
# 對應 AC: AC-935-2（PRD AC-SI-35-2；W11、W12）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_935_2_3*"（cwd＝AgentConsole/backend）
Scenario: （backend）close 端對端：終值組成 disposition，Bridge 本文等於黃金檔 G5
  Given 同 `SEAM`
  When 對 `OBS-SI-005` 送 decided 加 text 夾具關閉；另對七個終值各送一個有效請求
  Then G5 請求得 201 且 Bridge 收到的位元組等於 G5；七個終值組成的 body.disposition 逐項等於表 M-C；DB 列 kind 為 obs-close、subject_id 為 OBS-SI-005
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_2_3]"
```
```gherkin
# AT-935-2-4
# 對應 AC: AC-935-2（PRD AC-SI-35-2；W7、W8）
# 測試類型: Integration；自動化工具: pytest + 真 CLI 子行程 + tmp 倉 + 活 Bridge（hermetic）；判定指令: python -m pytest tests/test_si_console_ingest.py -k AT_935_2_4 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge／真 CLI）G5 被真 obs-close 收下，只動處置欄，其餘位元組逐字不變
  Given 新的 `STA` 倉，G5 入帳
  When 跑 `obs-close --carrier console --audit-ref <ref> --json`；入帳前後各跑一次 `check --json`
  Then rc 0；OBS 帳本前後逐行比對只有 OBS-SI-005 一行、且只有第八欄（處置）變為 `decided：夾具關閉`；行數不變；事件 obs.close 鍵值如 §5.3（含 disposition）；`check --json` 的 fail 集合（扣夾具既有）前後無新增
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_2_4]"
```
```gherkin
# AT-935-2-E-1
# 對應 AC: AC-935-2（PRD AC-SI-35-2；W20）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiObsCloseDialog.test.tsx -t AT_935_2_E_1（cwd＝AgentConsole/frontend）
Scenario: （frontend）關閉驗證：open 不可選、必填文字、ref 格式、豎線與之後再看
  Given 開啟關閉對話框
  When 試 text 為空、含豎線、含 之後再看；試 ref 為不合格式的 sha、DEF、OBS、PROP；試 text 為 121 個字元（120 個為合格的對照）
  Then 每種違規都在欄位下顯示錯誤且送出鈕停用、零請求；合格式的 ref 與 text 解除停用
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_2_E_1]"
```
```gherkin
# AT-935-2-E-2
# 對應 AC: AC-935-2（PRD AC-SI-35-2；W12）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_935_2_E_2*"（cwd＝AgentConsole/backend）
Scenario: （backend）close 違規一律 422，零副作用（代表樣本）
  Given 表 M-C 違規代表：terminal 為 open、decided 缺 text、fixed 的 ref 非十六進位、text 含 之後再看、路徑 id 格式不合
  When 各送一次
  Then 皆 422 `invalid_request` 且 `violations[].field` 含該欄；DB 零列、Bridge 零請求
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_2_E_2]"
```
```gherkin
# AT-935-2-E-3
# 對應 AC: AC-935-2（PRD AC-SI-35-2；W7）
# 測試類型: Integration；自動化工具: pytest + 真 CLI 子行程 + tmp 倉 + 活 Bridge（hermetic）；判定指令: python -m pytest tests/test_si_console_ingest.py -k AT_935_2_E_3 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge／真 CLI）CLI 拒收關閉：非 open 列、列不存在、處置文法不合，帳本位元組不變
  Given `STA` 倉；三個 obs-close 稽核檔：對 `OBS-SI-006`（處置非 open）、對不在帳本的 OBS 號、處置為 retired 而缺座標
  When 各自入帳
  Then rc 皆為 1 且碼依序為 NOT-OPEN、OBS-NOT-FOUND、DISPOSITION-TEXT-MISSING；OBS 與事件帳本位元組前後相同
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_2_E_3]"
```
```gherkin
# AT-935-3-1
# 對應 AC: AC-935-3（PRD AC-SI-35-3；W11、W23）
# 測試類型: Unit；自動化工具: JUnit 5 + ArchUnit（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.architecture.SiReadOnlyArchTest.AT_935_3_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）ArchUnit：SI 寫入映射只有四個 POST，寫入只經 SiConsoleWriteService，AgentBridge 的 si 方法恰五個
  Given `com.aisdlc.console` 主類別
  When 跑改名後的 `AT_935_3_1_…` 方法與既有規則 A1～A6
  Then `Si*Controller` 恰七個 `@GetMapping`、恰四個 `@PostMapping`，無 Put、Patch、Delete 映射；`AgentBridge` 名稱以 si 接大寫起頭的方法恰為 `siExport`、三個 `siWrite…`、`siValidateObservation`；呼叫三個 `siWrite…` 與寫入埠的類別只有 `SiConsoleWriteService`；`SiMirrorQueryService` 不依賴任何寫入埠；既有規則仍綠
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_3_1]"
```
```gherkin
# AT-935-3-2
# 對應 AC: AC-935-3（PRD AC-SI-35-3；W21）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiView.test.tsx -t AT_935_3_2（cwd＝AgentConsole/frontend）
Scenario: （frontend）沒有刪除 UI：ADMIN 畫面無刪除、移除、清除類控件，操作只有決定、新增、更正、關閉
  Given ADMIN 檢視三分頁與狀態橫幅（狀態 A，含一個 suspended 變體）
  When 列舉全部按鈕與連結的可及名稱與 `data-testid`
  Then 名稱與 testid 不含 刪除、移除、清除、delete、remove；寫入類控件的 testid 前綴恰為 `si-decide-open-`、`si-resume-open`、`si-obs-new`、`si-obs-correct-`、`si-close-open-`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_3_2]"
```
```gherkin
# AT-935-3-E-1
# 對應 AC: AC-935-3（PRD AC-SI-35-3；W10）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_935_3_E_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）DELETE、PUT、PATCH 矩陣：Admin 與 Operator 得 405，Viewer 得 403，Bridge 零請求
  Given 六個 backend SI 路徑（前綴 `/api/v1/si`）：`/proposals/PROP-SI-004/decide`、`/observations`、`/observations/OBS-SI-005/close`、`/observations/validate`、`/status`、`/console-writes`
  When 對每個路徑以 Viewer、Operator、Admin 各送 DELETE、PUT、PATCH
  Then Viewer 皆 403；Operator 與 Admin 皆 405；沒有任何 2xx；MiniBridge 零請求；`si_console_writes` 零列
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_3_E_1]"
```
```gherkin
# AT-935-3-E-2
# 對應 AC: AC-935-3（PRD AC-SI-35-3；W3）
# 測試類型: Integration；自動化工具: pytest + 活 Bridge（uvicorn）+ tmp 稽核目錄（hermetic）；判定指令: python -m pytest tests/test_si_write_routes.py -k AT_935_3_E_2 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge）DELETE、PUT、PATCH 對全部 `/si/` 路徑得 405，無檔案、無子行程
  Given `BR-LIVE` 與假 CLI 樹；全部九個 `/si/` 路徑（六個讀路徑加 `:decide`、`:close`、`:validate`；`/si/observations` 同時是讀與寫路徑）
  When 各送 DELETE、PUT、PATCH
  Then 皆 405；`AD` 內零檔案；假 CLI 零呼叫
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_3_E_2]"
```
```gherkin
# AT-935-4-1
# 對應 AC: AC-935-4（PRD AC-SI-35-4；W9、W10）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_935_4_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）資格通過矩陣：Admin 且在名單內，四個 POST 皆放行到用例
  Given `console.si.deciders` 為 `admin,ops_admin`；JWT 為 admin 與 ops_admin（皆 ADMIN 角色）
  When 兩個帳號各送四個 POST 的有效本文
  Then validate 為 200，其餘三個為 201；名單比對區分大小寫：另一個帳號名為 `Admin`（角色 ADMIN）的 JWT 因名單只含小寫 admin 而得 403 `si_write_forbidden`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_4_1]"
```
```gherkin
# AT-935-4-2
# 對應 AC: AC-935-4（PRD AC-SI-35-4；W21）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiView.test.tsx -t AT_935_4_2（cwd＝AgentConsole/frontend）
Scenario: （frontend）ADMIN 看得到全部寫入控件並發出 console-writes 查詢
  Given `renderSi({role: ADMIN})`，狀態 A
  When 檢視 DOM 與請求
  Then 有 `si-obs-new`、每張待決卡的 `si-decide-open-<id>`、處置為 open 的列的 `si-close-open-<id>`、各有效列的 `si-obs-correct-<id>` 與 `si-writes-panel`；請求集合含恰一個 `console-writes` GET
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_4_2]"
```
```gherkin
# AT-935-4-E-1
# 對應 AC: AC-935-4（PRD AC-SI-35-4；W9、W10）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_935_4_E_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）資格拒收矩陣：401、角色不足、不在名單、名單為空
  Given 名單為 `admin`；四個 POST 路徑
  When 無 token、亂碼 token、Viewer、Operator、Admin 但帳號名不在名單、名單設為空後的 admin 各送一次
  Then 依序 401、401、403 `ACCESS_DENIED`、403 `ACCESS_DENIED`、403 `si_write_forbidden`、403 `si_write_forbidden`；Bridge 零請求、DB 零列
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_4_E_1]"
```
```gherkin
# AT-935-4-E-2
# 對應 AC: AC-935-4（PRD AC-SI-35-4；W10、W12）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_935_4_E_2*"（cwd＝AgentConsole/backend）
Scenario: （backend）閘門序：先授權、再停用、再輸入；帳號名值域另判，設定齊全時本文違規得 422 且零副作用
  Given 五例：名單外 admin；名單內 admin 但金鑰未設；名單內 admin 但權杖未設；另一名單內帳號其帳號名含空白；設定齊全且在名單內的 admin
  When 各送一個本文非法的 decide（第五例送 approve 帶 reason、reject 缺 reasonClass 各一次）
  Then 依序 403 `si_write_forbidden`（非 422）、503 `si_write_disabled` 且 `details.cause` 為 audit_key_unset、503 `si_write_disabled` 且 cause 為 bridge_token_unset、422 且 `violations[].field` 含 user、422 `invalid_request` 且 `violations[].field` 含 reason 與 reasonClass；五例全程 DB 零列、Bridge 零請求、`SiAuditRefSource` 零次取用
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_4_E_2]"
```
```gherkin
# AT-935-4-E-3
# 對應 AC: AC-935-4（PRD AC-SI-35-4；W21）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiView.test.tsx -t AT_935_4_E_3（cwd＝AgentConsole/frontend）
Scenario: （frontend）非 ADMIN 沒有寫入面：VIEWER 與 OPERATOR 零控件、零 POST、零 console-writes 請求
  Given `renderSi` 以 VIEWER 與 OPERATOR 各一次（P1b 預設角色 OPERATOR 即此情境）
  When 完整操作（切分頁、篩選、展開、載入更多、重新整理）後檢視 DOM 與請求
  Then DOM 沒有任何 `si-decide-open-`、`si-resume-open`、`si-obs-new`、`si-obs-correct-`、`si-close-open-`、`si-writes-panel`；全部請求為不帶本文的 GET，且不含 `console-writes`；沒有 待入帳 或 紅色警示字樣
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_4_E_3]"
```
```gherkin
# AT-935-5-1
# 對應 AC: AC-935-5（PRD AC-SI-35-5；W14）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWritesReadApiIT.AT_935_5_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）console-writes：三種 kind 的 ingested 旗標與欄位集合
  Given 表內 decide、obs-add、obs-close 各兩列（一列已入帳、一列待入帳）；MiniBridge 的 events 與 observations 含已入帳三列的 audit_ref（dec／obs.add／obs.close 事件，及 `marks_kv.audit_ref`）
  When `GET /api/v1/si/console-writes`
  Then 已入帳三列的 `ingested` 為 true、待入帳三列為 false；`items[]` 鍵集合恰為 auditRef、kind、user、role、time、subjectId、digest、keyId、ingested；`reconcile.status` 為 ok、`truncated` 為 false
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_5_1]"
```
```gherkin
# AT-935-5-2
# 對應 AC: AC-935-5（PRD AC-SI-35-5；W14）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWritesReadApiIT.AT_935_5_2*"（cwd＝AgentConsole/backend）
Scenario: （backend）obs-add 的 subject_id 回填：只填 NULL，冪等，只動 Console 自有表
  Given 表內 obs-add 列 R4（subject_id 為 null）與 R5（已有 subject_id）；observations 含 R4 的 `marks_kv.audit_ref` 對應 `OBS-SI-013`
  When 連續讀兩次 console-writes
  Then R4 的 `subjectId` 變為 `OBS-SI-013` 且 `reconcile.backfilled` 第一次為 1、第二次為 0；R5 不變；除 `si_console_writes.subject_id` 外 DB 無任何寫入；MiniBridge 只收到 GET
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_5_2]"
```
```gherkin
# AT-935-5-3
# 對應 AC: AC-935-5（PRD AC-SI-35-5；W17、W21）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiView.test.tsx -t AT_935_5_3（cwd＝AgentConsole/frontend）
Scenario: （frontend）待入帳面板：項目、三種 kind 的入帳指令、入帳後消失
  Given ADMIN；console-writes 替身回三個待入帳項（decide、obs-add、obs-close）
  When 檢視面板，展開每項的指令；把替身改為已入帳後重新整理
  Then 三項皆列出 kind、subject（obs-add 為 破折號）、time；指令逐字等於 `ingestCommands` 的對應輸出；改為已入帳後 `si-writes-empty` 顯示 無待入帳、無警示
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_5_3]"
```
```gherkin
# AT-935-5-E-1
# 對應 AC: AC-935-5（PRD AC-SI-35-5；W14）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWritesReadApiIT.AT_935_5_E_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）orphans：帳本有 carrier=console 項而表無列（dec、obs.close、obs-add 事件與觀察列；排序與去重）
  Given MiniBridge 的 events（seq 依序遞增）含 carrier 為 console 的 dec、obs.close 與 obs.add（audit_ref 皆不在表），該 obs.add 同 audit_ref 的觀察列也在 observations；observations 另含狀態 A 夾具的 `OBS-SI-009`（標記 carrier=console，其 audit_ref 不在表）
  When `GET /api/v1/si/console-writes`
  Then `orphans` 恰四項：先事件側依 seq 升冪（kind 依序為 decide、obs-close、obs-add，subject 分別為該 dec 的 prop、該 close 的 obs、該 obs.add 的 obs），後觀察列側（`OBS-SI-009` 的 obs-add）；同一 obs-add 的事件與觀察列只計一項；帳本內 carrier 非 console 的項不列入
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_5_E_1]"
```
```gherkin
# AT-935-5-E-2
# 對應 AC: AC-935-5（PRD AC-SI-35-5；W14、W15）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWritesReadApiIT.AT_935_5_E_2*"（cwd＝AgentConsole/backend）
Scenario: （backend）對帳量不到：Bridge 503、502、504 與頁數上限皆回 200 加 NOT-EVALUABLE
  Given 表內三列；MiniBridge 依序設為 503 `si_unavailable`、連線拒絕、讀取逾時、observations 無窮頁（`truncated` 恆真）
  When 各讀一次 console-writes
  Then 四次皆 200，`items` 仍含三列，`reconcile.status` 為 NOT-EVALUABLE 且 `reason` 依序為 si_unavailable、bridge_unreachable、bridge_timeout、scan_cap_exceeded；每列 `ingested` 為 null、`orphans` 為 null；無回填寫入
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_5_E_2]"
```
```gherkin
# AT-935-5-E-3
# 對應 AC: AC-935-5（PRD AC-SI-35-5；W14）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWritesReadApiIT.AT_935_5_E_3*"（cwd＝AgentConsole/backend）
Scenario: （backend）讀面邊界：401、Viewer 可讀、limit 範圍與排序、body 與 mac 不外露、零 Bridge POST
  Given 表內 130 列；三種角色
  When 無 token、Viewer、Operator、Admin 各讀；limit 取預設、1、500、0、501、非數字
  Then 401；其餘 200；預設回 100 列且 `truncated` 為 true、時間新到舊；limit 為 1 與 500 合法；0、501、非數字為 400；回應任何位置都沒有 body、mac 鍵；MiniBridge 的請求全為 GET
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_5_E_3]"
```
```gherkin
# AT-935-5-E-4
# 對應 AC: AC-935-5（PRD AC-SI-35-5；W21）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiView.test.tsx -t AT_935_5_E_4（cwd＝AgentConsole/frontend）
Scenario: （frontend）紅色警示與量不到：orphans 顯示警示，NOT-EVALUABLE 時不顯示 無待入帳
  Given ADMIN；console-writes 替身依序回：含兩個 orphans；`reconcile` 為 NOT-EVALUABLE（reason 為 si_unavailable）；ok 且無待入帳無 orphans
  When 各渲染一次
  Then 第一次 `si-write-alerts` 為 role alert 並逐項顯示 auditRef、kind、subject；第二次顯示 `si-reconcile-ne` 與 reason 逐字、且整頁沒有 無待入帳；第三次才顯示 `si-writes-empty`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_935_5_E_4]"
```
```gherkin
# AT-950-1-1
# 對應 AC: AC-950-1（本檔自增；W1）
# 測試類型: Unit；自動化工具: pytest + 活 Bridge（uvicorn）+ tmp 稽核目錄（hermetic）；判定指令: python -m pytest tests/test_si_write_routes.py -k AT_950_1_1 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge）`load_settings` 對寫入權杖與稽核目錄的解析表，以及寫入面啟用條件
  Given 環境映射表：權杖為未設、全空白、31 字元、32 字元、`<YOUR_SI_TOKEN>`、含 `<YOUR_` 字樣者；稽核目錄為未設、空白、檔案系統根、相對路徑、tmp 絕對路徑
  When 對每列呼叫 `load_settings`
  Then 未設與空白得 None；31 字元、佔位、含 `<YOUR_` 者得 `SettingsError` 且訊息不含值本身；32 字元通過；根目錄得 `SettingsError`；其餘目錄 resolve 為絕對路徑且不進 `allowed_path_roots`；`repr(settings)` 不含權杖；寫入面啟用只在兩者皆非 None
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_1_1]"
```
```gherkin
# AT-950-1-2
# 對應 AC: AC-950-1（本檔自增；W2）
# 測試類型: Integration；自動化工具: pytest + 活 Bridge（uvicorn）+ tmp 稽核目錄（hermetic）；判定指令: python -m pytest tests/test_si_write_routes.py -k AT_950_1_2 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge）`store_audit` 原樣寫入：位元組逐位元相同，檔名為 `<ref>.json`，目錄內恰一檔
  Given tmp 稽核目錄 `AD`；原始位元組為 G3（含 CJK、跳脫引號、無結尾換行）與其結尾加換行、加 CRLF 的兩個變體
  When 對每個變體以新 ref 呼叫 `store_audit(AD, ref, raw)`
  Then `AD/<ref>.json` 位元組與 raw 的 sha256 相等；目錄內檔案數等於呼叫次數、無暫存檔；函式不回傳路徑；以 `os.open` 紀錄器見旗標含 O_CREAT 與 O_EXCL
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_1_2]"
```
```gherkin
# AT-950-1-3
# 對應 AC: AC-950-1（本檔自增；W1、W24）
# 測試類型: Contract；自動化工具: pytest + YAML 與文字解析（hermetic）；判定指令: python -m pytest tests/test_si_deploy_config.py -k AT_950_1_3 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge／文件）README 與設定檔頭載明兩個新環境變數、四個 POST 路徑與三個新 reason
  Given `engine-bridge/README.md` 與 `app/settings.py` 檔頭註解
  When 跑文字檢查函式（含缺項負控樣本）
  Then 兩處都含 `BRIDGE_SI_WRITE_TOKEN` 與 `BRIDGE_SI_AUDIT_DIR`；README 含四個 POST 路徑字面與 `si_write_disabled`、`si_write_forbidden`、`si_audit_exists`；檢查函式對缺項樣本回報缺哪一項
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_1_3]"
```
```gherkin
# AT-950-1-E-1
# 對應 AC: AC-950-1（本檔自增；W2）
# 測試類型: Integration；自動化工具: pytest + 活 Bridge（uvicorn）+ tmp 稽核目錄（hermetic）；判定指令: python -m pytest tests/test_si_write_routes.py -k AT_950_1_E_1 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge）同名不覆寫：再寫得 409 且檔案不變；八執行緒搶同名恰一成功
  Given `AD` 內已有 `<ref>.json`（內容 raw1）；另一組為八個執行緒同時對新 ref 呼叫 `store_audit`
  When 以 raw2 再寫同名；併發寫入
  Then 第一例 `ApiError(409, si_audit_exists)` 且檔案 sha256 仍為 raw1；併發例恰一個成功、七個 409，檔案內容等於成功者的 raw、目錄內恰一檔
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_1_E_1]"
```
```gherkin
# AT-950-1-E-2
# 對應 AC: AC-950-1（本檔自增；W2）
# 測試類型: Integration；自動化工具: pytest + 活 Bridge（uvicorn）+ tmp 稽核目錄（hermetic）；判定指令: python -m pytest tests/test_si_write_routes.py -k AT_950_1_E_2 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge）I/O 失敗：503 si_unavailable 帶 errno，不洩漏路徑，半成品被清除
  Given 三種失敗：目錄不存在；`os.open` 替身拋 EACCES；`os.write` 替身在寫入中途拋 ENOSPC
  When 各呼叫 `store_audit`
  Then 皆 `ApiError(503, si_unavailable)`，cause 為 audit_write_failed，detail 含 `errno=<n>` 與例外類名、不含任何絕對路徑；ENOSPC 例結束後目錄內零檔案；不存在的目錄不會被建立
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_1_E_2]"
```
```gherkin
# AT-950-1-E-3
# 對應 AC: AC-950-1（本檔自增；W2、W3）
# 測試類型: Unit；自動化工具: pytest + 活 Bridge + tmp 稽核目錄（hermetic）；判定指令: python -m pytest tests/test_si_audit_filename_safety.py -k AT_950_1_E_3 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge）檔名安全：非小寫正規 UUID 的 audit_ref 一律拒收，目錄與其上層都不留檔
  Given 非法 ref 表：空字串、`..`、`../x`、含斜線或反斜線、含 NUL、大寫 UUID、UUID 後接 `.json`、UUID 前後空白、36 字元非 UUID、全形數字、Windows 保留名 `con`
  When 對每列呼叫 `store_audit`，並以活 Bridge 的三個寫入端點送外層 audit_ref 為該值的請求
  Then 函式皆 `ValueError`；HTTP 皆 422 `invalid_request`；`AD` 與其上層目錄的檔案清單前後相同；小寫正規 UUID 的對照例成功
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_1_E_3]"
```
```gherkin
# AT-950-2-1
# 對應 AC: AC-950-2（本檔自增；W3）
# 測試類型: Integration；自動化工具: pytest + 活 Bridge（uvicorn）+ tmp 稽核目錄（hermetic）；判定指令: python -m pytest tests/test_si_write_routes.py -k AT_950_2_1 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge）三個寫入端點成功路徑：201 本文鍵集合固定，落檔位元組等於請求位元組
  Given `BR-LIVE`（`T0` 與 `AD` 已設）；G1、G3、G5 的位元組各對 `:decide`、observations、`:close` 端點
  When 帶 `X-Bridge-Token: T0` 發 POST
  Then 皆 201，本文恰 `audit_ref` 與 `stored`（鍵序固定、audit_ref 等於外層、不含路徑）；`AD/<ref>.json` 位元組與請求本文逐位元相同；`AD` 內恰三檔、無其他檔
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_2_1]"
```
```gherkin
# AT-950-2-2
# 對應 AC: AC-950-2（本檔自增；W3）
# 測試類型: Integration；自動化工具: pytest + 活 Bridge（uvicorn）+ tmp 稽核目錄（hermetic）；判定指令: python -m pytest tests/test_si_write_routes.py -k AT_950_2_2 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge）不解 body、不驗簽；稽核記錄只含決策且不含權杖值
  Given `BR-LIVE`；外層 `body` 為字串 not json、`mac` 為 64 個 0（形態合法的假簽章）
  When 帶正確權杖送 decide
  Then 仍 201；Bridge 的稽核 logger 與 `_audit.jsonl` 有 si_write 記錄（含 verb 與結果）且不含權杖值與 mac；權杖以 `hmac.compare_digest` 比對（兩邊為 bytes）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_2_2]"
```
```gherkin
# AT-950-2-3
# 對應 AC: AC-950-2（本檔自增；W3）
# 測試類型: Integration；自動化工具: pytest + 活 Bridge（uvicorn）+ tmp 稽核目錄（hermetic）；判定指令: python -m pytest tests/test_si_write_routes.py -k AT_950_2_3 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge）{id} 與外層 subject 相符的合格形態皆放行
  Given 合格形態：decide 的 `PROP-SI-004` 與 `RUN-SI-001`、close 的 `OBS-SI-005`、obs-add 的 subject 為 null
  When 各送對應外層
  Then 皆 201；路徑 id 為 ASCII 數字三位以上；close 與 decide 的 id 與 subject 相等
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_2_3]"
```
```gherkin
# AT-950-2-E-1
# 對應 AC: AC-950-2（本檔自增；W1、W3）
# 測試類型: Integration；自動化工具: pytest + 活 Bridge（uvicorn）+ tmp 稽核目錄（hermetic）；判定指令: python -m pytest tests/test_si_write_routes.py -k AT_950_2_E_1 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge）寫入面停用矩陣：權杖或稽核目錄任一未設，三個寫入端點皆 503 si_write_disabled
  Given 四種設定（皆未設、只缺權杖、只缺目錄、皆設）；請求本文為垃圾位元組
  When 對三個寫入端點各送（帶與不帶權杖）；另送 GET 與 validate
  Then 前三種設定下寫入端點皆 503 `si_write_disabled`（先於權杖比對與本文驗證）、無檔案、無子行程；GET 與 validate 不受影響；皆設時垃圾本文得 422 而非 503
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_2_E_1]"
```
```gherkin
# AT-950-2-E-2
# 對應 AC: AC-950-2（本檔自增；W3）
# 測試類型: Integration；自動化工具: pytest + 活 Bridge（uvicorn）+ tmp 稽核目錄（hermetic）；判定指令: python -m pytest tests/test_si_write_routes.py -k AT_950_2_E_2 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge）權杖矩陣：缺、錯、空、近似值皆 403 si_write_forbidden，缺與錯回應相同
  Given `BR-LIVE`；權杖為缺標頭、空字串、少一字、多一字、大小寫改一字、含非 ASCII、正確值
  When 對三個端點各送合法外層
  Then 前六種皆 403 `si_write_forbidden` 且回應本文逐位元組相同；正確值 201；被拒請求不落檔、不啟子行程
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_2_E_2]"
```
```gherkin
# AT-950-2-E-3
# 對應 AC: AC-950-2（本檔自增；W3）
# 測試類型: Integration；自動化工具: pytest + 活 Bridge（uvicorn）+ tmp 稽核目錄（hermetic）；判定指令: python -m pytest tests/test_si_write_routes.py -k AT_950_2_E_3 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge）形態違規一律 422 invalid_request 且不落檔
  Given 違規表：非 JSON、陣列、純量、JSON 後接垃圾、非 UTF-8、65537 位元組、外層少一鍵、多一鍵、`schema_rev` 為 2 或字串 1 或 true、`kind` 不等於端點、`audit_ref` 不合、`subject` 為數字、body 或 key_id 或 mac 為非字串
  When 帶正確權杖各送一次
  Then 皆 422 `invalid_request`，`violations[]` 含對應 `field` 與 `rule`；`AD` 零檔案；恰 65536 位元組的合法請求為 201（邊界對照）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_2_E_3]"
```
```gherkin
# AT-950-2-E-4
# 對應 AC: AC-950-2（本檔自增；W3、W2）
# 測試類型: Integration；自動化工具: pytest + 活 Bridge（uvicorn）+ tmp 稽核目錄（hermetic）；判定指令: python -m pytest tests/test_si_write_routes.py -k AT_950_2_E_4 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge）{id} 與 subject 不符或格式不合得 422；同名 audit_ref 再送得 409
  Given 路徑 id 與外層 subject 不相等；id 為小寫 prop 開頭、少於三位數字、OBS 號走 decide 路徑、PROP 號走 close 路徑；obs-add 的 subject 非 null；同一 audit_ref 對 decide 先後送兩次（第二次本文不同）
  When 各送一次
  Then 前述皆 422 `invalid_request`；重送得 409 `si_audit_exists`，檔案仍為第一次的位元組；全程無多餘檔案
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_2_E_4]"
```
```gherkin
# AT-950-3-1
# 對應 AC: AC-950-3（本檔自增；W4）
# 測試類型: Integration；自動化工具: pytest + 假 CLI 樹（hermetic）；判定指令: python -m pytest tests/test_si_cli.py -k AT_950_3_1 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge）`run_validate` 的子行程契約：argv、stdin、cwd、環境
  Given 假 CLI 樹 `FK`；請求位元組含 CJK；寫入設定未設
  When 呼叫 `run_validate(si_root, raw)`
  Then 紀錄的 argv 恰為 `[sys.executable, <FK>/tools/selfimproving.py, obs-add, --dry-run, --body-file, -, --json]`；stdin 位元組等於 raw；cwd 為 si_root；環境只有白名單與固定鍵（無 BRIDGE_ 與 AUTOSDD_ 開頭者）；不帶 `--repo`、`-I`、`-P`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_3_1]"
```
```gherkin
# AT-950-3-2
# 對應 AC: AC-950-3（本檔自增；W4）
# 測試類型: Integration；自動化工具: pytest + 活 Bridge（uvicorn）+ tmp 稽核目錄（hermetic）；判定指令: python -m pytest tests/test_si_write_routes.py -k AT_950_3_2 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge）validate 路由：不需權杖，rc 0 與 1 皆 200 並逐值透傳，零檔案
  Given `BR-LIVE`（寫入設定未設亦可）；假 CLI 的 `dry_run` 旋鈕：rc 0 的物件，與 rc 1 含兩筆 findings 的物件
  When 不帶權杖 POST `/si/observations:validate`
  Then 兩次皆 200，本文逐值等於旋鈕物件（鍵序保留、ok 為 true 與 false）；`AD` 與 repo 零新檔
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_3_2]"
```
```gherkin
# AT-950-3-3
# 對應 AC: AC-950-3（本檔自增；W4、W7）
# 測試類型: Integration；自動化工具: pytest + 真 CLI 子行程 + tmp 倉 + 活 Bridge（hermetic）；判定指令: python -m pytest tests/test_si_console_ingest.py -k AT_950_3_3 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge／真 CLI）validate 與真 CLI dry-run 逐值相等，預覽的 row_bytes 等於入帳列位元組數
  Given `STA` 倉與 `BR-LIVE`；G3 的 body（去掉簽章欄位，含 user、time、audit_ref）作為請求
  When POST validate（另以去掉 `audit_ref` 的同一 body 再預檢一次）；再把 G3 入帳
  Then validate 回 200 且與直接跑 `obs-add --dry-run --body-file - --json` 的 JSON 逐值相等；`row_bytes` 等於 `row` 的 UTF-8 長度；受控輸入（body 帶同一個 audit_ref 與 time）下該 `row` 逐字等於入帳後新增的帳本列，去掉 audit_ref 的預檢其 `row_bytes` 仍等於入帳列位元組數 287；validate 前後倉的 `git status --porcelain` 與家目錄相同
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_3_3]"
```
```gherkin
# AT-950-3-E-1
# 對應 AC: AC-950-3（本檔自增；W4）
# 測試類型: Integration；自動化工具: pytest + 假 CLI 樹（hermetic）；判定指令: python -m pytest tests/test_si_cli.py -k AT_950_3_E_1 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge）validate 失敗形態：rc 3、非 JSON、缺鍵、逾時、超量皆 503 si_unavailable 且 cause 固定
  Given 假 CLI 旋鈕：rc 3；stdout 非 JSON；JSON 缺 `ok` 或 `findings` 非陣列；睡超過逾時（含孫行程）；無窮輸出；另有 SI_ROOT 未設與腳本缺失
  When 各呼叫 `run_validate`
  Then 皆 `ApiError(503, si_unavailable)`，cause 依序為 nonzero_rc、bad_json、bad_shape、timeout（整棵行程樹被終止）、stdout_too_large、si_root_unset、si_script_missing；detail 為 `rc=<n|none>; stderr=<尾段>`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_3_E_1]"
```
```gherkin
# AT-950-3-E-2
# 對應 AC: AC-950-3（本檔自增；W4）
# 測試類型: Integration；自動化工具: pytest + 活 Bridge（uvicorn）+ tmp 稽核目錄（hermetic）；判定指令: python -m pytest tests/test_si_write_routes.py -k AT_950_3_E_2 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge）validate 請求違規：422 且不啟動子行程
  Given `BR-LIVE` 加假 CLI；請求為非 JSON、陣列、純量、65537 位元組、空本文
  When POST validate
  Then 皆 422 `invalid_request`；假 CLI 零呼叫；恰 65536 位元組的合法物件對照得 200
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_3_E_2]"
```
```gherkin
# AT-950-4-1
# 對應 AC: AC-950-4（本檔自增；W7、W8）
# 測試類型: Unit；自動化工具: JUnit 5（純單元；hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.application.service.SiAuditSignerTest.AT_950_4_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）跨語言向量：V1～V4 的 body、mac、key_id、位元組數與外層檔位元組逐字相等
  Given §5.1 向量（金鑰、四組輸入、期望 body 字串、mac、外層位元組數與 sha256）
  When 以 `SiAuditSigner` 用向量輸入現算
  Then 四組的 body 字串逐字、mac、key_id（f076edf0）、body 位元組數（281、355、380、227）、外層位元組數與 sha256 全部等於 §5.1；外層鍵序為 schema_rev、kind、audit_ref、subject、body、key_id、mac，緊湊、無結尾換行
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_4_1]"
```
```gherkin
# AT-950-4-2
# 對應 AC: AC-950-4（本檔自增；W7）
# 測試類型: Unit；自動化工具: JUnit 5（純單元；hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.application.service.SiAuditSignerTest.AT_950_4_2*"（cwd＝AgentConsole/backend）
Scenario: （backend）body 鍵序與鍵集合：表 M-D、M-O、M-C 的期望字串逐字相等
  Given 表 M-D（九個 dkind）、表 M-O（有無 exposure、有無 corrects）、表 M-C（七個終值）的輸入與期望 body 字串
  When 以 signer 組 body
  Then 全部逐字相等；`flags` 恆在、僅 promote 可含 `unverified_ack`；`digest` 只在六個 dkind；`reason_class` 只在 reject、decline-promote、return；`reason` 只在五個 dkind；obs-add 的 exposure 緊接 face、corrects 在最後
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_4_2]"
```
```gherkin
# AT-950-4-3
# 對應 AC: AC-950-4（本檔自增；W8）
# 測試類型: Contract；自動化工具: pytest + 真 CLI 子行程 + tmp 倉 + 活 Bridge（hermetic）；判定指令: python -m pytest tests/test_si_console_ingest.py -k AT_950_4_3 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge）黃金檔鏈：backend 資源與 Bridge 副本逐位元組相同，且以標準庫可重算
  Given `backend/src/test/resources/si/audit/` 與 `tests/fixtures/si_audit/` 的 G1～G5
  When 逐檔比對，並以 `hmac` 加 `hashlib` 重算
  Then 兩處檔名集合與 sha256 逐檔相同且等於 §5.3 表；每檔外層恰七鍵、`body` 為字串、mac 與 key_id 以 `K0` 重算相等；任一不同時失敗訊息指出哪一份
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_4_3]"
```
```gherkin
# AT-950-4-E-1
# 對應 AC: AC-950-4（本檔自增；W7）
# 測試類型: Unit；自動化工具: JUnit 5（純單元；hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.application.service.SiAuditSignerTest.AT_950_4_E_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）負控：改 body 一字、金鑰接 x、Z 時間各自得到 §5.1 的對照值
  Given §5.1 負控三列（V1 的 dkind 改 reject、金鑰加 x、time 換 Z）
  When 現算 mac 與格式化
  Then 負控一的正確 mac 為 `7801839b…`、負控二為 `e4a88cff…`，皆不等於 V1 原值；signer 與 time formatter 永遠不產出 Z 形態：以 UTC 瞬間格式化得 `+00:00`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_4_E_1]"
```
```gherkin
# AT-950-4-E-2
# 對應 AC: AC-950-4（本檔自增；W7、W9）
# 測試類型: Unit；自動化工具: JUnit 5（純單元；hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.application.service.SiAuditSignerTest.AT_950_4_E_2*"（cwd＝AgentConsole/backend）
Scenario: （backend）金鑰環語意：第一把簽章，逗號與空白被剝除，key_id 依實際金鑰
  Given 環字串 `  k1 , ,k2` 與只有空項的環；k1、k2 為不同的 32 字元以上字串
  When 解析環並簽 V1 body
  Then 簽章用 k1、key_id 為 sha256(k1) 前 8 碼；k2 保留但不簽；全為空項的環視同未設；環序改為 k2 先則 key_id 與 mac 隨之改變
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_4_E_2]"
```
```gherkin
# AT-950-4-E-3
# 對應 AC: AC-950-4（本檔自增；W7）
# 測試類型: Unit；自動化工具: JUnit 5（純單元；hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.application.service.SiAuditSignerTest.AT_950_4_E_3*"（cwd＝AgentConsole/backend）
Scenario: （backend）time 格式邊界：秒精度、±HH:MM、UTC 為 +00:00、毫秒被截
  Given `Clock` 固定在 UTC、+08:00、-05:30 三個時區與含毫秒的瞬間
  When 格式化 time
  Then 輸出恆為 `yyyy-MM-ddTHH:mm:ss` 接 `±HH:MM`；UTC 為 `+00:00`；毫秒被截斷、不四捨五入；與 §5.1 向量 time 字串同形
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_4_E_3]"
```
```gherkin
# AT-950-5-1
# 對應 AC: AC-950-5（本檔自增；W9）
# 測試類型: Unit；自動化工具: JUnit 5（純單元；hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.infrastructure.config.SiWritePropertiesTest.AT_950_5_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）設定解析：deciders 清單、金鑰環、Bridge 寫入權杖與 toString 遮蔽
  Given 屬性值：deciders 為 ` admin , ops ,,admin`；金鑰環 `k1,k2`（各 32 字元以上）；權杖 64 字元；另有各自未設的情形
  When 綁定 `console.si.*` 與 `console.bridge.si-write-token`
  Then deciders 為 admin、ops（去空白、去空項、去重、保序）；環為 k1、k2；預設 deciders 為空、金鑰與權杖未設且寫入面停用；`toString` 對金鑰與權杖只輸出 set 或 unset 標記
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_5_1]"
```
```gherkin
# AT-950-5-E-1
# 對應 AC: AC-950-5（本檔自增；W9）
# 測試類型: Unit；自動化工具: JUnit 5（純單元；hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.infrastructure.config.SiWritePropertiesTest.AT_950_5_E_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）啟動失敗：金鑰環任一把過短或為佔位，權杖過短或為佔位，訊息只講長度
  Given 金鑰環含一把短於 32 字元者、金鑰為 `<YOUR_KEY>`、權杖 31 字元、權杖為 `<YOUR_TOKEN>`
  When 綁定屬性
  Then 皆拋 `IllegalArgumentException`，訊息含屬性名與長度或序號、不含任何金鑰或權杖字元（掃描 8 字元以上的子字串）；既有 `BridgePropertiesTest` 的斷言一個不改弱
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_5_E_1]"
```
```gherkin
# AT-950-5-E-2
# 對應 AC: AC-950-5（本檔自增；W9、W11）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_950_5_E_2*"（cwd＝AgentConsole/backend）
Scenario: （backend）機密不外洩：金鑰與權杖不出現在回應、日誌、DB、例外與 details
  Given 金鑰環與權杖設為可辨識的 40 字元隨機字面；擷取 logback 輸出
  When 跑一次成功寫入、一次 Bridge 403、一次 Bridge 503、一次逾時
  Then 四次的 HTTP 回應本文與標頭、`si_console_writes` 與 `audit_log` 全部列、擷取的日誌都不含金鑰或權杖的任何 8 字元以上子字串（權杖只出現在送往 MiniBridge 的 `X-Bridge-Token` 標頭）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_5_E_2]"
```
```gherkin
# AT-950-6-1
# 對應 AC: AC-950-6（本檔自增；W11、W15）
# 測試類型: Unit；自動化工具: JUnit 5 + MockRestServiceServer（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.out.bridge.BridgeHttpAdapterSiWriteTest.AT_950_6_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）介面卡請求形態：網址、標頭、本文位元組原樣、逾時 2 與 20 秒、不重試
  Given `MockRestServiceServer`；四個新方法 `siWriteDecide`、`siWriteObservation`、`siWriteObservationClose`、`siValidateObservation`
  When 各呼叫一次（id 含需編碼字元者另測）
  Then 網址依序為 `<base>/si/proposals/<id>:decide`、`/si/observations`、`/si/observations/<id>:close`、`/si/observations:validate`（id 嚴格 percent-encode 成單一路徑段）；前三者帶 `X-Bridge-Token`、validate 不帶；本文位元組等於傳入字串的 UTF-8（不經 Jackson 重新序列化）；連線逾時 2 秒、讀取 20 秒；每次失敗恰一次請求
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_6_1]"
```
```gherkin
# AT-950-6-2
# 對應 AC: AC-950-6（本檔自增；W11、W15）
# 測試類型: Unit；自動化工具: JUnit 5 + MockRestServiceServer（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.out.bridge.BridgeHttpAdapterSiWriteTest.AT_950_6_2*"（cwd＝AgentConsole/backend）
Scenario: （backend）Bridge 回應到例外的對映：寫入端點的十二種回應，並區分確定未送達與結果不明
  Given Bridge 回 201、503 si_write_disabled、403 si_write_forbidden、409 si_audit_exists、422 invalid_request、503 si_unavailable、500、500 加非 JSON 本文、連線被拒、送出後連線被重設、讀取逾時、201 加非 JSON 本文
  When 介面卡處理各回應
  Then 201 解出 audit_ref 與 stored；503 si_write_disabled、403、409、422（含 violations）、503 si_unavailable（含 cause 與 detail）皆為 BridgeRejectedException（status 與 reason 原樣）；兩種 500 為 Failure（bridgeStatus 為 500）；連線被拒為 Unavailable 且確定未送達；送出後連線被重設為 Unavailable 且結果不明（旗標或子類，形態不鎖）；讀取逾時為 TimedOut；201 加非 JSON 本文為 Failure（bridgeStatus 為 200）；權杖不出現在任何例外訊息
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_6_2]"
```
```gherkin
# AT-950-6-3
# 對應 AC: AC-950-6（本檔自增；W11、W15）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_950_6_3*"（cwd＝AgentConsole/backend）
Scenario: （backend）成功回應與 validate 回應形態：camelCase，鍵集合固定
  Given `SEAM`；MiniBridge 回 201 與 validate 的 snake_case 物件
  When 送 decide、obs-add、close 與 validate
  Then 三個寫入的 `data` 鍵集合恰為 auditRef、kind、subject、time、keyId（obs-add 的 subject 為 null）；validate 的 `data` 為 ok、row、rowBytes、rowMaxBytes、findings（每筆 code、detail），值逐項等於 Bridge 物件；回應不含 body、mac
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_6_3]"
```
```gherkin
# AT-950-6-E-1
# 對應 AC: AC-950-6（本檔自增；W11、W15）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_950_6_E_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）補償矩陣：Bridge 明確拒絕與 5xx 故障一律刪列並逐字轉出 reason
  Given MiniBridge 依序回 403 si_write_forbidden、409 si_audit_exists、503 si_write_disabled、503 si_unavailable（含 cause 與 detail）、422、500
  When 各送一次 decide
  Then 回應依序為 403、409、503、503（details 含 cause 與 detail 逐字）、422（頂層 reason 為既有的 引擎拒絕此請求，details.bridgeReason 為 invalid_request）、502；每次之後 `si_console_writes` 為零列；每次 Bridge 恰一個請求
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_6_E_1]"
```
```gherkin
# AT-950-6-E-2
# 對應 AC: AC-950-6（本檔自增；W11、W15）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_950_6_E_2*"（cwd＝AgentConsole/backend）
Scenario: （backend）結果不明保留列、確定未送達刪列：讀取逾時、送出後連線重設、201 垃圾本文皆保留並帶 outcomeUnknown；連線被拒刪列
  Given 以測試用 request factory 縮短讀取逾時，MiniBridge 延遲回應；另三例：MiniBridge 收到請求後直接關閉連線、MiniBridge 回 201 加非 JSON 本文、MiniBridge 已關閉（連線被拒）
  When 各送一次 obs-add
  Then 逾時例 504；送出後重設與 201 垃圾本文兩例皆 502；這三例表內都保留恰一列（該 audit_ref）、`details.outcomeUnknown` 為 true，之後 console-writes 顯示其待入帳；連線被拒例 502、表內零列、details 無 outcomeUnknown
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_6_E_2]"
```
```gherkin
# AT-950-6-E-3
# 對應 AC: AC-950-6（本檔自增；W11）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_950_6_E_3*"（cwd＝AgentConsole/backend）
Scenario: （backend）不重試且每次新 audit_ref：同一 payload 連送兩次得兩個不同 ref
  Given MiniBridge 先回 503 si_unavailable 再回 201
  When 以同一 payload 送兩次
  Then 第一次 503 且零列、第二次 201；兩次 Bridge 請求各一個且 audit_ref 不同；請求總數為 2（沒有自動重試）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_6_E_3]"
```
```gherkin
# AT-950-7-1
# 對應 AC: AC-950-7（本檔自增；W12）
# 測試類型: Unit；自動化工具: JUnit 5（純單元；hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.application.service.SiWriteGatesTest.AT_950_7_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）decide 閘：表 M-D 九列的有效組合各通過並產生期望命令
  Given 表 M-D 的九個有效請求（含 reason 恰 500 個 code point、含全形字元與標點、前後空白）
  When 對每列呼叫 decide 閘
  Then 全數通過且命令的 dkind、subject、digest、reason、reasonClass、flags 等於表列；reason 前後空白被剝除；長度以 code point 計（代理對字元算一個）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_7_1]"
```
```gherkin
# AT-950-7-2
# 對應 AC: AC-950-7（本檔自增；W12）
# 測試類型: Unit；自動化工具: JUnit 5（純單元；hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.application.service.SiWriteGatesTest.AT_950_7_2*"（cwd＝AgentConsole/backend）
Scenario: （backend）觀察與關閉閘：表 M-O、M-C 的有效組合通過，七個終值組成 disposition 逐項相等
  Given 表 M-O 的有效範例（有無 exposure、有無 corrects）與表 M-C 的七列
  When 呼叫觀察閘與關閉閘
  Then 皆通過；觀察命令的字串欄已 trim；七個終值組成的 disposition 逐字等於表 M-C 的期望（含 `fixed@2b2b0b3d`、`DEF-200-559`、`merged@OBS-SI-001`、`proposed@PROP-SI-004` 與三個加文字的終值）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_7_2]"
```
```gherkin
# AT-950-7-E-1
# 對應 AC: AC-950-7（本檔自增；W12）
# 測試類型: Unit；自動化工具: JUnit 5（純單元；hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.application.service.SiWriteGatesTest.AT_950_7_E_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）decide 違規：禁止欄、缺必填欄、格式與值域，一次回報全部違規
  Given 違規表：digest 出現在 rollback、unblock、resume；reason 出現在 approve、promote、ack-handoff、unblock；reasonClass 出現在非三類 dkind；unverifiedAck 為 true 於非 promote；缺 digest、缺 reason、缺 reasonClass；digest 非 sha256 加 64 個小寫十六進位；reason 全空白、含 LF、CR、TAB、NUL、DEL、501 個字元；reasonClass 不在七值；dkind 為 approve-all；resume 配 PROP 號、其餘配 RUN 號
  When 各呼叫 decide 閘
  Then 皆形態違規且 `violations[].field` 為對應欄（dkind、digest、reason、reasonClass、unverifiedAck、id）；同一請求的多項違規一次全列，不只回報第一項
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_7_E_1]"
```
```gherkin
# AT-950-7-E-2
# 對應 AC: AC-950-7（本檔自增；W12）
# 測試類型: Unit；自動化工具: JUnit 5（純單元；hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.application.service.SiWriteGatesTest.AT_950_7_E_2*"（cwd＝AgentConsole/backend）
Scenario: （backend）觀察違規：欄位、列舉、守衛暴露、字元與長度
  Given 表 M-O 的違規欄：三個字串欄之一為空白、含豎線、含 LF、CR、TAB、NUL、DEL；單欄 301 字元；三欄位元組和 701；category、severity、face、exposure 不在列舉；守衛缺 exposure、非守衛帶 exposure；corrects 不合 `OBS-SI-` 加三位以上數字；externalDerived 缺
  When 呼叫觀察閘
  Then 皆形態違規且 `violations[].field` 為對應欄；位元組和以 UTF-8 計；恰 700 與單欄恰 300 字元的對照通過
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_7_E_2]"
```
```gherkin
# AT-950-7-E-3
# 對應 AC: AC-950-7（本檔自增；W12）
# 測試類型: Unit；自動化工具: JUnit 5（純單元；hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.application.service.SiWriteGatesTest.AT_950_7_E_3*"（cwd＝AgentConsole/backend）
Scenario: （backend）關閉違規：終值、ref、text 與路徑 id；validate 與 obs-add 共用觀察閘
  Given 表 M-C 的違規欄：terminal 為 open 或七值之外；ref 類缺 ref、fixed 的 ref 短於 7 或長於 40 或非小寫十六進位、DEF 格式不合、merged 非 OBS 號、proposed 非 PROP 號；deferred、retired、decided 缺 text 或帶 ref；text 含豎線、控制字元、之後再看、超過 120 個字元（121 個為違規，120 個為合格對照）；路徑 id 不合格式
  When 呼叫關閉閘；另以同一組觀察違規餵 validate 與 obs-add 的閘
  Then 皆形態違規且 `violations[].field` 為對應欄；恰 120 個字元的 text 通過；validate 與 obs-add 對同一輸入得同一組 violations
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_7_E_3]"
```
```gherkin
# AT-950-8-1
# 對應 AC: AC-950-8（本檔自增；W13）
# 測試類型: Integration；自動化工具: JUnit 5 + Testcontainers PG（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.infrastructure.persistence.SiConsoleWritesMigrationIT.AT_950_8_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）V13 表結構：欄位、型別、可空性、主鍵、檢查約束與升級路徑
  Given 由 V12 資料庫（含既有資料）升級到 V13；以 `information_schema` 查詢
  When 讀 `console.si_console_writes` 的欄位與約束
  Then 十個欄位名逐字為 audit_ref（uuid、主鍵）、kind、user、role、time（timestamptz）、subject_id（可空）、digest（可空）、body、key_id（8 字元）、mac（64 字元），其餘 NOT NULL；kind 的 CHECK 只收 decide、obs-add、obs-close；升級後既有表資料不變，Flyway 歷史含版本 13 且全部成功
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_8_1]"
```
```gherkin
# AT-950-8-2
# 對應 AC: AC-950-8（本檔自增；W13、W23）
# 測試類型: Unit；自動化工具: JUnit 5 + ArchUnit（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.architecture.SiReadOnlyArchTest.AT_950_8_2*"（cwd＝AgentConsole/backend）
Scenario: （backend）表的寫入面只有三條：insert、補償 delete、subject_id 回填
  Given 主類別與原始碼文字
  When ArchUnit 與原始碼掃描
  Then 存取 `si_console_writes` 的類別只有一個 persistence adapter；其 port 的方法為 insert、deleteByAuditRef、fillSubjectId 與唯讀查詢；原始碼對該表的 UPDATE 敘述恰一條且只設 subject_id；沒有 TRUNCATE 或其他 DML
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_8_2]"
```
```gherkin
# AT-950-8-E-1
# 對應 AC: AC-950-8（本檔自增；W13）
# 測試類型: Integration；自動化工具: JUnit 5 + Testcontainers PG（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.infrastructure.persistence.SiConsoleWritesMigrationIT.AT_950_8_E_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）列不可改：除 subject_id 由空填值外任何 UPDATE 皆被資料庫拒絕，DELETE 可行
  Given 表內一列 obs-add（subject_id 為 NULL）
  When 依序 UPDATE 各欄、把 subject_id 由 NULL 改成值、再改成另一值、最後 DELETE
  Then UPDATE audit_ref、kind、user、role、time、digest、body、key_id、mac 各自被觸發器拒絕；NULL 改為值成功；值改為另一值被拒；DELETE 成功（補償路徑）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_8_E_1]"
```
```gherkin
# AT-950-8-E-2
# 對應 AC: AC-950-8（本檔自增；W13）
# 測試類型: Integration；自動化工具: JUnit 5 + Testcontainers PG（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.infrastructure.persistence.SiConsoleWritesMigrationIT.AT_950_8_E_2*"（cwd＝AgentConsole/backend）
Scenario: （backend）約束：重複 audit_ref、kind 非法、key_id 或 mac 長度不符、body 為空皆被拒
  Given 空表
  When 插入一列合法資料，再依序插入同 audit_ref、kind 為 delete、key_id 為 7 字元、mac 為 63 字元、body 為 NULL 的列
  Then 後五次皆被約束拒絕；表內仍恰一列
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_8_E_2]"
```
```gherkin
# AT-950-9-1
# 對應 AC: AC-950-9（本檔自增；W16）
# 測試類型: Unit；自動化工具: vitest（jsdom；hermetic）；判定指令: npx vitest run lib/api/si.endpoints.test.ts -t AT_950_9_1（cwd＝AgentConsole/frontend）
Scenario: （frontend）五個新端點函式：方法、網址、本文與 id 編碼
  Given fetch 替身；`postSiDecide`、`postSiObservation`、`postSiObservationClose`、`postSiObservationValidate`、`getSiConsoleWrites`
  When 各呼叫一次（id 含需編碼字元者另測）
  Then 方法與網址依序為 `POST /api/v1/si/proposals/<seg>/decide`、`POST /api/v1/si/observations`、`POST /api/v1/si/observations/<seg>/close`、`POST /api/v1/si/observations/validate`、`GET /api/v1/si/console-writes?limit=<n>`；POST 本文逐位元組等於輸入的 `JSON.stringify`；id 以 `encodeURIComponent` 編成單一路徑段；GET 不帶本文
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_9_1]"
```
```gherkin
# AT-950-9-2
# 對應 AC: AC-950-9（本檔自增；W17）
# 測試類型: Unit；自動化工具: vitest（jsdom；hermetic）；判定指令: npx vitest run lib/domain/si.test.ts -t AT_950_9_2（cwd＝AgentConsole/frontend）
Scenario: （frontend）純函式：三個驗證函式、ingestCommands、pendingWrites、siWriteErrorText 與 SI_REASONS
  Given 表驅動輸入：各函式的有效與違規樣本，及 Architecture §11.1 表中 `si_` 起頭的 reason 列
  When 呼叫 `validateDecideForm`、`validateObservationForm`、`validateCloseForm`、`ingestCommands`、`pendingWrites`、`siWriteErrorText`
  Then 驗證函式的錯誤欄位集合與 W12 逐列相同（前端與 backend 同表）；`ingestCommands` 三種 kind 的輸出逐字如 W17；`pendingWrites` 只回 `ingested` 為 false 者且依 time 升冪、null 與 true 不回；`siWriteErrorText` 含 reason 逐字（422 另含各 message）；`SI_REASONS` 恰含該表五個 reason 且逐字相同
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_9_2]"
```
```gherkin
# AT-950-9-3
# 對應 AC: AC-950-9（本檔自增；W17、W19）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiObsForm.test.tsx -t AT_950_9_3（cwd＝AgentConsole/frontend）
Scenario: （frontend）estimateRowBytes：受控輸入的估計值等於真 CLI 預覽的 row_bytes，表單邊打邊顯示估計值與 row_max_bytes
  Given ADMIN 開啟新增觀察表單；受控輸入＝表 M-O 的 O1、O2、O3（下一個 OBS 號為 3 位數、user 為 admin），對照值為真 CLI dry-run 的 `row_bytes`：O1 為 287、O2 為 317、O3 為 311
  When 對三例呼叫 `estimateRowBytes`；另在表單逐欄輸入 O1 並於每次輸入後讀 `si-obs-estimate`；再送出並讓 validate 替身回對照值
  Then 三例估計值依序為 287、317、311；`si-obs-estimate` 隨輸入更新並同時顯示 `rowMaxBytes` 700，輸入途中零個網路請求；送出後 `si-obs-preview` 的 `rowBytes` 等於估計值，validate 回 ok 之後才發出寫入 POST
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_9_3]"
```
```gherkin
# AT-950-9-E-1
# 對應 AC: AC-950-9（本檔自增；W16、W23）
# 測試類型: Unit；自動化工具: vitest（jsdom；hermetic）；判定指令: npx vitest run lib/api/si.endpoints.test.ts -t AT_950_9_E_1（cwd＝AgentConsole/frontend）
Scenario: （frontend）匯出名稱受限：get 加 Si 恰七個、post 加 Si 恰四個，無 put、patch、delete，總數受同步
  Given `lib/api/endpoints.ts` 的匯出名稱表
  When 掃描以 get、post、put、patch、delete 加 Si 起頭者；讀既有 `endpoints.test.ts` 的總數釘選
  Then 恰七個 `getSi*`（原六個加 `getSiConsoleWrites`）與四個 `postSi*`；沒有 `putSi*`、`patchSi*`、`deleteSi*`；`endpoints.test.ts` 的總數由 74 改為 79、`EXPECTED` 加五列（只增不減）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_9_E_1]"
```
```gherkin
# AT-950-9-E-2
# 對應 AC: AC-950-9（本檔自增；W22）
# 測試類型: Unit；自動化工具: vitest（jsdom；hermetic）；判定指令: npx vitest run components/domain/si/si.static.test.ts -t AT_950_9_E_2（cwd＝AgentConsole/frontend）
Scenario: （frontend）靜態鎖：寫入字樣與表單只准在三個寫入元件，全樹無 HTML 渲染、直接 fetch、Bridge 路徑字面
  Given `components/domain/si/**` 與 `app/self-improving/**` 的非測試原始碼
  When 讀檔掃描（掃描器含負控樣本且範圍非空）
  Then `<form`、mutation hook 呼叫與非 GET 字樣只出現在 `SiDecideDialog.tsx`、`SiObsForm.tsx`、`SiObsCloseDialog.tsx`；全樹無 `dangerouslySetInnerHTML`、Markdown 或 HTML 渲染器 import、直接 `fetch(`、以 `/si/` 起頭的字串字面、8081 與 BRIDGE 字樣、delete／PUT／PATCH 方法字樣；負控樣本各自回非空
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_9_E_2]"
```
```gherkin
# AT-950-9-E-3
# 對應 AC: AC-950-9（本檔自增；W17、W19）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiObsForm.test.tsx -t AT_950_9_E_3（cwd＝AgentConsole/frontend）
Scenario: （frontend）估計與即時拒收：含豎線或控制字元不給估計值也不送出，三欄位元組和超過 700 時停用送出
  Given ADMIN 開啟新增觀察表單；三例輸入：欄位含豎線、欄位含換行與 TAB、三欄位元組和 701；另有三欄位元組和恰 700 的對照例
  When 逐例輸入並讀 `si-obs-estimate` 與 `si-obs-submit`
  Then 前兩例 `estimateRowBytes` 回拒收（無估計值），欄位下顯示錯誤、送出鈕停用、零個請求（含 validate）；第三例送出鈕停用，估計值大於 `rowMaxBytes` 時顯示超限警示；恰 700 的對照例送出鈕可用（超限警示不阻擋，送出時才走 validate，權威是 validate 與 CLI）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_9_E_3]"
```
```gherkin
# AT-950-10-1
# 對應 AC: AC-950-10（本檔自增；W23）
# 測試類型: Contract；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.infrastructure.config.OpenApiIT.AT_950_10_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）OpenAPI：SI 路徑與操作的精確集合與 operationId
  Given `/v3/api-docs`
  When 解析 paths
  Then 路徑數為 71、操作總數為 81；`/api/v1/si/observations` 為 get 與 post；新路徑 `/api/v1/si/proposals/{id}/decide`、`/api/v1/si/observations/{id}/close`、`/api/v1/si/observations/validate` 皆只有 post，`/api/v1/si/console-writes` 只有 get；五個新 operationId 為 `postSiDecide`、`postSiObservation`、`postSiObservationClose`、`postSiObservationValidate`、`getSiConsoleWrites`；SI 路徑沒有 delete、put、patch
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_10_1]"
```
```gherkin
# AT-950-10-2
# 對應 AC: AC-950-10（本檔自增；W23）
# 測試類型: Contract；自動化工具: vitest（jsdom；hermetic）；判定指令: npx vitest run lib/api/si.endpoints.test.ts -t AT_950_10_2（cwd＝AgentConsole/frontend）
Scenario: （frontend）`schema.d.ts` 含五個新 operationId 與四個新路徑，`gen:api` 指令存在
  Given `lib/api/schema.d.ts` 與 `package.json`
  When 字串搜尋
  Then 含四個新路徑字串與五個新 operationId；`/api/v1/si/observations` 有 get 與 post；`/api/v1/si/` 路徑無 delete、put、patch；`gen:api` 腳本存在
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_10_2]"
```
```gherkin
# AT-950-10-E-1
# 對應 AC: AC-950-10（本檔自增；W21、W23）
# 測試類型: Unit；自動化工具: vitest（jsdom；hermetic）；判定指令: npx vitest run lib/nav/registry.test.ts -t AT_950_10_E_1（cwd＝AgentConsole/frontend）
Scenario: （frontend）導覽登記表未改：仍七列，ToolsRegion 無入口常數，新元件沒有新增 NAV 列
  Given `lib/nav/registry.ts`、`components/layout/ToolsRegion.tsx`、`layout.test.tsx`
  When 既有 AT 與讀檔斷言
  Then `NAV_REGISTRY` 恰七項且各欄與 P1b 的值相同（`self-improving` 的 mobile 仍為 false）；`ToolsRegion.tsx` 不含入口常數；零變更由 V8 以 `git diff --name-only` 核對
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_10_E_1]"
```
```gherkin
# AT-950-11-1
# 對應 AC: AC-950-11（本檔自增；W24）
# 測試類型: Contract；自動化工具: pytest + YAML 與文字解析（hermetic）；判定指令: python -m pytest tests/test_si_deploy_config.py -k AT_950_11_1 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge／compose）engine-bridge 恰一個可寫 SI bind（稽核目錄）與新環境變數；backend 三個新環境變數
  Given `AgentConsole/docker-compose.yml`
  When 解析檔案
  Then engine-bridge 的 `BRIDGE_SI_AUDIT_DIR` 指向容器內路徑且恰有一條對應 bind（長語法、非唯讀、source 以 `console_audit` 結尾）；`BRIDGE_SI_WRITE_TOKEN` 以 `${BRIDGE_SI_WRITE_TOKEN:-}` 插值；backend 有 `BRIDGE_SI_WRITE_TOKEN`、`CONSOLE_SI_DECIDERS`、`CONSOLE_SI_AUDIT_KEY` 三個插值且預設皆為空；其餘 SI bind 仍全為唯讀、既有掛載保留
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_11_1]"
```
```gherkin
# AT-950-11-2
# 對應 AC: AC-950-11（本檔自增；W24）
# 測試類型: Contract；自動化工具: pytest + YAML 與文字解析（hermetic）；判定指令: python -m pytest tests/test_si_deploy_config.py -k AT_950_11_2 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge／CI）agentconsole-ci.yml 的 paths 涵蓋寫入閉包的每個根層輸入（兩個觸發器）
  Given `WRITE_CLOSURE`（`CLI_CLOSURE` 加 `tools/lib/apply_lock.py` 與 `tools/lib/sdd_latest.py`）、`PARAMS_SRC` 與 `.github/workflows/agentconsole-ci.yml`
  When 跑涵蓋檢查函式（含負控樣本）
  Then 每個輸入都被 pull_request 與 push 兩處的 paths 涵蓋（D10 由主控同 commit 補上之前本 AT 為預期紅）；負控樣本（缺檔案、缺目錄 glob、只有一個觸發器、glob 只涵蓋單層）各自回報缺哪一項
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_11_2]"
```
```gherkin
# AT-950-11-E-1
# 對應 AC: AC-950-11（本檔自增；W24）
# 測試類型: Contract；自動化工具: pytest + YAML 與文字解析（hermetic）；判定指令: python -m pytest tests/test_si_deploy_config.py -k AT_950_11_E_1 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge／compose）反例：其餘 SI bind 不得可寫，不得掛 repo 根與家目錄，不得發布 ports，.env.example 只有佔位
  Given 九種壞變體：稽核 bind 為短語法、稽核 bind 為唯讀、第二條可寫 SI bind、可寫掛 repo 根、掛整個家目錄、`create_host_path` 為真、engine-bridge 發布 ports、`.env.example` 含真值字樣、缺稽核 env
  When 跑檢查函式
  Then 各自回報；真檔回空；`.env.example` 對三個新變數只有 `<YOUR_…>` 佔位，且全檔無機密形態字面（含 sk- 起頭 20 字元以上者）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_11_E_1]"
```
```gherkin
# AT-950-11-E-2
# 對應 AC: AC-950-11（本檔自增；W6）
# 測試類型: Integration；自動化工具: pytest + 真 CLI 子行程 + tmp 倉 + 活 Bridge（hermetic）；判定指令: python -m pytest tests/test_si_console_ingest.py -k AT_950_11_E_2 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （Bridge／夾具）寫入閉包缺檔時大聲失敗，不退回假 CLI
  Given `WRITE_CLOSURE` 移除 `apply_lock.py`；另一例移除 `sdd_latest.py`
  When `make_si_repo(closure=…)` 後跑 `ingest_run`
  Then 建構器或首次入帳拋出清楚例外，訊息含 `WRITE_CLOSURE` 與缺失的檔名；完整閉包時成功
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_950_11_E_2]"
```

---

## 3. AT 完整清單

### 3.1 Unit Tests

| AT ID | 對應 AC | 層 | 測試方法 |
|-------|---------|----|---------|
| AT-933-1-1 | AC-933-1 | frontend | lib/domain/si.test.ts（it 標題 AT_933_1_1…） |
| AT-935-3-1 | AC-935-3 | backend | SiReadOnlyArchTest.AT_935_3_1_* |
| AT-950-1-1 | AC-950-1 | Bridge | tests/test_si_write_routes.py::test_AT_950_1_1_* |
| AT-950-1-E-3 | AC-950-1 | Bridge | tests/test_si_audit_filename_safety.py::test_AT_950_1_E_3_* |
| AT-950-4-1 | AC-950-4 | backend | SiAuditSignerTest.AT_950_4_1_* |
| AT-950-4-2 | AC-950-4 | backend | SiAuditSignerTest.AT_950_4_2_* |
| AT-950-4-E-1 | AC-950-4 | backend | SiAuditSignerTest.AT_950_4_E_1_* |
| AT-950-4-E-2 | AC-950-4 | backend | SiAuditSignerTest.AT_950_4_E_2_* |
| AT-950-4-E-3 | AC-950-4 | backend | SiAuditSignerTest.AT_950_4_E_3_* |
| AT-950-5-1 | AC-950-5 | backend | SiWritePropertiesTest.AT_950_5_1_* |
| AT-950-5-E-1 | AC-950-5 | backend | SiWritePropertiesTest.AT_950_5_E_1_* |
| AT-950-6-1 | AC-950-6 | backend | BridgeHttpAdapterSiWriteTest.AT_950_6_1_* |
| AT-950-6-2 | AC-950-6 | backend | BridgeHttpAdapterSiWriteTest.AT_950_6_2_* |
| AT-950-7-1 | AC-950-7 | backend | SiWriteGatesTest.AT_950_7_1_* |
| AT-950-7-2 | AC-950-7 | backend | SiWriteGatesTest.AT_950_7_2_* |
| AT-950-7-E-1 | AC-950-7 | backend | SiWriteGatesTest.AT_950_7_E_1_* |
| AT-950-7-E-2 | AC-950-7 | backend | SiWriteGatesTest.AT_950_7_E_2_* |
| AT-950-7-E-3 | AC-950-7 | backend | SiWriteGatesTest.AT_950_7_E_3_* |
| AT-950-8-2 | AC-950-8 | backend | SiReadOnlyArchTest.AT_950_8_2_* |
| AT-950-9-1 | AC-950-9 | frontend | lib/api/si.endpoints.test.ts（it 標題 AT_950_9_1…） |
| AT-950-9-2 | AC-950-9 | frontend | lib/domain/si.test.ts（it 標題 AT_950_9_2…） |
| AT-950-9-E-1 | AC-950-9 | frontend | lib/api/si.endpoints.test.ts（it 標題 AT_950_9_E_1…） |
| AT-950-9-E-2 | AC-950-9 | frontend | components/domain/si/si.static.test.ts（it 標題 AT_950_9_E_2…） |
| AT-950-10-E-1 | AC-950-10 | frontend | lib/nav/registry.test.ts（it 標題 AT_950_10_E_1…） |

### 3.2 Integration Tests

| AT ID | 對應 AC | 層 | 測試方法 |
|-------|---------|----|---------|
| AT-933-1-2 | AC-933-1 | frontend | components/domain/si/SiDecideDialog.test.tsx（it 標題 AT_933_1_2…） |
| AT-933-1-3 | AC-933-1 | frontend | components/domain/si/SiDecideDialog.test.tsx（it 標題 AT_933_1_3…） |
| AT-933-1-4 | AC-933-1 | backend | SiConsoleWriteApiIT.AT_933_1_4_* |
| AT-933-1-5 | AC-933-1 | Bridge | tests/test_si_console_ingest.py::test_AT_933_1_5_* |
| AT-933-1-E-1 | AC-933-1 | frontend | components/domain/si/SiDecideDialog.test.tsx（it 標題 AT_933_1_E_1…） |
| AT-933-1-E-2 | AC-933-1 | frontend | components/domain/si/SiDecideDialog.test.tsx（it 標題 AT_933_1_E_2…） |
| AT-933-1-E-4 | AC-933-1 | Bridge | tests/test_si_console_ingest.py::test_AT_933_1_E_4_* |
| AT-933-2-1 | AC-933-2 | backend | SiConsoleWriteApiIT.AT_933_2_1_* |
| AT-933-2-E-1 | AC-933-2 | backend | SiConsoleWritesReadApiIT.AT_933_2_E_1_* |
| AT-935-1-1 | AC-935-1 | frontend | components/domain/si/SiObsForm.test.tsx（it 標題 AT_935_1_1…） |
| AT-935-1-2 | AC-935-1 | frontend | components/domain/si/SiObsForm.test.tsx（it 標題 AT_935_1_2…） |
| AT-935-1-3 | AC-935-1 | backend | SiConsoleWriteApiIT.AT_935_1_3_* |
| AT-935-1-4 | AC-935-1 | Bridge | tests/test_si_console_ingest.py::test_AT_935_1_4_* |
| AT-935-1-E-1 | AC-935-1 | frontend | components/domain/si/SiObsForm.test.tsx（it 標題 AT_935_1_E_1…） |
| AT-935-1-E-2 | AC-935-1 | frontend | components/domain/si/SiObsForm.test.tsx（it 標題 AT_935_1_E_2…） |
| AT-935-1-E-3 | AC-935-1 | backend | SiConsoleWriteApiIT.AT_935_1_E_3_* |
| AT-935-1-E-4 | AC-935-1 | Bridge | tests/test_si_console_ingest.py::test_AT_935_1_E_4_* |
| AT-935-2-1 | AC-935-2 | frontend | components/domain/si/SiObsForm.test.tsx（it 標題 AT_935_2_1…） |
| AT-935-2-2 | AC-935-2 | frontend | components/domain/si/SiObsCloseDialog.test.tsx（it 標題 AT_935_2_2…） |
| AT-935-2-3 | AC-935-2 | backend | SiConsoleWriteApiIT.AT_935_2_3_* |
| AT-935-2-4 | AC-935-2 | Bridge | tests/test_si_console_ingest.py::test_AT_935_2_4_* |
| AT-935-2-E-1 | AC-935-2 | frontend | components/domain/si/SiObsCloseDialog.test.tsx（it 標題 AT_935_2_E_1…） |
| AT-935-2-E-2 | AC-935-2 | backend | SiConsoleWriteApiIT.AT_935_2_E_2_* |
| AT-935-2-E-3 | AC-935-2 | Bridge | tests/test_si_console_ingest.py::test_AT_935_2_E_3_* |
| AT-935-3-2 | AC-935-3 | frontend | components/domain/si/SiView.test.tsx（it 標題 AT_935_3_2…） |
| AT-935-3-E-1 | AC-935-3 | backend | SiConsoleWriteApiIT.AT_935_3_E_1_* |
| AT-935-3-E-2 | AC-935-3 | Bridge | tests/test_si_write_routes.py::test_AT_935_3_E_2_* |
| AT-935-4-1 | AC-935-4 | backend | SiConsoleWriteApiIT.AT_935_4_1_* |
| AT-935-4-2 | AC-935-4 | frontend | components/domain/si/SiView.test.tsx（it 標題 AT_935_4_2…） |
| AT-935-4-E-1 | AC-935-4 | backend | SiConsoleWriteApiIT.AT_935_4_E_1_* |
| AT-935-4-E-2 | AC-935-4 | backend | SiConsoleWriteApiIT.AT_935_4_E_2_* |
| AT-935-4-E-3 | AC-935-4 | frontend | components/domain/si/SiView.test.tsx（it 標題 AT_935_4_E_3…） |
| AT-935-5-1 | AC-935-5 | backend | SiConsoleWritesReadApiIT.AT_935_5_1_* |
| AT-935-5-2 | AC-935-5 | backend | SiConsoleWritesReadApiIT.AT_935_5_2_* |
| AT-935-5-3 | AC-935-5 | frontend | components/domain/si/SiView.test.tsx（it 標題 AT_935_5_3…） |
| AT-935-5-E-1 | AC-935-5 | backend | SiConsoleWritesReadApiIT.AT_935_5_E_1_* |
| AT-935-5-E-2 | AC-935-5 | backend | SiConsoleWritesReadApiIT.AT_935_5_E_2_* |
| AT-935-5-E-3 | AC-935-5 | backend | SiConsoleWritesReadApiIT.AT_935_5_E_3_* |
| AT-935-5-E-4 | AC-935-5 | frontend | components/domain/si/SiView.test.tsx（it 標題 AT_935_5_E_4…） |
| AT-950-1-2 | AC-950-1 | Bridge | tests/test_si_write_routes.py::test_AT_950_1_2_* |
| AT-950-1-E-1 | AC-950-1 | Bridge | tests/test_si_write_routes.py::test_AT_950_1_E_1_* |
| AT-950-1-E-2 | AC-950-1 | Bridge | tests/test_si_write_routes.py::test_AT_950_1_E_2_* |
| AT-950-2-1 | AC-950-2 | Bridge | tests/test_si_write_routes.py::test_AT_950_2_1_* |
| AT-950-2-2 | AC-950-2 | Bridge | tests/test_si_write_routes.py::test_AT_950_2_2_* |
| AT-950-2-3 | AC-950-2 | Bridge | tests/test_si_write_routes.py::test_AT_950_2_3_* |
| AT-950-2-E-1 | AC-950-2 | Bridge | tests/test_si_write_routes.py::test_AT_950_2_E_1_* |
| AT-950-2-E-2 | AC-950-2 | Bridge | tests/test_si_write_routes.py::test_AT_950_2_E_2_* |
| AT-950-2-E-3 | AC-950-2 | Bridge | tests/test_si_write_routes.py::test_AT_950_2_E_3_* |
| AT-950-2-E-4 | AC-950-2 | Bridge | tests/test_si_write_routes.py::test_AT_950_2_E_4_* |
| AT-950-3-1 | AC-950-3 | Bridge | tests/test_si_cli.py::test_AT_950_3_1_* |
| AT-950-3-2 | AC-950-3 | Bridge | tests/test_si_write_routes.py::test_AT_950_3_2_* |
| AT-950-3-3 | AC-950-3 | Bridge | tests/test_si_console_ingest.py::test_AT_950_3_3_* |
| AT-950-3-E-1 | AC-950-3 | Bridge | tests/test_si_cli.py::test_AT_950_3_E_1_* |
| AT-950-3-E-2 | AC-950-3 | Bridge | tests/test_si_write_routes.py::test_AT_950_3_E_2_* |
| AT-950-5-E-2 | AC-950-5 | backend | SiConsoleWriteApiIT.AT_950_5_E_2_* |
| AT-950-6-3 | AC-950-6 | backend | SiConsoleWriteApiIT.AT_950_6_3_* |
| AT-950-6-E-1 | AC-950-6 | backend | SiConsoleWriteApiIT.AT_950_6_E_1_* |
| AT-950-6-E-2 | AC-950-6 | backend | SiConsoleWriteApiIT.AT_950_6_E_2_* |
| AT-950-6-E-3 | AC-950-6 | backend | SiConsoleWriteApiIT.AT_950_6_E_3_* |
| AT-950-8-1 | AC-950-8 | backend | SiConsoleWritesMigrationIT.AT_950_8_1_* |
| AT-950-8-E-1 | AC-950-8 | backend | SiConsoleWritesMigrationIT.AT_950_8_E_1_* |
| AT-950-8-E-2 | AC-950-8 | backend | SiConsoleWritesMigrationIT.AT_950_8_E_2_* |
| AT-950-9-3 | AC-950-9 | frontend | components/domain/si/SiObsForm.test.tsx（it 標題 AT_950_9_3…） |
| AT-950-9-E-3 | AC-950-9 | frontend | components/domain/si/SiObsForm.test.tsx（it 標題 AT_950_9_E_3…） |
| AT-950-11-E-2 | AC-950-11 | Bridge | tests/test_si_console_ingest.py::test_AT_950_11_E_2_* |

### 3.3 Contract Tests（靜態與契約面檢查）

| AT ID | 對應 AC | 層 | 測試方法 |
|-------|---------|----|---------|
| AT-933-1-6 | AC-933-1 | Bridge | tests/test_si_readonly_lock.py::test_AT_933_1_6_* |
| AT-933-1-E-3 | AC-933-1 | Bridge | tests/test_si_readonly_lock.py::test_AT_933_1_E_3_* |
| AT-950-1-3 | AC-950-1 | Bridge | tests/test_si_deploy_config.py::test_AT_950_1_3_* |
| AT-950-4-3 | AC-950-4 | Bridge | tests/test_si_console_ingest.py::test_AT_950_4_3_* |
| AT-950-10-1 | AC-950-10 | backend | OpenApiIT.AT_950_10_1_* |
| AT-950-10-2 | AC-950-10 | frontend | lib/api/si.endpoints.test.ts（it 標題 AT_950_10_2…） |
| AT-950-11-1 | AC-950-11 | Bridge | tests/test_si_deploy_config.py::test_AT_950_11_1_* |
| AT-950-11-2 | AC-950-11 | Bridge | tests/test_si_deploy_config.py::test_AT_950_11_2_* |
| AT-950-11-E-1 | AC-950-11 | Bridge | tests/test_si_deploy_config.py::test_AT_950_11_E_1_* |

### 3.4 E2E Tests

（無 AT；真全棧、真瀏覽器、真容器與掌舵者真機屬 §6.2 的 V 系列，結果寫進 SCG-4 報告。）

---

## 4. 邊界與錯誤測試規格

容錯與邊界情境已併入各 AC 的 E 類 AT 與帶負控的 AT（`AT-<NNN>-<Y>-E-<n>`，列於 §1）；本節依場景分類登記，並登記刻意不做、已知邊界與需同步的既有測試。

| 場景類型 | AT ID | 描述 | 輸入 | 預期結果 |
|---------|-------|------|------|---------|
| 簽章篡改（真 CLI） | AT-933-1-E-4 | G1 的八種變形逐項被真 CLI 拒收且帳本位元組不變 | 改 body 一字、digest 末碼改 0、time 換 Z、外層多一鍵、金鑰環未設、同 ref 二次入帳、金鑰接 x 簽 mac 而 key_id 不變、key_id 不在環內 | rc 1；八碼依序為 AUDIT-MAC-MISMATCH、STALE-CARD、AUDIT-TIME-FORMAT、AUDIT-SCHEMA、AUDIT-KEY-MISSING、AUDIT-REF-REUSED、AUDIT-MAC-MISMATCH、AUDIT-KEY-UNKNOWN |
| 向量負控 | AT-950-4-E-1 | 改一字、金鑰接 x、Z 時間各得 §5.1 的對照 mac | V1 變形 | 對照值與 V1 原值不同；formatter 永不產 Z |
| 金鑰環與時間 | AT-950-4-E-2、AT-950-4-E-3 | 環第一把簽、空白與空項剝除；秒精度與偏移形態 | `  k1 , ,k2`；UTC、+08:00、負半小時偏移、含毫秒 | key_id 依第一把；毫秒截斷不進位；UTC 為 +00:00 |
| 落檔邊界 | AT-950-1-2、AT-950-1-E-1、AT-950-1-E-2、AT-950-1-E-3 | 位元組原樣（含結尾換行與 CRLF 變體）、同名 409、八執行緒搶同名、I/O 失敗、非法 ref | 十一種非法 ref；目錄不存在、EACCES、ENOSPC | 恰一成功；503 帶 errno 且無絕對路徑；半成品被清；上層目錄不變 |
| Bridge 權杖與形態 | AT-950-2-E-1～E-4 | 停用矩陣先於權杖、權杖七種形態、本文十餘種違規、{id} 與 subject 不符、同 ref 重送 | 見各 AT | 503／403／422／409 分明；403 回應逐位元組相同；恰 65536 位元組為 201 |
| validate 失敗形態 | AT-950-3-E-1、AT-950-3-E-2 | 子行程七種失敗、請求本文違規 | rc 3、非 JSON、缺鍵、逾時、超量、設定缺 | 503 cause 固定；422 不啟子行程 |
| 輸入閘邊界 | AT-950-7-E-1～E-3、AT-935-1-E-3、AT-935-2-E-2、AT-950-9-E-3 | reason 500 與 501 個 code point、單欄 300 與 301、三欄位元組和 700 與 701、關閉 text 120 與 121 個字元、控制字元、列舉、終值組合 | 表 M-D、M-O、M-C 的違規欄 | 一次全列違規；邊界對照為 201 |
| 資格與閘門序 | AT-935-4-1、AT-935-4-E-1～E-3 | 角色乘名單乘設定矩陣；非 ADMIN 零控件 | 無 token、Viewer、Operator、名單外 Admin、空名單、金鑰或權杖未設 | 401／403 ACCESS_DENIED／403 si_write_forbidden／503 si_write_disabled，先授權、再停用、再輸入 |
| 刪除不存在 | AT-935-3-1、AT-935-3-2、AT-935-3-E-1、AT-935-3-E-2 | 結構、UI、DELETE／PUT／PATCH 矩陣（兩層） | 全部 `/si/` 路徑 | Viewer 403；Operator 與 Admin 405；Bridge 零請求、零檔案 |
| 補償與結果不明 | AT-950-6-2、AT-950-6-E-1～E-3 | 明確拒絕與 5xx 補償刪列；逾時、送出後連線重設、2xx 垃圾本文保留列；連線被拒刪列；不重試 | 十二種 Bridge 回應、延遲、送出後關閉連線、201 加垃圾本文、關閉 | reason 逐字；結果不明者保留一列並帶 outcomeUnknown；請求數恰 2 |
| 對帳 | AT-933-2-E-1、AT-935-5-1、AT-935-5-2、AT-935-5-E-1～E-4 | 待入帳、紅色警示、回填冪等、量不到、limit 邊界 | 三種 kind 各兩列；orphans 三類；Bridge 503／拒絕／逾時／無窮頁；130 列 | NE 時 ingested 與 orphans 為 null、不顯示無待入帳；無 body 與 mac |
| DB 不可改 | AT-950-8-E-1、AT-950-8-E-2 | UPDATE 各欄被拒、NULL 改值可、DELETE 可；約束 | 九種 UPDATE；五種壞列 | 觸發器與 CHECK 拒絕；表內仍恰一列 |
| 前端預設拒絕與失敗不關窗 | AT-933-1-E-1、AT-933-1-E-2、AT-935-1-E-1、AT-935-1-E-2、AT-935-2-E-1 | 缺必填停用、連點只送一次、403／409／503／422 逐字、validate 不通過不送、即時拒收 | 見各 AT | 零請求或恰一個 POST；toast 含 reason 逐字；純文字渲染 |
| 機密 | AT-950-5-1、AT-950-5-E-1、AT-950-5-E-2 | 解析、啟動失敗、輸出掃描 | 40 字元隨機金鑰與權杖 | 任何 8 字元以上子字串不出現在回應、DB、日誌、例外 |
| 靜態鎖與夾具負控 | AT-933-1-E-3、AT-950-9-E-2、AT-950-11-E-1、AT-950-11-E-2 | 違規樣本各自回非空、良性回空；閉包缺檔大聲失敗 | 見各 AT | 各自指出判準；不退回假 CLI |

**刻意不做（附再開症狀）**

| 項目 | 為什麼不做 | 再開症狀 |
|------|-----------|----------|
| Console 內直接入帳（push）或在 Bridge 呼叫寫入型 CLI | ADR-SI-03′ 入帳模式為 pull、主控單窗口；AST 鎖釘死 argv 白名單 | 掌舵者要求按鈕直接入帳 |
| 「我是否在 deciders」端點 | 主控先行裁決 3：控件只對 Admin 顯示，名單由 backend 判、403 原因逐字顯示 | 掌舵者回報按鈕可見卻一律 403 |
| 在 Console 複製根層的列規則（retired 座標、corrects 是否存在、PROP 前提、digest 新鮮度） | AC-SI-35-2 誠實劃界：合法性判準全在 CLI；validate 只涵蓋 obs-add | 待入帳項頻繁被 CLI 拒收（見已知邊界 1） |
| 稽核檔輪替與目錄清理 | PRD 未要求；`console_audit/` 只增不減 | 目錄檔數大到影響主機端 `status` 的耗時 |
| 多人或代決、非 Admin 寫入 | AC-SI-35-4：K=1，放寬須 PRD 修訂 | 掌舵者要求第二位決定者 |
| 以 AT 或自動化截圖充當出口 (c) | PRD §8.1 明文：構造情境不能充當 | — |
| 驗證 CLI 的驗簽、列規則與折疊正確性 | 屬根層 P2 TCS；本檔只證明 Console 簽出的檔被它收 | 真 CLI 收下而 `check` 轉紅（見 §7.2 發現 1） |
| HTTP 層 `Cache-Control`、Bridge 認證 | 沿 P1b ⚖18 與 L-6（Bridge 只准 backend-net） | 沿 P1b 的再開症狀 |

**已知邊界（誠實登記）**

1. **前提在入帳時才判**：decide 的 PROP 態、route、晉升前提與卡面 digest 新鮮度由主機端 CLI 判；不成立＝rc 1，稽核檔與 DB 列原地不動，Console 持續顯示待入帳，直到掌舵者看到 CLI 的拒收碼（Console 無從得知拒收）。關閉的 `text` 上限 120 個 code point 只是上界：列是否超過 700 位元組取決於該列既有內容（SA 實測：夾具列 OBS-SI-005 加 120 個 CJK 字元的處置被 CLI 以 ROW-BYTES-OVER 拒收、60 個則收），權威仍是 CLI；validate 不涵蓋關閉（⚖13）。
2. **HMAC 偽造偵測弱於逐字稿載體**（PRD 誠實劃界）：持有金鑰的行程可鑄造合法稽核檔；獨立證據是 Console DB 稽核列。
3. **結果不明留下幽靈待入帳**：讀取逾時、送出後連線重設或提前 EOF、2xx 本文無法解析時（檔可能已落地也可能沒有），DB 列保留、Console 顯示待入帳並回報 `outcomeUnknown`；若檔其實未落地，補救是掌舵者重送（新 audit_ref）並由主控忽略該 ref（AT-950-6-E-2 釘住「保留」）。
4. **對帳全量掃描上限**為 observations 與 events 各 20 頁乘 500 筆；超限＝NOT-EVALUABLE（scan_cap_exceeded），不回空陣列。
5. **AST 鎖是形態判準**：`getattr`、動態拼接、`importlib` 看不到（W5）；行為面由 AT-950-2-1 的落檔清單與 AT-933-1-5 的真 CLI 入帳覆蓋。
6. **黃金檔是 Java 正式碼在固定輸入下的輸出**：序列化器日後變動會使 Bridge 副本與其不一致而紅（AT-950-4-3，刻意）。
7. **Starlette 路徑樣式**：`GET /si/proposals/PROP-SI-004:decide` 落到既有 GET 單筆處理器（422，不是 405），故 405 斷言一律用 DELETE、PUT、PATCH（AT-935-3-E-2）。
8. **前端 NE 的 return 不提供**：提案資料沒有 NE 的原因碼（`reasons`），故 verdict 為 NE 的卡只提供晉升後式與不晉升（⚖12）。
9. **真容器的可寫 bind**（Windows Docker Desktop 的寫入權限、主機端 CLI 讀得到同一目錄）只由靜態檢查與 V3 承擔；AT 不起容器。
10. **time 是 backend 時鐘**，與主機入帳可相隔數小時（pull 模式，PRD 已裁）；列的時間欄取簽章內的 time、不取入帳時刻。
11. **macOS 全部未驗**（NFR-SI-06-5）：AT 與 V 系列只在 Windows 與 Linux（CI）實跑。
12. **並行讀者可能讀到半成品**：`store_audit` 以 `O_EXCL` 直接寫檔（不經暫存檔改名，以免增加根層目錄項原語的站點）；寫入途中並行的讀者可能讀到不完整的檔，主機端 CLI 以 `audit_sha256` 與 mac 驗證，半成品必拒（AUDIT-SCHEMA 或 AUDIT-MAC-MISMATCH），檔寫完後可重試入帳。
13. **補償刪除自身失敗留幽靈列**：Bridge 明確拒絕後的補償刪列若因 DB 連線中斷而失敗，會留下無檔的列；記 warn 日誌，對帳面板以待入帳呈現（與邊界 3 同一處理）。
14. **Admin 但不在名單者送無法解析的 JSON 先得 400**：框架在用例入口之前解析本文，名單判定在用例入口（W10），故 403 `si_write_forbidden` 的前提是本文可解析。

**需同步的既有測試**（P2b 使下列既有測試的前提或精確釘選改變；開發 agent 須同步修改，只增不減，不得為使其變綠而改弱斷言；凡「取代」者＝以本檔對應 AT 改寫並改名，凍結的 P1b TCS 不改，RTM 的 P1b 子表由主控同 commit 改指新 AT）：

1. `engine-bridge/tests/test_si_readonly_lock.py`：`test_AT_932_2_1_*` 與 `test_AT_932_2_E_1_*` 整組改寫為 W5 的判準 1′～5′，取代為 AT-933-1-6、AT-933-1-E-3（輔助函式 `argv_functions`、`crit4_argv`、`crit5_dynamic` 隨判準改寫；白名單由 `export` 擴為兩個配對）。
2. `engine-bridge/tests/test_si_routes.py::test_AT_932_2_3_*`（六路徑乘四種非 GET 皆 405）：`POST /si/observations` 自此是寫入端點；改為 PUT／PATCH／DELETE 乘六個讀路徑皆 405、POST 乘其餘五個讀路徑皆 405；全部九個 `/si/` 路徑的三方法矩陣由 AT-935-3-E-2 承擔。
3. `engine-bridge/tests/test_si_deploy_config.py`：`si_mount_problems` 與 `test_AT_940_3_1_*`、`test_AT_940_3_E_1_*` 改為「設計 A 或 B 的唯讀 SI bind 加恰一條可寫稽核 bind」，P1b 的九種壞變體保留（其中「多掛一條」只指唯讀或非稽核的多餘 bind）；`SI_INPUTS` 改取 `WRITE_CLOSURE` 加 `PARAMS_SRC`（使 `test_AT_940_4_1_*` 續守新增輸入；D10 補上前為預期紅），`test_AT_940_4_E_1_*` 的 `FULL_PATHS` 補 `tools/lib/apply_lock.py`、`tools/lib/sdd_latest.py` 兩項；`test_AT_940_1_E_1_*` 不減（新增項另立 AT-950-1-3）。
4. `engine-bridge/tests/si_repo_support.py`、`fake_si.py`：只增（`WRITE_CLOSURE`、`ingest_run`、`dry_run` 旋鈕）；`CLI_CLOSURE` 與既有函式行為不變，`test_AT_940_7_*` 續綠。
5. `backend/.../config/OpenApiIT`：路徑釘選 `hasSize(67)` 改 71（新增 `/api/v1/si/proposals/{id}/decide`、`/api/v1/si/observations/{id}/close`、`/api/v1/si/observations/validate`、`/api/v1/si/console-writes`）；操作總數釘選 `isEqualTo(76)` 改 81（再加 `/api/v1/si/observations` 的 post）；`EXPECTED` 加四筆並把 `/api/v1/si/observations` 改為 get 與 post；類別 Javadoc 補一句。
6. `backend/.../persistence/SchemaMigrationIT`：`flywayAppliedVersionsOneToTwelveSuccessfully` 的 `containsExactly("1"…"12")` 加 `"13"`（方法名改 OneToThirteen），Javadoc 的 V1～V12 改 V1～V13，`CONSOLE_TABLES` 可加 `si_console_writes`（`containsAll`，只增）。
7. `backend/.../persistence/V5UpgradeMigrationIT`：版本清單 `containsExactly(…"12")` 加 `"13"`，Javadoc 的 V5～V12 改 V5～V13。
8. `backend/.../architecture/SiReadOnlyArchTest.AT_932_2_5_*`：改寫並取代為 AT-935-3-1（`@GetMapping` 由 6 改 7、`@PostMapping` 由 0 改 4、無 Put／Patch／Delete；`AgentBridge` 的 `si[A-Z]` 方法由 1 改 5；新增「寫入只經 `SiConsoleWriteService`」；A1～A6 與兩條落點規則保留；類別 Javadoc 的「零寫入是 P1b 的前提」改述）。
9. `backend/.../web/SiMirrorApiIT.AT_932_2_4_*`（六路徑乘 POST／PUT／PATCH／DELETE，Operator 與 Admin 皆 405）：`SecurityConfig` 對 `POST /api/v1/si/**` 要求 ADMIN，故 POST 自此組移出；PUT／PATCH／DELETE 乘六路徑維持（Viewer 403、Operator 與 Admin 405、無 token 401）；POST 乘五個無 POST 映射的讀路徑另測：無 token 401、Viewer 與 Operator 403、Admin 405；全程不觸 Bridge。`AT_932_4_1` 不變。
10. `backend/.../web/SiMirrorApiIT.AT_940_8_1_*`（OpenAPI 恰六個 SI 路徑各只有 get）：取代為 AT-950-10-1。
11. `backend/.../config/BridgePropertiesTest` 與其他直接建構 `BridgeProperties` 者：補新元件 `siWriteToken`；既有斷言一個不改弱（AT-950-5-E-1）。
12. `backend/src/test/.../minibridge/MiniBridge`、`MiniBridgeController`：只增 SI 寫入端點與 `Si` 旋鈕，`reset()` 回預設；既有 SDD、執行、SI 讀面的 AT 行為不變。
13. `frontend/lib/api/endpoints.test.ts`：標題與 `toHaveLength(74)` 改 79（再加 P2b 的五個函式）；`EXPECTED` 加 `postSiDecide`、`postSiObservation`、`postSiObservationClose`、`postSiObservationValidate`（方法 POST，網址同 W16）與 `getSiConsoleWrites`（GET，`/api/v1/si/console-writes?limit=100`）。
14. `frontend/lib/api/si.endpoints.test.ts`：`AT_932_2_7`（get 加 Si 恰六個）取代為 AT-950-9-E-1；`AT_940_8_2`（`schema.d.ts` 六路徑各只有 get）取代為 AT-950-10-2。
15. `frontend/components/domain/si/si.static.test.ts`：`AT_932_2_8`（無表單、mutation hook、非 GET 字樣）取代為 AT-950-9-E-2；`AT_932_1_E_8`、`AT_932_4_3` 不改（掃描範圍自動含新元件，新元件須通過）。
16. `frontend/components/domain/si/SiView.test.tsx`：`AT_932_2_6` 以預設角色 OPERATOR 續綠不改；其餘 `AT_932_*` 不改。
17. `frontend/lib/domain/si.test.ts`：`AT_940_5_1` 的比對範圍由「標 P1b 的 `si_` reason」改為「`reason` 以 `si_` 起頭的全部列」，常數由 2 改 5，與 AT-950-9-2 合併斷言（不減）。
18. `frontend/lib/nav/registry.test.ts`：`AT_932_6_*` 不改；新增 AT-950-10-E-1 一條。
19. `frontend/tests/helpers/si.tsx`：`renderSi` 增 `username` 選項與四個寫入端點、`console-writes` 的替身；預設行為（OPERATOR、`operator`）與既有回放不變。

不需改、但對新檔自動生效的機械鎖：`engine-bridge/tests/test_cross_platform_guard.py`（`si_audit.py` 不得用 POSIX 專屬 API）、根層 `TestDirEntryPrimitivesAreAccountedFor`（`si_audit.py` 不得新增 `os.replace`、`rename`、`move` 站點；半成品清除用 `os.unlink` 並包 `try/except OSError`）、`ArchitectureRulesTest` 的 A1～A6 與 JPA、WEB 規則（新類別 application 層不得依賴 adapter 或 infrastructure；`si_console_writes` 以 JDBC 配接器存取、不建 JPA 實體）、`frontend/tests/design-rules.test.ts`（新元件無陰影與漸層、無寫死色碼、只用 Lucide 且無 emoji、無 `outline-none`、無 `dark:`）、`AgentConsole/CLAUDE.md` 的文件閘（新文件不得有測試摘要字樣與 4 位數字同行）。

漏改第 5～9、13 項者，V7 的全套會紅；它們與 NFR-P2b-8 的零退化是同一條約束。

---

## 5. 測試資料規格

### 5.1 跨語言向量與金鑰（Java 與 Python 共用；V1～V4 與負控逐字取自根層 P2 TCS §5.5，SA 以標準庫重算全部相同）

- 金鑰 `K0`＝`si-p2-vector-key-0123456789-abcdefghijklmnopqrstuvwxyz`（UTF-8 字串，不做 base64 解碼；公開的測試金鑰，字面刻意不用 `sk-` 前綴以免機密掃描擋 commit）；`key_id`＝`f076edf0`（金鑰位元組 sha256 前 8 碼小寫 hex）；`mac`＝HMAC-SHA256(金鑰位元組, body 字串的 UTF-8 位元組) 小寫 hex，**不重新序列化 body**。向量共用 PROP digest＝`sha256:a45ee65aa8547255f96c45d106da2a239e0c6db4fc9c06a9af229cb9e9ec9bfe`；向量的 `time` 為 `2026-10-21T09:15:30+08:00`、`user` 為 `admin`、`role` 為 `ADMIN`。外層檔＝緊湊 JSON、鍵序 `schema_rev`、`kind`、`audit_ref`、`subject`、`body`（字串）、`key_id`、`mac`，UTF-8 無 BOM、無結尾換行（`audit_sha256` 的對象就是這些位元組）。

| 向量 | kind 與外層 subject | audit_ref | body 位元組 | mac | 外層檔位元組 | 外層檔 sha256 |
|------|--------------------|-----------|------------|-----|-------------|---------------|
| V1 | decide／PROP-SI-004 | `6f1c2a3e-8b4d-4e5f-9a7b-0c1d2e3f4a5b` | 281 | `a23f62da5cc2b8668a05570632b60700316350667c2fef600beda100c4bf3c21` | 527 | `sha256:4e35c9e5df306c11d77698bd0dbca4090d46fa4d09b8ffae87f135b27335c43f` |
| V2 | decide／PROP-SI-004 | `0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d` | 355 | `830722c9fcfccc37861f9fe62498aa0074822595e85578e48c8a04298de0ce9b` | 609 | `sha256:df7419ef9502262538fe8640a23a6bb691299b683929858178b02b89fe1ed3eb` |
| V3 | obs-add／null | `b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e` | 380 | `0e67b0e0be050c07dc3b539fed87b3f53f88856446d2468b0e9f1da71cb94f35` | 630 | `sha256:a923a24521bb7a05e2e05427e0b5f7e30d7080350c8ce6cba6944ae887cef601` |
| V4 | obs-close／OBS-SI-247 | `c3d4e5f6-a7b8-4c9d-8e0f-1a2b3c4d5e6f` | 227 | `f299d74dd7c261072b69a4c14a79999cda39716b5a9851b65fce8b6da016f6bc` | 469 | `sha256:5d3f20980c464cb020b8031a3009435ecc94e408c1f8b5873a45610bb590eba4` |

| 向量 | body 字串（逐字；緊湊 JSON、非 ASCII 原樣） |
|------|------------------------------------------|
| V1 | `{"schema_rev":1,"audit_ref":"6f1c2a3e-8b4d-4e5f-9a7b-0c1d2e3f4a5b","kind":"decide","user":"admin","role":"ADMIN","time":"2026-10-21T09:15:30+08:00","prop":"PROP-SI-004","digest":"sha256:a45ee65aa8547255f96c45d106da2a239e0c6db4fc9c06a9af229cb9e9ec9bfe","dkind":"approve","flags":[]}` |
| V2 | `{"schema_rev":1,"audit_ref":"0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d","kind":"decide","user":"admin","role":"ADMIN","time":"2026-10-21T09:15:30+08:00","prop":"PROP-SI-004","digest":"sha256:a45ee65aa8547255f96c45d106da2a239e0c6db4fc9c06a9af229cb9e9ec9bfe","dkind":"reject","reason_class":"證據不足","reason":"證據座標不足，無法判定","flags":[]}` |
| V3 | `{"schema_rev":1,"audit_ref":"b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e","kind":"obs-add","user":"admin","role":"ADMIN","time":"2026-10-21T09:15:30+08:00","context":"Console・自我進化頁","symptom":"待入帳徽章在入帳後仍顯示","evidence":"AgentConsole/frontend/components/domain/si/SiView.tsx:88","category":"bug","severity":"P3","face":"產品","external_derived":false}` |
| V4 | `{"schema_rev":1,"audit_ref":"c3d4e5f6-a7b8-4c9d-8e0f-1a2b3c4d5e6f","kind":"obs-close","user":"admin","role":"ADMIN","time":"2026-10-21T09:15:30+08:00","obs_id":"OBS-SI-247","disposition":"decided：掌舵者裁決，已修復"}` |

- 負控一：V1 body 的 `"dkind":"approve"` 換成 `"dkind":"reject"`、其餘不變，其正確 mac＝`7801839b8fd4d641711b8a982ae18526bc8ae9857f5c5fdc3df19e1b4d5c6b2b`（不等於 V1 的 mac）。負控二：V1 body 以 `K0` 接一個 `x` 簽出的 mac＝`e4a88cff0a4a932fc930efa4d3b1caeda3f4ad64ebfa82dfedffc1358a61e967`（外層 `key_id` 仍為原金鑰的）。負控三：V1 body 的 `+08:00` 換成 `Z`（真 CLI 先於 MAC 判 AUDIT-TIME-FORMAT；Java 的時間 formatter 對 UTC 瞬間須輸出 `+00:00`，絕不輸出 Z）。

### 5.2 欄位與值域表（backend 閘 W12、frontend 驗證函式 W17、signer 的 body 組裝 W7 共用同一張表）

**通則**：字串欄先 trim；不得含 C0 控制字元（U+0000～U+001F）與 DEL（U+007F）；長度以 code point 計；觀察與關閉的字串欄一律拒收 `|`（OBS 列是 Markdown 九欄表）。`user`＝JWT subject（須合 `^[A-Za-z0-9_.-]{1,64}$`）、`role` 恆為 `ADMIN`、`time`＝Clock 現在（截秒、`±HH:MM`、不用 Z）。

**表 M-V**（`decideVerbOptions` 的情境；輸入為提案物件的 `state`、`route`、`verdict`、`cooldown`，第 11 列的輸入是狀態橫幅的 `suspended` 物件；函式簽名不鎖，測試以匯出者為準）

| # | state | route | verdict | cooldown | 期望 `label=dkind` 序列（〔needsAck〕＝晉升後式） |
|---|-------|-------|---------|----------|------------------------------------------------|
| 1 | proposed | loop | null | null | 核准=approve；否決=reject；退回=return |
| 2 | proposed | handoff:T1 | null | null | 轉交=ack-handoff；不轉交=reject；退回=return |
| 3 | verified | loop | PASS | null | 晉升=promote；不晉升=decline-promote |
| 4 | verified | loop | NE | null | 晉升（未驗採納）=promote〔needsAck〕；不晉升=decline-promote |
| 5 | verified | loop | FAIL | null | 退回=return；不晉升=decline-promote |
| 6 | rejected | loop | 任意 | 物件（冷卻中） | 解除=unblock |
| 7 | rejected | loop | 任意 | null（已解除） | （空；無控件） |
| 8 | promoted | loop | PASS | null | 回滾=rollback |
| 9 | measuring（closed 同） | loop | PASS | null | 回滾=rollback |
| 10 | approved（returned、handed-off 同） | loop | null | null | （空；無控件） |
| 11 | 橫幅 `suspended` 非 null（`run` 為 RUN-SI-001） | — | — | — | 恢復=resume（綁 `suspended.run`） |

**表 M-D**（決定；`reason` 為 1～500 個 code point 的單行字串；`reasonClass` ∈ 證據不足、風險過高、工件類別錯、已被涵蓋、範圍外、卡面不清、未說明；`digest` 為 `sha256:` 接 64 個小寫十六進位，前端綁定開啟當下的卡面值；`flags` 恆在、僅 promote 可含 `unverified_ack`）

| dkind | 路徑 id | 必填欄 | 禁止欄 | 期望 body（標準輸入；refs 依序 b2000000-0000-4000-8000-000000000001～9） |
|-------|---------|--------|--------|------------------------------------------------------------------|
| approve | `PROP-SI-004` | `digest` | `reason`、`reasonClass`、`unverifiedAck` | `{"schema_rev":1,"audit_ref":"b2000000-0000-4000-8000-000000000001","kind":"decide","user":"admin","role":"ADMIN","time":"2026-10-24T22:30:15+08:00","prop":"PROP-SI-004","digest":"sha256:d21ae6f5a48de71266479e0a7f6278786764f9a52bbb0a7c6d82b7f1419cec9c","dkind":"approve","flags":[]}` |
| reject | `PROP-SI-004` | `digest`、`reason`、`reasonClass` | `unverifiedAck` | `{"schema_rev":1,"audit_ref":"b2000000-0000-4000-8000-000000000002","kind":"decide","user":"admin","role":"ADMIN","time":"2026-10-24T22:30:15+08:00","prop":"PROP-SI-004","digest":"sha256:d21ae6f5a48de71266479e0a7f6278786764f9a52bbb0a7c6d82b7f1419cec9c","dkind":"reject","reason_class":"證據不足","reason":"證據座標不足，無法判定","flags":[]}` |
| return | `PROP-SI-004` | `digest`、`reason`、`reasonClass` | `unverifiedAck` | `{"schema_rev":1,"audit_ref":"b2000000-0000-4000-8000-000000000003","kind":"decide","user":"admin","role":"ADMIN","time":"2026-10-24T22:30:15+08:00","prop":"PROP-SI-004","digest":"sha256:d21ae6f5a48de71266479e0a7f6278786764f9a52bbb0a7c6d82b7f1419cec9c","dkind":"return","reason_class":"工件類別錯","reason":"改用 M 類","flags":[]}` |
| promote | `PROP-SI-004` | `digest`；verdict 為 NE 時另勾 `unverifiedAck` | `reason`、`reasonClass` | `{"schema_rev":1,"audit_ref":"b2000000-0000-4000-8000-000000000004","kind":"decide","user":"admin","role":"ADMIN","time":"2026-10-24T22:30:15+08:00","prop":"PROP-SI-004","digest":"sha256:d21ae6f5a48de71266479e0a7f6278786764f9a52bbb0a7c6d82b7f1419cec9c","dkind":"promote","flags":[]}` |
| decline-promote | `PROP-SI-004` | `digest`、`reason`、`reasonClass` | `unverifiedAck` | `{"schema_rev":1,"audit_ref":"b2000000-0000-4000-8000-000000000005","kind":"decide","user":"admin","role":"ADMIN","time":"2026-10-24T22:30:15+08:00","prop":"PROP-SI-004","digest":"sha256:d21ae6f5a48de71266479e0a7f6278786764f9a52bbb0a7c6d82b7f1419cec9c","dkind":"decline-promote","reason_class":"風險過高","reason":"風險太高","flags":[]}` |
| rollback | `PROP-SI-004` | `reason` | `digest`、`reasonClass`、`unverifiedAck` | `{"schema_rev":1,"audit_ref":"b2000000-0000-4000-8000-000000000006","kind":"decide","user":"admin","role":"ADMIN","time":"2026-10-24T22:30:15+08:00","prop":"PROP-SI-004","dkind":"rollback","reason":"太慢","flags":[]}` |
| unblock | `PROP-SI-004` | （無） | `digest`、`reason`、`reasonClass`、`unverifiedAck` | `{"schema_rev":1,"audit_ref":"b2000000-0000-4000-8000-000000000007","kind":"decide","user":"admin","role":"ADMIN","time":"2026-10-24T22:30:15+08:00","prop":"PROP-SI-004","dkind":"unblock","flags":[]}` |
| resume | `RUN-SI-001`（`run`，非 `prop`） | `reason` | `digest`、`reasonClass`、`unverifiedAck` | `{"schema_rev":1,"audit_ref":"b2000000-0000-4000-8000-000000000008","kind":"decide","user":"admin","role":"ADMIN","time":"2026-10-24T22:30:15+08:00","run":"RUN-SI-001","dkind":"resume","reason":"兩個壞窗已人工檢視","flags":[]}` |
| ack-handoff | `PROP-SI-004` | `digest` | `reason`、`reasonClass`、`unverifiedAck` | `{"schema_rev":1,"audit_ref":"b2000000-0000-4000-8000-000000000009","kind":"decide","user":"admin","role":"ADMIN","time":"2026-10-24T22:30:15+08:00","prop":"PROP-SI-004","digest":"sha256:d21ae6f5a48de71266479e0a7f6278786764f9a52bbb0a7c6d82b7f1419cec9c","dkind":"ack-handoff","flags":[]}` |

晉升後式（verdict 為 NE、`unverifiedAck` 為 true）的 body 是 promote 列把 `"flags":[]` 換成 `"flags":["unverified_ack"]`，例（ref 為 `b2000000-0000-4000-8000-000000000010`）：`{"schema_rev":1,"audit_ref":"b2000000-0000-4000-8000-000000000010","kind":"decide","user":"admin","role":"ADMIN","time":"2026-10-24T22:30:15+08:00","prop":"PROP-SI-004","digest":"sha256:d21ae6f5a48de71266479e0a7f6278786764f9a52bbb0a7c6d82b7f1419cec9c","dkind":"promote","flags":["unverified_ack"]}`

**表 M-O**（觀察；請求欄 camelCase、body 鍵 snake_case；`marks_extra` 刻意不提供，見 W12）

| 欄 | 型別與值域 | 規則 | 入帳時 CLI 的對應拒收碼 |
|----|-----------|------|------------------------|
| `context`、`symptom`、`evidence` | 字串 | 各 1～300 個 code point；三欄 UTF-8 位元組和不得超過 700（必要條件；權威是 validate 與 CLI 的列位元組上限 `row_max_bytes`） | FIELD-EMPTY、PIPE-IN-FIELD、ROW-BYTES-OVER；`evidence` 須含可定位座標（COORD-NONE，Console 不複製） |
| `category` | process、bug、tooling、doc、decision | 必填 | ENUM-CATEGORY |
| `severity` | P1、P2、P3、P4 | 必填 | ENUM-SEVERITY |
| `face` | 守衛、產品、文件、流程 | 必填 | FACE-INVALID |
| `exposure` | a、b、c、無 | `face` 為守衛時必填，否則禁止 | EXPOSURE-REQUIRED、EXPOSURE-UNEXPECTED；守衛面 `severity` 為 P1 或 P2 時 `exposure` 不得為 無（GUARD-P12-NO-EXPOSURE，Console 不複製，入帳與預檢皆由 CLI 判） |
| `externalDerived` | 布林 | 必填（表單預設 false） | AUDIT-BODY-INVALID |
| `corrects` | `OBS-SI-` 接 3 位以上數字 | 選填；被更正列須存在（CLI 判） | CORRECTS-NOT-FOUND |

validate 的請求是未簽 body（無 `audit_ref`、`mac`、`key_id`；有 `user`、`time`）。預覽的 `row_bytes` 等於入帳列位元組數（`audit_ref` 以等長的全零 UUID 佔位、`time` 為預覽時刻而寬度相同）；`row` 逐字相等只在 AT 的受控輸入（body 帶同一個 `audit_ref` 與 `time`）成立。實測（狀態 A 倉的真 CLI）：O1 的預覽與入帳列皆 287 位元組、O2 為 317、O3 為 311。O1 的例：`{"schema_rev":1,"kind":"obs-add","user":"admin","role":"ADMIN","time":"2026-10-24T22:30:15+08:00","context":"Console・自我進化頁","symptom":"待入帳徽章在入帳後仍顯示","evidence":"AgentConsole/frontend/components/domain/si/SiView.tsx:88","category":"bug","severity":"P3","face":"產品","external_derived":false}`

| 例 | 輸入（camelCase 請求欄）與差異 | 期望 body（refs b3000000-0000-4000-8000-000000000001～3） |
|----|------------------------------|--------------------------------------------------------|
| O1 基本（＝黃金檔 G3 的輸入） | 六個必填欄；`externalDerived` 為 false；無 `exposure`、無 `corrects` | `{"schema_rev":1,"audit_ref":"b3000000-0000-4000-8000-000000000001","kind":"obs-add","user":"admin","role":"ADMIN","time":"2026-10-24T22:30:15+08:00","context":"Console・自我進化頁","symptom":"待入帳徽章在入帳後仍顯示","evidence":"AgentConsole/frontend/components/domain/si/SiView.tsx:88","category":"bug","severity":"P3","face":"產品","external_derived":false}` |
| O2 守衛面 | `category` 為 tooling、`severity` 為 P2、`face` 為 守衛、`exposure` 為 b、`externalDerived` 為 true | `{"schema_rev":1,"audit_ref":"b3000000-0000-4000-8000-000000000002","kind":"obs-add","user":"admin","role":"ADMIN","time":"2026-10-24T22:30:15+08:00","context":"Console・自我進化頁","symptom":"待入帳徽章在入帳後仍顯示","evidence":"AgentConsole/frontend/components/domain/si/SiView.tsx:88","category":"tooling","severity":"P2","face":"守衛","exposure":"b","external_derived":true}` |
| O3 更正列（＝黃金檔 G4 的輸入） | 同 O1 另加 `corrects` 為 OBS-SI-001 | `{"schema_rev":1,"audit_ref":"b3000000-0000-4000-8000-000000000003","kind":"obs-add","user":"admin","role":"ADMIN","time":"2026-10-24T22:30:15+08:00","context":"Console・自我進化頁","symptom":"待入帳徽章在入帳後仍顯示","evidence":"AgentConsole/frontend/components/domain/si/SiView.tsx:88","category":"bug","severity":"P3","face":"產品","external_derived":false,"corrects":"OBS-SI-001"}` |

**表 M-C**（關閉；`terminal` 的七個值，無 `open`；`ref` 與 `text` 恰擇一；`text` 為 1～120 個 code point（360 位元組上界，與 700 位元組的列上限相容，⚖26）且不得含 `之後再看`；終值與附加文字以全形冒號相接）

| terminal | 必填（且只帶這一項） | 標準輸入 | 期望 body（路徑 id 與 obs_id 為 OBS-SI-005；refs b4000000-0000-4000-8000-000000000001～7） |
|----------|--------------------|----------|-------------------------------------------------------------|
| fixed | `ref`＝7～40 碼小寫十六進位 | `ref`＝2b2b0b3d | `{"schema_rev":1,"audit_ref":"b4000000-0000-4000-8000-000000000001","kind":"obs-close","user":"admin","role":"ADMIN","time":"2026-10-24T22:30:15+08:00","obs_id":"OBS-SI-005","disposition":"fixed@2b2b0b3d"}` |
| def | `ref`＝`DEF-<n>-<n>` | `ref`＝DEF-200-559 | `{"schema_rev":1,"audit_ref":"b4000000-0000-4000-8000-000000000002","kind":"obs-close","user":"admin","role":"ADMIN","time":"2026-10-24T22:30:15+08:00","obs_id":"OBS-SI-005","disposition":"DEF-200-559"}` |
| deferred | `text` | `text`＝等 P3 輪 | `{"schema_rev":1,"audit_ref":"b4000000-0000-4000-8000-000000000003","kind":"obs-close","user":"admin","role":"ADMIN","time":"2026-10-24T22:30:15+08:00","obs_id":"OBS-SI-005","disposition":"deferred：等 P3 輪"}` |
| retired | `text`（須含可定位座標，由 CLI 判） | `text`＝docs/06_quality/SelfImproving_Protocol/params.json | `{"schema_rev":1,"audit_ref":"b4000000-0000-4000-8000-000000000004","kind":"obs-close","user":"admin","role":"ADMIN","time":"2026-10-24T22:30:15+08:00","obs_id":"OBS-SI-005","disposition":"retired：docs/06_quality/SelfImproving_Protocol/params.json"}` |
| decided | `text` | `text`＝夾具關閉 | `{"schema_rev":1,"audit_ref":"b4000000-0000-4000-8000-000000000005","kind":"obs-close","user":"admin","role":"ADMIN","time":"2026-10-24T22:30:15+08:00","obs_id":"OBS-SI-005","disposition":"decided：夾具關閉"}` |
| merged | `ref`＝`OBS-SI-` 接 3 位以上數字（`OBS-SI-\d{3,}`） | `ref`＝OBS-SI-001 | `{"schema_rev":1,"audit_ref":"b4000000-0000-4000-8000-000000000006","kind":"obs-close","user":"admin","role":"ADMIN","time":"2026-10-24T22:30:15+08:00","obs_id":"OBS-SI-005","disposition":"merged@OBS-SI-001"}` |
| proposed | `ref`＝`PROP-SI-` 接 3 位以上數字（`PROP-SI-\d{3,}`） | `ref`＝PROP-SI-004 | `{"schema_rev":1,"audit_ref":"b4000000-0000-4000-8000-000000000007","kind":"obs-close","user":"admin","role":"ADMIN","time":"2026-10-24T22:30:15+08:00","obs_id":"OBS-SI-005","disposition":"proposed@PROP-SI-004"}` |

### 5.3 黃金檔 G1～G5（固定輸入下 Java 正式碼的輸出）

固定輸入＝`Clock.fixed` 在 `2026-10-24T22:30:15+08:00`（偏移 +08:00）、`SiAuditRefSource` 依序給 `a1000000-0000-4000-8000-000000000001`～`5`、金鑰 `K0`、帳號 `admin`；請求欄依表末欄（D0＝`sha256:d21ae6f5a48de71266479e0a7f6278786764f9a52bbb0a7c6d82b7f1419cec9c`，即狀態 A 的 PROP-SI-004 卡面 digest）。檔住 `backend/src/test/resources/si/audit/` 與 `engine-bridge/tests/fixtures/si_audit/`（逐位元組相同，AT-950-4-3 鎖住）。

| 檔 | 檔名 | kind／subject | audit_ref | body 位元組 | 外層檔位元組 | 外層檔 sha256 | mac | 固定輸入（請求本文；路徑 id 同 subject） |
|----|------|---------------|-----------|------------|-------------|---------------|-----|----------------------------------------|
| G1 | `decide-approve.json` | decide／PROP-SI-004 | `a1000000-0000-4000-8000-000000000001` | 281 | 527 | `sha256:831acfcd69993cee663ded3ab6d5ac6305a90631d3c55259bdaa452b3e87b337` | `18f299d249ab36dfe28975fc61fff8a15a1c20fa9602af66fadd26e4af5917aa` | `{"dkind":"approve","digest":"sha256:d21ae6f5a48de71266479e0a7f6278786764f9a52bbb0a7c6d82b7f1419cec9c"}` |
| G2 | `decide-reject.json` | decide／PROP-SI-004 | `a1000000-0000-4000-8000-000000000002` | 355 | 609 | `sha256:9d81e866542ae0c84331861671f7780de91a328c19b487b3a23a45c85d06d046` | `ae47199c39cad71546f64170c885b7545c4f77a8a32b5a39b7f0a10933858c8b` | `{"dkind":"reject","digest":"sha256:d21ae6f5a48de71266479e0a7f6278786764f9a52bbb0a7c6d82b7f1419cec9c","reason":"證據座標不足，無法判定","reasonClass":"證據不足"}` |
| G3 | `obs-add.json` | obs-add／null | `a1000000-0000-4000-8000-000000000003` | 380 | 630 | `sha256:fc3917fa5c1d3b0dad7c258de028130981e5ac63ed1c0e991919054a9ffd3c1f` | `7505ec8a9eb60f7b6b168d2c659dbe77ed6fad2c103b0238396b42fc70accf09` | `{"context":"Console・自我進化頁","symptom":"待入帳徽章在入帳後仍顯示","evidence":"AgentConsole/frontend/components/domain/si/SiView.tsx:88","category":"bug","severity":"P3","face":"產品","externalDerived":false}` |
| G4 | `obs-add-corrects.json` | obs-add／null | `a1000000-0000-4000-8000-000000000004` | 404 | 658 | `sha256:faba0eed8cfe1cee1087a291c385011160d5fcca2406c8eb84889c3a1fc646c7` | `ccbc3e7aa73925b976a553dc2e062b758d556c7e5d27a2ded8202334b7b012b9` | `{"context":"Console・自我進化頁","symptom":"待入帳徽章在入帳後仍顯示","evidence":"AgentConsole/frontend/components/domain/si/SiView.tsx:88","category":"bug","severity":"P3","face":"產品","externalDerived":false,"corrects":"OBS-SI-001"}` |
| G5 | `obs-close.json` | obs-close／OBS-SI-005 | `a1000000-0000-4000-8000-000000000005` | 212 | 454 | `sha256:4c5985a35c6da9189ab0277149c67f745c9977b5b5694f229e03c95910af5b57` | `fb9c251546f9f40bbe303579c40c39ea2a3e53e09acea60317a0e72533e24410` | `{"terminal":"decided","text":"夾具關閉"}` |

入帳效果（SA 以真 CLI 在狀態 A 倉逐檔實跑，rc 皆為 0；AT-933-1-5、AT-935-1-4、AT-935-2-4 逐項斷言）：

- G1：stdout 為 `{"ok": true, "kind": "dec", "seq": 7, "id": "<DEC 號>", "prop": "PROP-SI-004", "dkind": "approve", "digest8": "d21ae6f5"}`（`id` 以 `DEC-SI-` 起頭接 3 位序號；狀態 A 倉的第一筆決定）；事件 `dec` 鍵集合恰為 `seq`、`t`、`kind`、`by`、`id`、`dkind`、`prop`、`digest`、`carrier`、`audit_ref`、`audit_sha256`、`key_id`、`decider`、`decided_at`（`carrier` 為 console、`audit_sha256` 等於檔 sha256、`key_id` 為 f076edf0、`decider` 為 admin、`decided_at` 為 `2026-10-24T22:30:15+08:00`；無 `quote`、`sid`、`line`、`card_seq`）；提案 state 為 approved。
- G2：事件另有 `reason`（證據座標不足，無法判定）與 `reason_class`（證據不足）；提案 state 為 rejected，冷卻項的 `reason_class` 為 證據不足、`rejected_seq` 為 7。
- G3：stdout 為 `{"ok": true, "kind": "obs.add", "seq": 7, "id": "OBS-SI-013", "audit_ref": "<ref>"}`；新增列 `| OBS-SI-013 | 2026-10-24 22:30 +08:00 | Console・自我進化頁 | 待入帳徽章在入帳後仍顯示 | AgentConsole/frontend/components/domain/si/SiView.tsx:88 | bug | P3 | open | 面=產品;來源=人;回報者=admin;carrier=console;audit_ref=a1000000-0000-4000-8000-000000000003 |`（287 位元組）；事件 `obs.add` 鍵集合恰為 `seq`、`t`、`kind`、`by`、`obs`、`audit_ref`、`audit_sha256`、`key_id`、`decider`、`carrier`。
- G4：同 G3，標記欄為 `面=產品;rel=corrects:OBS-SI-001;來源=人;回報者=admin;carrier=console;audit_ref=a1000000-0000-4000-8000-000000000004`。
- G5：stdout 的 `kind` 為 `obs.close`、`id` 為 `OBS-SI-005`；OBS 帳本前後逐行比對只有 OBS-SI-005 一行改變、且只有第八欄（處置）改為 `decided：夾具關閉`，行數不變；事件 `obs.close` 鍵集合同 `obs.add` 另加 `disposition`。

### 5.4 backend 測試設施（`backend/src/test/java/com/aisdlc/`）

- **`AbstractSiWriteIT`**（`console.support`，繼承 `AbstractApiIT`）：`@BeforeEach` 另 `TRUNCATE console.si_console_writes` 並 `MINI.si.reset()`；以 `@DynamicPropertySource` 設 `console.si.deciders=admin,ops_admin`、`console.si.audit-key=K0`、`console.bridge.si-write-token=T0`（`T0`＝`si-write-token-for-tests-0123456789-abcdef`，42 字元）與 `ENGINE_BRIDGE_URL`（沿 `SiMirrorApiIT`）。`adminAs(name)`＝以 `JwtTokenService.issue(name, Role.ADMIN)` 鑄任意帳號名的 ADMIN token（名單內外與帳號名值域案例用；`admin()` 的帳號名為 `admin`）。
- **`SEAM`**＝`SiWriteSeam`（`@TestConfiguration`）：`Clock.fixed(2026-10-24T14:30:15Z, 偏移 +08:00)`（故 `time` 為 `…T22:30:15+08:00`）與佇列式 `SiAuditRefSource`（`refs(...)` 排入該 AT 所需的 ref，例如 G3、G4 的 AT 排入 §5.3 的第 3、4 個；佇列耗盡時大聲失敗）。
- **MiniBridge 的 SI 寫入擴充**（`com.aisdlc.minibridge`）：`si.writes`（每筆 `path`、`token`〔`X-Bridge-Token` 標頭〕、`raw`〔請求本文位元組〕）、`si.writeReply`（預設 201 與 `{audit_ref, stored:true}`，可設 status 與 body）、`si.writeDelayMillis`、`si.onWrite`（收到請求當下的回呼，AT-933-2-1 以 JDBC 讀表）、`si.validateReply`（預設 `ok` 為 true、`row_bytes` 287、`row_max_bytes` 700、`findings` 空）；`MINI.requests()` 記 `POST /si/<路徑>`；`reset()` 回預設。

### 5.5 frontend 測試設施（`frontend/tests/helpers/si.tsx`，沿 P1b §5.4）

`renderSi({ role, username, fixture, overrides })` 增 `username`（預設 `operator`，ADMIN 案例傳 `admin`）；`SiEndpoint` 增 `decide`、`observation-add`、`observation-close`、`validate`、`console-writes` 五鍵（`overrides` 逐端點覆寫，回 `Response` 或 `{status, data}`）；POST 預設回 201 `{auditRef, kind, subject, time, keyId}`（`kind` 與 `subject` 取自請求）；validate 預設回 `{ok:true,row,rowBytes:287,rowMaxBytes:700,findings:[]}`；`console-writes` 預設回 `{items:[],truncated:false,orphans:[],reconcile:{status:"ok",reason:null,backfilled:0}}`；`stub.calls` 另記 `body`（原始字串，供斷言送出的 JSON 本文）。輔助 `writeItem({auditRef, kind, subjectId, ingested})` 造 `console-writes` 項。`CopyCommand` 的測試 id 沿既有 `sdd-recovery-command-<shell>`，因頁面可同時有多組，斷言一律 `within(對話框或列)` 取。

### 5.6 Bridge 測試設施（`engine-bridge/tests/`）

`si_repo_support.py` 增 `WRITE_CLOSURE`＝`CLI_CLOSURE` 加 `tools/lib/apply_lock.py`、`tools/lib/sdd_latest.py`（SA 實測：缺任一個，寫入動詞即 `ImportError`——`evwrite` 要 `apply_lock`、`writeverbs` 頂層要 `sdd_latest`），`make_si_repo(tmp_path, state, closure=)`（缺檔大聲失敗）、`ingest_run(root, home, key, *args)`（環境＝`cli_env` 加 `AUTOSDD_SI_DIR`＝`home`、`AUTOSDD_SI_AUDIT_KEY`；回 `(rc, stdout, stderr)`）、`audit_variant(raw, **changes)`（由黃金檔位元組造單點變形並依需要重簽；供 AT-933-1-E-4 等）；`fake_si.py` 增旋鈕 `dry_run`（要輸出的物件，預設最小合法物件）並記錄 stdin（`stdin_b64`）。`BR-LIVE` 沿 P1b 的 `make_bridge(replace(settings, si_root=…, si_write_token=T0, si_audit_dir=AD))`，`T0` 同上、`AD` 為 tmp 內的目錄。

### 5.7 hermetic 環境與允許變更的檔案集合

全部 AT 只用 tmp 目錄內的合成倉與假 CLI、loopback 的 uvicorn、Testcontainers 的 PG、`MockRestServiceServer`、jsdom 與 `fetch` 替身；不連外網、不寫真帳本、不寫真事件帳本、不碰真 `~/.autosdd/`；子行程的 `HOME`／`USERPROFILE`／`AUTOSDD_SI_DIR` 一律指向 tmp。測試結束必關活 Bridge 與回收子行程。

| 區 | 允許新增或修改的路徑（相對 monorepo 根；與 D1～D10 逐項一致） |
|----|--------------------------------------------------------------|
| Bridge | `AgentConsole/engine-bridge/app/si_audit.py`（新）、`app/si_cli.py`、`app/routers/si.py`、`app/security.py`、`app/settings.py`、`README.md`；`tests/test_si_write_routes.py`、`test_si_audit_filename_safety.py`、`test_si_console_ingest.py`（新）、`test_si_readonly_lock.py`、`test_si_routes.py`、`test_si_cli.py`、`test_si_deploy_config.py`、`fake_si.py`、`si_repo_support.py`；`tests/fixtures/si_audit/**`（新） |
| backend | `AgentConsole/backend/src/main/java/com/aisdlc/console/` 下依 D4～D7 列示的新增與修改（含 `V13__si_console_writes.sql`、`application.yml`、`SecurityConfig`、`BridgeProperties`、`SiWriteProperties`、`SiWriteUseCase`、`SiConsoleWriteService`、`SiAuditSigner`、`SiAuditRefSource`、`SiWriteGates`、`SiReconcileService`、請求與回應 DTO、`SiConsoleWriteRepository` 與 JDBC 配接器、`AgentBridge`、`BridgeHttpAdapter`、`SiBridgeErrors`、`ErrorReasons`、`SiController`）；`backend/src/test/` 下的七個新測試類別、`AbstractSiWriteIT`、`SiWriteSeam`、`MiniBridge`／`MiniBridgeController`、既有 `OpenApiIT`、`SchemaMigrationIT`、`V5UpgradeMigrationIT`、`SiReadOnlyArchTest`、`SiMirrorApiIT`、`BridgePropertiesTest` 的同步（§4）；`backend/src/test/resources/si/audit/**` |
| frontend | `AgentConsole/frontend/components/domain/si/{SiDecideDialog,SiObsForm,SiObsCloseDialog,SiWritesPanel}.tsx` 與各自測試、`SiView.tsx`、`SiStatusBanner.tsx`、`SiObservationsPanel.tsx`、`SiProposalsPanel.tsx`、`siParts.tsx`（共用小元件，可動；`SiEventsPanel.tsx` 不動）、`si.static.test.ts`、`SiView.test.tsx`；`lib/api/{endpoints,queries,types,endpoints.test,si.endpoints.test}.ts`、`schema.d.ts`；`lib/domain/si.ts`、`si.test.ts`；`lib/nav/registry.test.ts`；`tests/helpers/si.tsx` |
| 部署 | `AgentConsole/docker-compose.yml`、`AgentConsole/.env.example` |
| 不屬開發 agent（主控代做） | `.github/workflows/agentconsole-ci.yml`；`AgentConsole/docs/**`——含契約後繼檔 `AgentConsole/docs/02_architecture/API_Contract_SelfImproving_P2b.md`（**新檔**，W25；開發 agent 於交卷以純文字附全文草稿）、RTM 子表、SCG-4 報告；根層 RTM 的 FR-SI-33、35 列；RELEASE 之後才做的 `Architecture.md` 去註（凍結檔）；其餘一律不動 |

---

## 6. RTM 連結確認

### 6.1 追溯

| 追溯項目 | 覆蓋狀態 |
|---------|---------|
| PRD FR-SI-33 的 AC-SI-33-1、33-2 與 FR-SI-35 的 AC-SI-35-1～35-5 → F-902 | ☑ 已映射（FRD-lite 追溯矩陣） |
| F-902 → US-908～US-916 | ☑ 已映射 |
| US-908～US-916 → 本檔 18 個 AC（PRD 的 7 個加本檔自增 11 個） | ☑ 已映射（FRD-lite） |
| PRD 的 7 個 P2b AC → 本檔 `AC-933-1`、`AC-933-2`、`AC-935-1`～`AC-935-5` | ☑ 已映射（編號規則見 FRD-lite 與 §7.1 ⚖ 1） |
| 18 個 AC → 本檔全部 98 個 AT | ☑ 已映射（本文件 §1） |
| PRD §8.1 P2b 出口 (a)～(e) → V 系列與 AT | ☑ 已映射：(a)→V5；(b)→全部 AT 與 V7；(c)→V4（掌舵者真機）；(d)(e)→V12；真機操作不由 AT 充當 |
| PRD §9.1 C18 的 P2b 列（檔名表）與〈C21〉的 AgentConsole 半 → D1～D10 | ☑ 已映射（FRD-lite 的 D 表；檔名微調由主控回寫 C18，§7.1 ⚖ 18） |
| 契約後繼檔 `API_Contract_SelfImproving_P2b.md`（W25） | ☑ 已映射（主控於 SCG-5 落檔、與實作同 commit；存在與範圍由 V8 核對） |
| P1b 殘留：P3-2（Playwright route-mock 閘）、P3-3（差分測試吃活 CLI，根層 P2 已落地須重跑）、P4-3（`schema.d.ts` 路徑集合無對拍鎖） | ☑ 已登記：前兩項併入 V7；P4-3 由 AT-950-10-2 順帶接上 |
| PRD 指定的 FR-SI 追溯主載體＝根層 RTM → 根層 RTM 的 FR-SI-33、35 列 | ☑ 已登記（主控於 SCG-5 依 Root_Layout SSOT 填） |
| AT → CI Pipeline | □ 未整合（測試檔入庫後由雲端 agentconsole-ci 的三個 job 一併執行；`paths` 連動見 AC-950-11） |

**行為規則 → AT 對映**（W1～W25 各至少被一個 AT 釘住；W25 為文件規則，由 V8 與 SCG-5 核對表承擔）

| 規則 | 內容 | 釘住它的 AT |
|------|------|-------------|
| W1 | Bridge 設定與寫入面啟用 | AT-950-1-1、AT-950-1-3、AT-950-2-E-1 |
| W2 | `store_audit` 獨佔建檔與錯誤 | AT-950-1-2、AT-950-1-E-1、AT-950-1-E-2、AT-950-1-E-3、AT-950-2-E-4 |
| W3 | 三個寫入路由的閘門序與 201 本文 | AT-935-3-E-2、AT-950-1-E-3、AT-950-2-1、AT-950-2-2、AT-950-2-3、AT-950-2-E-1、AT-950-2-E-2、AT-950-2-E-3、AT-950-2-E-4 |
| W4 | validate 與 `run_validate` | AT-935-1-E-4、AT-950-3-1、AT-950-3-2、AT-950-3-3、AT-950-3-E-1、AT-950-3-E-2 |
| W5 | AST 鎖判準 1′～5′ | AT-933-1-6、AT-933-1-E-3 |
| W6 | 夾具、`WRITE_CLOSURE`、`ingest_run` | AT-950-11-E-2 |
| W7 | 稽核 JSON 格式與簽章 | AT-933-1-4、AT-933-1-5、AT-933-1-E-4、AT-935-1-4、AT-935-1-E-4、AT-935-2-4、AT-935-2-E-3、AT-950-3-3、AT-950-4-1、AT-950-4-2、AT-950-4-E-1、AT-950-4-E-2、AT-950-4-E-3 |
| W8 | 向量與黃金檔 | AT-933-1-5、AT-935-1-4、AT-935-2-4、AT-950-4-1、AT-950-4-3 |
| W9 | backend 設定與金鑰 | AT-935-4-1、AT-935-4-E-1、AT-950-4-E-2、AT-950-5-1、AT-950-5-E-1、AT-950-5-E-2 |
| W10 | 閘門序（授權、停用、輸入） | AT-933-1-4、AT-935-3-E-1、AT-935-4-1、AT-935-4-E-1、AT-935-4-E-2 |
| W11 | 寫入用例與補償 | AT-933-1-4、AT-933-2-1、AT-935-1-3、AT-935-2-3、AT-935-3-1、AT-950-5-E-2、AT-950-6-1、AT-950-6-2、AT-950-6-3、AT-950-6-E-1、AT-950-6-E-2、AT-950-6-E-3 |
| W12 | 請求 DTO 與輸入閘 | AT-935-1-3、AT-935-1-E-3、AT-935-2-3、AT-935-2-E-2、AT-935-4-E-2、AT-950-7-1、AT-950-7-2、AT-950-7-E-1、AT-950-7-E-2、AT-950-7-E-3 |
| W13 | Flyway V13 與列不可改 | AT-933-2-1、AT-950-8-1、AT-950-8-2、AT-950-8-E-1、AT-950-8-E-2 |
| W14 | 對帳讀面與回填 | AT-933-2-E-1、AT-935-5-1、AT-935-5-2、AT-935-5-E-1、AT-935-5-E-2、AT-935-5-E-3 |
| W15 | 錯誤對映與三個 reason | AT-935-5-E-2、AT-950-6-1、AT-950-6-2、AT-950-6-3、AT-950-6-E-1、AT-950-6-E-2 |
| W16 | frontend API 層 | AT-933-1-2、AT-935-1-1、AT-935-2-2、AT-950-9-1、AT-950-9-E-1 |
| W17 | 純函式（`lib/domain/si.ts`） | AT-933-1-1、AT-933-1-3、AT-933-1-E-2、AT-935-1-2、AT-935-5-3、AT-950-9-2、AT-950-9-3、AT-950-9-E-3 |
| W18 | `SiDecideDialog` | AT-933-1-2、AT-933-1-3、AT-933-1-E-1、AT-933-1-E-2 |
| W19 | `SiObsForm` | AT-935-1-1、AT-935-1-2、AT-935-1-E-1、AT-935-1-E-2、AT-935-2-1、AT-950-9-3、AT-950-9-E-3 |
| W20 | `SiObsCloseDialog` | AT-935-2-2、AT-935-2-E-1 |
| W21 | `SiView` 接入與對帳面板 | AT-935-1-2、AT-935-2-1、AT-935-3-2、AT-935-4-2、AT-935-4-E-3、AT-935-5-3、AT-935-5-E-4、AT-950-10-E-1 |
| W22 | 靜態鎖 | AT-950-9-E-2 |
| W23 | 既有釘選測試同步 | AT-935-3-1、AT-950-8-2、AT-950-9-E-1、AT-950-10-1、AT-950-10-2、AT-950-10-E-1 |
| W24 | 部署與 CI | AT-950-1-3、AT-950-11-1、AT-950-11-2、AT-950-11-E-1 |
| W25 | 文件連動（契約後繼檔、RTM、Architecture 去註） | （文件規則，見 §6.2 的 V8 與 SCG-5 核對表） |

### 6.2 V 系列：實查檢核（QA、主控、掌舵者；**不是 AT**，結果寫進 SCG-4 報告與 RTM 備註；未驗者如實標「未驗」，構造情境不得充當）

| 編號 | 實查項 | 步驟與指令要點 | 通過判準與證據 | 再開症狀 |
|------|--------|----------------|----------------|----------|
| V1 | 全棧寫入通路（真 PG、真 backend、真 Bridge、真 CLI、可寫 bind） | 設 `BRIDGE_SI_WRITE_TOKEN`、`CONSOLE_SI_AUDIT_KEY`（與主機 `AUTOSDD_SI_AUDIT_KEY` 同一把）、`CONSOLE_SI_DECIDERS=admin`，`docker compose --profile db --profile app up -d --build`；以 admin 登入取 JWT，對 `POST /api/v1/si/observations/validate` 與 `POST /api/v1/si/observations` 各送表 M-O 的 O1；核對主機 `<AUTOSDD_SI_DIR>/console_audit/<auditRef>.json` 的 sha256 等於 backend 送出的位元組；主機端 `python tools/selfimproving.py obs-add --carrier console --audit-ref <auditRef>` | 兩個請求 200 與 201；檔存在且雜湊相符；CLI rc 0 且帳本多一列；指令輸出逐字貼入 | 檔位元組與簽出者不同、CLI 拒收、或 validate 的 `row_bytes` 與入帳列位元組數不同 |
| V2 | 真瀏覽器寫入流程（QA 以真後端操作；可擴充 e2e spec，不屬開發 agent） | ADMIN 開 `/self-improving`：新增觀察（先預檢後送出）、對待決卡下決定、對處置為 open 的列關閉；Operator 與 Viewer 登入確認零寫入控件；待入帳面板在主機入帳前顯示、入帳後消失；視窗 1440 與 375 各一輪（每個 spec 的 `--output` 指向自己的暫存目錄） | DOM 與回應一致；403 原因逐字出現在 toast；跑完 `git status --porcelain` 確認沒有已追蹤截圖被改動 | 控件對非 ADMIN 可見、或待入帳不消失 |
| V3 | 真容器：稽核 bind 可寫、其餘唯讀、缺席時明確失敗 | 見下方指令：容器內對 `$BRIDGE_SI_AUDIT_DIR` 寫入成功而對 `/repo/tools` 寫入失敗；主機端 CLI 讀得到容器寫的檔（Windows Docker Desktop 與 Linux 各一次）；主機目錄缺席時 `docker compose up` 因 `create_host_path: false` 明確失敗；`docker compose config` 顯示 engine-bridge 無 `ports` | 結論寫進 SCG-4 報告並於 RELEASE 之後的純文件 commit 回寫 Architecture §12.1 L-14（凍結檔）；證據＝指令輸出 | 容器寫入的檔主機讀不到或權限不符；或其餘 SI bind 變為可寫 |
| V4 | **掌舵者真機各一次 decide、obs-add、obs-close**（PRD §8.1 出口 (c)） | 掌舵者在真機（真帳本）以自己的 Admin 帳號各操作一次；主控於主機端以 CLI 入帳（`dec` 帶 `carrier=console`、OBS 列帶 `carrier=console;audit_ref=`） | 掌舵者回覆附 sid 與 line；AT、自動化截圖與構造情境不能充當；入帳輸出逐字貼入 | 入帳被拒（附 CLI 碼）、或 Console 與帳本對不上 |
| V5 | 專用金鑰通道（出口 (a)） | 兩端專用金鑰已配置；刻意清掉 `CONSOLE_SI_AUDIT_KEY` 再 POST（預期 503 `si_write_disabled`、`details.cause` 為 `audit_key_unset`）；清掉主機 `AUTOSDD_SI_AUDIT_KEY` 再入帳（預期 AUDIT-KEY-MISSING）；缺金鑰時 `promote` 拒絕 Console 載體 DEC（fail-closed） | 三個預期各有輸出；金鑰只在環境變數，不在 repo、日誌與回應 | 金鑰缺席時仍寫入或仍放行晉升 |
| V6 | 對帳實況（真 PG 與真帳本） | 入帳前 `GET /api/v1/si/console-writes` 顯示 `ingested` 為 false；入帳後為 true 且 obs-add 的 `subjectId` 被回填；人為刪除一個 DB 列造 orphan（預期紅色警示）；停掉 Bridge（預期 `reconcile.status` 為 NOT-EVALUABLE，不是空陣列） | 四個狀態各有 API 輸出與畫面證據 | 量不到卻顯示無待入帳，或回填誤動已有值的列 |
| V7 | 閘門全綠（各服務；含 P1b 殘留 P3-2、P3-3） | Bridge：`ruff check`（`AgentConsole/engine-bridge` 與 monorepo 根視角各一次）、全套 pytest（含 `test_si_export_differential.py`）、`GET /health`、根層 `tools/tests` 的 `TestDirEntryPrimitivesAreAccountedFor`；backend：`gradlew clean build`（Checkstyle、JaCoCo 80%、ArchUnit）；frontend：`npm run lint`、`npx tsc --noEmit`、`npm run build`、`npx vitest run`（覆蓋率 70%）、四區塊 grep 無輸出、後端在線時 `npm run gen:api` 後 `schema.d.ts` 無差異、Playwright route-mock `mock.spec`；根層：`AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py`、`python tools/selfimproving.py check` 的 rc 不變 | 各指令 rc 為 0（讀 rc 先存變數再讀）；輸出逐字貼入 SCG-4 報告 | 任一閘門紅 |
| V8 | 範圍守衛與契約後繼檔存在性 | (1) `git diff --name-only` 與 `git status --porcelain`（含未追蹤檔）對照 §5.7；(2) `AgentConsole/docs/02_architecture/API_Contract_SelfImproving_P2b.md` 存在且含 W25 的全部項目，路徑集合與 `/v3/api-docs` 的 `/api/v1/si/` 路徑一致 | (1) 只出現允許集合，零根層 `tools/`、`.claude/`、`.github/`（主控代做者除外）、凍結檔與既有 TCS；(2) 缺檔或缺列即紅 | 出現允許集合外的檔；或後繼檔缺端點列、缺 reason 表 |
| V9 | 雲端 CI | push 後 `agentconsole-ci` 的三個 job 皆綠；根層寫入閉包輸入變動會觸發該 workflow（AC-950-11 的實際效果） | `gh run list` 現查的 run 與結論 | 雲端紅而本機綠（平台差異） |
| V10 | 平台 | Windows 實跑全部 AT 與 V1～V6；macOS 標「未驗」；Linux 由 CI 承擔 | 報告載明各平台狀態 | Windows 與 CI 結果不一致 |
| V11 | 機密與日誌 | 對新增與修改檔跑機密掃描（無 `sk-` 形態）；`.env.example` 只有佔位；跑完 V1 後 `docker compose logs` 不含金鑰與權杖的任何 8 字元以上子字串 | 掃描與日誌檢查輸出逐字貼入 | 日誌或回應出現金鑰、權杖片段 |
| V12 | 入帳後的 `check` 與歷史（出口 (d)(e)） | V4 入帳後 `python tools/selfimproving.py check --json`：`events.dec_console` 與 `obs.console_audit` 為 PASS（基線的既有紅項不計）、全帳本無 `ROW-MUTATED`；`git log -p` 逐筆對照 DEC 與 OBS 列 | 輸出逐字貼入；DEC 與稽核檔逐欄相符 | `check` 出現 `ROW-MUTATED` 或 Console 載體項轉紅 |

V3 的關鍵指令（bash 與 PowerShell 同形；容器內只有 Linux）：

```bash
(cd AgentConsole && docker compose exec engine-bridge sh -c 'touch "$BRIDGE_SI_AUDIT_DIR/.probe" && rm "$BRIDGE_SI_AUDIT_DIR/.probe" && echo audit-dir-writable; touch /repo/tools/.probe 2>&1')
```

```powershell
Push-Location AgentConsole; docker compose exec engine-bridge sh -c 'touch "$BRIDGE_SI_AUDIT_DIR/.probe" && rm "$BRIDGE_SI_AUDIT_DIR/.probe" && echo audit-dir-writable; touch /repo/tools/.probe 2>&1'; Pop-Location
```

---

## 7. 本檔採用的預設裁決與開放問題（掌舵者可推翻；推翻走 T1 或本檔修訂，凍結前由主控回報掌舵者）

### 7.1 開放問題與預設（⚖ 1～⚖ 26；主控先行裁決 1～10 已裁，不在此列）

| 編號 | 問題（上位文件未定、內部矛盾或不可測處） | 本檔已採用的預設 | 替代與再開症狀 |
|------|----------------------------------------|------------------|----------------|
| ⚖ 1 | AC 編號：PRD 的 `AC-SI-NN-Y` 含字母，不合 ADR-XPLAT-016 §8.1 的 `AC-[\d\-]+` | 沿 P1b ⚖1：`AC-SI-33-Y`＝`AC-933-Y`、`AC-SI-35-Y`＝`AC-935-Y`；自增 AC 自 `AC-950-1` 起（P1b 已用 932 與 940） | 替代：編譯前置轉換（框架改動）。再開症狀：`sdd_compile` 回報 `unmapped_at_ids` 非空，或 RTM 對不上 PRD AC |
| ⚖ 2 | 稽核 JSON 的外層與 `body` 鍵序：PRD §9.2 只列欄位表，根層碼解析不看序，但簽章對象是 `body` 字串位元組 | 釘住 W7 的序（外層 schema_rev、kind、audit_ref、subject、body、key_id、mac；`body` 依表 M-D、M-O、M-C，沿 P2 TCS 向量）；Java 手工序列化輸出，不經 Jackson 物件樹 | 替代：交給 Jackson 預設序。再開症狀：向量 AT（AT-950-4-1、AT-950-4-2）轉紅，或序列化器升級改序 |
| ⚖ 3 | Console 閘比根層 CLI 嚴（accept-then-red，§7.2 發現 1）：CLI 對 approve 多帶 reason 或 flags、reject 的 reason 為空或含換行、觀察與關閉的字串欄含換行皆 rc 0 入帳而 `check` 轉紅（關閉的換行還毀損帳本列） | W12：backend 與 frontend 兩端拒收這些形態，不等 CLI；根層碼不改。原則（沿 PRD AC-SI-35-2「Console 端不重複實作第二份列規則」）：Console 只複製防 accept-then-red 與表單可用性所需的形態與列舉檢查，合法性判準（NOT-OPEN、存在性、retired 座標、前提態、digest 新鮮度）不複製 | 替代：等根層收緊（另立缺陷）。再開症狀：根層收緊後兩邊規則漂移，或掌舵者要求 Console 允許多行理由 |
| ⚖ 4 | `reason` 長度上限：PRD 未定；根層 `event_max_bytes` 為 4096，SA 實測 1,200 個 CJK 字元入帳、1,400 個回 EVENT-BYTES-OVER | 500 個 code point（最壞約 1,500 位元組，留餘裕） | 替代：1,000。再開症狀：掌舵者需要更長的理由 |
| ⚖ 5 | 觀察三字串欄的上限：PRD 只說「不超過 `ROW_MAX_BYTES`」，該數在根層 `params.json`（跨專案） | 每欄 ≤300 個 code point；三欄位元組和 ≤700 為必要條件，常數 700 寫在 backend 與 frontend；權威是 validate 回的 `rowMaxBytes` 與 CLI | 替代：backend 讀 `params.json`（新增跨專案耦合）。再開症狀：根層 `row_max_bytes` 變動而本檔常數未跟 |
| ⚖ 6 | `audit_ref` 的形態：PRD 只說 UUID，根層是否收大寫未定；檔名須等於外層 ref（`AUDIT-REF-MISMATCH`） | Bridge 與 backend 只收與產出小寫正規 UUID，其餘 422 | 替代：收大寫並正規化。再開症狀：主機端以大寫 ref 呼叫而找不到檔（Linux 大小寫敏感） |
| ⚖ 7 | 寫入順序與結果不明：PRD §9.3 逐字順序（先寫 DB 列、再簽、再呼叫）與 C18 欄位表（`mac`、`key_id` 為 NOT NULL）互斥，列要有 mac 就得先簽；§9.3 只定非 2xx 補償與逾時保留 | 簽章→INSERT→Bridge：INSERT 仍先於 Bridge，不改 §9.3 的 WHY（寧可有列無檔、不要有檔無列）；補償刪列＝確定未落檔（Bridge 明確拒絕、5xx 故障、連線階段失敗）；保留列＝結果不明（讀取逾時、送出後通訊失敗、2xx 本文無法解析；後兩者是本檔擴充，WHY 同「有檔無列」禁令）；不重試、每次新 ref | 替代：結果不明者也刪列（會有「檔在而列無」的紅色警示）。再開症狀：保留列後出現無法消去的幽靈待入帳（已知邊界 3） |
| ⚖ 8 | `console-writes` 讀路徑的副作用：回填 `subject_id`（主控先行裁決 4）與 GET 慣例衝突 | 只動 Console 自有表、只填 NULL、冪等、回應帶 `backfilled`；Bridge 永遠只被 GET | 替代：回填改由寫入端點或排程做。再開症狀：GET 回填造成並發錯誤或審稽質疑 |
| ⚖ 9 | `si_console_writes` 的不可改：PRD 只要求「不可改」，未定機制與回填的例外 | DB 觸發器拒絕任何欄位變動，唯一例外是 `subject_id` 由 NULL 變非 NULL；port 只有 insert、deleteByAuditRef、fillSubjectId 與唯讀查詢（本檔類推） | 替代：應用層約定、不設觸發器。再開症狀：觸發器與資料修補或 Flyway 回復衝突 |
| ⚖ 10 | 對帳的判準與深度：PRD 說比對 `si_console_writes`，未定「已入帳」與掃描範圍 | 已入帳＝帳本有同 `audit_ref` 的 `dec`／`obs.add`／`obs.close` 事件或標記同 `audit_ref` 的列；orphans 只計 `carrier=console` 者；observations 與 events 各最多 20 頁乘 500 筆，超限＝NOT-EVALUABLE | 替代：比 `audit_sha256`（可由表內 body、key_id、mac 重組外層位元組算出）。再開症狀：偽造者以相同 ref 與不同內容入帳而判不出 |
| ⚖ 11 | `export --kind status` 的 `console_pending` 恆為 NOT-EVALUABLE（§7.2 發現 2）：Console 無法經 Bridge 取得主機端待入帳清單 | Console 的待入帳以自己的 DB 表為準（表有、帳本無）；不讀 `console_pending` | 替代：Bridge 加讀家目錄（破壞唯讀鏡像的最小面）。再開症狀：掌舵者要求 Console 顯示非 Console 產生的待入帳檔 |
| ⚖ 12 | `decideVerbOptions` 的資訊不足：提案資料沒有 NE 的原因碼，無從判 `return` 的前提（須 FAIL 或沙盒失敗型 NE） | 只依 `state`、`route`、`verdict`、`cooldown` 提供動詞；NE 的 `return` 不提供；前提由 CLI 入帳時判（已知邊界 1） | 替代：根層 `export` 補 `reasons`（根層碼）。再開症狀：待入帳項頻繁被 CLI 以 PRECONDITION 類碼拒收，或掌舵者要退回 NE 提案而無此動詞 |
| ⚖ 13 | validate 只涵蓋 obs-add：根層只有 `obs-add --dry-run`，decide 與 obs-close 無預檢 | 不新增預檢；兩者的欄位閘（W12）是 Console 端唯一的事前保護 | 替代：根層加 dry-run（根層碼）。再開症狀：retired 缺座標等 CLI 才判得出的拒收比例高 |
| ⚖ 14 | 帳號名比對：PRD 未定大小寫與空白 | 與 JWT subject 逐字相等、區分大小寫；清單去空白、去空項、去重、保序 | 替代：不分大小寫。再開症狀：掌舵者帳號大小寫不一致被擋（403 `si_write_forbidden`） |
| ⚖ 15 | 金鑰環：PRD 說依 `key_id` 選，Console 簽章用哪一把未定 | 環中第一把簽章，其餘保留供根層驗舊檔（主機端環須含全部仍待入帳檔所用的金鑰）；兩端專用金鑰與 JWT 金鑰分開 | 替代：只准單把。再開症狀：輪替期間入帳出現 AUDIT-KEY-UNKNOWN |
| ⚖ 16 | Bridge 對稽核檔的信任：Bridge 不解 `body`、不驗簽（Architecture §10.2；F-12 訂正），持有權杖者可落任意外層合規檔 | 只靠權杖與 backend-net；垃圾檔由 CLI 入帳時擋；請求上限 65536 位元組 | 替代：Bridge 檔數或容量配額（新設定面）。再開症狀：稽核目錄被垃圾檔塞滿 |
| ⚖ 17 | 稽核 bind 的主機來源與缺席行為：PRD 只說可寫掛載到主機同一目錄 | 長語法、可寫、source 以 `console_audit` 結尾且由 `AUTOSDD_SI_DIR`（根層 CLI 同一變數）提供、`create_host_path: false`（缺席時 compose 明確失敗，README 要求先建目錄）；`AUTOSDD_SI_DIR` 未設時預設來源為 `~/.autosdd/selfimproving`（Windows 以 `%USERPROFILE%`、macOS 與 Linux 以 `$HOME` 展開，寫法不鎖）；其餘 SI bind 維持唯讀 | 替代：`create_host_path: true`（Linux 主機上會建成 root 擁有的目錄）。再開症狀：首次啟動因目錄缺席失敗被回報，或主機 CLI 讀不到容器寫的檔 |
| ⚖ 18 | PRD §9.1 C18 未列的檔名與簽名：`SiWriteGates`、`SiAuditRefSource`、`SiReconcileService`、`store_audit`、`run_validate`、`MiniBridge.Si` 寫入旋鈕、`AbstractSiWriteIT`、`SiWriteSeam` | 本檔釘住（測試需要穩定入口）；C18 表依其「檔名可微調並回寫本表」的約定由主控回寫 | 替代：完全照 C18。再開症狀：實作者改名使 AT 的類別路徑對不上 |
| ⚖ 19 | 既有 AT 的取代與改名：P2b 使 P1b 的 AT-932-2-1 與 2-E-1、2-5、2-7、2-8、AT-940-8-1 與 8-2 前提反轉（零寫入、六路徑）；AT-932-2-3、2-4、AT-940-3-1 與 3-E-1、4-1 與 4-E-1、5-1 只是部分前提改變 | 前者以本檔對應 AT 改寫並改名（§4），後者原地改寫保留名；凍結的 P1b TCS 不改，RTM 的 P1b 子表由主控同 commit 改指新 AT | 替代：保留原名並改斷言（名實不符）。再開症狀：RTM 的 P1b 子表指向已不存在的測試名 |
| ⚖ 20 | 契約後繼檔與 RTM 子表範圍 | 沿 P1b ⚖12、⚖27：新檔 `API_Contract_SelfImproving_P2b.md`（W25 清單，主控落檔）；RTM 本地子表列 F-902、US-908～US-916、全部 AC 與 AT | 替代：改凍結契約（走 T1）。再開症狀：後繼檔與 `/v3/api-docs` 漂移 |
| ⚖ 21 | 路徑形態：backend 的 `{id}/decide`、`{id}/close`、`observations/validate` 對 Bridge 的 `{id}:decide`、`{id}:close`、`observations:validate` | 依 Architecture §10.3 原樣（兩邊不同形）；`{id}` 嚴格編碼為單一路徑段（沿 P1b ⚖29） | 替代：兩邊同形。再開症狀：路徑編碼在某一側造成穿越或 404 |
| ⚖ 22 | validate 的資格：Architecture 說 Bridge 的 validate 不需權杖，但任務書要求 backend 四個 POST 同一關 | backend 對 validate 同樣要求 Admin 且在名單；Bridge 的 validate 仍不需權杖 | 替代：Operator 以上可預檢。再開症狀：非 Admin 需要預檢 |
| ⚖ 23 | 對帳面板的形態與位置：PRD 只說 Console 頁比對並顯示待入帳與紅色警示 | ADMIN 專屬、獨立於三分頁與狀態橫幅的 `si-writes-panel`；量不到時顯示 `si-reconcile-ne` 且不得顯示無待入帳 | 替代：橫幅徽章。再開症狀：掌舵者找不到待入帳項 |
| ⚖ 24 | 動詞標籤：PRD 動詞表是逐字稿語法，Console 下拉的中文標籤未定 | 沿 §7.2 動詞表的中文動詞，handoff route 的 reject 標「不轉交」；晉升後式標「晉升（未驗採納）」 | 替代：自由文案。再開症狀：標籤與逐字稿動詞對不上而誤選 |
| ⚖ 25 | 文件最小化的取捨：§3 只列 AT、AC、層與測試方法，描述與預期結果在 §1 與 §2 | 為本檔 ≤1,800 行與 ≤300KB（T1 前言「省去非必要文件」）；P1b 的 §3 含描述與預期結果 | 替代：照 P1b 全欄。再開症狀：審查者要求 §3 自足 |
| ⚖ 26 | 表單的位元組提示與關閉文字上限：PRD AC-SI-35-1 要求表單即時顯示預估位元組與 `ROW_MAX_BYTES`，C18 要求送出前先過 validate；PRD 未定關閉 `text` 的上限，而列上限為 700 位元組（主控裁決） | (a) 兩者並存：表單邊打邊以前端純函式 `estimateRowBytes`（`lib/domain/si.ts`，與 CLI 同一九欄組列規則，僅供提示）即時顯示估計值與 `row_max_bytes`，送出時再走 validate（權威），ok 為 true 才 POST；(b) 關閉的 `text` 不超過 120 個 code point（360 位元組上界，與列上限相容；權威仍是 CLI 的 ROW-BYTES-OVER，validate 不涵蓋關閉，⚖13） | 替代：(a) 只靠 validate（失去即時性）；(b) 沿用 300。再開症狀：(a) 估計值與 validate 的 `row_bytes` 在常見輸入下不同（列號位數、標記欄組成）；(b) 掌舵者需要更長的關閉說明，或 120 仍常被 CLI 以 ROW-BYTES-OVER 拒收 |

### 7.2 SA 對根層碼與上位文件的發現（供主控處理；本檔未改任何凍結檔，根層碼不改）

1. **accept-then-red（根層 CLI 的入帳判準鬆於 `check`）**：SA 以真 CLI 在複本倉實跑稽核檔變形——approve 多帶 `reason` 或 `flags`（入帳 rc 0；`check` 出現 `events.structure` 的 EVENT-KEY-UNKNOWN）、reject 的 `reason` 為空或含換行（rc 0；EVENT-TYPE）、obs-add 的字串欄含換行（rc 0；`ledger.structure` 的 ROW-ARITY）、obs-close 的 `disposition` 含換行（rc 0；ROW-ARITY、`history.row_mutated` 的 ROW-MUTATED 與 EVENT-TYPE，**帳本列被毀**）。PRD AC-SI-33-1、35-1、35-2 把合法性判準歸 CLI，但碼未擋這些形態。本檔以 W12 在 Console 兩端擋下（⚖3）；建議主控另立根層缺陷（本檔不引新缺陷編號）。
2. **`export --kind status` 的 `console_pending` 恆為 NOT-EVALUABLE**（reason 為 `export-reads-no-home`）：PRD AC-SI-35-5 的「`si status` 另列 `console_audit/` 內尚未入帳的稽核檔」只在 `status` 動詞成立，而 Bridge 只准 `export`；Console 無法取得主機端待入帳清單，改以自己的 DB 表為準（⚖11）。
3. **`obs-add --dry-run` 對非 JSON 的 stdin 回 rc 3**（其餘違規回 rc 1 與 `ok` 為 false）：Bridge 的請求預檢保證子行程只收到 JSON 物件，故不會觸發；若仍觸發＝503 `nonzero_rc`（W4）。登記以免誤判為 Bridge 缺陷。
4. **Architecture §10.3 對 validate 與寫入的失敗列只列 Bridge 層**：backend 層另有 401、403 `ACCESS_DENIED`、403 `si_write_forbidden`、503 `si_write_disabled`（`cause`：`audit_key_unset`、`bridge_token_unset`）、504 等，由後繼契約 W25 載明；Architecture 去註於 RELEASE 之後的純文件 commit（凍結檔，本檔不改）。
5. **PRD §9.1 C18 的 `si_console_writes` 欄位表沒有 `audit_sha256`**：本檔不增欄；⚖10 的替代案可由表內 `body`、`key_id`、`mac` 重組外層位元組後計算。
6. **PRD §9.2〈Console 稽核 JSON〉（與 R94）的 `digest` 與根層碼不一致**：PRD 的 `decide` 欄位表寫 `digest`（`resume` 無）＝除 resume 外皆必備；根層 `_console_body_codes` 只在六個綁卡面的 dkind（approve、reject、return、promote、decline-promote、ack-handoff）要求 `digest`，rollback 與 unblock 的事件不帶 digest。本檔依碼：表 M-D 對 rollback、unblock、resume 禁止 `digest`。

---

## 📋 SCG-4 通過標準

| 驗證項目 | 判斷標準 | 狀態 |
|---------|---------|------|
| AC → AT 100% 映射 | 無未映射 AC（18 個 AC 皆至少一個 AT） | □ |
| AT 格式可自動化 | 使用 Given-When-Then 格式；每個 AT 可單跑（Bridge `-k`、backend `--tests`、frontend `-t`）；每個 AT 的驗收字樣逐字出現在最終回覆 | □ |
| 負向測試覆蓋 | 每個 AC 至少一個負向或負控 AT；負控數不少於正控數（49 對 49） | □ |
| 邊界值測試 | reason 500 與 501、單欄 300 與 301、三欄位元組和 700 與 701、關閉 `text` 120 與 121、請求 65536 位元組、`limit` 邊界、毫秒截斷、UTC 形態皆有對照 | □ |
| 與根層碼逐位元相容 | 黃金檔 G1～G5 被真 CLI 收下、向量 V1～V4 與負控跨語言逐字相等（AT-933-1-5、AT-935-1-4、AT-935-2-4、AT-950-4-1、AT-950-4-3） | □ |
| 測試資料規格完整 | 資料來源明確（§5）；夾具與黃金檔可重現；ID 引用只用真帳本已存在者 | □ |
| 出口與 V 系列 | V1～V12 有結果與證據；V4 為掌舵者真機回報；未驗者如實標記 | □ |

**確認人**: ____________  **確認日期**: ____________  **狀態**: □ 通過 / □ 待修訂

---

## 勘誤（本檔凍結之後的訂正；凍結前留空）

| # | 日期 | 位置 | 原文（摘） | 訂正 | 依據 |
|---|------|------|-----------|------|------|
