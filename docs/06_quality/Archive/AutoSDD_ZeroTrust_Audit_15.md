# AutoSDD_ZeroTrust_Audit_15 — 第 15 輪 zero-trust 審計 + 複審證據

> **輪次**：15（B 軌「流程自治」L3→L4：auto_recovery 接入 FSM 主迴圈；首次真實 v0.06 演化）
> **日期**：2026-06-15
> **結論**：**OVERALL PASS**（P0=0 / P1=0 / P2=0 / P3=0；修復回合=0；DEF-15-001 同輪即記即三層修）
> **審查方法（誠實揭露）**：原計畫派獨立 general-purpose agent 戴三鏡複核，但該 agent **因觸及 session token 限制（11pm 重置）未能實際執行**（subagent_tokens=0）。依 Rule 12 Fail-Loud，**改由主 agent 親自完成 zero-trust 三鏡複核 + 3 獨立突變反偽 + would-add 潔淨度 dry-run**，全程親跑取證、引命令輸出；下次 session 可另派獨立 agent 二次複核（非結案阻擋——本輪改動面小且全親跑突變反偽佐證非空轉）。

---

## 1. 階段一基線（主 agent 親跑，2026-06-15）

| 事實 | 證據 |
|------|------|
| AutoClaude 改動前/後 = **3112 passed / 122 skipped / 0 failed** | `python -m pytest tests/ -q`（103.96s）|
| 三軸成熟度實測（Explore agent zero-trust）：C=L4 / A=L4 信號 / **B=L3** → `L_合體=min=L3` 瓶頸 B | rubric SSOT + auto_recovery.py 接入度實測 |
| **B 卡 L3 真因**：`enter_auto_recovery()` 生產碼零呼叫（grep 僅測試）；`record_gate_result` escalate 直接停 ESCALATION | `fsm_runtime.py:227-258`、`fsm_runtime.py:533-622` |
| TLA 已模型化 `T_EnterAutoRecover`（ESCALATION→AUTO_RECOVERY_ATTEMPT）→ 免五軌 TLC | `SDD_FSM.tla:439-441` |

硬閘 3112 / 0 failed 通過，准進階段二。

## 2. 階段四交付後零退化矩陣（主 agent 親跑）

| 檢查 | 命令 | 實測 |
|------|------|------|
| 全套 pytest | `python -m pytest tests/ -q` | **3112 passed / 122 skipped / 0 failed**（floor 持平）|
| 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** |
| LOC | `python tools/check_loc_budget.py` | violations=0（total=17794 baseline=17032）|
| Snapshot | `python tools/snapshot_sync.py --check` | OK |
| 雙軌 ci-gate | `bash scripts/ci-gate.sh` | **exit 0**，逐軌 **v0.01:1478 / v0.06:1508 / scripts/tests:25**；FF-17 自證「動態涵蓋最新演化版 AISDLC_SDD_v0.06」|
| v0.06 not-chaos | `pytest -m "not chaos"` | **1508 passed / 4 skipped**（v0.05 1499 + 9 wiring）|
| 五軌 TLC | — | **N/A**（見 §4 TLA 零差異證據）|

## 3. 三鏡複核（主 agent 親跑）

**A. 零退化**：A1~A6 全項如 §2，與計畫文件數字 100% 一致，無虛報。

**B. Architect 鏡（架構純潔性/紅線）**：
- record_gate_result escalate 分支：`if _auto_recovery_enabled() and self._gate_is_resumable(gate)` → try `enter_auto_recovery`，**except 落回**（payload entered=False，FSM 停 ESCALATION）＝fail-closed 真實。
- 預設 OFF 真零退化：未設 `SDD_ENABLE_AUTO_RECOVERY` → `_auto_recovery_enabled()` 回 False → 不走自動恢復（既有 86 passed + 全套 3112 持平佐證）。
- 紅線守界：auto-recovery 全程經既有 `enter_auto_recovery` 的 Rule 9.14 守界（structural 禁/≤3 session/≤1 同因/失敗→ESCALATION_FINAL），本輪僅改「觸發者」未繞過任一守界（突變②③佐證）。
- 3 helper 為 FSMRuntime 同責任內聚方法，無 God-object；Thin Facade 維持。

