# R113 交棒書（結構性長債分軌輪；mac → 下輪 Windows 11）

> 輪次性質：結案輪（掌舵者指定觸發）＋輪中追加喚醒鏈 PRD 設計案（掌舵者 2026-08-31 直接指令）。
> 證據檔＝CrossPlatform_R113_Ledger_Closure.md（本輪唯一逐字證據載體：遷軌／噪音清理／喚醒鏈事件 §8／暫存清單 §5 全在）。

## 一、已驗證什麼（附實測）

1. 未結列：**61 → 54**（`--unresolved-count` 前後兩次實跑；遷軌 −7＋新增 0＝淨 −7。DEF-200-212 原擬 verify-only 結案，R3 複審 B1 揭露 ① main() 未接線＝部分完成，依 §4.7 改判回 open（交由R114），列上已載未接線事實與座標）
2. 全套根層 unittest：`Ran 3735 tests … OK (skipped=44)` rc=0（收尾窗口 2026-08-31 重跑 exit 0；skip census 44 全 platform 型、欠債 0、未標 0）
3. crossref：rc=0；已結列殘留待辦 warning 3 → 0；治理文件 78 份雙向核對；兩軌輸出行（外部 8＋長債 7）
4. `check_handoff_carriers.py --self-test`：16 PASS rc=0（DEF-200-212 ①**函式面**憑證；main() 接線刻意未做，見該列與證據檔 §3）
5. c1c2 鎖模組：160 支 OK rc=0（R113 稽核列 +140 < 上限 585；(113,585) 兌現＋重新武裝 (115,577) 步伐 8<10；Phase2 (113,[提案])）
6. 四方複審（R1 Architect／R2 Developer／R3 QA／R4 治理）：首輪 R2 APPROVE、R1/R3/R4 共 4 條 blocking（575↔577 轉錄錯、§8 缺 G4、212 過度宣稱、封印註解算術錯）；全修後複核**全員 APPROVE**（收斂第 2 輪，未觸 §8.1 停損線）

## 二、還沒做什麼（每項附載體與現查指令；本檔不新增帳本列）

- 🔴 **喚醒鏈最後一哩（G1~G4）實作尚未動工**：PRD_Amendment_R113_WakeChain_LastMile.md 僅 Proposed（修憲程序：四方＋掌舵者落款後才准動工），四缺口與程式座標見該檔 §1/§3；載體＝`DEF-200-234`／`DEF-200-235`／`DEF-200-236`；現查 `git grep -n "Status：Proposed" docs/04_planning/PRD_Amendment_R113_WakeChain_LastMile.md`（有命中＝仍未落款，動工即違規）。
- **DEF-200-212 ① main() 接線仍未接**：`ledger_def_ids(unresolved_only=True)` 已落、生產呼叫（`check_handoff_carriers.py:469`）刻意等帳本時鐘前進——現接生 3 筆假陽性（R3 複審 B1）；載體＝`DEF-200-212` 帳本列（交由R114）；strict 路徑紅綠現查 `python tools/check_handoff_carriers.py --self-test`。
- **DEF-200-211（ADR-XPLAT-013 Phase 2 (b)(c)）尚未動工**：[提案] 已入 `_PHASE2_REVIEW_LOG`（113 列），四方批（與 207 同場）過了才動；載體＝`DEF-200-211` 帳本列；現查 `python AutoClaude/tools/check_loc_budget.py --json`（policy_version 仍為 v3-assertion-only+sd08-special＝(b)(c) 還沒落）。
- **Windows 實機取證批仍未排上**：實機族 6 筆（playbook 附錄 B ②）＋外部軌 3 筆複查（693/063/147，複查日 2026-08-30）需 Windows 真機合批；載體＝外部軌該三列；現查 `python tools/check_defect_log_crossref.py --unresolved-count`（外部軌 8 筆行逐字列 ID）。
- **MIN_TESTS=3735 屬中途值**：Windows 輪若增測試而仍未同行重釘＋回填即紅；現查 `git grep -n "MIN_TESTS = " tools/run_root_unittests.py` 與 `python tools/sync_onboarding_baselines.py --check`。
- **長債軌 14 天複查時鐘**：2026-09-13 前須複查一次（DEF-101-886 為 P1 建議優先）；逾期自動出聲現查 `python tools/check_defect_log_crossref.py`（warn 級）。

