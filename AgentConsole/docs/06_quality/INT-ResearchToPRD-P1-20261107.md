# INT-ResearchToPRD-P1 整合證據（2026-11-07；鍵 `agentconsole-research-to-prd-p1`）

> 來源：INT-P1 整合棒（Sonnet）於 2026-11-07 16:2x～16:5x 的實跑證據（scratchpad `qa/int/INT-P1-20261107.md` 與同目錄日誌），由主控落檔。主控親驗（當回合真跑）：`tests/test_research_int_p1.py` 序列跑 **8 passed、0 skipped（163 s）**；`ruff check` engine-bridge 視角與 monorepo 根視角皆 All checks passed；根層三類平台鎖＋裸 python 登記表 96 tests OK。HEAD＝`2a5e7d5f`（P1 七包＋三補完棒皆已 push，雲端 CI 五支全綠）。
> 出口判準依 PRD §8.1 P1 列 (a)～(k)；載具設計依 IFACE-P1 §9（甲＝本機模式軌道 A、乙＝本機模式軌道 B＋假 gh、丙＝Docker mock-only、丁＝SCR 序列）；整合 AT 依 TCS-P1 §3.4／AC-961-22。

## 1. pytest 整合檔（載具甲／乙／丁的 pytest 形態）
- 檔：`AgentConsole/engine-bridge/tests/test_research_int_p1.py`（新；組合既有夾具 `tests/research_git_support.py`：真 git 只在 `tmp_path` 拋棄式倉、gh 一律假夾具、機密樣式字面執行期拼接）。
- 指令：`$env:BRIDGE_TEST_DSN=<autoclaude_pg>; python -m pytest tests/test_research_int_p1.py -q -p no:xdist -o addopts=`（cwd＝`AgentConsole/engine-bridge`）。
- 結果：八案全過、零 skip（`SDD_ROOT` 自動發現、DSN 在）：AT-961-22-1、22-2、22-2（fail-create 重試案）、22-3、22-4、22-E-1、22-E-2〔clone〕、22-E-2〔archive〕。日誌：scratchpad `qa/int/pytest_int_p1_final.log`、`pytest_int_p1_run4.log`（內含 22-1／22-2／22-3 的內環鍵 `show` 逐字）。
- 22-1（軌道 A）：clone 為真 repo `git clone --no-hardlinks`；預演前後 git snapshot 與路由表列數相等；確認後主工作樹 HEAD／status／index／stash 不變；`git diff --name-only main..feature/issue-N` 僅 `AgentConsole/docs/01_requirements/demo_PRD.md` 與 `AgentConsole/docs/02_architecture/Module_Placement_Stub_demo.md`；內環 Stage-1 的 `spec_doc_digests` 與外環相交；步驟全 OK；游標 `build／ROUTED`；對帳 `consistent=true`；假 gh 呼叫 0；真 repo HEAD／refs／status 前後相同。
- 22-2（軌道 B＋假 gh）：`git ls-files`＝預演 `expected_tracked_files`、無 `raw/**` 與 `.env`、單一 commit；gh 序 `auth status` → `repo create … --private --source . --push`；token 全表／全檔／回應掃描 0 命中；對帳 consistent。fail-create 重試案：本地步驟保留、遠端步驟重試後成功。
- 22-3：未拆解先 tcs-draft＝409（D-110）；`:decompose` → tcs-draft → 內環 SPEC_DRAFTING → SCG_VALIDATION → HUMAN_PENDING（三筆 transition）；`:freeze` 後 Stage-2。
- 22-4：夾具態（以 transition 推到 IMPLEMENTATION，非真實演練）；SCR MINOR 序列 `transition(SPEC_AUDIT)、publish、spec-refreeze、transition(PR_REVIEW)、gate(PR_REVIEW,FAIL)`；與人工等價序列 `decision_trace` 末三筆相等。

## 2. 載具丙（Docker mock-only；V-D1）
- 三映像以 HEAD `2a5e7d5f` 重建、三容器 healthy（容器內現查：Bridge 含 `scr.py`／`decompose_plan.py`／`research_scr.py`、Flyway 18～20 success、frontend BUILD_ID 新）。
- `npx playwright test -c tests/e2e/docker.config.ts tests/e2e/research-p1-docker.stack.spec.ts --output=<暫存>` → rc 0、兩案通過（1.4 分）：AT_961_22_5（capabilities mock-only、兩軌 422 `route_unsupported_in_deployment` 且研究表零寫入、UI 兩卡停用與文案）、AT_961_22_6（超前導回、拆解／SCR 讀端點空值、tcs-draft 409、事件帳零新增）。日誌 `qa/int/pw_carrier_c_p1docker.log`。