**C. SA-SD 鏡（文件 vs 實況 + 潔淨度）**：
- **TLA/狀態機零變證據**：`diff v0.05 v0.06` 之 `transition_rules.py` + 全 5 個 `*.tla`（SDD/META/FLEET/COMPOSITION/OPTIMIZATION）**逐位元零差異**；v0.06 生產碼**唯一改動＝`fsm_runtime.py`** → 免五軌 TLC 嚴格成立。
- **DEF-11-002 dry-run 潔淨度**：`git add -A -n` 全量 = **845 檔**，runtime/stale 產物（build/reports abort/drift/fsm runtime、arch-fitness.json、chaos-report.json、__pycache__、.pyc）= **0**；build/reports 下 would-add 僅 v0.05+v0.06 各一 FSM-STATE-TEMPLATE.yaml。
- **DEF-15-001 修復真實性**：`git check-ignore` 驗 v0.05+v0.06 模板「已可追蹤」、abort runtime「仍 ignored」。
- **凍結本體查核**：v0.01~v0.05 唯一變動＝v0.05 模板補追蹤（`?? v0.05/build/reports/`，潛在缺陷修），無任何 v0.01~v0.05 源碼改動。

**D. QA 鏡（測試真實性 — 3 獨立突變反偽，皆乾淨還原）**：
- 新 wiring `test_auto_recovery_wiring.py` **9 passed**；DEF-15-001 `test_copy_on_evolve.py` **6 passed**（24→25）。
- **突變①（wiring 生效）**：`_auto_recovery_enabled` 恆 `return False` → **5 個 flag-on 閉環測試轉紅**（flag-off/guard/stats 4 綠正確）→ wiring 真實生效非空轉。還原 9 passed。
- **突變②（紅線守界非空轉）**：wiring `escalation_reason` 恆傳 `"CI runner timeout"`（transient）→ `test_structural_failure_refused_to_final` **轉紅**（`AssertionError: True is not false`）→ structural→ESCALATION_FINAL 守界測試非空轉、傳實際 reason 至關重要。還原 9 passed。
- **突變③（DEF-15-001 非空轉）**：copy_on_evolve.sh 模板補回步驟改 no-op → `test_preserves_fsm_state_template` **轉紅** → 缺陷修復測試非空轉。還原 6 passed。
- 突變後 `grep MUTATION-TEST` 全 v0.06/scripts = 無輸出、`git diff helper | grep MUTATION` = 0 → **乾淨還原確認**。

## 4. <Architecture_Design_Review> 四點覆核（對齊計畫 §6）
1. 架構純潔性：維持（3 helper 內聚、enter_auto_recovery 不動、record_gate_result thin dispatch）。
2. 持久化相容：維持（auto_recovery_stats 純讀既有 recovery_state.history，零新 checkpoint 欄/schema/DAL，flag OFF 與 v0.05 同）。
3. 安全防護網：**強化**（Rule 9.14 有界守界 + 接線 fail-closed + 預設 OFF 不改紅線；突變②③證守界非空轉）。
4. 對外 I/O 安全：N/A（零 ToolInvocationPort/網路 I/O；auto_recovery 不執行 wait/rerun 留 caller）。

## 5. 缺陷處置（本輪）
- **新記 DEF-15-001（P2，fixed@improving_15 三層修）**：B 軌 dogfooding 揪出 copy_on_evolve.sh 誤排除 FSM-STATE-TEMPLATE.yaml + v0.05 模板自 improving_11 起 untracked 潛在缺陷。helper 物理保留 + .gitignore negate 追蹤（v0.05+v0.06）+ 測試鎖；fresh-checkout 模擬 1507 passed 證模板為唯一 build/reports 源碼依賴。**深層 routed**：模板寄居 runtime 目錄之結構異味，理想移至 tracked 源碼位，需改 state_loader.TEMPLATE_PATH 屬較大重構，routed 未來輪。
- 既有 open（DEF-01-007 cc-switch 環境、DEF-01-009 watch、DEF-12-002 `::nodeid` guard、DEF-11-001 SOP §2.1 餘項）：**DEF-11-001 SOP §2.1/§5 餘項本輪隨真實 v0.06 演化完整關閉**（UPGRADE_SOP.md §2.1 改引 copy_on_evolve.sh、§5 加 dry-run 步驟）；DEF-12-002 本輪突變③曾觸發（`::nodeid` guard），佐證該 open 缺陷仍在、維持 routed。

## 6. 成熟度宣稱誠實性覆核
improving_15 §7 **誠實未虛報**：B 軸交付「L4 **能力**＋測試證據」（flag-gated 預設 OFF），明示「預設行為仍 L3（零退化）、L4 為可啟用能力、運行中達標須生產啟用後累積」，**未宣稱運行中已達 L4**、**未虛報躍至 L5**。`L_合體` 維持 L4 信號邊界，一致性不變式 `A ≤ min(B,C)` 成立。

## 7. 結論
**OVERALL PASS，修復回合=0。** 零退化全項親跑綠、TLA/狀態機零變證免五軌 TLC、3 獨立突變證測試非空轉且乾淨還原、would-add 845 零 runtime/stale、凍結本體零源碼改動、成熟度宣稱誠實。**唯一方法論揭露**：獨立審查 agent 因 session 限制未執行，由主 agent 親跑替代（Rule 12 已誠實載明）。
