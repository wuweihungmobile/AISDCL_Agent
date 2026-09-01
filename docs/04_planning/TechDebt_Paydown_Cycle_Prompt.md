# 技術債總清償循環令（可重複投放；掌舵者裁決存證＋開工 Prompt 本體）

> 用途：掌舵者開新 session 時，將本檔〈Prompt 本體〉整段貼入即可；可重複投放直到
> 〈終止條件〉達成由執行者宣告 DONE。
> 裁決存證：以下 D1~D7 為掌舵者 2026-09-01 於 R115 收輪後以互動選項逐項裁決
>（載體＝R115 session 逐字稿；本檔為其權威轉錄），後續輪次直接執行、不得重問。

---

## Prompt 本體（自此行起整段複製投放）

# 技術債總清償循環令（RNN 自舉版；2026-09-01 掌舵者七項裁決已固化，勿再重問）
本指令可重複投放：每次開新 session 貼入即可，直到達成〈終止條件〉由你明確宣告 DONE。
與記憶／舊交棒書衝突時以本檔為準；本檔與帳本字面衝突時以帳本為準並回報。

## 0. 你的角色：舵手，不下場
不親寫代碼、不親審文件——派專職 sub-agent（Architect／SA／SD／QA／實作各司其職）。
遇不可預期狀況先自行分析、做當下最佳判斷推進；只有「毀滅性／不可逆」或「本檔未固化的
新裁決」才互動問我。pace band=notice 起改逐一 Agent（每 300s ≤4）；實作批可用
model: sonnet（R114/R115 實證可扛細規格）。

## 1. 掌舵者已裁決事項（2026-09-01 互動裁決，逐項固化——直接執行，不重問）
D1. 四份 Proposed 設計**全落款**：ADR-XPLAT-014／PRD_Amendment_R108_Pacing／
    PRD_Amendment_R108_BurnDown_Addendum／ADR-XPLAT-013_Phase2_Proposal_R108
    → Status 全改 Adopted。
D2. 三批修憲**全落款**：PRD v2.1.10／v2.1.11／v2.1.12 → 修訂表補列＋案檔 Status→Adopted
    （依 R110「未生效修憲不疊層」補齊落款程序；v2.1.10 與現行 --pace 實作重疊處＝落款後
    對齊帳，差異列缺陷）。
D3. DEF-101-886＝**檢查表形態**：CLAUDE.md 增「並行派工防互踩檢查表」條款（結案單線／
    修復棒串行／複審唯讀／收尾單人窗口四條現行慣例明文化）＋ tools/tests/ 對應規則鎖
    → 886 結案。
D4. DEF-200-212＝**授權豁免面工程解**：strict 的 3 筆歷史文件假陽性登記進具名豁免清單
    （shrink-only；不改寫歷史文件本身）→ strict 假陽性歸零 → 接 main() → 212 結案。
D5. R113/R114 守衛線分掛＝**追認**（掌舵者 2026-09-01 裁決即存證；證據檔記一筆，
    不重掛標號）。
D6. 目標＝**分階段**：落地輪（P0~P1）計「解鎖件落地數」不計淨減；結案輪（P2）目標
    每輪淨減 5~8。
D7. 平台＝**先 Windows 落地（P0~P2），再交棒 MAC 驗收輪（P3）**。

## 2. 開工必讀（依序）
docs/04_planning/ 最新一份 R*_HANDOFF.md（用 `ls` 現查最大號）→ 其指定證據檔 →
docs/06_quality/CrossPlatform_R115_Debt_Closure.md（本循環起點的裁決脈絡）→
三本帳（AutoSDD_Defect_Log／External_Blocked_Log／Structural_Debt_Log）。

## 3. 起手式（機械化，缺一不動工）
```powershell
python tools/check_defect_log_crossref.py --unresolved-count
python tools/check_archive_required.py
python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines
python tools/session_resume_planner.py --pace
```
另：開場若見 SessionStart 的 handback 未讀出聲（74403d0c…）＝R115 演練殘留，確認後
.ack＝G2 半格自然結案。請掌舵者以系統管理員 PowerShell 手動執行一次（R115 遺留，需提權）：
`Unregister-ScheduledTask -TaskName 'T-r95','T-f4b' -Confirm:$false`

## 4. 階段機（每次投放：起手式 → 讀最新交棒書 → 定位到未完成的最小階段續跑）
**P0 落款程序**（一次性，純文件＋帳本，收尾單人窗口做）：
  依 D1/D2 逐份落款（Status→Adopted＋PRD 修訂表補列）→ 改寫 234/236/211 解鎖條件的
  「Proposed」指向 → 結案 DEF-200-232（四檔 Status 落定即其解鎖條件）→ 文件閘門三支
  rc=0 → commit。
