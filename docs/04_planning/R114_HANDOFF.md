# R114 交棒書（喚醒鏈 PRD 四方複審輪；Windows 11）

> 輪次性質：架構輪（開場量測：未結 53、帳本 150,509 bytes、守衛線 +0 ⇒ A/B 條件未觸發；
> R113 交棒書指定喚醒鏈 PRD 複審最優先）＋Windows 實機取證批（交棒書第 3 步）。
> 證據檔＝`docs/06_quality/CrossPlatform_R114_WakeChain_Review.md`（本輪唯一逐字證據載體）。
> 改動面前半＝PRD 修憲案＋帳本兩軌＋證據檔＋本檔（零生產碼）；掌舵者落款後同日解凍，
> **後半＝G1~G4 實作批落地**（生產碼＋測試，見 §一 7 與證據檔 §8）。

## 一、已驗證什麼（附實測）

1. **喚醒鏈 PRD 修憲案（v2.1.13）四方複審收斂**：一輪 Architect REJECT／SA AWC／SD AWC／QA REJECT
   ＝去重 13 blocking＋6 advisory（「§0 DEF-200-234 解鎖條件指向誤述」四方同時獨立命中）；
   修訂三批（13+6+追加→3 minor→SD Major）後二輪 4×AWC、SD 定點複核 **APPROVE**＝條件全閉合。
   檔案 149→180 行、Status 仍 **Proposed**（落款待掌舵者，見呈報單）。掌舵裁決要點與 13 筆清單
   ＝證據檔 §2。
2. **Windows 實機取證批**：DEF-200-063 與 DEF-200-147 解鎖條件全達成、**已結案移出外部軌**
   （外部軌 8→6）——headless hook `SessionStart… success`＋pythonw True＋哨兵
   `NextRunTime=2026/8/31 14:23:02` 值憑證＋liveness 170 passed＋132 subtests＋govwrite 矩陣
   12 passed＋24 subtests＋NTFS 探針；DEF-101-693 部分覆蓋（smoke PASS=12 FAIL=0 rc=0＋sync
   1 passed；bootstrap／integration 數列無實跑紀錄）⇒ 列保留、複查日更新 2026-08-31。證據檔 §3。
3. **新發現 DEF-200-238**（P2，open）：`govwrite_hit()` 對「尚不存在」的保護面目標，Windows
   realpath 無檔可還原大小寫 ⇒ 目錄前綴全大寫與 hook 新檔大寫副檔名兩種變體形態實測繞過
   （探針字面＝證據檔 §3.2 逐字塊；已存在檔變體全數命中）；三鏡獨立重證。立案證據＝證據檔 §4。
4. **DEF-200-212① 接線條件探針**：`current_round()`=100、嚴格接線 strict=3 假陽性／loose=0
   ＝「帳本時鐘前進」條件未熟，列維持 open（證據檔 §5）。
5. 文件閘門（帳本編修後實跑）：crossref rc=0（未結 54/167、外部軌 6、長債軌 7）；
   `check_archive_required` rc=0；`check_handoff_carriers` rc=0（109 份載體）。
6. 收尾全套閘門數字見本檔〈附件一〉（依 R96 教訓，最後一次全套在最後一次寫文件之後跑）。
7. **G1~G4 實作批三棒全部落地（2026-08-31 落款後同日）**，各棒獨立全套皆綠：
   G1 權限姿態（`settings.unattended.json`＋`resume_route.py`＋A-PRE 預檢＋V-a 測試；全套
   `Ran 3741` rc=0）→ G2 handback 可見性（`endurance_env` SSOT 對齊＋planner 後檢三值＋
   SessionStart 未讀偵測、hook ⓿ 瘦身免 repin；全套 `Ran 3747` rc=0）→ G3+G4 接力狀態機＋
   哨兵自癒（`relay_machine.py` 判定序 ③→④→②→①＋REFUSE 契約＋ENV 常數二枚＋fire 後重掛；
   全套 `Ran 3767` rc=0）。每棒皆做突變驗紅；逐棒明細＝證據檔 §8。

