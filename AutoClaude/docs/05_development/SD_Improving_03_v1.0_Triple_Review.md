# SD_Improving_03 v1.0 — Architect / QA / PM 三方審查彙整報告

| 項目 | 內容 |
|------|------|
| 審查日期 | 2026-05-08 |
| 審查目標 | [SD_Improving_03_Phase4_Real_Switch.md](../04_planning/SD_Improving_03_Phase4_Real_Switch.md) **v1.0**（Draft） |
| 審查方式 | Architect / QA / PM 三方並行獨立審查 |
| 綜合 Verdict | **REJECT — 需大幅修訂為 v1.1** |
| 修訂結果 | SD_03 升 v1.1（同日完成）；本檔留作審查紀錄與 W0 KickOff 參考 |
| 下次觸發 | v1.1 三方覆審 / SD_03 Sprint W0 KickOff |

---

## 1. 三方 Verdict 總表

| 審查角色 | Verdict | Critical | Major | Minor | 主要打擊點 |
|---------|---------|----------|-------|-------|-----------|
| **Architect** | APPROVE WITH CONDITIONS | 5 | 5 | 6 | 雙 Kernel 風險、API leaky abstraction、4 高機率風險漏列、LOC 數字錯、W4 過載 |
| **QA** | **REJECT** | 4 | 7 | 5 | byte-level 物理不可達（step_log 字串格式 vs dry_run baseline）、F2 mock 耦合 ≥ 11 處、`.loc_baseline` 三處錯誤 |
| **PM** | APPROVE WITH CONDITIONS | 5 | 5 | 5 | 4 → 5 週、W4 過載、缺治理欄位（Owner/FTE/PD/延期決策權）、缺 Alternative Considered、與 Phase6 P1 取捨論證 |

**綜合 Verdict**：**REJECT**（QA 嚴格 reject + Architect/PM 合計 14 個 Critical 條件項超過 APPROVE WITH CONDITIONS 容忍上限）

---

## 2. 三方共同打擊點（11 項，跨角色重疊）

### 2.1 byte-level Equivalence 物理不可達 ⭐ 最高優先

- **QA C1**：`step_log` 字串格式從根本不同
  - `_runner_impl.py:586`：`f"[{task.step_id}] {task.name} ✓ (attempt {attempt + 1})"`
  - `kernel.py:159`：`f"[OK] {task.step_id} (attempt={attempt})"`
  - `tests/integration/test_kernel_facade.py:10` 已自承「不要求 byte-level 等價」
- **QA C3**：snapshot baseline 全部由 dry_run 模式產生（`_StepOutput(text=f"[dry-run] {keyword}")`），Kernel 路徑無同等短路
- **Architect C8**：Plugin priority 順序與舊 hardcoded log 順序衝突
- **修訂**（v1.1 §2.4）：
  - 降級為 **semantic-level**：`completed_steps / counters / failure_history / halt_for_token / evolved_playbook_path` 完全一致；`step_log` 行數 + step_id 集合 + regex 解析一致
  - **兩階段 baseline**：Stage A（CI 強制，semantic-level）+ Stage B（manual smoke）
  - **W0 prerequisite**：W0a（step_log 對齊）+ W0b（KernelResult 補 5 欄位）+ W0c（Kernel dry_run 短路）

### 2.2 W4 五件事 + G3 簽核 = 自殺式排程

- **三方一致**（Architect C5 / PM C2 / QA M6）
- **修訂**（v1.1 §4.1）：4 → **5 週**；W4 拆分為 W4（F3 + M1 + M6 + G3 簽核）+ W5（M4 + 復盤）；M2 前移至 W2

### 2.3 `.loc_baseline` 數字錯誤

- **QA C4**：v1.0 引用 8137 / 8500，真實值 7398
- **Architect C4**：v1.0 數字三處不一致
- **修訂**（v1.1 §5.3）：統一為 7398；補完整 LOC delta 表（11 個檔案 before/after/delta）

### 2.4 F2 反向委派風險嚴重低估

- **QA C2**：grep 證實 `runner._checkpoint_mgr` 在 24 個含 mock 的測試檔出現
- **Architect C3**：含本 sprint 自身 baseline 測試（`equivalence/test_runner_snapshot.py:77`）
- **PM C3**：W1 一週改不完即整 sprint cascade fail
- **修訂**（v1.1 §3.3）：W1 拆 W1a（前 3 日測試解耦）+ W1b（後 2 日委派）；DeprecationWarning 預設關閉、W4 才開 strict 模式

### 2.5 API 簽章違反 SD_02 §1.2.1 leaky abstraction 禁令

- **Architect C2**：v1.0 範例 `save(playbook_path)` 直接傳完整 path 給 IStateRepository
- **修訂**（v1.1 §3.1）：補 `_to_id(playbook_path) -> stem` 轉換；補完整 6 個 API（漏列 `seconds_until_resume / checkpoint_path / exists`）

