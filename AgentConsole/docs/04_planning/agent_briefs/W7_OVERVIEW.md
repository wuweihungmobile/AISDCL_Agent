# W7 收斂波總覽（主控 2026-10-16；所有 W7 棒次必讀，與口頭指示衝突時以本檔為準）

> 位置：`AgentConsole/docs/04_planning/agent_briefs/`。本檔是 W7 六棒（SA 契約 v1.3、ARCH 獨立審查、BE、FE、INFRA、QA）共同的全貌；各棒只做自己持有面內的事，但要知道別棒在做什麼、介面在哪裡定。本波只有這一份任務書，不另拆檔。

## 1. 背景與目標

- 現況（HEAD `ac9272da`）：RTM 364 列＝`✅ 已驗證` 359、`🟡 部分` 5、其餘 0。W5 十筆缺陷與 W6 的 DEF-AC-011 已全部在真後端／真瀏覽器／Docker 全棧結案。
- 剩下的 5 列 🟡 都是「主控裁決維持」而不是功能缺口。掌舵者授權主控依最理想方案裁決，裁決如下（編號接 Implementation_Plan §5.3）：

| 裁決 | RTM 列 | 裁決內容 | 誰做 |
|------|--------|----------|------|
| D-11 | `API-AUT-06` 等級 6～10 傳遞引擎 | **真的送引擎**：Console 依等級把 AutoClaude 既有的設定鍵（候選 `minimax.enable_kernel_brain`、`playbook.max_evolutions`、`playbook.require_evolution_signoff`）物化進 `config_overrides`，並在批次回應誠實標示引擎能力狀態（`engineCapabilities`）。零侵入：**不改 AutoClaude 一行**，只用它已有的鍵。 | SA 查證並定契約 → BE 實作 → QA 驗到磁碟上的引擎 config |
| D-12 | `US-M-10` 資源使用情況 | **補上資料來源**：Bridge 以 psutil 對引擎行程樹取樣（CPU％、RSS、行程數、取樣時間），`GET /runs/{id}` 回 `resources`；後端投影到 `GET /executions/{id}` 的 `bridge.resources`；前端 Agent 即時狀態卡顯示，拿掉「目前沒有提供這項資料」的說明句。 | SA 定契約 → INFRA（Bridge）∥ BE ∥ FE → QA |
| D-13 | `NFR-9.1-05` 20KB 預覽 131ms | **追到 < 100ms**：依 QA 的量法（`p9-w5-ui-evidence.spec.ts::NFR-9.1-05`，7 次取中位數）為唯一尺。做不到就誠實回報數字與試過的方法，列維持 🟡。 | FE → QA 重量 |
| D-14 | `NFR-9.3-01` 可用性 99.5% | **把量測機制做成可驗證的**：Prometheus recording rule（30 天／7 天／1 天可用率）＋ 低於 99.5% 的告警規則 ＋ `promtool test rules` 單元測試 ＋ Grafana SLO 面板。30 天實際值是營運觀測值，不是本輪能證的；RTM 列升級的口徑＝「量測機制已驗證，實際值由 Grafana 持續顯示」（QA 在 E2E 欄寫明）。 | INFRA → QA 在全棧驗 |
| D-15 | `INF-VOL-07` nginx_certs／HTTPS | **QA 親跑** `docker/README.md`〈14〉自簽憑證流程（卷內憑證、`nginx -t`、經 HTTPS 打到真實上游、80→443 轉址且 `/nginx-health` 仍 200）。真憑證申請與續期屬營運，不在 repo 範圍（README 已寫明）。 | INFRA 先自跑一次並把步驟修到可照抄 → QA 獨立重跑 |

- 另外：掌舵者要求「確認 PRD 全部功能都已完備、UI 依設計稿、三模組緊密結合」。這由 **ARCH 獨立審查鏡**（唯讀）從 PRD 重新推導需求清單、對照 RTM 與程式碼找缺口；找到的缺口由 QA 登記缺陷，本波能修的小缺口由主控補派。

