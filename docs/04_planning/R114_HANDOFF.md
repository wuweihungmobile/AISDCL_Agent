# R114 交棒書（喚醒鏈 PRD 四方複審輪；Windows 11）

> 輪次性質：架構輪（開場量測：未結 53、帳本 150,509 bytes、守衛線 +0 ⇒ A/B 條件未觸發；
> R113 交棒書指定喚醒鏈 PRD 複審最優先）＋Windows 實機取證批（交棒書第 3 步）。
> 證據檔＝`docs/06_quality/CrossPlatform_R114_WakeChain_Review.md`（本輪唯一逐字證據載體）。
> 本輪**零生產碼改動**：改動面＝PRD 修憲案＋帳本兩軌＋證據檔＋本檔。

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

## 二、還沒做什麼（每項附載體與現查指令）

- 🔴 **喚醒鏈 G1~G4 實作仍零行**：PRD 案已過四方但**未落款**（修憲程序：掌舵者落款後才准動工）。
  載體＝`DEF-200-234`／`DEF-200-235`／`DEF-200-236`；現查
  `git grep -n "Status：Proposed" docs/04_planning/PRD_Amendment_R113_WakeChain_LastMile.md`
  （有命中＝仍未落款，動工即違規）。
- **DEF-200-238 修復未動工**：大小寫正規化＋紅綠自證＋假紅普查；設計上與 `_GOV_EXACT` 納管二檔
  （PRD v2.1.13 §3(a)）同批、治理面動作由收尾單人窗口做。現查＝跑證據檔 §4 之可重跑探針。
- **DEF-200-211（ADR-XPLAT-013 Phase 2 (b)(c)）**：仍待四方批；現查
  `python AutoClaude/tools/check_loc_budget.py --json`（policy_version 未含 (b)(c) 即未落）。
- **DEF-200-212① main() 接線**：續等帳本時鐘（本輪實測 clock=100、strict 3）；現查＝重跑證據檔
  §5 探針；strict 紅綠現查 `python tools/check_handoff_carriers.py --self-test`。
- **DEF-101-693「22 步逐列覆核」缺口列**：bootstrap 往返／dev_start／AutoClaude 子集／SDD
  ci-gate 雙軌無獨立 Windows 實跑紀錄；載體＝外部軌該列（複查日 2026-08-31）。
- **長債軌 14 天複查時鐘**：2026-09-13 前須複查（DEF-101-886 P1 優先）；現查
  `python tools/check_defect_log_crossref.py`（逾期 warn 級自動出聲）。
- **v2.1.10／v2.1.11／v2.1.12 三批修憲仍 Proposed**（PRD 修訂表現查止於 v2.1.9）。

## 三、下一步確切指令（下輪開場）

```powershell
# 1. 開場量測四件套（缺一不動工）
python tools/check_defect_log_crossref.py --unresolved-count
python tools/check_archive_required.py
python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines
python tools/session_resume_planner.py --pace
# 2. 若掌舵者已落款 v2.1.13：依 PRD 案 §5 順序動工（(a)→(b)→(c)，(d) 並行；
#    DEF-200-238 正規化與 _GOV_EXACT 納管二檔同批，由收尾單人窗口做治理面）
# 3. 若未落款：催辦呈報單；改跑 DEF-200-211 四方批或長債軌複查（2026-09-13 前）
```

## 四、禁止事項

不准 `--no-verify`；不准 `AUTOCLAUDE_SKIP_HOOKS=1`；不准調高任何棘輪常數換綠；PRD 修憲未落款
前不准動工 G1~G4 實作（含無頭專屬 settings 檔的建立——該檔屬落款後保護面成員，檔名見 PRD 案
§3(a)）；Windows 側禁用 Bash 工具（鐵律一）；不得為消 DEF-200-212 的 strict 假陽性而改寫歷史
文件或帳本時鐘輸入。

## 附件一：收尾閘門與帳本前後量測

- 開場（2026-08-31 14:07）：未結 **53**／166，外部軌 8、長債軌 7。
- 收尾：未結 **54**／167（新增 1＝DEF-200-238／結案 0——外部軌 063/147 不計分母；淨 +1，
  性質＝架構輪順帶取證的誠實立案，非結案輪失效訊號）；外部軌 **6**、長債軌 7。
- 淨額棘輪逃生口：本輪收尾以 `AUTOSDD_NET_RATCHET_OFF=1` 跑 crossref——理由＝本輪為交棒書
  指定的架構輪＋實機取證批，取證過程誠實立案新缺陷（DEF-200-238），本質屬判準自述的
  「發現輪」形態；不立案才是砸溫度計。逃生口使用僅限本輪收尾窗口，下輪不繼承。
- 文件閘門：crossref rc=0／archive rc=0／carriers rc=0（帳本編修後實跑）。
- 全套根層 unittest（最後一次寫文件之後跑）：結果由收尾窗口回填於 commit 訊息與輪末回報
  （本檔不預寫未跑出的數字）。
- 守衛線：89592→89592（+0，本輪零生產碼/鎖檔改動）。

## 呈報單（需掌舵者本人核准）

1. **喚醒鏈 PRD 修憲案落款**（`PRD_Amendment_R113_WakeChain_LastMile.md`，批次序 v2.1.13）：
   四方複審已收斂（一輪 2×REJECT+2×AWC → 修訂三批 → 二輪 4×AWC → SD 定點 APPROVE）。
   落款後 G1~G4 實作批才准動工。
2. **v0.02/v0.03/v0.04 各 4 支假 SHA drift 檔（共 12 支）`git rm` 例外**（R113 呈報單原件，
   R114 已以 `git ls-files` 現查 12 支仍被追蹤；形態如
   `AISDLC_SDD/AISDLC_SDD_v0.02/build/reports/drift/COMMIT-sha-high.yaml`，另有 sha-low／
   sha-3rd／testsha-001 三名，×3 版目錄）：Copy-on-Evolve 例外核准後 <30 分鐘可清。