### 2.6 §2.2 facade fallback 自建 Kernel = 雙 Kernel 副作用

- **Architect C1**：注入 + fallback 自建會建兩個 Kernel；`KnowledgeBasePlugin / CheckpointPlugin` 註冊到不同 EventBus → record_success / checkpoint 寫兩次
- **修訂**（v1.1 §2.2）：strict-injection；`kernel=None` 走 DeprecationWarning；唯一 Kernel 來源

### 2.7 §4.3 風險矩陣漏列高機率風險、未承接 R-1~R-12 編號

- **Architect C3**：漏列 4 個風險（Plugin priority / both 模式 silent drop / 跨 Plugin state / W1 連鎖失敗）
- **PM C10**：未承接 risk_log.md R-1 / R-4 / R-9 觸發條件
- **QA M3 / M4**：dry_run baseline 失效未列風險
- **修訂**（v1.1 §4.3）：補 R-13~R-16（業務風險）+ R-G1~R-G4（治理風險）；對應 R-ID 欄；回滾策略欄

### 2.8 DoD 缺 Stakeholder 簽核 / staging smoke / 9 項 shim 自動化驗證 / 文件 propagation / Sprint 復盤

- **PM C6**：DoD 13 項缺 5 項
- **QA M1**：9 項 shim 純委派無自動化檢查機制
- **QA M2**：「`storage.mode=both` log 可見 PG shadow write」非 deterministic 無法 CI 驗
- **修訂**（v1.1 §5.1~§5.6）：DoD 拆 6 段 32 項；新增 `tools/check_frozen_surface_shim.py`（AST 驗證）；新增 10 項補測；新增 staging dual-write 24h drift=0；新增 Sprint 復盤文件

### 2.9 治理欄位完全缺失（PM 視角）

- **PM C3**：相比 SD_02 §2.1 / §6 既有「Owner / FTE / 決策時限 / 升級條件」治理規範，SD_03 v1.0 退步
- **修訂**（v1.1 §4.1 + §7）：每週排程加 Owner / FTE / PD 欄；新增 §7 Q-1~Q-5 待解問題（仿 SD_02 §6 風格）

### 2.10 §0 缺 Alternative Considered

- **PM C5**：v1.0 直接跳到「本 SD 是 Phase 4 真正切換」，無「為何不在 SD_02 v1.2 補修」/「為何不採用 dual-write feature flag」論證
- **修訂**（v1.1 §0.1）：補 3 個替代方案 + trade-off 表；採方案 C 並融合方案 B 的 feature flag 機制

### 2.11 `KernelResult` ↔ `PlaybookResult` 欄位映射 1:0

- **QA M7**：KernelResult 缺 `workflow / halt_for_token / scheduled_resume_at / evolved_playbook_path / evolution_fresh_required` 5 欄位；v1.0 §2.2 直接寫 `_adapt_result()` 無來源
- **修訂**（v1.1 §2.6）：補完整 mapping table；W0b prereq 擴充 KernelResult；補測 `test_result_mapping.py`

---

## 3. 三方各自獨家 findings

### 3.1 Architect 獨家

| # | 標題 | 修訂 |
|---|------|------|
| Architect M7 | AutoResumeService Layer 歸屬未指定 | v1.1 §2.1 + §2.5 明示 Layer 2 wrapper |
| Architect C9 | 缺 Component / Sequence Diagram | v1.1 §2.5 補完整 Component Diagram |
| Architect M10 | F2 漏列 wiring.py 改注入 IStateRepository / IMemoryStore | v1.1 §3.2 補完整 wiring.py diff |
| Architect Minor 12 | shim 訪問 Kernel `_eval` 私有屬性 | v1.1 §2.2 範例改用 public property `evaluator` |

### 3.2 QA 獨家

| # | 標題 | 修訂 |
|---|------|------|
| QA M5 | `_runner_impl.py` 內隱含相依未識別（`_handle_token_halt` 收 7 個 local） | v1.1 §2.3 補 HookContext payload 契約（7 必要欄位） |
| QA M6 | CI 阻擋強化時機應 W1 而非 W4 | v1.1 §4.1 + §4.4 每週末硬阻擋 + Daily Smoke |
| QA Minor m3 | `evolved_playbook_path` 含時間戳的 byte-level 不可重現 | v1.1 補測 #9 `test_evolved_playbook_deterministic_filename.py` |

### 3.3 PM 獨家

| # | 標題 | 修訂 |
|---|------|------|
| PM C1 | W2-W3 兩週搬 600~700 行嚴重低估（對比 SD_02 Phase 3 7 週 25~40 PD） | v1.1 §4.1 拆 5 週 + W2 Token HALT / W3 mutation + auto_resume |
| PM C4 | SD_02 文件本身未同步修正 | v1.1 §5.5 加「SD_02 升 v1.2 banner」DoD |
| PM Major 7 | M4 與 Phase6 P1 #1~#5 priority 衝突 | v1.1 §1.3 補取捨論證；M4 完成後 PG 仍處 dual-write 影子，production 仍需 P1 #1~#5 |
| PM Major 9 | §6 缺與 gate_audit.md / risk_log.md / Phase6 P1 交叉引用 | v1.1 §6 補完整 5 個交叉引用 |

