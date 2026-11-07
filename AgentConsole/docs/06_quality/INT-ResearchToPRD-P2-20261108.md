# INT-ResearchToPRD-P2 整合證據（2026-11-08；鍵 `agentconsole-research-to-prd-p2`）

> 來源：INT-P2 整合棒（Sonnet）於 2026-11-08 05:3x～06:1x 的實跑證據，原始日誌在 scratchpad `r2p2/dev/PKG-INT-P2/`（檔名見各節）。受測 HEAD＝`ea978443`；三映像於該 HEAD 重建（frontend `25d840379d51`、backend `bbc93d311e99`、engine-bridge `ea224dc7be76`），全部容器 healthy。
> **誠實總結先講**：十一個 AT 中，pytest 五案與 Playwright 兩案（28-7、28-8）已實跑通過；**28-3、28-4、28-5 三案未能實跑**——它們需要「本機模式」載具，而載具要重建共用的 `aisdlc-backend` 容器（`ENGINE_BRIDGE_URL` 指向主機 Bridge），該動作被 harness 的 auto mode 分類器拒絕（理由：Modify Shared Resources），本棒未繞過。28-E-2 清理核對已做。V-D5 與 SSE 真棧量測同因未量。
> 另有一項**規格與真棧不符**：AT-962-28-8 字面要求容器模式的 delivery/tag 回 422，真棧實際回 409（見 §2、§8 D-1）。
> 出口判準依 PRD §8.1 P2 列 (a)～(i)；整合 AT 依 TCS-P2 AC-962-28。載具劃界一律分「引擎真」與「構造」兩欄標示。

## 1. pytest 整合檔（載具甲：TestClient＋真 FSM CLI＋拋棄式庫＋`file://` bare origin＋假 gh）
- 檔：`AgentConsole/engine-bridge/tests/test_research_int_p2.py`（新）；沿用 `test_research_delivery`、`test_research_healing`、`test_research_inner_gates` 的夾具助手。
- 指令（cwd＝`AgentConsole/engine-bridge`，DSN 用 `127.0.0.1`）：`python -m pytest tests/test_research_int_p2.py -q -p no:xdist -o addopts= -s -rs`；結果：五案全過、零略過（最終一次 140 秒，日誌 `pytest_final.log`；早先兩次 41 秒，日誌 `pytest_run2.log`）。
- **28-1（出口 a）**
  - 構造：起點是「內環鍵以 transition 推到 IMPLEMENTATION」的夾具態；RTM 報告檔、`tasks` 列、拆解 SIGNED_OFF 列皆夾具構造；`gh` 假夾具。
  - 引擎真：`:gates` PR_REVIEW 回 `IMPLEMENTATION → RTM_VERIFY`；`:gates` RTM_VERIFY 回 `RTM_VERIFY → RELEASE_READY`；`:tag`（push true）後 `show` 輸出 `current_state=RELEASE`；git 呼叫序含 `tag --list`、`tag -a`、`ls-remote --tags origin`、`push origin v1.2.3`；`file://` bare origin 的 tag 清單恰為該 tag。
  - 人工等價序列逐動詞 rc 皆 0：`transition → PR_REVIEW`、`gate PR_REVIEW PASS`（`next_state` 為 RTM_VERIFY）、`gate RTM_VERIFY PASS`（`next_state` 為 RELEASE_READY）、`transition → RELEASE`。兩鍵的 `decision_trace`（from、to、trigger）全序列相等，diff 為空。
  - M2 對帳：七項皆 ok（含 `prd_sha256`、`delivery`），`consistent=true`。M3：官方指標是 console-api 的 `records/audit` 的 `missing[]`，Bridge 層拋棄式庫無此端點，僅記錄各紀錄表列數；**M3 官方值本輪未取**（需本機模式的真棧，見 §3）。
