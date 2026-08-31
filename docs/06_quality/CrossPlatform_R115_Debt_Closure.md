# CrossPlatform R115 技術債結案輪 — 證據檔（Windows 11）

> 輪次性質：結案輪（R114 交棒書指定 G1~G4 實作批四方複審最優先）。
> 開場量測（2026-09-01 01:02）：未結 55／168（warn=86）、歸檔 rc=0、守衛線 90351（+0、漂移 0）、pace band=free。
> 本檔＝R115 唯一逐字證據載體；量化數字皆當回合實測。

## 1. G1~G4 實作批四方複審（一審）

| 方 | verdict | blocking |
|---|---|---|
| Architect | REJECT | 5（ARCH-1~5） |
| SA | APPROVE_WITH_CONDITIONS | 6（SA-1~6）＋SA-10 結案射程判定 |
| SD | APPROVE_WITH_CONDITIONS | 3（SD-1~3） |
| QA | REJECT | 5（QA-1~5）＋QA-9 T-r95 實測重種 |

去重後 9 個收斂項（舵手親驗三個關鍵爭點皆屬實）：

| # | 收斂項 | 命中方 |
|---|---|---|
| C1 | `state["handback_path"]` production 從未寫入 ⇒ 接力判準③恆空、RELAY_NEXT 生產面不可達、DONE 假宣稱（測試 mock 掉接縫＝載具盲區同型） | ARCH 獨家 |
| C2 | A-PRE 拒 spawn 被寫成 `state="resumed"`（拒絕≠跑過家族在新分支復發） | ARCH＝SD＝QA |
| C3 | 施工圖判準④「前快照落 resume log 痕跡」未實作 | 四方 |
| C4 | 「reset_at 變更歸零」宣稱與 code 不符（鐵律四）＋歸零邊界零測試 | 四方 |
| C5 | `~` 展開 [需核對] 未履行＋settings 靜態 vs handback 動態解析分歧 | SD＝SA＝ARCH |
| C6 | 重掛失敗路徑（清閂＋loud）零測試＋V-d1(正面) 缺＋V-d2 後半實作不符 | QA＝SA＝ARCH |
| C7 | V-e2e 演練載具零交付**零申報**（靜默缺格） | ARCH＝SA＝QA |
| C8 | `_GOV_EXACT` 二檔未納管＋DEF-200-238 未同批（仲裁＝施工圖括號明文「治理面由收尾單人窗口執行」⇒ 非實作批缺陷，本輪治理批完成） | SA＝QA（SD/ARCH 判掛號延辦） |
| C9 | 守衛線 R113/R114 分掛程序＋連續上升 cap=2 已滿 ⇒ R115 淨額必須 ≤0 | ARCH 獨家 |

## 2. 修復波（三棒串行＋治理批＋收斂棒，sonnet 載具）

| 棒 | 交付 | 驗證 |
|---|---|---|
| 棒A（C1~C4） | planner 補 `state["handback_path"]`＋A-PRE 寫回 REFUSE＋`relay_snapshot_before` 事件＋`apply_reset_at()` 兩站點接線＋`_base_state` 無 relay 鍵鎖 | 逐項突變驗紅；`test_context_budget_guard.py` 506 passed rc=0 |
| 棒B（C5+C6+239） | `_add_dir_argv()` 動態補 handback 現解＋RearmAfterStop 失敗/成功測試＋`_heal_armed_drift` rc≠0 補清 stamp＋loud＋`_tick` 注入 `_StatefulFakeSchedulerBackend`＋回歸鎖 | 逐項突變驗紅；513 passed rc=0 |
| 棒C（C7） | V-e2e 演練載具（12 場景） | 12/12 rc=0＋`--break` rc=1 自證偽 |
| 治理批（C8） | `_GOV_EXACT` 納管二檔＋`_fold_gov_path()` 大小寫正規化（射程普查表：只收窄 Windows×不存在×大小寫錯誤一格，posix 逐位元組不變）＋6 支回歸測試 | R114 §4 探針重演：兩繞過形態轉命中、既存變體未退化；假紅普查前後零位移；158 passed rc=0 |
| 收斂棒（C9） | 史料搬遷三檔 docstring 沿革 -930 行至 `CrossPlatform_Guard_Line_History.md`〈R115 追加〉節 ⇒ R115 淨額 **-11**（90351→90340，款(11) 連升 streak 終止、款(12) 到期兌現 `(115,577)`＋重新武裝 117/570、sha 接鏈 ea038ea6→4e5f1156）；`_REPIN_APPROVED_ROUND_OVERAGE` 名冊零改動 | `--print-guard-lines` 現查一致；`test_adr_xplat001_c1c2_lock.py` 160 passed |