## 二、還沒做什麼（每項附載體與現查指令）

- 🔴 **G1~G4 實作批尚未過四方複審**（程式面已落地＝§一 7，但依 §6 品質流程未經 Architect/SA/
  SD/QA 獨立複審不得視為完成）——**下輪開場第一件事**；載體＝`DEF-200-234`／`DEF-200-235`／
  `DEF-200-236`（解鎖條件皆含「並過四方」）；現查
  `git grep -n "Status：Adopted" docs/04_planning/PRD_Amendment_R113_WakeChain_LastMile.md`
  ＋ `python -m pytest tools/tests/test_context_budget_guard.py -k "Relay or Handback or UnattendedPermission" -q`。
- **`AUTOSDD_RESUME_OFF`（User 層=1）尚未移除**＝自動續跑總閥仍關：刻意留待實作批過四方後
  才開（未經複審的煞車不上路）；移除後須做一次實彈演練（合成撞線→喚醒→接力→handback 可讀）。
  現查 `powershell -Command "[Environment]::GetEnvironmentVariable('AUTOSDD_RESUME_OFF','User')"`。
  根因取證＝證據檔 §7（本 session 撞線死亡、喚醒鏈四段全通、斷點即此閥＋G1~G4）。
- **DEF-200-238 修復尚未動工**：大小寫正規化＋紅綠自證＋假紅普查；設計上與 `_GOV_EXACT` 納管
  二檔（PRD v2.1.13 §3(a)）同批、治理面動作由收尾單人窗口做。現查
  `python tools/check_defect_log_crossref.py --unresolved-count`（238 仍列未結）＋證據檔 §4 探針。
- **DEF-200-239 修復尚未動工**：全套測試在真機種下自續排程 T-r95（孤兒本體已手動清除，但每跑
  一次全套就重種）；修法＝該測試族注入假 scheduler 後端＋回歸鎖。現查
  `Get-ScheduledTask -TaskName 'T-r95'`（跑過全套後仍查無＝已修）。
- **DEF-200-211（ADR-XPLAT-013 Phase 2 (b)(c)）仍未過四方批**；現查
  `python AutoClaude/tools/check_loc_budget.py --json`（policy_version 未含 (b)(c) 即仍未落）。
- **DEF-200-212① main() 接線尚未接**（續等帳本時鐘；本輪實測 clock=100、strict 3）；現查＝重跑
  證據檔 §5 探針；strict 紅綠現查 `python tools/check_handoff_carriers.py --self-test`。
- **DEF-101-693「22 步逐列覆核」尚未完成**：bootstrap 往返／dev_start／AutoClaude 子集／SDD
  ci-gate 雙軌仍未取得獨立 Windows 實跑紀錄；載體＝外部軌該列（複查日 2026-08-31）；現查
  `python tools/check_defect_log_crossref.py`（外部軌逐字列出 693）。
- **長債軌 14 天複查本輪尚未做**：2026-09-13 前須複查一次（DEF-101-886 P1 優先）；現查
  `python tools/check_defect_log_crossref.py`（逾期 warn 級自動出聲）。
- **v2.1.10／v2.1.11／v2.1.12 三批修憲仍未落款**（Proposed；PRD 修訂表現查有 v2.1.9 與
  v2.1.13、無此三批）；現查
  `git grep -n "Status：Proposed" docs/04_planning/PRD_Amendment_R112_WakeChain.md`。

## 三、下一步確切指令（下輪開場）

```powershell
# 1. 開場量測四件套（缺一不動工）
python tools/check_defect_log_crossref.py --unresolved-count
python tools/check_archive_required.py
python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines
python tools/session_resume_planner.py --pace
# 2. 第一件事＝G1~G4 實作批四方複審（審 diff：resume_route/relay_machine/endurance_env/
#    quota_policy_env/planner/settings.unattended.json/測試四類；施工圖＝v2.1.13）
# 3. 複審過後：(a) 治理批＝_GOV_EXACT 納管二檔＋DEF-200-238 大小寫正規化（收尾單人窗口）
#    (b) 移除 AUTOSDD_RESUME_OFF（User 層）＋實彈演練一次（合成撞線→喚醒→接力→handback）
# 4. 其餘：DEF-200-239 測試隔離修復／DEF-200-211 四方批／長債軌複查（2026-09-13 前）
```