- **28-2**：`:pr` 回 `https://github.com/octocat/demo-app/pull/7`（假 gh；`created=true`）；`research_deliveries` 有 `PULL_REQUEST` 列（快照欄為空）；`research.delivery` 事件六鍵齊全；假 gh 呼叫序 `auth status`、`pr list`、`pr create`，token 只在環境（`has_gh_token=true`）。token 掃描：DB 全表文字欄二百九十八格命中 0，argv、假 gh 紀錄、回應、日誌命中 0。`fail-pr` 一案：502 `delivery_step_failed`（`failure_step=pr_create`）、不寫 `FAILED` 列、只發事件（D-138 Q-10）。
- **28-6（出口 g）**：`:tag` 後對帳事件 `consistent=true`、`driftCount=0`；手改快照檔一個位元組（長度不變）後 `:reconcile` 的 `delivery` 項為 `drift`（`expectedSha256`、`actualSha256` 皆為實算值），檔位元組與 DB 列都不被修復；還原後再對帳回 `ok`。
- **28-E-1（SPEC_CHANGE 取證）**：手改已凍結 PRD 後 `:healing-sync`：偵測到該路徑、`research.alert{kind:SPEC_CHANGE_FORBIDDEN}` 一筆、`healing_history.log` 的 `spec_change` 行一筆；Bridge 不還原（檔 sha 等於手改後）；同漂移再 sync 不重複告警；同夾具打 `:gates`、`:tag` 皆 422 `digest_mismatch`（`details.drift[]` 三鍵）、FSM 寫入動詞 0、閘決定與交付列數不變；回應與事件文字不含 reject、block、denied（不聲稱「被拒」，屬 V-S1）。
- **28-E-3（hermetic）**：掃描判準＝AST 非 docstring 字串常數含 `https://github.com`、`api.github.com`、`github.com`，範圍＝P2 產品碼五檔加 P2 四個 Bridge 測試檔；命中兩處皆在登記的允許清單（gitops 的拒絕訊息文字、假 gh PR 清單夾具字串）；執行期以 socket 層替身攔截非 loopback 連線與 github 名稱解析，跑 `:pr`、`:tag`、`:healing-sync` 共十九筆 git／gh 呼叫，攔截為 0。
- 突變抽查（INT 的鑑別力；日誌 `mut_*.log`、`mutations.log`）：①28-1 人工序列少最後動詞→紅；②28-6 不改快照位元組→紅；③28-E-1 sync 後把檔還原→紅；④28-2 掃描詞表混入 token→紅；⑤28-2 把假 gh 切到 `leak`→**存活（預期）**：產品碼在輸出面遮蔽 gh 的洩漏（AT-962-20-6 同一防線），掃描器沒有被繞過，這不是測試鑑別力缺口。其餘兩項（28-8 缺項比對、28-E-3 放真網址）未做突變（28-8 在 Playwright 層；E-3 掃描器用正負對照已見命中登記）。

## 2. 載具丙：Docker mock-only（28-7、28-8；日誌 `pw_docker3.log`、`pw_docker1.log`、`pw_docker2.log`）
- 指令：`npx playwright test -c tests/e2e/docker.config.ts tests/e2e/research-deliver.stack.spec.ts --output=<各自目錄>`（`E2E_STACK=1`、ADMIN 帳密只放環境）；結果：兩案全過（最終一次 1.7 分）。
- 真棧現查：`GET /research/capabilities` 為 `mode:mock-only`、`repoWritable:false`、`ghCli.ok:false`、`scaffoldRoot:null`；Flyway 最高 22 且 success。
- **28-7**：新建研究專案走到 Gate 0 並核准後：`GET kanban` 回 200（`consoleProjectId:null`、各欄 NONE、`bridgeReachable:true`）、`GET healing` 回 200（`rows:[]`、`logLag:0`、`specChange:null`）、`GET delivery` 回 200（`containerMode:true`、`releaseReady:false`）、`GET delivery/traceability` 回 200（一個 AC 一列）；UI 開 `?step=build`、`?step=deliver` 皆導回 `step=route`；研究表（交付、閘決定、事件、游標）前後逐位相等；容器內 `/repo` 寫入探測為 READ_ONLY，可寫掛載只有 `/workspace`、`/app/logs`、`/si-audit`。誠實劃界：mock-only 下游標到不了步驟 4，所以**看板、自癒、終端、追溯表的 UI 面板無法在 Docker 內開啟**，只驗到 API 唯讀面與超前導回；面板本體由 mock 層（§5）與本機模式（未跑）承擔。
- **28-8（規格與真棧不符，見 §8 D-1）**：真棧回應逐字：
  - `POST delivery/tag` → 409 `fsm_state_conflict`，`details.unmet=["no_console_project"]`（console-api 的前置，Bridge 前就擋）；
  - `POST delivery/pr` → 409 `fsm_state_conflict`，`details.cause=route_not_succeeded`（Bridge 透傳）；
  - `POST gates` → 409，`details.unmet=["no_console_project"]`；
  - 容器內直呼 Bridge `:tag` → 409 `route_not_succeeded`。
  - 研究交付列、閘決定列、事件數與游標（`docker exec psql` 逐位）前後相等。TCS 字面的 422 `route_unsupported_in_deployment` 在真容器中**不可達**：容器模式的研究專案分流不可能成功，前置先於部署檢查觸發；該 422 只在「分流成功後部署才變唯讀」出現，Bridge 層已有 AT-962-18-E-6 以模擬覆蓋。