V-e2e 載具形態裁量：PRD 草案名 `.sh` 的實交付＝純 Python（`tools/probe/replay_r113_lastmile_driver.py`）——初版 .sh 薄殼為單邊腳本、撞 ADR-XPLAT-002 §4.2 AC/UEP 張力（AC 上升須具名對應 UEP 下降，本輪無 UEP 可降），而薄殼只做「找 python 跑本檔」，Python 直跑零豁免需求且雙平台同一條指令。裁量記於 driver docstring。

## 3. 四方定點複審（二審）

QA＝AWC（六條全證實修好；條件＝239 帳本結案，本檔 §7 已補）／Architect＝AWC（五條全證實；淨額算術覆核 -11 自洽；條件＝分掛程序顯式攤給掌舵者，見輪尾報告）／SA＝AWC（五條證實＋SA-4 的 `PowerShell(...)` allow 語法安排可接受為條件——deny 語法已由實彈演練意外實證，見 §4）／SD＝APPROVE（三條逐行證實；五個新函式零缺陷；SD-4／SD-8 advisory 座標未位移，留帳）。**二審零新程式 blocking ⇒ 收斂標準「四方皆無新發現」達成。**

## 4. 開閥＋實彈演練（2026-09-01 06:40）

- 總閥：`AUTOSDD_RESUME_OFF`（User 層）before=1 → after=空（已移除）。
- 演練設計：合成撞線任務書（犧牲 session `74403d0c…`）＋`--resume-tick` 手動觸發（help 明文驗證情境）＋`AUTOSDD_RELAY_MAX_SPAWNS=1` 只掛單一指令。**零 mock**：真探測、真 spawn headless、真排程器。
- 事件鏈逐字（`autosdd_resume_log_plan.jsonl`）：`woken` → `probed {rc:0, open:true}` → `route_chosen {SESSION_RESUME}` → `relay_snapshot_before {lines:33, digest:43c3c67a…}` → `resumed {handback_written:true}` → `relay_stopped {why:no_progress, note_written:true, notify_rc:-2}` → `sentinel_armed {credential:2026/9/1 上午 06:56:10}` → `relay_rearmed {next_state:NO_PROGRESS_STOP}`。
- 四缺口實彈判定：**G1** headless 窗口成功寫出 handback 新檔（R113 原事故正是此格被權限牆擋）；**G2** `~/.autosdd/handback/74403d0c….md` 四節齊；**G3** 零推進即停＋loud（`AUTOSDD_ATTENTION.md`）——落 NO_PROGRESS_STOP 而非 DONE，符合已記載的「『下一步指令』佔位文字恆真 ⇒ 判準④先短路」保守語意；**G4** 演練排程 REMOVED → 哨兵重掛 **NextRunTime=2026/9/1 上午 06:56:10 值憑證**。
- 意外實彈證據兩筆：① `resumed.err` 逐字 `Permission deny rule (.claude\settings.unattended.json): Write(./tools/tests/test_adr_x…`＝headless 窗口試寫 L3 保護面被 deny 實彈擋下（V-a3 動態半格＋settings 載入與 permissions deny 語法有效性就地驗證；SA-4 未驗面縮至 allow 的 `PowerShell(...)` 前綴語意）；② `notify_rc=-2`＝通知投遞失敗不重投的活體重現＝DEF-200-236 不可結案的佐證。
- 演練殘留清理：演練哨兵與 `T-live-drill-r115` 皆現查 confirmed gone；handback 檔**刻意留存**——下個互動 session 開場 SessionStart 未讀偵測應出聲一次（G2 SessionStart 面的自然驗證），看到即可 `.ack` 落地。