## 2. 棒次、持有面與順序

| 棒 | 模型 | 持有面（只准寫這些路徑） | 順序 |
|----|------|------------------------|------|
| W7-SA | Sonnet | `docs/02_architecture/API_Contract_P3-6.md`、`docs/02_architecture/openapi-p3-6.yaml`、`docs/02_architecture/Architecture.md`、`docs/02_architecture/ADR-001-TechStack-Lock.md` | 第一波（契約 v1.3 定稿後 BE 才開工、FE／INFRA 才做契約相關項） |
| W7-ARCH | Sonnet | **唯讀**；只寫 `docs/06_quality/Completeness_Audit_W7.md` | 第一波，與 SA 並行 |
| W7-FE | Sonnet | `frontend/**`（含 `tests/e2e/*.mock.spec.ts` 與單元測試；**不改** p3～p9 等真後端 spec）、`docs/06_quality/rtm_backfill_W7FE.md` | 第一波先做 D-13；契約定稿後主控以訊息追加 D-12／D-11 的前端項 |
| W7-INFRA | Sonnet | `engine-bridge/**`、`docker/**`、`docker-compose.yml`、`docker-compose.dev.yml`、`.env.example`、`docs/06_quality/rtm_backfill_W7INFRA.md` | 第一波先做 D-14／D-15；契約定稿後主控以訊息追加 D-12 的 Bridge 項 |
| W7-BE | Sonnet | `backend/**`、`docs/06_quality/rtm_backfill_W7BE.md` | 第二波（SA 交卷、主控裁決後） |
| W7-QA | Sonnet | `frontend/tests/e2e/**`（真後端 spec）、`docs/06_quality/**`（RTM.md 單線合併、`QA_W7_Closure.md`） | 第三波（三棒皆由主控親驗並 commit 後） |

並行鐵律（根層 CLAUDE.md 鐵律七）：不寫他棒路徑；不改 `RTM.md`（走各自的 `rtm_backfill_*.md`）；不 commit／push；不派子 agent；不自架背景等待後交卷；暫存檔一律放 session 暫存目錄。同一棵工作樹有人同時在改別的目錄是正常的，`git status` 看到他棒的檔不要碰、也不要「順手還原」。**不准動** `AutoClaude/`、`AISDLC_SDD/`、根層 `CLAUDE.md`、`.claude/`、`tools/`、`.github/`。

## 3. 各棒規格

### 3.1 W7-SA：契約 v1.3（D-11、D-12）

先讀：`API_Contract_P3-6.md` §3.4.2（物化）、§3.6.1（pause 決策表，等級 6～10 列）、§1.2（執行 API）、§4.3 M-19、附錄 C（設定鍵目錄）、附錄 E、§6.5（v1.2 變更一覽的寫法）；`backend/.../ConfigMaterializer.java`；`engine-bridge/app/security.py`（`_OVERRIDE_SECTIONS` 已含 `minimax`／`playbook`）、`engine-bridge/app/runner.py`（`materialize_config` 寫 `paths.config`）、`engine-bridge/app/models.py`（`RunStateOut`）。

**A. 引擎旋鈕查證（D-11）**——讀 `AutoClaude/autoclaude/utils/config.py`（`MinimaxConfig.enable_kernel_brain`、`PlaybookConfig.max_evolutions`／`require_evolution_signoff`／`enable_rtm_feedback`／`goal_synthesis_enabled`）、`plugins/evolution_plugin.py`、`evolution/playbook_evolver.py`、`core/kernel.py`（`decide_correction`）、`core/wiring.py`，逐題回答並附 `檔案:行號` 證據：
1. `minimax.enable_kernel_brain=true` 開了什麼（prompt 改寫＋step mutation）？沒有 `MINIMAX_API_KEY` 時是被忽略還是出錯？
2. `playbook.require_evolution_signoff=true` 而沒有注入 approver 時，fail-closed 的實際結果是「拒絕這次演化、批次繼續或升級」還是「整個批次停機」？
3. `max_evolutions` 的語意（每批次上限？每步驟？）；`enable_rtm_feedback`／`goal_synthesis_enabled`／`enable_translation_auto_propose` 各是什麼、送了會不會改變現有 E2E 行為。
4. Bridge 端：這些鍵能否通過 `validate_config_overrides`、會落在引擎 config 檔的哪個路徑（`paths.config` 的實際檔名與位置，QA 要在磁碟上斷言）。

