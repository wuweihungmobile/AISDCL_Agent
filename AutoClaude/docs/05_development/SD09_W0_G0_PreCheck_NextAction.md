# SD_09 W0 G0 簽核前置檢查 — NextAction（2026-06-23）

> 本檔為 G0 live 狀態 SSOT（SD_Improving_09.md §8.1/§8.2 為 2026-05-20 凍結快照）。
> 實測來源：`tools/g0_gate_check.ps1`（2026-06-23T21:56）+ Windows Task Scheduler 事件記錄。

---

## 一、schtasks 漏跑根因（已查證 + 已備修復）

**漏跑日 = 2026-06-19、06-20、06-21（連 3 天）**，事件記錄鐵證：

| 日期 | 事件 | 判讀 |
|------|------|------|
| 06-13~18、06-22~23 | Event 102/201 rc=0 | 正常每日 02:00 完成 |
| 06-19、06-20 | **完全無事件** | 02:00 機器**全關機**；`WakeToRun` 只能喚醒睡眠/休眠，無法喚醒關機 |
| 06-21 21:53 | **Event 153**「已錯過排程，請考慮使用設定選項在錯過排程時啟動工作」 | 傍晚開機，排程器偵測錯過，但 `StartWhenAvailable=false` → **不補跑** |

**根因兩層**：① 機器 02:00 處於關機（非睡眠）；② `StartWhenAvailable=false` 導致開機後不補跑。
（`DisallowStartIfOnBatteries=true` 非本次主因——電池阻擋仍會留事件，但 19/20 無任何事件＝關機；列為潛在風險一併修。）

**修復（需系統管理員權限，本 session 非提權無法套用——請在提權 PowerShell 執行一次）**：

```powershell
$t = Get-ScheduledTask -TaskName "AutoClaude_Nightly"
$t.Settings.StartWhenAvailable = $true            # 開機後補跑錯過的排程（Windows 事件 153 自身建議）
$t.Settings.DisallowStartIfOnBatteries = $false   # 筆電電池時不擋補跑
Set-ScheduledTask -TaskName "AutoClaude_Nightly" -Settings $t.Settings
```

驗證：`(Get-ScheduledTask AutoClaude_Nightly).Settings | Select StartWhenAvailable,DisallowStartIfOnBatteries` 期望 `True / False`。
（防再犯檢查已加入 `SD09_Execution_Guide.md §3.0.6` SOP step 1b。）

---

## 二、06-26 W0 G0 前置檢查清單（實測 2026-06-23）

### 已完成項（v1.0 已打勾，覆核仍成立）
- [x] (4) Tech Lead W0 task breakdown ✅ 2026-05-20
- [x] (5) §6 PM 拍板 8 項 + 形式核准 ✅ 2026-05-20
- [x] (6) §7 三方研究意見摘要 13 bullet + 四方 APPROVED ✅ 2026-05-20
- [x] (7) ADR-SD09-001~006 草案落地 ✅ 2026-05-20
- [x] (8) git tag `sd_08_w6_g6_pass` ✅ 2026-05-18
- [x] (9) gate_audit.md §1-septies 骨架 ✅ 2026-05-20
- [x] (10) risk_log.md §15 骨架 ✅ 2026-05-20

### 三觀察期（時間累積閘 — 實測 g0_gate_check 2026-06-23T21:56）
- [~] (1) #1 mutation TokenGuard：kill_rate **76.5%** ✅ 達標；unique sha 仍凍結（`20940e1b...`）— **設計上 G0 後 W1 改 token_guard 源碼才解鎖**（ADR-SD09-009 §11.6），非 G0 阻塞點
- [ ] (2) #2 AC4 14 天全綠：**green_streak=9/14**，`ready_for_labeled_pr=false` → 零漏跑下最早 **2026-06-28**
- [ ] (3) #3 obs/drift 30 天零事件：**green_streak=24/30** → 零漏跑下最早 **2026-06-29**

### 前置動作（達標後執行，來自 g0_gate_check VERDICT / improving_34 §4）
- [ ] 建 `needs-pg-e2e` labeled PR + 更新 SD08_AC_Matrix AC4-2 pass date
- [ ] #3+#1 作為 W5 db_only cutover 雙條件（ADR-SD09-001 §2.2）
- [ ] 啟動 W1 GoalSynthesis mutation pilot（合法 token_guard 源碼變更解鎖 #1 unique sha）
- [ ] gate_audit.md §1-septies 記 SD09-G0 + 確認 ADR 形式核准

---

## 三、🔴 關鍵結論與 PM 決策點

**06-26 PM 硬 deadline 當天，#2（最早 06-28）與 #3（最早 06-29）皆未達標 → G0 無法以「全綠」簽核。**
綁定約束 = **#3 = 2026-06-29**（落後 deadline 3 天）。根因即 06-19~21 三天漏跑造成的順延。

依 §8.1 未達標處理矩陣分類：本案為**「順延」（infra 漏跑，訊號本身全綠、無黃/紅告警）**，**非「未達」（無降級 / 不需延 SD_10）**。

**建議路徑（待掌舵者 / PM 裁定）**：
1. **先套用第一節 schtasks 修復**（保證 06-24 起零漏跑，否則再漏一天 #3 順延至 06-30+）。
2. PM 將 W0 啟動日由 06-26 順延至 **~2026-06-29**（落在 PM #6「決策緩衝」語意內），於 #3 達標當日跑 `g0_gate_check.ps1` 確認 `[G0-READY]` 後正式簽核。
3. **禁止**在條件未齊前提前推進 PG db_only 切換（ADR-SD08-005 §2.2 / SD_09 §8.2 絕對禁止條款）。

**下次檢查點**：2026-06-28（#2 達標）、2026-06-29（#3 達標 → 跑 g0_gate_check → G0 簽核）。
