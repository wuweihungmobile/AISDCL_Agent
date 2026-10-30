# SelfImproving 帳本改 DB：Architecture 補丁草稿（D4；P0 不套用）

- 性質：**草稿**。本檔備妥要插進 `AgentConsole/docs/02_architecture/Architecture.md`（§7.2、§9.4、§10.3 三處）與 `AgentConsole/docker/README.md`〈4.3〉的補丁原文；P0 **不改**那兩個檔（位元組不變，避免對 `agentconsole-si-decide`、`agentconsole-si-mirror` 兩鍵造成未 refreeze 的漂移）。
- 規格：`docs/01_requirements/SelfImproving_Ledger_DB_PRD.md` §8.2、§9.2～§9.4、FR-LD-08、FR-LD-09；`docs/03_testing/contracts/TCS-SelfImprovingLedgerDb-P0-20261027.md` 契約節 C3；決定背景見 `ADR-SIDB-001`（真相源與 DB 位置，B 或 C 方案取決於它）、`ADR-SIDB-006`（Console 載體）、`ADR-SIDB-007`（憑證）。
- 兩個變體：**B 方案**＝Console 既有 PG 加 `si` schema；**C 方案**＝專屬 PG 容器（ADR-SIDB-001 的建議，P3 進場前須定案）。補丁只在採用該方案時套用，每塊標明差異。
- 座標說明：下列「目標檔」行號是 P0 起點（TCS 凍結）的座標；之後 `Architecture.md` 因其他案的文件連動已位移（現行 HEAD `fdd9a738` 的位置另註於各塊），**套用時一律以標題錨點定位，不信行號**，並在套用 commit 重核。
- 套用路由：各塊依自己的「生效階段」由該階段的鍵套用（TCS §7.1#2、§7.3：§9.4→P1、§10.3→P2、§7.2 與 docker README〈4.3〉→P3；Console 分鍵 `agentconsole-si-ledgerdb-p2` 自 P2 起才有，P1 只有根層鍵 `monorepo-si-ledgerdb-p1`，§9.4 塊在 P1 的套用載體由 P1 TCS 定），套用後 `spec-refreeze` `agentconsole-si-decide` 與 `agentconsole-si-mirror` 兩鍵（Architecture 摘要聯集所在）；P4 連動面收尾時重核全部三塊。
- 階段規則：每塊的「生效階段」只有一個值；屬於較後階段的列或段落，放在它自己生效階段的塊內並標明目標位置（`console.si.read-source` 與 `CONSOLE_SI_DB_URL`／`_USERNAME`／`_PASSWORD` 兩個 P2 列放 §10.3 塊，`console.si.write-carrier` 一列與寫入載體契約段兩個 P3a 項放 §7.2 塊的「隨 P3 同批」小節），避免前一階段套用時把尚未存在的旗標與契約寫進 `Architecture.md`（TCS §7.1#2 的理由：`si.*` 表建好前寫進去是不實陳述）。

## 補丁 §7.2 資料所有權（`si.*` 表）

目標檔：`AgentConsole/docs/02_architecture/Architecture.md:612-618`（P0 起點座標：§7.2 表，末列為 `issue_priority`；現行 HEAD 為標題「### 7.2 其他表所有權與狀態映射」下的表，位於 `:620-627`，末列已是 `backup_jobs`；於表尾追加）。
插入文：見下方 B、C 兩方案各一列；每列只給表格列原文，欄位沿現有三欄（表｜寫入者｜讀取者）；另有「隨 P3 同批」小節（P3a 的旗標列與契約段，目標在 §9.4 表與 §10.3）。
生效階段：P3（TCS §7.1#2、§7.3）
階段說明：`si` 成為真相源前補上資料所有權列。P1 的影子寫入只由根層 CLI 做；P2 起 console-api 的唯讀直讀是非預設旗標〔`console.si.read-source=db`〕，其契約句隨 §10.3 塊於 P2 套用。
路由：`agentconsole-si-decide`、`agentconsole-si-mirror`。

### B 方案（Console PG 加 si schema）

插入文：

