# AutoSDD improving_45 — B 軌 Dogfooding：DEF-CLDREV-007 工具面根除 + .claude 全面複驗

> **輪次**：improving_45（接續 improving_44=DEF-43-008系列/DEF-CLDREV-001~005；LATEST 框架版＝`AISDLC_SDD_v0.19`）
> **柱別**：**B 軌（手腳框架自我迭代 / Dogfooding）**為主——標的＝`AISDLC_SDD_v0.19/.claude`（5 hooks + 42 skills + settings.json）與其 shared infra（`AISDLC_SDD/scripts/`）
> **下一份**：improving_46（候選見文末）
> **日期**：2026-06-22　**掌舵者**：Dr. Alan（L10 自治系統與微核心架構總監）

---

## 0. 本輪緣起與目標

上輪（`.claude` 全面審查輪）將 3 條 P3 缺陷 routed 至本輪：
- **DEF-CLDREV-007（主軸）**：50 個 skill 標頭寫死「基於 AISDLC-SDD v0.01」、`README.md` 套件版停在 v0.02-SDD。**這是每輪 Copy-on-Evolve（複製 LATEST→新版）都會人工漏改的系統性摩擦**，過去無任何機制偵測。掌舵者明確指示「請徹底解決」＝**從工具面封閉**，而非再次人工補。
- **DEF-CLDREV-006**：`context_ledger_pre.py` docstring matcher 漏 `NotebookEdit`（文件漂移）。
- **DEF-CLDREV-008**：spec-logical-validator SKILL.md 規則清單僅列至 SLV-011、SLV-013/014 與 verified SLV-007 重名。

並再次回應使用者「全面確認所有 hooks/skills 是否符合 SDD 與系統架構、不適當則派 Architect/SA/SD/QA 修復」之要求。

**成功判準（Rule 4）**：(1) DEF-CLDREV-007 由機械工具根除、下輪 Copy-on-Evolve 漏改即 CI 紅；(2) 006/008 就地清償；(3) 四鏡 zero-trust 全 PASS；(4) 零退化（ci-gate EXIT=0、v0.19 passed ≥ floor 1618、0 failed）。

---

## 1. 階段一：現況重偵察（Zero-Trust，實測）

| 項目 | 實測結果 |
|------|---------|
| (a) 基線 ci-gate | `bash scripts/ci-gate.sh` **EXIT=0**；逐軌 **v0.01:1478 / v0.19:1618 / scripts/tests:113**（＝上輪結案值，**floor 成立**） |
| (b) DEF-CLDREV-007 重現 | v0.19 內 `**基於**: AISDLC-SDD v0.01` footer **42 處** + `README.md`/`SKILL_DEVELOPMENT_PLAN.md` 套件版 `v0.02-SDD` 各 1 ＝**44 處 stale** |
| (c) DEF-CLDREV-006 重現 | `context_ledger_pre.py:6` docstring matcher＝`Write\|Edit\|Read\|Bash`（漏 NotebookEdit），settings.json 實裝含 NotebookEdit |
| (d) DEF-CLDREV-008 重現 | SKILL.md description/argument-hint/規則表僅至 SLV-011；磁碟實有 SLV-001~014；SLV-013/014 與 verified SLV-007 同名（FPL-001 二次重生，內容除 trust_level/日期外全同） |
| (e) 新發現 | `stage-compaction/SKILL.md:158`、`SKILL_DEVELOPMENT_PLAN.md:269` 在 v0.19 skill 內寫死 `AISDLC_SDD_v0.01` 路徑（Copy-on-Evolve 漂移） |

**硬閘**：基線無 failed、達上輪 passed → 通過，准進階段二。

---

## 2. 階段二：增量設計