## 3. 載具甲／乙（本機模式；Playwright 對主機 Bridge 18081＋Docker 全棧）
- 設定：主機 Bridge（`BRIDGE_REPO_ROOT`＝`%TEMP%\r2p1-int-clone`〔真 repo 的 `git clone --no-hardlinks`，HEAD 與真 repo 相同〕、worktree／scaffold／research 根皆 `%TEMP%\r2p1-int-*`）；PG 經暫存 relay 容器 `r2p1-pgrelay`（`127.0.0.1:55432` → `aisdlc-pg-primary`；db-net 為 internal、主機無法直連）；backend 以 shell 環境變數 `ENGINE_BRIDGE_URL=http://host.docker.internal:18081` 重建（未改 `.env`／compose）；PATH 前置假 gh。主機 Bridge 的 capabilities＝`mode:local`、`gh_cli.ok`、`repo_writable:true`、`scaffold_templates:[python-fastapi]`。
- 結果：`research-route-local.stack.spec.ts`（`E2E_LOCAL_BRIDGE=1`、`E2E_LOCAL_TRACK_A=1`、`E2E_LOCAL_TRACK_B=1`）兩案通過（1.1 分）：AT_961_22_1（軌道 A）、AT_961_22_2（軌道 B）。首跑兩案失敗＝§8 缺陷 D-1（DSN 寫 `localhost` 的 IPv6 逾時），改 `127.0.0.1` 後通過。日誌 `qa/int/pw_carrier_b_route_local.log`（首跑失敗版另存 `…_run1_FAIL_localhost-ipv6.log`）。
- 主機側核對：clone `status --porcelain` 0 行、current branch main、HEAD 不變；worktree `rp-0052-e2e-*`、分支 `feature/e2e-*`；`diff --name-only main..feature/e2e-*`＝`AutoClaude/docs/01_requirements/e2e-local-a-*_PRD.md`、`AutoClaude/docs/02_architecture/Module_Placement_Stub_e2e-local-a-*.md`；DB：route A SUCCEEDED 7 步、route B SUCCEEDED 7 步、`console_project_id` 已綁、`research_projects` 回填；游標 `build／ROUTED`（spec 斷言）。軌道 B 的 spec 未開 `create_github`，假 gh 紀錄檔未建立；gh 路徑由 pytest 22-2 與 fail-create 案覆蓋。
- 假 token：spec 以 `E2E_FAKE_GH_TOKEN` 掃回應與 DB（通過）；pytest 22-2 對全表／全檔掃描 0 命中。

## 4. 載具丁／SCR 序列
- `pytest tests/test_research_scr_fsm.py tests/test_research_int_p1.py -k "13_1 or 13_2 or 13_3 or 22_2"` → 十案通過（`qa/int/pytest_scr_matrix_and_22_2.log`）：內環現態矩陣六列（IMPLEMENTATION／EXECUTION_EVALUATION／PR_REVIEW／SPEC_AUDIT／RTM_VERIFY／RELEASE_READY）各實跑真 FSM CLI；13-1 的 `decision_trace` 與人工等價序列 diff 為空；13-3 BLOCKED 不重試。MAJOR（後繼專案）與 HEALING_FAILED（只產指令）由 BR-D2／D3 既有 AT 覆蓋，INT 未另跑。

## 5. AT-961-22-7／22-8
- 22-8：`research-docker.stack.spec.ts` → 四案通過、一案 skipped（7.2 分）；skipped＝AT_960_22_2（路徑 A 三輪審查未通過，spec 內本來標 skip，非 P1 造成）。日誌 `qa/int/pw_22_8_p0_docker.log`。
- 22-7：`a11y.mock.spec.ts` 在 `next dev` 下八案中 P1 兩案（步驟 3 分流抽屜、步驟 4 前半）通過；P0 既有四案（登入頁／新建專案對話框／專案詳情／研究清單）在 dev 模式冷編譯下逾時（Test timeout 120000ms、Execution context destroyed），非 P1 斷言。主控另以 production 建置（`E2E_MODE=standalone`）重跑全套，結果見本檔附記。日誌 `qa/int/pw_22_7_a11y_mock.log`。

