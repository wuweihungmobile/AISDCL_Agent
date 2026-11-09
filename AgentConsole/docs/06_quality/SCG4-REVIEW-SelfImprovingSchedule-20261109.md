# SCG-4 獨立審查報告：鍵 `agentconsole-si-schedule`（SelfImproving P4「自動演化排程」Console 半）

審查者：Sonnet QA 鏡（唯讀，未參與規格與實作）｜日期：2026-11-09｜審查基準 HEAD：`40d894bd`
審查載具：repo 外 worktree `C:\Users\wuwei\AppData\Local\Temp\si_qa_console_wt`（共用工作樹一個位元組未碰；審查結束 worktree 乾淨，所有突變皆還原並核 SHA256 相同）
Oracle：`AgentConsole/docs/03_testing/contracts/TCS-SelfImprovingSchedule-20261109.md`（§7.1 裁決 D-CS-1～25 優先）

## A 判定

**PASS**（P1 0、P2 0、P3 1、P4 5）。

- 69 個 AT 全部有對應測試函式，且本輪逐區親跑全綠（BE 20、BR 10、FE 36＋PW 3；合計 69）。
- 有效突變 32 個（BE 12、BR 8、FE 12）：29 個被紅燈抓到，3 個存活且皆為等價突變或死碼（F-1～F-3，P4）；另 1 個無效突變（BR-M6）不計。
- 跨半接縫兩個 AT（AT-964-9-3、AT-964-9-E-1）首跑與結尾重跑皆通過（見 C 節末段）。
- 無金鑰外洩、無未授權寫入路徑（非 ADMIN 在安全層即 403，且 AT-964-7-E-1 與突變 BE-M11、BE-M12 證明有牙）。

## B 發現表

| 編號 | 嚴重度 | 座標 | 症狀 | 重現 | 建議修法 |
|------|--------|------|------|------|----------|
| F-1 | P4 | `frontend/lib/domain/si.ts:900`；`siParts.tsx:345` | `SCHEDULE_PENDING_TEXT` 匯出常數全樹無人引用（死碼）；收據真正顯示的「稽核檔已落地，待入帳」是 `siParts.tsx` 的字面。對該常數的突變（改成「已生效」）無測試變紅（FE-M6）；改 `siParts.tsx` 字面則 5 個 AT 變紅（FE-M6b），所以 NFR-SC-1 實際仍被守住，只是常數是多餘的第二個真相源 | 把 `si.ts:900` 的值改成「已生效」跑 `npx vitest run components/domain/si lib/domain/si.test.ts`＝0 失敗 | 刪常數，或讓 `SiWriteResult` 引用它 |
| F-2 | P4 | `SiScheduleDialog.tsx:70`、`SiRunRequestDialog.tsx:55` | `submit()` 內的 `blocked !== null` 前置守門拿掉，測試仍全綠（FE-M9）。AT-964-3-E-2 以「點被停用的鈕」驗零 POST，走不到 submit 內的守門；依 HTML 隱式送出規則（預設鈕被停用時 Enter 不送出）此守門在瀏覽器內屬冗餘防線，故判等價突變——但**未以實際 Enter 鍵測試驗證**（見 G） | 突變 FE-M9 | 補一個 `fireEvent.submit(form)` 的案例，或承認為冗餘而刪守門 |
| F-3 | P4 | `engine-bridge/app/routers/si.py:147-149` | Content-Length 宣告值提早拒收那段拿掉後，AT-964-8-E-2 仍全綠（BR-M5）：逐塊累計的上限檢查獨立擋得住「不讀完」。兩者同時拿掉才紅（BR-M7）。屬縱深防禦重複，非缺陷 | 突變 BR-M5 | 可在測試加一個「宣告長度超限但實際串流極短」的案例讓兩道各有牙，或維持現狀 |
| F-4 | P3 | `Architecture.md` §12.1 L-SI-1（行 2177）、L-SI-2（行 2178） | 兩列仍標「〔P4 規劃 2026-11-09〕」，而 §3／§5.6／§10.3 已去註；AT-964-10-3 只掃 §5.6 與 §10.3，所以沒有抓到。TCS W-S10 (c) 只要求「兩列保留」，不算違規，但與 D-CS-24 去註方向不一致 | 檢視 Architecture §12.1 | 把「P4 規劃」改成「P4 已落地」，或在 TCS 勘誤記為刻意保留 |
| F-5 | P4 | `BridgeHttpAdapterSiWriteTest` 的 `AT_964_7_theTwoScheduleWrites…` | 測試名帶 `AT_964_7_` 前綴但不是 §1 的任何 AT（覆蓋對帳中唯一「測試有、規格無」者）；功能上是額外的轉接層單元測試，有益 | 覆蓋對帳 | 改名去掉 AT 前綴，避免被工具誤判為 AT |
| F-6 | P4 | `SiScheduleDialog.tsx:122` | 「理由」宣稱單行，卻用 `Textarea rows=2`；貼上換行會被正確擋下（AT-964-3-E-3 涵蓋），只是控件形態與「單行」不一致 | 開排程對話框 | 改單行 `Input`（與立即啟動的備註一致） |