**B. 物化對映（主控預設方案；查證結果牴觸時改掉並說明）**：
- `effAutoMutation = agent.enableAutoMutation || level ≥ 6`；`effSelfEvolution = agent.enableSelfEvolution || level ≥ 7`。
- 有 `model.apiKey` 時：`effAutoMutation` → `minimax.enable_kernel_brain=true`（覆蓋 `model.enableKernelBrain=false`；兩者皆 false 時沿用設定值）；`effSelfEvolution` → `playbook.max_evolutions`＝等級對映 `{≤7:3, 8:5, 9:8, 10:10}`；`!effSelfEvolution` → `playbook.require_evolution_signoff=true` **只在** 問題 2 的答案是「拒絕演化、批次不停機」時才送，否則不送並在附錄 C 的 impactNote 寫明「引擎內建演化在有 Brain 金鑰時一律啟用」。
- 沒有 `model.apiKey` 時：這些鍵一律不送（引擎沒有 Brain，送了也沒用）。
- 批次回應新增 `engineCapabilities: { autoMutation, selfEvolution }`，值域 `ENABLED`（已送引擎）／`OFF`（有效旗標為 false）／`UNAVAILABLE_NO_API_KEY`（有效旗標為 true 但無金鑰）；在 spawn 時決定並落庫（`execution_runs` 加 jsonb 欄，Flyway 新版本號接現有最大號＋1；`ddl-auto=validate` 要同步 entity），`GET /executions/{id}` 與 `POST execute` 的 201 回應都帶。
- 附錄 C：`agent.enableAutoMutation`／`agent.enableSelfEvolution` 的 `effect` 由 `U` 改 `E`，impactNote 寫清楚「需 `model.apiKey`；等級 ≥6／≥7 會強制開啟」；§3.6.1 等級 6～10 列改寫（Console 審核閘行為仍同等級 5，差異在引擎能力旗標）；附錄 E `API-AUT-06` 改為可驗證情境。
- 寫成 E2E 情境（QA 最低驗證矩陣）：專案等級 7、設定假金鑰（不得以 `sk-` 開頭）與 `model.apiUrl` 指向 allowlist 內的假伺服器 → `POST execute` 201 的 `engineCapabilities` 兩者 `ENABLED`；磁碟上的引擎 config 檔含 `enable_kernel_brain: true` 與 `max_evolutions: 3`；清掉金鑰後同專案再執行 → `UNAVAILABLE_NO_API_KEY`；等級 3 且設定皆 false → `OFF`。

**C. 資源使用（D-12）**：
- Bridge `RunStateOut` 新增 `resources: ResourcesOut | null`：`cpu_percent`（0～100，整機正規化＝行程樹各行程 `cpu_percent` 總和 ÷ 邏輯核心數，取一位小數）、`rss_bytes`（行程樹 RSS 總和）、`process_count`、`sampled_at`（ISO-8601 含 offset）。引擎行程不存活（未啟動、終態）時為 `null`。取樣由 Bridge 背景每 5 秒對存活的批次做一次（psutil，`cpu_percent(interval=None)` 第一筆可為 0.0），請求路徑不阻塞、只回最近一筆。
- 後端 `ExecutionRunResponse.bridge` 新增 `resources: { cpuPercent, memoryBytes, processCount, sampledAt } | null`（與現有 `bridge.connected／instance／status` 同一次探測取得；Bridge 不可達時 `null`）。
- §4.3 M-19 補「資源使用」欄位的顯示格式：`CPU 12.3%・記憶體 345 MB・3 行程`，無資料顯示 `—`。
- openapi YAML 同步（FE 用 `npm run gen:api-p36` 重產型別，交卷前自己跑一次 `npx openapi-typescript ../docs/02_architecture/openapi-p3-6.yaml -o <暫存檔>` 確認 rc=0）。