**P1 實作佇列**（嚴格依序、每項落地→過四方定點複審→結對應列→commit；一輪塞不下就
  交棒續投）：
  P1-1 ADR-XPLAT-013 Phase2 (b)(c) 減稅落地 → 結 DEF-200-211（小）
  P1-2 ADR-XPLAT-014 §4 巡邏 tick「主控死亡但 tasks/ 有活體」分支＋存活監測紅綠
       → 結 DEF-200-234
  P1-3 v2.1.12 §3-4 持久 notify_queue＋巡邏重投＋TTL＋delivered 憑證 → 結 DEF-200-236
       （R115 實彈已重現 notify_rc=-2 活體，驗收必含該情境重演轉綠）
  P1-4 D3 檢查表條款＋規則鎖 → 結 DEF-101-886
  P1-5 D4 豁免面＋strict 接 main() → 結 DEF-200-212
  P1-6 「平台專屬 skip 四層登記」收斂為單一 SSOT 派生（census 主表／MAX 表／凍結快照／
       skip_id_ledger M6——R115 漏一層紅一輪的結構解）
  P1-7 SD-4（RELAY_NEXT 排程失敗視同停止次態走 _rearm_after_stop）＋SD-8（settle_window
       外圈 try/except→清閂＋loud）＋SA-4 殘格（headless 窗口實跑 allow PowerShell(...)
       清單取證一次）
  P1-8 Pacing／BurnDown 落款後的實作差異盤點：與現行 --pace/--arm-endurance 實作逐條
       對齊，已被超越的條款在案檔加「已由實作超越」註記，未覆蓋的立列（誠實立案，不硬做）
**P2 Windows 驗證型結案**（單線逐筆，D6 目標淨減 5~8/輪）：
  挑解鎖條件＝「重跑指令綠即結」或 P2 級驗證型；每筆：現查解鎖條件→實測→結案編修
  （≤700 bytes、零輪號、指標指證據檔）→ crossref rc=0。
**P3 交棒 MAC 驗收輪**：P0~P2 完成後，交棒書明列 mac 積壓（235 mac launchd 重掛驗收半格／
  DEF-101-693 mac 面／darwin 剖面實機回填／useMacWin.md 對照），指示下一 session 在 MAC 開。

## 5. 品質與驗證（不可省）
每項實作：突變驗紅＋針對測試綠＋全套 `python tools/run_root_unittests.py` rc=0
（>10 分鐘用背景跑）。實作項過四方定點複審（一審全查、二審驗修復；sonnet 可）；
收斂標準＝四方無新 blocking。push 前本機全套綠；push 後必等雲端全部 completed
（等待用背景阻塞迴圈，不裸睡）；紅了先查是否本輪造成（❌ 不得套「長期紅」豁免；
paths 沒觸發的 workflow 用 workflow_dispatch 補驗）。

## 6. 教訓固化（R114＋R115，機械遵守）
- 新增平台專屬 skip＝**四層登記義務**（skip_group_policy 主表＋MAX 表＋test_skip_ceiling
  凍結快照＋skip_id_ledger 兩剖面 M6 id）——P1-6 完成前每次新增手動四層齊補
  （R115 漏一層紅一輪 ×4）。
- E501 存量債棘輪量 **EAW 顯示寬度**（中文佔 2 欄）；round-label-ok 豁免 token 必須與
  輪號**同行**。
- `.sh` 執行禁帶 bash `-n`（noexec 假綠）；讀 rc 不接管線；逃生口環境變數只掛單一指令。
- 守衛線款(11)：R115 已 -7 終止 streak；正淨額輪重新起算、連兩輪後下一輪必須 ≤0——
  實作批預先規劃搬遷抵銷（Guard_Line_History 體例）。款(12) 下一到期輪＝R117（cap→570）。
- 帳本「發現情境」欄零輪號（時鐘刻意凍結）；狀態欄 ≤700 bytes＝索引；交棒書 stale
  觸發字（尚未/仍未/仍缺…）＋現查指令動詞 code span＋不指名不存在路徑。
- 測試假 scheduler 後端 credential_key 一律 `sb.select().credential_key`（勿硬編平台家）；
  DEF-200-239 修復有姊妹 helper 前科——新增 tick 類測試 helper 必查是否已注入假後端。
- 淨額棘輪比「工作樹 vs HEAD」：先 commit 再跑全套自然轉綠。
- 帳本主檔編修後、最後一次全套之前，不再寫任何文件（R96）。

## 7. 每輪結尾必須輸出
1. 階段機現位（P0~P3 各項 done/塞不下交棒）；2. PRD/ADR 尚未完成清單；3. 帳本起訖未結
列數與淨額（＋主檔 bytes 變化）；4. commit＋push＋雲端 CI 結論表；5. 呈報單（僅本檔
未固化的新裁決件）；6. context 近滿則找乾淨點收輪並把「下次從 P 幾續跑」寫進交棒書。

## 8. 終止條件（達成即宣告 DONE，建議停止投放本 prompt）
P0~P1 八項全落地結案 ∧ 主帳本未結 ≤30 且其中零筆屬「本 prompt 已授權可解」形態
∧ mac 積壓已交棒 P3 輪。屆時輸出總結帳（起點 52 → 終點 N，逐階段淨減歸因）。

## 9. Token 資訊
（每次投放時貼上當時 /usage 快照）