結論：無 P1／P2。F-4 為唯一 P3（文件標註）。

## C 逐 AT 親跑表

### C.1 backend（cwd＝worktree `AgentConsole/backend`；`gradlew.bat cleanTest test --tests …`；讀 XML 結果）

首跑 9 個類別（SiScheduleWriteApiIT、SiConsoleWritesReadApiIT、SiKeyNamesTest、BridgeHttpAdapterSiWriteTest、SiAuditSignerTest、SiReadOnlyArchTest、IssueBridgeArchTest、OpenApiIT、SiConsoleWritesMigrationIT）：gradle `BUILD SUCCESSFUL in 59s`，各類別 0 失敗（10、14、5、7、11、4、2、35、4 個測試）。另跑回歸 `*MigrationIT`、`SiConsoleWriteApiIT`、`SiMirrorApiIT`、`SiWriteGatesTest`：rc=0，137 個測試 0 失敗（含 Flyway 全部 MigrationIT、既有 P2b 24 個寫入 IT）。

| AT | 測試（類別::方法前綴） | 結果 |
|----|------------------------|------|
| 964-7-1 ～ 7-5 | SiScheduleWriteApiIT::AT_964_7_1 … AT_964_7_5 | 通過 |
| 964-7-6 | SiConsoleWritesMigrationIT::AT_964_7_6 | 通過 |
| 964-7-7 | OpenApiIT::AT_964_7_7 | 通過 |
| 964-7-8 | SiKeyNamesTest::AT_964_7_8 | 通過 |
| 964-7-9 | SiReadOnlyArchTest::AT_964_7_9 | 通過 |
| 964-7-E-1 ～ E-5 | SiScheduleWriteApiIT::AT_964_7_E_1 … E_5 | 通過 |
| 964-9-1、9-2 | SiAuditSignerTest::AT_964_9_1（2 個）、AT_964_9_2 | 通過 |
| 964-9-4、9-5、9-E-2、9-E-3 | SiConsoleWritesReadApiIT::AT_964_9_4 / 9_5 / 9_E_2 / 9_E_3 | 通過 |

### C.2 engine-bridge（cwd＝worktree `AgentConsole/engine-bridge`；根 `.venv` 的 python；`-k 964`）

`pytest tests/test_si_write_routes.py tests/test_si_audit_filename_safety.py tests/test_si_console_ingest.py tests/test_si_readonly_lock.py -k 964`：rc=0，26 通過（含參數化展開）。

| AT | 測試 | 結果 |
|----|------|------|
| 964-8-1、8-2、8-3 | test_si_write_routes（G6～G9 參數化、內層 body 不重寫、外層七鍵） | 通過 |
| 964-8-4 | test_si_readonly_lock（路由普查、五判準、三個注入副本各被判出） | 通過 |
| 964-8-5 | test_si_audit_filename_safety | 通過 |
| 964-8-E-1、E-2、E-3 | test_si_write_routes（subject／kind、閘門序、I/O 失敗 503、超量 422 不讀完、405） | 通過 |
| 964-9-3 | test_si_console_ingest::AT_964_9_3（黃金檔副本＝backend、真根層 CLI 收下） | 通過 |
| 964-9-E-1 | test_si_console_ingest::AT_964_9_E_1（Python 向量驗簽、鍵序對調被 CLI 以 MAC 不符拒收） | 通過 |

### C.3 frontend（cwd＝worktree `AgentConsole/frontend`；node_modules 為實體複本，見 G）

- `npx vitest run components/domain/si lib/domain/si.test.ts lib/api/si.endpoints.test.ts lib/api/endpoints.test.ts lib/help/content.test.ts`：rc=0，517 通過、0 失敗（含 95 個帶 AT_964 名稱的斷言節點）。
- `npx tsc --noEmit` rc=0（0 行輸出）；`npm run lint` rc=0；`npx prettier --check "**/*.{ts,tsx,mts,mjs}"` rc=0；`npm run build`（`NEXT_PUBLIC_API_URL=http://localhost:8080`）rc=0。
- Playwright `tests/e2e/self-improving-schedule.mock.spec.ts`（`E2E_MODE=standalone`、`E2E_WEB_PORT=3100`）：rc=0，3 通過（AT_964_2_4、AT_964_3_4、AT_964_4_4），輸出目錄放 scratchpad，無截圖覆寫。

