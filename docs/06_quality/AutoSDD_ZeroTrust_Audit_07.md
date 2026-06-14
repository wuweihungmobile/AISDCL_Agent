# AutoSDD ZeroTrust 審計報告（第 7 輪）— improving_07

> **輪次**：07　｜　**日期**：2026-06-14　｜　**審計人**：Dr. Alan（主 agent 親跑）+ 多專家 Zero-Trust 審查閉環
> **範圍**：DEF-06-001（P3）取證友善性 — 雙軌 ci-gate 收斂補印逐軌 `N passed`（共享 CI infra，免 v0.05）。
> **絕對前提**：零退化。floor = **3069 passed / 0 failed**（本輪實測，非引用）。

---

## 1. 階段一 Zero-Trust 重偵察（實測，非文件宣稱）

| # | 項目 | 命令 | 實測結果 | 判定 |
|---|------|------|---------|------|
| (a) | AutoClaude 全套 pytest | `python -m pytest tests/ -q` | **3069 passed / 122 skipped / 0 failed**（95.15s） | ✅ = floor，**硬閘 PASS** |
| (b) | 架構契約 lint-imports | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken**（181 files / 460 deps） | ✅ 持平 |
| (c) | AISDLC_SDD 雙軌閘門（修復前基線） | `bash scripts/ci-gate.sh` | **exit 0**；v0.01:1478 passed / v0.04:1494 passed；arch_fitness exit 1 advisory 不阻擋 | ✅ 雙軌健康 |
| (d) | 上輪構件存在性 | 開檔複驗 | `ci-gate.sh` 雙軌 `FROZEN_BASELINE`+`LATEST` 在位；`scripts/tests/` 12 passed（version-resolution 4 + cross_version_guard 8） | ✅ 屬實 |
| (e) | open 缺陷重現 | log/grep | **DEF-06-001 重現**（`/tmp/cigate_before_07.log:50` 收斂行無逐軌計數）；DEF-01-007（cc-switch 未裝）續 open；DEF-01-009 已自癒 watch | ✅ 已盤點 |

**硬閘**：(a) 0 failed 且 3069 = 上輪 floor → 通過，准進階段二。

---

## 2. 階段二/三 增量設計與實作（DEF-06-001）

### 2.1 變更清單（git diff 範圍）

| 檔案 | 性質 | 變更 |
|------|------|------|
| `AISDLC_SDD/scripts/pytest_passed_count.sh` | **新增**（純函式 helper，共享 infra） | 讀 stdin → 印最終 `N passed` 整數，fail-soft 無匹配回 0 |
| `AISDLC_SDD/scripts/ci-gate.sh` | **additive 修改** | `GATE_SUMMARY` accumulator + `tee` 擷取逐軌 passed + 逐軌 echo + 收斂彙總行 |
| `AISDLC_SDD/scripts/tests/test_pytest_passed_count.py` | **新增**（回歸測試，7 case） | 鎖定擷取意圖（subtests 邊界 / 多匹配取最後 / fail-soft / 取最終 summary） |

**零觸碰**：AutoClaude（`core/`/`plugins/`/`adapters/`/`execution/`）；AISDLC_SDD 任一 v0.0X **凍結源碼本體**（`agent/`/`governance/`/`workflow/`/`tools/`/`.claude/`/`docs_template/`/`scenarios/`/`cicd/`/`guides/`）。**免 Copy-on-Evolve、無 v0.05、免五軌 TLC**（無 `_HAPPY_PATH`/`.tla` 改動）。

> **取證精確性聲明（A-1）**：本輪 dogfooding 跑 v0.04 ci-gate 時，FSM runtime hook 對 `AISDLC_SDD_v0.04/build/reports/`（CLAUDE.md 定義之**可寫運行工作區**、regenerable artifacts）追加了 8 個檔的時間戳/log——此屬 `build/` 運行 churn，**非凍結源碼本體改動**，且已於收尾以 `git checkout -- …build/reports/` 還原，最終 commit diff 不含任何 v0.0X 內容。故「凍結本體零改動」嚴格成立於**源碼本體**層級。

### 2.2 `<Architecture_Design_Review>` 四項自洽（見 improving_07.md §1）