## 3. 載具甲／乙：本機模式（28-3、28-4、28-5）——**未實跑**
- 已備好並驗證的部分：拋棄式 clone、PG relay（nginx stream 轉發，bridge 網路發佈加接 db-net）、主機 Bridge 於 18081（含 `BRIDGE_REPO_ROOT` 等根、假 gh 前置 PATH、pass 劇本、`MOCK_CLAUDE_FAIL_REGEX`）。主機 Bridge `capabilities` 讀回 `mode:local`、`repo_writable:true`、`scaffold_templates:["python-fastapi"]`、`db:true`（`local_caps.json`）。啟動腳本 `local_up.ps1` 可重現。
- 阻擋點：把 backend 以 `ENGINE_BRIDGE_URL=http://host.docker.internal:18081` 重建，被分類器拒絕；backend 容器全程未動（healthy、Up 時間連續）。主控授權後只差這一步，之後 28-4、28-5 的 spec 與 28-3 的 HTTP 客戶端測試才能寫成並跑。
- 另一個結構性疑慮（未驗證，列為風險）：`ResearchExecutionGuard` 要求內環鍵已有 Stage-2 凍結才准啟動 run；Stage-2 需拆解與 TCS 草擬，真拆解要 Brain（`MINIMAX_API_KEY`）。28-3、28-4 要走到「引擎真重試耗盡 → ESCALATED」，載具必須先把內環鍵構造到 Stage-2（框架 CLI 動詞，標「構造」）或提供拆解夾具。
- 補充的部分證據（Bridge 層，**不是全棧、不認領 28-3**）：對主機 Bridge 直接 `POST /autoclaude/runs` 起一個必失敗的單步 run（mock claude、`MOCK_CLAUDE_FAIL_REGEX` 命中、`max_retries_per_step=1`）：事件序 `STARTED → RETRYING → FAILED`，run 終態 FAILED，原因含 ESCALATION 字樣（日誌 `bridge_run_probe.out.log`）。這確認 V-D6：**現有機制足夠，不需 `inner_fail.json`**。沒有 console-api，所以沒有 `review_requests` 與視圖列，28-3 的視圖計數至少一列、review request 自然產生兩項**未驗**。

## 4. SCG 登錄與 FSM 序列
- `:gates` 現態矩陣各列的 `next_state` 逐字由 Bridge 既有 AT（BR-P2）覆蓋；INT 補的是整串：PR_REVIEW PASS（IMPLEMENTATION → RTM_VERIFY）、RTM_VERIFY PASS（RTM_VERIFY → RELEASE_READY）、`:tag`（RELEASE_READY → RELEASE），與人工等價序列 diff 為空（§1）。連 FAIL 進 ESCALATION 的 `next_state` 逐字本輪未另跑（沿 BR-P2 既有 AT）。

## 5. mock 層在 production 建置重跑（不認領 AT；日誌 `pw_mock_prod.log`）
- 先 `npm run build`（rc 0，`npm_build.log`），再 `E2E_MODE=standalone`、`E2E_WEB_PORT` 專用埠、`--output=<各自目錄>`：`research-kanban.mock.spec.ts`、`research-deliver.mock.spec.ts`、`a11y.mock.spec.ts` 共十四案全過、零略過（約 27 秒），含 AT_962_11_9 三案、AT_962_21_8 兩案、AT_962_11_E_4。
- 28-4 的「mock 一次」由上列看板與 a11y 的決策彈窗情境承擔；「真棧一次」未跑（§3）。

## 6. V 項
- V-S1／V-D8（同一次取證）：**真 AutoClaude 對凍結檔下手（V-S1）未驗**（hermetic 禁真 claude；需掌舵者或另案）。V-D8 以原始碼加執行期探針回答：`engine-bridge/app/runner.py`（約 64 行、230～233 行）把 `BRIDGE_SDD_WRITE_TOKEN`、`SDD_STATE_DIR`、`SDD_PROJECT` 自子行程環境剝除，只對含 `sdd` 區塊的 run 注入 `SDD_PROJECT`，**不注入 `SDD_STATE_DIR`、整個樹也沒有 `SDD_ACTIVE_VERSION` 的注入點**；探針 run（無 sdd 區塊）的 mock claude 回報 `SDD_PROJECT`、`SDD_STATE_DIR` 皆為 null。推論：三件組不完整，框架 hooks 在 run 子行程內不會生效，**P2 不得聲稱「被拒」**（與 TCS 預設一致）。
- V-D5（FSM 檔改變到看板更新的真棧上界）與 SSE 真棧量測：**未量**（需本機模式的步驟 4 看板，§3）；不寫任何達標字樣。
- V-D6：現查結論見 §3（機制足夠）。
- V-D7：原始碼判讀（`hooks/useRunStream.ts` 約 120～129 行）：斷線回補以 `steps?afterSeq` 取 `execution_steps` 並經 `stepToLogData` 轉成 log 形事件，內容是步驟級（開始、完成、失敗、錯誤訊息），不是 claude 輸出的逐行 log；`LiveLogCard` 每行以純文字渲染（`whitespace-pre-wrap`）。故 AT-962-13-4 的「與結束前一致」以夾具態成立，真棧逐行完整性**未驗**。
- V-H5、V-H6、掌舵者目視項、macOS／Linux：待掌舵者或未驗；構造情境不充當。