## 6. V 項
- V-D1：載具丙兩案通過（§2）。
- V-D3：真 repo 另 clone 後 `git worktree add`：`core.longpaths=true` 8.34 s、`false` 8.56 s，皆 rc 0；30055 個追蹤檔、472.5 MB、最長檔案路徑 193～194 字元；Bridge 實際 worktree（`%TEMP%\r2p1-int-wt\rp-0052-e2e-*`）最長 209 字元；本機 `LongPathsEnabled=0`，路徑皆小於 260 所以兩種設定都成功——長路徑風險在更深的使用者名／根路徑才會現形（未壓測）。
- V-D4：拆解以 FakeBrain 夾具、耗時可忽略；真引擎（MINIMAX）未跑（hermetic 禁外呼、本場無 `MINIMAX_API_KEY`）→ 未驗。
- V-D2：Bridge 層 pytest 22-3 串接 `:decompose` → tcs-draft → `:freeze`（含未拆解 409）；Docker 全棧上由 backend 驅動 `:decompose`／簽核／stale 未實跑（需真 Brain）→ 部分。
- V-R8：INT 不連 GitHub。附帶事實：`GH_TOKEN` 設為無效值時本機真 `gh auth status` rc=1（`GH_TOKEN` 覆蓋已存登入）；以 token 過 `repo create` 的唯讀探測未驗，留給 V-H3。
- V-H3：掌舵者真機（Private 庫）不在 INT 範圍。V-C1：由 SCG-4 報告承擔。

## 7. 出口判準 (a)～(k)
(a) pytest 22-1／22-2＋Playwright 22-1／22-2：通過（真 Private 庫由 V-H3）；(b) 預演零副作用：22-1 前後 snapshot／表列數相等，通過；(c) 主工作樹零擾動：22-1 HEAD／status／index／stash 不變、真 repo 唯讀，通過；(d) Stage-1 `show` 逐字與 Stage-2：通過；(e) 拆解覆蓋與簽核：Bridge pytest 層通過、全棧／真 Brain 未驗；(f) token 零外洩：22-2＋fail-create 通過；(g) SCR MINOR 序列：矩陣六列＋人工等價 diff 空，通過；(h) 分流時點對帳：22-1／22-2 皆 `consistent=true`，通過；(i) 未簽核草稿啟動 409：沿用 BR-D2／D3 與 API-P1 既有 AT（INT 未另跑全棧），部分；(j) V-R8：部分（見 §6）；(k) capabilities 缺 gh／scaffold 時 UI 停用：22-5 通過。

## 8. 缺陷表（未發現 P1／P2 產品缺陷）
| 編號 | 級 | 座標 | 描述 | 重現／處置 |
|------|----|------|------|-----------|
| D-1 | P3（載具／文件） | 主機 Bridge＋Docker PG relay | DSN 寫 `localhost` 時 Windows 上 psycopg 每次連線等滿 connect_timeout（先試 IPv6 `::1`，Docker 只發布 `127.0.0.1`）→ Bridge 啟動 `schema_ready` 逾時、stage 啟動阻塞、backend 回 504 `bridge_timeout`、併發上限再回 409 `stage_conflict`；改 `127.0.0.1` 即消失 | 實測 `localhost` 15 s、`127.0.0.1` 0.03 s；`tests/e2e/README.md` P1 真棧節已補一句（同 commit）；IFACE §9.2 為 scratchpad 設計稿，不另改 |
| D-2 | P3（測試載具） | `test_research_int_p1.py::make_source` | Windows bsdtar 解不了 `git archive` 含非 ASCII 檔名的 tar（`AISDLC_SDD/…/sample/*.md`） | 已改 Python `tarfile` |
| D-3 | P3（測試載具） | Windows `subprocess` | `subprocess.run(["gh", …])` 不解析 `gh.cmd`（CreateProcess 只補 `.exe`）而落到真 `gh.exe` | 須以 `shutil.which` 結果當 argv[0]（`gitops._spawn` 本來就如此；測試載具照辦） |
| D-4 | P4 | `a11y.mock.spec.ts`（`next dev`） | P0 既有四案在 dev server 冷編譯下逾時 | 以 standalone 重跑（附記） |
| D-5 | P4 | AT_960_22_2 | 在 `research-docker.stack.spec.ts` 內為 skipped（P0 既有） | 不在 P1 範圍 |

## 9. 殘留與還原
clone／worktree／scaffold／research 根／fakebin／fake gh log 已刪（`%TEMP%` 無 `r2p1*`）；`r2p1-pgrelay` 容器已 `rm -f`；主機 Bridge 行程已結束、18081 無監聽；pytest 拋棄式庫由 teardown 自 drop（`autoclaude_pg` 查無殘留）；`aisdlc-backend` 已以不帶覆寫環境變數重建（`ENGINE_BRIDGE_URL` 回容器內 Bridge、healthy）；`aisdlc-engine-bridge` 與 `aisdlc-frontend` 全程未動；compose 與 `.env` 零改動；repo 工作樹只新增整合測試檔。

## 附記（主控，2026-11-07 17:0x）
- AT-961-22-7 全套以 production 建置重跑（`E2E_MODE=standalone`、`E2E_WEB_PORT=3208`、`--output=<暫存>`）：`a11y.mock.spec.ts` **八案全過（19.9 秒）**，含 P0 既有四案與 P1 兩案（步驟 3 分流抽屜、步驟 4 前半）⇒ §5 的 dev 模式逾時（D-4）確認為載具現象、非產品缺陷。
