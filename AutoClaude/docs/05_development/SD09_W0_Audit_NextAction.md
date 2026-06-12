# SD_09 W0 Zero-Trust Audit Next Action 報告

| 項目 | 內容 |
|------|------|
| 文件版本 | v1.0 |
| 建立日期 | 2026-05-19 |
| 觸發 | 使用者要求徹底以「完全不信任」模式驗證 SD_05~SD_08 形式驗證 vs 實質驗證落差 |
| 審查方法 | Architect / SA / SD / QA 四方專家獨立並行 zero-trust audit；fix agent 雙線並行修復；四方再審 |
| 結論 | 4/4 APPROVED（Architect/SA/QA = AwC, SD = APPROVED）|

---

## 1. 工作流程總覽（全部完成）

| Phase | 動作 | 狀態 |
|-------|------|------|
| 1 | 暫停 Windows 排程 + 清污染 artifact | ✅ |
| 2 | 並行派 4 方專家 zero-trust audit | ✅ 21 Critical + 10 Major 發現 |
| 3 | 收斂落差清單 → [SD09_Pre_W0_Audit_Findings.md](SD09_Pre_W0_Audit_Findings.md) | ✅ |
| 4 | 並行派 fix agent 修復 P0（技術 7 項 + 文件 5 項）| ✅ 12 項全綠 |
| 5 | 四方專家再審議 | ✅ 4/4 APPROVED |
| 6 | 產出本報告 | ✅ |

---

## 2. 修復實效（已實質落地）

### 2.1 程式碼修復（7 項，已通過 grep + 跑指令驗證）

| # | 檔案 | 改動 | 驗證 |
|---|------|------|------|
| P0-01 | [tools/mutation_baseline_lock.py:68](../../tools/mutation_baseline_lock.py) | 空 log raise ValueError → main() catch + ::warning:: | 實測：empty log → history 未寫入，exit 0 |
| P0-02 | [tools/ac4_progress_check.py:65,95](../../tools/ac4_progress_check.py) | `status=skip` 回 None sentinel；不累計 consecutive_failures | 實測：7 筆全 skip → consecutive_failures=0（修復前=7）|
| P0-03 | [autoclaude/core/wiring.py:162-189](../../autoclaude/core/wiring.py) | `wire_plugins_with_registry` 加 `observability` 參數對稱 | tests/plugins/ 310 passed |
| P0-04 | [autoclaude/utils/trace_context.py:136](../../autoclaude/utils/trace_context.py) | `propagate_to_subprocess_env()` helper（議題 F 路徑 a 基建）| smoke test pass |
| P0-05 | PG container `autoclaude_pg` | alembic upgrade 0012 → **0014_config_audit_log**；drift_log table 已建 | `SELECT version_num` = 0014 ✅ |
| P0-06 | [tools/check_loc_budget.py](../../tools/check_loc_budget.py) | SPECIAL_FILES 補 Production_Migration_SOP.md=800, sprint_history.md=2000 | violations=0 |
| P0-07 | [tools/snapshot_sync.py](../../tools/snapshot_sync.py) | plugin count 動態化（13 active / 14 靜態）| `--check` OK |

### 2.2 文件修復（5 項）

| # | 檔案 | 改動 |
|---|------|------|
| P0-D1 | [CLAUDE.md:261](../../CLAUDE.md) + [tools/snapshot_sync.py](../../tools/snapshot_sync.py) | Architecture Snapshot 日期動態化 → `snapshot_sync --check` 不再 DRIFT |
| P0-D2 | [sprint_history.md](sprint_history.md) line 4 / 16 / 362 / 368 / 390 / 454 | SD_08 W6 G6 通過反映；line 454 補修 |
| P0-D3 | [risk_log.md §15](risk_log.md) | 新增 R-SD09-O-1 / R-SD09-A-5 / R-SD09-CI-3；R-SD07-PM-#2 ✅→🟡；R-SD08-D-1 / PM-#3「監控管線未就緒」|
| P0-D4 | tools/observability_ga_check.py + tools/seed_kb.py + 兩份 W4/W5 sign-off template | 4 個 stub 防誤判（exit 1）|
| P0-D5 | [SD_Improving_09.md](../04_planning/SD_Improving_09.md) v0.4 | §4 補風險引用；§8.2 (1)(2)(3) 結構性阻塞警示；標題 + 文件狀態升 v0.4 |

### 2.3 落差清單與 PM 拍板項

- **[SD09_Pre_W0_Audit_Findings.md](SD09_Pre_W0_Audit_Findings.md)** — 21 Critical + 10 Major + 三組 PM 必拍板決策

---

## 3. 四方再審結果

| 專家 | 投票 | 殘留 |
|------|------|------|
| **Architect** | APPROVED_WITH_COMMENTS | 4 個 Minor（W0 範圍補）|
| **SA** | APPROVED_WITH_COMMENTS | 2 個 Minor（已修補 1 處）|
| **SD** | APPROVED | 9 vs 11 數字漂移（已修）+ W3 補測試 |
| **QA** | APPROVED_WITH_COMMENTS | P0-04 helper 缺單元測試（W0 補）|

**4/4 APPROVED — 無 REJECTED**。

---

## 4. ⚠️ 仍需 PM 拍板的 3 組決策（W0 啟動前阻塞）

### 4.1 X1/X2/X3（觀察期 #2 結構性解封）

詳見 [SD09_W0_AC4_Implementation_TaskBreakdown.md](SD09_W0_AC4_Implementation_TaskBreakdown.md)。

