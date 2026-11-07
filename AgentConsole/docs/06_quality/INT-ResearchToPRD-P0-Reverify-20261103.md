# INT-P0 重驗補記（2026-11-03 10:4x～10:5x；主控親跑；鍵 agentconsole-research-to-prd-p0）

承接 `INT-P0-DockerMockE2E-20261103.md`（一審 INT 14 缺陷）。三支修復棒落地後以 Docker 全棧重驗：backend／engine-bridge 映像以 `f2369e7b`（含 FIX-BR `4d239986`、FIX-API `f2369e7b`）重建於 09:2x，frontend 映像以 FIX-FE 工作樹（＝commit `2254a468`）重建於 10:47；四容器 healthy。載具＝FIX-FE 新增的真棧 spec `AgentConsole/frontend/tests/e2e/research-docker.stack.spec.ts`（`docker.config.ts`、chromium、`E2E_STACK=1`、三角色帳密走環境變數、自 `backend/README.md` 開發預設解析、不印出），經 nginx 80 埠。

## 結果

| 劇本 | 測試 | 結果 | 時間 | 涵蓋的 INT 缺陷／AT |
|------|------|------|------|------------------|
| pass | AT_960_22_5 UI 殼層（側欄入口、390 Tab、零專案空狀態、超前 ?step= 導回、步驟 3～5 占位、mock-only 停用深研、VIEWER／OPERATOR／ADMIN 角色） | ✓ | 1.9 分 | INT-08（有效主機區可見）、INT-03（議題面板 camelCase 值）、AC-R2P-01／08-3 |
| pass | AT_960_22_E_1 無障礙與響應式（1440／1000／600 無水平溢出、axe 無 serious／critical；Studio 600 分頁籤；對話框焦點） | ✓ | 3.1 分 | INT-14⑤（1440 工作室 md-preview-region 不含 r2p:section）、AC-R2P-21-3 |
| pass | AT_960_22_3 路徑 B（審查通過→ADMIN UI 核准→FSM 凍結；凍結摘要＝FSM 視圖＝容器內檔案位元組；二次核准 409；OPERATOR 403；對帳一致） | ✓ | 2.7 秒 | INT-01（對帳列 id＋camelCase）、INT-09（凍結後 review-stale 計 0）、INT-13（D-72 核准只比對送來的鍵）、AC-R2P-06-2／06-4／10-1 |
| pass | AT_960_22_4 SSE 斷線重播（載入前 route.abort 串流、期間有事件、解除後自動重連、seq 連續無缺漏無重複；重載後動態欄＝資料庫） | ✓ | 1.3 分 | INT-12（重連後無新事件時動態欄補齊）、AC-R2P-08-3 |
| pass | AT_960_22_2 | skipped（需 fail3 劇本） | — | — |
| fail3 | AT_960_22_2 路徑 A（三輪審查都未通過、第 3 輪 ESCALATE；FSM 現態 ESCALATION 而非 AUTO_RECOVERY_ATTEMPT；工作室 ESCALATION 區塊與可複製恢復指令、沒有恢復動詞按鈕；R1～R5、R9、R13、R14 各至少一筆、R6 為零） | ✓ | 1.0 分 | INT-02／04／05（D-77 失敗游標與相態）、INT-07（研究 run 零外呼：fail3 全程 mock）、AC-R2P-04-11 |

pass 劇本：`4 passed／1 skipped`、rc 0、6.4 分（10:48:52～10:55:16）。fail3 劇本：`1 passed`、rc 0、1.0 分（10:56～10:57）；切換方式＝改 `AgentConsole/.env` 的 `MOCK_CLAUDE_RESEARCH_SCRIPT` 並 `docker compose … up -d engine-bridge`（第一次切換有 Recreated；切回 pass 時 compose 印 Running、容器內仍是 fail3 ⇒ 改用 `--force-recreate` 才吃到新值；見〈注意〉）。log：`scratchpad\r2p\dev\PKG-FIX-FE\stack-helm-pass.log`、`stack-helm-fail3.log`；Playwright 輸出 `pw-stack-helm-pass\`、`pw-stack-helm-fail3\`。

## 一審 14 缺陷對照（重驗後）
- 真棧 spec 直接覆蓋：INT-01、02、03、04、05、07、08、09、12、13、14⑤。
- 單元／mock 層覆蓋（FIX 棒交卷自證＋主控親驗全套綠，真棧無對應流程）：INT-06（劇本模式零外呼＝engine-bridge `test_research_offline.py`）、INT-10（對帳每檔一列＝Bridge 單元）、INT-11（README 夾具六軸）、INT-14⑥（失敗徽章＝vitest＋a11y mock 清單兩列）。
- 未在真棧驗到：取消流程（INT-04 的 cancelled 文案只到 vitest）、422 digest_mismatch／missing_digests 的 UI 文案（真棧無觸發路徑；後端 IT 覆蓋）。

## 注意（給 QA 二審與 P1）
1. `docker compose up -d <svc>` 在 `.env` 值改變時**不保證**重建容器（本次切回 pass 時印 Running 未重建），切劇本後一律 `--force-recreate` 並以 `docker exec … echo $MOCK_CLAUDE_RESEARCH_SCRIPT` 驗證；TCS §5.2 跑法與 `tests/e2e/README.md` 應註明。
2. 全站同時只准一個階段 run；限流每人每分鐘 100 次且 UI／REST 共用桶 ⇒ 真棧 spec 不可與其他真後端 spec 或人工研究並行（FIX-FE 交卷 O）。
3. 真棧工作區目錄（e2e-*／probe-*）留在 Bridge volume `/workspace/my-project/`（封存不刪檔）；資料庫未封存研究專案為 0。
