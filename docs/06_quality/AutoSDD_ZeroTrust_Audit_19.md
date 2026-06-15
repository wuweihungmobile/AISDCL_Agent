# AutoSDD_ZeroTrust_Audit_19 — improving_19（B 軌 catch 側契約）零信任審計

> 對應計畫書 `docs/04_planning/AutoSDD_improving_19.md`。本檔記錄階段一實測、三鏡審查、修復回合與複驗證據（zero-trust：實測命令輸出為準，禁文件宣稱當事實）。

---

## 1. 階段一實測（基線硬閘，全守住）

| 檢查 | 命令 | 實測 | floor | 判定 |
|------|------|------|-------|------|
| AutoClaude pytest | `python -m pytest tests/ -q` | 3112 passed / 0 failed / 122 skipped | 3112 | ✅ |
| lint-imports | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | 8 | ✅ |
| LOC budget | `check_loc_budget.py` | violations=0（total=17794/cap=20438） | 全過 | ✅ |
| snapshot | `snapshot_sync.py --check` | 新鮮 | 新鮮 | ✅ |
| AISLDC_SDD ci-gate | `ci-gate.sh` | exit 0（v0.01:1478 / v0.09:1534 / scripts:25） | exit 0 | ✅ |

**硬閘無觸發** → 准進階段二。

---

## 2. 階段四零退化矩陣（改動後實測）

| 檢查 | 實測 | 判定 |
|------|------|------|
| AutoClaude pytest | 3112（git status 證 AutoClaude/ 零改動 → 不可能退化，沿用階段一） | ✅ |
| lint / LOC / snapshot | 8 kept / violations=0 / 新鮮（AutoClaude 未動） | ✅ |
| AISLDC_SDD 雙軌 ci-gate | **exit 0，版本：v0.01 + v0.10**；v0.01:1478 / **v0.10:1545** / scripts:25 | ✅ |
| v0.10 全套 not-chaos | 1545 passed / 4 skipped / 0 failed（v0.09 1534 + 11 catch case，只增不減） | ✅ |
| 五軌 TLC | transition_rules.py + 5 *.tla 對 v0.09 逐位元零差異 → 免 | ✅ |

**flaky 註記**：`test_file_lock.py::test_parallel_writes_do_not_lose_increments` 某次 ci-gate 跑出 Windows O_EXCL 並行檔案鎖 PermissionError；單獨重跑 3×全 passed，本輪未碰 file_lock.py（逐位元複製自 v0.09）→ 確認環境 flaky 非退化；重跑 ci-gate 全綠。

---

## 3. DEF-19-002 修復實證（B 軌 dogfooding 抓到的真 bug）

版本偵測 glob `AISDLC_SDD_v0.0*` 在 v0.09→v0.10（開頭 `v0.0`→`v0.1`）失效，致最新演化版 v0.10 不入官方閘門。

- 修復前：`ls -d AISDLC_SDD_v0.0* | sort -V | tail -1` = **v0.09**（漏 v0.10）；首跑 ci-gate「版本：v0.01 v0.09」。
- 修復後（雙 glob）：`ls -d AISDLC_SDD_v0.0* AISDLC_SDD_v0.[1-9]* | sort -V | tail -1` = **v0.10**；dry-run `SDD_GATE_VERSIONS=AISDLC_SDD_v0.01 AISDLC_SDD_v0.10`；雙軌 ci-gate exit 0「版本：v0.01 v0.10」。
- 三處 glob 修復：`scripts/ci-gate.sh`（雙 glob，保 `v0.0*` 子串向後相容 v0.01 凍結 FF-17 regex）、`scripts/tests/test_ci_gate_version_resolution.py`（`_disk_versions`→`v0.*`）、`v0.10/tools/arch_fitness/arch_fitness.py`（`_latest_version_dir`→`v0.*`）。
- v0.01 凍結基線 FF-17 因保留 `v0.0*` 子串不破；FF-17 測試 5 passed。

---

## 4. 多專家三鏡審查閉環（修復回合=1）

| 鏡 | 結果 | 重點 |
|----|------|------|
| **Architect** | **OVERALL PASS（6/6）** | 架構純潔性（catch/fire 對偶同層、_record_escalation_catches thin）；接入點正確（record_escalation 繞過 transition() 屬實、只接 transition() 確會漏 gate_fail）；持久化陷阱解法正確；紅線只增計數；6 檔逐位元零差異免 TLC；雙 glob 修復正確。無誇大。 |
| **SA-SD** | **OVERALL PASS（6/6）** | catch 三要件程式真實實現（非僅文件）；無 last_fired_rules（未用時序猜測）；R-9.1/R-9.21 failure_mode 語意一致無歧義；coverage 2/39 誠實揭露；DEF-19-002 描述實跑印證；EVOLUTION_LOG/CHANGELOG 四欄一致。無不符。 |
| **QA** | **FAIL → 修復後 PASS** | 11 catch case 全為真測試（Case 9 交集語意 / Case 10 持久化回歸鎖品質最高，無假測試）；1545 passed 零退化；帳本三筆誠實。**唯一 FAIL（阻擋）**：`AISDLC_SDD/.gitignore` 缺 v0.10 區塊 → would-add 858 含 12 runtime 產物（arch-fitness.json + build/reports/abort/fsm/test-analysis runtime 輸出）。 |

### 4.1 QA FAIL 修復 + 複驗
- **根因**：Copy-on-Evolve 當下 would-add 乾淨 846（copy_on_evolve.sh 已排除 build/reports），但**後續跑 ci-gate/pytest 在 v0.10 生成 runtime 產物**，而 `AISDLC_SDD/.gitignore` 有 v0.01/v0.05~v0.09 區塊卻**缺 v0.10 區塊**（DEF-11-002 家族問題重現，與 improving_18 同款）。
- **修復**：補 `AISDLC_SDD/.gitignore` v0.10 區塊（比照 v0.09，含 negate 保留 FSM 種子模板）。
- **複驗（達 QA 自訂 PASS 標準）**：would-add **847**（846 凍結本體 + 1 新測試檔 test_rule_catch_telemetry_wiring.py）；runtime 殘留檢查（arch-fitness.json / chaos-report.json / build/reports/abort|test-analysis / CONTEXT-LEDGER / FSM-STATE-AISDLC / MONITOR-VIOLATION）**全空**；FSM-STATE-TEMPLATE.yaml 經 negate 正確保留。→ **QA 鏡複審 PASS**。

**三鏡最終：Architect 6/6 + SA-SD 6/6 + QA 修復後 PASS。**

---

## 5. 缺陷帳本（誠實揭露）

- **DEF-18-001**：routed → **fixed@v0.10**（catch 側契約定義並接入）。
- **DEF-19-001**（P3, open/routed）：catch 歸因僅覆蓋 2/39 規則，餘漸進補強（`catch_attribution_coverage` 程式內揭露）。
- **DEF-19-002**（P2, **fixed@v0.10 + 共享 infra**）：版本偵測 glob v0.0* 在 v0.10 失效，雙 glob 修復。殘留：第三處同款 glob 未通則化（下輪可考慮 FF 結構守門，類 FF-17）。

---

## 6. 成熟度誠實結論

交付 B 軸「L5 catch 遙測能力 + 證據」；flag 預設 OFF＝**運行仍 L4**，未虛報運行躍 L5、未動 `L_合體`（維持 L4 信號邊界）。catch 覆蓋 2/39＝刻意保守（寧缺勿濫，守 DEF-18-001 紅線），餘漸進補強。