**D. 文件**：契約加 §6.6「v1.3 變更一覽（W7）」（裁決對照、每條落點）；Architecture §10 Bridge 契約與 §11 回應模型同步；ADR-001 §4 的 NFR-9.1-05 條目先不動（等 FE 數字）。交卷時先給主控一段「裁決請求」：對映表最終版＋每格的證據行，主控確認後 BE 才開工。

### 3.2 W7-ARCH：PRD 完備性獨立審查（唯讀；量、不挖）

目的：回答掌舵者「PRD 全部功能是否完備、UI 是否依設計稿、三模組是否緊密結合」。**不改任何程式與 RTM**，只寫 `docs/06_quality/Completeness_Audit_W7.md`。

1. **從 PRD 重新推導需求清單**（`docs/01_requirements/Agent_ConsoleUI_PRD.md`，§0 權威）：58 條使用者故事、§4.2 路由、§5.1.4 Markdown 八項、§5.3.2 自治等級表、§5.4.4 告警規則、§5.5 設定鍵（50 鍵）、§9 NFR 表、§11 卷與服務、§12 維運程序。逐條對 `docs/06_quality/RTM.md` 找：(a) PRD 有、RTM 沒有列的；(b) RTM 列有但實作檔／測試欄指到的檔案或測試名稱不存在的（抽樣 ≥40 列，含每個分類）；(c) RTM 判 `✅ 已驗證` 但 E2E 欄沒有可追溯證據（spec 名稱或 QA 報告章節）的。
2. **UI 依設計稿**：`docs/01_requirements/01.UI_Design/Design_ConsoleUI/README.md` 列的畫面逐一對應前端路由與元件（`frontend/app/**`、`frontend/components/domain/**`）；差異是否都已登記在 `ADR-001` §4／§5 或契約 §4。
3. **三模組緊密結合**：Bridge 兩個 router（`engine-bridge/app/routers/autoclaude.py`、`routers/sdd.py`）每個端點在 Console 後端（`backend/.../adapter/out/bridge/BridgeEndpoints.java`、`BridgeHttpAdapter.java`）與前端是否有消費者；PRD 提到的引擎能力（AISDLC_SDD 規格編譯、FSM 狀態、AutoClaude 執行／checkpoint／演化）哪些已接、哪些只是存在於 Bridge 而 Console 沒用到、哪些 PRD 有而 Bridge 沒有。
4. 輸出格式：每筆發現一列——`編號｜類別（缺列／證據失效／設計稿差異／整合缺口）｜PRD 位置｜RTM 列或檔案｜證據（檔案:行號）｜建議處置（本波可修／登缺陷／裁決保留）`；最後一節「結論」用三句話各回答掌舵者的三個問題（能／不能／有條件），不寫空話。發現 0 筆也要寫明查了什麼、怎麼查（指令與結果）。
5. 文件規則：繁體中文；測試計數寫中文字（「十二支」或「12 支通過」）且**不與日期同行**（基線站點鎖）；LF 行尾；不得含「測試摘要字樣＋4 位數字」同行。

### 3.3 W7-FE：D-13 先行，契約定稿後追加 D-12／D-11