### <Architecture_Design_Review>
1. **架構純潔性**：`skill_header_sync.py` 放 `AISDLC_SDD/scripts/`（版本目錄**之上**的 shared infra，與 `sync_exposed_skills.py`/`framework_status_snapshot.py`/`rfc_lifecycle_lint.py` 同層同精神）→ **不在任何凍結 `v0.0X` 本體內、不隨 Copy-on-Evolve 複製**，不違反 Copy-on-Evolve 邊界。無 God-object（單一職責：戳記同步）。
2. **持久化相容**：不涉 PlaybookCheckpoint / DAL；純文字檔同步工具，無狀態。
3. **安全防護網**：工具僅讀寫框架自身 .md，無外部輸入、無 shell 注入面；regex 前綴鎖死防誤改 provenance。
4. **對外 I/O 安全**：無新增 `ToolInvocationPort` 外呼路徑。
5. **Copy-on-Evolve 邊界**：`--write` 只動 ci-gate LATEST（v0.19，可演化版），凍結基線（v0.01）戳記本就對齊自身目錄、不被重寫（`test_frozen_baseline_aligned_passes` 機械鎖死）。比照上輪「就地修 v0.19、不遞版」既定政策（不動 EVOLUTION_LOG/CHANGELOG）。

### 設計：`skill_header_sync.py`（SSOT＝所在版本目錄名）
- **真相源**：skill 框架版本戳應對齊其所在版本目錄；只校 LATEST（`sort -V | tail -1`，複用 `rfc_lifecycle_lint`）。
- **鎖定兩種精確樣式**：footer `**基於**: AISDLC-SDD vX.YY[（後綴）]`、套件版 `**版本**: vX.YY-SDD`。前綴鎖死故**不碰** provenance（`source: builtin (...v0.01...)`）/ 歷史事實（`6個…v0.01 新增`）/ 模板佔位版（`{N}.{N}`/`1.0`/`v1.0`）。
- **模式**：`--check`（ci-gate 硬閘，排於 skills 鏡像 lint **之前**＝戳記源頭先於鏡像）/ `--write`（同步並保留後綴）。
- **LOC**：~165 行（shared infra 腳本，無 LOC 分級紅線適用，對齊 sibling 體量）。

### 本輪 W 項（≤3 柱）
- **W-44-1**：建 `skill_header_sync.py` + 8 測試 + wire ci-gate（DEF-CLDREV-007 根除）。
- **W-44-2**：修 DEF-CLDREV-006（docstring）。
- **W-44-3**：修 DEF-CLDREV-008（SLV 文件清單 + SLV-013/014 superseded_by + 改名）；附帶清 stage-compaction/PLAN 寫死路徑（version-agnostic `v0.0X`）。

---

## 3. 階段三：實作與雙重驗證

- `skill_header_sync.py --write` 同步 **44 處**（42 footer + 2 套件版），後綴完整保留；`--check` 回 OK。
- 8 測試（正例 fire / 後綴保留 / README 同步；負例 provenance / 歷史 / 模板佔位鎖死；凍結基線邊界；token 擷取）→ **8 passed**；3 受控突變實證**非空殼**（M1 放寬前綴鎖→負例紅、M2 反向 stale 判斷→正例紅、M3 去後綴→保留測試紅）。
- DEF-CLDREV-006：pre.py docstring matcher 補 NotebookEdit。
- DEF-CLDREV-008：SKILL.md description→SLV-001~014、argument-hint 補 SANDBOX_HARDENING_GATE、新增 proposed 規則清單段；SLV-013/014.yaml 加 `superseded_by: SLV-007` + 改名（`slv_generator.load_rule` 容忍新欄位、test_slv_generator.py 35 passed；原誤植 39，DEF-CLDREV-016 訂正為實測 35，與本檔 §驗證表 line 75 一致）。
- stage-compaction:158 / PLAN:269 寫死 `AISDLC_SDD_v0.01` → version-agnostic `v0.0X` + 旁註（杜絕再漂）。
- 父層曝光鏡像 `sync_exposed_skills.py --write` 重生 59 檔。

---