| AT | 檔 | 結果 |
|----|----|------|
| 964-1-1、1-2、1-E-3、5-1、5-2、5-3、6-1 | SiSchedulePanel.test.tsx | 通過 |
| 964-1-3、1-E-2 | SiView.test.tsx | 通過 |
| 964-1-E-1、2-1、2-E-1（純函式）、3-2、3-E-3、4-3（純函式）、4-E-2、5-E-1、10-E-1 | lib/domain/si.test.ts | 通過 |
| 964-2-2、2-3、2-E-1、2-E-2、3-1、3-3、3-E-1、3-E-2、6-2、6-3、6-4 | SiScheduleDialog.test.tsx | 通過 |
| 964-4-1、4-2、4-3、4-E-1 | SiRunRequestDialog.test.tsx | 通過 |
| 964-6-E-1、6-E-2、10-3 | si.static.test.ts | 通過 |
| 964-10-1 | lib/help/content.test.ts | 通過 |
| 964-10-2 | lib/api/si.endpoints.test.ts | 通過 |
| 964-2-4、3-4、4-4 | Playwright mock | 通過 |

### C.4 跨半接縫

- 首跑（`-k 964` 整組）：AT_964_9_3、AT_964_9_E_1 皆通過（`test_si_console_ingest.py` 2 通過）。夾具 `CLI_CLOSURE` 手列檔已補齊，無缺檔錯誤。
- 結尾重跑：見 C.5。

### C.5 結尾重跑（最終狀態）

結尾重跑（審查最後一步，同一 worktree、同一 HEAD）：`pytest tests/test_si_console_ingest.py -k "AT_964_9_3 or AT_964_9_E_1"` rc=0，2 通過、21 取消選取；整組 `tests/test_si_*.py` rc=0，263 通過；`ruff check app tests` rc=0（All checks passed）。**兩個接縫 AT 最終狀態＝通過**，無「根層造成」的紅。

## D 覆蓋對帳

- TCS §1 抽出 AT 69 個（程式比對，非肉眼）；測試原始碼（backend、engine-bridge、frontend 三棵樹）出現的 AT 底線形 70 種。
- 規格有、測試無：0。測試有、規格無：1（`AT_964_7`，即 F-5 的 `BridgeHttpAdapterSiWriteTest` 額外轉接層測試，非缺陷）。
- 實際執行面核對：FE 36＋PW 3＋BE 20＋BR 10＝69，與 §1 的 AC 分佈（AC-964-7 共 14、AC-964-9 共 8、AC-964-8 共 8 等）逐 AC 吻合。
- 新增 skip／`it.skip`／`@Disabled`：全部親跑結果 0 個略過（vitest 0 pending、gradle 0 skipped、pytest 0 skipped）。

## E 契約／Architecture 對帳