**D-13（先做）**：目標 20KB 文件預覽更新中位數 < 100ms，量法＝`frontend/tests/e2e/p9-w5-ui-evidence.spec.ts` 的 `NFR-9.1-05` 區塊（MutationObserver 看預覽區最後一次 DOM 變動、150ms 無變動視為穩定、每種大小 7 次取中位數；內容樣板也照它）。做法：
1. 先重現：對 production 建置（`npm run build` 後 `npm run start`，或與 QA 相同的 standalone）用**同一量法**量 1KB／5KB／20KB 基線並記錄（mock 後端即可，別碰真後端 spec；自己的 Playwright 一律帶 `--output=<自己的暫存目錄>`，埠用 3100）。
2. 待驗假設（逐一用 Chrome DevTools performance profile 或 `performance.measure` 證實或推翻，交卷附數字）：(a) `@uiw/react-markdown-preview` 預設 rehype 外掛鏈（含 rehype-prism-plus 等）與本專案另加的 `rehype-highlight` 對程式碼區塊**重複高亮**——看套件原始碼與 `pluginsFilter` 能否拿掉預設鏈；(b) `useDeferredValue` 對單次大貼入多出一個畫面；(c) `rehypeTaskLabels`／`remark-gfm` 的成本；(d) 預覽端是否還有 `rehype-raw`／`rehype-slug`／autolink 等不需要的外掛。
3. 修法不得退化功能（GFM 表格、程式碼語言高亮、核取清單、匯入／匯出、鍵盤可達 region、axe）；`DEFER_ABOVE_CHARS` 的注解數字要更新成實測值。
4. 交卷附：修前／修後三種大小各 7 次樣本與中位數（同一量法）、改了什麼、為什麼。做不到 < 100ms 就如實寫「未達標」與最佳值。

**D-12／D-11 前端項（契約定稿後由主控訊息通知再做）**：`npm run gen:api-p36` 重產型別；`AgentCard.tsx` 加「資源使用」欄（格式見契約 §4.3 M-19）、刪掉「目前沒有提供這項資料」句；執行頁批次資訊顯示 `engineCapabilities` 兩個晶片（文案：自動突變／自演化＝已啟用／關閉／無金鑰不可用）；設定頁 `effect` 標籤隨契約自動變（確認 `ENGINE` 顯示正確）；vitest 與 mock spec 補齊；RTM 回填檔。

閘門：`npm run lint`（含 Prettier）rc=0、`npx tsc --noEmit` rc=0、`npm run build` rc=0、`npx vitest run` 全過、mock spec 全過、四區塊只在 `app/layout.tsx` 組裝（掃描無輸出）。

### 3.4 W7-INFRA：D-14／D-15 先行，契約定稿後追加 D-12 的 Bridge 項

**D-14（Prometheus SLO）**：
1. 新檔 `docker/prometheus/slo.yml`（`prometheus.yml` 的 `rule_files` 加進去；compose 的 prometheus 掛載照既有方式補）：recording rules `aisdlc:console_availability:ratio_1d`／`_7d`／`_30d` ＝ `avg_over_time(up{job="spring-boot"}[<窗>])`（Console 可用性以後端 `/actuator/prometheus` 的 `up` 為訊號；為什麼不是 nginx：沒有 exporter，寫在檔頭）；告警 `ConsoleDown`（`up{job="spring-boot"}==0` for 1m，critical）與 `ConsoleAvailabilityBelowTarget`（`ratio_30d < 0.995` for 15m，critical，annotation 引 PRD §9.3）。
2. `promtool` 單元測試 `docker/prometheus/tests/slo_test.yml`：至少兩個案例——30 天內停機 1% 時 `ratio_30d` 低於 0.995 且告警 firing；停機 0.1% 時不 firing；`ConsoleDown` 在連續 0 超過 1 分鐘時 firing。跑法（Windows Docker Desktop，絕對路徑掛載）：`docker run --rm -v <repo>\AgentConsole\docker\prometheus:/etc/prometheus --entrypoint promtool prom/prometheus:v3.15.0 test rules /etc/prometheus/tests/slo_test.yml`，另跑 `check rules` 與 `check config`；三條指令與 rc 逐字進交卷。
3. Grafana `docker/grafana/dashboards/app-overview.json` 加 SLO stat 面板（30 天可用率，閾值 99.5% 紅／綠）與 1 天可用率時序面板；JSON 要能被 provisioning 載入（全棧起來後 `GET /api/dashboards/uid/<uid>` 看得到面板）。
4. `docker/README.md` §7 監控補一段「可用性 SLO 怎麼看」。