## 三、下一步確切指令（Windows 11 輪開場）

```powershell
# 1. 開場量測四件套（playbook §1.2，缺一不動工）
python tools/check_defect_log_crossref.py --unresolved-count
python tools/check_archive_required.py
python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines
python tools/session_resume_planner.py --pace
# 2. 喚醒鏈 PRD 四方複審（過了才准實作 G1~G4）：
#    docs/04_planning/PRD_Amendment_R113_WakeChain_LastMile.md
# 3. Windows 實機取證批：外部軌 693/063/147 解鎖條件逐字跑；哨兵 schtasks 對照 mac launchd
```

## 四、禁止事項

不准 `--no-verify`；不准 `AUTOCLAUDE_SKIP_HOOKS=1`；不准調高任何棘輪常數換綠；PRD 修憲未過四方前不准動工 G1~G4 實作；Windows 側禁用 Bash 工具（鐵律一）。

## 附件一：帳本前後量測

- 開場（2026-08-30 21:58）：未結 61／165，外部軌 8
- 收尾（2026-08-31）：未結 54／165，外部軌 8＋長債軌 7（皆不計分母）
- 新增 0／結案 7／淨額 **−7**（連續兩輪淨額 <0，playbook 失效訊號未觸發）

## 附件二：護欄層淨額落款

<!-- guard-total:R113 --> 89452 → 89910（+458）。重釘清單：test_check_defect_log_crossref.py 3794→3906、test_defect_id_reference_integrity.py 274→281、test_adr_xplat001_c1c2_lock.py 6391→6412；MIN_TESTS 3631→3735 同行重釘；OVERSIZE 豁免 44→43、excess 34712→27682→27657（兩段皆 --repin-oversize 機械收緊＋rotation 封印同步 _SEAL_TOTAL_MIN_LEN 39→42）。同輪追加（v2.1.13 G1 實作批 (a)，2026-08-31）：test_context_budget_guard.py 8178→8307、test_adr_xplat001_c1c2_lock.py 6412→6424（稽核列＋rewrite ledger 接鏈＋凍結前綴延伸 82→83）。同輪追加（v2.1.13 G2 實作批 (b)，2026-08-31）：test_context_budget_guard.py 8307→8468（HandbackVisibilityTest＋HandbackSessionStartAnnounceTest 六格＋_isolated_env 補 AUTOSDD_HANDBACK_DIR 隔離）、test_adr_xplat001_c1c2_lock.py 6424→6440（稽核列＋rewrite ledger 接鏈 DEF-200-236＋凍結前綴延伸 83→84）；MIN_TESTS 3741→3747 同行重釘。

## 附件三：輪內暫存清單裁決

30 筆逐筆留痕＝證據檔 §5（含四方複審 advisory 補登 #24-30；當場修掉未立列 2 筆、併既有列 1 筆、本輪處置 2 筆、複審改判 1 筆、呈報單 1 筆、其餘 advisory 記錄）。

## 呈報單（需掌舵者本人核准）

1. **v0.02/v0.03/v0.04 各 4 支假 SHA drift 檔（共 12 支）仍被 git 追蹤**（R78 Debt_Audit :122 早有記載、帳外）：申請 Copy-on-Evolve 例外核准 `git rm`（同 DEF-101-338 判例，純刪測試產物）；核准後 <30 分鐘可修。
2. **喚醒鏈 PRD 修憲案**（PRD_Amendment_R113_WakeChain_LastMile.md，批次序 v2.1.13）：請於 Windows 輪召集四方複審＋落款。

## 喚醒鏈事件一頁摘要（回應掌舵者 2026-08-31 質問）

mac 喚醒鏈「偵測→武裝→喚醒→續跑」四段全通（首次實戰全通，時間線與逐字證據＝證據檔 §8）；敗在最後一哩四缺口 G1 權限牆／G2 交接不可見／G3 無自循環／G4 哨兵不自癒，三個機械根因已釘到程式碼座標（choose_resume_route :1120 無 --permission-mode；resume 終局 :1303-1315 fire-once；主 settings 無 permissions 鍵）。設計全文＝PRD 案 §3（含接力狀態機與出廠常數），驗收 11 條全機械（§4），Windows 輪落地。本輪已重新武裝哨兵（憑證 `launchctl print rc=0`＋interval 900s＋plist 持久化）。