1. 架構純潔性：✅ 無 God-object，thin orchestrator 維持，純函式抽出沿用 `cross_version_guard.py` 慣例。
2. 持久化相容：✅ N/A（零 DAL/checkpoint/alembic 觸碰；helper 純讀、用後即 rm 暫存）。
3. 安全防護網：✅ 無「從文件生成指令」路徑；helper 僅 grep 受信 pytest stdout，無 eval/注入面；`pipefail` 保留硬閘語意。
4. 對外 I/O 安全：✅ 否（無 `ToolInvocationPort`/網路/新網域）。

---

## 3. 階段四 CI 平價收斂（零退化矩陣全項實測）

| 檢查 | 命令 | 通過條件 | 實測 | 判定 |
|------|------|---------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 3069 / 0 failed | **3069 passed / 122 skipped / 0 failed**（95.15s） | ✅ |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept / 0 broken | **8 kept / 0 broken** | ✅ |
| AISDLC_SDD 雙軌閘門 | `bash scripts/ci-gate.sh` | 雙軌 not-chaos 全綠 + arch_fitness exit<2 + **收斂自證逐軌計數** | **exit 0**；逐軌 echo + 收斂行 `逐軌計數：v0.01:1478 v0.04:1494` | ✅ |
| 共享 infra 測試 | `pytest scripts/tests/` | 全綠（既有 12 + 新 7） | **19 passed**（2.31s） | ✅ |
| 五軌 TLC | 不觸發（無 `.tla` 改動） | N/A | — | — |

### 3.1 DEF-06-001 驗收（修復前 vs 後）

- **修復前** `/tmp/cigate_before_07.log:50`：`✅ 本機 CI 閘門全數通過（版本：AISDLC_SDD_v0.01 AISDLC_SDD_v0.04）`（**收斂行無逐軌計數**；逐軌數字僅散落於 `:24`/`:98` 各軌 pytest 尾行 → 截斷視窗不可見）。
- **修復後** `/tmp/cigate_final_07.log`（最終確認跑）：
  - 逐軌 echo：`==> [1/3] AISDLC_SDD_v0.01: 1478 passed（not chaos）` / `AISDLC_SDD_v0.04: 1494 passed（not chaos）`
  - 收斂彙總行：`逐軌計數：AISDLC_SDD_v0.01:1478 AISDLC_SDD_v0.04:1494`（**單次輸出即自證逐軌結果**，免捲動截斷輸出）
  - exit 0 維持；arch_fitness advisory 不阻擋（語意不變）。

### 3.2 helper 純函式單測（測意圖，Rule 9）

`test_pytest_passed_count.py` 7 case 全綠，鎖定：(1) plain `N passed`→N；(2) **subtests 邊界**（`… 14 subtests passed` 第二 token → 仍回主計數 1478，非 14）；(3) 多行取最終 summary；(4) **多 `N passed` 匹配取最後**（釘 `tail -1` 防退化，QA-1 補強：實證把 helper 改 `head -1` 此 case 即回 1478≠1494 變紅）；(5) 無匹配 fail-soft 回 0（取證輔助不反害硬閘）；(6) 含 failed 仍正確取 passed。

---

## 4. 多專家 Zero-Trust 審查閉環

> 派發獨立審查 agent 對「文件 vs 系統現況」全面比對（Architect / SA-SD / QA 三鏡，完全不信任親跑複核）。本輪無 mutation/並行就地寫檔，審查 agent 讀工作樹即可，無需 worktree 隔離（流程 #11 條件未觸發）。

### 4.1 三鏡親跑結論（不引用本文件數字，審查 agent 自行重跑）

| 鏡 | 結論 | 親跑證據摘要 |
|----|------|------------|
| Architect（架構紅線/凍結本體/硬閘語意） | **PASS** | 親跑 `pytest tests/ -q`＝3069 passed/0 failed（100.25s）；`lint-imports`＝8 kept/0 broken；mini-harness 實證 pytest 非零時 pipefail+set -e 在彙總前中止（false-green 從不印出）；v0.0X 凍結源碼本體零改動 |
| SA-SD（介面誠實性/文件 vs 實況/缺陷帳本） | **PASS** | 親跑 `pytest scripts/tests/`＝全綠；DEF-06-001＝fixed@improving_07 證據鏈完整、收斂格式與實況逐字吻合、無虛報漏記 |
| QA（DEF-06-001 驗收/非假測試/fail-soft） | **PASS** | 乾淨隔離單跑 ci-gate `CLEAN_EXIT=0` + 收斂行自證 `v0.01:1478 v0.04:1494` + 逐軌 echo；helper subtests 邊界回 1478、fail-soft 回 0、含 failed 回 1491 全對 |