---

## 4. v1.0 → v1.1 修訂落地對照表

| 修訂範圍 | 對應 finding | v1.1 章節 |
|----------|--------------|-----------|
| §0.1 Alternative Considered | PM C5 | 新增 |
| §2.1 main.py try/except MinimaxError | Architect 16 | 補完 |
| §2.1 AutoResumeService Layer 2 註解 | Architect M7 | 補完 |
| §2.2 strict-injection facade | Architect C1 | 重寫 |
| §2.2 9 項 Frozen Surface 對照表 | Architect M6 | 新增 |
| §2.3 「剩餘 1500 行」→ ≤ 600 | Architect 13 | 修正 |
| §2.3 HookContext payload 契約 | QA M5 | 新增 |
| §2.3 Plugin emit ordering 對齊 | Architect C8 / R-13 | 新增 |
| §2.4 byte-level → semantic-level | QA C1 / C3 / Architect C8 | 重寫 |
| §2.4 W0 prerequisite（W0a/b/c） | QA C1 | 新增 |
| §2.4 snapshot regen 雙簽流程 | QA Minor 12 | 新增 |
| §2.5 Component Diagram | Architect C9 | 新增 |
| §2.6 KernelResult ↔ PlaybookResult mapping | QA M7 | 新增 |
| §3.1 stem 轉換 + 完整 6 API | Architect C2 / QA C2 | 重寫 |
| §3.2 wiring.py diff（Port 注入） | Architect M10 | 新增 |
| §3.3 W1 拆 W1a/W1b | QA C2 / Architect C3 | 新增 |
| §4.1 4 → 5 週 + Owner/FTE/PD 欄 | 三方一致 | 重寫 |
| §4.2 G3 簽核三方 ✅ + 3 工作日上限 | PM C3 / PM C6 | 新增 |
| §4.3 R-13~R-16 + R-G1~R-G4 + R-ID 欄 | Architect C3 / PM C10 / QA M3 | 重寫 |
| §4.4 中段檢核點 + Daily Smoke | PM C8 / QA m2 | 新增 |
| §5.1~§5.6 DoD 拆 6 段 32 項 | PM C6 / QA M1 | 重寫 |
| §5.3 LOC budget 統一 7398 + delta 表 | QA C4 / Architect C4 | 重寫 |
| §6 完整 5 交叉引用 | PM Major 9 / Architect 11 | 補完 |
| §7 Q-1~Q-5 待解問題 | PM C3（仿 SD_02 §6 風格） | 新增 |

---

## 5. 結論與下一步

### 5.1 v1.0 結論

- 方向正確（Phase 4 確實未真正切換）但 **Draft 品質不足以啟動 sprint**
- 核心問題 byte-level Equivalence 物理不可達若不修正，sprint W2 即會撞牆
- 治理欄位相比 SD_02 退步（PM C3 為 v1.0 不可接受的核心問題）

### 5.2 v1.1 修訂結果

- 同日完成（2026-05-08）
- 修訂範圍涵蓋 14 Critical（100%）+ 17 Major（100%）+ 16 Minor 中重要部分
- 文件規模：v1.0 ~270 行 → v1.1 ~520 行

### 5.3 下一步建議

1. **三方覆審 v1.1**：建議在 W0 KickOff 前一週完成；若 v1.1 仍有 Critical，則繼續修為 v1.2
2. **W0 KickOff**：指派 Tech Lead（Q-1）+ pair review owner（Q-3 R-G3 緩解）+ FTE 確認
3. **同步更新 SD_02 v1.2**：在 §2.6 / §4 加 banner「⚠️ Phase 4 實際完成由 SD_03 補完」（v1.1 §5.5 DoD）
4. **同步更新 risk_log.md**：補 R-13~R-16 + R-G1~R-G4（已隨本次 commit 完成）
5. **同步更新 gate_audit.md §1 G3**：紀錄三方審查結果（已隨本次 commit 完成）

---

**文檔元數據**：
- 撰寫者：Phase 0~6 重構稽核 + SD_03 三方審查彙整
- 三方審查 Agent ID（內部追蹤）：Architect aa7a6de8 / QA a927b9e6 / PM a4d78c26
- 對應修訂：[SD_Improving_03.md v1.1](../04_planning/SD_Improving_03_Phase4_Real_Switch.md)
- 對應風險記錄：[risk_log.md](risk_log.md) §6
- 對應 Gate 紀錄：[gate_audit.md](gate_audit.md) §2 G3
- 下次審查觸發：SD_03 v1.1 三方覆審 / W0 KickOff