## 5. 舵手親踩親修：CLAUDE.md 教學形態 `-n` 假綠

根 CLAUDE.md 鐵律一原教 `.sh` 執行形態 `& (Find-GitBash) -n '<路徑>'`——bash 的 `-n`＝noexec（只檢查語法不執行），照抄「跑」腳本得 rc=0 假綠零輸出（本輪實測踩坑：第一跑 rc=0 零場景輸出、去 `-n` 重跑才真執行）。修復 7 站點（CLAUDE.md 教學行＋`lint_powershell_command.py` 指引訊息＋`test_bootstrap_core.py`／`test_check_hooks_liveness.py` 合法形態語料×4＋V-e2e 註解），受影響測試 192 passed rc=0。

## 6. 呈報單第 2 件執行：v0.02~v0.04 十二支假 SHA drift 檔 git rm

掌舵者 2026-09-01 互動裁決「核准 git rm（Recommended）」。刪除前查證零程式消費者（樣式 Grep 全樹僅存證文件自身）；`git status --porcelain` 恰 12 列 `D `、真 SHA 檔（`COMMIT-769eea4e3f66.yaml`）三版皆保留。存證＝`AISDLC_SDD/AISDLC_SDD_v0.30/EVOLUTION_LOG.md`〈凍結基線例外：v0.02～v0.04 測試假 SHA drift 殘留檔移除〉節（比照 R107 八欄體例；純刪測試產物、不計破例回補次數）。

## 7. 帳本異動（`current_round()` 讀「發現情境」欄——本輪編修全在狀態欄，時鐘不推）

- 結案 3 列：DEF-200-238（治理批）、DEF-200-239（棒B＋全套後 `Get-ScheduledTask T-r95` 現查為空）、DEF-200-235（解鎖條件全兌現：v2.1.13 落地＋過四方＋實彈演練）。
- 進度注記 2 列（維持 open）：DEF-200-234（餘 ADR-XPLAT-014 §4 那半）、DEF-200-236（餘 §3-4 補投佇列；實彈 `notify_rc=-2` 佐證）。
- 長債軌 7 筆 14 天複查完成（複查日 2026-09-01；全數未達解鎖條件）：DEF-101-886 條件改寫（原「等具名序列化條款」已無可達成路徑——ADR-XPLAT-006 §7 明文否決該方案；改為「掌舵者對三形態具名裁決」）；DEF-101-701 附記後半已達成。
- 未結列 55 → 52（結 3、新增 0）。

## 8. R114 證據檔 §8 訂正（訂正協議：不靜默覆寫）

R114 `CrossPlatform_R114_WakeChain_Review.md` §8 G3+G4 列原文逐字含「relay_seq/streak 入 relay 狀態塊、**reset_at 變更歸零**」與交付清單——經 R115 四方複審實測：①「reset_at 變更歸零」機制當時**不存在**（全樹零 reset_at↔relay 計數比對；實際只有 `_base_state` 重建的隱式歸零），宣稱先於實作＝鐵律四形態，R115 棒A 補齊實作（`apply_reset_at()` 兩站點）後宣稱方成立；② V-e2e 載具與 `_GOV_EXACT` 納管當時未交付且未申報（低報）。原文依訂正協議保留於 R114 檔不改，本節為權威訂正記載。結論（G1~G4 主體已落地）不變，但 §8 的完成度自報高於實況。

## 9. 收尾閘門（於本檔落檔後、commit 前重跑，數字見 R115_HANDOFF 附件）