```markdown
| `si.*`（14 張表，帳本改 DB PRD §9.3；`si` schema 與 `console` 同庫，由根層遷移執行器的 `V<NNN>__*.sql` 建立，**不走 Flyway**，`ddl-auto=validate` 不檢查本 schema） | **根層 `tools/selfimproving.py` 的寫入動詞**（唯一；以 `si_writer` 角色，非表擁有者、不能停用觸發器；遷移與切換用 `si_owner`，平時不用）；console-api 與 Bridge 對 `si.*` 零寫入（AC-LD-09-3；Console 載荷列在 `console.si_console_writes`，不在 `si`） | console-api 以 `si_reader`（唯讀、獨立 DataSource）讀取讀模型表（`si.issues`、`si.export_items`、`si.export_meta`；P2 起，旗標 `console.si.read-source=db`）；Bridge 不讀不寫，仍只經 `si export` 子行程取數 |
```

代價與注意：與 `console` 同卷，`docker compose down -v` 一次清場會一併清掉 `si`（治理資料全失）；ADR-SIDB-001 因此把「DB 生命週期隔離」列為 P3 進場條件（PRD §8.1 H2）。B 方案下 `console` 表的備份與還原核對須同時涵蓋 `si`（見本檔 docker/README.md 補丁）。

### C 方案（專屬 PG 容器）

插入文：

```markdown
| `si.*`（14 張表，帳本改 DB PRD §9.3；位於**專屬 PG 容器**〔服務名草案 `si-postgres`，P1 TCS 定稿〕的 `si` schema，與 Console 的 `console` schema 不同庫、不同卷；由根層遷移執行器建立，不走 Flyway） | **根層 `tools/selfimproving.py` 的寫入動詞**（14 表的唯一寫入者；`si_writer`，遷移與切換用 `si_owner`）；專屬容器內另有 `si.console_requests`（不在 14 表內；只准 console-api INSERT，載荷見 `ADR-SIDB-006` 的 B′），除此之外 console-api 與 Bridge 對 `si.*` 零寫入（AC-LD-09-3） | console-api 以 `si_reader` 經專屬連線唯讀讀取讀模型表（P2 起，旗標 `console.si.read-source=db`；需 console-api 所在網路可達專屬容器）；Bridge 不讀不寫 |
```

代價與注意：多一個容器與一組備份面；換得 `down -v` 清 Console 資料時 `si` 不受影響（PRD §8.2、ADR-SIDB-001 建議值）。連線憑證不進 `AgentConsole/.env`（D-5；見 §9.4 補丁）。

### 隨 P3 同批：P3a 的寫入載體旗標列與契約段

目標：`Architecture.md` 的 §9.4 環境變數表（緊接 P1 的三列與 P2 的兩個追加列之後）與 §10.3（緊接 P2 的「讀取源與 Bridge 的關係」段之後）。生效階段同本塊（P3）：旗標 `console.si.write-carrier` 隨 P3a 的 AC-LD-09-1 落地、`db` 值於 P3a 生效，兩處都不得在 P1、P2 套用。B、C 方案共用。

§9.4 表的追加列：

```markdown
| `console.si.write-carrier`（`application.yml`／`CONSOLE_SI_WRITE_CARRIER`） | backend | `file`（預設，現況：Bridge 落稽核檔，`si_console_writes` 照寫）、`dual`（兩者並存）、`db`（只寫表列、含原始位元組欄，Bridge 不再落檔）；回退＝旗標改回前一值，切換前 `console_pending` 須為 0 |
```

§10.3 的追加段：

```markdown
**寫入載體（P3a 起）**：旗標 `console.si.write-carrier` 決定簽章載荷的落點：`file` 時 Bridge 照 §10.2 把稽核 JSON 原樣獨佔建檔（現況）；`dual` 時兩者並存；`db` 時 console-api 只寫表列（含原始位元組 `raw`），Bridge 的 `si_audit.py` 路徑不再被呼叫，主機端 `si decide`／`obs-add`／`obs-close --carrier console --audit-ref` 自表驗簽入帳。Bridge 對帳本的寫入面不擴張：仍無任何寫入型 CLI 動詞；P4 才移除 `routers/si.py`、`si_cli.py`、`si_audit.py`。
```