| 項目 | 結論 |
|------|------|
| 契約 §1.1 閘門序（401→403 ACCESS_DENIED→403 si_write_forbidden→503 si_write_disabled→422→序 5′） | 與 `SiConsoleWriteService.setSchedule`（authorize→`SiWriteGates.schedSet`→`scheduleBounds`→`requirePeriodInBounds`→write）一致；`SecurityConfig` 的 `POST /api/v1/si/**` 僅 ADMIN；突變 BE-M11（放行 OPERATOR）與 BE-M12（略過 authorize）皆被 AT-964-7-E-1 抓到 |
| §1.1 GET 405、PUT／PATCH／DELETE（VIEWER 403、其餘 405） | AT-964-7-E-5 通過；`@PostMapping` 不帶 `method` |
| §1.2 輸入閘（`enabled` JSON 布林、`periodMinutes` 整數、`reason`／`note` 規則、全空白對齊 Python strip、未知欄位忽略） | `SiWriteGates.freeText`／`periodMinutes` 與前端 `optionalLineProblem`／`validateScheduleForm` 同表；突變 BE-M5（Double 放行）、BE-M9（全空白放行）被抓。FE 的 `\s` 較 Java／Python 寬（含 U+FEFF）屬「前端較嚴」方向，後端仍為權威（P4 備註，不列缺陷） |
| §1.4 reason 對映（`schedule_bounds_unavailable` 為 `si_unavailable` 的 cause） | 實作與 AT-964-7-E-3 一致；突變 BE-M10（min>max 檢查移除）被抓 |
| §2 Bridge 檢查序、`subject` null、`too_large` 422、判準 6 | `_outer_violations` 以 `must_be_null` rule；超量 422 `too_large`；突變 BR-M1、BR-M2、BR-M3、BR-M7 被抓；兩新路由僅呼叫 `_store_signed_audit` |
| §3 稽核 body 鍵序與黃金檔 G6～G9 位元組 | 共通鍵後接 `enabled`、`period_minutes`、`reason`（或 `note`）；突變 BE-M4（鍵序對調）被 AT-964-7-1、7-3、9-1、9-2 抓；對黃金檔動位元組（BR-M8、BR-M9）被 AT-964-9-3、9-E-1 抓 |
| §4.1 `schedule` camelCase | `SiKeyNamesTest`（9 鍵深層對映）通過；`schema.d.ts` 五值 kind、`enabled` boolean、`periodMinutes` number，`tsc` 通過 |
| §4.2 對帳 `ingested`／`orphans` | `SiReconcileService` 的 `sched.set`→sched-set、`run.open`／`sched.skip`→run-request；突變 BE-M6 被 AT-964-9-4、9-5、9-E-3 抓 |
| V23 Flyway | 實名 `si_console_writes_kind_check`、五值 CHECK、不動欄寬與 trigger；突變 BE-M3（退回三值）被 AT-964-7-6 與 7 個 IT 抓 |
| Architecture §5.6 回寫 vs FE | 三元件（面板、設定對話框、立即啟動對話框）分立，與實作一致；`SiWriteResult` 的 `meta`／`extra` 如 D-CS-24 所述 |
| 非 ADMIN 零控件零 POST／Console 不寫帳本 | `SiView` 以 `isAdmin` 同時閘面板與兩對話框；AT-964-6-1 與突變 FE-M4 證實；`SiReadOnlyArchTest`（AT-964-7-9）鎖唯一存取點 |
| Architecture §12.1 L-SI-1／L-SI-2 | 標註仍為「P4 規劃」（F-4） |
| 金鑰與機密 | 三個 commit 的新增行 0 筆符合金鑰樣式；測試金鑰僅用 TCS §5.1 的 K0 |

## F 突變表（嘗試 33、有效 32；全部還原且 SHA256 核對相同）

### F.1 backend（12；指令：gradle 針對相關 IT 類別；全部紅）

| 編號 | 改法 | 預期紅 | 實際紅 |
|------|------|--------|--------|
| BE-M1 | 界檢查 `> max` 改 `>= max` | 7-4 | AT-964-7-4 |
| BE-M2 | 移除序 5′ 的 `requirePeriodInBounds` | 7-4 | AT-964-7-4 |
| BE-M3 | V23 的 CHECK 退回三值 | 7-6 與五值可寫的各 IT | 7-6 ＋ 7-1、7-2、7-3、7-4、7-5、7-E-2、7-E-3、7-E-4（共 9 紅） |
| BE-M4 | `enabled`／`period_minutes` 鍵序對調 | 7-1、9-1、9-2 | 7-1、7-3、9-1、9-2 |
| BE-M5 | `periodMinutes` 另收 Double | 7-E-2 | AT-964-7-E-2 |
| BE-M6 | 對帳漏掉 `sched.skip` | 9-E-3 | 9-4、9-5、9-E-3 |
| BE-M7 | 補償刪列改為不動作 | 7-E-4 | AT-964-7-E-4 |
| BE-M8 | 結果不明也一律補償刪列 | 7-E-4 | AT-964-7-E-4 |
| BE-M9 | 全空白不再判違規 | 7-E-2 | AT-964-7-E-2 |
| BE-M10 | 移除 min>max 的取界失敗判斷 | 7-E-3 | AT-964-7-E-3 |
| BE-M11 | 安全層放行 OPERATOR 寫入 | 7-E-1 | AT-964-7-E-1 |
| BE-M12 | `requestRun` 略過 `authorize` | 7-E-1 | AT-964-7-E-1 |

### F.2 engine-bridge（9；`pytest -k 964_8`／`964_9`）

