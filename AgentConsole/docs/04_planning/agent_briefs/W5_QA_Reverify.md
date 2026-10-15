# 任務書 W5-QA：修復波獨立複驗、RTM 單線合併、缺陷結案

> 先讀 `W5_OVERVIEW.md`（裁決 C-1～C-22）與 W4 的 `W4_QA_E2E.md`、`docs/06_quality/QA_P3-6_E2E_Verification.md`（你的上一版報告；環境與啟動法在 §2 與 `frontend/tests/e2e/README.md`〈真 Bridge specs〉〈Docker 全棧〉）。你是零信任的獨立 QA：三棒（BE／FE／INFRA）的交卷與契約 v1.2 已由主控 commit，交卷裡的「已驗證」一律不採信、親自重跑。

## 持有面

`frontend/tests/e2e/**`（真後端 spec、`test.fail` 移除、新情境、截圖）、`docs/06_quality/**`（`RTM.md` 單線合併、`QA_P3-6_E2E_Verification.md` 加〈W5 複驗〉章或另立 `QA_W5_Reverification.md`）。不改 backend／frontend 程式／engine-bridge／docker／契約；程式有缺陷就登記（沿用 `DEF-AC-0NN` 連號，不改既有編號）並用 `test.fail` 釘住；不 commit。

## 範圍

1. **閘門重跑**：後端 `gradlew clean build`、前端 lint／tsc／build／vitest、Bridge ruff／pytest、Bridge `docker build`＋`git --version`、根層 `TestDirEntryPrimitivesAreAccountedFor`，數字逐字貼。
2. **缺陷逐條結案**（DEF-AC-001～010）：依契約 v1.2 寫或改真後端 spec 驗證；修好的移除 `test.fail`（p3 的 001、p6 的 002、p8 的 007／008），沒修好的維持並在報告寫明；RTM 對應列 `❌ 缺陷` → `✅ 已驗證`。
3. **新端點與行為**（契約 §6.5 變更一覽逐條）：C-1 task-totals 與各專案 task-trend 加總相等（真後端 spec，≥3 個專案）、儀表板真後端下每分鐘請求數重量（照上一版 §8 的方法，目標 ≤10 次）；C-3 restore 三種 409／404 與 UI 復原；C-4 PDF 下載（內容可抽出中文字）；C-5 經 nginx 重啟 backend 不登出、串流重連；C-6 原樣匯入 0 errors；C-7 跨批次升級各自告警；C-8 執行中刪目標 409；C-10 重開匯入記錄有 warnings；C-11 列表晶片；C-12 Bridge 日誌行含 trace_id 且與 backend 回應的 X-Trace-Id 相同；C-15 `/api/health` 經 nginx 200、error_log 無 token；C-16 未設金鑰 compose 拒起；C-17 空卷還原成功。
4. **Docker 全棧**（經 nginx）：映像重建後路徑 A 全鏈批次 COMPLETED（DEF-AC-003 結案證據）；`docker.config.ts` 整套；RPO／RTO 演練用新 restore.sh 在空卷上重做一次。
5. **本機整套**：`npx playwright test`（真後端＋假 Brain Bridge＋乾淨庫）全套一次，數字逐字；新 spec 全部過 `waitForQuota`／`ensureQuota`。
6. **RTM 單線合併**：合併 `rtm_backfill_W5BE.md`／`W5FE.md`／`W5INFRA.md`；追加新列 `API-MON-08`（task-totals）、`API-PRJ-06`（restore）、`BR-26`（/health/deep），編號接在各前綴最大號後、不改既有列號；主控裁決改列：UI-KPI-01／02 → ✅（引用 ADR-001 G-20）、US-M-09 → ✅（C-14 附註）、NFR-9.3-01 → `🟡 部分`（E2E 欄：「可用性量測機制已就緒（Prometheus `up`＋Grafana 面板，W2-B）；99.5% 需 30 天觀測，由營運持續量測」）；`✅ 實作+測試` 的 5 列（UI-DS-04／06／07、UI-OVL-02／03）補真瀏覽器逐項證據後升 ✅；UI-A11Y-02 逐頁鍵盤走查（Tab／Enter／Esc、拖曳的鍵盤替代）後升 ✅ 或登缺陷；NFR-9.1-05 重量 20KB；INF-DR-13 以手動觸發清理腳本對假的舊 WAL 檔驗行為。目標：`⬜ 未開始`＝0、`❌ 缺陷`＝0（沒修好的除外，須列清單）、`🟡` 只剩主控裁決維持列（API-AUT-06、US-M-10、INF-VOL-07、NFR-9.3-01）與你登記的新缺陷。
7. **RTM 計數現查**（Implementation_Plan W4 閘門的兩條指令）與基線站點鎖 `python tools\check_pytest_baseline_sites.py` rc=0；`AgentConsole/CLAUDE.md` ≤200 行、`README.md` ≤80 行。

## 交卷

依 `W5_OVERVIEW.md` §5；另附 RTM 狀態分佈表（前綴×狀態）、新登缺陷清單、〈未覆蓋〉；收尾把自己起的 backend／Bridge／前端／PG 容器／全棧全部收掉並貼行程與 `docker ps` 證據；被整套跑改寫的已追蹤截圖用 `git show HEAD:<path>` 位元組寫回（不用 restore／checkout）。