## 補丁 §9.4 環境變數

目標檔：`AgentConsole/docs/02_architecture/Architecture.md:854-870`（P0 起點座標：§9.4 環境變數表；現行 HEAD 為標題「### 9.4 環境變數」下的表，位於 `:867-881`；於 `BRIDGE_DB_DSN`／`BRIDGE_DB_SCHEMA` 列之後、`BRIDGE_INSTANCE` 列之前追加）。
插入文：下方三個表格列（B、C 方案共用，僅 `SI_DB_DSN` 的連線目標不同，已在說明欄註明）。
生效階段：P1（TCS §7.1#2、§7.3）
階段說明：本塊只含 `SI_DB_DSN`、`PGPASSFILE`、`SI_LEDGER_STORE` 三列。較後階段的列不在本塊：`console.si.read-source` 與 `CONSOLE_SI_DB_URL`／`_USERNAME`／`_PASSWORD` 兩列（P2）隨 §10.3 塊插入，`console.si.write-carrier` 一列（AC-LD-09-1，P3a）隨 §7.2 塊的「隨 P3 同批」小節插入；三列的目標同為本表，緊接下列三列之後。
路由：`agentconsole-si-decide`、`agentconsole-si-mirror`。

```markdown
| `SI_DB_DSN` | 根層 CLI（`tools/selfimproving.py`） | SelfImproving 帳本 DB 的連線字串（libpq keyword 形式，**不含密碼**）；有設且 `--repo` 為 CLI 所在 checkout 根時，模式由 `file` 升為 `shadow`（`LEDGER_TRUTH` 為 `db` 時為真相源）。B 方案指向 Console PG 的 `si` schema，C 方案指向專屬容器。**不讀 `AgentConsole/.env`**（帳本改 DB PRD D-5）；非 loopback 須 `sslmode` 至少 `require`，loopback 可 `prefer` |
| `PGPASSFILE` | 根層 CLI | libpq 的密碼檔路徑（內容 `<YOUR_SI_DB_PASSWORD>` 之類由各機器自設，不入 repo）；`db` 模式缺憑證＝fail-loud（不退回檔案模式的靜默讀寫）；`shadow` 模式不擋、印一行並標「量不到」（`ADR-SIDB-007`、AC-LD-04-2） |
| `SI_LEDGER_STORE` | 根層 CLI（僅測試與彩排） | 強制指定儲存後端（`file` 等）；`--repo` 非 checkout 根時靜默生效，否則 stderr 橫幅；測試夾具自 P1 起設為 `file`，避免開發機有 DSN 時寫到真影子庫 |
```

## 補丁 §10.3 SelfImproving 鏡像與寫入載體（Bridge 契約句）

目標檔：`AgentConsole/docs/02_architecture/Architecture.md:944-956`（P0 起點座標：§10.3；現行 HEAD 為標題「### 10.3 SelfImproving 鏡像與寫入載體」，位於 `:956-968`；於端點表之後、「backend 對應 `GET /api/v1/si/**`」段落之前追加）。
插入文：下方一段（B、C 方案共用；不改現有端點表），另附 §9.4 環境變數表的兩個 P2 追加列。
生效階段：P2（TCS §7.1#2、§7.3）
階段說明：`ledger-digest` 與旗標 `console.si.read-source` 於 P2 落地。P3a 的「寫入載體」段不在本塊，隨 §7.2 塊的「隨 P3 同批」小節於 P3 套用。
路由：`agentconsole-si-decide`、`agentconsole-si-mirror`。