| 編號 | 改法 | 預期紅 | 實際 |
|------|------|--------|------|
| BR-M1 | 移除 `must_be_null`（subject 非 null 放行） | 8-E-1 | 紅（2 個 subject 案例） |
| BR-M2 | 移除 kind 比對 | 8-E-1 | 紅（2 個 kind 案例） |
| BR-M3 | sched-set 路由改用 `run-request` kind | 8-1、8-3、8-5 | 紅（8 個） |
| BR-M4 | 落檔改存重新序列化的 JSON（非原樣位元組） | 8-1、8-2 | 紅（7 個） |
| BR-M5 | 移除 Content-Length 提早拒收 | 8-E-2 | **存活**（等價；F-3） |
| BR-M6 | 移除逐塊累計上限（替換字串沒命中，語法錯誤，**無效突變**，改以 M7 補） | — | 無效 |
| BR-M7 | 同時移除宣告長度與逐塊兩道上限 | 8-E-2 | 紅（3 個） |
| BR-M8 | 黃金檔 G6 動 body 一個位元組（mac 不再相符） | 9-3、9-E-1 | 紅（2 個） |
| BR-M9 | 黃金檔 G6 的 body 鍵序對調 | 9-3、9-E-1 | 紅（2 個） |

BR-M6 為無效突變（替換未套用，編譯期語法錯誤），不計入「被抓到」的數字；BR 有效突變 7 個紅＋1 個存活。

### F.3 frontend（11；vitest 相關檔）

| 編號 | 改法 | 預期紅 | 實際紅 |
|------|------|--------|--------|
| FE-M1 | 上界 `>` 改 `>=`（端點放不過） | 2-E-1 | AT-964-2-E-1 |
| FE-M2 | `overdue` 缺席時當成 false（顯示沒有逾期） | 1-E-1、5-2 | 1-E-1、1-E-2、5-2、5-E-1 |
| FE-M3 | `armed` 顯示已武裝 | 1-1、1-2 | 1-1、1-2、1-E-1、1-E-2 |
| FE-M4 | 非 ADMIN 也渲染面板 | 6-1 | AT-964-6-1 |
| FE-M5 | 待入帳 run-request 仍可再送（拿掉停用條件） | 4-2 | AT-964-4-2 |
| FE-M6 | 改死常數 `SCHEDULE_PENDING_TEXT` 為「已生效」 | — | **存活**（死碼；F-1） |
| FE-M6b | 改 `siParts.tsx` 收據字面為「已生效」 | 3-1、4-1 | 3-1、4-1 ＋既有 P2b 三個 AT（933-1-3、935-1-2、935-2-2） |
| FE-M7 | 立即啟動入帳指令漏 `--by console` | 3-2 | 3-2、4-1 |
| FE-M8 | `reason` 空也一律帶鍵 | 3-3 | 2-3、3-3、3-E-3 |
| FE-M9 | 拿掉 `submit()` 內的 `blocked` 守門 | 3-E-2 | **存活**（冗餘防線；F-2） |
| FE-M10 | 天換算除數 1440 改 1400 | 2-1 | 1-1、2-1、3-3 |
| FE-M11 | 界取不到時不再停用送出 | 2-E-2 | 2-2、2-E-1、2-E-2 |

合計：BE 12／12 紅；BR 有效 8 個（7 紅、1 存活）；FE 12 個（10 紅、2 存活：FE-M6 死碼、FE-M9 等價；FE-M6b 為 FE-M6 的補正突變）。有效突變 32 個中 29 個紅、3 個存活（F-1、F-2、F-3，皆 P4）。

## G 誠實劃界（沒跑到什麼、為什麼）

- 未跑 Docker 全棧的 V 系列出口實查（任務書範圍外，由主控與掌舵者做）；Playwright 只跑 mock 模式（路由替身），沒有連真 backend／真 Bridge。
- `schema.d.ts` 沒有重新以 `/v3/api-docs` 重產比對；只確認 `tsc --noEmit` 通過、`OpenApiIT`（35 個）通過，且五值 `kind`／boolean／number 型別就位。
- backend 沒有跑整套 `clean build`；跑了 9 個 P4 相關類別＋回歸 14 個類別（含全部 `*MigrationIT`），其餘測試類別未重跑。
- frontend vitest 只跑與 SI 相關的路徑（517 通過），沒有跑全 repo 的 vitest。
- F-2 的「Enter 鍵不會繞過停用鈕」是依 HTML 規格推論，沒有實際寫 Enter 鍵測試驗證。
- Windows 單平台；macOS／Linux 未驗（NFR-SC-7 的 CI 面不在本審查範圍）。
- 流程摩擦（非缺陷）：frontend 在 worktree 以 junction 連主樹 `node_modules` 時 `next build`（Turbopack）因根目錄解析失敗；改用實體複本（robocopy）後 build 通過。junction 已先以 `[IO.Directory]::Delete` 移除（只斷連結，主樹 `node_modules` 完好）。審查產物（`.next`、`build/`、node_modules 複本）全部在 worktree 內，隨 `git worktree remove` 清除。