### 4.2 審查發現 3 項 P3 非阻擋瑕疵 → 已全數修復（不留 partial）

| # | 發現 | 修復 |
|---|------|------|
| **SA-1**（文件 vs 碼不一致） | improving_07.md §2.2/§2.3/§3.3/RTM 寫 `1478passed`/`GATE_SUMMARY+=("...passed")`，但落地碼 `ci-gate.sh` 為無 `passed` 後綴 | improving_07.md 全部對齊為 `v0.01:1478 v0.04:1494`（無後綴）；Defect_Log/Audit_07 原已正確 |
| **A-1**（凍結本體聲明不精確） | 原聲稱「無任何 v0.0X 檔案被改」，但 dogfooding 使 `v0.04/build/reports/` 8 檔時間戳變動 | (1) 措辭限定為「凍結**源碼**本體」+ 註明 build/reports 為 regenerable artifacts（見 §2.1 取證精確性聲明）；(2) `git checkout` 還原該 8 檔，最終 commit 不含 v0.0X 內容 |
| **QA-1**（測試強度缺口） | 原 6 case 無一產生 ≥2 個 `N passed` 匹配 → `tail -1` 防禦語意未被釘（head -1 突變不變紅） | 補第 7 case `test_multiple_passed_lines_takes_last`（兩個 `N passed`→須回最後）；實證 head -1 突變使其回 1478≠1494 變紅，缺口閉合 |

### 4.3 修復後複驗（QA 複審）

- `scripts/tests/` **19 passed**（12 既有 + 7 新，含新增 tail-last 釘樁 case）。
- 工作樹收斂為外科手術式乾淨：僅 `ci-gate.sh`（M）+ `Defect_Log.md`（M）+ 4 新檔（helper / test / improving_07 / audit_07），**無任何 v0.0X 凍結本體或 build/reports churn**。
- 三鏡核心結論不變：零退化守住、DEF-06-001 修復生效、缺陷帳本誠實、無偽綠。**全 PASS，准結案。**

---

## 5. 缺陷帳本本輪變更

| 缺陷 | 變更 |
|------|------|
| DEF-06-001 | open → **fixed@improving_07**（附 §3.1 修復前後對比 + helper 7 case 證據） |
| DEF-01-007 | 續 open（cc-switch 環境工具未裝，本輪不涉） |
| DEF-01-009 | 續 watch（已自癒，本輪零擴充不碰） |
| **DEF-07-001（新）** | P3 流程摩擦（計畫文件介面描述與落地碼 drift，SA-1 之記帳；與 DEF-05-002 同根）→ **fixed@improving_07**（同輪修復）+ routed 範本補「實作後回掃文件引用」檢核 |

---

## 6. 結論

- 零退化守住：AutoClaude **3069/0** 持平、lint-imports **8/0**、雙軌 ci-gate **exit 0**。
- DEF-06-001 **fixed@improving_07**：雙軌收斂單行自證逐軌計數，取證友善性摩擦消除；共享 infra 免 v0.05。
- 架構紅線零破壞：AutoClaude 微核心 / AISDLC_SDD 凍結源碼本體零改動。
- 多專家三鏡（Architect/SA-SD/QA）親跑複核**全 PASS**；審查發現 3 項 P3 非阻擋瑕疵（SA-1/A-1/QA-1）已**同輪全數修復**（§4.2），QA 複審 19 passed、工作樹乾淨（§4.3）。
- B 軌 dogfooding 新記 **DEF-07-001**（P3 流程摩擦，fixed@improving_07 + routed 範本），缺陷帳本完整誠實無漏記。
- **正式結案准予**：四件套齊備，零退化矩陣全綠，待 §7 🔴 人工確認凍結即可 commit。