## 4. 階段四：CI 平價收斂（零退化矩陣 — 最終態實測）

| 檢查 | 命令 | 通過條件 | 結果 |
|------|------|---------|------|
| AutoClaude/AISDLC 全套 | `bash scripts/ci-gate.sh` | EXIT=0、v0.19 ≥ floor 1618、0 failed | ✅ **EXIT=0**；v0.01:1478 / v0.19:**1623**（floor 1618 +5 dedup gate 測試，只增不減）/ scripts/tests:**121**（113+8 skill_header_sync 測試） |
| slv_generator 去重閘測試（DEF-CLDREV-011） | `pytest tools/fsm_runtime/tests/test_slv_generator.py` | 通過 | ✅ 35 passed（含 +5 dedup gate；突變 gate→`if False` 實證正例紅、非空殼） |
| 新工具測試 | `pytest scripts/tests/test_skill_header_sync.py` | 通過 | ✅ 8 passed（突變實證非空殼） |
| Skill 版本戳 lint（新） | `skill_header_sync.py --check` | 全對齊 LATEST | ✅ OK（全對齊 v0.19，0 stale） |
| 曝光 skills 鏡像 lint | `sync_exposed_skills.py --check` | 父層==LATEST | ✅ 59 檔一致 |
| 框架版本/計數 SSOT | `framework_status_snapshot.py --check` | fresh | ✅ fresh（skills 仍 42） |
| 五軌 TLC | （僅 FSM/*.tla 變更時） | — | **不觸發**（本輪 FSM/*.tla 零變更） |

---

## 5. RTM（需求→實作→驗證追溯）

| 需求 | 實作 | 驗證 | 狀態 |
|------|------|------|------|
| DEF-CLDREV-007 工具面根除 | `scripts/skill_header_sync.py` + ci-gate wire + 44 處同步 | 8 測試 + 突變 + `--check` OK + 四鏡 PASS | ✅ fixed@v0.19 |
| DEF-CLDREV-006 docstring 對齊 | `context_ledger_pre.py:6` 補 NotebookEdit | diff 確認 + SA 鏡驗一致 | ✅ fixed@v0.19 |
| DEF-CLDREV-008 SLV 清單/重名 | SKILL.md + SLV-013/014.yaml superseded_by/改名 | 35 SLV 測試 + SD 鏡驗磁碟一致 | ✅ fixed@v0.19 |
| 寫死 v0.01 路徑 | stage-compaction/PLAN → `v0.0X` | grep 殘留 0 + Architect/SA 鏡驗可執行性 | ✅ fixed@v0.19 |
| DEF-CLDREV-009/010（新，README 殘留） | README.md SLV-001~014 + `/integration-api-client` | grep 殘留 0 | ✅ fixed@v0.19 |
| DEF-CLDREV-011（掌舵者裁定直接解決，治本） | slv_generator 去重閘：`FplAlreadyVerified` + `find_verified_rule_for_fpl` + `allow_duplicate_fpl` 逃生口 + CLI exit 3 + SKILL.md 註記 | +5 測試 + 突變實證非空殼 + 真實 dir `FPL-001→SLV-007` 命中 | ✅ fixed@v0.19 |
| 零退化 | — | ci-gate EXIT=0、v0.19 passed +5（dedup 測試）、0 failed | ✅ |

---

## 6. 結案與下輪候選

- **B 軌結案條件達成**：新缺陷全入帳完成分流（DEF-CLDREV-009/010 即修、**011 經掌舵者裁定直接解決＝治本 fixed**）；上輪 routed DEF-CLDREV-006/007/008 全閉並附驗證。臨時審查塊 DEF-CLDREV-001~011 全閉、零 routed 殘留。
- **improving_46 候選**：
  1. C 軌 SD_09 W1（待 06-26 G0 觀察期閘門）。
  2. B 軌既有 open：DEF-37-001 / DEF-42-001。
  3. A 軌續偵察 adapter 保真度。