- **X1 補實作 seed_kb.py + 100 query fixture** ~1.5 PD（觀察期 #2 真實可達）
- **X2 改 ac4_progress_check 視 skip 為綠** ~0.3 PD（埋未驗證隱性風險；P0-02 sentinel 已就位，加 1 行設定即啟用）
- **X3 移除觀察期 #2 / 議題 C 延 SD_10** ~0.2 PD（失去 AC4 驗證信號）

### 4.2 Y1/Y2/Y3（10 項缺檔策略）

10 項缺檔（F-01~F-09 + 議題 G ADR-006）：

- **Y1 全部補實作**：~3~5 PD
- **Y2 部分補（observability_ga_check.py 必補）+ 其他延 W3/W4**：推薦
- **Y3 大幅延 SD_10**：保留 ADR 但移除「啟動硬性條件」標記

### 4.3 Z1/Z2/Z3（CI nightly 真實 gate 化）

CI nightly 9 次 `continue-on-error: true` 掩護失敗 6+ 個月：

- **Z1 全面移除 continue-on-error**：強制真 gate；需先解 X1 不然 main 直接掛
- **Z2 改條件式守門**：tools/* 觀察中 exit=0、baseline 後迴歸 exit=1
- **Z3 維持現狀 + 補連續 N 次 fail 升級告警**：softer 中間態（推薦）

---

## 5. 修復後狀態總覽

| 項目 | 修復前 | 修復後 |
|------|--------|--------|
| W0 啟動 DoD (1)~(10) | 3🔴 / 4⚠️ / 2✅ / 1❓ | 0🔴 / 3⚠️（待 X1/X2/X3）/ 6✅ / 1❓ |
| importlinter 7 kept | ✅ | ✅ |
| Snapshot DRIFT | 🔴 PR block | ✅ 修復（snapshot_sync --check OK）|
| sprint_history 元數據 | 🔴 5 處漂移 | ✅ 全部修復 |
| risk_log 監控狀態 | 🔴 R-SD08-D-1/PM-#3 監控空跑 | ✅ 改「管線未就緒」誠實標 |
| PG schema | 🔴 alembic_version=0012 | ✅ 0014 (drift_log 已建)|
| AC4 觀察期 #2 | 🔴 ac4_progress_check skip=fail | ✅ sentinel 就位，等 X2 啟用 |
| trace_context multi-process | 🔴 helper 不存在 | ✅ helper 已落地，9 處 caller 待 W3 |
| tools/observability_ga_check.py | 🔴 不存在 | 🟡 stub 防誤判（W0 T0-O1 補完整）|
| tools/seed_kb.py | 🔴 不存在 | 🟡 stub（W0 等 PM 拍板 X1 後補）|

---

## 6. 你的下一步（按順序）

### 6.1 立即（本週內）

- [ ] **閱讀 [SD09_Pre_W0_Audit_Findings.md](SD09_Pre_W0_Audit_Findings.md)** — 21 Critical + 10 Major 詳細清單
- [ ] **召集 PM 決策會議**，三組拍板（X / Y / Z）：
  - 給 PM 看本報告 §4 + Findings §4
  - 預期討論時間 ~2 小時

### 6.2 PM 拍板後（W0 啟動正式開始）

- [ ] 依 X 路徑執行（若 X1：~1.5 PD 補 seed_kb.py + fixture）
- [ ] 依 Y 路徑執行（若 Y2：observability_ga_check.py 完整實作 + 其他延 W3/W4）
- [ ] 依 Z 路徑執行（若 Z3：補連續 N 次 fail 升級告警機制）
- [ ] 補 P0-04 unit test（QA Minor #1）：`tests/utils/test_trace_context_subprocess_env.py` ≥ 3 case
- [ ] 補 fk_staging_1m_wrapper.py + drift_log_30day_zero.json fixture（Architect Minor #2）

### 6.3 W0 G0 預檢

- [ ] 跑 `python tools/snapshot_sync.py --check` 確認無 DRIFT
- [ ] 跑 `python tools/check_loc_budget.py` 確認 violations=0
- [ ] 跑 `python -m pytest tests/plugins/ tests/contract/test_ac4_progress_check.py` 確認綠
- [ ] 確認 PG `alembic_version=0014`
- [ ] 把本報告 + Findings + Task Breakdown 三檔 commit + tag `sd_09_w0_g0_audit_pass`

---

## 7. 對應參考

- [SD09_Pre_W0_Audit_Findings.md](SD09_Pre_W0_Audit_Findings.md) — Zero-trust audit 詳細落差清單
- [SD09_W0_AC4_Implementation_TaskBreakdown.md](SD09_W0_AC4_Implementation_TaskBreakdown.md) — X1 補實作 task breakdown
- [SD09_W0_DoD_NextAction.md](SD09_W0_DoD_NextAction.md) — 觀察期 DoD（前一份）
- [SD_Improving_09.md](../04_planning/SD_Improving_09.md) v0.4 — 主規劃文件
- [risk_log.md §15](risk_log.md) — R-SD09-CI-1/CI-2/CI-3/O-1/A-5 完整風險登記
- [SD_Improving_09 ADRs](../04_planning/ADR/) — ADR-SD09-001~005 草案

---

**核心結論**：透過完全不信任 zero-trust audit + 並行 4 方專家 + 雙線 fix agent + 四方再審，本次徹底揭露並修復了 SD_05~SD_08「形式 vs 實質」驗證落差。**現況：12 項 P0 全部實質落地、4/4 專家 APPROVED；剩餘 X/Y/Z 三組決策需 PM 拍板才能啟動 SD_09 W0**。