```markdown
**讀取源與 Bridge 的關係（P2 起）**：旗標 `console.si.read-source=bridge`（預設）時行為與現況完全相同；`=db` 時 console-api 直讀 `si` 讀模型，`GET /api/v1/issues`、`/api/v1/si/*` 的請求路徑對假 Bridge 零請求，回應與 `bridge` 模式逐值相同，讀模型落後帳本鏈頭時 `ne` 含 `READ-MODEL-STALE`；唯一例外是 `FILE-DRIFT` 比對用的 `ledger-digest`——以 TTL ≥30 s 快取、逾期後非同步刷新、不阻塞請求，Bridge 不可達時略過（AC-LD-08-4）。Bridge 的 `/si/*` 六條 GET 保留作為預設與退路，並新增 `GET /si/ledger-digest`（唯讀，供 `FILE-DRIFT` 比對）。P2 的 Bridge 仍不連 `si` 資料庫、不持有 `SI_DB_DSN`，取數只經 `tools/selfimproving.py export` 子行程，其中 `ledger-digest` 不連 DB（AC-LD-08-4）；P3b 起若 Bridge 讀源的 CLI 子行程在 `db` 模式需要 `SI_DB_DSN`，憑證供應另案決定，不在本補丁範圍。
```

§9.4 表的 P2 追加列（目標位置同上方 §9.4 補丁，緊接 P1 的三列之後）：

```markdown
| `console.si.read-source`（`application.yml`／`CONSOLE_SI_READ_SOURCE`） | backend | `bridge`（預設，現況）或 `db`；`db` 時 `GET /api/v1/issues`、`/api/v1/si/*` 由 console-api 直讀 `si` 讀模型、請求路徑不呼叫 Bridge（`FILE-DRIFT` 用的 `ledger-digest` 例外，見 §10.3） |
| `CONSOLE_SI_DB_URL`／`_USERNAME`／`_PASSWORD` | backend | console-api 讀 `si` 的唯讀 DataSource（`si_reader` 角色）；密碼只來自環境變數或機密檔，不入映像、不入 `.env.example` 實值（只放 `<YOUR_...>`）；名稱為草案，P2 TCS 定稿 |
```

## 補丁 docker/README.md〈4.3〉還原核對清單加 si

目標檔：`AgentConsole/docker/README.md`〈4.3 還原（整庫還原或 PITR）〉之「還原後核對資料列數」三項核對（P0 起點座標由 PRD 記為 `:274` 附近；現行 HEAD 約 `:273-284`，以小節標題定位）。
插入文：見 B、C 兩方案；兩方案都修改核對項 1 的查詢範圍並增列判準句。
生效階段：P3（TCS §7.1#2、§7.3）
階段說明：`si` 成為真相源、進入備份面之前；P1、P2 的影子庫可丟可重建，不需此核對。
路由：`agentconsole-si-decide`、`agentconsole-si-mirror`（docker README 屬 Console 運維面；與 Architecture 同批 refreeze）。

### B 方案（Console PG 加 si schema）

插入文：把核對項 1 查詢的 `WHERE table_schema = 'console'` 改為 `WHERE table_schema IN ('console', 'si')`，並在判準段落後追加下列一句。

```markdown
`si` schema（SelfImproving 帳本）與 `console` 同庫：還原後第 1 項須同時列出 `si` 的各表精確列數，`si.audit` 的列數須與災難前一致或符合 PITR 目標點，且 `si check` 的 `chain.intact`、`readmodel.fresh` 兩項須全綠（`si.meta` 的 `ledger_head` 與稽核鏈頭一致）；`si` 表缺失或為空而 `console` 正常＝`down -v` 或不完整還原的特徵，須走 `ADR-SIDB-008` 的快照與離機備份路徑重建，不得宣告還原成功。
```

### C 方案（專屬 PG 容器）

插入文：核對項 1 的查詢不變（只涵蓋 `console` schema）；追加獨立小節，專屬容器的還原核對在其自己的 compose 服務內做。

```markdown
**SelfImproving 專屬 PG 容器的還原核對**（C 方案）：`si` schema 不在 `postgres-primary`，上列三項核對不涵蓋它。專屬容器還原後須另在該容器內核對 `si` 各表精確列數、`si.audit` 列數與 `si.meta` 的 `ledger_head`、時間軸與備份鏈檢查；`docker compose down -v` 清 Console 資料不影響專屬容器的卷，但清它的卷＝治理資料全失，須走 `ADR-SIDB-008` 的快照與離機備份路徑重建。具體服務名與指令於 P1 TCS 定稿後填入。
```