**D-15（HTTPS 可重現）**：照 `docker/README.md`〈14〉在 Docker 全棧（`--profile db --profile app --profile full`）實跑一次：自簽憑證進 `aisdlc_nginx_certs` 卷、`https.conf` 啟用、80→443 轉址、`nginx -t`、`curl.exe -k https://localhost/nginx-health` 200、經 HTTPS 登入打到真實後端（`/api/v1/auth/login` 200）、`http://localhost/x` 301、`/nginx-health` 80 埠仍 200、`docker compose ps nginx` healthy。步驟哪裡卡就把 README〈14〉修到可照抄（PowerShell 形態一併）；**收尾一定要還原**：刪 `https.conf`、`default.conf` 改回、`down`（不要 `down -v`，除非是你自己起的乾淨專案）。全棧只准在 INFRA 自驗時起一次，跑完就收，QA 之後會再獨立起。

**D-12 Bridge 項（契約定稿後由主控訊息通知再做）**：`RunStateOut.resources` 與背景取樣器（規格見 §3.1 C；psutil，Windows 可跑；`cpu_percent` 第一筆 0.0 可接受；終態或行程不存活回 `null`）；pytest 補：有行程時 `resources` 非空且欄位型別正確、終態後為 `null`、取樣器對已消失的 pid 不炸；`ruff check` 兩視角 rc=0；RTM 回填檔。

閘門：`ruff check`（本目錄與 monorepo 根視角）、`python -m pytest -q`（根層 `.venv`）、`docker build` Bridge 映像 rc=0、`docker compose config` 四種 profile rc=0、shellcheck 基線不變、根層 `TestDirEntryPrimitivesAreAccountedFor`。

### 3.5 W7-BE（第二波）：D-11、D-12 後端

- `ConfigMaterializer.materialize(int autonomyLevel)`：依契約 v1.3 的對映物化 `minimax.*`／`playbook.*`；回傳 `engineCapabilities`；`execution_runs` 新欄＋Flyway＋entity；`ExecutionRunResponse` 帶 `engineCapabilities` 與 `bridge.resources`（投影 Bridge `RunStateOut.resources`）；`ConfigCatalog` 兩鍵 `effect` 改 `ENGINE` 與 impactNote（附錄 C 一致）；`ReviewGatePolicy` 不動（等級 6～10 的審核閘行為同 5）。
- 測試：物化決策表單元測試（每個等級 × 金鑰有無 × 兩個設定值）、`ExecutionLifecycleApiIT` 補 `engineCapabilities` 與 `bridge.resources` 的 IT（MiniBridge 回 `resources`）、`SchemaMigrationIT` 新版本。閘門：`.\gradlew.bat clean build` BUILD SUCCESSFUL、JaCoCo ≥80%、Checkstyle 0、ArchUnit 全過。

### 3.6 W7-QA（第三波）：獨立零信任驗證＋RTM 單線合併