## 四、禁止事項

不准 `--no-verify`；不准 `AUTOCLAUDE_SKIP_HOOKS=1`；不准調高任何棘輪常數換綠；G1~G4 實作以
v2.1.13 為唯一施工圖（2026-08-31 已落款；無頭專屬 settings 檔屬保護面成員，建立後即納管，檔名
見 PRD 案 §3(a)）；Windows 側禁用 Bash 工具（鐵律一）；不得為消 DEF-200-212 的 strict 假陽性
而改寫歷史文件或帳本時鐘輸入。

## 附件一：收尾閘門與帳本前後量測

- 開場（2026-08-31 14:07）：未結 **53**／166，外部軌 8、長債軌 7。
- 收尾：未結 **55**／168（新增 2＝DEF-200-238、DEF-200-239／結案 0——外部軌 063/147 不計
  分母；淨 +2，性質＝架構輪順帶取證的誠實立案，非結案輪失效訊號）；外部軌 **6**、長債軌 7。
- 淨額棘輪逃生口：本輪收尾以 `AUTOSDD_NET_RATCHET_OFF=1` 跑 crossref／commit——理由＝本輪為
  交棒書指定的架構輪＋實機取證批，取證過程誠實立案新缺陷（238＝govwrite 大小寫繞過；239＝
  全套測試在真機種下自續排程 T-r95），本質屬判準自述的「發現輪」形態；不立案才是砸溫度計。
  逃生口使用僅限本輪收尾窗口，下輪不繼承。
- 文件閘門：crossref rc=0／archive rc=0／carriers rc=0（帳本編修後實跑；收輪窗口重跑再驗）。
- 全套根層 unittest：本輪四次全套皆綠——落款前 `Ran 3735` rc=0、G1 後 `Ran 3741` rc=0、
  G2 後 `Ran 3747` rc=0、G3+G4 後 `Ran 3767` rc=0（皆乾淨環境；MIN_TESTS 同步重釘 3767）。
- 守衛線：89592→**90351**（G1 +141＋G2 +177 記 R113 同輪追加、G3+G4 +441 記 R114，
  皆走重釘儀式＋sha 接鏈；`--print-guard-lines` 收斂 +0、逐檔漂移 0）。
- <!-- guard-total:R114 --> **守衛線追記（v2.1.13 G3+G4 實作批 (c)+(d)，同日 2026-08-31 落款後解凍，寄居本輪號）：護欄層累積淨額＝ 89910 → 90351（+441）** —— G1 批 (a) +141、G2 批 (b) +177 兩者記入稽核痕跡 R113 列同輪追加；本次 G3+G4 批 +441 標號改用 R114（非回頭改寫 R113，理由見 `_GUARD_LINES_REPIN_LOG` 該列）。逐檔清單見 `docs/06_quality/CrossPlatform_R106_Scan_Findings.md` 的 R114 標記行。

## 呈報單（需掌舵者本人核准）

1. ~~喚醒鏈 PRD 修憲案落款~~ ✅ **已落款**（掌舵者 2026-08-31 互動裁決「落款生效」；落款程序
   同日執行：PRD v2.1 修訂表 v2.1.13 列＋修憲案 Status→Adopted＋帳本三列解鎖條件改寫）。
2. **v0.02/v0.03/v0.04 各 4 支假 SHA drift 檔（共 12 支）`git rm` 例外**（R113 呈報單原件，
   R114 已以 `git ls-files` 現查 12 支仍被追蹤；形態如
   `AISDLC_SDD/AISDLC_SDD_v0.02/build/reports/drift/COMMIT-sha-high.yaml`，另有 sha-low／
   sha-3rd／testsha-001 三名，×3 版目錄）：掌舵者 2026-08-31 裁決**下輪再議**，本呈報單
   原樣交棒。
