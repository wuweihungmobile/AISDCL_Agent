# R218 額度牆續航／掌控／副作用隔離（本批落地前收尾）證據（W16-CLOSE1 單人窗口，2026-11-23）

> 範圍：R218 本批已 commit 但尚未 push 的 Q1～Q5、W1～W4b、W11a／c／d、S1～S6、FIX2、FIX3；本檔只收「缺陷明細」與收尾決策，
> 帳本列只留索引。剩餘工作（W11b、W6 續棒、W5、Q6、W11e、W7、終局 E2E 全跑）屬下一批，見〈未完成〉。
> 上游：`docs/02_architecture/` 的 QuotaWall 設計（r9 附錄 H）、Control_Handover 設計、`docs/03_testing/contracts/` 對應 TCS。

## 一、缺陷明細

### DEF-200-638（2026-11-23 撞五小時上限事件）
2026-11-23 10:00～10:40 主控與子代理撞五小時窗上限（讀數 10:00:02 為 80%，reset 10:40；10:21:19 harness 擋下）。RCA 為五個疊加的缺口：
1. `--pace` 標題把「最緊」綁到週軸，五小時窗的 converge 帶被藏掉（平手取剩餘分鐘較長者）；主控因此讀成「短窗降到注意帶」。
2. watch 額度閂鎖單一序列，07:43 一次 close 誤報（ping_pp 被在飛代理灌大）鎖住後，prepare 跨線與新派工都無聲。
3. 擋派判準寫好了沒接 hook（Q4 待辦），且可行性算式沒算在飛燃燒量。
4. realverify 開跑前沒有額度閘，撞牆的失敗被判成 FAIL。
5. 保溫成本 ping_pp 只有一筆樣本（6.0），且被在飛代理污染。
已修：W11c（f17da09a，ping 成本樣本修正與可行性算式加在飛燒量）、Q4＋W11a（348a2b62，PreToolUse 額度牆擋派與 Stop 認主載具）、W11d（059253c2，watch 額度閂鎖拆兩條序列、新派工重評、文案依來源）。
未修：W11b（`--pace` 標題呈現層）、W11e（realverify 額度前置），下一批。

### DEF-200-639（被停代理半成品被運作中 hook 載入）
2026-11-23 12:2x：主控 TaskStop 改守衛面的 Q4／W6 代理後，半成品 `converge.py` 被運作中的 `sessionctl_guard.py` 載入，污染值使額度擋派在 54% 硬擋主控派工。
緩解：`git stash create` 保全成 tag 與副本後把工作樹還原到 HEAD；教訓入記憶。根治（機械物）未做：停代理後沒有任何程序提醒「守衛面半成品須立刻移出運作路徑」。

### DEF-200-640（Stop 保溫閘在 park 標記有效時仍推回）
2026-11-23 12:4x（上下文 355,247）：park 標記 armed 且在有效窗內，Stop 保溫閘照樣推回要求掛 keepwarm；照做會使到點 fire 判 live_driver 而跳過換手。DES 把「park 標記有效」列為不掛的情形，實作與其不一致。
狀態：待修（348a2b62 的牆中靜音不涵蓋此分支；修後以 park 有效標記的 Stop 重放確認）。

### DEF-200-641（M-K9「宣稱已排程但未續上」）
`python tools/probe/waste_census.py --switch-metrics` 的 M-K9 判出 e4f80b15：2026-11-17 park spawn（`28059aa2`）首回合晚 66 分，即「宣稱已排程」與「實際續上」不一致。Q5（d4e95558）已能量到並印出，成因與偵測面由 Q6 承接。

### DEF-200-642（Q3 smoke 到點未起）
Q3（c258fb76）smoke 首跑 park 到點未起，原因未明。Q6 須偵測並區分（排程未到點／到點被讓路／失敗鏈終局）。

### DEF-200-643（RV-SE18 沙盒清理順序）
S6（48a6cecb）RV-SE18 FAIL：沙盒清理失敗後身分檔寫回順序錯誤、abandoned 下 note 項未處置。已修 6f4a9a86（FIX2，含 RV-K5 宣告 150 分租約）；回歸為 `test_realverify_*` 與真機 RV-SE18、RV-K5 PASS。

### DEF-200-644（check_pending_handoff 測試讀真 OIR 帳本）
7 個 `test_check_pending_handoff` 案例讀真 `OpenItems` 帳本的 capnote，隨帳本內容變紅；已修 c720b865（FIX3，測試改密閉）。

### DEF-200-645（測試把交接包寫進真 `~/.autosdd/handoff`）
2026-11-23 18:14 FIX3 以 pytest xdist `-n 14` 全量跑時，某支 handoff 相關測試把交接包寫進真 `~/.autosdd/handoff/sid-1_20261123T101410Z.md`（假 sid `sid-1`，HEAD 059253c2；主控已刪該檔）。疑似靠 `setUpModule`／行程環境設 `AUTOSDD_HANDOFF_DIR`，xdist 下順序或行程不同而失效；同族：`test_sessionctl_handoff.setUpModule` 洩漏 `AUTOSDD_SENTINEL_OFF`。
狀態：待修（逐支定位未做）。

## 二、收尾決策

1. 棘輪／掃描下限依各鎖訊息逐字重釘（舊→新值見交卷報告），不放寬方向、不刪測試；tools/tests 的 E501 存量棘輪只准往下，新增超寬行逐一折行（`_E501_DEBT_CEILING` 維持 136）。
2. 本批新增模組補登 `Root_Layout_and_Module_Placement.md` §3。
3. 帳本輪號推進到 R218（本檔檔名即時鐘），讓程式註解的 R218 標籤與帳本一致。

## 三、未完成

W11b、W11e、W6 續棒、W5、Q6、W7、終局 E2E 全跑與獨立 QA 審查。另列待修：`test_subprocess_encoding_hygiene` 指出四處 `text=True` 無 `encoding="utf-8", errors="replace"` 的真違規，屬 `tools/lib`／`tools/probe` 產品面，本窗依任務書不動，列交主控：`tools/lib/realverify/cases/sideeffect_prod.py:76`、`tools/lib/realverify/leases_undo.py:42`、`tools/probe/realverify_se_s5_smoke.py:45` 與 `:57`（測試側 `test_realverify_se_locks.py:672` 已於本窗補齊）。