## 7. 出口判準 (a)～(i)
(a) 內環走完到交付：28-1、28-2 通過（引擎真與構造已分欄，真人真機整串屬 V-H5，待掌舵者）；(b) 至少一次 ESCALATED 或待審彈窗：**未達**（28-3、28-4 未跑；Bridge 層重試耗盡探針為部分佐證）；(c) 一次 SCR 演練：**未達**（28-5 未跑）；(d)(e)(h) 由各包既有 AT 承擔，INT 於 mock 層重跑確認（§5）；(f) 視圖對真失敗步驟有列：**未驗**；(g) 交付時點對帳 ok：28-6 通過；(i) 掌舵者真機五步：待掌舵者。

## 8. 缺陷與偏差
| 編號 | 級 | 座標 | 描述 | 重現／處置 |
|------|----|------|------|-----------|
| D-1 | P3（規格與真棧不符） | TCS AT-962-28-8；console-api 交付前置與 Bridge 檢查序 | 容器模式的 delivery/tag 在真棧回 409，不是 TCS 寫的 422 `route_unsupported_in_deployment`；該 422 在真容器不可達 | 新建研究專案走到 Gate 0 核准後 `POST /api/v1/research/projects/{id}/delivery/tag`；建議勘誤 28-8 的 Then 為 409 與零變化，或把負控改掛 Bridge pytest（AT-962-18-E-6） |
| D-2 | P3（載具阻擋） | 本機模式載具 | 重建 backend 以指向主機 Bridge 被 auto mode 分類器拒絕，28-3、28-4、28-5、V-D5 無法實跑 | 由主控授權或代為執行該重建後續跑；kit 與腳本已備 |
| D-3 | P4 | `app.routers.research_deliver` 匯入順序 | 單獨 `import app.routers.research_deliver`（未先匯入 `app.main`）會因與 `routers/research.py` 的循環匯入而 AttributeError；經 `app.main` 啟動不受影響 | 容器內 `python -c 'import app.routers.research_deliver'` |
| D-4 | P4（外觀） | `delivery/traceability` 的 `gherkinSummary.then` | 夾具 PRD 的 AC 內文帶三個反引號圍欄，摘要尾端殘留 ` ``` ` 字樣 | 對 Gate 0 核准的專案 `GET …/delivery/traceability` 看 `AC-001-1` 的 `then` |
| D-5 | P4（說明） | TCS 28-7 字面（看板、自癒、終端、追溯表「可驗」） | Docker mock-only 下游標到不了步驟 4，面板無法開啟；只能驗 API 唯讀面與導回 | 同 §2 |

## 9. 殘留與還原
- 已清除：主機 Bridge 行程（18081 無監聽）、`r2p2-pgrelay` 容器（55432 無監聽）、`%TEMP%\r2p2-int`（clone、worktree 根、假 gh 目錄、研究根、日誌；`git worktree` 無殘留）；pytest 拋棄式庫由 teardown 自 drop（`autoclaude_pg` 只剩 `autoclaude`）。
- 未動：`aisdlc-backend`、`aisdlc-engine-bridge`、`aisdlc-frontend`、`aisdlc-pg-primary` 全程未重建、未重啟（healthy）；compose 與 `.env` 零改動；系統參數零改動（`settings_before.json` 為基準備份）。
- 資料庫真庫：僅經 API 建立的測試研究專案（各自走到 Gate 0 核准），afterAll 已封存；Flyway 與各表列數除這些專案外無變動。
- 工作樹只新增兩個測試檔與本證據檔；產品碼零差異。

## 10. V21／V22 真棧升級實證
- 比對基準：主控重建前快照（`pre_rebuild_snapshot_20261108_0236.txt`，Flyway 最高 20）對重建後 `console.flyway_schema_history`（日誌 `post_flyway.txt`、`post_counts.txt`）。
- 版本 1 至 20 的版本、描述、checksum、success 逐列比對差異為 0；新增 21（`research gate details delivery snapshot`）與 22（`research flow phase delivered`），皆 success，安裝時間同為 2026-11-07 21:26Z（即 05:26 重建）。
- 十八張 `research_*` 表列數與重建前逐表相同（比對差異為 0）。
- 約束現查：gate CHECK 含 `SCG6`；`ck_research_gate_details_object`、`ck_research_scr_evidence_url`、`ck_research_deliveries_snapshot_sha256` 各一條具名 CHECK；`research_projects_flow_phase_check` 恰一條且含 `DELIVERED`（十四個值）；無互相矛盾的 gate CHECK。
- 未對真庫做任何 DDL 或手寫 INSERT。