先讀 `agent_briefs/W5_QA_Reverify.md`（流程、環境、腳本）與 `docs/06_quality/QA_W5_Reverification.md`（上一版報告的格式），上一 session 的可複用腳本在 `C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\6121f0db-8785-4286-9143-5c37c2fc9496\scratchpad\qa\`（`reset_local.ps1`、`start_backend.ps1`、`start_fake_bridge.ps1`、`qa_lib.ps1`、`master_rerun.ps1`…），複製到自己的暫存目錄再用。`E2E_ROOT` 用 `$env:TEMP\e2e`（短且可刪，**不要放磁碟根**）。

1. 五列逐一親驗並改 RTM：`API-AUT-06`（契約 v1.3 **E2E-14** 第 1～7 列：`engineCapabilities` 三種值、磁碟 `<ENGINE_WORKSPACE>/<runId>/config.yaml` 以 YAML 解析器斷言、否定斷言 `playbook` 區段無 `max_evolutions`／`require_evolution_signoff`、假伺服器請求分類計數；順手把同一支 spec 擴到附錄 C 其餘標 ENGINE 的鍵——審查報告 V-12）、`US-M-10`（E2E-14 第 8～9 列：真後端長批次執行中 AgentCard 顯示 CPU／記憶體／行程數為數值且 `sampledAt` 前進，終態／PAUSED／Bridge 停掉後 `—`）、`NFR-9.1-05`（同 W5 量法、production 建置 `E2E_MODE=standalone` 重量 1／5／20KB 各 7 次中位數；把 `p9-w5-ui-evidence.spec.ts` 的 20KB 上限由 `< 400` 收緊為 `< 100`、標題與註解更新）、`NFR-9.3-01`（全棧起來**等約 2 分鐘**後：`GET :9090/api/v1/rules` 兩個群組五條規則 health ok、`query?query=aisdlc:console_availability:ratio_30d` 回值、Grafana `GET /api/dashboards/uid/aisdlc-app` 面板 id 21／22／23；promtool 三條照 README〈7〉親跑）、`INF-VOL-07`（README〈14〉獨立重跑，證據逐字；**先記下卷內 `fullchain.pem` 的指紋／notAfter，步驟 1a 跑完必須變化**——INFRA 殘留的 `aisdlc_nginx_certs` 卷裡已有一張自簽憑證，不證明變化就不算獨立重驗）。
2. 契約 v1.4 新增面（第二批交卷後才驗）：**E2E-15** AISDLC_SDD 接入（`GET /api/v1/engines/sdd`、監控頁「AISDLC_SDD 引擎」卡與 `AISDLC_SDD/<LATEST>/build/reports/fsm/FSM-STATE-AISDLC_SDD.yaml` 逐欄比對＝NFR-OBS-01 補強）、`GET /api/v1/signoffs/pending` 與儀表板清單／通知鈴連結（審查 I-05 的三種漏列草案都要造出來驗）、`autoclaude.healthCheckPath` 預設 `/health/deep`（Bridge 停掉或 `SDD_ROOT` 指到無效目錄時 Agent 可用率要降、頂列燈要變）、Redis refresh token 撤銷（登出後舊 refresh token → 401；Redis 停掉後登出仍可用且日誌有 WARN）、DAG 全螢幕（Esc 關閉、焦點歸還、axe）。
3. ARCH 審查報告（`Completeness_Audit_W7.md`）的發現逐筆核實：已由本波修掉的寫結案證據；真的缺且未修＝登 DEF-AC-012 起算、附重現；誤報＝寫明為何不是。**V-08**：九個畫面對 `docs/01_requirements/01.UI_Design/Design_ConsoleUI/screenshots/*.png` 做一次對照（DOM 結構斷言＋人眼差異描述），寫進 `UI-SCR-01～09` 的 E2E 欄。**L-01／L-02**：RTM 補 `INF-SVC-16`、`INF-VOL-09～12`（含 `prometheus_data`）與「只儲存／未驗設定鍵」追溯列；V-01～V-05、V-10 照報告建議處置。
4. Docker 全棧：**沿用 INFRA 的 `--env-file`**（`C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\8d63899d-5f25-4657-a85c-c8ae99f5656d\scratchpad\w7_infra\stack.env`，拋棄式隨機值；殘留卷內的 PG 是用它初始化的，換一份會連不上）；不要嘗試 `down -v`（分類器會擋，也不要用等價指令繞），收尾只 `down`。
5. 回歸：本機整套真後端 Playwright（含新 spec）與 Docker 全棧情境各跑一次（兩者不同時跑）；lint／tsc；RTM 單線合併四份 `rtm_backfill_W7*.md`（BE／FE／INFRA 三份，`SA` 無回填檔），狀態只准依當回合證據升級。
6. 報告 `docs/06_quality/QA_W7_Closure.md`：每列證據（指令、關鍵輸出逐字、log 絕對路徑）、缺陷表、ARCH 27 筆的逐筆處置表、〈未覆蓋〉、〈給主控的提醒〉、RTM 現查數字（Grep count）。

## 4. 環境事實（Windows 11，主控已實證；違反會白跑）

- 只用 PowerShell 工具；不裸 `cd`（`Push-Location <絕對路徑>; …; Pop-Location` 同一呼叫）；讀 rc 不接管線（先 `*> log` 再讀 `$LASTEXITCODE`）；跑 Bash 工具會被 hook 擋。
- Node v22.23.3（硬性）、OpenJDK 21、Gradle 9.8.1、Python 3.11（根層 `.venv`，Bridge 已以 `uv pip install -e` 裝入）、Docker Desktop。
- 埠：5432 `autoclaude_pg` **不准動**；5433 被原生 postgres 佔用；自己起 PG 用 25433（QA）或 15433（開發）（`docker run -d --rm --name <你的名字> …`，收尾 `docker stop`；`docker rm -f` 會被守衛擋）。backend 用 18080、Bridge 18081；**Bridge 先於 backend 啟動**（否則 `agentAvailability` 變 75），backend 先跑 Flyway 建 `console` schema；輪詢 ≥1 秒（e2e profile 限流每使用者每分鐘 100 次）。
- 並行 Playwright 互踩：任何 Playwright 執行一律 `--output=<自己的暫存目錄>`（共用 `frontend/test-results` 會被對方開跑時清空）；mock spec 與真後端 spec 不要同機同時跑；`next dev` 會被同樹內的截圖寫入觸發整頁重載。
- backend 跑著時 `gradlew clean build` 會失敗（jar 被鎖）；Playwright dev 模式起跑前先刪 `frontend\.next\dev`。
- 機密掃描：commit 會擋 `user:pw@host` 形態的 DSN 與 `sk-` 開頭的假 key——夾具一律用 `your_password_here`／不帶 `sk-` 前綴的佔位。
- 文件：繁體中文；測試計數寫中文（「230 支通過」），不與日期同行（基線站點鎖）；所有文字檔 LF；新 Python 一律 `encoding="utf-8"`、時間戳帶 tz、平台 API 罩 `sys.platform`；Write／Edit 工具會把 `\uXXXX` 解碼成實體字元（Java 原始碼要寫跳脫形式時交卷前用位元組掃描核對）。
- 鐵律 11：每做一條就編譯＋跑對應測試，不累積；失敗立即修，不跳過、不註解掉。
- 本機整套 Playwright（約 52 分）與 Docker 全棧（約 11 分）不要同時跑（Windows `ERR_NO_BUFFER_SPACE`）。

## 5. 交卷格式（每棒相同）

`STATUS: DONE|PARTIAL`；〈做了什麼〉（絕對路徑、每條對應 D-1x）；〈驗證證據〉（每道閘門的指令與 rc、關鍵輸出逐字，log 絕對路徑）；〈沒做／偏離〉（含原因）；〈給 QA 的提醒〉（怎麼驗、RTM 哪幾列該改）；〈git --no-optional-locks status --porcelain 全文〉（標出哪些不是你的）。宣稱「已驗證／通過」必附當回合真跑的輸出；「根因是 X」在實證前只是待驗假設。
